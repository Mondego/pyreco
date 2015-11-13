__FILENAME__ = defaultrobots
class Robot:
    def act(self, game):
        return ['guard']

########NEW FILE########
__FILENAME__ = game
import inspect
import random
import sys
import traceback
import imp
###
import rg
import defaultrobots
from settings import settings, AttrDict


def init_settings(map_data):
    global settings
    settings.spawn_coords = map_data['spawn']
    settings.obstacles = map_data['obstacle']
    settings.start1 = map_data['start1']
    settings.start2 = map_data['start2']
    rg.set_settings(settings)

class Player:
    def __init__(self, code=None, robot=None):
        if code is not None:
            self._mod = imp.new_module('usercode%d' % id(self))
            exec code in self._mod.__dict__
            self._robot = None
        elif robot is not None:
            self._mod = None
            self._robot = robot
        else:
            raise Exception('you need to provide code or a robot')

    def get_robot(self):
        if self._robot is not None:
            return self._robot

        mod = defaultrobots
        if self._mod is not None:
            if hasattr(self._mod, 'Robot'):
                if inspect.isclass(getattr(self._mod, 'Robot')):
                    mod = self._mod

        self._robot = getattr(mod, 'Robot')()
        return self._robot

class InternalRobot:
    def __init__(self, location, hp, player_id, robot_id, field):
        self.location = location
        self.hp = hp
        self.player_id = player_id
        self.robot_id = robot_id
        self.field = field

    def __repr__(self):
        return '<%s: player: %d, hp: %d>' % (
            self.location, self.player_id, self.hp
        )

    @staticmethod
    def parse_command(action):
        return (action[0], action[1:])

    def is_valid_action(self, action):
        global settings

        cmd, params = InternalRobot.parse_command(action)
        if not cmd in settings.valid_commands:
            return False

        if cmd == 'move' or cmd == 'attack':
            if not self.movable_loc(params[0]):
                return False

        return True

    def issue_command(self, action, actions):
        cmd, params = InternalRobot.parse_command(action)
        if cmd == 'move' or cmd == 'attack':
            getattr(self, 'call_' + cmd)(params[0], actions)
        if cmd == 'suicide':
            self.call_suicide(actions)

    def get_robots_around(self, loc):
        locs_around = rg.locs_around(loc, filter_out=['obstacle', 'invalid'])
        locs_around.append(loc)

        robots = [self.field[x] for x in locs_around]
        return [x for x in robots if x not in (None, self)]

    def movable_loc(self, loc):
        good_around = rg.locs_around(
            self.location, filter_out=['invalid', 'obstacle'])
        return loc in good_around

    def is_collision(self, loc, robot, cmd, params, actions, move_exclude):
        if cmd == 'suicide':
            return False
        if cmd != 'move':
            return robot.location == loc
        if params[0] == loc:
            return robot not in move_exclude
        elif robot.location == loc:
            if params[0] == self.location:
                return True
            move_exclude = move_exclude | set([robot])
            return (len(self.get_collisions(params[0], actions, move_exclude)) > 0)
        return False

    def get_collisions(self, loc, action_table, move_exclude=None):
        if move_exclude is None:
            move_exclude = set()

        collisions = []
        nearby_robots = self.get_robots_around(loc)
        nearby_robots = set(nearby_robots) - move_exclude

        for robot in nearby_robots:
            cmd, params = InternalRobot.parse_command(action_table[robot])
            if self.is_collision(loc, robot, cmd, params, action_table, move_exclude):
                collisions.append((robot, cmd, params))
        return collisions

    @staticmethod
    def damage_robot(robot, damage):
        robot.hp -= int(damage)

    def call_move(self, loc, action_table):
        global settings

        loc = tuple(map(int, loc))
        collisions = self.get_collisions(loc, action_table)

        for robot, cmd, params in collisions:
            if robot.player_id != self.player_id:
                if cmd != 'guard':
                    InternalRobot.damage_robot(robot, settings.collision_damage)
                if cmd != 'move':
                    InternalRobot.damage_robot(self, settings.collision_damage)

        if len(collisions) == 0:
            self.location = loc

    # should only be called after all robots have been moved
    def call_attack(self, loc, action_table, damage=None):
        global settings

        damage = int(damage or random.randint(*settings.attack_range))

        robot = self.field[loc]
        if not robot or robot.player_id == self.player_id:
            return

        cmd, params = InternalRobot.parse_command(action_table[robot])
        InternalRobot.damage_robot(robot,
                                   damage if cmd != 'guard' else damage / 2)

    def call_suicide(self, action_table):
        self.hp = 0
        self.call_attack(self.location, action_table, damage=settings.suicide_damage)
        for loc in rg.locs_around(self.location):
            self.call_attack(loc, action_table, damage=settings.suicide_damage)

# just to make things easier
class Field:
    def __init__(self, size):
        self.field = [[None for x in range(size)] for y in range(size)]

    def __getitem__(self, point):
        try:
            return self.field[int(point[1])][int(point[0])]
        except TypeError:
            print point[1], point[0]

    def __setitem__(self, point, v):
        try:
            self.field[int(point[1])][int(point[0])] = v
        except TypeError:
            print point[1], point[0]

