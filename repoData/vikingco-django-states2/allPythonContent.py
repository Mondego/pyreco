__FILENAME__ = compat
# Django >= 1.4 moves handler404, handler500, include, patterns and url from
# django.conf.urls.defaults to django.conf.urls.
try:
        from django.conf.urls import (patterns, url, include)
except ImportError:
        from django.conf.urls.defaults import (patterns, url, include)

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
"""Configuration options"""
from django.conf import settings


#: The basic configuration
base_conf = getattr(settings, 'STATES2_CONF', {})

#: The model name for the state transition logs.
#: It will be string replaced with ``%(model_name)s`` and ``%(field_name)s``.
LOG_MODEL_NAME = base_conf.get('LOG_MODEL_NAME',
                               '%(model_name)s%(field_name)sLog')

########NEW FILE########
__FILENAME__ = exceptions
# -*- coding: utf-8 -*-
"""Declared Exceptions"""


class States2Exception(Exception):
    pass


# ==========[ Transition exceptions ]==========

class TransitionException(States2Exception):
    pass


class TransitionOnUnsavedObject(TransitionException):
    def __init__(self, instance):
        TransitionException.__init__(self, "Cannot run state transition on unsaved object '%s'. "
                "Please call save() on this object first." % instance)


class PermissionDenied(TransitionException):
    def __init__(self, instance, transition, user):
        if user.is_authenticated():
            username = user.get_full_name()
        else:
            username = 'AnonymousUser'
        TransitionException.__init__(self, "Permission for executing the state '%s' has be denied to %s."
                % (transition, username))


class UnknownTransition(TransitionException):
    def __init__(self, instance, transition):
        TransitionException.__init__(self, "Unknown transition '%s' on %s" %
                    (transition, instance.__class__.__name__))


class TransitionNotFound(TransitionException):
    def __init__(self, model, from_state, to_state):
        TransitionException.__init__(self, "Transition from '%s' to '%s' on %s not found" %
                    (from_state, to_state, model.__name__))


class TransitionCannotStart(TransitionException):
    def __init__(self, instance, transition):
        TransitionException.__init__(self, "Transition '%s' on %s cannot start in the state '%s'" %
                    (transition, instance.__class__.__name__, instance.state))


class TransitionNotValidated(TransitionException):
    def __init__(self, instance, transition, validation_errors):
        TransitionException.__init__(self, "Transition '%s' on %s does not validate (%i errors)" %
                    (transition, instance.__class__.__name__, len(validation_errors)))
        self.validation_errors = validation_errors


class MachineDefinitionException(States2Exception):
    def __init__(self, machine, description):
        States2Exception.__init__(self, 'Error in state machine definition: ' + description)


class TransitionValidationError(TransitionException):
    """
    Errors yielded from StateTransition.validate.
    """
    pass


# ==========[ Other exceptions ]==========

class UnknownState(States2Exception):
    def __init__(self, state):
        States2Exception.__init__(self, 'State "%s" does not exist' % state)

########NEW FILE########
__FILENAME__ = fields
# -*- coding: utf-8 -*-
"""Fields used"""

__all__ = ('StateField',)

from django.db import models
from django.utils.functional import curry
from django_states.machine import StateMachine

from django_states.model_methods import (get_STATE_transitions,
                                   get_public_STATE_transitions,
                                   get_STATE_info, get_STATE_machine,
                                   get_STATE_display)


class StateField(models.CharField):
    """
    Add state information to a model.

    This will add extra methods to the model.

    Usage::

        status = StateField(machine=PowerState)
    """
    def __init__(self, **kwargs):
        # State machine parameter. (Fall back to default machine.
        # e.g. when South is creating an instance.)
        self._machine = kwargs.pop('machine', StateMachine)

        kwargs.setdefault('max_length', 100)
        kwargs['choices'] = None
        super(StateField, self).__init__(**kwargs)

    def contribute_to_class(self, cls, name):
        """
        Adds methods to the :class:`~django.db.models.Model`.

        The extra methods will be added for each :class:`StateField` in a
        model:

        - :meth:`~django_states.model_methods.get_STATE_transitions`
        - :meth:`~django_states.model_methods.get_public_STATE_transitions`
        - :meth:`~django_states.model_methods.get_STATE_info`
        - :meth:`~django_states.model_methods.get_STATE_machine`
        """
        super(StateField, self).contribute_to_class(cls, name)

        # Set choice options (for combo box)
        self._choices = self._machine.get_state_choices()
        self.default = self._machine.initial_state

        # do we need logging?
        if self._machine.log_transitions:
            from django_states.log import _create_state_log_model
            log_model = _create_state_log_model(cls, name, self._machine)
        else:
            log_model = None

        setattr(cls, '_%s_log_model' % name, log_model)

        # adding extra methods
        setattr(cls, 'get_%s_display' % name,
            curry(get_STATE_display, field=name, machine=self._machine))
        setattr(cls, 'get_%s_transitions' % name,
            curry(get_STATE_transitions, field=name))
        setattr(cls, 'get_public_%s_transitions' % name,
            curry(get_public_STATE_transitions, field=name))
        setattr(cls, 'get_%s_info' % name,
            curry(get_STATE_info, field=name, machine=self._machine))
        setattr(cls, 'get_%s_machine' % name,
            curry(get_STATE_machine, field=name, machine=self._machine))

        models.signals.class_prepared.connect(self.finalize, sender=cls)

    def finalize(self, sender, **kwargs):
        """
        Override ``save``, call initial state handler on save.

        When ``.save(no_state_validation=True)`` has been used, the state won't
        be validated, and the handler won't we executed. It's recommended to
        use this parameter in South migrations, because South is not really
        aware of which state machine is used for which classes.

        Note that we wrap ``save`` only after the ``class_prepared`` signal
        has been sent, it won't work otherwise when the model has a
        custom ``save`` method.
        """
        real_save = sender.save

        def new_save(obj, *args, **kwargs):
            created = not obj.id

            # Validate whether this is an existing state
            if kwargs.pop('no_state_validation', True):
                state = None
            else:
                # Can raise UnknownState
                state = self._machine.get_state(obj.state)

            # Save first using the real save function
            result = real_save(obj, *args, **kwargs)

            # Now call the handler
            if created and state:
                state.handler(obj)
            return result

        sender.save = new_save


