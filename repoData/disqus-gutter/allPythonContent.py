__FILENAME__ = base
class classproperty(object):

    def __init__(self, getter):
        self.getter = getter

    def __get__(self, instance, owner):
        return self.getter(owner)


class argument(object):

    def __init__(self, variable, getter):
        if issubclass(type(getter), basestring):
            self.getter = lambda self: getattr(self.input, getter)
        else:
            self.getter = getter

        self.owner = None
        self.variable = variable

    def __get__(self, instance, owner):
        self.owner = owner

        if instance:
            return self.variable(self.getter(instance))
        else:
            return self

    def __str__(self):
        if self.name:
            return "%s.%s" % (self.owner.__name__, self.name)
        else:
            return repr(self)

    @property
    def name(self):
        for name, attr in vars(self.owner).items():
            if attr is self:
                return name


class Container(object):
    """
    Base class for Arguments, which are responsible for understanding inputs
    and returning Argument Variables.  Argument variables are compared against
    the Operator inside of a Condition, for deciding if a condition applies to
    the specified input.
    """

    COMPATIBLE_TYPE = None

    def __init__(self, inpt):
        self.input = inpt

    @classproperty
    def arguments(cls):
        return dict(
            (key, value) for key, value in vars(cls).items()
            if type(value) is argument
        )

    @property
    def applies(self):
        return type(self.input) is self.COMPATIBLE_TYPE

########NEW FILE########
__FILENAME__ = variables
import random


class Base(object):

    def __init__(self, value):
        self.value = value

    def __proxy_to_value_method(method):
        def func(self, *args, **kwargs):

            if hasattr(self, 'value'):
                return getattr(self.value, method)(*args, **kwargs)
            else:
                raise NotImplementedError

        return func

    __cmp__ = __proxy_to_value_method('__cmp__')
    __hash__ = __proxy_to_value_method('__hash__')
    __nonzero__ = __proxy_to_value_method('__nonzero__')

    @staticmethod
    def to_python(value):
        return value


class Value(Base):
    pass


class Integer(Base):

    @staticmethod
    def to_python(value):
        return int(value)


class Float(Base):

    @staticmethod
    def to_python(value):
        return float(value)


class Boolean(Base):

    def __init__(self, value, hash_value=None):
        super(Boolean, self).__init__(value)
        self.hash_value = hash_value or random.getrandbits(128)

    def __hash__(self, *args, **kwargs):
        return hash(self.hash_value)

    @staticmethod
    def to_python(value):
        return bool(value)


class String(Base):

    def __cmp__(self, other):
        return cmp(self.value, other)

    def __nonzero__(self, *args, **kwargs):
        return bool(self.value)

    @staticmethod
    def to_python(value):
        return str(value)

########NEW FILE########
__FILENAME__ = decorators
from functools import wraps
from gutter.client.singleton import gutter as default_gutter
from django.http import Http404, HttpResponseRedirect


def switch_active(name, redirect_to=None, gutter=None):

    if not gutter:
        gutter = default_gutter

    def inner(func):

        @wraps(func)
        def view(request, *args, **kwargs):
            if gutter.active(name, request):
                return func(request, *args, **kwargs)
            elif redirect_to:
                return HttpResponseRedirect(redirect_to)
            else:
                raise Http404('Switch %s not active' % name)

        return view

    return inner

########NEW FILE########
__FILENAME__ = default
#: Default manager instance
from gutter.client.singleton import gutter

########NEW FILE########
__FILENAME__ = models
"""
gutter.models
~~~~~~~~~~~~~~~

:copyright: (c) 2010-2012 DISQUS.
:license: Apache License 2.0, see LICENSE for more details.
"""

from gutter.client import signals
from functools import partial
import threading


class Switch(object):
    """
    A switch encapsulates the concept of an item that is either 'on' or 'off'
    depending on the input.  The switch determines this by checking each of its
    conditions and seeing if it applies to a certain input.  All the switch does
    is ask each of its Conditions if it applies to the provided input.  Normally
    any condition can be true for the Switch to be enabled for a particular
    input, but of ``switch.compounded`` is set to True, then **all** of the
    switches conditions need to be true in order to be enabled.

    See the Condition class for more information on what a Condition is and how
    it checks to see if it's satisfied by an input.
    """

    class states:
        DISABLED = 1
        SELECTIVE = 2
        GLOBAL = 3

    def __init__(self, name, state=states.DISABLED, compounded=False,
                 parent=None, concent=True, manager=None, label=None,
                 description=None):
        self._name = str(name)
        self.label = label
        self.description = description
        self.state = state
        self.conditions = list()
        self.compounded = compounded
        self.parent = parent
        self.concent = concent
        self.children = []
        self.manager = manager
        self.reset()

    @property
    def name(self):
        return self._name

    def __repr__(self):
        kwargs = dict(
            state=self.state,
            compounded=self.compounded,
            concent=self.concent
        )
        parts = ["%s=%s" % (k, v) for k, v in kwargs.items()]
        return '<Switch("%s") conditions=%s, %s>' % (
            self.name,
            len(self.conditions),
            ', '.join(parts)
        )

    def __eq__(self, other):
            return (
                self.name == other.name and
                self.state is other.state and
                self.compounded is other.compounded and
                self.concent is other.concent
            )

    def __getstate__(self):
        inner_dict = vars(self).copy()
        inner_dict.pop('manager', False)
        return inner_dict

    def __setstate__(self, state):
        ### legacy conversion for 0.2 -> 0.3 ###
        parent_or_parentname = state.pop('parent', '')
        parent = getattr(parent_or_parentname, 'name', parent_or_parentname)
        state['parent'] = parent

        children = state.pop('children', [])
        children = [getattr(child, 'name', child) for child in children]
        state['children'] = children

        if 'name' in state:
            state['_name'] = state.pop('name')
        ### /legacy conversion for 0.2 -> 0.3 ###

        self.__dict__ = state
        if not hasattr(self, 'manager'):
            setattr(self, 'manager', None)

    def enabled_for(self, inpt):
        """
        Checks to see if this switch is enabled for the provided input.

        If ``compounded``, all switch conditions must be ``True`` for the switch
        to be enabled.  Otherwise, *any* condition needs to be ``True`` for the
        switch to be enabled.

        The switch state is then checked to see if it is ``GLOBAL`` or
        ``DISABLED``.  If it is not, then the switch is ``SELECTIVE`` and each
        condition is checked.

        Keyword Arguments:
        inpt -- An instance of the ``Input`` class.
        """
        signals.switch_checked.call(self)
        signal_decorated = partial(self.__signal_and_return, inpt)

        if self.state is self.states.GLOBAL:
            return signal_decorated(True)
        elif self.state is self.states.DISABLED:
            return signal_decorated(False)

        result = self.__enabled_func(cond.call(inpt) for cond in self.conditions)
        return signal_decorated(result)

    def save(self):
        """
        Saves this switch in its manager (if present).

        Equivalent to ``self.manager.update(self)``.  If no ``manager`` is set
        for the switch, this method is a no-op.
        """
        if self.manager:
            self.manager.update(self)

    @property
    def changes(self):
        """
        A dictionary of changes to the switch since last saved.

        Switch changes are a dict in the following format::

            {
                'property_name': {'previous': value, 'current': value}
            }

        For example, if the switch name change from ``foo`` to ``bar``, the
        changes dict will be in the following structure::

            {
                'name': {'previous': 'foo', 'current': 'bar'}
            }
        """
        return dict(list(self.__changes()))

    @property
    def changed(self):
        """
        Boolean of if the switch has changed since last saved.
        """
        return bool(list(self.__changes()))

    def reset(self):
        """
        Resets switch change tracking.

        No switch properties are altered, only the tracking of what has changed
        is reset.
        """
        self.__init_vars = vars(self).copy()

    @property
    def state_string(self):
        state_vars = vars(self.states)
        rev = dict(zip(state_vars.values(), state_vars))
        return rev[self.state]

    @property
    def __enabled_func(self):
        if self.compounded:
            return all
        else:
            return any

    def __changes(self):
        for key, value in self.__init_vars.items():
            if key is '_Switch__init_vars':
                continue
            elif key not in vars(self) or getattr(self, key) != value:
                yield (key, dict(previous=value, current=getattr(self, key)))

    def __signal_and_return(self, inpt, is_enabled):
        if is_enabled:
            signals.switch_active.call(self, inpt)

        return is_enabled


class Condition(object):
    """
    A Condition is the configuration of an argument, its attribute and an
    operator. It tells you if it itself is true or false given an input.

    The ``argument`` defines what this condition is checking.  Perhaps it's a
    ``User`` or ``Request`` object. The ``attribute`` name is then extracted out
    of an instance of the argument to produce a variable. That variable is then
    compared to the operator to determine if the condition applies to the input
    or not.

    For example, for the request IP address, you would define a ``Request``
    argument, that had an ``ip`` property.  A condition would then be constructed
    like so:

    from myapp.gutter import RequestArgument
    from gutter.client.models import Condition

        >> condition = Condition(argument=RequestArgument, attribute='ip', operator=some_operator)

    When the Condition is called, it is passed the input. The argument is then
    called (constructed) with input object to produce an instance.  The
    attribute is then extracted from that instance to produce the variable.
    The extracted variable is then checked against the operator.

    To put it another way, say you wanted a condition to only allow your switch
    to people between 15 and 30 years old.  To make the condition:

        1. You would create a ``UserArgument`` class that takes a user object in
           its constructor.  The class also has an ``age`` method which returns
           the user object's age.
        2. You would then create a new Condition via:
           ``Condition(argument=UserInput, attribute='age', operator=Between(15, 30))``.
        3. You then call that condition with a ``User``, and it would return
           ``True`` if the age of the user the ``UserArgument`` instance wraps
           is between 15 and 30.
    """

    def __init__(self, argument, attribute, operator, negative=False):
        self.attribute = attribute
        self.argument = argument
        self.operator = operator
        self.negative = negative

    def __repr__(self):
        argument = ".".join((self.argument.__name__, self.attribute))
        return '<Condition "%s" %s>' % (argument, self.operator)

    def __eq__(self, other):
        return (
            self.argument == other.argument and
            self.attribute == other.attribute and
            self.operator == other.operator and
            self.negative is other.negative
        )

    def call(self, inpt):
        """
        Returns if the condition applies to the ``inpt``.

        If the class ``inpt`` is an instance of is not the same class as the
        condition's own ``argument``, then ``False`` is returned.  This also
        applies to the ``NONE`` input.

        Otherwise, ``argument`` is called, with ``inpt`` as the instance and
        the value is compared to the ``operator`` and the Value is returned.  If
        the condition is ``negative``, then then ``not`` the value is returned.

        Keyword Arguments:
        inpt -- An instance of the ``Input`` class.
        """
        if inpt is Manager.NONE_INPUT:
            return False

        # Call (construct) the argument with the input object
        argument_instance = self.argument(inpt)

        if not argument_instance.applies:
            return False

        application = self.__apply(argument_instance, inpt)

        if self.negative:
            application = not application

        return application

    @property
    def argument_string(self):
        parts = [self.argument.__name__, self.attribute]
        return '.'.join(map(str, parts))

    def __str__(self):
        return "%s %s" % (self.argument_string, self.operator)

    def __apply(self, argument_instance, inpt):
        variable = getattr(argument_instance, self.attribute)

        try:
            return self.operator.applies_to(variable)
        except Exception as error:
            signals.condition_apply_error.call(self, inpt, error)
            return False