class Game:
    def __init__(self, player1, player2, record_turns=False, unit_testing=False):
        self._players = (player1, player2)
        self.turns = 0
        self._robots = []
        self._field = Field(settings.board_size)
        self._unit_testing = unit_testing
        self._id_inc = 0

        self._record = record_turns
        if self._record:
            self.history = [[] for i in range(2)]
            self.action_at = dict((x, dict()) for x in range(settings.max_turns))
            self.last_locs = {}
            self.last_hps = {}

        self.spawn_starting()

    def get_robot_id(self):
        ret = self._id_inc
        self._id_inc += 1
        return ret

    def spawn_starting(self):
        global settings
        for coord in settings.start1:
            self.spawn_robot(0, coord)
        for coord in settings.start2:
            self.spawn_robot(1, coord)

    def build_game_info(self):
        global settings
        return AttrDict({
            'robots': dict((
                y.location,
                AttrDict(dict(
                    (x, getattr(y, x)) for x in
                    (settings.exposed_properties + settings.player_only_properties)
                ))
            ) for y in self._robots),
            'turn': self.turns,
        })

    def build_players_game_info(self):
        game_info_copies = [self.build_game_info(), self.build_game_info()]

        for i in range(2):
            for loc, robot in game_info_copies[i].robots.iteritems():
                if robot.player_id != i:
                    for property in settings.player_only_properties:
                        del robot[property]
        return game_info_copies

    def make_robots_act(self):
        global settings

        game_info_copies = self.build_players_game_info()
        actions = {}

        for robot in self._robots:
            user_robot = self._players[robot.player_id].get_robot()
            for prop in settings.exposed_properties + settings.player_only_properties:
                setattr(user_robot, prop, getattr(robot, prop))
            try:
                next_action = user_robot.act(game_info_copies[robot.player_id])
                if not robot.is_valid_action(next_action):
                    raise Exception('Bot %d: %s is not a valid action from %s' % (robot.player_id + 1, str(next_action), robot.location))
            except Exception:
                traceback.print_exc(file=sys.stdout)
                next_action = ['guard']
            actions[robot] = next_action

        commands = list(settings.valid_commands)
        commands.remove('guard')
        commands.remove('move')
        commands.insert(0, 'move')

        self.last_locs = {}
        self.last_hps = {}
        for cmd in commands:
            for robot, action in actions.iteritems():
                if action[0] != cmd:
                    continue

                old_loc = robot.location
                self.last_hps[old_loc] = robot.hp  # save hp before actions are processed
                try:
                    robot.issue_command(action, actions)
                except Exception:
                    traceback.print_exc(file=sys.stdout)
                    actions[robot] = ['guard']
                if robot.location != old_loc:
                    if self._field[old_loc] is robot:
                        self._field[old_loc] = None
                        self.last_locs[robot.location] = old_loc
                    self._field[robot.location] = robot
                else:
                    self.last_locs[robot.location] = robot.location
        return actions

    def robot_at_loc(self, loc):
        return self._field[loc]

    def spawn_robot(self, player_id, loc):
        if self.robot_at_loc(loc) is not None:
            return False

        robot_id = self.get_robot_id()
        robot = InternalRobot(loc, settings.robot_hp, player_id, robot_id, self._field)
        self._robots.append(robot)
        self._field[loc] = robot
        if self._record:
            self.action_at[self.turns][loc] = {
                'name': 'spawn',
                'target': None,
                'hp': robot.hp,
                'hp_end': robot.hp,
                'loc': loc,
                'loc_end': loc,
                'player': player_id
            }
        return True

    def spawn_robot_batch(self):
        global settings

        locs = random.sample(settings.spawn_coords, settings.spawn_per_player * 2)
        for player_id in (0, 1):
            for i in range(settings.spawn_per_player):
                self.spawn_robot(player_id, locs.pop())

    def clear_spawn_points(self):
        for loc in settings.spawn_coords:
            if self._field[loc] is not None:
                self._robots.remove(self._field[loc])
                self._field[loc] = None
                if self._record:
                    old_loc = self.last_locs.get(loc, loc)
                    # simulate death by making this robot end with 0 HP in the actions log
                    self.action_at[self.turns][old_loc] = {'hp_end': 0}

    def remove_dead(self):
        to_remove = [x for x in self._robots if x.hp <= 0]
        for robot in to_remove:
            self._robots.remove(robot)
            if self._field[robot.location] == robot:
                self._field[robot.location] = None

    def make_history(self, actions):
        global settings

        robots = [[] for i in range(2)]
        for robot in self._robots:
            robot_info = []
            for prop in settings.exposed_properties:
                if prop != 'player_id':
                    robot_info.append(getattr(robot, prop))
            if robot in actions:
                robot_info.append(actions[robot])
            robots[robot.player_id].append(robot_info)
        return robots

    def run_turn(self):
        global settings

        actions = self.make_robots_act()
        self.remove_dead()

        if not self._unit_testing:
            if self.turns % settings.spawn_every == 0:
                self.clear_spawn_points()
                self.spawn_robot_batch()

        if self._record:
            round_history = self.make_history(actions)
            for i in (0, 1):
                self.history[i].append(round_history[i])

            for robot, action in actions.iteritems():
                loc = self.last_locs.get(robot.location, robot.location)
                log_action = self.action_at[self.turns].get(loc, {})
                hp_start = self.last_hps.get(loc, robot.hp)
                log_action['name'] = log_action.get('name', action[0])
                log_action['target'] = action[1] if len(action) > 1 else None
                log_action['hp'] = log_action.get('hp', hp_start)
                log_action['hp_end'] = log_action.get('hp_end', robot.hp)
                log_action['loc'] = log_action.get('loc', loc)
                log_action['loc_end'] = log_action.get('loc_end', robot.location)
                log_action['player'] = log_action.get('player', robot.player_id)
                self.action_at[self.turns][loc] = log_action

        self.turns += 1

    def get_scores(self):
        scores = [0, 0]
        for robot in self._robots:
            scores[robot.player_id] += 1
        return scores

    def get_robot_actions(self, turn):
        global settings
        if turn in self.action_at:
            return self.action_at[turn]
        elif turn <= 0:
            return self.action_at[1]
        else:
            return self.action_at[settings.max_turns-1]

########NEW FILE########
__FILENAME__ = mapeditor
#!/usr/bin/env python2

import ast
import Tkinter
import sys

from settings import settings, AttrDict

BLOCKSIZE = 20
PADDING = 4

color_mapping = {
    'a': ('black', 'obstacle'),
    's': ('#ddd', None),
    'g': ('darkgreen', 'spawn'),
    't': ('pink', 'start1'),
    'h': ('lightgreen', 'start2'),
    'r': ('darkred', None),
}

def print_instructions():
    print '''
usage: python mapeditor.py [<starting map file>]

I made this map editor to use for myself. Therefore, it might not seem
very user-friendly, but it's not that hard. There are just a bunch of
keyboard shortcuts to use.

Game-related colors
===================
[a] paint black (obstacle)
[s] erase (walking space)
[g] paint green (spawn point)
[t] paint pink (starting robot for p1)
[h] paint light green (starting robot for p2)

Just for yourself
=================
[r] paint red

Other functions
===============
[d] fill board with selected color
[f] save map data to map file provided or newmap.py by default
[i] invert black and white colors
'''

