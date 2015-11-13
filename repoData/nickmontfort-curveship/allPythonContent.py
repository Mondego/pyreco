__FILENAME__ = action_model
'Define categories of Action and their consequences in the World.'

__author__ = 'Nick Montfort'
__copyright__ = 'Copyright 2011 Nick Montfort'
__license__ = 'ISC'
__version__ = '0.5.0.0'
__status__ = 'Development'

import copy
import re

def generator(num):
    'Provides unique, increasing integers.'
    while 1:
        yield num
        num += 1

ACTION_ID = generator(1)

class Action(object):
    'Abstract base class for things done by an agent in the world.'

    def __init__(self, verb, agent, category, **keywords):
        if self.__class__ == Action:
            raise StandardError('Attempt to instantiate abstract base ' +
                                'class action_model.Action')
        self.id = ACTION_ID.next()
        self.verb = verb
        self.agent = agent
        self.cause = self.agent
        self.salience = 0.5
        for i in ['salience', 'template', 'force']:
            if i in keywords:
                setattr(self, i, keywords[i])
        for i in ['behave', 'configure', 'modify', 'sense']:
            setattr(self, i, (category == i))
        self._category = category
        self.preconditions = []
        self.start = None
        self.final = False
        self.failed = []
        self.refusal = None
        self.enlightened = []

    def __str__(self):
        'Describes the action in a one-line string.'
        string = ':' + str(self.id) + ': '
        if self.refusal is not None:
            string += 'Refused '
        elif len(self.failed) > 0:
            string += 'Failed '
        string += self.verb.upper() + ' (' + self._category + ') '
        for i in ['agent', 'direct', 'indirect', 'direction', 'utterance',
                  'preposition', 'modality', 'force', 'manner', 'feature',
                  'old_value', 'new_value', 'old_link', 'old_parent',
                  'new_link', 'new_parent', 'target', 'cause', 'start']:
            if hasattr(self, i):
                string += i + '=' + str(getattr(self, i)) + ' '
        return string[:-1]

    @property
    def category(self):
        'Returns the category (behave, configure, etc.) as a lowercase string.'
        return self._category

    @property
    def end(self):
        "Return the action's end time. All actions have duration 1 now."
        return self.start + 1

    def check_refusal(self, world):
        'If the agent refuses to do the action, update the reason.'
        if (not self.agent == '@cosmos' and 
            hasattr(world.item[self.agent], 'refuses')):
            agent = world.item[self.agent]
            for (wont_do, state, reason) in agent.refuses:
                if self.match_string(wont_do):
                    if type(state) == list:
                        if world.room_of(self.agent) in state: 
                            self.refusal = reason
                            break
                    elif state(world):
                        self.refusal = reason
                        break
            if self.refusal is None:
                if self.verb == 'leave':
                    room = world.room_of(self.agent)
                    if world.can_see(self.agent, str(room)):
                        if room.exit(self.direction) is None:
                            if self.direction not in room.exits:
                                self.refusal = ('[' + self.agent +
                                               '/s] [see/v] no way to do that')
                            else:
                                self.refusal = room.exits[self.direction]
                    else:
                        if self.direction in ['up', 'down']:
                            self.refusal = ('[' + self.agent +
                                            '/s] [find/not/v] any way to ' +
                                            'go [direction]')
            if self.refusal is not None:
                self.refusal = re.sub('\[\*', '[' + self.agent,
                                      self.refusal)

    def match_string(self, event_test):
        'Does the string indicate this action?'
        to_match = event_test.split()
        for i in to_match:
            if re.search(i, str(self)) is None:
                return False
        return True

    def undo(self, world):
        'Make the world as if this action had never happened.'
        self.change(world, False)

    def do(self, world):
        'Perform the action, updating the world.'
        to_be_done = []
        aware = set()
        self.start = world.ticks
        for actor in world.concept:
            # Did the actor see the agent or direct object (if any) beforehand?
            # If the actor performed the action, the actor is aware of it.
            if (actor == self.agent or world.can_see(actor, self.agent) or
                (hasattr(self, 'direct') and 
                 world.can_see(actor, self.direct))):
                aware.add(actor)
        self.check_refusal(world)
        if self.refusal is None:
            self.check_preconditions(world)
            can_respond = world.respondents(self)
            if len(self.failed) == 0:
                for tag in can_respond:
                    if world.item[tag].prevent(world, self):
                        self.failed.append(['prevented_by', tag])
            if len(self.failed) == 0:
                for tag in can_respond:
                    to_be_done += world.item[tag].react(world, self)
                self.change(world)
                if hasattr(self, 'entails'):
                    to_be_done += self.entails(world)
            else:
                for tag in can_respond:
                    to_be_done += world.item[tag].react_to_failed(world, self)
        for actor in world.concept:
            # Did the actor see the agent at the end of the action, for
            # instance, if the agent entered a room?
            if world.can_see(actor, self.agent):
                aware.add(actor)
        for actor in aware:
            world.concept[actor].act[self.id] = copy.deepcopy(self)
        world.act[self.id] = self
        return to_be_done

    def moved_somewhere_different(self, actor):
        'Tells whether this action caused the actor to move elsewhere.'
        return (self.configure and self.direct == actor and 
                not self.old_parent == self.new_parent)

    def change(self, world, making_change=True):
        'Alter the world. Only Modify and Configure actions do it.'
        pass

    def check_allowed(self, condition, world):
        'Does the "allowed" rule of the parent let the Item become a child?'
        head, tag, link, parent = condition                
        reason = None
        # First, the Item cannot be a room; rooms can only be 
        # children of @cosmos.
        if world.item[tag].room:
            reason = 'rooms_cannot_move'
        # Next, the Item can't be made the child of itself or
        # of any descendant of itself.
        elif tag in [parent] + world.ancestors(parent):
            reason = 'not_own_descendant' 
        # Next, if the Item is an amount of Substance (liquid, 
        # powder, etc.), there are different cases.
        elif world.item[tag].substance:
            substance = tag.partition('_')[0]
            # 'in' works if the amount is being placed in a 
            # vessel, or if a source is being replenished, or if
            # the amount is being moved to the substance item.
            if link == 'in':
                if not ((world.item[parent].substance and
                         parent == substance) or
                        (hasattr(world.item[parent], 'source') and
                         world.item[parent].source == substance) or
                        (hasattr(world.item[parent], 'vessel') and
                         len(world.item[parent].children) == 0)):
                    reason = 'substance_contained'
            # 'of' does not work; Substances cannot be held by
            # themselves, without vessels.
            elif link == 'of':
                reason = 'substance_contained'
            # There is no case for 'on' -- it falls through to success.
            # 'on' generally works -- an amount can be poured
            # onto anything. A Configure action will be entailed
            # immediately and the amount will be moved to the root
            # Substance Item.
        # Check the Item's own allowed rule:
        elif not world.item[parent].allowed(tag, link, world):
            reason = head + "_" + link
        # Finally, if there have been no other failures, continue
        # to test to see if the parent, with this new child,
        # is still allowed in the grandparent, and so on up the
        # tree. This is done for now rather expensively. A copy
        # of the world is made and, in it, the item is added as a
        # child of the new parent. Then, the testing proceeds.
        elif reason is None and not world.item[parent].parent == '@cosmos':
            met = True
            test = copy.deepcopy(world)
            test.item[parent].add_child(link, tag)
            met &= test.item[parent].allowed(tag, link, test)
            while met and not parent == '@cosmos':
                tag = parent
                parent = test.item[tag].parent
                link = test.item[tag].link
                met &= test.item[parent].allowed(tag, link, test)
            if not met:
                reason = head + '_' + link
        return reason

    def check_preconditions(self, world):
        'Determine if any of the preconditions fail, and why.'
        for condition in self.pre(world):
            failure = []
            head = condition[0]
            if head == 'allowed':
                reason = self.check_allowed(condition, world)
                if reason is not None:
                    failure.append([reason, agent, tag])
            elif head[:10] == 'can_access':
                _, agent, tag_list = condition
                met = False
                accessible_tags = world.accessible(agent)
                for tag in tag_list:
                    if tag in accessible_tags:
                        met = True
                if not met:
                    failure.append(condition)
            elif head == 'can_see':
                _, agent, tag = condition
                reason = world.prevents_sight(agent, tag)
                if reason is not None:
                    failure.append([reason, agent, tag])
            elif head == 'configure_to_different':
                _, child, link, parent = condition
                if (world.item[child].link == link and
                    world.item[child].parent == parent):
                    failure.append(condition)
            elif head == 'exit_exists':
                _, tag, direction = condition
                if direction not in world.room_of(tag).exits:
                    failure.append(condition)
            elif head == 'has_feature':
                _, tag, feature = condition
                if not hasattr(world.item[tag], feature):
                    failure.append(condition)
            elif head == 'has_value':
                _, tag, feature, value = condition
                if (hasattr(world.item[tag], feature) and
                    not getattr(world.item[tag], feature) == value):
                    failure.append(condition)
            elif head == 'modify_to_different':
                _, tag, feature, value = condition
                if (hasattr(world.item[tag], feature) and
                    getattr(world.item[tag], feature) == value):
                    failure.append(condition)
            elif head == 'never':
                failure.append([head + '_' + condition[1]])
            elif head == 'parent_is':
                _, child, link, parent = condition
                if (not world.item[child].link == link and
                    not world.item[child].parent == parent):
                    failure.append(condition)
            self.preconditions.append(((len(failure) == 0), condition))
            self.failed += failure

    def show(self):
        'Return verb, agent, cause, preconditions, type, any postcondition.'

        string = '\n'
        for (met, condition) in self.preconditions:
            if not type(condition) == str:
                condition = ' '.join(str(pre_part) for pre_part in condition)
            string += ['#####> ', '/ / /  '][met] + condition + '\n'
        string += str(self) + '\n'
        if hasattr(self, 'post'):
            success = (len(self.failed) == 0) and self.refusal is None
            string += [' ##### ', r'\ \ \  '][success]
            string += ' '.join(str(post_part) for post_part in self.post())
            string += '\n'
        return string

class Behave(Action):
    'An action that itself changes nothing, e.g., jumping up and down.'

    def __init__(self, verb, agent, **keywords):
        # Behave actions may have 'direct' 'indirect' 'direction' and/or 'utterance'
        for i in ['direct', 'indirect', 'target', 'direction', 'utterance']:
            if i in keywords:
                setattr(self, i, keywords[i])
                del keywords[i]
        self.force = 0.2
        Action.__init__(self, verb, agent, 'behave', **keywords)

    def pre(self, _):
        """Preconditions for Behave:

        The agent must be able to access all objects. If trying to consume
        food or drink, it must be consumable. If trying to leave, an exit
        must exist."""
        pre_list = []
        if hasattr(self, 'direct'):
            pre_list.append(('can_access_direct', self.agent, [self.direct]))
        if hasattr(self, 'indirect'):
            pre_list.append(('can_access_indirect', self.agent,
                             [self.indirect]))
        if hasattr(self, 'target'):
            pre_list.append(('can_see', self.agent, self.target))
        if self.verb in ['drink', 'eat']:
            pre_list.append(('has_feature', self.direct, 'consumable'))
        if self.verb == 'leave':
            pre_list.append(('exit_exists', self.agent, self.direction))
        return pre_list

    def entails(self, world):
        """Entailed Actions for Behave:

        Configure the actor to a new Room after leaving, remove food after 
        eating."""
        actions = []
        if len(self.failed) > 0:
            return actions
        # When an actor leaves in direction that is an exit, the Behave
        # action entails a new action: A Configure action that moves the actor 
        # to the new room or through the door.
        room = world.room_of(self.agent)
        if self.verb == 'leave' and room.exit(self.direction) is not None:
            goal = room.exits[self.direction]
            link = None
            if goal is not None and world.item[goal].door:
                link = 'through'
            else:
                link = 'in'
            new = Configure('enter', self.agent,
                            template='[agent/s] [arrive/v]',
                            direct=self.agent, new=(link, goal), salience=0.1)
            actions.append(new)
        if self.verb in ['drink', 'eat']:
            if hasattr(self, 'direct'):
                to_be_consumed = self.direct
            else:
                _, to_be_consumed = world.item[self.indirect].children[0]
            if world.item[to_be_consumed].substance:
                new_parent = ('in', to_be_consumed.partition('_')[0])
            else:
                new_parent = ('of', '@cosmos')
            actions.append(Configure('polish_off', '@cosmos', 
                                     direct=to_be_consumed,
                                     new=new_parent, salience=0))
        return actions

class Configure(Action):
    'An action that repositions an item in the item tree.'

    def __init__(self, verb, agent, **keywords):
        # Configure Actions must have 'direct' and 'new'.
        self.direct = keywords['direct']
        del keywords['direct']
        self.new_link = keywords['new'][0]
        self.new_parent = keywords['new'][1]
        del keywords['new']
        # 'old' is optional; if missing, any initial link and parent are fine.
        if 'old' in keywords:
            self.old_link = keywords['old'][0]
            self.old_parent = keywords['old'][1]
            del keywords['old']
        self.force = 0.2
        Action.__init__(self, verb, agent, 'configure', **keywords)

    def set_old_if_unset(self, world):
        'Set old_link and old_parent if they have been left off.'
        if not hasattr(self, 'old_link') and not hasattr(self, 'old_parent'):
            self.old_link = world.item[self.direct].link
            self.old_parent = world.item[self.direct].parent

    def change(self, world, making_change=True):
        'Put the item in the new (or old) arrangement in the tree.'
        self.set_old_if_unset(world)
        # If the Action failed, it itself had no consequence in the world.
        # In this case, there is nothing to do or reverse. However, it's
        # necessary to set the old_link and old_parent in the previous step
        # so that they will be there when the failed Action is later checked.
        if len(self.failed) > 0:
            return
        seen_by = {}
        if making_change:
            for actor in world.concept:
                seen_by[actor] = world.can_see(actor, self.direct)
                if (actor in [self.agent, self.direct] or
                    world.can_see(actor, self.direct)):
                    # Before the Action, the Actor can see the Item.
                    # Update the Item's departure from the "from" Item.
                    new_from = copy.deepcopy(world.item[self.old_parent])
                    new_from.remove_child(self.old_link, self.direct,
                                          making_change)
                    if not world.can_see(actor, self.old_parent):
                        new_from.blank()
                    world.transfer(new_from, actor, self.end)
        # Now make the event's changes in the world.
        world.item[self.old_parent].remove_child(self.old_link, self.direct,
                                                 making_change)
        world.item[self.new_parent].add_child(self.new_link, self.direct,
                                              making_change)
        item = world.item[self.direct]
        if making_change:
            item.parent = self.new_parent
            item.link = self.new_link
            for actor in world.concept:
                room_tag = str(world.room_of(actor))
                # If the item disappeared from sight, transfer it out...
                if seen_by[actor] and not world.can_see(actor, self.direct):
                    world.transfer_out(item, actor, self.end)  
                if (actor == self.agent or actor == self.direct or
                    world.can_see(actor, self.direct)):
                    # After the Action, the Actor can see the Item.
                    # Update the Item itself ...
                    world.transfer(item, actor, self.end)
                new_to = copy.deepcopy(world.item[self.new_parent])
                if (actor == self.new_parent or
                    world.can_see(actor, self.new_parent)):
                    # If the "to" Item is visible, update it fully.
                    world.transfer(new_to, actor, self.end)
                    # If the "to" Item is a Room, update other visible Rooms.
                    if new_to.room:
                        for view_tag in new_to.view:
                            if world.can_see(actor, view_tag):
                                world.transfer(world.item[view_tag], actor,
                                               self.end)
                else:
                    if (actor == self.direct and
                        not world.can_see(actor, room_tag)):
                    # Moved into a dark room; blank out the "to" item.
                        new_to.blank()
                        new_to.add_child(self.new_link, self.direct,
                                         making_change)
                        world.transfer(new_to, actor, self.end)
                if (room_tag in world.concept[actor].item and
                    world.concept[actor].item[room_tag].blanked and
                    world.can_see(actor, room_tag)):
                    world.transfer(world.item[room_tag], actor, self.end)
                    look_at = Sense('examine', actor, 
                                    modality='sight', direct=room_tag)
                    look_at.cause = ':' + str(self.id) + ':'
                    self.enlightened.append(look_at)
        else:
            item.parent = self.old_parent
            item.link = self.old_link

    def pre(self, world):
        """Preconditions for Configure:

        Only @cosmos may Configure Items that are part_of others, Doors, or 
        SharedThings. Configure requires a new link and parent. To be configured
        from "in" a container, the container (if it opens) must be open. To go
        "in" or "through" something, that Item must (if it opens) be open. Be
        able to access the Item and (in most cases) the new parent. The Item
        must be allowed in the new parent."""
        pre_list = []
        if not self.agent == '@cosmos':
            if world.item[self.direct].link == 'part_of':
                pre_list.append(('never', 'configure_parts'))
            if world.item[self.direct].door:
                pre_list.append(('never', 'configure_doors'))
            if hasattr(world.item[self.direct], 'sharedthing'):
                pre_list.append(('never', 'configure_sharedthings'))
        pre_list.append(('configure_to_different', self.direct, 
                         self.new_link, self.new_parent))
        if (hasattr(self, 'old_link') and self.old_link == 'in' and 
            hasattr(world.item[self.old_parent], 'open')):
            pre_list.append(('has_value', self.old_parent, 'open', True))
        if (self.new_link in ['in', 'through'] and
            hasattr(world.item[self.new_parent], 'open')):
            pre_list.append(('has_value', self.new_parent, 'open', True))
        if hasattr(self, 'old_link') and hasattr(self, 'old_parent'):
            pre_list.append(('parent_is', self.direct, self.old_link,
                            self.old_parent))
        pre_list.append(('can_access_direct', self.agent, [self.direct]))
        if (not self.new_parent == '@cosmos' and 
            not world.item[self.new_parent].room):
            pre_list.append(('can_access_indirect', self.agent,
                             [self.new_parent]))
        pre_list.append(('allowed', self.direct, self.new_link,
                         self.new_parent))
        return pre_list

    def post(self):
        'Postcondition: Item is in a new arrangement.'
        return ('parent_is', self.direct, self.new_link, self.new_parent)

    def entails(self, world):
        """Entailed Actions for Configure:

        Passing through Doors into new Rooms, looking at new Rooms,
        replenishing a source with a Substance and evaporating/dissipating a
        Substance. Also, looking at newly-lit Items."""
        actions = []
        if len (self.failed) > 0:
            return actions
        if self.new_link == 'through':
            if world.item[self.new_parent].door:
                rooms = world.item[self.new_parent].connects[:]
                rooms.remove(self.old_parent)
                goal = rooms[0] 
                actions.append(Configure('pass_through', self.agent,
                                 template=('[agent/s] [emerge/v] from [' + 
                                           self.new_parent + '/o]'),
                                 new=('in', goal), direct=self.direct))
            else:
                room = self.new_parent
                actions.append(Configure('fall', self.agent,
                                 template='[direct/s] [drop/v] to the ground',
                                 new=('in', room), direct=self.direct))
        elif (world.item[self.direct].actor and
             not self.old_parent == self.new_parent and
             not self.new_parent == '@cosmos'):
            room = self.new_parent
            look_at = Sense('examine', self.direct, 
                            modality='sight', direct=room)
            look_at.cause = ':' + str(self.id) + ':'
            actions.append(look_at)
        elif world.item[self.direct].substance:
            substance = self.direct.partition('_')[0]
            if (self.new_link == 'in' and 
                hasattr(world.item[self.old_parent], 'source') and 
                world.item[self.old_parent].source == substance):
                _, amount = world.item[substance].children[0]
                actions.append(Configure('replenish', '@cosmos',
                                         new=('in', self.old_parent),
                                         direct=amount, salience=0))
            elif (not hasattr(world.item[self.new_parent], 'vessel') and
                  not (hasattr(world.item[self.new_parent], 'source') and
                       world.item[self.new_parent].source == substance) and
                  not self.new_parent == substance):
                # The substance was poured onto something, and needs to vanish.
                actions.append(Configure('vanish', '@cosmos',
                                         new=('in', substance),
                                         template='the [' + self.direct + 
                                                  '/s] [is/v] gone [now]',
                                         direct=self.direct,))
        actions += self.enlightened
        return actions

class Modify(Action):
    "An action that changes some Item's state, the value of a feature."

    def __init__(self, verb, agent, **keywords):
        # Modify actions must have 'direct', 'feature', and 'new'
        self.direct = keywords['direct']
        del keywords['direct']
        self.feature = keywords['feature']
        del keywords['feature']
        self.new_value = keywords['new']
        del keywords['new']
        # 'old' is optional; if missing, any initial value is fine
        if 'old' in keywords:
            self.old_value = keywords['old']
            del keywords['old']
        # 'indirect' is optional, used only when an agent is using a tool
        if 'indirect' in keywords:
            self.indirect = keywords['indirect']
            del keywords['indirect']
        self.force = 0.2
        Action.__init__(self, verb, agent, 'modify', **keywords)

    def change(self, world, making_change=True):
        'Alter the state of the Item to the new (or old) one.'
        # If attributes are missing, indicating that any values work for this 
        # modify event, they are set with using the values in the world at 
        # this point. This allows the event to be undone later with the
        # correct old value put back into place.
        #
        item = world.item[self.direct]
        if not hasattr(self, 'old_value'):
            self.old_value = getattr(item, self.feature)
        # If the event failed, it itself had no consequence in the world.
        # Thus there is nothing to do or reverse.
        if len(self.failed) > 0:
            return
        # Make the change.
        value = (self.old_value, self.new_value)[making_change]
        setattr(item, self.feature, value)
        # Update the item in actors who can perceive this event. Also, check
        # to see if the actor's room became visible and needs an update.
        if making_change:
            for actor in world.concept:
                if (actor in [self.agent, self.direct] or 
                    world.can_see(actor, self.direct)):
                    world.transfer(item, actor, self.end)
                room_tag = str(world.room_of(actor))
                if (room_tag in world.concept[actor].item and
                    world.concept[actor].item[room_tag].blanked and
                    world.can_see(actor, room_tag)):
                    world.transfer(world.item[room_tag], actor, self.end)
                    look_at = Sense('examine', actor, 
                                    modality='sight', direct=room_tag)
                    look_at.cause = ':' + str(self.id) + ':'
                    self.enlightened.append(look_at)

    def pre(self, world):
        """Preconditions for Modify:

        The Item must have the feature being modified. Modify requires a 
        different value. The old value, if specified, must match. The item
        must be accessible by the agent. If opening an Item, it must (if
        lockable) be unlocked. If burning an Item, fire must be accessible.
        If unlocking an Item, the key must be accessible."""
        pre_list = [('has_feature', self.direct, self.feature)]
        pre_list.append(('modify_to_different', self.direct, self.feature,
                        self.new_value))
        if hasattr(self, 'old_value'):
            pre_list.append(('has_value', self.direct, self.feature,
                             self.old_value))
        pre_list.append(('can_access_direct', self.agent, [self.direct]))
        if self.feature == 'open' and self.new_value:
            if hasattr(world.item[self.direct], 'locked'):
                pre_list.append(('has_value', self.direct, 'locked', False))
        if self.feature == 'burnt':
            flames = [i for i in world.item if 
                      hasattr(world.item[i], 'flame') and world.item[i].flame]
            pre_list.append(('can_access_flames', self.agent, flames))
        if self.feature == 'locked':
            if hasattr(world.item[self.direct], 'key'):
                pre_list.append(('can_access_key', self.agent,
                                 [world.item[self.direct].key]))
            else:
                if not self.agent == '@cosmos':
                    pre_list.append(('never', 'permanently_locked'))
        return pre_list

    def post(self):
        "Postcondition: Item's feature has a new value."
        return ('has_value', self.direct, self.feature, str(self.new_value))

    def entails(self, _):
        'Entailed Actions for Modify: Just looking at newly-lit Items.'
        actions = self.enlightened
        return actions


class Sense(Action):
    'A perception that can update a concept.'

    def __init__(self, verb, agent, **keywords):
        # Sense Actions must have 'direct' and 'modality'.
        for i in ['direct', 'modality']:
            setattr(self, i, keywords[i])
            del keywords[i]
        self.force = 0.0
        Action.__init__(self, verb, agent, 'sense', **keywords)

    def pre(self, _):
        """Preconditions for Sense:

        The agent must be able to see the direct object if looking, access it
        if touching."""
        pre_list = []
        if self.modality == 'sight':
            pre_list.append(('can_see', self.agent, self.direct))
        if self.modality == 'touch':
            pre_list.append(('can_access_direct', self.agent, [self.direct]))
        return pre_list


########NEW FILE########
__FILENAME__ = can
'Rules for what can be a child of an item for use in fictions.'

__author__ = 'Nick Montfort'
__copyright__ = 'Copyright 2011 Nick Montfort'
__license__ = 'ISC'
__version__ = '0.5.0.0'
__status__ = 'Development'

def have_any_item(link, tag, world):
    'Mainly to turn off checking in non-interactive plots, not for IF.'
    return True

def not_have_items(link, tag, world):
    'The default; most items are not containers.'
    return False

def have_only_things(tag, link, world):
    'The item being checked and all its descendants must be Things.'
    for i in [tag] + world.descendants(tag):
        if not (world.item[i].thing or world.item[i].substance):
            return False
    return True

def possess_any_item(_, link, __):
    return link == 'of'

def permit_any_item(_, link, __):
    return link == 'through'

def contain_any_item(_, link, __):
    return link == 'in'

def contain_and_support_any_item(_, link, __):
    return link in ['in', 'on']

def contain_permit_and_have_parts(_, link, __):
    return link in ['in', 'part_of', 'through']

def possess_any_thing(tag, link, world):
    return link == 'of' and have_only_things(tag, link, world)

def possess_and_wear_any_thing(tag, link, world):
    return link in ['of', 'on'] and have_only_things(tag, link, world)

def contain_any_thing(tag, link, world):
    return link == 'in' and have_only_things(tag, link, world)

def contain_and_support_things(tag, link, world):
    return link in ['in', 'on'] and have_only_things(tag, link, world)


########NEW FILE########
__FILENAME__ = clarifier
'Deal with unrecognized inputs, including ambiguous ones.'

__author__ = 'Nick Montfort'
__copyright__ = 'Copyright 2011 Nick Montfort'
__license__ = 'ISC'
__version__ = '0.5.0.0'
__status__ = 'Development'

import re

import preparer
import presenter

def english_command(tokens, concept, discourse):
    """Converts a command to English.

    E.g., ['LOOK_AT', '@lamp'] becomes 'look at the lamp'"""
    verb = tokens[0]
    line = ''
    i = 1
    for part in discourse.command_canonical[verb].split():
        if (part in ['ACCESSIBLE', 'ACTOR', 'DESCENDANT', 'NEARBY', 
                     'NOT-DESCENDANT', 'WORN']):
            line += concept.item[tokens[i]].noun_phrase(discourse)
            i += 1
        elif part in ['RELATION']:
            line += tokens[i].lower()
            i += 1
        elif part in ['STRING']:
            line += tokens[i]
        else:
            line += part
        line += ' '
    return line[:-1]


def clarify(user_input, concept, discourse, in_stream, out_streams):
    'States that input was not understood or attempts to disambiguate input.'

    if len(user_input.normal) == 0 and len(user_input.possible) == 0:
        clarification = ('(It\'s not clear what "' + str(user_input) +
        '" means. Try typing some other command to ' +
        concept.item[discourse.spin['commanded']].noun_phrase(discourse) + '.)')
    else:
        question = '(Is this a command to '
        commands = []
        options = []
        for possibility in user_input.possible:
            commands.append(english_command(possibility, concept, discourse))
            options.append('(' + str(len(commands)) + ') "' +
                           commands[-1] + '"')
        options.append('(' + str(len(commands) + 1) + ') none of these')
        question += discourse.list_phrases(options, conjunction='or') + '?)'
        question = re.sub('",', ',"', question)
        presenter.present(question, out_streams)
        choose_a_number = preparer.prepare(discourse.separator,
                          '(1-' + str(len(commands) + 1) + ')? ', in_stream)
        selected = None
        if len(choose_a_number.tokens) == 1:
            try:
                selected = int(choose_a_number.tokens[0])
            except ValueError:
                pass
        if selected is None or selected < 1 or selected > len(commands):
            clarification = ('\n(Since you did not select '+
                             discourse.list_phrases(range(1, len(commands) + 1),
                             conjunction='or') + ', the command "' + 
                             str(user_input) +
                             '" cannot be understood. Try something else.)')
        else:
            clarification = '\n(Very well ...)'
            user_input.category = 'command'
            user_input.normal = user_input.possible[selected-1]

    presenter.present(clarification, out_streams)
    return user_input


########NEW FILE########
__FILENAME__ = command_map
'Translate commands, from user input or elsewhere, to Actions.'

__author__ = 'Nick Montfort'
__copyright__ = 'Copyright 2011 Nick Montfort'
__license__ = 'ISC'
__version__ = '0.5.0.0'
__status__ = 'Development'

from action_model import Behave, Configure, Modify, Sense

def check_for_metonymy(tag, concept):
    if hasattr(concept.item[concept.item[tag].parent], 'vessel'):
        tag = concept.item[tag].parent
    return tag

def burn(agent, tokens, _):
    'to consume with fire; to reduce to ashes by means of heat or fire'
    return Modify('burn', agent,
                  direct=tokens[1], feature='burnt', old=False, new=True)

def close(agent, tokens, concept):
    'to stop an opening; to shut; as, to close the eyes; to close a door'
    to_be_closed = check_for_metonymy(tokens[1], concept)
    return Modify('close', agent,
                  direct=to_be_closed, feature='open', old=True, new=False)

def drink(agent, tokens, _):
    'to swallow a specific liquid, as, to drink water'
    return Behave('drink', agent, direct=tokens[1])

def drink_it_from(agent, tokens, _):
    'to swallow a specific liquid from a vessel or source'
    return Behave('drink', agent,
                  template='[agent/s] [drink/v] [direct/o] from [indirect/o]',
                  direct=tokens[1], indirect=tokens[2])

def drink_from(agent, tokens, concept):
    'to swallow from a vessel or source'
    if len(concept.item[tokens[1]].children) > 0:
        (_, direct) = concept.item[tokens[1]].children[0]
    else:
        direct = '@cosmos'
    return Behave('drink', agent,
                  template='[agent/s] [drink/v] from [indirect/o]',
                  direct=direct, indirect=tokens[1])

def doff(agent, tokens, _):
    'to strip; to divest; to undress'
    return Configure('doff', agent,
                     template='[agent/s] [take/v] off [direct/o]',
                     direct=tokens[1], old=('on', agent), new=('of', agent))

def drop(agent, tokens, concept):
    'to let go; to set aside; to have done with; to let fall to the ground'
    to_be_dropped = check_for_metonymy(tokens[1], concept)
    room = str(concept.room_of(to_be_dropped))
    return Configure('drop', agent,
                     template=['[agent/s] [relinquish/v] [direct/o]',
                               '[agent/s] [set/v] [direct/o] down'],
                     direct=to_be_dropped, new=('in', room))

def eat(agent, tokens, _):
    'to chew and swallow as food; to devour'
    return Behave('eat', agent, direct=tokens[1])

def enter(agent, tokens, concept):
    'to go into something, such as a compartment or door'
    link = 'in'
    if concept.item[tokens[1]].door:
        link = 'through'
    return Configure('enter', agent,
                     template='[agent/s] [enter/v] [indirect/o]',
                     direct=agent, new=(link, tokens[1]))

def extinguish(agent, tokens, concept):
    'to quench; to put out, as a light or fire'
    if hasattr(concept.item[tokens[1]], 'lit'):
        feature = 'lit'
    else:
        feature = 'on'
    return Modify('extinguish', agent,
                  direct=tokens[1], feature=feature, old=True, new=False)

def feed(agent, tokens, _):
    'to give food to; to supply with nourishment'
    return Configure('feed', agent,
                     template='[agent/s] [feed/v] [direct/o] to [indirect/s]',
                     direct=tokens[1], old=('of', agent), new=('of', tokens[2]))

def fill_with(agent, tokens, _):
    'to make full with a substance; to supply with as much as can be contained'
    [new_parent, substance] = tokens[1:3]
    return Configure('fill', agent,
                     template='[agent/s] [fill/v] [indirect/o] with ' + 
                              '[direct/o]',
                     direct=substance, new=('in', new_parent))

def fill_from(agent, tokens, concept):
    'to make full from a source or vessel'
    [vessel, source] = tokens[1:3]
    if len(concept.item[source].children) > 0:
        (_, direct) = concept.item[source].children[0]
    else:
        direct = '@cosmos'
    return Configure('fill', agent,
                     template='[agent/s] [fill/v] [indirect/o] from [' + 
                              source + '/o]',
                     direct=direct, old=('in', source), new=('in', vessel))

def fill_with_from(agent, tokens, _):
    'to make full with a substance from a source or vessel'
    [vessel, substance, source] = tokens[1:4]
    return Configure('fill', agent,
                     template='[agent/s] [fill/v] [indirect/o] with ' + 
                              '[direct/o] from [' + source + '/o]',
                     direct=substance, old=('in', source), new=('in', vessel))

def free(agent, tokens, concept):
    'to bring out from confinement'
    tokens.append(concept.item[tokens[1]].parent)
    return free_from(agent, tokens, concept)

def free_from(agent, tokens, concept):
    'to bring out from some specified compartment'
    [direct, container] = tokens[1:3]
    link = 'in'
    if (container in concept.item and 
        concept.item[container] == concept.item[direct].parent):
        link = concept.item[direct].link
    room_tag = str(concept.room_of(agent))
    template = '[agent/s] [free/v] [direct/o] from [' + container + '/o]'
    return Configure('free', agent,
                     template=template, direct=direct,
                     old=(link, container), new=('in', room_tag))

def freeze(agent, _, __):
    'to halt; to stop moving as if congealed by cold'
    return Behave('freeze', agent,
                  template='[agent/s] [stand/v] very still')

def give(agent, tokens, concept):
    'to yield possession of; to deliver over, as property'
    to_be_given = check_for_metonymy(tokens[1], concept)
    return Configure('give', agent,
                     template='[agent/s] [give/v] [direct/o] to [indirect/o]',
                     direct=to_be_given, old=('of', agent),
                     new=('of', tokens[2]))

def illuminate(agent, tokens, concept):
    'to make light; to supply with light; to brighten'
    if hasattr(concept.item[tokens[1]], 'lit'):
        feature = 'lit'
    else:
        feature = 'on'
    return Modify('illuminate', agent,
                  direct=tokens[1], feature=feature, old=False, new=True)

def inventory(agent, tokens, concept):
    "to make an inventory of one's own possessions"
    return look_at(agent, tokens + [agent], concept)

def kick(agent, tokens, _):
    'to strike, thrust, or hit violently with the foot'
    return Behave('kick', agent, direct=tokens[1], force=0.5)

def leave(agent, tokens, _):
    'to pass from one place to another on foot at a normal pace'
    return Behave('leave', agent,
                  template='[agent/s] [head/v] [direction]',
                  direct=agent, direction=tokens[1])

def leave_from(agent, tokens, concept):
    'to bring oneself out of some location'
    link = 'in'
    if (tokens[1] in concept.item and 
        concept.item[tokens[1]] == concept.item[agent].parent):
        link = concept.item[agent].link
    room_tag = str(concept.room_of(agent))
    template = '[agent/s] [get/v] out of [' + tokens[1] + '/o]'
    return Configure('depart', agent,
                     template=template, direct=agent,
                     old=(link, tokens[1]), new=('in', room_tag))

def listen(agent, tokens, concept):
    'to give close attention with the purpose of hearing; to hearken'
    tokens.append(str(concept.room_of(agent)))
    action = listen_to(agent, tokens, concept)
    action.representation = '[agent/s] [listen/v]'
    return action

def listen_to(agent, tokens, _):
    'to give close attention to something specified with the purpose of hearing'
    return Sense('hear', agent,
                 template='[agent/s] [listen/v] to [direct/o]',
                 direct=tokens[1], modality='hearing')

def lock(agent, tokens, _):
    'to fasten with a lock, or as with a lock; to make fast; as, to lock a door'
    return Modify('lock', agent,
                  direct=tokens[1], feature='locked', old=False, new=True)

def look(agent, tokens, concept):
    'to examine the surrounding room or compartment'
    tokens.append(str(concept.compartment_of(agent)))
    action = look_at(agent, tokens, concept)
    action.representation = '[agent/s] [look/v] around'
    return action

def look_at(agent, tokens, _):
    'to inspect something carefully, visually'
    return Sense('examine', agent,
                 template='[agent/s] [look/v] at [direct/o]',
                 modality='sight', direct=tokens[1])

def pour_in(agent, tokens, _):
    'to cause a substance to flow in a stream into somewhere'
    [substance, vessel] = tokens[1:3]
    return Configure('pour', agent,
                     template='[agent/s] [pour/v] [direct/o] into [indirect/o]',
                     direct=substance, new=('in', vessel))

def pour_in_from(agent, tokens, _):
    'to cause a substance to flow from somewhere into somewhere else'
    [substance, source, vessel] = tokens[1:4]
    return Configure('pour', agent,
                     template='[agent/s] [pour/v] [direct/o] into [indirect/o]',
                     direct=substance, old=('in', source), new=('in', vessel))

def pour_on(agent, tokens, _):
    'to cause a substance to flow in a stream onto something'
    [substance, vessel] = tokens[1:3]
    return Configure('pour', agent,
                     template='[agent/s] [pour/v] [direct/o] onto [indirect/o]',
                     direct=substance, new=('on', vessel))

def pour_on_from(agent, tokens, _):
    'to cause a substance to flow from somewhere onto something'
    [substance, source, vessel] = tokens[1:4]
    return Configure('pour', agent,
                     template='[agent/s] [pour/v] [direct/o] onto [indirect/o]',
                     direct=substance, old=('in', source), new=('on', vessel))

def press(agent, tokens, _):
    'to exert pressure or force upon'
    return Behave('press', agent, direct=tokens[1])

def put_in(agent, tokens, _):
    'to bring to a position or place; to place; to lay; to set'
    return Configure('put', agent,
                     template='[agent/s] [put/v] [direct/o] in [indirect/o]',
                     direct=tokens[1], new=('in', tokens[2]))

def put_on(agent, tokens, _):
    'to bring to a position or place; to place; to lay; to set'
    return Configure('put', agent,
                     template='[agent/s] [put/v] [direct/o] on [indirect/o]',
                     direct=tokens[1], new=('on', tokens[2]))

def read(agent, tokens, concept):
    'to take in the sense of, as of language, by interpreting characters'
    return look_at(agent, tokens, concept)

def remove(agent, tokens, concept):
    'to bring out of some location'
    tokens.append(concept.item[tokens[1]].parent)
    return remove_from(agent, tokens, concept)

def remove_from(agent, tokens, concept):
    'to bring out of some location'
    [direct, container] = tokens[1:3]
    if (direct == agent):
        return free_from(agent, tokens, concept)
    link = 'in'
    if (container in concept.item and 
        concept.item[container] == concept.item[direct].parent):
        link = concept.item[direct].link
    template = '[agent/s] [remove/v] [direct/o] from [' + container + '/o]'
    return Configure('remove', agent,
                     template=template, direct=direct,
                     old=(link, container), new=('of', agent))

def smell(agent, tokens, concept):
    'to perceive generally by the sense of smell'
    tokens.append(str(concept.room_of(agent)))
    action = smell_of(agent, tokens, concept)
    action.representation = '[agent/s] [sniff/v] around'
    return action

def smell_of(agent, tokens, _):
    'to perceive something by the sense of smell'
    return Sense('smell', agent,
                 template='[agent/s] [smell/v] [direct/o]',
                 direct=tokens[1], modality='smell')

def take(agent, tokens, concept):
    "to get into one's hold or possession; to procure; to seize and carry away"
    to_be_taken = check_for_metonymy(tokens[1], concept)
    return Configure('take', agent,
                     template='[agent/s] [pick/v] [direct/o] up',
                     direct=to_be_taken, new=('of', agent))

def taste(agent, tokens, _):
    'to perceive by the sense of taste, by sampling a small bit'
    return Sense('taste', agent,
                 template='[agent/s] [taste/v] [direct/o]',
                 direct=tokens[1], modality='taste')

def shake(agent, tokens, _):
    'to cause to move with quick or violent vibrations; to make to tremble'
    return Behave('shake', agent,
                  template='[agent/s] [shake/v] [direct/o]',
                  direct=tokens[1])

def shake_at(agent, tokens, _):
    'to cause to move with quick or violent vibrations at something'
    return Behave('shake', agent,
                  template='[agent/s] [shake/v] [indirect/o] at [direct/o]',
                  indirect=tokens[1], target=tokens[2])

def strike(agent, tokens, _):
    'to touch or hit with force, with the hand; to smite'
    return Behave('strike', agent, direct=tokens[1], force=0.4)

def strike_with(agent, tokens, _):
    'to touch or hit with force, with an instrument; to smite'
    return Behave('strike', agent,
                  template='[agent/s] [strike/v] [direct/o] with [indirect/o]',
                  direct=tokens[1], indirect=tokens[2], force=0.4)

def tell(agent, tokens, _):
    'to utter or recite to one or more people; to say'
    said = ' '.join(tokens[2:])
    return Behave('tell', agent,
                  template='[agent/s] [say/v] [utterance] to [direct/o]',
                  utterance=said, target=tokens[1])

def throw(agent, tokens, concept):
    'to fling, cast, or hurl with a certain whirling motion of the arm'
    item = concept.item[tokens[1]]
    new_place = str(concept.room_of(agent))
    return Configure('throw', agent,
                     template='[agent/s] [toss/v] [direct/s] up',
                     direct=tokens[1], old=(item.link, item.parent),
                     new=('through', new_place))

def toggle(agent, tokens, concept):
    'to switch from one state to the other possible state'
    if concept.item[tokens[1]].on:
        return turn_off(agent, tokens, concept)
    else:
        return turn_on(agent, tokens, concept)

def touch(agent, tokens, _):
    'to come in contact with; to extend the hand so as to reach and feel'
    return Sense('touch', agent, direct=tokens[1], modality='touch')

def touch_with(agent, tokens, _):
    'to come in contact with; to extend an object so as to reach'
    return Behave('touch', agent,
                  template='[agent/s] [touch/v] [direct/o] with [indirect/o]',
                  direct=tokens[1], indirect=tokens[2])

def turn_off(agent, tokens, _):
    'to deactivate; to switch something from an active state to an inactive one'
    return Modify('deactivate', agent,
                  template='[agent/s] [turn/v] [direct/o] off',
                  direct=tokens[1], feature='on', old=True, new=False)

def turn_on(agent, tokens, _):
    'to activate; to switch something from an inactive state to an active one'
    return Modify('activate', agent,
                  template='[agent/s] [turn/v] [direct/o] on',
                  direct=tokens[1], feature='on', old=False, new=True)

def turn_to(agent, tokens, _):
    'to rotate; to revolve; to make to face differently'
    return Modify('rotate', agent,
                  template='[agent/s] [turn/v] [direct/o] to ' + tokens[2],
                  direct=tokens[1], feature='setting', new=int(tokens[2]))

def open_up(agent, tokens, concept):
    """to make or set open; to render free of access

    Since 'open' is a builtin function, this one is called 'open_up.'"""    
    to_be_opened = check_for_metonymy(tokens[1], concept)
    return Modify('open', agent,
                  direct=to_be_opened, feature='open', old=False, new=True)

def open_with(agent, tokens, world):
    'to attempt to make or set open using a tool; to render free of access'
    if (hasattr(world.item[tokens[1]], 'locked') and 
        world.item[tokens[1]].locked):
        return Modify('unlock', agent,
                      direct=tokens[1], feature='locked', old=True, new=False)
    return Modify('open', agent,
                  template='[agent/s] [open/v] [direct/o] using [' + tokens[2] +
                  '/o]', direct=tokens[1], indirect=tokens[2], feature='open',
                  old=False, new=True)

def unlock(agent, tokens, _):
    'to unfasten, as what is locked; as, to unlock a door or a chest'
    return Modify('unlock', agent,
                  direct=tokens[1], feature='locked', old=True, new=False)

def utter(agent, tokens, _):
    'to speak; to pronounce (to no one in particular)'
    said = ' '.join(tokens[1:])
    return Behave('say', agent, 
                  template='[agent/s] [say/v] [utterance]', utterance=said)

def wait(agent, _, __):
    'to remain idle'
    return Behave('wait', agent)

def wander(agent, _, __):
    'to ramble here and there without any certain course; to rove'
    return Behave('wander', agent,
             template='[agent/s] [wander/v] around, staying in the same area',
             direct=agent)

def wave(agent, _, __):
    'to move the hands one way and the other'
    return Behave('wave', agent)

def wave_at(agent, tokens, _):
    'to gesture at someone by moving the hands'
    return Behave('wave', agent,
                  template='[agent/s] [wave/v] at [direct/o]',
                  target=tokens[1])

def wear(agent, tokens, _):
    'to carry or bear upon the person, as an article of clothing, etc.'
    return Configure('wear', agent,
                     template='[agent/s] [put/v] [direct/o] on',
                     direct=tokens[1], old=('of', agent), new=('on', agent))


########NEW FILE########
__FILENAME__ = curveship
#!/usr/bin/env python
'An interactive fiction system offering control over the narrative discourse.'

__author__ = 'Nick Montfort'
__copyright__ = 'Copyright 2011 Nick Montfort'
__license__ = 'ISC'
__version__ = '0.5.0.0'
__status__ = 'Development'

import sys
import os
import time
import optparse

import clarifier
import command_map
import discourse_model
import joker
import microplanner
import preparer
import presenter
import recognizer
import reply_planner
import world_model

class Multistream(object):
    'Encapsulates multiple output streams.'

    def __init__(self, streams, log=None):
        self.streams = streams
        self.log = log

    def close(self):
        """Close each of the streams.

        If one or more of the streams returns some exit status, the maximum
        value is returned by this method."""
        overall_status = None
        for stream in self.streams:
            status = stream.close()
            if status is not None:
                overall_status = max(overall_status, status)
        return overall_status

    def write(self, string):
        'Write string to each of the streams.'
        for stream in self.streams:
            stream.write(string)


def start_log(out_streams):
    'Open a log file named with the next available integer.'
    log_files = [os.path.splitext(l)[0] for l in os.listdir('logs/') if
                 os.path.splitext(l)[1] == '.log']
    if len(log_files) == 0:
        latest = 0
    else:
        latest = max([int(log_file) for log_file in log_files])
    log_file = 'logs/' + str(latest + 1) + '.log'
    try:
        log = file(log_file, 'w')
    except IOError, err:
        msg = ('Unable to open log file "' + log_file + '" for ' +
               'writing due to this error: ' + str(err))
        raise joker.StartupError(msg)
    # So that we output to the screen and the log file:
    out_streams.streams.append(log)
    # And indicate that this stream is the log file:
    out_streams.log = log
    presenter.present('\nLogged to: ' + log_file + '\nSession started ' +
                      time.strftime("%Y-%m-%d %H:%M:%S"), out_streams)
    return out_streams


def initialize(if_file, spin_files, out_streams):
    'Load all files and present the header and prologue.'
    for startup_string in joker.session_startup(__version__):
        presenter.center(startup_string, out_streams)
    fiction = joker.load_fiction(if_file, ['discourse', 'items'],
                                 discourse_model.FICTION_DEFAULTS)
    presenter.center('fiction: ' + if_file, out_streams)
    world = world_model.World(fiction)
    world.set_concepts(fiction.concepts)
    for i in dir(fiction):
        if i[:8] == 'COMMAND_':            
            setattr(command_map, i.partition('_')[2], getattr(fiction, i))
            delattr(fiction, i)
    for (key, value) in discourse_model.SPIN_DEFAULTS.items():
        if key not in fiction.discourse['spin']:
            fiction.discourse['spin'][key] = value
    while len(spin_files) > 0:
        next_file = spin_files.pop(0)
        new_spin = joker.load_spin(fiction.discourse['spin'], next_file)
        fiction.discourse['spin'].update(new_spin)
        presenter.center('spin: ' + next_file, out_streams)
    presenter.present('\n', out_streams)
    presenter.present('', out_streams)
    discourse = discourse_model.Discourse(fiction.discourse)
    reply = joker.show_frontmatter(discourse)
    if 'prologue' in discourse.metadata:
        reply += '\n\n' + joker.show_prologue(discourse.metadata)
    presenter.present(reply, out_streams)
    return (world, discourse)


def handle_input(user_input, world, discourse, in_stream, out_streams):
    """Deal with input obtained, sending it to the appropriate module.

    The commanded character's concept is used when trying to recognize
    commands."""
    c_concept = world.concept[discourse.spin['commanded']]
    user_input = recognizer.recognize(user_input, discourse, c_concept)
    if user_input.unrecognized:
        user_input = clarifier.clarify(user_input, c_concept, discourse,
                                       in_stream, out_streams)
    if user_input.command:
        user_input, id_list, world = simulator(user_input, world,
                                                  discourse.spin['commanded'])
        if hasattr(world.item['@cosmos'], 'update_spin'):
            discourse.spin = world.item['@cosmos'].update_spin(world, 
                                                               discourse)
        spin = discourse.spin
        if hasattr(world.item['@cosmos'], 'use_spin'):
            spin = world.item['@cosmos'].use_spin(world, discourse.spin)
        f_concept = world.concept[spin['focalizer']]
        tale, discourse = teller(id_list, f_concept, discourse)
        presenter.present(tale, out_streams)
    elif user_input.directive:
        texts, world, discourse = joker.joke(user_input.normal, world,
                                             discourse)
        for text in texts:
            if text is not None:
                presenter.present(text, out_streams)
    discourse.input_list.update(user_input)
    return (user_input, world, discourse)


def each_turn(world, discourse, in_stream, out_streams):
    'Obtain and processes input, if the session is interactive.'
    if discourse.spin['commanded'] is None:
        if hasattr(world.item['@cosmos'], 'interval'):
            world.item['@cosmos'].interval()
        _, id_list, world = simulator(None, world,
                                         discourse.spin['commanded'])
        focal_concept = world.concept[discourse.spin['focalizer']]
        reply_text, discourse = teller(id_list, focal_concept, discourse)
        presenter.present(reply_text, out_streams)
    else:
        if (hasattr(discourse, 'initial_inputs') and 
             len(discourse.initial_inputs) > 0):
            input_string = discourse.initial_inputs.pop(0)
            user_input = preparer.tokenize(input_string, discourse.separator)
            presenter.present('[> ' + input_string, out_streams, '', '')
        else:
            user_input = preparer.prepare(discourse.separator, 
                                          discourse.typo.prompt, in_stream, 
                                          out_streams)
        # After each input, present a newline all by itself.
        presenter.present('\n', out_streams, '', '')
        while len(user_input.tokens) > 0 and world.running:
            (user_input, world, discourse) = handle_input(user_input, world,
                                              discourse, in_stream,
                                              out_streams)
            presenter.present(discourse.input_list.show(1),
                              out_streams.log)
    return (world, discourse)


def simulator(user_input, world, commanded, actions_to_do=None):
    'Simulate the IF world using the Action from user input.'
    if actions_to_do is None:
        actions_to_do = []
    done_list = []
    start_time = world.ticks
    for tag in world.item:
        if (world.item[tag].actor and not tag == commanded and 
            world.item[tag].alive):
            # The commanded character does not act automatically. That is,
            # his, her, or its "act" method is not called.
            new_actions = world.item[tag].act(command_map, world.concept[tag])
            actions_to_do.extend(new_actions)
    if commanded is not None and user_input is not None:
        commanded = world.item[commanded]
        c_action = commanded.do_command(user_input.normal, command_map, world)
        if c_action is not None:
            c_action.cause = '"' + ' '.join(user_input.normal) + '"'
            actions_to_do.append(c_action)
            if user_input is not None:
                user_input.caused = c_action.id
    current_time = start_time
    while len(actions_to_do) > 0 and world.running:
        action = actions_to_do.pop(0)
        to_be_done = action.do(world)
        done_list.append(action.id)
        if action.final:
            world.running = False
        actions_to_do = to_be_done + actions_to_do
        if action.end > current_time:
            world.advance_clock(action.end - current_time)
            current_time = action.end
    return user_input, done_list, world


def teller(id_list, concept, discourse):
    'Narrate actions based on the concept. Update the discourse.'
    reply_plan = reply_planner.plan(id_list, concept, discourse)
    section = microplanner.specify(reply_plan, concept, discourse)
    output = section.realize(concept, discourse)
    return output, discourse


def parse_command_line(argv):
    'Improved option/argument parsing and help thanks to Andrew Plotkin.'
    parser = optparse.OptionParser(usage='[options] fiction.py [ spin.py ... ]')
    parser.add_option('--auto', dest='autofile',
                      help='read inputs from FILE', metavar='FILE')
    parser.add_option('--nodebug', action='store_false', dest='debug',
                      help='disable debugging directives',
                      default=True)
    opts, args = parser.parse_args(argv[1:])
    if not args:
        parser.print_usage()
        msg = ('At least one argument (the fiction file name) is ' +
               'needed; any other file names are processed in order ' +
               'as spin files.')
        raise joker.StartupError(msg)
    return opts, args


def main(argv, in_stream=sys.stdin, out_stream=sys.stdout):
    "Set up a session and run Curveship's main loop."
    return_code = 0
    try:
        out_streams = Multistream([out_stream])
        opts, args = parse_command_line(argv)
        out_streams = start_log(out_streams)
        world, discourse = initialize(args[0], args[1:], out_streams)
        discourse.debug = opts.debug
        if opts.autofile is not None:
            auto = open(opts.autofile, 'r+')
            discourse.initial_inputs = auto.readlines()
            auto.close()
        if len(world.act) > 0:
            _, id_list, world = simulator(None, world,
                                          discourse.spin['commanded'],
                                          world.act.values())
            focal_concept = world.concept[discourse.spin['focalizer']]
            reply_text, discourse = teller(id_list, focal_concept, discourse)
            presenter.present(reply_text, out_streams)
        while world.running:
            previous_time = time.time()
            world, discourse = each_turn(world, discourse, in_stream,
                                         out_streams)
            out_streams.log.write('#' + str(time.time() - previous_time))
    except joker.StartupError, err:
        presenter.present(err.msg, Multistream([sys.stderr]))
        return_code = 2
    except KeyboardInterrupt, err:
        presenter.present('\n', out_streams)
        return_code = 2
    except EOFError, err:
        presenter.present('\n', out_streams)
        return_code = 2
    finally:
        in_stream.close()
        out_streams.close()
    return return_code


if __name__ == '__main__':
    sys.exit(main(sys.argv))


########NEW FILE########
__FILENAME__ = discourse_model
'Represent initial and ongoing discourse features. Extended by games/stories.'

__author__ = 'Nick Montfort'
__copyright__ = 'Copyright 2011 Nick Montfort'
__license__ = 'ISC'
__version__ = '0.5.0.0'
__status__ = 'Development'

import math
import re
import types

import input_model

class SpecialTime(object):
    'Adapted from extremes.py, based on PEP 326.'

    def __init__(self, comparator, name):
        object.__init__(self)
        self._comparator = comparator
        self._name = name

    def __cmp__(self, other):
        if isinstance(other, self.__class__):
            return cmp(self._comparator, other._comparator)
        return self._comparator

    def __repr__(self):
        return self._name

    def __lt__(self, other):
        return (self.__cmp__(other) < 0)

    def __le__(self, other):
        return (self.__cmp__(other) <= 0)

    def __gt__(self, other):
        return (self.__cmp__(other) > 0)

    def __eq__(self, other):
        return (self.__cmp__(other) == 0)

    def __ge__(self, other):
        return (self.__cmp__(other) >= 0)

    def __ne__(self, other):
        return (not self.__cmp__(other) == 0)


def reformat(string):
    'Split a long string into sentences at blank lines; collapse spaces.'
    if string is None:
        return None
    string = re.sub(' +', ' ', string.strip())
    string = re.sub(' *\n *', '\n', string)
    string = re.sub('\n\n\n+', '{}', string)
    sentence_list = []
    for paragraph in string.split('{}'):
        for sentence in paragraph.strip().split('\n\n'):
            sentence_list.append(re.sub('\n', ' ', sentence.strip()))
        sentence_list.append('')
    return sentence_list[:-1]


def splitoff(string):
    'Tokenize the string, splitting it on spaces.'
    if string[0].isupper():
        space_match = re.search(' ', string)
        if space_match is not None:
            first = string[:space_match.start()]
            rest = string[space_match.start()+1:]
            return [first] + splitoff(rest)
        else:
            return [string]
    else:
        upper_match = re.search('[A-Z]', string)
        if upper_match is not None:
            first = string[:upper_match.start()-1]
            rest = string[upper_match.start():]
            return [first] + splitoff(rest)
        else:
            return [string]


def zero_to_ten(point):
    'Maps a float with values of interest in (0.0, 1.0) to range(0,11).'
    digit = int(math.floor((point + .05) * 10))
    digit = max(0, digit)
    digit = min(10, digit)
    return digit


ZERO_TO_19 = ('zero', 'one', 'two', 'three', 'four', 'five', 'six', 'seven',
              'eight', 'nine', 'ten', 'eleven', 'twelve', 'thirteen',
              'fourteen', 'fifteen', 'sixteen', 'seventeen', 'eighteen',
              'nineteen')

HYPHEN_ONES = ('', '-one', '-two', '-three', '-four', '-five', '-six', '-seven',
               '-eight', '-nine')

TWENTY_UP = ('', '', 'twenty', 'thirty', 'forty', 'fifty', 'sixty', 'seventy',
             'eighty', 'ninety')

THOUSAND_UP = ('', ' thousand', ' million', ' billion', ' trillion',
               ' quadrillion', ' quintillion', ' sextillion', ' septillion',
               ' octillion', ' nonillion', ' decillion', ' undecillion',
               ' duodecillion', ' tredecillion', ' quattuordecillion',
               ' sexdecillion', ' septendecillion', ' octodecillion',
               ' novemdecillion', ' vigintillion')


def english_integer(val):
    'Returns an English name for any integer that has one.'
    if val < 0:
        return 'negative ' + english_integer(-val)
    elif val < 20:
        return ZERO_TO_19[val]
    elif val < 100:
        return TWENTY_UP[val / 10] + HYPHEN_ONES[val % 10]
    elif val < 1000:
        name = HYPHEN_ONES[val / 100][1:] + ' hundred'
        if val % 100 > 0:
            name += ' and ' + english_integer(val % 100)
        return name
    name = ''
    step = 0
    while val > 0:
        current = val % 1000
        if current > 0:
            name = english_integer(current) + THOUSAND_UP[step] + ' ' + name
        val = val / 1000
        step += 1
    name = name.strip()
    return name


FICTION_DEFAULTS = {
    'actions': [],
    'concepts': [],
    'cosmos': None,
    'people': []
}

SPIN_DEFAULTS = {
    'dynamic': True,
    'focalizer': '@focalizer',
    'commanded': '@commanded',
    'narratee': '@focalizer',
    'narrator': None,
    'order': 'chronicle',
    'speed': .75,
    'frequency': [('default', 'singulative')],
    'time': 'during',
    'window': 'current',
    'progressive': False,
    'perfect': False,
    'time_words': False,
    'room_name_headings': True,
    'known_directions': False,
    'template_filter': None,
    'sentence_filter': None,
    'paragraph_filter': None,
}

QUALITY_WORDS = {
    'actor': '| person',
    'clothing': ('of apparel | clothing garment threads wear wearable ' +
                 'vestment habiliment'),
    'container': '| container',
    'device': '| device mechanism machine apparatus',
    'doorway': ('liminal | doorway entry entrance entryway portal ' +
                'threshold passage'),
    'food': 'edible | food',
    'item': '| entity',
    'man': 'male | man guy dude hombre',
    'metal': 'metal metallic |',
    'of_stone': 'stone mineral rock stony |',
    'of_wood': 'wood wooden woody |',
    'person': 'human | person human individual being',
    'room': 'surrounding | area location place',
    'substance': 'amount quantity | substance',
    'thing': '| thing item object',
    'trash': 'discarded cast-off cast off | trash rubbish refuse waste junk',
    'treasure': 'precious valuable | treasure',
    'woman': 'female | woman lady gal'}


class Typography(object):
    'Parameters controlling the appearance of output.'
    indentation = '   '
    _indent_first = True
    _after_paragraph = 1
    _before_heading = 1
    _after_heading = 2
    _frame = ('== ', ' ==')
    prompt = '>'

# Try these settings to see how the typography can vary:
#    indentation = ' // '
#    _indent_first = False
#    _after_paragraph = 0
#    _before_heading = 2
#    _after_heading = 2
#    _frame = ('(<>) ', '')
#    prompt = '>) '

    def format_heading(self, string, previous, last):
        'Return the string framed and otherwise formatted as a heading.'
        string = self._frame[0] + string + self._frame[1]
        if previous is not None:
            string = ('\n' * self._before_heading) + string
        if not last:
            string += ('\n' * self._after_heading)
        return string

    def format_paragraph(self, string, previous, last):
        'Return a string indented and otherwise formatted as a paragraph.'
        if (self._indent_first or previous is not None and
            hasattr(previous, 'sentences')):
            string = self.indentation + string
        if not last:
            string += ('\n' * self._after_paragraph)
        return string


class Discourse(object):
    """The per-fiction/per-game discourse model.

    This represents all exchanges of language between system and interactor and
    all verbal resources that are needed to recognize, narrate and describe, 
    and output replies from the Joker."""

    typo = Typography()
    separator = [';', '.']
    determiner = '(a |an |the |my |your |his |her |that |these |one |some |)?'
    me_nouns = ['me', 'myself', 'self']
    you_nouns = ['you', 'yourself', 'self']
    indefinite = ['a', 'an', 'some']

    min = SpecialTime(-2, "minimum")
    right_before = SpecialTime(-1, "right before")
    follow = SpecialTime(0, "follow")
    right_after = SpecialTime(1, "right after")
    max = SpecialTime(2, "maximum")

    debug = False

    def __init__(self, discourse):
        self.input_list = input_model.InputList()
        self.narrated = {}
        self.spin = discourse['spin']
        self.initial_spin = discourse['spin']
        self.metadata = discourse['metadata']
        if 'prologue' in self.metadata:
            self.metadata['prologue'] = reformat(self.metadata['prologue'])
        self.action_templates = []
        for i in ['initial_inputs', 'action_templates']:
            if i in discourse:
                setattr(self, i, discourse[i])
        for i in ['command_grammar', 'compass', 'verb_representation']:
            if i in discourse:
                for key, new_value in discourse[i].items():
                    getattr(self, i)[key] = new_value
        self.givens = set()
        self.english_to_link = {}
        for (relation, names) in self.link_to_english.items():
            for name in names:
                self.english_to_link[name] = relation
        self.commands = []
        for action in self.command_grammar:
            action_parts = action.split()
            for rule in self.command_grammar[action]:
                rule_parts = splitoff(rule)
                self.commands += [(action_parts, rule_parts)]
        self.command_canonical = {}
        for action in self.command_grammar:
            verb = action.split()[0]
            self.command_canonical[verb] = self.command_grammar[action][0]

    def mark_narrated(self, action_id):
        'Tally the number of times a particular action has been narrated.'
        if action_id not in self.narrated:
            self.narrated[action_id] = 1
        else:
            self.narrated[action_id] += 1

    @staticmethod
    def list_phrases(phrases, delimiter=',', conjunction='and',
                     serial_comma=True):
        'Creates an English list, delimited and conjoined as specified.'
        for i in range(0, len(phrases)):
            # Convert any integers in the list to strings here
            if type(phrases[i]) == types.IntType:
                phrases[i] = str(phrases[i])
        if len(phrases) >= 2:
            phrases[-1] = conjunction + ' ' + phrases[-1]
        joiner = delimiter + ' '
        if len(phrases) <= 2:
            joiner = ' '
        if serial_comma:
            complete_list = joiner.join(phrases)
        else:
            complete_list = joiner.join(phrases[:-1]) + ' ' + phrases[-1]
        return complete_list

    verb_representation = {}

    command_grammar = {
        'BURN ACCESSIBLE':
         ['burn ACCESSIBLE',
          '(ignite|torch) ACCESSIBLE'],

        'CLOSE ACCESSIBLE':
         ['close ACCESSIBLE',
          '(close|shut)( up)? ACCESSIBLE'],

        'DOFF WORN':
         ['take off WORN',
          '(doff|remove|take off|shed|strip off) WORN',
          '(take|strip) WORN off'],

        'DRINK ACCESSIBLE':
         ['drink ACCESSIBLE',
          '(gulp|imbibe|sip|swallow) ACCESSIBLE'],

        'DRINK_FROM ACCESSIBLE':
         ['drink from ACCESSIBLE',
          '(gulp|imbibe|sip|swallow) from ACCESSIBLE'],

        'DRINK_IT_FROM ACCESSIBLE':
         ['drink ACCESSIBLE from ACCESSIBLE',
          '(gulp|imbibe|sip|swallow) ACCESSIBLE from ACCESSIBLE'],

        'DROP DESCENDANT':
         ['(discard|put down|release) DESCENDANT',
          'put DESCENDANT down',
          '(drop|dump)( off)? DESCENDANT'],

        'EAT ACCESSIBLE':
         ['eat ACCESSIBLE',
          '(consume|devour|ingest|yum) ACCESSIBLE'],

        'ENTER ACCESSIBLE':
         ['enter ACCESSIBLE',
          '(go|walk) (in|into|through) ACCESSIBLE'],

        'EXPLODE ACCESSIBLE':
         ['blow ACCESSIBLE up',
          '(explode|blow up|detonate) ACCESSIBLE'],

        'EXTINGUISH ACCESSIBLE':
         ['extinguish ACCESSIBLE',
          'snuff( out)? ACCESSIBLE'],

        'FEED ACCESSIBLE ACCESSIBLE':
         ['feed ACCESSIBLE to ACCESSIBLE',
          'feed ACCESSIBLE( with)? ACCESSIBLE'],

        'FILL_WITH ACCESSIBLE ACCESSIBLE':
         ['fill ACCESSIBLE with ACCESSIBLE',
          'fill( up)? ACCESSIBLE with ACCESSIBLE'],

        'FILL_FROM ACCESSIBLE ACCESSIBLE':
         ['fill ACCESSIBLE from ACCESSIBLE',
          'fill( up)? ACCESSIBLE (from|out of) ACCESSIBLE'],

        'FILL_WITH_FROM ACCESSIBLE ACCESSIBLE ACCESSIBLE':
         ['fill ACCESSIBLE with ACCESSIBLE from ACCESSIBLE',
          'fill( up)? ACCESSIBLE with ACCESSIBLE (from|out of) ACCESSIBLE'],

        'FREE NOT-DESCENDANT':
         ['free NOT-DESCENDANT',
          '(extract|extricate|liberate|release) NOT-DESCENDANT'],

        'FREE_FROM NOT-DESCENDANT ACCESSIBLE':
         ['free NOT-DESCENDANT from ACCESSIBLE',
          '(extract|extricate|free|liberate|release) '+
          'NOT-DESCENDANT (from|off) ACCESSIBLE'],

        'FREEZE':
         ['freeze',
          '(remain|stand)( extremely| very)? still'],

        'GIVE ACCESSIBLE ACCESSIBLE':
         ['give ACCESSIBLE to ACCESSIBLE',
          '(give|offer|provide|supply) ACCESSIBLE ACCESSIBLE',
          '(offer|provide|supply) ACCESSIBLE to ACCESSIBLE'],

        'INVENTORY':
         ['take inventory',
          '(inventory|inv|i)'],

        'ILLUMINATE ACCESSIBLE':
         ['light ACCESSIBLE',
          '(light up|illuminate) ACCESSIBLE'],

        'KICK ACCESSIBLE':
         ['kick ACCESSIBLE'],

        'LEAVE DIRECTION':
         ['go DIRECTION',
          '(continue|depart|explore|head|leave|move|proceed|stride|' +
          'travel|run|walk)( to)? DIRECTION'],

        'LEAVE_FROM ACCESSIBLE':
         ['leave ACCESSIBLE',
          '(depart|exit|get out of|leave)( from)? ACCESSIBLE'],

        'LISTEN':
         ['listen',
          '(eavesdrop|hear)'],

        'LISTEN_TO NEARBY':
         ['listen to NEARBY',
          '(hear|listen)( to)? NEARBY'],

        'LOCK ACCESSIBLE':
         ['lock ACCESSIBLE',
          '(lock down|lock up|engage) ACCESSIBLE'],

        'LOOK':
         ['look around',
          '(gaze|inspect|l|look|observe|peer|view)' +
          '( all)?( around| about| up and down| back and forth| to and fro)?'],

        'LOOK_AT NEARBY':
         ['look at NEARBY',
          '(examine|inspect|observe|ogle|peer at|view|x) NEARBY',
          '(l|look|stare) (at|on|in|through)? NEARBY',
          'gaze upon NEARBY'],

        'OPEN_UP ACCESSIBLE':
         ['open ACCESSIBLE',
          'open up ACCESSIBLE',
          'open ACCESSIBLE up',
          '(swing|throw) ACCESSIBLE open'],

        'OPEN_WITH ACCESSIBLE ACCESSIBLE':
         ['open ACCESSIBLE with ACCESSIBLE',
          'open up ACCESSIBLE with ACCESSIBLE',
          'open ACCESSIBLE up with ACCESSIBLE',
          '(swing|throw) ACCESSIBLE open with ACCESSIBLE'],

        'POUR_IN ACCESSIBLE ACCESSIBLE':
         ['pour ACCESSIBLE into ACCESSIBLE',
          'pour( out)? ACCESSIBLE (in|into|to) ACCESSIBLE',
          'decant ACCESSIBLE (in|into|to) ACCESSIBLE'],

        'POUR_IN_FROM ACCESSIBLE ACCESSIBLE ACCESSIBLE':
         ['pour ACCESSIBLE from ACCESSIBLE into ACCESSIBLE',
          'pour( out)? ACCESSIBLE (from|out of) ACCESSIBLE '+
              '(in|into|to) ACCESSIBLE',
          'decant ACCESSIBLE (from|out of) ACCESSIBLE '+
              '(in|into|to) ACCESSIBLE'],

        'POUR_ON ACCESSIBLE ACCESSIBLE':
         ['pour ACCESSIBLE onto ACCESSIBLE',
          'pour( out)? ACCESSIBLE (on|onto|upon) ACCESSIBLE'],

        'POUR_ON_FROM ACCESSIBLE ACCESSIBLE ACCESSIBLE':
         ['pour ACCESSIBLE from ACCESSIBLE onto ACCESSIBLE',
          'pour( out)? ACCESSIBLE (from|out of) ACCESSIBLE '+
              '(on|onto|upon) ACCESSIBLE'],

        'PRESS ACCESSIBLE':
         ['push ACCESSIBLE',
          'press ACCESSIBLE'],

        'PUT_IN ACCESSIBLE ACCESSIBLE':
         ['put ACCESSIBLE into ACCESSIBLE',
          '(put|place) ACCESSIBLE (in|into) ACCESSIBLE'],

        'PUT_ON ACCESSIBLE ACCESSIBLE':
         ['put ACCESSIBLE onto ACCESSIBLE',
          '(put|place) ACCESSIBLE (atop|on|onto) ACCESSIBLE'],

        'READ ACCESSIBLE':
         ['read ACCESSIBLE',
          '(read|peruse|scan|skim) ACCESSIBLE'],

        'REMOVE NOT-DESCENDANT':
         ['remove NOT-DESCENDANT'],

        'REMOVE_FROM NOT-DESCENDANT ACCESSIBLE':
         ['remove NOT-DESCENDANT from ACCESSIBLE',
          'remove NOT-DESCENDANT (off|out) ACCESSIBLE'],

        'SHAKE ACCESSIBLE':
         ['shake ACCESSIBLE',
          '(agitate|brandish|flourish|shake|swing|wave) ACCESSIBLE (all )?' +
          '(around|about|up and down|back and forth|to and fro)?',
          'move ACCESSIBLE ' +
          '(all )?(around|about|up and down|back and forth|to and fro)'],

        'SHAKE_AT ACCESSIBLE NEARBY':
         ['shake ACCESSIBLE at NEARBY',
          '(agitate|brandish|flourish|shake|swing|wave) ACCESSIBLE (all )?' +
          '(around|about|up and down|back and forth|to and fro)?' +
          '(at|to|toward) NEARBY',
          'move ACCESSIBLE ' +
          '(all )?(around|about|up and down|back and forth|to and fro) ' +
          '(at|to|toward) NEARBY'],

        'SMELL':
         ['smell',
          '(smell|sniff)( all)?( around| about)?'],

        'SMELL_OF NEARBY':
         ['smell NEARBY',
          '(nose|scent|smell|sniff|snuff|snuffle|whiff)( of)? ACCESSIBLE'],

        'STRIKE ACCESSIBLE':
         ['attack ACCESSIBLE',
          '(break|destroy|engage|fight|hit|kill|murder|shatter|' + 
          'slaughter|slay|smack|smash) ACCESSIBLE',
          'strike( down)? ACCESSIBLE',
          'strike ACCESSIBLE down'],

        'STRIKE_WITH ACCESSIBLE DESCENDANT':
         ['attack ACCESSIBLE with DESCENDANT',
          '(break|destroy|fight|hit|kill|murder|shatter|slaughter|' +
          'slay|strike|smack|smash) ACCESSIBLE (with|using) DESCENDANT',
          'strike DESCENDANT (against|at) ACCESSIBLE'],

        'TAKE NOT-DESCENDANT':
         ['pick NOT-DESCENDANT up',
          '(carry|keep|get|obtain|pick up|steal|take|tote) NOT-DESCENDANT'],

        'TASTE ACCESSIBLE':
         ['taste ACCESSIBLE',
          '(sample|smack) ACCESSIBLE'],

        'TELL ACCESSIBLE STRING':
         ['tell ACCESSIBLE STRING',
          '(chant|mumble|say|shout|sing|tell|utter) STRING to ACCESSIBLE',
          '(chant|mumble|say|sing|utter) to ACCESSIBLE STRING'],

        'THROW ACCESSIBLE ACCESSIBLE':
         ['throw ACCESSIBLE to ACCESSIBLE',
          '(hurl|throw|toss) ACCESSIBLE (at|to|toward) ACCESSIBLE'],

        'TOGGLE ACCESSIBLE':
         ['toggle ACCESSIBLE',
          '(flip|switch) ACCESSIBLE'],

        'TOUCH ACCESSIBLE':
         ['touch ACCESSIBLE',
          '(caress|feel|rub|stroke) ACCESSIBLE'],

        'TOUCH_WITH ACCESSIBLE DESCENDANT':
         ['touch ACCESSIBLE with DESCENDANT',
          '(caress|rub|touch) ACCESSIBLE (with|using) DESCENDANT'],

        'TURN_OFF ACCESSIBLE':
         ['turn off ACCESSIBLE',
          '(deactivate|stop) ACCESSIBLE',
          'power down ACCESSIBLE',
          'switch off ACCESSIBLE',
          '(switch|turn) ACCESSIBLE off',
          'shut ACCESSIBLE (off|down)'],

        'TURN_ON ACCESSIBLE':
         ['turn on ACCESSIBLE',
          'activate ACCESSIBLE',
          '(boot|start)( up)? ACCESSIBLE',
          '(boot|start) ACCESSIBLE up',
          '(power up|switch on) ACCESSIBLE',
          '(switch|turn) ACCESSIBLE on'],

        'TURN_TO ACCESSIBLE STRING':
         ['turn ACCESSIBLE to STRING',
          '(rotate|revolve|set|swivel|turn) ACCESSIBLE (at|to|toward) STRING'],

        'UNLOCK ACCESSIBLE':
         ['unlock ACCESSIBLE',
          'disengage ACCESSIBLE'],

        'UTTER STRING':
         ['say STRING',
          '(chant|mumble|pronounce|shout|sing|tell|utter) STRING'],

        'UTTER STRING STRING':
         ['say STRING STRING',
          '(chant|mumble|pronounce|shout|sing|tell|utter) STRING STRING'],

        'UTTER STRING STRING STRING':
         ['say STRING STRING STRING',
          '(chant|mumble|pronounce|shout|sing|tell|utter) STRING STRING ' + 
             'STRING'],

        'UTTER STRING STRING STRING STRING':
         ['say STRING STRING STRING STRING',
          '(chant|mumble|pronounce|shout|sing|tell|utter) STRING STRING ' + 
             'STRING STRING'],

        'WAIT':
         ['wait',
          'z'],

        'WANDER':
         ['wander around',
          '(explore|go|move|move about|ramble|rove|run|stroll|walk|wander)'],

        'WAVE':
         ['wave',
          '(beckon|gesture|gesticulate|wave)'],

        'WAVE_AT NEARBY':
         ['wave at NEARBY',
          '(beckon|gesture|gesticulate|wave) (at|to|toward) NEARBY'],

        'WEAR ACCESSIBLE':
         ['wear ACCESSIBLE',
          '(don|put on) ACCESSIBLE',
          'put ACCESSIBLE on']}

    debugging_verbs = {
        'world': 'world_info',
        'concept': 'concept_info',
        'focal': 'concept_info',
        'directives': 'count_directives',
        'inputs': 'inputs',
        'll': 'light',
        'lightlevel': 'light',
        'level': 'light',
        'narrating': 'narrating',
        'spin': 'narrating',
        'telling': 'narrating',
        'prologue': 'prologue',
        'recount': 'recount',
        'room': 'room_name',
        'location': 'room_name',
        'place': 'room_name',
        'ticks': 'ticks',
        'title': 'title',
        'unrecognized': 'count_unrecognized'}

    directive_verbs = {
        '#': 'comment',
        '*': 'comment',
        'commands': 'count_commands',
        'comment': 'comment',
        'turns': 'count_commands',
        'end': 'terminate',
        'exits': 'exits',
        'stop': 'terminate',
        'terminate': 'terminate',
        'q': 'terminate',
        'quit': 'terminate',
        'reset': 'restart',
        'restart': 'restart',
        'resume': 'resume',
        'restore': 'restore',
        'bookmark': 'save',
        'pause': 'save',
        'save': 'save',
        'suspend': 'save',
        'score': 'score',
        'undo': 'undo'}

    spin_arguments = {
        'focalize': 'focalizer',
        'focalized': 'focalizer',
        'focalizer': 'focalizer',
        'focal': 'focalizer',
        'fc': 'focalizer',
        'command': 'commanded',
        'commanded': 'commanded',
        'cc': 'commanded',
        'player': 'player',
        'pc': 'player',
        'narrator': 'narrator',
        'narratee': 'narratee',
        'order': 'order',
        'perfect': 'perfect',
        'progressive': 'progressive',
        'speed': 'speed',
        'time': 'time',
        'tw': 'timewords',
        'timewords': 'timewords',
        'uses': 'uses',
        'load': 'uses',
        'dynamic': 'dynamic'}

    compass = {
        'n': 'north',
        'north': 'north',
        'ne': 'northeast',
        'northeast': 'northeast',
        'e': 'east',
        'east': 'east',
        'se': 'southeast',
        'southeast': 'southeast',
        's': 'south',
        'south': 'south',
        'sw': 'southwest',
        'southwest': 'southwest',
        'w': 'west',
        'west': 'west',
        'nw': 'northwest',
        'northwest': 'northwest',
        'u': 'up',
        'up': 'up',
        'ascend': 'up',
        'd': 'down',
        'down': 'down',
        'descend': 'down',
        'in': 'in',
        'into': 'in',
        'inside': 'in',
        'within': 'in',
        'out': 'out',
        'outside': 'out'}

    link_to_english = {
        'on': ['on', 'on top of', 'onto', 'upon'],
        'of': ['held by', 'of'],
        'in': ['in', 'inside', 'into', 'within'],
        'part_of': ['on', 'part of', 'affixed to'],
        'through': ['through']}

    feature_to_english = {
        'on': lambda i: ('off', 'on')[i],
        'open': lambda i: ('closed', 'open')[i],
        'glow': lambda i: ('unlit', 'barely glowing', 'weakly glowing',
                           'dimly shining', 'glowing', 'shining',
                           'brightly glowing', 'brightly shining', 'brilliant',
                           'radiant', 'searingly radiant')[zero_to_ten(i)],
        'locked': lambda i: ('unlocked', 'locked')[i],
        'intact': lambda i: ('trampled', 'pristine')[i],
        'angry': lambda i: ('calm', 'enraged')[i],
        'setting': lambda i: str(i),
        'word': lambda i: i.upper()}

    failure_to_english = {
        'actor_in_play': '[agent/s] [is/not/v] in the world',
        'allowed_in': '[direct/s] [fit/do/not/v] into [indirect/o]',
        'allowed_of': '[indirect/s] [is/not/v] able to hold [direct/o]',
        'allowed_on': '[direct/s] [fit/do/not/v] onto [indirect/o]',
        'allowed_through': '[direct/s] [fit/do/not/v] through [indirect/o]',
        'can_access_direct': "[direct/s] [is/not/v] within [agent's] reach",
        'can_access_indirect': "[indirect/s] [is/not/v] within [agent's] reach",
        'can_access_flames': '[agent/s] [have/not/v] anything to light ' + 
                             '[direct/o] with',
        'can_access_key': "the key [is/not/1/v] within [agent's] reach",
        'configure_to_different': '[agent/s] [try/ing/v] to move [direct/o]' +
                                  ' to where [direct/s] already [is/v]',
        'enough_light': 'it [is/1/v] too dark for [agent/s] to see',
        'exit_exists': '[agent/s] [is/not/v] able to find an exit to the' + 
                        ' [direction]',
        'good_enough_view': '[agent/s] [do/v] not have a good enough view ' +
                            'from [here]',
        'has_feature': '[direct/s] [is/not/v] suitable for that',
        'has_value': '',
          # Don't add anything; in the microplanner this will be overwritten
          # to name the value of the feature which is required.
        'item_in_play': '[direct/s] [is/not/v] in the world',
        'item_prominent_enough': '[direct/s] [is/not/v] prominent enough ' +
                                 'to pick out',
        'line_of_sight': '[direct/s] [is/not/v] visible',
        'modify_to_different': '[agent/s] [try/ing/v] to change [direct/o]' +
                               ' to a state [direct/s] already [is/v] in',
        'never_configure_doors': '[direct/s] [is/not/v] repositionable',
        'never_configure_parts': '[agent/s] [is/not/v] able to detach' +
                                 ' [direct/o]',
        'never_configure_sharedthings': '[direct/s] [is/not/v] repositionable',
        'never_permanently_locked': 'there [is/1/v] no way to unlock' +
                                    ' [direct/o]',
        'no_new_parent': 'WHEN DOES THIS HAPPEN?',
        'not_own_descendant': 'things [go/do/not/2/v], directly or ' +
                              ' otherwise, into or onto themselves',
        'parent_is': '[direct/s] [is/not/v] [old_link] [old_parent/o]',
        'prevented_by': '',
          # Don't add anything; the preventing action will be narrated and
          # will explain why this action was prevented.
        'rooms_cannot_move': 'entire locations [move/do/not/2/v]',
        'substance_contained': '[indirect/s] [is/not/v] able to hold' + 
                               ' [direct/o]',
        'value_unchanged': '[direct/s] [is/v] already [feature/direct/o]'}

    sense_verb = {
        'sight': 'see',
        'touch': 'feel',
        'hearing': 'hear',
        'smell': 'smell',
        'taste': 'taste'}


########NEW FILE########
__FILENAME__ = adventure
'Adventure in Style, based on the classic game and an unusual book.'

__author__ = 'Nick Montfort (based on works by Crowther, Woods, and Queneau)'
__copyright__ = 'Copyright 2011 Nick Montfort'
__license__ = 'ISC'
__version__ = '0.5.0.0'
__status__ = 'Development'

from random import random, randint, choice

from item_model import Actor, Door, Room, SharedThing, Substance, Thing
from action_model import Behave, Configure, Modify, Sense
from joker import update_spin
import can

discourse = {

    'command_grammar': {
        'CAGE ACCESSIBLE':
         ['cage ACCESSIBLE',
          '(cage in|entrap|trap) ACCESSIBLE'],

        'OIL ACCESSIBLE':
         ['oil ACCESSIBLE',
          'lubricate ACCESSIBLE'],

        'UNCHAIN ACCESSIBLE':
         ['(unchain|unleash) ACCESSIBLE'],

        'WATER ACCESSIBLE':
         ['water ACCESSIBLE']},

    'compass': {
        'across': 'across',
        'barren': 'barren',
        'bed': 'bed',
        'bedquilt': 'bedquilt',
        'building': 'house',
        'broken': 'broken',
        'canyon': 'canyon',
        'cavern': 'cavern',
        'climb': 'climb',
        'cobble': 'cobble',
        'crack': 'crack',
        'crawl': 'crawl',
        'dark': 'dark',
        'debris': 'debris',
        'depression': 'depression',
        'downstream': 'downstream',
        'enter': 'enter',
        'entrance': 'entrance',
        'exit': 'leave',
        'floor': 'floor',
        'forest': 'forest',
        'fork': 'fork',
        'giant': 'giant',
        'gully': 'gully',
        'hall': 'hall',
        'hill': 'hill',
        'hole': 'hole',
        'house': 'house',
        'in': 'in',
        'jump': 'jump',
        'leave': 'leave',
        'left': 'left',
        'low': 'low',
        'nowhere': 'nowhere',
        'onward': 'onward',
        'oriental': 'oriental',
        'outdoors': 'outdoors',
        'over': 'over',
        'pit': 'pit',
        'plover': 'plover',
        'plugh': 'plugh',
        'reservoir': 'reservoir',
        'right': 'right',
        'rock': 'rock',
        'room': 'room',
        'secret': 'secret',
        'shell': 'shell',
        'slab': 'slab',
        'slit': 'slit',
        'stair': 'stair',
        'stream': 'stream',
        'surface': 'surface',
        'tunnel': 'tunnel',
        'upstream': 'upstream',
        'valley': 'valley',
        'view': 'view',
        'wall': 'wall',
        'xyzzy': 'xyzzy',
        'y2': 'y2'},

    'metadata': {
        'title': 'Adventure in Style',
        'headline': 'Two Great Tastes that Taste Great Together',
        'people': [('by', 'Nick Montfort'),
                   ('based on Adventure by',
                    'Will Crowther and Don Woods'),
                   ('and based on Exercises in Style by',
                    'Raymond Queneau')],
        'prologue': """Welcome to Adventure!!

        Note that the cave entrance is SOUTH, SOUTH, SOUTH from here."""},

    'spin': {
        'commanded': '@adventurer',
        'focalizer': '@adventurer',
        'narratee': '@adventurer'},

    'verb_representation': {
        'examine': '[agent/s] [take/v] a look at [direct/o]',
        'leave': '[agent/s] [set/v] off [direction]ward',
        'scare': '[agent/s] [scare/v] [direct/o] away',
        'appear': '[direct/s] [appear/v]',
        'block': '[direct/s] [are/not/v] able to get by [agent/o]',
        'flit': '[agent/s] [flit/v] away, remaining in the general area',
        'flee': '[agent/s] [flee/v], trembling (or at least wriggling)',
        'blast': 'the treasure valut [blast/1/v] open -- Victory!',
        'disappear': '[direct/s] [scurry/v] away out of sight',
        'set_closing': 'a voice [boom/v], "The cave will be closing soon!"'}}


def COMMAND_cage(agent, tokens, _):
    'to confine in a cage'
    return Configure('cage', agent,
                     template=('[agent/s] [put/v] [direct/o] in ' +
                               '[indirect/o]'),
                     direct=tokens[1], new=('in', '@cage'))


def COMMAND_oil(agent, tokens, concept):
    'to pour oil onto something, such as a rusty door'
    direct = '@cosmos'
    for held in concept.descendants(agent):
        if held[:4] == '@oil':
            direct = held
    return Configure('pour', agent,
                     template='[agent/s] [oil/v] [indirect/o]',
                     direct=direct, new=('on', tokens[1]))


def COMMAND_turn_to(agent, tokens, concept):
    'to rotate; to revolve; to make to face differently'
    if tokens[1] == '@lamp':
        tokens[1] = '@dial'
    try:
        value = int(tokens[2])
    except ValueError:
        value = 1
    if value < 1 or value > len(variation):
        value = 1
    return Modify('turn', agent,
                  template='[agent/s] [turn/v] [direct/o] to ' + str(value),
                  direct=tokens[1], feature='setting', new=value)


def COMMAND_unchain(agent, tokens, _):
    'to free from being restrained by a chain'
    return Modify('unchain', agent,
                  direct=tokens[1], feature='chained', new=False)


def COMMAND_water(agent, tokens, concept):
    'to pour water onto something, such as a plant'
    direct = '@cosmos'
    for held in concept.descendants(agent):
        if held[:6] == '@water':
            direct = held
    return Configure('pour', agent,
                     template='[agent/s] [water/v] [indirect/o]',
                     direct=direct, new=('on', tokens[1]))

initial_actions = [
    Sense('examine', '@adventurer', direct='@end_of_road', modality='sight')]

all_treasures = ['@nugget', '@diamonds', '@bars', '@jewelry', '@coins',
                 '@eggs', '@trident', '@vase', '@emerald', '@pyramid',
                 '@pearl', '@chest', '@rug', '@spices', '@chain']


interjections = ['uh', 'uh', 'uh', 'um', 'um', 'er']

def double_template(phrases):
    new_phrases = []
    for phrase in phrases.split():
        new_phrases.append(phrase)
        if phrase[-3:] == '/o]':
            new_phrases += ['and', choice(['the radiant being',
                'the majestic presence', 'the tremendous aura',
                'the incredible unity', 'the solemn physicality',
                'the uplifting nature', 'the full existence',
                'the all-singing, all-dancing being', 'the profound air',
                'the ineffable quality', 'the unbearable lightness',
                'the harmonious flow', 'the powerful memory']), 
                'of', phrase]
    return ' '.join(new_phrases)

def hesitant_sentence(phrases):
    new_phrases = phrases[:1]
    for original in phrases[1:]:
        if randint(1,6) == 1:
            if not new_phrases[-1][-1] in ',.:;':
                new_phrases.append(',')
            new_phrases.append(choice(interjections))
            if not original[:1] in ',.:;':
                new_phrases.append(',')
        new_phrases.append(original)
    return new_phrases

def surprise_sentence(phrases):
    chosen = randint(1,8)
    if chosen == 1:
        phrases = [choice(['whoa', 'dude']) + ','] + phrases
    elif chosen == 2:
        if not phrases[-1][-1] in ',.:;':
            phrases[-1] += ','
        phrases = phrases + [choice(['man', 'dude',])]
    phrases[-1] = phrases[-1] + '!'
    return phrases

def surprise_paragraph(paragraphs):
    chosen = randint(1,3)
    if chosen == 1:
        paragraphs = paragraphs + choice(['Amazing!', 'Wow!', 'Awesome!',
                                          'Out of this world!', 'Incredible!'])
    return paragraphs

def valley_sentence(phrases):
    new_phrases = phrases[:1]
    for original in phrases[1:]:
        if randint(1,5) == 1:
            if not new_phrases[-1][-1] in ',.:;':
                new_phrases.append(',')
            new_phrases.append('like')
            if not original in ',.:;':
                new_phrases.append(',')
        new_phrases.append(original)
    if len(new_phrases) > 0 and randint(1,6) == 1:
        if not new_phrases[-1] in ',.:;':
            new_phrases.append(',')
        new_phrases.append(choice(['totally', 'for sure']))
    return new_phrases

variation = [
    ['typical', {}],
    ['memoir', {'narrator': '@adventurer', 'narratee': None, 'time': 'after'}],
    ['royal', {'narrator': '@adventurer', 'narratee': None,
               '@adventurer': [('@adventurer',  'number', 'plural')]}],
# NEXT-STEPS
# This '@adventurer' entry doesn't do anything now; it's an idea for now
# spin files might override aspects of the simulated world to allow tellings
# of this sort.
    ['impersonal', {'narrator': None, 'narratee': None}],
    ['prophecy', {'time': 'before'}],
    ['retrograde', {'order': 'retrograde', 'window': 7,
                    'room_name_headings': False, 'time_words': True}],
# NEXT-STEPS
# 'time-words' are baked into the Microplanner right now. It would be better
# to pass in a dictionary with lists of words that can be selected from at
# random, at the least -- perheps with functions that would return
# appropriate words. 
    ['flashback', {'order': 'analepsis'}],
    ['double entry', {'narratee': None, 'template_filter': [double_template]}],
    ['oriented', {'known_directions': True, 'room_name_headings': False}],
    ['in medias res', {'progressive': True}],
    ['finished by then', {'perfect': True, 'time': 'before'}],
    ['tell it to the lamp', {'narrator': None, 'narratee': '@lamp'}],
]


class Cosmos(Actor):

    def __init__(self, tag, **keywords):
        self.closing = 0
        self.lamp_controls_changed = False
        Actor.__init__(self, tag, **keywords)

    def update_spin(self, world, discourse):
        if world.item['@lamp'].on and self.lamp_controls_changed:
            discourse.spin = discourse.initial_spin.copy()
            _, spin = variation[world.item['@dial'].setting - 1]
            discourse.spin = update_spin(discourse.spin, spin)
            if world.item['@hesitant'].on:
                discourse.spin['sentence_filter'] += [hesitant_sentence]
            if world.item['@surprise'].on:
                discourse.spin['sentence_filter'] += [surprise_sentence]
                discourse.spin['paragraph_filter'] += [surprise_paragraph]
            if world.item['@valley_girl'].on:
                discourse.spin['sentence_filter'] += [valley_sentence]
            if variation[world.item['@dial'].setting - 1][0] == 'royal':
                 world.item['@adventurer'].number = 'plural'
                 adv_concept = world.concept['@adventurer']
                 adv_concept.item['@adventurer'].number = 'plural'
            else:
                 world.item['@adventurer'].number = 'singular'
                 adv_concept = world.concept['@adventurer']
                 adv_concept.item['@adventurer'].number = 'singular'
            self.lamp_controls_changed = False
        return discourse.spin

    def react(self, world, basis):
        actions = []
        if (basis.modify and basis.direct == '@dial' and
            basis.feature == 'setting') or (basis.modify and
            basis.direct == '@lamp' and basis.feature == 'on' and
            basis.new_value == True):
            self.lamp_controls_changed = True
        elif (basis.modify and basis.direct in ['@hesitant', '@surprise',
                                                '@valley_girl']):
            self.lamp_controls_changed = True
        if (not world.item['@troll'].scared and
            not world.item['@troll'].parent == '@northeast_side_of_chasm'
            and basis.configure and basis.direct == '@adventurer' and
            basis.new_parent == '@northeast_side_of_chasm'):
            actions.append(Configure('appear', '@cosmos',
                                     template='[direct/s] [appear/v]',
                                     direct='@troll',
                                     new=('in', '@northeast_side_of_chasm'),
                                     salience=0.9))
            actions.append(Modify('change_blocked', '@cosmos',
                                 direct='@troll', feature='blocked',
                                 new=['cross', 'over', 'southwest'],
                                 salience=0.1))
        if (self.closing > 0 and world.ticks == self.closing):
            actions.append(Configure('appear', '@cosmos',
                                    template=('[direct/s] [appear/v] in ' +
                                              '[indirect/o]'),
                                    direct='@adventurer',
                                    new=('in', '@northeast_end'),
                                    salience=0.9))
        return actions

cosmos = Cosmos('@cosmos', called='creation', referring=None,
                allowed=can.have_any_item)


class Lamp(Thing):
    '@lamp is the only instance.'

    def react(self, _, basis):
        'Increase/decrease the light emitted when turned on/off.'
        actions = []
        if (basis.modify and basis.direct == str(self) and
            basis.feature == 'on'):
            # If turned on, make it glow; otherwise, have it stop glowing.
            if basis.new_value:
                actions.append(Modify('light', basis.agent,
                                      direct=str(self), feature='glow',
                                      new=0.6, salience=0.1))
            else:
                actions.append(Modify('extinguish', basis.agent,
                                      direct=str(self), feature='glow',
                                      new=0.0, salience=0.1))
        return actions


class Dial(Thing):
    '@dial is the only instance.'

    def react(self, _, basis):
        'Select the appropraite word for the new variation.'
        actions = []
        if (basis.modify and basis.direct == str(self) and
            basis.feature == 'setting'):
            (name, _) = variation[basis.new_value - 1]
            actions.append(Modify('select', basis.agent,
                                  template=('[agent/s] [select/v]' +
                                   ' [begin-caps]"' + name + '"'),
                                  direct=basis.direct, feature='word',
                                  new=name))
        return actions


class Button(Thing):
    '@button is the only instance.'

    def react(self, world, basis):
        'Blast and win the game if the black rod is in place.'
        actions = []
        if (basis.behave and hasattr(basis, 'direct') and
            basis.direct == str(self) and basis.force > 0.1 and
            str(world.room_of('@black_rod')) == '@northeast_end'):
            blast = Behave('blast', '@cosmos',
                           direct='@southwest_end', force=1)
            # The adventurer won't sense the action unless it has something
            # visible, such as the room, as its direct object.
            blast.final = True
            actions.append(blast)
        return actions


class Guardian(Thing):
    """There are several subclasses representing different guardians."""

    def __init__(self, tag, **keywords):
        self.alive = True
        Thing.__init__(self, tag, **keywords)

    def prevent(self, world, basis):
        """Block exits."""
        if (basis.behave and basis.verb == 'leave' and
            basis.direction in self.blocked):
            return True
        return False


class Snake(Guardian):
    '@snake is the only instance.'

    def react(self, world, basis):
        'Flee if the bird arrives.'
        actions = []
        if (basis.configure and basis.direct == '@bird' and
            basis.new_parent == world.room_of(str(self))):
            actions.append(Configure('flee', '@cosmos',
                                     template='[@snake/s] [flee/v]',
                                     direct='@snake', new=('of', '@cosmos'),
                                     salience=0.9))
        return actions + Guardian.react(self, world, basis)


class Dragon(Guardian):
    '@dragon is the only instance.'

    def react(self, world, basis):
        'Perish if struck, move off of rug, change description.'
        actions = []
        if (basis.behave and basis.direct == str(self) and
            basis.force > 0.3):
            actions.append(Modify('kill', basis.agent,
                                  direct=str(self), feature='alive',
                                  new=False, salience=0.9))
            actions.append(Configure('fall', '@cosmos',
                                     direct=str(self),
                                     new=('in',
                                          str(world.room_of(str(self)))),
                                     salience=0.1))
            sight = """
            [this] [is/1/v] just a huge, dead dragon, flopped on the ground"""
            actions.append(Modify('change_appearance', basis.agent,
                                 direct=str(self), feature='sight', new=sight,
                                 salience=0.0))
        return actions + Guardian.react(self, world, basis)


class Troll(Guardian):
    '@troll is the only instance.'

    def __init__(self, tag, **keywords):
        self.scared = False
        Guardian.__init__(self, tag, **keywords)

    def react(self, world, basis):
        actions = []
        'Disappear if given a treasure.'
        if (basis.configure and basis.new_parent == str(self) and
             'treasure' in world.item[basis.direct].qualities):
            actions.append(Configure('disappear', '@cosmos',
                                    template='[direct/s] [disappear/v]',
                                    direct='@troll', new=('of', '@cosmos'),
                                    salience=0.9))
        'Flee if scared.'
        if (basis.modify and basis.direct == str(self) and
            basis.feature == 'scared' and basis.new_value == True):
            actions.append(Configure('flee', '@cosmos',
                                     template='[@troll/s] [flee/v]',
                                     direct='@troll', new=('of', '@cosmos'),
                                     salience=0.9))
        return actions + Guardian.react(self, world, basis)


class Bear(Actor):
    '@bear is the only instance.'

    def __init__(self, tag, **keywords):
        self.angry = True
        self.chained = True
        Actor.__init__(self, tag, **keywords)

    def act(self, command_map, concept):
        'If not chained and the troll is present, scare him.'
        actions = []
        if ((not self.chained) and '@troll' in concept.item and
            concept.room_of(str(self)) == concept.room_of('@troll')):

            actions.append(Modify('scare', str(self),
                                  template='[agent/s] [scare/v] [@troll/s]',
                                  direct='@troll', feature='scared',
                                  new=True))
        return actions

    def prevent(self, world, basis):
        # No one can manipulate the chain if the bear is angry.
        if ((basis.configure or basis.modify) and
            basis.direct == '@chain' and self.angry):
            return True
        return False

    def react(self, world, basis):
        'Food- and chain-related reactions.'
        actions = []
        # Eat food if it is offered, calm down.
        if (basis.configure and basis.new_parent == str(self) and
            'food' in world.item[basis.direct].qualities):
            actions.append(Behave('eat', str(self), direct=basis.direct))
            actions.append(Modify('calm', '@cosmos',
                                  template='[direct/s] [calm/v] down',
                                  direct=str(self), feature='angry',
                                  new=False))
        # If chained, follow the holder of the chain.
        if (self.chained and basis.configure and
            basis.direct == world.item['@chain'].parent):
            actions.append(Configure('follow', str(self),
                                     template=('[agent/s] [follow/v] [' +
                                               basis.direct + '/o]'),
                                     direct=str(self),
                                     new=(basis.new_link, basis.new_parent)))
        # If entering the bridge, destroy it; kill whoever is holding the chain.
        if (basis.configure and basis.direct == str(self) and
            basis.new_parent == '@bridge'):
            actions.append(Modify('collapse', '@cosmos',
                                  template='the bridge [collapse/1/v]',
                                  direct='@bridge', feature='connects',
                                  new=()))
            actions.append(Modify('die', '@cosmos',
                                  template='[direct/s] [die/1/v]',
                                  direct='@bear', feature='alive',
                                  new=False))
            if self.chained:
                holder = world.item['@chain'].parent
                actions.append(Modify('die', '@cosmos',
                                      template='[direct/s] [die/1/v]',
                                      direct=holder, feature='alive',
                                      new=False))
        return actions


class Oyster(Thing):
    '@oyster is the only instance.'

    def prevent(self, _, basis):
        if (basis.modify and basis.direct == str(self) and
            basis.feature == 'open' and basis.new_value and
            (not hasattr(basis, 'indirect') or
             not basis.indirect == '@trident')):
            return True
        return False

    def react(self, _, basis):
        'When opened, move the pearl to the cul-de-sac.'
        actions = []
        if (basis.modify and basis.direct == str(self) and
            basis.feature == 'open' and basis.new_value and
            ('in', '@pearl') in self.children):
            sight = """
            an enormous oyster, currently [open/@oyster/a]"""
            actions.append(Configure('fall', '@cosmos',
                                template=('[direct/o] [fall/v] from ' +
                                          '[@oyster/o]'),
                                direct='@pearl',
                                new=('in', '@cul_de_sac')))
            actions.append(Modify('change_sight', basis.agent,
                                  direct=str(self), feature='sight',
                                  new=sight, salience=0))
            actions.append(Modify('rename', basis.agent,
                                  direct=str(self), feature='called',
                                  template="""so, at it happens, [this]
                                           actually [is/v/v] an oyster,
                                           not a clam""",
                                  new='(enormous) oyster'))
        return actions


class Plant(Thing):
    '@plant is the only instance.'

    def __init__(self, tag, **keywords):
        self.size = 0
        self.alive = True
        Thing.__init__(self, tag, **keywords)

    def react(self, world, basis):
        'Consume water; then grow when watered, the first two times.'
        actions = []
        if (basis.configure and basis.new_parent == str(self) and
            basis.direct.partition('_')[0] == '@oil'):
            # Consume oil
            actions.append(Configure('consume', '@cosmos',
                           template=('[direct/s] [soak/v] into [' +
                                     str(self) + '/o]'),
                           direct=basis.direct, new=('of', '@cosmos'),
                           salience=0.1))
            # And die!
            actions.append(Modify('die', '@cosmos',
                              template='[@plant/s] [die/v]',
                              direct=str(self), feature='alive',
                              new=False))
        if (basis.configure and basis.new_parent == str(self) and
            basis.direct.partition('_')[0] == '@water'):
            # Consume water
            actions.append(Configure('consume', '@cosmos',
                                     template=('[@plant/s] [soak/v] up ' +
                                               '[direct/o]'),
                                     direct=basis.direct,
                                     new=('of', '@cosmos'), salience=0.1))
            # If not already the maximum size, grow.
            if self.size == 0 or self.size == 1:
                actions.append(Modify('grow', '@cosmos',
                                  template='[@plant/s] [grow/v]',
                                  direct=str(self), feature='size',
                                  new=(self.size + 1)))
                sight = ["""a twelve-foot beanstalk""",
                """a 25-foot beanstalk"""][self.size]
                actions.append(Modify('change_sight', '@cosmos',
                                      direct=str(self), feature='sight',
                                      new=sight, salience=0.0))
                if self.size == 1:
                    exits = world.item['@west_pit'].exits.copy()
                    exits.update({'climb': '@narrow_corridor'})
                    actions.append(Modify('change_exits', '@cosmos',
                                          direct='@west_pit',
                                          feature='exits', new=exits,
                                          salience=0.0))
        return actions


class RustyDoor(Door):
    '@rusty_door is the only instance.'

    def react(self, world, basis):
        'Consume oil; then unlock if not already unlocked.'
        actions = []
        if (basis.configure and basis.new_parent == str(self) and
            basis.direct.partition('_')[0] == '@oil'):
            # Consume the oil
            actions.append(Configure('consume', '@cosmos',
                           template=('[direct/s] [soak/v] into [' +
                                     str(self) + '/o]'),
                           direct=basis.direct, new=('of', '@cosmos'),
                           salience=0.1))
            # If not already unlocked, unlock.
            if self.locked:
                actions.append(Modify('unlock', '@cosmos',
                               template=('[' + str(self) + '/s] ' +
                                         '[come/v] loose'),
                               direct=str(self), feature='locked', new=False,
                               salience=0.9))
        return actions


class Bird(Thing):
    '@bird is the only instance.'

    def __init__(self, tag, **keywords):
        self.alive = True
        Thing.__init__(self, tag, **keywords)

    def prevent(self, world, basis):
        if (basis.configure and basis.direct == str(self) and
            basis.new_parent == '@cage' and
            basis.agent == world.item['@rusty_rod'].parent):
            return True
        return False

    def react(self, world, basis):
        'Flee from one holding the rod; Leave all but the cage or a room.'
        actions = []
        if (basis.configure and basis.direct == str(self) and
            not basis.new_parent == '@cage' and
            not world.item[basis.new_parent].room):
            room = str(world.item[str(self)].place(world))
            actions.append(Configure('flit', str(self),
                                     template='[agent/s] [flit/v] off',
                                     direct=str(self), new=('in', room),
                                     salience=0.7))
        return actions


class Delicate(Thing):
    '@vase is the only instance.'

    def react(self, _, basis):
        'Shatter if placed on anything other than the pillow.'
        actions = []
        if (basis.configure and basis.direct == str(self)):
            if (not basis.new_parent in ['@pillow', '@soft_room',
                                         '@adventurer', '@cosmos']):
                smash = Configure('smash', basis.agent, direct=basis.direct,
                                  new=('of', '@cosmos'), salience=0.9)
                actions.append(smash)
        return actions


class Wanderer(Actor):
    'Not used, but could be used for the dwarves and the pirate.'

    def act(self, command_map, world):
        if random() > .2 and len(self.exits(world)) > 0:
            way = choice(self.exits(world).keys())
            return [self.do_command('exit ' + way, command_map, world)]


class OutsideArea(Room):
    'Subclass for all forest/outside Rooms, with sky and sun.'

    def __init__(self, tag, **keywords):
        if 'shared' not in keywords:
            keywords['shared'] = []
        keywords['shared'] += ['@sky', '@sun']
        Room.__init__(self, tag, **keywords)


class CaveRoom(Room):
    'Subclass for all cave Rooms.'

    def __init__(self, tag, **keywords):
        adj, noun = '', ''
        if 'referring' in keywords:
            (adj, _, noun) = keywords['referring'].partition('|')
        keywords['referring'] = adj + '| cave chamber room' + noun
        if 'glow' not in keywords:
            keywords['glow'] = 0.0
        Room.__init__(self, tag, **keywords)


class Bridgable(CaveRoom):
    '@fissure_east is the only instance.'

    def react(self, world, basis):
        'When the rod is waved, the bridge appears.'
        actions = []
        if (basis.behave and basis.direct == '@rusty_rod' and
            basis.verb == 'shake' and 'west' not in self.exits):
            exits = self.exits.copy()
            exits.update({'west': '@bridge',
                          'over': '@bridge'})
            sight = """
            [*/s] [are/v] on the east bank of a fissure slicing clear across
            the hall

            the mist [is/1/v] quite thick [here], and the fissure [is/1/v]
            too wide to jump

            it [is/1/v] a good thing the fissure [is/1/v] bridged [now], and
            [*/s] [are/v] able to walk across it to the west
            """
            actions.append(Modify('change_exits', '@cosmos',
                                  template='a_bridge [now] [lead/v] west',
                                  direct=str(self), feature='exits',
                                  new=exits, salience=0.9))
            actions.append(Modify('change_sight', '@cosmos',
                                  direct=str(self), feature='sight',
                                  new=sight, salience=0.0))
        return actions


class EggSummoning(CaveRoom):
    '@giant_room_92 is the only instance.'

    def react(self, world, basis):
        'Have "fee fie foe sum" summon the eggs here.'
        actions = []
        if (basis.behave and hasattr(basis, 'utterance') and
            basis.utterance in ['fee fie foe foo', '"fee fie foe foo"'] and
            ('@eggs', 'in') not in self.children):
            actions.append(Configure('appear', '@cosmos',
                           template='[direct/s] [appear/v]',
                           direct='@eggs', new=('in', str(self)),
                           salience=0.9))
        return actions


class Building(Room):
    '@building_3 is the only instance.'

    def react(self, world, basis):
        'When all treasures are in place, countdown to cave closing.'
        actions = []
        if world.item['@cosmos'].closing == 0:
            all_there = True
            for treasure in all_treasures:
                all_there &= (str(self) == str(world.room_of(treasure)))
            if all_there:
                actions.append(Modify('change_closing', '@cosmos',
                                      direct='@cosmos', feature='closing',
                                      new=(world.ticks + 28), salience=0))
        return actions

def contain_any_thing_if_open(tag, link, world):
    return link == 'in' and getattr(world.item['@cage'], 'open')

def support_one_item(tag, link, world):
    return link == 'on' and len(world.item['@pillow'].children) < 2

def contain_any_treasure(tag, link, world):
    return link == 'in' and 'treasure' in world.item[tag].qualities

def possess_any_treasure(tag, link, world):
    return link == 'of' and 'treasure' in world.item[tag].qualities

def support_any_item_or_dragon(tag, link, world):
    return link == 'on' and '@dragon' not in world.item['@rug'].children

def support_chain(tag, link, world):
    return (tag, link) == ('@chain', 'on')

can.contain_any_thing_if_open = contain_any_thing_if_open
can.support_one_item = support_one_item
can.contain_any_treasure = contain_any_treasure
can.possess_any_treasure = possess_any_treasure
can.support_any_item_or_dragon = support_any_item_or_dragon
can.support_chain = support_chain

items = [

    Substance('@water',
        called='water',
        referring='clear |',
        qualities=['drink', 'liquid'],
        consumable=True,
        sight='clear water',
        taste="nothing unpleasant"),

    Substance('@oil',
        called='oil',
        referring='black dark thick |',
        qualities=['liquid'],
        sight='black oil'),

    Actor('@adventurer in @end_of_road',
        article='the',
        called='(intrepid) adventurer',
        allowed=can.possess_any_thing,
        qualities=['person', 'man'],
        gender='?',
        sight='a nondescript adventurer'),

    OutsideArea('@end_of_road',
        article='the',
        called='end of the road',
        referring='of the | road end',
        exits={'hill': '@hill', 'west': '@hill', 'up': '@hill',
               'enter': '@building', 'house': '@building',
               'in': '@building', 'east': '@building',
               'downstream': '@valley', 'gully': '@valley',
               'stream': '@valley', 'south': '@valley',
               'down': '@valley', 'forest': '@forest_near_road',
               'north': '@forest_near_road', 'depression': '@outside_grate'},
        sight="""

        [*/s] [stand/ing/v] at _the_end of _a_road before
        _a_small_brick_building

        [@stream_by_road/s] [flow/v] out of _the_building and down _a_gully"""),

    Thing('@stream_by_road part_of @end_of_road',
        article='a',
        called='small stream',
        referring='| stream creek river spring',
        source='@water',
        mention=False,
        sight='a small stream',
        touch='cool water',
        hearing='quiet babbling'),

    SharedThing('@sky',
        article='the',
        called='sky',
        referring='blue clear | heavens',
        mention=False,
        accessible=False,
        sight='a blue, clear sky'),

    SharedThing('@sun',
        article='the',
        called='sun',
        mention=False,
        accessible=False),

    OutsideArea('@hill',
        article='the',
        called='hill in road',
        exits={'hill': '@end_of_road', 'house': '@end_of_road',
               'onward': '@end_of_road', 'east': '@end_of_road',
               'north': '@end_of_road', 'down': '@end_of_road',
               'forest': '@forest_near_road', 'south': '@forest_near_road'},
        sight="""

        [*/s] [walk/ed/v] up _a_hill, still in _the_forest

        _the_road [slope/1/v] back down _the_other_side of _the_hill

        there [is/1/v] _a_building in the_distance"""),

    Building('@building',
        article='the',
        called="building's interior",
        referring='well | building house',
        exits={'enter': '@end_of_road', 'leave': '@end_of_road',
               'outdoors': '@end_of_road', 'west': '@end_of_road',
               'xyzzy': '@debris_room', 'plugh': '@y2',
               'down': """the_stream [flow/1/v] out through a pair of 
               1 foot diameter sewer pipes, too small to enter""",
               'stream': """the_stream [flow/1/v] out through a pair of 
               1 foot diameter sewer pipes, too small to enter"""},
        sight="""

        [*/s] [are/v] inside _a_building, _a_well_house for _a_large_spring"""),

    Thing('@keys in @building',
        article='some',
        called='(glinting) keys',
        referring='key of ring | key keyring ring',
        qualities=['device', 'metal'],
        number='plural',
        sight='ordinary keys, on a ring'),

    Thing('@food in @building',
        article='some',
        called='food',
        referring='tasty fresh edible | wrap',
        qualities=['food'],
        consumable=True,
        sight='a wrap, fresh and edible',
        smell="""

        something pleasing

        _bacon was somehow involved in the production of [this] wrap""",
        taste="food that [seem/1/v] fresh and palatable"),

    Thing('@bottle in @building',
        article='a',
        called='(clear) (glass) bottle',
        open=False,
        transparent=True,
        vessel='@water',
        sight='a clear glass bottle, currently [open/@bottle/a]',
        touch="smooth glass"),

    Lamp('@lamp in @building',
        article='a',
        called='(shiny) (brass) (carbide) lamp',
        referring='| lantern light',
        qualities=['device', 'metal'],
        on=False,
        sight="""

        a brass carbide lamp, the kind often used for illuminating caves

        [@lamp/s/pro] [is/v] shiny and [glow/@lamp/a]

        [@lamp/s/pro] [display/v] the word [word/@dial/a] and [have/v] three
        switches: a "HESITANT" switch, a "SURPRISE" switch, and a "VALLEY GIRL"
        switch

        [@lamp/s] also [feature/v] a dial which can range from 1 to 12 and
        [is/v] set to [setting/@dial/a]""",
        touch="""

        [@lamp/s] and [@dial/s] on it, which [*/s] [sense/v] [is/1/v] set to
        [setting/@dial/a]"""),

    Dial('@dial part_of @lamp',
        article='the',
        called='dial',
        referring='round | dial knob',
        setting=2,
        word='memoir',
        mention=False,
        sight="""

        [@dial/s] can be set to any number between 1 and 12

        [@dial/pro/s] [is/v] set to [setting/@dial/a]"""),

    Thing('@hesitant part_of @lamp',
        article='the',
        called='"HESITANT" switch',
        referring='hesitant | switch',
        mention=False,
        on=False),

    Thing('@surprise part_of @lamp',
        article='the',
        called='"SURPRISE" switch',
        referring='surprise | switch',
        mention=False,
        on=False),

    Thing('@valley_girl part_of @lamp',
        article='the',
        called='"VALLEY GIRL" switch',
        referring='valley girl | switch',
        mention=False,
        on=False),

    OutsideArea('@valley',
        article='the',
        called='valley',
        exits={'upstream': '@end_of_road', 'house': '@end_of_road',
               'north': '@end_of_road', 'forest': '@forest_near_road',
               'east': '@forest_near_road', 'west': '@forest_near_road',
               'up': '@forest_near_road', 'downstream': '@slit',
               'south': '@slit', 'down': '@slit',
               'depression': '@outside_grate'},
        sight="""

        [*/s] [are/v] in _a_valley in _the_forest beside _a_stream tumbling
        along _a_rocky_bed"""),

    Thing('@stream_in_valley part_of @valley',
        article='a',
        called='tumbling stream',
        referring='| stream creek river spring',
        qualities=['liquid'],
        source='@water',
        mention=False,
        sight='a tumbling stream'),

    OutsideArea('@forest_near_road',
        article='the',
        called='forest',
        exits={'valley': '@valley', 'east': '@valley', 'down': '@valley',
               'forest': '@forest_near_valley', 'west': '@forest_near_road',
               'south': '@forest_near_road'},
        sight="""

        [*/s] [are/v] in open forest, with _a_deep_valley to _one_side"""),

    OutsideArea('@forest_near_valley',
        article='the',
        called='forest',
        sight="""

        [*/s] [are/v] in open forest near both _a_valley and _a_road""",
        exits={'hill': '@end_of_road', 'north': '@end_of_road',
               'valley': '@valley', 'east': '@valley', 'west': '@valley',
               'down': '@valley', 'forest': '@forest_near_road',
               'south': '@forest_near_road'}),

    OutsideArea('@slit',
        article='the',
        called='slit in the streambed',
        exits={'house': '@end_of_road', 'upstream': '@valley',
               'north': '@valley', 'forest': '@forest_near_road',
               'east': '@forest_near_road', 'west': '@forest_near_road',
               'downstream': '@outside_grate', 'rock': '@outside_grate',
               'bed': '@outside_grate', 'south': '@outside_grate',
               'slit': '[*/s] [fit/not/v] through a two-inch slit',
               'stream': '[*/s] [fit/not/v] through a two-inch slit',
               'down': '[*/s] [fit/not/v] through a two-inch slit'},
        sight="""

        at [*'s] feet all _the_water of _the_stream [splash/1/v] into
        _a_2-inch_slit in _the_rock

        downstream _the_streambed [is/1/v] bare rock"""),

    Thing('@spring_7 in @slit',
        article='a',
        called='small stream',
        referring='| stream creek river spring',
        qualities=['liquid'],
        source='@water',
        mention=False,
        sight='a small stream'),

    OutsideArea('@outside_grate',
        article='the',
        called='area outside the grate',
        sight="""

        [*/s] [are/v] in a _20-foot_depression floored with bare dirt

        set into the_dirt [is/1/v] [@grate/o] mounted in _concrete

        _a_dry_streambed [lead/1/v] into _the_depression""",
        exits={'forest': '@forest_near_road', 'east': '@forest_near_road',
               'west': '@forest_near_road', 'south': '@forest_near_road',
               'house': '@end_of_road', 'upstream': '@slit', 'gully': '@slit',
               'north': '@slit', 'enter': '@grate', 'down': '@grate'}),

    Door('@grate',
        article='a',
        called='(strong) (steel) grate',
        referring='| grating grill grille barrier',
        qualities=['doorway', 'metal'],
        allowed=can.permit_any_item,
        open=False,
        locked=True,
        key='@keys',
        transparent=True,
        connects=['@outside_grate', '@below_grate'],
        mention=False,
        sight="""

        a grate, placed to restrict entry to the cave

        it [is/1/v] currently [open/@grate/a]"""),

    CaveRoom('@below_grate',
        article='the',
        called='area below the grate',
        referring='below the grate |',
        sight="""

        [*/s] [are/v] in _a_small_chamber beneath _a_3x3_steel_grate to the
        surface

        _a_low crawl over _cobbles [lead/1/v] inward to the west""",
        glow=0.7,
        exits={'leave': '@grate', 'exit': '@grate',
               'up': '@grate', 'crawl': '@cobble_crawl',
               'cobble': '@cobble_crawl', 'in': '@cobble_crawl',
               'west': '@cobble_crawl', 'pit': '@small_pit',
               'debris': '@debris_room'}),

    CaveRoom('@cobble_crawl',
        article='the',
        called='cobble crawl',
        referring='passage',
        sight="""

        [*/s] [crawl/ing/v] over _cobbles in _a_low_passage

        there [is/1/v] a dim _light at _the_east_end of _the_passage""",
        glow=0.5,
        exits={'leave': '@below_grate', 'surface': '@below_grate',
               'nowhere': '@below_grate', 'east': '@below_grate',
               'in': '@debris_room', 'dark': '@debris_room',
               'west': '@debris_room', 'debris': '@debris_room',
               'pit': '@small_pit'}),

    Thing('@cage in @cobble_crawl',
        article='a',
        called='wicker cage',
        referring='wicker | cage',
        allowed=can.contain_any_thing_if_open,
        open=True,
        transparent=True,
        sight="""

        a wicker cage, about the size of a breadbasket, currently
        [open/@cage/a]"""),

    CaveRoom('@debris_room',
        article='the',
        called='debris room',
        sight="""
        [*/s] [are/v] in _a_room filled with _debris washed in from
        _the_surface

        _a_low_wide_passage with _cobbles [become/1/v] plugged with _mud and
        _debris [here], but _an_awkward_canyon [lead/1/v] upward and west

        _a_note on the wall [say/1/v] "MAGIC WORD XYZZY\"""",
        exits={'entrance': '@below_grate', 'crawl': '@cobble_crawl',
               'cobble': '@cobble_crawl', 'tunnel': '@cobble_crawl',
               'low': '@cobble_crawl', 'east': '@cobble_crawl',
               'canyon': '@awkward_canyon', 'in': '@awkward_canyon',
               'up': '@awkward_canyon', 'west': '@awkward_canyon',
               'xyzzy': '@building', 'pit': '@small_pit'}),

    Thing('@rusty_rod in @debris_room',
        article='a',
        called='black rod',
        referring='black iron rusty sinister | rod',
        sight='[this] ordinary sinister black rod, rather rusty'),

    CaveRoom('@awkward_canyon',
        article='the',
        called='awkward canyon',
        sight="""

        [*/s] [are/v] in _an_awkward_sloping_east/west_canyon""",
        exits={'entrance': '@below_grate', 'down': '@debris_room',
               'east': '@debris_room', 'debris': '@debris_room',
               'in': '@bird_chamber', 'up': '@bird_chamber',
               'west': '@bird_chamber', 'pit': '@small_pit'}),

    CaveRoom('@bird_chamber',
        article='the',
        called='bird chamber',
        sight="""

        [*/s] [are/v] in _a_splendid_chamber thirty feet high

        _the_walls [are/2/v] frozen _rivers of orange _stone

        _an_awkward_canyon and _a_good_passage [exit/2/v] from the east and
        west _sides of _the_chamber""",
        exits={'entrance': '@below_grate', 'debris': '@debris_room',
               'canyon': '@awkward_canyon', 'east': '@awkward_canyon',
               'tunnel': '@small_pit', 'pit': '@small_pit',
               'west': '@small_pit'}),

    Bird('@bird in @bird_chamber',
        article='a',
        called='little bird',
        referring='little cheerful | bird',
        sight='nothing more than a bird'),

    CaveRoom('@small_pit',
        article='the',
        called='top of the small pit',
        exits={'entrance': '@below_grate', 'debris': '@debris_room',
               'tunnel': '@bird_chamber', 'east': '@bird_chamber',
               'down': '@hall_of_mists',
               'west': 'the crack [is/1/v] far too small to follow',
               'crack': 'the crack [is/1/v] far too small to follow'},
        sight="""
        at [*'s] feet [is/1/v] _a_small_pit breathing traces of white _mist

        _an_east_passage [end/1/v] [here] except for _a_small_crack leading
        on"""),

    CaveRoom('@hall_of_mists',
        article='the',
        called='hall of mists',
        sight="""
        [*/s] [are/v] at one _end of _a_vast_hall stretching forward out of
        sight to the west

        there [are/2/v] _openings to either _side

        nearby, _a_wide_stone_staircase [lead/1/v] downward

        _the_hall [is/1/v] filled with _wisps of white _mist swaying to and fro
        almost as if alive

        _a_cold_wind [blow/1/v] up _the_staircase

        there [is/1/v] _a_passage at _the_top of _a_dome behind [*/o]""",
        exits={'left': '@nugget_room', 'south': '@nugget_room',
               'onward': '@fissure_east', 'hall': '@fissure_east',
               'west': '@fissure_east', 'stair': '@hall_of_mountain_king',
               'down': '@hall_of_mountain_king',
               'north': '@hall_of_mountain_king', 'up': '@small_pit',
               'y2': '@y2'}),

    Bridgable('@fissure_east',
        article='the',
        called='east bank of the fissure',
        referring='east of fissure | bank',
        sight="""

        [*/s] [are/v] on _the_east_bank of _a_fissure that [slice/1/v] clear
        across _the_hall

        _the_mist [is/1/v] quite thick here, and _the_fissure [is/1/v] too
        wide to jump""",
        shared=['@fissure'],
        exits={'hall': '@hall_of_mists', 'east': '@hall_of_mists'}),

    SharedThing('@fissure',
        article='a',
        called='fissure',
        referring='massive |',
        sight='a massive fissure'),

    Door('@bridge',
        article='a',
        called='bridge',
        referring='| bridge span',
        allowed=can.permit_any_item,
        connects=['@fissure_east', '@fissure_west'],
        sight='[@bridge] [span/v] the chasm'),

    CaveRoom('@nugget_room',
        article='the',
        called='nugget of gold room',
        referring='nugget of gold low |',
        exits={'hall': '@hall_of_mists', 'leave': '@hall_of_mists',
               'north': '@hall_of_mists'},
        sight="""

        [this] [is/1/v] _a_low_room with _a_crude_note on _the_wall

        _the_note [say/1/v] , "You won't get it up the steps" """),

    Thing('@nugget in @nugget_room',
        article='a',
        called='nugget of gold',
        referring='large sparkling of | nugget gold',
        qualities=['treasure', 'metal'],
        sight='a large gold nugget'),

    CaveRoom('@hall_of_mountain_king',
        article='the',
        called='Hall of the Mountain King',
        referring='of the mountain king | hall',
        sight="""

        [*/s] [are/v] in _the_Hall_of_the_Mountain_King, with _passages off in
        all _directions""",
        exits={'stair': '@hall_of_mists', 'up': '@hall_of_mists',
               'east': '@hall_of_mists', 'west': '@west_side_chamber',
               'north': '@low_passage', 'south': '@south_side_chamber',
               'secret': '@secret_east_west_canyon',
               'southwest': '@secret_east_west_canyon'}),

    Snake('@snake in @hall_of_mountain_king',
        article='a',
        called='huge snake',
        referring='huge green fierce | snake',
        sight='[this] [is/1/v] just a huge snake, barring the way',
        smell="something like Polo cologne",
        blocked=['west', 'north', 'south', 'secret', 'southwest']),

    CaveRoom('@west_end_of_twopit_room',
        article='the',
        called='west end of twopit room',
        sight="""

        [*/s] [are/v] at _the_west_end of _the_Twopit_Room

        there [is/1/v] _a_large_hole in _the_wall above _the_pit at [this]
        _end of _the_room""",
        exits={'east': '@east_end_of_twopit_room',
               'across': '@east_end_of_twopit_room', 'west': '@slab_room',
               'slab': '@slab_room', 'down': '@west_pit',
               'pit': '@west_pit', 'hole': '@complex_junction'}),

    CaveRoom('@east_pit',
        article='the',
        called='east pit',
        referring='eastern east | pit',
        sight="""

        [*/s] [are/v] at _the_bottom of _the_eastern_pit in _the_Twopit_Room

        there [is/1/v] [@pool_of_oil/o] in _one_corner of _the_pit""",
        exits={'up': '@east_end_of_twopit_room',
               'leave': '@east_end_of_twopit_room'}),

    Thing('@pool_of_oil in @east_pit',
        article='a',
        called='small pool of oil',
        referring='small of oil | pool',
        qualities=['liquid'],
        source='@oil',
        sight='a small pool of oil'),

    CaveRoom('@west_pit',
        article='the',
        called='west pit',
        referring='western west | pit',
        sight="""

        [*/s] [are/v] at _the_bottom of _the_western_pit in _the_Twopit_Room

        there [is/1/v] _a_large_hole in _the_wall about 25 feet above [*/o]""",
        exits={'up': '@west_end_of_twopit_room',
               'leave': '@west_end_of_twopit_room'}),

    Plant('@plant in @west_pit',
        article='a',
        called='plant',
        referring='tiny little big tall gigantic | plant beanstalk',
        open=False,
        sight='a tiny little plant, murmuring "Water, water, ..."'),

    CaveRoom('@fissure_west',
        article='the',
        called='west side of fissure',
        referring='west of fissure | side',
        sight="""

        [*/s] [are/v] on _the_west_side of _the_fissure in
        _the_Hall_of_Mists""",
        shared=['@fissure'],
        exits={'over': '@fissure_east', 'east': '@fissure_east',
               'west': '@west_end_of_hall_of_mists'}),

    Thing('@diamonds in @fissure_west',
        article='some',
        called='diamonds',
        referring='| jewel jewels',
        qualities=['treasure'],
        sight='diamonds'),

    CaveRoom('@low_passage',
        article='the',
        called='low passage',
        sight="""

        [*/s] [are/v] in _a_low_north/south_passage at _a_hole in _the_floor

        the hole [go/1/v] down to an east/west passage""",
        exits={'hall': '@hall_of_mountain_king',
               'leave': '@hall_of_mountain_king',
               'south': '@hall_of_mountain_king', 'north': '@y2',
               'y2': '@y2', 'down': '@dirty_passage',
               'hole': '@dirty_passage'}),

    Thing('@bars in @low_passage',
        article='the',
        called='bars of silver',
        referring='several of | bars silver',
        qualities=['treasure', 'metal'],
        number='plural',
        sight='several bars of silver'),

    CaveRoom('@south_side_chamber',
        article='the',
        called='south side chamber',
        sight="""

        [*/s] [are/v] in the south side chamber""",
        exits={'hall': '@hall_of_mountain_king',
               'leave': '@hall_of_mountain_king',
               'north': '@hall_of_mountain_king'}),

    Thing('@jewelry in @south_side_chamber',
        article='some',
        called='(precious) jewelry',
        referring='| jewel jewels',
        qualities=['treasure'],
        sight='precious jewelry'),

    CaveRoom('@west_side_chamber',
        article='the',
        called='west side chamber',
        sight="""

        [*/s] [are/v] in _the_west_side_chamber of
        _the_Hall_of_the_Mountain_King

        _a_passage continues west and up [here]""",
        exits={'hall': '@hall_of_mountain_king',
               'leave': '@hall_of_mountain_king',
               'east': '@hall_of_mountain_king', 'west': '@crossover',
               'up': '@crossover'}),

    Thing('@coins in @west_side_chamber',
        article='many',
        called='coins',
        referring='shiny numerous | money',
        qualities=['treasure', 'metal'],
        number='plural',
        sight='numerous coins'),

    CaveRoom('@y2',
        called='Y2',
        sight="""

        [*/s] [are/v] in _a_large_room, with _a_passage to the south,
        _a_passage to the west, and _a_wall of broken _rock to the east

        there [is/1/v] a large "Y2" on a rock in the room's center""",
        exits={'plugh': '@building', 'south': '@low_passage',
               'east': '@jumble', 'wall': '@jumble',
               'broken': '@jumble', 'west': '@window_on_pit',
               'plover': '@plover_room'}),

    CaveRoom('@jumble',
        article='the',
        called='jumble',
        sight="""

        [*/s] [are/v] in _a_jumble of _rock, with _cracks everywhere""",
        exits={'down': '@y2', 'y2': '@y2', 'up': '@hall_of_mists'}),

    CaveRoom('@window_on_pit',
        article='the',
        called='window on pit',
        sight="""

        [*/s] [are/v] at _a_low_window overlooking _a_huge_pit, which extends
        up out of sight

        _a_floor [is/1/v] indistinctly visible over 50 feet below

        _traces of white _mist [cover/2/v] _the_floor of _the_pit, becoming
        thicker to the right

        _marks in _the_dust around _the_window [seem/2/v] to indicate that
        _someone [have/1/v] been [here] recently

        directly across _the_pit from [*/o] and 25 feet away there [is/1/v]
        _a_similar_window looking into _a_lighted_room

        _a_shadowy_figure [is/1/v] there peering back at [*/o]""",
        exits={'east': '@y2', 'y2': '@y2'}),

    CaveRoom('@dirty_passage',
        article='the',
        called='dirty passage',
        sight="""

        [*/s] [are/v] in _a_dirty_broken_passage

        to the east [is/1/v] _a_crawl

        to the west [is/1/v] _a_large_passage

        above [*/o] [is/1/v] _a_hole to _another_passage""",
        exits={'east': '@brink_of_pit', 'crawl': '@brink_of_pit',
               'up': '@low_passage', 'hole': '@low_passage',
               'west': '@dusty_rock_room', 'bedquilt': '@bedquilt'}),

    CaveRoom('@brink_of_pit',
        article='the',
        called='brink of pit',
        sight="""

        [*/s] [are/v] on _the_brink of _a_small_clean_climbable_pit

        _a_crawl [lead/1/v] west""",
        exits={'west': '@dirty_passage', 'crawl': '@dirty_passage',
               'down': '@bottom_of_pit', 'pit': '@bottom_of_pit',
               'climb': '@bottom_of_pit'}),

    CaveRoom('@bottom_of_pit',
        article='the',
        called='bottom of pit',
        sight="""

        [*/s] [are/v] in the bottom of _a_small_pit with [@stream_in_pit/o],
        which [enter/1/v] and [exit/1/v] through _tiny_slits""",
        exits={'climb': '@brink_of_pit', 'up': '@brink_of_pit',
               'leave': '@brink_of_pit'}),

    Thing('@stream_in_pit part_of @bottom_of_pit',
        article='a',
        called='little stream',
        referring='small | stream creek river spring',
        qualities=['liquid'],
        source='@water',
        mention=False,
        sight='a little stream'),

    CaveRoom('@dusty_rock_room',
        article='the',
        called='dusty rock room',
        sight="""

        [*/s] [are/v] in _a_large_room full of _dusty_rocks

        there [is/1/v] _a_big_hole in _the_floor

        there [are/2/v] _cracks everywhere, and _a_passage leading east""",
        exits={'east': '@dirty_passage', 'tunnel': '@dirty_passage',
               'down': '@complex_junction', 'hole': '@complex_junction',
               'floor': '@complex_junction', 'bedquilt': '@bedquilt'}),

    CaveRoom('@west_end_of_hall_of_mists',
        article='the',
        called='west end of hall of mists',
        sight="""
        [*/s] [are/v] at _the_west_end of _the_Hall_of_Mists

        _a_low_wide_crawl [continue/1/v] west and _another [go/1/v] north

        to the south [is/1/v] _a_little_passage 6 feet off _the_floor""",
        exits={'south': '@maze_1', 'up': '@maze_1', 'tunnel': '@maze_1',
               'climb': '@maze_1', 'east': '@fissure_west',
               'west': '@east_end_of_long_hall',
               'crawl': '@east_end_of_long_hall'}),

    CaveRoom('@maze_1',
        article='the',
        called='maze',
        sight="""

        [*/s] [are/v] in _a_maze of _twisty_little_passages, all alike""",
        exits={'up': '@west_end_of_hall_of_mists', 'north': '@maze_1',
               'east': '@maze_2', 'south': '@maze_4', 'west': '@maze_11'}),

    CaveRoom('@maze_2',
        article='the',
        called='maze',
        sight="""

        [*/s] [are/v] in _a_maze of _twisty_little_passages, all alike""",
        exits={'west': '@maze_1', 'south': '@maze_3', 'east': '@room'}),

    CaveRoom('@maze_3',
        article='the',
        called='maze',
        sight="""

        [*/s] [are/v] in _a_maze of _twisty_little_passages, all alike""",
        exits={'east': '@maze_2', 'down': '@dead_end_3', 'south': '@maze_6',
               'north': '@dead_end_11'}),

    CaveRoom('@maze_4',
        article='the',
        called='maze',
        sight="""

        [*/s] [are/v] in _a_maze of _twisty_little_passages, all alike""",
        exits={'west': '@maze_1', 'north': '@maze_2', 'east': '@dead_end_1',
               'south': '@dead_end_2', 'up': '@maze_14', 'down': '@maze_14'}),

    CaveRoom('@dead_end_1',
        article='the',
        called='dead end',
        referring='dead | end',
        exits={'west': '@maze_4', 'leave': '@maze_4'}),

    CaveRoom('@dead_end_2',
        article='the',
        called='dead end',
        referring='dead | end',
        sight="""
        dead end""",
        exits={'east': '@maze_4', 'leave': '@maze_4'}),

    CaveRoom('@dead_end_3',
        article='the',
        called='dead end',
        referring='dead | end',
        exits={'up': '@maze_3', 'leave': '@maze_3'}),

    CaveRoom('@maze_5',
        article='the',
        called='maze',
        sight="""

        [*/s] [are/v] in _a_maze of _twisty_little_passages, all alike""",
        exits={'east': '@maze_6', 'west': '@maze_7'}),

    CaveRoom('@maze_6',
        article='the',
        called='maze',
        sight="""

        [*/s] [are/v] in _a_maze of _twisty_little_passages, all alike""",
        exits={'east': '@maze_3', 'west': '@maze_5', 'down': '@maze_7',
               'south': '@maze_8'}),

    CaveRoom('@maze_7',
        article='the',
        called='maze',
        sight="""

        [*/s] [are/v] in _a_maze of _twisty_little_passages, all alike""",
        exits={'west': '@maze_5', 'up': '@maze_6', 'east': '@maze_8',
               'south': '@maze_9'}),

    CaveRoom('@maze_8',
        article='the',
        called='maze',
        sight="""

        [*/s] [are/v] in _a_maze of _twisty_little_passages, all alike""",
        exits={'west': '@maze_6', 'east': '@maze_7', 'south': '@maze_8',
               'up': '@maze_9', 'north': '@maze_10', 'down': '@dead_end_13'}),

    CaveRoom('@maze_9',
        article='the',
        called='maze',
        sight="""

        [*/s] [are/v] in _a_maze of _twisty_little_passages, all alike""",
        exits={'west': '@maze_7', 'north': '@maze_8',
               'south': '@dead_end_4'}),

    CaveRoom('@dead_end_4',
        article='the',
        called='dead end',
        referring='dead | end',
        exits={'west': '@maze_9', 'leave': '@maze_9'}),

    CaveRoom('@maze_10',
        article='the',
        called='maze',
        sight="""

        [*/s] [are/v] in _a_maze of _twisty_little_passages, all alike""",
        exits={'west': '@maze_8', 'north': '@maze_10', 'down': '@dead_end_5',
               'east': '@brink_with_column'}),

    CaveRoom('@dead_end_5',
        article='the',
        called='dead end',
        referring='dead | end',
        exits={'up': '@maze_10', 'leave': '@maze_10'}),

    CaveRoom('@brink_with_column',
        article='the',
        called='brink of pit',
        sight="""

        [*/s] [are/v] on _the_brink of _a_thirty_foot_pit with
        _a_massive_orange_column down _one_wall

        [*/s] could climb down [here] but [*/s] could not get back up

        _the_maze [continue/1/v] at _this_level""",
        exits={'down': '@bird_chamber', 'climb': '@bird_chamber',
               'west': '@maze_10', 'south': '@dead_end_6', 'north': '@maze_12',
               'east': '@maze_13'}),

    CaveRoom('@dead_end_6',
        article='the',
        called='dead end',
        referring='dead | end',
        exits={'east': '@brink_with_column', 'leave': '@brink_with_column'}),

    CaveRoom('@east_end_of_long_hall',
        article='the',
        called='east end of long hall',
        sight="""

        [*/s] [are/v] at _the_east_end of _a_very_long_hall apparently without
        _side_chambers

        to the east _a_low_wide_crawl [slant/1/v] up

        to the north _a_round_two-foot_hole [slant/1/v] down""",
        exits={'east': '@west_end_of_hall_of_mists',
               'up': '@west_end_of_hall_of_mists',
               'crawl': '@west_end_of_hall_of_mists',
               'west': '@west_end_of_long_hall',
               'north': '@crossover', 'down': '@crossover',
               'hole': '@crossover'}),

    CaveRoom('@west_end_of_long_hall',
        article='the',
        called='west end of long hall',
        sight="""

        [*/s] [are/v] at _the_west_end of _a_very_long_featureless_hall

        _the_hall [join/1/v] up with _a_narrow_north/south_passage""",
        exits={'east': '@east_end_of_long_hall',
               'north': '@crossover'}),

    CaveRoom('@crossover',
        article='the',
        called='crossover',
        sight="""

        [*/s] [are/v] at _a_crossover of _a_high_north/south_passage and
        _a_low_east/west_one""",
        exits={'west': '@east_end_of_long_hall', 'north': '@dead_end_7',
               'east': '@west_side_chamber',
               'south': '@west_end_of_long_hall'}),

    CaveRoom('@dead_end_7',
        article='the',
        called='dead end',
        referring='dead | end',
        exits={'south': '@crossover', 'leave': '@crossover'}),

    CaveRoom('@complex_junction',
        article='the',
        called='complex junction',
        sight="""

        [*/s] [are/v] at a_complex_junction

        _a_low_hands_and_knees_passage from the north [join/1/v]
        _a_higher_crawl from the east to make _a_walking_passage going west

        there [is/1/v] also _a_large_room above

        _the_air [is/1/v] damp [here]""",
        exits={'up': '@dusty_rock_room', 'climb': '@dusty_rock_room',
               'room': '@dusty_rock_room', 'west': '@bedquilt',
               'bedquilt': '@bedquilt', 'north': '@shell_room',
               'shell': '@shell_room', 'east': '@anteroom'}),

    CaveRoom('@bedquilt',
        article='the',
        called='bedquilt',
        sight="""

        [*/s] [are/v] in Bedquilt, _a_long_east/west_passage with _holes
        everywhere""",
        exits={'east': '@complex_junction', 'west': '@swiss_cheese_room',
               'slab': '@slab_room', 'up': '@dusty_rock_room',
               'north': '@junction_of_three_secret_canyons',
               'down': '@anteroom'}),
        # NEXT STEPS Passages should lead off randomly, south should exist

    CaveRoom('@swiss_cheese_room',
        article='the',
        called='swiss cheese room',
        sight="""

        [*/s] [are/v] in _a_room whose _walls [resemble/1/v] _Swiss_cheese

        _obvious_passages [go/2/v] west, east, northeast, and northwest

        _part of _the_room [is/1/v] occupied by _a_large_bedrock_block""",
        exits={'northeast': '@bedquilt',
               'west': '@east_end_of_twopit_room',
               'canyon': '@tall_canyon', 'south': '@tall_canyon',
               'east': '@soft_room', 'oriental': '@oriental_room'}),

    CaveRoom('@east_end_of_twopit_room',
        article='the',
        called='east end of twopit room',
        exits={'east': '@swiss_cheese_room',
               'west': '@west_end_of_twopit_room',
               'across': '@west_end_of_twopit_room',
               'down': '@east_pit',
               'pit': '@east_pit'},
        sight="""

        [*/s] [are/v] at _the_east_end of _the_Twopit_Room

        _the_floor [here] [is/1/v] littered with _thin_rock_slabs, which
        [make/2/v] it easy to descend _the_pits

        there [is/1/v] _a_path [here] bypassing _the_pits to connect
        _passages from east and west

        there [are/2/v] _holes all over, but the only _big_one [is/1/v]
        on _the_wall directly over _the_west_pit where [*/s] [are/v] unable to
        get to it"""),

    CaveRoom('@slab_room',
        article='the',
        called='slab room',
        exits={'south': '@west_end_of_twopit_room',
               'up': '@secret_canyon_above_room',
               'climb': '@secret_canyon_above_room',
               'north': '@bedquilt'},
        sight="""

        [*/s] [are/v] in _a_large_low_circular_chamber whose _floor [is/v]
        _an_immense_slab fallen from _the_ceiling

        east and west there once were _large_passages, but _they [are/2/v]
        [now] filled with _boulders

        _low_small_passages [go/2/v] north and south, and _the_south_one
        quickly [bend/1/v] west around _the_boulders"""),

    CaveRoom('@secret_canyon_above_room',
        article='the',
        called='secret canyon above room',
        sight="""

        [*/s] [are/v] in _a_secret_north/south_canyon above _a_large_room""",
        exits={'down': '@slab_room', 'slab': '@slab_room',
               'south': '@secret_canyon', 'north': '@mirror_canyon',
               'reservoir': '@reservoir'}),

    CaveRoom('@secret_canyon_above_passage',
        article='the',
        called='secret canyon above passage',
        sight="""

        [*/s] [are/v] in _a_secret_north/south_canyon above
        _a_sizable_passage""",
        exits={'north': '@junction_of_three_secret_canyons',
               'down': '@bedquilt', 'tunnel': '@bedquilt',
               'south': '@top_of_stalactite'}),

    CaveRoom('@junction_of_three_secret_canyons',
        article='the',
        called='junction of three secret canyons',
        sight="""

        [*/s] [are/v] in _a_secret_canyon at _a_junction of _three_canyons,
        bearing north, south, and southeast

        _the_north_one is as tall as _the_other_two combined""",
        exits={'southeast': '@bedquilt',
               'south': '@secret_canyon_above_passage',
               'north': '@window_on_pit_redux'}),

    CaveRoom('@large_low_room',
        article='the',
        called='large low room',
        sight="""

        [*/s] [are/v] in _a_large_low_room

        _crawls lead north, southeast, and southwest""",
        exits={'bedquilt': '@bedquilt', 'southwest': '@sloping_corridor',
               'north': '@dead_end_8', 'southeast': '@oriental_room',
               'oriental': '@oriental_room'}),

    CaveRoom('@dead_end_8',
        article='the',
        called='dead end crawl',
        referring='dead | end crawl',
        exits={'south': '@large_low_room', 'crawl': '@large_low_room',
               'leave': '@large_low_room'}),

    CaveRoom('@secret_east_west_canyon',
        article='the',
        called='secret east/west canyon above tight canyon',
        sight="""

        [*/s] [are/v] in _a_secret_canyon which [here] [run/1/v] east/west

        it [cross/1/v] over _a_very_tight_canyon 15 feet below

        if [*/s] were to go down [*/s] may not be able to get back up""",
        exits={'east': '@hall_of_mountain_king',
               'west': '@secret_canyon', 'down': '@wide_place'}),

    CaveRoom('@wide_place',
        article='the',
        called='wide place',
        sight="""

        [*/s] [are/v] at _a_wide_place in _a_very_tight_north/south_canyon""",
        exits={'south': '@tight_spot', 'north': '@tall_canyon'}),

    CaveRoom('@tight_spot',
        article='the',
        called='tight spot',
        sight='_the_canyon [here] [become/1/v] too tight to go further south',
        exits={'north': '@wide_place'}),

    CaveRoom('@tall_canyon',
        article='the',
        called='tall canyon',
        sight="""

        [*/s] [are/v] in _a_tall_east/west_canyon

        _a_low_tight_crawl [go/1/v] three feet north and [seem/1/v] to open
        up""",
        exits={'east': '@wide_place', 'west': '@dead_end_9',
               'north': '@swiss_cheese_room',
               'crawl': '@swiss_cheese_room'}),

    CaveRoom('@dead_end_9',
        article='the',
        called='dead end',
        referring='dead | end',
        sight="""
        _the_canyon runs into _a_mass_of_boulders -- [*/s] [are/v] at
        _a_dead_end""",
        exits={'south': '@tall_canyon'}),

    CaveRoom('@maze_11',
        article='the',
        called='maze',
        sight="""

        [*/s] [are/v] in _a_maze of _twisty_little_passages, all alike""",
        exits={'north': '@maze_1', 'west': '@maze_11', 'south': '@maze_11',
               'east': '@dead_end_10'}),

    CaveRoom('@dead_end_10',
        article='the',
        called='dead end',
        referring='dead | end',
        exits={'west': '@maze_11', 'leave': '@maze_11'}),

    CaveRoom('@dead_end_11',
        article='the',
        called='dead end',
        referring='dead | end',
        exits={'south': '@maze_3', 'leave': '@maze_3'}),

    CaveRoom('@maze_12',
        article='the',
        called='maze',
        sight='[*/s] [are/v] in _a_maze of _twisty_little_passages, all alike',
        exits={'south': '@brink_with_column', 'east': '@maze_13',
               'west': '@dead_end_12'}),

    CaveRoom('@maze_13',
        article='the',
        called='maze',
        sight='[*/s] [are/v] in _a_maze of _twisty_little_passages, all alike',
        exits={'north': '@brink_with_column', 'west': '@maze_12',
               'northwest': '@dead_end_14'}),

    CaveRoom('@dead_end_12',
        article='the',
        called='dead end',
        referring='dead | end',
        exits={'east': '@maze_12', 'leave': '@maze_12'}),

    CaveRoom('@dead_end_13',
        article='the',
        called='dead end',
        referring='dead | end',
        exits={'up': '@maze_8', 'leave': '@maze_8'}),

    CaveRoom('@maze_14',
        article='the',
        called='maze',
        sight='[*/s] [are/v] in _a_maze of _twisty_little_passages, all alike',
        exits={'up': '@maze_4', 'down': '@maze_4'}),

    CaveRoom('@narrow_corridor',
        article='the',
        called='narrow corridor',
        sight="""

        [*/s] [are/v] in _a_long,_narrow_corridor stretching out of sight to
        _the_west

        at _the_eastern_end [is/v] _a_hole through which [*/s] [can/v] see
        _a_profusion of _leaves""",
        exits={'down': '@west_pit', 'climb': '@west_pit',
               'east': '@west_pit',
               'west': '@giant_room', 'giant': '@giant_room'}),

    CaveRoom('@steep_incline',
        article='the',
        called='steep incline above large room',
        sight="""

        [*/s] [are/v] at _the_top of _a_steep_incline above _a_large_room

        [*/s] could climb down [here], but [*/s] would not be able to climb up

        there is _a_passage leading back to the north""",
        exits={'north': '@cavern_with_waterfall',
               'cavern': '@cavern_with_waterfall',
               'tunnel': '@cavern_with_waterfall',
               'down': '@large_low_room', 'climb': '@large_low_room'}),

    EggSummoning('@giant_room',
        article='the',
        called='giant room',
        sight="""

        [*/s] [are/v] in _the_Giant_Room

        _the_ceiling [here] [is/1/v] too high up for [*'s] lamp to show
        _it

        _cavernous_passages [lead/2/v] east, north, and south

        on _the_west_wall [is/1/v] scrawled _the_inscription,
        "FEE FIE FOE FOO" \[sic]""",
        exits={'south': '@narrow_corridor', 'east': '@blocked_passage',
               'north': '@end_of_immense_passage'}),

    Thing('@eggs in @giant_room',
        article='some',
        called='golden eggs',
        referring='several gold golden | egg eggs',
        qualities=['treasure', 'metal'],
        number='plural',
        sight='several golden eggs'),

    CaveRoom('@blocked_passage',
        article='the',
        called='blocked passage',
        sight='_the_passage [here] [is/1/v] blocked by _a_recent_cave-in',
        exits={'south': '@giant_room', 'giant': '@giant_room',
               'leave': '@giant_room'}),

    CaveRoom('@end_of_immense_passage',
        article='the',
        called='end of immense passage',
        sight='[*/s] [are/v] at _one_end of _an_immense_north/south_passage',
        exits={'south': '@giant_room', 'giant': '@giant_room',
               'tunnel': '@giant_room', 'north': '@rusty_door'}),

    RustyDoor('@rusty_door',
        article='a',
        called='(massive) (rusty) (iron) door',
        referring='| door',
        qualities=['doorway', 'metal'],
        allowed=can.permit_any_item,
        open=False,
        locked=True,
        connects=['@end_of_immense_passage', '@cavern_with_waterfall'],
        sight="""

        a door, placed to restrict passage to the north, which [is/v]
        [now] [open/@rusty_door/a]"""),

    CaveRoom('@cavern_with_waterfall',
        article='the',
        called='cavern with waterfall',
        sight="""

        [*/s] [are/v] in _a_magnificent_cavern with _a_rushing_stream, which
        [cascade/1/v] over [@waterfall/o] into _a_roaring_whirlpool
        which [disappear/1/v] through _a_hole in _the_floor

        _passages [exit/2/v] to the south and west""",
        exits={'south': '@end_of_immense_passage',
               'leave': '@end_of_immense_passage', 'giant': '@giant_room',
               'west': '@steep_incline'}),

    Thing('@waterfall part_of @cavern_with_waterfall',
        article='a',
        called='sparkling waterfalll',
        referring='rushing sparkling roaring | stream creek river spring ' +
                  'waterfall whirlpool',
        qualities=['liquid'],
        source='@water',
        mention=False),

    Thing('@trident in @cavern_with_waterfall',
        article='a',
        called='jewel-encrusted trident',
        referring='jeweled | trident',
        qualities=['treasure', 'metal'],
        sight='a jewel-encrusted trident'),

    CaveRoom('@soft_room',
        article='the',
        called='soft room',
        sight="""

        [*/s] [are/v] in _the_Soft_Room

        _the_walls [are/2/v] covered with _heavy_curtains, _the_floor with
        _a_thick_pile_carpet

        _moss [cover/1/v] _the_ceiling""",
        exits={'west': '@swiss_cheese_room',
               'leave': '@swiss_cheese_room'}),

    Thing('@pillow in @soft_room',
        article='a',
        called='(small) (velvet) pillow',
        referring='| pillow',
        allowed=can.support_one_item),

    CaveRoom('@oriental_room',
        article='the',
        called='oriental room',
        sight="""

        [this] [is/1/v] _the_Oriental_Room

        _ancient_oriental_cave_drawings [cover/2/v] _the_walls

        _a_gently_sloping_passage [lead/1/v] upward to the north,
        _another_passage [lead/1/v] southeast, and _a_hands_and_knees_crawl
        [lead/1/v] west""",
        exits={'southeast': '@swiss_cheese_room',
               'west': '@large_low_room', 'crawl': '@large_low_room',
               'up': '@misty_cavern', 'north': '@misty_cavern',
               'cavern': '@misty_cavern'}),

    Delicate('@vase in @oriental_room',
        article='a',
        called='(delicate) (precious) (Ming) vase',
        referring='| vase',
        qualities=['treasure'],
        sight='a delicate, precious, Ming vase'),

    CaveRoom('@misty_cavern',
        article='the',
        called='misty cavern',
        sight="""

        [*/s] [are/v] following _a_wide_path around _the_outer_edge of
        _a_large_cavern

        far below, through _a_heavy_white_mist, _strange_splashing_noises
        [are/2/v] heard

        _the_mist [rise/1/v] up through _a_fissure in _the_ceiling

        _the_path [exit/1/v] to the south and west""",
        exits={'south': '@oriental_room', 'oriental': '@oriental_room',
               'west': '@alcove'}),

    CaveRoom('@alcove',
        article='the',
        called='alcove',
        sight="""

        [*/s] [are/v] in _an_alcove

        _a_small_northwest_path [seem/1/v] to widen after _a_short_distance

        _an_extremely_tight_tunnel [lead/1/v] east

        it [look/1/v] like _a_very_tight_squeeze

        _an_eerie_light [is/1/v] seen at _the_other_end""",
        exits={'northwest': '@misty_cavern', 'cavern': '@misty_cavern',
               'east': '@plover_room'}),

    CaveRoom('@plover_room',
        article='the',
        called='plover room',
        sight="""

        [*/s] [are/v] in _a_small_chamber lit by _an_eerie_green_light

        _an_extremely_narrow_tunnel [exit/1/v] to the west

        _a_dark_corridor [lead/1/v] northeast""",
        glow=0.5,
        exits={'west': '@alcove', 'plover': '@y2',
               'northeast': '@dark_room', 'dark': '@dark_room'}),

    Thing('@emerald in @plover_room',
        article='an',
        called='emerald',
        referring='| jewel egg',
        qualities=['treasure'],
        sight='an emerald the size of a plover\'s egg'),

    CaveRoom('@dark_room',
        article='the',
        called='dark room',
        sight="""

        [*/s] [are/v] in _the_Dark_Room

        _a_corridor leading south [is/1/v] _the_only_exit""",
        exits={'south': '@plover_room', 'plover': '@plover_room',
               'leave': '@plover_room'}),

    Thing('@pyramid in @dark_room',
        article='a',
        called='platinum pyramid',
        referring='| platinum pyramid',
        qualities=['treasure', 'metal'],
        sight='a platinum pyramid, eight inches on a side'),

    CaveRoom('@arched_hall',
        article='the',
        called='arched hall',
        sight="""

        [*/s] [are/v] in an arched hall

        _a_coral_passage once continued up and east from [here], but [is/1/v]
        [now] blocked by _debris""",
        smell="sea water",
        exits={'down': '@shell_room', 'shell': '@shell_room',
               'leave': '@shell_room'}),

    CaveRoom('@shell_room',
        article='the',
        called='shell room',
        referring='shell |',
        sight="""

        [*/s] [are/v] in _a_large_room carved out of _sedimentary_rock

        _the_floor and _walls [are/2/v] littered with _bits of _shells embedded
        in _the_stone

        _a_shallow_passage [proceed/1/v] downward, and _a_somewhat_steeper_one
        [lead/1/v] up

        a low hands and knees passage [enter/1/v] from the south""",
        exits={'up': '@arched_hall', 'hall': '@arched_hall',
               'down': '@long_sloping_corridor',
               'south': '@complex_junction'}),

    Oyster('@oyster in @shell_room',
        article='a',
        called='(enormous) clam',
        referring='tightly closed tightly-closed | bivalve',
        open=False,
        sight='a tightly-closed and enormous bivalve'),

    Thing('@pearl in @oyster',
        article='a',
        called='glistening pearl',
        referring='| pearl',
        qualities=['treasure'],
        sight='a glistening pearl'),

    CaveRoom('@long_sloping_corridor',
        article='the',
        called='long sloping corridor',
        sight="""

        [*/s] [are/v] in _a_long_sloping_corridor with _ragged_sharp_walls""",
        exits={'up': '@shell_room', 'shell': '@shell_room',
               'down': '@cul_de_sac'}),

    CaveRoom('@cul_de_sac',
        article='the',
        called='cul-de-sac',
        sight='[*/s] [are/v] in _a_cul-de-sac about eight feet across',
        exits={'up': '@long_sloping_corridor',
               'leave': '@long_sloping_corridor',
               'shell': '@shell_room'}),

    CaveRoom('@anteroom',
        article='the',
        called='anteroom',
        sight="""

        [*/s] [are/v] in _an_anteroom leading to _a_large_passage to the east

        _small_passages [go/2/v] west and up

        _the_remnants of recent digging [are/2/v] evident

        _a_sign in midair [here] [say/1/v]: "Cave under construction beyond
        this point. Proceed at own risk. \[Witt Construction Company]\"""",
        exits={'up': '@complex_junction', 'west': '@bedquilt',
               'east': '@witts_end'}),

    Thing('@magazine in @anteroom',
        article='some',
        called='magazines',
        referring='a few recent | issues magazine magazines',
        number='plural',
        sight='a few recent issues of "Spelunker Today" magazine'),

    CaveRoom('@maze_15',
        article='the',
        called='maze',
        sight="""

        [*/s] [are/v] in _a_maze of _twisty_little_passages, all different""",
        exits={'south': '@maze_17', 'southwest': '@maze_18',
               'northeast': '@maze_19', 'southeast': '@maze_20',
               'up': '@maze_21', 'northwest': '@maze_22', 'east': '@maze_23',
               'west': '@maze_24', 'north': '@maze_25',
               'down': '@west_end_of_long_hall'}),

    CaveRoom('@witts_end',
        called="Witt's End",
        sight="""

        [*/s] [are/v] at _Witt's_End

        _passages [lead/2/v] off ... well, east and west""",
        exits={'east': '@anteroom', 'west': '@crossover'}),
        # NEXT STEPS Passages should lead off "in ALL directions", randomness

    CaveRoom('@mirror_canyon',
        article='the',
        called='mirror canyon',
        sight="""

        [*/s] [are/v] in _a_north/south_canyon about 25 feet across

        _the_floor [is/1/v] covered by _white_mist seeping in from the north

        _the_walls [extend/2/v] upward for well over 100 feet

        suspended from _some_unseen_point far above [*/s],
        _an_enormous_two-sided_mirror [hang/ing/1/v] parallel to and midway 
        between the _canyon_walls

        (_The_mirror [is/1/v] obviously provided for the use of _the_dwarves,
        who are extremely vain.)

        _a_small_window [is/1/v] seen in _either_wall, some fifty feet up""",
        exits={'south': '@secret_canyon_above_room',
               'north': '@reservoir', 'reservoir': '@reservoir'}),

    CaveRoom('@window_on_pit_redux',
        article='the',
        called='window on pit',
        sight="""

        [*/s] [are/v] at _a_low_window overlooking _a_huge_pit, which
        [extend/1/v] up out of sight

        _a_floor [is/1/v] indistinctly visible over 50 feet below

        _traces of _white_mist [cover/2/v] _the_floor of _the_pit, becoming
        thicker to the left

        _marks in _the_dust around _the_window [seem/2/v] to indicate that
        _someone has been [here] recently

        directly across _the_pit from [*/o] and 25 feet away there [is/1/v]
        _a_similar_window looking into _a_lighted_room

        _a_shadowy_figure [is/1/v] seen there peering back at [*/s]""",
        exits={'west': '@junction_of_three_secret_canyons'}),

    CaveRoom('@top_of_stalactite',
        article='the',
        called='top of stalactite',
        sight="""

        _a_large_stalactite [extend/1/v] from _the_roof and almost [reach/1/v]
        _the_floor below

        [*/s] could climb down _it, and jump from _it to _the_floor, but having
        done so [*/s] would be unable to reach _it to climb back up""",
        exits={'north': '@secret_canyon_above_passage', 'down': '@maze_4'}),

    CaveRoom('@maze_16',
        article='the',
        called='maze',
        sight="""

        [*/s] [are/v] in _a_little_maze of _twisting_passages, all different""",
        exits={'southwest': '@maze_17', 'north': '@maze_18',
               'east': '@maze_19', 'northwest': '@maze_20',
               'southeast': '@maze_21', 'northeast': '@maze_22',
               'west': '@maze_23', 'down': '@maze_24', 'up': '@maze_25',
               'south': '@dead_end_15'}),

    CaveRoom('@reservoir',
        article='the',
        called='edge of the reservoir',
        referring='| edge',
        sight="""

        [*/s] [are/v] at _the_edge of _a_large_underground_reservoir

        _an_opaque_cloud of _white_mist [fill/1/v] _the_room and [rise/1/v]
        rapidly upward

        _the_lake [is/1/v] fed by _a_stream, which [tumble/1/v] out of _a_hole
        in _the_wall about 10 feet overhead and [splash/1/v] noisily into
        _the_water somewhere within _the_mist

        _the_only_passage [go/1/v] back toward the south""",
        exits={'south': '@mirror_canyon', 'leave': '@mirror_canyon'}),

    Thing('@lake part_of @reservoir',
        article='a',
        called='a large underground lake',
        referring='large underground | stream creek river spring lake',
        source='@water',
        mention=False),

    CaveRoom('@dead_end_14',
        article='the',
        called='dead end',
        referring='dead | end',
        exits={'southeast': '@maze_13'}),

    Thing('@chest in @dead_end_14',
        article='the',
        called="(pirate's) treasure chest",
        referring='| chest',
        qualities=['treasure'],
        sight="the pirate's treasure chest",
        allowed=can.contain_any_treasure),

    CaveRoom('@northeast_end',
        article='the',
        called='northeast end',
        sight="""

        [*/s] [are/v] at _the_northeast_end of _an_immense_room, even larger
        than _the_giant_room

        it [appear/1/v] to be _a_repository for _the_"ADVENTURE"_program

        _massive_torches far overhead [bathe/2/v] _the_room with
        _smoky_yellow_light

        scattered about [*/s] [see/v] _a_pile_of_bottles (all of them
        empty), _a_nursery of _young_beanstalks murmuring quietly, _a_bed of
        _oysters, _a_bundle of _black_rods with _rusty_stars on _their_ends,
        and _a_collection_of_brass_lanterns

        off to _one_side a_great_many_dwarves [sleep/ing/2/v] on _the_floor,
        snoring loudly

        _a_sign nearby [read/1/v]: "Do not disturb the dwarves!"

        _an_immense_mirror [hang/ing/v] against _one_wall, and [stretch/1/v]
        to _the_other_end of _the_room, where _various_other_sundry_objects
        [are/2/v] glimpsed dimly in the distance""",
        exits={'southwest': '@southwest_end'}),

    CaveRoom('@southwest_end',
        article='the',
        called='southwest end',
        sight="""

        [*/s] [are/v] at _the_southwest end of _the_repository

        to _one_side [is/1/v] _a_pit full of _fierce_green_snakes

        on _the_other_side [is/1/v] _a_row of _small_wicker_cages, each of
        which [contain/1/v] _a_little_sulking_bird

        in _one_corner [is/1/v] _a_bundle of _black_rods with _rusty_marks on
        _their_ends

        _a_large_number of _velvet_pillows [are/2/v] scattered about on
        _the_floor

        _a_vast_mirror [stretch/1/v] off to the northeast

        at [*'s] _feet [is/1/v] _a_large_steel_grate, next to which
        [is/1/v] _a_sign which [read/1/v], "Treasure vault. Keys in Main
        Office\"""",
        exits={'northeast': '@northeast_end'}),

    Thing('@black_rod in @southwest_end',
        article='a',
        called='small black rod',
        referring='small black | rod',
        sight='a small black rod'),

    Button('@button in @southwest_end',
        article='a',
        called='button',
        referring='red | button',
        sight='just a red button'),

    CaveRoom('@southwest_side_of_chasm',
        article='the',
        called='southwest side of chasm',
        sight="""

        [*/s] [are/v] on _one_side of _a_large,_deep_chasm

        _a_heavy_white_mist rising up from below [obscure/1/v] _all_view of
        _the_far_side

        _a_southwest_path [lead/1/v] away from _the_chasm into
        _a_winding_corridor""",
        exits={'southwest': '@sloping_corridor',
               'over': '@northeast_side_of_chasm',
               'cross': '@northeast_side_of_chasm',
               'northeast': '@northeast_side_of_chasm'}),

    Troll('@troll in @southwest_side_of_chasm',
        article='a',
        called='(burly) troll',
        referring=' | monster guardian',
        sight='[this] [is/1/v] just a burly troll, barring the way',
        allowed=can.possess_any_treasure,
        blocked=['northeast', 'over', 'cross']),

    CaveRoom('@sloping_corridor',
        article='the',
        called='sloping corridor',
        sight="""

        [*/s] [are/v] in _a_long_winding_corridor sloping out of sight in
        both directions""",
        exits={'down': '@large_low_room',
               'up': '@southwest_side_of_chasm'}),

    CaveRoom('@secret_canyon',
        article='the',
        called='secret canyon',
        sight="""

        [*/s] [are/v] in _a_secret_canyon which [exit/1/v] to the north and
        east""",
        exits={'north': '@secret_canyon_above_room',
               'east': '@secret_east_west_canyon'}),

    Thing('@rug in @secret_canyon',
        article='a',
        called='(Persian) rug',
        referring='persian | rug',
        qualities=['treasure'],
        allowed=can.support_any_item_or_dragon,
        sight='a Persian rug'),

    Dragon('@dragon on @rug',
        article='a',
        called='huge dragon',
        referring='huge green fierce | dragon',
        sight='[this] [is/1/v] just a huge dragon, barring the way',
        blocked=['north', 'onward']),

    CaveRoom('@northeast_side_of_chasm',
        article='the',
        called='northeast side of chasm',
        sight="""

        [*/s] [are/v] on _the_far_side of _the_chasm

        _a_northeast_path [lead/1/v] away from _the_chasm on [this] side""",
        exits={'northeast': '@corridor',
               'over': '@southwest_side_of_chasm',
               'fork': '@fork_in_path',
               'view': '@breath_taking_view',
               'barren': '@front_of_barren_room',
               'southwest': '@southwest_side_of_chasm',
               'cross': '@southwest_side_of_chasm'}),

    CaveRoom('@corridor',
        article='the',
        called='corridor',
        sight="""

        [*/s] [are/v] in a long east/west corridor

        _a_faint_rumbling_noise [is/1/v] heard in the distance""",
        exits={'west': '@northeast_side_of_chasm',
               'east': '@fork_in_path', 'fork': '@fork_in_path',
               'view': '@breath_taking_view',
               'barren': '@front_of_barren_room'}),

    CaveRoom('@fork_in_path',
        article='the',
        called='fork in path',
        sight="""

        _the_path [fork/1/v] [here]

        _the_left_fork [lead/1/v] northeast

        _a_dull_rumbling [seem/1/v] to get louder in that direction

        _the_right_fork [lead/1/v] southeast down _a_gentle_slope

        _the_main_corridor [enter/1/v] from the west""",
        exits={'west': '@corridor',
               'northeast': '@junction_with_warm_walls',
               'left': '@junction_with_warm_walls',
               'southeast': '@limestone_passage',
               'right': '@limestone_passage',
               'down': '@limestone_passage',
               'view': '@breath_taking_view',
               'barren': '@front_of_barren_room'}),

    CaveRoom('@junction_with_warm_walls',
        article='the',
        called='junction with warm walls',
        sight="""

        _the_walls [are/2/v] quite warm here

        from the north [*/s] [hear/v] _a_steady_roar, so loud that
        _the_entire_cave [seem/1/v] to be trembling

        _another_passage [lead/1/v] south, and _a_low_crawl [go/1/v] east""",
        exits={'south': '@fork_in_path', 'fork': '@fork_in_path',
               'north': '@breath_taking_view',
               'view': '@breath_taking_view',
               'east': '@chamber_of_boulders',
               'crawl': '@chamber_of_boulders'}),

    CaveRoom('@breath_taking_view',
        article='the',
        called='breath-taking view',
        sight="""

        [*/s] [are/v] on _the_edge of _a_breath-taking_view

        far below [*/s] [is/1/v] _an_active_volcano, from which _great_gouts
        of _molten_lava [come/2/v] surging out, cascading back down into
        _the_depths

        _the_glowing_rock [fill/1/v] _the_farthest_reaches of _the_cavern with
        _a_blood-red_glare, giving _everything _an_eerie,_macabre_appearance

        _the_air [is/1/v] filled with flickering sparks of ash

        _the_walls [are/2/v] hot to the touch, and _the_thundering of
        _the_volcano [drown/1/v] out all other sounds

        embedded in _the_jagged_roof far overhead [are/1/v]
        _myriad_twisted_formations composed of _pure_white_alabaster,
        which scatter _the_murky_light into _sinister_apparitions upon
        _the_walls

        to _one_side [is/1/v] _a_deep_gorge, filled with _a_bizarre_chaos of
        _tortured_rock which seems to have been crafted by _the_devil _himself

        _an_immense_river of _fire [crash/1/v] out from _the_depths of
        _the_volcano, [burn/1/v] its way through _the_gorge, and [plummet/1/v]
        into _a_bottomless_pit far off to [*'s] left

        to _the_right, _an_immense_geyser of _blistering_steam [erupt/1/v]
        continuously from _a_barren_island in _the_center of
        _a_sulfurous_lake, which bubbles ominously

        _the_far_right_wall [is/1/v] aflame with _an_incandescence of its
        own, which [lend/1/v] _an_additional_infernal_splendor to
        _the_already_hellish_scene

        _a_dark,_foreboding_passage [exit/1/v] to the south""",
        smell="a heavy smell of brimstone",
        exits={'south': '@junction_with_warm_walls',
               'tunnel': '@junction_with_warm_walls',
               'leave': '@junction_with_warm_walls',
               'fork': '@fork_in_path',
               'down': '@west_end_of_long_hall',
               'jump': '@west_end_of_long_hall'}),

    CaveRoom('@chamber_of_boulders',
        article='the',
        called='chamber of boulders',
        sight="""

        [*/s] [are/v] in _a_small_chamber filled with _large_boulders

        _the_walls [are/2/v] very warm, causing _the_air in _the_room to be
        almost stifling from _the_heat

        _the_only_exit [is/1/v] _a_crawl heading west, through which [is/1/v]
        coming _a_low_rumbling""",
        exits={'west': '@junction_with_warm_walls',
               'leave': '@junction_with_warm_walls',
               'crawl': '@junction_with_warm_walls',
               'fork': '@fork_in_path', 'view': '@breath_taking_view'}),

    Thing('@spices in @chamber_of_boulders',
        article='some',
        called='rare spices',
        referring='rare | spice spices',
        qualities=['treasure'],
        sight='rare spices'),

    CaveRoom('@limestone_passage',
        article='the',
        called='limestone passage',
        sight="""

        [*/s] [are/v] walking along _a_gently_sloping_north/south_passage
        lined with _oddly_shaped_limestone_formations""",
        exits={'north': '@fork_in_path', 'up': '@fork_in_path',
               'fork': '@fork_in_path',
               'south': '@front_of_barren_room',
               'down': '@front_of_barren_room',
               'barren': '@front_of_barren_room',
               'view': '@breath_taking_view'}),

    CaveRoom('@front_of_barren_room',
        article='the',
        called='front of barren room',
        sight="""

        [*/s] [stand/ing/v] at _the_entrance to _a_large,_barren_room

        _a_sign posted above _the_entrance [read/1/v]: "Caution! Bear in
        room!\"""",
        exits={'west': '@limestone_passage',
               'up': '@limestone_passage', 'fork': '@fork_in_path',
               'east': '@barren_room', 'in': '@barren_room',
               'barren': '@barren_room', 'enter': '@barren_room',
               'view': '@breath_taking_view'}),

    CaveRoom('@barren_room',
        article='the',
        called='barren room',
        sight="""

        [*/s] [are/v] inside _a_barren_room

        _the_center of _the_room [is/1/v] completely empty except for
        _some_dust

        marks in _the_dust [lead/2/v] away toward _the_far_end of _the_room

        the only exit [is/1/v] the way you came in""",
        exits={'west': '@front_of_barren_room',
               'leave': '@front_of_barren_room',
               'fork': '@fork_in_path',
               'view': '@breath_taking_view'}),

    Bear('@bear in @barren_room',
        article='a',
        called='(ferocious) (cave) bear',
        referring=' | animal creature',
        sight='a ferocious cave bear, currently [angry/@bear/a]',
        allowed=can.possess_any_thing),

    Thing('@hook part_of @barren_room',
        article='a',
        called='(small) hook',
        referring='| peg',
        qualities=['metal'],
        allowed=can.support_chain,
        sight='a small metal hook, somehow affixed to the cave wall'),

    Thing('@chain on @hook',
        article='a',
        called='(golden) chain',
        referring='gold | leash',
        qualities=['treasure', 'metal'],
        sight='just an ordinary golden chain'),

    CaveRoom('@maze_17',
        article='the',
        called='maze',
        sight="""

        [*/s] [are/v] in _a_maze of _twisting_little_passages, all different""",
        exits={'west': '@maze_15', 'southeast': '@maze_18',
               'northwest': '@maze_19', 'southwest': '@maze_20',
               'northeast': '@maze_21', 'up': '@maze_22',
               'down': '@maze_23', 'north': '@maze_24',
               'south': '@maze_25', 'east': '@maze_16'}),

    CaveRoom('@maze_18',
        article='the',
        called='maze',
        sight="""

        [*/s] [are/v] in _a_little_maze of _twisty_passages, all different""",
        exits={'northwest': '@maze_15', 'up': '@maze_17',
               'north': '@maze_19', 'south': '@maze_20', 'west': '@maze_21',
               'southwest': '@maze_22', 'northeast': '@maze_23',
               'east': '@maze_24', 'down': '@maze_25',
               'southeast': '@maze_16'}),

    CaveRoom('@maze_19',
        article='the',
        called='maze',
        sight="""

        [*/s] [are/v] in _a_twisting_maze of _little_passages, all different""",
        exits={'up': '@maze_15', 'down': '@maze_17', 'west': '@maze_18',
               'northeast': '@maze_20', 'southwest': '@maze_21',
               'east': '@maze_22', 'north': '@maze_23',
               'northwest': '@maze_24', 'southeast': '@maze_25',
               'south': '@maze_16'}),

    CaveRoom('@maze_20',
        article='the',
        called='maze',
        sight="""
        [*/s] [are/v] in _a_twisting_little_maze of _passages, all different""",
        exits={'northeast': '@maze_15', 'north': '@maze_17',
               'northwest': '@maze_18', 'southeast': '@maze_19',
               'east': '@maze_21', 'down': '@maze_22',
               'south': '@maze_23', 'up': '@maze_24',
               'west': '@maze_25', 'southwest': '@maze_16'}),

    CaveRoom('@maze_21',
        article='the',
        called='maze',
        sight="""

        [*/s] [are/v] in _a_twisty_little_maze of _passages, all different""",
        exits={'north': '@maze_15', 'southeast': '@maze_17',
               'down': '@maze_18', 'south': '@maze_19',
               'east': '@maze_20', 'west': '@maze_22',
               'southwest': '@maze_23', 'northeast': '@maze_24',
               'northwest': '@maze_25', 'up': '@maze_16'}),

    CaveRoom('@maze_22',
        article='the',
        called='maze',
        sight="""

        [*/s] [are/v] in _a_twisty_maze of _little_passages, all different""",
        exits={'east': '@maze_15', 'west': '@maze_17', 'up': '@maze_18',
               'southwest': '@maze_19', 'down': '@maze_20',
               'south': '@maze_21', 'northwest': '@maze_23',
               'southeast': '@maze_24', 'northeast': '@maze_25',
               'north': '@maze_16'}),

    CaveRoom('@maze_23',
        article='the',
        called='maze',
        sight="""

        [*/s] [are/v] in _a_little_twisty_maze of _passages, all different""",
        exits={'southeast': '@maze_15', 'northeast': '@maze_17',
               'south': '@maze_18', 'down': '@maze_19', 'up': '@maze_20',
               'northwest': '@maze_21', 'north': '@maze_22',
               'southwest': '@maze_24', 'east': '@maze_25',
               'west': '@maze_16'}),

    CaveRoom('@maze_24',
        article='the',
        called='maze',
        sight="""

        [*/s] [are/v] in _a_maze of _little_twisting_passages, all different""",
        exits={'down': '@maze_15', 'east': '@maze_17',
               'northeast': '@maze_18', 'up': '@maze_19',
               'west': '@maze_20', 'north': '@maze_21', 'south': '@maze_22',
               'southeast': '@maze_23', 'southwest': '@maze_25',
               'northwest': '@maze_16'}),

    CaveRoom('@maze_25',
        article='the',
        called='maze',
        sight="""

        [*/s] [are/v] in _a_maze of _little_twisty_passages, all different""",
        exits={'southwest': '@maze_15', 'northwest': '@maze_17',
               'east': '@maze_18', 'west': '@maze_19', 'north': '@maze_20',
               'down': '@maze_21', 'southeast': '@maze_22',
               'up': '@maze_23', 'south': '@maze_24',
               'northeast': '@maze_16'}),

    CaveRoom('@dead_end_15',
        article='the',
        called='dead end',
        referring='dead | end',
        exits={'north': '@maze_16', 'leave': '@maze_16'})]


########NEW FILE########
__FILENAME__ = artmaking
'Artmaking, a tiny demonstration game for Curveship.'

__author__ = 'Nick Montfort'
__copyright__ = 'Copyright 2011 Nick Montfort'
__license__ = 'ISC'
__version__ = '0.5.0.0'

from item_model import Actor, Room, Thing
from action_model import Modify, Sense
import can
import when

discourse = {
    'metadata': {
        'title': 'Artmaking',
        'headline': 'A very simple example',
        'people': [('by', 'Nick Montfort')],
        'prologue': 'Settle for nothing less than an artistic breakthrough.'},
    'spin':
    {'commanded': '@artist', 'focalizer': '@artist', 'narratee': '@artist'}}

initial_actions = [Sense('ogle', '@artist', direct='@studio', modality='sight')]

class Art(Thing):
    '@sculpture is the only instance.'

    def react(self, world, basis):
        'Win the game when smashed.'
        actions = []
        if (basis.verb in ['kick', 'strike'] and basis.direct == str(self)):
            damage = Modify('puncture', basis.agent, direct=str(self),
                            feature='intact', new=False)
            damage.after = """finally, a worthy contribution to the art world
            ... victory!"""
            damage.final = True
            actions = [damage]
        return actions

items = [
    Actor('@artist in @studio',
        article='the',
        called='artist',
        gender='female',
        allowed=can.possess_any_item,
        refuses=[('LEAVE way=(north|out)', when.always,
                 '[@artist/s] [have/v] work to do')]),

    Room('@studio',
        article='the',
        called='studio',
        exits={},
        sight='a bare studio space with a single exit, to the north'),

    Thing('@box in @studio',
        article='a',
        called='box',
        open=False,
        allowed=can.contain_and_support_things,
        sight='the medium-sized parcel [is/1/v] [open/@box/a]'),

    Art('@sculpture in @box',
        article='a',
        called='sculpture',
        intact=True,
        sight='a sculpture of a mountain, made to order in China')]


########NEW FILE########
__FILENAME__ = cloak
﻿"""Cloak of Darkness

An implementation of Roger Firth's Cloak of Darkness (1999) in Curveship,
an interactive fiction development system by Nick Montfort."""

__author__ = 'Nick Montfort (based on a game by Roger Firth)'
__copyright__ = 'Copyright 2011 Nick Montfort'
__license__ = 'ISC'
__version__ = '0.5.0.0'
__status__ = 'Development'

from item_model import Actor, Room, Thing
from action_model import Behave, Modify, Sense
import can
import when

discourse = {

    'metadata': {
        'title': 'Cloak of Darkness',
        'headline': 'A Basic IF Demonstration',
        'people': [('Curveship implementation by', 'Nick Montfort'),
                   ('original game by', 'Roger Firth')],
        'prologue': ''},

    'command_grammar': {
        'PUT_ON ACCESSIBLE ACCESSIBLE':
         ['put ACCESSIBLE onto ACCESSINLE',
          '(hang|put|place) ACCESSIBLE (up )?(atop|on|onto) ACCESSIBLE',
          '(hang|put)( up)? ACCESSIBLE (atop|on|onto) ACCESSIBLE']},

    'action_templates': [
        ('PUT new_link=on new_parent=@hook',
         '[agent/s] [hang/v] [direct/o] up on [indirect/o]')],

    'spin': {
        'focalizer': '@person',
        'commanded': '@person',
        'narratee': '@person',
        'known_directions': True}}

ARRIVE = Behave('arrive', '@person',
                template="""
                hurrying through the rainswept November night, [@person/s] 
                [are/v] glad to see the bright lights of the Opera House""",
                indirect='@foyer')
ARRIVE.after = """it [is/1/v] surprising that there [are/not/2/v] more people 
               about but, hey, what should [@person/s] expect in a cheap demo 
               game?"""

LOOK_AROUND = Sense('see', '@person', direct='@foyer', modality='sight')

initial_actions = [ARRIVE, LOOK_AROUND]

class ScrawledMessage(Thing):

    def __init__(self, tag, **keywords):
        self.intact = True
        Thing.__init__(self, tag, **keywords)

    def react(self, world, basis):
        actions = []
        if (basis.sense and basis.direct == '@message' and
            basis.modality == 'sight'):
            sigh =  Behave('sigh', basis.agent)
            sigh.final = True
            actions.append(sigh)
        return actions

    def react_to_failed(self, world, basis):
        actions = []
        if (basis.behave and basis.verb == 'leave' and self.intact):
            actions.append(Modify('trample', basis.agent,
                                  direct='@message', feature='intact',
                                  new=False, salience=0))
            sight = """
            the message, now little but a cipher of trampled sawdust, 
            [seem/1/v] to read: [begin-caps] [*/s] [lose/ed/v]"""
            actions.append(Modify('rewrite', basis.agent, 
                                  direct=str(self), feature='sight',
                                  new=sight, salience=0))
        return actions

def support_cloak(tag, link, world):
    return (tag, link) == ('@cloak', 'on')

def possess_things_and_wear_cloak(tag, link, world):
    return ((tag, link) == ('@cloak', 'on') or
            link == 'of' and can.have_only_things(tag, link, world))

can.support_cloak = support_cloak
can.possess_things_and_wear_cloak = possess_things_and_wear_cloak

def in_foyer(world):
    return str(world.room_of('@person')) == '@foyer'

when.in_foyer = in_foyer

items = [

    Actor('@person in @foyer',
        article='the',
        called='operagoer',
        referring='| operagoer',
        qualities=['person', 'woman'],
        allowed=can.possess_things_and_wear_cloak,
        gender='female',
        refuses=[
        ('behave LEAVE direct=@person way=north', when.in_foyer,
         """[*/s] [have/v] only just arrived, and besides, the weather
         outside [seem/1/v] to be getting worse"""),
        ('configure direct=@cloak new_parent=@foyer', when.always,
         """the floor [is/not/1/v] the best place to leave a smart cloak
         lying around""")],
        sight="""
        [*/s] [see/v] a typically nondescript character"""),

    Thing('@cloak on @person',
        article='a',
        called='(handsome) cloak (of darkness)',
        referring='black damp trimmed with satin smart soft sumptuous ' +
                  'velvet | cape',
        qualities=['clothing'],
        glow=-0.5,
        sight="""
        [@cloak/s] [is/v] of velvet trimmed with satin and [is/v] slightly
        spattered with raindrops

        [@cloak's] blackness [is/1/v] so deep that it [seem/1/v] to suck light
        from the room""",
        touch="""
        a material that [is/1/v] soft and sumptuous, despite being damp"""),

    Room('@foyer',
        article='the',
        called='(splendid) foyer (of the opera house)',
        referring='splendidly decorated red gold spacious | hall',
        exits={'south': '@bar', 'west': '@cloakroom'},
        sight="""
        [*/s] [see/v] [*/o] standing in a spacious hall, splendidly decorated
        in red and gold, with glittering chandeliers overhead

        the entrance from the street [is/1/v] to the north, and there [are/2/v]
        doorways south and west"""),

    Room('@cloakroom',
        article='a',
        called='(small) cloakroom',
        referring='cloak hat check | room check checkroom hatcheck',
        exits={'east':'@foyer'},
        sight="""
        [*/s] [see/v] that clearly, the walls of this small room were once
        lined with hooks, though [now] only one [remain/1/v]

        the exit [is/1/v] a door to the east"""),

    Thing('@hook part_of @cloakroom',
        article='a',
        called='(small) (brass) hook',
        referring='| peg',
        qualities=['metal'],
        allowed=can.support_cloak,
        sight="""
        [this] [is/v] just a small brass hook, screwed to the wall""",
        mention=False),

    Room('@bar',
        article='a',
        called='(empty) (foyer) bar',
        referring='rough rougher |',
        glow=0.4,
        exits={'north': '@foyer'},
        sight="""
        the bar, much rougher than [*/s] would have guessed after the opulence
        of the foyer to the north, [is/1/v] completely empty

        there [seem/1/v] to be some sort of message scrawled in the sawdust on
        the floor"""),

    ScrawledMessage('@message part_of @bar',
        article='a',
        called='(scrawled) message',
        referring='trampled | sawdust message floor scrawl',
        sight="""
        the message, neatly marked in the sawdust, [read/1/v]:
        [begin-caps] [*/s] [win/ed/v]""")]


########NEW FILE########
__FILENAME__ = cplus
"""Cloak of Darkness Plus

An augmentation of Roger Firth's Cloak of Darkness (1999) in Curveship,
an interactive fiction development system by Nick Montfort."""

__author__ = 'Nick Montfort (extending a game by Roger Firth)'
__copyright__ = 'Copyright 2011 Nick Montfort'
__license__ = 'ISC'
__version__ = '0.5.0.0'
__status__ = 'Development'

from item_model import Actor, Thing, Substance
from action_model import Modify
import can

import fiction.cloak

discourse = fiction.cloak.discourse
discourse['metadata']['title'] = 'Cloak of Darkness Plus'
discourse['metadata']['people'] = [
    ('augmented and implemented in Curveship by', 'Nick Montfort'),
    ('original game by', 'Roger Firth')]

initial_actions = fiction.cloak.initial_actions


class Lamp(Thing):
    '@lamp is the only instance.'

    def react(self, _, basis):
        'Increase/decrease the light emitted when turned on/off.'
        actions = []
        if (basis.modify and basis.direct == str(self) and 
            basis.feature == 'on'):
            # If turned on, make it glow; otherwise, have it stop glowing.
            if basis.new_value:
                actions.append(Modify('light', basis.agent,
                                      direct=str(self), feature='glow',
                                      new=0.6, salience=0.1))
            else:
                actions.append(Modify('extinguish', basis.agent,
                                      direct=str(self), feature='glow',
                                      new=0.0, salience=0.1))
        return actions


class Waver(Actor):
    '@mime is the only instance.'

    def __init__(self, tag, **keywords):
        self.waves_next_turn = True
        self.angry = False
        Actor.__init__(self, tag, **keywords)

    def act(self, command_map, concept):
        actions = []
        self.waves_next_turn = not self.waves_next_turn
        if self.waves_next_turn and not self.angry:
            actions.append(self.do_command('wave', command_map, concept))
        return actions


items = fiction.cloak.items + [

    Substance('@water',
        called='water',
        referring='clear |',
        qualities=['drink', 'liquid'],
        consumable=True,
        sight='clear water',
        taste="nothing unpleasant"),

    Waver('@mime in @foyer',
        article='a',
        called='(dazed) mime',
        referring='oblivious strange | greeter character',
        allowed=can.possess_things_and_wear_cloak,
        qualities=['person', 'man'],
        gender='male',
        sight="""

        [here] [is/1/v] a strange character who [seem/1/v] almost completely
        oblivious to everything""",
        start=50),

    Thing('@bottle in @foyer',
        article='a',
        called='(clear) (glass) bottle',
        open=False,
        transparent=True,
        vessel='@water',
        sight='a clear glass bottle, currently [open/@bottle/a]',
        touch="smooth glass"),

    Thing('@ticket of @person',
        article='a',
        called='ticket',
        referring='opera |',
        sight="""

        [@ticket/ordinary/s] [read/v] "VALID FOR A NIGHT AT THE OPERA UNLESS
        IT RAINS"

        """),

    Thing('@massive_sack in @foyer',
        article='a',
        called='(plain) massive sack',
        referring='massive | bag sack',
        allowed=can.contain_and_support_any_item,
        sight='a plain sack, totally massive',
        open=True),

    Thing('@large_sack in @foyer',
        article='a',
        called='(plain) large sack',
        referring='large | bag sack',
        allowed=can.contain_any_thing,
        sight='a plain sack, quite large',
        open=True),

    Lamp('@lamp in @cloakroom',
        article='a',
        called='(shiny) (brass) (carbide) lamp',
        referring='| lantern light',
        qualities=['device', 'metal'],
        on=False,
        flame=True,
        sight="""

        [@lamp/nifty/s] [here] [is/v] the kind often used for illuminating caves

        [@lamp/s] [is/v] shiny and [glow/@lamp/a]
        """)]

########NEW FILE########
__FILENAME__ = lost_one
"""Lost One

A demo interactive fiction in Curveship, an IF development system by
Nick Montfort. Shows how narrative distance can be changed based on the
player character's actions."""

__author__ = 'Nick Montfort'
__copyright__ = 'Copyright 2011 Nick Montfort'
__license__ = 'ISC'
__version__ = '0.5.0.0'
__status__ = 'Development'

import random
import time

from item_model import Actor, Thing
from action_model import Behave, Sense
import can

import fiction.plaza

discourse = {
    'metadata': {
        'title': 'Lost One',
        'headline': 'An Interactive Demo',
        'people': [('by', 'Nick Montfort')]},

    'action_templates': [
        ('KICK', '[agent/s] [give/v] [direct/o] a fierce kick'),
        ('SHINE', 'the sun [hit/1/v] the plaza')],

    'spin': {
        'focalizer': '@visitor',
        'commanded': '@visitor',
        'speed': 0.5,
        'time': 'during',
        'order': 'chronicle',
        'narratee': '@visitor',
        'narrator': None,
        'known_directions': False,
        'room_name_headings': False,
        'time_words': False,
        'dynamic': True}}

SHINE = Behave('shine', '@cosmos', direct='@visitor')
SHINE.after ="""

[now] they [drive/2/v] cars, seeking flatpacks across the sprawl

once they were supposed to cluster [here]

[@visitor/s] [arrive/ed/v], visitor to this place where [@visitor/s] briefly 
lived years ago, where [@visitor/s] knew spaces and faces now almost forgotten

there is one [here] less lost to you than the others, though, and it [is/1/v] 
right [here] in this plaza, about [now], that [@visitor/s] [are/v] to meet him

somewhere right around [here]"""

SEE_PLAZA = Sense('see', '@visitor', direct='@plaza_center', modality='sight')

initial_actions = [SHINE, SEE_PLAZA]


class Distance_Filter:
    'Increases narrative distance by changing to less immediate styles.'

    def __init__(self, how_far):
        self.suffixes = [', apparently ', ', evidently', ', or so it seemed', 
                         ', if memory serves', ', perhaps']
        self.prefixes = ['it seemed that','it appeared that', 
                         'it looked like','it was as if','no doubt,']
        # For each step of distance, we roll one die; that is, 0 if we are at
        # distance 0, 8 if we are at distance 8, etc.
        # If any of these rolls are successful, a suffix (half the time) or a
        # prefix (half the time) will be added.
        # The base probability gives our chance for one die being successful.
        self.base_prob = 0.0
        self.update(how_far)

    def update(self, how_far):
        self.distance = how_far
        no_success = 1.0 - self.base_prob
        self.expression_prob = .5 * (1.0 - (no_success ** self.distance))

    def sentence_filter(self, phrases):
        pick = random.random()
        if pick < self.expression_prob * .5:
            prefix = [random.choice(self.prefixes)]
            time_words = []
            if phrases[0] in ['before that,', 'meanwhile,', 'then,']:
                time_words = [phrases.pop(0)]
            phrases = time_words + prefix + phrases
        elif pick < self.expression_prob:
            suffix = random.choice(self.suffixes)
            phrases.append(suffix)
        return phrases

distance_filter = Distance_Filter(0)


class Cosmos(Actor):

    def __init__(self, tag, **keywords):
        self.visitor_places = []
        self.visitor_moved = []
        self.distance = 0
        self.distance_filter = distance_filter
        self.timer = 16
        Actor.__init__(self, tag, **keywords)

    def act(self, command_map, concept):
        actions = []
        if (self.distance == 0 and concept.ticks > 80 and
            str(concept.item['@visitor'].place(concept)) == '@plaza_center'):
            smile = Behave('smile', '@visitor')
            smile.final = True
            smile.before = """[@visitor/s] [turn/v] and [see/v] [@visitor's] 
                           friend"""
            actions.append(smile)
        return actions

    def interval(self):
        if self.timer > 0:
            self.timer -= 1
        time.sleep(self.timer / 5.0)

    def update_distance(self, spin):
        spin['time'] = ('during', 'after')[self.distance > 2]
        self.distance_filter.base_prob = (0.0, (1.0/6.0))[self.distance > 2]
        spin['narratee'] = ('@visitor', None)[self.distance > 4]
        spin['time_words'] = (False, True)[self.distance > 5]
        spin['commanded'] = ('@visitor', None)[self.distance > 9]
        self.distance_filter.update(self.distance)
        spin['sentence_filter'] = [distance_filter.sentence_filter]
        if self.distance < 6:
            spin['order'] = 'chronicle'
        elif self.distance < 8:
            spin['order'] = 'retrograde'
        else:
            spin['order'] = 'achrony'
        return spin

    def update_spin(self, concept, discourse):
        if discourse.spin['dynamic']:
            if len(self.visitor_places) > 0:
                self.visitor_moved.append( not self.visitor_places[-1] == \
                 concept.item['@visitor'].place(concept) )
            new_place = concept.item['@visitor'].place(concept)
            self.visitor_places.append(new_place)
            if sum(self.visitor_moved[-1:]) > 0:
                self.distance += 1
            else:
                if self.distance > 0:
                    self.distance -= .25
            discourse.spin = self.update_distance(discourse.spin)
        else:
            self.distance = 1
        return discourse.spin

cosmos = Cosmos('@cosmos', called='creation', allowed=can.have_any_item)


class Wanderer(Actor):
    '@visitor is the only instance. act() is used when commanded is None.'

    def act(self, command_map, concept):
        if random.random() < self.walk_probability:
            way = random.choice(self.place(concept).exits.keys())
            return [self.do_command(['leave', way], command_map, concept)]
        return []


class Collector(Actor):
    'Not used! @collector uses a deterministic script instead.'

    def act(self, command_map, concept):
        for (tag, link) in list(concept.item[str(self)].r(concept).child()):
            if link == 'in' and 'trash' in concept.item[tag].qualities:
                return [self.do_command(['take', tag], command_map, concept)]
        if random.random() < self.walk_probability:
            way = random.choice(self.place(concept).exits.keys())
            return [self.do_command(['leave', way], command_map, concept)]
        return []


class Kicker(Actor):
    'Not used! @punk uses a deterministic script instead.'

    def act(self, command_map, concept):
        if random.random() < self.walk_probability:
            way = random.choice(self.place(concept).exits.keys())
            return [self.do_command(['leave', way], command_map, concept)]
        elif random.random() < self.kick_probability:
            for (tag, link) in concept.item[str(self)].r(concept).child():
                if link == 'part_of':
                    return [self.do_command(['kick', tag], command_map,
                                            concept)]
        return []


items = fiction.plaza.items + [

    Wanderer('@visitor in @plaza_center',
        article='the',
        called='visitor',
        referring='|',
        allowed=can.possess_any_thing,
        qualities=['person', 'woman'],
        gender='female',
        sight='[*/s] [see/v] someone who is out of place',
        walk_probability=0.7,
        start=25),

    Thing('@tortilla of @visitor',
        article='a',
        called='(tasty) (corn) tortilla',
        referring='tasty typical circular thin white corn | circle disc disk',
        sight='a thin white circle, a corn tortilla',
        taste='bland but wholesome nutriment',
        consumable=True,
        prominence=0.2),

    Actor('@flaneur in @plaza_center',
        article='a',
        called='flaneur',
        referring='distracted foppish | flaneur',
        allowed=can.possess_any_thing,
        sight='a foppish man who [seem/1/v] dedicated to strolling about',
        qualities=['person', 'man'],
        gender='male',
        script=['leave north','wait','wait','wander','wait','leave east','wait',
                'wait','wander','wait','leave south','wait','wander','wait',
                'wander','wait','wait','leave south','wait','wait',
                'leave west','wait','wait','wander','wait','wait',
                'leave west','wait','wait','wander','wait','wait',
                'leave north','wait','wait','wander','wait','wait',
                'leave north','wait', 'wait','leave east','wait','wait',
                'leave southwest','wait','wait'],
        start=5),

    Actor('@punk in @plaza_w',
        article='some',
        called='punk',
        referring='angry punky | punk',
        allowed=can.possess_any_thing,
        sight='a girl who clearly [participate/ing/v] in the punk subculture',
        qualities=['person', 'woman'],
        gender='female',
        angry=True,
        script=['kick @tree', 'wait', 'wait', 'leave southeast', 
                'kick @obelisk', 'wait', 'wait', 'leave north', 'leave west'],
        script_loops=True,
        start=10),

    Actor('@collector in @plaza_sw',
        article='a',
        called='trash collector',
        referring='some nondescript trash | collector',
        allowed=can.possess_any_thing,
        sight='a nondescript man who seems to be a bona fide trash collector',
        qualities=['person', 'man'],
        gender='male',
        script=['take @candy_wrapper',
                'leave north',
                'take @smashed_cup',
                'leave north',
                'leave east',
                'leave south',
                'leave south',
                'leave east',
                'take @scrap',
                'leave north',
                'take @shredded_shirt',
                'take @newspaper_sheet'],
        start=45),

    Actor('@boy in @plaza_ne',
        article='a',
        called='boy',
        referring='| child',
        allowed=can.possess_any_thing,
        sight='an unremarkable boy',
        qualities=['person', 'man'],
        gender='male',
        script=['throw @ball', 'take @ball', 'wait'],
        script_loops=True,
        start=20),

    Thing('@ball of @boy',
        article='a',
        called='ball',
        referring='| ball baseball')]


########NEW FILE########
__FILENAME__ = plaza
"""Plaza

Items (in particular, Things and Rooms) representing the setting of Lost One."""

__author__ = 'Nick Montfort'
__copyright__ = 'Copyright 2011 Nick Montfort'
__license__ = 'ISC'
__version__ = '0.5.0.0'
__status__ = 'Development'

from item_model import Room, Thing

items = [

    Room('@plaza_center',
        article='the',
        called='center of the plaza',
        referring='center broad plaza of | plaza americas center middle',
        sight="""

        [*'s] senses [hum/ing/2/v] as [*/s] [view/v] [@plaza_center/o]

        the morning [conclude/1/ed/v]

        it [is/1/v] midday [now]
        """,
        exits={
        'north':'@plaza_n',
        'northeast':'@plaza_ne',
        'east':'@plaza_e',
        'southeast':'@plaza_se',
        'south':'@plaza_s',
        'southwest':'@plaza_sw',
        'west':'@plaza_w',
        'northwest':'@plaza_nw'},
        view={
        '@plaza_n': (.5, 'to the north'),
        '@plaza_ne': (.5, 'to the northeast'),
        '@plaza_e': (.5, 'to the east'),
        '@plaza_se': (.5, 'to the southeast'),
        '@plaza_s': (.5, 'to the south'),
        '@plaza_sw': (.5, 'to the southwest'),
        '@plaza_w': (.5, 'to the west'),
        '@plaza_nw': (.5, 'to the northwest')}),

    Room('@plaza_n',
        article='the',
        called='northern area',
        referring='broad plaza of northern | plaza americas part expanse space',
        sight="""
        
        the space north of the plaza's center, which [is/1/v] particularly 
        barren of vegetation and ornament""",
        exits={
        'east':'@plaza_ne',
        'southeast':'@plaza_e',
        'south':'@plaza_center',
        'west':'@plaza_nw',
        'southwest':'@plaza_w',},
        view={
        '@plaza_ne': (.5, 'to the east'),
        '@plaza_e': (.5, 'to the southeast'),
        '@plaza_center': (.5, 'to the south'),
        '@plaza_nw': (.5, 'to the west'),
        '@plaza_w': (.5, 'to the southwest'),
        '@plaza_se': (.25, 'off toward the southeast'),
        '@plaza_s': (.25, 'across the plaza'),
        '@plaza_sw': (.25, 'off toward the southwest')}),

    Thing('@rock in @plaza_n',
        article='a',
        called=' rock',
        referring='fist-sized fist sized | rock stone',
        sight='a fist-sized rock',
        prominence=0.3),

    Thing('@statue part_of @plaza_n',
        article='a',
        called='statue',
        referring='marble | likeness Einstein',
        sight="""
        
        [*/s] [see/v] a marble likeness of Einstein
        
        there [is/1/v] almost no hint [here] of the playful, disheveled 
        scientist so often seen in the photographs that were popular in the 
        early twenty-first century""",
        qualities=['stone'],
        prominence=0.8),

        Room('@plaza_ne',
        article='the',
        called='northeastern area',
        referring=('broad of northeastern | plaza americas part side ' +
                   'expanse space'),
        sight="the space northeast of the plaza's center",
        exits={
       'south':'@plaza_e',
       'southwest':'@plaza_center',
       'west':'@plaza_n'},
        view={
       '@plaza_e': (.5, 'to the south'),
       '@plaza_center': (.5, 'to the southwest'),
       '@plaza_n': (.5, 'to the west'),
       '@plaza_nw': (.25, 'to the far west'),
       '@plaza_w': (.25, 'off toward the west'),
       '@plaza_sw': (.25, 'across the plaza'),
       '@plaza_s': (.25, 'off toward the south'),
       '@plaza_se': (.25, 'to the far south')}),

        Room('@plaza_e',
        article='the',
        called='eastern area',
        referring='broad of eastern | plaza americas part side expanse space',
        sight="the space east of the plaza's center",
        exits={
       'north':'@plaza_ne',
       'south':'@plaza_se',
       'southwest':'@plaza_s',
       'west':'@plaza_center',
       'northwest':'@plaza_n'},
        view={
       '@plaza_ne': (.5, 'to the north'),
       '@plaza_center': (.5, 'to the west'),
       '@plaza_se': (.5, 'to the south'),
       '@plaza_n': (.5, 'to the northwest'),
       '@plaza_s': (.5, 'to the southwest'),
       '@plaza_nw': (.25, 'off toward the northwest'),
       '@plaza_w': (.25, 'across the plaza'),
       '@plaza_sw': (.25, 'off toward the southwest')}),

        Thing('@shredded_shirt in @plaza_e',
        article='a',
        called='shredded shirt',
        referring=('shredded torn flesh-colored flesh colored useless of | ' +
                   'cloth shirt mess'),
        sight='a useless mess of flesh-colored cloth',
        qualities=['clothing', 'trash'],
        prominence=0.3),

        Thing('@newspaper_sheet in @plaza_e',
        article='a',
        called=' newspaper (sheet)',
        referring='news newspaper | sheet page paper newspaper',
        sight="""
        
        there [are/2/v] summary texts LEADER WORKING THROUGH NIGHT FOR COUNTRY,
        MONUMENT NEARS COMPLETION, and PURITY ACCOMPLISHED
        """,
        qualities=['trash'],
        prominence=0.3),

    Thing('@fountain part_of @plaza_e',
        article='a',
        called='fountain',
        referring='rectangular plain | fountain basin jet',
        sight='a single jet [fan/1/v] out, feeding a basin',
        prominence=0.8),

    Room('@plaza_se',
        article='the',
        called='southeastern area',
        referring=('broad plaza of southeastern | plaza americas part ' +
                   'expanse space'),
        sight="the space southeast of the plaza's center",
        exits={
       'north':'@plaza_e',
       'west':'@plaza_s',
       'northwest':'@plaza_center'},
        view={
        '@plaza_e': (.5, 'to the north'),
        '@plaza_s': (.5, 'to the west'),
        '@plaza_center': (.5, 'to the northwest'),
        '@plaza_sw': (.25, 'to the far west'),
        '@plaza_w': (.25, 'off to the west'),
        '@plaza_ne': (.25, 'to the far north'),
        '@plaza_n': (.25, 'off to the north'),
        '@plaza_nw': (.25, 'across the plaza')}),

    Thing('@scrap in @plaza_se',
        article='a',
        called='plastic scrap',
        referring='plastic black | scrap',
        sight='something that was perhaps once part of a black plastic bag',
        qualities=['trash'],
        prominence=0.3),

    Room('@plaza_s',
        article='the',
        called='southern area',
        referring=('broad plaza of southern | plaza americas part ' +
                   'expanse space'),
        sight="the space south of the plaza's center",
        exits={
        'north':'@plaza_center',
        'northeast':'@plaza_e',
        'northwest':'@plaza_w',
        'east':'@plaza_se',
        'west':'@plaza_sw'},
        view={
        '@plaza_se': (.5, 'to the east'),
        '@plaza_e': (.5, 'to the northeast'),
        '@plaza_center': (.5, 'to the north'),
        '@plaza_sw': (.5, 'to the west'),
        '@plaza_w': (.5, 'to the northwest'),
        '@plaza_ne': (.25, 'off toward the northeast'),
        '@plaza_n': (.25, 'across the plaza'),
        '@plaza_nw': (.25, 'off toward the northwest')}),

    Thing('@obelisk part_of @plaza_s',
        article='an',
        called='obelisk',
        referring='| obelisk',
        sight='the stone pointing the way it has for centuries',
        qualities=['stone'],
        prominence=1.0),

    Room('@plaza_sw',
        article='the',
        called='southwestern area',
        referring=('broad plaza of southwestern | plaza americas part ' +
                   'expanse space'),
        sight="the space southwest of the plaza's center",
        exits={
        'north':'@plaza_w',
        'northeast':'@plaza_center',
        'east':'@plaza_s'},
        view={
        '@plaza_w': (.5, 'to the north'),
        '@plaza_s': (.5, 'to the east'),
        '@plaza_center': (.5, 'to the northeast'),
        '@plaza_se': (.25, 'to the far east'),
        '@plaza_e': (.25, 'off to the east'),
        '@plaza_nw': (.25, 'to the far north'),
        '@plaza_n': (.25, 'off to the north'),
        '@plaza_ne': (.25, 'across the plaza')}),

    Thing('@candy_wrapper in @plaza_sw',
        article='a',
        called='candy wrapper',
        referring="candy commodity's | wrapper husk",
        sight="a commodity's husk",
        qualities=['trash'],
        prominence=0.3),

    Room('@plaza_w',
        article='the',
        called='western area',
        referring='broad plaza of western | plaza americas part expanse space',
        sight="the space west of the plaza's center",
        exits={
        'north':'@plaza_nw',
        'east':'@plaza_center',
        'south':'@plaza_sw',
        'northeast':'@plaza_n',
        'southeast':'@plaza_s'},
        view={
        '@plaza_nw': (.5, 'to the north'),
        '@plaza_center': (.5, 'to the east'),
        '@plaza_sw': (.5, 'to the south'),
        '@plaza_n': (.5, 'to the northeast'),
        '@plaza_s': (.5, 'to the southeast'),
        '@plaza_ne': (.25, 'off toward the northeast'),
        '@plaza_e': (.25, 'across the plaza'),
        '@plaza_se': (.25, 'off toward the southeast')}),

    Thing('@smashed_cup in @plaza_w',
        article='a',
        called='smashed cup',
        referring='smashed paper drinking | cup vessel',
        sight='what was once a paper drinking vessel',
        qualities=['trash'],
        prominence=0.3),

    Thing('@tree part_of @plaza_w',
        article='a',
        called='tree',
        referring='large immense sprawling |',
        sight='a tree sprawling by itself on the west side of the plaza',
        prominence=1.0),

    Room('@plaza_nw',
        article='the',
        called='northwestern area',
        referring=('broad plaza of northwestern | plaza americas part ' +
                   'expanse space'),
        sight="the space northwest of the plaza's center",
        exits={
        'east':'@plaza_n',
        'southeast':'@plaza_center',
        'south':'@plaza_w'},
        view={
        '@plaza_w': (.5, 'to the south'),
        '@plaza_n': (.5, 'to the east'),
        '@plaza_center': (.5, 'to the southeast'),
        '@plaza_ne': (.25, 'to the far east'),
        '@plaza_e': (.25, 'off to the east'),
        '@plaza_sw': (.25, 'to the far south'),
        '@plaza_s': (.25, 'off to the south'),
        '@plaza_se': (.25, 'across the plaza')})]


########NEW FILE########
__FILENAME__ = robbery
'The Simulated Bank Robbery, a story (not an IF) for telling via Curveship.'

__author__ = 'Nick Montfort'
__copyright__ = 'Copyright 2011 Nick Montfort'
__license__ = 'ISC'
__version__ = '0.5.0.0'
__status__ = 'Development'

from item_model import Actor, Room, Thing
from action_model import Behave, Configure, Sense
import can

discourse = {
    'metadata': {
         'title': 'The Simulated Bank Robbery'},
    'spin':
    {'commanded': '@robber', 'focalizer': '@robber', 'narratee': None,
     'time_words': False, 'room_name_headings': False}}

READ_SLIPS = Behave('read', '@teller', direct='@slips')
SNOOZE = Behave('snooze', '@guard',
    template='[agent/s] [snooze/ing/v]')
COUNT_SLIPS = Behave('count', '@teller', direct='@slips')
DON_MASK = Configure('wear', '@robber', direct='@mask', new=('on', '@robber'),
    template='[agent/s] [put/v] on [direct/o]')
TYPE = Behave('type', '@teller')
PLAY = Behave('play', '@teller',
    template="[agent/s] [play/v] Solitaire a bit on [agent's] computer")
ROBBER_TO_LOBBY = Behave('leave', '@robber',
    template='[agent/s] [leave/v] the street',
    direct='@robber', direction='in')
WAVE = Behave('wave', '@teller', target='@robber',
    template='[agent/s] [wave/v] to [direct/o]')
BRANDISH = Behave('brandish', '@robber', target='@teller', indirect='@fake_gun',
    template='[agent/s] [brandish/v] [indirect/o] at [direct/o]')
LAUGH = Behave('laugh', '@teller')
WAKE = Behave('wake', '@guard')
SEE_ROBBER = Sense('see', '@guard', direct='@robber', modality='sight')
GUARD_TO_LOBBY = Behave('leave', '@guard',
    template='[agent/s] [leave/v] the guard post',
    direct='@guard', direction='out')
BAG_FAKE = Configure('put', '@teller', direct='@fake_money', new=('in', '@bag'),
    template='[agent/s] [put/v] [direct/o] in [@bag/o]')
TURN = Behave('turn', '@robber', target='@guard',
    template = '[agent/s] [turn/v] to [direct/o]')
SHOOT_1 = Behave('shoot', '@guard', target='@robber',
    template='[agent/s] [shoot/v] [direct/o] in the chest')
SHOOT_2 = Behave('shoot', '@guard', target='@robber',
    template='[agent/s] [shoot/v] [direct/o] in the chest')
FALL = Behave('fall', '@robber')
DIE = Behave('die', '@robber')
CRY = Behave('cry', '@teller')

# Uncomment this line to have Curveship exit after narrating CRY.
# CRY.final = True

initial_actions = [READ_SLIPS, SNOOZE, TYPE, DON_MASK, COUNT_SLIPS, PLAY,
                   ROBBER_TO_LOBBY, WAVE, BRANDISH, LAUGH, WAKE, SEE_ROBBER,
                   GUARD_TO_LOBBY, BAG_FAKE, TURN, SHOOT_1, SHOOT_2,
                   FALL, DIE, CRY]

items = [
    Room('@vestibule',
        article='the',
        called='vestibule',
        exits={},
        view={'@lobby': (0.8, 'out in the lobby')}),

    Room('@lobby',
        article='the',
        called='lobby',
        exits={'out': '@street', 'in': '@guard_post'},
        view={'@vestibule': (0.6, 'inside the vestibule')}),

    Room('@guard_post',
        article='the',
        called='guard post',
        exits={'out': '@lobby'},
        view={'@lobby': (0.8, 'through the one-way mirror')}),

    Room('@street',
        article='the',
        called='street outside the bank',
        exits={'in': '@lobby'}),

    Actor('@teller in @vestibule',
        article='the',
        called='bank teller',
        gender='female',
        allowed=can.have_any_item),

    Actor('@robber in @street',
        article='the',
        called='twitchy man',
        gender='male',
        allowed=can.have_any_item),

    Actor('@guard in @guard_post',
        article='the',
        called='burly guard',
        gender='male',
        allowed=can.have_any_item),

    Thing('@slips in @vestibule',
        article='some',
        called='deposit slips'),

    Thing('@fake_money in @vestibule',
        article='some',
        prominence=0.3,
        called='fake money'),

    Thing('@bag in @vestibule',
        article='a',
        called='black bag',
        allowed=can.have_any_item),

    Thing('@mask of @robber',
        article='a',
        called='Dora the Explorer mask'),

    Thing('@fake_gun of @robber',
        article='a',
        called='gun-shaped object'),

    Thing('@pistol of @guard',
        article='a',
        called='pistol')
]


########NEW FILE########
__FILENAME__ = input_model
'Represent different user inputs (commands, directives, unrecognized).'

__author__ = 'Nick Montfort'
__copyright__ = 'Copyright 2011 Nick Montfort'
__license__ = 'ISC'
__version__ = '0.5.0.0'
__status__ = 'Development'

class RichInput(object):
    'Encapsulates a user input string and information derived from it.'

    def __init__(self, input_string, tokens):
        self.unrecognized = True
        self.command = False
        self.directive = False
        self._category = 'unrecognized'
        self.string = input_string
        self.tokens = tokens
        self.normal = []
        # "tokens" will be reduced to [] in building the normal form, "normal"
        self.possible = []
        self.caused = None

    def __str__(self):
        return self.string

    def get_category(self):
        'Getter for the input category (e.g., "command").'
        return self._category

    def set_category(self, value):
        'Setter for the input category (e.g., "command").'
        if value not in ['unrecognized', 'command', 'directive']:
            raise StandardError('"' + value + '" was given as an input ' +
                                'category but is not a valid category.')
        self._category = value
        self.unrecognized = (value == 'unrecognized')
        self.command = (value == 'command')
        self.directive = (value == 'directive')

    category = property(get_category, set_category)


class InputList(object):
    """Encapsulates all user inputs that have been typed, in order.

    Distinguishes between a session (everything since the program has started
    running) and a traversal (when the current game started, which might be
    because the player typed 'restart.')"""

    def __init__(self):
        self._all = []
        self._traversal_start = 0

    def _count(self, category):
        """Counts only those inputs in the specified category.

        The first count covers the whole session (everything in the list). The
        second only considers the current traversal."""
        session = len([i for i in self._all if getattr(i, category)])
        traversal = len([i for i in self._all[self._traversal_start:]
                         if getattr(i, category)])
        return (session, traversal)

    def latest_command(self):
        'Returns the most recently entered command.'
        i = len(self._all) - 1
        while i >= 0:
            if self._all[i].command:
                return self._all[i]
            i -= 1

    def update(self, user_input):
        'Adds an input.'
        self._all.append(user_input)

    def reset(self):
        'Sets the list so that the next input will begin a new traversal.'
        self._traversal_start = len(self._all)

    def total(self):
        'Counts inputs in the whole session and in the current traversal.'
        session = len(self._all)
        traversal = session - self._traversal_start
        return (session, traversal)

    def show(self, number):
        'Produces a nicely-formatted list of up to number inputs.'
        full_list = ''
        index = max(len(self._all)-number, 0)
        begin = index
        for i in self._all[begin:]:
            index += 1
            full_list += str(index) + '. "' + str(i) + '" => ' + i.category
            if not i.unrecognized:
                full_list += ': ' + ' '.join(i.normal)
            full_list += '\n'
            if index == self._traversal_start:
                full_list += '\n---- Start of Current Traversal ----\n'
        return (full_list[:-1])

    def undo(self):
        """Changes a command to a directive. Used when the command is undone.

        Since the input no longer maps to an Action in this World, it makes
        to reclassify it as a directive."""
        for i in range(len(self._all)-1, -1, -1):
            if self._all[i].command:
                self._all[i].category = 'directive'
                self._all[i].normal = ['(HYPOTHETICALLY)'] + self._all[i].normal
                break

    def count_commands(self):
        'Counts commands in the session and current traversal.'
        return self._count('command')

    def count_directives(self):
        'Counts directives in the session and current traversal.'
        return self._count('directive')

    def count_unrecognized(self):
        'Counts unrecognized inputs in the session and current traversal.'
        return self._count('unrecognized')


########NEW FILE########
__FILENAME__ = irregular_verb
"""English-language verb forms for all but the most simply conjugated verbs.

Not only irregular verbs (strictly speaking) but also any regular verbs that
are not correctly conjugated by the simple algorithm in the Realizer. The
Realizer does not do any consonant doubling, so verbs whose consontants are
doubled have to be included here.
"""

__author__ = 'Nick Montfort'
__copyright__ = 'Copyright 2011 Nick Montfort'
__license__ = 'ISC'
__version__ = '0.5.0.0'
__status__ = 'Development'

FORMS = {
    'abet': ('abetted', 'abetted', 'abetting'),
    'abhor': ('abhorred', 'abhorred', 'abhorring'),
    'abide': ('abode', 'abode', 'abiding'),
    'abut': ('abutted', 'abutted', 'abutting'),
    'aby': ('abyed', 'abyed', 'abying'),
    'acquire': ('acquired', 'acquired', 'acquiring'),
    'acquit': ('acquitted', 'acquitted', 'acquitting'),
    'ad-lib': ('ad-libbed', 'ad-libbed', 'ad-libbing'),
    'admit': ('admitted', 'admitted', 'admitting'),
    'agree': ('agreed', 'agreed', 'agreeing'),
    'air-drop': ('air-dropped', 'air-dropped', 'air-dropping'),
    'air-ship': ('air-shipped', 'air-shipped', 'air-shipping'),
    'allot': ('allotted', 'allotted', 'allotting'),
    'alter': ('altered', 'altered', 'altering'),
    'anagram': ('anagrammed', 'anagrammed', 'anagramming'),
    'annul': ('annulled', 'annulled', 'annulling'),
    'ante': ('anted', 'anted', 'anteing'),
    'appal': ('appalled', 'appalled', 'appalling'),
    'arise': ('arose', 'arisen', 'arising'),
    'aver': ('averred', 'averred', 'averring'),
    'awake': ('awoke', 'awoken', 'awaking'),
    'baby-sit': ('baby-sat', 'baby-sat', 'baby-sitting'),
    'backbite': ('backbit', 'backbitten', 'backbiting'),
    'backlog': ('backlogged', 'backlogged', 'backlogging'),
    'backpedal': ('backpedalled', 'backpedalled', 'backpedalling'),
    'backslap': ('backslapped', 'backslapped', 'backslapping'),
    'backslide': ('backslid', 'backslidden', 'backsliding'),
    'backstop': ('backstopped', 'backstopped', 'backstopping'),
    'bag': ('bagged', 'bagged', 'bagging'),
    'ban': ('banned', 'banned', 'banning'),
    'bar': ('barred', 'barred', 'barring'),
    'bat': ('batted', 'batted', 'batting'),
    'bayonet': ('bayonetted', 'bayonetted', 'bayonetting'),
    'be': ('was', 'been', 'being'),
    'bear': ('bore', 'born', 'bearing'),
    'beat': ('beat', 'beat', 'beating'),
    'beat2': ('beat', 'beaten', 'beating'),
    'become': ('became', 'became', 'becoming'),
    'become2': ('became', 'become', 'becoming'),
    'bed-hop': ('bed-hopped', 'bed-hopped', 'bed-hopping'),
    'bed': ('bedded', 'bedded', 'bedding'),
    'befall': ('befell', 'befallen', 'befalling'),
    'befit': ('befitted', 'befitted', 'befitting'),
    'befog': ('befogged', 'befogged', 'befogging'),
    'beg': ('begged', 'begged', 'begging'),
    'beget': ('begot', 'begotten', 'begetting'),
    'begin': ('began', 'begun', 'beginning'),
    'begird': ('begirt', 'begirt', 'begirding'),
    'behold': ('beheld', 'beholden', 'beholding'),
    'belie': ('belied', 'belied', 'belying'),
    'belly-flop': ('belly-flopped', 'belly-flopped', 'belly-flopping'),
    'bend': ('bent', 'bent', 'bending'),
    'benefit': ('benefitted', 'benefitted', 'benefitting'),
    'bereave': ('bereft', 'bereft', 'bereaving'),
    'beseech': ('besought', 'besought', 'beseeching'),
    'beset': ('beset', 'beset', 'besetting'),
    'besot': ('besotted', 'besotted', 'besotting'),
    'bespeak': ('bespoke', 'bespoken', 'bespeaking'),
    'bespot': ('bespotted', 'bespotted', 'bespotting'),
    'bestir': ('bestirred', 'bestirred', 'bestirring'),
    'bestrew': ('bestrewed', 'bestrewn', 'bestrewing'),
    'bestride': ('bestrode', 'bestridden', 'bestriding'),
    'bet': ('bet', 'bet', 'betting'),
    'bethink': ('bethought', 'bethought', 'bethinking'),
    'bib': ('bibbed', 'bibbed', 'bibbing'),
    'bid': ('bade', 'bidden', 'bidding'),
    'bid2': ('bid', 'bid', 'bidding'),
    'bin': ('binned', 'binned', 'binning'),
    'bind': ('bound', 'bound', 'binding'),
    'birdie': ('birdied', 'birdied', 'birdieing'),
    'bite': ('bit ', 'bitten', 'biting'),
    'bite2': ('bit', 'bitten', 'biting'),
    'bivouac': ('bivouacked', 'bivouacked', 'bivouacking'),
    'blab': ('blabbed', 'blabbed', 'blabbing'),
    'blackleg': ('blacklegged', 'blacklegged', 'blacklegging'),
    'blacktop': ('blacktopped', 'blacktopped', 'blacktopping'),
    'blat': ('blatted', 'blatted', 'blatting'),
    'bleed': ('bled', 'bled', 'bleeding'),
    'blob': ('blobbed', 'blobbed', 'blobbing'),
    'blog': ('blogged', 'blogged', 'blogging'),
    'blot': ('blotted', 'blotted', 'blotting'),
    'blow': ('blew', 'blown', 'blowing'),
    'blub': ('blubbed', 'blubbed', 'blubbing'),
    'blur': ('blurred', 'blurred', 'blurring'),
    'bob': ('bobbed', 'bobbed', 'bobbing'),
    'bobsled': ('bobsledded', 'bobsledded', 'bobsledding'),
    'bog': ('bogged', 'bogged', 'bogging'),
    'boogie': ('boogied', 'boogied', 'boogieing'),
    'bootleg': ('bootlegged', 'bootlegged', 'bootlegging'),
    'bop': ('bopped', 'bopped', 'bopping'),
    'bottle-feed': ('bottle-fed', 'bottle-fed', 'bottle-feeding'),
    'brad': ('bradded', 'bradded', 'bradding'),
    'brag': ('bragged', 'bragged', 'bragging'),
    'break': ('broke', 'broken', 'breaking'),
    'breastfeed': ('breastfed', 'breastfed', 'breastfeeding'),
    'breed': ('bred', 'bred', 'breeding'),
    'brim': ('brimmed', 'brimmed', 'brimming'),
    'bring': ('brought', 'brought', 'bringing'),
    'broadcast': ('broadcast', 'broadcast', 'broadcasting'),
    'browbeat': ('browbeat', 'browbeaten', 'browbeating'),
    'bud': ('budded', 'budded', 'budding'),
    'buffet': ('buffetted', 'buffetted', 'buffetting'),
    'bug': ('bugged', 'bugged', 'bugging'),
    'build': ('built', 'built', 'building'),
    'bullshit': ('bullshitted', 'bullshitted', 'bullshitting'),
    'bum': ('bummed', 'bummed', 'bumming'),
    'bur': ('burred', 'burred', 'burring'),
    'burn': ('burned', 'burned', 'burning'),
    'burst': ('burst', 'burst', 'bursting'),
    'bus': ('bussed', 'bussed', 'bussing'),
    'bust': ('bust', 'bust', 'busting'),
    'buy': ('bought', 'bought', 'buying'),
    'by-bid': ('by-bade', 'by-bidden', 'by-bidding'),
    'cab': ('cabbed', 'cabbed', 'cabbing'),
    'cabal': ('caballed', 'caballed', 'caballing'),
    'caddie': ('caddied', 'caddied', 'caddying'),
    'can': ('canned', 'canned', 'canning'),
    'canoe': ('canoed', 'canoed', 'canoeing'),
    'cap': ('capped', 'capped', 'capping'),
    'caravan': ('caravanned', 'caravanned', 'caravanning'),
    'carburet': ('carburetted', 'carburetted', 'carburetting'),
    'cast': ('cast', 'cast', 'casting'),
    'cat': ('catted', 'catted', 'catting'),
    'catch': ('caught', 'caught', 'catching'),
    'catnap': ('catnapped', 'catnapped', 'catnapping'),
    'chap': ('chapped', 'chapped', 'chapping'),
    'char': ('charred', 'charred', 'charring'),
    'chasse': ('chassed', 'chassed', 'chasseing'),
    'chat': ('chatted', 'chatted', 'chatting'),
    'chicken-fight': ('chicken-fought', 'chicken-fought', 'chicken-fighting'),
    'chin': ('chinned', 'chinned', 'chinning'),
    'chip': ('chipped', 'chipped', 'chipping'),
    'chirrup': ('chirrupped', 'chirrupped', 'chirrupping'),
    'chivy': ('chivvied', 'chivvied', 'chivvying'),
    'choose': ('chose', 'chosen', 'choosing'),
    'chop': ('chopped', 'chopped', 'chopping'),
    'chug': ('chugged', 'chugged', 'chugging'),
    'clam': ('clammed', 'clammed', 'clamming'),
    'clap': ('clapped', 'clapped', 'clapping'),
    'clear-cut': ('clear-cut', 'clear-cut', 'clear-cutting'),
    'cleave': ('clove', 'cloven', 'cleaving'),
    'cling': ('clung', 'clung', 'clinging'),
    'cling2': ('clung', 'clung', 'clining'),
    'clip': ('clipped', 'clipped', 'clipping'),
    'clog': ('clogged', 'clogged', 'clogging'),
    'clop': ('clopped', 'clopped', 'clopping'),
    'clot': ('clotted', 'clotted', 'clotting'),
    'clothe': ('clad', 'clad', 'clothing'),
    'club': ('clubbed', 'clubbed', 'clubbing'),
    'co-occur': ('co-occurred', 'co-occurred', 'co-occurring'),
    'co-star': ('co-starred', 'co-starred', 'co-starring'),
    'cod': ('codded', 'codded', 'codding'),
    'coif': ('coiffed', 'coiffed', 'coiffing'),
    'combat': ('combatted', 'combatted', 'combatting'),
    'come': ('came', 'came', 'coming'),
    'come2': ('came', 'come', 'coming'),
    'commit': ('committed', 'committed', 'committing'),
    'comparison-shop': ('comparison-shopped', 'comparison-shopped',
                       'comparison-shopping'),
    'compel': ('compelled', 'compelled', 'compelling'),
    'con': ('conned', 'conned', 'conning'),
    'conclude': ('conclude', 'concluded', 'concluding'),
    'conclude2': ('concluded', 'concluded', 'concluding'),
    'concur': ('concurred', 'concurred', 'concurring'),
    'confab': ('confabbed', 'confabbed', 'confabbing'),
    'confer': ('conferred', 'conferred', 'conferring'),
    'congee': ('congeed', 'congeed', 'congeeing'),
    'control': ('controlled', 'controlled', 'controlling'),
    'cop': ('copped', 'copped', 'copping'),
    'coquet': ('coquetted', 'coquetted', 'coquetting'),
    'corbel': ('corbelled', 'corbelled', 'corbelling'),
    'corral': ('corralled', 'corralled', 'corralling'),
    'cost': ('cost', 'cost', 'costing'),
    'counterplot': ('counterplotted', 'counterplotted', 'counterplotting'),
    'countersink': ('countersank', 'countersunk', 'countersinking'),
    'crab': ('crabbed', 'crabbed', 'crabbing'),
    'cram': ('crammed', 'crammed', 'cramming'),
    'crap': ('crapped', 'crapped', 'crapping'),
    'creep': ('crept', 'crept', 'creeping'),
    'creep2': ('crept', 'crept', 'creping'),
    'crenel': ('crenelled', 'crenelled', 'crenelling'),
    'crib': ('cribbed', 'cribbed', 'cribbing'),
    'crop': ('cropped', 'cropped', 'cropping'),
    'cross-refer': ('cross-referred', 'cross-referred', 'cross-referring'),
    'crossbreed': ('crossbred', 'crossbred', 'crossbreeding'),
    'crosscut': ('crosscut', 'crosscut', 'crosscutting'),
    'cub': ('cubbed', 'cubbed', 'cubbing'),
    'cup': ('cupped', 'cupped', 'cupping'),
    'custom-make': ('custom-made', 'custom-made', 'custom-making'),
    'cut': ('cut', 'cut', 'cutting'),
    'dab': ('dabbed', 'dabbed', 'dabbing'),
    'dam': ('dammed', 'dammed', 'damming'),
    'deal': ('dealt', 'dealt', 'dealing'),
    'debar': ('debarred', 'debarred', 'debarring'),
    'debug': ('debugged', 'debugged', 'debugging'),
    'decontrol': ('decontrolled', 'decontrolled', 'decontrolling'),
    'decree': ('decreed', 'decreed', 'decreeing'),
    'deep-dye': ('deep-dyed', 'deep-dyed', 'deep-dyeing'),
    'defer': ('deferred', 'deferred', 'deferring'),
    'defog': ('defogged', 'defogged', 'defogging'),
    'degas': ('degassed', 'degassed', 'degassing'),
    'demob': ('demobbed', 'demobbed', 'demobbing'),
    'demur': ('demurred', 'demurred', 'demurring'),
    'deter': ('deterred', 'deterred', 'deterring'),
    'diagram': ('diagrammed', 'diagrammed', 'diagramming'),
    'dial': ('dialled', 'dialled', 'dialling'),
    'die': ('died', 'died', 'dying'),
    'dig': ('dug', 'dug', 'digging'),
    'dim': ('dimmed', 'dimmed', 'dimming'),
    'din': ('dinned', 'dinned', 'dinning'),
    'dip': ('dipped', 'dipped', 'dipping'),
    'dis': ('dissed', 'dissed', 'dissing'),
    'disagree': ('disagreed', 'disagreed', 'disagreeing'),
    'disbar': ('disbarred', 'disbarred', 'disbarring'),
    'disbud': ('disbudded', 'disbudded', 'disbudding'),
    'discomfit': ('discomfitted', 'discomfitted', 'discomfitting'),
    'disinter': ('disinterred', 'disinterred', 'disinterring'),
    'dispel': ('dispelled', 'dispelled', 'dispelling'),
    'distil': ('distilled', 'distilled', 'distilling'),
    'dive': ('dived', 'dived', 'diving'),
    'do': ('did', 'done', 'doing'),
    'dog': ('dogged', 'dogged', 'dogging'),
    'don': ('donned', 'donned', 'donning'),
    'dot': ('dotted', 'dotted', 'dotting'),
    'drag': ('dragged', 'dragged', 'dragging'),
    'draw': ('drew', 'drawn', 'drawing'),
    'dream': ('dreamed', 'dreamed', 'dreaming'),
    'dream2': ('dreamt', 'dreamt', 'dreaming'),
    'drink': ('drank', 'drunk', 'drinking'),
    'drip': ('dripped', 'dripped', 'dripping'),
    'drive': ('drove', 'driven', 'driving'),
    'drop': ('dropped', 'dropped', 'dropping'),
    'drub': ('drubbed', 'drubbed', 'drubbing'),
    'drug': ('drugged', 'drugged', 'drugging'),
    'drum': ('drummed', 'drummed', 'drumming'),
    'dry-rot': ('dry-rotted', 'dry-rotted', 'dry-rotting'),
    'dub': ('dubbed', 'dubbed', 'dubbing'),
    'duel': ('duelled', 'duelled', 'duelling'),
    'dun': ('dunned', 'dunned', 'dunning'),
    'dwell': ('dwelt', 'dwelt', 'dwelling'),
    'dye': ('dyed', 'dyed', 'dyeing'),
    'eat': ('ate', 'eaten', 'eating'),
    'eavesdrop': ('eavesdropped', 'eavesdropped', 'eavesdropping'),
    'egotrip': ('egotripped', 'egotripped', 'egotripping'),
    'embed': ('embedded', 'embedded', 'embedding'),
    'emcee': ('emceed', 'emceed', 'emceeing'),
    'emit': ('emitted', 'emitted', 'emitting'),
    'englut': ('englutted', 'englutted', 'englutting'),
    'enrol': ('enrolled', 'enrolled', 'enrolling'),
    'enthral': ('enthralled', 'enthralled', 'enthralling'),
    'entrap': ('entrapped', 'entrapped', 'entrapping'),
    'enwrap': ('enwrapped', 'enwrapped', 'enwrapping'),
    'equip': ('equipped', 'equipped', 'equipping'),
    'excel': ('excelled', 'excelled', 'excelling'),
    'expel': ('expelled', 'expelled', 'expelling'),
    'extol': ('extolled', 'extolled', 'extolling'),
    'eye': ('eyed', 'eyed', 'eyeing'),
    'facsimile': ('facsimiled', 'facsimiled', 'facsimileing'),
    'fag': ('fagged', 'fagged', 'fagging'),
    'fall': ('fell', 'fallen', 'falling'),
    'fan': ('fanned', 'fanned', 'fanning'),
    'fat': ('fatted', 'fatted', 'fatting'),
    'featherbed': ('featherbedded', 'featherbedded', 'featherbedding'),
    'fee': ('feed', 'feed', 'feeing'),
    'feed': ('fed', 'fed', 'feeding'),
    'feel': ('felt', 'felt', 'feeling'),
    'fib': ('fibbed', 'fibbed', 'fibbing'),
    'fight': ('fought', 'fought', 'fighting'),
    'filigree': ('filigreed', 'filigreed', 'filigreeing'),
    'film-make': ('film-made', 'film-made', 'film-making'),
    'fin': ('finned', 'finned', 'finning'),
    'find': ('found', 'found', 'finding'),
    'fit': ('fit', 'fit', 'fitting'),
    'fit2': ('fitted', 'fitted', 'fitting'),
    'flag': ('flagged', 'flagged', 'flagging'),
    'flambe': ('flambeed', 'flambeed', 'flambeing'),
    'flap': ('flapped', 'flapped', 'flapping'),
    'flash-freeze': ('flash-froze', 'flash-frozen', 'flash-freezing'),
    'flat-hat': ('flat-hatted', 'flat-hatted', 'flat-hatting'),
    'flee': ('fled', 'fled', 'fleeing'),
    'flim-flam': ('flim-flammed', 'flim-flammed', 'flim-flamming'),
    'fling': ('flung', 'flung', 'flinging'),
    'flip-flop': ('flip-flopped', 'flip-flopped', 'flip-flopping'),
    'flip': ('flipped', 'flipped', 'flipping'),
    'flit': ('flitted', 'flitted', 'flitting'),
    'flog': ('flogged', 'flogged', 'flogging'),
    'floodlight': ('floodlit', 'floodlit', 'floodlighting'),
    'flop': ('flopped', 'flopped', 'flopping'),
    'flub': ('flubbed', 'flubbed', 'flubbing'),
    'fly': ('flew', 'flown', 'flying'),
    'fob': ('fobbed', 'fobbed', 'fobbing'),
    'focus': ('focussed', 'focussed', 'focussing'),
    'fog': ('fogged', 'fogged', 'fogging'),
    'footslog': ('footslogged', 'footslogged', 'footslogging'),
    'forbear': ('forbore', 'forborne', 'forbearing'),
    'forbid': ('forbade', 'forbidden', 'forbidding'),
    'force-feed': ('force-fed', 'force-fed', 'force-feeding'),
    'forecast': ('forecast', 'forecast', 'forecasting'),
    'forego': ('forewent', 'foregone', 'foregoing'),
    'foreknow': ('foreknew', 'foreknown', 'foreknowing'),
    'foresee': ('foresaw', 'foreseen', 'foreseeing'),
    'foreshow': ('foreshowed', 'foreshown', 'foreshowing'),
    'foreswear': ('foreswore', 'foreswore', 'foreswearing'),
    'foretell': ('foretold', 'foretold', 'foretelling'),
    'forget': ('forgot', 'forgotten', 'forgetting'),
    'forgive': ('forgave', 'forgiven', 'forgiving'),
    'forgo': ('forwent', 'forgone', 'forgoing'),
    'format': ('formatted', 'formatted', 'formatting'),
    'forsake': ('forsook', 'forsaken', 'forsaking'),
    'forswear': ('forswore', 'forsworn', 'forswearing'),
    'foxtrot': ('foxtrotted', 'foxtrotted', 'foxtrotting'),
    'frap': ('frapped', 'frapped', 'frapping'),
    'free': ('freed', 'freed', 'freeing'),
    'freeze': ('froze', 'frozen', 'freezing'),
    'fret': ('fretted', 'fretted', 'fretting'),
    'fricassee': ('fricasseed', 'fricasseed', 'fricasseeing'),
    'frog': ('frogged', 'frogged', 'frogging'),
    'frolic': ('frolicked', 'frolicked', 'frolicking'),
    'fuel': ('fuelled', 'fuelled', 'fuelling'),
    'fulfil': ('fulfilled', 'fulfilled', 'fulfilling'),
    'gad': ('gadded', 'gadded', 'gadding'),
    'gag': ('gagged', 'gagged', 'gagging'),
    'gainsay': ('gainsaid', 'gainsaid', 'gainsaying'),
    'gap': ('gapped', 'gapped', 'gapping'),
    'garnishee': ('garnisheed', 'garnisheed', 'garnisheeing'),
    'gas': ('gassed', 'gassed', 'gassing'),
    'gee': ('geed', 'geed', 'geeing'),
    'gel': ('gelled', 'gelled', 'gelling'),
    'geld': ('gelded', 'gelt', 'gelding'),
    'get': ('got', 'gotten', 'getting'),
    'ghostwrite': ('ghostwrote', 'ghostwritten', 'ghostwriting'),
    'gift-wrap': ('gift-wrapped', 'gift-wrapped', 'gift-wrapping'),
    'gin': ('ginned', 'gan', 'ginning'),
    'gip': ('gipped', 'gipped', 'gipping'),
    'give': ('gave', 'given', 'giving'),
    'globe-trot': ('globe-trotted', 'globe-trotted', 'globe-trotting'),
    'glom': ('glommed', 'glommed', 'glomming'),
    'glug': ('glugged', 'glugged', 'glugging'),
    'glut': ('glutted', 'glutted', 'glutting'),
    'go': ('went', 'gone', 'going'),
    'gossip': ('gossipped', 'gossipped', 'gossipping'),
    'grab': ('grabbed', 'grabbed', 'grabbing'),
    'grave': ('graved', 'graven', 'graving'),
    'grin': ('grinned', 'grinned', 'grinning'),
    'grind': ('ground', 'ground', 'grinding'),
    'grip': ('gripped', 'gripped', 'gripping'),
    'grit': ('gritted', 'gritted', 'gritting'),
    'grow': ('grew', 'grown', 'growing'),
    'grub': ('grubbed', 'grubbed', 'grubbing'),
    'guarantee': ('guaranteed', 'guaranteed', 'guaranteeing'),
    'gum': ('gummed', 'gummed', 'gumming'),
    'gun': ('gunned', 'gunned', 'gunning'),
    'gut': ('gutted', 'gutted', 'gutting'),
    'gyp': ('gypped', 'gypped', 'gypping'),
    'ham': ('hammed', 'hammed', 'hamming'),
    'hamstring': ('hamstrung', 'hamstrung', 'hamstringing'),
    'hand-build': ('hand-built', 'hand-built', 'hand-building'),
    'hand-dye': ('hand-dyed', 'hand-dyed', 'hand-dyeing'),
    'handicap': ('handicapped', 'handicapped', 'handicapping'),
    'handwrite': ('handwrote', 'handwritten', 'handwriting'),
    'hang': ('hung', 'hung', 'hanging'),
    'hap': ('happed', 'happed', 'happing'),
    'happy-slap': ('happy-slapped', 'happy-slapped', 'happy-slapping'),
    'hat': ('hatted', 'hatted', 'hatting'),
    'have': ('had', 'had', 'having'),
    'hear': ('heard', 'heard', 'hear'),
    'hear2': ('heard', 'heard', 'hearing'),
    'hedgehop': ('hedgehopped', 'hedgehopped', 'hedgehopping'),
    'hem': ('hemmed', 'hemmed', 'hemming'),
    'hero-worship': ('hero-worshipped', 'hero-worshipped', 'hero-worshipping'),
    'hew': ('hewed', 'hewn', 'hewing'),
    'hiccup': ('hiccupped', 'hiccupped', 'hiccupping'),
    'hide': ('hid', 'hidden', 'hiding'),
    'hie': ('hied', 'hied', 'hieing'),
    'hit': ('hit', 'hit', 'hit'),
    'hit2': ('hit', 'hit', 'hitting'),
    'hob': ('hobbed', 'hobbed', 'hobbing'),
    'hobnob': ('hobnobbed', 'hobnobbed', 'hobnobbing'),
    'hoe': ('hoed', 'hoed', 'hoeing'),
    'hog-tie': ('hog-tied', 'hog-tied', 'hog-tying'),
    'hog': ('hogged', 'hogged', 'hogging'),
    'hold': ('held', 'held', 'holding'),
    'honey': ('honied', 'honied', 'honeying'),
    'hop-skip': ('hop-skipped', 'hop-skipped', 'hop-skipping'),
    'hop': ('hopped', 'hopped', 'hopping'),
    'horseshoe': ('horseshoed', 'horseshoed', 'horseshoeing'),
    'horsewhip': ('horsewhipped', 'horsewhipped', 'horsewhipping'),
    'hot-dog': ('hot-dogged', 'hot-dogged', 'hot-dogging'),
    'housebreak': ('housebroke', 'housebroken', 'housebreaking'),
    'housekeep': ('housekept', 'housekept', 'housekeeping'),
    'hue': ('hued', 'hued', 'hueing'),
    'hug': ('hugged', 'hugged', 'hugging'),
    'hum': ('hum', 'hummed', 'humming'),
    'hum2': ('hummed', 'hummed', 'humming'),
    'humbug': ('humbugged', 'humbugged', 'humbugging'),
    'hurt': ('hurt', 'hurt', 'hurting'),
    'imbed': ('imbedded', 'imbedded', 'imbedding'),
    'impel': ('impelled', 'impelled', 'impelling'),
    'imperil': ('imperilled', 'imperilled', 'imperilling'),
    'impulse-buy': ('impulse-bought', 'impulse-bought', 'impulse-buying'),
    'incur': ('incurred', 'incurred', 'incurring'),
    'indwell': ('indwelt', 'indwelt', 'indwelling'),
    'infer': ('inferred', 'inferred', 'inferring'),
    'initial': ('initialled', 'initialled', 'initialling'),
    'inlay': ('inlaid', 'inlaid', 'inlaying'),
    'input': ('inputted', 'inputted', 'inputting'),
    'inset': ('inset', 'inset', 'insetting'),
    'inspan': ('inspanned', 'inspanned', 'inspanning'),
    'instal': ('installed', 'installed', 'installing'),
    'instil': ('instilled', 'instilled', 'instilling'),
    'inter': ('interred', 'interred', 'interring'),
    'interbreed': ('interbred', 'interbred', 'interbreeding'),
    'intermit': ('intermitted', 'intermitted', 'intermitting'),
    'interweave': ('interwove', 'interwoven', 'interweaving'),
    'inweave': ('inwove', 'inwoven', 'inweaving'),
    'jab': ('jabbed', 'jabbed', 'jabbing'),
    'jag': ('jagged', 'jagged', 'jagging'),
    'jam': ('jammed', 'jammed', 'jamming'),
    'japan': ('japanned', 'japanned', 'japanning'),
    'jar': ('jarred', 'jarred', 'jarring'),
    'jet': ('jetted', 'jetted', 'jetting'),
    'jib': ('jibbed', 'jibbed', 'jibbing'),
    'jig': ('jigged', 'jigged', 'jigging'),
    'jitterbug': ('jitterbugged', 'jitterbugged', 'jitterbugging'),
    'job': ('jobbed', 'jobbed', 'jobbing'),
    'jog': ('jogged', 'jogged', 'jogging'),
    'jot': ('jotted', 'jotted', 'jotting'),
    'joyride': ('joyrode', 'joyridden', 'joyriding'),
    'jug': ('jugged', 'jugged', 'jugging'),
    'jut': ('jutted', 'jutted', 'jutting'),
    'keep': ('kept', 'kept', 'keeping'),
    'kid': ('kidded', 'kidded', 'kidding'),
    'kidnap': ('kidnapped', 'kidnapped', 'kidnapping'),
    'kip': ('kipped', 'kipped', 'kipping'),
    'kit': ('kitted', 'kitted', 'kitting'),
    'knap': ('knapped', 'knapped', 'knapping'),
    'kneecap': ('kneecapped', 'kneecapped', 'kneecapping'),
    'kneel': ('knelt', 'knelt', 'kneeling'),
    'knit': ('knit', 'knit', 'knitting'),
    'knit2': ('knitted', 'knitted', 'knitting'),
    'knot': ('knotted', 'knotted', 'knotting'),
    'know': ('knew', 'known', 'knowing'),
    'lade': ('laded', 'laden', 'lading'),
    'lag': ('lagged', 'lagged', 'lagging'),
    'lam': ('lammed', 'lammed', 'lamming'),
    'lap': ('lapped', 'lapped', 'lapping'),
    'lay': ('laid', 'laid', 'lay'),
    'lay2': ('laid', 'laid', 'laying'),
    'lead': ('led', 'led', 'lead'),
    'lead2': ('led', 'led', 'leading'),
    'leap': ('leaped', 'leaped', 'leap'),
    'leap2': ('leapt', 'leapt', 'leaping'),
    'leapfrog': ('leapfrogged', 'leapfrogged', 'leapfrogging'),
    'learn': ('learned', 'learned', 'learn'),
    'learn2': ('learnt', 'learnt', 'learning'),
    'leave': ('left', 'left', 'leaving'),
    'lend': ('lent', 'lent', 'lending'),
    'let': ('let', 'let', 'let'),
    'let2': ('let', 'let', 'letting'),
    'lie': ('lay', 'lain', 'lying'),
    'lie2': ('lied', 'lain', 'lying'),
    'light': ('lit', 'lighted', 'lighting'),
    'light2': ('lit', 'lit', 'lighting'),
    'lip-read': ('lip-read', 'lip-read', 'lip-reading'),
    'lob': ('lobbed', 'lobbed', 'lobbing'),
    'log-in': ('logged-in', 'logged-in', 'logging-in'),
    'log': ('logged', 'logged', 'logging'),
    'lollop': ('lollopped', 'lollopped', 'lollopping'),
    'lop': ('lopped', 'lopped', 'lopping'),
    'lose': ('lost', 'lost', 'losing'),
    'lug': ('lugged', 'lugged', 'lugging'),
    'make': ('made', 'made', 'making'),
    'man': ('manned', 'manned', 'manning'),
    'manumit': ('manumitted', 'manumitted', 'manumitting'),
    'map': ('mapped', 'mapped', 'mapping'),
    'mar': ('marred', 'marred', 'marring'),
    'mat': ('matted', 'matted', 'matting'),
    'matt-up': ('matt-upped', 'matt-upped', 'matt-upping'),
    'mean': ('meant', 'meant', 'meaning'),
    'meet': ('met', 'met', 'meeting'),
    'melt': ('melted', 'molten', 'melting'),
    'mimic': ('mimicked', 'mimicked', 'mimicking'),
    'miscast': ('miscast', 'miscast', 'miscasting'),
    'misdeal': ('misdealt', 'misdealt', 'misdealing'),
    'misdo': ('misdid', 'misdone', 'misdoing'),
    'misgive': ('misgave', 'misgiven', 'misgiving'),
    'mislay': ('mislaid', 'mislaid', 'mislaying'),
    'mislead': ('misled', 'misled', 'misleading'),
    'misread': ('misread', 'misread', 'misreading'),
    'misspeak': ('misspoke', 'misspoken', 'misspeaking'),
    'misspell': ('misspelled', 'misspelled', 'misspelling'),
    'misspend': ('misspent', 'misspent', 'misspending'),
    'mistake': ('mistook', 'mistaken', 'mistake'),
    'mistake2': ('mistook', 'mistaken', 'mistaking'),
    'misunderstand': ('misunderstood', 'misunderstood', 'misunderstanding'),
    'mob': ('mobbed', 'mobbed', 'mobbing'),
    'model': ('modelled', 'modelled', 'modelling'),
    'mop': ('mopped', 'mopped', 'mopping'),
    'move': ('moved', 'moved', 'moving'),
    'mow': ('mowed', 'mowed', 'mowing'),
    'mow2': ('mowed', 'mown', 'mowing'),
    'mud': ('mudded', 'mudded', 'mudding'),
    'mug': ('mugged', 'mugged', 'mugging'),
    'nab': ('nabbed', 'nabbed', 'nabbing'),
    'nag': ('nagged', 'nagged', 'nagging'),
    'nap': ('napped', 'napped', 'napping'),
    'net': ('netted', 'netted', 'netting'),
    'nip': ('nipped', 'nipped', 'nipping'),
    'nod': ('nodded', 'nodded', 'nodding'),
    'nonplus': ('nonplussed', 'nonplussed', 'nonplussing'),
    'nut': ('nutted', 'nutted', 'nutting'),
    'occur': ('occurred', 'occurred', 'occurring'),
    'offset': ('offset', 'offset', 'offsetting'),
    'omit': ('omitted', 'omitted', 'omitting'),
    'one-step': ('one-stepped', 'one-stepped', 'one-stepping'),
    'open': ('opened', 'opened', 'opening'),
    'outbid': ('outbid', 'outbid', 'outbidding'),
    'outcrop': ('outcropped', 'outcropped', 'outcropping'),
    'outdo': ('outdid', 'outdone', 'outdoing'),
    'outfight': ('outfought', 'outfought', 'outfighting'),
    'outfit': ('outfitted', 'outfitted', 'outfitting'),
    'outgo': ('outwent', 'outgone', 'outgoing'),
    'outgrow': ('outgrew', 'outgrown', 'outgrowing'),
    'output': ('outputted', 'outputted', 'outputting'),
    'outride': ('outrode', 'outridden', 'outriding'),
    'outrun': ('outran', 'outran', 'outrunning'),
    'outsell': ('outsold', 'outsold', 'outselling'),
    'outshine': ('outshone', 'outshone', 'outshining'),
    'outspan': ('outspanned', 'outspanned', 'outspanning'),
    'outstrip': ('outstripped', 'outstripped', 'outstripping'),
    'outvie': ('outvied', 'outvieed', 'outvieing'),
    'outwear': ('outwore', 'outworn', 'outwearing'),
    'outwit': ('outwitted', 'outwitted', 'outwitting'),
    'overbear': ('overbore', 'overborne', 'overbearing'),
    'overbid': ('overbid', 'overbid', 'overbidding'),
    'overcast': ('overcast', 'overcast', 'overcasting'),
    'overcome': ('overcame', 'overcame', 'overcoming'),
    'overcome2': ('overcame', 'overcome', 'overcoming'),
    'overcrop': ('overcropped', 'overcropped', 'overcropping'),
    'overdo': ('overdid', 'overdone', 'overdoing'),
    'overdraw': ('overdrew', 'overdrawn', 'overdrawing'),
    'overdrive': ('overdrove', 'overdriven', 'overdriving'),
    'overfly': ('overflew', 'overflown', 'overflying'),
    'overgrow': ('overgrew', 'overgrown', 'overgrowing'),
    'overhang': ('overhung', 'overhung', 'overhanging'),
    'overhear': ('overheard', 'overheard', 'overhearing'),
    'overlap': ('overlapped', 'overlapped', 'overlapping'),
    'overlay': ('overlaid', 'overlaid', 'overlaying'),
    'overlie': ('overlay', 'overlain', 'overlying'),
    'overpay': ('overpaid', 'overpaid', 'overpaying'),
    'override': ('overrode', 'overridden', 'overriding'),
    'overrun': ('overran', 'overran', 'overrunning'),
    'oversee': ('oversaw', 'overseen', 'overseeing'),
    'oversew': ('oversewed', 'oversewn', 'oversewing'),
    'overshoot': ('overshot', 'overshot', 'overshooting'),
    'oversleep': ('overslept', 'overslept', 'oversleeping'),
    'overspend': ('overspent', 'overspent', 'overspending'),
    'overstep': ('overstepped', 'overstepped', 'overstepping'),
    'overtake': ('overtook', 'overtaken', 'overtaking'),
    'overthrow': ('overthrew', 'overthrown', 'overthrowing'),
    'overtop': ('overtopped', 'overtopped', 'overtopping'),
    'overwrite': ('overwrote', 'overwritten', 'overwriting'),
    'pad': ('padded', 'padded', 'padding'),
    'pan': ('panned', 'panned', 'panning'),
    'panic': ('panicked', 'panicked', 'panicking'),
    'par': ('parred', 'parred', 'parring'),
    'partake': ('partook', 'partaken', 'partaking'),
    'pat': ('patted', 'patted', 'patting'),
    'patrol': ('patrolled', 'patrolled', 'patrolling'),
    'pay': ('paid', 'paid', 'paying'),
    'pee-pee': ('pee-peed', 'pee-peed', 'pee-peeing'),
    'pee': ('peed', 'peed', 'peeing'),
    'peg': ('pegged', 'pegged', 'pegging'),
    'pen': ('penned', 'penned', 'penning'),
    'permit': ('permitted', 'permitted', 'permitting'),
    'pet': ('petted', 'petted', 'petting'),
    'pettifog': ('pettifogged', 'pettifogged', 'pettifogging'),
    'photostat': ('photostatted', 'photostatted', 'photostatting'),
    'picnic': ('picnicked', 'picnicked', 'picnicking'),
    'piece-dye': ('piece-dyed', 'piece-dyed', 'piece-dyeing'),
    'pig': ('pigged', 'pigged', 'pigging'),
    'pin': ('pinned', 'pinned', 'pinning'),
    'pip': ('pipped', 'pipped', 'pipping'),
    'pistol-whip': ('pistol-whipped', 'pistol-whipped', 'pistol-whipping'),
    'pit': ('pitted', 'pitted', 'pitting'),
    'plan': ('planned', 'planned', 'planning'),
    'plead': ('pleaded', 'pleaded', 'pleading'),
    'plead2': ('pled', 'pled', 'pleading'),
    'plod': ('plodded', 'plodded', 'plodding'),
    'plop': ('plopped', 'plopped', 'plopping'),
    'plot': ('plotted', 'plotted', 'plotting'),
    'plug': ('plugged', 'plugged', 'plugging'),
    'plummet': ('plummetted', 'plummetted', 'plummetting'),
    'pod': ('podded', 'podded', 'podding'),
    'pop': ('popped', 'popped', 'popping'),
    'pot': ('potted', 'potted', 'potting'),
    'prefer': ('preferred', 'preferred', 'preferring'),
    'prepay': ('prepaid', 'prepaid', 'prepaying'),
    'prim': ('primmed', 'primmed', 'primming'),
    'prizefight': ('prizefought', 'prizefought', 'prizefighting'),
    'prod': ('prodded', 'prodded', 'prodding'),
    'program': ('programmed', 'programmed', 'programming'),
    'prop': ('propped', 'propped', 'propping'),
    'propel': ('propelled', 'propelled', 'propelling'),
    'prove': ('proved', 'proved', 'proving'),
    'prove2': ('proved', 'proven', 'proving'),
    'pun': ('punned', 'punned', 'punning'),
    'pup': ('pupped', 'pupped', 'pupping'),
    'puree': ('pureed', 'pureed', 'pureeing'),
    'put': ('put', 'put', 'putting'),
    'queue': ('queued', 'queued', 'queueing'),
    'quick-freeze': ('quick-froze', 'quick-frozen', 'quick-freezing'),
    'quickstep': ('quickstepped', 'quickstepped', 'quickstepping'),
    'quip': ('quipped', 'quipped', 'quipping'),
    'quit': ('quit', 'quit', 'quitting'),
    'quiz': ('quizzed', 'quizzed', 'quizzing'),
    'rabbit': ('rabbitted', 'rabbitted', 'rabbitting'),
    'radiate': ('radiated', 'radiated', 'radiating'),
    'rag': ('ragged', 'ragged', 'ragging'),
    'ram': ('rammed', 'rammed', 'ramming'),
    'rap': ('rapped', 'rapped', 'rapping'),
    'rat': ('ratted', 'ratted', 'ratting'),
    're-equip': ('re-equipped', 're-equipped', 're-equipping'),
    'read': ('read', 'read', 'reading'),
    'readmit': ('readmitted', 'readmitted', 'readmitting'),
    'reallot': ('reallotted', 'reallotted', 'reallotting'),
    'reave': ('reft', 'reft', 'reaving'),
    'rebel': ('rebelled', 'rebelled', 'rebelling'),
    'rebind': ('rebound', 'rebound', 'rebinding'),
    'rebuild': ('rebuilt', 'rebuilt', 'rebuilding'),
    'rebut': ('rebutted', 'rebutted', 'rebutting'),
    'recap': ('recapped', 'recapped', 'recapping'),
    'recast': ('recast', 'recast', 'recasting'),
    'recommit': ('recommitted', 'recommitted', 'recommitting'),
    'recur': ('recurred', 'recurred', 'recurring'),
    'red-eye': ('red-eyed', 'red-eyed', 'red-eyeing'),
    'redo': ('redid', 'redone', 'redoing'),
    'reeve': ('rove', 'rove', 'reeving'),
    'refer': ('referred', 'referred', 'referring'),
    'referee': ('refereed', 'refereed', 'refereeing'),
    'refit': ('refitted', 'refitted', 'refitting'),
    'regret': ('regretted', 'regretted', 'regretting'),
    'rejig': ('rejigged', 'rejigged', 'rejigging'),
    'relay': ('relaid', 'relaid', 'relaying'),
    'remake': ('remade', 'remade', 'remaking'),
    'remit': ('remitted', 'remitted', 'remitting'),
    'rend': ('rent', 'rent', 'rending'),
    'render-set': ('render-set', 'render-set', 'render-setting'),
    'repay': ('repaid', 'repaid', 'repaying'),
    'repel': ('repelled', 'repelled', 'repelling'),
    'repot': ('repotted', 'repotted', 'repotting'),
    'rerun': ('reran', 'reran', 'rerunning'),
    'resell': ('resold', 'resold', 'reselling'),
    'reset': ('reset', 'reset', 'resetting'),
    'resew': ('resewed', 'resewn', 'resewing'),
    'reship': ('reshipped', 'reshipped', 'reshipping'),
    'reshoot': ('reshot', 'reshot', 'reshooting'),
    'resubmit': ('resubmitted', 'resubmitted', 'resubmitting'),
    'ret': ('retted', 'retted', 'retting'),
    'retake': ('retook', 'retaken', 'retaking'),
    'retell': ('retold', 'retold', 'retelling'),
    'rethink': ('rethought', 'rethought', 'rethinking'),
    'retie': ('retied', 'retied', 'retying'),
    'retransmit': ('retransmitted', 'retransmitted', 'retransmitting'),
    'retrofit': ('retrofitted', 'retrofitted', 'retrofitting'),
    'rev': ('revved', 'revved', 'revving'),
    'revet': ('revetted', 'revetted', 'revetting'),
    'rewrite': ('rewrote', 'rewritten', 'rewriting'),
    'rib': ('ribbed', 'ribbed', 'ribbing'),
    'rid': ('rid', 'rid', 'ridding'),
    'rid2': ('ridded', 'ridded', 'ridding'),
    'ride': ('rode', 'ridden', 'riding'),
    'rig': ('rigged', 'rigged', 'rigging'),
    'rim': ('rimmed', 'rimmed', 'rimming'),
    'ring': ('rang', 'rung', 'ringing'),
    'rip': ('ripped', 'ripped', 'ripping'),
    'rise': ('rose', 'risen', 'rising'),
    'rive': ('rived', 'riven', 'riving'),
    'rob': ('robbed', 'robbed', 'robbing'),
    'rot': ('rotted', 'rotted', 'rotting'),
    'rough-hew': ('rough-hewed', 'rough-hewn', 'rough-hewing'),
    'roughcast': ('roughcast', 'roughcast', 'roughcasting'),
    'rub': ('rubbed', 'rubbed', 'rubbing'),
    'run': ('ran', 'ran', 'running'),
    'run2': ('ran', 'run', 'running'),
    'rut': ('rutted', 'rutted', 'rutting'),
    'sag': ('sagged', 'sagged', 'sagging'),
    'sandbag': ('sandbagged', 'sandbagged', 'sandbagging'),
    'sap': ('sapped', 'sapped', 'sapping'),
    'saute': ('sauteed', 'sauteed', 'sauteing'),
    'saw': ('sawed', 'sawed', 'sawing'),
    'say': ('said', 'said', 'saying'),
    'scab': ('scabbed', 'scabbed', 'scabbing'),
    'scam': ('scammed', 'scammed', 'scamming'),
    'scan': ('scanned', 'scanned', 'scanning'),
    'scar': ('scarred', 'scarred', 'scarring'),
    'scat': ('scatted', 'scatted', 'scatting'),
    'schlep': ('schlepped', 'schlepped', 'schlepping'),
    'scrag': ('scragged', 'scragged', 'scragging'),
    'scram': ('scrammed', 'scrammed', 'scramming'),
    'scrap': ('scrapped', 'scrapped', 'scrapping'),
    'scrub': ('scrubbed', 'scrubbed', 'scrubbing'),
    'scud': ('scudded', 'scudded', 'scudding'),
    'scum': ('scummed', 'scummed', 'scumming'),
    'see': ('saw', 'seen', 'seeing'),
    'seek': ('sought', 'sought', 'seeking'),
    'sell': ('sold', 'sold', 'selling'),
    'send': ('sent', 'sent', 'sending'),
    'set': ('set', 'set', 'setting'),
    'sew': ('sewed', 'sewed', 'sewing'),
    'sew2': ('sewed', 'sewn', 'sewing'),
    'shag': ('shagged', 'shagged', 'shagging'),
    'shake': ('shook', 'shaken', 'shaking'),
    'sham': ('shammed', 'shammed', 'shamming'),
    'sharpshoot': ('sharpshot', 'sharpshot', 'sharpshooting'),
    'shave': ('shaved', 'shaved', 'shaving'),
    'shave2': ('shaved', 'shaven', 'shaving'),
    'she-bop': ('she-bopped', 'she-bopped', 'she-bopping'),
    'shear': ('sheared', 'shorn', 'shearing'),
    'shear2': ('shore', 'shorn', 'shearing'),
    'shed': ('shed', 'shed', 'shedding'),
    'shellac': ('shellacked', 'shellacked', 'shellacking'),
    'shew': ('shewed', 'shewn', 'shewing'),
    'shin': ('shinned', 'shinned', 'shinning'),
    'shine': ('shone', 'shone', 'shining'),
    'ship': ('shipped', 'shipped', 'shipping'),
    'shit': ('shat', 'shat', 'shitting'),
    'shoe': ('shod', 'shod', 'shoeing'),
    'shoe2': ('shoed', 'shoed', 'shoeing'),
    'shoetree': ('shoetreed', 'shoetreed', 'shoetreeing'),
    'shoot': ('shot', 'shot', 'shooting'),
    'shop': ('shopped', 'shopped', 'shopping'),
    'show': ('showed', 'showed', 'showing'),
    'show2': ('showed', 'shown', 'showing'),
    'shred': ('shredded', 'shredded', 'shredding'),
    'shrink': ('shrank', 'shrunk', 'shrinking'),
    'shrinkwrap': ('shrinkwrapped', 'shrinkwrapped', 'shrinkwrapping'),
    'shrive': ('shrove', 'shriven', 'shriving'),
    'shrug': ('shrugged', 'shrugged', 'shrugging'),
    'shun': ('shunned', 'shunned', 'shunning'),
    'shut': ('shut', 'shut', 'shutting'),
    'sic': ('sicced', 'sicced', 'siccing'),
    'side-slip': ('side-slipped', 'side-slipped', 'side-slipping'),
    'sidestep': ('sidestepped', 'sidestepped', 'sidestepping'),
    'sight-read': ('sight-read', 'sight-read', 'sight-reading'),
    'sight-sing': ('sight-sang', 'sight-sung', 'sight-singing'),
    'sightsee': ('sightsaw', 'sightseen', 'sightseeing'),
    'signal': ('signalled', 'signalled', 'signalling'),
    'sin': ('sinned', 'sinned', 'sinning'),
    'sing': ('sang', 'sung', 'singing'),
    'singe': ('singed', 'singed', 'singeing'),
    'sink': ('sank', 'sunk', 'sinking'),
    'sip': ('sipped', 'sipped', 'sipping'),
    'sit': ('sat', 'sat', 'sitting'),
    'skid': ('skidded', 'skidded', 'skidding'),
    'skim': ('skimmed', 'skimmed', 'skimming'),
    'skin': ('skinned', 'skinned', 'skinning'),
    'skinny-dip': ('skinny-dipped', 'skinny-dipped', 'skinny-dipping'),
    'skip': ('skipped', 'skipped', 'skipping'),
    'skydive': ('skydove', 'skydove', 'skydiving'),
    'slag': ('slagged', 'slagged', 'slagging'),
    'slam': ('slammed', 'slammed', 'slamming'),
    'slap': ('slapped', 'slapped', 'slapping'),
    'slay': ('slew', 'slain', 'slaying'),
    'sled': ('sledded', 'sledded', 'sledding'),
    'sleep': ('slept', 'slept', 'sleeping'),
    'slide': ('slid', 'slid', 'sliding'),
    'slim': ('slimmed', 'slimmed', 'slimming'),
    'sling': ('slung', 'slung', 'slinging'),
    'slink': ('slunk', 'slunk', 'slinking'),
    'slip': ('slipped', 'slipped', 'slipping'),
    'slit': ('slit', 'slit', 'slitting'),
    'slog': ('slogged', 'slogged', 'slogging'),
    'slop': ('slopped', 'slopped', 'slopping'),
    'slot': ('slotted', 'slotted', 'slotting'),
    'slug': ('slugged', 'slugged', 'slugging'),
    'slum': ('slummed', 'slummed', 'slumming'),
    'slur': ('slurred', 'slurred', 'slurring'),
    'smite': ('smit', 'smitten', 'smiting'),
    'smite2': ('smote', 'smitten', 'smiting'),
    'smut': ('smutted', 'smutted', 'smutting'),
    'snag': ('snagged', 'snagged', 'snagging'),
    'snap': ('snapped', 'snapped', 'snapping'),
    'snip': ('snipped', 'snipped', 'snipping'),
    'snog': ('snogged', 'snogged', 'snogging'),
    'snorkel': ('snorkelled', 'snorkelled', 'snorkelling'),
    'snowshoe': ('snowshoed', 'snowshoed', 'snowshoeing'),
    'snub': ('snubbed', 'snubbed', 'snubbing'),
    'sob': ('sobbed', 'sobbed', 'sobbing'),
    'sod': ('sodded', 'sodded', 'sodding'),
    'sop': ('sopped', 'sopped', 'sopping'),
    'sow': ('sowed', 'sowed', 'sowing'),
    'sow2': ('sowed', 'sown', 'sowing'),
    'spam': ('spammed', 'spammed', 'spamming'),
    'span': ('spanned', 'spanned', 'spanning'),
    'spar': ('sparred', 'sparred', 'sparring'),
    'spat': ('spatted', 'spatted', 'spatting'),
    'speak': ('spoke', 'spoken', 'speaking'),
    'speech-read': ('speech-read', 'speech-read', 'speech-reading'),
    'speed': ('sped', 'sped', 'speeding'),
    'spellbind': ('spellbound', 'spellbound', 'spellbinding'),
    'spend': ('spent', 'spent', 'spending'),
    'spill': ('spilled', 'spilled', 'spilling'),
    'spin': ('spun', 'spun', 'spining'),
    'spin2': ('spun', 'spun', 'spinning'),
    'spit': ('spat', 'spat', 'spitting'),
    'spit2': ('spit', 'spit', 'spitting'),
    'splat': ('splatted', 'splatted', 'splatting'),
    'split': ('split', 'split', 'splitting'),
    'spoil': ('spoilt', 'spoilt', 'spoiling'),
    'spot': ('spotted', 'spotted', 'spotting'),
    'spotlight': ('spotlit', 'spotlit', 'spotlighting'),
    'spread': ('spread', 'spread', 'spreading'),
    'spree': ('spreed', 'spreed', 'spreeing'),
    'spring': ('sprang', 'sprung', 'springing'),
    'spud': ('spudded', 'spudded', 'spudding'),
    'spur': ('spurred', 'spurred', 'spurring'),
    'squat': ('squatted', 'squatted', 'squatting'),
    'squeegee': ('squeegeed', 'squeegeed', 'squeegeeing'),
    'stab': ('stabbed', 'stabbed', 'stabbing'),
    'stag': ('stagged', 'stagged', 'stagging'),
    'stand': ('stood', 'stood', 'standing'),
    'star': ('starred', 'starred', 'starring'),
    'stare': ('stare', 'stared', 'staring'),
    'stare2': ('stared', 'stared', 'staring'),
    'stave': ('stove', 'stove', 'staving'),
    'steal': ('stole', 'stolen', 'stealing'),
    'stem': ('stemmed', 'stemmed', 'stemming'),
    'step': ('stepped', 'stepped', 'stepping'),
    'stet': ('stetted', 'stetted', 'stetting'),
    'stick': ('stuck', 'stuck', 'sticking'),
    'sting': ('stung', 'stung', 'stinging'),
    'stink': ('stank', 'stunk', 'stinking'),
    'stir': ('stirred', 'stirred', 'stirring'),
    'stock-take': ('stock-took', 'stock-taken', 'stock-taking'),
    'stop': ('stopped', 'stopped', 'stopping'),
    'strap': ('strapped', 'strapped', 'strapping'),
    'strew': ('strewed', 'strewn', 'strewing'),
    'stride': ('strod', 'stridden', 'striding'),
    'stride2': ('strode', 'stridden', 'striding'),
    'strike': ('struck', 'struck', 'striking'),
    'string': ('strung', 'strung', 'string'),
    'string2': ('strung', 'strung', 'stringing'),
    'strip': ('stripped', 'stripped', 'stripping'),
    'strive': ('strove', 'striven', 'striving'),
    'strop': ('stropped', 'stropped', 'stropping'),
    'strum': ('strummed', 'strummed', 'strumming'),
    'strut': ('strutted', 'strutted', 'strutting'),
    'stub': ('stubbed', 'stubbed', 'stubbing'),
    'stud': ('studded', 'studded', 'studding'),
    'stun': ('stunned', 'stunned', 'stunning'),
    'stymie': ('stymied', 'stymied', 'stymying'),
    'sub': ('subbed', 'subbed', 'subbing'),
    'sublet': ('sublet', 'sublet', 'subletting'),
    'submit': ('submitted', 'submitted', 'submitting'),
    'sum': ('summed', 'summed', 'summing'),
    'summit': ('summitted', 'summitted', 'summitting'),
    'sun': ('sunned', 'sunned', 'sunning'),
    'suntan': ('suntanned', 'suntanned', 'suntanning'),
    'sup': ('supped', 'supped', 'supping'),
    'swab': ('swabbed', 'swabbed', 'swabbing'),
    'swag': ('swagged', 'swagged', 'swagging'),
    'swan': ('swanned', 'swanned', 'swanning'),
    'swap': ('swapped', 'swapped', 'swapping'),
    'swat': ('swatted', 'swatted', 'swatting'),
    'swear': ('swore', 'sworn', 'swearing'),
    'sweep': ('swept', 'swept', 'sweeping'),
    'swell': ('swelled', 'swelled', 'swelling'),
    'swell2': ('swelled', 'swollen', 'swelling'),
    'swig': ('swigged', 'swigged', 'swigging'),
    'swim': ('swam', 'swum', 'swimming'),
    'swing': ('swung', 'swung', 'swinging'),
    'swing2': ('swung', 'swung', 'swinning'),
    'switch-hit': ('switch-hit', 'switch-hit', 'switch-hitting'),
    'swot': ('swotted', 'swotted', 'swotting'),
    'tag': ('tagged', 'tagged', 'tagging'),
    'tailor-make': ('tailor-made', 'tailor-made', 'tailor-making'),
    'take': ('took', 'taken', 'taking'),
    'tan': ('tanned', 'tanned', 'tanning'),
    'tap': ('tapped', 'tapped', 'tapping'),
    'tar': ('tarred', 'tarred', 'tarring'),
    'tarmac': ('tarmacked', 'tarmacked', 'tarmacing'),
    'tat': ('tatted', 'tatted', 'tatting'),
    'teabag': ('teabagged', 'teabagged', 'teabagging'),
    'teach': ('taught', 'taught', 'teaching'),
    'tear': ('tore', 'torn', 'tearing'),
    'tee': ('teed', 'teed', 'teeing'),
    'telecast': ('telecast', 'telecast', 'telecasting'),
    'tell': ('told', 'told', 'telling'),
    'thermostat': ('thermostatted', 'thermostatted', 'thermostatting'),
    'thin': ('thinned', 'thinned', 'thinning'),
    'think': ('thought', 'thought', 'thinking'),
    'thrive': ('thrived', 'thrived', 'thriving'),
    'throb': ('throbbed', 'throbbed', 'throbbing'),
    'throw': ('threw', 'thrown', 'throw'),
    'throw2': ('threw', 'thrown', 'throwing'),
    'thrum': ('thrummed', 'thrummed', 'thrumming'),
    'thrust': ('thrust', 'thrust', 'thrust'),
    'thrust2': ('thrust', 'thrust', 'thrusting'),
    'thud': ('thudded', 'thudded', 'thudding'),
    'tie-dye': ('tie-dyed', 'tie-dyed', 'tie-dyeing'),
    'tie': ('tied', 'tied', 'tying'),
    'tin': ('tinned', 'tinned', 'tinning'),
    'tinge': ('tinged', 'tinged', 'tingeing'),
    'tip': ('tipped', 'tipped', 'tipping'),
    'tippytoe': ('tippytoeed', 'tippytoeed', 'tippytoeing'),
    'tiptoe': ('tiptoeed', 'tiptoeed', 'tiptoeing'),
    'tittup': ('tittupped', 'tittupped', 'tittupping'),
    'toe': ('toed', 'toed', 'toeing'),
    'tog': ('togged', 'togged', 'togging'),
    'tongue-tie': ('tongue-tied', 'tongue-tied', 'tongue-tying'),
    'top': ('topped', 'topped', 'topping'),
    'tot': ('totted', 'totted', 'totting'),
    'traffic': ('trafficked', 'trafficked', 'trafficking'),
    'tram': ('trammed', 'trammed', 'tramming'),
    'trammel': ('trammelled', 'trammelled', 'trammelling'),
    'transfer': ('transferred', 'transferred', 'transferring'),
    'transmit': ('transmitted', 'transmitted', 'transmitting'),
    'trap': ('trapped', 'trapped', 'trapping'),
    'travel': ('travelled', 'travelled', 'travelling'),
    'tread': ('trod', 'trodden', 'treading'),
    'tree': ('treed', 'treed', 'treeing'),
    'trek': ('trekked', 'trekked', 'trekking'),
    'trepan': ('trepanned', 'trepanned', 'trepanning'),
    'trim': ('trimmed', 'trimmed', 'trimming'),
    'trip': ('tripped', 'tripped', 'tripping'),
    'trot': ('trotted', 'trotted', 'trotting'),
    'trouble-shoot': ('trouble-shot', 'trouble-shot', 'trouble-shooting'),
    'tug': ('tugged', 'tugged', 'tugging'),
    'tut-tut': ('tut-tutted', 'tut-tutted', 'tut-tutting'),
    'tut': ('tutted', 'tutted', 'tutting'),
    'twig': ('twigged', 'twigged', 'twigging'),
    'twin': ('twinned', 'twinned', 'twinning'),
    'twit': ('twitted', 'twitted', 'twitting'),
    'two-step': ('two-stepped', 'two-stepped', 'two-stepping'),
    'typecast': ('typecast', 'typecast', 'typecasting'),
    'typeset': ('typeset', 'typeset', 'typesetting'),
    'typewrite': ('typewrote', 'typewritten', 'typewriting'),
    'unbar': ('unbarred', 'unbarred', 'unbarring'),
    'unbend': ('unbent', 'unbent', 'unbending'),
    'unbind': ('unbound', 'unbound', 'unbinding'),
    'unclip': ('unclipped', 'unclipped', 'unclipping'),
    'unclothe': ('unclad', 'unclad', 'unclothing'),
    'underbid': ('underbid', 'underbid', 'underbidding'),
    'undercut': ('undercut', 'undercut', 'undercutting'),
    'undergird': ('undergirt', 'undergirt', 'undergirding'),
    'undergo': ('underwent', 'undergone', 'undergoing'),
    'underlay': ('underlaid', 'underlaid', 'underlaying'),
    'underlie': ('underlay', 'underlain', 'underlying'),
    'underpay': ('underpaid', 'underpaid', 'underpaying'),
    'underpin': ('underpinned', 'underpinned', 'underpinning'),
    'undersell': ('undersold', 'undersold', 'underselling'),
    'undershoot': ('undershot', 'undershot', 'undershooting'),
    'understand': ('understood', 'understood', 'understanding'),
    'undertake': ('undertook', 'undertaken', 'undertaking'),
    'underwrite': ('underwrote', 'underwritten', 'underwriting'),
    'undo': ('undid', 'undone', 'undoing'),
    'unfit': ('unfitted', 'unfitted', 'unfitting'),
    'unfreeze': ('unfroze', 'unfrozen', 'unfreezing'),
    'unknot': ('unknotted', 'unknotted', 'unknotting'),
    'unlearn': ('unlearnt', 'unlearnt', 'unlearning'),
    'unmake': ('unmade', 'unmade', 'unmaking'),
    'unman': ('unmanned', 'unmanned', 'unmanning'),
    'unpin': ('unpinned', 'unpinned', 'unpinning'),
    'unplug': ('unplugged', 'unplugged', 'unplugging'),
    'unsay': ('unsaid', 'unsaid', 'unsaying'),
    'unstring': ('unstrung', 'unstrung', 'unstringing'),
    'unteach': ('untaught', 'untaught', 'unteaching'),
    'untie': ('untied', 'untied', 'untying'),
    'unwind': ('unwound', 'unwound', 'unwinding'),
    'unwrap': ('unwrapped', 'unwrapped', 'unwrapping'),
    'unzip': ('unzipped', 'unzipped', 'unzipping'),
    'up': ('upped', 'upped', 'upping'),
    'upheave': ('uphove', 'uphove', 'upheaving'),
    'uphold': ('upheld', 'upheld', 'upholding'),
    'uprise': ('uprose', 'uprisen', 'uprising'),
    'upset': ('upset', 'upset', 'upseting'),
    'upset2': ('upset', 'upset', 'upsetting'),
    'vet': ('vetted', 'vetted', 'vetting'),
    'victual': ('victualled', 'victualled', 'victualling'),
    'vie': ('vied', 'vied', 'vying'),
    'vitriol': ('vitriolled', 'vitriolled', 'vitriolling'),
    'wad': ('wadded', 'wadded', 'wadding'),
    'wag': ('wagged', 'wagged', 'wagging'),
    'wake': ('woke', 'woken', 'waking'),
    'wan': ('wanned', 'wanned', 'wanning'),
    'war': ('warred', 'warred', 'warring'),
    'wave': ('waved', 'waved', 'waving'),
    'waylay': ('waylaid', 'waylain', 'waylaying'),
    'wear': ('wore', 'worn', 'wearing'),
    'weave': ('weaved', 'weaved', 'weaving'),
    'weave2': ('wove', 'woven', 'weaving'),
    'web': ('webbed', 'webbed', 'webbing'),
    'wed': ('wed', 'wed', 'wedding'),
    'wee-wee': ('wee-weed', 'wee-weed', 'wee-weeing'),
    'wee': ('weed', 'weed', 'weeing'),
    'weep': ('wept', 'wept', 'weeping'),
    'wet': ('wet', 'wet', 'wetting'),
    'wham': ('whammed', 'whammed', 'whamming'),
    'whet': ('whetted', 'whetted', 'whetting'),
    'whip': ('whipped', 'whipped', 'whipping'),
    'whipsaw': ('whipsawed', 'whipsawn', 'whipsawing'),
    'whir': ('whirred', 'whirred', 'whirring'),
    'whiz': ('whizzed', 'whizzed', 'whizzing'),
    'whop': ('whopped', 'whopped', 'whopping'),
    'win': ('won', 'won', 'winning'),
    'wind': ('wound', 'wound', 'winding'),
    'window-shop': ('window-shopped', 'window-shopped', 'window-shopping'),
    'wiretap': ('wiretapped', 'wiretapped', 'wiretapping'),
    'withdraw': ('withdrew', 'withdrawn', 'withdrawing'),
    'withhold': ('withheld', 'withheld', 'withholding'),
    'withstand': ('withstood', 'withstood', 'withstanding'),
    'worship': ('worshipped', 'worshipped', 'worshipping'),
    'wrap': ('wrapped', 'wrapped', 'wrapping'),
    'wring': ('wrung', 'wrung', 'wringing'),
    'write': ('wrote', 'written', 'writing'),
    'yap': ('yapped', 'yapped', 'yapping'),
    'yarn-dye': ('yarn-dyed', 'yarn-dyed', 'yarn-dyeing'),
    'yen': ('yenned', 'yenned', 'yenning'),
    'yip': ('yipped', 'yipped', 'yipping'),
    'yum': ('yummed', 'yummed', 'yumming'),
    'zap': ('zapped', 'zapped', 'zapping'),
    'zigzag': ('zigzagged', 'zigzagged', 'zigzagging'),
    'zip': ('zipped', 'zipped', 'zipping')}

########NEW FILE########
__FILENAME__ = item_model
'Represent existents with Item classes, instantiated by games/stories.'

__author__ = 'Nick Montfort'
__copyright__ = 'Copyright 2011 Nick Montfort'
__license__ = 'ISC'
__version__ = '0.5.0.0'
__status__ = 'Development'

import random
import re
import types

import can
import discourse_model

def check_attributes(identifier, required, impossible, attributes):
    'Raise errors if required attributes are missing or impossible ones present.'
    some_wrong = ''
    if 'parent' in impossible:
        if not len(identifier.split()) == 1:
            some_wrong += ('The item "' + identifier + '" has a link and ' +
                           'parent specified, but this type of item is ' +
                           'placed automatically in the item tree and cannot ' +
                           'have these.')
        impossible.remove('parent')
    for missing in required:
        if missing not in attributes:
            some_wrong += ('The item "' + identifier + '" is missing ' +
                'a required attribute: "' + missing + '".\n')
    for present in impossible:
        if present in attributes:
            some_wrong += ('For the item "' + identifier + '" there is ' +
                'an attempt to specify the attribute "' + present + 
                '" which cannot be specified for this type of item.\n')
    if len(some_wrong) > 0:
        raise StandardError(some_wrong[:-1])

def determine_called(called):
    'Using the called string, determine the name triple.'
    match = re.match('(\(.*\)) +[^\(]', called)
    if match is None:
        before_adjs = []
    else:
        before_adjs = match.group(1)[1:-1].split(') (')
        called = called[match.end(1) + 1:]
        for i in range(0, len(before_adjs)):
            before_adjs[i] = before_adjs[i]
    match = re.search('[^\)] +(\(.*\))$', called)
    if match is None:
        after_adjs = []
    else:
        after_adjs = match.group(1)[1:-1].split(') (')
        called = re.sub(' +' + match.group(1), '', called)
        called = called[:match.start(1) - 1:]
        for i in range(0, len(after_adjs)):
            after_adjs[i] = after_adjs[i]
    return (before_adjs, called, after_adjs)

def set_features(item, category, keywords):
    """Sets features modeling the current state (condition) of an Item.

    These data attributes represent the item's important features within
    the fiction/game world. The values held in particular entries are
    changed by Modify actions. The location and configuration of an item
    in the overall context of the world (what parent it has and what its link
    to the parent is) is not represented here. That aspect of the world is
    changed by Configure instead of Modify. These features model the item
    itself, not where it is located.

    The built-in features, represented by data attributes, are:

    article: string
        The initial article to use. "a" will be adjusted to "an" if
        necessary when text is generated.

    called: string
        What the item can be called when text is generated.

    referring: string | None
        Additional words that can be typed to refer to the item. Optional words
        first, separated by spaces; then "|", then space-delimited names. If 
        referring is the '' (the empty string, which is the default), there are 
        no special words added, but the item can still be referred to by words
        derived from its category and qualities. For the special case in which
        there should be no way to refer to an item, set referring to None.

    qualities: list of strings
        Terms describing the item; synonyms of these are used in recognition
        and the terms can be used in simulation.

    gender: 'female' | 'male' | 'neuter'
        Whether the item should be referred to as a she, he, or it.

    glow: float
        How much light the item is radiating, typically in (0, 1).
        Can be set outside of (0, 1) for supernatural reasons.

    number: 'singular' | 'plural'
        Whether the item should be referred to in the singular or plural.

    prominence: float
        How visible or noticeable an item is, typically in (0, 1).

    transparent: True | False
        Can one see through the item and see what is inside?

    mention: True | False
        Should the item ever be mentioned (for instance, in lists)? Almost
        everything should be, but not, for instance, part of another item 
        that is described in the main description of the parent item.

    allowed: can.function(tag, link, world)
        Determines what an item can contain. Specifically, returns whether
        the item 'tag' can be a child of the parent, in the specified link
        relationship, given the situation of world.

    shared: list of strings
        If a Room, the tags of SharedThings that this Room has; otherwise [].

    sight: string
        Template that produces a description of what an agent sees when
        looking at an item.

    touch: string
        Template that produces a description of what an agent feels when
        touching at an item. Should be able to complete the sentence
        "The adventurer feels ..." or "You feel ..."

    hearing: string
        Similar template for hearing.

    smell: string
        Similar template for hearing.

    taste: string
        Similar template for taste."""

    settings = {
        'article': '',
        'called': '',
        'referring': '',
        'qualities': [],
        'glow': 0.0,
        'prominence': 0.5,
        'transparent': False,
        'mention': True,
        'allowed' : can.not_have_items,
        'shared' : []
    }
    settings.update(keywords)
    if (settings['referring'] is not None and
        len(settings['referring']) > 0 and '|' not in settings['referring']):
        raise StandardError('The item tagged "' + str(item) +
         '" has a nonempty "referring" attribute without a "|" ' +
         'separator. Place "|" after any optional words and before ' +
         'any names, at the very beginning or end, if appropriate.')
    if category not in settings['qualities']:
        settings['qualities'] += [category]
    for (name, value) in settings.items():
        if re.search('[^a-z_]', name):
            raise StandardError('A feature with invalid name "' + name +
             '" is used in the fiction module.')
        setattr(item, name, value)
    return item

class Item(object):
    'Abstract base class for items.'

    def __init__(self, tag_and_parent, category, **keywords):        
        if self.__class__ == Item:
            raise StandardError('Attempt in Item "' + self._tag +
                  '" to instantiate abstract base class world_model.Item')
        if tag_and_parent == '@cosmos':
            self._tag = tag_and_parent
            (self.link, self.parent) = (None, None)
        else:
            (self._tag, self.link, self.parent) = tag_and_parent.split()
        if (not type(self._tag) == types.StringType) or len(self._tag) == 0:
            raise StandardError('An Item lacking a "tag" attribute, ' +
             'or with a non-string or empty tag, has been specified. A ' +
             'valid tag is required for each item.')
        if not re.match('@[a-z0-9_]{2,30}', self._tag):
            raise StandardError('The tag "' + self._tag +
             '" is invalid. Tags start with "@" and otherwise consist of ' +
             '2-30 characters which are only lowercase letters, numerals, ' +
             'and underscores.')
        self._children = []
        for i in ['actor', 'door', 'room', 'thing', 'substance']:
            setattr(self, i, (category == i))
        self.blanked = False
        # Five of these features have to be set "manually" (private properties
        # set directly) now because their setters depend on each other.
        #
        # Called: what an item is called is included in the way to refer to it.
        # Gender and number: pronouns that can refer to an item depend on those.
        # Referring extra: The string with "extra" referring expressions.
        # Qualities: These are expanded into elements of a referring expression.
        #
        # Once the four setters run, whichever one runs last will leave 
        # "._referring" in the correct state.
        self._called = ([], '', [])
        self._gender = 'neuter'
        self._number = 'singular'
        self._referring_extra = '|'
        self._qualities = []
        self._referring = (set(), set(), set())
        self._sense = {}
        for sense in ['sight', 'touch', 'hearing', 'smell', 'taste']:
            setattr(self, sense, '')
        self = set_features(self, category, keywords)

    def __str__(self):
        return self._tag

    def __eq__(self, item):
        if item is None:
            return False
        if type(item) == types.StringType:
            return str(self) == item
        self_list = [str(self), self.article, self.called]
        item_list = [str(item), item.article, item.called]
        equal_attrs = (set(dir(self)) == set(dir(item)))
        if equal_attrs:
            for i in dir(self):
                if (not i[0] == '_' and not callable(getattr(self, i))):
                    equal_attrs &= (getattr(self, i) == getattr(item, i))
        return (self_list == item_list) and equal_attrs

    def __ne__(self, item):
        return not self.__eq__(item)

    def get_called(self):
        return self._called
    def set_called(self, string):
        self._called = determine_called(string)
        self._update_referring()
    called = property(get_called, set_called, 'Names used in output.')

    def get_referring(self):
        return self._referring
    def set_referring(self, string):
        self._referring_extra = string
        self._update_referring()
    referring = property(get_referring, set_referring,
                         'Triple of referring expressions.')

    def get_gender(self):
        return self._gender
    def set_gender(self, string):
        self._gender = string
        self._update_referring()
    gender = property(get_gender, set_gender, 'Grammatical gender.')

    def get_number(self):
        return self._number
    def set_number(self, string):
        self._number = string
        self._update_referring()
    number = property(get_number, set_number, 'Grammatical number.')

    def get_qualities(self):
        return self._qualities
    def set_qualities(self, quality_list):
        self._qualities = quality_list
        self._update_referring()
    qualities = property(get_qualities, set_qualities,
                         'Terms used to add referring words.')

    def get_sight(self):
        return self._sense['sight']
    def set_sight(self, string):
        self._sense['sight'] = discourse_model.reformat(string)
    sight = property(get_sight, set_sight,
                     'What is seen when an Item is looked at.')

    def get_touch(self):
        return self._sense['touch']
    def set_touch(self, string):
        'Setter. Needed because strings must be reformatted before being set.'
        self._sense['touch'] = discourse_model.reformat(string)
    touch = property(get_touch, set_touch,
                     'What is felt when an Item is touched.')

    def get_hearing(self):
        return self._sense['hearing']
    def set_hearing(self, string):
        self._sense['hearing'] = discourse_model.reformat(string)
    hearing = property(get_hearing, set_hearing,
                       'What is heard when an Item is listened to.')

    def get_smell(self):
        return self._sense['smell']
    def set_smell(self, string):
        self._sense['smell'] = discourse_model.reformat(string)
    smell = property(get_smell, set_smell,
                     'What is smelled when an Item is sniffed.')

    def get_taste(self):
        return self._sense['taste']
    def set_taste(self, string):
        self._sense['taste'] = discourse_model.reformat(string)
    taste = property(get_taste, set_taste,
                     'What is tasted when an Item is sampled.')

    def _update_referring(self):
        'Determine or update the triple of referring words.'
        if self._referring_extra is None:
            self._referring = ('', '', '')
        else:
            optional, _, names = self._referring_extra.partition('|')
            before = set(optional.strip().split() + self._called[0])
            after = set(optional.strip().split() + self._called[2])
            names = set(names.strip().split())
            if not ' ' in self._called[1]:
                names.add(self._called[1])
            if self.number == 'singular':
                if self.gender == 'neuter':
                    names.add('it')
                elif self.gender == 'female':
                    names.add('her')
                else:
                    names.add('him')
            else:
                names.add('them')
            for i in self.qualities:
                if i in discourse_model.QUALITY_WORDS:
                    (q_before,
                     q_names) = discourse_model.QUALITY_WORDS[i].split('|')
                    before.update(q_before.strip().split())
                    names.update(q_names.strip().split())
            self._referring = (before, names, after)

    def blank(self):
        'Erase an Item when nothing is known about it by an Actor.'
        self.article = 'the'
        self.called = 'object'
        if self.room:
            self.called = 'place'
        elif self.actor:
            self.called = 'individual'
        self.referring = None
        for attr in ['link', 'parent', 'sight', 'touch', 'hearing', 'smell',
                     'taste']:
            setattr(self, attr, '')
        self._children = []
        self.allowed = can.not_have_items
        self.blanked = True

    def noun_phrase(self, discourse=None, entire=True, extra_adjs='',
                    length=0.0):
        'Return the noun phrase representing this Item.'
        string = self.called[1]
        if len(self.called[0]) > 0 and length > 0.0:
            before_adjs = random.choice(self.called[0] + [''])
            string = (before_adjs + ' ' + string).strip()
        if len(self.called[2]) > 0 and length > 0.0:
            after_adjs = random.choice(self.called[2] + [''])
            string = (string + ' ' + after_adjs).strip()
        string = (extra_adjs + ' ' + string).strip()
        if discourse is None:
            # This method was called without a discourse parameter. In this
            # case, the correct article can't be generated and the givens list
            # can't be updated; so, return the noun phrase without an article.
            return string
        if entire:
            use_article = self.article
            if (self.article in discourse.indefinite and
                str(self) in discourse.givens):
                use_article = 'the'
            else:
                if self.article in ['a', 'an']:
                    use_article = 'a'
                    if string[:1] in ['a', 'e', 'i', 'o', 'u']:
                        use_article += 'n'
            if len(use_article) > 0:
                string = use_article + ' ' + string
        discourse.givens.add(str(self))
        return string

    def place(self, world):
        'Returns the Room this Item is located in, according to World.'
        tag = str(self)
        while not world.has('room', tag) and not tag == '@cosmos':
            tag = world.item[tag].parent
        return world.item[tag]

    @property
    def children(self):
        'Return the children of this Item.'
        return self._children

    def add_child(self, link, item, making_change=True):
        'Add (or remove) a child from this Item.'
        if not making_change:
            self.remove_child(link, item)
        else:
            if (link, item) not in self._children:
                self._children.append((link, item))

    def remove_child(self, link, item, making_change=True):
        'Remove (or add) a child from this Item.'
        if not making_change:
            self.add_child(link, item)
        else:
            if (link, item) in self._children:
                self._children.remove((link, item))

    def prevent(self, _, __):
        'By default, items do not prevent actions Subclasses can override.'
        return False

    def react(self, _, __):
        'By default, items do nothing when reacting. Subclasses can override.'
        return []

    def react_to_failed(self, _, __):
        'By default, items do nothing when reacting to a failed action.'
        return []


class Actor(Item):
    """Any Item that can initiate action, whether human-like or not.

    Features of interest:

    alive: True | False
        Actors can only act and react if alive. If not specified, this feature
        will always be True. Things can also have an alive feature, but it must
        be set when needed. It should probably be set on a subclass created
        for a particular Thing that can react and prevent.

    refuses: list of (string, when.function(world), string)
        Determines what an actor will refuse to do when commanded. The first
        string is matched against actions; the function determines whether or
        not the refusal will take place given a match; and the final string
        is a template used to generate a message explaining the refusal."""

    def __init__(self, tag_and_parent, **keywords):
        if 'alive' not in keywords:
            self.alive = True
        if 'refuses' not in keywords:
            self.refuses = []
        else:
            self.refuses = keywords['refuses']
            del(keywords['refuses'])
        Item.__init__(self, tag_and_parent, 'actor', **keywords)

    def exits(self, concept):
        "Return this Actor's current Room's exit dictionary."
        return concept.room_of(str(self)).exits

    def act(self, command_map, concept):
        'The default act method runs a script, if there is one.'
        if hasattr(self, 'script') and len(self.script) > 0:
            next_command = self.script.pop(0)
            if hasattr(self, 'script_loops'):
                self.script.append(next_command)
            next_command = next_command.split()
            return [self.do_command(next_command, command_map, concept)]
        return []

    def do_command(self, command_words, command_map, concept):
        'Return the Action that would result from the provided command.'
        if type(command_words) == types.StringType:
            command_words = command_words.split()
        head = command_words[0].lower()
        if not hasattr(command_map, head):
            raise StandardError('The command headed with "' + head +
             '" is defined in the discourse, but the routine to build an ' +
             'action from it is missing.')
        else:
            mapping = getattr(command_map, head)
            return mapping(str(self), command_words, concept)


class Door(Item):
    """An Item representing a doorway, portal, or passage between two places.

    Features of interest

    connects: list of two strings
        Each string is the tag of a Room; This Door connects the two."""

    def __init__(self, tag, **keywords):
        check_attributes(tag, ['connects'], ['parent', 'shared'], keywords)
        tag_and_parent = tag + ' of @cosmos'
        keywords['allowed'] = can.permit_any_item
        Item.__init__(self, tag_and_parent, 'door', **keywords)


class Room(Item):
    """An Item representing a physical location.

    Features that are particular to Rooms:

    exits: dictionary of string: string
        The key is a direction; the value is the tag of the Door or Room in 
        that direction.

    shared: list of strings
        Each string is the tag of a SharedThing; That Item is present in this
        room and all other rooms that list it.

    view: dictionary of string: (float, string)
        The key is the tag of a Room which is visible from this one; the tuple
        that is the value has the visibility of that room (a floating point
        number in (0, 1)) and a string which is used to generate a textual
        description of the direction of that room."""

    def __init__(self, tag, **keywords):
        check_attributes(tag, ['exits'], ['parent'], keywords)
        tag_and_parent = tag + ' of @cosmos'
        keywords['allowed'] = can.contain_permit_and_have_parts
        self.exits = keywords['exits']
        del(keywords['exits'])
        self.view = {}
        if 'view' in keywords:
            self.view = keywords['view']
            del(keywords['view'])
        if 'glow' not in keywords:
            keywords['glow'] = 1.0
        keywords['prominence'] = 1.0
        Item.__init__(self, tag_and_parent, 'room', **keywords)

    def exit(self, direction):
        'Return the Room or Door that lies in this direction, if there is one.'
        if direction in self.exits and self.exits[direction][0] == '@':
            # The key exists in the dictionary and the value begins with
            # '@', which means it is a tag. If someone writes a template
            # beginning with '@', this will fail.
            return self.exits[direction]
        else:
            return None


class Thing(Item):
    'An item that is not a room, has no concept, and cannot act.'

    def __init__(self, tag_and_parent, **keywords):
        check_attributes(tag_and_parent, [], ['exits', 'refuses', 'shared'],
                         keywords)
        Item.__init__(self, tag_and_parent, 'thing', **keywords)


class SharedThing(Thing):
    """A special sort of (large) Thing that appears in more than one room.

    Note that SharedThing is a subclass of Thing and shares the same category:
    example.thing is True for a SharedThing; there is no 'sharedthing' category.
    However, all SharedThings will have an attribute "sharedthing" that is set
    to True. Testing hasattr(item, 'sharedthing') will determine if the item is
    a SharedThing.

    SharedThing is provided to allow implementation of things like the sky, the
    sun, or a massive wall of the sort the United States has erected along the
    US/Mexico border. Because shared things are meant to represent these sorts
    of entities, they have an allowed expression that always returns False.
    Nothing can be placed in one, on one, through one, be part of one, or be 
    held by one. If it were possible, for instance, to place a sticker on a 
    massive border wall, this implementation would make the sticker visible in
    every room along the border, which makes no sense.

    A SharedThing does *not* have a shared feature. The Rooms that it is
    located in have shared features which are lists containing the tags of each
    shared item."""

    def __init__(self, tag_and_parent, **keywords):
        check_attributes(tag_and_parent, [], ['allowed', 'parent'], keywords)
        tag_and_parent = tag_and_parent + ' of @cosmos'
        keywords['allowed'] = can.not_have_items
        self.sharedthing = True
        Thing.__init__(self, tag_and_parent, **keywords)


class Substance(Item):
    'Includes powders and liquids; must be in a source or vessel.'

    def __init__(self, tag, **keywords):
        check_attributes(tag, [], ['exits', 'shared', 'refuses'], keywords)
        tag_and_parent = tag + ' of @cosmos'
        keywords['allowed'] = can.have_any_item
        Item.__init__(self, tag_and_parent, 'substance', **keywords)


########NEW FILE########
__FILENAME__ = joker
'Carry out directives such as save, restore, and quit.'

__author__ = 'Nick Montfort'
__copyright__ = 'Copyright 2011 Nick Montfort'
__license__ = 'ISC'
__version__ = '0.5.0.0'
__status__ = 'Development'

import os
import pickle
import re

import discourse_model
import microplanner
import reply_planner

MESSAGE = {
    'are': '[] are the [].',

    'world_missing_item': 'The item [] does not exist in the interactive ' + 
        "fiction's world.",

    'world_usage': 'The "world" debugging directive provides information ' + 
        'about items as represented in the simulated world, as opposed to ' + 
        'any one actor\'s concept of it: \n\n"world actions" shows the ' + 
        'actions from the world .\n"world tree" shows items in the world as ' +
        'they are hierarchically arranged.\n"world tree [item]" shows a ' + 
        'subtree rooted at a specific item.\n"world dir [item]" shows the ' + 
        'directory of attributes of a specific item.',

    'concept_missing_item': 'The item [] is not included in []\'s concept of ' +
        'the world.',

    'concept_usage': 'The "concept" debugging directive provides information ' +
        'about items as represented in an actor\'s concept: \n\n"concept ' + 
        '[actor] actions" shows the actions known to the actor.\n"concept ' + 
        '[actor] tree" shows the item tree of the actor\'s concept.\n' + 
        '"concept [actor] tree [item]" shows a subtree rooted at a specific ' + 
        'item.\n"concept [actor] dir [item]" shows the directory of ' + 
        'attributes of a specific item as it represented in that actor\'s ' + 
        'concept.\n\nPossible actors are: [].',

    'inputs': 'The number of [] input so far is [] in this session, [] in ' + 
        'this traversal.',

    'invalid_actor': 'The tag "[]" does not specify a valid actor. Possible ' +
        'actors are: [].',

    'is': '[] is the [].',

    'light_level': "Light level in focalizer's room or compartment: [].",

    'not_an_actor': 'It is only possible to set the [] to be one of the ' + 
        'following: [].',

    'nothing_happened': 'Nothing has happened yet.',

    'order_usage': 'Order can be set to chronicle, retrograde, or achrony.',

    'spin_report': 'Current spin: \n\n[]',

    'spin_usage': 'Type "spin" or "narrating" by itself to see the current ' +
        'spin. Add other arguments to view or set specific values, e.g., ' + 
        '"narrating time after" to set the time of narrating to after events.',

    'quitting': 'This ends the session.',

    'recounting': 'Recounting the specified actions.',

    'restarted': 'The session has been restarted.',

    'restore_error': 'The session could not be restored due to an error ' +
         'locating, opening, or reading the save file.',

    'restore_usage': 'To restore the game, type "restore [filename]", where ' +
        '[filename] consists of only letters, underscores, and numbers.',

    'restored': 'The session has been restored.',

    'save_error': 'The session could not be save due to an error ' +
         'opening or writing the save file.',

    'save_usage': 'To save the game, type "save [filename]", where ' + 
        '[filename] consists of only letters, underscores, and numbers.',

    'saved': 'The session has been saved.',

    'set': 'The [] has been set to [].',

    'speed_usage': 'The default speed can only be set to a number between 0 ' +
        'and 1.',

    'ticks': '[] ticks have passed.',

    'time': 'The narration is done as if it were happening [] the events.',

    'time_already': 'That is the existing setting for the time of narration.',

    'time_usage': 'Time of narration can be set to "before," "during," or ' + 
        '"after" events.',

    'time_words_usage': 'Time words can be turned on or off.',

    'undo_impossible': 'It is not possible to undo [] when the total number ' +
        'of commands is [].',

    'undo_usage': 'The directive "undo" can be used alone or with a number ' + 
        'of commands, for instance, "undo 3," to cancel the effects of one ' +
        'or more previous commands. To type a command to undo something ' + 
        'within the fictional world, use a similar word, such as "unfasten."',

    'undone': 'The command "[]" has been undone.',

    'uses': 'New spin, [], has been loaded.',

    'uses_usage': 'Use "narrating uses [filename]" to load spin from a file; ' +
        '"filename.py" must exist in the "spin" directory.',

    'wrap': '[]'}


class StartupError(Exception):
    'Exception occurring during session startup or in loading a spin.'
    def __init__(self, msg):
        self.msg = msg
        Exception.__init__(self, msg)


def load_file(file_name, required, defaults, module_type):
    """Loads either an interactive fiction or a spin file.

    Improved filename parsing thanks to Max Battcher."""
    dirname, _ = os.path.splitext(file_name)
    pieces = []
    while dirname:
        dirname, basename = os.path.split(dirname)
        if basename:
            pieces.append(basename)
        else:
            break
    pieces.reverse()
    module_name = '.'.join(pieces)
    try:
        mod = __import__(module_name, globals(), locals(), required, -1)
        for attr in required:
            if not hasattr(mod, attr):
                msg = ('This is not a complete fiction file: "' + attr +
                       '" is a required attribute, but the ' + module_type +
                       ' module ' + module_name + ' lacks it.')
                raise StartupError(msg)
        for (attr, default) in defaults.items():
            module = __import__(module_name, globals(), locals(), [attr])
            if not hasattr(module, attr):
                setattr(module, attr, default)
    except ImportError, err:
        msg = ('Unable to open '+ module_type + ' module "' + module_name +
               '" due to this error: ' + str(err))
        raise StartupError(msg)
    return module


def load_fiction(file_name, required, defaults):
    'Loads a fiction file.'
    fiction = load_file(file_name, required, defaults, 'interactive fiction')
    return fiction

def load_spin(existing_spin, spin_file):
    'Loads one spin file and returns an updated spin.'
    new_file = load_file(spin_file, [], discourse_model.SPIN_DEFAULTS, 'spin')
    if hasattr(new_file, 'spin'):
        existing_spin = update_spin(existing_spin, new_file.spin)
    return existing_spin

def update_spin(existing_spin, new_spin):
    focalizer = existing_spin['focalizer']
    commanded = existing_spin['commanded']
    for function in ['focalizer', 'commanded', 'narrator', 'narratee']:
        if function in new_spin and new_spin[function] == '@focalizer':
            new_spin[function] = focalizer
        if function in new_spin and new_spin[function] == '@commanded':
            new_spin[function] = commanded
    for level in ['token', 'sentence', 'paragraph']:
        if (level + '_filter' not in existing_spin or
            existing_spin[level + '_filter'] is None):
            existing_spin[level + '_filter'] = []
        if level + '_filter' in new_spin:
            new_filters = new_spin[level + '_filter']
            if new_filters is None:
                existing_spin[level + '_filter'] = []
            else:
                existing_spin[level + '_filter'] += new_filters
            del(new_spin[level + '_filter'])
# This is some of the machinery that would be used to update a concept if
# '@adventurer' or a similar key is in the spin file. Requires that "concept"
# is passed in as an argument.
##        for actor in concept:
#            if actor in new_spin:
#                for tag, feature, value in new_spin[actor]:
#                    setattr(concept[actor].item[tag], feature, value)
    existing_spin.update(new_spin)
    return existing_spin

def session_startup(version):
    'Return strings to be presented, centered, as a session begins.'
    startup_strings = [' __________', '/ Curveship', 'version ' + version]
    return startup_strings


def show_frontmatter(discourse):
    'Return a string with the title, headline, and credits.'
    frontmatter = ''
    if discourse.metadata['title'] is not None:
        frontmatter += discourse.metadata['title'].upper() + '\n'
    if 'headline' in discourse.metadata:
        frontmatter += discourse.metadata['headline'] + '\n'
    if 'people' in discourse.metadata:
        for (credit, person) in discourse.metadata['people']:
            frontmatter += discourse.typo.indentation + credit + ' '
            frontmatter += person + '\n'
    return frontmatter[:-1]


def show_prologue(data):
    'Return a string containing the prologue, if there is one.'
    if 'prologue' in data:
        return '\n\n'.join(data['prologue'])
    return ''


def report(kind, *params):
    'Prepare a report text using the MESSAGE dictionary.'
    parts = MESSAGE[kind].split('[]')
    string = parts.pop(0)
    params = list(params)
    while len(parts) > 0:
        string += str(params.pop(0))
        string += parts.pop(0)
    return '---\n' + string + '\n---'


def set_role(role, tokens, world, discourse):
    'Name or change a narrative role, such as focalizer.'
    if len(tokens) == 2:
        report_text = report('is', discourse.spin[role], role)
    elif len(tokens) > 2 and tokens[2] == 'none':
        discourse.spin[role] = None
        report_text = report('set', role, None)
    elif len(tokens) > 2 and tokens[2] in world.concept:
        discourse.spin[role] = tokens[2]
        report_text = report('set', role, tokens[2])
    else:
        all_actors = ', '.join(world.concept)
        report_text = report('not_an_actor', role, all_actors)
    return (report_text, world, discourse)


def wc_info(tokens, world_or_concept, world, discourse):
    'Reports on the world or a concept: tree, item info, actions.'
    report_text = ''
    if tokens[1] == 'actions':
        ids = world_or_concept.act.keys()
        if len(ids) == 0:
            report_text = report('nothing_happened')
        else:
            ids.sort()
            if len(tokens) > 2:
                first = len(ids) - int(tokens[2])
                ids = ids[first:]
            for action in [world_or_concept.act[i] for i in ids]:
                report_text += action.show()
            report_text = report('wrap', report_text[1:-1])
    elif tokens[1] in ['attrs', 'dir']:
        item = world_or_concept.item[tokens[2]]
        for attr in dir(item):
            if not callable(getattr(item, attr)) and not attr[:2] == '__':
                report_text += attr + ': ' + str(getattr(item, attr))
                report_text += '\n'
        report_text = report('wrap', report_text[:-1])
    elif tokens[1] == 'tree':
        root = '@cosmos'
        if len(tokens) > 2:
            root = tokens[2]
        tree_string = world_or_concept.show_descendants(root)[:-1]
        report_text = report('wrap', tree_string)
    return (report_text, None, world, discourse)


# The following functions map directives to replies, reports, changes to the
# world, and changes to the discourse.


def comment(_, world, discourse):
    'A comment has been entered. Just continue.'
    return ('', None, world, discourse)


def concept_info(tokens, world, discourse):
    "Describes items or actions based on a particular actor's concept."
    report_text = ''
    try:
        tag = tokens.pop(1)
        if tag not in world.concept:
            all_actors = ', '.join(world.concept)
            report_text = report('invalid_actor', tag, all_actors)
        else:
            world_or_concept = world.concept[tag]
            if (tokens[1] in ['attrs', 'dir', 'tree'] and len(tokens) > 2 and
                tokens[2] not in world_or_concept.item):
                report_text = report('concept_missing_item', tokens[2], tag)
            else:
                (report_text, _, __, ___) = wc_info(tokens, world_or_concept,
                                                       world, discourse)
    except IndexError:
        pass
    if report_text == '':
        all_actors = ', '.join(world.concept)
        report_text = report('concept_usage', all_actors)
    return (report_text, None, world, discourse)


def count_commands(_, world, discourse):
    'Returns a report on the number of commands issued so far.'
    session, traversal = discourse.input_list.count_commands()
    report_text = report('inputs', 'commands', session, traversal)
    return (report_text, None, world, discourse)


def count_directives(_, world, discourse):
    'Return a report on the number of directives issues so far.'
    session, traversal = discourse.input_list.count_directives()
    report_text = report('inputs', 'directives', session, traversal)
    return (report_text, None, world, discourse)


def count_unrecognized(_, world, discourse):
    'Returns a report on the number of unrecognized inputs so far.'
    session, traversal = discourse.input_list.count_unrecognized()
    report_text = report('inputs', 'unrecognized strings', session, traversal)
    return (report_text, None, world, discourse)


def exits(_, world, discourse):
    "Lists the exits from the focalizer's current room."
    focalizer = discourse.spin['focalizer']
    exit_string = ""
    for (direction, room) in world.room_of(focalizer).exits.items():
        exit_string += direction + ' -> ' + room + '\n'
    report_text = report('are', exit_string,
                         "the exits from the focalizer's current room")
    return (report_text, None, world, discourse)


def inputs(tokens, world, discourse):
    'Returns a report listing all requested inputs.'
    if len(tokens) == 1:
        (how_many, _) = discourse.input_list.total()
    else:
        how_many = int(tokens[1])
    report_text = report('wrap', discourse.input_list.show(how_many))
    return (report_text, None, world, discourse)


def light(_, world, discourse):
    "Returns a report on the focalizer's compartment's light level."
    focalizer = discourse.spin['focalizer']
    report_text = report('light_level', world.light_level(focalizer))
    return (report_text, None, world, discourse)


def narrating_commanded(tokens, world, discourse):
    'Changes the commanded actor.'
    return set_role('commanded', tokens, world, discourse)


def narrating_dynamic(tokens, world, discourse):
    'Changes whether the spin is dynamic.'
    if len(tokens) == 2 or tokens[2] == 'on':
        discourse.spin['dynamic'] = True
    else:
        discourse.spin['dynamic'] = False
    setting = ('static', '(potentially) dynamic')[discourse.spin['progressive']]
    report_text = report('set', 'spin', setting)
    return (report_text, world, discourse)


def narrating_focalizer(tokens, world, discourse):
    'Changes the focalizing actor.'
    return set_role('focalizer', tokens, world, discourse)


def narrating_narratee(tokens, world, discourse):
    'Changes which actor (if any) is the narratee.'
    return set_role('narratee', tokens, world, discourse)


def narrating_narrator(tokens, world, discourse):
    'Changes which actor (if any) is the narrator.'
    return set_role('narrator', tokens, world, discourse)


def narrating_order(tokens, world, discourse):
    'Changes the order.'
    report_text = report('order_usage')
    if len(tokens) == 2:
        report_text = report('is', discourse.spin['order'].capitalize(),
                             'order (the method of ordering events)')
    if len(tokens) > 2:
        report_text = report('set', 'order', tokens[2])
        if tokens[2] in ['chronicle', 'retrograde', 'achrony', 'analepsis',
                         'syllepsis']:
            discourse.spin['order'] = tokens[2]
    return (report_text, world, discourse)


def narrating_perfect(tokens, world, discourse):
    'Changes whether narration is in the perfect by default.'
    if len(tokens) == 2 or tokens[2] == 'on':
        discourse.spin['perfect'] = True
    else:
        discourse.spin['perfect'] = False
    setting = 'default to ' + ('off', 'on')[discourse.spin['perfect']]
    report_text = report('set', 'perfect aspect', setting)
    return (report_text, world, discourse)


def narrating_player(tokens, world, discourse):
    'Changes the player character (both focalizer and commanded).'
    (report1, world, discourse) = set_role('commanded', tokens, world,
                                           discourse)
    (report2, world, discourse) = set_role('focalizer', tokens, world,
                                           discourse)
    return (report1 + report2, world, discourse)


def narrating_progressive(tokens, world, discourse):
    'Changes whether narration is in the progressive by default.'
    if len(tokens) == 2 or tokens[2] == 'on':
        discourse.spin['progressive'] = True
    else:
        discourse.spin['progressive'] = False
    setting = 'default to ' + ('off', 'on')[discourse.spin['progressive']]
    report_text = report('set', 'progressive aspect', setting)
    return (report_text, world, discourse)


def narrating_speed(tokens, world, discourse):
    'Changes the default speed of narration.'
    report_text = report('speed_usage')
    if len(tokens) == 2:
        report_text = report('is', discourse.spin['speed'], 'default speed')
    else:
        number = float(''.join(tokens[2:]))
        if number >= 0 and number <= 10:
            discourse.spin['speed'] = number
            report_text = report('set', 'default speed', number)
    return (report_text, world, discourse)


def narrating_time(tokens, world, discourse):
    "Changes the narrator's position in time relative to events."
    report_text = report('time_usage')
    new_value = None
    if len(tokens) == 2:
        report_text = report('time', discourse.spin['time'])
    elif len(tokens) > 2:
        if tokens[2] in ['before', 'previous', 'anterior', 'earlier']:
            new_value = 'before'
        elif tokens[2] in ['during', 'simultaneous']:
            new_value = 'during'
        elif tokens[2] in ['after', 'later', 'subsequent', 'posterior']:
            new_value = 'after'
        if new_value is not None:
            if new_value == discourse.spin['time']:
                report_text = report('time_already')
            else:
                discourse.spin['time'] = new_value
                report_text = report('set', 'time of narrating', new_value)
    return (report_text, world, discourse)


def narrating_timewords(tokens, world, discourse):
    'Turns time_words on or off.'
    if len(tokens) == 2 or tokens[2] == 'on':
        discourse.spin['time_words'] = True
    else:
        discourse.spin['time_words'] = False
    setting = ('off', 'on')[discourse.spin['time_words']]
    report_text = report('set', 'use of time words', setting)
    return (report_text, world, discourse)


def narrating_uses(tokens, world, discourse):
    'Loads a new spin (parameters for telling) from a file.'
    report_text = report('uses_usage')
    if len(tokens) > 2 and re.match('[a-zA-Z_0-9]+$', tokens[1]):
        spin_file = 'spin/' + tokens[2] + '.py'
        try:
            new_spin = load_spin(discourse.spin, spin_file)
            discourse.spin.update(new_spin)
            report_text = report('uses', tokens[2])
        except StartupError, err:
            report_text = str(err) + '. ' + report('uses_usage')
    return (report_text, world, discourse)


def narrating(tokens, world, discourse):
    'Returns a report describing the current spin.'
    report_text = report('spin_usage')
    if len(tokens) < 2:
        pairs = discourse.spin.items()
        pairs.sort()
        longest = max([len(i) for (i, _) in pairs])
        string = ''
        for (key, value) in pairs:
            string += (longest - len(key) + 1) * ' '
            string += key + '  ' + str(value) + '\n'
        report_text = report('spin_report', string[:-1])
    elif 'narrating_'+tokens[1] in globals():
        (report_text, _,
         __) = globals()['narrating_' + tokens[1]](tokens, world, discourse)
    return (report_text, None, world, discourse)


def prologue(_, world, discourse):
    'Returns a reply containing the prologue.'
    reply_text = report('wrap', show_prologue(discourse.metadata))
    return (reply_text, None, world, discourse)


def recount(tokens, world, discourse):
    'Returns a report and a reply with narration of previous events.'
    reply_text = None
    if len(world.concept[discourse.spin['focalizer']].act) == 0:
        report_text = report('nothing_happened')
    else:
        report_text = report('recounting')
        concept = world.concept[discourse.spin['focalizer']]
        ids = concept.act.keys()
        ids.sort()
        start = ids[0]
        end = ids[-1]
        if len(tokens) >= 2:
            start = int(tokens[1])
        if len(tokens) == 3:
            end = int(tokens[2])
        recount_ids = []
        current = start
        while current <= end:
            if current in concept.act:
                recount_ids.append(current)
            current = current + 1
        original_time = discourse.spin['time']
        discourse.spin['time'] = 'after'
        reply_plan = reply_planner.plan(recount_ids, concept, discourse)
        section = microplanner.specify(reply_plan, concept, discourse)
        reply_text = section.realize(concept, discourse)
        discourse.spin['time'] = original_time
    return (report_text, reply_text, world, discourse)


def restart(_, world, discourse):
    'Restarts the game and emit an appropriate report.'
    discourse.input_list.reset()
    world.reset()
    return (report('restarted'), None, world, discourse)


def restore(tokens, world, discourse):
    'Restores the game and emit an appropriate report.'
    if len(tokens) > 1 and re.match('[a-zA-Z_0-9]+$', tokens[1]):
        try:
            file_name = 'save/' + tokens[1] + '.ses'
            restore_file = file(file_name, 'r')
            (world, discourse) = pickle.load(restore_file)
            restore_file.close()
            report_text = report('restored')
        except IOError:
            report_text = report('restore_error')
    else:
        report_text = report('restore_usage')
    return (report_text, None, world, discourse)


def room_name(_, world, discourse):
    "Give the name of the focalizer's current room."
    focalizer = discourse.spin['focalizer']
    room = str(world.room_of(focalizer))
    report_text = report('is', room, "focalizer's current room")
    return (report_text, None, world, discourse)


def save(tokens, world, discourse):
    'Save the fiction/game/world and emit an appropriate report.'
    if len(tokens) > 1 and re.match('[a-z_0-9]+$', tokens[1]):
        try:
            file_name = 'save/' + tokens[1] + '.ses'
            save_file = file(file_name, 'w')
            pickle.dump((world, discourse), save_file)
            save_file.close()
            report_text = report('saved')
        except IOError:
            report_text = report('save_error')   
    else:
        report_text = report('save_usage')
    return (report_text, None, world, discourse)


def terminate(_, world, discourse):
    """Quits the game after emitting an appropriate report.

    Since 'quit' is a builtin function, this one is called 'terminate.'"""
    world.running = False
    return (report('quitting'), None, world, discourse)


def ticks(_, world, discourse):
    'Returns a report on how many ticks (time units) have passed.'
    return (report('ticks', world.ticks), None, world, discourse)


def title(_, world, discourse):
    'Returns a reply containing the frontmatter.'
    reply_text = report('wrap', show_frontmatter(discourse))
    return (reply_text, None, world, discourse)


def undo(tokens, world, discourse):
    'Undoes a turn and emits an appropriate report.'
    (_, commands) = discourse.input_list.count_commands()
    to_undo = 1
    try:
        if len(tokens) > 1:
            to_undo = int(tokens[1])
            if to_undo < 1:
                raise ValueError
        if to_undo > commands:
            if to_undo == 1:
                to_undo = 'a command'
            else:
                to_undo = str(to_undo) + ' commands'
            report_text = report('undo_impossible', to_undo, commands)
        else:
            report_text = ''
            undone = 0
            while undone < to_undo:
                command_to_undo = discourse.input_list.latest_command()
                report_text += report('undone', str(command_to_undo))
                discourse.input_list.undo()
                world.undo(command_to_undo.caused)
                undone += 1
    except ValueError:
        report_text = report('undo_usage')
    return (report_text, None, world, discourse)


def world_info(tokens, world, discourse):
    "Describes the world's items or actions."
    report_text = ''
    try:
        world_or_concept = world
        if (tokens[1] in ['attrs', 'dir', 'tree'] and len(tokens) > 2 and
            tokens[2] not in world.item):
            report_text = report('world_missing_item', tokens[2])
        else:
            (report_text, _, __, ___) = wc_info(tokens, world_or_concept,
                                                   world, discourse)
    except IndexError:
        pass
    if report_text == '':
        report_text = report('world_usage')
    return (report_text, None, world, discourse)


def joke(tokens, world, discourse):
    'Handles directives -- inputs that deal with the program state.'
    head = tokens[0].lower()
    if head in globals():
        (report_text, reply_text, world,
         discourse) = globals()[head](tokens, world, discourse)
    else:
        raise StandardError('The directive "' + head + '" is defined in the ' +
         'discourse, but the corresponding routine in the Joker is missing.')
    texts = (report_text, reply_text)
    return (texts, world, discourse)

########NEW FILE########
__FILENAME__ = microplanner
'Text planning: Set tense and referring expressions, lexicalize.'

__author__ = 'Nick Montfort'
__copyright__ = 'Copyright 2011 Nick Montfort'
__license__ = 'ISC'
__version__ = '0.5.0.0'
__status__ = 'Development'

import random
import re
import types

import reply_planner
from realizer import Section, Paragraph, Heading

def has_final(node):
    final = False
    if (hasattr(node, 'info') and hasattr(node.info, 'final') and 
        node.info.final):
        final = True
    elif hasattr(node, 'children'):
        for child in node.children:
            final = final or has_final(child)
    return final


def specify(reply_plan, concept, discourse):
    'Main microplanner invocation, returns blocks wrapped up as a section.'
    blocks = micro(reply_plan, concept, discourse, discourse.min,
                   discourse.max)
    if has_final(reply_plan):
        blocks += [Heading('The End')]
    return Section(blocks)


def determine_tense(event, ref, speech):
    "Returns a tense using Hans Reichenbach's system (1947)."
    if event < ref:
        tense_er = 'anterior'
    elif event == ref:
        tense_er = 'simple'
    else:
        tense_er = 'posterior'
    if ref < speech:
        tense_rs = 'past'
    elif ref == speech:
        tense_rs = 'present'
    else:
        tense_rs = 'future'
    return tense_er, tense_rs


def micro(reply_node, concept, discourse, ref, speech):
    'Does microplanning based on given reference and speech times or rules.'
    blocks = []
    if not isinstance(reply_node, reply_planner.Internal):
        if reply_node.category in ['action', 'room', 'ok']:
            if ref == discourse.right_before:
                ref = reply_node.event - 1
            if ref == discourse.follow:
                ref = reply_node.event
            if ref == discourse.right_after:
                ref = reply_node.event + 1
            if speech is discourse.follow:
                speech = reply_node.event
            e_r, r_s = determine_tense(reply_node.event, ref, speech)
        if reply_node.category == 'action':
            blocks = narrate_action(reply_node, concept, discourse, e_r, r_s)
        elif reply_node.category == 'room':
            blocks = name_room(reply_node, e_r, r_s, concept, discourse)
        elif reply_node.category == 'commentary':
            para = Paragraph(discourse.spin['template_filter'],
                             [reply_node.info])
            para.set(discourse.spin['narrator'], discourse.spin['narratee'],
                     'simple', 'present', discourse.spin['progressive'])
            blocks = [para]
        elif reply_node.category == 'ok':
            blocks = acknowledge(e_r, r_s, concept, discourse,
                                 discourse.spin['focalizer'])
    else:
        for child in reply_node.children:
            blocks += micro(child, concept, discourse, reply_node.ref,
                            reply_node.speech)
    return blocks


def acknowledge(tense_er, tense_rs, _, discourse, __):
    'Produces a rather empty utterance when there is nothing to represent.'
    template = 'nothing special [happen/1/v]'
    para = Paragraph(discourse.spin['template_filter'], [template])
    para.set(discourse.spin['narrator'], discourse.spin['narratee'],
             tense_er, tense_rs, discourse.spin['progressive'])
    return [para]


def name_room(node, tense_er, tense_rs, concept_now, discourse):
    'States the name of the room.'
    agent, time = node.info.agent, node.info.end
    concept = concept_now.copy_at(time)
    room = concept.room_of(agent)
    template = '[' + agent + '/s] [is/v] in ' + room.noun_phrase(discourse)
    para = Paragraph(discourse.spin['template_filter'], [template], time)
    para.set(discourse.spin['narrator'], discourse.spin['narratee'], tense_er,
              tense_rs, discourse.spin['progressive'])
    blocks = [para]
    return blocks


def select(string_or_list):
    'Return a string, either the one passed or a random element from a list.'
    if type(string_or_list) == types.StringType:
        return string_or_list
    else:
        return random.choice(string_or_list)


def get_representation(action, discourse):
    'Returns the appropriate representation of an action.'
    verb = action.verb
    if verb in discourse.verb_representation:
        template = select(discourse.verb_representation[verb])
    else:
        template = None
        if hasattr(action, 'template'):
            template = select(action.template)
        for (rule, possible_template) in discourse.action_templates:
            if action.match_string(rule):
                template = select(possible_template)
                break
        if template is None:
            template = '[agent/s] [' + verb + '/v]'
            if hasattr(action, 'direct') or hasattr(action, 'target'):
                template = '[agent/s] [' + verb + '/v] [direct/o]'
            if hasattr(action, 'indirect') or hasattr(action, 'new_parent'):
                template = ('<<<ERROR:' + str(verb) +
                            ' has an indirect object but no template.>>>')
    return template


def failed(template, reasons, discourse):
    'Returns a template representing a failed action, explaining the failure.'
    if re.match('\[agent/s\]', template):
        verb_match = re.search('\[(\w+)/v\]', template)
        template = re.sub('\[(\w+)/v\]', verb_match.group(1), template)
        new_part = '[agent/s] [is/v] unable to'
        template = re.sub('\[agent/s\]', new_part, template)
    else:
        template = "impossible"
    first_reason = reasons[0]
    explanation = discourse.failure_to_english[first_reason[0]]
    if first_reason[0] == 'modify_to_different':
        (_, tag, feature, value) = first_reason
        explanation = ('[' + tag + '/s] [is/v] ' +
                       discourse.feature_to_english[feature](value) +
                       ' to begin with')
    if first_reason[0] == 'has_value':
        (_, tag, feature, value) = first_reason
        explanation = ('[' + tag + '/s] [is/not/v] ' +
                       discourse.feature_to_english[feature](value))
    if len(explanation) > 0:
        template += ' because ' + explanation
    return template


def refused(template, refusal):
    'Returns a template explaining a refused action.'
    if re.match('\[agent/s\]', template):
        verb_match = re.search('\[(\w+)/v\]', template)
        template = re.sub('\[(\w+)/v\]', verb_match.group(1), template)
        new_part = '[agent/s] [decide/v] not to'
        template += ' because ' + refusal
        template = re.sub('\[agent/s\]', new_part, template)
    else:
        template = "impossible"
    return template


def replace(node, label, attrs, template):
    'Return a template with label replaced if any attr is present.'
    for attr in attrs:
        if hasattr(node, attr):
            label = '\[' + label
            tag = '[' + getattr(node, attr)
            template = re.sub(label, tag, template)
    return template


def substitute_tags(template, info):
    """Returns a modified template with tags for agent and all objects.

    If certain passive constructions are used in the representations above,
    the direct (more rarely, even the indirect) objects can be subjects."""
    template = replace(info, 'agent', ['agent'], template)
    template = replace(info, 'direct', ['direct', 'target'], template)
    template = replace(info, 'indirect', ['indirect', 'new_parent'], template)
    return template


def narrate_action(node, concept_now, discourse, tense_er, tense_rs):
    'Return blocks that narrate the action in the node.'
    time = node.info.start
    sentence = get_representation(node.info, discourse)
    if len(node.info.failed) > 0:
        sentence = failed(sentence, node.info.failed, discourse)
    elif node.info.refusal is not None:
        sentence = refused(sentence, node.info.refusal)
    if '[old_link]' in sentence:
        old_link = discourse.link_to_english[node.info.old_link][0]
        sentence = re.sub('\[old_link\]', old_link, sentence)
    if '[old_parent' in sentence:
        sentence = re.sub('\[old_parent', '[' + node.info.old_parent, sentence)
    if '[direction]' in sentence:
        sentence = re.sub('\[direction\]', node.info.direction, sentence)
    if '[utterance]' in sentence:
        sentence = re.sub('\[utterance\]', node.info.utterance.lower(),
                          sentence)
    sentence = substitute_tags(sentence, node.info)
    strings = [sentence]
    if len(node.info.failed) == 0 and node.info.refusal is None:
        if hasattr(node.info, 'before'):
            strings = [node.info.before] + strings
        if hasattr(node.info, 'after'):
            strings += [node.info.after]
    para = Paragraph(discourse.spin['template_filter'], strings, time)
    para.set(discourse.spin['narrator'], discourse.spin['narratee'], tense_er,
             tense_rs, discourse.spin['progressive'])
    blocks = [para]
    time = node.info.end
    concept = concept_now.copy_at(time)
    if (node.info.sense and node.info.agent == discourse.spin['focalizer'] and
        len(node.info.failed) == 0 and node.info.refusal is None):
        if node.info.modality == 'sight':
            new_blocks = describe(node.info.direct, tense_er, tense_rs,
                node.speed, concept, discourse, node.info.agent,
                node.info.start)
            blocks += new_blocks
        elif node.info.modality in ['touch', 'hearing', 'smell', 'taste']:
            sense = getattr(concept.item[node.info.direct], node.info.modality)
            if not (sense == ['']):
                sense[0] = ('[*/s] [' +
                            discourse.sense_verb[node.info.modality] + '/v] ' +
                            sense[0])
                para = Paragraph(discourse.spin['template_filter'], sense, time)
                para.set(discourse.spin['narrator'],
                         discourse.spin['narratee'], tense_er, tense_rs,
                         discourse.spin['progressive'])
                blocks += [para]
    blocks = prepend_any_time_words(blocks, node, discourse.spin['time_words'])
    return blocks


def prepend_any_time_words(blocks, node, use_time_words):
    'Add the appropirate time phrase at the start of the first sentence.'
    if use_time_words and node.prior is not None:
        time_words = 'then,'
        if node.event == node.prior:
            time_words = 'meanwhile,'
        elif node.event < node.prior:
            time_words = random.choice(['before that,', 'previously,',
                                        'previous to that,', 'that was after',
                                        'earlier,', 'just beforehand,',
                                        'a moment before'])
        if (len(blocks) > 0 and hasattr(blocks[0], 'sentences') and
            len(blocks[0].sentences) > 0):
            blocks[0].sentences[0].prepend(time_words)
    return blocks

def slots(tag_list, role='o'):
    slot_list = []
    for tag in tag_list:
       slot_list.append('[' + tag + '/' + role + ']')
    return slot_list

def describe(tag, tense_er, tense_rs, speed, concept, discourse, sensor, time):
    'Return blocks of generated text describing the item.'

    # NOTE: This is quite a mess and could use to be broken up and streamlined.
    children = {'in':[], 'of':[], 'on':[], 'part_of':[], 'through':[]}
    child_sentences = []
    to_exclude = [sensor]
    item = concept.item[tag]
    if item == concept.compartment_of(sensor):
        to_exclude += concept.descendants(sensor)
    to_mention = [i for i in concept.descendants(tag, stop='opaque') 
                          if i not in to_exclude]
    for desc_tag in to_mention:
        desc_item = concept.item[desc_tag]
        if desc_item.mention:
            if desc_item.parent == str(item):
                children[desc_item.link].append(desc_tag)
            elif desc_item.parent == '@cosmos':
                children['in'].append(desc_tag)
            else:
                link = desc_item.link
                link_name = discourse.link_to_english[link][0]
                child_sentences.append('[' + desc_tag + '/s] [is/v]' + 
                                   link_name + ' [' + desc_item.parent + '/o]')
    description_block = []
    current_sentences = []
    for string in item.sight + ['']:
        if not string == '':
            current_sentences.append(re.sub('\[\*', '[' + sensor, string))
        elif len(current_sentences) > 0:
            description_block += [Paragraph(discourse.spin['template_filter'],
                                            current_sentences, time)]
            current_sentences = []
    for paragraph in description_block:
        paragraph.set(discourse.spin['narrator'], discourse.spin['narratee'],
                      tense_er, tense_rs, discourse.spin['progressive'])
    heading = None
    if (item.room and speed < 0.8 and concept.room_of(sensor) == item):
        if ('room_name_headings' not in discourse.spin or
            discourse.spin['room_name_headings']):
            room_name = item.noun_phrase(discourse, entire=False)
            heading = room_name[:1].upper() + room_name[1:]
    contents = None
    if (len(children['in']) + len(children['of']) +
        len(children['on'])) > 0:
        contents = '[' + sensor + '/s] [see/v] '
        parent = '[' + tag + '/s]'
        if item.room:
            contents += discourse.list_phrases(slots(children['in']))
        else:
            contents += 'that '
            if item.actor:
                contents += parent
                if len(children['of']) > 0:
                    contents += (' [possess/v] ' +
                                 discourse.list_phrases(slots(children['of'])))
                    if len(children['on']) > 0:
                        contents += ' and'
                if len(children['on']) > 0:
                    contents += (' [wear/ing/v] ' + 
                                 discourse.list_phrases(slots(children['on'],
                                                        role='s')))
            elif len(children['on']) > 0:
                contents += (discourse.list_phrases(slots(children['on'],
                                      role='s')) + ' [is/v] on ' + parent)
                if len(children['in']) > 0:
                    contents += (', which [contain/v] ' +
                                  discourse.list_phrases(slots(children['in'],
                                                         role='s')))
            elif len(children['in']) > 0:
                contents += (parent + ' [contain/v] ' +
                             discourse.list_phrases(slots(children['in'])))
        contents = [contents] + child_sentences
    listed = []
    in_directions = []
    if item.room:
        for direction in item.exits:
            if (concept.has('room', item.exits[direction]) and
                item.exits[direction] not in listed and
                discourse.spin['known_directions']):
                leads_to = concept.item[item.exits[direction]]
                in_directions += [leads_to.noun_phrase(discourse) +
                                  ' [is/1/v] toward the ' + direction]
                listed.append(item.exits[direction])
        far_strings = []
        for far_room in item.view:
            vdir = item.view[far_room][1]
            far_items = []
            if far_room in concept.item:
                for (_, child) in concept.item[far_room].children:
                    if child in concept.item:
                        far_items.append('[' + child + '/o]')
                if len(far_items) > 0:
                    far_line = (vdir + ', ' +
                                discourse.list_phrases(far_items))
                    far_strings.append(far_line)
        if len(far_strings) > 0:
            far_st = ('from [here], [' + sensor + '/s] [is/v] able to see: ' +
                     discourse.list_phrases(far_strings, delimiter=';'))
            in_directions += [far_st]
    blocks = []
    if heading is not None:
        blocks += [Heading(heading)]
    blocks += description_block
    if contents is not None:
        para = Paragraph(discourse.spin['template_filter'], contents, time)
        para.set(discourse.spin['narrator'], discourse.spin['narratee'],
                 tense_er, tense_rs, discourse.spin['progressive'])
        blocks += [para]
    if len(in_directions) > 0 and speed < 0.8:
        far_off = Paragraph(discourse.spin['template_filter'], in_directions,
                            time)
        far_off.set(discourse.spin['narrator'], discourse.spin['narratee'],
                    tense_er, tense_rs, discourse.spin['progressive'])
        blocks += [far_off]
    return blocks


########NEW FILE########
__FILENAME__ = preparer
'Tokenize input text for the Recognizer.'

__author__ = 'Nick Montfort'
__copyright__ = 'Copyright 2011 Nick Montfort'
__license__ = 'ISC'
__version__ = '0.5.0.0'
__status__ = 'Development'

import sys
import re
try:
    import readline
except ImportError:
    pass

import input_model

def prepare(separator, prompt='', in_stream=sys.stdin, out_stream=sys.stdout):
    """Read a string from the input string and return it tokenized.

    Andrew Plotkin fixed this so that up arrow fetches the previous command."""
    if (hasattr(in_stream, 'isatty') and in_stream.isatty()):
        input_string = raw_input(prompt)
    else:
        out_stream.write(prompt)
        input_string = in_stream.readline()
        if input_string == '':
            # Empty string indicates end of the input file.
            # (A blank input line would look like '\n'.)
            raise EOFError()
        out_stream.write(input_string)
    return tokenize(input_string, separator)

def tokenize(input_string, separator):
    'Returns tokenized and slightly reformatted text.'
    input_string = re.sub('\s*$', '', input_string)
    new_text = input_string
    new_text = re.sub(' *([\.\?\!\&\(\)\-\;\:\,]) *', r' \1 ', new_text)
    new_text = re.sub('^[ \t]+', '', new_text)
    new_text = re.sub('[ \t\n]+$', '', new_text)
    new_text = re.sub('[ \t]+', ' ', new_text)
    new_text = re.sub(" *' *", " '", new_text)

    new_text = re.sub(" *' *", " '", new_text)
    tokens = new_text.lower().split()
    while len(tokens) > 0 and tokens[0] in separator:
        tokens.pop(0)
    while len(tokens) > 0 and tokens[-1] in separator:
        tokens.pop()
    user_input = input_model.RichInput(input_string, tokens)
    return user_input

if __name__ == "__main__":
    TEST_INPUT = prepare()
    print TEST_INPUT.tokens


########NEW FILE########
__FILENAME__ = presenter
'Format and display the output text.'

__author__ = 'Nick Montfort'
__copyright__ = 'Copyright 2011 Nick Montfort'
__license__ = 'ISC'
__version__ = '0.5.0.0'
__status__ = 'Development'

import os
import re
import struct

def ioctl_term_size(filed):
    'Attempt to find terminal dimensions using an IO Control system call.'
    try:
        import fcntl, termios
        packed = fcntl.ioctl(filed, termios.TIOCGWINSZ, '1234')
        rows_cols = struct.unpack('hh', packed)
    except ImportError:
        return None
    if rows_cols == (0, 0):
        return None
    return rows_cols


def terminal_size():
    """Determine the terminal size or set a default size if that fails.
    
    From Chuck Blake's code, http://pdos.csail.mit.edu/~cblake/cls/cls.py
    Modifications by Doug Orleans to allow Curveship to run in GNU Emacs."""
    rows_cols = ioctl_term_size(0) or ioctl_term_size(1) or ioctl_term_size(2)
    if not rows_cols:
        try:
            filed = os.open(os.ctermid(), os.O_RDONLY)
            rows_cols = ioctl_term_size(filed)
            os.close(filed)
        except AttributeError:
            pass
    if not rows_cols:
        # Some shells may set these environment variables.
        rows_cols = (os.environ.get('LINES', 25), os.environ.get('COLUMNS', 80))
    return int(rows_cols[1]), int(rows_cols[0]) # Reverses it to cols, rows.


def _break_words(string, char_limit):
    'Lineate the string based on the passed-in character limit.'
    if len(string) <= char_limit:
        next_line = string
        string = ''
    elif '\n' in string[0:char_limit]:
        first_newline = string.index('\n')
        next_line = string[0:first_newline]
        string = string[(first_newline + 1):]
    elif ' ' not in string[0:char_limit]:
        next_line = string[0:char_limit]
        string = string[char_limit:]
    else:
        last_space = string[0:char_limit].rindex(' ')
        next_line = string[0:last_space]
        string = string[(last_space + 1):]
    return (next_line, string)


def present(string, out_streams, pre='', post='\n\n'):
    'Print the string, broken into lines, to the output streams.'
    if len(string) == 0:
        return
    if string[-1:] == '\n':
        post = re.sub('^[ \t]+', '', post)
    string = pre + string + post
    while len(string) > 0:
        (cols, _) = terminal_size()
        (next_line, string) = _break_words(string, cols)
        out_streams.write(next_line)
        if len(string) > 0:
            out_streams.write('\n')
    out_streams.write(string)


def center(string, out_streams, pre='', post='\n'):
    'Center the output and print it to the output streams.'
    string = pre + string + post
    (cols, _) = terminal_size()
    while len(string) > 0:
        (next_line, string) = _break_words(string, cols)
        while len(next_line) > 0 and next_line[0] == '\n':
            out_streams.write('\n')
            next_line = next_line[1:]
        spaces = ''
        i = 1
        while i <= (cols - len(next_line))/2:
            spaces += ' '
            i += 1
        out_streams.write(' ' + spaces + next_line)
        if len(string) > 0:
            out_streams.write('\n')


########NEW FILE########
__FILENAME__ = realizer
'Surface realization: Convert a fully specified section to a string.'

__author__ = 'Nick Montfort'
__copyright__ = 'Copyright 2011 Nick Montfort'
__license__ = 'ISC'
__version__ = '0.5.0.0'
__status__ = 'Development'

import re
import types
import irregular_verb

def apply_filter_list(filter_list, string):
    'Transforms the string by applying all filters in the list.'
    if filter_list is not None:
        for output_filter in filter_list:
            string = output_filter(string)
    return string


class Section(object):
    'Encapsulates blocks of text, each one a paragraph or heading.'

    def __init__(self, blocks):
        self.blocks = blocks

    def __str__(self):
        string = '\n<section>\n\n'
        for i in self.blocks:
            string += str(i) + '\n'
        return string + '</section>\n'

    def realize(self, concept, discourse):
        'Return a string realized from this, the concept, and the discourse.'
        string = ''
        previous = None
        for (i, block) in enumerate(self.blocks):
            last = (i == len(self.blocks) - 1)
            string += block.realize(previous, last, concept, discourse)
            previous = block
        return string


class Heading(object):
    'A normally one-line heading, e.g., for indicating the current room.'

    def __init__(self, string):
        self.line = string

    def __str__(self):
        return '<h>' + self.line + '</h>\n'

    def realize(self, previous, last, _, discourse):
        'Return a string realized from this, position info, and the discourse.'
        string = discourse.typo.format_heading(self.line, previous, last)
        return string


class Paragraph(object):
    'Unit of several sentences, realized with indentation and spacing.'

    def __init__(self, template_filter, strings, time=0):
        self.sentences = []
        for i in strings:
            self.sentences.append(Sentence(template_filter, i, time))

    def __eq__(self, pgraph):
        return self.sentences == pgraph.sentences

    def __ne__(self, pgraph):
        return not self.__eq__(pgraph)

    def __str__(self):
        string = ''
        for i in self.sentences:
            string += str(i)
        return '<p>' + string + '</p>\n'

    def merge(self, paragraph):
        "Add the argument's sentences to this paragraph."
        for i in paragraph.sentences:
            self.sentences.append(i)

    def set(self, narrator, narratee, tense_er, tense_rs, progressive):
        'Defines the generator settings for all the sentences.'
        for i in self.sentences:
            i.set(narrator, narratee, tense_er, tense_rs, progressive)

    def realize(self, previous, last, concept, discourse):
        'Return a string from this, position info, concept, and discourse.'
        string = ''
        capitalize = True
        for i in self.sentences:
            if hasattr(i, 'realize'):
                new_sentence = i.realize(concept, discourse)
                string += fix_orthography(new_sentence, capitalize) + ' '
                if len(new_sentence) > 0 and new_sentence[-1] == ',':
                    capitalize = False
                else:
                    capitalize = True
        string = apply_filter_list(discourse.spin['paragraph_filter'], string)
        string = string.strip()
        return discourse.typo.format_paragraph(string, previous, last)


class GeneratorSettings(object):
    'Five narrative/grammatical parameters important for realization.'

    def __init__(self, narrator, narratee, tense_er, tense_rs, progressive):
        self.narrator = narrator
        self.narratee = narratee
        self.tense_er = tense_er
        self.tense_rs = tense_rs
        self.progressive = progressive


class Sentence(object):
    'Holds a template with slots and other necessary parameters.'

    def __init__(self, t_filter, string, time):
        string = re.sub(']', '] ', string)
        string = apply_filter_list(t_filter, string)
        self.parts = []
        self.settings = None
        for token in string.split():
            noun_kws = {}
            if token[0] == '[' and token[-1] == ']':
                slot = token[1:-1].lower()
                if slot[-2:] == "'s":
                    self.parts.append(Pronoun(slot[:-2], Pronoun.possessive,
                                      time))
                else:
                    bits = slot.split('/') # A slot has different bits.
                    if 'pro' in bits:
                        noun_kws['pronominalize'] = True
                        bits.remove('pro')
                    kind = bits.pop()
                    if kind in ['here', 'now', 'this', 'these']:
                        self.parts.append(Deictic(kind))
                    elif kind in ['begin-caps', 'end-caps']:
                        self.parts.append(token)
                    else:
                        head = bits.pop(0)
                        if kind == 's':
                            self.parts.append(Noun(head, Noun.subject, bits,
                                                   time, **noun_kws))
                        elif kind == 'o':
                            self.parts.append(Noun(head, Noun.object, bits,
                                                   time, **noun_kws))
                        elif kind == 'a':
                            self.parts.append(Adjective(bits[-1], head, time))
                        elif kind == 'v':
                            verb_kws = {}
                            verb_kws['negated'] = False
                            if 'do' in bits:
                                verb_kws['intensive'] = True
                            if 'not' in bits:
                                verb_kws['negated'] = True
                            if '1' in bits:
                                verb_kws['default_number'] = 'singular'
                            elif '2' in bits:
                                verb_kws['default_number'] = 'plural'
                            if 'ing' in bits:
                                verb_kws['progressive'] = True
                            if 'ed' in bits:
                                verb_kws['tense_er'] = 'anterior'
                            self.parts.append(Verb(head, time, **verb_kws))
            elif '_' in token:
                self.parts.append(NP(token))
            else:
                if token[:2] == '\\[':
                    token = token[1:]
                self.parts.append(token)

    def __eq__(self, sentence):
        return self.parts == sentence.parts

    def __ne__(self, sentence):
        return not self.__eq__(sentence)

    def __str__(self):
        string = ''
        for i in self.parts:
            string += str(i) + ' '
        if len(self.parts) > 0:
            string = string[0:-1]
        return '<s>' + string + '</s>'

    def set(self, narrator, narratee, tense_er, tense_rs, progressive):
        'Defines five grammatical/narrative settings needed to realize.'
        self.settings = GeneratorSettings(narrator, narratee, tense_er,
                                          tense_rs, progressive)

    def prepend(self, string):
        'Add this string to the beginning of the sentence.'
        self.parts = [string] + self.parts

    def realize(self, concept, discourse):
        'Return a string from this, a concept, and the discourse.'
        phrases = []
        all_caps = False
        subjects, tf = (), False
        for part in self.parts:
            more = ''
            if type(part) is types.StringType:
                if part == '[begin-caps]':
                    all_caps = True
                elif part == '[end-caps]':
                    all_caps = False
                else:
                    more = part
            else:
                (more, subjects, tf) = part.realize(concept, discourse,
                                                    self.settings, subjects, tf)
            if len(more) > 0:
                if all_caps:
                    more = more.upper()
                phrases.append(more)
        phrases = apply_filter_list(discourse.spin['sentence_filter'], phrases)
        string = ' '.join(phrases)
        string = re.sub('\( ', '(', string)
        string = re.sub(' \)', ')', string)
        return string.strip()
 

def fix_orthography(string, capitalize=True):
    'Capitalize (optionally) and punctuate the end of a sentence string.'

    string = string.strip()
    if len(string) == 0:
        return string
    else:
        if capitalize:
            string = string[0].upper() + string[1:]
    if (re.match('[a-zA-Z0-9]', string) and string[-1] not in list(',.!?;:')):
        string = string + '.'
    string = re.sub(' *\,', ',', string)
    string = re.sub(' *\;', ';', string)
    string = re.sub(' *\:', ':', string)
    string = re.sub('"\.$', '."', string)
    string = re.sub('"\,$', ',"', string)
    return string


class Word(object):
    'Base representation of a lexical element, not for instantiation.'

    def __init__(self, tag):
        self.tag = tag

    def __eq__(self, word):
        return str(self) == str(word)

    def __ne__(self, word):
        return not self.__eq__(word)

    def __str__(self):
        return self.tag

    def realize(self, _, __, ___, subjects, tf):
        'Return a string realized from the word.'
        return (self.tag, subjects, tf)


class Adjective(Word):
    'Adjective describing a feature of an item.'

    def __init__(self, tag, feature, time):
        self.feature = feature
        self.time = time
        Word.__init__(self, tag)

    def __str__(self):
        return 'A.' + self.tag + '.' + self.feature

    def realize(self, concept, discourse, _, subjects, tf):
        'Return a string realized from the word.'
        tag = self.tag
        if self.tag == '*':
            tag = discourse.spin['focalizer']
        value = getattr(concept.item_at(tag, self.time), self.feature)
        string = discourse.feature_to_english[self.feature](value)
        return (string, subjects, tf)


class NP(Word):
    'Noun phrase.'

    def __init__(self, string):
        if string[:1] == '_':
            string = string[1:]
        words = string.split('_')
        self.determiner = ''
        if words[0] in ['a', 'an', 'one', 'some', 'the', 'that', 'this']:
            self.determiner = words.pop(0)
        self.rest = words
        Word.__init__(self, words[-1])

    def __str__(self):
        return self.determiner + '_'.join(self.rest)

    def realize(self, _, discourse, __, subjects, tf):
        'Return a string realized from the word.'
        string = ''
        phrase = '_' + '_'.join(self.rest)
        if len(self.determiner) > 0:
            if phrase not in discourse.givens:
                string = self.determiner + ' '
            else:
                string = 'the '
        string += ' '.join(self.rest)
        if phrase not in discourse.givens:
            discourse.givens.add(phrase)
        return (string, subjects, tf)


class Noun(Word):
    'Noun describing an Item; may be pronominalized upon realization.'

    subject, object, possessive, reflexive = range(4)

    def __init__(self, tag, form, adjs, time, **keywords):
        self.form = form
        self.adjs = adjs
        self.pronominalize = False
        if 'pronominalize' in keywords:
            self.pronominalize = keywords['pronominalize']
        self.time = time
        Word.__init__(self, tag)

    def __str__(self):
        return 'N.' + self.tag + '.' + 'SOPR'[self.form]

    def realize(self, concept, discourse, settings, subjects, tf):
        'Return a string realized from the word.'
        tag = self.tag
        if self.tag == '*':
            tag = discourse.spin['focalizer']
        if tag in subjects and self.form == self.object:
            self.form = self.reflexive
            self.pronominalize = True
        elif tag in [settings.narrator, settings.narratee]:
            self.pronominalize = True
        if self.pronominalize:
            # Ignore what pronoun returns as subjects to avoid double-
            # counting this word
            (string, _, __) = Pronoun(tag, self.form, 
                self.time).realize(concept, discourse, settings, subjects, tf)
        else:
            extra_adjs = ', '.join(self.adjs)
            item = concept.item_at(tag, self.time)
            if item is None:
                string = 'something'
            else:
                string = item.noun_phrase(discourse, extra_adjs=extra_adjs)
            if self.form == self.possessive:
                string += "'s"
        if tag not in discourse.givens:
            discourse.givens.add(tag)
        if self.form == self.subject:
            if tf is True:
                subjects = ()
            subjects = tuple(list(subjects) + [tag])
            tf = False
        return (string, subjects, tf)


class Deictic(Word):
    'Deictic word which is sensitive to the use of the present tense.'

    def __str__(self):
        return 'D.' + self.tag

    def realize(self, _, __, settings, subjects, tf):
        'Return a string realized from the word.'
        string = str(self)
        if self.tag == 'now':
            string = ['then', 'now'][settings.tense_rs == 'present']
        elif self.tag == 'here':
            string = ['there', 'here'][settings.tense_rs == 'present']
        elif self.tag == 'this':
            string = ['that', 'this'][settings.tense_rs == 'present']
        elif self.tag == 'these':
            string = ['those', 'these'][settings.tense_rs == 'present']
        return (string, subjects, tf)


class Pronoun(Word):
    'Pronoun of some form representing some Item.'

    subject, object, possessive, reflexive = range(4)

    subject_pronoun = {1:
    {'singular': {'male': 'I', 'female': 'I', 'neuter': 'I', '?': 'I'},
     'plural': {'male': 'we', 'female': 'we', 'neuter': 'we', '?': 'we'}},
    2:
    {'singular': {'male': 'you', 'female': 'you', 'neuter': 'you', '?': 'you'},
     'plural': {'male': 'you', 'female': 'you', 'neuter': 'you', '?': 'you'}},
    3:
    {'singular': {'male': 'he', 'female': 'she', 'neuter': 'it',
                  '?': 'she or he'},
     'plural': {'male': 'they', 'female': 'they', 'neuter': 'they',
                '?': 'they'}}}

    object_pronoun = {1:
    {'singular': {'male': 'me', 'female': 'me', 'neuter': 'me', '?': 'me'},
     'plural': {'male': 'us', 'female': 'us', 'neuter': 'us', '?': 'us'}},
    2:
    {'singular': {'male': 'you', 'female': 'you', 'neuter': 'you', '?': 'you'},
     'plural': {'male': 'you', 'female': 'you', 'neuter': 'you', '?': 'you'}},
    3:
    {'singular': {'male': 'him', 'female': 'her', 'neuter': 'it',
                  '?': 'her or him'},
     'plural': {'male': 'them', 'female': 'them', 'neuter': 'them',
                '?': 'them'}}}

    possessive_pronoun = {1:
    {'singular': {'male': 'my', 'female': 'my', 'neuter': 'my', '?': 'my'},
     'plural': {'male': 'our', 'female': 'our', 'neuter': 'our', '?': 'our'}},
    2:
    {'singular': {'male': 'your', 'female': 'your', 'neuter': 'your',
                  '?': 'your'},
     'plural': {'male': 'your', 'female': 'your', 'neuter': 'your',
                '?': 'your'}},
    3:
    {'singular': {'male': 'his', 'female': 'her', 'neuter': 'its',
                  '?': 'her or his'},
     'plural': {'male': 'their', 'female': 'their', 'neuter': 'their',
                '?': 'their'}}}

    reflexive_pronoun = {1:
    {'singular': {'male': 'myself', 'female': 'myself', 'neuter': 'myself',
                  '?': 'myself'},
     'plural': {'male': 'ourselves', 'female': 'ourselves',
                'neuter': 'ourselves', '?': 'selves'}},
    2:
    {'singular': {'male': 'yourself', 'female': 'yourself',
                  'neuter': 'yourself', '?': 'yourself'},
     'plural': {'male': 'yourself', 'female': 'yourself', 'neuter': 'yourself',
                '?': 'yourself'}},
    3:
    {'singular': {'male': 'himself', 'female': 'herself', 'neuter': 'itself',
                  '?': 'herself or himself'},
     'plural': {'male': 'themselves', 'female': 'themselves',
                'neuter': 'themselves', '?': 'themselves'}}}

    def __init__(self, tag, form, time):
        self.form = form
        self.time = time
        Word.__init__(self, tag)

    def __str__(self):
        return 'P.' + self.tag + '.' + str(self.form)

    def realize(self, concept, discourse, settings, subjects, tf):
        'Return a string realized from the word.'
        tag = self.tag
        if tag == '*':
            tag = discourse.spin['focalizer']
        if tag == settings.narrator:
            person = 1
        elif tag == settings.narratee:
            person = 2
        else:
            person = 3
        item = concept.item_at(tag ,self.time)
        if item is None:
            number = 'singular'
            gender = 'neuter'
            # If we knew this referred to an unknown person, gender = '?'
        else:
            number = item.number
            gender = item.gender
        if self.form == self.subject:
            string = self.subject_pronoun[person][number][gender]
        elif self.form == self.object:
            string = self.object_pronoun[person][number][gender]
        elif self.form == self.possessive:
            string = self.possessive_pronoun[person][number][gender]
        elif self.form == self.reflexive:
            string = self.reflexive_pronoun[person][number][gender]
        if self.form == self.subject:
            subjects = tuple(list(subjects) + [tag])
        return (string, subjects, tf)


class Verb(Word):
    'Verb, conjugated based on the subject and other settings.'

    helpers = [
        '',               #  0 Infinitive
        '',               #  1 1-S-present
        '',               #  2 1-P-present
        'am ',            #  3 1-S-present-progressive
        'are ',           #  4 1-P-present-progressive
        'have ',          #  5 1-S-present-perfect
        'have ',          #  6 1-P-present-perfect
        'have been ',     #  7 1-S-present-progressive-perfect
        'have been ',     #  8 1-P-present-progressive-perfect
        '',               #  9 1-S-past
        '',               # 10 1-P-past
        'was ',           # 11 1-S-past-progressive
        'were ',          # 12 1-P-past-progressive
        'had ',           # 13 1-S-past-perfect
        'had ',           # 14 1-P-past-perfect
        'had been ',      # 15 1-S-past-progressive-perfect
        'had been ',      # 16 1-P-past-progressive-perfect
        'will ',          # 17 1-S-future
        'will ',          # 18 1-P-future
        'will be ',       # 19 1-S-future-progressive
        'will be ',       # 20 1-P-future-progressive
        'will have ',     # 21 1-S-future-perfect
        'will have ',     # 22 1-P-future-perfect
        'had been ',      # 23 1-S-future-progressive-perfect
        'had been ',      # 24 1-P-future-progressive-perfect
        '',               # 25 2-S-present
        '',               # 26 2-P-present
        'are ',           # 27 2-S-present-progressive
        'are ',           # 28 2-P-present-progressive
        'have ',          # 29 2-S-present-perfect
        'have ',          # 30 2-P-present-perfect
        'have been ',     # 31 2-S-present-progressive-perfect
        'have been ',     # 32 2-P-present-progressive-perfect
        '',               # 33 2-S-past
        '',               # 34 2-P-past
        'were ',          # 35 2-S-past-progressive
        'were ',          # 36 2-P-past-progressive
        'had ',           # 37 2-S-past-perfect
        'had ',           # 38 2-P-past-perfect
        'had been ',      # 39 2-S-past-progressive-perfect
        'had been ',      # 40 2-P-past-progressive-perfect
        'will ',          # 41 2-S-future
        'will ',          # 42 2-P-future
        'will be ',       # 43 2-S-future-progressive
        'will be ',       # 44 2-P-future-progressive
        'will have ',     # 45 2-S-future-perfect
        'will have ',     # 46 2-P-future-perfect
        'will have been ',# 47 2-S-future-progressive-perfect
        'will have been ',# 48 2-P-future-progressive-perfect
        '',               # 49 3-S-present
        '',               # 50 3-P-present
        'is ',            # 51 3-S-present-progressive
        'are ',           # 52 3-P-present-progressive
        'has ',           # 53 3-S-present-perfect
        'have ',          # 54 3-P-present-perfect
        'has been ',      # 55 3-S-present-progressive-perfect
        'have been ',     # 56 3-P-present-progressive-perfect
        '',               # 57 3-S-past
        '',               # 58 3-P-past
        'was ',           # 59 3-S-past-progressive
        'were ',          # 60 3-P-past-progressive
        'had ',           # 61 3-S-past-perfect
        'had ',           # 62 3-P-past-perfect
        'had been ',      # 63 3-S-past-progressive-perfect
        'had been ',      # 64 3-P-past-progressive-perfect
        'will ',          # 65 3-S-future
        'will ',          # 66 3-P-future
        'will be ',       # 67 3-S-future-progressive
        'will be ',       # 68 3-P-future-progressive
        'will have ',     # 69 3-S-future-perfect
        'will have ',     # 70 3-P-future-perfect
        'will have been ',# 71 3-S-future-progressive-perfect
        'will have been ']# 72 3-P-future-progressive-perfect

    to_be = [
       'be',       #  0 Infinitive
       'am',       #  1 1-S-present
       'are',      #  2 1-P-present
       'being',    #  3 1-S-present-progressive
       'being',    #  4 1-P-present-progressive
       'been',     #  5 1-S-present-perfect
       'been',     #  6 1-P-present-perfect
       'being',    #  7 1-S-present-progressive-perfect
       'being',    #  8 1-P-present-progressive-perfect
       'was',      #  9 1-S-past
       'were',     # 10 1-P-past
       'being',    # 11 1-S-past-progressive
       'being',    # 12 1-P-past-progressive
       'been',     # 13 1-S-past-perfect
       'been',     # 14 1-P-past-perfect
       'being',    # 15 1-S-past-progressive-perfect
       'being',    # 16 1-P-past-progressive-perfect
       'be',       # 17 1-S-future
       'be',       # 18 1-P-future
       'being',    # 19 1-S-future-progressive
       'being',    # 20 1-P-future-progressive
       'been',     # 21 1-S-future-perfect
       'been',     # 22 1-P-future-perfect
       'being',    # 23 1-S-future-progressive-perfect
       'being',    # 24 1-P-future-progressive-perfect
       'are',      # 25 2-S-present
       'are',      # 26 2-P-present
       'being',    # 27 2-S-present-progressive
       'being',    # 28 2-P-present-progressive
       'been',     # 29 2-S-present-perfect
       'been',     # 30 2-P-present-perfect
       'being',    # 31 2-S-present-progressive-perfect
       'being',    # 32 2-P-present-progressive-perfect
       'were',     # 33 2-S-past
       'were',     # 34 2-P-past
       'being',    # 35 2-S-past-progressive
       'being',    # 36 2-P-past-progressive
       'been',     # 37 2-S-past-perfect
       'been',     # 38 2-P-past-perfect
       'being',    # 39 2-S-past-progressive-perfect
       'being',    # 40 2-P-past-progressive-perfect
       'be',       # 41 2-S-future
       'be',       # 42 2-P-future
       'being',    # 43 2-S-future-progressive
       'being',    # 44 2-P-future-progressive
       'been',     # 45 2-S-future-perfect
       'been',     # 46 2-P-future-perfect
       'being',    # 47 2-S-future-progressive-perfect
       'being',    # 48 2-P-future-progressive-perfect
       'is',       # 49 3-S-present
       'are',      # 50 3-P-present
       'being',    # 51 3-S-present-progressive
       'being',    # 52 3-P-present-progressive
       'been',     # 53 3-S-present-perfect
       'been',     # 54 3-P-present-perfect
       'being',    # 55 3-S-present-progressive-perfect
       'being',    # 56 3-P-present-progressive-perfect
       'was',      # 57 3-S-past
       'were',     # 58 3-P-past
       'being',    # 59 3-S-past-progressive
       'being',    # 60 3-P-past-progressive
       'been',     # 61 3-S-past-perfect
       'been',     # 62 3-P-past-perfect
       'being',    # 63 3-S-past-progressive-perfect
       'being',    # 64 3-P-past-progressive-perfect
       'be',       # 65 3-S-future
       'be',       # 66 3-P-future
       'being',    # 67 3-S-future-progressive
       'being',    # 68 3-P-future-progressive
       'been',     # 69 3-S-future-perfect
       'been',     # 70 3-P-future-perfect
       'being',    # 71 3-S-future-progressive-perfect
       'being']     # 72 3-P-future-progressive-perfect

    def __init__(self, tag, time, **keywords):
        self.default_number = None
        self.progressive = None
        self.intensive = False
        self.negated = False
        self.future_style = 'will'
        for (key, value) in keywords.items():
            setattr(self, key, value)
        self.is_be = (tag in ['be', 'am', 'are', 'is'])
        self.time = time
        Word.__init__(self, tag)

    def __str__(self):
        return 'V.' + self.tag + '.' + str(self.default_number)

    def third_person_singular(self):
        if re.search('(ch|sh|s|z|x)$', self.tag):
            new_form = self.tag + 'es'
        elif re.search('[bcdfghjklmnpqrstvwxz]y$', self.tag):
            new_form = self.tag[:-1] + 'ies'
        elif re.search('[^o]o$', self.tag):
            new_form = self.tag + 'es'
        elif self.tag == 'have':
            new_form = 'has'
        else:
            new_form = self.tag + 's'
        return new_form

    def regular_pret_pp(self):
        if self.tag[-1] == 'e':
            new_form = self.tag + 'd'
        elif re.search('[bcdfghjklmnpqrstvwxz]y$', self.tag):
            new_form = self.tag[:-1] + 'ied'
        else:
            new_form = self.tag + 'ed'
        return new_form

    def preterite(self):
        if self.tag in irregular_verb.FORMS:
            new_form = irregular_verb.FORMS[self.tag][0]
        else:
            new_form = self.regular_pret_pp()
        return new_form

    def past_participle(self):
        if self.tag in irregular_verb.FORMS:
            new_form = irregular_verb.FORMS[self.tag][1]
        else:
            new_form = self.regular_pret_pp()
        return new_form

    def present_participle(self):
        if self.tag in irregular_verb.FORMS:
            new_form = irregular_verb.FORMS[self.tag][2]
        else:
            if re.search('e$', self.tag):
                new_form = self.tag[:-1] + 'ing'
            elif re.search('ie$', self.tag):
                new_form = self.tag[:-2] + 'ying'
            else:
                new_form = self.tag + 'ing'
        return new_form

    def determine_person(self, concept, settings, subjects):
        'Check narrator/naratee and use first, second, or third person.'
        person = 3
        if self.default_number is None and len(subjects) == 1:
            only_tag = subjects[0]
            if concept.item_at(only_tag, self.time) is not None:
                if (settings.narrator is not None and
                    only_tag == settings.narrator):
                    person = 1
                elif (settings.narratee is not None and
                      only_tag == settings.narratee):
                    person = 2
        return person

    def determine_number(self, concept, _, subjects):
        "Check verb's number setting or fall back to the subjects' number."
        number = self.default_number
        if number is None:
            number = 'singular'
            if len(subjects) == 0:
                number = 'singular'
            elif len(subjects) == 1:
                only_tag = subjects[0]
                only_item = concept.item_at(only_tag, self.time)
                if only_item is None:
                    number = 'singular'
                else:
                    number = only_item.number
            else:
                number = 'plural'
        return number

    def determine_progressive(self, settings):
        "Check verb's override for progressive or use sentence settings."
        if self.progressive is None:
            progressive = settings.progressive
        else:
            progressive = self.progressive
        return progressive

    def determine_main_word(self, person, number, r_s, e_r, progressive):
        'Based on tense, produce main word and appropriate helpers.'
        i = 0
        if person > 0:
            i = (24 * person) - 23
        if r_s == 'past':
            i += 8
        if r_s == 'future':
            i += 16
        if progressive:
            i += 2
        if e_r == 'anterior': # Perfect aspect
            i += 4
        if number == 'plural':
            i += 1
        if self.is_be:
            main_word = self.to_be[i]
        else:
            main_word = self.tag
            if r_s == 'present' and number == 'singular' and person == 3:
                main_word = self.third_person_singular()
            elif r_s == 'past':
                main_word = self.preterite()
            if progressive:
                main_word = self.present_participle()
            if e_r == 'anterior':
                main_word = self.past_participle()
        return main_word, self.helpers[i]

    def apply_intensive(self, main_word, helper_words, person, number, r_s, e_r,
                        progressive):
        'Change, e.g., "eat" to "do eat".'
        if not progressive and not e_r == 'anterior' and not self.is_be:
            main_word = self.tag
            if r_s == 'present':
                if person == 3:
                    if number == 'plural':
                        helper_words = 'do '
                    else:
                        helper_words = 'does '
                else:
                    if number == 'plural':
                        helper_words = 'does '
                    else:
                        helper_words = 'do '
            if r_s == 'past':
                helper_words = 'did '
        return main_word, helper_words

    def apply_future_style(self, main_word, helper_words, person,
                           number, e_r, progressive):
        'Use "will" or "shall" to get the future.'
        if not self.future_style == 'will':
            if self.future_style == 'shall':
                helper_words = re.sub('will', 'shall', helper_words)
            if self.future_style == 'going to':
                if not e_r == 'anterior' and not progressive:
                    main_word = self.tag
                i = 0
                if person > 0:
                    i = (24 * person) - 23
                if number == 'plural':
                    i += 1
                helper_words = self.to_be[i] + ' going to '
                if progressive and e_r == 'anterior':
                    helper_words += 'have been '
                elif progressive:
                    helper_words += 'be '
                elif e_r == 'anterior':
                    helper_words += 'have '
        return main_word, helper_words

    def realize(self, concept, _, settings, subjects, tf):
        'Return a string realized from the word.'
        person = self.determine_person(concept, settings, subjects)
        number = self.determine_number(concept, settings, subjects)
        progressive = self.determine_progressive(settings)
        if hasattr(self, 'tense_er'):
            settings.tense_er = self.tense_er

        main_word, helper_words = self.determine_main_word(person, number,
                                  settings.tense_rs, settings.tense_er,
                                  progressive)
        if self.intensive or self.negated:
            main_word, helper_words = self.apply_intensive(main_word,
                                      helper_words, person, number, 
                                      settings.tense_rs, settings.tense_er,
                                      progressive)
        if self.negated:
            main_word, helper_words = negate(main_word, helper_words)
        if settings.tense_rs == 'future':
            main_word, helper_words = self.apply_future_style(main_word,
                                      helper_words, person, number,
                                      settings.tense_er, progressive)

        if settings.tense_er == 'posterior' and settings.tense_rs == 'future':
            helper_words += 'be about to '

        all_words = helper_words + main_word

        tf = True
        return (all_words, subjects, tf)


def negate(main_word, helper_words):
    'Return the negative of the verb passed in as main words and helper words.'
    if helper_words == '':
        main_word = main_word + ' not'
    else:
        helper_list = helper_words.split(' ')
        helper_list = helper_list[:1] + ['not'] + helper_list[1:]
        helper_words = ' '.join(helper_list)
    return main_word, helper_words


########NEW FILE########
__FILENAME__ = recognizer
'Understand prepared user input as commands or directives. The "parser."'

__author__ = 'Nick Montfort'
__copyright__ = 'Copyright 2011 Nick Montfort'
__license__ = 'ISC'
__version__ = '0.5.0.0'
__status__ = 'Development'

import copy
import re

def noun_phrase(item, discourse):
    'Returns a regular expression (string) corresponding to the Item.'
    (before, nouns, after) = item.referring
    if str(item) == discourse.spin['narratee']:
        nouns.update(discourse.me_nouns)
    if str(item) == discourse.spin['narrator']:
        nouns.update(discourse.you_nouns)
    phrase = ('((and|,|' + '|'.join(before) + '|' + '|'.join(nouns) + ') )*' +
              '(' + '|'.join(nouns) + ')' +
              '( (' + '|'.join(after) + '|' + '|'.join(nouns) + '))*')
    return discourse.determiner + phrase

def correspond(exp, string):
    'Returns True if and only if the expression matches the entire string.'
    if len(exp) > 0:
        if not exp[0] == '^':
            exp = '^' + exp
        if not exp[-1] == '$':
            exp = exp + '$'
    return re.match(exp, string)

def contained_substances(items, concept):
    contents = []
    for i in items:
        if ((hasattr(concept.item[i], 'vessel') or
             hasattr(concept.item[i], 'source')) and
            len(concept.item[i].children) > 0):
            (_, child) = concept.item[i].children[0]
            if child not in items:
                contents += [child]
    return contents

def nonterminal(nonterm, discourse, concept):
    'Returns all phrases that a token such as ACCESSIBLE matches.'
    phrases = []
    agent = discourse.spin['commanded']
    if nonterm == 'RELATION':
        link_names = discourse.english_to_link.items()
        link_names.sort()
        # Sorted here because 'onto' should be listed before 'on' and so on,
        # so the list of name to link mappings is reversed.
        link_names.reverse()
        for mapping in link_names:
            phrases.append(mapping)
    elif nonterm == 'ACCESSIBLE':
        for i in agent_access(agent, concept):
            phrases.append((noun_phrase(concept.item[i], discourse), i))
    elif nonterm == 'ACTOR':
        for i in agent_access(agent, concept):
            if concept.has('actor', i):
                phrases.append((noun_phrase(concept.item[i], discourse), i))
    elif nonterm == 'NOT-DESCENDANT':
        for i in not_descendant(agent, concept):
            phrases.append((noun_phrase(concept.item[i], discourse), i))
    elif nonterm == 'DESCENDANT':
        for i in concept.descendants(agent):
            phrases.append((noun_phrase(concept.item[i], discourse), i))
    elif nonterm == 'WORN':
        for i in worn(agent, concept):
            phrases.append((noun_phrase(concept.item[i], discourse), i))
    elif nonterm == 'DIRECTION':
        for (i, j) in discourse.compass.items():
            phrases.append((discourse.determiner + i, j))
    elif nonterm == 'NEARBY':
        if agent == '@cosmos':
            for i in concept.item:
                phrases.append((noun_phrase(concept.item[i], discourse), i))
            return phrases
        agent_room = concept.room_of(agent)
        if agent_room is None:
            return []
        elif concept.item[str(agent_room)].door:
            rooms_visible = concept.item[str(agent_room)].connects
        else:
            rooms_visible = agent_room.view.keys()
        for room in [str(agent_room)] + rooms_visible:
            for i in [room] + concept.descendants(room):
                phrases.append((noun_phrase(concept.item[i], discourse), i))
    return phrases

def agent_access(agent, concept):
    """Returns a list of everything the agent can access.

    Plus contained substances, actually, because even if they are in closed
    containers their names may be used metonymically."""
    items = concept.accessible(agent)
    items += contained_substances(items, concept)
    return items

def not_descendant(agent, concept):
    "Returns a list of accessible items not in the agent's descendants."
    not_of = []
    agent_children = []
    for (_, item) in concept.item[agent].children:
        agent_children += [item]
    for item in agent_access(agent, concept):
        if item not in agent_children:
            not_of += [item]
    return not_of

def worn(agent, concept):
    'Returns a list of things on (worn by) the agent.'
    items = []
    for (link, item) in concept.item[agent].children:
        if link == 'on':
            items.append(item)
    return items

def check_rule(rule_list, action_list, token_string, discourse, concept):
    """Returns all rules on the rule list that match the token string.

    For instance, the two tokens "take lamp" will match ['TAKE', '@lamp'],
    assuming there is an object @lamp called "lamp" in the area and nothing
    else is called "lamp." That will be returned from TAKE's rule list. When
    check_rule() is called with other rule lists, an empty list will be
    returned.

    In cases of ambiguity ("take a thing" when there are several around) a
    single call of check_rule() may return a list with several Items."""
    verb_part = rule_list[0]
    command_verb = action_list[0]
    result = []
    if len(rule_list) == 1:
        if correspond(verb_part, token_string):
            result = [[command_verb]]
    elif re.match(verb_part, token_string) is not None:
        token_string = re.sub('^' + verb_part + ' ', '', token_string)
        r_list = copy.copy(rule_list)
        a_list = copy.copy(action_list)
        args = check_args((r_list, 1), (a_list, 1), token_string,
                          discourse, concept)
        if len(args) == 1:
            if args[0].pop() == '-SUCCESS-':
                result = [[command_verb] + args[0]]
        elif len(args) > 1: # Ambiguous arguments; list every possibility
            result = []
            for i in args:
                i.pop() # Get rid of the "-SUCCESS-" token
                result.append([command_verb] + i)
    return result

def check_args(rule, action, token_string, discourse, concept):
    'Returns matches for tokens past the first one, the arguments.'
    (rule_list, rule_index) = rule
    (action_list, action_index) = action
    matched = []
    if len(token_string) == 0:
        # Nothing left to match. Two possibilities for success here.
        if len(rule_list) == rule_index:
            # The rule list has been exhausted too
            matched = [['-SUCCESS-']]
        elif len(rule_list) == rule_index + 1:
            # There is one last part remaining in the rule list...
            if (rule_list[rule_index][0] == '(' and
                rule_list[rule_index][-2:] == ')?'):
                # But this last part is optional.
                matched = [['-SUCCESS-']]
    # Continuing: There is something left in the token string.
    elif not len(rule_list) == rule_index:
        # As long as there is something left in the rule list, too, keep
        # checking...
        rule_piece = rule_list[rule_index]
        if not rule_piece[0].isupper():
            if not rule_piece[-1] == ' ':
                rule_piece += '(\\b|$)'
            if re.match(rule_piece, token_string) is not None:
                token_string = re.sub('^' + rule_piece, '', token_string)
                if token_string[:1] == ' ':
                    token_string = token_string[1:]
                matched = check_args((rule_list, rule_index+1),
                                     (action_list, action_index),
                                     token_string, discourse, concept)
        elif rule_piece == 'STRING':
            word = re.sub(' .*', '', token_string)
            token_string = re.sub('^'+word+' ?', '', token_string)
            additional = check_args((rule_list, rule_index+1),
                                    (action_list, action_index),
                                    token_string, discourse, concept)
            for i in additional:
                matched.append([word] + i)
        else:
            for (exp, arg) in nonterminal(rule_piece, discourse, concept):
                if len(exp) > 0 and not exp[-1] == ' ':
                    exp += '(\\b|$)'
                if re.match(exp, token_string) is not None:
                    new_token_string = re.sub('^' + exp, '', token_string)
                    if new_token_string[:1] == ' ':
                        new_token_string = new_token_string[1:]
                    additional = check_args((rule_list, rule_index+1),
                                            (action_list, action_index+1),
                                            new_token_string, discourse,
                                            concept)
                    for i in additional:
                        matched.append([arg] + i)
    return matched

def recognize(user_input, discourse, concept):
    """Main function for parsing user input.

    Deals with special cases (such as "west", which is mapped to a command
    with a verb), invokes check_rule for each command, and sets the
    appropriate information on user_input."""
    first = []
    while (len(user_input.tokens) > 0 and
           user_input.tokens[0] not in discourse.separator):
        first.append(user_input.tokens.pop(0))

    # Remove any extra separators
    while (len(user_input.tokens) > 0 and
           (user_input.tokens[0] in discourse.separator)):
        user_input.tokens.pop(0)

    if first[0] in discourse.compass:
        user_input.category = 'command'
        direction = discourse.compass[first[0]]
        user_input.normal = ['LEAVE', direction]

    rule_matches = []
    token_string = ' '.join(first)
    for (action_list, rule_list) in discourse.commands:
        for new_match in check_rule(rule_list, action_list, token_string,
                                    discourse, concept):
            if not new_match in rule_matches:
                rule_matches.append(new_match)

    if len(rule_matches) == 1:
        command = rule_matches[0]
        if (command[0] == 'TURN_ON' and
            'on' not in dir(concept.item[command[1]]) and
            'lit' in dir(concept.item[command[1]])):
            command[0] = 'ILLUMINATE'
        elif (command[0] == 'TURN_OFF' and
            'on' not in dir(concept.item[command[1]]) and
            'lit' in dir(concept.item[command[1]])):
            command[0] = 'EXTINGUISH'
        for token in command:
            if token in concept.item:
                if token not in discourse.givens:
                    discourse.givens.add(token)
        user_input.category = 'command'
        user_input.normal = command

    elif len(rule_matches) > 1:
        user_input.category = 'unrecognized'
        user_input.possible = rule_matches

    if first[0] in discourse.directive_verbs:
        head = discourse.directive_verbs[first[0]]
        directive = [head] + first[1:]
        user_input.category = 'directive'
        user_input.normal = directive

    if discourse.debug and first[0] in discourse.debugging_verbs:
        head = discourse.debugging_verbs[first[0]]
        if (head == 'narrating' and len(first) > 1 and
            first[1] in discourse.spin_arguments):
            argument = discourse.spin_arguments[first[1]]
            directive = [head] + [argument] + first[2:]
        else:
            directive = [head] + first[1:]
        user_input.category = 'directive'
        user_input.normal = directive

    return user_input

########NEW FILE########
__FILENAME__ = reply_planner
'Plan a reply, as in "document planning" (but this is a reply in a dialogue).'

__author__ = 'Nick Montfort'
__copyright__ = 'Copyright 2011 Nick Montfort'
__license__ = 'ISC'
__version__ = '0.5.0.0'
__status__ = 'Development'

import operator
import random

def determine_speed(action, discourse):
    'Returns a number in [0, 1], the speed of narration for this Action.'
    if action.salience > 0.75:
        speed = discourse.spin['speed'] + ((1-discourse.spin['speed'])/2)
    elif (action.verb == 'wait' and
          not action.agent == discourse.spin['focalizer']):
        # Do not ever narrate other characters waiting (doing nothing).
        speed = 0.0
    else:
        speed = discourse.spin['speed']
    return speed


def structure_nodes(nodes, ref_time, speech_time, discourse):
    'Return the root node of a reply structure organized using the parameters.'
    children = []
    last_action_time = None
    for node in nodes:
        if node.category == 'action':
            node.speed = determine_speed(node.info, discourse)
            node.prior = last_action_time
            last_action_time = node.info.start
            if node.speed > 0.0:
                discourse.mark_narrated(node.info)
                children.append(node)
        else:
            children.append(node)
    return Internal('-', ref_time, speech_time, children)


def produce_analepsis(key_action, previous, concept, discourse):
    'Finds an analepsis based on and to be inserted after the key Action.'
    if hasattr(key_action, 'direct'):
        for action in previous:
            if (hasattr(action, 'direct') and 
                action.direct == key_action.direct and
                not concept.item[action.direct] == '@adventurer'):
                intro = Commentary("Ah, let's remember ...")
                room = NameRoom(action)
                tell_action = TellAction(action)
                outro = Commentary("Yes, that was a fine recollection.")
                return [structure_nodes([intro, room, tell_action, outro], 
                                        discourse.follow, key_action.end,
                                        discourse)]
    return []


def cull_actions(actions, concept, discourse):
    'Remove Actions that should not be narrated at all from a sorted list.'

    to_remove = []
    to_aggregate = []
    post_final = False
    for action in actions:
        if (action.verb == 'examine' and
            not action.agent == discourse.spin['focalizer'] and
            action.direct == str(concept.room_of(action.agent))):
            to_remove.append(action)
        elif action.salience < .2:
            to_remove.append(action)
        elif post_final:
            to_remove.append(action)
        if action.final:
            post_final = True
    for omit in to_remove:
        actions.remove(omit)
    if discourse.spin['frequency'][0][1] == 'iterative':
        if discourse.spin['frequency'][0][0][0] == 'agent':
            quality = discourse.spin['frequency'][0][0][1]
            for action in actions:
                if quality in concept.item[action.agent].qualities:
                    to_aggregate.append(action)
            if len(to_aggregate) >= 2:
                for omit in to_aggregate:
                    actions.remove(omit)
                actions.append(to_aggregate)
    return actions


def determine_speech_time(discourse):
    'Set speech time all the way ahead, or to follow the events, or back.'

    if discourse.spin['time'] == 'before':
        speech_time = discourse.min
    if discourse.spin['time'] == 'during':
        speech_time = discourse.follow
    if discourse.spin['time'] == 'after':
        speech_time = discourse.max
    return speech_time


def plan(action_ids, concept, discourse):
    'Create a reply structure based on indicated Actions and the spin.'


    speech_time = determine_speech_time(discourse)

    # Determine which Actions this focalizer knows about.
    # Build a list of the appropriate (Action, start time) tuples.
    known_id_times = []
    if discourse.spin['window'] == 'current':
        for i in action_ids:
            if i in concept.act:
                known_id_times.append((i, concept.act[i].start))
    else:
        for i in concept.act:
            known_id_times.append((i, concept.act[i].start))

    # Produce a list of Actions sorted by time.
    actions = [concept.act[id_etc[0]] for id_etc in
               sorted(known_id_times, key=operator.itemgetter(1))]

    if not discourse.spin['window'] == 'current':
        actions = actions[-discourse.spin['window']:]

    # Remove Actions which won't be narrated at all, aggregate others.
    actions = cull_actions(actions, concept, discourse)

    if len(actions) == 0:
        return Leaf('ok')

    if discourse.spin['perfect']:
        reference_time = discourse.right_after
    else:
        reference_time = discourse.follow

    # Sort the Actions chronologically to begin with.
    actions.sort(key=operator.attrgetter('start'))
    if discourse.spin['order'] == 'chronicle':
        nodes = [TellAction(i) for i in actions]
        reply_plan = structure_nodes(nodes, reference_time, speech_time,
                                     discourse)
    elif discourse.spin['order'] == 'retrograde':
        actions.reverse()
        if speech_time == discourse.follow:
            speech_time = actions[0].start
        nodes = [TellAction(i) for i in actions]
        reply_plan = structure_nodes(nodes, reference_time, speech_time,
                                     discourse)
    elif discourse.spin['order'] == 'achrony':
        random.shuffle(actions)
        nodes = [TellAction(i) for i in actions]
        reply_plan = structure_nodes(nodes, reference_time, speech_time,
                                     discourse)
    elif discourse.spin['order'] == 'analepsis':
        nodes = [TellAction(i) for i in actions]
        if actions[-1].id > 4:
            limit = actions[-1].id - 4
            previous = [concept.act[i] for i in
                        range(1, limit) if i in concept.act]
            analepsis = produce_analepsis(actions[0], previous, concept, 
                                          discourse)
            nodes = nodes[:1] + analepsis + nodes[1:]
        reply_plan = structure_nodes(nodes, reference_time, speech_time,
                                     discourse)
    elif discourse.spin['order'] == 'syllepsis':
        nodes = [TellAction(i) for i in actions]
        reply_plan = structure_nodes(nodes, reference_time, speech_time,
                                     discourse)
    return reply_plan


class ReplyNode(object):
    'Abstract base class for reply structure nodes.'

    def __init__(self, category):
        if self.__class__ == ReplyNode:
            raise StandardError('Attempt to instantiate abstract base ' +
                                'class reply_planner.ReplyNode')
        self.category = category


class Internal(ReplyNode):
    'Internal node in a reply structure, representing organization.'

    def __init__(self, category, reference_time, speech_time, children):
        self.ref = reference_time
        self.speech = speech_time
        self.children = children
        ReplyNode.__init__(self, category)

    def __str__(self):
        string = self.category + ' ('
        for child in self.children:
            string += str(child) + ' '
        string = string[:-1] + ') '
        return string


class Leaf(ReplyNode):
    'Leaf node in a reply structure, representing something to narrate.'

    def __init__(self, category, info=None):
        if info is not None:
            self.info = info
        self.speed = None
        self.event = None
        self.prior = None
        if category == 'action' or category == 'room':
            self.event = info.start
        ReplyNode.__init__(self, category)

    def __str__(self):
        return self.category + ' ' + str(self.info)


class Commentary(Leaf):
    'A statement that does not narrate or describe: "Be careful, dear reader!"'

    def __init__(self, info):
        Leaf.__init__(self, 'commentary', info)


class NameRoom(Leaf):
    'A statement naming the Room in which the Action took place.'

    def __init__(self, info):
        Leaf.__init__(self, 'room', info)
        self.prior = self.event - 0.5


class TellAction(Leaf):
    'A statement narrating an Action.'

    def __init__(self, info):
        Leaf.__init__(self, 'action', info)


########NEW FILE########
__FILENAME__ = flashback
spin = {
    'order': 'analepsis'}


########NEW FILE########
__FILENAME__ = hesitant
from random import randint, choice

interjections = ['uh', 'uh', 'uh', 'um', 'um', 'er']

def sentence_filter(phrases):
    new_phrases = phrases[:1]
    for original in phrases[1:]:
        if randint(1,6) == 1:
            if not new_phrases[-1][-1] in ',.:;':
                new_phrases.append(',')
            new_phrases.append(choice(interjections))
            if not original[:1] in ',.:;':
                new_phrases.append(',')
        new_phrases.append(original)
    return new_phrases

spin = {'sentence_filter': [sentence_filter]}


########NEW FILE########
__FILENAME__ = prophecy
spin = {
    'time': 'before'}


########NEW FILE########
__FILENAME__ = retrograde
spin = {
    'order': 'retrograde',
    'time_words': True}


########NEW FILE########
__FILENAME__ = surprise
'A spin to make the narrator seem surprised at everything.'

__author__ = 'Nick Montfort <nickm@nickm.com>'
__version__ = '0.5'

from random import randint, choice


def sentence_filter(phrases):
    chosen = randint(1,8)
    if chosen == 1:
        phrases = [choice(['whoa,', 'dude,',])] + phrases
    elif chosen == 2:
        if not phrases[-1][-1] in ',.:;':
            phrases[-1] += ','
        phrases = phrases + [choice(['man','dude',])]
    phrases[-1] = phrases[-1] + '!'
    return phrases

def paragraph_filter(paragraphs):
    chosen = randint(1,3)
    if chosen == 1:
        paragraphs = paragraphs + choice(['Amazing!', 'Wow!', 'Awesome!',
                                          'Out of this world!', 'Incredible!'])
    return paragraphs

spin = {'sentence_filter': [sentence_filter],
        'paragraph_filter': [paragraph_filter]}


########NEW FILE########
__FILENAME__ = told_and_focalized_by_guard
spin = {
    'narrator': '@guard',
    'narratee': '@teller',
    'focalizer': '@guard',
    'time': 'after'}


########NEW FILE########
__FILENAME__ = valley_girl
from random import randint, choice

def sentence_filter(phrases):
    new_phrases = phrases[:1]
    for original in phrases[1:]:
        if randint(1,5) == 1:
            if not new_phrases[-1][-1] in ',.:;':
                new_phrases.append(',')
            new_phrases.append('like')
            if not original in ',.:;':
                new_phrases.append(',')
        new_phrases.append(original)
    if len(new_phrases) > 0 and randint(1,6) == 1:
        if not new_phrases[-1] in ',.:;':
            new_phrases.append(',')
        new_phrases.append(choice(['totally', 'for sure']))
    return new_phrases

spin = {'sentence_filter': [sentence_filter]}


########NEW FILE########
__FILENAME__ = when
'Rules for when a refusal by an actor will happen, for use in fictions.'

__author__ = 'Nick Montfort'
__copyright__ = 'Copyright 2011 Nick Montfort'
__license__ = 'ISC'
__version__ = '0.5.0.0'
__status__ = 'Development'

def always(_):
    'No matter what the situation, refuse to do the action.'
    return True


########NEW FILE########
__FILENAME__ = world_model
'World and Concept classes for instantiation by interactive fictions.'

__author__ = 'Nick Montfort'
__copyright__ = 'Copyright 2011 Nick Montfort'
__license__ = 'ISC'
__version__ = '0.5.0.0'
__status__ = 'Development'

import copy
import operator

import can
import item_model

def check_for_reserved_tags(items):
    'Raise an error if a reserved tag, such as @cosmos, is in the list.'
    if '@cosmos' in items:
        raise StandardError('The tag "@cosmos" is reserved for the ' +
         'special item at the root of the item tree. Use a different ' +
         'tag for item now tagged "@cosmos".')
    if '@focalizer' in items:
        raise StandardError('The tag "@focalizer" is reserved for use ' +
         'in indicating the actor who is currently focalizing the ' +
         'narration. Use a different tag for item now tagged ' +
         '"@focalizer".')
    if '@commanded' in items:
        raise StandardError('The tag "@commanded" is reserved for use ' +
         'in indicating the actor who is currently being commanded. ' +
         'Use a different tag for item now tagged "@commanded".')


class WorldOrConcept(object):
    'Abstract base class for the World and for Concepts.'

    def __init__(self, item_list, actions):
        if self.__class__ == WorldOrConcept:
            raise StandardError('Attempt to instantiate abstract base ' +
                                'class world_model.WorldOrConcept')
        self.item = {}
        self.act = actions
        self.ticks = 0
        seen_tags = []
        # Construct the World's Item dictionary from the Item list:
        for item in item_list:
            if str(item) in seen_tags:
                raise StandardError('The tag "' + str(item) + '" is ' +
                 "given to more than one item in the fiction's code. " +
                 'Item tags must be unique.')
            seen_tags.append(str(item))
            self.item[str(item)] = item
        check_for_reserved_tags(self.item)

    def __str__(self):
        return str(self.act) + '\n' + str(self.item)

    def accessible(self, actor):
        'List all Items an Item can access.'
        if actor == '@cosmos':
            return self.item.keys()
        compartment = self.compartment_of(actor)
        tag_list = [str(compartment)]
        for (link, child) in compartment.children:
            if not link == 'on':
                tag_list += [child]
                tag_list += self.descendants(child, stop='closed')
        tag_list += compartment.shared + self.doors(str(compartment))
        accessible_list = []
        for tag in tag_list:
            if (not hasattr(self.item[tag], 'accessible') or 
                self.item[tag].accessible):
                accessible_list.append(tag)
        return accessible_list

    def ancestors(self, tag):
        'List all Items hierarchically above an Item.'
        items_above = []
        i = self.item[tag].parent
        while i is not None:
            items_above += [i]
            i = self.item[i].parent
        return items_above

    def compartment_of(self, tag):
        'Return the opaque compartment around the Item.'
        if tag == '@cosmos' or self.item[tag].room:
            return self.item[tag]
        compartment = self.item[self.item[tag].parent]
        while not (compartment.room or compartment.door or
                   str(compartment) == '@cosmos' or
                   (not compartment.transparent and
                    hasattr(compartment, 'open') and not compartment.open)):
        # Keep ascending to the next parent until we encounter either
        # (1) a room, (2) @cosmos, or (3) an opaque Item that has the "open" 
        # feature and is closed.
            compartment = self.item[compartment.parent]
        return compartment

    def respondents(self, action):
        """Return a list: the cosmos, the Room of the agent, (living) contents.

        These are all the Items that can prevent or react to an Action by
        the agent of the action. If the Item has an "alive" feature, it is only 
        added if alive is True.

        A special case: If the agent has configured itself to a new Room, the
        new Room and (living) contents have a chance to respond, too."""
        tag_list = []
        tag_list.append('@cosmos')
        room = self.room_of(action.agent)
        if room is not None:
            tag_list.append(str(room))
            for tag in self.descendants(str(room)):
                if (not hasattr(self.item[tag], 'alive') or
                    self.item[tag].alive):
                    tag_list.append(tag)
        if action.configure and action.direct == action.agent:
            new_room = self.room_of(action.new_parent)
            if not room == new_room and new_room is not None:
                tag_list.append(str(new_room))
                for tag in self.descendants(str(new_room)):
                    if (not hasattr(self.item[tag], 'alive') or
                        self.item[tag].alive):
                        tag_list.append(tag)
        return tag_list

    def descendants(self, tag, stop='bottom'):
        """List all Items hierarchically under "tag".

        If stop='bottom', descend all the way. If stop='closed', go to down to
        closed children, but not inside those; for stop='opaque', stop at 
        opaque ones."""
        items_under = []
        if (stop == 'bottom' or
           (stop == 'closed' and (not hasattr(self.item[tag], 'open')
            or self.item[tag].open)) or
           (stop == 'opaque' and (not hasattr(self.item[tag], 'open')
            or self.item[tag].open or self.item[tag].transparent))):
            for (_, child) in self.item[tag].children:
                if child in self.item:
                    items_under += [child] + self.descendants(child, stop=stop)
        # If this is a room, include doors & shared things; otherwise [].
        return items_under + self.item[tag].shared + self.doors(tag)

    def has(self, category, tag):
        'Does the tag represent an Item of this category in this World/Concept?'
        return tag in self.item and getattr(self.item[tag], category)

    def room_of(self, tag):
        'If the Item exists and is in a Room, return the Room.'
        while (tag in self.item and not self.has('room', tag) and
            not self.has('door', tag) and not tag == '@cosmos'):
            tag = self.item[tag].parent
        if self.has('room', tag) or self.has('door', tag):
            return self.item[tag]
        return None

    def show_descendants(self, tag, padding=''):
        'Return the tree rooted at this Item.'
        if tag not in self.item:
            return ''
        link = ''
        if not tag == '@cosmos':
            link = self.item[tag].link
        string = (padding + tag + ': ' + self.item[tag].noun_phrase() +
                  ' [' + link + ']\n')
        for (_, child) in self.item[tag].children:
            string += self.show_descendants(child, padding + ('    '))
        return string

    def doors(self, tag):
        "Returns a list of the Item's Doors; [] if there are none."
        doors = []
        if tag in self.item and self.item[tag].room:
            for direction in self.item[tag].exits:
                leads_to = self.item[tag].exits[direction]
                if self.has('door', leads_to) and not leads_to in doors:
                    doors.append(leads_to)
        return doors


class Concept(WorldOrConcept):
    "An Actor's theory or model of the World, which can be used in telling."

    def __init__(self, item_list, actions, cosmos=None):
        self.changed = []
        WorldOrConcept.__init__(self, item_list, actions)
        if cosmos is None:
            cosmos = item_model.Actor('@cosmos', called='nature',
                                       allowed=can.have_any_item)
        self.item['@cosmos'] = cosmos
        for (tag, item) in self.item.items():
            if not tag == '@cosmos':
                self.item[item.parent].add_child(item.link, tag, True)


    def item_at(self, tag, time):
        'Return the Item from this moment in the Concept.'
        if tag not in self.item:
            return None
        item = self.item[tag]
        current = len(self.changed) - 1
        while current >= 0 and self.changed[current][0] > time:
            (_, changed_tag, old) = self.changed[current]
            if changed_tag == tag:
                item = old
            current -= 1
        return item

    def update_item(self, item, time):
        'After perception, change an Item within this Concept.'
        if str(item) in self.item:
            old = self.item[str(item)]
        else:
            old = None
        self.item[str(item)] = item
        self.changed.append((time, str(item), old))

    def roll_back_to(self, time):
        'Go back to a previous state of this Concept.'
        new_ids = []
        for action_id in self.act:
            new_ids.append((action_id, self.act[action_id].start))
        ids_times = sorted(new_ids, key=operator.itemgetter(1))
        while len(ids_times) > 0 and ids_times[-1][1] > time:
            (last_id, _) = ids_times.pop()
            self.act.pop(last_id)
        while len(self.changed) > 0 and self.changed[-1][0] > time:
            (_, tag, old) = self.changed.pop()
            if old is None:
                del self.item[tag]
            else:
                self.item[tag] = old

    def copy_at(self, time):
        'Return a new Concept based on this one, but from an earlier time.'
        new_concept = copy.deepcopy(self)
        new_concept.roll_back_to(time)
        return new_concept


def sight_culprit(prominence, view, lit):
    'Which of the three factors is mostly to blame for the lack of visibility?'
    if lit <= prominence and lit <= view:
        return 'enough_light'
    if view <= prominence and view <= lit:
        return 'good_enough_view'
    return 'item_prominent_enough'


class World(WorldOrConcept):
    'The simulated world; it has Items and Actions.'

    def __init__(self, fiction):
        self.running = True
        action_dict = {}
        for action in fiction.initial_actions:
            action.cause = 'initial_action'
            action_dict[action.id] = action
        self.concept = {}
        WorldOrConcept.__init__(self, fiction.items, action_dict)
        # Instantiate the needed amounts of Substance
        for substance in [i for i in fiction.items if i.substance]:
            parents = []
            for tag in self.item:
                if (hasattr(self.item[tag], 'source') and
                    self.item[tag].source == str(substance)):
                    parents.append(tag)
                elif hasattr(self.item[tag], 'vessel'):
                    if self.item[tag].vessel == str(substance):
                        # The amount should go into the vessel itself.
                        parents.append(tag)
                    else:
                        # The amount should become the child of the main
                        # Substance Item, which is of @cosmos. It's necessary
                        # to create one amount for each empty vessel (or
                        # vessel that is holding something else) since that 
                        # vessel might hold the Substance later.
                        parents.append(str(substance))
            tag_number = 1
            for parent in parents:
                new_item = copy.deepcopy(substance)
                new_item._tag += '_'  + str(tag_number)
                tag_number += 1
                new_item.link = 'in'
                new_item.parent = parent
                self.item[str(new_item)] = new_item
        if fiction.cosmos is None:
            fiction.cosmos = item_model.Actor('@cosmos', called='nature',
                                       allowed=can.have_any_item)
        self.item['@cosmos'] = fiction.cosmos
        for (tag, item) in self.item.items():
            if not tag == '@cosmos':
                self.item[item.parent].add_child(item.link, tag, True)


    def advance_clock(self, duration):
        'Move the time forward a specified number of ticks.'
        self.ticks += duration
        for actor in self.concept:
            self.concept[actor].ticks = self.ticks

    def back_up_clock(self, target_time):
        'Roll the time back to a particular tick.'
        self.ticks = target_time
        for actor in self.concept:
            self.concept[actor].roll_back_to(self.ticks)

    def light_level(self, tag):
        "Determines the light level (not just glow) in the Item's compartment."
        compartment = self.compartment_of(tag)
        if compartment is None:
            return 0.0
        total = compartment.glow
        for (_, child) in compartment.children:
            total += self.light_within(child)
        return total

    def light_within(self, tag):
        'Returns the light illuminating an Item, inherently and within.'
        total = self.item[tag].glow # The inherent light coming from the item.
        for (link, child) in self.item[tag].children:
            if link == 'in':
            # For Items that are 'in', descend if open or transparent.
                if not hasattr(self.item[tag], 'open') or self.item[tag].open:
                    total += self.light_within(child)
                elif self.item[tag].transparent:
                    total += self.light_within(child)
            else:
                total += self.light_within(child)
        return total

    def prevents_sight(self, actor, tag):
        'Returns a reason (if there are any) that "actor" cannot see "tag".'
        if actor == '@cosmos':
        # @cosmos can see everything at all times.
            return None
        item_place = self.room_of(tag)
        actor_place = self.room_of(actor)
        if actor_place is None:
        # The Actor is "out of play" (of @cosmos), and cannot see anything.
            return 'actor_in_play'
        if (item_place is None and
            not tag in self.item[str(actor_place)].shared and
            not tag in self.doors(str(actor_place))):
        # The Item could be either a SharedThing or a Door if its Room is
        # None. If its Room is None and neither is the case, however, it 
        # must be "out of play."
            return 'item_in_play'
        compartment = self.compartment_of(actor)
        view_tags = []
        if not compartment == actor_place:
        # The Actor is is some sort of opaque compartment within a room.
        # Only Items within that compartment will be visible.
            view_tags = [str(compartment)]
            for (link, child) in compartment.children:
                if not link == 'on':
                    view_tags += [child] 
                    view_tags += self.descendants(child, stop='opaque')
        else:
        # Otherwise, list all the Items to which there is a line of sight
        # in the Actor's Room and in every Room that has a view from there.
            if self.item[str(actor_place)].door:
                rooms_visible = self.item[str(actor_place)].connects
            else:
                rooms_visible = actor_place.view.keys()
            for room_tag in [str(actor_place)] + rooms_visible:
                view_tags += ([room_tag] + 
                               self.descendants(room_tag, stop='opaque'))
        if tag not in view_tags:
            return 'line_of_sight'
        view = 1.0
        # Set the view to be perfect (1.0). This applies if the Actor and
        # Item are in the same Room, or if the Item is a SharedThing or Door
        # of the Actor's Room, or if the Actor is in a Door and the Item is
        # in a connecting Room.
        if actor_place.room and str(item_place) in actor_place.view:
        # If looking onto a Room in view, check how well it can be seen.
            (view, _) = actor_place.view[str(item_place)]
        lit = self.light_level(tag)
        if str(self.compartment_of(actor)) == tag:
        # The compartment itself is the one case where it's important to
        # get the interior light level. If the line of sight crosses the 
        # compartment, the light level doesn't matter; the item can't be seen.
        # If inside, the light level is computed within the compartment. But
        # the compartment itself has different "inside" and "outside" light
        # levels. Select an arbitrary child of the compartment (there must
        # be at least one, the Actor) and check the light level for that child.
            (_, child) = self.item[tag].children[0]
            lit = self.light_level(child)
        visibility = self.item[tag].prominence * view * lit
        if visibility >= 0.2:
        # 0.2 is the threshhold for seeing something.
        # An actor sees something that has prominence 0.5 and is in a room with
        #   view 0.5 under full light (1): 0.5 * 0.5 * 1 = 0.25 >= 0.2
        # An actor sees something that has prominence 1 and is in the same room
        #   even under very low (0.2) light: 1 * 1 * .02 = 0.2 >= 0.2
        # Something with prominence below 0.2 will never be visible to an actor
        #   in the current system.
        # Something with prominence 0.3 will be seen (under full light) in the
        #   same room but not from a room where the view is 0.6.
            return None
        # Assign blame to whichever value is smallest.
        return sight_culprit(self.item[tag].prominence, view, lit)

    def can_see(self, actor, tag):
        'Is the item identified by "tag" visible to "actor"?'
        return self.prevents_sight(actor, tag) is None

    def reset(self):
        'Revert the World and Concepts to their initial states.'
        self.undo(1)
        for actor in self.concept:
            self.concept[actor].roll_back_to(1)

    def set_concepts(self, actors):
        "Set initial information in all Actors' Concepts."
        for actor in self.item:
            if self.has('actor', actor) and not actor == '@cosmos':
                known_items = []
                for i in self.item:
                    if self.can_see(actor, i):
                        known_items.append(copy.deepcopy(self.item[i]))
                self.concept[actor] = Concept(known_items, {})
        for (actor, items, actions) in actors:
            self.concept[actor] = Concept(items, actions)
        cosmos_items = []
        for i in self.item:
            if not i == '@cosmos':
                cosmos_items.append(copy.deepcopy(self.item[i]))
        cosmos_acts = copy.deepcopy(self.act)
        self.concept['@cosmos'] = Concept(cosmos_items, cosmos_acts)
        for actor in self.concept.keys():
            self.concept[actor].concept_of = actor

    def transfer(self, item, actor, time):
        "Place an appropriate version of an Item in the Actor's Concept."
        concept = self.concept[actor]
        # If a Room, first add this Room as a child of @cosmos
        if item.room and str(item) not in self.concept[actor].item:
            new_cosmos = copy.deepcopy(concept.item['@cosmos'])
            new_cosmos.add_child('in', str(item))
            concept.update_item(new_cosmos, time)
        # Now, the basic transfer applicable to all Items
        if (str(item) not in concept.item or
            not concept.item[str(item)] == item):
            seen_item = copy.deepcopy(item)
            concept.update_item(seen_item, time)
            for (_, child) in item.children:
                if self.can_see(actor, child):
                    self.transfer(self.item[child], actor, time)
        # If a Room, add SharedThings & Doors to the Actor's Concept.
        if item.room:
            for shared_tag in self.item[str(item)].shared:
                self.transfer(self.item[shared_tag], actor, time)
            for door_tag in self.doors(str(item)):
                self.transfer(self.item[door_tag], actor, time)
        
    def transfer_out(self, item, actor, time):
        "Remove the Item from the Actor's Concept."
        concept = self.concept[actor]
        if str(item) in concept.item:
            missing_item = copy.deepcopy(concept.item[str(item)])
            missing_item.link = 'of'
            missing_item.parent = '@cosmos'
            concept.update_item(missing_item, time)

    def undo(self, action_id):
        'Revert the World back to the start time of the specified Action.'
        new_ids = []
        for i in self.act:
            new_ids.append((i, self.act[i].start))
        ids_times = sorted(new_ids, key=operator.itemgetter(1))
        target_time = self.act[action_id].start
        while len(ids_times) > 0 and ids_times[-1][1] >= target_time:
            (last_id, _) = ids_times.pop()
            last_action = self.act.pop(last_id)
            last_action.undo(self)
        self.back_up_clock(target_time)


########NEW FILE########