class Manager(threading.local):
    """
    The Manager holds all state for Gutter.  It knows what Switches have been
    registered, and also what Input objects are currently being applied.  It
    also offers an ``active`` method to ask it if a given switch name is
    active, given its conditions and current inputs.
    """

    key_separator = ':'
    namespace_separator = '.'
    default_namespace = ['default']

    #: Special singleton used to represent a "no input" which arguments can look
    #: for and ignore
    NONE_INPUT = object()

    def __init__(self, storage, autocreate=False, switch_class=Switch,
                 inputs=None, namespace=None):

        if inputs is None:
            inputs = []

        if namespace is None:
            namespace = self.default_namespace
        elif isinstance(namespace, basestring):
            namespace = [namespace]

        self.storage = storage
        self.autocreate = autocreate
        self.inputs = inputs
        self.switch_class = switch_class
        self.namespace = namespace

    def __getstate__(self):
        inner_dict = vars(self).copy()
        inner_dict.pop('inputs', False)
        inner_dict.pop('storage', False)
        return inner_dict

    def __getitem__(self, key):
        return self.switch(key)

    @property
    def switches(self):
        """
        List of all switches currently registered.
        """
        results = [
            switch for name, switch in self.storage.iteritems()
            if name.startswith(self.__joined_namespace)
        ]

        return results

    def switch(self, name):
        """
        Returns the switch with the provided ``name``.

        If ``autocreate`` is set to ``True`` and no switch with that name
        exists, a ``DISABLED`` switch will be with that name.

        Keyword Arguments:
        name -- A name of a switch.
        """
        try:
            switch = self.storage[self.__namespaced(name)]
        except KeyError:
            if not self.autocreate:
                raise ValueError("No switch named '%s' registered" % name)

            switch = self.__create_and_register_disabled_switch(name)

        switch.manager = self
        return switch

    def register(self, switch, signal=signals.switch_registered):
        '''
        Register a switch and persist it to the storage.
        '''
        if not switch.name:
            raise ValueError('Switch name cannot be blank')

        self.__persist(switch)
        self.__sync_parental_relationships(switch)

        switch.manager = self
        signal.call(switch)

    def unregister(self, switch_or_name):
        name = getattr(switch_or_name, 'name', switch_or_name)
        switch = self.switch(name)

        [self.unregister(child) for child in switch.children]

        del self.storage[self.__namespaced(name)]
        signals.switch_unregistered.call(switch)

    def input(self, *inputs):
        self.inputs = list(inputs)

    def flush(self):
        self.inputs = []

    def active(self, name, *inputs, **kwargs):
        switch = self.switch(name)

        if not kwargs.get('exclusive', False):
            inputs = tuple(self.inputs) + inputs

        # Also check the switches against "NONE" input. This ensures there will
        # be at least one input checked.
        if not inputs:
            inputs = (self.NONE_INPUT,)

        # If necessary, the switch first consents with its parent and returns
        # false if the switch is consenting and the parent is not enabled for
        # ``inputs``.
        if switch.concent and switch.parent and not self.active(switch.parent, *inputs, **kwargs):
            return False

        return any(map(switch.enabled_for, inputs))

    def update(self, switch):

        self.register(switch, signal=signals.switch_updated)
        switch.reset()

        # If this switch has any children, it's likely their instance of this
        # switch (their ``parent``) is now "stale" since this switch has
        # been updated. In order for them to pick up their new parent, we need
        # to re-save them.
        #
        # ``register`` is not used here since we do not need/want to sync
        # parental relationships.
        for child in getattr(switch, 'children', []):
            child = self.storage[self.__namespaced(child)]
            child.parent = switch.name
            self.__persist(child)

    def namespaced(self, namespace):
        new_namespace = []

        # Only start with the current namesapce if it's not the default
        # namespace
        if self.namespace is not self.default_namespace:
            new_namespace = list(self.namespace)

        new_namespace.append(namespace)

        return type(self)(
            storage=self.storage,
            autocreate=self.autocreate,
            inputs=self.inputs,
            switch_class=self.switch_class,
            namespace=new_namespace,
        )

    def __persist(self, switch):
        self.storage[self.__namespaced(switch.name)] = switch
        return switch

    def __create_and_register_disabled_switch(self, name):
        switch = self.switch_class(name)
        switch.state = self.switch_class.states.DISABLED
        self.register(switch)
        return switch

    def __sync_parental_relationships(self, switch):
        new_parent = None

        try:
            new_parent = self.switch(self.__parent_key_for(switch))
            switch.parent = new_parent.name
            new_parent.children.append(switch.name)
            new_parent.save()
        except ValueError:
            # no parent found or created, so we just pass
            pass


    def __parent_key_for(self, switch):
        # TODO: Make this a method on the switch object
        parent_parts = switch.name.split(self.key_separator)[:-1]
        return self.key_separator.join(parent_parts)

    def __namespaced(self, name=''):
        if not self.__joined_namespace:
            return name
        else:
            return self.namespace_separator.join(
                (self.__joined_namespace, name)
            )

    @property
    def __joined_namespace(self):
        return self.namespace_separator.join(self.namespace)

########NEW FILE########
__FILENAME__ = comparable
from gutter.client.operators import Base


class Equals(Base):

    name = 'equals'
    group = 'comparable'
    preposition = 'equal to'
    arguments = ('value',)

    def applies_to(self, argument):
        return argument == self.value

    def __str__(self):
        return 'equal to "%s"' % self.value


class Between(Base):

    name = 'between'
    group = 'comparable'
    preposition = 'between'
    arguments = ('lower_limit', 'upper_limit')

    def applies_to(self, argument):
        return argument > self.lower_limit and argument < self.upper_limit

    def __str__(self):
        return 'between "%s" and "%s"' % (self.lower_limit, self.upper_limit)


class LessThan(Base):

    name = 'before'
    group = 'comparable'
    preposition = 'less than'
    arguments = ('upper_limit',)

    def applies_to(self, argument):
        return argument < self.upper_limit

    def __str__(self):
        return 'less than "%s"' % self.upper_limit


class LessThanOrEqualTo(LessThan):

    name = 'less_than_or_equal_to'
    group = 'comparable'
    preposition = 'less than or equal to'

    def applies_to(self, argument):
        return argument <= self.upper_limit

    def __str__(self):
        return 'less than or equal to "%s"' % self.upper_limit


class MoreThan(Base):

    name = 'more_than'
    group = 'comparable'
    preposition = 'more than'
    arguments = ('lower_limit',)

    def applies_to(self, argument):
        return argument > self.lower_limit

    def __str__(self):
        return 'more than "%s"' % self.lower_limit


class MoreThanOrEqualTo(MoreThan):

    name = 'more_than_or_equal_to'
    group = 'comparable'
    preposition = 'more than or equal to'

    def applies_to(self, argument):
        return argument >= self.lower_limit

    def __str__(self):
        return 'more than or equal to "%s"' % self.lower_limit

########NEW FILE########
__FILENAME__ = identity
from gutter.client.operators import Base


class Truthy(Base):

    name = 'true'
    group = 'identity'
    preposition = 'true'

    def applies_to(self, argument):
        return bool(argument)

    def __str__(self):
        return 'true'

########NEW FILE########
__FILENAME__ = misc
from gutter.client.operators import Base


class PercentRange(Base):

    name = 'percent_range'
    group = 'misc'
    preposition = 'in the percentage range of'
    arguments = ('lower_limit', 'upper_limit')

    def __init__(self, lower_limit, upper_limit):
        self.upper_limit = float(upper_limit)
        self.lower_limit = float(lower_limit)

    def applies_to(self, argument):
        if not argument:
            return False
        else:
            return self.lower_limit <= (hash(argument) % 100) < self.upper_limit

    def __str__(self):
        return 'in %s - %s%% of values' % (self.lower_limit, self.upper_limit)


class Percent(PercentRange):

    name = 'percent'
    group = 'misc'
    preposition = 'within the percentage of'
    arguments = ('percentage',)

    def __init__(self, percentage):
        self.upper_limit = float(percentage)
        self.lower_limit = 0.0

    @property
    def variables(self):
        return dict(percentage=self.upper_limit)

    def __str__(self):
        return 'in %s%% of values' % self.upper_limit

########NEW FILE########
__FILENAME__ = settings
from durabledict import MemoryDict


class manager(object):
    storage_engine = MemoryDict()
    autocreate = False
    inputs = []
    default = None

########NEW FILE########
__FILENAME__ = signals
class Signal(object):

    def __init__(self):
        self.__callbacks = []

    def connect(self, callback):
        if not callable(callback):
            raise ValueError("Callback argument must be callable")

        self.__callbacks.append(callback)

    def call(self, *args, **kwargs):
        for callback in self.__callbacks:
            callback(*args, **kwargs)

    def reset(self):
        self.__callbacks = []


switch_registered = Signal()
switch_unregistered = Signal()
switch_updated = Signal()
condition_apply_error = Signal()
switch_checked = Signal()
switch_active = Signal()

########NEW FILE########
__FILENAME__ = singleton
from gutter.client import settings
from gutter.client.models import Manager

gutter = settings.manager.default or Manager(
    storage=settings.manager.storage_engine,
    autocreate=settings.manager.autocreate,
    inputs=settings.manager.inputs
)

########NEW FILE########
__FILENAME__ = testutils
"""
gutter.testutils
~~~~~~~~~~~~~~~~~~

:copyright: (c) 2010-2012 DISQUS.
:license: Apache License 2.0, see LICENSE for more details.
"""

from functools import wraps
from gutter.client.singleton import gutter


class SwitchContextManager(object):
    """
    Allows temporarily enabling or disabling a switch.

    Ideal for testing.

    >>> @switches(my_switch_name=True)
    >>> def foo():
    >>>     print gutter.active('my_switch_name')

    >>> def foo():
    >>>     with switches(my_switch_name=True):
    >>>         print gutter.active('my_switch_name')

    You may also optionally pass an instance of ``SwitchManager``
    as the first argument.

    >>> def foo():
    >>>     with switches(gutter, my_switch_name=True):
    >>>         print gutter.active('my_switch_name')
    """
    def __init__(self, gutter=gutter, **keys):
        self.previous_active_func = gutter.active
        self.gutter = gutter
        self.keys = keys

    def __call__(self, func):
        @wraps(func)
        def inner(*args, **kwargs):
            with self:
                return func(*args, **kwargs)

        return inner

    def __enter__(self):

        def patched_active(gutter):
            real_active = gutter.active

            def wrapped(key, *args, **kwargs):
                if key in self.keys:
                    return self.keys[key]

                return real_active(key, *args, **kwargs)

            return wrapped

        self.gutter.active = patched_active(self.gutter)

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.gutter.active = self.previous_active_func

