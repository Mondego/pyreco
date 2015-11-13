__FILENAME__ = admin
# -*- coding: UTF-8 -*-
from django.contrib import admin
from models import Role, Workflow, State, Transition, EventType, Event

class RoleAdmin(admin.ModelAdmin):
    """
    Role administration
    """
    list_display = ['name', 'description']
    search_fields = ['name', 'description']
    save_on_top = True

class WorkflowAdmin(admin.ModelAdmin):
    """
    Workflow administration
    """
    list_display = ['name', 'description', 'status', 'created_on', 'created_by',
            'cloned_from']
    search_fields = ['name', 'description']
    save_on_top = True
    exclude = ['created_on', 'cloned_from']
    list_filter = ['status']

class StateAdmin(admin.ModelAdmin):
    """
    State administration
    """
    list_display = ['name', 'description']
    search_fields = ['name', 'description']
    save_on_top = True

class TransitionAdmin(admin.ModelAdmin):
    """
    Transition administation
    """
    list_display = ['name', 'from_state', 'to_state']
    search_fields = ['name',]
    save_on_top = True

class EventTypeAdmin(admin.ModelAdmin):
    """
    EventType administration
    """
    list_display = ['name', 'description']
    save_on_top = True
    search_fields = ['name', 'description']

class EventAdmin(admin.ModelAdmin):
    """
    Event administration
    """
    list_display = ['name', 'description', 'workflow', 'state', 'is_mandatory']
    save_on_top = True
    search_fields = ['name', 'description']
    list_filter = ['event_types', 'is_mandatory']

admin.site.register(Role, RoleAdmin)
admin.site.register(Workflow, WorkflowAdmin)
admin.site.register(State, StateAdmin)
admin.site.register(Transition, TransitionAdmin)
admin.site.register(EventType, EventTypeAdmin)
admin.site.register(Event, EventAdmin)

########NEW FILE########
__FILENAME__ = forms
# -*- coding: UTF-8 -*-
"""
Forms for Workflows. 

Copyright (c) 2009 Nicholas H.Tollervey (http://ntoll.org/contact)

All rights reserved.

Redistribution and use in source and binary forms, with or without modification,
are permitted provided that the following conditions are met:

* Redistributions of source code must retain the above copyright notice,
this list of conditions and the following disclaimer.
* Redistributions in binary form must reproduce the above copyright
notice, this list of conditions and the following disclaimer in
the documentation and/or other materials provided with the
distribution.
* Neither the name of ntoll.org nor the names of its
contributors may be used to endorse or promote products
derived from this software without specific prior written
permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND
CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES,
INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF
MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR
CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR
OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

"""
# Django
from django import forms
from django.forms.util import ErrorList
from django.utils.translation import ugettext as _

# Workflow models 
from workflow.models import *

########NEW FILE########
__FILENAME__ = models
# -*- coding: UTF-8 -*-
"""
Models for Workflows. 

Copyright (c) 2009 Nicholas H.Tollervey (http://ntoll.org/contact)

All rights reserved.

Redistribution and use in source and binary forms, with or without modification,
are permitted provided that the following conditions are met:

* Redistributions of source code must retain the above copyright notice,
this list of conditions and the following disclaimer.
* Redistributions in binary form must reproduce the above copyright
notice, this list of conditions and the following disclaimer in
the documentation and/or other materials provided with the
distribution.
* Neither the name of ntoll.org nor the names of its
contributors may be used to endorse or promote products
derived from this software without specific prior written
permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND
CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES,
INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF
MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR
CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR
OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

"""
from django.db import models
from django.core.exceptions import ObjectDoesNotExist
from django.utils.translation import ugettext_lazy as _, ugettext as __
from django.contrib.auth.models import User
import django.dispatch
import datetime

############
# Exceptions
############

class UnableToActivateWorkflow(Exception):
    """
    To be raised if unable to activate the workflow because it did not pass the
    validation steps
    """

class UnableToCloneWorkflow(Exception):
    """
    To be raised if unable to clone a workflow model (and related models)
    """

class UnableToStartWorkflow(Exception):
    """
    To be raised if a WorkflowActivity is unable to start a workflow
    """

class UnableToProgressWorkflow(Exception):
    """
    To be raised if the WorkflowActivity is unable to progress a workflow with a
    particular transition.
    """

class UnableToLogWorkflowEvent(Exception):
    """
    To be raised if the WorkflowActivity is unable to log an event in the
    WorkflowHistory
    """

class UnableToAddCommentToWorkflow(Exception):
    """
    To be raised if the WorkflowActivity is unable to log a comment in the
    WorkflowHistory
    """

class UnableToDisableParticipant(Exception):
    """
    To be raised if the WorkflowActivity is unable to disable a participant
    """

class UnableToEnableParticipant(Exception):
    """
    To be raised if the WorkflowActivity is unable to enable a participant
    """

#########
# Signals
#########

# Fired when a role is assigned to a user for a particular run of a workflow
# (defined in the WorkflowActivity). The sender is an instance of the
# WorkflowHistory model logging this event.
role_assigned = django.dispatch.Signal()
# Fired when a role is removed from a user for a particular run of a workflow
# (defined in the WorkflowActivity). The sender is an instance of the
# WorkflowHistory model logging this event.
role_removed = django.dispatch.Signal()
# Fired when a new WorkflowActivity starts navigating a workflow. The sender is
# an instance of the WorkflowActivity model
workflow_started = django.dispatch.Signal()
# Fired just before a WorkflowActivity creates a new item in the Workflow History
# (the sender is an instance of the WorkflowHistory model)
workflow_pre_change = django.dispatch.Signal()
# Fired after a WorkflowActivity creates a new item in the Workflow History (the
# sender is an instance of the WorkflowHistory model)
workflow_post_change = django.dispatch.Signal() 
# Fired when a WorkflowActivity causes a transition to a new state (the sender is
# an instance of the WorkflowHistory model)
workflow_transitioned = django.dispatch.Signal()
# Fired when some event happens during the life of a WorkflowActivity (the 
# sender is an instance of the WorkflowHistory model)
workflow_event_completed = django.dispatch.Signal()
# Fired when a comment is created during the lift of a WorkflowActivity (the
# sender is an instance of the WorkflowHistory model)
workflow_commented = django.dispatch.Signal()
# Fired when an active WorkflowActivity reaches a workflow's end state. The
# sender is an instance of the WorkflowActivity model
workflow_ended = django.dispatch.Signal()

########
# Models
########
class Role(models.Model):
    """
    Represents a type of user who can be associated with a workflow. Used by
    the State and Transition models to define *who* has permission to view a
    state or use a transition. The Event model uses this model to reference
    *who* should be involved in a particular event.
    """
    name = models.CharField(
            _('Name of Role'),
            max_length=64
            )
    description = models.TextField(
            _('Description'),
            blank=True
            )

    def __unicode__(self):
        return self.name

    class Meta:
        ordering = ['name',]
        verbose_name = _('Role')
        verbose_name_plural = _('Roles')
        permissions = (
                ('can_define_roles', __('Can define roles')),
            )

class Workflow(models.Model):
    """
    Instances of this class represent a named workflow that achieve a particular
    aim through a series of related states / transitions. A name for a directed
    graph.
    """

    # A workflow can be in one of three states:
    # 
    # * definition: you're building the thing to meet whatever requirements you
    # have
    #
    # * active: you're using the defined workflow in relation to things in your
    # application - the workflow definition is frozen from this point on.
    #
    # * retired: you no longer use the workflow (but we keep it so it can be 
    # cloned as the basis of new workflows starting in the definition state)
    #
    # Why do this? Imagine the mess that could be created if a "live" workflow
    # was edited and states were deleted or orphaned. These states at least
    # allow us to check things don't go horribly wrong. :-/
    DEFINITION = 0
    ACTIVE = 1
    RETIRED = 2

    STATUS_CHOICE_LIST  = (
                (DEFINITION, _('In definition')),
                (ACTIVE, _('Active')),
                (RETIRED, _('Retired')),
            )

    name = models.CharField(
            _('Workflow Name'),
            max_length=128
            )
    slug = models.SlugField(
            _('Slug')
            )
    description = models.TextField(
            _('Description'),
            blank=True
            )
    status = models.IntegerField(
            _('Status'),
            choices=STATUS_CHOICE_LIST,
            default = DEFINITION
            )
    # These next fields are helpful for tracking the history and devlopment of a
    # workflow should it have been cloned
    created_on = models.DateTimeField(
            auto_now_add=True
            )
    created_by = models.ForeignKey(
            User
            )
    cloned_from = models.ForeignKey(
            'self', 
            null=True
            )

    # To hold error messages created in the validate method
    errors = {
                'workflow':[], 
                'states': {},
                'transitions':{},
             }

    def is_valid(self):
        """
        Checks that the directed graph doesn't contain any orphaned nodes (is
        connected), any cul-de-sac nodes (non-end nodes with no exit
        transition), has compatible roles for transitions and states and
        contains exactly one start node and at least one end state.

        Any errors are logged in the errors dictionary.

        Returns a boolean
        """
        self.errors = {
                'workflow':[], 
                'states': {},
                'transitions':{},
             }
        valid = True

        # The graph must have only one start node
        if self.states.filter(is_start_state=True).count() != 1:
            self.errors['workflow'].append(__('There must be only one start'\
                ' state'))
            valid = False

        # The graph must have at least one end state
        if self.states.filter(is_end_state=True).count() < 1:
            self.errors['workflow'].append(__('There must be at least one end'\
                ' state'))
            valid = False

        # Check for orphan nodes / cul-de-sac nodes
        all_states = self.states.all()
        for state in all_states:
            if state.transitions_into.all().count() == 0 and state.is_start_state == False:
                if not state.id in self.errors['states']:
                    self.errors['states'][state.id] = list()
                self.errors['states'][state.id].append(__('This state is'\
                        ' orphaned. There is no way to get to it given the'\
                        ' current workflow topology.'))
                valid = False

            if state.transitions_from.all().count() == 0 and state.is_end_state == False:
                if not state.id in self.errors['states']:
                    self.errors['states'][state.id] = list()
                self.errors['states'][state.id].append(__('This state is a'\
                        ' dead end. It is not marked as an end state and there'\
                        ' is no way to exit from it.'))
                valid = False

        # Check the role collections are compatible between states and
        # transitions (i.e. there cannot be any transitions that are only
        # available to participants with roles that are not also roles
        # associated with the parent state).
        for state in all_states:
            # *at least* one role from the state must also be associated
            # with each transition where the state is the from_state 
            state_roles = state.roles.all()
            for transition in state.transitions_from.all():
                if not transition.roles.filter(pk__in=[r.id for r in state_roles]):
                    if not transition.id in self.errors['transitions']:
                        self.errors['transitions'][transition.id] = list()
                    self.errors['transitions'][transition.id].append(__('This'\
                            ' transition is not navigable because none of the'\
                            ' roles associated with the parent state have'\
                            ' permission to use it.'))
                    valid = False
        return valid

    def has_errors(self, thing):
        """
        Utility method to quickly get a list of errors associated with the
        "thing" passed to it (either a state or transition)
        """
        if isinstance(thing, State):
            if thing.id in self.errors['states']:
                return self.errors['states'][thing.id]
            else:
                return []
        elif isinstance(thing, Transition):
            if thing.id in self.errors['transitions']:
                return self.errors['transitions'][thing.id]
            else:
                return []
        else:
            return []

    def activate(self):
        """
        Puts the workflow in the "active" state after checking the directed
        graph doesn't contain any orphaned nodes (is connected), is in 
        DEFINITION state, has compatible roles for transitions and states and 
        contains exactly one start state and at least one end state
        """
        # Only workflows in definition state can be activated
        if not self.status == self.DEFINITION:
            raise UnableToActivateWorkflow, __('Only workflows in the'\
                    ' "definition" state may be activated')
        if not self.is_valid():
            raise UnableToActivateWorkflow, __("Cannot activate as the"\
                    " workflow doesn't validate.")
        # Good to go...
        self.status = self.ACTIVE
        self.save()

    def retire(self):
        """
        Retires the workflow so it can no-longer be used with new
        WorkflowActivity models
        """
        self.status = self.RETIRED
        self.save()

    def clone(self, user):
        """
        Returns a clone of the workflow. The clone will be in the DEFINITION
        state whereas the source workflow *must* be ACTIVE or RETIRED (so we
        know it *must* be valid).
        """

        # TODO: A target for refactoring so calling this method doesn't hit the
        # database so hard. Would welcome ideas..?

        if self.status >= self.ACTIVE:
            # Clone this workflow
            clone_workflow = Workflow()
            clone_workflow.name = self.name
            clone_workflow.slug = self.slug+'_clone'
            clone_workflow.description = self.description
            clone_workflow.status = self.DEFINITION
            clone_workflow.created_by = user
            clone_workflow.cloned_from = self
            clone_workflow.save()
            # Clone the states
            state_dict = dict() # key = old pk of state, val = new clone state
            for s in self.states.all():
                clone_state = State()
                clone_state.name = s.name
                clone_state.description = s.description
                clone_state.is_start_state = s.is_start_state
                clone_state.is_end_state = s.is_end_state
                clone_state.workflow = clone_workflow
                clone_state.estimation_value = s.estimation_value
                clone_state.estimation_unit = s.estimation_unit
                clone_state.save()
                for r in s.roles.all():
                    clone_state.roles.add(r)
                state_dict[s.id] = clone_state
            # Clone the transitions
            for tr in self.transitions.all():
                clone_trans = Transition()
                clone_trans.name = tr.name
                clone_trans.workflow = clone_workflow
                clone_trans.from_state = state_dict[tr.from_state.id]
                clone_trans.to_state = state_dict[tr.to_state.id]
                clone_trans.save()
                for r in tr.roles.all():
                    clone_trans.roles.add(r)
            # Clone the events
            for ev in self.events.all():
                clone_event = Event()
                clone_event.name = ev.name
                clone_event.description = ev.description
                clone_event.workflow = clone_workflow
                clone_event.state = state_dict[ev.state.id]
                clone_event.is_mandatory = ev.is_mandatory
                clone_event.save()
                for r in ev.roles.all():
                    clone_event.roles.add(r)
            return clone_workflow
        else:
            raise UnableToCloneWorkflow, __('Only active or retired workflows'\
                    ' may be cloned')

    def __unicode__(self):
        return self.name

    class Meta:
        ordering = ['status', 'name']
        verbose_name = _('Workflow')
        verbose_name_plural = _('Workflows')
        permissions = (
                ('can_manage_workflows', __('Can manage workflows')),
            )