class MapEditor:
    def __init__(self, blocksize, padding, map_file="newmap.py"):
        global settings

        self._blocksize = blocksize
        self._padding = padding
        self._map_file = map_file
        self.make_canvas()

    def make_canvas(self):
        global settings

        root = Tkinter.Tk()
        size = (self._blocksize + self._padding) * settings.board_size + self._padding * 2 + 40

        self._canvas = Tkinter.Canvas(root, width=size, height=size)
        self._rect_items = []
        self._colors = []
        self._pressed = False

        self.prepare_backdrop(size)
        self.load_map()
        self.set_color('black')
        self.bind_events()

        self._canvas.pack()
        root.title('robot game map editor')
        root.mainloop()

    def prepare_backdrop(self, size):
        for y in range(settings.board_size):
            for x in range(settings.board_size):
                item = self._canvas.create_rectangle(
                    x * (self._blocksize + self._padding) + self._padding + 20, y * (self._blocksize + self._padding) + self._padding + 20,
                    (x+1) * (self._blocksize + self._padding) + 20, (y+1) * (self._blocksize + self._padding) + 20,
                    fill='#ddd',
                    width=0)
                self._colors.append('#ddd')
                self._rect_items.append(item)
        self._bar = self._canvas.create_rectangle(0, 0, size, 15, width=0)

    def set_color(self, color):
        self._current_color = color
        self._canvas.itemconfigure(self._bar, fill=self._current_color)

    def bind_events(self):
        self._canvas.bind_all('<Button-1>', self.click_handler)
        self._canvas.bind_all('<B1-Motion>', self.move_handler)
        self._canvas.bind_all('<ButtonRelease-1>', self.release_handler)
        self._canvas.bind_all('<Key>', self.key_handler)

    def paint_square(self, tk_event=None, item_id=None):
        if tk_event is None and item_id is None:
            raise Exception('must supply either tk_event or item_id')

        if item_id is None:
            try:
                widget = tk_event.widget.find_closest(tk_event.x, tk_event.y)
                item_id = widget[0] - 1
            except:
                return

        if 0 <= item_id < len(self._rect_items):
            self._canvas.itemconfigure(self._rect_items[item_id], fill=self._current_color)
            self._colors[item_id] = self._current_color

    def click_handler(self, event):
        self._pressed = True
        self.paint_square(tk_event=event)

    def move_handler(self, event):
        if self._pressed:
            self.paint_square(tk_event=event)

    def release_handler(self, event):
        self._pressed = False

    def paint_all(self):
        for i, item in enumerate(self._rect_items):
            self.paint_square(item_id=i)
            self._canvas.itemconfigure(item, fill=self._current_color)

    def load_map(self):
        if self._map_file is None:
            return

        map_data = ast.literal_eval(open(self._map_file).read())

        label_mapping = dict((v, k) for k, v in color_mapping.values() if v is not None)

        for label, color in label_mapping.iteritems():
            if label not in map_data:
                continue

            self.set_color(color)
            for coord in map_data[label]:
                self.paint_square(item_id=coord[0] + settings.board_size * coord[1])

    def save_map(self):
        global settings

        coords = {}
        label_mapping = dict(color_mapping.values())

        for color, label in label_mapping.iteritems():
            if label is not None:
                coords[label] = []

        for i, color in enumerate(self._colors):
            if color in label_mapping and label_mapping[color] is not None:
                coords[label_mapping[color]].append((i % settings.board_size, int(i / settings.board_size)))

        with open(self._map_file, 'w') as f:
            f.write(str(coords))
            print 'saved!'

    def invert_colors(self):
        old_color = self._current_color
        for i, c in enumerate(self._colors):
            if c == '#ddd':
                self._current_color = 'black'
            elif c == 'black':
                self._current_color = '#ddd'

            self.paint_square(item_id=i)
            self._colors[i] = self._current_color
        self._current_color = old_color

    def key_handler(self, event):
        global color_mapping

        if event.char in color_mapping:
            self.set_color(color_mapping[event.char][0])

        func_map = {
            'd': self.paint_all,
            'f': self.save_map,
            'i': self.invert_colors
        }

        if event.char in func_map:
            func_map[event.char]()

if __name__ == '__main__':
    print_instructions()
    if len(sys.argv) > 1:
        MapEditor(BLOCKSIZE, PADDING, sys.argv[1])
    else:
        MapEditor(BLOCKSIZE, PADDING)

########NEW FILE########
__FILENAME__ = default
{'start1':[],'start2':[],'spawn':[(7,1),(8,1),(9,1),(10,1),(11,1),(5,2),(6,2),(12,2),(13,2),(3,3),(4,3),(14,3),(15,3),(3,4),(15,4),(2,5),(16,5),(2,6),(16,6),(1,7),(17,7),(1,8),(17,8),(1,9),(17,9),(1,10),(17,10),(1,11),(17,11),(2,12),(16,12),(2,13),(16,13),(3,14),(15,14),(3,15),(4,15),(14,15),(15,15),(5,16),(6,16),(12,16),(13,16),(7,17),(8,17),(9,17),(10,17),(11,17)],'obstacle':[(0,0),(1,0),(2,0),(3,0),(4,0),(5,0),(6,0),(7,0),(8,0),(9,0),(10,0),(11,0),(12,0),(13,0),(14,0),(15,0),(16,0),(17,0),(18,0),(0,1),(1,1),(2,1),(3,1),(4,1),(5,1),(6,1),(12,1),(13,1),(14,1),(15,1),(16,1),(17,1),(18,1),(0,2),(1,2),(2,2),(3,2),(4,2),(14,2),(15,2),(16,2),(17,2),(18,2),(0,3),(1,3),(2,3),(16,3),(17,3),(18,3),(0,4),(1,4),(2,4),(16,4),(17,4),(18,4),(0,5),(1,5),(17,5),(18,5),(0,6),(1,6),(17,6),(18,6),(0,7),(18,7),(0,8),(18,8),(0,9),(18,9),(0,10),(18,10),(0,11),(18,11),(0,12),(1,12),(17,12),(18,12),(0,13),(1,13),(17,13),(18,13),(0,14),(1,14),(2,14),(16,14),(17,14),(18,14),(0,15),(1,15),(2,15),(16,15),(17,15),(18,15),(0,16),(1,16),(2,16),(3,16),(4,16),(14,16),(15,16),(16,16),(17,16),(18,16),(0,17),(1,17),(2,17),(3,17),(4,17),(5,17),(6,17),(12,17),(13,17),(14,17),(15,17),(16,17),(17,17),(18,17),(0,18),(1,18),(2,18),(3,18),(4,18),(5,18),(6,18),(7,18),(8,18),(9,18),(10,18),(11,18),(12,18),(13,18),(14,18),(15,18),(16,18),(17,18),(18,18)]}

########NEW FILE########
__FILENAME__ = test
{'spawn': [], 'start2': [(6, 2), (11, 2), (10, 4), (12, 4), (16, 6), (2, 7), (3, 7), (4, 7), (17, 7), (16, 8), (14, 9), (3, 11), (5, 12), (5, 14), (7, 15), (15, 15), (10, 16), (12, 16)], 'start1': [(9, 2), (14, 3), (9, 7), (8, 8), (9, 8), (12, 8), (2, 9), (7, 9), (8, 9), (10, 9), (11, 9), (13, 9), (15, 9), (2, 10), (9, 10), (9, 11), (4, 15)], 'obstacle': []}
########NEW FILE########
__FILENAME__ = collide-attack
{'spawn': [], 'start2': [(9, 9), (10, 9)], 'start1': [(9, 8)], 'obstacle': []}
########NEW FILE########
__FILENAME__ = suicide
{'spawn': [], 'start2': [(10, 7)], 'start1': [(10, 6), (9, 7), (11, 7), (10, 8)], 'obstacle': []}
########NEW FILE########
__FILENAME__ = render
import Tkinter
import game
import rg
import time

def millis():
    return int(time.time() * 1000)

def rgb_to_hex(r, g, b, normalized=True):
    if normalized:
        return '#%02x%02x%02x' % (r*255, g*255, b*255)
    else:
        return '#%02x%02x%02x' % (r, g, b)

def blend_colors(color1, color2, weight):
    r1, g1, b1 = color1
    r2, g2, b2 = color2
    r = r1 * weight + r2 * (1-weight)
    g = g1 * weight + g2 * (1-weight)
    b = b1 * weight + b2 * (1-weight)
    return (r, g, b)

class HighlightSprite:
    def __init__(self, loc, target, render):
        self.location = loc
        self.target = target
        self.renderer = render
        self.hlt_square = None
        self.target_square = None

    def clear(self):
        self.renderer.remove_object(self.hlt_square)
        self.renderer.remove_object(self.target_square)
        self.hlt_square = None
        self.target_square = None

    def animate(self, delta=0):
        # blink like a cursor
        if self.location is not None:
            if delta < 0.5:
                if self.hlt_square is None:
                    color = rgb_to_hex(*self.renderer._settings.highlight_color)
                    self.hlt_square = self.renderer.draw_grid_object(self.location, fill=color, layer=2, width=0)
                if self.target is not None and self.target_square is None:
                    color = rgb_to_hex(*self.renderer._settings.target_color)
                    self.target_square = self.renderer.draw_grid_object(self.target, fill=color, layer=2, width=0)
            else:
                self.clear()