switches = SwitchContextManager

########NEW FILE########
__FILENAME__ = wsgi
from gutter.client import signals
from werkzeug.local import Local


class EnabledSwitchesMiddleware(object):
    """
    Middleware to add active gutter switches for the HTTP request in a
    X-Gutter-Switch headers.

    NOTE: This middleware breaks streaming responses.  Since it is impossible
    to determine the active switches used for an HTTP response until the entire
    response body has been read, this middleware buffers the entire reponse body
    into memory, then adds the X-Gutter-Switch header, before returning.
    """

    def __init__(self, application, gutter=None):
        self.application = application

        if not gutter:
            from gutter.client.singleton import gutter

        self.gutter = gutter
        self.locals = Local()

        self.locals.on_switch_active = self.__signal_handler
        signals.switch_active.connect(self.locals.on_switch_active)

    def __signal_handler(self, switch, inpt):
        self.locals.switches_active.append(switch.name)

    def __call__(self, environ, start_response):
        self.locals.switches_active = []
        body, status, headers = self.__call_app(environ, start_response)
        self.__add_gutter_header_to(headers)

        start_response(status, headers)
        return body

    def __add_gutter_header_to(self, headers):
        active_switches = ','.join(self.locals.switches_active)
        headers.append(('X-Gutter-Switch', 'active=%s' % active_switches))

    def __call_app(self, environ, start_response):
        status_headers = [None, None]
        body = []

        def capture_start_response(status, headers):
            status_headers[:] = (status, headers)
            return body.append

        map(body.append, self.application(environ, capture_start_response))

        return (body,) + tuple(status_headers)

########NEW FILE########
__FILENAME__ = test_arguments
import unittest2
from mock import MagicMock, Mock
from nose.tools import *

from gutter.client.arguments.variables import *
from gutter.client import arguments
from gutter.client.arguments import Container

from exam.decorators import fixture


class MyArguments(Container):
    variable1 = arguments.Value(lambda self: self.input)
    opposite_variable1 = arguments.Value(lambda self: not self.input)
    str_variable = arguments.String('prop')


class TestBase(unittest2.TestCase):

    container = fixture(Container, True)
    subclass_arguments = fixture(MyArguments, True)
    subclass_str_arg = fixture(MyArguments, Mock(prop=45))

    def test_applies_is_false_if_compatible_type_is_none(self):
        eq_(self.container.COMPATIBLE_TYPE, None)
        eq_(self.container.applies, False)

    def applies_is_true_if_input_type_is_compatible_type(self):
        self.container.COMPATIBLE_TYPE = int
        ok_(type(self.container.input) is not int)

        self.assertFalse(self.container.applies)
        self.container.input = 9
        self.assertTrue(self.container.applies)

    def test_argument_variables_defaults_to_nothing(self):
        eq_(self.container.arguments, {})

    def test_variables_only_returns_argument_objects(self):
        eq_(
            MyArguments.arguments,
            dict(
                variable1=MyArguments.variable1,
                opposite_variable1=MyArguments.opposite_variable1,
                str_variable=MyArguments.str_variable
            )
        )

    def test_arguments_work(self):
        ok_(self.subclass_arguments.variable1)

    def test_can_use_string_as_argument(self):
        eq_(self.subclass_str_arg.str_variable, 45)

    def test_str_is_argument_container_plus_argument_name(self):
        eq_(str(MyArguments.variable1), 'MyArguments.variable1')

    def test_owner_is_class_its_in(self):
        eq_(MyArguments.variable1.owner, MyArguments)

    def test_name_is_name_inside_class(self):
        eq_(MyArguments.variable1.name, 'variable1')
        eq_(MyArguments.opposite_variable1.name, 'opposite_variable1')


class BaseVariableTest(object):

    interface_functions = ['__cmp__', '__hash__', '__nonzero__']

    @fixture
    def argument(self):
        return self.klass(self.valid_comparison_value)

    @fixture
    def interface_methods(self):
        return [getattr(self.argument, f) for f in self.interface_functions]

    def test_implements_comparison_methods(self):
        map(ok_, self.interface_methods)

    def test_implements_to_python(self):
        ok_(self.klass.to_python('1'))


class DelegateToValue(object):

    def test_delegates_all_interface_function_to_the_value_passed_in(self):
        value_passed_in = MagicMock()
        value_passed_in.__cmp__ = Mock()
        argument = self.klass(value_passed_in)

        for function in self.interface_functions:
            values_function = getattr(value_passed_in, function)
            arguments_function = getattr(argument, function)

            arguments_function(self.valid_comparison_value)
            values_function.assert_called_once_with(self.valid_comparison_value)


class ValueTest(BaseVariableTest, DelegateToValue, unittest2.TestCase):

    klass = Value
    valid_comparison_value = 'marv'

    def test_to_python_returns_same_object(self):
        variable = 'hello'
        eq_(Value.to_python(variable), variable)


class BooleanTest(BaseVariableTest, DelegateToValue, unittest2.TestCase):

    klass = Boolean
    valid_comparison_value = True
    interface_functions = ['__cmp__', '__nonzero__']

    def test_hashes_its_hash_value_instead_of_value(self):
        boolean = Boolean(True, hash_value='another value')
        assert_not_equals(hash(True), hash(boolean))
        assert_equals(hash('another value'), hash(boolean))

    def test_creates_random_hash_value_if_not_provided(self):
        boolean = Boolean(True)
        assert_not_equals(hash(True), hash(boolean))
        assert_not_equals(hash(None), hash(boolean))

        assert_not_equals(hash(boolean), hash(Boolean(True)))

    def test_to_python_booleans_the_value(self):
        eq_(Boolean.to_python(1), True)
        eq_(Boolean.to_python(0), False)
        eq_(Boolean.to_python('0'), True)


class StringTest(BaseVariableTest, DelegateToValue, unittest2.TestCase):

    klass = String
    valid_comparison_value = 'foobazzle'
    interface_functions = ['__hash__']

    def test_cmp_compares_with_other_value(self):
        eq_(self.argument.__cmp__('zebra'), -1)
        eq_(self.argument.__cmp__('aardvark'), 1)
        eq_(self.argument.__cmp__('foobazzle'), 0)

    def test_nonzero_returns_if_truthy(self):
        ok_(String('hello').__nonzero__() is True)
        ok_(String('').__nonzero__() is False)
        ok_(String('0').__nonzero__() is True)

    def test_to_python_strs_the_value(self):
        eq_(String.to_python(True), 'True')
        eq_(String.to_python('hello'), 'hello')
        eq_(String.to_python(1), '1')


class IntegerTest(BaseVariableTest, DelegateToValue, unittest2.TestCase):

    klass = Integer
    valid_comparison_value = 1

    def test_to_python_ints_the_value(self):
        eq_(Integer.to_python(True), 1)
        eq_(Integer.to_python(1.0), 1)
        eq_(Integer.to_python(1.5), 1)
        eq_(Integer.to_python('1337'), 1337)

########NEW FILE########
__FILENAME__ = test_decorators
import unittest2

from mock import patch

from exam.cases import Exam
from exam.decorators import patcher

from gutter.client.decorators import switch_active

from nose.tools import *

from django.http import Http404


def my_view(request):
    return 'view called'


def decorated(*args, **kwargs):
    return switch_active('request', *args, **kwargs)(my_view)


class DecoratorTest(Exam, unittest2.TestCase):

    gutter = patcher(
        'gutter.client.decorators.default_gutter',
        **{'active.return_value': False}
    )

    def test_raises_a_404_error_if_switch_is_inactive(self):
        self.assertFalse(self.gutter.active('junk'))
        self.assertRaises(Http404, decorated(), 'junk')

    @patch('gutter.client.decorators.HttpResponseRedirect')
    def test_redirects_to_url_if_inactive_and_redirect_to_passed(self, httprr):
        self.assertFalse(self.gutter.active('junk'))
        eq_(decorated(redirect_to='location')('junk'), httprr.return_value)
        httprr.assert_called_once_with('location')

    def test_calls_the_function_if_switch_is_active(self):
        self.gutter.active.return_value = True
        eq_(decorated()('junk'), 'view called')

########NEW FILE########
__FILENAME__ = test_gutter
import unittest2

from nose.tools import *


class GutterTest(unittest2.TestCase):

    def test_root_gutter_is_just_singleton(self):
        from gutter.client.default import gutter as root_gutter
        from gutter.client.singleton import gutter as singleton_gutter
        eq_(root_gutter, singleton_gutter)

########NEW FILE########
__FILENAME__ = test_integration
import unittest2
from nose.tools import *

import zlib

from redis import Redis
from durabledict.redis import RedisDict

from gutter.client.operators.comparable import *
from gutter.client.operators.identity import *
from gutter.client.operators.misc import *
from gutter.client.models import Switch, Condition, Manager
from gutter.client import arguments
from gutter.client import signals

from exam.decorators import fixture, before, after, around
from exam.cases import Exam


class deterministicstring(str):
    """
    Since the percentage-based conditions rely on the hash value from their
    arguments, we use this special deterministicstring class to return
    deterministic string values from the crc32 of itself.
    """

    def __hash__(self):
        return zlib.crc32(self)


class User(object):

    def __init__(self, name, age, location='San Francisco', married=False):
        self.name = name
        self.age = age
        self.location = location
        self.married = married


class UserArguments(arguments.Container):

    COMPATIBLE_TYPE = User

    name = arguments.String(lambda self: self.input.name)
    age = arguments.Value(lambda self: self.input.age)
    location = arguments.String(lambda self: self.input.location)
    married = arguments.Boolean(lambda self: self.input.married)


class IntegerArguments(arguments.Container):
    COMPATIBLE_TYPE = int

    value = arguments.Integer(lambda self: self.input)