class State(models.Model):
    """
    Represents a specific state that a thing can be in during its progress
    through a workflow. A node in a directed graph.
    """

    # Constant values to denote a period of time in seconds
    SECOND = 1
    MINUTE = 60
    HOUR = 3600
    DAY = 86400
    WEEK = 604800

    DURATIONS = (
            (SECOND, _('Second(s)')),
            (MINUTE, _('Minute(s)')),
            (HOUR, _('Hour(s)')),
            (DAY, _('Day(s)')),
            (WEEK, _('Week(s)')),
            )

    name = models.CharField(
            _('Name'),
            max_length=256
            )
    description = models.TextField(
            _('Description'),
            blank=True
            )
    is_start_state = models.BooleanField(
            _('Is the start state?'),
            help_text=_('There can only be one start state for a workflow'),
            default=False
            )
    is_end_state = models.BooleanField(
            _('Is an end state?'),
            help_text=_('An end state shows that the workflow is complete'),
            default=False
            )
    workflow = models.ForeignKey(
            Workflow,
            related_name='states')
    # The roles defined here define *who* has permission to view the item in
    # this state.
    roles = models.ManyToManyField(
            Role, 
            blank=True
            )
    # The following two fields allow a specification of expected duration to be
    # associated with a state. The estimation_value field stores the amount of 
    # time, whilst estimation_unit stores the unit of time estimation_value is
    # in. For example, estimation_value=5, estimation_unit=DAY means something
    # is expected to be in this state for 5 days. By doing estimation_value *
    # estimation_unit we can get the number of seconds to pass into a timedelta
    # to discover when the deadline for a state is.
    estimation_value = models.IntegerField(
            _('Estimated time (value)'),
            default=0,
            help_text=_('Use whole numbers')
            )
    estimation_unit = models.IntegerField(
            _('Estimation unit of time'),
            default=DAY,
            choices = DURATIONS
            )

    def deadline(self):
        """
        Will return the expected deadline (or None) for this state calculated
        from datetime.today()
        """
        if self.estimation_value > 0:
            duration = datetime.timedelta(
                    seconds=(self.estimation_value*self.estimation_unit)
                    )
            return (self._today()+duration)
        else:
            return None

    def _today(self):
        """
        To help with the unit tests
        """
        return datetime.datetime.today()

    def __unicode__(self):
        return self.name

    class Meta:
        ordering = ['-is_start_state','is_end_state']
        verbose_name = _('State')
        verbose_name_plural = _('States')

class Transition(models.Model):
    """
    Represents how a workflow can move between different states. An edge 
    between state "nodes" in a directed graph.
    """
    name = models.CharField(
            _('Name of transition'),
            max_length=128,
            help_text=_('Use an "active" verb. e.g. "Close Issue", "Open'\
                ' Vacancy" or "Start Interviews"')
            )
    # This field is the result of denormalization to help with the Workflow 
    # class's clone() method.
    workflow = models.ForeignKey(
            Workflow,
            related_name = 'transitions'
            )
    from_state = models.ForeignKey(
            State,
            related_name = 'transitions_from'
            )
    to_state = models.ForeignKey(
            State,
            related_name = 'transitions_into'
            )
    # The roles referenced here define *who* has permission to use this 
    # transition to move between states.
    roles = models.ManyToManyField(
            Role,
            blank=True
            )

    def __unicode__(self):
        return self.name

    class Meta:
        verbose_name = _('Transition')
        verbose_name_plural = _('Transitions')

class EventType(models.Model):
    """
    Defines the types of event that can be associated with a workflow. Examples
    might include: meeting, deadline, review, assessment etc...
    """
    name = models.CharField(
            _('Event Type Name'),
            max_length=256
            )
    description = models.TextField(
            _('Description'),
            blank=True
            )

    def __unicode__(self):
        return self.name

class Event(models.Model):
    """
    A definition of something that is supposed to happen when in a particular
    state.
    """
    name = models.CharField(
            _('Event summary'),
            max_length=256
            )
    description = models.TextField(
            _('Description'),
            blank=True
            )
    # The workflow field is the result of denormalization to help with the
    # Workflow class's clone() method.
    # Also, workflow and state can be nullable so an event can be treated as
    # "generic" for all workflows / states in the database.
    workflow = models.ForeignKey(
            Workflow,
            related_name='events',
            null=True,
            blank=True
            )
    state = models.ForeignKey(
            State,
            related_name='events',
            null=True,
            blank=True
            )
    # The roles referenced here indicate *who* is supposed to be a part of the
    # event
    roles = models.ManyToManyField(Role)
    # The event types referenced here help define what sort of event this is.
    # For example, a meeting and review (an event might be of more than one
    # type)
    event_types = models.ManyToManyField(EventType)
    # If this field is true then the workflow cannot progress beyond the related
    # state without it first appearing in the workflow history
    is_mandatory = models.BooleanField(
            _('Mandatory event'),
            default=False,
            help_text=_('This event must be marked as complete before moving'\
                    ' out of the associated state.')
            )

    def __unicode__(self):
        return self.name

    class Meta:
        verbose_name = _('Event')
        verbose_name_plural = _('Events')

