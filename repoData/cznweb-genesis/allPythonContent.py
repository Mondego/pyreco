__FILENAME__ = api
from genesis.com import Interface

class ICategoryProvider (Interface):
    """
    Base interface for plugins that provide a sidebar entry

    See :class:`genesis.api.CategoryPlugin`
    """
    def get_ui(self):
        """
        Should return :class:`genesis.ui.Layout` or :class:`genesis.ui.Element`
        representing plugin's UI state
        """


class IModuleConfig (Interface):
    """
    Base interface for module configurations.

    See :class:`genesis.api.ModuleConfig`
    """

class IEventDispatcher (Interface):
    """
    Base interface for :class:`Plugin` which may dispatch UI Events_.

    See :class:`genesis.api.EventProcessor`
    """

    def match_event(self, event):
        pass

    def event(self, event, *params, **kwparams):
        pass


class IXSLTFunctionProvider (Interface):
    """
    Interface for classes which provide additional XSLT functions for
    use in Widgets_ templates.
    """

    def get_funcs(self):
        """
        Gets all XSLT functions provided. Functions are subject to be invoked
        by ``lxml``.

        :returns: dict(str:func)
        """

########NEW FILE########
__FILENAME__ = components
from genesis.com import *
from genesis.utils import *


class IComponent (Interface):
    """
    Base interface for background components.

    See :class:`Component`.
    """
    def run(self):
        pass


class Component (Plugin, BackgroundWorker):
    """
    Base class for a custom Component. Components are thread-safe objects (optionally
    containing a background thread) that are persisted for all the run time.

    - ``name`` - `str`, unique component ID
    """
    implements(IComponent)

    name = 'unknown'
    proxy = None
    abstract = True

    def __init__(self):
        BackgroundWorker.__init__(self)

    @classmethod
    def get(cls):
        """
        Convinience method, will return the component.
        Same as ``ComponentManager.get().find(name)``.
        """
        return ComponentManager.get().find(cls.name)

    def start(self):
        """
        Starts the component. For internal use only.
        """
        self.on_starting()
        BackgroundWorker.start(self)

    def stop(self):
        """
        Stops the component. For internal use only.
        """
        self.on_stopping()
        self.kill()
        self.on_stopped()

    def run(self):
        """
        Derived classes should put here the body of background thread (if any).
        """

    def on_starting(self):
        """
        Called when component is started. Use this instead of ``__init__``.
        """

    def on_stopping(self):
        """
        Called when component is about to be stopped. Thread is still running.
        """

    def on_stopped(self):
        """
        Called when component's thread has been stopped.
        """

    def unload(self):
        self.stop()


class ComponentManager (Plugin):
    """
    A general manager for all :class:`Component` classes.
    """
    instance = None

    @staticmethod
    def create(app):
        """
        Initializes the ComponentManager
        """
        ComponentManager.instance = ComponentManager(app)

    @staticmethod
    def get():
        """
        :returns: the ComponentManager instance
        """
        return ComponentManager.instance

    def __init__(self):
        self.components = []
        self.rescan()

    def stop(self):
        """
        Shutdowns all the components
        """
        for c in self.components:
            c.stop()

    def find(self, name):
        """
        Finds a :class:`Component` by ID.
        """
        for c in self.components:
            if c.name == name:
                return c.proxy

    def rescan(self):
        """
        Finds and starts any newly-found Components
        """
        for c in self.app.grab_plugins(IComponent):
            if not c in self.components:
                self.log.debug('Registered component: ' + c.name)
                c.proxy = ClassProxy(c)
                c.start()
                self.components.append(c)

########NEW FILE########
__FILENAME__ = confmanager
from genesis.com import Interface, implements
from genesis.api import *
from genesis.apis import API
from genesis import apis

import traceback


class ConfManager (Component):
    """
    A :class:`Component`, proxyfies access to system's config files.
    Use this when possible instead of ``open``. You'll have to create an
    :class:`IConfigurable` first, then use ``load``, ``save``, and ``commit``
    functions.
    """
    name = 'confmanager'

    configurables = {}
    hooks = []

    def load(self, id, path):
        """
        Reads a config file.

        :param  id:     :class:`IConfigurable` ID.
        :type   id:     str
        :param  path:   file location
        :type   path:   str
        :rtype:         str
        :returns:       file contents
        """
        cfg = self.get_configurable(id)
        for c in self.hooks:
            c.pre_load(cfg, path)

        with open(path, 'r') as f:
            data = f.read()

        for c in self.hooks:
            data = c.post_load(cfg, path, data)

        return data

    def save(self, id, path, data):
        """
        Writes a config file.

        :param  id:     :class:`IConfigurable` ID.
        :type   id:     str
        :param  path:   file location
        :type   path:   str
        :param  data:   file contents
        :type   data:   str
        """
        cfg = self.get_configurable(id)

        for c in self.hooks:
            data = c.pre_save(cfg, path, data)
            if data is None:
                return

        with open(path, 'w') as f:
            f.write(data)

        for c in self.hooks:
            c.post_save(cfg, path)

        return data

    def commit(self, id):
        """
        Notifies ConfManager that you have finished writing Configurable's files.
        For example, at this point Recovery plugin will make a backup.

        :param  id:     :class:`IConfigurable` ID.
        :type   id:     str
        """
        cfg = self.get_configurable(id)
        for c in self.hooks:
            c.finished(cfg)

    def get_configurable(self, id):
        """
        Finds a Configurable.

        :param  id:     :class:`IConfigurable` ID.
        :type   id:     str
        :rtype:         :class:`IConfigurable`
        """
        for c in self.configurables.values():
            if c.id == id:
                return c

    def rescan(self):
        """
        Registers any newly found Configurables
        """
        self.configurables = {}
        self.hooks = []
        try:
            for cfg in self.app.grab_plugins(IConfigurable):
                self.log.debug('Registered configurable: ' + cfg.id + ' ' + str(cfg))
                self.configurables[cfg.id] = cfg
        except Exception, e:
            self.app.log.error('Configurables loading failed: ' + str(e) + traceback.format_exc())
        for h in self.app.grab_plugins(IConfMgrHook):
            self.app.log.debug('Registered configuration hook: ' + str(h))
            self.hooks.append(h)

    def on_starting(self):
        self.rescan()

    def on_stopping(self):
        pass

    def on_stopped(self):
        pass


class IConfMgrHook (Interface):
    """
    Base interface for ConfManager hooks that react to events and process
    the config files.
    """
    def pre_load(self, cfg, path):
        """
        Called before reading a file.

        :param  cfg:    Configurable
        :type   cfg:    :class:`IConfigurable`
        :param  path:   file location
        :type   path:   str
        """

    def post_load(self, cfg, path, data):
        """
        Called after reading a file. Implementation has to process the file and
        return new content

        :param  cfg:    Configurable
        :type   cfg:    :class:`IConfigurable`
        :param  path:   file location
        :type   path:   str
        :param  data:   file contents
        :type   data:   str
        :rtype:         str
        :returns:       modified contents
        """

    def pre_save(self, cfg, path, data):
        """
        Called before saving a file. Implementation has to process the file and
        return new content.

        :param  cfg:    Configurable
        :type   cfg:    :class:`IConfigurable`
        :param  path:   file location
        :type   path:   str
        :param  data:   file contents
        :type   data:   str
        :rtype:         str
        :returns:       modified contents
        """

    def post_save(self, cfg, path):
        """
        Called after saving a file.

        :param  cfg:    Configurable
        :type   cfg:    :class:`IConfigurable`
        :param  path:   file location
        :type   path:   str
        """

    def finished(self, cfg):
        """
        Called when a ``commit`` is performed. Good time to make backups/save data/etc.

        :param  cfg:    Configurable
        :type   cfg:    :class:`IConfigurable`
        """


class ConfMgrHook (Plugin):
    """
    Handy base class in case you don't want to reimplement all hook methods.
    """
    implements(IConfMgrHook)
    abstract = True

    def pre_load(self, cfg, path):
        pass

    def post_load(self, cfg, path, data):
        return data

    def pre_save(self, cfg, path, data):
        return data

    def post_save(self, cfg, path):
        pass

    def finished(self, cfg):
        pass


class IConfigurable (Interface):
    """
    Interface for Configurables. Configurable is an entity (software or
    system aspect) which has a set of config files.

    - ``name`` - `str`, a human-readable name.
    - ``id`` - `str`, unique ID.
    """
    name = None
    id = None

    def list_files(self):
        """
        Implementation should return list of config file paths - file names or
        wildcards (globs) which will be expanded by :func:`glob.glob`.
        """

########NEW FILE########
__FILENAME__ = helpers
import inspect
import traceback

from genesis.com import *
from genesis.api import *
from genesis.ui import *
from genesis import apis


def event(event_name):
    """ Decorator function to register event handlers

    >>> class a(object):
    ...     @event('some/event')
    ...     def test1 (self):
    ...         pass
    ...
    ...     @event('other/event')
    ...     def test2 (self):
    ...         pass
    >>> a._events
    {'other/event': 'test2', 'some/event': 'test1'}
    >>>
    """
    # Get parent exection frame
    frame = inspect.stack()[1][0]
    # Get locals from it
    locals = frame.f_locals

    if ((locals is frame.f_globals) or
        ('__module__' not in locals)):
        raise TypeError('@event() can only be used in class definition')

    loc_events = locals.setdefault('_events',{})

    def event_decorator(func):
        loc_events[event_name] = func.__name__
        return func
    #def event_decorator

    return event_decorator
#def event


class EventProcessor(object):
    """
    A base class for plugins suitable for handling UI Events_.
    You will need to decorate handler methods with :func:`event`.
    """
    implements(IEventDispatcher)


    def _get_event_handler(self, event):
        """
        >>> class Test(EventProcessor):
        ...     @event('test')
        ...     def test(self):
        ...         pass
        ...
        >>> t = Test()
        >>> t._get_event_handler('test')
        'test'
        >>>
        """
        for cls in self.__class__.mro():
            if '_events' in dir(cls):
                if event in cls._events:
                    return cls._events[event]
        return None

    def match_event(self, event):
        """ Returns True if class (or any parent class) could handle event

        >>> class Test(EventProcessor):
        ...     @event('test')
        ...     def test(self):
        ...         pass
        ...
        >>> t = Test()
        >>> t._get_event_handler('test')
        'test'
        >>> t.match_event('test')
        True
        >>> t.match_event('test2')
        False
        >>>
        """
        if self._get_event_handler(event) is not None:
            return True
        return False

    def event(self, event, *params, **kwparams):
        """
        Calls a handler method suitable for given event.

        >>> class Test(EventProcessor):
        ...     @event('test')
        ...     def test(self, *p, **kw):
        ...         print(kw)
        ...
        >>> t = Test()
        >>> t.event('test', value='test')
        {'value': 'test'}
        >>>
        """
        handler = self._get_event_handler(event)
        if handler is None:
            return
        try:
            handler = self.__getattribute__(handler)
        except AttributeError:
            return

        return handler(event, *params, **kwparams)


class SessionPlugin(Plugin):
    """
    A base class for plugins attached to the current user's session.

    Instance variables starting with '_' will be automatically [re]stored
    from/into the session.

    """

    session_proxy = None

    def __init__(self):
        if self.session_proxy is None:
            self.session_proxy = self.app.session.proxy(self.__class__.__name__)

        if self.session_proxy.get('sp_estabilished', None) is None:
            self.session_proxy['sp_estabilished'] = 'yes'
            try:
                self.on_session_start()
            except Exception:
                traceback.print_exc()
                raise

    def __getattr__(self, name):
        # TODO: use regexps
        if name[0] == '_' and not name[1] == '_':
            return self.session_proxy.get(name, None)
        else:
            raise AttributeError("'%s' object has no attribute '%s'"%
                                  (self.__class__.__name__, name))

    def __setattr__(self, name, value):
        # TODO: use regexps
        if name[0] == '_' and not name[1] == '_':
            self.session_proxy[name] = value
        else:
            self.__dict__[name] = value

    def on_session_start(self):
        """
        Called when a session is estabilished for new user or a new plugin
        is attached to the session for the first time.
        """


class CategoryPlugin(SessionPlugin, EventProcessor):
    """
    A base class for plugins providing sidebar entry

    - ``text`` - `str`, sidebar entry text
    - ``iconfont`` - `str`, sidebar iconfont class
    - ``folder`` - `str`, sidebar section name (lowercase)
    """
    abstract = True

    implements(ICategoryProvider)

    text = 'Caption'
    iconfont = 'gen-question'
    folder = 'other'

    def on_init(self):
        """
        Called when a web request has arrived and this plugin is active (visible).
        """

    def get_counter(self):
        """
        May return short string to be displayed in 'bubble' right to the sidebar
        entry.

        :returns: None or str
        """

    def get_config(self):
        """
        Returns a most preferred ModuleConfig for this class.

        :returns:   :class:`ModuleConfig` or None
        """
        try:
            return self.app.get_config(self)
        except:
            return None

    def put_message(self, cls, msg):
        """
        Pushes a visual message to the message queue.
        All messages will be displayed on the next webpage update user will
        receive.

        :param  cls:    one of 'info', 'warn', 'err'
        :type   cls:    str
        :params msg:    message text
        """
        if not self.app.session.has_key('messages'):
            self.app.session['messages'] = []
        self.app.session['messages'].append((cls, msg))

    def put_statusmsg(self, msg):
        """
        Sets a blocking status message to appear while an operation completes.
        """
        if not self.app.session.has_key('statusmsg'):
            self.app.session['statusmsg'] = []
        self.app.session['statusmsg'].append((self.text, msg))

    def clr_statusmsg(self):
        """
        Clear the currently shown status window
        """
        if not self.app.session.has_key('statusmsg'):
            self.app.session['statusmsg'] = []
        self.app.session['statusmsg'].append((self.text, False))

    def redirapp(self, service, port, ssl=False):
        if self.app.get_backend(apis.services.IServiceManager).get_status(service) == 'running':
            if ssl:
                return UI.JS(code='window.location.replace("/embapp/'+str(port)+'/ssl")')
            else:
                return UI.JS(code='window.location.replace("/embapp/'+str(port)+'")')
        else:
            return UI.DialogBox(UI.Label(text='The service %s is not '
                'running. Please start the service with the Status button '
                'before continuing.' % service), hidecancel=True)

    def update_services(self):
        apis.networkcontrol(self.app).port_changed(self.plugin_info)

    def send_order(self, id, *params, **kwparams):
        d = filter(lambda x: x.id == id,
            self.app.grab_plugins(apis.orders.IListener))
        if d:
            d[0].order(*params)
            return UI.JS(code="Genesis.selectCategory('%s')"%d[0].cat)
        else:
            self.put_message('err', 'No listener found for %s. '
                'Please make sure the necessary plugin is installed.' % id)

    def can_order(self, id):
        d = filter(lambda x: x.id == id,
            self.app.grab_plugins(apis.orders.IListener))
        return d != []


class ModuleConfig(Plugin):
    """
    Base class for simple "configs" for different platforms for the plugins.

    - ``target`` - `type`, :class:`genesis.com.Plugin` class for which this config
      is targeted.
    - ``labels`` - `dict(str:str)` - text labels for visual editing of each property.

    All other properties are considered ModuleConfig parameters - they are shown
    in the UI and saved to config files.
    """
    abstract = True
    implements(IModuleConfig)

    target = None
    labels = {}

    def overlay_config(self):
        section = 'cfg_' + self.target.__name__
        for k in self.__class__.__dict__:
            if not k in ['platform', 'plugin', 'labels']:
                if self.app.config.has_option(section, k):
                    setattr(self, k, eval(self.app.config.get(section, k)))

    def save(self):
        section = 'cfg_' + self.target.__name__
        for k in self.__class__.__dict__:
            if not k in ['platform', 'plugin', 'labels'] and not k.startswith('_'):
                if getattr(self, k) != getattr(self.__class__, k):
                    self.app.config.set(section, k, repr(getattr(self, k)))
                else:
                    self.app.config.remove_option(section, k)
        self.app.config.save()

    def get_ui_edit(self):
        t = UI.Container()
        for k in self.__class__.__dict__:
            if not k in ['platform', 'plugin', 'labels'] and not k.startswith('_'):
                val = getattr(self, k)
                lbl = k
                if k in self.labels:
                    lbl = self.labels[k]
                if type(val) is str and hasattr(self, k+'_opts'):
                    t.append(UI.Formline(
                        UI.Select(*[UI.SelectOption(text=x, value=x, selected=x==val) for x in getattr(self, k+'_opts')], 
                            id=k, name=k),
                        text=lbl
                    ))
                elif type(val) is bool:
                    t.append(UI.Formline(
                        UI.CheckBox(name=k, checked=val),
                        text=lbl
                    ))
                elif type(val) is str:
                    t.append(UI.Formline(
                        UI.TextInput(name=k, value=val),
                        text=lbl,
                    ))
        return UI.DialogBox(t, id='dlgEditModuleConfig')

    def apply_vars(self, vars):
        for k in vars:
            if not k in ['action'] and not k.startswith('_'):
                nval = vars.getvalue(k, None)
                oval = getattr(self, k)
                if type(oval) is str:
                    setattr(self, k, nval)
                elif type(oval) is bool:
                    setattr(self, k, nval=='1')

########NEW FILE########
__FILENAME__ = meters
from genesis.com import *

class IMeter (Interface):
    pass


class BaseMeter (Plugin):
    """
    Meters are determinable values (int, float, bool) representing system status
    (sysload, memory usage, service status, etc.) which are used and exported
    over HTTP by ``health`` builtin plugin.

    - ``name`` - `str`, meter name
    - ``text`` - `str`, text shown on the specific meter widget
    - ``category`` - `str`, meter category name
    - ``type`` - `str`, one of 'binary', 'linear', 'decimal'
    - ``transform`` - `str`, value->text transform applied to meter. One of
      'float', 'fsize', 'percent', 'fsize_percent', 'yesno', 'onoff', 'running'
    """
    implements(IMeter)
    abstract = True
    multi_instance = True

    name = 'Unknown'
    text = ''
    category = ''
    type = None
    transform = None

    def prepare(self, variant=None):
        self = self.__class__(self.app)
        self.variant = variant
        self.init()
        return self

    def init(self):
        """
        Implementation may perform preparations based on ``self.variant`` here.
        """

    def get_variants(self):
        """
        Implementation should return list of meter 'variants' here.
        """
        return ['None']

    def format_value(self):
        return None


class BinaryMeter (BaseMeter):
    """
    Base class for binary value meters
    """
    abstract = True
    type = 'binary'

    def get_value(self):
        """
        Implementation should return binary meter value
        """

    def format_value(self):
        BaseMeter.format_value(self)
        return { 'value': self.get_value() }


class DecimalMeter (BaseMeter):
    """
    Base class for decimal/float value meters
    """
    abstract = True
    type = 'decimal'

    def get_value(self):
        """
        Implementation should return decimal meter value
        """

    def format_value(self):
        BaseMeter.format_value(self)
        return { 'value': self.get_value() }


class LinearMeter (BaseMeter):
    """
    Base class for decimal/float value meters with min/max range
    """
    abstract = True
    type = 'linear'

    def get_value(self):
        """
        Implementation should return decimal meter value
        """
        return 0

    def get_max(self):
        """
        Implementation should return decimal meter range maximum
        """
        return 0

    def get_min(self):
        """
        Implementation should return decimal meter range minimum
        """
        return 0

    def format_value(self):
        BaseMeter.format_value(self)
        return {
            'value': self.get_value(),
            'max': self.get_max(),
            'min': self.get_min(),
        }

########NEW FILE########
__FILENAME__ = urlhandler
import re
import cgi
import inspect

from genesis.com import Interface, implements


def url(uri):
    """ Decorator function to register URL handlers
    """
    # Get parent exection frame
    frame = inspect.stack()[1][0]
    # Get locals from it
    locals = frame.f_locals

    if ((locals is frame.f_globals) or
        ('__module__' not in locals)):
        raise TypeError('@url() can only be used in class definition')

    loc_urls = locals.setdefault('_urls',{})

    def url_decorator(func):
        loc_urls[re.compile(uri)] = func.__name__
        return func
    #def url_decorator

    return url_decorator
#def url


class IURLHandler(Interface):
    """
    Base interface for classes that can handle HTTP requests
    """

    def match_url(self, req):
        """
        Determines if the class can handle given request.

        :param  req:    WSGI request environment
        :type   req:    dict
        :rtype:         bool
        """

    def url_handler(self, req, sr):
        """
        Should handle given request.

        :param  req:    WSGI request environment
        :type   req:    dict
        :param  sr:     start_response callback for setting HTTP code and headers
        :type   sr:     func(code, headers)
        :returns:       raw response body
        :rtype:         str
        """


class URLHandler(object):
    """
    Base class that handles HTTP requests based on its methods decorated with
    :func:url
    """
    implements(IURLHandler)

    def _get_url_handler(self, uri):
        for cls in self.__class__.mro():
            if '_urls' in dir(cls):
                for uri_re in cls._urls.keys():
                    if uri_re.match(uri):
                        return cls._urls[uri_re]
        return None

    def match_url(self, req):
        """ Returns True if class (or any parent class) could handle URL
        """
        if self._get_url_handler(req.get('PATH_INFO')) is not None:
            return True
        return False

    def url_handler(self, req, start_response):
        handler = self._get_url_handler(req.get('PATH_INFO'))
        if handler is None:
            return
        try:
            handler = self.__getattribute__(handler)
        except AttributeError:
            return

        return handler(req, start_response)


def get_environment_vars(req):
    """
    Extracts POST data from WSGI environment

    :rtype: :class:`cgi.FieldStorage`
    """
    res = None
    req.setdefault('QUERY_STRING', '')
    if req['REQUEST_METHOD'].upper() == 'POST':
        ctype = req.get('CONTENT_TYPE', 'application/x-www-form-urlencoded')
        if ctype.startswith('application/x-www-form-urlencoded') \
           or ctype.startswith('multipart/form-data'):
            res = cgi.FieldStorage(fp=req['wsgi.input'],
                                   environ=req,
                                   keep_blank_values=1)
    else:
        res = cgi.FieldStorage(environ=req, keep_blank_values=1)

    return res

########NEW FILE########
__FILENAME__ = apis
import sys


class MetaAPI(type):
    def __new__ (mcs, name, bases, d):
        new_class = type.__new__(mcs, name, bases, d)
        setattr(sys.modules[__name__], name.lower(), new_class)
        return new_class


class API(object):
    __metaclass__ = MetaAPI

########NEW FILE########
__FILENAME__ = com
"""
Base plugin-interface architecture for Genesis
"""

__all__ = ['Interface', 'implements', 'Plugin', 'PluginManager']

import inspect
import traceback

from genesis.utils import PrioList


class Interface:
    """ Base abstract class for all interfaces

    Can be used as callable (decorator)
    to check if Plugin implements all methods
    (internal use only)
    """

    def __call__(self, cls):
        # Check that target class supports all our interface methods
        cls_methods = [m for m in dir(cls) if not m.startswith('_')]

        # Check local interface methods
        methods = [m for m in dir(self.__class__) if not m.startswith('_')]
        # Filter out property methods
        methods = [m for m in methods if m not in dir(property)]

        for method in methods:
            if method not in cls_methods:
                raise AttributeError(
                      "%s implementing interface %s, does not have '%s' method"%
                      (cls, self.__class__, method))


def implements (*interfaces):
    """
    Used to note that a :class:`Plugin` implements an :class:`Interface`.
    Example:

        class IFoo (Interface):
            pass

        class IBaz (Interface):
            pass

        class FooBazImp (Plugin):
            implements (IFoo, IBaz)
    """

    # Get parent exection frame
    frame = inspect.stack()[1][0]
    # Get locals from it
    locals = frame.f_locals

    if ((locals is frame.f_globals) or
        ('__module__' not in locals)):
        raise TypeError('implements() can only be used in class definition')

    if '_implements' in locals:
        raise TypeError('implements() could be used only once')

    locals.setdefault('_implements',[]).extend(interfaces)
    # TODO: trac also all base interfaces (if needed)


class PluginManager (object):
    """ Holds all registered classes, instances and implementations
    You should have one class instantiated from both PluginManager and Plugin
    to trigger plugins magick
    """
    # Class-wide properties
    __classes = []
    __plugins = {}
    __tracking = False
    __tracker = None

    def __init__(self):
        self.__instances = {}

    @staticmethod
    def class_register (cls):
        """
        Registers a new class

        :param  cls:    class
        :type   cls:    type
        """
        PluginManager.__classes.append(cls)
        if PluginManager.__tracking:
            PluginManager.__tracker.append(cls)

    @staticmethod
    def class_unregister (cls):
        """
        Unregisters a class

        :param  cls:    class
        :type   cls:    type
        """
        PluginManager.__classes.remove(cls)
        for lst in PluginManager.__plugins.values():
            if cls in lst:
                lst.remove(cls)

    @staticmethod
    def class_list ():
        """
        Lists all registered classes

        :returns:       list(:class:`type`)
        """
        return PluginManager.__classes

    @staticmethod
    def plugin_list ():
        return PluginManager.__plugins

    @staticmethod
    def plugin_register (iface, cls):
        """
        Registers a :class:`Plugin` for implementing an :class:`Interface`

        :param  iface:  interface
        :type   iface:  type
        :param  cls:    plugin
        :type   cls:    :class:`Plugin`
        """
        lst = PluginManager.__plugins.setdefault(iface,PrioList())
        for item in lst:
            if str(item) == str(cls):
                return
        lst.append(cls)

    @staticmethod
    def plugin_get (iface):
        """
        Returns plugins that implement given :class:`Interface`

        :param  iface:  interface
        :type   iface:  type
        """
        return PluginManager.__plugins.get(iface, [])

    @staticmethod
    def start_tracking():
        """
        Starts internal registration tracker
        """
        PluginManager.__tracking = True
        PluginManager.__tracker = []

    @staticmethod
    def stop_tracking():
        """
        Stops internal registration tracker and returns all classes
        registered since calling ``start_tracking``
        """
        PluginManager.__tracking = False
        return PluginManager.__tracker

    def instance_get(self, cls, instantiate=False):
        """
        Gets a saved instance for the :class:`Plugin` subclass

        :param  instantiate:  instantiate plugin if it wasn't instantiate before
        :type   instantiate:  bool
        """
        if not self.plugin_enabled(cls):
            return None
        inst = self.__instances.get(cls)
        if instantiate == True and inst is None:
            if cls not in PluginManager.__classes:
                raise Exception('Class "%s" is not registered'% cls.__name__)
            try:
                inst = cls(self)
            except TypeError, e:
                print traceback.format_exc()
                raise Exception('Unable instantiate plugin %r (%s)'%(cls, e))

        return inst

    def instance_set(self, cls, inst):
        self.__instances[cls] = inst

    def instance_list(self):
        return self.__instances

    def plugin_enabled(self, cls):
        """
        Called to check if :class:`Plugin` is eligible for running on this system

        :returns: bool
        """
        return True

    def plugin_activated(self, plugin):
        """
        Called when a :class:`Plugin` is successfully instantiated
        """


class MetaPlugin (type):
    """
    Metaclass for Plugin
    """

    def __new__ (cls, name, bases, d):
        """ Create new class """

        # Create new class
        new_class = type.__new__(cls, name, bases, d)

        # If we creating base class, do nothing
        if name == 'Plugin':
            return new_class

        # Override __init__ for Plugins, for instantiation process
        if True not in [issubclass(x, PluginManager) for x in bases]:
            # Allow Plugins to have own __init__ without parameters
            init = d.get('__init__')
            if not init:
                # Because we're replacing the initializer, we need to make sure
                # that any inherited initializers are also called.
                for init in [b.__init__._original for b in new_class.mro()
                             if issubclass(b, Plugin)
                             and '__init__' in b.__dict__]:
                    break
            def maybe_init(self, plugin_manager, init=init, cls=new_class):
                if plugin_manager.instance_get(cls) is None:
                    # Plugin is just created
                    if init:
                        init(self)
                    if not self.multi_instance:
                        plugin_manager.instance_set(cls, self)
            maybe_init._original = init
            new_class.__init__ = maybe_init

        # If this is abstract class, do no record it
        if d.get('abstract'):
            return new_class

        # Save created class for future reference
        PluginManager.class_register(new_class)

        # Collect all interfaces that this class implements
        interfaces = d.get('_implements',[])
        for base in [base for base in new_class.mro()[1:] if hasattr(base, '_implements')]:
            interfaces.extend(base._implements)

        # Delete duplicates, in case we inherit same Intarfaces
        # or we need to override priority
        _ints = []
        _interfaces = []
        for interface in interfaces:
            _int = interface
            if isinstance(interface, tuple):
                _int = interface[0]

            if _int not in _ints:
                _ints.append(_int)
                _interfaces.append(interface)

        interfaces = _interfaces

        # Check that class supports all needed methods
        for interface in interfaces:
            _int = interface
            if isinstance(interface, tuple):
                _int = interface[0]
            _int()(new_class)

        # Register plugin
        for interface in interfaces:
            if isinstance(interface, tuple):
                PluginManager.plugin_register(interface[0], (new_class, interface[1]))
            else:
                PluginManager.plugin_register(interface, new_class)

        return new_class

#class MetaPlugin


class Plugin (object):
    """
    Base class for all plugins

    - ``multi_instance`` - `bool`, if True, plugin will be not treated as a singleton
    - ``abstract`` - `bool`, abstract plugins are not registered in :class:`PluginManager`
    - ``platform`` - `list(str)`, platforms where the Plugin can be run
    - ``plugin_id`` - `str`, autoset to lowercase class name
    """

    __metaclass__ = MetaPlugin

    multi_instance = False

    platform = ['any']


    def __new__(cls, *args, **kwargs):
        """ Returns a class instance,
        If it already instantiated, return it
        otherwise return new instance
        """
        if issubclass(cls, PluginManager):
            # If we also a PluginManager, just create and return
            self = super(Plugin, cls).__new__(cls)
            self.plugin_manager = self
            return self

        # Normal case when we are standalone plugin
        self = None
        plugin_manager = args[0]
        if not cls.multi_instance:
            self = plugin_manager.instance_get(cls)

        if self is None:
            self = super(Plugin, cls).__new__(cls)
            self.plugin_manager = plugin_manager
            self.plugin_id = cls.__name__.lower()
            from genesis.plugmgr import PluginLoader
            pl, mod = PluginLoader.list_plugins(), cls.__module__.split('.')[0]
            self.plugin_info = pl[mod] if pl.has_key(mod) else None
            # Allow PluginManager implementation to update Plugin
            plugin_manager.plugin_activated(self)

        return self

    def unload(self):
        """
        Called when plugin class is being unloaded by
        :class:`genesis.plugmgr.PluginLoader`
        """

########NEW FILE########
__FILENAME__ = config
"""
Tools for manipulating Genesis configuration files
"""

__all__ = ['Config', 'ConfigProxy']

from ConfigParser import ConfigParser
import os

from genesis.utils import detect_platform, detect_architecture


class Config(ConfigParser):
    """
    A wrapper around ConfigParser
    """
    internal = {}
    filename = ''
    proxies = {}

    def __init__(self):
        ConfigParser.__init__(self)
        self.set('platform', detect_platform()) # TODO: move this out
        arch, board = detect_architecture()
        self.set('arch', arch)
        self.set('board', board)

    def load(self, fn):
        """
        Loads configuration data from the specified file
        :param  fn:     Config file path
        :type   fn:     str
        """
        self.filename = fn
        self.read(fn)

    def save(self):
        """
        Saves data to the last loaded file
        """
        with open(self.filename, 'w') as f:
            self.write(f)

    def get_proxy(self, user):
        """
        :param  user: User
        :type   user: str
        :returns:   :class:`ConfigProxy` for the specified :param:user
        """
        if not user in self.proxies:
            self.proxies[user] = ConfigProxy(self, user)
        return self.proxies[user]

    def get(self, section, val=None, default=None):
        """
        Gets a configuration parameter
        :param  section:    Config file section
        :type   section:    str
        :param  val:        Value name
        :type   val:        str
        :param  section:    Default value
        :type   section:    str
        :returns:           value or default value if value was not found
        """
        if val is None:
            return self.internal[section]
        else:
            try:
                return ConfigParser.get(self, section, val)
            except:
                if default is not None:
                    return default
                raise

    def set(self, section, val, value=None):
        """
        Sets a configuration parameter
        :param  section:    Config file section
        :type   section:    str
        :param  val:        Value name
        :type   val:        str
        :param  value:      Value
        :type   value:      str
        """
        if value is None:
            self.internal[section] = val
        else:
            if not self.has_section(section):
                self.add_section(section)
            ConfigParser.set(self, section, val, value)

    def has_option(self, section, name):
        """
        Checks if an parameter is present in the given section
        :param  section:    Config file section
        :type   section:    str
        :param  name:        Value name
        :type   name:        str
        :returns:           bool
        """
        try:
            return ConfigParser.has_option(self, section, name)
        except:
            return False


class ConfigProxy:
    """
    A proxy class that directs all writes into user's personal config file
    while reading from both personal and common configs.

    - *cfg* - :class:`Config` common for all users,
    - *user* - user name
    """

    def __init__(self, cfg, user):
        self.base = cfg
        self.user = user
        self.filename = None
        if user is None:
            return
        self.cfg = Config()
        path = os.path.split(self.base.filename)[0] + '/users/%s.conf'%user
        if not os.path.exists(path):
            open(path, 'w').close()
        self.filename = path
        self.cfg.load(path)

        # Proxy methods
        self.save = self.cfg.save
        self.add_section = self.cfg.add_section
        self.has_section = self.cfg.has_section
        self.remove_section = self.cfg.remove_section

    def get(self, section, val=None, default=None):
        """
        Gets a configuration parameter
        :param  section:    Config file section
        :type   section:    str
        :param  val:        Value name
        :type   val:        str
        :param  section:    Default value
        :type   section:    str
        :returns:           value or default value if value was not found
        """
        if self.user is not None and self.cfg.has_option(section, val):
            return self.cfg.get(section, val)
        else:
            return self.base.get(section, val, default)

    def set(self, section, val, value=None):
        """
        Sets a configuration parameter
        :param  section:    Config file section
        :type   section:    str
        :param  val:        Value name
        :type   val:        str
        :param  value:      Value
        :type   value:      str
        """
        if self.user is None:
            raise Exception('Cannot modify anonymous config')
        self.cfg.set(section, val, value)

    def has_option(self, section, name):
        """
        Checks if a parameter is present in the given section
        :param  section:    Config file section
        :type   section:    str
        :param  name:        Value name
        :type   name:        str
        :returns:           bool
        """
        if self.base.has_option(section, name):
            return True
        if self.user is None:
            return False
        return self.cfg.has_option(section, name)

    def options(self, section):
        """
        Enumerates parameters in the given section
        :param  section:    Config file section
        :type   section:    str
        :returns:           list(str)
        """
        r = []
        try:
            r.extend(self.base.options(section))
        except:
            pass
        try:
            r.extend(self.cfg.options(section))
        except:
            pass
        return r

    def remove_option(self, section, val):
        """
        Removes a parameter from the given section
        :param  section:    Config file section
        :type   section:    str
        :param  val:        Value name
        :type   val:        str
        :returns:           False is there were no such parameter
        """
        try:
            self.cfg.remove_option(section, val)
        except:
            return False

    def remove_section(self, section):
        """
        Removes a section from the given section
        :param  section:    Config file section
        :type   section:    str
        :returns:           False is there were no such parameter
        """
        try:
            self.cfg.remove_section(section)
        except:
            return False

########NEW FILE########
__FILENAME__ = application
from genesis.plugins import *
from genesis.utils import *
from genesis.ui import *
from genesis.plugmgr import PluginLoader
import genesis.ui.xslt as xslt
import genesis


from session import *
from auth import *


class Application (PluginManager, Plugin):
    """
    Class representing app state during a request.
    Instance vars:

    - ``config`` - :class:`genesis.config.ConfigProxy` - config for the current user
    - ``gconfig`` - :class:`genesis.config.Config` - global app config
    - ``auth`` - :class:`genesis.core.AuthManager` - authentication system
    - ``log`` - :class:`logging.Logger` - app log
    - ``session`` - ``dict`` - full access to the session
    """

    def __init__(self, config=None):
        PluginManager.__init__(self)
        self.gconfig = config
        self.log = config.get('log_facility')
        self.platform = config.get('platform')
        PluginLoader.register_observer(self)
        self.refresh_plugin_data()

    def plugins_changed(self):
        """
        Implementing PluginLoader observer
        """
        self.refresh_plugin_data()

    def refresh_plugin_data(self):
        """
        Rescans plugins for JS, CSS, LESS, XSLT widgets and XML templates.
        """
        self.template_path = []
        self.less_styles = []
        self.woff_fonts = []
        self.eot_fonts = []
        self.svg_fonts = []
        self.ttf_fonts = []
        self.template_styles = []
        self.template_scripts = []
        self.layouts = {}
        includes = []
        functions = {}

        for f in self.grab_plugins(IXSLTFunctionProvider):
            functions.update(f.get_funcs())

        # Get path for static content and templates
        plugins = []
        plugins.extend(PluginLoader.list_plugins().keys())
        plugins.extend(genesis.plugins.plist)

        for c in plugins:
            path = os.path.join(PluginLoader.get_plugin_path(self, c), c)

            fp = os.path.join(path, 'files')
            if os.path.exists(fp):
                self.template_styles.extend([
                    '/dl/'+c+'/'+s
                    for s in os.listdir(fp)
                    if s.endswith('.css')
                ])
                self.less_styles.extend([
                    '/dl/'+c+'/'+s
                    for s in os.listdir(fp)
                    if s.endswith('.less')
                ])
                self.woff_fonts.extend([
                    '/dl/'+c+'/'+s
                    for s in os.listdir(fp)
                    if s.endswith('.woff')
                ])
                self.eot_fonts.extend([
                    '/dl/'+c+'/'+s
                    for s in os.listdir(fp)
                    if s.endswith('.eot')
                ])
                self.svg_fonts.extend([
                    '/dl/'+c+'/'+s
                    for s in os.listdir(fp)
                    if s.endswith('.svg')
                ])
                self.ttf_fonts.extend([
                    '/dl/'+c+'/'+s
                    for s in os.listdir(fp)
                    if s.endswith('.ttf')
                ])
                self.template_scripts.extend([
                    '/dl/'+c+'/'+s
                    for s in os.listdir(fp)
                    if s.endswith('.js')
                ])

            wp = os.path.join(path, 'widgets')
            if os.path.exists(wp):
                includes.extend([
                    os.path.join(wp, s)
                    for s in os.listdir(wp)
                    if s.endswith('.xslt')
                ])

            lp = os.path.join(path, 'layout')
            if os.path.exists(lp):
                for s in os.listdir(lp):
                    if s.endswith('.xml'):
                        self.layouts['%s:%s'%(c,s)] = os.path.join(lp, s)

            tp = os.path.join(path, 'templates')
            if os.path.exists(tp):
                self.template_path.append(tp)

        if xslt.xslt is None:
            xslt.prepare(
                includes,
                functions
            )

    @property
    def config(self):
        if hasattr(self, 'auth'):
            return self.gconfig.get_proxy(self.auth.user)
        else:
            return self.gconfig.get_proxy(None)

    def start_response(self, status, headers=[]):
        self.status = status
        self.headers = headers

    def fix_length(self, content):
        # TODO: maybe move this method to middleware
        has_content_length = False
        for header, value in self.headers:
            if header.upper() == 'CONTENT-LENGTH':
                has_content_length = True
        if not has_content_length:
            self.headers.append(('Content-Length',str(len(content))))

    def dispatcher(self, environ, start_response):
        """
        Dispatches WSGI requests
        """
        self.log.debug('Dispatching %s'%environ['PATH_INFO'])
        self.environ = environ
        self.status = '200 OK'
        self.headers = [('Content-type','text/html')]
        self.session = environ['app.session']

        content = 'Sorry, no content for you'
        for handler in self.grab_plugins(IURLHandler):
            if handler.match_url(environ):
                try:
                    self.log.debug('Calling handler for %s'%environ['PATH_INFO'])
                    content = handler.url_handler(self.environ,
                                                  self.start_response)
                except Exception, e:
                    #print traceback.format_exc()
                    try:
                        content = format_error(self, e)
                    except:
                        status = '418 I\'m a teapot'
                        content = 'Fatal error occured:\n' + traceback.format_exc()
                finally:
                    break

        start_response(self.status, self.headers)
        self.fix_length(content)
        content = [content]
        self.log.debug('Finishing %s'%environ['PATH_INFO'])
        return content

    def plugin_enabled(self, cls):
        return self.platform.lower() in [x.lower() for x in cls.platform] \
           or 'any' in cls.platform

    def plugin_activated(self, plugin):
        plugin.log = self.log
        plugin.app = self

    def grab_plugins(self, iface, flt=None):
        """
        Returns list of available plugins for given interface, optionally filtered.

        :param  iface:  interface to match plugins against
        :type   iface:  :class:`genesis.com.Interface`
        :param  flt:    filter function
        :type   flt:    func(Plugin)
        :rtype:         list(:class:`genesis.com.Plugin`)
        """
        plugins = self.plugin_get(iface)
        plugins = list(set(filter(None, [self.instance_get(cls, True) for cls in plugins])))
        if flt:
            plugins = filter(flt, plugins)
        return plugins

    def get_backend(self, iface, flt=None):
        """
        Same as ``grab_plugins``, but returns the first plugin found and will
        raise :class:`genesis.util.BackendRequirementError` if no plugin was
        found.

        :param  iface:  interface to match plugins against
        :type   iface:  :class:`genesis.com.Interface`
        :param  flt:    filter function
        :type   flt:    func(Plugin)
        :rtype:         :class:`genesis.com.Plugin`
        """
        lst = self.grab_plugins(iface, flt)
        if len(lst) == 0:
            raise BackendRequirementError(iface.__name__)
        return lst[0]

    def get_config(self, plugin):
        """
        Returns :class:`genesis.api.ModuleConfig` for a given plugin.
        """
        if plugin.__class__ != type:
            plugin = plugin.__class__
        return self.get_config_by_classname(plugin.__name__)

    def get_config_by_classname(self, name):
        """
        Returns :class:`genesis.api.ModuleConfig` for a given plugin class name.
        """
        cfg = self.get_backend(IModuleConfig,
                flt=lambda x: x.target.__name__==name)
        cfg.overlay_config()
        return cfg

    def get_template(self, filename=None, search_path=[]):
        return BasicTemplate(
                filename=filename,
                search_path=self.template_path + search_path,
                styles=self.template_styles,
                scripts=self.template_scripts
               )

    def inflate(self, layout):
        """
        Inflates an XML UI layout into DOM UI tree.

        :param  layout: '<pluginid>:<layoutname>', ex: dashboard:main for
                        /plugins/dashboard/layout/main.xml
        :type   layout: str
        :rtype:         :class:`genesis.ui.Layout`
        """
        f = self.layouts[layout+'.xml']
        return Layout(f)

    def stop(self):
        """
        Exits Genesis
        """
        if os.path.exists('/var/run/genesis.pid'):
            os.unlink('/var/run/genesis.pid')
        self.config.get('server').stop()

    def restart(self):
        """
        Restarts Genesis process
        """
        self.config.get('server').restart_marker = True
        self.stop()


class AppDispatcher(object):
    """
    Main WSGI dispatcher which assembles session, auth and application
    altogether
    """
    def __init__(self, config=None):
        self.config = config
        self.log = config.get('log_facility')
        self.sessions = SessionStore.init_safe()

    def dispatcher(self, environ, start_response):
        self.log.debug('Dispatching %s'%environ['PATH_INFO'])

        app = Application(self.config)
        auth = AuthManager(self.config, app, app.dispatcher)
        sm = SessionManager(self.sessions, auth)

        return sm(environ, start_response)

########NEW FILE########
__FILENAME__ = auth
from hashlib import sha1
from base64 import b64encode
from passlib.hash import sha512_crypt, bcrypt
import syslog
import time

from genesis.api import get_environment_vars


def check_password(passw, hash):
    """
    Tests if a password is the same as the hash.

    Instance vars:

    - ``passw`` - ``str``, The password in it's original form
    - ``hash`` - ``str``, The hashed version of the password to check against
    """
    if hash.startswith('{SHA}'):
        try:
            import warnings
            warnings.warn(
                'SHA1 as a password hash may be removed in a future release.')
            passw_hash = '{SHA}' + b64encode(sha1(passw).digest())
            if passw_hash == hash:
                return True
        except:
            import traceback
            traceback.print_exc()
    elif hash.startswith('$2a$') and len(hash) == 60:
        return bcrypt.verify(passw, hash)
    elif sha512_crypt.identify(hash):
        return sha512_crypt.verify(passw, hash)
    return False

class AuthManager(object):
    """
    Authentication middleware which takes care of user authentication

    Instance vars:

    - ``user`` - `str`, current user logged in or None
    """

    def __init__(self, config, app, dispatcher):
        self.user = None

        self.app = app
        app.auth = self
        self._dispatcher = dispatcher
        self._log = config.get('log_facility')

        self._config = config
        self._enabled = False
        if config.has_option('genesis', 'auth_enabled'):
            if config.getint('genesis', 'auth_enabled'):
                # Check for 'users' section
                if config.has_section('users'):
                    if len(config.items('users')) > 0:
                        self._enabled = True
                    else:
                        self._log.error('Authentication requested, but no users configured')
                else:
                    self._log.error('Authentication requested, but no [users] section')

    def deauth(self):
        """
        Deauthenticates current user.
        """
        if self.app.config.has_option('genesis', 'auth_enabled') \
        and self.app.config.get('genesis', 'auth_enabled') == '1':
            self.app.log.info('Session closed for user %s' % self.app.session['auth.user'])
            self.app.session['auth.user'] = None

    def __call__(self, environ, start_response):
        session = environ['app.session']

        if environ['PATH_INFO'] == '/auth-redirect':
            start_response('301 Moved Permanently', [('Location', '/')])
            return ''

        self.user = session['auth.user'] if 'auth.user' in session else None
        if not self._enabled:
            self.user = 'anonymous'
        if self.user is not None or environ['PATH_INFO'].startswith('/dl') \
            or environ['PATH_INFO'].startswith('/core'):
            return self._dispatcher(environ, start_response)

        if environ['PATH_INFO'] == '/auth':
            vars = get_environment_vars(environ)
            user = vars.getvalue('username', '')
            if self._config.has_option('users', user):
                pwd = self._config.get('users', user)
                resp = vars.getvalue('response', '')
                if check_password(resp, pwd):
                    self.app.log.info('Session opened for user %s from %s' % (user, environ['REMOTE_ADDR']))
                    session['auth.user'] = user
                    start_response('200 OK', [
                        ('Content-type','text/plain'),
                        ('X-Genesis-Auth', 'ok'),
                    ])
                    return ''

            self.app.log.error('Login failed for user %s from %s' % (user, environ['REMOTE_ADDR']))
            time.sleep(2)

            start_response('403 Login Failed', [
                ('Content-type','text/plain'),
                ('X-Genesis-Auth', 'fail'),
            ])
            return 'Login failed'

        templ = self.app.get_template('auth.xml')
        start_response('200 OK', [('Content-type','text/html')])
        start_response('200 OK', [
            ('Content-type','text/html'),
            ('X-Genesis-Auth', 'start'),
        ])
        return templ.render()

########NEW FILE########
__FILENAME__ = session
# encoding: utf-8
#
# Copyright (C) 2010 Dmitry Zamaruev (dmitry.zamaruev@gmail.com)


"""
This module provides simple session handling and WSGI Middleware.
You should instantiate SessionStore, and pass it to WSGI middleware
along with next WSGI application in chain.
Example:
>>> environ = {}
>>>
>>> def my_start_response(status, headers):
...     environ['HTTP_COOKIE'] = headers[0][1]
...
>>> def my_application(env, sr):
...     print("var = " + env['app.session'].get('var','None'))
...     env['app.session']['var'] = environ.get('REMOTE_ADDR', 'Test')
...     sr('200 OK',[])
...     return None  # Just for test, please return string
...
>>> s = SessionStore()
>>>
>>> SessionManager(s, my_application)(environ, my_start_response)
var = None
>>> SessionManager(s, my_application)(environ, my_start_response)
var = Test
>>>
>>> environ['REMOTE_ADDR'] = '127.0.0.1'
>>> SessionManager(s, my_application)(environ, my_start_response)
var = None
>>> SessionManager(s, my_application)(environ, my_start_response)
var = 127.0.0.1
>>> cookie = environ['HTTP_COOKIE']
>>>
>>> environ['REMOTE_ADDR'] = '127.0.0.2'
>>> SessionManager(s, my_application)(environ, my_start_response)
var = None
>>> environ['HTTP_COOKIE'] = None
>>> SessionManager(s, my_application)(environ, my_start_response)
var = None
>>>
>>> environ['REMOTE_ADDR'] = '127.0.0.1'
>>> environ['HTTP_COOKIE'] = cookie
>>> SessionManager(s, my_application)(environ, my_start_response)
var = 127.0.0.1
>>>
"""
import os
import time
import Cookie
import hashlib
from genesis.utils import ClassProxy


def sha1(var):
    return hashlib.sha1(str(var)).hexdigest()


class SessionProxy(object):
    """ SessionProxy used to automatically add prefixes to keys

    >>> sess = Session('')
    >>> proxy = sess.proxy('test')
    >>> proxy['123'] = 'value'
    >>> sess
    {'test-123': 'value'}
    >>> proxy.get('123')
    'value'
    >>> proxy['123']
    'value'
    >>>
    """
    def __init__(self, session, prefix):
        self._session = session
        self._prefix = prefix + '-'

    def __getitem__(self, key):
        return self._session[self._prefix + key]

    def __setitem__(self, key, value):
        self._session[self._prefix + key] = value

    def get(self, key, default=None):
        return self._session.get(self._prefix + key, default)


class Session(dict):
    """ Session object
    Holds data between requests
    """
    def __init__(self, id):
        dict.__init__(self)
        self._id = id
        self._creationTime = self._accessTime = time.time()

    @property
    def id(self):
        """ Session ID """
        return self._id

    @property
    def creationTime(self):
        """ Session create time """
        return self._creationTime

    @property
    def accessTime(self):
        """ Session last access time """
        return self._accessTime

    def touch(self):
        self._accessTime = time.time()

    def proxy(self, prefix):
        return SessionProxy(self, prefix)

    @staticmethod
    def generateId():
        return sha1(os.urandom(40))


class SessionStore(object):
    """ Manages multiple session objects
    """
    # TODO: add session deletion/invalidation
    def __init__(self, timeout=30):
        # Default timeout is 30 minutes
        # Use internal timeout in seconds (for easier calculations)
        self._timeout = timeout*60
        self._store = {}

    @staticmethod
    def init_safe():
        """ Create a thread-safe SessionStore """
        return ClassProxy(SessionStore())

    def create(self):
        """ Create a new session,
        you should commit session to save it for future
        """
        sessId = Session.generateId()
        return Session(sessId)

    def checkout(self, id):
        """ Checkout session for use,
        you should commit session to save it for future
        """
        sess = self._store.get(id)

        if sess is not None:
            sess.touch()

        return sess

    def commit(self, session):
        """ Saves session for future use (useful in database backends)
        """
        self._store[session.id] = session

    def vacuum(self):
        """ Goes through all sessions and deletes all old sessions
        Should be called periodically
        """
        ctime = time.time()
        # We should use .keys() here, because we could change size of dict
        for sessId in self._store.keys():
            if (ctime - self._store[sessId].accessTime) > self._timeout:
                del self._store[sessId]


class SessionManager(object):
    """
    Session middleware. Takes care of creation/checkout/commit of a session.
    Sets 'app.session' variable inside WSGI environment.
    """
    # TODO: Add cookie expiration and force expiration
    # TODO: Add deletion of invalid session
    def __init__(self, store, application):
        """ Initializes SessionManager

        @store - instance of SessionStore
        @application - wsgi dispatcher callable
        """
        self._session_store = store
        self._application = application
        self._session = None
        self._start_response_args = ('200 OK', [])

    def add_cookie(self, headers):
        if self._session is None:
            raise RuntimeError('Attempt to save non-initialized session!')

        sess_id = self._session.id
        C = Cookie.SimpleCookie()
        C['sess'] = sess_id
        C['sess']['path'] = '/'

        headers.append(('Set-Cookie',C['sess'].OutputString()))

    def start_response(self, status, headers):
        self.add_cookie(headers)
        self._start_response_args = (status, headers)

    def _load_session_cookie(self, environ):
        C = Cookie.SimpleCookie(environ.get('HTTP_COOKIE'))
        cookie = C.get('sess')
        if cookie is not None:
            self._session = self._session_store.checkout(cookie.value)

    def _get_client_id(self, environ):
        hash = 'salt'
        hash += environ.get('REMOTE_ADDR', '')
        hash += environ.get('REMOTE_HOST', '')
        hash += environ.get('HTTP_USER_AGENT', '')
        hash += environ.get('HTTP_HOST', '')
        return sha1(hash)

    def _get_session(self, environ):
        # Load session from cookie
        self._load_session_cookie(environ)

        # Check is session exists and valid
        client_id = self._get_client_id(environ)
        if self._session is not None:
            if self._session.get('client_id','') != client_id:
                self._session = None

        # Create session
        if self._session is None:
            self._session = self._session_store.create()
            self._session['client_id'] = client_id

        return self._session

    def __call__(self, environ, start_response):
        self.start_response_origin = start_response
        self._session_store.vacuum()
        sess = self._get_session(environ)
        environ['app.session'] = sess

        result = None
        try:
            result = self._application(environ, self.start_response)
        finally:
            self._session_store.commit(self._session)

        self.start_response_origin(*self._start_response_args)
        return result

########NEW FILE########
__FILENAME__ = daemon
import sys
import os
import time
import atexit
from signal import SIGTERM


class Daemon:
    """
    A generic daemon class.

    Usage: subclass the Daemon class and override the run() method
    """

    def __init__(self, pidfile, stdin='/dev/null',
                    stdout='/dev/null', stderr='/dev/null'):
        self.stdin = stdin
        self.stdout = stdout
        self.stderr = stderr
        self.pidfile = pidfile

    def daemonize(self):
        """
        do the UNIX double-fork magic, see Stevens' "Advanced
        Programming in the UNIX Environment" for details (ISBN 0201563177)
        http://www.erlenstar.demon.co.uk/unix/faq_2.html#SEC16
        """
        try:
            pid = os.fork()
            if pid > 0:
                # exit first parent
                sys.exit(0)
        except OSError, e:
            sys.stderr.write("fork #1 failed: %d (%s)\n" % (e.errno, e.strerror))
            sys.exit(1)

        # decouple from parent environment
        #os.chdir("/")
        os.setsid()
        os.umask(0066)

        # do second fork
        try:
            pid = os.fork()
            if pid > 0:
                # exit from second parent
                sys.exit(0)
        except OSError, e:
            sys.stderr.write("fork #2 failed: %d (%s)\n" % (e.errno, e.strerror))
            sys.exit(1)

        # redirect standard file descriptors
        sys.stdout.flush()
        sys.stderr.flush()
        si = file(self.stdin, 'r')
        so = file(self.stdout, 'a+')
        se = file(self.stderr, 'a+', 0)
        os.dup2(si.fileno(), sys.stdin.fileno())
        os.dup2(so.fileno(), sys.stdout.fileno())
        os.dup2(se.fileno(), sys.stderr.fileno())

        # write pidfile
        atexit.register(self.delpid)
        pid = str(os.getpid())
        try:
            open(self.pidfile,'w+').write("%s\n" % pid)
        except:
            pass

    def delpid(self):
        os.remove(self.pidfile)

    def start(self):
        """
        Start the daemon
        """
        # Check for a pidfile to see if the daemon already runs
        try:
            pf = file(self.pidfile,'r')
            pid = int(pf.read().strip())
            pf.close()
        except IOError:
            pid = None

        if pid:
            message = "pidfile %s already exist. Daemon already running?\n"
            sys.stderr.write(message % self.pidfile)
            sys.exit(1)

        # Start the daemon
        self.daemonize()
        self.run()

    def stop(self):
        """
        Stop the daemon
        """
        # Get the pid from the pidfile
        try:
            pf = file(self.pidfile,'r')
            pid = int(pf.read().strip())
            pf.close()
        except IOError:
            pid = None

        if not pid:
            message = "pidfile %s does not exist. Daemon not running?\n"
            sys.stderr.write(message % self.pidfile)
            return # not an error in a restart

        # Try killing the daemon process
        try:
            while 1:
                os.kill(pid, SIGTERM)
                time.sleep(0.1)
        except OSError, err:
            err = str(err)
            if err.find("No such process") > 0:
                if os.path.exists(self.pidfile):
                    os.remove(self.pidfile)
            else:
                print str(err)
                sys.exit(1)

    def restart(self):
        """
        Restart the daemon
        """
        self.stop()
        self.start()

    def run(self):
        """
        You should override this method when you subclass Daemon.
        It will be called after the process has been
        daemonized by start() or restart().
        """

########NEW FILE########
__FILENAME__ = deployed
import os
from genesis.utils import hashpw, shell
from ConfigParser import ConfigParser


RCFG_FILE = '/root/genesis-re.conf'

def reconfigure(cfg):
    if not os.path.exists(RCFG_FILE):
        return

    rcfg = ConfigParser()
    rcfg.read(RCFG_FILE)

    if rcfg.has_option('genesis', 'credentials'):
        u,p = rcfg.get('genesis', 'credentials').split(':')
        cfg.remove_option('users', 'admin')
        if not p.startswith('{SHA}'):
            p = hashpw(p)
        cfg.set('users', u, p)

    if rcfg.has_option('genesis', 'plugins'):
        for x in rcfg.get('genesis', 'plugins').split():
            shell('genesis-pkg get ' + x)

    if rcfg.has_option('genesis', 'ssl'):
        c,k = rcfg.get('genesis', 'ssl').split()
        cfg.set('ssl', '1')
        cfg.set('cert_key', k)
        cfg.set('cert_file', c)

    if rcfg.has_option('genesis', 'port'):
        cfg.set('genesis', 'bind_port', rcfg.get('genesis', 'port'))

    if rcfg.has_option('genesis', 'host'):
        cfg.set('genesis', 'bind_host', rcfg.get('genesis', 'host'))

    cfg.set('genesis', 'firstrun', 'no')
    cfg.save()
    os.unlink(RCFG_FILE)

########NEW FILE########
__FILENAME__ = backend
import ConfigParser
import glob
import OpenSSL
import os

from genesis import apis
from genesis.com import *
from genesis.utils import SystemTime
from genesis.utils.error import SystemTimeError
from genesis.plugins.core.api import ISSLPlugin
from genesis.plugins.webapps.backend import WebappControl


class CertControl(Plugin):
	text = "Certificates"
	iconfont = 'gen-certificate'

	def get_certs(self):
		# Find all certs added by Genesis and return basic information
		certs = []
		if not os.path.exists('/etc/ssl/certs/genesis'):
			os.mkdir('/etc/ssl/certs/genesis')
		if not os.path.exists('/etc/ssl/private/genesis'):
			os.mkdir('/etc/ssl/private/genesis')
		for x in glob.glob('/etc/ssl/certs/genesis/*.gcinfo'):
			cfg = ConfigParser.ConfigParser()
			cfg.read(x)
			certs.append({'name': cfg.get('cert', 'name'),
				'expiry': cfg.get('cert', 'expiry') if cfg.has_option('cert', 'expiry') else 'Unknown',
				'domain': cfg.get('cert', 'domain') if cfg.has_option('cert', 'domain') else 'Unknown',
				'keytype': cfg.get('cert', 'keytype') if cfg.has_option('cert', 'keytype') else 'Unknown',
				'keylength': cfg.get('cert', 'keylength') if cfg.has_option('cert', 'keylength') else 'Unknown',
				'assign': cfg.get('cert', 'assign').split('\n') if cfg.has_option('cert', 'assign') else 'Unknown'})
		return certs

	def get_cas(self):
		# Find all certificate authorities generated by Genesis 
		# and return basic information
		certs = []
		if not os.path.exists('/etc/ssl/certs/genesis/ca'):
			os.mkdir('/etc/ssl/certs/genesis/ca')
		if not os.path.exists('/etc/ssl/private/genesis/ca'):
			os.mkdir('/etc/ssl/private/genesis/ca')
		for x in glob.glob('/etc/ssl/certs/genesis/ca/*.pem'):
			name = os.path.splitext(os.path.split(x)[1])[0]
			cert = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, open(x, 'r').read())
			key = OpenSSL.crypto.load_privatekey(OpenSSL.crypto.FILETYPE_PEM, 
				open(os.path.join('/etc/ssl/private/genesis/ca', name+'.key'), 'r').read())
			certs.append({'name': name, 'expiry': cert.get_notAfter()})
		return certs

	def get_ssl_capable(self):
		lst = []
		for x in apis.webapps(self.app).get_sites():
			if x.ssl_able:
				lst.append(x)
		return lst, self.app.grab_plugins(ISSLPlugin)

	def has_expired(self, certname):
		# Return True if the plugin is expired, False if not
		c = open('/etc/ssl/certs/genesis/'+certname+'.crt', 'r').read()
		crt = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, c)
		return crt.has_expired()

	def add_ext_cert(self, name, cert, key, chain='', assign=[]):
		# Save the file streams as we get them, and
		# Add a .gcinfo file for a certificate uploaded externally
		try:
			crt = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, cert)
		except Exception, e:
			raise Exception('Could not read certificate file. Please make sure you\'ve selected the proper file.', e)
		try:
			ky = OpenSSL.crypto.load_privatekey(OpenSSL.crypto.FILETYPE_PEM, key)
		except Exception, e:
			raise Exception('Could not read private keyfile. Please make sure you\'ve selected the proper file.', e)
		
		x = open(os.path.join('/etc/ssl/certs/genesis', name + '.crt'), 'w')
		x.write(cert)
		if chain:
			x.write('\n') if not cert.endswith('\n') else None
			x.write(chain)
		x.close()
		open(os.path.join('/etc/ssl/private/genesis', name + '.key'), 'w').write(key)

		if ky.type() == OpenSSL.crypto.TYPE_RSA:
			keytype = 'RSA'
		elif ky.type() == OpenSSL.crypto.TYPE_DSA:
			keytype = 'DSA'
		else:
			keytype = 'Unknown'
		cfg = ConfigParser.ConfigParser()
		cfg.add_section('cert')
		cfg.set('cert', 'name', name)
		cfg.set('cert', 'expiry', crt.get_notAfter())
		cfg.set('cert', 'keytype', keytype)
		cfg.set('cert', 'keylength', str(int(ky.bits())))
		cfg.set('cert', 'domain', crt.get_subject().CN)
		cfg.set('cert', 'assign', '\n'.join(assign))
		cfg.write(open(os.path.join('/etc/ssl/certs/genesis', name + '.gcinfo'), 'w'))
		os.chmod(os.path.join('/etc/ssl/certs/genesis', name + '.crt'), 0660)
		os.chmod(os.path.join('/etc/ssl/private/genesis', name + '.key'), 0660)

	def gencert(self, name, vars, hostname):
		# Make sure our folders are in place
		if not os.path.exists('/etc/ssl/certs/genesis'):
			os.mkdir('/etc/ssl/certs/genesis')
		if not os.path.exists('/etc/ssl/private/genesis'):
			os.mkdir('/etc/ssl/private/genesis')

		# If system time is way off, raise an error
		try:
			st = SystemTime().get_offset()
			if st < -3600 or st > 3600:
				raise SystemTimeError(st)
		except:
			raise SystemTimeError('UNKNOWN')

		# Check to see that we have a CA ready
		ca_cert_path = '/etc/ssl/certs/genesis/ca/'+hostname+'.pem'
		ca_key_path = '/etc/ssl/private/genesis/ca/'+hostname+'.key'
		if not os.path.exists(ca_cert_path) and not os.path.exists(ca_key_path):
			self.create_authority(hostname)
		ca_cert = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, open(ca_cert_path).read())
		ca_key = OpenSSL.crypto.load_privatekey(OpenSSL.crypto.FILETYPE_PEM, open(ca_key_path).read())

		# Generate a key, then use it to sign a new cert
		# We'll use 2048-bit RSA until pyOpenSSL supports ECC
		keytype = OpenSSL.crypto.TYPE_DSA if self.app.get_config(self).keytype == 'DSA' else OpenSSL.crypto.TYPE_RSA
		keylength = int(self.app.get_config(self).keylength)
		try:
			key = OpenSSL.crypto.PKey()
			key.generate_key(keytype, keylength)
			crt = OpenSSL.crypto.X509()
			crt.set_version(3)
			if vars.getvalue('certcountry', ''):
				crt.get_subject().C = vars.getvalue('certcountry')
			if vars.getvalue('certsp', ''):
				crt.get_subject().ST = vars.getvalue('certsp')
			if vars.getvalue('certlocale', ''):
				crt.get_subject().L = vars.getvalue('certlocale')
			if vars.getvalue('certcn', ''):
				crt.get_subject().CN = vars.getvalue('certcn')
			if vars.getvalue('certemail', ''):
				crt.get_subject().emailAddress = vars.getvalue('certemail')
			crt.set_serial_number(int(SystemTime().get_serial_time()))
			crt.gmtime_adj_notBefore(0)
			crt.gmtime_adj_notAfter(2*365*24*60*60)
			crt.set_issuer(ca_cert.get_subject())
			crt.set_pubkey(key)
			crt.sign(ca_key, 'sha1')
		except Exception, e:
			raise Exception('Error generating self-signed certificate: '+str(e))
		open('/etc/ssl/certs/genesis/'+name+'.crt', "wt").write(
			OpenSSL.crypto.dump_certificate(
				OpenSSL.crypto.FILETYPE_PEM, crt)
			)
		os.chmod('/etc/ssl/certs/genesis/'+name+'.crt', 0660)
		open('/etc/ssl/private/genesis/'+name+'.key', "wt").write(
			OpenSSL.crypto.dump_privatekey(
				OpenSSL.crypto.FILETYPE_PEM, key)
			)
		os.chmod('/etc/ssl/private/genesis/'+name+'.key', 0660)

		if key.type() == OpenSSL.crypto.TYPE_RSA:
			keytype = 'RSA'
		elif key.type() == OpenSSL.crypto.TYPE_DSA:
			keytype = 'DSA'
		else:
			keytype = 'Unknown'
		cfg = ConfigParser.ConfigParser()
		cfg.add_section('cert')
		cfg.set('cert', 'name', name)
		cfg.set('cert', 'expiry', crt.get_notAfter())
		cfg.set('cert', 'domain', crt.get_subject().CN)
		cfg.set('cert', 'keytype', keytype)
		cfg.set('cert', 'keylength', str(int(key.bits())))
		cfg.set('cert', 'assign', '')
		cfg.write(open('/etc/ssl/certs/genesis/'+name+'.gcinfo', 'w'))

	def create_authority(self, hostname):
		key = OpenSSL.crypto.PKey()
		key.generate_key(OpenSSL.crypto.TYPE_RSA, 2048)

		ca = OpenSSL.crypto.X509()
		ca.set_version(3)
		ca.set_serial_number(int(SystemTime().get_serial_time()))
		ca.get_subject().CN = hostname
		ca.gmtime_adj_notBefore(0)
		ca.gmtime_adj_notAfter(5*365*24*60*60)
		ca.set_issuer(ca.get_subject())
		ca.set_pubkey(key)
		ca.add_extensions([
		  OpenSSL.crypto.X509Extension("basicConstraints", True,
		                               "CA:TRUE, pathlen:0"),
		  OpenSSL.crypto.X509Extension("keyUsage", True,
		                               "keyCertSign, cRLSign"),
		  OpenSSL.crypto.X509Extension("subjectKeyIdentifier", False, "hash",
		                               subject=ca),
		  ])
		ca.sign(key, 'sha1')
		open('/etc/ssl/certs/genesis/ca/'+hostname+'.pem', "wt").write(
			OpenSSL.crypto.dump_certificate(
				OpenSSL.crypto.FILETYPE_PEM, ca)
			)
		os.chmod('/etc/ssl/certs/genesis/ca/'+hostname+'.pem', 0660)
		open('/etc/ssl/private/genesis/ca/'+hostname+'.key', "wt").write(
			OpenSSL.crypto.dump_privatekey(
				OpenSSL.crypto.FILETYPE_PEM, key)
			)

	def delete_authority(self, data):
		os.unlink(os.path.join('/etc/ssl/certs/genesis/ca', data['name']+'.pem'))
		os.unlink(os.path.join('/etc/ssl/private/genesis/ca', data['name']+'.key'))

	def assign(self, name, assign):
		# Assign a certificate to plugins/webapps as listed
		cfg = ConfigParser.ConfigParser()
		cfg.read('/etc/ssl/certs/genesis/'+name+'.gcinfo')
		alist = cfg.get('cert', 'assign').split('\n')
		for i in alist:
			if i == '':
				alist.remove(i)
		for x in assign:
			if x[0] == 'genesis':
				self.app.gconfig.set('genesis', 'cert_file', 
					'/etc/ssl/certs/genesis/'+name+'.crt')
				self.app.gconfig.set('genesis', 'cert_key', 
					'/etc/ssl/private/genesis/'+name+'.key')
				self.app.gconfig.set('genesis', 'ssl', '1')
				alist.append('Genesis SSL')
				self.app.gconfig.save()
			elif x[0] == 'webapp':
				WebappControl(self.app).ssl_enable(x[1],
					'/etc/ssl/certs/genesis/'+name+'.crt',
					'/etc/ssl/private/genesis/'+name+'.key')
				alist.append(x[1].name + ' ('+x[1].stype+')')
				WebappControl(self.app).nginx_reload()
			elif x[0] == 'plugin':
				x[1].enable_ssl('/etc/ssl/certs/genesis/'+name+'.crt',
					'/etc/ssl/private/genesis/'+name+'.key')
				alist.append(x[1].text)
		cfg.set('cert', 'assign', '\n'.join(alist))
		cfg.write(open('/etc/ssl/certs/genesis/'+name+'.gcinfo', 'w'))

	def unassign(self, name, assign):
		cfg = ConfigParser.ConfigParser()
		cfg.read('/etc/ssl/certs/genesis/'+name+'.gcinfo')
		alist = cfg.get('cert', 'assign').split('\n')
		for i in alist:
			if i == '':
				alist.remove(i)
		for x in assign:
			if x[0] == 'genesis':
				self.app.gconfig.set('genesis', 'cert_file', '')
				self.app.gconfig.set('genesis', 'cert_key', '')
				self.app.gconfig.set('genesis', 'ssl', '0')
				alist.remove('Genesis SSL')
				self.app.gconfig.save()
			elif x[0] == 'webapp':
				WebappControl(self.app).ssl_disable(x[1])
				alist.remove(x[1].name + ' ('+x[1].stype+')')
				WebappControl(self.app).nginx_reload()
			elif x[0] == 'plugin':
				x[1].disable_ssl()
				alist.remove(x[1].text)
		cfg.set('cert', 'assign', '\n'.join(alist))
		cfg.write(open('/etc/ssl/certs/genesis/'+name+'.gcinfo', 'w'))

	def remove_notify(self, name):
		# Called by plugin when removed.
		# Removes the associated entry from gcinfo tracker file
		try:
			cfg = ConfigParser.ConfigParser()
			cfg.read('/etc/ssl/certs/genesis/'+name+'.gcinfo')
			alist = []
			for x in cfg.get('cert', 'assign').split('\n'):
				if x != name:
					alist.append(x)
			cfg.set('cert', 'assign', '\n'.join(alist))
			cfg.write(open('/etc/ssl/certs/genesis/'+name+'.gcinfo', 'w'))
		except:
			pass

	def remove(self, name):
		# Remove cert, key and control file for associated name
		cfg = ConfigParser.ConfigParser()
		cfg.read('/etc/ssl/certs/genesis/'+name+'.gcinfo')
		alist = cfg.get('cert', 'assign').split('\n')
		wal, pal = self.get_ssl_capable()
		for x in wal:
			if (x.name+' ('+x.stype+')') in alist:
				WebappControl(self.app).ssl_disable(x)
		for y in pal:
			if y.text in alist:
				y.disable_ssl()
		if 'Genesis SSL' in alist:
			self.app.gconfig.set('genesis', 'cert_file', '')
			self.app.gconfig.set('genesis', 'cert_key', '')
			self.app.gconfig.set('genesis', 'ssl', '0')
			self.app.gconfig.save()
		os.unlink('/etc/ssl/certs/genesis/'+name+'.gcinfo')
		try:
			os.unlink('/etc/ssl/certs/genesis/'+name+'.crt')
		except:
			pass
		try:
			os.unlink('/etc/ssl/private/genesis/'+name+'.key')
		except:
			pass

########NEW FILE########
__FILENAME__ = config
from genesis.api import ModuleConfig
from backend import CertControl


class GeneralConfig(ModuleConfig):
    target = CertControl
    
    labels = {
        'keylength': 'Default key length',
        'keytype': 'Default key type',
        'ciphers': 'Cipher string'
    }
    
    keylength = '2048'
    keylength_opts = ['1024', '2048', '4096']
    keytype = 'RSA'
    keytype_opts = ['DSA', 'RSA']
    ciphers = 'ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-AES256-GCM-SHA384:kEDH+AESGCM:ECDHE-RSA-AES128-SHA256:ECDHE-ECDSA-AES128-SHA256:ECDHE-RSA-AES128-SHA:ECDHE-ECDSA-AES128-SHA:ECDHE-RSA-AES256-SHA384:ECDHE-ECDSA-AES256-SHA384:ECDHE-RSA-AES256-SHA:ECDHE-ECDSA-AES256-SHA:DHE-RSA-AES128-SHA256:DHE-RSA-AES128-SHA:DHE-RSA-AES256-SHA256:DHE-DSS-AES256-SHA:AES128-GCM-SHA256:AES256-GCM-SHA384:ECDHE-RSA-DES-CBC3-SHA:ECDHE-ECDSA-DES-CBC3-SHA:EDH-RSA-DES-CBC3-SHA:EDH-DSS-DES-CBC3-SHA:DES-CBC3-SHA:HIGH:!aNULL:!eNULL:!EXPORT:!DES:!RC4:!MD5:!PSK'

########NEW FILE########
__FILENAME__ = main
from genesis.com import *
from genesis.api import *
from genesis.ui import *
from genesis import apis
from genesis.utils import *
from genesis.plugins.network.backend import IHostnameManager

from backend import CertControl

import os
import re


class CertificatesPlugin(CategoryPlugin, URLHandler):
    text = 'Certificates'
    iconfont = 'gen-certificate'
    folder = 'system'

    def on_init(self):
        self.certs = sorted(self._cc.get_certs(),
            key=lambda x: x['name'])
        self.cas = sorted(self._cc.get_cas(),
            key=lambda x: x['name'])

    def on_session_start(self):
        self._cc = CertControl(self.app)
        self._gen = None
        self._tab = 0
        self._wal = []
        self._pal = []
        self._upload = None

    def get_ui(self):
        ui = self.app.inflate('certificates:main')
        ui.find('tabs').set('active', self._tab)

        cfg = self.app.get_config(CertControl(self.app))
        ui.find('kl'+cfg.keylength).set('selected', True)
        ui.find('kt'+cfg.keytype.lower()).set('selected', True)
        ui.find('ciphers').set('value', cfg.ciphers)

        lst = ui.find('certlist')
        for s in self.certs:
            lst.append(UI.DTR(
                UI.IconFont(iconfont='gen-certificate'),
                UI.Label(text=s['name']),
                UI.Label(text=', '.join(filter(None, s['assign']))),
                UI.HContainer(
                    UI.TipIcon(iconfont='gen-info', text='Information',
                        id='info/' + str(self.certs.index(s))),
                    UI.TipIcon(iconfont='gen-close', text='Delete',
                        id='del/' + str(self.certs.index(s)),
                        warning=('Are you sure you wish to remove this certificate? '
                            'SSL on all associated services will be disabled'), ),
                    ),
               ))

        lst = ui.find('certauth')
        if not self.cas:
            lst.append(UI.Button(text="Generate New", id="cagen"))
        for s in self.cas:
            exp = s['expiry']
            exp = exp[0:4] + '-' + exp[4:6] + '-' + exp[6:8] + ', ' + exp[8:10] + ':' + exp[10:12]
            lst.append(UI.FormLine(
                UI.HContainer(
                    UI.Label(text='Expires '+exp),
                    UI.TipIcon(iconfont='gen-download', text='Download',
                        id='cadl',
                        onclick='window.open("/certificates/dl", "_blank")'),
                    UI.TipIcon(iconfont='gen-close', text='Delete',
                        id='cadel/' + str(self.cas.index(s))),
                    ), text=s['name']
               ))

        if self._gen:
            ui.find('certcn').set('value', self.app.get_backend(IHostnameManager).gethostname().lower())
            self._wal, self._pal = self._cc.get_ssl_capable()
            alist, wlist, plist = [], [], []
            for cert in self.certs:
                for i in cert['assign']:
                    if i != '':
                        alist.append(i)
            if not 'Genesis SSL' in alist:
                ui.find('certassign').append(
                    UI.Checkbox(text='Genesis SSL', name='genesis', value='genesis', checked=False),
                )
            for x in self._wal:
                if not (x.name+' ('+x.stype+')') in alist:
                    ui.find('certassign').append(
                        UI.Checkbox(text=x.name, name='wassign[]', value=x.name, checked=False),
                    )
                    wlist.append(x)
            self._wal = wlist
            for x in self._pal:
                if not x.text in alist:
                    ui.find('certassign').append(
                        UI.Checkbox(text=x.text, name='passign[]', value=x.text, checked=False),
                    )
                    plist.append(x)
            self._pal = plist
        else:
            ui.remove('dlgGen')

        if self._cinfo:
            self._wal, self._pal = self._cc.get_ssl_capable()
            ui.find('certname').set('text', self._cinfo['name'])
            ui.find('domain').set('text', self._cinfo['domain'])
            ui.find('ikeytype').set('text', self._cinfo['keylength']+'-bit '+self._cinfo['keytype'])
            exp = self._cinfo['expiry']
            exp = exp[0:4] + '-' + exp[4:6] + '-' + exp[6:8] + ', ' + exp[8:10] + ':' + exp[10:12]
            ui.find('expires').set('text', exp)

            alist = []
            for cert in self.certs:
                if cert != self._cinfo:
                    for i in cert['assign']:
                        if i != '':
                            alist.append(i)

            if not 'Genesis SSL' in alist:
                if 'Genesis SSL' in self._cinfo['assign']:
                    ic, ict, show = 'gen-checkmark-circle', 'Assigned', 'd'
                else:
                    ic, ict, show = None, None, 'e'
                ui.find('certassign').append(
                    UI.DTR(
                        UI.IconFont(iconfont=ic, text=ict),
                        UI.IconFont(iconfont='gen-arkos-round'),
                        UI.Label(text='Genesis'),
                        UI.HContainer(
                            (UI.TipIcon(iconfont='gen-checkmark-circle',
                                text='Assign', id='ac/'+self._cinfo['name']+'/g') if show == 'e' else None),
                            (UI.TipIcon(iconfont='gen-close',
                                text='Unassign', id='uc/'+self._cinfo['name']+'/g',
                                warning=('Are you sure you wish to unassign this certificate? '
                                    'SSL on this service will be disabled, and you will need to '
                                    'reload Genesis for changes to take place.')) if show == 'd' else None),
                        ),
                    )
                )
            for x in self._wal:
                if not (x.name+' ('+x.stype+')') in alist:
                    if (x.name+' ('+x.stype+')') in self._cinfo['assign']:
                        ic, ict, show = 'gen-checkmark-circle', 'Assigned', 'd'
                    else:
                        ic, ict, show = None, None, 'e'
                    ui.find('certassign').append(
                        UI.DTR(
                            UI.IconFont(iconfont=ic, text=ict),
                            UI.IconFont(iconfont='gen-earth'),
                            UI.Label(text=x.name),
                            UI.HContainer(
                                (UI.TipIcon(iconfont='gen-checkmark-circle',
                                    text='Assign', id='ac/'+self._cinfo['name']+'/w/'+str(self._wal.index(x))) if show == 'e' else None),
                                (UI.TipIcon(iconfont='gen-close',
                                    text='Unassign', id='uc/'+self._cinfo['name']+'/w/'+str(self._wal.index(x)),
                                    warning=('Are you sure you wish to unassign this certificate? '
                                        'SSL on this service will be disabled.')) if show == 'd' else None),
                            ),
                        )
                    )
            for x in self._pal:
                if not x.text in alist:
                    if x.text in self._cinfo['assign']:
                        ic, ict, show = 'gen-checkmark-circle', 'Assigned', 'd'
                    else:
                        ic, ict, show = None, None, 'e'
                    ui.find('certassign').append(
                        UI.DTR(
                            UI.IconFont(iconfont=ic, text=ict),
                            UI.IconFont(iconfont=x.iconfont),
                            UI.Label(text=x.text),
                            UI.HContainer(
                                (UI.TipIcon(iconfont='gen-checkmark-circle',
                                    text='Assign', id='ac/'+self._cinfo['name']+'/p/'+str(self._pal.index(x))) if show == 'e' else None),
                                (UI.TipIcon(iconfont='gen-close',
                                    text='Unassign', id='uc/'+self._cinfo['name']+'/p/'+str(self._pal.index(x)),
                                    warning=('Are you sure you wish to unassign this certificate? '
                                        'SSL on this service will be disabled.')) if show == 'd' else None),
                            ),
                        )
                    )
        else:
            ui.remove('dlgInfo')

        if self._upload:
            ui.append('main', UI.DialogBox(
                UI.FormLine(UI.TextInput(name='certname'), text='Name'),
                UI.FormLine(UI.FileInput(id='certfile'), text='Certificate file'),
                UI.FormLine(UI.FileInput(id='keyfile'), text='Certificate keyfile'),
                UI.FormLine(UI.FileInput(id='chainfile'), text='Certificate chainfile', 
                    help='This is optional, only put it if you know you need one.'),
                id='dlgUpload', mp=True))

        return ui

    @url('^/certificates/dl$')
    def download(self, req, start_response):
        params = req['PATH_INFO'].split('/')[3:] + ['']
        filename = CertControl(self.app).get_cas()[0]['name']+'.pem'
        path = os.path.join('/etc/ssl/certs/genesis/ca', filename)
        f = open(path, 'rb')
        size = os.path.getsize(path)
        start_response('200 OK', [
            ('Content-length', str(size)),
            ('Content-Disposition', 'attachment; filename=%s' % filename)
        ])
        return f.read()

    @event('button/click')
    def on_click(self, event, params, vars = None):
        if params[0] == 'info':
            self._tab = 0
            self._cinfo = self.certs[int(params[1])]
        elif params[0] == 'gen':
            self._tab = 0
            self._gen = True
        elif params[0] == 'del':
            self._tab = 0
            self._cc.remove(self.certs[int(params[1])]['name'])
            self.put_message('info', 'Certificate successfully deleted')
        elif params[0] == 'ac' and params[2] == 'p':
            self._tab = 0
            self._cc.assign(self._cinfo['name'], 
                [('plugin', self._pal[int(params[3])])])
            self.put_message('info', '%s added to %s plugin' % (self._cinfo['name'], self._pal[int(params[3])].text))
            self._cinfo = None
        elif params[0] == 'ac' and params[2] == 'w':
            self._tab = 0
            self._cc.assign(self._cinfo['name'],
                [('webapp', self._wal[int(params[3])])])
            self.put_message('info', '%s added to %s webapp' % (self._cinfo['name'], self._wal[int(params[3])].name))
            self._cinfo = None
        elif params[0] == 'ac' and params[2] == 'g':
            self._tab = 0
            self._cc.assign(self._cinfo['name'], [[('genesis')]])
            self.put_message('info', '%s serving as Genesis certificate. Restart Genesis for changes to take effect' % self._cinfo['name'])
            self._cinfo = None
        elif params[0] == 'uc' and params[2] == 'p':
            self._tab = 0
            self._cc.unassign(self._cinfo['name'], 
                [('plugin', self._pal[int(params[3])])])
            self.put_message('info', '%s removed from %s plugin, and SSL disabled.' % (self._cinfo['name'], self._pal[int(params[3])].text))
            self._cinfo = None
        elif params[0] == 'uc' and params[2] == 'w':
            self._tab = 0
            self._cc.unassign(self._cinfo['name'],
                [('webapp', self._wal[int(params[3])])])
            self.put_message('info', '%s removed from %s webapp, and SSL disabled.' % (self._cinfo['name'], self._wal[int(params[3])].name))
            self._cinfo = None
        elif params[0] == 'uc' and params[2] == 'g':
            self._tab = 0
            self._cc.unassign(self._cinfo['name'], [[('genesis')]])
            self.put_message('info', 'Certificate removed and SSL disabled for Genesis. Reload Genesis for changes to take effect')
            self._cinfo = None
        elif params[0] == 'upl':
            self._tab = 0
            self._upload = True
        elif params[0] == 'cagen':
            self._tab = 1
            self._cc.create_authority(self.app.get_backend(IHostnameManager).gethostname().lower())
        elif params[0] == 'cadel':
            self._tab = 1
            self._cc.delete_authority(self.cas[int(params[1])])

    @event('form/submit')
    @event('dialog/submit')
    def on_submit(self, event, params, vars = None):
        if params[0] == 'dlgAdd':
            self._tab = 0
            if vars.getvalue('action', '') == 'OK':
                pass
        elif params[0] == 'dlgGen':
            self._tab = 0
            if vars.getvalue('action', '') == 'OK':
                if vars.getvalue('certname', '') == '':
                    self.put_message('err', 'Certificate name is mandatory')
                elif re.search('\.|-|`|\\\\|\/|[ ]', vars.getvalue('certname')):
                    self.put_message('err', 'Certificate name must not contain spaces, dots, dashes or special characters')
                elif vars.getvalue('certname', '') in [x['name'] for x in self.certs]:
                    self.put_message('err', 'You already have a certificate with that name.')
                elif len(vars.getvalue('certcountry', '')) != 2:
                    self.put_message('err', 'The country field must be a two-letter abbreviation')
                else:
                    lst = []
                    if vars.getvalue('genesis', '') == '1':
                        lst.append([('genesis')])
                    for i in range(0, len(self._wal)):
                        try:
                            if vars.getvalue('wassign[]')[i] == '1':
                                lst.append(('webapp', self._wal[i]))
                        except TypeError:
                            pass
                    for i in range(0, len(self._pal)):
                        try:
                            if vars.getvalue('passign[]')[i] == '1':
                                lst.append(('plugin', self._pal[i]))
                        except TypeError:
                            pass
                    cgw = CertGenWorker(self, vars.getvalue('certname'), vars, lst)
                    cgw.start()
            self._wal = []
            self._pal = []
            self._gen = False
        elif params[0] == 'dlgInfo':
            self._tab = 0
            self._cinfo = None
            self._wal = []
            self._pal = []
        elif params[0] == 'dlgUpload':
            self._tab = 0
            if vars.getvalue('action', '') == 'OK':
                if not vars.has_key('certfile') and not vars.has_key('keyfile'):
                    self.put_message('err', 'Please select at least a certificate and private key')
                elif not vars.has_key('certfile'):
                    self.put_message('err', 'Please select a certificate file')
                elif not vars.has_key('keyfile'):
                    self.put_message('err', 'Please select a key file')
                elif not vars.getvalue('certname', ''):
                    self.put_message('err', 'Must choose a certificate name')
                elif vars.getvalue('certname', '') in [x['name'] for x in self.certs]:
                    self.put_message('err', 'You already have a certificate with that name.')
                elif re.search('\.|-|`|\\\\|\/|[ ]', vars.getvalue('certname')):
                    self.put_message('err', 'Certificate name must not contain spaces, dots, dashes or special characters')
                else:
                    try:
                        self._cc.add_ext_cert(vars.getvalue('certname'), 
                            vars['certfile'].value, vars['keyfile'].value,
                            vars['chainfile'].value if vars.has_key('chainfile') else None)
                        self.put_message('info', 'Certificate %s installed' % vars.getvalue('certname'))
                    except Exception, e:
                        self.put_message('err', 'Couldn\'t add certificate: %s' % str(e[0]))
                        self.app.log.error('Couldn\'t add certificate: %s - Error: %s' % (str(e[0]), str(e[1])))
            self._upload = None
        elif params[0] == 'frmCertSettings':
            self._tab = 1
            if vars.getvalue('action', '') == 'OK':
                cfg = self.app.get_config(CertControl(self.app))
                cfg.keylength = vars.getvalue('keylength', '2048')
                cfg.keytype = vars.getvalue('keytype', 'RSA')
                cfg.ciphers = vars.getvalue('ciphers', '')
                cfg.save()
                self.put_message('info', 'Settings saved successfully')


class CertGenWorker(BackgroundWorker):
    def __init__(self, *args):
        BackgroundWorker.__init__(self, *args)

    def run(self, cat, name, vars, assign):
        cat.put_statusmsg('Generating a certificate and key...')
        try:
            CertControl(cat.app).gencert(name, vars, 
                cat.app.get_backend(IHostnameManager).gethostname().lower())
            cat.put_statusmsg('Assigning new certificate...')
            CertControl(cat.app).assign(name, assign)
        except Exception, e:
            cat.clr_statusmsg()
            cat.put_message('err', str(e))
            cat.app.log.error(str(e))
        cat.clr_statusmsg()
        cat.put_message('info', 'Certificate successfully generated')

########NEW FILE########
__FILENAME__ = main
from genesis.api import *
from genesis.ui import *
from genesis.utils import hashpw
from genesis.plugins.recovery.api import *
from genesis.plugins.core.updater import UpdateCheck
from genesis import apis
from genesis.utils import shell_cs


class ConfigPlugin(CategoryPlugin):
    text = 'Settings'
    iconfont = 'gen-cog'
    folder = False

    def on_session_start(self):
        self._config = None
        self._updstat = (False, '')
        self._update = None

    def get_ui(self):
        ui = self.app.inflate('config:main')

        # General
        ui.find('bind_host').set('value', self.app.gconfig.get('genesis', 'bind_host', ''))
        ui.find('bind_port').set('value', self.app.gconfig.get('genesis', 'bind_port', ''))
        ui.find('dformat').set('value', self.app.gconfig.get('genesis', 'dformat', '%d %b %Y'))
        ui.find('tformat').set('value', self.app.gconfig.get('genesis', 'tformat', '%H:%M'))
        ui.find('ssl').set('text', ('Enabled' if self.app.gconfig.get('genesis', 'ssl', '')=='1' else 'Disabled'))
        ui.find('nofx').set('checked', self.app.gconfig.get('genesis', 'nofx', '')=='1')
        ui.find('updcheck').set('checked', self.app.gconfig.get('genesis', 'updcheck', '')=='1')
        ui.find('purge').set('checked', self.app.gconfig.get('genesis', 'purge', '')=='1')

        # Security
        ui.find('httpauth').set('checked', self.app.gconfig.get('genesis','auth_enabled')=='1')

        # Configs
        cfgs = self.app.grab_plugins(IModuleConfig)
        cfgs = sorted(cfgs, key=lambda config: config.target.__name__ if not hasattr(config.target, 'text') else config.target.text)
        t = ui.find('configs')
        for c in cfgs:
            if c.target:
                t.append(UI.DTR(
                UI.IconFont(iconfont=(None if not hasattr(c.target, 'iconfont') else c.target.iconfont)),
                UI.Label(text=(c.target.__name__ if not hasattr(c.target, 'text') else c.target.text)),
                UI.TipIcon(text='Edit', iconfont="gen-pencil-2", id='editconfig/'+c.target.__name__),
            ))

        # Updates
        self._updstat = UpdateCheck.get().get_status()
        if self._updstat[0] == True:
            ui.find('updstatus').set('text', 'An update for Genesis is available.')
            ui.find('updstatus').set('size', '3')
            ui.find('updaction').set('text', 'Update Now')
            ui.find('updaction').set('iconfont', 'gen-arrow-down-3')
            ui.find('updaction').set('design', 'primary')

        if self._config:
            ui.append('main',
                self.app.get_config_by_classname(self._config).get_ui_edit()
            )

        if self._update is not None:
            pass
        else:
            ui.remove('dlgUpdate')

        if self._changed:
            self.put_message('warn', 'A restart is required for this setting change to take effect.')

        return ui

    @event('button/click')
    def on_click(self, event, params, vars=None):
        if params[0] == 'updaction':
            if self._updstat[0] == False:
                UpdateCheck.get().check_updates(refresh=True)
            else:
                self._update = True
        if params[0] == 'editconfig':
            self._config = params[1]
        if params[0] == 'restart':
            self.app.restart()
        if params[0] == 'shutdown':
            shell('shutdown -P now')
        if params[0] == 'reboot':
            shell('reboot')

    @event('form/submit')
    @event('dialog/submit')
    def on_submit(self, event, params, vars=None):
        if params[0] == 'frmGeneral':
            if vars.getvalue('action', '') == 'OK':
                if self.app.gconfig.get('genesis', 'bind_host', '') != vars.getvalue('bind_host', ''):
                    self._changed = True
                if self.app.gconfig.get('genesis', 'bind_port', '') != vars.getvalue('bind_port', ''):
                    self._changed = True
                self.app.gconfig.set('genesis', 'bind_host', vars.getvalue('bind_host', ''))
                self.app.gconfig.set('genesis', 'bind_port', vars.getvalue('bind_port', '8000'))
                self.app.gconfig.set('genesis', 'dformat', vars.getvalue('dformat', '%d %b %Y'))
                self.app.gconfig.set('genesis', 'tformat', vars.getvalue('tformat', '%H:%M'))
                self.app.gconfig.set('genesis', 'auth_enabled', vars.getvalue('httpauth', '0'))
                self.app.gconfig.set('genesis', 'nofx', vars.getvalue('nofx', '0'))
                self.app.gconfig.set('genesis', 'updcheck', vars.getvalue('updcheck', '1'))
                self.app.gconfig.set('genesis', 'purge', vars.getvalue('purge', '0'))
                self.app.gconfig.save()
                self.put_message('info', 'Settings saved.')
        if params[0] == 'dlgEditModuleConfig':
            if vars.getvalue('action','') == 'OK':
                cfg = self.app.get_config_by_classname(self._config)
                cfg.apply_vars(vars)
                cfg.save()
            self._config = None
        if params[0] == 'dlgUpdate':
            if vars.getvalue('action', '') == 'OK':
                shell('pacman -S --noconfirm genesis')
                self.put_message('err', 'Update complete. Please reboot your system.')
            self._update = None


class GenesisConfig (Plugin):
    implements (IConfigurable)
    name = 'Genesis'
    iconfont = 'gen-arkos-round'
    id = 'genesis'

    def list_files(self):
        return ['/etc/genesis/*']

########NEW FILE########
__FILENAME__ = api
from genesis.com import *
from genesis import apis


class IProgressBoxProvider(Interface):
    """
    Allows your plugin to show a background progress dialog 

    - ``iconfont`` - `str`, iconfont class
    - ``title`` - `str`, text describing current activity
    """
    iconfont = ""
    title = ""
    
    def has_progress(self):
        """
        :returns:       whether this plugin has any currently running activity
        """
        return False
        
    def get_progress(self):
        """
        :returns:       text describing activity's current status
        """
        return ''
        
    def can_abort(self):
        """
        :returns:       whether currently running activity can be aborted
        """
        return False
        
    def abort(self):
        """
        Should abort current activity
        """


class ISSLPlugin(Interface):
    text = ''
    iconfont = ''
    cert_type = 'cert-key'

    def enable_ssl(self):
        pass

    def disable_ssl(self):
        pass


class LangAssist(apis.API):
    def __init__(self, app):
        self.app = app

    class ILangMgr(Interface):
        name = ''

    def get_interface(self, name):
        return filter(lambda x: x.name == name,
            self.app.grab_plugins(apis.langassist.ILangMgr))[0]


class Orders(apis.API):
    def __init__(self, app):
        self.app = app

    class IListener(Interface):
        id = ''

        def order(self, *params):
            pass

    def get_interface(self, name):
        return filter(lambda x: x.id == name,
            self.app.grab_plugins(apis.orders.IListener))

########NEW FILE########
__FILENAME__ = download
import os.path

from genesis.com import *
from genesis.api import URLHandler, url
from genesis.utils import wsgi_serve_file
from genesis.plugmgr import PluginLoader


class Downloader(URLHandler, Plugin):

    @url('^/dl/.+/.+')
    def process_dl(self, req, start_response):
        params = req['PATH_INFO'].split('/', 3)
        self.log.debug('Dispatching download: %s'%req['PATH_INFO'])

        path = PluginLoader.get_plugin_path(self.app, params[2])
        file = os.path.join(path, params[2], 'files', params[3])

        return wsgi_serve_file(req, start_response, file)

    @url('^/htdocs/.+')
    def process_htdocs(self, req, start_response):
        params = req['PATH_INFO'].split('/', 2)
        self.log.debug('Dispatching htdocs: %s'%req['PATH_INFO'])

        path = self.app.config.get('genesis', 'htdocs')
        file = os.path.join(path, params[2])
        file = os.path.normpath(os.path.realpath(file))

        if not file.startswith(path):
            start_response('404 Not Found', [])
            return ''

        return wsgi_serve_file(req, start_response, file)

########NEW FILE########
__FILENAME__ = root
import platform
import json

from genesis.ui import UI
from genesis.com import *
from genesis import version
from genesis.api import ICategoryProvider, EventProcessor, SessionPlugin, event, URLHandler, url, get_environment_vars
from genesis.ui import BasicTemplate
from genesis.utils import ConfigurationError, shell
from api import IProgressBoxProvider


class RootDispatcher(URLHandler, SessionPlugin, EventProcessor, Plugin):
    # Plugin folders. This dict is here forever^W until we make MUI support
    folders = {
        'cluster': 'CLUSTER',
        'system': 'SYSTEM',
        'hardware': 'HARDWARE',
        'apps': 'APPLICATIONS',
        'servers': 'SERVERS',
        'tools': 'TOOLS',
        'advanced': 'ADVANCED',
        'other': 'OTHER',
    }

    # Folder order
    folder_ids = ['cluster', 'apps', 'servers', 'system', 'hardware', 'tools', 'advanced', 'other']

    def on_session_start(self):
        self._cat_selected = 'firstrun' if self.is_firstrun() else 'dashboard'
        self._about_visible = False
        self._module_config = None

    def is_firstrun(self):
        return not self.app.gconfig.has_option('genesis', 'firstrun')

    def main_ui(self):
        self.selected_category.on_init()
        templ = self.app.inflate('core:main')

        if self.app.config.get('genesis', 'nofx', '') != '1':
            templ.remove('fx-disable')

        if self._about_visible:
            templ.append('main-content', self.get_ui_about())

        templ.append('main-content', self.selected_category.get_ui())

        if self.app.session.has_key('messages'):
            for msg in self.app.session['messages']:
                templ.append(
                    'system-messages',
                    UI.SystemMessage(
                        cls=msg[0],
                        text=msg[1],
                    )
                )
            del self.app.session['messages']
        return templ

    def do_init(self):
        # end firstrun wizard
        if self._cat_selected == 'firstrun' and not self.is_firstrun():
            self._cat_selected = 'dashboard'

        cat = None
        for c in self.app.grab_plugins(ICategoryProvider):
            if c.plugin_id == self._cat_selected: # initialize current plugin
                cat = c
        self.selected_category = cat

    def get_ui_about(self):
        ui = self.app.inflate('core:about')
        ui.find('ver').set('text', version())
        return ui

    @url('^/core/progress$')
    def serve_progress(self, req, sr):
        r = []
        rm = []
        if self.app.session.has_key('statusmsg'):
            clear = None
            # Look for new messages pushed to the queue
            for msg in self.app.session['statusmsg']:
                if msg[1]:
                    r.append({
                        'id': msg[0],
                        'type': 'statusbox',
                        'owner': msg[0],
                        'status': msg[1]
                    })
                    clear = False
                    rm.append(msg)
            # Remove messages from queue when they are shown
            for x in rm:
                self.app.session['statusmsg'].remove(x)
            # If a clear command is sent and no messages waiting, clear
            for msg in self.app.session['statusmsg']:
                if clear == None and msg[1] == False:
                    r.append({
                        'id': msg[0],
                        'type': 'statusbox',
                        'owner': msg[0],
                        'status': msg[1]
                    })
                    del self.app.session['statusmsg']
        for p in sorted(self.app.grab_plugins(IProgressBoxProvider)):
            if p.has_progress():
                r.append({
                    'id': p.plugin_id,
                    'type': 'progressbox',
                    'owner': p.title,
                    'status': p.get_progress(),
                    'can_abort': p.can_abort
                })
        return json.dumps(r)

    @url('^/core/styles.less$')
    def serve_styles(self, req, sr):
        r = ''
        for s in sorted(self.app.less_styles):
            r += '@import "%s";\n'%s
        return r
    
    @url('^/$')
    def process(self, req, start_response):
        self.do_init()

        templ = self.app.get_template('index.xml')

        cat = None
        v = UI.VContainer(spacing=0)

        # Sort plugins by name
        cats = self.app.grab_plugins(ICategoryProvider)
        cats = sorted(cats, key=lambda p: p.text)

        for fld in self.folder_ids:
            cat_vc = UI.VContainer(spacing=0)
            if self.folders[fld] == '':
                cat_folder = cat_vc # Omit wrapper for special folders
            else:
                cat_folder = UI.CategoryFolder(
                                cat_vc,
                                text=self.folders[fld],
                                icon='/dl/core/ui/catfolders/'+ fld + '.png'
                                    if self.folders[fld] != '' else '',
                                id=fld
                             )
            # cat_vc will be VContainer or CategoryFolder

            exp = False
            empty = True
            for c in cats:
                if c.folder == fld: # Put corresponding plugins in this folder
                    empty = False
                    if c == self.selected_category:
                        exp = True
                    cat_vc.append(UI.Category(
                        iconfont=c.plugin_info.iconfont if hasattr(c.plugin_info, 'iconfont') else c.iconfont,
                        name=c.text,
                        id=c.plugin_id,
                        counter=c.get_counter(),
                        selected=c == self.selected_category
                    ))

            if not empty: v.append(cat_folder)
            cat_folder['expanded'] = exp

        for c in cats:
            if c.folder in ['top', 'bottom']:
                templ.append(
                    'topplaceholder-'+c.folder,
                    UI.TopCategory(
                        text=c.text,
                        id=c.plugin_id,
                        iconfont=c.iconfont,
                        counter=c.get_counter(),
                        selected=c==self.selected_category
                    )
                )

        templ.append('_head', UI.HeadTitle(text='Genesis @ %s'%platform.node()))
        templ.append('leftplaceholder', v)
        templ.append('version', UI.Label(text='Genesis '+version(), size=2))
        templ.insertText('cat-username', self.app.auth.user)
        templ.appendAll('links', 
                UI.LinkLabel(iconfont='gen-info', text='About', id='about'),
                UI.OutLinkLabel(iconfont='gen-certificate', text='License', url='http://www.gnu.org/licenses/gpl.html')
            )

        return templ.render()

    @url('^/session_reset$')
    def process_reset(self, req, start_response):
        self.app.session.clear()
        start_response('301 Moved Permanently', [('Location', '/')])
        return ''

    @url('^/logout$')
    def process_logout(self, req, start_response):
        self.app.auth.deauth()
        start_response('301 Moved Permanently', [('Location', '/')])
        return ''

    @url('^/embapp/.+')
    def goto_embed(self, req, start_response):
        path = req['PATH_INFO'].split('/')
        host = req['HTTP_HOST']
        bhost = req['HTTP_HOST'].split(':')[0]
        ssl = False

        try:
            if path[3] == 'ssl':
                ssl = True
        except IndexError:
            pass

        content = self.app.inflate('core:embapp')
        content.insertText('ea-port', ':' + path[2])
        content.find('ea-link').set('href', req['wsgi.url_scheme']+'://'+host)
        content.append('ea-frame-container', UI.IFrame(id='ea-frame', 
            src=('https://' if ssl else 'http://')+bhost+':'+path[2]))
        self._cat_selected = 'dashboard'
        return content.render()

    @event('category/click')
    def handle_category(self, event, params, **kw):
        if not isinstance(params, list):
            return
        if len(params) != 1:
            return

        self._cat_selected = 'firstrun' if self.is_firstrun() else params[0]
        self.do_init()

    @event('linklabel/click')
    def handle_linklabel(self, event, params, vars=None):
        if params[0] == 'about':
            self._about_visible = True

    @event('button/click')
    def handle_btns(self, event, params, vars=None):
        if params[0] == 'aborttask':
            for p in self.app.grab_plugins(IProgressBoxProvider):
                if p.plugin_id == params[1] and p.has_progress():
                    p.abort()
        if params[0] == 'gen_reload':
            self.app.restart()
        if params[0] == 'gen_shutdown':
            shell('shutdown -P now')
        if params[0] == 'gen_reboot':
            shell('reboot')

    @event('dialog/submit')
    def handle_dlg(self, event, params, vars=None):
        if params[0] == 'dlgAbout':
            self._about_visible = False

    @url('^/handle/.+')
    def handle_generic(self, req, start_response):
        # Iterate through the IEventDispatchers and find someone who will take care of the event
        # TODO: use regexp for shorter event names, ex. 'btn_clickme/click'
        path = req['PATH_INFO'].split('/')
        event = '/'.join(path[2:4])
        params = path[4:]


        try:
            self.do_init()
            self.selected_category.on_init()
        except ConfigurationError, e:
            # ignore problems if we are leaving the plugin anyway
            if params[0] == self._cat_selected or event != 'category/click':
                raise

        # Current module
        cat = self.app.grab_plugins(ICategoryProvider, lambda x: x.plugin_id == self._cat_selected)[0]

        # Search self and current category for event handler
        vars = get_environment_vars(req)
        for handler in (cat, self):
            if handler.match_event(event):
                result = handler.event(event, params, vars = vars)
                if isinstance(result, str):
                    # For AJAX calls that do not require information
                    # just return ''
                    return result
                if isinstance(result, BasicTemplate):
                    # Useful for inplace AJAX calls (that returns partial page)
                    return result.render()

        # We have no result or handler - return default page
        main = self.main_ui()
        return main.render()

########NEW FILE########
__FILENAME__ = updater
from genesis.api import *
from genesis.plugmgr import RepositoryManager
from genesis.utils import *

import time
import feedparser


class FeedUpdater (Component):
    name = 'updater'

    def on_starting(self):
        self.feed = {}

    def get_feed(self):
        return self.feed

    def run(self):
        rm = RepositoryManager(self.app.log, self.app.config)
        feed_url = feedparser.parse('http://arkos.io/feed')

        while True:
            try:
                self.feed = []
                rm.update_list(crit=True)
                for e in feed_url.entries:
                    self.feed.append({'title': e.title, 'link': e.link, 
                        'time': e.published_parsed})
            except:
                pass
            time.sleep(60*60*12) # check once every 12 hours


class UpdateCheck(Component):
    name = 'updcheck'

    def on_starting(self):
        self.update = False
        self.version = ''

    def get_status(self):
        return (self.update, self.version)

    def check_updates(self, refresh=False):
        if refresh:
            shell('pacman -Sy')
        out = shell('pacman -Qu')
        try:
            for thing in out.split('\n'):
                if not thing.strip():
                    continue
                if thing.split()[0] == 'genesis':
                    self.update = True
                    self.version = thing.split()[1]
        except Exception, e:
            self.app.log.error('Update check failed: ' + str(e))

    def run(self):
        try:
            status = self.app.gconfig.get('genesis', 'updcheck')
        except:
            status = '1'
        if status == '1':
            platform = detect_platform()
            if platform == 'arkos':
                self.check_updates()
                time.sleep(60*60*24) # check once every day

########NEW FILE########
__FILENAME__ = widgets
from genesis.ui import *
from genesis.com import implements, Plugin
from genesis.api import *
from genesis import apis
from updater import FeedUpdater

# We want apis.dashboard already!
import genesis.plugins.sysmon.api


class NewsWidget(Plugin):
    implements(apis.dashboard.IWidget)
    title = 'Project news'
    iconfont = 'gen-bullhorn'
    name = 'Project news'
    style = 'normal'

    def get_ui(self, cfg, id=None):
        ui = self.app.inflate('core:news')
        feed = FeedUpdater.get().get_feed()
        if feed is not '':
            for i in sorted(feed, key=lambda dt: dt['time'], reverse=True):
                ui.append('list', UI.CustomHTML(html='<a href="%s" target="_blank"><li>%s</li></a>'%(i['link'],i['title'])))
        return ui

    def handle(self, event, params, cfg, vars=None):
        pass

    def get_config_dialog(self):
        return None

    def process_config(self, event, params, vars):
        pass

########NEW FILE########
__FILENAME__ = xslt
import base64
import random

from genesis.com import Plugin, implements
from genesis.api import IXSLTFunctionProvider


def attr(_, v, d):
    return d if v == [] or v == ['None'] else v[0]

def css(_, v, d):
    v = d if v == [] or v == ['None'] else v[0]
    if v == 'auto':
            return v
    return v if '%' in v else '%spx'%v

def iif(_, q, a, b):
    return a if (q != False) and ((q == True) or (len(q)>0 and q[0].lower() == 'true')) else b

def jsesc(_, s):
    try:
        return s.replace('\'', '\\')
    except:
        return s[0].replace('\'', '\\')

def idesc(_, s):
    try:
        return s.replace('/', '_').replace('.', '_')
    except:
        return s[0].replace('/', '_').replace('.', '_')

def b64(_, s):
    try:
        return base64.b64encode(str(s[0]))
    except:
        return base64.b64encode(str(s))

def id(_, s):
    if s.__class__ == list and len(s) > 0:
        s = s[0]
    return s if s else str(random.randint(1, 9000*9000))


class CoreFunctions (Plugin):
    implements(IXSLTFunctionProvider)

    def get_funcs(self):
        return {
            'attr' : attr,
            'iif' : iif,
            'b64' : b64,
            'jsesc' : jsesc,
            'idesc' : idesc,
            'css' : css,
            'id' : id
        }

########NEW FILE########
__FILENAME__ = api
from genesis.com import *
from genesis import apis
from genesis.utils import shell_status

from utils import *

class Databases(apis.API):
    def __init__(self, app):
        self.app = app

    class IDatabase(Interface):
        def add(self):
            pass

        def remove(self):
            pass

        def usermod(self):
            pass

        def chperm(self):
            pass

        def execute(self):
            pass

        def get_dbs(self):
            pass

        def get_users(self):
            pass

    def get_dbconn(self, dbtype):
        if self.app.session.has_key('dbconns') and \
        dbtype in self.app.session['dbconns']:
            return self.app.session['dbconns'][dbtype]
        elif self.app.session.has_key('dbconns'):
            return False
        else:
            self.app.session['dbconns'] = {}
            return False

    def clear_dbconn(self, dbtype):
        if self.app.session.has_key('dbconns') and \
        dbtype in self.app.session['dbconns']:
            del self.app.session['dbconns'][dbtype]

    def get_dbtypes(self):
        dblist = []
        for plugin in self.app.grab_plugins(apis.databases.IDatabase):
            active = None
            if plugin.plugin_info.db_task:
                status = shell_status('systemctl is-active %s' % plugin.plugin_info.db_task)
                if status is 0:
                    active = True
                else:
                    active = False
            dblist.append((plugin.plugin_info.db_name, plugin.plugin_info.db_task, active))
        return dblist

    def get_databases(self):
        try:
            dblist = []
            for plugin in self.app.grab_plugins(apis.databases.IDatabase):
                if plugin.plugin_info.multiuser:
                    try:
                        dbconn = self.app.session['dbconns'][plugin.plugin_info.db_name]
                        for item in plugin.get_dbs(dbconn):
                            dblist.append(item)
                    except:
                        pass
                else:
                    for item in plugin.get_dbs():
                        dblist.append(item)
            return dblist
        except DBConnFail:
            return []

    def get_info(self, name):
        return filter(lambda x: x.__class__.__name__ == name,
            self.app.grab_plugins(apis.databases.IDatabase))[0].plugin_info

    def get_interface(self, name):
        return filter(lambda x: x.__class__.__name__ == name,
            self.app.grab_plugins(apis.databases.IDatabase))[0]

    def get_users(self):
        try:
            userlist = []
            for plugin in self.app.grab_plugins(apis.databases.IDatabase):
                if plugin.plugin_info.multiuser:
                    try:
                        dbconn = self.app.session['dbconns'][plugin.plugin_info.db_name]
                        for item in plugin.get_users(dbconn):
                            userlist.append(item)
                    except:
                        pass
            return userlist
        except DBConnFail:
            return []



########NEW FILE########
__FILENAME__ = main
from genesis.api import *
from genesis.ui import *
from genesis import apis

from utils import *


class DatabasesPlugin(apis.services.ServiceControlPlugin):
	text = 'Databases'
	iconfont = 'gen-database'
	folder = 'system'
	services = []

	def on_init(self):
		self.dbops = apis.databases(self.app)
		self.dbs = sorted(self.dbops.get_databases(), 
			key=lambda db: db['name'])
		self.users = sorted(self.dbops.get_users(), 
			key=lambda db: db['name'])
		self.dbtypes = sorted(self.dbops.get_dbtypes(), 
			key=lambda db: db[0])
		for dbtype in self.dbtypes:
			ok = True
			if dbtype[1] == '':
				ok = False
			for svc in self.services:
				if svc['binary'] == dbtype[1]:
					ok = False
			if ok == True:
				self.services.append(
					{
						"name": dbtype[0], 
						"binary": dbtype[1],
						"ports": []
					}
				)

	def on_session_start(self):
		self._tab = 0
		self._add = None
		self._useradd = None
		self._chmod = None
		self._exec = None
		self._execmsg = ''
		self._import = None
		self._input = None
		self._output = None
		self._rootpwds = {}
		self._cancelauth = []

	def get_main_ui(self):
		ui = self.app.inflate('databases:main')
		ui.find('tabs').set('active', self._tab)
		t = ui.find('list')
		ut = ui.find('usrlist')
		st = ui.find('settings')
		tlbr = ui.find('toolbar')

		ubutton = False
		for dbtype in self.dbtypes:
			if dbtype[2] is False:
				self.put_message('err', 'The %s database process is not '
					'running. Your databases/users for this type will not '
					'appear until you start the process.' % dbtype[0])
				self.dbtypes.remove(dbtype)
			else:
				if self.dbops.get_info(dbtype[0]).requires_conn == True and \
				not self.dbops.get_interface(dbtype[0]).checkpwstat():
					self._rootpwds[dbtype[0]] = False
					self.put_message('err', '%s does not have a root password set. '
						'Please add this via the Settings tab.' % dbtype[0])
					ubutton = True
				elif not dbtype[0] in self._cancelauth and \
				self.dbops.get_info(dbtype[0]).requires_conn == True and \
				not self.dbops.get_dbconn(dbtype[0]):
					ui.append('main', 
						UI.InputBox(id='dlgAuth%s' % dbtype[0], 
							text='Enter the database password for %s' 
							% dbtype[0],
							password=True)
					)
					self._rootpwds[dbtype[0]] = True
				elif self.dbops.get_info(dbtype[0]).multiuser == True:
					self._rootpwds[dbtype[0]] = True
					ubutton = True
				else:
					self._rootpwds[dbtype[0]] = True

		for d in self.dbs:
			t.append(UI.DTR(
				UI.Iconfont(iconfont="gen-database"),
				UI.Label(text=d['name']),
				UI.Label(text=d['type']),
				UI.HContainer(
					UI.TipIcon(
						iconfont='gen-target',
						id='exec/' + str(self.dbs.index(d)),
						text='Execute'
					),
					UI.TipIcon(
						iconfont='gen-cancel-circle',
						id='drop/' + str(self.dbs.index(d)),
						text='Delete',
						warning='Are you sure you wish to delete database %s? This may prevent any applications using it from functioning properly.'%d['name']
						)
					),
				))

		for u in self.users:
			ut.append(UI.DTR(
				UI.Iconfont(iconfont="gen-user"),
				UI.Label(text=u['name']),
				UI.Label(text=u['type']),
				UI.HContainer(
					UI.TipIcon(
						iconfont='gen-tools',
						id='chmod/' + str(self.users.index(u)),
						text='Grant/Revoke Permissions'
					),
					UI.TipIcon(
						iconfont='gen-cancel-circle',
						id='deluser/' + str(self.users.index(u)),
						text='Delete',
						warning='Are you sure you wish to delete user %s? This may prevent any applications using it from functioning properly.'%u['name']
						)
					),
				))

		for dbtype in self.dbtypes:
			if self.dbops.get_info(dbtype[0]).multiuser:
				st.append(UI.Label(text=dbtype[0], size='5'))
			if self.dbops.get_info(dbtype[0]).multiuser and dbtype[0] in self._cancelauth:
				st.append(UI.Label(text='You must authenticate before changing these settings.'))
			elif self.dbops.get_info(dbtype[0]).multiuser:
				st.append(UI.SimpleForm(
					UI.Formline(UI.EditPassword(id='newpasswd', value='Click to change'),
						text="New root password"
					),
					UI.Formline(UI.Button(onclick="form", form="frmPasswd%s" % dbtype[0],
						design="primary", action="OK", text="Change Password")),
					id="frmPasswd%s" % dbtype[0]
				))
			if self.dbops.get_info(dbtype[0]).requires_conn:
				st.append(UI.Formline(UI.Button(text='Reauthenticate', id='reauth/'+dbtype[0])))

		type_sel_all = [UI.SelectOption(text = x[0], value = x[0])
			for x in self.dbtypes if x[0] not in self._cancelauth]
		type_sel_multiuser = [UI.SelectOption(text = x[0], value = x[0])
			for x in self.dbtypes if x[0] not in self._cancelauth and \
			self.dbops.get_info(x[0]).multiuser]
		if not type_sel_multiuser:
			ubutton = False

		if self._add is not None and type_sel_all:
			ui.appendAll('type', *type_sel_all)
		else:
			ui.remove('dlgAdd')

		if self._exec is not None:
			edlg = self.app.inflate('databases:execute')
			if self._execmsg:
				edlg.insertText('execmsg', self._execmsg)
				self._execmsg = ''
			if self._input is not None:
				elem = edlg.find('input')
				elem.set('value', self._input)
			if self._output is not None:
				elem = edlg.find('output')
				elem.set('value', self._output)
			ui.append('main', edlg)

		if self._useradd is not None:
			ui.appendAll('usertype', *type_sel_multiuser)
		else:
			ui.remove('dlgAddUser')

		if self._chmod is not None:
			iface = self.dbops.get_interface(self._chmod['type'])
			plist = iface.chperm('', self._chmod['name'], 'check')
			dblist = [UI.SelectOption(text=x['name'], value=x['name'])
					for x in iface.get_dbs()]
			ui.find('permlist').set('value', plist)
			ui.appendAll('dblist', *dblist)
		else:
			ui.remove('dlgChmod')

		if ubutton == True:
			tlbr.append(
				UI.Button(
					id="adduser",
					text="Add user",
					iconfont="gen-user-plus"
					)
				)

		return ui

	@event('button/click')
	def on_click(self, event, params, vars = None):
		if params[0] == 'add':
			if self.dbtypes == []:
				self.put_message('err', 'No database engines installed. Check the Applications tab to find some')
			else:
				self._add = len(self.dbs)
			self._tab = 0
		if params[0] == 'adduser':
			self._useradd = len(self.users)
			self._tab = 1
		if params[0] == 'exec':
			self._exec = self.dbs[int(params[1])]
			self._input = None
			self._output = None
			self._tab = 0
		if params[0] == 'chmod':
			self._chmod = self.users[int(params[1])]
			self._tab = 1
		if params[0] == 'import':
			self._import = True
			self._tab = 0
		if params[0] == 'drop':
			self._tab = 0
			try:
				dt = self.dbs[int(params[1])]
				cls = self.dbops.get_interface(dt['type'])
				if cls.plugin_info.requires_conn:
					cls.remove(dt['name'], self.app.session['dbconns'][dt['type']])
				else:
					cls.remove(dt['name'])
			except Exception, e:
				self.put_message('err', 'Database drop failed: ' + str(e))
				self.app.log.error('Database drop failed: ' + str(e))
			else:
				self.put_message('info', 'Database successfully dropped')
		if params[0] == 'deluser':
			self._tab = 1
			try:
				dt = self.users[int(params[1])]
				iface = self.dbops.get_interface(dt['type'])
				iface.usermod(dt['name'], 'del', '')
			except Exception, e:
				self.put_message('err', 'User drop failed: ' + str(e))
				self.app.log.error('User drop failed: ' + str(e))
			else:
				self.put_message('info', 'User deleted') 
		if params[0] == 'reauth':
			if params[1] in self._cancelauth:
				self._cancelauth.remove(params[1])
			self.dbops.clear_dbconn(params[1])

	@event('form/submit')
	@event('dialog/submit')
	def on_submit(self, event, params, vars = None):
		if params[0] == 'dlgAdd':
			if vars.getvalue('action', '') == 'OK':
				name = vars.getvalue('name', '')
				dbtype = vars.getvalue('type', '')
				if not name or not dbtype:
					self.put_message('err', 'Name or type not selected')
				elif self._rootpwds[dbtype] == False:
					self.put_message('err', 'Please add a root password for this database type via the Settings tab first.')
				else:
					cls = self.dbops.get_interface(dbtype)
					try:
						if cls.plugin_info.requires_conn:
							cls.add(name, self.app.session['dbconns'][dbtype])
						else:
							cls.add(name)
					except Exception, e:
						self.put_message('err', 'Database add failed: ' 
							+ str(e))
						self.app.log.error('Database add failed: ' 
							+ str(e))
					else:
						self.put_message('info', 
							'Database %s added sucessfully' % name)
			self._add = None
		elif params[0] == 'dlgExec':
			if vars.getvalue('action', '') == 'OK':
				self._input = vars.getvalue('input', '')
				iface = self.dbops.get_interface(self._exec['type'])
				try:
					self._output = iface.execute(self._exec['name'], self._input)
				except Exception, e:
					self._execmsg = str(e[1])
			else:
				self._exec = None
		elif params[0] == 'dlgAddUser':
			if vars.getvalue('action', '') == 'OK':
				username = vars.getvalue('username')
				passwd = vars.getvalue('passwd')
				usertype = vars.getvalue('usertype', '')
				if not username or not usertype:
					self.put_message('err', 'Name or type not selected')
				elif self._rootpwds[usertype] == False:
					self.put_message('err', 'Please add a root password for this database type via the Settings tab first.')
				else:
					try:
						iface = self.dbops.get_interface(usertype)
						iface.usermod(username, 'add', passwd)
					except Exception, e:
						self.put_message('err', 'User add failed: '
							+ str(e))
						self.app.log.error('User add failed: '
							+ str(e))
					else:
						self.put_message('info',
							'User %s added successfully' % username)
			self._useradd = None
		elif params[0] == 'dlgChmod':
			if vars.getvalue('action', '') == 'OK':
				action = vars.getvalue('chperm', '')
				dbname = vars.getvalue('dblist', '')
				try:
					iface = self.dbops.get_interface(self._chmod['type'])
					iface.chperm(dbname, self._chmod['name'], action)
				except Exception, e:
					self.put_message('err', 'Permission change failed, see logs')
					self.app.log.error('Permission change failed: '
						+ str(e))
				else:
					self.put_message('info',
						'Permissions for %s changed successfully' % self._chmod['name'])
			self._chmod = None
		elif params[0].startswith('dlgAuth'):
			dbtype = params[0].split('dlgAuth')[1]
			if vars.getvalue('action', '') == 'OK':
				login = vars.getvalue('value', '')
				try:
					self.dbops.get_interface(dbtype).connect(
						store=self.app.session['dbconns'],
						passwd=login)
				except DBAuthFail, e:
					self.put_message('err', str(e))
			else:
				self.put_message('err', 'You refused to authenticate to %s. '
					'You will not be able to perform operations with this database type. '
					'Go to Settings and click Reauthenticate to retry.' % dbtype)
				self._cancelauth.append(dbtype)
		elif params[0].startswith('frmPasswd'):
			dbtype = params[0].split('frmPasswd')[1]
			v = vars.getvalue('newpasswd')
			if v != vars.getvalue('newpasswdb',''):
				self.put_message('err', 'Passwords must match')
			else:
				try:
					if not self.app.session.has_key('dbconns'):
						self.app.session['dbconns'] = {}
					if not self.dbops.get_interface(dbtype).checkpwstat():
						self.dbops.get_interface(dbtype).connect(
							store=self.app.session['dbconns'],
							passwd='')
					self.dbops.get_interface(dbtype).chpwstat(
						vars.getvalue('newpasswd'),
						self.app.session['dbconns'][dbtype]
						)
					self.put_message('info', 'Password for %s changed successfully' % dbtype)
				except Exception, e:
					self.put_message('err', 'Error changing password for %s: %s' % (dbtype, str(e)))
			self._tab = 2

########NEW FILE########
__FILENAME__ = utils
class DBConnFail(Exception):
	def __init__(self, dbtype, op=None):
		self.dbtype = dbtype
		self.op = op

	def __str__(self):
		if self.op:
			return 'The database connection for %s failed, while performing %s' % (self.dbtype, self.op)
		else:
			return 'The database connection for %s failed generally' % self.dbtype


class DBAuthFail(Exception):
	def __init__(self, dbtype):
		self.dbtype = dbtype

	def __str__(self):
		return 'Authentication for %s failed, did you use the correct password?' % self.dbtype


########NEW FILE########
__FILENAME__ = acl
from genesis.utils import *

def get_acls(f):
    ss = shell('getfacl -cp -- "%s"' % f).split('\n')
    r = []
    for s in ss:
        if not s.startswith('#') and not s.startswith('getfacl'):
            try:
                x = [z.strip() for z in s.split(':')]
                x[-1] = x[-1].split()[0]
                r.append((':'.join(x[:-1]), x[-1]))
            except:
                pass
    return r
    
def del_acl(f, acl):
    print shell('setfacl -x %s "%s"'%(acl,f))

def set_acl(f, who, rights):
    print shell('setfacl -m %s:%s "%s"'%(who,rights,f))    

########NEW FILE########
__FILENAME__ = config
from genesis.api import ModuleConfig
from main import *

import os


class GeneralConfig(ModuleConfig):
    target = FMPlugin
    platform = ['any']
    
    labels = {
        'dir': 'Initial directory',
        'showhidden': 'Show hidden files?'
    }
    
    dir = '/'
    showhidden = False
   
    def __init__(self):
        self.dir = os.path.expanduser('~%s' % self.app.auth.user) \
        if hasattr(self.app, 'auth') and self.app.auth.user != 'anonymous' \
        and os.path.isdir(os.path.expanduser('~%s' % self.app.auth.user)) else '/'

########NEW FILE########
__FILENAME__ = main
# coding: utf-8
from genesis.ui import *
from genesis.api import *
from genesis.plugins.core.api import *
from genesis.utils import *
import os
from base64 import b64encode, b64decode
from stat import ST_UID, ST_GID, ST_MODE, ST_SIZE
import grp, pwd
import shutil
import threading
from acl import *
import utils


class FMPlugin(CategoryPlugin, URLHandler):
    text = 'File Manager'
    iconfont = 'gen-files'
    folder = 'tools'

    def on_init(self):
        self._has_acls = shell_status('which getfacl')==0

    def on_session_start(self):
        self._config = self.app.get_config(self)
        self._root = self._config.dir
        self._tabs = []
        self._tab = 0
        self._clipboard = []
        self._cbs = None
        self._renaming = None
        self._newfolder = None
        self._upload = None
        self._redirect = None
        self._archupl = []
        self._showhidden = self._config.showhidden
        self.add_tab()

    def get_ui(self):
        if self._redirect is not None:
            r = self._redirect
            self._redirect = None
            return r

        ui = self.app.inflate('fileman:main')
        tc = UI.TabControl(active=self._tab)

        if self._showhidden:
            ui.find('hidden').set('text', 'Hide hidden')
            ui.find('hidden').set('iconfont', 'gen-eye-blocked')

        idx = 0
        for tab in self._tabs:
            tc.add(tab, content=self.get_tab(tab, tidx=idx), id=str(idx))
            idx += 1
        tc.add('+', None)

        self._clipboard = sorted(self._clipboard)
        idx = 0
        for f in self._clipboard:
            ui.append('clipboard', UI.DTR(
                UI.HContainer(
                    UI.IconFont(iconfont='gen-'+
                        ('folder' if os.path.isdir(f) else 'file')),
                    UI.Label(text=f),
                ),
                UI.TipIcon(
                    iconfont='gen-cancel-circle',
                    text='Remove from clipboard',
                    id='rmClipboard/%i'%idx
                ),
            ))
            idx += 1

        ui.append('main', tc)

        if self._renaming is not None:
            ui.append('main', UI.InputBox(
                text='New name',
                value=os.path.split(self._renaming)[1],
                id='dlgRename'
            ))

        if self._editing_acl is not None:
            dlg = self.app.inflate('fileman:acl')
            ui.append('main', dlg)
            acls = get_acls(self._editing_acl)
            idx = 0
            for acl in acls:
                dlg.append('list', UI.DTR(
                    UI.Editable(id='edAclSubject/%i'%idx, value=acl[0]),
                    UI.Editable(id='edAclPerm/%i'%idx, value=acl[1]),
                    UI.TipIcon(
                        iconfont='gen-cancel-circle',
                        text='Delete',
                        id='delAcl/%i'%idx
                    )
                ))
                idx += 1

        if self._upload:
            ui.append('main', UI.UploadBox(id='dlgUpload', 
                text="Select file(s) to upload",
                location=self._tabs[self._tab]))

        if self._archupl:
            ui.append('main', UI.DialogBox(
                UI.Label(text='The file you just uploaded, %s, appears to be a compressed archive. '
                    'Do you want to extract its contents to %s?' % (self._archupl[0][1], self._archupl[0][0]),
                    lbreak=True, bold=True),
                id='dlgArchUpl', yesno=True))

        if self._newfolder:
            ui.append('main', UI.InputBox(
                text='Enter path for folder',
                value='',
                id='dlgNewFolder'
            ))

        return ui

    def get_tab(self, tab, tidx):
        ui = self.app.inflate('fileman:tab')

        ui.find('paste').set('id', 'paste/%i'%tidx)
        ui.find('newfld').set('id', 'newfld/%i'%tidx)
        ui.find('close').set('id', 'close/%i'%tidx)

        # Is Notepad present?
        notepad = self.can_order('notepad')

        # Generate breadcrumbs
        path = tab
        parts = path.split('/')
        while '' in parts:
            parts.remove('')
        parts.insert(0, '/')

        idx = 0
        for part in parts:
            ui.append('path', UI.Button(
                text=part,
                id='goto/%i/%s' % (
                    tidx,
                    self.enc_file('/'.join(parts[:idx+1])),
                )
            ))
            idx += 1

        # File listing
        try:
            templist = os.listdir(path)
        except:
            templist = []
        lst = []

        for x in sorted(templist):
            if self._showhidden and os.path.isdir(os.path.join(path, x)):
                lst.append(x)
            elif not self._showhidden and not x.startswith('.') \
            and os.path.isdir(os.path.join(path, x)):
                lst.append(x)
        for x in sorted(templist):
            if self._showhidden and not os.path.isdir(os.path.join(path, x)):
                lst.append(x)
            elif not self._showhidden and not x.startswith('.') \
            and not os.path.isdir(os.path.join(path, x)):
                lst.append(x)

        for f in lst:
            np = os.path.join(path, f)
            isdir = os.path.isdir(np)
            islink = os.path.islink(np)
            ismount = os.path.ismount(np)

            iconfont = 'gen-file'
            if isdir: iconfont = 'gen-folder'
            if islink: iconfont ='gen-link'
            if ismount: iconfont = 'gen-storage'

            try:
                stat = os.stat(np)
                mode = stat[ST_MODE]
                size = stat[ST_SIZE]
            except:
                continue

            try:
                user = pwd.getpwuid(stat[ST_UID])[0]
            except:
                user = str(stat[ST_UID])
            try:
                group = grp.getgrgid(stat[ST_GID])[0]
            except:
                group = str(stat[ST_GID])

            name = f
            if islink:
                name += ' → ' + os.path.realpath(np)

            if not isdir:
                tc = ''.join(map(chr, [7,8,9,10,12,13,27] + range(0x20, 0x100)))
                ibs = lambda b: bool(b.translate(None, tc))
                if not notepad or ibs(open(np).read(1024)):
                    item = UI.Label(text=name)
                else:
                    item = UI.LinkLabel(text=name, id='open/%i/%s' % (
                        tidx,
                        self.enc_file(np)
                    ))
            else:
                item = UI.LinkLabel(text=name, id='goto/%i/%s' % (
                    tidx,
                    self.enc_file(np)
                ))
            row = UI.DTR(
                UI.HContainer(
                    UI.Checkbox(name='%i/%s' % (
                        tidx,
                        self.enc_file(np)
                    )),
                    UI.IconFont(iconfont=iconfont),
                ),
                UI.HContainer(
                    item,
                    UI.LinkLabel(
                        text='↗',
                        id='gototab/%i/%s' % (
                            tidx,
                            self.enc_file(np)
                    )) if isdir else None,
                ),
                UI.Label(text=str_fsize(size)),
                UI.Label(text='%s:%s'%(user,group), monospace=True),
                UI.Label(text=self.mode_string(mode), monospace=True),
                UI.HContainer(
                    UI.TipIcon(
                        iconfont='gen-download',
                        text='Download',
                        onclick='window.open("/fm/s/%i/%s", "_blank")'%(
                            tidx,
                            self.enc_file(f)
                        ),
                    ),
                    UI.TipIcon(
                        iconfont='gen-lock',
                        text='ACLs',
                        id='acls/%i/%s'%(
                            tidx,
                            self.enc_file(np)
                        ),
                    ) if self._has_acls else None,
                    UI.TipIcon(
                        iconfont='gen-cancel-circle',
                        text='Delete',
                        warning='Delete %s'%np,
                        id='delete/%i/%s'%(
                            tidx,
                            self.enc_file(np)
                            ),
                        ),
                    )
                )

            ui.append('list', row)
        return ui

    def enc_file(self, path):
        path = path.replace('//','/')
        return b64encode(path, altchars='+-').replace('=', '*')

    def dec_file(self, b64):
        return b64decode(b64.replace('*', '='), altchars='+-')

    def add_tab(self):
        self._tabs.append(self._root)

    def mode_string(self, mode):
        return ('r' if mode & 256 else '-') + \
           ('w' if mode & 128 else '-') + \
           ('x' if mode & 64 else '-') + \
           ('r' if mode & 32 else '-') + \
           ('w' if mode & 16 else '-') + \
           ('x' if mode & 8 else '-') + \
           ('r' if mode & 4 else '-') + \
           ('w' if mode & 2 else '-') + \
           ('x' if mode & 1 else '-')

    @url('^/fm/s/.*$')
    def download(self, req, start_response):
        params = req['PATH_INFO'].split('/')[3:] + ['']
        filename = self.dec_file(params[1])
        path = os.path.join(self._tabs[int(params[0])], filename)
        if os.path.isdir(path):
            t = utils.compress([path])
            size = os.path.getsize(t)
            f = open(t, 'rb')
            start_response('200 OK', [
                ('Content-length', str(size)),
                ('Content-type', 'application/gzip'),
                ('Content-Disposition', 'attachment; filename=%s' % filename+'.tar.gz')
            ])
        else:
            f = open(path, 'rb')
            size = os.path.getsize(path)
            start_response('200 OK', [
                ('Content-length', str(size)),
                ('Content-Disposition', 'attachment; filename=%s' % filename)
            ])
        return f.read()

    @event('tab/click')
    def on_tab_click(self, event, params, vars=None):
        self.add_tab()

    @event('button/click')
    @event('linklabel/click')
    def on_btn_click(self, event, params, vars=None):
        if params[0] == 'hidden':
            self._showhidden = not self._showhidden
            if self.app.auth.user:
                self._config.showhidden = self._showhidden
                self._config.save()
        if params[0] == 'breadcrumb':
            self._tabs[int(params[1])] = self.dec_file(params[2])
        if params[0] == 'goto':
            self._tab = int(params[1])
            self._tabs[self._tab] = self.dec_file(params[2])
        if params[0] == 'gototab':
            self._tab = len(self._tabs)
            self._tabs.append(self.dec_file(params[2]))
        if params[0] == 'open':
            s = self.send_order('notepad', 'open', 
                os.path.join(self._tabs[int(params[1])],self.dec_file(params[2])),
                open=True)
            if s is not None:
                self._redirect = s
        if params[0] == 'rmClipboard':
            self._clipboard.remove(self._clipboard[int(params[1])])
        if params[0] == 'close' and len(self._tabs)>1:
            self._tabs.remove(self._tabs[int(params[1])])
            self._tab = 0
        if params[0] == 'paste':
            self._tab = int(params[1])
            path = self._tabs[int(params[1])]
            self.work(self._cbs, self._clipboard, path)
        if params[0] == 'upload':
            self._upload = True
        if params[0] == 'newfld':
            self._tab = int(params[1])
            self._newfolder = self._tabs[int(params[1])]
        if params[0] == 'delete':
            self._tab = int(params[1])
            f = self.dec_file(params[2])
            try:
                if os.path.isdir(f):
                    shutil.rmtree(f)
                else:
                    os.unlink(f)
                self.put_message('info', 'Deleted %s'%f)
            except Exception, e:
                self.put_message('err', str(e))
        if params[0] == 'download':
            pass
        if params[0] == 'acls':
            self._tab = int(params[1])
            self._editing_acl = self.dec_file(params[2])
        if params[0] == 'delAcl':
            idx = int(params[1])
            del_acl(self._editing_acl, get_acls(self._editing_acl)[idx][0])

    @event('form/submit')
    @event('dialog/submit')
    def on_submit(self, event, params, vars=None):
        if params[0] == 'files':
            act = vars.getvalue('action', '')
            tab = self._tab
            lst = []
            for x in vars:
                if '/' in x and vars.getvalue(x, None) == '1':
                    tab, f = x.split('/')
                    f = self.dec_file(f)
                    lst.append(f)
            if len(lst) > 0:
                if act == 'copy':
                    self._clipboard = lst
                    self._cbs = 'copy'
                if act == 'cut':
                    self._clipboard = lst
                    self._cbs = 'cut'
                if act == 'rename':
                    self._renaming = lst[0]
            self._tab = tab
        if params[0] == 'dlgRename':
            if vars.getvalue('action', None) == 'OK':
                os.rename(self._renaming,
                    os.path.join(
                        os.path.split(self._renaming)[0],
                        vars.getvalue('value', None)
                    ))
            self._renaming = None
        if params[0] == 'dlgAcl':
            self._editing_acl = None
        if params[0] == 'dlgUpload':
            if vars.getvalue('action', '') == 'OK' and vars.has_key('file'):
                files = []
                if type(vars['file']) == list:
                    names = []
                    for x in vars['file']:
                        open(os.path.join(self._tabs[self._tab], x.filename), 'w').write(x.value)
                        names.append(x.filename)
                        files.append((self._tabs[self._tab], x.filename))
                    self.put_message('info', 'Uploaded the following files to %s: %s'
                        % (self._tabs[self._tab], ', '.join(names)))
                else:
                    f = vars['file']
                    open(os.path.join(self._tabs[self._tab], f.filename), 'w').write(f.value)
                    self.put_message('info', 'Uploaded %s to %s'
                        % (f.filename, self._tabs[self._tab]))
                    files.append((self._tabs[self._tab], f.filename))
                for x in files:
                    archives = ['.tar.gz', '.tgz', '.gz', '.tar.bz2', '.tbz2', '.bz2', '.zip']
                    for y in archives:
                        if x[1].endswith(y):
                            self._archupl.append((x[0], x[1], y))
                            break
            self._upload = None
        if params[0] == 'dlgArchUpl':
            f = self._archupl[0]
            if vars.getvalue('action', '') == 'OK':
                try:
                    utils.extract(os.path.join(f[0], f[1]), f[0], False)
                except Exception, e:
                    self.put_message('err', 'Failed to extract %s: %s' % (f[1], str(e)))
            self._archupl.remove(f)
        if params[0] == 'dlgNewFolder':
            if vars.getvalue('action', '') == 'OK' and vars.getvalue('value', ''):
                fld = vars.getvalue('value', '')
                if fld[0] != '/':
                    fld = os.path.join(self._newfolder, fld)
                try:
                    os.makedirs(fld)
                    self.put_message('info', 'Folder(s) created: %s' % fld)
                except Exception, e:
                    self.put_message('err', 'Folder creation failed: %s' % str(e))
            self._newfolder = None
        if params[0] == 'frmAddAcl':
            if vars.getvalue('action', None) == 'OK':
                set_acl(self._editing_acl,
                    vars.getvalue('subject', None),
                    vars.getvalue('perm', None),
                    )
        if params[0] == 'edAclPerm':
            idx = int(params[1])
            set_acl(self._editing_acl, get_acls(self._editing_acl)[idx][0], vars.getvalue('value', None))
        if params[0] == 'edAclSubject':
            idx = int(params[1])
            perm = get_acls(self._editing_acl)[idx][1]
            del_acl(self._editing_acl, get_acls(self._editing_acl)[idx][0])
            set_acl(self._editing_acl, vars.getvalue('value', None), perm)

    def work(self, action, files, target):
        w = FMWorker(self, action, files, target)
        self.app.session['fm_worker'] = w
        w.start()


class FMWorker(BackgroundWorker):
    def __init__(self, *args):
        self.action = ''
        BackgroundWorker.__init__(self, *args)

    def run(self, cat, action, files, target):
        self.action = action
        try:
            for f in files:
                np = os.path.join(target, os.path.split(f)[1])
                if action == 'copy':
                    if (not os.path.isdir(f)) or os.path.islink(f):
                        shutil.copy2(f, np)
                    else:
                        shutil.copytree(f, np, symlinks=True)
                if action == 'cut':
                    os.rename(f, np)
        except Exception, e:
            cat.put_message('err', str(e))

    def get_status(self):
        return self.action


class FMProgress(Plugin):
    implements(IProgressBoxProvider)
    title = 'File manager'
    iconfont = 'gen-files'
    can_abort = True

    def get_worker(self):
        try:
            return self.app.session['fm_worker']
        except:
            return None

    def has_progress(self):
        if self.get_worker() is None:
            return False
        return self.get_worker().alive

    def get_progress(self):
        return self.get_worker().get_status()

    def abort(self):
        if self.has_progress():
            self.get_worker().kill()

########NEW FILE########
__FILENAME__ = utils
import bz2
import gzip
import os
import tarfile
import tempfile
import zipfile


def compress(pin, pout='', format='tgz', delete=False):
    if format == 'tgz':
        pout = tempfile.mkstemp('.tar.gz')[1] if not pout else pout
        a = tarfile.open(pout, 'w:gz')
        for x in pin:
            a.add(x, os.path.split(x)[1])
        a.close()
    elif format == 'zip':
        pout = tempfile.mkstemp('.zip')[1] if not pout else pout
        a = zipfile.ZipFile(pout, 'w')
        for x in pin:
            a.write(x)
        a.close()
    return pout

def extract(pin, pout, delete=False):
    name = os.path.basename(pin)
    if name.endswith(('.tar.gz', '.tgz')):
        t = tarfile.open(pin, 'r:gz')
        t.extractall(pout)
    elif name.endswith('.gz'):
        i = gzip.open(pin, 'rb').read()
        open(os.path.join(pout, name.split('.gz')[0]), 'wb').write(i)
    elif name.endswith(('.tar.bz2', '.tbz2')):
        t = tarfile.open(pin, 'r:bz2')
        t.extractall(f[0])
    elif name.endswith('.bz2'):
        i = bz2.BZ2File(pin, 'r').read()
        open(os.path.join(pout, name.split('.bz2')[0]), 'wb').write(i)
    elif name.endswith('.zip'):
        zipfile.ZipFile(pin, 'r').extractall(pout)
    else:
        raise Exception('Not an archive, or unknown archive type')
    if delete:
        os.unlink(pin)

########NEW FILE########
__FILENAME__ = api
from genesis.com import *
from genesis import apis

from backend import FSControl


class POI(object):
    name = ''
    ptype = ''
    path = ''
    created_by = ''
    remove = True


class POIControl(apis.API):
    pois = []

    def __init__(self, app):
        self.app = app
        self.pois = []
        self.generate_pois()

    def add(self, name, ptype, path, created_by='', remove=True):
        i = POI()
        i.name = name
        i.ptype = ptype
        i.path = path
        i.created_by = created_by
        i.remove = remove
        self.pois.append(i)

    def drop(self, poi):
        self.pois.remove(poi)

    def drop_by_path(self, path):
        for x in self.pois:
            if x.path == path:
                self.drop(x)

    def get_pois(self):
        return self.pois

    def generate_pois(self):
        self.pois = []
        fs = FSControl(self.app).get_filesystems()
        for x in fs[0]:
            if x.mount and not (x.mount == '/' or x.mount.startswith('/boot')):
                self.add(x.name, 'disk', x.mount, 'filesystems', False)
        for x in fs[1]:
            if x.mount and not (x.mount == '/' or x.mount.startswith('/boot')):
                self.add(x.name, 'vdisk', x.mount, 'filesystems', False)

########NEW FILE########
__FILENAME__ = backend
import re
import os
import glob
import shutil

from genesis import apis
from genesis.api import *
from genesis.com import *
from genesis.utils import *

import losetup


class Filesystem(object):
    name = ''
    dev = ''
    img = ''
    fstype = 'disk'
    icon = ''
    size = 0
    mount = ''
    parent = None
    delete = True


class FSControl(Plugin):
    def get_filesystems(self):
        devs, vdevs = [],[]
        fdisk = shell('lsblk -Ppnbo NAME,SIZE,TYPE,MOUNTPOINT,PKNAME').split('\n')
        l = losetup.get_loop_devices()
        l = [l[x] for x in l if l[x].is_used()]

        for x in fdisk:
            if not x.split():
                continue
            x = x.split()
            for y in enumerate(x):
                x[y[0]] = y[1].split('"')[1::2][0]

            f = Filesystem()
            f.name = x[0].split('/')[-1]
            f.dev = x[0]
            f.size = int(x[1])
            f.fstype = x[2]
            if x[2] == 'part':
                f.icon = 'gen-arrow-down'
            elif x[2] == 'rom':
                f.icon = 'gen-cd'
            elif x[2] == 'crypt':
                f.icon = 'gen-lock'
                f.delete = False
            elif x[2] == 'loop':
                f.icon = 'gen-loop-2'
                f.delete = False
            else:
                f.icon = 'gen-storage'
            f.mount = x[3] if len(x) >= 4 else ''
            f.parent = x[4] if len(x) >= 5 else None
            for y in devs:
                if y.dev in f.dev:
                    f.parent = y
                    break
            if f.fstype in ['crypt', 'loop']:
                vdevs.append(f)
            else:
                devs.append(f)

        if not os.path.exists('/vdisk'):
            os.mkdir('/vdisk')
        for x in glob.glob('/vdisk/*.img'):
            f = Filesystem()
            found = False
            for y in l:
                if y.get_filename() == x:
                    for z in vdevs:
                        if z.dev == y.device:
                            found = True
                            z.name = os.path.splitext(os.path.split(x)[1])[0]
                            z.icon = 'gen-embed'
                            z.img = x
                            z.delete = True
            if not found:
                f.name = os.path.splitext(os.path.split(x)[1])[0]
                f.img = x
                f.fstype = 'vdisk'
                f.icon = 'gen-embed'
                f.size = os.path.getsize(x)
                vdevs.append(f)
        for x in glob.glob('/vdisk/*.crypt'):
            f = Filesystem()
            found = False
            for y in l:
                if y.get_filename() == x:
                    for z in vdevs:
                        if z.parent == y.device:
                            found = True
                            z.img = x
                            z.delete = True
                            vdevs.remove([i for i in vdevs if i.dev == z.parent][0])
            if not found:
                f.name = os.path.splitext(os.path.split(x)[1])[0]
                f.img = x
                f.fstype = 'crypt'
                f.icon = 'gen-lock'
                f.size = os.path.getsize(x)
                vdevs.append(f)
        devs = sorted(devs, key=lambda x: x.name)
        vdevs = sorted(vdevs, key=lambda x: x.name)
        return devs, vdevs

    def add_vdisk(self, name, size, mkfs=True, mount=False):
        with open(os.path.join('/vdisk', name+'.img'), 'wb') as f:
            written = 0
            while (int(size)*1048576) > written:
                written += 1024
                f.write(os.urandom(1024))
            f.close()
        if mkfs:
            l = losetup.find_unused_loop_device()
            l.mount(os.path.join('/vdisk', name+'.img'))
            s = shell_cs('mkfs.ext4 %s'%l.device)
            if s[0] != 0:
                raise Exception('Failed to format loop device: %s'%s[1])
            l.unmount()
        fs = Filesystem()
        fs.name = name
        fs.img = os.path.join('/vdisk', name+'.img')
        fs.fstype = 'vdisk'
        if mount:
            self.mount(fs)
        return fs

    def encrypt_vdisk(self, fs, passwd, opts={'cipher': 'aes-xts-plain64', 'keysize': '256', 'hash': 'sha1'}, move=True, mount=False):
        opts = '-c %s -s %s -h %s'%(opts['cipher'], str(opts['keysize']), opts['hash'])
        l = losetup.get_loop_devices()
        if move:
            os.rename(os.path.join('/vdisk', fs.name+'.img'), os.path.join('/vdisk', fs.name+'.crypt'))
        dev = losetup.find_unused_loop_device()
        dev.mount(os.path.join('/vdisk', fs.name+'.crypt'))
        fs.img = os.path.join('/vdisk', fs.name+'.crypt')
        s = shell_cs('echo "%s" | cryptsetup %s luksFormat %s'%(passwd,opts,dev.device), stderr=True)
        if s[0] != 0:
            if move:
                dev.unmount()
                os.rename(os.path.join('/vdisk', fs.name+'.crypt'), os.path.join('/vdisk', fs.name+'.img'))
            raise Exception('Failed to encrypt %s: %s'%(fs.name, s[1]))
        fs.fstype = 'crypt'
        s = shell_cs('echo "%s" | cryptsetup luksOpen %s %s'%(passwd,dev.device,fs.name), stderr=True)
        if s[0] != 0:
            dev.unmount()
            raise Exception('Failed to decrypt %s: %s'%(fs.name, s[1]))
        s = shell_cs('mkfs.ext4 /dev/mapper/%s'%fs.name, stderr=True)
        shell('cryptsetup luksClose %s'%fs.name)
        dev.unmount()
        if s[0] != 0:
            raise Exception('Failed to format loop device: %s'%s[1])
        if mount:
            self.mount(fs, passwd)

    def mount(self, fs, passwd=''):
        if not os.path.isdir(os.path.join('/media', fs.name)):
            os.makedirs(os.path.join('/media', fs.name))
        if fs.fstype in ['crypt', 'vdisk', 'loop']:
            dev = losetup.find_unused_loop_device()
            dev.mount(fs.img)
            if fs.fstype == 'crypt':
                s = shell_cs('echo "%s" | cryptsetup luksOpen %s %s'%(passwd,dev.device,fs.name), stderr=True)
                if s[0] != 0:
                    dev.unmount()
                    raise Exception('Failed to decrypt %s: %s'%(fs.name, s[1]))
                s = shell_cs('mount /dev/mapper/%s %s'%(fs.name, os.path.join('/media', fs.name)), stderr=True)
                if s[0] != 0:
                    shell('cryptsetup luksClose %s'%fs.name)
                    dev.unmount()
                    raise Exception('Failed to mount %s: %s'%(fs.name, s[1]))
            else:
                s = shell_cs('mount %s %s'%(dev.device, os.path.join('/media', fs.name)), stderr=True)
                if s[0] != 0:
                    dev.unmount()
                    raise Exception('Failed to mount %s: %s'%(fs.name, s[1]))
            apis.poicontrol(self.app).add(fs.name, 'vdisk', 
                fs.mount, 'filesystems', False)
        else:
            s = shell_cs('mount %s %s'%(fs.dev, os.path.join('/media', fs.name)), stderr=True)
            if s[0] != 0:
                raise Exception('Failed to mount %s: %s'%(fs.name, s[1]))
            apis.poicontrol(self.app).add(fs.name, 'disk', 
                fs.mount, 'filesystems', False)

    def umount(self, fs, rm=False):
        if not fs.mount:
            return
        if fs.fstype in ['crypt', 'vdisk', 'loop']:
            dev = None
            l = losetup.get_loop_devices()
            for x in l:
                if l[x].is_used() and l[x].get_filename() == fs.img:
                    dev = l[x]
                    break
            if dev and fs.fstype == 'crypt':
                s = shell_cs('umount /dev/mapper/%s'%fs.name, stderr=True)
                if s[0] != 0:
                    raise Exception('Failed to unmount %s: %s'%(fs.name, s[1]))
                shell('cryptsetup luksClose %s'%fs.name)
                dev.unmount()
            elif dev:
                s = shell_cs('umount %s'%dev.device, stderr=True)
                if s[0] != 0:
                    raise Exception('Failed to unmount %s: %s'%(fs.name, s[1]))
                dev.unmount()
        else:
            s = shell_cs('umount %s'%fs.name, stderr=True)
            if s[0] != 0:
                raise Exception('Failed to unmount %s: %s'%(fs.name, s[1]))
        apis.poicontrol(self.app).drop_by_path(fs.mount)
        if rm:
            shutil.rmtree(fs.mount)

    def delete(self, fs):
        self.umount(fs, rm=True)
        if fs.fstype == 'crypt':
            os.unlink(os.path.join('/vdisk', fs.name+'.crypt'))
        else:
            os.unlink(os.path.join('/vdisk', fs.name+'.img'))


class Entry:
    def __init__(self):
        self.src = ''
        self.dst = ''
        self.options = ''
        self.fs_type = ''
        self.dump_p = 0
        self.fsck_p = 0


def read():
    ss = ConfManager.get().load('filesystems', '/etc/fstab').split('\n')
    r = []

    for s in ss:
        if s != '' and s[0] != '#':
            try:
                s = s.split()
                e = Entry()
                try:
                    e.src = s[0]
                    e.dst = s[1]
                    e.fs_type = s[2]
                    e.options = s[3]
                    e.dump_p = int(s[4])
                    e.fsck_p = int(s[5])
                except:
                    pass
                r.append(e)
            except:
                pass

    return r

def save(ee):
    d = ''
    for e in ee:
        d += '%s\t%s\t%s\t%s\t%i\t%i\n' % (e.src, e.dst, e.fs_type, e.options, e.dump_p, e.fsck_p)
    ConfManager.get().save('filesystems', '/etc/fstab', d)
    ConfManager.get().commit('filesystems')

def list_disks():
    r = []
    for s in os.listdir('/dev'):
        if re.match('sd.$|hd.$|scd.$|fd.$|ad.+$', s):
            r.append('/dev/' + s)
    return sorted(r)

def list_partitions():
    r = []
    for s in os.listdir('/dev'):
        if re.match('sd..$|hd..$|scd.$|fd.$', s):
            r.append('/dev/' + s)
    return sorted(r)

def get_disk_vendor(d):
    return ' '.join(shell('hdparm -I ' + d + ' | grep Model').split()[3:])

def get_partition_uuid_by_name(p):
    return shell('blkid -o value -s UUID ' + p).split('\n')[0]

def get_partition_name_by_uuid(u):
    return shell('blkid -U ' + u)


class FSConfigurable (Plugin):
    implements(IConfigurable)
    name = 'Filesystems'
    id = 'filesystems'

    def list_files(self):
        return ['/etc/fstab']

########NEW FILE########
__FILENAME__ = main
import re
import os

from genesis.ui import *
from genesis.com import implements
from genesis.api import *
from genesis.utils import can_be_int, str_fsize

import backend


class FSPlugin(CategoryPlugin):
    text = 'Filesystems'
    iconfont = 'gen-storage'
    folder = 'advanced'

    def on_init(self):
        self.fstab = backend.read()
        self._devs, self._vdevs = self._fsc.get_filesystems()

    def on_session_start(self):
        self._editing = -1
        self._tab = 0
        self._fsc = backend.FSControl(self.app)
        self._add = None
        self._addenc = None
        self._auth = None

    def get_ui(self):
        ui = self.app.inflate('filesystems:main')

        t = ui.find('vdlist')

        for x in self._vdevs:
            t.append(UI.DTR(
                UI.Iconfont(iconfont=x.icon),
                UI.Label(text=x.name),
                UI.Label(text='Encrypted Disk' if x.fstype == 'crypt' else 'Virtual Disk'),
                UI.Label(text=str_fsize(x.size)),
                UI.Label(text=x.mount if x.mount else 'Not Mounted'),
                UI.HContainer(
                    UI.TipIcon(iconfont='gen-key', 
                        text='Encrypt Disk', 
                        id=('ecvd/' + str(self._vdevs.index(x))),
                        warning='Are you sure you wish to encrypt virtual disk %s? This will erase ALL data on the disk, and is irreversible.'%x.name
                    ) if x.fstype != 'crypt' else None,
                    UI.TipIcon(iconfont='gen-arrow-down-3' if x.mount else 'gen-arrow-up-3', 
                        text='Unmount' if x.mount else 'Mount', 
                        id=('umvd/' if x.mount else 'mvd/') + str(self._vdevs.index(x))
                    ) if x.mount != '/' else None,
                    UI.TipIcon(iconfont='gen-cancel-circle', 
                        text='Delete', 
                        id=('delvd/' + str(self._vdevs.index(x))), 
                        warning='Are you sure you wish to delete virtual disk %s?' % (x.name)
                    ) if x.delete else None,
                )
            ))

        t = ui.find('pdlist')

        for x in self._devs:
            if x.fstype == 'disk':
                fstype = 'Physical Disk'
            elif x.fstype == 'rom':
                fstype = 'Optical Disk Drive'
            elif x.fstype == 'part':
                fstype = 'Disk Partition'
            elif x.fstype == 'loop':
                fstype = 'Loopback'
            else:
                fstype = 'Unknown'
            t.append(UI.DTR(
                UI.Iconfont(iconfont=x.icon),
                UI.Label(text=x.name, bold=False if x.parent else True),
                UI.Label(text=fstype),
                UI.Label(text=str_fsize(x.size)),
                UI.HContainer(
                    UI.TipIcon(iconfont='gen-arrow-down-3' if x.mount else 'gen-arrow-up-3', 
                        text='Unmount' if x.mount else 'Mount', 
                        id=('umd/' if x.mount else 'md/') + str(self._devs.index(x))
                    ) if x.mount != '/' and x.fstype != 'disk' else None,
                )
            ))

        t = ui.find('list')

        for u in self.fstab:
            t.append(UI.DTR(
                    UI.Label(text=u.src, bold=True),
                    UI.Label(text=u.dst),
                    UI.Label(text=u.fs_type),
                    UI.Label(text=u.options),
                    UI.Label(text=str(u.dump_p)),
                    UI.Label(text=str(u.fsck_p)),
                    UI.HContainer(
                        UI.TipIcon(iconfont='gen-pencil-2', id='edit/'+str(self.fstab.index(u)), text='Edit'),
                        UI.TipIcon(iconfont='gen-cancel-circle', id='del/'+str(self.fstab.index(u)), text='Delete', warning='Remove %s from fstab'%u.src)
                    ),
                ))

        if self._editing != -1:
            try:
                e = self.fstab[self._editing]
            except:
                e = backend.Entry()
                e.src = '/dev/sda1'
                e.dst = '/tmp'
                e.options = 'none'
                e.fs_type = 'none'
                e.dump_p = 0
                e.fsck_p = 0
            self.setup_ui_edit(ui, e)
        else:
            ui.remove('dlgEdit')

        if self._add:
            ui.append('main', UI.DialogBox(
                UI.FormLine(
                    UI.TextInput(name='addname', id='addname'),
                    text='Virtual disk name'
                ),
                UI.FormLine(
                    UI.TextInput(name='addsize', id='addsize'),
                    text='Disk size (in MB)'
                ),
                UI.FormLine(
                    UI.EditPassword(id='passwd', value='Click to add password'),
                    text='Password'
                ) if self._add == 'enc' else None,
                id='dlgAdd'
            ))

        if self._enc:
            ui.append('main', UI.DialogBox(
                UI.FormLine(
                    UI.EditPassword(id='encpasswd', value='Click to add password'),
                    text='Password'
                ),
                id='dlgEnc'
            ))

        if self._auth:
            ui.append('main', UI.DialogBox(
                UI.FormLine(
                    UI.Label(text=self._auth.name),
                    text='For disk:'
                ),
                UI.FormLine(
                    UI.TextInput(name='authpasswd', password=True),
                    text='Password'
                ), id='dlgAuth'
            ))

        return ui

    def get_ui_sources_list(self, e):
        lst = UI.Select(name='disk')
        cst = True
        for p in backend.list_partitions():
            s = p
            try:
                s += ': %s partition %s' % (backend.get_disk_vendor(p), p[-1])
            except:
                pass
            sel = e != None and e.src == p
            cst &= not sel
            lst.append(UI.SelectOption(value=p, text=s, selected=sel))
        for p in backend.list_partitions():
            u = backend.get_partition_uuid_by_name(p)
            if u != '':
                s = 'UUID=' + u
                sel = e != None and e.src == s
                cst &= not sel
                lst.append(UI.SelectOption(value=s, text=p+': '+u , selected=sel))

        lst.append(UI.SelectOption(text='proc', value='proc', selected=e.src=='proc'))
        cst &= e.src != 'proc'
        lst.append(UI.SelectOption(text='Custom', value='custom', selected=cst))
        return lst, cst

    def setup_ui_edit(self, ui, e):
        opts = e.options.split(',')
        bind = False
        ro = False
        loop = False
        if 'bind' in opts:
            opts.remove('bind')
            bind = True
        if 'ro' in opts:
            opts.remove('ro')
            ro = True
        if 'loop' in opts:
            opts.remove('loop')
            loop = True
        opts = ','.join(opts)

        lst,cst = self.get_ui_sources_list(e)
        ui.append('sources', lst)
        ui.find('src').set('value', e.src if cst else '')
        ui.find('mp').set('value', e.dst)
        ui.find('fs').set('value', e.fs_type)
        ui.find('opts').set('value', e.options)
        ui.find('ro').set('checked', ro)
        ui.find('bind').set('checked', bind)
        ui.find('loop').set('checked', loop)
        ui.find('dump_p').set('value', e.dump_p)
        ui.find('fsck_p').set('value', e.fsck_p)

    @event('button/click')
    @event('linklabel/click')
    def on_click(self, event, params, vars=None):
        if params[0] == 'adisk':
            self._tab = 0
            self._add = 'reg'
        if params[0] == 'aedisk':
            self._tab = 0
            self._add = 'enc'
        if params[0] == 'add':
            self._editing = len(self.fstab)
        if params[0] == 'edit':
            self._editing = int(params[1])
        if params[0] == 'del':
            self.fstab.pop(int(params[1]))
            backend.save(self.fstab)
        if params[0] == 'ecvd':
            self._enc = self._vdevs[int(params[1])]
        if params[0] == 'md':
            self._tab = 1
            try:
                self._fsc.mount(self._devs[int(params[1])])
                self.put_message('info', 'Disk mounted successfully')
            except Exception, e:
                self.put_message('err', str(e))
        if params[0] == 'umd':
            self._tab = 1
            try:
                self._fsc.umount(self._devs[int(params[1])], rm=True)
                self.put_message('info', 'Disk unmounted successfully')
            except Exception, e:
                self.put_message('err', str(e))
        if params[0] == 'mvd':
            if self._vdevs[int(params[1])].fstype == 'crypt':
                self._auth = self._vdevs[int(params[1])]
            else:
                try:
                    self._fsc.mount(self._vdevs[int(params[1])])
                    self.put_message('info', 'Virtual disk mounted successfully')
                except Exception, e:
                    self.put_message('err', str(e))
        if params[0] == 'umvd':
            try:
                self._fsc.umount(self._vdevs[int(params[1])], rm=True)
                self.put_message('info', 'Virtual disk unmounted successfully')
            except Exception, e:
                self.put_message('err', str(e))
        if params[0] == 'delvd':
            try:
                self._fsc.delete(self._vdevs[int(params[1])])
                self.put_message('info', 'Virtual disk deleted successfully')
            except Exception, e:
                self.put_message('err', str(e))

    @event('dialog/submit')
    def on_submit(self, event, params, vars=None):
        if params[0] == 'dlgAdd':
            if vars.getvalue('action', '') == 'OK':
                name = vars.getvalue('addname', '')
                size = vars.getvalue('addsize', '')
                passwd = vars.getvalue('passwd', '')
                if not name or not size:
                    self.put_message('err', 'Must choose a name and size')
                elif name in [x.name for x in self._vdevs]:
                    self.put_message('err', 'You already have a virtual disk with that name')
                elif re.search('\.|-|`|\\\\|\/|[ ]', name):
                    self.put_message('err', 'Disk name must not contain spaces, dots, dashes or special characters')
                elif not can_be_int(size):
                    self.put_message('err', 'Size must be a number in megabytes')
                elif self._add == 'enc' and not passwd:
                    self.put_message('err', 'Must choose a password')
                elif self._add == 'enc' and passwd != vars.getvalue('passwdb', ''):
                    self.put_message('err', 'Passwords must match')
                elif self._add == 'enc':
                    x = self._fsc.add_vdisk(name, size)
                    self._fsc.encrypt_vdisk(x, passwd, mount=True)
                else:
                    self._fsc.add_vdisk(name, size, mount=True)
            self._add = None
        if params[0] == 'dlgEdit':
            v = vars.getvalue('value', '')
            if vars.getvalue('action', '') == 'OK':
                e = backend.Entry()
                if vars.getvalue('disk', 'custom') == 'custom':
                    e.src = vars.getvalue('src', 'none')
                else:
                    e.src = vars.getvalue('disk', 'none')
                e.dst = vars.getvalue('mp', 'none')
                e.fs_type = vars.getvalue('fs', 'none')
                e.options = vars.getvalue('opts', '')
                if vars.getvalue('bind', '0') == '1':
                    e.options += ',bind'
                if vars.getvalue('loop', '0') == '1':
                    e.options += ',loop'
                if vars.getvalue('ro', '0') == '1':
                    e.options += ',ro'
                e.options = e.options.strip(',')
                if e.options.startswith('none,'):
                    e.options = e.options[5:]

                e.dump_p = int(vars.getvalue('dump_p', '0'))
                e.fsck_p = int(vars.getvalue('fsck_p', '0'))
                try:
                    self.fstab[self._editing] = e
                except:
                    self.fstab.append(e)
                backend.save(self.fstab)
            self._editing = -1
        if params[0] == 'dlgAuth':
            if vars.getvalue('action', '') == 'OK':
                try:
                    self._fsc.mount(self._auth, vars.getvalue('authpasswd', ''))
                    self.put_message('info', 'Virtual disk decrypted and mounted successfully')
                except Exception, e:
                    self.put_message('err', str(e))
                self._auth = None
        if params[0] == 'dlgEnc':
            if vars.getvalue('action', '') == 'OK':
                passwd = vars.getvalue('encpasswd', '')
                if passwd != vars.getvalue('encpasswdb', ''):
                    self.put_message('err', 'Passwords must match')
                else:
                    try:
                        self._fsc.umount(self._enc)
                        self._fsc.encrypt_vdisk(self._enc, passwd, mount=True)
                        self.put_message('info', 'Virtual disk encrypted and mounted successfully')
                    except Exception, e:
                        self.put_message('err', str(e))
            self._enc = None

########NEW FILE########
__FILENAME__ = main
import os
import random
import re

from genesis.api import *
from genesis.ui import *
from genesis.utils import *
from genesis.plugmgr import RepositoryManager
from genesis.plugins.network import backend
from genesis.plugins.users.backend import *
from genesis.plugins.sysconfig import zonelist

class FirstRun(CategoryPlugin, URLHandler):
    text = 'First run wizard'
    iconfont = None
    folder = None

    def on_init(self):
        self.nb = backend.Config(self.app)
        self.ub = UsersBackend(self.app)
        self.arch = detect_architecture()

    def on_session_start(self):
        self._step = 1
        self._tree = TreeManager()
        self._reboot = True
        self._username = ''
        self._password = ''

    def get_ui(self):
        ui = self.app.inflate('firstrun:main')
        step = self.app.inflate('firstrun:step%i'%self._step)
        ui.append('content', step)

        if self._step == 4:
            if self.arch[1] != 'Raspberry Pi':
                ui.remove('rpi-ogm')
            if self.arch[1] in ['Unknown', 'General']:
                ui.remove('sdc')
            if self.arch[1] not in ['Cubieboard2', 'Cubietruck']:
                ui.remove('cbb-mac')
            else:
                mac = ':'.join(map(lambda x: "%02x" % x, 
                    [0x54, 0xb3, 0xeb, random.randint(0x00, 0x7f), 
                    random.randint(0x00, 0xff), 
                    random.randint(0x00, 0xff)]))
                ui.find('macaddr').set('value', mac)
            tz_sel = [UI.SelectOption(text = x, value = x,
                        selected = False)
                        for x in zonelist.zones]
            ui.appendAll('zoneselect', *tz_sel)

        if self._step == 5:
            self._mgr = RepositoryManager(self.app.log, self.app.config)
            try:
                self._mgr.update_list(crit=True)
            except Exception, e:
                self.put_message('err', str(e))
                self.app.log.error(str(e))

            lst = self._mgr.available

            for k in sorted(lst, key=lambda x:x.name):
                row = self.app.inflate('firstrun:item')
                row.find('name').set('text', k.name)
                row.find('desc').set('text', k.description)
                row.find('icon').set('class', k.icon)
                row.find('version').set('text', k.version)
                row.find('author').set('text', k.author)
                row.find('author').set('url', k.homepage)

                req = k.str_req()

                row.find('check').set('name', 'install-'+k.id)
                if req != '':
                    row.append('reqs', UI.HelpIcon(text=req))

                ui.append('list', row)

        return ui

    def resize(self, part):
        if part == 1:
            shell_stdin('fdisk /dev/mmcblk0', 'd\nn\np\n1\n\n\nw\n')
        else:
            shell_stdin('fdisk /dev/mmcblk0', 'd\n2\nn\np\n2\n\n\nw\n')
        f = open('/etc/cron.d/resize', 'w')
        f.write('@reboot root resize2fs /dev/mmcblk0p%s\n'%part)
        f.write('@reboot root rm /etc/cron.d/resize\n')
        f.close()
        self.app.gconfig.set('genesis', 'restartmsg', 'yes')
        self.app.gconfig.save()

    @event('form/submit')
    def on_event(self, event, params, vars=None):
        reboot = False
        if params[0] == 'splash':
            self._step = 2
        if params[0] == 'frmChangePassword':
            self._username = vars.getvalue('login', '')
            self._password = vars.getvalue('password', '')
            self._password_again = vars.getvalue('password_again', '')
            if self._username == '':
                self.put_message('err', 'The username can\'t be empty')
            elif self._password == '':
                self.put_message('err', 'The password can\'t be empty')
            elif self._password != self._password_again:
                self.put_message('err', 'The passwords don\'t match')
            elif re.search('[A-Z]|\.|:|[ ]|-$', self._username):
                self.put_message('err', 'Username must not contain capital letters, dots, colons, spaces, or end with a hyphen')
            else:
                # add Unix user
                users = self.ub.get_all_users()
                for u in users:
                    if u.login == self._username:
                        self.put_message('err', 'Duplicate name, please choose another')
                        self._editing = ''
                        return
                self._step = 3
        if params[0] == 'frmChangeRootPassword':
            self._root_password = vars.getvalue('root_password', '')
            self._root_password_again = vars.getvalue('root_password_again', '')
            if self._root_password == '':
                self.put_message('err', 'The password can\'t be empty')
            elif self._root_password != self._root_password_again:
                self.put_message('err', 'The passwords don\'t match')
            else:
                self._step = 4
        if params[0] == 'frmSettings':
            hostname = vars.getvalue('hostname', '')
            zone = vars.getvalue('zoneselect', 'UTC')
            resize = vars.getvalue('resize', '0') if self.arch[1] in ['Cubieboard2', 'Cubietruck', 'Raspberry Pi'] else '0'
            gpumem = vars.getvalue('gpumem', '0') if self.arch[1] == 'Raspberry Pi' else '0'
            macaddr = vars.getvalue('macaddr', '') if self.arch[1] in ['Cubieboard2', 'Cubietruck'] else ''
            ssh_as_root = vars.getvalue('ssh_as_root', '0')

            if not hostname:
                self.put_message('err', 'Hostname must not be empty')
                return
            elif not re.search('^[a-zA-Z0-9.-]', hostname) or re.search('(^-.*|.*-$)', hostname):
                self.put_message('err', 'Hostname must only contain '
                    'letters, numbers, hyphens or periods, and must '
                    'not start or end with a hyphen.')
                return
            else:
                self.nb.sethostname(hostname)
            
            if resize != '0':
                reboot = self.resize(2 if self.arch[1] == 'Raspberry Pi' else 1)
                self.put_message('info', 'Remember to restart your arkOS node after this wizard. To do this, click "Settings > Reboot".')
           
            if ssh_as_root != '0':
                shell('sed -i "/PermitRootLogin no/c\PermitRootLogin yes" /etc/ssh/sshd_config')
            else:
                shell('sed -i "/PermitRootLogin yes/c\PermitRootLogin no" /etc/ssh/sshd_config')

            if gpumem != '0':
                shell('mount /dev/mmcblk0p1 /boot')
                if os.path.exists('/boot/config.txt'):
                    shell('sed -i "/gpu_mem=/c\gpu_mem=16" /boot/config.txt')
                else:
                    shell('echo "gpu_mem=16" >> /boot/config.txt')

            if macaddr != '' and self.arch[1] == 'Cubieboard2':
                open('/boot/uEnv.txt', 'w').write('extraargs=mac_addr=%s\n'%macaddr)
            elif macaddr != '' and self.arch[1] == 'Cubietruck':
                open('/etc/modprobe.d/gmac.conf', 'w').write('options sunxi_gmac mac_str="%s"\n'%macaddr)

            zone = zone.split('/')
            if len(zone) > 1:
                zonepath = os.path.join('/usr/share/zoneinfo', zone[0], zone[1])
            else:
                zonepath = os.path.join('/usr/share/zoneinfo', zone[0])
            if os.path.exists('/etc/localtime'):
                os.remove('/etc/localtime')
            os.symlink(zonepath, '/etc/localtime')
            self._step = 5
        if params[0] == 'frmPlugins':
            lst = self._mgr.available

            toinst = []

            for k in lst:
                if vars.getvalue('install-'+k.id, '0') == '1':
                    toinst.append(k.id)

            t = self._mgr.list_available()
            for y in toinst:
                for i in t[y].deps:
                    for dep in i[1]:
                        if dep[0] == 'plugin' and dep[1] not in toinst:
                            self.put_message('err', ('%s can\'t be installed, as it depends on %s. Please '
                                'install that also.' % (t[y].name, t[dep[1]].name)))
                            return

            for k in lst:
                if vars.getvalue('install-'+k.id, '0') == '1':
                    try:
                        self._mgr.install(k.id)
                    except:
                        pass
            ComponentManager.get().rescan()
            ConfManager.get().rescan();

            self.app.gconfig.set('genesis', 'firstrun', 'no')
            self.app.gconfig.save()
            self.put_message('info', 'Setup complete!')

            # change root password, add Unix user, and allow sudo use
            self.ub.change_user_password('root', self._root_password)            
            self.ub.add_user(self._username)
            self.ub.change_user_password(self._username, self._password)
            sudofile = open('/etc/sudoers', 'r+')
            filedata = sudofile.readlines()
            filedata = ["%sudo ALL=(ALL) ALL\n" if "# %sudo" in line else line for line in filedata]
            sudofile.close()
            sudofile = open('/etc/sudoers', 'w')
            for thing in filedata:
                sudofile.write(thing)
            sudofile.close()
            self.ub.add_group('sudo')
            self.ub.add_to_group(self._username, 'sudo')

            # add user to Genesis config
            self.app.gconfig.remove_option('users', 'admin')
            self.app.gconfig.set('users', self._username, hashpw(self._password))
            self.app.gconfig.save()
            self._step = 6

########NEW FILE########
__FILENAME__ = api
from genesis.com import *
from genesis.api import *
from genesis import apis


class INetworkConfig(Interface):
    interfaces = None
    
    def save(self):
        pass

"""
    def up(self, iface):
        pass

    def down(self, iface):
        pass

    def get_ui_info(self, iface):
        pass
        
    def get_tx(self, iface):
        pass

    def get_rx(self, iface):
        pass

    def get_ip(self, iface):
        pass

    def detect_dev_class(self, iface):
        pass

"""

class IConnConfig(Interface):
    connections = None

    def save(self):
        pass

    
class INetworkConfigBit(Interface):
    def get_ui(self):
        pass

    def apply(self, vars):
        pass


class NetworkConfigBit(Plugin):
    implements(INetworkConfigBit)
    multi_instance = True

    cls = 'unknown'
    iface = None
    title = 'Unknown'

    autovars = []
    
    def __init__(self):
        self.params = {}

    def get_ui(self):
        pass

    def apply(self, vars):
        for k in self.autovars:
            if vars.getvalue(k, None) is not None:
                self.iface[k] = vars.getvalue(k, '')
                if self.iface[k] == '':
                    del self.iface.params[k]


class NetworkInterface(object):
    def __init__(self):
        self.up = False
        self.auto = False
        self.name = ''
        self.devclass = ''
        self.addressing = 'static'
        self.bits = []
        self.params = {'address': '0.0.0.0'}
        self.type = ''
        self.editable = True
        
    def __getitem__(self, idx):
        if self.params.has_key(idx):
            return self.params[idx]
        else:
            return ''

    def __setitem__(self, idx, val):
        self.params[idx] = val
        
    def get_bits(self, app, bits):
        for x in bits:
            try:
                b = app.grab_plugins(INetworkConfigBit,\
                        lambda p: p.cls == x)[0]
                b.iface = self
                self.bits.append(b)
            except:
                pass


class NetworkConnection(object):
    def __init__(self):
        self.up = False
        self.auto = False
        
    def __getitem__(self, idx):
        if self.params.has_key(idx):
            return self.params[idx]
        else:
            return ''

    def __setitem__(self, idx, val):
        self.params[idx] = val      


class IDNSConfig(Interface):
    nameservers = None

    def save(self):
        pass


class Nameserver:
    cls = ''
    address = ''

########NEW FILE########
__FILENAME__ = backend
import re
import os

from genesis.api import *
from genesis.utils import *
from genesis.com import *
from genesis import apis


class Host:
    def __init__(self):
        self.ip = '';
        self.name = '';
        self.aliases = '';


class Config(Plugin):
    implements(IConfigurable)
    name = 'Hosts'
    iconfont = 'gen-screen'
    id = 'hosts'

    def list_files(self):
        return ['/etc/hosts']

    def read(self):
        ss = ConfManager.get().load('hosts', '/etc/hosts').split('\n')
        r = []

        for s in ss:
            if s != '' and s[0] != '#':
                try:
                    s = s.split()
                    h = Host()
                    try:
                        h.ip = s[0]
                        h.name = s[1]
                        for i in range(2, len(s)):
                            h.aliases += '%s ' % s[i]
                        h.aliases = h.aliases.rstrip();
                    except:
                        pass
                    r.append(h)
                except:
                    pass

        return r

    def save(self, hh):
        d = ''
        for h in hh:
            d += '%s\t%s\t%s\n' % (h.ip, h.name, h.aliases)
        ConfManager.get().save('hosts', '/etc/hosts', d)
        ConfManager.get().commit('hosts')

    def gethostname(self):
        return self.app.get_backend(IHostnameManager).gethostname()

    def sethostname(self, hn):
        self.app.get_backend(IHostnameManager).sethostname(hn)



class IHostnameManager(Interface):
    def gethostname(self):
        pass

    def sethostname(self, hn):
        pass


class LinuxGenericHostnameManager(Plugin):
    implements(IHostnameManager)
    platform = ['debian']

    def gethostname(self):
        return open('/etc/hostname').read()

    def sethostname(self, hn):
        open('/etc/hostname', 'w').write(hn)


class ArchHostnameManager(Plugin):
    implements(IHostnameManager)
    platform = ['arch', 'arkos']

    def gethostname(self):
        return open('/etc/hostname').read().rstrip('\n')

    def sethostname(self, hn):
        open('/etc/hostname', 'w').write(hn)


class BSDHostnameManager(Plugin):
    implements(IHostnameManager)
    platform = ['freebsd']

    def gethostname(self):
        return apis.rcconf.RCConf(self.app).get_param('hostname')

    def sethostname(self, hn):
        apis.rcconf.RCConf(self.app).set_param('hostname', hn, near='hostname')


class CentOSHostnameManager(Plugin):
    implements(IHostnameManager)
    platform = ['centos', 'fedora', 'mandriva']

    def gethostname(self):
        rc = apis.rcconf.RCConf(self.app)
        rc.file = '/etc/sysconfig/network'
        return rc.get_param('HOSTNAME')

    def sethostname(self, hn):
        rc = apis.rcconf.RCConf(self.app)
        rc.file = '/etc/sysconfig/network'
        rc.set_param('HOSTNAME', hn, near='HOSTNAME')


class GentooHostnameManager(Plugin):
    implements(IHostnameManager)
    platform = ['gentoo']

    def gethostname(self):
        rc = apis.rcconf.RCConf(self.app)
        rc.file = '/etc/conf.d/hostname'
        return rc.get_param('hostname')

    def sethostname(self, hn):
        rc = apis.rcconf.RCConf(self.app)
        rc.file = '/etc/conf.d/hostname'
        rc.set_param('hostname', hn, near='hostname')
        

########NEW FILE########
__FILENAME__ = control
from genesis.com import *
from genesis.api import *
from genesis.plugins.security.firewall import RuleManager, FWMonitor

from servers import *


class NetworkControl(apis.API):
    # Convenience functions for routine synchronized ops
    def __init__(self, app):
        self.app = app

    def session_start(self):
        servers = ServerManager(self.app)
        servers.add('arkos', 'genesis', 'Genesis', 'gen-arkos-round',
            [('tcp', self.app.gconfig.get('genesis', 'bind_port'))])
        servers.add('arkos', 'beacon', 'Beacon', 'gen-arkos-round',
            [('tcp', '8765')])
        servers.scan_plugins()
        servers.scan_webapps()
        RuleManager(self.app).scan_servers()
        FWMonitor(self.app).regen()
        FWMonitor(self.app).save()

    def add_webapp(self, d):
        servers = ServerManager(self.app)
        s = servers.add('webapps', d[0], 
            d[0] + ' (' + d[1] + ')', 'gen-earth', 
            [('tcp', d[2])])
        RuleManager(self.app).set(s, 2)
        FWMonitor(self.app).regen()
        FWMonitor(self.app).save()

    def change_webapp(self, oldsite, newsite):
        servers = ServerManager(self.app)
        rm = RuleManager(self.app)
        s = servers.get(oldsite.name)[0]
        r = rm.get(s)
        rm.remove(s)
        servers.update(oldsite.name, newsite.name, 
            newsite.name + ' (' + newsite.stype + ')',
            'gen-earth', [('tcp', newsite.port)])
        rm.set(s, r)
        FWMonitor(self.app).regen()
        FWMonitor(self.app).save()

    def remove_webapp(self, sid):
        servers = ServerManager(self.app)
        s = servers.get(sid)
        if s:
            s = s[0]
        else:
            return
        RuleManager(self.app).remove(s)
        servers.remove(sid)
        FWMonitor(self.app).regen()
        FWMonitor(self.app).save()

    def port_changed(self, s):
        sm = ServerManager(self.app)
        rm = RuleManager(self.app)
        for p in s.services:
            try:
                if p['ports'] != [] and sm.get(p['binary']) != []:
                    sg = sm.get(p['binary'])[0]
                    r = rm.get(sg)
                    rm.remove(sg)
                    sm.update(p['binary'], p['binary'], p['name'], 
                        s.iconfont, p['ports'])
                    rm.set(sg, r)
                elif p['ports'] != []:
                    sg = sm.get(p['binary'])[0]
                    sm.add(s.plugin_id, p['binary'], p['name'], 
                        s.iconfont, p['ports'])
                    rm.set(sg, 2)
                FWMonitor(self.app).regen()
                FWMonitor(self.app).save()
            except IndexError:
                continue

    def refresh(self):
        servers = ServerManager(self.app)
        servers.scan_plugins()
        RuleManager(self.app).scan_servers()
        FWMonitor(self.app).regen()
        FWMonitor(self.app).save()

    def remove(self, id):
        servers = ServerManager(self.app)
        if servers.get_by_plugin(id) != []:
            RuleManager(self.app).remove_by_plugin(id)
            servers.remove_by_plugin(id)
            FWMonitor(self.app).regen()
            FWMonitor(self.app).save()

########NEW FILE########
__FILENAME__ = dns_resolvconf
from genesis.api import *
from genesis.com import *
from genesis.utils import *

from api import *


class ResolvConfDNSConfig(Plugin):
    implements(IDNSConfig)
    platform = ['debian', 'arch', 'arkos', 'freebsd', 'centos', 'fedora', 'gentoo', 'mandriva']
    name = 'DNS'
    id = 'dns'
    
    nameservers = None

    def __init__(self):
        self.nameservers = []

        try:
            ss = ConfManager.get().load('dns', '/etc/resolv.conf')
            ss = ss.splitlines()
        except IOError, e:
            return

        for s in ss:
            if len(s) > 0:
                if s[0] != '#':
                    s = s.split(' ')
                    ns = Nameserver()
                    ns.cls = s[0]
                    ns.address = ' '.join(s[1:])
                    self.nameservers.append(ns)

    def save(self):
        s = ''
        for i in self.nameservers:
            s += i.cls + ' ' + i.address + '\n'
        ConfManager.get().save('dns', '/etc/resolv.conf', s)
        ConfManager.get().commit('dns')
        

class DNSConfig (Plugin):
    implements(IConfigurable)
    name = 'DNS'
    id = 'dns'
    
    def list_files(self):
        return ['/etc/resolv.conf']
    

########NEW FILE########
__FILENAME__ = main
from genesis.ui import *
from genesis.api import CategoryPlugin, event
from genesis.utils import *

import backend
import re

from api import *


class NetworkPlugin(CategoryPlugin):
    text = 'Networks'
    iconfont = 'gen-network'
    folder = None

    def on_init(self):
        be = backend.Config(self.app)
        self.hosts = be.read()
        self.dns_config = self.app.get_backend(IDNSConfig)
        self.net_config = self.app.get_backend(INetworkConfig)
        self.conn_config = self.app.get_backend(IConnConfig)

    def on_session_start(self):
        self._tab = 0
        self._editing_iface = ""
        self._editing_conn = None
        self._editing = None
        self._editing_ns = None
        self._newconn = None
        
    def get_ui(self):
        self.ifacelist = []
        ui = self.app.inflate('network:main')
        ui.find('tabs').set('active', self._tab)

        """
        Network Config
        """
        cl = ui.find('connlist')
        for x in self.conn_config.connections:
            i = self.conn_config.connections[x]
            cl.append(UI.DTR(
                UI.HContainer(
                    UI.IconFont(iconfont=('gen-checkmark-circle' if i.up else ''),
                        text=('Connected' if i.up else ''),
                    ),
                    UI.Label(text=' '),
                    UI.IconFont(iconfont=('gen-link' if i.enabled else ''),
                        text=('Enabled' if i.enabled else ''),
                    ),
                ),
                UI.Label(text=i.name),
                UI.Label(text=i.devclass),
                UI.Label(text=(i.addressing+' (%s)' % self.net_config.get_ip(i.interface)) if i.up else i.addressing),
                UI.HContainer(
                    UI.TipIcon(iconfont='gen-pencil-2',
                        text='Edit', id='editconn/' + i.name),
                    UI.TipIcon(iconfont='gen-%s'%('checkmark-circle' if not i.up else 'minus-circle'), 
                        text=('Disconnect' if i.up else 'Connect'), 
                        id=('conn' + ('down' if i.up else 'up') + '/' + i.name), 
                        warning='Are you sure you wish to %s %s? This may interrupt your session.' % (('disconnect from' if i.up else 'connect to'), i.name)),
                    UI.TipIcon(iconfont='gen-%s'%('link' if not i.enabled else 'link-2'), 
                        text=('Disable' if i.enabled else 'Enable'), 
                        id=('conn' + ('disable' if i.enabled else 'enable') + '/' + i.name)),
                    UI.TipIcon(iconfont='gen-cancel-circle', 
                        text='Delete', 
                        id=('delconn/' + i.name), 
                        warning='Are you sure you wish to delete %s? This is permanent and may interrupt your session.' % (i.name))
                    ),
               ))

        nl = ui.find('devlist')
        for x in self.net_config.interfaces:
            i = self.net_config.interfaces[x]
            ip = self.net_config.get_ip(i.name)
            tx, rx = self.net_config.get_tx(i), self.net_config.get_rx(i)
            nl.append(UI.DTR(
                UI.HContainer(
                    UI.IconFont(iconfont='gen-%s'%('checkmark-circle' if i.up else ''),
                        text=('Up' if i.up else '')
                    ),
                ),
                UI.Label(text=i.name),
                UI.Label(text=i.devclass),
                UI.Label(text=(ip if ip != '0.0.0.0' else 'none')),
                UI.Label(text=(str_fsize(tx) if tx else '-')),
                UI.Label(text=(str_fsize(rx) if rx else '-')),
                UI.HContainer(
                    UI.TipIcon(iconfont='gen-%s'%('checkmark-circle' if not i.up else 'cancel-circle'), 
                        text=('Down' if i.up else 'Up'), 
                        id=('if' + ('down' if i.up else 'up') + '/' + i.name), 
                        warning='Are you sure you wish to bring %s interface %s? This may interrupt your session.' % (('down' if i.up else 'up'), i.name)
                    ),
                    UI.TipIcon(iconfont='gen-%s'%('link' if not i.enabled else 'link-2'), 
                        text=('Disable' if i.enabled else 'Enable'), 
                        id=('if' + ('disable' if i.enabled else 'enable') + '/' + i.name))
                    ),
               ))
            self.ifacelist.extend(i.name)

        c = ui.find('conn')
        if self._newconn == True:
            c.append(
                UI.DialogBox(
                    UI.FormLine(
                        UI.SelectInput(
                            UI.SelectOption(value="ethernet", text="Wired (Ethernet)"),
                            UI.SelectOption(value="wireless", text="Wireless"),
                            id="devclass", name="devclass"
                        ),
                        text="Network type"
                    ),
                    UI.FormLine(
                        UI.SelectInput(
                            UI.SelectOption(value="dhcp", text="Automatic (DHCP)"),
                            UI.SelectOption(value="static", text="Manual (Static)"),
                            id="addressing", name="addressing"
                        ),
                        text="Addressing"
                    ), id="dlgNewConn"
                ))

        if self._editing_conn and type(self._editing_conn) == dict:
            ifaces_list = [x for x in self.net_config.interfaces]
            ui.appendAll('interface', 
                *[UI.SelectOption(id='iface-'+x, text=x, value=x) for x in ifaces_list if x != 'lo'])
            if self._editing_conn['devclass'] == 'ethernet':
                ui.find('dc-ethernet').set('selected', True)
                ui.find('devclass').set('disabled', True)
                ui.remove('fl-security')
                ui.remove('fl-essid')
                ui.remove('fl-key')
                if 'eth0' in ifaces_list:
                    ui.find('iface-eth0').set('selected', True)
            elif self._editing_conn['devclass'] == 'wireless':
                ui.find('dc-wireless').set('selected', True)
                ui.find('devclass').set('disabled', True)
                if 'wlan0' in ifaces_list:
                    ui.find('iface-wlan0').set('selected', True)
            if self._editing_conn['addressing'] == 'dhcp':
                ui.find('ad-dhcp').set('selected', True)
                ui.find('addressing').set('disabled', True)
                ui.remove('fl-address')
                ui.remove('fl-gateway')
            elif self._editing_conn['addressing'] == 'static':
                ui.find('ad-static').set('selected', True)
                ui.find('addressing').set('disabled', True)
        elif self._editing_conn and self._editing_conn != True:
            ifaces_list = [x for x in self.net_config.interfaces]
            ui.appendAll('interface', 
                *[UI.SelectOption(id='iface-'+x, text=x, value=x) for x in ifaces_list if x != 'lo'])
            ce = self._editing_conn
            ui.find('connname').set('value', ce.name)
            ui.find('connname').set('disabled', True)
            ui.find('dc-%s' % ce.devclass).set('selected', True)
            ui.find('iface-%s' % ce.interface).set('selected', True)
            ui.find('description').set('value', ce.description)
            ui.find('ad-%s' % ce.addressing).set('selected', True)
            ui.find('address').set('value', ce.address if ce.address else '')
            ui.find('gateway').set('value', ce.gateway if ce.gateway else '')
            if ce.devclass == 'wireless':
                ui.find('se-%s' % ce.security).set('selected', True)
                ui.find('essid').set('value', ce.essid if ce.essid else 'Unknown')
                if ce.security != 'none' and ce.security != 'wpa-configsection':
                    ui.find('key').set('value', ce.key if ce.key else '')
        else:
            ui.remove('dlgEditConn')


        """
        Hosts Config
        """
        ht = ui.find('hostlist')
        for h in self.hosts:
            ht.append(UI.DTR(
                UI.Label(text=h.ip),
                UI.Label(text=h.name),
                UI.Label(text=h.aliases),
                UI.HContainer(
                    UI.TipIcon(
                        iconfont='gen-pencil-2',
                        id='edit/' + str(self.hosts.index(h)),
                        text='Edit'
                    ),
                    UI.TipIcon(
                        iconfont='gen-cancel-circle',
                        id='del/' + str(self.hosts.index(h)),
                        text='Delete',
                        warning='Are you sure you wish to remove %s from the list of hosts?'%h.ip
                    )
                ),
            ))

        if self._editing != None:
            h = self.hosts[self._editing] if self._editing < len(self.hosts) else backend.Host()
            ui.find('ip').set('value', h.ip)
            ui.find('name').set('value', h.name)
            ui.find('aliases').set('value', h.aliases)
        else:
            ui.remove('dlgEdit')


        """
        DNS Config
        """
        td = ui.find('list')
        for x in range(0, len(self.dns_config.nameservers)):
            i = self.dns_config.nameservers[x]
            td.append(UI.DTR(
                UI.Label(text=i.cls),
                UI.Label(text=i.address),
                UI.HContainer(
                    UI.TipIcon(iconfont='gen-pencil-2', text='Edit', id='editns/' + str(x)),
                    UI.TipIcon(iconfont='gen-close', text='Remove', id='delns/' + str(x))
                ),
            ))

        if self._editing_ns != None:
            ns = self.dns_config.nameservers[self._editing_ns] if self._editing_ns < len(self.dns_config.nameservers) else Nameserver()
            classes = ['nameserver', 'domain', 'search', 'sortlist', 'options']
            for c in classes:
                e = ui.find('cls-' + c)
                e.set('value', c)
                e.set('selected', ns.cls==c)
            ui.find('value').set('value', ns.address)
        else:
            ui.remove('dlgEditDNS')

        return ui

    @event('button/click')
    @event('linklabel/click')
    def on_ll_click(self, event, params, vars=None):
        if params[0] == 'ifup':
            self._tab = 0
            self.net_config.up(self.net_config.interfaces[params[1]])
            self.net_config.rescan()
        if params[0] == 'ifdown':
            self._tab = 0
            self.net_config.down(self.net_config.interfaces[params[1]])
            self.net_config.rescan()
        if params[0] == 'ifenable':
            self._tab = 0
            self.net_config.enable(self.net_config.interfaces[params[1]])
            self.net_config.rescan()
        if params[0] == 'ifdisable':
            self._tab = 0
            self.net_config.disable(self.net_config.interfaces[params[1]])
            self.net_config.rescan()
        if params[0] == 'connup':
            self._tab = 0
            self.conn_config.connup(self.conn_config.connections[params[1]])
        if params[0] == 'conndown':
            self._tab = 0
            self.conn_config.conndown(self.conn_config.connections[params[1]])
        if params[0] == 'connenable':
            self._tab = 0
            self.conn_config.connenable(self.conn_config.connections[params[1]])
            self.conn_config.rescan()
        if params[0] == 'conndisable':
            self._tab = 0
            self.conn_config.conndisable(self.conn_config.connections[params[1]])
            self.conn_config.rescan()
        if params[0] == 'addconn':
            self._tab = 0
            self._newconn = True
        if params[0] == 'delconn':
            self._tab = 0
            shell('rm /etc/netctl/' + params[1])
            self.conn_config.rescan()
        if params[0] == 'editconn':
            self._tab = 0
            self._editing_conn = self.conn_config.connections[params[1]]
        if params[0] == 'refresh':
            self._tab = 0
            self.net_config.rescan()
            self.conn_config.rescan()
        if params[0] == 'add':
            self._tab = 1
            self._editing = len(self.hosts)
        if params[0] == 'edit':
            self._tab = 1
            self._editing = int(params[1])
        if params[0] == 'del':
            self._tab = 1
            self.hosts.pop(int(params[1]))
            backend.Config(self.app).save(self.hosts)
        if params[0] == 'addns':
            self._tab = 2
            self._editing_ns = len(self.dns_config.nameservers) + 1
        if params[0] == 'editns':
            self._tab = 2
            self._editing_ns = int(params[1])
        if params[0] == 'delns':
            self._tab = 2
            self.dns_config.nameservers.pop(int(params[1]))
            self.dns_config.save()

    @event('dialog/submit')
    def on_dlg_submit(self, event, params, vars=None):
        if params[0] == 'dlgEditConn':
            if vars.getvalue('action', '') == 'OK':
                ip4 = '(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])'
                ip4regex = '^'+ip4+'$'
                ip4cidrregex = '^'+ip4+'(\/(\d|[1-2]\d|3[0-2]))$'
                if not vars.getvalue('connname', ''):
                    self.put_message('err', 'Must choose a name for the connection')
                elif re.search('\.|-|`|\\\\|\/|^test$|[ ]', vars.getvalue('connname')):
                    self.put_message('err', 'Connection name must not contain spaces, dots, dashes or special characters')
                elif vars.getvalue('addressing') == 'static' \
                and not vars.getvalue('address', ''):
                    self.put_message('err', 'Static connections must have an IP address')
                elif vars.getvalue('addressing') == 'static' \
                and not re.match(ip4cidrregex, vars.getvalue('address')):
                    self.put_message('err', 'IP address must be in the following format, with CIDR number: xxx.xxx.xxx.xxx/xx')
                elif vars.getvalue('addressing') == 'static' and vars.getvalue('gateway', '') \
                and not re.match(ip4regex, vars.getvalue('gateway')):
                    self.put_message('err', 'Gateway IP must be in the following format: xxx.xxx.xxx.xxx')
                elif vars.getvalue('devclass') == 'wireless' and not vars.getvalue('essid', ''):
                    self.put_message('err', 'Wireless connections must have an ESSID (access point name)')
                elif vars.getvalue('devclass') == 'wireless' and len(vars.getvalue('essid')) > 32:
                    self.put_message('err', 'ESSIDs cannot be longer than 32 characters')
                elif vars.getvalue('devclass') == 'wireless' \
                and re.search('^\!|^#|^;|\?|\"|\$|\[|\\\\|\]|\+', vars.getvalue('essid')):
                    self.put_message('err', 'ESSIDs cannot start with !#; or contain any the following: ?"$[]\+')
                elif vars.getvalue('devclass') == 'wireless' and vars.getvalue('security') == 'wep' \
                and len(vars.getvalue('key', '')) not in [5, 13]:
                    self.put_message('err', 'WEP keys must be either 5 or 13 characters long')
                elif vars.getvalue('devclass') == 'wireless' and vars.getvalue('security') == 'wpa' \
                and (8 > len(vars.getvalue('key', '')) or len(vars.getvalue('key', '')) > 63):
                    self.put_message('err', 'WPA keys must be between 8 and 63 characters long')
                else:
                    name = vars.getvalue('connname', '')
                    f = open('/etc/netctl/' + name, 'w')
                    f.write("# automatically generated by arkOS Genesis\n")

                    devclass = vars.getvalue('devclass', '')
                    if devclass:
                        f.write('Connection=\'' + devclass + '\'\n')

                    description = vars.getvalue('description', '')
                    if description:
                        f.write('Description=\'' + description + '\'\n')

                    interface = vars.getvalue('interface', '')
                    if interface:
                        f.write('Interface=\'' + interface + '\'\n')

                    security = vars.getvalue('security', '')
                    if security and devclass == 'wireless':
                        f.write('Security=\'' + security + '\'\n')

                    essid = vars.getvalue('essid', '')
                    if essid and devclass == 'wireless':
                        f.write('ESSID=\"' + essid + '\"\n')

                    addressing = vars.getvalue('addressing', '')
                    if addressing:
                        f.write('IP=\'' + addressing + '\'\n')

                    address = vars.getvalue('address', '')
                    if address and addressing == 'static':
                        f.write('Address=(\'' + address + '\')\n')

                    gateway = vars.getvalue('gateway', '')
                    if gateway and addressing == 'static':
                        f.write('Gateway=\'' + gateway + '\'\n')

                    key = vars.getvalue('key', '')
                    if key and devclass == 'wireless':
                        f.write('Key=\"' + key + '\"\n')

                    f.close()
                    self.conn_config.rescan()
            self._editing_conn = None
        if params[0] == 'dlgEdit':
            v = vars.getvalue('value', '')
            if vars.getvalue('action', '') == 'OK':
                h = backend.Host()
                h.ip = vars.getvalue('ip', 'none')
                h.name = vars.getvalue('name', 'none')
                h.aliases = vars.getvalue('aliases', '')
                if self._editing < len(self.hosts):
                    self.hosts[self._editing] = h
                else:
                    self.hosts.append(h)
                backend.Config(self.app).save(self.hosts)
            self._editing = None
        if params[0] == 'dlgEditDNS':
            if vars.getvalue('action', '') == 'OK':
                if self._editing_ns < len(self.dns_config.nameservers):
                    i = self.dns_config.nameservers[self._editing_ns]
                else:
                    i = Nameserver()
                    self.dns_config.nameservers.append(i)
                i.cls = vars.getvalue('cls', 'nameserver')
                i.address = vars.getvalue('address', '127.0.0.1')
                self.dns_config.save()
            self._editing_ns = None
        if params[0] == 'dlgNewConn':
            if vars.getvalue('action', '') == 'OK':
                self._editing_conn = {'addressing': vars.getvalue('addressing'),
                    'devclass': vars.getvalue('devclass')}
            self._newconn = None

########NEW FILE########
__FILENAME__ = nctp_ip
import time

from genesis.com import *
from genesis.ui import *
from genesis.utils import shell, str_fsize


class LinuxIp(Plugin):
    platform = ['Arch', 'arkos']
        
    def get_tx(self, iface):
        s = shell('ip -s link ls %s' % iface.name)
        s = s.split('\n')[5]
        s = s.split()[0] if len(s.split()) > 1 else '0'
        return int(s)
    
    def get_rx(self, iface):
        s = shell('ip -s link ls %s' % iface.name)
        s = s.split('\n')[3]
        s = s.split()[0] if len(s.split()) > 1 else '0'
        return int(s)
        
    def get_ip(self, iface):
        s = shell('ip addr list %s | grep \'inet \''%iface)
        s = s.split()[1] if len(s.split()) > 2 else '0.0.0.0'
        return s

    def detect_dev_class(self, iface):
        if iface.name[:-1] in ['ppp', 'wvdial']:
            return 'ppp'
        if iface.name[:-1] in ['wlan', 'ra', 'wifi', 'ath']:
            return 'wireless'
        if iface.name[:-1] == 'br':
            return 'bridge'
        if iface.name[:-1] == 'tun':
            return 'tunnel'
        if iface.name == 'lo':
            return 'loopback'
        if iface.name[:-1] == 'eth':
            return 'ethernet'
        return ''

    def detect_iface_bits(self, iface):
        r = ['linux-basic']
        cls = self.detect_dev_class(iface)
        if iface.type == 'inet' and iface.addressing == 'static':
            r.append('linux-ipv4')
        if iface.type == 'inet6' and iface.addressing == 'static':
            r.append('linux-ipv6')
        if iface.addressing == 'dhcp':
            r.append('linux-dhcp')
        if cls == 'ppp':
            r.append('linux-ppp')
        if cls == 'wireless':
            r.append('linux-wlan')
        if cls == 'bridge':
            r.append('linux-bridge')
        if cls == 'tunnel':
            r.append('linux-tunnel')

        r.append('linux-ifupdown')
        return r
        
    def up(self, iface):
        shell('ip link set dev %s up' % iface.name)
        time.sleep(1)

    def down(self, iface):
        shell('ip link set dev %s down' % iface.name)
        time.sleep(1)

    def enable(self, iface):
        shell('systemctl enable netctl-auto@%s.service' % iface.name)
        time.sleep(1)

    def disable(self, iface):
        shell('systemctl disable netctl-auto@%s.service' % iface.name)
        time.sleep(1)
    
    def connup(self, conn):
        shell('netctl start %s' % conn.name)
        time.sleep(1)

    def conndown(self, conn):
        shell('netctl stop %s' % conn.name)
        time.sleep(1)

    def connenable(self, conn):
        shell('netctl enable %s' % conn.name)
        time.sleep(1)

    def conndisable(self, conn):
        shell('netctl disable %s' % conn.name)
        time.sleep(1)

########NEW FILE########
__FILENAME__ = nc_arch
from genesis.com import *
from genesis.utils import *
from genesis import apis

from api import *
from nctp_ip import *
import os

class ArchNetworkConfig(LinuxIp):
    implements(INetworkConfig)
    platform = ['Arch', 'arkos']
    
    interfaces = None
    
    def __init__(self):
        self.rescan()
    
    def rescan(self):
        self.interfaces = {}
        name = ''

        s = shell('ip -o link list')
        for x in s.split('\n'):
            if x.strip():
                name = x.split(':')[1].strip()
                iface = NetworkInterface()
                self.interfaces[name] = iface
                iface.name = name
                iface.devclass = self.detect_dev_class(iface)
                iface.up = (x.find('state UP') != -1)
                iface.get_bits(self.app, self.detect_iface_bits(iface))
                iface.enabled = True if os.path.exists('/etc/systemd/system/multi-user.target.wants/netctl-auto@' + iface.name + '.service') \
                or os.path.exists('/etc/systemd/system/multi-user.target.wants/netctl-ifplugd@' + iface.name + '.service') else False
                iface.editable = False

    def save(self):
        return


class ArchConnConfig(LinuxIp):
    implements(IConnConfig)
    platform = ['Arch', 'arkos']
    connections = None
    
    def __init__(self):
        self.rescan()
    
    def rescan(self):
        self.connections = {}
        name = ''

        # List connections in /etc/netctl
        netctl = shell('netctl list')
        for line in netctl.split('\n'):
            data = {}
            if line:
                # Check if the connection is active
                status = True if line.startswith('*') else False
                line = line[2:]

                c = NetworkConnection()
                self.connections[line] = c
                c.name = line

                # Read the options from connection configs to variable
                for x in open(os.path.join('/etc/netctl', line)).readlines():
                    if x.startswith('#') or not x.strip():
                        continue
                    parse = x.split('=')
                    parse[1] = parse[1].translate(None, '\"\'\n')
                    data[parse[0]] = parse[1]

                # Send options one-by-one to the configuration
                c.devclass = data['Connection']
                c.interface = data['Interface']
                if 'dhcp' in data['IP']:
                    c.addressing = 'dhcp'
                    c.address = None
                    c.gateway = None
                else:
                    c.addressing = 'static'
                    c.address = data['Address']
                    c.gateway = data['Gateway'] if data.has_key('Gateway') else None
                c.description = data['Description'] if data.has_key('Description') else None
                if c.devclass == 'wireless':
                    c.essid = data['ESSID'] if data.has_key('ESSID') else 'Unknown'
                    c.security = data['Security'] if data.has_key('Security') else 'none'
                    if c.security != 'none' and c.security != 'wpa-configsection':
                        c.key = data['Key'] if data.has_key('Key') else None
                c.enabled = True if os.path.exists('/etc/systemd/system/multi-user.target.wants/netctl@' + c.name + '.service') else False
                c.up = status

    def save(self):
        return

########NEW FILE########
__FILENAME__ = recovery
from genesis.api import *
from genesis.com import *

import os


class ArchNetworkCfg(Plugin):
    implements(IConfigurable)
    name = 'Network'
    id = 'network'
    platform = ['arch', 'arkos']
    
    def list_files(self):
        return [os.path.join('/etc/netctl', file) for file in os.listdir('/etc/netctl')
            if os.path.isfile(os.path.join('/etc/netctl', file))]

class DebianNetworkCfg(Plugin):
    implements(IConfigurable)
    name = 'Network'
    id = 'network'
    platform = ['Debian', 'Ubuntu']
    
    def list_files(self):
        dir = '/etc/network/'
        return [dir+'*', dir+'*/*', dir+'*/*/*']
    

########NEW FILE########
__FILENAME__ = servers
from genesis import apis
from genesis.com import *
from genesis.api import *
from genesis.plugmgr import PluginLoader

from api import *


class Server(object):
	server_id = ''
	plugin_id = ''
	name = ''
	icon = ''
	ports = []


class ServerManager(Plugin):
	abstract = True
	servers = []

	def add(self, plugin_id, server_id, name, icon='', ports=[]):
		s = Server()
		s.server_id = server_id
		s.plugin_id = plugin_id
		s.name = name
		s.icon = icon
		s.ports = ports
		self.servers.append(s)
		return s

	def update(self, old_id, new_id, name, icon='', ports=[]):
		s = self.get(old_id)[0]
		s.server_id = new_id
		s.name = name
		s.icon = icon
		s.ports = ports

	def get(self, id):
		slist = []
		for x in self.servers:
			if x.server_id == id:
				slist.append(x)
		return slist

	def get_by_plugin(self, id):
		slist = []
		for x in self.servers:
			if x.plugin_id == id:
				slist.append(x)
		return slist

	def get_by_port(self, port):
		slist = []
		for x in self.servers:
			if port in x.ports[1]:
				slist.append(x)
		return slist

	def get_all(self):
		return self.servers

	def get_ranges(self):
		ranges = []
		nc = self.app.get_backend(INetworkConfig)
		for x in nc.interfaces:
			i = nc.interfaces[x]
			r = nc.get_ip(i.name)
			if '127.0.0.1' in r or '0.0.0.0' in r:
				continue
			if not '/' in r:
			    ri = r
			    rr = '32'
			else:
				ri, rr = r.split('/')
			ri = ri.split('.')
			ri[3] = '0'
			ri = ".".join(ri)
			r = ri + '/' + rr
			ranges.append(r)
		return ranges

	def scan_plugins(self):
		lst = PluginLoader.list_plugins()
		for c in lst:
			if hasattr(lst[c], 'services'):
				for s in self.servers:
					if lst[c].id == s.plugin_id:
						break
				else:
					for p in lst[c].services:
						try:
							if p['ports'] != []:
								self.add(lst[c].id, p['binary'], p['name'], 
									lst[c].iconfont, p['ports'])
						except IndexError:
							pass

	def scan_webapps(self):
		for x in enumerate(self.servers):
			if x[1].plugin_id == 'webapps':
				self.servers.pop(x[0])
		for s in apis.webapps(self.app).get_sites():
			self.add('webapps', s.name, s.name + ' (' + s.stype + ')',
				'gen-earth', [('tcp', s.port)])

	def remove(self, id):
		for s in enumerate(self.servers):
			if s[1].server_id == id:
				self.servers.pop(s[0])

	def remove_by_plugin(self, id):
		for s in enumerate(self.servers):
			if s[1].plugin_id == id:
				self.servers.pop(s[0])

########NEW FILE########
__FILENAME__ = widget
from genesis.ui import *
from genesis.utils import *
from genesis import apis
from genesis.com import implements, Plugin
from api import *

        
class NetworkWidget(Plugin):
    implements(apis.dashboard.IWidget)
    iconfont = 'gen-network'
    name = 'Network monitor'
    title = None
    style = 'normal'

    def __init__(self):
        self.iface = None
        self.connection = "None"
        
    def get_ui(self, cfg, id=None):
        self.iface = cfg
        be = self.app.get_backend(INetworkConfig)
        bc = self.app.get_backend(IConnConfig)
        i = be.interfaces[cfg]
        self.title = 'Network interface: %s (%s)' % (i.devclass.capitalize(), cfg)
        if not cfg in be.interfaces:
            return UI.Label(text='Interface not found')
        self.connection = []
        for x in bc.connections:
            c = bc.connections[x]
            if c.interface in cfg and c.up:
                self.connection.append(c.name)
        self.icon = 'gen-%s'%('checkmark' if i.up else 'close-2')
        
        ui = self.app.inflate('network:widget')
        ui.find('connection').set('text', 'Connected to: %s' % ', '.join(self.connection))
        ui.find('ip').set('text', be.get_ip(i.name))
        ui.find('in').set('text', str_fsize(be.get_rx(i)))
        ui.find('out').set('text', str_fsize(be.get_tx(i)))
        return ui
                
    def handle(self, event, params, cfg, vars=None):
        pass
    
    def get_config_dialog(self):
        be = self.app.get_backend(INetworkConfig)
        dlg = self.app.inflate('network:widget-config')
        for i in be.interfaces:
            dlg.append('list', UI.Radio(
                value=i,
                text=i,
                name='iface'
            ))
        return dlg
        
    def process_config(self, vars):
        return vars.getvalue('iface', None)

########NEW FILE########
__FILENAME__ = main
from genesis.api import *
from genesis.ui import *
from genesis import apis
from genesis.plugmgr import ImSorryDave, PluginLoader, RepositoryManager, LiveInstall, LiveRemove


class PluginManager(CategoryPlugin, URLHandler):
    text = 'Applications'
    iconfont = 'gen-box-add'
    folder = None

    def on_session_start(self):
        self._mgr = RepositoryManager(self.app.log, self.app.config)
        self._nc = apis.networkcontrol(self.app)
        self._reloadfw = False

    def on_init(self):
        self._mgr.refresh()

    def get_counter(self):
        return len(self._mgr.upgradable) or None

    def get_ui(self):
        if self._reloadfw == True:
            self._nc.refresh()
            self._reloadfw = False

        ui = self.app.inflate('plugins:main')

        inst = sorted(self._mgr.installed, key=lambda x: x.name.lower())

        for k in inst:
            row = self.app.inflate('plugins:item')
            desc = '<span class="ui-el-label-1" style="padding-left: 5px;">%s</span>'%k.desc
            row.find('name').set('text', k.name)
            row.find('desc').set('text', k.desc)
            row.find('icon').set('class', k.iconfont)
            row.find('version').set('text', k.version)
            row.find('author').set('text', k.author)
            row.find('author').set('url', k.homepage)
            row.append('buttons', UI.TipIcon(
                        iconfont="gen-cancel-circle",
                        text='Uninstall',
                        id='remove/'+k.id,
                        warning='Are you sure you wish to remove "%s"? Software and data associated with this application will be removed.' % k.name,
                    ))

            if k.problem:
                row.find('status').set('iconfont', 'gen-close-2 text-error')
                row.find('status').set('text', k.problem)
                row.find('icon').set('class', k.iconfont + ' text-error')
                row.find('name').set('class', 'text-error')
                row.find('desc').set('class', 'text-error')
                row.append('reqs', UI.IconFont(iconfont="gen-warning text-error", text=k.problem))
            else:
                row.find('status').set('iconfont', 'gen-checkmark')
                row.find('status').set('text', 'Installed and Enabled')
            ui.append('list', row)


        lst = sorted(self._mgr.available, key=lambda x: x.name.lower())

        btn = UI.Button(text='Check for updates', id='update')
        if len(lst) == 0:
            btn['text'] = 'Download plugin list'

        for k in lst:
            row = self.app.inflate('plugins:item')
            row.find('name').set('text', k.name)
            row.find('desc').set('text', k.description)
            row.find('icon').set('class', k.icon)
            row.find('version').set('text', k.version)
            row.find('author').set('text', k.author)
            row.find('author').set('url', k.homepage)

            for p in inst:
                if k.id == p.id and not p.problem:
                    row.find('status').set('iconfont', 'gen-arrow-up-2')
                    row.find('status').set('text', 'Upgrade Available')

            reqs = k.str_req()

            url = 'http://%s/view/plugins.php?id=%s' % (
                    self.app.config.get('genesis', 'update_server'),
                    k.id
                   )

            if reqs == '':
                row.append('buttons', UI.TipIcon(
                        iconfont="gen-box-add",
                        text='Download and install',
                        id='install/'+k.id,
                    ))
            else:
                row.append('reqs', UI.Icon(iconfont="gen-warning", text=reqs))

            ui.append('avail', row)

        return ui

    def get_ui_upload(self):
        return UI.Uploader(
            url='/upload_plugin',
            text='Install'
        )

    @url('^/upload_plugin$')
    def upload(self, req, sr):
        vars = get_environment_vars(req)
        f = vars.getvalue('file', None)
        try:
            self._mgr.install_stream(f)
        except:
            pass
        sr('301 Moved Permanently', [('Location', '/')])
        return ''

    @event('button/click')
    def on_click(self, event, params, vars=None):
        if params[0] == 'update':
            try:
                self._mgr.update_list(crit=True)
            except Exception, e:
                self.put_message('err', str(e))
                self.app.log.error(str(e))
            else:
                self.put_message('info', 'Plugin list updated')
        if params[0] == 'remove':
            try:
                self._mgr.check_conflict(params[1], 'remove')
                lr = LiveRemove(self._mgr, params[1], self)
                lr.start()
                self._nc.remove(params[1])
            except ImSorryDave, e:
                self.put_message('err', str(e))
        if params[0] == 'reload':
            try:
                PluginLoader.unload(params[1])
            except:
                pass
            try:
                PluginLoader.load(params[1])
            except:
                pass
            self.put_message('info', 'Plugin reloaded. Refresh page for changes to take effect.')
        if params[0] == 'restart':
            self.app.restart()
        if params[0] == 'install':
            try:
                self._mgr.check_conflict(params[1], 'install')
                li = LiveInstall(self._mgr, params[1], 
                    True, self)
                li.start()
            except Exception, e:
                self.put_message('err', str(e))

########NEW FILE########
__FILENAME__ = api
import os
import glob
import tempfile
import shutil
import time
import tempfile

from genesis.com import *
from genesis.api import *
from genesis.utils import shell, shell_status


class BackupRevision:
    def __init__(self, rev, fmts, date):
        self.revision = rev
        self.date = time.strftime('%s %s' % fmts, date)
        self._date = date


class Manager(Plugin):
    def __init__(self):
        try:
            self.dir = self.config.get('recovery', 'dir')
        except:
            self.dir = '/var/backups/genesis'
        if not os.path.exists(self.dir):
            os.makedirs(self.dir)
        
    def list_backups(self, id):
        r = []
        if not os.path.exists(os.path.join(self.dir, id)):
            return r
            
        for x in os.listdir(os.path.join(self.dir, id)):
            r.append(BackupRevision(
                        x.split('.')[0],
                        (self.app.gconfig.get('genesis', 'dformat', '%d %b %Y'), 
                            self.app.gconfig.get('genesis', 'tformat', '%H:%M')),
                        time.localtime(
                            os.path.getmtime(
                                os.path.join(self.dir, id, x)
                            )
                         )
                     ))
        return reversed(sorted(r, key=lambda x: x._date))

    def find_provider(self, id):
        return ConfManager.get().get_configurable(id)
        
    def delete_backup(self, id, rev):
        os.unlink(os.path.join(self.dir, id, rev+'.tar.gz'))
        
    def backup_all(self):
        errs = []
        for x in self.app.grab_plugins(IConfigurable):
            try:
                self.backup(x)
            except:
                errs.append(x.name)
        return errs
        
    def backup(self, provider):
        try:
            os.makedirs(os.path.join(self.dir, provider.id))
        except:
            pass
        dir = tempfile.mkdtemp()
        
        try:
            for f in provider.list_files():
                for x in glob.glob(f):
                    xdir = os.path.join(dir, os.path.split(x)[0][1:])
                    shell('mkdir -p \'%s\'' % xdir)
                    shell('cp -r \'%s\' \'%s\'' % (x, xdir))

            metafile = open(dir + '/genesis-backup', 'w')
            metafile.write(provider.id)
            metafile.close()

            if shell_status('cd %s; tar czf backup.tar.gz *'%dir) != 0:
                raise Exception()
            
            name = 0
            try:
                name = int(os.listdir(self.dir+'/'+provider.id)[0].split('.')[0])
            except:
                pass
            
            while os.path.exists('%s/%s/%i.tar.gz'%(self.dir,provider.id,name)):
                name += 1
            
            shutil.move('%s/backup.tar.gz'%dir, '%s/%s/%s.tar.gz'%(self.dir,provider.id,name))
        except:
            raise
        finally:
            shutil.rmtree(dir)
        
    def restore(self, provider, revision):
        dir = tempfile.mkdtemp()
        shutil.copy('%s/%s/%s.tar.gz'%(self.dir,provider.id,revision), '%s/backup.tar.gz'%dir)
        for f in provider.list_files():
            for x in glob.glob(f):
                os.unlink(x)
        if shell_status('cd %s; tar xf backup.tar.gz -C / --exclude genesis-backup'%dir) != 0:
            raise Exception()
        os.unlink('%s/backup.tar.gz'%dir)
        shutil.rmtree(dir)

    def upload(self, file):
        dir = '/var/backups/genesis/'

        # Get the backup then read its metadata
        tempdir = tempfile.mkdtemp()
        temparch = os.path.join(tempdir, 'backup.tar.gz')
        open(temparch, 'wb').write(file.value)

        shell('tar xzf ' + temparch + ' -C ' + tempdir)
        bfile = open(os.path.join(tempdir, 'genesis-backup'), 'r')
        name = bfile.readline()
        bfile.close()

        # Name the file and do some work
        if not os.path.exists(os.path.join(dir, name)):
            os.makedirs(os.path.join(dir, name))
        priors = os.listdir(dir + name)
        thinglist = []
        for thing in priors:
            thing = thing.split('.')
            thinglist.append(thing[0])
        newver = int(max(thinglist)) + 1 if thinglist else 0

        shell('cp %s %s' % (temparch, os.path.join(dir, name, str(newver) + '.tar.gz')))
        shell('rm -r ' + tempdir)

    def get_backups(self):
        dir = tempfile.mkdtemp()
        temparch = os.path.join(dir, 'backup-all.tar.gz')
        shell('tar czf ' + temparch + ' -C /var/backups/ genesis')
        size = os.path.getsize(temparch)

        f = open(temparch, 'rb')
        arch = f.read()
        f.close()
        shell('rm -r ' + dir)
        return (size, arch)

class RecoveryHook (ConfMgrHook):
    def finished(self, cfg):
        Manager(self.app).backup(cfg)
        

########NEW FILE########
__FILENAME__ = config
from genesis.api import ModuleConfig
from main import RecoveryPlugin


class GeneralConfig(ModuleConfig):
    target = RecoveryPlugin
    
    labels = {
        'auto': 'Automatic backup'
    }
    
    auto = True
   

########NEW FILE########
__FILENAME__ = main
from genesis.api import *
from genesis.ui import *
from genesis.utils import shell

from api import Manager
import os

class RecoveryPlugin(CategoryPlugin, URLHandler):
    text = 'Recovery'
    iconfont = 'gen-history'
    folder = None

    def on_init(self):
        self.manager = Manager(self.app)
        self.providers = self.app.grab_plugins(IConfigurable)
        self.providers = sorted(self.providers, key=lambda x: x.name)
        if not self._current:
            self._current = self.providers[0].id
            self._current_name = self.providers[0].name

    def on_session_start(self):
        self._uploader = None

    def get_ui(self):
        ui = self.app.inflate('recovery:main')

        provs = ui.find('provs')

        for p in self.providers:
            provs.append(
                    UI.ListItem(
                        UI.Label(text=p.name),
                        id=p.id,
                        active=p.id==self._current
                    )
                  )

        backs = ui.find('backs')

        for rev in self.manager.list_backups(self._current):
            backs.append(
                UI.DTR(
                    UI.Label(text=rev.revision),
                    UI.Label(text=rev.date),
                    UI.DTC(
                        UI.HContainer(
                            UI.TipIcon(
                                text='Recover',
                                iconfont="gen-folder-upload",
                                id='restore/%s/%s'%(self._current,rev.revision),
                                warning='Are you sure you wish to restore the configuration of %s as of %s (rev %s)?'%(
                                        self._current,
                                        rev.date,
                                        rev.revision
                                    )
                            ),
                            UI.TipIcon(
                                text='Download',
                                iconfont="gen-download",
                                onclick="window.open('/recovery/single/%s/%s', '_blank')" % (self._current,rev.revision),
                                id='download'
                            ),
                            UI.TipIcon(
                                text='Drop',
                                iconfont='gen-folder-minus',
                                id='drop/%s/%s'%(self._current,rev.revision),
                                warning='Are you sure you wish to delete the backed up configuration of %s as of %s (rev %s)?'%(
                                        self._current,
                                        rev.date,
                                        rev.revision
                                    )
                            ),
                            spacing=0
                        ),
                        width=0,
                    )
                )
            )

        ui.find('btnBackup').set('text', 'Backup %s'%self._current_name)
        ui.find('btnBackup').set('id', 'backup/%s'%self._current)

        if self._uploader:
            ui.append('main', UI.UploadBox(id='dlgUpload',
                text="Select archive to upload",
                multiple=False))

        return ui

    @url('^/recovery/single/.*$')
    def get_backup(self, req, start_response):
        params = req['PATH_INFO'].split('/')[3:] + ['']
        filename = '/var/backups/genesis/' + params[0] + '/' + params[1] + '.tar.gz'
        f = open(filename, 'rb')
        size = os.path.getsize(filename)

        start_response('200 OK', [
            ('Content-type', 'application/gzip'),
            ('Content-length', str(size)),
            ('Content-Disposition', 'attachment; filename=' + params[0] + '-' + params[1] + '.tar.gz')
        ])
        return f.read()

    @url('^/recovery/all$')
    def get_backups(self, req, start_response):
        data = Manager(self.app).get_backups()
        start_response('200 OK', [
            ('Content-type', 'application/gzip'),
            ('Content-length', str(data[0])),
            ('Content-Disposition', 'attachment; filename=backup-all.tar.gz')
        ])
        return data[1]

    @event('button/click')
    def on_click(self, event, params, vars=None):
        if params[0] == 'backup':
            p = self.manager.find_provider(params[1])
            try:
                self.manager.backup(p)
                self.put_message('info', 'Stored backup for %s.' % p.name)
            except:
                self.put_message('err', 'Failed to backup %s.' % p.name)
        if params[0] == 'backupall':
            errs = self.manager.backup_all()
            if errs != []:
                self.put_message('err', 'Backup failed for %s.' % ', '.join(errs))
            else:
                self.put_message('info', 'Stored full backup')
        if params[0] == 'restore':
            p = self.manager.find_provider(params[1])
            try:
                self.manager.restore(p, params[2])
                self.put_message('info', 'Restored configuration of %s (rev %s).' % (p.name, params[2]))
            except:
                self.put_message('err', 'Failed to recover %s.' % p.name)
        if params[0] == 'drop':
            try:
                self.manager.delete_backup(params[1], params[2])
                self.put_message('info', 'Deleted backup rev %s for %s.' % (params[2], params[1]))
            except:
                self.put_message('err', 'Failed to delete backup rev %s for %s.' % (params[2], params[1]))
        if params[0] == 'upload':
            self._uploader = True

    @event('listitem/click')
    def on_list_click(self, event, params, vars=None):
        for p in self.providers:
            if p.id == params[0]:
                self._current = p.id
                self._current_name = p.name

    @event('form/submit')
    @event('dialog/submit')
    def on_submit(self, event, params, vars=None):
        if params[0] == 'dlgUpload':
            if vars.getvalue('action', '') == 'OK' and vars.has_key('file'):
                f = vars['file']
                try:
                    self.manager.upload(f)
                    self.put_message('info', 'Upload successful.')
                except Exception, e:
                    self.put_message('err', 'Failed to upload backup: %s' % str(e))
        self._uploader = None

########NEW FILE########
__FILENAME__ = backend
import os
import getopt
import iptc

from genesis.ui import UI
from genesis.utils import shell, cidr_to_netmask
from genesis.api import *
from genesis import apis
from genesis.com import *

# Keeping this section for advanced use, for now.
# TODO: Migrate this where possible to calls for python-iptables

class Rule:
    states = ['NEW', 'ESTABLISHED', 'RELATED', 'INVALID']
    flags = ['SYN', 'ACK', 'FIN', 'RST', 'URG', 'PSH', 'ALL', 'NONE']

    def __init__(self, line='-A INPUT -j ACCEPT'):
        self.reset()
        self.raw = line
        opts = line.split()
        self.desc = ' '.join(opts[2:-2])

        while len(opts) > 0:
            inv = False
            if opts[0] == '!':
                inv = True
                opts = opts[1:]
            s = [opts[0]]
            prefix = ''
            while s[0].startswith('-'):
                prefix += s[0][0]
                s[0] = s[0][1:]
            opts = opts[1:]
            while len(opts) > 0 and not opts[0].startswith('-'):
                if opts[0] == '!':
                    break
                else:
                    s.append(opts[0])
                    opts = opts[1:]

            # S is one option
            if s[0] == 'f':
                self.fragment = (inv, True)
                continue
            if s[0] == 'A':
                self.chain = s[1]
                continue
            if s[0] == 'j':
                self.action = s[1]
                continue
            if s[0] == 'm':
                self.modules.append(s[1])
                continue
            if s[0] == 'tcp-flags':
                self.tcp_flags = (inv, s[1].split(','), s[2].split(','))
                continue
            if s[0] == 'state':
                self.state = (inv, s[1].split(','))
                continue

            self.tryset('protocol', inv, s, 'p', 'protocol') or \
            self.tryset('source', inv, s, 's', 'src') or \
            self.tryset('destination', inv, s, 'd', 'dst') or \
            self.tryset('mac_source', inv, s, 'mac-source') or \
            self.tryset('in_interface', inv, s, 'i', 'in-interface') or \
            self.tryset('out_interface', inv, s, 'i', 'in-interface') or \
            self.tryset('sport', inv, s, 'sport', 'source-port') or \
            self.tryset('dport', inv, s, 'dport', 'destination-port') or \
            self.tryset('sport', inv, s, 'sports', 'source-ports') or \
            self.tryset('dport', inv, s, 'dports', 'destination-ports') or \
            self.add_option(inv, prefix, s)


    def get_ui_text(self, param, help=''):
        v = getattr(self, param)
        return UI.HContainer(
                    UI.SelectInput(
                        UI.SelectOption(text='Ign.', value='ign', selected=v[1] is None),
                        UI.SelectOption(text='Is', value='nrm', selected=not v[0] and v[1] is not None),
                        UI.SelectOption(text='Isn\'t', value='inv', selected=v[0] and v[1] is not None),
                        design='mini',
                        name='%s-mode'%param
                    ),
                    UI.TextInput(name=param, value=v[1] or '', help=help),
                    spacing=5
               )

    def get_ui_bool(self, param):
        v = getattr(self, param)
        return UI.HContainer(
                    UI.SelectInput(
                        UI.SelectOption(text='Ign.', value='ign', selected=v[1] is None),
                        UI.SelectOption(text='Yes', value='nrm', selected=v[1]==True),
                        UI.SelectOption(text='No', value='inv', selected=v[1]==False),
                        design='mini',
                        name='%s-mode'%param
                    ),
                    spacing=5
               )

    def get_ui_select(self, param, opts):
        # opts == [['Desc', 'value'], ['Desc #2', 'value2']]
        v = getattr(self, param)

        return UI.HContainer(
                    UI.SelectInput(
                        UI.SelectOption(text='Ign.', value='ign', selected=v[1] is None),
                        UI.SelectOption(text='Is', value='nrm', selected=not v[0] and v[1] is not None),
                        UI.SelectOption(text='Isn\'t', value='inv', selected=v[0] and v[1] is not None),
                        design='mini',
                        name='%s-mode'%param
                    ),
                    UI.SelectTextInput(
                        *[UI.SelectOption(text=x[0], value=x[1], selected=v[1]==x[1])
                            for x in opts],
                        name=param,
                        value=v[1] or '',
                        design='mini'
                    ),
                    spacing=5
               )

    def get_ui_flags(self):
        v = self.tcp_flags

        return UI.HContainer(
                    UI.SelectInput(
                        UI.SelectOption(text='Ign.', value='ign', selected=v[1] is None),
                        UI.SelectOption(text='Are', value='nrm', selected=not v[0] and v[1] is not None),
                        UI.SelectOption(text='Are not', value='inv', selected=v[0] and v[1] is not None),
                        design='mini',
                        name='tcpflags-mode'
                    ),
                        UI.LT(
                            UI.LTR(
                                UI.Label(text='Check:'),
                                *[UI.Checkbox(text=x, name='tcpflags-vals[]', value=x, checked=x in v[2] if v[2] else False)
                                    for x in self.flags]
                            ),
                            UI.LTR(
                                UI.Label(text='Mask:'),
                                *[UI.Checkbox(text=x, name='tcpflags-mask[]', value=x, checked=x in v[1] if v[1] else False)
                                    for x in self.flags]
                            )
                        ),
               )

    def get_ui_states(self):
        v = self.state
        return UI.HContainer(
                    UI.SelectInput(
                        UI.SelectOption(text='Ign.', value='ign', selected=v[1] is None),
                        UI.SelectOption(text='Is', value='nrm', selected=not v[0] and v[1] is not None),
                        UI.SelectOption(text='Isn\'t', value='inv', selected=v[0] and v[1] is not None),
                        design='mini',
                        name='state-mode',
                    ),
                    UI.HContainer(
                        *[UI.Checkbox(text=x, name='state[]', value=x, checked=v[1] and x in v[1])
                            for x in self.states]
                    )
               )

    def tryset(self, param, inv, args, *names):
        if args[0] in names:
            setattr(self, param, (inv, ' '.join(args[1:])))
        return args[0] in names

    def add_option(self, inv, prefix, s):
        self.miscopts.append(('! ' if inv else '') + prefix + ' '.join(s))

    def reset(self):
        self.action = 'ACCEPT'
        self.chain = 'INPUT'
        self.miscopts = []
        self.modules = []
        self.tcp_flags = (False, None, None)

    def __getattr__(self, attr):
        return (False, None)

    def dump(self):
        return self.raw

    def apply_vars(self, vars):
        line = '-A ' + self.chain

        self.modules = vars.getvalue('modules', '').split()
        for m in self.modules:
            line += ' -m ' + m

        line += self._format_option('-p', 'protocol', vars)
        line += self._format_option('-s', 'source', vars)
        line += self._format_option('-d', 'destination', vars)
        line += self._format_option('--mac-source', 'mac_source', vars, module='mac')
        line += self._format_option('-i', 'in_interface', vars)
        line += self._format_option('-o', 'out_interface', vars)

        line += self._format_option('--sports', 'sport', vars, module='multiport')
        line += self._format_option('--dports', 'dport', vars, module='multiport')

        if vars.getvalue('fragmented-mode', '') == 'nrm':
            line += ' -f'
        if vars.getvalue('fragmented-mode', '') == 'inv':
            line += ' ! -f'

        if vars.getvalue('tcpflags-mode', '') != 'ign':
            if vars.getvalue('tcpflags-mode', '') == 'inv':
                line += ' !'

            mask = []
            for i in range(0, len(self.flags)):
                if vars.getvalue('tcpflags-mask[]')[i] == '1':
                    mask.append(self.flags[i])
            vals = []
            for i in range(0, len(self.flags)):
                if vars.getvalue('tcpflags-vals[]')[i] == '1':
                    vals.append(self.flags[i])

            if mask == []:
                mask = ['NONE']
            if vals == []:
                vals = ['NONE']

            line += ' --tcp-flags ' + ','.join(mask) + ' '  + ','.join(vals)

        if vars.getvalue('state-mode', '') != 'ign':
            if not 'state' in self.modules:
                line += ' -m state'
            if vars.getvalue('state-mode', '') == 'inv':
                line += ' !'
            st = []
            for i in range(0, len(self.states)):
                if vars.getvalue('state[]')[i] == '1':
                    st.append(self.states[i])
            if st == []:
                st = ['NONE']
            line += ' --state ' + ','.join(st)

        line += ' ' + ' '.join(self.miscopts)

        self.action = vars.getvalue('caction', 'ACCEPT')
        if self.action == 'RUN':
            self.action = vars.getvalue('runchain', 'ACCEPT')

        line += ' -j ' + self.action

        self.__init__(line)


    def _format_option(self, name, key, vars, flt=lambda x: x, module=None):
        if vars.getvalue(key+'-mode') == 'ign':
            return ''
        s = ''
        if module is not None:
            if not module in self.modules:
                self.modules.append(module)
                s = ' -m '+ module
        if vars.getvalue(key+'-mode') == 'nrm':
            s += ' ' + name + ' ' + flt(vars.getvalue(key, ''))
        if vars.getvalue(key+'-mode') == 'inv':
            s += ' ! ' + name + ' ' + flt(vars.getvalue(key, ''))
        return s


class Chain:
    rules = None

    def __init__(self, name, default):
        self.rules = []
        self.name = name
        self.comment = None
        self.default = default

    def dump(self):
        s = ''
        for r in self.rules:
            s += '%s\n' % r.dump()
        return s


class Table:
    chains = None

    def __init__(self, name):
        self.chains = {}
        self.name = name

    def load(self, data):
        while len(data)>0:
            s = data[0]
            if s.startswith('*'):
                return
            elif s.startswith(':'):
                n,d = s.split()[0:2]
                n = n[1:]
                self.chains[n] = Chain(n, d)
            elif s.startswith('-'):
                r = Rule(s)
                self.chains[r.chain].rules.append(r)
            data = data[1:]

    def dump(self):
        s = '*%s\n' % self.name
        for r in self.chains:
            r = self.chains[r]
            s += ':%s %s [0:0]\n' % (r.name, r.default)
        for r in self.chains:
            r = self.chains[r]
            s += '%s' % r.dump()
        s += 'COMMIT\n'
        return s


class Config(Plugin):
    implements(IConfigurable)
    name = 'iptables'
    iconfile = 'gen-fire'
    id = 'iptables'
    tables = {}
    apply_shell = 'cat /etc/iptables.up.rules | iptables-restore'

    def __init__(self):
        if self.app.config.has_option('iptables', 'rules_file'):
            self.rules_file = self.app.config.get('iptables', 'rules_file')
        else:
            cfg = self.app.get_backend(IConfig)
            if hasattr(cfg, 'rules_file'):
                self.rules_file = cfg.rules_file
            elif os.path.exists('/etc/iptables'):
                self.rules_file = '/etc/iptables/rules'
            else:
                self.rules_file = '/etc/iptables.up.rules' # webmin import
        self.apply_shell = 'cat %s | iptables-restore' % self.rules_file

    def list_files(self):
        return [self.rules_file]

    def load_runtime(self):
        shell('iptables -L -t filter')
        shell('iptables -L -t mangle')
        shell('iptables -L -t nat')
        shell('iptables-save > %s' % self.rules_file)
        self.load()

    def apply_now(self):
        return shell(self.apply_shell)

    def has_autostart(self):
        b = self.app.get_backend(IConfig)
        return b.has_autostart()

    def set_autostart(self, active):
        b = self.app.get_backend(IConfig)
        b.set_autostart(active)

    def load(self, file=None):
        file = file or self.rules_file
        self.tables = {}
        try:
            data = ConfManager.get().load('iptables', file).split('\n')
            while len(data)>0:
                s = data[0]
                data = data[1:]
                if s != '':
                    if s[0] == '*':
                        self.tables[s[1:]] = Table(s[1:])
                        self.tables[s[1:]].load(data)
        except:
            pass

    def get_devices(self):
        d = []
        for l in open('/proc/net/dev').read().splitlines():
            if ':' in l:
                dev = l.split(':')[0].strip()
                d.append((dev,dev))
        return d

    def dump(self):
        s = ''
        for r in self.tables:
            s += '%s\n' % self.tables[r].dump()
        return s

    def save(self, file=None):
        file = file or self.rules_file
        ConfManager.get().save('iptables', file, self.dump())
        ConfManager.get().commit('iptables')

    def table_index(self, name):
        i = 0
        for t in self.tables:
            if self.tables[t].name == name:
                return i
            i += 1


class IConfig(Interface):
    def has_autostart(self):
        pass

    def set_autostart(self, active):
        pass


class DebianConfig(Plugin):
    implements(IConfig)
    platform = ['debian', 'ubuntu']
    path = '/etc/network/if-up.d/iptables'

    @property
    def apply_shell(self):
        return '#!/bin/sh\ncat \'%s\' | iptables-restore' % Config(self.app).rules_file

    def has_autostart(self):
        return os.path.exists(self.path)

    def set_autostart(self, active):
        if active:
            open(self.path, 'w').write(self.apply_shell)
            shell('chmod 755 ' + self.path)
        else:
            try:
                os.unlink(self.path)
            except:
                pass


class ArchConfig(Plugin):
    implements(IConfig)
    platform = ['arch', 'arkos']
    path = '/etc/systemd/system/multi-user.target.wants/iptables.service'

    @property
    def apply_shell(self):
        return '#!/bin/sh\ncat \'%s\' | iptables-restore' % Config(self.app).rules_file

    def has_autostart(self):
        return os.path.exists(self.path)

    def set_autostart(self, active):
        if active:
            os.symlink('/usr/lib/systemd/system/iptables.service', self.path)
        else:
            try:
                os.unlink(self.path)
            except:
                pass


class GentooConfig(Plugin):
    implements(IConfig)
    platform = ['gentoo']
    rules_file = '/var/lib/iptables/rules-save'

    @property
    def apply_shell(self):
        return '#!/bin/sh\ncat \'%s\' | iptables-restore' % Config(self.app).rules_file

    def has_autostart(self):
        return True

    def set_autostart(self, active):
        pass


class CentosConfig(Plugin):
    implements(IConfig)
    platform = ['centos']
    rules_file = '/etc/sysconfig/iptables'

    @property
    def apply_shell(self):
        return '#!/bin/sh\ncat \'%s\' | iptables-restore' % Config(self.app).rules_file

    def has_autostart(self):
        return True

    def set_autostart(self, active):
        pass

########NEW FILE########
__FILENAME__ = defense
import ConfigParser
import os

from genesis.com import *
from genesis.api import *
from genesis import apis


class F2BConfigNotFound(Exception):
	def __str__(self):
		return ('The intrusion prevention config file could not be found, '
			'or the system (fail2ban) is not installed.')


class F2BManager(Plugin):
	abstract = True
	jailconf = '/etc/fail2ban/jail.conf'
	filters = '/etc/fail2ban/filter.d'

	def get_jail_config(self):
		cfg = ConfigParser.RawConfigParser()
		if cfg.read(self.jailconf) == []:
			raise F2BConfigNotFound()
		return cfg

	def enable_jail(self, jailname):
		cfg = self.get_jail_config()
		cfg.set(jailname, 'enabled', 'true')
		f = open(self.jailconf, 'w')
		cfg.write(f)
		f.close()

	def disable_jail(self, jailname):
		cfg = self.get_jail_config()
		cfg.set(jailname, 'enabled', 'false')
		f = open(self.jailconf, 'w')
		cfg.write(f)
		f.close()

	def enable_all(self, obj):
		cfg = self.get_jail_config()
		for jail in obj['f2b']:
			cfg.set(jail['name'], 'enabled', 'true')
		f = open(self.jailconf, 'w')
		cfg.write(f)
		f.close()

	def disable_all(self, obj):
		cfg = self.get_jail_config()
		for jail in obj['f2b']:
			cfg.set(jail['name'], 'enabled', 'false')
		f = open(self.jailconf, 'w')
		cfg.write(f)
		f.close()

	def bantime(self, bantime=''):
		cfg = self.get_jail_config()
		if bantime == '':
			return cfg.get('DEFAULT', 'bantime')
		elif bantime != cfg.get('DEFAULT', 'bantime'):
			cfg.set('DEFAULT', 'bantime', bantime)
			f = open(self.jailconf, 'w')
			cfg.write(f)
			f.close()

	def findtime(self, findtime=''):
		cfg = self.get_jail_config()
		if findtime == '':
			return cfg.get('DEFAULT', 'findtime')
		elif findtime != cfg.get('DEFAULT', 'findtime'):
			cfg.set('DEFAULT', 'findtime', findtime)
			f = open(self.jailconf, 'w')
			cfg.write(f)
			f.close()

	def maxretry(self, maxretry=''):
		cfg = self.get_jail_config()
		if maxretry == '':
			return cfg.get('DEFAULT', 'maxretry')
		elif maxretry != cfg.get('DEFAULT', 'maxretry'):
			cfg.set('DEFAULT', 'maxretry', maxretry)
			f = open(self.jailconf, 'w')
			cfg.write(f)
			f.close()

	def upd_ignoreip(self, ranges):
		ranges.insert(0, '127.0.0.1/8')
		s = ' '.join(ranges)
		cfg = self.get_jail_config()
		if s != cfg.get('DEFAULT', 'ignoreip'):
			cfg.set('DEFAULT', 'ignoreip', s)
			f = open(self.jailconf, 'w')
			cfg.write(f)
			f.close()

	def get_all(self):
		lst = []
		remove = []
		cfg = self.get_jail_config()
		fcfg = ConfigParser.SafeConfigParser()
		for c in self.app.grab_plugins(ICategoryProvider):
			if hasattr(c.plugin_info, 'f2b') and \
			hasattr(c.plugin_info, 'f2b_name') and \
			c.plugin_info.f2b and c.plugin_info.f2b_name:
				lst.append({'name': c.plugin_info.f2b_name,
					'icon': c.plugin_info.f2b_icon,
					'f2b': c.plugin_info.f2b})
			elif hasattr(c.plugin_info, 'f2b') and c.plugin_info.f2b:
				lst.append({'name': c.text,
					'icon': c.plugin_info.iconfont,
					'f2b': c.plugin_info.f2b})
			elif hasattr(c, 'f2b') and hasattr(c, 'f2b_name') and \
			c.f2b and c.f2b_name:
				lst.append({'name': c.f2b_name,
					'icon': c.f2b_icon,
					'f2b': c.f2b})
			elif hasattr(c, 'f2b') and c.f2b:
				lst.append({'name': c.text,
					'icon': c.iconfont,
					'f2b': c.f2b})
		for s in apis.webapps(self.app).get_apptypes():
			if hasattr(s.plugin_info, 'f2b') and s.plugin_info.f2b:
				lst.append({'name': s.plugin_info.name, 
					'icon': 'gen-earth',
					'f2b': s.plugin_info.f2b})
		for p in lst:
			for l in p['f2b']:
				if not 'custom' in l:
					try:
						jail_opts = cfg.items(l['name'])
					except ConfigParser.NoSectionError:
						remove.append(p)
						continue
					filter_name = cfg.get(l['name'], 'filter')
					if "%(__name__)s" in filter_name:
						filter_name = filter_name.replace("%(__name__)s", l['name'])
					c = fcfg.read([self.filters+'/common.conf', 
						self.filters+'/'+filter_name+'.conf'])
					filter_opts = fcfg.items('Definition')
					l['jail_opts'] = jail_opts
					l['filter_name'] = filter_name
					l['filter_opts'] = filter_opts
				else:
					if not os.path.exists(self.filters+'/'+l['filter_name']+'.conf'):
						f = open(self.filters+'/'+l['filter_name']+'.conf', 'w')
						fcfg = ConfigParser.SafeConfigParser()
						fcfg.add_section('Definition')
						for o in l['filter_opts']:
							fcfg.set('Definition', o[0], o[1])
						fcfg.write(f)
						f.close()
					if not l['name'] in cfg.sections():
						f = open(self.jailconf, 'w')
						cfg.add_section(l['name'])
						for o in l['jail_opts']:
							cfg.set(l['name'], o[0], o[1])
						cfg.write(f)
						f.close()
					else:
						jail_opts = cfg.items(l['name'])
						filter_name = cfg.get(l['name'], 'filter')
						fcfg.read([self.filters+'/common.conf', 
							self.filters+'/'+filter_name+'.conf'])
						filter_opts = fcfg.items('Definition')
						l['jail_opts'] = jail_opts
						l['filter_name'] = filter_name
						l['filter_opts'] = filter_opts
		for x in remove:
			lst.remove(x)
		return lst

########NEW FILE########
__FILENAME__ = firewall
import iptc
import re

from genesis.com import *
from genesis.api import *
from genesis.utils import shell, cidr_to_netmask
from genesis.plugins.network.servers import ServerManager


class RuleManager(Plugin):
    abstract = True
    rules = []

    def set(self, server, allow):
        self.app.gconfig.set('security', 'fw-%s-%s'
            %(server.plugin_id, server.server_id), str(allow))
        self.app.gconfig.save()

    def get(self, server):
        for x in ServerManager(self.app).get_all():
            if x == server:
                return int(self.app.gconfig.get('security', 'fw-%s-%s'
                    %(x.plugin_id, x.server_id)))
        return False

    def get_by_id(self, id):
        for x in ServerManager(self.app).get_all():
            if x.server_id == id:
                return (x, int(self.app.gconfig.get('security', 'fw-%s-%s'
                    %(x.plugin_id, x.server_id))))
        return False

    def get_by_plugin(self, id):
        plist = []
        for x in ServerManager(self.app).get_all():
            if x.plugin_id == id:
                plist.append((x, int(self.app.gconfig.get('security', 'fw-%s-%s'
                    %(x.plugin_id, x.server_id)))))
        return plist

    def get_all(self):
        rules = []
        for x in ServerManager(self.app).get_all():
            rules.append((x, int(self.app.gconfig.get('security', 'fw-%s-%s'
                %(x.plugin_id, x.server_id)))))
        return rules

    def scan_servers(self):
        # Scan active servers and create entries for them when necessary
        for x in ServerManager(self.app).get_all():
            if x.plugin_id == 'arkos' and x.server_id == 'beacon' and not self.app.gconfig.has_option('security', 'fw-%s-%s'
                %(x.plugin_id, x.server_id)):
                self.set(x, 1)
            elif x.plugin_id == 'arkos' and x.server_id == 'genesis' and not self.app.gconfig.has_option('security', 'fw-%s-%s'
                %(x.plugin_id, x.server_id)):
                self.set(x, 2)
            elif not self.app.gconfig.has_option('security', 'fw-%s-%s'
                %(x.plugin_id, x.server_id)):
                self.set(x, 2)

    def clear_cache(self):
        # Compares active firewall preferences stored in config
        # to active servers, removes obsolete entries
        s = ServerManager(self.app).get_all()
        r = re.compile('fw-((?:[a-z][a-z]+))-((?:[a-z][a-z]+))',
            re.IGNORECASE)
        for o in self.app.gconfig.options('security'):
            m = r.match(o)
            if m:
                pid, sid = m.group(1), m.group(2)
                for x in s:
                    present = False
                    if x.plugin_id == pid and x.server_id == sid:
                        present = True
                    if present == False:
                        self.remove(o)

    def remove(self, server):
        # Remove an entry from firewall config
        self.app.gconfig.remove_option('security', 'fw-%s-%s'
            %(server.plugin_id, server.server_id))
        self.app.gconfig.save()

    def remove_by_plugin(self, id):
        # Remove all entries for a particular plugin
        r = re.compile('fw-((?:[a-z][a-z]+))-((?:[a-z][a-z]+))',
            re.IGNORECASE)
        for o in self.app.gconfig.options('security'):
            m = r.match(o)
            if m and m.group(1) == id:
                self.app.gconfig.remove_option('security', o)
        self.app.gconfig.save()


class FWMonitor(Plugin):
    abstract = True

    def initialize(self):
        tb = iptc.Table(iptc.Table.FILTER)
        c = iptc.Chain(tb, 'INPUT')
        c.flush()

        # Accept loopback
        r = iptc.Rule()
        r.in_interface = 'lo'
        t = iptc.Target(r, 'ACCEPT')
        r.target = t
        c.append_rule(r)

        # Accept designated apps
        r = iptc.Rule()
        t = iptc.Target(r, 'genesis-apps')
        r.target = t
        c.append_rule(r)

        # Allow ICMP (ping)
        shell('iptables -A INPUT -p icmp --icmp-type echo-request -j ACCEPT')

        # Accept established/related connections
        # Unfortunately this has to be done clasically
        shell('iptables -A INPUT -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT')

        # Reject all else by default
        r = iptc.Rule()
        t = iptc.Target(r, 'DROP')
        r.target = t
        c.append_rule(r)

        self.save()

    def scan(self):
        # Update our local configs from what is in our iptables chain.
        # This should probably never be used, but it looks pretty.
        rm = RuleManager(self.app)
        tb = iptc.Table(iptc.Table.FILTER)
        c = iptc.Chain(tb, "genesis-apps")
        if not tb.is_chain(c):
            tb.create_chain(c)
            return
        for r in c.rules:
            m = r.matches[0]
            for s in ServerManager(self.app).get_by_port(m.dport):
                srv = rm.get(s)
                if 'anywhere' in r.src:
                    rm.set(s, 2)
                else:
                    rm.set(s, 1)

    def regen(self, range=[]):
        # Regenerate our chain.
        # If local ranges are not provided, get them.
        self.flush()
        if range == []:
            range = ServerManager(self.app).get_ranges()
        for x in RuleManager(self.app).get_all():
            for p in x[0].ports:
                if int(x[1]) == 2:
                    self.add(p[0], p[1], 'anywhere')
                elif int(x[1]) == 1:
                    for r in range:
                        self.add(p[0], p[1], r)
                else:
                    self.remove(p[0], p[1])
        tb = iptc.Table(iptc.Table.FILTER)
        c = iptc.Chain(tb, "genesis-apps")
        r = iptc.Rule()
        t = iptc.Target(r, 'RETURN')
        r.target = t
        c.append_rule(r)

    def add(self, protocol, port, range=''):
        # Add rule for this port
        # If range is not provided, assume '0.0.0.0'
        tb = iptc.Table(iptc.Table.FILTER)
        c = iptc.Chain(tb, "genesis-apps")
        if not tb.is_chain(c):
            tb.create_chain(c)
        r = iptc.Rule()
        r.protocol = protocol
        if range != '' and range != 'anywhere' and range != '0.0.0.0':
            ip, cidr = range.split('/')
            mask = cidr_to_netmask(int(cidr))
            r.src = ip + '/' + mask
        m = iptc.Match(r, protocol)
        m.dport = str(port)
        r.add_match(m)
        t = iptc.Target(r, 'ACCEPT')
        r.target = t
        c.insert_rule(r)

    def remove(self, protocol, port, range=''):
        # Remove rule(s) in our chain matching this port
        # If range is not provided, delete all rules for this port
        tb = iptc.Table(iptc.Table.FILTER)
        c = iptc.Chain(tb, "genesis-apps")
        if not tb.is_chain(c):
            return
        for r in c.rules:
            if range != '':
                if r.matches[0].dport == port and range in r.dst:
                    c.delete_rule(r)
            else:
                if r.matches[0].dport == port:
                    c.delete_rule(r)

    def find(self, protocol, port, range=''):
        # Returns true if rule is found for this port
        # If range IS provided, return true only if range is the same
        tb = iptc.Table(iptc.Table.FILTER)
        c = iptc.Chain(tb, "genesis-apps")
        if not tb.is_chain(c):
            return False
        for r in c.rules:
            if range != '':
                if r.matches[0].dport == port and range in r.dst:
                    return True
            elif range == '' and r.matches[0].dport == port:
                return True
        return False

    def flush(self):
        # Flush out our chain
        tb = iptc.Table(iptc.Table.FILTER)
        c = iptc.Chain(tb, "genesis-apps")
        if tb.is_chain(c):
            c.flush()

    def save(self):
        # Save rules to file loaded on boot
        f = open('/etc/iptables/iptables.rules', 'w')
        f.write(shell('iptables-save'))
        f.close()

########NEW FILE########
__FILENAME__ = main
from genesis.ui import *
from genesis.com import implements
from genesis.api import *
from genesis import apis
from genesis.utils import *
from genesis.plugins.network.api import *

from firewall import RuleManager, FWMonitor
from defense import F2BManager, F2BConfigNotFound
from backend import *


class SecurityPlugin(apis.services.ServiceControlPlugin):
    text = 'Security'
    iconfont = 'gen-lock-2'
    folder = 'system'
    services = [{"name": 'Intrusion Prevention', "binary": 'fail2ban', "ports": []}]
    f2b_name = 'Genesis'
    f2b_icon = 'gen-arkos-round'
    f2b = [{
        'custom': True,
        'name': 'genesis',
        'jail_opts': [
            ('enabled', 'true'),
            ('filter', 'genesis'),
            ('logpath', '/var/log/genesis.log'),
            ('action', 'iptables[name=genesis, port=8000, protocol=tcp]')
        ],
        'filter_name': 'genesis',
        'filter_opts': [
            ('_daemon', 'genesis-panel'),
            ('failregex', '.*[ERROR] auth: Login failed for user .* from <HOST>$')
        ]
    }]

    defactions = ['ACCEPT', 'DROP', 'REJECT', 'LOG', 'EXIT', 'MASQUERADE']

    def on_init(self):
        self.cfg = Config(self.app)
        self.cfg.load()
        self.net_config = self.app.get_backend(INetworkConfig)
        self.rules = sorted(self._srvmgr.get_all(), 
            key=lambda s: s[0].name)
        try:
            self.f2brules = sorted(self._f2bmgr.get_all(),
                key= lambda s: s['name'])
        except F2BConfigNotFound, e:
            self.put_message('err', e)
            self.f2brules = []

    def on_session_start(self):
        self._idef = None
        self._stab = 0
        self._tab = 0
        self._shuffling = None
        self._shuffling_table = None
        self._adding_chain = None
        self._editing_table = None
        self._editing_chain = None
        self._editing_rule = None
        self._error = None
        self._ranges = []
        self._srvmgr = RuleManager(self.app)
        self._fwmgr = FWMonitor(self.app)
        self._f2bmgr = F2BManager(self.app)

    def get_main_ui(self):
        ui = self.app.inflate('security:main')
        ui.find('stabs').set('active', 's'+str(self._stab))
        if self.cfg.has_autostart():
            btn = ui.find('autostart')
            btn.set('text', 'Disable autostart')
            btn.set('id', 'noautostart')

        present = False
        try:
            if self.app.gconfig.get('security', 'noinit') == 'yes':
                present = True
        except:
            pass
        for rx in iptc.Chain(iptc.Table(iptc.Table.FILTER), 'INPUT').rules:
            if rx.target.name == 'genesis-apps':
                present = True
            elif rx.target.name == 'DROP':
                present = True
        if present == False:
            self.put_message('err', 'There may be a problem with your '
                'firewall. Please reload the table by clicking "Reinitialize" '
                'under the Settings tab below.')

        self._ranges = []
        for x in self.net_config.interfaces:
            i = self.net_config.interfaces[x]
            r = self.net_config.get_ip(i.name)
            if '127.0.0.1' in r or '0.0.0.0' in r:
                continue
            if not '/' in r:
                ri = r
                rr = '32'
            else:
                ri, rr = r.split('/')
            ri = ri.split('.')
            ri[3] = '0'
            ri = ".".join(ri)
            r = ri + '/' + rr
            self._ranges.append(r)
        ui.find('ranges').set('text', 'Local networks: ' + ', '.join(self._ranges))

        al = ui.find('applist')
        ql = ui.find('arkoslist')
        fl = ui.find('f2blist')

        for s in self.rules:
            if s[0].plugin_id != 'arkos':
                if s[1] == 1:
                    perm, ic, show = 'Local Only', 'gen-home', [2, 0]
                elif s[1] == 2:
                    perm, ic, show = 'All Networks', 'gen-earth', [1, 0]
                else:
                    perm, ic, show = 'None', 'gen-close', [2, 1]
                al.append(UI.DTR(
                    UI.IconFont(iconfont=s[0].icon),
                    UI.Label(text=s[0].name),
                    UI.Label(text=', '.join(str(x[1]) for x in s[0].ports)),
                    UI.HContainer(
                        UI.IconFont(iconfont=ic),
                        UI.Label(text=' '),
                        UI.Label(text=perm),
                        ),
                    UI.HContainer(
                        (UI.TipIcon(iconfont='gen-earth',
                            text='Allow From Anywhere', id='2/' + str(self.rules.index(s))) if 2 in show else None),
                        (UI.TipIcon(iconfont='gen-home',
                            text='Local Access Only', id='1/' + str(self.rules.index(s))) if 1 in show else None),
                        (UI.TipIcon(iconfont='gen-close', 
                            text='Deny All', 
                            id='0/' + str(self.rules.index(s)), 
                            warning='Are you sure you wish to deny all access to %s? '
                            'This will prevent anyone (including you) from connecting to it.' 
                            % s[0].name) if 0 in show else None),
                        ),
                   ))
            else:
                if s[0].server_id == 'beacon' and s[1] == 2:
                    self._srvmgr.set(s[0], 1)
                    perm, ic, show = 'Local Only', 'gen-home', [0]
                elif s[0].server_id == 'beacon' and s[1] == 1:
                    perm, ic, show = 'Local Only', 'gen-home', [0]
                elif s[0].server_id == 'beacon' and s[1] == 0:
                    perm, ic, show = 'None', 'gen-close', [1]
                elif s[0].server_id == 'genesis' and s[1] == 2:
                    perm, ic, show = 'All Networks', 'gen-earth', [1]
                elif s[0].server_id == 'genesis' and s[1] == 1:
                    perm, ic, show = 'Local Only', 'gen-home', [2]
                ql.append(UI.DTR(
                    UI.IconFont(iconfont=s[0].icon),
                    UI.Label(text=s[0].name),
                    UI.Label(text=', '.join(str(x[1]) for x in s[0].ports)),
                    UI.HContainer(
                        UI.IconFont(iconfont=ic),
                        UI.Label(text=' '),
                        UI.Label(text=perm),
                        ),
                    UI.HContainer(
                        (UI.TipIcon(iconfont='gen-earth',
                            text='Allow From Anywhere', id='2/' + str(self.rules.index(s))) if 2 in show else None),
                        (UI.TipIcon(iconfont='gen-home',
                            text='Local Access Only', id='1/' + str(self.rules.index(s))) if 1 in show else None),
                        (UI.TipIcon(iconfont='gen-close', 
                            text='Deny All', 
                            id='0/' + str(self.rules.index(s)), 
                            warning='Are you sure you wish to deny all access to %s? '
                            'This will prevent anyone (including you) from connecting to it.' 
                            % s[0].name) if 0 in show else None),
                        ),
                   ))

        for s in self.f2brules:
            perm, ic, show = 'Disabled', 'gen-close', 'e'
            for f in s['f2b']:
                for line in f['jail_opts']:
                    if line[0] == 'enabled' and line[1] == 'true':
                        perm, ic, show = 'Enabled', 'gen-checkmark-circle', 'd'
            fl.append(UI.DTR(
                UI.IconFont(iconfont=s['icon']),
                UI.Label(text=s['name']),
                UI.HContainer(
                    UI.IconFont(iconfont=ic),
                    UI.Label(text=' '),
                    UI.Label(text=perm),
                    ),
                UI.HContainer(
                    UI.TipIcon(iconfont='gen-info', text='Information',
                        id='idef/' + str(self.f2brules.index(s))),
                    (UI.TipIcon(iconfont='gen-checkmark-circle',
                        text='Enable All Defense', id='edef/' + str(self.f2brules.index(s))) if show == 'e' else None),
                    (UI.TipIcon(iconfont='gen-close',
                        text='Disable All Defense', id='ddef/' + str(self.f2brules.index(s))) if show == 'd' else None),
                    ),
               ))

        tc = UI.TabControl(active=self._tab)
        ui.append('advroot', tc)

        if len(self.cfg.tables) == 0:
            self.cfg.load_runtime()

        for t in self.cfg.tables:
            t = self.cfg.tables[t]
            vc = UI.VContainer(spacing=15)
            for ch in t.chains:
                ch = t.chains[ch]
                uic = UI.FWChain(tname=t.name, name=ch.name, default=ch.default)
                idx = 0
                for r in ch.rules:
                    uic.append(
                        UI.FWRule(
                            action=r.action,
                            desc=('' if r.action in self.defactions else r.action + ' ') + r.desc,
                            id='%s/%s/%i'%(t.name,ch.name,idx)
                        ))
                    idx += 1
                vc.append(uic)
            vc.append(UI.Button(iconfont='gen-plus-circle', text='Add new chain to '+t.name, id='addchain/'+t.name))
            tc.add(t.name, vc)

        try:
            ui.find('f2b_maxretry').set('value', self._f2bmgr.maxretry())
            ui.find('f2b_findtime').set('value', self._f2bmgr.findtime())
            ui.find('f2b_bantime').set('value', self._f2bmgr.bantime())
        except F2BConfigNotFound:
            ui.find('f2b_maxretry').set('disabled', 'true')
            ui.find('f2b_findtime').set('disabled', 'true')
            ui.find('f2b_bantime').set('disabled', 'true')
            ui.remove('frmDefenseButton')

        if self._idef is not None:
            ui.find('f2b_appname').set('text', self._idef['name'])
            for j in self._idef['f2b']:
                perm, ic, show = 'Disabled', 'gen-close', 'e'
                for line in j['jail_opts']:
                    if line[0] == 'enabled' and line[1] == 'true':
                        perm, ic, show = 'Enabled', 'gen-checkmark-circle', 'd'
                ui.find('f2b_jails').append(
                    UI.DTR(
                        UI.Label(text=j['name']),
                        UI.HContainer(
                            (UI.TipIcon(iconfont='gen-checkmark-circle',
                                text='Enable', id='ed/' + j['name']) if show == 'e' else None),
                            (UI.TipIcon(iconfont='gen-close',
                                text='Disable', id='dd/' + j['name']) if show == 'd' else None),
                        ),
                    ))
        else:
            ui.remove('dlgF2BInfo')

        if self._error is not None and len(self._error) > 0:
            self.put_message('warn', self._error)
            self._error = None

        if self._shuffling != None:
            ui.append('advroot', self.get_ui_shuffler())

        if self._adding_chain != None:
            ui.append('advroot', UI.InputBox(id='dlgAddChain', text='Chain name:'))

        if self._editing_rule != None:
            ui.append('advroot', self.get_ui_edit_rule(
                        rule=self.cfg.tables[self._editing_table].\
                                      chains[self._editing_chain].\
                                      rules[self._editing_rule]
                    ))

        return ui

    def get_ui_edit_rule(self, rule=Rule()):
        protocols = (('TCP','tcp'), ('UDP','udp'), ('ICMP','icmp'))

        tc = UI.TabControl(active='r0')
        tc.add('Main',
            UI.Container(
                UI.Formline(
                    UI.Radio(text='Accept', name='caction', value='ACCEPT',     checked=rule.action=="ACCEPT"),
                    UI.Radio(text='Drop',   name='caction', value='DROP',       checked=rule.action=="DROP"),
                    UI.Radio(text='Reject', name='caction', value='REJECT',     checked=rule.action=="REJECT"),
                    UI.Radio(text='Log',    name='caction', value='LOG',        checked=rule.action=="LOG"),
                    UI.Radio(text='Masq',   name='caction', value='MASQUERADE', checked=rule.action=="MASQUERADE"),
                    UI.Radio(text='Exit',   name='caction', value='EXIT',       checked=rule.action=="EXIT"),
                    UI.Radio(text='Run chain:', name='caction', value='RUN',    checked=rule.action not in self.defactions),
                    UI.TextInput(name='runchain', value=rule.action),
                    text='Action'
                ),
                UI.Formline(
                    rule.get_ui_select('protocol', protocols),
                    text='Protocol'
                ),
                UI.Formline(
                    rule.get_ui_text('source'),
                    text='Source IP',
                    help='You can specify IP mask like 192.168.0.0/24'
                ),
                UI.Formline(
                    rule.get_ui_text('destination'),
                    text='Destination IP',
                ),
                UI.Formline(
                    rule.get_ui_text('mac_source'),
                    text='Source MAC'
                ),
                UI.Formline(
                    rule.get_ui_select('in_interface', self.cfg.get_devices()),
                    text='Incoming interface'
                ),
                UI.Formline(
                    rule.get_ui_select('out_interface', self.cfg.get_devices()),
                    text='Outgoing interface'
                ),
                UI.Formline(
                    rule.get_ui_bool('fragmented'),
                    text='Fragmentation'
                ),
                UI.Formline(
                    UI.TextInput(name='modules', value=' '.join(rule.modules)),
                    text='Modules',
                    help='Additional IPTables modules to load',
                ),
                UI.Formline(
                    UI.TextInput(name='options', value=' '.join(rule.miscopts)),
                    text='Additional options',
                ),
            ), id='r0')

        tc.add('TCP/UDP',
            UI.Container(
                UI.Formline(
                    rule.get_ui_text('sport'),
                    text='Source port',
                    help='Can accept lists and ranges like 80:85,8000 up to 15 ports',
                ),
                UI.Formline(
                    rule.get_ui_text('dport'),
                    text='Destination port'
                ),
                UI.Formline(
                    rule.get_ui_flags(),
                    text='TCP flags',
                ),
                UI.Formline(
                    rule.get_ui_states(),
                    text='TCP states',
                ),
            ), id='r1')

        return UI.DialogBox(tc, id='dlgEditRule', miscbtn='Delete', miscbtnid='deleterule')

    def get_ui_shuffler(self):
        li = UI.SortList(id='list')
        for r in self.cfg.tables[self._shuffling_table].chains[self._shuffling].rules:
            li.append(
                UI.SortListItem(
                    UI.FWRule(action=r.action, desc=r.desc, id=''),
                    id=r.raw
                ))

        return UI.DialogBox(li, id='dlgShuffler')

    @event('button/click')
    def on_click(self, event, params, vars=None):
        if params[0] == '2':
            self._stab = 0
            self._srvmgr.set(self.rules[int(params[1])][0], 2)
            self._fwmgr.regen(self._ranges)
        if params[0] == '1':
            self._stab = 0
            self._srvmgr.set(self.rules[int(params[1])][0], 1)
            self._fwmgr.regen(self._ranges)
        if params[0] == '0':
            self._stab = 0
            sel = self.rules[int(params[1])][0]
            if sel.plugin_id == 'arkos' and sel.server_id == 'genesis':
                self.put_message('err', 'You cannot deny all access to Genesis. '
                    'Try limiting it to your local network instead.')
            else:
                self._srvmgr.set(sel, 0)
                self._fwmgr.regen(self._ranges)
        if params[0] == 'idef':
            self._stab = 1
            self._idef = self.f2brules[int(params[1])]
        if params[0] == 'ed':
            self._stab = 1
            try:
                self._f2bmgr.enable_jail(params[1])
            except F2BConfigNotFound, e:
                self.put_message('err', e)
        if params[0] == 'dd':
            self._stab = 1
            try:
                self._f2bmgr.disable_jail(params[1])
            except F2BConfigNotFound, e:
                self.put_message('err', e)
        if params[0] == 'edef':
            self._stab = 1
            try:
                self._f2bmgr.enable_all(self.f2brules[int(params[1])])
            except F2BConfigNotFound, e:
                self.put_message('err', e)
        if params[0] == 'ddef':
            self._stab = 1
            try:
                self._f2bmgr.disable_all(self.f2brules[int(params[1])])
            except F2BConfigNotFound, e:
                self.put_message('err', e)
        if params[0] == 'reinit':
            self._stab = 3
            self._fwmgr.initialize()
        if params[0] == 'apply':
            self._stab = 2
            self._error = self.cfg.apply_now()
        if params[0] == 'autostart':
            self._stab = 2
            self.cfg.set_autostart(True)
        if params[0] == 'noautostart':
            self._stab = 2
            self.cfg.set_autostart(False)
        if params[0] == 'loadruntime':
            self._stab = 2
            self.cfg.load_runtime()
        if params[0] == 'setdefault':
            self._stab = 2
            self._tab = self.cfg.table_index(params[1])
            self.cfg.tables[params[1]].chains[params[2]].default = params[3]
            self.cfg.save()
        if params[0] == 'shuffle':
            self._stab = 2
            self._tab = self.cfg.table_index(params[1])
            self._shuffling_table = params[1]
            self._shuffling = params[2]
        if params[0] == 'addchain':
            self._stab = 2
            self._tab = self.cfg.table_index(params[1])
            self._adding_chain = params[1]
        if params[0] == 'deletechain':
            self._stab = 2
            self._tab = self.cfg.table_index(params[1])
            self.cfg.tables[params[1]].chains.pop(params[2])
            self.cfg.save()
        if params[0] == 'addrule':
            self._stab = 2
            self._tab = self.cfg.table_index(params[1])
            self._editing_table = params[1]
            self._editing_chain = params[2]
            ch = self.cfg.tables[self._editing_table].\
                         chains[self._editing_chain]
            self._editing_rule = len(ch.rules)
            ch.rules.append(Rule('-A %s -j ACCEPT'%params[2]))
            self.cfg.save()
        if params[0] == 'deleterule':
            self._stab = 2
            self.cfg.tables[self._editing_table].\
                     chains[self._editing_chain].\
                     rules.pop(self._editing_rule)
            self._editing_chain = None
            self._editing_table = None
            self._editing_rule = None
            self.cfg.save()

    @event('fwrule/click')
    def on_fwrclick(self, event, params, vars=None):
        self._stab = 2
        self._tab = self.cfg.table_index(params[0])
        self._editing_table = params[0]
        self._editing_chain = params[1]
        self._editing_rule = int(params[2])

    @event('form/submit')
    @event('dialog/submit')
    def on_submit(self, event, params, vars):
        if params[0] == 'frmDefense':
            self._stab = 3
            if vars.getvalue('action', '') == 'OK':
                try:
                    self._f2bmgr.maxretry(vars.getvalue('f2b_maxretry', ''))
                    self._f2bmgr.findtime(vars.getvalue('f2b_findtime', ''))
                    self._f2bmgr.bantime(vars.getvalue('f2b_bantime', ''))
                except F2BConfigNotFound:
                    pass
        if params[0] == 'dlgF2BInfo':
            self._stab = 1
            self._idef = None
        if params[0] == 'dlgAddChain':
            if vars.getvalue('action', '') == 'OK':
                n = vars.getvalue('value', '')
                if n == '': return
                self.cfg.tables[self._adding_chain].chains[n] = Chain(n, '-')
                self.cfg.save()
            self._stab = 2
            self._adding_chain = None
        if params[0] == 'dlgShuffler':
            if vars.getvalue('action', '') == 'OK':
                d = vars.getvalue('list', '').split('|')
                ch = self.cfg.tables[self._shuffling_table].chains[self._shuffling]
                ch.rules = []
                for s in d:
                    ch.rules.append(Rule(s))
                self.cfg.save()
            self._stab = 2
            self._shuffling = None
            self._shuffling_table = None
        if params[0] == 'dlgEditRule':
            if vars.getvalue('action', '') == 'OK':
                self.cfg.tables[self._editing_table].\
                         chains[self._editing_chain].\
                          rules[self._editing_rule].apply_vars(vars)
                self.cfg.save()
            self._stab = 2
            self._editing_chain = None
            self._editing_table = None
            self._editing_rule = None

########NEW FILE########
__FILENAME__ = backend
from genesis.api import *
from genesis.com import *
import json


class Backend (Plugin):
    default_binary = { 'good_state': True }
    default_decimal = { 'limit_susp': 33.0, 'limit_dang': 66.0 }

    def __init__(self):
        self.cfg = self._get_cfg()

    def list_meters(self, category=None):
        return filter(lambda x:(not category)or(x.category==category),
             sorted(self.app.grab_plugins(IMeter), key=lambda x: x.name))

    def get_meter(self, cls, var):
        return filter(lambda x:x.plugin_id==cls, self.app.grab_plugins(IMeter))[0].prepare(var)

    def list_variated(self, x):
        for v in x.get_variants():
            yield x.prepare(v)

    def _get_cfg(self):
        return json.loads(self.app.config.get('meters', 'config', '{}'))

    def _save_cfg(self):
        self.app.gconfig.set('meters', 'config', json.dumps(self.cfg))
        self.app.gconfig.save()

    def has_cfg(self, cls, var):
        return cls in self.cfg and var in self.cfg[cls]

    def get_cfg(self, cls, var):
        if not self.has_cfg(cls, var):
            return {}
        return self.cfg[cls][var]

    def set_cfg(self, cls, var, cfg):
        print cfg
        self.cfg.setdefault(cls, {})[var] = cfg
        self._save_cfg()

    def del_cfg(self, cls, var):
        del self.cfg[cls][var]
        if self.cfg[cls] == {}:
            del self.cfg[cls]
        self._save_cfg()

########NEW FILE########
__FILENAME__ = main
from genesis.api import *
from genesis.ui import *
from backend import Backend
import trans


class SysAlertsPlugin(CategoryPlugin):
    text = 'Alerts'
    iconfont = 'gen-warning'
    folder = 'bottom'

    def on_init(self):
        self.backend = Backend(self.app)
        self.mon = ComponentManager.get().find('sysalerts-monitor')

    def on_session_start(self):
        self._settings = False
        self._configuring = None

    def get_counter(self):
        lst = ComponentManager.get().find('sysalerts-monitor').get()
        return len(filter(lambda x:x!='good', lst.values())) or None

    def get_ui(self):
        ui = self.app.inflate('sysalerts:main')

        ostat = 'good'

        stat = { 'good': 'info', 'susp': 'warn', 'dang': 'err' }
        text = { 'good': 'GOOD', 'susp': 'WARNING', 'dang': 'DANGER' }

        for m in sorted(self.mon.get(), key=lambda x:x.name):
            st = self.mon.get()[m]
            if st == 'susp' and ostat == 'good':
                ostat = st
            if st == 'dang':
                ostat = st
            ui.append('list', UI.DTR(
                UI.StatusCell(status=stat[st], text=text[st]),
                UI.DTD(
                    UI.Label(text=m.name, bold=True),
                    UI.Label(text=m.text),
                ),
                UI.Label(
                    text=getattr(trans, 'trans_%s'%m.transform)(m.format_value())
                ),
                UI.DTD(
                    UI.TipIcon(
                        iconfont="gen-pencil-2",
                        id='config/%s/%s'%(m.plugin_id,m.variant),
                        text='Configure',
                    ),
                ),
            ))

        if self._settings:
            ui.append('main', self.get_ui_settings())

        if self._configuring:
            ui.append('main', getattr(self, 'get_ui_cfg_%s'%self._configuring.type)(self._configuring))

        return ui

    def get_ui_settings(self):
        ui = self.app.inflate('sysalerts:settings')

        for m in self.backend.list_meters():
            for v in self.backend.list_variated(m):
                ui.append('list', UI.DTR(
                    UI.DTD(
                        UI.Label(text=v.name, bold=True),
                        UI.Label(text=v.text),
                    ),
                    UI.DTD(
                        UI.TipIcon(
                            iconfont="gen-pencil-2",
                            id='config/%s/%s'%(m.plugin_id,v.variant),
                            text='Configure',
                        ),
                        UI.TipIcon(
                            iconfont="gen-cancel-circle",
                            id='disable/%s/%s'%(m.plugin_id,v.variant),
                            text='Disable',
                        ) if self.backend.has_cfg(m.plugin_id,v.variant) else None,
                    ),
                ))
        return ui

    @event('button/click')
    def on_click(self, event, params, vars=None):
        if params[0] == 'btnRefresh':
            self.mon.refresh()
        if params[0] == 'btnSettings':
            self._settings = True
        if params[0] == 'config':
            self._configuring = self.backend.get_meter(*params[1:])
        if params[0] == 'disable':
            self.backend.del_cfg(*params[1:])
            self.mon.refresh()

    @event('dialog/submit')
    def on_submit(self, event, params, vars=None):
        if params[0] == 'dlgSettings':
            self._settings = False
        if params[0] == 'dlgConfigure':
            if vars.getvalue('action', None) == 'OK':
                try:
                    getattr(self, 'apply_cfg_%s'%(self._configuring.type))(self._configuring, vars)
                except:
                    self.app.log.error('Invalid meter configuration')
                self.mon.refresh()
            self._configuring = None

    def get_ui_cfg_binary(self, cls):
        ui = self.app.inflate('sysalerts:cfg-binary')
        t = self.backend.get_cfg(cls.plugin_id, cls.variant).setdefault('good_state', True)
        ui.find('r-true').set('checked', t)
        ui.find('r-false').set('checked', not t)
        return ui

    def get_ui_cfg_decimal(self, cls):
        ui = self.app.inflate('sysalerts:cfg-decimal')
        c = self.backend.get_cfg(cls.plugin_id, cls.variant)
        ui.find('limit_susp').set('value', str(c.setdefault('limit_susp', 33.0)))
        ui.find('limit_dang').set('value', str(c.setdefault('limit_dang', 66.0)))
        return ui

    def get_ui_cfg_linear(self, cls):
        ui = self.app.inflate('sysalerts:cfg-linear')
        c = self.backend.get_cfg(cls.plugin_id, cls.variant)
        ui.find('limit_susp').set('value', str(c.setdefault('limit_susp', 33.0)))
        ui.find('limit_dang').set('value', str(c.setdefault('limit_dang', 66.0)))
        ui.find('max').set('text', 'Min: %.2f, max: %.2f'%(cls.get_min(), cls.get_max()))
        return ui

    def apply_cfg_binary(self, cls, vars):
        self.backend.set_cfg(cls.plugin_id, cls.variant, {'good_state': eval(vars.getvalue('val', 'True'))})

    def apply_cfg_decimal(self, cls, vars):
        self.backend.set_cfg(cls.plugin_id, cls.variant, {
            'limit_susp': float(vars.getvalue('lim_susp', True)),
            'limit_dang': float(vars.getvalue('lim_dang', True)),
        })

    apply_cfg_linear = apply_cfg_decimal

########NEW FILE########
__FILENAME__ = monitor
from genesis.api import *
from genesis.com import *
import threading
import json



class SysAlertsMonitor (Component):
    name = 'sysalerts-monitor'

    def on_starting(self):
        self._cond_refresh = threading.Condition()
        self._cond_refreshed = threading.Condition()
        self._lock_refresh = threading.Lock()
        self._state = {}

    def refresh(self):
        with self._lock_refresh:
            with self._cond_refresh:
                self._cond_refresh.notify()
        with self._cond_refreshed:
            self._cond_refreshed.wait()

    def iterate(self):
        cfg = json.loads(self.app.gconfig.get('meters', 'config'))
        res = {}
        for cls in cfg:
            try:
                inst = self.app.grab_plugins(IMeter, lambda x:x.plugin_id==cls)[0]
                for var in cfg[cls]:
                    constr = cfg[cls][var]
                    i = inst.prepare(var)
                    res[i] = getattr(self, 'validate_%s'%i.type)(i.format_value(), constr)
            except:
                pass
        self._state = res

    def get(self):
        return self._state

    def run(self):
        while True:
            with self._lock_refresh:
                try:
                    self.iterate()
                except:
                    pass
            with self._cond_refreshed:
                self._cond_refreshed.notify()
            with self._cond_refresh:
                self._cond_refresh.wait(1000*60*5)

    def validate_binary(self, val, cfg):
        return 'good' if val['value'] == cfg['good_state'] else 'dang'

    def validate_decimal(self, val, cfg):
        if cfg['limit_susp'] < cfg['limit_dang']:
            if val['value'] < cfg['limit_susp']:
                return 'good'
            if val['value'] > cfg['limit_dang']:
                return 'dang'
        if cfg['limit_susp'] > cfg['limit_dang']:
            if val['value'] > cfg['limit_susp']:
                return 'good'
            if val['value'] < cfg['limit_dang']:
                return 'dang'
        return 'susp'

    validate_linear = validate_decimal



class MetersExporter (Plugin, URLHandler):

    @url('^/api/meters$')
    def export(self, req, sr):
        clss = self.app.grab_plugins(IMeter)
        r = {}

        for cls in clss:
            variants = cls.get_variants()
            for v in variants:
                inst = cls.prepare(v)
                r.setdefault(cls.category, {}).setdefault(cls.plugin_id, {})[v] = \
                    {
                        'name': inst.name,
                        'mtype': inst.type,
                        'text': inst.text,
                        'variant': v,
                        'transform': inst.transform,
                        'data': inst.format_value(),
                    }

        return json.dumps(r)



class SysAlertsExporter (Plugin, URLHandler):

    @url('^/api/alerts$')
    def export(self, req, sr):
        mon = ComponentManager.get().find('sysalerts-monitor')
        data = json.loads(self.app.gconfig.get('meters', 'config', '{}'))
        nd = {}
        mon.refresh()
        for i in mon.get():
            nd.setdefault(i.category, {}).setdefault(i.plugin_id, {})[i.variant] = {
                'value': i.format_value(),
                'info': {
                    'text': i.text,
                    'name': i.name,
                    'type': i.type,
                    'variant': i.variant,
                    'transform': i.transform,
                },
                'contraints': data[i.plugin_id][i.variant],
                'state': mon.get()[i],
            }
        return json.dumps(nd)

########NEW FILE########
__FILENAME__ = trans
from genesis.utils import str_fsize

def trans_None(x):
    return x

def trans_float(x):
    return '%.2f'%x['value']

def trans_fsize(x):
    return str_fsize(int(x['value']))

def trans_percent(x):
    if float(x['max']) == float(x['min']):
        return '0%'
    return '%.2f%%'%((float(x['value'])-float(x['min']))/(float(x['max'])-float(x['min']))*100)

def trans_fsize_percent(x):
    return '%s (%s)'%(trans_fsize(x), trans_percent(x))

def trans_yesno(x):
    return 'Yes' if x['value'] else 'No'

def trans_onoff(x):
    return 'On' if x['value'] else 'Off'

def trans_running(x):
    return 'Running' if x['value'] else 'Stopped'

########NEW FILE########
__FILENAME__ = widget
from genesis.ui import *
from genesis import apis
from genesis.com import implements, Plugin
from genesis.api import *


class SysAlertsWidget(Plugin):
    implements(apis.dashboard.IWidget)
    title = 'Alerts'
    iconfont = 'gen-warning'
    name = 'System alerts'
    style = 'linear'

    def get_ui(self, cfg, id=None):
        self.mon = ComponentManager.get().find('sysalerts-monitor')
        text = { 'good': 'GOOD', 'susp': 'WARNING', 'dang': 'DANGER' }
        stat = { 'good': 'info', 'susp': 'warn', 'dang': 'err' }
        ostat = 'good'
        for m in sorted(self.mon.get(), key=lambda x:x.name):
            st = self.mon.get()[m]
            if st == 'susp' and ostat == 'good':
                ostat = st
            if st == 'dang':
                ostat = st

        ui = self.app.inflate('sysalerts:widget')
        ui.find('overall').text = text[ostat]
        ui.find('overall')['class'] = 'status-cell-%s'%stat[ostat]
        return ui

    def handle(self, event, params, cfg, vars=None):
        pass

    def get_config_dialog(self):
        pass

    def process_config(self, vars):
        pass

########NEW FILE########
__FILENAME__ = main
from genesis.api import *
from genesis.ui import *
from genesis import apis
from genesis.utils import shell_cs, SystemTime
from genesis.plugins.network import backend

import os
import re

import zonelist


class SysConfigPlugin(CategoryPlugin):
    text = 'System Settings'
    iconfont = 'gen-cog'
    folder = False

    def on_init(self):
        self._mgr = self.app.get_backend(apis.services.IServiceManager)
        self._be = backend.Config(self.app)
        self._st = SystemTime()
        self.hostname = self._be.gethostname()

    def get_ui(self):
        ui = self.app.inflate('sysconfig:main')
        systime = self._st.get_datetime('%s, %s' \
            % (self.app.gconfig.get('genesis', 'dformat', '%d %b %Y'), 
                self.app.gconfig.get('genesis', 'tformat', '%H:%M')))
        offset = 0
        try:
            offset = self._st.get_offset()
        except Exception, e:
            self.app.log.error('Could not get Internet time. Please check your connection. Error: %s' % str(e))
            self.put_message('err', 'Could not get Internet time. Please check your connection.')

        # General
        ui.find('hostname').set('value', self.hostname)
        tz_active = os.path.realpath('/etc/localtime').split('/usr/share/zoneinfo/')[1] if os.path.exists('/etc/localtime') else ''
        tz_sel = [UI.SelectOption(text=x, value=x, 
            selected=True if tz_active in x else False)
            for x in zonelist.zones]
        ui.appendAll('zoneselect', *tz_sel)

        # Time
        ui.find('systime').set('text', systime)
        ui.find('offset').set('text', '%s seconds' % offset)

        # Tools
        if shell_cs('which logrunnerd')[0] != 0:
            lrstat = 'Not installed'
        else:
            if self._mgr.get_status('logrunner') == 'running':
                lrstat = 'Running'
                ui.find('fllogrunner').append(UI.Button(text="Stop", id="svc/logrunner/stop"))
            else:
                lrstat = 'Not running'
                ui.find('fllogrunner').append(UI.Button(text="Start", id="svc/logrunner/start"))
            if self._mgr.get_enabled('logrunner') == 'enabled':
                lrstat += ' and enabled on boot'
                ui.find('fllogrunner').append(UI.Button(text="Disable on boot", id="svc/logrunner/disable"))
            else:
                lrstat += ' and not enabled on boot'
                ui.find('fllogrunner').append(UI.Button(text="Enable on boot", id="svc/logrunner/enable"))
        if shell_cs('which beacond')[0] != 0:
            bestat = 'Not installed'
        else:
            if self._mgr.get_status('beacon') == 'running':
                bestat = 'Running'
                ui.find('flbeacon').append(UI.Button(text="Stop", id="svc/beacon/stop"))
            else:
                bestat = 'Not running'
                ui.find('flbeacon').append(UI.Button(text="Start", id="svc/beacon/start"))
            if self._mgr.get_enabled('beacon') == 'enabled':
                bestat += ' and enabled on boot'
                ui.find('flbeacon').append(UI.Button(text="Disable on boot", id="svc/beacon/disable"))
            else:
                bestat += ' and not enabled on boot'
                ui.find('flbeacon').append(UI.Button(text="Enable on boot", id="svc/beacon/enable"))
        ui.find('logrunner').set('text', lrstat)
        ui.find('beacon').set('text', bestat)

        if self._changed:
            self.put_message('warn', 'A restart is required for this setting change to take effect.')

        return ui

    @event('button/click')
    def on_click(self, event, params, vars=None):
        if params[0] == 'svc':
            if params[2] == 'start':
                self._mgr.start(params[1])
            elif params[2] == 'stop':
                self._mgr.stop(params[1])
            elif params[2] == 'enable':
                self._mgr.enable(params[1])
            elif params[2] == 'disable':
                self._mgr.disable(params[1])
        if params[0] == 'settime':
            try:
                self._st.set_datetime()
                self.put_message('info', 'System time updated successfully')
            except Exception, e:
                self.app.log.error('Could not set time. Please check your connection. Error: %s' % str(e))
                self.put_message('err', 'Could not set time. Please check your connection.')

    @event('form/submit')
    @event('dialog/submit')
    def on_submit(self, event, params, vars=None):
        if params[0] == 'frmGeneral':
            if vars.getvalue('action', '') == 'OK':
                hn = vars.getvalue('hostname', '')
                zone = vars.getvalue('zoneselect', 'UTC')
                if not hn:
                    self.put_message('err', 'Hostname must not be empty')
                elif not re.search('^[a-zA-Z0-9.-]', hn) or re.search('(^-.*|.*-$)', hn):
                    self.put_message('err', 'Hostname must only contain '
                        'letters, numbers, hyphens or periods, and must '
                        'not start or end with a hyphen.')
                else:
                    self._be.sethostname(vars.getvalue('hostname'))
                zone = zone.split('/')
                if len(zone) > 1:
                    zonepath = os.path.join('/usr/share/zoneinfo', zone[0], zone[1])
                else:
                    zonepath = os.path.join('/usr/share/zoneinfo', zone[0])
                if os.path.exists('/etc/localtime'):
                    os.remove('/etc/localtime')
                os.symlink(zonepath, '/etc/localtime')
                self.put_message('info', 'Settings saved.')

########NEW FILE########
__FILENAME__ = zonelist
zones = ['Africa/Abidjan', 'Africa/Accra', 'Africa/Addis_Ababa', 'Africa/Algiers', 'Africa/Asmara', 'Africa/Asmera', 'Africa/Bamako', 'Africa/Bangui', 'Africa/Banjul', 'Africa/Bissau', 'Africa/Blantyre', 'Africa/Brazzaville', 'Africa/Bujumbura', 'Africa/Cairo', 'Africa/Casablanca', 'Africa/Ceuta', 'Africa/Conakry', 'Africa/Dakar', 'Africa/Dar_es_Salaam', 'Africa/Djibouti', 'Africa/Douala', 'Africa/El_Aaiun', 'Africa/Freetown', 'Africa/Gaborone', 'Africa/Harare', 'Africa/Johannesburg', 'Africa/Juba', 'Africa/Kampala', 'Africa/Khartoum', 'Africa/Kigali', 'Africa/Kinshasa', 'Africa/Lagos', 'Africa/Libreville', 'Africa/Lome', 'Africa/Luanda', 'Africa/Lubumbashi', 'Africa/Lusaka', 'Africa/Malabo', 'Africa/Maputo', 'Africa/Maseru', 'Africa/Mbabane', 'Africa/Mogadishu', 'Africa/Monrovia', 'Africa/Nairobi', 'Africa/Ndjamena', 'Africa/Niamey', 'Africa/Nouakchott', 'Africa/Ouagadougou', 'Africa/Porto-Novo', 'Africa/Sao_Tome', 'Africa/Timbuktu', 'Africa/Tripoli', 'Africa/Tunis', 'Africa/Windhoek', 'America/Adak', 'America/Anchorage', 'America/Anguilla', 'America/Antigua', 'America/Araguaina', 'America/Argentina', 'America/Aruba', 'America/Asuncion', 'America/Atikokan', 'America/Atka', 'America/Bahia', 'America/Bahia_Banderas', 'America/Barbados', 'America/Belem', 'America/Belize', 'America/Blanc-Sablon', 'America/Boa_Vista', 'America/Bogota', 'America/Boise', 'America/Buenos_Aires', 'America/Cambridge_Bay', 'America/Campo_Grande', 'America/Cancun', 'America/Caracas', 'America/Catamarca', 'America/Cayenne', 'America/Cayman', 'America/Chicago', 'America/Chihuahua', 'America/Coral_Harbour', 'America/Cordoba', 'America/Costa_Rica', 'America/Creston', 'America/Cuiaba', 'America/Curacao', 'America/Danmarkshavn', 'America/Dawson', 'America/Dawson_Creek', 'America/Denver', 'America/Detroit', 'America/Dominica', 'America/Edmonton', 'America/Eirunepe', 'America/El_Salvador', 'America/Ensenada', 'America/Fortaleza', 'America/Fort_Wayne', 'America/Glace_Bay', 'America/Godthab', 'America/Goose_Bay', 'America/Grand_Turk', 'America/Grenada', 'America/Guadeloupe', 'America/Guatemala', 'America/Guayaquil', 'America/Guyana', 'America/Halifax', 'America/Havana', 'America/Hermosillo', 'America/Indiana', 'America/Indianapolis', 'America/Inuvik', 'America/Iqaluit', 'America/Jamaica', 'America/Jujuy', 'America/Juneau', 'America/Kentucky', 'America/Knox_IN', 'America/Kralendijk', 'America/La_Paz', 'America/Lima', 'America/Los_Angeles', 'America/Louisville', 'America/Lower_Princes', 'America/Maceio', 'America/Managua', 'America/Manaus', 'America/Marigot', 'America/Martinique', 'America/Matamoros', 'America/Mazatlan', 'America/Mendoza', 'America/Menominee', 'America/Merida', 'America/Metlakatla', 'America/Mexico_City', 'America/Miquelon', 'America/Moncton', 'America/Monterrey', 'America/Montevideo', 'America/Montreal', 'America/Montserrat', 'America/Nassau', 'America/New_York', 'America/Nipigon', 'America/Nome', 'America/Noronha', 'America/North_Dakota', 'America/Ojinaga', 'America/Panama', 'America/Pangnirtung', 'America/Paramaribo', 'America/Phoenix', 'America/Port-au-Prince', 'America/Porto_Acre', 'America/Port_of_Spain', 'America/Porto_Velho', 'America/Puerto_Rico', 'America/Rainy_River', 'America/Rankin_Inlet', 'America/Recife', 'America/Regina', 'America/Resolute', 'America/Rio_Branco', 'America/Rosario', 'America/Santa_Isabel', 'America/Santarem', 'America/Santiago', 'America/Santo_Domingo', 'America/Sao_Paulo', 'America/Scoresbysund', 'America/Shiprock', 'America/Sitka', 'America/St_Barthelemy', 'America/St_Johns', 'America/St_Kitts', 'America/St_Lucia', 'America/St_Thomas', 'America/St_Vincent', 'America/Swift_Current', 'America/Tegucigalpa', 'America/Thule', 'America/Thunder_Bay', 'America/Tijuana', 'America/Toronto', 'America/Tortola', 'America/Vancouver', 'America/Virgin', 'America/Whitehorse', 'America/Winnipeg', 'America/Yakutat', 'America/Yellowknife', 'Antarctica/Casey', 'Antarctica/Davis', 'Antarctica/DumontDUrville', 'Antarctica/Macquarie', 'Antarctica/Mawson', 'Antarctica/McMurdo', 'Antarctica/Palmer', 'Antarctica/Rothera', 'Antarctica/South_Pole', 'Antarctica/Syowa', 'Antarctica/Vostok', 'Arctic/Longyearbyen', 'Asia/Aden', 'Asia/Almaty', 'Asia/Amman', 'Asia/Anadyr', 'Asia/Aqtau', 'Asia/Aqtobe', 'Asia/Ashgabat', 'Asia/Ashkhabad', 'Asia/Baghdad', 'Asia/Bahrain', 'Asia/Baku', 'Asia/Bangkok', 'Asia/Beirut', 'Asia/Bishkek', 'Asia/Brunei', 'Asia/Calcutta', 'Asia/Choibalsan', 'Asia/Chongqing', 'Asia/Chungking', 'Asia/Colombo', 'Asia/Dacca', 'Asia/Damascus', 'Asia/Dhaka', 'Asia/Dili', 'Asia/Dubai', 'Asia/Dushanbe', 'Asia/Gaza', 'Asia/Harbin', 'Asia/Hebron', 'Asia/Ho_Chi_Minh', 'Asia/Hong_Kong', 'Asia/Hovd', 'Asia/Irkutsk', 'Asia/Istanbul', 'Asia/Jakarta', 'Asia/Jayapura', 'Asia/Jerusalem', 'Asia/Kabul', 'Asia/Kamchatka', 'Asia/Karachi', 'Asia/Kashgar', 'Asia/Kathmandu', 'Asia/Katmandu', 'Asia/Khandyga', 'Asia/Kolkata', 'Asia/Krasnoyarsk', 'Asia/Kuala_Lumpur', 'Asia/Kuching', 'Asia/Kuwait', 'Asia/Macao', 'Asia/Macau', 'Asia/Magadan', 'Asia/Makassar', 'Asia/Manila', 'Asia/Muscat', 'Asia/Nicosia', 'Asia/Novokuznetsk', 'Asia/Novosibirsk', 'Asia/Omsk', 'Asia/Oral', 'Asia/Phnom_Penh', 'Asia/Pontianak', 'Asia/Pyongyang', 'Asia/Qatar', 'Asia/Qyzylorda', 'Asia/Rangoon', 'Asia/Riyadh', 'Asia/Riyadh87', 'Asia/Riyadh88', 'Asia/Riyadh89', 'Asia/Saigon', 'Asia/Sakhalin', 'Asia/Samarkand', 'Asia/Seoul', 'Asia/Shanghai', 'Asia/Singapore', 'Asia/Taipei', 'Asia/Tashkent', 'Asia/Tbilisi', 'Asia/Tehran', 'Asia/Tel_Aviv', 'Asia/Thimbu', 'Asia/Thimphu', 'Asia/Tokyo', 'Asia/Ujung_Pandang', 'Asia/Ulaanbaatar', 'Asia/Ulan_Bator', 'Asia/Urumqi', 'Asia/Ust-Nera', 'Asia/Vientiane', 'Asia/Vladivostok', 'Asia/Yakutsk', 'Asia/Yekaterinburg', 'Asia/Yerevan', 'Atlantic/Azores', 'Atlantic/Bermuda', 'Atlantic/Canary', 'Atlantic/Cape_Verde', 'Atlantic/Faeroe', 'Atlantic/Faroe', 'Atlantic/Jan_Mayen', 'Atlantic/Madeira', 'Atlantic/Reykjavik', 'Atlantic/South_Georgia', 'Atlantic/Stanley', 'Atlantic/St_Helena', 'Australia/ACT', 'Australia/Adelaide', 'Australia/Brisbane', 'Australia/Broken_Hill', 'Australia/Canberra', 'Australia/Currie', 'Australia/Darwin', 'Australia/Eucla', 'Australia/Hobart', 'Australia/LHI', 'Australia/Lindeman', 'Australia/Lord_Howe', 'Australia/Melbourne', 'Australia/North', 'Australia/NSW', 'Australia/Perth', 'Australia/Queensland', 'Australia/South', 'Australia/Sydney', 'Australia/Tasmania', 'Australia/Victoria', 'Australia/West', 'Australia/Yancowinna', 'Brazil/Acre', 'Brazil/DeNoronha', 'Brazil/East', 'Brazil/West', 'Canada/Atlantic', 'Canada/Central', 'Canada/Eastern', 'Canada/East-Saskatchewan', 'Canada/Mountain', 'Canada/Newfoundland', 'Canada/Pacific', 'Canada/Saskatchewan', 'Canada/Yukon', 'Chile/Continental', 'Chile/EasterIsland', 'Etc/GMT', 'Etc/GMT0', 'Etc/GMT-0', 'Etc/GMT+0', 'Etc/GMT-1', 'Etc/GMT+1', 'Etc/GMT-10', 'Etc/GMT+10', 'Etc/GMT-11', 'Etc/GMT+11', 'Etc/GMT-12', 'Etc/GMT+12', 'Etc/GMT-13', 'Etc/GMT-14', 'Etc/GMT-2', 'Etc/GMT+2', 'Etc/GMT-3', 'Etc/GMT+3', 'Etc/GMT-4', 'Etc/GMT+4', 'Etc/GMT-5', 'Etc/GMT+5', 'Etc/GMT-6', 'Etc/GMT+6', 'Etc/GMT-7', 'Etc/GMT+7', 'Etc/GMT-8', 'Etc/GMT+8', 'Etc/GMT-9', 'Etc/GMT+9', 'Etc/Greenwich', 'Etc/UCT', 'Etc/Universal', 'Etc/UTC', 'Etc/Zulu', 'Europe/Amsterdam', 'Europe/Andorra', 'Europe/Athens', 'Europe/Belfast', 'Europe/Belgrade', 'Europe/Berlin', 'Europe/Bratislava', 'Europe/Brussels', 'Europe/Bucharest', 'Europe/Budapest', 'Europe/Busingen', 'Europe/Chisinau', 'Europe/Copenhagen', 'Europe/Dublin', 'Europe/Gibraltar', 'Europe/Guernsey', 'Europe/Helsinki', 'Europe/Isle_of_Man', 'Europe/Istanbul', 'Europe/Jersey', 'Europe/Kaliningrad', 'Europe/Kiev', 'Europe/Lisbon', 'Europe/Ljubljana', 'Europe/London', 'Europe/Luxembourg', 'Europe/Madrid', 'Europe/Malta', 'Europe/Mariehamn', 'Europe/Minsk', 'Europe/Monaco', 'Europe/Moscow', 'Europe/Nicosia', 'Europe/Oslo', 'Europe/Paris', 'Europe/Podgorica', 'Europe/Prague', 'Europe/Riga', 'Europe/Rome', 'Europe/Samara', 'Europe/San_Marino', 'Europe/Sarajevo', 'Europe/Simferopol', 'Europe/Skopje', 'Europe/Sofia', 'Europe/Stockholm', 'Europe/Tallinn', 'Europe/Tirane', 'Europe/Tiraspol', 'Europe/Uzhgorod', 'Europe/Vaduz', 'Europe/Vatican', 'Europe/Vienna', 'Europe/Vilnius', 'Europe/Volgograd', 'Europe/Warsaw', 'Europe/Zagreb', 'Europe/Zaporozhye', 'Europe/Zurich', 'GMT', 'Indian/Antananarivo', 'Indian/Chagos', 'Indian/Christmas', 'Indian/Cocos', 'Indian/Comoro', 'Indian/Kerguelen', 'Indian/Mahe', 'Indian/Maldives', 'Indian/Mauritius', 'Indian/Mayotte', 'Indian/Reunion', 'Mexico/BajaNorte', 'Mexico/BajaSur', 'Mexico/General', 'Mideast/Riyadh87', 'Mideast/Riyadh88', 'Mideast/Riyadh89', 'Pacific/Apia', 'Pacific/Auckland', 'Pacific/Chatham', 'Pacific/Chuuk', 'Pacific/Easter', 'Pacific/Efate', 'Pacific/Enderbury', 'Pacific/Fakaofo', 'Pacific/Fiji', 'Pacific/Funafuti', 'Pacific/Galapagos', 'Pacific/Gambier', 'Pacific/Guadalcanal', 'Pacific/Guam', 'Pacific/Honolulu', 'Pacific/Johnston', 'Pacific/Kiritimati', 'Pacific/Kosrae', 'Pacific/Kwajalein', 'Pacific/Majuro', 'Pacific/Marquesas', 'Pacific/Midway', 'Pacific/Nauru', 'Pacific/Niue', 'Pacific/Norfolk', 'Pacific/Noumea', 'Pacific/Pago_Pago', 'Pacific/Palau', 'Pacific/Pitcairn', 'Pacific/Pohnpei', 'Pacific/Ponape', 'Pacific/Port_Moresby', 'Pacific/Rarotonga', 'Pacific/Saipan', 'Pacific/Samoa', 'Pacific/Tahiti', 'Pacific/Tarawa', 'Pacific/Tongatapu', 'Pacific/Truk', 'Pacific/Wake', 'Pacific/Wallis', 'Pacific/Yap', 'US/Alaska', 'US/Aleutian', 'US/Arizona', 'US/Central', 'US/Eastern', 'US/East-Indiana', 'US/Hawaii', 'US/Indiana-Starke', 'US/Michigan', 'US/Mountain', 'US/Pacific', 'US/Pacific-New', 'US/Samoa', 'UTC']

########NEW FILE########
__FILENAME__ = api
from genesis.com import *
from genesis.apis import API
from genesis.api import CategoryPlugin, event
from genesis import apis
from genesis.ui import UI
from base64 import b64encode, b64decode


class Dashboard (API):
    """
    Dashboard API
    """
    class IWidget(Interface):
        """
        Interface for a dashboard widget

        - ``iconfont`` - `str`, iconfont class
        - ``title`` - `str`, short title text
        - ``name`` - `str`, name shown in 'choose widget' dialog
        - ``style`` - `str`, 'normal' and 'linear' now supported
        """
        title = ''
        name = ''
        iconfont = ''
        style = 'normal'

        def get_ui(self, cfg, id=None):
            """
            Returns plugin UI (Layout or Element)

            :param  id:     plugin ID
            :type   id:     str
            :param  cfg:    saved plugin configuration
            :type   cfg:    str
            """

        def handle(self, event, params, cfg, vars=None):
            """
            Handles UI event of a plugin

            :param  cfg:    saved plugin configuration
            :type   cfg:    str
            """

        def get_config_dialog(self):
            """
            Returns configuration dialog UI (Layout or Element), or None
            """

        def process_config(self, vars):
            """
            Saves configuration from the configuration dialog (get_config_dialog)

            :rtype   cfg:    str
            """

    class WidgetManager (Plugin):
        def __init__(self):
            self.refresh()

        def refresh(self):
            self._left = []
            self._right = []
            self._widgets = {}

            try:
                self._left = [int(x) for x in self.app.config.get('dashboard', 'left').split(',')]
                self._right = [int(x) for x in self.app.config.get('dashboard', 'right').split(',')]
            except:
                pass

            for x in (self._left + self._right):
                self._widgets[x] = (
                    self.app.config.get('dashboard', '%i-class'%x),
                    eval(b64decode(self.app.config.get('dashboard', '%i-cfg'%x)))
                )

        def list_left(self): return self._left
        def list_right(self): return self._right

        def add_widget(self, id, cfg):
            if id.__class__ is not str:
                id = id.plugin_id
            idx = 0
            while idx in self._widgets:
                idx += 1
            self._widgets[idx] = (id, cfg)
            self._left.append(idx)
            self.save_cfg()

        def reorder(self, nl, nr):
            self._left = nl
            self._right = nr
            self.save_cfg()

        def remove_widget(self, id):
            if id in self._right:
                self._right.remove(id)
            else:
                self._left.remove(id)
            del self._widgets[id]
            self.app.config.remove_option('dashboard', '%i-class'%id)
            self.app.config.remove_option('dashboard', '%i-cfg'%id)
            self.save_cfg()

        def save_cfg(self):
            self.app.config.set('dashboard', 'left', ','.join(str(x) for x in self._left))
            self.app.config.set('dashboard', 'right', ','.join(str(x) for x in self._right))
            for x in self._widgets:
                self.app.config.set('dashboard', '%i-class'%x, self._widgets[x][0])
                self.app.config.set(
                    'dashboard', '%i-cfg'%x,
                    b64encode(repr(self._widgets[x][1]))
                )
            self.app.config.save()

        def get_widget_object(self, id):
            return self.get_by_name(self._widgets[id][0])

        def get_widget_config(self, id):
            return self._widgets[id][1]

        def get_by_name(self, id):
            try:
                return self.app.grab_plugins(
                   apis.dashboard.IWidget,
                   lambda x:x.plugin_id==id,
                )[0]
            except:
                return None


class SysStat(API):
    class ISysStat(Interface):
        def get_load(self):
            pass
        
        def get_ram(self):
            pass
            
        def get_swap(self):
            pass


class Services(API):
    class IServiceManager(Interface):
        def list_all(self):
            pass

        def get_status(self, name):
            pass

        def start(self, name):
            pass

        def stop(self, name):
            pass

        def restart(self, name):
            pass


    class Service:
        name = ''

        @property
        def status(self):
            if not hasattr(self, '_status'):
                self._status = self.mgr.get_status(self.name)
            return self._status

        @property
        def enabled(self):
            if not hasattr(self, '_enabled'):
                self._enabled = self.mgr.get_enabled(self.name)
            return self._enabled

        def __cmp__(self, b):
            return 1 if self.name > b.name else -1

        def __str__(self):
            return self.name
            
    
    class ServiceControlPlugin(CategoryPlugin):
        abstract = True
        display = False
        disports = False
        
        services = []
        
        def get_ui(self):
            from genesis.plugins.security.firewall import RuleManager, FWMonitor

            mgr = self.app.get_backend(apis.services.IServiceManager)
            rum = RuleManager(self.app)
            self._rules_list = rum.get_by_plugin(self.plugin_id)
            fwm = FWMonitor(self.app)

            res = UI.DT(UI.DTR(
                    UI.DTH(width=20),
                    UI.DTH(UI.Label(text='Service')),
                    UI.DTH(width=20),
                    header=True
                  ), width='100%', noborder=True)

            alert = False

            services = self.plugin_info.services if hasattr(self.plugin_info, 'services') else self.services
            for s in services:
                ctl = UI.HContainer()

                try:
                    st = mgr.get_status(s['binary'])
                except:
                    st = 'failed'
                    alert = True
                try:
                    en = mgr.get_enabled(s['binary'])
                except:
                    en = 'failed'

                if st == 'running':
                    ctl.append(UI.TipIcon(text='Stop', cls='servicecontrol', iconfont='gen-stop', id='stop/' + s['binary']))
                    ctl.append(UI.TipIcon(text='Restart', cls='servicecontrol', iconfont='gen-loop-2', id='restart/' + s['binary']))
                else:
                    ctl.append(UI.TipIcon(text='Start', cls='servicecontrol', iconfont='gen-play-2', id='start/' + s['binary']))
                    alert = True
                if en == 'enabled':
                    ctl.append(UI.TipIcon(text='Disable', cls='servicecontrol', iconfont='gen-minus-circle', id='disable/' + s['binary']))
                else:
                    ctl.append(UI.TipIcon(text='Enable', cls='servicecontrol', iconfont='gen-plus-circle', id='enable/' + s['binary']))
                
                t = UI.DTR(
                        UI.HContainer(
                            UI.IconFont(iconfont='gen-' + ('play-2' if st == 'running' else 'stop')),
                            UI.IconFont(iconfont='gen-' + ('checkmark' if en == 'enabled' else 'close-2')),
                        ),
                        UI.Label(text='%s (%s)'%(s['name'], s['binary'])),
                        ctl
                    )
                res.append(t)

            ptalert = False

            if self._rules_list != []:
                pts = UI.DT(UI.DTR(
                        UI.DTH(width=20),
                        UI.DTH(UI.Label(text='Application')),
                        UI.DTH(UI.Label(text='Ports')),
                        UI.DTH(UI.Label(text='Authorization')),
                        UI.DTH(width=20),
                        header=True
                      ), width='100%', noborder=True)
                for p in self._rules_list:
                    if p[1] == 1:
                        perm, ic, show = 'Local', 'gen-home', [2, 0]
                    elif p[1] == 2:
                        perm, ic, show = 'All', 'gen-earth', [1, 0]
                    else:
                        perm, ic, show = 'None', 'gen-close', [2, 1]
                        ptalert = True
                    pts.append(UI.DTR(
                        UI.IconFont(iconfont=p[0].icon),
                        UI.Label(text=p[0].name),
                        UI.Label(text=', '.join(str(x[1]) for x in p[0].ports)),
                        UI.HContainer(
                            UI.IconFont(iconfont=ic),
                            UI.Label(text=' '),
                            UI.Label(text=perm),
                            ),
                        UI.HContainer(
                            (UI.TipIcon(iconfont='gen-earth',
                                text='Allow All', cls='servicecontrol', 
                                id='2/' + str(self._rules_list.index(p))) if 2 in show else None),
                            (UI.TipIcon(iconfont='gen-home',
                                text='Local Only', cls='servicecontrol',
                                id='1/' + str(self._rules_list.index(p))) if 1 in show else None),
                            (UI.TipIcon(iconfont='gen-close', 
                                text='Deny All', cls='servicecontrol',
                                id='0/' + str(self._rules_list.index(p)),
                                warning='Are you sure you wish to deny all access to %s? '
                                'This will prevent anyone (including you) from connecting to it.' 
                                % p[0].name) if 0 in show else None),
                            ),
                       ))
            
            panel = UI.ServicePluginPanel(
                alert=('True' if alert else 'False'),
                ports=('True' if self._rules_list != [] else 'False'),
                ptalert=('True' if ptalert else 'False'),
            )

            if self.display:
                dlg = UI.DialogBox(
                        UI.ScrollContainer(res, width=300, height=300),
                        id='dlgServices',
                        hidecancel='True'
                    )
                return UI.Container(panel, dlg, self.get_main_ui())
            elif self.disports:
                dlg = UI.DialogBox(
                        UI.ScrollContainer(pts, width=300, height=300),
                        id='dlgPorts',
                        hidecancel='True'
                    )
                return UI.Container(panel, dlg, self.get_main_ui())
            else:
                return UI.Container(panel, self.get_main_ui())

        @event('servicecontrol/click')
        def on_service_control(self, event, params, vars=None):
            from genesis.plugins.security.firewall import RuleManager, FWMonitor
            if params[0] == 'services':
                self.display = True
            if params[0] == 'security':
                self.disports = True
            if params[0] == '2':
                RuleManager(self.app).set(self._rules_list[int(params[1])][0], 2)
                FWMonitor(self.app).regen()
            if params[0] == '1':
                RuleManager(self.app).set(self._rules_list[int(params[1])][0], 1)
                FWMonitor(self.app).regen()
            if params[0] == '0':
                sel = self._rules_list[int(params[1])][0]
                RuleManager(self.app).set(sel, 0)
                FWMonitor(self.app).regen()
            if params[0] == 'restart':
                mgr = self.app.get_backend(apis.services.IServiceManager)
                mgr.restart(params[1])
            if params[0] == 'start':
                mgr = self.app.get_backend(apis.services.IServiceManager)
                mgr.start(params[1])
            if params[0] == 'stop':
                mgr = self.app.get_backend(apis.services.IServiceManager)
                mgr.stop(params[1])
            if params[0] == 'enable':
                mgr = self.app.get_backend(apis.services.IServiceManager)
                mgr.enable(params[1])
            if params[0] == 'disable':
                mgr = self.app.get_backend(apis.services.IServiceManager)
                mgr.disable(params[1])

########NEW FILE########
__FILENAME__ = config
from genesis.api import ModuleConfig
from logs import *


class GeneralConfig(ModuleConfig):
    target = LogsPlugin
    platform = ['any']
    
    labels = {
        'dir': 'Log directory'
    }
    
    dir = '/var/log'
   

########NEW FILE########
__FILENAME__ = groups
from genesis.api import *
from genesis.com import *


class ServiceGroups (Plugin):
    def __init__(self):
        self.read()

    def read(self):
        if not self.app.config.has_section('services'):
            self.app.config.add_section('services')

        r = {}
        names = {}
        content = {}
        for n in self.app.config.options('services'):
            if n.startswith('groupname-'):
                names[n.split('-')[1]] = self.app.config.get('services', n)
            if n.startswith('groupcontent-'):
                content[n.split('-')[1]] = self.app.config.get('services', n)

        for n in names.keys():
            r[names[n]] = content[n].split(' ')

        self.groups = r

    def save(self):
        if self.app.config.has_section('services'):
            self.app.config.remove_section('services')
        self.app.config.add_section('services')

        idx = 0
        for i in self.groups.keys():
            self.app.config.set('services', 'groupname-%i'%idx, i)
            self.app.config.set('services', 'groupcontent-%i'%idx, ' '.join(self.groups[i]))
            idx += 1
            
        self.app.config.save()
########NEW FILE########
__FILENAME__ = logs
import gzip
import bz2
import os

from genesis.ui import *
from genesis.com import implements
from genesis.api import *
from genesis.utils import *


class LogsPlugin(CategoryPlugin):
    text = 'Logs'
    iconfont = 'gen-file-2'
    folder = 'system'

    def on_session_start(self):
        self._log = ''
        self._tree = TreeManager()

    def get_ui(self):
        ui = self.app.inflate('sysmon:logs')
        data = None
        try:
            if self._log != '':
                if self._log.endswith('.gz'):
                    data = self.format_log(gzip.open(self._log).read())
                elif self._log.endswith('.bz2'):
                    data = self.format_log(bz2.BZ2File(self._log, 'r').read())
                else:
                    data = self.format_log(open(self._log).read())
            ui.append('data', data)
        except:
            self.put_message('err', 'Failed to open log file')
        ui.append('tree', self.get_ui_tree())
        return ui

    def get_ui_tree(self):
        root = UI.TreeContainer(text='System Logs', id='/')

        try:
            self.scan_logs(self.app.get_config(self).dir, root, '/')
        except:
            raise ConfigurationError('Can\'t read log tree')

        self._tree.apply(root)
        root['expanded'] = True
        return root

    def scan_logs(self, path, node, nodepath):
        dirs = os.listdir(path)
        dirs.sort()

        for x in dirs:
            try:
                fn = os.path.join(path, x)
                if os.path.isdir(fn):
                    tn = UI.TreeContainer(text=x, id=nodepath+'/'+x)
                    node.append(tn)
                    self.scan_logs(os.path.join(path, x), tn, nodepath+'/'+x)
                else:
                    tn = UI.LinkLabel(text=fix_unicode(x),
                        id='view/'+nodepath+'/'+fix_unicode(x))
                    tn = UI.TreeContainerNode(tn, active=fn==self._log)
                    node.append(tn)
            except:
                pass


    def format_log(self, data):
        d = '<span style="font-family: monospace">'
        d += enquote(data)
        d += '</span>'
        return UI.CustomHTML(html=d)

    @event('linklabel/click')
    def on_click(self, event, params, vars=None):
        if params[0] == 'view':
            self._log = os.path.join(self.app.get_config(self).dir, *params[1:])

    @event('treecontainer/click')
    def on_tclick(self, event, params, vars=None):
        self._tree.node_click('/'.join(params))
        return ''

########NEW FILE########
__FILENAME__ = main
import platform

from genesis.com import Interface
from genesis.ui import UI
from genesis.utils import detect_distro, detect_platform
from genesis.api import *
from genesis import apis
from genesis.plugins.core.updater import UpdateCheck


class Dashboard(CategoryPlugin):
    text = 'System Monitor'
    iconfont = 'gen-chart'
    folder = 'top'

    def on_session_start(self):
        self._adding_widget = None
        self._failed = []

        # start widget manager and show SSL warning if applicable
        self._mgr = apis.dashboard.WidgetManager(self.app)
        if self.app.gconfig.get('genesis', 'ssl') == '0':
            self.put_message('warn', 'Please enable SSL to ensure secure communication with the server')

    def fill(self, side, lst, ui, tgt):
        for x in lst:
            try:
                w = self._mgr.get_widget_object(x)
                if not w:
                    continue
                ui.append(tgt,
                    UI.Widget(
                        w.get_ui(self._mgr.get_widget_config(x), id=str(x)),
                        pos=side,
                        iconfont=w.iconfont,
                        style=w.style,
                        title=w.title,
                        id=str(x),
                    )
                )
            except Exception, e:
                self.put_message('err', 'One or more widgets failed to load. Check the logs for info, or click Clean Up to remove the offending widget(s).')
                self._failed.append(x)
                self.app.log.error('System Monitor Widget failed to load '+w.title+': '+str(e))

    def get_ui(self):
        ui = self.app.inflate('sysmon:main')
        self._mgr = apis.dashboard.WidgetManager(self.app)
        self._mgr.refresh()
        self._failed = []

        self.fill('l', self._mgr.list_left(), ui, 'cleft')
        self.fill('r', self._mgr.list_right(), ui, 'cright')

        if self._failed != []:
            ui.find('ui-dashboard-buttons').append(UI.Button(id='btnCleanUp', text='Clean Up', iconfont='gen-remove'))

        ui.insertText('host', platform.node())
        ui.insertText('distro', detect_distro())
        ui.find('icon').set('src', '/dl/sysmon/distributor-logo-%s.png'%detect_platform(mapping=False))

        if self._adding_widget == True:
            dlg = self.app.inflate('sysmon:add-widget')
            idx = 0
            for prov in sorted(self.app.grab_plugins(apis.dashboard.IWidget)):
                if hasattr(prov, 'hidden'):
                    continue
                dlg.append('list', UI.ListItem(
                    UI.HContainer(
                        UI.IconFont(iconfont=prov.iconfont),
                        UI.Label(text=' '+prov.name),
                    ),
                    id=prov.plugin_id,
                ))
                idx += 1
            ui.append('main', dlg)

        elif self._adding_widget != None:
            ui.append('main', self._mgr.get_by_name(self._adding_widget).get_config_dialog())

        if UpdateCheck.get().get_status()[0] == True:
            self.put_message('info', 'An update for Genesis is available. See the Settings pane for details.')

        return ui

    @event('listitem/click')
    def on_list(self, event, params, vars):
        id = params[0]
        w = self._mgr.get_by_name(id)
        dlg = w.get_config_dialog()
        if dlg is None:
            self._mgr.add_widget(id, None)
            self._adding_widget = None
        else:
            self._adding_widget = id

    @event('sysmon/save')
    def on_save(self, event, params, vars):
        l = params[0]
        r = params[1]
        l = [int(x) for x in l.split(',') if x]
        r = [int(x) for x in r.split(',') if x]
        self._mgr.reorder(l,r)

    @event('button/click')
    @event('linklabel/click')
    def on_event(self, event, params, vars):
        if params[0] == 'btnAddWidget':
            self._adding_widget = True
            try:
                wid = int(params[0])
                params = params[1:]
                self._mgr.get_widget_object(wid).\
                    handle(event, params, self._mgr.get_widget_config(wid), vars)
            except:
                pass
        elif params[0] == 'btnCleanUp':
            for x in self._failed:
                self._mgr.remove_widget(x)

    @event('dialog/submit')
    def on_dialog(self, event, params, vars):
        if params[0] == 'dlgAddWidget':
            self._adding_widget = None
        if params[0] == 'dlgWidgetConfig':
            if vars.getvalue('action', None) == 'OK':
                id = self._adding_widget
                w = self._mgr.get_by_name(id)
                cfg = w.process_config(vars)
                self._mgr.add_widget(id, cfg)
            self._adding_widget = None

########NEW FILE########
__FILENAME__ = meters
import os
import re

from genesis.api import *
from genesis.utils import shell, detect_platform
from genesis import apis


class SysloadMeter (DecimalMeter):
    name = 'System load'
    category = 'System'
    transform = 'float'

    def get_variants(self):
        return ['1', '5', '15']

    def init(self):
        self.load = self.app.get_backend(apis.sysstat.ISysStat).get_load()
        self.text = self.variant + ' min'

    def get_value(self):
        return float(self.load[self.get_variants().index(self.variant)])


class RAMMeter (LinearMeter):
    name = 'RAM'
    category = 'System'
    transform = 'fsize_percent'

    def init(self):
        self.ram = self.app.get_backend(apis.sysstat.ISysStat).get_ram()

    def get_max(self):
        return int(self.ram[1])

    def get_value(self):
        return int(self.ram[0])


class SwapMeter (LinearMeter):
    name = 'Swap'
    category = 'System'
    transform = 'fsize_percent'

    def init(self):
        self.swap = self.app.get_backend(apis.sysstat.ISysStat).get_swap()

    def get_max(self):
        return int(self.swap[1])

    def get_value(self):
        return int(self.swap[0])


class DiskUsageMeter(LinearMeter):
    name = 'Disk usage'
    category = 'System'
    transform = 'percent'

    _platform = detect_platform()
    _partstatformat = re.compile('(/dev/)?(?P<dev>\w+)\s+\d+\s+\d+\s+\d+\s+' +
                                       '(?P<usage>\d+)%\s+(?P<mountpoint>\S+)$')
    if 'arkos' in _platform or 'arch' in _platform:
        _totalformat = re.compile('(?P<dev>total)\s+\d+\s+\d+\s+\d+\s+(?P<usage>\d+)%+\s+\-$')
    else:
        _totalformat = re.compile('(?P<dev>total)\s+\d+\s+\d+\s+\d+\s+(?P<usage>\d+)%$')

    def init(self):
        if self.variant == 'total':
            self.text = 'total'
        else:
            mountpoints = self.get_mountpoints()
            self.text = '%s (%s)' % (self.variant, ', '.join(mountpoints))

    def _get_stats(self, predicate = (lambda m: True)):
        if hasattr(self, 'variant') and self.variant == 'total':
            matcher = DiskUsageMeter._totalformat
        else:
            matcher = DiskUsageMeter._partstatformat

        stats = shell('df --total')
        matches = []
        for stat in stats.splitlines():
            match = matcher.match(stat)
            if match and predicate(match):
                matches.append(match)
        return matches

    def _get_stats_for_this_device(self):
        return self._get_stats(lambda m: m.group('dev').endswith(self.variant))

    def get_variants(self):
        if 'arkos' in self._platform or 'arch' in self._platform:
            return sorted(set([ m.group('dev') for m in self._get_stats()]))
        else:
            return sorted(set([ m.group('dev') for m in self._get_stats()])) + ['total']

    def get_mountpoints(self):
        devmatches = self._get_stats_for_this_device()
        return sorted([ m.group('mountpoint') for m in devmatches])

    def get_value(self):
        devmatches = self._get_stats_for_this_device()
        return int(devmatches[0].group('usage'))

    def get_min(self):
        return 0

    def get_max(self):
        return 100


class CpuMeter(LinearMeter):
    name = 'CPU usage'
    category = 'System'
    transform = 'percent'
    
    def get_usage(self):
         u = shell('ps h -eo pcpu').split()
         b=0.0
         for a in u:  
            b += float(a)
         return b
    
    def get_value(self):
        return self.get_usage()
    
    def get_min(self):
        return 0
    
    def get_max(self):
        return 100


class ServiceMeter (BinaryMeter):
    name = 'Service'
    category = 'Software'
    transform = 'running'

    def get_variants(self):
        return [x.name for x in self.app.get_backend(apis.services.IServiceManager).list_all()]

    def init(self):
        self.mgr = self.app.get_backend(apis.services.IServiceManager)
        self.text = self.variant

    def get_value(self):
        return self.mgr.get_status(self.variant) == 'running'
        
########NEW FILE########
__FILENAME__ = services
from genesis.com import implements
from genesis.api import *
from genesis.ui import *
from genesis import apis

from groups import *


class ServicesPlugin(CategoryPlugin):
    text = 'Services'
    iconfont = 'gen-atom'
    folder = 'system'

    def on_init(self):
        self.svc_mgr = self.app.get_backend(apis.services.IServiceManager)
        self.groupmgr = ServiceGroups(self.app)
        
    def on_session_start(self):
        self._editing = None

    def get_ui(self):
        ui = self.app.inflate('sysmon:services')
        ts = ui.find('list')

        lst = sorted(self.svc_mgr.list_all(), key=lambda x: x.status)
        for svc in lst:
            row = self.get_row(svc)
            ts.append(row)

        for g in sorted(self.groupmgr.groups.keys()):
            gui = self.app.inflate('sysmon:group')
            gui.find('edit').set('id', 'edit/'+g)
            gui.find('delete').set('id', 'delete/'+g)
            gui.find('name').set('text', g)
            show_run = False
            show_stop = False
            for s in self.groupmgr.groups[g]:
                try:
                    svc = filter(lambda x:x.name==s, lst)[0]
                    if svc.status == 'running':
                        show_stop = True
                    else:
                        show_run = True
                    gui.append('list', self.get_row(svc))
                except:
                    pass
            if show_stop:
                gui.appendAll('btns',
                    UI.TipIcon(text='Stop all', iconfont='gen-stop', id='gstop/' + g),
                    UI.TipIcon(text='Restart all', iconfont='gen-loop-2', id='grestart/' + g)
                  )
            if show_run:
                gui.append('btns',
                    UI.TipIcon(text='Start all', iconfont='gen-play-2', id='gstart/' + g)
                )
        
            ui.append('groups', gui)

        if self._editing is not None:
            has = self._editing in self.groupmgr.groups.keys()
            eui = self.app.inflate('sysmon:edit')
            eui.find('name').set('value', self._editing)
            for svc in self.svc_mgr.list_all():
                eui.append('services', UI.Checkbox(
                    name=svc.name,
                    text=svc.name,
                    checked=has and (svc.name in self.groupmgr.groups[self._editing]),
                ))
            ui.append('main', eui)

        return ui

    def get_row(self, svc):
        ctl = UI.HContainer()
        if svc.status == 'running':
            ctl.append(UI.TipIcon(text='Stop', iconfont='gen-stop', id='stop/' + svc.name))
            ctl.append(UI.TipIcon(text='Restart', iconfont='gen-loop-2', id='restart/' + svc.name))
        else:
            ctl.append(UI.TipIcon(text='Start', iconfont='gen-play-2', id='start/' + svc.name))
        if svc.enabled == 'enabled':
            ctl.append(UI.TipIcon(text='Disable', iconfont='gen-minus-circle', id='disable/' + svc.name))
        else:
            ctl.append(UI.TipIcon(text='Enable', iconfont='gen-plus-circle', id='enable/' + svc.name))

        fn = 'gen-' + ('play-2' if svc.status == 'running' else 'stop')
        row = UI.DTR(
                UI.IconFont(iconfont=fn),
                UI.Label(text=svc.name),
                ctl
              )
        return row
                      
    @event('button/click')
    def on_click(self, event, params, vars=None):
        if params[0] == 'start':
            self.svc_mgr.start(params[1])
        if params[0] == 'restart':
            self.svc_mgr.restart(params[1])
        if params[0] == 'stop':
            self.svc_mgr.stop(params[1])
        if params[0] == 'enable':
            self.svc_mgr.enable(params[1])
        if params[0] == 'disable':
            self.svc_mgr.disable(params[1])
        if params[0] == 'gstart':
            for s in self.groupmgr.groups[params[1]]:
                self.svc_mgr.start(s)
        if params[0] == 'grestart':
            for s in self.groupmgr.groups[params[1]]:
                self.svc_mgr.restart(s)
        if params[0] == 'gstop':
            for s in self.groupmgr.groups[params[1]]:
                self.svc_mgr.stop(s)
        if params[0] == 'addGroup':
            self._editing = ''
        if params[0] == 'delete':
            del self.groupmgr.groups[params[1]]
            self.groupmgr.save()
        if params[0] == 'edit':
            self._editing = params[1]

    @event('dialog/submit')
    def on_submit(self, event, params, vars=None):
        if params[0] == 'dlgEdit':
            if vars.getvalue('action') == 'OK':
                svcs = []
                for svc in self.svc_mgr.list_all():
                    if vars.getvalue(svc.name) == '1':
                        svcs.append(svc.name)
                if self._editing != '':
                    del self.groupmgr.groups[self._editing]                        
                self.groupmgr.groups[vars.getvalue('name')] = sorted(svcs)
                self.groupmgr.save()
            self._editing = None


########NEW FILE########
__FILENAME__ = ss_bsd
from genesis import apis
from genesis.utils import shell
from genesis.com import *


class BSDSysStat(Plugin):
    implements(apis.sysstat.ISysStat)
    platform = ['freebsd']

    def get_load(self):
        return shell('sysctl vm.loadavg').split()[2:5]

    def get_ram(self):
        s = shell("top -b | grep Mem | sed 's/[^0-9]/ /g' | awk '{print $1+$2+$3+$4+$5+$6, $1+$2, $3+$4+$5+$6}'").split()
        t = int(s[0]) * 1024*1024
        u = int(s[1]) * 1024*1024
        f = int(s[2]) * 1024*1024
        return (u, t)

    def get_swap(self):
        s = shell('top -b | grep Swap | sed "s/[^0-9]/ /g"').split()
        return (int(s[1]) * 1024*1024, int(s[0]) * 1024*1024)


########NEW FILE########
__FILENAME__ = ss_linux
# -*- coding: UTF-8 -*-

import re
import os

from genesis import apis
from genesis.utils import shell, detect_architecture
from genesis.com import *


class LinuxSysStat(Plugin):
    implements(apis.sysstat.ISysStat)
    platform = ['debian', 'arch', 'arkos', 'centos', 'fedora', 'gentoo', 'mandriva']

    def get_load(self):
        return open('/proc/loadavg', 'r').read().split()[0:3]

    def get_temp(self):
        if detect_architecture()[1] == 'Raspberry Pi':
            return '%3.1f°C'%(float(shell('cat /sys/class/thermal/thermal_zone0/temp').split('\n')[0])/1000)
        else:
            if os.path.exists('/sys/class/hwmon/hwmon1/temp1_input'):
                return '%3.1f°C'%(float(shell('cat /sys/class/hwmon/hwmon1/temp1_input'))/1000)
        return ''

    def get_ram(self):
        s = shell('free -b | grep Mem').split()[1:]
        t = int(s[0])
        u = int(s[1])
        b = int(s[4])
        c = int(s[5])
        u -= c + b;
        return (u, t)

    def get_swap(self):
        s = shell('free -b | grep Swap').split()[1:]
        return (int(s[1]), int(s[0]))

    def get_uptime(self):
        minute = 60
        hour = minute * 60
        day = hour * 24

        d = h = m = 0

        try:
            s = int(open('/proc/uptime').read().split('.')[0])

            d = s / day
            s -= d * day
            h = s / hour
            s -= h * hour
            m = s / minute
            s -= m * minute
        except IOError:
            # Try use 'uptime' command
            up = os.popen('uptime').read()
            if up:
                uptime = re.search('up\s+(.*?),\s+[0-9]+ user',up).group(1)
                return uptime

        uptime = ""
        if d > 1:
            uptime = "%d days, "%d
        elif d == 1:
            uptime = "1 day, "

        return uptime + "%d:%02d:%02d"%(h,m,s)

########NEW FILE########
__FILENAME__ = s_arch
import glob
import os
import re

from genesis.com import *
from genesis.utils import *
from genesis import apis


class ArchServiceManager(Plugin):
    implements(apis.services.IServiceManager)
    platform = ['arch', 'arkos']

    def __init__(self):
        self.use_systemd = os.path.realpath("/proc/1/exe").endswith("/systemd")

    def list_all(self):
        services = []
        enlist = []

        if self.use_systemd:
            for x in glob.iglob('/etc/systemd/system/*.wants/*.service'):
                enlist.append(x.rsplit('/')[5])
            for unit in shell("systemctl --no-ask-password --full -t service --all").splitlines():
                data = unit.split()
                if data == [] or not data[0].endswith('.service'):
                    continue
                status = 'stopped' if 'inactive' in data[2] else 'running'
                enabled = 'enabled' if data[0] in enlist else 'disabled'
                services.append((re.sub('\.service$', '', data[0]), status, enabled))
        else:
            services = os.listdir('/etc/rc.d')

        r = []
        for s in services:
            svc = apis.services.Service()
            svc.name = s[0]
            svc._status = s[1]
            svc._enabled = s[2]
            svc.mgr = self
            r.append(svc)

        return sorted(r, key=lambda s: s.name)

    def get_status(self, name):
        if self.use_systemd:
            status = shell_status("systemctl --no-ask-password is-active {}.service".format(name))
            if status != 0:
                return 'stopped'
            else:
                return 'running'
        else:
            s = shell('/etc/rc.d/{} status'.format(name))
            return 'running' if 'running' in s else 'stopped'

    def get_enabled(self, name):
        if self.use_systemd:
            status = shell_status("systemctl --no-ask-password is-enabled {}.service".format(name))
            if status != 0:
                return 'disabled'
            else:
                return 'enabled'
        else:
            return 'unknown'

    def start(self, name):
        if self.use_systemd:
            shell("systemctl --no-ask-password start {}.service".format(name))
        else:
            shell('/etc/rc.d/{} start'.format(name))

    def stop(self, name):
        if self.use_systemd:
            shell("systemctl --no-ask-password stop {}.service".format(name))
        else:
            shell('/etc/rc.d/{} stop'.format(name))

    def restart(self, name):
        if self.use_systemd:
            shell("systemctl --no-ask-password reload-or-restart {}.service".format(name))
        else:
            shell('/etc/rc.d/{} restart'.format(name))

    def real_restart(self, name):
        if self.use_systemd:
            shell("systemctl --no-ask-password restart {}.service".format(name))
        else:
            shell('/etc/rc.d/{} restart'.format(name))

    def enable(self, name):
        if self.use_systemd:
            shell("systemctl --no-ask-password enable {}.service".format(name))
        else:
            pass

    def disable(self, name):
        if self.use_systemd:
            shell("systemctl --no-ask-password disable {}.service".format(name))
        else:
            pass

########NEW FILE########
__FILENAME__ = widget
from genesis.ui import *
from genesis import apis
from genesis.com import implements, Plugin
from genesis.api import *
from genesis.utils import *
from meters import DiskUsageMeter, CpuMeter


class LoadWidget(Plugin):
    implements(apis.dashboard.IWidget)
    title = 'System load'
    iconfont = 'gen-meter'
    name = 'System load'
    style = 'linear'

    def get_ui(self, cfg, id=None):
        stat = self.app.get_backend(apis.sysstat.ISysStat)
        ui = self.app.inflate('sysmon:load')
        load = stat.get_load()
        ui.find('1m').set('text', load[0])
        ui.find('5m').set('text', load[1])
        ui.find('15m').set('text', load[2])
        return ui

    def handle(self, event, params, cfg, vars=None):
        pass

    def get_config_dialog(self):
        return None

    def process_config(self, event, params, vars):
        pass


class RamWidget(Plugin):
    implements(apis.dashboard.IWidget)
    title = 'RAM'
    iconfont = 'gen-database'
    name = 'Memory'
    style = 'normal'

    def get_ui(self, cfg, id=None):
        stat = self.app.get_backend(apis.sysstat.ISysStat)
        ru, rt = stat.get_ram()
        return UI.HContainer(
            UI.ProgressBar(value=ru, max=rt, width=220),
            UI.Label(text=str_fsize(ru)),
        )

    def handle(self, event, params, cfg, vars=None):
        pass

    def get_config_dialog(self):
        return None

    def process_config(self, vars):
        pass


class SwapWidget(Plugin):
    implements(apis.dashboard.IWidget)
    title = 'Swap'
    iconfont = 'gen-storage'
    name = 'Swap'
    style = 'normal'

    def get_ui(self, cfg, id=None):
        stat = self.app.get_backend(apis.sysstat.ISysStat)
        su, st = stat.get_swap()
        return UI.HContainer(
            UI.ProgressBar(value=su, max=int(st)+1, width=220),
            UI.Label(text=str_fsize(su)),
        )

    def handle(self, event, params, cfg, vars=None):
        pass

    def get_config_dialog(self):
        return None

    def process_config(self, vars):
        pass


class TempWidget(Plugin):
    implements(apis.dashboard.IWidget)
    title = 'Temperature'
    iconfont = 'gen-sun'
    name = 'Temperature'
    style = 'linear'
    
    def get_ui(self, cfg, id=None):
        stat = self.app.get_backend(apis.sysstat.ISysStat)
        return UI.Label(text=stat.get_temp())
        
    def handle(self, event, params, cfg, vars=None):
        pass
    
    def get_config_dialog(self):
        return None
        
    def process_config(self, vars):
        pass


class UptimeWidget(Plugin):
    implements(apis.dashboard.IWidget)
    title = 'Uptime'
    iconfont = 'gen-clock'
    name = 'Uptime'
    style = 'linear'
    
    def get_ui(self, cfg, id=None):
        stat = self.app.get_backend(apis.sysstat.ISysStat)
        return UI.Label(text=stat.get_uptime())
        
    def handle(self, event, params, cfg, vars=None):
        pass
    
    def get_config_dialog(self):
        return None
        
    def process_config(self, vars):
        pass


class DiskUsageWidget(Plugin):
    implements(apis.dashboard.IWidget)
    title = 'Disk Usage'
    iconfont = 'gen-storage'
    name = 'Disk Usage'
    style = 'normal'

    def get_ui(self, cfg, id=None):
        self.title = '%s Disk Usage' % cfg
        if cfg == None:
            cfg = "total"
        m = DiskUsageMeter(self.app).prepare(cfg)
        return UI.HContainer(
            UI.ProgressBar(value=m.get_value(), max=m.get_max(), width=220),
            UI.Label(text=str('%d%%' % m.get_value())),
        )

    def handle(self, event, params, cfg, vars=None):
        pass

    def get_config_dialog(self):
        usageMeter = DiskUsageMeter(self.app)
        dialog = self.app.inflate('sysmon:hddstat-config')
        for option in usageMeter.get_variants():
            dialog.append('list', UI.SelectOption(
                value=option,
                text=option,
            ))
        return dialog

    def process_config(self, vars):
        return vars.getvalue('disk', None)


class CpuWidget(Plugin):
    implements(apis.dashboard.IWidget)
    title = 'CPU Usage'
    iconfont = 'gen-busy'
    name = 'CPU Usage'
    style = 'normal'

    def get_ui(self, cfg, id=None):
        m = CpuMeter(self.app).prepare(cfg)
        return UI.HContainer(
            UI.ProgressBar(value=m.get_value(), max=m.get_max(), width=220),
            UI.Label(text=str(m.get_value())+'%'),
        )

    def handle(self, event, params, cfg, vars=None):
        pass

    def get_config_dialog(self):
        return None
    
    def process_config(self, vars):
        pass


class ServiceWidget(Plugin):
    implements(apis.dashboard.IWidget)
    iconfont = 'gen-atom'
    name = 'Service control'
    title = None
    style = 'linear'

    def __init__(self):
        self.iface = None

    def get_ui(self, cfg, id=None):
        mgr = self.app.get_backend(apis.services.IServiceManager)
        running = mgr.get_status(cfg) == 'running'
        self.title = cfg
        self.iconfont = 'gen-' + ('play-2' if running else 'stop')

        ui = self.app.inflate('sysmon:services-widget')
        if running:
            ui.remove('start')
            ui.find('stop').set('id', id+'/stop')
            ui.find('restart').set('id', id+'/restart')
        else:
            ui.remove('stop')
            ui.remove('restart')
            ui.find('start').set('id', id+'/start')
        return ui

    def handle(self, event, params, cfg, vars=None):
        mgr = self.app.get_backend(apis.services.IServiceManager)
        if params[0] == 'start':
            mgr.start(cfg)
        if params[0] == 'stop':
            mgr.stop(cfg)
        if params[0] == 'restart':
            mgr.restart(cfg)

    def get_config_dialog(self):
        mgr = self.app.get_backend(apis.services.IServiceManager)
        dlg = self.app.inflate('sysmon:services-config')
        for s in sorted(mgr.list_all()):
            dlg.append('list', UI.SelectOption(
                value=s.name,
                text=s.name,
            ))
        return dlg

    def process_config(self, vars):
        return vars.getvalue('svc', None)

########NEW FILE########
__FILENAME__ = backend
from subprocess import *

from genesis.api import *
from genesis.com import *
from genesis.utils import *


class User:
    login = ''
    uid = 0
    gid = 0
    home = ''
    shell = ''
    info = ''
    groups = []


class Group:
    name = ''
    gid = 0
    users = []


class UsersBackend(Plugin):
    iconfont = 'gen-users'

    def __init__(self):
        self.cfg = self.app.get_config(self)

    def get_all_users(self):
        r = []
        for s in open('/etc/passwd', 'r').read().split('\n'):
            try:
                s = s.split(':')
                u = User()
                u.login = s[0]
                u.uid = int(s[2])
                u.gid = int(s[3])
                u.info = s[4]
                u.home = s[5]
                u.shell = s[6]
                r.append(u)
            except:
                pass

        sf = lambda x: -1 if x.uid==0 else (x.uid+1000 if x.uid<1000 else x.uid-1000)
        return sorted(r, key=sf)

    def get_all_groups(self):
        r = []
        for s in open('/etc/group', 'r').read().split('\n'):
            try:
                s = s.split(':')
                g = Group()
                g.name = s[0]
                g.gid = s[2]
                g.users = s[3].split(',')
                r.append(g)
            except:
                pass

        return r

    def map_groups(self, users, groups):
        for u in users:
            u.groups = []
            for g in groups:
                if u.login in g.users:
                    u.groups.append(g.name)

    def get_user(self, name, users):
        return filter(lambda x:x.login == name, users)[0]

    def get_group(self, name, groups):
        return filter(lambda x:x.name == name, groups)[0]

    def add_user(self, v):
        shell(self.cfg.cmd_add.format(v))

    def add_sys_user(self, v):
        shell(self.cfg.cmd_add_sys.format(v))

    def add_sys_with_home(self, v):
        shell(self.cfg.cmd_add_sys_with_home.format(v))

    def add_group(self, v):
        shell(self.cfg.cmd_add_group.format(v))

    def del_user(self, v):
        shell(self.cfg.cmd_del.format(v))

    def del_user_with_home(self, v):
        shell(self.cfg.cmd_del_with_home.format(v))

    def del_group(self, v):
        shell(self.cfg.cmd_del_group.format(v))

    def add_to_group(self, u, v):
        shell(self.cfg.cmd_add_to_group.format(u,v))

    def change_user_param(self, u, p, l):
        shell(getattr(self.cfg, 'cmd_set_user_'+p).format(l,u))

    def change_user_password(self, u, l):
        shell_stdin('passwd ' + u, '%s\n%s\n' % (l,l))

    def change_group_param(self, u, p, l):
        shell(getattr(self.cfg, 'cmd_set_group_'+p).format(l,u))


class LinuxConfig(ModuleConfig):
    target = UsersBackend
    platform = ['debian', 'arch', 'arkos', 'fedora', 'centos', 'gentoo', 'mandriva']

    cmd_add = 'useradd -m {0}'
    cmd_add_sys = 'useradd -r {0}'
    cmd_add_sys_with_home = 'useradd -rm {0}'
    cmd_del = 'userdel {0}'
    cmd_del_with_home = 'userdel -r {0}'
    cmd_add_group = 'groupadd {0}'
    cmd_del_group = 'groupdel {0}'
    cmd_set_user_login = 'usermod -l {0} {1}'
    cmd_set_user_uid = 'usermod -u {0} {1}'
    cmd_set_user_gid = 'usermod -g {0} {1}'
    cmd_set_user_shell = 'usermod -s {0} {1}'
    cmd_set_user_home = 'usermod -d {0} {1}'
    cmd_set_group_gname = 'groupmod -n {0} {1}'
    cmd_set_group_ggid = 'groupmod -g {0} {1}'
    cmd_add_to_group = 'usermod -a -G {1} {0}'


class BSDConfig(ModuleConfig):
    target = UsersBackend
    platform = ['freebsd']

    cmd_add = 'pw useradd {0}'
    cmd_del = 'pw userdel {0}'
    cmd_del_with_home = 'pw userdel -r {0}'
    cmd_add_group = 'pw groupadd {0}'
    cmd_del_group = 'pw groupdel {0}'
    cmd_set_user_login = 'pw usermod {1} -l {0}'
    cmd_set_user_uid = 'pw usermod {1} -u {0}'
    cmd_set_user_gid = 'pw usermod {1} -g {0}'
    cmd_set_user_shell = 'pw usermod {1} -s {0}'
    cmd_set_user_home = 'pw usermod {1} -h {0}'
    cmd_set_group_gname = 'pw groupmod {1} -n {0}'
    cmd_set_group_ggid = 'pw groupmod {1} -g {0}'
    cmd_add_to_group = 'pw groupmod {1} -m {0}'
    cmd_remove_from_group = 'pw groupmod {1} -d {0}'

########NEW FILE########
__FILENAME__ = main
import re

from genesis.ui import *
from genesis.com import implements
from genesis.api import *
from genesis.utils import *

from backend import *


class UsersPlugin(CategoryPlugin):
    text = 'Users'
    iconfont = 'gen-users'
    folder = 'system'

    params = {
            'login': 'Login',
            'password': 'Password',
            'name': 'Name',
            'uid': 'UID',
            'home': 'Home directory',
            'adduser': 'New user login',
        }


    def on_init(self):
        self.backend = UsersBackend(self.app)
        self.users = self.backend.get_all_users()

    def reload_data(self):
        self.users = self.backend.get_all_users()

    def get_config(self):
        return self.app.get_config(self.backend)

    def on_session_start(self):
        self._tab = 0
        self._selected_user = ''
        self._editing = ''

    def get_ui(self):
        self.reload_data()
        ui = self.app.inflate('users:main')

        if self._editing == 'deluser':
            u = self.backend.get_user(self._selected_user, self.users)
            ui.find('dlgConfirmDelete').set('text', 
                'Do you want to delete user data (stored at %s) for %s?' % (u.home, u.login))
            ui.remove('dlgEdit')
        elif self._editing != '' and self._editing in self.params:
            ui.find('dlgEdit').set('text', self.params[self._editing])
            ui.remove('dlgConfirmDelete')
        else:
            ui.remove('dlgEdit')
            ui.remove('dlgConfirmDelete')

        # Users
        t = ui.find('userlist')

        for u in self.users:
            if u.uid == 0 or u.uid >= 1000:
                t.append(UI.DTR(
                        UI.IconFont(iconfont='gen-user'),
                        UI.Label(text=u.login, bold=True),
                        UI.Label(text=u.uid, bold=True),
                        UI.Label(text=u.home),
                        UI.TipIcon(iconfont='gen-pencil-2', id='edit/'+u.login, text='Edit'),
                    ))

        if self._selected_user != '' and self._editing != 'deluser':
            u = self.backend.get_user(self._selected_user, self.users)
            ui.find('login').set('value', u.login)
            ui.find('home').set('text', u.home)
        else:
            ui.remove('dlgEditUser')

        return ui

    @event('button/click')
    def on_click(self, event, params, vars=None):
        if params[0] == 'edit':
            self._tab = 0
            self._selected_user = params[1]
        if params[0] == 'gedit':
            self._tab = 1
            self._selected_group = params[1]
        if params[0].startswith('ch'):
            self._tab = 0
            self._editing = params[0][2:]
        if params[0] == 'adduser':
            self._tab = 0
            self._editing = 'adduser'
        if params[0] == 'deluser':
            self._editing = 'deluser'

    @event('dialog/submit')
    @event('form/submit')
    def on_submit(self, event, params, vars=None):
        if params[0] == 'dlgEdit':
            v = vars.getvalue('value', '')
            if vars.getvalue('action', '') == 'OK':
                if self._editing == 'adduser':
                    if re.search('[A-Z]|\.|:|[ ]|-$', v):
                        self.put_message('err', 'Username must not contain capital letters, dots, colons, spaces, or end with a hyphen')
                        self._editing = ''
                        return
                    self.reload_data()
                    for u in self.users:
                        if u.login == v:
                            self.put_message('err', 'Duplicate name')
                            self._editing = ''
                            return
                    self.app.gconfig.set('users', v, '')
                    self.app.gconfig.save()
                    self.backend.add_user(v)
                    self._selected_user = v
            self._editing = ''
        if params[0] == 'dlgEditUser':
            if vars.getvalue('passwd', '') != '':
                v = vars.getvalue('passwd')
                if v != vars.getvalue('passwdb',''):
                    self.put_message('err', 'Passwords must match')
                    self._selected_user = ''
                else:
                    self.backend.change_user_password(self._selected_user, v)
                    self.app.gconfig.set('users', self._selected_user, hashpw(v))
            if vars.getvalue('login', '') != '' and vars.getvalue('login', '') != self._selected_user:
                v = vars.getvalue('login')
                for u in self.users:
                    if u.login == v:
                        self.put_message('err', 'Duplicate name')
                        self._selected_user = ''
                        return
                if re.search('[A-Z]|\.|:|[ ]|-$', v):
                    self.put_message('err', 'Username must not contain capital letters, dots, colons, spaces, or end with a hyphen')
                    self._selected_user = ''
                else:
                    self.backend.change_user_param(self._selected_user, 'login', v)
                    pw = self.app.gconfig.get('users', self._selected_user, '')
                    self.app.gconfig.remove_option('users', self._selected_user)
                    self.app.gconfig.set('users', v, pw)
                    self._selected_user = v
                    self.app.gconfig.save()
                    self._editing = ''
            self._selected_user = ''
        if params[0] == 'dlgConfirmDelete':
            self._tab = 0
            answer = vars.getvalue('action', '')
            if answer == 'Confirm':
                self.backend.del_user_with_home(self._selected_user)
            elif answer == 'Reject':
                self.backend.del_user(self._selected_user)
            if answer != 'Cancel':
                try:
                    self.app.gconfig.remove_option('users', self._selected_user)
                    self.app.gconfig.save()
                except:
                    pass
            self._selected_user = ''
            self._editing = ''

########NEW FILE########
__FILENAME__ = api
from genesis.com import *
from genesis import apis

import ConfigParser
import glob
import nginx
import os
import re


class Webapp(object):
    name = ''
    stype = ''
    ssl = False
    ssl_able = True
    addr = ''
    port = ''
    path = ''
    php = False
    sclass = None
    enabled = False


class Webapps(apis.API):
    def __init__(self, app):
        self.app = app

    class IWebapp(Interface):
        def pre_install(self, name, vars):
            pass

        def post_install(self, name, path, vars):
            pass

        def pre_remove(self, name, path):
            pass

        def post_remove(self, name):
            pass

        def ssl_enable(self, path, cfile, kfile):
            pass

        def ssl_disable(self, path):
            pass

    def get_apptypes(self):
        applist = []
        for plugin in self.app.grab_plugins(apis.webapps.IWebapp):
            applist.append(plugin)
        return applist

    def get_sites(self):
        applist = []
        if not os.path.exists('/etc/nginx/sites-available'):
            os.makedirs('/etc/nginx/sites-available')
        if not os.path.exists('/etc/nginx/sites-enabled'):
            os.makedirs('/etc/nginx/sites-enabled')

        for site in os.listdir('/etc/nginx/sites-available'):
            w = Webapp()
            # Set default values and regexs to use
            w.name = site
            w.addr = False
            w.port = '80'
            w.stype = 'Unknown'
            w.path = os.path.join('/etc/nginx/sites-available', site)
            rtype = re.compile('GENESIS ((?:[a-z][a-z]+))', flags=re.IGNORECASE)
            rport = re.compile('(\\d+)\s*(.*)')

            # Get actual values
            try:
                s = None
                c = nginx.loadf(w.path)
                w.stype = re.match(rtype, c.filter('Comment')[0].comment).group(1)
                # Get the right serverblock - SSL if it's here
                for x in c.servers:
                    if 'ssl' in x.filter('Key', 'listen')[0].value:
                        s = x
                        break
                if not s:
                    s = c.servers[0]
                w.port, w.ssl = re.match(rport, s.filter('Key', 'listen')[0].value).group(1, 2)
                w.addr = s.filter('Key', 'server_name')[0].value
                w.path = s.filter('Key', 'root')[0].value
                w.php = True if 'php' in s.filter('Key', 'index')[0].value else False
            except IndexError:
                pass

            w.enabled = True if os.path.exists(os.path.join('/etc/nginx/sites-enabled', site)) else False

            w.sclass = self.get_interface(w.stype)
            w.sinfo = self.get_info(w.stype)
            w.dbengine = w.sinfo.dbengine if hasattr(w.sinfo, 'dbengine') else None
            w.ssl_able = w.sinfo.ssl if hasattr(w.sinfo, 'ssl') else False

            applist.append(w)
        return applist

    def get_info(self, name):
        cs = filter(lambda x: x.__class__.__name__ == name,
            self.app.grab_plugins(apis.webapps.IWebapp))
        return cs[0].plugin_info if len(cs) else None

    def get_interface(self, name):
        cs = filter(lambda x: x.__class__.__name__ == name,
            self.app.grab_plugins(apis.webapps.IWebapp))
        return cs[0] if len(cs) else None

    def cert_remove_notify(self, name, stype):
        # Called by webapp when removed.
        # Removes the associated entry from gcinfo tracker file
        # Placed here for now to avoid awkward circular import
        try:
            cfg = ConfigParser.ConfigParser()
            for x in glob.glob('/etc/ssl/certs/genesis/*.gcinfo'):
                cfg.read(x)
                alist = []
                write = False
                for i in cfg.get('cert', 'assign').split('\n'):
                    if i != (name+' ('+stype+')'):
                        alist.append(i)
                    else:
                        write = True
                if write == True:
                    cfg.set('cert', 'assign', '\n'.join(alist))
                    cfg.write(open(x, 'w'))
        except:
            pass

########NEW FILE########
__FILENAME__ = backend
from genesis.com import Plugin, Interface, implements
from genesis.utils import shell, shell_cs, download
from genesis import apis
from api import Webapp

import nginx
import os
import re
import shutil


class InstallError(Exception):
	def __init__(self, cause):
		self.cause = cause

	def __str__(self):
		return 'Installation failed: %s' % self.cause

class PartialError(Exception):
	def __init__(self, cause):
		self.cause = cause

	def __str__(self):
		return 'Installation successful, but %s' % self.cause

class ReloadError(Exception):
	def __init__(self, cause):
		self.cause = cause

	def __str__(self):
		return 'Installation successful, but %s restart failed. Check your configs' % self.cause


class WebappControl(Plugin):
	def add(self, cat, name, wa, vars, enable=True):
		specialmsg = ''
		webapp = apis.webapps(self.app).get_interface(wa.wa_plugin)

		if not wa.dpath:
			ending = ''
		elif wa.dpath.endswith('.tar.gz'):
			ending = '.tar.gz'
		elif wa.dpath.endswith('.tar.bz2'):
			ending = '.tar.bz2'
		elif wa.dpath.endswith('.zip'):
			ending = '.zip'
		elif wa.dpath.endswith('.git'):
			ending = '.git'
		else:
			raise InstallError('Only GIT repos, gzip, bzip, and zip packages supported for now')

		# Run webapp preconfig, if any
		try:
			cat.put_statusmsg('Running pre-install configuration...')
			webapp.pre_install(name, vars)
		except Exception, e:
			raise InstallError('Webapp config - '+str(e))

		# Make sure the target directory exists, but is empty
		# Testing for sites with the same name should have happened by now
		target_path = os.path.join('/srv/http/webapps', name)
		pkg_path = '/tmp/'+name+ending
		if os.path.isdir(target_path):
			shutil.rmtree(target_path)
		os.makedirs(target_path)

		# Download and extract the source package
		if wa.dpath and ending == '.git':
			status = shell_cs('git clone %s %s'%(wa.dpath,target_path), stderr=True)
			if status[0] >= 1:
				raise InstallError(status[1])
		elif wa.dpath:
			try:
				cat.put_statusmsg('Downloading webapp package...')
				download(wa.dpath, file=pkg_path, crit=True)
			except Exception, e:
				raise InstallError('Couldn\'t download - %s' % str(e))

			if ending in ['.tar.gz', '.tar.bz2']:
				extract_cmd = 'tar '
				extract_cmd += 'xzf' if ending is '.tar.gz' else 'xjf'
				extract_cmd += ' /tmp/%s -C %s --strip 1' % (name+ending, target_path)
			else:
				extract_cmd = 'unzip -d %s /tmp/%s' % (target_path, name+ending)

			status = shell_cs(extract_cmd, stderr=True)
			if status[0] >= 1:
				raise InstallError(status[1])
			os.remove(pkg_path)

		php = vars.getvalue('php', '')
		addtoblock = vars.getvalue('addtoblock', '')

		if addtoblock:
			addtoblock = nginx.loads(addtoblock, False)
		else:
			addtoblock = []
		if wa.wa_plugin == 'Website' and php == '1' and addtoblock:
			addtoblock.extend(x for x in webapp.phpblock)
		elif wa.wa_plugin == 'Website' and php == '1':
			addtoblock = webapp.phpblock

		# Setup the webapp and create an nginx serverblock
		try:
			w = Webapp()
			w.name = name
			w.stype = wa.wa_plugin
			w.path = target_path
			w.addr = vars.getvalue('addr', 'localhost')
			w.port = vars.getvalue('port', '80')
			w.php = True if wa.php is True or php is '1' else False
			self.nginx_add(site=w, 
				add=addtoblock if addtoblock else webapp.addtoblock, 
				)
		except Exception, e:
			raise PartialError('nginx serverblock couldn\'t be written - '+str(e))

		try:
			cat.put_statusmsg('Running post-install configuration...')
			specialmsg = webapp.post_install(name, target_path, vars)
		except Exception, e:
			shutil.rmtree(target_path, True)
			self.nginx_remove(w, False)
			raise InstallError('Webapp config - '+str(e))

		if enable is True:
			try:
				self.nginx_enable(w)
			except:
				raise ReloadError('nginx')
		if enable is True and wa.php is True:
			try:
				self.php_reload()
			except:
				raise ReloadError('PHP-FPM')

		# Make sure that nginx is enabled by default
		cat.app.get_backend(apis.services.IServiceManager).enable('nginx')

		cat.clr_statusmsg()

		if specialmsg:
			return specialmsg

	def add_reverse_proxy(self, name, path, addr, port, block):
		w = Webapp()
		w.name = name
		w.stype = 'ReverseProxy'
		w.path = path
		w.addr = addr
		w.port = port
		if not block:
			block = [
				nginx.Location('/admin/media/',
					nginx.Key('root', '/usr/lib/python2.7/site-packages/django/contrib')
				),
				nginx.Location('/',
					nginx.Key('proxy_set_header', 'X-Forwarded-For $proxy_add_x_forwarded_for'),
					nginx.Key('proxy_set_header', 'Host $http_host'),
					nginx.Key('proxy_redirect', 'off'),
					nginx.If('(!-f $request_filename)',
						nginx.Key('proxy_pass', 'unix:%s'%os.path.join(path, 'gunicorn.sock')),
						nginx.Key('break', '')
					)
				)
			]
		self.nginx_add(w, block)
		self.nginx_enable(w)

	def remove(self, cat, site):
		if site.sclass != '' and site.stype != 'ReverseProxy':
			cat.put_statusmsg('Preparing for removal...')
			site.sclass.pre_remove(site.name, site.path)
		cat.put_statusmsg('Removing website...')
		if site.path.endswith('_site'):
			shutil.rmtree(site.path.split('/_site')[0])
		elif site.path.endswith('htdocs'):
			shutil.rmtree(site.path.split('/htdocs')[0])
		else:
			shutil.rmtree(site.path)
		self.nginx_remove(site)
		apis.webapps(self.app).cert_remove_notify(site.name,
			site.stype)
		if site.sclass != '' and site.stype != 'ReverseProxy':
			cat.put_statusmsg('Cleaning up...')
			site.sclass.post_remove(site.name)

		cat.clr_statusmsg()

	def nginx_add(self, site, add):
		if site.path == '':
			site.path = os.path.join('/srv/http/webapps/', site.name)
		c = nginx.Conf()
		c.add(nginx.Comment('GENESIS %s %s' % (site.stype, 'http://'+site.addr+':'+site.port)))
		s = nginx.Server(
			nginx.Key('listen', site.port),
			nginx.Key('server_name', site.addr),
			nginx.Key('root', site.path),
			nginx.Key('index', 'index.'+('php' if site.php else 'html'))
		)
		if add:
			s.add(*[x for x in add])
		c.add(s)
		nginx.dumpf(c, os.path.join('/etc/nginx/sites-available', site.name))

	def nginx_edit(self, oldsite, site):
		# Update the nginx serverblock
		c = nginx.loadf(os.path.join('/etc/nginx/sites-available', oldsite.name))
		c.filter('Comment')[0].comment = 'GENESIS %s %s' % (site.stype, (('https://' if site.ssl else 'http://')+site.addr+':'+site.port))
		s = c.servers[0]
		if oldsite.ssl and oldsite.port == '443':
			for x in c.servers:
				if x.filter('Key', 'listen')[0].value == '443 ssl':
					s = x
			if site.port != '443':
				for x in c.servers:
					if not 'ssl' in x.filter('Key', 'listen')[0].value \
					and x.filter('key', 'return'):
						c.remove(x)
		elif site.port == '443':
			c.add(nginx.Server(
				nginx.Key('listen', '80'),
				nginx.Key('server_name', site.addr),
				nginx.Key('return', '301 https://%s$request_uri'%site.addr)
			))
		s.filter('Key', 'listen')[0].value = site.port+' ssl' if site.ssl else site.port
		s.filter('Key', 'server_name')[0].value = site.addr
		s.filter('Key', 'root')[0].value = site.path
		s.filter('Key', 'index')[0].value = 'index.php' if site.php else 'index.html'
		nginx.dumpf(c, os.path.join('/etc/nginx/sites-available', oldsite.name))
		# If the name was changed, rename the folder and files
		if site.name != oldsite.name:
			if os.path.exists(os.path.join('/srv/http/webapps', site.name)):
				shutil.rmtree(os.path.join('/srv/http/webapps', site.name))
			shutil.move(os.path.join('/srv/http/webapps', oldsite.name), 
				os.path.join('/srv/http/webapps', site.name))
			shutil.move(os.path.join('/etc/nginx/sites-available', oldsite.name),
				os.path.join('/etc/nginx/sites-available', site.name))
			self.nginx_disable(oldsite, reload=False)
			self.nginx_enable(site)
		self.nginx_reload()

	def nginx_remove(self, site, reload=True):
		try:
			self.nginx_disable(site, reload)
		except:
			pass
		os.unlink(os.path.join('/etc/nginx/sites-available', site.name))

	def nginx_enable(self, site, reload=True):
		origin = os.path.join('/etc/nginx/sites-available', site.name)
		target = os.path.join('/etc/nginx/sites-enabled', site.name)
		if not os.path.exists(target):
			os.symlink(origin, target)
		if reload == True:
			self.nginx_reload()

	def nginx_disable(self, site, reload=True):
		os.unlink(os.path.join('/etc/nginx/sites-enabled', site.name))
		if reload == True:
			self.nginx_reload()

	def nginx_reload(self):
		status = shell_cs('systemctl restart nginx')
		if status[0] >= 1:
			raise Exception('nginx failed to reload.')

	def php_enable(self):
		shell('sed -i "s/.*include \/etc\/nginx\/php.conf.*/\tinclude \/etc\/nginx\/php.conf;/" /etc/nginx/nginx.conf')

	def php_disable(self):
		shell('sed -i "s/.*include \/etc\/nginx\/php.conf.*/\t#include \/etc\/nginx\/php.conf;/" /etc/nginx/nginx.conf')

	def php_reload(self):
		status = shell_cs('systemctl restart php-fpm')
		if status[0] >= 1:
			raise Exception('PHP FastCGI failed to reload.')

	def ssl_enable(self, data, cpath, kpath):
		# If no cipher preferences set, use the default ones
		# As per Mozilla recommendations, but substituting 3DES for RC4
		from genesis.plugins.certificates.backend import CertControl
		ciphers = ':'.join([
			'ECDHE-RSA-AES128-GCM-SHA256', 'ECDHE-ECDSA-AES128-GCM-SHA256',
			'ECDHE-RSA-AES256-GCM-SHA384', 'ECDHE-ECDSA-AES256-GCM-SHA384',
			'kEDH+AESGCM', 'ECDHE-RSA-AES128-SHA256', 
			'ECDHE-ECDSA-AES128-SHA256', 'ECDHE-RSA-AES128-SHA', 
			'ECDHE-ECDSA-AES128-SHA', 'ECDHE-RSA-AES256-SHA384',
			'ECDHE-ECDSA-AES256-SHA384', 'ECDHE-RSA-AES256-SHA', 
			'ECDHE-ECDSA-AES256-SHA', 'DHE-RSA-AES128-SHA256',
			'DHE-RSA-AES128-SHA', 'DHE-RSA-AES256-SHA256', 
			'DHE-DSS-AES256-SHA', 'AES128-GCM-SHA256', 'AES256-GCM-SHA384',
			'ECDHE-RSA-DES-CBC3-SHA', 'ECDHE-ECDSA-DES-CBC3-SHA',
			'EDH-RSA-DES-CBC3-SHA', 'EDH-DSS-DES-CBC3-SHA', 
			'DES-CBC3-SHA', 'HIGH', '!aNULL', '!eNULL', '!EXPORT', '!DES',
			'!RC4', '!MD5', '!PSK'
			])
		cfg = self.app.get_config(CertControl(self.app))
		if hasattr(cfg, 'ciphers') and cfg.ciphers:
			ciphers = cfg.ciphers
		elif hasattr(cfg, 'ciphers'):
			cfg.ciphers = ciphers
			cfg.save()

		name, stype = data.name, data.stype
		port = '443'
		c = nginx.loadf('/etc/nginx/sites-available/'+name)
		s = c.servers[0]
		l = s.filter('Key', 'listen')[0]
		if l.value == '80':
			l.value = '443 ssl'
			port = '443'
			c.add(nginx.Server(
				nginx.Key('listen', '80'),
				nginx.Key('server_name', data.addr),
				nginx.Key('return', '301 https://%s$request_uri'%data.addr)
			))
			for x in c.servers:
				if x.filter('Key', 'listen')[0].value == '443 ssl':
					s = x
					break
		else:
			port = l.value.split(' ssl')[0]
			l.value = l.value.split(' ssl')[0] + ' ssl'
		for x in s.all():
			if type(x) == nginx.Key and x.name.startswith('ssl_'):
				s.remove(x)
		s.add(
			nginx.Key('ssl_certificate', cpath),
			nginx.Key('ssl_certificate_key', kpath),
			nginx.Key('ssl_protocols', 'SSLv3 TLSv1 TLSv1.1 TLSv1.2'),
			nginx.Key('ssl_ciphers', ciphers),
			nginx.Key('ssl_session_timeout', '5m'),
			nginx.Key('ssl_prefer_server_ciphers', 'on'),
			nginx.Key('ssl_session_cache', 'shared:SSL:50m'),
			)
		c.filter('Comment')[0].comment = 'GENESIS %s https://%s:%s' \
			% (stype, data.addr, port)
		nginx.dumpf(c, '/etc/nginx/sites-available/'+name)
		apis.webapps(self.app).get_interface(stype).ssl_enable(
			os.path.join('/srv/http/webapps', name), cpath, kpath)

	def ssl_disable(self, data):
		name, stype = data.name, data.stype
		port = '80'
		s = None
		c = nginx.loadf('/etc/nginx/sites-available/'+name)
		if len(c.servers) > 1:
			for x in c.servers:
				if not 'ssl' in x.filter('Key', 'listen')[0].value \
				and x.filter('key', 'return'):
					c.remove(x)
					break
		s = c.servers[0]
		l = s.filter('Key', 'listen')[0]
		if l.value == '443 ssl':
			l.value = '80'
			port = '80'
		else:
			l.value = l.value.rstrip(' ssl')
			port = l.value
		s.remove(*[x for x in s.filter('Key') if x.name.startswith('ssl_')])
		c.filter('Comment')[0].comment = 'GENESIS %s http://%s:%s' \
			% (stype, data.addr, port)
		nginx.dumpf(c, '/etc/nginx/sites-available/'+name)
		apis.webapps(self.app).get_interface(stype).ssl_disable(
			os.path.join('/srv/http/webapps', name))

########NEW FILE########
__FILENAME__ = main
from genesis.com import *
from genesis.api import *
from genesis.plugins.core.api import *
from genesis.ui import *
from genesis import apis
from genesis.utils import *
from genesis.plugins.databases.utils import *
from genesis.plugins.network.backend import IHostnameManager

import re

from backend import WebappControl
from api import Webapp


class WebAppsPlugin(apis.services.ServiceControlPlugin):
	text = 'Websites'
	iconfont = 'gen-earth'
	folder = 'servers'
	services = []

	def on_init(self):
		if self._relsec != None:
			if self._relsec[0] == 'add':
				apis.networkcontrol(self.app).add_webapp(self._relsec[1])
				self._relsec = None
			elif self._relsec[0] == 'del':
				apis.networkcontrol(self.app).remove_webapp(self._relsec[1])
			self._relsec = None
		self.services = []
		self.apiops = apis.webapps(self.app)
		self.dbops = apis.databases(self.app)
		self.mgr = WebappControl(self.app)
		self.sites = sorted(self.apiops.get_sites(), 
			key=lambda st: st.name)
		ats = sorted([x.plugin_info for x in self.apiops.get_apptypes()], key=lambda x: x.name.lower())
		self.apptypes = sorted(ats, key=lambda x: (hasattr(x, 'sort')))
		if len(self.sites) != 0:
			self.services.append(
				{
					"name": 'Web Server',
					"binary": 'nginx',
					"ports": []
				}
			)
			for x in self.sites:
				if x.php:
					self.services.append(
						{
							"name": 'PHP FastCGI',
							"binary": 'php-fpm',
							"ports": []
						}
					)
					break
		if not self._current:
			self._current = self.apptypes[0] if len(self.apptypes) else None
		for apptype in self.apptypes:
			ok = False
			for site in self.sites:
				if site.stype == apptype.wa_plugin:
					ok = True
			if ok == False:
				continue
			if hasattr(apptype, 'services'):
				for dep in apptype.services:
					post = True
					for svc in self.services:
						if svc['binary'] == dep['binary']:
							post = False
					if post == True:
						self.services.append({"name": dep['name'], "binary": dep['binary'], "ports": []})

	def on_session_start(self):
		self._add = None
		self._edit = None
		self._setup = None
		self._relsec = None
		self._dbauth = ('','','')

	def get_main_ui(self):
		ui = self.app.inflate('webapps:main')
		t = ui.find('list')

		for s in self.sites:
			if s.addr and s.ssl:
				addr = 'https://' + s.addr + (':'+s.port if s.port != '443' else '')
			elif s.addr:
				addr = 'http://' + s.addr + (':'+s.port if s.port != '80' else '')
			else:
				addr = False

			t.append(UI.DTR(
				UI.Iconfont(iconfont=s.sclass.plugin_info.iconfont if s.sclass and hasattr(s.sclass.plugin_info, 'iconfont') else 'gen-earth'),
				(UI.OutLinkLabel(
					text=s.name,
					url=addr
					) if s.addr is not False else UI.Label(text=s.name)
				),
				UI.Label(text=s.stype),
				UI.HContainer(
					UI.TipIcon(
						iconfont='gen-minus-circle' if s.enabled else 'gen-checkmark-circle',
						id=('disable/' if s.enabled else 'enable/') + str(self.sites.index(s)),
						text='Disable' if s.enabled else 'Enable'
					),
					UI.TipIcon(
						iconfont='gen-tools',
						id='config/' + str(self.sites.index(s)),
						text='Configure'
					),
					UI.TipIcon(
						iconfont='gen-cancel-circle',
						id='drop/' + str(self.sites.index(s)),
						text='Delete',
						warning='Are you sure you wish to delete site %s? This action is irreversible.%s'%(s.name,
							' If this Reverse Proxy was set up automatically by Genesis, this may cause the associated plugin to stop functioning.' if s.stype == 'ReverseProxy' else '')
						)
					),
				))

		provs = ui.find('provs')

		for apptype in self.apptypes:
			provs.append(
					UI.ListItem(
						UI.Label(text=apptype.name),
						id=apptype.name,
						active=apptype.name==self._current.name
					)
				)

		info = self._current
		if info:
			if info.logo:
				ui.find('logo').append(UI.Image(file='/dl/'+self._current.id+'/logo.png'))
			ui.find('appname').set('text', info.name)
			ui.find('short').set('text', info.desc)
			if info.app_homepage is None:
				ui.find('website').set('text', 'None')
				ui.find('website').set('url', 'http://localhost')
			else:
				ui.find('website').set('text', info.app_homepage)
				ui.find('website').set('url', info.app_homepage)
			ui.find('desc').set('text', info.longdesc)

		if self._add is None:
			ui.remove('dlgAdd')

		if self._setup is not None:
			ui.find('addr').set('value', self.app.get_backend(IHostnameManager).gethostname().lower())
			if self._setup.nomulti is True:
				for site in self.sites:
					if self._setup.wa_plugin in site.stype:
						ui.remove('dlgSetup')
						ui.remove('dlgEdit')
						self.put_message('err', 'Only one site of this type at any given time')
						self._setup = None
						return ui
			try:
				cfgui = self.app.inflate(self._setup.id + ':conf')
				if hasattr(self.apiops.get_interface(self._setup.wa_plugin), 'show_opts_add'):
					self.apiops.get_interface(self._setup.wa_plugin).show_opts_add(cfgui)
				ui.append('app-config', cfgui)
			except:
				ui.find('app-config').append(UI.Label(text="No config options available for this app"))
		else:
			ui.remove('dlgSetup')

		if self._edit is not None:
			try:
				edgui = self.app.inflate(self._edit.stype.lower() + ':edit')
				ui.append('dlgEdit', edgui)
			except:
				pass
			ui.find('cfgname').set('value', self._edit.name)
			ui.find('cfgaddr').set('value', self._edit.addr)
			ui.find('cfgport').set('value', self._edit.port)
		else:
			ui.remove('dlgEdit')

		if self._dbauth[0] and not self.dbops.get_interface(self._dbauth[0]).checkpwstat():
			self.put_message('err', '%s does not have a root password set. '
				'Please add this via the Databases screen.' % self._dbauth[0])
			self._dbauth = ('','','')
		if self._dbauth[0]:
			ui.append('main', UI.InputBox(id='dlgAuth%s' % self._dbauth[0], 
				text='Enter the database password for %s' 
				% self._dbauth[0], password=True))

		return ui

	@event('button/click')
	def on_click(self, event, params, vars = None):
		if params[0] == 'add':
			if self.apptypes == []:
				self.put_message('err', 'No webapp types installed. Check the Applications tab to find some')
			else:
				self._add = len(self.sites)
		elif params[0] == 'config':
			self._edit = self.sites[int(params[1])]
		elif params[0] == 'drop':
			if hasattr(self.sites[int(params[1])], 'dbengine') and \
			self.sites[int(params[1])].dbengine and \
			self.dbops.get_info(self.sites[int(params[1])].dbengine).requires_conn and \
			not self.dbops.get_dbconn(self.sites[int(params[1])].dbengine):
				self._dbauth = (self.sites[int(params[1])].dbengine, 
					self.sites[int(params[1])], 'drop')
			else:
				w = WAWorker(self, 'drop', self.sites[int(params[1])])
				w.start()
		elif params[0] == 'enable':
			self.mgr.nginx_enable(self.sites[int(params[1])])
		elif params[0] == 'disable':
			self.mgr.nginx_disable(self.sites[int(params[1])])
		else: 
			for x in self.apptypes:
				if x.name.lower() == params[0]:
					speccall = getattr(self.apiops.get_interface(x.wa_plugin), params[1])
					speccall(self._edit)

	@event('dialog/submit')
	def on_submit(self, event, params, vars = None):
		if params[0] == 'dlgAdd':
			if vars.getvalue('action', '') == 'OK':
				if hasattr(self._current, 'dbengine') and self._current.dbengine:
					on = False
					for dbtype in self.dbops.get_dbtypes():
						if self._current.dbengine == dbtype[0] and dbtype[2] == True:
							on = True
						elif self._current.dbengine == dbtype[0] and dbtype[2] == None:
							on = True
					if on:
						if self.dbops.get_info(self._current.dbengine).requires_conn and \
						not self.dbops.get_dbconn(self._current.dbengine):
							self._dbauth = (self._current.dbengine, '', 'add')
						else:
							self._setup = self._current
					else:
						self.put_message('err', 'The database engine for %s is not running. Please start it via the Status button.' % self._current.dbengine)
				else:
					self._setup = self._current
			self._add = None
		if params[0] == 'dlgEdit':
			if vars.getvalue('action', '') == 'OK':
				name = vars.getvalue('cfgname', '')
				addr = vars.getvalue('cfgaddr', '')
				port = vars.getvalue('cfgport', '')
				vaddr = True
				for site in self.sites:
					if addr == site.addr and port == site.port:
						vaddr = False
				if name == '':
					self.put_message('err', 'Must choose a name')
				elif re.search('\.|-|`|\\\\|\/|^test$|[ ]', name):
					self.put_message('err', 'Site name must not contain spaces, dots, dashes or special characters')
				elif addr == '':
					self.put_message('err', 'Must choose an address')
				elif port == '':
					self.put_message('err', 'Must choose a port (default 80)')
				elif port == self.app.gconfig.get('genesis', 'bind_port', ''):
					self.put_message('err', 'Can\'t use the same port number as Genesis')
				elif not vaddr:
					self.put_message('err', 'Site must have either a different domain/subdomain or a different port')
				elif self._edit.ssl and port == '80':
					self.put_message('err', 'Cannot set an HTTPS site to port 80')
				elif not self._edit.ssl and port == '443':
					self.put_message('err', 'Cannot set an HTTP-only site to port 443')
				else:
					w = Webapp()
					w.name = name
					w.stype = self._edit.stype
					w.path = self._edit.path
					w.addr = addr
					w.port = port
					w.ssl = self._edit.ssl
					w.php = self._edit.php
					self.mgr.nginx_edit(self._edit, w)
					apis.networkcontrol(self.app).change_webapp(self._edit, w)
					self.put_message('info', 'Site edited successfully')
			self._edit = None
		if params[0] == 'dlgSetup':
			if vars.getvalue('action', '') == 'OK':
				name = vars.getvalue('name', '').lower()
				addr = vars.getvalue('addr', '')
				port = vars.getvalue('port', '80')
				vname, vaddr = True, True
				for site in self.sites:
					if name == site.name:
						vname = False
					if addr == site.addr and port == site.port:
						vaddr = False
				if not name or not self._setup:
					self.put_message('err', 'Name or type not selected')
				elif re.search('\.|-|`|\\\\|\/|^test$|[ ]', name):
					self.put_message('err', 'Site name must not contain spaces, dots, dashes or special characters')
				elif addr == '':
					self.put_message('err', 'Must choose an address')
				elif port == '':
					self.put_message('err', 'Must choose a port (default 80)')
				elif port == self.app.gconfig.get('genesis', 'bind_port', ''):
					self.put_message('err', 'Can\'t use the same port number as Genesis')
				elif not vaddr:
					self.put_message('err', 'Site must have either a different domain/subdomain or a different port')
				elif not vname:
					self.put_message('err', 'A site with this name already exists')
				else:
					w = WAWorker(self, 'add', name, self._current, vars)
					w.start()
			self._setup = None
		if params[0].startswith('dlgAuth'):
			dbtype = params[0].split('dlgAuth')[1]
			if vars.getvalue('action', '') == 'OK':
				login = vars.getvalue('value', '')
				try:
					dbauth = self._dbauth
					self._dbauth = ('','','')
					self.dbops.get_interface(dbtype).connect(
						store=self.app.session['dbconns'],
						passwd=login)
					if dbauth[2] == 'drop':
						w = WAWorker(self, 'drop', dbauth[1])
						w.start()
					elif dbauth[2] == 'add':
						self._setup = self._current
				except DBAuthFail, e:
					self.put_message('err', str(e))
			else:
				self.put_message('info', 'Website %s cancelled' % self._dbauth[2])
				self._dbauth = ('','','')

	@event('listitem/click')
	def on_list_click(self, event, params, vars=None):
		for p in self.apptypes:
			if p.name == params[0]:
				self._current = p


class WAWorker(BackgroundWorker):
	def run(self, cat, action, site, current='', vars=None):
		if action == 'add':
			try:
				spmsg = WebappControl(cat.app).add(
					cat, site, current, vars, True)
			except Exception, e:
				cat.clr_statusmsg()
				cat.put_message('err', str(e))
				cat.app.log.error(str(e))
			else:
				cat.put_message('info', 
					'%s added sucessfully' % site)
				cat._relsec = ('add', (site, current.name, vars.getvalue('port', '80')))
				if spmsg:
					cat.put_message('info', spmsg)
		elif action == 'drop':
			try:
				WebappControl(cat.app).remove(cat, site)
			except Exception, e:
				cat.clr_statusmsg()
				cat.put_message('err', 'Website removal failed: ' + str(e))
				cat.app.log.error('Website removal failed: ' + str(e))
			else:
				cat.put_message('info', 'Website successfully removed')
				cat._relsec = ('del', site.name)

########NEW FILE########
__FILENAME__ = plugmgr
"""
Tools for manipulating plugins and repository
"""

__all__ = [
    'BaseRequirementError',
    'PlatformRequirementError',
    'PluginRequirementError',
    'ModuleRequirementError',
    'SoftwareRequirementError',
    'PluginLoader',
    'RepositoryManager',
    'PluginInfo',
]

import os
import imp
import json
import sys
import traceback
import weakref
import urllib2

from genesis.api import *
from genesis.com import *
from genesis.utils import BackgroundWorker, detect_platform, shell, shell_cs, shell_status, download
import genesis

RETRY_LIMIT = 10


class BaseRequirementError(Exception):
    """
    Basic exception that means a plugin wasn't loaded due to unmet
    dependencies
    """


class PlatformRequirementError(BaseRequirementError):
    """
    Exception that means a plugin wasn't loaded due to
    unsupported platform
    """

    def __init__(self, lst):
        BaseRequirementError.__init__(self)
        self.lst = lst

    def __str__(self):
        return 'requires platforms %s' % self.lst


class GenesisVersionRequirementError(BaseRequirementError):
    """
    Exception that means a plugin wasn't loaded due to
    unsupported Genesis version
    """

    def __init__(self, lst):
        BaseRequirementError.__init__(self)
        self.lst = lst

    def __str__(self):
        return 'requires %s' % self.lst


class PluginRequirementError(BaseRequirementError):
    """
    Exception that means a plugin wasn't loaded due to
    required plugin being unavailable
    """

    def __init__(self, dep):
        BaseRequirementError.__init__(self)
        self.name = dep['name']
        self.package = dep['package']

    def __str__(self):
        return 'requires plugin "%s"' % self.name


class ModuleRequirementError(BaseRequirementError):
    """
    Exception that means a plugin wasn't loaded due to
    required Python module being unavailable
    """

    def __init__(self, dep, restart):
        BaseRequirementError.__init__(self)
        self.name = dep['name'] if type(dep) == dict else dep
        self.restart = restart

    def __str__(self):
        if self.restart:
            return 'Dependency "%s" has been installed. Please reload Genesis to use this plugin.' % self.name
        else:
            return 'requires Python module "%s"' % self.name


class SoftwareRequirementError(BaseRequirementError):
    """
    Exception that means a plugin wasn't loaded due to
    required software being unavailable
    """

    def __init__(self, dep):
        BaseRequirementError.__init__(self)
        self.name = dep['name']
        self.pack = dep['package']
        self.bin = dep['binary']

    def __str__(self):
        return 'requires application "%s" (package: %s, executable: %s)' % (self.name, self.pack, self.bin)


class CrashedError(BaseRequirementError):
    """
    Exception that means a plugin crashed during load
    """

    def __init__(self, inner):
        BaseRequirementError.__init__(self)
        self.inner = inner

    def __str__(self):
        return 'crashed during load: %s' % self.inner


class ImSorryDave(Exception):
    """
    General exception when an attempted operation has a conflict
    """
    def __init__(self, target, depend, reason):
        self.target = target
        self.reason = reason
        self.depend = depend

    def __str__(self):
        if self.reason == 'remove':
            return ('%s can\'t be removed, as %s still depends on it. '
                'Please remove that first if you would like to remove '
                'this plugin.' % (self.target, self.depend))
        else:
            return ('%s can\'t be installed, as it depends on %s. Please '
                'install that first.' % (self.target, self.depend))


class PluginLoader:
    """
    Handles plugin loading and unloading
    """

    __classes = {}
    __plugins = {}
    __submods = {}
    __managers = []
    __observers = []
    platform = None
    log = None
    path = None

    @staticmethod
    def initialize(log, path, arch, platform):
        """
        Initializes the PluginLoader

        :param  log:        Logger
        :type   log:        :class:`logging.Logger`
        :param  path:       Path to the plugins
        :type   path:       str
        :param  platform:   System platform for plugin validation
        :type   platform:   str
        """

        PluginLoader.log = log
        PluginLoader.path = path
        PluginLoader.arch = arch
        PluginLoader.platform = platform

    @staticmethod
    def list_plugins():
        """
        Returns dict of :class:`PluginInfo` for all plugins
        """

        return PluginLoader.__plugins

    @staticmethod
    def register_mgr(mgr):
        """
        Registers an :class:`genesis.com.PluginManager` from which the unloaded
        classes will be removed when a plugin is unloaded
        """
        PluginLoader.__managers.append(mgr)

    @staticmethod
    def register_observer(mgr):
        """
        Registers an observer which will be notified when plugin set is changed.
        Observer should have a callable ``plugins_changed`` method.
        """
        PluginLoader.__observers.append(weakref.ref(mgr,
            callback=PluginLoader.__unregister_observer))

    @staticmethod
    def __unregister_observer(ref):
        PluginLoader.__observers.remove(ref)

    @staticmethod
    def notify_plugins_changed():
        """
        Notifies all observers that plugin set has changed.
        """
        for o in PluginLoader.__observers:
            if o():
                o().plugins_changed()

    @staticmethod
    def load(plugin, cat=''):
        """
        Loads given plugin
        """
        log = PluginLoader.log
        path = PluginLoader.path
        platform = PluginLoader.platform
        from genesis import generation, version

        if cat:
            cat.put_statusmsg('Loading plugin %s...' % plugin)
        log.debug('Loading plugin %s' % plugin)

        try:
            mod = imp.load_module(plugin, *imp.find_module(plugin, [path]))
            log.debug('  -- version ' + mod.VERSION)
        except:
            log.warn(' *** Plugin not loadable: ' + plugin)
            return

        info = PluginInfo()
        try:
            d = None
            # Save info
            info.id = plugin
            info.ptype = mod.TYPE
            info.iconfont = mod.ICON
            info.services = mod.SERVICES if hasattr(mod, 'SERVICES') else []
            info.name, info.version = mod.NAME, mod.VERSION
            info.desc, info.longdesc = mod.DESCRIPTION, mod.LONG_DESCRIPTION if hasattr(mod, 'LONG_DESCRIPTION') else ''
            info.author, info.homepage, info.logo = mod.AUTHOR, mod.HOMEPAGE, mod.LOGO if hasattr(mod, 'LOGO') else False
            info.app_author, info.app_homepage = mod.APP_AUTHOR if hasattr(mod, 'APP_AUTHOR') else None, \
                mod.APP_HOMEPAGE if hasattr(mod, 'APP_HOMEPAGE') else None
            info.cats = mod.CATEGORIES
            info.deps = []
            info.problem = None
            info.installed = True
            info.descriptor = mod

            # Add special information
            if info.ptype == 'webapp':
                info.wa_plugin, info.dpath = mod.WA_PLUGIN, mod.DPATH
                info.dbengine = mod.DBENGINE if hasattr(mod, 'DBENGINE') else None
                info.php, info.nomulti, info.ssl = mod.PHP, mod.NOMULTI, mod.SSL
            elif info.ptype == 'database':
                info.db_name, info.db_plugin, info.db_task = mod.DB_NAME, mod.DB_PLUGIN, mod.DB_TASK
                info.multiuser, info.requires_conn = mod.MULTIUSER, mod.REQUIRES_CONN
            info.f2b = mod.F2B if hasattr(mod, 'F2B') else None
            info.f2b_name = mod.F2B_NAME if hasattr(mod, 'F2B_NAME') else None
            info.f2b_icon = mod.F2B_ICON if hasattr(mod, 'F2B_ICON') else None

            PluginLoader.__plugins[plugin] = info

            # Verify platform
            if mod.PLATFORMS != ['any'] and not platform in mod.PLATFORMS:
                raise PlatformRequirementError(mod.PLATFORMS)

            # Verify version
            if not hasattr(mod, 'GENERATION') or mod.GENERATION != generation:
                raise GenesisVersionRequirementError('other Genesis platform generation')

            # Verify dependencies
            if hasattr(mod, 'DEPENDENCIES'):
                deps = []
                for k in mod.DEPENDENCIES:
                    if platform.lower() in k or 'any' in k:
                        deps = mod.DEPENDENCIES[k]
                        break
                info.deps = deps
                for req in deps:
                    d = PluginLoader.verify_dep(req, cat)

            PluginLoader.__classes[plugin] = []
            PluginLoader.__submods[plugin] = {}

            # Load submodules
            for submod in mod.MODULES:
                try:
                    log.debug('  -> %s' % submod)
                    PluginManager.start_tracking()
                    m = imp.load_module(plugin + '.' + submod, *imp.find_module(submod, mod.__path__))
                    classes = PluginManager.stop_tracking()
                    # Record new Plugin subclasses
                    PluginLoader.__classes[plugin] += classes
                    # Store submodule
                    PluginLoader.__submods[plugin][submod] = m
                    setattr(mod, submod, m)
                except ImportError, e:
                    del mod
                    raise ModuleRequirementError(e.message.split()[-1], False)
                except Exception:
                    del mod
                    raise

            # Store the whole plugin
            setattr(genesis.plugins, plugin, mod)
            PluginLoader.notify_plugins_changed()
            if d:
                return d
        except BaseRequirementError, e:
            info.problem = e
            raise e
        except Exception, e:
            log.warn(' *** Plugin loading failed: %s' % str(e))
            print traceback.format_exc()
            PluginLoader.unload(plugin)
            info.problem = CrashedError(e)

    @staticmethod
    def load_plugins():
        """
        Loads all plugins from plugin path
        """
        log = PluginLoader.log
        path = PluginLoader.path

        plugs = [plug for plug in os.listdir(path) if not plug.startswith('.')]
        plugs = [plug[:-3] if plug.endswith('.py') else plug for plug in plugs]
        plugs = list(set(plugs)) # Leave just unique items

        queue = plugs
        retries = {}

        while len(queue) > 0:
            plugin = queue[-1]
            if not plugin in retries:
                retries[plugin] = 0

            try:
                PluginLoader.load(plugin)
                queue.remove(plugin)
            except PluginRequirementError, e:
                retries[plugin] += 1
                if retries[plugin] > RETRY_LIMIT:
                    log.error('Circular dependency between %s and %s. Aborting' % (plugin,e.name))
                    sys.exit(1)
                try:
                    queue.remove(e.package)
                    queue.append(e.package)
                    if (e.package in PluginLoader.__plugins) and (PluginLoader.__plugins[e.package].problem is not None):
                        raise e
                except:
                    log.warn('Plugin %s requires plugin %s, which is not available.' % (plugin,e.name))
                    queue.remove(plugin)
            except BaseRequirementError, e:
                log.warn('Plugin %s %s' % (plugin,str(e)))
                PluginLoader.unload(plugin)
                queue.remove(plugin)
            except Exception:
                PluginLoader.unload(plugin)
                queue.remove(plugin)
        log.info('Plugins loaded.')

    @staticmethod
    def unload(plugin):
        """
        Unloads given plugin
        """
        PluginLoader.log.info('Unloading plugin %s'%plugin)
        if plugin in PluginLoader.__classes:
            for cls in PluginLoader.__classes[plugin]:
                for m in PluginLoader.__managers:
                    i = m.instance_get(cls)
                    if i is not None:
                        i.unload()
                PluginManager.class_unregister(cls)
        if plugin in PluginLoader.__plugins:
            del PluginLoader.__plugins[plugin]
        if plugin in PluginLoader.__submods:
            del PluginLoader.__submods[plugin]
        if plugin in PluginLoader.__classes:
            del PluginLoader.__classes[plugin]
        PluginLoader.notify_plugins_changed()

    @staticmethod
    def verify_dep(dep, cat=''):
        """
        Verifies that given plugin dependency is satisfied.
        """
        platform = PluginLoader.platform
        log = PluginLoader.log

        if dep['type'] == 'app':
            if ((dep['binary'] and shell_status('which '+dep['binary']) != 0) \
            or not dep['binary']) and shell_status('pacman -Q '+dep['package']) != 0:
                if platform == 'arch' or platform == 'arkos':
                    try:
                        if cat:
                            cat.put_statusmsg('Installing dependency %s...' % dep['name'])
                        log.warn('Missing %s, which is required by a plugin. Attempting to install...' % dep['name'])
                        shell('pacman -Sy --noconfirm --needed '+dep['package'])
                        if dep['binary']:
                            shell('systemctl enable '+dep['binary'])
                    except Exception, e:
                        log.error('Failed to install %s - %s' % (dep['name'], str(e)))
                        raise SoftwareRequirementError(dep)
                elif platform == 'debian':
                    try:
                        shell('apt-get -y --force-yes install '+dep['package'])
                    except:
                        raise SoftwareRequirementError(dep)
                elif platform == 'gentoo':
                    try:
                        shell('emerge '+dep['package'])
                    except:
                        raise SoftwareRequirementError(dep)
                elif platform == 'freebsd':
                    try:
                        shell('portupgrade -R '+dep['package'])
                    except:
                        raise SoftwareRequirementError(dep)
                elif platform == 'centos' or platform == 'fedora':
                    try:
                        shell('yum -y install  '+dep['package'])
                    except:
                        raise SoftwareRequirementError(dep)
                else:
                    raise SoftwareRequirementError(dep)
        if dep['type'] == 'plugin':
            if not dep['package'] in PluginLoader.list_plugins() or \
                    PluginLoader.__plugins[dep['package']].problem:
                raise PluginRequirementError(dep)
        if dep['type'] == 'module':
            if dep.has_key('binary') and dep['binary']:
                try:
                    exec('import %s'%dep['binary'])
                except:
                    # Let's try to install it anyway
                    s = shell_cs('pip%s install %s' % ('2' if platform in ['arkos', 'arch'] else '', dep['package']))
                    if s[0] != 0:
                        raise ModuleRequirementError(dep, False)
                    else:
                        return 'Restart Genesis for changes to take effect.'
                        raise ModuleRequirementError(dep, False)
            else:
                p = False
                s = shell('pip%s freeze'%'2' if platform in ['arkos', 'arch'] else '')
                for x in s.split('\n'):
                    if dep['package'].lower() in x.split('==')[0].lower():
                        p = True
                if not p:
                    shell('pip%s install %s' % ('2' if platform in ['arkos', 'arch'] else '', dep['package']))
                    raise ModuleRequirementError(dep, True)

    @staticmethod
    def get_plugin_path(app, id):
        """
        Returns path for plugin's files. Parameters: :class:`genesis.core.Application`, ``str``
        """
        if id in PluginLoader.list_plugins():
            return app.config.get('genesis', 'plugins')
        else:
            return os.path.join(os.path.split(__file__)[0], 'plugins') # ./plugins


class RepositoryManager:
    """
    Manages official Genesis plugin repository. ``cfg`` is :class:`genesis.config.Config`

    - ``available`` - list(:class:`PluginInfo`), plugins available in the repository
    - ``installed`` - list(:class:`PluginInfo`), plugins that are locally installed
    - ``upgradable`` - list(:class:`PluginInfo`), plugins that are locally installed
      and have other version in the repository
    """

    def __init__(self, log, cfg):
        self.config = cfg
        self.log = log
        self.server = cfg.get('genesis', 'update_server')
        self.refresh()

    def list_available(self):
        d = {}
        for x in self.available:
            d[x.id] = x
        return d

    def check_conflict(self, id, op):
        """
        Check if an operation can be performed due to dependency conflict
        """
        pdata = PluginLoader.list_plugins()
        if op == 'remove':
            for i in pdata:
                for dep in pdata[i].deps:
                    if dep['type'] == 'plugin' and dep['package'] == id and dep['package'] in [x.id for x in self.installed]:
                        raise ImSorryDave(pdata[dep['package']].name, pdata[i].name, op)
        elif op == 'install':
            t = self.list_available()
            try:
                for i in t[id].deps:
                    for dep in t[id].deps[i]:
                        if dep['type'] == 'plugin' and dep['package'] not in [x.id for x in self.installed]:
                            raise ImSorryDave(t[id].name, t[dep['package']].name, op)
            except KeyError:
                raise Exception('There was a problem in checking dependencies. '
                    'Please try again after refreshing the plugin list. '
                    'If this problem persists, please contact Genesis maintainers.')

    def refresh(self):
        """
        Re-reads saved repository information and rebuilds installed/available lists
        """
        self.available = []
        self.installed = []
        self.update_installed()
        self.update_available()
        self.update_upgradable()

    def update_available(self):
        """
        Re-reads saved list of available plugins
        """
        try:
            data = json.load(open('/var/lib/genesis/plugins.list', 'r'))
        except IOError, e:
            self.log.error('Could not load plugin list file: %s' % str(e))
            data = []
        except ValueError, e:
            self.log.error('Could not parse plugin list file: %s' % str(e))
            data = []

        self.available = []
        for item in data:
            inst = False
            for i in self.installed:
                if i.id == item['id'] and i.version == item['version']:
                    inst = True
                    break
            if inst:
                continue

            i = PluginInfo()
            for k,v in item.items():
                setattr(i, k, v)
            i.installed = False
            i.problem = None
            self.available.append(i)

    def update_installed(self):
        """
        Rebuilds list of installed plugins
        """
        self.installed = sorted(PluginLoader.list_plugins().values(), key=lambda x:x.name)

    def update_upgradable(self):
        """
        Rebuilds list of upgradable plugins
        """
        upg = []
        for p in self.available:
            u = False
            g = None
            for g in self.installed:
                if g.id == p.id and g.version != p.version:
                    u = True
                    break
            if u:
                g.upgradable = p.upgradable = True
                upg += [g]
        self.upgradable = upg

    def update_list(self, crit=False):
        """
        Downloads fresh list of plugins and rebuilds installed/available lists
        """
        from genesis import generation, version
        if not os.path.exists('/var/lib/genesis'):
            os.mkdir('/var/lib/genesis')
        try:
            data = download('http://%s/genesis/list/%s' % (self.server, PluginLoader.platform), crit=crit)
            open('/var/lib/genesis/plugins.list', 'w').write(data)
        except urllib2.HTTPError, e:
            self.log.error('Application list retrieval failed with HTTP Error %s' % str(e.code))
        except urllib2.URLError, e:
            self.log.error('Application list retrieval failed - Server not found or URL malformed. Please check your Internet settings.')
        except IOError, e:
            self.log.error('Failed to write application list to disk.')
        else:
            self.update_installed()
            self.update_available()
            self.update_upgradable()

    def remove(self, id, cat=''):
        """
        Uninstalls given plugin

        :param  id:     Plugin id
        :type   id:     str
        """

        try:
            self.purge = self.config.get('genesis', 'purge')
        except:
            self.purge = '1'

        exclude = ['openssl', 'openssh', 'nginx', 'python2']

        if cat:
            cat.put_statusmsg('Removing plugin...')
        dir = self.config.get('genesis', 'plugins')
        shell('rm -r %s/%s' % (dir, id))

        if id in PluginLoader.list_plugins():
            depends = []
            try:
                pdata = PluginLoader.list_plugins()
                thisplugin = pdata[id].deps
                for thing in thisplugin:
                    if 'app' in thing[0]:
                        depends.append((thing, 0))
                for plugin in pdata:
                    for item in enumerate(depends):
                        if item[1][0] in pdata[plugin].deps:
                            depends[item[0]] = (depends[item[0]][0], depends[item[0]][1]+1)
                for thing in depends:
                    if thing[1] <= 1 and not thing[0][1] in exclude:
                        if cat:
                            cat.put_statusmsg('Removing dependency %s...' % thing[0][1])
                        shell('systemctl stop ' + thing[0][2])
                        shell('systemctl disable ' + thing[0][2])
                        shell('pacman -%s --noconfirm ' %('Rn' if self.purge is '1' else 'R') + thing[0][1])
            except KeyError:
                pass
            PluginLoader.unload(id)

        self.update_installed()
        self.update_available()
        if cat:
            cat.put_message('info', 'Plugin removed. Refresh page for changes to take effect.')

    def install(self, id, load=True, cat=''):
        """
        Installs a plugin

        :param  id:     Plugin id
        :type   id:     str
        :param  load:   True if you want Genesis to load the plugin immediately
        :type   load:   bool
        """
        from genesis import generation, version
        dir = self.config.get('genesis', 'plugins')

        if cat:
            cat.put_statusmsg('Downloading plugin package...')
        download('http://%s/genesis/plugin/%s' % (self.server, id),
            file='%s/plugin.tar.gz'%dir, crit=True)

        self.remove(id)
        self.install_tar(load=load, cat=cat)

    def install_stream(self, stream):
        """
        Installs a plugin from a stream containing the package

        :param  stream: Data stream
        :type   stream: file
        """
        dir = self.config.get('genesis', 'plugins')
        open('%s/plugin.tar.gz'%dir, 'w').write(stream)
        self.install_tar()

    def install_tar(self, load=True, cat=''):
        """
        Unpacks and installs a ``plugin.tar.gz`` file located in the plugins directory.

        :param  load:   True if you want Genesis to load the plugin immediately
        :type   load:   bool
        """
        dir = self.config.get('genesis', 'plugins')

        if cat:
            cat.put_statusmsg('Extracting plugin package...')
        id = shell('tar tzf %s/plugin.tar.gz'%dir).split('\n')[0].strip('/')

        shell('cd %s; tar xf plugin.tar.gz' % dir)
        shell('rm %s/plugin.tar.gz' % dir)

        if load:
            PluginLoader.load(id, cat=cat)

        self.update_installed()
        self.update_available()
        self.update_upgradable()


class PluginInfo:
    """
    Container for the plugin description
    - ``upgradable`` - `bool`, if the plugin can be upgraded
    - ``problem``- :class:`Exception` which occured while loading plugin, else ``None``
    - ``deps`` - list of dependency tuples
    And other fields read by :class:`PluginLoader` from plugin's ``__init__.py``
    """

    def __init__(self):
        self.upgradable = False
        self.problem = None
        self.deps = []

    def str_req(self):
        """
        Formats plugin's unmet requirements into human-readable string

        :returns:    str
        """

        reqs = []
        for p in self.deps:
            if any(x in [PluginLoader.platform, 'any'] for x in p[0]):
                for r in p[1]:
                    try:
                        PluginLoader.verify_dep(r)
                    except Exception, e:
                        reqs.append(str(e))
        return ', '.join(reqs)


class LiveInstall(BackgroundWorker):
    def run(self, rm, id, load, cat):
        d = rm.install(id, load=load, cat=cat)
        if d:
            cat.put_message('info', 'Plugin installed. %s'%str(d))
        ComponentManager.get().rescan()
        ConfManager.get().rescan()
        cat._reloadfw = True
        cat.clr_statusmsg()

class LiveRemove(BackgroundWorker):
    def run(self, rm, id, cat):
        rm.remove(id, cat)
        cat._reloadfw = True
        cat.clr_statusmsg()

########NEW FILE########
__FILENAME__ = standalone
import sys
import os
import logging
import syslog

from genesis.api import ComponentManager
from genesis.config import Config
from genesis.core import Application, AppDispatcher
from genesis.plugmgr import PluginLoader
from genesis import version
from genesis import deployed
import genesis.utils

try:
    from gevent.pywsgi import WSGIServer
    import gevent.pool
    http_server = 'gevent'
except ImportError:
    from wsgiref.simple_server import make_server
    WSGIServer = lambda adr,**kw : make_server(adr[0], adr[1], kw['application'])
    http_server = 'wsgiref'

from datetime import datetime


class DebugHandler (logging.StreamHandler):
    def __init__(self):
        self.capturing = False
        self.buffer = ''

    def start(self):
        self.capturing = True

    def stop(self):
        self.capturing = False

    def handle(self, record):
        if self.capturing:
            self.buffer += self.formatter.format(record) + '\n'

class ConsoleHandler (logging.StreamHandler):
    def __init__(self, stream, debug):
        self.debug = debug
        logging.StreamHandler.__init__(self, stream)

    def handle(self, record):
        if not self.stream.isatty():
            return logging.StreamHandler.handle(self, record)

        s = ''
        d = datetime.fromtimestamp(record.created)
        s += d.strftime("\033[37m%d.%m.%Y %H:%M \033[0m")
        if self.debug:
            s += ('%s:%s'%(record.filename,record.lineno)).ljust(30)
        l = ''
        if record.levelname == 'DEBUG':
            l = '\033[37mDEBUG\033[0m '
        if record.levelname == 'INFO':
            l = '\033[32mINFO\033[0m  '
        if record.levelname == 'WARNING':
            l = '\033[33mWARN\033[0m  '
        if record.levelname == 'ERROR':
            l = '\033[31mERROR\033[0m '
        s += l.ljust(9)
        s += record.msg
        s += '\n'
        self.stream.write(s)


def make_log(debug=False, log_level=logging.INFO):
    log = logging.getLogger('genesis')
    log.setLevel(logging.DEBUG)

    stdout = ConsoleHandler(sys.stdout, debug)
    stdout.setLevel(log_level)

    log.blackbox = DebugHandler()
    log.blackbox.setLevel(logging.DEBUG)
    dformatter = logging.Formatter('%(asctime)s [%(levelname)s] %(module)s: %(message)s')
    log.blackbox.setFormatter(dformatter)
    stdout.setFormatter(dformatter)
    log.addHandler(log.blackbox)

    log.addHandler(stdout)

    return log


def run_server(log_level=logging.INFO, config_file=''):
    log = make_log(debug=log_level==logging.DEBUG, log_level=log_level)

    # For the debugging purposes
    log.info('Genesis %s' % version())

    # We need this early
    genesis.utils.logger = log

    # Read config
    config = Config()
    if config_file:
        log.info('Using config file %s'%config_file)
        config.load(config_file)
    else:
        log.info('Using default settings')

    # Handle first-launch reconfiguration
    deployed.reconfigure(config)
    
    # Add log handler to config, so all plugins could access it
    config.set('log_facility',log)

    # Start recording log for the bug reports
    log.blackbox.start()

    arch = genesis.utils.detect_architecture()
    log.info('Detected architecture/hardware: %s, %s'%(arch[0],arch[1]))

    platform = genesis.utils.detect_platform()
    log.info('Detected platform: %s'%platform)

    # Load external plugins
    PluginLoader.initialize(log, config.get('genesis', 'plugins'), arch[0], platform)
    PluginLoader.load_plugins()

    # Start components
    app = Application(config)
    PluginLoader.register_mgr(app) # Register permanent app
    ComponentManager.create(app)

    # Check system time
    log.info('Verifying system time...')
    os = 0
    try:
        st = genesis.utils.SystemTime()
        os = st.get_offset()
    except Exception, e:
        log.error('System time could not be retrieved. Error: %s' % str(e))
    if os < -3600 or os > 3600:
        log.info('System time was off by %s secs - updating' % str(os))
        try:
            st.set_datetime()
        except Exception, e:
            log.error('System time could not be set. Error: %s' % str(e))

    # Make sure correct kernel modules are enabled
    genesis.utils.shell('modprobe ip_tables')
    genesis.utils.shell('modprobe loop')
    # Load and verify security rules
    log.info('Starting security plugin...')
    genesis.apis.networkcontrol(app).session_start()

    # Start server
    host = config.get('genesis','bind_host')
    port = config.getint('genesis','bind_port')
    log.info('Listening on %s:%d'%(host, port))

    # SSL params
    ssl = {}
    if config.getint('genesis', 'ssl') == 1:
        ssl = {
    	    'keyfile':  config.get('genesis','cert_key'),
    	    'certfile': config.get('genesis','cert_file'),
    	}

    log.info('Using HTTP server: %s'%http_server)

    server = WSGIServer(
        (host, port),
        application=AppDispatcher(config).dispatcher,
        **ssl
    )

    config.set('server', server)

    try:
        syslog.openlog(
            ident='genesis',
            facility=syslog.LOG_AUTH,
        )
    except:
        syslog.openlog('genesis')

    log.info('Starting server')

    server.serve_forever()

    ComponentManager.get().stop()

    if hasattr(server, 'restart_marker'):
        log.info('Restarting by request')

        fd = 20 # Close all descriptors. Creepy thing
        while fd > 2:
            try:
                os.close(fd)
                log.debug('Closed descriptor #%i'%fd)
            except:
                pass
            fd -= 1

        import os
        os.execv(sys.argv[0], sys.argv)
    else:
        log.info('Stopped by request')

########NEW FILE########
__FILENAME__ = classes
import random
from lxml import etree
from genesis.utils import fix_unicode


class Element(etree.ElementBase):
    """
    XML layout element - derived from lxml.ElementBase.
    See http://lxml.de/api/lxml.etree.ElementBase-class.html

    `args` should be child elements and `kwargs` - attributes.
    """
    def __init__(self, tag, *args, **kwargs):
        etree.ElementBase.__init__(self)
        self.tag = tag.lower()
        if not 'id' in kwargs.keys() or kwargs['id'] is None:
            self['id'] = str(random.randint(1,9000*9000))
        self._init(*args, **kwargs)
        self._children = []
        for k in args:
            self.append(k)
        for k in kwargs:
            if kwargs[k] is not None:
                self[k] = kwargs[k]

    def _init(self, *args, **kwargs):
        etree.ElementBase._init(self)
        if not hasattr(self, '_children'):
            self._children = []

    def append(self, el):
        """
        Appends an :class:`Element` or :class:`Layout` to current element.
        """
        if el is not None:
            if hasattr(el, 'elements'):
                el = el.elements()
            self._children.append(el)
            etree.ElementBase.append(self, el)
        return self

    def append_all(self, *els):
        """
        Appends all :class:`Element` or :class:`Layout` instances to current element.
        """
        for el in els:
            self.append(el)
        return self

    def __setitem__(self, idx, val):
        self.set(idx, val)

    def set(self, attr, val):
        """
        Sets `attr` attribute to `val`, converting value to unicode string.
        """
        etree.ElementBase.set(self, attr, fix_unicode(str(val)))
        return self

    def __getitem__(self, idx):
        return self.get(idx)


class UI(object):

    """
    Automatically generate XML tags by calling name

    >>> m = UI.Meta(encoding="ru")
    >>> m.toxml()
    '<meta encoding="ru"/>'
    >>>

    Some of tags have overriding classes here.
    """

    __overrides_cache = None

    class __metaclass__(type):
        def __getattr__(cls, name):
            return lambda *args, **kw: Element(name.lower(), *args, **kw)

    @staticmethod
    def list_overrides():
        if UI.__overrides_cache is None:
            UI.__overrides_cache = dict(
                [(x.lower(),getattr(UI,x)) for x in UI.__dict__]
            )
        return UI.__overrides_cache

    @staticmethod
    def gen(name, *args, **kwargs):
        """ Generate XML tags by name, if name will violate Pyhton syntax

        >>> xi = UI.gen('xml:include', href="some.xml")
        >>> xi.toxml()
        '<xml:include href="some.xml"/>'
        >>>
        """
        return Element(name.lower(), *args, **kwargs)

    class ProgressBar(Element):
        def __init__(self, value=0, max=1, width=1):
            Element.__init__(self, 'progressbar')
            self['right'] = width - int(value*width/max)
            self['left'] = int(value*width/max)

    class LT(Element):
        def __init__(self, *args, **kwargs):
            Element.__init__(self, 'lt', **kwargs)
            for e in args:
                if isinstance(e, Element):
                    if e.tag == 'ltr':
                        self.append(e)
                    else:
                        c = UI.LTR(e)
                        c['spacing'] = self['spacing']
                        self.append(c)

    class LTR(Element):
        def __init__(self, *args, **kwargs):
            Element.__init__(self, 'ltr', **kwargs)
            for e in args:
                if isinstance(e, Element):
                    if e.tag == 'ltd':
                        self.append(e)
                    else:
                        c = UI.LTD(e)
                        c['spacing'] = self['spacing']
                        self.append(c)

    class DT(Element):
        def __init__(self, *args, **kwargs):
            Element.__init__(self, 'dt', **kwargs)
            for e in args:
                if isinstance(e, Element):
                    if e.tag == 'dtr':
                        self.append(e)
                    else:
                        self.append(UI.DTD(e))
            for e in args:
                self.append(e)

    class DTR(Element):
        def __init__(self, *args, **kwargs):
            Element.__init__(self, 'dtr', **kwargs)
            for e in args:
                if isinstance(e, Element):
                    if e.tag in ['dtd', 'dth', 'statuscell']:
                        self.append(e)
                    else:
                        self.append(UI.DTD(e))

    class TreeContainer(Element):
        def __init__(self, *args, **kwargs):
            Element.__init__(self, 'treecontainer', **kwargs)
            for e in args:
                if isinstance(e, Element):
                    if e.tag == 'treecontainer':
                        self.append(e)
                    elif e.tag == 'treecontainernode':
                        self.append(e)
                    else:
                        self.append(UI.TreeContainerNode(e))

    class TabControl(Element):
        def __init__(self, *args, **kwargs):
            Element.__init__(self, 'tabcontrol', **kwargs)
            self.tc = 0

        def add(self, name, content, form=None, id=None):
            if id is None:
                id = str(self.tc)
            tb = UI.TabBody(content, id=id)
            self.append(UI.TabHeader(text=name, id=(id or tb['id']), live=(content is None), form=form))
            if content is not None:
                self.append(tb)
            self.tc += 1



class TreeManager(object):
    """
    Processes treenode click events and stores the nodes' collapsed/expanded
    states. You should keep the TreeManager inside the session, call
    node_click() on each 'click' event, and apply() to the tree object before
    rendering it.
    """
    states = None

    def __init__(self):
        self.reset()

    def reset(self):
        """
        Removes all saved node states.
        """
        self.states = []

    def node_click(self, id):
        """
        Toggles node state (collapsed/expanded)
        """
        if id in self.states:
            self.states.remove(id)
        else:
            self.states.append(id)

    def apply(self, tree):
        """
        Applies saved node states to a TreeContainer element
        """
        try:
            tree['expanded'] = tree['id'] in self.states

            for n in tree._children:
                if n.tag == 'treecontainer':
                    self.apply(n)
        except:
            raise

########NEW FILE########
__FILENAME__ = template
from lxml import etree
from classes import *
import os.path
import xslt

class Layout:
    """
    An XML user interface layout storage. Loads layout data from `file`.
    """

    def __init__(self, file):
        parser = etree.XMLParser()
        parser.set_element_class_lookup(Lookup())
        self._dom = etree.parse(file, parser=parser)

    def find(self, id):
        """
        Finds a child element by `id` attribute.
        """
        el = self._dom.find('//*[@id=\'%s\']'%id)
        return el

    def remove(self, id):
        """
        Removes a child element by `id` attribute.
        """
        el = self.find(id)
        el.getparent().remove(el)

    def xpath(self, path):
        """
        Performs an XPath query on the tree.
        """
        return self._dom.find(path)

    def append(self, dest, child):
        """
        Appends `child` to a tag with `id`=`dest`.
        """
        el = self.find(dest)
        if el is not None:
            if isinstance(child, Layout):
                child = child.elements()
            el.append(child)
        else:
            raise RuntimeError("Tag with id=%s not found"%dest)

    def appendAll(self, dest, *args):
        """
        Appends `*args` to a tag with `id`=`dest`.
        """
        for a in args:
            self.append(dest, a)

    def insertText(self, dest, text):
        """
        Sets node's text.
        """
        self.find(dest).text = text

    def elements(self):
        """
        Returns root element.
        """
        return self._dom.getroot()

    def render(self):
        """
        Renders HTML into a string.
        """
        return xslt.render(self._dom.getroot())


class BasicTemplate(Layout):

    def __init__(self, filename, search_path=[], styles=[], scripts=[]):
        for p in search_path:
            if os.path.isfile(os.path.join(p, filename)):
                filename = os.path.join(p, filename)
        Layout.__init__(self, filename)

        def core_first(path):
            return ((1 if path.startswith('/dl/core') else 2), path)

        # Fill in CSS and JS refs
        try:
            for x in sorted(styles, key=core_first):
                self._dom.find('.//headstylesheets').append(etree.Element('headstylesheet', href=x))
            for x in sorted(scripts, key=core_first):
                self._dom.find('.//headscripts').append(etree.Element('headscript', href=x))
        except:
            pass


class Lookup(etree.CustomElementClassLookup):
    def lookup(self, node_type, document, namespace, name):
        if node_type != 'element':
            return None
        ovs = UI.list_overrides()
        if name in ovs:
            return ovs[name]
        return Element

########NEW FILE########
__FILENAME__ = xslt
from lxml import etree
from lxml.etree import *


xslt = None

def prepare(includes, funcs):
    global xslt, xslt2
    xml = XSLT % ''.join([open(x).read() for x in includes])
    
    ex = {}
    for x in funcs:
        ex[('x', x)] = funcs[x]

    xslt = etree.XSLT(etree.fromstring(xml), extensions=ex)
    xslt2 = etree.XSLT(etree.fromstring(XSLT2), extensions=ex)
        
def render(templ):
    global xslt, xslt2
    return etree.tostring(xslt2(xslt(xslt(templ))), method="html", pretty_print=True) #!!!
    
    

XSLT="""<?xml version="1.0" encoding="utf-8"?>
<xsl:stylesheet version="1.0" 
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform" 
    xmlns:x="x"
    xmlns:h="h"
    extension-element-prefixes="x">
    
  <xsl:output method="html" doctype-public="-//W3C//DTD XHTML 1.0 Transitional//EN" doctype-system="http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd" encoding="utf-8" />

  <xsl:template match="@*|node()">
     <xsl:copy>
        <xsl:apply-templates select="@*|node()"/>
     </xsl:copy>
  </xsl:template>

  <xsl:template match="html">
      <html xmlns="http://www.w3.org/1999/xhtml" class="{@class}">
          <xsl:apply-templates />
      </html>
  </xsl:template>

  <xsl:template match="xml">
      <xsl:apply-templates />
  </xsl:template>
  
  <xsl:template match="headstylesheets">
     <xsl:for-each select="headstylesheet">
         <link href="{@href}" rel="stylesheet/less" />
     </xsl:for-each>
  </xsl:template>

  <xsl:template match="headscripts">
     <xsl:for-each select="headscript">
         <script src="{@href}">
            <xsl:text> </xsl:text>
         </script>
     </xsl:for-each>
  </xsl:template>
  
  %s
  
</xsl:stylesheet>  
"""


XSLT2 = """<?xml version="1.0" encoding="utf-8"?>
<xsl:stylesheet version="1.0" 
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform" 
    xmlns:x="x"
    extension-element-prefixes="x">
    
  <xsl:output method="html" doctype-public="-//W3C//DTD XHTML 1.0 Transitional//EN" doctype-system="http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd" encoding="utf-8" />

  <xsl:template match="@*|node()">
     <xsl:copy>
        <xsl:apply-templates select="@*|node()"/>
     </xsl:copy>
  </xsl:template>

  <xsl:template match="hlabel">
     <label for="{@for}" class="{@class}"><xsl:value-of select="@text" /><xsl:apply-templates /></label>
  </xsl:template>
</xsl:stylesheet>  
"""

########NEW FILE########
__FILENAME__ = error
from genesis.utils import *
from genesis import version
from genesis.ui import UI
from genesis.ui.template import BasicTemplate

import platform
import traceback



class BackendRequirementError(Exception):
    """
    Raised by :func:`genesis.core.Application.get_backend` if backend plugin
    wasn't found.
    """
    def __init__(self, interface):
        Exception.__init__(self)
        self.interface = interface

    def __str__(self):
        return 'Backend required: ' + str(self.interface)


class ConfigurationError(Exception):
    """
    You should raise this exception if ModuleConfig or other configuration means
    contain wrong or non-consitent parameters.
    """
    def __init__(self, hint):
        Exception.__init__(self)
        self.hint = hint

    def __str__(self):
        return 'Plugin failed to configure: ' + self.hint


class SystemTimeError(Exception):
    def __init__(self, offset):
        Exception.__init__(self)
        self.offset = offset

    def __str__(self):
        return 'System time is too far off - offset is ' + str(self.offset)


def format_exception(app, err):
    print '\n%s\n' % err
    templ = app.get_template('error.xml')
    templ.append('trace',
            UI.TextInputArea(value=err, width=550))
    templ.append('report',
            UI.TextInputArea(value=make_report(app, err), width=550))
    return templ.render()


def format_error(app, ex):
    templ = app.get_template('disabled.xml')
    tool = None
    if isinstance(ex, BackendRequirementError):
        reason = 'Required backend is unavailable.'
        hint = 'You need a plugin that provides <b>%s</b> interface support for <b>%s</b> platform.<br/>' % (ex.interface, app.platform)
    elif isinstance(ex, ConfigurationError):
        reason = 'The plugin was unable to start with current configuration.<br/>Consider using configuration dialog for this plugin.'
        hint = ex.hint
    else:
        return format_exception(app, traceback.format_exc())

    templ.append('reason', UI.CustomHTML(html=reason))
    templ.append('hint', UI.CustomHTML(html=hint))
    return templ.render()


def make_report(app, err):
    """
    Formats a bug report.
    """
    from genesis.plugmgr import PluginLoader
    pr = ''
    for p in sorted(PluginLoader.list_plugins().keys()):
        pr += p + '\n'

    # Finalize the reported log
    app.log.blackbox.stop()

    buf = app.log.blackbox.buffer.split('\n')
    if len(buf) >= 50:
      buf = buf[-50:]
      buf.insert(0, '(Showing only the last 50 entries)\n')
    buf = '\n'.join(buf)

    return (('Genesis %s bug report\n' +
           '--------------------\n\n' +
           'System: %s\n' +
           'Detected platform: %s\n' +
           'Detected distro: %s\n' +
           'Python: %s\n\n' +
           'Config path: %s\n\n' +
           '%s\n\n'
           'Loaded plugins:\n%s\n\n' +
           'Log:\n%s\n'
           )
            % (version(),
               shell('uname -a'),
               detect_platform(),
               detect_distro(),
               '.'.join([str(x) for x in platform.python_version_tuple()]),
               app.config.filename,
               err,
               pr,
               buf,
              ))

########NEW FILE########
__FILENAME__ = interlocked
import threading


class ClassProxy (object):
    """
    Wraps class methods into :class:`MethodProxy`, thus making them thread-safe.
    """
    inner = None
    locks = None

    def __init__(self, inner):
        self.inner = inner
        self.locks = {}

    def __getattr__(self, attr):
        if not attr in self.locks:
            self.locks[attr] = threading.Lock()

        return MethodProxy(getattr(self.inner, attr), self.locks[attr])

    def deproxy(self):
        return self.inner


def nonblocking(fun):
    """
    Decorator, prevents a method from being wrapped in a MethodProxy.
    """
    fun.nonblocking = True
    return fun


class MethodProxy (object):
    """
    Prevents a method from being called by two threads simultaneously.
    """
    def __init__(self, method, lock):
        self.lock = lock
        self.method = method

    def __call__(self, *args, **kwargs):
        if hasattr(self.method, 'nonblocking'):
            return self.method(*args, **kwargs)

        self.lock.acquire()

        res = None

        try:
            res = self.method(*args, **kwargs)
        finally:
            self.lock.release()

        return res

########NEW FILE########
__FILENAME__ = misc
import subprocess
import threading
import os
import sys
import pwd


class BackgroundWorker:
    """
    A stoppable background operation.

    Instance vars:

    - ``alive`` - `bool`, if the operation is running
    """
    def __init__(self, *args):
        self.thread = KThread(target=self.__run, args=args)
        self.thread.daemon = True
        self.alive = False
        self.output = ''
        self._aborted = False

    def is_running(self):
        """
        Checks if background thread is running.
        """
        if self.alive:
            return not self.thread.killed
        return False

    def start(self):
        """
        Starts the operation
        """
        if not self.is_running():
            self.thread.start()
        self.alive = True

    def run(self, *args):
        """
        Put the operation body here.
        """

    def __run(self, *args):
        self.run(*args)
        self.alive = False

    def kill(self):
        """
        Aborts the operation thread.
        """
        self._aborted = True
        if self.is_running():
            self.thread.kill()


class BackgroundProcess (BackgroundWorker):
    """
    A class wrapping a background subprocess.
    See :class:`BackgroundWorker`.

    Instance vars:

    - ``output`` - `str`, process' stdout data
    - ``errors`` - `str`, process' stderr data
    - ``exitcode`` - `int`, process' exit code
    - ``cmdline`` - `str`, process' commandline
    """
    def __init__(self, cmd, runas=None):
        BackgroundWorker.__init__(self, cmd, runas)
        self.output = ''
        self.errors = ''
        self.exitcode = None
        self.cmdline = cmd
        self.runas = runas

    def run(self, c, runas):
        """
        Runs the process in foreground
        """
        if runas != None and runas != 'anonymous':
            env = os.environ.copy()
            env['USER'] = runas
            env['LOGNAME'] = runas
            cwd = os.path.expanduser('~'+runas)
            env['HOME'] = cwd
            env['PWD'] = cwd
            self.process = subprocess.Popen(c, shell=True,
                                               stderr=subprocess.PIPE,
                                               stdout=subprocess.PIPE,
                                               stdin=subprocess.PIPE,
                                               preexec_fn=self.as_user(runas),
                                               cwd=cwd,
                                               env=env)
        else:
            self.process = subprocess.Popen(c, shell=True,
                                               stderr=subprocess.PIPE,
                                               stdout=subprocess.PIPE,
                                               stdin=subprocess.PIPE)

        self.output += self.process.stdout.readline() # Workaround; waiting first causes a deadlock
        while self.process.returncode is None and not self._aborted:
            self.output += self.process.stdout.readline()
            self.process.poll()
        self.errors += self.process.stderr.read()
        self.output += self.process.stdout.read()
        self.exitcode = self.process.returncode

    def as_user(self, runas):
        uid = pwd.getpwnam(runas)[2]
        gid = pwd.getpwnam(runas)[3]
        def set_ids():
            os.setgroups([])
            os.setregid(gid, gid)
            os.setreuid(uid, uid)
        return set_ids

    def feed_input(self, data):
        """
        Sends stdin to the process
        """
        if self.is_running():
            self.process.stdin.write(data)

    def kill(self):
        """
        Interrupts the process
        """
        if self.is_running():
            try:
                self.process.terminate()
            except:
                pass
            try:
                self.process.kill()
            except:
                pass
            BackgroundWorker.kill(self)


class KThread(threading.Thread):
    """
    A killable Thread class, derived from :class:`threading.Thread`.
    Instance var ``killed`` - `bool`, shows if the thread was killed.
    """

    def __init__(self, *args, **keywords):
        threading.Thread.__init__(self, *args, **keywords)
        self.killed = False

    def start(self):
        self.__run_backup = self.run
        self.run = self.__run
        threading.Thread.start(self)

    def __run(self):
        sys.settrace(self.globaltrace)
        self.__run_backup()
        self.run = self.__run_backup

    def globaltrace(self, frame, why, arg):
        if why == 'call':
            return self.localtrace
        else:
            return None

    def localtrace(self, frame, why, arg):
        if self.killed:
            if why == 'line':
                raise SystemExit()
        return self.localtrace

    def kill(self):
        """
        Emits ``SystemExit`` inside the thread.
        """
        self.killed = True

########NEW FILE########
__FILENAME__ = PrioList
# encoding: utf-8
#
# Copyright (C) 2006-2010 Dmitry Zamaruev (dmitry.zamaruev@gmail.com)


from UserList import UserList


class PrioList(UserList):
    def __init__(self, max_priority=100):
        super(PrioList, self).__init__()
        self.prio = []
        self._max = max_priority
        self._def = max_priority/2

    def __delitem__(self, i):
        del self.data[i]
        del self.prio[i]

    # Prohibit following operations
    __setslice__ = None
    __delslice__ = None
    __add__ = None
    __radd__ = None
    __iadd__ = None
    __mul__ = None
    __imul__ = None

    def _prio_index(self, prio):
        i = None
        for p, el in enumerate(self.prio):
             if prio < el:
                i = p
                break
        if i is None:
            i = len(self.prio)
        return i

    def _append_prio(self, item, prio):
        i = self._prio_index(prio)
        super(PrioList, self).insert(i, item)
        self.prio.insert(i, prio)

    # Access methods
    def append(self, item):
        if isinstance(item, tuple):
            self._append_prio(item[0], item[1])
        else:
            self._append_prio(item, self._def)

    # Prohibit following methods
    insert = None
    pop = None
    index = None
    reverse = None
    sort = None
    extend = None

########NEW FILE########
__FILENAME__ = utils
import time
import subprocess
import ntplib
import platform
import os
import mimetypes
import urllib2
from datetime import datetime
from hashlib import sha1
from base64 import b64encode
from passlib.hash import sha512_crypt, bcrypt


class SystemTime:
    def get_datetime(self, display=''):
        if display:
            return time.strftime(display)
        else:
            return time.localtime()

    def get_idatetime(self):
        ntp = ntplib.NTPClient()
        resp = ntp.request('0.pool.ntp.org', version=3)
        return resp.tx_time

    def set_datetime(self, dt=''):
        dt = dt if dt else self.get_idatetime()
        e = shell_cs('date -s @%s' % dt)
        if e[0] != 0:
            raise Exception('System time could not be set. Error: %s' % str(e[1]))

    def get_serial_time(self):
        return time.strftime('%Y%m%d%H%M%S')

    def get_date(self):
        return time.strftime('%d %b %Y')

    def get_time(self):
        return time.strftime('%H:%M')

    def get_offset(self):
        ntp = ntplib.NTPClient()
        resp = ntp.request('0.pool.ntp.org', version=3)
        return resp.offset


def enquote(s):
    """
    Inserts ``&lt;`` and ``&gt;`` entities and replaces newlines with ``<br/>``.
    """
    s = s.replace('<', '&lt;').replace('>', '&gt;').replace('\n', '<br/>')
    return s

def fix_unicode(s):
    """
    Tries to fix a broken Unicode string.

    :rtype: str
    """
    d = ''.join(max(i, ' ') if not i in ['\n', '\t', '\r'] else i for i in s)
    return unicode(d.encode('utf-8', 'xmlcharref'), errors='replace')

def cidr_to_netmask(cidr):
    """
    Convert a CIDR to netmask. Takes integer.
    Returns string in xxx.xxx.xxx.xxx format.
    """
    mask = [0, 0, 0, 0]
    for i in range(cidr):
        mask[i/8] = mask[i/8] + (1 << (7 - i % 8))
    return ".".join(map(str, mask))

def netmask_to_cidr(mask):
    """
    Convert a netmask to CIDR. Takes string in xxx.xxx.xxx.xxx format.
    Returns integer.
    """
    mask = mask.split('.')
    binary_str = ''
    for octet in mask:
        binary_str += bin(int(octet))[2:].zfill(8)
    return len(binary_str.rstrip('0'))

def detect_architecture():
    """
    Returns a tuple: current system architecture, and board type
    (if it can be determined).
    :rtype:             tuple(str, str)
    """
    arch, btype = 'Unknown', 'Unknown'
    cpuinfo = {}
    # Get architecture
    for x in shell('lscpu').split('\n'):
        if x.split() and 'Architecture' in x.split()[0]: 
            arch = x.split()[1]
            break
    # Let's play a guessing game!
    if arch in ['x86_64', 'i686']:
        btype = 'General'
    else:
        for x in shell('cat /proc/cpuinfo').split('\n'):
            # Parse output of function function c_show in linux/arch/arm/kernel/setup.c
            k, _, v = x.partition(':')
            cpuinfo[k.strip()] = v.strip()
        # Is this a... Raspberry Pi?
        if cpuinfo['Hardware'] in ('BCM2708', 'BCM2835'):
            btype = 'Raspberry Pi'
        # Is this a... BeagleBone Black?
        elif 'Generic AM33XX' in cpuinfo['Hardware'] and cpuinfo['CPU part'] == '0xc08':
            btype = 'BeagleBone Black'
        # Is this a Cubieboard (series)?
        elif cpuinfo['Hardware'] == 'sun7i' and cpuinfo['CPU part'] == '0xc07':
            meminfo = {}
            # Since both the Cubieboard2 and Cubietruck have the same processor,
            # we need to check memory size to make a good guess.
            for x in shell('cat /proc/meminfo').split('\n'):
                k, _, v = x.partition(':')
                meminfo[k.strip()] = v.strip()
            # Is this a... Cubieboard2?
            if int(meminfo['MemTotal'].split(' ')[0]) < 1100000:
                btype = 'Cubieboard2'
            # Then it must be a Cubietruck!
            else:
                btype = 'Cubietruck'
    return (arch, btype)

def detect_platform(mapping=True):
    """
    Returns a text shortname of the current system platform.

    :param  mapping:    if True, map Ubuntu to Debian and so on.
    :type   mapping:    bool
    :rtype:             str
    """
    base_mapping = {
        'gentoo base system': 'gentoo',
        'centos linux': 'centos',
        'mandriva linux': 'mandriva',
    }

    platform_mapping = {
        'ubuntu': 'debian',
        'linuxmint': 'debian',
    }

    if platform.system() != 'Linux':
        return platform.system().lower()

    dist = ''
    (maj, min, patch) = platform.python_version_tuple()
    if (maj * 10 + min) >= 26:
        dist = platform.linux_distribution()[0]
    else:
        dist = platform.dist()[0]

    if dist == '':
        try:
            dist = shell('strings -4 /etc/issue').split()[0]
        except:
            dist = 'unknown'

    res = dist.strip().lower()
    if res in base_mapping:
        res = base_mapping[res]
    if mapping:
        if res in platform_mapping:
            res = platform_mapping[res]
    return res

def detect_distro():
    """
    Returns human-friendly OS name.
    """
    if shell_status('lsb_release -sd') == 0:
        return shell('lsb_release -sd').replace('"', '')
    return shell('uname -mrs')

def download(url, file=None, crit=False):
    """
    Downloads data from an URL

    :param  file:   file path to save data into. If None, returns data as string
    :param  crit:   if False, exceptions will be swallowed
    :rtype:         None or str
    """
    try:
        data = urllib2.urlopen(url).read()
        if file:
            open(file, 'w').write(data)
        else:
            return data
    except Exception, e:
        if crit:
            raise

def shell(c, stderr=False, env={}):
    """
    Runs commandline in the default shell and returns output. Blocking.
    """
    p = subprocess.Popen('LC_ALL=C '+c, shell=True,
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE,
            env=env if env else None)

    try:
        data = p.stdout.read() # Workaround; waiting first causes a deadlock
    except: # WTF OSError (interrupted request)
        data = ''
    p.wait()
    return data + p.stdout.read() + (p.stderr.read() if stderr else '')

def shell_bg(c, output=None, deleteout=False):
    """
    Same, but runs in background. For controlled execution, see
    :class:BackgroundProcess.

    :param  output:     if not None, saves output in this file
    :type   output:     str
    :param  deleteout:  if True, will delete output file upon completion
    :type   deleteout:  bool
    """
    if output is not None:
        c = 'LC_ALL=C bash -c "%s" > %s 2>&1'%(c,output)
        if deleteout:
            c = 'touch %s; %s; rm -f %s'%(output,c,output)
    subprocess.Popen(c, shell=True,
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE)

def shell_status(c):
    """
    Same, but returns only the exitcode.
    """
    return subprocess.Popen('LC_ALL=C '+c, shell=True,
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE).wait()

def shell_cs(c, stderr=False, env={}):
    """
    Same, but returns exitcode and output in a tuple.
    """
    p = subprocess.Popen('LC_ALL=C '+c, shell=True,
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE,
            env=env if env else None)

    try:
        data = p.stdout.read() # Workaround; waiting first causes a deadlock
    except: # WTF OSError (interrupted request)
        data = ''
    p.wait()
    return (p.returncode, data + p.stdout.read() + (p.stderr.read() if stderr else ''))

def shell_stdin(c, input):
    """
    Same, but feeds input to process' stdin and returns its stdout
    upon completion.
    """
    p = subprocess.Popen('LC_ALL=C '+c, shell=True,
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stdin=subprocess.PIPE)
    return p.communicate(input)


def hashpw(passw, scheme = 'sha512_crypt'):
    """
    Returns a hashed form of given password. Default scheme is
    sha512_crypt. Accepted schemes: sha512_crypt, bcrypt, sha (deprecated)
    """
    if scheme == 'sha512_crypt':
        return sha512_crypt.encrypt(passw)
    elif scheme == 'bcrypt':
        # TODO: rounds should be configurable
        return bcrypt.encrypt(passw, rounds=12)
    elif scheme == 'ssha':
        salt = os.urandom(32)
        return '{SSHA}' + b64encode(sha1(passw + salt).digest() + salt)
    # This scheme should probably be dropped to avoid creating new
    # unsaltes SHA1 hashes.
    elif scheme == 'sha':
        import warnings
        warnings.warn(
            'SHA1 as a password hash may be removed in a future release.')
        return '{SHA}' + b64encode(sha1(passw).digest())
    return sha512_crypt.encrypt(passw)


def can_be_int(data):
    try: 
        int(data)
        return True
    except ValueError:
        return False


def str_fsize(sz):
    """
    Formats file size as string (1.2 Mb)
    """
    if sz < 1024:
        return '%.1f bytes' % sz
    sz /= 1024.0
    if sz < 1024:
        return '%.1f Kb' % sz
    sz /= 1024.0
    if sz < 1024:
        return '%.1f Mb' % sz
    sz /= 1024.0
    return '%.1f Gb' % sz

def wsgi_serve_file(req, start_response, file):
    """
    Serves a file as WSGI reponse.
    """
    # Check for directory traversal
    if file.find('..') > -1:
        start_response('404 Not Found', [])
        return ''

    # Check if this is a file
    if not os.path.isfile(file):
        start_response('404 Not Found',[])
        return ''

    headers = []
    # Check if we have any known file type
    # For faster response, check for known types:
    content_type = 'application/octet-stream'
    if file.endswith('.css'):
        content_type = 'text/css'
    elif file.endswith('.less'):
        content_type = 'text/css'
    elif file.endswith('.js'):
        content_type = 'application/javascript'
    elif file.endswith('.png'):
        content_type = 'image/png'
    else:
        (mimetype, encoding) = mimetypes.guess_type(file)
        if mimetype is not None:
            content_type = mimetype
    headers.append(('Content-type',content_type))

    size = os.path.getsize(file)
    mtimestamp = os.path.getmtime(file)
    mtime = datetime.utcfromtimestamp(mtimestamp)

    rtime = req.get('HTTP_IF_MODIFIED_SINCE', None)
    if rtime is not None:
        try:
            rtime = datetime.strptime(rtime, '%a, %b %d %Y %H:%M:%S GMT')
            if mtime <= rtime:
                start_response('304 Not Modified',[])
                return ''
        except:
            pass

    headers.append(('Content-length',str(size)))
    headers.append(('Last-modified',mtime.strftime('%a, %b %d %Y %H:%M:%S GMT')))
    start_response('200 OK', headers)
    return open(file).read()

########NEW FILE########
__FILENAME__ = make_plugin_info
#!/usr/bin/env python
import os
import commands

def shell(s):
    commands.getstatusoutput(s)

shell('mkdir meta/plugins -p')
for s in os.listdir('../plugins'):
    print '> '+s
    shell('mkdir meta/plugins/'+s)
    shell('cp ../plugins/%s/__init__.py meta/plugins/%s'%(s,s))
    shell('cp ../plugins/%s/files/icon.png meta/plugins/%s'%(s,s))
    shell('cd ../plugins; tar -cz %s > plugin.tar.gz'%s)
    shell('mv ../plugins/plugin.tar.gz meta/plugins/%s'%s)
    

########NEW FILE########
__FILENAME__ = backend
from subprocess import *

from genesis.api import *
from genesis.com import *
from genesis.utils import *


class User:
    login = ''
    uid = 0
    gid = 0
    home = ''
    shell = ''
    info = ''
    groups = []


class Group:
    name = ''
    gid = 0
    users = []


class SysUsersBackend(Plugin):
    iconfont = 'gen-users'

    def __init__(self):
        self.cfg = self.app.get_config(self)

    def get_all_users(self):
        r = []
        for s in open('/etc/passwd', 'r').read().split('\n'):
            try:
                s = s.split(':')
                u = User()
                u.login = s[0]
                u.uid = int(s[2])
                u.gid = int(s[3])
                u.info = s[4]
                u.home = s[5]
                u.shell = s[6]
                r.append(u)
            except:
                pass

        sf = lambda x: -1 if x.uid==0 else (x.uid+1000 if x.uid<1000 else x.uid-1000)
        return sorted(r, key=sf)

    def get_all_groups(self):
        r = []
        for s in open('/etc/group', 'r').read().split('\n'):
            try:
                s = s.split(':')
                g = Group()
                g.name = s[0]
                g.gid = s[2]
                g.users = s[3].split(',')
                r.append(g)
            except:
                pass

        return r

    def map_groups(self, users, groups):
        for u in users:
            u.groups = []
            for g in groups:
                if u.login in g.users:
                    u.groups.append(g.name)

    def get_user(self, name, users):
        return filter(lambda x:x.login == name, users)[0]

    def get_group(self, name, groups):
        return filter(lambda x:x.name == name, groups)[0]

    def add_user(self, v):
        shell(self.cfg.cmd_add.format(v))

    def add_group(self, v):
        shell(self.cfg.cmd_add_group.format(v))

    def del_user(self, v):
        shell(self.cfg.cmd_del.format(v))

    def del_group(self, v):
        shell(self.cfg.cmd_del_group.format(v))

    def add_to_group(self, u, v):
        shell(self.cfg.cmd_add_to_group.format(u,v))

    def remove_from_group(self, u, v):
        shell(self.cfg.cmd_remove_from_group.format(u,v))

    def change_user_param(self, u, p, l):
        shell(getattr(self.cfg, 'cmd_set_user_'+p).format(l,u))

    def change_user_password(self, u, l):
        shell_stdin('passwd ' + u, '%s\n%s\n' % (l,l))

    def change_group_param(self, u, p, l):
        shell(getattr(self.cfg, 'cmd_set_group_'+p).format(l,u))


class LinuxConfig(ModuleConfig):
    target = SysUsersBackend
    platform = ['debian', 'arch', 'arkos', 'fedora', 'centos', 'gentoo', 'mandriva']

    cmd_add = 'useradd {0}'
    cmd_del = 'userdel {0}'
    cmd_add_group = 'groupadd {0}'
    cmd_del_group = 'groupdel {0}'
    cmd_set_user_login = 'usermod -l {0} {1}'
    cmd_set_user_uid = 'usermod -u {0} {1}'
    cmd_set_user_gid = 'usermod -g {0} {1}'
    cmd_set_user_shell = 'usermod -s {0} {1}'
    cmd_set_user_home = 'usermod -h {0} {1}'
    cmd_set_group_gname = 'groupmod -n {0} {1}'
    cmd_set_group_ggid = 'groupmod -g {0} {1}'
    cmd_add_to_group = 'adduser {0} {1}'
    cmd_remove_from_group = 'deluser {0} {1}'


class BSDConfig(ModuleConfig):
    target = SysUsersBackend
    platform = ['freebsd']

    cmd_add = 'pw useradd {0}'
    cmd_del = 'pw userdel {0}'
    cmd_add_group = 'pw groupadd {0}'
    cmd_del_group = 'pw groupdel {0}'
    cmd_set_user_login = 'pw usermod {1} -l {0}'
    cmd_set_user_uid = 'pw usermod {1} -u {0}'
    cmd_set_user_gid = 'pw usermod {1} -g {0}'
    cmd_set_user_shell = 'pw usermod {1} -s {0}'
    cmd_set_user_home = 'pw usermod {1} -h {0}'
    cmd_set_group_gname = 'pw groupmod {1} -n {0}'
    cmd_set_group_ggid = 'pw groupmod {1} -g {0}'
    cmd_add_to_group = 'pw groupmod {1} -m {0}'
    cmd_remove_from_group = 'pw groupmod {1} -d {0}'

########NEW FILE########
__FILENAME__ = main
import re

from genesis.ui import *
from genesis.com import implements
from genesis.api import *
from genesis.utils import *

from backend import *


class SysUsersPlugin(CategoryPlugin):
    text = 'System Users'
    iconfont = 'gen-users'
    folder = 'advanced'

    params = {
            'login': 'Login',
            'password': 'Password',
            'name': 'Name',
            'uid': 'UID',
            'gid': 'GID',
            'home': 'Home directory',
            'shell': 'Shell',
            'groups': 'Groups',
            'adduser': 'New user login',
            'addgrp': 'New group name',
            'addtogroup': 'Add to group',
            'delfromgroup': 'Delete from group',
        }

    gparams = {
            'gname': 'Name',
            'ggid': 'GID',
        }

    def on_init(self):
        self.backend = SysUsersBackend(self.app)
        self.users = self.backend.get_all_users()
        self.groups = self.backend.get_all_groups()
        self.backend.map_groups(self.users, self.groups)

    def reload_data(self):
        self.users = self.backend.get_all_users()
        self.groups = self.backend.get_all_groups()
        self.backend.map_groups(self.users, self.groups)

    def get_config(self):
        return self.app.get_config(self.backend)

    def on_session_start(self):
        self._tab = 0
        self._selected_user = ''
        self._selected_group = ''
        self._editing = ''

    def get_ui(self):
        self.reload_data()
        ui = self.app.inflate('advusers:main')
        ui.find('tabs').set('active', self._tab)

        if self._editing != '':
            if self._editing in self.params:
                ui.find('dlgEdit').set('text', self.params[self._editing])
            else:
                ui.find('dlgEdit').set('text', self.gparams[self._editing])
        else:
            ui.remove('dlgEdit')

        # Users
        t = ui.find('userlist')

        for u in self.users:
            t.append(UI.DTR(
                    UI.IconFont(iconfont='gen-user'),
                    UI.Label(text=u.login, bold=True),
                    UI.Label(text=u.uid, bold=(u.uid>=1000)),
                    UI.Label(text=u.home),
                    UI.Label(text=u.shell),
                    UI.TipIcon(iconfont='gen-pencil-2', id='edit/'+u.login, text='Edit'),
                ))

        if self._selected_user != '':
            u = self.backend.get_user(self._selected_user, self.users)
            self.backend.map_groups([u], self.backend.get_all_groups())

            ui.find('elogin').set('value', u.login)
            ui.find('deluser').set('warning', 'Delete user %s'%u.login)
            ui.find('euid').set('value', str(u.uid))
            ui.find('egid').set('value', str(u.gid))
            ui.find('ehome').set('value', u.home)
            ui.find('eshell').set('value', u.shell)
            ui.find('lblugroups').set('text', ', '.join(u.groups))
        else:
            ui.remove('dlgEditUser')


        # Groups
        t = ui.find('grouplist')

        for u in self.groups:
            t.append(UI.DTR(
                    UI.IconFont(iconfont='gen-users'),
                    UI.Label(text=u.name, bold=True),
                    UI.Label(text=u.gid, bold=(u.gid>=1000)),
                    UI.Label(text=', '.join(u.users)),
                    UI.TipIcon(iconfont='gen-pencil-2', id='gedit/'+u.name, text='Edit'),
                ))

        if self._selected_group != '':
            u = self.backend.get_group(self._selected_group, self.groups)
            g = ', '.join(u.users)

            ui.find('ename').set('value', u.name)
            ui.find('delgroup').set('warning', 'Delete group %s'%u.name)
            ui.find('eggid').set('value', str(u.gid))
            ui.find('lblgusers').set('text', g)
        else:
            ui.remove('dlgEditGroup')

        return ui

    @event('button/click')
    def on_click(self, event, params, vars=None):
        if params[0] == 'edit':
            self._tab = 0
            self._selected_user = params[1]
        if params[0] == 'gedit':
            self._tab = 1
            self._selected_group = params[1]
        if params[0].startswith('ch'):
            self._tab = 0
            self._editing = params[0][2:]
        if params[0] == 'adduser':
            self._tab = 0
            self._editing = 'adduser'
        if params[0] == 'addgrp':
            self._tab = 1
            self._editing = 'addgrp'
        if params[0] == 'deluser':
            self._tab = 0
            self.backend.del_user(self._selected_user)
            try:
                self.app.gconfig.remove_option('users', self._selected_user)
                self.app.gconfig.save()
            except:
                pass
            self._selected_user = ''
        if params[0] == 'delgroup':
            self._tab = 1
            self.backend.del_group(self._selected_group)
            self._selected_group = ''

    @event('dialog/submit')
    @event('form/submit')
    def on_submit(self, event, params, vars=None):
        if params[0] == 'dlgEdit':
            v = vars.getvalue('value', '')
            if vars.getvalue('action', '') == 'OK':
                if self._editing == 'adduser':
                    if re.search('[A-Z]|\.|:|[ ]|-$', v):
                        self.put_message('err', 'Username must not contain capital letters, dots, colons, spaces, or end with a hyphen')
                        self._editing = ''
                        return
                    self.reload_data()
                    for u in self.users:
                        if u.login == v:
                            self.put_message('err', 'Duplicate name')
                            self._editing = ''
                            return
                    self.app.gconfig.set('users', v, '')
                    self.app.gconfig.save()
                    self.backend.add_user(v)
                    self._selected_user = v
                elif self._editing == 'addgrp':
                    self.reload_data()
                    for u in self.groups:
                        if u.name == v:
                            self.put_message('err', 'Duplicate name')
                            self._editing = ''
                            return
                    self.backend.add_group(v)
                    self._selected_group = v
                elif self._editing == 'addtogroup':
                    self.backend.add_to_group(self._selected_user, v)
                elif self._editing == 'delfromgroup':
                    self.backend.remove_from_group(self._selected_user, v)
            self._editing = ''
        if params[0].startswith('e'):
            v = vars.getvalue('value', '')
            if params[0] == 'epassword':
                self.backend.change_user_password(self._selected_user, v)
                self.app.gconfig.set('users', self._selected_user, hashpw(v))
            elif params[0] == 'elogin':
                self.backend.change_user_param(self._selected_user, 'login', v)
                pw = self.app.gconfig.get('users', self._selected_user, '')
                self.app.gconfig.remove_option('users', self._selected_user)
                self.app.gconfig.set('users', v, pw)
                self._selected_user = v
            elif params[0] in self.params:
                self.backend.change_user_param(self._selected_user, params[0][:1], v)
            elif params[0] in self.gparams:
                self.backend.change_group_param(self._selected_group, params[0][:1], v)
            self.app.gconfig.save()
            self._editing = None
        if params[0] == 'dlgEditUser':
            self._selected_user = ''
        if params[0] == 'dlgEditGroup':
            self._selected_group = ''

########NEW FILE########
__FILENAME__ = main
from genesis.api import *
from genesis.ui import *
from genesis.com import Plugin, Interface, implements
from genesis import apis
from genesis.utils import shell

import os
import nginx


class Website(Plugin):
    implements(apis.webapps.IWebapp)

    addtoblock = []

    phpblock = [
        nginx.Location('~ ^(.+?\.php)(/.*)?$',
            nginx.Key('include', 'fastcgi_params'),
            nginx.Key('fastcgi_param', 'SCRIPT_FILENAME $document_root$1'),
            nginx.Key('fastcgi_param', 'PATH_INFO $2'),
            nginx.Key('fastcgi_pass', 'unix:/run/php-fpm/php-fpm.sock'),
            nginx.Key('fastcgi_read_timeout', '900s'),
            )
        ]

    def pre_install(self, name, vars):
        if vars.getvalue('ws-dbsel', 'None') == 'None':
            if vars.getvalue('ws-dbname', '') != '':
                raise Exception('Must choose a database type if you want to create one')
            elif vars.getvalue('ws-dbpass', '') != '':
                raise Exception('Must choose a database type if you want to create one')
        if vars.getvalue('ws-dbsel', 'None') != 'None':
            if vars.getvalue('ws-dbname', '') == '':
                raise Exception('Must choose a database name if you want to create one')
            elif vars.getvalue('ws-dbpass', '') == '':
                raise Exception('Must choose a database password if you want to create one')
            elif ' ' in vars.getvalue('ws-dbname') or '-' in vars.getvalue('ws-dbname'):
                raise Exception('Database name must not contain spaces or dashes')
            elif vars.getvalue('ws-dbname') > 16 and vars.getvalue('ws-dbsel') == 'MariaDB':
                raise Exception('Database name must be shorter than 16 characters')

    def post_install(self, name, path, vars):
        # Write a basic index file showing that we are here
        if vars.getvalue('php', '0') == '1':
            php = True
            path = os.path.join(path, 'htdocs')
            os.mkdir(path)
            c = nginx.loadf(os.path.join('/etc/nginx/sites-available', name))
            for x in c.servers:
                if x.filter('Key', 'root'):
                    x.filter('Key', 'root')[0].value = path
            nginx.dumpf(c, os.path.join('/etc/nginx/sites-available', name))
        else:
            php = False
            
        # Create a database if the user wants one
        if php:
            phpctl = apis.langassist(self.app).get_interface('PHP')
        if vars.getvalue('ws-dbsel', 'None') != 'None':
            dbtype = vars.getvalue('ws-dbsel', '')
            dbname = vars.getvalue('ws-dbname', '')
            passwd = vars.getvalue('ws-dbpass', '')
            dbase = apis.databases(self.app).get_interface(dbtype)
            if hasattr(dbase, 'connect'):
                conn = apis.databases(self.app).get_dbconn(dbtype)
                dbase.add(dbname, conn)
                dbase.usermod(dbname, 'add', passwd, conn)
                dbase.chperm(dbname, dbname, 'grant', conn)
            else:
                dbase.add(dbname)
                dbase.usermod(dbname, 'add', passwd)
                dbase.chperm(dbname, dbname, 'grant')
            if php:
                phpctl.enable_mod('mysql')

        f = open(os.path.join(path, 'index.'+('php' if php is True else 'html')), 'w')
        f.write(
            '<html>\n'
            '<body>\n'
            '<h1>Genesis - Custom Site</h1>\n'
            '<p>Your site is online and available at '+path+'</p>\n'
            '<p>Feel free to paste your site files here</p>\n'
            '</body>\n'
            '</html>\n'
            )
        f.close()

        # Give access to httpd
        shell('chown -R http:http '+path)

        # Enable xcache if PHP is set
        if php:
            phpctl.enable_mod('xcache')

    def pre_remove(self, name, path):
        pass

    def post_remove(self, name):
        pass

    def ssl_enable(self, path, cfile, kfile):
        pass

    def ssl_disable(self, path):
        pass

    def show_opts_add(self, ui):
        type_sel = [UI.SelectOption(text='None', value='None')]
        for x in sorted(apis.databases(self.app).get_dbtypes()):
            type_sel.append(UI.SelectOption(text=x[0], value=x[0]))
        ui.appendAll('ws-dbsel', *type_sel)

########NEW FILE########
__FILENAME__ = backend
"""
This module provide an interface for working with crontab.
It's using shell command 'crontab' and donn't change file manualy
"""
from genesis.api import IConfigurable
from genesis.com import Plugin, implements
from genesis.utils import shell, shell_stdin


class Task():
    """Class to represent the task in crontab"""
    def __init__(self, line=''):
        if not line:
            self.m, self.h, self.dom, self.mon, self.dow = ['*'] * 5
            self.command = ''
            self.special = ''
        elif line[0] == '@':
            tlist = line.split()
            if tlist[0] == '@annually':
                self.special = '@yearly'
            elif tlist[0] == '@midnight':
                self.special = '@hourly'
            else:
                self.special = tlist[0]
            self.command = ' '.join(tlist[1:])\
                                if tlist[1] else ''
        else:
            params = line.split()
            self.m, self.h, self.dom, self.mon, self.dow = params[:5]
            self.command = ' '.join(params[5:])
            self.special = ''

    def __repr__(self):
        """task in string for write in crontab"""
        if self.special:
            string = self.special + '\t' + self.command
        else:
            string = ' '.join((self.m, self.h, self.dom, self.mon,
                          self.dow)) + '\t' + self.command
        return string


def read_crontab(user='root'):
    """Read crontab file with shell command 'crontab -l'"""
    tasks = []
    others = []
    lines = shell('crontab -l -u ' + user).split('\n')
    for line in lines:
        if not line:
            continue
        if line.startswith('no'):
            continue
        if line[0] == '#':
            others.append(line)
            continue
        try:
            tasks.append(Task(line))
        except ValueError:
            others.append(line)
            continue
    return tasks, others

def write_crontab(tasks, user='root'):
    """
    Write tasks to crontab file with shell command and stdin.
    tasks - list of instance Task class or string.
    """
    lines = '\n'.join([str(task) for task in tasks])
    lines += '\n'
    return shell_stdin('crontab - -u ' + user, lines)[1]

def fix_crontab(user='root'):
    """
    Read and comment wrong for crontab string.
    """
    cron_lines = filter(None, shell('crontab -l -u ' + user).split('\n'))
    fixed_lines = []
    for line in cron_lines:
        if shell_stdin('crontab - -u ' + user, line + '\n')[1]:
            fixed_lines.append('#' + line)
        else:
            fixed_lines.append(line)
    write_crontab(fixed_lines, user)
    return 0

def get_all_users():
    user_list = []
    for s in open('/etc/passwd', 'r').read().split('\n'):
        try:
            s = s.split(':')
            u = s[0]
            user_list.append(u)
        except:
            pass
    return sorted(user_list)
    
    
class CronConfig (Plugin):
    implements(IConfigurable)
    name = 'Cron'
    id = 'cron'
    
    def list_files(self):
        return ['/var/spool/cron/*/*']
        

########NEW FILE########
__FILENAME__ = main
from genesis.ui import UI
from genesis.api import event, helpers, ConfManager
from genesis.utils import shell

import backend

class CronPlugin(helpers.CategoryPlugin):
    text = 'Scheduled Tasks'
    iconfont = 'gen-alarm'
    folder = 'system'

    def on_init(self):
        self._tasks, self._others = backend.read_crontab(self._user)

    def on_session_start(self):
        self._user = shell('whoami').strip()
        backend.fix_crontab(self._user)
        self._labeltext = ''
        self._editing_task = -1
        self._editing_other = -1
        self._error = ''
        self._tasks = []
        self._others = []
        self._tab = 0
        self._show_dialog = 0
        self._show_dialog_user = 0
        self._newtask = False

    def get_ui(self):
        ui = self.app.inflate('cron:main')
        ui.find('tabs').set('active', self._tab)
        ui.find('title').set('text','Scheduled tasks for %s' % self._user)
        user_sel = [UI.SelectOption(text = x, value = x,
                    selected = True if x == self._user else False)
                    for x in backend.get_all_users()]
        ui.appendAll('users_select', *user_sel)

        table_other = ui.find("table_other")
        table_task = ui.find("table_task")
        #Fill non-task strings table
        for i, oth_str in enumerate(self._others):
            table_other.append(UI.DTR(
                    UI.Label(text=oth_str),
                    UI.DTD(
                        UI.HContainer(
                            UI.TipIcon(iconfont='gen-pencil-2', id='edit_oth/' + str(i),
                                text='Edit'),
                            UI.TipIcon(iconfont='gen-cancel-circle', id='del_oth/' + str(i),
                                text='Delete', warning='Delete a string')
                        ),
                        hidden=True)
                    ))
        #Fill tasks table
        for i, t in enumerate(self._tasks):
            table_task.append(UI.DTR(
                    UI.Label(text=t.special if t.special else t.m),
                    UI.Label(text=t.h   if not t.special else ''),
                    UI.Label(text=t.dom if not t.special else ''),
                    UI.Label(text=t.mon if not t.special else ''),
                    UI.Label(text=t.dow if not t.special else ''),
                    UI.Label(text=t.command),
                    UI.DTD(
                        UI.HContainer(
                            UI.TipIcon(iconfont='gen-pencil-2', id='edit_task/' + str(i),
                                text='Edit'),
                            UI.TipIcon(iconfont='gen-cancel-circle', id='del_task/' + str(i),
                                text='Delete', warning='Delete a task')
                        ),
                    )))
        #if crontab return error
        part = self._error.partition(':')[2]
        self._error = 'Error:' + part if part else self._error
        if self._error:
            self.put_message('err', self._error)

        #For tabs name
        REGULARTAB = 11
        ADVANCEDTAB = 12
        SPECIALTAB = 13
        #special values
        avaible_values = ('@reboot', '@hourly', '@daily',
                            '@weekly', '@monthly', '@yearly')
        #edit or new task
        if self._editing_task != -1:
            try:
                task = self._tasks[self._editing_task]
            except IndexError:
                task = backend.Task()
            #edit task
            if not self._newtask:
                ui.remove(str(REGULARTAB))
                if task.special:
                    ui.remove(str(ADVANCEDTAB))
                    ui.find('tabsEdit').set('active', SPECIALTAB)
                    #select special values
                    if task.special and task.special in avaible_values:
                        ui.find('r' + task.special[1:]).\
                            set('checked', 'True')
                    else:
                        ui.find('rreboot').set('checked', 'True')
                    ui.find('s_command').set("value", task.command)
                else:
                    #fill advanced view task
                    ui.find('tabsEdit').set('active', ADVANCEDTAB)
                    ui.remove(str(SPECIALTAB))
                    ui.find('m').set("value", task.m)
                    ui.find('h').set("value", task.h)
                    ui.find('dom').set("value", task.dom)
                    ui.find('mon').set("value", task.mon)
                    ui.find('dow').set("value", task.dow)
                    ui.find('a_command').set("value", task.command)
            #new task
            else:
                ui.find('tabsEdit').set('active', REGULARTAB)
                ui.find('rreboot').set('checked', 'True')
                ui.find('m').set("value", task.m)
                ui.find('h').set("value", task.h)
                ui.find('dom').set("value", task.dom)
                ui.find('mon').set("value", task.mon)
                ui.find('dow').set("value", task.dow)
                #For templates
                ui.find('tabsRegular').set('active', 15)
                SelectOptionNumbs = lambda r: [UI.SelectOption(text=str(m), value=str(m))
                                    for m in xrange(r)]
                #generate similar selectOptions lists for xml.
                minute_select_h = SelectOptionNumbs(60)
                minute_select_d = SelectOptionNumbs(60)
                minute_select_w = SelectOptionNumbs(60)
                minute_select_m = SelectOptionNumbs(60)
                hour_select_d = SelectOptionNumbs(24)
                hour_select_w = SelectOptionNumbs(24)
                hour_select_m = SelectOptionNumbs(24)

                weekday = ('Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday',
                    'Saturday', 'Sunday')
                weekday_select = [UI.SelectOption(text=str(w), value=str(v+1))
                        for v, w in enumerate(weekday)]
                day_select = [UI.SelectOption(text=str(d), value=str(d))
                        for d in range(1, 32)]
                #Fill selects
                ui.appendAll("minute_select_h", *minute_select_h)
                ui.appendAll("minute_select_d", *minute_select_d)
                ui.appendAll("minute_select_w", *minute_select_w)
                ui.appendAll("minute_select_m", *minute_select_m)
                ui.appendAll("hour_select_d", *hour_select_d)
                ui.appendAll("hour_select_w", *hour_select_w)
                ui.appendAll("hour_select_m", *hour_select_m)
                ui.appendAll("weekday_select", *weekday_select)
                ui.appendAll("day_select", *day_select)
        #Nothing happens with task
        else:
            ui.remove('dlgEditTask')
        #edit non-task string
        if self._editing_other != -1 and self._show_dialog:
            other_value = self._others[self._editing_other]\
                if self._editing_other < len(self._others) else ''
            ui.find("other_str").set("value", other_value)
        #Nothing happens with non-task string
        else:
            ui.remove('dlgEditOther')
        return ui


    @event('button/click')
    @event('linklabel/click')
    def on_click(self, event, params, vars=None):
        "Actions on buttons"
        if params[0] == 'add_task':
            self._editing_task = len(self._tasks)
            self._show_dialog = 1
            self._newtask = True
        if params[0] == 'edit_task':
            self._editing_task = int(params[1])
            self._show_dialog = 1
        if params[0] == 'del_task':
            self._tasks.pop(int(params[1]))
            self._error = backend.write_crontab(self._others + self._tasks,
                                                self._user)
        if params[0] == 'add_oth':
            self._editing_other = len(self._others)
            self._show_dialog = 1
        if params[0] == 'edit_oth':
            self._editing_other = int(params[1])
            self._show_dialog = 1
        if params[0] == 'del_oth':
            self._others.pop(int(params[1]))
            self._error = backend.write_crontab(self._others + self._tasks,
                                                self._user)
            self._tab = 1


    @event('form/submit')
    def on_submit_form(self, event, params, vars=None):
        "For user select or Regular and advanced Task"
        if params[0] == 'frmUser':
            self._user = vars.getvalue('users_select') or 'root'
            backend.fix_crontab(self._user)
            self._tasks, self._others = backend.read_crontab(self._user)
            return 0
        if params[0] == 'frmAdvanced' and\
                vars.getvalue('action') == 'OK':
            task_str = ' '.join((
                        vars.getvalue('m').replace(' ', '') or '*',
                        vars.getvalue('h').replace(' ', '') or '*',
                        vars.getvalue('dom').replace(' ', '') or '*',
                        vars.getvalue('mon').replace(' ', '') or '*',
                        vars.getvalue('dow').replace(' ', '') or '*'
                        ))
            task_str += '\t' + vars.getvalue('a_command')
            if self.set_task(task_str):
                return 1
        elif params[0] == 'frmSpecial' and\
                vars.getvalue('action') == 'OK':
            task_str = '@' + vars.getvalue('special')
            task_str += '\t' + vars.getvalue('s_command')
            if self.set_task(task_str):
                return 1
        elif params[0] == 'frmTempMinutes' and\
                vars.getvalue('action') == 'OK':
            task_str = '*/' + (vars.getvalue('minutes') or '1')
            task_str += ' * * * *'
            task_str += '\t' + vars.getvalue('command')
            if self.set_task(task_str):
                return 1
        elif params[0] == 'frmTempHours' and\
                vars.getvalue('action') == 'OK':
            task_str = vars.getvalue('minute_select_h') + ' '
            task_str += '*/' + (vars.getvalue('hours')  or '1')
            task_str += ' * * *'
            task_str += '\t' + vars.getvalue('command')
            if self.set_task(task_str):
                return 1
        elif params[0] == 'frmTempDays' and\
                vars.getvalue('action') == 'OK':
            task_str = vars.getvalue('minute_select_d') + ' '
            task_str += vars.getvalue('hour_select_d') + ' '
            task_str += '*/' + (vars.getvalue('days')  or '1')
            task_str += ' * *'
            task_str += '\t' + vars.getvalue('command')
            if self.set_task(task_str):
                return 1
        elif params[0] == 'frmTempMonths' and\
                vars.getvalue('action') == 'OK':
            task_str = vars.getvalue('minute_select_m') + ' '
            task_str += vars.getvalue('hour_select_m') + ' '
            task_str += vars.getvalue('day_select') + ' '
            task_str += '*/' + (vars.getvalue('months')  or '1')
            task_str += ' *'
            task_str += '\t' + vars.getvalue('command')
            if self.set_task(task_str):
                return 1
        elif params[0] == 'frmTempWeek' and\
                vars.getvalue('action') == 'OK':
            task_str = vars.getvalue('minute_select_w') + ' '
            task_str += vars.getvalue('hour_select_w') + ' '
            task_str += '* * '
            task_str += vars.getvalue('weekday_select')
            task_str += '\t' + vars.getvalue('command')
            if self.set_task(task_str):
                return 1
        self._show_dialog = 0
        self._editing_task = -1
        self._newtask = False
        self._tab = 0

    def set_task(self, task_str):
        "Set new or edited task"
        #noinspection PyBroadException
        try:
            new_task = backend.Task(task_str)
        except:
            self._error = 'Error: Wrong options.'
            self._editing_task = -1
            return 1
        if self._editing_task < len(self._tasks):
            self._tasks[self._editing_task] = new_task
        else:
            self._tasks.append(new_task)
        self._error = backend.write_crontab(self._others + self._tasks,
                                            self._user)
        if self._error:
            self._tasks, self._others = backend.read_crontab()
        ConfManager.get().commit('cron')
        return 0


    @event('dialog/submit')
    def on_submit_dlg(self, event, params, vars=None):
        " for submit non-task string. It is use dialog"
        if params[0] == 'dlgEditOther':
            if vars.getvalue('action') == 'OK':
                if self._editing_other < len(self._others):
                    self._others[self._editing_other] = vars.getvalue('other_str')
                else:
                    self._others.append(vars.getvalue('other_str'))
                self._error = backend.write_crontab(self._others + self._tasks,
                                                    self._user)
                if self._error:
                    self._tasks, self._others = backend.read_crontab()
            self._show_dialog = 0
            self._editing_other = -1
            self._tab = 1

########NEW FILE########
__FILENAME__ = main
from genesis.api import *
from genesis.ui import *
from genesis.com import Plugin, Interface, implements
from genesis import apis
from genesis.utils import *
from genesis.plugins.databases.utils import *

import re
import _mysql
import _mysql_exceptions


class MariaDB(Plugin):
    implements(apis.databases.IDatabase)
    db = None

    def connect(self, store, user='root', passwd='', db=None):
        if db:
            self.db = _mysql.connect('localhost', user, passwd, db)
            store[self.plugin_info.db_name] = self.db
        else:
            try:
                self.db = _mysql.connect('localhost', user, passwd)
            except _mysql_exceptions.OperationalError:
                raise DBAuthFail(self.plugin_info.db_name)
            store[self.plugin_info.db_name] = self.db

    def checkpwstat(self):
        try:
            _mysql.connect('localhost', 'root', '')
            return False
        except:
            return True

    def chpwstat(self, newpasswd, conn=None):
        if not self.db and conn:
            self.db = conn
        self.db.query('USE mysql')
        self.db.query('UPDATE user SET password=PASSWORD("'+newpasswd+'") WHERE User=\'root\'')
        self.db.query('FLUSH PRIVILEGES')

    def validate(self, name='', user='', passwd='', conn=None):
        if not self.db and conn:
            self.db = conn
        if name and re.search('\.|-|`|\\\\|\/|^test$|[ ]', name):
            raise Exception('Database name must not contain spaces, dots, dashes or other special characters')
        elif name and len(name) > 16:
            raise Exception('Database name must be shorter than 16 characters')
        if user and re.search('\.|-|`|\\\\|\/|^test$|[ ]', user):
            raise Exception('Database username must not contain spaces, dots, dashes or other special characters')
        elif user and len(user) > 16:
            raise Exception('Database username must be shorter than 16 characters')
        if passwd and len(passwd) < 8:
            raise Exception('Database password must be longer than 8 characters')
        if name:
            for x in self.get_dbs(self.db):
                if x['name'] == name:
                    raise Exception('You already have a database named %s - please remove that one or choose a new name!' % name)
        if user:
            for x in self.get_users(self.db):
                if x['name'] == user:
                    raise Exception('You already have a database user named %s - please remove that one or choose a new name!' % user)
        return True

    def add(self, dbname, conn=None):
        if not self.db and conn:
            self.db = conn
        self.validate(name=dbname, user=dbname)
        self.db.query('CREATE DATABASE %s' % dbname)

    def remove(self, dbname, conn=None):
        if not self.db and conn:
            self.db = conn
        if self.db:
            self.db.query('DROP DATABASE %s' % dbname)
        else:
            raise DBConnFail(self.plugin_info.db_name)

    def usermod(self, user, action, passwd, conn=None):
        if not self.db and conn:
            self.db = conn
        if action == 'add' and self.db:
            self.validate(user=user, passwd=passwd)
            self.db.query('CREATE USER \'%s\'@\'localhost\' IDENTIFIED BY \'%s\''
                % (user,passwd))
        elif action == 'del' and self.db:
            self.db.query('DROP USER \'%s\'@\'localhost\'' % user)
        else:
            raise Exception('Unknown input or database connection failure')

    def chperm(self, dbname, user, action, conn=None):
        if not self.db and conn:
            self.db = conn
        if action == 'check' and self.db:
            self.db.query('SHOW GRANTS FOR \'%s\'@\'localhost\''
                % user)
            r = self.db.store_result()
            out = r.fetch_row(0)
            parse = []
            status = ''
            for line in out:
                if line[0].startswith('Grants for'):
                    continue
                elif line[0] is '' or line[0] is ' ':
                    continue
                else:
                    parse.append(line[0].split(' IDENT')[0])
            for line in parse:
                status += line + '\n'
            return status
        elif action == 'grant' and self.db:
            self.db.query('GRANT ALL ON %s.* TO \'%s\'@\'localhost\'' 
                % (dbname, user))
        elif action == 'revoke' and self.db:
            self.db.query('REVOKE ALL ON %s.* FROM \'%s\'@\'localhost\'' 
                % (dbname, user))
        else:
            raise Exception('Unknown input or database connection failure')

    def execute(self, dbname, command, conn=None, strf=True):
        if not self.db and conn:
            self.db = conn
        cmds = command.split(';')
        if self.db:
            self.db.query('USE %s' % dbname)
            parse = []
            for x in cmds:
                if x.split():
                    self.db.query('%s' % x)
                    r = self.db.store_result()
                    if r:
                        out = r.fetch_row(0)
                        for line in out:
                            parse.append(line)
            if strf:
                status = ''
                for line in parse:
                    status += ', '.join(line)+'\n'
                return status
            else:
                return parse
        else:
            raise DBConnFail(self.plugin_info.db_name)

    def get_dbs(self, conn=None):
        dblist = []
        excludes = ['Database', 'information_schema', 
            'mysql', 'performance_schema']
        if not self.db and conn:
            self.db = conn
        if self.db:
            self.db.query('SHOW DATABASES')
            r = self.db.store_result()
            dbs = r.fetch_row(0)
        else:
            raise DBConnFail(self.plugin_info.db_name)
        for db in dbs:
            if not db[0] in excludes and db[0].split():
                dblist.append({
                    'name': db[0],
                    'type': 'MariaDB',
                    'class': self.__class__
                })
        return dblist

    def get_users(self, conn=None):
        userlist = []
        excludes = ['root', ' ', '']
        if not self.db and conn:
            self.db = conn
        if self.db:
            self.db.query('SELECT user FROM mysql.user')
            r = self.db.store_result()
            output = r.fetch_row(0)
        else:
            raise DBConnFail(self.plugin_info.db_name)
        for usr in output:
            if not usr[0] in userlist and not usr[0] in excludes:
                userlist.append({
                    'name': usr[0],
                    'type': 'MariaDB',
                    'class': self.__class__
                })
        return userlist

########NEW FILE########
__FILENAME__ = main
from genesis.api import *
from genesis.ui import *
from genesis.com import Plugin, Interface, implements
from genesis import apis
from genesis.utils import *

import os
import re
import sqlite3


class SQLite3(Plugin):
    implements(apis.databases.IDatabase)

    def add(self, dbname):
        if re.search('\.|-|`|\\\\|\/|[ ]', dbname):
            raise Exception('Name must not contain spaces, dots, dashes or other special characters')
        self.chkpath()
        path = '/var/lib/sqlite3/%s.db' % dbname
        status = shell_cs('sqlite3 %s "ATTACH \'%s\' AS %s;"' % (path,path,dbname), stderr=True)
        if status[0] >= 1:
            raise Exception(status[1])

    def remove(self, dbname):
        shell('rm /var/lib/sqlite3/%s.db' % dbname)

    def usermod(self):
        pass

    def chperm(self):
        pass

    def execute(self, dbname, command):
        try:
            cmds = command.split(';')
            conn = sqlite3.connect('/var/lib/sqlite3/%s.db' % dbname)
            c = conn.cursor()
            parse = []
            for x in cmds:
                if x.split():
                    c.execute('%s' % x)
                    out = c.fetchall()
                    for line in out:
                        parse.append(line[0])
            status = ''
            for line in parse:
                status += line + '\n'
            return status
        except Exception, e:
            raise Exception('', e)

    def get_dbs(self):
        self.chkpath()
        dblist = []
        for thing in os.listdir('/var/lib/sqlite3'):
            if thing.endswith('.db'):
                dblist.append({'name': thing.split('.db')[0], 'type': 'SQLite3', 'class': self.__class__})
        return dblist

    def get_users(self):
        pass

    def chkpath(self):
        if not os.path.isdir('/var/lib/sqlite3'):
            os.makedirs('/var/lib/sqlite3')

########NEW FILE########
__FILENAME__ = backend
import os
import re
import hashlib
import random
import shutil
import stat
import _mysql_exceptions

from passlib.hash import ldap_md5_crypt

from genesis.api import *
from genesis.com import *
from genesis import apis
from genesis.utils import shell_cs
from genesis.plugins.core.api import ISSLPlugin
from genesis.plugins.users.backend import UsersBackend
from genesis.plugins.network.backend import IHostnameManager


class MailConfig(Plugin):
    implements(IConfigurable)
    name = 'Mailserver'
    id = 'email'
    iconfont = 'gen-envelop'

    def load(self):
        if not os.path.exists('/etc/dovecot/dovecot.conf'):
            shutil.copy('/usr/share/doc/dovecot/example-config/dovecot.conf',
                '/etc/dovecot/dovecot.conf')
        if not os.path.exists('/etc/dovecot/conf.d/10-auth.conf'):
            shutil.rmtree('/etc/dovecot/conf.d')
            shutil.copytree('/usr/share/doc/dovecot/example-config/conf.d',
                '/etc/dovecot/conf.d')
        if not os.path.exists('/etc/dovecot/dovecot-sql.conf.ext'):
            shutil.copy('/usr/share/doc/dovecot/example-config/dovecot-sql.conf.ext',
                '/etc/dovecot/dovecot-sql.conf.ext')
        s = ConfManager.get().load('email', self.postfix_main_file)
        self.postfix_main = self.loads('postfix_main', s)
        s = ConfManager.get().load('email', self.postfix_master_file)
        self.postfix_master = self.loads('postfix_master', s)
        s = ConfManager.get().load('email', self.dovecot_conf_file)
        self.dovecot_conf = self.loads('dovecot_conf', s)
        s = ConfManager.get().load('email', 
            os.path.join(self.dovecot_conf_dir, '10-auth.conf'))
        self.dovecot_auth = self.loads('dovecot_conf', s)
        s = ConfManager.get().load('email', 
            os.path.join(self.dovecot_conf_dir, '10-mail.conf'))
        self.dovecot_mail = self.loads('dovecot_conf', s)
        s = ConfManager.get().load('email', 
            os.path.join(self.dovecot_conf_dir, '10-ssl.conf'))
        self.dovecot_ssl = self.loads('dovecot_conf', s)
        s = ConfManager.get().load('email', 
            os.path.join(self.dovecot_conf_dir, '10-master.conf'))
        self.dovecot_master = self.loads('dovecot_conf', s)
        s = ConfManager.get().load('email', 
            os.path.join(self.dovecot_conf_dir, 'auth-sql.conf.ext'))
        self.dovecot_authsql = self.loads('dovecot_conf', s)
        s = ConfManager.get().load('email', '/etc/dovecot/dovecot-sql.conf.ext')
        self.dovecot_dovecotsql = self.loads('dovecot_conf', s)

    def save(self, wasrunning=False):
        self.mgr = self.app.get_backend(apis.services.IServiceManager)
        if self.mgr.get_status('postfix') == 'running':
            wasrunning = True
            self.mgr.stop('postfix')
            self.mgr.stop('dovecot')
        s = self.dumps('postfix_main', self.postfix_main)
        ConfManager.get().save('email', self.postfix_main_file, s)
        s = self.dumps('postfix_master', self.postfix_master)
        ConfManager.get().save('email', self.postfix_master_file, s)
        s = self.dumps('dovecot_conf', self.dovecot_conf)
        ConfManager.get().save('email', self.dovecot_conf_file, s)
        s = self.dumps('dovecot_conf', self.dovecot_auth)
        ConfManager.get().save('email', 
            os.path.join(self.dovecot_conf_dir, '10-auth.conf'), s)
        s = self.dumps('dovecot_conf', self.dovecot_mail)
        ConfManager.get().save('email', 
            os.path.join(self.dovecot_conf_dir, '10-mail.conf'), s)
        s = self.dumps('dovecot_conf', self.dovecot_ssl)
        ConfManager.get().save('email', 
            os.path.join(self.dovecot_conf_dir, '10-ssl.conf'), s)
        s = self.dumps('dovecot_conf', self.dovecot_master)
        ConfManager.get().save('email', 
            os.path.join(self.dovecot_conf_dir, '10-master.conf'), s)
        s = self.dumps('dovecot_conf', self.dovecot_authsql)
        ConfManager.get().save('email', 
            os.path.join(self.dovecot_conf_dir, 'auth-sql.conf.ext'), s)
        s = self.dumps('dovecot_conf', self.dovecot_dovecotsql)
        ConfManager.get().save('email', '/etc/dovecot/dovecot-sql.conf.ext', s)
        ConfManager.get().commit('email')
        if wasrunning:
            self.mgr.start('postfix')
            self.mgr.start('dovecot')

    def __init__(self):
        self.postfix_main_file = '/etc/postfix/main.cf'
        self.postfix_master_file = '/etc/postfix/master.cf'
        self.dovecot_conf_file = '/etc/dovecot/dovecot.conf'
        self.dovecot_conf_dir = '/etc/dovecot/conf.d'
        self.postfix_main = {}
        self.postfix_master = []
        self.dovecot_conf = {}
        self.dovecot_auth = {}
        self.dovecot_mail = {}
        self.dovecot_ssl = {}
        self.dovecot_master = {}
        self.dovecot_authsql = {}
        self.dovecot_dovecotsql = {}

    def list_files(self):
        dcf = [os.path.join(self.dovecot_conf_dir, x) for x in os.listdir(self.dovecot_conf_dir) \
            if os.path.isfile(os.path.join(self.dovecot_conf_dir, x))]
        dcf.append(self.postfix_main_file)
        dcf.append(self.postfix_master_file)
        dcf.append(self.dovecot_conf_file)
        return dcf

    def loads(self, cfgtype, data):
        # Decode configuration files to a manageable Python object
        if cfgtype == 'postfix_main':
            conf = {}
            lastname = ''
            for line in data.split('\n'):
                if re.match('.*#.*', line):
                    line = line.split('#')[0]
                    if not line.split():
                        continue
                if re.match('^\t.*', line) and lastname:
                    if not type(conf[lastname]) == list:
                        conf[lastname] = []
                    val = re.match('^\s*(.*)$', line).group(1)
                    conf[lastname].append(val)
                elif re.match('.*\s*=\s*.*', line):
                    name, val = re.match('(\S+)\s*=\s*(.*)$', line).group(1,2)
                    name = name.split()[0]
                    val = re.sub(r'"', '', val)
                    if ', ' in val:
                        val = val.split(', ')
                    else:
                        val = val.split()[0] if val.split() else ''
                    conf[name] = val
                    lastname = name
        elif cfgtype == 'postfix_master':
            conf = []
            lastname = ''
            for line in data.split('\n'):
                if re.match('.*#.*', line):
                    line = line.split('#')[0]
                    if not line.split():
                        continue
                if re.match('^\s*-o.*', line) and lastname:
                    val = re.match('^\s*-o\s*(.*)$', line).group(1)
                    for x in enumerate(conf):
                        if x[1][0] == lastname:
                            if len(conf[x[0]]) <= 8:
                                conf[x[0]].insert(9, '')
                            conf[x[0]].append(val)
                            break
                elif re.match('^\s\s(.*)$', line) and lastname:
                    val = re.match('^\s\s(.*)$', line).group(1)
                    for x in enumerate(conf):
                        if x[1][0] == lastname:
                            conf[x[0]].insert(9, val)
                            break
                elif line.split():
                    conf.append(line.split())
                    lastname = line.split()[0]
        elif cfgtype == 'dovecot_conf':
            conf = {}
            active = []
            for line in data.split('\n'):
                if re.match('.*#.*', line):
                    line = line.split('#')[0]
                    if not line.split():
                        continue
                elif line.startswith('!'):
                    num = 0
                    name, val = re.match('^!(.+)\s(.+)$', line).group(1,2)
                    if active:
                        for x in conf[active[-1]]:
                            if x.startswith(name+'_'):
                                num = num + 1
                        conf[active[-1]][name+'_'+str(num)] = val
                    else:
                        for x in conf:
                            if x.startswith(name+'_') and re.match('[0-9]$', x):
                                num = num + 1
                        conf[name+'_'+str(num)] = val
                elif re.match('\s*(.+)\s*{\s*$', line):
                    val = re.match('\s*(.+)\s+{', line).group(1)
                    num = 0
                    if active:
                        for x in conf[active[-1]]:
                            if x.startswith(val+'_'):
                                num = num + 1
                        conf[active[-1]][val+'_'+str(num)] = {}
                        active.append(val+'_'+str(num))
                    else:
                        for x in conf:
                            if x.startswith(val+'_'):
                                num = num + 1
                        conf[val+'_'+str(num)] = {}
                        active.append(val+'_'+str(num))
                elif re.match('.*\s*=\s*.*', line):
                    name, val = re.match('\s*(\S+)\s*=\s*(.*)\s*$', line).group(1,2)
                    name = name.split()[0]
                    val = re.sub(r'"', '', val)
                    if ', ' in val:
                        val = val.split(', ')
                    if len(active) == 2:
                        conf[active[0]][active[1]][name] = val
                    elif active:
                        conf[active[-1]][name] = val
                    else:
                        conf[name] = val
                # Match the end of an array
                if re.match('.*}', line):
                    closenum = len(re.findall('}', line))
                    while closenum > 0:
                        active.pop()
                        closenum = closenum - 1
        return conf

    def dumps(self, cfgtype, data):
        f = ''
        if cfgtype == 'postfix_main':
            for x in data:
                if type(data[x]) == str:
                    f += x+' = '+data[x]+'\n'
                else:
                    f += x+' = '+', '.join(data[x])+'\n'
        elif cfgtype == 'postfix_master':
            sp = (' '*7)
            for x in data:
                f += x[0]+sp+x[1]+' '+x[2]+sp+x[3]+sp+x[4]+sp+x[5]+sp+x[6]+sp+x[7]+'\n'
                if len(x) >= 9 and x[8]:
                    f += '  '+x[8]+'\n'
                if len(x) >= 10:
                    for y in x[9:]:
                        f += '  -o '+y+'\n'
        elif cfgtype == 'dovecot_conf':
            for x in data:
                if x.startswith('include'):
                    f += '!'+x.rsplit('_', 1)[0]+' '+data[x]+'\n'
                elif re.match('.*_[0-9]+$', x):
                    f += x.rsplit('_', 1)[0]+' {\n'
                    for y in data[x]:
                        if type(data[x][y]) == dict:
                            f += '  '+y.rsplit('_', 1)[0]+' {\n'
                            for z in data[x][y]:
                                f += '    '+z+' = '+data[x][y][z]+'\n'
                            f += '  }\n'
                        else:
                            f += '  '+y+' = '+data[x][y]+'\n'
                    f += '}\n'
                else:
                    if type(data[x]) == str:
                        f += x+' = '+data[x]+'\n'
                    else:
                        f += x+' = '+', '.join(data[x])+'\n'
        return f


class MailControl(Plugin):
    def is_setup(self):
        dbase = apis.databases(self.app).get_interface('MariaDB')
        conn = apis.databases(self.app).get_dbconn('MariaDB')
        if 'vmail' not in [x['name'] for x in dbase.get_dbs(conn)] \
        or 'vmail' not in [x['name'] for x in dbase.get_users(conn)]:
            return False
        else:
            return True

    def initial_setup(self):
        # Grab frameworks for use later
        config = MailConfig(self.app)
        users = UsersBackend(self.app)
        dbase = apis.databases(self.app).get_interface('MariaDB')
        conn = apis.databases(self.app).get_dbconn('MariaDB')
        config.load()

        # Create a MySQL database for storing mailbox, alias and
        # domain information
        if 'vmail' in [x['name'] for x in dbase.get_dbs(conn)]:
            dbase.remove('vmail', conn)
        if 'vmail' in [x['name'] for x in dbase.get_users(conn)]:
            dbase.usermod('vmail', 'del', '', conn)
        dbase.add('vmail', conn)
        passwd = hashlib.sha1(str(random.random())).hexdigest()[0:16]
        dbase.usermod('vmail', 'add', passwd, conn)
        dbase.chperm('vmail', 'vmail', 'grant', conn)
        sql = (
            'CREATE TABLE alias ( '
            'address varchar(255) NOT NULL default \'\', '
            'goto text NOT NULL, '
            'domain varchar(255) NOT NULL default \'\', '
            'created datetime NOT NULL default \'0000-00-00 00:00:00\', '
            'active tinyint(1) NOT NULL default \'1\', '
            'PRIMARY KEY  (address), '
            'KEY address (address) '
            ') COMMENT=\'Virtual Aliases\'; '
            'CREATE TABLE domain ( '
            'domain varchar(255) NOT NULL default \'\', '
            'transport varchar(255) default NULL, '
            'backupmx tinyint(1) NOT NULL default \'0\', '
            'created datetime NOT NULL default \'0000-00-00 00:00:00\', '
            'active tinyint(1) NOT NULL default \'1\', '
            'PRIMARY KEY  (domain), '
            'KEY domain (domain) '
            ') COMMENT=\'Virtual Domains\'; '
            'CREATE TABLE alias_domain ( '
            'alias_domain varchar(255) NOT NULL default \'\', '
            'target_domain varchar(255) NOT NULL default \'\', '
            'created datetime NOT NULL default \'0000-00-00 00:00:00\', '
            'active tinyint(1) NOT NULL default \'1\', '
            'PRIMARY KEY (alias_domain), '
            'KEY active (active), '
            'KEY target_domain (target_domain) '
            ') COMMENT=\'Domain Aliases\'; '
            'CREATE TABLE mailbox ( '
            'username varchar(255) NOT NULL default \'\', '
            'password varchar(255) NOT NULL default \'\', '
            'name varchar(255) NOT NULL default \'\', '
            'maildir varchar(255) NOT NULL default \'\', '
            'quota bigint(20) NOT NULL default \'0\', '
            'local_part varchar(255) NOT NULL default \'\', '
            'domain varchar(255) NOT NULL default \'\', '
            'created datetime NOT NULL default \'0000-00-00 00:00:00\', '\
            'active tinyint(1) NOT NULL default \'1\', '
            'PRIMARY KEY  (username), '
            'KEY username (username) '
            ') COMMENT=\'Virtual Mailboxes\';'
        )
        dbase.execute('vmail', sql, conn, False)

        # Add system user and group for handling mail
        users.add_sys_user('vmail')
        users.add_group('vmail')
        users.add_to_group('vmail', 'vmail')
        uid = int(users.get_user('vmail', users.get_all_users()).uid)
        gid = int(users.get_group('vmail', users.get_all_groups()).gid)
        pfgid = int(users.get_group('dovecot', users.get_all_groups()).gid)

        # Create the virtual mail directory
        if not os.path.exists('/var/vmail'):
            os.mkdir('/var/vmail')
        users.change_user_param('vmail', 'home', '/var/vmail')
        users.change_user_param('vmail', 'shell', '/sbin/nologin')
        os.chmod('/var/vmail', 0770)
        os.chown('/var/vmail', uid, gid)

        # Tell Dovecot (MDA) where to find users and passwords
        config.dovecot_authsql = {
            'passdb_0': {
                'driver': 'sql',
                'args': '/etc/dovecot/dovecot-sql.conf.ext'
            },
            'userdb_0': {
                'driver': 'sql',
                'args': '/etc/dovecot/dovecot-sql.conf.ext'
            }
        }

        # Tell Dovecot how to read our SQL
        config.dovecot_dovecotsql['driver'] = 'mysql'
        config.dovecot_dovecotsql['connect'] = \
            'host=localhost dbname=vmail user=vmail password=%s'%passwd
        config.dovecot_dovecotsql['default_pass_scheme'] = 'MD5-CRYPT'
        config.dovecot_dovecotsql['password_query'] = (
            'SELECT username as user, password, \'/var/vmail/%d/%n\''
            ' as userdb_home, \'maildir:/var/vmail/%d/%n\' as userdb_mail,'
            ' '+str(uid)+' as userdb_uid, '+str(gid)+' as userdb_gid FROM mailbox '
            'WHERE username = \'%u\' AND active = \'1\'')
        config.dovecot_dovecotsql['user_query'] = (
            'SELECT \'/var/vmail/%d/%n\' as home, '
            '\'maildir:/var/vmail/%d/%n\' as mail, '+str(uid)+' AS uid, '+str(gid)+' AS gid, '
            'concat(\'dirsize:storage=\', quota) AS quota FROM mailbox '
            'WHERE username = \'%u\' AND active = \'1\'')
        config.dovecot_auth['disable_plaintext_auth'] = 'yes'
        config.dovecot_auth['auth_mechanisms'] = 'plain login'
        rm = ''
        for x in config.dovecot_auth:
            if x.startswith('include') and config.dovecot_auth[x] != 'auth-sql.conf.ext':
                rm = x
        if rm:
            del config.dovecot_auth[rm]
        config.dovecot_auth['include_0'] = 'auth-sql.conf.ext'

        config.dovecot_ssl['ssl_key'] = ''
        config.dovecot_ssl['ssl_cert'] = ''

        # Tell Dovecot where to put its mail and how to save/access it
        config.dovecot_mail['mail_location'] = 'maildir:/var/vmail/%d/%n'
        config.dovecot_mail['mail_uid'] = 'vmail'
        config.dovecot_mail['mail_gid'] = 'vmail'
        config.dovecot_mail['first_valid_uid'] = str(uid)
        config.dovecot_mail['last_valid_uid'] = str(uid)

        # Tell Dovecot to communicate with Postfix (MTA)
        config.dovecot_master['service auth_0'] = {
            'unix_listener auth-userdb_0': {
                'mode': '0600',
                'user': 'vmail',
                'group': 'vmail'
            },
            'unix_listener /var/spool/postfix/private/auth_0': {
                'mode': '0660',
                'user': 'postfix',
                'group': 'postfix'
            }
        }

        # Protect Dovecot configuration folder
        for r, d, f in os.walk('/etc/dovecot'):
            for x in d:
                os.chown(os.path.join(r, x), uid, pfgid)
                st = os.stat(os.path.join(r, x))
                os.chmod(os.path.join(r, x), st.st_mode&~stat.S_IROTH&~stat.S_IWOTH&~stat.S_IXOTH)
            for x in f:
                os.chown(os.path.join(r, x), uid, pfgid)
                st = os.stat(os.path.join(r, x))
                os.chmod(os.path.join(r, x), st.st_mode&~stat.S_IROTH&~stat.S_IWOTH&~stat.S_IXOTH)

        # Tell Postfix (MTA) how to get mailbox, alias and domain info
        # from our MySQL database
        f = open('/etc/postfix/mysql_virtual_alias_domainaliases_maps.cf', 'w')
        f.write('user = vmail\n'
            'password = '+passwd+'\n'
            'hosts = 127.0.0.1\n'
            'dbname = vmail\n'
            'query = SELECT goto FROM alias,alias_domain\n'
            '  WHERE alias_domain.alias_domain = \'%d\'\n'
            '  AND alias.address=concat(\'%u\', \'@\', alias_domain.target_domain)\n'
            '  AND alias.active = 1\n')
        f.close()
        f = open('/etc/postfix/mysql_virtual_alias_maps.cf', 'w')
        f.write('user = vmail\n'
            'password = '+passwd+'\n'
            'hosts = 127.0.0.1\n'
            'dbname = vmail\n'
            'table = alias\n'
            'select_field = goto\n'
            'where_field = address\n'
            'additional_conditions = and active = \'1\'\n')
        f.close()
        f = open('/etc/postfix/mysql_virtual_domains_maps.cf', 'w')
        f.write('user = vmail\n'
            'password = '+passwd+'\n'
            'hosts = 127.0.0.1\n'
            'dbname = vmail\n'
            'table = domain\n'
            'select_field = domain\n'
            'where_field = domain\n'
            'additional_conditions = and backupmx = \'0\' and active = \'1\'\n')
        f.close()
        f = open('/etc/postfix/mysql_virtual_mailbox_domainaliases_maps.cf', 'w')
        f.write('user = vmail\n'
            'password = '+passwd+'\n'
            'hosts = 127.0.0.1\n'
            'dbname = vmail\n'
            'query = SELECT maildir FROM mailbox, alias_domain\n'
            '  WHERE alias_domain.alias_domain = \'%d\'\n'
            '  AND mailbox.username=concat(\'%u\', \'@\', alias_domain.target_domain )\n'
            '  AND mailbox.active = 1\n')
        f.close()
        f = open('/etc/postfix/mysql_virtual_mailbox_maps.cf', 'w')
        f.write('user = vmail\n'
            'password = '+passwd+'\n'
            'hosts = 127.0.0.1\n'
            'dbname = vmail\n'
            'table = mailbox\n'
            'select_field = CONCAT(domain, \'/\', local_part)\n'
            'where_field = username\n'
            'additional_conditions = and active = \'1\'\n')
        f.close()
        f = open('/etc/postfix/header_checks', 'w')
        f.write('/^Received:/                 IGNORE\n'
            '/^User-Agent:/               IGNORE\n'
            '/^X-Mailer:/                 IGNORE\n'
            '/^X-Originating-IP:/         IGNORE\n'
            '/^x-cr-[a-z]*:/              IGNORE\n'
            '/^Thread-Index:/             IGNORE\n')
        f.close()

        # Configure Postfix
        config.postfix_main = {
            'smtpd_banner': '$myhostname ESMTP $mail_name',
            'biff': 'no',
            'append_dot_mydomain': 'no',
            'readme_directory': 'no',
            'smtpd_sasl_type': 'dovecot',
            'smtpd_sasl_path': 'private/auth',
            'smtpd_sasl_auth_enable': 'yes',
            'broken_sasl_auth_clients': 'yes',
            'smtpd_sasl_security_options': 'noanonymous',
            'smtpd_sasl_local_domain': '',
            'smtpd_sasl_authenticated_header': 'yes',
            'smtp_tls_note_starttls_offer': 'no',
            'smtpd_tls_loglevel': '1',
            'smtpd_tls_received_header': 'yes',
            'smtpd_tls_session_cache_timeout': '3600s',
            'tls_random_source': 'dev:/dev/urandom',
            'smtpd_use_tls': 'no',
            'smtpd_enforce_tls': 'no',
            'smtp_use_tls': 'no',
            'smtp_enforce_tls': 'no',
            'smtpd_tls_security_level': 'may',
            'smtp_tls_security_level': 'may',
            'unknown_local_recipient_reject_code': '450',
            'maximal_queue_lifetime': '7d',
            'minimal_backoff_time': '1800s',
            'maximal_backoff_time': '8000s',
            'smtp_helo_timeout': '60s',
            'smtpd_recipient_limit': '16',
            'smtpd_soft_error_limit': '3',
            'smtpd_hard_error_limit': '12',
            'smtpd_helo_restrictions': 'permit_mynetworks, warn_if_reject reject_non_fqdn_hostname, reject_invalid_hostname, permit',
            'smtpd_sender_restrictions': 'permit_sasl_authenticated, permit_mynetworks, warn_if_reject reject_non_fqdn_sender, reject_unknown_sender_domain, reject_unauth_pipelining, permit',
            'smtpd_client_restrictions': 'reject_rbl_client sbl.spamhaus.org, reject_rbl_client blackholes.easynet.nl',
            'smtpd_recipient_restrictions': 'reject_unauth_pipelining, permit_mynetworks, permit_sasl_authenticated, reject_non_fqdn_recipient, reject_unknown_recipient_domain, reject_unauth_destination, permit',
            'smtpd_data_restrictions': 'reject_unauth_pipelining',
            'smtpd_relay_restrictions': 'reject_unauth_pipelining, permit_mynetworks, permit_sasl_authenticated, reject_non_fqdn_recipient, reject_unknown_recipient_domain, reject_unauth_destination, permit',
            'smtpd_helo_required': 'yes',
            'smtpd_delay_reject': 'yes',
            'disable_vrfy_command': 'yes',
            'myhostname': self.app.get_backend(IHostnameManager).gethostname().lower(),
            'myorigin': self.app.get_backend(IHostnameManager).gethostname().lower(),
            'mydestination': '',
            'mynetworks': '127.0.0.0/8 [::ffff:127.0.0.0]/104 [::1]/128',
            'mailbox_size_limit': '0',
            'recipient_delimiter': '+',
            'inet_interfaces': 'all',
            'mynetworks_style': 'host',
            'virtual_mailbox_base': '/var/vmail',
            'virtual_mailbox_maps': 'mysql:/etc/postfix/mysql_virtual_mailbox_maps.cf, mysql:/etc/postfix/mysql_virtual_mailbox_domainaliases_maps.cf',
            'virtual_uid_maps': 'static:'+str(uid),
            'virtual_gid_maps': 'static:'+str(gid),
            'virtual_alias_maps': 'mysql:/etc/postfix/mysql_virtual_alias_maps.cf, mysql:/etc/postfix/mysql_virtual_alias_domainaliases_maps.cf',
            'virtual_mailbox_domains': 'mysql:/etc/postfix/mysql_virtual_domains_maps.cf',
            'virtual_transport': 'dovecot',
            'dovecot_destination_recipient_limit': '1',
            'header_checks': 'regexp:/etc/postfix/header_checks',
            'enable_original_recipient': 'no'
        }
        xs, xss, xd = False, False, False
        for x in config.postfix_master:
            if x[0] == 'smtp':
                x = ['smtp', 'inet', 'n', '-', '-', '-', '-', 'smtpd']
                xs = True
            elif x[0] == 'submission':
                x = ['submission', 'inet', 'n', '-', '-', '-', '-', 'smtpd', '',
                    'syslog_name=postfix/submission', 'smtpd_sasl_auth_enable=yes', 'smtpd_tls_auth_only=yes',
                    'smtpd_client_restrictions=permit_sasl_authenticated,reject_unauth_destination,reject',
                    'smtpd_sasl_security_options=noanonymous,noplaintext',
                    'smtpd_sasl_tls_security_options=noanonymous']
                xss = True
            elif x[0] == 'dovecot':
                x = ['dovecot', 'unix', '-', 'n', 'n', '-', '-', 'pipe',
                    'flags=DRhu user=vmail:vmail argv=/usr/lib/dovecot/dovecot-lda -d $(recipient)']
                xd = True
        if not xs:
            config.postfix_master.insert(0, ['smtp', 'inet', 'n', '-', '-', '-', '-', 'smtpd'])
        if not xss:
            config.postfix_master.insert(2, ['submission', 'inet', 'n', '-', '-', '-', '-', 'smtpd', '',
                'syslog_name=postfix/submission', 'smtpd_sasl_auth_enable=yes', 'smtpd_tls_auth_only=yes',
                'smtpd_client_restrictions=permit_sasl_authenticated,reject_unauth_destination,reject',
                'smtpd_sasl_security_options=noanonymous,noplaintext',
                'smtpd_sasl_tls_security_options=noanonymous'])
        if not xd:
            config.postfix_master.append(['dovecot', 'unix', '-', 'n', 'n', '-', '-', 'pipe',
                'flags=DRhu user=vmail:vmail argv=/usr/lib/dovecot/dovecot-lda -d $(recipient)'])
        open('/etc/aliases', 'w').write('')

        # Save the configurations and start the services
        config.save(True)
        cfg =  self.app.get_config(self)
        cfg.reinitialize = False
        cfg.save()

    def list_domains(self):
        dbase = apis.databases(self.app).get_interface('MariaDB')
        conn = apis.databases(self.app).get_dbconn('MariaDB')
        try:
            d = dbase.execute('vmail', 
                'SELECT domain FROM domain;', conn, False)
        except _mysql_exceptions.OperationalError, e:
            if e[0] == 1049:
                return []
        except Exception, e:
            raise
        for x in d:
            if x == ('ALL',):
                d.remove(x)
        return [x[0] for x in d]

    def list_mailboxes(self, domain):
        r = []
        dbase = apis.databases(self.app).get_interface('MariaDB')
        conn = apis.databases(self.app).get_dbconn('MariaDB')
        d = dbase.execute('vmail', 
            'SELECT local_part,name,quota FROM mailbox WHERE domain = \"%s\"'%domain, 
            conn, False)
        for x in d:
            r.append({'username': x[0], 'name': x[1], 'quota': x[2],
                'domain': domain})
        return r

    def list_aliases(self, domain):
        r = []
        dbase = apis.databases(self.app).get_interface('MariaDB')
        conn = apis.databases(self.app).get_dbconn('MariaDB')
        d = dbase.execute('vmail', 
            'SELECT address,goto FROM alias WHERE domain = \"%s\";'%domain, 
            conn, False)
        for x in d:
            r.append({'address': x[0], 'forward': x[1], 'domain': domain})
        return r

    def add_mailbox(self, name, dom, passwd, fullname, quota=False):
        dbase = apis.databases(self.app).get_interface('MariaDB')
        conn = apis.databases(self.app).get_dbconn('MariaDB')
        pwhash = ldap_md5_crypt.encrypt(passwd).split('{CRYPT}')[1]
        dbase.execute('vmail',
            'INSERT INTO `mailbox` VALUES (\"'+name+'@'+dom+'\", '+\
            '\"'+pwhash+'\", \"'+fullname+'\", \"'+name+'@'+dom+'/\", '+\
            (quota if quota else '0')+', \"'+name+'\", \"'+dom+'\", '+\
            'NOW(), 1)', conn, False)

    def del_mailbox(self, name, dom):
        dbase = apis.databases(self.app).get_interface('MariaDB')
        conn = apis.databases(self.app).get_dbconn('MariaDB')
        dbase.execute('vmail',
            'DELETE FROM `mailbox` WHERE local_part = \"%s\" AND domain = \"%s\"'%(name,dom), conn, False)

    def add_alias(self, name, dom, forward):
        dbase = apis.databases(self.app).get_interface('MariaDB')
        conn = apis.databases(self.app).get_dbconn('MariaDB')
        dbase.execute('vmail',
            'INSERT INTO `alias` VALUES (\"'+name+'@'+dom+'\", \"'+forward+'\", '+\
            '\"'+dom+'\", NOW(), 1)', conn, False)

    def del_alias(self, addr, forward):
        dbase = apis.databases(self.app).get_interface('MariaDB')
        conn = apis.databases(self.app).get_dbconn('MariaDB')
        dbase.execute('vmail',
            'DELETE FROM `alias` WHERE address = \"%s\" AND goto = \"%s\"'%(addr,forward), conn, False)

    def add_domain(self, name):
        dbase = apis.databases(self.app).get_interface('MariaDB')
        conn = apis.databases(self.app).get_dbconn('MariaDB')
        dbase.execute('vmail',
            'INSERT INTO `domain` VALUES (\"'+name+'\", \"virtual\", '
            +'0, NOW(), 1)', conn, False)

    def del_domain(self, name):
        dbase = apis.databases(self.app).get_interface('MariaDB')
        conn = apis.databases(self.app).get_dbconn('MariaDB')
        dbase.execute('vmail',
            'DELETE FROM `domain` WHERE domain = \"%s\"'%name, conn, False)

    def edit(self, name, dom, quota, passwd):
        dbase = apis.databases(self.app).get_interface('MariaDB')
        conn = apis.databases(self.app).get_dbconn('MariaDB')
        if passwd:
            pwhash = ldap_md5_crypt.encrypt(passwd).split('{CRYPT}')[1]
        if passwd and quota:
            dbase.execute('vmail',
                'UPDATE mailbox SET quota = %s, password = \"%s\" WHERE local_part = \"%s\" AND domain = \"%s\"'%(quota,pwhash,name,dom), conn, False)
        elif passwd:
            dbase.execute('vmail',
                'UPDATE mailbox SET password = \"%s\" WHERE local_part = \"%s\" AND domain = \"%s\"'%(pwhash,name,dom), conn, False)
        elif quota:
            dbase.execute('vmail',
                'UPDATE mailbox SET quota = %s WHERE local_part = \"%s\" AND domain = \"%s\"'%(quota,name,dom), conn, False)


class MailSSLPlugin(Plugin):
    implements(ISSLPlugin)
    text = 'Mailserver'
    iconfont = 'gen-envelop'
    cert_type = 'cert-key'

    def enable_ssl(self, cert, key):
        config = MailConfig(self.app)
        config.load()
        config.postfix_main['smtpd_tls_cert_file'] = cert
        config.postfix_main['smtpd_tls_key_file'] = key
        config.postfix_main['smtpd_use_tls'] = 'yes'
        config.postfix_main['smtp_tls_note_starttls_offer'] = 'yes'
        config.postfix_main['smtp_tls_security_level'] = 'may'
        config.postfix_main['smtpd_tls_security_level'] = 'may'
        config.postfix_main['smtpd_tls_auth_only'] = 'yes'
        config.postfix_main['smtp_tls_ciphers'] = 'high'
        config.postfix_main['smtp_tls_exclude_ciphers'] = ['aNULL', 
            'DES', '3DES', 'MD5', 'DES+MD5', 'RC4']
        config.postfix_main['smtpd_tls_protocols'] = ['TLSv1.2',
            'TLSv1.1', 'TLSv1', 'SSLv3', '!SSLv2']
        config.dovecot_ssl['ssl'] = 'yes'
        config.dovecot_ssl['ssl_cert'] = '<'+cert
        config.dovecot_ssl['ssl_key'] = '<'+key
        config.save()

    def disable_ssl(self):
        config = MailConfig(self.app)
        config.load()
        del config.postfix_main['smtpd_tls_cert_file']
        del config.postfix_main['smtpd_tls_key_file']
        del config.postfix_main['smtpd_tls_auth_only']
        del config.postfix_main['smtp_tls_note_starttls_offer']
        del config.postfix_main['smtpd_use_tls']
        del config.postfix_main['smtp_tls_security_level']
        del config.postfix_main['smtpd_tls_security_level']
        del config.postfix_main['smtp_tls_ciphers']
        del config.postfix_main['smtp_tls_exclude_ciphers']
        del config.postfix_main['smtpd_tls_protocols']
        config.dovecot_ssl['ssl'] = 'no'
        config.dovecot_ssl['ssl_cert'] = ''
        config.dovecot_ssl['ssl_key'] = ''
        config.save()

########NEW FILE########
__FILENAME__ = config
from genesis.api import ModuleConfig
from backend import MailControl


class GeneralConfig(ModuleConfig):
    target = MailControl
    
    labels = {
        'reinitialize': 'Reinitialize'
    }
    
    reinitialize = True

########NEW FILE########
__FILENAME__ = main
import re

from genesis.ui import *
from genesis.api import *
from genesis import apis
from genesis.plugins.databases.utils import DBAuthFail, DBConnFail

import backend

class MailPlugin(apis.services.ServiceControlPlugin):
    text = 'Mailserver'
    iconfont = 'gen-envelop'
    folder = 'servers'

    def on_session_start(self):
        self._edit = None
        self._addbox = None
        self._addalias = None
        self._adddom = None
        self._list = None
        self._aliases, self._boxes = [], []
        self._config = backend.MailConfig(self.app)
        self._mc = backend.MailControl(self.app)
        self._config.load()

    def on_init(self):
        try:
            self._domains = self._mc.list_domains()
        except DBConnFail:
            pass

    def get_main_ui(self):
        ui = self.app.inflate('email:main')

        if not apis.databases(self.app).get_interface('MariaDB').checkpwstat():
            self.put_message('err', 'MariaDB does not have a root password set. '
                'Please add this via the Databases screen.')
            return ui
        elif not apis.databases(self.app).get_dbconn('MariaDB'):
            ui.append('main', UI.InputBox(id='dlgAuth', 
                text='Enter the database password for MariaDB', 
                password=True))
            return ui

        is_setup = self._mc.is_setup()
        if self.app.get_config(self._mc).reinitialize \
        or not is_setup:
            if not is_setup:
                self.put_message('err', 'Your mailserver does not appear to be properly configured. Please rerun this setup.')
            return UI.Button(iconfont="gen-cog", text="Setup Mailserver", id="setup")

        t = ui.find('list')
        for x in self._domains:
            t.append(UI.DTR(
                UI.Iconfont(iconfont='gen-code'),
                UI.Label(text=x),
                UI.HContainer(
                    UI.TipIcon(iconfont='gen-pencil', id='list/'+str(self._domains.index(x)), text='Show Boxes/Aliases'),
                    UI.TipIcon(iconfont='gen-cancel-circle', id='deldom/'+str(self._domains.index(x)), text='Delete Domain',
                        warning='Are you sure you want to delete mail domain %s?'%x)
                ),
            ))

        if self._addbox:
            doms = [UI.SelectOption(text=x, value=x) for x in self._domains]
            if doms:
                ui.append('main',
                    UI.DialogBox(
                        UI.FormLine(
                            UI.TextInput(name='acct', id='acct'),
                            text='Account Name', help="The \'name\' in name@example.com"
                        ),
                        UI.FormLine(
                            UI.Select(*doms if doms else 'None', id='dom', name='dom'),
                            text='Domain'
                        ),
                        UI.FormLine(
                            UI.EditPassword(id='passwd', value='Click to add password'),
                            text='Password'
                        ),
                        UI.FormLine(
                            UI.TextInput(name='fullname', id='fullname'),
                            text='Full Name'
                        ),
                        UI.FormLine(
                            UI.TextInput(name='quota', id='quota'),
                            text='Quota (in MB)', help='Enter 0 for unlimited'
                        ),
                        id='dlgAddBox')
                    )
            else:
                self.put_message('err', 'You must add a domain first!')
                self._addbox = None

        if self._addalias:
            doms = [UI.SelectOption(text=x, value=x) for x in self._domains]
            if doms:
                ui.append('main',
                    UI.DialogBox(
                        UI.FormLine(
                            UI.TextInput(name='acct', id='acct'),
                            text='Account Name', help="The \'name\' in name@example.com"
                        ),
                        UI.FormLine(
                            UI.Select(*doms if doms else 'None', id='dom', name='dom'),
                            text='Domain'
                        ),
                        UI.FormLine(
                            UI.TextInput(name='forward', id='forward'),
                            text='Points to', help="A full email address to forward messages to"
                        ),
                        id='dlgAddAlias')
                    )
            else:
                self.put_message('err', 'You must add a domain first!')
                self._addalias = None

        if self._adddom:
            ui.append('main',
                UI.InputBox(id='dlgAddDom', text='Enter domain name to add'))

        if self._edit:
            ui.append('main',
                UI.DialogBox(
                    UI.FormLine(
                        UI.Label(text=self._edit['username']+'@'+self._edit['domain']),
                        text="Editing mailbox for"
                    ),
                    UI.FormLine(
                        UI.TextInput(name='quota', id='quota', value=self._edit['quota']),
                        text='Quota (in MB)', help="Enter 0 for unlimited"
                    ),
                    UI.FormLine(
                        UI.EditPassword(id='chpasswd', value='Click to change password'),
                        text='Password'
                    ),
                    id='dlgEdit')
                )

        if self._list:
            dui = self.app.inflate('email:list')
            t = dui.find('ulist')
            self._boxes = []
            for x in self._mc.list_mailboxes(self._list):
                self._boxes.append(x)
                t.append(UI.DTR(
                    UI.Iconfont(iconfont='gen-user'),
                    UI.Label(text=x['username']),
                    UI.Label(text=x['name']),
                    UI.Label(text=x['quota']+' MB' if x['quota'] != '0' else 'Unlimited'),
                    UI.HContainer(
                        UI.TipIcon(iconfont='gen-key', id='edit/'+str(self._boxes.index(x)), text='Edit Mailbox'),
                        UI.TipIcon(iconfont='gen-cancel-circle', id='delbox/'+str(self._boxes.index(x)), text='Delete Mailbox',
                            warning='Are you sure you want to delete mailbox %s@%s?'%(x['username'],x['domain']))
                    ),
                ))
            t = dui.find('alist')
            self._aliases = []
            for x in self._mc.list_aliases(self._list):
                self._aliases.append(x)
                t.append(UI.DTR(
                    UI.Iconfont(iconfont='gen-link'),
                    UI.Label(text=x['address']),
                    UI.Label(text=x['forward']),
                    UI.HContainer(
                        UI.TipIcon(iconfont='gen-cancel-circle', id='delal/'+str(self._aliases.index(x)), text='Delete Mailbox',
                            warning='Are you sure you want to delete alias %s, pointing at %s?'%(x['address'],x['forward']))
                    ),
                ))
            ui.append('main',
                UI.DialogBox(dui, id='dlgList')
            )

        return ui

    @event('button/click')
    def on_click(self, event, params, vars = None):
        if params[0] == 'setup':
            self._mc.initial_setup()
        elif params[0] == 'add':
            self._addbox = True
        elif params[0] == 'addalias':
            self._addalias = True
        elif params[0] == 'adddom':
            self._adddom = True
        elif params[0] == 'list':
            self._list = self._domains[int(params[1])]
        elif params[0] == 'edit':
            self._list = None
            b = self._boxes[int(params[1])]
            self._boxes = []
            self._edit = b
        elif params[0] == 'delbox':
            try:
                b = self._boxes[int(params[1])]
                self._boxes = []
                self._mc.del_mailbox(b['username'], b['domain'])
                self.put_message('info', 'Mailbox deleted successfully')
            except Exception, e:
                self.app.log.error('Mailbox could not be deleted. Error: %s' % str(e))
                self.put_message('err', 'Mailbox could not be deleted')
        elif params[0] == 'delal':
            try:
                a = self._aliases[int(params[1])]
                self._aliases = []
                self._mc.del_alias(a['address'], a['forward'])
                self.put_message('info', 'Alias deleted successfully')
            except Exception, e:
                self.app.log.error('Alias could not be deleted. Error: %s' % str(e))
                self.put_message('err', 'Alias could not be deleted')
        elif params[0] == 'deldom':
            for x in self._boxes + self._aliases:
                if x['domain'] == self._domains[int(params[1])]:
                    self.put_message('err', 'You still have mailboxes or aliases attached to this domain. Remove them before deleting the domain!')
                    break
            else:
                self._mc.del_domain(self._domains[int(params[1])])
                self.put_message('info', 'Domain deleted')

    @event('dialog/submit')
    @event('form/submit')
    def on_submit(self, event, params, vars=None):
        if params[0] == 'dlgAddBox':
            acct = vars.getvalue('acct', '')
            dom = vars.getvalue('dom', '')
            passwd = vars.getvalue('passwd', '')
            fullname = vars.getvalue('fullname', '')
            quota = vars.getvalue('quota', '')
            if vars.getvalue('action', '') == 'OK':
                m = re.match('([-0-9a-zA-Z.+_]+)', acct)
                if not acct or not m:
                    self.put_message('err', 'Must choose a valid mailbox name')
                elif acct in [x['username'] for x in self._mc.list_mailboxes(dom)]:
                    self.put_message('err', 'You already have a mailbox with this name on this domain')
                elif not passwd:
                    self.put_message('err', 'Must choose a password')
                elif passwd != vars.getvalue('passwdb',''):
                    self.put_message('err', 'Passwords must match')
                else:
                    try:
                        self._mc.add_mailbox(acct, dom, passwd, fullname, quota)
                        self.put_message('info', 'Mailbox added successfully')
                    except Exception, e:
                        self.app.log.error('Mailbox %s@%s could not be added. Error: %s' % (acct,dom,str(e)))
                        self.put_message('err', 'Mailbox could not be added')
            self._addbox = None
        elif params[0] == 'dlgAddAlias':
            acct = vars.getvalue('acct', '')
            dom = vars.getvalue('dom', '')
            forward = vars.getvalue('forward', '')
            if vars.getvalue('action', '') == 'OK':
                m = re.match('([-0-9a-zA-Z.+_]+)', acct)
                if not acct or not m:
                    self.put_message('err', 'Must choose a valid alias name')
                elif (acct+'@'+dom, forward) in [(x['address'], x['forward']) for x in self._mc.list_aliases(dom)]:
                    self.put_message('err', 'This alias has already been created')
                else:
                    try:
                        self._mc.add_alias(acct, dom, forward)
                        self.put_message('info', 'Alias added successfully')
                    except Exception, e:
                        self.app.log.error('Alias from %s@%s to %s could not be added. Error: %s' % (acct,dom,forward,str(e)))
                        self.put_message('err', 'Alias could not be added')
            self._addalias = None
        elif params[0] == 'dlgAddDom':
            v = vars.getvalue('value', '')
            if vars.getvalue('action', '') == 'OK':
                if not v or not re.match('([-0-9a-zA-Z.+_]+\.[a-zA-Z]{2,4})', v):
                    self.put_message('err', 'Must enter a valid domain to add')
                elif v in self._domains:
                    self.put_message('err', 'You have already added this domain!')
                else:
                    try:
                        self._mc.add_domain(v)
                        self.put_message('info', 'Domain added successfully')
                    except Exception, e:
                        self.app.log.error('Domain %s could not be added. Error: %s' % (v,str(e)))
                        self.put_message('err', 'Domain could not be added')
            self._adddom = None
        if params[0] == 'dlgList':
            self._list = None
        if params[0] == 'dlgEdit':
            quota = vars.getvalue('quota', '')
            passwd = vars.getvalue('chpasswd', '')
            if vars.getvalue('action', '') == 'OK':
                if passwd and passwd != vars.getvalue('chpasswdb',''):
                    self.put_message('err', 'Passwords must match')
                else:
                    try:
                        self._mc.edit(self._edit['username'], self._edit['domain'], 
                            quota, passwd)
                        self.put_message('info', 'Mailbox edited successfully')
                    except Exception, e:
                        self.app.log.error('Mailbox %s@%s could not be edited. Error: %s' % (self._edit['username'],self._edit['domain'],str(e)))
                        self.put_message('err', 'Mailbox could not be edited')
            self._edit = None
        if params[0].startswith('dlgAuth'):
            if vars.getvalue('action', '') == 'OK':
                login = vars.getvalue('value', '')
                try:
                    apis.databases(self.app).get_interface('MariaDB').connect(
                        store=self.app.session['dbconns'],
                        passwd=login)
                except DBAuthFail, e:
                    self.put_message('err', str(e))

########NEW FILE########
__FILENAME__ = main
from genesis.com import Plugin, implements
from genesis import apis
from genesis.utils import shell
from genesis.plugins.users.backend import UsersBackend

import hashlib
import json
import nginx
import os
import random


class Etherpad(Plugin):
    implements(apis.webapps.IWebapp)
    name = 'Etherpad'
    icon = 'gen-pen'

    addtoblock = [
        nginx.Location('/',
            nginx.Key('proxy_pass', 'http://127.0.0.1:2369'),
            nginx.Key('proxy_set_header', 'X-Real-IP $remote_addr'),
            nginx.Key('proxy_set_header', 'Host $host'),
            nginx.Key('proxy_buffering', 'off')
        )
    ]

    def pre_install(self, name, vars):
        eth_name = vars.getvalue('ether_admin', '')
        eth_pass = vars.getvalue('ether_pass', '')
        if not (eth_name and eth_pass):
            raise Exception('You must enter an admin name AND password'
                            'in the App Settings tab!')
        conn = apis.databases(self.app).get_dbconn('MariaDB')
        apis.databases(self.app).get_interface('MariaDB').validate(
            name, name, eth_pass, conn
        )

    def post_install(self, name, path, vars):
        users = UsersBackend(self.app)
        users.add_user('etherpad')

        # Request a database and user to interact with it
        dbase = apis.databases(self.app).get_interface('MariaDB')
        conn = apis.databases(self.app).get_dbconn('MariaDB')
        dbname = name
        session_key = hashlib.sha1(str(random.random())).hexdigest()
        dbpass = session_key[0:8]
        dbase.add(dbname, conn)
        dbase.usermod(dbname, 'add', dbpass, conn)
        dbase.chperm(dbname, dbname, 'grant', conn)

        # Create/Edit the config file
        cfg = {
            "title": "Etherpad",
            "favicon": "favicon.ico",
            "ip": "127.0.0.1",
            "port": "2369",
            "sessionKey": session_key,
            "dbType": "mysql",
            "dbSettings": {
                "user": dbname,
                "host": "localhost",
                "password": dbpass,
                "database": dbname
            },
            "defaultPadText": (
                "Welcome to Etherpad on arkOS!\n\nThis pad text is "
                "synchronized as you type, so that everyone viewing this page "
                "sees the same text. This allows you to collaborate seamlessly "
                "on documents!\n\nGet involved with Etherpad at "
                "http://etherpad.org, or with arkOS at http://arkos.io\n"
            ),
            "requireSession": False,
            "editOnly": False,
            "minify": True,
            "maxAge": 60 * 60 * 6,
            "abiword": None,
            "requireAuthentication": False,
            "requireAuthorization": False,
            "trustProxy": True,
            "disableIPlogging": False,
            "socketTransportProtocols": [
                "xhr-polling", "jsonp-polling", "htmlfile"
            ],
            "loglevel": "INFO",
            "logconfig": {
                "appenders": [
                    {"type": "console"}
                ]
            },
            "users": {
                vars.getvalue('ether_admin'): {
                    "password": vars.getvalue('ether_pass'),
                    "is_admin": True
                },
            },

        }
        with open(os.path.join(path, 'settings.json'), 'w') as f:
            json.dump(cfg, f, indent=4)

        # node-gyp needs the HOME variable to be set
        with open(os.path.join(path, 'bin/run.sh')) as f:
            run_script = f.readlines()
        run_script.insert(1, "export HOME=%s" % path)
        with open(os.path.join(path, 'bin/run.sh'), 'w') as f:
            f.writelines(run_script)

        # Install deps right away
        if not shell(os.path.join(path, 'bin/installDeps.sh') + ' || exit 1'):
            raise RuntimeError(
                "Etherpad dependencies could not be installed.")

        # Install selected plugins
        mods = list(                            # e.g. "ep_plugin/ep_adminpads"
            str(var).split("/")[1]              #                 ^^^^^^^^^^^^
            for var in vars
            if var.startswith('ep_plugin/') and int(vars.getvalue(var))
        )
        if mods:
            mod_inst_path = os.path.join(path, "node_modules")
            if not os.path.exists(mod_inst_path):
                os.mkdir(mod_inst_path)
            nodectl = apis.langassist(self.app).get_interface('NodeJS')
            nodectl.install(*mods, install_path=mod_inst_path)

        # Make supervisor entry
        s = apis.orders(self.app).get_interface('supervisor')
        if s:
            s[0].order(
                'new',
                'etherpad',
                'program',
                [
                    ('directory', path),
                    ('user', 'etherpad'),
                    ('command', os.path.join(path, 'bin/run.sh')),
                    ('autostart', 'true'), ('autorestart', 'true'),
                    ('stdout_logfile', '/var/log/etherpad.log'),
                    ('stderr_logfile', '/var/log/etherpad.log')
                ]
            )

        # Change owner of everything in the etherpad path
        shell('chown -R etherpad ' + path)
        #TODO: user auth with nginx??

    def pre_remove(self, name, path):
        with open(os.path.join(path, 'settings.json')) as f:
            cfg = json.load(f)
            dbname = cfg["dbSettings"]["user"]
        dbase = apis.databases(self.app).get_interface('MariaDB')
        conn = apis.databases(self.app).get_dbconn('MariaDB')
        dbase.remove(dbname, conn)
        dbase.usermod(dbname, 'del', '', conn)

    def post_remove(self, name):
        users = UsersBackend(self.app)
        users.del_user('etherpad')
        s = apis.orders(self.app).get_interface('supervisor')
        if s:
            s[0].order('del', 'etherpad')

    def ssl_enable(self, path, cfile, kfile):
        name = os.path.basename(path)
        n = nginx.loadf('/etc/nginx/sites-available/%s' % name)
        for x in n.servers:
            if x.filter('Location', '/'):
                x.remove(x.filter('Location', '/')[0])
                self.addtoblock[0].add(
                    nginx.Key('proxy_set_header',
                              'X-Forwarded-For $proxy_add_x_forwarded_for'),
                    nginx.Key('proxy_set_header',
                              'X-Forwarded-Proto $scheme'),
                )
                x.add(self.addtoblock[0])
                nginx.dumpf(n, '/etc/nginx/sites-available/%s' % name)

    def ssl_disable(self, path):
        name = os.path.basename(path)
        n = nginx.loadf('/etc/nginx/sites-available/%s' % name)
        for x in n.servers:
            if x.filter('Location', '/'):
                x.remove(x.filter('Location', '/')[0])
                x.add(self.addtoblock[0])
                nginx.dumpf(n, '/etc/nginx/sites-available/%s' % name)


########NEW FILE########
__FILENAME__ = main
from genesis.api import *
from genesis.ui import *
from genesis.com import Plugin, Interface, implements
from genesis import apis
from genesis.utils import shell
from genesis.plugins.users.backend import UsersBackend

import json
import nginx
import os


class Ghost(Plugin):
    implements(apis.webapps.IWebapp)
    name = 'Ghost'
    icon = 'gen-earth'

    addtoblock = [
        nginx.Location('/',
            nginx.Key('proxy_pass', 'http://127.0.0.1:2368'),
            nginx.Key('proxy_set_header', 'X-Real-IP $remote_addr'),
            nginx.Key('proxy_set_header', 'Host $host'),
            nginx.Key('proxy_buffering', 'off')
            )
        ]

    def pre_install(self, name, vars):
        pass

    def post_install(self, name, path, vars):
        nodectl = apis.langassist(self.app).get_interface('NodeJS')
        users = UsersBackend(self.app)

        if not os.path.exists('/usr/bin/python') and os.path.exists('/usr/bin/python'):
            os.symlink('/usr/bin/python2', '/usr/bin/python')

        d = json.loads(open(os.path.join(path, 'package.json'), 'r').read())
        del d['dependencies']['bcryptjs']
        d['dependencies']['bcrypt'] = '0.7.8'
        open(os.path.join(path, 'package.json'), 'w').write(json.dumps(d))
        d = open(os.path.join(path, 'core/server/models/user.js'), 'r').read()
        d = d.replace('bcryptjs', 'bcrypt')
        open(os.path.join(path, 'core/server/models/user.js'), 'w').write(d)

        nodectl.install_from_package(path, 'production')
        users.add_user('ghost')

        s = apis.orders(self.app).get_interface('supervisor')
        if s:
            s[0].order('new', 'ghost', 'program', 
                [('directory', path), ('user', 'ghost'), 
                ('command', 'node %s'%os.path.join(path, 'index.js')),
                ('autostart', 'true'), ('autorestart', 'true'),
                ('environment', 'NODE_ENV="production"'),
                ('stdout_logfile', '/var/log/ghost.log'),
                ('stderr_logfile', '/var/log/ghost.log')])

        addr = vars.getvalue('addr', 'localhost')
        port = vars.getvalue('port', '80')

        # Get Mail settings
        mail_settings = {
            'transport' : vars.getvalue('ghost-transport', ''),
            'service' : vars.getvalue('ghost-service', ''),
            'mail_user' : vars.getvalue('ghost-mail-user', ''),
            'mail_pass' : vars.getvalue('ghost-mail-pass', ''),
            'from_address' : vars.getvalue('ghost-from-address', '')
        }

        # Create/Edit the Ghost config file
        f = open(os.path.join(path, 'config.example.js'), 'r').read()
        with open(os.path.join(path, 'config.js'), 'w') as config_file:
            f = f.replace('http://my-ghost-blog.com', 'http://'+addr+(':'+port if port != '80' else''))
            if len(set(mail_settings.values())) != 1 and\
               mail_settings['transport'] != '':
                # If the mail settings exist, add them
                f = f.replace(
                    "mail: {},",\
                    'mail: {\n'
                    "\tfromaddress: '" + mail_settings['from_address'] + "',\n"
                    "\ttransport: '" + mail_settings['transport'] + "',\n"
                    "\t\toptions: {\n"
                    "\t\t\tservice: '" + mail_settings['service'] + "',\n"
                    "\t\t\tauth: {\n"
                    "\t\t\t\tuser: '" + mail_settings['mail_user'] + "',\n"
                    "\t\t\t\tpass: '" + mail_settings['mail_pass'] + "'\n"
                    "\t\t\t}\n"
                    "\t\t}\n"
                    "},\n"
                )
            config_file.write(f)
            config_file.close()

        # Finally, make sure that permissions are set so that Ghost
        # can make adjustments and save plugins when need be.
        shell('chown -R ghost ' + path)

    def pre_remove(self, name, path):
        pass

    def post_remove(self, name):
        users = UsersBackend(self.app)
        users.del_user('ghost')
        s = apis.orders(self.app).get_interface('supervisor')
        if s:
            s[0].order('del', 'ghost')

    def ssl_enable(self, path, cfile, kfile):
        name = os.path.basename(path)
        n = nginx.loadf('/etc/nginx/sites-available/%s'%name)
        for x in n.servers:
            if x.filter('Location', '/'):
                x.remove(x.filter('Location', '/')[0])
                self.addtoblock[0].add(
                    nginx.Key('proxy_set_header', 'X-Forwarded-For $proxy_add_x_forwarded_for'),
                    nginx.Key('proxy_set_header', 'X-Forwarded-Proto $scheme'),
                )
                x.add(self.addtoblock[0])
                nginx.dumpf(n, '/etc/nginx/sites-available/%s'%name)
        f = open(os.path.join(path, 'config.js'), 'r').read()
        with open(os.path.join(path, 'config.js'), 'w') as config_file:
            f = f.replace('production: {\n        url: \'http://', 
                'production: {\n        url: \'https://')
            config_file.write(f)
            config_file.close()
        s = apis.orders(self.app).get_interface('supervisor')
        if s:
            s[0].order('rel', 'ghost')

    def ssl_disable(self, path):
        name = os.path.basename(path)
        n = nginx.loadf('/etc/nginx/sites-available/%s'%name)
        for x in n.servers:
            if x.filter('Location', '/'):
                x.remove(x.filter('Location', '/')[0])
                x.add(self.addtoblock[0])
                nginx.dumpf(n, '/etc/nginx/sites-available/%s'%name)
        f = open(os.path.join(path, 'config.js'), 'r').read()
        with open(os.path.join(path, 'config.js'), 'w') as config_file:
            f = f.replace('production: {\n        url: \'https://', 
                'production: {\n        url: \'http://')
            config_file.write(f)
            config_file.close()
        s = apis.orders(self.app).get_interface('supervisor')
        if s:
            s[0].order('rel', 'ghost')

########NEW FILE########
__FILENAME__ = main
from genesis.api import *
from genesis.ui import *
from genesis.com import Plugin, Interface, implements
from genesis import apis
from genesis.utils import shell, shell_cs

import re
import nginx
import os


class Jekyll(Plugin):
	implements(apis.webapps.IWebapp)

	addtoblock = []

	def pre_install(self, name, vars):
		rubyctl = apis.langassist(self.app).get_interface('Ruby')
		rubyctl.install_gem('jekyll', 'rdiscount')

	def post_install(self, name, path, vars):
		# Make sure the webapps config points to the _site directory and generate it.
		c = nginx.loadf(os.path.join('/etc/nginx/sites-available', name))
		for x in c.servers:
			if x.filter('Key', 'root'):
				x.filter('Key', 'root')[0].value = os.path.join(path, '_site')
		nginx.dumpf(c, os.path.join('/etc/nginx/sites-available', name))
		s = shell_cs('jekyll build --source '+path+' --destination '+os.path.join(path, '_site'), stderr=True)
		if s[0] != 0:
			raise Exception('Jekyll failed to build: %s'%str(s[1]))

		# Return an explicatory message.
		return 'Jekyll has been setup, with a sample site at '+path+'. Modify these files as you like. To learn how to use Jekyll, visit http://jekyllrb.com/docs/usage. After making changes, click the Configure button next to the site, then "Regenerate Site" to bring your changes live.'

	def pre_remove(self, name, path):
		pass

	def post_remove(self, name):
		pass

	def ssl_enable(self, path, cfile, kfile):
		pass

	def ssl_disable(self, path):
		pass

	def regenerate_site(self, site):
		s = shell_cs('jekyll build --source '+site.path.rstrip('_site')+' --destination '+os.path.join(site.path), stderr=True)
		if s[0] != 0:
			raise Exception('Jekyll failed to build: %s'%str(s[1]))

########NEW FILE########
__FILENAME__ = main
import os

from genesis.ui import *
from genesis.api import *
from genesis import apis
from genesis.com import Plugin, Interface, implements
from genesis.utils import shell, shell_cs


class NodeJS(Plugin):
    implements(apis.langassist.ILangMgr)
    name = 'NodeJS'

    def install(self, *mods, **kwargs):
        cd = ('cd %s;' % kwargs['install_path']) if 'install_path' in kwargs else ''
        s = shell_cs('%s npm install %s%s' % (cd, ' '.join(x for x in mods), (' --'+' --'.join(x for x in kwargs['opts']) if kwargs.has_key('opts') else '')), stderr=True)
        if s[0] != 0:
            self.app.log.error('Failed to install %s via npm; log output follows:\n%s'%(' '.join(x for x in mods),s[1]))
            raise Exception('Failed to install %s via npm, check logs for info'%' '.join(x for x in mods))

    def remove(self, *mods):
        s = shell_cs('npm uninstall %s' % ' '.join(x for x in mods), stderr=True)
        if s[0] != 0:
            self.app.log.error('Failed to remove %s via npm; log output follows:\n%s'%(' '.join(x for x in mods),s[1]))
            raise Exception('Failed to remove %s via npm, check logs for info'%' '.join(x for x in mods))

    def install_from_package(self, path, stat='production'):
        s = shell_cs('cd %s; npm install %s' % (path, '--'+stat if stat else ''), stderr=True, env={'HOME': '/root'})
        if s[0] != 0:
            self.app.log.error('Failed to install %s via npm; log output follows:\n%s'%(path,s[1]))
            raise Exception('Failed to install %s via npm, check logs for info'%path)

########NEW FILE########
__FILENAME__ = config
from genesis.api import ModuleConfig
from main import *


class GeneralConfig(ModuleConfig):
    target = NotepadPlugin
    platform = ['any']
    
    labels = {
        'dir': 'Initial directory'
    }
    
    dir = '/etc'
   

########NEW FILE########
__FILENAME__ = main
import os

from genesis.ui import *
from genesis.com import implements
from genesis.api import *
from genesis.utils import shell, enquote, BackgroundProcess
from genesis.plugins.core.api import *
from genesis.utils import *


class NotepadPlugin(CategoryPlugin):
    text = 'Notepad'
    iconfont = 'gen-file-2'
    folder = 'tools'

    def on_session_start(self):
        self._roots = []
        self._files = []
        self._data = []
        self.add_tab()

        self._favs = []

        if self.app.config.has_option('notepad', 'favs'):
            self._favs = self.app.config.get('notepad', 'favs').split('|')

    def add_tab(self):
        self._tab = len(self._roots)
        self._roots.append(self.app.get_config(self).dir)
        self._files.append(None)
        self._data.append(None)

    def open(self, path):
        self.add_tab()
        data = open(path).read()
        self._files[self._tab] = path
        self._data[self._tab] = data

    def get_ui(self):
        mui = self.app.inflate('notepad:main')
        tabs = UI.TabControl(active=self._tab,test='test')
        mui.append('main', tabs)

        idx = 0
        for root in self._roots:
            file = self._files[idx]
            data = self._data[idx]

            ui = self.app.inflate('notepad:tab')
            tabs.add(file or root, ui, id=str(idx))

            favs = ui.find('favs')
            files = ui.find('files')

            for f in self._favs:
                files.append(
                    UI.ListItem(
                        UI.HContainer(
                            UI.IconFont(iconfont='gen-bookmark-2'),
                            UI.Label(text=f),
                        ),
                        id='*'+str(self._favs.index(f))+'/%i'%idx,
                        active=f==file
                    )
                  )

            if root != '/':
                files.append(
                    UI.ListItem(
                        UI.HContainer(
                            UI.IconFont(iconfont='gen-folder'),
                            UI.Label(text='..'),
                        ),
                        id='<back>/%i'%idx,
                        active=False,
                    )
                )

            for p in sorted(os.listdir(root)):
                path = os.path.join(root, p)
                if os.path.isdir(path):
                    files.append(
                        UI.ListItem(
                            UI.HContainer(
                                UI.IconFont(iconfont='gen-folder'),
                                UI.Label(text=p),
                            ),
                            id=p+'/%i'%idx
                        )
                      )

            for p in sorted(os.listdir(root)):
                path = os.path.join(root, p)
                if not os.path.isdir(path):
                    files.append(
                        UI.ListItem(
                            UI.IconFont(iconfont='gen-file'),
                            UI.Label(text=p),
                            id=p+'/%i'%idx,
                            active=path==file
                        )
                      )

            ui.find('data').set('name', 'data/%i'%idx)
            if file is not None:
                ui.find('data').set('value', data)
            ui.find('data').set('id', 'data%i'%idx)

            fbtn = ui.find('btnFav')
            ui.find('btnSave').set('action', 'save/%i'%idx)
            ui.find('btnClose').set('action', 'close/%i'%idx)
            if file is not None:
                if not file in self._favs:
                    fbtn.set('text', 'Bookmark')
                    fbtn.set('action', 'fav/%i'%idx)
                    fbtn.set('iconfont', 'gen-bubble-plus')
                else:
                    fbtn.set('text', 'Unbookmark')
                    fbtn.set('action', 'unfav/%i'%idx)
                    fbtn.set('iconfont', 'gen-bubble-minus')
            else:
                ui.remove('btnSave')
                ui.remove('btnFav')
                if len(self._roots) == 1:
                    ui.remove('btnClose')

            idx += 1


        tabs.add("+", None, id='newtab', form='frmEdit')
        return mui

    @event('listitem/click')
    def on_list_click(self, event, params, vars=None):
        self._tab = int(params[1])
        if params[0] == '<back>':
            params[0] = '..'
        if params[0].startswith('*'):
            params[0] = self._favs[int(params[0][1:])]

        p = os.path.abspath(os.path.join(self._roots[self._tab], params[0]))
        if os.path.isdir(p):
            self._roots[self._tab] = p
        else:
            try:
                data = open(p).read()
                self._files[self._tab] = p
                self._data[self._tab] = data
            except:
                self.put_message('warn', 'Cannot open %s'%p)

    @event('button/click')
    def on_button(self, event, params, vars=None):
        if params[0] == 'btnClose':
            self._file = None

    @event('form/submit')
    def on_submit(self, event, params, vars=None):
        if vars.getvalue('action', None) == 'newtab':
            self.add_tab()

        for idx in range(0,len(self._roots)):
            if idx >= len(self._roots): # closed
                break

            self._data[idx] = vars.getvalue('data/%i'%idx, None)
            if vars.getvalue('action', None) == 'save/%i'%idx:
                self._tab = idx
                if self._files[idx] is not None:
                    open(self._files[idx], 'w').write(self._data[idx])
                    self.put_message('info', 'Saved')
            if vars.getvalue('action', '') == 'fav/%i'%idx:
                self._tab = idx
                self._favs.append(self._files[idx])
            if vars.getvalue('action', '') == 'unfav/%i'%idx:
                self._tab = idx
                self._favs.remove(self._files[idx])
            if vars.getvalue('action', '') == 'close/%i'%idx:
                self._tab = 0
                del self._roots[idx]
                del self._files[idx]
                del self._data[idx]
                if len(self._roots) == 0:
                    self.add_tab()
            self.app.config.set('notepad', 'favs', '|'.join(self._favs))
            self.app.config.save()


class NotepadListener(Plugin):
    implements(apis.orders.IListener)
    id = 'notepad'
    cat = 'notepadplugin'

    def order(self, op, path):
        if op == 'open':
            NotepadPlugin(self.app).open(path)

########NEW FILE########
__FILENAME__ = main
from genesis.api import *
from genesis.ui import *
from genesis.com import Plugin, Interface, implements
from genesis import apis
from genesis.utils import shell, shell_cs, download, detect_architecture

import hashlib
import errno
import nginx
import os
import random
import shutil


class ownCloud(Plugin):
    implements(apis.webapps.IWebapp)

    addtoblock = [
        nginx.Key('error_page', '403 = /core/templates/403.php'),
        nginx.Key('error_page', '404 = /core/templates/404.php'),
        nginx.Key('client_max_body_size', '10G'),
        nginx.Key('fastcgi_buffers', '64 4K'),
        nginx.Key('rewrite', '^/caldav(.*)$ /remote.php/caldav$1 redirect'),
        nginx.Key('rewrite', '^/carddav(.*)$ /remote.php/carddav$1 redirect'),
        nginx.Key('rewrite', '^/webdav(.*)$ /remote.php/webdav$1 redirect'),
        nginx.Location('= /robots.txt',
            nginx.Key('allow', 'all'),
            nginx.Key('log_not_found', 'off'),
            nginx.Key('access_log', 'off')
            ),
        nginx.Location('~ ^/(data|config|\.ht|db_structure\.xml|README)',
            nginx.Key('deny', 'all')
            ),
        nginx.Location('/',
            nginx.Key('rewrite', '^/.well-known/host-meta /public.php?service=host-meta last'),
            nginx.Key('rewrite', '^/.well-known/host-meta.json /public.php?service=host-meta-json last'),
            nginx.Key('rewrite', '^/.well-known/carddav /remote.php/carddav/ redirect'),
            nginx.Key('rewrite', '^/.well-known/caldav /remote.php/caldav/ redirect'),
            nginx.Key('rewrite', '^(/core/doc/[^\/]+/)$ $1/index.html'),
            nginx.Key('try_files', '$uri $uri/ index.php')
            ),
        nginx.Location('~ ^(.+?\.php)(/.*)?$',
            nginx.Key('try_files', '$1 = 404'),
            nginx.Key('include', 'fastcgi_params'),
            nginx.Key('fastcgi_param', 'SCRIPT_FILENAME $document_root$1'),
            nginx.Key('fastcgi_param', 'PATH_INFO $2'),
            nginx.Key('fastcgi_pass', 'unix:/run/php-fpm/php-fpm.sock'),
            nginx.Key('fastcgi_read_timeout', '900s')
            ),
        nginx.Location('~* ^.+\.(jpg|jpeg|gif|bmp|ico|png|css|js|swf)$',
            nginx.Key('expires', '30d'),
            nginx.Key('access_log', 'off')
            )
        ]

    def pre_install(self, name, vars):
        dbname = vars.getvalue('oc-dbname', '')
        dbpasswd = vars.getvalue('oc-dbpasswd', '')
        conn = apis.databases(self.app).get_dbconn('MariaDB')
        if dbname and dbpasswd:
            apis.databases(self.app).get_interface('MariaDB').validate(
                dbname, dbname, dbpasswd, conn)
        elif dbname:
            raise Exception('You must enter a database password if you specify a database name!')
        elif dbpasswd:
            raise Exception('You must enter a database name if you specify a database password!')
        if vars.getvalue('oc-username', '') == '':
            raise Exception('Must choose an ownCloud username')
        elif vars.getvalue('oc-logpasswd', '') == '':
            raise Exception('Must choose an ownCloud password')

    def post_install(self, name, path, vars):
        phpctl = apis.langassist(self.app).get_interface('PHP')
        datadir = ''
        dbase = apis.databases(self.app).get_interface('MariaDB')
        conn = apis.databases(self.app).get_dbconn('MariaDB')
        if vars.getvalue('oc-dbname', '') == '':
            dbname = name
        else:
            dbname = vars.getvalue('oc-dbname')
        secret_key = hashlib.sha1(str(random.random())).hexdigest()
        if vars.getvalue('oc-dbpasswd', '') == '':
            passwd = secret_key[0:8]
        else:
            passwd = vars.getvalue('oc-dbpasswd')
        username = vars.getvalue('oc-username')
        logpasswd = vars.getvalue('oc-logpasswd')

        # Request a database and user to interact with it
        dbase.add(dbname, conn)
        dbase.usermod(dbname, 'add', passwd, conn)
        dbase.chperm(dbname, dbname, 'grant', conn)

        # Set ownership as necessary
        if not os.path.exists(os.path.join(path, 'data')):
            os.makedirs(os.path.join(path, 'data'))
        shell('chown -R http:http '+os.path.join(path, 'apps'))
        shell('chown -R http:http '+os.path.join(path, 'data'))
        shell('chown -R http:http '+os.path.join(path, 'config'))

        # If there is a custom path for the data directory, do the magic
        if vars.getvalue('oc-ddir', '') != '':
            datadir = vars.getvalue('oc-ddir')
            if not os.path.exists(os.path.join(datadir if datadir else path, 'data')):
                os.makedirs(os.path.join(datadir if datadir else path, 'data'))
            shell('chown -R http:http '+os.path.join(datadir if datadir else path, 'data'))
            phpctl.open_basedir('add', datadir)

        # Create ownCloud automatic configuration file
        f = open(os.path.join(path, 'config', 'autoconfig.php'), 'w')
        f.write(
            '<?php\n'
            '   $AUTOCONFIG = array(\n'
            '   "adminlogin" => "'+username+'",\n'
            '   "adminpass" => "'+logpasswd+'",\n'
            '   "dbtype" => "mysql",\n'
            '   "dbname" => "'+dbname+'",\n'
            '   "dbuser" => "'+dbname+'",\n'
            '   "dbpass" => "'+passwd+'",\n'
            '   "dbhost" => "localhost",\n'
            '   "dbtableprefix" => "",\n'
            '   "directory" => "'+os.path.join(datadir if datadir else path, 'data')+'",\n'
            '   );\n'
            '?>\n'
            )
        f.close()
        shell('chown http:http '+os.path.join(path, 'config', 'autoconfig.php'))

        # Make sure that the correct PHP settings are enabled
        phpctl.enable_mod('mysql', 'pdo_mysql', 'zip', 'gd',
            'iconv', 'openssl', 'xcache')
        
        # Make sure xcache has the correct settings, otherwise ownCloud breaks
        f = open('/etc/php/conf.d/xcache.ini', 'w')
        oc = ['extension=xcache.so\n',
            'xcache.size=64M\n',
            'xcache.var_size=64M\n',
            'xcache.admin.enable_auth = Off\n',
            'xcache.admin.user = "admin"\n',
            'xcache.admin.pass = "'+secret_key[8:24]+'"\n']
        f.writelines(oc)
        f.close()

        # Return an explicatory message
        if detect_architecture()[1] == 'Raspberry Pi':
            return ('ownCloud takes a long time to set up on the RPi. '
            'Once you open the page for the first time, it may take 5-10 '
            'minutes for the content to appear. Please do not refresh the '
            'page.')

    def pre_remove(self, name, path):
        datadir = ''
        dbname = name
        if os.path.exists(os.path.join(path, 'config', 'config.php')):
            f = open(os.path.join(path, 'config', 'config.php'), 'r')
            for line in f.readlines():
                if 'dbname' in line:
                    data = line.split('\'')[1::2]
                    dbname = data[1]
                elif 'datadirectory' in line:
                    data = line.split('\'')[1::2]
                    datadir = data[1]
            f.close()
        elif os.path.exists(os.path.join(path, 'config', 'autoconfig.php')):
            f = open(os.path.join(path, 'config', 'autoconfig.php'), 'r')
            for line in f.readlines():
                if 'dbname' in line:
                    data = line.split('\"')[1::2]
                    dbname = data[1]
                elif 'directory' in line:
                    data = line.split('\'')[1::2]
                    datadir = data[1]
            f.close()
        dbase = apis.databases(self.app).get_interface('MariaDB')
        conn = apis.databases(self.app).get_dbconn('MariaDB')
        dbase.remove(dbname, conn)
        dbase.usermod(dbname, 'del', '', conn)
        if datadir:
            shutil.rmtree(datadir)
            phpctl.open_basedir('del', datadir)

    def post_remove(self, name):
        pass

    def ssl_enable(self, path, cfile, kfile):
        # First, force SSL in ownCloud's config file
        if os.path.exists(os.path.join(path, 'config', 'config.php')):
            px = os.path.join(path, 'config', 'config.php')
        else:
            px = os.path.join(path, 'config', 'autoconfig.php')
        ic = open(px, 'r').readlines()
        f = open(px, 'w')
        oc = []
        found = False
        for l in ic:
            if '"forcessl" =>' in l:
                l = '"forcessl" => true,\n'
                oc.append(l)
                found = True
            else:
                oc.append(l)
        if found == False:
            for x in enumerate(oc):
                if '"dbhost" =>' in x[1]:
                    oc.insert(x[0] + 1, '"forcessl" => true,\n')
        f.writelines(oc)
        f.close()

        # Next, update the ca-certificates thing to include our cert
        # (if necessary)
        if not os.path.exists('/usr/share/ca-certificates'):
            try:
                os.makedirs('/usr/share/ca-certificates')
            except OSError, e:
                if e.errno == errno.EEXIST and os.path.isdir('/usr/share/ca-certificates'):
                    pass
                else:
                    raise
        shutil.copy(cfile, '/usr/share/ca-certificates/')
        fname = cfile.rstrip('/').split('/')[-1]
        ic = open('/etc/ca-certificates.conf', 'r').readlines()
        f = open('/etc/ca-certificates.conf', 'w')
        oc = []
        for l in ic:
            if l != fname+'\n':
                oc.append(l)
        oc.append(fname+'\n')
        f.writelines(oc)
        f.close()
        shell('update-ca-certificates')

    def ssl_disable(self, path):
        if os.path.exists(os.path.join(path, 'config', 'config.php')):
            px = os.path.join(path, 'config', 'config.php')
        else:
            px = os.path.join(path, 'config', 'autoconfig.php')
        ic = open(px, 'r').readlines()
        f = open(px, 'w')
        oc = []
        found = False
        for l in ic:
            if '"forcessl" =>' in l:
                l = '"forcessl" => false,\n'
                oc.append(l)
                found = True
            else:
                oc.append(l)
        if found == False:
            for x in enumerate(oc):
                if '"dbhost" =>' in x[1]:
                    oc.insert(x[0] + 1, '"forcessl" => false,\n')
        f.writelines(oc)
        f.close()

    def show_opts_add(self, ui):
        poi_sel = []
        for x in sorted(apis.poicontrol(self.app).get_pois(), key=lambda x: x.name):
            poi_sel.append(UI.SelectOption(text=x.name, value=x.path))
        ui.appendAll('oc-ddir', *poi_sel)

########NEW FILE########
__FILENAME__ = main
import os

from genesis.ui import *
from genesis.api import *
from genesis import apis
from genesis.com import Plugin, Interface, implements
from genesis.utils import shell, shell_cs, shell_status, download


class PHP(Plugin):
    implements(apis.langassist.ILangMgr)
    name = 'PHP'

    def install_composer(self):
        cwd = os.getcwd()
        os.environ['COMPOSER_HOME'] = '/root'
        self.enable_mod('phar')
        self.open_basedir('add', '/root')
        s = shell_cs('cd /root; curl -sS https://getcomposer.org/installer | php', stderr=True)
        if s[0] != 0:
            raise Exception('Composer download/config failed. Error: %s'%str(s[1]))
        os.rename('/root/composer.phar', '/usr/local/bin/composer')
        os.chmod('/usr/local/bin/composer', 755)
        self.open_basedir('add', '/usr/local/bin')
        shell('cd %s'%cwd)

    def verify_composer(self):
        if not shell_status('which composer') == 0:
            self.install_composer()
        if not shell_status('which composer') == 0:
            raise Exception('Composer was not installed successfully.')

    def composer_install(self, path):
        self.verify_composer()
        s = shell_cs('cd %s; composer install'%path, stderr=True)
        if s[0] != 0:
            raise Exception('Composer failed to install this app\'s bundle. Error: %s'%str(s[1]))

    def enable_mod(self, *mod):
        for x in mod:
            shell('sed -i s/\;extension=%s.so/extension=%s.so/g /etc/php/php.ini'%(x,x))

    def disable_mod(self, *mod):
        for x in mod:
            shell('sed -i s/extension=%s.so/\;extension=%s.so/g /etc/php/php.ini'%(x,x))

    def open_basedir(self, op, path):
        if op == 'add':
            ic = open('/etc/php/php.ini', 'r').readlines()
            f = open('/etc/php/php.ini', 'w')
            oc = []
            for l in ic:
                if 'open_basedir = ' in l and path not in l:
                    l = l.rstrip('\n') + ':%s\n' % path
                    oc.append(l)
                else:
                    oc.append(l)
            f.writelines(oc)
            f.close()
        elif op == 'del':
            ic = open('/etc/php/php.ini', 'r').readlines()
            f = open('/etc/php/php.ini', 'w')
            oc = []
            for l in ic:
                if 'open_basedir = ' in l and path in l:
                    l = l.replace(':'+path, '')
                    l = l.replace(':'+path+'/', '')
                    oc.append(l)
                else:
                    oc.append(l)
            f.writelines(oc)
            f.close()

########NEW FILE########
__FILENAME__ = api
from genesis.com import *
from genesis.api import *
from genesis.apis import API


class PkgMan(API):
    class IPackageManager(Interface):
        def refresh(self, st):
            pass

        def get_lists(self, st):
            pass

        def search(self, q):
            pass

        def mark_install(self, st, name):
            pass

        def mark_remove(self, st, name):
            pass

        def mark_cancel(self, st, name):
            pass

        def mark_cancel_all(self, st):
            pass
    
        def apply(self, st):
            pass

        def is_busy(self):
            pass

        def get_busy_status(self):
            pass

        def get_expected_result(self, st):
            pass

        def abort(self):
            pass
            
        def get_info(self, pkg):
            pass

        def get_info_ui(self, pkg):
            pass
            
                        
    class Package(object):
        def __init__(self):
            self.name = ''
            self.version = ''
            self.state = ''
            self.description = ''


    class PackageInfo(object):
        def __init__(self):
            self.installed = ''
            self.available = ''
            self.description = ''            
    
    
    class Status(object):
        upgradeable = {}
        pending = {}
        full = {}
        

########NEW FILE########
__FILENAME__ = component
from genesis.api import *
from genesis import apis

import time


class PackageManagerComponent (Component):
    name = 'pkgman'

    def on_starting(self):
        self.status = apis.pkgman.Status()
        self.last_refresh = 0
        
        self.mgr = self.app.get_backend(apis.pkgman.IPackageManager)
            
    def get_status(self):
        if time.time() - self.last_refresh >= 5 * 60:
            self.last_refresh = time.time()
            self.mgr.refresh(self.status) 
        return self.status
        
    def refresh(self):
        self.last_refresh = 0
        return self.proxy.get_status()
        
    def run(self):
        while True:
            self.proxy.get_status()
            time.sleep(5*60 + 1)
            
    def __getattr__(self, attr):
        return getattr(self.mgr, attr)
        

########NEW FILE########
__FILENAME__ = main
import time

from genesis.ui import *
from genesis.com import implements
from genesis.api import *
from genesis.plugins.core.api import *
from genesis import apis


class PackageManagerPlugin(CategoryPlugin):
    text = 'Packages'
    iconfont = 'gen-cube'
    folder = 'advanced'

    def on_init(self):
        self.mgr = ComponentManager.get().find('pkgman')

        if self._in_progress and not self.mgr.is_busy():
            self._need_refresh = True
            self.mgr.mark_cancel_all(self._status)
            self._in_progress = False

        if self._need_refresh:
            self.mgr.refresh()
            self._need_refresh = False

        self._status = self.mgr.get_status()

    def on_session_start(self):
        self._status = None
        self._current = 'upgrades'
        self._need_refresh = False
        self._confirm_apply = False
        self._in_progress = False
        self._search = {}
        self._search_query = ''
        self._info = None

    def get_counter(self):
        c = len(ComponentManager.get().find('pkgman').get_status().upgradeable)
        if c > 0:
            return str(c)

    def _get_icon(self, p):
        r = 'gen-'
        if p in self._status.pending.keys():
            if self._status.pending[p] == 'install':
                r += 'arrow-up-2'
            else:
                r += 'minus-circle'
        else:
            if p in self._status.full.keys():
                if self._status.full[p].state == 'broken':
                    r += 'notification'
                elif p in self._status.upgradeable.keys():
                    r += 'arrow-down-2'
                else:
                    r += 'checkmark-circle'
            else:
                r += 'cube'
        return r

    def get_ui(self):
        ui = self.app.inflate('pkgman:main')

        ui.find('tabs').set('active', self._current)

        pnl = ui.find('main')

        if self._confirm_apply:
            res = UI.DT(UI.DTR(
                    UI.DTH(width=20),
                    UI.DTH(UI.Label(text='Package')),
                    header=True
                  ), width='100%', noborder=True)

            if self._confirm_apply:
                r = self.mgr.get_expected_result(self._status)
                for x in r:
                    i = 'gen-'
                    i += 'arrow-up-2' if r[x] == 'install' else 'minus-circle'
                    t = UI.DTR(
                            UI.IconFont(iconfont=i),
                            UI.Label(text=x)
                        )
                    res.append(t)

            dlg = UI.DialogBox(
                    UI.ScrollContainer(res, width=300, height=300),
                    id='dlgApply'
                  )
            pnl.append(dlg)

        if self._info is not None:
            pnl.append(self.get_ui_info())

        tbl_pkgs = ui.find('uplist')
        for p in sorted(self._status.upgradeable.keys()):
            p = self._status.upgradeable[p]
            stat = self._get_icon(p.name)
            if p.name == 'genesis':
                continue
            r = UI.DTR(
                    UI.IconFont(iconfont=stat),
                    UI.Label(text=p.name),
                    UI.Label(text=p.version),
                    UI.Label(text=p.description),
                        UI.HContainer(
                            UI.TipIcon(iconfont='gen-info', text='Info', id='info/'+p.name),
                            UI.TipIcon(iconfont='gen-minus', text='Deselect', id='cancel/'+p.name)
                                if p.name in self._status.pending else
                            UI.TipIcon(iconfont='gen-checkmark-circle', text='Select', id='upgrade/'+p.name),
                            spacing=0
                        ),
                )
            tbl_pkgs.append(r)

        tbl_pkgs = ui.find('brlist')
        for p in sorted(self._status.full.keys()):
            p = self._status.full[p]
            if p.state != 'broken': continue
            stat = self._get_icon(p.name)
            r = UI.DTR(
                    UI.IconFont(iconfont=stat),
                    UI.Label(text=p.name),
                    UI.Label(text=p.version),
                    UI.Label(text=p.description),
                        UI.HContainer(
                            UI.TipIcon(iconfont='gen-info', text='Info', id='info/'+p.name),
                            UI.TipIcon(iconfont='gen-loop-2', text='Reinstall', id='install/'+p.name),
                            UI.TipIcon(iconfont='gen-minus', text='Remove', id='remove/'+p.name),
                            spacing=0
                        ),
                )
            tbl_pkgs.append(r)

        tbl_pkgs = ui.find('selist')
        for p in self._search.keys()[:50]:
            stat = self._get_icon(p)
            r = UI.DTR(
                    UI.IconFont(iconfont=stat),
                    UI.Label(text=p),
                    UI.Label(text=self._search[p].version),
                    UI.Label(text=self._search[p].description),
                        UI.HContainer(
                            UI.TipIcon(iconfont='gen-info', text='Info', id='info/'+p) if self._search[p].state == 'installed' else None,
                            UI.TipIcon(iconfont='gen-checkmark', text='Install', id='install/'+p) if self._search[p].state == 'removed' else
                            UI.TipIcon(iconfont='gen-minus', text='Remove', id='remove/'+p),
                            spacing=0
                        ),
            )
            tbl_pkgs.append(r)
        if len(self._search.keys()) > 50:
            tbl_pkgs.append(UI.DTR(
                UI.DTD(
                    UI.Label(text='Too many packages. Try to use a more precise search query'),
                    colspan=5
                )
            ))

        tbl_pkgs = ui.find('pelist')
        for p in sorted(self._status.pending.keys()):
            stat = self._get_icon(p)
            r = UI.DTR(
                    UI.IconFont(iconfont=stat),
                    UI.Label(text=p),
                    UI.Label(),
                    UI.Label(),
                        UI.HContainer(
                            UI.TipIcon(iconfont='gen-info', text='Info', id='info/'+p),
                            UI.TipIcon(iconfont='gen-cancel-circle', text='Cancel', id='cancel/'+p),
                            spacing=0
                        ),
                )
            tbl_pkgs.append(r)

        return ui

    def get_ui_info(self):
        pkg = self._info
        info = self.mgr.get_info(pkg)
        iui = self.mgr.get_info_ui(pkg)
        ui = UI.LT(
                UI.LTR(
                    UI.LTD(
                        UI.IconFont(iconfont='gen-cube'),
                        rowspan=6
                    ),
                    UI.Label(text='Package:', bold=True),
                    UI.Label(text=pkg, bold=True)
                ),
                UI.LTR(
                    UI.Label(text='Installed:'),
                    UI.Label(text=info.installed)
                ),
                UI.LTR(
                    UI.Label(text='Available:'),
                    UI.Label(text=info.available)
                ),
                UI.LTR(
                    UI.Label(text='Description:'),
                    UI.Container(
                        UI.Label(text=info.description),
                        width=300
                    )
                ),
                UI.LTR(
                    UI.LTD(
                        iui,
                        colspan=2
                    )
                ),
                UI.LTR(
                    UI.LTD(
                        UI.HContainer(
                            UI.Button(text='(Re)install', id='install/'+pkg),
                            UI.Button(text='Remove', id='remove/'+pkg)
                        ),
                        colspan=2
                    )
                )
            )
        return UI.DialogBox(ui, id='dlgInfo')

    @event('tab/click')
    def on_li_click(self, event, params, vars=None):
        self._current = params[0]

    @event('button/click')
    def on_click(self, event, params, vars=None):
        if params[0] == 'refresh':
            self.mgr.refresh()
        if params[0] == 'getlists':
            self.mgr.get_lists()
            time.sleep(0.5)
        if params[0] == 'apply':
            self._confirm_apply = True
            time.sleep(0.5)
        if params[0] == 'install':
            self.mgr.mark_install(self._status, params[1])
            self._info = None
        if params[0] == 'remove':
            self.mgr.mark_remove(self._status, params[1])
            self._info = None
        if params[0] == 'upgrade':
            self.mgr.mark_install(self._status, params[1])
        if params[0] == 'cancel':
            self.mgr.mark_cancel(self._status, params[1])
        if params[0] == 'upgradeall':
            for p in self._status.upgradeable:
                self.mgr.mark_install(self._status, p)
        if params[0] == 'info':
            self._info = params[1]
        if params[0] == 'cancelall':
            self.mgr.mark_cancel_all(self._status)


    @event('dialog/submit')
    @event('form/submit')
    def on_dialog(self, event, params, vars=None):
        if params[0] == 'dlgApply':
            self._confirm_apply = False
            if vars.getvalue('action', '') == 'OK':
                self.mgr.apply(self._status)
                self._in_progress = True
        if params[0] == 'frmSearch':
            q = vars.getvalue('query','')
            if q != '':
                self._search = self.mgr.search(q, self._status)
            self._current = 'search'
        if params[0] == 'dlgInfo':
            self._info = None


class PackageManagerProgress(Plugin):
    implements(IProgressBoxProvider)
    title = 'Packages'
    iconfont = 'gen-cube'
    can_abort = True

    def __init__(self):
        self.mgr = self.app.get_backend(apis.pkgman.IPackageManager)

    def has_progress(self):
        try:
            return self.mgr.is_busy()
        except:
            return False

    def get_progress(self):
        return self.mgr.get_busy_status()

    def abort(self):
        self.mgr.abort()

########NEW FILE########
__FILENAME__ = pm_apt
import os
import subprocess

from genesis.com import *
from genesis import utils
from genesis import apis


class APTPackageManager(Plugin):
    implements(apis.pkgman.IPackageManager)
    platform = ['debian']

    _pending = {}

    def refresh(self, st):
        p = self._parse_apt(utils.shell('apt-get upgrade -s -qq').splitlines())
        a = self._get_all()
        st.upgradeable = {}

        for s in p:
            s = p[s]
            if s.state == 'installed':
                if a.has_key(s.name) and a[s.name].state == 'installed':
                    st.upgradeable[s.name] = a[s.name]

        st.pending = {}
        try:
            ss = open('/tmp/genesis-apt-pending.list', 'r').read().splitlines()
            for s in ss:
                s = s.split()
                try:
                    st.pending[s[1]] = s[0]
                except:
                    pass
        except:
            pass

        st.full = a

    def get_lists(self):
        utils.shell_bg('apt-get update', output='/tmp/genesis-apt-output', deleteout=True)

    def search(self, q, st):
        ss = utils.shell('apt-cache search %s' % q).splitlines()
        a = st.full
        r = {}
        for s in ss:
            s = s.split()
            r[s[0]] = apis.pkgman.Package()
            r[s[0]].name = s[0]
            r[s[0]].description = ' '.join(s[2:])
            r[s[0]].state = 'removed'
            if a.has_key(s[0]) and a[s[0]].state == 'installed':
                r[s[0]].state = 'installed'
        return r

    def mark_install(self, st, name):
        st.pending[name] = 'install'
        self._save_pending(st.pending)

    def mark_remove(self, st, name):
        st.pending[name] = 'remove'
        self._save_pending(st.pending)

    def mark_cancel(self, st, name):
        del st.pending[name]
        self._save_pending(st.pending)

    def mark_cancel_all(self, st):
        st.pending = {}
        self._save_pending(st.pending)
    
    def apply(self, st):
        cmd = 'apt-get -y --force-yes install '
        for x in st.pending:
            cmd += x + ('+ ' if st.pending[x] == 'install' else '- ')
        utils.shell_bg(cmd, output='/tmp/genesis-apt-output', deleteout=True)

    def is_busy(self):
        if utils.shell_status('pgrep apt-get') != 0: return False
        return os.path.exists('/tmp/genesis-apt-output')

    def get_busy_status(self):
        try:
            return open('/tmp/genesis-apt-output', 'r').read().splitlines()[-1]
        except:
            return ''

    def get_expected_result(self, st):
        cmd = 'apt-get -qq -s install '
        for x in st.pending:
            cmd += x + ('+ ' if st.pending[x] == 'install' else '- ')
        r = self._parse_apt(utils.shell(cmd).splitlines())
        for x in r:
            if r[x].state == 'installed':
                r[x] = 'install'
            else:
                r[x] = 'remove'
        return r

    def abort(self):
        utils.shell('pkill apt')
        utils.shell('rm /tmp/genesis-apt-output')

    def get_info(self, pkg):
        i = apis.pkgman.PackageInfo()
        ss = utils.shell('apt-cache policy '+pkg).split('\n')
        i.installed = ss[1].split(':')[1].strip()
        i.available = ss[2].split(':')[1].strip()
        ss = utils.shell('apt-cache show '+pkg).split('\n')
        while len(ss)>0 and not ss[0].startswith('Desc'):
            ss = ss[1:]
        i.description = ss[0].split(':')[1]
        ss = ss[1:]
        while len(ss)>0 and ss[0].startswith(' '):
            i.description += '\n' + ss[0][1:]
            ss = ss[1:]
        return i
        
    def get_info_ui(self, pkg):
        return None
        
    def _save_pending(self, p):
        f = open('/tmp/genesis-apt-pending.list', 'w')
        for x in p:
            f.write('%s %s\n' % (p[x], x))
        f.close()

    def _parse_apt(self, ss):
        r = {}
        for s in ss:
            s = s.split()
            try:
                if s[0] == 'Inst':
                    r[s[1]] = apis.pkgman.Package()
                    r[s[1]].name = s[1]
                    r[s[1]].version = s[2].strip('[]')
                    r[s[1]].state = 'installed'
                if s[0] == 'Purg' or s[0] == 'Remv':
                    r[s[1]] = apis.pkgman.Package()
                    r[s[1]].name = s[1]
                    r[s[1]].version = s[2].strip('[]')
                    r[s[1]].state = 'removed'
                if len(r.keys()) > 250: break
            except:
                pass
        return r

    def _get_all(self):
        ss = utils.shell('dpkg -l').splitlines()
        r = {}
        for s in ss:
            s = s.split()
            try:
                p = apis.pkgman.Package()
                p.name = s[1]
                p.version = s[2]
                if s[0][1] == 'i':
                    p.state = 'installed'
                else:
                    p.state = 'removed'
                r[p.name] = p
            except:
                pass

        return r
        

########NEW FILE########
__FILENAME__ = pm_pacman
import os
import subprocess

from genesis.com import *
from genesis import utils
from genesis import apis


class PacmanPackageManager(Plugin):
    implements(apis.pkgman.IPackageManager)
    platform = ['arch', 'arkos']

    _pending = {}

    def refresh(self, st):
        a = self._get_all()
        st.upgradeable = self._parse_pm_u(utils.shell('pacman -Qu').splitlines())

        st.pending = {}
        try:
            ss = open('/tmp/genesis-pacman-pending.list', 'r').read().splitlines()
            for s in ss:
                s = s.split()
                try:
                    st.pending[s[1]] = s[0]
                except:
                    pass
        except:
            pass

        st.full = a

    def get_lists(self):
        utils.shell_bg('pacman -Sy', output='/tmp/genesis-pacman-output', deleteout=True)

    def search(self, q, st):
        return self._parse_pm(utils.shell('pacman -Ss %s' % q).splitlines())

    def mark_install(self, st, name):
        st.pending[name] = 'install'
        self._save_pending(st.pending)

    def mark_remove(self, st, name):
        st.pending[name] = 'remove'
        self._save_pending(st.pending)

    def mark_cancel(self, st, name):
        del st.pending[name]
        self._save_pending(st.pending)

    def mark_cancel_all(self, st):
        st.pending = {}
        self._save_pending(st.pending)
    
    def apply(self, st):
        fcmd = ''
        
        cmd = 'pacman -S --noconfirm '
        a = False
        for x in st.pending:
            if st.pending[x] == 'install':
                cmd += x + ' '
                a = True
                
        if a:
            fcmd += cmd + '; '
        
        cmd = 'pacman -Rc --noconfirm '
        a = False
        for x in st.pending:
            if st.pending[x] != 'install':
                cmd += x + ' '
                a = True

        if a:
            fcmd += cmd
        
        utils.shell_bg(fcmd, output='/tmp/genesis-pacman-output', deleteout=True)

    def is_busy(self):
        if utils.shell_status('pgrep pacman') != 0: return False
        return os.path.exists('/tmp/genesis-pacman-output')

    def get_busy_status(self):
        try:
            return open('/tmp/genesis-pacman-output', 'r').read().splitlines()[-1]
        except:
            return ''

    def get_expected_result(self, st):
        r = {}

        cmd = 'pacman -Sp --noconfirm --print-format \'%n %v\' '
        a = False
        for x in st.pending:
            if st.pending[x] == 'install':
                cmd += x + ' '
                a = True
                
        if a:
            r.update(self._parse_pm_p(utils.shell(cmd).splitlines(), 'install'))
        
        cmd = 'pacman -Rpc --noconfirm --print-format \'%n %v\' '
        a = False
        for x in st.pending:
            if st.pending[x] != 'install':
                cmd += x + ' '
                a = True
                
        if a:
            r.update(self._parse_pm_p(utils.shell(cmd).splitlines(), 'remove'))
 
        return r

    def abort(self):
        utils.shell('pkill pacman')
        utils.shell('rm /tmp/genesis-pacman-output')

    def get_info(self, pkg):
        i = apis.pkgman.PackageInfo()
        ss = utils.shell('pacman -Qi '+pkg).split('\n')
        i.installed = ''
        i.available = ss[1].split(':')[1]
        while len(ss)>0 and not ss[0].startswith('Desc'):
            ss = ss[1:]
        ss[0] = ss[0].split(':')[1]
        i.description = '\n'.join(ss)
        return i

    def get_info_ui(self, pkg):
        pass
               
    def _save_pending(self, p):
        f = open('/tmp/genesis-pacman-pending.list', 'w')
        for x in p:
            f.write('%s %s\n' % (p[x], x))
        f.close()

    def _parse_pm(self, ss):
        r = {}
        while len(ss)>0:
            s = ss[0].split()
            ss.pop(0)
            try:
                if '/' in s[0]:
                    s[0] = s[0].split('/')[1]
                r[s[0]] = apis.pkgman.Package()
                r[s[0]].name = s[0]
                r[s[0]].version = s[1]
                r[s[0]].description = ''
                r[s[0]].state = 'installed' if utils.shell_status('pacman -Q '+s[0])==0 else 'removed'
                while ss[0][0] in ['\t', ' '] and len(ss)>0:
                    r[s[0]].description += ss[0]
                    ss.pop(0)
                if len(r.keys()) > 250: break
            except:
                pass
        return r

    def _parse_pm_p(self, ss, v):
        r = {}
        while len(ss)>0:
            s = ss[0].split()
            ss.pop(0)
            try:
                if '/' in s[0]:
                    s[0] = s[0].split('/')[1]
                r[s[0]] = v
                while ss[0][0] in ['\t', ' '] and len(ss)>0:
                    ss.pop(0)
                if len(r.keys()) > 250: break
            except:
                pass
        return r

    def _parse_pm_u(self, ss):
        r = {}
        for s in ss:
            s = s.split()
            try:
                if '/' in s[0]:
                    s[0] = s[0].split('/')[1]
                r[s[0]] = apis.pkgman.Package()
                r[s[0]].name = s[0]
                r[s[0]].version = s[1]
                r[s[0]].state = 'installed'
                if len(r.keys()) > 250: break
            except:
                pass
        return r

    def _get_all(self):
        ss = utils.shell('pacman -Q').splitlines()
        return self._parse_pm_u(ss)
        

########NEW FILE########
__FILENAME__ = pm_portage
import os
import subprocess
import lxml.etree

from genesis.com import *
from genesis.utils import shell, shell_bg
from genesis import apis


class PortagePackageManager(Plugin):
    implements(apis.pkgman.IPackageManager)
    platform = ['gentoo']
    _pending = {}

    def refresh(self, st):
        st.full = self.eix_parse(shell('eix \'-I*\' --xml'))
        st.upgradeable = self.eix_parse(shell('eix -u --xml'))
        st.pending = self._pending

    def get_lists(self):
        shell_bg('emerge --sync', output='/tmp/genesis-portage-output', deleteout=True)

    def search(self, q, st):
        return self.eix_parse(shell('eix --xml \'%s\''%q))

    def mark_install(self, st, name):
        st.pending[name] = 'install'

    def mark_remove(self, st, name):
        st.pending[name] = 'remove'

    def mark_cancel(self, st, name):
        del st.pending[name]

    def mark_cancel_all(self, st):
        st.pending = {}

    def apply(self, st):
        cmd = 'emerge '
        cmd2 = 'emerge --unmerge'
        for x in st.pending:
            if st.pending[x] == 'install':
                cmd += ' ' + x
            else:
                cmd2 += ' ' + x
        shell_bg('%s; %s'%(cmd,cmd2), output='/tmp/genesis-portage-output', deleteout=True)

    def is_busy(self):
        return os.path.exists('/tmp/genesis-portage-output')

    def get_busy_status(self):
        try:
            return open('/tmp/genesis-portage-output', 'r').read().splitlines()[-1]
        except:
            return ''

    def get_expected_result(self, st):
        return st.pending

    def abort(self):
        shell('pkill emerge')
        shell('rm /tmp/genesis-portage-output')

    def get_info(self, pkg):
        return self.eix_parse(shell('eix \'-I*\' --xml'))[pkg]

    def get_info_ui(self, pkg):
        return None

    def eix_parse(self, data):
        xml = lxml.etree.fromstring(data)
        r = {}

        for pkg in xml.findall('*/package'):
            try:
                p = apis.pkgman.Package()
                p.name = pkg.get('name')
                p.available = pkg.findall('version')[-1].get('id')
                if len(pkg.findall('version[@installed]')) == 0:
                    p.state = 'removed'
                else:
                    p.installed = pkg.findall('version[@installed]')[0].get('id')
                    p.version = p.installed
                p.description = pkg.find('description').text
                r[p.name] = p
                if len(r.keys()) > 250: break
            except:
                pass

        return r

########NEW FILE########
__FILENAME__ = pm_ports
import os
import subprocess

from genesis.com import *
from genesis import utils
from genesis import apis


class PortsPackageManager(Plugin):
    implements(apis.pkgman.IPackageManager)
    platform = ['freebsd']

    _pending = {}

    def refresh(self, st):
        p = utils.shell('pkg_version|grep \'<\'').split('\n')
        a = self._get_all()
        st.upgradeable = {}

        for x in p:
            try:
                s = x.split()[0]
                st.upgradeable[s] = a[s]
            except:
                pass
                
        st.pending = {}
        try:
            ss = open('/tmp/genesis-ports-pending.list', 'r').read().splitlines()
            for s in ss:
                s = s.split()
                try:
                    st.pending[s[1]] = s[0]
                except:
                    pass
        except:
            pass

        st.full = a

    def get_lists(self):
        utils.shell_bg('portsnap fetch', output='/tmp/genesis-ports-output', deleteout=True)

    def search(self, q, st):
        ss = utils.shell('cd /usr/ports; make search name=%s' % q).splitlines()
        a = st.full
        r = {}
        while len(ss)>0:
            if ss[0].startswith('Port'):
                pkg = apis.pkgman.Package()            
                pkg.name = ss[0].split()[1].split('-')[0]
                pkg.state = 'removed'
                if a.has_key(pkg.name) and a[pkg.name].state == 'installed':
                    pkg.state = 'installed'
                r[pkg.name] = pkg
            if ss[0].startswith('Info'):
                pkg.description = ' '.join(ss[0].split()[1:])
            ss = ss[1:]
        return r

    def mark_install(self, st, name):
        st.pending[name] = 'install'
        self._save_pending(st.pending)

    def mark_remove(self, st, name):
        st.pending[name] = 'remove'
        self._save_pending(st.pending)

    def mark_cancel(self, st, name):
        del st.pending[name]
        self._save_pending(st.pending)

    def mark_cancel_all(self, st):
        st.pending = {}
        self._save_pending(st.pending)
    
    def apply(self, st):
        cmd = 'portupgrade -R'
        cmd2 = 'pkg_deinstall -r'
        for x in st.pending:
            if st.pending[x] == 'install':
                cmd += ' ' + x
            else:
                cmd2 += ' ' + x
        utils.shell_bg('%s; %s'%(cmd,cmd2), output='/tmp/genesis-ports-output', deleteout=True)

    def is_busy(self):
        return os.path.exists('/tmp/genesis-ports-output')

    def get_busy_status(self):
        try:
            return open('/tmp/genesis-ports-output', 'r').read().splitlines()[-1]
        except:
            return ''

    def get_expected_result(self, st):
        cmd = 'portupgrade -Rn'
        cmd2 = 'pkg_deinstall -nr'
        for x in st.pending:
            if st.pending[x] == 'install':
                cmd += ' ' + x
            else:
                cmd2 += ' ' + x

        r = utils.shell('%s; %s | grep \'[+-] \''%(cmd,cmd2)).splitlines()
        res = {}
        for x in r:
            s = x.split()
            if not s[0] in ['+', '-']:
                continue
            name = '-'.join(s[-1].split('-')[:-1])[1:]
            if s[0] == '+':
                res[name] = 'install'
            else:
                res[name] = 'remove'
        return res

    def abort(self):
        utils.shell('pkill make')
        utils.shell('rm /tmp/genesis-ports-output')
        
    def get_info(self, pkg):
        i = apis.pkgman.PackageInfo()
        ss = utils.shell('pkg_info \'%s-*\''%pkg).split('\n')
        i.installed = ''
        i.available = ss[0].split('-')[-1][:-1]
        while len(ss)>0 and not ss[0].startswith('Desc'):
            ss = ss[1:]
        ss = ss[1:]
        i.description = '\n'.join(ss)
        return i
        
    def get_info_ui(self, pkg):
        return None

    def _save_pending(self, p):
        f = open('/tmp/genesis-ports-pending.list', 'w')
        for x in p:
            f.write('%s %s\n' % (p[x], x))
        f.close()

    def _get_all(self):
        ss = utils.shell('pkg_info').splitlines()
        r = {}
        for s in ss:
            s = s.split()
            try:
                p = apis.pkgman.Package()
                nv = s[0].split('-')
                p.name = '-'.join(nv[0:-1])
                p.version = nv[-1]
                p.description = ' '.join(s[1:])
                p.state = 'installed'
                r[p.name] = p
                if len(r.keys()) > 250: break
            except:
                pass

        return r
        

########NEW FILE########
__FILENAME__ = pm_yum
import os
import subprocess

from genesis.com import *
from genesis import utils
from genesis import apis


class YumPackageManager(Plugin):
    implements(apis.pkgman.IPackageManager)
    platform = ['centos', 'fedora']

    _pending = {}

    def refresh(self, st):
        p = self._parse_yum(utils.shell('yum -C -q -d0 -e0 check-update').splitlines())
        a = self._get_all()
        st.upgradeable = {}

        for s in p:
            s = p[s]
            if s.state == 'installed':
                if a.has_key(s.name) and a[s.name].state == 'installed':
                    st.upgradeable[s.name] = a[s.name]

        st.pending = {}
        try:
            ss = open('/tmp/genesis-yum-pending.list', 'r').read().splitlines()
            for s in ss:
                s = s.split()
                try:
                    st.pending[s[1]] = s[0]
                except:
                    pass
        except:
            pass

        st.full = a

    def get_lists(self):
        utils.shell_bg('yum check-update', output='/tmp/genesis-yum-output', deleteout=True)

    def search(self, q, st):
        ss = utils.shell('yum -q -C -d0 -e0 search %s' % q).splitlines()
        a = st.full
        r = {}
        for s in ss:
            s = s.split()
            if s[0].startswith('===='):
                continue
            else:
                r[s[0]] = apis.pkgman.Package()
                r[s[0]].name = s[0]
                r[s[0]].description = ' '.join(s[2:])
                r[s[0]].state = 'removed'
                if a.has_key(s[0]) and a[s[0]].state == 'installed':
                    r[s[0]].state = 'installed'
        return r

    def mark_install(self, st, name):
        st.pending[name] = 'install'
        self._save_pending(st.pending)

    def mark_remove(self, st, name):
        st.pending[name] = 'remove'
        self._save_pending(st.pending)

    def mark_cancel(self, st, name):
        del st.pending[name]
        self._save_pending(st.pending)

    def mark_cancel_all(self, st):
        st.pending = {}
        self._save_pending(st.pending)

    def apply(self, st):
        cmd = 'yum -y install '
        for x in st.pending:
            cmd += x + (' ' if st.pending[x] == 'install' else ' ')
        utils.shell_bg(cmd, output='/tmp/genesis-yum-output', deleteout=True)

    def is_busy(self):
        if utils.shell_status('ps ax | grep \"/usr/bin/python /usr/bin/yum\" | grep -v \"grep /usr/bin/python /usr/bin/yum\" | awk \'{print $1}\'') != 0: return False
        return os.path.exists('/tmp/genesis-yum-output')

    def get_busy_status(self):
        try:
            return open('/tmp/genesis-yum-output', 'r').read().splitlines()[-1]
        except:
            return ''

    def get_expected_result(self, st):
        return st.pending

    def abort(self):
        utils.shell('killall -9 yum')
        utils.shell('rm /tmp/genesis-yum-output')

    def get_info(self, pkg):
        i = apis.pkgman.PackageInfo()
        ss = utils.shell('yum -C -d0 -e0 info '+pkg).split('\n')

        section = ''
        dinst = {}
        davail = {}
        lk = None

        for s in ss:
            if not ':' in s:
                section = s
            else:
                k,v = s.split(':', 1)
                k = k.strip()
                v = v.strip()
                if k == '':
                    k = lk
                if section.startswith('Installed'):
                    if k in dinst:
                        dinst[k] += '\n' + v
                    else:
                        dinst[k] = v
                else:
                    if k in davail:
                        davail[k] += '\n' + v
                    else:
                        davail[k] = v
                lk = k

        i.installed = dinst['Version']
        try:
            i.available = davail['Version']
        except:
            i.available = None

        dinst.update(davail)

        i.description = dinst['Description']

        return i

    def get_info_ui(self, pkg):
        return None

    def _save_pending(self, p):
        f = open('/tmp/genesis-yum-pending.list', 'w')
        for x in p:
            f.write('%s %s\n' % (p[x], x))
        f.close()

    def _parse_yum(self, ss):
        r = {}
        for s in ss:
            s = s.split()
            try:
                if s[0] == '':
                    continue
                else:
                    r[s[0]] = apis.pkgman.Package()
                    r[s[0]].name = s[0]
                    r[s[0]].version = s[1]
                    r[s[0]].state = 'installed'
                if len(r.keys()) > 250: break
            except:
                pass
        return r

    def _get_all(self):
        ss = utils.shell('yum -C -d0 -e0 list installed -q').splitlines()
        r = {}
        for s in ss:
            s = s.split()
            try:
                p = apis.pkgman.Package()
                p.name = s[0]
                p.version = s[1]
                p.state = 'installed'
                r[p.name] = p
                if len(r.keys()) > 250: break
            except:
                pass

        return r

########NEW FILE########
__FILENAME__ = main
import os
import stat
import shutil

from genesis.ui import *
from genesis.api import *
from genesis import apis
from genesis.com import Plugin, Interface, implements
from genesis.utils import shell, shell_cs


class PythonLangAssist(Plugin):
    implements(apis.langassist.ILangMgr)
    name = 'Python'

    def install(self, *mods):
        s = shell_cs('pip%s install %s' % \
            ('2' if self.app.platform in ['arkos', 'arch'] else '',
                ' '.join(x for x in mods)))
        if s[0] != 0:
            self.app.log.error('Failed to install %s via PyPI; %s'%(' '.join(x for x in mods),s[1]))
            raise Exception('Failed to install %s via PyPI, check logs for info'%' '.join(x for x in mods))

    def remove(self, *mods):
        s = shell_cs('pip%s uninstall %s' % \
            ('2' if self.app.platform in ['arkos', 'arch'] else '',
                ' '.join(x for x in mods)))
        if s[0] != 0:
            self.app.log.error('Failed to remove %s via PyPI; %s'%(' '.join(x for x in mods),s[1]))
            raise Exception('Failed to remove %s via PyPI, check logs for info'%' '.join(x for x in mods))

    def is_installed(self, name):
        s = shell('pip%s freeze'%'2' if self.app.platform in ['arkos', 'arch'] else '')
        for x in s.split('\n'):
            if name in x.split('==')[0]:
                return True
        return False

    def add_django_site(self, name, path, user, group):
        shell('cd %s; django-admin.py startproject %s' % (path,name))
        gconf = '#! /bin/bash\n\n'
        gconf += 'NAME="%s"\n' % name
        gconf += 'SOCKFILE=%s\n' % os.path.join(path, 'gunicorn.sock')
        gconf += 'USER=%s\n' % user
        gconf += 'GROUP=%s\n' % group
        gconf += 'NUM_WORKERS=3\n'
        gconf += 'DJANGODIR=%s\n' % path
        gconf += 'DJANGO_SETTINGS_MODULE=%s.settings\n' % name
        gconf += 'DJANGO_WSGI_MODULE=%s.wsgi\n\n' % name
        gconf += 'export PYTHONPATH=$DJANGODIR:$PYTHONPATH\n\n'
        gconf += 'echo "Starting $NAME as `whoami`"\n\n'
        gconf += 'exec gunicorn ${DJANGO_WSGI_MODULE}:application \ \n'
        gconf += '--name $NAME --workers $NUM_WORKERS \ \n'
        gconf += '--user=$USER --group=$GROUP \ \n'
        gconf += '--log-level=debug --bind=unix:$SOCKFILE\n'
        open(os.path.join(path, 'gunicorn'), 'w').write(gconf)
        st = os.stat(os.path.join(path, 'gunicorn'))
        os.chmod(os.path.join(path, 'gunicorn'), st.st_mode | 0111)
        s = filter(lambda x: x.id == 'supervisor',
            self.app.grab_plugins(apis.orders.IListener))
        if s:
            s[0].order('new', name, 'program', 
                [('directory', path), ('user', user), 
                ('command', os.path.join(path, 'gunicorn')),
                ('stdout_logfile', os.path.join(path, '%s_logfile.log'%name)),
                ('stderr_logfile', os.path.join(path, '%s_logfile.log'%name))])

    def remove_django_site(self, name, path):
        s = filter(lambda x: x.id == 'supervisor',
            self.app.grab_plugins(apis.orders.IListener))
        if s:
            s[0].order('del', name)
        shutil.rmtree(path)

########NEW FILE########
__FILENAME__ = backend
import ConfigParser
import nginx
import os
import stat

from genesis.api import *
from genesis.com import *
from genesis import apis
from genesis.plugins.users.backend import *
from genesis.plugins.webapps.backend import WebappControl
from genesis.utils import shell_cs, hashpw


class RadicaleConfig(Plugin):
    implements(IConfigurable)
    name = 'Calendar/Contacts'
    id = 'radicale'
    iconfont = 'gen-calendar'

    def load(self):
        self.config = ConfigParser.RawConfigParser()
        self.config.read(ConfManager.get().load('radicale', self.configFile))

    def save(self):
        self.config.write(open(self.configFile, 'w'))
        ConfManager.get().commit('radicale')

    def __init__(self):
        self.configFile = self.app.get_config(self).cfg_file
        self.config = None

    def list_files(self):
        return [self.configFile]


class GeneralConfig(ModuleConfig):
    target=RadicaleConfig
    platform = ['debian', 'centos', 'arch', 'arkos', 'gentoo', 'mandriva']

    labels = {
        'cfg_file': 'Configuration file',
        'first_run_complete': 'First Run is complete'
    }

    cfg_file = '/etc/radicale/config'
    first_run_complete = False


class RadicaleControl(Plugin):
    default_config = (
        '[server]\n'
        '# CalDAV server hostnames separated by a comma\n'
        '# IPv4 syntax: address:port\n'
        '# IPv6 syntax: [address]:port\n'
        '# For example: 0.0.0.0:9999, [::]:9999\n'
        '# IPv6 adresses are configured to only allow IPv6 connections\n'
        'hosts = 0.0.0.0:5232\n'
        '# Daemon flag\n'
        'daemon = False\n'
        '# File storing the PID in daemon mode\n'
        'pid =\n'
        '# SSL flag, enable HTTPS protocol\n'
        'ssl = False\n'
        '# SSL certificate path\n'
        'certificate = /etc/apache2/ssl/server.crt\n'
        '# SSL private key\n'
        'key = /etc/apache2/ssl/server.key\n'
        '# Reverse DNS to resolve client address in logs\n'
        'dns_lookup = True\n'
        '# Root URL of Radicale (starting and ending with a slash)\n'
        'base_prefix = /\n'
        '# Message displayed in the client when a password is needed\n'
        'realm = Radicale - Password Required lol\n'
        '\n'
        '\n'
        '[encoding]\n'
        '# Encoding for responding requests\n'
        'request = utf-8\n'
        '# Encoding for storing local collections\n'
        'stock = utf-8\n'
        '\n'
        '\n'
        '[auth]\n'
        '# Authentication method\n'
        '# Value: None | htpasswd | IMAP | LDAP | PAM | courier | http\n'
        'type = None\n'
        '\n'
        '# Usernames used for public collections, separated by a comma\n'
        'public_users = public\n'
        '# Usernames used for private collections, separated by a comma\n'
        'private_users = private\n'
        '# Htpasswd filename\n'
        'htpasswd_filename = /etc/radicale/users\n'
        '# Htpasswd encryption method\n'
        '# Value: plain | sha1 | crypt\n'
        'htpasswd_encryption = crypt\n'
        '\n'
        '# LDAP server URL, with protocol and port\n'
        'ldap_url = ldap://localhost:389/\n'
        '# LDAP base path\n'
        'ldap_base = ou=users,dc=example,dc=com\n'
        '# LDAP login attribute\n'
        'ldap_attribute = uid\n'
        '# LDAP filter string\n'
        '# placed as X in a query of the form (&(...)X)\n'
        '# example: (objectCategory=Person)(objectClass=User)(memberOf=cn=calenderusers,ou=users,dc=example,dc=org)\n'
        '# leave empty if no additional filter is needed\n'
        'ldap_filter =\n'
        '# LDAP dn for initial login, used if LDAP server does not allow anonymous searches\n'
        '# Leave empty if searches are anonymous\n'
        'ldap_binddn =\n'
        '# LDAP password for initial login, used with ldap_binddn\n'
        'ldap_password =\n'
        '# LDAP scope of the search\n'
        'ldap_scope = OneLevel\n'
        '\n'
        '# IMAP Configuration\n'
        'imap_hostname = localhost\n'
        'imap_port = 143\n'
        'imap_ssl = False\n'
        '\n'
        '# PAM group user should be member of\n'
        'pam_group_membership =\n'
        '\n'
        '# Path to the Courier Authdaemon socket\n'
        'courier_socket =\n'
        '\n'
        '# HTTP authentication request URL endpoint\n'
        'http_url =\n'
        '# POST parameter to use for username\n'
        'http_user_parameter =\n'
        '# POST parameter to use for password\n'
        'http_password_parameter =\n'
        '\n'
        '\n'
        '[rights]\n'
        '# Rights management method\n'
        '# Value: None | owner_only | owner_write | from_file\n'
        'type = None\n'
        '\n'
        '# File for rights management from_file\n'
        'file = ~/.config/radicale/rights\n'
        '\n'
        '\n'
        '[storage]\n'
        '# Storage backend\n'
        '# Value: filesystem | database\n'
        'type = filesystem\n'
        '\n'
        '# Folder for storing local collections, created if not present\n'
        'filesystem_folder = ~/.config/radicale/collections\n'
        '\n'
        '# Database URL for SQLAlchemy\n'
        '# dialect+driver://user:password@host/dbname[?key=value..]\n'
        '# For example: sqlite:///var/db/radicale.db, postgresql://user:password@localhost/radicale\n'
        '# See http://docs.sqlalchemy.org/en/rel_0_8/core/engines.html#sqlalchemy.create_engine\n'
        'database_url =\n'
        '\n'
        '\n'
        '[logging]\n'
        '# Logging configuration file\n'
        '# If no config is given, simple information is printed on the standard output\n'
        '# For more information about the syntax of the configuration file, see:\n'
        '# http://docs.python.org/library/logging.config.html\n'
        'config = /etc/radicale/logging\n'
        '# Set the default logging level to debug\n'
        'debug = False\n'
        '# Store all environment variables (including those set in the shell)\n'
        'full_environment = False\n'
        '\n'
        '\n'
        '# Additional HTTP headers\n'
        '#[headers]\n'
        '#Access-Control-Allow-Origin = *\n'
        )

    def add_user(self, user, passwd):
        ic = []
        if os.path.exists('/etc/radicale/users'):
            for x in open('/etc/radicale/users', 'r').read().split('\n'):
                ic.append(x)
        f = open('/etc/radicale/users', 'w')
        for x in ic:
            f.write(x+'\n')
        f.write('%s:%s'%(user, hashpw(passwd, 'ssha')))
        f.close()

    def edit_user(self, user, passwd):
        ic = []
        if os.path.exists('/etc/radicale/users'):
            for x in open('/etc/radicale/users', 'r').read().split('\n'):
                if not user == x.split(':')[0]:
                    ic.append(x)
        f = open('/etc/radicale/users', 'w')
        for x in ic:
            f.write(x+'\n')
        f.write('%s:%s'%(user, hashpw(passwd, 'ssha')))
        f.close()

    def del_user(self, user):
        ic = []
        if os.path.exists('/etc/radicale/users'):
            for x in open('/etc/radicale/users', 'r').read().split('\n'):
                if not user == x.split(':')[0]:
                    ic.append(x)
        f = open('/etc/radicale/users', 'w')
        for x in ic:
            f.write(x+'\n')
        f.close()

    def list_users(self):
        u = []
        if os.path.exists('/etc/radicale/users'):
            for x in open('/etc/radicale/users', 'r').read().split('\n'):
                if x.split():
                    u.append(x.split(':')[0])
        return u

    def is_installed(self):
        # Verify the different components of the server setup
        if not os.path.exists('/etc/radicale/config') or not os.path.isdir('/usr/lib/radicale') \
        or not os.path.exists('/etc/radicale/radicale.wsgi'):
            return False
        elif not 'radicale' in [x.name for x in apis.webapps(self.app).get_sites()]:
            return False
        return True

    def setup(self, addr, port):
        # Make sure Radicale is installed and ready
        pyctl = apis.langassist(self.app).get_interface('Python')
        users = UsersBackend(self.app)
        if not pyctl.is_installed('Radicale'):
            pyctl.install('radicale')
        # due to packaging bugs, make extra sure perms are readable
        st = os.stat('/usr/lib/python2.7/site-packages/radicale')
        for r, d, f in os.walk('/usr/lib/python2.7/site-packages/radicale'):
            for x in d:
                os.chmod(os.path.join(r, x), st.st_mode | stat.S_IROTH | stat.S_IRGRP)
            for x in f:
                os.chmod(os.path.join(r, x), st.st_mode | stat.S_IROTH | stat.S_IRGRP)
        if not os.path.exists('/etc/radicale/config'):
            if not os.path.isdir('/etc/radicale'):
                os.mkdir('/etc/radicale')
            open('/etc/radicale/config', 'w').write(self.default_config)
        if not os.path.isdir('/usr/lib/radicale'):
            os.mkdir('/usr/lib/radicale')
        # Add the site process
        users.add_user('radicale')
        users.add_group('radicale')
        users.add_to_group('radicale', 'radicale')
        wsgi_file = 'import radicale\n'
        wsgi_file += 'radicale.log.start()\n'
        wsgi_file += 'application = radicale.Application()\n'
        open('/etc/radicale/radicale.wsgi', 'w').write(wsgi_file)
        os.chmod('/etc/radicale/radicale.wsgi', 0766)
        s = apis.orders(self.app).get_interface('supervisor')
        if s:
            s[0].order('new', 'radicale', 'program', 
                [('directory', '/etc/radicale'), ('user', 'radicale'), 
                ('command', 'uwsgi -s /tmp/radicale.sock -C --plugin python2 --wsgi-file radicale.wsgi'),
                ('stdout_logfile', '/var/log/radicale.log'),
                ('stderr_logfile', '/var/log/radicale.log')])
        block = [
            nginx.Location('/',
                nginx.Key('auth_basic', '"Genesis Calendar Server (Radicale)"'),
                nginx.Key('auth_basic_user_file', '/etc/radicale/users'),
                nginx.Key('include', 'uwsgi_params'),
                nginx.Key('uwsgi_pass', 'unix:///tmp/radicale.sock'),
            )
        ]
        if not os.path.exists('/etc/radicale/users'):
            open('/etc/radicale/users', 'w').write('')
            os.chmod('/etc/radicale/users', 0766)
        WebappControl(self.app).add_reverse_proxy('radicale', 
            '/usr/lib/radicale', addr, port, block)
        apis.networkcontrol(self.app).add_webapp(('radicale', 'ReverseProxy', port))
        c = self.app.get_config(RadicaleConfig(self.app))
        c.first_run_complete = True
        c.save()

########NEW FILE########
__FILENAME__ = main
import re

from genesis.ui import *
from genesis.api import *
from genesis import apis
from genesis.plugins.network.backend import IHostnameManager

import backend

class RadicalePlugin(CategoryPlugin):
    text = 'Calendar'
    iconfont = 'gen-calendar'
    folder = 'servers'

    def on_session_start(self):
        self._config = backend.RadicaleConfig(self.app)
        self._wa = apis.webapps(self.app)
        self._rc = backend.RadicaleControl(self.app)
        self._add = None
        self._edit = None

    def on_init(self):
        self._users = self._rc.list_users()
        self.site = filter(lambda x: x.name=='radicale', self._wa.get_sites())
        if self.site:
            self.site = self.site[0]
        else:
            self.site = None

    def get_ui(self):
        is_installed = self._rc.is_installed()
        if not self.app.get_config(self._config).first_run_complete \
        or not is_installed:
            ui = self.app.inflate('radicale:setup')
            ui.find('addr').set('value', self.app.get_backend(IHostnameManager).gethostname())
            if not is_installed:
                self.put_message('err', 'Your Calendar/Contacts server does not appear to be properly configured. Please rerun this setup.')
            return ui
        ui = self.app.inflate('radicale:main')

        ui.find('rinfo').append(
            UI.Label(size='1', bold=True,
                text='Your Calendar/Contacts server is listening at http%s://%s%s'%('s' if self.site.ssl else '', self.site.addr, ':'+self.site.port if self.site.port not in ['80', '443'] else ''))
            )

        t = ui.find('list')
        for u in self._users:
            t.append(UI.DTR(
                    UI.Iconfont(iconfont='gen-user'),
                    UI.Label(text=u),
                    UI.HContainer(
                        UI.TipIcon(iconfont='gen-key', id='edit/'+str(self._users.index(u)), text='Change Password'),
                        UI.TipIcon(iconfont='gen-cancel-circle', id='del/'+str(self._users.index(u)), text='Delete', warning='Are you sure you want to delete calendar user %s?'%u)
                    ),
                ))

        if self._add:
            ui.append('main',
                UI.DialogBox(
                    UI.FormLine(
                        UI.TextInput(name='acct', id='acct'),
                        text='Username'
                    ),
                    UI.FormLine(
                        UI.EditPassword(id='passwd', value='Click to add password'),
                        text='Password'
                    ),
                    id='dlgAddUser')
                )

        if self._edit:
            ui.append('main',
                UI.DialogBox(
                    UI.FormLine(
                        UI.EditPassword(id='chpasswd', value='Click to change password'),
                        text='Password'
                    ),
                    id='dlgChpasswd')
                )

        return ui

    @event('button/click')
    def on_click(self, event, params, vars = None):
        if params[0] == 'add':
            self._add = True
        if params[0] == 'edit':
            self._edit = self._users[int(params[1])]
        if params[0] == 'del':
            try:
                u = self._users[int(params[1])]
                self._rc.del_user(u)
                self.put_message('info', 'User deleted successfully')
            except Exception, e:
                self.app.log.error('Calendar user could not be deleted. Error: %s' % str(e))
                self.put_message('err', 'User could not be deleted')

    @event('dialog/submit')
    @event('form/submit')
    def on_submit(self, event, params, vars=None):
        if params[0] == 'frmSetup':
            vaddr = True
            addr = vars.getvalue('addr', '')
            port = vars.getvalue('port', '')
            for site in apis.webapps(self.app).get_sites():
                if addr == site.addr and port == site.port:
                    vaddr = False
            if not addr or not port:
                self.put_message('err', 'Must choose an address and port!')
            elif port == self.app.gconfig.get('genesis', 'bind_port', ''):
                self.put_message('err', 'Can\'t use the same port number as Genesis')
            elif not vaddr:
                self.put_message('err', 'This domain/subdomain and port conflicts with a website you have. '
                    'Change one of the two, or remove the site before continuing.')
            else:
                try:
                    self._rc.setup(addr, port)
                except Exception, e:
                    self.put_message('err', 'Setup failed: %s'%str(e))
        elif params[0] == 'dlgAddUser':
            acct = vars.getvalue('acct', '')
            passwd = vars.getvalue('passwd', '')
            if vars.getvalue('action', '') == 'OK':
                m = re.match('([-0-9a-zA-Z.+_]+)', acct)
                if not acct or not m:
                    self.put_message('err', 'Must choose a valid username')
                elif acct in self._users:
                    self.put_message('err', 'You already have a user with this name')
                elif not passwd:
                    self.put_message('err', 'Must choose a password')
                elif passwd != vars.getvalue('passwdb',''):
                    self.put_message('err', 'Passwords must match')
                else:
                    try:
                        self._rc.add_user(acct, passwd)
                        self.put_message('info', 'User added successfully')
                    except Exception, e:
                        self.app.log.error('Calendar user %s could not be added. Error: %s' % (acct,str(e)))
                        self.put_message('err', 'User could not be added')
            self._add = None
        if params[0] == 'dlgChpasswd':
            passwd = vars.getvalue('chpasswd', '')
            if vars.getvalue('action', '') == 'OK':
                if not passwd:
                    self.put_message('err', 'Must choose a password')
                elif passwd != vars.getvalue('chpasswdb',''):
                    self.put_message('err', 'Passwords must match')
                else:
                    try:
                        self._rc.edit_user(self._edit, passwd)
                        self.put_message('info', 'Password changed successfully')
                    except Exception, e:
                        self.app.log.error('Calendar password for %s could not be changed. Error: %s' % (self._edit,str(e)))
                        self.put_message('err', 'Password could not be changed')
            self._edit = None

########NEW FILE########
__FILENAME__ = main
from genesis.api import *
from genesis.ui import *
from genesis.com import Plugin, Interface, implements
from genesis import apis
from genesis.utils import shell

import nginx
import os


class ReverseProxy(Plugin):
	implements(apis.webapps.IWebapp)

	addtoblock = []

	def pre_install(self, name, vars):
		if vars:
			if not vars.getvalue('rp-type', '') or not vars.getvalue('rp-pass', ''):
				raise Exception('Must enter ReverseProxy type and location to pass to')
			elif vars.getvalue('rp-type') in ['fastcgi', 'uwsgi']:
				self.addtoblock = [nginx.Location(vars.getvalue('rp-lregex', '/'), 
					nginx.Key('%s_pass'%vars.getvalue('rp-type'), 
						'%s'%vars.getvalue('rp-pass')),
					nginx.Key('include', '%s_params'%vars.getvalue('rp-type')),
					nginx.Key('proxy_set_header', 'X-Real-IP $remote_addr') if vars.getvalue('rp-xrip', '') == '1' else None,
					nginx.Key('proxy_set_header', 'X-Forwarded-For $proxy_add_x_forwarded_for') if vars.getvalue('rp-xff', '') == '1' else None,
					)]
			else:
				self.addtoblock = [nginx.Location(vars.getvalue('rp-lregex', '/'), 
					nginx.Key('proxy_pass', '%s'%vars.getvalue('rp-pass')),
					nginx.Key('proxy_redirect', 'off'),
					nginx.Key('proxy_buffering', 'off'),
					nginx.Key('proxy_set_header', 'Host $host'),
					nginx.Key('proxy_set_header', 'X-Real-IP $remote_addr') if vars.getvalue('rp-xrip', '') == '1' else None,
					nginx.Key('proxy_set_header', 'X-Forwarded-For $proxy_add_x_forwarded_for') if vars.getvalue('rp-xff', '') == '1' else None,
					)]

	def post_install(self, name, path, vars):
		pass

	def pre_remove(self, name, path):
		pass

	def post_remove(self, name):
		pass

	def ssl_enable(self, path, cfile, kfile):
		pass

	def ssl_disable(self, path):
		pass

########NEW FILE########
__FILENAME__ = main
import os

from genesis.ui import *
from genesis.api import *
from genesis import apis
from genesis.com import Plugin, Interface, implements
from genesis.utils import shell, shell_cs, shell_status, download


class Ruby(Plugin):
    implements(apis.langassist.ILangMgr)
    name = 'Ruby'

    def verify_path(self):
        profile = []
        f = open('/etc/profile', 'r')
        for l in f.readlines():
            if l.startswith('PATH="') and not '/usr/lib/ruby/gems/2.0.0/bin' in l:
                l = l.split('"\n')[0]
                l += ':/usr/lib/ruby/gems/2.0.0/bin"\n'
                profile.append(l)
                os.environ['PATH'] = os.environ['PATH'] + ':/usr/lib/ruby/gems/2.0.0/bin'
            else:
                profile.append(l)
        f.close()
        open('/etc/profile', 'w').writelines(profile)

    def install_gem(self, *gems, **kwargs):
        self.verify_path()
        gemlist = shell('gem list').split('\n')
        for x in gems:
            if not any(x==s for s in gemlist) or force:
                d = shell_cs('gem install -N --no-user-install %s' % x)
                if d[0] != 0:
                    self.app.log.error('Gem install \'%s\' failed: %s'%(x,str(d[1])))
                    raise Exception('Gem install \'%s\' failed. See logs for more info'%x)

########NEW FILE########
__FILENAME__ = backend
import os
import shutil

from genesis.api import *
from genesis.com import *
from genesis.utils import *


class SambaConfig(Plugin):
    implements(IConfigurable)
    name = 'Samba'
    id = 'samba'
    iconfont = 'gen-upload-2'
    shares = {}
    general = {}
    users = {}

    general_defaults = {
        'server string': '',
        'workgroup': 'WORKGROUP',
        'interfaces': ''
    }

    defaults = {
        'browseable': 'yes',
        'valid users': '',
        'path': '',
        'read only': 'yes',
        'guest ok': 'yes',
        'only guest': 'no'
    }

    editable = {
        'Account Flags': '-c',
        'User SID': '-U',
        'Primary Group SID': '-G',
        'Full Name': '-f',
        'Home Directory': '-h',
        'HomeDir Drive': '-D',
        'Logon Script': '-S',
        'Profile Path': '-p',
        'Kickoff time': '-K'
    }

    fields = []

    def __init__(self):
        self.cfg_file = self.app.get_config(self).cfg_file
        if not os.path.exists(self.cfg_file):
            shutil.copyfile('/etc/samba/smb.conf.default', self.cfg_file)

    def list_files(self):
        return [self.cfg_file]

    def load(self):
        self.shares = {}

        if os.path.exists(self.cfg_file):
            fn = self.cfg_file
        else:
            fn = self.cfg_file + '.default'
        ss = ConfManager.get().load('samba', fn).split('\n')
        cs = ''
        for s in ss:
            s = s.strip()
            try:
                if s[0] != '#' and s[0] != ';':
                    if s[0] == '[':
                        cs = s[1:-1]
                        if cs == 'homes' or cs == 'printers':
                            continue
                        else:
                            self.shares[cs] = self.new_share() if cs != 'global' else self.general_defaults.copy()
                    else:
                        s = s.split('=')
                        self.shares[cs][s[0].strip()] = s[1].strip()
            except:
                pass

        self.general = self.shares['global']
        self.shares.pop('global')

        self.users = {}
        ss = [s.split(',')[0].split(':')[0] for s in shell('pdbedit -L').split('\n')]
        for s in ss:
            if s != '':
                x = shell('pdbedit -L -v -u ' + s).split('\n')
                self.users[s] = {}
                self.fields = []
                for l in x:
                    try:
                        self.users[s][l.split(':')[0]] = l.split(':')[1].strip()
                        self.fields.append(l.split(':')[0])
                    except:
                        pass


    def save(self):
        print self.shares
        ss = ''
        ss += '[global]\n'
        for k in self.general:
            if not k in self.general_defaults or \
                self.general[k] != self.general_defaults[k]:
                ss += '\t%s = %s\n' % (k,self.general[k])
        for s in self.shares:
            ss += '\n[%s]\n' % s
            for k in self.shares[s]:
                #if not k in self.defaults or self.shares[s][k] != self.defaults[k]:
                ss += '\t%s = %s\n' % (k,self.shares[s][k])
        ConfManager.get().save('samba', self.cfg_file, ss)
        ConfManager.get().commit('samba')

    def modify_user(self, u, p, v):
        shell('pdbedit -r -u %s %s "%s"' % (u,self.editable[p],v))

    def del_user(self, u):
        shell('pdbedit -x -u ' + u)

    def add_user(self, u, p):
        shell_stdin('smbpasswd -as %s' % u, p+'\n'+p+'\n')

    def get_shares(self):
        return self.shares.keys()

    def new_share(self):
        return self.defaults.copy()

    def set_param(self, share, param, value):
        if share == 'general':
            self.general[param] = value
        else:
            self.shares[share][param] = value

    def set_param_from_vars(self, share, param, vars):
        if share == 'general':
            value = vars.getvalue(param, self.general_defaults[param])
        else:
            value = vars.getvalue(param, self.defaults[param])
        self.set_param(share, param, value)

    def set_param_from_vars_yn(self, share, param, vars):
        if share == 'general':
            value = 'yes' if vars.getvalue(param, self.general_defaults[param]) == '1' else 'no'
        else:
            value = 'yes' if vars.getvalue(param, self.defaults[param]) == '1' else 'no'
        self.set_param(share, param, value)


class GeneralConfig(ModuleConfig):
    target=SambaConfig
    platform = ['debian', 'centos', 'arch', 'arkos', 'gentoo', 'mandriva']
    
    labels = {
        'cfg_file': 'Configuration file'
    }
    
    cfg_file = '/etc/samba/smb.conf'
   
   
class BSDConfig(GeneralConfig):
    implements((IModuleConfig, -100))
    platform = ['freebsd']
    
    cfg_file = '/usr/local/etc/samba/smb.conf'


########NEW FILE########
__FILENAME__ = main
from genesis.api import *
from genesis.ui import *
from genesis.utils import *
from genesis import apis

from genesis.plugins.users.backend import UsersBackend

import os
import backend
import re


class SambaPlugin(apis.services.ServiceControlPlugin):
    text = 'Fileshares (Win)'
    iconfont = 'gen-upload-2'
    folder = 'servers'
    
    def on_session_start(self):
        self._tab = 0
        self._cfg = backend.SambaConfig(self.app)
        self._cfg.load()
        self._editing_share = None
        self._editing_user = None
        self._editing = None
        self._adding_user = False

    def get_main_ui(self):
        ui = self.app.inflate('samba:main')
        ui.find('tabs').set('active', self._tab)

        # Shares
        for h in self._cfg.get_shares():
            r = UI.DTR(
                UI.IconFont(iconfont='gen-folder'),
                UI.Label(text=h),
                UI.Label(text=self._cfg.shares[h]['path']),
                UI.HContainer(
                    UI.TipIcon(iconfont='gen-pencil-2',
                        text='Edit', id='editshare/' + h),
                    UI.TipIcon(
                        iconfont='gen-close',
                        text='Delete', id='delshare/' + h, warning='Are you sure you want to delete the %s share?'%h)
                ),
            )
            ui.append('shares', r)

        if not self._editing_share is None:
            if self._editing_share == '':
                ui.append('main', self.get_ui_edit_share())
            else:
                ui.append('main', self.get_ui_edit_share(
                    self._cfg.shares[self._editing_share]
                ))

        # Users
        for h in sorted(self._cfg.users.keys()):
            r = UI.DTR(
                UI.IconFont(iconfont='gen-user'),
                UI.Label(text=h),
                UI.HContainer(
                    #UI.TipIcon(iconfont='gen-pencil-2',
                    #    text='Edit', id='edituser/' + h),
                    UI.TipIcon(
                        iconfont='gen-close',
                        text='Delete', id='deluser/' + h, warning='Are you sure you want to delete %s from the Samba users list?'%h)
                ),
            )
            ui.append('users', r)

        #if not self._editing_user is None:
        #    if self._editing_user == '':
        #        ui.append('main', self.get_ui_edit_user())
        #    else:
        #        if not self._editing_user in self._cfg.users.keys():
        #            self.put_message('err', 'User not found')
        #            self._editing_user = None
        #        else:
        #            ui.append('main', self.get_ui_edit_user(
        #                self._cfg.users[self._editing_user]
        #            ))

        if not self._editing is None:
            ui.append('main', UI.InputBox(
                title=self._editing,
                value=self._cfg.users[self._editing_user][self._editing],
                id='dlgEdit'
            ))

        if self._adding_user:
            users = [UI.SelectOption(text=x.login, value=x.login) for x in UsersBackend(self.app).get_all_users() if x.uid >= 1000]
            if users:
                ui.append('main',
                    UI.DialogBox(
                        UI.FormLine(
                            UI.Select(*users, name='acct', id='acct'),
                            text='Username'
                        ),
                        UI.FormLine(
                            UI.EditPassword(id='passwd', value='Click to add password'),
                            text='Password'
                        ),
                        id='dlgAddUser')
                    )
            else:
                self.put_message('err', 'No non-root Unix users found')
    
        # Config
        ui.append('tab2', self.get_ui_general())
        
        return ui

    def get_ui_edit_share(self, s=None):
        if s is None or s == '':
            s = self._cfg.new_share()

        dlg = UI.DialogBox(
            UI.Container(
                UI.Formline(
                    UI.TextInput(name='name'),
                    text='Name', help='The name you will use to connect to your share'
                ) if self._editing_share == '' else None,
                UI.Formline(
                    UI.TextInput(name='path', value=s['path']),
                    text='Path', help='The path to the folder on the disk you want to share'
                ),
                UI.Formline(
                    *[UI.Checkbox(text=x, name='validusers[]', value=x, checked=True if x in s['valid users'] else False) \
                        for x in sorted(self._cfg.users.keys())],
                    text='Valid users', help='A list of Samba users that will be able to connect to this share'
                ) if self._cfg.users.keys() else None,
                UI.Formline(
                    UI.Checkbox(text='Yes', name='browseable', checked=s['browseable']=='yes'),
                    text='Browseable?', help='This share will show up in Windows Explorer/My Computer'
                ),
                UI.Formline(
                    UI.Checkbox(text='Yes', name='read only', checked=s['read only']=='yes'),
                    text='Read only?', help='Prevent anyone from editing or deleting files in this share'
                ),
                UI.Formline(
                    UI.Checkbox(text='Yes', name='guest ok', checked=s['guest ok']=='yes'),
                    text='Guest access?', help='Allow anyone (not just valid users) to connect to this share'
                ),
                UI.Formline(
                    UI.Checkbox(text='Yes', name='only guest', checked=s['only guest']=='yes'),
                    text='Force guest?', help='Only allow guests to connect (ignores the \'valid users\' field)'
                )
            ),
            id='dlgEditShare',
            title='Edit share'
        )
        return dlg

    #def get_ui_edit_user(self, u=None):
    #    t = UI.Container()
    #    for k in self._cfg.fields:
    #        if k in u.keys():
    #            t.append(
    #                UI.Formline(
    #                    UI.Label(text=u[k]),
    #                    UI.Button(design='mini',
    #                        text='Change', id='chuser/'+k) if k in self._cfg.editable else None,
    #                    text=k
    #                )
    #            )
    #
    #    dlg = UI.DialogBox(
    #        t,
    #        title='Edit user',
    #        id='dlgEditUser'
    #    )
    #    return dlg

    def get_ui_general(self):
        dlg = UI.FormBox(
            UI.Formline(
                UI.TextInput(name='server string', value=self._cfg.general['server string']),
                text='Machine description',
            ),
            UI.Formline(
                UI.TextInput(name='workgroup', value=self._cfg.general['workgroup']),
                text='Workgroup',
            ),
            UI.Formline(
                UI.TextInput(name='interfaces', value=self._cfg.general['interfaces']),
                text='Listen on interfaces', help='Space-separated list. Can be interfaces (eth0), IP addresses or IP/mask pairs'
            ),
            id='frmGeneral'
        )
        return dlg

    @event('button/click')
    def on_click(self, event, params, vars=None):
        if params[0] == 'restart':
            backend.restart()
        if params[0] == 'editshare':
            self._editing_share = params[1]
            self._tab = 0
        if params[0] == 'delshare':
            if params[1] in self._cfg.shares.keys():
                del self._cfg.shares[params[1]]
            self._cfg.save()
            self._tab = 0
        if params[0] == 'newshare':
            self._editing_share = ''
            self._tab = 0
        #if params[0] == 'edituser':
        #    self._editing_user = params[1]
        #    self._tab = 1
        if params[0] == 'newuser':
            self._adding_user = True
            self._tab = 1
        if params[0] == 'deluser':
            self._cfg.del_user(params[1])
            self._cfg.load()
            self._tab = 1
        if params[0] == 'chuser':
            self._tab = 1
            self._editing = params[1]

    @event('dialog/submit')
    @event('form/submit')
    def on_submit(self, event, params, vars=None):
        if params[0] == 'dlgEditShare':
            if vars.getvalue('action', '') == 'OK':
                if vars.has_key('name') and not vars.getvalue('name', ''):
                    self.put_message('err', 'Must choose a valid name for this share')
                elif not vars.getvalue('path', '') or not os.path.isdir(vars.getvalue('path')):
                    self.put_message('err', 'Must choose a valid path on disk')
                else:
                    es = self._editing_share
                    if es == '':
                        es = vars.getvalue('name', 'new')
                        self._cfg.shares[es] = self._cfg.new_share()

                    validusers = []
                    for i in range(0, len(sorted(self._cfg.users.keys()))):
                        try:
                            if vars.getvalue('validusers[]')[i] == '1':
                                validusers.append(sorted(self._cfg.users.keys())[i])
                        except TypeError:
                            pass

                    self._cfg.set_param_from_vars(es, 'path', vars)
                    if validusers:
                        self._cfg.set_param(es, 'valid users', ' '.join(validusers))
                    self._cfg.set_param_from_vars_yn(es, 'browseable', vars)
                    self._cfg.set_param_from_vars_yn(es, 'read only', vars)
                    self._cfg.set_param_from_vars_yn(es, 'guest ok', vars)
                    self._cfg.set_param_from_vars_yn(es, 'only guest', vars)
                    self._cfg.save()
            self._editing_share = None
        if params[0] == 'frmGeneral':
            if vars.getvalue('action', '') == 'OK':
                self._cfg.set_param_from_vars('general', 'server string', vars)
                self._cfg.set_param_from_vars('general', 'workgroup', vars)
                self._cfg.set_param_from_vars('general', 'interfaces', vars)
                self._cfg.save()
            self._tab = 2

        #if params[0] == 'dlgEditUser':
        #    self._editing_user = None

        if params[0] == 'dlgAddUser':
            acct = vars.getvalue('acct', '')
            passwd = vars.getvalue('passwd', '')
            if vars.getvalue('action', '') == 'OK':
                m = re.match('([-0-9a-zA-Z.+_]+)', acct)
                if not acct or not m:
                    self.put_message('err', 'Must choose a valid username')
                elif acct in self._cfg.users.keys():
                    self.put_message('err', 'You already have a user with this name')
                elif not passwd:
                    self.put_message('err', 'Must choose a password')
                elif passwd != vars.getvalue('passwdb',''):
                    self.put_message('err', 'Passwords must match')
                else:
                    self._cfg.add_user(acct, passwd)
                    self._cfg.load()
            self._adding_user = False

        if params[0] == 'dlgEdit':
            if vars.getvalue('action', '') == 'OK':
                self._cfg.modify_user(self._editing_user, self._editing, vars.getvalue('value', ''))
                self._cfg.load()
            self._editing = None

########NEW FILE########
__FILENAME__ = main
from genesis.ui import *
from genesis.com import implements
from genesis.api import *
from genesis.utils import shell, enquote, BackgroundProcess
from genesis.plugins.core.api import *

import time

class ShellPlugin(CategoryPlugin):
    text = 'Execute'
    iconfont = 'gen-target'
    folder = 'tools'

    def on_session_start(self):
        self._recent = []
        self._process = BackgroundProcess('')

    def get_ui(self):
        ui = self.app.inflate('shell:main')
        recent = [UI.SelectOption(text=x[0:40] + '...' if len(x) > 40 else x,
                                  value=x) for x in self._recent]
        
        if self._process is not None and self._process.is_running():
            time.sleep(1)
        
        if self._process is not None and self._process.is_running():
            ui.append('status', UI.Label(
                text='Process is running. Refresh on will'
            ))
        
        log = UI.CustomHTML(id='logdata', html=enquote(self._process.output + self._process.errors))

        ui.append('log', log)
        ui.appendAll('shell-recent', *recent)
        

        return ui

    def go(self, cmd):
        if not self._process.is_running():
            self._process = BackgroundProcess(cmd, runas=self.app.auth.user)
            self._process.start()
            rcnt = [cmd]
            if len(self._recent) > 0:
                for x in self._recent:
                    rcnt.append(x)
            if len(rcnt) > 5:
                rcnt = rcnt[:5]
            self._recent = rcnt

    @event('form/submit')
    def on_submit(self, event, params, vars=None):
        self.go(vars.getvalue('cmd', ''))


class ShellProgress(Plugin):
    implements(IProgressBoxProvider)
    title = 'Shell'
    iconfont = 'gen-target'
    can_abort = True
    
    def __init__(self):
        self.proc = self.app.session.get('ShellPlugin-_process')

    def has_progress(self):         
        if self.proc is None:
            self.proc = self.app.session.get('ShellPlugin-_process')
            return False
        return self.proc.is_running()
        
    def get_progress(self):
        return self.proc.cmdline
    
    def abort(self):
        self.proc.kill()
   

########NEW FILE########
__FILENAME__ = backend
import os
import pwd
import grp
import shutil

from genesis import apis
from genesis.com import Plugin
from genesis.utils import shell, shell_cs
from genesis.plugins.users.backend import UsersBackend
from genesis.plugins.network.backend import IHostnameManager


class SSControl(Plugin):
    def setup(self):
        # Make sure Unix user/group are active
        users = UsersBackend(self.app)
        users.add_sys_with_home('sparkleshare')
        users.add_group('sparkleshare')
        users.add_to_group('sparkleshare', 'sparkleshare')
        users.change_user_param('sparkleshare', 'shell', '/usr/bin/git-shell')
        if not os.path.exists('/home/sparkleshare'):
            os.makedirs('/home/sparkleshare')

        # Configure SSH
        if not os.path.exists('/home/sparkleshare/.ssh'):
            os.makedirs('/home/sparkleshare/.ssh')
            os.chmod('/home/sparkleshare/.ssh', 700)
        if not os.path.exists('/home/sparkleshare/.ssh/authorized_keys'):
            open('/home/sparkleshare/.ssh/authorized_keys', 'w').write('')
            os.chmod('/home/sparkleshare/.ssh/authorized_keys', 600)
        f = open('/etc/ssh/sshd_config', 'r').read()
        if not '# SparkleShare' in f:
            f += '\n'
            f += '# SparkleShare\n'
            f += '# Please do not edit the above comment as it\'s used as a check by Dazzle/Genesis\n'
            f += 'Match User sparkleshare\n'
            f += '    PasswordAuthentication no\n'
            f += '    PubkeyAuthentication yes\n'
            f += '# End of SparkleShare configuration\n'
            open('/etc/ssh/sshd_config', 'w').write(f)
        self.app.get_backend(apis.services.IServiceManager).restart('sshd')

    def add_project(self, name, crypto=False):
        self.setup()
        if crypto:
            name = name + '-crypto'
        s = shell_cs('git init --quiet --bare "%s"'%os.path.join('/home/sparkleshare', name))
        if s[0] != 0:
            self.app.log.error('Creation of Git repository failed. Error:\n%s'%s[1])
            raise Exception('Creation of Git repository failed. See the logs for details')
        shell('git config --file %s receive.denyNonFastForwards true'%os.path.join('/home/sparkleshare', name, 'config'))

        # Add list of files that Git should not compress
        extensions = ['jpg', 'jpeg', 'png', 'tiff', 'gif', 'flac', 'mp3',
            'ogg', 'oga', 'avi', 'mov', 'mpg', 'mpeg', 'mkv', 'ogv', 'ogx',
            'webm', 'zip', 'gz', 'bz', 'bz2', 'rpm', 'deb', 'tgz', 'rar',
            'ace', '7z', 'pak', 'iso', 'dmg']
        if os.path.exists(os.path.join('/home/sparkleshare', name, 'info/attributes')):
            f = open(os.path.join('/home/sparkleshare', name, 'info/attributes'), 'r').read()
        else:
            f = ''
        for x in extensions:
            f += '*.%s -delta\n' % x
            f += '*.%s -delta\n' % x.upper()
        open(os.path.join('/home/sparkleshare', name, 'info/attributes'), 'w').write(f)

        uid = pwd.getpwnam('sparkleshare').pw_uid
        gid = grp.getgrnam('sparkleshare').gr_gid
        for r, d, f in os.walk(os.path.join('/home/sparkleshare', name)):
            for x in d:
                os.chown(os.path.join(r, x), uid, gid)
                os.chmod(os.path.join(r, x), 770)
            for x in f:
                os.chown(os.path.join(r, x), uid, gid)
                os.chmod(os.path.join(r, x), 770)

        return ('ssh://sparkleshare@%s'%self.app.get_backend(IHostnameManager).gethostname().lower(),
            os.path.join('/home/sparkleshare', name))

    def get_projects(self):
        p = []
        for x in os.listdir('/home/sparkleshare'):
            if os.path.isdir(os.path.join('/home/sparkleshare', x)) and not x.startswith('.'):
                p.append(x)
        return p

    def link_client(self, cid):
        f = open('/home/sparkleshare/.ssh/authorized_keys', 'r').read()
        f += cid+'\n'
        open('/home/sparkleshare/.ssh/authorized_keys', 'w').write(f)

    def del_project(self, name):
        shutil.rmtree(os.path.join('/home/sparkleshare', name))

########NEW FILE########
__FILENAME__ = main
import os

from genesis.ui import *
from genesis.api import *
from genesis.utils import *
from genesis import apis
from genesis.plugins.network.backend import IHostnameManager

from backend import SSControl


class SSPlugin(CategoryPlugin):
    text = 'SparkleShare'
    iconfont = 'gen-upload-2'
    folder = 'servers'

    def on_session_start(self):
        self._hostname = self.app.get_backend(IHostnameManager).gethostname().lower()
        self._sc = SSControl(self.app)
        self._add, self._link = None, None

    def get_ui(self):
        if not os.path.exists('/home/sparkleshare'):
            os.makedirs('/home/sparkleshare')
            
        ui = self.app.inflate('sparkleshare:main')

        for x in self._sc.get_projects():
            ui.append('list', UI.DTR(
                UI.Label(text=x),
                UI.Label(text='ssh://sparkleshare@%s'%self._hostname),
                UI.Label(text=os.path.join('/home/sparkleshare', x)),
                UI.HContainer(
                    UI.TipIcon(
                        id='remove/'+x,
                        text='Remove',
                        iconfont='gen-cancel-circle',
                        warning='Are you sure you want to remove the %s project?'%x
                    )
                ),
            ))

        if self._add:
            ui.append('main', UI.DialogBox(
                UI.FormLine(
                    UI.TextInput(name='name'),
                    text='Project name'
                ),
                UI.FormLine(
                    UI.Checkbox(name='crypt'),
                    text='Encrypted?'
                ),
                id='dlgAdd'
            ))

        if self._link:
            ui.append('main', UI.InputBox(
                text='Paste your Client ID', id='dlgLink'
            ))

        return ui

    @event('button/click')
    def on_button(self, event, params, vars=None):
        if params[0] == 'add':
            self._add = True
        if params[0] == 'link':
            self._link = True
        if params[0] == 'remove':
            self._sc.del_project(params[1])
            self.put_message('info', 'Project deleted successfully')

    @event('dialog/submit')
    def on_submit(self, event, params, vars=None):
        if params[0] == 'dlgAdd':
            if vars.getvalue('action', '') == 'OK':
                name = vars.getvalue('name', '')
                p = self._sc.get_projects()
                if not name:
                    self.put_message('err', 'You must choose a project name')
                elif name in p or name+'-crypto' in p:
                    self.put_message('err', 'You already have a project with this name!')
                else:
                    try:
                        self._sc.add_project(name, crypto=vars.getvalue('crypt', '')=='1')
                        self.put_message('info', 'Project created successfully')
                    except Exception, e:
                        self.put_message('err', str(e))
            self._add = None
        elif params[0] == 'dlgLink':
            if vars.getvalue('action', '') == 'OK' and vars.getvalue('value', ''):
                self._sc.link_client(vars.getvalue('value'))
            self._link = None

########NEW FILE########
__FILENAME__ = backend
from genesis.api import *
from genesis.utils import *
from genesis.com import *
from genesis import apis

import os
import pwd
import re


class SSHConfig(Plugin):
    implements(IConfigurable)
    name = 'SSH Options'
    iconfont = 'gen-console'
    id = 'ssh'

    def list_files(self):
        return ['/etc/ssh/sshd_config']

    def read(self):
        ss = ConfManager.get().load('ssh', '/etc/ssh/sshd_config').split('\n')
        r = {}
        rroot = re.compile('.*?PermitRootLogin ([^\s]+)', flags=re.IGNORECASE)
        rpkey = re.compile('.*?PubkeyAuthentication ([^\s]+)', flags=re.IGNORECASE)
        rpasswd = re.compile('.*?PasswordAuthentication ([^\s]+)', flags=re.IGNORECASE)
        repasswd = re.compile('.*?PermitEmptyPasswords ([^\s]+)', flags=re.IGNORECASE)

        for line in ss:
            if re.match(rroot, line):
                r['root'] = True if 'yes' in re.match(rroot, line).group(1) else False
            elif re.match(rpkey, line):
                r['pkey'] = True if 'yes' in re.match(rpkey, line).group(1) else False
            elif re.match(rpasswd, line):
                r['passwd'] = True if 'yes' in re.match(rpasswd, line).group(1) else False
            elif re.match(repasswd, line):
                r['epasswd'] = True if 'yes' in re.match(repasswd, line).group(1) else False

        return r

    def save(self, s):
        conf = ConfManager.get().load('ssh', '/etc/ssh/sshd_config').split('\n')
        f = ''
        rroot = re.compile('.*?PermitRootLogin ([^\s]+)', flags=re.IGNORECASE)
        rpkey = re.compile('.*?PubkeyAuthentication ([^\s]+)', flags=re.IGNORECASE)
        rpasswd = re.compile('.*?PasswordAuthentication ([^\s]+)', flags=re.IGNORECASE)
        repasswd = re.compile('.*?PermitEmptyPasswords ([^\s]+)', flags=re.IGNORECASE)
        for line in conf:
            if re.match(rroot, line):
                if s['root'] is True:
                    f += 'PermitRootLogin yes\n'
                else:
                    f += 'PermitRootLogin no\n'
            elif re.match(rpkey, line):
                if s['pkey'] is True:
                    f += 'PubkeyAuthentication yes\n'
                else:
                    f += 'PubkeyAuthentication no\n'
            elif re.match(rpasswd, line):
                if s['passwd'] is True:
                    f += 'PasswordAuthentication yes\n'
                else:
                    f += 'PasswordAuthentication no\n'
            elif re.match(repasswd, line):
                if s['epasswd'] is True:
                    f += 'PermitEmptyPasswords yes\n'
                else:
                    f += 'PermitEmptyPasswords no\n'
            else:
                f += line + '\n'
        ConfManager.get().save('ssh', '/etc/ssh/sshd_config', f)
        ConfManager.get().commit('ssh')
        mgr = self.app.get_backend(apis.services.IServiceManager)
        if mgr.get_status('sshd') == 'running':
            mgr.real_restart('sshd')


class PKey:
    def __init__(self):
        self.type = '';
        self.key = '';
        self.name = '';


class PKeysConfig(Plugin):
    implements(IConfigurable)
    name = 'SSH Public Keys'
    iconfont = 'gen-console'
    id = 'ssh_pkeys'

    def list_files(self):
        filelist = []
        for user in self.app.gconfig.options('users'):
            if user == 'root':
                filelist.extend('/root/.ssh/authorized_keys')
            else:
                filelist.extend(os.path.join('/home', user, '.ssh', 'authorized_keys'))
        return filelist

    def read(self):
        if self.app.auth.user == 'anonymous':
            self.currentuser = 'root'
            if not os.path.exists('/root/.ssh'):
                os.makedirs('/root/.ssh')
                os.chown('/root/.ssh', 0, 100)
            if not os.path.exists('/root/.ssh/authorized_keys'):
                open('/root/.ssh/authorized_keys', 'w').write('')
                os.chown('/root/.ssh/authorized_keys', 0, 100)
        else:
            self.currentuser = self.app.auth.user

        for user in self.app.gconfig.options('users'):
            try:
                uid = pwd.getpwnam(user).pw_uid
            except KeyError:
                continue
            user_home = '/root' if user == 'root' else os.path.join('/home', user)
            if not os.path.exists(os.path.join(user_home, '.ssh')):
                os.makedirs(os.path.join(user_home, '.ssh'))
                os.chown(os.path.join(user_home, '.ssh'), uid, 100)
            if not os.path.exists(os.path.join(user_home, '.ssh', 'authorized_keys')):
                f = open(os.path.join(user_home, '.ssh', 'authorized_keys'), 'w')
                f.write('')
                f.close()
                os.chown(os.path.join(user_home, '.ssh', 'authorized_keys'), uid, 100)

        ss = ConfManager.get().load('ssh_pkeys', 
            os.path.join('/root' if self.currentuser == 'root' else os.path.join('/home', self.currentuser), '.ssh', 'authorized_keys')).split('\n')
        r = []

        for s in ss:
            if s != '' and s[0] != '#':
                k = PKey()
                s = s.split()
                try:
                    k.type = s[0]
                    k.key = s[1]
                    k.name = s[2]
                except:
                    pass
                r.append(k)

        return r

    def save(self, data):
        if self.app.auth.user == 'anonymous':
            self.currentuser = 'root'
        else:
            self.currentuser = self.app.auth.user

        try:
            pwd.getpwnam(self.currentuser)
        except KeyError:
            raise Exception('%s not a valid system user' % self.currentuser)

        d = ''
        for k in data:
            d += '%s %s %s\n' % (k.type, k.key, k.name)
        ConfManager.get().save('ssh_pkeys', 
            os.path.join('/root' if self.currentuser == 'root' else os.path.join('/home/', self.currentuser), 
                '.ssh', 'authorized_keys'), d)
        ConfManager.get().commit('ssh_pkeys')

########NEW FILE########
__FILENAME__ = main
from genesis.ui import *
from genesis.api import *
from genesis import apis

import backend


class SSHPlugin(apis.services.ServiceControlPlugin):
    text = 'SSH'
    iconfont = 'gen-console'
    folder = 'advanced'

    def on_init(self):
        ss = backend.SSHConfig(self.app)
        pk = backend.PKeysConfig(self.app)
        self.ssh = ss.read()
        self.pkeys = pk.read()

    def on_session_start(self):
        self._editing = None

    def get_main_ui(self):
        ui = self.app.inflate('ssh:main')
        t = ui.find('list')

        for h in self.pkeys:
            t.append(UI.DTR(
                UI.Label(text=h.type),
                UI.Label(text=h.name),
                UI.HContainer(
                    UI.TipIcon(
                        iconfont='gen-pencil-2',
                        id='edit/' + str(self.pkeys.index(h)),
                        text='Edit'
                    ),
                    UI.TipIcon(
                        iconfont='gen-cancel-circle',
                        id='del/' + str(self.pkeys.index(h)),
                        text='Delete',
                        warning='Remove %s public key'%h.name
                    )
                ),
            ))

        ui.find('root').set('checked', self.ssh['root'])
        ui.find('pkey').set('checked', self.ssh['pkey'])
        ui.find('passwd').set('checked', self.ssh['passwd'])
        ui.find('epasswd').set('checked', self.ssh['epasswd'])

        if self._editing is not None:
            try:
                h = self.pkeys[self._editing]
            except:
                h = backend.PKey()
            wholekey = h.type + ' ' + h.key + ' ' + h.name
            ui.find('dlgEdit').set('value', wholekey)
        else:
            ui.remove('dlgEdit')

        return ui

    @event('button/click')
    def on_click(self, event, params, vars = None):
        if params[0] == 'add':
            self._editing = len(self.pkeys)
        if params[0] == 'edit':
            self._editing = int(params[1])
        if params[0] == 'del':
            self.pkeys.pop(int(params[1]))
            try:
                backend.PKeysConfig(self.app).save(self.pkeys)
            except Exception, e:
                self.put_message('err', 'Failed to save private keys config: %s' % str(e))

    @event('form/submit')
    @event('dialog/submit')
    def on_submit(self, event, params, vars = None):
        if params[0] == 'dlgEdit':
            v = vars.getvalue('value', '')
            if vars.getvalue('action', '') == 'OK':
                h = backend.PKey()
                data = vars.getvalue('value', '').split()
                try:
                    h.type = data[0]
                    h.key = data[1]
                    h.name = data[2]
                except:
                    pass
                try:
                    self.pkeys[self._editing] = h
                except:
                    self.pkeys.append(h)
                try:
                    backend.PKeysConfig(self.app).save(self.pkeys)
                except Exception, e:
                    self.put_message('err', 'Failed to save private keys config: %s' % str(e))
            self._editing = None
        if params[0] == 'frmSSH':
            v = vars.getvalue('value', '')
            if vars.getvalue('action', '') == 'OK':
                self.ssh['root'] = True if vars.getvalue('root', True) is '1' else False
                self.ssh['pkey'] = True if vars.getvalue('pkey', False) is '1' else False
                self.ssh['passwd'] = True if vars.getvalue('passwd', True) is '1' else False
                self.ssh['epasswd'] = True if vars.getvalue('epasswd', False) is '1' else False
                backend.SSHConfig(self.app).save(self.ssh)
                self.put_message('info', 'Saved')

########NEW FILE########
__FILENAME__ = client
import ConfigParser
import os

from genesis import apis
from genesis.com import Plugin
from genesis.utils import shell, shell_status


class SVClient(Plugin):
    def test(self):
        mgr = self.app.get_backend(apis.services.IServiceManager)
        return mgr.get_status('supervisord') == 'running'

    def run(self, cmd):
        return shell('supervisorctl ' + cmd)

    def status(self):
        r = {}
        if self.test():
            for l in self.run('status').splitlines():
                l = l.split(None, 2)
                r[l[0]] = {
                    'status': '' if len(l)<2 else l[1],
                    'info': '' if len(l)<3 else l[2]
                }
        return r

    def list(self):
        r = []
        s = self.status()
        if not os.path.exists('/etc/supervisor.d'):
            os.mkdir('/etc/supervisor.d')
        for x in os.listdir('/etc/supervisor.d'):
            x = x.split('.ini')[0]
            r.append({
                'name': x,
                'ptype': self.get_type(x),
                'status': s[x]['status'] if s else 'Unknown',
                'info': s[x]['info'] if s else 'Unknown'
            })
        return r

    def start(self, id):
        self.run('start ' + id)

    def restart(self, id):
        self.run('restart ' + id)

    def stop(self, id):
        self.run('stop ' + id)

    def tail(self, id):
        return self.run('tail ' + id)

    def get(self, id):
        d = []
        if os.path.exists(os.path.join('/etc/supervisor.d', id+'.ini')):
            c = ConfigParser.RawConfigParser()
            c.read(os.path.join('/etc/supervisor.d', id+'.ini'))
            for x in c.items(c.sections()[0]):
                d.append(x)
        return d

    def get_type(self, id):
        c = ConfigParser.RawConfigParser()
        c.read(os.path.join('/etc/supervisor.d', id+'.ini'))
        return c.sections()[0].split(':')[0]

    def set(self, ptype, id, cfg, restart=True):
        name = '%s:%s'%(ptype,id)
        c = ConfigParser.RawConfigParser()
        c.add_section(name)
        for x in cfg:
            c.set(name, x[0], x[1])
        c.write(open(os.path.join('/etc/supervisor.d', id+'.ini'), 'w'))
        if restart:
            self.run('reload')

    def remove(self, id, restart=False):
        self.stop(id)
        if os.path.exists(os.path.join('/etc/supervisor.d', id+'.ini')):
            os.unlink(os.path.join('/etc/supervisor.d', id+'.ini'))
        if restart:
            self.run('reload')

########NEW FILE########
__FILENAME__ = main
from genesis.ui import *
from genesis.com import Plugin, implements
from genesis.api import *
from genesis.utils import *
from genesis import apis

from client import SVClient


class SVPlugin(apis.services.ServiceControlPlugin):
    text = 'Supervisor'
    iconfont = 'gen-bullhorn'
    folder = 'system'

    def on_session_start(self):
        self._client = SVClient(self.app)
        self._tail = None
        self._set = None

    def get_main_ui(self):
        ui = self.app.inflate('supervisor:main')

        if not self._client.test():
            self.put_message('err', 'Supervisor is not running. '
                'Please start it via the Status button to see your tasks.')

        for x in self._client.list():
            ui.append('list', UI.DTR(
                UI.Label(text=x['name']),
                UI.Label(text=x['ptype']),
                UI.Label(text=x['status']),
                UI.Label(text=x['info']),
                UI.HContainer(
                    UI.TipIcon(
                        id='start/'+x['name'],
                        text='Start',
                        iconfont='gen-play-2',
                    ) if x['status'] != 'RUNNING' else None,
                    UI.TipIcon(
                        id='restart/'+x['name'],
                        text='Restart',
                        iconfont='gen-loop-2',
                    ) if x['status'] == 'RUNNING' else None,
                    UI.TipIcon(
                        id='stop/'+x['name'],
                        text='Stop',
                        iconfont='gen-stop',
                    ) if x['status'] == 'RUNNING' else None,
                    UI.TipIcon(
                        id='set/'+x['ptype']+'/'+x['name'],
                        text='Edit',
                        iconfont='gen-pencil',
                    ),
                    UI.TipIcon(
                        id='remove/'+x['name'],
                        text='Remove',
                        iconfont='gen-cancel-circle',
                        warning='Are you sure you want to remove the process %s?'%x['name']
                    ),
                    UI.TipIcon(
                        id='tail/'+x['name'],
                        text='Show logs',
                        iconfont='gen-paste',
                    )
                ),
            ))

        if self._tail:
            ui.append('main', UI.InputBox(
                value=self._client.tail(self._tail),
                hidecancel=True,
                extra='code', id='dlgTail'
            ))

        if self._set and self._set != True:
            ui.find('p%s'%self._set[0]).set('selected', True)
            ui.find('name').set('value', self._set[1])
            ui.find('config').set('value', '\n'.join(['%s = %s' % (x[0], x[1]) for x in self._client.get(self._set[1])]))
        elif not self._set:
            ui.remove('dlgSet')

        return ui

    @event('button/click')
    def on_button(self, event, params, vars=None):
        if params[0] == 'start':
            self._client.start(params[1])
        if params[0] == 'restart':
            self._client.restart(params[1])
        if params[0] == 'stop':
            self._client.stop(params[1])
        if params[0] == 'set':
            if len(params) >= 2:
                self._set = (params[1], params[2])
            else:
                self._set = True
        if params[0] == 'remove':
            self._client.remove(params[1])
        if params[0] == 'tail':
            self._tail = params[1]
        if params[0] == 'reload':
            self._client.run('reload')

    @event('dialog/submit')
    def on_submit(self, event, params, vars=None):
        if params[0] == 'dlgTail':
            self._tail = None
        elif params[0] == 'dlgSet':
            if vars.getvalue('action', '') == 'OK':
                name = vars.getvalue('name', '')
                ptype = vars.getvalue('ptype', '')
                cfg = vars.getvalue('config', '')
                self._client.set(ptype, name, [x.split(' = ') for x in cfg.split('\n')])
                if self._set and self._set != True and name != self._set[1]:
                    self._client.remove(self._set[1])
            self._set = None


class SVListener(Plugin):
    implements(apis.orders.IListener)
    id = 'supervisor'

    def order(self, op, name, ptype='program', args=[]):
        if op == 'new':
            SVClient(self.app).set(ptype, name, args)
        elif op == 'del':
            SVClient(self.app).remove(name, restart=True)
        elif op == 'rel':
            SVClient(self.app).restart(name)

########NEW FILE########
__FILENAME__ = widget
from genesis.ui import *
from genesis import apis
from genesis.com import implements, Plugin
from genesis.api import *

from client import SVClient


class SVWidget(Plugin):
    implements(apis.dashboard.IWidget)
    iconfont = 'gen-bullhorn'
    name = 'Supervisor'
    title = 'Supervisor'
    style = 'linear'

    def __init__(self):
        self.iface = None

    def get_ui(self, cfg, id=None):
        mgr = SVClient(self.app)
        running = False

        for x in mgr.list():
            if x['name'] == cfg and x['status'] == 'RUNNING':
                running = True

        self.title = cfg
        self.iconfont = 'gen-' + ('play-2' if running else 'stop')

        ui = self.app.inflate('supervisor:widget')
        if running:
            ui.remove('start')
            ui.find('stop').set('id', id+'/stop')
            ui.find('restart').set('id', id+'/restart')
        else:
            ui.remove('stop')
            ui.remove('restart')
            ui.find('start').set('id', id+'/start')
        return ui

    def handle(self, event, params, cfg, vars=None):
        mgr = SVClient(self.app)
        if params[0] == 'start':
            mgr.start(cfg)
        if params[0] == 'stop':
            mgr.stop(cfg)
        if params[0] == 'restart':
            mgr.restart(cfg)

    def get_config_dialog(self):
        mgr = SVClient(self.app)
        dlg = self.app.inflate('supervisor:widget-config')
        for s in mgr.list():
            dlg.append('list', UI.SelectOption(
                value=s['name'],
                text=s['name'],
            ))
        return dlg

    def process_config(self, vars):
        return vars.getvalue('svc', None)

########NEW FILE########
__FILENAME__ = main
#coding: utf-8
from genesis.ui import *
from genesis.com import implements
from genesis.api import *
from genesis.utils import *
from genesis import apis

import psutil
import signal
import os


class TaskManagerPlugin(CategoryPlugin):
    text = 'Task Monitor'
    iconfont = 'gen-enter'
    folder = 'advanced'

    rev_sort = [
        'get_cpu_percent',
        'get_memory_percent',
    ]

    def on_session_start(self):
        self._sort = ('pid', False)
        self._info = None

    def sort_key(self, x):
        z = getattr(x,self._sort[0])
        return z() if callable(z) else z

    def get_ui(self):
        ui = self.app.inflate('taskmgr:main')
        l = psutil.get_process_list()
        l = sorted(l, key=self.sort_key)
        if self._sort[1]:
            l = reversed(l)

        for x in l:
            try:
                ui.append('list', UI.DTR(
                    UI.IconFont(iconfont='gen-%s'%('play-2' if x.is_running() else 'stop')),
                    UI.Label(text=str(x.pid)),
                    UI.Label(text=str(int(x.get_cpu_percent()))),
                    UI.Label(text=str(int(x.get_memory_percent()))),
                    UI.Label(text=x.username),
                    UI.Label(text=x.name),
                    UI.TipIcon(
                        iconfont='gen-info',
                        id='info/%i'%x.pid,
                        text='Info'
                    )
                ))
            except:
                pass

        hdr = ui.find('sort/'+self._sort[0])
        hdr.set('text', ('↑ ' if self._sort[1] else '↓ ')+ hdr['text'])

        if self._info is not None:
            try:
                p = filter(lambda x:x.pid==self._info, l)[0]
                iui = self.app.inflate('taskmgr:info')
                iui.find('name').set('text', '%i / %s'%(p.pid,p.name))
                iui.find('cmd').set('text', ' '.join("'%s'"%x for x in p.cmdline))
                iui.find('uid').set('text', '%s (%s)'%(p.username,p.uids.real))
                iui.find('gid').set('text', str(p.gids.real))
                iui.find('times').set('text', ' / '.join(str(x) for x in p.get_cpu_times()))
                if p.parent:
                    iui.find('parent').set('text', p.parent.name)
                    iui.find('parentinfo').set('id', 'info/%i'%p.parent.pid)
                else:
                    iui.remove('parentRow')

                sigs = [
                    (x, getattr(signal, x))
                    for x in dir(signal)
                    if x.startswith('SIG')
                ]

                for x in sigs:
                    iui.append('sigs', UI.SelectOption(
                        text=x[0], value=x[1]
                    ))
                ui.append('main', iui)
            except:
                pass

        return ui

    @event('button/click')
    def on_button(self, event, params, vars=None):
        if params[0] == 'info':
            self._info = int(params[1])
            return

        try:
            x = filter(lambda p:p.pid==self._info, psutil.get_process_list())[0]
        except:
            return
        if params[0] == 'suspend':
            x.suspend()
        if params[0] == 'resume':
            x.resume()

    @event('linklabel/click')
    def on_sort(self, event, params, vars=None):
        if params[1] == self._sort[0]:
            self._sort = (self._sort[0], not self._sort[1])
        else:
            self._sort = (params[1], params[1] in self.rev_sort)

    @event('dialog/submit')
    @event('form/submit')
    def on_submit(self, event, params, vars=None):
        if params[0] == 'dlgInfo':
            self._info = None
        if params[0] == 'frmKill':
            self._info = None
            try:
                x = filter(lambda p:p.pid==self._info, psutil.get_process_list())[0]
                x.kill(int(vars.getvalue('signal', None)))
                self.put_message('info', 'Killed process')
            except:
                self.put_message('err', 'Can\'t kill process')

########NEW FILE########
__FILENAME__ = config
from genesis.api import ModuleConfig
from main import *


class GeneralConfig(ModuleConfig):
    target = TerminalPlugin
    platform = ['any']
    
    labels = {
        'shell': 'Shell'
    }
    
    shell = 'su'

########NEW FILE########
__FILENAME__ = main
from genesis.api import *
from genesis.utils import *
from genesis.ui import *

import os
import sys
import signal
import json
import gzip
import StringIO
import pty
import subprocess as sp
import fcntl
import pty
from base64 import b64decode, b64encode
from PIL import Image, ImageDraw

from gevent.event import Event
import gevent

import pyte


TERM_W = 160
TERM_H = 40


class TerminalPlugin(CategoryPlugin, URLHandler):
    text = 'Terminal'
    iconfont = 'gen-console'
    folder = 'advanced'

    def on_session_start(self):
        self._terminals = {}
        self._tid = 1
        self._terminals[0] = Terminal()
        
    def get_ui(self):
        ui = self.app.inflate('terminal:main')
        for id in self._terminals:
            ui.append('main', UI.TerminalThumbnail(
                id=id
            ))
        return ui

    @event('button/click')
    def onclick(self, event, params, vars=None):
        if params[0] == 'add':
            self._terminals[self._tid] = Terminal()
            self._tid += 1

    @event('term/kill')
    def onkill(self, event, params, vars=None):
        id = int(params[0])
        self._terminals[id].kill()
        del self._terminals[id]
    
    @url('^/terminal/.*$')
    def get(self, req, start_response):
        params = req['PATH_INFO'].split('/')[1:] + ['']
        id = int(params[1])

        if self._terminals[id].dead():
            self._terminals[id].start(self.app.get_config(self).shell)

        if params[2] in ['history', 'get']:
            if params[2] == 'history':
                data = self._terminals[id]._proc.history()
            else:
                data = self._terminals[id]._proc.read()
            sio = StringIO.StringIO()
            gz = gzip.GzipFile(fileobj=sio, mode='w')
            gz.write(json.dumps(data))
            gz.close()
            return b64encode(sio.getvalue())

        if params[2] == 'post':
            data = params[3]
            self._terminals[id].write(b64decode(data))
            return ''

        if params[2] == 'kill':
            self._terminals[id].restart()

        page = self.app.inflate('terminal:page')
        page.find('title').text = shell('echo `whoami`@`hostname`')
        page.append('main', UI.JS(
            code='termInit(\'%i\');'%id
        ))
        return page.render()


    @url('^/terminal-thumb/.*$')
    def get_thumb(self, req, start_response):
        params = req['PATH_INFO'].split('/')[1:]
        id = int(params[1])

        if self._terminals[id].dead():
            self._terminals[id].start(self.app.get_config(self).shell)

        img = Image.new("RGB", (TERM_W, TERM_H*2+20))
        draw = ImageDraw.Draw(img)
        draw.rectangle([0,0,TERM_W,TERM_H], fill=(0,0,0))

        colors = ['black', 'darkgrey', 'darkred', 'red', 'darkgreen',
                  'green', 'brown', 'yellow', 'darkblue', 'blue',
                  'darkmagenta', 'magenta', 'darkcyan', 'cyan',
                  'lightgrey', 'white'] 

        for y in range(0,TERM_H):
            for x in range(0,TERM_W):
                fc = self._terminals[id]._proc.term[y][x][1]
                if fc == 'default': fc = 'lightgray'
                fc = ImageDraw.ImageColor.getcolor(fc, 'RGB')
                bc = self._terminals[id]._proc.term[y][x][2]
                if bc == 'default': bc = 'black'
                bc = ImageDraw.ImageColor.getcolor(bc, 'RGB')
                ch = self._terminals[id]._proc.term[y][x][0]
                draw.point((x,10+y*2+1),fill=(fc if ord(ch) > 32 else bc))
                draw.point((x,10+y*2),fill=bc)

        sio = StringIO.StringIO()
        img.save(sio, 'PNG')
        start_response('200 OK', [('Content-type', 'image/png')])
        return sio.getvalue()


class Terminal:
    def __init__(self):
        self._proc = None

    def start(self, app):
        env = {}
        env.update(os.environ)
        env['TERM'] = 'linux'
        env['COLUMNS'] = str(TERM_W)
        env['LINES'] = str(TERM_H)
        env['LC_ALL'] = 'en_US.UTF8'
        sh = app 

        pid, master = pty.fork()
        if pid == 0:
            p = sp.Popen(
                sh,
                shell=True,
                close_fds=True,
                env=env,
            )
            p.wait()
            sys.exit(0)
        self._proc = PTYProtocol(pid, master)

    def restart(self):
        if self._proc is not None:
            self._proc.kill()
        self.start()

    def dead(self):
        return self._proc is None 

    def write(self, data):
        self._proc.write(data)

    def kill(self):
        self._proc.kill()


class PTYProtocol():
    def __init__(self, proc, stream):
        self.data = ''
        self.proc = proc
        self.master = stream

        fd = self.master
        fl = fcntl.fcntl(fd, fcntl.F_GETFL)
        fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)

        self.mstream = os.fdopen(self.master, 'r+')
        gevent.sleep(2)
        self.term = pyte.DiffScreen(TERM_W,TERM_H)
        self.stream = pyte.Stream()
        self.stream.attach(self.term)
        self.data = ''
        self.unblock()

    def unblock(self):
        fd = self.master
        fl = fcntl.fcntl(fd, fcntl.F_GETFL)
        fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)

    def block(self):
        fd = self.master
        fl = fcntl.fcntl(fd, fcntl.F_GETFL)
        fcntl.fcntl(fd, fcntl.F_SETFL, fl - os.O_NONBLOCK)

    def read(self):
        cond = Event()
        def reread():
            cond.set()
            cond.clear()
        for i in range(0,45):
            try:
                d = self.mstream.read()
                self.data += d
                if len(self.data) > 0:
                    u = unicode(str(self.data))
                    self.stream.feed(u)
                    self.data = ''
                break
            except IOError, e:
                pass
            except UnicodeDecodeError, e:
                print 'UNICODE'
            gevent.spawn_later(0.33, reread)
            cond.wait(timeout=0.33)
        return self.format()

    def history(self):
        return self.format(full=True)

    def format(self, full=False):
        l = {}
        self.term.dirty.add(self.term.cursor.y)
        for k in self.term.dirty:
            l[k] = self.term[k]
        self.term.dirty.clear()
        r = {
            'lines': self.term if full else l,
            'cx': self.term.cursor.x,
            'cy': self.term.cursor.y,
            'cursor': not self.term.cursor.hidden,
        }
        return r

    def write(self, data):
        self.block()
        self.mstream.write(data)
        self.mstream.flush()
        self.unblock()

    def kill(self):
        os.kill(self.proc, 9)

########NEW FILE########
__FILENAME__ = charsets
# -*- coding: utf-8 -*-
"""
    pyte.charsets
    ~~~~~~~~~~~~~~

    This module defines ``G0`` and ``G1`` charset mappings the same way
    they are defined for linux terminal, see
    ``linux/drivers/tty/consolemap.c`` @ http://git.kernel.org

    .. note:: ``VT100_MAP`` and ``IBMPC_MAP`` were taken unchanged
              from linux kernel source and therefore are licensed
              under **GPL**.

    :copyright: (c) 2011 by Selectel, see AUTHORS for more details.
    :license: LGPL, see LICENSE for more details.
"""

from __future__ import unicode_literals


#: Latin1.
LAT1_MAP = map(unichr, xrange(256))

#: VT100 graphic character set.
VT100_MAP = "".join(unichr(c) for c in [
    0x0000, 0x0001, 0x0002, 0x0003, 0x0004, 0x0005, 0x0006, 0x0007,
    0x0008, 0x0009, 0x000a, 0x000b, 0x000c, 0x000d, 0x000e, 0x000f,
    0x0010, 0x0011, 0x0012, 0x0013, 0x0014, 0x0015, 0x0016, 0x0017,
    0x0018, 0x0019, 0x001a, 0x001b, 0x001c, 0x001d, 0x001e, 0x001f,
    0x0020, 0x0021, 0x0022, 0x0023, 0x0024, 0x0025, 0x0026, 0x0027,
    0x0028, 0x0029, 0x002a, 0x2192, 0x2190, 0x2191, 0x2193, 0x002f,
    0x2588, 0x0031, 0x0032, 0x0033, 0x0034, 0x0035, 0x0036, 0x0037,
    0x0038, 0x0039, 0x003a, 0x003b, 0x003c, 0x003d, 0x003e, 0x003f,
    0x0040, 0x0041, 0x0042, 0x0043, 0x0044, 0x0045, 0x0046, 0x0047,
    0x0048, 0x0049, 0x004a, 0x004b, 0x004c, 0x004d, 0x004e, 0x004f,
    0x0050, 0x0051, 0x0052, 0x0053, 0x0054, 0x0055, 0x0056, 0x0057,
    0x0058, 0x0059, 0x005a, 0x005b, 0x005c, 0x005d, 0x005e, 0x00a0,
    0x25c6, 0x2592, 0x2409, 0x240c, 0x240d, 0x240a, 0x00b0, 0x00b1,
    0x2591, 0x240b, 0x2518, 0x2510, 0x250c, 0x2514, 0x253c, 0x23ba,
    0x23bb, 0x2500, 0x23bc, 0x23bd, 0x251c, 0x2524, 0x2534, 0x252c,
    0x2502, 0x2264, 0x2265, 0x03c0, 0x2260, 0x00a3, 0x00b7, 0x007f,
    0x0080, 0x0081, 0x0082, 0x0083, 0x0084, 0x0085, 0x0086, 0x0087,
    0x0088, 0x0089, 0x008a, 0x008b, 0x008c, 0x008d, 0x008e, 0x008f,
    0x0090, 0x0091, 0x0092, 0x0093, 0x0094, 0x0095, 0x0096, 0x0097,
    0x0098, 0x0099, 0x009a, 0x009b, 0x009c, 0x009d, 0x009e, 0x009f,
    0x00a0, 0x00a1, 0x00a2, 0x00a3, 0x00a4, 0x00a5, 0x00a6, 0x00a7,
    0x00a8, 0x00a9, 0x00aa, 0x00ab, 0x00ac, 0x00ad, 0x00ae, 0x00af,
    0x00b0, 0x00b1, 0x00b2, 0x00b3, 0x00b4, 0x00b5, 0x00b6, 0x00b7,
    0x00b8, 0x00b9, 0x00ba, 0x00bb, 0x00bc, 0x00bd, 0x00be, 0x00bf,
    0x00c0, 0x00c1, 0x00c2, 0x00c3, 0x00c4, 0x00c5, 0x00c6, 0x00c7,
    0x00c8, 0x00c9, 0x00ca, 0x00cb, 0x00cc, 0x00cd, 0x00ce, 0x00cf,
    0x00d0, 0x00d1, 0x00d2, 0x00d3, 0x00d4, 0x00d5, 0x00d6, 0x00d7,
    0x00d8, 0x00d9, 0x00da, 0x00db, 0x00dc, 0x00dd, 0x00de, 0x00df,
    0x00e0, 0x00e1, 0x00e2, 0x00e3, 0x00e4, 0x00e5, 0x00e6, 0x00e7,
    0x00e8, 0x00e9, 0x00ea, 0x00eb, 0x00ec, 0x00ed, 0x00ee, 0x00ef,
    0x00f0, 0x00f1, 0x00f2, 0x00f3, 0x00f4, 0x00f5, 0x00f6, 0x00f7,
    0x00f8, 0x00f9, 0x00fa, 0x00fb, 0x00fc, 0x00fd, 0x00fe, 0x00ff
])

#: IBM Codepage 437.
IBMPC_MAP = "".join(unichr(c) for c in [
    0x0000, 0x263a, 0x263b, 0x2665, 0x2666, 0x2663, 0x2660, 0x2022,
    0x25d8, 0x25cb, 0x25d9, 0x2642, 0x2640, 0x266a, 0x266b, 0x263c,
    0x25b6, 0x25c0, 0x2195, 0x203c, 0x00b6, 0x00a7, 0x25ac, 0x21a8,
    0x2191, 0x2193, 0x2192, 0x2190, 0x221f, 0x2194, 0x25b2, 0x25bc,
    0x0020, 0x0021, 0x0022, 0x0023, 0x0024, 0x0025, 0x0026, 0x0027,
    0x0028, 0x0029, 0x002a, 0x002b, 0x002c, 0x002d, 0x002e, 0x002f,
    0x0030, 0x0031, 0x0032, 0x0033, 0x0034, 0x0035, 0x0036, 0x0037,
    0x0038, 0x0039, 0x003a, 0x003b, 0x003c, 0x003d, 0x003e, 0x003f,
    0x0040, 0x0041, 0x0042, 0x0043, 0x0044, 0x0045, 0x0046, 0x0047,
    0x0048, 0x0049, 0x004a, 0x004b, 0x004c, 0x004d, 0x004e, 0x004f,
    0x0050, 0x0051, 0x0052, 0x0053, 0x0054, 0x0055, 0x0056, 0x0057,
    0x0058, 0x0059, 0x005a, 0x005b, 0x005c, 0x005d, 0x005e, 0x005f,
    0x0060, 0x0061, 0x0062, 0x0063, 0x0064, 0x0065, 0x0066, 0x0067,
    0x0068, 0x0069, 0x006a, 0x006b, 0x006c, 0x006d, 0x006e, 0x006f,
    0x0070, 0x0071, 0x0072, 0x0073, 0x0074, 0x0075, 0x0076, 0x0077,
    0x0078, 0x0079, 0x007a, 0x007b, 0x007c, 0x007d, 0x007e, 0x2302,
    0x00c7, 0x00fc, 0x00e9, 0x00e2, 0x00e4, 0x00e0, 0x00e5, 0x00e7,
    0x00ea, 0x00eb, 0x00e8, 0x00ef, 0x00ee, 0x00ec, 0x00c4, 0x00c5,
    0x00c9, 0x00e6, 0x00c6, 0x00f4, 0x00f6, 0x00f2, 0x00fb, 0x00f9,
    0x00ff, 0x00d6, 0x00dc, 0x00a2, 0x00a3, 0x00a5, 0x20a7, 0x0192,
    0x00e1, 0x00ed, 0x00f3, 0x00fa, 0x00f1, 0x00d1, 0x00aa, 0x00ba,
    0x00bf, 0x2310, 0x00ac, 0x00bd, 0x00bc, 0x00a1, 0x00ab, 0x00bb,
    0x2591, 0x2592, 0x2593, 0x2502, 0x2524, 0x2561, 0x2562, 0x2556,
    0x2555, 0x2563, 0x2551, 0x2557, 0x255d, 0x255c, 0x255b, 0x2510,
    0x2514, 0x2534, 0x252c, 0x251c, 0x2500, 0x253c, 0x255e, 0x255f,
    0x255a, 0x2554, 0x2569, 0x2566, 0x2560, 0x2550, 0x256c, 0x2567,
    0x2568, 0x2564, 0x2565, 0x2559, 0x2558, 0x2552, 0x2553, 0x256b,
    0x256a, 0x2518, 0x250c, 0x2588, 0x2584, 0x258c, 0x2590, 0x2580,
    0x03b1, 0x00df, 0x0393, 0x03c0, 0x03a3, 0x03c3, 0x00b5, 0x03c4,
    0x03a6, 0x0398, 0x03a9, 0x03b4, 0x221e, 0x03c6, 0x03b5, 0x2229,
    0x2261, 0x00b1, 0x2265, 0x2264, 0x2320, 0x2321, 0x00f7, 0x2248,
    0x00b0, 0x2219, 0x00b7, 0x221a, 0x207f, 0x00b2, 0x25a0, 0x00a0
])


MAPS = {
    "B": LAT1_MAP,
    "0": VT100_MAP,
    "U": IBMPC_MAP
}

########NEW FILE########
__FILENAME__ = control
# -*- coding: utf-8 -*-
"""
    pyte.control
    ~~~~~~~~~~~~

    This module defines simple control sequences, recognized by
    :class:`~pyte.streams.Stream`, the set of codes here is for
    ``TERM=linux`` which is a superset of VT102.

    :copyright: (c) 2011 by Selectel, see AUTHORS for more details.
    :license: LGPL, see LICENSE for more details.
"""

from __future__ import unicode_literals

#: *Space*: Not suprisingly -- ``" "``.
SP = " "

#: *Null*: Does nothing.
NUL = "\u0000"

#: *Bell*: Beeps.
BEL = "\u0007"

#: *Backspace*: Backspace one column, but not past the begining of the
#: line.
BS = "\u0008"

#: *Horizontal tab*: Move cursor to the next tab stop, or to the end
#: of the line if there is no earlier tab stop.
HT = "\u0009"

#: *Linefeed*: Give a line feed, and, if :data:`pyte.modes.LNM` (new
#: line mode) is set also a carriage return.
LF = "\n"
#: *Vertical tab*: Same as :data:`LF`.
VT = "\u000b"
#: *Form feed*: Same as :data:`LF`.
FF = "\u000c"

#: *Carriage return*: Move cursor to left margin on current line.
CR = "\r"

#: *Shift out*: Activate G1 character set.
SO = "\u000e"

#: *Shift in*: Activate G0 character set.
SI = "\u000f"

#: *Cancel*: Interrupt escape sequence. If received during an escape or
#: control sequence, cancels the sequence and displays substitution
#: character.
CAN = "\u0018"
#: *Substitute*: Same as :data:`CAN`.
SUB = "\u001a"

#: *Escape*: Starts an escape sequence.
ESC = "\u001b"

#: *Delete*: Is ingored.
DEL = "\u007f"

#: *Control sequence introducer*: An equavalent for ``ESC [``.
CSI = "\u009b"

########NEW FILE########
__FILENAME__ = escape
# -*- coding: utf-8 -*-
"""
    pyte.escape
    ~~~~~~~~~~~

    This module defines bot CSI and non-CSI escape sequences, recognized
    by :class:`~pyte.streams.Stream` and subclasses.

    :copyright: (c) 2011 by Selectel, see AUTHORS for more details.
    :license: LGPL, see LICENSE for more details.
"""

from __future__ import unicode_literals


#: *Reset*.
RIS = "c"

#: *Index*: Move cursor down one line in same column. If the cursor is
#: at the bottom margin, the screen performs a scroll-up.
IND = "D"

#: *Next line*: Same as :data:`pyte.control.LF`.
NEL = "E"

#: Tabulation set: Set a horizontal tab stop at cursor position.
HTS = "H"

#: *Reverse index*: Move cursor up one line in same column. If the
#: cursor is at the top margin, the screen performs a scroll-down.
RI = "M"

#: Save cursor: Save cursor position, character attribute (graphic
#: rendition), character set, and origin mode selection (see
#: :data:`DECRC`).
DECSC = "7"

#: *Restore cursor*: Restore previously saved cursor position, character
#: attribute (graphic rendition), character set, and origin mode
#: selection. If none were saved, move cursor to home position.
DECRC = "8"


# "Sharp" escape sequences.
# -------------------------

#: *Alignment display*: Fill screen with uppercase E's for testing
#: screen focus and alignment.
DECALN = "8"


# ECMA-48 CSI sequences.
# ---------------------

#: *Insert character*: Insert the indicated # of blank characters.
ICH = "@"

#: *Cursor up*: Move cursor up the indicated # of lines in same column.
#: Cursor stops at top margin.
CUU = "A"

#: *Cursor down*: Move cursor down the indicated # of lines in same
#: column. Cursor stops at bottom margin.
CUD = "B"

#: *Cursor forward*: Move cursor right the indicated # of columns.
#: Cursor stops at right margin.
CUF = "C"

#: *Cursor back*: Move cursor left the indicated # of columns. Cursor
#: stops at left margin.
CUB = "D"

#: *Cursor next line*: Move cursor down the indicated # of lines to
#: column 1.
CNL = "E"

#: *Cursor previous line*: Move cursor up the indicated # of lines to
#: column 1.
CPL = "F"

#: *Cursor horizontal align*: Move cursor to the indicated column in
#: current line.
CHA = "G"

#: *Cursor position*: Move cursor to the indicated line, column (origin
#: at ``1, 1``).
CUP = "H"

#: *Erase data* (default: from cursor to end of line).
ED = "J"

#: *Erase in line* (default: from cursor to end of line).
EL = "K"

#: *Insert line*: Insert the indicated # of blank lines, starting from
#: the current line. Lines displayed below cursor move down. Lines moved
#: past the bottom margin are lost.
IL = "L"

#: *Delete line*: Delete the indicated # of lines, starting from the
#: current line. As lines are deleted, lines displayed below cursor
#: move up. Lines added to bottom of screen have spaces with same
#: character attributes as last line move up.
DL = "M"

#: *Delete character*: Delete the indicated # of characters on the
#: current line. When character is deleted, all characters to the right
#: of cursor move left.
DCH = "P"

#: *Erase character*: Erase the indicated # of characters on the
#: current line.
ECH = "X"

#: *Horizontal position relative*: Same as :data:`CUF`.
HPR = "a"

#: *Vertical position adjust*: Move cursor to the indicated line,
#: current column.
VPA = "d"

#: *Vertical position relative*: Same as :data:`CUD`.
VPR = "e"

#: *Horizontal / Vertical position*: Same as :data:`CUP`.
HVP = "f"

#: *Tabulation clear*: Clears a horizontal tab stop at cursor position.
TBC = "g"

#: *Set mode*.
SM = "h"

#: *Reset mode*.
RM = "l"

#: *Select graphics rendition*: The terminal can display the following
#: character attributes that change the character display without
#: changing the character (see :mod:`pyte.graphics`).
SGR = "m"

#: *Select top and bottom margins*: Selects margins, defining the
#: scrolling region; parameters are top and bottom line. If called
#: without any arguments, whole screen is used.
DECSTBM = "r"

#: *Horizontal position adjust*: Same as :data:`CHA`.
HPA = "'"

########NEW FILE########
__FILENAME__ = graphics
# -*- coding: utf-8 -*-
"""
    pyte.graphics
    ~~~~~~~~~~~~~

    This module defines graphic-related constants, mostly taken from
    :manpage:`console_codes(4)` and
    http://pueblo.sourceforge.net/doc/manual/ansi_color_codes.html.

    :copyright: (c) 2011 by Selectel, see AUTHORS for more details.
    :license: LGPL, see LICENSE for more details.
"""

#: A mapping of ANSI text style codes to style names, "+" means the:
#: attribute is set, "-" -- reset; example:
#:
#: >>> text[1]
#: '+bold'
#: >>> text[9]
#: '+strikethrough'
TEXT = {
    1: "+bold" ,
    3: "+italics",
    4: "+underscore",
    7: "+reverse",
    9: "+strikethrough",
    22: "-bold",
    23: "-italics",
    24: "-underscore",
    27: "-reverse",
    29: "-strikethrough"
}


#: A mapping of ANSI foreground color codes to color names, example:
#:
#: >>> FG[30]
#: 'black'
#: >>> FG[38]
#: 'default'
FG = {
    30: "black",
    31: "red",
    32: "green",
    33: "brown",
    34: "blue",
    35: "magenta",
    36: "cyan",
    37: "white",
    39: "default"  # white.
}

#: A mapping of ANSI background color codes to color names, example:
#:
#: >>> BG[40]
#: 'black'
#: >>> BG[48]
#: 'default'
BG = {
    40: "black",
    41: "red",
    42: "green",
    43: "brown",
    44: "blue",
    45: "magenta",
    46: "cyan",
    47: "white",
    49: "default"  # black.
}

# Reverse mapping of all available attributes -- keep this private!
_SGR = dict((v, k) for k, v in BG.items() + FG.items() + TEXT.items())

########NEW FILE########
__FILENAME__ = modes
# -*- coding: utf-8 -*-
"""
    pyte.modes
    ~~~~~~~~~~

    This module defines terminal mode switches, used by
    :class:`~pyte.screens.Screen`. There're two types of terminal modes:

    * `non-private` which should be set with ``ESC [ N h``, where ``N``
      is an integer, representing mode being set; and
    * `private` which should be set with ``ESC [ ? N h``.

    The latter are shifted 5 times to the right, to be easily
    distinguishable from the former ones; for example `Origin Mode`
    -- :data:`DECOM` is ``192`` not ``6``.

    >>> DECOM
    192

    :copyright: (c) 2011 by Selectel, see AUTHORS for more details.
    :license: LGPL, see LICENSE for more details.
"""

#: *Line Feed/New Line Mode*: When enabled, causes a received
#: :data:`~pyte.control.LF`, :data:`pyte.control.FF`, or
#: :data:`~pyte.control.VT` to move the cursor to the first column of
#: the next line.
LNM = 20

#: *Insert/Replace Mode*: When enabled, new display characters move
#: old display characters to the right. Characters moved past the
#: right margin are lost. Otherwise, new display characters replace
#: old display characters at the cursor position.
IRM = 4


# Private modes.
# ..............

#: *Text Cursor Enable Mode*: determines if the text cursor is
#: visible.
DECTCEM = 25 << 5

#: *Screen Mode*: toggles screen-wide reverse-video mode.
DECSCNM = 5 << 5

#: *Origin Mode*: allows cursor addressing relative to a user-defined
#: origin. This mode resets when the terminal is powered up or reset.
#: It does not affect the erase in display (ED) function.
DECOM = 6 << 5

#: *Auto Wrap Mode*: selects where received graphic characters appear
#: when the cursor is at the right margin.
DECAWM = 7 << 5

#: *Column Mode*: selects the number of columns per line (80 or 132)
#: on the screen.
DECCOLM = 3 << 5

########NEW FILE########
__FILENAME__ = screens
# -*- coding: utf-8 -*-
"""
    pyte.screens
    ~~~~~~~~~~~~

    This module provides classes for terminal screens, currently
    it contains three screens with different features:

    * :class:`~pyte.screens.Screen` -- base screen implementation,
      which handles all the core escape sequences, recognized by
      :class:`~pyte.streams.Stream`.
    * If you need a screen to keep track of the changed lines
      (which you probably do need) -- use
      :class:`~pyte.screens.DiffScreen`.
    * If you also want a screen to collect history and allow
      pagination -- :class:`pyte.screen.HistoryScreen` is here
      for ya ;)

    .. note:: It would be nice to split those features into mixin
              classes, rather than subclasses, but it's not obvious
              how to do -- feel free to submit a pull request.

    :copyright: (c) 2011 Selectel, see AUTHORS for more details.
    :license: LGPL, see LICENSE for more details.
"""

from __future__ import (
    absolute_import, print_function, unicode_literals, division
)

import copy
import math
import operator
from collections import namedtuple, deque
from itertools import islice, repeat

from . import modes as mo, graphics as g, charsets as cs


try:
    xrange
except NameError:
    pass
else:
    range = xrange


def take(n, iterable):
    """Returns first n items of the iterable as a list."""
    return list(islice(iterable, n))


#: A container for screen's scroll margins.
Margins = namedtuple("Margins", "top bottom")

#: A container for savepoint, created on :data:`~pyte.escape.DECSC`.
Savepoint = namedtuple("Savepoint", [
    "cursor",
    "g0_charset",
    "g1_charset",
    "charset",
    "origin",
    "wrap"
])

#: A container for a single character, field names are *hopefully*
#: self-explanatory.
_Char = namedtuple("_Char", [
    "data",
    "fg",
    "bg",
    "bold",
    "italics",
    "underscore",
    "strikethrough",
    "reverse",
])


class Char(_Char):
    """A wrapper around :class:`_Char`, providing some useful defaults
    for most of the attributes.
    """
    def __new__(cls, data, fg="default", bg="default", bold=False,
                italics=False, underscore=False, reverse=False,
                strikethrough=False):
        return _Char.__new__(cls, data, fg, bg, bold, italics, underscore,
                             reverse, strikethrough)


class Cursor(object):
    """Screen cursor.

    :param int x: horizontal cursor position.
    :param int y: vertical cursor position.
    :param pyte.screens.Char attrs: cursor attributes (see
        :meth:`~pyte.screens.Screen.selectel_graphic_rendition`
        for details).
    """
    def __init__(self, x, y, attrs=Char(" ")):
        self.x, self.y, self.attrs, self.hidden = x, y, attrs, False


class Screen(list):
    """
    A screen is an in-memory matrix of characters that represents the
    screen display of the terminal. It can be instantiated on it's own
    and given explicit commands, or it can be attached to a stream and
    will respond to events.

    .. attribute:: cursor

       Reference to the :class:`~pyte.screens.Cursor` object, holding
       cursor position and attributes.

    .. attribute:: margins

       Top and bottom screen margins, defining the scrolling region;
       the actual values are top and bottom line.

    .. note::

       According to ``ECMA-48`` standard, **lines and columnns are
       1-indexed**, so, for instance ``ESC [ 10;10 f`` really means
       -- move cursor to position (9, 9) in the display matrix.

    .. seealso::

       `Standard ECMA-48, Section 6.1.1 \
       <http://www.ecma-international.org/publications/standards/Ecma-048.htm>`_
         For a description of the presentational component, implemented
         by ``Screen``.
    """
    #: A plain empty character with default foreground and background
    #: colors.
    default_char = Char(data=" ", fg="default", bg="default")

    #: An inifinite sequence of default characters, used for populating
    #: new lines and columns.
    default_line = repeat(default_char)

    def __init__(self, columns, lines):
        self.savepoints = []
        self.lines, self.columns = lines, columns
        self.reset()

    @property
    def size(self):
        """Returns screen size -- ``(lines, columns)``"""
        return self.lines, self.columns

    @property
    def display(self):
        """Returns a :func:`list` of screen lines as unicode strings."""
        return ["".join(map(operator.attrgetter("data"), line))
                for line in self]

    def __before__(self, command):
        """Hook, called **before** a command is dispatched to the
        :class:`Screen` instance.

        :param unicode command: command name, for example ``"LINEFEED"``.
        """

    def __after__(self, command):
        """Hook, called **after** a command is dispatched to the
        :class:`Screen` instance.

        :param unicode command: command name, for example ``"LINEFEED"``.
        """

    def reset(self):
        """Resets the terminal to its initial state.

        * Scroll margins are reset to screen boundaries.
        * Cursor is moved to home location -- ``(0, 0)`` and its
          attributes are set to defaults (see :attr:`default_char`).
        * Screen is cleared -- each character is reset to
          :attr:`default_char`.
        * Tabstops are reset to "every eight columns".

        .. note::

           Neither VT220 nor VT102 manuals mentioned that terminal modes
           and tabstops should be reset as well, thanks to
           :manpage:`xterm` -- we now know that.
        """
        self[:] = (take(self.columns, self.default_line)
                   for _ in range(self.lines))
        self.mode = set([mo.DECAWM, mo.DECTCEM, mo.LNM, mo.DECTCEM])
        self.margins = Margins(0, self.lines - 1)

        # According to VT220 manual and ``linux/drivers/tty/vt.c``
        # the default G0 charset is latin-1, but for reasons unknown
        # latin-1 breaks ascii-graphics; so G0 defaults to cp437.
        self.g0_charset = self.charset = cs.IBMPC_MAP
        self.g1_charset = cs.VT100_MAP

        # From ``man terminfo`` -- "... hardware tabs are initially
        # set every `n` spaces when the terminal is powered up. Since
        # we aim to support VT102 / VT220 and linux -- we use n = 8.
        self.tabstops = set(range(7, self.columns, 8))

        self.cursor = Cursor(0, 0)
        self.cursor_position()

    def resize(self, lines=None, columns=None):
        """Resize the screen to the given dimensions.

        If the requested screen size has more lines than the existing
        screen, lines will be added at the bottom. If the requested
        size has less lines than the existing screen lines will be
        clipped at the top of the screen. Similarly, if the existing
        screen has less columns than the requested screen, columns will
        be added at the right, and if it has more -- columns will be
        clipped at the right.

        .. note:: According to `xterm`, we should also reset origin
                  mode and screen margins, see ``xterm/screen.c:1761``.

        :param int lines: number of lines in the new screen.
        :param int columns: number of columns in the new screen.
        """
        lines = lines or self.lines
        columns = columns or self.columns

        # First resize the lines:
        diff = self.lines - lines

        # a) if the current display size is less than the requested
        #    size, add lines to the bottom.
        if diff < 0:
            self.extend(take(self.columns, self.default_line)
                        for _ in range(diff, 0))
        # b) if the current display size is greater than requested
        #    size, take lines off the top.
        elif diff > 0:
            self[:diff] = ()

        # Then resize the columns:
        diff = self.columns - columns

        # a) if the current display size is less than the requested
        #    size, expand each line to the new size.
        if diff < 0:
            for y in range(lines):
                self[y].extend(take(abs(diff), self.default_line))
        # b) if the current display size is greater than requested
        #    size, trim each line from the right to the new size.
        elif diff > 0:
            self[:] = (line[:columns] for line in self)

        self.lines, self.columns = lines, columns
        self.margins = Margins(0, self.lines - 1)
        self.reset_mode(mo.DECOM)

    def set_margins(self, top=None, bottom=None):
        """Selects top and bottom margins for the scrolling region.

        Margins determine which screen lines move during scrolling
        (see :meth:`index` and :meth:`reverse_index`). Characters added
        outside the scrolling region do not cause the screen to scroll.

        :param int top: the smallest line number that is scrolled.
        :param int bottom: the biggest line number that is scrolled.
        """
        if top is None or bottom is None:
            return

        # Arguments are 1-based, while :attr:`margins` are zero based --
        # so we have to decrement them by one. We also make sure that
        # both of them is bounded by [0, lines - 1].
        top = max(0, min(top - 1, self.lines - 1))
        bottom = max(0, min(bottom - 1, self.lines - 1))

        # Even though VT102 and VT220 require DECSTBM to ignore regions
        # of width less than 2, some programs (like aptitude for example)
        # rely on it. Practicality beats purity.
        if bottom - top >= 1:
            self.margins = Margins(top, bottom)

            # The cursor moves to the home position when the top and
            # bottom margins of the scrolling region (DECSTBM) changes.
            self.cursor_position()

    def set_charset(self, code, mode):
        """Set active ``G0`` or ``G1`` charset.

        :param unicode code: character set code, should be a character
                             from ``"B0UK"`` -- otherwise ignored.
        :param unicode mode: if ``"("`` ``G0`` charset is set, if
                             ``")"`` -- we operate on ``G1``.

        .. warning:: User-defined charsets are currently not supported.
        """
        if code in cs.MAPS:
            setattr(self, {"(": "g0_charset", ")": "g1_charset"}[mode],
                    cs.MAPS[code])

    def set_mode(self, *modes, **kwargs):
        """Sets (enables) a given list of modes.

        :param list modes: modes to set, where each mode is a constant
                           from :mod:`pyte.modes`.
        """
        # Private mode codes are shifted, to be distingiushed from non
        # private ones.
        if kwargs.get("private"):
            modes = [mode << 5 for mode in modes]

        self.mode.update(modes)

        # When DECOLM mode is set, the screen is erased and the cursor
        # moves to the home position.
        if mo.DECCOLM in modes:
            self.resize(columns=132)
            self.erase_in_display(2)
            self.cursor_position()

        # According to `vttest`, DECOM should also home the cursor, see
        # vttest/main.c:303.
        if mo.DECOM in modes:
            self.cursor_position()

        # Mark all displayed characters as reverse.
        if mo.DECSCNM in modes:
            self[:] = ([char._replace(reverse=True) for char in line]
                       for line in self)
            self.select_graphic_rendition(g._SGR["+reverse"])

        # Make the cursor visible.
        if mo.DECTCEM in modes:
            self.cursor.hidden = False

    def reset_mode(self, *modes, **kwargs):
        """Resets (disables) a given list of modes.

        :param list modes: modes to reset -- hopefully, each mode is a
                           constant from :mod:`pyte.modes`.
        """
        # Private mode codes are shifted, to be distingiushed from non
        # private ones.
        if kwargs.get("private"):
            modes = [mode << 5 for mode in modes]

        self.mode.difference_update(modes)

        # Lines below follow the logic in :meth:`set_mode`.
        if mo.DECCOLM in modes:
            self.resize(columns=80)
            self.erase_in_display(2)
            self.cursor_position()

        if mo.DECOM in modes:
            self.cursor_position()

        if mo.DECSCNM in modes:
            self[:] = ([char._replace(reverse=False) for char in line]
                       for line in self)
            self.select_graphic_rendition(g._SGR["-reverse"])

        # Hide the cursor.
        if mo.DECTCEM in modes:
            self.cursor.hidden = True

    def shift_in(self):
        """Activates ``G0`` character set."""
        self.charset = self.g0_charset

    def shift_out(self):
        """Activates ``G1`` character set."""
        self.charset = self.g1_charset

    def draw(self, char):
        """Display a character at the current cursor position and advance
        the cursor if :data:`~pyte.modes.DECAWM` is set.

        :param unicode char: a character to display.
        """
        # Translating a given character.
        char = char.translate(self.charset)

        # If this was the last column in a line and auto wrap mode is
        # enabled, move the cursor to the next line. Otherwise replace
        # characters already displayed with newly entered.
        if self.cursor.x == self.columns:
            if mo.DECAWM in self.mode:
                self.linefeed()
            else:
                self.cursor.x -= 1

        # If Insert mode is set, new characters move old characters to
        # the right, otherwise terminal is in Replace mode and new
        # characters replace old characters at cursor position.
        if mo.IRM in self.mode:
            self.insert_characters(1)

        self[self.cursor.y][self.cursor.x] = self.cursor.attrs \
            ._replace(data=char)

        # .. note:: We can't use :meth:`cursor_forward()`, because that
        #           way, we'll never know when to linefeed.
        self.cursor.x += 1

    def carriage_return(self):
        """Move the cursor to the beginning of the current line."""
        self.cursor.x = 0

    def index(self):
        """Move the cursor down one line in the same column. If the
        cursor is at the last line, create a new line at the bottom.
        """
        top, bottom = self.margins

        if self.cursor.y == bottom:
            self.pop(top)
            self.insert(bottom, take(self.columns, self.default_line))
        else:
            self.cursor_down()

    def reverse_index(self):
        """Move the cursor up one line in the same column. If the cursor
        is at the first line, create a new line at the top.
        """
        top, bottom = self.margins

        if self.cursor.y == top:
            self.pop(bottom)
            self.insert(top, take(self.columns, self.default_line))
        else:
            self.cursor_up()

    def linefeed(self):
        """Performs an index and, if :data:`~pyte.modes.LNM` is set, a
        carriage return.
        """
        self.index()

        if mo.LNM in self.mode:
            self.carriage_return()

    def tab(self):
        """Move to the next tab space, or the end of the screen if there
        aren't anymore left.
        """
        for stop in sorted(self.tabstops):
            if self.cursor.x < stop:
                column = stop
                break
        else:
            column = self.columns - 1

        self.cursor.x = column

    def backspace(self):
        """Move cursor to the left one or keep it in it's position if
        it's at the beginning of the line already.
        """
        self.cursor_back()

    def save_cursor(self):
        """Push the current cursor position onto the stack."""
        self.savepoints.append(Savepoint(copy.copy(self.cursor),
                                         self.g0_charset,
                                         self.g1_charset,
                                         self.charset,
                                         mo.DECOM in self.mode,
                                         mo.DECAWM in self.mode))

    def restore_cursor(self):
        """Set the current cursor position to whatever cursor is on top
        of the stack.
        """
        if self.savepoints:
            savepoint = self.savepoints.pop()

            self.g0_charset = savepoint.g0_charset
            self.g1_charset = savepoint.g1_charset
            self.charset = savepoint.charset

            if savepoint.origin: self.set_mode(mo.DECOM)
            if savepoint.wrap: self.set_mode(mo.DECAWM)

            self.cursor = savepoint.cursor
            self.ensure_bounds(use_margins=True)
        else:
            # If nothing was saved, the cursor moves to home position;
            # origin mode is reset. :todo: DECAWM?
            self.reset_mode(mo.DECOM)
            self.cursor_position()

    def insert_lines(self, count=None):
        """Inserts the indicated # of lines at line with cursor. Lines
        displayed **at** and below the cursor move down. Lines moved
        past the bottom margin are lost.

        :param count: number of lines to delete.
        """
        count = count or 1
        top, bottom = self.margins

        # If cursor is outside scrolling margins it -- do nothin'.
        if top <= self.cursor.y <= bottom:
            #                           v +1, because range() is exclusive.
            for line in range(self.cursor.y, min(bottom + 1, self.cursor.y + count)):
                self.pop(bottom)
                self.insert(line, take(self.columns, self.default_line))

            self.carriage_return()

    def delete_lines(self, count=None):
        """Deletes the indicated # of lines, starting at line with
        cursor. As lines are deleted, lines displayed below cursor
        move up. Lines added to bottom of screen have spaces with same
        character attributes as last line moved up.

        :param int count: number of lines to delete.
        """
        count = count or 1
        top, bottom = self.margins

        # If cursor is outside scrolling margins it -- do nothin'.
        if top <= self.cursor.y <= bottom:
            #                v -- +1 to include the bottom margin.
            for _ in range(min(bottom - self.cursor.y + 1, count)):
                self.pop(self.cursor.y)
                self.insert(bottom, list(
                    repeat(self.cursor.attrs, self.columns)))

            self.carriage_return()

    def insert_characters(self, count=None):
        """Inserts the indicated # of blank characters at the cursor
        position. The cursor does not move and remains at the beginning
        of the inserted blank characters. Data on the line is shifted
        forward.

        :param int count: number of characters to insert.
        """
        count = count or 1

        for _ in range(min(self.columns - self.cursor.y, count)):
            self[self.cursor.y].insert(self.cursor.x, self.cursor.attrs)
            self[self.cursor.y].pop()

    def delete_characters(self, count=None):
        """Deletes the indicated # of characters, starting with the
        character at cursor position. When a character is deleted, all
        characters to the right of cursor move left. Character attributes
        move with the characters.

        :param int count: number of characters to delete.
        """
        count = count or 1

        for _ in range(min(self.columns - self.cursor.x, count)):
            self[self.cursor.y].pop(self.cursor.x)
            self[self.cursor.y].append(self.cursor.attrs)

    def erase_characters(self, count=None):
        """Erases the indicated # of characters, starting with the
        character at cursor position. Character attributes are set
        cursor attributes. The cursor remains in the same position.

        :param int count: number of characters to erase.

        .. warning::

           Even though *ALL* of the VTXXX manuals state that character
           attributes **should be reset to defaults**, ``libvte``,
           ``xterm`` and ``ROTE`` completely ignore this. Same applies
           too all ``erase_*()`` and ``delete_*()`` methods.
        """
        count = count or 1

        for column in range(self.cursor.x, min(self.cursor.x + count, self.columns)):
            self[self.cursor.y][column] = self.cursor.attrs

    def erase_in_line(self, type_of=0, private=False):
        """Erases a line in a specific way.

        :param int type_of: defines the way the line should be erased in:

            * ``0`` -- Erases from cursor to end of line, including cursor
              position.
            * ``1`` -- Erases from beginning of line to cursor, including cursor
              position.
            * ``2`` -- Erases complete line.
        :param bool private: when ``True`` character attributes aren left
                             unchanged **not implemented**.
        """
        interval = (
            # a) erase from the cursor to the end of line, including
            # the cursor,
            range(self.cursor.x, self.columns),
            # b) erase from the beginning of the line to the cursor,
            # including it,
            range(0, self.cursor.x + 1),
            # c) erase the entire line.
            range(0, self.columns)
        )[type_of]

        for column in interval:
            self[self.cursor.y][column] = self.cursor.attrs

    def erase_in_display(self, type_of=0, private=False):
        """Erases display in a specific way.

        :param int type_of: defines the way the line should be erased in:

            * ``0`` -- Erases from cursor to end of screen, including
              cursor position.
            * ``1`` -- Erases from beginning of screen to cursor,
              including cursor position.
            * ``2`` -- Erases complete display. All lines are erased
              and changed to single-width. Cursor does not move.
        :param bool private: when ``True`` character attributes aren left
                             unchanged **not implemented**.
        """
        interval = (
            # a) erase from cursor to the end of the display, including
            # the cursor,
            range(self.cursor.y + 1, self.lines),
            # b) erase from the beginning of the display to the cursor,
            # including it,
            range(0, self.cursor.y),
            # c) erase the whole display.
            range(0, self.lines)
        )[type_of]

        for line in interval:
            self[line][:] = \
                (self.cursor.attrs for _ in range(self.columns))

        # In case of 0 or 1 we have to erase the line with the cursor.
        if type_of in [0, 1]:
            self.erase_in_line(type_of)

    def set_tab_stop(self):
        """Sest a horizontal tab stop at cursor position."""
        self.tabstops.add(self.cursor.x)

    def clear_tab_stop(self, type_of=None):
        """Clears a horizontal tab stop in a specific way, depending
        on the ``type_of`` value:

        * ``0`` or nothing -- Clears a horizontal tab stop at cursor
          position.
        * ``3`` -- Clears all horizontal tab stops.
        """
        if not type_of:
            # Clears a horizontal tab stop at cursor position, if it's
            # present, or silently fails if otherwise.
            self.tabstops.discard(self.cursor.x)
        elif type_of == 3:
            self.tabstops = set()  # Clears all horizontal tab stops.

    def ensure_bounds(self, use_margins=None):
        """Ensure that current cursor position is within screen bounds.

        :param bool use_margins: when ``True`` or when
                                 :data:`~pyte.modes.DECOM` is set,
                                 cursor is bounded by top and and bottom
                                 margins, instead of ``[0; lines - 1]``.
        """
        if use_margins or mo.DECOM in self.mode:
            top, bottom = self.margins
        else:
            top, bottom = 0, self.lines - 1

        self.cursor.x = min(max(0, self.cursor.x), self.columns - 1)
        self.cursor.y = min(max(top, self.cursor.y), bottom)

    def cursor_up(self, count=None):
        """Moves cursor up the indicated # of lines in same column.
        Cursor stops at top margin.

        :param int count: number of lines to skip.
        """
        self.cursor.y -= count or 1
        self.ensure_bounds(use_margins=True)

    def cursor_up1(self, count=None):
        """Moves cursor up the indicated # of lines to column 1. Cursor
        stops at bottom margin.

        :param int count: number of lines to skip.
        """
        self.cursor_up(count)
        self.carriage_return()

    def cursor_down(self, count=None):
        """Moves cursor down the indicated # of lines in same column.
        Cursor stops at bottom margin.

        :param int count: number of lines to skip.
        """
        self.cursor.y += count or 1
        self.ensure_bounds(use_margins=True)

    def cursor_down1(self, count=None):
        """Moves cursor down the indicated # of lines to column 1.
        Cursor stops at bottom margin.

        :param int count: number of lines to skip.
        """
        self.cursor_down(count)
        self.carriage_return()

    def cursor_back(self, count=None):
        """Moves cursor left the indicated # of columns. Cursor stops
        at left margin.

        :param int count: number of columns to skip.
        """
        self.cursor.x -= count or 1
        self.ensure_bounds()

    def cursor_forward(self, count=None):
        """Moves cursor right the indicated # of columns. Cursor stops
        at right margin.

        :param int count: number of columns to skip.
        """
        self.cursor.x += count or 1
        self.ensure_bounds()

    def cursor_position(self, line=None, column=None):
        """Set the cursor to a specific `line` and `column`.

        Cursor is allowed to move out of the scrolling region only when
        :data:`~pyte.modes.DECOM` is reset, otherwise -- the position
        doesn't change.

        :param int line: line number to move the cursor to.
        :param int column: column number to move the cursor to.
        """
        column = (column or 1) - 1
        line = (line or 1) - 1

        # If origin mode (DECOM) is set, line number are relative to
        # the top scrolling margin.
        if mo.DECOM in self.mode:
            line += self.margins.top

            # Cursor is not allowed to move out of the scrolling region.
            if not self.margins.top <= line <= self.margins.bottom:
                return

        self.cursor.x, self.cursor.y = column, line
        self.ensure_bounds()

    def cursor_to_column(self, column=None):
        """Moves cursor to a specific column in the current line.

        :param int column: column number to move the cursor to.
        """
        self.cursor.x = (column or 1) - 1
        self.ensure_bounds()

    def cursor_to_line(self, line=None):
        """Moves cursor to a specific line in the current column.

        :param int line: line number to move the cursor to.
        """
        self.cursor.y = (line or 1) - 1

        # If origin mode (DECOM) is set, line number are relative to
        # the top scrolling margin.
        if mo.DECOM in self.mode:
            self.cursor.y += self.margins.top

            # FIXME: should we also restrict the cursor to the scrolling
            # region?

        self.ensure_bounds()

    def bell(self, *args):
        """Bell stub -- the actual implementation should probably be
        provided by the end-user.
        """

    def alignment_display(self):
        """Fills screen with uppercase E's for screen focus and alignment."""
        for line in self:
            for column, char in enumerate(line):
                line[column] = char._replace(data="E")

    def select_graphic_rendition(self, *attrs):
        """Set display attributes.

        :param list attrs: a list of display attributes to set.
        """
        replace = {}

        for attr in attrs or [0]:
            if attr in g.FG:
                replace["fg"] = g.FG[attr]
            elif attr in g.BG:
                replace["bg"] = g.BG[attr]
            elif attr in g.TEXT:
                attr = g.TEXT[attr]
                replace[attr[1:]] = attr.startswith("+")
            elif not attr:
                replace = self.default_char._asdict()

        self.cursor.attrs = self.cursor.attrs._replace(**replace)


class DiffScreen(Screen):
    """A screen subclass, which maintains a set of dirty lines in its
    :attr:`dirty` attribute. The end user is responsible for emptying
    a set, when a diff is applied.

    .. attribute:: dirty

       A set of line numbers, which should be re-drawn.

       >>> screen = DiffScreen(80, 24)
       >>> screen.dirty.clear()
       >>> screen.draw(u"!")
       >>> screen.dirty
       set([0])
    """
    def __init__(self, *args):
        self.dirty = set()
        super(DiffScreen, self).__init__(*args)

    def set_mode(self, *modes, **kwargs):
       	if mo.DECSCNM >> 5 in modes and kwargs.get("private"):
            self.dirty.update(range(self.lines))
        super(DiffScreen, self).set_mode(*modes, **kwargs)

    def reset_mode(self, *modes, **kwargs):
        if mo.DECSCNM >> 5 in modes and kwargs.get("private"):
            self.dirty.update(range(self.lines))
        super(DiffScreen, self).reset_mode(*modes, **kwargs)

    def reset(self):
        self.dirty.update(range(self.lines))
        super(DiffScreen, self).reset()

    def resize(self, *args, **kwargs):
        self.dirty.update(range(self.lines))
        super(DiffScreen, self).resize(*args, **kwargs)

    def draw(self, *args):
        self.dirty.add(self.cursor.y)
        super(DiffScreen, self).draw(*args)

    def index(self):
        if self.cursor.y == self.margins.bottom:
            self.dirty.update(range(self.lines))

        super(DiffScreen, self).index()

    def reverse_index(self):
        if self.cursor.y == self.margins.top:
            self.dirty.update(range(self.lines))

        super(DiffScreen, self).reverse_index()

    def insert_lines(self, *args):
        self.dirty.update(range(self.cursor.y, self.lines))
        super(DiffScreen, self).insert_lines(*args)

    def delete_lines(self, *args):
        self.dirty.update(range(self.cursor.y, self.lines))
        super(DiffScreen, self).delete_lines(*args)

    def insert_characters(self, *args):
        self.dirty.add(self.cursor.y)
        super(DiffScreen, self).insert_characters(*args)

    def delete_characters(self, *args):
        self.dirty.add(self.cursor.y)
        super(DiffScreen, self).delete_characters(*args)

    def erase_characters(self, *args):
        self.dirty.add(self.cursor.y)
        super(DiffScreen, self).erase_characters(*args)

    def erase_in_line(self, *args):
        self.dirty.add(self.cursor.y)
        super(DiffScreen, self).erase_in_line(*args)

    def erase_in_display(self, type_of=0):
        self.dirty.update((
            range(self.cursor.y + 1, self.lines),
            range(0, self.cursor.y),
            range(0, self.lines)
        )[type_of])
        super(DiffScreen, self).erase_in_display(type_of)

    def alignment_display(self):
        self.dirty.update(range(self.lines))
        super(DiffScreen, self).alignment_display()


History = namedtuple("History", "top bottom ratio size position")


class HistoryScreen(DiffScreen):
    """A screen subclass, which keeps track of screen history and allows
    pagination. This is not linux-specific, but still useful; see  page
    462 of VT520 User's Manual.

    :param int history: total number of history lines to keep; is split
                        between top and bottom queues.
    :param int ratio: defines how much lines to scroll on :meth:`next_page`
                      and :meth:`prev_page` calls.

    .. attribute:: history

       A pair of history queues for top and bottom margins accordingly;
       here's the overall screen structure::

            [ 1: .......]
            [ 2: .......]  <- top history
            [ 3: .......]
            ------------
            [ 4: .......]  s
            [ 5: .......]  c
            [ 6: .......]  r
            [ 7: .......]  e
            [ 8: .......]  e
            [ 9: .......]  n
            ------------
            [10: .......]
            [11: .......]  <- bottom history
            [12: .......]

    .. note::

       Don't forget to update :class:`~pyte.streams.Stream` class with
       appropriate escape sequences -- you can use any, since pagination
       protocol is not standardized, for example::

           Stream.escape["N"] = "next_page"
           Stream.escape["P"] = "prev_page"
    """

    def __init__(self, columns, lines, history=100, ratio=.5):
        self.history = History(deque(maxlen=history // 2),
                               deque(maxlen=history),
                               float(ratio),
                               history,
                               history)

        super(HistoryScreen, self).__init__(columns, lines)

    def __before__(self, command):
        """Ensures a screen is at the bottom of the history buffer."""
        if command not in ["prev_page", "next_page"]:
            while self.history.position < self.history.size:
                self.next_page()

        super(HistoryScreen, self).__before__(command)

    def __after__(self, command):
        """Ensures all lines on a screen have proper width (attr:`columns`).

        Extra characters are truncated, missing characters are filled
        with whitespace.
        """
        if command in ["prev_page", "next_page"]:
            for idx, line in enumerate(self):
                if len(line) > self.columns:
                    self[idx] = line[:self.columns]
                elif len(line) < self.columns:
                    self[idx] = line + take(self.columns - len(line),
                                            self.default_line)

        # If we're at the bottom of the history buffer and `DECTCEM`
        # mode is set -- show the cursor.
        self.cursor.hidden = not (
            abs(self.history.position - self.history.size) < self.lines and
            mo.DECTCEM in self.mode
        )

        super(HistoryScreen, self).__after__(command)

    def reset(self):
        """Overloaded to reset screen history state: history position
        is reset to bottom of both queues;  queues themselves are
        emptied.
        """
        super(HistoryScreen, self).reset()

        self.history.top.clear()
        self.history.bottom.clear()
        self.history = self.history._replace(position=self.history.size)

    def index(self):
        """Overloaded to update top history with the removed lines."""
        top, bottom = self.margins

        if self.cursor.y == bottom:
            self.history.top.append(self[top])

        super(HistoryScreen, self).index()

    def reverse_index(self):
        """Overloaded to update bottom history with the removed lines."""
        top, bottom = self.margins

        if self.cursor.y == top:
            self.history.bottom.append(self[bottom])

        super(HistoryScreen, self).reverse_index()

    def prev_page(self):
        """Moves the screen page up through the history buffer. Page
        size is defined by ``history.ratio``, so for instance
        ``ratio = .5`` means that half the screen is restored from
        history on page switch.
        """
        if self.history.position > self.lines and self.history.top:
            mid = min(len(self.history.top),
                      int(math.ceil(self.lines * self.history.ratio)))

            self.history.bottom.extendleft(reversed(self[-mid:]))
            self.history = self.history \
                ._replace(position=self.history.position - self.lines)

            self[:] = list(reversed([
                self.history.top.pop() for _ in range(mid)
            ])) + self[:-mid]

            self.dirty = set(range(self.lines))

            if len(self) is not self.lines or self.history.position > self.history.size:
                import pdb; pdb.set_trace()


    def next_page(self):
        """Moves the screen page down through the history buffer."""
        if self.history.position < self.history.size and self.history.bottom:
            mid = min(len(self.history.bottom),
                      int(math.ceil(self.lines * self.history.ratio)))

            self.history.top.extend(self[:mid])
            self.history = self.history \
                ._replace(position=self.history.position + self.lines)

            self[:] = self[mid:] + [
                self.history.bottom.popleft() for _ in range(mid)
            ]

            self.dirty = set(range(self.lines))

            if len(self) is not self.lines or self.history.position > self.history.size:
                import pdb; pdb.set_trace()

########NEW FILE########
__FILENAME__ = streams
# -*- coding: utf-8 -*-
"""
    pyte.streams
    ~~~~~~~~~~~~

    This module provides three stream implementations with different
    features; for starters, here's a quick example of how streams are
    typically used:

    >>> import pyte
    >>>
    >>> class Dummy(object):
    ...     def __init__(self):
    ...         self.y = 0
    ...
    ...     def cursor_up(self, count=None):
    ...         self.y += count or 1
    ...
    >>> dummy = Dummy()
    >>> stream = pyte.Stream()
    >>> stream.attach(dummy)
    >>> stream.feed(u"\u001B[5A")  # Move the cursor up 5 rows.
    >>> dummy.y
    5

    :copyright: (c) 2011 by Selectel, see AUTHORS for more details.
    :license: LGPL, see LICENSE for more details.
"""

from __future__ import absolute_import, unicode_literals

import codecs
import sys

from . import control as ctrl, escape as esc


class Stream(object):
    """A stream is a state machine that parses a stream of characters
    and dispatches events based on what it sees.

    .. note::

       Stream only accepts unicode strings as input, but if, for some
       reason, you need to feed it with byte strings, consider using
       :class:`~pyte.streams.ByteStream` instead.

    .. seealso::

        `man console_codes <http://linux.die.net/man/4/console_codes>`_
            For details on console codes listed bellow in :attr:`basic`,
            :attr:`escape`, :attr:`csi` and :attr:`sharp`.
    """

    #: Control sequences, which don't require any arguments.
    basic = {
        ctrl.BEL: "bell",
        ctrl.BS: "backspace",
        ctrl.HT: "tab",
        ctrl.LF: "linefeed",
        ctrl.VT: "linefeed",
        ctrl.FF: "linefeed",
        ctrl.CR: "carriage_return",
        ctrl.SO: "shift_out",
        ctrl.SI: "shift_in",
    }

    #: non-CSI escape sequences.
    escape = {
        esc.RIS: "reset",
        esc.IND: "index",
        esc.NEL: "linefeed",
        esc.RI: "reverse_index",
        esc.HTS: "set_tab_stop",
        esc.DECSC: "save_cursor",
        esc.DECRC: "restore_cursor",
    }

    #: "sharp" escape sequences -- ``ESC # <N>``.
    sharp = {
        esc.DECALN: "alignment_display",
    }

    #: CSI escape sequences -- ``CSI P1;P2;...;Pn <fn>``.
    csi = {
        esc.ICH: "insert_characters",
        esc.CUU: "cursor_up",
        esc.CUD: "cursor_down",
        esc.CUF: "cursor_forward",
        esc.CUB: "cursor_back",
        esc.CNL: "cursor_down1",
        esc.CPL: "cursor_up1",
        esc.CHA: "cursor_to_column",
        esc.CUP: "cursor_position",
        esc.ED: "erase_in_display",
        esc.EL: "erase_in_line",
        esc.IL: "insert_lines",
        esc.DL: "delete_lines",
        esc.DCH: "delete_characters",
        esc.ECH: "erase_characters",
        esc.HPR: "cursor_forward",
        esc.VPA: "cursor_to_line",
        esc.VPR: "cursor_down",
        esc.HVP: "cursor_position",
        esc.TBC: "clear_tab_stop",
        esc.SM: "set_mode",
        esc.RM: "reset_mode",
        esc.SGR: "select_graphic_rendition",
        esc.DECSTBM: "set_margins",
        esc.HPA: "cursor_to_column",
    }

    def __init__(self):
        self.handlers = {
            "stream": self._stream,
            "escape": self._escape,
            "arguments": self._arguments,
            "sharp": self._sharp,
            "charset": self._charset
        }

        self.listeners = []
        self.reset()

    def reset(self):
        """Reset state to ``"stream"`` and empty parameter attributes."""
        self.state = "stream"
        self.flags = {}
        self.params = []
        self.current = ""

    def consume(self, char):
        """Consume a single unicode character and advance the state as
        necessary.

        :param unicode char: a unicode character to consume.
        """
        if not isinstance(char, unicode):
            raise TypeError(
                "%s requires unicode input" % self.__class__.__name__)

        try:
            self.handlers.get(self.state)(char)
        except TypeError:
            pass
        except KeyError:
            if __debug__:
                self.flags["state"] = self.state
                self.flags["unhandled"] = char
                self.dispatch("debug", *self.params)
                self.reset()
            else:
                raise

    def feed(self, chars):
        """Consume a unicode string and advance the state as necessary.

        :param unicode chars: a unicode string to feed from.
        """
        if not isinstance(chars, unicode):
            raise TypeError(
                "%s requires unicode input" % self.__class__.__name__)

        for char in chars: self.consume(char)

    def attach(self, screen, only=()):
        """Adds a given screen to the listeners queue.

        :param pyte.screens.Screen screen: a screen to attach to.
        :param list only: a list of events you want to dispatch to a
                          given screen (empty by default, which means
                          -- dispatch all events).
        """
        self.listeners.append((screen, set(only)))

    def detach(self, screen):
        """Removes a given screen from the listeners queue and failes
        silently if it's not attached.

        :param pyte.screens.Screen screen: a screen to detach.
        """
        for idx, (listener, _) in enumerate(self.listeners):
            if screen is listener:
                self.listeners.pop(idx)

    def dispatch(self, event, *args, **kwargs):
        """Dispatch an event.

        Event handlers are looked up implicitly in the listeners'
        ``__dict__``, so, if a listener only wants to handle ``DRAW``
        events it should define a ``draw()`` method or pass
        ``only=["draw"]`` argument to :meth:`attach`.

        .. warning::

           If any of the attached listeners throws an exception, the
           subsequent callbacks are be aborted.

        :param unicode event: event to dispatch.
        :param list args: arguments to pass to event handlers.
        """
        for listener, only in self.listeners:
            if only and event not in only:
                continue

            try:
                handler = getattr(listener, event)
            except AttributeError:
                continue

            if hasattr(listener, "__before__"):
                listener.__before__(event)

            handler(*args, **self.flags)

            if hasattr(listener, "__after__"):
                listener.__after__(event)
        else:
            if kwargs.get("reset", True): self.reset()

    # State transformers.
    # ...................

    def _stream(self, char):
        """Process a character when in the default ``"stream"`` state."""
        if char in self.basic:
            self.dispatch(self.basic[char])
        elif char == ctrl.ESC:
            self.state = "escape"
        elif char == ctrl.CSI:
            self.state = "arguments"
        elif char not in [ctrl.NUL, ctrl.DEL]:
            self.dispatch("draw", char)

    def _escape(self, char):
        """Handle characters seen when in an escape sequence.

        Most non-VT52 commands start with a left-bracket after the
        escape and then a stream of parameters and a command; with
        a single notable exception -- :data:`escape.DECOM` sequence,
        which starts with a sharp.
        """
        if char == "#":
            self.state = "sharp"
        elif char == "[":
            self.state = "arguments"
        elif char in "()":
            self.state = "charset"
            self.flags["mode"] = char
        else:
            self.dispatch(self.escape[char])

    def _sharp(self, char):
        """Parse arguments of a `"#"` seqence."""
        self.dispatch(self.sharp[char])

    def _charset(self, char):
        """Parse ``G0`` or ``G1`` charset code."""
        self.dispatch("set-charset", char)

    def _arguments(self, char):
        """Parse arguments of an escape sequence.

        All parameters are unsigned, positive decimal integers, with
        the most significant digit sent first. Any parameter greater
        than 9999 is set to 9999. If you do not specify a value, a 0
        value is assumed.

        .. seealso::

           `VT102 User Guide <http://vt100.net/docs/vt102-ug/>`_
               For details on the formatting of escape arguments.

           `VT220 Programmer Reference <http://http://vt100.net/docs/vt220-rm/>`_
               For details on the characters valid for use as arguments.
        """
        if char == "?":
            self.flags["private"] = True
        elif char in [ctrl.BEL, ctrl.BS, ctrl.HT, ctrl.LF, ctrl.VT,
                      ctrl.FF, ctrl.CR]:
            # Not sure why, but those seem to be allowed between CSI
            # sequence arguments.
            self.dispatch(self.basic[char], reset=False)
        elif char == ctrl.SP:
            pass
        elif char in [ctrl.CAN, ctrl.SUB]:
            # If CAN or SUB is received during a sequence, the current
            # sequence is aborted; terminal displays the substitute
            # character, followed by characters in the sequence received
            # after CAN or SUB.
            self.dispatch("draw", char)
            self.state = "stream"
        elif char.isdigit():
            self.current += char
        else:
            self.params.append(min(int(self.current or 0), 9999))

            if char == ";":
                self.current = ""
            else:
                self.dispatch(self.csi[char], *self.params)


class ByteStream(Stream):
    """A stream, which takes bytes strings (instead of unicode) as input
    and tries to decode them using a given list of possible encodings.
    It uses :class:`codecs.IncrementalDecoder` internally, so broken
    bytes is not an issue.

    By default, the following decoding strategy is used:

    * First, try strict ``"utf-8"``, proceed if recieved and
      :exc:`UnicodeDecodeError` ...
    * Try strict ``"cp437"``, failed? move on ...
    * Use ``"utf-8"`` with invalid bytes replaced -- this one will
      allways succeed.

    >>> stream = ByteStream()
    >>> stream.feed(b"foo".decode("utf-8"))
    Traceback (most recent call last):
      File "<stdin>", line 1, in <module>
      File "pyte/streams.py", line 323, in feed
        "%s requires input in bytes" % self.__class__.__name__)
    TypeError: ByteStream requires input in bytes
    >>> stream.feed(b"foo")

    :param list encodings: a list of ``(encoding, errors)`` pairs,
                           where the first element is encoding name,
                           ex: ``"utf-8"`` and second defines how
                           decoding errors should be handeld; see
                           :meth:`str.decode` for possible values.
    """

    def __init__(self, encodings=None):
        encodings = encodings or [
            ("utf-8", "strict"),
            ("cp437", "strict"),
            ("utf-8", "replace")
        ]

        self.buffer = b"", 0
        self.decoders = [codecs.getincrementaldecoder(encoding)(errors)
                         for encoding, errors in encodings]

        super(ByteStream, self).__init__()

    def feed(self, chars):
        if not isinstance(chars, bytes):
            raise TypeError(
                "%s requires input in bytes" % self.__class__.__name__)

        for decoder in self.decoders:
            decoder.setstate(self.buffer)

            try:
                chars = decoder.decode(chars)
            except UnicodeDecodeError:
                continue

            self.buffer = decoder.getstate()
            return super(ByteStream, self).feed(chars)
        else:
            raise


class DebugStream(ByteStream):
    """Stream, which dumps a subset of the dispatched events to a given
    file-like object (:data:`sys.stdout` by default).

    >>> stream = DebugStream()
    >>> stream.feed("\x1b[1;24r\x1b[4l\x1b[24;1H\x1b[0;10m")
    SET_MARGINS 1; 24
    RESET_MODE 4
    CURSOR_POSITION 24; 1
    SELECT_GRAPHIC_RENDITION 0; 10

    :param file to: a file-like object to write debug information to.
    :param list only: a list of events you want to debug (empty by
                      default, which means -- debug all events).
    """

    def __init__(self, to=sys.stdout, only=(), *args, **kwargs):
        super(DebugStream, self).__init__(*args, **kwargs)

        class Bugger(object):
            def fixup(self, arg):
                if isinstance(arg, str):
                    return arg.encode("utf-8")
                elif not isinstance(arg, unicode):
                    return str(arg)
                else:
                    return arg

            def __getattr__(self, event):
                def inner(*args, **flags):
                    to.write(event.upper() + " ")
                    to.write("; ".join(map(self.fixup, args)))
                    to.write(" ")
                    to.write(", ".join("{0}: {1}".format(name, self.fixup(arg))
                                       for name, arg in flags.iteritems()))
                    to.write("\n")
                return inner

        self.attach(Bugger(), only=only)

########NEW FILE########
__FILENAME__ = backend
import json
import os

from genesis.api import *
from genesis.com import *
from genesis import apis

class TransmissionConfig(Plugin):
    implements(IConfigurable)
    name = 'Transmission'
    id = 'transmission'
    iconfont = 'gen-download'
    serviceName = 'transmission'

    def load(self):
        self.mgr = self.app.get_backend(apis.services.IServiceManager)
        # The transmission package doesn't install the config file.
        # So if this is first run, start then stop the daemon to generate it.
        # TODO: Make this less awful
        if not os.path.exists(self.configFile):
            self.mgr.stop(self.serviceName)
            self.mgr.start(self.serviceName)
        s = ConfManager.get().load('transmission', self.configFile)
        self.config = json.loads(s)

    def save(self):
        wasrunning = False
        s = json.dumps(self.config)
        if self.mgr.get_status('transmission') == 'running':
            wasrunning = True
            self.mgr.stop(self.serviceName)
        ConfManager.get().save('transmission', self.configFile, s)
        ConfManager.get().commit('transmission')
        if wasrunning:
            self.mgr.start(self.serviceName)

    def get(self, key):
        return self.config[key]

    def set(self, key, value):
        self.config[key] = value

    def items(self):
        return self.config.items()

    def __init__(self):
        self.configFile = self.app.get_config(self).cfg_file
        self.config = {}

    def list_files(self):
        return [self.configFile]

class GeneralConfig(ModuleConfig):
    target=TransmissionConfig
    platform = ['debian', 'centos', 'arch', 'arkos', 'gentoo', 'mandriva']

    labels = {
        'cfg_file': 'Configuration file'
    }

    cfg_file = '/var/lib/transmission/.config/transmission-daemon/settings.json'

########NEW FILE########
__FILENAME__ = main
from genesis.ui import *
from genesis.api import *
from genesis import apis

import backend

class TransmissionPlugin(apis.services.ServiceControlPlugin):
    text = 'Transmission'
    iconfont = 'gen-download'
    folder = 'apps'

    def on_session_start(self):
        self._redir = False
        self._tab = 0
        self._config = backend.TransmissionConfig(self.app)
        self._config.load()
        self.plugin_info.services[0]['ports'] = [('tcp', self._config.get('rpc-port'))]
        self.update_services()

    def get_main_ui(self):
        if self._redir:
            self._redir = False
            return self.redirapp('transmission', int(self._config.get('rpc-port')))
        else:
            ui = self.app.inflate('transmission:main')
            ui.find('tabs').set('active', self._tab)

            basic = UI.FormBox(
                UI.FormLine(
                    UI.TextInput(name='download-dir', value=self._config.get('download-dir')),
                    text='Download Directory',
                ),
                UI.Formline(
                    UI.TextInput(name='rpc-port', value=self._config.get('rpc-port')),
                    text='RPC Port',
                ),
                UI.Formline(
                    UI.Checkbox( name='rpc-whitelist-enabled', checked=self._config.get('rpc-whitelist-enabled')),
                    text='RPC Whitelist Enabled',
                ),
                UI.Formline(
                    UI.TextInput(name='rpc-whitelist', value=self._config.get('rpc-whitelist')),
                    text='RPC IP Whitelist',
                ),
                id="frmBasic"
            )
            ui.append('tab0', basic)

            for k,v in sorted(self._config.items()):
                e = UI.DTR(
                    UI.IconFont(iconfont='gen-folder'),
                    UI.Label(text=k),
                    UI.Label(text=v),
                )
                ui.append('all_config', e)

            return ui

    @event('button/click')
    def on_click(self, event, params, vars = None):
        if params[0] == 'launch':
            self._redir=True

    @event('dialog/submit')
    @event('form/submit')
    def on_submit(self, event, params, vars=None):
        if params[0] == 'frmBasic':
            if vars.getvalue('action', '') == 'OK':
                self.plugin_info.services[0]['ports'] = [('tcp', vars.getvalue('rpc-port'))]
                if int(self._config.get('rpc-port')) != int(vars.getvalue('rpc-port')):
                    self.update_services()
                self._config.set('rpc-port', int(vars.getvalue('rpc-port', '')))
                self._config.set('rpc-whitelist-enabled', vars.getvalue('rpc-whitelist-enabled', '')=='1')
                self._config.set('download-dir', vars.getvalue('download-dir', ''))
                self._config.set('rpc-whitelist', vars.getvalue('rpc-whitelist', ''))
                self._config.save()
            elif vars.getvalue('action', '') == 'Cancel':
                self._config.load()

########NEW FILE########
__FILENAME__ = backend
import pylibconfig2

from genesis.api import *
from genesis.com import *
from genesis import apis
from genesis.plugins.core.api import ISSLPlugin

arkos_welcome = "Welcome to uMurmur on arkOS!"


class UMurmurConfig(Plugin):
    implements(IConfigurable)
    name = "Murmur"
    id = "umurmur"
    iconfont = "gen-phone"
    service_name = "umurmur"

    def __init__(self):
        self.config_file = self.app.get_config(self).cfg_file
        self.service_mgr = self.app.get_backend(apis.services.IServiceManager)
        self.config = pylibconfig2.Config("")

    def load(self):
        cfg_str = ConfManager.get().load('umurmur', self.config_file)
        try:
            self.config = pylibconfig2.Config(cfg_str)
        except pylibconfig2.PyLibConfigErrors as e:
            self.app.log.error(e)
        self.config.welcometext = arkos_welcome

    def save(self):
        running = self.is_service_running()
        if running:
            self.service_mgr.stop(self.service_name)
        ConfManager.get().save("umurmur", self.config_file, str(self.config))
        ConfManager.get().commit("umurmur")
        if running:
            self.service_mgr.start(self.service_name)

    def list_files(self):
        return [self.config_file]

    def is_service_running(self):
        return self.service_mgr.get_status(self.service_name) == "running"


class GeneralConfig(ModuleConfig):
    target = UMurmurConfig
    platform = ['arch', 'arkos']
    labels = {'cfg_file': 'Configuration file'}
    cfg_file = '/etc/umurmur/umurmur.conf'


class UMurmurSSLPlugin(Plugin):
    implements(ISSLPlugin)
    text = "Mumble Server (uMurmur)"
    iconfont = "gen-phone"
    cert_type = 'cert-key'

    def enable_ssl(self, cert, key):
        config = UMurmurConfig(self.app)
        config.load()
        config.config.certificate = cert
        config.config.private_key = key
        config.save()

    def disable_ssl(self):
        config = UMurmurConfig(self.app)
        config.load()
        config.config.certificate = "/etc/umurmur/umurmur.cert"
        config.config.private_key = "/etc/umurmur/umurmur.key"
        config.save()

########NEW FILE########
__FILENAME__ = main
from genesis.ui import *
from genesis.api import *
from genesis import apis
import backend


class UMurmurPlugin(apis.services.ServiceControlPlugin):
    text = 'Mumble Server'
    iconfont = 'gen-phone'
    folder = 'servers'

    def on_init(self):
        self._config = backend.UMurmurConfig(self.app)
        self._config.load()

    def on_session_start(self):
        self._tab = 0
        self._open_dialog = None
        self.update_services()

    def get_main_ui(self):
        ui = self.app.inflate('umurmur:main')
        ui.find('tabs').set('active', 'tab' + str(self._tab))
        cfg = self._config.config

        if not hasattr(cfg, "channels"):
            ui.remove('dlg_add_chan')
            ui.remove('dlg_add_chan_lnk')
            ui.append("container_settings", UI.Label(
                text="uMurmur settings file damaged. "
                     "Please reinstall uMurmur",
                size=3)
            )
            return ui

        # Tab 0: General Server Settings
        content = UI.FormBox(
            UI.FormLine(
                UI.TextInput(
                    name="welcometext",
                    value=cfg.get("welcometext", ""),
                ),
                text="Welcome text"
            ),
            UI.FormLine(
                UI.TextInput(
                    name="password",
                    value=cfg.get("password", ""),
                    password=True
                ),
                text="Server password"
            ),
            UI.FormLine(
                UI.TextInput(
                    name="max_bandwidth",
                    value=cfg.get("max_bandwidth", 48000),
                ),
                text="Max. bandwidth",
                help="In bits/second/user",
            ),
            UI.FormLine(
                UI.TextInput(
                    name="max_users",
                    value=cfg.get("max_users", 10),
                ),
                text="Max. users"
            ),
            id="form_server"
        )
        ui.append("container_settings", content)

        # Tab 1: Channels
        # TODO password for channels

        # channels
        channels = dict((c.name, c) for c in cfg.channels)
        channel_names = sorted(channels.keys())
        channel_names.remove("Root")
        channel_leaves = list()

        def recursive_add_row(chan, depth):
            children = list(
                channels[c] for c in channel_names
                if channels[c].parent == chan.name
            )
            if not children:
                channel_leaves.append(chan.name)
                delete_button = UI.TipIcon(  # only leaves can be deleted
                    iconfont='gen-cancel-circle',
                    text='Delete',
                    warning='Delete channel "%s"' % chan.name,
                    id='deleteChan/%s' % chan.name
                )
            else:
                delete_button = UI.Label(text="-")
            row = UI.DTR(
                UI.Label(text=". . "*depth + (" %s" % chan.name)),
                UI.Label(text=chan.description),
                UI.Label(text=("Yes" if chan.get("silent") else "No")),
                delete_button
            )
            ui.append('table_channels', row)
            if children:
                for c in children:
                    recursive_add_row(c, depth+1)
        recursive_add_row(channels["Root"], 0)

        # channel links
        for lnk in cfg.channel_links:
            src_dest = (lnk.source, lnk.destination)
            row = UI.DTR(
                UI.Label(text=lnk.source),
                UI.Label(text="=>"),
                UI.Label(text=lnk.destination),
                UI.TipIcon(
                    iconfont='gen-cancel-circle',
                    text='Delete',
                    warning='Delete channel link "%s => %s"' % src_dest,
                    id='deleteChanLnk/%s/%s' % src_dest
                )
            )
            ui.append('table_channel_links', row)

        # form: default channel
        def_chan = cfg.default_channel
        content = UI.FormBox(
            UI.FormLine(
                UI.SelectInput(*list(
                    UI.SelectOption(text=c, value=c, selected=(c == def_chan))
                    for c in channel_names if c != "Root"
                ), name="default_channel"),
                text="Default channel",
            ),
            id="form_def_chan"
        )
        ui.append("container_default_channel", content)

        # Tab 2: Info
        # TODO: remove info tab
        for k, v in sorted(cfg.items()):
            if k in ("password", "channel_links", "channels"):
                continue
            e = UI.DTR(
                UI.IconFont(iconfont='gen-folder'),
                UI.Label(text=k),
                UI.Label(text=v),
            )
            ui.append('all_config', e)

        # dialogs
        if self._open_dialog == 'dlg_add_channel':
            content = UI.SimpleForm(
                UI.FormLine(
                    UI.TextInput(
                        name="chan_name",
                        value=""
                    ),
                    text="Channel name"
                ),
                UI.FormLine(
                    UI.TextInput(
                        name="chan_descr",
                        value=""
                    ),
                    text="Channel description"
                ),
                UI.FormLine(
                    UI.SelectInput(*list(
                        UI.SelectOption(text=c, value=c)
                        for c in (["Root"] + channel_names),
                    ), name="chan_parent"),
                    text="Parent channel"
                ),
                UI.FormLine(
                    UI.CheckBox(
                        name="chan_silent",
                        text="Yes",
                        checked=False,
                    ),
                    text="Silent",
                    #TODO: help="" (checkout silent mode before... )
                ),
                id="dialog_add_channel"
            )
            box = UI.DialogBox(
                content,
                id="dlg_add_chan",
                title='Add channel'
            )
            ui.append("dialog_container", box)

        if self._open_dialog == 'dlg_add_channel_link':
            content = UI.SimpleForm(
                UI.HContainer(
                    UI.SelectInput(*list(
                        UI.SelectOption(text=c, value=c)
                        for c in channel_names,
                    ), name="chan_src"),
                    UI.Label(text=" => "),
                    UI.SelectInput(*list(
                        UI.SelectOption(text=c, value=c)
                        for c in channel_names,
                    ), name="chan_dest"),
                ),
                id="dialog_add_channel_link"
            )
            box = UI.DialogBox(
                content,
                id="dlg_add_chan_lnk",
                title='Add channel link'
            )
            ui.append("dialog_container", box)

        self._open_dialog = None
        return ui

    @event('button/click')
    def on_click(self, event, params, vars=None):
        cfg = self._config.config
        if params[0].startswith("dlg_"):
            self._open_dialog = params[0]

        if params[0] == "deleteChan":
            self._tab = 1
            del_chan = params[1]
            for chan in cfg.channels[:]:
                if del_chan == chan.name:
                    cfg.channels.remove(chan)
                    break
            for lnk in cfg.channel_links[:]:
                if del_chan in (lnk.source, lnk.destination):
                    cfg.channel_links.remove(lnk)
            self._config.save()

        if params[0] == 'deleteChanLnk':
            self._tab = 1
            src, dest = params[1:3]
            for lnk in cfg.channel_links[:]:
                if src == lnk.source and dest == lnk.destination:
                    cfg.channel_links.remove(lnk)
            self._config.save()

    @event('form/submit')
    def on_submit(self, event, params, vars=None):
        cfg = self._config.config

        # server settings
        if params[0] == 'form_server':
            self._tab = 0
            if vars.getvalue('action', '') == 'OK':
                cfg.set(
                    "welcometext",
                    vars.getvalue("welcometext", "")
                )
                cfg.set(
                    "password",
                    vars.getvalue("password", "")
                )
                try:
                    cfg.set(
                        "max_bandwidth",
                        int(vars.getvalue("max_bandwidth", ""))
                    )
                except ValueError:
                    self.put_message(
                        'warn', '"Max. bandwidth" must be an integer value.'
                    )
                try:
                    cfg.set(
                        "max_users",
                        int(vars.getvalue("max_users", ""))
                    )
                except ValueError:
                    self.put_message(
                        'warn', '"Max. users" must be an integer value.'
                    )
                self._config.save()

        # channel settings
        if params[0] == 'form_def_chan':
            self._tab = 1
            if vars.getvalue('action', '') == 'OK':
                cfg.set("default_channel", vars.getvalue("default_channel"))
                self._config.save()

        if vars.getvalue('action', '') == 'Cancel':
            self._config.load()

    @event('dialog/submit')
    def on_submit_dlg(self, event, params, vars=None):
        if vars.getvalue('action', '') != 'OK':
            return

        cfg = self._config.config
        if params[0] == 'dlg_add_chan':

            chan_name = vars.getvalue('chan_name')
            if not chan_name:
                self.put_message('warn', 'Channel name cannot be empty.')
                return

            if chan_name.lower() in (n.name.lower() for n in cfg.channels):
                self.put_message('warn', 'Channel name already exists.')
                return

            new_chan = backend.pylibconfig2.ConfGroup()
            setattr(new_chan, "name", chan_name)
            setattr(new_chan, "description", vars.getvalue('chan_descr'))
            setattr(new_chan, "parent", vars.getvalue('chan_parent'))
            if int(vars.getvalue('chan_silent')):
                setattr(new_chan, "silent", True),
            cfg.channels.append(new_chan)
            self._config.save()
            self._tab = 1

        if params[0] == 'dlg_add_chan_lnk':
            chan_src = vars.getvalue('chan_src')
            chan_dest = vars.getvalue('chan_dest')
            if chan_src == chan_dest:
                self.put_message(
                    'warn', "Nope. I won't make a link with src == dest."
                )
                return
            if (chan_src, chan_dest) in (
                    (lnk.source, lnk.destination) for lnk in cfg.channel_links
            ):
                self.put_message(
                    'warn', "Nope. This channel link exists."
                )
                return
            new_lnk = backend.pylibconfig2.ConfGroup()
            setattr(new_lnk, "source", chan_src)
            setattr(new_lnk, "destination", chan_dest)
            cfg.channel_links.append(new_lnk)
            self._config.save()
            self._tab = 1

# TODO: check input for all submits
# TODO: Warning message if no cert assigned
# TODO: Move website content from here to layout file
########NEW FILE########
__FILENAME__ = main
import nginx

from genesis.api import *
from genesis.ui import *
from genesis.com import Plugin, Interface, implements
from genesis import apis
from genesis.utils import shell

import hashlib
import os
import random
import shutil


class Wallabag(Plugin):
    implements(apis.webapps.IWebapp)

    addtoblock = [
        nginx.Location('~ /(db)',
            nginx.Key('deny', 'all'),
            nginx.Key('return', '404')
            ),
        nginx.Location('= /favicon.ico',
            nginx.Key('log_not_found', 'off'),
            nginx.Key('access_log', 'off')
            ),
        nginx.Location('= /robots.txt',
            nginx.Key('allow', 'all'),
            nginx.Key('log_not_found', 'off'),
            nginx.Key('access_log', 'off')
            ),
        nginx.Location('/',
            nginx.Key('try_files', '$uri $uri/ /index.php?$args')
            ),
        nginx.Location('~ \.php$',
            nginx.Key('fastcgi_pass', 'unix:/run/php-fpm/php-fpm.sock'),
            nginx.Key('fastcgi_index', 'index.php'),
            nginx.Key('include', 'fastcgi.conf')
            ),
        nginx.Location('~* \.(js|css|png|jpg|jpeg|gif|ico)$',
            nginx.Key('expires', 'max'),
            nginx.Key('log_not_found', 'off')
            )
        ]

    def pre_install(self, name, vars):
        dbname = vars.getvalue('wb-dbname', '')
        dbpasswd = vars.getvalue('wb-dbpasswd', '')
        if dbname and dbpasswd:
            apis.databases(self.app).get_interface('MariaDB').validate(
                dbname, dbname, dbpasswd)
        elif dbname:
            raise Exception('You must enter a database password if you specify a database name!')
        elif dbpasswd:
            raise Exception('You must enter a database name if you specify a database password!')

    def post_install(self, name, path, vars):
        # Get the database object, and determine proper values
        phpctl = apis.langassist(self.app).get_interface('PHP')
        dbase = apis.databases(self.app).get_interface('MariaDB')
        conn = apis.databases(self.app).get_dbconn('MariaDB')
        if vars.getvalue('wb-dbname', '') == '':
            dbname = name
        else:
            dbname = vars.getvalue('wb-dbname')
        secret_key = hashlib.sha1(str(random.random())).hexdigest()
        if vars.getvalue('wb-dbpasswd', '') == '':
            passwd = secret_key[0:8]
        else:
            passwd = vars.getvalue('wb-dbpasswd')

        # Write a standard Wallabag config file
        shutil.copy(os.path.join(path, 'inc/poche/config.inc.php.new'),
            os.path.join(path, 'inc/poche/config.inc.php'))
        ic = open(os.path.join(path, 'inc/poche/config.inc.php'), 'r').readlines()
        f = open(os.path.join(path, 'inc/poche/config.inc.php'), 'w')
        oc = []
        for l in ic:
            if 'define (\'SALT\'' in l:
                l = 'define (\'SALT\', \''+secret_key+'\');\n'
                oc.append(l)
            elif 'define (\'STORAGE\'' in l:
                l = 'define (\'STORAGE\', \'mysql\');\n'
                oc.append(l)
            elif 'define (\'STORAGE_DB\'' in l:
                l = 'define (\'STORAGE_DB\', \''+dbname+'\');\n'
                oc.append(l)
            elif 'define (\'STORAGE_USER\'' in l:
                l = 'define (\'STORAGE_USER\', \''+dbname+'\');\n'
                oc.append(l)
            elif 'define (\'STORAGE_PASSWORD\'' in l:
                l = 'define (\'STORAGE_PASSWORD\', \''+passwd+'\');\n'
                oc.append(l)
            else:
                oc.append(l)
        f.writelines(oc)
        f.close()

        # Make sure that the correct PHP settings are enabled
        phpctl.enable_mod('mysql', 'pdo_mysql', 'zip', 
            'tidy', 'xcache', 'openssl')

        # Set up Composer and install the proper modules
        phpctl.composer_install(path)

        # Set up the database then delete the install folder
        dbase.add(dbname, conn)
        dbase.usermod(dbname, 'add', passwd, conn)
        dbase.chperm(dbname, dbname, 'grant', conn)
        dbase.execute(dbname, 
            open(os.path.join(path, 'install/mysql.sql')).read(), conn)
        shutil.rmtree(os.path.join(path, 'install'))

        # Finally, make sure that permissions are set so that Poche
        # can make adjustments and save plugins when need be.
        shell('chmod -R 755 '+os.path.join(path, 'assets/')+' '
            +os.path.join(path, 'cache/')+' '
            +os.path.join(path, 'db/'))
        shell('chown -R http:http '+path)

    def pre_remove(self, name, path):
        f = open(os.path.join(path, 'inc/poche/config.inc.php'), 'r')
        for line in f.readlines():
            if 'STORAGE_DB' in line:
                data = line.split('\'')[1::2]
                dbname = data[1]
                break
        f.close()
        dbase = apis.databases(self.app).get_interface('MariaDB')
        conn = apis.databases(self.app).get_dbconn('MariaDB')
        dbase.remove(dbname, conn)
        dbase.usermod(dbname, 'del', '', conn)

    def post_remove(self, name):
        pass

    def ssl_enable(self, path, cfile, kfile):
        pass

    def ssl_disable(self, path):
        pass

########NEW FILE########
__FILENAME__ = main
from genesis.api import *
from genesis.ui import *
from genesis.com import Plugin, Interface, implements
from genesis import apis
from genesis.utils import shell

import hashlib
import nginx
import os
import random
import urllib


class WordPress(Plugin):
	implements(apis.webapps.IWebapp)

	addtoblock = [
		nginx.Location('= /favicon.ico',
			nginx.Key('log_not_found', 'off'),
			nginx.Key('access_log', 'off')
			),
		nginx.Location('= /robots.txt',
			nginx.Key('allow', 'all'),
			nginx.Key('log_not_found', 'off'),
			nginx.Key('access_log', 'off')
			),
		nginx.Location('/',
			nginx.Key('try_files', '$uri $uri/ /index.php?$args')
			),
		nginx.Location('~ \.php$',
			nginx.Key('fastcgi_pass', 'unix:/run/php-fpm/php-fpm.sock'),
			nginx.Key('fastcgi_index', 'index.php'),
			nginx.Key('include', 'fastcgi.conf')
			),
		nginx.Location('~* \.(js|css|png|jpg|jpeg|gif|ico)$',
			nginx.Key('expires', 'max'),
			nginx.Key('log_not_found', 'off')
			)
		]

	def pre_install(self, name, vars):
		dbname = vars.getvalue('wp-dbname', '')
		dbpasswd = vars.getvalue('wp-dbpasswd', '')
		if dbname and dbpasswd:
			apis.databases(self.app).get_interface('MariaDB').validate(
				dbname, dbname, dbpasswd)
		elif dbname:
			raise Exception('You must enter a database password if you specify a database name!')
		elif dbpasswd:
			raise Exception('You must enter a database name if you specify a database password!')

	def post_install(self, name, path, vars):
		# Get the database object, and determine proper values
		phpctl = apis.langassist(self.app).get_interface('PHP')
		dbase = apis.databases(self.app).get_interface('MariaDB')
		conn = apis.databases(self.app).get_dbconn('MariaDB')
		if vars.getvalue('wp-dbname', '') == '':
			dbname = name
		else:
			dbname = vars.getvalue('wp-dbname')
		secret_key = hashlib.sha1(str(random.random())).hexdigest()
		if vars.getvalue('wp-dbpasswd', '') == '':
			passwd = secret_key[0:8]
		else:
			passwd = vars.getvalue('wp-dbpasswd')

		# Request a database and user to interact with it
		dbase.add(dbname, conn)
		dbase.usermod(dbname, 'add', passwd, conn)
		dbase.chperm(dbname, dbname, 'grant', conn)

		# Use the WordPress key generators as first option
		# If connection fails, use the secret_key as fallback
		try:
			keysection = urllib.urlopen('https://api.wordpress.org/secret-key/1.1/salt/').read()
		except:
			keysection = ''
		if not 'define(\'AUTH_KEY' in keysection:
			keysection = (
				'define(\'AUTH_KEY\', \''+secret_key+'\');\n'
				'define(\'SECURE_AUTH_KEY\', \''+secret_key+'\');\n'
				'define(\'LOGGED_IN_KEY\', \''+secret_key+'\');\n'
				'define(\'NONCE_KEY\', \''+secret_key+'\');\n'
				)

		# Write a standard WordPress config file
		f = open(os.path.join(path, 'wp-config.php'), 'w')
		f.write('<?php\n'
				'define(\'DB_NAME\', \''+dbname+'\');\n'
				'define(\'DB_USER\', \''+dbname+'\');\n'
				'define(\'DB_PASSWORD\', \''+passwd+'\');\n'
				'define(\'DB_HOST\', \'localhost\');\n'
				'define(\'DB_CHARSET\', \'utf8\');\n'
				'define(\'SECRET_KEY\', \''+secret_key+'\');\n'
				'\n'
				'define(\'WP_CACHE\', true);\n'
				'define(\'FORCE_SSL_ADMIN\', false);\n'
				'\n'
				+keysection+
				'\n'
				'$table_prefix = \'wp_\';\n'
				'\n'
				'/** Absolute path to the WordPress directory. */\n'
				'if ( !defined(\'ABSPATH\') )\n'
				'	define(\'ABSPATH\', dirname(__FILE__) . \'/\');\n'
				'\n'
				'/** Sets up WordPress vars and included files. */\n'
				'require_once(ABSPATH . \'wp-settings.php\');\n'
			)
		f.close()

		# Make sure that the correct PHP settings are enabled
		phpctl.enable_mod('mysql', 'xcache')

		# Finally, make sure that permissions are set so that Wordpress
		# can make adjustments and save plugins when need be.
		shell('chown -R http:http '+path)

	def pre_remove(self, name, path):
		f = open(os.path.join(path, 'wp-config.php'), 'r')
		for line in f.readlines():
			if 'DB_NAME' in line:
				data = line.split('\'')[1::2]
				dbname = data[1]
				break
		f.close()
		dbase = apis.databases(self.app).get_interface('MariaDB')
		conn = apis.databases(self.app).get_dbconn('MariaDB')
		dbase.remove(dbname, conn)
		dbase.usermod(dbname, 'del', '', conn)

	def post_remove(self, name):
		pass

	def ssl_enable(self, path, cfile, kfile):
		ic = open(os.path.join(path, 'wp-config.php'), 'r').readlines()
		f = open(os.path.join(path, 'wp-config.php'), 'w')
		oc = []
		found = False
		for l in ic:
			if 'define(\'FORCE_SSL_ADMIN\'' in l:
				l = 'define(\'FORCE_SSL_ADMIN\', false);\n'
				oc.append(l)
				found = True
			else:
				oc.append(l)
		if found == False:
			oc.append('define(\'FORCE_SSL_ADMIN\', true);\n')
		f.writelines(oc)
		f.close()

	def ssl_disable(self, path):
		ic = open(os.path.join(path, 'wp-config.php'), 'r').readlines()
		f = open(os.path.join(path, 'wp-config.php'), 'w')
		oc = []
		found = False
		for l in ic:
			if 'define(\'FORCE_SSL_ADMIN\'' in l:
				l = 'define(\'FORCE_SSL_ADMIN\', false);\n'
				oc.append(l)
				found = True
			else:
				oc.append(l)
		if found == False:
			oc.append('define(\'FORCE_SSL_ADMIN\', false);\n')
		f.writelines(oc)
		f.close()

########NEW FILE########
__FILENAME__ = backend
import os
import re
import urllib

from genesis.api import *
from genesis.com import *
from genesis import apis
from genesis.plugins.core.api import ISSLPlugin
from genesis.utils import shell_cs


class XMPPConfig(Plugin):
    implements(IConfigurable)
    name = 'XMPP'
    id = 'xmpp'
    iconfont = 'gen-bubbles'

    def load(self):
        s = ConfManager.get().load('xmpp', '/etc/prosody/prosody.cfg.lua')
        self.config = self.loads(s)

    def save(self):
        self.mgr = self.app.get_backend(apis.services.IServiceManager)
        wasrunning = False
        s = self.dumps(self.config)
        if self.mgr.get_status('prosody') == 'running':
            wasrunning = True
            self.mgr.stop('prosody')
        ConfManager.get().save('xmpp', self.configFile, s)
        ConfManager.get().commit('xmpp')
        if wasrunning:
            self.mgr.start('prosody')

    def get(self, key):
        return self.config[key]

    def set(self, key, value):
        self.config[key] = value

    def items(self):
        return self.config.items()

    def __init__(self):
        #self.configFile = self.app.get_config(self).cfg_file
        self.configFile = '/etc/prosody/prosody.cfg.lua'
        self.config = {}

    def list_files(self):
        return [self.configFile]

    def domains(self):
        d = []
        for x in self.config:
            if x.startswith('_VirtualHost'):
                d.append(x.split('_VirtualHost_')[1])
        return d

    def loads(self, data):
        # Decode the Prosody lua configuration to a manageable Python object
        conf = {}
        active = []
        for line in data.split('\n'):
            # Get rid of comments
            if re.match('.*--.*', line):
                line = line.split('--')[0]
                if not line.split():
                    continue
            # Close any objects if necessary
            if line and active and active[-1].startswith('_') \
            and not re.match('^\t', line):
                active.pop()
            # Arrays and linked lists
            if re.match('\s*(.+)\s*=\s*{', line):
                val = re.match('\s*(.+)\s*=\s*{', line).group(1).split()[0]
                if active:
                    conf[active[-1]][val] = {}
                else:
                    conf[val] = {}
                active.append(val)
            # Base-level variable or keyed list item
            elif re.match('.*\s*=\s*.*', line):
                name, val = re.match('.*(?:^|^\s*|{\s*)(\S+)\s=\s(.+)', line).group(1,2)
                name, val = name.split()[0], val.split()[0].rstrip(';')
                val = re.sub(r'"', '', val)
                if val == 'true':
                    val = True
                elif val == 'false':
                    val = False
                if active and active[-1].startswith('_'):
                    conf[active[-1]][name] = val
                elif active and len(active) >= 2 and active[-2].startswith('_'):
                    conf[active[-2]][active[-1]][name] = val
                elif active:
                    conf[active[-1]][name] = val
                else:
                    conf[name] = val
            # Objects (VirtualHosts)
            elif re.match('\s*(.+) "(.+)"$', line):
                name, val = re.match('\s*(.+) "(.+)"', line).group(1,2)
                name, val = name.split()[0], val.split()[0]
                conf['_'+name+'_'+val] = {}
                active.append('_'+name+'_'+val)
            # Non-keyed list item
            elif re.match('.*\s*"(.+)";', line):
                val = re.match('.*\s*"(.+)";', line).group(1).split()[0]
                conf[active[-1]][len(conf[active[-1]])] = val
            # Match the end of an array
            if re.match('.*}', line):
                closenum = len(re.findall('}', line))
                while closenum > 0:
                    active.pop()
                    closenum = closenum - 1
        return conf

    def dumps(self, data):
        # Dumps the data back to Lua-readable format and returns as string
        vhosts = ''
        allow_registration = ''
        c2s_require_encryption = ''
        s2s_secure_auth = ''
        for x in data:
            if x.startswith('_VirtualHost'):
                vhosts += 'VirtualHost "%s"\n'%x.split('_')[2]
                for y in data[x]:
                    if type(data[x][y]) == dict:
                        vhosts += '\t%s = {\n' % y
                        for z in data[x][y]:
                            vhosts += '\t\t%s = "%s";\n' % (z, data[x][y][z])
                        vhosts += '\t}\n'
                    elif type(data[x][y]) == bool:
                        vhosts += '\t%s = %s\n' % (y, 'true' if data[x][y] else 'false')
                    else:
                        vhosts += '\t%s = "%s";\n' % (y, data[x][y])
                vhosts += '\n'
            elif x == 'allow_registration':
                allow_registration = 'true' if data[x] else 'false'
            elif x == 'c2s_require_encryption':
                c2s_require_encryption = 'true' if data[x] else 'false'
            elif x == 's2s_secure_auth':
                s2s_secure_auth = 'true' if data[x] else 'false'
        cfgfile = (
            '-- Prosody Example Configuration File\n'
            '--\n'
            '-- Information on configuring Prosody can be found on our\n'
            '-- website at http://prosody.im/doc/configure\n'
            '--\n'
            '-- Tip: You can check that the syntax of this file is correct\n'
            '-- when you have finished by running: luac -p prosody.cfg.lua\n'
            '-- If there are any errors, it will let you know what and where\n'
            '-- they are, otherwise it will keep quiet.\n'
            '--\n'
            '-- The only thing left to do is rename this file to remove the .dist ending, and fill in the\n'
            '-- blanks. Good luck, and happy Jabbering!\n'
            '\n'
            'daemonize = true\n'
            'pidfile = "/run/prosody/prosody.pid"\n'
            '\n'
            '---------- Server-wide settings ----------\n'
            '-- Settings in this section apply to the whole server and are the default settings\n'
            '-- for any virtual hosts\n'
            '\n'
            '-- This is a (by default, empty) list of accounts that are admins\n'
            '-- for the server. Note that you must create the accounts separately\n'
            '-- (see http://prosody.im/doc/creating_accounts for info)\n'
            '-- Example: admins = { "user1@example.com", "user2@example.net" }\n'
            'admins = { }\n'
            '\n'
            '-- Enable use of libevent for better performance under high load\n'
            '-- For more information see: http://prosody.im/doc/libevent\n'
            '--use_libevent = true;\n'
            '\n'
            '-- This is the list of modules Prosody will load on startup.\n'
            '-- It looks for mod_modulename.lua in the plugins folder, so make sure that exists too.\n'
            '-- Documentation on modules can be found at: http://prosody.im/doc/modules\n'
            'modules_enabled = {\n'
            '\n'
            '\t-- Generally required\n'
            '\t\t"roster"; -- Allow users to have a roster. Recommended ;)\n'
            '\t\t"saslauth"; -- Authentication for clients and servers. Recommended if you want to log in.\n'
            '\t\t"tls"; -- Add support for secure TLS on c2s/s2s connections\n'
            '\t\t"dialback"; -- s2s dialback support\n'
            '\t\t"disco"; -- Service discovery\n'
            '\n'
            '\t-- Not essential, but recommended\n'
            '\t\t"private"; -- Private XML storage (for room bookmarks, etc.)\n'
            '\t\t"vcard"; -- Allow users to set vCards\n'
            '\n'
            '\t-- These are commented by default as they have a performance impact\n'
            '\t\t--"privacy"; -- Support privacy lists\n'
            '\t\t--"compression"; -- Stream compression\n'
            '\n'
            '\t-- Nice to have\n'
            '\t\t"version"; -- Replies to server version requests\n'
            '\t\t"uptime"; -- Report how long server has been running\n'
            '\t\t"time"; -- Let others know the time here on this server\n'
            '\t\t"ping"; -- Replies to XMPP pings with pongs\n'
            '\t\t"pep"; -- Enables users to publish their mood, activity, playing music and more\n'
            '\t\t"register"; -- Allow users to register on this server using a client and change passwords\n'
            '\n'
            '\t-- Admin interfaces\n'
            '\t\t"admin_adhoc"; -- Allows administration via an XMPP client that supports ad-hoc commands\n'
            '\t\t--"admin_telnet"; -- Opens telnet console interface on localhost port 5582\n'
            '\n'
            '\t-- HTTP modules\n'
            '\t\t--"bosh"; -- Enable BOSH clients, aka "Jabber over HTTP"\n'
            '\t\t--"http_files"; -- Serve static files from a directory over HTTP\n'
            '\n'
            '\t-- Other specific functionality\n'
            '\t\t"posix"; -- POSIX functionality, sends server to background, enables syslog, etc.\n'
            '\t\t--"groups"; -- Shared roster support\n'
            '\t\t--"announce"; -- Send announcement to all online users\n'
            '\t\t--"welcome"; -- Welcome users who register accounts\n'
            '\t\t--"watchregistrations"; -- Alert admins of registrations\n'
            '\t\t--"motd"; -- Send a message to users when they log in\n'
            '\t\t--"legacyauth"; -- Legacy authentication. Only used by some old clients and bots.\n'
            '};\n'          
            '\n'
            '-- These modules are auto-loaded, but should you want\n'
            '-- to disable them then uncomment them here:\n'
            'modules_disabled = {\n'
            '\t-- "offline"; -- Store offline messages\n'
            '\t-- "c2s"; -- Handle client connections\n'
            '\t-- "s2s"; -- Handle server-to-server connections\n'
            '};\n'
            '\n'
            '-- Disable account creation by default, for security\n'
            '-- For more information see http://prosody.im/doc/creating_accounts\n'
            'allow_registration = '+allow_registration+';\n'
            '\n'
            '-- These are the SSL/TLS-related settings. If you don\'t want\n'
            '-- to use SSL/TLS, you may comment or remove this\n'
            'ssl = {\n'
            '\tkey = "/etc/prosody/certs/localhost.key";\n'
            '\tcertificate = "/etc/prosody/certs/localhost.crt";\n'
            '}\n'
            '\n'
            '-- Force clients to use encrypted connections? This option will\n'
            '-- prevent clients from authenticating unless they are using encryption.\n'
            '\n'
            'c2s_require_encryption = false\n'
            '\n'
            '-- Force certificate authentication for server-to-server connections?\n'
            '-- This provides ideal security, but requires servers you communicate\n'
            '-- with to support encryption AND present valid, trusted certificates.\n'
            '-- NOTE: Your version of LuaSec must support certificate verification!\n'
            '-- For more information see http://prosody.im/doc/s2s#security\n'
            '\n'
            's2s_secure_auth = false\n'
            '\n'
            '-- Many servers don\'t support encryption or have invalid or self-signed\n'
            '-- certificates. You can list domains here that will not be required to\n'
            '-- authenticate using certificates. They will be authenticated using DNS.\n'
            '\n'
            '--s2s_insecure_domains = { "gmail.com" }\n'
            '\n'
            '-- Even if you leave s2s_secure_auth disabled, you can still require valid\n'
            '-- certificates for some domains by specifying a list here.\n'
            '\n'
            '--s2s_secure_domains = { "jabber.org" }\n'
            '\n'
            '-- Select the authentication backend to use. The \'internal\' providers\n'
            '-- use Prosody\'s configured data storage to store the authentication data.\n'
            '-- To allow Prosody to offer secure authentication mechanisms to clients, the\n'
            '-- default provider stores passwords in plaintext. If you do not trust your\n'
            '-- server please see http://prosody.im/doc/modules/mod_auth_internal_hashed\n'
            '-- for information about using the hashed backend.\n'
            '\n'
            'authentication = "internal_plain"\n'
            '\n'
            '-- Select the storage backend to use. By default Prosody uses flat files\n'
            '-- in its configured data directory, but it also supports more backends\n'
            '-- through modules. An "sql" backend is included by default, but requires\n'
            '-- additional dependencies. See http://prosody.im/doc/storage for more info.\n'
            '\n'
            '--storage = "sql" -- Default is "internal"\n'
            '\n'
            '-- For the "sql" backend, you can uncomment *one* of the below to configure:\n'
            '--sql = { driver = "SQLite3", database = "prosody.sqlite" } -- Default. \'database\' is the filename.\n'
            '--sql = { driver = "MySQL", database = "prosody", username = "prosody", password = "secret", host = "localhost" }\n'
            '--sql = { driver = "PostgreSQL", database = "prosody", username = "prosody", password = "secret", host = "localhost" }\n'
            '\n'
            '-- Logging configuration\n'
            '-- For advanced logging see http://prosody.im/doc/logging\n'
            'log = {\n'
            '\t-- info = "prosody.log"; -- Change \'info\' to \'debug\' for verbose logging\n'
            '\t-- error = "prosody.err";\n'
            '\t"*syslog"; -- Uncomment this for logging to syslog\n'
            '\t-- "*console"; -- Log to the console, useful for debugging with daemonize=false\n'
            '}\n'
            '\n'
            '----------- Virtual hosts -----------\n'
            '-- You need to add a VirtualHost entry for each domain you wish Prosody to serve.\n'
            '-- Settings under each VirtualHost entry apply *only* to that host.\n'
            '\n'+vhosts+
            '------ Components ------\n'
            '-- You can specify components to add hosts that provide special services,\n'
            '-- like multi-user conferences, and transports.\n'
            '-- For more information on components, see http://prosody.im/doc/components\n'
            '\n'
            '---Set up a MUC (multi-user chat) room server on conference.example.com:\n'
            '--Component "conference.example.com" "muc"\n'
            '\n'
            '-- Set up a SOCKS5 bytestream proxy for server-proxied file transfers:\n'
            '--Component "proxy.example.com" "proxy65"\n'
            '\n'
            '---Set up an external component (default component port is 5347)\n'
            '--\n'
            '-- External components allow adding various services, such as gateways/\n'
            '-- transports to other networks like ICQ, MSN and Yahoo. For more info\n'
            '-- see: http://prosody.im/doc/components#adding_an_external_component\n'
            '--\n'
            '--Component "gateway.example.com"\n'
            '--  component_secret = "password"\n'
        )
        return cfgfile


class XMPPUserControl:
    def list_users(self):
        users = []
        if not os.path.exists('/var/lib/prosody'):
            os.mkdir('/var/lib/prosody')
        for x in os.listdir('/var/lib/prosody'):
            for y in os.listdir(os.path.join('/var/lib/prosody', x, 'accounts')):
                users.append((y.split('.dat')[0], urllib.unquote(x)))
        return sorted(users, key=lambda x: x[0])

    def list_domains(self):
        return [urllib.unquote(x) for x in os.listdir('/var/lib/prosody')]

    def add_user(self, name, dom, passwd):
        x = shell_cs('echo -e "%s\n%s\n" | prosodyctl adduser %s@%s' % (passwd,passwd,name,dom))
        if x[0] != 0:
            raise Exception('XMPP Add user failed: %s' % x[1])

    def del_user(self, name, dom):
        x = shell_cs('prosodyctl deluser %s@%s' % (name,dom))
        if x[0] != 0:
            raise Exception('XMPP Delete user failed: %s' % x[1])

    def chpasswd(self, name, dom, passwd):
        x = shell_cs('echo -e "%s\n%s\n" | prosodyctl passwd %s@%s' % (passwd,passwd,name,dom))
        if x[0] != 0:
            raise Exception('XMPP Password change failed: %s' % x[1])


class XMPPSSLPlugin(Plugin):
    implements(ISSLPlugin)
    text = 'XMPP Chat'
    iconfont = 'gen-bubbles'
    cert_type = 'cert-key'

    def enable_ssl(self, cert, key):
        config = XMPPConfig(self.app)
        config.load()
        config.config['ssl'] = {'certificate': cert, 'key': key}
        config.save()

    def disable_ssl(self):
        config = XMPPConfig(self.app)
        config.load()
        config.config['ssl'] = {}
        config.save()


#class GeneralConfig(ModuleConfig):
#    target=XMPPConfig
#    platform = ['debian', 'centos', 'arch', 'arkos', 'gentoo', 'mandriva']
#
#    labels = {
#        'cfg_file': 'Configuration file'
#    }
#
#    cfg_file = '/etc/prosody/prosody.cfg.lua'

########NEW FILE########
__FILENAME__ = main
import re

from genesis.ui import *
from genesis.api import *
from genesis import apis

import backend

class XMPPPlugin(apis.services.ServiceControlPlugin):
    text = 'Chat (XMPP)'
    iconfont = 'gen-bubbles'
    folder = 'servers'

    def on_session_start(self):
        self._chpasswd = None
        self._adduser = None
        self._config = backend.XMPPConfig(self.app)
        self._uc = backend.XMPPUserControl()
        self._config.load()

    def on_init(self):
        self._users = self._uc.list_users()
        self._domains = self._config.domains()

    def get_main_ui(self):
        ui = self.app.inflate('xmpp:main')

        t = ui.find('list')
        for u in self._users:
            t.append(UI.DTR(
                    UI.Iconfont(iconfont='gen-user'),
                    UI.Label(text=u[0]),
                    UI.Label(text=u[1]),
                    UI.HContainer(
                        UI.TipIcon(iconfont='gen-key', id='edit/'+str(self._users.index(u)), text='Change Password'),
                        UI.TipIcon(iconfont='gen-cancel-circle', id='del/'+str(self._users.index(u)), text='Delete', warning='Are you sure you want to delete XMPP account %s@%s?'%(u[0], u[1]))
                    ),
                ))

        t = ui.find('dlist')
        for x in self._domains:
            if not self._config.config['_VirtualHost_'+x].has_key('enabled'):
                self._config.config['_VirtualHost_'+x]['enabled'] = False
            t.append(UI.DTR(
                    UI.Iconfont(iconfont='gen-code'),
                    UI.Label(text=x),
                    UI.Label(text='Enabled' if self._config.config['_VirtualHost_'+x]['enabled'] else 'Disabled'),
                    UI.HContainer(
                        #UI.TipIcon(iconfont='gen-pencil', id='editdom/'+str(self._domains.index(x)), text='Edit Domain'),
                        UI.TipIcon(iconfont='gen-%s'%('link' if not self._config.config['_VirtualHost_'+x]['enabled'] else 'link-2'), 
                            id='togdom/'+str(self._domains.index(x)), text=('Disable' if self._config.config['_VirtualHost_'+x]['enabled'] else 'Enable')),
                        UI.TipIcon(iconfont='gen-cancel-circle', id='deldom/'+str(self._domains.index(x)), text='Delete Domain',
                            warning='Are you sure you want to delete XMPP domain %s?'%x),
                    ),
                ))

        ui.find('allow_registration').set('checked', True if self._config.config['allow_registration'] else False)
        ui.find('c2s_require_encryption').set('checked', True if self._config.config['c2s_require_encryption'] else False)
        ui.find('s2s_secure_auth').set('checked', True if self._config.config['s2s_secure_auth'] else False)

        if self._adduser:
            doms = [UI.SelectOption(text=x, value=x) for x in self._domains]
            ui.append('main',
                UI.DialogBox(
                    UI.FormLine(
                        UI.TextInput(name='acct', id='acct'),
                        text='Username'
                    ),
                    UI.FormLine(
                        UI.Select(*doms if doms else 'None', id='dom', name='dom'),
                        text='Domain'
                    ),
                    UI.FormLine(
                        UI.EditPassword(id='passwd', value='Click to add password'),
                        text='Password'
                    ),
                    id='dlgAddUser')
                )

        if self._adddom:
            ui.append('main',
                UI.InputBox(id='dlgAddDom', text='Enter domain name to add'))

        if self._chpasswd:
            ui.append('main',
                UI.DialogBox(
                    UI.FormLine(
                        UI.EditPassword(id='chpasswd', value='Click to change password'),
                        text='Password'
                    ),
                    id='dlgChpasswd')
                )

        return ui

    @event('button/click')
    def on_click(self, event, params, vars = None):
        if params[0] == 'add':
            self._adduser = True
        elif params[0] == 'adddom':
            self._adddom = True
        elif params[0] == 'edit':
            self._chpasswd = self._users[int(params[1])]
        elif params[0] == 'togdom':
            self._config.config['_VirtualHost_%s'%self._domains[int(params[1])]]['enabled'] = True \
            if self._config.config['_VirtualHost_%s'%self._domains[int(params[1])]]['enabled'] == False \
            else False
            self._config.save()
        elif params[0] == 'del':
            try:
                u = self._users[int(params[1])]
                self._uc.del_user(u[0], u[1])
                self.put_message('info', 'User deleted successfully')
            except Exception, e:
                self.app.log.error('XMPP user could not be deleted. Error: %s' % str(e))
                self.put_message('err', 'User could not be deleted')
        elif params[0] == 'deldom':
            candel = True
            for x in self._users:
                if x[1] == self._domains[int(params[1])]:
                    self.put_message('err', 'You still have user accounts attached to this domain. Remove them before deleting the domain!')
                    candel = False
            if candel:
                del self._config.config['_VirtualHost_%s'%self._domains[int(params[1])]]
                self.put_message('info', 'Domain deleted')
                self._config.save()

    @event('dialog/submit')
    @event('form/submit')
    def on_submit(self, event, params, vars=None):
        if params[0] == 'dlgAddUser':
            acct = vars.getvalue('acct', '')
            dom = vars.getvalue('dom', '')
            passwd = vars.getvalue('passwd', '')
            if vars.getvalue('action', '') == 'OK':
                m = re.match('([-0-9a-zA-Z.+_]+)', acct)
                if not acct or not m:
                    self.put_message('err', 'Must choose a valid username')
                elif (acct, dom) in self._users:
                    self.put_message('err', 'You already have a user with this name on this domain')
                elif not passwd:
                    self.put_message('err', 'Must choose a password')
                elif passwd != vars.getvalue('passwdb',''):
                    self.put_message('err', 'Passwords must match')
                else:
                    try:
                        self._uc.add_user(acct, dom, passwd)
                        self.put_message('info', 'User added successfully')
                    except Exception, e:
                        self.app.log.error('XMPP user %s@%s could not be added. Error: %s' % (acct,dom,str(e)))
                        self.put_message('err', 'User could not be added')
            self._adduser = None
        elif params[0] == 'dlgAddDom':
            v = vars.getvalue('value', '')
            if vars.getvalue('action', '') == 'OK':
                if not v or not re.match('([-0-9a-zA-Z.+_]+\.[a-zA-Z]{2,4})', v):
                    self.put_message('err', 'Must enter a valid domain to add')
                elif v in self._domains:
                    self.put_message('err', 'You have already added this domain!')
                else:
                    self._config.set('_VirtualHost_%s'%v, {'enabled': False})
                    self._config.save()
                    self.put_message('info', 'Domain added successfully')
            self._adddom = None
        elif params[0] == 'dlgChpasswd':
            passwd = vars.getvalue('chpasswd', '')
            if vars.getvalue('action', '') == 'OK':
                if not passwd:
                    self.put_message('err', 'Must choose a password')
                elif passwd != vars.getvalue('chpasswdb',''):
                    self.put_message('err', 'Passwords must match')
                else:
                    try:
                        self._uc.chpasswd(self._chpasswd[0], 
                            self._chpasswd[1], passwd)
                        self.put_message('info', 'Password changed successfully')
                    except Exception, e:
                        self.app.log.error('XMPP password for %s@%s could not be changed. Error: %s' % (self._chpasswd[0],self._chpasswd[1],str(e)))
                        self.put_message('err', 'Password could not be changed')
            self._chpasswd = None
        elif params[0] == 'frmOptions':
            if vars.getvalue('action', '') == 'OK':
                self._config.config['allow_registration'] = True if vars.getvalue('allow_registration', '') == '1' else False
                self._config.config['c2s_require_encryption'] = True if vars.getvalue('c2s_require_encryption', '') == '1' else False
                self._config.config['s2s_secure_auth'] = True if vars.getvalue('s2s_secure_auth', '') == '1' else False
                self._config.save()
                self.put_message('info', 'Settings saved')

########NEW FILE########
