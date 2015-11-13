__FILENAME__ = app_settings
"""Application-specific settings."""
import os
from django.conf import settings as _settings
from django.core.exceptions import ImproperlyConfigured


###############################################################################
# Single settings.
###############################################################################
class Setting(object):
    """Settings option helper class."""
    def __init__(self, **kwargs):
        """Initializer.

        :kwarg default: Override default for getting.
        :type  default: ``object``
        :kwarg from_env: Allow variable from evironment.
        :type  from_env: ``bool``
        :kwarg valid_set: Set of valid values for setting.
        :type  valid_set: ``set``
        """
        self.from_env = kwargs.get('from_env', False)
        self.default = kwargs.get('default', None)
        self.valid_set = kwargs.get('valid_set', None)

    def validate(self, name, value):
        """Validate and return a value."""

        if self.valid_set and value not in self.valid_set:
            raise ImproperlyConfigured(
                "%s: \"%s\" is not a valid setting (choose between %s)." %
                (name, value, ", ".join("\"%s\"" % x for x in self.valid_set)))

        return value

    def env_clean(self, value):  # pylint: disable=R0201
        """Clean / convert environment variable to proper type."""
        return value

    def get(self, name, default=None):
        """Get value."""
        default = default if default is not None else self.default
        try:
            value = getattr(_settings, name)
        except AttributeError:
            value = os.environ.get(name, default) if self.from_env else default
            # Convert env variable.
            if value != default:
                value = self.env_clean(value)

        return self.validate(name, value)


class BoolSetting(Setting):
    """Boolean setting.."""
    def env_clean(self, value):
        """Clean / convert environment variable to proper type."""
        return self.parse_bool(value)

    @classmethod
    def parse_bool(cls, value, default=None):
        """Convert ``string`` or ``bool`` to ``bool``."""
        if value is None:
            return default

        elif isinstance(value, bool):
            return value

        elif isinstance(value, basestring):
            if value == 'True':
                return True
            elif value == 'False':
                return False

        raise Exception("Value %s is not boolean." % value)


###############################################################################
# Settings wrapper.
###############################################################################
class Settings(object):
    """Cloud Browser application settings.

    This class wraps the "real" Django settings object, so can be used instead.
    The additional cloud browser settings are as follows:

    .. note::
      **Environment Variables**: Certain credential settings can come from OS
      environment variables instead of from a settings file value to open up
      more options for secrets management. Values that can be set in the
      environment are designated with an "(*Env*)" notation.

      Setting a value this way could be done, e.g.::

          $ export CLOUD_BROWSER_AWS_ACCOUNT="my_account"
          $ export CLOUD_BROWSER_AWS_SECRET_KEY="my_secret"
          $ # ... start django application with environment variables.

    **Datastore Settings**:

    * ``CLOUD_BROWSER_DATASTORE``: Choice of datastore (see values below).

    **Amazon Web Services**: Configure AWS S3 as backing datastore.

    * ``CLOUD_BROWSER_DATASTORE = "AWS"``
    * ``CLOUD_BROWSER_AWS_ACCOUNT``: Account name. (*Env*)
    * ``CLOUD_BROWSER_AWS_SECRET_KEY``: Account API secret key. (*Env*)

    **Google Storage for Developers**: Configure Google Storage as backing
    datastore.

    * ``CLOUD_BROWSER_DATASTORE = "Google"``
    * ``CLOUD_BROWSER_GS_ACCOUNT``: Account name. (*Env*)
    * ``CLOUD_BROWSER_GS_SECRET_KEY``: Account API secret key. (*Env*)

    **Rackspace**: Configure Rackspace Cloud Files as backing datastore.

    * ``CLOUD_BROWSER_DATASTORE = "Rackspace"``
    * ``CLOUD_BROWSER_RACKSPACE_ACCOUNT``: Account name. (*Env*)
    * ``CLOUD_BROWSER_RACKSPACE_SECRET_KEY``: Account API secret key. (*Env*)
    * ``CLOUD_BROWSER_RACKSPACE_SERVICENET``: Boolean designating whether or
      not to use Rackspace's servicenet (i.e., the private interface on a
      Cloud Server). (*Env*)
    * ``CLOUD_BROWSER_RACKSPACE_AUTHURL``: Alternative authorization server,
      for use, e.g., with `OpenStack <http://www.openstack.org/>`_ instead of
      Rackspace. (*Env*)

    **Filesystem**: Configure simple filesystem mock datastore.

    * ``CLOUD_BROWSER_DATASTORE = "Filesystem"``
    * ``CLOUD_BROWSER_FILESYSTEM_ROOT``: Filesystem root to serve from.

    **View Permissions**: A standard Django view decorator object can be
    specified, which is wrapped for all browsing / viewing view -- for example,
    to limit views to logged in members, use ``login_required`` and for staff
    only, use ``staff_member_required``. Note that either a real decorator
    function or a fully-qualifid string path are acceptable, so you can use,
    e.g., "django.contrib.admin.views.decorators.staff_member_required" instead
    which might help with certain settings.py import-order-related issues.

    * ``CLOUD_BROWSER_VIEW_DECORATOR``: View decorator or fully-qualified
      string path.

    **Container Permissions**: Cloud browser allows a very rudimentary form
    of access control at the container level with white and black lists.
    If the white list is set, only container names in the white list are
    allowed. If the white list is unset, then any container name *not* in
    the black list is permitted. All name matching is exact (no regular
    expressions, etc.).

    * ``CLOUD_BROWSER_CONTAINER_WHITELIST``: White list of names. (Iterable)
    * ``CLOUD_BROWSER_CONTAINER_BLACKLIST``: Black list of names. (Iterable)

    **General**: Other settings.

    * ``CLOUD_BROWSER_DEFAULT_LIST_LIMIT``: Default number of objects to
      diplay per browser page.
    * ``CLOUD_BROWSER_STATIC_MEDIA_DIR``: If this applications static media
      (found in ``app_media``) is served up under the ``settings.MEDIA_ROOT``,
      then set a relative path from the root, and the static media will be used
      instead of a Django-based static view fallback.
    """
    #: Valid datastore types.
    DATASTORES = set((
        'AWS',
        'Google',
        'Rackspace',
        'Filesystem',
    ))

    #: Settings dictionary of accessor callables.
    SETTINGS = {
        # Datastore choice.
        'CLOUD_BROWSER_DATASTORE': \
            Setting(default='Filesystem', valid_set=DATASTORES),

        # Amazon Web Services S3 datastore settings.
        'CLOUD_BROWSER_AWS_ACCOUNT': Setting(from_env=True),
        'CLOUD_BROWSER_AWS_SECRET_KEY': Setting(from_env=True),

        # Google Storage for Developers datastore settings.
        'CLOUD_BROWSER_GS_ACCOUNT': Setting(from_env=True),
        'CLOUD_BROWSER_GS_SECRET_KEY': Setting(from_env=True),

        # Rackspace datastore settings.
        'CLOUD_BROWSER_RACKSPACE_ACCOUNT': Setting(from_env=True),
        'CLOUD_BROWSER_RACKSPACE_SECRET_KEY': Setting(from_env=True),
        'CLOUD_BROWSER_RACKSPACE_SERVICENET': BoolSetting(from_env=True),
        'CLOUD_BROWSER_RACKSPACE_AUTHURL': BoolSetting(from_env=True),

        # Filesystem datastore settings.
        'CLOUD_BROWSER_FILESYSTEM_ROOT': Setting(),

        # View permissions.
        'CLOUD_BROWSER_VIEW_DECORATOR': Setting(),

        # Permissions lists for containers.
        'CLOUD_BROWSER_CONTAINER_WHITELIST': Setting(),
        'CLOUD_BROWSER_CONTAINER_BLACKLIST': Setting(),

        # Browser settings.
        'CLOUD_BROWSER_DEFAULT_LIST_LIMIT': Setting(default=20),

        # Static media root.
        'CLOUD_BROWSER_STATIC_MEDIA_DIR': Setting(),
    }

    def __init__(self):
        """Initializer."""
        self.__container_whitelist = None
        self.__container_blacklist = None

    def __getattr__(self, name, default=None):
        """Get setting."""
        if name in self.SETTINGS:
            return self.SETTINGS[name].get(name, default)

        # Use real Django settings.
        return getattr(_settings, name, default)

    @property
    def _container_whitelist(self):
        """Container whitelist."""
        if self.__container_whitelist is None:
            self.__container_whitelist = \
                set(self.CLOUD_BROWSER_CONTAINER_WHITELIST or [])
        return self.__container_whitelist

    @property
    def _container_blacklist(self):
        """Container blacklist."""
        if self.__container_blacklist is None:
            self.__container_blacklist = \
                set(self.CLOUD_BROWSER_CONTAINER_BLACKLIST or [])
        return self.__container_blacklist

    def container_permitted(self, name):
        """Return whether or not a container is permitted.

        :param name: Container name.
        :return: ``True`` if container is permitted.
        :rtype:  ``bool``
        """
        white = self._container_whitelist
        black = self._container_blacklist
        return name not in black and (not white or name in white)

    @property
    def app_media_url(self):
        """Get application media root from real media root URL."""
        url = None
        media_dir = self.CLOUD_BROWSER_STATIC_MEDIA_DIR
        if media_dir:
            url = os.path.join(self.MEDIA_URL, media_dir).rstrip('/') + '/'

        return url

    @property
    def app_media_doc_root(self):  # pylint: disable=R0201
        """Get application media document (file) root."""
        app_dir = os.path.abspath(os.path.dirname(__file__))
        media_root = os.path.join(app_dir, 'media')

        return media_root