class WorkflowActivity(models.Model):
    """
    Other models in a project reference this model so they become associated 
    with a particular workflow.

    The WorkflowActivity object also contains *all* the methods required to
    start, progress and stop a workflow.
    """
    workflow = models.ForeignKey(Workflow)
    created_by = models.ForeignKey(User)
    created_on = models.DateTimeField(auto_now_add=True)
    completed_on = models.DateTimeField(
            null=True,
            blank=True
            )

    def current_state(self):
        """ 
        Returns the instance of the WorkflowHistory model that represents the 
        current state this WorkflowActivity is in.
        """
        if self.history.all():
            return self.history.all()[0]
        else:
            return None

    def start(self, user):
        """
        Starts a WorkflowActivity by putting it into the start state of the
        workflow defined in the "workflow" field after validating the workflow
        activity is in a state appropriate for "starting"
        """
        participant = Participant.objects.get(workflowactivity=self, user=user,
                disabled=False)

        start_state_result = State.objects.filter(
                workflow=self.workflow, 
                is_start_state=True
                )
        # Validation...
        # 1. The workflow activity isn't already started
        if self.current_state():
            if self.current_state().state:
                raise UnableToStartWorkflow, __('Already started')
        # 2. The workflow activity hasn't been force_stopped before being 
        # started
        if self.completed_on:
            raise UnableToStartWorkflow, __('Already completed')
        # 3. There is exactly one start state
        if not len(start_state_result) == 1:
            raise UnableToStartWorkflow, __('Cannot find single start state')
        # Good to go...
        first_step = WorkflowHistory(
                workflowactivity=self,
                state=start_state_result[0],
                log_type=WorkflowHistory.TRANSITION,
                participant=participant,
                note=__('Started workflow'),
                deadline=start_state_result[0].deadline()
            )
        first_step.save()
        return first_step

    def progress(self, transition, user, note=''):
        """
        Attempts to progress a workflow activity with the specified transition 
        as requested by the specified participant.

        The transition is validated (to make sure it is a legal "move" in the
        directed graph) and the method returns the new WorkflowHistory state or
        raises an UnableToProgressWorkflow exception.
        """
        participant = Participant.objects.get(workflowactivity=self, user=user,
                disabled=False)
        # Validate the transition
        current_state = self.current_state()

        # 1. Make sure the workflow activity is started
        if not current_state:
            raise UnableToProgressWorkflow, __('Start the workflow before'\
                    ' attempting to transition')
        # 2. Make sure it's parent is the current state
        if not transition.from_state == current_state.state:
            raise UnableToProgressWorkflow, __('Transition not valid (wrong'\
                    ' parent)')
        # 3. Make sure all mandatory events for the current state are found in 
        # the WorkflowHistory
        mandatory_events = current_state.state.events.filter(is_mandatory=True)
        for me in mandatory_events:
            if not me.history.filter(workflowactivity=self):
                raise UnableToProgressWorkflow, __('Transition not valid'\
                    ' (mandatory event missing)')
        # 4. Make sure the user has the appropriate role to allow them to make
        # the transition
        if not transition.roles.filter(pk__in=[role.id for role in participant.roles.all()]):
            raise UnableToProgressWorkflow, __('Participant has insufficient'\
                    ' authority to use the specified transition')
        # The "progress" request has been validated to store the transition into
        # the appropriate WorkflowHistory record and if it is an end state then
        # update this WorkflowActivity's record with the appropriate timestamp
        if not note:
            note = transition.name
        wh = WorkflowHistory(
                workflowactivity=self,
                state=transition.to_state,
                log_type=WorkflowHistory.TRANSITION,
                transition=transition,
                participant=participant,
                note=note,
                deadline=transition.to_state.deadline()
                )
        wh.save()
        # If we're at the end then mark the workflow activity as completed on
        # today
        if transition.to_state.is_end_state:
            self.completed_on = datetime.datetime.today()
            self.save()
        return wh

    def log_event(self, event, user, note=''):
        """
        Logs the occurance of an event in the WorkflowHistory of a 
        WorkflowActivity and returns the resulting record.

        If the event is associated with a workflow or state then this method
        validates that the event is associated with the workflow, that the
        participant logging the event is also one of the event participants and
        if the event is mandatory then it must be done whilst in the
        appropriate state.
        """
        participant = Participant.objects.get(workflowactivity=self, user=user,
                disabled=False)
        current_state = self.current_state()
        if event.workflow:
            # Make sure we have an event for the right workflow
            if not event.workflow == self.workflow:
                raise UnableToLogWorkflowEvent, __('The event is not associated'\
                        ' with the workflow for the WorkflowActivity')
            if event.state:
                # If the event is mandatory then it must be completed whilst in
                # the associated state
                if event.is_mandatory:
                    if not event.state == current_state.state:
                        raise UnableToLogWorkflowEvent, __('The mandatory'\
                                ' event is not associated with the current'\
                                ' state')
        if event.roles.all():
            # Make sure the participant is associated with the event
            if not event.roles.filter(pk__in=[p.id for p in participant.roles.all()]):
                raise UnableToLogWorkflowEvent, __('The participant is not'\
                        ' associated with the specified event')
        if not note:
            note=event.name
        # Good to go...
        current_state = self.current_state().state if self.current_state() else None
        deadline = self.current_state().deadline if self.current_state() else None
        wh = WorkflowHistory(
                workflowactivity=self,
                state=current_state,
                log_type=WorkflowHistory.EVENT,
                event=event,
                participant=participant,
                note=note,
                deadline=deadline
                )
        wh.save()
        return wh

    def add_comment(self, user, note):
        """
        In many sorts of workflow it is necessary to add a comment about
        something at a particular state in a WorkflowActivity. 
        """
        if not note:
            raise UnableToAddCommentToWorkflow, __('Cannot add an empty comment')
        p, created = Participant.objects.get_or_create(workflowactivity=self,
                user=user)  
        current_state = self.current_state().state if self.current_state() else None
        deadline = self.current_state().deadline if self.current_state() else None
        wh = WorkflowHistory(
                workflowactivity=self,
                state=current_state,
                log_type=WorkflowHistory.COMMENT,
                participant=p,
                note=note,
                deadline=deadline
                )
        wh.save()
        return wh

    def assign_role(self, user, assignee, role):
        """
        Assigns the role to the assignee for this instance of a workflow 
        activity. The arg 'user' logs who made the assignment
        """
        p_as_user = Participant.objects.get(workflowactivity=self, user=user,
                disabled=False)
        p_as_assignee, created = Participant.objects.get_or_create(
                workflowactivity=self,
                user=assignee)
        p_as_assignee.roles.add(role)
        name = assignee.get_full_name() if assignee.get_full_name() else assignee.username
        note = _('Role "%s" assigned to %s')%(role.__unicode__(), name)
        current_state = self.current_state().state if self.current_state() else None
        deadline = self.current_state().deadline if self.current_state() else None
        wh = WorkflowHistory(
                workflowactivity=self,
                state=current_state,
                log_type=WorkflowHistory.ROLE,
                participant=p_as_user,
                note=note,
                deadline=deadline
                )
        wh.save()
        role_assigned.send(sender=wh)
        return wh

    def remove_role(self, user, assignee, role):
        """
        Removes the role from the assignee. The 'user' argument is used for
        logging purposes.
        """
        try:
            p_as_user = Participant.objects.get(workflowactivity=self, 
                        user=user, disabled=False)
            p_as_assignee = Participant.objects.get(workflowactivity=self, 
                    user=assignee)
            if role in p_as_assignee.roles.all():
                p_as_assignee.roles.remove(role)
                name = assignee.get_full_name() if assignee.get_full_name() else assignee.username
                note = _('Role "%s" removed from %s')%(role.__unicode__(), name)
                current_state = self.current_state().state if self.current_state() else None
                deadline = self.current_state().deadline if self.current_state() else None
                wh = WorkflowHistory(
                        workflowactivity=self,
                        state=current_state,
                        log_type=WorkflowHistory.ROLE,
                        participant=p_as_user,
                        note=note,
                        deadline=deadline
                        )
                wh.save()
                role_removed.send(sender=wh)
                return wh
            else:
                # The role isn't associated with the assignee anyway so there is
                # nothing to do
                return None
        except ObjectDoesNotExist:
            # If we can't find the assignee as a participant then there is 
            # nothing to do
            return None 

    def clear_roles(self, user, assignee):
        """
        Clears all the roles from assignee. The 'user' argument is used for
        logging purposes.
        """
        try:
            p_as_user = Participant.objects.get(workflowactivity=self, 
                        user=user, disabled=False)
            p_as_assignee = Participant.objects.get(workflowactivity=self, 
                    user=assignee)
            p_as_assignee.roles.clear()
            name = assignee.get_full_name() if assignee.get_full_name() else assignee.username
            note = _('All roles removed from %s')%name
            current_state = self.current_state().state if self.current_state() else None
            deadline = self.current_state().deadline if self.current_state() else None
            wh = WorkflowHistory(
                        workflowactivity=self,
                        state=current_state,
                        log_type=WorkflowHistory.ROLE,
                        participant=p_as_user,
                        note=note,
                        deadline=deadline
                        )
            wh.save()
            role_removed.send(sender=wh)
            return wh
        except ObjectDoesNotExist:
            # If we can't find the assignee then there is nothing to do
            pass

    def disable_participant(self, user, user_to_disable, note):
        """
        Mark the user_to_disable as disabled. Must include a note explaining
        reasons for this action. Also the 'user' arg is used for logging who
        carried this out
        """
        if not note:
            raise UnableToDisableParticipant, __('Must supply a reason for'\
                    ' disabling a participant. None given.')
        try:
            p_as_user = Participant.objects.get(workflowactivity=self, 
                            user=user, disabled=False)
            p_to_disable = Participant.objects.get(workflowactivity=self, 
                    user=user_to_disable)
            if not p_to_disable.disabled:
                p_to_disable.disabled = True
                p_to_disable.save()
                name = user_to_disable.get_full_name() if user_to_disable.get_full_name() else user_to_disable.username
                note = _('Participant %s disabled with the reason: %s')%(name, note)
                current_state = self.current_state().state if self.current_state() else None
                deadline = self.current_state().deadline if self.current_state() else None
                wh = WorkflowHistory(
                            workflowactivity=self,
                            state=current_state,
                            log_type=WorkflowHistory.ROLE,
                            participant=p_as_user,
                            note=note,
                            deadline=deadline
                            )
                wh.save()
                return wh
            else:
                # They're already disabled
                return None
        except ObjectDoesNotExist:
            # If we can't find the assignee then there is nothing to do
            return None 
    
    def enable_participant(self, user, user_to_enable, note):
        """
        Mark the user_to_enable as enabled. Must include a note explaining
        reasons for this action. Also the 'user' arg is used for logging who
        carried this out
        """
        if not note:
            raise UnableToEnableParticipant, __('Must supply a reason for'\
                    ' enabling a disabled participant. None given.')
        try:
            p_as_user = Participant.objects.get(workflowactivity=self, 
                            user=user, disabled=False)
            p_to_enable = Participant.objects.get(workflowactivity=self, 
                    user=user_to_enable)
            if p_to_enable.disabled:
                p_to_enable.disabled = False 
                p_to_enable.save()
                name = user_to_enable.get_full_name() if user_to_enable.get_full_name() else user_to_enable.username
                note = _('Participant %s enabled with the reason: %s')%(name, 
                        note)
                current_state = self.current_state().state if self.current_state() else None
                deadline = self.current_state().deadline if self.current_state() else None
                wh = WorkflowHistory(
                            workflowactivity=self,
                            state=current_state,
                            log_type=WorkflowHistory.ROLE,
                            participant=p_as_user,
                            note=note,
                            deadline=deadline
                            )
                wh.save()
                return wh
            else:
                # The participant is already enabled
                return None
        except ObjectDoesNotExist:
            # If we can't find the participant then there is nothing to do
            return None 

    def force_stop(self, user, reason):
        """
        Should a WorkflowActivity need to be abandoned this method cleanly logs
        the event and puts the WorkflowActivity in the appropriate state (with
        reason provided by participant).
        """
        # Lets try to create an appropriate entry in the WorkflowHistory table
        current_state = self.current_state()
        participant = Participant.objects.get(
                        workflowactivity=self, 
                        user=user)
        if current_state:
            final_step = WorkflowHistory(
                workflowactivity=self,
                state=current_state.state,
                log_type=WorkflowHistory.TRANSITION,
                participant=participant,
                note=__('Workflow forced to stop! Reason given: %s') % reason,
                deadline=None
                )
            final_step.save()

        self.completed_on = datetime.datetime.today()
        self.save()

    class Meta:
        ordering = ['-completed_on', '-created_on']
        verbose_name = _('Workflow Activity')
        verbose_name_plural = _('Workflow Activites')
        permissions = (
                ('can_start_workflow',__('Can start a workflow')),
                ('can_assign_roles',__('Can assign roles'))
            )