class RobotSprite:
    def __init__(self, action_info, render):
        self.location = action_info['loc']
        self.location_next = action_info['loc_end']
        self.action = action_info['name']
        self.target = action_info['target']
        self.hp = max(0, action_info['hp'])
        self.hp_next = max(0, action_info['hp_end'])
        self.id = action_info['player']
        self.renderer = render
        self.animation_offset = (0, 0)

        # Tkinter objects
        self.square = None
        self.overlay = None
        self.text = None

    def animate(self, delta=0):
        """Animate this sprite

           delta is between 0 and 1. it tells us how far along to render (0.5 is halfway through animation)
                this allows animation logic to be separate from timing logic
        """
        # fix delta to between 0 and 1
        delta = max(0, min(delta, 1))
        bot_color = self.compute_color(self.id, self.hp)
        # if spawn, fade in
        if self.action == 'spawn':
            bot_color = blend_colors(bot_color, self.renderer._settings.normal_color, delta)
        # if dying, fade out
        elif self.hp_next <= 0:
            bot_color = blend_colors(bot_color, self.renderer._settings.normal_color, 1-delta)
        bot_color = rgb_to_hex(*bot_color)
        x, y = self.location
        self.animation_offset = (0, 0)
        if self.action == 'move':
            # if normal move, start at bot location and move to next location
            # (note that first half of all move animations is the same)
            if delta < 0.5 or self.location_next == self.target:
                x, y = self.location
                tx, ty = self.target
            # if we're halfway through this animation AND the movement didn't succeed, reverse it (bounce back)
            else:
                # starting where we wanted to go
                x, y = self.target
                # and ending where we are now
                tx, ty = self.location
            dx = tx - x
            dy = ty - y
            off_x = dx*delta*self.renderer._blocksize
            off_y = dy*delta*self.renderer._blocksize
            self.animation_offset = (off_x, off_y)
        elif self.action == 'attack':
            if self.overlay is None and self.renderer.show_arrows.get():
                offset = (self.renderer._blocksize/2, self.renderer._blocksize/2)
                self.overlay = self.renderer.draw_line(self.location, self.target, layer=4, fill='orange', offset=offset, width=3.0, arrow=Tkinter.LAST)
            elif self.overlay is not None and not self.renderer.show_arrows.get():
                self.renderer.remove_object(self.overlay)
                self.overlay = None
        elif self.action == 'guard':
            pass
        elif self.action == 'suicide':
            pass
        self.draw_bot(delta, (x, y), bot_color)
        self.draw_bot_hp(delta, (x, y))

    def compute_color(self, player, hp):
        max_hp = float(self.renderer._settings.robot_hp + 20)
        r, g, b = self.renderer._settings.colors[player]
        hp = float(hp + 20)
        r *= hp / max_hp
        g *= hp / max_hp
        b *= hp / max_hp
        r = max(r, 0)
        g = max(g, 0)
        b = max(b, 0)
        return (r, g, b)

    def draw_bot(self, delta, loc, color):
        x, y = self.renderer.grid_to_xy(loc)
        rx, ry = self.renderer.square_bottom_corner((x, y))
        ox, oy = self.animation_offset
        if self.square is None:
            self.square = self.renderer.draw_grid_object(self.location, type="circle", layer=3, fill=color, width=0)
        self.renderer._win.itemconfig(self.square, fill=color)
        self.renderer._win.coords(self.square, (x+ox, y+oy, rx+ox, ry+oy))

    def draw_bot_hp(self, delta, loc):
        x, y = self.renderer.grid_to_xy(loc)
        ox, oy = self.animation_offset
        tex_color = "#888"
        val = int(self.hp * (1-delta) + self.hp_next * delta)
        if self.text is None:
            self.text = self.renderer.draw_text(self.location, val, tex_color)
        self.renderer._win.itemconfig(self.text, text=val)
        self.renderer._win.coords(self.text, (x+ox+10, y+oy+10))

    def clear(self):
        self.renderer.remove_object(self.square)
        self.renderer.remove_object(self.overlay)
        self.renderer.remove_object(self.text)
        self.square = None
        self.overlay = None
        self.text = None