settings = Settings()  # pylint: disable=C0103

########NEW FILE########
__FILENAME__ = aws
"""Amazon Simple Storage Service (S3) datastore.

.. note::
    **Installation**: Use of this module requires the open source boto_
    package.

.. _boto: http://code.google.com/p/boto/
"""
from cloud_browser.cloud import boto_base as base
from cloud_browser.common import requires

###############################################################################
# Constants / Conditional Imports
###############################################################################
try:
    import boto  # pylint: disable=F0401
except ImportError:
    boto = None  # pylint: disable=C0103


###############################################################################
# Classes
###############################################################################
class AwsObject(base.BotoObject):
    """AWS 'key' object wrapper."""

    @classmethod
    @requires(boto, 'boto')
    def is_key(cls, result):
        """Return ``True`` if result is a key object."""
        from boto.s3.key import Key

        return isinstance(result, Key)

    @classmethod
    @requires(boto, 'boto')
    def is_prefix(cls, result):
        """Return ``True`` if result is a prefix object."""
        from boto.s3.prefix import Prefix

        return isinstance(result, Prefix)


class AwsContainer(base.BotoContainer):
    """AWS container wrapper."""
    #: Storage object child class.
    obj_cls = AwsObject


class AwsConnection(base.BotoConnection):
    """AWS connection wrapper."""
    #: Container child class.
    cont_cls = AwsContainer

    @base.BotoConnection.wrap_boto_errors
    @requires(boto, 'boto')
    def _get_connection(self):
        """Return native connection object."""
        return boto.connect_s3(self.account, self.secret_key)

########NEW FILE########
__FILENAME__ = base
"""Cloud datastore API base abstraction."""
import mimetypes

from cloud_browser.cloud import errors
from cloud_browser.app_settings import settings
from cloud_browser.common import SEP, \
    path_join, basename


class CloudObjectTypes(object):
    """Cloud object types helper."""
    FILE = 'file'
    SUBDIR = 'subdirectory'


class CloudObject(object):
    """Cloud object wrapper."""
    type_cls = CloudObjectTypes

    def __init__(self, container, name, **kwargs):
        """Initializer.

        :param container: Container object.
        :param name: Object name / path.
        :kwarg size: Number of bytes in object.
        :kwarg content_type: Document 'content-type'.
        :kwarg content_encoding: Document 'content-encoding'.
        :kwarg last_modified: Last modified date.
        :kwarg obj_type: Type of object (e.g., file or subdirectory).
        """
        self.container = container
        self.name = name.rstrip(SEP)
        self.size = kwargs.get('size', 0)
        self.content_type = kwargs.get('content_type', '')
        self.content_encoding = kwargs.get('content_encoding', '')
        self.last_modified = kwargs.get('last_modified', None)
        self.type = kwargs.get('obj_type', self.type_cls.FILE)
        self.__native = None

    @property
    def native_obj(self):
        """Native storage object."""
        if self.__native is None:
            self.__native = self._get_object()

        return self.__native

    def _get_object(self):
        """Return native storage object."""
        raise NotImplementedError

    @property
    def is_subdir(self):
        """Is a subdirectory?"""
        return self.type == self.type_cls.SUBDIR

    @property
    def is_file(self):
        """Is a file object?"""
        return self.type == self.type_cls.FILE

    @property
    def path(self):
        """Full path (including container)."""
        return path_join(self.container.name, self.name)

    @property
    def basename(self):
        """Base name from rightmost separator."""
        return basename(self.name)

    @property
    def smart_content_type(self):
        """Smart content type."""
        content_type = self.content_type
        if content_type in (None, '', 'application/octet-stream'):
            content_type, _ = mimetypes.guess_type(self.name)

        return content_type

    @property
    def smart_content_encoding(self):
        """Smart content encoding."""
        encoding = self.content_encoding
        if not encoding:
            base_list = self.basename.split('.')
            while (not encoding) and len(base_list) > 1:
                _, encoding = mimetypes.guess_type('.'.join(base_list))
                base_list.pop()

        return encoding

    def read(self):
        """Return contents of object."""
        return self._read()

    def _read(self):
        """Return contents of object."""
        raise NotImplementedError


class CloudContainer(object):
    """Cloud container wrapper."""
    #: Storage object child class.
    obj_cls = CloudObject

    #: Maximum number of objects that can be listed or ``None``.
    max_list = None

    def __init__(self, conn, name=None, count=None, size=None):
        """Initializer."""
        self.conn = conn
        self.name = name
        self.count = count
        self.size = size
        self.__native = None

    @property
    def native_container(self):
        """Native container object."""
        if self.__native is None:
            self.__native = self._get_container()

        return self.__native

    def _get_container(self):
        """Return native container object."""
        raise NotImplementedError

    def get_objects(self, path, marker=None,
                    limit=settings.CLOUD_BROWSER_DEFAULT_LIST_LIMIT):
        """Get objects."""
        raise NotImplementedError

    def get_object(self, path):
        """Get single object."""
        raise NotImplementedError


class CloudConnection(object):
    """Cloud connection wrapper."""
    #: Container child class.
    cont_cls = CloudContainer

    #: Maximum number of containers that can be listed or ``None``.
    max_list = None

    def __init__(self, account, secret_key):
        """Initializer."""
        self.account = account
        self.secret_key = secret_key
        self.__native = None

    @property
    def native_conn(self):
        """Native connection object."""
        if self.__native is None:
            self.__native = self._get_connection()

        return self.__native

    def _get_connection(self):
        """Return native connection object."""
        raise NotImplementedError

    def get_containers(self):
        """Return available containers."""
        permitted = lambda c: settings.container_permitted(c.name)
        return [c for c in self._get_containers() if permitted(c)]

    def _get_containers(self):
        """Return available containers."""
        raise NotImplementedError

    def get_container(self, path):
        """Return single container."""
        if not settings.container_permitted(path):
            raise errors.NotPermittedException(
                "Access to container \"%s\" is not permitted." % path)
        return self._get_container(path)

    def _get_container(self, path):
        """Return single container."""
        raise NotImplementedError

########NEW FILE########
__FILENAME__ = boto_base
"""Abstract boto-based datastore.

The boto_ library provides interfaces to both Amazon S3 and Google Storage
for Developers. This abstract base class gets most of the common work done.

.. note::
    **Installation**: Use of this module requires the open source boto_
    package.

.. _boto: http://code.google.com/p/boto/
"""
from cloud_browser.app_settings import settings
from cloud_browser.cloud import errors, base
from cloud_browser.common import SEP, requires, dt_from_header

###############################################################################
# Constants / Conditional Imports
###############################################################################
try:
    import boto  # pylint: disable=F0401
except ImportError:
    boto = None  # pylint: disable=C0103


###############################################################################
# Classes
###############################################################################
class BotoExceptionWrapper(errors.CloudExceptionWrapper):
    """Boto :mod:`boto` exception translator."""
    error_cls = errors.CloudException

    @requires(boto, 'boto')
    def translate(self, exc):
        """Return whether or not to do translation."""
        from boto.exception import StorageResponseError

        if isinstance(exc, StorageResponseError):
            if exc.status == 404:
                return self.error_cls(unicode(exc))

        return None


class BotoKeyWrapper(errors.CloudExceptionWrapper):
    """Boto :mod:`boto` key exception translator."""
    error_cls = errors.NoObjectException


class BotoBucketWrapper(errors.CloudExceptionWrapper):
    """Boto :mod:`boto` bucket exception translator."""
    error_cls = errors.NoContainerException