class Participant(models.Model):
    """
    Defines which users have what roles in a particular run of a workflow
    """
    user = models.ForeignKey(User)
    # can be nullable because a participant *might* not have a role assigned to
    # them (yet), and is many-to-many as they might have many different roles.
    roles = models.ManyToManyField(
            Role,
            null=True)
    workflowactivity= models.ForeignKey(
            WorkflowActivity,
            related_name='participants'
            )
    disabled = models.BooleanField(default=False)

    def __unicode__(self):
        name = self.user.get_full_name() if self.user.get_full_name() else self.user.username
        if self.roles.all():
            roles = u' - ' + u', '.join([r.__unicode__() for r in self.roles.all()])
        else:
            roles = '' 
        disabled = _(' (disabled)') if self.disabled else ''
        return u"%s%s%s"%(name, roles, disabled)

    class Meta:
        ordering = ['-disabled', 'workflowactivity', 'user',]
        verbose_name = _('Participant')
        verbose_name_plural = _('Participants')
        unique_together = ('user', 'workflowactivity')

class WorkflowHistory(models.Model):
    """
    Records what has happened and when in a particular run of a workflow. The
    latest record for the referenced WorkflowActivity will indicate the current 
    state.
    """

    # The sort of things we can log in the workflow history
    TRANSITION = 1
    EVENT = 2
    ROLE = 3
    COMMENT = 4

    # Used to indicate what sort of thing we're logging in the workflow history
    TYPE_CHOICE_LIST = (
            (TRANSITION, _('Transition')),
            (EVENT, _('Event')),
            (ROLE, _('Role')),
            (COMMENT, _('Comment')),
            )

    workflowactivity= models.ForeignKey(
            WorkflowActivity,
            related_name='history')
    log_type = models.IntegerField(
            help_text=_('The sort of thing being logged'),
            choices=TYPE_CHOICE_LIST
            )
    state = models.ForeignKey(
            State,
            help_text=_('The state at this point in the workflow history'),
            null=True
            )
    transition = models.ForeignKey(
            Transition, 
            null=True,
            related_name='history',
            help_text=_('The transition relating to this happening in the'\
                ' workflow history')
            )
    event = models.ForeignKey(
            Event, 
            null=True,
            related_name='history',
            help_text=_('The event relating to this happening in the workflow'\
                    ' history')
            )
    participant = models.ForeignKey(
            Participant,
            help_text=_('The participant who triggered this happening in the'\
                ' workflow history')
            )
    created_on = models.DateTimeField(auto_now_add=True)
    note = models.TextField(
            _('Note'),
            blank=True
            )
    deadline = models.DateTimeField(
            _('Deadline'),
            null=True,
            blank=True,
            help_text=_('The deadline for staying in this state')
            )

    def save(self):
        workflow_pre_change.send(sender=self)
        super(WorkflowHistory, self).save()
        workflow_post_change.send(sender=self)
        if self.log_type==self.TRANSITION:
            workflow_transitioned.send(sender=self)
        if self.log_type==self.EVENT:
            workflow_event_completed.send(sender=self)
        if self.log_type==self.COMMENT:
            workflow_commented.send(sender=self)
        if self.state:
            if self.state.is_start_state:
                workflow_started.send(sender=self.workflowactivity)
            elif self.state.is_end_state:
                workflow_ended.send(sender=self.workflowactivity)

    def __unicode__(self):
        return u"%s created by %s"%(self.note, self.participant.__unicode__())

    class Meta:
        ordering = ['-created_on']
        verbose_name = _('Workflow History')
        verbose_name_plural = _('Workflow Histories')

########NEW FILE########
__FILENAME__ = tests
# -*- coding: UTF-8 -*-
"""
Define a simple document management workflow:

>>> from django.contrib.auth.models import User
>>> from workflow.models import *

A couple of users to interact with the workflow

>>> fred = User.objects.create_user('fred','fred@acme.com','password')
>>> joe = User.objects.create_user('joe','joe@acme.com','password')

A document class that really should be a models.Model class (but you get the
idea)

>>> class Document():
...     def __init__(self, title, body, workflow_activity):
...             self.title = title
...             self.body = body
...             self.workflow_activity = workflow_activity
... 

Roles define the sort of person involved in a workflow.

>>> author = Role.objects.create(name="author", description="Author of a document")
>>> boss = Role.objects.create(name="boss", description="Departmental boss")

EventTypes define what sort of events can happen in a workflow.

>>> approval = EventType.objects.create(name="Document Approval", description="A document is reviewed by an approver")
>>> meeting = EventType.objects.create(name='Meeting', description='A meeting at the offices of Acme Inc')

Creating a workflow puts it into the "DEFINITION" status. It can't be used yet.

>>> wf = Workflow.objects.create(name='Simple Document Approval', slug='docapp', description='A simple document approval process', created_by=joe)

Adding four states:

>>> s1 = State.objects.create(name='In Draft', description='The author is writing a draft of the document', is_start_state=True, workflow=wf)
>>> s2 = State.objects.create(name='Under Review', description='The approver is reviewing the document', workflow=wf)
>>> s3 = State.objects.create(name='Published', description='The document is published', workflow=wf)
>>> s4 = State.objects.create(name='Archived', description='The document is put into the archive', is_end_state=True, workflow=wf)

Defining what sort of person is involved in each state by associating roles.

>>> s1.roles.add(author)
>>> s2.roles.add(boss)
>>> s2.roles.add(author)
>>> s3.roles.add(boss)
>>> s4.roles.add(boss)

Adding transitions to define how the states relate to each other. Notice how the
name of each transition is an "active" description of what it does in order to
get to the next state.

>>> t1 = Transition.objects.create(name='Request Approval', workflow=wf, from_state=s1, to_state=s2)
>>> t2 = Transition.objects.create(name='Revise Draft', workflow=wf, from_state=s2, to_state=s1)
>>> t3 = Transition.objects.create(name='Publish', workflow=wf, from_state=s2, to_state=s3)
>>> t4 = Transition.objects.create(name='Archive', workflow=wf, from_state=s3, to_state=s4)

Once again, using roles to define what sort of person can transition between
states.

>>> t1.roles.add(author)
>>> t2.roles.add(boss)
>>> t3.roles.add(boss)
>>> t4.roles.add(boss)

Creating a mandatory event to be attended by the boss and author during the
"Under Review" state.

>>> approval_meeting = Event.objects.create(name='Approval Meeting', description='Approver and author meet to discuss document', workflow=wf, state=s2, is_mandatory=True)
>>> approval_meeting.roles.add(author)
>>> approval_meeting.roles.add(boss)

Notice how we can define what sort of event this is by associating event types
defined earlier

>>> approval_meeting.event_types.add(approval)
>>> approval_meeting.event_types.add(meeting)

An event doesn't have to be *so* constrained by workflow, roles or state. The
following state can take place in any workflow, at any state by any role:

>>> team_meeting = Event.objects.create(name='Team Meeting', description='A team meeting that can happen in any workflow')
>>> team_meeting.event_types.add(meeting)

The activate method on the workflow validates the directed graph and puts it in
the "active" state so it can be used.

>>> wf.activate()

Lets set up a workflow activity and assign roles to users for a new document so
we can interact with the workflow we defined above.

>>> wa = WorkflowActivity(workflow=wf, created_by=fred)
>>> wa.save()

Use the built in methods associated with the WorkflowActivity class to ensure
such changes are appropriately logged in the history.

>>> p1 = Participant()
>>> p1 = Participant(user=fred, workflowactivity=wa)
>>> p1.save()
>>> p2 = Participant(user=joe, workflowactivity=wa)
>>> p2.save()
>>> wa.assign_role(fred, joe, boss)
<WorkflowHistory: Role "boss" assigned to joe created by fred>
>>> wa.assign_role(joe, fred, author)
<WorkflowHistory: Role "author" assigned to fred created by joe - boss>
>>> d = Document(title='Had..?', body="Bob, where Alice had had 'had', had had 'had had'; 'had had' had had the examiner's approval", workflow_activity=wa)

Starting the workflow via the workflow activity is easy... notice we have to pass
the participant and that the method returns the current state.

>>> d.workflow_activity.start(fred)
<WorkflowHistory: Started workflow created by fred - author>

The WorkflowActivity's current_state() method does exactly what it says. You can
find out lots of interesting things...

>>> current = d.workflow_activity.current_state()
>>> current.participant
<Participant: fred - author>
>>> current.note
u'Started workflow'
>>> current.state
<State: In Draft>
>>> current.state.transitions_from.all()
[<Transition: Request Approval>]

Lets progress the workflow for this document (the author has finished the draft
and submits it for approval)

>>> my_transition = current.state.transitions_from.all()[0]
>>> my_transition
<Transition: Request Approval>
>>> d.workflow_activity.progress(my_transition, fred)
<WorkflowHistory: Request Approval created by fred - author>

Notice the WorkflowActivity's progress method returns the new state. What is 
current_state() telling us..?

>>> current = d.workflow_activity.current_state()
>>> current.state
<State: Under Review>
>>> current.state.roles.all()
[<Role: author>, <Role: boss>]
>>> current.transition
<Transition: Request Approval>
>>> current.note
u'Request Approval'
>>> current.state.events.all()
[<Event: Approval Meeting>]

So we have an event associated with this event. Lets pretend it's happened.
Notice that I can pass a bespoke "note" to store against the event.

>>> my_event = current.state.events.all()[0]
>>> d.workflow_activity.log_event(my_event, joe, "A great review meeting, loved the punchline!")
<WorkflowHistory: A great review meeting, loved the punchline! created by joe - boss>
>>> current = d.workflow_activity.current_state()
>>> current.state
<State: Under Review>
>>> current.event
<Event: Approval Meeting>
>>> current.note
u'A great review meeting, loved the punchline!'

Continue with the progress of the workflow activity... Notice I can also pass a
bespoke "note" to the progress method.

>>> current.state.transitions_from.all().order_by('id')
[<Transition: Revise Draft>, <Transition: Publish>]
>>> my_transition = current.state.transitions_from.all().order_by('id')[1]
>>> d.workflow_activity.progress(my_transition, joe, "We'll be up for a Pulitzer")
<WorkflowHistory: We'll be up for a Pulitzer created by joe - boss>

We can also log events that have not been associated with specific workflows,
states or roles...

>>> d.workflow_activity.log_event(team_meeting, joe)
<WorkflowHistory: Team Meeting created by joe - boss>
>>> current = d.workflow_activity.current_state()
>>> current.event
<Event: Team Meeting>

Lets finish the workflow just to demonstrate what useful stuff is logged:

>>> current = d.workflow_activity.current_state()
>>> current.state.transitions_from.all().order_by('id')
[<Transition: Archive>]
>>> my_transition = current.state.transitions_from.all().order_by('id')[0]
>>> d.workflow_activity.progress(my_transition, joe)
<WorkflowHistory: Archive created by joe - boss>
>>> for item in d.workflow_activity.history.all():
...     print '%s by %s'%(item.note, item.participant.user.username)
... 
Archive by joe
Team Meeting by joe
We'll be up for a Pulitzer by joe
A great review meeting, loved the punchline! by joe
Request Approval by fred
Started workflow by fred
Role "author" assigned to fred by joe
Role "boss" assigned to joe by fred

Unit tests are found in the unit_tests module. In addition to doctests this file
is a hook into the Django unit-test framework. 

Author: Nicholas H.Tollervey

"""
from unit_tests.test_views import *
from unit_tests.test_models import *
from unit_tests.test_forms import *

