__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# ptah documentation build configuration file
#
# This file is execfile()d with the current directory set to its containing
# dir.
#
# The contents of this file are pickled, so don't put values in the
# namespace that aren't pickleable (module imports are okay, they're
# removed automatically).
#
# All configuration values have a default value; values that are commented
# out serve to show the default value.


# General configuration
# ---------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.intersphinx',
              'sphinx.ext.autodoc']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['.templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The master toctree document.
master_doc = 'index'

# General substitutions.
project = 'ptah'

# The default replacements for |version| and |release|, also used in various
# other places throughout the built documents.
#
# The short X.Y version.
version = '0.3'
# The full version, including alpha/beta/rc tags.
release = version

# There are two options for replacing |today|: either, you set today to
# some non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
today_fmt = '%B %d, %Y'

# List of documents that shouldn't be included in the build.
#unused_docs = ['_themes/README']

# List of directories, relative to source directories, that shouldn't be
# searched for source files.
#exclude_dirs = []

# The reST default role (used for this markup: `text`) to use for all
# documents.
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


# Options for HTML output
# -----------------------

#sys.path.append(os.path.abspath('_themes'))
#html_theme_path = ['_themes']
#html_theme = 'pylons'

# The style sheet to use for HTML and HTML Help pages. A file of that name
# must exist either in Sphinx' static/ path, or in one of the custom paths
# given in html_static_path.
#html_style = 'pylons.css'

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
#html_title = None

# A shorter title for the navigation bar.  Default is the same as
# html_title.
#html_short_title = None

# The name of an image file (within the static path) to place at the top of
# the sidebar.
#html_logo = '.static/logo_hi.gif'

# The name of an image file (within the static path) to use as favicon of
# the docs.  This file should be a Windows icon file (.ico) being 16x16 or
# 32x32 pixels large.
#html_favicon = None

# Add any paths that contain custom static files (such as style sheets)
# here, relative to this directory. They are copied after the builtin
# static files, so a file named "default.css" will overwrite the builtin
# "default.css".
#html_static_path = ['.static']

# If not '', a 'Last updated on:' timestamp is inserted at every page
# bottom, using the given strftime format.
html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
#html_use_smartypants = True

# Custom sidebar templates, maps document names to template names.
#html_sidebars = {}

# Additional templates that should be rendered to pages, maps page names to
# template names.
#html_additional_pages = {}

# If false, no module index is generated.
#html_use_modindex = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, the reST sources are included in the HTML build as
# _sources/<name>.
#html_copy_source = True

# If true, an OpenSearch description file will be output, and all pages
# will contain a <link> tag referring to it.  The value of this option must
# be the base URL from which the finished HTML is served.
#html_use_opensearch = ''

# If nonempty, this is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = ''

# Output file base name for HTML help builder.
htmlhelp_basename = 'atemplatedoc'


# Options for LaTeX output
# ------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title,
#  author, document class [howto/manual]).
latex_documents = [
  ('index', 'atemplate.tex', 'Ptah Framework Documentation',
   'Developers', 'manual'),
]

# The name of an image file (relative to this directory) to place at the
# top of the title page.
latex_logo = '.static/logo_hi.gif'

# For "manual" documents, if this is true, then toplevel headings are
# parts, not chapters.
#latex_use_parts = False

# Additional stuff for the LaTeX preamble.
#latex_preamble = ''

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_use_modindex = True

#autoclass_content = 'both'

########NEW FILE########
__FILENAME__ = authentication
from pyramid.security import authenticated_userid
from pyramid.threadlocal import get_current_request

from ptah import config
from ptah.uri import resolve, resolver
from ptah.util import tldata


class _Superuser(object):
    """ Default ptah superuser. check_permission always pass with superuser """

    def __init__(self):
        self.__uri__ = 'ptah-auth:superuser'
        self.login = ''
        self.name = 'Manager'

    def __repr__(self):
        return '<ptah Superuser>'


SUPERUSER = _Superuser()
SUPERUSER_URI = 'ptah-auth:superuser'


@resolver('ptah-auth')
def superuser_resolver(uri):
    """System super user"""
    if uri == SUPERUSER_URI:
        return SUPERUSER


AUTH_CHECKER_ID = 'ptah:authchecker'
AUTH_PROVIDER_ID = 'ptah:authprovider'
AUTH_SEARCHER_ID = 'ptah:authsearcher'


def auth_checker(checker, __cfg=None, __depth=1):
    """Register authentication checker. Checker function accepts
    :py:class:`ptah.authentication.AuthInfo` object.

    :param checker: Checker function.

    Checker function interface :py:func:`ptah.interfaces.auth_checker`

    .. code-block:: python

      @ptah.auth_checker
      def my_checker(info):
          ...

    """
    info = config.DirectiveInfo(__depth)
    discr = (AUTH_CHECKER_ID, hash(checker))
    intr = config.Introspectable(
        AUTH_CHECKER_ID, discr, checker.__name__, 'ptah-authchecker')
    intr['name'] = '{0}.{1}'.format(info.codeinfo.module, checker.__name__)
    intr['callable'] = checker
    intr['codeinfo'] = info.codeinfo

    info.attach(
        config.Action(
            lambda config, checker: config.get_cfg_storage(AUTH_CHECKER_ID)\
                .update({id(checker): checker}),
            (checker,), discriminator=discr, introspectables=(intr,)),
        __cfg)
    return checker


def pyramid_auth_checker(cfg, checker):
    """ Pyramid configurator directive for authentication
    checker registration.

    :param checker: Checker function

    Checker function interface :py:func:`ptah.interfaces.auth_checker`

    .. code-block:: python

      config = Configurator()
      config.include('ptah')

      def my_checker(info):
          ...

      config.ptah_auth_checker(my_checker)
    """
    auth_checker(checker, cfg, 3)


class auth_provider(object):
    """ Register authentication provider.
    Auth provider interface :py:class:`ptah.interfaces.AuthProvider`

    :param name: provider name

    .. code-block:: python

      @ptah.auth_provider('my-provider')
      class AuthProvider(object):
           ...

    """
    def __init__(self, name, __depth=1):
        self.depth = __depth
        self.info = config.DirectiveInfo(__depth)

        self.discr = (AUTH_PROVIDER_ID, name)
        self.intr = config.Introspectable(
            AUTH_PROVIDER_ID, self.discr, name, 'ptah-authprovider')
        self.intr['id'] = name
        self.intr['codeinfo'] = self.info.codeinfo

    def __call__(self, cls, __cfg=None):
        self.intr['provider'] = cls
        self.intr['name'] = '{0}.{1}'.format(
            self.info.codeinfo.module, cls.__name__)

        self.info.attach(
            config.Action(
                lambda config, n, p: config.get_cfg_storage(AUTH_PROVIDER_ID)\
                    .update({n: cls()}),
                (self.intr['name'], cls),
                discriminator=self.discr, introspectables=(self.intr,)),
            __cfg, self.depth)
        return cls

    @classmethod
    def register(cls, name, provider):
        """ authentication provider registration::

        .. code-block:: python

          class AuthProvider(object):
             ...

          ptah.auth_provider.register('my-provider', AuthProvider)

        """
        cls(name, 2)(provider)

    @classmethod
    def pyramid(cls, cfg, name, provider):
        """ ``ptah_auth_provider`` directive implementation """
        cls(name, 3)(provider, cfg)


class AuthInfo(object):
    """ Authentication information """

    #: Principal uri or None if principal is not set
    __uri__ = None

    #: Principal object
    principal = None

    #: Status, True is principal has been authenticated, false otherwise
    status = False

    #: Extra message from auth checkers
    message = False

    def __init__(self, principal, status=False, message=''):
        self.__uri__ = getattr(principal, '__uri__', None)
        self.principal = principal
        self.status = status
        self.message = message
        self.arguments = {}


_not_set = object()

USER_KEY = '__ptah_userid__'
EFFECTIVE_USER_KEY = '__ptah_effective__userid__'


class Authentication(object):
    """ Ptah authentication utility """

    def authenticate(self, credentials):
        """Authenticate credentials.

        :param credentials: Dictionary with `login` and `password`
        :rtype: :py:class:`ptah.authentication.AuthInfo`
        """
        providers = config.get_cfg_storage(AUTH_PROVIDER_ID)
        for pname, provider in providers.items():
            principal = provider.authenticate(credentials)
            if principal is not None:
                info = AuthInfo(principal)

                for checker in \
                        config.get_cfg_storage(AUTH_CHECKER_ID).values():
                    if not checker(info):
                        return info

                info.status = True
                return info

        return AuthInfo(None)

    def authenticate_principal(self, principal):
        """Authenticate principal, check principal with
        auth checkers

        :param principal: Principal object
        :rtype: :py:class:`ptah.authentication.AuthInfo`
        """
        info = AuthInfo(principal)

        for checker in \
                config.get_cfg_storage(AUTH_CHECKER_ID).values():
            if not checker(info):
                return info

        info.status = True
        return info

    def set_userid(self, uri):
        """ Set current user id """
        tldata.set(USER_KEY, uri)

    def get_userid(self):
        """ Get current user id. By default it uses
        ``pyramid.security.authenticated_userid``"""
        uri = tldata.get(USER_KEY, _not_set)
        if uri is _not_set:
            self.set_userid(authenticated_userid(get_current_request()))
            return tldata.get(USER_KEY)
        return uri

    def set_effective_userid(self, uri):
        """ Set effective user uri """
        tldata.set(EFFECTIVE_USER_KEY, uri)

    def get_effective_userid(self):
        """ Return effective user uri, of current user uri. """
        uri = tldata.get(EFFECTIVE_USER_KEY, _not_set)
        if uri is _not_set:
            return self.get_userid()
        return uri

    def get_current_principal(self):
        """ Resolve and return current user uri """
        return resolve(self.get_userid())

    def get_principal_bylogin(self, login):
        """ Return principal by login """
        providers = config.get_cfg_storage(AUTH_PROVIDER_ID)

        for pname, provider in providers.items():
            principal = provider.get_principal_bylogin(login)
            if principal is not None:
                return principal

    def get_principal_byemail(self, email):
        """ Return principal by email """
        providers = config.get_cfg_storage(AUTH_PROVIDER_ID)

        for pname, provider in providers.items():
            principal = provider.get_principal_byemail(email)
            if principal is not None:
                return principal

auth_service = Authentication()


def search_principals(term):
    """ Search principals by term, it uses principal_searcher functions """
    searchers = config.get_cfg_storage(AUTH_SEARCHER_ID)
    for name, searcher in searchers.items():
        for principal in searcher(term):
            yield principal


class principal_searcher(object):
    """ Register principal searcher function.

    Searcher function interface :py:func:`ptah.interfaces.principal_searcher`

    .. code-block:: python

      @ptah.principal_searcher('test')
      def searcher(term):
           ...

    searcher function receives text as term variable, and
    should return iterator to principal objects.
    """
    def __init__(self, name, __depth=1):
        self.depth = __depth
        self.info = config.DirectiveInfo(__depth)

        self.discr = (AUTH_SEARCHER_ID, name)
        self.intr = config.Introspectable(
            AUTH_SEARCHER_ID, self.discr, name, AUTH_SEARCHER_ID)
        self.intr['name'] = name

    def __call__(self, searcher, cfg=None):
        self.intr['callable'] = searcher

        self.info.attach(
            config.Action(
                lambda config, name, searcher:
                    config.get_cfg_storage(AUTH_SEARCHER_ID)\
                        .update({name: searcher}),
                (self.intr['name'], searcher),
                discriminator=self.discr, introspectables=(self.intr,)),
            cfg, self.depth)

        return searcher

    @classmethod
    def register(cls, name, searcher):
        """ register principal searcher:

        .. code-block:: python

          def searcher(term):
              ...

          ptah.principal_searcher.register('test', searcher)

        """
        cls(name, 2)(searcher)

    @classmethod
    def pyramid(cls, cfg, name, searcher):
        """ pyramid configurator directive for
        principal searcher registration """
        cls(name, 3)(searcher, cfg)

########NEW FILE########
__FILENAME__ = config
import sys
import logging
import signal
import traceback
from collections import defaultdict, namedtuple, OrderedDict
from pyramid.compat import NativeIO
from pyramid.registry import Introspectable
from pyramid.threadlocal import get_current_registry

import venusian
from venusian.advice import getFrameInfo

ATTACH_ATTR = '__ptah_actions__'
ID_SUBSCRIBER = 'ptah:subscriber'

__all__ = ('initialize', 'get_cfg_storage', 'StopException',
           'event', 'subscriber', 'shutdown', 'shutdown_handler',
           'Action', 'DirectiveInfo')

log = logging.getLogger('ptah')


class StopException(Exception):
    """ Special initialization exception means stop execution """

    def __init__(self, exc=None):
        self.exc = exc
        if isinstance(exc, BaseException):
            self.isexc = True
            self.exc_type, self.exc_value, self.exc_traceback = sys.exc_info()
        else:
            self.isexc = False

    def __str__(self):
        return ('\n{0}'.format(self.print_tb()))

    def print_tb(self):
        if self.isexc and self.exc_value:
            out = NativeIO()
            traceback.print_exception(
                self.exc_type, self.exc_value, self.exc_traceback, file=out)
            return out.getvalue()
        else:
            return self.exc


class ObjectEventNotify(object):

    def __init__(self, registry):
        self.registry = registry

    def __call__(self, event):
        self.registry.subscribers((event.object, event), None)


def get_cfg_storage(id, registry=None, default_factory=OrderedDict):
    """ Return current config storage """
    if registry is None:
        registry = get_current_registry()

    try:
        storage = registry.__ptah_storage__
    except AttributeError:
        storage = defaultdict(lambda: OrderedDict())
        registry.__ptah_storage__ = storage

    if id not in storage:
        storage[id] = default_factory()
    return storage[id]


def pyramid_get_cfg_storage(config, id):
    return get_cfg_storage(id, config.registry)


def subscriber(*args):
    """ Register event subscriber. """
    info = DirectiveInfo(allowed_scope=('module', 'function call'))

    def wrapper(func):
        required = tuple(args)
        discr = (ID_SUBSCRIBER, func, required)

        intr = Introspectable(
            ID_SUBSCRIBER, discr, 'Subscriber', 'ptah-subscriber')
        intr['required'] = required
        intr['handler'] = func
        intr['codeinfo'] = info.codeinfo

        def _register(cfg, func, required):
            cfg.registry.registerHandler(func, required)

        info.attach(
            Action(
                _register, (func, required),
                discriminator=discr, introspectables=(intr,))
            )
        return func

    return wrapper


class Action(object):

    hash = None

    def __init__(self, callable, args=(), kw={},
                 discriminator=None, order=0, introspectables=(), info=None):
        self.callable = callable
        self.args = args
        self.kw = kw
        self.order = order
        self.info = info
        self.introspectables = introspectables
        self.discriminator = discriminator

    def __hash__(self):
        return hash(self.hash)

    def __repr__(self):
        return '<%s "%s">'%(
            self.__class__.__name__,
            self.discriminator[0] if self.discriminator else None)

    def __call__(self, cfg):
        if self.callable:
            try:
                self.callable(cfg, *self.args, **self.kw)
            except:  # pragma: no cover
                log.exception(self.discriminator)
                raise


CodeInfo = namedtuple('Codeinfo', 'filename lineno function source module')


class AttachData(OrderedDict):
    """ container for Attach infos """


class DirectiveInfo(object):

    def __init__(self, depth=1, moduleLevel=False, allowed_scope=None):
        scope, module, f_locals, f_globals, codeinfo = \
            getFrameInfo(sys._getframe(depth + 1))

        if allowed_scope and scope not in allowed_scope: # pragma: no cover
            raise TypeError("This directive is not allowed "
                            "to run in this scope: %s" % scope)

        if scope == 'module':
            self.name = f_locals['__name__']
        else:
            self.name = codeinfo[2]

        self.locals = f_locals
        self.scope = scope
        self.module = module
        self.codeinfo = CodeInfo(
            codeinfo[0], codeinfo[1], codeinfo[2], codeinfo[3], module.__name__)

        if depth > 1:
            _, mod, _, _, ci = getFrameInfo(sys._getframe(2))
            self.hash = (module.__name__, codeinfo[1], mod.__name__, ci[1])
        else:
            self.hash = (module.__name__, codeinfo[1])

    @property
    def context(self): # pragma: no cover
        if self.scope == 'module':
            return self.module
        else:
            return getattr(self.module, self.name, None)

    def _runaction(self, action, cfg):
        cfg.__ptah_action__ = action
        action(cfg)

    def attach(self, action, cfg=None, depth=1):
        action.info = self
        if action.hash is None:
            action.hash = self.hash

        data = getattr(self.module, ATTACH_ATTR, None)
        if data is None:
            data = AttachData()
            setattr(self.module, ATTACH_ATTR, data)

        if cfg is None and action.hash in data:
            raise TypeError(
                "Directive registered twice: %s" % (action.discriminator,))
        data[action.hash] = action

        def callback(context, name, ob):
            config = context.config.with_package(self.module)

            config.info = action.info
            config.action(
                action.discriminator, self._runaction, (action, config),
                introspectables=action.introspectables,
                order=action.order)

        if cfg is not None:
            cfg.action(
                action.discriminator,
                self._runaction, (action, cfg),
                introspectables=action.introspectables, order=action.order)
        else:
            venusian.attach(data, callback, category='ptah', depth=depth+1)

    def __repr__(self):
        filename, line, function, source, module = self.codeinfo
        return ' File "%s", line %d, in %s\n' \
               '      %s\n' % (filename, line, function, source)


handlers = []
_handler_int = signal.getsignal(signal.SIGINT)
_handler_term = signal.getsignal(signal.SIGTERM)


def shutdown_handler(handler):
    """ register shutdown handler """
    handlers.append(handler)
    return handler


def shutdown():
    """ Execute all registered shutdown handlers """
    for handler in handlers:
        try:
            handler()
        except:
            log.exception("Showndown handler: %s"%handler)
            pass


def process_shutdown(sig, frame):
    """ os signal handler """
    shutdown()

    if sig == signal.SIGINT and callable(_handler_int):
        _handler_int(sig, frame)

    if sig == signal.SIGTERM and callable(_handler_term):  # pragma: no cover
        _handler_term(sig, frame)

    if sig == signal.SIGTERM:
        raise sys.exit()


def install_sigterm_handler(): # pragma: no cover
    try:
        import mod_wsgi
    except ImportError:
        signal.signal(signal.SIGINT, process_shutdown)
        signal.signal(signal.SIGTERM, process_shutdown)

########NEW FILE########
__FILENAME__ = events
from ptah import config
from zope.interface.interfaces import ObjectEvent


class event(object):
    """ Register event object, it is used for introspection only. """

    ID_EVENT = 'ptah.config:event'

    #: Event name
    name = ''

    #: Event title
    title = ''

    #: Event category
    category = ''

    #: Event class or interface
    factory = None

    def __init__(self, title='', category=''):
        self.title = title
        self.category = category

        self.info = config.DirectiveInfo()

    def __call__(self, cls):
        self.factory = cls
        self.description = cls.__doc__
        self.name = '{0}.{1}'.format(cls.__module__, cls.__name__)

        discr = (self.ID_EVENT, self.name)
        intr = config.Introspectable(
            self.ID_EVENT, discr, self.title, 'ptah-event')
        intr['ev'] = self
        intr['name'] = self.name
        intr['codeinfo'] = self.info.codeinfo

        def _event(cfg, desc, intr):
            storage = cfg.get_cfg_storage(self.ID_EVENT)
            storage[desc.name] = desc
            storage[desc.factory] = desc

        self.info.attach(
            config.Action(_event, (self, intr),
                          discriminator=discr, introspectables=(intr,))
            )
        return cls


# settings related events

@event('Settings initializing event')
class SettingsInitializing(object):
    """ Settings initializing event """

    config = None
    registry = None

    def __init__(self, config, registry):
        self.config = config
        self.registry = registry


@event('Settings initialized event')
class SettingsInitialized(object):
    """ ptah sends this event when settings initialization is completed. """

    config = None
    registry = None

    def __init__(self, config, registry):
        self.config = config
        self.registry = registry


@event('Settings group modified event')
class SettingsGroupModified(object):
    """ ptah sends this event when settings group is modified. """

    def __init__(self, group):
        self.object = group


# uri events

@event('Uri invalidate event')
class UriInvalidateEvent(object):
    """ Uri object has been changed. """

    def __init__(self, uri):
        self.uri = uri


# principal events

class PrincipalEvent(object):
    """ base class for all principal related events """

    principal = None  # IPrincipal object

    def __init__(self, principal):  # pragma: no cover
        self.principal = principal


@event('Logged in event')
class LoggedInEvent(PrincipalEvent):
    """ User logged in to system."""


@event('Login failed event')
class LoginFailedEvent(PrincipalEvent):
    """ User login failed."""

    message = ''

    def __init__(self, principal, message=''):  # pragma: no cover
        self.principal = principal
        self.message = message


@event('Logged out event')
class LoggedOutEvent(PrincipalEvent):
    """ User logged out."""


@event('Reset password initiated event')
class ResetPasswordInitiatedEvent(PrincipalEvent):
    """ User has initiated password changeing."""


@event('User password has been changed')
class PrincipalPasswordChangedEvent(PrincipalEvent):
    """ User password has been changed. """


@event('Account validation event')
class PrincipalValidatedEvent(PrincipalEvent):
    """ Principal account has been validated."""


@event('Principal added event')
class PrincipalAddedEvent(PrincipalEvent):
    """ Principal added event """


@event('Principal registered event')
class PrincipalRegisteredEvent(PrincipalEvent):
    """ Principal registered event """


@event('Principal modified event')
class PrincipalModifiedEvent(PrincipalEvent):
    """ Principal modified event """


@event('Principal deleting event')
class PrincipalDeletingEvent(PrincipalEvent):
    """ Principal deleting event """


# content events

class ContentEvent(ObjectEvent):
    """ Base content event """

    object = None


@event('Content created event')
class ContentCreatedEvent(ContentEvent):
    """ :py:class:`ptah.TypeInformation` will send event during create().
    """


@event('Content added event')
class ContentAddedEvent(ContentEvent):
    """ :py:class:`ptahcms.Container` will send event when content has been
        created through containers __setitem__ method.
    """


@event('Content moved event')
class ContentMovedEvent(ContentEvent):
    """ :py:class:`ptahcms.Container` will send event when content has moved.
    """


@event('Content modified event')
class ContentModifiedEvent(ContentEvent):
    """ :py:class:`ptahcms.Content` will send event during update().
    """


@event('Content deleting event')
class ContentDeletingEvent(ContentEvent):
    """ :py:class:`ptahcms.Container` will send event before content has been
        deleted through containers __delitem__ method.
    """


# db schema creation
class BeforeCreateDbSchema(object):
    """ :py:data:`ptah.POPULATE_DB_SCHEMA` populate step sends event before
    tables have been created.

    ``registry``: Pyramid registry object
    """

    def __init__(self, registry):
        self.registry = registry

########NEW FILE########
__FILENAME__ = formatter
""" formatters """
import pytz
import translationstring
from datetime import datetime, timedelta
from pyramid.i18n import get_localizer
from pyramid.compat import text_type
from babel.dates import format_date, format_time

import ptah

_ = translationstring.TranslationStringFactory('ptah')

def date_formatter(request, value, **kwargs):
    """Date formatters
    """
    if not isinstance(value, datetime):
        return value

    if value.tzinfo is None:
        value = value.replace(tzinfo=pytz.utc)

    return text_type(format_date(value, **kwargs))


def time_formatter(request, value, **kwargs):
    """Time formatters
    """
    if not isinstance(value, datetime):
        return value

    if value.tzinfo is None:
        value = value.replace(tzinfo=pytz.utc)

    return text_type(format_time(value, **kwargs))


def datetime_formatter(request, value, tp='medium'):
    """DateTime formatter

    Short::

      >> dt = datetime(2011, 2, 6, 10, 35, 45, 80, pytz.UTC)

      >> request.fmt.datetime(dt, 'short')
      '02/06/11 04:35 AM'


    Medium::

      >> request.fmt.datetime(dt, 'medium')
      'Feb 06, 2011 04:35 AM'

    Long::

      >> request.fmt.datetime(dt, 'long')
      'February 06, 2011 04:35 AM -0600'

    Full::

      >> request.fmt.datetime(dt, 'full')
      'Sunday, February 06, 2011 04:35:45 AM CST'

    """
    if not isinstance(value, datetime):
        return value

    FORMAT = ptah.get_settings('format', request.registry)

    tz = FORMAT['timezone']
    if value.tzinfo is None:
        value = datetime(value.year, value.month, value.day, value.hour,
                         value.minute, value.second, value.microsecond,
                         pytz.utc)

    value = value.astimezone(tz)

    format = '%s %s' % (FORMAT['date_%s' % tp], FORMAT['time_%s' % tp])
    return text_type(value.strftime(str(format)))


def timedelta_formatter(request, value, type='short'):
    """Timedelta formatter

    Full format::

      >> td = timedelta(hours=10, minutes=5, seconds=45)
      >> request.fmt.timedelta(td, 'full')
      '10 hour(s) 5 min(s) 45 sec(s)'

    Seconds::

      >> request.fmt.timedelta(td, 'seconds')
      '36345.0000'


    Default::

      >> request.fmt.timedelta(td)
      '10:05:45'

    """
    if not isinstance(value, timedelta):
        return value

    if type == 'full':
        hours = value.seconds // 3600
        hs = hours * 3600
        mins = (value.seconds - hs) // 60
        ms = mins * 60
        secs = value.seconds - hs - ms
        frm = []
        translate = get_localizer(request).translate

        if hours:
            frm.append(translate(
                '${hours} hour(s)', 'ptah.view', {'hours': hours}))
        if mins:
            frm.append(translate(
                '${mins} min(s)', 'ptah.view', {'mins': mins}))
        if secs:
            frm.append(translate(
                '${secs} sec(s)', 'ptah.view', {'secs': secs}))

        return ' '.join(frm)

    elif type == 'medium':
        return str(value)

    elif type == 'seconds':
        s = value.seconds + value.microseconds / 1000000.0
        return '%2.4f' % s

    else:
        return str(value).split('.')[0]


_size_types = {
    'b': (1.0, 'B'),
    'k': (1024.0, 'KB'),
    'm': (1024.0*1024.0, 'MB'),
    'g': (1024.0*1024.0*1024.0, 'GB'),
}

def size_formatter(request, value, type='k'):
    """Size formatter

    bytes::

        >> v = 1024
        >> request.fmt.size(v, 'b')
        '1024 B'

    kylobytes::

        >> requst.fmt.size(v, 'k')
        '1.00 KB'

    megabytes::

        >> request.fmt.size(1024*768, 'm')
        '0.75 MB'

        >> request.fmt.size(1024*768*768, 'm')
        '576.00 MB'

    terabytes::

        >> request.fmt.size(1024*768*768, 'g')
        '0.56 GB'

    """
    if not isinstance(value, (int, float)):
        return value

    f, t = _size_types.get(type, (1024.0, 'KB'))

    if t == 'B':
        return '%.0f %s' % (value / f, t)

    return '%.2f %s' % (value / f, t)

########NEW FILE########
__FILENAME__ = interfaces
""" interfaces """
import translationstring
from zope import interface
from pyramid.httpexceptions import HTTPForbidden, HTTPNotFound

_ = translationstring.TranslationStringFactory('ptah')


def resolver(uri):
    """Resolve uri to object.

    :param uri: Uri string
    :rtype: Resolved object
    """


class Principal(object):
    """ Principal interface

    .. attribute:: __uri__

       Principal uri

    .. attribute:: name

       Principal name

    .. attribute:: login

       Principal login

    """


class AuthInfo(object):
    """ Authentication information

    .. attribute:: __uri__

       Principal uri or None if principal is not set

    .. attribute:: principal

       :py:class:`ptah.interfaces.Principal` object

    .. attribute:: status

       Status, True is principal has been authenticated, false otherwise

    .. attribute:: message

       Readable message from auth checkers

    """


def auth_checker(info):
    """ Perform additional checks on principal during authentication process.

    :param info: A instance of :py:class:`ptah.interfaces.AuthInfo` class
    """


class AuthProvider(object):
    """ Authentication provider interface """

    def authenticate(self, credentials):
        """ Authenticate credentials,
        return :py:class:`ptah.interfaces.Principal` object or None """

    def get_principal_bylogin(self, login):
        """ return instance of :py:class:`ptah.interfaces.Principal` or None """

    def get_principal_byemail(self, email):
        """ return instance of :py:class:`ptah.interfaces.Principal` or None """


def principal_searcher(term):
    """ Search users by term

    :param term: search term (str)
    :rtype: iterator of :py:class:`ptah.interfaces.Principal` instances

    """

class IOwnersAware(interface.Interface):
    """ Owners aware context

    .. attribute:: __owner__

       Owner principal uri
    """

    __owner__ = interface.Attribute('Owner')


class ILocalRolesAware(interface.Interface):
    """ Local roles aware context

    .. attribute:: __local_roles__

    """

    __local_roles__ = interface.Attribute('Local roles dict')


class IACLsAware(interface.Interface):
    """ acl maps aware context """

    __acls__ = interface.Attribute('List of acl map ids')


def populate_step(registry):
    """ Populate data step.

    :param registry: Pyramid :py:class:`pyramid.registry.Registry` object
    """


def roles_provider(context, uid, registry):
    """ Roles provider interface

    :param context: Current context object
    :param userid: User id
    :param registry: Pyramid registry object
    :rtype: Sequence of roles
    """


class TypeException(Exception):
    """ type exception """


class Forbidden(HTTPForbidden, TypeException):
    """ something is forbidden """


class NotFound(HTTPNotFound, TypeException):
    """ something is not found """


class ITypeInformation(interface.Interface):
    """ Content type information """

    name = interface.Attribute('Name')
    title = interface.Attribute('Title')
    description = interface.Attribute('Description')

    permission = interface.Attribute('Add permission')

    filter_content_types = interface.Attribute('Filter addable types')
    allowed_content_types = interface.Attribute('List of addable types')
    global_allow = interface.Attribute('Addable globally')

    def create(**data):
        """ construct new content instance """

    def is_allowed(container):
        """ allow create this content in container """

    def check_context(container):
        """ same as isAllowed, but raises HTTPForbidden """

    def list_types(self, container):
        """ list addable content types """

########NEW FILE########
__FILENAME__ = jsfields
""" various fields """
import ptah
import datetime
import pytz
import pform
from pform.interfaces import _, null, Invalid
from pform.fields import TextAreaField, DateField, DateTimeField


@pform.field('ckeditor')
class CKEditorField(TextAreaField):
    """ CKEditor input widget. Field name is ``ckeditor``.

    Extra params:

    :param width: Width of widget, default is ``400px``
    :param height: Height os widget, default is ``300px``
    """

    klass = 'ckeditor-widget form-control'

    width = '400px'
    height = '300px'

    tmpl_input = "ptah:ckeditor"


@pform.field('date')
class JSDateField(DateField):
    """Date input widget with Bootstrap Datepicker. Field name is ``date``."""

    klass = 'date-widget form-control'
    value = ''

    tmpl_input = 'ptah:jsdate'

#    def to_form(self, value):
#        if value is null or value is None:
#            return null

#        if isinstance(value, datetime.datetime):
#            value = value.date()

#        if not isinstance(value, datetime.date):
#            raise Invalid(
#                _('"${val}" is not a date object'), self,
#                mapping={'val': value})

#        return value

#    def to_field(self, value):
#        if not value:
#            return None
#        try:
#            return datetime.datetime.strptime(value, '%Y-%m-%d')
#        except Exception:
#            raise Invalid(_('Invalid date'), self)


@pform.field('datetime')
class JSDateTimeField(DateTimeField):
    """DateTime input widget with JQuery Datepicker.
    Field name is ``datetime``."""

    klass = 'datetime-widget form-control'
    value = ''

    #time_part = null
    #date_part = null
    #tzinfo = None

    tmpl_input = "ptah:jsdatetime"

#    def update(self):
#        self.date_name = '%s.date' % self.name
#        self.time_name = '%s.time' % self.name

#        super(JSDateTimeField, self).update()

#        self.date_part = self.params.get(self.date_name, null)
#        self.time_part = self.params.get(self.time_name, null)

#        if self.value:
#            raw = self.value
#            self.tzinfo = raw.tzinfo
#            if self.date_part is null:
#                self.date_part = raw.strftime('%m/%d/%Y')
#            if self.time_part is null:
#                FORMAT = ptah.get_settings(
#                    ptah.CFG_ID_FORMAT, self.request.registry)
#                self.time_part = raw.strftime(FORMAT['time_short'])

#        if self.date_part is null:
#            self.date_part = ''
#        if self.time_part is null:
#            self.time_part = ''

#    def extract(self, default=null):
#        date = self.params.get(self.date_name, default)
#        if date is default:
#            return default

#        if not date:
#            return null

#        time = self.params.get(self.time_name, default)
#        if time is default:
#            return default

#        if not time:
#            return null

#        #FORMAT = ptah.get_settings(ptah.CFG_ID_FORMAT, self.request.registry)
#        try:
#            dt = datetime.datetime.strptime(
#                '%s %s' % (date, time), '%m/%d/%Y %H:%M')
#        except ValueError:
#            try:
#                dt = datetime.datetime.strptime(
#                    '%s %s' % (date, time), '%m/%d/%Y %I:%M %p')
#            except ValueError:
#                return null

#        return dt.replace(tzinfo=self.tzinfo).isoformat()

########NEW FILE########
__FILENAME__ = mail
""" mail settings """
import ptah
import os.path
import itertools
from email import encoders
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.nonmultipart import MIMENonMultipart
from email.utils import formatdate, formataddr
from email.header import make_header

from pyramid import renderers
from pyramid.compat import bytes_


class MailGenerator(object):
    """ mail generator """

    def __init__(self, context):
        self._headers = {}
        self.context = context

    def _add_header(self, header, value, encode=False):
        self._headers[header] = (header, value, encode)

    def set_headers(self, message):
        charset = str(self.context.charset)

        extra = list(self.context.get_headers())
        for key, val, encode in itertools.chain(self._headers.values(), extra):
            if encode:
                message[key] = make_header(((val, charset),))
            else:
                message[key] = val

    def get_message(self):
        """ render a mail template """
        context = self.context

        charset = str(context.charset)
        contentType = context.content_type

        mail_body = context.render()
        maintype, subtype = contentType.split('/')

        return MIMEText(mail_body, subtype, charset)

    def get_attachments(self):
        attachments = []

        # attach files
        for data, content_type, filename, disposition in \
                self.context.get_attachments():
            maintype, subtype = content_type.split('/')

            msg = MIMENonMultipart(maintype, subtype)

            msg.set_payload(data)
            if filename:
                msg['Content-Id']=bytes_('<{0}@ptah>'.format(filename),'utf-8')
                msg['Content-Disposition']=bytes_('{0}; filename="{1}"'.format(
                    disposition, filename), 'utf-8')

            encoders.encode_base64(msg)
            attachments.append(msg)

        return attachments

    def message(self, multipart_format='mixed', *args, **kw):
        context = self.context

        # generate message
        message = self.get_message()

        # generate attachments
        attachments = self.get_attachments()
        if attachments:
            # create multipart message
            root = MIMEMultipart(multipart_format)

            # insert headers
            self.set_headers(root)

            # create message with attachments
            related = MIMEMultipart('related')
            related.attach(message)

            for attach in attachments:
                disposition = attach['Content-Disposition']\
                              .decode('utf-8').split(';')[0]
                if disposition == 'attachment':
                    root.attach(attach)
                else:
                    related.attach(attach)

            root.attach(related)
            message = root

        # alternative
        alternatives = self.context.get_alternative()
        if alternatives:
            mainmessage = MIMEMultipart('alternative')
            mainmessage.attach(message)

            for msg in alternatives:
                mainmessage.attach(MailGenerator(msg).message(
                        multipart_format, *args, **kw))

            message = mainmessage

        # default headers
        self._add_header('Subject', context.subject, True)

        self.set_headers(message)
        return message

    def __call__(self, multipart_format='mixed', *args, **kw):
        context = self.context
        message = self.message(multipart_format, *args, **kw)

        message['Date'] = formatdate()
        if context.message_id:
            message['Message-ID'] = context.message_id

        if not message.get('To') and context.to_address:
            message['To'] = context.to_address

        if not message.get('From') and context.from_address:
            message['From'] = formataddr(
                (context.from_name, context.from_address))

        return message


class MailTemplate(object):
    """ mail template with base features """

    subject = ''
    charset = 'utf-8'
    content_type = 'text/plain'
    message_id = None
    template = None

    from_name = ''
    from_address = ''
    to_address = ''
    return_address = ''
    errors_address = ''

    def __init__(self, context, request, **kwargs):
        self.__dict__.update(kwargs)

        self.context = context
        self.request = request
        self.cfg = ptah.get_settings(ptah.CFG_ID_PTAH, request.registry)

        self._files = []
        self._headers = {}
        self._alternative = []

    def add_header(self, header, value, encode=False):
        self._headers[header] = (header, value, encode)

    def has_header(self, header):
        header = header.lower()
        for key in self._headers.keys():
            if key.lower() == header:
                return True

        return False

    def get_headers(self):
        return self._headers.values()

    def add_attachment(self, file_data, content_type,
                       filename, disposition='attachment'):
        self._files.append((file_data, content_type,
                            wrap_filename(filename), disposition))

    def get_attachments(self):
        return self._files

    def add_alternative(self, template):
        self._alternative.append(template)

    def get_alternative(self):
        return self._alternative

    def update(self):
        if not self.from_name:
            self.from_name = self.cfg['email_from_name']
        if not self.from_address:
            self.from_address = self.cfg['email_from_address']

    def render(self):
        kwargs = {'view': self,
                  'context': self.context,
                  'request': self.request}

        return renderers.render(self.template, kwargs, self.request)

    def send(self, email=None, mailer=None, **kw):
        if email:
            self.to_address = email

        message = self(**kw)

        if mailer is None:
            mailer = self.cfg.get('Mailer')

        if mailer is not None:
            mailer.send(message['from'], message['to'], message)

    def __call__(self, **kw):
        for key, value in kw.items():
            if type(value) is tuple:
                self.add_header(key, value[0], value[1])
            else:
                self.add_header(key, value)

        self.update()
        return MailGenerator(self)()


def wrap_filename(f_name):
    dir, f_name = os.path.split(f_name)
    f_name = f_name.split('\\')[-1].split('/')[-1]
    for key in '~,\'':
        f_name = f_name.replace(key, '_')

    return f_name

########NEW FILE########
__FILENAME__ = fieldpreviews
import pytz
import pform
import decimal, datetime
from ptah.jsfields import JSDateField, JSDateTimeField, CKEditorField


vocabulary = pform.Vocabulary(
    (1, 'one', 'One', 'One description'),
    (2, 'two', 'Two', 'Two description'),
    (3, 'three', 'Three', 'Three description'))


@pform.fieldpreview(pform.MultiChoiceField)
def multiChoicePreview(request):
    field = pform.MultiChoiceField(
        'MultiChoiceField',
        title = 'Multi choice field',
        description = 'Multi choice field preview description',
        default = [1,3],
        vocabulary = vocabulary)

    widget = field.bind(request, 'preview.', pform.null, {})
    widget.update()
    return widget.render_widget()


@pform.fieldpreview(pform.ChoiceField)
def choicePreview(request):
    field = pform.ChoiceField(
        'ChoiceField',
        title = 'Choice field',
        description = 'Choice field preview description',
        missing = 1,
        vocabulary = vocabulary)

    widget = field.bind(request, 'preview.', pform.null, {})
    widget.update()
    return widget.render_widget()


@pform.fieldpreview(pform.BoolField)
def boolPreview(request):
    field = pform.BoolField(
        'BoolField',
        default = True,
        title = 'Boolean field',
        description = 'Boolean field preview description')

    widget = field.bind(request, 'preview.', pform.null, {})
    widget.update()
    return widget.render_widget()


@pform.fieldpreview(pform.RadioField)
def radioPreview(request):
    field = pform.RadioField(
        'RadioField',
        title = 'Radio field',
        description = 'Radio field preview description',
        default = 1,
        vocabulary = vocabulary)

    widget = field.bind(request, 'preview.', pform.null, {})
    widget.update()
    return widget.render_widget()


@pform.fieldpreview(pform.TextAreaField)
def textareaPreview(request):
    field = pform.TextAreaField(
        'TextAreaField',
        title = 'TextArea field',
        description = 'TextArea field preview description',
        default = 'Test text in text area field.')

    widget = field.bind(request, 'preview.', pform.null, {})
    widget.update()
    return widget.render_widget()


@pform.fieldpreview(pform.LinesField)
def linesPreview(request):
    field = pform.LinesField(
        'LinesField',
        title = 'Lines field',
        description = 'Lines field preview description',
        default = ['One', 'Two', 'Three'])

    widget = field.bind(request, 'preview.', pform.null, {})
    widget.update()
    return widget.render_widget()


@pform.fieldpreview(pform.TextField)
def textPreview(request):
    field = pform.TextField(
        'TextField',
        title = 'Text field',
        description = 'Text field preview description',
        default = 'Test text in text field.')

    widget = field.bind(request, 'preview.', pform.null, {})
    widget.update()
    return widget.render_widget()


@pform.fieldpreview(pform.FileField)
def filePreview(request):
    field = pform.FileField(
        'FileField',
        title = 'File field',
        description = 'File field preview description',
        default = 'Test file in file field.')

    widget = field.bind(request, 'preview.', pform.null, {})
    widget.update()
    return widget.render_widget()


@pform.fieldpreview(pform.IntegerField)
def intPreview(request):
    field = pform.IntegerField(
        'IntegerField',
        title = 'Integer field',
        description = 'Integer field preview description',
        default = 456782)

    widget = field.bind(request, 'preview.', pform.null, {})
    widget.update()
    return widget.render_widget()


@pform.fieldpreview(pform.FloatField)
def floatPreview(request):
    field = pform.FloatField(
        'FloatField',
        title = 'Float field',
        description = 'Float field preview description',
        default = 456782.236)

    widget = field.bind(request, 'preview.', pform.null, {})
    widget.update()
    return widget.render_widget()


@pform.fieldpreview(pform.DecimalField)
def decimalPreview(request):
    field = pform.DecimalField(
        'DecimalField',
        title = 'Decimal field',
        description = 'Decimal field preview description',
        default = decimal.Decimal('10.54'))

    widget = field.bind(request, 'preview.', pform.null, {})
    widget.update()
    return widget.render_widget()


@pform.fieldpreview(pform.PasswordField)
def passwordPreview(request):
    field = pform.PasswordField(
        'PasswordField',
        title = 'Password field',
        description = 'Password field preview description')

    widget = field.bind(request, 'preview.', pform.null, {})
    widget.update()
    return widget.render_widget()


@pform.fieldpreview(JSDateField)
def jsdatePreview(request):
    field = JSDateField(
        'JSDateField',
        title = 'jQuery Date field',
        description = 'jQuery Date field preview description',
        default = datetime.date.today())

    widget = field.bind(request, 'preview.', pform.null, {})
    widget.update()
    return widget.render_widget()


@pform.fieldpreview(JSDateTimeField)
def jsdatetimePreview(request):
    field = JSDateTimeField(
        'JSDateTimeField',
        title = 'jQuery DateTime field',
        description = 'jQuery DateTime field preview description')

    widget = field.bind(request, 'preview.', datetime.datetime.now(), {})
    widget.update()
    return widget.render_widget()


@pform.fieldpreview(CKEditorField)
def ckeditorPreview(request):
    field = CKEditorField(
        'CKEditorField',
        title = 'CKEditor field',
        description = 'CKEditor field preview description',
        default = 'Test text in ckeditor field.',
        width = '200px')

    widget = field.bind(request, 'preview.', pform.null, {})
    widget.update()
    return widget.render_widget()


@pform.fieldpreview(pform.TimezoneField)
def timezonePreview(request):
    field = pform.TimezoneField(
        'TimezoneField',
        title = 'Timezone field',
        description = 'Timezone field preview description',
        default = pytz.timezone('US/Central'))

    widget = field.bind(request, 'preview.', pform.null, {})
    widget.update()
    return widget.render_widget()

########NEW FILE########
__FILENAME__ = fields
""" pform fields """
import ptah
import player
from pform.directives import ID_FIELD, ID_PREVIEW
from pyramid.view import view_config


@ptah.manage.module('fields')
class FieldsModule(ptah.manage.PtahModule):
    __doc__ = ('A preview and listing of all form fields in the '
      'application. This is useful to see what fields are available. '
      'You may also interact with the field to see how it works in '
      'display mode.')

    title = 'Field types'


@view_config(
    context=FieldsModule,
    renderer=player.layout('ptah-manage:fields.lt'))

class FieldsView(ptah.View):
    """ Fields manage module view """

    def update(self):
        data = []

        fields = self.request.registry[ID_FIELD]
        previews = self.request.registry[ID_PREVIEW]

        for name, cls in fields.items():
            data.append({'name': name,
                         'doc': cls.__doc__,
                         'preview': previews.get(cls)})

        self.fields = sorted(data, key = lambda item: item['name'])

########NEW FILE########
__FILENAME__ = introspect
""" introspect module """
import player
from player import RendererNotFound
from pyramid.view import view_config
from pyramid.compat import url_unquote

import ptah
from ptah.manage import get_manage_url
from pform.directives import ID_PREVIEW


@ptah.manage.module('introspect')
class IntrospectModule(ptah.manage.PtahModule):
    __doc__ = 'Insight into all configuration and registrations.'

    title = 'Introspect'

    def __getitem__(self, key):
        key = url_unquote(key)
        if key in self.request.registry.introspector.categories():
            return Introspector(key, self, self.request)

        raise KeyError(key)


class Introspector(object):

    def __init__(self, name, mod, request):
        self.__name__ = name
        self.__parent__ = mod

        self.name = name
        self.request = request


@view_config(
    context=IntrospectModule,
    renderer=player.layout('ptah-manage:introspect.lt'))

class MainView(ptah.View):
    __doc__ = 'Introspection module view.'

    def update(self):
        registry = self.request.registry
        self.categories = registry.introspector.categories()
        self.manage_url = '{0}/introspect'.format(get_manage_url(self.request))


@view_config(
    context=Introspector,
    renderer=player.layout('ptah-manage:introspect-intr.lt'))

class IntrospectorView(ptah.View):

    def update(self):
        name = self.context.name
        registry = self.request.registry

        self.intrs = sorted(
            (item['introspectable'] for item in
             registry.introspector.get_category(name)),
            key = lambda item: item.title)

        self.manage_url = '{0}/introspect'.format(get_manage_url(self.request))

        self.categories = registry.introspector.categories()

    def render_intr(self, intr):
        try:
            return self.request.render_tmpl(
                'ptah-intr:%s'%intr.type_name, intr,
                manage_url = self.manage_url, rst_to_html = ptah.rst_to_html)
        except RendererNotFound:
            return self.request.render_tmpl(
                'ptah-intr:ptah-default', intr,
                manage_url = self.manage_url, rst_to_html = ptah.rst_to_html)


@player.tmpl_filter('ptah-intr:pform-field')
def tmpl_formfield(context, request):
    return {'previews': request.registry[ID_PREVIEW]}


@player.tmpl_filter('ptah-intr:ptah-subscriber')
def tmpl_subscriber(intr, request):
    handler = intr['handler']
    required = intr['required']
    factoryInfo = '%s.%s'%(intr['codeinfo'].module, handler.__name__)

    if len(required) > 1: # pragma: no cover
        obj = required[0]
        klass = required[1]
    else:
        obj = None
        klass = required[0]

    return dict(factoryInfo=factoryInfo, obj=obj, klass=klass)

########NEW FILE########
__FILENAME__ = layout
from zope.interface import providedBy
from pyramid.view import view_config
from pyramid.interfaces import IView, IViewClassifier
from pyramid.httpexceptions import HTTPNotFound


@view_config(name='layout-preview.html')
def layoutPreview(context, request):
    view_name = request.GET.get('view', '')

    adapters = request.registry.adapters

    view = adapters.lookup(
        (IViewClassifier, providedBy(request), providedBy(context)),
        IView, name=view_name, default=None)

    if view is None:
        return HTTPNotFound()

    request.__layout_debug__ = view.__discriminator__(context, request)

    return view(context, request)

########NEW FILE########
__FILENAME__ = manage
import player
from pyramid.view import view_config
from pyramid.interfaces import IRootFactory
from pyramid.traversal import DefaultRootFactory
from pyramid.httpexceptions import HTTPForbidden
from pyramid.decorator import reify

import ptah
from ptah import config

CONFIG_ID = 'ptah.manage:config'
MANAGE_ID = 'ptah.manage:module'
MANAGE_ACTIONS = 'ptah.manage:actions'


class PtahModule(object):

    #: Module name (also is used for url generation)
    name = ''

    #: Module title
    title = ''

    def __init__(self, manager, request):
        self.__parent__ = manager
        self.request = request

    def url(self):
        """ return url to this module """
        return '{0}/{1}'.format(get_manage_url(self.request), self.name)

    @property
    def __name__(self):
        return self.name

    def available(self):
        """ is module available """
        return True


def get_manage_url(request):
    url = request.application_url
    if url.endswith('/'):
        url = url[:-1]

    cfg = ptah.get_settings(ptah.CFG_ID_PTAH, request.registry)
    return '{0}/{1}'.format(url, cfg['manage'])


def module(name):
    info = config.DirectiveInfo()

    def wrapper(cls):
        discr = (MANAGE_ID, name)
        intr = config.Introspectable(
            MANAGE_ID, discr, cls.title, 'ptah-managemodule')
        intr['name'] = name
        intr['factory'] = cls
        intr['codeinfo'] = info.codeinfo

        def _complete(cfg, cls, name):
            cls.name = name
            cfg.get_cfg_storage(MANAGE_ID)[name] = cls

        info.attach(
            config.Action(
                _complete, (cls, name),
                discriminator=discr, introspectables=(intr,))
            )
        return cls

    return wrapper


class PtahAccessManager(object):
    """ Allow access to ptah manage for users with specific role and id """

    def __init__(self, registry=None):
        self.cfg = ptah.get_settings(ptah.CFG_ID_PTAH, registry)

    def __call__(self, userid, request):
        managers = self.cfg['managers']

        if userid == ptah.SUPERUSER_URI or '*' in managers:
            return True

        role = self.cfg['manager_role']
        if role:
            root = getattr(request, 'root', None)
            if root is None:
                root_factory = request.registry.queryUtility(
                    IRootFactory, default=DefaultRootFactory)
                root = root_factory(request)

            if role in ptah.get_local_roles(userid, request, root):
                return True

        principal = ptah.resolve(userid)

        if principal is not None and principal.login in managers:
            return True

        return False


def check_access(userid, request):
    manager = ptah.get_settings(ptah.CFG_ID_PTAH).get('access_manager')
    if manager is not None:
        return manager(userid, request)
    return False


def set_access_manager(manager, registry=None):
    ptah.get_settings(ptah.CFG_ID_PTAH, registry)['access_manager'] = manager


class root(object):
    __name__ = None
    __parent__ = None

    title = 'Home'


class PtahManageRoute(object):
    """ ptah management route """

    __name__ = 'ptah-manage'
    __parent__ = root()

    title = 'Manage'

    def __init__(self, request):
        self.request = request

        userid = ptah.auth_service.get_userid()
        if not check_access(userid, request):
            raise HTTPForbidden()

        self.userid = userid
        self.cfg = ptah.get_settings(ptah.CFG_ID_PTAH)
        self.__name__ = self.cfg['manage']

        ptah.auth_service.set_effective_userid(ptah.SUPERUSER_URI)

    def __getitem__(self, key):
        if self.cfg['enable_modules']:
            if key in self.cfg['enable_modules']:
                mod = ptah.get_cfg_storage(MANAGE_ID).get(key)
                if mod is not None:
                    return mod(self, self.request)

        elif key not in self.cfg['disable_modules']:
            mod = ptah.get_cfg_storage(MANAGE_ID).get(key)
            if mod is not None:
                return mod(self, self.request)

        raise KeyError(key)


class LayoutManage(ptah.View):
    """ Base layout for ptah manage """

    def update(self):
        self.user = ptah.resolve(self.context.userid)
        self.manage_url = get_manage_url(self.request)

        mod = self.request.context
        while not isinstance(mod, PtahModule):
            mod = getattr(mod, '__parent__', None)
            if mod is None: # pragma: no cover
                break

        self.module = mod
        self.actions = ptah.list_uiactions(mod, self.request, MANAGE_ACTIONS)


@view_config(
    context=PtahManageRoute,
    renderer=player.layout('ptah-manage:manage.lt'))

class ManageView(ptah.View):
    """List ptah modules"""

    rst_to_html = staticmethod(ptah.rst_to_html)

    def update(self):
        context = self.context
        request = self.request
        self.cfg = ptah.get_settings(ptah.CFG_ID_PTAH, request.registry)

        mods = []
        for name, mod in ptah.get_cfg_storage(MANAGE_ID).items():
            if self.cfg['enable_modules'] and \
                    name not in self.cfg['enable_modules']:
                continue
            if name in self.cfg['disable_modules']:
                continue

            mod = mod(context, request)
            if not mod.available():
                continue
            mods.append((mod.title, mod))

        self.modules = [mod for _t, mod in sorted(mods)]

########NEW FILE########
__FILENAME__ = permissions
""" security ptah module """
import ptah
import player
from ptah.manage import get_manage_url
from pyramid.view import view_config


@ptah.manage.module('permissions')
class PermissionsModule(ptah.manage.PtahModule):
    __doc__ = 'A listing of all permission sets and their definitions'

    title = 'Permissions'


@view_config(
    context=PermissionsModule,
    renderer=player.layout('ptah-manage:permissions.lt'))

class PermissionsView(ptah.View):
    """ Permissions module default view """

    def update(self):
        self.manage = get_manage_url(self.request)
        self.permissions = sorted(ptah.get_permissions().values(),
                                  key = lambda p: p.title)

        acls = ptah.get_acls()
        self.acls = sorted([acl for acl in acls.values() if acl.id != ''],
                           key = lambda a: a.title)
        self.acls.insert(0, ptah.DEFAULT_ACL)


@view_config(
    name='roles.html',
    context=PermissionsModule,
    renderer=player.layout('ptah-manage:roles.lt'))

class RolesView(ptah.View):
    """ Roles view for permissions manage module """

    def update(self):
        self.roles = sorted(ptah.get_roles().values(), key = lambda r: r.title)

########NEW FILE########
__FILENAME__ = settings
""" settings module """
import pform
import player
import ptah
from ptah.settings import ID_SETTINGS_GROUP
from pyramid.decorator import reify
from pyramid.view import view_config
from pyramid.httpexceptions import HTTPFound


@ptah.manage.module('settings')
class SettingsModule(ptah.manage.PtahModule):
    __doc__ = 'The current settings which include defaults not used by .ini'

    title = 'Settings'

    def __getitem__(self, key):
        grp = ptah.get_settings(key, self.request.registry)
        if grp is not None and grp.__ttw__:
            return SettingsWrapper(grp, self)
        raise KeyError(key)


class SettingsWrapper(object):

    def __init__(self, grp, mod):
        self.__name__ = grp.__name__
        self.__parent__ = mod
        self.group = grp


@view_config(
    context=SettingsModule,
    renderer=player.layout('ptah-manage:settings.lt'))

class SettingsView(ptah.View):
    """ Settings manage module view """

    grps = None

    def update(self):
        groups = ptah.get_cfg_storage(ID_SETTINGS_GROUP).items()

        data = []
        for name, group in sorted(groups):
            if self.grps is not None and name not in self.grps:
                continue

            title = group.__title__ or name
            description = group.__description__

            schema = []
            for field in group.__fields__.values():
                if getattr(field, 'tint', False):
                    value = '* * * * * * *'
                else:
                    value = ptah.json.dumps(group[field.name])
                schema.append(
                    ({'name': '{0}.{1}'.format(name, field.name),
                      'type': field.__class__.__name__,
                      'value': value,
                      'title': field.title,
                      'description': field.description,
                      'default': ptah.json.dumps(field.default)}))

            data.append(
                ({'title': title,
                  'description': description,
                  'schema': schema,
                  'name': group.__name__,
                  'ttw': group.__ttw__}))

        return {'data': sorted(data, key=lambda item: item['title'])}


@view_config(context=SettingsWrapper, renderer=player.layout())

class EditForm(pform.Form):
    """ Settings group edit form """

    @reify
    def label(self):
        return self.context.group.__title__

    @reify
    def description(self):
        return self.context.group.__description__

    @reify
    def fields(self):
        grp = self.context.group
        return grp.__fields__.omit(*grp.__ttw_skip_fields__)

    def form_content(self):
        return self.context.group

    @pform.button('Modify', actype=pform.AC_PRIMARY)
    def modify_handler(self):
        data, errors = self.extract()
        if errors: # pragma: no cover
            self.add_error_message(errors)
            return

        self.request.add_message("Settings have been modified.")
        self.context.group.updatedb(**data)
        return HTTPFound('../#{0}'.format(self.context.group.__name__))

    #@pform.button('Reset defaults', actype=pform.AC_INFO)
    #def reset_handler(self):
    #    pass

    @pform.button('Back')
    def back_handler(self):
        return HTTPFound('..')

########NEW FILE########
__FILENAME__ = source
""" Source code view """
import os.path
import pkg_resources
import player
from pyramid.view import view_config
from pyramid.httpexceptions import HTTPFound

import ptah
from ptah.manage.manage import PtahManageRoute


@view_config(
    name='source.html', context=PtahManageRoute,
    renderer=ptah.layout('ptah-manage:source.lt'))

class SourceView(ptah.View):
    __doc__ = 'Source introspection page.'

    source = None
    format = None

    def update(self):
        name = self.request.params.get('pkg')
        if name is None:
            return HTTPFound(location='.')

        dist = None
        pkg_name = name
        while 1:
            try:
                dist = pkg_resources.get_distribution(pkg_name)
                if dist is not None: # pragma: no cover
                    break
            except pkg_resources.DistributionNotFound:
                if '.' not in pkg_name:
                    break
                pkg_name = pkg_name.rsplit('.',1)[0]

        if dist is None:
            self.source = None

        names = name[len(pkg_name)+1:].split('.')
        path = '%s.py'%os.path.join(*names)
        try:
            abspath = pkg_resources.resource_filename(pkg_name, path)
        except:
            return HTTPFound(location='.')

        if os.path.isfile(abspath):
            self.file = abspath
            self.name = '%s.py'%names[-1]
            self.pkg_name = pkg_name
            source = open(abspath, 'rb').read()

            if not self.format:
                try:
                    from pygments import highlight
                    from pygments.lexers import PythonLexer
                    from pygments.formatters import HtmlFormatter

                    html = HtmlFormatter(
                        linenos='inline',
                        lineanchors='sl',
                        anchorlinenos=True,
                        noclasses = True,
                        cssclass="ptah-source")

                    def format(self, code, highlight=highlight,
                               lexer = PythonLexer()):
                        return highlight(code, lexer, html)

                except ImportError: # pragma: no cover
                    def format(self, text):
                        return '<pre>%s</pre>'%text

                self.__class__.format = format

            self.source = self.format(source)

########NEW FILE########
__FILENAME__ = sqla
""" sqla module """
import pform
import player
from sqlalchemy.orm.mapper import _mapper_registry
from pyramid.view import view_config
from pyramid.compat import url_quote_plus
from pyramid.decorator import reify
from pyramid.httpexceptions import HTTPFound

import ptah

Session = ptah.get_session()


@ptah.manage.module('sqla')
class SQLAModule(ptah.manage.PtahModule):
    __doc__ = 'A listing of all tables with ability to view and edit records'

    title = 'SQLAlchemy'

    metadata = {}

    def __getitem__(self, key):
        try:
            id, table = key.split('-', 1)
        except:
            raise KeyError(key)

        md = self.metadata[id][0]
        return Table(md.tables[table], self, self.request)

    def available(self):
        PTAH = ptah.get_settings(ptah.CFG_ID_PTAH, self.request.registry)
        return PTAH.get('sqlalchemy_initialized', False)

    @classmethod
    def addMetadata(cls, md, id, title=''):
        cls.metadata[id] = [md, title or id.capitalize()]

addMetadata = SQLAModule.addMetadata
addMetadata(ptah.get_base().metadata, 'psqla', 'Pyramid sqla')


class Table(object):

    def __init__(self, table, mod, request):
        self.__name__ = 'psqla-%s' % table.name
        self.__parent__ = mod

        self.table = table
        self.request = request

        self.title = table.name

    def __getitem__(self, key):
        if key == 'add.html':
            raise KeyError(key)

        try:
            return Record(key, self.table, self, self.request)
        except:
            raise KeyError(key)


class Record(object):

    def __init__(self, pid, table, parent, request):
        self.pid = pid
        self.table = table
        self.request = request

        self.__name__ = str(pid)
        self.__parent__ = parent

        self.pname = None
        self.pcolumn = None
        for cl in table.columns:
            if cl.primary_key:
                self.pname = cl.name
                self.pcolumn = cl

        self.data = Session.query(table).filter(
            self.pcolumn == pid).one()


@view_config(
    context=SQLAModule,
    renderer=player.layout('ptah-manage:sqla-index.lt'))

class MainView(ptah.View):
    __doc__ = "sqlalchemy tables listing page."

    def printTable(self, table):
        columns = []
        for cl in table.columns:
            kwarg = []
            if cl.key != cl.name:
                kwarg.append('key') # pragma: no cover
            if cl.primary_key:
                kwarg.append('primary_key')
            if not cl.nullable:
                kwarg.append('nullable')
            if cl.default:
                kwarg.append('default')

            columns.append(
                "Column(%s)" % ', '.join(
                    [repr(cl.name)] + [repr(cl.type)] +
                    [repr(x) for x in cl.foreign_keys if x is not None] +
                    [repr(x) for x in cl.constraints] +
                    ["%s=%s" % (k, repr(getattr(cl, k))) for k in kwarg])
                )

        return ("Table(%s)" % repr(table.name), columns)

    def update(self):
        tables = []

        for id, (md, title) in self.context.metadata.items():
            data = []
            for name, table in md.tables.items():
                data.append((name, self.printTable(table)))

            tables.append((title, id, sorted(data)))

        self.tables = sorted(tables)


def get_inheritance(table):
    # inheritance
    inherits = []
    mapper = None
    for m, s in _mapper_registry.items():
        if m.local_table is table:
            mapper = m

    curr_mapper = mapper
    while curr_mapper is not None:
        curr_mapper = curr_mapper.inherits
        if curr_mapper is not None and \
                curr_mapper.local_table.name != table.name and \
                curr_mapper.local_table.name not in inherits:
            inherits.append(curr_mapper.local_table.name)

    inherits.reverse()
    return inherits


@view_config(
    context=Table,
    renderer=player.layout('ptah-manage:sqla-table.lt'))

class TableView(pform.Form):
    __doc__ = "List table records."

    csrf = True
    page = ptah.Pagination(15)

    def update_form(self):
        table = self.table = self.context.table
        self.primary = None
        self.pcolumn = None
        self.uris = []

        self.inheritance = get_inheritance(table)

        if table.name == 'ptah_nodes' or self.inheritance:
            self.show_actions = False
        else:
            self.show_actions = True

        names = []
        for cl in table.columns:
            names.append(cl.name)
            if cl.primary_key:
                self.primary = cl.name
                self.pcolumn = cl
            if cl.info.get('uri'):
                self.uris.append(len(names)-1)

        res = super(TableView, self).update_form()

        request = self.request
        try:
            current = int(request.params.get('batch', None))
            if not current:
                current = 1

            request.session['table-current-batch'] = current
        except:
            current = request.session.get('table-current-batch')
            if not current:
                current = 1

        self.size = Session.query(table).count()
        self.current = current

        self.pages, self.prev, self.next = self.page(self.size, self.current)

        offset, limit = self.page.offset(current)
        self.data = Session.query(table).offset(offset).limit(limit).all()

        return res

    def quote(self, val):
        return url_quote_plus(val)

    def val(self, val):
        try:
            if isinstance(val, str): # pragma: no cover
                val = str(val)
            elif isinstance(val, bytes):
                raise
            elif not isinstance(val, str):
                val = str(val)
        except: # pragma: no cover
            val = "Can't show"
        return val[:100]

    @pform.button('Add', actype=pform.AC_PRIMARY)
    def add(self):
        return HTTPFound(location='add.html')

    @pform.button('Remove', actype=pform.AC_DANGER)
    def remove(self):
        self.validate_csrf_token()

        ids = []
        for id in self.request.POST.getall('rowid'):
            ids.append(id)

        if not ids:
            self.request.add_message(
                'Please select records for removing.', 'warning')
            return

        self.table.delete(self.pcolumn.in_(ids)).execute()
        self.request.add_message('Select records have been removed.')


@view_config(
    context=Record,
    renderer=player.layout('ptah-manage:sqla-edit.lt'))

class EditRecord(pform.Form):
    __doc__ = "Edit table record."

    csrf = True

    @reify
    def label(self):
        return 'record %s'%self.context.__name__

    @reify
    def fields(self):
        return ptah.build_sqla_fieldset(
            [(cl.name, cl) for cl in self.context.table.columns],
            skipPrimaryKey=True)

    def update_form(self):
        self.inheritance = get_inheritance(self.context.table)
        if self.context.table.name == 'ptah_nodes' or self.inheritance:
            self.show_remove = False
        else:
            self.show_remove = True

        return super(EditRecord, self).update_form()

    def form_content(self):
        data = {}
        for field in self.fields.fields():
            data[field.name] = getattr(
                self.context.data, field.name, field.default)
        return data

    @pform.button('Cancel')
    def cancel_handler(self):
        return HTTPFound(location='..')

    @pform.button('Modify', actype=pform.AC_PRIMARY)
    def modify_handler(self):
        data, errors = self.extract()

        if errors:
            self.add_error_message(errors)
            return

        self.context.table.update(
            self.context.pcolumn == self.context.__name__, data).execute()
        self.request.add_message('Table record has been modified.', 'success')
        return HTTPFound(location='..')

    @pform.button('Remove', actype=pform.AC_DANGER,
                  condition=lambda form: form.show_remove)
    def remove_handler(self):
        self.validate_csrf_token()

        self.context.table.delete(
            self.context.pcolumn == self.context.__name__).execute()
        self.request.add_message('Table record has been removed.')
        return HTTPFound(location='..')



@view_config(name='add.html', context=Table, renderer=player.layout())

class AddRecord(pform.Form):
    """ Add new table record. """

    csrf = True

    @reify
    def label(self):
        return '%s: new record'%self.context.table.name

    @reify
    def fields(self):
        return ptah.build_sqla_fieldset(
            [(cl.name, cl) for cl in self.context.table.columns],
            skipPrimaryKey = True)

    @pform.button('Create', actype=pform.AC_PRIMARY)
    def create(self):
        data, errors = self.extract()

        if errors:
            self.add_error_message(errors)
            return

        try:
            self.context.table.insert(values = data).execute()
        except Exception as e: # pragma: no cover
            self.request.add_message(e, 'error')
            return

        self.request.add_message('Table record has been created.', 'success')
        return HTTPFound(location='.')

    @pform.button('Save & Create new',
                      name='createmulti', actype=pform.AC_PRIMARY)
    def create_multiple(self):
        data, errors = self.extract()

        if errors:
            self.add_error_message(errors)
            return

        try:
            self.context.table.insert(values = data).execute()
        except Exception as e: # pragma: no cover
            self.request.add_message(e, 'error')
            return

        self.request.add_message('Table record has been created.', 'success')

    @pform.button('Back')
    def cancel(self):
        return HTTPFound(location='.')

########NEW FILE########
__FILENAME__ = test_fieldpreviews
import ptah
import pform
from pform.directives import ID_PREVIEW
from ptah.manage import fieldpreviews
from ptah.testing import PtahTestCase
from pyramid.testing import DummyRequest
from pyramid.view import render_view_to_response


class TestFieldPreviews(PtahTestCase):

    def test_multiChoicePreview(self):
        previews = self.registry[ID_PREVIEW]
        self.assertIs(previews[pform.MultiChoiceField],
                      fieldpreviews.multiChoicePreview)

        request = DummyRequest()
        html = fieldpreviews.multiChoicePreview(request)
        self.assertIn('Multi choice field', html)

    def test_choicePreview(self):
        previews = self.registry[ID_PREVIEW]
        self.assertIs(previews[pform.ChoiceField],
                      fieldpreviews.choicePreview)

        request = DummyRequest()
        html = fieldpreviews.choicePreview(request)
        self.assertIn('Choice field', html)

    def test_boolPreview(self):
        previews = self.registry[ID_PREVIEW]
        self.assertIs(previews[pform.BoolField],
                      fieldpreviews.boolPreview)

        request = DummyRequest()
        html = fieldpreviews.boolPreview(request)
        self.assertIn('Boolean field', html)

    def test_radioPreview(self):
        previews = self.registry[ID_PREVIEW]
        self.assertIs(previews[pform.RadioField],
                      fieldpreviews.radioPreview)

        request = DummyRequest()
        html = fieldpreviews.radioPreview(request)
        self.assertIn('Radio field', html)

    def test_textareaPreview(self):
        previews = self.registry[ID_PREVIEW]
        self.assertIs(previews[pform.TextAreaField],
                      fieldpreviews.textareaPreview)

        request = DummyRequest()
        html = fieldpreviews.textareaPreview(request)
        self.assertIn('TextArea field', html)

    def test_linesPreview(self):
        previews = self.registry[ID_PREVIEW]
        self.assertIs(previews[pform.LinesField],
                      fieldpreviews.linesPreview)

        request = DummyRequest()
        html = fieldpreviews.linesPreview(request)
        self.assertIn('Lines field', html)

    def test_textPreview(self):
        previews = self.registry[ID_PREVIEW]
        self.assertIs(previews[pform.TextField],
                      fieldpreviews.textPreview)

        request = DummyRequest()
        html = fieldpreviews.textPreview(request)
        self.assertIn('Text field', html)

    def test_intPreview(self):
        previews = self.registry[ID_PREVIEW]
        self.assertIs(previews[pform.IntegerField],
                      fieldpreviews.intPreview)

        request = DummyRequest()
        html = fieldpreviews.intPreview(request)
        self.assertIn('Integer field', html)

    def test_floatPreview(self):
        previews = self.registry[ID_PREVIEW]
        self.assertIs(previews[pform.FloatField],
                      fieldpreviews.floatPreview)

        request = DummyRequest()
        html = fieldpreviews.floatPreview(request)
        self.assertIn('Float field', html)

    def test_decimalPreview(self):
        previews = self.registry[ID_PREVIEW]
        self.assertIs(previews[pform.DecimalField],
                      fieldpreviews.decimalPreview)

        request = DummyRequest()
        html = fieldpreviews.decimalPreview(request)
        self.assertIn('Decimal field', html)

    def test_passwordPreview(self):
        previews = self.registry[ID_PREVIEW]
        self.assertIs(previews[pform.PasswordField],
                      fieldpreviews.passwordPreview)

        request = DummyRequest()
        html = fieldpreviews.passwordPreview(request)
        self.assertIn('Password field', html)

    def test_timezonePreview(self):
        previews = self.registry[ID_PREVIEW]
        self.assertIs(previews[pform.TimezoneField],
                      fieldpreviews.timezonePreview)

        request = DummyRequest()
        html = fieldpreviews.timezonePreview(request)
        self.assertIn('Timezone field', html)


class TestFieldsModule(PtahTestCase):

    def test_fields_module(self):
        from ptah.manage.manage import PtahManageRoute
        from ptah.manage.fields import FieldsModule

        request = DummyRequest()

        ptah.auth_service.set_userid('test')
        cfg = ptah.get_settings(ptah.CFG_ID_PTAH, self.registry)
        cfg['managers'] = ('*',)
        mr = PtahManageRoute(request)
        mod = mr['fields']

        self.assertIsInstance(mod, FieldsModule)

    def test_fields_view(self):
        from ptah.manage.fields import FieldsModule, FieldsView

        request = DummyRequest()

        mod = FieldsModule(None, request)

        res = render_view_to_response(mod, request, '', False)
        self.assertEqual(res.status, '200 OK')

        from pform.directives import ID_FIELD

        fields = self.registry[ID_FIELD]

        view = FieldsView(None, request)
        view.update()

        self.assertEqual(len(view.fields), len(fields))
        self.assertIn('name', view.fields[0])
        self.assertIn('preview', view.fields[0])

########NEW FILE########
__FILENAME__ = test_introspect
import ptah
from ptah.testing import PtahTestCase
from pyramid.view import render_view_to_response


class TestIntrospectModule(PtahTestCase):

    def test_introspect_module(self):
        from ptah.manage.manage import PtahManageRoute
        from ptah.manage.introspect import IntrospectModule

        request = self.make_request()

        ptah.auth_service.set_userid('test')
        cfg = ptah.get_settings(ptah.CFG_ID_PTAH, self.registry)
        cfg['managers'] = ('*',)

        mr = PtahManageRoute(request)
        mod = mr['introspect']

        self.assertIsInstance(mod, IntrospectModule)

    def test_traversable(self):
        from ptah.manage.introspect import IntrospectModule, Introspector

        request = self.make_request()
        mod = IntrospectModule(None, request)

        self.assertRaises(KeyError, mod.__getitem__, 'unknown')

        package = mod['ptah:resolver']
        self.assertIsInstance(package, Introspector)

    def test_view(self):
        from ptah.manage.introspect import IntrospectModule

        request = self.make_request()
        mod = IntrospectModule(None, request)

        res = render_view_to_response(mod, request)
        self.assertIn('ptah:resolver', res.text)
        self.assertIn(
          '<a href="http://example.com/ptah-manage/introspect/ptah:resolver/">',
          res.text)

    def test_intr_view(self):
        from ptah.manage.introspect import IntrospectModule

        request = self.make_request()
        mod = IntrospectModule(None, request)

        intr = mod['ptah:resolver']

        res = render_view_to_response(intr, request)
        self.assertIn('System super user', res.text)

    def test_intr_view_default(self):
        from ptah.manage.introspect import IntrospectModule

        request = self.make_request()
        mod = IntrospectModule(None, request)

        intr = mod['pform:field-preview']

        res = render_view_to_response(intr, request)
        self.assertIn('pform:field-preview', res.text)

########NEW FILE########
__FILENAME__ = test_intr_renderers
import ptah
from pyramid.view import render_view_to_response


class TestUriIntrospect(ptah.PtahTestCase):

    def test_uri_introspect(self):
        from ptah.manage.uri import ID_RESOLVER

        def resolver(uri): # pragma: no cover
            return 'Resolved'

        self.config.ptah_uri_resolver('uri-intro-test', resolver)

        intr = self.registry.introspector.get(
            ID_RESOLVER, (ID_RESOLVER, 'uri-intro-test'))

        rendered = self.request.render_tmpl(
            'ptah-intr:ptah-uriresolver', intr,
            manage_url='/ptah-manage', rst_to_html=ptah.rst_to_html)

        self.assertIn('uri-intro-test', rendered)
        self.assertIn('test_intr_renderers', rendered)


class SubscribersIntrospect(ptah.PtahTestCase):

    def test_subscribers(self):
        from ptah.manage.introspect import IntrospectModule

        mod = IntrospectModule(None, self.request)

        intr = mod['ptah:subscriber']

        res = render_view_to_response(intr, self.request)
        self.assertIn('ptah:subscriber', res.text)


class FieldIntrospect(ptah.PtahTestCase):

    def test_fields(self):
        from ptah.manage.introspect import IntrospectModule

        mod = IntrospectModule(None, self.request)

        intr = mod['pform:field']

        res = render_view_to_response(intr, self.request)
        self.assertIn('pform:field', res.text)

########NEW FILE########
__FILENAME__ = test_layout
from pyramid.compat import text_
from pyramid.testing import DummyRequest
from pyramid.httpexceptions import HTTPNotFound

import ptah
import player


class TestLayoutPreview(ptah.PtahTestCase):

    _init_ptah = False

    def test_layout_preview_notfound(self):
        from ptah.manage.layout import layoutPreview

        request = DummyRequest()

        res = layoutPreview(None,request)
        self.assertIsInstance(res, HTTPNotFound)

    def test_layout_preview(self):
        from ptah.manage.layout import layoutPreview

        class Context(object):
            """ """
            __name__ = 'test'

        def View(context, request):
            request.response.text = text_('test body')
            return request.response

        self.init_ptah()

        self.config.add_view(
            name='', context=Context, renderer=player.layout(), view=View)
        self.config.add_layout(
            '', parent='page', context=Context,
            renderer='ptah.manage:tests/test_layout.pt')

        request = DummyRequest()

        res = layoutPreview(Context(), request).text

        #self.assertIn('"python-module": "test_layout"', res)
        #self.assertIn('"renderer": "ptah.manage:tests/test_layout.pt"', res)

########NEW FILE########
__FILENAME__ = test_manage
import ptah
from ptah import config
from ptah.testing import PtahTestCase
from pyramid.testing import DummyRequest
from pyramid.interfaces import IRouteRequest
from pyramid.httpexceptions import HTTPForbidden


class TestManageModule(PtahTestCase):

    _init_ptah = False

    def test_get_manage_url(self):
        from ptah.manage import get_manage_url
        self.init_ptah()

        self.request.application_url = 'http://example.com'
        self.assertEqual(get_manage_url(self.request),
                         'http://example.com/ptah-manage')

        self.request.application_url = 'http://example.com/'
        self.assertEqual(get_manage_url(self.request),
                         'http://example.com/ptah-manage')

        cfg = ptah.get_settings(ptah.CFG_ID_PTAH, self.registry)
        cfg['manage'] = 'manage'

        self.assertEqual(get_manage_url(self.request),
                         'http://example.com/manage')

    def test_manage_module(self):
        from ptah.manage.manage import \
           module, MANAGE_ID, PtahModule, PtahManageRoute,\
           PtahAccessManager, set_access_manager

        @module('test-module')
        class TestModule(PtahModule):
            """ module description """

            title = 'Test module'

        self.init_ptah()

        set_access_manager(PtahAccessManager())

        MODULES = config.get_cfg_storage(MANAGE_ID)
        self.assertIn('test-module', MODULES)

        self.assertRaises(HTTPForbidden, PtahManageRoute, self.request)

        ptah.auth_service.set_userid('test-user')

        self.assertRaises(HTTPForbidden, PtahManageRoute, self.request)

        def accessManager(id, request):
            return True

        set_access_manager(accessManager)

        route = PtahManageRoute(self.request)
        mod = route['test-module']
        self.assertIsInstance(mod, TestModule)
        self.assertTrue(mod.available())
        self.assertEqual(mod.__name__, 'test-module')
        self.assertEqual(mod.url(),'http://example.com/ptah-manage/test-module')

        self.assertRaises(KeyError, route.__getitem__, 'unknown')

    def test_manage_access_manager1(self):
        from ptah.manage.manage import PtahAccessManager
        self.init_ptah()

        cfg = ptah.get_settings(ptah.CFG_ID_PTAH, self.registry)
        cfg['managers'] = ['*']

        self.assertTrue(PtahAccessManager()('test:user', self.request))

        cfg['managers'] = ['admin@ptahproject.org']

        self.assertFalse(PtahAccessManager()('test:user', self.request))

    def test_manage_access_manager2(self):
        from ptah.manage.manage import PtahAccessManager

        class Principal(object):
            id = 'test-user'
            login = 'admin@ptahproject.org'

        principal = Principal()

        @ptah.resolver('test')
        def principalResolver(uri):
            return principal

        self.init_ptah()

        cfg = ptah.get_settings(ptah.CFG_ID_PTAH, self.registry)
        cfg['managers'] = ['admin@ptahproject.org']
        self.assertTrue(PtahAccessManager()('test:user', self.request))

    def test_manage_access_manager_role(self):
        from ptah.manage.manage import PtahAccessManager

        class Principal(object):
            id = 'test-user'
            login = 'admin@ptahproject.org'

        principal = Principal()

        @ptah.resolver('test')
        def principalResolver(uri):
            return principal

        self.init_ptah()

        orig_lr = ptah.get_local_roles

        def get_lr(userid, request, context):
            if userid == 'test:user':
                return ('Manager',)
            return ()

        ptah.get_local_roles = get_lr

        cfg = ptah.get_settings(ptah.CFG_ID_PTAH, self.registry)
        cfg['manager_role'] = 'Manager'

        self.assertTrue(PtahAccessManager()('test:user', self.request))
        self.assertFalse(PtahAccessManager()('test:user2', self.request))

        ptah.get_local_roles = orig_lr

    def test_manage_check_access_no_manager(self):
        self.init_ptah()
        cfg = ptah.get_settings(ptah.CFG_ID_PTAH, self.registry)
        del cfg['access_manager']
        self.assertFalse(ptah.manage.check_access('test:user2', self.request))

    def test_manage_pyramid_directive(self):
        from pyramid.config import Configurator

        config = Configurator(autocommit=True)
        config.include('ptah')

        def access_manager():
            """ """

        config.ptah_init_manage(
            'test-manage',
            access_manager=access_manager,
            managers = ('manager',),
            manager_role = 'Manager',
            disable_modules = ('module',),
            enable_modules = ('module2',))

        cfg = config.ptah_get_settings(ptah.CFG_ID_PTAH)

        self.assertEqual(cfg['manage'], 'test-manage')
        self.assertEqual(cfg['managers'], ('manager',))
        self.assertEqual(cfg['manager_role'], 'Manager')
        self.assertEqual(cfg['disable_modules'], ('module',))
        self.assertEqual(cfg['enable_modules'], ('module2',))
        self.assertIs(cfg['access_manager'], access_manager)

        iface = config.registry.getUtility(IRouteRequest, 'ptah-manage')
        self.assertIsNotNone(iface)

    def test_manage_pyramid_directive_default(self):
        from pyramid.config import Configurator
        from ptah.manage.manage import PtahAccessManager

        config = Configurator(autocommit=True)
        config.include('ptah')

        config.ptah_init_manage('test-manage')

        cfg = config.ptah_get_settings(ptah.CFG_ID_PTAH)
        self.assertIsInstance(cfg['access_manager'], PtahAccessManager)

    def test_manage_view(self):
        from ptah.manage.manage import \
            module, PtahModule, PtahManageRoute, ManageView, \
            set_access_manager

        @module('test-module')
        class TestModule(PtahModule):
            """ module description """

            title = 'Test module'

        def accessManager(id, request):
            return True

        self.init_ptah()

        set_access_manager(accessManager)
        ptah.auth_service.set_userid('test-user')

        route = PtahManageRoute(self.request)

        v = ManageView(route, self.request)
        v.update()

        self.assertIsInstance(v.modules[-1], TestModule)

    def test_manage_view_unavailable(self):
        from ptah.manage.manage import \
            module, PtahModule, PtahManageRoute, ManageView, \
            set_access_manager

        @module('test-module')
        class TestModule(PtahModule):
            """ module description """

            title = 'Test module'

            def available(self):
                return False

        def accessManager(id, request):
            return True

        self.init_ptah()

        set_access_manager(accessManager)
        ptah.auth_service.set_userid('test-user')

        route = PtahManageRoute(self.request)

        v = ManageView(route, self.request)
        v.update()

        found = False
        for mod in v.modules:
            if isinstance(mod, TestModule): # pragma: no cover
                found = True

        self.assertFalse(found)

    def test_manage_traverse(self):
        from ptah.manage.manage import \
            module, PtahModule, PtahManageRoute, set_access_manager

        @module('test-module')
        class TestModule(PtahModule):
            """ module description """

            title = 'Test module'

        def accessManager(id, request):
            return True

        self.init_ptah()

        set_access_manager(accessManager)
        ptah.auth_service.set_userid('test-user')

        route = PtahManageRoute(self.request)

        mod = route['test-module']
        self.assertIsInstance(mod, TestModule)

    def test_manage_enable_modules(self):
        from ptah.manage.manage import \
            module, PtahModule, PtahManageRoute, ManageView, set_access_manager

        @module('test-module1')
        class TestModule1(PtahModule):
            title = 'Test module1'

        @module('test-module2')
        class TestModule2(PtahModule):
            title = 'Test module2'

        def accessManager(id, request):
            return True

        self.init_ptah()

        set_access_manager(accessManager)
        ptah.auth_service.set_userid('test-user')

        cfg = ptah.get_settings(ptah.CFG_ID_PTAH, self.registry)
        cfg['enable_modules'] = ('test-module1',)

        request = DummyRequest()
        route = PtahManageRoute(request)

        view = ManageView(route, request)
        view.update()

        self.assertEqual(len(view.modules), 1)
        self.assertTrue(isinstance(view.modules[0], TestModule1))

        cfg['enable_modules'] = ('test-module2',)

        view = ManageView(route, request)
        view.update()

        self.assertEqual(len(view.modules), 1)
        self.assertTrue(isinstance(view.modules[0], TestModule2))

    def test_manage_enable_modules_traverse(self):
        from ptah.manage.manage import \
            module, PtahModule, PtahManageRoute, set_access_manager

        @module('test-module1')
        class TestModule1(PtahModule):
            title = 'Test module1'

        @module('test-module2')
        class TestModule2(PtahModule):
            title = 'Test module2'

        def accessManager(id, request):
            return True

        self.init_ptah()

        set_access_manager(accessManager)
        ptah.auth_service.set_userid('test-user')

        cfg = ptah.get_settings(ptah.CFG_ID_PTAH, self.registry)
        cfg['enable_modules'] = ('test-module1',)

        request = DummyRequest()
        route = PtahManageRoute(request)

        self.assertIsNotNone(route['test-module1'])
        self.assertRaises(KeyError, route.__getitem__, 'test-module2')

    def test_manage_disable_modules(self):
        from ptah.manage.manage import \
            module, PtahModule, PtahManageRoute, ManageView, set_access_manager

        @module('test-module')
        class TestModule(PtahModule):
            """ module description """

            title = 'Test module'

        def accessManager(id, request):
            return True

        self.init_ptah()

        set_access_manager(accessManager)
        ptah.auth_service.set_userid('test-user')

        cfg = ptah.get_settings(ptah.CFG_ID_PTAH, self.registry)
        cfg['disable_modules'] = ('test-module',)

        request = DummyRequest()
        route = PtahManageRoute(request)

        view = ManageView(route, request)
        view.update()

        for mod in view.modules:
            self.assertFalse(isinstance(mod, TestModule))

    def test_manage_disable_modules_traverse(self):
        from ptah.manage.manage import \
            module, PtahModule, PtahManageRoute, set_access_manager

        @module('test-module')
        class TestModule(PtahModule):
            """ module description """

            title = 'Test module'

        def accessManager(id, request):
            return True

        self.init_ptah()

        set_access_manager(accessManager)
        ptah.auth_service.set_userid('test-user')

        cfg = ptah.get_settings(ptah.CFG_ID_PTAH, self.registry)
        cfg['disable_modules'] = ('test-module',)

        request = DummyRequest()
        route = PtahManageRoute(request)

        self.assertRaises(KeyError, route.__getitem__, 'test-module')

    def test_manage_layout(self):
        from ptah.manage.manage import \
            module, PtahModule, LayoutManage

        @module('test-module')
        class TestModule(PtahModule):
            """ module description """

            title = 'Test module'

        class Content(object):
            __parent__ = None

        self.init_ptah()

        mod = TestModule(None, self.request)
        content = Content()
        content.__parent__ = mod
        self.request.context = content

        layout = LayoutManage(mod, self.request)
        layout.viewcontext = content
        layout.context.userid = ''
        layout.update()

        self.assertIs(layout.module, mod)

########NEW FILE########
__FILENAME__ = test_permissions
import ptah
from ptah.testing import PtahTestCase
from pyramid.testing import DummyRequest
from pyramid.view import render_view_to_response


class TestPermissionsModule(PtahTestCase):

    def test_perms_module(self):
        from ptah.manage.manage import PtahManageRoute
        from ptah.manage.permissions import PermissionsModule

        request = DummyRequest()

        ptah.auth_service.set_userid('test')
        cfg = ptah.get_settings(ptah.CFG_ID_PTAH, self.registry)
        cfg['managers'] = ('*',)
        mr = PtahManageRoute(request)
        mod = mr['permissions']

        self.assertIsInstance(mod, PermissionsModule)

    def test_perms_view(self):
        from ptah.manage.permissions import PermissionsModule

        request = DummyRequest()

        mod = PermissionsModule(None, request)

        res = render_view_to_response(mod, request, '', False)
        self.assertEqual(res.status, '200 OK')

    def test_perms_roles(self):
        from ptah.manage.permissions import PermissionsModule

        request = DummyRequest()

        mod = PermissionsModule(None, request)

        res = render_view_to_response(mod, request, 'roles.html', False)
        self.assertEqual(res.status, '200 OK')
        self.assertIn('<h2>Roles</h2>', res.text)

########NEW FILE########
__FILENAME__ = test_settings
import pform
import ptah
from ptah.testing import PtahTestCase
from pyramid.compat import text_
from pyramid.testing import DummyRequest
from pyramid.view import render_view_to_response
from pyramid.httpexceptions import HTTPFound


class TestSettingsModule(PtahTestCase):

    def test_settings_module(self):
        from ptah.manage.manage import PtahManageRoute
        from ptah.manage.settings import SettingsModule

        request = DummyRequest()

        ptah.auth_service.set_userid('test')
        cfg = ptah.get_settings(ptah.CFG_ID_PTAH, self.registry)
        cfg['managers'] = ('*',)
        mr = PtahManageRoute(request)
        mod = mr['settings']

        self.assertIsInstance(mod, SettingsModule)

    def test_settings_view(self):
        from ptah.manage.settings import SettingsModule, SettingsView

        request = DummyRequest()

        mod = SettingsModule(None, request)
        SettingsView.grps = ('ptah',)
        res = render_view_to_response(mod, request, '', False)
        SettingsView.grps = None
        self.assertEqual(res.status, '200 OK')
        self.assertIn('Ptah settings', text_(res.body))


class TestSettingsTTW(PtahTestCase):

    _init_ptah = False

    def test_traverse_ttw(self):
        from ptah.manage.settings import SettingsModule, SettingsWrapper

        ptah.register_settings(
            'test',
            pform.TextField('node1', default='test1'),
            pform.TextField('node2', default='test2', tint=True),
            title = 'Test settings')

        self.init_ptah()

        grp = ptah.get_settings('test', self.registry)
        mod = SettingsModule(None, self.request)

        self.assertRaises(
            KeyError,
            mod.__getitem__, 'test')

        grp.__ttw__ = True

        tgrp = mod['test']
        self.assertIs(tgrp.group, grp)
        self.assertIsInstance(tgrp, SettingsWrapper)

    def test_edit_form(self):
        from ptah.manage.settings import SettingsModule, EditForm

        ptah.register_settings(
            'test',
            pform.TextField('node1', default='test1', required=False),
            pform.TextField('node2', default='test2', required=False),
            title = 'Test settings',
            ttw = True,
            ttw_skip_fields = ('node2',))

        self.init_ptah()

        mod = SettingsModule(None, self.request)
        grp = mod['test']
        settings = grp.group

        form = EditForm(grp, self.request)

        self.assertEqual(form.label, settings.__title__)
        self.assertEqual(form.description, settings.__description__)
        self.assertIs(form.form_content(), settings)

        fields = form.fields
        self.assertIn('node1', fields)
        self.assertNotIn('node2', fields)

        res = form.back_handler()
        self.assertIsInstance(res, HTTPFound)
        self.assertEqual(res.headers['location'], '..')

        form.update_form()
        form.modify_handler()
        self.assertIn('Settings have been modified.',
                      self.request.render_messages())

########NEW FILE########
__FILENAME__ = test_source
import ptah
from ptah.testing import PtahTestCase
from pyramid.testing import DummyRequest
from pyramid.httpexceptions import HTTPFound
from pyramid.view import render_view_to_response


class TestSourceView(PtahTestCase):

    def test_source(self):
        from ptah.manage.manage import PtahManageRoute

        ptah.auth_service.set_userid(ptah.SUPERUSER_URI)

        request = DummyRequest()
        manage = PtahManageRoute(request)
        res = render_view_to_response(manage, request, 'source.html', False)
        self.assertIsInstance(res, HTTPFound)
        self.assertEqual(res.headers['location'], '.')

    def test_source_view(self):
        from ptah.manage.manage import PtahManageRoute

        ptah.auth_service.set_userid(ptah.SUPERUSER_URI)

        request = DummyRequest(
            params = {'pkg': 'ptah.config'})
        manage = PtahManageRoute(request)
        res = render_view_to_response(manage, request, 'source.html', False)
        self.assertIn('Source: ptah/config.py', res.text)

    def test_source_view_unknown(self):
        from ptah.manage.manage import PtahManageRoute

        ptah.auth_service.set_userid(ptah.SUPERUSER_URI)

        request = DummyRequest(
            params = {'pkg': 'unknown'})
        manage = PtahManageRoute(request)
        res = render_view_to_response(manage, request, 'source.html', False)
        self.assertIsInstance(res, HTTPFound)
        self.assertEqual(res.headers['location'], '.')

########NEW FILE########
__FILENAME__ = test_sqla
import sqlalchemy as sqla
from webob.multidict import MultiDict
from pyramid.testing import DummyRequest
from pyramid.compat import text_type
from pyramid.httpexceptions import HTTPFound
from pyramid.view import render_view_to_response

import ptah
from ptah.testing import PtahTestCase


TestSqlaModuleContent = None


class TestSqlaModuleTable(ptah.get_base()):
    __tablename__ = 'test_sqla_table'
    __table_args__ = {'extend_existing': True}

    id = sqla.Column('id', sqla.Integer, primary_key=True)
    name = sqla.Column(sqla.Unicode(255))


class TestSqlaModuleBase(ptah.get_base()):
    __tablename__ = 'ptah_nodes'
    __table_args__ = {'extend_existing': True}

    id = sqla.Column(sqla.Integer(), primary_key=True)
    name = sqla.Column(sqla.Unicode(), default=text_type('123'))
    title = sqla.Column(sqla.Unicode(), info={'uri':True})


class TestSqlaModule(PtahTestCase):

    def setUp(self):
        global TestSqlaModuleContent

        Base = ptah.get_base()
        ptah.get_session()

        table = Base.metadata.tables['test_sqla_table']
        if not table.exists():
            Base.metadata.create_all(tables=(table,))

        @ptah.tinfo('Test')
        class TestSqlaModuleContent(TestSqlaModuleBase):
            __tablename__ = 'test_sqla_content'
            __table_args__ = {'extend_existing': True}
            __mapper_args__ = {'polymorphic_identity': 'nodes'}

            id = sqla.Column(
                sqla.Integer(),
                sqla.ForeignKey('ptah_nodes.id'), primary_key=True)
            name = sqla.Column(sqla.Unicode())
            title = sqla.Column(sqla.Unicode())

        super(TestSqlaModule, self).setUp()

    def test_sqla_module(self):
        from ptah.manage.manage import PtahManageRoute
        from ptah.manage.sqla import SQLAModule, Table

        request = DummyRequest()

        cfg = ptah.get_settings(ptah.CFG_ID_PTAH, self.registry)
        cfg['managers'] = ['*']
        mr = PtahManageRoute(request)
        mod = mr['sqla']
        self.assertIsInstance(mod, SQLAModule)

        self.assertRaises(KeyError, mod.__getitem__, 'psqla-unknown')
        self.assertRaises(KeyError, mod.__getitem__, 'unknown')

        table = mod['psqla-ptah_tokens']
        self.assertIsInstance(table, Table)

    def test_sqla_traverse(self):
        from ptah.manage.sqla import SQLAModule, Table

        request = DummyRequest()

        mod = SQLAModule(None, request)

        table = mod['psqla-ptah_nodes']
        self.assertIsInstance(table, Table)

        self.assertRaises(KeyError, mod.__getitem__, 'unknown')

    def test_sqla_view(self):
        from ptah.manage.sqla import SQLAModule

        request = self.make_request()

        mod = SQLAModule(None, request)

        res = render_view_to_response(mod, request, '', False)
        self.assertEqual(res.status, '200 OK')

    def test_sqla_table_view(self):
        from ptah.manage.sqla import SQLAModule

        request = self.make_request()

        mod = SQLAModule(None, request)
        table = mod['psqla-ptah_tokens']

        res = render_view_to_response(table, request, '', False)
        self.assertEqual(res.status, '200 OK')
        self.assertIn('form.buttons.add', res.text)

    def test_sqla_table_view_model(self):
        from ptah.manage.sqla import SQLAModule

        ptah.get_session().add(TestSqlaModuleContent(title='test'))

        request = self.make_request()

        mod = SQLAModule(None, request)
        table = mod['psqla-test_sqla_content']

        res = render_view_to_response(table, request, '', False).text
        self.assertIn('Inherits from:', res)
        self.assertIn('ptah_node', res)
        self.assertNotIn('form.buttons.add', res)

    def test_sqla_table_view_model_nodes(self):
        from ptah.manage.sqla import SQLAModule

        rec = TestSqlaModuleContent(title='test')
        ptah.get_session().add(rec)
        ptah.get_session().flush()

        #uri = rec.__uri__
        #type_uri = rec.__type__.__uri__

        request = DummyRequest(params={'batch': 1})

        mod = SQLAModule(None, request)
        table = mod['psqla-ptah_nodes']

        render_view_to_response(table, request, '', False).text
        #self.assertIn(url_quote_plus(uri), res)
        #self.assertIn(url_quote_plus(type_uri), res)

        request = DummyRequest(params={'batch': 'unknown'})
        render_view_to_response(table, request, '', False).text
        #self.assertIn(url_quote_plus(uri), res)

        request = DummyRequest(params={'batch': '0'})
        render_view_to_response(table, request, '', False).text
        #self.assertIn(url_quote_plus(uri), res)

    def test_sqla_table_view_inheritance(self):
        from ptah.manage.sqla import SQLAModule

        request = self.make_request()

        mod = SQLAModule(None, request)
        table = mod['psqla-ptah_tokens']

        res = render_view_to_response(table, request, '', False)
        self.assertEqual(res.status, '200 OK')

    def test_sqla_table_traverse(self):
        from ptah.manage.sqla import SQLAModule, Record
        from ptah.settings import SettingRecord

        inst = SettingRecord(name='test', value='12345')
        ptah.get_session().add(inst)
        ptah.get_session().flush()

        mod = SQLAModule(None, DummyRequest())
        table = mod['psqla-ptah_settings']

        rec = table[str(inst.name)]

        self.assertIsInstance(rec, Record)
        self.assertEqual(rec.pname, 'name')
        self.assertIsNotNone(rec.pcolumn)
        self.assertIsNotNone(rec.data)

        self.assertRaises(KeyError, table.__getitem__, 'add.html')
        self.assertRaises(KeyError, table.__getitem__, 'unknown')

    def test_sqla_table_addrec_basics(self):
        from ptah.manage.sqla import SQLAModule, AddRecord

        request = self.make_request()

        mod = SQLAModule(None, request)
        table = mod['psqla-test_sqla_table']

        form = AddRecord(table, request)
        form.update()

        self.assertEqual(form.label, 'test_sqla_table: new record')

        request = DummyRequest(
            POST={'form.buttons.back': 'Back'})

        form = AddRecord(table, request)
        res = form()

        self.assertIsInstance(res, HTTPFound)
        self.assertEqual(res.headers['location'], '.')

    def test_sqla_table_addrec_create(self):
        from ptah.manage.sqla import SQLAModule, AddRecord

        request = self.make_request()

        mod = SQLAModule(None, request)
        table = mod['psqla-test_sqla_table']

        request = self.make_request(
            POST={'form.buttons.create': 'Create'})

        form = AddRecord(table, request)
        form.csrf = False
        form.update_form()

        self.assertIn('Please fix indicated errors',
                      request.render_messages())

        request = self.make_request(
            POST={'form.buttons.create': 'Create',
                  'name': 'Test'})

        form = AddRecord(table, request)
        form.csrf = False
        res = form()

        self.assertIn('Table record has been created.',
                      request.render_messages())
        self.assertIsInstance(res, HTTPFound)

        rec = ptah.get_session().query(TestSqlaModuleTable).first()
        self.assertEqual(rec.name, 'Test')

    def test_sqla_table_addrec_create_multi(self):
        from ptah.manage.sqla import SQLAModule, AddRecord

        request = self.make_request()

        mod = SQLAModule(None, request)
        table = mod['psqla-test_sqla_table']

        request = self.make_request(
            POST={'form.buttons.createmulti': 'Create'})

        form = AddRecord(table, request)
        form.csrf = False
        form.update_form()

        self.assertIn('Please fix indicated errors',
                      request.render_messages())

        request = self.make_request(
            POST={'form.buttons.createmulti': 'Create',
                  'name': 'Test multi'})

        form = AddRecord(table, request)
        form.csrf = False
        form.update_form()

        self.assertIn('Table record has been created.',
                      request.render_messages())

        rec = ptah.get_session().query(TestSqlaModuleTable).first()
        self.assertEqual(rec.name, 'Test multi')

    def test_sqla_table_editrec_basics(self):
        from ptah.manage.sqla import SQLAModule, EditRecord

        rec = TestSqlaModuleTable()
        rec.name = 'Test record'
        ptah.get_session().add(rec)
        ptah.get_session().flush()

        rec_id = rec.id

        request = self.make_request()

        mod = SQLAModule(None, request)
        table = mod['psqla-test_sqla_table']

        rec = table[rec_id]

        form = EditRecord(rec, request)
        form.update_form()

        self.assertEqual(form.label, 'record 1')
        self.assertEqual(form.form_content(),
                         {'name': 'Test record'})

        request = DummyRequest(
            POST={'form.buttons.cancel': 'Cancel'})

        form = EditRecord(rec, request)
        res = form()

        self.assertIsInstance(res, HTTPFound)
        self.assertEqual(res.headers['location'], '..')

    def test_sqla_table_editrec_modify(self):
        from ptah.manage.sqla import SQLAModule, EditRecord

        rec = TestSqlaModuleTable()
        rec.name = 'Test record'
        ptah.get_session().add(rec)
        ptah.get_session().flush()

        rec_id = rec.id

        mod = SQLAModule(None, DummyRequest())
        table = mod['psqla-test_sqla_table']

        rec = table[rec_id]

        request = self.make_request(
            POST={'form.buttons.modify': 'Modify'})

        form = EditRecord(rec, request)
        form.csrf = False
        form.update_form()

        self.assertIn('Please fix indicated errors',
                      request.render_messages())

        request = self.make_request(
            POST={'form.buttons.modify': 'Modify',
                  'name': 'Record modified'})

        form = EditRecord(rec, request)
        form.csrf = False
        res = form()

        self.assertIn('Table record has been modified.',
                      request.render_messages())
        self.assertIsInstance(res, HTTPFound)
        self.assertEqual(res.headers['location'], '..')

        rec = ptah.get_session().query(TestSqlaModuleTable).filter(
            TestSqlaModuleTable.id == rec_id).first()
        self.assertEqual(rec.name, 'Record modified')

    def test_sqla_table_editrec_remove(self):
        from ptah.manage.sqla import SQLAModule, EditRecord

        rec = TestSqlaModuleTable()
        rec.name = 'Test record'
        ptah.get_session().add(rec)
        ptah.get_session().flush()

        rec_id = rec.id

        mod = SQLAModule(None, DummyRequest())
        table = mod['psqla-test_sqla_table']

        rec = table[rec_id]

        request = self.make_request(
            POST={'form.buttons.remove': 'Remove'})

        form = EditRecord(rec, request)
        form.csrf = False
        res = form()

        self.assertIn('Table record has been removed.',
                      request.render_messages())
        self.assertIsInstance(res, HTTPFound)
        self.assertEqual(res.headers['location'], '..')

        rec = ptah.get_session().query(TestSqlaModuleTable).filter(
            TestSqlaModuleTable.id == rec_id).first()
        self.assertIsNone(rec, None)

    def test_sqla_table_add(self):
        from ptah.manage.sqla import SQLAModule, TableView

        mod = SQLAModule(None, DummyRequest())
        table = mod['psqla-test_sqla_table']

        request = DummyRequest(
            POST={'form.buttons.add': 'Add'})

        form = TableView(table, request)
        res = form()

        self.assertIsInstance(res, HTTPFound)
        self.assertEqual(res.headers['location'], 'add.html')

    def test_sqla_table_remove(self):
        from ptah.manage.sqla import SQLAModule, TableView

        rec = TestSqlaModuleTable()
        rec.name = 'Test record'
        ptah.get_session().add(rec)
        ptah.get_session().flush()

        rec_id = rec.id

        request = self.make_request()
        mod = SQLAModule(None, request)
        table = mod['psqla-test_sqla_table']

        request = self.make_request(
            POST=MultiDict([('form.buttons.remove', 'Remove')]))

        form = TableView(table, request)
        form.csrf = False
        form.update_form()

        self.assertIn('lease select records for removing.',
                      request.render_messages())

        request = self.make_request(
            POST=MultiDict([('form.buttons.remove', 'Remove'),
                            ('rowid', 'wrong')]))

        form = TableView(table, request)
        form.csrf = False
        form.update_form()

        #self.assertIn('Please select records for removing.',
        #              request.render_messages())

        request = self.make_request(
            POST=MultiDict([('form.buttons.remove', 'Remove'),
                            ('rowid', rec_id),
                            ('csrf-token',
                             self.request.session.get_csrf_token())]))

        form = TableView(table, request)
        form.csrf = True
        form.update_form()

        self.assertIn('Select records have been removed.',
                      request.render_messages())

        rec = ptah.get_session().query(TestSqlaModuleTable).filter(
            TestSqlaModuleTable.id == rec_id).first()
        self.assertIsNone(rec, None)

    def test_sqla_table_no_remove_for_edit_model(self):
        from ptah.manage.sqla import SQLAModule, EditRecord

        rec = TestSqlaModuleContent()
        rec.name = 'Test record'
        ptah.get_session().add(rec)
        ptah.get_session().flush()

        rec_id = rec.id

        mod = SQLAModule(None, DummyRequest())
        table = mod['psqla-test_sqla_content']

        rec = table[rec_id]

        form = EditRecord(rec, self.make_request())
        form.update()

        self.assertNotIn('form.buttons.remove', form.render())

########NEW FILE########
__FILENAME__ = test_uri
from ptah.testing import PtahTestCase
from pyramid.testing import DummyRequest


class TestUriView(PtahTestCase):

    _cleanup_mod = False

    def test_uri_view(self):
        from ptah.manage.uri import UriResolver

        request = DummyRequest(
            GET = {'uri': 'ptah-auth:superuser'})

        view = UriResolver(None, request)
        view.update()

        self.assertEqual(view.data[0]['name'],
                         'ptah.authentication.superuser_resolver')

    def test_uri_handler(self):
        from ptah.manage.uri import UriResolver

        request = DummyRequest(
            POST = {'form.buttons.show': 'Show'})

        view = UriResolver(None, request)
        view.update()

        request = DummyRequest(
            POST = {'form.buttons.show': 'Show', 'uri': 'ptah-auth:superuser'})

        view = UriResolver(None, request)
        view.update_form()

        self.assertEqual(view.data[0]['name'],
                         'ptah.authentication.superuser_resolver')

########NEW FILE########
__FILENAME__ = uri
""" uri resolve """
import inspect
import pform
import player
from pyramid.view import view_config

import ptah
from ptah import config
from ptah.uri import ID_RESOLVER
from ptah.manage.manage import PtahManageRoute


@view_config(
    name='uri.html', context=PtahManageRoute,
    renderer=player.layout('ptah-manage:uri.lt'))

class UriResolver(pform.Form):
    """ Uri resolver form """

    fields = pform.Fieldset(
        pform.LinesField(
            'uri',
            title = 'Uri',
            description = "List of uri's",
            klass = 'xxlarge'))

    uri = None
    rst_to_html = staticmethod(ptah.rst_to_html)

    def form_content(self):
        return {'uri': [self.request.GET.get('uri','')]}

    @pform.button2('Show', actype=pform.AC_PRIMARY)
    def show_handler(self, data):
        self.uri = data['uri']

    def update(self):
        uri = self.uri
        if uri is None:
            uri = [self.request.GET.get('uri','')]

        resolvers = config.get_cfg_storage(ID_RESOLVER)

        self.data = data = []
        for u in uri:
            if u:
                schema = ptah.extract_uri_schema(u)
                resolver = resolvers.get(schema)
                info = {'uri': u,
                        'resolver': None,
                        'module': None,
                        'line': None,
                        'obj': None,
                        'cls': None,
                        'clsdoc': None}

                if resolver is not None:
                    info['resolver'] = resolver.__name__
                    info['r_doc'] = ptah.rst_to_html(resolver.__doc__ or '')
                    info['module'] = resolver.__module__
                    info['name'] = '%s.%s'%(
                        resolver.__module__, resolver.__name__)
                    info['line'] = inspect.getsourcelines(resolver)[-1]

                    obj = ptah.resolve(u)
                    info['obj'] = obj

                    if obj is not None:
                        cls = getattr(obj, '__class__', None)
                        info['cls'] = cls
                        info['clsdoc'] = ptah.rst_to_html(
                            getattr(cls, '__doc__', '') or '')

                        if cls is not None:
                            info['clsmod'] = cls.__module__
                            info['clsline'] = inspect.getsourcelines(cls)[-1]

                data.append(info)

########NEW FILE########
__FILENAME__ = migrate
import os
import logging
import sqlalchemy as sqla

import alembic.util
from alembic.script import ScriptDirectory
from alembic.migration import MigrationContext

import ptah
from ptah import config
from pyramid.path import AssetResolver

MIGRATION_ID = 'ptah:migrate'


class Version(ptah.get_base()):

    __tablename__ = 'ptah_db_versions'

    package = sqla.Column(sqla.String(128), primary_key=True)
    version_num = sqla.Column(sqla.String(32), nullable=False)


class ScriptDirectory(ScriptDirectory):

    file_template = "%(rev)s"

    def __init__(self, pkg):
        path = ptah.get_cfg_storage(MIGRATION_ID).get(pkg)
        if path is None:
            raise ValueError("Can't find package.")

        res = AssetResolver(pkg)
        self.dir = res.resolve('ptah:scripts').abspath()
        self.versions = res.resolve(path).abspath()

        if not os.access(self.versions, os.F_OK):
            raise alembic.util.CommandError("Path doesn't exist: %r." % path)


class MigrationContext(MigrationContext):

    pkg_name = ''

    def __init__(self, pkg, dialect, connection, opts):
        self.pkg_name = pkg
        super(MigrationContext, self).__init__(dialect, connection, opts)

    def get_current_rev(self):
        if self.as_sql: # pragma: no cover
            return self._start_from_rev
        else:
            if self._start_from_rev: # pragma: no cover
                raise alembic.util.CommandError(
                    "Can't specify current_rev to context "
                    "when using a database connection")
            Version.__table__.create(checkfirst=True)

        item = ptah.get_session().query(Version.version_num).filter(
            Version.package == self.pkg_name).first()
        return getattr(item, 'version_num', None)

    def _update_current_rev(self, old, new):
        if old == new: # pragma: no cover
            return
        if new is None: # pragma: no cover
            self.impl._exec(Version.__table__.delete().where(
                package=self.pkg_name))
        elif old is None:
            self.impl._exec(
                Version.__table__.insert().
                values(package=self.pkg_name,
                       version_num=sqla.literal_column("'%s'" % new))
                )
        else:
            self.impl._exec(
                Version.__table__.update().
                values(package=self.pkg_name,
                       version_num=sqla.literal_column("'%s'" % new))
                )

    def run_migrations(self, **kw):
        current_rev = rev = False
        log = logging.getLogger('ptah.alembic')
        self.impl.start_migrations()

        for change, prev_rev, rev in \
                self._migrations_fn(self.get_current_rev(), self):
            if current_rev is False:
                current_rev = prev_rev
                if self.as_sql and not current_rev: # pragma: no cover
                    Version.__table__.create(checkfirst=True)

            log.info("%s: running %s %s -> %s",
                     self.pkg_name, change.__name__, prev_rev, rev)
            if self.as_sql: # pragma: no cover
                self.impl.static_output(
                    "-- Running %s %s -> %s"%(change.__name__, prev_rev, rev))

            change(**kw)

            if not self.impl.transactional_ddl: # pragma: no cover
                self._update_current_rev(prev_rev, rev)
            prev_rev = rev

        if rev is not False:
            if self.impl.transactional_ddl:
                self._update_current_rev(current_rev, rev)

            if self.as_sql and not rev: # pragma: no cover
                Version.__table___.drop()


def upgrade(pkg, sql=False):
    """Upgrade to a later version."""
    from alembic.config import Config
    from alembic.environment import EnvironmentContext

    if ':' in pkg:
        pkg, rev = pkg.split(':',1)
    else:
        rev = 'head'

    script = ScriptDirectory(pkg)
    env = EnvironmentContext(Config(''), script)
    conn = ptah.get_base().metadata.bind.connect()

    def upgrade(revision, context):
        return script._upgrade_revs(rev, revision)

    env.configure(
        connection = conn,
        fn = upgrade,
        as_sql = sql,
        starting_rev = None,
        destination_rev = rev,
    )

    mc = env._migration_context
    env._migration_context = MigrationContext(pkg, conn.dialect, conn, mc.opts)

    with env:
        try:
            with env.begin_transaction():
                env.run_migrations()
        finally:
            conn.close()


def revision(pkg, rev=None, message=None):
    """Create a new revision file."""
    script = ScriptDirectory(pkg)
    revs = [sc.revision for sc in script.walk_revisions()]

    if not rev:
        rev = alembic.util.rev_id()

    if rev in revs:
        raise KeyError('Revision already exists')

    return script.generate_revision(rev, message, True).revision


def ptah_migrate(cfg):
    def action(cfg,):
        for pkg in cfg.get_cfg_storage(MIGRATION_ID).keys():
            upgrade(pkg)

    cfg.action('ptah.ptah_migrate', action, (cfg,), order=999999+1)


def register_migration(pkg, path, title='', force=False):
    """Registers a migration for package.
    Check :ref:`data_migration_chapter` chapter for detailed description.

    :param pkg: Package name
    :param path: String implying a path or `asset specification`
        (e.g. ``ptah:migrations``). Path to directory with migration scripts.
    :param title: Optional human readable title.
    :param force: Force execute migration during bootstrap process

    .. code-block:: python

      import ptah

      ptah.register_migration(
          'ptah', 'ptah:migrations', 'Ptah database migration')

    """
    info = config.DirectiveInfo()
    discr = (MIGRATION_ID, pkg)

    intr = config.Introspectable(MIGRATION_ID, discr, pkg, MIGRATION_ID)
    intr['package'] = pkg
    intr['path'] = path
    intr['title'] = title
    intr['force'] = force

    def _complete(cfg, pkg, path):
        cfg.get_cfg_storage(MIGRATION_ID)[pkg] = path

    info.attach(
        config.Action(
            _complete, (pkg, path),
            discriminator=discr, introspectables=(intr,))
        )


def update_versions(registry):
    packages = []
    for item in registry.introspector.get_category(MIGRATION_ID,()):
        intr = item['introspectable']
        if not intr['force']:
            packages.append(intr['package'])

    session = ptah.get_session()

    for pkg in packages:
        item = session.query(Version).filter(Version.package==pkg).first()
        if item is not None:
            continue

        script = ScriptDirectory(pkg)
        revs = [sc for sc in script.walk_revisions()]

        # set head as version
        for sc in revs:
            if sc.is_head:
                session.add(Version(package=pkg, version_num=sc.revision))
                break


def check_version(ev):
    """ ApplicationCreated event handler """
    if not Version.__table__.exists():
        return

    versions = dict((v.package, v.version_num)
                    for v in ptah.get_session().query(Version).all())
    packages = ptah.get_cfg_storage(MIGRATION_ID).keys()

    has_steps = False
    log = logging.getLogger('ptah.alembic')

    for pkg in packages:
        version = versions.get(pkg)
        script = ScriptDirectory(pkg)
        for sc in script.walk_revisions():
            if sc.is_head:
                if sc.revision != version:
                    has_steps = True
                    log.error("Package '%s' current revision: '%s', head: '%s'",
                              pkg, version, sc.revision)
                break

    if has_steps:
        config.shutdown()
        log.error("Please run `ptah-migrate` script. Stopping...")
        raise SystemExit(1)

########NEW FILE########
__FILENAME__ = password
""" password tool """
import pform
import translationstring
from os import urandom
from datetime import timedelta
from codecs import getencoder
from hashlib import sha1
from base64 import urlsafe_b64encode, urlsafe_b64decode
from pyramid.compat import bytes_

import ptah
from ptah import config, token

_ = translationstring.TranslationStringFactory('ptah')


ID_PASSWORD_CHANGER = 'ptah.password:changer'

TOKEN_TYPE = token.TokenType(
    '35c9b7df958f4e93ae9b275a7dc2219e', timedelta(minutes=10),
    'Reset password tokens')


class PlainPasswordManager(object):
    """PLAIN password manager."""

    def encode(self, password, salt=None):
        return '{plain}%s' % password

    def check(self, encoded, password):
        if encoded != password:
            return encoded == '{plain}%s' % password
        return True


class SSHAPasswordManager(object):
    """SSHA password manager."""

    _encoder = getencoder("utf-8")

    def encode(self, password, salt=None):
        if salt is None:
            salt = urandom(4)
        hash = sha1(self._encoder(password)[0])
        hash.update(salt)
        return bytes_('{ssha}','ascii') + urlsafe_b64encode(hash.digest()+salt)

    def check(self, encoded_password, password):
        # urlsafe_b64decode() cannot handle unicode input string. We
        # encode to ascii. This is safe as the encoded_password string
        # should not contain non-ascii characters anyway.
        encoded_password = bytes_(encoded_password, 'ascii')
        byte_string = urlsafe_b64decode(encoded_password[6:])
        salt = byte_string[20:]
        return encoded_password == self.encode(password, salt)


class PasswordTool(object):
    """ Password management utility. """

    pm = {'{plain}': PlainPasswordManager(),
          '{ssha}': SSHAPasswordManager(),
          }

    @property
    def manager(self):
        PWD_CONFIG = ptah.get_settings(ptah.CFG_ID_PTAH)
        try:
            return self.pm['{%s}' % PWD_CONFIG['pwd_manager']]
        except KeyError:
            return self.pm['{plain}']

    def check(self, encoded, password):
        """ Compare encoded password with plain password.

        :param encoded: Encoded password
        :param password: Plain password
        """
        try:
            pm, pwd = encoded.split('}', 1)
        except:
            return self.manager.check(encoded, password)

        manager = self.pm.get('%s}' % pm)
        if manager is not None:
            return manager.check(encoded, password)
        return False

    def encode(self, password, salt=None):
        """ Encode password with current password manager """
        return self.manager.encode(password, salt)

    def can_change_password(self, principal):
        """ Can principal password be changed.
        :py:class:`ptah.password_changer` is beeing used. """
        return ptah.extract_uri_schema(principal.__uri__) in \
            config.get_cfg_storage(ID_PASSWORD_CHANGER)

    def get_principal(self, passcode):
        """ Return principal by previously generated passcode. """
        data = token.service.get(passcode)

        if data is not None:
            return ptah.resolve(data)

    def generate_passcode(self, principal):
        """ Generate passcode for principal.

        :param principal: Principal object
        """
        return token.service.generate(TOKEN_TYPE, principal.__uri__)

    def remove_passcode(self, passcode):
        """ Remove passcode """
        token.service.remove(passcode)

    def change_password(self, passcode, password):
        """ Encode and change password.
        :py:class:`ptah.password_changer` is beeing used.

        :param passcode: Previously generated passcode
        :param passsword: Plain password.
        :rtype: True if password has been changed, False otherwise.
        """
        principal = self.get_principal(passcode)

        self.remove_passcode(passcode)

        if principal is not None:
            changers = config.get_cfg_storage(ID_PASSWORD_CHANGER)

            changer = changers.get(ptah.extract_uri_schema(principal.__uri__))
            if changer is not None:
                changer(principal, self.encode(password))
                return True

        return False

    def validate(self, password):
        """ Validate password """
        PWD_CONFIG = ptah.get_settings(ptah.CFG_ID_PTAH)

        if len(password) < PWD_CONFIG['pwd_min_length']:
            #return _('Password should be at least ${count} characters.',
            #         mapping={'count': self.min_length})
            return 'Password should be at least %s characters.' % \
                PWD_CONFIG['pwd_min_length']
        elif PWD_CONFIG['pwd_letters_digits'] and \
                (password.isalpha() or password.isdigit()):
            return _('Password should contain both letters and digits.')
        elif PWD_CONFIG['pwd_letters_mixed_case'] and \
                (password.isupper() or password.islower()):
            return _('Password should contain letters in mixed case.')


pwd_tool = PasswordTool()


class password_changer(object):
    """ Register password changer function.

    :param schema: Principal uri schema.

    .. code-block:: python

      @ptah.password_change('myuser')
      def change_password(principal, password):
          principal.password = password

    """
    def __init__(self, schema, __depth=1):
        self.info = config.DirectiveInfo(__depth)
        self.discr = (ID_PASSWORD_CHANGER, schema)

        self.intr = config.Introspectable(
            ID_PASSWORD_CHANGER, self.discr, schema, ID_PASSWORD_CHANGER)
        self.intr['schema'] = schema

    def __call__(self, changer, cfg=None):
        self.intr.title = changer.__doc__
        self.intr['callable'] = changer

        self.info.attach(
            config.Action(
                lambda config, schema, changer: \
                    config.get_cfg_storage(ID_PASSWORD_CHANGER).update(
                            {schema: changer}),
                (self.intr['schema'], changer),
                discriminator=self.discr, introspectables=(self.intr,)),
            cfg)
        return changer

    @classmethod
    def pyramid(cls, cfg, schema, changer):
        """ pyramid password changer registration directive.

        :param schema: Principal uri schema.
        :param changer: Function

        .. code-block:: python

          config = Configurator()
          config.include('ptah')

          config.ptah_password_changer('custom-schema', custom_changer)
        """
        cls(schema, 3)(changer, cfg)


def passwordValidator(field, value):
    """ password schema validator
    that uses password tool for additional checks"""
    if value is not pform.null:
        err = pwd_tool.validate(value)
        if err is not None:
            raise pform.Invalid(err, field)


def passwordSchemaValidator(field, appstruct):
    """ password schema validator that checks
    equality of password and confirm_password"""
    if appstruct['password'] and appstruct['confirm_password']:
        if appstruct['password'] != appstruct['confirm_password']:
            raise pform.Invalid(
                _("Password and Confirm Password should be the same."), field)

        passwordValidator(field, appstruct['password'])


PasswordSchema = pform.Fieldset(

    pform.FieldFactory(
        'password',
        'password',
        title = _('Password'),
        description = _('Enter password. '\
                        'No spaces or special characters, should contain '\
                        'digits and letters in mixed case.'),
        default = ''),

    pform.FieldFactory(
        'password',
        'confirm_password',
        title = _('Confirm password'),
        description = _('Re-enter the password. '
                        'Make sure the passwords are identical.'),
        default = ''),

    validator = passwordSchemaValidator
)

########NEW FILE########
__FILENAME__ = populate
""" populate data """
import logging
import transaction
from pyramid.request import Request
from pyramid.interfaces import IRequestFactory
from pyramid.threadlocal import manager as threadlocal_manager

import ptah
from ptah import config
from ptah.migrate import update_versions

POPULATE_ID = 'ptah:populate-step'
POPULATE_DB_SCHEMA = 'ptah-db-schema'


class populate(object):
    """Registers a data populate step. Populate steps are used by
    :ref:`data_populate_script` command line tool and by
    :ref:`ptah_populate_dir` pyramid directive for populate system data.

    :param name: Unique step name
    :param title: Human readable title
    :param active: Should this step automaticly executed or not
    :param requires: List of steps that should be executed before this step

    Populate step interface :py:class:`ptah.interfaces.populate_step`.
    Steps are executed after configuration is completed.

    .. code-block:: python

       import ptah

       @ptah.populate('custom-user',
                      title='Create custom user',
                      requires=(ptah.POPULATE_DB_SCHEMA,))
       def create_custom_user(registry):
           # create user

    ``create_custom_user`` executes only after ``ptah.POPULATE_DB_SCHEMA`` step.

    Perpose of inactive steps is for example entering testing data or executing
    custom step.
    """

    def __init__(self, name, title='', active=True, requires=(), __depth=1):
        self.info = config.DirectiveInfo(__depth)
        self.discr = (POPULATE_ID, name)

        self.intr = intr = config.Introspectable(
            POPULATE_ID, self.discr, name, POPULATE_ID)

        intr['name'] = name
        intr['title'] = title
        intr['active'] = active
        intr['requires'] = requires
        intr['codeinfo'] = self.info.codeinfo

    @classmethod
    def pyramid(cls, cfg, name, factory=None,
                title='', active=True, requires=()):
        """ Pyramid `ptah_populate_step` directive:

        .. code-block:: python

          config = Configurator()
          config.include('ptah')

          config.ptah_populate_step('ptah-create-db-schema', factory=..)
        """
        populate(name, title, active, requires, 3)(factory, cfg)

    def __call__(self, factory, cfg=None):
        intr = self.intr
        intr['factory'] = factory

        self.info.attach(
            config.Action(
                lambda cfg, name, intr:
                    cfg.get_cfg_storage(POPULATE_ID).update({name: intr}),
                (intr['name'], intr),
                   discriminator=self.discr, introspectables=(intr,)),
            cfg)
        return factory


class Populate(object):

    def __init__(self, registry):
        self.registry = registry

    def list_steps(self, p_steps=None, all=False):
        seen = set()

        steps = dict(
            (name, intr) for name, intr in
            ptah.get_cfg_storage(POPULATE_ID, self.registry).items())

        sorted_steps = []
        def _step(name, step):
            if name in seen:
                return

            seen.add(name)

            for dep in step['requires']:
                if dep not in steps:
                    raise RuntimeError(
                        "Can't find populate step '{0}'.".format(dep))
                _step(dep, steps[dep])

            sorted_steps.append(step)

        if p_steps is not None:
            for name in p_steps:
                if name not in steps:
                    raise RuntimeError(
                        "Can't find populate step '{0}'.".format(name))

                _step(name, steps[name])
        else:
            for name, step in steps.items():
                if all:
                    _step(name, step)
                elif step['active']:
                    _step(name, step)

        return sorted_steps

    def execute(self, p_steps=None, request=None):
        registry = self.registry
        if request is None:
            request_factory = registry.queryUtility(
                IRequestFactory, default=Request)
            request = request_factory.blank('/')
            request.registry = registry

        threadlocals = {'registry':registry, 'request':request}
        threadlocal_manager.push(threadlocals)

        steps = self.list_steps(p_steps)

        log = logging.getLogger('ptah')

        for step in steps:
            log.info('Executing populate step: %s', step['name'])
            step['factory'](registry)

        transaction.commit()
        threadlocal_manager.pop()


@populate(POPULATE_DB_SCHEMA, title='Create db schema')
def create_db_schema(registry, update=True):
    registry.notify(ptah.events.BeforeCreateDbSchema(registry))

    skip_tables = ptah.get_settings(ptah.CFG_ID_PTAH)['db_skip_tables']

    Base = ptah.get_base()

    log = logging.getLogger('ptah')

    tables = []
    for name, table in Base.metadata.tables.items():
        if name not in skip_tables and not table.exists():
            log.info("Creating db table `%s`.", name)
            tables.append(table)

    if tables:
        Base.metadata.create_all(tables=tables)
        transaction.commit()

    # update db versions
    if update:
        update_versions(registry)

########NEW FILE########
__FILENAME__ = ptahsettings
""" ptah settings """
import pytz
import logging
import sqlalchemy
import translationstring
import pform
from email.utils import formataddr
from pyramid.events import ApplicationCreated

import ptah
from ptah import settings

_ = translationstring.TranslationStringFactory('ptah')

log = logging.getLogger('ptah')


ptah.register_settings(
    ptah.CFG_ID_PTAH,

    pform.BoolField(
        'auth',
        title = _('Authentication policy'),
        description = _('Enable authentication policy.'),
        default = False),

    pform.TextField(
        'secret',
        title = _('Authentication policy secret'),
        description = _('The secret (a string) used for auth_tkt '
                        'cookie signing'),
        default = '',
        tint = True),

    pform.TextField(
        'manage',
        title = 'Ptah manage id',
        default = 'ptah-manage'),

    pform.LinesField(
        'managers',
        title = 'Manage login',
        description = 'List of user logins with access rights to '\
                            'ptah management ui.',
        default = ()),

    pform.TextField(
        'manager_role',
        title = 'Manager role',
        description = 'Specific role with access rights to ptah management ui.',
        default = ''),

    pform.LinesField(
        'disable_modules',
        title = 'Hide Modules in Management UI',
        description = 'List of modules names to hide in manage ui',
        default = ()),

    pform.LinesField(
        'enable_modules',
        title = 'Enable Modules in Management UI',
        description = 'List of modules names to enable in manage ui',
        default = ()),

    pform.LinesField(
        'disable_models',
        title = 'Hide Models in Model Management UI',
        description = 'List of models to hide in model manage ui',
        default = ()),

    pform.TextField(
        'email_from_name',
        default = 'Site administrator'),

    pform.TextField(
        'email_from_address',
        validator = pform.Email(),
        required = False,
        default = 'admin@localhost'),

    pform.ChoiceField(
        'pwd_manager',
        title = 'Password manager',
        description = 'Available password managers '\
            '("plain", "ssha", "bcrypt")',
        vocabulary = pform.Vocabulary(
            "plain", "ssha",),
        default = 'plain'),

    pform.IntegerField(
        'pwd_min_length',
        title = 'Length',
        description = 'Password minimium length.',
        default = 5),

    pform.BoolField(
        'pwd_letters_digits',
        title = 'Letters and digits',
        description = 'Use letters and digits in password.',
        default = False),

    pform.BoolField(
        'pwd_letters_mixed_case',
        title = 'Letters mixed case',
        description = 'Use letters in mixed case.',
        default = False),

    pform.LinesField(
        'db_skip_tables',
        title = 'Skip table creation',
        description = 'Do not create listed tables during data population.',
        default = ()),

    pform.LinesField(
        'default_roles',
        title = 'Default roles',
        description = 'List of default assigned roles for all principals.',
        default = ()),

    pform.TextField(
        name = 'site_title',
        title = _('Site title'),
        description = _('Title of your site.'),
        default = 'Ptah'),

    title = _('Ptah settings'),
)


ptah.register_settings(
    ptah.CFG_ID_FORMAT,

    pform.TimezoneField(
        'timezone',
        default = pytz.timezone('US/Central'),
        title = _('Timezone'),
        description = _('Site wide timezone.')),

    pform.TextField(
        'date_short',
        default = '%m/%d/%y',
        title = _('Date'),
        description = _('Date short format')),

    pform.TextField(
        'date_medium',
        default = '%b %d, %Y',
        title = _('Date'),
        description = _('Date medium format')),

    pform.TextField(
        'date_long',
        default = '%B %d, %Y',
        title = _('Date'),
        description = _('Date long format')),

    pform.TextField(
        'date_full',
        default = '%A, %B %d, %Y',
        title = _('Date'),
        description = _('Date full format')),

    pform.TextField(
        'time_short',
        default = '%I:%M %p',
        title = _('Time'),
        description = _('Time short format')),

    pform.TextField(
        'time_medium',
        default = '%I:%M %p',
        title = _('Time'),
        description = _('Time medium format')),

    pform.TextField(
        'time_long',
        default = '%I:%M %p %z',
        title = _('Time'),
        description = _('Time long format')),

    pform.TextField(
        'time_full',
        default = '%I:%M:%S %p %Z',
        title = _('Time'),
        description = _('Time full format')),

    title = 'Site formats',
    )


def set_mailer(cfg, mailer):
    def action(cfg, mailer):
        PTAH = ptah.get_settings(ptah.CFG_ID_PTAH, cfg.registry)
        PTAH['Mailer'] = mailer

    cfg.action('ptah.ptah_mailer', action, (cfg, mailer))


class DummyMailer(object):

    def send(self, from_, to_, message):
        log.warning("Mailer is not configured.")
        log.warning(message)


@ptah.subscriber(ptah.events.SettingsInitializing)
def initialized(ev):
    PTAH = ptah.get_settings(ptah.CFG_ID_PTAH, ev.registry)

    # mail
    if PTAH.get('Mailer') is None:
        PTAH['Mailer'] = DummyMailer()
        PTAH['full_email_address'] = formataddr(
            (PTAH['email_from_name'], PTAH['email_from_address']))


def enable_manage(cfg, name='ptah-manage', access_manager=None,
                  managers=None, manager_role=None,
                  disable_modules=None, enable_modules=None):
    """Implementation for pyramid `ptah_init_manage` directive """
    def action(cfg, name, access_manager,
               managers, manager_role, disable_modules):
        PTAH = cfg.ptah_get_settings(ptah.CFG_ID_PTAH)

        PTAH['manage'] = name
        if managers is not None:
            PTAH['managers'] = managers
        if manager_role is not None:
            PTAH['manager_role'] = manager_role
        if disable_modules is not None:
            PTAH['disable_modules'] = disable_modules
        if enable_modules is not None:
            PTAH['enable_modules'] = enable_modules

        if access_manager is None:
            access_manager = ptah.manage.PtahAccessManager(cfg.registry)

        ptah.manage.set_access_manager(access_manager, cfg.registry)

    cfg.add_route('ptah-manage', '/{0}/*traverse'.format(name),
                  factory=ptah.manage.PtahManageRoute, use_global_views=True)
    cfg.action(
        'ptah.ptah_manage', action,
        (cfg, name, access_manager,
         managers, manager_role, disable_modules), order=999999+1)


def initialize_sql(cfg, prefix='sqlalchemy.'):
    def action(cfg, cache):
        PTAH = cfg.ptah_get_settings(ptah.CFG_ID_PTAH)
        PTAH['sqlalchemy_cache'] = {}
        PTAH['sqlalchemy_initialized'] = True

    cache = {}
    engine = sqlalchemy.engine_from_config(
        cfg.registry.settings, prefix,
        execution_options = {'compiled_cache': cache, 'echo': True})

    ptah.get_session().configure(bind=engine)
    ptah.get_session_maker().configure(bind=engine)
    ptah.get_base().metadata.bind = engine

    cfg.action('ptah.initalize_sql', action, (cfg, cache))

    # check_version
    from ptah import migrate
    cfg.add_subscriber(migrate.check_version, ApplicationCreated)


@ptah.subscriber(ApplicationCreated)
def starting(ev):
    settings.load_dbsettings()

########NEW FILE########
__FILENAME__ = rst
import os.path
import logging
import tempfile
import threading
from pyramid.compat import text_type, bytes_

try:
    from docutils import io
    from docutils.core import Publisher

    from sphinx.application import Sphinx
    from sphinx.writers.html import HTMLWriter, HTMLTranslator

    has_sphinx = True
    tempdir = tempfile.mkdtemp()
    tmp = open(os.path.join(tempdir, 'conf.py'), 'wb')
    tmp.write(bytes_('# -*- coding: utf-8 -*-'))
    tmp.close()
except ImportError: # pragma: no cover
    has_sphinx = False


log = logging.getLogger('ptah.rst')
local_data = threading.local()


def get_sphinx():
    sphinx = getattr(local_data, 'sphinx', None)
    if sphinx is None:
        sphinx = Sphinx(tempdir, tempdir, tempdir,
                        tempdir, 'json', status=None, warning=None)
        sphinx.builder.translator_class = CustomHTMLTranslator

        sphinx.env.patch_lookup_functions()
        sphinx.env.temp_data['docname'] = 'text'
        sphinx.env.temp_data['default_domain'] = 'py'

        pub = Publisher(reader=None,
                        parser=None,
                        writer=HTMLWriter(sphinx.builder),
                        source_class=io.StringInput,
                        destination_class=io.NullOutput)
        pub.set_components('standalone', 'restructuredtext', None)
        pub.process_programmatic_settings(None, sphinx.env.settings, None)
        pub.set_destination(None, None)

        sphinx.publisher = pub

        local_data.sphinx = sphinx

    return sphinx, sphinx.publisher


def rst_to_html(text):
    if not isinstance(text, text_type):
        text = text_type(text)

    if not has_sphinx: # pragma: no cover
        return '<pre>%s</pre>' % text if text else ''

    sphinx, pub = get_sphinx()

    pub.set_source(text, None)

    try:
        pub.publish()
    except:
        log.warning('ReST to HTML error\n %s', text)
        return '<pre>%s</pre>' % text

    doctree = pub.document
    sphinx.env.filter_messages(doctree)
    for domain in sphinx.env.domains.values():
        domain.process_doc(sphinx.env, 'text', doctree)

    pub.writer.write(doctree, io.StringOutput(encoding='unicode'))
    pub.writer.assemble_parts()

    parts = pub.writer.parts
    return ''.join((parts['body_pre_docinfo'],
                    parts['docinfo'], parts['body']))


if has_sphinx:
    class CustomHTMLTranslator(HTMLTranslator):

        def visit_pending_xref(self, node):
            pass

        def depart_pending_xref(self, node):
            pass

########NEW FILE########
__FILENAME__ = manage
""" ptah-manage command """
from __future__ import print_function
import sys
import argparse
import textwrap

import ptah
from ptah import scripts
from ptah.manage.manage import MANAGE_ID


grpTitleWrap = textwrap.TextWrapper(
    initial_indent='* ',
    subsequent_indent='  ')

grpDescriptionWrap = textwrap.TextWrapper(
    initial_indent='    ',
    subsequent_indent='    ')


def main(init=True):
    args = ManageCommand.parser.parse_args()

    # bootstrap pyramid
    if init: # pragma: no cover
        scripts.bootstrap(args.config)

    cmd = ManageCommand(args)
    cmd.run()

    ptah.shutdown()


class ManageCommand(object):

    parser = argparse.ArgumentParser(description="ptah manage")
    parser.add_argument('config', metavar='config',
                        help='ini config file')
    parser.add_argument('--list-modules', action="store_true",
                        dest='modules',
                        help='List ptah management modules')

    parser.add_argument('--list-models', action="store_true",
                        dest='models',
                        help='List ptah models')

    def __init__(self, args):
        self.options = args

    def run(self):
        print ('')
        if self.options.modules:
            self.list_modules()
        elif self.options.models:
            self.list_models()
        else:
            self.parser.print_help()

    def list_modules(self):
        cfg = ptah.get_settings(ptah.CFG_ID_PTAH)
        disabled = cfg['disable_modules']

        mods = []
        for name, mod in ptah.get_cfg_storage(MANAGE_ID).items():
            mods.append(
                 {'id': name,
                  'title': mod.title,
                  'description': mod.__doc__,
                  'disabled': name in disabled})

        for mod in sorted(mods, key=lambda item:item['id']):
            print (grpTitleWrap.fill(
                    '{id}: {title} (disabled: {disabled})'.format(**mod)))
            print (grpDescriptionWrap.fill(mod['description']))
            print ('\n')

    def list_models(self):
        cfg = ptah.get_settings(ptah.CFG_ID_PTAH)
        disabled = cfg['disable_models']

        types = []
        for ti in ptah.get_types().values():
            types.append(
                {'name': ti.__uri__,
                 'title': ti.title,
                 'description': ti.description,
                 'disabled': ti.__uri__ in disabled,
                 'cls': ti.cls})

        for ti in sorted(types, key=lambda item:item['name']):
            print (grpTitleWrap.fill(
                    '{name}: {title} (disabled: {disabled})'.format(**ti)))
            if ti['description']:
                print (grpDescriptionWrap.fill(ti['description']))
            print('')

            cls = ti['cls']
            print(grpDescriptionWrap.fill('class: {0}'.format(cls.__name__)))
            print(grpDescriptionWrap.fill('module: {0}'.format(cls.__module__)))
            print('    file: ', sys.modules[cls.__module__].__file__)
            print('\n')

########NEW FILE########
__FILENAME__ = migrate
""" ptah-migrate command """
from __future__ import print_function
import argparse
import textwrap
from alembic.config import Config
from alembic.environment import EnvironmentContext
from pyramid.path import AssetResolver

import ptah
import ptah.migrate
from ptah import scripts
from ptah.populate import create_db_schema
from ptah.migrate import upgrade, revision
from ptah.migrate import MigrationContext, MIGRATION_ID


def main():
    parser = argparse.ArgumentParser(description="ptah migrate")
    parser.add_argument('config', metavar='config',
                        help='ini config file')

    subparsers = parser.add_subparsers()

    # revision
    subparser = subparsers.add_parser(
        revision.__name__,
        help=revision.__doc__)
    subparser.add_argument('package', metavar='package',
                           help='package name')
    subparser.add_argument("-r", "--revision",
                           type=str, dest='revid',
                           help="Unique revision id")
    subparser.add_argument("-m", "--message",
                           type=str, dest='message',
                           help="Message string to use with 'revision'")
    subparser.set_defaults(cmd='revision')

    # current
    subparser = subparsers.add_parser(
        current.__name__,
        help=current.__doc__)
    subparser.add_argument('package', metavar='package',
                           nargs='*', help='package name')
    subparser.set_defaults(cmd='current')

    # upgrade
    subparser = subparsers.add_parser(
        upgrade.__name__,
        help=upgrade.__doc__)
    subparser.add_argument('package', metavar='package',
                           nargs='*', help='package name')
    subparser.set_defaults(cmd='upgrade')

    # history
    subparser = subparsers.add_parser(
        history.__name__,
        help=history.__doc__)
    subparser.add_argument('package', metavar='package',
                           nargs='*', help='package name')
    subparser.set_defaults(cmd='history')

    # list
    subparser = subparsers.add_parser(
        'list', help='List registered migrations.')
    subparser.set_defaults(cmd='list')

    # parse
    args = parser.parse_args()

    # bootstrap pyramid
    env = scripts.bootstrap(args.config)

    if args.cmd == 'current':
        print ('')
        if not args.package:
            args.package = ptah.get_cfg_storage(MIGRATION_ID).keys()

        for pkg in args.package:
            current(pkg)

    if args.cmd == 'revision':
        if args.revid:
            for ch in ',.;-':
                if ch in args.revid:
                    print ('Revision id contains forbidden characters')
                    ptah.shutdown()
                    return

        revision(args.package, args.revid, args.message)

    if args.cmd == 'upgrade':
        # create db schemas
        create_db_schema(env['registry'], False)

        for pkg in args.package:
            upgrade(pkg)

    if args.cmd == 'history':
        if not args.package:
            args.package = ptah.get_cfg_storage(MIGRATION_ID).keys()

        for pkg in args.package:
            history(pkg)

    if args.cmd == 'list':
        list_migrations(env['registry'])

    ptah.shutdown()


def history(pkg):
    """List changeset scripts in chronological order."""
    script = ptah.migrate.ScriptDirectory(pkg)
    print('')
    print (pkg)
    print ('='*len(pkg))
    for sc in script.walk_revisions():
        print('{0}: {1}'.format(sc.revision, sc.doc))


def current(pkg):
    """Display the current revision."""

    def display_version(rev, context):
        rev = script._get_rev(rev)
        if rev is None:
            print ("Package '{0}' rev: None".format(pkg))
        else:
            print ("Package '{0}' rev: {1}{2} {3}".format(
                    pkg, rev.revision, '(head)' if rev.is_head else "",rev.doc))
        return []

    conn = ptah.get_base().metadata.bind.connect()

    script = ptah.migrate.ScriptDirectory(pkg)
    env = EnvironmentContext(Config(''), script)
    env.configure(connection=conn, fn=display_version)

    mc = env._migration_context
    env._migration_context = MigrationContext(pkg, conn.dialect, conn, mc.opts)

    with env.begin_transaction():
        env.run_migrations()


def list_migrations(registry):
    print ('')
    wrpTitle = textwrap.TextWrapper(
        initial_indent='* ',
        subsequent_indent='  ')

    wrpDesc = textwrap.TextWrapper(
        initial_indent='    ',
        subsequent_indent='    ')

    res = []
    for item in registry.introspector.get_category(MIGRATION_ID):
        intr = item['introspectable']
        res.append((intr['package'], intr['title'], intr['path']))

    for pkg, title, path in sorted(res):
        res = AssetResolver(pkg)
        print (wrpTitle.fill('{0}: {1}'.format(pkg, title)))
        print (wrpDesc.fill(path))
        print (wrpDesc.fill(res.resolve(path).abspath()))
        print ('')

########NEW FILE########
__FILENAME__ = populate
from __future__ import print_function
import argparse
import textwrap

import ptah
from ptah import scripts
from ptah.populate import Populate


def main():
    parser = argparse.ArgumentParser(description="ptah populate")
    parser.add_argument('config', metavar='config',
                        help='ini config file')
    parser.add_argument('step', metavar='step', nargs='*',
                        help='list of populate steps')
    parser.add_argument('-l', action="store_true", dest='list',
                        help='list of registered populate steps')
    parser.add_argument('-a', action="store_true", dest='all',
                        help='execute all active populate steps')
    args = parser.parse_args()

    env = scripts.bootstrap(args.config)

    populate = Populate(env['registry'])

    if args.list:
        titleWrap = textwrap.TextWrapper(
            initial_indent='* ',
            subsequent_indent='  ')

        descWrap = textwrap.TextWrapper(
            initial_indent='    ',
            subsequent_indent='    ')

        print('')

        for step in sorted(populate.list_steps(all=True),
                           key=lambda i:i['name']):
            print(titleWrap.fill('{0}: {1} ({2})'.format(
                        step['name'], step['title'],
                        'active' if step['active'] else 'inactive')))
            if step['factory'].__doc__:
                print(descWrap.fill(step['factory'].__doc__))

            print('')
    elif args.all:
        populate.execute()
    elif args.step:
        populate.execute(args.step)
    else:
        parser.print_help()

    ptah.shutdown()

########NEW FILE########
__FILENAME__ = settings
""" ptah-settings command """
import argparse
import textwrap

from collections import OrderedDict
from pyramid.compat import configparser, NativeIO

import ptah
from ptah import config, scripts
from ptah.settings import SETTINGS_OB_ID
from ptah.settings import ID_SETTINGS_GROUP


grpTitleWrap = textwrap.TextWrapper(
    initial_indent='* ',
    subsequent_indent='  ')

grpDescriptionWrap = textwrap.TextWrapper(
    initial_indent='    ',
    subsequent_indent='    ')

nameWrap = textwrap.TextWrapper(
    initial_indent='  - ',
    subsequent_indent='    ')

nameTitleWrap = textwrap.TextWrapper(
    initial_indent='       ',
    subsequent_indent='       ')

nameDescriptionWrap = textwrap.TextWrapper(
    initial_indent=' * ',
    subsequent_indent='')


def main(init=True):
    args = SettingsCommand.parser.parse_args()

    # bootstrap pyramid
    if init: # pragma: no cover
        scripts.bootstrap(args.config)

    cmd = SettingsCommand(args)
    cmd.run()

    ptah.shutdown()


class SettingsCommand(object):
    """ 'settings' command"""

    parser = argparse.ArgumentParser(description="ptah settings management")
    parser.add_argument('config', metavar='config',
                        help='Config file')
    parser.add_argument('-a', '--all', action="store_true",
                        dest='all',
                        help='List all registered settings')
    parser.add_argument('-l', '--list',
                        dest='section', default='',
                        help='List registered settings')
    parser.add_argument('-p', '--print', action="store_true",
                        dest='printcfg',
                        help='Print default settings in ConfigParser format')

    def __init__(self, args):
        self.config = config
        self.options = args

    def run(self):
        # print defaults
        if self.options.printcfg:
            data = config.get_cfg_storage(SETTINGS_OB_ID).export(True)

            parser = configparser.ConfigParser(dict_type=OrderedDict)
            for key, val in sorted(data.items()):
                parser.set(configparser.DEFAULTSECT,
                           key, val.replace('%', '%%'))

            fp = NativeIO()
            try:
                parser.write(fp)
            finally:
                pass

            print (fp.getvalue())
            return

        if self.options.all:
            section = ''
        else:
            section = self.options.section

        # print description
        groups = sorted(config.get_cfg_storage(ID_SETTINGS_GROUP).items(),
                        key = lambda item: item[1].__title__)

        for name, group in groups:
            if section and name != section:
                continue

            print ('')
            title = group.__title__ or name

            print (grpTitleWrap.fill('{0} ({1})'.format(title, name)))
            if group.__description__:
                print (grpDescriptionWrap.fill(
                    group.__description__))

            print ('')
            for node in group.__fields__.values():
                default = '<required>' if node.required else node.default
                print (nameWrap.fill(
                    ('%s.%s: %s (%s: %s)' % (
                        name, node.name, node.title,
                        node.__class__.__name__, default))))

                print (nameTitleWrap.fill(node.description))
                print ('')

########NEW FILE########
__FILENAME__ = test_bootstrap
import unittest
from pyramid.registry import Registry


class Test_bootstrap(unittest.TestCase):

    def setUp(self):
        import ptah.scripts
        import pyramid.paster
        self.original_get_app = ptah.scripts.get_app
        self.original_global_registries = ptah.scripts.global_registries

        self.app = app = object()
        self.registry = registry = Registry()

        class DummyGetApp(object):

            last = registry

            def __call__(self, *a, **kw):
                self.a = a
                self.kw = kw
                return app

        pyramid.paster.get_app = DummyGetApp()
        ptah.scripts.global_registries = DummyGetApp()

    def tearDown(self):
        import ptah.scripts
        import pyramid.paster
        pyramid.paster.get_app = self.original_get_app
        ptah.scripts.global_registries = self.original_global_registries

    def test_boostrap(self):
        import ptah
        from ptah.scripts import bootstrap

        result = bootstrap('/foo/settings.ini')

        self.assertEqual(result['app'], self.app)
        self.assertEqual(result['registry'], self.registry)
        self.assertTrue(result['request'] is not None)
        self.assertEqual(result['request'].registry, self.registry)
        self.assertFalse(ptah.POPULATE)

########NEW FILE########
__FILENAME__ = test_manage
import sys
import ptah
from ptah.scripts import manage
from pyramid.compat import NativeIO


class TestManageCommand(ptah.PtahTestCase):

    _init_ptah = False

    def test_manage_no_params(self):
        self.init_ptah()

        sys.argv[:] = ['ptah-manage', 'ptah.ini']

        stdout = sys.stdout
        out = NativeIO()
        sys.stdout = out

        manage.main(False)
        sys.stdout = stdout

        val = out.getvalue()

        self.assertIn(
            '[-h] [--list-modules] [--list-models] config', val)

    def test_list_modules(self):

        @ptah.manage.module('custom')
        class CustomModule(ptah.manage.PtahModule):
            """ Custom module description """

            title = 'Custom Module'

        self.init_ptah()

        sys.argv[1:] = ['--list-modules', 'ptah.ini']

        stdout = sys.stdout
        out = NativeIO()
        sys.stdout = out

        manage.main(False)
        sys.stdout = stdout

        val = out.getvalue()

        self.assertIn('* custom: Custom Module (disabled: False)', val)
        self.assertIn('Custom module description', val)

        # disable
        cfg = ptah.get_settings(ptah.CFG_ID_PTAH)
        cfg['disable_modules'] = ('custom',)

        out = NativeIO()
        sys.stdout = out

        manage.main(False)
        sys.stdout = stdout

        val = out.getvalue()

        self.assertIn('* custom: Custom Module (disabled: True)', val)

    def test_list_models(self):
        @ptah.tinfo(
            'custom', title='Custom model',
            description = 'Custom model description')

        class CustomModel(object):
            """ Custom module description """

            title = 'Custom Module'

        self.init_ptah()

        sys.argv[1:] = ['--list-models', 'ptah.ini']

        stdout = sys.stdout
        out = NativeIO()
        sys.stdout = out

        manage.main(False)
        sys.stdout = stdout

        val = out.getvalue()

        self.assertIn('* type:custom: Custom model (disabled: False)', val)
        self.assertIn('Custom model description', val)
        self.assertIn('class: CustomModel', val)
        self.assertIn('module: test_manage', val)

        # disable
        cfg = ptah.get_settings(ptah.CFG_ID_PTAH)
        cfg['disable_models'] = ('type:custom',)

        out = NativeIO()
        sys.stdout = out

        manage.main(False)
        sys.stdout = stdout

        val = out.getvalue()

        self.assertIn('* type:custom: Custom model (disabled: True)', val)

########NEW FILE########
__FILENAME__ = test_migrate
import os
import sys
import shutil
import tempfile
import ptah
from ptah.scripts import migrate
from pyramid.compat import NativeIO


class TestMigrateCommand(ptah.PtahTestCase):

    _init_ptah = False

    def setUp(self):
        super(TestMigrateCommand, self).setUp()

        # fix stdout
        self.orig_stdout = sys.stdout
        self.out = out = NativeIO()
        sys.stdout = out

        # fix bootstrap
        import ptah.scripts
        self.original_bootstrap = ptah.scripts.bootstrap

        def bootstrap(*args, **kw):
            return {'registry': self.registry, 'request': self.request,
                    'app': object()}

        ptah.scripts.bootstrap = bootstrap

        # fix ScriptDirectory
        from ptah import migrate as migrate_mod

        self.dirs = dirs = {}

        class ScriptDirectory(migrate_mod.ScriptDirectory):

            def __init__(self, pkg):
                if pkg in dirs:
                    dir = dirs[pkg]
                else:
                    dir = tempfile.mkdtemp()
                    dirs[pkg] = dir

                self.dir = os.path.join(
                    os.path.dirname(ptah.__file__), 'scripts')
                self.versions = dir

        self.orig_ScriptDirectory = migrate_mod.ScriptDirectory
        migrate_mod.ScriptDirectory = ScriptDirectory

    def tearDown(self):
        # reset bootstrap
        import ptah.scripts
        ptah.scripts.bootstrap = self.original_bootstrap

        # reset stdout
        sys.stdout = self.orig_stdout

        # reset ScriptDirectory
        for dir in self.dirs.values():
            shutil.rmtree(dir)

        from ptah import migrate as migrate_mod
        migrate_mod.ScriptDirectory = self.orig_ScriptDirectory

        super(TestMigrateCommand, self).tearDown()

    def _reset_stdout(self):
        sys.stdout = self.orig_stdout

    def test_script_help(self):
        self.init_ptah()

        sys.argv[:] = ['ptah-migrate', '-h', 'ptah.ini']

        try:
            migrate.main()
        except:
            pass

        self._reset_stdout()
        self.assertIn('usage: ptah-migrate [-h] config', self.out.getvalue())

    def test_list_migrations(self):
        ptah.register_migration('test', 'test:path', 'Test migration')

        self.init_ptah()

        sys.argv[:] = ['ptah-migrate', 'ptah.ini', 'list']

        migrate.main()

        self._reset_stdout()
        self.assertIn('* test: Test migration', self.out.getvalue())

    def test_upgrade_one(self):
        from ptah.migrate import revision, Version

        ptah.register_migration('test1', 'test1:path', 'Test migration',True)
        ptah.register_migration('test2', 'test2:path', 'Test migration',True)

        self.init_ptah()

        rev1 = revision('test1')
        revision('test2')

        sys.argv[:] = ['ptah-migrate', 'ptah.ini', 'upgrade', 'test1']

        migrate.main()

        self._reset_stdout()

        versions = dict((v.package, v.version_num)
                        for v in ptah.get_session().query(Version).all())

        self.assertIn('test1', versions)
        self.assertEqual(versions['test1'], rev1)
        self.assertNotIn('test2', versions)

    def test_upgrade_several(self):
        from ptah.migrate import revision, Version

        ptah.register_migration('test1', 'test1:path', 'Test migration')
        ptah.register_migration('test2', 'test2:path', 'Test migration')

        self.init_ptah()

        versions = dict((v.package, v.version_num)
                        for v in ptah.get_session().query(Version).all())

        rev1 = revision('test1')
        rev2 = revision('test2')

        sys.argv[:] = ['ptah-migrate', 'ptah.ini', 'upgrade', 'test1', 'test2']

        migrate.main()

        self._reset_stdout()

        versions = dict((v.package, v.version_num)
                        for v in ptah.get_session().query(Version).all())

        self.assertIn('test1', versions)
        self.assertIn('test2', versions)
        self.assertEqual(versions['test1'], rev1)
        self.assertEqual(versions['test2'], rev2)

    def test_revision(self):
        ptah.register_migration('test', 'test:path', 'Test migration')
        self.init_ptah()

        sys.argv[:] = ['ptah-migrate', 'ptah.ini',
                       'revision', 'test', '-r', '001', '-m', 'Test message']
        migrate.main()

        path = self.dirs['test']
        self.assertIn('001.py', os.listdir(path))

    def test_revision_error(self):
        ptah.register_migration('test', 'test:path', 'Test migration')
        self.init_ptah()

        sys.argv[:] = ['ptah-migrate', 'ptah.ini',
                       'revision', 'test', '-r', '0.0;1', '-m', 'Test message']
        migrate.main()
        self._reset_stdout()

        self.assertIn('Revision id contains forbidden characters',
                      self.out.getvalue())

    def test_history(self):
        from ptah.migrate import revision, upgrade

        ptah.register_migration('test1', 'test1:path', 'Test migration')
        ptah.register_migration('test2', 'test2:path', 'Test migration')

        self.init_ptah()

        revision('test1', message='test1 step')
        revision('test2', message='test2 step')

        upgrade('test1')
        upgrade('test2')

        sys.argv[:] = ['ptah-migrate', 'ptah.ini', 'history', 'test1']

        migrate.main()

        self.assertIn('test1 step', self.out.getvalue())

        sys.argv[:] = ['ptah-migrate', 'ptah.ini', 'history']
        migrate.main()

        self.assertIn('test1 step', self.out.getvalue())
        self.assertIn('test2 step', self.out.getvalue())

    def test_current_one(self):
        from ptah.migrate import revision, upgrade

        ptah.register_migration('test1', 'test1:path', 'Test migration')
        ptah.register_migration('test2', 'test2:path', 'Test migration')

        self.init_ptah()

        rev1 = revision('test1', message='test1 step')
        revision('test2', message='test2 step')
        upgrade('test1')

        sys.argv[:] = ['ptah-migrate', 'ptah.ini', 'current', 'test1']

        migrate.main()

        self.assertIn("Package 'test1' rev: %s(head) test1 step"%rev1,
                      self.out.getvalue())

    def test_current_all(self):
        from ptah.migrate import revision, upgrade

        ptah.register_migration('test1', 'test1:path', 'Test migration')
        ptah.register_migration('test2', 'test2:path', 'Test migration')

        self.init_ptah()

        rev1 = revision('test1', message='test1 step')
        revision('test2', message='test2 step')
        upgrade('test1')

        sys.argv[:] = ['ptah-migrate', 'ptah.ini', 'current']

        migrate.main()

        self.assertIn("Package 'test1' rev: %s(head) test1 step"%rev1,
                      self.out.getvalue())
        self.assertIn("Package 'test2' rev: None", self.out.getvalue())

########NEW FILE########
__FILENAME__ = test_populate
import sys
import ptah
from ptah.scripts import populate
from pyramid.compat import NativeIO


class TestPopulateCommand(ptah.PtahTestCase):

    def setUp(self):
        super(TestPopulateCommand, self).setUp()

        import ptah.scripts
        self.original_bootstrap = ptah.scripts.bootstrap

        def bootstrap(*args, **kw):
            return {'registry': self.registry, 'request': self.request,
                    'app': object()}

        ptah.scripts.bootstrap = bootstrap

    def tearDown(self):
        import ptah.scripts
        ptah.scripts.bootstrap = self.original_bootstrap

        super(TestPopulateCommand, self).tearDown()

    def test_populate_no_params(self):
        sys.argv[:] = ['ptah-populate', 'ptah.ini']

        stdout = sys.stdout
        out = NativeIO()
        sys.stdout = out

        populate.main()
        sys.stdout = stdout

        val = out.getvalue()

        self.assertIn(
            'usage: ptah-populate [-h] [-l] [-a] config [step [step ...]]', val)

    def test_populate_list(self):

        def step(registry):
            """ """

        self.config.ptah_populate_step(
            'custom-step', title='Custom step',
            active=False, factory=step)

        sys.argv[:] = ['ptah-populate', 'ptah.ini', '-l']

        stdout = sys.stdout
        out = NativeIO()
        sys.stdout = out

        populate.main()
        sys.stdout = stdout

        val = out.getvalue()

        self.assertIn('* custom-step: Custom step (inactive)', val)

    def test_populate_execute_step(self):
        data = [False]
        def step(registry):
            data[0] = True

        self.config.ptah_populate_step(
            'custom-step', title='Custom step',
            active=False, factory=step)

        sys.argv[:] = ['ptah-populate', 'ptah.ini', 'custom-step']

        populate.main()

        self.assertTrue(data[0])

    def test_populate_execute_all(self):
        data = [False, False]
        def step1(registry):
            data[0] = True

        def step2(registry): # pragma: no cover
            data[0] = True

        self.config.ptah_populate_step(
            'custom-step1', title='Custom step 1',
            active=True, factory=step1)

        self.config.ptah_populate_step(
            'custom-step2', title='Custom step 2',
            active=False, factory=step2)

        sys.argv[:] = ['ptah-populate', 'ptah.ini', '-a']

        populate.main()

        self.assertTrue(data[0])
        self.assertFalse(data[1])

########NEW FILE########
__FILENAME__ = test_settings
import sys
import ptah
import pform
from ptah.scripts import settings
from ptah.testing import PtahTestCase
from pyramid.compat import NativeIO


class TestCommand(PtahTestCase):

    _init_ptah = False

    def test_settings_command(self):
        field = pform.TextField(
            'node',
            default = 'test')

        ptah.register_settings(
            'group1', field,
            title = 'Section1',
            description = 'Description1',
            )

        ptah.register_settings(
            'group2', field,
            title = 'Section2',
            description = 'Description2',
            )

        self.init_ptah()

        ptah.get_settings('group1', self.registry)
        ptah.get_settings('group2', self.registry)

        # all
        sys.argv[1:] = ['-a', 'ptah.ini']

        stdout = sys.stdout
        out = NativeIO()
        sys.stdout = out

        settings.main(False)
        sys.stdout = stdout

        val = out.getvalue()
        self.assertIn('Section1', val)
        self.assertIn('Section2', val)
        self.assertIn('group1.node', val)
        self.assertIn('group2.node', val)

        # section
        sys.argv[1:] = ['-l', 'group1', 'ptah.ini']

        stdout = sys.stdout
        out = NativeIO()
        sys.stdout = out

        settings.main(False)
        sys.stdout = stdout

        val = out.getvalue()
        self.assertIn('Section1', val)
        self.assertNotIn('Section2', val)
        self.assertIn('group1.node', val)
        self.assertNotIn('group2.node', val)

        # print
        sys.argv[1:] = ['-p', 'ptah.ini']

        stdout = sys.stdout
        out = NativeIO()
        sys.stdout = out

        settings.main(False)
        sys.stdout = stdout

        val = out.getvalue().strip()
        self.assertIn('group1.node = "test"', val)
        self.assertIn('group2.node = "test"', val)

########NEW FILE########
__FILENAME__ = security
from collections import OrderedDict
from pyramid.compat import string_types
from pyramid.location import lineage
from pyramid.security import ACLDenied, ACLAllowed, Allow, Deny
from pyramid.security import ALL_PERMISSIONS, NO_PERMISSION_REQUIRED
from pyramid.authorization import ACLAuthorizationPolicy
from pyramid.interfaces import IAuthorizationPolicy
from pyramid.threadlocal import get_current_registry
from pyramid.httpexceptions import HTTPForbidden

import ptah
from ptah import config
from ptah import auth_service
from ptah import SUPERUSER_URI
from ptah.settings import get_settings
from ptah.interfaces import IOwnersAware
from ptah.interfaces import ILocalRolesAware


ID_ACL = 'ptah:aclmap'
ID_ROLE = 'ptah:role'
ID_ROLES_PROVIDER = 'ptah:roles-provider'
ID_PERMISSION = 'ptah:permission'


def get_acls():
    """ return list of registered ACLS """
    return config.get_cfg_storage(ID_ACL)


def get_roles():
    """ return list of registered roles """
    return config.get_cfg_storage(ID_ROLE)


def get_permissions():
    """ return list of registered permissions """
    return config.get_cfg_storage(ID_PERMISSION)


class PermissionInfo(str):
    """ Permission information """

    title = ''
    description = ''


def Permission(name, title, description=''):
    """ Register new permission. """
    info = config.DirectiveInfo()

    permission = PermissionInfo(name)
    permission.title = title
    permission.description = description

    discr = (ID_PERMISSION, name)
    intr = config.Introspectable(ID_PERMISSION, discr, title, 'ptah-permission')
    intr['permission'] = permission
    intr['module'] = info.module.__name__
    intr['codeinfo'] = info.codeinfo

    info.attach(
        config.Action(
            lambda config, p: \
                config.get_cfg_storage(ID_PERMISSION).update({str(p): p}),
            (permission,), discriminator=discr, introspectables=(intr,))
        )

    return permission


class ACL(list):
    """ Named ACL map

    ACL contains list of permit rules, for example::

      >> acl = ACL('test', 'Test ACL')
      >> acl.allow('system.Everyone', 'View')
      >> acl.deny('system.Everyone', 'Edit')

      >> list(acl)
      [(Allow, 'system.Everyone', ('View',)),
       (Deny, 'system.Everyone', ('Edit',))]

    """

    # do we need somthing like Unset, to unset permission from parent

    def __init__(self, id, title, description=''):
        self.id = id
        self.title = title
        self.description = description

        info = config.DirectiveInfo()
        discr = (ID_ACL, id)
        intr = config.Introspectable(ID_ACL, discr, title, 'ptah-aclmap')
        intr['acl'] = self
        intr['codeinfo'] = info.codeinfo

        info.attach(
            config.Action(
                lambda config, p: \
                    config.get_cfg_storage(ID_ACL).update({id: p}),
                (self,), discriminator=discr, introspectables=(intr,))
            )
        self.directiveInfo = info

    def get(self, typ, role):
        for r in self:
            if r[0] == typ and r[1] == role:
                return r

        return None

    def allow(self, role, *permissions):
        """ Give permissions to role """

        if not isinstance(role, string_types):
            role = role.id

        rec = self.get(Allow, role)
        if rec is None:
            rec = [Allow, role, set()]
            self.append(rec)

        if rec[2] is ALL_PERMISSIONS:
            return

        if ALL_PERMISSIONS in permissions:
            rec[2] = ALL_PERMISSIONS
        else:
            rec[2].update(permissions)

    def deny(self, role, *permissions):
        """ Deny permissions for role """

        if not isinstance(role, string_types):
            role = role.id

        rec = self.get(Deny, role)
        if rec is None:
            rec = [Deny, role, set()]
            self.append(rec)

        if rec[2] is ALL_PERMISSIONS:
            return

        if ALL_PERMISSIONS in permissions:
            rec[2] = ALL_PERMISSIONS
        else:
            rec[2].update(permissions)

    def unset(self, role, *permissions):
        """ Unset any previously defined permissions """
        for perm in permissions:
            for rec in self:
                if role is not None and rec[1] != role:
                    continue

                if rec[2] is ALL_PERMISSIONS or perm is ALL_PERMISSIONS:
                    rec[2] = set()
                else:
                    if perm in rec[2]:
                        rec[2].remove(perm)

        records = []
        for rec in self:
            if rec[2]:
                records.append(rec)
        self[:] = records


class ACLsMerge(object):
    """ Special class that merges different ACLs maps """

    def __init__(self, acls):
        self.acls = acls

    def __iter__(self):
        acls = config.get_cfg_storage(ID_ACL)
        for aname in self.acls:
            acl = acls.get(aname)
            if acl is not None:
                for rec in acl:
                    yield rec


class ACLsProperty(object):
    """ This property merges `__acls__` list of ACLs and
    generate one `__acl__`

    For example::

      >> class Content(object):
      ...
      ...   __acls__ = ['map1', 'map2']
      ...
      ...   __acl__ = ACLsProperty()

    In this case it is possible to manipulate permissions
    by just changing `__acls__` list.

    """

    def __get__(self, inst, klass):
        acls = getattr(inst, '__acls__', ())
        if acls:
            return ACLsMerge(acls)
        else:
            return ()


class Role(object):
    """ Register new security role in the system """

    def __init__(self, name, title, description='',
                 prefix='role:', system=False):
        id = '%s%s' % (prefix, name)

        self.id = id
        self.name = name
        self.title = title
        self.description = description
        self.system = system

        self.allowed = set()
        self.denied = set()

        # conflict detection and introspection
        info = config.DirectiveInfo()

        discr = (ID_ROLE, name)
        intr = config.Introspectable(ID_ROLE, discr, title, 'ptah-role')
        intr['role'] = self
        intr['codeinfo'] = info.codeinfo

        info.attach(
            config.Action(
                lambda config, r: \
                    config.get_cfg_storage(ID_ROLE).update({r.name: r}),
                (self, ), discriminator=discr, introspectables=(intr,))
            )

    def __str__(self):
        return 'Role<%s>' % self.title

    def __repr__(self):
        return self.id

    def allow(self, *permissions):
        DEFAULT_ACL.allow(self.id, *permissions)

    def deny(self, *permissions):
        DEFAULT_ACL.deny(self.id, *permissions)

    def unset(self, *permissions):
        DEFAULT_ACL.unset(self.id, *permissions)


class roles_provider(object):
    """ Register roles provider.

    roles provider accepts userid and registry and returns
    sequence of roles.

    :param name: Unique name

    Roles provider interface :py:func:`ptah.interfaces.roles_provider`.

    .. code-block:: python

       import ptah

       @ptah.roles_provider('custom-roles')
       def custom_roles(context, userid, registry):
           if userid == '...':
               return ['Role1', 'Role2']
    """

    def __init__(self, name, __depth=1):
        self.info = config.DirectiveInfo(__depth)
        self.discr = (ID_ROLES_PROVIDER, name)

        self.intr = intr = config.Introspectable(
            ID_ROLES_PROVIDER, self.discr, name, ID_ROLES_PROVIDER)

        intr['name'] = name
        intr['codeinfo'] = self.info.codeinfo

    def __call__(self, factory, cfg=None):
        intr = self.intr
        intr['factory'] = factory

        self.info.attach(
            config.Action(
                lambda cfg, name, f:
                    cfg.get_cfg_storage(ID_ROLES_PROVIDER).update({name: f}),
                (intr['name'], factory),
                discriminator=self.discr, introspectables=(intr,)),
            cfg)
        return factory


@roles_provider('ptah_default_roles')
def ptah_default_roles(context, uid, registry):
    cfg = get_settings(ptah.CFG_ID_PTAH, registry)
    return cfg['default_roles']


def get_local_roles(userid, request=None,
                    context=None, get_cfg_storage=config.get_cfg_storage):
    """ calculates local roles for userid """
    if context is None:
        context = getattr(request, 'context', None)
        if context is None:
            context = getattr(request, 'root', None)

    roles = OrderedDict()

    if IOwnersAware.providedBy(context):
        if userid == context.__owner__:
            roles[Owner.id] = Allow

    for location in lineage(context):
        if ILocalRolesAware.providedBy(location):
            local_roles = location.__local_roles__
            if local_roles:
                user_props = getattr(ptah.resolve(userid), 'properties', dict())
                user_roles = []

                for r in local_roles.get(userid, ()):
                    if r not in user_roles:
                        user_roles.append(r)
                for grp in user_props.get('groups', ()):
                    for r in local_roles.get(grp, ()):
                        if r not in roles:
                            user_roles.append(r)

                for r in user_roles:
                    if r not in roles:
                        roles[r] = Allow

    data = []
    for r, val in roles.items():
        if val is Allow:
            data.append(r)

    registry = get_current_registry()
    for provider in get_cfg_storage(ID_ROLES_PROVIDER, registry).values():
        data.extend(provider(context, userid, registry))

    return data


DEFAULT_ACL = ACL('', 'Default ACL map')

Everyone = Role(
    'Everyone', 'Everyone', '', 'system.', True)

Authenticated = Role(
    'Authenticated', 'Authenticated', '', 'system.', True)

Owner = Role(
    'Owner', 'Owner', '', 'system.', True)

NOT_ALLOWED = Permission('__not_allowed__', 'Special permission')


def check_permission(permission, context, request=None, throw=False):
    """ Check `permission` withing `context`.

    :param permission: Permission
    :type permission: (Permission or sting)
    :param context: Context object
    :param throw: Throw HTTPForbidden exception.
    """

    if not permission or permission == NO_PERMISSION_REQUIRED:
        return True
    if permission == NOT_ALLOWED:
        if throw:
            raise HTTPForbidden()
        return False

    userid = auth_service.get_effective_userid()
    if userid == SUPERUSER_URI:
        return True

    AUTHZ = get_current_registry().getUtility(IAuthorizationPolicy)

    principals = [Everyone.id]

    if userid is not None:
        principals.extend((Authenticated.id, userid))

        roles = get_local_roles(userid, context=context)
        if roles:
            principals.extend(roles)

    res = AUTHZ.permits(context, principals, permission)

    if isinstance(res, ACLDenied):
        if throw:
            raise HTTPForbidden(res)

        return False
    return True


class PtahAuthorizationPolicy(ACLAuthorizationPolicy):

    def permits(self, context, principals, permission):
        if not permission or permission == NO_PERMISSION_REQUIRED:
            return True
        if permission == NOT_ALLOWED:
            return ACLDenied(
                '<NOT ALLOWED permission>',
                None, permission, principals, context)

        if SUPERUSER_URI in principals or \
           auth_service.get_effective_userid() == SUPERUSER_URI:
            return ACLAllowed(
                'Superuser', None, permission, principals, context)

        return super(PtahAuthorizationPolicy, self).permits(
            context, principals, permission)

########NEW FILE########
__FILENAME__ = settings
""" settings """
import logging
import os.path
import sqlalchemy as sqla
from collections import OrderedDict

from zope import interface
from zope.interface.interface import InterfaceClass
from pyramid.compat import configparser

import pform as form

import ptah
from ptah import uri, config
from ptah.sqlautils import JsonType
from ptah.config import StopException

log = logging.getLogger('ptah')

SETTINGS_ID = 'settings'
SETTINGS_OB_ID = 'ptah:settings'
ID_SETTINGS_GROUP = 'ptah:settings-group'

_marker = object()


def get_settings(grp, registry=None):
    """Get settings group by group id. Also there is `ptah_get_settins`
    pyramid configurator directive.

    .. code-block:: python

      config = Configurator()
      config.include('ptah')
      config.commit()

      # get settings with pyramid directive
      ptah_settings = config.ptah_get_settings('ptah')

      # get settings with `get_settings`
      ptah_settings = ptah.get_settings(ptah.CFG_ID_PTAH, config.registry)

    """
    return config.get_cfg_storage(ID_SETTINGS_GROUP, registry)[grp]


@uri.resolver('settings')
def settings_resolver(uri):
    """ Ptah settings resolver """
    return config.get_cfg_storage(ID_SETTINGS_GROUP)[uri[9:]]


def pyramid_get_settings(config, grp):
    """ pyramid configurator directive for getting settings group::

        config = Configurator()
        config.include('ptah')

        PTAH_CFG = config.get_settings(ptah.CFG_ID_PTAH)
    """
    return config.get_cfg_storage(ID_SETTINGS_GROUP)[grp]


def load_dbsettings(registry=None):
    session = ptah.get_session()
    if not (session.bind and SettingRecord.__table__.exists()):
        return

    # load db settings
    s_ob = config.get_cfg_storage(
        SETTINGS_OB_ID, registry, default_factory=Settings)
    s_ob.load_fromdb()


def init_settings(pconfig, cfg=None, section=configparser.DEFAULTSECT):
    """Initialize settings management system. This function available
    as pyramid configurator directive. You should call it during
    application configuration process.

    .. code-block:: python

      config = Configurator()
      config.include('ptah')

      # initialize ptah setting management system
      config.ptah_init_settings()

    """
    settings = config.get_cfg_storage(SETTINGS_OB_ID, pconfig.registry,Settings)

    if settings.initialized:
        raise RuntimeError(
            "initialize_settings has been called more than once.")

    log.info('Initializing ptah settings')

    settings.initialized = True

    if cfg is None:
        cfg = pconfig.registry.settings

    here = cfg.get('here', './')
    include = cfg.get('include', '')
    for f in include.split('\n'):
        f = f.strip()
        if f and os.path.exists(f):
            parser = configparser.SafeConfigParser()
            parser.read(f)
            if section == configparser.DEFAULTSECT or \
                    parser.has_section(section):
                cfg.update(parser.items(section, vars={'here': here}))

    pconfig.begin()
    try:
        settings.init(pconfig, cfg)
        pconfig.registry.notify(
            ptah.events.SettingsInitializing(pconfig, pconfig.registry))
        pconfig.registry.notify(
            ptah.events.SettingsInitialized(pconfig, pconfig.registry))
    except Exception as e:
        raise StopException(e)
    finally:
        pconfig.end()


def register_settings(name, *fields, **kw):
    """Register settings group.

    :param name: Name of settings group
    :param fields: List of :py:class:`pform.Field` objects

    """
    iname = name
    for ch in ('.', '-'):
        iname = iname.replace(ch, '_')

    category = InterfaceClass(
        'SettingsGroup:%s' % iname.upper(), (),
        __doc__='Settings group: %s' % name,
        __module__='ptah.config.settings')

    for field in fields:
        field.required = False
        field.missing = field.default
        if field.default is form.null:
            raise StopException(
              'Default value is required for "{0}.{1}"'.format(name,field.name))

    group = Group(name=name, *fields, **kw)
    interface.directlyProvides(Group, category)

    info = config.DirectiveInfo()
    discr = (ID_SETTINGS_GROUP, name)
    intr = config.Introspectable(
        ID_SETTINGS_GROUP, discr, group.__title__, 'ptah-settingsgroup')
    intr['name'] = name
    intr['group'] = group
    intr['codeinfo'] = info.codeinfo

    info.attach(
        config.Action(
            lambda config, group: config.get_cfg_storage(ID_SETTINGS_GROUP)\
                .update({group.__name__: group.clone(config.registry)}),
            (group,), discriminator=discr, introspectables=(intr,))
        )


class Settings(object):
    """ settings management system """

    initialized = False

    def init(self, config, defaults=None):
        groups = config.get_cfg_storage(ID_SETTINGS_GROUP).items()

        for name, group in groups:
            data = {}
            for field in group.__fields__.values():
                if field.default is not form.null:
                    data[field.name] = field.default

            group.update(data)

        if defaults is None: # pragma: no cover
            return

        self.load(defaults, True)

    def load(self, rawdata, setdefaults=False):
        groups = config.get_cfg_storage(ID_SETTINGS_GROUP).items()

        try:
            rawdata = dict((k.lower(), v) for k, v in rawdata.items())
        except Exception as e:
            raise StopException(e)

        for name, group in groups:
            data, errors = group.extract(rawdata)

            if errors:
                log.error(errors.msg)
                raise StopException(errors)

            for k, v in data.items():
                if v is not form.null:
                    if setdefaults:
                        group.__fields__[k].default = v

            group.update(data)

    def load_fromdb(self):
        records = dict(ptah.get_session().
                       query(SettingRecord.name, SettingRecord.value))
        self.load(records)

        # load non defined fields
        groups = config.get_cfg_storage(ID_SETTINGS_GROUP).items()

        for name, group in groups:
            name = '%s.'%name
            for attr, val in records.items():
                if attr.startswith(name):
                    fname = attr[len(name):]
                    if fname not in group.__fields__:
                        try:
                            group[fname] = JsonType.serializer.loads(val)
                        except ValueError:
                            group[fname] = val

    def export(self, default=False):
        groups = config.get_cfg_storage(ID_SETTINGS_GROUP).items()

        result = {}
        for name, group in groups:
            for field in group.__fields__.values():
                fname = field.name
                if group[fname] == field.default and not default:
                    continue

                result['{0}.{1}'.format(name,fname)] = \
                                    ptah.json.dumps(group[fname])

        return result


class Group(OrderedDict):
    """ Settings group """

    def __init__(self, *args, **kwargs):
        super(Group, self).__init__()

        fields = form.Fieldset(*args, **kwargs)
        self.__uri__ = 'settings:{0}'.format(fields.name)
        self.__name__ = fields.name
        self.__title__ = fields.title
        self.__description__ = fields.description
        self.__fields__ = fields
        self.__ttw__ = kwargs.get('ttw', False)
        self.__ttw_skip_fields__ = kwargs.get('ttw_skip_fields', ())

    def clone(self, registry):
        clone = self.__class__.__new__(self.__class__)
        clone.__dict__.update(self.__dict__)
        clone.__registry__ = registry
        return clone

    def extract(self, rawdata):
        fieldset = self.__fields__
        name = fieldset.name

        data = {}
        errors = form.FieldsetErrors(fieldset)

        for field in fieldset.fields():
            value = rawdata.get('{0}.{1}'.format(name, field.name), _marker)

            if value is _marker:
                value = self.get(field.name)
            else:
                try:

                    try:
                        value = ptah.json.loads(value)
                    except:
                        if not value.startswith('"'):
                            value = '"{0}"'.format(value)
                        value = value.replace('\n', '\\n')
                        value = ptah.json.loads(value)

                    field.validate(value)

                    if field.preparer is not None:
                        value = field.preparer(value)
                except form.Invalid as e:
                    errors.append(e)
                    value = field.default

            data[field.name] = value

        if not errors:
            try:
                fieldset.validate(data)
            except form.Invalid as e:
                errors.append(e)

        return data, errors

    def get(self, name, default=None):
        try:
            return super(Group, self).__getitem__(name)
        except (KeyError, AttributeError):
            pass

        if name in self.__fields__:
            return self.__fields__[name].default

        return default

    def keys(self):
        return [node.name for node in self.__fields__.values()]

    def items(self):
        return [(key, self.get(key)) for key in self.__fields__.keys()]

    def __getitem__(self, name):
        res = self.get(name, _marker)
        if res is _marker:
            raise KeyError(name)
        return res

    def updatedb(self, **data):
        self.update(data)

        name = self.__name__
        fields = self.__fields__

        Session = ptah.get_session()

        # remove old data
        keys = tuple('{0}.{1}'.format(name, key) for key in data.keys())
        if keys:
            Session.query(SettingRecord)\
                .filter(SettingRecord.name.in_(keys)).delete(False)

        # insert new data
        for fname in data.keys():
            if fname in fields:
                field = fields[fname]
                value = self[fname]
                if value == field.default:
                    continue

                rec = SettingRecord(name='{0}.{1}'.format(name, fname),
                                    value = ptah.json.dumps(value))
            else:
                rec = SettingRecord(
                    name='{0}.{1}'.format(name, fname),
                    value = JsonType.serializer.dumps(data[fname]))

            Session.add(rec)

        Session.flush()

        self.__registry__.notify(ptah.events.SettingsGroupModified(self))
        self.__registry__.notify(ptah.events.UriInvalidateEvent(self.__uri__))


class SettingRecord(ptah.get_base()):

    __tablename__ = 'ptah_settings'

    name = sqla.Column(sqla.String(128), primary_key=True)
    value = sqla.Column(sqla.UnicodeText)

########NEW FILE########
__FILENAME__ = sqla
""" sqlalchemy query wrapper """
import pform
import sqlalchemy as sqla


def get_columns_order(mapper):
    if mapper.inherits is not None:
        order = get_columns_order(mapper.inherits)
    else:
        order = []

    table = mapper.local_table
    for cl in table.columns:
        order.append((table.name, cl.name))

    return order


def generate_fieldset(model, fieldNames=None, namesFilter=None,
                      skipPrimaryKey=True):
    """
    :param model: subclass of sqlalchemy.ext.declarative.declarative_base
    :param fieldNames: **optional** sequence of strings to use
    :param namesFilter: **optional** callable which takes a key and list
        of fieldNames to compute if fieldName should filtered out of Fieldset
        generation.
    :param skipPrimaryKey: **default: True** Should PrimaryKey be omitted
        from fieldset generation.
    :returns: a instance of :py:class:`pform.Fieldset`
    """
    mapper = model.__mapper__
    order = get_columns_order(mapper)

    columns = []
    for attr in list(mapper.class_manager.attributes):
        cl = attr.__clause_element__()
        if isinstance(cl, sqla.Column):
            if fieldNames is not None and attr.key not in fieldNames:
                continue

            if namesFilter is not None and \
                    not namesFilter(attr.key, fieldNames):
                continue

            idx = order.index((cl.table.name, cl.name))
            columns.append((idx, attr.key, cl))

    columns = [(name, cl) for i, name, cl in sorted(columns)]

    return build_sqla_fieldset(columns, skipPrimaryKey)


mapping = {
    (sqla.Unicode, sqla.UnicodeText, sqla.String, sqla.Text): 'text',
    sqla.Integer: 'int',
    sqla.Float: 'float',
    sqla.Date: 'date',
    sqla.DateTime: 'datetime',
    sqla.Boolean: 'bool',
}


def build_sqla_fieldset(columns, skipPrimaryKey=False):
    """
    Given a list of SQLAlchemy columns generate a pform.Fieldset.

    :param columns: sequence of sqlachemy.schema.Column instances
    :param skipPrimaryKey: **default: False** boolean whether to include PK
      Columns in Fieldset generation.
    :returns: a instance of :py:class:`pform.Fieldset`
    """
    fields = []

    for name, cl in columns:
        if cl.info.get('skip', False):
            continue

        if 'field' in cl.info:
            field = cl.info['field']
            fields.append(field)
            continue

        if cl.primary_key and skipPrimaryKey:
            continue

        typ = cl.info.get('factory')
        if typ is None:
            typ = cl.info.get('field_type')

        if typ is None:
            for cls, field_type in mapping.items():
                if isinstance(cl.type, cls):
                    typ = field_type
                    break
        if typ is None:
            continue

        kwargs = {}
        for attr in ('missing', 'title', 'description',
                     'vocabulary', 'validator',
                     'required', 'default',
                     'rows', 'cols'):
            if attr in cl.info:
                kwargs[attr] = cl.info[attr]

        if cl.primary_key and (typ == 'int'):
            kwargs['readonly'] = True

        if 'title' not in kwargs:
            kwargs['title'] = name.capitalize()

        if callable(typ):
            field = typ(name, **kwargs)
        else:
            field = pform.FieldFactory(typ, name, **kwargs)
        fields.append(field)

    return pform.Fieldset(*fields)

########NEW FILE########
__FILENAME__ = sqlautils
# -*- coding: utf-8 -*-
from __future__ import (absolute_import, division, print_function,
    unicode_literals)  # Avoid breaking Python 3

import uuid
from threading import local

from sqlalchemy import orm
from sqlalchemy.ext import declarative
from sqlalchemy.ext.mutable import Mutable
from sqlalchemy.types import TypeDecorator, TEXT
from zope.sqlalchemy import ZopeTransactionExtension

from ptah.util import json

_base = declarative.declarative_base()
_zte = ZopeTransactionExtension()
_session = orm.scoped_session(orm.sessionmaker(extension=[_zte]))
_session_maker = orm.sessionmaker()
_sa_session = local()


def get_base():
    """Return the central SQLAlchemy declarative base."""
    return _base


def reset_session():
    """Reset sqla session"""
    global _zte, _session

    _zte = ZopeTransactionExtension()
    _session = orm.scoped_session(orm.sessionmaker(extension=[_zte]))


class transaction(object):

    def __init__(self, sa):
        self.sa = sa

    def __enter__(self):
        global _sa_session

        t = getattr(_sa_session, 'transaction', None)
        if t is not None:
            raise RuntimeError("Nested transactions are not allowed")

        _sa_session.sa = self.sa
        _sa_session.transaction = self

        return self.sa

    def __exit__(self, type, value, traceback):
        global _sa_session
        _sa_session.sa = None
        _sa_session.transaction = None

        if type is None:
            try:
                self.sa.commit()
            except:
                self.sa.rollback()
                raise
        else:
            self.sa.rollback()


def sa_session():
    return transaction(_session_maker())


def get_session_maker():
    return _session_maker


def get_session():
    """Return the central SQLAlchemy contextual session.

    To customize the kinds of sessions this contextual session creates, call
    its ``configure`` method::

        ptah.get_session().configure(...)

    But if you do this, be careful about the 'ext' arg. If you pass it, the
    ZopeTransactionExtension will be disabled and you won't be able to use this
    contextual session with transaction managers. To keep the extension active
    you'll have to re-add it as an argument. The extension is accessible under
    the semi-private variable ``_zte``. Here's an example of adding your own
    extensions without disabling the ZTE::

        ptah.get_session().configure(ext=[ptah._zte, ...])
    """
    return getattr(_sa_session, 'sa', _session) or _session


class QueryFreezer(object):
    """ A facade for sqla.Session.query which caches internal query structure.

    :param builder: anonymous function containing SQLAlchemy query

    .. code-block:: python

        _sql_parent = ptah.QueryFreezer(
            lambda: Session.query(Content)
                .filter(Content.__uri__ == sqla.sql.bindparam('parent')))
    """

    def __init__(self, builder):
        self.id = uuid.uuid4().int
        self.builder = builder

    def reset(self):
        pass

    def iter(self, **params):
        sa = get_session()
        try:
            data = sa.__ptah_cache__
        except AttributeError:
            sa.__ptah_cache__ = data = {}

        q = data.get(self.id, None)

        if q is None:
            query = self.builder()
            mapper = query._mapper_zero_or_none()
            querycontext = query._compile_context()
            querycontext.statement.use_labels = True
            stmt = querycontext.statement
            data[self.id] = (query, mapper, querycontext, stmt)
        else:
            query, mapper, querycontext, stmt = q

        conn = query._connection_from_session(
            mapper=mapper,
            clause=stmt,
            close_with_result=True)

        result = conn.execute(stmt, **params)
        return query.instances(result, querycontext)

    def one(self, **params):
        ret = list(self.iter(**params))

        l = len(ret)
        if l == 1:
            return ret[0]
        elif l == 0:
            raise orm.exc.NoResultFound("No row was found for one()")
        else:
            raise orm.exc.MultipleResultsFound(
                "Multiple rows were found for one()")

    def first(self, **params):
        ret = list(self.iter(**params))[0:1]
        if len(ret) > 0:
            return ret[0]
        else:
            return None

    def all(self, **params):
        return list(self.iter(**params))


def set_jsontype_serializer(serializer):
    JsonType.serializer = serializer


class JsonType(TypeDecorator):
    """Represents an immutable structure as a json-encoded string."""

    impl = TEXT
    serializer = json

    def __init__(self, serializer=None, *args, **kw):
        if serializer is not None:
            self.serializer = serializer
        super(JsonType, self).__init__(*args, **kw)

    def process_bind_param(self, value, dialect):
        if value is not None:
            value = self.serializer.dumps(value)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            value = self.serializer.loads(value)
        return value


class MutationList(Mutable, list):

    @classmethod
    def coerce(cls, key, value):
        if not isinstance(value, MutationList):
            if isinstance(value, list):
                return MutationList(value)
            return Mutable.coerce(key, value) # pragma: no cover
        else:
            return value # pragma: no cover

    def append(self, value):
        list.append(self, value)
        self.changed()

    def __setitem__(self, key, value):
        list.__setitem__(self, key, value)
        self.changed()

    def __delitem__(self, key):
        list.__delitem__(self, key)
        self.changed()


class MutationDict(Mutable, dict):

    @classmethod
    def coerce(cls, key, value):
        if not isinstance(value, MutationDict):
            if isinstance(value, dict):
                return MutationDict(value)
            return Mutable.coerce(key, value)  # pragma: no cover
        else:
            return value # pragma: no cover

    def __setitem__(self, key, value):
        dict.__setitem__(self, key, value)
        self.changed()

    def __delitem__(self, key):
        dict.__delitem__(self, key)
        self.changed()


def JsonDictType(serializer=None):
    """
    function which returns a SQLA Column Type suitable to store a Json dict.

    :returns: ptah.sqla.MutationDict
    """
    return MutationDict.as_mutable(JsonType(serializer=serializer))


def JsonListType(serializer=None):
    """
    function which returns a SQLA Column Type suitable to store a Json array.

    :returns: ptah.sqla.MutationList
    """
    return MutationList.as_mutable(JsonType(serializer=serializer))

########NEW FILE########
__FILENAME__ = testing
""" base class """
import sys
import transaction
from zope.interface import directlyProvides
from pyramid import testing
from pyramid.interfaces import IRequest
from pyramid.interfaces import IRouteRequest
from pyramid.interfaces import IRequestExtensions
from pyramid.view import render_view_to_response
from pyramid.path import package_name
from player.renderer import render

if sys.version_info[:2] == (2, 6): # pragma: no cover
    import unittest2 as unittest
    from unittest2 import TestCase
else:
    import unittest
    from unittest import TestCase

import ptah


class PtahTestCase(TestCase):

    _init_ptah = True
    _init_sqla = True
    _includes = ()
    _auto_commit = True

    _settings = {'sqlalchemy.url': 'sqlite://'}
    _packages = ()
    _trusted_manage = True
    _environ = {
        'wsgi.url_scheme':'http',
        'wsgi.version':(1,0),
        'HTTP_HOST': 'example.com',
        'SCRIPT_NAME': '',
        'PATH_INFO': '/',}

    def make_request(self, registry=None, environ=None,
                     request_iface=IRequest, **kwargs):
        if registry is None:
            registry = self.registry
        if environ is None:
            environ=self._environ
        request = testing.DummyRequest(environ=environ, **kwargs)
        request.request_iface = IRequest
        request.registry = registry
        request._set_extensions(registry.getUtility(IRequestExtensions))
        return request

    def init_request_extensions(self, registry):
        from pyramid.config.factories import _RequestExtensions

        exts = registry.queryUtility(IRequestExtensions)
        if exts is None:
            exts = _RequestExtensions()
            registry.registerUtility(exts, IRequestExtensions)

    def init_ptah(self, *args, **kw):
        self.registry.settings.update(self._settings)
        self.config.include('ptah')

        for pkg in self._includes: # pragma: no cover
            self.config.include(pkg)

        pkg = package_name(sys.modules[self.__class__.__module__])
        if pkg != 'ptah':
            parts = self.__class__.__module__.split('.')
            for l in range(len(parts)):
                pkg = '.'.join(parts[:l+1])
                if pkg == 'ptah' or pkg.startswith('ptah.') or \
                       pkg in self._includes:
                    continue # pragma: no cover
                try:
                    self.config.include(pkg)
                except: # pragma: no cover
                    pass

        self.config.scan(self.__class__.__module__)

        self.config.commit()
        self.config.autocommit = self._auto_commit

        self.config.ptah_init_settings()

        ptah.reset_session()

        if self._init_sqla:
            # create engine
            self.config.ptah_init_sql()

            # create sql tables
            Base = ptah.get_base()
            Base.metadata.create_all()
            transaction.commit()

        if self._trusted_manage:
            def trusted(*args):
                return True
            ptah.manage.set_access_manager(trusted)

    def init_pyramid(self):
        self.config = testing.setUp(settings=self._settings, autocommit=False)
        self.config.get_routes_mapper()
        self.init_request_extensions(self.config.registry)
        self.registry = self.config.registry

        self.config.include('pform')
        self.config.include('player')
        self.config.include('pyramid_amdjs')

        self.request = self.make_request()
        def set_ext():
            self.request._set_extensions(
                self.registry.getUtility(IRequestExtensions))

        self.config.action(id(self), callable=set_ext)
        self.config.begin(self.request)

    def setUp(self):
        self.init_pyramid()

        if self._init_ptah:
            self.init_ptah()

    def tearDown(self):
        import ptah.util
        ptah.util.tldata.clear()

        import ptah.security
        ptah.security.DEFAULT_ACL[:] = []

        from ptah.config import ATTACH_ATTR

        mod = sys.modules[self.__class__.__module__]
        if hasattr(mod, ATTACH_ATTR):
            delattr(mod, ATTACH_ATTR)

        testing.tearDown()
        transaction.abort()

    def render_route_view(self, context, request, route_name, view=''): # pragma: no cover
        directlyProvides(
            request, self.registry.getUtility(IRouteRequest, route_name))

        return render_view_to_response(context, request, view)

########NEW FILE########
__FILENAME__ = 0301
"""Ptah 0.3.x changes

Revision ID: 0301
Revises: None
Create Date: 2012-01-10 10:53:51.715491

"""

# revision identifiers, used by Alembic.
revision = '0301'
down_revision = None

import ptah
from alembic import op
from alembic import context
import sqlalchemy as sa
from sqlalchemy.engine import reflection


def upgrade():
    # it possible that this script is being called on new database
    # in this case we should not do anything
    insp = reflection.Inspector.from_engine(ptah.get_base().metadata.bind)

    if 'annotations' in [r['name'] for r in insp.get_columns('ptah_nodes')]:
        return

    # ptah_nodes
    op.add_column(
        'ptah_nodes',
        sa.Column('annotations', ptah.JsonDictType(), default={}))

    # ptah_content
    op.add_column(
        'ptah_content', sa.Column('lang', sa.String(12), default='en'))

    op.create_index(
        'ix_ptah_content_path', 'ptah_content', ('path',))

    # sqlite doesnt support column drop
    impl = context.get_impl()

    if impl.__dialect__ != 'sqlite':
        op.drop_column('ptah_content', 'view')
        op.drop_column('ptah_content', 'creators')
        op.drop_column('ptah_content', 'subjects')
        op.drop_column('ptah_content', 'publisher')
        op.drop_column('ptah_content', 'contributors')

    op.drop_table('test_sqla_table')


def downgrade():
    pass

########NEW FILE########
__FILENAME__ = test_api
from ptah.testing import TestCase


class StopExceptionTesting(TestCase):

    def test_api_stopexception_msg(self):
        from ptah import config

        err = config.StopException('Error message')

        self.assertEqual(str(err), '\nError message')
        self.assertEqual(err.print_tb(), 'Error message')

    def test_api_stopexception_exc(self):
        from ptah import config

        s_err = None
        try:
            raise ValueError('err')
        except Exception as exc:
            s_err = config.StopException(exc)

        self.assertIn("raise ValueError('err')", s_err.print_tb())


class LoadpackageTesting(TestCase):

    def test_stop_exc(self):
        from ptah import config

        err = ValueError('test')

        exc = config.StopException(err)
        self.assertIs(exc.exc, err)
        self.assertEqual(str(exc), '\ntest')

########NEW FILE########
__FILENAME__ = test_auth
from ptah.testing import PtahTestCase
from pyramid import testing


class Principal(object):

    def __init__(self, uri, name, login):
        self.__uri__ = uri
        self.name = name
        self.login = login


class TestAuthentication(PtahTestCase):

    _init_ptah = False

    def test_auth_provider(self):
        import ptah

        info = ptah.auth_service.authenticate(
            {'login': 'user', 'password': '12345'})

        self.assertFalse(info.status)
        self.assertIsNone(info.principal)

        class Provider(object):
            def authenticate(self, creds):
                if creds['login'] == 'user':
                    return Principal('1', 'user', 'user')

        ptah.auth_provider.register('test-provider', Provider)
        self.init_ptah()

        info = ptah.auth_service.authenticate(
            {'login': 'user', 'password': '12345'})

        self.assertTrue(info.status)
        self.assertEqual(info.__uri__, '1')

    def test_auth_provider_declarative(self):
        import ptah

        @ptah.auth_provider('test-provider')
        class Provider(object):

            def authenticate(self, creds):
                if creds['login'] == 'user':
                    return Principal('1', 'user', 'user')

        self.init_ptah()

        info = ptah.auth_service.authenticate(
            {'login': 'user', 'password': '12345'})

        self.assertTrue(info.status)
        self.assertEqual(info.__uri__, '1')

    def test_auth_provider_pyramid(self):
        import ptah

        class Provider(object):
            def authenticate(self, creds):
                if creds['login'] == 'user':
                    return Principal('1', 'user', 'user')

        config = testing.setUp()
        config.include('ptah')

        self.assertTrue(getattr(config, 'ptah_auth_provider'))

        config.ptah_auth_provider('test-provider', Provider)
        config.commit()

        info = ptah.auth_service.authenticate(
            {'login': 'user', 'password': '12345'})

        self.assertTrue(info.status)
        self.assertEqual(info.__uri__, '1')

    def test_auth_checker_default(self):
        import ptah
        self.init_ptah()

        principal = Principal('1', 'user', 'user')

        info = ptah.auth_service.authenticate_principal(principal)
        self.assertTrue(info.status)
        self.assertEqual(info.__uri__, '1')
        self.assertEqual(info.message, '')
        self.assertEqual(info.arguments, {})

    def test_auth_checker(self):
        import ptah

        principal = Principal('1', 'user', 'user')

        class Provider(object):
            def authenticate(self, creds):
                if creds['login'] == 'user':
                    return Principal('1', 'user', 'user')

        ptah.auth_provider.register('test-provider', Provider)

        @ptah.auth_checker
        def checker(info):
            info.message = 'Suspended'
            info.arguments['additional'] = 'test'
            return False

        self.init_ptah()

        info = ptah.auth_service.authenticate(
            {'login': 'user', 'password': '12345'})

        self.assertFalse(info.status)
        self.assertEqual(info.__uri__, '1')
        self.assertEqual(info.message, 'Suspended')
        self.assertEqual(info.arguments, {'additional': 'test'})

        principal = Principal('1', 'user', 'user')

        info = ptah.auth_service.authenticate_principal(principal)
        self.assertFalse(info.status)
        self.assertEqual(info.__uri__, '1')
        self.assertEqual(info.message, 'Suspended')
        self.assertEqual(info.arguments, {'additional': 'test'})

    def test_auth_checker_pyramid(self):
        import ptah

        principal = Principal('1', 'user', 'user')

        class Provider(object):
            def authenticate(self, creds):
                if creds['login'] == 'user':
                    return Principal('1', 'user', 'user')

        config = testing.setUp()
        config.include('ptah')

        def checker(info):
            info.message = 'Suspended'
            info.arguments['additional'] = 'test'
            return False

        config.ptah_auth_checker(checker)
        config.ptah_auth_provider('test-provider', Provider)

        info = ptah.auth_service.authenticate(
            {'login': 'user', 'password': '12345'})

        self.assertFalse(info.status)
        self.assertEqual(info.__uri__, '1')
        self.assertEqual(info.message, 'Suspended')
        self.assertEqual(info.arguments, {'additional': 'test'})

        principal = Principal('1', 'user', 'user')

        info = ptah.auth_service.authenticate_principal(principal)
        self.assertFalse(info.status)
        self.assertEqual(info.__uri__, '1')
        self.assertEqual(info.message, 'Suspended')
        self.assertEqual(info.arguments, {'additional': 'test'})

    def test_auth_get_set_userid(self):
        import ptah
        import ptah.util

        self.assertEqual(ptah.auth_service.get_userid(), None)

        ptah.auth_service.set_userid('user')
        self.assertEqual(ptah.auth_service.get_userid(), 'user')

        ptah.util.resetThreadLocalData(None)
        self.assertEqual(ptah.auth_service.get_userid(), None)

    def test_auth_get_set_effective_userid(self):
        import ptah
        import ptah.util

        self.assertEqual(ptah.auth_service.get_effective_userid(), None)

        ptah.auth_service.set_effective_userid('user')
        self.assertEqual(ptah.auth_service.get_effective_userid(), 'user')

        ptah.util.resetThreadLocalData(None)
        self.assertEqual(ptah.auth_service.get_effective_userid(), None)

        ptah.auth_service.set_userid('user')
        self.assertEqual(ptah.auth_service.get_effective_userid(), 'user')

        ptah.auth_service.set_effective_userid('user2')
        self.assertEqual(ptah.auth_service.get_effective_userid(), 'user2')

        ptah.auth_service.set_userid('user3')
        self.assertEqual(ptah.auth_service.get_effective_userid(), 'user2')

    def test_auth_principal(self):
        import ptah

        principal = Principal('1', 'user', 'user')
        def resolver(uri):
            if uri == 'test:1':
                return principal

        ptah.resolver.register('test', resolver)
        self.init_ptah()

        self.assertEqual(ptah.auth_service.get_current_principal(), None)

        ptah.auth_service.set_userid('test:1')
        self.assertEqual(ptah.auth_service.get_current_principal(), principal)

    def test_auth_principal_login(self):
        import ptah

        principal = Principal('1', 'user', 'user')
        class Provider(object):
            def get_principal_bylogin(self, login):
                if login == 'user':
                    return principal

        ptah.auth_provider.register('test-provider', Provider)
        self.init_ptah()

        self.assertEqual(
            ptah.auth_service.get_principal_bylogin('user2'), None)

        self.assertEqual(
            ptah.auth_service.get_principal_bylogin('user'), principal)


class TestPrincipalSearcher(PtahTestCase):

    _init_ptah = False

    def test_principal_searcher(self):
        import ptah

        principal = Principal('1', 'user', 'user')
        def search(term=''):
            if term == 'user':
                yield principal

        ptah.principal_searcher.register('test-provider', search)
        self.init_ptah()

        self.assertEqual(list(ptah.search_principals('user')), [principal])

    def test_principal_searcher_pyramid(self):
        import ptah

        principal = Principal('1', 'user', 'user')
        def search(term=''):
            if term == 'user':
                yield principal

        config = testing.setUp()
        config.include('ptah')
        config.ptah_principal_searcher('test-provider', search)

        self.assertEqual(list(ptah.search_principals('user')), [principal])


class TestSuperUser(PtahTestCase):

    _init_ptah = False

    def test_superuser_resolver(self):
        import ptah
        from ptah.authentication import SUPERUSER
        self.init_ptah()

        user = ptah.resolve(ptah.SUPERUSER_URI)
        self.assertIs(user, SUPERUSER)
        self.assertIsNone(ptah.resolve('ptah-auth:unknown'))
        self.assertEqual(repr(user), '<ptah Superuser>')

########NEW FILE########
__FILENAME__ = test_directives
""" directives tests """
import sys
from pyramid import testing

from zope import interface
from zope.interface.interfaces import IObjectEvent

from ptah import config
from ptah.testing import TestCase


class BaseTesting(TestCase):

    def _init_ptah(self, *args, **kw):
        self.config.include('ptah')
        self.config.scan(self.__class__.__module__)
        self.config.commit()
        self.config.autocommit = True

    def setUp(self):
        self.config = testing.setUp(autocommit=False)
        self.config.include('ptah')
        self.registry = self.config.registry

    def tearDown(self):
        mod = sys.modules[self.__class__.__module__]
        if hasattr(mod, config.ATTACH_ATTR):
            delattr(mod, config.ATTACH_ATTR)

        testing.tearDown()


class IContext(interface.Interface):
    pass


class IContext2(interface.Interface):
    pass


class Context(object):

    def __init__(self, iface):
        interface.directlyProvides(self, iface)


class TestSubscriberDirective(BaseTesting):

    def test_subscriber(self):
        events = []

        @config.subscriber(IContext)
        def testHandler(*args):
            events.append(args)

        self._init_ptah()

        sm = self.registry
        sm.subscribers((Context(IContext),), None)

        self.assertTrue(len(events) == 1)

        sm.subscribers((Context(IContext2),), None)
        self.assertTrue(len(events) == 1)

    def test_subscriber_multple(self):
        events = []

        @config.subscriber(IContext)
        @config.subscriber(IContext2)
        def testHandler(*args):
            events.append(args)

        self._init_ptah()

        sm = self.registry
        sm.subscribers((Context(IContext),), None)
        sm.subscribers((Context(IContext2),), None)

        self.assertTrue(len(events) == 2)

    def test_subscriber_object(self):
        from zope.interface.interfaces import ObjectEvent

        events = []

        @config.subscriber(IContext, IObjectEvent)
        def testSubscriber(*args):
            events.append(args)

        self._init_ptah()

        sm = self.config.registry
        sm.subscribers((ObjectEvent(Context(IContext)),), None)

        self.assertTrue(len(events) == 1)
        self.assertTrue(len(events[0]) == 2)


class TestExtraDirective(BaseTesting):

    def test_action(self):
        info = config.DirectiveInfo(0)

        action = config.Action(None, discriminator=('test', ))

        self.assertIsNone(action.hash)

        info.attach(action)

        self.assertIsNotNone(action.hash)
        self.assertIsNotNone(hash(action))
        self.assertRaises(TypeError, info.attach, action)
        self.assertEqual('<Action "test">', repr(action))
        self.assertIn('test_action\n', repr(info), '')

########NEW FILE########
__FILENAME__ = test_event
import ptah
from pyramid.exceptions import ConfigurationConflictError


class TestEvent(ptah.PtahTestCase):

    _init_ptah = False

    def test_event_registration(self):
        import ptah

        @ptah.event('TestEvent')
        class TestEvent(object):
            """ test event """

        self.init_ptah()

        storage = self.config.get_cfg_storage(ptah.event.ID_EVENT)

        self.assertIn(TestEvent, storage)
        ev = storage[TestEvent]
        self.assertIn(ev.name, storage)

    def test_event_registration_dupl(self):
        import ptah

        @ptah.event('TestEvent')
        class TestEvent1(object):
            """ test event """

        @ptah.event('TestEvent')
        class TestEvent2(object):
            """ test event """

        self.config.scan('ptah')
        self.config.scan(self.__class__.__module__)
        self.assertRaises(ConfigurationConflictError, self.init_ptah)

    def test_event_intr(self):
        import ptah

        @ptah.event('TestEvent')
        class TestEvent(object):
            """ test event """

        self.init_ptah()

        name = '{0}.{1}'.format(TestEvent.__module__, TestEvent.__name__)

        intr = self.registry.introspector.get(
            ptah.event.ID_EVENT,
            (ptah.event.ID_EVENT, name))
        self.assertIsNotNone(intr)
        self.assertIs(intr['ev'].factory, TestEvent)

########NEW FILE########
__FILENAME__ = test_formatter
""" formatter tests """
import pytz
from datetime import datetime, timedelta

import ptah
from ptah.testing import PtahTestCase


class TestFormatter(PtahTestCase):

    def test_datetime_formatter(self):
        format = self.request.fmt

        # format only datetime
        self.assertEqual(format.datetime('text string'), 'text string')

        # default format
        dt = datetime(2011, 2, 6, 10, 35, 45, 80, pytz.UTC)
        self.assertEqual(format.datetime(dt, 'short'),
                         '02/06/11 04:35 AM')
        self.assertEqual(format.datetime(dt, 'medium'),
                         'Feb 06, 2011 04:35 AM')
        self.assertEqual(format.datetime(dt, 'long'),
                         'February 06, 2011 04:35 AM -0600')
        self.assertEqual(format.datetime(dt, 'full'),
                         'Sunday, February 06, 2011 04:35:45 AM CST')

    def test_datetime_formatter2(self):
        format = self.request.fmt

        # datetime without timezone
        dt = datetime(2011, 2, 6, 10, 35, 45, 80)
        self.assertEqual(format.datetime(dt, 'short'),
                         '02/06/11 04:35 AM')

        # different format
        dt = datetime(2011, 2, 6, 10, 35, 45, 80, pytz.UTC)

        FORMAT = ptah.get_settings('format', self.registry)
        FORMAT['date_short'] = '%b %d, %Y'

        self.assertEqual(format.datetime(dt, 'short'),
                         'Feb 06, 2011 04:35 AM')

    def test_timedelta_formatter(self):
        format = self.request.fmt

        # format only timedelta
        self.assertEqual(format.timedelta('text string'), 'text string')

        # full format
        td = timedelta(hours=10, minutes=5, seconds=45)

        self.assertEqual(format.timedelta(td, 'full'),
                         '10 hour(s) 5 min(s) 45 sec(s)')

        # medium format
        self.assertEqual(format.timedelta(td, 'medium'),
                         '10:05:45')

        # seconds format
        self.assertEqual(format.timedelta(td, 'seconds'),
                         '36345.0000')

        # default format
        self.assertEqual(format.timedelta(td), '10:05:45')

    def test_size_formatter(self):
        format = self.request.fmt

        # format only timedelta
        self.assertEqual(format.size('text string'), 'text string')

        v = 1024
        self.assertEqual(format.size(v, 'b'), '1024 B')

        self.assertEqual(format.size(v, 'k'), '1.00 KB')

        self.assertEqual(format.size(1024*768, 'm'), '0.75 MB')
        self.assertEqual(format.size(1024*768*768, 'm'), '576.00 MB')

        self.assertEqual(format.size(1024*768*768, 'g'), '0.56 GB')

########NEW FILE########
__FILENAME__ = test_init
from pyramid.config import Configurator

import ptah
from ptah.testing import TestCase


class TestInitializeSql(TestCase):

    def test_ptahinit_sqla(self):
        config = Configurator(
            settings = {'sqlalchemy.url': 'sqlite://'})
        config.include('ptah')
        config.commit()

        config.ptah_init_sql()
        self.assertIsNotNone(ptah.get_base().metadata.bind)


class TestPtahInit(TestCase):

    def test_init_includeme(self):
        config = Configurator()
        config.include('ptah')
        config.commit()

        for name in ('ptah_init_settings', 'ptah_init_sql',
                     'ptah_init_manage', 'ptah_init_mailer',
                     'get_cfg_storage',
                     'ptah_get_settings', 'ptah_auth_checker',
                     'ptah_auth_provider', 'ptah_principal_searcher',
                     'ptah_uri_resolver', 'ptah_password_changer',
                     'ptah_populate', 'ptah_populate_step'):
            self.assertTrue(hasattr(config, name))

        from pyramid.interfaces import \
             IAuthenticationPolicy, IAuthorizationPolicy

        self.assertIsNotNone(
            config.registry.queryUtility(IAuthenticationPolicy))
        self.assertIsNotNone(
            config.registry.queryUtility(IAuthorizationPolicy))

    def test_init_ptah_init(self):
        config = Configurator()

        data = [False, False]

        def settings_initialized_handler(ev):
            data[1] = True

        sm = config.registry
        sm.registerHandler(
            settings_initialized_handler,
            (ptah.events.SettingsInitialized,))

        config.include('ptah')
        config.ptah_init_settings()
        config.commit()

        self.assertTrue(data[1])

    def test_init_ptah_init_settings_exception(self):
        config = Configurator(autocommit = True)

        class CustomException(Exception):
            pass

        def initialized_handler(ev):
            raise CustomException()

        sm = config.registry
        sm.registerHandler(
            initialized_handler,
            (ptah.events.SettingsInitialized,))

        config.include('ptah')

        err = None
        try:
            config.ptah_init_settings()
        except Exception as e:
            err = e

        self.assertIsInstance(err, ptah.config.StopException)
        self.assertIsInstance(err.exc, CustomException)


class TestDummyMailer(ptah.PtahTestCase):

    def test_dummy_mailer(self):
        from ptah.ptahsettings import DummyMailer

        PTAH = ptah.get_settings(ptah.CFG_ID_PTAH, self.registry)

        self.assertIsInstance(PTAH['Mailer'], DummyMailer)

        PTAH['Mailer'].send('test@example.com', 'to@example.com', 'msg')

########NEW FILE########
__FILENAME__ = test_jsfields
import pform
from ptah.testing import PtahTestCase
from pyramid.compat import text_type


def invalid_exc(func, *arg, **kw):
    from pform import Invalid
    try:
        func(*arg, **kw)
    except Invalid as e:
        return e
    else:
        raise AssertionError('Invalid not raised')


def strip(str):
    return ' '.join(s.strip() for s in str.split())


class TestJSDateTimeField(PtahTestCase):

    def _makeOne(self, name, **kw):
        from ptah.jsfields import JSDateTimeField
        return JSDateTimeField(name, **kw)

    def test_fields_jsdatetime_update(self):
        from datetime import datetime

        request = self.request
        field = self._makeOne('test')

        f = field.bind(request, '', pform.null, {})
        f.update()

        self.assertEqual(f.date_part, '')
        self.assertEqual(f.time_part, '')

        dt = datetime(2011, 1, 1, 10, 10)

        f = field.bind(request, '', dt, {})
        f.update()

        self.assertEqual(f.date_part, '01/01/2011')
        self.assertEqual(f.time_part, '10:10 AM')

    def test_fields_jsdatetime_extract(self):
        request = self.request
        field = self._makeOne('test')

        f = field.bind(request, '', pform.null, {})
        f.update()
        self.assertIs(f.extract('default'), 'default')

        f = field.bind(request, '', pform.null, {'test.date': ''})
        f.update()
        self.assertIs(f.extract(), pform.null)

        f = field.bind(request, '', pform.null,
                       {'test.date': '12/01/2011'})
        f.update()
        self.assertIs(f.extract('default'), 'default')

        f = field.bind(request, '', pform.null,
                       {'test.date': '12/01/2011',
                        'test.time': ''})
        f.update()
        self.assertIs(f.extract(), pform.null)

        f = field.bind(request, '', pform.null,
                       {'test.date': 'exception',
                        'test.time': 'exception'})
        f.update()
        self.assertIs(f.extract(), pform.null)

        f = field.bind(request, '', pform.null,
                       {'test.date': '12/01/2011',
                        'test.time': '10:10 AM'})
        f.update()
        self.assertEqual(f.extract(), '2011-12-01T10:10:00')


class TestJSDateField(PtahTestCase):

    def _makeOne(self, **kw):
        from ptah.jsfields import JSDateField
        return JSDateField('test', **kw)

    def test_serialize_null(self):
        typ = self._makeOne()
        result = typ.to_form(pform.null)
        self.assertEqual(result, pform.null)

    def test_serialize_with_garbage(self):
        typ = self._makeOne()
        e = invalid_exc(typ.to_form, 'garbage')
        self.assertEqual(text_type(e), '"garbage" is not a date object')

    def test_serialize_with_date(self):
        import datetime
        typ = self._makeOne()
        date = datetime.date.today()
        result = typ.to_form(date)
        expected = date.strftime('%m/%d/%Y')
        self.assertEqual(result, expected)

    def test_serialize_with_datetime(self):
        import datetime
        typ = self._makeOne()
        dt = datetime.datetime.now()
        result = typ.to_form(dt)
        expected = dt.strftime('%m/%d/%Y')
        self.assertEqual(result, expected)

    def test_deserialize_invalid(self):
        typ = self._makeOne()
        e = invalid_exc(typ.to_field, 'garbage')
        self.assertTrue('Invalid' in e.msg)

    def test_deserialize_invalid_weird(self):
        typ = self._makeOne()
        e = invalid_exc(typ.to_field, '10-10-10-10')
        self.assertTrue('Invalid' in e.msg)

    def test_deserialize_null(self):
        typ = self._makeOne()
        result = typ.to_field(pform.null)
        self.assertEqual(result, pform.null)

    def test_deserialize_empty(self):
        typ = self._makeOne()
        result = typ.to_field('')
        self.assertEqual(result, pform.null)

    def test_deserialize_success_date(self):
        import datetime
        typ = self._makeOne()
        date = datetime.date.today()
        iso = date.strftime('%m/%d/%Y')
        result = typ.to_field(iso)
        self.assertEqual(result, date)

    def test_deserialize_success_datetime(self):
        import datetime

        dt = datetime.datetime.now()
        typ = self._makeOne()
        iso = dt.strftime('%m/%d/%Y')
        result = typ.to_field(iso)
        self.assertEqual(result.isoformat(), dt.date().isoformat())

########NEW FILE########
__FILENAME__ = test_mail
from ptah import mail
from pyramid.compat import bytes_
from pyramid.testing import DummyRequest

from ptah.testing import PtahTestCase


class Content(object):
    pass


class TestMailTemplate(PtahTestCase):

    def _make_one(self):
        from ptah.mail import MailTemplate

        class MyMailTemplate(MailTemplate):
            template = 'ptah:tests/test_mail_tmpl.pt'
            subject = 'Test subject'
            charset = 'utf-8'
            content_type = 'text/html'

        return MyMailTemplate

    def test_mailtmpl_ctor(self):
        tmpl = mail.MailTemplate(Content(), DummyRequest(),
                                 testattr = 'testattr')

        self.assertEqual(tmpl.testattr, 'testattr')

    def test_mailtmpl_basics(self):
        cls = self._make_one()
        cls.message_id = 'message id'

        tmpl = cls(Content(), DummyRequest())()

        self.assertEqual(
            tmpl['Content-Type'], 'text/html; charset="utf-8"')
        self.assertEqual(
            tmpl['Content-Transfer-Encoding'], 'base64')
        self.assertEqual(
            tmpl['Subject'].encode(), '=?utf-8?q?Test_subject?=')
        self.assertEqual(
            tmpl['Message-ID'], 'message id')
        self.assertEqual(
            tmpl['From'], 'Site administrator <admin@localhost>')

    def test_mailtmpl_from(self):
        cls = self._make_one()

        cls.from_name = 'Test'
        cls.from_address = 'ptah@ptahproject.com'

        tmpl = cls(Content(), DummyRequest())()
        self.assertEqual(tmpl['From'], 'Test <ptah@ptahproject.com>')

    def test_mailtmpl_to(self):
        cls = self._make_one()

        cls.to_address = 'ptah@ptahproject.com'

        tmpl = cls(Content(), DummyRequest())()
        self.assertEqual(tmpl['To'], 'ptah@ptahproject.com')

    def test_mailtmpl_headers(self):
        cls = self._make_one()

        tmpl = cls(Content(), DummyRequest())
        self.assertFalse(tmpl.has_header('X-Mailer'))

        tmpl.add_header('X-Mailer', 'ptah')
        self.assertTrue(tmpl.has_header('X-Mailer'))

        msg = tmpl()
        self.assertEqual(msg['X-Mailer'], 'ptah')

    def test_mailtmpl_headers_encoding(self):
        cls = self._make_one()

        tmpl = cls(Content(), DummyRequest())
        tmpl.add_header('X-Mailer', 'ptah', True)

        msg = tmpl()
        self.assertEqual(msg['X-Mailer'].encode(), '=?utf-8?q?ptah?=')

    def test_mailtmpl_headers_gen(self):
        cls = self._make_one()
        tmpl = cls(Content(), DummyRequest())

        msg = tmpl(**{'X-Mailer': 'ptah'})
        self.assertEqual(msg['X-Mailer'], 'ptah')

        msg = tmpl(**{'X-Mailer': ('ptah', True)})
        self.assertEqual(str(msg['X-Mailer'].encode()), '=?utf-8?q?ptah?=')

    def test_mailtmpl_attachment(self):
        cls = self._make_one()
        tmpl = cls(Content(), DummyRequest())
        self.assertEqual(tmpl.get_attachments(), [])

        tmpl.add_attachment(bytes_('File data','utf-8'),'text/plain','file.txt')
        self.assertEqual(
            tmpl.get_attachments(),
            [(bytes_('File data','utf-8'),'text/plain','file.txt','attachment')])

        msg = tmpl()
        payload = msg.get_payload()

        self.assertTrue(msg.is_multipart())
        self.assertEqual(
            payload[0]['Content-Id'], bytes_('<file.txt@ptah>','utf-8'))
        self.assertEqual(
            payload[0]['Content-Disposition'],
            bytes_('attachment; filename="file.txt"','utf-8'))

    def test_mailtmpl_attachment_inline(self):
        cls = self._make_one()
        tmpl = cls(Content(), DummyRequest())
        self.assertEqual(tmpl.get_attachments(), [])

        tmpl.add_attachment(bytes_('File data','utf-8'),
                            'text/plain', 'file.txt', 'inline')
        self.assertEqual(
            tmpl.get_attachments(),
            [(bytes_('File data','utf-8'), 'text/plain', 'file.txt', 'inline')])

        msg = tmpl()
        payload = msg.get_payload()[0]
        payload = payload.get_payload()[-1]

        self.assertEqual(
            payload['Content-Disposition'],
            bytes_('inline; filename="file.txt"','utf-8'))

    def test_mailtmpl_alternative(self):
        cls = self._make_one()

        tmpl = cls(Content(), DummyRequest())
        tmpl.add_header('x-tmpl', 'Template1')
        tmpl2 = cls(Content(), DummyRequest())
        tmpl2.add_header('x-tmpl', 'Template2')

        tmpl.add_alternative(tmpl2)
        self.assertEqual(tmpl.get_alternative(), [tmpl2])

        msg = tmpl()

        payload = msg.get_payload()
        self.assertEqual(msg['x-tmpl'], 'Template1')
        self.assertEqual(payload[1]['x-tmpl'], 'Template2')

    def test_mailtmpl_send(self):
        cls = self._make_one()
        tmpl = cls(Content(), DummyRequest())

        data = []
        class Mailer(object):

            def send(self, frm, to, msg):
                data.append((frm, to, msg))

        self.config.ptah_init_mailer(Mailer())

        tmpl.send()

        self.assertEqual(
            data[0][0], 'Site administrator <admin@localhost>')
        self.assertEqual(
            data[0][1], None)
        self.assertIn('From: Site administrator <admin@localhost>',
                      data[0][2].as_string())

        tmpl.send('test@ptahproject.org')
        self.assertEqual(data[-1][1], 'test@ptahproject.org')

########NEW FILE########
__FILENAME__ = test_migrate
import os
import ptah
import shutil
import tempfile
from pyramid.config import ConfigurationConflictError

ptah.register_migration('ptah', 'ptah:tests/migrations')


class TestRegisterMigration(ptah.PtahTestCase):

    _init_ptah = False

    def test_register(self):
        from ptah.migrate import MIGRATION_ID

        ptah.register_migration(
            'test', 'ptah.tests:migrations', 'Ptah database migration')
        self.init_ptah()

        st = ptah.get_cfg_storage(MIGRATION_ID)

        self.assertIn('test', st)
        self.assertEqual(st['test'], 'ptah.tests:migrations')

    def test_register_conflict(self):
        ptah.register_migration(
            'test', 'ptah.tests:migrations', 'Ptah database migration')
        ptah.register_migration(
            'test', 'ptah.tests:migrations', 'Ptah database migration')

        self.assertRaises(ConfigurationConflictError, self.init_ptah)


class TestPyramidDirective(ptah.PtahTestCase):

    def setUp(self):
        from ptah import migrate

        self._pkgs = []
        def upgrade(pkg):
            self._pkgs.append(pkg)

        self.orig_upgrade = migrate.upgrade
        migrate.upgrade = upgrade

        super(TestPyramidDirective, self).setUp()

    def tearDown(self):
        super(TestPyramidDirective, self).tearDown()

        from ptah import migrate
        migrate.upgrade = self.orig_upgrade

    def test_pyramid_directive(self):
        from pyramid.config import Configurator

        config = Configurator()
        config.include('ptah')

        self.assertTrue(hasattr(config, 'ptah_migrate'))

    def test_directive_execution(self):
        from pyramid.config import Configurator

        config = Configurator()
        config.include('ptah')
        config.scan(self.__class__.__module__)
        config.ptah_migrate()
        config.commit()

        self.assertEqual(self._pkgs, ['ptah'])


class TestScriptDirectory(ptah.PtahTestCase):

    _init_ptah = False

    def test_unknown_package(self):
        self.init_ptah()

        from ptah.migrate import ScriptDirectory

        self.assertRaises(ValueError, ScriptDirectory, 'unknown')

    def test_normal(self):
        self.init_ptah()
        self.config.get_cfg_storage(
            'ptah:migrate')['ptah']='ptah:tests/migrations'

        from ptah.migrate import ScriptDirectory

        script = ScriptDirectory('ptah')

        self.assertEqual(
            script.dir,
            os.path.join(os.path.dirname(ptah.__file__), 'scripts'))

        self.assertEqual(
            script.versions,
            os.path.join(os.path.dirname(ptah.__file__), 'tests', 'migrations'))

    def test_doesnt_exist(self):
        from alembic.util import CommandError
        from ptah.migrate import ScriptDirectory

        ptah.register_migration('test', 'ptah:unknown_migrations')
        self.init_ptah()

        self.assertRaises(CommandError, ScriptDirectory, 'test')


class BaseScript(ptah.PtahTestCase):

    def setUp(self):
        from ptah import migrate

        self.dirs = dirs = {}

        class ScriptDirectory(migrate.ScriptDirectory):

            def __init__(self, pkg):
                if pkg in dirs:
                    dir = dirs[pkg]
                else:
                    dir = tempfile.mkdtemp()
                    dirs[pkg] = dir

                self.dir = os.path.join(
                    os.path.dirname(ptah.__file__), 'scripts')
                self.versions = dir

        self.orig_ScriptDirectory = migrate.ScriptDirectory
        migrate.ScriptDirectory = ScriptDirectory

        super(BaseScript, self).setUp()

    def tearDown(self):
        super(BaseScript, self).tearDown()

        for dir in self.dirs.values():
            shutil.rmtree(dir)

        from ptah import migrate
        migrate.ScriptDirectory = self.orig_ScriptDirectory


class TestRevision(BaseScript):

    def test_revision_default(self):
        from ptah.migrate import revision

        rev = revision('test', message='Test message')
        self.assertIn('{0}.py'.format(rev), os.listdir(self.dirs['test']))

    def test_revision_custom(self):
        from ptah.migrate import revision

        rev = revision('test', rev='001', message='Test message')
        self.assertEqual(rev, '001')
        self.assertIn('001.py', os.listdir(self.dirs['test']))

        self.assertRaises(
            KeyError, revision, 'test', rev='001')


class TestUpdateVersions(BaseScript):

    _init_ptah = False

    def test_update_force(self):
        from ptah.migrate import Version, revision, update_versions

        ptah.register_migration(
            'test', 'ptah.tests:migrations', force=True)
        self.init_ptah()

        revision('test', message='Test message')

        update_versions(self.registry)

        session = ptah.get_session()

        versions = dict((v.package, v.version_num)
                        for v in session.query(Version).all())
        self.assertNotIn('test', versions)

    def test_update_versions(self):
        from ptah.migrate import Version, revision, update_versions

        ptah.register_migration('test', 'ptah.tests:migrations')
        self.init_ptah()

        rev = revision('test', message='Test message')

        update_versions(self.registry)

        session = ptah.get_session()

        versions = dict((v.package, v.version_num)
                        for v in session.query(Version).all())
        self.assertIn('test', versions)
        self.assertEqual(versions['test'], rev)

    def test_update_version_exists(self):
        from ptah.migrate import Version, revision, update_versions

        ptah.register_migration('test', 'ptah.tests:migrations')
        self.init_ptah()

        revision('test', message='Test message')

        session = ptah.get_session()

        session.add(Version(package='test', version_num='123'))
        session.flush()

        update_versions(self.registry)

        versions = dict((v.package, v.version_num)
                        for v in session.query(Version).all())
        self.assertIn('test', versions)
        self.assertEqual(versions['test'], '123')


class TestUpgrade(BaseScript):

    _init_ptah = False

    def test_upgrade_to_rev(self):
        from ptah.migrate import Version, revision, upgrade

        ptah.register_migration(
            'test', 'ptah.tests:migrations', force=True)
        self.init_ptah()

        rev1 = revision('test', message='Test message1')
        revision('test', message='Test message2')

        upgrade('test:%s'%rev1)

        versions = dict((v.package, v.version_num)
                        for v in ptah.get_session().query(Version).all())
        self.assertEqual(versions['test'], rev1)

    def test_upgrade_to_head(self):
        from ptah.migrate import Version, revision, upgrade

        ptah.register_migration(
            'test', 'ptah.tests:migrations', force=True)
        self.init_ptah()

        revision('test', message='Test message1')
        rev2 = revision('test', message='Test message2')

        upgrade('test:head')

        versions = dict((v.package, v.version_num)
                        for v in ptah.get_session().query(Version).all())
        self.assertEqual(versions['test'], rev2)

    def test_upgrade_to_head_by_default(self):
        from ptah.migrate import Version, revision, upgrade

        ptah.register_migration(
            'test', 'ptah.tests:migrations', force=True)
        self.init_ptah()

        revision('test', message='Test message1')
        rev2 = revision('test', message='Test message2')

        upgrade('test')

        versions = dict((v.package, v.version_num)
                        for v in ptah.get_session().query(Version).all())
        self.assertEqual(versions['test'], rev2)

    def test_upgrade_to_same_rev(self):
        from ptah.migrate import Version, revision, upgrade

        ptah.register_migration(
            'test', 'ptah.tests:migrations', force=True)
        self.init_ptah()

        revision('test', message='Test message1')
        rev2 = revision('test', message='Test message2')

        upgrade('test')

        upgrade('test')

        versions = dict((v.package, v.version_num)
                        for v in ptah.get_session().query(Version).all())
        self.assertEqual(versions['test'], rev2)

    def test_upgrade_in_two_steps(self):
        from ptah.migrate import Version, revision, upgrade

        ptah.register_migration(
            'test', 'ptah.tests:migrations', force=True)
        self.init_ptah()

        rev1 = revision('test', message='Test message1')
        rev2 = revision('test', message='Test message2')

        upgrade('test:%s'%rev1)
        versions = dict((v.package, v.version_num)
                        for v in ptah.get_session().query(Version).all())
        self.assertEqual(versions['test'], rev1)

        upgrade('test')
        versions = dict((v.package, v.version_num)
                        for v in ptah.get_session().query(Version).all())
        self.assertEqual(versions['test'], rev2)

    def test_startup_check_version(self):
        from ptah.migrate import Version, revision, check_version

        ptah.register_migration(
            'test1', 'ptah.tests1:migrations')
        ptah.register_migration(
            'test2', 'ptah.tests2:migrations')
        self.init_ptah()

        rev1 = revision('test1', message='Test message1')
        rev2 = revision('test2', message='Test message2')

        session = ptah.get_session()
        session.add(Version(package='test1', version_num=rev1))
        session.add(Version(package='test2', version_num=rev2))
        session.flush()

        exc = None
        try:
            check_version(None)
        except SystemExit as err: # pragma: no cover
            exc = err

        self.assertIsNone(exc)

    def test_startup_check_version_exit(self):
        from ptah.migrate import revision, check_version

        ptah.register_migration(
            'test1', 'ptah.tests1:migrations')
        ptah.register_migration(
            'test2', 'ptah.tests2:migrations')
        self.init_ptah()

        revision('test1', message='Test message1')
        revision('test2', message='Test message2')

        exc = None
        try:
            check_version(None)
        except SystemExit as err: # pragma: no cover
            exc = err

        self.assertIsInstance(exc, SystemExit)

########NEW FILE########
__FILENAME__ = test_pagination
import ptah
from ptah.testing import TestCase


class TestPagination(TestCase):

    def test_pagination_values(self):
        page = ptah.Pagination(10)

        self.assertEqual(page.page_size, 10)
        self.assertEqual(page.left_neighbours, 3)
        self.assertEqual(page.right_neighbours, 3)

        page = ptah.Pagination(11, 5, 2)
        self.assertEqual(page.page_size, 11)
        self.assertEqual(page.left_neighbours, 5)
        self.assertEqual(page.right_neighbours, 2)

        self.assertEqual(page.offset(3), (page.page_size*2, page.page_size))

    def test_pagination_nb_begin(self):
        page = ptah.Pagination(10, 2, 2)

        self.assertRaises(ValueError, page, 1000, 0)

        self.assertEqual(
            page(1000, 1)[0], [1, 2, 3, None, 100])

        self.assertEqual(
            page(1000, 2)[0], [1, 2, 3, 4, None, 100])

        self.assertEqual(
            page(1000, 3)[0], [1, 2, 3, 4, 5, None, 100])

        self.assertEqual(
            page(1000, 4)[0], [1, 2, 3, 4, 5, 6, None, 100])

        self.assertEqual(
            page(1000, 5)[0], [1, None, 3, 4, 5, 6, 7, None, 100])

        self.assertEqual(
            page(1000, 6)[0], [1, None, 4, 5, 6, 7, 8, None, 100])


    def test_pagination_nb_end(self):
        page = ptah.Pagination(10, 2, 2)

        self.assertEqual(
            page(1000, 95)[0], [1, None, 93, 94, 95, 96, 97, None, 100])

        self.assertEqual(
            page(1000, 96)[0], [1, None, 94, 95, 96, 97, 98, None, 100])

        self.assertEqual(
            page(1000, 97)[0], [1, None, 95, 96, 97, 98, 99, 100])

        self.assertEqual(
            page(1000, 98)[0], [1, None, 96, 97, 98, 99, 100])

        self.assertEqual(
            page(1000, 99)[0], [1, None, 97, 98, 99, 100])

        self.assertEqual(
            page(1000, 100)[0], [1, None, 98, 99, 100])

    def test_pagination_zero_nb(self):
        page = ptah.Pagination(10, 0, 0)

        self.assertEqual(
            page(1000, 1)[0], [1, None, 100])

        self.assertEqual(
            page(1000, 2)[0], [1, 2, None, 100])

        self.assertEqual(
            page(1000, 3)[0], [1, None, 3, None, 100])

    def test_pagination_one_nb(self):
        page = ptah.Pagination(10, 1, 1)

        self.assertEqual(
            page(1000, 1)[0], [1, 2, None, 100])

        self.assertEqual(
            page(1000, 2)[0], [1, 2, 3, None, 100])

        self.assertEqual(
            page(1000, 3)[0], [1, 2, 3, 4, None, 100])

        self.assertEqual(
            page(1000, 4)[0], [1, None, 3, 4, 5, None, 100])

    def test_pagination_prev_next(self):
        page = ptah.Pagination(10, 3, 3)

        self.assertEqual(page(1000, 1)[1], None)
        self.assertEqual(page(1000, 2)[1], 1)
        self.assertEqual(page(1000, 3)[1], 2)
        self.assertEqual(page(1000, 100)[1], 99)

        self.assertEqual(page(1000, 100)[2], None)
        self.assertEqual(page(1000, 99)[2], 100)
        self.assertEqual(page(1000, 98)[2], 99)
        self.assertEqual(page(1000, 1)[2], 2)

########NEW FILE########
__FILENAME__ = test_password
# -*- coding: utf-8 -*-
import pform
import ptah
from ptah import config
from ptah.testing import TestCase, PtahTestCase
from pyramid import testing
from pyramid.compat import text_, bytes_
from pyramid.exceptions import ConfigurationConflictError


class Principal(object):

    def __init__(self, uri, name, login):
        self.__uri__ = uri
        self.name = name
        self.login = login


class TestPasswordSchema(PtahTestCase):

    def test_password_required(self):
        from ptah.password import PasswordSchema

        pwdSchema = PasswordSchema.bind(self.request, params={})

        data, errors = pwdSchema.extract()
        self.assertEqual(len(errors), 2)
        self.assertEqual(errors[0].field.name, 'password')

    def test_password_equal(self):
        from ptah.password import PasswordSchema

        pwdSchema = PasswordSchema.bind(
            self.request,
            params={'password': '12345', 'confirm_password': '123456'})
        data, errors = pwdSchema.extract()

        self.assertEqual(len(errors), 1)
        self.assertIsInstance(errors[0].field, pform.Fieldset)
        self.assertEqual(
            errors[0].msg[0],
            "Password and Confirm Password should be the same.")

    def test_password(self):
        from ptah.password import PasswordSchema

        pwdSchema = PasswordSchema.bind(
            self.request,
            params={'password': '12345', 'confirm_password': '12345'})
        data, errors = pwdSchema.extract()
        self.assertEqual(len(errors), 0)

    def test_password_validator(self):
        from ptah.password import passwordValidator, PasswordTool

        vp = PasswordTool.validate

        def validatePassword(self, pwd):
            return 'Error'

        PasswordTool.validate = validatePassword

        self.assertRaises(
            pform.Invalid, passwordValidator, None, 'pwd')

        PasswordTool.validate = vp


class TestSHAPasswordManager(TestCase):

    def test_password_ssha(self):
        from ptah.password import SSHAPasswordManager

        manager = SSHAPasswordManager()

        password = text_("right А", 'utf-8')
        encoded = manager.encode(password, salt=bytes_("",'utf-8'))

        self.assertEqual(
            encoded, bytes_('{ssha}BLTuxxVMXzouxtKVb7gLgNxzdAI=','ascii'))
        self.assertTrue(manager.check(encoded, password))
        self.assertFalse(manager.check(encoded, password + "wrong"))

        encoded = manager.encode(password)
        self.assertTrue(manager.check(encoded, password))


class TestPlainPasswordManager(TestCase):

    def test_password_plain(self):
        from ptah.password import PlainPasswordManager

        manager = PlainPasswordManager()

        password = "test pwd"
        encoded = manager.encode(password, salt="")

        self.assertEqual(encoded, '{plain}test pwd')
        self.assertTrue(manager.check(encoded, password))
        self.assertTrue(manager.check(password, password))
        self.assertFalse(manager.check(encoded, password + "wrong"))

        encoded = manager.encode(password)
        self.assertTrue(manager.check(encoded, password))


class TestPasswordSettings(PtahTestCase):

    def test_password_settings(self):
        from ptah.password import \
             PlainPasswordManager, SSHAPasswordManager

        cfg = ptah.get_settings(ptah.CFG_ID_PTAH, self.registry)

        cfg['pwd_manager'] = 'unknown'
        self.assertIsInstance(ptah.pwd_tool.manager, PlainPasswordManager)

        cfg['pwd_manager'] = 'ssha'
        self.assertIsInstance(ptah.pwd_tool.manager, SSHAPasswordManager)


class TestPasswordChanger(PtahTestCase):

    _init_ptah = False

    def test_password_changer_decl(self):
        import ptah

        @ptah.password_changer('test-schema')
        def changer(schema):
            """ """

        self.init_ptah()

        from ptah.password import ID_PASSWORD_CHANGER
        changers = config.get_cfg_storage(ID_PASSWORD_CHANGER)

        self.assertIn('test-schema', changers)
        self.assertIs(changers['test-schema'], changer)

    def test_password_changer_decl_conflict(self):
        import ptah

        @ptah.password_changer('test-schema')
        def changer(schema):
            """ """

        @ptah.password_changer('test-schema')
        def changer2(schema):
            """ """

        self.assertRaises(ConfigurationConflictError, self.init_ptah)

    def test_password_changer(self):
        import ptah

        @ptah.password_changer('test-schema')
        def changer(schema):
            """ """

        self.init_ptah()

        p = Principal('test-schema:numbers_numbers', 'name', 'login')
        self.assertTrue(ptah.pwd_tool.can_change_password(p))

        p = Principal('unknown-schema:numbers_numbers', 'name', 'login')
        self.assertFalse(ptah.pwd_tool.can_change_password(p))

    def test_password_changer_pyramid(self):
        import ptah

        def changer(schema):
            """ """

        config = testing.setUp()
        config.include('ptah')
        config.ptah_password_changer('test-schema', changer)

        p = Principal('test-schema:numbers_numbers', 'name', 'login')
        self.assertTrue(ptah.pwd_tool.can_change_password(p))


class TestPasswordTool(PtahTestCase):

    _init_ptah = False

    def test_password_encode(self):
        self.init_ptah()

        cfg = ptah.get_settings(ptah.CFG_ID_PTAH, self.registry)
        cfg['pwd_manager'] = 'plain'

        encoded = ptah.pwd_tool.encode('12345')
        self.assertEqual(encoded, '{plain}12345')

    def test_password_check(self):
        self.init_ptah()

        cfg = ptah.get_settings(ptah.CFG_ID_PTAH, self.registry)
        cfg['pwd_manager'] = 'ssha'

        self.assertFalse(ptah.pwd_tool.check('12345', '12345'))
        self.assertTrue(ptah.pwd_tool.check('{plain}12345', '12345'))
        self.assertFalse(ptah.pwd_tool.check('{plain}12345', '123455'))
        self.assertFalse(ptah.pwd_tool.check('{unknown}12345', '123455'))

    def test_password_passcode(self):
        p = Principal('test-schema:test', 'name', 'login')
        principals = {'test-schema:test': p}

        @ptah.resolver('test-schema')
        def resolver(uri):
            return principals.get(uri)

        self.init_ptah()

        token = ptah.pwd_tool.generate_passcode(p)
        self.assertIsNotNone(token)

        newp = ptah.pwd_tool.get_principal(token)
        self.assertIs(newp, p)

        ptah.pwd_tool.remove_passcode(token)

        newp = ptah.pwd_tool.get_principal(token)
        self.assertIsNone(newp)

    def test_password_change_password(self):
        p = Principal('test-schema:test', 'name', 'login')
        principals = {'test-schema:test': p}

        @ptah.resolver('test-schema')
        def resolver(uri):
            return principals.get(uri)

        @ptah.password_changer('test-schema')
        def changer(principal, password):
            p.password = password

        self.init_ptah()

        token = ptah.pwd_tool.generate_passcode(p)
        self.assertIsNotNone(token)

        newp = ptah.pwd_tool.get_principal(token)
        self.assertIs(newp, p)

        self.assertTrue(ptah.pwd_tool.change_password(token, '12345'))
        self.assertEqual(p.password, '{plain}12345')

        newp = ptah.pwd_tool.get_principal(token)
        self.assertIsNone(newp)

        self.assertFalse(ptah.pwd_tool.change_password('unknown', '12345'))

    def test_password_validate(self):
        self.init_ptah()

        cfg = ptah.get_settings(ptah.CFG_ID_PTAH, self.registry)
        cfg['pwd_min_length'] = 5
        self.assertEqual(ptah.pwd_tool.validate('1234'),
                         'Password should be at least 5 characters.')

        cfg['pwd_letters_digits'] = True
        self.assertEqual(ptah.pwd_tool.validate('123456'),
                         'Password should contain both letters and digits.')

        cfg['pwd_letters_mixed_case'] = True
        self.assertEqual(ptah.pwd_tool.validate('abs456'),
                         'Password should contain letters in mixed case.')

        self.assertIsNone(ptah.pwd_tool.validate('aBs456'))

########NEW FILE########
__FILENAME__ = test_populate
import sqlalchemy as sqla
import ptah
from ptah.populate import POPULATE_ID, Populate
from pyramid import testing
from pyramid.exceptions import ConfigurationConflictError


class TestPopulateDirective(ptah.PtahTestCase):

    _init_ptah = False

    def test_step_registration(self):
        import ptah

        @ptah.populate('step', title='Step', requires=['test-dep'])
        def step(registry):
            """ """

        self.init_ptah()

        data = ptah.get_cfg_storage(POPULATE_ID)

        self.assertIn('step', data)
        self.assertIs(data['step']['factory'], step)
        self.assertEqual(data['step']['title'], 'Step')
        self.assertTrue(data['step']['active'])
        self.assertEqual(data['step']['requires'], ['test-dep'])

    def test_step_pyramid_registration(self):

        def step(registry):
            """ """

        config = testing.setUp()
        config.include('ptah')
        config.ptah_populate_step('step', factory=step,
                                  title='Test', active=False)
        config.commit()

        data = config.get_cfg_storage(POPULATE_ID)

        self.assertIn('step', data)
        self.assertIs(data['step']['factory'], step)
        self.assertEqual(data['step']['title'], 'Test')
        self.assertFalse(data['step']['active'])
        self.assertEqual(data['step']['requires'], ())

    def test_step_registration_conflicts(self):
        import ptah

        @ptah.populate('step')
        @ptah.populate('step')
        def step(registry):
            """ """

        self.assertRaises(ConfigurationConflictError, self.init_ptah)


class TestPyramidDrective(ptah.PtahTestCase):

    def test_directive_execute(self):
        data = [False, False]
        def step1(registry):
            data[0] = True

        def step2(registry): # pragma: no cover
            data[0] = True

        self.config.ptah_populate_step(
            'custom-step1', title='Custom step 1',
            active=True, factory=step1)

        self.config.ptah_populate_step(
            'custom-step2', title='Custom step 2',
            active=False, factory=step2)

        self.config.ptah_populate()

        self.assertTrue(data[0])
        self.assertFalse(data[1])

    def test_directive_execute_populate_mode(self):
        data = [False]
        def step(registry): # pragma: no cover
            data[0] = True

        self.config.ptah_populate_step(
            'custom-step', title='Custom step',
            active=True, factory=step)

        import ptah
        ptah.POPULATE = True

        self.config.ptah_populate()

        ptah.POPULATE = False

        self.assertFalse(data[0])


class TestListSteps(ptah.PtahTestCase):

    def test_list_simple(self):
        def step1(registry):
            """ """
        def step2(registry):
            """ """

        self.config.ptah_populate_step(
            'custom-step1', title='Custom step 1',
            active=True, factory=step1)

        self.config.ptah_populate_step(
            'custom-step2', title='Custom step 2',
            active=False, factory=step2)

        steps = Populate(self.registry).list_steps()
        steps = dict((s['name'], s) for s in steps)

        self.assertIn('custom-step1', steps)
        self.assertNotIn('custom-step2', steps)
        self.assertEqual(steps['custom-step1']['factory'], step1)

    def test_list_all(self):
        def step1(registry):
            """ """
        def step2(registry):
            """ """

        self.config.ptah_populate_step(
            'custom-step1', title='Custom step 1',
            active=True, factory=step1)

        self.config.ptah_populate_step(
            'custom-step2', title='Custom step 2',
            active=False, factory=step2)

        steps = Populate(self.registry).list_steps(all=True)
        steps = dict((s['name'], s) for s in steps)

        self.assertIn('custom-step1', steps)
        self.assertIn('custom-step2', steps)
        self.assertEqual(steps['custom-step1']['factory'], step1)
        self.assertEqual(steps['custom-step2']['factory'], step2)

    def test_list_explicit(self):
        def step1(registry):
            """ """
        def step2(registry):
            """ """

        self.config.ptah_populate_step(
            'custom-step1', title='Custom step 1',
            active=True, factory=step1)

        self.config.ptah_populate_step(
            'custom-step2', title='Custom step 2',
            active=False, factory=step2)

        steps = Populate(self.registry).list_steps(('custom-step2',))
        steps = dict((s['name'], s) for s in steps)

        self.assertNotIn('custom-step1', steps)
        self.assertIn('custom-step2', steps)

    def test_list_requires_inactive(self):
        def step1(registry):
            """ """
        def step2(registry):
            """ """
        self.config.ptah_populate_step(
            'custom-step1', title='Custom step 1',
            active=True, requires=('custom-step2',), factory=step1)
        self.config.ptah_populate_step(
            'custom-step2', title='Custom step 2',
            active=False, factory=step2)

        steps = Populate(self.registry).list_steps()
        d_steps = dict((s['name'], s) for s in steps)

        self.assertIn('custom-step1', d_steps)
        self.assertIn('custom-step2', d_steps)

    def test_list_requires_order(self):
        def step1(registry):
            """ """
        def step2(registry):
            """ """
        self.config.ptah_populate_step(
            'custom-step1', title='Custom step 1',
            active=True, requires=('custom-step2',), factory=step1)
        self.config.ptah_populate_step(
            'custom-step2', title='Custom step 2',
            active=False, factory=step2)

        steps = Populate(self.registry).list_steps()
        l_steps = [s['name'] for s in steps]

        self.assertTrue(l_steps.index('custom-step2') <
                        l_steps.index('custom-step1'))

    def test_list_once(self):
        self.config.ptah_populate_step(
            'custom-step1', title='Custom step 1', requires=('custom-step2',))
        self.config.ptah_populate_step(
            'custom-step2', title='Custom step 2')
        self.config.ptah_populate_step(
            'custom-step3', title='Custom step 3', requires=('custom-step2',))

        steps = Populate(self.registry).list_steps()

        count = 0
        for step in steps:
            if step['name'] == 'custom-step2':
                count += 1

        self.assertEqual(count, 1)

    def test_list_unknown(self):
        self.assertRaises(
            RuntimeError,
            Populate(self.registry).list_steps, ('unknown',))

    def test_list_unknown_dependency(self):
        self.config.ptah_populate_step(
            'custom-step1', title='Custom step 1', requires=('unknown',))

        self.assertRaises(
            RuntimeError, Populate(self.registry).list_steps)


class TestCreateDbSchema(ptah.PtahTestCase):

    def test_event(self):
        from ptah.populate import create_db_schema

        data = [False]
        def event_handler(ev):
            data[0] = True

        self.registry.registerHandler(
            event_handler, (ptah.events.BeforeCreateDbSchema,))

        create_db_schema(self.registry)
        self.assertTrue(data[0])

    def test_skip_tables(self):
        from ptah.populate import create_db_schema

        base = ptah.get_base()

        class test_populate_TestTable(base):
            __tablename__ = 'test_populate_TestTable'

            id = sqla.Column('id', sqla.Integer, primary_key=True)

        cfg = ptah.get_settings(ptah.CFG_ID_PTAH)
        cfg['db_skip_tables'] = ('test_populate_TestTable',)

        create_db_schema(self.registry)

        self.assertFalse(
            base.metadata.tables['test_populate_TestTable'].exists())

        cfg['db_skip_tables'] = ()
        create_db_schema(self.registry)

        self.assertTrue(
            base.metadata.tables['test_populate_TestTable'].exists())

########NEW FILE########
__FILENAME__ = test_rst
from ptah import rst
from ptah.testing import TestCase


class TestRST(TestCase):

    def tearDown(self):
        rst.local_data.sphinx = None

    def test_rst_py_domain(self):
        text = """ Test text :py:class:`ptahcms.Node` """

        self.assertIn('Test text :py:class:`ptahcms.Node`',
                      rst.rst_to_html(text))

    def test_rst_error(self):
        text = """ Test text `ptahcms.Node` """

        self.assertEqual(
            '<pre> Test text `ptahcms.Node` </pre>', rst.rst_to_html(text))

########NEW FILE########
__FILENAME__ = test_security
from zope import interface
from pyramid.security import Allow, Deny, ALL_PERMISSIONS, DENY_ALL
from pyramid.security import NO_PERMISSION_REQUIRED
from pyramid.httpexceptions import HTTPForbidden
from pyramid.exceptions import ConfigurationConflictError

import ptah
from ptah.testing import PtahTestCase


class TestPermission(PtahTestCase):

    _init_ptah = False

    def test_permission_register(self):
        perm = ptah.Permission('perm', 'Permission', 'Test permission')
        self.init_ptah()

        self.assertTrue(perm == 'perm')
        self.assertTrue(perm.title == 'Permission')
        self.assertTrue(perm.description == 'Test permission')
        self.assertTrue(ptah.get_permissions()['perm'] is perm)

    def test_permission_register_same_name(self):
        ptah.Permission('perm', 'Permission1')
        ptah.Permission('perm', 'Permission2')

        self.assertRaises(ConfigurationConflictError, self.init_ptah)


class TestACL(PtahTestCase):

    _init_ptah = False

    def test_acl_register(self):
        pmap = ptah.ACL('map', 'ACL', 'Map')
        self.init_ptah()

        self.assertTrue(pmap.id == 'map')
        self.assertTrue(pmap.title == 'ACL')
        self.assertTrue(pmap.description == 'Map')
        self.assertTrue(ptah.get_acls()['map'] is pmap)

    def test_acl_register_same_name(self):
        ptah.ACL('map', 'acl1')
        ptah.ACL('map', 'acl2')

        self.assertRaises(ConfigurationConflictError, self.init_ptah)

    def test_acl_allow(self):
        role = ptah.Role('test', 'test')

        pmap = ptah.ACL('map', 'acl map')
        pmap.allow(role, 'perm1')
        pmap.allow('role:test', 'perm2')

        self.assertEqual(len(pmap), 1)
        self.assertEqual(pmap[0][0], Allow)
        self.assertEqual(pmap[0][1], 'role:test')
        self.assertEqual(pmap[0][2], set(('perm2', 'perm1')))

    def test_acl_allow_all(self):
        role = ptah.Role('test', 'test')

        pmap = ptah.ACL('map', 'acl map')
        pmap.allow(role, 'perm1')
        pmap.allow(role, ALL_PERMISSIONS)
        pmap.allow(role, 'perm2')

        self.assertEqual(len(pmap), 1)
        self.assertEqual(pmap[0][0], Allow)
        self.assertEqual(pmap[0][1], 'role:test')
        self.assertEqual(pmap[0][2], ALL_PERMISSIONS)

    def test_acl_deny(self):
        role = ptah.Role('test', 'test')

        pmap = ptah.ACL('map', 'acl map')
        pmap.deny(role, 'perm1')
        pmap.deny('role:test', 'perm2')

        self.assertEqual(len(pmap), 1)
        self.assertEqual(pmap[0][0], Deny)
        self.assertEqual(pmap[0][1], 'role:test')
        self.assertEqual(pmap[0][2], set(('perm2', 'perm1')))

    def test_acl_deny_all(self):
        pmap = ptah.ACL('map', 'acl map')
        pmap.deny('role:test', 'perm1')
        pmap.deny('role:test', ALL_PERMISSIONS)
        pmap.deny('role:test', 'perm2')

        self.assertEqual(len(pmap), 1)
        self.assertEqual(pmap[0][0], Deny)
        self.assertEqual(pmap[0][1], 'role:test')
        self.assertEqual(pmap[0][2], ALL_PERMISSIONS)

    def test_acl_order(self):
        pmap = ptah.ACL('map', 'acl map')
        pmap.deny('role:test', 'perm1')
        pmap.allow('role:test', 'perm2')
        pmap.allow('role:test2', 'perm2')
        pmap.deny('role:test2', 'perm2')

        self.assertEqual(pmap[0][0], Deny)
        self.assertEqual(pmap[0][1], 'role:test')
        self.assertEqual(pmap[1][0], Allow)
        self.assertEqual(pmap[1][1], 'role:test')
        self.assertEqual(pmap[2][0], Allow)
        self.assertEqual(pmap[2][1], 'role:test2')
        self.assertEqual(pmap[3][0], Deny)
        self.assertEqual(pmap[3][1], 'role:test2')

    def test_acl_unset_allow(self):
        role = ptah.Role('test', 'test')

        pmap = ptah.ACL('map', 'acl map')
        pmap.allow(role, 'perm1', 'perm2')
        pmap.allow('role:test2', 'perm1')

        pmap.unset(None, 'perm1')

        self.assertEqual(len(pmap), 1)
        self.assertEqual(pmap[0][0], Allow)
        self.assertEqual(pmap[0][1], 'role:test')
        self.assertEqual(pmap[0][2], set(('perm2',)))

    def test_acl_unset_role_allow(self):
        role = ptah.Role('test', 'test')

        pmap = ptah.ACL('map', 'acl map')
        pmap.allow(role, 'perm1', 'perm2')
        pmap.allow('role:test2', 'perm1')

        pmap.unset(role.id, 'perm1')

        self.assertEqual(len(pmap), 2)
        self.assertEqual(pmap[0][0], Allow)
        self.assertEqual(pmap[0][1], 'role:test')
        self.assertEqual(pmap[0][2], set(('perm2',)))
        self.assertEqual(pmap[1][0], Allow)
        self.assertEqual(pmap[1][1], 'role:test2')
        self.assertEqual(pmap[1][2], set(('perm1',)))

    def test_acl_unset_deny(self):
        role = ptah.Role('test', 'test')

        pmap = ptah.ACL('map', 'acl map')
        pmap.deny(role, 'perm1', 'perm2')
        pmap.deny('role:test2', 'perm1')

        pmap.unset(None, 'perm1')

        self.assertEqual(len(pmap), 1)
        self.assertEqual(pmap[0][0], Deny)
        self.assertEqual(pmap[0][1], 'role:test')
        self.assertEqual(pmap[0][2], set(('perm2',)))

    def test_acl_unset_role_deny(self):
        role = ptah.Role('test', 'test')

        pmap = ptah.ACL('map', 'acl map')
        pmap.deny(role, 'perm1', 'perm2')
        pmap.deny('role:test2', 'perm1')

        pmap.unset(role.id, 'perm1')

        self.assertEqual(len(pmap), 2)
        self.assertEqual(pmap[0][0], Deny)
        self.assertEqual(pmap[0][1], 'role:test')
        self.assertEqual(pmap[0][2], set(('perm2',)))
        self.assertEqual(pmap[1][0], Deny)
        self.assertEqual(pmap[1][1], 'role:test2')
        self.assertEqual(pmap[1][2], set(('perm1',)))

    def test_acl_unset_all(self):
        pmap = ptah.ACL('map', 'acl map')
        pmap.allow('role:test1', 'perm1', 'perm2')
        pmap.allow('role:test2', 'perm1')
        pmap.deny('role:test1', 'perm1', 'perm2')
        pmap.deny('role:test2', ALL_PERMISSIONS)

        pmap.unset(None, ALL_PERMISSIONS)
        self.assertEqual(len(pmap), 0)

    def test_acl_unset_role_all(self):
        pmap = ptah.ACL('map', 'acl map')
        pmap.allow('role:test1', 'perm2')
        pmap.allow('role:test2', 'perm1')
        pmap.deny('role:test1', 'perm1', 'perm2')
        pmap.deny('role:test2', ALL_PERMISSIONS)

        pmap.unset('role:test2', ALL_PERMISSIONS)
        self.assertEqual(len(pmap), 2)
        self.assertEqual(pmap[0][0], Allow)
        self.assertEqual(pmap[0][1], 'role:test1')
        self.assertEqual(pmap[0][2], set(('perm2',)))
        self.assertEqual(pmap[1][0], Deny)
        self.assertEqual(pmap[1][1], 'role:test1')
        self.assertEqual(pmap[1][2], set(('perm1','perm2')))


class TestACLsProps(PtahTestCase):

    _init_ptah = False

    def test_acls(self):
        acl1 = ptah.ACL('acl1', 'acl1')
        acl1.allow('role1', 'perm1', 'perm2')

        acl2 = ptah.ACL('acl2', 'acl2')
        acl2.deny('role1', 'perm1', 'perm2')

        self.init_ptah()

        class Content(object):
            __acl__ = ptah.ACLsProperty()

        content = Content()

        self.assertEqual(content.__acl__, ())

        content.__acls__ = ()
        self.assertEqual(content.__acl__, ())

        content.__acls__ = ('acl1',)
        self.assertEqual(list(content.__acl__),
                         [['Allow', 'role1', set(['perm2', 'perm1'])]])

        content.__acls__ = ('acl1', 'acl2',)
        self.assertEqual(list(content.__acl__),
                         [['Allow', 'role1', set(['perm2', 'perm1'])],
                          ['Deny', 'role1', set(['perm2', 'perm1'])]])

        content.__acls__ = ('acl2', 'acl1')
        self.assertEqual(list(content.__acl__),
                         [['Deny', 'role1', set(['perm2', 'perm1'])],
                          ['Allow', 'role1', set(['perm2', 'perm1'])]])


class TestRole(PtahTestCase):

    _init_ptah = False

    def test_role_register(self):
        role = ptah.Role('myrole', 'MyRole')

        self.assertTrue(role.id == 'role:myrole')
        self.assertTrue(role.name == 'myrole')
        self.assertTrue(role.title == 'MyRole')
        self.assertTrue(role.description == '')
        self.assertTrue(str(role) == 'Role<MyRole>')
        self.assertTrue(repr(role) == 'role:myrole')

    def test_role_register_conflict(self):
        ptah.Role('myrole', 'MyRole1')
        ptah.Role('myrole', 'MyRole2')

        self.assertRaises(ConfigurationConflictError, self.init_ptah)

    def test_role_roles(self):
        role = ptah.Role('myrole', 'MyRole')
        self.init_ptah()

        self.assertTrue('myrole' in ptah.get_roles())
        self.assertTrue(ptah.get_roles()['myrole'] is role)

    def test_role_allow_permission(self):
        from ptah import DEFAULT_ACL

        role = ptah.Role('myrole', 'MyRole')
        role.allow('perm1', 'perm2')

        rec = DEFAULT_ACL.get(Allow, role.id)

        self.assertEqual(rec[0], Allow)
        self.assertEqual(rec[1], role.id)
        self.assertTrue('perm1' in rec[2])
        self.assertTrue('perm2' in rec[2])

    def test_role_deny_permission(self):
        from ptah import DEFAULT_ACL

        role = ptah.Role('myrole', 'MyRole')
        role.deny('perm1', 'perm2')

        rec = DEFAULT_ACL.get(Deny, role.id)

        self.assertEqual(rec[0], Deny)
        self.assertEqual(rec[1], role.id)
        self.assertTrue('perm1' in rec[2])
        self.assertTrue('perm2' in rec[2])

    def test_role_unset_allowed_permission(self):
        from ptah import DEFAULT_ACL

        role = ptah.Role('myrole', 'MyRole')
        role.allow('perm1')

        self.assertEqual(len(DEFAULT_ACL), 1)

        role.unset('perm1')
        self.assertEqual(len(DEFAULT_ACL), 0)

    def test_role_unset_denied_permission(self):
        from ptah import DEFAULT_ACL

        role = ptah.Role('myrole', 'MyRole')
        role.deny('perm1')

        self.assertEqual(len(DEFAULT_ACL), 1)

        role.unset('perm1')
        self.assertEqual(len(DEFAULT_ACL), 0)


class TestDefaultRoles(PtahTestCase):

    def test_role_defaults(self):
        roles = sorted(list(ptah.get_roles().keys()))[:3]

        self.assertTrue(['Authenticated', 'Everyone', 'Owner'] == roles)
        self.assertTrue(
            ptah.get_roles()['Everyone'].id == 'system.Everyone')
        self.assertTrue(
            ptah.get_roles()['Authenticated'].id=='system.Authenticated')
        self.assertTrue(
            ptah.get_roles()['Owner'].id=='system.Owner')


class Content(object):

    def __init__(self, parent=None, iface=None, acl=None):
        self.__parent__ = parent
        self.__local_roles__ = {}
        if acl is not None:
            self.__acl__ = acl

        if iface:
            interface.directlyProvides(self, iface)


class TestLocalRoles(PtahTestCase):

    def test_local_role_simple(self):
        from ptah import security

        content = Content(iface=security.ILocalRolesAware)

        self.assertEqual(security.get_local_roles('userid', context=content),[])

        content.__local_roles__['userid'] = ('role:test',)

        self.assertEqual(
            security.get_local_roles('userid', context=content), ['role:test'])

    def test_local_role_default_roles(self):
        from ptah import security

        cfg = ptah.get_settings(ptah.CFG_ID_PTAH)
        cfg['default_roles'] = ['role1', 'role2']

        content = Content(iface=security.ILocalRolesAware)

        roles = security.get_local_roles('userid', context=content)
        self.assertIn('role1', roles)
        self.assertIn('role2', roles)

    def test_local_role_default_roles_for_non_localaware(self):
        from ptah import security

        cfg = ptah.get_settings(ptah.CFG_ID_PTAH)
        cfg['default_roles'] = ['role1', 'role2']

        content = Content()
        roles = security.get_local_roles('userid', context=content)
        self.assertIn('role1', roles)
        self.assertIn('role2', roles)

    def test_local_role_lineage(self):
        from ptah import security

        parent = Content(iface=security.ILocalRolesAware)
        content = Content(parent=parent, iface=security.ILocalRolesAware)

        self.assertEqual(security.get_local_roles('userid', context=content),[])

        parent.__local_roles__['userid'] = ('role:test',)

        self.assertEqual(
            security.get_local_roles('userid', context=content), ['role:test'])

    def test_local_role_lineage_multiple(self):
        from ptah import security

        parent = Content(iface=security.ILocalRolesAware)
        content = Content(parent=parent, iface=security.ILocalRolesAware)

        self.assertEqual(security.get_local_roles('userid', context=content),[])

        parent.__local_roles__['userid'] = ('role:test',)
        content.__local_roles__['userid'] = ('role:test2',)

        lr = sorted(security.get_local_roles('userid', context=content))

        self.assertTrue(lr == ['role:test', 'role:test2'])

    def test_local_role_lineage_no_localroles(self):
        from ptah import security

        parent = Content(iface=security.ILocalRolesAware)
        content = Content(parent=parent)

        self.assertEqual(security.get_local_roles('userid', context=content),[])

        parent.__local_roles__['userid'] = ('role:test',)

        self.assertEqual(
            security.get_local_roles('userid', context=content), ['role:test'])

    def test_local_role_lineage_context_from_request(self):
        from ptah import security

        class Request(object):
            content = None
            root = None

        request = Request()

        content = Content(iface=security.ILocalRolesAware)
        content.__local_roles__['userid'] = ('role:test',)

        request.root = content

        self.assertEqual(
            security.get_local_roles('userid', request), ['role:test'])

        content2 = Content(iface=security.ILocalRolesAware)
        content2.__local_roles__['userid'] = ('role:test2',)

        request.context = content2
        self.assertEqual(
            security.get_local_roles('userid', request), ['role:test2'])


class Content2(object):

    def __init__(self, parent=None, iface=None):
        self.__parent__ = parent
        self.__owner__ = ''

        if iface:
            interface.directlyProvides(self, iface)


class TestOwnerLocalRoles(PtahTestCase):

    def test_owner_role_simple(self):
        from ptah import security

        content = Content2(iface=security.IOwnersAware)

        self.assertEqual(security.get_local_roles('userid', context=content), [])

        content.__owner__ = 'userid'

        self.assertEqual(
            security.get_local_roles('userid', context=content), ['system.Owner'])

    def test_owner_role_in_parent(self):
        # return owner only on current context
        from ptah import security

        parent = Content2(iface=security.IOwnersAware)
        content = Content2(parent=parent, iface=security.IOwnersAware)

        parent.__owner__ = 'user'

        self.assertEqual(security.get_local_roles('user', context=content), [])
        self.assertEqual(
            security.get_local_roles('user', context=parent), ['system.Owner'])


class TestCheckPermission(PtahTestCase):

    _init_auth = True

    def test_checkpermission_allow(self):
        import ptah

        content = Content(acl=[DENY_ALL])

        self.assertFalse(ptah.check_permission('View', content, throw=False))
        self.assertTrue(ptah.check_permission(
            NO_PERMISSION_REQUIRED, content, throw=False))

    def test_checkpermission_deny(self):
        import ptah

        content = Content(acl=[(Allow, ptah.Everyone.id, ALL_PERMISSIONS)])

        self.assertTrue(ptah.check_permission('View', content, throw=False))
        self.assertFalse(ptah.check_permission(
            ptah.NOT_ALLOWED, content, throw=False))

    def test_checkpermission_exc(self):
        import ptah

        content = Content(acl=[DENY_ALL])

        self.assertRaises(
            HTTPForbidden, ptah.check_permission, 'View', content, throw=True)

        content = Content(acl=[(Allow, ptah.Everyone.id, ALL_PERMISSIONS)])

        self.assertRaises(
            HTTPForbidden, ptah.check_permission,
            ptah.NOT_ALLOWED, content, throw=True)

    def test_checkpermission_authenticated(self):
        import ptah

        content = Content(acl=[(Allow, ptah.Authenticated.id, 'View')])

        self.assertFalse(ptah.check_permission('View', content, throw=False))

        ptah.auth_service.set_userid('test-user')
        self.assertTrue(ptah.check_permission('View', content, throw=False))

    def test_checkpermission_user(self):
        import ptah

        content = Content(acl=[(Allow, 'test-user', 'View')])
        self.assertFalse(ptah.check_permission('View', content, throw=False))

        ptah.auth_service.set_userid('test-user')
        self.assertTrue(ptah.check_permission('View', content, throw=False))

    def test_checkpermission_effective_user(self):
        import ptah

        content = Content(acl=[(Allow, 'test-user2', 'View')])

        ptah.auth_service.set_userid('test-user')
        ptah.auth_service.set_effective_userid('test-user2')
        self.assertTrue(ptah.check_permission('View', content, throw=False))

    def test_checkpermission_superuser(self):
        import ptah
        from pyramid import security

        content = Content(
            acl=[(Deny, ptah.SUPERUSER_URI, security.ALL_PERMISSIONS)])

        ptah.auth_service.set_userid(ptah.SUPERUSER_URI)
        self.assertTrue(ptah.check_permission('View', content))
        self.assertFalse(ptah.check_permission(ptah.NOT_ALLOWED, content))

    def test_checkpermission_effective_superuser(self):
        import ptah
        from pyramid import security

        content = Content(
            acl=[(Deny, ptah.SUPERUSER_URI, security.ALL_PERMISSIONS)])

        ptah.auth_service.set_userid('test-user')
        ptah.auth_service.set_effective_userid(ptah.SUPERUSER_URI)

        self.assertTrue(ptah.check_permission('View', content))
        self.assertFalse(ptah.check_permission(ptah.NOT_ALLOWED, content))

    def test_checkpermission_local_roles(self):
        import ptah

        content = Content(
            iface=ptah.ILocalRolesAware,
            acl=[(Allow, 'role:test', 'View')])

        ptah.auth_service.set_userid('test-user')
        self.assertFalse(ptah.check_permission('View', content, throw=False))

        content.__local_roles__['test-user'] = ['role:test']
        self.assertTrue(ptah.check_permission('View', content, throw=False))

    def test_checkpermission_effective_local_roles(self):
        import ptah

        content = Content(
            iface=ptah.ILocalRolesAware,
            acl=[(Allow, 'role:test', 'View')])

        ptah.auth_service.set_userid('test-user2')
        self.assertFalse(ptah.check_permission('View', content, throw=False))

        content.__local_roles__['test-user'] = ['role:test']
        self.assertFalse(ptah.check_permission('View', content, throw=False))

        ptah.auth_service.set_effective_userid('test-user')
        self.assertTrue(ptah.check_permission('View', content, throw=False))


class TestAauthorization(PtahTestCase):

    _init_auth = True

    def _make_one(self):
        from ptah.security import PtahAuthorizationPolicy
        return PtahAuthorizationPolicy()

    def test_authz_allow_no_permissions(self):
        authz = self._make_one()
        content = Content(acl=[DENY_ALL])

        self.assertFalse(
            authz.permits(content, (ptah.Everyone.id,), 'View'))
        self.assertTrue(
            authz.permits(content, (ptah.Everyone.id,), NO_PERMISSION_REQUIRED))

    def test_authz_deny_not_allowed(self):
        authz = self._make_one()
        content = Content(acl=[(Allow, ptah.Everyone.id, ALL_PERMISSIONS)])

        self.assertTrue(authz.permits(
            content, (ptah.Everyone.id,), 'View'))
        self.assertFalse(authz.permits(
            content, (ptah.Everyone.id,), ptah.NOT_ALLOWED))

    def test_authz_effective_user(self):
        authz = self._make_one()
        content = Content(acl=[(Allow, 'test-user2', 'View')])

        ptah.auth_service.set_effective_userid('test-user2')
        self.assertFalse(
            authz.permits(content, ('test-user',), 'View'))

    def test_authz_superuser(self):
        authz = self._make_one()
        content = Content(acl=[(Allow, 'test-user2', 'View')])
        self.assertTrue(authz.permits(content, (ptah.SUPERUSER_URI,), 'View'))

    def test_authz_superuser_allow(self):
        authz = self._make_one()
        content = Content(
            acl=[(Deny, ptah.SUPERUSER_URI, ptah.ALL_PERMISSIONS)])

        self.assertTrue(
            authz.permits(content, (ptah.SUPERUSER_URI,), 'View'))

    def test_authz_effective_superuser(self):
        authz = self._make_one()
        content = Content(
            acl=[(Deny, ptah.SUPERUSER_URI, ptah.ALL_PERMISSIONS)])

        ptah.auth_service.set_effective_userid(ptah.SUPERUSER_URI)

        self.assertTrue(
            authz.permits(content, ('test-user',), 'View'))
        self.assertFalse(
            authz.permits(content, ('test-user',), ptah.NOT_ALLOWED))


class TestRolesProvider(PtahTestCase):

    _init_ptah = False

    def test_roles_provider(self):
        import ptah
        from ptah.security import ID_ROLES_PROVIDER

        @ptah.roles_provider('test1')
        def provider1(context, uid, registry):
            """ """

        @ptah.roles_provider('test2')
        def provider2(context, uid, registry):
            """ """

        self.init_ptah()

        data = self.config.get_cfg_storage(ID_ROLES_PROVIDER)

        self.assertIn('test1', data)
        self.assertIn('test2', data)
        self.assertIs(data['test1'], provider1)
        self.assertIs(data['test2'], provider2)

    def test_roles_provider_conflict(self):
        @ptah.roles_provider('test1')
        def provider1(context, uid, registry):
            """ """

        @ptah.roles_provider('test1')
        def provider2(context, uid, registry):
            """ """

        self.assertRaises(ConfigurationConflictError, self.init_ptah)

    def test_get_local_roles(self):
        import ptah
        from ptah import security

        data = {}

        @ptah.roles_provider('test1')
        def provider1(context, uid, registry):
            data['test1'] = uid
            return ('Role1',)

        @ptah.roles_provider('test2')
        def provider2(context, uid, registry):
            data['test2'] = uid
            return ('Role2',)

        self.init_ptah()

        content = Content()

        roles = security.get_local_roles('userid', context=content)
        self.assertIn('Role1', roles)
        self.assertIn('Role2', roles)
        self.assertIn('test1', data)
        self.assertIn('test2', data)

########NEW FILE########
__FILENAME__ = test_settings
import os
import pform
import shutil
import tempfile
from pyramid.compat import bytes_, text_type

import ptah
from ptah.settings import Settings
from ptah.settings import SETTINGS_OB_ID
from ptah.testing import PtahTestCase


def get_settings_ob():
    return ptah.config.get_cfg_storage(SETTINGS_OB_ID, default_factory=Settings)


class BaseTesting(PtahTestCase):

    _init_ptah = False

    def init_ptah(self, initsettings=False, *args, **kw):
        self.config.include('ptah')
        self.config.scan(self.__class__.__module__)
        self.config.commit()
        self.config.autocommit = True

        if initsettings:
            self.config.ptah_init_settings()


class TestSettingsResolver(BaseTesting):

    def test_settings_uri_resolver(self):
        node = pform.TextField(
            'node',
            default = 'test')

        ptah.register_settings(
            'group', node,
            title = 'Section title',
            description = 'Section description',
            )
        self.init_ptah()

        grp1 = ptah.get_settings('group', self.registry)
        self.assertEqual(grp1.__uri__, 'settings:group')

        grp2 = ptah.resolve('settings:group')
        self.assertIs(grp1, grp2)


class TestSettings(BaseTesting):

    def test_settings_no_default(self):
        field = pform.TextField('node')

        self.assertRaises(
            ptah.config.StopException,
            ptah.register_settings,
            'group1', field,
            title = 'Section title',
            description = 'Section description',
            )

    def test_settings_group_basics(self):
        node = pform.TextField(
            'node',
            default = 'test')

        ptah.register_settings(
            'group1', node,
            title = 'Section title',
            description = 'Section description',
            )
        self.init_ptah()

        group = ptah.get_settings('group1', self.registry)
        self.assertEqual(group.keys(), ['node'])
        self.assertEqual(group.items(), [('node', 'test')])

        group.update({'node': '12345'})
        self.assertEqual(group.get('node'), '12345')

    def test_settings_group_uninitialized(self):
        node = pform.TextField(
            'node',
            default = 'test')

        ptah.register_settings(
            'group1', node,
            title = 'Section title',
            description = 'Section description',
            )
        self.init_ptah()

        group = ptah.get_settings('group1', self.registry)
        self.assertEqual(group.get('node'), 'test')

    def test_settings_group_extract(self):
        node1 = pform.TextField(
            'node1', default = 'test1')

        node2 = pform.TextField(
            'node2', default = 'test2')

        ptah.register_settings('group', node1, node2)
        self.init_ptah()

        group = ptah.get_settings('group', self.registry)

        data, errors = group.extract({'group.node1': 'test-extract'})

        self.assertEqual(data['node1'], 'test-extract')
        self.assertEqual(data['node2'], 'test2')

        group['node2'] = 'value'
        data, errors = group.extract({'group.node1': 'test-extract'})
        self.assertEqual(data['node2'], 'value')

    def test_settings_get_settings_pyramid(self):
        node = pform.TextField(
            'node',
            default = 'test')

        ptah.register_settings(
            'group1', node,
            title = 'Section title',
            description = 'Section description',
            )

        self.init_ptah()

        grp = self.config.ptah_get_settings('group1')
        self.assertIsNotNone(grp)
        self.assertEqual(grp.__name__, 'group1')
        self.assertIn(node, grp.__fields__.values())

    def test_settings_register_simple(self):
        node = pform.TextField(
            'node',
            default = 'test')

        ptah.register_settings(
            'group1', node,
            title = 'Section title',
            description = 'Section description',
            )

        self.init_ptah()

        group = ptah.get_settings('group1', self.registry)

        self.assertEqual(len(group.__fields__), 1)
        self.assertIn(node, group.__fields__.values())
        self.assertEqual(group['node'], 'test')
        self.assertRaises(
            KeyError,
            group.__getitem__, 'unknown')

        group.node = 'test2'
        self.assertFalse(group.node == group['node'])

    def test_settings_group_validation(self):
        def validator(node, appstruct):
            raise pform.Invalid('Error', node['node'])

        node = pform.TextField(
            'node',
            default = 'test')

        ptah.register_settings(
            'group2', node, validator=validator)

        self.init_ptah()

        group = ptah.get_settings('group2', self.registry)

        data, err = group.extract({'group2.node': 'value'})

        self.assertEqual(err.msg, {'group2': text_type(['Error'])})

    def test_settings_group_multiple_validation(self):
        def validator1(fs, appstruct):
            raise pform.Invalid('Error1', fs['node1'])

        def validator2(fs, appstruct):
            raise pform.Invalid('Error2', fs['node2'])

        node1 = pform.TextField(
            'node1',
            default = 'test')

        node2 = pform.TextField(
            'node2',
            default = 'test')

        ptah.register_settings(
            'group3', node1, node2, validator=(validator1, validator2))

        self.init_ptah()

        group = ptah.get_settings('group3', self.registry)
        data, err = group.extract({
            'group3.node1': 'value',
            'group3.node2': 'value'})

        self.assertEqual(err.msg, {'group3': text_type(['Error1', 'Error2'])})

    def test_settings_export(self):
        field1 = pform.TextField(
            'node1',
            default = 'test')

        field2 = pform.TextField(
            'node2',
            default = 'test1')

        ptah.register_settings('group4', field1, field2)
        self.init_ptah(initsettings=True)

        settings = get_settings_ob()

        # changed settings
        self.assertEqual(settings.export(), {})

        # default settings
        data = settings.export(default=True)
        self.assertIn('group4.node1', data)
        self.assertIn('group4.node2', data)
        self.assertEqual(data['group4.node1'], '"test"')
        self.assertEqual(data['group4.node2'], '"test1"')

        # changed settings
        group = ptah.get_settings('group4', self.registry)

        group['node2'] = 'changed'
        data = dict(settings.export())
        self.assertEqual(data['group4.node2'], '"changed"')

    def _create_default_group(self):
        node1 = pform.TextField(
            'node1',
            default = 'default1')

        node2 = pform.IntegerField(
            'node2',
            default = 10)

        ptah.register_settings('group', node1, node2)
        self.init_ptah(initsettings=True)

        return ptah.get_settings('group', self.registry)

    def test_settings_load_rawdata(self):
        group = self._create_default_group()

        get_settings_ob().init(self.config, {'group.node1': 'val1'})

        # new value
        self.assertEqual(group['node1'], 'val1')

        # default value
        self.assertEqual(group['node2'], 10)

    def test_settings_load_rawdata_and_change_defaults(self):
        group = self._create_default_group()

        # change defaults
        get_settings_ob().init(self.config, {'group.node2': '30'})

        # new values
        self.assertEqual(group['node1'], 'default1')
        self.assertEqual(group['node2'], 30)

        self.assertEqual(group.__fields__['node1'].default, 'default1')
        self.assertEqual(group.__fields__['node2'].default, 30)

    def test_settings_load_rawdata_with_errors_in_rawdata(self):
        self._create_default_group()

        self.assertRaises(
            ptah.config.StopException,
            get_settings_ob().init,
            self.config, {10: 'value'})

    def test_settings_load_defaults_rawdata_with_errors_in_values(self):
        node = pform.FloatField(
            'node1',
            default = ())

        ptah.register_settings('group', node)
        self.init_ptah(initsettings=True)

        self.assertRaises(
            ptah.config.StopException,
            get_settings_ob().init,
            self.config,
            {'group.node1': 'l,1'})

    def test_settings_init_with_no_loader_with_defaults(self):
        group = self._create_default_group()

        get_settings_ob().init(self.config,
                               {'group.node1': 'new-default',
                                'group.node2': '50'})

        self.assertEqual(group['node1'], 'new-default')
        self.assertEqual(group['node2'], 50)

        self.assertEqual(group.__fields__['node1'].default, 'new-default')
        self.assertEqual(group.__fields__['node2'].default, 50)


class TestSettingsInitialization(BaseTesting):

    def setUp(self):
        BaseTesting.setUp(self)
        self.dir = tempfile.mkdtemp()

    def tearDown(self):
        BaseTesting.tearDown(self)
        shutil.rmtree(self.dir)

    def test_settings_initialize_events(self):
        from ptah.settings import init_settings

        self.init_ptah()

        sm = self.config.registry

        events = []

        def h1(ev):
            events.append(ev)

        def h2(ev):
            events.append(ev)

        sm.registerHandler(h1, (ptah.events.SettingsInitializing,))
        sm.registerHandler(h2, (ptah.events.SettingsInitialized,))

        init_settings(self.config, {})

        self.assertTrue(isinstance(events[0], ptah.events.SettingsInitializing))
        self.assertTrue(isinstance(events[1], ptah.events.SettingsInitialized))

        self.assertTrue(events[0].config is self.config)
        self.assertTrue(events[1].config is self.config)

    def test_settings_initialize_events_exceptions(self):
        from ptah.settings import init_settings

        self.init_ptah()

        sm = self.config.registry

        err_tp = TypeError()

        def h1(ev):
            raise err_tp

        sm.registerHandler(h1, (ptah.events.SettingsInitializing,))

        err = None
        try:
            init_settings(self.config, {})
        except Exception as exc:
            err = exc

        self.assertIsInstance(err, ptah.config.StopException)
        self.assertIs(err.exc, err_tp)

    def test_settings_initialize_only_once(self):
        from ptah.settings import init_settings

        self.init_ptah()
        init_settings(self.config, {})

        self.assertRaises(
            RuntimeError, init_settings, self.config, {})

    def test_settings_initialize_load_defaults(self):
        from ptah.settings import init_settings

        node1 = pform.TextField(
            'node1',
            default = 'default1')

        node2 = pform.TextField(
            'node2',
            default = 10)

        ptah.register_settings('group', node1, node2)
        self.init_ptah()

        init_settings(self.config, None)

        group = ptah.get_settings('group', self.request.registry)
        self.assertEqual(group['node1'], 'default1')
        self.assertEqual(group['node2'], 10)

    def test_settings_initialize_load_preparer(self):
        from ptah.settings import init_settings

        node1 = pform.TextField(
            'node',
            default = 'default1',
            preparer = lambda s: s.lower())

        ptah.register_settings('group', node1)
        self.init_ptah()

        init_settings(self.config, {'group.node': 'Test'})

        group = ptah.get_settings('group', self.request.registry)
        self.assertEqual(group['node'], 'test')

    def test_settings_initialize_load_partly_defaults(self):
        from ptah.settings import init_settings

        node1 = pform.TextField(
            'node1',
            default = 'default1')

        node2 = pform.TextField(
            'node2',
            default = 10)

        ptah.register_settings('group', node1, node2)
        self.init_ptah()

        init_settings(self.config, {'group.node1': 'setting from ini'})

        group = ptah.get_settings('group', self.request.registry)
        self.assertEqual(group['node1'], 'setting from ini')
        self.assertEqual(group['node2'], 10)

    def test_settings_initialize_load_settings_include(self):
        from ptah.settings import init_settings

        path = os.path.join(self.dir, 'settings.cfg')
        f = open(path, 'wb')
        f.write(bytes_('[DEFAULT]\ngroup.node1 = value\n\n','ascii'))
        f.close()

        node1 = pform.TextField(
            'node1',
            default = 'default1')

        node2 = pform.IntegerField(
            'node2',
            default = 10)

        ptah.register_settings('group', node1, node2)
        self.init_ptah()

        init_settings(self.config, {'include': path})

        group = ptah.get_settings('group', self.request.registry)

        self.assertEqual(group['node1'], 'value')
        self.assertEqual(group['node2'], 10)


class TestDBSettingsBase(PtahTestCase):

    def _make_grp(self):
        node1 = pform.TextField(
            'node1',
            default = 'test')

        node2 = pform.IntegerField(
            'node2',
            default = 50)

        ptah.register_settings(
            'group', node1, node2,
            title = 'Section title',
            description = 'Section description',
            )
        self.init_ptah()

        return ptah.get_settings('group', self.registry)


class TestDBSettings(TestDBSettingsBase):

    _init_ptah = False

    def test_settings_updatedb(self):
        grp = self._make_grp()
        grp.updatedb(node1 = 'new text',
                     node2 = 65)

        self.assertEqual(grp['node1'], 'new text')
        self.assertEqual(grp['node2'], 65)

        from ptah.settings import SettingRecord
        Session = ptah.get_session()

        res = {}
        for rec in Session.query(SettingRecord):
            res[rec.name] = rec.value

        self.assertIn('group.node1', res)
        self.assertIn('group.node2', res)
        self.assertEqual(res['group.node1'], '"new text"')
        self.assertEqual(res['group.node2'], '65')

    def test_settings_updatedb_unknown(self):
        grp = self._make_grp()
        grp.updatedb(node1 = 'new text',
                     node2 = 65,
                     node3 = 500)

        self.assertEqual(grp['node3'], 500)

        from ptah.settings import SettingRecord
        Session = ptah.get_session()

        res = {}
        for rec in Session.query(SettingRecord):
            res[rec.name] = rec.value

        self.assertEqual(len(res), 3)
        self.assertEqual(res['group.node3'], '500')

        grp['node3'] = 600
        self.assertEqual(grp['node3'], 600)

        settings = self.config.get_cfg_storage('ptah:settings')
        settings.load_fromdb()
        self.assertEqual(grp['node3'], 500)

    def test_settings_updatedb_partial(self):
        grp = self._make_grp()
        grp.updatedb(node1 = 'new text')

        self.assertEqual(grp['node1'], 'new text')
        self.assertEqual(grp['node2'], 50)

        from ptah.settings import SettingRecord
        Session = ptah.get_session()

        res = {}
        for rec in Session.query(SettingRecord):
            res[rec.name] = rec.value

        self.assertEqual(len(res), 1)
        self.assertIn('group.node1', res)
        self.assertEqual(res['group.node1'], '"new text"')

    def test_settings_updatedb_set_default(self):
        grp = self._make_grp()
        grp.updatedb(node1 = 'new text', node2 = 65)
        grp.updatedb(node1 = 'new text 2', node2 = 50)

        from ptah.settings import SettingRecord
        Session = ptah.get_session()

        res = {}
        for rec in Session.query(SettingRecord):
            res[rec.name] = rec.value

        self.assertEqual(len(res), 1)
        self.assertIn('group.node1', res)
        self.assertEqual(res['group.node1'], '"new text 2"')

    def test_settings_updatedb_event(self):
        event_grp = []

        @ptah.config.subscriber(ptah.events.SettingsGroupModified)
        def handler(ev):
            event_grp.append(ev.object)

        grp = self._make_grp()
        grp.updatedb(node1 = 'new text', node2 = 65)

        self.assertIs(grp, event_grp[0])

    def test_settings_updatedb_load_from_db(self):
        grp = self._make_grp()
        grp.updatedb(node1 = 'new text',
                     node2 = 65)
        grp.clear()

        from ptah.settings import SettingRecord
        Session = ptah.get_session()

        # non json obj
        Session.add(SettingRecord(name='group.node3', value='value'))

        settings = self.registry.__ptah_storage__[SETTINGS_OB_ID]
        settings.load({})

        self.assertEqual(grp['node1'], 'test')
        self.assertEqual(grp['node2'], 50)

        settings.load_fromdb()
        self.assertEqual(grp['node1'], 'new text')
        self.assertEqual(grp['node2'], 65)

        self.assertEqual(grp['node3'], 'value')

    def test_settings_load_from_db_on_startup(self):
        grp = self._make_grp()

        grp.updatedb(node1 = 'new text',
                     node2 = 65)
        grp.clear()

        ptah.get_base().metadata.tables['ptah_db_versions'].drop()

        self.config.make_wsgi_app()
        self.assertEqual(grp['node1'], 'new text')
        self.assertEqual(grp['node2'], 65)


class TestDBSettings2(TestDBSettingsBase):

    _init_ptah = False
    _init_sqla = False

    def test_settings_load_from_db_on_startup_do_not_brake(self):
        from ptah.settings import SettingRecord
        ptah.get_base().metadata.drop_all()

        grp = self._make_grp()

        self.config.make_wsgi_app()

        self.assertEqual(grp['node1'], 'test')
        self.assertEqual(grp['node2'], 50)
        self.assertFalse(SettingRecord.__table__.exists())

########NEW FILE########
__FILENAME__ = test_shutdown
import signal
import sys
from ptah import config
from ptah.testing import TestCase


class TestShutdownHandlers(TestCase):

    def test_shutdown_handler(self):
        shutdownExecuted = []

        @config.shutdown_handler
        def shutdown():
            shutdownExecuted.append(True)

        shutdown = sys.modules['ptah.config']
        shutdown._shutdown = False

        err = None
        try:
            shutdown.process_shutdown(signal.SIGINT, None)
        except BaseException as e:
            err = e

        self.assertTrue(isinstance(err, KeyboardInterrupt))
        self.assertTrue(shutdownExecuted[0])

    def test_shutdown_exception_in_handler(self):

        @config.shutdown_handler
        def shutdown():
            raise ValueError()

        from ptah.config import shutdown
        shutdown._shutdown = False

        err = None
        try:
            shutdown.process_shutdown(signal.SIGINT, None)
        except BaseException as e:
            err = e

        self.assertFalse(isinstance(err, ValueError))

    def test_shutdown_sigterm(self):
        shutdownExecuted = []

        @config.shutdown_handler
        def shutdown():
            shutdownExecuted.append(True)

        shutdown = sys.modules['ptah.config']
        shutdown._shutdown = False
        try:
            shutdown.process_shutdown(signal.SIGTERM, None)
        except:
            pass

        self.assertTrue(shutdownExecuted[0])

########NEW FILE########
__FILENAME__ = test_sqlfields
import transaction
import sqlalchemy as sqla
import pform
import ptah
from ptah.testing import TestCase, PtahTestCase

Session = ptah.get_session()


class TestSqlSchema(PtahTestCase):

    def test_sqlschema_fields(self):
        import ptah

        class Test(ptah.get_base()):
            __tablename__ = 'test'

            id = sqla.Column('id', sqla.Integer, primary_key=True)
            name = sqla.Column(sqla.Unicode())
            count = sqla.Column(sqla.Integer())
            score = sqla.Column(sqla.Float())
            date = sqla.Column(sqla.Date())
            datetime = sqla.Column(sqla.DateTime())
            boolean = sqla.Column(sqla.Boolean())

        fieldset = ptah.generate_fieldset(Test)

        # no primary keya
        self.assertNotIn('id', fieldset)

        self.assertEqual(fieldset['name'].__field__, 'text')
        self.assertEqual(fieldset['count'].__field__, 'int')
        self.assertEqual(fieldset['score'].__field__, 'float')
        self.assertEqual(fieldset['date'].__field__, 'date')
        self.assertEqual(fieldset['datetime'].__field__, 'datetime')
        self.assertEqual(fieldset['boolean'].__field__, 'bool')
        self.assertEqual(fieldset['name'].title, 'Name')

        fieldset = ptah.generate_fieldset(Test, fieldNames=('name', 'count'))
        self.assertEqual(len(fieldset), 2)
        self.assertIn('name', fieldset)
        self.assertIn('count', fieldset)

        fieldset = ptah.generate_fieldset(
            Test, fieldNames=('id', 'name'), skipPrimaryKey=False)
        self.assertEqual(len(fieldset), 2)
        self.assertIn('name', fieldset)
        self.assertIn('id', fieldset)
        self.assertTrue(fieldset['id'].readonly)

        # no table
        class TestNoTable(Test):
            pass

        fieldset = ptah.generate_fieldset(TestNoTable)
        self.assertEqual(len(fieldset), 6)

    def test_sqlschema_extra_fields(self):
        import ptah

        class Test2(ptah.get_base()):
            __tablename__ = 'test2'

            id = sqla.Column('id', sqla.Integer, primary_key=True)
            name = sqla.Column(
                sqla.Unicode(),
                info={'title': 'Test title',
                      'missing': 'missing value',
                      'description': 'Description',
                      'field_type': 'textarea',
                      'vocabulary': ['1','2']})

        fieldset = ptah.generate_fieldset(Test2)

        field = fieldset['name']

        self.assertEqual(field.title, 'Test title')
        self.assertEqual(field.description, 'Description')
        self.assertEqual(field.missing, 'missing value')
        self.assertEqual(field.__field__, 'textarea')
        self.assertEqual(field.vocabulary, ['1', '2'])

    def test_sqlschema_custom(self):
        import ptah

        field = pform.TextField('name', title = 'Custom')

        class Test3(ptah.get_base()):
            __tablename__ = 'test3'
            id = sqla.Column('id', sqla.Integer, primary_key=True)
            name = sqla.Column(sqla.Unicode(), info={'field': field})

        fieldset = ptah.generate_fieldset(Test3)

        m_field = fieldset['name']

        self.assertEqual(m_field.name, 'name')
        self.assertEqual(m_field.title, 'Custom')
        self.assertIs(m_field, field)

    def test_sqlschema_custom_type(self):
        import ptah

        class Test31(ptah.get_base()):
            __tablename__ = 'test31'
            id = sqla.Column('id', sqla.Integer, primary_key=True)
            name = sqla.Column(sqla.Unicode(), info={'field_type': 'int'})

        fieldset = ptah.generate_fieldset(Test31)

        m_field = fieldset['name']

        self.assertEqual(m_field.__field__, 'int')

    def test_sqlschema_custom_factory(self):
        import ptah

        class Test32(ptah.get_base()):
            __tablename__ = 'test32'
            id = sqla.Column('id', sqla.Integer, primary_key=True)
            name = sqla.Column(sqla.Unicode(),
                               info={'field_type': pform.IntegerField})

        fieldset = ptah.generate_fieldset(Test32)

        m_field = fieldset['name']
        self.assertIsInstance(m_field, pform.IntegerField)

    def test_sqlschema_skip(self):
        import ptah

        class Test34(ptah.get_base()):
            __tablename__ = 'test34'
            id = sqla.Column('id', sqla.Integer, primary_key=True)
            name = sqla.Column(sqla.Unicode(), info={'skip': True})

        fieldset = ptah.generate_fieldset(Test34)

        self.assertNotIn('name', fieldset)

    def test_sqlschema_unknown(self):
        import ptah

        class Test2(ptah.get_base()):
            __tablename__ = 'test5'

            id = sqla.Column('id', sqla.Integer, primary_key=True)
            name = sqla.Column(sqla.Unicode())
            json = sqla.Column(ptah.JsonListType())

        fieldset = ptah.generate_fieldset(Test2)

        self.assertNotIn('json', fieldset)


class TestQueryFreezer(PtahTestCase):

    _init_sqla = False

    def test_freezer_one(self):
        import ptah

        class Test(ptah.get_base()):
            __tablename__ = 'test10'

            id = sqla.Column('id', sqla.Integer, primary_key=True)
            name = sqla.Column(sqla.Unicode())

        ptah.get_base().metadata.create_all()
        transaction.commit()

        sql_get = ptah.QueryFreezer(
            lambda: Session.query(Test)
            .filter(Test.name == sqla.sql.bindparam('name')))

        self.assertRaises(
            sqla.orm.exc.NoResultFound, sql_get.one, name='test')

        rec = Test()
        rec.name = 'test'
        Session.add(rec)
        Session.flush()

        rec = sql_get.one(name='test')
        self.assertEqual(rec.name, 'test')

        rec = Test()
        rec.name = 'test'
        Session.add(rec)
        Session.flush()

        self.assertRaises(
            sqla.orm.exc.MultipleResultsFound, sql_get.one, name='test')

    def test_freezer_first(self):
        import ptah

        class Test(ptah.get_base()):
            __tablename__ = 'test12'

            id = sqla.Column('id', sqla.Integer, primary_key=True)
            name = sqla.Column(sqla.Unicode())

        ptah.get_base().metadata.create_all()
        transaction.commit()

        sql_get = ptah.QueryFreezer(
            lambda: Session.query(Test)
            .filter(Test.name == sqla.sql.bindparam('name')))

        self.assertIsNone(sql_get.first(name='test'))

        rec = Test()
        rec.name = 'test'
        Session.add(rec)
        Session.flush()

        rec = sql_get.one(name='test')
        self.assertEqual(rec.name, 'test')

        sql_get.reset()
        rec = sql_get.one(name='test')
        self.assertEqual(rec.name, 'test')

    def test_freezer_all(self):
        import ptah

        class Test(ptah.get_base()):
            __tablename__ = 'test13'

            id = sqla.Column('id', sqla.Integer, primary_key=True)
            name = sqla.Column(sqla.Unicode())

        ptah.get_base().metadata.create_all()
        transaction.commit()

        sql_get = ptah.QueryFreezer(
            lambda: Session.query(Test)
            .filter(Test.name == sqla.sql.bindparam('name')))

        self.assertIsNone(sql_get.first(name='test'))

        rec = Test()
        rec.name = 'test'
        Session.add(rec)
        Session.flush()

        rec = sql_get.all(name='test')
        self.assertEqual(rec[0].name, 'test')


class TestJsonDict(PtahTestCase):

    _init_sqla = False

    def test_jsondict(self):
        import ptah
        ptah.reset_session()

        self.config.ptah_init_sql()

        class Test(ptah.get_base()):
            __tablename__ = 'test14'

            id = sqla.Column('id', sqla.Integer, primary_key=True)
            data = sqla.Column(ptah.JsonDictType())

        Session = ptah.get_session()
        ptah.get_base().metadata.create_all()
        transaction.commit()

        rec = Test()
        rec.data = {'test': 'val'}
        Session.add(rec)
        Session.flush()
        id = rec.id
        transaction.commit()

        rec = Session.query(Test).filter_by(id = id).one()
        self.assertEqual(rec.data, {'test': 'val'})

        rec.data['test2'] = 'val2'
        transaction.commit()

        rec = Session.query(Test).filter_by(id = id).one()
        self.assertEqual(rec.data,
                         {'test': 'val', 'test2': 'val2'})

        del rec.data['test']
        transaction.commit()

        rec = Session.query(Test).filter_by(id = id).one()
        self.assertEqual(rec.data, {'test2': 'val2'})


class TestJsonList(PtahTestCase):

    _init_sqla = False

    def test_jsonlist(self):
        import ptah

        Base = ptah.get_base()

        class Test(Base):
            __tablename__ = 'test15'

            id = sqla.Column('id', sqla.Integer, primary_key=True)
            data = sqla.Column(ptah.JsonListType())

        Session = ptah.get_session()
        Base.metadata.create_all()
        transaction.commit()

        rec = Test()
        rec.data = ['test']
        Session.add(rec)
        Session.flush()
        id = rec.id
        transaction.commit()

        rec = Session.query(Test).filter_by(id = id).one()
        self.assertEqual(rec.data, ['test'])

        rec.data[0] = 'test2'
        transaction.commit()

        rec = Session.query(Test).filter_by(id = id).one()
        self.assertEqual(rec.data, ['test2'])

        rec.data.append('test')
        transaction.commit()

        rec = Session.query(Test).filter_by(id = id).one()
        self.assertEqual(rec.data, ['test2', 'test'])

        del rec.data[rec.data.index('test2')]
        transaction.commit()

        rec = Session.query(Test).filter_by(id = id).one()
        self.assertEqual(rec.data, ['test'])


class TestJsonSerializer(TestCase):

    def test_global_custom_serializer(self):
        from ptah.sqlautils import JsonType

        s = object()

        ptah.set_jsontype_serializer(s)

        jsType = JsonType()
        self.assertIs(jsType.serializer, s)

    def test_custom_serializer(self):
        from ptah.sqlautils import JsonType

        s = object()

        jsType = JsonType(serializer=s)
        self.assertIs(jsType.serializer, s)

########NEW FILE########
__FILENAME__ = test_sqlsession
import ptah
from ptah.testing import PtahTestCase


class TestSqlSession(PtahTestCase):

    def test_transaction(self):
        from ptah.sqlautils import transaction

        class SA(object):

            commited = False
            rollbacked = False

            raise_commit = False

            def commit(self):
                if self.raise_commit:
                    raise RuntimeError()
                self.commited = True

            def rollback(self):
                self.rollbacked = True

        sa = SA()
        trans = transaction(sa)

        with trans:
            pass

        self.assertTrue(sa.commited)

        sa = SA()
        trans = transaction(sa)
        try:
            with trans:
                raise ValueError()
        except:
            pass
        self.assertTrue(sa.rollbacked)

        sa = SA()
        sa.raise_commit = True
        trans = transaction(sa)
        try:
            with trans:
                pass
        except:
            pass
        self.assertTrue(sa.rollbacked)

    def test_sa_session(self):
        with ptah.sa_session() as sa:
            self.assertIs(sa, ptah.get_session())

    def test_sa_session_nested(self):
        err = None

        try:
            with ptah.sa_session():
                with ptah.sa_session():
                    pass
        except Exception as e:
            err = e

        self.assertIsNotNone(err)

########NEW FILE########
__FILENAME__ = test_tinfo
import pform
from pyramid.httpexceptions import HTTPForbidden
from pyramid.exceptions import ConfigurationError, ConfigurationConflictError
from ptah.testing import PtahTestCase, TestCase


class TestTypeInfo(PtahTestCase):

    _init_auth = True
    _init_ptah = False

    def tearDown(self):
        super(TestTypeInfo, self).tearDown()

        from ptah import typeinfo
        t = []
        for name, h in typeinfo.phase_data:
            if name !='test':
                t.append((name, h))
        typeinfo.phase_data[:] = t

    def test_tinfo(self):
        import ptah

        @ptah.tinfo('mycontent', 'MyContent')
        class Mycontent(object):
            pass

        self.init_ptah()

        all_types = ptah.get_types()

        self.assertTrue('type:mycontent' in all_types)

        tinfo = ptah.get_type('type:mycontent')

        self.assertEqual(tinfo.__uri__, 'type:mycontent')
        self.assertEqual(tinfo.name, 'mycontent')
        self.assertEqual(tinfo.title, 'MyContent')
        self.assertIs(tinfo.cls, Mycontent)
        self.assertIs(Mycontent.__type__, tinfo)

    def test_tinfo_title(self):
        import ptah

        @ptah.tinfo('mycontent')
        class MyContent(object):
            pass

        self.assertEqual(MyContent.__type__.title, 'Mycontent')

        @ptah.tinfo('mycontent', 'MyContent')
        class MyContent(object):
            pass

        self.assertEqual(MyContent.__type__.title, 'MyContent')

    def test_tinfo_checks(self):
        import ptah

        @ptah.tinfo('mycontent', 'Content', permission=None)
        class MyContent(object):
            pass
        @ptah.tinfo('mycontainer', 'Container')
        class MyContainer(object):
            pass
        self.init_ptah()

        container = MyContainer()

        #
        self.assertTrue(MyContent.__type__.is_allowed(container))
        self.assertEqual(MyContent.__type__.check_context(container), None)

        # permission
        MyContent.__type__.permission = 'Protected'
        self.assertFalse(MyContent.__type__.is_allowed(container))
        self.assertRaises(
            HTTPForbidden, MyContent.__type__.check_context, container)

    def test_tinfo_list(self):
        import ptah

        @ptah.tinfo('mycontent', 'Content', permission=None)
        class MyContent(object):
            pass
        @ptah.tinfo('mycontainer', 'Container')
        class MyContainer(object):
            pass
        self.init_ptah()

        content = MyContent()
        container = MyContainer()

        self.assertEqual(MyContent.__type__.list_types(content), [])
        self.assertEqual(MyContent.__type__.list_types(container), ())

        MyContent.__type__.global_allow = True
        self.assertEqual(MyContainer.__type__.list_types(container),
                         [MyContent.__type__])

        MyContent.__type__.global_allow = False
        self.assertEqual(MyContainer.__type__.list_types(container), [])

        MyContent.__type__.global_allow = True
        MyContent.__type__.permission = 'Protected'
        self.assertEqual(MyContainer.__type__.list_types(container), [])

    def test_tinfo_list_filtered(self):
        import ptah

        @ptah.tinfo('mycontent', 'Content', permission=None)
        class MyContent(object):
            pass

        @ptah.tinfo('mycontainer', 'Container', filter_content_types=True)
        class MyContainer(object):
            pass
        self.init_ptah()

        container = MyContainer()
        self.assertEqual(MyContainer.__type__.list_types(container), [])

        MyContainer.__type__.allowed_content_types = ('mycontent',)
        self.assertEqual(MyContainer.__type__.list_types(container),
                         [MyContent.__type__])

    def test_tinfo_list_filtered_callable(self):
        import ptah

        @ptah.tinfo('mycontent', 'Content', permission=None)
        class MyContent(object):
            pass
        @ptah.tinfo('mycontainer', 'Container', filter_content_types=True)
        class MyContainer(object):
            pass

        self.init_ptah()

        container = MyContainer()
        self.assertEqual(MyContainer.__type__.list_types(container), [])

        def filter(content):
            return ('mycontent',)

        MyContainer.__type__.allowed_content_types = filter
        self.assertEqual(MyContainer.__type__.list_types(container),
                         [MyContent.__type__])

    def test_tinfo_conflicts(self):
        import ptah

        @ptah.tinfo('mycontent2', 'MyContent')
        class MyContent(object):
            pass
        @ptah.tinfo('mycontent2', 'MyContent')
        class MyContent2(object):
            pass

        self.assertRaises(ConfigurationConflictError, self.init_ptah)

    def test_tinfo_create(self):
        import ptah

        @ptah.tinfo('mycontent', 'MyContent')
        class MyContent(object):

            def __init__(self, title=''):
                self.title = title

        self.init_ptah()

        all_types = ptah.get_types()

        content = all_types['type:mycontent'].create(title='Test content')

        self.assertTrue(isinstance(content, MyContent))
        self.assertEqual(content.title, 'Test content')

    def test_tinfo_fieldset(self):
        import ptah

        MySchema = pform.Fieldset(pform.TextField('test'))

        @ptah.tinfo('mycontent2', 'MyContent', fieldset=MySchema)
        class MyContent(object):
            pass

        tinfo = MyContent.__type__
        self.assertIs(tinfo.fieldset, MySchema)

    def test_tinfo_type_resolver(self):
        import ptah

        @ptah.tinfo('mycontent2', 'MyContent')
        class MyContent(object):
            pass

        self.init_ptah()

        tinfo_uri = MyContent.__type__.__uri__

        self.assertEqual(tinfo_uri, 'type:mycontent2')
        self.assertIs(ptah.resolve(tinfo_uri), MyContent.__type__)

    def test_add_method(self):
        import ptah

        @ptah.tinfo('mycontent2', 'MyContent')
        class MyContent(object):
            pass

        self.init_ptah()

        tinfo = MyContent.__type__

        err=None
        try:
            tinfo.add(None, MyContent())
        except Exception as e:
            err=e

        self.assertIsNotNone(err)

        added = []
        def add_content(item):
            added.append(item)

        tinfo.add_method = add_content

        item = MyContent()
        tinfo.add(item)
        self.assertIn(item, added)

    def test_phase2_err(self):
        from ptah.typeinfo import phase2

        @phase2('test')
        def t(): pass

        err = None
        try:
            @phase2('test')
            def t1(): pass
        except Exception as e:
            err = e

        self.assertIsNotNone(err)


class TestSqlTypeInfo(PtahTestCase):

    _init_auth = True
    _init_ptah = False

    def tearDown(self):
        super(TestSqlTypeInfo, self).tearDown()

        from ptah import typeinfo

        t = []
        for name, h in typeinfo.phase_data:
            if name !='test':
                t.append((name, h))
        typeinfo.phase_data[:] = t

    def test_tinfo(self):
        import ptah
        from ptah import typeinfo
        import sqlalchemy as sqla

        @ptah.tinfo('mycontent', 'MyContent')
        class MyContentSql(ptah.get_base()):

            __tablename__ = 'tinfo_sql_test'

            id = sqla.Column('id', sqla.Integer, primary_key=True)

        self.init_ptah()

        ti = ptah.get_type('type:mycontent')
        self.assertIs(ti.add_method, typeinfo.sqla_add_method)

    def test_custom_fieldset(self):
        import ptah
        import sqlalchemy as sqla

        @ptah.tinfo('mycontent', 'MyContent')
        class MyContentSql(ptah.get_base()):

            __tablename__ = 'tinfo_sql_test2'

            id = sqla.Column(sqla.Integer, primary_key=True)
            test = sqla.Column(sqla.Unicode)

        self.init_ptah()

        ti = ptah.get_type('type:mycontent')
        self.assertIn('test', ti.fieldset)

    def test_custom_fieldset_fieldNames(self):
        import ptah
        import sqlalchemy as sqla

        @ptah.tinfo('mycontent', 'MyContent', fieldNames=['test'])
        class MyContentSql(ptah.get_base()):

            __tablename__ = 'tinfo_sql_test21'

            id = sqla.Column(sqla.Integer, primary_key=True)
            test = sqla.Column(sqla.Unicode)
            test1 = sqla.Column(sqla.Unicode)

        self.init_ptah()

        ti = ptah.get_type('type:mycontent')
        self.assertIn('test', ti.fieldset)
        self.assertNotIn('test1', ti.fieldset)

    def test_custom_fieldset_namesFilter(self):
        import ptah
        import sqlalchemy as sqla

        def filter(n, names):
            return n != 'test'

        @ptah.tinfo('mycontent', 'MyContent', namesFilter=filter)
        class MyContentSql(ptah.get_base()):

            __tablename__ = 'tinfo_sql_test22'

            id = sqla.Column(sqla.Integer, primary_key=True)
            test = sqla.Column(sqla.Unicode)
            test1 = sqla.Column(sqla.Unicode)

        self.init_ptah()

        ti = ptah.get_type('type:mycontent')
        self.assertIn('test1', ti.fieldset)
        self.assertNotIn('test', ti.fieldset)

    def test_sqla_add_method(self):
        import ptah
        import sqlalchemy as sqla

        @ptah.tinfo('mycontent', 'MyContent')
        class MyContentSql(ptah.get_base()):

            __tablename__ = 'tinfo_sql_test3'

            id = sqla.Column(sqla.Integer, primary_key=True)
            test = sqla.Column(sqla.Unicode)

        self.init_ptah()

        ti = ptah.get_type('type:mycontent')

        item = ti.add(MyContentSql(test='title'))
        sa = ptah.get_session()
        self.assertIn(item, sa)

    def test_uri_prop(self):
        import ptah
        import sqlalchemy as sqla

        @ptah.tinfo('mycontent', 'MyContent')
        class MyContentSql(ptah.get_base()):

            __tablename__ = 'tinfo_sql_test4'
            id = sqla.Column(sqla.Integer, primary_key=True)
            test = sqla.Column(sqla.Unicode)

        self.init_ptah()

        self.assertTrue(hasattr(MyContentSql, '__uri__'))

        self.assertEqual(MyContentSql.__uri__.cname, 'id')
        self.assertEqual(MyContentSql.__uri__.prefix, 'mycontent')

    def test_uri_prop_exist(self):
        import ptah
        import sqlalchemy as sqla

        @ptah.tinfo('mycontent', 'MyContent')
        class MyContentSql(ptah.get_base()):

            __uri__ = 'test'
            __tablename__ = 'tinfo_sql_test5'
            id = sqla.Column(sqla.Integer, primary_key=True)
            test = sqla.Column(sqla.Unicode)

        self.init_ptah()
        self.assertTrue(MyContentSql.__uri__, 'test')

    def test_uri_resolver_exists(self):
        import ptah
        import sqlalchemy as sqla

        def resolver(uri):
            """ """

        ptah.resolver.register('mycontent', resolver)

        @ptah.tinfo('mycontent', 'MyContent')
        class MyContentSql(ptah.get_base()):
            __tablename__ = 'tinfo_sql_test6'

            id = sqla.Column(sqla.Integer, primary_key=True)
            test = sqla.Column(sqla.Unicode)

        self.assertRaises(ConfigurationError, self.init_ptah)

    def test_uri_resolver(self):
        import ptah
        import sqlalchemy as sqla

        @ptah.tinfo('mycontent', 'MyContent')
        class MyContentSql(ptah.get_base()):
            __tablename__ = 'tinfo_sql_test7'

            id = sqla.Column(sqla.Integer, primary_key=True)
            test = sqla.Column(sqla.Unicode)

        self.init_ptah()

        id = None
        uri = None

        with ptah.sa_session() as sa:
            item = MyContentSql(test='title')
            sa.add(item)
            sa.flush()

            id = item.id
            uri = item.__uri__

        self.assertEqual(uri, 'mycontent:%s'%id)

        item = ptah.resolve(uri)
        self.assertTrue(item.id == id)


class TestUriProperty(TestCase):

    def test_uri_property(self):
        from ptah.typeinfo import UriProperty

        class Test(object):

            __uri__ = UriProperty('test-uri', 'id')

        self.assertTrue(isinstance(Test.__uri__, UriProperty))

        item = Test()
        item.id = 10

        self.assertEqual(item.__uri__, 'test-uri:10')

########NEW FILE########
__FILENAME__ = test_token
import transaction
from datetime import timedelta
from pyramid.exceptions import ConfigurationConflictError

from ptah.testing import PtahTestCase


class TestTokenType(PtahTestCase):

    _init_ptah = False

    def test_token(self):
        from ptah import token

        tt = token.TokenType('unique-id', timedelta(minutes=20))
        self.init_ptah()

        t = token.service.generate(tt, 'data')
        transaction.commit()

        self.assertEqual(token.service.get(t), 'data')
        self.assertEqual(token.service.get_bydata(tt, 'data'), t)

        token.service.remove(t)
        self.assertEqual(token.service.get(t), None)

    def test_token_type(self):
        from ptah import token

        token.TokenType('unique-id', timedelta(minutes=20))
        token.TokenType('unique-id', timedelta(minutes=20))

        self.assertRaises(ConfigurationConflictError, self.init_ptah)

    def test_token_remove_expired(self):
        pass

########NEW FILE########
__FILENAME__ = test_uiaction
import ptah
from ptah.testing import PtahTestCase
from pyramid.exceptions import ConfigurationConflictError


class TestUIAction(PtahTestCase):

    _init_ptah = False

    def test_uiaction(self):
        class Content(object):
            __name__ = ''

        ptah.uiaction(Content, 'action1', 'Action 1')
        self.init_ptah()

        actions = ptah.list_uiactions(Content(), self.request)

        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0]['id'], 'action1')

    def test_uiaction_conflicts(self):
        class Content(object):
            __name__ = ''

        ptah.uiaction(Content, 'action1', 'Action 1')
        ptah.uiaction(Content, 'action1', 'Action 1')
        self.assertRaises(ConfigurationConflictError, self.init_ptah)

    def test_uiaction_url(self):

        class Content(object):
            __name__ = ''

        ptah.uiaction(Content, 'action1', 'Action 1', action='test.html')
        self.init_ptah()

        actions = ptah.list_uiactions(Content(), self.request)
        self.assertEqual(actions[0]['url'], 'http://example.com/test.html')

    def test_uiaction_url_no_request(self):

        class Content(object):
            __name__ = ''

        ptah.uiaction(Content, 'action1', 'Action 1', action='test.html')
        self.init_ptah()

        actions = ptah.list_uiactions(Content(), registry=self.registry)
        self.assertEqual(actions[0]['url'], '')

    def test_uiaction_absolute_url(self):

        class Content(object):
            __name__ = ''

        ptah.uiaction(
            Content, 'action1', 'Action 1', action='/content/about.html')
        self.init_ptah()

        actions = ptah.list_uiactions(Content(), self.request)
        self.assertEqual(actions[0]['url'],
                         'http://example.com/content/about.html')

    def test_uiaction_custom_url(self):

        class Content(object):
            __name__ = ''

        def customAction(content, request):
            return 'http://github.com/ptahproject'

        ptah.uiaction(Content, 'action1', 'Action 1', action=customAction)

        self.init_ptah()

        actions = ptah.list_uiactions(Content(), self.request)
        self.assertEqual(actions[0]['url'], 'http://github.com/ptahproject')

    def test_uiaction_condition(self):

        class Content(object):
            __name__ = ''

        allow = False
        def condition(content, request):
            return allow

        ptah.uiaction(
            Content, 'action1', 'Action 1',
            action='test.html', condition=condition)

        self.init_ptah()

        actions = ptah.list_uiactions(Content(), self.request)
        self.assertEqual(len(actions), 0)

        allow = True
        actions = ptah.list_uiactions(Content(), self.request)
        self.assertEqual(len(actions), 1)

    def test_uiaction_permission(self):

        class Content(object):
            __name__ = ''

        allow = False
        def check_permission(permission, content, request=None, throw=False):
            return allow

        ptah.uiaction(Content, 'action1', 'Action 1', permission='View')

        self.init_ptah()

        orig_cp = ptah.check_permission
        ptah.check_permission = check_permission

        actions = ptah.list_uiactions(Content(), self.request)
        self.assertEqual(len(actions), 0)

        allow = True
        actions = ptah.list_uiactions(Content(), self.request)
        self.assertEqual(len(actions), 1)

        ptah.check_permission = orig_cp

    def test_uiaction_sort_weight(self):

        class Content(object):
            __name__ = ''

        ptah.uiaction(Content, 'view', 'View', sort_weight=1.0)
        ptah.uiaction(Content, 'action', 'Action', sort_weight=2.0)

        self.init_ptah()

        actions = ptah.list_uiactions(Content(), self.request)

        self.assertEqual(actions[0]['id'], 'view')
        self.assertEqual(actions[1]['id'], 'action')

    def test_uiaction_userdata(self):

        class Content(object):
            __name__ = ''

        ptah.uiaction(Content, 'view', 'View', testinfo='test')

        self.init_ptah()

        actions = ptah.list_uiactions(Content(), self.request)

        self.assertEqual(actions[0]['data'], {'testinfo': 'test'})

    def test_uiaction_category(self):
        class Content(object):
            __name__ = ''

        ptah.uiaction(Content, 'action1', 'Action 1',
                      category='test')

        self.init_ptah()

        actions = ptah.list_uiactions(Content(), self.request)
        self.assertEqual(len(actions), 0)

        actions = ptah.list_uiactions(Content(), self.request, category='test')

        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0]['id'], 'action1')

    def test_uiaction_category_reg_fail(self):
        class Content(object):
            __name__ = ''

        ptah.uiaction(Content, 'action1', 'Action 10', category='test')
        ptah.uiaction(Content, 'action1', 'Action 11', category='test')
        self.assertRaises(ConfigurationConflictError, self.init_ptah)

    def test_uiaction_category_reg(self):
        class Content(object):
            __name__ = ''

        ptah.uiaction(Content, 'action1', 'Action 10')
        ptah.uiaction(Content, 'action1', 'Action 11', category='test')

        self.init_ptah()

        actions = ptah.list_uiactions(Content(), self.request)
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0]['title'], 'Action 10')

        actions = ptah.list_uiactions(Content(), self.request, category='test')

        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0]['title'], 'Action 11')

########NEW FILE########
__FILENAME__ = test_uri
from pyramid import testing
from pyramid.exceptions import ConfigurationConflictError
from ptah.testing import PtahTestCase


class TestUri(PtahTestCase):

    _init_ptah = False

    def test_uri_registration(self):
        import ptah

        def resolver1(uri):
            return 'Resolved1'
        def resolver2(uri):
            return 'Resolved2'

        ptah.resolver.register('test1', resolver1)
        ptah.resolver.register('test2', resolver2)

        self.init_ptah()

        self.assertEqual(ptah.resolve('test1:uri'), 'Resolved1')
        self.assertEqual(ptah.resolve('test2:uri'), 'Resolved2')

        self.assertEqual(ptah.resolve(None), None)
        self.assertEqual(ptah.resolve('unknown'), None)
        self.assertEqual(ptah.resolve('unknown:uri'), None)

    def test_uri_resolver_pyramid(self):
        import ptah

        def resolver1(uri):
            return 'Resolved-pyramid'

        config = testing.setUp()
        config.include('ptah')
        config.ptah_uri_resolver('test1', resolver1)
        config.commit()

        self.assertEqual(ptah.resolve('test1:uri'), 'Resolved-pyramid')

    def test_uri_registration_decorator(self):
        import ptah

        @ptah.resolver('test1')
        def resolver1(uri):
            return 'Resolved1'

        @ptah.resolver('test2')
        def resolver2(uri):
            return 'Resolved2'

        self.init_ptah()

        self.assertEqual(ptah.resolve('test1:uri'), 'Resolved1')
        self.assertEqual(ptah.resolve('test2:uri'), 'Resolved2')

        self.assertEqual(ptah.resolve(None), None)
        self.assertEqual(ptah.resolve('unknown'), None)
        self.assertEqual(ptah.resolve('unknown:uri'), None)

    def test_uri_registration_conflicts(self):
        import ptah
        ptah.resolver.register('test', None)
        ptah.resolver.register('test', None)

        self.assertRaises(ConfigurationConflictError, self.init_ptah)

    def test_uri_registration_decorator_conflicts(self):
        import ptah

        @ptah.resolver('test1')
        def resolver1(uri): # pragma: no cover
            return 'Resolved1'

        @ptah.resolver('test1')
        def resolver2(uri): # pragma: no cover
            return 'Resolved2'

        self.assertRaises(ConfigurationConflictError, self.init_ptah)

    def test_uri_extract_type(self):
        import ptah

        self.assertEqual(ptah.extract_uri_schema('test:uri'), 'test')
        self.assertEqual(ptah.extract_uri_schema('test'), None)
        self.assertEqual(ptah.extract_uri_schema(None), None)

    def test_uri_uri_generator(self):
        import ptah

        uri = ptah.UriFactory('test')

        u1 = uri()
        u2 = uri()

        self.assertTrue(u1.startswith('test:'))
        self.assertTrue(u2.startswith('test:'))
        self.assertTrue(u1 != u2)

########NEW FILE########
__FILENAME__ = test_util
from datetime import datetime
from ptah.testing import TestCase


class TestJson(TestCase):

    def test_datetime(self):
        from ptah import util
        dt = datetime(2011, 10, 1, 1, 56)

        self.assertEqual(util.dthandler(dt), 'Sat, 01 Oct 2011 01:56:00 -0000')
        self.assertIsNone(util.dthandler(object()))

    def test_json(self):
        from ptah import util

        data = {'date': datetime(2011, 10, 1, 1, 56),
                'int': 10,
                'str': 'string'}

        self.assertEqual(
            util.json.dumps(data),
            '{"date":"Sat, 01 Oct 2011 01:56:00 -0000","int":10,"str":"string"}')

        self.assertEqual(
            util.json.loads('{"int":10,"str":"string"}'),
            {'int': 10, 'str': 'string'})

########NEW FILE########
__FILENAME__ = test_view
# -*- coding: utf-8 -*-
import ptah
from ptah.testing import PtahTestCase


class Context(object):
    pass


class TestView(PtahTestCase):

    _init_ptah = False

    def test_view_app_root(self):
        view = ptah.View(Context(), self.request)
        self.assertEqual(view.application_url, 'http://example.com')

        view = ptah.View(Context(), self.request)
        self.request.application_url = 'http://example.com/'
        self.assertEqual(view.application_url, 'http://example.com')

    def test_view_update(self):
        view = ptah.View(Context(), self.request)
        self.assertEqual(view.update(), {})


class TestMasterLayout(PtahTestCase):

    def test_master_layout(self):
        from ptah.view import MasterLayout

        ml = MasterLayout(object(), self.request)
        self.assertIsNone(ml.user)
        self.assertEqual(ml.manage_url, 'http://example.com/ptah-manage')
        self.assertEqual(ml.actions, [])

########NEW FILE########
__FILENAME__ = token
""" simple token service """
import uuid
import datetime
import sqlalchemy as sqla

import ptah
from ptah import config
from ptah.sqlautils import QueryFreezer

__all__ = ['TokenType', 'service']

ID_TOKEN_TYPE = 'ptah:tokentype'


class TokenType(object):
    """ Token type interface

    ``id`` unique token type id. Token service uses this id
    for token type identification in tokens storage.

    ``timeout`` token timout, it has to be timedelta instance.
    """

    def __init__(self, id, timeout, title='', description=''):
        self.id = id
        self.timeout = timeout
        self.title = title
        self.description = description

        info = config.DirectiveInfo()
        discr = (ID_TOKEN_TYPE, id)
        intr = config.Introspectable(
            ID_TOKEN_TYPE, discr, title, 'ptah-tokentype')
        intr['ttype'] = self
        intr['codeinfo'] = info.codeinfo

        info.attach(
            config.Action(
                lambda config, id, tp: \
                    config.get_cfg_storage(ID_TOKEN_TYPE).update({id: tp}),
                (id, self), discriminator=discr, introspectables=(intr,))
            )


class TokenService(object):
    """ Token management service """

    _sql_get = QueryFreezer(
        lambda: ptah.get_session().query(Token).filter(
            Token.token == sqla.sql.bindparam('token')))

    _sql_get_by_data = QueryFreezer(
        lambda: ptah.get_session().query(Token).filter(
            sqla.sql.and_(Token.data == sqla.sql.bindparam('data'),
                          Token.typ == sqla.sql.bindparam('typ'))))

    def generate(self, typ, data):
        """ Generate and return string token.

        ``type`` object implemented ITokenType interface.

        ``data`` token type specific data, it must be python string. """

        t = Token(typ, data)

        Session = ptah.get_session()
        Session.add(t)
        Session.flush()
        return t.token

    def get(self, token):
        """ Get data for token """
        t = self._sql_get.first(token=token)
        if t is not None:
            return t.data

    def get_bydata(self, typ, data):
        """ Get token for data """
        t = self._sql_get_by_data.first(data=data, typ=typ.id)
        if t is not None:
            return t.token

    def remove(self, token):
        """ Remove token """
        ptah.get_session().query(Token).filter(
            sqla.sql.or_(Token.token == token,
                         Token.valid > datetime.datetime.now())).delete()


service = TokenService()

class Token(ptah.get_base()):

    __tablename__ = 'ptah_tokens'

    id = sqla.Column(sqla.Integer, primary_key=True)
    token = sqla.Column(sqla.Unicode(48))
    valid = sqla.Column(sqla.DateTime)
    data = sqla.Column(sqla.Text)
    typ = sqla.Column('type', sqla.Unicode(48))

    def __init__(self, typ, data):
        super(Token, self).__init__()

        self.typ = typ.id
        self.data = data
        self.valid = datetime.datetime.now() + typ.timeout
        self.token = uuid.uuid4().hex

########NEW FILE########
__FILENAME__ = typeinfo
""" type implementation """
import logging
import sqlalchemy as sqla
from zope.interface import implementer
from pyramid.compat import string_types
from pyramid.threadlocal import get_current_registry
from pyramid.exceptions import ConfigurationError

import ptah
from ptah import config
from ptah.uri import ID_RESOLVER
from ptah.security import NOT_ALLOWED
from ptah.interfaces import ITypeInformation, Forbidden, TypeException

log = logging.getLogger('ptah')

TYPES_DIR_ID = 'ptah:type'


@ptah.resolver('type')
def typeInfoResolver(uri):
    """Type resolver

       :Parameters:
         - type scheme, e.g. blob-sql
       :Returns:
         - :py:class:`ptah.TypeInformation`
    """
    return config.get_cfg_storage(TYPES_DIR_ID).get(uri)


def get_type(uri):
    """ Get registered type.

    :param uri: string identifier for TypeInformation, e.g. `type:sqlblob`

    :Returns:
      - :py:class:`ptah.TypeInformation`

    """
    return config.get_cfg_storage(TYPES_DIR_ID).get(uri)


def get_types():
    """ Get all registered types.

    :Returns:
      - mapping of all registered identifier and TypeInformation
    """
    return config.get_cfg_storage(TYPES_DIR_ID)


phase_data = []

class phase2(object):

    def __init__(self, name):
        self.name = name
        for n, _ in phase_data:
            if n == name:
                raise ConfigurationError(
                    'type phase "%s" is already registered'%name)

    def __call__(self, callback):
        phase_data.append((self.name, callback))
        return callback


@implementer(ITypeInformation)
class TypeInformation(object):
    """ Type information """

    title = ''
    description = ''

    fieldset = None
    permission = NOT_ALLOWED

    filter_content_types = False
    allowed_content_types = ()
    global_allow = False

    add_method = None

    def __init__(self, cls, name, **kw):
        self.__dict__.update(kw)

        self.__uri__ = 'type:%s'%name

        self.cls = cls
        self.name = name

    def add(self, content, *args, **kw):
        if self.add_method is None:
            raise TypeException("Add method is not defined")

        return self.add_method(content, *args, **kw)

    def create(self, **data):
        content = self.cls(**data)
        get_current_registry().notify(ptah.events.ContentCreatedEvent(content))
        return content

    def is_allowed(self, container):
        if self.permission:
            return ptah.check_permission(self.permission, container)
        return True

    def check_context(self, container):
        if not self.is_allowed(container):
            raise Forbidden()

    def list_types(self, container):
        if container.__type__ is not self:
            return ()

        types = []
        all_types = config.get_cfg_storage(TYPES_DIR_ID)

        if self.filter_content_types:
            allowed_types = self.allowed_content_types
            if callable(allowed_types):
                allowed_types = allowed_types(container)

            for tinfo in allowed_types:
                if isinstance(tinfo, string_types):
                    tinfo = all_types.get('type:%s'%tinfo)

                if tinfo and tinfo.is_allowed(container):
                    types.append(tinfo)
        else:
            for tinfo in all_types.values():
                if tinfo.global_allow and tinfo.is_allowed(container):
                    types.append(tinfo)

        return types


class tinfo(object):
    """ Declare new type. This function has to be called within a content
    class declaration.

    .. code-block:: python

        @ptah.tinfo('My content')
        class MyContent(object):
            pass

    """

    def __init__(self, name, title=None, **kw):
        self.name = name
        self.info = config.DirectiveInfo()
        kw['title'] = name.capitalize() if title is None else title
        self.kw = kw

    def __call__(self, cls):
        typeinfo = TypeInformation(cls, self.name, **self.kw)
        cls.__type__ = typeinfo

        # config actino and introspection info
        discr = (TYPES_DIR_ID, self.name)
        intr = config.Introspectable(
            TYPES_DIR_ID, discr, self.name, 'ptah-type')
        intr['name'] = self.name
        intr['type'] = typeinfo
        intr['codeinfo'] = self.info.codeinfo

        def register_type_impl(cfg):
            # run phase handlers
            for name, handler in phase_data:
                handler(cfg, cls, typeinfo, self.name, **self.kw)

            cfg.get_cfg_storage(TYPES_DIR_ID)[typeinfo.__uri__] = typeinfo

        self.info.attach(
            config.Action(register_type_impl,
                          discriminator=discr, introspectables=(intr,))
            )

        return cls


def sqla_add_method(content, *args, **kw):
    sa = ptah.get_session()
    sa.add(content)
    sa.flush()
    return content


@phase2('sqla')
def register_sqla_type(config, cls, tinfo, name, **kw):
    base = ptah.get_base()
    if not issubclass(cls, base):
        return

    # generate schema
    fieldset = tinfo.fieldset

    if fieldset is None:
        fieldset = ptah.generate_fieldset(
            cls, fieldNames=kw.get('fieldNames'),
            namesFilter=kw.get('namesFilter'))
        log.info("Generating fieldset for %s content type.", cls)

    if fieldset is not None:
        tinfo.fieldset = fieldset

    if tinfo.add_method is None:
        tinfo.add_method = sqla_add_method

    # install __uri__ property
    if not hasattr(cls, '__uri__') or hasattr(cls, '__uri_reinstall__'):
        pname = None
        for cl in cls.__table__.columns:
            if cl.primary_key:
                pname = cl.name
                break

        l = len(tinfo.name)+1
        cls.__uri_reinstall__ = True
        cls.__uri__ = UriProperty(tinfo.name, cl.name)

        cls.__uri_sql_get__ = ptah.QueryFreezer(
            lambda: ptah.get_session().query(cls) \
                .filter(getattr(cls, pname) == sqla.sql.bindparam('uri')))

        def resolver(uri):
            """Content resolver for %s type'"""%tinfo.name
            return cls.__uri_sql_get__.first(uri=uri[l:])

        storage = config.get_cfg_storage(ID_RESOLVER)
        if tinfo.name in storage:
            raise ConfigurationError(
                'Resolver for "%s" already registered'%tinfo.name)
        storage[tinfo.name] = resolver


class UriProperty(object):

    def __init__(self, prefix, cname):
        self.cname = cname
        self.prefix = prefix

    def __get__(self, inst, cls):
        if inst is None:
            return self

        return '%s:%s'%(self.prefix, getattr(inst, self.cname))

########NEW FILE########
__FILENAME__ = uiactions
""" ui actions """
import ptah
from ptah import config
from zope.interface import implementer, providedBy, Interface

ID_UIACTION = 'ptah:uiaction'


class IAction(Interface):
    """ marker interface for actions """


@implementer(IAction)
class Action(object):
    """ UI Action implementation """

    id = ''
    title = ''
    description = ''
    category = ''
    action = ''
    action_factory = None
    condition = None
    permission = None
    sort_weight = 1.0,
    data = None

    def __init__(self, id='', **kw):
        self.id = id
        self.__dict__.update(kw)

    def url(self, context, request, url=''):
        if request is None:
            return ''

        if self.action_factory is not None:
            return self.action_factory(context, request)

        if self.action.startswith('/'):
            return '%s%s'%(request.application_url, self.action)
        else:
            return '%s%s'%(url, self.action)

    def check(self, context, request):
        if request is None:
            return True

        if self.permission:
            if not ptah.check_permission(
                self.permission, context, request):
                return False

        if self.condition is not None:
            return self.condition(context, request)

        return True


def uiaction(context, id, title, description='',
             action='', condition=None, permission=None,
             category='', sort_weight = 1.0, **kw):
    """ Register ui action """

    kwargs = {'id': id,
              'title': title,
              'description': description,
              'category': category,
              'condition': condition,
              'permission': permission,
              'sort_weight': sort_weight,
              'data': kw}

    if callable(action):
        kwargs['action_factory'] = action
    else:
        kwargs['action'] = action

    ac = Action(**kwargs)

    info = config.DirectiveInfo()
    discr = (ID_UIACTION, id, context, category)
    intr = ptah.config.Introspectable(
        ID_UIACTION, discr, title, 'ptah-uiaction')
    intr['action'] = ac
    intr['codeinfo'] = info.codeinfo

    info.attach(
        config.Action(
            lambda cfg, id, category, context, ac: \
                cfg.registry.registerAdapter(\
                   ac, (context,), IAction, '%s-%s'%(category, id)),
            (id, category, context, ac,),
            discriminator = discr, introspectables = (intr,))
        )


def list_uiactions(content, request=None, registry=None, category=''):
    """ List ui actions for specific content """
    if request is not None:
        registry = request.registry
        url = request.resource_url(content)
    else:
        url = ''

    actions = []
    for name, action in registry.adapters.lookupAll((providedBy(content),), IAction):
        if (action.category == category) and action.check(content, request):
            actions.append(
                (action.sort_weight,
                 {'id': action.id,
                  'url': action.url(content, request, url),
                  'title': action.title,
                  'description': action.description,
                  'data': action.data}))

    return [ac for _w, ac in sorted(actions, key=lambda action: action[0])]

########NEW FILE########
__FILENAME__ = uri
""" uri resolver """
import uuid
from ptah import config

ID_RESOLVER = 'ptah:resolver'


def resolve(uri):
    """ Resolve uri, return resolved object.

    Uri contains two parts, `schema` and `uuid`. `schema` is used for
    resolver selection. `uuid` is resolver specific data. By default
    uuid is a uuid.uuid4 string.
    """
    if not uri:
        return

    try:
        schema, data = uri.split(':', 1)
    except ValueError:
        return None

    try:
        return config.get_cfg_storage(ID_RESOLVER)[schema](uri)
    except KeyError:
        pass

    return None


def extract_uri_schema(uri):
    """ Extract schema of given uri """
    if uri:
        try:
            schema, data = uri.split(':', 1)
            return schema
        except:
            pass

    return None


class resolver(object):
    """ Register resolver for given schema. `resolver` is decorator style
    registration.

        :param schema: uri schema

        Resolver interface :py:class:`ptah.interfaces.resolver`

        .. code-block:: python

          import ptah

          @ptah.resolver('custom-schema')
          def my_resolver(uri):
             ....

          # now its possible to resolver 'custom-schema:xxx' uri's
          ptah.resolve('custom-schema:xxx')
    """

    def __init__(self, schema, __depth=1):
        self.depth = __depth
        self.info = config.DirectiveInfo(__depth)
        self.discr = (ID_RESOLVER, schema)

        self.intr = config.Introspectable(
            ID_RESOLVER, self.discr, schema, 'ptah-uriresolver')
        self.intr['schema'] = schema
        self.intr['codeinfo'] = self.info.codeinfo

    def __call__(self, resolver, cfg=None):
        self.intr.title = resolver.__doc__
        self.intr['callable'] = resolver

        self.info.attach(
            config.Action(
                lambda cfg, schema, resolver:
                    cfg.get_cfg_storage(ID_RESOLVER)\
                        .update({schema: resolver}),
                (self.intr['schema'], resolver),
                discriminator=self.discr, introspectables=(self.intr,)),
            cfg, self.depth)

        return resolver

    @classmethod
    def register(cls, schema, resolver):
        """ Register resolver for given schema

        :param schema: uri schema
        :param resolver: Callable object that accept one parameter.

        Example:

        .. code-block:: python

          import ptah

          def my_resolver(uri):
             ....

          ptah.resolver.register('custom-schema', my_resolver)

          # now its possible to resolver 'custom-schema:xxx' uri's
          ptah.resolve('custom-schema:xxx')

        """
        cls(schema, 2)(resolver)

    @classmethod
    def pyramid(cls, cfg, schema, resolver):
        """ pyramid configurator directive `ptah_uri_resolver`.

        .. code-block:: python

            config = Configurator()
            config.include('ptah')

            def my_resolver(uri):
                ....

            config.ptah_uri_resolver('custom-schema', my_resolver)
        """
        cls(schema, 3)(resolver, cfg)


class UriFactory(object):
    """ Uri Generator

    .. code-block:: python

      uri = UriFactory('cms-content')

      uri()
      'cms-content:f73f3266fa15438e94cca3621a3f2dbc'

    """
    def __init__(self, schema):
        self.schema = schema

    def __call__(self):
        """ Generate new uri using supplied schema """
        return '%s:%s' % (self.schema, uuid.uuid4().hex)

########NEW FILE########
__FILENAME__ = util
import ptah
import threading
from datetime import datetime
from pyramid.interfaces import INewRequest

_days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
_months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
           'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

def dthandler(obj):
    if isinstance(obj, datetime):
        now = obj.timetuple()
        return '%s, %02d %s %04d %02d:%02d:%02d -0000' % (
            _days[now[6]], now[2],
            _months[now[1] - 1], now[0], now[3], now[4], now[5])

kwargs = {'default': dthandler, 'separators': (',', ':')}

# Faster
try:
    import simplejson as jsonmod
except ImportError: #pragma: no cover
    # Slowest
    import json as jsonmod

class json(object):

    @staticmethod
    def dumps(o, **kw):
        kw.update(kwargs)
        return jsonmod.dumps(o, **kw)

    @staticmethod
    def loads(s, **kw):
        return jsonmod.loads(s, **kw)


class ThreadLocalManager(threading.local):

    def __init__(self):
        self.data = {}

    def get(self, key, default=None):
        return self.data.get(key, default)

    def set(self, key, value):
        self.data[key] = value

    def clear(self):
        self.data = {}

tldata = ThreadLocalManager()


@ptah.subscriber(INewRequest)
def resetThreadLocalData(ev):
    tldata.clear()


class Pagination(object):
    """ simple pagination """

    def __init__(self, page_size, left_neighbours=3, right_neighbours=3):
        self.page_size = page_size
        self.left_neighbours = left_neighbours
        self.right_neighbours = right_neighbours

    def offset(self, current):
        return (current - 1) * self.page_size, self.page_size

    def __call__(self, total, current):
        if not current:
            raise ValueError(current)

        size = int(round(total / float(self.page_size) + 0.4))

        pages = []

        first = 1
        last = size

        prevIdx = current - self.left_neighbours
        nextIdx = current + 1

        if first < current:
            pages.append(first)
        if first + 1 < prevIdx:
            pages.append(None)
        for i in range(prevIdx, prevIdx + self.left_neighbours):
            if first < i:
                pages.append(i)

        pages.append(current)

        for i in range(nextIdx, nextIdx + self.right_neighbours):
            if i < last:
                pages.append(i)
        if nextIdx + self.right_neighbours < last:
            pages.append(None)
        if current < last:
            pages.append(last)

        # prev/next idx
        prevLink = None if current <= 1 else current - 1
        nextLink = None if current >= size else current + 1

        return pages, prevLink, nextLink

########NEW FILE########
__FILENAME__ = view
""" base view class with access to various api's """
import logging
from pyramid.decorator import reify

import ptah

log = logging.getLogger('ptah.view')


class View(object):
    """ Base view """

    __name__ = ''
    __parent__ = None

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.__parent__ = context

    @reify
    def application_url(self):
        url = self.request.application_url
        if url.endswith('/'):
            url = url[:-1]
        return url

    def update(self):
        return {}

    def __call__(self):
        result = self.update()
        if result is None:
            result = {}

        return result


class MasterLayout(View):

    @reify
    def site_title(self):
        PTAH = ptah.get_settings(ptah.CFG_ID_PTAH, self.request.registry)
        return PTAH['site_title']

    @reify
    def user(self):
        userid = ptah.auth_service.get_userid()
        return ptah.resolve(userid)

    @reify
    def manage_url(self):
        userid = ptah.auth_service.get_userid()
        if ptah.manage.check_access(userid, self.request):
            return ptah.manage.get_manage_url(self.request)

    @reify
    def actions(self):
        return []

########NEW FILE########
