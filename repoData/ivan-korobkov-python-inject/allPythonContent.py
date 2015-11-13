__FILENAME__ = inject
"""
Python dependency injection framework.

Usage:
- Create an optional configuration::
    def my_config(binder):
        binder.bind(Cache, RedisCache('localhost:1234'))
        binder.bind_to_provider(CurrentUser, get_current_user)
    
- Create a shared injector::
    inject.configure(my_config)

- Use `inject.instance`, `inject.attr` or `inject.param` to inject dependencies::
    class User(object):
        cache = inject.attr(Cache)

        @classmethod
        def load(cls, id):
            return cls.cache.load('user', id)

        def save(self):
            self.cache.save(self)

    def foo(bar):
        cache = inject.instance(Cache)
        cache.save('bar', bar)

    @inject.param('cache', Cache)
    def bar(foo, cache=None):
        cache.save('foo', foo)

Binding types:
- Instance bindings configured via `bind(cls, instance) which always return the same instance.
- Constructor bindings `bind_to_constructor(cls, callable)` which create a singleton
  on first access.
- Provider bindings `bind_to_provider(cls, callable)` which call the provider
  for each injection.
- Runtime bindings which automatically create class singletons.

Thread-safety:
After configuration the injector is thread-safe and can be safely reused by multiple threads.

Unit testing:
In tests use `inject.clear_and_configure(callable)` to create a new injector on setup,
and `inject.clear()` to clean-up on tear down.

Runtime bindings greatly reduce the required configuration by automatically creating singletons
on first access. For example, below only the Config class requires binding configuration, 
all other classes are runtime bindings::
    class Cache(object):
        config = inject.attr(Config)
        
        def __init__(self):
            self._redis = connect(self.config.redis_address)
    
    class Db(object):
        pass
    
    class UserRepo(object):
        cache = inject.attr(Cache)
        db = inject.attr(Db)
        
        def load(self, user_id):
            return cache.load('user', user_id) or db.load('user', user_id)
    
    class Config(object):
        def __init__(self, redis_address):
            self.redis_address = redis_address
    
    def my_config(binder):
        binder.bind(Config, load_config_file())
    
    inject.configure(my_config)

"""
__version__ = '3.1.1'
__author__ = 'Ivan Korobkov <ivan.korobkov@gmail.com>'
__license__ = 'Apache License 2.0'
__url__ = 'https://github.com/ivan-korobkov/python-inject'

import logging
import threading
from functools import wraps

logger = logging.getLogger('inject')

_INJECTOR = None                    # Shared injector instance.
_INJECTOR_LOCK = threading.RLock()  # Guards injector initialization. 
_BINDING_LOCK = threading.RLock()   # Guards runtime bindings.


def configure(config=None):
    """Create an injector with a callable config or raise an exception when already configured."""
    global _INJECTOR

    with _INJECTOR_LOCK:
        if _INJECTOR:
            raise InjectorException('Injector is already configured')

        _INJECTOR = Injector(config)
        logger.debug('Created and configured an injector, config=%s', config)
        return _INJECTOR


def clear_and_configure(config=None):
    """Clear an existing injector and create another one with a callable config."""
    with _INJECTOR_LOCK:
        clear()
        return configure(config)


def clear():
    """Clear an existing injector if present."""
    global _INJECTOR

    with _INJECTOR_LOCK:
        if _INJECTOR is None:
            return

        _INJECTOR = None
        logger.debug('Cleared an injector')


def instance(cls):
    """Inject an instance of a class."""
    return get_injector_or_die().get_instance(cls)


def attr(cls):
    """Return a attribute injection (descriptor)."""
    return _AttributeInjection(cls)


def param(name, cls=None):
    """Return a parameter injection decorator"""
    return _ParameterInjection(name, cls)


def get_injector():
    """Return the current injector or None."""
    return _INJECTOR


def get_injector_or_die():
    """Return the current injector or raise an InjectorException."""
    injector = _INJECTOR
    if not injector:
        raise InjectorException('No injector is configured')

    return injector