class BotoObject(base.CloudObject):
    """Boto 'key' object wrapper."""
    #: Exception translations.
    wrap_boto_errors = BotoKeyWrapper()

    @classmethod
    def is_key(cls, result):
        """Return ``True`` if result is a key object."""
        raise NotImplementedError

    @classmethod
    def is_prefix(cls, result):
        """Return ``True`` if result is a prefix object."""
        raise NotImplementedError

    @wrap_boto_errors
    def _get_object(self):
        """Return native storage object."""
        return self.container.native_container.get_key(self.name)

    @wrap_boto_errors
    def _read(self):
        """Return contents of object."""
        return self.native_obj.read()

    @classmethod
    def from_result(cls, container, result):
        """Create from ambiguous result."""
        if result is None:
            raise errors.NoObjectException

        elif cls.is_prefix(result):
            return cls.from_prefix(container, result)

        elif cls.is_key(result):
            return cls.from_key(container, result)

        raise errors.CloudException("Unknown boto result type: %s" %
                                    type(result))

    @classmethod
    def from_prefix(cls, container, prefix):
        """Create from prefix object."""
        if prefix is None:
            raise errors.NoObjectException

        return cls(container,
                   name=prefix.name,
                   obj_type=cls.type_cls.SUBDIR)

    @classmethod
    def from_key(cls, container, key):
        """Create from key object."""
        if key is None:
            raise errors.NoObjectException

        # Get Key   (1123): Tue, 13 Apr 2010 14:02:48 GMT
        # List Keys (8601): 2010-04-13T14:02:48.000Z
        return cls(container,
                   name=key.name,
                   size=key.size,
                   content_type=key.content_type,
                   content_encoding=key.content_encoding,
                   last_modified=dt_from_header(key.last_modified),
                   obj_type=cls.type_cls.FILE)


class BotoContainer(base.CloudContainer):
    """Boto container wrapper."""
    #: Storage object child class.
    obj_cls = BotoObject

    #: Exception translations.
    wrap_boto_errors = BotoBucketWrapper()

    #: Maximum number of objects that can be listed or ``None``.
    #:
    #: :mod:`boto` transparently pages through objects, so there is no real
    #: limit to the number of object that can be displayed.  However, for
    #: practical reasons, we'll limit it to the same as Rackspace.
    max_list = 10000

    @wrap_boto_errors
    def _get_container(self):
        """Return native container object."""
        return self.conn.native_conn.get_bucket(self.name)

    @wrap_boto_errors
    def get_objects(self, path, marker=None,
                    limit=settings.CLOUD_BROWSER_DEFAULT_LIST_LIMIT):
        """Get objects."""
        from itertools import islice

        path = path.rstrip(SEP) + SEP if path else path
        result_set = self.native_container.list(path, SEP, marker)

        # Get +1 results because marker and first item can match as we strip
        # the separator from results obscuring things. No real problem here
        # because boto masks any real request limits.
        results = list(islice(result_set, limit+1))
        if results:
            if marker and results[0].name.rstrip(SEP) == marker.rstrip(SEP):
                results = results[1:]
            else:
                results = results[:limit]

        return [self.obj_cls.from_result(self, r) for r in results]

    @wrap_boto_errors
    def get_object(self, path):
        """Get single object."""
        key = self.native_container.get_key(path)
        return self.obj_cls.from_key(self, key)

    @classmethod
    def from_bucket(cls, connection, bucket):
        """Create from bucket object."""
        if bucket is None:
            raise errors.NoContainerException

        # It appears that Amazon does not have a single-shot REST query to
        # determine the number of keys / overall byte size of a bucket.
        return cls(connection, bucket.name)


class BotoConnection(base.CloudConnection):
    """Boto connection wrapper."""
    #: Container child class.
    cont_cls = BotoContainer

    #: Exception translations.
    wrap_boto_errors = BotoBucketWrapper()

    def _get_connection(self):
        """Return native connection object."""
        raise NotImplementedError("Must create boto connection.")

    @wrap_boto_errors
    def _get_containers(self):
        """Return available containers."""
        buckets = self.native_conn.get_all_buckets()
        return [self.cont_cls.from_bucket(self, b) for b in buckets]

    @wrap_boto_errors
    def _get_container(self, path):
        """Return single container."""
        bucket = self.native_conn.get_bucket(path)
        return self.cont_cls.from_bucket(self, bucket)

########NEW FILE########
__FILENAME__ = config
"""Cloud configuration."""


class Config(object):
    """General class helper to construct connection objects."""
    __connection_obj = None
    __connection_cls = None
    __connection_fn = None

    @classmethod
    def from_settings(cls):
        """Create configuration from Django settings or environment."""
        from cloud_browser.app_settings import settings
        from django.core.exceptions import ImproperlyConfigured

        conn_cls = conn_fn = None
        datastore = settings.CLOUD_BROWSER_DATASTORE
        if datastore == 'AWS':
            # Try AWS
            from cloud_browser.cloud.aws import AwsConnection
            account = settings.CLOUD_BROWSER_AWS_ACCOUNT
            secret_key = settings.CLOUD_BROWSER_AWS_SECRET_KEY
            if account and secret_key:
                conn_cls = AwsConnection
                conn_fn = lambda: AwsConnection(account, secret_key)

        if datastore == 'Google':
            # Try Google Storage
            from cloud_browser.cloud.google import GsConnection
            account = settings.CLOUD_BROWSER_GS_ACCOUNT
            secret_key = settings.CLOUD_BROWSER_GS_SECRET_KEY
            if account and secret_key:
                conn_cls = GsConnection
                conn_fn = lambda: GsConnection(account, secret_key)

        elif datastore == 'Rackspace':
            # Try Rackspace
            account = settings.CLOUD_BROWSER_RACKSPACE_ACCOUNT
            secret_key = settings.CLOUD_BROWSER_RACKSPACE_SECRET_KEY
            servicenet = settings.CLOUD_BROWSER_RACKSPACE_SERVICENET
            authurl = settings.CLOUD_BROWSER_RACKSPACE_AUTHURL
            if account and secret_key:
                from cloud_browser.cloud.rackspace import RackspaceConnection
                conn_cls = RackspaceConnection
                conn_fn = lambda: RackspaceConnection(
                    account,
                    secret_key,
                    servicenet=servicenet,
                    authurl=authurl)

        elif datastore == 'Filesystem':
            # Mock filesystem
            root = settings.CLOUD_BROWSER_FILESYSTEM_ROOT
            if root is not None:
                from cloud_browser.cloud.fs import FilesystemConnection
                conn_cls = FilesystemConnection
                conn_fn = lambda: FilesystemConnection(root)

        if conn_cls is None:
            raise ImproperlyConfigured(
                "No suitable credentials found for datastore: %s." %
                datastore)

        # Adjust connection function.
        conn_fn = staticmethod(conn_fn)

        # Directly cache attributes.
        cls.__connection_cls = conn_cls
        cls.__connection_fn = conn_fn

        return conn_cls, conn_fn

    @classmethod
    def get_connection_cls(cls):
        """Return connection class.

        :rtype: :class:`type`
        """
        if cls.__connection_cls is None:
            cls.__connection_cls, _ = cls.from_settings()
        return cls.__connection_cls

    @classmethod
    def get_connection(cls):
        """Return connection object.

        :rtype: :class:`cloud_browser.cloud.base.CloudConnection`
        """
        if cls.__connection_obj is None:
            if cls.__connection_fn is None:
                _, cls.__connection_fn = cls.from_settings()
            cls.__connection_obj = cls.__connection_fn()
        return cls.__connection_obj

########NEW FILE########
__FILENAME__ = errors
"""Common cloud error wrappers."""
import sys

from functools import wraps


class CloudException(Exception):
    """Base cloud exception."""
    pass


class InvalidNameException(CloudException):
    """Bad name."""
    pass


class NotPermittedException(CloudException):
    """Access is not permitted"""
    pass


class NoContainerException(CloudException):
    """No container found."""
    pass


class NoObjectException(CloudException):
    """No storage object found."""
    pass