class TestIntegration(Exam, unittest2.TestCase):

    class Callback(object):

        def __init__(self):
            self.register_calls = []
            self.unregister_calls = []
            self.update_calls = []

        def switch_added(self, switch):
            self.register_calls.append(switch)

        def switch_removed(self, switch):
            self.unregister_calls.append(switch)

        def switch_updated(self, switch):
            self.update_calls.append((switch, switch.changes))

    class inputs(object):

        def __init__(self, manager, *inputs):
            self.manager = manager
            self.manager.input(*inputs)

        def __enter__(self):
            return self

        def active(self, *args, **kwargs):
            return self.manager.active(*args, **kwargs)

        def __exit__(self, type, value, traceback):
            self.manager.flush()

    callback = fixture(Callback)

    @fixture
    def manager(self):
        return Manager(storage=dict())

    @before
    def build_objects(self):
        self.setup_inputs()
        self.setup_conditions()
        self.setup_switches()

    @after
    def reset_objects(self):
        signals.switch_registered.reset()
        signals.switch_unregistered.reset()
        signals.switch_updated.reset()

    def setup_inputs(self):
        self.jeff = User(deterministicstring('jeff'), 21)
        self.frank = User(deterministicstring('frank'), 10, location="Seattle")
        self.larry = User(deterministicstring('bill'), 70, location="Yakima", married=True)
        self.timmy = User(deterministicstring('timmy'), 12)
        self.steve = User(deterministicstring('timmy'), 19)

    def setup_conditions(self):
        self.age_65_and_up = Condition(UserArguments, 'age', MoreThanOrEqualTo(lower_limit=65))
        self.age_under_18 = Condition(UserArguments, 'age', LessThan(upper_limit=18))
        self.age_not_under_18 = Condition(UserArguments, 'age', LessThan(upper_limit=18), negative=True)
        self.age_21_plus = Condition(UserArguments, 'age', MoreThanOrEqualTo(lower_limit=21))
        self.age_between_13_and_18 = Condition(UserArguments, 'age', Between(lower_limit=13, upper_limit=18))

        self.in_sf = Condition(UserArguments, 'location', Equals(value='San Francisco'))
        self.has_location = Condition(UserArguments, 'location', Truthy())

        self.ten_percent = Condition(UserArguments, 'name', Percent(percentage=10))
        self.upper_50_percent = Condition(UserArguments, 'name', PercentRange(lower_limit=50, upper_limit=100))
        self.answer_to_life = Condition(IntegerArguments, 'value', Equals(value=42))

    def setup_switches(self):
        self.add_switch('can drink', condition=self.age_21_plus)
        self.add_switch('can drink in europe', condition=self.age_21_plus, state=Switch.states.GLOBAL)
        self.add_switch('can drink:answer to life', condition=self.answer_to_life)
        self.add_switch('can drink:wine', condition=self.in_sf, concent=True)
        self.add_switch('retired', condition=self.age_65_and_up)
        self.add_switch('can vote', condition=self.age_not_under_18)
        self.add_switch('teenager', condition=self.age_between_13_and_18)
        self.add_switch('SF resident', condition=self.in_sf)
        self.add_switch('teen or in SF', self.age_between_13_and_18, self.in_sf)
        self.add_switch('teen and in SF', self.age_between_13_and_18,
                        self.has_location, compounded=True)
        self.add_switch('10 percent', self.ten_percent)
        self.add_switch('Upper 50 percent', self.upper_50_percent)

    def add_switch(self, name, condition=None, *conditions, **kwargs):
        switch = Switch(name, compounded=kwargs.get('compounded', False))
        switch.state = kwargs.get('state', Switch.states.SELECTIVE)
        conditions = list(conditions)

        if condition:
            conditions.append(condition)

        [switch.conditions.append(c) for c in conditions]
        kwargs.get('manager', self.manager).register(switch)
        return switch

    def test_basic_switches_work_with_conditions(self):
        with self.inputs(self.manager, self.larry) as context:
            ok_(context.active('can drink') is True)
            ok_(context.active('can drink in europe') is True)
            ok_(context.active('can vote') is True)
            ok_(context.active('SF resident') is False)
            ok_(context.active('retired') is True)
            ok_(context.active('10 percent') is False)
            ok_(context.active('Upper 50 percent') is True)

        with self.inputs(self.manager, self.jeff) as context:
            ok_(context.active('can drink') is True)
            ok_(context.active('can drink in europe') is True)
            ok_(context.active('can vote') is True)
            ok_(context.active('SF resident') is True)
            ok_(context.active('teenager') is False)
            ok_(context.active('teen or in SF') is True)
            ok_(context.active('teen and in SF') is False)
            ok_(context.active('10 percent') is False)
            ok_(context.active('Upper 50 percent') is True)

        with self.inputs(self.manager, self.frank) as context:
            ok_(context.active('can drink') is False)
            ok_(context.active('can drink in europe') is True)
            ok_(context.active('can vote') is False)
            ok_(context.active('teenager') is False)
            ok_(context.active('10 percent') is False)
            ok_(context.active('Upper 50 percent') is True)

    def test_can_use_extra_inputs_to_active(self):
        with self.inputs(self.manager, self.frank) as context:
            ok_(context.active('can drink') is False)
            ok_(context.active('can drink', self.larry) is True)

        with self.inputs(self.manager, self.larry) as context:
            ok_(context.active('can drink') is True)
            ok_(context.active('can drink', self.frank, exclusive=True) is False)

    def test_switches_with_multiple_inputs(self):

        with self.inputs(self.manager, self.larry, self.jeff) as context:
            ok_(context.active('can drink') is True)
            ok_(context.active('can drink in europe') is True)
            ok_(context.active('SF resident') is True)
            ok_(context.active('teenager') is False)
            ok_(context.active('10 percent') is False)
            ok_(context.active('Upper 50 percent') is True)

        with self.inputs(self.manager, self.frank, self.jeff) as context:
            ok_(context.active('can drink') is True)
            ok_(context.active('can drink in europe') is True)
            ok_(context.active('SF resident') is True)
            ok_(context.active('teenager') is False)
            ok_(context.active('10 percent') is False)
            ok_(context.active('Upper 50 percent') is True)

    def test_switches_can_concent_top_parent_switch(self):
        with self.inputs(self.manager, self.jeff) as context:
            ok_(context.active('can drink') is True)
            ok_(context.active('can drink in europe') is True)
            ok_(context.active('SF resident') is True)
            ok_(context.active('can drink:wine') is True)
        with self.inputs(self.manager, self.timmy) as context:
            ok_(context.active('can drink') is False)
            ok_(context.active('can drink in europe') is True)
            ok_(context.active('SF resident') is True)
            ok_(context.active('can drink:wine') is False)

    def test_changing_parent_is_reflected_in_child_switch(self):
        with self.inputs(self.manager, self.jeff) as context:
            assert self.manager['can drink'].children
            ok_(context.active('can drink:wine') is True)

            parent = self.manager['can drink']
            parent.state = Switch.states.DISABLED
            parent.save()

            assert self.manager['can drink'].children
            ok_(context.active('can drink:wine') is False)

    def test_switches_can_be_deregistered_and_then_autocreated(self):
        with self.inputs(self.manager, self.jeff) as context:
            ok_(context.active('can drink') is True)

            context.manager.unregister('can drink')

            assert_raises(ValueError, context.manager.active, 'can drink')

            context.manager.autocreate = True
            ok_(context.active('can drink') is False)

    def test_can_register_signals_and_get_notified(self):
        signals.switch_registered.connect(self.callback.switch_added)
        signals.switch_unregistered.connect(self.callback.switch_removed)
        signals.switch_updated.connect(self.callback.switch_updated)

        eq_(self.callback.register_calls, [])
        eq_(self.callback.unregister_calls, [])
        eq_(self.callback.update_calls, [])

        switch = Switch('foo')

        self.manager.register(switch)
        eq_(self.callback.register_calls, [switch])

        self.manager.unregister(switch.name)
        eq_(self.callback.unregister_calls, [switch])

        self.manager.register(switch)
        eq_(self.callback.register_calls, [switch, switch])

        switch.state = Switch.states.GLOBAL
        self.manager.update(switch)

        change = self.callback.update_calls[0]
        eq_(change[0], switch)
        changes = change[1]
        eq_(changes['state'], dict(current=Switch.states.GLOBAL, previous=Switch.states.DISABLED))

    def test_namespaes_keep_switches_isloated(self):
        germany = self.manager.namespaced('germany')
        usa = self.manager.namespaced('usa')

        self.add_switch('booze', condition=self.age_21_plus, manager=usa)
        self.add_switch('booze', condition=self.age_not_under_18, manager=germany)

        eq_(len(germany.switches), 1)
        eq_(len(usa.switches), 1)

        eq_(usa.switches[0].conditions, [self.age_21_plus])
        eq_(germany.switches[0].conditions, [self.age_not_under_18])

        with self.inputs(usa, self.jeff) as context:
            ok_(context.active('booze') is True)

        with self.inputs(usa, self.jeff, self.timmy) as context:
            ok_(context.active('booze') is True)  # Jeff is 21, so he counts
            ok_(context.active('booze', self.timmy, exclusive=True) is False)  # Timmy is 10

        with self.inputs(usa, self.timmy) as context:
            ok_(context.active('booze') is False)

        with self.inputs(usa, self.timmy, self.steve) as context:
            ok_(context.active('booze') is False)

        with self.inputs(germany, self.timmy) as context:
            ok_(context.active('booze') is False)  # 10 is still too young

        with self.inputs(germany, self.steve) as context:
            ok_(context.active('booze') is True)  # 19 is old enough!

        with self.inputs(germany, self.timmy, self.steve) as context:
            ok_(context.active('booze') is True)  # Cause steve is 19

        with self.inputs(germany, self.jeff, self.timmy) as context:
            ok_(context.active('booze') is True)  # Cause jeff is 21

        with self.inputs(germany, self.jeff) as context:
            ok_(context.active('booze', self.timmy, exclusive=True) is False)  # exclusive timmy is 10

    def test_namespace_switches_not_shared_with_parent(self):
        base = self.manager
        daughter = self.manager.namespaced('daughter')
        son = self.manager.namespaced('son')

        ok_(base.switches is not daughter.switches)
        ok_(base.switches is not son.switches)
        ok_(daughter.switches is not son.switches)

        daughter_switch = self.add_switch('daughter only', manager=daughter)
        son_switch = self.add_switch('son only', manager=son)

        eq_(daughter.switches, [daughter_switch])
        eq_(son.switches, [son_switch])

        ok_(daughter_switch not in base.switches)
        ok_(son_switch not in base.switches)

    def test_retrieved_switches_can_be_updated(self):
        switch = Switch('foo')
        self.manager.register(switch)

        self.assertEquals(self.manager.switch('foo').name, 'foo')

        switch.state = Switch.states.GLOBAL
        switch.save()

        self.assertEquals(
            self.manager.switch('foo').state,
            Switch.states.GLOBAL
        )

    def test_concent_with_different_arguments(self):
        # Test that a parent switch with a different argument type from the
        # child works.
        with self.inputs(self.manager, self.jeff, 42) as context:
            ok_(context.active('can drink:answer to life') is True)
        with self.inputs(self.manager, self.timmy, 42) as context:
            ok_(context.active('can drink:answer to life') is False)

        with self.inputs(self.manager, self.jeff, 77) as context:
            ok_(context.active('can drink:answer to life') is False)
        with self.inputs(self.manager, self.timmy, 77) as context:
            ok_(context.active('can drink:answer to life') is False)


class TestIntegrationWithRedis(TestIntegration):

    @fixture
    def redis(self):
        return Redis(db=15)

    @after
    def flush_redis(self):
        self.redis.flushdb()

    @fixture
    def manager(self):
        return Manager(storage=RedisDict('gutter-tests', self.redis))

    def test_parent_switch_pickle_input(self):
        import pickle

        # Passing in module `pickle` as unpicklable input.
        evil = User(deterministicstring('evil'), pickle)
        self.manager.input(evil)

        self.manager.autocreate = True

        try:
            self.manager.active('new:switch')
        except pickle.PicklingError, e:
            self.fail('Encountered pickling error: "%s"' % e)

########NEW FILE########
__FILENAME__ = test_middleware
import unittest2
from nose.tools import *
from gutter.client.wsgi import EnabledSwitchesMiddleware, signals
from gutter.client.singleton import gutter as singleton_gutter
import mock
import threading
import time

from werkzeug.test import Client