# South introspection
try:
    from south.modelsinspector import add_introspection_rules
except ImportError:
    pass
else:
    add_introspection_rules([
        (
            (StateField,),
            [],
            {
                'max_length': [100, {"is_value": True}],
            },
        ),

        ], ["^django_states\.fields\.StateField"])

########NEW FILE########
__FILENAME__ = log
# -*- coding: utf-8 -*-
"""log model"""

"""
Suport for Django 1.5 custom user model.
"""

import json

from django.db import models
from django.db.models.base import ModelBase
from django.utils.translation import ugettext_lazy as _
from django.conf import settings

from django_states import conf
from django_states.fields import StateField
from django_states.machine import StateMachine, StateDefinition, StateTransition


def _create_state_log_model(state_model, field_name, machine):
    """
    Create a new model for logging the state transitions.

    :param django.db.models.Model state_model: the model that has the
        :class:`~django_states.fields.StateField`
    :param str field_name: the field name of the
        :class:`~django_states.fields.StateField` on the model
    :param django_states.machine.StateMachine machine: the state machine that's used
    """
    class StateTransitionMachine(StateMachine):
        """
        A :class:`~django_states.machine.StateMachine` for log entries (depending on
        what happens).
        """
        # We don't need logging of state transitions in a state transition log
        # entry, as this would cause eternal, recursively nested state
        # transition models.
        log_transitions = False

        class transition_initiated(StateDefinition):
            """Transition has initiated"""
            description = _('State transition initiated')
            initial = True

        class transition_started(StateDefinition):
            """Transition has started"""
            description = _('State transition started')

        class transition_failed(StateDefinition):
            """Transition has failed"""
            description = _('State transition failed')

        class transition_completed(StateDefinition):
            """Transition has completed"""
            description = _('State transition completed')

        class start(StateTransition):
            """Transition Started"""
            from_state = 'transition_initiated'
            to_state = 'transition_started'
            description = _('Start state transition')

        class complete(StateTransition):
            """Transition Complete"""
            from_state = 'transition_started'
            to_state = 'transition_completed'
            description = _('Complete state transition')

        class fail(StateTransition):
            """Transition Failure"""
            from_states = ('transition_initiated', 'transition_started')
            to_state = 'transition_failed'
            description = _('Mark state transition as failed')

    class _StateTransitionMeta(ModelBase):
        """
        Make :class:`_StateTransition` act like it has another name and was
        defined in another model.
        """
        def __new__(c, name, bases, attrs):

            new_unicode = u''
            if '__unicode__' in attrs:
                old_unicode = attrs['__unicode__']

                def new_unicode(self):
                    """New Unicode"""
                    return u'%s (%s)' % (old_unicode(self), self.get_state_info().description)

            attrs['__unicode__'] = new_unicode

            attrs['__module__'] = state_model.__module__
            values = {'model_name': state_model.__name__,
                      'field_name': field_name.capitalize()}
            class_name = conf.LOG_MODEL_NAME % values
            return ModelBase.__new__(c, class_name, bases, attrs)

    get_state_choices = machine.get_state_choices

    class _StateTransition(models.Model):
        """
        The log entries for :class:`~django_states.machine.StateTransition`.
        """
        __metaclass__ = _StateTransitionMeta

        state = StateField(max_length=100, default='0',
                           verbose_name=_('state id'),
                           machine=StateTransitionMachine)

        from_state = models.CharField(max_length=100,
                                      choices=get_state_choices())
        to_state = models.CharField(max_length=100, choices=get_state_choices())
        user = models.ForeignKey(getattr(settings, 'AUTH_USER_MODEL', 'auth.User'), blank=True, null=True)
        serialized_kwargs = models.TextField(blank=True)

        start_time = models.DateTimeField(
            auto_now_add=True, db_index=True,
            verbose_name=_('transition started at')
        )
        on = models.ForeignKey(state_model, related_name=('%s_history' % field_name))

        class Meta:
            """Non-field Options"""
            verbose_name = _('%s transition') % state_model._meta.verbose_name

            # When the state class has been given an app_label, use
            # use this app_label as well for this StateTransition model.
            if hasattr(state_model._meta, 'app_label'):
                app_label = state_model._meta.app_label

        @property
        def kwargs(self):
            """
            The ``kwargs`` that were used when calling the state transition.
            """
            if not self.serialized_kwargs:
                return {}
            return json.loads(self.serialized_kwargs)

        @property
        def completed(self):
            """
            Was the transition completed?
            """
            return self.state == 'transition_completed'

        @property
        def state_transition_definition(self):
            """
            Gets the :class:`django_states.machine.StateTransition` that was used.
            """
            return machine.get_transition_from_states(self.from_state, self.to_state)

        @property
        def from_state_definition(self):
            """
            Gets the :class:`django_states.machine.StateDefinition` from which we
            originated.
            """
            return machine.get_state(self.from_state)

        @property
        def from_state_description(self):
            """
            Gets the description of the
            :class:`django_states.machine.StateDefinition` from which we were
            originated.
            """
            return unicode(self.from_state_definition.description)

        @property
        def to_state_definition(self):
            """
            Gets the :class:`django_states.machine.StateDefinition` to which we
            transitioning.
            """
            return machine.get_state(self.to_state)

        @property
        def to_state_description(self):
            """
            Gets the description of the
            :class:`django_states.machine.StateDefinition` to which we were
            transitioning.
            """
            return unicode(self.to_state_definition.description)

        def make_transition(self, transition, user=None):
            """
            Execute state transition.
            Provide ``user`` to do permission checking.
            :param transition: Name of the transition
            :param user: User object
            """
            return self.get_state_info().make_transition(transition, user=user)

        @property
        def is_public(self):
            """
            Returns ``True`` when this state transition is defined public in
            the machine.
            """
            return self.state_transition_definition.public

        @property
        def transition_description(self):
            """
            Returns the description for this transition as defined in the
            :class:`django_states.machine.StateTransition` declaration of the
            machine.
            """
            return unicode(self.state_transition_definition.description)

        def __unicode__(self):
            return '<State transition on {0} at {1} from "{2}" to "{3}">'.format(
                state_model.__name__, self.start_time, self.from_state, self.to_state)

    # This model will be detected by South because of the models.Model.__new__
    # constructor, which will register it somewhere in a global variable.
    return _StateTransition