class CloudExceptionWrapper(object):
    """Exception translator.

    This class wraps a "real" underlying cloud class exception and translates
    it to a "common" exception class from this module. The exception stack
    from the wrapped exception is preserved through some :meth:`sys.exc_info`
    hackery.

    It is implemented as a decorator such that you can do something like::

        class MyWrapper(CloudExceptionWrapper):
            '''Convert exception to another one.'''
            translations = { Exception: NotImplementedError }

        @MyWrapper()
        def foo():
            raise Exception("Hi.")

        foo()

    The alternate way is to handle the translations directly in a member
    function::

        class MyWrapper(CloudExceptionWrapper):
            '''Convert exception to another one.'''
            def translate(self, exc):
                if isinstance(exc, Exception):
                    return NotImplementedError

                return None

        @MyWrapper()
        def foo():
            raise Exception("Hi.")

        foo()

    which produces output like::

        Traceback (most recent call last):
          File "...", line ..., in <module>
            foo()
          File "...", line ..., in wrapped
            return operation(*args, **kwargs)
          File "...", line ..., in foo
            raise Exception("Hi.")
        NotImplementedError: Hi.

    So, we can see that we get a different exception with the proper stack.

    Overriding classes should implement the ``translations`` class variable
    dictionary for translating an underlying library exception to a class
    in this module. See any of the data implementation modules for examples.
    """
    translations = {}
    _excepts = None

    def __new__(cls, *args, **kwargs):
        """New."""
        obj = object.__new__(cls, *args, **kwargs)

        # Patch in lazy translations.
        if not obj.translations:
            lazy_translations = cls.lazy_translations()
            if lazy_translations:
                obj.translations = lazy_translations

        return obj

    @classmethod
    def excepts(cls):
        """Return tuple of underlying exception classes to trap and wrap.

        :rtype: ``tuple`` of ``type``
        """
        if cls._excepts is None:
            cls._excepts = tuple(cls.translations.keys())
        return cls._excepts

    def translate(self, exc):
        """Return translation of exception to new class.

        Calling code should only raise exception if exception class is passed
        in, else ``None`` (which signifies no wrapping should be done).
        """
        # Find actual class.
        for key in self.translations.keys():
            if isinstance(exc, key):
                return self.translations[key](unicode(exc))

        return None

    def __call__(self, operation):
        """Call and wrap exceptions."""

        @wraps(operation)
        def wrapped(*args, **kwargs):
            """Wrapped function."""

            try:
                return operation(*args, **kwargs)
            except self.excepts(), exc:
                new_exc = self.translate(exc)
                if new_exc:
                    # Wrap and raise with stack intact.
                    raise new_exc.__class__, new_exc, sys.exc_info()[2]
                else:
                    raise

        return wrapped

    @classmethod
    def lazy_translations(cls):
        """Lazy translations definitions (for additional checks)."""
        return None

########NEW FILE########
__FILENAME__ = fs
"""File-system datastore."""
from __future__ import with_statement

import os
import re

from cloud_browser.app_settings import settings
from cloud_browser.cloud import errors, base
from cloud_browser.common import SEP


###############################################################################
# Helpers / Constants
###############################################################################
NO_DOT_RE = re.compile("^[^.]+")


def not_dot(path):
    """Check if non-dot."""
    return NO_DOT_RE.match(os.path.basename(path))


def is_dir(path):
    """Check if non-dot and directory."""
    return not_dot(path) and os.path.isdir(path)


###############################################################################
# Classes
###############################################################################
class FilesystemContainerWrapper(errors.CloudExceptionWrapper):
    """Exception translator."""
    translations = {
        OSError: errors.NoContainerException,
    }
wrap_fs_cont_errors = FilesystemContainerWrapper()  # pylint: disable=C0103


class FilesystemObjectWrapper(errors.CloudExceptionWrapper):
    """Exception translator."""
    translations = {
        OSError: errors.NoObjectException,
    }
wrap_fs_obj_errors = FilesystemObjectWrapper()  # pylint: disable=C0103


class FilesystemObject(base.CloudObject):
    """Filesystem object wrapper."""

    def _get_object(self):
        """Return native storage object."""
        return object()

    def _read(self):
        """Return contents of object."""
        with open(self.base_path, 'rb') as file_obj:
            return file_obj.read()

    @property
    def base_path(self):
        """Base absolute path of container."""
        return os.path.join(self.container.base_path, self.name)

    @classmethod
    def from_path(cls, container, path):
        """Create object from path."""
        from datetime import datetime

        path = path.strip(SEP)
        full_path = os.path.join(container.base_path, path)
        last_modified = datetime.fromtimestamp(os.path.getmtime(full_path))
        obj_type = cls.type_cls.SUBDIR if is_dir(full_path)\
            else cls.type_cls.FILE

        return cls(container,
                   name=path,
                   size=os.path.getsize(full_path),
                   content_type=None,
                   last_modified=last_modified,
                   obj_type=obj_type)


class FilesystemContainer(base.CloudContainer):
    """Filesystem container wrapper."""
    #: Storage object child class.
    obj_cls = FilesystemObject

    def _get_container(self):
        """Return native container object."""
        return object()

    @wrap_fs_obj_errors
    def get_objects(self, path, marker=None,
                    limit=settings.CLOUD_BROWSER_DEFAULT_LIST_LIMIT):
        """Get objects."""
        def _filter(name):
            """Filter."""
            return (not_dot(name) and
                    (marker is None or
                     os.path.join(path, name).strip(SEP) > marker.strip(SEP)))

        search_path = os.path.join(self.base_path, path)
        objs = [self.obj_cls.from_path(self, os.path.join(path, o))
                for o in os.listdir(search_path) if _filter(o)]
        objs = sorted(objs, key=lambda x: x.base_path)
        return objs[:limit]

    @wrap_fs_obj_errors
    def get_object(self, path):
        """Get single object."""
        return self.obj_cls.from_path(self, path)

    @property
    def base_path(self):
        """Base absolute path of container."""
        return os.path.join(self.conn.abs_root, self.name)

    @classmethod
    def from_path(cls, conn, path):
        """Create container from path."""
        path = path.strip(SEP)
        full_path = os.path.join(conn.abs_root, path)
        return cls(conn, path, 0, os.path.getsize(full_path))


class FilesystemConnection(base.CloudConnection):
    """Filesystem connection wrapper."""
    #: Container child class.
    cont_cls = FilesystemContainer

    def __init__(self, root):
        """Initializer."""
        super(FilesystemConnection, self).__init__(None, None)
        self.root = root
        self.abs_root = os.path.abspath(root)

    def _get_connection(self):
        """Return native connection object."""
        return object()

    @wrap_fs_cont_errors
    def _get_containers(self):
        """Return available containers."""
        full_fn = lambda p: os.path.join(self.abs_root, p)
        return [self.cont_cls.from_path(self, d)
                for d in os.listdir(self.abs_root) if is_dir(full_fn(d))]

    @wrap_fs_cont_errors
    def _get_container(self, path):
        """Return single container."""
        path = path.strip(SEP)
        if SEP in path:
            raise errors.InvalidNameException(
                "Path contains %s - %s" % (SEP, path))
        return self.cont_cls.from_path(self, path)

########NEW FILE########
__FILENAME__ = google
"""Google Storage for Developers datastore.

`Google Storage for Developers`_ (GS) is cosmetically an implementation of the
S3 interface by Google.

.. note::
    **Installation**: Use of this module requires the open source boto_
    package. Not sure exactly which version installed GS support, but we'll
    validate the version if it becomes an issue.

.. _`Google Storage for Developers`: http://code.google.com/apis/storage/
.. _boto: http://code.google.com/p/boto/
"""
from cloud_browser.app_settings import settings
from cloud_browser.cloud import boto_base as base
from cloud_browser.common import SEP, requires

###############################################################################
# Constants / Conditional Imports
###############################################################################
try:
    import boto  # pylint: disable=F0401
except ImportError:
    boto = None  # pylint: disable=C0103


###############################################################################
# Classes
###############################################################################
class GsObject(base.BotoObject):
    """Google Storage 'key' object wrapper."""

    _gs_folder_suffix = "_$folder$"

    @classmethod
    def _is_gs_folder(cls, result):
        """Return ``True`` if GS standalone folder object.

        GS will create a 0 byte ``<FOLDER NAME>_$folder$`` key as a
        pseudo-directory place holder if there are no files present.
        """
        return (cls.is_key(result) and
                result.size == 0 and
                result.name.endswith(cls._gs_folder_suffix))

    @classmethod
    @requires(boto, 'boto')
    def is_key(cls, result):
        """Return ``True`` if result is a key object."""
        from boto.gs.key import Key

        return isinstance(result, Key)

    @classmethod
    @requires(boto, 'boto')
    def is_prefix(cls, result):
        """Return ``True`` if result is a prefix object.

        .. note::
            Boto uses the S3 Prefix object for GS prefixes.
        """
        from boto.s3.prefix import Prefix

        return isinstance(result, Prefix) or cls._is_gs_folder(result)

    @classmethod
    def from_prefix(cls, container, prefix):
        """Create from prefix object."""
        if (cls._is_gs_folder(prefix)):
            name, suffix, extra = prefix.name.partition(cls._gs_folder_suffix)
            if (suffix, extra) == (cls._gs_folder_suffix, ''):
                # Patch GS specific folder to remove suffix.
                prefix.name = name

        return super(GsObject, cls).from_prefix(container, prefix)