from exam.decorators import fixture, after
from exam.cases import Exam


class BaseTest(Exam, unittest2.TestCase):

    SWITCH_HEADER_NAME = 'X-Gutter-Switch'

    @fixture
    def switch_active_signal_args(self):
        return []

    def signaling_wsgi_app(self, environ, start_response):
        start_response('200 OK', [('Content-Type', 'text/plain')])
        for args in self.switch_active_signal_args:
            signals.switch_active.call(*args)

        yield 'Hello World\n'

    @after
    def reset_signal(self):
        signals.switch_active.reset()

    @fixture
    def middleware_app(self):
        return EnabledSwitchesMiddleware(self.signaling_wsgi_app)

    @fixture
    def client(self):
        return Client(self.middleware_app)

    def start_response(self, status, headers):
        return mock.Mock()

    def build_switch(self, name='switch'):
        switch = mock.Mock(name='switch-%s' % name)
        switch.name = name
        return switch


class TestInterface(BaseTest):

    def test_it_is_constructed_with_an_application(self):
        ware = EnabledSwitchesMiddleware('app')
        ware.application = 'app'

    def test_can_be_constructed_with_a_gutter_instance(self):
        ware = EnabledSwitchesMiddleware('app', 'gutter')
        ware.gutter = 'gutter'

    def test_uses_gutter_singleton_if_constructed_with_no_gutter(self):
        ware = EnabledSwitchesMiddleware('app')
        eq_(ware.gutter, singleton_gutter)

    def test_is_callable_with_environ_and_start_response(self):
        self.middleware_app('environ', self.start_response)

    def test_calls_app_with_same_environ(self):
        self.middleware_app.application = mock.Mock()

        for chunk in self.middleware_app('environ', self.start_response):
            yield

        call_args = self.middleware_app.application.call_args
        eq_(call_args[0][0], 'environ')


class TestSwitchTracking(BaseTest):

    @fixture
    def switch_active_signal_args(self):
        return [
            (self.build_switch('switch'), 'inpt'),
            (self.build_switch('switch2'), 'inpt2')
        ]

    def call_and_get_headers(self):
        start_response = mock.Mock()
        self.middleware_app('environ', start_response)
        return dict(start_response.call_args[0][1])

    @fixture
    def gutter_header(self):
        return self.call_and_get_headers()[self.SWITCH_HEADER_NAME]

    def test_calls_start_response_with_x_gutter_switches_header(self):
        ok_(self.SWITCH_HEADER_NAME in self.call_and_get_headers())

    def test_adds_comma_separated_list_of_switches_to_x_gutter_header(self):
        eq_(self.gutter_header, 'active=switch,switch2')

    def test_returns_empty_active_list_when_no_switches_are_applied(self):
        self.switch_active_signal_args = []
        eq_(self.gutter_header, 'active=')

    def test_does_not_stop_other_global_switch_active_signals(self):
        global_called = []

        def update_called(switch, inpt):
            global_called.append(switch)

        signals.switch_active.connect(update_called)

        self.call_and_get_headers()
        self.call_and_get_headers()

        ok_(len(global_called) is 4)


class ConcurrencyTest(BaseTest):

    def signaling_wsgi_app(self, environ, start_response):
        time.sleep(0.01)
        return super(ConcurrencyTest, self).signaling_wsgi_app(environ, start_response)

    @fixture
    def switch_active_signal_args(self):
        return [
            (self.build_switch('switch_a'), 'inpt'),
            (self.build_switch('switch_b'), 'inpt2')
        ]

    def test_signals_do_not_leak_between_threads(self):
        switch_headers = []

        def run_app():
            body, status, headers = self.client.get('/')
            switch_headers.append(dict(headers)[self.SWITCH_HEADER_NAME])

        threads = [threading.Thread(target=run_app) for i in range(2)]

        [thread.start() for thread in threads]
        [thread.join() for thread in threads]

        eq_(switch_headers, ['active=switch_a,switch_b', 'active=switch_a,switch_b'])

########NEW FILE########
__FILENAME__ = test_models
import unittest2
import threading
import itertools

from nose.tools import *
from gutter.client.arguments import Container as BaseArgument
from gutter.client import arguments
from gutter.client.models import Switch, Manager, Condition
from durabledict import MemoryDict
from durabledict.base import DurableDict
from gutter.client import signals
import mock

from exam.decorators import fixture, before
from exam.cases import Exam



class EncodingDict(DurableDict):
    __last_updated = 0

    def last_updated(self):
        return self.__last_updated


def unbound_method():
    pass


class Argument(object):
    def bar(self):
        pass


class MOLArgument(BaseArgument):
    applies = True
    foo = arguments.Value(lambda self: 42)


class TestSwitch(unittest2.TestCase):

    possible_properties = [
        ('state', (Switch.states.DISABLED, Switch.states.SELECTIVE)),
        ('compounded', (True, False)),
        ('concent', (True, False))
    ]

    def test_legacy_unpickle(self):
        d = EncodingDict()

        parent = Switch('a')
        switch = Switch('a:b')

        children = [
            Switch('a:b:c'),
            Switch('a:b:d'),
        ]

        [setattr(child, 'parent', switch) for child in children]

        switch.children = children
        switch.parent = parent

        decoded_switch = d._decode(d._encode(switch))
        self.assertEquals(decoded_switch.name, switch.name)
        self.assertEquals(decoded_switch.parent, switch.parent.name)
        self.assertListEqual([child.name for child in children], decoded_switch.children)


    def test_switch_name_is_immutable(self):
        switch = Switch('foo')
        with self.assertRaises(AttributeError):
            switch.name = 'bar'

    def test_switch_has_state_constants(self):
        self.assertTrue(Switch.states.DISABLED)
        self.assertTrue(Switch.states.SELECTIVE)
        self.assertTrue(Switch.states.GLOBAL)

    def test_no_switch_state_is_equal_to_another(self):
        states = (Switch.states.DISABLED, Switch.states.SELECTIVE,
                  Switch.states.GLOBAL)
        eq_(list(states), list(set(states)))

    def test_switch_constructs_with_a_name_attribute(self):
        eq_(Switch('foo').name, 'foo')

    def test_switch_has_label(self):
        ok_(Switch('foo').label is None)

    def test_switch_can_be_constructed_with_a_label(self):
        eq_(Switch('foo', label='A label').label, 'A label')

    def test_switch_has_description(self):
        ok_(Switch('foo').description is None)

    def test_switch_can_be_constructed_with_a_description(self):
        eq_(Switch('foo', description='A description').description, 'A description')

    def test_switch_strs_the_name_argument(self):
        eq_(Switch(name=12345).name, '12345')

    def test_switch_state_defaults_to_disabled(self):
        eq_(Switch('foo').state, Switch.states.DISABLED)

    def test_switch_state_can_be_changed(self):
        switch = Switch('foo')
        old_state = switch.state

        switch.state = Switch.states.GLOBAL
        eq_(switch.state, Switch.states.GLOBAL)
        ok_(old_state is not switch.state)

    def test_switch_compounded_defaults_to_false(self):
        eq_(Switch('foo').compounded, False)

    def test_swtich_can_be_constructed_with_a_state(self):
        switch = Switch(name='foo', state=Switch.states.GLOBAL)
        eq_(switch.state, Switch.states.GLOBAL)

    def test_swtich_can_be_constructed_with_a_compounded_val(self):
        switch = Switch(name='foo', compounded=True)
        eq_(switch.compounded, True)

    def test_conditions_defaults_to_an_empty_list(self):
        eq_(Switch('foo').conditions, [])

    def test_condtions_can_be_added_and_removed(self):
        switch = Switch('foo')
        condition = lambda: False

        ok_(condition not in switch.conditions)

        switch.conditions.append(condition)
        ok_(condition in switch.conditions)

        switch.conditions.remove(condition)
        ok_(condition not in switch.conditions)

    def test_parent_property_defaults_to_none(self):
        eq_(Switch('foo').parent, None)

    def test_can_be_constructed_with_parent(self):
        eq_(Switch('foo', parent='dog').parent, 'dog')

    def test_concent_defaults_to_true(self):
        eq_(Switch('foo').concent, True)

    def test_can_be_constructed_with_concent(self):
        eq_(Switch('foo', concent=False).concent, False)

    def test_children_defaults_to_an_empty_list(self):
        eq_(Switch('foo').children, [])

    def test_switch_manager_defaults_to_none(self):
        eq_(Switch('foo').manager, None)

    def test_switch_can_be_constructed_witn_a_manager(self):
        eq_(Switch('foo', manager='manager').manager, 'manager')

    @mock.patch('gutter.client.signals.switch_checked')
    def test_switch_enabed_for_calls_switch_checked_signal(self, signal):
        switch = Switch('foo', manager='manager')
        switch.enabled_for(True)
        signal.call.assert_called_once_with(switch)

    @mock.patch('gutter.client.signals.switch_active')
    def test_switch_enabed_for_calls_switch_active_signal_when_enabled(self, signal):
        switch = Switch('foo', manager='manager', state=Switch.states.GLOBAL)
        ok_(switch.enabled_for('causing input'))
        signal.call.assert_called_once_with(switch, 'causing input')

    @mock.patch('gutter.client.signals.switch_active')
    def test_switch_enabed_for_skips_switch_active_signal_when_not_enabled(self, signal):
        switch = Switch('foo', manager='manager', state=Switch.states.DISABLED)
        eq_(switch.enabled_for('causing input'), False)
        eq_(signal.call.called, False)

    def test_switches_are_equal_if_they_have_the_same_properties(self):
        a = Switch('a') # must init with the same name as name is immutable
        b = Switch('a')

        for prop, (a_value, b_value) in self.possible_properties:
            setattr(a, prop, a_value)
            setattr(b, prop, b_value)
            self.assertNotEqual(a, b, "expected %s to not be equals" % prop)

            setattr(b, prop, a_value)
            eq_(a, b, "expected %s to be equal" % prop)

    def test_switches_are_still_equal_with_different_managers(self):
        a = Switch('a')
        b = Switch('a')

        eq_(a, b)

        a.manager = 'foo'
        b.manager = 'bar'

        eq_(a, b)


class TestSwitchChanges(unittest2.TestCase):

    @fixture
    def switch(self):
        return Switch('foo')

    def changes_dict(self, previous, current):
        return dict(previous=previous, current=current)

    def test_switch_is_not_changed_by_default(self):
        ok_(Switch('foo').changed is False)

    def test_switch_is_changed_if_property_changes(self):
        ok_(self.switch.changed is False)
        self.switch.state = 'another name'
        ok_(self.switch.changed is True)

    def test_switch_reset_causes_switch_to_reset_change_tracking(self):
        self.switch.state = 'another name'
        ok_(self.switch.changed is True)
        self.switch.reset()
        ok_(self.switch.changed is False)

    def test_switch_changes_returns_changes(self):
        eq_(self.switch.changes, {})

        self.switch.state = 'new name'
        eq_(
            self.switch.changes,
            dict(state=self.changes_dict(1, 'new name'))
        )

        self.switch.concent = False
        eq_(self.switch.changes,
            dict(
                state=self.changes_dict(1, 'new name'),
                concent=self.changes_dict(True, False)
            )
        )