########NEW FILE########
__FILENAME__ = test_runner
# -*- coding: UTF-8 -*-
"""

A custom test runner that includes reporting of unit test coverage. Based upon
code found here:

    http://www.thoughtspark.org/node/6

You should also have coverage.py in your python path. See:

    http://nedbatchelder.com/code/modules/coverage.html

for more information.

To use this test runner modify your settings.py file with the following:

# Specify your custom test runner to use
TEST_RUNNER='workflow.test_runner.test_runner_with_coverage'
     
# List of modules to enable for code coverage
COVERAGE_MODULES = ['workflow.models', 'workflow.views',] # etc...

You'll get a code coverage report for your unit tests:

------------------------------------------------------------------
 Unit Test Code Coverage Results
------------------------------------------------------------------
 Name           Stmts   Exec  Cover   Missing
--------------------------------------------
 sample.urls        2      0     0%   1-3
 sample.views       3      0     0%   1-5
--------------------------------------------
 TOTAL              5      0     0%
------------------------------------------------------------------

For every module added to COVERAGE_MODULES you'll get an entry telling you the
number of executable statements, the number executed, the percentage executed
and a list of the code lines not executed (in the above play example, no tests
have been written). Aim for 100% :-)

!!!! WARNING !!!

Because of the use of coverage, this test runner is SLOW.

Also, use with care - this code works with the command:

    python manage.py test workflow

(Where workflow is the name of this app in your project) 

It probably won't work for all other manage.py test cases.

TODO: Fix the cause of the warning above!

"""
import os, shutil, sys, unittest

# Look for coverage.py in __file__/lib as well as sys.path
sys.path = [os.path.join(os.path.dirname(__file__), "lib")] + sys.path
 
import coverage
from django.test.simple import run_tests as django_test_runner
  
from django.conf import settings

def test_runner_with_coverage(test_labels, verbosity=1, interactive=True, extra_tests=[]):
    """
    Custom test runner.  Follows the django.test.simple.run_tests() interface.
    """
    # Start code coverage before anything else if necessary
    if hasattr(settings, 'COVERAGE_MODULES'):
        coverage.use_cache(0) # Do not cache any of the coverage.py stuff
        coverage.start()

    test_results = django_test_runner(test_labels, verbosity, interactive, extra_tests)

    # Stop code coverage after tests have completed
    if hasattr(settings, 'COVERAGE_MODULES'):
        coverage.stop()

    # Print code metrics header
    print ''
    print '----------------------------------------------------------------------'
    print ' Unit Test Code Coverage Results'
    print '----------------------------------------------------------------------'

    # Report code coverage metrics
    if hasattr(settings, 'COVERAGE_MODULES'):
        coverage_modules = []
        for module in settings.COVERAGE_MODULES:
            coverage_modules.append(__import__(module, globals(), locals(), ['']))
        coverage.report(coverage_modules, show_missing=1)
        # Print code metrics footer
        print '----------------------------------------------------------------------'

    return test_results

########NEW FILE########
__FILENAME__ = test_forms
# -*- coding: UTF-8 -*-
"""
Forms tests for workflow 

Author: Nicholas H.Tollervey

"""
# python
import datetime

# django
from django.test.client import Client
from django.test import TestCase

# project
from workflow.forms import * 

class FormTestCase(TestCase):
        """
        Testing Forms 
        """
        # Reference fixtures here
        fixtures = []

        def test_something(self):
            pass

########NEW FILE########
__FILENAME__ = test_models
# -*- coding: UTF-8 -*-
"""
Model tests for Workflow 

Author: Nicholas H.Tollervey

"""
# python
import datetime
import sys

# django
from django.test.client import Client
from django.test import TestCase
from django.contrib.auth.models import User

# project
from workflow.models import *