class GsContainer(base.BotoContainer):
    """Google Storage container wrapper."""
    #: Storage object child class.
    obj_cls = GsObject

    def get_objects(self, path, marker=None,
                    limit=settings.CLOUD_BROWSER_DEFAULT_LIST_LIMIT):
        """Get objects.

        Certain upload clients may add a 0-byte object (e.g., ``FOLDER`` object
        for path ``path/to/FOLDER`` - ``path/to/FOLDER/FOLDER``). We add an
        extra +1 limit query and ignore any such file objects.
        """
        # Get basename of implied folder.
        folder = path.split(SEP)[-1]

        # Query extra objects, then strip 0-byte dummy object if present.
        objs = super(GsContainer, self).get_objects(path, marker, limit+1)
        objs = [o for o in objs if not (o.size == 0 and o.name == folder)]

        return objs[:limit]


class GsConnection(base.BotoConnection):
    """Google Storage connection wrapper."""
    #: Container child class.
    cont_cls = GsContainer

    @base.BotoConnection.wrap_boto_errors
    @requires(boto, 'boto')
    def _get_connection(self):
        """Return native connection object."""
        return boto.connect_gs(self.account, self.secret_key)

########NEW FILE########
__FILENAME__ = rackspace
"""Rackspace Cloud Files datastore.

.. note::
    **Installation**: Use of this module requires the Rackspace
    cloudfiles_ package, and at least version 1.7.4 (which introduced the
    ``delimiter`` container query support).

.. _cloudfiles: https://github.com/rackspace/python-cloudfiles
"""
from cloud_browser.app_settings import settings
from cloud_browser.cloud import errors, base
from cloud_browser.common import SEP, check_version, requires, dt_from_header

###############################################################################
# Constants / Conditional Imports
###############################################################################
# 1.7.4 introduced the ``path`` parameter for ``list_objects_info``.
RS_MIN_CLOUDFILES_VERSION = (1, 7, 4)

# Current Rackspace maximum number of objects/containers for listing.
RS_MAX_LIST_OBJECTS_LIMIT = 10000
RS_MAX_LIST_CONTAINERS_LIMIT = 10000

try:
    import cloudfiles  # pylint: disable=F0401
    check_version(cloudfiles, RS_MIN_CLOUDFILES_VERSION)
except ImportError:
    cloudfiles = None  # pylint: disable=C0103


###############################################################################
# Classes
###############################################################################
class RackspaceExceptionWrapper(errors.CloudExceptionWrapper):
    """Rackspace :mod:`cloudfiles` exception translator."""

    @classmethod
    @requires(cloudfiles, 'cloudfiles')
    def lazy_translations(cls):
        """Lazy translations."""
        return  {
            cloudfiles.errors.NoSuchContainer: errors.NoContainerException,
            cloudfiles.errors.NoSuchObject: errors.NoObjectException,
        }


class RackspaceObject(base.CloudObject):
    """Cloud object wrapper."""
    #: Exception translations.
    wrap_rs_errors = RackspaceExceptionWrapper()

    #: Subdirectory content types.
    #: Rackspace has "special" content types that should be interpreted as
    #: pseudo-directory delimiters from "old style" hierarchy detection.
    subdir_types = set((
        "application/directory",
        "application/folder",
    ))

    @wrap_rs_errors
    def _get_object(self):
        """Return native storage object."""
        return self.container.native_container.get_object(self.name)

    @wrap_rs_errors
    def _read(self):
        """Return contents of object."""
        return self.native_obj.read()

    @classmethod
    def from_info(cls, container, info_obj):
        """Create from subdirectory or file info object."""
        create_fn = cls.from_subdir if 'subdir' in info_obj \
            else cls.from_file_info
        return create_fn(container, info_obj)

    @classmethod
    def from_subdir(cls, container, info_obj):
        """Create from subdirectory info object."""
        return cls(container,
                   info_obj['subdir'],
                   obj_type=cls.type_cls.SUBDIR)

    @classmethod
    def choose_type(cls, content_type):
        """Choose object type from content type."""
        return cls.type_cls.SUBDIR if content_type in cls.subdir_types \
            else cls.type_cls.FILE

    @classmethod
    def from_file_info(cls, container, info_obj):
        """Create from regular info object."""
        # RFC 8601: 2010-04-15T01:52:13.919070
        return cls(container,
                   name=info_obj['name'],
                   size=info_obj['bytes'],
                   content_type=info_obj['content_type'],
                   last_modified=dt_from_header(info_obj['last_modified']),
                   obj_type=cls.choose_type(info_obj['content_type']))

    @classmethod
    def from_obj(cls, container, file_obj):
        """Create from regular info object."""
        # RFC 1123: Thu, 07 Jun 2007 18:57:07 GMT
        return cls(container,
                   name=file_obj.name,
                   size=file_obj.size,
                   content_type=file_obj.content_type,
                   last_modified=dt_from_header(file_obj.last_modified),
                   obj_type=cls.choose_type(file_obj.content_type))


class RackspaceContainer(base.CloudContainer):
    """Rackspace container wrapper."""
    #: Storage object child class.
    obj_cls = RackspaceObject

    #: Exception translations.
    wrap_rs_errors = RackspaceExceptionWrapper()

    #: Maximum number of objects that can be listed or ``None``.
    #:
    #: Enforced Rackspace maximums. We need a lower max. to be enforced on
    #: the input end because under the hood, we can try subsequent larger
    #: queries if we have marker or psuedo/dummy directory clashes.
    #:
    #: Specifically, we need to add one to the query to detect a
    #: pseudo-directory matching the marker, and double the limit for a
    #: follow-on query if we have both dummy and pseudo-directory objects
    #: in results.
    max_list = (RS_MAX_LIST_OBJECTS_LIMIT - 1) / 2

    @wrap_rs_errors
    def _get_container(self):
        """Return native container object."""
        return self.conn.native_conn.get_container(self.name)

    @wrap_rs_errors
    def get_objects(self, path, marker=None,
                    limit=settings.CLOUD_BROWSER_DEFAULT_LIST_LIMIT):
        """Get objects.

        **Pseudo-directory Notes**: Rackspace has two approaches to pseudo-
        directories within the (really) flat storage object namespace:

          1. Dummy directory storage objects. These are real storage objects
             of type "application/directory" and must be manually uploaded
             by the client.
          2. Implied subdirectories using the `path` API query parameter.

        Both serve the same purpose, but the latter is much preferred because
        there is no independent maintenance of extra dummy objects, and the
        `path` approach is always correct (for the existing storage objects).

        This package uses the latter `path` approach, but gets into an
        ambiguous situation where there is both a dummy directory storage
        object and an implied subdirectory. To remedy this situation, we only
        show information for the dummy directory object in results if present,
        and ignore the implied subdirectory. But, under the hood this means
        that our `limit` parameter may end up with less than the desired
        number of objects. So, we use the heuristic that if we **do** have
        "application/directory" objects, we end up doing an extra query of
        double the limit size to ensure we can get up to the limit amount
        of objects. This double query approach is inefficient, but as
        using dummy objects should now be deprecated, the second query should
        only rarely occur.

        """
        object_infos, full_query = self._get_object_infos(path, marker, limit)
        if full_query and len(object_infos) < limit:
            # The underlying query returned a full result set, but we
            # truncated it to under limit. Re-run at twice the limit and then
            # slice back.
            object_infos, _ = self._get_object_infos(path, marker, 2*limit)
            object_infos = object_infos[:limit]

        return [self.obj_cls.from_info(self, x) for x in object_infos]

    @wrap_rs_errors
    def _get_object_infos(self, path, marker=None,
                          limit=settings.CLOUD_BROWSER_DEFAULT_LIST_LIMIT):
        """Get raw object infos (single-shot)."""
        # Adjust limit to +1 to handle marker object as first result.
        # We can get in to this situation for a marker of "foo", that will
        # still return a 'subdir' object of "foo/" because of the extra
        # slash.
        orig_limit = limit
        limit += 1

        # Enforce maximum object size.
        if limit > RS_MAX_LIST_OBJECTS_LIMIT:
            raise errors.CloudException("Object limit must be less than %s" %
                                        RS_MAX_LIST_OBJECTS_LIMIT)

        def _collapse(infos):
            """Remove duplicate dummy / implied objects."""
            name = None
            for info in infos:
                name = info.get('name', name)
                subdir = info.get('subdir', '').strip(SEP)
                if not name or subdir != name:
                    yield info

        path = path + SEP if path else ''
        object_infos = self.native_container.list_objects_info(
            limit=limit, delimiter=SEP, prefix=path, marker=marker)

        full_query = len(object_infos) == limit
        if object_infos:
            # Check first object for marker match and truncate if so.
            if marker and \
                object_infos[0].get('subdir', '').strip(SEP) == marker:
                object_infos = object_infos[1:]

            # Collapse subdirs and dummy objects.
            object_infos = list(_collapse(object_infos))

            # Adjust to original limit.
            if len(object_infos) > orig_limit:
                object_infos = object_infos[:orig_limit]

        return object_infos, full_query

    @wrap_rs_errors
    def get_object(self, path):
        """Get single object."""
        obj = self.native_container.get_object(path)
        return self.obj_cls.from_obj(self, obj)