class TestCondition(unittest2.TestCase):

    def argument_dict(name):
        return dict(
            module='module%s' % name,
            klass='klass%s' % name,
            func='func%s' % name
        )

    possible_properties = [
        ('argument_dict', (argument_dict('1'), argument_dict('2'))),
        ('operator', ('o1', 'o2')),
        ('negative', (False, True))
    ]

    @fixture
    def operator(self):
        m = mock.Mock(name='operator')
        m.applies_to.return_value = True
        return m

    @fixture
    def condition(self):
        return Condition(MOLArgument, 'foo', self.operator)

    @fixture
    def input(self):
        return mock.Mock(name='input')

    def test_returns_results_from_calling_operator_with_argument_value(self):
        self.condition.call(self.input)
        self.operator.applies_to.assert_called_once_with(42)

    def test_condition_can_be_negated(self):
        eq_(self.condition.call(self.input), True)
        self.condition.negative = True
        eq_(self.condition.call(self.input), False)

    def test_can_be_negated_via_init_argument(self):
        condition = Condition(MOLArgument, 'foo', self.operator)
        eq_(condition.call(self.input), True)
        condition = Condition(MOLArgument, 'foo', self.operator, negative=True)
        eq_(condition.call(self.input), False)

    def test_if_apply_explodes_it_returns_false(self):
        self.operator.applies_to.side_effect = Exception
        eq_(self.condition.call(self.input), False)

    def test_returns_false_if_argument_does_not_apply_to_input(self):
        self.condition.argument = mock.Mock()
        eq_(self.condition.call(self.input), True)
        self.condition.argument.return_value.applies = False
        eq_(self.condition.call(self.input), False)

    def test_if_input_is_NONE_it_returns_false(self):
        eq_(self.condition.call(Manager.NONE_INPUT), False)

    @mock.patch('gutter.client.signals.condition_apply_error')
    def test_if_apply_explodes_it_signals_condition_apply_error(self, signal):
        error = Exception('boom!')
        inpt = self.input

        self.operator.applies_to.side_effect = error
        self.condition.call(inpt)

        signal.call.assert_called_once_with(self.condition, inpt, error)

    def test_str_returns_argument_and_str_of_operator(self):
        def local_str(self):
            return 'str of operator'

        self.operator.__str__ = local_str
        eq_(str(self.condition), "MOLArgument.foo str of operator")

    def test_equals_if_has_the_same_properties(self):
        a = Condition(Argument, 'bar', bool)
        b = Condition(Argument, 'bar', bool)

        for prop, (a_val, b_val) in self.possible_properties:
            setattr(a, prop, a_val)
            setattr(b, prop, b_val)

            self.assertNotEqual(a, b)

            setattr(b, prop, a_val)
            eq_(a, b)


class SwitchWithConditions(object):

    @fixture
    def switch(self):
        switch = Switch('parent:with conditions', state=Switch.states.SELECTIVE)
        switch.conditions.append(self.pessamistic_condition)
        switch.conditions.append(self.pessamistic_condition)
        return switch

    @fixture
    def parent_switch(self):
        switch = Switch('parent', state=Switch.states.DISABLED)
        return switch

    @property
    def pessamistic_condition(self):
        mck = mock.MagicMock()
        mck.call.return_value = False
        return mck


class ConcentTest(Exam, SwitchWithConditions, unittest2.TestCase):

    @fixture
    def manager(self):
        return Manager(storage=MemoryDict())

    @fixture
    def parent(self):
        p = mock.Mock()
        p.enabled_for.return_value = False
        return p

    @before
    def make_all_conditions_true(self):
        self.make_all_conditions(True)

    @before
    def register_switches(self):
        self.manager.register(self.parent_switch)
        self.manager.register(self.switch)

    def make_all_conditions(self, val):
        for cond in self.switch.conditions:
            cond.call.return_value = val

    def test_with_concent_only_enabled_if_parent_is_too(self):
        self.manager.register(self.switch)

        parent = self.manager.switch(self.switch.parent)
        eq_(parent.enabled_for('input'), False)
        eq_(self.manager.active('parent:with conditions', 'input'), False)

        parent.state = Switch.states.GLOBAL
        eq_(self.manager.active('parent:with conditions', 'input'), True)

    def test_without_concent_ignores_parents_enabled_status(self):
        self.switch.concent = False

        parent = self.manager.switch(self.switch.parent)
        eq_(parent.enabled_for('input'), False)
        eq_(self.switch.enabled_for('input'), True)

        self.make_all_conditions(False)
        eq_(self.switch.enabled_for('input'), False)


class DefaultConditionsTest(SwitchWithConditions, unittest2.TestCase):

    def test_enabled_for_is_true_if_any_conditions_are_true(self):
        ok_(self.switch.enabled_for('input') is False)
        self.switch.conditions[0].call.return_value = True
        ok_(self.switch.enabled_for('input') is True)

    def test_is_true_when_state_is_global(self):
        eq_(self.switch.enabled_for('input'), False)
        self.switch.state = Switch.states.GLOBAL
        eq_(self.switch.enabled_for('input'), True)

    def test_is_false_when_state_is_disabled(self):
        self.switch.conditions[0].call.return_value = True
        eq_(self.switch.enabled_for('input'), True)
        self.switch.state = Switch.states.DISABLED
        eq_(self.switch.enabled_for('input'), False)


class CompoundedConditionsTest(Exam, SwitchWithConditions, unittest2.TestCase):

    @before
    def make_switch_compounded(self):
        self.switch.compounded = True

    def test_enabled_if_all_conditions_are_true(self):
        ok_(self.switch.enabled_for('input') is False)
        self.switch.conditions[0].call.return_value = True
        ok_(self.switch.enabled_for('input') is False)
        self.switch.conditions[1].call.return_value = True
        ok_(self.switch.enabled_for('input') is True)


class ManagerTest(unittest2.TestCase):

    storage_with_existing_switches = {
        'default.existing': 'switch',
        'default.another': 'valuable switch'
    }
    expected_switches_from_storage = ['switch', 'valuable switch']
    namespace_base = []

    @fixture
    def mockstorage(self):
        return mock.MagicMock(dict)

    @fixture
    def manager(self):
        return Manager(storage=self.mockstorage)

    @fixture
    def switch(self):
        switch = mock.Mock(spec=Switch)
        switch.changes = {}
        switch.parent = None
        switch.name = 'foo'
        switch.manager = None
        return switch

    def namespaced(self, *names):
        parts = itertools.chain(self.manager.namespace, names)
        return self.manager.namespace_separator.join(parts)

    def test_autocreate_defaults_to_false(self):
        eq_(Manager(storage=dict()).autocreate, False)

    def test_autocreate_can_be_passed_to_init(self):
        eq_(Manager(storage=dict(), autocreate=True).autocreate, True)

    def test_namespace_defaults_to_default(self):
        eq_(Manager(storage=dict()).namespace, ['default'])

    def test_namespace_can_be_set_on_construction(self):
        eq_(Manager(storage=dict(), namespace='foo').namespace, ['foo'])

    def test_register_adds_switch_to_storge_keyed_by_its_name(self):
        self.manager.register(self.switch)
        self.mockstorage.__setitem__.assert_called_once_with(
            self.namespaced(self.switch.name),
            self.switch
        )

    def test_register_adds_self_as_manager_to_switch(self):
        ok_(self.switch.manager is not self.manager)
        self.manager.register(self.switch)
        ok_(self.switch.manager is self.manager)

    def test_uses_switches_from_storage_on_itialization(self):
        self.manager.storage = self.storage_with_existing_switches
        self.assertItemsEqual(
            self.manager.switches,
            self.expected_switches_from_storage
        )

    def test_update_tells_manager_to_register_with_switch_updated_signal(self):
        self.manager.register = mock.Mock()
        self.manager.update(self.switch)
        self.manager.register.assert_called_once_with(self.switch, signal=signals.switch_updated)

    @mock.patch('gutter.client.signals.switch_updated')
    def test_update_calls_the_switch_updateed_signal(self, signal):
        self.manager.update(self.switch)
        signal.call.assert_call_once()

    def test_manager_resets_switch_dirty_tracking(self):
        self.manager.update(self.switch)
        self.switch.reset.assert_called_once_with()

    def test_manager_properties_not_shared_between_threads(self):
        manager = Manager(storage=self.mockstorage, autocreate=True)

        def change_autocreate_to_false():
            manager.autocreate = False

        threading.Thread(target=change_autocreate_to_false).start()
        eq_(manager.autocreate, True)

    def test_can_be_constructed_with_inputs(self):
        eq_(
            Manager(storage=self.mockstorage, inputs=[3]).inputs,
            [3]
        )

    def test_namespaced_returns_new_manager_only_different_by_namespace(self):
        parent = self.manager
        child = self.manager.namespaced('ns')
        grandchild = child.namespaced('other')

        self.assertNotEqual(parent.namespace, child.namespace)
        self.assertNotEqual(child.namespace, grandchild.namespace)

        child_ns_list = list(itertools.chain(self.namespace_base, ['ns']))
        grandchild_ns_list = list(
            itertools.chain(self.namespace_base, ['ns', 'other'])
        )

        eq_(child.namespace, child_ns_list)
        eq_(grandchild.namespace, grandchild_ns_list)

        properties = (
            'storage',
            'autocreate',
            'inputs',
            'switch_class'
        )

        for decendent_manager in (child, grandchild):
            for prop in properties:
                eq_(getattr(decendent_manager, prop), getattr(parent, prop))

    def test_getitem_proxies_to_storage_getitem(self):
        eq_(
            self.manager['foo'],
            self.manager.storage.__getitem__.return_value
        )
        self.manager.storage.__getitem__.assert_called_once_with(
            self.namespaced('foo')
        )


class NamespacedManagertest(ManagerTest):

    storage_with_existing_switches = {
        'a.b.brother': 'brother switch',
        'a.b.sister': 'sister switch',
        'a.b.c.grandchild': 'grandchild switch',
        'a.c.cousin': 'cousin switch',
    }
    expected_switches_from_storage = [
        'brother switch',
        'sister switch',
        'grandchild switch'
    ]
    namespace_base = ['a', 'b']

    @fixture
    def manager(self):
        return Manager(storage=self.mockstorage, namespace=['a', 'b'])