class ModelTestCase(TestCase):
        """
        Testing Models 
        """
        # Reference fixtures here
        fixtures = ['workflow_test_data']

        def test_workflow_unicode(self):
            """
            Makes sure that the slug field (name) is returned from a call to
            __unicode__()
            """
            w = Workflow.objects.get(id=1)
            self.assertEquals(u'test workflow', w.__unicode__())

        def test_workflow_lifecycle(self):
            """
            Makes sure the methods in the Workflow model work as expected
            """
            # All new workflows start with status DEFINITION - from the fixtures
            w = Workflow.objects.get(id=1)
            self.assertEquals(Workflow.DEFINITION, w.status)

            # Activate the workflow
            w.activate()
            self.assertEquals(Workflow.ACTIVE, w.status)

            # Retire it.
            w.retire()
            self.assertEquals(Workflow.RETIRED, w.status)

        def test_workflow_is_valid(self):
            """
            Makes sure that the validation for a workflow works as expected
            """
            # from the fixtures
            w = Workflow.objects.get(id=1)
            self.assertEquals(Workflow.DEFINITION, w.status)

            # make sure the workflow contains exactly one start state
            # 0 start states
            state1 = State.objects.get(id=1)
            state1.is_start_state=False
            state1.save()
            self.assertEqual(False, w.is_valid())
            self.assertEqual(True, u'There must be only one start state' in w.errors['workflow'])
            state1.is_start_state=True
            state1.save()

            # >1 start states
            state2 = State.objects.get(id=2)
            state2.is_start_state=True
            state2.save()
            self.assertEqual(False, w.is_valid())
            self.assertEqual(True, u'There must be only one start state' in w.errors['workflow'])
            state2.is_start_state=False
            state2.save()

            # make sure we have at least one end state
            # 0 end states
            end_states = w.states.filter(is_end_state=True)
            for state in end_states:
                state.is_end_state=False
                state.save()
            self.assertEqual(False, w.is_valid())
            self.assertEqual(True, u'There must be at least one end state' in w.errors['workflow'])
            for state in end_states:
                state.is_end_state=True
                state.save()
            
            # make sure we don't have any orphan states 
            orphan_state = State(name='orphaned_state', workflow=w)
            orphan_state.save()
            self.assertEqual(False, w.is_valid())
            self.assertEqual(True, orphan_state.id in w.errors['states'])
            msg = u'This state is orphaned. There is no way to get to it given'\
                    ' the current workflow topology.'
            self.assertEqual(True, msg in w.errors['states'][orphan_state.id])
            orphan_state.delete()

            # make sure we don't have any cul-de-sacs from which one can't
            # escape (re-using an end state for the same effect)
            cul_de_sac = end_states[0]
            cul_de_sac.is_end_state = False
            cul_de_sac.save()
            self.assertEqual(False, w.is_valid())
            self.assertEqual(True, cul_de_sac.id in w.errors['states'])
            msg = u'This state is a dead end. It is not marked as an end state'\
                    ' and there is no way to exit from it.'
            self.assertEqual(True, msg in w.errors['states'][cul_de_sac.id])
            cul_de_sac.is_end_state = True
            cul_de_sac.save()

            # make sure transition's roles are a subset of the roles associated
            # with the transition's from_state (otherwise you'll have a
            # transition that none of the participants for a state can make use
            # of)
            role = Role.objects.get(id=2)
            transition = Transition.objects.get(id=10)
            transition.roles.clear()
            transition.roles.add(role)
            self.assertEqual(False, w.is_valid())
            self.assertEqual(True, transition.id in w.errors['transitions'])
            msg = u'This transition is not navigable because none of the'\
                ' roles associated with the parent state have permission to'\
                ' use it.'
            self.assertEqual(True, msg in w.errors['transitions'][transition.id])

            # so all the potential pitfalls have been vaidated. Lets make sure
            # we *can* validate it as expected.
            transition.roles.clear()
            admin_role = Role.objects.get(id=1)
            staff_role = Role.objects.get(id=3)
            transition.roles.add(admin_role)
            transition.roles.add(staff_role)
            self.assertEqual(True, w.is_valid())
            self.assertEqual([], w.errors['workflow'])
            self.assertEqual({}, w.errors['states'])
            self.assertEqual({}, w.errors['transitions'])

        def test_workflow_has_errors(self):
            """
            Ensures that has_errors() returns the appropriate response for all
            possible circumstances
            """
            # Some housekeepeing
            w = Workflow.objects.get(id=1)
            u = User.objects.get(id=1)
            w.activate()
            w2 = w.clone(u)

            # A state with no errors
            state1 = State.objects.get(id=1)
            w.is_valid()
            self.assertEqual([], w.has_errors(state1))

            # A state with errors
            state1.is_start_state = False
            state1.save()
            w.is_valid()
            msg = u'This state is orphaned. There is no way to get to it given'\
                    ' the current workflow topology.'
            self.assertEqual([msg], w.has_errors(state1))
            
            # A transition with no errors
            transition = Transition.objects.get(id=10)
            w.is_valid()
            self.assertEqual([], w.has_errors(transition))

            # A transition with errors
            role = Role.objects.get(id=2)
            transition.roles.clear()
            transition.roles.add(role)
            w.is_valid()
            msg = u'This transition is not navigable because none of the'\
                ' roles associated with the parent state have permission to'\
                ' use it.'
            self.assertEqual([msg], w.has_errors(transition))

            # A state not associated with the workflow
            state2 = w2.states.all()[0]
            state2.is_start_state = False
            state2.save()
            w.is_valid()
            # The state is a problem state but isn't anything to do with the
            # workflow w
            self.assertEqual([], w.has_errors(state2))

            # A transition not associated with the workflow
            transition2 = w2.transitions.all()[0]
            transition2.roles.clear()
            w.is_valid()
            # The transition has a problem but isn't anything to do with the
            # workflow w
            self.assertEqual([], w.has_errors(transition2))

            # Something not either a state or transition (e.g. a string)
            w.is_valid()
            self.assertEqual([], w.has_errors("Test"))

        def test_workflow_activate_validation(self):
            """
            Makes sure that the appropriate validation of a workflow happens
            when the activate() method is called
            """
            # from the fixtures
            w = Workflow.objects.get(id=1)
            self.assertEquals(Workflow.DEFINITION, w.status)

            # make sure only workflows in definition can be activated
            w.status=Workflow.ACTIVE
            w.save()
            try:
                w.activate()
            except Exception, instance:
                self.assertEqual(u'Only workflows in the "definition" state may'\
                        ' be activated', instance.args[0]) 
            else:
                self.fail('Exception expected but not thrown')
            w.status=Workflow.DEFINITION
            w.save()

            # Lets make sure the workflow is validated before being activated by
            # making sure the workflow in not valid
            state1 = State.objects.get(id=1)
            state1.is_start_state=False
            state1.save()
            try:
                w.activate()
            except Exception, instance:
                self.assertEqual(u"Cannot activate as the workflow doesn't"\
                        " validate.", instance.args[0])
            else:
                self.fail('Exception expected but not thrown')
            state1.is_start_state=True
            state1.save()
            
            # so all the potential pitfalls have been validated. Lets make sure
            # we *can* approve it as expected.
            w.activate()
            self.assertEqual(Workflow.ACTIVE, w.status)

        def test_workflow_retire_validation(self):
            """
            Makes sure that the appropriate state is set against a workflow when
            this method is called
            """
            w = Workflow.objects.get(id=1)
            w.retire()
            self.assertEqual(Workflow.RETIRED, w.status)

        def test_workflow_clone(self):
            """
            Makes sure we can clone a workflow correctly.
            """
            # We can't clone workflows that are in definition because they might
            # not be "correct" (see the validation that happens when activate()
            # method is called
            u = User.objects.get(id=1)
            w = Workflow.objects.get(id=1)
            try:
                w.clone(u)
            except Exception, instance:
                self.assertEqual(u'Only active or retired workflows may be'\
                        ' cloned', instance.args[0])
            else:
                self.fail('Exception expected but not thrown')
            w.activate()
            clone = w.clone(u)
            self.assertEqual(Workflow.DEFINITION, clone.status)
            self.assertEqual(u, clone.created_by)
            self.assertEqual(w, clone.cloned_from)
            self.assertEqual(w.name, clone.name)
            self.assertEqual(w.description, clone.description)
            # Lets check we get the right number of states, transitions and
            # events
            self.assertEqual(w.transitions.all().count(),
                    clone.transitions.all().count())
            self.assertEqual(w.states.all().count(), clone.states.all().count())
            self.assertEqual(w.events.all().count(), clone.events.all().count())

        def test_state_deadline(self):
            """
            Makes sure we get the right result from the deadline() method in the
            State model
            """
            w = Workflow.objects.get(id=1)
            s = State(
                    name='test',
                    workflow=w
                    )
            s.save()

            # Lets make sure the default is correct
            self.assertEquals(None, s.deadline())

            # Changing the unit of time measurements mustn't change anything
            s.estimation_unit = s.HOUR
            s.save()
            self.assertEquals(None, s.deadline())

            # Only when we have a positive value in the estimation_value field
            # should a deadline be returned
            s._today = lambda : datetime.datetime(2000, 1, 1, 0, 0, 0)

            # Seconds
            s.estimation_unit = s.SECOND
            s.estimation_value = 1
            s.save()
            expected = datetime.datetime(2000, 1, 1, 0, 0, 1)
            actual = s.deadline()
            self.assertEquals(expected, actual)

            # Minutes
            s.estimation_unit = s.MINUTE
            s.save()
            expected = datetime.datetime(2000, 1, 1, 0, 1, 0)
            actual = s.deadline()
            self.assertEquals(expected, actual)

            # Hours
            s.estimation_unit = s.HOUR
            s.save()
            expected = datetime.datetime(2000, 1, 1, 1, 0)
            actual = s.deadline()
            self.assertEquals(expected, actual)

            # Days
            s.estimation_unit = s.DAY
            s.save()
            expected = datetime.datetime(2000, 1, 2)
            actual = s.deadline()
            self.assertEquals(expected, actual)
            
            # Weeks 
            s.estimation_unit = s.WEEK
            s.save()
            expected = datetime.datetime(2000, 1, 8)
            actual = s.deadline()
            self.assertEquals(expected, actual)

        def test_state_unicode(self):
            """
            Makes sure we get the right result from the __unicode__() method in
            the State model
            """
            w = Workflow.objects.get(id=1)
            s = State(
                    name='test',
                    workflow=w
                    )
            s.save()
            self.assertEqual(u'test', s.__unicode__())

        def test_transition_unicode(self):
            """
            Makes sure we get the right result from the __unicode__() method in
            the Transition model
            """
            tr = Transition.objects.get(id=1)
            self.assertEqual(u'Proceed to state 2', tr.__unicode__())

        def test_event_unicode(self):
            """
            Makes sure we get the right result from the __unicode__() method in
            the Event model
            """
            e = Event.objects.get(id=1)
            self.assertEqual(u'Important meeting', e.__unicode__())

        def test_event_type_unicode(self):
            """
            Make sure we get the name of the event type
            """
            et = EventType.objects.get(id=1)
            self.assertEquals(u'Meeting', et.__unicode__())

        def test_workflowactivity_current_state(self):
            """
            Check we always get the latest state (or None if the WorkflowActivity
            hasn't started navigating a workflow
            """
            w = Workflow.objects.get(id=1)
            u = User.objects.get(id=1)
            r = Role.objects.get(id=1)
            wa = WorkflowActivity(workflow=w, created_by=u)
            wa.save()
            p = Participant(user=u, workflowactivity=wa)
            p.save()
            p.roles.add(r)
            # We've not started the workflow yet so make sure we don't get
            # anything back
            self.assertEqual(None, wa.current_state())
            wa.start(p)
            # We should be in the first state
            s1 = State.objects.get(id=1) # From the fixtures
            current_state = wa.current_state()
            # check we have a good current state
            self.assertNotEqual(None, current_state)
            self.assertEqual(s1, current_state.state)
            self.assertEqual(p, current_state.participant)
            # Lets progress the workflow and make sure the *latest* state is the
            # current state
            tr = Transition.objects.get(id=1)
            wa.progress(tr, u)
            s2 = State.objects.get(id=2)
            current_state = wa.current_state()
            self.assertEqual(s2, current_state.state)
            self.assertEqual(tr, current_state.transition)
            self.assertEqual(p, current_state.participant)

        def test_workflowactivity_start(self):
            """
            Make sure the method works in the right way for all possible
            situations
            """
            w = Workflow.objects.get(id=1)
            u = User.objects.get(id=1)
            r = Role.objects.get(id=1)
            wa = WorkflowActivity(workflow=w, created_by=u)
            wa.save()
            p = Participant(user=u, workflowactivity=wa)
            p.save()
            p.roles.add(r)
            # Lets make sure we can't start a workflow that has been stopped
            wa.force_stop(p, 'foo')
            try:
                wa.start(u)
            except Exception, instance:
                self.assertEqual(u'Already completed', instance.args[0])
            else:
                self.fail('Exception expected but not thrown')
            wa = WorkflowActivity(workflow=w, created_by=u)
            wa.save()
            p = Participant(user=u, workflowactivity=wa)
            p.save()
            p.roles.add(r)
            # Lets make sure we can't start a workflow activity if there isn't
            # a single start state
            s2 = State.objects.get(id=2)
            s2.is_start_state=True
            s2.save()
            try:
                wa.start(u)
            except Exception, instance:
                self.assertEqual(u'Cannot find single start state', 
                        instance.args[0])
            else:
                self.fail('Exception expected but not thrown')
            s2.is_start_state=False
            s2.save()
            # Lets make sure we *can* start it now we only have a single start
            # state
            wa.start(u)
            # We should be in the first state
            s1 = State.objects.get(id=1) # From the fixtures
            current_state = wa.current_state()
            # check we have a good current state
            self.assertNotEqual(None, current_state)
            self.assertEqual(s1, current_state.state)
            self.assertEqual(p, current_state.participant)
            # Lets make sure we can't "start" the workflowactivity again
            try:
                wa.start(u)
            except Exception, instance:
                self.assertEqual(u'Already started', instance.args[0])
            else:
                self.fail('Exception expected but not thrown')

        def test_workflowactivity_progress(self):
            """
            Make sure the transition from state to state is validated and
            recorded in the correct way.
            """
            # Some housekeeping...
            w = Workflow.objects.get(id=1)
            u = User.objects.get(id=1)
            r = Role.objects.get(id=1)
            wa = WorkflowActivity(workflow=w, created_by=u)
            wa.save()
            self.assertEqual(None, wa.completed_on)
            p = Participant(user=u, workflowactivity=wa)
            p.save()
            p.roles.add(r)
            # Validation checks:
            # 1. The workflow activity must be started
            tr5 = Transition.objects.get(id=5)
            try:
                wa.progress(tr5, u)
            except Exception, instance:
                self.assertEqual(u'Start the workflow before attempting to'\
                        ' transition', instance.args[0])
            else:
                self.fail('Exception expected but not thrown')
            wa.start(p)
            # 2. The transition's from_state *must* be the current state
            try:
                wa.progress(tr5, u)
            except Exception, instance:
                self.assertEqual(u'Transition not valid (wrong parent)', 
                        instance.args[0])
            else:
                self.fail('Exception expected but not thrown')
            # Lets test again with a valid transition with the correct
            # from_state
            tr1 = Transition.objects.get(id=1)
            wa.progress(tr1, u)
            s2 = State.objects.get(id=2)
            self.assertEqual(s2, wa.current_state().state)
            # 3. All mandatory events for the state are in the worklow history
            # (s2) has a single mandatory event associated with it
            tr2 = Transition.objects.get(id=2)
            try:
                wa.progress(tr2, u)
            except Exception, instance:
                self.assertEqual(u'Transition not valid (mandatory event'\
                        ' missing)', instance.args[0])
            else:
                self.fail('Exception expected but not thrown')
            # Lets log the event and make sure we *can* progress
            e = Event.objects.get(id=1)
            wa.log_event(e, u)
            # Lets progress with a custom note
            wa.progress(tr2, u, 'A Test')
            s3 = State.objects.get(id=3)
            self.assertEqual(s3, wa.current_state().state)
            self.assertEqual('A Test', wa.current_state().note)
            # 4. The participant has the correct role to make the transition
            r2 = Role.objects.get(id=2)
            p.roles.clear()
            p.roles.add(r2)
            tr4 = Transition.objects.get(id=4) # won't work with r2
            try:
                wa.progress(tr4, u)
            except Exception, instance:
                self.assertEqual(u'Participant has insufficient authority to'\
                        ' use the specified transition', instance.args[0])
            else:
                self.fail('Exception expected but not thrown')
            # We have the good transition so make sure everything is logged in
            # the workflow history properly
            p.roles.add(r)
            s5 = State.objects.get(id=5)
            wh = wa.progress(tr4, u)
            self.assertEqual(s5, wh.state)
            self.assertEqual(tr4, wh.transition)
            self.assertEqual(p, wh.participant)
            self.assertEqual(tr4.name, wh.note)
            self.assertNotEqual(None, wh.deadline)
            self.assertEqual(WorkflowHistory.TRANSITION, wh.log_type)
            # Get to the end of the workflow and check that by progressing to an
            # end state the workflow activity is given a completed on timestamp
            tr8 = Transition.objects.get(id=8)
            tr10 = Transition.objects.get(id=10)
            tr11 = Transition.objects.get(id=11)
            wa.progress(tr8, u)
            # Lets log a generic event
            e2 = Event.objects.get(id=4)
            wa.log_event(e2, u, "A generic event has taken place")
            wa.progress(tr10, u)
            wa.progress(tr11, u)
            self.assertNotEqual(None, wa.completed_on)

        def test_workflowactivity_log_event(self):
            """
            Make sure the logging of events for a workflow is validated and
            recorded in the correct way.
            """
            # Some housekeeping...
            w = Workflow.objects.get(id=1)
            u = User.objects.get(id=1)
            r = Role.objects.get(id=1)
            wa = WorkflowActivity(workflow=w, created_by=u)
            wa.save()
            p = Participant(user=u, workflowactivity=wa)
            p.save()
            p.roles.add(r)
            # Lets make sure we can log a generic event prior to starting the
            # workflow activity
            ge = Event.objects.get(id=4)
            wh = wa.log_event(ge, u, 'Another test')
            self.assertEqual(None, wh.state)
            self.assertEqual(ge, wh.event)
            self.assertEqual(p, wh.participant)
            self.assertEqual('Another test', wh.note)
            self.assertEqual(None, wh.deadline)
            wa.start(p)
            # Validation checks:
            # 1. Make sure the event we're logging is for the appropriate
            # workflow
            wf2 = Workflow(name="dummy", created_by=u)
            wf2.save()
            dummy_state = State(name="dummy", workflow=wf2)
            dummy_state.save()
            dummy_event = Event(
                    name="dummy event", 
                    workflow=wf2, 
                    state=dummy_state
                    )
            dummy_event.save()
            try:
                wa.log_event(dummy_event, u)
            except Exception, instance:
                self.assertEqual(u'The event is not associated with the'\
                        ' workflow for the WorkflowActivity', instance.args[0])
            else:
                self.fail('Exception expected but not thrown')
            # 2. Make sure the participant has the correct role to log the event
            # (Transition to second state where we have an appropriate event
            # already specified)
            tr1 = Transition.objects.get(id=1)
            wa.progress(tr1, u)
            e1 = Event.objects.get(id=1)
            p.roles.clear()
            try:
                wa.log_event(e1, u)
            except Exception, instance:
                self.assertEqual(u'The participant is not associated with the'\
                        ' specified event', instance.args[0])
            else:
                self.fail('Exception expected but not thrown')
            p.roles.add(r)
            # Try again but with the right profile
            wa.log_event(e1, u)
            # 3. Make sure, if the event is mandatory it can only be logged
            # whilst in the correct state
            e2 = Event.objects.get(id=2)
            e2.is_mandatory = True
            e2.save()
            try:
                wa.log_event(e2, u)
            except Exception, instance:
                self.assertEqual(u'The mandatory event is not associated with'\
                        ' the current state', instance.args[0])
            else:
                self.fail('Exception expected but not thrown')
            # Save a good event instance and check everything is logged in the
            # workflow history properly
            tr2 = Transition.objects.get(id=2)
            s3 = State.objects.get(id=3)
            wa.progress(tr2, u)
            wh = wa.log_event(e2, u)
            self.assertEqual(s3, wh.state)
            self.assertEqual(e2, wh.event)
            self.assertEqual(p, wh.participant)
            self.assertEqual(e2.name, wh.note)
            self.assertEqual(WorkflowHistory.EVENT, wh.log_type)
            # Lets log a second event of this type and make sure we handle the
            # bespoke note
            wh = wa.log_event(e2, u, 'A Test')
            self.assertEqual(s3, wh.state)
            self.assertEqual(e2, wh.event)
            self.assertEqual(p, wh.participant)
            self.assertEqual('A Test', wh.note)
            # Finally, make sure we can log a generic event (not associated with
            # a particular workflow, state or set of roles)
            e3 = Event.objects.get(id=4)
            wh = wa.log_event(e3, u, 'Another test')
            self.assertEqual(s3, wh.state)
            self.assertEqual(e3, wh.event)
            self.assertEqual(p, wh.participant)
            self.assertEqual('Another test', wh.note)

        def test_workflowactivity_add_comment(self):
            """
            Make sure we can add comments to the workflow history via the
            WorkflowActivity instance
            """
            w = Workflow.objects.get(id=1)
            u = User.objects.get(id=1)
            r = Role.objects.get(id=1)
            wa = WorkflowActivity(workflow=w, created_by=u)
            wa.save()
            p = Participant(user=u, workflowactivity=wa)
            p.save()
            p.roles.add(r)
            # Test we can add a comment to an un-started workflow
            wh = wa.add_comment(u, 'test')
            self.assertEqual('test', wh.note)
            self.assertEqual(p, wh.participant)
            self.assertEqual(WorkflowHistory.COMMENT, wh.log_type)
            self.assertEqual(None, wh.state)
            # Start the workflow and add a comment
            wa.start(p)
            s = State.objects.get(id=1)
            wh = wa.add_comment(u, 'test2')
            self.assertEqual('test2', wh.note)
            self.assertEqual(p, wh.participant)
            self.assertEqual(WorkflowHistory.COMMENT, wh.log_type)
            self.assertEqual(s, wh.state)
            # Add a comment from an unknown user
            u2 = User.objects.get(id=2)
            wh = wa.add_comment(u2, 'test3')
            self.assertEqual('test3', wh.note)
            self.assertEqual(u2, wh.participant.user)
            self.assertEqual(0, len(wh.participant.roles.all()))
            self.assertEqual(WorkflowHistory.COMMENT, wh.log_type)
            self.assertEqual(s, wh.state)
            # Make sure we can't add an empty comment
            try:
                wa.add_comment(u, '')
            except Exception, instance:
                self.assertEqual(u'Cannot add an empty comment', instance.args[0])
            else:
                self.fail('Exception expected but not thrown')

        def test_workflowactivity_assign_role(self):
            """
            Makes sure the appropriate things happen when a role is assigned to
            a user for a workflow activity
            """
            w = Workflow.objects.get(id=1)
            u = User.objects.get(id=1)
            r = Role.objects.get(id=1)
            wa = WorkflowActivity(workflow=w, created_by=u)
            wa.save()
            p = Participant(user=u, workflowactivity=wa)
            p.save()
            p.roles.add(r)
            # Lets test we can assign a role *before* the workflow activity is
            # started
            u2 = User.objects.get(id=2)
            wh = wa.assign_role(u, u2, r)
            self.assertEqual('Role "Administrator" assigned to test_manager',
                    wh.note)
            self.assertEqual(p, wh.participant)
            self.assertEqual(WorkflowHistory.ROLE, wh.log_type)
            self.assertEqual(None, wh.state)
            self.assertEqual(None, wh.deadline)
            # Lets start the workflow activity and try again
            wa.start(p)
            s = State.objects.get(id=1)
            r2 = Role.objects.get(id=2)
            wh = wa.assign_role(u2, u, r2)
            self.assertEqual('Role "Manager" assigned to test_admin', wh.note)
            self.assertEqual(u2, wh.participant.user)
            self.assertEqual(WorkflowHistory.ROLE, wh.log_type)
            self.assertEqual(s, wh.state)

        def test_workflowactivity_remove_role(self):
            """
            Makes sure the appropriate things happen when a role is removed from
            a user for a workflow activity
            """
            w = Workflow.objects.get(id=1)
            u = User.objects.get(id=1)
            r = Role.objects.get(id=1)
            wa = WorkflowActivity(workflow=w, created_by=u)
            wa.save()
            p = Participant(user=u, workflowactivity=wa)
            p.save()
            p.roles.add(r)
            # Lets test we can remove a role *before* the workflow activity is
            # started
            u2 = User.objects.get(id=2)
            p2 = Participant(user=u2, workflowactivity=wa)
            p2.save()
            p2.roles.add(r)
            wh = wa.remove_role(u, u2, r)
            self.assertEqual('Role "Administrator" removed from test_manager',
                    wh.note)
            self.assertEqual(p, wh.participant)
            self.assertEqual(WorkflowHistory.ROLE, wh.log_type)
            self.assertEqual(None, wh.state)
            self.assertEqual(None, wh.deadline)
            # Lets start the workflow activity and try again
            wa.start(p)
            s = State.objects.get(id=1)
            wh = wa.remove_role(u2, u, r)
            self.assertEqual('Role "Administrator" removed from test_admin', wh.note)
            self.assertEqual(u2, wh.participant.user)
            self.assertEqual(WorkflowHistory.ROLE, wh.log_type)
            self.assertEqual(s, wh.state)
            # Lets make sure we return None from trying to remove a role that
            # isn't associated
            p.roles.add(r)
            p2.roles.add(r)
            r2 = Role.objects.get(id=2)
            result = wa.remove_role(u, u2, r2)
            self.assertEqual(None, result)
            # Lets make sure we return None from trying to use a user who isn't
            # a participant
            u3 = User.objects.get(id=3)
            result = wa.remove_role(u, u3, r)
            self.assertEqual(None, result)

        def test_workflowactivity_clear_roles(self):
            """
            Makes sure the appropriate things happen when a user has all roles
            cleared against a workflow activity
            """
            w = Workflow.objects.get(id=1)
            u = User.objects.get(id=1)
            r = Role.objects.get(id=1)
            wa = WorkflowActivity(workflow=w, created_by=u)
            wa.save()
            p = Participant(user=u, workflowactivity=wa)
            p.save()
            p.roles.add(r)
            # Lets test we can clear roles *before* the workflow activity is
            # started
            u2 = User.objects.get(id=2)
            p2 = Participant(user=u2, workflowactivity=wa)
            p2.save()
            p2.roles.add(r)
            wh = wa.clear_roles(u, u2)
            self.assertEqual('All roles removed from test_manager',
                    wh.note)
            self.assertEqual(p, wh.participant)
            self.assertEqual(WorkflowHistory.ROLE, wh.log_type)
            self.assertEqual(None, wh.state)
            self.assertEqual(None, wh.deadline)
            # Lets start the workflow activity and try again
            wa.start(p)
            s = State.objects.get(id=1)
            wh = wa.clear_roles(u2, u)
            self.assertEqual('All roles removed from test_admin', wh.note)
            self.assertEqual(u2, wh.participant.user)
            self.assertEqual(WorkflowHistory.ROLE, wh.log_type)
            self.assertEqual(s, wh.state)
            # Lets make sure we return None from trying to use a user who isn't
            # a participant
            u3 = User.objects.get(id=3)
            result = wa.clear_roles(u, u3)
            self.assertEqual(None, result)

        def test_workflowactivity_disable_participant(self):
            """
            Makes sure a participant in a workflow activity is disabled
            elegantly
            """
            w = Workflow.objects.get(id=1)
            u = User.objects.get(id=1)
            r = Role.objects.get(id=1)
            wa = WorkflowActivity(workflow=w, created_by=u)
            wa.save()
            p = Participant(user=u, workflowactivity=wa)
            p.save()
            p.roles.add(r)
            # Lets test we can disable a participant *before* the workflow 
            # activity is started
            u2 = User.objects.get(id=2)
            p2 = Participant(user=u2, workflowactivity=wa)
            p2.save()
            p2.roles.add(r)
            wh = wa.disable_participant(u, u2, 'test')
            self.assertEqual('Participant test_manager disabled with the'\
                    ' reason: test', wh.note)
            self.assertEqual(p, wh.participant)
            self.assertEqual(WorkflowHistory.ROLE, wh.log_type)
            self.assertEqual(None, wh.state)
            self.assertEqual(None, wh.deadline)
            p2.disabled=False
            p2.save()
            # Lets start the workflow activity and try again
            wa.start(p)
            s = State.objects.get(id=1)
            wh = wa.disable_participant(u, u2, 'test')
            self.assertEqual('Participant test_manager disabled with the'\
                    ' reason: test', wh.note)
            self.assertEqual(u, wh.participant.user)
            self.assertEqual(WorkflowHistory.ROLE, wh.log_type)
            self.assertEqual(s, wh.state)
            # Make sure we return None if the participant is already disabled
            result = wa.disable_participant(u, u2, 'test')
            self.assertEqual(None, result)
            # Lets make sure we must supply a note
            try:
                wa.disable_participant(u, u2, '')
            except Exception, instance:
                self.assertEqual(u'Must supply a reason for disabling a'\
                        ' participant. None given.', instance.args[0])
            else:
                self.fail('Exception expected but not thrown')
            # Lets make sure we return None from trying to disable a user who 
            # isn't a participant
            u3 = User.objects.get(id=3)
            result = wa.disable_participant(u, u3, 'test')
            self.assertEqual(None, result)

        def test_workflowactivity_enable_participant(self):
            """
            Make sure we can re-enable a participant in a workflow activity
            """
            w = Workflow.objects.get(id=1)
            u = User.objects.get(id=1)
            r = Role.objects.get(id=1)
            wa = WorkflowActivity(workflow=w, created_by=u)
            wa.save()
            p = Participant(user=u, workflowactivity=wa)
            p.save()
            p.roles.add(r)
            # Lets test we can disable a participant *before* the workflow 
            # activity is started
            u2 = User.objects.get(id=2)
            p2 = Participant(user=u2, workflowactivity=wa)
            p2.save()
            p2.roles.add(r)
            p2.disabled=True;
            p2.save()
            wh = wa.enable_participant(u, u2, 'test')
            self.assertEqual('Participant test_manager enabled with the'\
                    ' reason: test', wh.note)
            self.assertEqual(p, wh.participant)
            self.assertEqual(WorkflowHistory.ROLE, wh.log_type)
            self.assertEqual(None, wh.state)
            self.assertEqual(None, wh.deadline)
            p2.disabled=True
            p2.save()
            # Lets start the workflow activity and try again
            wa.start(p)
            s = State.objects.get(id=1)
            wh = wa.enable_participant(u, u2, 'test')
            self.assertEqual('Participant test_manager enabled with the'\
                    ' reason: test', wh.note)
            self.assertEqual(u, wh.participant.user)
            self.assertEqual(WorkflowHistory.ROLE, wh.log_type)
            self.assertEqual(s, wh.state)
            # Make sure we return None if the participant is already disabled
            result = wa.enable_participant(u, u2, 'test')
            self.assertEqual(None, result)
            # Lets make sure we must supply a note
            try:
                wa.enable_participant(u, u2, '')
            except Exception, instance:
                self.assertEqual(u'Must supply a reason for enabling a'\
                        ' disabled participant. None given.', instance.args[0])
            else:
                self.fail('Exception expected but not thrown')
            # Lets make sure we return None from trying to disable a user who 
            # isn't a participant
            u3 = User.objects.get(id=3)
            result = wa.enable_participant(u, u3, 'test')
            self.assertEqual(None, result)

        def test_workflowactivity_force_stop(self):
            """
            Make sure a WorkflowActivity is stopped correctly with this method
            """
            # Make sure we can appropriately force_stop an un-started workflow
            # activity
            w = Workflow.objects.get(id=1)
            u = User.objects.get(id=1)
            r = Role.objects.get(id=1)
            wa = WorkflowActivity(workflow=w, created_by=u)
            wa.save()
            p = Participant(user=u, workflowactivity=wa)
            p.save()
            p.roles.add(r)
            wa.force_stop(u, 'foo')
            self.assertNotEqual(None, wa.completed_on)
            self.assertEqual(None, wa.current_state())
            # Lets make sure we can force_stop an already started workflow
            # activity
            wa = WorkflowActivity(workflow=w, created_by=u)
            wa.save()
            p = Participant(user=u, workflowactivity=wa)
            p.save()
            p.roles.add(r)
            wa.start(u)
            wa.force_stop(u, 'foo')
            self.assertNotEqual(None, wa.completed_on)
            wh = wa.current_state()
            self.assertEqual(p, wh.participant)
            self.assertEqual(u'Workflow forced to stop! Reason given: foo',
                    wh.note)
            self.assertEqual(None, wh.deadline)

        def test_participant_unicode(self):
            """
            Make sure the __unicode__() method returns the correct string in
            both enabled / disabled states
            """
            w = Workflow.objects.get(id=1)
            u = User.objects.get(id=1)
            r = Role.objects.get(id=1)
            r2 = Role.objects.get(id=2)
            wa = WorkflowActivity(workflow=w, created_by=u)
            wa.save()
            p = Participant(user=u, workflowactivity=wa)
            p.save()
            p.roles.add(r)
            self.assertEquals(u'test_admin - Administrator', p.__unicode__())
            p.roles.add(r2)
            self.assertEquals(u'test_admin - Administrator, Manager', p.__unicode__())
            p.disabled = True
            p.save()
            self.assertEquals(u'test_admin - Administrator, Manager (disabled)', p.__unicode__())
            p.roles.clear()
            self.assertEquals(u'test_admin (disabled)', p.__unicode__())

        def test_workflow_history_unicode(self):
            """
            Make sure the __unicode__() method returns the correct string for
            workflow history items
            """
            w = Workflow.objects.get(id=1)
            u = User.objects.get(id=1)
            r = Role.objects.get(id=1)
            wa = WorkflowActivity(workflow=w, created_by=u)
            wa.save()
            p = Participant(user=u, workflowactivity=wa)
            p.save()
            p.roles.add(r)
            wh = wa.start(p)
            self.assertEqual(u'Started workflow created by test_admin - Administrator', wh.__unicode__())