class Render:
    def __init__(self, game_inst, settings, animations, block_size=25):
        self._settings = settings
        self.animations = animations
        self._blocksize = block_size
        self._winsize = block_size * self._settings.board_size + 40
        self._game = game_inst
        self._paused = True
        self._layers = {}

        self._master = Tkinter.Tk()
        self._master.title('Robot Game')

        width = self._winsize
        height = self._winsize + self._blocksize * 11/4
        self._win = Tkinter.Canvas(self._master, width=width, height=height)
        self._win.pack()

        self.prepare_backdrop(self._win)
        self._label = self._win.create_text(
            self._blocksize/2, self._winsize + self._blocksize/2,
            anchor='nw', font='TkFixedFont', fill='white')

        self.create_controls(self._win, width, height)

        self._turn = 1

        self._highlighted = None
        self._highlighted_target = None

        # Animation stuff (also see #render heading in settings.py)
        self._sprites = []
        self._highlight_sprite = None
        self._t_paused = 0
        self._t_frame_start = 0
        self._t_next_frame = 0
        self.slider_delay = 0
        self.update_frame_timing()

        self.draw_background()
        self.update_title()
        self.update_sprites_new_turn()
        self.paint()

        self.callback()
        self._win.mainloop()

    def remove_object(self, obj):
        if obj is not None:
            self._win.delete(obj)

    def change_turn(self, turns):
        self._turn = min(max(self._turn + turns, 1), self._game.turns)
        self.update_title()
        self._highlighted = None
        self._highlighted_target = None
        self.update_sprites_new_turn()
        self.paint()

    def toggle_pause(self):
        self._paused = not self._paused
        print "paused" if self._paused else "unpaused"
        self._toggle_button.config(text=u'\u25B6' if self._paused else u'\u25FC')
        now = millis()
        if self._paused:
            self._t_paused = now
        else:
            if self._t_paused != 0:
                self.update_frame_timing(now - (self._t_paused - self._t_frame_start))
            else:
                self.update_frame_timing(now)

    def update_frame_timing(self, tstart=None):
        if tstart is None:
            tstart = millis()
        self._t_frame_start = tstart
        self._t_next_frame = tstart + self.slider_delay

    def create_controls(self, win, width, height):
        def change_turn(turns):
            if not self._paused:
                self.toggle_pause()
            self.change_turn(turns)

        def prev():
            change_turn(-1)

        def next():
            change_turn(+1)

        def restart():
            change_turn((-self._turn)+1)

        def pause():
            self.toggle_pause()

        def onclick(event):
            x = (event.x - 20) / self._blocksize
            y = (event.y - 20) / self._blocksize
            loc = (x, y)
            if loc[0] >= 0 and loc[1] >= 0 and loc[0] < self._settings.board_size and loc[1] < self._settings.board_size:
                if loc == self._highlighted:
                    self._highlighted = None
                else:
                    self._highlighted = loc
                action = self._game.get_robot_actions(self.current_turn()).get(loc)
                if action is not None:
                    self._highlighted_target = action.get("target", None)
                else:
                    self._highlighted_target = None
                self.update_highlight_sprite()
                self.update_title()

        self._master.bind("<Button-1>", lambda e: onclick(e))
        self._master.bind('<Left>', lambda e: prev())
        self._master.bind('<Right>', lambda e: next())
        self._master.bind('<space>', lambda e: pause())

        self.show_arrows = Tkinter.BooleanVar()

        frame = Tkinter.Frame()
        win.create_window(width, height, anchor=Tkinter.SE, window=frame)

        arrows_box = Tkinter.Checkbutton(frame, text="Show Arrows", variable=self.show_arrows, command=self.paint)
        arrows_box.pack()

        self._toggle_button = Tkinter.Button(frame, text=u'\u25B6', command=self.toggle_pause)
        self._toggle_button.pack(side='left')

        prev_button = Tkinter.Button(frame, text='<', command=prev)
        prev_button.pack(side='left')

        next_button = Tkinter.Button(frame, text='>', command=next)
        next_button.pack(side='left')

        restart_button = Tkinter.Button(frame, text='<<', command=restart)
        restart_button.pack(side='left')

        self._time_slider = Tkinter.Scale(frame,
                                          from_=-self._settings.turn_interval/2,
                                          to_=self._settings.turn_interval/2,
                                          orient=Tkinter.HORIZONTAL, borderwidth=0)
        self._time_slider.pack(fill=Tkinter.X)
        self._time_slider.set(0)

    def prepare_backdrop(self, win):
        self._win.create_rectangle(0, 0, self._winsize, self._winsize + self._blocksize, fill='#555', width=0)
        self._win.create_rectangle(0, self._winsize, self._winsize, self._winsize + self._blocksize * 15/4, fill='#333', width=0)
        for x in range(self._settings.board_size):
            for y in range(self._settings.board_size):
                rgb = self._settings.normal_color if "normal" in rg.loc_types((x, y)) else self._settings.obstacle_color
                self.draw_grid_object((x, y), fill=rgb_to_hex(*rgb), layer=1, width=0)

    def draw_grid_object(self, loc, type="square", layer=0, **kargs):
        layer_id = 'layer %d' % layer
        self._layers[layer_id] = None
        tags = kargs.get("tags", [])
        tags.append(layer_id)
        kargs["tags"] = tags
        x, y = self.grid_to_xy(loc)
        rx, ry = self.square_bottom_corner((x, y))
        if type == "square":
            item = self._win.create_rectangle(
                x, y, rx, ry,
                **kargs)
        elif type == "circle":
            item = self._win.create_oval(
                x, y, rx, ry,
                **kargs)
        return item

    def update_layers(self):
        for layer in self._layers:
            self._win.tag_raise(layer)

    def draw_text(self, loc, text, color=None):
        layer_id = 'layer %d' % 9
        self._layers[layer_id] = None
        x, y = self.grid_to_xy(loc)
        item = self._win.create_text(
            x+10, y+10,
            text=text, font='TkFixedFont', fill=color, tags=[layer_id])
        return item

    def draw_line(self, src, dst, offset=(0, 0), layer=0, **kargs):
        layer_id = 'layer %d' % layer
        self._layers[layer_id] = None
        tags = kargs.get("tags", [])
        tags.append(layer_id)
        kargs["tags"] = tags
        ox, oy = offset
        srcx, srcy = self.grid_to_xy(src)
        dstx, dsty = self.grid_to_xy(dst)

        item = self._win.create_line(srcx+ox, srcy+oy, dstx+ox, dsty+oy, **kargs)
        return item

    def current_turn(self):
        return min(self._settings.max_turns-1, self._turn)

    def update_title(self):
        turns = self.current_turn()
        max_turns = self._settings.max_turns
        red = len(self._game.history[0][self._turn - 1])
        green = len(self._game.history[1][self._turn - 1])
        info = ''
        currentAction = ''
        if self._highlighted is not None:
            squareinfo = self.get_square_info(self._highlighted)
            if 'obstacle' in squareinfo:
                info = 'Obstacle'
            elif 'bot' in squareinfo:
                actioninfo = squareinfo[1]
                hp = actioninfo['hp']
                team = actioninfo['player']
                info = '%s Bot: %d HP' % (['Red', 'Green'][team], hp)
                if actioninfo.get('name') is not None:
                    currentAction += 'Current Action: %s' % (actioninfo['name'],)
                    if self._highlighted_target is not None:
                        currentAction += ' to %s' % (self._highlighted_target,)

        lines = [
            'Red: %d | Green: %d | Turn: %d/%d' % (red, green, turns, max_turns),
            'Highlighted: %s; %s' % (self._highlighted, info),
            currentAction
        ]
        self._win.itemconfig(
            self._label, text='\n'.join(lines))

    def get_square_info(self, loc):
        if loc in self._settings.obstacles:
            return ['obstacle']

        all_bots = self._game.get_robot_actions(self.current_turn())
        if loc in all_bots:
            return ['bot', all_bots[loc]]

        return ['normal']

    def update_slider_value(self):
        v = -self._time_slider.get()
        if v > 0:
            v = v * 20
        self.slider_delay = self._settings.turn_interval + v

    def callback(self):
        self.update_slider_value()
        self.tick()
        self._win.after(int(1000.0 / self._settings.FPS), self.callback)

    def tick(self):
        now = millis()
        # check if frame-update
        if not self._paused:
            if now >= self._t_next_frame:
                self.change_turn(1)
                if self._turn >= self._settings.max_turns:
                    self.toggle_pause()
                else:
                    self.update_frame_timing(self._t_next_frame)
        subframe = float((now - self._t_frame_start) % self.slider_delay) / float(self.slider_delay)
        if self.animations:
            self.paint(subframe)
        else:
            self.paint(0)

    def determine_bg_color(self, loc):
        if loc in self._settings.obstacles:
            return rgb_to_hex(*self._settings.obstacle_color)
        return rgb_to_hex(*self._settings.normal_color)

    def draw_background(self):
        # draw squares
        for y in range(self._settings.board_size):
            for x in range(self._settings.board_size):
                loc = (x, y)
                self.draw_grid_object(loc, fill=self.determine_bg_color(loc), layer=1, width=0)
        # draw text labels
        for y in range(self._settings.board_size):
            self.draw_text((y, 0), str(y), '#888')
            self.draw_text((0, y), str(y), '#888')

    def update_sprites_new_turn(self):
        for sprite in self._sprites:
            sprite.clear()
        self._sprites = []

        self.update_highlight_sprite()
        bots_activity = self._game.get_robot_actions(self._turn)
        try:
            for bot_data in bots_activity.values():
                self._sprites.append(RobotSprite(bot_data, self))
        except:
            print bots_activity
            raw_input()

    def update_highlight_sprite(self):
        need_update = self._highlight_sprite is not None and self._highlight_sprite.location != self._highlighted
        if self._highlight_sprite is not None or need_update:
            self._highlight_sprite.clear()
        self._highlight_sprite = HighlightSprite(self._highlighted, self._highlighted_target, self)

    def paint(self, subframe=0):
        for sprite in self._sprites:
            sprite.animate(subframe if not self._paused else 0)
        if self._highlight_sprite is not None:
            self._highlight_sprite.animate(subframe)
        self.update_layers()

    def grid_to_xy(self, loc):
        x, y = loc
        return (x * self._blocksize + 20, y * self._blocksize + 20)

    def square_bottom_corner(self, square_topleft):
        x, y = square_topleft
        return (x + self._blocksize - 3, y + self._blocksize - 3)