########NEW FILE########
__FILENAME__ = machine
# -*- coding: utf-8 -*-
"""State Machine"""

__all__ = ('StateMachine', 'StateDefinition', 'StateTransition')

from collections import defaultdict
import logging

from django_states.exceptions import (TransitionNotFound, TransitionValidationError,
                                UnknownState, TransitionException, MachineDefinitionException)


logger = logging.getLogger(__name__)


class StateMachineMeta(type):
    def __new__(c, name, bases, attrs):
        """
        Validate state machine, and make ``states``, ``transitions`` and
        ``initial_state`` attributes available.
        """
        states = {}
        transitions = {}
        groups = {}
        initial_state = None
        for a in attrs:
            # All definitions are derived from StateDefinition and should be
            # addressable by Machine.states
            if isinstance(attrs[a], StateDefinitionMeta):
                states[a] = attrs[a]
                logger.debug('Found state: %s' % states[a].get_name())
                if states[a].initial:
                    logger.debug('Found initial state: %s' % states[a].get_name())
                    if not initial_state:
                        initial_state = a
                    else:
                        raise Exception('Machine defines multiple initial states')

            # All transitions are derived from StateTransition and should be
            # addressable by Machine.transitions
            if isinstance(attrs[a], StateTransitionMeta):
                transitions[a] = attrs[a]
                logger.debug('Found state transition: %s' % transitions[a].get_name())

            # All definitions derived from StateGroup
            # should be addressable by Machine.groups
            if isinstance(attrs[a], StateGroupMeta):
                groups[a] = attrs[a]
                logger.debug('Found state group: %s' % groups[a].get_name())

        # At least one initial state required. (But don't throw error for the
        # base defintion.)
        if not initial_state and bases != (object,):
            raise MachineDefinitionException(c, 'Machine does not define initial state')

        attrs['states'] = states
        attrs['transitions'] = transitions
        attrs['initial_state'] = initial_state
        attrs['groups'] = groups

        # Give all state transitions a 'to_state_description' attribute.
        # by copying the description from the state definition. (no
        # from_state_description, because multiple from-states are possible.)
        for t in transitions.values():
            t.to_state_description = states[t.to_state].description

        return type.__new__(c, name, bases, attrs)

    def has_transition(self, transition_name):
        """
        Gets whether a transition with the given name is defined in the
        machine.

        :param str transition_name: the transition name

        :returns: ``True`` or ``False``
        """
        return transition_name in self.transitions

    def get_transitions(self, transition_name):
        """
        Gets a transition with the given name.

        :param str transition_name: the transition name

        :returns: the :class:`StateTransition` or raises a :class:`KeyError`
        """
        return self.transitions[transition_name]

    def has_state(self, state_name):
        """
        Gets whether a state with given name is defined in the machine.

        :param str state_name: the state name

        :returns: ``True`` or ``False``
        """
        return state_name in self.states

    def get_state(self, state_name):
        """
        Gets the state with given name

        :param str state_name: the state name

        :returns: a :class:`StateDefinition` or raises
            a :class:`~django_states.exceptions.UnknownState`
        """
        try:
            return self.states[state_name]
        except KeyError:
            raise UnknownState(state_name)

    def get_transition_from_states(self, from_state, to_state):
        """
        Gets the transitions between 2 specified states.

        :param str from_state: the from state
        :param str to_state: the to state

        :returns: a :class:`StateTransition` or raises
            a :class:`~django_states.exceptions.TransitionNotFound`
        """
        for t in self.transitions.values():
            if from_state in t.from_states and t.to_state == to_state:
                return t
        raise TransitionNotFound(self, from_state, to_state)

    def get_state_groups(self, state_name):
        """
        Gets a :class:`dict` of state groups, which will be either ``True`` or
        ``False`` if the current state is specified in that group.

        .. note:: That groups that are not defined will still return ``False``
            and not raise a ``KeyError``.

        :param str state_name: the current state
        """
        result = defaultdict(lambda: False)
        for group in self.groups:
            sg = self.groups[group]
            if hasattr(sg, 'states'):
                result[group] = state_name in sg.states
            elif hasattr(sg, 'exclude_states'):
                result[group] = not state_name in sg.exclude_states
        return result


class StateDefinitionMeta(type):
    def __new__(c, name, bases, attrs):
        """
        Validate state definition
        """
        if bases != (object,):
            if name.lower() != name and not attrs.get('abstract', False):
                raise Exception('Please use lowercase names for state definitions (instead of %s)' % name)
            if not 'description' in attrs and not attrs.get('abstract', False):
                raise Exception('Please give a description to this state definition')

        if 'handler' in attrs and len(attrs['handler'].func_code.co_varnames) < 2:
            raise Exception('StateDefinition handler needs at least two arguments')

        # Turn `handler` into classmethod
        if 'handler' in attrs:
            attrs['handler'] = classmethod(attrs['handler'])

        return type.__new__(c, name, bases, attrs)


class StateGroupMeta(type):
    def __new__(c, name, bases, attrs):
        """
        Validate state group definition
        """
        if bases != (object,):
            # check attributes
            if 'states' in attrs and 'exclude_states' in attrs:
                raise Exception('Use either states or exclude_states but not both')
            elif not 'states' in attrs and not 'exclude_states' in attrs:
                raise Exception('Please specify states or exclude_states to this state group')
            # check type of attributes
            if 'exclude_states' in attrs and not isinstance(attrs['exclude_states'], (list, set)):
                raise Exception('Please give a list (or set) of states to this state group')
            elif 'states' in attrs and not isinstance(attrs['states'], (list, set)):
                raise Exception('Please give a list (or set) of states to this state group')

        return type.__new__(c, name, bases, attrs)