class ActsLikeManager(object):

    def namespaced(self, *names):
        parts = itertools.chain(self.manager.namespace, names)
        return self.manager.key_separator.join(parts)

    @fixture
    def manager(self):
        return Manager(storage=MemoryDict())

    @fixture
    def test_switch(self):
        return self.new_switch('test')

    def new_switch(self, name, parent=None):
        switch = mock.Mock(name=name)
        switch.name = name
        switch.parent = parent
        switch.children = []
        return switch

    def mock_and_register_switch(self, name, parent=None):
        switch = self.new_switch(name, parent)
        self.manager.register(switch)
        return switch

    def test_switches_list_registed_switches(self):
        eq_(self.manager.switches, [])
        self.manager.register(self.test_switch)
        eq_(self.manager.switches, [self.test_switch])

    def test_active_raises_exception_if_no_switch_found_with_name(self):
        assert_raises(ValueError, self.manager.active, 'junk')

    def test_unregister_removes_a_switch_from_storage_with_name(self):
        switch = self.mock_and_register_switch('foo')
        ok_(switch in self.manager.switches)

        self.manager.unregister(switch.name)
        ok_(switch not in self.manager.switches)

    def test_unregister_can_remove_if_given_switch_instance(self):
        switch = self.mock_and_register_switch('foo')
        ok_(switch in self.manager.switches)

        self.manager.unregister(switch)
        ok_(switch not in self.manager.switches)

    def test_register_does_not_set_parent_by_default(self):
        switch = self.mock_and_register_switch('foo')
        eq_(switch.parent, None)

    def test_register_sets_parent_on_switch_if_there_is_one(self):
        parent = self.mock_and_register_switch('movies')
        child = self.mock_and_register_switch('movies:jaws')
        eq_(child.parent, parent.name)

    def test_register_adds_self_to_parents_children(self):
        parent = self.mock_and_register_switch('movies')
        child = self.mock_and_register_switch('movies:jaws')

        eq_(parent.children, [child.name])

        sibling = self.mock_and_register_switch('movies:jaws')

        eq_(parent.children, [child.name, sibling.name])

    def test_register_raises_value_error_for_blank_name(self):
        with self.assertRaises(ValueError):
            self.mock_and_register_switch('')

    def test_switch_returns_switch_from_manager_with_name(self):
        switch = self.mock_and_register_switch('foo')
        eq_(switch, self.manager.switch('foo'))

    def test_switch_returns_switch_with_manager_assigned(self):
        switch = self.new_switch('foo')
        self.manager.register(switch)
        switch.manager = None
        eq_(self.manager, self.manager.switch('foo').manager)

    def test_swich_raises_valueerror_if_no_switch_by_name(self):
        assert_raises(ValueError, self.manager.switch, 'junk')

    def test_unregister_removes_all_child_switches_too(self):
        grandparent = self.mock_and_register_switch('movies')
        parent = self.mock_and_register_switch('movies:star_wars')
        child1 = self.mock_and_register_switch('movies:star_wars:a_new_hope')
        child2 = self.mock_and_register_switch('movies:star_wars:return_of_the_jedi')
        great_uncle = self.mock_and_register_switch('books')

        ok_(grandparent in self.manager.switches)
        ok_(parent in self.manager.switches)
        ok_(child1 in self.manager.switches)
        ok_(child2 in self.manager.switches)
        ok_(great_uncle in self.manager.switches)

        self.manager.unregister(grandparent.name)

        ok_(grandparent not in self.manager.switches)
        ok_(parent not in self.manager.switches)
        ok_(child1 not in self.manager.switches)
        ok_(child2 not in self.manager.switches)
        ok_(great_uncle in self.manager.switches)

    @mock.patch('gutter.client.signals.switch_unregistered')
    def test_register_signals_switch_registered_with_switch(self, signal):
        switch = self.mock_and_register_switch('foo')
        self.manager.unregister(switch.name)
        signal.call.assert_called_once_with(switch)


class EmptyManagerInstanceTest(ActsLikeManager, unittest2.TestCase):

    def test_input_accepts_variable_input_args(self):
        eq_(self.manager.inputs, [])
        self.manager.input('input1', 'input2')
        eq_(self.manager.inputs, ['input1', 'input2'])

    def test_flush_clears_all_inputs(self):
        self.manager.input('input1', 'input2')
        ok_(len(self.manager.inputs) is 2)
        self.manager.flush()
        ok_(len(self.manager.inputs) is 0)

    def test_can_pass_extra_inputs_to_check_enabled_for_on(self):
        switch = self.mock_and_register_switch('foo')
        additional_input = mock.Mock()
        self.manager.active('foo', additional_input)
        switch.enabled_for.assert_called_once_with(additional_input)

    def test_checks_against_NONE_input_if_no_inputs(self):
        switch = self.mock_and_register_switch('global')
        eq_(self.manager.inputs, [])

        self.manager.active('global')

        switch.enabled_for.assert_called_once_with(Manager.NONE_INPUT)


class NamespacedEmptyManagerInstanceTest(EmptyManagerInstanceTest):

    @fixture
    def manager(self):
        return Manager(storage=MemoryDict(), namespace=['a', 'b'])


class ManagerWithInputTest(Exam, ActsLikeManager, unittest2.TestCase):

    def build_and_register_switch(self, name, enabled_for=False):
        switch = Switch(name)
        switch.enabled_for = mock.Mock(return_value=enabled_for)
        self.manager.register(switch)
        return switch

    @before
    def add_to_inputs(self):
        self.manager.input('input 1', 'input 2')

    def test_returns_boolean_if_named_switch_is_enabled_for_any_input(self):
        self.build_and_register_switch('disabled', enabled_for=False)
        eq_(self.manager.active('disabled'), False)

        self.build_and_register_switch('enabled', enabled_for=True)
        eq_(self.manager.active('disabled'), False)

    def test_raises_exception_if_invalid_switch_name_created(self):
        self.assertRaisesRegexp(ValueError, 'switch named', self.manager.active, 'junk')

    def test_autocreates_disabled_switch_when_autocreate_is_true(self):
        eq_(self.manager.switches, [])
        assert_raises(ValueError, self.manager.active, 'junk')

        self.manager.autocreate = True

        eq_(self.manager.active('junk'), False)
        ok_(len(self.manager.switches) is 1)
        ok_(self.manager.switches[0].state, Switch.states.DISABLED)

    def test_active_extra_inputs_considered_in_check_with_global_inputs(self):
        switch = self.build_and_register_switch('foo')
        self.manager.active('foo', 'input 3')
        calls = [mock.call(c) for c in ('input 1', 'input 2', 'input 3')]
        switch.enabled_for.assert_has_calls(calls)

    def test_active_with_extra_inputs_only_considers_extra_when_only_kw_arg_is_used(self):
        switch = self.build_and_register_switch('foo')
        self.manager.active('foo', 'input 3', exclusive=True)
        switch.enabled_for.assert_called_once_with('input 3')


class NamespacedManagerWithInputTest(ManagerWithInputTest):

    @fixture
    def manager(self):
        return Manager(storage=MemoryDict(), namespace=['a', 'b'])

########NEW FILE########
__FILENAME__ = test_operators
import unittest2
from nose.tools import *

from gutter.client.operators import OperatorInitError
from gutter.client.operators.comparable import *
from gutter.client.operators.identity import *
from gutter.client.operators.misc import *

from exam.decorators import fixture


class BaseOperator(object):

    def test_has_name(self):
        ok_(self.operator.name)

    def test_has_preposition(self):
        ok_(self.operator.preposition)

    def test_has_applies_to_method(self):
        ok_(self.operator.applies_to)

    def test_has_variables_property(self):
        ok_(hasattr(self.property_class, 'variables'))

    def test_has_arguments_property(self):
        ok_(hasattr(self.property_class, 'arguments'))

    def test_instances_with_identical_properties_are_equals(self):
        eq_(self.make_operator(), self.make_operator())

    @fixture
    def operator(self):
        return self.make_operator()

    @fixture
    def str(self):
        return str(self.operator)

    @fixture
    def property_class(self):
        return type(self.operator)


class TestTruthyCondition(BaseOperator, unittest2.TestCase):

    def make_operator(self):
        return Truthy()

    def test_applies_to_if_argument_is_truthy(self):
        ok_(self.operator.applies_to(True))
        ok_(self.operator.applies_to("hello"))
        ok_(self.operator.applies_to(False) is False)
        ok_(self.operator.applies_to("") is False)

    def test_str_says_is_truthy(self):
        eq_(self.str, 'true')

    def test_variables_is_empty_list(self):
        eq_(self.operator.variables, {})

    def test_arguments_is_empty_list(self):
        eq_(self.operator.arguments, ())


class TestEqualsCondition(BaseOperator, unittest2.TestCase):

    def make_operator(self):
        return Equals(value='Fred')

    def test_applies_to_if_argument_is_equal_to_value(self):
        ok_(self.operator.applies_to('Fred'))
        ok_(self.operator.applies_to('Steve') is False)
        ok_(self.operator.applies_to('') is False)
        ok_(self.operator.applies_to(True) is False)

    @raises(OperatorInitError)
    def test_raises_operator_init_error_if_not_provided_value(self):
        Equals()

    def test_str_says_is_equal_to_condition(self):
        eq_(self.str, 'equal to "Fred"')

    def test_variables_is_just_a_single_value(self):
        eq_(self.operator.variables, dict(value='Fred'))

    def test_arguments_is_value(self):
        eq_(self.operator.arguments, ('value',))


class TestBetweenCondition(BaseOperator, unittest2.TestCase):

    def make_operator(self, lower=1, higher=100):
        return Between(lower_limit=lower, upper_limit=higher)

    def test_applies_to_if_between_lower_and_upper_bound(self):
        ok_(self.operator.applies_to(0) is False)
        ok_(self.operator.applies_to(1) is False)
        ok_(self.operator.applies_to(2))
        ok_(self.operator.applies_to(99))
        ok_(self.operator.applies_to(100) is False)
        ok_(self.operator.applies_to('steve') is False)

    def test_applies_to_works_with_any_comparable(self):
        animals = Between(lower_limit='cobra', upper_limit='orangatang')
        ok_(animals.applies_to('dog'))
        ok_(animals.applies_to('elephant'))
        ok_(animals.applies_to('llama'))
        ok_(animals.applies_to('aardvark') is False)
        ok_(animals.applies_to('whale') is False)
        ok_(animals.applies_to('zebra') is False)

    def test_str_says_between_values(self):
        eq_(self.str, 'between "1" and "100"')

    def test_variables_is_just_a_lower_and_higher(self):
        eq_(self.operator.variables, dict(lower_limit=1, upper_limit=100))


class TestLessThanCondition(BaseOperator, unittest2.TestCase):

    def make_operator(self, upper=500):
        return LessThan(upper_limit=upper)

    def test_applies_to_if_value_less_than_argument(self):
        ok_(self.operator.applies_to(float("-inf")))
        ok_(self.operator.applies_to(-50000))
        ok_(self.operator.applies_to(-1))
        ok_(self.operator.applies_to(0))
        ok_(self.operator.applies_to(499))
        ok_(self.operator.applies_to(500) is False)
        ok_(self.operator.applies_to(10000) is False)
        ok_(self.operator.applies_to(float("inf")) is False)

    def test_works_with_any_comparable(self):
        ok_(LessThan(upper_limit='giraffe').applies_to('aardvark'))
        ok_(LessThan(upper_limit='giraffe').applies_to('zebra') is False)
        ok_(LessThan(upper_limit=56.7).applies_to(56))
        ok_(LessThan(upper_limit=56.7).applies_to(56.0))
        ok_(LessThan(upper_limit=56.7).applies_to(57.0) is False)
        ok_(LessThan(upper_limit=56.7).applies_to(56.71) is False)

    def test_str_says_less_than_value(self):
        eq_(self.str, 'less than "500"')

    def test_variables_is_upper_limit(self):
        eq_(self.operator.variables, dict(upper_limit=500))