class RackspaceConnection(base.CloudConnection):
    """Rackspace connection wrapper."""
    #: Container child class.
    cont_cls = RackspaceContainer

    #: Exception translations.
    wrap_rs_errors = RackspaceExceptionWrapper()

    #: Maximum number of containers that can be listed or ``None``.
    max_list = RS_MAX_LIST_CONTAINERS_LIMIT

    def __init__(self, account, secret_key, servicenet=False, authurl=None):
        """Initializer."""
        super(RackspaceConnection, self).__init__(account, secret_key)
        self.servicenet = servicenet
        self.authurl = authurl

    @wrap_rs_errors
    @requires(cloudfiles, 'cloudfiles')
    def _get_connection(self):
        """Return native connection object."""
        kwargs = {
            'username': self.account,
            'api_key': self.secret_key,
        }

        # Only add kwarg for servicenet if True because user could set
        # environment variable 'RACKSPACE_SERVICENET' separately.
        if self.servicenet:
            kwargs['servicenet'] = True

        if self.authurl:
            kwargs['authurl'] = self.authurl

        return cloudfiles.get_connection(**kwargs)  # pylint: disable=W0142

    @wrap_rs_errors
    def _get_containers(self):
        """Return available containers."""
        infos = self.native_conn.list_containers_info()
        return [self.cont_cls(self, i['name'], i['count'], i['bytes'])
                for i in infos]

    @wrap_rs_errors
    def _get_container(self, path):
        """Return single container."""
        cont = self.native_conn.get_container(path)
        return self.cont_cls(self,
                             cont.name,
                             cont.object_count,
                             cont.size_used)

########NEW FILE########
__FILENAME__ = common
"""Common operations.

Because cloud operations are OS agnostic, we don't use any of :mod:`os` or
:mod:`os.path`.
"""
from datetime import datetime
from django.core.exceptions import ImproperlyConfigured


###############################################################################
# Constants.
###############################################################################
# File-like constants.
#: Browser file path separator.
SEP = "/"
#: Parent path phrase.
PARENT = ".."


###############################################################################
# General.
###############################################################################
def get_int(value, default, test_fn=None):
    """Convert value to integer.

    :param value: Integer value.
    :param default: Default value on failed conversion.
    :param test_fn: Constraint function. Use default if returns ``False``.
    :return: Integer value.
    :rtype:  ``int``
    """
    try:
        converted = int(value)
    except ValueError:
        return default

    test_fn = test_fn if test_fn else lambda x: True
    return converted if test_fn(converted) else default


def check_version(mod, required):
    """Require minimum version of module using ``__version__`` member."""
    vers = tuple(int(v) for v in mod.__version__.split('.')[:3])
    if vers < required:
        req = '.'.join(str(v) for v in required)
        raise ImproperlyConfigured(
            "Module \"%s\" version (%s) must be >= %s." %
            (mod.__name__, mod.__version__, req))


def requires(module, name=""):
    """Enforces module presence.

    The general use here is to allow conditional imports that may fail (e.g., a
    required python package is not installed) but still allow the rest of the
    python package to compile and run fine. If the wrapped method with this
    decorated is invoked, then a runtime error is generated.

    :param module: required module (set as variable to ``None`` on import fail)
    :type  module: ``module`` or ``None``
    :param name: module name
    :type  name: ``string``
    """
    def wrapped(method):
        """Call and enforce method."""
        if module is None:
            raise ImproperlyConfigured("Module '%s' is not installed." % name)
        return method

    return wrapped


###############################################################################
# Date / Time.
###############################################################################
def dt_from_rfc8601(date_str):
    """Convert 8601 (ISO) date string to datetime object.

    Handles "Z" and milliseconds transparently.

    :param date_str: Date string.
    :type  date_str: ``string``
    :return: Date time.
    :rtype:  :class:`datetime.datetime`
    """
    # Normalize string and adjust for milliseconds. Note that Python 2.6+ has
    # ".%f" format, but we're going for Python 2.5, so truncate the portion.
    date_str = date_str.rstrip('Z').split('.')[0]

    # Format string. (2010-04-13T14:02:48.000Z)
    fmt = "%Y-%m-%dT%H:%M:%S"
    # Python 2.6+: Could format and handle milliseconds.
    #if date_str.find('.') >= 0:
    #    fmt += ".%f"

    return datetime.strptime(date_str, fmt)


def dt_from_rfc1123(date_str):
    """Convert 1123 (HTTP header) date string to datetime object.

    :param date_str: Date string.
    :type  date_str: ``string``
    :return: Date time.
    :rtype:  :class:`datetime.datetime`
    """
    fmt = "%a, %d %b %Y %H:%M:%S GMT"
    return datetime.strptime(date_str, fmt)


def dt_from_header(date_str):
    """Try various RFC conversions to ``datetime`` or return ``None``.

    :param date_str: Date string.
    :type  date_str: ``string``
    :return: Date time.
    :rtype:  :class:`datetime.datetime` or ``None``
    """
    convert_fns = (
        dt_from_rfc8601,
        dt_from_rfc1123,
    )

    for convert_fn in convert_fns:
        try:
            return convert_fn(date_str)
        except ValueError:
            pass

    return None


###############################################################################
# Path helpers.
###############################################################################
def basename(path):
    """Rightmost part of path after separator."""
    base_path = path.strip(SEP)
    sep_ind = base_path.rfind(SEP)
    if sep_ind < 0:
        return path

    return base_path[sep_ind+1:]


def path_parts(path):
    """Split path into container, object.

    :param path: Path to resource (including container).
    :type  path: `string`
    :return: Container, storage object tuple.
    :rtype:  `tuple` of `string`, `string`
    """
    path = path if path is not None else ''
    container_path = object_path = ''
    parts = path_list(path)

    if len(parts) > 0:
        container_path = parts[0]
    if len(parts) > 1:
        object_path = path_join(*parts[1:])

    return container_path, object_path


def path_yield(path):
    """Yield on all path parts."""
    for part in (x for x in path.strip(SEP).split(SEP) if x not in (None, '')):
        yield part


def path_list(path):
    """Return list of path parts."""
    return list(path_yield(path))


def path_join(*args):
    """Join path parts to single path."""
    return SEP.join((x for x in args if x not in (None, ''))).strip(SEP)


def relpath(path, start):
    """Get relative path to start.

    Note: Modeled after python2.6 :meth:`os.path.relpath`.
    """
    path_items = path_list(path)
    start_items = path_list(start)

    # Find common parts of path.
    common = []
    for pth, stt in zip(path_items, start_items):
        if pth != stt:
            break
        common.append(pth)

    # Shared parts index in both lists.
    common_ind = len(common)
    parent_num = len(start_items) - common_ind

    # Start with parent traversal and add relative parts.
    rel_items = [PARENT] * parent_num + path_items[common_ind:]
    return path_join(*rel_items)  # pylint: disable=W0142

########NEW FILE########
__FILENAME__ = errors
"""Cloud browser errors.

All cloud browser errors are sub-classed off the base
:class:`CloudBrowserException` error.
"""


class CloudBrowserException(Exception):
    """Base class for all exceptions."""
    pass

########NEW FILE########
__FILENAME__ = models
"""Cloud browser models."""

########NEW FILE########
__FILENAME__ = cloud_browser_extras
"""Cloud browser template tags."""
import os

from django import template
from django.template import TemplateSyntaxError, Node
from django.template.defaultfilters import stringfilter

from cloud_browser.app_settings import settings

register = template.Library()  # pylint: disable=C0103


@register.filter
@stringfilter
def truncatechars(value, num, end_text="..."):
    """Truncate string on character boundary.

    .. note::
        Django ticket `5025 <http://code.djangoproject.com/ticket/5025>`_ has a
        patch for a more extensible and robust truncate characters tag filter.

    Example::

        {{ my_variable|truncatechars:22 }}

    :param value: Value to truncate.
    :type  value: ``string``
    :param num: Number of characters to trim to.
    :type  num: ``int``
    """
    length = None
    try:
        length = int(num)
    except ValueError:
        pass

    if length is not None and len(value) > length:
        return value[:length-len(end_text)] + end_text

    return value