########NEW FILE########
__FILENAME__ = rg
# users will import rg to be able to use robot game functions
from math import sqrt

settings = None

# constants

CENTER_POINT = None

def after_settings():
    global CENTER_POINT
    global settings
    CENTER_POINT = (int(settings.board_size / 2), int(settings.board_size / 2))

def set_settings(s):
    global settings
    settings = s
    after_settings()

##############################

def dist(p1, p2):
    return sqrt((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2)

def wdist(p1, p2):
    return abs(p2[0] - p1[0]) + abs(p2[1] - p1[1])

def memodict(f):
    """ Memoization decorator for a function taking a single argument """
    class memodict(dict):
        def __missing__(self, key):
            ret = self[key] = f(key)
            return ret
    return memodict().__getitem__

@memodict
def loc_types(loc):
    for i in range(2):
        if not (0 <= loc[i] < settings.board_size):
            return set(['invalid'])
    types = set(['normal'])
    if loc in settings.spawn_coords:
        types.add('spawn')
    if loc in settings.obstacles:
        types.add('obstacle')
    return types

@memodict
def _locs_around(loc):
    x, y = loc
    offsets = ((0, 1), (1, 0), (0, -1), (-1, 0))
    return [(x+dx, y+dy) for dx, dy in offsets]

def locs_around(loc, filter_out=None):
    filter_out = set(filter_out or [])
    return [loc for loc in _locs_around(loc) if
            len(filter_out & loc_types(loc)) == 0]

def toward(curr, dest):
    if curr == dest:
        return curr

    x0, y0 = curr
    x, y = dest
    x_diff, y_diff = x - x0, y - y0

    if abs(x_diff) < abs(y_diff):
        return (x0, y0 + y_diff / abs(y_diff))
    return (x0 + x_diff / abs(x_diff), y0)

########NEW FILE########
__FILENAME__ = run
#!/usr/bin/env python2

import os
import ast
import argparse
import itertools

_is_multiprocessing_supported = True
try:
    from multiprocessing import Pool
except ImportError:
    _is_multiprocessing_supported = False  # the OS does not support it. See http://bugs.python.org/issue3770

###
import game
from settings import settings

parser = argparse.ArgumentParser(description="Robot game execution script.")
parser.add_argument("usercode1",
                    help="File containing first robot class definition.")
parser.add_argument("usercode2",
                    help="File containing second robot class definition.")
parser.add_argument("-m", "--map", help="User-specified map file.",
                    default=os.path.join(os.path.dirname(__file__), 'maps/default.py'))
parser.add_argument("-H", "--headless", action="store_true",
                    default=False,
                    help="Disable rendering game output.")
parser.add_argument("-c", "--count", type=int,
                    default=1,
                    help="Game count, default: 1")
parser.add_argument("-A", "--no-animate", action="store_false",
                    default=True,
                    help="Disable animations in rendering.")

def make_player(fname):
    with open(fname) as player_code:
        return game.Player(player_code.read())

def play(players, print_info=True, animate_render=True):
    g = game.Game(*players, record_turns=True)
    for i in xrange(settings.max_turns):
        if print_info:
            print (' running turn %d ' % (g.turns + 1)).center(70, '-')
        g.run_turn()

    if print_info:
        # only import render if we need to render the game;
        # this way, people who don't have tkinter can still
        # run headless
        import render

        render.Render(g, game.settings, animate_render)
        print g.history

    return g.get_scores()

def test_runs_sequentially(args):
    players = [make_player(args.usercode1), make_player(args.usercode2)]
    scores = []
    for i in xrange(args.count):
        scores.append(
            play(players, not args.headless, args.no_animate)
        )
        print scores[-1]
    return scores

def task(data):
    usercode1, usercode2, headless, no_animate = data
    result = play(
        [
            make_player(usercode1),
            make_player(usercode2)
        ],
        not headless,
        no_animate,
    )
    print result
    return result

def test_runs_concurrently(args):
    data = itertools.repeat(
        [
            args.usercode1,
            args.usercode2,
            args.headless,
            args.no_animate,
        ],
        args.count
    )
    return Pool().map(task, data, 1)

if __name__ == '__main__':

    args = parser.parse_args()

    map_name = os.path.join(args.map)
    map_data = ast.literal_eval(open(map_name).read())
    game.init_settings(map_data)

    runner = test_runs_sequentially
    if _is_multiprocessing_supported and args.count > 1:
        runner = test_runs_concurrently
    scores = runner(args)

    if args.count > 1:
        p1won = sum(p1 > p2 for p1, p2 in scores)
        p2won = sum(p2 > p1 for p1, p2 in scores)
        print [p1won, p2won, args.count - p1won - p2won]

########NEW FILE########
__FILENAME__ = settings
settings = {
    # game settings
    'spawn_every': 10,
    'spawn_per_player': 5,
    'board_size': 19,
    'robot_hp': 50,
    'attack_range': (8, 10),
    'collision_damage': 5,
    'suicide_damage': 15,
    'max_turns': 100,

    # rendering
    'FPS': 60,  # frames per second
    'turn_interval': 300,  # milliseconds per turn
    'colors': [(0.9, 0, 0.2), (0, 0.9, 0.2)],
    'obstacle_color': (.2, .2, .2),
    'normal_color': (.9, .9, .9),
    'highlight_color': (0.6, 0.6, 0.6),
    'target_color': (0.6, 0.6, 1),

    # rating systems
    'rating_range': 150,
    'default_rating': 1200,

    # user-scripting
    'max_usercode_time': 150,
    'exposed_properties': ('location', 'hp', 'player_id'),
    'player_only_properties': ('robot_id',),
    'user_obj_types': ('Robot',),
    'valid_commands': ('move', 'attack', 'guard', 'suicide'),
    'user_modules': ('numpy', 'euclid', 'random'),
}

# just change stuff above this line

class AttrDict(dict):
    def __init__(self, *args, **kwargs):
        super(AttrDict, self).__init__(*args, **kwargs)
        self.__dict__ = self
settings = AttrDict(settings)

########NEW FILE########
__FILENAME__ = attack_test
import base
from bots import *
from rgkit import game
from rgkit.settings import settings

class TestAttack(base.BaseTestCase):
    def test_attack_with_floating_point_location(self):
        [bot1], [bot2] = self.simulate(
            [RobotAttackRightWithFloatingLocation, RobotMoveLeft],
            [(10, 10)], [(10, 10)],
            [(12, 10)], [(11, 10)])

        assert(bot1)
        assert(bot2.hp < settings['robot_hp'])

    def test_attack_with_invalid_tuple_length(self):
        [bot1], _ = self.simulate(
            [RobotAttackWithInvalidLocation, RobotGuard],
            [(10, 10)], [(10, 10)],
            [], [])

        assert(bot1)
        self.assertEqual(self._game.history[0][0][0][2], ['guard'])

########NEW FILE########
__FILENAME__ = base
import ast
import pprint
import unittest
from rgkit import game

default_spawn = ast.literal_eval('[(7,1),(8,1),(9,1),(10,1),(11,1),(5,2),(6,2),(12,2),(13,2),(3,3),(4,3),(14,3),(15,3),(3,4),(15,4),(2,5),(16,5),(2,6),(16,6),(1,7),(17,7),(1,8),(17,8),(1,9),(17,9),(1,10),(17,10),(1,11),(17,11),(2,12),(16,12),(2,13),(16,13),(3,14),(15,14),(3,15),(4,15),(14,15),(15,15),(5,16),(6,16),(12,16),(13,16),(7,17),(8,17),(9,17),(10,17),(11,17)]')
default_obstacle = ast.literal_eval('[(0,0),(1,0),(2,0),(3,0),(4,0),(5,0),(6,0),(7,0),(8,0),(9,0),(10,0),(11,0),(12,0),(13,0),(14,0),(15,0),(16,0),(17,0),(18,0),(0,1),(1,1),(2,1),(3,1),(4,1),(5,1),(6,1),(12,1),(13,1),(14,1),(15,1),(16,1),(17,1),(18,1),(0,2),(1,2),(2,2),(3,2),(4,2),(14,2),(15,2),(16,2),(17,2),(18,2),(0,3),(1,3),(2,3),(16,3),(17,3),(18,3),(0,4),(1,4),(2,4),(16,4),(17,4),(18,4),(0,5),(1,5),(17,5),(18,5),(0,6),(1,6),(17,6),(18,6),(0,7),(18,7),(0,8),(18,8),(0,9),(18,9),(0,10),(18,10),(0,11),(18,11),(0,12),(1,12),(17,12),(18,12),(0,13),(1,13),(17,13),(18,13),(0,14),(1,14),(2,14),(16,14),(17,14),(18,14),(0,15),(1,15),(2,15),(16,15),(17,15),(18,15),(0,16),(1,16),(2,16),(3,16),(4,16),(14,16),(15,16),(16,16),(17,16),(18,16),(0,17),(1,17),(2,17),(3,17),(4,17),(5,17),(6,17),(12,17),(13,17),(14,17),(15,17),(16,17),(17,17),(18,17),(0,18),(1,18),(2,18),(3,18),(4,18),(5,18),(6,18),(7,18),(8,18),(9,18),(10,18),(11,18),(12,18),(13,18),(14,18),(15,18),(16,18),(17,18),(18,18)]')
map = {'spawn': default_spawn, 'obstacle': default_obstacle}

class BaseTestCase(unittest.TestCase):
    def simulate(self, robots, locs1, next_locs1, locs2, next_locs2, turns=1):
        players = [game.Player(robot=robot()) for robot in robots]
        map['start1'], map['start2'] = locs1, locs2
        game.init_settings(map)
        self._game = game.Game(*players, unit_testing=True, record_turns=True)

        for i in range(turns):
            self._game.run_turn()

        pprint.pprint(self._game._robots)

        return [[self._game.robot_at_loc(loc) for loc in locs]
                for locs in (next_locs1, next_locs2)]

########NEW FILE########
__FILENAME__ = bots
class RobotSuicide:
    def act(self, game):
        return ['suicide']

class RobotGuard:
    def act(self, game):
        return ['guard']

class RobotAttackRightWithFloatingLocation:
    def act(self, game):
        return [
            'attack',
            (float(self.location[0] + 1),
             float(self.location[1]))
            ]

class RobotAttackWithInvalidLocation:
    def act(self, game):
        return ['attack', ()]

class RobotMoveRight:
    def act(self, game):
        return ['move', (self.location[0] + 1, self.location[1])]

class RobotMoveLeft:
    def act(self, game):
        return ['move', (self.location[0] - 1, self.location[1])]

class RobotSaveState(RobotMoveLeft):
    do_not_move = {}

    def act(self, game):
        if self.robot_id in RobotSaveState.do_not_move:
            return ['guard']
        RobotSaveState.do_not_move[self.robot_id] = True
        return RobotMoveLeft.act(self, game)

class RobotMoveUp:
    def act(self, game):
        return ['move', (self.location[0], self.location[1] - 1)]

class RobotMoveInvalid:
    def act(self, game):
        return ['move', (self.location[0] + 1, self.location[1] + 1)]

class RobotMoveRightAndGuard:
    def act(self, game):
        if (self.location[0] % 2 == 0):
            return ['move', (self.location[0] + 1, self.location[1])]
        else:
            return ['guard']

class RobotMoveInCircle:
    def act(self, game):
        from operator import add

        moves = {0: {0: (1, 0), 1: (0, 1)}, 1: {0: (0, -1), 1: (-1, 0)}}

        dest = tuple(map(add, self.location,
                         moves[self.location[1] % 2][self.location[0] % 2]))

        return ['move', dest]

class RobotMoveInCircleCounterclock:
    def act(self, game):
        from operator import add

        moves = {0: {0: (0, 1), 1: (-1, 0)}, 1: {0: (1, 0), 1: (0, -1)}}

        dest = tuple(map(add, self.location,
                         moves[self.location[1] % 2][self.location[0] % 2]))

        return ['move', dest]

class RobotMoveInCircleCollision:
    def act(self, game):
        from operator import add

        moves = {0: {0: (0, 1), 1: (-1, 0)}, 1: {0: (0, -1), 1: (0, -1)}}

        dest = tuple(map(add, self.location,
                         moves[self.location[1] % 2][self.location[0] % 2]))

        return ['move', dest]

########NEW FILE########
__FILENAME__ = move_test
import base
from bots import *
from rgkit import game
from rgkit.settings import settings

class TestMove(base.BaseTestCase):
    def test_move_no_collision(self):
        [bot1], [bot2] = self.simulate(
            [RobotMoveRight, RobotMoveLeft],
            [(10, 10)], [(11, 10)],
            [(8, 10)], [(7, 10)])

        assert(not self._game.robot_at_loc((10, 10)))
        assert(not self._game.robot_at_loc((8, 10)))
        self.assertEqual(bot1.hp, settings['robot_hp'])
        self.assertEqual(bot2.hp, settings['robot_hp'])

    def test_basic_collision(self):
        [bot1], [bot2] = self.simulate(
            [RobotMoveRight, RobotMoveLeft],
            [(8, 10)], [(8, 10)],
            [(10, 10)], [(10, 10)])

        self.assertEqual(bot1.hp, settings['robot_hp'] - settings['collision_damage'])
        self.assertEqual(bot2.hp, settings['robot_hp'] - settings['collision_damage'])

    def test_try_invalid_move(self):
        [bot1], [bot2] = self.simulate(
            [RobotMoveInvalid, RobotMoveInvalid],
            [(10, 10)], [(10, 10)],
            [(8, 10)], [(8, 10)])

        self.assertEqual(bot1.hp, settings['robot_hp'])
        self.assertEqual(bot2.hp, settings['robot_hp'])

    def test_move_train(self):
        [bot1, bot2, bot3], _ = self.simulate(
            [RobotMoveLeft, RobotMoveLeft],
            [(10, 10), (11, 10), (12, 10)], [(9, 10), (10, 10), (11, 10)],
            [], [])

        assert(not self._game.robot_at_loc((12, 10)))
        assert(bot1)
        assert(bot2)
        assert(bot3)

    def test_train_collision(self):
        [bot1, bot2, bot3], [bot4] = self.simulate(
            [RobotMoveLeft, RobotMoveRight],
            [(10, 10), (11, 10), (12, 10)], [(10, 10), (11, 10), (12, 10)],
            [(8, 10)], [(8, 10)])

        self.assertEqual(bot1.hp, settings['robot_hp'] - settings['collision_damage'])
        self.assertEqual(bot2.hp, settings['robot_hp'])
        self.assertEqual(bot3.hp, settings['robot_hp'])
        self.assertEqual(bot4.hp, settings['robot_hp'] - settings['collision_damage'])

    def test_try_swap(self):
        [bot1], [bot2] = self.simulate(
            [RobotMoveLeft, RobotMoveRight],
            [(9, 9)], [(9, 9)],
            [(8, 9)], [(8, 9)])

        # they shouldn't have swapped
        self.assertEqual(bot1.player_id, 0)
        self.assertEqual(bot2.player_id, 1)

    def test_try_move_in_circle(self):
        [bot1, bot2], [bot3, bot4] = self.simulate(
            [RobotMoveInCircle, RobotMoveInCircle],
            [(9, 9), (8, 8)], [(9, 9), (8, 8)],
            [(8, 9), (9, 8)], [(8, 9), (9, 8)])

        self.assertEqual(bot1.player_id, 0)
        self.assertEqual(bot2.player_id, 0)
        self.assertEqual(bot3.player_id, 1)
        self.assertEqual(bot4.player_id, 1)

    def test_infinite_recursion(self):
        [bot1, bot2], [bot3] = self.simulate(
            [RobotMoveInCircle, RobotMoveUp],
            [(12, 6), (13, 6)], [(12, 6), (13, 6)],
            [(13, 7)], [(13, 7)])

        self.assertEqual(bot1.player_id, 0)
        self.assertEqual(bot2.player_id, 0)
        self.assertEqual(bot3.player_id, 1)

    def test_overlapping_from_collision(self):
        [bot1, bot2], [bot3, bot4] = self.simulate(
            [RobotMoveRight, RobotMoveUp],
            [(9, 10), (10, 10)], [(9, 10), (10, 10)],
            [(11, 11), (11, 12)], [(11, 11), (11, 12)])

        assert(bot1)
        assert(bot2)
        assert(bot3)
        assert(bot4)

    def test_double_collision(self):
        [bot1], [bot2, bot3] = self.simulate(
            [RobotMoveRight, RobotMoveUp],
            [(9, 10)], [(9, 10)],
            [(9, 11), (10, 11)], [(9, 11), (10, 11)])

        assert(bot1.hp == 40)
        assert(bot2.hp == 45)
        assert(bot3.hp == 45)

########NEW FILE########
__FILENAME__ = state_test
import base
from bots import *
from rgkit import game
from rgkit.settings import settings

class TestRobotState(base.BaseTestCase):
    def test_save_robot_state(self):
        [bot1, bot2], [bot3, bot4] = self.simulate(
            [RobotSaveState, RobotSaveState],
            [(9, 9), (9, 10)], [(8, 9), (8, 10)],
            [(9, 11), (9, 12)], [(8, 11), (8, 12)], turns=5)
        assert(bot1)
        assert(bot2)
        assert(bot3)
        assert(bot4)

########NEW FILE########
__FILENAME__ = style_test
import pep8
import unittest
from glob import glob

class TestCodeFormat(unittest.TestCase):
    def test_pep8_conformance(self):
        files = glob('*.py') + glob('test/*.py')

        pep8style = pep8.StyleGuide()
        pep8style.options.ignore += ('E302', 'E501')
        result = pep8style.check_files(files)
        self.assertEqual(result.total_errors, 0, "Found code style errors (and warnings).")

########NEW FILE########
__FILENAME__ = suicide_test
import base
import unittest
from bots import *
from rgkit import game
from rgkit.settings import settings


class SuicideTest(base.BaseTestCase):
    def test_basic_suicide(self):
        _, [bot2] = self.simulate(
            [RobotSuicide, RobotGuard],
            [(10, 10)], [],
            [(11, 10)], [(11, 10)])

        assert(not self._game.robot_at_loc((10, 10)))
        self.assertEqual(bot2.hp, settings['robot_hp'] - settings['suicide_damage'] / 2)

    def test_move_out_of_suicide_range(self):
        _, [bot2] = self.simulate(
            [RobotSuicide, RobotMoveRight],
            [(10, 10)], [],
            [(11, 10)], [(12, 10)])

        assert(not self._game.robot_at_loc((10, 10)))
        self.assertEqual(bot2.hp, settings['robot_hp'])

    def test_move_into_suicide_range(self):
        _, [bot2] = self.simulate(
            [RobotSuicide, RobotMoveLeft],
            [(10, 10)], [],
            [(12, 10)], [(11, 10)])

        assert(not self._game.robot_at_loc((10, 10)))
        self.assertEqual(bot2.hp, settings['robot_hp'] - settings['suicide_damage'])

    def test_collide_and_stay_out_of_suicide_range(self):
        _, [bot2, bot3] = self.simulate(
            [RobotSuicide, RobotMoveRightAndGuard],
            [(10, 10)], [],
            [(8, 10), (9, 10)], [(8, 10), (9, 10)])

        assert(not self._game.robot_at_loc((10, 10)))
        self.assertEqual(bot2.hp, settings['robot_hp'])
        self.assertEqual(bot3.hp, settings['robot_hp'] - settings['suicide_damage'] / 2)

    def test_collide_and_stay_in_suicide_range(self):
        _, [bot2, bot3] = self.simulate(
            [RobotSuicide, RobotMoveRightAndGuard],
            [(9, 10)], [],
            [(10, 10), (11, 10)], [(10, 10), (11, 10)])

        assert(not self._game.robot_at_loc((9, 10)))
        self.assertEqual(bot2.hp, settings['robot_hp'] - settings['suicide_damage'])
        self.assertEqual(bot3.hp, settings['robot_hp'])

    def test_move_into_suicide_bot(self):
        _, [bot2] = self.simulate(
            [RobotSuicide, RobotMoveLeft],
            [(10, 10)], [],
            [(11, 10)], [(10, 10)])

        self.assertEqual(len(self._game._robots), 1)
        self.assertEqual(bot2.hp, settings['robot_hp'] - settings['suicide_damage'])

########NEW FILE########
