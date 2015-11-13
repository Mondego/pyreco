__FILENAME__ = ants
#!/usr/bin/env python

from random import randrange, choice, shuffle, randint, seed, random
from math import sqrt
from collections import deque, defaultdict

from fractions import Fraction
import operator
from game import Game
from copy import deepcopy
try:
    from sys import maxint
except ImportError:
    from sys import maxsize as maxint

ANTS = 0
DEAD = -1
LAND = -2
FOOD = -3
WATER = -4
UNSEEN = -5

PLAYER_ANT = 'abcdefghij'
HILL_ANT = string = 'ABCDEFGHIJ'
PLAYER_HILL = string = '0123456789'
MAP_OBJECT = '?%*.!'
MAP_RENDER = PLAYER_ANT + HILL_ANT + PLAYER_HILL + MAP_OBJECT

HILL_POINTS = 2
RAZE_POINTS = -1

# possible directions an ant can move
AIM = {'n': (-1, 0),
       'e': (0, 1),
       's': (1, 0),
       'w': (0, -1)}

# precalculated sqrt
SQRT = [int(sqrt(r)) for r in range(101)]

class Ants(Game):
    def __init__(self, options=None):
        # setup options
        map_text = options['map']
        self.turns = int(options['turns'])
        self.loadtime = int(options['loadtime'])
        self.turntime = int(options['turntime'])
        self.viewradius = int(options["viewradius2"])
        self.attackradius = int(options["attackradius2"])
        self.spawnradius = int(options["spawnradius2"])
        self.engine_seed = options.get('engine_seed', randint(-maxint-1, maxint))
        self.player_seed = options.get('player_seed', randint(-maxint-1, maxint))
        seed(self.engine_seed)
        self.food_rate = options.get('food_rate', (5,11)) # total food
        if type(self.food_rate) in (list, tuple):
            self.food_rate = randrange(self.food_rate[0], self.food_rate[1]+1)
        self.food_turn = options.get('food_turn', (19,37)) # per turn
        if type(self.food_turn) in (list, tuple):
            self.food_turn = randrange(self.food_turn[0], self.food_turn[1]+1)
        self.food_start = options.get('food_start', (75,175)) # per land area
        if type(self.food_start) in (list, tuple):
            self.food_start = randrange(self.food_start[0], self.food_start[1]+1)
        self.food_visible = options.get('food_visible', (3,5)) # in starting loc
        if type(self.food_visible) in (list, tuple):
            self.food_visible = randrange(self.food_visible[0], self.food_visible[1]+1)
        self.food_extra = Fraction(0,1)

        self.cutoff_percent = options.get('cutoff_percent', 0.85)
        self.cutoff_turn = options.get('cutoff_turn', 150)
        self.hill_kill = False # used to stall cutoff counter

        self.do_attack = {
            'focus':   self.do_attack_focus,
            'closest': self.do_attack_closest,
            'support': self.do_attack_support,
            'damage':  self.do_attack_damage
        }.get(options.get('attack'), self.do_attack_focus)

        self.do_food = {
            'none':      self.do_food_none,
            'random':    self.do_food_random,
            'sections':  self.do_food_sections,
            'symmetric': self.do_food_symmetric
        }.get(options.get('food'), self.do_food_sections)

        self.scenario = options.get('scenario', False)

        map_data = self.parse_map(map_text)

        self.turn = 0
        self.num_players = map_data['num_players']

        self.current_ants = {} # ants that are currently alive
        self.killed_ants = []  # ants which were killed this turn
        self.all_ants = []     # all ants that have been created

        self.all_food = []     # all food created
        self.current_food = {} # food currently in game
        self.pending_food = defaultdict(int)

        self.hills = {}        # all hills
        self.hive_food = [0]*self.num_players # food waiting to spawn for player
        self.hive_history = [[0] for _ in range(self.num_players)]

        # used to cutoff games early
        self.cutoff = None
        self.cutoff_bot = LAND # Can be ant owner, FOOD or LAND
        self.cutoff_turns = 0
        # used to calculate the turn when the winner took the lead
        self.winning_bot = None
        self.winning_turn = 0
        # used to calculate when the player rank last changed
        self.ranking_bots = None
        self.ranking_turn = 0

        # initialize size
        self.height, self.width = map_data['size']
        self.land_area = self.height*self.width - len(map_data['water'])

        # initialize map
        # this matrix does not track hills, just ants
        self.map = [[LAND]*self.width for _ in range(self.height)]

        # initialize water
        for row, col in map_data['water']:
            self.map[row][col] = WATER

        # for new games
        # ants are ignored and 1 ant is created per hill
        # food is ignored
        # for scenarios, the map file is followed exactly

        # initialize hills
        for owner, locs in map_data['hills'].items():
            for loc in locs:
                hill = self.add_hill(loc, owner)
                if not self.scenario or len(map_data['ants']) == 0:
                    self.add_ant(hill)

        if self.scenario:
            # initialize ants
            for player, player_ants in map_data['ants'].items():
                for ant_loc in player_ants:
                    self.add_initial_ant(ant_loc, player)
            # initialize food
            for food in map_data['food']:
                self.add_food(food)
            self.original_map = []
            for map_row in self.map:
                self.original_map.append(map_row[:])
                
        # initialize scores
        # points start at # of hills to prevent negative scores
        self.score = [len(map_data['hills'][0])]*self.num_players
        self.bonus = [0]*self.num_players
        self.score_history = [[s] for s in self.score]

        # used to remember where the ants started
        self.initial_ant_list = sorted(self.current_ants.values(), key=operator.attrgetter('owner'))
        self.initial_access_map = self.access_map()

        # cache used by neighbourhood_offsets() to determine nearby squares
        self.offsets_cache = {}

        # used to track dead players, ants may still exist, but orders are not processed
        self.killed = [False for _ in range(self.num_players)]

        # used to give a different ordering of players to each player
        #   initialized to ensure that each player thinks they are player 0
        self.switch = [[None]*self.num_players + list(range(-5,0)) for i in range(self.num_players)]
        for i in range(self.num_players):
            self.switch[i][i] = 0
        # used to track water and land already reveal to player
        self.revealed = [[[False for col in range(self.width)]
                          for row in range(self.height)]
                         for _ in range(self.num_players)]
        # used to track what a player can see
        self.init_vision()

        # the engine may kill players before the game starts and this is needed to prevent errors
        self.orders = [[] for i in range(self.num_players)]
        

    def distance(self, a_loc, b_loc):
        """ Returns distance between x and y squared """
        d_row = abs(a_loc[0] - b_loc[0])
        d_row = min(d_row, self.height - d_row)
        d_col = abs(a_loc[1] - b_loc[1])
        d_col = min(d_col, self.width - d_col)
        return d_row**2 + d_col**2

    def parse_map(self, map_text):
        """ Parse the map_text into a more friendly data structure """
        ant_list = None
        hill_list = []
        hill_count = defaultdict(int)
        width = height = None
        water = []
        food = []
        ants = defaultdict(list)
        hills = defaultdict(list)
        row = 0
        score = None
        hive = None
        num_players = None

        for line in map_text.split('\n'):
            line = line.strip()

            # ignore blank lines and comments
            if not line or line[0] == '#':
                continue

            key, value = line.split(' ', 1)
            key = key.lower()
            if key == 'cols':
                width = int(value)
            elif key == 'rows':
                height = int(value)
            elif key == 'players':
                num_players = int(value)
                if num_players < 2 or num_players > 10:
                    raise Exception("map",
                                    "player count must be between 2 and 10")
            elif key == 'score':
                score = list(map(int, value.split()))
            elif key == 'hive':
                hive = list(map(int, value.split()))
            elif key == 'm':
                if ant_list is None:
                    if num_players is None:
                        raise Exception("map",
                                        "players count expected before map lines")
                    ant_list = [chr(97 + i) for i in range(num_players)]
                    hill_list = list(map(str, range(num_players)))
                    hill_ant = [chr(65 + i) for i in range(num_players)]
                if len(value) != width:
                    raise Exception("map",
                                    "Incorrect number of cols in row %s. "
                                    "Got %s, expected %s."
                                    %(row, len(value), width))
                for col, c in enumerate(value):
                    if c in ant_list:
                        ants[ant_list.index(c)].append((row,col))
                    elif c in hill_list:
                        hills[hill_list.index(c)].append((row,col))
                        hill_count[hill_list.index(c)] += 1
                    elif c in hill_ant:
                        ants[hill_ant.index(c)].append((row,col))
                        hills[hill_ant.index(c)].append((row,col))
                        hill_count[hill_ant.index(c)] += 1
                    elif c == MAP_OBJECT[FOOD]:
                        food.append((row,col))
                    elif c == MAP_OBJECT[WATER]:
                        water.append((row,col))
                    elif c != MAP_OBJECT[LAND]:
                        raise Exception("map",
                                        "Invalid character in map: %s" % c)
                row += 1

        if score and len(score) != num_players:
            raise Exception("map",
                            "Incorrect score count.  Expected %s, got %s"
                            % (num_players, len(score)))
        if hive and len(hive) != num_players:
            raise Exception("map",
                            "Incorrect score count.  Expected %s, got %s"
                            % (num_players, len(score)))

        if height != row:
            raise Exception("map",
                            "Incorrect number of rows.  Expected %s, got %s"
                            % (height, row))

        # look for ants without hills to invalidate map for a game
        if not self.scenario:
            for hill, count in hill_count.items():
                if count == 0:
                    raise Exception("map",
                                    "Player %s has no starting hills"
                                    % hill)

        return {
            'size':        (height, width),
            'num_players': num_players,
            'hills':       hills,
            'ants':        ants,
            'food':        food,
            'water':       water
        }

    def neighbourhood_offsets(self, max_dist):
        """ Return a list of squares within a given distance of loc

            Loc is not included in the list
            For all squares returned: 0 < distance(loc,square) <= max_dist

            Offsets are calculated so that:
              -height <= row+offset_row < height (and similarly for col)
              negative indicies on self.map wrap thanks to python
        """
        if max_dist not in self.offsets_cache:
            offsets = []
            mx = int(sqrt(max_dist))
            for d_row in range(-mx,mx+1):
                for d_col in range(-mx,mx+1):
                    d = d_row**2 + d_col**2
                    if 0 < d <= max_dist:
                        offsets.append((
                            d_row%self.height-self.height,
                            d_col%self.width-self.width
                        ))
            self.offsets_cache[max_dist] = offsets
        return self.offsets_cache[max_dist]

    def init_vision(self):
        """ Initialise the vision data """
        # calculate and cache vision offsets
        cache = {}
        # all offsets that an ant can see
        locs = set(self.neighbourhood_offsets(self.viewradius))
        locs.add((0,0))
        cache['new'] = list(locs)
        cache['-'] = [list(locs)]

        for d in AIM:
            # determine the previous view
            p_r, p_c = -AIM[d][0], -AIM[d][1]
            p_locs = set(
                (((p_r+r)%self.height-self.height),
                 ((p_c+c)%self.width-self.width))
                for r,c in locs
            )
            cache[d] = [list(p_locs), list(locs-p_locs), list(p_locs-locs)]
        self.vision_offsets_cache = cache

        # create vision arrays
        self.vision = []
        for _ in range(self.num_players):
            self.vision.append([[0]*self.width for __ in range(self.height)])

        # initialise the data based on the initial ants
        self.update_vision()
        self.update_revealed()

    def update_vision(self):
        """ Incrementally updates the vision data """
        for ant in self.current_ants.values():
            if not ant.orders:
                # new ant
                self.update_vision_ant(ant, self.vision_offsets_cache['new'], 1)
            else:
                order = ant.orders[-1]
                if order in AIM:
                    # ant moved
                    self.update_vision_ant(ant, self.vision_offsets_cache[order][1], 1)
                    self.update_vision_ant(ant, self.vision_offsets_cache[order][-1], -1)
                # else: ant stayed where it was
        for ant in self.killed_ants:
            order = ant.orders[-1]
            self.update_vision_ant(ant, self.vision_offsets_cache[order][0], -1)

    def update_vision_ant(self, ant, offsets, delta):
        """ Update the vision data for a single ant

            Increments all the given offsets by delta for the vision
              data for ant.owner
        """
        a_row, a_col = ant.loc
        vision = self.vision[ant.owner]
        for v_row, v_col in offsets:
            # offsets are such that there is never an IndexError
            vision[a_row+v_row][a_col+v_col] += delta

    def update_revealed(self):
        """ Make updates to state based on what each player can see

            Update self.revealed to reflect the updated vision
            Update self.switch for any new enemies
            Update self.revealed_water
        """
        self.revealed_water = []
        for player in range(self.num_players):
            water = []
            revealed = self.revealed[player]
            switch = self.switch[player]

            for row, squares in enumerate(self.vision[player]):
                for col, visible in enumerate(squares):
                    if not visible:
                        continue

                    value = self.map[row][col]

                    # if this player encounters a new enemy then
                    #   assign the enemy the next index
                    if value >= ANTS and switch[value] is None:
                        switch[value] = self.num_players - switch.count(None)

                    # mark square as revealed and determine if we see any
                    #   new water
                    if not revealed[row][col]:
                        revealed[row][col] = True
                        if value == WATER:
                            water.append((row,col))

            # update the water which was revealed this turn
            self.revealed_water.append(water)

    def get_perspective(self, player=None):
        """ Get the map from the perspective of the given player

            If player is None, the map is return unaltered.
            Squares that are outside of the player's vision are
               marked as UNSEEN.
            Enemy identifiers are changed to reflect the order in
               which the player first saw them.
        """
        if player is not None:
            v = self.vision[player]
        result = []
        for row, squares in enumerate(self.map):
            map_row = []
            for col, square in enumerate(squares):
                if player is None or v[row][col]:
                    if (row,col) in self.hills:
                        if (row,col) in self.current_ants:
                            # assume ant is hill owner
                            # numbers should be divisible by the length of PLAYER_ANT
                            map_row.append(square+10)
                        else:
                            map_row.append(square+20)
                    else:
                        map_row.append(square)
                else:
                    map_row.append(UNSEEN)
            result.append(map_row)
        return result

    def render_changes(self, player):
        """ Create a string which communicates the updates to the state

            Water which is seen for the first time is included.
            All visible transient objects (ants, food) are included.
        """
        updates = self.get_state_changes()
        v = self.vision[player]
        visible_updates = []

        # first add unseen water
        for row, col in self.revealed_water[player]:
            visible_updates.append(['w', row, col])

        # next list all transient objects
        for update in updates:
            ilk, row, col = update[0:3]

            # only include updates to squares which are visible
            # and the current players dead ants
            if v[row][col] or (ilk == 'd' and update[-1] == player):
                visible_updates.append(update)

                # switch player perspective of player numbers
                if ilk in ['a', 'd', 'h']:
                    # an ant can appear in a bots vision and die the same turn
                    # in this case the ant has not been assigned a number yet
                    #   assign the enemy the next index
                    if self.switch[player][update[-1]] is None:
                        self.switch[player][update[-1]] = self.num_players - self.switch[player].count(None)
                    update[-1] = self.switch[player][update[-1]]

        visible_updates.append([]) # newline
        return '\n'.join(' '.join(map(str,s)) for s in visible_updates)

    def get_state_changes(self):
        """ Return a list of all transient objects on the map.

            Food, living ants, ants killed this turn
            Changes are sorted so that the same state will result in the same output
        """
        changes = []

        # hills not razed
        changes.extend(sorted(
            [['h', hill.loc[0], hill.loc[1], hill.owner]
             for _, hill in self.hills.items()
             if hill.killed_by is None]
        ))

        # current ants
        changes.extend(sorted(
            ['a', ant.loc[0], ant.loc[1], ant.owner]
            for ant in self.current_ants.values()
        ))
        # current food
        changes.extend(sorted(
            ['f', row, col]
            for row, col in self.current_food
        ))
        # ants killed this turn
        changes.extend(sorted(
            ['d', ant.loc[0], ant.loc[1], ant.owner]
            for ant in self.killed_ants
        ))

        return changes

    def get_map_output(self, player=None, replay=False):
        """ Render the map from the perspective of the given player.

            If player is None, then no squares are hidden and player ids
              are not reordered.
        """
        result = []
        if replay and self.scenario:
            for row in self.original_map:
                result.append(''.join([MAP_RENDER[col] for col in row]))
        else:
            for row in self.get_perspective(player):
                result.append(''.join([MAP_RENDER[col] for col in row]))
        return result

    def nearby_ants(self, loc, max_dist, exclude=None):
        """ Returns ants where 0 < dist to loc <= sqrt(max_dist)

            If exclude is not None, ants with owner == exclude
              will be ignored.
        """
        ants = []
        row, col = loc
        for d_row, d_col in self.neighbourhood_offsets(max_dist):
            if ANTS <= self.map[row+d_row][col+d_col] != exclude:
                n_loc = self.destination(loc, (d_row, d_col))
                ants.append(self.current_ants[n_loc])
        return ants

    def parse_orders(self, player, lines):
        """ Parse orders from the given player

            Orders must be of the form: o row col direction
            row, col must be integers
            direction must be in (n,s,e,w)
        """
        orders = []
        valid = []
        ignored = []
        invalid = []

        for line in lines:
            line = line.strip().lower()
            # ignore blank lines and comments
            if not line or line[0] == '#':
                continue

            data = line.split()

            # validate data format
            if data[0] != 'o':
                invalid.append((line, 'unknown action'))
                continue
            if len(data) != 4:
                invalid.append((line, 'incorrectly formatted order'))
                continue

            row, col, direction = data[1:]
            loc = None

            # validate the data types
            try:
                loc = int(row), int(col)
            except ValueError:
                invalid.append((line,'invalid row or col'))
                continue
            if direction not in AIM:
                invalid.append((line,'invalid direction'))
                continue

            # this order can be parsed
            orders.append((loc, direction))
            valid.append(line)

        return orders, valid, ignored, invalid

    def validate_orders(self, player, orders, lines, ignored, invalid):
        """ Validate orders from a given player

            Location (row, col) must be ant belonging to the player
            direction must not be blocked
            Can't multiple orders to one ant
        """
        valid = []
        valid_orders = []
        seen_locations = set()
        for line, (loc, direction) in zip(lines, orders):
            # validate orders
            if loc in seen_locations:
                invalid.append((line,'duplicate order'))
                continue
            try:
                if self.map[loc[0]][loc[1]] != player:
                    invalid.append((line,'not player ant'))
                    continue
            except IndexError:
                invalid.append((line,'out of bounds'))
                continue
            if loc[0] < 0 or loc[1] < 0:
                invalid.append((line,'out of bounds'))
                continue
            dest = self.destination(loc, AIM[direction])
            if self.map[dest[0]][dest[1]] in (FOOD, WATER):
                ignored.append((line,'move blocked'))
                continue

            # this order is valid!
            valid_orders.append((loc, direction))
            valid.append(line)
            seen_locations.add(loc)

        return valid_orders, valid, ignored, invalid

    def do_orders(self):
        """ Execute player orders and handle conflicts

            All ants are moved to their new positions.
            Any ants which occupy the same square are killed.
        """
        # set old ant locations to land
        for ant in self.current_ants.values():
            row, col = ant.loc
            self.map[row][col] = LAND

        # determine the direction that each ant moves
        #  (holding any ants that don't have orders)
        move_direction = {}
        for orders in self.orders:
            for loc, direction in orders:
                move_direction[self.current_ants[loc]] = direction
        for ant in self.current_ants.values():
            if ant not in move_direction:
                move_direction[ant] = '-'

        # move all the ants
        next_loc = defaultdict(list)
        for ant, direction in move_direction.items():
            ant.loc = self.destination(ant.loc, AIM.get(direction, (0,0)))
            ant.orders.append(direction)
            next_loc[ant.loc].append(ant)

        # if ant is sole occupant of a new square then it survives
        self.current_ants = {}
        colliding_ants = []
        for loc, ants in next_loc.items():
            if len(ants) == 1:
                self.current_ants[loc] = ants[0]
            else:
                for ant in ants:
                    self.kill_ant(ant, True)
                    colliding_ants.append(ant)

        # set new ant locations
        for ant in self.current_ants.values():
            row, col = ant.loc
            self.map[row][col] = ant.owner

    def do_gather(self):
        """ Gather food

            If there are no ants within spawnradius of a food then
              the food remains.
            If all the ants within spawnradius of a food are owned by the
              same player then the food gets added to the hive and will
              spawn a new ant as soon as possible ( 1 turn later ).
            If ants of more than one owner are within spawnradius of a food
              then that food disappears.
        """
        # gather food
        for f_loc in list(self.current_food.keys()):
            # find the owners of all the ants near the food
            nearby_players = set(
                ant.owner for ant in self.nearby_ants(f_loc, self.spawnradius)
            )

            if len(nearby_players) == 1:
                # gather food because there is only one player near the food
                owner = nearby_players.pop()
                self.remove_food(f_loc, owner)
            elif nearby_players:
                # remove food because it is contested
                self.remove_food(f_loc)

    def do_spawn(self):
        """ Spawn new ants at hills from hive amount

            Ants spawn at hills.  The least recently touched hill has priority.
            Ties are done randomly.  The bot can control by standing over a hill
            to prevent spawning where they don't want to spawn.
        """
        # Determine new ant locations
        for player in range(self.num_players):
            player_hills = sorted(self.player_hills(player),
                                  key=lambda hill: (hill.last_touched, random()))
            for hill in player_hills:
                # hill must not be razed or occupied to be used
                # player must have food in hive to spawn
                if (self.hive_food[player] > 0 and
                        hill.loc not in self.current_ants):
                    self.hive_food[player] -= 1
                    self.add_ant(hill)

    def add_food(self, loc):
        """ Add food to a location

            An error is raised if the location is not free
        """
        if self.map[loc[0]][loc[1]] != LAND:
            raise Exception("Add food error",
                            "Food already found at %s" %(loc,))
        self.map[loc[0]][loc[1]] = FOOD
        food = Food(loc, self.turn)
        self.current_food[loc] = food
        self.all_food.append(food)
        return food

    def remove_food(self, loc, owner=None):
        """ Remove food from a location

            An error is raised if no food exists there.
        """
        try:
            self.map[loc[0]][loc[1]] = LAND
            self.current_food[loc].end_turn = self.turn
            if owner is not None:
                self.current_food[loc].owner = owner
                self.hive_food[owner] += 1
            return self.current_food.pop(loc)
        except KeyError:
            raise Exception("Remove food error",
                            "Food not found at %s" %(loc,))

    def add_hill(self, loc, owner):
        hill = Hill(loc, owner)
        self.hills[loc] = hill
        return hill

    def raze_hill(self, hill, killed_by):
        hill.end_turn = self.turn
        hill.killed_by = killed_by
        self.score[killed_by] += HILL_POINTS
        if not hill.raze_points:
            hill.raze_points = True
            self.score[hill.owner] += RAZE_POINTS
        # reset cutoff_turns
        self.cutoff_turns = 0

    def player_hills(self, player):
        """ Return the current hills belonging to the given player """
        return [hill for _, hill in self.hills.items()
                if hill.owner == player and hill.killed_by is None]

    def add_ant(self, hill):
        """ Spawn an ant on a hill
        """
        loc = hill.loc
        owner = hill.owner
        ant = Ant(loc, owner, self.turn)
        row, col = loc
        self.map[row][col] = owner
        self.all_ants.append(ant)
        self.current_ants[loc] = ant
        hill.last_touched = self.turn
        return ant

    def add_initial_ant(self, loc, owner):
        ant = Ant(loc, owner, self.turn)
        row, col = loc
        self.map[row][col] = owner
        self.all_ants.append(ant)
        self.current_ants[loc] = ant
        return ant
    
    def kill_ant(self, ant, ignore_error=False):
        """ Kill the ant at the given location

            Raises an error if no ant is found at the location
              (if ignore error is set to False)
        """
        try:
            loc = ant.loc
            self.map[loc[0]][loc[1]] = LAND
            self.killed_ants.append(ant)
            ant.killed = True
            ant.die_turn = self.turn
            # check for hill kills to stall cutoff counter
            if (loc in self.hills and
                    self.hills[loc].owner != self.cutoff_bot and
                    self.hills[loc].killed_by is None):
                self.hill_kill = True
            return self.current_ants.pop(loc)
        except KeyError:
            if not ignore_error:
                raise Exception("Kill ant error",
                                "Ant not found at %s" %(loc,))

    def player_ants(self, player):
        """ Return the current ants belonging to the given player """
        return [ant for ant in self.current_ants.values() if player == ant.owner]

    def do_raze_hills(self):
        for loc, hill in self.hills.items():
            if loc in self.current_ants:
                ant = self.current_ants[loc]
                if ant.owner == hill.owner:
                    hill.last_touched = self.turn
                elif hill.killed_by is None:
                    self.raze_hill(hill, ant.owner)

    def do_attack_damage(self):
        """ Kill ants which take more than 1 damage in a turn

            Each ant deals 1/#nearby_enemy damage to each nearby enemy.
              (nearby enemies are those within the attackradius)
            Any ant with at least 1 damage dies.
            Damage does not accumulate over turns
              (ie, ants heal at the end of the battle).
        """
        damage = defaultdict(Fraction)
        nearby_enemies = {}

        # each ant damages nearby enemies
        for ant in self.current_ants.values():
            enemies = self.nearby_ants(ant.loc, self.attackradius, ant.owner)
            if enemies:
                nearby_enemies[ant] = enemies
                strenth = 10 # dot dot dot
                if ant.orders[-1] == '-':
                    strenth = 10
                else:
                    strenth = 10
                damage_per_enemy = Fraction(strenth, len(enemies)*10)
                for enemy in enemies:
                    damage[enemy] += damage_per_enemy

        # kill ants with at least 1 damage
        for ant in damage:
            if damage[ant] >= 1:
                self.kill_ant(ant)

    def do_attack_support(self):
        """ Kill ants which have more enemies nearby than friendly ants

            An ant dies if the number of enemy ants within the attackradius
            is greater than the number of friendly ants within the attackradius.
            The current ant is not counted in the friendly ant count.

            1 point is distributed evenly among the enemies of the dead ant.
        """
        # map ants (to be killed) to the enemies that kill it
        ants_to_kill = {}
        for ant in self.current_ants.values():
            enemies = []
            friends = []
            # sort nearby ants into friend and enemy lists
            for nearby_ant in self.nearby_ants(ant.loc, self.attackradius, ant.owner):
                if nearby_ant.owner == ant.owner:
                    friends.append(nearby_ant)
                else:
                    enemies.append(nearby_ant)
            # add ant to kill list if it doesn't have enough support
            if len(friends) < len(enemies):
                ants_to_kill[ant] = enemies

        # actually do the killing and score distribution
        for ant, enemies in ants_to_kill.items():
            self.kill_ant(ant)

    def do_attack_focus(self):
        """ Kill ants which are the most surrounded by enemies

            For a given ant define: Focus = 1/NumOpponents
            An ant's Opponents are enemy ants which are within the attackradius.
            Ant alive if its Focus is greater than Focus of any of his Opponents.
            If an ant dies 1 point is shared equally between its Opponents.
        """
        # maps ants to nearby enemies
        nearby_enemies = {}
        for ant in self.current_ants.values():
            nearby_enemies[ant] = self.nearby_ants(ant.loc, self.attackradius, ant.owner)

        # determine which ants to kill
        ants_to_kill = []
        for ant in self.current_ants.values():
            # determine this ants weakness (1/focus)
            weakness = len(nearby_enemies[ant])
            # an ant with no enemies nearby can't be attacked
            if weakness == 0:
                continue
            # determine the most focused nearby enemy
            min_enemy_weakness = min(len(nearby_enemies[enemy]) for enemy in nearby_enemies[ant])
            # ant dies if it is weak as or weaker than an enemy weakness
            if min_enemy_weakness <= weakness:
                ants_to_kill.append(ant)

        # kill ants and distribute score
        for ant in ants_to_kill:
            self.kill_ant(ant)

    def do_attack_closest(self):
        """ Iteratively kill neighboring groups of ants """
        # maps ants to nearby enemies by distance
        ants_by_distance = {}
        for ant in self.current_ants.values():
            # pre-compute distance to each enemy in range
            dist_map = defaultdict(list)
            for enemy in self.nearby_ants(ant.loc, self.attackradius, ant.owner):
                dist_map[self.distance(ant.loc, enemy.loc)].append(enemy)
            ants_by_distance[ant] = dist_map

        # create helper method to find ant groups
        ant_group = set()
        def find_enemy(ant, distance):
            """ Recursively finds a group of ants to eliminate each other """
            # we only need to check ants at the given distance, because closer
            #   ants would have been eliminated already
            for enemy in ants_by_distance[ant][distance]:
                if not enemy.killed and enemy not in ant_group:
                    ant_group.add(enemy)
                    find_enemy(enemy, distance)

        # setup done - start the killing
        for distance in range(1, self.attackradius):
            for ant in self.current_ants.values():
                if not ants_by_distance[ant] or ant.killed:
                    continue

                ant_group = set([ant])
                find_enemy(ant, distance)

                # kill all ants in groups with more than 1 ant
                #  this way of killing is order-independent because the
                #  the ant group is the same regardless of which ant
                #  you start looking at
                if len(ant_group) > 1:
                    for ant in ant_group:
                        self.kill_ant(ant)

    def destination(self, loc, d):
        """ Returns the location produced by offsetting loc by d """
        return ((loc[0] + d[0]) % self.height, (loc[1] + d[1]) % self.width)

    def access_map(self):
        """ Determine the list of locations that each player is closest to """
        distances = {}
        players = defaultdict(set)
        square_queue = deque()

        # determine the starting squares and valid squares
        # (where food can be placed)
        for row, squares in enumerate(self.map):
            for col, square in enumerate(squares):
                loc = (row, col)
                if square >= 0:
                    distances[loc] = 0
                    players[loc].add(square)
                    square_queue.append(loc)
                elif square != WATER:
                    distances[loc] = None

        # use bfs to determine who can reach each square first
        while square_queue:
            c_loc = square_queue.popleft()
            for d in AIM.values():
                n_loc = self.destination(c_loc, d)
                if n_loc not in distances: continue # wall

                if distances[n_loc] is None:
                    # first visit to this square
                    distances[n_loc] = distances[c_loc] + 1
                    players[n_loc].update(players[c_loc])
                    square_queue.append(n_loc)
                elif distances[n_loc] == distances[c_loc] + 1:
                    # we've seen this square before, but the distance is
                    # the same - therefore combine the players that can
                    # reach this square
                    players[n_loc].update(players[c_loc])

        # summarise the final results of the squares that are closest
        # to a single unique player
        access_map = defaultdict(list)
        for coord, player_set in players.items():
            if len(player_set) != 1: continue
            access_map[player_set.pop()].append(coord)

        return access_map

    def find_closest_land(self, coord):
        """ Find the closest square to coord which is a land square using BFS

            Return None if no square is found
        """
        if self.map[coord[0]][coord[1]] == LAND:
            return coord

        visited = set()
        square_queue = deque([coord])

        while square_queue:
            c_loc = square_queue.popleft()

            for d in AIM.values():
                n_loc = self.destination(c_loc, d)
                if n_loc in visited: continue

                if self.map[n_loc[0]][n_loc[1]] == LAND:
                    return n_loc

                visited.add(n_loc)
                square_queue.append(n_loc)

        return None

    def do_food_none(self, amount=0):
        """ Place no food """
        return amount

    def do_food_random(self, amount=1):
        """ Place food randomly on the map """
        for _ in range(amount):
            while True:
                row = randrange(self.height)
                col = randrange(self.width)
                if self.map[row][col] == LAND:
                    self.pending_food[(row, col)] += 1
                    break
        self.place_food()
        return 0

    def do_food_offset(self, amount=1):
        """ Place food at the same offset from each player's start position

            Pick a col/row offset each turn.
            Calculate this offset for each bots starting location and place
              food there.
            If the spot is not land, find the closest land to that spot and
              place the food there.
        """
        left_over = amount % len(self.initial_ant_list)
        for _ in range(amount//len(self.initial_ant_list)):
            dr = -self.height//4 + randrange(self.height//2)
            dc = -self.width//4  + randrange(self.width//2)
            for ant in self.initial_ant_list: # assumes one ant per player
                row = (ant.loc[0]+dr)%self.height
                col = (ant.loc[1]+dc)%self.width
                coord = self.find_closest_land((row, col))
                if coord:
                    self.pending_food[coord] += 1
        self.place_food()
        return left_over

    def do_food_sections(self, amount=1):
        """ Place food randomly in each player's start section

            Split the map into sections that each ant can access first at
              the start of the game.
            Place food evenly into each space.
        """
        left_over = amount % self.num_players
        for _ in range(amount//self.num_players):
            for p in range(self.num_players):
                squares = self.initial_access_map[p]
                row, col = choice(squares)
                if self.map[row][col] == LAND:
                    self.pending_food[(row, col)] += 1
        self.place_food()
        return left_over

    def do_food_visible(self, amount=1):
        """ Place food in vison of starting spots """
        # if this is the first time calling this function then
        #   create the food sets
        if not hasattr(self, 'food_sets_visible'):
            self.food_sets_visible = deque(self.get_symmetric_food_sets(True))
            # add a sentinal so we know when to shuffle
            self.food_sets_visible.append(None)

        # place food while next food set is <= left over amount
        while True:
            s = self.food_sets_visible.pop()
            # if we finished one rotation, shuffle for the next
            if s is None:
                shuffle(self.food_sets_visible)
                self.food_sets_visible.appendleft(None)
                s = self.food_sets_visible.pop()

            if len(s) > amount:
                # reached food limit, save set, place food and return left over
                self.food_sets_visible.append(s)
                self.place_food()
                return amount
            else:
                amount -= len(s)
                self.food_sets_visible.appendleft(s)
                for loc in s:
                    self.pending_food[loc] += 1


    def do_food_symmetric(self, amount=1):
        """ Place food in the same relation player start positions.

            Food that can't be placed is put into a queue and is placed
              as soon as the location becomes available.
            Positions are randomly ordered and cycled to evenly
              distribute food.
        """
        # if this is the first time calling this function then
        #   create the food sets
        if not hasattr(self, 'food_sets'):
            self.food_sets = deque(self.get_symmetric_food_sets())
            # add a sentinal so we know when to shuffle
            self.food_sets.append(None)

        # place food while next food set is <= left over amount
        while True:
            s = self.food_sets.pop()
            # if we finished one rotation, shuffle for the next
            if s is None:
                shuffle(self.food_sets)
                self.food_sets.appendleft(None)
                s = self.food_sets.pop()

            if len(s) > amount:
                self.food_sets.append(s)
                self.place_food()
                return amount
            else:
                amount -= len(s)
                self.food_sets.appendleft(s)
                for loc in s:
                    self.pending_food[loc] += 1

    def place_food(self):
        """ Place food in scheduled locations if they are free
        """
        for loc in list(self.pending_food.keys()):
            if self.map[loc[0]][loc[1]] == LAND:
                self.add_food(loc)
                self.pending_food[loc] -= 1

                # remove from queue if the count reaches 0
                if not self.pending_food[loc]:
                    del self.pending_food[loc]

    def offset_aim(self, offset, aim):
        """ Return proper offset given an orientation
        """
        # eight possible orientations
        row, col = offset
        if aim == 0:
            return offset
        elif aim == 1:
            return -row, col
        elif aim == 2:
            return row, -col
        elif aim == 3:
            return -row, -col
        elif aim == 4:
            return col, row
        elif aim == 5:
            return -col, row
        elif aim == 6:
            return col, -row
        elif aim == 7:
            return -col, -row

    def map_similar(self, loc1, loc2, aim, player):
        """ find if map is similar given loc1 aim of 0 and loc2 ant of player
            return a map of translated enemy locations
        """
        enemy_map = {}
        for row in range(self.height):
            for col in range(self.width):
                row0, col0 = self.destination(loc1, (row, col))
                row1, col1 = self.destination(loc2, self.offset_aim((row, col), aim))
                # compare locations
                ilk0 = self.map[row0][col0]
                ilk1 = self.map[row1][col1]
                if ilk0 == 0 and ilk1 != player:
                    # friendly ant not in same location
                    return None
                elif ilk0 > 0 and (ilk1 < 0 or ilk1 == player):
                    # enemy ant not in same location
                    return None
                elif ilk0 < 0 and ilk1 != ilk0:
                    # land or water not in same location
                    return None
                if ilk0 >= 0 and enemy_map != None:
                    enemy_map[ilk0] = ilk1
        return enemy_map

    def get_map_symmetry(self):
        """ Get orientation for each starting hill
        """
        # get list of player 0 hills
        hills = [hill for hill in self.hills.values() if hill.owner == 0]
        # list of
        #     list of tuples containing
        #         location, aim, and enemy map dict
        orientations = [[(hills[0].loc, 0,
            dict([(i, i, ) for i in range(self.num_players)]))]]
        for player in range(1, self.num_players):
            player_hills = [hill for hill in self.hills.values() if hill.owner == player]
            if len(player_hills) != len(hills):
                raise Exception("Invalid map",
                                "This map is not symmetric.  Player 0 has {0} hills while player {1} has {2} hills."
                                .format(len(hills), player, len(player_hills)))
            new_orientations = []
            for player_hill in player_hills:
                for aim in range(8):
                # check if map looks similar given the orientation
                    enemy_map = self.map_similar(hills[0].loc, player_hill.loc, aim, player)
                    if enemy_map != None:
                        # produce combinations of orientation sets
                        for hill_aims in orientations:
                            new_hill_aims = deepcopy(hill_aims)
                            new_hill_aims.append((player_hill.loc, aim, enemy_map))
                            new_orientations.append(new_hill_aims)
            orientations = new_orientations
            if len(orientations) == 0:
                raise Exception("Invalid map",
                                "This map is not symmetric. Player {0} does not have an orientation that matches player 0"
                                .format(player))
        # ensure types of hill aims in orientations are symmetric
        # place food set and double check symmetry
        valid_orientations = []
        for hill_aims in orientations:
            fix = []
            for loc, aim, enemy_map in hill_aims:
                row, col = self.destination(loc, self.offset_aim((1,2), aim))
                fix.append(((row, col), self.map[row][col]))
                self.map[row][col] = FOOD
            for loc, aim, enemy_map in hill_aims:
                if self.map_similar(hill_aims[0][0], loc, aim, enemy_map[0]) is None:
                    break
            else:
                valid_orientations.append(hill_aims)
            for (row, col), ilk in reversed(fix):
                self.map[row][col] = ilk
        if len(valid_orientations) == 0:
            raise Exception("Invalid map",
                            "There are no valid orientation sets")
        return valid_orientations

    def get_initial_vision_squares(self):
        """ Get initial squares in bots vision that are traversable

            flood fill from each starting hill up to the vision radius
        """
        vision_squares = {}
        for hill in self.hills.values():
            squares = deque()
            squares.append(hill.loc)
            while squares:
                c_loc = squares.popleft()
                vision_squares[c_loc] = True
                for d in AIM.values():
                    n_loc = self.destination(c_loc, d)
                    if (n_loc not in vision_squares
                            and self.map[n_loc[0]][n_loc[1]] != WATER and
                            self.distance(hill.loc, n_loc) <= self.viewradius):
                        squares.append(n_loc)
        return vision_squares

    def get_symmetric_food_sets(self, starting=False):
        """ Split map into sets of squares

            Each set contains self.num_players points where each point
              is at a consistent offset from each player's starting
              position.
            A square may be the same distance to more than one player
                which will cause the set to be smaller than the number of players
            Assumes map is symmetric.
        """
        if not hasattr(self, 'map_symmetry'):
            # randomly choose one symmetry
            # get_map_symmetry will raise an exception for non-symmetric maps
            self.map_symmetry = choice(self.get_map_symmetry())


        food_sets = []
        # start with only land squares
        visited = [[False for col in range(self.width)]
                          for row in range(self.height)]

        # aim for ahill0 will always be 0
        ant0 = self.map_symmetry[0][0]

        if starting:
            vision_squares = self.get_initial_vision_squares()

        for row, squares in enumerate(visited):
            for col, square in enumerate(squares):
                # if this square has been visited then we don't need to process
                if square:
                    continue

                # skip locations of hills
                if (row, col) in self.hills:
                    continue

                if starting:
                    # skip locations outside of initial ants' view radius
                    if (row, col) not in vision_squares:
                        continue

                # offset to ant 0
                o_row, o_col = row - ant0[0], col - ant0[1]
                # set of unique food locations based on offsets from each starting ant
                locations = list(set([
                    self.destination(loc, self.offset_aim((o_row, o_col), aim))
                    for loc, aim, _ in self.map_symmetry
                ]))
                # duplicates can happen if 2 ants are the same distance from 1 square
                # the food set will be smaller and food spawning takes this into account

                # check for spawn location next to each other
                # create food dead zone along symmetric lines
                too_close = False
                loc1 = locations[0]
                for loc2 in locations[1:]:
                    if self.distance(loc1, loc2) == 1:
                        # spawn locations too close
                        too_close = True
                        break
                if too_close:
                    continue

                # prevent starting food from being equidistant to ants
                if not starting or len(locations) == self.num_players:
                    # set locations to visited
                    for loc in locations:
                        visited[loc[0]][loc[1]] = True
                    food_sets.append(locations)

        return food_sets

    def remaining_players(self):
        """ Return the players still alive """
        return [p for p in range(self.num_players) if self.is_alive(p)]

    def remaining_hills(self):
        """ Return the players with active hills """
        return [h.owner for h in self.hills.values() if h.killed_by is None]

    # Common functions for all games

    def is_rank_stabilized(self):
        """ Determine if the rank can be changed by bots with hills.

            Determines if there are enough hills left for any player to overtake
            another in score.  Only consider bots with remaining hills.
            Those without hills will not be given the opportunity to overtake
        """
        for player in range(self.num_players):
            if self.is_alive(player) and player in self.remaining_hills():
                max_score = sum([HILL_POINTS for hill in self.hills.values()
                                 if hill.killed_by is None
                                 and hill.owner != player]) + self.score[player]
                for opponent in range(self.num_players):
                    if player != opponent:
                        min_score = sum([RAZE_POINTS for hill in self.hills.values()
                                         if hill.killed_by is None
                                         and hill.owner == opponent]) + self.score[opponent]
                        if ((self.score[player] < self.score[opponent]
                                and max_score >= min_score)
                                or (self.score[player] == self.score[opponent]
                                and max_score > min_score)):
                            return False
        return True

    def game_over(self):
        """ Determine if the game is over

            Used by the engine to determine when to finish the game.
            A game is over when there are no players remaining, or a single
              winner remaining.
        """
        if len(self.remaining_players()) < 1:
            self.cutoff = 'extermination'
            return True
        if len(self.remaining_players()) == 1:
            self.cutoff = 'lone survivor'
            return True
        if self.cutoff_turns >= self.cutoff_turn:
            if self.cutoff_bot == FOOD:
                self.cutoff = 'food not being gathered'
            else:
                self.cutoff = 'ants not razing hills'
            return True
        if self.is_rank_stabilized():
            self.cutoff = 'rank stabilized'
            return True

        return False

    def kill_player(self, player):
        """ Used by engine to signal that a player is out of the game """
        self.killed[player] = True
        # remove player's points for hills
        for hill in self.hills.values():
            if hill.owner == player and not hill.raze_points:
                hill.raze_points = True
                self.score[player] += RAZE_POINTS

    def start_game(self):
        """ Called by engine at the start of the game """
        if self.do_food != self.do_food_none:
            self.game_started = True
            if self.food_start:
                starting_food = ((self.land_area // self.food_start)
                                 - self.food_visible * self.num_players)
            else:
                starting_food = 0
            if self.food_visible > 0:
                self.do_food_visible(self.food_visible * self.num_players)
            self.do_food(starting_food)

    def finish_game(self):
        """ Called by engine at the end of the game """
        # lone survivor gets bonus of killing all other hills
        # owners of hills should lose points
        players = self.remaining_players()
        if len(players) == 1:
            for hill in self.hills.values():
                if hill.owner != players[0]:
                    if hill.killed_by == None:
                        self.bonus[players[0]] += HILL_POINTS
                        hill.killed_by = players[0]
                    if not hill.raze_points:
                        self.bonus[hill.owner] += RAZE_POINTS
                        hill.raze_points = True
            for player in range(self.num_players):
                self.score[player] += self.bonus[player]

        self.calc_significant_turns()
        
        # check if a rule change lengthens games needlessly
        if self.cutoff is None:
            self.cutoff = 'turn limit reached'

    def start_turn(self):
        """ Called by engine at the start of the turn """
        self.turn += 1
        self.killed_ants = []
        self.revealed_water = [[] for _ in range(self.num_players)]
        self.removed_food = [[] for _ in range(self.num_players)]
        self.orders = [[] for _ in range(self.num_players)]
        self.hill_kill = False # used to stall cutoff counter

    def finish_turn(self):
        """ Called by engine at the end of the turn """
        self.do_orders()
        self.do_attack()
        self.do_raze_hills()
        self.do_spawn()
        self.do_gather()
        self.food_extra += Fraction(self.food_rate * self.num_players, self.food_turn)
        food_now = int(self.food_extra)
        left_over = self.do_food(food_now)
        self.food_extra -= (food_now - left_over)

        # record score in score history
        for i, s in enumerate(self.score):
            if self.is_alive(i):
                self.score_history[i].append(s)
            elif s != self.score_history[i][-1]:
                # the score has changed, probably due to a dead bot losing a hill
                # increase the history length to the proper amount
                last_score = self.score_history[i][-1]
                score_len = len(self.score_history[i])
                self.score_history[i].extend([last_score]*(self.turn-score_len))
                self.score_history[i].append(s)

        # record hive_food in hive_history
        for i, f in enumerate(self.hive_food):
            if self.is_alive(i):
                self.hive_history[i].append(f)
            elif f != self.hive_history[i][-1]:
                # the hive has changed, probably due to a dead bot gathering food
                # increase the history length to the proper amount
                last_hive = self.hive_history[i][-1]
                hive_len = len(self.hive_history[i])
                self.hive_history[i].extend([last_hive]*(self.turn-hive_len))
                self.hive_history[i].append(f)

        # now that all the ants have moved we can update the vision
        self.update_vision()
        self.update_revealed()

        # calculate population counts for stopping games early
        # FOOD can end the game as well, since no one is gathering it
        pop_count = defaultdict(int)
        for ant in self.current_ants.values():
            pop_count[ant.owner] += 1
        for owner in self.remaining_hills():
            pop_count[owner] += self.hive_food[owner]
        pop_count[FOOD] = len(self.current_food)
        pop_total = sum(pop_count.values())
        for owner, count in pop_count.items():
            if (count >= pop_total * self.cutoff_percent):
                if self.cutoff_bot == owner:
                    if not self.hill_kill:
                        self.cutoff_turns += 1
                else:
                    self.cutoff_bot = owner
                    self.cutoff_turns = 1
                break
        else:
            self.cutoff_bot = LAND
            self.cutoff_turns = 0
        self.calc_significant_turns()

    def calc_significant_turns(self):
        ranking_bots = [sorted(self.score, reverse=True).index(x) for x in self.score]
        if self.ranking_bots != ranking_bots:
            self.ranking_turn = self.turn
        self.ranking_bots = ranking_bots

        winning_bot = [p for p in range(len(self.score)) if self.score[p] == max(self.score)]
        if self.winning_bot != winning_bot:
            self.winning_turn = self.turn
        self.winning_bot = winning_bot

    def get_state(self):
        """ Get all state changes

            Used by engine for streaming playback
        """
        updates = self.get_state_changes()
        updates.append([]) # newline

        return '\n'.join(' '.join(map(str,s)) for s in updates)

    def get_player_start(self, player=None):
        """ Get game parameters visible to players

            Used by engine to send bots startup info on turn 0
        """
        result = []
        result.append(['turn', 0])
        result.append(['loadtime', self.loadtime])
        result.append(['turntime', self.turntime])
        result.append(['rows', self.height])
        result.append(['cols', self.width])
        result.append(['turns', self.turns])
        result.append(['viewradius2', self.viewradius])
        result.append(['attackradius2', self.attackradius])
        result.append(['spawnradius2', self.spawnradius])
        result.append(['player_seed', self.player_seed])
        # information hidden from players
        if player is None:
            result.append(['food_rate', self.food_rate])
            result.append(['food_turn', self.food_turn])
            result.append(['food_start', self.food_start])
            for line in self.get_map_output():
                result.append(['m',line])
        result.append([]) # newline
        return '\n'.join(' '.join(map(str,s)) for s in result)

    def get_player_state(self, player):
        """ Get state changes visible to player

            Used by engine to send state to bots
        """
        return self.render_changes(player)

    def is_alive(self, player):
        """ Determine if player is still alive

            Used by engine to determine players still in the game
        """
        if self.killed[player]:
            return False
        else:
            return bool(self.player_ants(player))

    def get_error(self, player):
        """ Returns the reason a player was killed

            Used by engine to report the error that kicked a player
              from the game
        """
        return ''

    def do_moves(self, player, moves):
        """ Called by engine to give latest player orders """
        orders, valid, ignored, invalid = self.parse_orders(player, moves)
        orders, valid, ignored, invalid = self.validate_orders(player, orders, valid, ignored, invalid)
        self.orders[player] = orders
        return valid, ['%s # %s' % ignore for ignore in ignored], ['%s # %s' % error for error in invalid]

    def get_scores(self, player=None):
        """ Gets the scores of all players

            Used by engine for ranking
        """
        if player is None:
            return self.score
        else:
            return self.order_for_player(player, self.score)

    def order_for_player(self, player, data):
        """ Orders a list of items for a players perspective of player #

            Used by engine for ending bot states
        """
        s = self.switch[player]
        return [None if i not in s else data[s.index(i)]
                for i in range(max(len(data),self.num_players))]

    def get_stats(self):
        """ Get current ant counts

            Used by engine to report stats
        """
        ant_count = [0 for _ in range(self.num_players+1)]
        for ant in self.current_ants.values():
            ant_count[ant.owner] += 1
        stats = {}
        stats['ant_count'] = ant_count
        stats['food'] = len(self.current_food)
        stats['cutoff'] = 'Food' if self.cutoff_bot == FOOD else '-' if self.cutoff_bot == LAND else self.cutoff_bot
        stats['c_turns'] = self.cutoff_turns
        stats['winning'] = self.winning_bot
        stats['w_turn'] = self.winning_turn
        stats['ranking_bots'] = self.ranking_bots
        stats['r_turn'] = self.ranking_turn
        stats['score'] = self.score
        stats['s_alive'] = [1 if self.is_alive(player) else 0 for player in range(self.num_players)]
        stats['s_hills'] = [1 if player in self.remaining_hills() else 0 for player in range(self.num_players)]
        stats['climb?'] = []
#        stats['max_score'] = {}
        for player in range(self.num_players):
            if self.is_alive(player) and player in self.remaining_hills():
                found = 0
                max_score = sum([HILL_POINTS for hill in self.hills.values()
                                 if hill.killed_by is None
                                 and hill.owner != player]) + self.score[player]
#                stats['max_score'][player] = max_score
#                stats['min_score_%s' % player] = {}
                for opponent in range(self.num_players):
                    if player != opponent:
                        min_score = sum([RAZE_POINTS for hill in self.hills.values()
                                         if hill.killed_by is None
                                         and hill.owner == opponent]) + self.score[opponent]
#                        stats['min_score_%s' % player][opponent] = min_score
                        if ((self.score[player] < self.score[opponent]
                                and max_score >= min_score)
                                or (self.score[player] == self.score[opponent]
                                and max_score > min_score)):
                            found = 1
                            #return False
                            break
                stats['climb?'].append(found)
            else:
                stats['climb?'].append(0)
        return stats

    def get_replay(self):
        """ Return a summary of the entire game

            Used by the engine to create a replay file which may be used
              to replay the game.
        """
        replay = {}
        # required params
        replay['revision'] = 3
        replay['players'] = self.num_players

        # optional params
        replay['loadtime'] = self.loadtime
        replay['turntime'] = self.turntime
        replay['turns'] = self.turns
        replay['viewradius2'] = self.viewradius
        replay['attackradius2'] = self.attackradius
        replay['spawnradius2'] = self.spawnradius
        replay['engine_seed'] = self.engine_seed
        replay['player_seed'] = self.player_seed
        replay['food_rate'] = self.food_rate
        replay['food_turn'] = self.food_turn
        replay['food_start'] = self.food_start

        # map
        replay['map'] = {}
        replay['map']['rows'] = self.height
        replay['map']['cols'] = self.width
        replay['map']['data'] = self.get_map_output(replay=True)

        # food and ants combined
        replay['food'] = []
        for food in self.all_food:
            food_data = [food.loc[0], food.loc[1], food.start_turn]
            if food.end_turn is None:
                # food survives to end of game
                food_data.append(self.turn + 1)
            else: # food.ant is None:
                # food disappears
                food_data.append(food.end_turn)
            if food.owner != None:
                food_data.append(food.owner)
            replay['food'].append(food_data)

        replay['ants'] = []
        for ant in self.all_ants:
            # mimic food data
            ant_data = [ant.initial_loc[0], ant.initial_loc[1], ant.spawn_turn]
            if not ant.killed:
                ant_data.append(self.turn + 1)
            else:
                ant_data.append(ant.die_turn)
            ant_data.append(ant.owner)
            ant_data.append(''.join(ant.orders))

            replay['ants'].append(ant_data)

        replay['hills'] = []
        for hill in self.hills.values():
            # mimic food data
            hill_data = [hill.loc[0], hill.loc[1], hill.owner]
            if not hill.end_turn:
                hill_data.append(self.turn + 1)
            else:
                hill_data.append(hill.end_turn)
            #if not hill.killed_by is None:
            #    hill_data.append(hill.owner)

            replay['hills'].append(hill_data)

        # scores
        replay['scores'] = self.score_history
        replay['bonus'] = self.bonus
        replay['hive_history'] = self.hive_history
        replay['winning_turn'] = self.winning_turn
        replay['ranking_turn'] = self.ranking_turn
        replay['cutoff'] =  self.cutoff

        return replay

class Ant:
    def __init__(self, loc, owner, spawn_turn=None):
        self.loc = loc
        self.owner = owner

        self.initial_loc = loc
        self.spawn_turn = spawn_turn
        self.die_turn = None
        self.orders = []
        self.killed = False

    def __str__(self):
        return '(%s, %s, %s, %s, %s)' % (self.initial_loc, self.owner, self.spawn_turn, self.die_turn, ''.join(self.orders))

class Food:
    def __init__(self, loc, start_turn):
        self.loc = loc
        self.start_turn = start_turn
        self.end_turn = None
        self.owner = None

    def __str__(self):
        return '(%s, %s, %s)' % (self.loc, self.start_turn, self.end_turn)

class Hill:
    def __init__(self, loc, owner):
        self.loc = loc
        self.owner = owner
        self.end_turn = None
        self.killed_by = None
        self.raze_points = False

        # used to order hills for spawn points
        # hills are chosen by the least recently spawned first
        # ties are determined randomly
        self.last_touched = 0 # turn lasted touched by ant

    def __str__(self):
        return '(%s, %s, %s)' % (self.loc, self.end_turn, self.killed_by)

def test_symmetry():
    import sys
    import visualizer.visualize_locally
    if len(sys.argv) < 2:
        map_file_name = 'maps/test_maps/sym_test_2.map'
    else:
        map_file_name = sys.argv[1]
    with open(map_file_name, 'r') as f:
        options = {'map': f.read(),
                   'turns': 1,
                   'loadtime': 1000,
                   'turntime': 1000,
                   'viewradius2': 77,
                   'attackradius2': 5,
                   'spawnradius2': 1 }
    a = Ants(options)
    ors = a.get_map_symmetry()
    for o_count, ant_aims in enumerate(ors):
        sys.stdout.write('=== orientation {0} \n'.format(o_count) + '=' * 30)
        fix = []
        lines = ['' for _ in range(a.height)]
        for loc, aim, enemy_map in ant_aims:
            row, col = a.destination(loc, a.offset_aim((1,2), aim))
            fix.append(((row, col), a.map[row][col]))
            a.map[row][col] = FOOD
        for loc, aim, enemy_map in ant_aims:
            sys.stdout.write('{0} {1} {2}'.format(aim, enemy_map, loc))
            for row in range(a.height):
                lines[row] += ' '
                for col in range(a.width):
                    row1, col1 = a.destination(loc, a.offset_aim((row, col), aim))
                    lines[row] += MAP_RENDER[a.map[row1][col1]]
        # write test file
        if len(sys.argv) > 2:
            test_map_name = map_file_name + ''.join([str(aim) for _, aim, __ in ant_aims]) + '.replay'
            with open(test_map_name, 'w') as f:
                f.write("players {0}\n".format(a.num_players))
                f.write("rows {0}\n".format(a.height))
                f.write("cols {0}\n".format(a.width))
                for row in range(a.height):
                    f.write("m ")
                    for col in range(a.width):
                        f.write(MAP_RENDER[a.map[row][col]])
                    f.write("\n")
            visualizer.visualize_locally.launch(test_map_name)
            for (row, col), ilk in reversed(fix):
                a.map[row][col] = ilk

if __name__ == '__main__':
    test_symmetry()

########NEW FILE########
__FILENAME__ = ants
#!/usr/bin/env python
import sys
import traceback
import random

try:
    from sys import maxint
except ImportError:
    from sys import maxsize as maxint
        
MY_ANT = 0
ANTS = 0
DEAD = -1
LAND = -2
FOOD = -3
WATER = -4
UNSEEN = -5
HILL = -6

PLAYER_ANT = 'abcdefghij'
HILL_ANT = string = 'ABCDEFGHIJ'
PLAYER_HILL = string = '0123456789'
MAP_OBJECT = '?%*.!'
MAP_RENDER = PLAYER_ANT + HILL_ANT + PLAYER_HILL + MAP_OBJECT


AIM = {'n': (-1, 0),
       'e': (0, 1),
       's': (1, 0),
       'w': (0, -1)}
RIGHT = {'n': 'e',
         'e': 's',
         's': 'w',
         'w': 'n'}
LEFT = {'n': 'w',
        'e': 'n',
        's': 'e',
        'w': 's'}
BEHIND = {'n': 's',
          's': 'n',
          'e': 'w',
          'w': 'e'}

class Ants():
    def __init__(self):
        self.width = None
        self.height = None
        self.map = None
        self.ant_list = {}
        self.food_list = []
        self.dead_list = []
        self.hill_list = {}

    def setup(self, data):
        'parse initial input and setup starting game state'
        for line in data.split('\n'):
            line = line.strip().lower()
            if len(line) > 0:
                tokens = line.split()
                key = tokens[0]
                if key == 'cols':
                    self.width = int(tokens[1])
                elif key == 'rows':
                    self.height = int(tokens[1])
                elif key == 'player_seed':
                    random.seed(int(tokens[1]))
                elif key == 'turntime':
                    self.turntime = int(tokens[1])
                elif key == 'loadtime':
                    self.loadtime = int(tokens[1])
                elif key == 'viewradius2':
                    self.viewradius2 = int(tokens[1])
                elif key == 'attackradius2':
                    self.attackradius2 = int(tokens[1])
                elif key == 'spawnradius2':
                    self.spawnradius2 = int(tokens[1])
        self.map = [[LAND for col in range(self.width)]
                    for row in range(self.height)]

    def update(self, data):
        # clear ant and food data
        for (row, col), owner in self.ant_list.items():
            self.map[row][col] = LAND
        self.ant_list = {}
        for row, col in self.food_list:
            self.map[row][col] = LAND
        self.food_list = []
        for row, col in self.dead_list:
            self.map[row][col] = LAND
        self.dead_list = []
        for (row, col), owner in self.hill_list.items():
            self.map[row][col] = LAND
        self.hill_list = {}

        # update map and create new ant and food lists
        for line in data.split('\n'):
            line = line.strip().lower()
            if len(line) > 0:
                tokens = line.split()
                if len(tokens) >= 3:
                    row = int(tokens[1])
                    col = int(tokens[2])
                    if tokens[0] == 'a':
                        owner = int(tokens[3])
                        self.map[row][col] = owner
                        self.ant_list[(row, col)] = owner
                    elif tokens[0] == 'f':
                        self.map[row][col] = FOOD
                        self.food_list.append((row, col))
                    elif tokens[0] == 'w':
                        self.map[row][col] = WATER
                    elif tokens[0] == 'd':
                        # food could spawn on a spot where an ant just died
                        # don't overwrite the space unless it is land
                        if self.map[row][col] == LAND:
                            self.map[row][col] = DEAD
                        # but always add to the dead list
                        self.dead_list.append((row, col))
                    elif tokens[0] == 'h':
                        owner = int(tokens[3])
                        self.hill_list[(row, col)] = owner

    def issue_order(self, order):
        sys.stdout.write('o %s %s %s\n' % (order[0], order[1], order[2]))
        sys.stdout.flush()
        
    def finish_turn(self):
        sys.stdout.write('go\n')
        sys.stdout.flush()

    def my_ants(self):
        return [loc for loc, owner in self.ant_list.items()
                    if owner == MY_ANT]

    def enemy_ants(self):
        return [(loc, owner) for loc, owner in self.ant_list.items()
                    if owner != MY_ANT]
    
    def my_hills(self):
        return [loc for loc, owner in self.hill_list.items()
                    if owner == MY_ANT]

    def enemy_hills(self):
        return [(loc, owner) for loc, owner in self.hill_list.items()
                    if owner != MY_ANT]
        
    def food(self):
        return self.food_list[:]

    def passable(self, row, col):
        return self.map[row][col] != WATER
    
    def unoccupied(self, row, col):
        return self.map[row][col] in (LAND, DEAD, UNSEEN)

    def destination(self, row, col, direction):
        d_row, d_col = AIM[direction]
        return ((row + d_row) % self.height, (col + d_col) % self.width)        

    def distance(self, row1, col1, row2, col2):
        row1 = row1 % self.height
        row2 = row2 % self.height
        col1 = col1 % self.width
        col2 = col2 % self.width
        d_col = min(abs(col1 - col2), self.width - abs(col1 - col2))
        d_row = min(abs(row1 - row2), self.height - abs(row1 - row2))
        return d_col + d_row

    def direction(self, row1, col1, row2, col2):
        d = []
        row1 = row1 % self.height
        row2 = row2 % self.height
        col1 = col1 % self.width
        col2 = col2 % self.width
        if row1 < row2:
            if row2 - row1 >= self.height//2:
                d.append('n')
            if row2 - row1 <= self.height//2:
                d.append('s')
        if row2 < row1:
            if row1 - row2 >= self.height//2:
                d.append('s')
            if row1 - row2 <= self.height//2:
                d.append('n')
        if col1 < col2:
            if col2 - col1 >= self.width//2:
                d.append('w')
            if col2 - col1 <= self.width//2:
                d.append('e')
        if col2 < col1:
            if col1 - col2 >= self.width//2:
                d.append('e')
            if col1 - col2 <= self.width//2:
                d.append('w')
        return d

    def closest_food(self,row1,col1,filter=None):
        #find the closest food from this row/col
        min_dist=maxint
        closest_food = None
        for food in self.food_list:
            if filter is None or food not in filter:
                dist = self.distance(row1,col1,food[0],food[1])
                if dist<min_dist:
                    min_dist = dist
                    closest_food = food
        return closest_food    

    def closest_enemy_ant(self,row1,col1,filter=None):
        #find the closest enemy ant from this row/col
        min_dist=maxint
        closest_ant = None
        for ant in self.enemy_ants():
            if filter is None or ant not in filter:
                dist = self.distance(row1,col1,ant[0][0],ant[0][1])
                if dist<min_dist:
                    min_dist = dist
                    closest_ant = ant[0]
        return closest_ant    

    def closest_enemy_hill(self,row1,col1,filter=None):
        #find the closest enemy hill from this row/col
        min_dist=maxint
        closest_hill = None
        for hill in self.enemy_hills():
            if filter is None or hill[0] not in filter:
                dist = self.distance(row1,col1,hill[0][0],hill[0][1])
                if dist<min_dist:
                    min_dist = dist
                    closest_hill = hill[0]
        return closest_hill   

    def closest_unseen(self,row1,col1,filter=None):
        #find the closest unseen from this row/col
        min_dist=maxint
        closest_unseen = None
        for row in range(self.height):
            for col in range(self.width):
                if filter is None or (row, col) not in filter:
                    if self.map[row][col] == UNSEEN:
                        dist = self.distance(row1,col1,row,col)
                        if dist<min_dist:
                            min_dist = dist
                            closest_unseen = (row, col)
        return closest_unseen

    def render_text_map(self):
        tmp = ''
        for row in self.map:
            tmp += '# %s\n' % ''.join([MAP_RENDER[col] for col in row])
        return tmp

    @staticmethod
    def run(bot):
        ants = Ants()
        map_data = ''
        while(True):
            try:
                current_line = sys.stdin.readline().rstrip('\r\n') # strip new line char
                if current_line.lower() == 'ready':
                    ants.setup(map_data)
                    ants.finish_turn()
                    map_data = ''
                elif current_line.lower() == 'go':
                    ants.update(map_data)
                    bot.do_turn(ants)
                    ants.finish_turn()
                    map_data = ''
                else:
                    map_data += current_line + '\n'
            except EOFError:
                break
            except Exception as e:
                traceback.print_exc(file=sys.stderr)
                break

########NEW FILE########
__FILENAME__ = ErrorBot
#!/usr/bin/env python
from ants import *

class ErrorBot:
    def __init__(self):
        self.gander = ['duck', 'duck', 'duck', 'duck', 'goose']
    def do_turn(self, ants):
        if self.gander.pop(0) == 'goose':
            raise Exception('ErrorBot produces error now')

if __name__ == '__main__':
    try:
        import psyco
        psyco.full()
    except ImportError:
        pass
    try:
        Ants.run(ErrorBot())
    except KeyboardInterrupt:
        print('ctrl-c, leaving ...')

########NEW FILE########
__FILENAME__ = GreedyBot
#!/usr/bin/env python
from random import shuffle
from ants import *
import logging
import sys
from optparse import OptionParser
from logutils import initLogging,getLogger

turn_number = 0
bot_version = 'v0.1'

class LogFilter(logging.Filter):
  """
  This is a filter that injects stuff like TurnNumber into the log
  """
  def filter(self,record):
    global turn_number,bot_version
    record.turn_number = turn_number
    record.version = bot_version
    return True

class GreedyBot:
    def __init__(self):
        """Add our log filter so that botversion and turn number are output correctly"""        
        log_filter  = LogFilter()
        getLogger().addFilter(log_filter)
        self.visited = [] #keep track of visited row/cols
        self.standing_orders = []

    def hunt_hills(self,ants,a_row,a_col,destinations,hunted,orders):
        getLogger().debug("Start Finding Ant")
        closest_enemy_hill = ants.closest_enemy_hill(a_row,a_col)
        getLogger().debug("Done Finding Ant")            
        if closest_enemy_hill!=None:
            return self.do_order(ants, HILL, (a_row,a_col), closest_enemy_hill, destinations, hunted, orders)
            
    def hunt_ants(self,ants,a_row,a_col,destinations,hunted,orders):
        getLogger().debug("Start Finding Ant")
        closest_enemy_ant = ants.closest_enemy_ant(a_row,a_col,hunted)
        getLogger().debug("Done Finding Ant")            
        if closest_enemy_ant!=None:
            return self.do_order(ants, ANTS, (a_row,a_col), closest_enemy_ant, destinations, hunted, orders)

    def hunt_food(self,ants,a_row,a_col,destinations,hunted,orders):
        getLogger().debug("Start Finding Food")
        closest_food = ants.closest_food(a_row,a_col,hunted)
        getLogger().debug("Done Finding Food")            
        if closest_food!=None:
            return self.do_order(ants, FOOD, (a_row,a_col), closest_food, destinations, hunted, orders)

    def hunt_unseen(self,ants,a_row,a_col,destinations,hunted,orders):
        getLogger().debug("Start Finding Unseen")
        closest_unseen = ants.closest_unseen(a_row,a_col,hunted)
        getLogger().debug("Done Finding Unseen")            
        if closest_unseen!=None:
            return self.do_order(ants, UNSEEN, (a_row,a_col), closest_unseen, destinations, hunted, orders)
    
    def random_move(self,ants,a_row,a_col,destinations,hunted,orders):
        #if we didn't move as there was no food try a random move
        directions = list(AIM.keys())
        getLogger().debug("random move:directions:%s","".join(directions))                
        shuffle(directions)
        getLogger().debug("random move:shuffled directions:%s","".join(directions))
        for direction in directions:
            getLogger().debug("random move:direction:%s",direction)
            (n_row, n_col) = ants.destination(a_row, a_col, direction)
            if (not (n_row, n_col) in destinations and
                    ants.unoccupied(n_row, n_col)):
                return self.do_order(ants, LAND, (a_row,a_col), (n_row, n_col), destinations, hunted, orders)
        
    def do_order(self, ants, order_type, loc, dest, destinations, hunted, orders):
        order_type_desc = ["ant", "hill", "unseen", None, "food", "random", None]
        a_row, a_col = loc
        getLogger().debug("chasing %s:start" % order_type_desc)
        directions = ants.direction(a_row,a_col,dest[0],dest[1])
        getLogger().debug("chasing %s:directions:%s" % (order_type_desc[order_type],"".join(directions)))
        shuffle(directions)
        for direction in directions:
            getLogger().debug("chasing %s:direction:%s" % (order_type_desc[order_type],direction))
            (n_row,n_col) = ants.destination(a_row,a_col,direction)
            if (not (n_row,n_col) in destinations and
                ants.unoccupied(n_row,n_col)):
                ants.issue_order((a_row,a_col,direction))
                getLogger().debug("issue_order:%s,%d,%d,%s","chasing %s" % order_type_desc[order_type],a_row,a_col,direction)                        
                destinations.append((n_row,n_col))
                hunted.append(dest)
                orders.append([loc, (n_row,n_col), dest, order_type])
                return True
        return False
        
    def do_turn(self, ants):
        global turn_number
        turn_number = turn_number+1
        destinations = []
        getLogger().debug("Starting Turn")
        # continue standing orders
        orders = []
        hunted = []
        for order in self.standing_orders:
            ant_loc, step_loc, dest_loc, order_type = order
            if ((order_type == HILL and dest_loc in ants.enemy_hills()) or
                    (order_type == FOOD and dest_loc in ants.food()) or
                    (order_type == ANTS and dest_loc in ants.enemy_ants()) or
                    (order_type == UNSEEN and ants.map[dest_loc[0]][dest_loc[1]] == UNSEEN)):
                self.do_order(ants, order_type, ant_loc, dest_loc, destinations, hunted, orders)
                
        origins = [order[0] for order in orders]
        for a_row, a_col in ants.my_ants():
            if (a_row, a_col) not in origins:
                if not self.hunt_hills(ants, a_row, a_col, destinations, hunted, orders):
                    if not self.hunt_food(ants, a_row, a_col, destinations, hunted, orders):
                        if not self.hunt_ants(ants, a_row, a_col, destinations, hunted, orders):
                            if not self.hunt_unseen(ants, a_row, a_col, destinations, hunted, orders):
                                if not self.random_move(ants, a_row, a_col, destinations, hunted, orders):
                                    getLogger().debug("blocked:can't move:%d,%d",a_row,a_col)
                                    destinations.append((a_row,a_col))
        self.standing_orders = orders
        for order in self.standing_orders:
            # move ant location to step destination
            order[0] = order[1]
                    
if __name__ == '__main__':
    try:
        import psyco
        psyco.full()
    except ImportError:
        pass
    try:
        Ants.run(GreedyBot())
    except KeyboardInterrupt:
        print('ctrl-c, leaving ...')

########NEW FILE########
__FILENAME__ = HoldBot
#!/usr/bin/env python
from ants import *

class HoldBot:
    def do_turn(self, ants):
        pass

if __name__ == '__main__':
    try:
        import psyco
        psyco.full()
    except ImportError:
        pass
    try:
        Ants.run(HoldBot())
    except KeyboardInterrupt:
        print('ctrl-c, leaving ...')

########NEW FILE########
__FILENAME__ = HunterBot
#!/usr/bin/env python
from random import shuffle
from ants import *

class HunterBot():
    def do_turn(self, ants):
        destinations = []
        for a_row, a_col in ants.my_ants():
            targets = ants.food() + [(row, col) for (row, col), owner in ants.enemy_ants()]
            # find closest food or enemy ant
            closest_target = None
            closest_distance = 999999
            for t_row, t_col in targets:
                dist = ants.distance(a_row, a_col, t_row, t_col)
                if dist < closest_distance:
                    closest_distance = dist
                    closest_target = (t_row, t_col)
            if closest_target == None:
                # no target found, mark ant as not moving so we don't run into it
                destinations.append((a_row, a_col))
                continue
            directions = ants.direction(a_row, a_col, closest_target[0], closest_target[1])
            shuffle(directions)
            for direction in directions:
                n_row, n_col = ants.destination(a_row, a_col, direction)
                if ants.unoccupied(n_row, n_col) and not (n_row, n_col) in destinations:
                    destinations.append((n_row, n_col))
                    ants.issue_order((a_row, a_col, direction))
                    break
            else:
                # mark ant as not moving so we don't run into it
                destinations.append((a_row, a_col))

if __name__ == '__main__':
    try:
        import psyco
        psyco.full()
    except ImportError:
        pass
    try:
        Ants.run(HunterBot())
    except KeyboardInterrupt:
        print('ctrl-c, leaving ...')

########NEW FILE########
__FILENAME__ = InvalidBot
#!/usr/bin/env python
from random import choice
from ants import *

class InvalidBot:
    def __init__(self):
        self.gander = ['duck', 'duck', 'goose']
    def do_turn(self, ants):
        if choice(self.gander) == 'goose':
            ants.issue_order((-1, -1, 'h'))
        else:
            self.gander.append('goose')

if __name__ == '__main__':
    try:
        import psyco
        psyco.full()
    except ImportError:
        pass
    try:
        Ants.run(InvalidBot())
    except KeyboardInterrupt:
        print('ctrl-c, leaving ...')

########NEW FILE########
__FILENAME__ = LeftyBot
#!/usr/bin/env python
from random import choice, randrange
from ants import *
import sys
import logging
from optparse import OptionParser

class LeftyBot:
    def __init__(self):
        self.ants_straight = {}
        self.ants_lefty = {}

    def do_turn(self, ants):
        destinations = []
        new_straight = {}
        new_lefty = {}
        for a_row, a_col in ants.my_ants():
            # send new ants in a straight line
            if (not (a_row, a_col) in self.ants_straight and
                    not (a_row, a_col) in self.ants_lefty):
                if a_row % 2 == 0:
                    if a_col % 2 == 0:
                        direction = 'n'
                    else:
                        direction = 's'
                else:
                    if a_col % 2 == 0:
                        direction = 'e'
                    else:
                        direction = 'w'
                self.ants_straight[(a_row, a_col)] = direction

            # send ants going in a straight line in the same direction
            if (a_row, a_col) in self.ants_straight:
                direction = self.ants_straight[(a_row, a_col)]
                n_row, n_col = ants.destination(a_row, a_col, direction)
                if ants.passable(n_row, n_col):
                    if (ants.unoccupied(n_row, n_col) and
                            not (n_row, n_col) in destinations):
                        ants.issue_order((a_row, a_col, direction))
                        new_straight[(n_row, n_col)] = direction
                        destinations.append((n_row, n_col))
                    else:
                        # pause ant, turn and try again next turn
                        new_straight[(a_row, a_col)] = LEFT[direction]
                        destinations.append((a_row, a_col))
                else:
                    # hit a wall, start following it
                    self.ants_lefty[(a_row, a_col)] = RIGHT[direction]

            # send ants following a wall, keeping it on their left
            if (a_row, a_col) in self.ants_lefty:
                direction = self.ants_lefty[(a_row, a_col)]
                directions = [LEFT[direction], direction, RIGHT[direction], BEHIND[direction]]
                # try 4 directions in order, attempting to turn left at corners
                for new_direction in directions:
                    n_row, n_col = ants.destination(a_row, a_col, new_direction)
                    if ants.passable(n_row, n_col):
                        if (ants.unoccupied(n_row, n_col) and
                                not (n_row, n_col) in destinations):
                            ants.issue_order((a_row, a_col, new_direction))
                            new_lefty[(n_row, n_col)] = new_direction
                            destinations.append((n_row, n_col))
                            break
                        else:
                            # have ant wait until it is clear
                            new_straight[(a_row, a_col)] = RIGHT[direction]
                            destinations.append((a_row, a_col))
                            break

        # reset lists
        self.ants_straight = new_straight
        self.ants_lefty = new_lefty

if __name__ == '__main__':
    try:
        import psyco
        psyco.full()
    except ImportError:
        pass
    try:
        Ants.run(LeftyBot())
    except KeyboardInterrupt:
        print('ctrl-c, leaving ...')
        
########NEW FILE########
__FILENAME__ = logutils
import logging

"""Initializes Logging infrastructure for the bot"""

def initLogging():
  #logLevel = logging.DEBUG
  logLevel = logging.INFO
  #logLevel = logging.WARNING
  logger = logging.getLogger("ConsoleLog")
  logger.setLevel(logLevel)

  ch = logging.StreamHandler()
  ch.setLevel(logLevel)

  formatter = logging.Formatter("%(asctime)s-%(version)s- Turn:%(turn_number)s-%(funcName)25s() - %(message)s")
  ch.setFormatter(formatter)
  getLogger().addHandler(ch)


def getLogger():
  return logging.getLogger("ConsoleLog")

########NEW FILE########
__FILENAME__ = RandomBot
#!/usr/bin/env python
from random import shuffle
from ants import *

class RandomBot:
    def do_turn(self, ants):
        destinations = []
        for a_row, a_col in ants.my_ants():
            # try all directions randomly until one is passable and not occupied
            directions = AIM.keys()
            shuffle(directions)
            for direction in directions:
                (n_row, n_col) = ants.destination(a_row, a_col, direction)
                if (not (n_row, n_col) in destinations and
                        ants.passable(n_row, n_col)):
                    ants.issue_order((a_row, a_col, direction))
                    destinations.append((n_row, n_col))
                    break
            else:
                destinations.append((a_row, a_col))

if __name__ == '__main__':
    try:
        import psyco
        psyco.full()
    except ImportError:
        pass
    try:
        Ants.run(RandomBot())
    except KeyboardInterrupt:
        print('ctrl-c, leaving ...')

########NEW FILE########
__FILENAME__ = TimeoutBot
#!/usr/bin/env python
import time
from ants import *
import sys

class TimeoutBot:
    def __init__(self):
        self.gander = ['duck', 'duck', 'goose']
    def do_turn(self, ants):
        if self.gander.pop(0) == 'goose':
            sys.stderr.write("Cooking my goose...\n")
            time.sleep((ants.turntime * 2)/1000)

if __name__ == '__main__':
    try:
        import psyco
        psyco.full()
    except ImportError:
        pass
    try:
        Ants.run(TimeoutBot())
    except KeyboardInterrupt:
        print('ctrl-c, leaving ...')

########NEW FILE########
__FILENAME__ = ants
#!/usr/bin/env python
import sys
import traceback
import random
import time
from collections import defaultdict
from math import sqrt

MY_ANT = 0
ANTS = 0
DEAD = -1
LAND = -2
FOOD = -3
WATER = -4

PLAYER_ANT = 'abcdefghij'
HILL_ANT = string = 'ABCDEFGHIJ'
PLAYER_HILL = string = '0123456789'
MAP_OBJECT = '?%*.!'
MAP_RENDER = PLAYER_ANT + HILL_ANT + PLAYER_HILL + MAP_OBJECT

AIM = {'n': (-1, 0),
       'e': (0, 1),
       's': (1, 0),
       'w': (0, -1)}
RIGHT = {'n': 'e',
         'e': 's',
         's': 'w',
         'w': 'n'}
LEFT = {'n': 'w',
        'e': 'n',
        's': 'e',
        'w': 's'}
BEHIND = {'n': 's',
          's': 'n',
          'e': 'w',
          'w': 'e'}

class Ants():
    def __init__(self):
        self.cols = None
        self.rows = None
        self.map = None
        self.hill_list = {}
        self.ant_list = {}
        self.dead_list = defaultdict(list)
        self.food_list = []
        self.turntime = 0
        self.loadtime = 0
        self.turn_start_time = None
        self.vision = None
        self.viewradius2 = 0
        self.attackradius2 = 0
        self.spawnradius2 = 0
        self.turns = 0

    def setup(self, data):
        'parse initial input and setup starting game state'
        for line in data.split('\n'):
            line = line.strip().lower()
            if len(line) > 0:
                tokens = line.split()
                key = tokens[0]
                if key == 'cols':
                    self.cols = int(tokens[1])
                elif key == 'rows':
                    self.rows = int(tokens[1])
                elif key == 'player_seed':
                    random.seed(int(tokens[1]))
                elif key == 'turntime':
                    self.turntime = int(tokens[1])
                elif key == 'loadtime':
                    self.loadtime = int(tokens[1])
                elif key == 'viewradius2':
                    self.viewradius2 = int(tokens[1])
                elif key == 'attackradius2':
                    self.attackradius2 = int(tokens[1])
                elif key == 'spawnradius2':
                    self.spawnradius2 = int(tokens[1])
                elif key == 'turns':
                    self.turns = int(tokens[1])
        self.map = [[LAND for col in range(self.cols)]
                    for row in range(self.rows)]

    def update(self, data):
        'parse engine input and update the game state'
        # start timer
        self.turn_start_time = time.time()
        
        # reset vision
        self.vision = None
        
        # clear hill, ant and food data
        self.hill_list = {}
        for row, col in self.ant_list.keys():
            self.map[row][col] = LAND
        self.ant_list = {}
        for row, col in self.dead_list.keys():
            self.map[row][col] = LAND
        self.dead_list = defaultdict(list)
        for row, col in self.food_list:
            self.map[row][col] = LAND
        self.food_list = []
        
        # update map and create new ant and food lists
        for line in data.split('\n'):
            line = line.strip().lower()
            if len(line) > 0:
                tokens = line.split()
                if len(tokens) >= 3:
                    row = int(tokens[1])
                    col = int(tokens[2])
                    if tokens[0] == 'w':
                        self.map[row][col] = WATER
                    elif tokens[0] == 'f':
                        self.map[row][col] = FOOD
                        self.food_list.append((row, col))
                    else:
                        owner = int(tokens[3])
                        if tokens[0] == 'a':
                            self.map[row][col] = owner
                            self.ant_list[(row, col)] = owner
                        elif tokens[0] == 'd':
                            # food could spawn on a spot where an ant just died
                            # don't overwrite the space unless it is land
                            if self.map[row][col] == LAND:
                                self.map[row][col] = DEAD
                            # but always add to the dead list
                            self.dead_list[(row, col)].append(owner)
                        elif tokens[0] == 'h':
                            owner = int(tokens[3])
                            self.hill_list[(row, col)] = owner
                        
    def time_remaining(self):
        return self.turntime - int(1000 * (time.time() - self.turn_start_time))
    
    def issue_order(self, order):
        'issue an order by writing the proper ant location and direction'
        (row, col), direction = order
        sys.stdout.write('o %s %s %s\n' % (row, col, direction))
        sys.stdout.flush()
        
    def finish_turn(self):
        'finish the turn by writing the go line'
        sys.stdout.write('go\n')
        sys.stdout.flush()
    
    def my_hills(self):
        return [loc for loc, owner in self.hill_list.items()
                    if owner == MY_ANT]

    def enemy_hills(self):
        return [(loc, owner) for loc, owner in self.hill_list.items()
                    if owner != MY_ANT]
        
    def my_ants(self):
        'return a list of all my ants'
        return [(row, col) for (row, col), owner in self.ant_list.items()
                    if owner == MY_ANT]

    def enemy_ants(self):
        'return a list of all visible enemy ants'
        return [((row, col), owner)
                    for (row, col), owner in self.ant_list.items()
                    if owner != MY_ANT]

    def food(self):
        'return a list of all food locations'
        return self.food_list[:]

    def passable(self, loc):
        'true if not water'
        row, col = loc
        return self.map[row][col] != WATER
    
    def unoccupied(self, loc):
        'true if no ants are at the location'
        row, col = loc
        return self.map[row][col] in (LAND, DEAD)

    def destination(self, loc, direction):
        'calculate a new location given the direction and wrap correctly'
        row, col = loc
        d_row, d_col = AIM[direction]
        return ((row + d_row) % self.rows, (col + d_col) % self.cols)        

    def distance(self, loc1, loc2):
        'calculate the closest distance between to locations'
        row1, col1 = loc1
        row2, col2 = loc2
        d_col = min(abs(col1 - col2), self.cols - abs(col1 - col2))
        d_row = min(abs(row1 - row2), self.rows - abs(row1 - row2))
        return d_row + d_col

    def direction(self, loc1, loc2):
        'determine the 1 or 2 fastest (closest) directions to reach a location'
        row1, col1 = loc1
        row2, col2 = loc2
        height2 = self.rows//2
        width2 = self.cols//2
        d = []
        if row1 < row2:
            if row2 - row1 >= height2:
                d.append('n')
            if row2 - row1 <= height2:
                d.append('s')
        if row2 < row1:
            if row1 - row2 >= height2:
                d.append('s')
            if row1 - row2 <= height2:
                d.append('n')
        if col1 < col2:
            if col2 - col1 >= width2:
                d.append('w')
            if col2 - col1 <= width2:
                d.append('e')
        if col2 < col1:
            if col1 - col2 >= width2:
                d.append('e')
            if col1 - col2 <= width2:
                d.append('w')
        return d

    def visible(self, loc):
        ' determine which squares are visible to the given player '

        if self.vision == None:
            if not hasattr(self, 'vision_offsets_2'):
                # precalculate squares around an ant to set as visible
                self.vision_offsets_2 = []
                mx = int(sqrt(self.viewradius2))
                for d_row in range(-mx,mx+1):
                    for d_col in range(-mx,mx+1):
                        d = d_row**2 + d_col**2
                        if d <= self.viewradius2:
                            self.vision_offsets_2.append((
                                # Create all negative offsets so vision will
                                # wrap around the edges properly
                                (d_row % self.rows) - self.rows,
                                (d_col % self.cols) - self.cols
                            ))
            # set all spaces as not visible
            # loop through ants and set all squares around ant as visible
            self.vision = [[False]*self.cols for row in range(self.rows)]
            for ant in self.my_ants():
                a_row, a_col = ant
                for v_row, v_col in self.vision_offsets_2:
                    self.vision[a_row + v_row][a_col + v_col] = True
        row, col = loc
        return self.vision[row][col]
    
    def render_text_map(self):
        'return a pretty string representing the map'
        tmp = ''
        for row in self.map:
            tmp += '# %s\n' % ''.join([MAP_RENDER[col] for col in row])
        return tmp

    # static methods are not tied to a class and don't have self passed in
    # this is a python decorator
    @staticmethod
    def run(bot):
        'parse input, update game state and call the bot classes do_turn method'
        ants = Ants()
        map_data = ''
        while(True):
            try:
                current_line = sys.stdin.readline().rstrip('\r\n') # string new line char
                if current_line.lower() == 'ready':
                    ants.setup(map_data)
                    bot.do_setup(ants)
                    ants.finish_turn()
                    map_data = ''
                elif current_line.lower() == 'go':
                    ants.update(map_data)
                    # call the do_turn method of the class passed in
                    bot.do_turn(ants)
                    ants.finish_turn()
                    map_data = ''
                else:
                    map_data += current_line + '\n'
            except EOFError:
                break
            except KeyboardInterrupt:
                raise
            except:
                # don't raise error or return so that bot attempts to stay alive
                traceback.print_exc(file=sys.stderr)
                sys.stderr.flush()

########NEW FILE########
__FILENAME__ = MyBot
#!/usr/bin/env python
from ants import *

# define a class with a do_turn method
# the Ants.run method will parse and update bot input
# it will also run the do_turn method for us
class MyBot:
    def __init__(self):
        # define class level variables, will be remembered between turns
        pass
    
    # do_setup is run once at the start of the game
    # after the bot has received the game settings
    # the ants class is created and setup by the Ants.run method
    def do_setup(self, ants):
        # initialize data structures after learning the game settings
        pass
    
    # do turn is run once per turn
    # the ants class has the game state and is updated by the Ants.run method
    # it also has several helper methods to use
    def do_turn(self, ants):
        # loop through all my ants and try to give them orders
        # the ant_loc is an ant location tuple in (row, col) form
        for ant_loc in ants.my_ants():
            # try all directions in given order
            directions = ('n','e','s','w')
            for direction in directions:
                # the destination method will wrap around the map properly
                # and give us a new (row, col) tuple
                new_loc = ants.destination(ant_loc, direction)
                # passable returns true if the location is land
                if (ants.passable(new_loc)):
                    # an order is the location of a current ant and a direction
                    ants.issue_order((ant_loc, direction))
                    # stop now, don't give 1 ant multiple orders
                    break
            # check if we still have time left to calculate more orders
            if ants.time_remaining() < 10:
                break
            
if __name__ == '__main__':
    # psyco will speed up python a little, but is not needed
    try:
        import psyco
        psyco.full()
    except ImportError:
        pass
    
    try:
        # if run is passed a class with a do_turn method, it will do the work
        # this is not needed, in which case you will need to write your own
        # parsing function and your own game state class
        Ants.run(MyBot())
    except KeyboardInterrupt:
        print('ctrl-c, leaving ...')

########NEW FILE########
__FILENAME__ = ants
#!/usr/bin/env python
import sys
import traceback
import random
import time
from collections import defaultdict
from math import sqrt

MY_ANT = 0
ANTS = 0
DEAD = -1
LAND = -2
FOOD = -3
WATER = -4

PLAYER_ANT = 'abcdefghij'
HILL_ANT = string = 'ABCDEFGHIJ'
PLAYER_HILL = string = '0123456789'
MAP_OBJECT = '?%*.!'
MAP_RENDER = PLAYER_ANT + HILL_ANT + PLAYER_HILL + MAP_OBJECT

AIM = {'n': (-1, 0),
       'e': (0, 1),
       's': (1, 0),
       'w': (0, -1)}
RIGHT = {'n': 'e',
         'e': 's',
         's': 'w',
         'w': 'n'}
LEFT = {'n': 'w',
        'e': 'n',
        's': 'e',
        'w': 's'}
BEHIND = {'n': 's',
          's': 'n',
          'e': 'w',
          'w': 'e'}

class Ants():
    def __init__(self):
        self.cols = None
        self.rows = None
        self.map = None
        self.hill_list = {}
        self.ant_list = {}
        self.dead_list = defaultdict(list)
        self.food_list = []
        self.turntime = 0
        self.loadtime = 0
        self.turn_start_time = None
        self.vision = None
        self.viewradius2 = 0
        self.attackradius2 = 0
        self.spawnradius2 = 0
        self.turns = 0

    def setup(self, data):
        'parse initial input and setup starting game state'
        for line in data.split('\n'):
            line = line.strip().lower()
            if len(line) > 0:
                tokens = line.split()
                key = tokens[0]
                if key == 'cols':
                    self.cols = int(tokens[1])
                elif key == 'rows':
                    self.rows = int(tokens[1])
                elif key == 'player_seed':
                    random.seed(int(tokens[1]))
                elif key == 'turntime':
                    self.turntime = int(tokens[1])
                elif key == 'loadtime':
                    self.loadtime = int(tokens[1])
                elif key == 'viewradius2':
                    self.viewradius2 = int(tokens[1])
                elif key == 'attackradius2':
                    self.attackradius2 = int(tokens[1])
                elif key == 'spawnradius2':
                    self.spawnradius2 = int(tokens[1])
                elif key == 'turns':
                    self.turns = int(tokens[1])
        self.map = [[LAND for col in range(self.cols)]
                    for row in range(self.rows)]

    def update(self, data):
        'parse engine input and update the game state'
        # start timer
        self.turn_start_time = time.time()
        
        # reset vision
        self.vision = None
        
        # clear hill, ant and food data
        self.hill_list = {}
        for row, col in self.ant_list.keys():
            self.map[row][col] = LAND
        self.ant_list = {}
        for row, col in self.dead_list.keys():
            self.map[row][col] = LAND
        self.dead_list = defaultdict(list)
        for row, col in self.food_list:
            self.map[row][col] = LAND
        self.food_list = []
        
        # update map and create new ant and food lists
        for line in data.split('\n'):
            line = line.strip().lower()
            if len(line) > 0:
                tokens = line.split()
                if len(tokens) >= 3:
                    row = int(tokens[1])
                    col = int(tokens[2])
                    if tokens[0] == 'w':
                        self.map[row][col] = WATER
                    elif tokens[0] == 'f':
                        self.map[row][col] = FOOD
                        self.food_list.append((row, col))
                    else:
                        owner = int(tokens[3])
                        if tokens[0] == 'a':
                            self.map[row][col] = owner
                            self.ant_list[(row, col)] = owner
                        elif tokens[0] == 'd':
                            # food could spawn on a spot where an ant just died
                            # don't overwrite the space unless it is land
                            if self.map[row][col] == LAND:
                                self.map[row][col] = DEAD
                            # but always add to the dead list
                            self.dead_list[(row, col)].append(owner)
                        elif tokens[0] == 'h':
                            owner = int(tokens[3])
                            self.hill_list[(row, col)] = owner
                        
    def time_remaining(self):
        return self.turntime - int(1000 * (time.clock() - self.turn_start_time))
    
    def issue_order(self, order):
        'issue an order by writing the proper ant location and direction'
        (row, col), direction = order
        sys.stdout.write('o %s %s %s\n' % (row, col, direction))
        sys.stdout.flush()
        
    def finish_turn(self):
        'finish the turn by writing the go line'
        sys.stdout.write('go\n')
        sys.stdout.flush()
    
    def my_hills(self):
        return [loc for loc, owner in self.hill_list.items()
                    if owner == MY_ANT]

    def enemy_hills(self):
        return [(loc, owner) for loc, owner in self.hill_list.items()
                    if owner != MY_ANT]
        
    def my_ants(self):
        'return a list of all my ants'
        return [(row, col) for (row, col), owner in self.ant_list.items()
                    if owner == MY_ANT]

    def enemy_ants(self):
        'return a list of all visible enemy ants'
        return [((row, col), owner)
                    for (row, col), owner in self.ant_list.items()
                    if owner != MY_ANT]

    def food(self):
        'return a list of all food locations'
        return self.food_list[:]

    def passable(self, loc):
        'true if not water'
        row, col = loc
        return self.map[row][col] > WATER
    
    def unoccupied(self, loc):
        'true if no ants are at the location'
        row, col = loc
        return self.map[row][col] in (LAND, DEAD)

    def destination(self, loc, direction):
        'calculate a new location given the direction and wrap correctly'
        row, col = loc
        d_row, d_col = AIM[direction]
        return ((row + d_row) % self.rows, (col + d_col) % self.cols)        

    def distance(self, loc1, loc2):
        'calculate the closest distance between to locations'
        row1, col1 = loc1
        row2, col2 = loc2
        d_col = min(abs(col1 - col2), self.cols - abs(col1 - col2))
        d_row = min(abs(row1 - row2), self.rows - abs(row1 - row2))
        return d_row + d_col

    def direction(self, loc1, loc2):
        'determine the 1 or 2 fastest (closest) directions to reach a location'
        row1, col1 = loc1
        row2, col2 = loc2
        height2 = self.rows//2
        width2 = self.cols//2
        d = []
        if row1 < row2:
            if row2 - row1 >= height2:
                d.append('n')
            if row2 - row1 <= height2:
                d.append('s')
        if row2 < row1:
            if row1 - row2 >= height2:
                d.append('s')
            if row1 - row2 <= height2:
                d.append('n')
        if col1 < col2:
            if col2 - col1 >= width2:
                d.append('w')
            if col2 - col1 <= width2:
                d.append('e')
        if col2 < col1:
            if col1 - col2 >= width2:
                d.append('e')
            if col1 - col2 <= width2:
                d.append('w')
        return d

    def visible(self, loc):
        ' determine which squares are visible to the given player '

        if self.vision == None:
            if not hasattr(self, 'vision_offsets_2'):
                # precalculate squares around an ant to set as visible
                self.vision_offsets_2 = []
                mx = int(sqrt(self.viewradius2))
                for d_row in range(-mx,mx+1):
                    for d_col in range(-mx,mx+1):
                        d = d_row**2 + d_col**2
                        if d <= self.viewradius2:
                            self.vision_offsets_2.append((
                                d_row%self.rows-self.rows,
                                d_col%self.cols-self.cols
                            ))
            # set all spaces as not visible
            # loop through ants and set all squares around ant as visible
            self.vision = [[False]*self.cols for row in range(self.rows)]
            for ant in self.my_ants():
                a_row, a_col = ant
                for v_row, v_col in self.vision_offsets_2:
                    self.vision[a_row+v_row][a_col+v_col] = True
        row, col = loc
        return self.vision[row][col]
    
    def render_text_map(self):
        'return a pretty string representing the map'
        tmp = ''
        for row in self.map:
            tmp += '# %s\n' % ''.join([MAP_RENDER[col] for col in row])
        return tmp

    # static methods are not tied to a class and don't have self passed in
    # this is a python decorator
    @staticmethod
    def run(bot):
        'parse input, update game state and call the bot classes do_turn method'
        ants = Ants()
        map_data = ''
        while(True):
            try:
                current_line = sys.stdin.readline().rstrip('\r\n') # string new line char
                if current_line.lower() == 'ready':
                    ants.setup(map_data)
                    bot.do_setup(ants)
                    ants.finish_turn()
                    map_data = ''
                elif current_line.lower() == 'go':
                    ants.update(map_data)
                    # call the do_turn method of the class passed in
                    bot.do_turn(ants)
                    ants.finish_turn()
                    map_data = ''
                else:
                    map_data += current_line + '\n'
            except EOFError:
                break
            except KeyboardInterrupt:
                raise
            except:
                # don't raise error or return so that bot attempts to stay alive
                traceback.print_exc(file=sys.stderr)
                sys.stderr.flush()

########NEW FILE########
__FILENAME__ = game
#!/usr/bin/env python

# Games used by the engine should implement the following methods
class Game:
    def __init__(self):
        pass

    # load starting map or game board positions
    def load_map(self, filename):
        pass

    # common functions for all games used by engine
    def start_game(self):
        pass

    # do things needed for start of turn (cleanup, etc...)
    def start_turn(self):
        pass

    # do things needed for finishing a turn (resolving orders, scoring, etc...)
    def finish_turn(self):
        pass

    # do things needed for finishing a game (scoring, etc...)
    def finish_game(self):
        pass

    # remove a player from the game, may be a crashed/timed out bot
    def kill_player(self, player):
        pass

    # return if a player is alive, might be removed by game mechanics
    def is_alive(self, player):
        pass

    # returns if the game is over due to a win condition
    def game_over(self): # returns boolean
        pass

    # used by engine to get the current game state for the streaming format
    def get_state(self):
        pass

    # used for turn 0, sending minimal info for bot to load
    # when passed none, the output is used at the start of the streaming format
    def get_player_start(self, player=None):
        pass

    # used for sending state to bots for each turn
    def get_player_state(self, player):
        pass

    # process a single player's moves, may be appropriate to resolve during finish turn
    def do_moves(self, player, moves):
        # returns valid, ignored, invalid
        #         [''],  [('','')], [('','')]
        pass

    def do_all_moves(self, bot_moves):
        return [self.do_moves(b, moves) for b, moves in enumerate(bot_moves)]

    # used for ranking
    def get_scores(self):
        pass

    # can be used to determine fairness of game and other stuff for visualizers
    def get_stats(self):
        pass
    
    # used for getting a compact replay of the game
    def get_replay(self):
        pass

########NEW FILE########
__FILENAME__ = cavemap
#!/usr/bin/env python

import random
from symmetricmap import *

class Cavemap(SymmetricMap):
    def __init__(self, **kwargs):
        kwargs["defaultterrain"]=WATER
        SymmetricMap.__init__(self, **kwargs)
    
    def add_water_randomly(self,percent=0.49):
        for point in self.size.upto():
            self[point]=LAND
            if random.random() < percent:
                self[point]=WATER
    
    def random_walk(self,start,cover=0.5):
        total_squares=self.size.x*self.size.y
        squares_water=0
        symmetric_locations=len(self.symmetry_vector(Point(0,0)))
        
        location=start
        end_reached=False
        
        while squares_water<total_squares*cover:
            if self[location]==WATER:
                self[location]=LAND
                squares_water+=symmetric_locations
            
            location+=random.choice(directions.values())
    
    def smooth(self, times=1):
        """Apply a cellular automaton to smoothen the walls"""
        for time in xrange(times):
            oldmap=self.copy()
            
            for point in self.size.upto():
                neighbour_water=[d for d in diag_directions.values() if oldmap[point+d]==WATER]
                
                if len(neighbour_water)<4:
                    self[point]=LAND
                if len(neighbour_water)>4:
                    self[point]=WATER
    
    def generate(self,**kwargs):
        self.random_walk(list(self.hills())[0])
        
        try:
            self.smooth(kwargs["smooth"])
        except KeyError:
            self.smooth(4)

if __name__=="__main__":
    #random.seed(6)
    
    size=Point(60,60)
    playerone=size.random_upto()*(0.5/3)+size*(0.5/3)
    
    map=Cavemap(size=size,num_players=4,symmetry="translational")
    
    map.add_hill(playerone)
    map.generate()
    
    print map
########NEW FILE########
__FILENAME__ = map
#!/usr/bin/env python

import collections

from terrain import *

class Map(Terrain):
    def __init__(self, **kwargs):
        Terrain.__init__(self, **kwargs)
        
        #A list of players, each player being a set of hills
        self.players=[set() for player in xrange(kwargs["num_players"])]
    
    def add_hill(self,player,location):
        """Adds a hill to the map, and clears the immediate area"""
        location=location.normalize(self.size)
        
        #check if there's already a hill there
        if location in self.hills():
            raise Exception("Already a hill at %s" % (location,))
        
        #Actually add the hill
        self.players[player].add(location)
        
        #clear an area
        clearsize=Point(3,3)
        offset=clearsize*0.5
        for point in clearsize.upto():
            point=(point-offset)+location
            self[point]=LAND
    
    def hills(self):
        """Returns a set of all hills(locations) on the map"""
        return reduce(lambda x,y: x|y, self.players)

    def render(self):
        string ="rows %s\n" % self.size.y
        string+="cols %s\n" % self.size.x
        string+="players %s\n" % len(self.players)
        
        for y in xrange(self.size.y):
            string+="m "
            for x in xrange(self.size.x):
                character=self[Point(x,y)]
                
                #Check if there's a hill
                for player,hills in enumerate(self.players):
                    if Point(x,y) in hills:
                        character=str(player)
                
                string+=character
            string+="\n"
        return string[:-1]

if __name__=="__main__":
    map=Map(size=Point(10,10),num_players=3,defaultterrain=WATER)
    map.addbase(0,Point(1,1))
    print map
    print "Hills", map.hills()
########NEW FILE########
__FILENAME__ = mapgen
#!/usr/bin/env python

from symmetricmap import *
from cavemap import *
import random

def mapgen(mapsizex, mapsizey, carver, symmetry, players, hills, seed):
    random.seed(seed)
    
    map=Cavemap(size=Point(mapsizex, mapsizey),num_players=players,symmetry=symmetry)
    
    #Decide where to place the hills
    for hillid in xrange(hills):
        player0hill=map.size.random_upto()
        map.add_hill(player0hill)
    
    map.generate()

    print map

if __name__=="__main__":
    import optparse, sys
    
    parser = optparse.OptionParser(usage="""Usage: %prog [options]\n""")
    
    parser.add_option("--cols", dest="mapsizex", type="int", default=60, help="Number of cols, aka x")
    parser.add_option("--rows", dest="mapsizey", type="int", default=60, help="Number of rows, aka y")
    parser.add_option("--carver", dest="carver", type="str", default=0, help="Carver type")
    parser.add_option("--symmetry", dest="symmetry", type="str", default="translational", help="Symmetry types (%s)" % ', '.join(symmetry_types))
    
    parser.add_option("--players", dest="players", type="int", default=4, help="Number of players")
    parser.add_option("--hills", dest="hills", type="int", default=2, help="Number of hills per player")
    parser.add_option("--seed", dest="seed", type="int", default=None, help="Seed for the random number generator")
    
    opts,_ = parser.parse_args(sys.argv)
        
    mapgen(**eval(str(opts)))
########NEW FILE########
__FILENAME__ = symmetricmap
#!/usr/bin/env python

from map import *

class SymmetryException(Exception):
    def __init__(self, msg):
        Exception.__init__(self, msg)
        self.msg = msg
    def __str__(self):
        return "This symmetry type only supports %s." % self.msg

class SymmetricMap(Map):
    def __init__(self, **kwargs):
        Map.__init__(self, **kwargs)
        
        #setup symmetry
        symmetry_type=kwargs["symmetry"]
        if symmetry_type not in symmetry_types:
            raise Exception("Unknown symmetry type %s" % symmetry_type)
        self.symmetry_vector=self.__getattribute__("vector_"+symmetry_type)
        
        #setup translational symmetry
        num_players=kwargs["num_players"]
        try:
            self.translation_factor=kwargs["translation_factor"]
        except KeyError:
            self.translation_factor=Point(num_players-1,num_players+1)
            
        if symmetry_type=="translational":
            if (self.size.x%num_players!=0) or (self.size.y%num_players!=0):
                raise SymmetryException("map size divisible to the number of players")
            self.translation=Point(self.size.x/num_players*self.translation_factor.x,self.size.y/num_players*self.translation_factor.y)
        
        #test the symmetry
        assert(len(self.symmetry_vector(Point(0,0)))>0)
    
    def __setitem__(self,point,value):
        """Sets a point in the terrain, applies to all other points that are symmetric"""
        for symmetric_point in self.symmetry_vector(point):
            Terrain.__setitem__(self, symmetric_point, value)
    
    def add_hill(self,location):
        """Adds a hill at specified location, adds enemy hills to all other symmetric locations too."""
        for player_id,location in enumerate(self.symmetry_vector(location)):
            Map.add_hill(self, player_id, location)
    
    #vector functions given a Point will return a list of all the points that are symmetric including themselves
    def symmetry_vector(self,origin):
        """To be overridden later"""
        pass
    
    def vector_horizontal(self,origin):
        if len(self.players)!=2:
            raise SymmetryException("2 players")
        return [origin,Point(origin.x, self.size.y-origin.y-1)]
    
    def vector_diagonal(self,origin):
        if len(self.players)!=2:
            raise SymmetryException("2 players")
        if self.size.x!=self.size.y:
            raise SymmetryException("square maps")
        return [origin,Point(self.size.x-origin.y-1, self.size.y-origin.x-1)]
    
    def vector_point(self,origin):
        if len(self.players) not in [2,4,8]:
            raise SymmetryException("2, 4 or 8 players")
        
        points = [origin]
        
        if len(self.players)>=2:
            points.append(Point(self.size.x-origin.x-1, self.size.y-origin.y-1)) #vertical/horizontal(point) reflection
        
        if len(self.players)>=4:
            if self.size.x!=self.size.y:
                raise SymmetryException("square maps")
            points.append(Point(self.size.x-origin.x-1, origin.y))               #vertical reflection
            points.append(Point(origin.x, self.size.y-origin.y-1))               #horizontal reflection
        
        if len(self.players)>=8:
            points.append(Point(self.size.x-origin.y-1, self.size.y-origin.x-1)) #diagonal reflection to origin
            points.append(Point(origin.y, origin.x))                             #diagonal reflection to point reflection
            points.append(Point(origin.y, self.size.y-origin.x-1))               #diagonal reflection to vertical reflection
            points.append(Point(self.size.x-origin.y-1, origin.x))               #diagonal reflection to horizontal reflection
        
        return points
    
        
    def vector_rotational(self,origin):
        if len(self.players) not in [2,4]:
            raise SymmetryException("2 or 4 players")
        
        points = [origin]
        
        if len(self.players)>=2:
            points.append(Point(self.size.x-origin.x-1, self.size.y-origin.y-1)) #vertical/horizontal(point) reflection
        
        if len(self.players)>=4:
            if self.size.x!=self.size.y:
                raise SymmetryException("square maps")
            points.append(Point(self.size.x-origin.y-1, origin.x))
            points.append(Point(origin.y, self.size.y-origin.x-1))
        
        return points
    
    def vector_translational(self,origin):
        return [(origin+self.translation*playerid).normalize(self.size)
                for playerid in xrange(len(self.players))]
    
#Generate symmetry types based on the function names
symmetry_types=set(function[len("vector_"):] for function in dir(SymmetricMap) if function.startswith("vector_"))

if __name__=="__main__":
    for symmetry in symmetry_types:
        #title
        print symmetry
        print "="*len(symmetry)
        
        try:
            map=SymmetricMap(size=Point(20,20),num_players=4,symmetry=symmetry)
            
            #add a water spot
            map[Point(1,1)]=WATER
            
            #add player hills
            map.add_hill(Point(2,6))
            
            print map
        except SymmetryException as e:
            print e
        
        #newline
        print
########NEW FILE########
__FILENAME__ = terrain
#!/usr/bin/env python

import random
from util import *

directions = {'N': Point(-1,0), 'S': Point(1,0), 'E': Point(0,1), 'W': Point(0,-1)}
diag_directions = {'NW': Point(-1,-1), 'SW': Point(1,-1), 'NE': Point(-1,1), 'SW': Point(1,-1)}
diag_directions.update(directions)

WATER = "%"
LAND = "."

class Terrain(object):
    """Terrain class contains only map size and terrain data.
    It does not concern itself with players and symmetries"""
    
    def __init__(self, **kwargs):
        self.size=kwargs["size"]
        
        try:
            defaultterrain=kwargs["defaultterrain"]
        except KeyError:
            defaultterrain=LAND
        self.terrain=[[defaultterrain for x in xrange(self.size.x)] for y in xrange(self.size.y)]
        
    def __getitem__(self,point):
        """Gets a point in the terrain"""
        point=point.normalize(self.size)
        return self.terrain[point.y][point.x]
    
    def __setitem__(self,point,value):
        """Sets a point in the terrain"""
        point=point.normalize(self.size)
        self.terrain[point.y][point.x]=value
    
    def copy(self):
        """Makes a copy of this map"""
        newterrain=Terrain(size=self.size)
        for point in self.size.upto():
            newterrain[point]=self[point]
        return newterrain
    
    def render(self):
        string ="rows %s\n" % self.size.y
        string+="cols %s\n" % self.size.x
        
        for y in xrange(self.size.y):
            string+="m "
            for x in xrange(self.size.x):
                string+=self[Point(x,y)]
            string+="\n"
        
        return string[:-1]
    
    def __str__(self):
        return self.render()

if __name__=="__main__":
    terrain=Terrain(size=Point(10,10))
    terrain[Point(-1,-1)]=WATER
    print terrain
########NEW FILE########
__FILENAME__ = util
#!/usr/bin/env python

import collections
import random

class Point(collections.namedtuple('Point', ['x', 'y'])):
    def upto(self):
        """Iterates over all points from origin to Point"""
        for y in xrange(self.y):
            for x in xrange(self.x):
                yield Point(x,y)
    
    def normalize(self,size):
        """Returns a normalized point from a toroid(with a given size)
        Point(-9,-9).normalize(Point(10,10)) => Point(1,1)"""
        return Point(self.x%size.x,self.y%size.y)
    
    def __add__(self,other):
        return Point(self.x+other.x,self.y+other.y)
    
    def __sub__(self,other):
        return Point(self.x-other.x,self.y-other.y)
    
    def __mul__(self,number):
        return Point(int(self.x*number),int(self.y*number))
    
    def random_upto(self):
        """Returns a random point less than self"""
        return Point(random.randint(0,self.x),random.randint(0,self.y))

class Range(collections.namedtuple('Range', ['min','max'])):
    def __contains__(self,what):
        return what>=self.min and what<=self.max
    
    def randint(self):
        """Picks a randint inside the range and remembers it, next time being called it returns the same"""
        try:
            return self.value
        except AttributeError:
            self.value=random.randint(self.min,self.max)
            return self.value
########NEW FILE########
__FILENAME__ = asymmetric_mapgen
#!/usr/bin/env python

import math
import random
from collections import deque

#functions
def gcd(a, b):
    while b:
        a, b = b, a%b
    return a

def lcm(a, b):
    if a == 0 and b == 0:
        return 0
    else:
        return abs(a*b)/gcd(a,b)

#map class
class AsymmetricMap():
    cdirections = ['N', 'E', 'S', 'W']
    directions = {'N': (-1,0), 'S': (1,0), 'E': (0,1), 'W': (0,-1)}

    #game parameters
    min_players = 4
    max_players = 10
    min_dim = 70
    max_dim = 120
    min_start_distance = 30

    min_land_proportion = 0.6
    max_land_proportion = 0.9

    #map parameters
    no_players = 0
    rows = cols = 0
    row_t = col_t = 0
    land_squares = 0
    map_data = []
    basis = []
    a_loc = c_locs = []
    no_extra_walks = 70


    #makes a map by carving it out of water
    def random_walk_map(self):
        self.pick_dimensions()
        self.map_data = [ ['%' for c in range(self.cols)] for r in range(self.rows) ]

        self.add_ants()
        self.basis = self.get_basis()

        self.start_walks()
        self.add_land()

    def random_map(self):
        self.pick_dimensions()
        self.map_data = [ ['%' for c in range(self.cols)] for r in range(self.rows) ]
        self.add_ants()
        self.basis = self.get_basis()
        self.add_random_land()

    #outputs the map
    def print_map(self):
        print "rows", self.rows
        print "cols", self.cols
        print "players", self.no_players
        for row in self.map_data:
            print 'm', ''.join(row)

    #picks the dimensions of the map
    def pick_dimensions(self):
        while True:
            while True:
                self.rows = random.randint(self.min_dim, self.max_dim)
                self.cols = random.randint(self.min_dim, self.max_dim)

                self.row_t = random.randint(3, self.rows-3)
                self.col_t = random.randint(3, self.cols-3)

                #makes sure no two players start in the same row or column
                if self.rows/gcd(self.row_t, self.rows) == self.cols/gcd(self.col_t, self.cols):
                    break

            self.no_players = lcm(self.rows/gcd(self.row_t, self.rows),
                                  self.cols/gcd(self.col_t, self.cols) )

            #forces a valid number of players all starting at a valid distance
            if self.no_players >= self.min_players and self.no_players <= self.max_players and self.is_valid_start():
                break

    #returns the distance between two squares
    def distance(self, loc1, loc2):
        d1 = abs(loc1[0] - loc2[0])
        d2 = abs(loc1[1] - loc2[1])
        dr = min(d1, self.rows - d1)
        dc = min(d2, self.cols - d2)
        return math.sqrt(dr*dr + dc*dc)

    #randomly picks a location inside the map
    def pick_square(self):
        return [random.randint(0, self.rows-1), random.randint(0, self.cols-1)]

    #starts two random walks from the players starting ants
    def start_walks(self):
        self.c_locs = [self.a_loc, self.a_loc]
        for w in range(self.no_extra_walks):
            c_loc = self.pick_square()
            for n in range(self.no_players):
                self.c_locs.append(self.pick_square())
                self.c_loc = self.get_translate_loc(c_loc)

    #randomly walks the ants in a direction
    def walk_ants(self):
        #walks the locations in a random direction
        for c in range(len(self.c_locs)):
            d = self.cdirections[random.randint(0, 3)]
            n_loc = self.get_loc(self.c_locs[c], d)
            self.c_locs[c] = n_loc

    #returns the new location after moving in a particular direction
    def get_loc(self, loc, direction):
        dr, dc = self.directions[direction]
        return [(loc[0]+dr)%self.rows, (loc[1]+dc)%self.cols ]

    #returns the new location after translating it by (rtranslate, ctranslate)
    def get_translate_loc(self, loc):
        return [(loc[0]+self.row_t)%self.rows,
                (loc[1]+self.col_t)%self.cols ]

    #returns the new location after translating it by (rtranslate, ctranslate)
    def get_translate_loc2(self, loc, row_t, col_t):
        return [(loc[0]+row_t)%self.rows,
                (loc[1]+col_t)%self.cols ]


    #fills in all symmetrically equivalent squares with the given type
    def fill_squares(self, loc, type):
        value = type
        for n in range(self.no_players):
            self.map_data[loc[0] ][loc[1] ] = value
            if type == '0':
                value = chr(ord(value)+1)
            loc = self.get_translate_loc(loc)

    #checks whether the players start far enough apart
    def is_valid_start(self):
        loc = n_loc = [0,0]
        for n in range(self.no_players-1):
            n_loc = self.get_translate_loc(n_loc)
            if self.distance(loc, n_loc) < self.min_start_distance:
                return False
        return True

    #checks whether the players can reach every non-wall square
    def is_valid(self):
        start_loc = self.a_loc
        visited = [ [False for c in range(self.cols)] for r in range(self.rows)]
        visited[start_loc[0] ][start_loc[1] ] = True
        squaresVisited = 1

        stack = [start_loc]
        while stack != []:
            c_loc = stack.pop()
            for d in self.directions:
                n_loc = self.get_loc(c_loc, d)

                if visited[n_loc[0] ][n_loc[1] ] == False and self.map_data[n_loc[0] ][n_loc[1] ] != '%':
                    stack.append(n_loc)
                    visited[n_loc[0] ][n_loc[1] ] = True
                    squaresVisited += 1

        if squaresVisited == self.land_squares:
            return True
        return False

    #adds ants to the map
    def add_ants(self):
        self.land_squares = self.no_players
        self.a_loc = self.c_loc = self.pick_square()
        self.fill_squares(self.a_loc, '0')

        for c_loc in self.c_locs:
            self.land_squares += self.no_players
            self.fill_squares(c_loc, '.')

    #returns a basis for the squares under translation
    def get_basis(self):
        visited = [ [False for c in range(self.cols)] for r in range(self.rows)]
        visited[self.a_loc[0]][self.a_loc[1]] = True

        basis = [self.a_loc]
        queue = deque([self.a_loc])
        while len(queue) > 0:
            c_loc = queue.popleft()
            for d in self.directions:
                n_loc = self.get_loc(c_loc, d)

                if visited[n_loc[0] ][n_loc[1] ] == False:
                    basis.append(n_loc)
                    queue.append(n_loc)
                    for n in range(self.no_players):
                        visited[n_loc[0] ][n_loc[1] ] = True
                        n_loc = self.get_translate_loc(n_loc)

        return basis

    #randomly adds land to the map
    def add_random_land(self):
        no_land_squares = random.randint(int(self.min_land_proportion*self.rows*self.cols),
                                          int(self.max_land_proportion*self.rows*self.cols))

        while self.land_squares < no_land_squares or not self.is_valid():
            for w in range(self.no_extra_walks):
                for n in range(self.no_players):
                    c_loc = self.basis[random.randint(0, len(self.basis)-1)]
                    c_loc = self.get_translate_loc2(c_loc, n*self.row_t, n*self.col_t)
                    while self.map_data[c_loc[0]][c_loc[1]] != '%':
                        c_loc = self.pick_square()
                        c_loc = self.get_translate_loc2(c_loc, n*self.row_t, n*self.col_t)

                    self.map_data[c_loc[0]][c_loc[1]] = '.'
                    self.land_squares += 1

    #adds land to a map of water
    def add_land(self):
        no_land_squares = random.randint(int(self.min_land_proportion*self.rows*self.cols),
                                          int(self.max_land_proportion*self.rows*self.cols))

        while self.land_squares < no_land_squares or not self.is_valid():
            self.walk_ants()

            for c_loc in self.c_locs:
                if self.map_data[c_loc[0]][c_loc[1]] == '%':
                    self.land_squares += 1
                    self.map_data[c_loc[0]][c_loc[1]] = '.'

if __name__ == '__main__':
    example_map = AsymmetricMap()
    example_map.random_walk_map()
    example_map.print_map()


########NEW FILE########
__FILENAME__ = cell_maze
#!/usr/bin/python
from __future__ import print_function
    
from random import randrange, random, choice, paretovariate, betavariate, shuffle, sample
from math import sqrt, ceil
from optparse import OptionParser
from copy import deepcopy
from itertools import combinations

from map import *
euclidean_distance = None

class CellMazeMap(Map):
    def __init__(self, options={}):
        options['name'] = 'cell maze'
        super(CellMazeMap, self).__init__(options)
        self.players = options.get('players', max(2, min(10, int((betavariate(2.5, 3.0) * 10) + 1))))
        self.area = options.get('area', randrange(900 * self.players, min(25000, 5000 * self.players)))
        self.cell_width = options.get('cell_width', min(paretovariate(2), 7.0))
        self.cell_size = options.get('cell_size', min(paretovariate(2) + max(5.0 + self.cell_width, self.cell_width * 2), 20.0))
        self.openness = options.get('openness', betavariate(1.0, 3.0))
        self.aspect_ratio = options.get('aspect_ratio', None)
        self.grid = options.get('grid', None)
        self.maze_type = options.get('maze_type', choice(['prims','backtrack','growing']))
        self.v_sym = options.get('v_sym', None)
        self.v_step = options.get('v_step', None)
        self.h_sym = options.get('h_sym', None)
        self.h_step = options.get('h_step', None)
        self.hills = options.get('hills', None)
        self.grandularity = options.get('grandularity', 1)

        self.report('players {0}'.format(self.players))
        self.report('area {0}, {1} ({2:.1f}^2) per player'.format(self.area, self.area//self.players, sqrt(self.area/self.players)))
        self.report('cell width: {0}'.format(self.cell_width))
        self.report('cell size: {0}'.format(self.cell_size))
        self.report('openness: {0}'.format(self.openness))
        if self.grid is not None:
            self.report('grid: {0}'.format(self.grid))
        self.report('maze type {0}'.format(self.maze_type))
        if self.v_sym is not None:
            self.report('vertical symmetry: {0}'.format(self.v_sym))
        if self.v_step is not None:
            self.report('vertical shear step: {0}'.format(self.v_step))
        if self.h_sym is not None:
            self.report('horizontal symmetry: {0}'.format(self.h_sym))
        if self.h_step is not None:
            self.report('horizontal shear step: {0}'.format(self.h_step))
        if self.hills is not None:
            self.report('hills per player: {0}'.format(self.hills))
            
        self.min_hill_dist = 20
        self.max_hill_dist = 150
                                    
    def generate(self):
        
        def destination(loc, d, size):
            """ Returns the location produced by offsetting loc by d """
            return ((loc[0] + d[0]) % size[0], (loc[1] + d[1]) % size[1])

        def pick_size(grid=None, aspect_ratio=None):
            if grid is None:
                # pick random grid size
                divs = [i for i in range(1,self.players+1) if self.players%i==0]
                row_sym = choice(divs)
                col_sym = self.players//row_sym
            else:
                row_sym, col_sym = grid
            # the min/max values for aspect ratio are tuned for more grid rows than columns
            if row_sym > col_sym:
                row_sym, col_sym = col_sym, row_sym
                self.v_sym, self.h_sym = self.h_sym, self.v_sym
                self.v_step, self.h_step = self.h_step, self.v_step
            grid = (row_sym, col_sym) 
                
            min_val = 0.5 * row_sym / col_sym
            max_val = 5.0 * row_sym / col_sym

            if aspect_ratio is None:
                aspect_ratio = (random() * (max_val - min_val) + min_val) * col_sym / row_sym
            
            rows = sqrt(self.area / aspect_ratio)
            cols = self.area / rows
            rows = int(rows / row_sym)
            cols = int(cols / col_sym)
            
            # modulo to ensure shearing will come out even
            size = (rows - rows % col_sym, cols - cols % row_sym)
            if grid[0] * size[0] > 200:
                rows = 200 // row_sym
                cols = self.area // (rows * row_sym * col_sym)
                size = (rows - rows % col_sym, cols - cols % row_sym)
            elif grid[1] * size[1] > 200:
                cols = 200 // col_sym
                rows = self.area // (cols * col_sym * row_sym)
                size = (rows - rows % col_sym, cols - cols % row_sym)
            
            return size, grid

        def random_points(size, spacing, grandularity=1, count=1000):
            spacing_2 = int(ceil(spacing ** 2))
            spacing = int(ceil(spacing))
            # ensure each random point is on a unique row and col
            rows, cols = size
            # matrix of available spots left
            # range is from 1 to keep points from touching on mirror lines
            matrix = {row: list(range(0,cols,grandularity))
                      for row in range(0,rows,grandularity)}
            
            # offsets for removing points
            offsets = []
            for d_row in range(-spacing, spacing+1):
                for d_col in range(-spacing, spacing+1):
                    if d_row ** 2 + d_col ** 2 <= spacing_2:
                        offsets.append((d_row, d_col))
            
            def remove_point(loc):
                for d_row, d_col in offsets:
                    n_row, n_col = destination(loc, (d_row, d_col), size)
                    if n_row in matrix:
                        if n_col in matrix[n_row]:
                            matrix[n_row].remove(n_col)
                        if len(matrix[n_row]) == 0:
                            del matrix[n_row]
                                    
            points = []
            for _ in range(count):
                row = choice(list(matrix.keys()))
                col = choice(matrix[row])
                point = (row, col)
                points.append(point)
                remove_point(point)
        
                if len(matrix) == 0:
                    break
                
            return sorted(points)
                               
        def make_symmetric(points, size, players, grid, v_sym=None, v_step=None, h_sym=None, h_step=None):
            def copy(value, size, step):
                return size+value
            def mirror(value, size, step):
                return size * 2 - value - 1
            def flip(value, size, step):
                return size-value-1
            def shear(value, size, step):
                return (size//step[1] * step[0] + value) % size
            
            def both_point(point, size, step, funcs):
                vert_func, horz_func = funcs
                return (vert_func(point[0], size[0], step), horz_func(point[1], size[1], step))
            def vert_point(point, size, step, funcs):
                return (funcs[0](point[0], size[0], step), point[1])
            def horz_point(point, size, step, funcs):
                return (point[0], funcs[0](point[1], size[1], step))
            # TODO: ensure square or change output size
            def flip_point(point, size, funcs):
                return (funcs[0](point[1], size[1]), funcs[1](point[0], size[0]))
            
            def vert_increase(size, count):
                return (size[0]*count, size[1])
            def horz_increase(size, count):
                return (size[0], size[1]*count)
            
            vert_copy = (vert_point, (copy,), vert_increase)
            vert_shear = (both_point, (copy, shear), vert_increase)
            vert_mirror = (vert_point, (mirror,), vert_increase)
            vert_rotate = (both_point, (mirror, flip), vert_increase)
            horz_copy = (horz_point, (copy,), horz_increase)
            horz_shear = (both_point, (shear, copy), horz_increase)
            horz_mirror = (horz_point, (mirror,), horz_increase)
            horz_rotate = (both_point, (flip, mirror), horz_increase)    
            extend_report = {vert_copy: "vert_copy",
                             vert_shear: "vert_shear",
                             vert_mirror: "vert_mirror",
                             vert_rotate: "vert_rotate",
                             horz_copy: "horz_copy",
                             horz_shear: "horz_shear",
                             horz_mirror: "horz_mirror",
                             horz_rotate: "horz_rotate"}
            def extend(funcs, points, size, count=2, step=0, shear=1):
                # shear is used for a MxN grid where shearing occurs in both directions
                point_func, trans_funcs, increase_func = funcs
                self.report(extend_report[funcs])
                #rows, cols = size
                new_points = []
                for sym_points in points:
                    if type(sym_points) != list:
                        sym_points = [sym_points]
                    new_sym_points = sym_points[:]
                    for point in sym_points:
                        for c in range(1,count):
                            new_sym_points.append(
                                point_func(point,                    # point
                                increase_func(size, c),              # size
                                ((c * step) % count, count * shear), # step
                                trans_funcs)                         # vert/horz functions
                            )
                    new_points.append(new_sym_points)
                return new_points, increase_func(size, count)
        
            row_sym, col_sym = grid
            # TODO: 90 degree rotate

            #print_points(points, size)
            step = 0
            # limit shearing to values that produce good maps
            sym_step = {2: [0, 1],
                        3: [0, 1, 2],
                        4: [0, 1, 2, 3],
                        5: [1, 2, 3, 4],
                        6: [2, 3, 4], 
                        7: [2, 3, 4, 5],
                        8: [2, 3, 4, 5, 6],
                        9: [2, 3, 4, 5, 6, 7],
                        10: [3, 4, 5, 6, 7]}
            if row_sym > 1:
                if v_sym is None:
                    if row_sym % 2 == 0 and random() < 0.5 and row_sym <= 6:
                        v_sym = choice((vert_mirror, vert_rotate)) if row_sym < 6 else vert_rotate
                    else:
                        if v_step is None:
                            step = choice(sym_step[row_sym])
                        else:
                            step = v_step
                        v_sym = vert_shear
                else:
                    v_sym = [key for key, value in extend_report.items()
                             if value == 'vert_' + v_sym][0]
                    if v_sym == vert_shear:
                        if v_step is None:
                            step = choice(sym_step[row_sym])
                        else:
                            step = v_step
                    else:
                        step = 0
                if step > 0:
                    self.report("vert shear step: {0}".format(step))                
                if v_sym in (vert_mirror, vert_rotate):
                    points, size = extend(v_sym, points, size)
                    if row_sym//2 > 1:
                        points, size = extend(vert_copy, points, size, row_sym//2)
                else:
                    points, size = extend(v_sym, points, size, row_sym, step)

            if col_sym > 1:
                if step > 0:
                    # can't shear, mirror or rotate if vert shearing happened
                    h_sym = horz_copy
                    step = 0
                else:
                    if h_sym is None:
                        if col_sym % 2 == 0 and random() < 0.5 and col_sym <= 6:
                            h_sym = choice((horz_mirror, horz_rotate)) if col_sym < 6 else horz_rotate
                        else:
                            if v_sym in (vert_mirror, vert_rotate):
                                # can't shear after mirror or rotate
                                h_step = 0
                                h_sym = horz_copy
                            else:
                                if h_step is None:
                                    step = choice(sym_step[col_sym])
                                else:
                                    step = h_step
                                h_sym = horz_shear
                    else:
                        h_sym = [key for key, value in extend_report.items()
                                 if value == 'horz_' + h_sym][0]
                        if h_sym == horz_shear:
                            if v_sym in (vert_mirror, vert_rotate):
                                # can't shear after mirror or rotate
                                h_step = 0
                                h_sym = horz_copy
                            else:
                                if h_step is None:
                                    step = choice(sym_step[col_sym])
                                else:
                                    step = h_step
                        else:
                            step = 0
                if step > 0:
                    self.report("horz shear step: {0}".format(step))                
                if h_sym in (horz_mirror, horz_rotate):
                    points, size = extend(h_sym, points, size)
                    if col_sym//2 > 1:
                        points, size = extend(horz_copy, points, size, col_sym//2)
                else:
                    points, size = extend(h_sym, points, size, col_sym, step, row_sym)
            
            return points, size
        
        def build_neighbors(paths):
            # undirected node graph
            # key is start
            # value is another start
            # only added if neighbors share a location with only each other
            #  or must have water tuple with just these neighbors
            new_neighbor = defaultdict(list)
            for path in sorted(paths):
                if len(path) == 2 and path[0] != path[1]:
                    new_neighbor[path[0]].append(path[1])
                    new_neighbor[path[1]].append(path[0])
            return new_neighbor

        def build_paths(points, size, distance):
            rows, cols = size
            # list of water to remove when carving a passage between nodes
            # key is tuple of nearest starts (locations)
            # value is list of locations
            paths = {}
#            mirror_points = {}
            
            # for each square, find closest starting points
            for row in range(rows):
                for col in range(cols):
                    distances = {}
                    #for loc in points.keys():
                    for comp, sym_points in enumerate(points):
                        for point in sym_points:
                            distances[(point, comp)] = distance((row, col), point, size)
                    cutoff = min(distances.values()) + self.cell_width
                    closest = [point_comp for point_comp, d in distances.items()
                               if d <= cutoff]
                    comps = tuple(sorted(set([comp for point, comp in closest])))
                    if len(closest) > 1:
                        if len(comps) > 1:
                            self.map[row][col] = WATER
                            # find all starting points that contributed to the water wall,
                            # add to water wall dict
#                        else:
#                            if distance(closest[0][0], closest[1][0], size) > self.cell_width:
#                                comps = (comps[0], comps[0])
#                                # store unique points in path structure so we can later check if traversable
#                                if comps not in mirror_points:
#                                    mirror_points[comps] = []
#                                if closest not in mirror_points[comps]:
#                                    mirror_points[comps].append(closest)
                    if comps not in paths:
                        paths[comps] = []
                    paths[comps].append((row, col))

                    
#            # close small gaps in mirrored/rotated paths between same comps
#            for path, closests in mirror_points.items():
#                for closest in closests:
#                    if not self.get_path(closest[0][0], closest[1][0], size, 3):
#                        for row, col in paths[path]:
#                            self.map[row][col] = FOOD
#                        del paths[path]
#                        break
                        
            return paths

        def fuse_cells(paths, cell1, cell2):
            paths = deepcopy(paths)
            self.log("fuse {0} and {1}".format(cell1, cell2))
            # join some cells together as one, fix data structures to match
            for path in list(paths.keys()):
                if cell2 in path:
                    if cell1 in path:
                        new_path = tuple(sorted(n for n in path if n != cell2))
                    else:
                        new_path = tuple(sorted(cell1 if n == cell2 else n for n in path))
                    for loc in paths[path]:
                        if new_path == (cell1,):
                            self.map[loc[0]][loc[1]] = LAND
                        if new_path not in paths:
                            paths[new_path] = [loc]
                        elif loc not in paths[new_path]:
                            paths[new_path].append(loc)
                    del paths[path]
            return paths
                    
        def neighbor_dist(neighbors, start, end):
            dist = 0
            visited = set([start])
            frontier = set(neighbors[start])
            while len(frontier) > 0:
                dist += 1
                if end in frontier:
                    return dist
                else:
                    visited.update(frontier)
                    for n in list(frontier):
                        frontier.update(set(neighbors[n]))
                    frontier.difference_update(visited)
            return None
                            
        def remove_narrow_paths(paths, neighbors, points, size):
            neighbors = deepcopy(neighbors)
            paths = deepcopy(paths)
            
            # reverse index of starts
            # key is comp id, value is list of locations
            starts_by_comp = {}
            for comp, sym_points in enumerate(points):
                starts_by_comp[comp] = sym_points[:]            
            # remove paths between cells that are not large enough
            restart_path_check = True
            while restart_path_check:
                narrow_paths = []
                for path in sorted(paths.keys()):
                    if len(path) == 2:
                        if not any(self.get_path(starts_by_comp[path[0]][0], dest_loc, size, 3, paths[path])
                               for dest_loc in starts_by_comp[path[1]]):
                            neighbors[path[0]].remove(path[1])
                            neighbors[path[1]].remove(path[0])
                            if neighbor_dist(neighbors, path[0], path[1]) is not None:
                                narrow_paths.append(path)
                            else:
                                # find 3 cells that can be fused
                                for triple in list(paths.keys()):
                                    if len(set(triple)) == 3 and path[0] in triple and path[1] in triple:
                                        path3 = [n for n in triple if n not in path][0]
                                        paths = fuse_cells(paths, path3, path[0])
                                        paths = fuse_cells(paths, path3, path[1])
                                        break
                                neighbors = build_neighbors(paths.keys())
                                # we should restart the path checks since the openings between cells have changed
                                break
                else:
                    # did not break due to fusing cells, stop outer loop
                    restart_path_check = False
            
            return paths, neighbors, narrow_paths
                                
        def carve(paths, path, ilk=LAND, inclusive=False):
            # carve passages function to pass to maze and other functions
            if inclusive:
                path = [p for p in paths.keys() if len(set(path) - set(p)) == 0]
            elif type(path) != list:
                path = [tuple(sorted(path))]
            for p in path:
                if p in paths:
                    for row, col in paths[p]:
                        self.map[row][col] = ilk
            return path

        def mark_sections(sections):
            for i, (area_visited, _) in enumerate(sections):
                for loc in area_visited:
                    if self.map[loc[0]][loc[1]] == LAND:
                        self.map[loc[0]][loc[1]] = i
                          
        def ensure_connected(paths, carved_paths, carve):
            carved_paths = deepcopy(carved_paths)
            # I'm too lazy to search for disconnected nodes and fuse cells for proper 3x3 block traversal
            # blow up random walls until valid
            sections = self.section(1)
            neighbor = build_neighbors(paths.keys()) # includes removed neighbors
            if len(sections) > 1:
                self.log('connecting maze, sections: {0}'.format(len(sections)))
                # look for largest blocks of squares first, since this will make it easiest to traverse
                for path in (path for l, path in
                             sorted((-len(locs), path) for path, locs in paths.items()
                             if len(path) == 2 and
                             path not in carved_paths)):
                    carve(path, LAND)
                    new_sections = self.section(0)
                    if len(new_sections) < len(sections):
                        self.log('maze connected, sections: {0}'.format(len(new_sections)))
                        #print('# found %s: %s' % (path, self.water[path]))
                        block_sections = [s for s in self.section(1) if len(s[0]) > 9]
                        if len(block_sections) > len(new_sections):
                            self.log('opening connection, sections: {0}'.format(len(block_sections)))
                            # carved path not wide enough
                            for third in neighbor.keys():
                                # find start c that connects to both a and b
                                ac = tuple(sorted([third, path[0]]))
                                bc = tuple(sorted([third, path[1]]))
                                abc = tuple(sorted([third, path[0], path[1]]))
                                if (ac in paths.keys() and bc in paths.keys()):
                                    for p in (ac, bc, abc):
                                        if p not in carved_paths:
                                            carve(p, LAND)                                       
                                    #log('# found %s' % (tuple(sorted([third, path[0], path[1]])),))
                                    new_block_sections = [s for s in self.section(1) if len(s[0]) > 9]
                                    if len(new_block_sections) <= len(new_sections):
                                        # triple connection successful, fix data structures
                                        for p in (ac, bc, abc):
                                            carved_paths.append(p)
                                        break # goes to # connection successful line
                                    # next statement only run in triple not successful
                                    for p in (ac, bc, abc):
                                        if p not in carved_paths:
                                            carve(p, WATER)
                            else:
                                self.log('failed to connect wide path')
                        # connection successful, fix data structures
                        carved_paths.append(path)
                        if len(new_sections) == 1:
                            break
                        else:
                            sections = new_sections
                            self.log('connecting maze, sections: {0}'.format(len(sections)))
                            continue
                    # next statement only runs if connection not found
                    carve(path, WATER)
                else:
                    self.log('failed to connect')
            return carved_paths
                    
        def growing_tree(nodes, carve, visited=[]):
            visited = set(visited)
            carved_paths = []
            
            def prims(cells):
                return randrange(len(cells))
            def recursivebacktracker(cells):
                return -1
            def oldest(cells):
                return 0
            maze_type_report = {prims: 'prims',
                               recursivebacktracker: 'backtrack',
                               oldest: 'growing'}
            maze_type = [f for f, t in maze_type_report.items() if t == self.maze_type][0]
            
            unvisited = [node for node in nodes.keys() if node not in visited]
            next_cell = choice(unvisited)
            cells = [next_cell]
            visited.add(cells[0])
            while len(cells) > 0:
                index = maze_type(cells)
                cell = cells[index]
                unvisited = [node for node in nodes[cell] if not node in visited]
                if len(unvisited) > 0:
                    next_cell = choice(unvisited)
                    carve((cell, next_cell))
                    carved_paths.append(tuple(sorted([cell, next_cell])))
                    visited.add(next_cell)
                    cells.append(next_cell)
                else:
                    cells.pop(index)
            return carved_paths
        
        def set_openness(points, braids, carved_paths, openness, carve, open_braids=[]):
            def carve_braid(open_paths, braids):
                carved_neighbors = build_neighbors(open_paths)            
                braid = sorted(braids,
                               key=lambda path: neighbor_dist(carved_neighbors, *path),
                               reverse=True)[0]
                carve(braid, LAND)
                return braid

            # open initial set of braids
            self.log("set openness to {0} on {1} braids".format(self.openness, len(braids)))
            open_braid_count = int(len(braids) * openness)
            closed_braids = braids[:]
            for _ in range(open_braid_count):
                braid = carve_braid(carved_paths+open_braids, closed_braids)
                open_braids.append(braid)
                closed_braids.remove(braid)
                
            # adjust braids until hill distances are within proper ranges
            min_count = max_count = valid_first_count = 0
            valid_hills = []
            adjusted = False
            while valid_first_count == 0:
                min_count = max_count = valid_first_count = 0
                valid_hills = []
                for i, s_points in enumerate(points):
                    hill_dists = [dist for _, dist in self.get_distances(s_points[0], s_points[1:])]
                    if len(hill_dists) == 0:
                        if len(closed_braids) > 0:
                            braid = closed_braids.pop()
                            carve(braid, WATER)
                            continue
                        else:
                            raise Exception("MapException", "Map closed off")
                    elif min(hill_dists) < self.min_hill_dist:
                        min_count += 1
                    elif max(hill_dists) > self.max_hill_dist:
                        max_count += 1
                    else:
                        if min_count > 0 or stdev(hill_dists) < 2.0*max(hill_dists)/self.players:
                            valid_first_count += 1
                        else:
                            self.log(stdev(hill_dists))
                            max_count += 1
                        valid_hills.append((i, hill_dists, stdev(hill_dists)))
                if valid_first_count == 0:
                    adjusted = True
                    if min_count > max_count:
                        # reduce openness, close 1 braid
                        if len(open_braids) == 0:
                            raise Exception("Openness", "Map too open")
                        braid = open_braids.pop()
                        carve(braid, WATER)
                        closed_braids.append(braid)
                        self.log("decrease openness")
                    elif max_count > min_count:
                        # increase openness, open 1 braid
                        if len(closed_braids) == 0:
                            raise Exception("Openness", "Map too closed")
                        braid = carve_braid(carved_paths+open_braids, closed_braids)
                        open_braids.append(braid)
                        closed_braids.remove(braid)
                        self.log("increase openness")
                    else:
                        raise Exception("Openness", "Map too weird")
                    self.openness = 1.0 * len(open_braids) / len(braids)
            if adjusted:
                self.log("adjust openness to {0}".format(self.openness))
            return open_braids, valid_hills
                    
        def make_euclidean_distance(size):
            rows, cols = size
            dist_table = [ [ sqrt(min(y,cols-y)**2 + min(x,rows-x)**2)
                            for y in range(cols) ]
                          for x in range(rows) ]
            def distance(loc1, loc2, size):
                return dist_table[loc1[0]-loc2[0]][loc1[1]-loc2[1]]
            return distance
                
        def print_points(points, size, tile_size, fd=sys.stderr):
            TILE = [',','.','-',"'"]
            for r in range(size[0]):
                for c in range(size[1]):
                    for i, sym_points in enumerate(points):
                        if (r, c) in sym_points:
                            fd.write(MAP_RENDER[i % 30])
                            break
                    else:
                        fd.write(TILE[(r//tile_size[0] + c//tile_size[1])%len(TILE)])
                fd.write('\n')
            fd.write('\n')

        def stdev(values):
            avg = 1.0*sum(values)/len(values)
            return sqrt(sum([pow(d - avg, 2) for d in values])/len(values))

        def mark_points(points):
            # add point markers for debugging
            for comp, sym_p in enumerate(points):
                for _, (row, col) in enumerate(sym_p):
                    self.map[row][col] = comp % 30

        def cavern(nodes, all_nodes, carve, carve2, cavern_count=7):
            closed = []
            visited = []
            carved_paths = []
            caves = list(all_nodes.keys())
            while len(caves) > 0 and cavern_count > 0:
                # pick random cell
                cave = choice(caves)
                caves.remove(cave)
                if len(all_nodes[cave]) == 0:
                    continue
                #caves = []
                # find surrounding cells
                juxs = []
                for jux in all_nodes[cave]:
                    if jux not in closed:
                        carved_paths.extend(carve((cave, jux)))
                        closed.append(jux)
                        juxs.append(jux)
                if len(juxs) > 0:
                    # clean out cavern walls
                    carve((cave,))
                    for path in combinations(juxs, 2):
                        carved_paths.extend(carve(tuple(sorted(path))))
                        carve(tuple(sorted([cave, path[0], path[1]])))
                    # find paths out of cavern
                    doors = []
                    closed.append(cave)
                    for jux in juxs:
                        carve((jux,))
                        for jux2 in nodes[jux]:
                            if jux2 not in closed:
                                #closed.append(jux2)
                                if jux2 in caves:
                                    caves.remove(jux2)
                                doors.append(tuple(sorted((jux, jux2))))
                    # open doorways to cavern
                    shuffle(doors)
                    for _ in range(len(juxs)//4 + 1):
                        if len(doors) > 0:
                            door = doors.pop()
                            carved_paths.extend(carve2(door))
                    # add cavern cells to visited list for maze carving
                    if len(juxs) > 0:
                        visited.append(cave)
                        visited.extend(juxs)
                    cavern_count -= 1
            return carved_paths, visited
            
        def cell_maze():
            # actual maze code
            tile_size, grid = pick_size(self.grid, self.aspect_ratio)
            points = random_points(tile_size, self.cell_size, self.grandularity)
            sym_points, sym_size = make_symmetric(points, tile_size, self.players, grid, self.v_sym, self.v_step, self.h_sym, self.h_step)
        
            self.report("final parameters")
            self.report('area: {0}'.format(sym_size[0] * sym_size[1]))
            self.report('grid size: {0}'.format(grid))
            self.report('tile size: {0} {1}'.format(tile_size, 1.0 * tile_size[1] / tile_size[0]))
            self.report('map size: {0} {1}'.format((sym_size[0], sym_size[1]),
                                              1.0 * sym_size[1] / sym_size[0]))
            self.log("point count: {0}".format(len(points)))
            
            rows, cols = sym_size
            self.map = [[LAND]* cols for _ in range(rows)]
    
            paths = build_paths(sym_points, sym_size, make_euclidean_distance(sym_size))
            neighbors = build_neighbors(paths.keys())
            paths, neighbors, narrow_paths = remove_narrow_paths(paths, neighbors, sym_points, sym_size)
    
            carved_paths = []
#            carved_paths, visited = cavern(neighbors,
#                                           build_neighbors(paths.keys()),
#                                           lambda path: carve(paths, path, LAND),
#                                           lambda path: carve(paths, path, LAND))        
            carved_paths.extend(growing_tree(neighbors, lambda path: carve(paths, path)))            
            carved_paths = ensure_connected(paths, carved_paths, lambda path, ilk: carve(paths, path, ilk))        

            braids = [path for path in paths.keys() if len(path) == 2 and path not in narrow_paths + carved_paths]
            mirror_braids = sorted([path for path in paths.keys() if len(path) == 2 and path[0] == path[1]], key=lambda path: len(paths[path]))
            braid_paths, valid_hills = set_openness(sym_points, braids, carved_paths, self.openness, lambda path, ilk: carve(paths, path, ilk), mirror_braids)
            carved_paths.extend(braid_paths)
                
            valid_hills.sort(key=lambda valid_hill: (valid_hill[2], -max(valid_hill[1])))
            comp, hill_dists, _ = valid_hills.pop(0)
            first_hills = sym_points[comp]
            self.log("first hill stdev: {0}".format(stdev(hill_dists)))
            for player, (row, col) in enumerate(first_hills):
                self.map[row][col] = player
            map_sym = choice(self.get_map_symmetry())
            all_hills = first_hills[:]
            
            hill_count = None if self.hills is None else self.hills - 1
            while len(valid_hills) > 0:
                if (hill_count is None and random() < 0.5) or hill_count > 0:
                    comp = randrange(0, len(valid_hills))
                    comp, hill_dists, _ = valid_hills.pop(comp)
                    hills = sym_points[comp]
                    hill_dists = list(self.get_distances(hills[0], all_hills, sym_size))
                    if max([dist for _, dist in hill_dists]) > self.max_hill_dist:
                        # a potiential hill is too far away from other hills
                        continue
                    enemies = set([self.map[row][col] for (row, col), dist in
                                   hill_dists if dist < self.min_hill_dist])
                    #log(sym_points)
                    if len(enemies) > 1:
                        # a potential hill is within min distance to 2 enemies
                        continue
                    all_hills.extend(hills)
                    if hill_count is not None:
                        hill_count -= 1
                    for player, (row, col) in enumerate(hills):
                        if player == 0:
                            if len(enemies) == 1:
                                next_player = list(enemies)[0]
                            else:
                                next_player = randrange(0, self.players)
                            self.map[row][col] = next_player
                            # find offset to self
                            first_hill = first_hills[next_player]
                            hill_offset = (first_hill[0] - row, first_hill[1] - col)
                        else:
                            p_row, p_col = self.dest_offset((row, col), self.offset_aim(hill_offset, map_sym[player][1]), sym_size)
                            next_player = self.map[p_row][p_col]
                            self.map[row][col] = next_player
                else:
                    break
            self.fill_small_areas()
            self.make_wider()

        def add_border(size):
            rows, cols = size
            self.map[0] = [WATER] * cols
            self.map[-1] = [WATER] * cols
            for row in range(rows):
                self.map[row][0] = WATER
                self.map[row][-1] = WATER
                
        def corner_hills(size):
            self.map[3][3] = 0
            self.map[3][-4] = 1
            self.map[-4][-4] = 2
            self.map[-4][3] = 3
                
        def caverns():
            #self.cell_width = max(self.cell_width, 4)
            #self.cell_size += max(self.cell_size, 9.0)
            # actual maze code
            tile_size, grid = pick_size(self.grid, self.aspect_ratio)
            points = random_points(tile_size, self.cell_size)
            sym_points, sym_size = make_symmetric(points, tile_size, self.players, grid, self.v_sym, self.v_step, self.h_sym, self.h_step)
        
            self.report("final parameters")
            self.report('area: {0}'.format(sym_size[0] * sym_size[1]))
            self.report('grid size: {0}'.format(grid))
            self.report('tile size: {0} {1}'.format(tile_size, 1.0 * tile_size[1] / tile_size[0]))
            self.report('map size: {0} {1}'.format((sym_size[0], sym_size[1]),
                                              1.0 * sym_size[1] / sym_size[0]))
            self.log("point count: {0}".format(len(points)))
            
            rows, cols = sym_size
            self.map = [[LAND]* cols for _ in range(rows)]
    
            paths = build_paths(sym_points, sym_size, make_euclidean_distance(sym_size))
            for path in paths.keys():
                if len(path) == 1:
                    carve(paths, path, WATER)
                else:
                    carve(paths, path, LAND)
                    
#            if len(self.section(1)) > 1:
#                sys.exit()
            neighbors = build_neighbors(paths.keys())
            while True:
                n = choice(list(neighbors.keys()))
                nw = neighbors[n][:]
                if len(nw) < 4:
                    continue
                ns = randrange(1,len(nw)-1)
                nl = nw[:ns]
                nr = nw[ns:]
                for path in combinations(nl,2):
                    if path in paths:
                        carve(paths, path, WATER)
                for path in combinations(nr,2):
                    if path in paths:
                        carve(paths, path, WATER)
                carve(paths, (n,), LAND)
                break
                    
            mark_points(sym_points)
            self.toText()
            return
                    
            paths, neighbors, narrow_paths = remove_narrow_paths(paths, neighbors, sym_points, sym_size)
    
            carved_paths = growing_tree(neighbors, lambda path: carve(paths, path))
            carved_paths = ensure_connected(paths, carved_paths, lambda path, ilk: carve(paths, path, ilk))        

            braids = [path for path in paths.keys() if len(path) == 2 and path not in narrow_paths + carved_paths]
            mirror_braids = sorted([path for path in paths.keys() if len(path) == 2 and path[0] == path[1]], key=lambda path: len(paths[path]))
            braid_paths, valid_hills = set_openness(sym_points, braids, carved_paths, self.openness, lambda path, ilk: carve(paths, path, ilk), mirror_braids)
            carved_paths.extend(braid_paths)

                
            valid_hills.sort(key=lambda valid_hill: (valid_hill[2], -max(valid_hill[1])))
            comp, hill_dists, _ = valid_hills.pop(0)
            first_hills = sym_points[comp]
            self.log("first hill stdev: {0}".format(stdev(hill_dists)))
            for player, (row, col) in enumerate(first_hills):
                self.map[row][col] = player
            map_sym = choice(self.get_map_symmetry())
            all_hills = first_hills[:]
            
            hill_count = None if self.hills is None else self.hills - 1
            while len(valid_hills) > 0:
                if (hill_count is None and random() < 0.5) or hill_count > 0:
                    comp = randrange(0, len(valid_hills))
                    comp, hill_dists, _ = valid_hills.pop(comp)
                    hills = sym_points[comp]
                    hill_dists = list(self.get_distances(hills[0], all_hills, sym_size))
                    if max([dist for _, dist in hill_dists]) > self.max_hill_dist:
                        # a potiential hill is too far away from other hills
                        continue
                    enemies = set([self.map[row][col] for (row, col), dist in
                                   hill_dists if dist < self.min_hill_dist])
                    #log(sym_points)
                    if len(enemies) > 1:
                        # a potential hill is within min distance to 2 enemies
                        continue
                    all_hills.extend(hills)
                    if hill_count is not None:
                        hill_count -= 1
                    for player, (row, col) in enumerate(hills):
                        if player == 0:
                            if len(enemies) == 1:
                                next_player = list(enemies)[0]
                            else:
                                next_player = randrange(0, self.players)
                            self.map[row][col] = next_player
                            # find offset to self
                            first_hill = first_hills[next_player]
                            hill_offset = (first_hill[0] - row, first_hill[1] - col)
                        else:
                            p_row, p_col = self.dest_offset((row, col), self.offset_aim(hill_offset, map_sym[player][1]), sym_size)
                            next_player = self.map[p_row][p_col]
                            self.map[row][col] = next_player
                else:
                    break
            self.fill_small_areas()
            self.make_wider()
                    
        cell_maze()
        
def main():
    parser = OptionParser()
    parser.add_option("-s", "--seed", dest="seed", type="int",
                        help="random seed")
    parser.add_option("-p", "--players", dest="players", type="int",
                        help="number of players")
    parser.add_option("-o", "--openness", dest="openness", type="float",
                        help="openness of map (0.0 to 1.0)")
    parser.add_option("-a", "--area", dest="area", type="int",
                        help="area of map")
    parser.add_option("-w", "--cell_width", dest="cell_width", type="float",
                      help="cell width (or width of walls)")
    parser.add_option("-c", "--cell_size", dest="cell_size", type="float",
                      help="cell size")
    parser.add_option("-g", "--grid", dest="grid", type="int", nargs=2,
                      help="grid layout (product must equal players)")
    parser.add_option("--v_sym", dest="v_sym",
                      choices=["copy", "mirror", "rotate", "shear"],
                      help="vertical symmetry")
    parser.add_option("--v_step", dest="v_step", type="int",
                      help="vertical shearing step")
    parser.add_option("--h_sym", dest="h_sym",
                      choices=["copy", "mirror", "rotate", "shear"],
                      help="horizontal symmetry")
    parser.add_option("--h_step", dest="h_step", type="int",
                      help="horizontal shearing step")
    parser.add_option("-r", "--ratio", dest="aspect_ratio", type="float",
                      help="aspect ratio of final map")
    parser.add_option("-m", "--maze", dest="maze_type",
                      choices=["backtrack", "prims", "growing"],
                      help="maze type for carving passages")
    parser.add_option("--hills", dest="hills", type="int",
                      help="hills per player")
    parser.add_option("--grandularity", dest="grandularity", type="int",
                      help="align random points on a grid")
    
    opts, _ = parser.parse_args(sys.argv)

    options = {key: value for key, value in vars(opts).items() if value is not None}
    new_map = CellMazeMap(options)
    
    # check that all land area is accessible
    reason = new_map.generate()
    if not reason:
        reason = new_map.allowable(check_sym=True, check_dist=True)
    exit_code = 0
    if reason is not None:
        new_map.toText(sys.stderr)
        print('# ' + reason)
        exit_code = 1
        sys.exit(exit_code)
        
    new_map.toText()
    #new_map.toFile()

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = heightmap
#!/usr/bin/env python
from map import *
from random import randint, choice
from collections import defaultdict

class HeightMapMap(Map):
    def __init__(self, options={}):
        super(HeightMapMap, self).__init__(options)
        self.name = 'height_map'
        self.rows = options.get('rows', (40,120))
        self.cols = options.get('cols', (40,120))
        self.players = options.get('players', (2,4))
        self.land = options.get('land', (85, 90))

    def generate_heights(self, size):
        rows, cols = size

        # initialize height map
        height_map = [[0]*cols for _ in range(rows)]

        # cut and lift
        iterations = 1000
        for _ in range(iterations):
            row = randint(0, rows-1)
            col = randint(0, cols-1)
            radius = randint(5, (rows+cols)/4)
            radius2 = radius**2
            for d_row in range(-radius, radius+1):
                for d_col in range(-radius, radius+1):
                    h_row = (row + d_row) % rows
                    h_col = (col + d_col) % cols
                    if self.euclidean_distance2((row, col), (h_row, h_col), (rows, cols)) <= radius2:
                        height_map[h_row][h_col] += 1
        return height_map

    def normalize(self, hmap):
        rows = len(hmap)
        cols = len(hmap[0])
        min_height = min([min(hrow) for hrow in hmap])
        for row in range(rows):
            for col in range(cols):
                hmap[row][col] -= min_height

    def local_min(self, hmap):
        rows = len(hmap)
        cols = len(hmap[0])
        min_list = []
        for row in range(rows):
            for col in range(cols):
                for d_row, d_col in ((1,0), (0,1), (-1,0), (0,-1)):
                    h_row = (row + d_row) % rows
                    h_col = (col + d_col) % cols
                    if hmap[h_row][h_col] < hmap[row][col]:
                        break
                else:
                    min_list.append((row, col))
        return min_list

    def generate_rivers(self, hmap):
        rows = len(hmap)
        cols = len(hmap[0])

        # new height map
        min_list = self.local_min(hmap)
        self.normalize(hmap)
        water_map = [[0] * cols for _ in range(rows)]

        # place drop of water, follow to lowest point
        for w_row in range(rows):
            for w_col in range(cols):
                water_path = []
                c_row, c_col = w_row, w_col
                while True:
                    water_path.append((c_row, c_col))
                    water_map[c_row][c_col] += 1
                    h = defaultdict(list) # used to find lowest point around square
                    for d_row, d_col in ((1,0), (0,1), (-1,0), (0,-1)):
                        h_row = (c_row + d_row) % rows
                        h_col = (c_col + d_col) % cols
                        if not (h_row, h_col) in water_path:
                            h[hmap[h_row][h_col]] += [(h_row, h_col)]
                    # select randomly if there are 2 squares at the same height
                    if len(h) == 0:
                        # no space left
                        break
                    else:
                        min_height = min(h.keys())
                        if min_height >= hmap[c_row][c_col]:
                            # point lower, move
                            c_row, c_col = choice(h[min_height])
                        else:
                            # no point lower
                            break
        return water_map

    def generate(self):
        # pick random full size for map
        rows = self.get_random_option(self.rows)
        cols = self.get_random_option(self.cols)

        # ensure map rows:cols ratio is within 2:1
        while cols < rows // 2 or cols > rows * 2:
            cols = self.get_random_option(self.cols)

        # calc max players that can be tiled
        row_max = rows//16
        col_max = cols//16
        player_max = row_max*col_max

        players = self.get_random_option(self.players)
        # ensure player count choosen is within max
        while players > player_max:
            players = self.get_random_option(self.players)

        # pick random grid size
        # ensure grid rows < row_max
        # ensure grid cols < col_max
        divs = [(i, players//i)
                for i in range(1,min(players+1, row_max+1))
                if players % i == 0
                    and players//i < col_max]
        if len(divs) == 0:
            # there were no acceptable grid sizes for map
            # usually do to a prime number of players which has to be 1xN
            return self.generate()
        row_sym, col_sym = choice(divs)

        # fix dimensions for even tiling
        rows //= row_sym
        cols //= col_sym

        # get percent of map that should be land
        land = self.get_random_option(self.land)

        height_map = self.generate_heights((rows, cols))
        height_map = self.generate_rivers(height_map)

        # create histogram
        histo = defaultdict(int)
        for height_row in height_map:
            for height in height_row:
                histo[height] += 1

        # find sea and snow levels
        map_area = rows * cols
        sea_level = min(histo.keys())
        snow_level = max(histo.keys())
        max_water = map_area * (100 - land) // 100
        sea_area = histo[sea_level]
        snow_area = histo[snow_level]
        while sea_area + snow_area < max_water:
            sea_level += 1
            sea_area += histo[sea_level]
            if sea_area + snow_area >= max_water:
                break
            snow_level -= 1
            snow_area += histo[snow_level]

        # initialize map
        self.map = [[LAND]*cols for _ in range(rows)]

        # place salty and frozen water
        for row in range(rows):
            for col in range(cols):
                if (height_map[row][col] <= sea_level
                        or height_map[row][col] >= snow_level):
                    self.map[row][col] = WATER
        #self.toText()
        self.fill_small_areas()

        # check too make sure too much wasn't filled in, only 2 percent of area
        areas = self.section(0)
        water_area = map_area - len(areas[0][0])
        added_area = water_area - snow_area - sea_area
        if map_area * 2 // 100 < added_area:
            return self.generate()

        # place player start in largest unblockable section
        areas = self.section()
        row, col = choice(areas[0][0])
        self.map[row][col] = ANTS
        # center ant in section
        d_row = rows//2 - row
        d_col = cols//2 - col
        self.translate((d_row, d_col))

        # finish map
        #self.tile((row_sym, col_sym))
        self.make_wider()

def main():
    new_map = HeightMapMap()
    new_map.generate()

    # check that all land area is accessable
    #while new_map.allowable() != None:
        #new_map.generate()

    new_map.toText()

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = map
#!/usr/bin/env python
import sys
from random import randint, choice, seed
from collections import deque
from itertools import product
try:
    from sys import maxint
except ImportError:
    from sys import maxsize as maxint
from copy import deepcopy
import heapq
from collections import defaultdict
import os
from optparse import OptionParser

MY_ANT = 0
ANTS = 0
DEAD = -1
LAND = -2
FOOD = -3
WATER = -4
UNSEEN = -5

PLAYER_ANT = 'abcdefghij'
HILL_ANT = string = 'ABCDEFGHIJ'
PLAYER_HILL = string = '0123456789'
MAP_OBJECT = '?%*.!'
MAP_RENDER = PLAYER_HILL + HILL_ANT + PLAYER_ANT + MAP_OBJECT
ALLOWABLE = list(range(30)) + [LAND, FOOD, WATER]
#MAP_RENDER = ["{0:02}".format(n) for n in range(100)] + [' ?', ' %', ' *', ' .', ' !']

AIM = {'n': (-1, 0),
       'e': (0, 1),
       's': (1, 0),
       'w': (0, -1)}

class Map(object):
    def __init__(self, options={}):
        super(Map, self).__init__()
        self.name = options.get('name', 'blank')
        self.map = [[]]
        self.reports = []

        self.report('map type: {0}'.format(self.name))
        self.random_seed = options.get('seed', None)
        if self.random_seed == None:
            self.random_seed = randint(-maxint-1, maxint)
        seed(self.random_seed)
        self.report('random seed: {0}'.format(self.random_seed))
        
    def log(self, msg):
        msg = '# ' + str(msg) + '\n'
        sys.stderr.write(msg)
    
    def report(self, msg):
        msg = '# ' + str(msg) + '\n'
        self.reports.append(msg)
    
    def generate(self):
        raise Exception("Not Implemented")

    def get_random_option(self, option):
        if type(option) == tuple:
            if len(option) == 2:
                return randint(*option)
            elif len(option) == 1:
                return option[0]
            elif len(option) == 0:
                raise Exception("Invalid option: 0 length tuple")
            else:
                return choice(option)
        elif type(option) in (list, set):
            if len(option) > 0:
                return choice(option)
            else:
                raise Exception("Invalid option: 0 length list")
        elif type(option) in (int, float, str):
            return option
        else:
            raise Exception("Invalid option: type {0} not supported".format(type(option)))

    def toPNG(self, fd=sys.stdout):
        raise Exception("Not Implemented")

    def toText(self, fd=sys.stdout):
        players = set()
        for row in self.map:
            for c in row:
                if c >= ANTS:
                    players.add(c)
        for msg in self.reports:
            fd.write(msg)
        fd.write('players {0}\nrows {1}\ncols {2}\n'.format(len(players),
                                                            len(self.map),
                                                            len(self.map[0])))
        for r, row in enumerate(self.map):
            fd.write("m {0}\n".format(''.join([MAP_RENDER[c] for c in row])))

    def toFile(self, filename=None):
        if filename is None:
            filename = self.name.replace(' ', '_') + '_p' + '{0:02}'.format(self.players) + '_'
            filename += ('{0:02}'.format(max(map(lambda x: 0 if not x.isdigit() else int(x),
                            [f[len(filename):len(filename)+2] for f in os.listdir('.')
                             if f.startswith(filename)]+['0'])) + 1))
            filename += '.map'
        with open(filename, 'w') as mapfile:
            self.toText(mapfile)

    def manhatten_distance(self, loc1, loc2, size):
        rows, cols = size
        row1, col1 = loc1
        row2, col2 = loc2
        row1 = row1 % rows
        row2 = row2 % rows
        col1 = col1 % cols
        col2 = col2 % cols
        d_col = min(abs(col1 - col2), cols - abs(col1 - col2))
        d_row = min(abs(row1 - row2), rows - abs(row1 - row2))
        return d_row + d_col

    def euclidean_distance2(self, loc1, loc2, size):
        rows, cols = size
        row1, col1 = loc1
        row2, col2 = loc2
        row1 = row1 % rows
        row2 = row2 % rows
        col1 = col1 % cols
        col2 = col2 % cols
        d_col = min(abs(col1 - col2), cols - abs(col1 - col2))
        d_row = min(abs(row1 - row2), rows - abs(row1 - row2))
        return d_row**2 + d_col**2

    def get_distances(self, start_loc, end_locs, size=None):
        'get a list of distances from 1 location to a bunch of others'
        end_locs = end_locs[:]
        if size == None:
            rows, cols = len(self.map), len(self.map[0])
        else:
            rows, cols = size
        visited = {}
        open_nodes = deque()
        open_nodes.append((start_loc, 0))
        if start_loc in end_locs:
            yield open_nodes[-1]
            end_locs.remove(start_loc)
        while open_nodes and len(end_locs) > 0:
            (row, col), dist = open_nodes.popleft()
            for n_loc in [((row + 1) % rows, col),
                          ((row - 1) % rows, col),
                          (row, (col + 1) % cols),
                          (row, (col - 1) % cols)]:
                if n_loc not in visited:
                    if self.map[n_loc[0]][n_loc[1]] != WATER:
                        new_dist = dist + 1
                        visited[n_loc] = new_dist
                        open_nodes.append((n_loc, new_dist))
                        if n_loc in end_locs:
                            #print('# get distances: {0}'.format(open_nodes[-1]))
                            yield open_nodes[-1]
                            end_locs.remove(n_loc)
                    else:
                        visited[n_loc] = None
    
    def get_path(self, loc1, loc2, size, block=1, ignore=None):
        'get path from 1 location to another as a list of locations'
        # make a node class to calc F, G and H automatically
        def nodeMaker(distance=self.manhatten_distance, dest=loc2, size=size):
            class Node:
                def __init__(self, loc, parent, G):
                    self.loc = loc
                    self.parent = parent
                    self.G = G
                    self.H = distance(loc, dest, size)
                    self.F = self.G + self.H
                def __lt__(self, other):
                    return self.F < other.F
                    
            return Node
        Node = nodeMaker()
        
        # heap list to help get lowest F cost
        open_nodes = []
        # lists indexed by location
        closed_list = {}
        open_list = {}
        block_offsets = list(product(range(block), range(block)))
        
        def add_open(node, open_nodes=open_nodes, open_list=open_list):
            heapq.heappush(open_nodes, (node.F, node))
            open_list[node.loc] = node
        
        def get_open(open_nodes=open_nodes, open_list=open_list):
            _, node = heapq.heappop(open_nodes)
            del open_list[node.loc]
            return node
        
        def replace_open(new_node, open_nodes=open_nodes, open_list=open_list):
            old_node = open_list[new_node.loc]
            open_nodes.remove((old_node.F, old_node))
            heapq.heapify(open_nodes)
            add_open(new_node)

        def build_path(node):
            path = []
            while node:
                path.append(node.loc)
                node = node.parent
            path.reverse()
            return path            
        
        # A* search
        # add starting square to open list
        if block > 1:
            # find open block position on starting location
            for o_loc in product(range(-block+1,1), range(-block+1,1)):
                s_loc = self.dest_offset(loc1, o_loc, size)
                for d_loc in block_offsets:
                    b_row, b_col = self.dest_offset(s_loc, d_loc, size)
                    if self.map[b_row][b_col] == WATER and (ignore is None or (b_row, b_col) not in ignore):
                        break
                else:
                    # no water found, use this start location
                    add_open(Node(s_loc, None, 0))
                    break
        else:
            add_open(Node(loc1, None, 0))
        while len(open_nodes) > 0:
            # get lowest F cost node
            node = get_open()
            # switch to closed list
            closed_list[node.loc] = node
            # check if found distination
            if block > 1:
                for d_loc in block_offsets:
                    if loc2 == self.dest_offset(node.loc, d_loc, size):
                        return build_path
            else:
                if node.loc == loc2:
                    # build path
                    return build_path(node)
            # expand node
            for d in AIM:
                loc = self.destination(node.loc, d, size)
                # ignore if closed or not traversable
                # ignore list is a set of locations to assume as traversable
                # block is a block size that must fit, the loc is the upper left corner
                if loc in closed_list:
                    continue
                skip = False
                for d_loc in block_offsets:
                    b_row, b_col = self.dest_offset(loc, d_loc, size)
                    if self.map[b_row][b_col] == WATER and (ignore is None or (b_row, b_col) not in ignore):
                        skip = True
                        break
                if skip:
                    continue
                    
                if loc in open_list:
                    old_node = open_list[loc]
                    # check for shortest path
                    if node.G + 1 < old_node.G:
                        # replace node
                        replace_open(Node(loc, node, node.G + 1))
                else:
                    # add to open list
                    add_open(Node(loc, node, node.G + 1))
        return None
                                        
    def destination(self, loc, direction, size):
        rows, cols = size
        row, col = loc
        d_row, d_col = AIM[direction]
        return ((row + d_row) % rows, (col + d_col) % cols)

    def dest_offset(self, loc, d_loc, size):
        rows, cols = size
        d_row, d_col = d_loc
        row, col = loc
        return ((row + d_row) % rows, (col + d_col) % cols)
    
    def section(self, block_size=1):
        '''split map into sections that can be travesered by a block
        
        block_size 1 is a 3x3 block (1 step each direction)'''
        rows = len(self.map)
        cols = len(self.map[0])
        visited = [[False] * cols for _ in range(rows)]

        def is_block_free(loc):
            row, col = loc
            for d_row in range(-block_size, block_size+1):
                for d_col in range(-block_size, block_size+1):
                    h_row = (row + d_row) % rows
                    h_col = (col + d_col) % cols
                    if self.map[h_row][h_col] == WATER:
                        return False
            return True

        def mark_block(loc, m, ilk):
            row, col = loc
            for d_row in range(-block_size, block_size+1):
                for d_col in range(-block_size, block_size+1):
                    h_row = (row + d_row) % rows
                    h_col = (col + d_col) % cols
                    m[h_row][h_col] = ilk

        def find_open_spot():
            for row, col in product(range(rows), range(cols)):
                if is_block_free((row, col)) and not visited[row][col]:
                    return (row, col)
            else:
                return None

        # list of contiguous areas
        areas = []

        # flood fill map for each separate area
        while find_open_spot():
            # maintain lists of visited and seen squares
            # visited will not overlap, but seen may
            area_visited = [[False] * cols for _ in range(rows)]
            area_seen = [[False] * cols for _ in range(rows)]

            squares = deque()
            row, col = find_open_spot()

            #seen_area = open_block((row, col))
            squares.appendleft((row, col))

            while len(squares) > 0:
                row, col = squares.pop()
                visited[row][col] = True
                area_visited[row][col] = True
                area_seen[row][col] = True
                for d_row, d_col in ((1,0), (0,1), (-1,0), (0,-1)):
                    s_row = (row + d_row) % rows
                    s_col = (col + d_col) % cols
                    if not visited[s_row][s_col] and is_block_free((s_row, s_col)):
                        visited[s_row][s_col] = True
                        mark_block((s_row, s_col), area_seen, True)
                        squares.appendleft((s_row, s_col))

            # check percentage filled
            #areas.append(1.0 * seen_area / land_area)
            visited_list = []
            seen_list = []
            for row in range(rows):
                for col in range(cols):
                    if area_visited[row][col]:
                        visited_list.append((row, col))
                    elif area_seen[row][col]:
                        seen_list.append((row, col))
            areas.append([visited_list, seen_list])

        # sort by largest area first
        areas.sort(key=lambda area: len(area[0]), reverse=True)
        return areas

    def fill_small_areas(self):
        # keep largest contiguous area as land, fill the rest with water
        count = 0
        areas = self.section(0)
        for area in areas[1:]:
            for row, col in area[0]:
                self.map[row][col] = WATER
                count += 1
        #print("fill {0}".format(count))

    def make_wider(self):
        # make sure the map has more columns than rows
        rows = len(self.map)
        cols = len(self.map[0])
        if rows > cols:
            map = [[LAND] * rows for _ in range(cols)]
            for row in range(rows):
                for col in range(cols):
                    map[col][row] = self.map[row][col]
            self.map = map

    def tile(self, grid):
        rows = len(self.map)
        cols = len(self.map[0])
        row_sym, col_sym = grid

        # select random mirroring
        row_mirror = 0
        if row_sym % 2 == 0:
            #if row_sym % 4 == 0:
            #    row_mirror = choice((0,4))
            row_mirror = choice((row_mirror, 2))
            row_mirror = 2

        col_mirror = 0
        if col_sym % 2 == 0:
            #if col_sym % 4 == 0:
            #    col_mirror = choice((0,4))
            col_mirror = choice((col_mirror, 2))
            col_mirror = 2

        # perform tiling
        t_rows = rows * row_sym
        t_cols = cols * col_sym
        ant = 0
        map = [[LAND]*t_cols for _ in range(t_rows)]
        for t_row in range(t_rows):
            for t_col in range(t_cols):
                # detect grid location
                g_row = t_row // rows
                g_col = t_col // cols
                if row_mirror == 2 and g_row % 2 == 1:
                    row = rows - 1 - (t_row % rows)
                else:
                    row = t_row % rows
                if col_mirror == 2 and g_col % 2 == 1:
                    col = cols - 1 - (t_col % cols)
                else:
                    col = t_col % cols
                try:
                    map[t_row][t_col] = self.map[row][col]
                except:
                    print("issue")
                if self.map[row][col] == ANTS:
                    map[t_row][t_col] = ant
                    ant += 1
        self.map = map

    def translate(self, offset):
        d_row, d_col = offset
        rows = len(self.map)
        cols = len(self.map[0])
        map = [[LAND] * cols for _ in range(rows)]
        for row in range(rows):
            for col in range(cols):
                o_row = (d_row + row) % rows
                o_col = (d_col + col) % cols
                map[o_row][o_col] = self.map[row][col]
        self.map = map

    def offset_aim(self, offset, aim):
        """ Return proper offset given an orientation
        """
        # eight possible orientations
        row, col = offset
        if aim == 0:
            return offset
        elif aim == 1:
            return -row, col
        elif aim == 2:
            return row, -col
        elif aim == 3:
            return -row, -col
        elif aim == 4:
            return col, row
        elif aim == 5:
            return -col, row
        elif aim == 6:
            return col, -row
        elif aim == 7:
            return -col, -row

    def map_similar(self, loc1, loc2, aim, player):
        """ find if map is similar given loc1 aim of 0 and loc2 ant of player
            return a map of translated enemy locations
        """
        enemy_map = {}
        rows = len(self.map)
        cols = len(self.map[0])
        size = (rows, cols)
        for row in range(rows):
            for col in range(cols):
                row0, col0 = self.dest_offset(loc1, (row, col), size)
                row1, col1 = self.dest_offset(loc2, self.offset_aim((row, col), aim), size)
                # compare locations
                ilk0 = self.map[row0][col0]
                ilk1 = self.map[row1][col1]
                if ilk0 == 0 and ilk1 != player:
                    # friendly ant not in same location
                    return None
                elif ilk0 > 0 and (ilk1 < 0 or ilk1 == player):
                    # enemy ant not in same location
                    return None
                elif ilk0 < 0 and ilk1 != ilk0:
                    # land or water not in same location
                    return None
                if ilk0 >= 0 and enemy_map != None:
                    enemy_map[ilk0] = ilk1
        return enemy_map

    def get_map_symmetry(self):
        """ Get orientation for each starting hill
        """
        size = (len(self.map), len(self.map[0]))
        # build list of all hills
        player_hills = defaultdict(list) # list of hills for each player
        for row, squares in enumerate(self.map):
            for col, square in enumerate(squares):
                if 0 <= square < 10:
                    player_hills[square].append((row, col))
        if len(player_hills) > 0:
            # list of
            #     list of tuples containing
            #         location, aim, and enemy map dict
            orientations = [[(player_hills[0][0], 0,
                dict([(i, i, ) for i in range(self.players)]))]]
            for player in range(1, self.players):
                if len(player_hills[player]) != len(player_hills[0]):
                    raise Exception("Invalid map",
                                    "This map is not symmetric.  Player 0 has {0} hills while player {1} has {2} hills."
                                    .format(len(player_hills[0]), player, len(player_hills[player])))
                new_orientations = []
                for player_hill in player_hills[player]:
                    for aim in range(8):
                    # check if map looks similar given the orientation
                        enemy_map = self.map_similar(player_hills[0][0], player_hill, aim, player)
                        if enemy_map != None:
                            # produce combinations of orientation sets
                            for hill_aims in orientations:
                                new_hill_aims = deepcopy(hill_aims)
                                new_hill_aims.append((player_hill, aim, enemy_map))
                                new_orientations.append(new_hill_aims)
                orientations = new_orientations
                if len(orientations) == 0:
                    raise Exception("Invalid map",
                                    "This map is not symmetric. Player {0} does not have an orientation that matches player 0"
                                    .format(player))
            # ensure types of hill aims in orientations are symmetric
            # place food set and double check symmetry
            valid_orientations = []
            for hill_aims in orientations:
                fix = []
                for loc, aim, enemy_map in hill_aims:
                    row, col = self.dest_offset(loc, self.offset_aim((1,2), aim), size)
                    fix.append(((row, col), self.map[row][col]))
                    self.map[row][col] = FOOD
                for loc, aim, enemy_map in hill_aims:
                    if self.map_similar(hill_aims[0][0], loc, aim, enemy_map[0]) is None:
                        break
                else:
                    valid_orientations.append(hill_aims)
                for (row, col), ilk in reversed(fix):
                    self.map[row][col] = ilk
            if len(valid_orientations) == 0:
                raise Exception("Invalid map",
                                "There are no valid orientation sets")
            return valid_orientations
        else:
            raise Exception("Invalid map",
                            "There are no player hills")
            
    def allowable(self, check_sym=True, check_dist=True):
        # Maps are limited to at most 200 squares for either dimension
        size = (len(self.map), len(self.map[0]))
        if size[0] > 200 or size[1] > 200:
            return "Map is too large"

        # Maps are limited to 10 players
        players = set()
        hills = {}
        for row, squares in enumerate(self.map):
            for col, square in enumerate(squares):
                if square not in ALLOWABLE:
                    return "Maps are limited to 10 players and must contain the following characters: A-Ja-j0-9.*%"
                elif square >= 0:
                    players.add(square % 10)
                    if square < 10:
                        hills[(row, col)] = square

        # Maps are limited in area by number of players
        if size[0] * size[1] > min(25000, 5000 * len(players)):
            return "Map area is too large for player count"
        if size[0] * size[1] < 900 * len(players):
            return "Map area is too small for player count"

        # Maps are limited in area by number of hills
        if size[0] * size[1] < 500 * len(hills):
            return "Map has too many hills for its size"

        # Maps must be symmetric
        if check_sym:
            try:
                self.get_map_symmetry()
            except Exception as e:
                return "Map is not symmetric: " + str(e)

        # Hills must be between 20 and 150 steps away from other hills
        # Hills must be more than 5 distance apart
        hill_min = False
        hill_max = False
        hill_range = False
        self.report('hill distance ' + ' '.join(['{0[0]:>3},{0[1]:>3}'.format(loc) for loc in hills.keys()]))
        for hill_loc in hills.keys():
            hill_dists = {point: dist for point, dist in self.get_distances(hill_loc, hills.keys(), size)}
            hill_msg = '      {0[0]:>3},{0[1]:>3} '.format(hill_loc)
            for hill_loc2 in hills.keys():
                if hill_loc != hill_loc2 and self.euclidean_distance2(hill_loc, hill_loc2, size) <= 25:
                    hill_range = True
                hill_msg += '{0:>7} '.format(hill_dists[hill_loc2])
            self.report(hill_msg)
            if min([dist for point, dist in hill_dists.items() if self.map[point[0]][point[1]] != self.map[hill_loc[0]][hill_loc[1]] ]) < 20:
                hill_min = True
            if max(hill_dists.values()) > 150:
                hill_max = True
        if hill_min and hill_max:
            return "Map has hills too close and too far"
        elif hill_min:
            return "Map has hills too close"
        elif hill_max:
            return "Map has hills too far"
        elif hill_range:
            return "Map has hills within attack range"

        # Maps must not contain islands
        # all squares must be accessible from all other squares
        # fill small areas can fix this
        areas = self.section(0)
        if len(areas) > 1:
            area_visited, _ = areas[0]
            for loc in area_visited:
                if self.map[loc[0]][loc[1]] == LAND:
                    self.map[loc[0]][loc[1]] = UNSEEN
            return "Map not 100% accessible"

        # find section with first hill
        areas = self.section(1)
        first_hill_loc = list(hills.keys())[0]
        area_visited = area_seen = None
        for area_visited, area_seen in areas:
            if first_hill_loc in area_seen or first_hill_loc in area_visited:
                break
        else:
            return "Could not find first hill area"

        for hill_loc in hills.keys():
            if hill_loc not in area_seen and hill_loc not in area_visited:
                return "Starting hills not in same unblockable area"

        return None

    def fromFile(self, fd):
        """ Parse the map_text into a more friendly data structure """
        ant_list = None
        hill_list = []
        hill_count = defaultdict(int)
        width = height = None
        water = []
        food = []
        ants = defaultdict(list)
        hills = defaultdict(list)
        row = 0
        score = None
        hive = None
        num_players = None
    
        #for line in map_text.split('\n'):
        for line in fd:
            line = line.strip()
    
            # ignore blank lines and comments
            if not line or line[0] == '#':
                continue
    
            key, value = line.split(' ', 1)
            key = key.lower()
            if key == 'cols':
                width = int(value)
            elif key == 'rows':
                height = int(value)
            elif key == 'players':
                num_players = int(value)
                if num_players < 2 or num_players > 10:
                    raise Exception("map",
                                    "player count must be between 2 and 10")
            elif key == 'm':
                if ant_list is None:
                    if num_players is None:
                        raise Exception("map",
                                        "players count expected before map lines")
                    ant_list = [chr(97 + i) for i in range(num_players)]
                    hill_list = list(map(str, range(num_players)))
                    hill_ant = [chr(65 + i) for i in range(num_players)]
                if len(value) != width:
                    raise Exception("map",
                                    "Incorrect number of cols in row %s. "
                                    "Got %s, expected %s."
                                    %(row, len(value), width))
                for col, c in enumerate(value):
                    if c in ant_list:
                        ants[ant_list.index(c)].append((row,col))
                    elif c in hill_list:
                        hills[hill_list.index(c)].append((row,col))
                        hill_count[hill_list.index(c)] += 1
                    elif c in hill_ant:
                        ants[hill_ant.index(c)].append((row,col))
                        hills[hill_ant.index(c)].append((row,col))
                        hill_count[hill_ant.index(c)] += 1
                    elif c == MAP_OBJECT[FOOD]:
                        food.append((row,col))
                    elif c == MAP_OBJECT[WATER]:
                        water.append((row,col))
                    elif c != MAP_OBJECT[LAND]:
                        raise Exception("map",
                                        "Invalid character in map: %s" % c)
                row += 1
    
        if height != row:
            raise Exception("map",
                            "Incorrect number of rows.  Expected %s, got %s"
                            % (height, row))
    
        # look for ants without hills to invalidate map for a game
        for hill, count in hill_count.items():
            if count == 0:
                raise Exception("map",
                                "Player %s has no starting hills"
                                % hill)
                        
        map_data = {
                        'size':        (height, width),
                        'num_players': num_players,
                        'hills':       hills,
                        'ants':        ants,
                        'food':        food,
                        'water':       water
                    }  
        
        # initialize size
        self.height, self.width = map_data['size']
        self.land_area = self.height*self.width - len(map_data['water'])

        # initialize map
        # this matrix does not track hills, just ants
        self.map = [[LAND]*self.width for _ in range(self.height)]

        # initialize water
        for row, col in map_data['water']:
            self.map[row][col] = WATER

        # for new games
        # ants are ignored and 1 ant is created per hill
        # food is ignored
        # for scenarios, the map file is followed exactly

        # initialize hills
        for owner, locs in map_data['hills'].items():
            for loc in locs:
                self.map[loc[0]][loc[1]] = owner
        self.players = num_players

def main():
    parser = OptionParser()
    parser.add_option("-f", "--filename", dest="filename",
                        help="filename to check for allowable map")
    parser.add_option("-n", "--name", dest="name",
                      help="name of map file to create")
    parser.add_option("-q", "--quiet", action="store_true", default=False,
                      help="Do not output map data to console")

    opts, _ = parser.parse_args(sys.argv)
    new_map = Map()
    if opts.filename:
        with open(opts.filename) as f:
            new_map.fromFile(f)
    else:
        new_map.fromFile(sys.stdin)
    errors = new_map.allowable()
    if errors:
        if opts.filename:
            print(opts.filename)
        print(errors)
        sys.exit(1)
    else:
        if opts.name:
            new_map.name = opts.name
            new_map.toFile()
        else:
            if not opts.quiet:
                new_map.toText()

    #options = {key: value for key, value in vars(opts).items() if value is not None}

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = mapgen
#!/usr/bin/env python

import math
import random
from collections import deque
import sys
from optparse import OptionParser

#direction information
cdirections = ['N', 'E', 'S', 'W']
directions = {'N': (-1,0), 'S': (1,0), 'E': (0,1), 'W': (0,-1)}

#game parameters
min_players = 2
max_players = 8

#functions
def gcd(a, b):
    while b:
        a, b = b, a%b
    return a

def lcm(a, b):
    if a == 0 and b == 0:
        return 0
    else:
        return abs(a*b)/gcd(a,b)

#map class
class Grid():
    #sets up a grid with valid parameters for tile symmetry
    def tile_symmetric_grid(self, no_players,
                                  min_dimensions, max_dimensions,
                                  min_starting_distance,
                                  min_block_size, max_block_size):
        self.no_players = no_players
        self.min_dimensions = min_dimensions
        self.max_dimensions = max_dimensions
        self.min_starting_distance = min_starting_distance
        self.min_block_size = min_block_size
        self.max_block_size = max_block_size

        if not self.pick_tile_dimensions():
            return False

        self.squares = [ ['%' for c in range(self.cols)] for r in range(self.rows) ]

        self.add_starting_hills()
        a_block = self.make_block(self.h_loc, self.block_size)
        self.add_block_land(a_block)
        return True

    #sets up a grid with valid parameters for rotational symmetry
    def rotationally_symmetric_grid(self, no_players,
                                          min_dimensions, max_dimensions,
                                          min_starting_distance,
                                          min_block_size, max_block_size,
                                          r_sym_type):
        self.no_players = no_players
        self.min_dimensions = min_dimensions
        self.max_dimensions = max_dimensions
        self.r_sym_type = r_sym_type
        self.min_starting_distance = min_starting_distance
        self.min_block_size = min_block_size
        self.max_block_size = max_block_size

        if not self.pick_rotational_dimensions():
            return False

        self.squares = [ ['%' for c in range(self.cols)] for r in range(self.rows) ]

        self.add_starting_hills()
        a_block = self.make_block(self.h_loc, self.block_size)
        self.add_block_land(a_block)
        return True

    #picks valid dimensions for a tile symmetric grid
    def pick_tile_dimensions(self):
        original_no_players = self.no_players
        for d_attempt in range(200000):
            self.block_size = random.randint(self.min_block_size, self.max_block_size)
            self.rows = random.randint(self.min_dimensions, self.max_dimensions)
            self.cols = random.randint(self.rows, self.max_dimensions)
            self.rows += 2*self.block_size - self.rows%(2*self.block_size)
            self.cols += 2*self.block_size - self.cols%(2*self.block_size)

            self.row_t = random.randint(3, self.rows-3)
            self.col_t = random.randint(3, self.cols-3)

            if original_no_players == -1:
                self.no_players = lcm(self.rows/gcd(self.row_t, self.rows),
                                      self.cols/gcd(self.col_t, self.cols))

            self.h_loc = self.random_loc()

            if self.rows <= self.max_dimensions and \
               self.cols <= self.max_dimensions and \
               self.no_players == lcm(self.rows/gcd(self.row_t, self.rows),
                                  self.cols/gcd(self.col_t, self.cols) ) and \
               self.no_players >= min_players and \
               self.no_players <= max_players and\
               self.rows/gcd(self.row_t, self.rows) == \
                    self.cols/gcd(self.col_t, self.cols) and \
               self.row_t%(2*self.block_size) == 0 and \
               self.col_t%(2*self.block_size) == 0 and \
               self.is_valid_start():
                return True
        return False

    #picks valid dimensions for a rotationally symmetric grid
    def pick_rotational_dimensions(self):
        original_no_players = self.no_players
        original_r_sym_type = self.r_sym_type
        for d_attempt in range(100):
            #picks number of players if it is not given
            if original_no_players == -1:
                if original_r_sym_type > 3:
                    self.no_players = 2
                elif original_r_sym_type > 1:
                    self.no_players = 2**random.randint(1,2)
                else:
                    self.no_players = 2**random.randint(1,3)

            #picks a symmetry type if one is not given
            if original_r_sym_type == -1:
                if self.no_players == 2:
                    self.r_sym_type = random.randint(1, 5)
                elif self.no_players == 4:
                    self.r_sym_type = random.randint(1, 3)
                elif self.no_players == 8:
                    self.r_sym_type = 1;


            self.block_size = random.randint(self.min_block_size, self.max_block_size)
            self.rows = random.randint(self.min_dimensions, self.max_dimensions)
            self.cols = random.randint(self.rows, self.max_dimensions)
            self.rows += 2*self.block_size - self.rows%(2*self.block_size)
            self.cols += 2*self.block_size - self.cols%(2*self.block_size)

            if (self.no_players == 2 and self.r_sym_type > 3) or \
               (self.no_players == 4 and self.r_sym_type > 1) or \
                self.no_players == 8:
                self.cols = self.rows

            visited = [ [False for c in range(self.cols)] for r in range(self.rows)]
            for a_attempt in range(2*self.rows):
                while True:
                    self.h_loc = self.random_loc()
                    if not visited[self.h_loc[0]][self.h_loc[1]]:
                        break

                visited[self.h_loc[0]][self.h_loc[1]] = True

                if self.rows <= self.max_dimensions and \
                   self.cols <= self.max_dimensions and \
                   self.is_valid_start():
                    return True
        return False

    #works out a list of loctations that generates the set of locations under the given symmetry
    def generate_basis_information(self):
        self.basis_locs = []
        self.is_basis_block = [ [False for c in range(self.cols)] for r in range(self.rows)]
        self.is_basis_loc = [ [False for c in range(self.cols)] for r in range(self.rows)]
        visited = [ [False for c in range(self.cols)] for r in range(self.rows)]

        a_block = self.make_block(self.h_loc, self.block_size)

        queue = deque([a_block[0]])

        self.is_basis_block[a_block[0][0]][a_block[0][1]] = True
        for loc in a_block:
            self.is_basis_loc[loc[0]][loc[1]] = True
            self.basis_locs.append(loc)
            s_locs = self.get_symmetric_locs(loc)
            for s_loc in s_locs:
                visited[s_loc[0]][s_loc[1]] = True

        while queue:
            c_loc = queue.popleft()
            c_block = self.make_block(c_loc, self.block_size)

            for d in directions:
                n_block = self.get_adjacent_block(c_block, d)
                n_loc = n_block[0]
                if not visited[n_loc[0]][n_loc[1]]:
                    queue.append(n_loc)

                    self.is_basis_block[n_loc[0]][n_loc[1]] = True
                    for loc in n_block:
                        self.is_basis_loc[loc[0]][loc[1]] = True
                        self.basis_locs.append(loc)
                        s_locs = self.get_symmetric_locs(loc)
                        for s_loc in s_locs:
                            visited[s_loc[0]][s_loc[1]] = True

    #returns a list of directions in random order
    def random_directions(self):
        r_directions = []
        t = random.randint(0, 3)
        for i in range(len(directions)):
            r_directions.append(cdirections[(i+t)%4])
        return r_directions

    #randomly picks a location inside the map
    def random_loc(self):
        return [random.randint(0, self.rows-1), random.randint(0, self.cols-1)]

    #returns the new location after moving in a particular direction
    def get_loc(self, loc, direction):
        dr, dc = directions[direction]
        return [(loc[0]+dr)%self.rows, (loc[1]+dc)%self.cols ]

    #returns the new location after translating it by t_amount = [rt, ct]
    def get_translate_loc(self, loc, t_amount):
        return [(loc[0]+t_amount[0])%self.rows,
                (loc[1]+t_amount[1])%self.cols ]

    #returns a symmetrically equivalent location as specified by num
    def get_symmetric_loc(self, loc, num):
        if num == 1:   #horizontal
            return [loc[0], self.cols - loc[1]-1]
        elif num == 2: #vertical
            return [self.rows - loc[0]-1, loc[1]]
        elif num == 3: #horizontal and vertial
            return [self.rows - loc[0]-1, self.cols - loc[1]-1]
        elif num == 4: #diagonal/transpose
            return [loc[1], loc[0]]
        elif num == 5: # horizontal then vertical then diagonal
            return [self.rows - loc[1]-1, self.cols - loc[0]-1]
        elif num == 6: # horizontal then diagonal
            return [self.rows - loc[1]-1, loc[0]]
        elif num == 7: # vertical then diagonal
            return [loc[1], self.cols-loc[0]-1]

    #returns a list of the symmetric locations for all players
    def get_symmetric_locs(self, loc):
        locs = [loc]

        if self.symmetry == "tile":
            n_loc = loc
            for n in range(self.no_players-1):
                n_loc = self.get_translate_loc(n_loc, [self.row_t, self.col_t])
                locs.append(n_loc)
        elif self.symmetry == "rotational":
            if self.no_players == 2:
                locs.append(self.get_symmetric_loc(loc, self.r_sym_type))
            elif self.no_players == 4:
                if self.r_sym_type == 1:
                    locs.append(self.get_symmetric_loc(loc, 1))
                    locs.append(self.get_symmetric_loc(loc, 2))
                    locs.append(self.get_symmetric_loc(loc, 3))
                elif self.r_sym_type == 2:
                    locs.append(self.get_symmetric_loc(loc, 3))
                    locs.append(self.get_symmetric_loc(loc, 4))
                    locs.append(self.get_symmetric_loc(loc, 5))
                elif self.r_sym_type == 3:
                    locs.append(self.get_symmetric_loc(loc, 3))
                    locs.append(self.get_symmetric_loc(loc, 6))
                    locs.append(self.get_symmetric_loc(loc, 7))
            elif self.no_players == 8:
                for n in range(self.no_players-1):
                    locs.append(self.get_symmetric_loc(loc, n+1))
        return locs

    #makes a block inside the map
    def make_block(self, loc, block_size):
        block = []

        for row_t in range(block_size):
            for col_t in range(block_size):
                block.append(self.get_translate_loc(loc, [row_t, col_t]))
        return block

    #returns the new block after moving in a particular direction
    def get_block(self, block, direction):
        n_block = []
        for loc in block:
            n_block.append(self.get_loc(loc, direction))
        return n_block

    #returns the adjacent block in a given direction
    def get_adjacent_block(self, block, direction):
        for n in range(int(math.sqrt(len(block)))):
            block = self.get_block(block, direction)
        return block


    #returns the euclidean distance (squared) between two squares
    def dist(self, loc1, loc2):
        d1 = abs(loc1[0] - loc2[0])
        d2 = abs(loc1[1] - loc2[1])
        dr = min(d1, self.rows - d1)
        dc = min(d2, self.cols - d2)
        return dr*dr + dc*dc

    #checks whether the players start far enough apart
    def is_valid_start(self):
        h_locs = self.get_symmetric_locs(self.h_loc)
        for n in range(self.no_players-1):
            if self.dist(h_locs[0], h_locs[n+1]) < self.min_starting_distance:
                return False
        return True

    #checks whether the hills start far enough apart
    def is_valid_hill_loc(self, h_loc):
        if self.squares[h_loc[0]][h_loc[1]] != '.':
            return False

        h_locs = self.get_symmetric_locs(h_loc)
        for n in range(len(h_locs)-1):
            if self.dist(h_locs[0], h_locs[n+1]) < self.min_starting_distance:
                return False

        for c_loc in self.h_locs:
            if self.dist(c_loc, h_loc) < self.min_starting_distance:
                return False
        return True

    #adds land information to the grid
    def add_land(self, loc):
        if self.squares[loc[0]][loc[1]] == '%':
            self.squares[loc[0]][loc[1]] = '.'

    #add land information for a block
    def add_block_land(self, block):
        for loc in block:
            self.add_land(loc)

    #adds ants to the map
    def add_starting_hills(self):
        h_locs = self.get_symmetric_locs(self.h_loc)
        player = '0'
        for n in range(self.no_players):
            self.squares[h_locs[n][0]][h_locs[n][1]] = player
            player = chr(ord(player)+1)

    #adds extra hills to the map
    def add_extra_hills(self):
        self.h_locs = self.get_symmetric_locs(self.h_loc)

        for h in range(self.no_hills-1):
            for d_attempt in range(100):
                h_loc = self.random_loc()
                if self.is_valid_hill_loc(h_loc):
                    break

            if not self.is_valid_hill_loc(h_loc):
                return

            player = '0'
            h_locs = self.get_symmetric_locs(h_loc)
            for n in range(self.no_players):
                self.squares[h_locs[n][0]][h_locs[n][1]] = player
                self.h_locs.append(h_locs[n])
                player = chr(ord(player)+1)

    #outputs the grid in the expected format
    def print_grid(self):
        print "rows", self.rows
        print "cols", self.cols
        print "players", self.no_players
        #self.print_food_spawn_info()
        for row in self.squares:
            print 'm', ''.join(row)

    #adds land to a water map using backtracking "recursively"
    def add_land_with_recursive_backtracking(self):
        stack = []
        c_loc = self.h_loc
        c_block = self.make_block(c_loc, self.block_size)
        visited = [ [False for c in range(self.cols)] for r in range(self.rows)]

        while True:
            visited[c_loc[0]][c_loc[1]] = True
            neighbour_found = False

            r_directions = self.random_directions()
            for d in r_directions:
                n_block = self.get_adjacent_block(c_block, d)
                n_loc = n_block[0]

                if not self.is_basis_block[n_loc[0]][n_loc[1]]: #can't carve here
                    continue

                t_block = self.get_adjacent_block(n_block, d)
                t_loc = t_block[0]
                f_loc = t_block[0]
                f_block = t_block

                if not self.is_basis_block[t_loc[0]][t_loc[1]]:
                    f_loc = c_loc
                    f_block = self.make_block(c_loc, self.block_size)

                if not visited[t_loc[0]][t_loc[1]]:
                    if self.is_basis_block[t_loc[0]][t_loc[1]]:
                        stack.append(c_loc)
                        self.add_block_land(n_block)
                        self.add_block_land(f_block)
                    elif random.randint(1,3) == 1:
                        self.add_block_land(n_block)

                    c_loc = f_loc
                    c_block = self.make_block(c_loc, self.block_size)
                    neighbour_found = True
                    visited[t_loc[0]][t_loc[1]] = True
                    break

            if not neighbour_found:
                if stack:
                    c_loc = stack.pop()
                    c_block = self.make_block(c_loc, self.block_size)
                else:
                    break

    #adds extra land blocks to the map
    def add_extra_land_blocks(self):
        extra_locs = random.randint(2, 12)
        for extra_loc in range(extra_locs):
            block_found = False
            for b_attempt in range(100):
                c_block = self.make_block(self.h_loc, self.block_size)

                r_directions = self.random_directions()
                for d in r_directions:
                    n_block = self.get_adjacent_block(c_block, d)
                    if self.is_basis_block[n_block[0][0]][n_block[0][1]]:
                        c_block = n_block
                        break

                for i in range(15):
                    r_directions = self.random_directions()
                    for d in r_directions:
                        n_block = c_block
                        n_block = self.get_adjacent_block(n_block, d)
                        n_block = self.get_adjacent_block(n_block, d)
                        if self.is_basis_block[n_block[0][0]][n_block[0][1]]:
                            c_block = n_block
                            break

                if self.squares[c_block[0][0]][c_block[0][1]] == '%':
                    for d in directions:
                        n_block = self.get_adjacent_block(c_block, d)
                        if self.is_basis_block[n_block[0][0]][n_block[0][1]] and\
                           self.squares[n_block[0][0]][n_block[0][1]] == '.':
                            block_found = True
                            break
                    if block_found:
                        break

            if not block_found:
                return
            for loc in c_block:
                if self.is_basis_loc[loc[0]][loc[1]]:
                    self.add_land(loc)

    #adds extra land locations to the map
    def add_extra_land_locs(self):
        visited = [ [False for c in range(self.cols)] for r in range(self.rows)]
        w_locs = []

        stack = [self.h_loc]
        visited[self.h_loc[0]][self.h_loc[1]] = True

        while stack:
            c_loc = stack.pop()
            for d in directions:
                n_loc = self.get_loc(c_loc, d)

                if not visited[n_loc[0]][n_loc[1]]:
                    if self.is_basis_loc[n_loc[0]][n_loc[1]] and \
                       self.squares[n_loc[0]][n_loc[1]] == '%':
                            w_locs.append(n_loc)
                    elif self.squares[n_loc[0]][n_loc[1]] == '.':
                        stack.append(n_loc)

                    visited[n_loc[0]][n_loc[1]] = True

        locs_to_add = int(0.5*len(w_locs))
        for w in range(locs_to_add):
            r_square = random.randint(0, len(w_locs)-1)
            self.add_land(w_locs[r_square])
            w_locs.remove(w_locs[r_square])
            if len(w_locs) == 0:
                break

    #makes the map symmetric
    def make_symmetric(self):
        for loc in self.basis_locs:
            if self.squares[loc[0]][loc[1]] == '.':
                s_locs = self.get_symmetric_locs(loc)
                for s_loc in s_locs:
                    self.add_land(s_loc)

    #randomly translates the map
    def translate(self):
        old_map = [ ['%' for c in range(self.cols)] for r in range(self.rows) ]
        for r in range(self.rows):
            for c in range(self.cols):
                old_map[r][c] = self.squares[r][c]

        t_loc = [random.randint(1, self.rows-2), random.randint(1, self.cols-2)]

        self.h_loc = self.get_translate_loc(self.h_loc, t_loc)

        for r in range(self.rows):
            for c in range(self.cols):
                o_loc = self.get_translate_loc([r,c], t_loc)
                self.squares[r][c] = old_map[o_loc[0]][o_loc[1]]

def main(argv):
    usage ="""Usage: %prog [options]\n"""
    parser = OptionParser(usage=usage)
    parser.add_option("--no_players", dest="no_players",
                      type="int", default=-1,
                      help="Minimum number of players to be used")

    parser.add_option("--min_hills", dest="min_hills",
                      type="int", default=1,
                      help="Minimum number of hills for each player")

    parser.add_option("--max_hills", dest="max_hills",
                      type="int", default=9,
                      help="Maximum number of hills for each player")

    parser.add_option("--min_dimensions", dest="min_dimensions",
                      type="int", default=60,
                      help="Minimum number of rows/cols to be used")
    parser.add_option("--max_dimensions", dest="max_dimensions",
                      type="int", default=150,
                      help="Maximum number of rows/cols to be used")

    parser.add_option("--min_starting_distance", dest="min_starting_distance",
                      type="int", default=10**2,
                      help="Minimum starting distance between ants")

    parser.add_option("--symmetry", dest="symmetry",
                      type="string", default="",
                      help="Type of symmetry to be used")
    parser.add_option("--rotational_symmetry", dest="rotational_symmetry",
                      type="int", default=-1,
                      help="Number of players to be used")

    parser.add_option("--min_block_size", dest="min_block_size",
                      type="int", default=3,
                      help="Minimum block size to be used")
    parser.add_option("--max_block_size", dest="max_block_size",
                      type="int", default=4,
                      help="Maximum block size to be used")
    parser.add_option("--seed", dest="seed",
                      type="int", default=None,
                      help="Seed to initialize the random number generator.")

    (opts,_) = parser.parse_args(argv)

    #makes sure the parameters are valid
    if (opts.no_players < min_players and opts.no_players != -1)\
            or opts.no_players > max_players:
        print "Invalid number of players"
        return
    if opts.min_hills < 1 or opts.max_hills < opts.min_hills:
        print "Invalid min/max number of hills per player"
        return
    if opts.min_dimensions < 1 or opts.max_dimensions < opts.min_dimensions:
        print "Invalid min/max dimensions parameters"
        return
    if opts.min_block_size < 1 or opts.max_block_size < opts.min_block_size:
        print "Invalid min/max block size parameters"
        return
    if opts.symmetry == "rotational":
        if opts.no_players != -1 and opts.no_players != 2 and\
           opts.no_players != 4 and opts.no_players != 8:
            print "Invalid number of players for a rotationally symmetric map"
            return
        if opts.rotational_symmetry != -1:
            if (opts.no_players == 2 and (opts.rotational_symmetry < 1 or \
                                          opts.rotational_symmetry > 5))  \
                or (opts.no_players == 4 and (opts.rotational_symmetry < 1 or \
                                              opts.rotational_symmetry > 3))  \
                or (opts.no_players == 8 and opts.rotational_symmetry != 1)   \
                or (opts.rotational_symmetry < 0 or opts.rotational_symmetry > 5):
                print "Invalid rotational symmetry type for the number of players"
                return
    
    random.seed(opts.seed)

    #creates the map
    grid = Grid()

    #works out how many hills to have
    grid.no_hills = random.randint(opts.min_hills, opts.max_hills)

    #works out the type of symmetry
    if opts.symmetry == "rotational":
        grid.symmetry = "rotational"
    elif opts.symmetry == "tile":
        grid.symmetry = "tile"
    elif opts.symmetry:
        print "invalid symmetry type"
        return
    else:
        if (opts.no_players == -1 or opts.no_players%2 == 0) \
                and random.randint(0,5):
            grid.symmetry = "rotational"
        else:
            grid.symmetry = "tile"

    #constructs a water filled grid
    if grid.symmetry == "rotational":
        if not grid.rotationally_symmetric_grid(opts.no_players,
                                         opts.min_dimensions, opts.max_dimensions,
                                         opts.min_starting_distance,
                                         opts.min_block_size, opts.max_block_size,
                                         opts.rotational_symmetry):
            print "Failed to create a valid rotationally symmetric grid with", \
                         opts.no_players, "players"
            return

    elif grid.symmetry == "tile":
        if not grid.tile_symmetric_grid(opts.no_players,
                                        opts.min_dimensions, opts.max_dimensions,
                                        opts.min_starting_distance,
                                        opts.min_block_size, opts.max_block_size):
            print "Failed to create a valid tile symmetric grid with", \
                         opts.no_players, "players and block size", grid.block_size
            return

    grid.generate_basis_information()
    grid.add_land_with_recursive_backtracking()
    grid.add_extra_land_blocks()
    grid.add_extra_land_locs()
    grid.make_symmetric()
    grid.add_extra_hills()
    grid.translate() #this will make it (even) harder to determine some symmetries

    grid.print_grid()

if __name__ == '__main__':
    main(sys.argv[1:])


########NEW FILE########
__FILENAME__ = McMaps
#!/usr/bin/python
import sys
from random import randrange, random, choice, seed
from math import sqrt
import Image, ImageDraw, ImageChops
from itertools import combinations
from collections import defaultdict

MY_ANT = 0
ANTS = 0
DEAD = -1
LAND = -2
FOOD = -3
BARRIER = -4
UNSEEN = -5

BARRIER_COLOR = (128, 128, 128)
LAND_COLOR = (139, 69, 19)
FOOD_COLOR = (255, 255, 255)

COLOR = {LAND: LAND_COLOR,
         BARRIER: BARRIER_COLOR,
         UNSEEN: LAND_COLOR}
for i in range(26):
    COLOR[i] = FOOD_COLOR

class Node:
    def all(self):
        yield self.location
        if self.left_child != None:
            for location in self.left_child.all():
                yield location
        if self.right_child != None:
            for location in self.right_child.all():
                yield location
 
def kdtree(point_list, depth=0):
    if not point_list:
        return
 
    # Select axis based on depth so that axis cycles through all valid values
    k = len(point_list[0]) # assumes all points have the same dimension
    axis = depth % k
    def key_func(point):
        return point[axis]
 
    # Sort point list and choose median as pivot element
    point_list.sort(key=key_func)
    median = len(point_list) // 2 # choose median
 
    # Create node and construct subtrees
    node = Node()
    node.location = [point_list[median], depth]
    node.left_child = kdtree(point_list[:median], depth + 1)
    node.right_child = kdtree(point_list[median + 1:], depth + 1)
    return node

def draw_line(image, point, neighbor, size):
    width, height = size
    center_point = (width//2, height//2)
    offset = (width//2 - point[0], height//2 - point[1])
    image = ImageChops.offset(image, offset[0], offset[1])
    draw = ImageDraw.Draw(image)
    to_point = ((neighbor[0] + offset[0]) % width, (neighbor[1] + offset[1]) % height)
    draw.line((center_point, to_point))
    return ImageChops.offset(image, -offset[0], -offset[1])

class Point:
    def __init__(self, x, y):
        self.x = x
        self.y = y
    def sort_key(self):
        return (self.x, self.y)

class Triangle:
    def __init__(self, points):
        self.p1 = points[0]
        self.p2 = points[1]
        if len(points) > 2:
            self.p3 = points[2]
        else:
            self.p3 = None
    def center(self):
        if self._center == None:
            x1, y1 = self.p1.x, self.p1.y
            x2, y2 = self.p2.x, self.p2.y
            if self.p3 == None:
                # return midpoint of segment
                self._center = (x1+x2)/2, (y1+y2)/2
            else:
                x3, y3 = self.p3.x, self.p3.y
                # check for coincident lines
                # check for infinite slope
                (x1, y1), (x2, y2), (x3, y3) = self.p1, self.p2, self.p3
                ma = (y2-y1)/(x2-x1)
                mb = (y3-y2)/(x3-x2)
                if ma != mb:                    
                    x = (ma*mb*(y1-y3) +
                         mb*(x1+x2) -
                         ma*(x2+x3))/(2*(mb-ma))
                    y = -1/ma*(x-(x1+x2)/2) + (y1+y2)/2
                    self._center = (x, y)
        return self._center

def divide_conquer():
    class Delaunay:
        pass
    
    def form(points):
        if len(points) > 3:
            mid = len(points)//2
            left = form(points[:mid])
            right = form(points[mid:])
            return merge(left, right)
        else:
            t = Triangle(points)
            return
    def merge(left, right):
        pass
    
    width = 100.0
    height = 100.0
    
    points = [Point(random()*width, random()*height) for i in range(10)]
    points.sort()    
    
    # draw image
    size = (int(width), int(height))
    image = Image.new('RGB', size, (128,128,128))
    draw = ImageDraw.Draw(image)
    for point in points:
        r = 1.0
        draw.ellipse((point[0]-r, point[1]-r, point[0]+r, point[1]+r), (255, 0, 0))
    image.save('delaunay.png')

def delaunay():
    class Triangle:
        def __init__(self, points):
            self._center = None
            self.points = points
        def center(self):
            if self._center == None:
                (x1, y1), (x2, y2), (x3, y3) = self.points
                ma = (y2-y1)/(x2-x1)
                mb = (y3-y2)/(x3-x2)
                if ma != mb:                    
                    x = (ma*mb*(y1-y3) +
                         mb*(x1+x2) -
                         ma*(x2+x3))/(2*(mb-ma))
                    y = -1/ma*(x-(x1+x2)/2) + (y1+y2)/2
                    self._center = (x, y)
                # check for coincident lines
                # check for 
            return self._center
    # setup
    width = 100.0
    height = 100.0
    # create point at 0,0, create 2 triangles in square
    points = [(0.0,0.0)]
    triangles = []
    triangles.append(Triangle([(0.0,0.0),(0.0, height), (width, 0.0)]))
    triangles.append(Triangle([(0.0, height), (width, 0.0), (width, height)]))
    
    # add point, remove inside triangles, create new ones
    point = (random()*width, random()*height)
    
    
    # draw triangles
    size = (int(width), int(height))
    image = Image.new('RGB', size, BARRIER_COLOR)
    draw = ImageDraw.Draw(image)
    draw.rectangle((0,0,width,height), outline=(32,32,32))
    for triangle in triangles:
        points = [(int(x), int(y)) for x, y in triangle.points]
        for i in range(len(triangle.points)):
            image = draw_line(image, points[i-1], points[i], size)
    image.save('delaunay.png')


def distance(x1, y1, x2, y2, width, height):
    x1 = x1 % width
    x2 = x2 % width
    y1 = y1 % height
    y2 = y2 % height
    d_x = min(abs(x1 - x2), width - abs(x1 - x2))
    d_y = min(abs(y1 - y2), height - abs(y1 - y2))
    return d_x**2 + d_y**2

def voronoi(players=4):
    width = randrange(64, 256)
    height = randrange(64, 256)
    point_count = randrange(players*3, players*6)
    min_dist = width * height / point_count
    print('%s, %s  %s %s' % (width, height, min_dist, sqrt(min_dist)))
    px, py = 0, 0
    points = []
    while min_dist > 100 and len(points) < point_count:
        while min_dist > 100:
            px, py = randrange(width), randrange(height)
            for nx, ny in points:
                if distance(px, py, nx, ny, width, height) < min_dist:
                    break
            else:
                break
            min_dist -= 1
        points.append((px, py))
    #for px, py in points:
    #    for nx, ny in points:
    #        print('(%s)-(%s) = %s' % ((px,py),(nx,ny),distance(px, py, nx, ny, width, height)))
    path = {}
    closest = {}
    for p_x, p_y in points:
        nearest = {}
        for n_x, n_y in points:
            if (p_x, p_y) != (n_x, n_y):
                dist = distance(p_x, p_y, n_x, n_y, width, height)
                nearest[dist] = (n_x, n_y)
        sorted = nearest.keys()
        sorted.sort()
        path[(p_x, p_y)] = [nearest[key] for key in sorted[:3]]
        closest[(p_x, p_y)] = sorted[0]
    image = Image.new('RGB', (width, height), BARRIER_COLOR)
    draw = ImageDraw.Draw(image)
    for point in points:
        image.putpixel(point, (0,0,0))
        size = int(sqrt(closest[point]))//2 - 2
        draw.ellipse((point[0]-size, point[1]-size, point[0]+size, point[1]+size),
                fill=LAND_COLOR, outline=LAND_COLOR)
    from_point = (width//2, height//2)
    for point, path_neighbors in path.items():
        offset = (width//2 - point[0], height//2 - point[1])
        image = ImageChops.offset(image, offset[0], offset[1])
        draw = ImageDraw.Draw(image)
        for neighbor in path_neighbors:
            to_point = ((neighbor[0] + offset[0]) % width, (neighbor[1] + offset[1]) % height)
            draw.line((from_point, to_point), width=randrange(3,6), fill=LAND_COLOR)
        image = ImageChops.offset(image, -offset[0], -offset[1])
    image = image.resize((width*4, height*4))
    image.save('voronoi.png')
    
def random_box():
    players = 4
    width = randrange(16, 64) * 2
    height = randrange(16, 64) * 2
    m = [[BARRIER for x in range(width)] for y in range(height)]
    def carve(row, col):
        if m[row][col] == BARRIER:
            m[row][col] = LAND
    for box in range(randrange(7,14)):
        l = randrange(width-5)
        t = randrange(height-5)
        r = randrange(l+2, min(l+width//4,width))
        b = randrange(t+2, min(t+height//4,height))
        for y in range(t, b+1):
            for x in range(l, r+1):
                carve(y, x)
        for y in range(height-b-1, height-t):
            for x in range(l, r+1):
                carve(y, x)
        for y in range(t, b+1):
            for x in range(width-r-1, width-l):
                carve(y, x)
        for y in range(height-b-1, height-t):
            for x in range(width-r-1, width-l):
                carve(y, x)
        if box == 0:
            m[t][l] = 1
            m[height-t-1][l] = 2
            m[t][width-l-1] = 3
            m[height-t-1][width-l-1] = 4
            for y in range(t+1, height-t-1):
                carve(y, l)
                carve(y, width-l-1)
            for x in range(l+1, width-l-1):
                carve(t, x)
                carve(height-t-1, x)
    return ant_map(m)

def mid_point(loc1, loc2, size):
    if loc1 == (31,24) and loc2 == (3,25):
        pass
    row1, col1 = loc1
    row2, col2 = loc2
    rows, cols = size
    row1, row2 = sorted((row1, row2))
    col1, col2 = sorted((col1, col2))
    m_row = (row1 + row2)//2
    if row2 - row1 > rows//2:
        m_row = (m_row + rows//2) % rows
    m_col = (col1 + col2)//2
    if col2 - col1 > cols//2:
        m_col = (m_col + cols//2) % cols
    return m_row, m_col

def row_distance(row1, row2, rows):
    return min(abs(row1-row2),rows-abs(row1-row2))

def col_distance(col1, col2, cols):
    return min(abs(col1-col2),cols-abs(col1-col2))

def manhatten_distance(loc1, loc2, size):
    row1, col1 = loc1
    row2, col2 = loc2
    rows, cols = size
    d_row = min(abs(row1-row2),rows-abs(row1-row2))
    d_col = min(abs(col1-col2),cols-abs(col1-col2))
    return d_row + d_col

def chebychev_distance(loc1, loc2, size):
    row1, col1 = loc1
    row2, col2 = loc2
    rows, cols = size
    d_row = min(abs(row1-row2),rows-abs(row1-row2))
    d_col = min(abs(col1-col2),cols-abs(col1-col2))
    return max(d_row, d_col)

euclidean_cache = {}
def euclidean_distance(loc1, loc2, size):
    row1, col1 = loc1
    row2, col2 = loc2
    rows, cols = size
    d_row = min(abs(row1-row2),rows-abs(row1-row2))
    d_col = min(abs(col1-col2),cols-abs(col1-col2))
    key = (d_row, d_col)
    if key in euclidean_cache:
        return euclidean_cache[key]
    value = sqrt(d_row**2 + d_col**2)
    euclidean_cache[key] = value
    return value

def copy(value, size):
    return size+value
def mirror(value, size):
    return size*2-value-1
def flip(value, size):
    return size-value-1

def both_point(point, size, funcs):
    return (funcs[0](point[0], size[0]), funcs[1](point[1], size[1]))
def vert_point(point, size, funcs):
    return (funcs[0](point[0], size[0]), point[1])
def horz_point(point, size, funcs):
    return (point[0], funcs[0](point[1], size[1]))
# TODO: ensure square or change output size
def flip_point(point, size, funcs):
    return (funcs[0](point[1], size[1]), funcs[1](point[0], size[0]))

def vert_increase(size, count):
    return (size[0]*count, size[1])
def horz_increase(size, count):
    return (size[0], size[1]*count)

vert_copy = (vert_point, (copy,), vert_increase)
vert_mirror = (vert_point, (mirror,), vert_increase)
vert_rotate = (both_point, (mirror, flip), vert_increase)
horz_copy = (horz_point, (copy,), horz_increase)
horz_mirror = (horz_point, (mirror,), horz_increase)
horz_rotate = (both_point, (flip, mirror), horz_increase)    

def extend(funcs, points, size, count=2):
    if type(points) == list:
        points = {point: x for x, point in enumerate(points)}
    rows, cols = size
    new_points = {}
    for point, id in points.items():
        new_points[point] = id
        for c in range(1,count):
            new_points[funcs[0](point, funcs[2](size, c), funcs[1])] = id
    return new_points, funcs[2](size, count)
               
def make_symmetric(points, size, players):
    # TODO: shearing, like antimatroid
    #    3, 4 and 7 player can be made fair
    # TODO: rotational
    #    2, 4 and 8 can be made fairish
    
    # pick random grid size
    divs = [i for i in range(1,players+1) if players%i==0]
    row_sym = choice(divs)
    col_sym = players/row_sym
    grid = (row_sym, col_sym)
    
    newsize = (size[0]*row_sym, size[1]*col_sym)
    newpoints = []
    comps = []

    if row_sym % 2 == 0:
        points, size = extend(choice((vert_copy, vert_mirror, vert_rotate)), points, size)
        row_sym /= 2
    if row_sym > 1:
        points, size = extend(vert_copy, points, size, row_sym)

    if col_sym % 2 == 0:
        points, size = extend(choice((horz_copy, horz_mirror, horz_rotate)), points, size)
        col_sym /= 2
    if col_sym > 1:
        points, size = extend(horz_copy, points, size, col_sym)
    
    return points, size, grid

def random_points(count, size, spacing, distance):
    rows, cols = size
    points = []
    failures = 0
    for c in range(count):
        while True:
            point = (randrange(rows), randrange(cols))
            for other_point in points:
                if distance(point, other_point, size) < spacing:
                    failures += 1
                    if failures > 100000:
                        return points
                    break
            else:
                break
        points.append(point)
    return points

def random_points_unique(count, size, spacing, distance):
    rows, cols = size
    avail_rows = list(range(rows))
    avail_cols = list(range(cols))
    points = []
    failures = 0
    for c in range(count):
        while True:
            point = (choice(avail_rows), choice(avail_cols))
            for other_point in points:
                if distance(point, other_point, size) < spacing:
                    failures += 1
                    if failures > 100000:
                        return points
                    break
            else:
                break
        points.append(point)
        avail_rows.remove(point[0])
        if len(avail_rows) == 0:
            avail_rows = list(range(rows))
        avail_cols.remove(point[1])
        if len(avail_cols) == 0:
            avail_cols = list(range(cols))
    return points

def cells(size, points, min_gap=5, max_braids=1000, openness=0.25, distance=euclidean_distance):
    rows, cols = size
    size = (rows, cols)
    m = [[LAND for col in range(cols)] for row in range(rows)]
    
    # ensure points is a dict with id's
    if type(points) == dict:
        points = {point: x for x, point in enumerate(points)}
        
    # undirected node graph
    neighbor = defaultdict(list) 
    # list of barriers to remove when carving a passage between nodes
    barrier = defaultdict(list)
    
    for row in range(rows):
        for col in range(cols):
            # TODO: improve speed with nearest neighbor queries
            distances = {loc: distance((row,col), loc, size) for loc in points.keys()}
            cutoff = min(distances.values()) + 1
            closest = [point for point, d in distances.items() if d <= cutoff]
            comps = set([points[point] for point in closest])
            
            # find if there are unique complement sets that are closest
            # if not, this is probably a mirrored edge and the points should be
            # considered one cell
            #if closest[0] + 1 >= closest[1]:
            if len(closest) > 1:
                if comps_found:
                    m[row][col] = BARRIER
                    # find all starting points that contributed to the barrier,
                    # mark them as neighbors, add to barrier dict
                    if len(nearest) == 2:
                        neighbor[nearest[0]].append(nearest[1])
                        neighbor[nearest[1]].append(nearest[0])
                        # note: a path from one point to another could have 2 barrier sections if they touch
                        #       left and right or top and bottom due to wrapping
                        #       the path midpoint attempts to choose one and only one barrier section
                        m_row, m_col = mid_point(points[nearest[0]], points[nearest[1]], size)
                        if (row_distance(m_row, row, rows) <= rows//4 and
                                col_distance(m_col, col, cols) <= cols//4):
                            barrier[tuple(nearest)].append((row, col))
                    else:
                        pass
                        # barrier[tuple(nearest)].append((row, col))
                else:
                    # todo: similar logic to wrap around fix, but for
                    #       complementary points
                    pass
            else:
                # note: a cell could wrap around vertically or horizontally
                #       depending on the placement of other cells
                #       this draws a barrier halfway around on the other side
                nearest = distances.index(min(distances))
                if (row_distance(row, points[nearest][0], rows) >= rows//2 or
                    col_distance(col, points[nearest][1], cols) >= cols//2):
                    m[row][col] = BARRIER # this barrier can't be carved
                #m[row][col] = distances.index(closest[0])
    
    # add starting positions
    #for i, (row, col) in enumerate(points):
    #    m[row][col] = i
    
    # remove small gaps
    for path in barrier.keys():
        if len(path) == 2:
            if len(barrier[path]) < min_gap:
                neighbor[path[0]].remove(path[1])
                neighbor[path[1]].remove(path[0])
                
    # carve passages function to pass to maze function
    def carve(path):
        #print('%s-%s (%s,%s)-(%s,%s) %s,%s' % (chr(path[0]+97), chr(path[1]+97),
        #                                       points[path[0]][0], points[path[0]][1],
        #                                       points[path[1]][0], points[path[1]][1],
        #                                       m_row, m_col))
        paths = [path]
        if comps != None:
            paths = zip(comps[path[0]],comps[path[1]])
        for path in paths:
            path = tuple(sorted(path))
            for row, col in barrier[path]:
                m[row][col] = LAND
                
            
    carved = growing_tree(neighbor, carve, max_braids=max_braids, openness=openness)
    #for c1, cs in carved.items():
    #    for c2 in cs:
    #        print "%s-%s " % (chr(c1+97),chr(c2+97)),
    #print
    #for n in sorted(barrier.keys()):
    #    if len(n) == 2:
    #        print("%s : %s" % ('-'.join([chr(x+97) for x in n]),
    #                           ' '.join([','.join([str(s2) for s2 in s])
    #                                     for s in barrier[n]])))
    return m

def growing_tree(nodes, carve, max_braids=1000, openness=0.5):
    cells = [choice(nodes.keys())]
    visited = cells[:]
    carved = defaultdict(list) # modified node graph
    #carved[cells[0]].append(cells[0])
    new = True # track real dead ends, not backtracked forks
    while len(cells) > 0:
        # tune this for different generation methods
        # recursive backtracker
        #index = -1                     
        # Prim's algorithm
        index = randrange(len(cells)) 
        
        cell = cells[index]
        unvisited = [node for node in nodes[cell] if not node in visited]
        if len(unvisited) > 0:
            next = choice(unvisited)
            carve((cell, next))
            carved[next].append(cell)
            carved[cell].append(next)
            visited.append(next)
            cells.append(next)
            new = True
        else:
            if max_braids > 0 and (new or bool(random() < openness)):
                # tune this for different braiding methods
                # random
                #braid = choice([n for n in nodes[cell] if not n in carved[cell]])
                # longest loop
                braid = ([c for c in cells if c in nodes[cell]]+nodes[cell])[0]
                
                carve((cell, braid))
                carved[cell].append(braid)
                max_braids -= 1
            cells.pop(index)
            new = False
    return carved

def cell_maze():
    # these control how much barrier carving will happen
    max_braids = 100 # points where the maze can create a loop
    openness = 0.01  # chance that non dead ends can create a loop
    
    size = (100,100)
    point_count = 100
    spacing= 5
    points = random_points(point_count, size, spacing, euclidean_distance)
    
def ant_map(m):
    tmp = 'rows %s\ncols %s\n' % (len(m), len(m[0]))
    players = {}
    for row in m:
        tmp += 'm '
        for col in row:
            if col == LAND:
                tmp += '.'
            elif col == BARRIER:
                tmp += '%'
            elif col == FOOD:
                tmp += '*'
            elif col == UNSEEN:
                tmp += '?'
            else:
                players[col] = True
                tmp += chr(col + 97)
        tmp += '\n'
    tmp = ('players %s\n' % len(players)) + tmp
    return tmp

def file_to_map(filename):
    f = open(filename, 'r')
    m = []
    for line in f:
        if line.startswith('rows '):
            rows = int(line[5:])
        elif line.startswith('cols '):
            cols = int(line[5:])
        elif line.startswith('M '):
            data = line[2:-1]
            m.append([])
            for c in data:
                if c == '%':
                    m[-1].append(BARRIER)
                elif c == '.':
                    m[-1].append(LAND)
                elif c >= 'a' and c <= 'z':
                    m[-1].append(LAND)
                else:
                    print('found "%s"' % c)
    f.close()
    return m

def map_to_png(m, output_filename):
    rows = len(m)
    cols = len(m[0])
    image = Image.new('RGB', (cols*2, rows*2), FOOD_COLOR)
    for row, row_data in enumerate(m):
        for col, c in enumerate(row_data):
            #image.putpixel((col, row), COLOR[c])
            #image.putpixel((col+cols, row), COLOR[c])
            #image.putpixel((col, row+rows), COLOR[c])
            #image.putpixel((col+cols, row+rows), COLOR[c])

            image.putpixel((col, row), COLOR[c])
            image.putpixel((cols*2-col-1, row), COLOR[c])
            image.putpixel((col, rows*2-row-1), COLOR[c])
            image.putpixel((cols*2-col-1, rows*2-row-1), COLOR[c])
    image.save(output_filename)

def main():
    #map_to_png(sys.argv[1])
    #seed(0)
    size = (100, 100)
    points = random_points_unique(400, size, 6, euclidean_distance)
    m = cells(size, points, max_braids=choice((0,1000)), openness=random())
    #print(ant_map(m))
    #map_to_png(m, "test.png")

def make_text(points, size):
    tmp = ''
    rows, cols = size
    if cols > rows:
        for row in range(rows):
            for col in range(cols):
                if (row,col) in points:
                    tmp += chr(points[(row,col)]+97)
                else:
                    tmp += '.'
            tmp += '\n'
    else:
        for col in range(cols):
            for row in range(rows):
                if (row,col) in points:
                    tmp += chr(points[(row,col)]+97)
                else:
                    tmp += '.'
            tmp += '\n'
    return tmp

if __name__ == '__main__':
    p = [(0,0),(0,1)]
    s = (2,2)
    p, s, g = make_symmetric(p, s, randrange(2,12))
    t = make_text(p, s)
    print("size: %s\ngrid: %s\n\n%s" % (s, g, t))
    
    #import cProfile
    #cProfile.run('main()')
    
    
########NEW FILE########
__FILENAME__ = random_map
#!/usr/bin/env python
from map import *
from random import choice, randint, randrange, shuffle, seed

class RandomMap(Map):
    def __init__(self, options={}):
        self.name = 'random'
        self.rows = options.get('rows', (40,120))
        self.cols = options.get('cols', (40,120))
        self.players = options.get('players', (2,26))
        self.land = options.get('land', (80, 95))

    def generate(self):
        rows = self.get_random_option(self.rows)
        cols = self.get_random_option(self.cols)
        players = self.get_random_option(self.players)
        land = self.get_random_option(self.land)

        # initialize map
        self.map = [[LAND]*cols for _ in range(rows)]

        # place water
        water = rows*cols*(100-land)//100
        row = 0
        col = 0
        for _ in range(water):
            while self.map[row][col] == WATER:
                row = randint(0, rows-1)
                col = randint(0, cols-1)
            self.map[row][col] = WATER

        # place player starts
        for player in range(players):
            while self.map[row][col] != LAND:
                row = randint(0, rows-1)
                col = randint(0, cols-1)
            self.map[row][col] = player

def main():
    new_map = RandomMap()
    new_map.generate()
    new_map.toText()

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = symmetric_mapgen
#!/usr/bin/env python

import math
import random
import sys

#functions
def gcd(a, b):
    while b:
        a, b = b, a%b
    return a

def lcm(a, b):
    if a == 0 and b == 0:
        return 0
    else:
        return abs(a*b)/gcd(a,b)

#map class
class SymmetricMap():
    cdirections = ['N', 'E', 'S', 'W']
    directions = {'N': (-1,0), 'S': (1,0), 'E': (0,1), 'W': (0,-1)}

    #game parameters
    min_players = 2
    max_players = 10
    per_player_dim = (10, 50)
    dim_bounds = (50, 150)
    min_start_distance = 30

    min_land_proportion = 0.60
    max_land_proportion = 0.98

    no_extra_walks = 30

    #map parameters
    no_players = 0
    rows = cols = 0
    row_t = col_t = 0
    water_squares = 0
    land_squares = 0
    map_data = []
    times_visited = []
    a_loc = c_locs = []


    #makes a map by performing a bunch of random walks carving out water
    def random_walk_map(self):
        self.pick_dimensions()
        self.map_data = [ ['%' for c in range(self.cols)] for r in range(self.rows) ]
        self.add_ants()
        self.start_walks()
        self.add_walk_land()

    #outputs the map
    def print_map(self):
        print "rows", self.rows
        print "cols", self.cols
        print "players", self.no_players
        for row in self.map_data:
            print 'm', ''.join(row)

    #picks the dimensions of the map
    def pick_dimensions(self):
        while True:
            while True:
                no_players = random.randint(self.min_players, self.max_players)
                self.no_players = no_players

                min_dim = max(self.per_player_dim[0] * no_players,
                        self.dim_bounds[0])
                max_dim = min(self.per_player_dim[1] * no_players,
                        self.dim_bounds[1])
                self.rows = random.randint(min_dim, max_dim)
                # make maps generally wider than they are tall
                min_cols = max(min_dim, int(self.rows * 0.80))
                max_cols = min(max_dim, int(self.rows * 2))
                self.cols = random.randint(min_cols, max_cols)

                if self.rows % no_players == 0 and self.cols % no_players == 0:
                    break

            row_p = random.randint(1, no_players-1)
            while gcd(row_p, no_players) != 1:
                row_p = random.randint(1, no_players-1)
            self.row_t = (self.rows / no_players) * row_p

            col_p = random.randint(1, no_players-1)
            while gcd(col_p, no_players) != 1:
                col_p = random.randint(1, no_players-1)
            self.col_t = (self.cols / no_players) * col_p

            if self.is_valid_start():
                break

    #returns the distance between two squares
    def distance(self, loc1, loc2):
        d1 = abs(loc1[0] - loc2[0])
        d2 = abs(loc1[1] - loc2[1])
        dr = min(d1, self.rows - d1)
        dc = min(d2, self.cols - d2)
        return math.sqrt(dr*dr + dc*dc)

    #randomly picks a location inside the map
    def pick_square(self):
        return [random.randint(0, self.rows-1), random.randint(0, self.cols-1)]

    #starts two random walks from the players starting ants
    def start_walks(self):
        self.c_locs = [self.a_loc, self.a_loc]
        for w in range(self.no_extra_walks):
            self.c_locs.append(self.pick_square())

    #walks the random walk locations
    def walk_locations(self):
        for c in range(len(self.c_locs)):
            d = self.cdirections[random.randint(0, 3)]
            self.c_locs[c] = self.get_loc(self.c_locs[c], d)

    #returns the new location after moving in a particular direction
    def get_loc(self, loc, direction):
        dr, dc = self.directions[direction]
        return [(loc[0]+dr)%self.rows, (loc[1]+dc)%self.cols ]

    #return the neighbors of the given location
    def get_neighbors(self, loc):
        n = []
        for d in self.directions.values():
            n.append(((loc[0]+d[0])%self.rows, (loc[1]+d[1])%self.cols))
        return n

    #returns the new location after translating it by (rtranslate, ctranslate)
    def get_translate_loc(self, loc):
        return [(loc[0]+self.row_t)%self.rows,
                (loc[1]+self.col_t)%self.cols ]

    #fills in all symmetrically equivalent squares with the given type
    def fill_squares(self, loc, type):
        value = type
        for n in range(self.no_players):
            self.map_data[loc[0] ][loc[1] ] = value
            if type == '0':
                value = chr(ord(value)+1)
            loc = self.get_translate_loc(loc)

    #checks whether the players start far enough apart
    def is_valid_start(self):
        loc = n_loc = [0,0]
        for n in range(self.no_players-1):
            n_loc = self.get_translate_loc(n_loc)
            if self.distance(loc, n_loc) < self.min_start_distance:
                return False
        return True

    #checks whether the players can reach every non-wall square
    def is_valid(self):
        start_loc = self.a_loc
        visited = [ [False for c in range(self.cols)] for r in range(self.rows)]
        visited[start_loc[0] ][start_loc[1] ] = True
        squaresVisited = 1

        stack = [start_loc]
        while stack:
            c_loc = stack.pop()
            for d in self.directions:
                n_loc = self.get_loc(c_loc, d)

                if not visited[n_loc[0]][n_loc[1]] and self.map_data[n_loc[0]][n_loc[1]] != '%':
                    stack.append(n_loc)
                    visited[n_loc[0] ][n_loc[1] ] = True
                    squaresVisited += 1

        if squaresVisited == self.land_squares:
            return True
        return False

    #adds ants to the map
    def add_ants(self):
        self.land_squares = self.no_players
        self.a_loc = self.pick_square()
        self.fill_squares(self.a_loc, '0')

    #adds land to a map of water
    def add_walk_land(self):
        #random.gauss(2,10)
        no_land_squares = random.randint(int(self.min_land_proportion*self.rows*self.cols),
                                          int(self.max_land_proportion*self.rows*self.cols))

        while self.land_squares < no_land_squares or not self.is_valid():
            self.walk_locations()

            for c_loc in self.c_locs:
                if self.map_data[c_loc[0]][c_loc[1]] == '%':
                    self.land_squares += self.no_players
                    self.fill_squares(c_loc, '.')

                    #fill in isolated water
                    wchecks = [s for s in self.get_neighbors(c_loc)
                            if self.map_data[s[0]][s[1]] == '%']
                    for check_sq in wchecks:
                        is_puddle = True
                        for cn in self.get_neighbors(check_sq):
                            if self.map_data[cn[0]][cn[1]] == '%':
                                is_puddle = False
                                break
                        if is_puddle:
                            self.land_squares += self.no_players
                            self.fill_squares(check_sq, '.')

        print >>sys.stderr, "Land per:", self.land_squares / float(self.rows * self.cols)

if __name__ == '__main__':
    example_map = SymmetricMap()
    example_map.random_walk_map()
    example_map.print_map()


########NEW FILE########
__FILENAME__ = playgame
#!/usr/bin/env python
from __future__ import print_function
import traceback
import sys
import os
import time
from optparse import OptionParser, OptionGroup
import random
import cProfile
import visualizer.visualize_locally
import json
try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO

from ants import Ants

sys.path.append("../worker")
try:
    from engine import run_game
except ImportError:
    # this can happen if we're launched with cwd outside our own dir
    # get our full path, then work relative from that
    cmd_folder = os.path.dirname(os.path.abspath(__file__))
    if cmd_folder not in sys.path:
        sys.path.insert(0, cmd_folder)
    sys.path.append(cmd_folder + "/../worker")
    # try again
    from engine import run_game

# make stderr red text
try:
    import colorama
    colorama.init()
    colorize = True
    color_default = (colorama.Fore.RED)
    color_reset = (colorama.Style.RESET_ALL)
except:
    colorize = False
    color_default = None
    color_reset = None

class Colorize(object):
    def __init__(self, file, color=color_default):
        self.file = file
        self.color = color
        self.reset = color_reset
    def write(self, data):
        if self.color:
            self.file.write(''.join(self.color))
        self.file.write(data)
        if self.reset:
            self.file.write(''.join(self.reset))
    def flush(self):
        self.file.flush()
    def close(self):
        self.file.close()

if colorize:
    stderr = Colorize(sys.stderr)
else:
    stderr = sys.stderr

class Comment(object):
    def __init__(self, file):
        self.file = file
        self.last_char = '\n'
    def write(self, data):
        for char in data:
            if self.last_char == '\n':
                self.file.write('# ')
            self.file.write(char)
            self.last_char = char
    def flush(self):
        self.file.flush()
    def close(self):
        self.file.close()

class Tee(object):
    ''' Write to multiple files at once '''
    def __init__(self, *files):
        self.files = files
    def write(self, data):
        for file in self.files:
            file.write(data)
    def flush(self):
        for file in self.files:
            file.flush()
    def close(self):
        for file in self.files:
            file.close()
            
def main(argv):
    usage ="Usage: %prog [options] map bot1 bot2\n\nYou must specify a map file."
    parser = OptionParser(usage=usage)

    # map to be played
    # number of players is determined by the map file
    parser.add_option("-m", "--map_file", dest="map",
                      help="Name of the map file")

    # maximum number of turns that the game will be played
    parser.add_option("-t", "--turns", dest="turns",
                      default=1000, type="int",
                      help="Number of turns in the game")

    parser.add_option("--serial", dest="serial",
                      action="store_true",
                      help="Run bots in serial, instead of parallel.")

    parser.add_option("--turntime", dest="turntime",
                      default=1000, type="int",
                      help="Amount of time to give each bot, in milliseconds")
    parser.add_option("--loadtime", dest="loadtime",
                      default=3000, type="int",
                      help="Amount of time to give for load, in milliseconds")
    parser.add_option("-r", "--rounds", dest="rounds",
                      default=1, type="int",
                      help="Number of rounds to play")
    parser.add_option("--player_seed", dest="player_seed",
                      default=None, type="int",
                      help="Player seed for the random number generator")
    parser.add_option("--engine_seed", dest="engine_seed",
                      default=None, type="int",
                      help="Engine seed for the random number generator")
    
    parser.add_option('--strict', dest='strict',
                      action='store_true', default=False,
                      help='Strict mode enforces valid moves for bots')
    parser.add_option('--capture_errors', dest='capture_errors',
                      action='store_true', default=False,
                      help='Capture errors and stderr in game result')
    parser.add_option('--end_wait', dest='end_wait',
                      default=0, type="float",
                      help='Seconds to wait at end for bots to process end')
    parser.add_option('--secure_jail', dest='secure_jail',
                      action='store_true', default=False,
                      help='Use the secure jail for each bot (*nix only)')
    parser.add_option('--fill', dest='fill',
                      action='store_true', default=False,
                      help='Fill up extra player starts with last bot specified')
    parser.add_option('-p', '--position', dest='position',
                      default=0, type='int',
                      help='Player position for first bot specified')

    # ants specific game options
    game_group = OptionGroup(parser, "Game Options", "Options that affect the game mechanics for ants")
    game_group.add_option("--attack", dest="attack",
                          default="focus",
                          help="Attack method to use for engine. (closest, focus, support, damage)")
    game_group.add_option("--kill_points", dest="kill_points",
                          default=2, type="int",
                          help="Points awarded for killing a hill")
    game_group.add_option("--food", dest="food",
                          default="symmetric",
                          help="Food spawning method. (none, random, sections, symmetric)")
    game_group.add_option("--viewradius2", dest="viewradius2",
                          default=77, type="int",
                          help="Vision radius of ants squared")
    game_group.add_option("--spawnradius2", dest="spawnradius2",
                          default=1, type="int",
                          help="Spawn radius of ants squared")
    game_group.add_option("--attackradius2", dest="attackradius2",
                          default=5, type="int",
                          help="Attack radius of ants squared")
    game_group.add_option("--food_rate", dest="food_rate", nargs=2, type="int", default=(5,11),
                          help="Numerator of food per turn per player rate")
    game_group.add_option("--food_turn", dest="food_turn", nargs=2, type="int", default=(19,37),
                          help="Denominator of food per turn per player rate")
    game_group.add_option("--food_start", dest="food_start", nargs=2, type="int", default=(75,175),
                          help="One over percentage of land area filled with food at start")
    game_group.add_option("--food_visible", dest="food_visible", nargs=2, type="int", default=(3,5),
                          help="Amount of food guaranteed to be visible to starting ants")
    game_group.add_option("--cutoff_turn", dest="cutoff_turn", type="int", default=150,
                          help="Number of turns cutoff percentage is maintained to end game early")
    game_group.add_option("--cutoff_percent", dest="cutoff_percent", type="float", default=0.85,
                          help="Number of turns cutoff percentage is maintained to end game early")
    game_group.add_option("--scenario", dest="scenario",
                          action='store_true', default=False)
    parser.add_option_group(game_group)

    # the log directory must be specified for any logging to occur, except:
    #    bot errors to stderr
    #    verbose levels 1 & 2 to stdout and stderr
    #    profiling to stderr
    # the log directory will contain
    #    the replay or stream file used by the visualizer, if requested
    #    the bot input/output/error logs, if requested    
    log_group = OptionGroup(parser, "Logging Options", "Options that control the logging")
    log_group.add_option("-g", "--game", dest="game_id", default=0, type='int',
                         help="game id to start at when numbering log files")
    log_group.add_option("-l", "--log_dir", dest="log_dir", default=None,
                         help="Directory to dump replay files to.")
    log_group.add_option('-R', '--log_replay', dest='log_replay',
                         action='store_true', default=False),
    log_group.add_option('-S', '--log_stream', dest='log_stream',
                         action='store_true', default=False),
    log_group.add_option("-I", "--log_input", dest="log_input",
                         action="store_true", default=False,
                         help="Log input streams sent to bots")
    log_group.add_option("-O", "--log_output", dest="log_output",
                         action="store_true", default=False,
                         help="Log output streams from bots")
    log_group.add_option("-E", "--log_error", dest="log_error",
                         action="store_true", default=False,
                         help="log error streams from bots")
    log_group.add_option('-e', '--log_stderr', dest='log_stderr',
                         action='store_true', default=False,
                         help='additionally log bot errors to stderr')
    log_group.add_option('-o', '--log_stdout', dest='log_stdout',
                         action='store_true', default=False,
                         help='additionally log replay/stream to stdout')
    # verbose will not print bot input/output/errors
    # only info+debug will print bot error output
    log_group.add_option("-v", "--verbose", dest="verbose",
                         action='store_true', default=False,
                         help="Print out status as game goes.")
    log_group.add_option("--profile", dest="profile",
                         action="store_true", default=False,
                         help="Run under the python profiler")
    parser.add_option("--nolaunch", dest="nolaunch",
                      action='store_true', default=False,
                      help="Prevent visualizer from launching")
    log_group.add_option("--html", dest="html_file",
                         default=None,
                         help="Output file name for an html replay")
    parser.add_option_group(log_group)

    (opts, args) = parser.parse_args(argv)
    if opts.map is None or not os.path.exists(opts.map):
        parser.print_help()
        return -1
    try:
        if opts.profile:
            # put profile file into output dir if we can
            prof_file = "ants.profile"
            if opts.log_dir:
                prof_file = os.path.join(opts.log_dir, prof_file)
            # cProfile needs to be explitly told about out local and global context
            print("Running profile and outputting to {0}".format(prof_file,), file=stderr)
            cProfile.runctx("run_rounds(opts,args)", globals(), locals(), prof_file)
        else:
            # only use psyco if we are not profiling
            # (psyco messes with profiling)
            try:
                import psyco
                psyco.full()
            except ImportError:
                pass
            run_rounds(opts,args)
        return 0
    except Exception:
        traceback.print_exc()
        return -1

def run_rounds(opts,args):
    def get_cmd_wd(cmd, exec_rel_cwd=False):
        ''' get the proper working directory from a command line '''
        new_cmd = []
        wd = None
        for i, part in reversed(list(enumerate(cmd.split()))):
            if wd == None and os.path.exists(part):
                wd = os.path.dirname(os.path.realpath(part))
                basename = os.path.basename(part)
                if i == 0:
                    if exec_rel_cwd:
                        new_cmd.insert(0, os.path.join(".", basename))
                    else:
                        new_cmd.insert(0, part)
                else:
                    new_cmd.insert(0, basename)
            else:
                new_cmd.insert(0, part)
        return wd, ' '.join(new_cmd)
    def get_cmd_name(cmd):
        ''' get the name of a bot from the command line '''
        for i, part in enumerate(reversed(cmd.split())):
            if os.path.exists(part):
                return os.path.basename(part)
# this split of options is not needed, but left for documentation
    game_options = {
        "map": opts.map,
        "attack": opts.attack,
        "kill_points": opts.kill_points,
        "food": opts.food,
        "viewradius2": opts.viewradius2,
        "attackradius2": opts.attackradius2,
        "spawnradius2": opts.spawnradius2,
        "loadtime": opts.loadtime,
        "turntime": opts.turntime,
        "turns": opts.turns,
        "food_rate": opts.food_rate,
        "food_turn": opts.food_turn,
        "food_start": opts.food_start,
        "food_visible": opts.food_visible,
        "cutoff_turn": opts.cutoff_turn,
        "cutoff_percent": opts.cutoff_percent,
        "scenario": opts.scenario }
    if opts.player_seed != None:
        game_options['player_seed'] = opts.player_seed
    if opts.engine_seed != None:
        game_options['engine_seed'] = opts.engine_seed
    engine_options = {
        "loadtime": opts.loadtime,
        "turntime": opts.turntime,
        "map_file": opts.map,
        "turns": opts.turns,
        "log_replay": opts.log_replay,
        "log_stream": opts.log_stream,
        "log_input": opts.log_input,
        "log_output": opts.log_output,
        "log_error": opts.log_error,
        "serial": opts.serial,
        "strict": opts.strict,
        "capture_errors": opts.capture_errors,
        "secure_jail": opts.secure_jail,
        "end_wait": opts.end_wait }
    for round in range(opts.rounds):
        # initialize game
        game_id = round + opts.game_id
        with open(opts.map, 'r') as map_file:
            game_options['map'] = map_file.read()
        if opts.engine_seed:
            game_options['engine_seed'] = opts.engine_seed + round
        game = Ants(game_options)
        # initialize bots
        bots = [get_cmd_wd(arg, exec_rel_cwd=opts.secure_jail) for arg in args]
        bot_count = len(bots)
        # insure correct number of bots, or fill in remaining positions
        if game.num_players != len(bots):
            if game.num_players > len(bots) and opts.fill:
                extra = game.num_players - len(bots)
                for _ in range(extra):
                    bots.append(bots[-1])
            else:
                print("Incorrect number of bots for map.  Need {0}, got {1}"
                      .format(game.num_players, len(bots)), file=stderr)
                for arg in args:
                    print("Bot Cmd: {0}".format(arg), file=stderr)
                break
        bot_count = len(bots)
        # move position of first bot specified
        if opts.position > 0 and opts.position <= len(bots):
            first_bot = bots[0]
            bots = bots[1:]
            bots.insert(opts.position, first_bot)

        # initialize file descriptors
        if opts.log_dir and not os.path.exists(opts.log_dir):
            os.mkdir(opts.log_dir)
        if not opts.log_replay and not opts.log_stream and (opts.log_dir or opts.log_stdout):
            opts.log_replay = True
        replay_path = None # used for visualizer launch
        
        if opts.log_replay:
            if opts.log_dir:
                replay_path = os.path.join(opts.log_dir, '{0}.replay'.format(game_id))
                engine_options['replay_log'] = open(replay_path, 'w')
            if opts.log_stdout:
                if 'replay_log' in engine_options and engine_options['replay_log']:
                    engine_options['replay_log'] = Tee(sys.stdout, engine_options['replay_log'])
                else:
                    engine_options['replay_log'] = sys.stdout
        else:
            engine_options['replay_log'] = None

        if opts.log_stream:
            if opts.log_dir:
                engine_options['stream_log'] = open(os.path.join(opts.log_dir, '{0}.stream'.format(game_id)), 'w')
            if opts.log_stdout:
                if engine_options['stream_log']:
                    engine_options['stream_log'] = Tee(sys.stdout, engine_options['stream_log'])
                else:
                    engine_options['stream_log'] = sys.stdout
        else:
            engine_options['stream_log'] = None
        
        if opts.log_input and opts.log_dir:
            engine_options['input_logs'] = [open(os.path.join(opts.log_dir, '{0}.bot{1}.input'.format(game_id, i)), 'w')
                             for i in range(bot_count)]
        else:
            engine_options['input_logs'] = None
        if opts.log_output and opts.log_dir:
            engine_options['output_logs'] = [open(os.path.join(opts.log_dir, '{0}.bot{1}.output'.format(game_id, i)), 'w')
                              for i in range(bot_count)]
        else:
            engine_options['output_logs'] = None
        if opts.log_error and opts.log_dir:
            if opts.log_stderr:
                if opts.log_stdout:
                    engine_options['error_logs'] = [Tee(Comment(stderr), open(os.path.join(opts.log_dir, '{0}.bot{1}.error'.format(game_id, i)), 'w'))
                                      for i in range(bot_count)]
                else:
                    engine_options['error_logs'] = [Tee(stderr, open(os.path.join(opts.log_dir, '{0}.bot{1}.error'.format(game_id, i)), 'w'))
                                      for i in range(bot_count)]
            else:
                engine_options['error_logs'] = [open(os.path.join(opts.log_dir, '{0}.bot{1}.error'.format(game_id, i)), 'w')
                                  for i in range(bot_count)]
        elif opts.log_stderr:
            if opts.log_stdout:
                engine_options['error_logs'] = [Comment(stderr)] * bot_count
            else:
                engine_options['error_logs'] = [stderr] * bot_count
        else:
            engine_options['error_logs'] = None
        
        if opts.verbose:
            if opts.log_stdout:
                engine_options['verbose_log'] = Comment(sys.stdout)
            else:
                engine_options['verbose_log'] = sys.stdout
            
        engine_options['game_id'] = game_id 
        if opts.rounds > 1:
            print('# playgame round {0}, game id {1}'.format(round, game_id))

        # intercept replay log so we can add player names
        if opts.log_replay:
            intcpt_replay_io = StringIO()
            real_replay_io = engine_options['replay_log']
            engine_options['replay_log'] = intcpt_replay_io

        result = run_game(game, bots, engine_options)

        # add player names, write to proper io, reset back to normal
        if opts.log_replay:
            replay_json = json.loads(intcpt_replay_io.getvalue())
            replay_json['playernames'] = [get_cmd_name(arg) for arg in args]
            real_replay_io.write(json.dumps(replay_json))
            intcpt_replay_io.close()
            engine_options['replay_log'] = real_replay_io

        # close file descriptors
        if engine_options['stream_log']:
            engine_options['stream_log'].close()
        if engine_options['replay_log']:
            engine_options['replay_log'].close()
        if engine_options['input_logs']:
            for input_log in engine_options['input_logs']:
                input_log.close()
        if engine_options['output_logs']:
            for output_log in engine_options['output_logs']:
                output_log.close()
        if engine_options['error_logs']:
            for error_log in engine_options['error_logs']:
                error_log.close()
        if replay_path:
            if opts.nolaunch:
                if opts.html_file:
                    visualizer.visualize_locally.launch(replay_path, True, opts.html_file)
            else:
                if opts.html_file == None:
                    visualizer.visualize_locally.launch(replay_path,
                            generated_path="replay.{0}.html".format(game_id))
                else:
                    visualizer.visualize_locally.launch(replay_path,
                            generated_path=opts.html_file)
if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

########NEW FILE########
__FILENAME__ = ants
#!/usr/bin/env python
import sys
import traceback
import random
import time
from collections import defaultdict
from math import sqrt

MY_ANT = 0
ANTS = 0
DEAD = -1
LAND = -2
FOOD = -3
WATER = -4

PLAYER_ANT = 'abcdefghij'
HILL_ANT = string = 'ABCDEFGHI'
PLAYER_HILL = string = '0123456789'
MAP_OBJECT = '?%*.!'
MAP_RENDER = PLAYER_ANT + HILL_ANT + PLAYER_HILL + MAP_OBJECT

AIM = {'n': (-1, 0),
       'e': (0, 1),
       's': (1, 0),
       'w': (0, -1)}
RIGHT = {'n': 'e',
         'e': 's',
         's': 'w',
         'w': 'n'}
LEFT = {'n': 'w',
        'e': 'n',
        's': 'e',
        'w': 's'}
BEHIND = {'n': 's',
          's': 'n',
          'e': 'w',
          'w': 'e'}

class Ants():
    def __init__(self):
        self.cols = None
        self.rows = None
        self.map = None
        self.hill_list = {}
        self.ant_list = {}
        self.dead_list = defaultdict(list)
        self.food_list = []
        self.turntime = 0
        self.loadtime = 0
        self.turn_start_time = None
        self.vision = None
        self.viewradius2 = 0
        self.attackradius2 = 0
        self.spawnradius2 = 0
        self.turns = 0

    def setup(self, data):
        'parse initial input and setup starting game state'
        for line in data.split('\n'):
            line = line.strip().lower()
            if len(line) > 0:
                tokens = line.split()
                key = tokens[0]
                if key == 'cols':
                    self.cols = int(tokens[1])
                elif key == 'rows':
                    self.rows = int(tokens[1])
                elif key == 'player_seed':
                    random.seed(int(tokens[1]))
                elif key == 'turntime':
                    self.turntime = int(tokens[1])
                elif key == 'loadtime':
                    self.loadtime = int(tokens[1])
                elif key == 'viewradius2':
                    self.viewradius2 = int(tokens[1])
                elif key == 'attackradius2':
                    self.attackradius2 = int(tokens[1])
                elif key == 'spawnradius2':
                    self.spawnradius2 = int(tokens[1])
                elif key == 'turns':
                    self.turns = int(tokens[1])
        self.map = [[LAND for col in range(self.cols)]
                    for row in range(self.rows)]

    def update(self, data):
        'parse engine input and update the game state'
        # start timer
        self.turn_start_time = time.clock()
        
        # reset vision
        self.vision = None
        
        # clear hill, ant and food data
        self.hill_list = {}
        for row, col in self.ant_list.keys():
            self.map[row][col] = LAND
        self.ant_list = {}
        for row, col in self.dead_list.keys():
            self.map[row][col] = LAND
        self.dead_list = defaultdict(list)
        for row, col in self.food_list:
            self.map[row][col] = LAND
        self.food_list = []
        
        # update map and create new ant and food lists
        for line in data.split('\n'):
            line = line.strip().lower()
            if len(line) > 0:
                tokens = line.split()
                if len(tokens) >= 3:
                    row = int(tokens[1])
                    col = int(tokens[2])
                    if tokens[0] == 'w':
                        self.map[row][col] = WATER
                    elif tokens[0] == 'f':
                        self.map[row][col] = FOOD
                        self.food_list.append((row, col))
                    else:
                        owner = int(tokens[3])
                        if tokens[0] == 'a':
                            self.map[row][col] = owner
                            self.ant_list[(row, col)] = owner
                        elif tokens[0] == 'd':
                            # food could spawn on a spot where an ant just died
                            # don't overwrite the space unless it is land
                            if self.map[row][col] == LAND:
                                self.map[row][col] = DEAD
                            # but always add to the dead list
                            self.dead_list[(row, col)].append(owner)
                        elif tokens[0] == 'h':
                            owner = int(tokens[3])
                            self.hill_list[(row, col)] = owner
                        
    def time_remaining(self):
        return self.turntime - int(1000 * (time.clock() - self.turn_start_time))
    
    def issue_order(self, order):
        'issue an order by writing the proper ant location and direction'
        (row, col), direction = order
        sys.stdout.write('o %s %s %s\n' % (row, col, direction))
        sys.stdout.flush()
        
    def finish_turn(self):
        'finish the turn by writing the go line'
        sys.stdout.write('go\n')
        sys.stdout.flush()
    
    def my_hills(self):
        return [loc for loc, owner in self.hill_list.items()
                    if owner == MY_ANT]

    def enemy_hills(self):
        return [(loc, owner) for loc, owner in self.hill_list.items()
                    if owner != MY_ANT]
        
    def my_ants(self):
        'return a list of all my ants'
        return [(row, col) for (row, col), owner in self.ant_list.items()
                    if owner == MY_ANT]

    def enemy_ants(self):
        'return a list of all visible enemy ants'
        return [((row, col), owner)
                    for (row, col), owner in self.ant_list.items()
                    if owner != MY_ANT]

    def food(self):
        'return a list of all food locations'
        return self.food_list[:]

    def passable(self, loc):
        'true if not water'
        row, col = loc
        return self.map[row][col] != WATER
    
    def unoccupied(self, loc):
        'true if no ants are at the location'
        row, col = loc
        return self.map[row][col] in (LAND, DEAD)

    def destination(self, loc, direction):
        'calculate a new location given the direction and wrap correctly'
        row, col = loc
        d_row, d_col = AIM[direction]
        return ((row + d_row) % self.rows, (col + d_col) % self.cols)        

    def distance(self, loc1, loc2):
        'calculate the closest distance between to locations'
        row1, col1 = loc1
        row2, col2 = loc2
        d_col = min(abs(col1 - col2), self.cols - abs(col1 - col2))
        d_row = min(abs(row1 - row2), self.rows - abs(row1 - row2))
        return d_row + d_col

    def direction(self, loc1, loc2):
        'determine the 1 or 2 fastest (closest) directions to reach a location'
        row1, col1 = loc1
        row2, col2 = loc2
        height2 = self.rows//2
        width2 = self.cols//2
        d = []
        if row1 < row2:
            if row2 - row1 >= height2:
                d.append('n')
            if row2 - row1 <= height2:
                d.append('s')
        if row2 < row1:
            if row1 - row2 >= height2:
                d.append('s')
            if row1 - row2 <= height2:
                d.append('n')
        if col1 < col2:
            if col2 - col1 >= width2:
                d.append('w')
            if col2 - col1 <= width2:
                d.append('e')
        if col2 < col1:
            if col1 - col2 >= width2:
                d.append('e')
            if col1 - col2 <= width2:
                d.append('w')
        return d

    def visible(self, loc):
        ' determine which squares are visible to the given player '

        if self.vision == None:
            if not hasattr(self, 'vision_offsets_2'):
                # precalculate squares around an ant to set as visible
                self.vision_offsets_2 = []
                mx = int(sqrt(self.viewradius2))
                for d_row in range(-mx,mx+1):
                    for d_col in range(-mx,mx+1):
                        d = d_row**2 + d_col**2
                        if d <= self.viewradius2:
                            self.vision_offsets_2.append((
                                d_row%self.rows-self.rows,
                                d_col%self.cols-self.cols
                            ))
            # set all spaces as not visible
            # loop through ants and set all squares around ant as visible
            self.vision = [[False]*self.cols for row in range(self.rows)]
            for ant in self.my_ants():
                a_row, a_col = ant
                for v_row, v_col in self.vision_offsets_2:
                    self.vision[a_row+v_row][a_col+v_col] = True
        row, col = loc
        return self.vision[row][col]
    
    def render_text_map(self):
        'return a pretty string representing the map'
        tmp = ''
        for row in self.map:
            tmp += '# %s\n' % ''.join([MAP_RENDER[col] for col in row])
        return tmp

    # static methods are not tied to a class and don't have self passed in
    # this is a python decorator
    @staticmethod
    def run(bot):
        'parse input, update game state and call the bot classes do_turn method'
        ants = Ants()
        map_data = ''
        while(True):
            try:
                current_line = sys.stdin.readline().rstrip('\r\n') # string new line char
                if current_line.lower() == 'ready':
                    ants.setup(map_data)
                    bot.do_setup(ants)
                    ants.finish_turn()
                    map_data = ''
                elif current_line.lower() == 'go':
                    ants.update(map_data)
                    # call the do_turn method of the class passed in
                    bot.do_turn(ants)
                    ants.finish_turn()
                    map_data = ''
                else:
                    map_data += current_line + '\n'
            except EOFError:
                break
            except KeyboardInterrupt:
                raise
            except:
                # don't raise error or return so that bot attempts to stay alive
                traceback.print_exc(file=sys.stderr)
                sys.stderr.flush()
########NEW FILE########
__FILENAME__ = TestBot
#!/usr/bin/env python
from ants import *

# define a class with a do_turn method
# the Ants.run method will parse and update bot input
# it will also run the do_turn method for us
class MyBot:
    def __init__(self):
        # define class level variables, will be remembered between turns
        pass
    
    # do_setup is run once at the start of the game
    # after the bot has received the game settings
    # the ants class is created and setup by the Ants.run method
    def do_setup(self, ants):
        # initialize data structures after learning the game settings
        pass
    
    # do turn is run once per turn
    # the ants class has the game state and is updated by the Ants.run method
    # it also has several helper methods to use
    def do_turn(self, ants):
        # loop through all my ants and try to give them orders
        # the ant_loc is an ant location tuple in (row, col) form
        for ant_loc in ants.my_ants():
            # try all directions in given order
            directions = ('n','e','s','w')
            for direction in directions:
                # the destination method will wrap around the map properly
                # and give us a new (row, col) tuple
                new_loc = ants.destination(ant_loc, direction)
                # passable returns true if the location is land
                if (ants.passable(new_loc)):
                    # an order is the location of a current ant and a direction
                    ants.issue_order((ant_loc, direction))
                    # stop now, don't give 1 ant multiple orders
                    break
            # check if we still have time left to calculate more orders
            if ants.time_remaining() < 10:
                break
            
if __name__ == '__main__':
    # psyco will speed up python a little, but is not needed
    try:
        import psyco
        psyco.full()
    except ImportError:
        pass
    
    try:
        # if run is passed a class with a do_turn method, it will do the work
        # this is not needed, in which case you will need to write your own
        # parsing function and your own game state class
        Ants.run(MyBot())
    except KeyboardInterrupt:
        print('ctrl-c, leaving ...')

########NEW FILE########
__FILENAME__ = battle_sim
#!/usr/bin/env python

"""
    Simulates a battle using each attack option
    ./battle_sim.py [attackradius2]

    attackradius2 is optional, default is 6.

    Map is read in via stdin until EOF or a blank line is encountered.
    Map is automatically padded out to be rectangular.
    Spaces count as LAND.
    Newlines seperate rows but pipes (|) may also be used.
        Pipes are useful for creating one liners:
        ./battle_sim.py <<<"a.b.c||..a"
    Wrapping does not affect the battles.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from ants import Ants, MAP_RENDER, PLAYER_CHARS
from math import sqrt

def create_map_data(map_segment, buffer):
    # horizontal buffer
    map_segment = ['.'*buffer + s + '.'*buffer for s in map_segment]

    # vertical buffer
    width = len(map_segment[0])
    map_segment = ['.'*width]*buffer + map_segment + ['.'*width]*buffer
    height = len(map_segment)

    # create the map text
    map_data = []
    map_data.append(['rows', height])
    map_data.append(['cols', width])
    map_data.extend(['m', s] for s in map_segment)
    map_data.append([])

    return '\n'.join(' '.join(map(str,s)) for s in map_data)

def create_map_output(map_grid, buffer):
    # remove vertical buffer
    map_grid = map_grid[buffer:-buffer]

    # remove horizontal buffer
    map_grid = [row[buffer:-buffer] for row in map_grid]

    return [''.join(MAP_RENDER[c] for c in row) for row in map_grid]

def simulate_battle(map_segment, attackradius2, attack_method):
    # add buffer so that battles aren't affected by wrapping
    buffer = int(sqrt(attackradius2)) + 1

    map_data = create_map_data(map_segment, buffer)

    game = Ants({
        'attackradius2': attackradius2,
        'map': map_data,
        'attack': attack_method,
        # the rest of these options don't matter
        'loadtime': 0,
        'turntime': 0,
        'viewradius2': 100,
        'spawnradius2': 2,
        'turns': 1
    })
    game.do_attack()

    # remove buffer and return
    return create_map_output(game.map, buffer)

def read_map_segment():
    map_segment = []

    # read from stdin until we get an empty line
    while True:
        line = sys.stdin.readline().rstrip()
        if line:
            map_segment.extend(line.split('|'))
        else:
            break

    # normalise
    width = max(map(len,map_segment))
    map_segment = [s.ljust(width).replace(' ','.') for s in map_segment]

    return map_segment

def reset_player_names(before, after):
    after = map(list, after)
    for i, row in enumerate(after):
        for j, value in enumerate(row):
            if value in PLAYER_CHARS:
                after[i][j] = before[i][j]
    return [''.join(s) for s in after]

if __name__ == "__main__":
    attackradius2 = 6
    if len(sys.argv) > 1:
        attackradius2 = int(sys.argv[1])

    map_segment = read_map_segment()

    print '\n'.join(map_segment)

    for method in ['power', 'closest', 'support', 'damage']:
        result = simulate_battle(map_segment, attackradius2, method)
        result = reset_player_names(map_segment, result)

        print
        print method + ":"
        print '\n'.join(result)

########NEW FILE########
__FILENAME__ = vision_compare
#!/usr/bin/python
# For comparing the speed of the two vision algorithms
# usage: vision_compare.py [block_size] [ant_spacing]
#   block_size, is the number of rows and columns of ants to use
#       (default is a 10x10 block of ants)
#   spacing is the amount of space between each row and column
#       (it defaults to 1 space in between if not supplied)


import sys
import timeit
from collections import deque, defaultdict
from math import sqrt

# possible directions an ant can move
AIM = {'n': (-1, 0),
       'e': (0, 1),
       's': (1, 0),
       'w': (0, -1)}
HORIZ_DIRECTIONS = [(-1,0),(0,1),(1,0),(0,-1)]
DIAG_DIRECTIONS = [(1,1),(-1,1),(1,-1),(-1,-1)]

class Ant:
    def __init__(self, loc):
        self.loc = loc

class CheckVision:
    def __init__(self, ant_locs, size, vr2=96):
        self.ants = [Ant(l) for l in ant_locs]
        self.height = size[0]
        self.width = size[1]
        self.viewradius2 = vr2

    def player_ants(self, player):
        return self.ants

    def destination(self, loc, d):
        """ Returns the location produced by offsetting loc by d """
        return ((loc[0] + d[0]) % self.height, (loc[1] + d[1]) % self.width)

    def distance(self, x, y):
        """ Returns distance between x and y squared """
        d_row = abs(x[0] - y[0])
        d_row = min(d_row, self.height - d_row)
        d_col = abs(x[1] - y[1])
        d_col = min(d_col, self.width - d_col)
        return d_row**2 + d_col**2

    def vision_by_ant_faster(self, player=0):
        """ Determine which squares are visible to the given player """

        if not hasattr(self, 'vision_offsets_2'):
            # precalculate squares to test
            self.vision_offsets_2 = []
            mx = int(sqrt(self.viewradius2))
            for d_row in range(-mx,mx+1):
                for d_col in range(-mx,mx+1):
                    d = d_row**2 + d_col**2
                    if d <= self.viewradius2:
                        self.vision_offsets_2.append((
                            d_row%self.height-self.height,
                            d_col%self.width-self.width
                        ))

        vision = [[False]*self.width for row in range(self.height)]
        for ant in self.player_ants(player):
            a_row, a_col = ant.loc
            for v_row, v_col in self.vision_offsets_2:
                vision[a_row+v_row][a_col+v_col] = True
        return vision

    def vision_by_ant(self, player=0):
        """ Determine which squares are visible to the given player """

        if not hasattr(self, 'vision_offsets'):
            # precalculate squares to test
            self.vision_offsets = []
            mx = int(sqrt(self.viewradius2))
            for d_row in range(-mx,mx+1):
                for d_col in range(-mx,mx+1):
                    d = d_row**2 + d_col**2
                    if d <= self.viewradius2:
                        self.vision_offsets.append((d_row,d_col))

        vision = [[False]*self.width for row in range(self.height)]
        for ant in self.player_ants(player):
            loc = ant.loc
            for v_loc in self.vision_offsets:
                row, col = self.destination(ant.loc, v_loc)
                vision[row][col] = True
        return vision

    def vision_distance(self, loc1, loc2):
        # this returns the square of the euclidean distance
        # so it can be compared with the viewradius2, which is squared
        row1, col1 = loc1
        row2, col2 = loc2
        d_col = min(abs(col1 - col2), self.width - abs(col1 - col2))
        d_row = min(abs(row1 - row2), self.height - abs(row1 - row2))
        return d_row**2 + d_col**2

    def vision_by_square(self, player=0):
        'determine which squares are visible to the given player'
        """ DOESN'T WORK """

        vision = [[False for col in range(self.width)]
                       for row in range(self.height)]
        # squares_to_check is a list of painted squares that may still
        # have unpainted squares near it
        # a deque is like a list, but faster when poping items from the left
        squares_to_check = deque()
        # for each ant, slowly paint all the squares around it
        # keep rotating ants so that they all paint at the same rate
        # if 2 ants paint the same square, it is merged and we save time
        for ant in self.player_ants(player):
            squares_to_check.append((ant.loc, ant.loc))
        while squares_to_check:
            a_loc, v_loc = squares_to_check.popleft()
            # paint all 4 squares around the square to check at once
            for d in AIM.values():
                n_loc = self.destination(v_loc, d)
                n_row, n_col = n_loc
                if (not vision[n_row][n_col] and
                        self.vision_distance(a_loc, n_loc) <= self.viewradius2):
                    # we can see this square
                    vision[n_row][n_col] = True
                    # add to list to see if other square near it are also
                    # visible
                    squares_to_check.append((a_loc, n_loc))
        return vision

    def vision_by_distance(self, player=0):
        """ DOESN'T WORK """
        vision = [[False]*self.width for row in range(self.height)]
        min_dist = 0
        squares_to_check = [[] for i in range(self.viewradius2 + 1)]
        squares_to_check.append([None]) # sentinal
        for ant in self.player_ants(player):
            squares_to_check[0].append((ant.loc, ant.loc))
            vision[ant.loc[0]][ant.loc[1]] = True
        while min_dist <= self.viewradius2:
            a_loc, v_loc = squares_to_check[min_dist].pop()
            while not squares_to_check[min_dist]:
                min_dist += 1
            for d in AIM.values():
                n_loc = self.destination(v_loc, d)
                n_row, n_col = n_loc
                if not vision[n_row][n_col]:
                    dist = self.vision_distance(a_loc, n_loc)
                    if dist <= self.viewradius2:
                        vision[n_row][n_col] = True
                        squares_to_check[dist].append((a_loc, n_loc))
        return vision

    def vision_by_distance_2(self, player=0):
        vision = [[False]*self.width for row in range(self.height)]
        squares_to_check = [[] for i in range(self.viewradius2 + 1)]
        for ant in self.player_ants(player):
            squares_to_check[0].append((ant.loc, ant.loc))
            vision[ant.loc[0]][ant.loc[1]] = True
        for locs in squares_to_check:
            for d_set in (HORIZ_DIRECTIONS, DIAG_DIRECTIONS):
                for a_loc, v_loc in locs:
                    for d in d_set:
                        n_row, n_col = n_loc = self.destination(v_loc, d)
                        if not vision[n_row][n_col]:
                            dist = self.vision_distance(a_loc, n_loc)
                            if dist <= self.viewradius2:
                                vision[n_row][n_col] = True
                                squares_to_check[dist].append((a_loc, n_loc))
        return vision

    def vision_by_distance_2_faster(self, player=0):
        """ vision_by_distance_2 without function calls """
        vision = [[False]*self.width for row in range(self.height)]
        squares_to_check = [[] for i in range(self.viewradius2 + 1)]
        for ant in self.player_ants(player):
            squares_to_check[0].append((ant.loc[0], ant.loc[1], ant.loc[0], ant.loc[1]))
            vision[ant.loc[0]][ant.loc[1]] = True
        for locs in squares_to_check:
            for d_set in (HORIZ_DIRECTIONS, DIAG_DIRECTIONS):
                for a_row, a_col, v_row, v_col in locs:
                    for d_row, d_col in d_set:
                        n_row = (v_row+d_row)%self.height
                        n_col = (v_col+d_col)%self.width
                        if not vision[n_row][n_col]:
                            d_row = abs(n_row-a_row)
                            d_row = min(d_row, self.height - d_row)
                            d_col = abs(a_col-n_col)
                            d_col = min(d_col, self.width - d_col)
                            dist = d_row**2 + d_col**2
                            if dist <= self.viewradius2:
                                vision[n_row][n_col] = True
                                squares_to_check[dist].append((a_row,a_col,n_row,n_col))
        return vision

def make_block(size, offset=0, spacing=1):
    locs = []
    for row in xrange(size[0]):
        for col in xrange(size[1]):
            locs.append(((row * spacing) + offset, (col * spacing) + offset))
    return locs

def time_to_str(seconds):
    units = ["secs", "msecs", "usecs", "nsecs"]
    for unit in units:
        if seconds > 0.1:
            break
        seconds *= 1000.
    return "%.2f %s" % (seconds, unit)

def vision_to_str(vision):
    return '\n'.join(''.join('x' if v is True else v if v  else '.' for v in row) for row in vision)

def check_algos(algo):
    print "Checking %s against vision_by_ant" %(algo,)
    size = (50, 50)
    cloc = (25, 25)
    result = True
    for row in xrange(size[0]):
        for col in xrange(size[1]):
            cv = CheckVision([cloc, (row, col)], size)
            by_ant = cv.vision_by_ant()
            other = getattr(cv,algo)()
            if by_ant != other:
                print "Vision didn't match"
                print "first ant at", cloc
                print "second ant at", (row, col)
                print vision_to_str(by_ant)
                print
                print vision_to_str(other)
                return False
    return result

def time_algo(algo, repetitions=1000):
    print "Timing " + algo
    time = timeit.timeit("cv.%s()" %(algo,),
            setup="from __main__ import cv", number=repetitions)
    print "It took %s per call to %s" % (
            time_to_str(time / repetitions), algo)

if __name__ == "__main__":
    block_size = 5
    if len(sys.argv) > 1:
        block_size = int(sys.argv[1])
    spacing = 2
    if len(sys.argv) > 2:
        spacing = int(sys.argv[2]) + 1
    size = max(120, ((block_size-1) * spacing) + 30)
    size = (size, size)
    if not check_algos('vision_by_distance_2'): sys.exit()
    if not check_algos('vision_by_distance_2_faster'): sys.exit()
    if not check_algos('vision_by_ant_faster'): sys.exit()
    global cv
    cv = CheckVision(make_block((block_size, block_size), 15, spacing), size)
    time_algo("vision_by_ant")
    time_algo("vision_by_distance_2_faster")
    time_algo("vision_by_ant_faster")
    #time_algo("vision_by_distance")
    time_algo("vision_by_distance_2")
    # time_algo("vision_by_square")


########NEW FILE########
__FILENAME__ = visualize_locally
#!/usr/bin/env python

import re
import sys
import os
import webbrowser
import json

def generate(data, generated_path):
    path = os.path.dirname(__file__)
    template_path = os.path.join(path, 'replay.html.template')
    template = open(template_path, 'r')
    content = template.read()
    template.close()

    path1 = os.path.realpath(__file__)
    path2 = os.path.realpath(generated_path)
    common = os.path.commonprefix((path1, path2))
    path1 = path1[len(common):]
    path2 = path2[len(common):]
    mod_path = '/'.join(['..'] * (path2.count(os.sep)) + [os.path.split(path1)[0].replace('\\', '/')])
    if len(mod_path) > 0 and mod_path[-1] != '/':
        mod_path += '/'

    quote_re = re.compile("'")
    newline_re = re.compile("\s", re.MULTILINE)
    insert_re = re.compile(r"## REPLAY PLACEHOLDER ##")
    path_re = re.compile(r"## PATH PLACEHOLDER ##")
    
    try:
        json.loads(data)
        data = quote_re.sub(r"\\\\'", data)
        data = newline_re.sub("", data)
    except ValueError:
        data = data.replace('\n', '\\\\n')

    content = path_re.sub(mod_path, content)
    content = insert_re.sub(data, content)   
       
    output = open(generated_path, 'w')
    output.write(content)
    output.close()

def launch(filename=None, nolaunch=False, generated_path=None):
    if generated_path == None:
        generated_path = 'replay.html'
    if filename == None:
        data = sys.stdin.read()
        generated_path = os.path.realpath(os.path.join(os.path.dirname(__file__)
                                                       , generated_path))
    else:
        with open(filename, 'r') as f:
            data = f.read()
        generated_path = os.path.join(os.path.split(filename)[0], generated_path)

    generate(data, generated_path)

    # open the page in the browser
    if not nolaunch:
        webbrowser.open('file://'+os.path.realpath(generated_path))    

if __name__ == "__main__":
    launch(nolaunch=len(sys.argv) > 1 and sys.argv[1] == '--nolaunch')

########NEW FILE########
__FILENAME__ = create_test_accounts
#!/usr/bin/env python

import MySQLdb
import random
from server_info import server_info
import sys

if len(sys.argv) != 2:
  print "USAGE: python create_accounts.py num_accounts"
  sys.exit(1)
n = int(sys.argv[1])
connection = MySQLdb.connect(host = server_info["db_host"],
                             user = server_info["db_username"],
                             passwd = server_info["db_password"],
                             db = server_info["db_name"])
cursor = connection.cursor(MySQLdb.cursors.DictCursor)
for i in range(1, n + 1):
  username = "testbot" + str(i)
  country_id = str(random.randint(0, 20))
  org_id = str(random.randint(0, 20))
  cursor.execute("""
    INSERT INTO users
    (username,password,email,status_id,activation_code,org_id,bio,country_id,
      created,theme_id,activated,admin)
    VALUES ('""" + username + """','no password','donotsend',1,'',
      """ + org_id + """,
      'I am a test bot controlled by the contest staff. Just ignore me!',
      """ + country_id + """,CURRENT_TIMESTAMP,NULL,1,0)
  """)
cursor.close()
connection.close()

########NEW FILE########
__FILENAME__ = create_test_bot
#!/usr/bin/python
import os
import sys
import zipfile
import MySQLdb
from server_info import server_info
import argparse
import shutil

extension = { 'python': '.py',
              'java': '.java' }
support = { 'python': ['ants.py',
                       'logutils.py'],
            'java': ['Ants.java',
                     'Aim.java',
                     'Bot.java',
                     'Ilk.java',
                     'Tile.java'] }

# this path structure should match the php api code
# the worker code uses a different path structure
def submission_dir(submission_id):
    return os.path.join(server_info["uploads_path"],
                        str(submission_id//1000),
                        str(submission_id))
    
def create_starter_bot(name):
    name = name + "_starter_package"
    bot_zip_starter = os.path.join(server_info["repo_path"], "website", "starter_packages", name + ".zip")
    if not os.path.exists(bot_zip_starter):
        print("Starter package {0} not found.".format(bot_zip_starter))
        return False
    connection = MySQLdb.connect(host = server_info['db_host'],
                                 user = server_info['db_username'],
                                 passwd = server_info['db_password'],
                                 db = server_info['db_name'])
    cursor = connection.cursor(MySQLdb.cursors.DictCursor)
    
    # get next bot name number
    cursor.execute('''
    select username
    from user
    where username like '%s%%'
    ''' % name)
    bot_id = max([int(row['username'][len(name):])
                 for row in cursor.fetchall()] or [0]) + 1
    
    # create user database entry
    # password is test
    cursor.execute('''
    insert into user
    values (null,'%s%s','$6$rounds=54321$hQd}`.j1e#X&PuN*$D8.wbEp6vwwLoC27GpiGVOFediuAWaGTQ2MPHD64i/bVGxtj0XNeRJeJRKVgDC/uTh.W2m5YoaoA6To1cJ7ZF/',
    '%s%s@ai-contest.com',1,'7b3f9842775fa9c9d489a3714e857580',0,'Test Account',11,current_timestamp(),0,0);
    ''' % (name, bot_id, name, bot_id))
    user_id = cursor.lastrowid
    print('user_id: %s' % user_id)
    
    # create submission entry
    cursor.execute('''
    insert into submission (user_id, version, status, timestamp, language_id)  
    values (%s, 1, 20, current_timestamp(), 0)
    ''' % (user_id))
    submission_id = cursor.lastrowid
    print('submission_id: %s' % submission_id)
    
    connection.commit()
    connection.close()

    # create submission file
    bot_dir = submission_dir(submission_id)
    print(bot_dir)
    if os.path.exists(bot_dir):
        os.rmdir(bot_dir)
    os.makedirs(bot_dir)

    bot_zip_filename = os.path.join(bot_dir, 'entry.zip')
    shutil.copy2(bot_zip_starter, bot_zip_filename)
    
    return True
    
def create_test_bot(name, language):
    botpath = os.path.join(server_info["repo_path"],
                           'ants','dist','sample_bots',language)
    bot_filename = os.path.join(botpath, name + extension[language])
    if not os.path.exists(bot_filename):
        if not create_starter_bot(name):
            print('No {0} bot named {1}'.format(language, name))
            print(bot_filename)
            return False
        else:
            return True
    
    connection = MySQLdb.connect(host = server_info['db_host'],
                                 user = server_info['db_username'],
                                 passwd = server_info['db_password'],
                                 db = server_info['db_name'])
    cursor = connection.cursor(MySQLdb.cursors.DictCursor)
    
    # get next bot name number
    cursor.execute('''
    select username
    from user
    where username like '%s%%'
    ''' % name)
    bot_id = max([int(row['username'][len(name):])
                 for row in cursor.fetchall()] or [0]) + 1
    
    # create user database entry
    # password is test
    cursor.execute('''
    insert into user
    values (null,'%s%s','$6$rounds=54321$hQd}`.j1e#X&PuN*$D8.wbEp6vwwLoC27GpiGVOFediuAWaGTQ2MPHD64i/bVGxtj0XNeRJeJRKVgDC/uTh.W2m5YoaoA6To1cJ7ZF/',
    '%s%s@ai-contest.com',1,'7b3f9842775fa9c9d489a3714e857580',0,'Test Account',11,current_timestamp(),0,0);
    ''' % (name, bot_id, name, bot_id))
    user_id = cursor.lastrowid
    print('user_id: %s' % user_id)
    
    # create submission entry
    cursor.execute('''
    insert into submission (user_id, version, status, timestamp, language_id)  
    values (%s, 1, 20, current_timestamp(), 0)
    ''' % (user_id))
    submission_id = cursor.lastrowid
    print('submission_id: %s' % submission_id)
    
    connection.commit()
    connection.close()

    # create submission file
    bot_dir = submission_dir(submission_id)
    print(bot_dir)
    if os.path.exists(bot_dir):
        os.rmdir(bot_dir)
    os.makedirs(bot_dir)

    bot_zip_filename = os.path.join(bot_dir, 'entry.zip')
    with zipfile.ZipFile(bot_zip_filename, 'w') as bot_zip:
        bot_zip.write(bot_filename, 'MyBot' + extension[language])
        for filename in support[language]:
            support_filename = os.path.join(botpath, filename)
            if os.path.exists(support_filename):
                bot_zip.write(support_filename, filename)
            else:
                print('No support file {0}'.format(filename))
    
    return True

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('name')
    parser.add_argument('language', nargs='?', default='python')
    parser.add_argument('-c', '--count', type=int, default=1)
    #parser.add_argument('-u', '--user', type=str, default='contest')
    args = parser.parse_args()

    for i in range(args.count):
        if not create_test_bot(args.name, args.language):
            break
    
    # ensure correct dir permissions, www-data must be group for uploads
    os.system("chown -R www-data:www-data %s/*" % (server_info["uploads_path"]))
    os.system("find %s -type d -exec chmod 775 {} \;" % (server_info["uploads_path"]))
    os.system("find %s -type f -exec chmod 664 {} \;" % (server_info["uploads_path"]))

if __name__ == '__main__':
    main()
    

########NEW FILE########
__FILENAME__ = create_test_data
#!/usr/bin/env python
import os
import sys
import random
import MySQLdb

sys.path.append("../manager")
from server_info import server_info

def create_test_data(user_count=10000, map_count=1000, game_count=30000, matchup_count=10):
    connection = MySQLdb.connect(host = server_info["db_host"],
                                 user = server_info["db_username"],
                                 passwd = server_info["db_password"],
                                 db = server_info["db_name"])
    cursor = connection.cursor(MySQLdb.cursors.DictCursor)
    
    # create loads of users
    for i in range(user_count):
        cursor.execute("""
        insert into user
        values (null,'TestUser%s','$6$rounds=54321$hQd}`.j1e#X&PuN*$D8.wbEp6vwwLoC27GpiGVOFediuAWaGTQ2MPHD64i/bVGxtj0XNeRJeJRKVgDC/uTh.W2m5YoaoA6To1cJ7ZF/',
        'TestUser%s@ai-contest.com',1,'7b3f9842775fa9c9d489a3714e857580',0,'Test Account',11,current_timestamp(),0,0);
        """ % (i, i))
    connection.commit()        
    
    # create layers of old and new submissions
    user_max = int(user_count * 0.95) # ensure a few users don't have submissions
    version = 1
    while user_max > 1:
        cursor.execute("""
        insert into submission (user_id, version, status, timestamp, language_id, latest)
        select user_id, %s, 40, CURRENT_TIMESTAMP, 6, 0
        from user
        order by user_id
        limit %s;
        """ % (version, user_max))
        user_max = int(user_max * 0.6)
        version += 1
    connection.commit()
    
    # set last submission as latest
    cursor.execute("""
    update submission
    set latest = 0;
    """)
    connection.commit()
    cursor.execute("""
    update submission
    inner join (
        select s.user_id, MAX(s.submission_id) as submission_id
        from submission s
        group by s.user_id
    ) as sub_max on sub_max.submission_id = submission.submission_id
    set latest = 1;
    """)
    
    # get valid user and submission data
    connection.commit()
    submission_id = {}
    cursor.execute("""
    select user_id, submission_id
    from submission
    where latest = 1
    """)
    rows = cursor.fetchall()
    for row in rows[:-10]: # ensure a few users don't have games
        submission_id[row["user_id"]] = row["submission_id"]
        
    # create loads of maps
    for i in range(map_count):
        cursor.execute("""
        insert into map (filename, priority, players)
        values ('map%s', %s, %s);
        """ % (i, random.randrange(1,10), random.randrange(2,26)))
    connection.commit()
    map_pool = []
    cursor.execute("""
    select map_id
    from map
    """)
    for row in cursor.fetchall():
        map_pool.append(row["map_id"])
    
    # create loads of games
    for i in range(game_count):
        seed_id = random.choice(list(submission_id.keys()))
        map_id = random.choice(map_pool)
        cursor.execute("""
        insert into game (seed_id, map_id, timestamp, worker_id, replay_path)
        values (%s, %s, CURRENT_TIMESTAMP(), 1, '');
        """ % (seed_id, map_id))
        game_id = cursor.lastrowid
        cursor.execute("""
        select players from map where map_id = %s
        """ % map_id)
        player_count = cursor.fetchone()['players']
        user_ids = random.sample(list(submission_id.keys()), player_count)
        if not seed_id in user_ids:
            user_ids[random.randrange(0,player_count-1)] = seed_id
        for player_id in range(player_count):
            #print(user_ids[player_id])
            #print(submission_id[user_ids[player_id]])
            cursor.execute("""
            insert into game_player (game_id, user_id, submission_id, player_id, game_rank, game_score, sigma_before, mu_before)
            values (%s, %s, %s, %s, 1, 1, 50.0, 16.6667);
            """ % (game_id, user_ids[player_id], submission_id[user_ids[player_id]], player_id))
    connection.commit()

    # create a few matchups
    for i in range(matchup_count):
        seed_id = random.choice(list(submission_id.keys()))
        map_id = random.choice(map_pool)
        cursor.execute("""
        insert into matchup (seed_id, map_id, worker_id)
        values (%s, %s, 1);
        """ % (seed_id, map_id))
        matchup_id = cursor.lastrowid
        cursor.execute("""
        select players from map where map_id = %s
        """ % map_id)
        player_count = cursor.fetchone()['players']
        user_ids = random.sample(list(submission_id.keys()), player_count)
        if not seed_id in user_ids:
            user_ids[random.randrange(0,player_count-1)] = seed_id
        for player_id in range(player_count):
            cursor.execute("""
            insert into matchup_player (matchup_id, user_id, submission_id, player_id)
            values (%s, %s, %s, %s);
            """ % (matchup_id, user_ids[player_id], submission_id[user_ids[player_id]], player_id))
    connection.commit()

    # create small set of lurkers with no submission
    for i in range(user_count/10):
        cursor.execute("""
        insert into user
        values (null,'TestUser%s','$6$rounds=54321$hQd}`.j1e#X&PuN*$D8.wbEp6vwwLoC27GpiGVOFediuAWaGTQ2MPHD64i/bVGxtj0XNeRJeJRKVgDC/uTh.W2m5YoaoA6To1cJ7ZF/',
        'TestUser%s@ai-contest.com',1,'7b3f9842775fa9c9d489a3714e857580',0,'Test Account',11,current_timestamp(),0,0);
        """ % (i, i))
    connection.commit()        
        
if __name__ == '__main__':
    create_test_data()
########NEW FILE########
__FILENAME__ = create_test_submissions
#!/usr/bin/env python
import MySQLdb
import os
import random
from server_info import server_info
import sys

if len(sys.argv) != 2:
  print "USAGE: python create_test_submissions.py num_submissions"
  sys.exit(1)
n = int(sys.argv[1])
connection = MySQLdb.connect(host = server_info["db_host"],
                             user = server_info["db_username"],
                             passwd = server_info["db_password"],
                             db = server_info["db_name"])
cursor = connection.cursor(MySQLdb.cursors.DictCursor)
query = "SELECT user_id, username FROM users WHERE username LIKE 'testbot%'"
cursor.execute(query)
accounts = cursor.fetchall()
if len(accounts) == 0:
  print "ERROR: there are no test accounts in the database. You can " + \
    "create some using the create_test_accounts.py script."
  sys.exit(1);
for i in range(n):
  account = random.choice(accounts)
  cursor.execute("INSERT INTO submissions (user_id,status,timestamp," + \
    "language_id) VALUES (" + str(account["user_id"]) + ",20," + \
    "CURRENT_TIMESTAMP,3)")
  submission_id = connection.insert_id()
  path = "../submissions/" + str(submission_id) + "/"
  os.mkdir(path)
  os.chdir("entry")
  os.system("zip -r ../" + path + "entry.zip *.java > /dev/null 2> /dev/null")
  os.chdir("..")
cursor.close()
connection.close()

########NEW FILE########
__FILENAME__ = delete_test_accounts
#!/usr/bin/env python
import sys
import MySQLdb
from server_info import server_info

connection = MySQLdb.connect(host = server_info["db_host"],
                             user = server_info["db_username"],
                             passwd = server_info["db_password"],
                             db = server_info["db_name"])
cursor = connection.cursor(MySQLdb.cursors.DictCursor)
query = "SELECT user_id, username FROM users WHERE username LIKE 'testbot%'"
cursor.execute(query)
accounts = cursor.fetchall()
if len(accounts) > 0:
  submission_ids = ",".join([str(acc["user_id"]) for acc in accounts])
  query = "DELETE FROM submissions WHERE user_id IN (" + submission_ids + ")"
  cursor.execute(query)
  cursor.execute("DELETE FROM users WHERE username LIKE 'testbot%'")
cursor.close()
connection.close()

########NEW FILE########
__FILENAME__ = forkbomb
import os
import sys
max_num_processes = 0
for i in range(50):
  try:
    child_pid = os.fork()
  except:
    break
  if child_pid == 0:
#    max_num_processes = i + 1
  else:
    os.wait()
    sys.exit()
print "processes:", max_num_processes
#import os
#while True:
#  os.fork()

########NEW FILE########
__FILENAME__ = add_maps_to_database
#!/usr/bin/python

import os
import sys

import MySQLdb
from server_info import server_info
from sql import sql

def main():
    # get list of all map files
    maps_path = server_info["maps_path"]
    map_files = set()
    for root, dirs, files in os.walk(maps_path):
        for filepath in files:
            if filepath.endswith(".map"):
                map_files.add(os.path.join(root, filepath)[len(maps_path)+1:])
    
    # get list of maps in database
    connection = MySQLdb.connect(host = server_info["db_host"],
                                 user = server_info["db_username"],
                                 passwd = server_info["db_password"],
                                 db = server_info["db_name"])
    cursor = connection.cursor()
    cursor.execute(sql["select_map_filenames"])
    db_maps = set([row[0] for row in cursor.fetchall()])
    
    # get maps not in database
    new_maps = map_files.difference(db_maps)
    
    # add new maps to database with top priority
    if len(new_maps) > 0:
        cursor.execute(sql["update_map_priorities"])
        for mapfile in new_maps:
            players = 0
            with open(os.path.join(maps_path,mapfile), 'r') as f:
                for line in f:
                    if line.startswith('players'):
                        players = int(line.split()[1])
                        break
            if players:
                cursor.execute(sql["insert_map_filenames"], (mapfile, players))
            print(mapfile)
        connection.commit()
        print('{0} maps added to database'.format(len(new_maps)))
    else:
        print("No maps added, priorities not changed.")
    
if __name__ == "__main__":
    main()


########NEW FILE########
__FILENAME__ = adjust_turnlimits
#!/usr/bin/python

import argparse
import logging
import logging.handlers
import os
import sys
from os.path import basename, splitext

import MySQLdb
from server_info import server_info

# require this many games to be played before adjusting the turn limit
MIN_GAMES_PLAYED = 100

# percentage of games hitting the turn limit before increasing the limit
LOW_MARK_PER = 0.9

# percentage of games hitting the turn limit before decreasing the limit
HIGH_MARK_PER = 0.95

# when decreasing the limit set the new limit so it would include
# this percentage of games (should be between the high and low marks above)
DEC_PER = 0.925

# when increasing the limit increase by this multiple
INC_MULTIPLE = 1.2

# never increase the turn limit beyond this
HARD_LIMIT = 1500

log = logging.getLogger('turn_adjuster')
log.setLevel(logging.INFO)

formatter = logging.Formatter("%(asctime)s - " + str(os.getpid()) +
                              " - %(levelname)s - %(message)s")

log_file = os.path.join(server_info['logs_path'], 'turn_adjuster.log')
try:
    handler = logging.handlers.RotatingFileHandler(log_file,
                                                   maxBytes=1000000,
                                                   backupCount=5)
    handler.setLevel(logging.INFO)
    handler.setFormatter(formatter)
    log.addHandler(handler)
except IOError:
    # ignore errors about file permissions
    pass

handler2 = logging.StreamHandler(sys.stdout)
handler2.setLevel(logging.INFO)
handler2.setFormatter(formatter)
log.addHandler(handler2)


def main(dry_run):
    connection = MySQLdb.connect(host = server_info["db_host"],
                                     user = server_info["db_username"],
                                     passwd = server_info["db_password"],
                                     db = server_info["db_name"])
    cursor = connection.cursor()

    cursor.execute("""select map_id, filename, max_turns, timestamp from map
            where priority >= 0""")
    maplist = cursor.fetchall()
    for map_id, map_name, map_limit, last_adjusted in maplist:
        map_name = splitext(basename(map_name))[0]
        cursor.execute("""select game_length from game
            where map_id = '%s' and timestamp > '%s' and cutoff = 0"""
            % (map_id, last_adjusted))
        game_lengths = [n for (n,) in cursor.fetchall()]
        games_played = len(game_lengths)
        if games_played < MIN_GAMES_PLAYED:
            continue
        log.info("Checking map %d (%s) limit currently %d with %d games played"
                % (map_id, map_name, map_limit, games_played))
        game_lengths.sort()

        lowmark_ix = max(int(round(LOW_MARK_PER * games_played)) - 1, 0)
        highmark_ix = max(int(round(HIGH_MARK_PER * games_played)) - 1, 0)
        lowmark_len = game_lengths[lowmark_ix]
        highmark_len = game_lengths[highmark_ix]

        new_limit = None
        if lowmark_len == map_limit:
            new_limit = min(map_limit * INC_MULTIPLE, HARD_LIMIT)
        elif highmark_len < map_limit:
            new_limit = game_lengths[int(round(DEC_PER * games_played)) - 1]
        if new_limit:
            log.info("Adjusting map %d turn limit from %d to %d"
                    % (map_id, map_limit, new_limit))
            if not dry_run:
                cursor.execute("""update map
                    set max_turns = '%s', timestamp = NOW()
                    where map_id = '%s'""" % (new_limit, map_id))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--simulate", default=False, action="store_true",
            help="Don't store any adjustments back to the database")
    args = parser.parse_args()
    main(dry_run=args.simulate)


########NEW FILE########
__FILENAME__ = archive_games
#!/usr/bin/python

import logging
import logging.handlers
import os
import time
import sys

import MySQLdb
from server_info import server_info

logger = logging.getLogger('compile_logger')
logger.setLevel(logging.INFO)
_my_pid = os.getpid()
def log_message(message):
  logger.info(str(_my_pid) + ": " + message)
  print message

def main(max_games=10000):
    start_time = time.time()
    try:
        handler = logging.handlers.RotatingFileHandler("archive_games.log",
                                               maxBytes=1000000,
                                               backupCount=5)
        logger.addHandler(handler)
    except IOError:
       # couldn't start the file logger
       pass
    connection = MySQLdb.connect(host = server_info["db_host"],
                                     user = server_info["db_username"],
                                     passwd = server_info["db_password"],
                                     db = server_info["db_name"])
    cursor = connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("""INSERT INTO games_archive
        SELECT g.* FROM games g LEFT JOIN games_archive ga
            ON g.game_id = ga.game_id
            WHERE ga.game_id IS NULL
            LIMIT %d""" % (max_games,))
    copied = cursor.rowcount
    log_message("copied %d old games in %.2f seconds"
            % (copied, time.time()-start_time))
    if copied < max_games:
        time.sleep(1)
        del_start = time.time()
        max_games -= copied
        cursor.execute("""DELETE QUICK FROM games
                LIMIT %d""" % (max_games,))
        log_message("removed %d old games from primary table in %.2f seconds"
                % (cursor.rowcount, time.time() - del_start))
    log_message("total runtime %.2f seconds" % (time.time()-start_time,))

if __name__ == '__main__':
    if len(sys.argv) > 1:
        main(int(sys.argv[1]))
    else:
        main()


########NEW FILE########
__FILENAME__ = cutoff_adjuster
#!/usr/bin/python

import argparse
import time
from datetime import datetime, timedelta

import MySQLdb
from server_info import server_info

DEFAULT_BUFFER = 30
MAX_FILL = 100

def log(msg, *args):
    timestamp = time.asctime()
    msg = msg % args
    print "%s: %s" % (timestamp, msg)

def parse_time(time_str):
    return datetime.strptime(time_str, "%Y-%m-%d %H:%M")

INITIAL_INSERT = """insert into settings (name, number)
    values ("pairing_cutoff", %d)"""
CUTOFF_QUERY = """select number from settings where name = 'pairing_cutoff'"""
UPDATE_QUERY = """update settings set number = %d where name='pairing_cutoff'"""

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("cutoff", type=int,
            help="Target cutoff")
    time_opts = parser.add_mutually_exclusive_group()
    time_opts.add_argument("--minutes", "-m", type=int,
            help="Time to reach target cutoff, in minutes")
    time_opts.add_argument("--time", "-t", type=parse_time,
            help='Time to reach target cutoff, in "Year-Month-Day Hours:Minutes" format')
    parser.add_argument("--commit", "-c", action="store_true", default=False,
            help="Write changes to the database")
    args = parser.parse_args()

    start_time = datetime.now()
    if args.minutes:
        target_time = datetime.now() + timedelta(minutes=args.minutes)
    elif args.time:
        target_time = args.time
    else:
        target_time = datetime.now() + timedelta(hours=8)
    target_cutoff = args.cutoff
    log("Target cutoff is %d at %s" % (target_cutoff, target_time))

    connection = MySQLdb.connect(host = server_info["db_host"],
                                 user = server_info["db_username"],
                                 passwd = server_info["db_password"],
                                 db = server_info["db_name"])
    cursor = connection.cursor()

    cursor.execute(CUTOFF_QUERY)
    if cursor.rowcount > 0:
        initial_cutoff = cursor.fetchone()[0]
        log("Initial cutoff found as %d", initial_cutoff)
    else:
        cursor.execute("select max(rank) + 1 from submission where latest = 1")
        initial_cutoff = cursor.fetchone()[0]
        log("No cutoff found, effective starting cutoff %d", initial_cutoff)
        if args.commit:
            cursor.execute(INITIAL_INSERT % (initial_cutoff,))
            pass
    current_cutoff = initial_cutoff

    cutoff_diff = target_cutoff - initial_cutoff
    total_time = target_time - start_time
    total_time = total_time.total_seconds()
    log("Changing cutoff by %d in %d minutes", cutoff_diff, total_time / 60)
    while current_cutoff > target_cutoff:
        now = datetime.now()
        to_go = target_time - now
        to_go = to_go.total_seconds()
        log ("%.1f minutes left of %.1f", to_go / 60., total_time / 60.)
        if to_go > 0:
            time_completed = 1 - (to_go / total_time)
            next_cutoff = initial_cutoff + (cutoff_diff * time_completed)
        else:
            time_completed = 1.0
            next_cutoff = target_cutoff
        log("%.0f%% done, changing cutoff from %d to %d",
                time_completed * 100, current_cutoff, next_cutoff)
        if args.commit:
            cursor.execute(UPDATE_QUERY % (next_cutoff,))
        else:
            log("WARNING: Database not updated, -c option not given")
        time.sleep(30)
        cursor.execute(CUTOFF_QUERY)
        if cursor.rowcount > 0:
            current_cutoff = cursor.fetchone()[0]
        else:
            log("WARNING: No cutoff found in database")


if __name__ == "__main__":
    main()


########NEW FILE########
__FILENAME__ = ec2-check
#!/usr/bin/python

import httplib
import os
import sys
import time
from subprocess import Popen, PIPE

API_KEY = os.getenv("AI_QUERY_KEY")
STORE_FILE = "instance_data"

import json

def get_ec2_instances():
    data = {}
    api_proc = Popen("ec2-describe-instances", shell=True, stdout=PIPE)
    api_out, _ = api_proc.communicate()
    for line in api_out.splitlines():
        fields = line.split('\t')
        if fields[0] != 'INSTANCE' or fields[5] != 'running':
            continue
        data[fields[16]] = fields[1]
    return data

def get_old_data():
    try:
        dfile = open(STORE_FILE)
        data = json.load(dfile)
        dfile.close()
    except (IOError, ValueError):
        data = {}
    return data

def get_worker_game_data(ip):
    con = httplib.HTTPConnection("ai-contest.com")
    con.request("GET", "/api_worker_query.php?api_query_key=%s&ip=%s" % (
        API_KEY, ip))
    result = con.getresponse()
    body = result.read()
    try:
        data = json.loads(body)
    except ValueError:
        print "IP: %s\nresult body:" % (ip,)
        print body
        raise
    if data.has_key('error'):
        data = {'gpm': 0.0, 'epm': 0.0, 'id': None}
    else:
        data['gpm'] = float(data['gpm'])
        data['epm'] = float(data['epm'])
    return data

def reboot_instance(instance_id):
    os.system("ec2-reboot-instances %s" % (instance_id,))

def write_data(data):
    dfile = open(STORE_FILE, 'w')
    json.dump(data, dfile, sort_keys=True, indent=2)
    dfile.close()

old_store = get_old_data()
instances = get_ec2_instances()
new_store = {}
for worker in instances.keys():
    worker_data = get_worker_game_data(worker)
    if old_store.has_key(worker):
        worker_data['boot_time'] = old_store[worker]['boot_time']
    else:
        worker_data['boot_time'] = time.time()
    new_store[worker] = worker_data

min_age = time.time() - (60 * 30)
for worker in new_store.keys():
    worker_data = new_store[worker]
    if ((worker_data['boot_time'] < min_age and worker_data['gpm'] < 4) or
            (worker_data['gpm'] > 8 and
                worker_data['epm'] > worker_data['gpm'] * 0.8)):
        print "%s: Rebooting %s at %s as worker %s with %s gpm %s epm" % (
                time.asctime(), instances[worker], worker, worker_data['id'],
                worker_data['gpm'], worker_data['epm'])
        reboot_instance(instances[worker])
        worker_data['boot_time'] = time.time()

write_data(new_store)

########NEW FILE########
__FILENAME__ = gmail
import smtplib
from server_info import server_info

# Uses Gmail to send an email message. This function also work with Google Apps
# (Gmail for your domain) accounts.
#   username: the full email address of the sender (ex: sunflower@gmail.com).
#   password: the gmail password for the sender.
#   recipients: a list of addresses to send the message to. Can also be a
#               single email address.
#   subject: the subject line of the email
#   body: the actual content of the email
#   full_name: the full name of the sender. If this is omitted or has length
#              zero, then the name of the sender will just be the sender's
#              email address.
def send_gmail(username, password, recipients, subject, body, full_name):
  if isinstance(recipients, list):
    recipients = [r for r in recipients if r.find("@") >= 0]
  print recipients
  try:
    if full_name is not None and len(full_name) > 0:
      from_line = full_name + " <" + username + ">"
    else:
      from_line = username  
    message = "From: " + from_line + "\n" + \
      "Subject: " + subject + "\n" + \
      "\n" + body
    server_port = 25
    if server_info.has_key("mail_server_port"):
        server_port = server_info["mail_server_port"]
    smtp_server = smtplib.SMTP(server_info["mail_server"], server_port)
    smtp_server.ehlo()
    try:
        smtp_server.starttls()
        smtp_server.ehlo()
    except smtplib.SMTPException: # thrown if tls is not supported by server
        pass
    if password is not None:
        smtp_server.login(username, password)
    smtp_server.sendmail(username, recipients, message)
    smtp_server.quit()
    return True
  except Exception, inst:
    return False

# Sends an email message using the email account specified in the
# server_info.txt file. If the message is successfully sent, returns True.
# Otherwise, returns False.
def send(recipients, subject, body):
  mail_username = server_info["mail_username"]
  try:
      mail_password = server_info["mail_password"]
  except KeyError:
      mail_password = None
  mail_name = server_info["mail_name"]
  return send_gmail(mail_username, \
                    mail_password, \
                    recipients, \
                    subject, \
                    body, \
                    mail_name)

def main():
  print "result: " + \
    str(send("youraddress@yourdomain.com", "Test mail message", "Test!"))

if __name__ == "__main__":
  main()

########NEW FILE########
__FILENAME__ = manager
#!/usr/bin/env python
from __future__ import print_function

import argparse
import logging
import logging.handlers
import os
import os.path
import sys
import time
import traceback
from subprocess import Popen, PIPE

import MySQLdb
from server_info import server_info
from sql import sql

use_log = True

# Set up logging
log = logging.getLogger('manager')
log.setLevel(logging.INFO)

formatter = logging.Formatter("%(asctime)s - " + str(os.getpid()) +
                              " - %(levelname)s - %(message)s")

log_file = os.path.join(server_info['logs_path'], 'manager.log')
try:
    handler = logging.handlers.RotatingFileHandler(log_file,
                                                   maxBytes=1000000,
                                                   backupCount=5)
    handler.setLevel(logging.INFO)
    handler.setFormatter(formatter)
    log.addHandler(handler)
except IOError:
    # ignore errors about file permissions
    pass

handler2 = logging.StreamHandler()
handler2.setLevel(logging.INFO)
handler2.setFormatter(formatter)
log.addHandler(handler2)

class Player(object):
    def __init__(self, name, skill, rank):
        self.name = name
        self.old_skill = skill
        self.skill = skill
        self.rank = rank
    def __str__(self):
        return ('id=%5d rank=%1d, mu=%8.5f->%8.5f, sigma=%8.5f->%8.5f' %
                (self.name, self.rank, self.old_skill[0], self.skill[0], self.old_skill[1], self.skill[1]))

connection = None
def get_connection():
    global connection
    if connection == None:
        connection = MySQLdb.connect(host = server_info["db_host"],
                                     user = server_info["db_username"],
                                     passwd = server_info["db_password"],
                                     db = server_info["db_name"])
    return connection

def update_trueskill(game_id):
    log.info("Updating TrueSkill for game {0}".format(game_id))
    conn = get_connection()
    cursor = conn.cursor(MySQLdb.cursors.DictCursor)

    # get list of players and their mu/sigma values from the database
    players = []
    cursor.execute(sql['select_game_players'], game_id)
    results = cursor.fetchall()
    for row in results:
        player = Player(row['submission_id'], (row['mu'], row['sigma']), row['game_rank'])
        players.append(player)
        # check to ensure all rows have null _after values
        if row['mu_after'] != None:
            log.error("Game already has values!")
            return False
    if len(players) == 0:
        log.error("No players found for game %s" % (game_id,))
        return False

    classpath = "{0}/JSkills_0.9.0.jar:{0}".format(
            os.path.join(os.path.dirname(os.path.realpath(__file__)),
                "jskills"))
    tsupdater = Popen(["java", "-Xmx100m", "-cp", classpath, "TSUpdate"],
            stdin=PIPE, stdout=PIPE)
    for player in players:
        tsupdater.stdin.write("P %s %d %f %f\n" % (player.name, player.rank,
            player.skill[0], player.skill[1]))
    tsupdater.stdin.write("C\n")
    tsupdater.stdin.flush()
    tsupdater.wait()
    for player in players:
        # this might seem like a fragile way to handle the output of TSUpdate
        # but it is meant as a double check that we are getting good and
        # complete data back
        result = tsupdater.stdout.readline().split()
        if str(player.name) != result[0]:
            log.error("Unexpected player name in TSUpdate result. %s != %s"
                    % (player.name, result[0]))
            return False
        player.skill = (float(result[1]), float(result[2]))
    if tsupdater.stdout.read() != "":
        log.error("Received extra data back from TSUpdate")
        return False

    for player in players:
        log.debug(player)
        cursor.execute(sql['update_game_player_trueskill'],
                (player.old_skill[0], player.old_skill[1],
                    player.skill[0], player.skill[1], game_id, player.name))
    conn.commit()
    cursor.execute(sql['update_submission_trueskill'], game_id)
    conn.commit()
    cursor.execute('call update_rankings(%s)' % game_id);
    conn.commit()
    return True

def update_leaderboard(wait_time):
    conn = get_connection()
    cursor = conn.cursor(MySQLdb.cursors.DictCursor)
    while True:
        try:
            if use_log:
                log.info("Updating leaderboard and adding some sigma")
            cursor.execute("call generate_leaderboard;")
            if wait_time == 0:
                break
            for s in range(wait_time):
                # allow for a [Ctrl]+C during the sleep cycle
                time.sleep(1)
        except KeyboardInterrupt:
            break
        except:
            # log error
            log.error(traceback.format_exc())
            break
    cursor.close()
    conn.close()

def reset_submissions(status):
    log.info("Resetting all latest submissions to status {0}".format(status))
    conn = get_connection()
    cursor = conn.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('update submission set status = 20 where latest = 1')
    conn.commit()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-g", "--game_id", type=int,
                        help="game_id to update")
    parser.add_argument("-l", "--leaderboard", type=int, default=None,
                        help="produce a new leaderboard every X seconds")
    parser.add_argument('-r', '--reset', type=int,
                        help="reset submissions to status")
    parser.add_argument('--debug', default=False,
                        action='store_true',
                        help="Set the log level to debug")
    args = parser.parse_args()

    if args.debug:
        log.setLevel(logging.DEBUG)

    if args.game_id:
        if update_trueskill(args.game_id):
            sys.exit(0)
        else:
            sys.exit(-1)
    elif args.leaderboard != None:
        update_leaderboard(args.leaderboard)
    elif args.reset:
        reset_submissions(args.reset)
    else:
        parser.print_usage()

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = map_analyzer
#!/usr/bin/env python

from collections import deque, defaultdict
import sys

#returns the new location after moving in a particular direction
directions = {'N': (-1,0), 'S': (1,0), 'E': (0,1), 'W': (0,-1)}
def get_loc(loc, direction, rows, cols):                                    
    dr, dc = directions[direction]                              
    return [(loc[0]+dr)%rows, (loc[1]+dc)%cols ]

def analyze_map(map_location):
    #variables
    rows = cols = no_players = 0
    map_data = []
    players = []

    given_no_players = -1
    player_line_given = False

    no_land_squares = no_water_squares = no_food_squares = 0

    #reads the data from the map file
    map_file = open(map_location, 'r')
    for line in map_file.readlines():
        tokens = line.split()
        
        if tokens[0] == "rows":
            rows = int(tokens[1])
        elif tokens[0] == "cols":
            cols = int(tokens[1])
        elif tokens[0] == "players":
            player_line_given = True
            given_no_players = int(tokens[1])
        elif tokens[0] == "m":
            map_data.append(tokens[1])
    map_file.close()

    #checks to see that the map is of the correct dimensions
    if len(map_data) != rows:
        raise ValueError("incorrect number of rows given")
    for row in range(len(map_data)):
        if len(map_data[row]) != cols:
            raise ValueError("incorrect number of columns in row " + str(row))
            
    #gets information about the map
    for row in range(len(map_data)):
        for col in range(len(map_data[row])):
            if map_data[row][col] == '.':
                no_land_squares += 1
            elif map_data[row][col] == '%':
                no_water_squares += 1
            elif map_data[row][col] == '*':
                no_food_squares += 1
            elif map_data[row][col] >= 'a' and map_data[row][col] <= 'z':
                if not map_data[row][col] in players:
                    players.append(map_data[row][col])
                    no_players += 1
            else:
                raise ValueError("incorrect square value given")

    #checks the correct number of players were given
    if player_line_given and no_players != given_no_players:
        raise ValueError("wrong number of players specified")
        
    #checks the correct players were given
    players.sort()
    expected = 'a'
    for player in players:
        if player != expected:
            raise ValueError("player " + str(expected) + " not given")
        expected = chr(ord(expected)+1)	

    #finds information about where players are
    ant_counts = defaultdict(int)
    access_map = [ [ [-1, [] ] for c in range(cols)] for r in range(rows) ]
    square_queue = deque([])

    for row in range(len(map_data)):
        for col in range(len(map_data[row])):
            if map_data[row][col] >= 'a' and map_data[row][col] <= 'z':
                p = ord(map_data[row][col])-97
                ant_counts[p] += 1
                access_map[row][col] = [0, [p], [ [row, col] ] ]
                square_queue.append( [row, col] )


    #finds information about who can reach what land and food squares first	
    while len(square_queue) > 0:
        c_loc = square_queue.popleft()
        c_players = access_map[c_loc[0] ][c_loc[1] ][1]
        
        for d in directions:
            n_loc = get_loc(c_loc, d, rows, cols)
            
            if map_data[n_loc[0] ][n_loc[1] ] != '%':
                if access_map[n_loc[0] ][n_loc[1] ][0] == -1: #first time reached
                    access_map[n_loc[0]][n_loc[1]][0] = access_map[c_loc[0]][c_loc[1]][0] + 1
                    access_map[n_loc[0] ][n_loc[1] ][1] += c_players
                    square_queue.append(n_loc)
                elif access_map[n_loc[0]][n_loc[1]][0] == access_map[c_loc[0]][c_loc[1]][0] + 1:
                    for p in c_players:
                        if not p in access_map[n_loc[0]][n_loc[1]][1]:
                            access_map[n_loc[0] ][n_loc[1] ][1].append(p)
                    access_map[n_loc[0]][n_loc[1]][1].sort()
            
    #works out access counts
    land_access_counts = defaultdict(int)

    for row in access_map:
        for cell in row:
            t = cell[1]
            if len(t) >= 1:
                land_access_counts[tuple(t)] += 1

    #build dictionary of information
    result = {'players': no_players,
        'rows': rows,
        'cols': cols,
        'counts': ant_counts,
        'space': land_access_counts
    }
    sys.stdout.write("# " + str(result) + "\n")

    #outputs the partitioned map_data
    sys.stdout.write("players " + str(no_players) + "\n")                        
    sys.stdout.write("rows " + str(rows) + "\n")                        
    sys.stdout.write("cols " + str(cols) + "\n")                        
    for row in range(len(access_map)):
        sys.stdout.write("m ")
        for col in range(len(access_map[row])):
            if map_data[row][col] == '%':
                sys.stdout.write('%')
            elif len(access_map[row][col][1]) == 1:
                sys.stdout.write( chr(int(access_map[row][col][1][0]) + 97))
            else:
                #sys.stdout.write(str( len(access_map[row][col][1])))
                sys.stdout.write(".")
        sys.stdout.write('\n')

    
    return result

if __name__ == '__main__':
    analyze_map(sys.argv[1])

########NEW FILE########
__FILENAME__ = mass_skill_update
#!/usr/bin/python
# Query the database for all games without player trueskill updates done and
# attempt to fill them in
import manager
import MySQLdb

_unfilled_game_query = """
select game_id from game_player where mu_after is null
    group by game_id;
"""

def main():
    connection = manager.get_connection()
    cursor = connection.cursor(MySQLdb.cursors.DictCursor)

    cursor.execute(_unfilled_game_query)
    results = cursor.fetchall()
    for row in results:
        manager.update_trueskill(row['game_id'])

if __name__ == "__main__":
    main()


########NEW FILE########
__FILENAME__ = matchup_buffer
#!/usr/bin/python

import time

import MySQLdb
from server_info import server_info

DEFAULT_BUFFER = 50
MAX_FILL = 60

def log(msg):
    timestamp = time.asctime()
    print "%s: %s" % (timestamp, msg)

def main():
    connection = MySQLdb.connect(host = server_info["db_host"],
                                 user = server_info["db_username"],
                                 passwd = server_info["db_password"],
                                 db = server_info["db_name"])
    cursor = connection.cursor()

    buf_size = DEFAULT_BUFFER
    log("Buffer size set to %d" % (buf_size,))

    fill_size = buf_size
    full = False
    while True:
        cursor.execute("select count(*) from matchup where worker_id is NULL")
        cur_buffer = cursor.fetchone()[0]
        if cur_buffer >= buf_size:
            log("Buffer full with %d matches in buffer" % (cur_buffer,))
            time.sleep(10)
            if full:
                fill_size = max(buf_size, fill_size * 0.9)
            full = True
        else:
            if not full:
                fill_size = min(MAX_FILL, fill_size * 1.5)
            full = False
            add = int(fill_size) - cur_buffer
            if cur_buffer == 0:
                log("WARNING: Found empty buffer")
            log("Adding %d matches to buffer already having %d" % (
                add, cur_buffer))
            for i in range(add):
                cursor.execute("call generate_matchup")
                cursor.nextset()

if __name__ == "__main__":
    main()


########NEW FILE########
__FILENAME__ = random_pairing
#!/usr/bin/python

import sys
import time
import random

import MySQLdb
import MySQLdb.cursors

from server_info import server_info

def log(msg):
    timestamp = time.asctime()
    print "%s: %s" % (timestamp, msg)

class Matchup:
    def __init__(self, game_map):
        self.map = game_map
        self.players = []

    def commit(self, cursor):
        log("Match on map %s" % (self.map["filename"],))
        log("with players: %s" % ([p["user_id"] for p in self.players],))
        cursor.execute("""insert matchup (seed_id, worker_id, map_id, max_turns)
                values (%s, 0, %s, %s)""",
                (self.players[0]["user_id"], self.map["map_id"],
                    self.map["max_turns"])
                )
        matchup_id = cursor.lastrowid
        for num, player in enumerate(self.players):
            cursor.execute("""insert matchup_player
                (matchup_id, user_id, submission_id, player_id, mu, sigma)
                values (%s, %s, %s, %s, %s, %s)""",
                (matchup_id, player["user_id"], player["submission_id"], num,
                    player["mu"], player["sigma"])
                )
        cursor.execute("""update matchup set worker_id = null
                where matchup_id = %s""", (matchup_id,))
        log("inserted as match %d" %(matchup_id,))


def main(rounds = 1):
    connection = MySQLdb.connect(host = server_info["db_host"],
                                 user = server_info["db_username"],
                                 passwd = server_info["db_password"],
                                 db = server_info["db_name"],
                                 cursorclass = MySQLdb.cursors.DictCursor)
    cursor = connection.cursor()

    cursor.execute("select * from map where priority > 0")
    maps = cursor.fetchall()

    cursor.execute("select * from submission where latest = 1")
    players = list(cursor.fetchall())
    random.shuffle(players)

    cur_round = 1
    map_ix = 0
    player_ix = 0
    pairings = 0
    while cur_round <= rounds:
        match = Matchup(maps[map_ix])
        map_ix = (map_ix + 1) % len(maps)
        for player_num in range(match.map["players"]):
            next_player = players[player_ix]
            while next_player in match.players:
                # Should only happen when a game wraps around the end of the 
                # player list
                assert player_ix < player_num, "Duplicate player later in list"
                rnd_ix = random.randint(player_ix + 1, len(players) - 1)
                players[player_ix], players[rnd_ix] = players[rnd_ix], players[player_ix]
                next_player = players[player_ix]
            match.players.append(next_player)
            player_ix = (player_ix + 1) % len(players)
            if player_ix == 0:
                cur_round += 1
                random.shuffle(players)
        match.commit(cursor)
        pairings += 1

    log("Paired %d rounds with %d matches" % (rounds, pairings))


if __name__ == "__main__":
    rounds = 1
    if len(sys.argv) > 1:
        rounds = int(sys.argv[1])
    main(rounds)


########NEW FILE########
__FILENAME__ = sql
# this file gathers all sql into one place for ease of changing the database
sql = {
    # used in worker_ssh
    "select_workers" : "select worker_id, ip_address from worker order by worker_id desc",
    
    # used in add_maps_to_database.py
    "select_map_filenames": "select filename from map",
    "update_map_priorities": """
        update map set priority = priority + 1
            where priority >= 0
        """,
    "insert_map_filenames": "insert into map (filename, players, max_turns, timestamp) values (%s, %s, 1000, current_timestamp)",

    # used in delete_some_old_submissions.py
    "select_latest_submissions": "select submission_id from submission where latest = 1",
    
    # used in manager.py
    "select_game_players": "select gp.submission_id, gp.game_rank, s.mu, s.sigma, gp.mu_after from game_player gp inner join submission s on s.submission_id = gp.submission_id where gp.game_id = %s",

    "update_game_player_trueskill": """
        update game_player
        set mu_before = %s,
            sigma_before = %s,
            mu_after = %s,
            sigma_after = %s
        where game_id = %s and
              submission_id = %s""",

    "update_submission_trueskill": """
        update submission s
        inner join game_player gp
            on s.submission_id = gp.submission_id
        set s.mu = gp.mu_after,
            s.mu_change = gp.mu_after - gp.mu_before,
            s.sigma = gp.sigma_after,
            s.sigma_change = gp.sigma_after - gp.sigma_before
        where game_id = %s;"""
}

########NEW FILE########
__FILENAME__ = submission_hash
#!/usr/bin/python

import os
import sys
from hashlib import sha1
from subprocess import Popen, PIPE

SUB_PATH = "/home/contest/ai-contest/planet_wars/submissions"

EXT_EXCLUDES = frozenset(['.zip', '.tgz'])
NAME_EXCLUDES = frozenset(['PlayGame.jar', 'ShowGame.jar', '.DS_Store', 'Icon'])

def collect_filenames(path):
    filenames = []
    for root, dirs, files in os.walk(path):
        for name in files:
            if name in NAME_EXCLUDES:
                continue
            ext = name.rfind('.')
            if name[ext:] in EXT_EXCLUDES:
                continue
            filenames.append(os.path.join(root, name))
    return filenames

# suprisingly in testing this is slower than doing the file hash in python
# this hash value will include the full absolute path to the file
def hash_file_md5sum(filename):
    proc = Popen(["md5sum", filename], stdout=PIPE)
    fhash, _ = proc.communicate()
    if proc.returncode != 0:
        raise OSError("md5sum had an error while hashing %s" % (filename,))
    return fhash

def hash_file_sha(filename):
    READ_SIZE = 4096 * 2500
    fhash = sha1()
    #fhash.update(os.path.basename(filename))
    f = open(filename, 'rb')
    content = f.read(READ_SIZE)
    while len(content) != 0:
        fhash.update(content)
        content = f.read(READ_SIZE)
    return fhash.hexdigest()

# this was only around 20-25% faster than the full hash
def hash_file_size(filename):
    fhash = sha1()
    fhash.update(os.path.basename(filename))
    fhash.update(str(os.path.getsize(filename)))
    return fhash.digest()

def hash_file(filename):
    return hash_file_sha(filename)

def hash_submission(submission_dir):
    sub_files = collect_filenames(submission_dir)
    sub_files.sort()
    sub_hash = sha1()
    for name in sub_files:
        sub_hash.update(hash_file(name))
    return sub_hash.hexdigest()

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print "usage: submission_hash.py <submission_file>"
        sys.exit(1)
    if os.path.exists(sys.argv[1]):
        sys.stdout.write(hash_file_sha(sys.argv[1]))


########NEW FILE########
__FILENAME__ = test_trueskill
#!/usr/bin/env python
from trueskill import trueskill

class Player(object):
    def __init__(self, name, skill, rank):
        self.name = name
        self.old_skill = skill
        self.skill = skill
        self.rank = rank
    def __str__(self):
        return ('id=%5d rank=%1d\n\t   mu=%8.5f->%8.5f,\n\tsigma=%8.5f->%8.5f' %
                (self.name, self.rank, self.old_skill[0], self.skill[0], self.old_skill[1], self.skill[1]))

def test_trueskill():
    # get list of players and their mu/sigma values from the database
    players = [Player(0, (41.0538, 1.6888), 1),
               Player(1, (31.6869, 1.70811), 2),
               Player(2, (28.0252, 1.74717), 2),
               Player(3, (27.0053, 1.83862), 2)]
    
    trueskill.AdjustPlayers(players)

    print('\nAfter:')
    for player in players:
        print(player)

if __name__ == '__main__':
    test_trueskill()
########NEW FILE########
__FILENAME__ = worker_ssh
#!/usr/bin/python

import os
import sys
import subprocess
import re
import threading
import logging

import MySQLdb
from server_info import server_info
from sql import sql

ALIVE_WORKERS_CACHE="/tmp/aliveworkers"
WORKER_KEY="~/workerkey"
SSH_COMMAND="ssh -i %s -l ubuntu %%s" % WORKER_KEY

logging.basicConfig(level=logging.INFO, format="~~worker_ssh~~(%(levelname)s): %(message)s")

DEVNULL=open("/dev/null","w")

def get_workers():
    """get the list of workers, last $limit workers"""
    connection = MySQLdb.connect(host = server_info["db_host"],
                                 user = server_info["db_username"],
                                 passwd = server_info["db_password"],
                                 db = server_info["db_name"])
    cursor = connection.cursor()
    cursor.execute(sql["select_workers"])
    return cursor.fetchall()

def ping(worker,count=4):
    """Pings and returns false if 100% packet loss"""
    ip=worker[1]
    
    ping = subprocess.Popen(
        ["ping", "-c", str(count), str(ip)],
        stdout = subprocess.PIPE,
        stderr = subprocess.PIPE
    )
    
    out, error = ping.communicate()
    
    #if anything is wrong stdout will be blank, therefore failure
    if len(out)==0:
        return False
    
    #search for packet loss and return the percentage
    return int(re.search("(\d*)\% packet loss",out).group(1))!=100

def tcpping(worker):
    """Opens a socket to the ssh port, tests if successful. Returns false on timeout(2.0s), connection refused, unknown hostname or no route to host."""
    import socket
    
    try:
        logging.debug("Getting ip of %r" % (worker,))
        ip=socket.gethostbyname(worker[1])
        logging.debug("IP of %r retrieved as %s!" % (worker,ip))
        
        logging.debug("Creating a new socket and connecting to %r..." % (worker,))
        s = socket.create_connection((ip, 22),2.0)
        logging.debug("Connected to %r!" % (worker,))
        
        logging.debug("Closing connection to %r." % (worker,))
        s.close()
    except socket.error as e:
        logging.debug("%r has a socket.error(%s)" % (worker,e))
        return False
    except socket.gaierror as e:
        logging.debug("%r has a socket.gaierror(%s)" % (worker,e))
        return False
    return True

def sshping(worker):
    """Tries to connect via ssh to host, returns true only if publickey was accepted(false if a ssh server was found but asked for password)."""
    host=worker[1]
    command=(SSH_COMMAND + " -oBatchMode=yes -oStrictHostKeyChecking=no -oConnectTimeout=5 -oUserKnownHostsFile=/dev/null exit") % host
    status = subprocess.call(command, shell=True, stdout=DEVNULL, stderr=DEVNULL)
    return status==0

def aliveworkers(workers):
    """returns a list of workers that are alive, packetloss<100"""
    
    #ping everyone using threads
    threads=[]
    results={}
    output=threading.Lock()
    
    def threadcode(worker):
        worker=worker[:]
        logging.info("Pinging %r" % (worker,))
        results[worker]=sshping(worker)
        logging.info("Worker %r is %s." % (worker, ["down","up"][results[worker]]))
    
    
    try:
        for i,worker in enumerate(workers):
            threads.append(threading.Thread())
            threads[i].run=lambda: threadcode(worker)
            threads[i].start()
            threads[i].join(0.1)
        
        #wait for threads to finish
        for thread in threads:
            thread.join()
    except KeyboardInterrupt:
        logging.info("KeyboardInterrupt! Saving alive workers cache.")
        pass
    
    aliveworkers=[worker for worker,result in results.items() if result==True]
    return aliveworkers

def loadaliveworkers(filename=ALIVE_WORKERS_CACHE):
    try:
        return dict(eval(open(filename).read()))
    except :
        logging.warning("%s not found, assuming blank list. Try reloading the alive worker list." % (filename,))
        return {}

def ssh(host):
    logging.info("Connecting to %s:" % (host,))
    host=host[1]
    subprocess.call(SSH_COMMAND % host, shell=True)

if __name__ == "__main__":
    import getopt
    
    optlist, hostids = getopt.getopt(sys.argv[1:], '::ral')
    optlist=dict(optlist)
    
    if "-r" in optlist.keys():
        #regenerate alive worker list
        logging.info("Regenerating alive worker list.")
        workers=get_workers()
        logging.info("Worker list from the database: %s" % (workers,))
        workers=aliveworkers(workers)
        open(ALIVE_WORKERS_CACHE,"w").write(repr(workers))
    
    if "-l" in optlist.keys():
        #list
        workers=loadaliveworkers()
        print "Workers that are online(%s):" % len(workers)
        for worker in sorted(workers.items()):
            print "\t%d - %s" % (worker)
        if len(workers)==0:
            print "\tAll workers are offline."
    
    if "-a" in optlist.keys():
        #put all hosts in hostsids
        hostids=loadaliveworkers().keys()
        
    if len(hostids)>0 or "-a" in optlist.keys():
        #ssh in all hostids
        allworkers=loadaliveworkers()
        
        hosts=[]
        for hostid in hostids:
            try:
                host=(int(hostid),allworkers[int(hostid)])
            except KeyError as e:
                raise Exception("Worker %s not found. Try reloading the alive worker list. Alive workers: %r" % (e.args[0], allworkers))
            except ValueError:
                #interpret hostid as an ip
                host=(hostid, hostid)
                for workerid,workerhostname in allworkers.items():
                    if hostid==workerhostname:
                        host=(workerid,workerhostname)
            hosts.append(host)
        
        logging.info("Will connect to %s" % hosts)
        
        for host in hosts:
            ssh(host)
    
    if "-h" in optlist.keys() or (len(optlist)==0 and len(hostids)==0):
        #show help
        print "worker_ssh.py [-r] [-l] [-a] [worker_id list] [ip list]"
        print
        print "-r to generate a new alive worker list in %s" % ALIVE_WORKERS_CACHE
        print "-l prints the alive worker list"
        print "-a connects to all workers sequentially"
        print "If worker_ids are given it will load the active worker list and connect to them."
        print "If ips are given it will just connect to them."

########NEW FILE########
__FILENAME__ = create_worker_archive
#!/usr/bin/python

import os.path
import sys

from install_tools import CD, run_cmd

ARCHIVE_CMD = "git archive --format=tar --prefix=aichallenge/ HEAD | gzip > "

def main(output_directory):
    repo_root = run_cmd("git rev-parse --show-toplevel", True).strip()
    output_directory = os.path.abspath(output_directory)
    with CD(repo_root):
        run_cmd(ARCHIVE_CMD + os.path.join(output_directory, "worker-src.tgz"))

if __name__ == "__main__":
    out_dir = "."
    if len(sys.argv) > 1:
        out_dir = sys.argv[1]
    main(out_dir)


########NEW FILE########
__FILENAME__ = install_tools
import getpass
import os
import re
from subprocess import Popen, PIPE

class Environ(object):
    """ Context manager that sets and restores an environment variable """
    def __init__(self, var, value):
        self.env_var = var
        self.new_value = value

    def __enter__(self):
        self.start_value = os.environ.get(self.env_var, None)
        os.environ[self.env_var] = self.new_value
        return self.new_value

    def __exit__(self, type, value, traceback):
        if self.start_value is not None:
            os.environ[self.env_var] = self.start_value
        else:
            del os.environ[self.env_var]

class CD(object):
    """ Context manager to change and restore the current working directory """
    def __init__(self, new_dir):
        self.new_dir = new_dir

    def __enter__(self):
        self.org_dir = os.getcwd()
        os.chdir(self.new_dir)
        return self.new_dir

    def __exit__(self, type, value, traceback):
        os.chdir(self.org_dir)

def file_contains(filename, line_pattern):
    """ Checks if a file has a line matching the given pattern """
    if not os.path.exists(filename):
        return False
    regex = re.compile(line_pattern)
    with open(filename, 'r') as src:
        for line in src:
            if regex.search(line):
                return True
    return False

def append_line(filename, line):
    """ Appends a line to a file """
    with open(filename, "a+") as afile:
        afile.write(line + '\n')

class CmdError(StandardError):
    """ Exception raised on an error return code results from run_cmd """
    def __init__(self, cmd, returncode):
        self.cmd = cmd
        self.returncode = returncode
        StandardError.__init__(self, "Error %s returned from %s"
            % (returncode, cmd))

def run_cmd(cmd, capture_stdout=False):
    """ Run a command in a shell """
    print "Executing:", cmd
    stdout_loc = PIPE if capture_stdout else None
    proc = Popen(cmd, shell=True, stdout=stdout_loc)
    output, error_out = proc.communicate()
    status = proc.wait()
    if status != 0:
        raise CmdError(cmd, status)
    return output

def install_apt_packages(packages):
    """ Install system packages using aptitude """
    apt_cmd = "apt-get install -y "
    try:
        cmd = apt_cmd + packages
    except TypeError:
        cmd = apt_cmd + " ".join(packages)
    run_cmd(cmd)

def get_choice(query, default=False):
    negative_responses = ["no", "n"]
    positive_responses = ["yes", "y"]
    query += " [%s] " % ('yes' if default else 'no')
    while True:
        resp = raw_input(query).lower().strip()
        if resp in negative_responses or (resp == "" and not default):
            return False
        if resp in positive_responses or (resp == "" and default):
            return True

def get_password(pw_name):
    while True:
        passwd = getpass.getpass("%s password? " % (pw_name.capitalize()))
        confirm = getpass.getpass("Confirm %s password? " % (pw_name,))
        if passwd == confirm:
            return passwd
        print "Sorry, passwords did not match."

def get_ubuntu_release_info():
    version="notubuntu"
    arch="unknown"
    try:
        version=re.match(".*DISTRIB_CODENAME=(\w*).*",open("/etc/lsb-release").read(),re.DOTALL).group(1)
        arch=run_cmd("dpkg --print-architecture",True).strip()
    except CmdError, IOError:
        arch=run_cmd("uname -p",True).strip()
    except:
        pass
    
    return version, arch

def check_ubuntu_version():
    version,arch=get_ubuntu_release_info()
    if version!="notubuntu":
        print "Install tools on Ubuntu version:%s arch:%s." % (version, arch)
    else:
        print "Installing on an %s non-Ubuntu host." % (arch)
    
    if version!="natty":
        raise Exception("This contest framework was designed to work on Ubuntu Natty(11.04) only.")
    
    return version, arch

########NEW FILE########
__FILENAME__ = retrieve_languages
#!/usr/bin/python
# Download third party language packages to the directory specified

import os.path
import sys
import urllib2
import urlparse

from install_tools import CD, run_cmd, CmdError

sources = [
    ("http://repo1.maven.org/maven2/org/clojure/clojure/1.3.0/clojure-1.3.0.zip",
        "clojure.zip"),
    ("https://github.com/jashkenas/coffee-script/tarball/1.1.2",
        "coffeescript.tgz"),
    ("http://ftp.digitalmars.com/dmd_2.054-0_amd64.deb",
        "dmd.deb"),
    ("https://github.com/downloads/aichallenge/aichallenge/golang_60.1-9753~natty1_amd64.deb",
        "golang.deb"),
    ("http://dist.groovy.codehaus.org/distributions/installers/deb/groovy_1.7.8-1_all.deb",
        "groovy.deb"),
    ("https://github.com/downloads/aichallenge/aichallenge/nodejs_0.4.10~natty1~ppa201107202043_amd64.deb",
        "nodejs.deb"),
    ("http://download.racket-lang.org/installers/5.2/racket/racket-5.2-bin-x86_64-linux-debian-lenny.sh", 
        "racket.sh"),
    ("http://www.scala-lang.org/downloads/distrib/files/scala-2.9.0.1.tgz",
        "scala.tgz"),
    ("https://github.com/downloads/aichallenge/aichallenge/dart-frogsh-r1499.tgz", "dart.tgz"),
    ("https://bitbucket.org/pypy/pypy/downloads/pypy-1.7-linux64.tar.bz2", "pypy.tar.bz2"),
]

if len(sys.argv) < 2:
    print "usage: %s <destination directory>"
    sys.exit()

out_dir = os.path.abspath(sys.argv[1])
if not os.path.isdir(out_dir):
    print "Destination directory does not exist"
    sys.exit(1)

with CD(out_dir):
    print "Downloading files to %s" % (out_dir,)
    for url, filename in sources:
        try:
            run_cmd("wget -U NewName/1.0 '%s' -O %s" % (url, filename))
        except CmdError, exc:
            print >>sys.stderr, str(exc)

########NEW FILE########
__FILENAME__ = md
#!/usr/bin/env python
import sys
import markdown
md = markdown.Markdown(
        extensions=['extra',
                    'codehilite',
                    'toc',
                    'wikilinks',
                    'latex',
                    'github']
     )
mdfile = open(sys.argv[1], 'r')
mdtext = mdfile.read()
mdfile.close()
sys.stdout.write(md.convert(mdtext))
sys.stdout.write('\n');

########NEW FILE########
__FILENAME__ = mdx_github
import markdown
import re

START_FENCE = re.compile('^```(.*)')
END_FENCE = re.compile('^```$')

class GithubPreprocessor(markdown.preprocessors.Preprocessor):
    def run(self, lines):
        # replace github fenced code blocks with python markdown ones
        new_lines = []
        fenced = False
        for line in lines:
            if fenced:
                if END_FENCE.match(line):
                    new_lines.append('')
                    fenced = False
                else:
                    new_lines.append('    '+line)
            else:
                fence = START_FENCE.match(line)
                if fence:
                    fenced = True
                    new_lines.append('')
                    if fence.group(1):
                        new_lines.append('    :::' + fence.group(1))
                else:
                    new_lines.append(line)
        return new_lines

class MarkdownGithub(markdown.Extension):
    def extendMarkdown(self, md, md_globals):
        md.preprocessors.add('github',
                GithubPreprocessor(self), "_begin")

def makeExtension(configs=None):
    return MarkdownGithub(configs=configs)

########NEW FILE########
__FILENAME__ = mdx_latex
"""
Copyright (c) 2011 Justin Bruce Van Horne

Python-Markdown LaTeX Extension
===============================

Adds support for $math mode$ and %text mode%. This plugin supports
multiline equations/text.

The actual image generation is done via LaTeX/DVI output.
It encodes data as base64 so there is no need for images directly.
All the work is done in the preprocessor.
"""

import re
import os
import string
import base64
import tempfile
import markdown


from subprocess import call, PIPE


# %TEXT% mode which is the default LaTeX mode.
TEX_MODE = re.compile(r'(?=(?<!\\)\\\[).(.+?)(?<!\\)\\\]',
        re.MULTILINE | re.DOTALL)

# $MATH$ mode which is the typical LaTeX math mode.
MATH_MODE = re.compile(r'(?=(?<!\\)\$).(.+?)(?<!\\)\$',
        re.MULTILINE)

# %%PREAMBLE%% text that modifys the LaTeX preamble for the document
PREAMBLE_MODE = re.compile(r'(?=(?<!\\)\$\$\$).(.+?)(?<!\\)\$\$\$',
        re.MULTILINE | re.DOTALL)

# Defines our basic inline image
IMG_EXPR = "<img class='latex-inline math-%s' alt='%s' id='%s'" + \
        " src='data:image/png;base64,%s'>"


# Base CSS template
IMG_CSS = "<style>img.latex-inline { vertical-align: middle; }</style>\n"


class LaTeXPreprocessor(markdown.preprocessors.Preprocessor):
    # These are our cached expressions that are stored in latex.cache
    cached = {}

    # Basic LaTex Setup as well as our list of expressions to parse
    tex_preamble = r"""\documentclass{article}
\usepackage{amsmath}
\usepackage{amsthm}
\usepackage{amssymb}
\usepackage{bm}
\usepackage[usenames,dvipsnames]{color}
\pagestyle{empty}
"""

    def __init__(self, configs):
        try:
            cache_file = open('latex.cache', 'r+')
            for line in cache_file.readlines():
                key, val = line.strip("\n").split(" ")
                self.cached[key] = val
        except IOError:
            pass

    """The TeX preprocessor has to run prior to all the actual processing
    and can not be parsed in block mode very sanely."""
    def _latex_to_base64(self, tex, math_mode):
        """Generates a base64 representation of TeX string"""
        # Generate the temporary file
        tempfile.tempdir = ""
        path = tempfile.mktemp()
        tmp_file = open(path, "w")
        tmp_file.write(self.tex_preamble)

        # Figure out the mode that we're in
        if math_mode:
            tmp_file.write("$%s$" % tex)
        else:
            tmp_file.write("%s" % tex)

        tmp_file.write('\n\end{document}')
        tmp_file.close()

        # compile LaTeX document. A DVI file is created
        status = call(('latex -halt-on-error %s' % path).split(), stdout=PIPE)

        # clean up if the above failed
        if status:
            self._cleanup(path, err=True)
            raise Exception("Couldn't compile LaTeX document." +
                "Please read '%s.log' for more detail." % path)

        # Run dvipng on the generated DVI file. Use tight bounding box.
        # Magnification is set to 1200
        dvi = "%s.dvi" % path
        png = "%s.png" % path

        # Extract the image
        cmd = "dvipng -q -T tight -x 1200 -z 9 \
                %s -o %s" % (dvi, png)
        status = call(cmd.split(), stdout=PIPE)

        # clean up if we couldn't make the above work
        if status:
            self._cleanup(path, err=True)
            raise Exception("Couldn't convert LaTeX to image." +
                    "Please read '%s.log' for more detail." % path)

        # Read the png and encode the data
        png = open(png, "rb")
        data = png.read()
        data = base64.b64encode(data)
        png.close()

        self._cleanup(path)

        return data

    def _cleanup(self, path, err=False):
        # don't clean up the log if there's an error
        extensions = ["", ".aux", ".dvi", ".png", ".log"]
        if err:
            extensions.pop()

        # now do the actual cleanup, passing on non-existent files
        for extension in extensions:
            try:
                os.remove("%s%s" % (path, extension))
            except (IOError, OSError):
                pass

    def run(self, lines):
        """Parses the actual page"""
        # Re-creates the entire page so we can parse in a multine env.
        page = "\n".join(lines)

        # Adds a preamble mode
        preambles = PREAMBLE_MODE.findall(page)
        for preamble in preambles:
            self.tex_preamble += preamble + "\n"
            page = PREAMBLE_MODE.sub("", page, 1)
        self.tex_preamble += "\n\\begin{document}\n"

        # Figure out our text strings and math-mode strings
        tex_expr = [(TEX_MODE, False, x) for x in TEX_MODE.findall(page)]
        tex_expr += [(MATH_MODE, True, x) for x in MATH_MODE.findall(page)]

        # No sense in doing the extra work
        if not len(tex_expr):
            return page.split("\n")

        # Parse the expressions
        new_cache = {}
        for reg, math_mode, expr in tex_expr:
            simp_expr = filter(unicode.isalnum, expr)
            if simp_expr in self.cached:
                data = self.cached[simp_expr]
            else:
                data = self._latex_to_base64(expr, math_mode)
                new_cache[simp_expr] = data
            expr = expr.replace('"', "").replace("'", "")
            page = reg.sub(IMG_EXPR %
                    (str(math_mode).lower(), simp_expr,
                        simp_expr[:15], data), page, 1)

        # Cache our data
        cache_file = open('latex.cache', 'a')
        for key, value in new_cache.items():
            cache_file.write("%s %s\n" % (key, value))
        cache_file.close()

        # Make sure to resplit the lines
        return page.split("\n")


class LaTeXPostprocessor(markdown.postprocessors.Postprocessor):
        """This post processor extension just allows us to further
        refine, if necessary, the document after it has been parsed."""
        def run(self, text):
            # Inline a style for default behavior
            text = IMG_CSS + text
            return text


class MarkdownLatex(markdown.Extension):
    """Wrapper for LaTeXPreprocessor"""
    def extendMarkdown(self, md, md_globals):
        # Our base LaTeX extension
        md.preprocessors.add('latex',
                LaTeXPreprocessor(self), ">html_block")
        # Our cleanup postprocessing extension
        md.postprocessors.add('latex',
                LaTeXPostprocessor(self), ">amp_substitute")


def makeExtension(configs=None):
    """Wrapper for a MarkDown extension"""
    return MarkdownLatex(configs=configs)

########NEW FILE########
__FILENAME__ = worker_init
# This script is purposefully left non-executable as it can easily have
# unintended, hard to reverse effects on a server
#
# This script is meant to be run on a fresh install of ubuntu (such as a newly
# instantiated Ec2 instance) and will create a user, download the contest
# code and run the worker_setup.py script so it can then finish setting up a
# contest worker instance.
#
# usage: worker_init.py download_url worker_api_key

WARNING = "WARNING, this script will make invasive changes to your system!"

import os
import os.path
import sys
from subprocess import Popen

def run_cmd(cmd):
    """ Run a command in a shell """
    print "Executing:", cmd
    proc = Popen(cmd, shell=True)
    status = proc.wait()
    if status != 0:
        raise Exception("Command %s exited with %d" % (cmd, status))

def setup_contest_user():
    """ Setup the contest user that all worker scripts run under """
    if not os.path.exists("/home/contest"):
        run_cmd('adduser --disabled-password --gecos "" contest')

def get_contest_files(download_url):
    """ Get the contest files downloaded and placed in the current directory """
    if os.path.exists("aichallenge"):
        return
    run_cmd("wget %s/worker-src.tgz" % (download_url,))
    run_cmd("tar -xf worker-src.tgz")
    run_cmd("rm worker-src.tgz")

def main():
    if len(sys.argv) < 3:
        print "usage: %s api_base_url worker_api_key [source_url]"
        print WARNING
        sys.exit(1)
    setup_contest_user()
    os.chdir("/home/contest")
    get_contest_files(sys.argv[1])
    os.chdir("aichallenge/setup")
    setup_cmd = "./worker_setup.py -y --username contest --api-url %s \
            --api-key %s --install-cronjob --start" % (sys.argv[1], sys.argv[2])
    if len(sys.argv) > 3:
        setup_cmd += " " + " ".join(sys.argv[3:])
    run_cmd(setup_cmd)

if __name__=="__main__":
    main()


########NEW FILE########
__FILENAME__ = compiler
#!/usr/bin/python
# compiler.py
# Author: Jeff Cameron (jeff@jpcameron.com)
#
# Auto-detects the language of the entry based on the extension,
# attempts to compile it, returning the stdout and stderr.
# The auto-detection works by looking for the "main" code file of
# the available languages. If the number of matching languages is 0 or
# more than 1, it is an error, and an appropriate error message is returned.
#
# To add a new language you must add an entry to the "languages" list.
#
# For example the entry for Python is as follows:
#    Language("Python", BOT +".py", "MyBot.py",
#        "python MyBot.py",
#        ["*.pyc"],
#        [(["*.py"], ChmodCompiler("Python"))]
#    ),
# This defines the output file as MyBot.py, removes all .pyc files, and runs
# all the found .py files through the ChmodCompiler, which is a pseudo-compiler
# class which only chmods the found files.
#
# If you want to run a real compiler then you need to define a set of flags to
# send it. In this case you would either use TargetCompiler or ExternalCompiler.
# The difference between the two is the TargetCompiler iterates over the found
# files and creates object files from them, whereas the External doesn't.
# If in doubt just stick to the ExternalCompiler.
#
# An example is from the C# Entry:
#     "C#" : (".exe", ["*.exe"],
#                     [(["*.cs"], ExternalCompiler(comp_args["C#"][0]))])
#
# To make the dictionary more readable the flags have been split into a
# separate "comp_args" dictionary. C#'s entry looks like so:
#     "C#" : [["gmcs", "-warn:0", "-out:%s.exe" % BOT]]
# At runtime this all boils down to:
#     gmcs -warn:0 -out:MyBot.exe *.cs
# (though the *.cs is actually replaced with the list of files found)

import collections
import errno
import fnmatch
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import time
from optparse import OptionParser

from sandbox import get_sandbox
from string import split

try:
    from server_info import server_info
    MEMORY_LIMIT = server_info.get('memory_limit', 1500)
except ImportError:
    MEMORY_LIMIT = 1500

BOT = "MyBot"
SAFEPATH = re.compile('[a-zA-Z0-9_.$-]+$')

class CD(object):
    def __init__(self, new_dir):
        self.new_dir = new_dir

    def __enter__(self):
        self.org_dir = os.getcwd()
        os.chdir(self.new_dir)
        return self.new_dir

    def __exit__(self, type, value, traceback):
        os.chdir(self.org_dir)

def safeglob(pattern):
    safepaths = []
    for root, dirs, files in os.walk("."):
        files = fnmatch.filter(files, pattern)
        for fname in files:
            if SAFEPATH.match(fname):
                safepaths.append(os.path.join(root, fname))
    return safepaths

def safeglob_multi(patterns):
    safepaths = []
    for pattern in patterns:
        safepaths.extend(safeglob(pattern))
    return safepaths

def nukeglob(pattern):
    paths = safeglob(pattern)
    for path in paths:
        # Ought to be all files, not folders
        try:
            os.unlink(path)
        except OSError, e:
            if e.errno != errno.ENOENT:
                raise

def _run_cmd(sandbox, cmd, timelimit):
    out = []
    errors = []
    sandbox.start(cmd)
    # flush stdout to keep stuff moving
    try:
        while (sandbox.is_alive and time.time() < timelimit):
            out_ln = sandbox.read_line((timelimit - time.time()) + 1)
            if out_ln:
                out.append(out_ln)
    finally:
        sandbox.kill()
    # capture final output for error reporting
    tmp = sandbox.read_line(1)
    while tmp:
        out.append(tmp)
        tmp = sandbox.read_line(1)

    if time.time() > timelimit:
        errors.append("Compilation timed out with command %s"
                % (cmd,))
    err_line = sandbox.read_error()
    while err_line is not None:
        errors.append(err_line)
        err_line = sandbox.read_error()
    return out, errors

def check_path(path, errors):
    if not os.path.exists(path):
        errors.append("Output file " + str(os.path.basename(path)) + " was not created.")
        return False
    else:
        return True

class Compiler:
    def compile(self, globs, errors):
        raise NotImplementedError

class ChmodCompiler(Compiler):
    def __init__(self, language):
        self.language = language

    def __str__(self):
        return "ChmodCompiler: %s" % (self.language,)

    def compile(self, bot_dir, globs, errors, timelimit):
        with CD(bot_dir):
            for f in safeglob_multi(globs):
                try:
                    os.chmod(f, 0644)
                except Exception, e:
                    errors.append("Error chmoding %s - %s\n" % (f, e))
        return True

class ExternalCompiler(Compiler):
    def __init__(self, args, separate=False, out_files=[], out_ext=None):
        """Compile files using an external compiler.

        args, is a list of the compiler command and any arguments to run.
        separate, controls whether all input files are sent to the compiler
            in one command or one file per compiler invocation.
        out_files, is a list of files that should exist after each invocation
        out_ext, is an extension that is replaced on each input file and should
            exist after each invocation.
        """

        self.args = args
        self.separate = separate
        self.out_files = out_files
        self.out_ext = out_ext

    def __str__(self):
        return "ExternalCompiler: %s" % (' '.join(self.args),)

    def compile(self, bot_dir, globs, errors, timelimit):
        with CD(bot_dir):
            files = safeglob_multi(globs)

        box = get_sandbox(bot_dir)
        try:
            if self.separate:
                for filename in files:
                    cmdline = " ".join(self.args + [filename])
                    cmd_out, cmd_errors = _run_cmd(box, cmdline, timelimit)
                    cmd_errors = self.cmd_error_filter(cmd_out, cmd_errors);
                    if not cmd_errors:
                        for ofile in self.out_files:
                            box.check_path(ofile, cmd_errors)
                        if self.out_ext:
                            oname = os.path.splitext(filename)[0] + self.out_ext
                            box.check_path(oname, cmd_errors)
                        if cmd_errors:
                            cmd_errors += cmd_out
                    if cmd_errors:
                        errors += cmd_errors
                        return False
            else:
                cmdline = " ".join(self.args + files)
                cmd_out, cmd_errors = _run_cmd(box, cmdline, timelimit)
                cmd_errors = self.cmd_error_filter(cmd_out, cmd_errors);
                if not cmd_errors:
                    for ofile in self.out_files:
                        box.check_path(ofile, cmd_errors)
                    if self.out_ext:
                        for filename in files:
                            oname = os.path.splitext(filename)[0] + self.out_ext
                            box.check_path(oname, cmd_errors)
                    if cmd_errors:
                        cmd_errors += cmd_out
                if cmd_errors:
                    errors += cmd_errors
                    return False
            box.retrieve()
        finally:
            box.release()
        return True

    def cmd_error_filter(self, cmd_out, cmd_errors):
        """Default implementation doesn't filter"""
        return cmd_errors


# An external compiler with some stdout/sdtderr post-processing power
class ErrorFilterCompiler(ExternalCompiler):
    def __init__(self, args, separate=False, out_files=[], out_ext=None, stdout_is_error=False, skip_stdout=0, filter_stdout=None, filter_stderr=None):
        """Compile files using an external compiler.

        args, is a list of the compiler command and any arguments to run.
        separate, controls whether all input files are sent to the compiler
            in one command or one file per compiler invocation.
        out_files, is a list of files that should exist after each invocation
        out_ext, is an extension that is replaced on each input file and should
            exist after each invocation.
        stdout_is_error, controls if stdout contains error compiler error messages
        skip_stdout, controls how many lines at the start of stdout are ignored
        filter_stdout, is a regex that filters out lines from stdout that are no errors
        filter_stderr, is a regex that filters out lines from stderr that are no errors
        """

        ExternalCompiler.__init__(self, args, separate, out_files, out_ext)
        self.stdout_is_error = stdout_is_error
        self.skip_stdout = skip_stdout;
        if filter_stdout is None:
            self.stdout_re = None
        else:
            self.stdout_re = re.compile(filter_stdout)
        if filter_stderr is None:
            self.stderr_re = None
        else:
            self.stderr_re = re.compile(filter_stderr)

    def __str__(self):
        return "ErrorFilterCompiler: %s" % (' '.join(self.args),)

    def cmd_error_filter(self, cmd_out, cmd_errors):
        """Skip and filter lines"""
        if self.skip_stdout > 0:
            del cmd_out[:self.skip_stdout]
        # Somehow there are None values in the output
        if self.stdout_re is not None:
            cmd_out = [line for line in cmd_out if
                       line is None or not self.stdout_re.search(line)]
        if self.stderr_re is not None:
            cmd_errors = [line for line in cmd_errors if
                          line is None or not self.stderr_re.search(line)]
        if self.stdout_is_error:
            return [line for line in cmd_out if line is not None] + cmd_errors
        return cmd_errors

# Compiles each file to its own output, based on the replacements dict.
class TargetCompiler(Compiler):
    def __init__(self, args, replacements, outflag="-o"):
        self.args = args
        self.replacements = replacements
        self.outflag = outflag

    def __str__(self):
        return "TargetCompiler: %s" % (' '.join(self.args),)

    def compile(self, bot_dir, globs, errors, timelimit):
        with CD(bot_dir):
            sources = safeglob_multi(globs)

        box = get_sandbox(bot_dir)
        try:
            for source in sources:
                head, ext = os.path.splitext(source)
                if ext in self.replacements:
                    target = head + self.replacements[ext]
                else:
                    errors.append("Could not determine target for source file %s." % source)
                    return False
                cmdline = " ".join(self.args + [self.outflag, target, source])
                cmd_out, cmd_errors = _run_cmd(box, cmdline, timelimit)
                if cmd_errors:
                    errors += cmd_errors
                    return False
            box.retrieve()
        finally:
            box.release()
        return True

PYTHON_EXT_COMPILER = '''"from distutils.core import setup
from distutils.extension import read_setup_file
setup(ext_modules = read_setup_file('setup_exts'), script_args = ['-q', 'build_ext', '-i'])"'''

comp_args = {
    # lang : ([list of compilation arguments], ...)
    #                If the compilation should output each source file to
    #                its own object file, don't include the -o flags here,
    #                and use the TargetCompiler in the languages dict.
    "Ada"           : [["gcc-4.4", "-O3", "-funroll-loops", "-c"],
                             ["gnatbind"],
                             ["gnatlink", "-o", BOT]],
    "C"             : [["gcc", "-O3", "-funroll-loops", "-c"],
                             ["gcc", "-O2", "-lm", "-o", BOT]],
    "C#"            : [["gmcs", "-warn:0", "-optimize+", "-out:%s.exe" % BOT]],
    "VB"            : [["vbnc", "-out:%s.exe" % BOT]],
    "C++"         : [["g++", "-O3", "-funroll-loops", "-c"],
                             ["g++", "-O2", "-lm", "-o", BOT]],
    "C++11"         : [["g++", "-O3", "-std=c++0x", "-c"],
                             ["g++", "-O2", "-lm", "-std=c++0x", "-o", BOT]],
    "D"             : [["dmd", "-O", "-inline", "-release", "-noboundscheck", "-of" + BOT]],
    "Go"            : [["6g", "-o", "_go_.6"],
                             ["6l", "-o", BOT, "_go_.6"]],
    "Groovy"    : [["groovyc"],
                             ["jar", "cfe", BOT + ".jar", BOT]],
    # If we ever upgrade to GHC 7, we will need to add -rtsopts to this command
    # in order for the maximum heap size RTS flag to work on the executable.
    "Haskell" : [["ghc", "--make", BOT + ".hs", "-O", "-v0"]],
    "Java"        : [["javac", "-J-Xmx%sm" % (MEMORY_LIMIT)],
                             ["jar", "cfe", BOT + ".jar", BOT]],
    "Lisp"      : [['sbcl', '--dynamic-space-size', str(MEMORY_LIMIT), '--script', BOT + '.lisp']],
    "OCaml"     : [["ocamlbuild -lib unix", BOT + ".native"]],
    "Pascal"    : [["fpc", "-Mdelphi", "-Si", "-O3", "-Xs", "-v0", "-o" + BOT]],
    "Python"    : [["python", "-c", PYTHON_EXT_COMPILER]],
    "Python3"   : [["python3", "-c", PYTHON_EXT_COMPILER]],
    "Scala"     : [["scalac"]],
    }

targets = {
    # lang : { old_ext : new_ext, ... }
    "C"     : { ".c" : ".o" },
    "C++" : { ".c" : ".o", ".cpp" : ".o", ".cc" : ".o" },
    }

Language = collections.namedtuple("Language",
        ['name', 'out_file', 'main_code_file', 'command', 'nukeglobs',
            'compilers']
        )

languages = (
    # Language(name, output file,
    #      main_code_file
    #      command_line
    #      [nukeglobs],
    #      [(source glob, compiler), ...])
    #
    # The compilers are run in the order given.
    # If a source glob is "" it means the source is part of the compiler
    #   arguments.
    Language("Ada", BOT, "mybot.adb",
        "./MyBot",
        ["*.ali"],
        [(["*.adb"], ExternalCompiler(comp_args["Ada"][0])),
            (["mybot.ali"], ExternalCompiler(comp_args["Ada"][1])),
            (["mybot.ali"], ExternalCompiler(comp_args["Ada"][2]))]
    ),
    Language("C", BOT, "MyBot.c",
        "./MyBot",
        ["*.o", BOT],
        [(["*.c"], TargetCompiler(comp_args["C"][0], targets["C"])),
            (["*.o"], ExternalCompiler(comp_args["C"][1]))]
    ),
    Language("C#", BOT +".exe", "MyBot.cs",
        "mono MyBot.exe",
        [BOT + ".exe"],
        [(["*.cs"], ExternalCompiler(comp_args["C#"][0]))]
    ),
    Language("VB", BOT +".exe", "MyBot.vb",
        "mono MyBot.exe",
        [BOT + ".exe"],
        [(["*.vb"],
            ExternalCompiler(comp_args["VB"][0], out_files=['MyBot.exe']))]
    ),
    # These two C++ variants should be combined after the ants contest
    Language("C++", BOT, "MyBot.cc",
        "./MyBot",
        ["*.o", BOT],
        [
            (["*.c", "*.cpp", "*.cc"],
                TargetCompiler(comp_args["C++"][0], targets["C++"])),
            (["*.o"], ExternalCompiler(comp_args["C++"][1]))
        ]
    ),
    Language("C++11", BOT, "MyBot.cpp",
        "./MyBot",
        ["*.o", BOT],
        [
            (["*.c", "*.cpp", "*.cc"],
                TargetCompiler(comp_args["C++11"][0], targets["C++"])),
            (["*.o"], ExternalCompiler(comp_args["C++11"][1]))
        ]
    ),
    Language("Clojure", BOT +".clj", "MyBot.clj",
		"java -Xmx%sm -cp /usr/share/java/clojure.jar:. clojure.main MyBot.clj" % (MEMORY_LIMIT,),
        [],
        [(["*.clj"], ChmodCompiler("Clojure"))]
    ),
    Language("CoffeeScript", BOT +".coffee", "MyBot.coffee",
        "coffee MyBot.coffee",
        [],
        [(["*.coffee"], ChmodCompiler("CoffeeScript"))]
    ),
    Language("D", BOT, "MyBot.d",
        "./MyBot",
        ["*.o", BOT],
        [(["*.d"], ExternalCompiler(comp_args["D"][0]))]
    ),
    Language("Dart", BOT +".dart", "MyBot.dart",
        "frogsh MyBot.dart",
        [],
        [(["*.dart"], ChmodCompiler("Dart"))]
    ),
    Language("Erlang", "my_bot.beam", "my_bot.erl",
        "erl -hms"+ str(MEMORY_LIMIT) +"m -smp disable -noshell -s my_bot start -s init stop",
        ["*.beam"],
        [(["*.erl"], ExternalCompiler(["erlc"], out_ext=".beam"))]
    ),
    Language("Go", BOT, "MyBot.go",
        "./MyBot",
        ["*.8", "*.6", BOT],
        [(["*.go"], ExternalCompiler(comp_args["Go"][0], out_files=['_go_.6'])),
            ([""], ExternalCompiler(comp_args["Go"][1], out_files=['_go_.6']))]
    ),
    Language("Groovy", BOT +".jar", "MyBot.groovy",
        "java -Xmx" + str(MEMORY_LIMIT) + "m -cp MyBot.jar:/usr/share/groovy/embeddable/groovy-all-1.7.5.jar MyBot",
        ["*.class, *.jar"],
        [(["*.groovy"], ExternalCompiler(comp_args["Groovy"][0])),
        (["*.class"], ExternalCompiler(comp_args["Groovy"][1]))]
    ),
    Language("Haskell", BOT, "MyBot.hs",
        "./MyBot +RTS -M" + str(MEMORY_LIMIT) + "m",
        [BOT],
        [([""], ExternalCompiler(comp_args["Haskell"][0]))]
    ),
    Language("Java", BOT +".jar", "MyBot.java",
        "java -Xmx" + str(MEMORY_LIMIT) + "m -jar MyBot.jar",
        ["*.class", "*.jar"],
        [(["*.java"], ExternalCompiler(comp_args["Java"][0])),
            (["*.class"], ExternalCompiler(comp_args["Java"][1]))]
    ),
    Language("Javascript", BOT +".js", "MyBot.js",
        "node MyBot.js",
        [],
        [(["*.js"], ChmodCompiler("Javascript"))]
    ),
    Language("Lisp", BOT, "MyBot.lisp",
        "./MyBot --dynamic-space-size " + str(MEMORY_LIMIT),
        [BOT],
        [([""], ExternalCompiler(comp_args["Lisp"][0]))]
    ),
    Language("Lua", BOT +".lua", "MyBot.lua",
        "luajit-2.0.0-beta5 MyBot.lua",
        [],
        [(["*.lua"], ChmodCompiler("Lua"))]
    ),
    Language("OCaml", BOT +".native", "MyBot.ml",
        "./MyBot.native",
        [BOT + ".native"],
        [([""], ExternalCompiler(comp_args["OCaml"][0]))]
    ),
    Language("Octave", BOT + ".m", "MyBot.m", 
        "octave -qf MyBot.m",
        [],
        [(["*.m"], ChmodCompiler("Octave"))]
    ),
    Language("Pascal", BOT, BOT + ".pas",
        "./" + BOT,
        [BOT, "*.o", "*.ppu"],
        [([BOT + ".pas"], ErrorFilterCompiler(comp_args["Pascal"][0], 
           stdout_is_error=True, skip_stdout=2,
           filter_stderr='^/usr/bin/ld: warning: link.res contains output sections; did you forget -T\?$'))]
    ),
    Language("Perl", BOT +".pl", "MyBot.pl",
        "perl MyBot.pl",
        [],
        [(["*.pl"], ChmodCompiler("Perl"))]
    ),
    Language("PHP", BOT +".php", "MyBot.php",
        "php MyBot.php",
        [],
        [(["*.php"], ChmodCompiler("PHP"))]
    ),
    Language("Python", BOT +".py", "MyBot.py",
        "python MyBot.py",
        ["*.pyc"],
        [(["*.py"], ChmodCompiler("Python")),
        (["setup_exts"], ErrorFilterCompiler(comp_args["Python"][0], separate=True, filter_stderr='-Wstrict-prototypes'))]
    ),
    Language("Python3", BOT +".py3", "MyBot.py3",
        "python3 MyBot.py3",
        ["*.pyc"],
        [(["*.py3"], ChmodCompiler("Python3")),
        (["setup_exts"], ErrorFilterCompiler(comp_args["Python3"][0], separate=True, filter_stderr='-Wstrict-prototypes'))]
    ),
    Language("PyPy", BOT +".pypy", "MyBot.pypy",
        "pypy MyBot.pypy",
        ["*.pyc"],
        [(["*.py"], ChmodCompiler("Python"))]
    ),
    Language("Racket", BOT +".rkt", "MyBot.rkt",
        "racket MyBot.rkt",
        [],
        [(["*.rkt"], ChmodCompiler("Racket"))]
    ),
    Language("Ruby", BOT +".rb", "MyBot.rb",
        "ruby MyBot.rb",
        [],
        [(["*.rb"], ChmodCompiler("Ruby"))]
    ),
    Language("Scala", BOT +".scala", "MyBot.scala",
        'scala -J-Xmx'+ str(MEMORY_LIMIT) +'m -howtorun:object MyBot',
        ["*.scala, *.jar"],
        [(["*.scala"], ExternalCompiler(comp_args["Scala"][0]))]
    ),
    Language("Scheme", BOT +".ss", "MyBot.ss",
        "./MyBot",
        [],
        [(["*.ss"], ChmodCompiler("Scheme"))]
    ),
    Language("Tcl", BOT +".tcl", "MyBot.tcl",
        "tclsh8.5 MyBot.tcl",
        [],
        [(["*.tcl"], ChmodCompiler("Tcl"))]
    ),
)


def compile_function(language, bot_dir, timelimit):
    """Compile submission in the current directory with a specified language."""
    with CD(bot_dir):
        for glob in language.nukeglobs:
            nukeglob(glob)

    errors = []
    stop_time = time.time() + timelimit
    for globs, compiler in language.compilers:
        try:
            if not compiler.compile(bot_dir, globs, errors, stop_time):
                return False, errors
        except StandardError, exc:
            raise
            errors.append("Compiler %s failed with: %s"
                    % (compiler, exc))
            return False, errors

    compiled_bot_file = os.path.join(bot_dir, language.out_file)
    return check_path(compiled_bot_file, errors), errors

_LANG_NOT_FOUND = """Did not find a recognized MyBot.* file.
Please add one of the following filenames to your zip file:
%s"""

def detect_language(bot_dir):
    """Try and detect what language a submission is using"""
    with CD(bot_dir):
        # Autodetects the language of the entry in the current working directory
        detected_langs = [
            lang for lang in languages if os.path.exists(lang.main_code_file)
        ]

        # If no language was detected
        if len(detected_langs) > 1:
            return None, ['Found multiple MyBot.* files: \n'+
                          '\n'.join([l.main_code_file for l in detected_langs])]
        elif len(detected_langs) == 0:
            return None, [_LANG_NOT_FOUND % (
                '\n'.join(l.name +": "+ l.main_code_file for l in languages),)]
        else:
            return detected_langs[0], None

def get_run_cmd(submission_dir):
    """Get the language of a submission"""
    with CD(submission_dir):
        if os.path.exists('run.sh'):
            with open('run.sh') as f:
                for line in f:
                    if line[0] != '#':
                        return line.rstrip('\r\n')

def get_run_lang(submission_dir):
    """Get the command to run a submission"""
    with CD(submission_dir):
        if os.path.exists('run.sh'):
            with open('run.sh') as f:
                for line in f:
                    if line[0] == '#':
                        return line[1:-1]

def compile_anything(bot_dir, timelimit=600, max_error_len = 3072):
    """Autodetect the language of an entry and compile it."""
    detected_language, errors = detect_language(bot_dir)
    if detected_language:
        # If we get this far, then we have successfully auto-detected
        # the language that this entry is using.
        compiled, errors = compile_function(detected_language, bot_dir,
                timelimit)
        if compiled:
            name = detected_language.name
            run_cmd = detected_language.command
            run_filename = os.path.join(bot_dir, '../run.sh')
            with open(run_filename, 'w') as f:
                f.write('#%s\n%s\n' % (name, run_cmd))
            return name, None
        else:
            # limit length of reported errors
            if len(errors) > 0 and sum(map(len, errors)) > max_error_len:
                first_errors = []
                cur_error = 0
                length = len(errors[0])
                while length < (max_error_len / 3): # take 1/3 from start
                    first_errors.append(errors[cur_error])
                    cur_error += 1
                    length += len(errors[cur_error])
                first_errors.append("...")
                length += 3
                end_errors = []
                cur_error = -1
                while length <= max_error_len:
                    end_errors.append(errors[cur_error])
                    cur_error -= 1
                    length += len(errors[cur_error])
                end_errors.reverse()
                errors = first_errors + end_errors

            return detected_language.name, errors
    else:
        return "Unknown", errors

def main(argv=sys.argv):
    parser = OptionParser(usage="Usage: %prog [options] [directory]")
    parser.add_option("-j", "--json", action="store_true", dest="json",
            default=False,
            help="Give compilation results in json format")
    options, args = parser.parse_args(argv)
    if len(args) == 1:
        detected_lang, errors = compile_anything(os.getcwd())
    elif len(args) == 2:
        detected_lang, errors = compile_anything(args[1])
    else:
        parser.error("Extra arguments found, use --help for usage")
    if options.json:
        import json
        print json.dumps([detected_lang, errors])
    else:
        print "Detected language:", detected_lang
        if errors != None and len(errors) != 0:
            for error in errors:
                print(error)

if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = engine
#!/usr/bin/env python
from __future__ import print_function
import time
import traceback
import os
import random
import sys
import json
import io
if sys.version_info >= (3,):
    def unicode(s):
        return s

from sandbox import get_sandbox

class HeadTail(object):
    'Capture first part of file write and discard remainder'
    def __init__(self, file, max_capture=510):
        self.file = file
        self.max_capture = max_capture
        self.capture_head_len = 0
        self.capture_head = unicode('')
        self.capture_tail = unicode('')
    def write(self, data):
        if self.file:
            self.file.write(data)
        capture_head_left = self.max_capture - self.capture_head_len
        if capture_head_left > 0:
            data_len = len(data)
            if data_len <= capture_head_left:
                self.capture_head += data
                self.capture_head_len += data_len
            else:
                self.capture_head += data[:capture_head_left]
                self.capture_head_len = self.max_capture
                self.capture_tail += data[capture_head_left:]
                self.capture_tail = self.capture_tail[-self.max_capture:]
        else:
            self.capture_tail += data
            self.capture_tail = self.capture_tail[-self.max_capture:]
    def flush(self):
        if self.file:
            self.file.flush()
    def close(self):
        if self.file:
            self.file.close()
    def head(self):
        return self.capture_head
    def tail(self):
        return self.capture_tail
    def headtail(self):
        if self.capture_head != '' and self.capture_tail != '':
            sep = unicode('\n..\n')
        else:
            sep = unicode('')
        return self.capture_head + sep + self.capture_tail

def run_game(game, botcmds, options):
    # file descriptors for replay and streaming formats
    replay_log = options.get('replay_log', None)
    stream_log = options.get('stream_log', None)
    verbose_log = options.get('verbose_log', None)
    # file descriptors for bots, should be list matching # of bots
    input_logs = options.get('input_logs', [None]*len(botcmds))
    output_logs = options.get('output_logs', [None]*len(botcmds))
    error_logs = options.get('error_logs', [None]*len(botcmds))

    capture_errors = options.get('capture_errors', False)
    capture_errors_max = options.get('capture_errors_max', 510)

    turns = int(options['turns'])
    loadtime = float(options['loadtime']) / 1000
    turntime = float(options['turntime']) / 1000
    strict = options.get('strict', False)
    end_wait = options.get('end_wait', 0.0)

    location = options.get('location', 'localhost')
    game_id = options.get('game_id', 0)

    error = ''

    bots = []
    bot_status = []
    bot_turns = []
    if capture_errors:
        error_logs = [HeadTail(log, capture_errors_max) for log in error_logs]
    try:
        # create bot sandboxes
        for b, bot in enumerate(botcmds):
            bot_cwd, bot_cmd = bot
            sandbox = get_sandbox(bot_cwd,
                    secure=options.get('secure_jail', None))
            sandbox.start(bot_cmd)
            bots.append(sandbox)
            bot_status.append('survived')
            bot_turns.append(0)

            # ensure it started
            if not sandbox.is_alive:
                bot_status[-1] = 'crashed 0'
                bot_turns[-1] = 0
                if verbose_log:
                    verbose_log.write('bot %s did not start\n' % b)
                game.kill_player(b)
            sandbox.pause()

        if stream_log:
            stream_log.write(game.get_player_start())
            stream_log.flush()

        if verbose_log:
            verbose_log.write('running for %s turns\n' % turns)
        for turn in range(turns+1):
            if turn == 0:
                game.start_game()

            # send game state to each player
            for b, bot in enumerate(bots):
                if game.is_alive(b):
                    if turn == 0:
                        start = game.get_player_start(b) + 'ready\n'
                        bot.write(start)
                        if input_logs and input_logs[b]:
                            input_logs[b].write(start)
                            input_logs[b].flush()
                    else:
                        state = 'turn ' + str(turn) + '\n' + game.get_player_state(b) + 'go\n'
                        bot.write(state)
                        if input_logs and input_logs[b]:
                            input_logs[b].write(state)
                            input_logs[b].flush()
                        bot_turns[b] = turn

            if turn > 0:
                if stream_log:
                    stream_log.write('turn %s\n' % turn)
                    stream_log.write('score %s\n' % ' '.join([str(s) for s in game.get_scores()]))
                    stream_log.write(game.get_state())
                    stream_log.flush()
                game.start_turn()

            # get moves from each player
            if turn == 0:
                time_limit = loadtime
            else:
                time_limit = turntime

            if options.get('serial', False):
                simul_num = int(options['serial']) # int(True) is 1
            else:
                simul_num = len(bots)

            bot_moves = [[] for b in bots]
            error_lines = [[] for b in bots]
            statuses = [None for b in bots]
            bot_list = [(b, bot) for b, bot in enumerate(bots)
                        if game.is_alive(b)]
            random.shuffle(bot_list)
            for group_num in range(0, len(bot_list), simul_num):
                pnums, pbots = zip(*bot_list[group_num:group_num + simul_num])
                moves, errors, status = get_moves(game, pbots, pnums,
                        time_limit, turn)
                for p, b in enumerate(pnums):
                    bot_moves[b] = moves[p]
                    error_lines[b] = errors[p]
                    statuses[b] = status[p]

            # handle any logs that get_moves produced
            for b, errors in enumerate(error_lines):
                if errors:
                    if error_logs and error_logs[b]:
                        error_logs[b].write(unicode('\n').join(errors)+unicode('\n'))
            # set status for timeouts and crashes
            for b, status in enumerate(statuses):
                if status != None:
                    bot_status[b] = status
                    bot_turns[b] = turn

            # process all moves
            bot_alive = [game.is_alive(b) for b in range(len(bots))]
            if turn > 0 and not game.game_over():
                for b, moves in enumerate(bot_moves):
                    if game.is_alive(b):
                        valid, ignored, invalid = game.do_moves(b, moves)
                        if output_logs and output_logs[b]:
                            output_logs[b].write('# turn %s\n' % turn)
                            if valid:
                                if output_logs and output_logs[b]:
                                    output_logs[b].write('\n'.join(valid)+'\n')
                                    output_logs[b].flush()
                        if ignored:
                            if error_logs and error_logs[b]:
                                error_logs[b].write('turn %4d bot %s ignored actions:\n' % (turn, b))
                                error_logs[b].write('\n'.join(ignored)+'\n')
                                error_logs[b].flush()
                            if output_logs and output_logs[b]:
                                output_logs[b].write('\n'.join(ignored)+'\n')
                                output_logs[b].flush()
                        if invalid:
                            if strict:
                                game.kill_player(b)
                                bot_status[b] = 'invalid'
                                bot_turns[b] = turn
                            if error_logs and error_logs[b]:
                                error_logs[b].write('turn %4d bot %s invalid actions:\n' % (turn, b))
                                error_logs[b].write('\n'.join(invalid)+'\n')
                                error_logs[b].flush()
                            if output_logs and output_logs[b]:
                                output_logs[b].write('\n'.join(invalid)+'\n')
                                output_logs[b].flush()

            if turn > 0:
                game.finish_turn()

            # send ending info to eliminated bots
            bots_eliminated = []
            for b, alive in enumerate(bot_alive):
                if alive and not game.is_alive(b):
                    bots_eliminated.append(b)
            for b in bots_eliminated:
                if verbose_log:
                    verbose_log.write('turn %4d bot %s eliminated\n' % (turn, b))
                if bot_status[b] == 'survived': # could be invalid move
                    bot_status[b] = 'eliminated'
                    bot_turns[b] = turn
                score_line ='score %s\n' % ' '.join([str(s) for s in game.get_scores(b)])
                status_line = 'status %s\n' % ' '.join(map(str, game.order_for_player(b, bot_status)))
                status_line += 'playerturns %s\n' % ' '.join(map(str, game.order_for_player(b, bot_turns)))
                end_line = 'end\nplayers %s\n' % len(bots) + score_line + status_line
                state = end_line + game.get_player_state(b) + 'go\n'
                bots[b].write(state)
                if input_logs and input_logs[b]:
                    input_logs[b].write(state)
                    input_logs[b].flush()
                if end_wait:
                    bots[b].resume()
            if bots_eliminated and end_wait:
                if verbose_log:
                    verbose_log.write('waiting {0} seconds for bots to process end turn\n'.format(end_wait))
                time.sleep(end_wait)
            for b in bots_eliminated:
                bots[b].kill()

            if verbose_log:
                stats = game.get_stats()
                stat_keys = sorted(stats.keys())
                s = 'turn %4d stats: ' % turn
                if turn % 50 == 0:
                    verbose_log.write(' '*len(s))
                    for key in stat_keys:
                        values = stats[key]
                        verbose_log.write(' {0:^{1}}'.format(key, max(len(key), len(str(values)))))
                    verbose_log.write('\n')
                verbose_log.write(s)
                for key in stat_keys:
                    values = stats[key]
                    if type(values) == list:
                        values = '[' + ','.join(map(str,values)) + ']'
                    verbose_log.write(' {0:^{1}}'.format(values, max(len(key), len(str(values)))))
                verbose_log.write('\n')

            #alive = [game.is_alive(b) for b in range(len(bots))]
            #if sum(alive) <= 1:
            if game.game_over():
                break

        # send bots final state and score, output to replay file
        game.finish_game()
        score_line ='score %s\n' % ' '.join(map(str, game.get_scores()))
        status_line = 'status %s\n' % ' '.join(bot_status)
        status_line += 'playerturns %s\n' % ' '.join(map(str, bot_turns))
        end_line = 'end\nplayers %s\n' % len(bots) + score_line + status_line
        if stream_log:
            stream_log.write(end_line)
            stream_log.write(game.get_state())
            stream_log.flush()
        if verbose_log:
            verbose_log.write(score_line)
            verbose_log.write(status_line)
            verbose_log.flush()
        for b, bot in enumerate(bots):
            if game.is_alive(b):
                score_line ='score %s\n' % ' '.join([str(s) for s in game.get_scores(b)])
                status_line = 'status %s\n' % ' '.join(map(str, game.order_for_player(b, bot_status)))
                status_line += 'playerturns %s\n' % ' '.join(map(str, game.order_for_player(b, bot_turns)))
                end_line = 'end\nplayers %s\n' % len(bots) + score_line + status_line
                state = end_line + game.get_player_state(b) + 'go\n'
                bot.write(state)
                if input_logs and input_logs[b]:
                    input_logs[b].write(state)
                    input_logs[b].flush()

    except Exception as e:
        # TODO: sanitize error output, tracebacks shouldn't be sent to workers
        error = traceback.format_exc()
        if verbose_log:
            verbose_log.write(traceback.format_exc())
        # error = str(e)
    finally:
        if end_wait:
            for bot in bots:
                bot.resume()
            if verbose_log:
                verbose_log.write('waiting {0} seconds for bots to process end turn\n'.format(end_wait))
            time.sleep(end_wait)
        for bot in bots:
            if bot.is_alive:
                bot.kill()
            bot.release()

    if error:
        game_result = { 'error': error }
    else:
        scores = game.get_scores()
        game_result = {
            'challenge': game.__class__.__name__.lower(),
            'location': location,
            'game_id': game_id,
            'status': bot_status,
            'playerturns': bot_turns,
            'score': scores,
            'rank': [sorted(scores, reverse=True).index(x) for x in scores],
            'replayformat': 'json',
            'replaydata': game.get_replay(),
            'game_length': turn
        }
        if capture_errors:
            game_result['errors'] = [head.headtail() for head in error_logs]

    if replay_log:
        json.dump(game_result, replay_log, sort_keys=True)

    return game_result

def get_moves(game, bots, bot_nums, time_limit, turn):
    bot_finished = [not game.is_alive(bot_nums[b]) for b in range(len(bots))]
    bot_moves = [[] for b in bots]
    error_lines = [[] for b in bots]
    statuses = [None for b in bots]

    # resume all bots
    for bot in bots:
        if bot.is_alive:
            bot.resume()

    # don't start timing until the bots are started
    start_time = time.time()

    # loop until received all bots send moves or are dead
    #   or when time is up
    while (sum(bot_finished) < len(bot_finished) and
            time.time() - start_time < time_limit):
        time.sleep(0.01)
        for b, bot in enumerate(bots):
            if bot_finished[b]:
                continue # already got bot moves
            if not bot.is_alive:
                error_lines[b].append(unicode('turn %4d bot %s crashed') % (turn, bot_nums[b]))
                statuses[b] = 'crashed'
                line = bot.read_error()
                while line != None:
                    error_lines[b].append(line)
                    line = bot.read_error()
                bot_finished[b] = True
                game.kill_player(bot_nums[b])
                continue # bot is dead

            # read a maximum of 100 lines per iteration
            for x in range(100):
                line = bot.read_line()
                if line is None:
                    # stil waiting for more data
                    break
                line = line.strip()
                if line.lower() == 'go':
                    bot_finished[b] = True
                    # bot finished sending data for this turn
                    break
                bot_moves[b].append(line)

            for x in range(100):
                line = bot.read_error()
                if line is None:
                    break
                error_lines[b].append(line)
    # pause all bots again
    for bot in bots:
        if bot.is_alive:
            bot.pause()

    # check for any final output from bots
    for b, bot in enumerate(bots):
        if bot_finished[b]:
            continue # already got bot moves
        if not bot.is_alive:
            error_lines[b].append(unicode('turn %4d bot %s crashed') % (turn, bot_nums[b]))
            statuses[b] = 'crashed'
            line = bot.read_error()
            while line != None:
                error_lines[b].append(line)
                line = bot.read_error()
            bot_finished[b] = True
            game.kill_player(bot_nums[b])
            continue # bot is dead

        line = bot.read_line()
        while line is not None and len(bot_moves[b]) < 40000:
            line = line.strip()
            if line.lower() == 'go':
                bot_finished[b] = True
                # bot finished sending data for this turn
                break
            bot_moves[b].append(line)
            line = bot.read_line()

        line = bot.read_error()
        while line is not None and len(error_lines[b]) < 1000:
            error_lines[b].append(line)
            line = bot.read_error()

    # kill timed out bots
    for b, finished in enumerate(bot_finished):
        if not finished:
            error_lines[b].append(unicode('turn %4d bot %s timed out') % (turn, bot_nums[b]))
            statuses[b] = 'timeout'
            bot = bots[b]
            for x in range(100):
                line = bot.read_error()
                if line is None:
                    break
                error_lines[b].append(line)
            game.kill_player(bot_nums[b])
            bots[b].kill()

    return bot_moves, error_lines, statuses

########NEW FILE########
__FILENAME__ = gmail
import smtplib
from server_info import server_info

# Uses Gmail to send an email message. This function also work with Google Apps
# (Gmail for your domain) accounts.
#   username: the full email address of the sender (ex: sunflower@gmail.com).
#   password: the gmail password for the sender.
#   recipients: a list of addresses to send the message to. Can also be a
#               single email address.
#   subject: the subject line of the email
#   body: the actual content of the email
#   full_name: the full name of the sender. If this is omitted or has length
#              zero, then the name of the sender will just be the sender's
#              email address.
def send_gmail(username, password, recipients, subject, body, full_name):
  if isinstance(recipients, list):
    recipients = [r for r in recipients if r.find("@") >= 0]
  print recipients
  try:
    if full_name is not None and len(full_name) > 0:
      from_line = full_name + " <" + username + ">"
    else:
      from_line = username  
    message = "From: " + from_line + "\n" + \
      "Subject: " + subject + "\n" + \
      "\n" + body
    smtp_server = smtplib.SMTP("smtp.gmail.com", 587)
    smtp_server.ehlo()
    smtp_server.starttls()
    smtp_server.ehlo()
    smtp_server.login(username, password)
    smtp_server.sendmail(username, recipients, message)
    smtp_server.quit()
    return True
  except Exception, inst:
    return False

# Sends an email message using the email account specified in the
# server_info.txt file. If the message is successfully sent, returns True.
# Otherwise, returns False.
def send(recipients, subject, body):
  mail_username = server_info["mail_username"]
  mail_password = server_info["mail_password"]
  mail_name = server_info["mail_name"]
  return send_gmail(mail_username, \
                    mail_password, \
                    recipients, \
                    subject, \
                    body, \
                    mail_name)

def main():
  print "result: " + \
    str(send("youraddress@yourdomain.com", "Test mail message", "Test!"))

if __name__ == "__main__":
  main()

########NEW FILE########
__FILENAME__ = jailguard
#!/usr/bin/python
# relay stdio to and from subprocess
# send stop and continue signal to subprocess and any processes the child starts

import os
import sys
import time
from Queue import Queue, Empty
from threading import Thread
from signal import SIGSTOP, SIGCONT, SIGKILL
from subprocess import Popen, PIPE

# Seconds between updating potential child processes
_UPDATE_INTERVAL = 0.5

def _get_active_pids():
    return [int(pid) for pid in os.listdir("/proc") if pid.isdigit()]

class Guard(object):
    def __init__(self, args):
        self.checked_pids = set(_get_active_pids())
        self.child_pids = set()
        self.running = True

        self.out_queue = Queue()
        self.child_queue = Queue()
        self.child = Popen(args, stdin=PIPE, stdout=PIPE, stderr=PIPE)
        self.checked_pids.add(self.child.pid)
        self.child_pids.add(self.child.pid)
        self.child_streams = 2
        Thread(target=self.reader, args=("STDOUT", self.child.stdout)).start()
        Thread(target=self.reader, args=("STDERR", self.child.stderr)).start()
        Thread(target=self.writer).start()
        Thread(target=self.child_writer).start()
        cmd_thread = Thread(target=self.cmd_loop, args=(sys.stdin,))
        cmd_thread.daemon = True
        cmd_thread.start()

    def writer(self):
        queue = self.out_queue
        while self.running or self.child_streams or not queue.empty():
            item = queue.get()
            if item:
                sys.stdout.write("%s %f %s\n" % item)
                sys.stdout.flush()

    def reader(self, name, pipe):
        queue = self.out_queue
        try:
            while True:
                ln = pipe.readline()
                if not ln:
                    break
                queue.put((name, time.time(), ln[:-1]))
        finally:
            self.child_streams -= 1
            queue.put(None)

    def child_writer(self):
        queue = self.child_queue
        stdin = self.child.stdin
        while True:
            ln = queue.get()
            if ln is None:
                break
            try:
                stdin.write(ln)
                stdin.flush()
            except IOError as exc:
                if exc.errno == 32:
                    break
                raise

    def signal_children(self, sig):
        cpids = frozenset(self.child_pids)
        for pid in cpids:
            try:
                os.kill(pid, sig)
            except OSError as exc:
                if exc.errno == 3:
                    self.child_pids.remove(pid)
                    self.checked_pids.remove(pid)
                else:
                    raise

    def cmd_loop(self, pipe):
        while True:
            cmd = pipe.readline()
            if not cmd or cmd == "EXIT\n":
                self.kill()
                break
            elif cmd == "STOP\n":
                self.signal_children(SIGSTOP)
                self.out_queue.put(("SIGNALED", time.time(), "STOP"))
            elif cmd == "CONT\n":
                self.signal_children(SIGCONT)
                self.out_queue.put(("SIGNALED", time.time(), "CONT"))
            elif cmd == "KILL\n":
                self.signal_children(SIGKILL)
                self.out_queue.put(("SIGNALED", time.time(), "KILL"))
            elif cmd.startswith("SEND"):
                self.child_queue.put(cmd[5:])
            else:
                self.kill()
                raise ValueError("Unrecognized input found '%s'" % (cmd,))

    def kill(self):
        try:
            self.child.kill()
        except OSError as exc:
            if exc.errno != 3:
                raise
        self.running = False

    def run(self):
        checked = self.checked_pids
        uid = os.getuid()
        while self.child.poll() is None:
            pids = [pid for pid in _get_active_pids() if pid not in checked]
            checked.update(pids)
            cpids = []
            for pid in pids:
                try:
                    if os.stat("/proc/%d" % (pid,)).st_uid == uid:
                        cpids.append(pid)
                except OSError as exc:
                    if exc.errno != 2:
                        raise
            self.child_pids.update(cpids)
            time.sleep(_UPDATE_INTERVAL)
        self.running = False
        self.out_queue.put(None)
        self.child_queue.put(None)

if __name__ == "__main__":
    g = Guard(sys.argv[1:])
    g.run()


########NEW FILE########
__FILENAME__ = release_stale_jails
#!/usr/bin/python
import os
import os.path

CHROOT_PATH = "/srv/chroot"

def main():
    jails = [j for j in os.listdir(CHROOT_PATH) if j.startswith("jailuser")]
    for jail in jails:
        jail_lock = os.path.join(CHROOT_PATH, jail, "locked")
        jail_pid_file = os.path.join(jail_lock, "lock.pid")
        try:
            with open(jail_pid_file) as lock_file:
                lock_pid = int(lock_file.readline())
            print "Found jail %s locked by pid %d." % (jail, lock_pid)
            if not os.path.exists("/proc/%d" % (lock_pid,)):
                print "    jail process does not exist, releasing jail."
                os.unlink(jail_pid_file)
                os.rmdir(jail_lock)
        except IOError as exc:
            if exc.errno != 2:
                raise

if __name__ == "__main__":
    main()


########NEW FILE########
__FILENAME__ = sandbox
#!/usr/bin/python
from __future__ import print_function
import os
import shlex
import signal
import subprocess
import sys
import time
from optparse import OptionParser
from threading import Thread
try:
    from Queue import Queue, Empty
except ImportError:
    from queue import Queue, Empty

# make python 3.x compatible with python 2.x
if sys.version_info >= (3,):
    def unicode(s, errors="strict"):
        if isinstance(s, str):
            return s
        elif isinstance(s, bytes) or isinstance(s, bytearray):
            return s.decode("utf-8", errors)
        raise SandboxError("Tried to convert unrecognized type to unicode")

try:
    from server_info import server_info
    _SECURE_DEFAULT = server_info.get('secure_jail', True)
except ImportError:
    _SECURE_DEFAULT = False

class SandboxError(Exception):
    pass

def _guard_monitor(jail):
    guard_out = jail.command_process.stdout
    while True:
        line = guard_out.readline()
        if not line:
            end_item = (time.time(), None)
            jail.resp_queue.put(end_item)
            jail.stdout_queue.put(end_item)
            jail.stderr_queue.put(end_item)
            break
        line = line.rstrip("\r\n")
        words = line.split(None, 2)
        if len(words) < 3:
            msg, ts = words
            data = ""
        else:
            msg, ts, data = words
        ts = float(ts)
        data = unicode(data, errors="replace")
        if msg == "STDOUT":
            jail.stdout_queue.put((time, data))
        elif msg == "STDERR":
            jail.stderr_queue.put((time, data))
        elif msg == "SIGNALED":
            jail.resp_queue.put((time, data))

class Jail(object):
    """ Provide a secure sandbox to run arbitrary commands in.

    This will only function on specially prepared Ubuntu systems.

    """
    def __init__(self, working_directory):
        """Initialize a new sandbox for the given working directory.

        working_directory: the directory in which the shell command should
                           be launched. Files from this directory are copied
                           into the secure space before the shell command is
                           executed.
        """
        self.locked = False
        jail_base = "/srv/chroot"
        all_jails = os.listdir(jail_base)
        all_jails = [j for j in all_jails if j.startswith("jailuser")]
        for jail in all_jails:
            lock_dir = os.path.join(jail_base, jail, "locked")
            try:
                os.mkdir(lock_dir)
            except OSError:
                # if the directory could not be created, that should mean the
                # jail is already locked and in use
                continue
            with open(os.path.join(lock_dir, "lock.pid"), "w") as pid_file:
                pid_file.write(str(os.getpid()))
            self.locked = True
            self.name = jail
            break
        else:
            raise SandboxError("Could not find an unlocked jail")
        self.jchown = os.path.join(server_info["repo_path"], "worker/jail_own")
        self.base_dir = os.path.join(jail_base, jail)
        self.number = int(jail[len("jailuser"):])
        self.chroot_cmd = "sudo -u {0} schroot -u {0} -c {0} -d {1} -- jailguard.py ".format(
                self.name, "/home/jailuser")

        self._is_alive = False
        self.command_process = None
        self.resp_queue = Queue()
        self.stdout_queue = Queue()
        self.stderr_queue = Queue()
        self._prepare_with(working_directory)

    def __del__(self):
        if self.locked:
            raise SandboxError("Jail object for %s freed without being released"
                    % (self.name))

    @property
    def is_alive(self):
        """Indicates whether a command is currently running in the sandbox"""
        if self._is_alive:
            sub_result = self.command_process.poll()
            if sub_result is None:
                return True
            self._is_alive = False
        return False

    def release(self):
        """Release the sandbox for further use

        Unlocks and releases the jail for reuse by others.
        Must be called exactly once after Jail.is_alive == False.

        """
        if self.is_alive:
            raise SandboxError("Sandbox released while still alive")
        if not self.locked:
            raise SandboxError("Attempt to release jail that is already unlocked")
        if os.system("sudo umount %s" % (os.path.join(self.base_dir, "root"),)):
            raise SandboxError("Error returned from umount of jail %d"
                    % (self.number,))
        lock_dir = os.path.join(self.base_dir, "locked")
        pid_filename = os.path.join(lock_dir, "lock.pid")
        with open(pid_filename, 'r') as pid_file:
            lock_pid = int(pid_file.read())
            if lock_pid != os.getpid():
                # if we ever get here something has gone seriously wrong
                # most likely the jail locking mechanism has failed
                raise SandboxError("Jail released by different pid, name %s, lock_pid %d, release_pid %d"
                        % (self.name, lock_pid, os.getpid()))
        os.unlink(pid_filename)
        os.rmdir(lock_dir)
        self.locked = False

    def _prepare_with(self, command_dir):
        if os.system("%s c %d" % (self.jchown, self.number)) != 0:
            raise SandboxError("Error returned from jail_own c %d in prepare"
                    % (self.number,))
        scratch_dir = os.path.join(self.base_dir, "scratch")
        if os.system("rm -rf %s" % (scratch_dir,)) != 0:
            raise SandboxError("Could not remove old scratch area from jail %d"
                    % (self.number,))
        home_dir = os.path.join(scratch_dir, "home/jailuser")
        os.makedirs(os.path.join(scratch_dir, "home"))
        if os.system("cp -r %s %s" % (command_dir, home_dir)) != 0:
            raise SandboxError("Error copying working directory '%s' to jail %d"
                    % (command_dir, self.number))
        if os.system("sudo mount %s" % (os.path.join(self.base_dir, "root"),)):
            raise SandboxError("Error returned from mount of %d in prepare"
                    % (self.number,))
        if os.system("%s j %d" % (self.jchown, self.number)) != 0:
            raise SandboxError("Error returned from jail_own j %d in prepare"
                    % (self.number,))
        self.home_dir = home_dir
        self.command_dir = command_dir

    def retrieve(self):
        """Copy the working directory back out of the sandbox."""
        if self.is_alive:
            raise SandboxError("Tried to retrieve sandbox while still alive")
        os.system("rm -rf %s" % (self.command_dir,))
        if os.system("%s c %d" % (self.jchown, self.number)) != 0:
            raise SandboxError("Error returned from jail_own c %d in prepare"
                    % (self.number,))
        os.system("cp -r %s %s" % (self.home_dir, self.command_dir))

    def start(self, shell_command):
        """Start a command running in the sandbox"""
        if self.is_alive:
            raise SandboxError("Tried to run command with one in progress.")
        shell_command = self.chroot_cmd + shell_command
        shell_command = shlex.split(shell_command.replace('\\','/'))
        try:
            self.command_process = subprocess.Popen(shell_command,
                                                    stdin=subprocess.PIPE,
                                                    stdout=subprocess.PIPE)
        except OSError:
            raise SandboxError('Failed to start {0}'.format(shell_command))
        self._is_alive = True
        monitor = Thread(target=_guard_monitor, args=(self,))
        monitor.daemon = True
        monitor.start()

    def _signal(self, signal):
        if not self.locked:
            raise SandboxError("Attempt to send %s to unlocked jail" % (signal,))
        result = subprocess.call("sudo -u {0} kill -{1} -1".format(
            self.name, signal), shell=True)
        if result != 0:
            raise SandboxError("Error returned from jail %s sending signal %s"
                    % (self.name, signal))

    def kill(self):
        """Stops the sandbox.

        Stops down the sandbox, cleaning up any spawned processes, threads, and
        other resources. The shell command running inside the sandbox may be
        suddenly terminated.

        """
        try:
            self.command_process.stdin.write("KILL\n")
            self.command_process.stdin.flush()
        except IOError as exc:
            if exc.errno != 32:
                raise
        try:
            item = self.resp_queue.get(timeout=5)
            if item[1] != "KILL" and item[1] is not None:
                raise SandboxError("Bad response from jailguard after kill, %s"
                        % (item,))
        except Empty:
            pass
        self._signal("CONT")
        for i in range(20):
            if self.command_process.poll() != None:
                break
            if i == 10:
                self._signal("KILL")
            time.sleep(0.1)

        # final check to make sure processes are died and raise error if not
        if self.is_alive:
            raise SandboxError("Could not kill sandbox children")

    def pause(self):
        """Pause the process by sending a SIGSTOP to the child"""
        try:
            self.command_process.stdin.write("STOP\n")
            self.command_process.stdin.flush()
        except IOError as exc:
            if exc.errno == 32: # Broken pipe, guard exited
                return
            raise
        item = self.resp_queue.get()
        if item[1] != "STOP" and item[1] is not None:
            raise SandboxError("Bad response from jailguard after pause, %s"
                    % (item,))


    def resume(self):
        """Resume the process by sending a SIGCONT to the child"""
        try:
            self.command_process.stdin.write("CONT\n")
            self.command_process.stdin.flush()
        except IOError as exc:
            if exc.errno == 32: # Broken pipe, guard exited
                return
            raise
        item = self.resp_queue.get()
        if item[1] != "CONT" and item[1] is not None:
            raise SandboxError("Bad response from jailguard after resume, %s"
                    % (item,))

    def write(self, data):
        """Write str to stdin of the process being run"""
        for line in data.splitlines():
            self.write_line(line)

    def write_line(self, line):
        """Write line to stdin of the process being run

        A newline is appended to line and written to stdin of the child process

        """
        if not self.is_alive:
            return False
        try:
            self.command_process.stdin.write("SEND %s\n" % (line,))
            self.command_process.stdin.flush()
        except (OSError, IOError):
            self.kill()

    def read_line(self, timeout=0):
        """Read line from child process

        Returns a line of the child process' stdout, if one isn't available
        within timeout seconds it returns None. Also guaranteed to return None
        at least once after each command that is run in the sandbox.

        """
        if not self.is_alive:
            timeout=0
        try:
            time, line = self.stdout_queue.get(block=True, timeout=timeout)
            return line
        except Empty:
            return None

    def read_error(self, timeout=0):
        """Read line from child process' stderr

        Returns a line of the child process' stderr, if one isn't available
        within timeout seconds it returns None. Also guaranteed to return None
        at least once after each command that is run in the sandbox.

        """
        if not self.is_alive:
            timeout=0
        try:
            time, line = self.stderr_queue.get(block=True, timeout=timeout)
            return line
        except Empty:
            return None

    def check_path(self, path, errors):
        resolved_path = os.path.join(self.home_dir, path)
        if not os.path.exists(resolved_path):
            errors.append("Output file " + str(path) + " was not created.")
            return False
        else:
            return True


def _monitor_file(fd, q):
    while True:
        line = fd.readline()
        if not line:
            q.put(None)
            break
        line = unicode(line, errors="replace")
        line = line.rstrip('\r\n')
        q.put(line)

class House:
    """Provide an insecure sandbox to run arbitrary commands in.

    The sandbox class is used to invoke arbitrary shell commands.
    This class provides the same interface as the secure Sandbox but doesn't
    provide any actual security or require any special system setup.

    """

    def __init__(self, working_directory):
        """Initialize a new sandbox for the given working directory.

        working_directory: the directory in which the shell command should
                           be launched.
        """
        self._is_alive = False
        self.command_process = None
        self.stdout_queue = Queue()
        self.stderr_queue = Queue()
        self.working_directory = working_directory

    @property
    def is_alive(self):
        """Indicates whether a command is currently running in the sandbox"""
        if self._is_alive:
            sub_result = self.command_process.poll()
            if sub_result is None:
                return True
            self.child_queue.put(None)
            self._is_alive = False
        return False

    def start(self, shell_command):
        """Start a command running in the sandbox"""
        if self.is_alive:
            raise SandboxError("Tried to run command with one in progress.")
        working_directory = self.working_directory
        self.child_queue = Queue()
        shell_command = shlex.split(shell_command.replace('\\','/'))
        try:
            self.command_process = subprocess.Popen(shell_command,
                                                    stdin=subprocess.PIPE,
                                                    stdout=subprocess.PIPE,
                                                    stderr=subprocess.PIPE,
                                                    universal_newlines=True,
                                                    cwd=working_directory)
        except OSError:
            raise SandboxError('Failed to start {0}'.format(shell_command))
        self._is_alive = True
        stdout_monitor = Thread(target=_monitor_file,
                                args=(self.command_process.stdout, self.stdout_queue))
        stdout_monitor.daemon = True
        stdout_monitor.start()
        stderr_monitor = Thread(target=_monitor_file,
                                args=(self.command_process.stderr, self.stderr_queue))
        stderr_monitor.daemon = True
        stderr_monitor.start()
        Thread(target=self._child_writer).start()

    def kill(self):
        """Stops the sandbox.

        Shuts down the sandbox, cleaning up any spawned processes, threads, and
        other resources. The shell command running inside the sandbox may be
        suddenly terminated.

        """
        if self.is_alive:
            try:
                self.command_process.kill()
            except OSError:
                pass
            self.command_process.wait()
            self.child_queue.put(None)

    def retrieve(self):
        """Copy the working directory back out of the sandbox."""
        if self.is_alive:
            raise SandboxError("Tried to retrieve sandbox while still alive")
        pass

    def release(self):
        """Release the sandbox for further use

        If running in a jail unlocks and releases the jail for reuse by others.
        Must be called exactly once after Sandbox.kill has been called.

        """
        if self.is_alive:
            raise SandboxError("Sandbox released while still alive")
        pass

    def pause(self):
        """Pause the process by sending a SIGSTOP to the child

        A limitation of the method is it will only pause the initial
        child process created any further (grandchild) processes created
        will not be paused.

        This method is a no-op on Windows.
        """
        try:
            self.command_process.send_signal(signal.SIGSTOP)
        except (ValueError, AttributeError, OSError):
            pass

    def resume(self):
        """Resume the process by sending a SIGCONT to the child

        This method is a no-op on Windows
        """
        try:
            self.command_process.send_signal(signal.SIGCONT)
        except (ValueError, AttributeError, OSError):
            pass

    def _child_writer(self):
        queue = self.child_queue
        stdin = self.command_process.stdin
        while True:
            ln = queue.get()
            if ln is None:
                break
            try:
                stdin.write(ln)
                stdin.flush()
            except (OSError, IOError):
                self.kill()
                break

    def write(self, str):
        """Write str to stdin of the process being run"""
        if not self.is_alive:
            return False
        self.child_queue.put(str)

    def write_line(self, line):
        """Write line to stdin of the process being run

        A newline is appended to line and written to stdin of the child process

        """
        if not self.is_alive:
            return False
        self.child_queue.put(line + "\n")

    def read_line(self, timeout=0):
        """Read line from child process

        Returns a line of the child process' stdout, if one isn't available
        within timeout seconds it returns None. Also guaranteed to return None
        at least once after each command that is run in the sandbox.

        """
        if not self.is_alive:
            timeout=0
        try:
            return self.stdout_queue.get(block=True, timeout=timeout)
        except Empty:
            return None

    def read_error(self, timeout=0):
        """Read line from child process' stderr

        Returns a line of the child process' stderr, if one isn't available
        within timeout seconds it returns None. Also guaranteed to return None
        at least once after each command that is run in the sandbox.

        """
        if not self.is_alive:
            timeout=0
        try:
            return self.stderr_queue.get(block=True, timeout=timeout)
        except Empty:
            return None

    def check_path(self, path, errors):
        resolved_path = os.path.join(self.working_directory, path)
        if not os.path.exists(resolved_path):
            errors.append("Output file " + str(path) + " was not created.")
            return False
        else:
            return True

def get_sandbox(working_dir, secure=None):
    if secure is None:
        secure = _SECURE_DEFAULT
    if secure:
        return Jail(working_dir)
    else:
        return House(working_dir)

def main():
    parser = OptionParser(usage="usage: %prog [options] <command to run>")
    parser.add_option("-d", "--directory", action="store", dest="working_dir",
            default=".",
            help="Working directory to run command in (copied in secure mode)")
    parser.add_option("-l", action="append", dest="send_lines", default=list(),
            help="String to send as a line on commands stdin")
    parser.add_option("-s", "--send-delay", action="store", dest="send_delay",
            type="float", default=0.0,
            help="Time in seconds to sleep after sending a line")
    parser.add_option("-r", "--receive-wait", action="store",
            dest="resp_wait", type="float", default=600,
            help="Time in seconds to wait for another response line")
    parser.add_option("-j", "--jail", action="store_true", dest="secure",
            default=_SECURE_DEFAULT,
            help="Run in a secure jail")
    parser.add_option("-o", "--open", action="store_false", dest="secure",
            help="Run without using a secure jail")
    options, args = parser.parse_args()
    if len(args) == 0:
        parser.error("Must include a command to run.\
                \nRun with --help for more information.")

    print("Using secure sandbox: %s" % (options.secure))
    print("Sandbox working directory: %s" % (options.working_dir))
    sandbox = get_sandbox(options.working_dir, secure=options.secure)
    try:
        print()
        sandbox.start(" ".join(args))
        for line in options.send_lines:
            sandbox.write_line(line)
            print("sent: " + line)
            time.sleep(options.send_delay)
        while True:
            response = sandbox.read_line(options.resp_wait)
            if response is None:
                print()
                print("No more responses. Terminating.")
                break
            print("response: " + response)
        sandbox.kill()
    finally:
        sandbox.release()

if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = semaphore_cleanup

import os
import subprocess
from collections import defaultdict

import MySQLdb
from server_info import server_info

ipcs_proc = subprocess.Popen("ipcs -s", shell=True, stdout=subprocess.PIPE)
ipcs_out, ipcs_err = ipcs_proc.communicate()
ipcs_out = ipcs_out.splitlines()
user_semaphores = defaultdict(list)
for line in ipcs_out:
    values = line.split()
    if len(values) == 5 and values[2].startswith("jailuser"):
        user_semaphores[values[2]].append(values[1])

connection = MySQLdb.connect(host = server_info["db_host"],
        user = server_info["db_username"],
        passwd = server_info["db_password"],
        db = server_info["db_name"])
cursor = connection.cursor(MySQLdb.cursors.DictCursor)
query = "UPDATE jail_users SET in_use = 1 WHERE username = '%s' AND in_use = 0"

for jail_user, semaphores in user_semaphores.items():
    cursor.execute(query % (jail_user,))
    if connection.affected_rows() > 0:
        try:
            for semaphore in semaphores:
                os.system("ipcrm -s "+ semaphore)
        finally:
            cursor.execute(
                    "UPDATE jail_users SET in_use = 0 WHERE username = '%s'" %
                    (jail_user,))

cursor.close()
connection.close()


########NEW FILE########
__FILENAME__ = worker
#!/usr/bin/env python
from __future__ import print_function
import sys
import os
import json
import urllib
import logging.handlers
import logging
import pickle
import shutil
from hashlib import md5
import time
import stat
import platform
import unicodedata
import traceback
import tempfile
from copy import copy, deepcopy

from optparse import OptionParser

from server_info import server_info

import compiler
from engine import run_game

# Set up logging
log = logging.getLogger('worker')
log.setLevel(logging.INFO)
log_file = os.path.join(server_info.get('logs_path', '.'), 'worker.log')
handler = logging.handlers.RotatingFileHandler(log_file,
                                               maxBytes=10000000,
                                               backupCount=5)
handler.setLevel(logging.INFO)
handler2 = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s - " + str(os.getpid()) +
                              " - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
handler2.setFormatter(formatter)
log.addHandler(handler)
log.addHandler(handler2)

handler2 = logging.StreamHandler()


STATUS_CREATED = 10
STATUS_UPLOADED = 20
STATUS_COMPILING = 30
# these 4 will be returned by the worker
STATUS_RUNABLE = 40
STATUS_DOWNLOAD_ERROR = 50
STATUS_UNPACK_ERROR = 60
STATUS_COMPILE_ERROR = 70
STATUS_TEST_ERROR = 80

# get game from ants dir
sys.path.append(os.path.join(server_info.get('repo_path', '..'), 'ants'))
from ants import Ants


def uni_to_ascii(ustr):
    return unicodedata.normalize('NFKD', ustr).encode('ascii','ignore')

class CD(object):
    def __init__(self, new_dir):
        self.new_dir = new_dir

    def __enter__(self):
        self.org_dir = os.getcwd()
        os.chdir(self.new_dir)
        return self.new_dir

    def __exit__(self, type, value, traceback):
        os.chdir(self.org_dir)

class GameAPIClient:
    def __init__(self, base_url, api_key):
        self.base_url = base_url
        self.api_key = api_key

    def get_url(self, method):
        return '%s/%s.php?api_key=%s' % (self.base_url, method, self.api_key)

    def get_task(self):
        try:
            url = self.get_url('api_get_task')
            log.debug(url)
            data = urllib.urlopen(url).read()
            return json.loads(data)
        except ValueError as ex:
            log.error("Bad json from server during get task: %s" % data)
            return None
        except Exception as ex:
            log.error("Get task error: %s" % ex)
            return None

    def get_submission_hash(self, submission_id):
        try:
            url = self.get_url('api_get_submission_hash')
            url += '&submission_id=%s' % submission_id
            data = json.loads(urllib.urlopen(url).read())
            return data['hash']
        except ValueError as ex:
            log.error("Bad json from server during get sumbission hash: %s" % data)
            return None
        except Exception as ex:
            log.error("Get submission hash error: %s" % ex)
            return None

    def get_submission(self, submission_id, download_dir):
        try:
            url = self.get_url('api_get_submission')
            url += '&submission_id=%s' % submission_id
            log.debug(url)
            remote_zip = urllib.urlopen(url)
            filename = remote_zip.info().getheader('Content-disposition')
            if filename == None:
                log.error("File not returned by server: {0}".format(remote_zip.read()))
                return None
            filename = filename.split('filename=')[1]
            filename = os.path.join(download_dir, filename)
            local_zip = open(filename, 'wb')
            local_zip.write(remote_zip.read())
            local_zip.close()
            remote_zip.close()
            return filename
        except Exception as ex:
            log.error(traceback.format_exc())
            log.error("Get submission error: %s" % ex)
            return None

    def get_map(self, map_filename):
        try:
            url = '%s/map/%s' % (self.base_url, map_filename)
            log.info("Downloading map %s" % url)
            data = urllib.urlopen(url).read()
            log.debug(data)
            return data
        except Exception as ex:
            log.error("Get map error: %s" % ex)
            return None

    def post_result(self, method, result):
        # save result in case of failure
        with open('last_post.json', 'w') as f:
            try:
                f.write(json.dumps([method, result]))
            except:
                with open('bad_result', 'w') as br:
                    pickle.dump([method, result], br)
                raise
        # retry 100 times or until post is successful
        retry = 100
        wait_time = 2
        for i in range(retry):
            wait_time = min(wait_time * 2, 300)
            try:
                url = self.get_url(method)
                log.info(url)
                if i == 0:
                    json_log = deepcopy(result)
                    if 'replaydata' in json_log:
                        del json_log['replaydata']
                    json_log = json.dumps(json_log)
                    log.debug("Posting result %s: %s" % (method, json_log))
                else:
                    log.warning("Posting attempt %s" % (i+1))
                json_data = json.dumps(result)
                hash = md5(json_data).hexdigest()
                if i == 0:
                    log.info("Posting hash: %s" % hash)
                response = urllib.urlopen(url, json.dumps(result))
                if response.getcode() == 200:
                    data = response.read()
                    try:
                        log.debug(data.strip())
                        data = json.loads(data)["hash"]
                        log.info("Server returned hash: %s" % data)
                        if hash == data:
                            os.remove('last_post.json')
                            break
                        elif i < retry-1:
                            log.warning('Waiting %s seconds...' % wait_time)
                            time.sleep(wait_time)
                    except ValueError:
                        log.warning("Bad json from server during post result: %s" % data)
                        if i < retry-1:
                            log.warning('Waiting %s seconds...' % wait_time)
                            time.sleep(wait_time)
                else:
                    log.warning("Server did not receive post: %s, %s" % (response.getcode(), response.read()))
                    time.sleep(wait_time)
            except IOError as e:
                log.error(traceback.format_exc())
                log.warning('Waiting %s seconds...' % wait_time)
                time.sleep(wait_time)
        else:
            return False
        return True

class Worker:
    def __init__(self, debug=False):
        self.cloud = GameAPIClient( server_info['api_base_url'], server_info['api_key'])
        self.post_id = 0
        self.test_map = None
        self.download_dirs = {}
        self.debug = debug

    def submission_dir(self, submission_id):
        return os.path.join(server_info["compiled_path"], str(submission_id//1000), str(submission_id))

    def download_dir(self, submission_id):
        if submission_id not in self.download_dirs:
            tmp_dir = tempfile.mkdtemp(dir=server_info["compiled_path"])
            self.download_dirs[submission_id] = tmp_dir
        return self.download_dirs[submission_id]

    def clean_download(self, submission_id):
        if not self.debug and submission_id in self.download_dirs:
            d_dir = self.download_dirs[submission_id]
            log.debug('Cleaning up {0}'.format(d_dir))
            if os.path.exists(d_dir):
                shutil.rmtree(d_dir)
            del self.download_dirs[submission_id]

    def download_submission(self, submission_id):
        submission_dir = self.submission_dir(submission_id)
        if os.path.exists(submission_dir):
            log.info("Already downloaded and compiled: %s..." % submission_id)
            return True
        elif submission_id in self.download_dirs:
            log.info("Already downloaded: %s..." % submission_id)
            return True
        else:
            download_dir = self.download_dir(submission_id)
            log.info("Downloading %s..." % submission_id)
            os.chmod(download_dir, 0755)
            filename = self.cloud.get_submission(submission_id, download_dir)
            if filename != None:
                remote_hash = self.cloud.get_submission_hash(submission_id)
                with open(filename, 'rb') as f:
                    local_hash = md5(f.read()).hexdigest()
                if local_hash != remote_hash:
                    log.error("After downloading submission %s to %s hash didn't match" %
                            (submission_id, download_dir))
                    log.error("local_hash: %s , remote_hash: %s" % (local_hash, remote_hash))
                    shutil.rmtree(download_dir)
                    log.error("Hash error.")
                    return False
                return True
            else:
                shutil.rmtree(download_dir)
                log.error("Submission not found on server.")
                return False

    def unpack(self, submission_id):
        try:
            if submission_id in self.download_dirs:
                download_dir = self.download_dir(submission_id)
            else:
                return False
            log.info("Unpacking %s..." % download_dir)
            with CD(download_dir):
                if platform.system() == 'Windows':
                    zip_files = [
                        ("entry.tar.gz", "7z x -obot -y entry.tar.gz > NUL"),
                        ("entry.tgz", "7z x -obot -y entry.tgz > NUL"),
                        ("entry.zip", "7z x -obot -y entry.zip > NUL")
                    ]
                else:
                    zip_files = [
                        ("entry.tar.gz", "mkdir bot; tar xfz entry.tar.gz -C bot > /dev/null 2> /dev/null"),
                        ("entry.tar.xz", "mkdir bot; tar xfJ entry.tar.xz -C bot > /dev/null 2> /dev/null"),
                        ("entry.tar.bz2", "mkdir bot; tar xfj entry.tar.bz2 -C bot > /dev/null 2> /dev/null"),
                        ("entry.txz", "mkdir bot; tar xfJ entry.txz -C bot > /dev/null 2> /dev/null"),
                        ("entry.tbz", "mkdir bot; tar xfj entry.tbz -C bot > /dev/null 2> /dev/null"),
                        ("entry.tgz", "mkdir bot; tar xfz entry.tgz -C bot > /dev/null 2> /dev/null"),
                        ("entry.zip", "unzip -u -dbot entry.zip > /dev/null 2> /dev/null")
                    ]
                for file_name, command in zip_files:
                    if os.path.exists(file_name):
                        exit_status = os.system(command)
                        log.info("unzip %s, status: %s"
                                % (file_name, exit_status))
                        if exit_status != 0:
                            return False
                        # remove __MACOSX directory
                        mac_path = os.path.join('bot', '__MACOSX')
                        if os.path.exists(mac_path) and os.path.isdir(mac_path):
                            shutil.rmtree(mac_path)
                        # check for single directory only and move everything up
                        unpacked_listing = [p for p in os.listdir('bot')]
                        if len(unpacked_listing) == 1:
                            one_path = os.path.join('bot', unpacked_listing[0])
                            if os.path.isdir(one_path):
                                os.rename(one_path, 'tmp')
                                shutil.rmtree('bot')
                                os.rename('tmp', 'bot')
                        for dirpath, _, filenames in os.walk("."):
                            os.chmod(dirpath, 0755)
                            for filename in filenames:
                                filename = os.path.join(dirpath, filename)
                                os.chmod(filename,stat.S_IMODE(os.stat(filename).st_mode) | stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
                        break
                else:
                    return False
                return True
        except:
            log.error(traceback.format_exc())
            return False

    def compile(self, submission_id=None, report_status=(False, False), run_test=True):
        report_success, report_failure = report_status
        def report(status, language="Unknown", errors=None):
            # oooh, tricky, a terinary in an if
            if report_success if type(errors) != list else report_failure:
                self.post_id += 1
                result = {"post_id": self.post_id,
                          "submission_id": submission_id,
                          "status_id": status,
                          "language": language }
                if status != 40:
                    if type(errors) != list:
                        errors = [errors] # for valid json
                    result['errors'] = json.dumps(errors)
                return self.cloud.post_result('api_compile_result', result)
            else:
                return True
        if submission_id == None:
            # compile in current directory
            compiler.compile_anything(os.getcwd())
        else:
            submission_dir = self.submission_dir(submission_id)
            if os.path.exists(submission_dir):
                log.info("Already compiled: %s" % submission_id)
                if run_test:
                    errors = self.functional_test(submission_id)
                else:
                    errors = None
                if errors == None:
                    if report(STATUS_RUNABLE, compiler.get_run_lang(submission_dir)):
                        return True
                    else:
                        log.debug("Cleanup of compiled dir: {0}".format(submission_dir))
                        shutil.rmtree(submission_dir)
                        return False
                else:
                    report(STATUS_TEST_ERROR, compiler.get_run_lang(submission_dir), errors)
                    log.debug("Cleanup of compiled dir: {0}".format(submission_dir))
                    shutil.rmtree(submission_dir)
                    return False
            if (not submission_id in self.download_dirs or
                len(os.listdir(self.download_dir(submission_id))) == 0):
                if not self.download_submission(submission_id):
                    report(STATUS_DOWNLOAD_ERROR)
                    log.error("Download Error")
                    return False
            download_dir = self.download_dir(submission_id)
            if not os.path.exists(os.path.join(self.download_dir(submission_id),
                                               'bot')):
                if len(os.listdir(download_dir)) == 1:
                    if not self.unpack(submission_id):
                        report(STATUS_UNPACK_ERROR)
                        log.error("Unpack Error")
                        return False
            log.info("Compiling %s " % submission_id)
            bot_dir = os.path.join(download_dir, 'bot')
            timelimit = 10 * 60 # 10 minute limit to compile submission
            if not run_test:
                # give it 50% more time if this isn't the initial compilation
                # this is to try and prevent the situation where the initial
                # compilation just makes it in the time limit and then a
                # subsequent compilation fails when another worker goes to
                # play a game with it
                timelimit += timelimit * 0.5
            detected_lang, errors = compiler.compile_anything(bot_dir,
                    timelimit)
            if errors != None:
                log.error(errors)
                if not self.debug:
                    shutil.rmtree(download_dir)
                log.error(detected_lang)
                report(STATUS_COMPILE_ERROR, detected_lang, errors=errors);
                log.error("Compile Error")
                return False
            else:
                log.info("Detected language: {0}".format(detected_lang))
                if not os.path.exists(os.path.split(submission_dir)[0]):
                    os.makedirs(os.path.split(submission_dir)[0])
                if run_test:
                    errors = self.functional_test(submission_id)
                else:
                    errors = None
                if errors == None:
                    os.rename(download_dir, submission_dir)
                    del self.download_dirs[submission_id]
                    if report(STATUS_RUNABLE, detected_lang):
                        return True
                    else:
                        # could not report back to server, cleanup compiled dir
                        log.debug("Cleanup of compiled dir: {0}".format(submission_dir))
                        shutil.rmtree(submission_dir)
                        return False
                else:
                    log.info("Functional Test Failure")
                    report(STATUS_TEST_ERROR, detected_lang, errors)
                    return False

    def get_map(self, map_filename):
        map_file = os.path.join(server_info["maps_path"], map_filename)
        if not os.path.exists(map_file):
            data = self.cloud.get_map(map_filename)
            if data == None:
                raise Exception("map", "Could not download map from main server.")
            map_dir = os.path.split(map_file)[0]
            if not os.path.exists(map_dir):
                os.makedirs(map_dir)
            f = open(map_file, 'w')
            f.write(data)
            f.close()
        else:
            f = open(map_file, 'r')
            data = f.read()
            f.close()
        return data

    def get_test_map(self):
        if self.test_map == None:
            f = open(os.path.join(server_info['repo_path'],
                                  'ants/submission_test/test.map'), 'r')
            self.test_map = f.read()
            f.close()
        return self.test_map

    def functional_test(self, submission_id):
        self.post_id += 1
        log.info("Running functional test for %s" % submission_id)
        options = copy(server_info["game_options"])
        options['strict'] = True # kills bot on invalid inputs
        options['food'] = 'none'
        options['turns'] = 30
        log.debug(options)
        options["map"] = self.get_test_map()
        options['capture_errors'] = True
        game = Ants(options)
        if submission_id in self.download_dirs:
            bot_dir = self.download_dirs[submission_id]
        else:
            bot_dir = self.submission_dir(submission_id)
        bots = [(os.path.join(bot_dir, 'bot'),
                 compiler.get_run_cmd(bot_dir)),
                (os.path.join(server_info['repo_path'],"ants","submission_test"), "python TestBot.py")]
        log.debug(bots)
        # set worker debug logging
        if self.debug:
            options['verbose_log'] = sys.stdout
            #options['stream_log'] = sys.stdout
            options['error_logs'] = [sys.stderr, sys.stderr]
            # options['output_logs'] = [sys.stdout, sys.stdout]
            # options['input_logs'] = [sys.stdout, sys.stdout]
        result = run_game(game, bots, options)
        if 'status' in result:
            if result['status'][1] in ('crashed', 'timeout', 'invalid'):
                if type(result['errors'][1]) == unicode:
                    errors_str = uni_to_ascii(result['errors'][1])
                else:
                    errors_str = '["'+ '","'.join(uni_to_ascii(e) for e in
                        result['errors'][1]) + '"]'
                msg = 'TestBot is not operational\n' + errors_str
                log.error(msg)
                return msg
            log.info(result['status'][0]) # player 0 is the bot we are testing
            if result['status'][0] in ('crashed', 'timeout', 'invalid'):
                if type(result['errors'][1]) == unicode:
                    errors_str = uni_to_ascii(result['errors'][0])
                else:
                    errors_str = '["'+ '","'.join(uni_to_ascii(e) for e in
                        result['errors'][0]) + '"]'
                log.info(errors_str)
                return result['errors'][0]
        elif 'error' in result:
            msg = 'Function Test failure: ' + result['error']
            log.error(msg)
            return msg
        return None

    def game(self, task, report_status=False):
        self.post_id += 1
        try:
            matchup_id = int(task["matchup_id"])
            log.info("Running game %s..." % matchup_id)
            options = None
            if 'game_options' in task:
                options = task["game_options"]
            if options == None:
                options = copy(server_info["game_options"])
            options["map"] = self.get_map(task['map_filename'])
            options["turns"] = task['max_turns']
            options["output_json"] = True
            game = Ants(options)
            bots = []
            for submission_id in task["submissions"]:
                submission_id = int(submission_id)
                # sometimes the Go bots get marked good,
                # then the Go language is updated and breaks syntax,
                # then they need to be marked as invalid again
                # so this will report status to turn off bots that fail
                #   sometime after they already succeeded
                if self.compile(submission_id, report_status=(False, True), run_test=False):
                    submission_dir = self.submission_dir(submission_id)
                    run_cmd = compiler.get_run_cmd(submission_dir)
                    #run_dir = tempfile.mkdtemp(dir=server_info["compiled_path"])
                    bot_dir = os.path.join(submission_dir, 'bot')
                    bots.append((bot_dir, run_cmd))
                    #shutil.copytree(submission_dir, run_dir)
                else:
                    self.clean_download(submission_id)
                    raise Exception('bot', 'Can not compile bot %s' % submission_id)
            options['game_id'] = matchup_id
            log.debug((game.__class__.__name__, task['submissions'], options, matchup_id))
            # set worker debug logging
            if self.debug:
                options['verbose_log'] = sys.stdout
                replay_log = open('replay.json', 'w')
                options['replay_log'] = replay_log
                #options['stream_log'] = sys.stdout
                options['error_logs'] = [sys.stderr for _ in range(len(bots))]
                # options['output_logs'] = [sys.stdout, sys.stdout]
                # options['input_logs'] = [sys.stdout, sys.stdout]
            options['capture_errors'] = True
            result = run_game(game, bots, options)
            if self.debug:
                replay_log.close()
            log.debug(result)
            if 'game_id' in result:
                del result['game_id']
            result['matchup_id'] = matchup_id
            result['post_id'] = self.post_id
            if report_status:
                return self.cloud.post_result('api_game_result', result)
        except Exception as ex:
            log.error(traceback.format_exc())
            result = {"post_id": self.post_id,
                      "matchup_id": matchup_id,
                      "error": traceback.format_exc() }
            success = self.cloud.post_result('api_game_result', result)
            # cleanup download dirs
            map(self.clean_download, map(int, task['submissions']))
            return success

    def task(self, last=False):
        task = self.cloud.get_task()
        if task:
            try:
                log.info("Received task: %s" % task)
                if task['task'] == 'compile':
                    submission_id = int(task['submission_id'])
                    try:
                        if not self.compile(submission_id, (True, True)):
                            self.clean_download(submission_id)
                        return True
                    except Exception:
                        log.error(traceback.format_exc())
                        self.clean_download(submission_id)
                        return False
                elif task['task'] == 'game':
                    return self.game(task, True)
                else:
                    if not last:
                        time.sleep(20)
                    # prevent worker from stopping on unknown tasks
                    return True
            except:
                log.error('Task Failure')
                log.error(traceback.format_exc())
                quit()
        else:
            log.error("Error retrieving task from server.")

def main(argv):
    usage ="""Usage: %prog [options]\nThe worker will not attempt to retrieve
    tasks from the server if a specifec submission_id is given."""
    parser = OptionParser(usage=usage)
    parser.add_option("-s", "--submission_id", dest="submission_id",
                      type="int", default=0,
                      help="Submission id to use for hash, download and compile")
    parser.add_option("-d", "--download", dest="download",
                      action="store_true", default=False,
                      help="Download submission")
    parser.add_option("-c", "--compile", dest="compile",
                      action="store_true", default=False,
                      help="Compile current directory or submission")
    parser.add_option("-t", "--task", dest="task",
                      action="store_true", default=False,
                      help="Get next task from server")
    parser.add_option("-n", "--num_tasks", dest="num_tasks",
                      type="int", default=1,
                      help="Number of tasks to get from server")
    parser.add_option("--debug", dest="debug",
                      action="store_true", default=False,
                      help="Set the log level to debug")

    (opts, _) = parser.parse_args(argv)
    if opts.debug:
        log.setLevel(logging.DEBUG)
        worker = Worker(True)
    else:
        worker = Worker()

    # if the worker is not run in task mode, it will not clean up the download
    #    dir, so that debugging can be done on what had been downloaded/unzipped

    # download and compile
    if opts.submission_id != 0 and opts.compile:
        worker.compile(opts.submission_id)
        return

    # download submission
    if opts.submission_id != 0 and opts.download:
        if worker.download_submission(opts.submission_id):
            worker.unpack(opts.submission_id)
        return

    # compile submission
    if opts.submission_id != 0 and opts.compile:
        worker.compile(opts.submission_id)
        return

    # compile in current directory
    if opts.compile:
        worker.compile()
        return

    # get tasks
    if opts.task:
        if os.path.exists('last_post.json'):
            log.warning("Last result was not sent successfully, resending....")
            result = None
            with open('last_post.json') as f:
                try:
                    method, result = json.loads(f.read())
                except:
                    log.warning("Last game result file can't be read")
            if result != None:
                if not worker.cloud.post_result(method, result):
                    return False
            else:
                os.remove('last_post.json')
        if opts.num_tasks <= 0:
            try:
                script_loc = os.path.realpath(os.path.dirname(__file__))
                while True:
                    log.info("Getting task infinity + 1")
                    if not worker.task():
                        log.warning("Task failed, stopping worker")
                        break
                    print()
                    if os.path.exists(os.path.join(script_loc, "stop_worker")):
                        log.info("Found worker stop file, exiting.")
                        break
            except KeyboardInterrupt:
                log.info("[Ctrl] + C, Stopping worker")
        else:
            for task_count in range(opts.num_tasks):
                log.info("Getting task %s" % (task_count + 1))
                worker.task((task_count+1)==opts.num_tasks)
                print()
        return

    parser.print_help()

if __name__ == '__main__':
    main(sys.argv[1:])

########NEW FILE########