class StateTransitionMeta(type):
    def __new__(c, name, bases, attrs):
        """
        Validate state transition definition
        """
        if bases != (object,):
            if 'from_state' in attrs and 'from_states' in attrs:
                raise Exception('Please use either from_state or from_states')
            if 'from_state' in attrs:
                attrs['from_states'] = (attrs['from_state'],)
                del attrs['from_state']
            if not 'from_states' in attrs:
                raise Exception('Please give a from_state to this state transition')
            if not 'to_state' in attrs:
                raise Exception('Please give a from_state to this state transition')
            if not 'description' in attrs:
                raise Exception('Please give a description to this state transition')

        if 'handler' in attrs and len(attrs['handler'].func_code.co_varnames) < 3:
            raise Exception('StateTransition handler needs at least three arguments')

        # Turn `has_permission` and `handler` into classmethods
        for m in ('has_permission', 'handler', 'validate'):
            if m in attrs:
                attrs[m] = classmethod(attrs[m])

        return type.__new__(c, name, bases, attrs)

    def __unicode__(self):
        return '%s: (from %s to %s)' % (unicode(self.description), ' or '.join(self.from_states), self.to_state)


class StateMachine(object):
    """
    Base class for a state machine definition
    """
    __metaclass__ = StateMachineMeta

    #: Log transitions? Log by default.
    log_transitions = True

    @classmethod
    def get_admin_actions(cls, field_name='state'):
        """
        Creates a list of actions for use in the Django Admin.
        """
        actions = []

        def create_action(transition_name):
            def action(modeladmin, request, queryset):
                # Dry run first
                for o in queryset:
                    get_STATE_info = getattr(o, 'get_%s_info' % field_name)
                    try:
                        get_STATE_info.test_transition(transition_name,
                                                       request.user)
                    except TransitionException, e:
                        modeladmin.message_user(request, 'ERROR: %s on: %s' % (e.message, unicode(o)))
                        return

                # Make actual transitions
                for o in queryset:
                    get_STATE_info = getattr(o, 'get_%s_info' % field_name)
                    get_STATE_info.make_transition(transition_name,
                                                   request.user)

                # Feeback
                modeladmin.message_user(request, 'State changed for %s objects.' % len(queryset))

            action.short_description = unicode(cls.transitions[transition_name])
            action.__name__ = 'state_transition_%s' % transition_name
            return action

        for t in cls.transitions.keys():
            actions.append(create_action(t))

        return actions

    @classmethod
    def get_state_choices(cls):
        """
        Gets all possible choices for a model.
        """
        return [(k, cls.states[k].description) for k in cls.states.keys()]


class StateDefinition(object):
    """
    Base class for a state definition
    """
    __metaclass__ = StateDefinitionMeta

    #: Is this the initial state?  Not initial by default. The machine should
    # define at least one state where ``initial=True``
    initial = False

    def handler(cls, instance):
        """
        Override this method if some specific actions need
        to be executed *after arriving* in this state.
        """
        pass

    @classmethod
    def get_name(cls):
        """
        The name of the state is given by its classname
        """
        return cls.__name__


class StateGroup(object):
    """
    Base class for a state groups
    """
    __metaclass__ = StateGroupMeta

    #: Description for this state group
    description = ''

    @classmethod
    def get_name(cls):
        """
        The name of the state group is given by its classname
        """
        return cls.__name__


class StateTransition(object):
    """
    Base class for a state transitions
    """
    __metaclass__ = StateTransitionMeta

    #: When a transition has been defined as public, is meant to be seen
    #: by the end-user.
    public = False

    def has_permission(cls, instance, user):
        """
        Check whether this user is allowed to execute this state transition on
        this object. You can override this function for every StateTransition.
        """
        return user.is_superuser
        # By default, only superusers are allowed to execute this transition.
        # Note that this is the only permission checking for the POST views.

    def validate(cls, instance):
        """
        Validates whether this object is valid to make this state transition.

        Yields a list of
        :class:`~django_states.exceptions.TransitionValidationError`. You can
        override this function for every StateTransition.
        """
        if False:
            yield TransitionValidationError('Example error')
        # Don't use the 'raise'-statement in here, just yield all the errors.
        # yield TransitionValidationError("This object needs ....")
        # yield TransitionValidationError("Another error ....")

    def handler(cls, instance, user):
        """
        Override this method if some specific actions need
        to be executed during this state transition.
        """
        pass

    @classmethod
    def get_name(cls):
        """
        The name of the state transition is always given by its classname
        """
        return cls.__name__

    @property
    def handler_kwargs(self):
        return self.handler.func_code.co_varnames[3:]

########NEW FILE########
__FILENAME__ = graph_states2
import logging
import os
from optparse import make_option
from yapgvb import Graph

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db.models import get_model

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = '''Generates a graph of available state machines'''
    option_list = BaseCommand.option_list + (
        make_option('--layout', '-l', action='store', dest='layout', default='dot',
            help='Layout to be used by GraphViz for visualization. Layouts: circo dot fdp neato twopi'),
        make_option('--format', '-f', action='store', dest='format', default='pdf',
            help='Format of the output file. Formats: pdf, jpg, png'),
        make_option('--create-dot', action='store_true', dest='create_dot', default=False,
            help='Create a dot file'),
    )
    args = '[model_label.field]'
    label = 'model name, i.e. mvno.subscription.state'

    def handle(self, *args, **options):
        if len(args) < 1:
            raise CommandError('need one or more arguments for model_name.field')

        for model_label in args:
            self.render_for_model(model_label, **options)

    def render_for_model(self, model_label, **options):
        app_label,model,field = model_label.split('.')
        Model = get_model(app_label, model)
        STATE_MACHINE = getattr(Model(), 'get_%s_machine' % field)()

        name = unicode(Model._meta.verbose_name)
        g = Graph('state_machine_graph_%s' % model_label, False)
        g.label = 'State Machine Graph %s' % name
        nodes = {}
        edges = {}

        for state in STATE_MACHINE.states:
            nodes[state] = g.add_node(state,
                                      label=state.upper(),
                                      shape='rect',
                                      fontname='Arial')
            logger.debug('Created node for %s', state)

        def find(f, a):
            for i in a:
                if f(i): return i
            return None

        for trion_name,trion in STATE_MACHINE.transitions.iteritems():
            for from_state in trion.from_states:
                edge = g.add_edge(nodes[from_state], nodes[trion.to_state])
                edge.dir = 'forward'
                edge.arrowhead = 'normal'
                edge.label = '\n_'.join(trion.get_name().split('_'))
                edge.fontsize = 8
                edge.fontname = 'Arial'

                if getattr(trion, 'confirm_needed', False):
                    edge.style = 'dotted'
                edges[u'%s-->%s' % (from_state, trion.to_state)] = edge
            logger.debug('Created %d edges for %s', len(trion.from_states), trion.get_name())

            #if trion.next_function_name is not None:
            #    tr = find(lambda t: t.function_name == trion.next_function_name and t.from_state == trion.to_state, STATE_MACHINE.trions)
            #    while tr.next_function_name is not None:
            #        tr = find(lambda t: t.function_name == tr.next_function_name and t.from_state == tr.to_state, STATE_MACHINE.trions)

            #    if tr is not None:
            #        meta_edge = g.add_edge(nodes[trion.from_state], nodes[tr.to_state])
            #        meta_edge.arrowhead = 'empty'
            #        meta_edge.label = '\n_'.join(trion.function_name.split('_')) + '\n(compound)'
            #        meta_edge.fontsize = 8
            #        meta_edge.fontname = 'Arial'
            #        meta_edge.color = 'blue'

            #if any(lambda t: (t.next_function_name == trion.function_name), STATE_MACHINE.trions):
            #    edge.color = 'red'
            #    edge.style = 'dashed'
            #    edge.label += '\n(auto)'
        logger.info('Creating state graph for %s with %d nodes and %d edges' % (name, len(nodes), len(edges)))

        loc = 'state_machine_%s' % (model_label,)
        if options['create_dot']:
            g.write('%s.dot' % loc)

        logger.debug('Setting layout %s' % options['layout'])
        g.layout(options['layout'])
        format = options['format']
        logger.debug('Trying to render %s' % loc)
        g.render(loc + '.' + format, format, None)
        logger.info('Created state graph for %s at %s' % (name, loc))