########NEW FILE########
__FILENAME__ = test_views
# -*- coding: UTF-8 -*-
"""
View tests for Workflows 

Author: Nicholas H.Tollervey

"""
# python
import datetime

# django
from django.test.client import Client
from django.test import TestCase
from django.conf import settings

# project
from workflow.views import *
from workflow.models import Workflow

class ViewTestCase(TestCase):
        """
        Testing Views 
        """
        # Make sure the URLs play nice
        urls = 'workflow.urls'
        # Reference fixtures here
        fixtures = ['workflow_test_data']

        def test_get_dotfile(self):
            """
            Make sure we get the expected .dot file given the current state of
            the fixtures
            """
            w = Workflow.objects.get(id=1)
            result = get_dotfile(w)
            for state in w.states.all():
                # make sure we find references to the states
                self.assertEqual(True, result.find("state%d"%state.id) > -1)
                self.assertEqual(True, result.find(state.name) > -1)
            for transition in w.transitions.all():
                # make sure we find references to the transitions
                search = 'state%d -> state%d [label="%s"];'%(
                        transition.from_state.id,
                        transition.to_state.id,
                        transition.name)
                self.assertEqual(True, result.find(search) > -1)
            # Make sure we have START: and END:
            self.assertEqual(True, result.find("START:") > -1)
            self.assertEqual(True, result.find("END:") > -1)

        def test_dotfile(self):
            """
            Makes sure a GET to the url results in the .dot file as an
            attachment
            """
            c = Client()
            response = c.get('/test_workflow/dotfile/')
            self.assertContains(response, 'A definition for a diagram of the'\
                ' workflow: test workflow')

        def test_graphviz(self):
            """
            Makes sure a GET to the url results in a .png file
            """
            c = Client()
            response = c.get('/test_workflow.png')
            self.assertEqual(200, response.status_code)
            self.assertEqual('image/png', response['Content-Type'])

        def test_graphviz_with_no_graphviz(self):
            """
            Makes sure the graphviz method returns an appropriate exception if
            graphviz path is not specified
            """
            _target = settings._target
            del _target.GRAPHVIZ_DOT_COMMAND
            settings.__setattr__('_target', _target)
            c = Client()
            try:
                response = c.get('/test_workflow.png')
            except Exception, instance:
                self.assertEqual(u"GRAPHVIZ_DOT_COMMAND constant not set in"\
                        " settings.py (to specify the absolute path to"\
                        " graphviz's dot command)", instance.args[0])
            else:
                self.fail('Exception expected but not thrown')

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