class Binder(object):
    def __init__(self):
        self._bindings = {}

    def install(self, config):
        """Install another callable configuration."""
        config(self)
        return self

    def bind(self, cls, instance):
        """Bind a class to an instance."""
        self._check_class(cls)
        self._bindings[cls] = lambda: instance
        logger.debug('Bound %s to an instance %s', cls, instance)
        return self

    def bind_to_constructor(self, cls, constructor):
        """Bind a class to a callable singleton constructor."""
        self._check_class(cls)
        if constructor is None:
            raise InjectorException('Constructor cannot be None, key=%s' % cls)

        self._bindings[cls] = _ConstructorBinding(constructor)
        logger.debug('Bound %s to a constructor %s', cls, constructor)
        return self

    def bind_to_provider(self, cls, provider):
        """Bind a class to a callable instance provider executed for each injection."""
        self._check_class(cls)
        if provider is None:
            raise InjectorException('Provider cannot be None, key=%s' % cls)

        self._bindings[cls] = provider
        logger.debug('Bound %s to a provider %s', cls, provider)
        return self

    def _check_class(self, cls):
        if cls is None:
            raise InjectorException('Binding key cannot be None')

        if cls in self._bindings:
            raise InjectorException('Duplicate binding, key=%s' % cls)


class Injector(object):
    def __init__(self, config=None):
        if config:
            binder = Binder()
            config(binder)
            self._bindings = dict(binder._bindings)
        else:
            self._bindings = {}

    def get_instance(self, cls):
        """Return an instance for a class."""
        binding = self._bindings.get(cls)
        if binding:
            return binding()

        # Try to create a runtime binding.
        with _BINDING_LOCK:
            binding = self._bindings.get(cls)
            if binding:
                return binding()

            if not callable(cls):
                raise InjectorException(
                    'Cannot create a runtime binding, the key is not callable, key=%s' % cls)

            instance = cls()
            self._bindings[cls] = lambda: instance

            logger.debug('Created a runtime binding for key=%s, instance=%s', cls, instance)
            return instance


class InjectorException(Exception):
    pass


class _ConstructorBinding(object):
    def __init__(self, constructor):
        self._constructor = constructor
        self._created = False
        self._instance = None

    def __call__(self):
        if self._created:
            return self._instance

        with _BINDING_LOCK:
            if self._created:
                return self._instance

            self._created = True
            self._instance = self._constructor()

        return self._instance


class _AttributeInjection(object):
    def __init__(self, cls):
        self._cls = cls

    def __get__(self, obj, owner):
        return instance(self._cls)


class _ParameterInjection(object):
    __slots__ = ('_name', '_cls')

    def __init__(self, name, cls=None):
        self._name = name
        self._cls = cls

    def __call__(self, func):
        @wraps(func)
        def injection_wrapper(*args, **kwargs):
            if not self._name in kwargs:
                kwargs[self._name] = instance(self._cls or self._name)
            return func(*args, **kwargs)
        return injection_wrapper

########NEW FILE########
__FILENAME__ = test_inject
from random import random
from unittest import TestCase

import inject
from inject import Binder, InjectorException, Injector


class TestBinder(TestCase):
    def test_bind(self):
        binder = Binder()
        binder.bind(int, 123)

        assert int in binder._bindings

    def test_bind__class_required(self):
        binder = Binder()

        self.assertRaisesRegexp(InjectorException, 'Binding key cannot be None',
                                binder.bind, None, None)

    def test_bind__duplicate_binding(self):
        binder = Binder()
        binder.bind(int, 123)

        self.assertRaisesRegexp(InjectorException, "Duplicate binding", 
                                binder.bind, int, 456)

    def test_bind_provider(self):
        provider = lambda: 123
        binder = Binder()
        binder.bind_to_provider(int, provider)

        assert binder._bindings[int] is provider

    def test_bind_provider__provider_required(self):
        binder = Binder()
        self.assertRaisesRegexp(InjectorException, "Provider cannot be None",
                                binder.bind_to_provider, int, None)

    def test_bind_constructor(self):
        constructor = lambda: 123
        binder = Binder()
        binder.bind_to_constructor(int, constructor)

        assert binder._bindings[int]._constructor is constructor

    def test_bind_constructor__constructor_required(self):
        binder = Binder()
        self.assertRaisesRegexp(InjectorException, "Constructor cannot be None",
                                binder.bind_to_constructor, int, None)