########NEW FILE########
__FILENAME__ = models
# -*- coding: utf-8 -*-
"""Models"""

# Author: Jonathan Slenders, CityLive

__doc__ = \
"""

Base models for every State.

"""


__all__ = ('StateMachine', 'StateDefinition', 'StateTransition', 'StateModel')

from django.db import models
from django.db.models.base import ModelBase
from django.utils.translation import ugettext_lazy as _

from django_states.machine import StateMachine, StateDefinition, StateTransition
from django_states.exceptions import States2Exception
from django_states.fields import StateField


# =======================[ State ]=====================
class StateModelBase(ModelBase):
    """
    Metaclass for State models.

    This metaclass will initiate a logging model as well, if required.
    """
    def __new__(cls, name, bases, attrs):
        """
        Instantiation of the State type.

        When this type is created, also create a logging model if required.
        """
        if name != 'StateModel' and 'Machine' in attrs:
            attrs['state'] = StateField(max_length=100, default='0',
                                        verbose_name=_('state id'),
                                        machine=attrs['Machine'])

        # Wrap __unicode__ for state model
        if '__unicode__' in attrs:
            old_unicode = attrs['__unicode__']

            def new_unicode(self):
                return '%s (%s)' % (old_unicode(self), self.Machine.get_state(self.state).description)
            attrs['__unicode__'] = new_unicode

        # Call class constructor of parent
        return ModelBase.__new__(cls, name, bases, attrs)


class StateModel(models.Model):
    """
    Every model which needs state can inherit this abstract model.

    This will dynamically add a :class:`~django_states.fields.StateField` named
    ``state``.
    """
    __metaclass__ = StateModelBase

    class Machine(StateMachine):
        """
        Example machine definition.

        State machines should override this by creating a new machine,
        inherited directly from :class:`~django_states.machine.StateMachine`.
        """
        #: True when we should log all transitions
        log_transitions = False

        # Definition of states (mapping from state_slug to description)
        class initial(StateDefinition):
            initial = True
            description = _('Initial state')

        # Possible transitions, and their names
        class dummy(StateTransition):
            from_state = 'initial'
            to_state = 'initial'
            description = _('Make dummy state transition')

    class Meta:
        abstract = True

    def __unicode__(self):
        return 'State: ' + self.state

    @property
    def state_transitions(self):
        """
        Wraps :meth:`django_states.model_methods.get_STATE_transitions`
        """
        return self.get_state_transitions()

    @property
    def public_transitions(self):
        """
        Wraps :meth:`django_states.model_methods.get_public_STATE_transitions`
        """
        return self.get_public_state_transitions()

    @property
    def state_description(self):
        """
        Gets the full description of the (current) state
        """
        return unicode(self.get_state_info().description)

    @property
    def is_initial_state(self):
        """
        Gets whether this is the initial state.

        :returns: ``True`` when the current state is the initial state
        """
        return bool(self.get_state_info().initial)

    @property
    def possible_transitions(self):
        """
        Gets the list of transitions which can be made from the current state.

        :returns: list of transitions which can be made from the current state
        """
        return self.get_state_info().possible_transitions()

    @classmethod
    def get_state_model_name(self):
        """
        Gets the state model
        """
        return '%s.%s' % (self._meta.app_label, self._meta.object_name)

    def can_make_transition(self, transition, user=None):
        """
        Gets whether we can make the transition.

        :param str transition: the transition name
        :param user: the user that will execute the transition. Used for
            permission checking
        :type: :class:`django.contrib.auth.models.User` or ``None``

        :returns: ``True`` when we should be able to make this transition
        """
        try:
            return self.test_transition(transition, user)
        except States2Exception:
            return False

    def test_transition(self, transition, user=None):
        """
        Check whether we could execute this transition.

        :param str transition: the transition name
        :param user: the user that will execute the transition. Used for
            permission checking
        :type: :class:`django.contrib.auth.models.User` or ``None``

        :returns:``True`` when we expect this transition to be executed
            succesfully. It will raise an ``Exception`` when this
            transition is impossible or not allowed.
        """
        return self.get_state_info().test_transition(transition, user=user)

    def make_transition(self, transition, user=None, **kwargs):
        """
        Executes state transition.

        :param str transition: the transition name
        :param user: the user that will execute the transition. Used for
            permission checking
        :type: :class:`django.contrib.auth.models.User` or ``None``
        :param dict kwargs: the kwargs that will be passed to
            :meth:`~django_states.machine.StateTransition.handler`
        """
        return self.get_state_info().make_transition(transition, user=user, **kwargs)

    @classmethod
    def get_state_choices(cls):
        return cls.Machine.get_state_choices()