urlpatterns = patterns('',
    # get a dotfile for the referenced workflow 
    url(r'^(?P<workflow_slug>\w+)/dotfile/$', 'workflow.views.dotfile', name='dotfile'),
    # get a png image generated by graphviz for the referenced workflow 
    url(r'^(?P<workflow_slug>\w+).png$', 'workflow.views.graphviz', name='graphviz'),
)

########NEW FILE########
__FILENAME__ = views
# -*- coding: UTF-8 -*-

# Python
import subprocess
from os.path import join

# django
from django.template import Context, loader
from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from django.conf import settings

# Workflow app
from workflow.models import Workflow

###################
# Utility functions
###################

def get_dotfile(workflow):
    """
    Given a workflow will return the appropriate contents of a .dot file for 
    processing by graphviz
    """
    c = Context({'workflow': workflow})
    t = loader.get_template('graphviz/workflow.dot')
    return t.render(c)

################
# view functions
################

def dotfile(request, workflow_slug):
    """
    Returns the dot file for use with graphviz given the workflow name (slug) 
    """
    w = get_object_or_404(Workflow, slug=workflow_slug)
    response = HttpResponse(mimetype='text/plain')
    response['Content-Disposition'] = 'attachment; filename=%s.dot'%w.name
    response.write(get_dotfile(w))
    return response

def graphviz(request, workflow_slug):
    """
    Returns a png representation of the workflow generated by graphviz given 
    the workflow name (slug)

    The following constant should be defined in settings.py:

    GRAPHVIZ_DOT_COMMAND - absolute path to graphviz's dot command used to
    generate the image
    """
    if not hasattr(settings, 'GRAPHVIZ_DOT_COMMAND'):
        # At least provide a helpful exception message
        raise Exception("GRAPHVIZ_DOT_COMMAND constant not set in settings.py"\
                " (to specify the absolute path to graphviz's dot command)")
    w = get_object_or_404(Workflow, slug=workflow_slug)
    # Lots of "pipe" work to avoid hitting the file-system
    proc = subprocess.Popen('%s -Tpng' % settings.GRAPHVIZ_DOT_COMMAND,
                shell=True,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                )
    response = HttpResponse(mimetype='image/png')
    response.write(proc.communicate(get_dotfile(w).encode('utf_8'))[0])
    return response

########NEW FILE########