class TestLessThanOrEqualToOperator(BaseOperator):

    def make_operator(self, upper=500):
        return LessThanOrEqualTo(upper_limit=upper)

    def test_applies_if_value_is_less_than_or_equal_to_argument(self):
        ok_(self.operator.applies_to(float("-inf")))
        ok_(self.operator.applies_to(-50000))
        ok_(self.operator.applies_to(-1))
        ok_(self.operator.applies_to(0))
        ok_(self.operator.applies_to(499))
        ok_(self.operator.applies_to(500) is True)
        ok_(self.operator.applies_to(10000) is False)
        ok_(self.operator.applies_to(float("inf")) is False)

    def test_works_with_any_comparable(self):
        ok_(LessThanOrEqualTo(upper_limit='giraffe').applies_to('aardvark'))
        ok_(LessThanOrEqualTo(upper_limit='giraffe').applies_to('zebra') is False)
        ok_(LessThanOrEqualTo(upper_limit='giraffe').applies_to('giraffe') is True)
        ok_(LessThanOrEqualTo(upper_limit=56.7).applies_to(56))
        ok_(LessThanOrEqualTo(upper_limit=56.7).applies_to(56.0))
        ok_(LessThanOrEqualTo(upper_limit=56.7).applies_to(56.7))
        ok_(LessThanOrEqualTo(upper_limit=56.7).applies_to(57.0) is False)
        ok_(LessThanOrEqualTo(upper_limit=56.7).applies_to(56.71) is False)

    def test_str_says_less_than_or_equal_to_value(self):
        eq_(self.str, 'less than or equal to "500"')

    def test_variables_is_upper_limit(self):
        eq_(self.operator.variables, dict(upper_limit=500))


class TestMoreThanOperator(BaseOperator, unittest2.TestCase):

    def make_operator(self, lower=10):
        return MoreThan(lower_limit=lower)

    def test_applies_to_if_value_more_than_argument(self):
        ok_(self.operator.applies_to(float("inf")))
        ok_(self.operator.applies_to(10000))
        ok_(self.operator.applies_to(11))
        ok_(self.operator.applies_to(10) is False)
        ok_(self.operator.applies_to(0) is False)
        ok_(self.operator.applies_to(-100) is False)
        ok_(self.operator.applies_to(float('-inf')) is False)

    def test_works_with_any_comparable(self):
        ok_(MoreThan(lower_limit='giraffe').applies_to('zebra'))
        ok_(MoreThan(lower_limit='giraffe').applies_to('aardvark') is False)
        ok_(MoreThan(lower_limit=56.7).applies_to(57))
        ok_(MoreThan(lower_limit=56.7).applies_to(57.0))
        ok_(MoreThan(lower_limit=56.7).applies_to(56.0) is False)
        ok_(MoreThan(lower_limit=56.7).applies_to(56.71))

    def test_str_says_more_than_value(self):
        eq_(self.str, 'more than "10"')

    def test_variables_is_lower_limit(self):
        eq_(self.operator.variables, dict(lower_limit=10))


class TestMoreThanOrEqualToOperator(BaseOperator, unittest2.TestCase):

    def make_operator(self, lower=10):
        return MoreThanOrEqualTo(lower_limit=lower)

    def test_applies_to_if_value_more_than_argument(self):
        ok_(self.operator.applies_to(float("inf")))
        ok_(self.operator.applies_to(10000))
        ok_(self.operator.applies_to(11))
        ok_(self.operator.applies_to(10) is True)
        ok_(self.operator.applies_to(0) is False)
        ok_(self.operator.applies_to(-100) is False)
        ok_(self.operator.applies_to(float('-inf')) is False)

    def test_works_with_any_comparable(self):
        ok_(MoreThanOrEqualTo(lower_limit='giraffe').applies_to('zebra'))
        ok_(MoreThanOrEqualTo(lower_limit='giraffe').applies_to('aardvark') is False)
        ok_(MoreThanOrEqualTo(lower_limit='giraffe').applies_to('giraffe'))
        ok_(MoreThanOrEqualTo(lower_limit=56.7).applies_to(57))
        ok_(MoreThanOrEqualTo(lower_limit=56.7).applies_to(57.0))
        ok_(MoreThanOrEqualTo(lower_limit=56.7).applies_to(56.7))
        ok_(MoreThanOrEqualTo(lower_limit=56.7).applies_to(56.0) is False)
        ok_(MoreThanOrEqualTo(lower_limit=56.7).applies_to(56.71))

    def test_str_says_more_than_or_equal_to_value(self):
        eq_(self.str, 'more than or equal to "10"')

    def test_variables_is_lower_limit(self):
        eq_(self.operator.variables, dict(lower_limit=10))


class PercentTest(BaseOperator):

    class FalseyObject(object):

        def __nonzero__(self):
            return False

    def successful_runs(self, number):
        runs = map(self.operator.applies_to, range(1000))
        return len(filter(bool, runs))

    def test_returns_false_if_argument_is_falsey(self):
        eq_(self.operator.applies_to(False), False)
        eq_(self.operator.applies_to(self.FalseyObject()), False)


class PercentageTest(PercentTest, unittest2.TestCase):

    def make_operator(self):
        return Percent(percentage=50)

    def test_applies_to_percentage_passed_in(self):
        self.assertAlmostEqual(self.successful_runs(1000), 500, delta=50)

    def test_str_says_applies_to_percentage_of_values(self):
        eq_(self.str, 'in 50.0% of values')

    def test_variables_is_percentage(self):
        eq_(self.operator.variables, dict(percentage=50))


class PercentRangeTest(PercentTest, unittest2.TestCase):

    def make_operator(self):
        return self.range_of(10, 20)

    def range_of(self, lower, upper):
        return PercentRange(lower_limit=lower, upper_limit=upper)

    def test_can_apply_to_a_certain_percent_range(self):
        self.assertAlmostEqual(self.successful_runs(1000), 100, delta=20)

    def test_percentage_range_does_not_overlap(self):
        bottom_10 = self.range_of(0, 10)
        next_10 = self.range_of(10, 20)

        for i in range(1, 500):
            bottom = bottom_10.applies_to(i)
            next = next_10.applies_to(i)
            assert_false(bottom is next is True)

    def test_str_says_applies_to_percentage_range_of_values(self):
        eq_(self.str, 'in 10.0 - 20.0% of values')

    def test_variables_is_lower_and_upper(self):
        eq_(self.operator.variables, dict(lower_limit=10, upper_limit=20))

########NEW FILE########
__FILENAME__ = test_signals
import unittest2
from nose.tools import *
from gutter.client import signals
import mock

from exam.decorators import fixture


class ActsLikeSignal(object):

    @fixture
    def callback(self):
        return mock.Mock(name="callback")

    @fixture
    def signal_with_callback(self):
        self.signal.connect(self.callback)
        return self.signal

    def test_signal_has_connect_callable(self):
        ok_(callable(self.signal.connect))

    def test_connect_raises_exceptiion_if_argument_is_not_callable(self):
        assert_raises(ValueError, self.signal.connect, True)

    def tests_callback_called_when_signal_is_called(self):
        self.signal_with_callback.call()
        self.callback.assert_called_once()

    def test_signal_passes_args_along_to_callback(self):
        self.signal_with_callback.call(1, 2.0, kw='args')
        self.callback.assert_called_once_with(1, 2.0, kw='args')


class TestSwitchRegisteredCallback(ActsLikeSignal, unittest2.TestCase):

    @fixture
    def signal(self):
        return signals.switch_registered


class TestSwitchUnregisteredCallback(ActsLikeSignal, unittest2.TestCase):

    @fixture
    def signal(self):
        return signals.switch_unregistered


class TestSwitchUpdatedCallback(ActsLikeSignal, unittest2.TestCase):

    @fixture
    def signal(self):
        return signals.switch_updated


class TestConditionApplyErrorCallback(ActsLikeSignal, unittest2.TestCase):

    @fixture
    def signal(self):
        return signals.switch_updated


class TestSwitchChecked(ActsLikeSignal, unittest2.TestCase):

    @fixture
    def signal(self):
        return signals.switch_checked


class TestSwitchActive(ActsLikeSignal, unittest2.TestCase):

    @fixture
    def signal(self):
        return signals.switch_active

########NEW FILE########
__FILENAME__ = test_singleton
import unittest2
from nose.tools import *
import mock

from gutter.client.settings import manager
import gutter.client.models

from exam.decorators import after, around
from exam.cases import Exam


class TestGutter(Exam, unittest2.TestCase):

    other_engine = dict()
    manager_defaults = dict(
        storage=manager.storage_engine,
        autocreate=manager.autocreate,
        inputs=manager.inputs
    )

    @after
    def reset_to_defaults(self):
        for key, val in self.manager_defaults.items():
            setattr(manager, key, val)

    @around
    def preserve_default_singleton(self):
        import gutter.client.singleton
        original_singleton = gutter.client.singleton.gutter
        yield
        gutter.client.singleton.gutter = original_singleton

    def test_gutter_global_is_a_switch_manager(self):
        reload(gutter.client.singleton)
        self.assertIsInstance(gutter.client.singleton.gutter,
                              gutter.client.models.Manager)

    def test_consructs_manager_with_defaults_from_settings(self):
        with mock.patch('gutter.client.models.Manager') as init:
            init.return_value = None
            reload(gutter.client.singleton)
            expected = ((), self.manager_defaults)
            eq_(init.call_args, expected)

    def test_can_change_settings_before_importing(self):
        with mock.patch('gutter.client.models.Manager') as init:
            init.return_value = None
            manager.storage_engine = self.other_engine
            manager.autocreate = True
            manager.inputs = [4]
            manager.operators = [5]
            reload(gutter.client.singleton)
            expected = (
                (),
                dict(
                    storage=self.other_engine,
                    autocreate=True,
                    inputs=[4],
                )
            )
            eq_(init.call_args, expected)

    def test_uses_default_manager_if_set(self):
        manager.default = mock.sentinel.default_manager
        reload(gutter.client.singleton)
        eq_(gutter.client.singleton.gutter, mock.sentinel.default_manager)
########NEW FILE########
__FILENAME__ = test_testutils
import unittest2
from nose.tools import *

from gutter.client.singleton import gutter
from gutter.client.testutils import switches
from gutter.client.models import Switch

from exam.decorators import around
from exam.cases import Exam


class TestDecorator(Exam, unittest2.TestCase):

    @around
    def add_and_remove_switch(self):
        gutter.register(Switch('foo'))
        yield
        gutter.flush()

    @switches(foo=True)
    def with_decorator(self):
        return gutter.active('foo')

    def without_decorator(self):
        return gutter.active('foo')

    def test_decorator_overrides_switch_setting(self):
        eq_(self.without_decorator(), False)
        eq_(self.with_decorator(), True)

    def test_context_manager_overrides_swich_setting(self):
        eq_(gutter.active('foo'), False)

        with switches(foo=True):
            eq_(gutter.active('foo'), True)

########NEW FILE########