########NEW FILE########
__FILENAME__ = model_methods
# -*- coding: utf-8 -*-
"""Model Methods"""

import json

from django_states.exceptions import PermissionDenied, TransitionCannotStart, \
    TransitionException, TransitionNotValidated, UnknownTransition
from django_states.machine import StateMachineMeta
from django_states.signals import before_state_execute, after_state_execute


def get_STATE_transitions(self, field='state'):
    """
    Returns state transitions logs.

    :param str field: the name of the :class:`~django_states.fields.StateField`
    """
    if getattr(self, '_%s_log_model' % field, None):
        LogModel = getattr(self, '_%s_log_model' % field, None)
        return LogModel.objects.filter(on=self)
    else:
        raise Exception('This model does not log state transitions. '
                        'Please enable it by setting log_transitions=True')


def get_public_STATE_transitions(self, field='state'):
    """
    Returns the transitions which are meant to be seen by the customer.
    The admin on the other hand should be able to see everything.

    :param str field: the name of the :class:`~django_states.fields.StateField`
    """
    if getattr(self, '_%s_log_model' % field, None):
        transitions = getattr(self, 'get_%s_transitions' % field)
        return filter(lambda t: t.is_public and t.completed, transitions())
    else:
        return []


def get_STATE_machine(self, field='state', machine=None):
    """
    Gets the machine

    :param str field: the name of the :class:`~django_states.fields.StateField`
    :param django_states.machine.StateMachine machine: the state machine, default
        ``None``
    """
    return machine


def get_STATE_display(self, field='state', machine=None):
    """
    Gets the description of the current state from the machine
    """

    if machine is None:
        return None
    assert isinstance(machine, StateMachineMeta), "Machine must be a valid StateMachine"

    si = machine.get_state(getattr(self, field))
    return si.description


def get_STATE_info(self, field='state', machine=None):
    """
    Gets the state definition from the machine

    :param str field: the name of the :class:`~django_states.fields.StateField`
    :param django_states.machine.StateMachine machine: the state machine, default
        ``None``
    """
    if machine is None:
        return None
    assert isinstance(machine, StateMachineMeta), "Machine must be a valid StateMachine"

    class state_info(object):
        """
        An extra object that hijacks the actual state methods.
        """
        @property
        def name(si_self):
            """
            The name of the current state
            """
            return getattr(self, field)

        @property
        def description(si_self):
            """
            The description of the current state
            """
            si = machine.get_state(getattr(self, field))
            return si.description

        @property
        def in_group(si_self):
            """
            In what groups is this state? It's a dictionary that will return
            ``True`` for the state groups that this state is in.
            """
            return machine.get_state_groups(getattr(self, field))

        def possible_transitions(si_self):
            """
            Return list of transitions which can be made from the current
            state.
            """
            for name in machine.transitions:
                t = machine.transitions[name]
                if getattr(self, field) in t.from_states:
                    yield t

        def test_transition(si_self, transition, user=None):
            """
            Check whether we could execute this transition.

            :param str transition: the transition name
            :param user: the user that will execute the transition. Used for
                permission checking
            :type: :class:`django.contrib.auth.models.User` or ``None``

            :returns:``True`` when we expect this transition to be executed
                successfully. It will raise an ``Exception`` when this
                transition is impossible or not allowed.
            """
            # Transition name should be known
            if not machine.has_transition(transition):
                raise UnknownTransition(self, transition)

            t = machine.get_transitions(transition)

            if getattr(self, field) not in t.from_states:
                raise TransitionCannotStart(self, transition)

            # User should have permissions for this transition
            if user and not t.has_permission(self, user):
                raise PermissionDenied(self, transition, user)

            # Transition should validate
            validation_errors = list(t.validate(self))
            if validation_errors:
                raise TransitionNotValidated(si_self, transition, validation_errors)

            return True

        def make_transition(si_self, transition, user=None, **kwargs):
            """
            Executes state transition.

            :param str transition: the transition name
            :param user: the user that will execute the transition. Used for
                permission checking
            :type: :class:`django.contrib.auth.models.User` or ``None``
            :param dict kwargs: the kwargs that will be passed to
                :meth:`~django_states.machine.StateTransition.handler`
            """
            # Transition name should be known
            if not machine.has_transition(transition):
                raise UnknownTransition(self, transition)
            t = machine.get_transitions(transition)

            _state_log_model = getattr(self, '_%s_log_model' % field, None)

            # Start transition log
            if _state_log_model:
                # Try to serialize kwargs, for the log. Save null
                # when it's not serializable.
                try:
                    serialized_kwargs = json.dumps(kwargs)
                except TypeError:
                    serialized_kwargs = json.dumps(None)

                transition_log = _state_log_model.objects.create(
                    on=self, from_state=getattr(self, field), to_state=t.to_state,
                    user=user, serialized_kwargs=serialized_kwargs)

            # Test transition (access/execution validation)
            try:
                si_self.test_transition(transition, user)
            except TransitionException, e:
                if _state_log_model:
                    transition_log.make_transition('fail')
                raise e

            # Execute
            if _state_log_model:
                transition_log.make_transition('start')

            try:
                from_state = getattr(self, field)

                before_state_execute.send(sender=self,
                                          from_state=from_state,
                                          to_state=t.to_state)
                # First call handler (handler should still see the original
                # state.)
                t.handler(self, user, **kwargs)

                # Then set new state and save.
                setattr(self, field, t.to_state)
                self.save()
                after_state_execute.send(sender=self,
                                         from_state=from_state,
                                         to_state=t.to_state)
            except Exception, e:
                if _state_log_model:
                    transition_log.make_transition('fail')

                raise
            else:
                if _state_log_model:
                    transition_log.make_transition('complete')

                # *After completion*, call the handler of this state
                # definition
                machine.get_state(t.to_state).handler(self)

    return state_info()

########NEW FILE########
__FILENAME__ = signals
# -*- coding: utf-8 -*-
"""Signals"""