class TestInjector(TestCase):
    def test_instance_binding__should_use_the_same_instance(self):
        injector = Injector(lambda binder: binder.bind(int, 123))
        instance = injector.get_instance(int)
        assert instance == 123

    def test_constructor_binding__should_construct_singleton(self):
        injector = Injector(lambda binder: binder.bind_to_constructor(int, random))
        instance0 = injector.get_instance(int)
        instance1 = injector.get_instance(int)

        assert instance0 == instance1

    def test_provider_binding__should_call_provider_for_each_injection(self):
        injector = Injector(lambda binder: binder.bind_to_provider(int, random))
        instance0 = injector.get_instance(int)
        instance1 = injector.get_instance(int)
        assert instance0 != instance1


    def test_runtime_binding__should_create_runtime_singleton(self):
        class MyClass(object):
            pass

        injector = Injector()
        instance0 = injector.get_instance(MyClass)
        instance1 = injector.get_instance(MyClass)

        assert instance0 is instance1
        assert isinstance(instance0, MyClass)

    def test_runtime_binding__not_callable(self):
        injector = Injector()
        self.assertRaisesRegexp(InjectorException, 
                               'Cannot create a runtime binding, the key is not callable, key=123',
                                injector.get_instance, 123)


class TestInject(TestCase):
    def tearDown(self):
        inject.clear()

    def test_configure__should_create_injector(self):
        injector0 = inject.configure()
        injector1 = inject.get_injector()
        assert injector0
        assert injector0 is injector1

    def test_configure__should_add_bindings(self):
        injector = inject.configure(lambda binder: binder.bind(int, 123))
        instance = injector.get_instance(int)
        assert instance == 123

    def test_configure__already_configured(self):
        inject.configure()

        self.assertRaisesRegexp(InjectorException, 'Injector is already configured',
                                inject.configure)

    def test_clear_and_configure(self):
        injector0 = inject.configure()
        injector1 = inject.clear_and_configure()    # No exception.
        assert injector0
        assert injector1
        assert injector1 is not injector0

    def test_get_injector_or_die(self):
        self.assertRaisesRegexp(InjectorException, 'No injector is configured',
                                inject.get_injector_or_die)

    def test_instance(self):
        inject.configure(lambda binder: binder.bind(int, 123))
        instance = inject.instance(int)
        assert instance == 123

    def test_attr(self):
        class MyClass(object):
            field = inject.attr(int)

        inject.configure(lambda binder: binder.bind(int, 123))
        my = MyClass()
        value0 = my.field
        value1 = my.field

        assert value0 == 123
        assert value1 == 123

    def test_class_attr(self):
        class MyClass(object):
            field = inject.attr(int)

        inject.configure(lambda binder: binder.bind(int, 123))
        value0 = MyClass.field
        value1 = MyClass.field

        assert value0 == 123
        assert value1 == 123

    def test_param_by_name(self):
        @inject.param('val')
        def test_func(val=None):
            return val

        inject.configure(lambda binder: binder.bind('val', 123))

        assert test_func() == 123
        assert test_func(val=321) == 321

    def test_param_by_class(self):
        @inject.param('val', int)
        def test_func(val):
            return val

        inject.configure(lambda binder: binder.bind(int, 123))

        assert test_func() == 123


        
class TestFunctional(TestCase):
    def tearDown(self):
        inject.clear()
    
    def test(self):
        class Config(object):
            def __init__(self, greeting):
                self.greeting = greeting
        
        class Cache(object):
            config = inject.attr(Config)
            
            def load_greeting(self):
                return self.config.greeting
        
        class User(object):
            cache = inject.attr(Cache)
            
            def __init__(self, name):
                self.name = name
                
            def greet(self):
                return '%s, %s' % (self.cache.load_greeting(), self.name)
        
        def config(binder):
            binder.bind(Config, Config('Hello'))
        
        inject.configure(config)
        
        user = User('John Doe')
        greeting = user.greet()
        assert greeting == 'Hello, John Doe'

########NEW FILE########