truncatechars.is_safe = True  # pylint: disable=W0612


@register.tag
def cloud_browser_media_url(_, token):
    """Get base media URL for application static media.

    Correctly handles whether or not the settings variable
    ``CLOUD_BROWSER_STATIC_MEDIA_DIR`` is set and served.

    For example::

        <link rel="stylesheet" type="text/css"
            href="{% cloud_browser_media_url "css/cloud-browser.css" %}" />
    """
    bits = token.split_contents()
    if len(bits) != 2:
        raise TemplateSyntaxError("'%s' takes one argument" % bits[0])
    rel_path = bits[1]

    return MediaUrlNode(rel_path)


class MediaUrlNode(Node):
    """Media URL node."""

    #: Static application media URL (or ``None``).
    static_media_url = settings.app_media_url

    def __init__(self, rel_path):
        """Initializer."""
        super(MediaUrlNode, self).__init__()
        self.rel_path = rel_path.lstrip('/').strip("'").strip('"')

    def render(self, context):
        """Render."""
        from django.core.urlresolvers import reverse

        # Check if we have real or Django static-served media
        if self.static_media_url is not None:
            # Real.
            return os.path.join(self.static_media_url, self.rel_path)

        else:
            # Django.
            return reverse("cloud_browser_media",
                           args=[self.rel_path],
                           current_app='cloud_browser')

########NEW FILE########
__FILENAME__ = tests
"""Cloud browser tests."""

########NEW FILE########
__FILENAME__ = urls
"""Cloud browser URLs."""
from django.conf.urls.defaults import patterns, url
from django.views.generic.simple import redirect_to

from cloud_browser.app_settings import settings

urlpatterns = patterns('cloud_browser.views',  # pylint: disable=C0103
    url(r'^$', redirect_to, name="cloud_browser_index",
        kwargs={'url': 'browser'}),
    url(r'^browser/(?P<path>.*)$', 'browser', name="cloud_browser_browser"),
    url(r'^document/(?P<path>.*)$', 'document', name="cloud_browser_document"),
)

if settings.app_media_url is None:
    # Use a static serve.
    urlpatterns += patterns('',  # pylint: disable=C0103
        url(r'^app_media/(?P<path>.*)$', 'django.views.static.serve',
            {'document_root': settings.app_media_doc_root},
            name="cloud_browser_media"),
    )

########NEW FILE########
__FILENAME__ = urls_admin
"""Cloud browser URLs for Django admin integration."""
from django.conf.urls.defaults import patterns, url
from django.views.generic.simple import redirect_to

from cloud_browser.app_settings import settings

urlpatterns = patterns('cloud_browser.views',  # pylint: disable=C0103
    url(r'^$', redirect_to, name="cloud_browser_index",
        kwargs={'url': 'browser'}),
    url(r'^browser/(?P<path>.*)$', 'browser', name="cloud_browser_browser",
        kwargs={'template': "cloud_browser/admin/browser.html"}),
    url(r'^document/(?P<path>.*)$', 'document', name="cloud_browser_document"),
)

if settings.app_media_url is None:
    # Use a static serve.
    urlpatterns += patterns('',  # pylint: disable=C0103
        url(r'^app_media/(?P<path>.*)$', 'django.views.static.serve',
            {'document_root': settings.app_media_doc_root},
            name="cloud_browser_media"),
    )

########NEW FILE########
__FILENAME__ = views
"""Cloud browser views."""
from django.http import HttpResponse, Http404
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.utils.importlib import import_module

from cloud_browser.app_settings import settings
from cloud_browser.cloud import get_connection, get_connection_cls, errors
from cloud_browser.common import get_int, \
    path_parts, path_join, path_yield, relpath


MAX_LIMIT = get_connection_cls().cont_cls.max_list


def settings_view_decorator(function):
    """Insert decorator from settings, if any.

    .. note:: Decorator in ``CLOUD_BROWSER_VIEW_DECORATOR`` can be either a
        callable or a fully-qualified string path (the latter, which we'll
        lazy import).
    """

    dec = settings.CLOUD_BROWSER_VIEW_DECORATOR

    # Trade-up string to real decorator.
    if isinstance(dec, basestring):
        # Split into module and decorator strings.
        mod_str, _, dec_str = dec.rpartition('.')
        if not (mod_str and dec_str):
            raise ImportError("Unable to import module: %s" % mod_str)

        # Import and try to get decorator function.
        mod = import_module(mod_str)
        if not hasattr(mod, dec_str):
            raise ImportError("Unable to import decorator: %s" % dec)

        dec = getattr(mod, dec_str)

    if dec and callable(dec):
        return dec(function)

    return function


def _breadcrumbs(path):
    """Return breadcrumb dict from path."""

    full = None
    crumbs = []
    for part in path_yield(path):
        full = path_join(full, part) if full else part
        crumbs.append((full, part))

    return crumbs


@settings_view_decorator
def browser(request, path='', template="cloud_browser/browser.html"):
    """View files in a file path.

    :param request: The request.
    :param path: Path to resource, including container as first part of path.
    :param template: Template to render.
    """
    from itertools import ifilter, islice

    # Inputs.
    container_path, object_path = path_parts(path)
    incoming = request.POST or request.GET or {}

    marker = incoming.get('marker', None)
    marker_part = incoming.get('marker_part', None)
    if marker_part:
        marker = path_join(object_path, marker_part)

    # Get and adjust listing limit.
    limit_default = settings.CLOUD_BROWSER_DEFAULT_LIST_LIMIT
    limit_test = lambda x: x > 0 and (MAX_LIMIT is None or x <= MAX_LIMIT - 1)
    limit = get_int(incoming.get('limit', limit_default),
                    limit_default,
                    limit_test)

    # Q1: Get all containers.
    #     We optimize here by not individually looking up containers later,
    #     instead going through this in-memory list.
    # TODO: Should page listed containers with a ``limit`` and ``marker``.
    conn = get_connection()
    containers = conn.get_containers()

    marker_part = None
    container = None
    objects = None
    if container_path != '':
        # Find marked container from list.
        cont_eq = lambda c: c.name == container_path
        cont_list = list(islice(ifilter(cont_eq, containers), 1))
        if not cont_list:
            raise Http404("No container at: %s" % container_path)

        # Q2: Get objects for instant list, plus one to check "next".
        container = cont_list[0]
        objects = container.get_objects(object_path, marker, limit+1)
        marker = None

        # If over limit, strip last item and set marker.
        if len(objects) == limit + 1:
            objects = objects[:limit]
            marker = objects[-1].name
            marker_part = relpath(marker, object_path)

    return render_to_response(template,
                              {'path': path,
                               'marker': marker,
                               'marker_part': marker_part,
                               'limit': limit,
                               'breadcrumbs': _breadcrumbs(path),
                               'container_path': container_path,
                               'containers': containers,
                               'container': container,
                               'object_path': object_path,
                               'objects': objects},
                              context_instance=RequestContext(request))


@settings_view_decorator
def document(_, path=''):
    """View single document from path.

    :param path: Path to resource, including container as first part of path.
    """
    container_path, object_path = path_parts(path)
    conn = get_connection()
    try:
        container = conn.get_container(container_path)
    except errors.NoContainerException:
        raise Http404("No container at: %s" % container_path)
    except errors.NotPermittedException:
        raise Http404("Access denied for container at: %s" % container_path)

    try:
        storage_obj = container.get_object(object_path)
    except errors.NoObjectException:
        raise Http404("No object at: %s" % object_path)

    # Get content-type and encoding.
    content_type = storage_obj.smart_content_type
    encoding = storage_obj.smart_content_encoding
    response = HttpResponse(content=storage_obj.read(),
                            content_type=content_type)
    if encoding not in (None, ''):
        response['Content-Encoding'] = encoding

    return response

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
from django.core.management import execute_manager
try:
    import cloud_browser_project.settings as settings
except ImportError:
    import sys
    sys.stderr.write(
      "Error: Can't find the file 'settings.py' in the directory containing "
      "%r. It appears you've customized things.\nYou'll have to run "
      "django-admin.py, passing it your settings module.\n(If the file "
      "settings.py does indeed exist, it's causing an ImportError somehow.)\n"
      % __file__)
    sys.exit(1)

if __name__ == "__main__":
    execute_manager(settings)

########NEW FILE########
__FILENAME__ = settings
# Django settings for cloud_browser project.
import os

# Current project path
PROJECT_PATH = os.path.abspath(os.path.dirname(__file__))

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(PROJECT_PATH, 'db/dev.sqlite3'),
        'USER': '',
        'PASSWORD': '',
        'HOST': '',
        'PORT': '',
    }
}

TIME_ZONE = 'America/Chicago'

LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale
USE_L10N = True

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = os.path.join(PROJECT_PATH, 'media')

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = '/static_media/'

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/media/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = '(4bum1ge3nl_dm(&+3e!4^xozw3yl3m=ik#!-@)vp=#oxn@))y'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
)

ROOT_URLCONF = 'cloud_browser_project.urls'

TEMPLATE_DIRS = (
    os.path.join(PROJECT_PATH, "templates"),
)

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'cloud_browser',
)

# EXAMPLE: Serve up the "/usr/share" directory.
CLOUD_BROWSER_DATASTORE = "Filesystem"
CLOUD_BROWSER_FILESYSTEM_ROOT = "/usr/share/doc"

########NEW FILE########
__FILENAME__ = urls
from django.conf import settings
from django.conf.urls.defaults import patterns, url, include
from django.conf.urls.defaults import (  # pylint: disable=W0611
    handler404, handler500)
from django.contrib import admin
from django.views.generic.simple import redirect_to

# Enable admin.
admin.autodiscover()

ADMIN_URLS = False
urlpatterns = patterns('')  # pylint: disable=C0103

if ADMIN_URLS:
    urlpatterns += patterns('',
        # Admin URLs. Note: Include ``urls_admin`` **before** admin.
        url(r'^$', redirect_to, name='index', kwargs={'url': 'admin/'}),
        url(r'^admin/cb/', include('cloud_browser.urls_admin')),
    )

else:
    urlpatterns += patterns('',
        # Normal URLs.
        url(r'^$', redirect_to, name='index', kwargs={'url': 'cb/'}),
        url(r'^cb/', include('cloud_browser.urls')),
    )

urlpatterns += patterns('',
    # Hack in the bare minimum to get accounts support.
    url(r'^admin/', include(admin.site.urls)),
    url(r'^accounts/', include('django.contrib.auth.urls')),
    url(r'^accounts/$', redirect_to, kwargs={'url': 'login'}),
    url(r'^accounts/profile', redirect_to, kwargs={'url': '/'}),
)

if settings.DEBUG:
    # Serve up static media.
    urlpatterns += patterns('',
        url(r'^' + settings.MEDIA_URL.strip('/') + '/(?P<path>.*)$',
            'django.views.static.serve',
            {'document_root': settings.MEDIA_ROOT}),
    )

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# Cloud Browser documentation build configuration file, created by
# sphinx-quickstart on Tue Jan 18 22:53:44 2011.
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
sys.path.insert(0, os.path.abspath('..'))
import cloud_browser
import sphinx_bootstrap_theme

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.coverage']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'Cloud Browser'
copyright = u'2011, Ryan Roemer'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = cloud_browser.__version__
# The full version, including alpha/beta/rc tags.
release = cloud_browser.__version_full__

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
exclude_patterns = ['_build']

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

# Activate the theme.
# sys.path.append(os.path.abspath('_themes'))
# html_theme_path = ['_themes']
html_theme_path = sphinx_bootstrap_theme.get_html_theme_path()
html_theme = 'bootstrap'

# (Optional) Use a shorter name to conserve nav. bar space.
html_short_title = "Cloud Browser"

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#html_theme = 'nature'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
html_theme_options = {
    'source_link_position': "footer",
    'globaltoc_depth': 2,
    #'bootswatch_theme': "cerulean",
}

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
#html_static_path = ['_static']

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
htmlhelp_basename = 'CloudBrowserdoc'


# -- Options for LaTeX output --------------------------------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'CloudBrowser.tex', u'Cloud Browser Documentation',
   u'Ryan Roemer', 'manual'),
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
    ('index', 'cloud_browser', u'Cloud Browser Documentation',
     [u'Ryan Roemer'], 1)
]

########NEW FILE########
__FILENAME__ = fabfile
"""Fabric file."""
from __future__ import with_statement

import os
import urllib

from contextlib import contextmanager
from fabric.api import abort, local, settings


###############################################################################
# Constants
###############################################################################
MOD = "cloud_browser"
PROJ = "cloud_browser_project"
PROJ_SETTINGS = ".".join((PROJ, "settings"))

DEV_DB_DIR = os.path.join(PROJ, "db")

CHECK_INCLUDES = (
    "fabfile.py",
    "setup.py",
    MOD,
    PROJ,
)
PEP8_IGNORES = ('E225',)
PYLINT_CFG = "dev/pylint.cfg"

DOC_INPUT = "doc"
DOC_OUTPUT = "doc_html"
DOC_UNDERSCORE_DIRS = (
    "sources",
    "static",
)

BUILD_DIRS = (
    "dist",
    "django_cloud_browser.egg-info",
)

SDIST_RST_FILES = (
    "INSTALL.rst",
    "README.rst",
    "CHANGES.rst",
)
SDIST_TXT_FILES = [os.path.splitext(x)[0] + ".txt" for x in SDIST_RST_FILES]


###############################################################################
# Build
###############################################################################
def clean():
    """Clean build files."""
    for build_dir in list(BUILD_DIRS) + [DOC_OUTPUT, DEV_DB_DIR]:
        local("rm -rf %s" % build_dir)


@contextmanager
def _dist_wrapper():
    """Add temporary distribution build files (and then clean up)."""
    try:
        # Copy select *.rst files to *.txt for build.
        for rst_file, txt_file in zip(SDIST_RST_FILES, SDIST_TXT_FILES):
            local("cp %s %s" % (rst_file, txt_file))

        # Perform action.
        yield
    finally:
        # Clean up temp *.txt files.
        for rst_file in SDIST_TXT_FILES:
            local("rm -f %s" % rst_file, capture=False)


def sdist():
    """Package into distribution."""
    with _dist_wrapper():
        local("python setup.py sdist", capture=False)


def register():
    """Register and prep user for PyPi upload.

    .. note:: May need to weak ~/.pypirc file per issue:
        http://stackoverflow.com/questions/1569315
    """
    with _dist_wrapper():
        local("python setup.py register", capture=False)


def upload():
    """Upload package."""
    with _dist_wrapper():
        local("python setup.py sdist upload", capture=False)


###############################################################################
# Quality
###############################################################################
def pylint(rcfile=PYLINT_CFG):
    """Run pylint style checker.

    :param rcfile: PyLint configuration file.
    """
    # Have a spurious DeprecationWarning in pylint.
    local(
        "python -W ignore::DeprecationWarning `which pylint` --rcfile=%s %s" %
        (rcfile, " ".join(CHECK_INCLUDES)), capture=False)


def pep8():
    """Run pep8 style checker."""
    includes = "-r %s" % " ".join(CHECK_INCLUDES)
    ignores = "--ignore=%s" % ",".join(PEP8_IGNORES) if PEP8_IGNORES else ''
    with settings(warn_only=True):
        results = local("pep8 %s %s" % (includes, ignores), capture=True)
    errors = results.strip() if results else None
    if errors:
        print(errors)
        abort("PEP8 failed.")


def check():
    """Run all checkers."""
    pep8()
    pylint()


###############################################################################
# Documentation
###############################################################################
def _parse_bool(value):
    """Convert ``string`` or ``bool`` to ``bool``."""
    if isinstance(value, bool):
        return value

    elif isinstance(value, basestring):
        if value == 'True':
            return True
        elif value == 'False':
            return False

    raise Exception("Value %s is not boolean." % value)


def docs(output=DOC_OUTPUT, proj_settings=PROJ_SETTINGS, github=False):
    """Generate API documentation (using Sphinx).

    :param output: Output directory.
    :param proj_settings: Django project settings to use.
    :param github: Convert to GitHub-friendly format?
    """

    local("export PYTHONPATH='' && "
          "export DJANGO_SETTINGS_MODULE=%s && "
          "sphinx-build -b html %s %s" % (proj_settings, DOC_INPUT, output),
          capture=False)

    if _parse_bool(github):
        local("touch %s/.nojekyll" % output, capture=False)


###############################################################################
# Django Targets
###############################################################################
def _manage(target, extra='', proj_settings=PROJ_SETTINGS):
    """Generic wrapper for ``django-admin.py``."""
    local("export PYTHONPATH='' && "
          "export DJANGO_SETTINGS_MODULE='%s' && "
          "django-admin.py %s %s" %
          (proj_settings, target, extra),
          capture=False)


def syncdb(proj_settings=PROJ_SETTINGS):
    """Run syncdb."""
    local("mkdir -p %s" % DEV_DB_DIR)
    _manage("syncdb", proj_settings=proj_settings)


def run_server(addr="127.0.0.1:8000", proj_settings=PROJ_SETTINGS):
    """Run Django dev. server."""
    _manage("runserver", addr, proj_settings)

########NEW FILE########