import django.dispatch

#: Signal that is sent before a state transition is executed
before_state_execute = django.dispatch.Signal(providing_args=['from_state',
                                                              'to_state'])
#: Signal that s sent after a state transition is executed
after_state_execute = django.dispatch.Signal(providing_args=['from_state',
                                                             'to_state'])

########NEW FILE########
__FILENAME__ = django_states
from django.template import Node, NodeList, Variable
from django.template import TemplateSyntaxError, VariableDoesNotExist
from django.template import Library

register = Library()


class CanMakeTransitionNode(Node):
    def __init__(self, object, transition_name, nodelist):
        self.object = object
        self.transition_name = transition_name
        self.nodelist = nodelist

    def render(self, context):
        object = Variable(self.object).resolve(context)
        transition_name = Variable(self.transition_name).resolve(context)
        user = Variable('request.user').resolve(context)

        if user and object.can_make_transition(transition_name, user):
            return self.nodelist.render(context)
        else:
            return ''


@register.tag
def can_make_transition(parser, token):
    """
    Conditional tag to validate whether it's possible to make a state
    transition (and the user is allowed to make the transition)

    Usage::

        {% can_make_transition object transition_name %}
           ...
        {% end_can_make_transition %}
    """
    # Parameters
    args = token.split_contents()

    # Read nodelist
    nodelist = parser.parse(('endcan_make_transition', ))
    parser.delete_first_token()

    # Return meta node
    return CanMakeTransitionNode(args[1], args[2], nodelist)

########NEW FILE########
__FILENAME__ = tests
# -*- coding: utf-8 -*-
"""Tests"""
from django.contrib.auth.models import User

from django.db import models
from django.test import TransactionTestCase
from django_states.exceptions import PermissionDenied
from django_states.machine import StateMachine, StateDefinition, StateTransition
from django_states.models import StateModel


class TestMachine(StateMachine):
    """A basic state machine"""
    log_transitions = False

    # States
    class start(StateDefinition):
        """Start"""
        description = "Starting State."
        initial = True

    class step_1(StateDefinition):
        """Normal State"""
        description = "Normal State"

    class step_2_fail(StateDefinition):
        """Failure State"""
        description = "Failure State"

    class step_3(StateDefinition):
        """Completed"""
        description = "Completed"

    # Transitions
    class start_step_1(StateTransition):
        """Transition from start to normal"""
        from_state = 'start'
        to_state = 'step_1'
        description = "Transition from start to normal"

    class step_1_step_2_fail(StateTransition):
        """Transition from normal to failure"""
        from_state = 'step_1'
        to_state = 'step_2_fail'
        description = "Transition from normal to failure"

    class step_1_step_3(StateTransition):
        """Transition from normal to complete"""
        from_state = 'step_1'
        to_state = 'step_3'
        description = "Transition from normal to complete"

    class step_2_fail_step_1(StateTransition):
        """Transition from failure back to normal"""
        from_state = 'step_2_fail'
        to_state = 'step_1'
        description = "Transition from failure back to normal"


#class TestLogMachine(TestMachine):
#    """Same as above but this one logs"""
#    log_transitions = True

# ----- Django Test Models ------


class DjangoStateClass(StateModel):
    """Django Test Model implementing a State Machine"""
    field1 = models.IntegerField()
    field2 = models.CharField(max_length=25)
    Machine = TestMachine


#class DjangoStateLogClass(models.Model):
#    """Django Test Model implementing a Logging State Machine"""
#    field1 = models.IntegerField()
#    field2 = models.CharField(max_length=25)
#    Machine = TestLogMachine

# ---- Tests ----


class StateTestCase(TransactionTestCase):
    """This will test out the non-logging side of things"""

    def setUp(self):
        self.superuser = User.objects.create_superuser(
            username='super', email="super@h.us", password="pass")

    def test_initial_state(self):
        """Full end to end test"""
        testmachine = DjangoStateClass(field1=100, field2="LALALALALA")
        testmachine.save()
        self.assertEqual(testmachine.state, 'start')
        self.assertTrue(testmachine.is_initial_state)
        testmachine.make_transition('start_step_1', user=self.superuser)
        self.assertFalse(testmachine.is_initial_state)

    def test_end_to_end(self):
        """Full end to end test"""
        testmachine = DjangoStateClass(field1=100, field2="LALALALALA")
        testmachine.save()
        # Verify the starting state.
        self.assertEqual(testmachine.state, 'start')
        self.assertEqual(testmachine.state_description, 'Starting State.')
        possible = set([x.get_name() for x in testmachine.possible_transitions])
        self.assertEqual(possible, {'start_step_1'})
        # Shift to the first state
        testmachine.make_transition('start_step_1', user=self.superuser)
        self.assertEqual(testmachine.state, 'step_1')
        self.assertEqual(testmachine.state_description, 'Normal State')
        possible = set([x.get_name() for x in testmachine.possible_transitions])
        self.assertEqual(possible, {'step_1_step_3', 'step_1_step_2_fail'})
        # Shift to a failure
        testmachine.make_transition('step_1_step_2_fail', user=self.superuser)
        self.assertEqual(testmachine.state, 'step_2_fail')
        self.assertEqual(testmachine.state_description, 'Failure State')
        possible = set([x.get_name() for x in testmachine.possible_transitions])
        self.assertEqual(possible, {'step_2_fail_step_1'})
        # Shift to a failure
        testmachine.make_transition('step_2_fail_step_1', user=self.superuser)
        self.assertEqual(testmachine.state, 'step_1')
        self.assertEqual(testmachine.state_description, 'Normal State')
        possible = set([x.get_name() for x in testmachine.possible_transitions])
        self.assertEqual(possible, {'step_1_step_3', 'step_1_step_2_fail'})
        # Shift to a completed
        testmachine.make_transition('step_1_step_3', user=self.superuser)
        self.assertEqual(testmachine.state, 'step_3')
        self.assertEqual(testmachine.state_description, 'Completed')
        possible = [x.get_name() for x in testmachine.possible_transitions]
        self.assertEqual(len(possible), 0)

    def test_invalid_user(self):
        """Verify permissions for a user"""
        user = User.objects.create(
            username='user', email="user@h.us", password="pass")
        testmachine = DjangoStateClass(field1=100, field2="LALALALALA")
        testmachine.save()
        kwargs = {'transition': 'start_step_1', 'user': user}
        self.assertRaises(PermissionDenied, testmachine.make_transition, **kwargs)

########NEW FILE########
__FILENAME__ = urls
# -*- coding: utf-8 -*-
"""Urls"""

from .compat import patterns, url
from django_states.views import make_state_transition

urlpatterns = patterns('',
    url(r'^make-state-transition/$', make_state_transition, name='django_states_make_transition'),
)

########NEW FILE########
__FILENAME__ = views
# -*- coding: utf-8 -*-
"""Views"""

from django.db.models import get_model
from django.http import (HttpResponseRedirect, HttpResponseForbidden,
                         HttpResponse,)
from django.shortcuts import get_object_or_404

from django_states.exceptions import PermissionDenied


def make_state_transition(request):
    """
    View to be called by AJAX code to do state transitions. This must be a
    ``POST`` request.

    Required parameters:

    - ``model_name``: the name of the state model, as retured by
      ``instance.get_state_model_name``.
    - ``action``: the name of the state transition, as given by
      ``StateTransition.get_name``.
    - ``id``: the ID of the instance on which the state transition is applied.

    When the handler requires additional kwargs, they can be passed through as
    optional parameters: ``kwarg-{{ kwargs_name }}``
    """
    if request.method == 'POST':
        # Process post parameters
        app_label, model_name = request.POST['model_name'].split('.')
        model = get_model(app_label, model_name)
        instance = get_object_or_404(model, id=request.POST['id'])
        action = request.POST['action']

        # Build optional kwargs
        kwargs = {}
        for p in request.REQUEST:
            if p.startswith('kwarg-'):
                kwargs[p[len('kwargs-')-1:]] = request.REQUEST[p]

        if not hasattr(instance, 'make_transition'):
            raise Exception('No such state model "%s"' % model_name)

        try:
            # Make state transition
            instance.make_transition(action, request.user, **kwargs)
        except PermissionDenied, e:
            return HttpResponseForbidden()
        else:
            # ... Redirect to 'next'
            if 'next' in request.REQUEST:
                return HttpResponseRedirect(request.REQUEST['next'])
            else:
                return HttpResponse('OK')
    else:
        return HttpResponseForbidden()

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# django-states documentation build configuration file, created by
# sphinx-quickstart on Tue Oct 18 17:22:53 2011.
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

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.intersphinx', 'sphinx.ext.viewcode']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'django-states'
copyright = u'2011, Jonathan Slenders, Gert Van Gool'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
import django_states
# The short X.Y version, only interested in the number, e.g. 0.9.2
version = django_states.__version__.split(' ')[0]
# The full version, including alpha/beta/rc tags.
release = django_states.__version__

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
title_dict = {'project': project,
              'version': version,
              'release': release}
html_title = "%(project)s v%(release)s documentation" % title_dict

# A shorter title for the navigation bar.  Default is the same as html_title.
html_short_title = "%(project)s v%(version)s" % title_dict

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
htmlhelp_basename = 'django-statesdoc'


# -- Options for LaTeX output --------------------------------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'django-states.tex', u'django-states Documentation',
   u'Jonathan Slenders, Gert Van Gool', 'manual'),
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
    ('index', 'django-states', u'django-states Documentation',
     [u'Jonathan Slenders, Gert Van Gool'], 1)
]

# -- Option for autodoc
autodoc_member_order = 'bysource'
autodoc_default_flags = ['members', 'undoc-members']

# Example configuration for intersphinx: refer to the Python standard library.
intersphinx_mapping = {'http://docs.python.org/': None}

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
from django.core.management import execute_manager
import imp
try:
    imp.find_module('settings') # Assumed to be in the same directory.
except ImportError:
    import sys
    sys.stderr.write("Error: Can't find the file 'settings.py' in the directory containing %r. It appears you've customized things.\nYou'll have to run django-admin.py, passing it your settings module.\n" % __file__)
    sys.exit(1)

import settings

if __name__ == "__main__":
    execute_manager(settings)

########NEW FILE########
__FILENAME__ = settings
# Django settings for test_proj project.

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

MANAGERS = ADMINS

ROOT = os.path.abspath(
    os.path.join(
        os.path.abspath(os.path.dirname(__file__)),
        '..'
    )
)

path_to = lambda * x: os.path.join(ROOT, *x)

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': path_to('django_states_test.sqlite'),
        'USER': '',
        'PASSWORD': '',
        'HOST': '',
        'PORT': '',
    }
}

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# On Unix systems, a value of None will cause Django to use the same
# timezone as the operating system.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'America/Chicago'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale
USE_L10N = True

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/home/media/media.lawrence.com/media/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://media.lawrence.com/media/", "http://example.com/media/"
MEDIA_URL = ''

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/home/media/media.lawrence.com/static/"
STATIC_ROOT = ''

# URL prefix for static files.
# Example: "http://media.lawrence.com/static/"
STATIC_URL = '/static/'

# URL prefix for admin static files -- CSS, JavaScript and images.
# Make sure to use a trailing slash.
# Examples: "http://foo.com/static/admin/", "/static/admin/".
ADMIN_MEDIA_PREFIX = '/static/admin/'

# Additional locations of static files
STATICFILES_DIRS = (
    # Put strings here, like "/home/html/static" or "C:/www/django/static".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
#    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

# Make this unique, and don't share it with anybody.
SECRET_KEY = '5dtmvd)w%lf8l#!w%gybx^upm0k_&_se-)=0x0ola@(-*&8utn'

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

ROOT_URLCONF = 'test_proj.urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.admin',
    'django.contrib.admindocs',
    'django_states'
)

# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler'
        }
    },
    'loggers': {
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
    }
}

########NEW FILE########
__FILENAME__ = urls
from .compat import patterns, include, url

from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'test_proj.views.home', name='home'),
    # url(r'^test_proj/', include('test_proj.foo.urls')),

    url(r'^admin/doc/', include('django.contrib.admindocs.urls')),
    url(r'^admin/', include(admin.site.urls)),
)

########NEW FILE########
