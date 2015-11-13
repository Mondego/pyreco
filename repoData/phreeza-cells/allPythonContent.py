__FILENAME__ = cells
#!/usr/bin/env python

import ConfigParser
import random
import sys
import time

import numpy
import pygame, pygame.locals

from terrain.generator import terrain_generator

if not pygame.font: print 'Warning, fonts disabled'

try:
    import psyco
    psyco.full()
except ImportError:
    pass


def get_mind(name):
    full_name = 'minds.' + name
    __import__(full_name)
    mind = sys.modules[full_name]
    mind.name = name
    return mind



STARTING_ENERGY = 20
SCATTERED_ENERGY = 10 

#Plant energy output. Remember, this should always be less
#than ATTACK_POWER, because otherwise cells sitting on the plant edge
#might become invincible.
PLANT_MAX_OUTPUT = 20
PLANT_MIN_OUTPUT = 5

#BODY_ENERGY is the amount of energy that a cells body contains
#It can not be accessed by the cells, think of it as: they can't
#eat their own body. It is released again at death.
BODY_ENERGY  = 25
ATTACK_POWER = 30
#Amount by which attack power is modified for each 1 height difference.
ATTACK_TERR_CHANGE = 2
ENERGY_CAP   = 2500

#SPAWN_COST is the energy it takes to seperate two cells from each other.
#It is lost forever, not to be confused with the BODY_ENERGY of the new cell.
SPAWN_LOST_ENERGY = 20
SUSTAIN_COST      = 0
MOVE_COST         = 1    
#MESSAGE_COST    = 0    

#BODY_ENERGY + SPAWN_COST is invested to create a new cell. What remains is split evenly.
#With this model we only need to make sure a cell can't commit suicide by spawning.
SPAWN_TOTAL_ENERGY = BODY_ENERGY + SPAWN_LOST_ENERGY

TIMEOUT = None

config = ConfigParser.RawConfigParser()


def get_next_move(old_x, old_y, x, y):
    ''' Takes the current position, old_x and old_y, and a desired future position, x and y,
    and returns the position (x,y) resulting from a unit move toward the future position.'''
    dx = numpy.sign(x - old_x)
    dy = numpy.sign(y - old_y)
    return (old_x + dx, old_y + dy)


class Game(object):
    ''' Represents a game between different minds. '''
    def __init__(self, bounds, mind_list, symmetric, max_time, headless = False):
        self.size = self.width, self.height = (bounds, bounds)
        self.mind_list = mind_list
        self.messages = [MessageQueue() for x in mind_list]
        self.headless = headless
        if not self.headless:
            self.disp = Display(self.size, scale=2)
        self.time = 0
        self.clock = pygame.time.Clock()
        self.max_time = max_time
        self.tic = time.time()
        self.terr = ScalarMapLayer(self.size)
        self.terr.set_perlin(10, symmetric)
        self.minds = [m[1].AgentMind for m in mind_list]

        self.show_energy = True
        self.show_agents = True

        self.energy_map = ScalarMapLayer(self.size)
        self.energy_map.set_streak(SCATTERED_ENERGY, symmetric)

        self.plant_map = ObjectMapLayer(self.size)
        self.plant_population = []

        self.agent_map = ObjectMapLayer(self.size)
        self.agent_population = []
        self.winner = None
        if symmetric:
            self.n_plants = 7
        else:
            self.n_plants = 14
            
        # Add some randomly placed plants to the map. 
        for x in xrange(self.n_plants):
            mx = random.randrange(1, self.width - 1)
            my = random.randrange(1, self.height - 1)
            eff = random.randrange(PLANT_MIN_OUTPUT, PLANT_MAX_OUTPUT)
            p = Plant(mx, my, eff)
            self.plant_population.append(p)
            if symmetric:
                p = Plant(my, mx, eff)
                self.plant_population.append(p)
        self.plant_map.lock()
        self.plant_map.insert(self.plant_population)
        self.plant_map.unlock()

        # Create an agent for each mind and place on map at a different plant.
        self.agent_map.lock()
        for idx in xrange(len(self.minds)):
            # BUG: Number of minds could exceed number of plants?
            (mx, my) = self.plant_population[idx].get_pos()
            fuzzed_x = mx
            fuzzed_y = my
            while fuzzed_x == mx and fuzzed_y == my:
                fuzzed_x = mx + random.randrange(-1, 2)
                fuzzed_y = my + random.randrange(-1, 2)
            self.agent_population.append(Agent(fuzzed_x, fuzzed_y, STARTING_ENERGY, idx,
                                               self.minds[idx], None))
            self.agent_map.insert(self.agent_population)
        self.agent_map.unlock()

    def run_plants(self):
        ''' Increases energy at and around (adjacent position) for each plant.
        Increase in energy is equal to the eff(?) value of each the plant.'''
        for p in self.plant_population:
            (x, y) = p.get_pos()
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    adj_x = x + dx
                    adj_y = y + dy
                    if self.energy_map.in_range(adj_x, adj_y):
                        self.energy_map.change(adj_x, adj_y, p.get_eff())


    def add_agent(self, a):
        ''' Adds an agent to the game. '''
        self.agent_population.append(a)
        self.agent_map.set(a.x, a.y, a)

    def del_agent(self, a):
        ''' Kills the agent (if not already dead), removes them from the game and
        drops any load they were carrying in there previously occupied position. '''
        self.agent_population.remove(a)
        self.agent_map.set(a.x, a.y, None)
        a.alive = False
        if a.loaded:
            a.loaded = False
            self.terr.change(a.x, a.y, 1)

    def move_agent(self, a, x, y):
        ''' Moves agent, a, to new position (x,y) unless difference in terrain levels between
        its current position and new position is greater than 4.'''
        if abs(self.terr.get(x, y)-self.terr.get(a.x, a.y)) <= 4:
            self.agent_map.set(a.x, a.y, None)
            self.agent_map.set(x, y, a)
            a.x = x
            a.y = y

    def run_agents(self):
        # Create a list containing the view for each agent in the population.
        views = []
        agent_map_get_small_view_fast = self.agent_map.get_small_view_fast
        plant_map_get_small_view_fast = self.plant_map.get_small_view_fast
        energy_map = self.energy_map
        terr_map = self.terr
        WV = WorldView
        views_append = views.append
        for a in self.agent_population:
            x = a.x
            y = a.y
            agent_view = agent_map_get_small_view_fast(x, y)
            plant_view = plant_map_get_small_view_fast(x, y)
            world_view = WV(a, agent_view, plant_view, terr_map, energy_map)
            views_append((a, world_view))

        # Create a list containing the action for each agent, where each agent
        # determines its actions based on its view of the world and messages 
        # from its team.
        messages = self.messages
        actions = [(a, a.act(v, messages[a.team])) for (a, v) in views]
        actions_dict = dict(actions)
        random.shuffle(actions)

        self.agent_map.lock()
        # Apply the action for each agent - in doing so agent uses up 1 energy unit.
        for (agent, action) in actions:
            #This is the cost of mere survival
            agent.energy -= SUSTAIN_COST

            if action.type == ACT_MOVE: # Changes position of agent.
                act_x, act_y = action.get_data()
                (new_x, new_y) = get_next_move(agent.x, agent.y,
                                               act_x, act_y)
                # Move to the new position if it is in range and it's not 
                #currently occupied by another agent.
                if (self.agent_map.in_range(new_x, new_y) and
                    not self.agent_map.get(new_x, new_y)):
                    self.move_agent(agent, new_x, new_y)
                    agent.energy -= MOVE_COST
            elif action.type == ACT_SPAWN: # Creates new agents and uses additional 50 energy units.
                act_x, act_y = action.get_data()[:2]
                (new_x, new_y) = get_next_move(agent.x, agent.y,
                                               act_x, act_y)
                if (self.agent_map.in_range(new_x, new_y) and
                    not self.agent_map.get(new_x, new_y) and
                    agent.energy >= SPAWN_TOTAL_ENERGY):
                    agent.energy -= SPAWN_TOTAL_ENERGY
                    agent.energy /= 2
                    a = Agent(new_x, new_y, agent.energy, agent.get_team(),
                              self.minds[agent.get_team()],
                              action.get_data()[2:])
                    self.add_agent(a)
            elif action.type == ACT_EAT:
                #Eat only as much as possible.
                intake = min(self.energy_map.get(agent.x, agent.y),
                            ENERGY_CAP - agent.energy)
                agent.energy += intake
                self.energy_map.change(agent.x, agent.y, -intake)
            elif action.type == ACT_RELEASE:
                #Dump some energy onto an adjacent field
                #No Seppuku
                output = action.get_data()[2]
                output = min(agent.energy - 1, output) 
                act_x, act_y = action.get_data()[:2]
                #Use get_next_move to simplyfy things if you know 
                #where the energy is supposed to end up.
                (out_x, out_y) = get_next_move(agent.x, agent.y,
                                               act_x, act_y)
                if (self.agent_map.in_range(out_x, out_y) and
                    agent.energy >= 1):
                    agent.energy -= output
                    self.energy_map.change(out_x, out_y, output)
            elif action.type == ACT_ATTACK:
                #Make sure agent is attacking an adjacent field.
                act_x, act_y = act_data = action.get_data()
                next_pos = get_next_move(agent.x, agent.y, act_x, act_y)
                new_x, new_y = next_pos
                victim = self.agent_map.get(act_x, act_y)
                terr_delta = (self.terr.get(agent.x, agent.y) 
                            - self.terr.get(act_x, act_y))
                if (victim is not None and victim.alive and
                    next_pos == act_data):
                    #If both agents attack each other, both loose double energy
                    #Think twice before attacking 
                    try:
                        contested = (actions_dict[victim].type == ACT_ATTACK)
                    except:
                        contested = False
                    agent.attack(victim, terr_delta, contested)
                    if contested:
                        victim.attack(agent, -terr_delta, True)
                     
            elif action.type == ACT_LIFT:
                if not agent.loaded and self.terr.get(agent.x, agent.y) > 0:
                    agent.loaded = True
                    self.terr.change(agent.x, agent.y, -1)
                    
            elif action.type == ACT_DROP:
                if agent.loaded:
                    agent.loaded = False
                    self.terr.change(agent.x, agent.y, 1)

        # Kill all agents with negative energy.
        team = [0 for n in self.minds]
        for (agent, action) in actions:
            if agent.energy < 0 and agent.alive:
                self.energy_map.change(agent.x, agent.y, BODY_ENERGY)
                self.del_agent(agent)
            else :
                team[agent.team] += 1
            
        # Team wins (and game ends) if opposition team has 0 agents remaining.
        # Draw if time exceeds time limit.
        winner = 0
        alive = 0
        for t in team:
            if t != 0:
                alive += 1
            else:
                if alive == 0:
                    winner += 1
        
        if alive == 1:
            colors = ["red", "white", "purple", "yellow"]
            print "Winner is %s (%s) in %s" % (self.mind_list[winner][1].name, 
                                                colors[winner], str(self.time))
            self.winner = winner
        
        if alive == 0 or (self.max_time > 0 and self.time > self.max_time):
            print "It's a draw!"
            self.winner = -1

        self.agent_map.unlock()
        
    def tick(self):
        if not self.headless:
            # Space starts new game
            # q or close button will quit the game
            for event in pygame.event.get():
                if event.type == pygame.locals.KEYUP:
                    if event.key == pygame.locals.K_SPACE:
                        self.winner = -1
                    elif event.key == pygame.locals.K_q:
                         sys.exit()
                    elif event.key == pygame.locals.K_e:
                         self.show_energy = not self.show_energy
                    elif event.key == pygame.locals.K_a:
                         self.show_agents = not self.show_agents
                elif event.type == pygame.locals.MOUSEBUTTONUP:
                    if event.button == 1:
                        print self.agent_map.get(event.pos[0]/2,
                                                 event.pos[1]/2)
                elif event.type == pygame.QUIT:
                    sys.exit()
            self.disp.update(self.terr, self.agent_population,
                             self.plant_population, self.agent_map,
                             self.plant_map, self.energy_map, self.time,
                             len(self.minds), self.show_energy,
                             self.show_agents)
            
            # test for spacebar pressed - if yes, restart
            for event in pygame.event.get(pygame.locals.KEYUP):
                if event.key == pygame.locals.K_SPACE:
                    self.winner = -1
            if pygame.event.get(pygame.locals.QUIT):
                sys.exit()
            pygame.event.pump()
            self.disp.flip()

        self.run_agents()
        self.run_plants()
        for msg in self.messages:
            msg.update()
        self.time += 1
        self.tic = time.time()
        self.clock.tick()
        if self.time % 100 == 0:
            print 'FPS: %f' % self.clock.get_fps()


class MapLayer(object):
    def __init__(self, size, val=0, valtype=numpy.object_):
        self.size = self.width, self.height = size
        self.values = numpy.empty(size, valtype)
        self.values.fill(val)

    def get(self, x, y):
        if y >= 0 and x >= 0:
            try:
                return self.values[x, y]
            except IndexError:
                return None
        return None

    def set(self, x, y, val):
        self.values[x, y] = val

    def in_range(self, x, y):
        return (0 <= x < self.width and 0 <= y < self.height)


class ScalarMapLayer(MapLayer):
    def set_random(self, range, symmetric = True):
        self.values = terrain_generator().create_random(self.size, range, 
                                                        symmetric)

    def set_streak(self, range, symmetric = True):
        self.values = terrain_generator().create_streak(self.size, range,
                                                        symmetric)

    def set_simple(self, range, symmetric = True):
        self.values = terrain_generator().create_simple(self.size, range,
                                                        symmetric)
    
    def set_perlin(self, range, symmetric = True):
        self.values = terrain_generator().create_perlin(self.size, range,
                                                        symmetric)


    def change(self, x, y, val):
        self.values[x, y] += val


class ObjectMapLayer(MapLayer):
    def __init__(self, size):
        MapLayer.__init__(self, size, None, numpy.object_)
        self.surf = pygame.Surface(size)
        self.surf.set_colorkey((0,0,0))
        self.surf.fill((0,0,0))
        self.pixels = None
#        self.pixels = pygame.PixelArray(self.surf)

    def lock(self):
        self.pixels = pygame.surfarray.pixels2d(self.surf)

    def unlock(self):
        self.pixels = None

    def get_small_view_fast(self, x, y):
        ret = []
        get = self.get
        append = ret.append
        width = self.width
        height = self.height
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if not (dx or dy):
                    continue
                try:
                    adj_x = x + dx
                    if not 0 <= adj_x < width:
                        continue
                    adj_y = y + dy
                    if not 0 <= adj_y < height:
                        continue
                    a = self.values[adj_x, adj_y]
                    if a is not None:
                        append(a.get_view())
                except IndexError:
                    pass
        return ret

    def get_view(self, x, y, r):
        ret = []
        for x_off in xrange(-r, r + 1):
            for y_off in xrange(-r, r + 1):
                if x_off == 0 and y_off == 0:
                    continue
                a = self.get(x + x_off, y + y_off)
                if a is not None:
                    ret.append(a.get_view())
        return ret

    def insert(self, list):
        for o in list:
            self.set(o.x, o.y, o)

    def set(self, x, y, val):
        MapLayer.set(self, x, y, val)
        if val is None:
            self.pixels[x][y] = 0
#            self.surf.set_at((x, y), 0)
        else:
            self.pixels[x][y] = val.color
#            self.surf.set_at((x, y), val.color)


# Use Cython version of get_small_view_fast if available.
# Otherwise, don't bother folks about it.
try:
    import cells_helpers
    import types
    ObjectMapLayer.get_small_view_fast = types.MethodType(
        cells_helpers.get_small_view_fast, None, ObjectMapLayer)
except ImportError:
    pass

TEAM_COLORS = [(255, 0, 0), (255, 255, 255), (255, 0, 255), (255, 255, 0)]
TEAM_COLORS_FAST = [0xFF0000, 0xFFFFFF, 0xFF00FF, 0xFFFF00]

class Agent(object):
    __slots__ = ['x', 'y', 'mind', 'energy', 'alive', 'team', 'loaded', 'color',
                 'act']
    def __init__(self, x, y, energy, team, AgentMind, cargs):
        self.x = x
        self.y = y
        self.mind = AgentMind(cargs)
        self.energy = energy
        self.alive = True
        self.team = team
        self.loaded = False
        self.color = TEAM_COLORS_FAST[team % len(TEAM_COLORS_FAST)]
        self.act = self.mind.act
    def __str__(self):
        return "Agent from team %i, energy %i" % (self.team,self.energy)
    def attack(self, other, offset = 0, contested = False):
        if not other:
            return False
        max_power = ATTACK_POWER + ATTACK_TERR_CHANGE * offset
        if contested:
            other.energy -= min(self.energy, max_power)
        else:
            other.energy -= max_power
        return other.energy <= 0

    def get_team(self):
        return self.team

    def get_pos(self):
        return (self.x, self.y)

    def set_pos(self, x, y):
        self.x = x
        self.y = y

    def get_view(self):
        return AgentView(self)

# Actions available to an agent on each turn.
ACT_SPAWN, ACT_MOVE, ACT_EAT, ACT_RELEASE, ACT_ATTACK, ACT_LIFT, ACT_DROP = range(7)

class Action(object):
    '''
    A class for passing an action around.
    '''
    def __init__(self, action_type, data=None):
        self.type = action_type
        self.data = data

    def get_data(self):
        return self.data

    def get_type(self):
        return self.type


class PlantView(object):
    def __init__(self, p):
        self.x = p.x
        self.y = p.y
        self.eff = p.get_eff()

    def get_pos(self):
        return (self.x, self.y)

    def get_eff(self):
        return self.eff


class AgentView(object):
    def __init__(self, agent):
        (self.x, self.y) = agent.get_pos()
        self.team = agent.get_team()

    def get_pos(self):
        return (self.x, self.y)

    def get_team(self):
        return self.team


class WorldView(object):
    def __init__(self, me, agent_views, plant_views, terr_map, energy_map):
        self.agent_views = agent_views
        self.plant_views = plant_views
        self.energy_map = energy_map
        self.terr_map = terr_map
        self.me = me

    def get_me(self):
        return self.me

    def get_agents(self):
        return self.agent_views

    def get_plants(self):
        return self.plant_views

    def get_terr(self):
        return self.terr_map
    
    def get_energy(self):
        return self.energy_map


class Display(object):
    black = (0, 0, 0)
    red = (255, 0, 0)
    green = (0, 255, 0)
    yellow = (255, 255, 0)

    def __init__(self, size, scale=2):
        self.width, self.height = size
        self.scale = scale
        self.size = (self.width * scale, self.height * scale)
        pygame.init()
        self.screen  = pygame.display.set_mode(self.size)
        self.surface = self.screen
        pygame.display.set_caption("Cells")

        self.background = pygame.Surface(self.screen.get_size())
        self.background = self.background.convert()
        self.background.fill((150,150,150))

        self.text = []

    if pygame.font:
        def show_text(self, text, color, topleft):
            font = pygame.font.Font(None, 24)
            text = font.render(text, 1, color)
            textpos = text.get_rect()
            textpos.topleft = topleft
            self.text.append((text, textpos))
    else:
        def show_text(self, text, color, topleft):
            pass

    def update(self, terr, pop, plants, agent_map, plant_map, energy_map,
               ticks, nteams, show_energy, show_agents):
        # Slower version:
        # img = ((numpy.minimum(150, 20 * terr.values) << 16) +
        #       ((numpy.minimum(150, 10 * terr.values + 10.energy_map.values)) << 8))
         
        r = numpy.minimum(150, 20 * terr.values)
        r <<= 16

#        g = numpy.minimum(150, 10 * terr.values + 10 * energy_map.values)
        if show_energy:
            g = terr.values + energy_map.values
            g *= 10
            g = numpy.minimum(150, g)
            g <<= 8

        img = r
        if show_energy:
            img += g
 #       b = numpy.zeros_like(terr.values)

        img_surf = pygame.Surface((self.width, self.height))
        pygame.surfarray.blit_array(img_surf, img)
        if show_agents:
            img_surf.blit(agent_map.surf, (0,0))
        img_surf.blit(plant_map.surf, (0,0))

        scale = self.scale
        pygame.transform.scale(img_surf,
                               self.size, self.screen)
        if not ticks % 60:
            #todo: find out how many teams are playing
            team_pop = [0] * nteams

            for team in xrange(nteams):
                team_pop[team] = sum(1 for a in pop if a.team == team)

            self.text = []
            drawTop = 0
            for t in xrange(nteams):
                drawTop += 20
                self.show_text(str(team_pop[t]), TEAM_COLORS[t], (10, drawTop))

        for text, textpos in self.text:
            self.surface.blit(text, textpos)

    def flip(self):
        pygame.display.flip()


class Plant(object):
    color = 0x00FF00
 
    def __init__(self, x, y, eff):
        self.x = x
        self.y = y
        self.eff = eff

    def get_pos(self):
        return (self.x, self.y)

    def get_eff(self):
        return self.eff

    def get_view(self):
        return PlantView(self)


class MessageQueue(object):
    def __init__(self):
        self.__inlist = []
        self.__outlist = []

    def update(self):
        self.__outlist = self.__inlist
        self.__inlist = []

    def send_message(self, m):
        self.__inlist.append(m)

    def get_messages(self):
        return self.__outlist


class Message(object):
    def __init__(self, message):
        self.message = message
    def get_message(self):
        return self.message


def main():
    global bounds, symmetric, mind_list
    
    try:
        config.read('default.cfg')
        bounds = config.getint('terrain', 'bounds')
        symmetric = config.getboolean('terrain', 'symmetric')
        minds_str = str(config.get('minds', 'minds'))
    except Exception as e:
        print 'Got error: %s' % e
        config.add_section('minds')
        config.set('minds', 'minds', 'mind1,mind2')
        config.add_section('terrain')
        config.set('terrain', 'bounds', '300')
        config.set('terrain', 'symmetric', 'true')

        with open('default.cfg', 'wb') as configfile:
            config.write(configfile)

        config.read('default.cfg')
        bounds = config.getint('terrain', 'bounds')
        symmetric = config.getboolean('terrain', 'symmetric')
        minds_str = str(config.get('minds', 'minds'))
    mind_list = [(n, get_mind(n)) for n in minds_str.split(',')]

    # accept command line arguments for the minds over those in the config
    try:
        if len(sys.argv)>2:
            mind_list = [(n,get_mind(n)) for n in sys.argv[1:] ]
    except (ImportError, IndexError):
        pass


if __name__ == "__main__":
    main()
    while True:
        game = Game(bounds, mind_list, symmetric, -1)
        while game.winner is None:
            game.tick()

########NEW FILE########
__FILENAME__ = ben
#
#  Benjamin C. Meyer <ben@meyerhome.net>
#
#  Overall rules:
#  Agents at plants reproduce as much as possible
#  Agents are born with a random direction away from the plant
#  Agents send a message with they attack
#  Agents always attack
#  Agents goto the location of the attack, exception scouts that keep looking
#
#  Results
#  Large growing swarm that explores that area for all plants as fast as possible
#  until the enemy is found.  By the time the enemy is found everyone is spread out
#  Once the enemy is found everyone heads in that direction and if there are any
#  plants between the two they are usually taken before they enemy.
#  Once a new plant is reached more are quickly spawned and that plant is overrun
#  From there it is simple attrition
#

import random, cells
import numpy

class MessageType(object):
    ATTACK = 0

class AgentMind(object):
    def __init__(self, args):
        # The direction to walk in
        self.x = False
        # Don't come to the rescue, continue looking for plants & bad guys
        self.scout = (random.random() > 0.9)
        # Once we are attacked (mainly) those reproducing at plants should eat up a defense
        self.defense = 0
        # Don't have everyone walk on the same line to 1) eat as they walk and 2) find still hidden plants easier
        self.step = 0
        # reproduce for at least X children at a plant before going out and attacking
        self.children = 0
        self.my_plant = None
        pass
    def get_available_space_grid(self, me, view):
        grid = numpy.ones((3,3))
        for agent in view.get_agents():
            grid[agent.x - me.x + 1, agent.y - me.y + 1] = 0
        for plant in view.get_plants():
            grid[plant.x - me.x + 1, plant.y - me.y + 1] = 0
        grid[1,1] = 0
        return grid

    def smart_spawn(self, me, view):
        grid = self.get_available_space_grid(me, view)
        for x in xrange(3):
            for y in range(3):
                if grid[x,y]:
                    return (x-1, y-1)
        return (-1, -1)

    def choose_new_direction(self, view) :
        me = view.get_me()
        self.x = random.randrange(view.energy_map.width) - me.x
        self.y = random.randrange(view.energy_map.height) - me.y
        #self.x = random.randrange(-2, 2)
        #self.y = random.randrange(-2, 2)

    def act(self, view, msg):
        if not self.x:
            self.choose_new_direction(view)

        me = view.get_me()
        my_pos = (mx,my) = me.get_pos()

        # Attack anyone next to me, but first send out the distress message with my position
        for a in view.get_agents():
            if (a.get_team() != me.get_team()):
                msg.send_message((MessageType.ATTACK, mx,my))
                if (me.energy > 2000) :
                    spawn_x, spawn_y = self.smart_spawn(me, view)
                    return cells.Action(cells.ACT_SPAWN,(mx+spawn_x, my+spawn_y, self))
                return cells.Action(cells.ACT_ATTACK, a.get_pos())

        # Eat any energy I find until I am 'full'
        if (view.get_energy().get(mx, my) > 0) :
            if (me.energy < 50) :
                return cells.Action(cells.ACT_EAT)
            if (me.energy < self.defense and (random.random()>0.3)):
                return cells.Action(cells.ACT_EAT)

        if (self.scout and me.energy > 1000 and random.random()>0.5):
            spawn_x, spawn_y = self.smart_spawn(me, view)
            return cells.Action(cells.ACT_SPAWN,(mx + spawn_x, my + spawn_y, self))

        # If there is a plant near by go to it and spawn all I can
        if (not self.my_plant) :
            plants = view.get_plants()
            if (len(plants) > 0) :
                self.my_plant = plants[0];
        if (self.my_plant and (self.children < 50 or random.random()>0.9)):
            self.children += 1;
            spawn_x, spawn_y = self.smart_spawn(me, view)
            return cells.Action(cells.ACT_SPAWN,(mx + spawn_x, my + spawn_y, self))

        # If I get the message of help go and rescue!
        map_size = view.energy_map.width
        if (self.step == 0 and True != self.scout and (random.random()>0.2)) :
            ax = 0;
            ay = 0;
            best = view.energy_map.width + view.energy_map.height;
            message_count = len(msg.get_messages());
            for m in msg.get_messages():
                (type, ox,oy) = m
                if (type == MessageType.ATTACK) :
                    dist = max(abs(mx-ax),abs(my-ay))
                    if dist < best:
                        ax = ox
                        ay = oy
                        best = dist
            if (ax != 0 and ay != 0) :
                self.defense = 2000
                self.x = ax - mx
                self.y = ay - my
                if (message_count > 1) :
                    # Attack the base, not the front
                    agent_offset = random.randrange(1, 50)
                    if (self.x > 0) :
                        self.x += agent_offset
                    else :
                        self.x -= agent_offset
                    if (self.y > 0) :
                        self.y += agent_offset
                    else :
                        self.y -= agent_offset
                # Don't stand still once we get there
                if (self.x == 0 and self.y == 0) :
                    self.choose_new_direction(view)
                self.step = random.randrange(3, 10);

        # hit world wall
        if mx <= 0 or mx >= map_size-1 or my <= 0 or my >= map_size-1 :
            self.choose_new_direction(view)

        # Back to step 0 we can change direction at the next attack
        if (self.step > 0):
            self.step -= 1;

        # Move quickly randomly in my birth direction
        return cells.Action(cells.ACT_MOVE,(mx+self.x+random.randrange(-1,1),my+self.y+random.randrange(-1,1)))

########NEW FILE########
__FILENAME__ = ben2
#
# Copyright (c) 2010, Benjamin C. Meyer <ben@meyerhome.net>
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
# 3. Neither the name of the Benjamin Meyer nor the names of its contributors
#    may be used to endorse or promote products derived from this software
#    without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE REGENTS AND CONTRIBUTORS ``AS IS'' AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE REGENTS OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS
# OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
# OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
# SUCH DAMAGE.
#

#
#  Idea:
#  Keep track of how long we have been alive relative to our plant.
#  The more time has past, the farther away we will go on a rescue mission and
#  the more energy we will gather before heading out
#
#  Result:
#  strong cells have a good chance of making it to another plant where there
#  are many attacks one after another causing the battle line to shift to a plant
#
#  At the start (weak) cells goto closer attacks and not far away
#  At the end (strong) cells are sent straight to the (far away) attacking area
#

import random, cells
import cmath, numpy

class Type:
  PARENT  = 0
  SCOUT   = 1

class MessageType:
    ATTACK     = 0
    FOUNDPLANT = 1

class AgentMind:
  def __init__(self, args):
    self.id = 0
    self.time = 0

    self.type = Type.SCOUT
    # scout vars
    self.x = None
    self.y = None
    self.search = (random.random() > 0.9) # AKA COW, mostly just go and eat up the world grass so the other team can't
    self.last_pos = (-1,-1)
    self.bumps = 0
    self.step = 0
    self.rescue = None
    # parent vars
    self.children = 0
    self.plant = None
    self.plants = []
    if args:
        parent = args[0]
        self.time = parent.time
        self.plants = parent.plants
        if len(self.plants) > 7:
            self.id = random.randrange(0,1)
        if parent.search:
            self.search = (random.random() > 0.2)
    pass

  def choose_new_direction(self, view, msg):
    me = view.get_me()
    self.x = random.randrange(-9,9)
    self.y = random.randrange(-9,9)
    if self.x == 0 and self.y == 0:
        self.choose_new_direction(view, msg)
    self.step = 3
    self.bumps = 0

  def act_scout(self, view, msg):
    me = view.get_me()
    if self.x is None:
        self.choose_new_direction(view, msg)

    currentEnergy = view.get_energy().get(me.x, me.y)

    # Grabbing a plant is the most important thing, we get this we win
    plants = view.get_plants()
    if plants :
        plant = (plants[0]).get_pos()
        if plant != self.plant:
            if self.plants.count(plant) == 0:
                #print "Found a new plant, resetting time: " + str(len(self.plants))
                msg.send_message((MessageType.FOUNDPLANT, 0, self.id, me.x, me.y))
                self.plants.append(plant)
                self.time = 0
            self.plant = plant
            self.type = Type.PARENT
            self.search = None
            #print str(len(self.plants)) + " " + str(me.get_team())
            return self.act_parent(view, msg)
    else:
        # Don't let this go to waste
        if currentEnergy >= 3:
            return cells.Action(cells.ACT_EAT)

    if self.search:
        if me.energy > 100:
            spawn_x, spawn_y = self.smart_spawn(me, view)
            return cells.Action(cells.ACT_SPAWN, (me.x + spawn_x, me.y + spawn_y, self))
        if (currentEnergy > 3) :
            return cells.Action(cells.ACT_EAT)

    # Make sure we wont die
    if (me.energy < 25 and currentEnergy > 1) :
        return cells.Action(cells.ACT_EAT)

    # hit world wall, bounce back
    map_size = view.energy_map.width
    if me.x <= 0 or me.x >= map_size-1 or me.y <= 0 or me.y >= map_size-1 :
        self.choose_new_direction(view, msg)

    # If I get the message of help go and rescue!
    if self.step == 0 and (not self.search) and (random.random()>0.2):
        ax = 0;
        ay = 0;
        best = 300 + self.time / 2
        message_count = len(msg.get_messages());
        for m in msg.get_messages():
            (type, count, id, ox, oy) = m
            if (id == self.id and type == MessageType.ATTACK) :
                dist = abs(me.x-ax) + abs(me.y-ay)
                if count >= 2:
                    dist /= count
                if dist < best and dist > 1:
                    ax = ox
                    ay = oy
                    best = dist
        if (ax != 0 and ay != 0) :
            dir = ax-me.x + (ay - me.y) * 1j
            r, theta = cmath.polar(dir)
            theta += 0.1 * random.random() - 0.5
            dir =  cmath.rect(r, theta)
            self.x = dir.real
            self.y = dir.imag
            # if (message_count > 1) :
            #     # Attack the base, not the front
            #     agent_scale = 1 + random.random()
            #     self.x *= agent_scale
            #     self.y *= agent_scale
            # don't stand still once we get there
            if (self.x == 0 and self.y == 0) :
                self.x = random.randrange(-2, 2)
                self.y = random.randrange(-2, 2)

            self.step = random.randrange(1, min(30, max(2,int((best+2)/2))))
            self.rescue = True

    if not self.rescue and me.energy > cells.SPAWN_MIN_ENERGY and me.energy < 100:
        spawn_x, spawn_y = self.smart_spawn(me, view)
        return cells.Action(cells.ACT_SPAWN,(me.x + spawn_x, me.y + spawn_y, self))

    # Back to step 0 we can change direction at the next attack.
    if self.step:
        self.step -= 1

    return self.smart_move(view, msg)

  def get_available_space_grid(self, me, view):
    grid = numpy.ones((3,3))
    grid[1,1] = 0
    for agent in view.get_agents():
      grid[agent.x - me.x + 1, agent.y - me.y + 1] = 0
    for plant in view.get_plants():
      grid[plant.x - me.x + 1, plant.y - me.y + 1] = 0
    return grid

  def smart_move(self, view, msg):
    me = view.get_me()

    # make sure we can actually move
    if me.get_pos() == self.last_pos:
      self.bumps += 1
    else:
      self.bumps = 0
    if self.bumps >= 2:
        self.choose_new_direction(view, msg)
    self.last_pos = view.me.get_pos()

    offsetx = 0
    offsety = 0
    if self.search:
        offsetx = random.randrange(-1, 1)
        offsety = random.randrange(-1, 1)

    wx = me.x + self.x + offsetx
    wy = me.y + self.y + offsety

    grid = self.get_available_space_grid(me, view)

    bestEnergy = 2
    bestEnergyX = -1
    bestEnergyY = -1

    for x in xrange(3):
      for y in range(3):
        if grid[x,y]:
            e = view.get_energy().get(me.x + x-1, me.y + y-1)
            if e > bestEnergy:
                bestEnergy = e;
                bestEnergyX = x
                bestEnergyY = y;

    # Check the desired location first
    if (wx <  me.x) : bx = 0
    if (wx == me.x) : bx = 1
    if (wx >  me.x) : bx = 2
    if (wy <  me.y) : by = 0
    if (wy == me.y) : by = 1
    if (wy >  me.y) : by = 2
    if bx == bestEnergyX and bestEnergy > 1:
        return cells.Action(cells.ACT_MOVE,(me.x + bestEnergyX-1, me.y + bestEnergyY-1))
    if by == bestEnergyY and bestEnergy > 1:
        return cells.Action(cells.ACT_MOVE,(me.x + bestEnergyX-1, me.y + bestEnergyY-1))

    if grid[bx,by]:
        return cells.Action(cells.ACT_MOVE,(wx, wy))

    if bestEnergy > 1:
        return cells.Action(cells.ACT_MOVE,(me.x + bestEnergyX-1, me.y + bestEnergyY-1))

    if grid[2,0] and random.random() > 0.5:
        return cells.Action(cells.ACT_MOVE,(me.x + 1, me.y - 1))

    for x in xrange(3):
      for y in range(3):
        if grid[x,y]:
            return cells.Action(cells.ACT_MOVE,(x-1, y-1))
    return cells.Action(cells.ACT_MOVE,(wx, wy))

  def smart_spawn(self, me, view):
    grid = self.get_available_space_grid(me, view)

    # So we don't always spawn in our top left
    if grid[2,0] and random.random() > 0.8:
        return (1, -1)

    for x in xrange(3):
      for y in range(3):
        if grid[x,y]:
          return (x-1, y-1)
    return (-1, -1)

  def should_attack(self, view, msg):
        me = view.get_me()
        count = 0
        for a in view.get_agents():
            if a.get_team() != me.get_team():
                count += 1
        if count > 0:
            currentEnergy = view.get_energy().get(me.x, me.y)
            if currentEnergy > 20:
                return cells.Action(cells.ACT_EAT)
            if self.plant:
                count = 10
            msg.send_message((MessageType.ATTACK, count, self.id, me.x, me.y))
            return cells.Action(cells.ACT_ATTACK, a.get_pos())
        return None

  def check(self, x, y, view):
    plant_pos = (px, py) = self.plant
    me = view.get_me()
    oldx = x
    oldy = y
    x += me.x
    y += me.y
    # Make sure the plant is always populated
    grid = self.get_available_space_grid(me, view)
 
    if abs(px - x) <= 1 and abs(py - y) <= 1:
        grid = self.get_available_space_grid(me, view)
        if grid[oldx+1, oldy+1] == 1:
            #print str(x) + " " + str(y) + " " + str(abs(px - x)) + " " + str(abs(py - y))
            return True
    return None

  def act_parent(self, view, msg):
    me = view.get_me()
    plant_pos = (px, py) = self.plant

    # Make sure the plant is always populated
    grid = self.get_available_space_grid(me, view)
    xoffset = -2
    yoffset = -2
    if self.check( 1,  0, view):  xoffset = 1;  yoffset = 0;  # right
    if self.check(-1,  0, view):  xoffset = -1; yoffset = 0;  # left
    if self.check( 0,  1, view):  xoffset = 0;  yoffset = 1;  # down
    if self.check( 0, -1, view):  xoffset = 0;  yoffset = -1; # up
    if self.check( -1, -1, view): xoffset = -1; yoffset = -1; # diag left
    if self.check( -1, 1, view):  xoffset = -1; yoffset = 1; # diag right
    if self.check( 1, -1, view):  xoffset = 1;  yoffset = -1;  # diag left
    if self.check( 1, 1, view):   xoffset = 1;  yoffset = 1;  # diag right
    if xoffset != -2:
        if me.energy < cells.SPAWN_MIN_ENERGY : return cells.Action(cells.ACT_EAT)
        # When we are populating plant cells we must spawn some children in case we are being attacked
        # When we are all alone we don't spawn any cheap children and only do high quality cells
        self.children += 1
        return cells.Action(cells.ACT_SPAWN, (me.x + xoffset, me.y + yoffset, self))

    # When there are more then two plants always charge up and then leave
    # when there are less then two plants only half of the cells should charge up and then leave
    if self.children <= 0:
        if me.energy >= cells.ENERGY_CAP or me.energy > cells.SPAWN_MIN_ENERGY + self.time + random.randrange(-10,100):
            self.type = Type.SCOUT
            return self.act_scout(view, msg)
        return cells.Action(cells.ACT_EAT)

    if me.energy < cells.SPAWN_MIN_ENERGY :
        return cells.Action(cells.ACT_EAT)
    self.children -= 1
    spawn_x, spawn_y = self.smart_spawn(me, view)
    return cells.Action(cells.ACT_SPAWN,(me.x + spawn_x, me.y + spawn_y, self))

  def act(self, view, msg):
    self.time += 1
    r = self.should_attack(view, msg)
    if r: return r

    if self.type == Type.PARENT:
        return self.act_parent(view, msg)
    if self.type == Type.SCOUT:
        return self.act_scout(view, msg)

########NEW FILE########
__FILENAME__ = benmark
#
#  Benjamin C. Meyer, improved by Mark O'Connor
#
#  Overall rules:
#  Agents at plants reproduce as much as possible
#  Agents are born with a random direction away from the plant
#  Agents send a message with they attack
#  Agents love to eat and reproduce (this is really brutal in long battles)
#  Agents always attack
#  Agents go to the location of the attack, exception scouts that keep looking
#  After a while the AI gets bored and rushes the enemy. Then it rests for a 
#  while and tries again.
#
#  Results
#  Grab plants quickly without being distracted by nearby enemies
#  Quickly convert battlefields into huge swarms of our cells
#  Once we think we've done enough expanding, make a concerted push at the enemy
#  Relax this after gaining some ground and build up more forces before a final push
#  Obliterates the standard AIs, ben and benvolution
#
#  There is clearly a lot of room for improvement in plant finding, battle tactics
#  and energy management.

import random, cells, numpy
from math import sqrt

armageddon_declared = False

class MessageType:
    ATTACK = 0

class AgentMind:
    def __init__(self, parent_args):
        if parent_args == None: # initial instance
            self.game_age = 0
        else:
            self.game_age = parent_args[0].game_age
        # The direction to walk in
        self.x = random.randrange(-3,4)
        self.y = random.randrange(-3,4)
        # Don't come to the rescue, continue looking for plants & bad guys
        self.scout = random.randrange(0, self.game_age+1) < 200
        # Once we are attacked (mainly) those reproducing at plants should eat up a defense
        self.defense = 0
        # Don't have everyone walk on the same line to 1) eat as they walk and 2) find still hidden plants easier
        self.step = 0
        self.age = 0
        # reproduce for at least X children at a plant before going out and attacking
        self.children = 0
        self.my_plant = None
        self.bumps = 0
        self.last_pos = (-1, -1)

    def get_available_spaces(self, me, view):
        x, y = me.get_pos()
        agents = set((a.x - x, a.y - y) for a in view.get_agents())
        plants = set((p.x - x, p.y - y) for p in view.get_plants())
        my_pos = set((0, 0))
        all = set((x,y) for x in xrange(-1, 2) for y in xrange(-1, 2))
        return all - agents - plants - my_pos

    def smart_spawn(self, me, view):
        free = self.get_available_spaces(me, view)
        if len(free)>0:
            return free.pop()
        else:
            return None

    def act(self, view, msg):
        ret = self.act_wrapper(view, msg)
        self.last_pos = view.me.get_pos()
        return ret

    def act_wrapper(self, view, msg):
        global armageddon_declared
        me = view.get_me()
        my_pos = (mx,my) = me.get_pos()
        # after a while, armageddon!
        self.age += 1
        self.game_age += 1
        bored = (view.energy_map.width+view.energy_map.height)
        if self.game_age > bored and self.game_age <= bored*2 or self.game_age > bored*2.5:
            self.scout = False
            if not armageddon_declared:
                print "Mark declares armageddon!"
                armageddon_declared = True
        if self.game_age > bored*2 and self.game_age < bored*2.5 and armageddon_declared: 
            print "Mark calls armageddon off..."
            armageddon_declared = False
    
        # Attack anyone next to me, but first send out the distress message with my position
        target = next((a for a in view.get_agents() if a.get_team() != me.get_team()), None)
        if target:
            msg.send_message((MessageType.ATTACK, mx, my))
            return cells.Action(cells.ACT_ATTACK, target.get_pos())
    
        # Eat any energy I find until I am 'full'
        if view.get_energy().get(mx, my) > 0:
            if (me.energy < 50):
                return cells.Action(cells.ACT_EAT)
            if (me.energy < self.defense):# and (random.random()>0.1)):
               return cells.Action(cells.ACT_EAT)
    
        # If there is a plant near by go to it and spawn all I can
        if not self.my_plant and len(view.get_plants())>0:
            self.my_plant = view.get_plants()[0]
        if self.my_plant:
            pos = self.smart_spawn(me, view)
            if pos:
                return cells.Action(cells.ACT_SPAWN, (me.x + pos[0], me.y + pos[1], self))
    
        if me.energy > 50 or (armageddon_declared and me.energy > 400):
            pos = self.smart_spawn(me, view)
            if pos:
                return cells.Action(cells.ACT_SPAWN, (me.x + pos[0], me.y + pos[1], self))
    
        # If I get the message of help go and rescue!
        if (self.step == 0 and (random.random()>0.2)) :
            calls_to_arms = [((mx-ox)**2+(my-oy)**2, ox, oy) for t, ox, oy in msg.get_messages() if t == MessageType.ATTACK]
            if len(calls_to_arms)>0:
                best, ox, oy = min(calls_to_arms)
                if not self.scout or best < min(self.game_age, (view.energy_map.width/8)**2):
                    self.defense = 2000
                    self.x = ox - mx
                    self.y = oy - my
                    if (len(calls_to_arms) > 1) :
                        # Attack the base, not the front
                        agent_offset = random.randrange(1, view.energy_map.width/6)
                        if (self.x > 0) :
                            self.x += agent_offset
                        else :
                            self.x -= agent_offset
                        if (self.y > 0) :
                            self.y += agent_offset
                        else :
                            self.y -= agent_offset
                        # don't all aim directly at the target
                        roam = int(sqrt(best))
                        if roam > 1:
                            self.x += random.randrange(-roam, roam+1)
                            self.y += random.randrange(-roam, roam+1)
                    # Don't stand still once we get there
                    if (self.x == 0 and self.y == 0) :
                        self.x = random.randrange(-3, 4)
                        self.y = random.randrange(-3, 4)
                    self.step = random.randrange(3, 30)
    
        # don't get stuck and die 
        if self.bumps >= 2:
            self.x = random.randrange(-3,4)
            self.y = random.randrange(-3,4)
            self.bumps = 0
    
        # hit world wall
        if (mx == 0 or mx == view.energy_map.width-1):
            self.scout = False
            self.x *= -1
            self.bumps = 0
        if (my == 0 or my == view.energy_map.height-1):
            self.scout = False
            self.y *= -1
            self.bumps = 0
    
        # Back to step 0 we can change direction at the next attack
        if (self.step > 0):
            self.step -= 1;
    
        # Move quickly randomly in my birth direction
        return cells.Action(cells.ACT_MOVE,(mx+self.x+random.randrange(-1,2),my+self.y+random.randrange(-1,2)))

########NEW FILE########
__FILENAME__ = benvolution
#
#  Benjamin C. Meyer
#  Modified by Scott Wolchok
#
#  Overall rules:
#  Agents at plants reproduce as much as possible
#  Agents are born with a random direction away from the plant
#  Agents send a message with they attack
#  Agents always attack
#  Agents goto the location of the attack, exception scouts that keep looking
#
#  Results
#  Large growing swarm that explores that area for all plants as fast as possible
#  until the enemy is found.  By the time the enemy is found everyone is spread out
#  Once the enemy is found everyone heads in that direction and if there are any
#  plants between the two they are usually taken before they enemy.
#  Once a new plant is reached more are quickly spawned and that plant is overrun
#  From there it is simple attrition
#

import cmath
import random, cells

import numpy

import genes

class MessageType(object):
    ATTACK = 0

class AgentMind(object):
    def __init__(self, args):
        # The direction to walk in
        self.x = None
        # Once we are attacked (mainly) those reproducing at plants should eat up a defense.
        self.defense = 0

        self.step = 0
        self.my_plant = None
        self.bumps = 0
        self.last_pos = (-1, -1)

        if args is None:
            self.strain = 0
            self.scout = False
        else:
            parent = args[0]
            self.strain = parent.strain
            # Don't come to the rescue, continue looking for plants & bad guys.
            if parent.my_plant:
                self.scout = (random.random() > 0.9)
            else:
                self.scout = False


    def get_available_space_grid(self, me, view):
        grid = numpy.ones((3,3))
        for agent in view.get_agents():
            grid[agent.x - me.x + 1, agent.y - me.y + 1] = 0
        for plant in view.get_plants():
            grid[plant.x - me.x + 1, plant.y - me.y + 1] = 0
        grid[1,1] = 0
        return grid

    def smart_spawn(self, me, view):
        grid = self.get_available_space_grid(me, view)
        for x in xrange(3):
            for y in range(3):
                if grid[x,y]:
                    return (x-1, y-1)
        return (-1, -1)

    def would_bump(self, me, view, dir_x, dir_y):
        grid = self.get_available_space_grid(me, view)
        dx = numpy.sign(dir_x)
        dy = numpy.sign(dir_y)
        adj_dx = dx + 1
        adj_dy = dy + 1
        return grid[adj_dx,adj_dy] == 0


    def act(self, view, msg):
        ret = self.act_wrapper(view, msg)
        self.last_pos = view.me.get_pos()
        return ret

    def act_wrapper(self, view, msg):
        me = view.get_me()
        my_pos = (mx,my) = me.get_pos()
        if my_pos == self.last_pos:
            self.bumps += 1
        else:
            self.bumps = 0

        if self.x is None:
            self.x = random.randrange(view.energy_map.width) - me.x
            self.y = random.randrange(view.energy_map.height) - me.y
        # Attack anyone next to me, but first send out the distress message with my position
        for a in view.get_agents():
            if (a.get_team() != me.get_team()):
                msg.send_message((self.strain, MessageType.ATTACK, mx,my))
                return cells.Action(cells.ACT_ATTACK, a.get_pos())

        # Eat any energy I find until I am 'full'. The cost of eating
        # is 1, so don't eat just 1 energy.
        if view.get_energy().get(mx, my) > 1:
            if (me.energy <= 50):
                return cells.Action(cells.ACT_EAT)
            if (me.energy < self.defense and (random.random()>0.3)):
                return cells.Action(cells.ACT_EAT)


        # If there is a plant near by go to it and spawn all I can
        if self.my_plant is None :
            plants = view.get_plants()
            if plants :
                self.my_plant = plants[0]
                self.x = self.y = 0
                self.strain = self.my_plant.x * 41 + self.my_plant.y

        # Current rules don't make carrying around excess energy
        # worthwhile.  Generates a very nice "They eat their
        # wounded?!" effect. Also burns extra energy so the enemy
        # can't use it.
        # Spawning takes 25 of the energy and gives it
        # to the child and reserves the other 25 for the child's death
        # drop. In addition, the action costs 1 unit. Therefore, we
        # can't create energy by spawning...
        if me.energy >= 51:
            spawn_x, spawn_y = self.smart_spawn(me, view)
            return cells.Action(cells.ACT_SPAWN,
                                (me.x + spawn_x, me.y + spawn_y, self))

        # If I get the message of help go and rescue!
        if not self.step and not self.scout and random.random() > 0.1:
            ax = 0;
            ay = 0;
            best = 500;
            message_count = len(msg.get_messages());
            for m in msg.get_messages():
                (strain, type, ox,oy) = m
                if strain != self.strain:
                    continue
                if (type == MessageType.ATTACK) :
                    dist = max(abs(mx-ax), abs(my-ay))
                    if dist < best:
                        ax = ox
                        ay = oy
                        best = dist
            if ax and ay:
                self.defense = 200
                dir = ax-mx + (ay - my) * 1j
                r, theta = cmath.polar(dir)
                theta += 0.02 * random.random() - 0.5
                dir =  cmath.rect(r, theta)
                self.x = dir.real
                self.y = dir.imag
                # if (message_count > 1) :
                #     # Attack the base, not the front
                #     agent_scale = 1 + random.random()
                #     self.x *= agent_scale
                #     self.y *= agent_scale
                # don't stand still once we get there
                if (self.x == 0 and self.y == 0) :
                    self.x = random.randrange(-1, 2)
                    self.y = random.randrange(-1, 2)
                self.step = random.randrange(20, 100);

        if self.bumps >= 2:
            self.x = random.randrange(-3,4)
            self.y = random.randrange(-3,4)
            self.bumps = 0


        # hit world wall
        map_size = view.energy_map.width
        if (mx == 0 or mx == map_size-1) :
            self.x = random.randrange(-1,2)
        if (my == 0 or my == map_size-1) :
            self.y = random.randrange(-1,2)

        # Back to step 0 we can change direction at the next attack.
        if self.step:
            self.step -= 1

        return cells.Action(cells.ACT_MOVE,(mx+self.x,my+self.y))

########NEW FILE########
__FILENAME__ = benvolution_genetic
#
#  Benjamin C. Meyer
#  Modified by Scott Wolchok
#
#  Overall rules:
#  Agents at plants reproduce as much as possible
#  Agents are born with a random direction away from the plant
#  Agents send a message with they attack
#  Agents always attack
#  Agents goto the location of the attack, exception scouts that keep looking
#
#  Results
#  Large growing swarm that explores that area for all plants as fast as possible
#  until the enemy is found.  By the time the enemy is found everyone is spread out
#  Once the enemy is found everyone heads in that direction and if there are any
#  plants between the two they are usually taken before they enemy.
#  Once a new plant is reached more are quickly spawned and that plant is overrun
#  From there it is simple attrition
#

import cells

from cells import Action
from cells import ACT_SPAWN, ACT_MOVE, ACT_EAT, ACT_RELEASE, ACT_ATTACK
from cells import ACT_LIFT, ACT_DROP

import cmath
from random import choice, random, randrange

import numpy

from genes import InitializerGene, make_normally_perturbed_gene


DesiredEnergyGene = make_normally_perturbed_gene(5, cells.ATTACK_POWER,
                                                 cells.ENERGY_CAP)
FieldSpawnEnergyGene = make_normally_perturbed_gene(5, cells.SPAWN_MIN_ENERGY,
                                                    cells.ENERGY_CAP)
PlantSpawnEnergyGene = make_normally_perturbed_gene(5, cells.SPAWN_MIN_ENERGY,
                                                    cells.ENERGY_CAP)


def debug(s):
    #print s
    pass

class MessageType(object):
    ATTACK = 0

size = 300 #cells.config.getint('terrain', 'bounds')

class AgentMind(object):
    def __init__(self, args):
        # The direction to walk in
        self.tx = randrange(size)
        self.ty = randrange(size)

        self.step = 0
        self.my_plant = None
        self.apoptosis = randrange(100, 201)

        if args is None:
            self.strain = 0
            self.scout = False
            self.genes = genes = {}
            genes['desired_energy'] = DesiredEnergyGene(
                InitializerGene(2 * cells.SPAWN_MIN_ENERGY))
            genes['field_spawn_energy'] = FieldSpawnEnergyGene(
                InitializerGene(4 * cells.ENERGY_CAP / 5))
            genes['plant_spawn_energy'] = PlantSpawnEnergyGene(
                InitializerGene(2 * cells.SPAWN_MIN_ENERGY))
        else:
            parent = args[0]
            self.strain = parent.strain
            # Don't come to the rescue, continue looking for plants & bad guys.
            self.genes = dict((k, v.spawn()) for (k,v) in parent.genes.iteritems())
            if parent.my_plant is not None:
                self.scout = (random() > 0.9)
            else:
                self.scout = False


    def get_available_space_grid(self, me, view):
        grid = numpy.ones((3,3))
        for agent in view.get_agents():
            grid[agent.x - me.x + 1, agent.y - me.y + 1] = 0
        for plant in view.get_plants():
            grid[plant.x - me.x + 1, plant.y - me.y + 1] = 0
        grid[1,1] = 0
        return grid

    def smart_spawn(self, me, view):
        grid = self.get_available_space_grid(me, view)
        ret = []
        for x in xrange(3):
            for y in range(3):
                if grid[x,y]:
                    ret.append((x-1, y-1))
        if ret:
            return choice(ret)
        return (-1, -1)

    def would_bump(self, me, view, dir_x, dir_y):
        grid = self.get_available_space_grid(me, view)
        dx = numpy.sign(dir_x)
        dy = numpy.sign(dir_y)
        adj_dx = dx + 1
        adj_dy = dy + 1
        return grid[adj_dx,adj_dy] == 0


    def act(self, view, msg):
        me = view.me
        mx = me.x
        my = me.y
        my_pos = mx, my

        tx = self.tx
        ty = self.ty
        if mx == tx and my == ty:
            self.tx = tx = randrange(tx - 5, tx + 6)
            self.ty = ty = randrange(tx - 5, tx + 6)
            self.step = 0


        if self.apoptosis <= 0:
            return Action(ACT_MOVE, (0, 0))

        # Attack anyone next to me, but first send out the distress message with my position
        my_team = me.team
        for a in view.agent_views:
            if a.team != my_team:
                ax = a.y
                ay = a.y
                msg.send_message((self.strain, MessageType.ATTACK, ax, ay))
                return Action(ACT_ATTACK, (ax, ay))

        # Eat any energy I find until I am 'full'. The cost of eating
        # is 1, so don't eat just 1 energy.
        my_energy = me.energy
        if self.my_plant is None and view.energy_map.values[my_pos] > 1:
            if my_energy <= self.genes['desired_energy'].val:
                return Action(ACT_EAT)
#            else:
#                debug('Not eating. Have %s which is above %s' %
#                      (my_energy, self.genes['desired_energy'].val))


        # If there is a plant near by go to it and spawn all I can
        if self.my_plant is None :
            plants = view.get_plants()
            if plants:
                self.my_plant = plants[0]
                self.tx = tx = mx
                self.ty = ty = my
                self.strain = self.my_plant.x * 41 + self.my_plant.y
                debug('attached to plant, strain %s' % self.strain)
        else:
            self.apoptosis -= 1
            if self.apoptosis <= 0:
                self.my_plant = None
                return Action(ACT_RELEASE, (mx + 1, my, my_energy - 1))
            

        if self.my_plant is None:
            spawn_threshold = self.genes['field_spawn_energy'].val
        else:
            spawn_threshold = self.genes['plant_spawn_energy'].val
        if my_energy >= spawn_threshold:
            spawn_x, spawn_y = self.smart_spawn(me, view)
            return Action(ACT_SPAWN,
                                (me.x + spawn_x, me.y + spawn_y, self))
        elif self.my_plant is not None:
            return Action(ACT_EAT)

        
        # If I get the message of help go and rescue!
        if (not self.step) and (not self.scout) and random() > 0.1:
            ax = 0;
            ay = 0;
            best = 500;
            message_count = len(msg.get_messages());
            for strain, type, ox, oy in msg.get_messages():
                if strain != self.strain:
                    continue
                if (type == MessageType.ATTACK) :
                    dist = max(abs(mx-ax), abs(my-ay))
                    if dist < best:
                        ax = ox
                        ay = oy
                        best = dist
            if ax and ay:
                self.tx = tx = ax + randrange(-3, 4)
                self.ty = ty = ay + randrange(-3, 4)
                # if (message_count > 1) :
                #     # Attack the base, not the front
                #     agent_scale = 1 + random()
                #     self.x *= agent_scale
                #     self.y *= agent_scale
                # don't stand still once we get there
                self.step = randrange(20, 100);

        # Back to step 0 we can change direction at the next attack.
        if self.step:
            self.step -= 1

        return Action(ACT_MOVE, (tx, ty))

########NEW FILE########
__FILENAME__ = crawling_chaos
import random,cells

import cmath, math

class AgentMind(object):
    def __init__(self, junk):
        self.my_plant = None
        self.mode = 1
        self.target_range = random.randrange(50,200)
        pass

    def act(self,view,msg):
        x_sum = 0
        y_sum = 0
        dir = 1
        n = len(view.get_plants())
        me = view.get_me()
        mp = (mx,my)= me.get_pos()
        for a in view.get_agents():
            if (a.get_team()!=me.get_team()):
                msg.send_message(mp)
                return cells.Action(cells.ACT_ATTACK,a.get_pos())

        for m in msg.get_messages():
            r = random.random()
            if ((self.my_plant and random.random()>0.6) or
                (not self.my_plant and random.random() > 0.5)):
                self.mode = 5
                (tx,ty) = m
                self.target = (tx+random.randrange(-3,4),ty+random.randrange(-3,4))

        if n:
            best_plant = max(view.get_plants(), key=lambda x: x.eff)
            if not self.my_plant or self.my_plant.eff < best_plant.eff:
                self.my_plant = view.get_plants()[0]
                self.mode = 0

        if self.mode == 5:
            dist = max(abs(mx-self.target[0]),abs(my-self.target[1]))
            self.target_range = max(dist,self.target_range)
            if me.energy > dist*1.5:
                self.mode = 6

        if self.mode == 6:
            dist = max(abs(mx-self.target[0]),abs(my-self.target[1]))
            if dist > 4:
                return cells.Action(cells.ACT_MOVE,self.target)
            else:
                self.my_plant = None
                self.mode = 0

        if (me.energy < self.target_range) and (view.get_energy().get(mx, my) > 0):
            return cells.Action(cells.ACT_EAT)

        if self.my_plant:
            dist = max(abs(mx-self.my_plant.get_pos()[0]),abs(my-self.my_plant.get_pos()[1]))
            if me.energy < dist*1.5:
                (mx,my) = self.my_plant.get_pos()
                return cells.Action(cells.ACT_MOVE,(mx+random.randrange(-1,2),my+random.randrange(-1,2)))
            if (random.random()>0.9999):
                (mx,my) = self.my_plant.get_pos()
                dtheta = random.random() * 2 * math.pi
                dr = random.randrange(100)
                curr_r, curr_theta = cmath.polar(mx + my*1j)
                m = cmath.rect(curr_r + dr, curr_theta + dtheta)
                msg.send_message((m.real, m.imag))

        if (random.random()>0.9 and me.energy >= 50):
            return cells.Action(cells.ACT_SPAWN,(mx+random.randrange(-1,2),my+random.randrange(-1,2)))
        else:
            return cells.Action(cells.ACT_MOVE,(mx+random.randrange(-1,2),my+random.randrange(-1,2)))

########NEW FILE########
__FILENAME__ = evolving_chaos
import cells
import genes

import cmath
import math
from random import random, randrange

CallForHelpGene = genes.make_normally_perturbed_gene(0.01)
CallOfDutyGene = genes.make_normally_perturbed_gene(0.01)
DraftDodgerGene = genes.make_normally_perturbed_gene(0.01)
SpawnProbabilityGene = genes.make_normally_perturbed_gene(0.01)
SpawnEnergyThresholdGene = genes.make_normally_perturbed_gene(5, 50, 5000)
ColonizeProbabilityGene = genes.make_normally_perturbed_gene(0.01)

CallTypeGene = genes.make_drastic_mutation_gene(0.01)

MODE_NORMAL = 0
MODE_PREP = 5
MODE_ATTACK = 6
MODE_COLONIZE = 7

def fuzz_coord(c):
    return c + randrange(-1,2)


class AgentMind(object):
    def __init__(self, args):
        self.my_plant = None
        self.mode = MODE_NORMAL
        self.target_range = randrange(50,200)
        if args is None:
            self.call_for_help = CallForHelpGene(genes.InitializerGene(0.25))
            self.call_of_duty = CallOfDutyGene(genes.InitializerGene(0.75))
            self.draft_dodger = DraftDodgerGene(genes.InitializerGene(0.75))
            self.spawn_prob = SpawnProbabilityGene(genes.InitializerGene(0.1))
            self.spawn_energy = SpawnEnergyThresholdGene(genes.InitializerGene(50))
            self.call_type = CallTypeGene(genes.InitializerGene(0))
            self.colonize_prob = ColonizeProbabilityGene(genes.InitializerGene(0.001))
        else:
            parent = args[0]
            self.call_for_help = parent.call_for_help.spawn()
            self.call_of_duty = parent.call_of_duty.spawn()
            self.draft_dodger = parent.draft_dodger.spawn()
            self.spawn_prob = parent.spawn_prob.spawn()
            self.spawn_energy = parent.spawn_energy.spawn()
            self.call_type = parent.call_type.spawn()
            self.colonize_prob = parent.colonize_prob.spawn()

    def _colonize_from(self, mx, my, mapsize):
        tx = randrange(mapsize)
        ty = randrange(mapsize)
        self._set_target(MODE_COLONIZE, tx, ty, mapsize)

    def _set_target(self, next_mode, tx, ty, mapsize):
        self.mode = MODE_PREP
        self.next_mode = next_mode
        tx += randrange(-3, 4)
        ty += randrange(-3, 4)
        tx = min(max(tx, 0), mapsize)
        ty = min(max(ty, 0), mapsize)
        self.target = (tx, ty)

    def act(self,view,msg):
        x_sum = 0
        y_sum = 0
        dir = 1
        me = view.me
        mp = (mx,my)= (me.x, me.y)
        map_size = view.energy_map.width

        cfh_val = self.call_for_help.val
        for a in view.agent_views:
            if (a.team != me.team):
                if random() > cfh_val:
                    msg.send_message((self.call_type.val, MODE_ATTACK, mp))
                return cells.Action(cells.ACT_ATTACK, (a.x, a.y))

        my_call_type = self.call_type.val
        my_plant = self.my_plant
        for message in msg.get_messages():
            call_type, move_mode, m = message
            if call_type != my_call_type:
                continue
            if my_plant:
                my_team = me.team
                num_nearby = sum(1 for x in view.agent_views if x.team == my_team)
                if num_nearby > 1 and random() > self.draft_dodger.val:
                    tx, ty = m
                    self._set_target(move_mode, tx, ty, map_size)
            elif random() < self.call_of_duty.val:
                tx, ty = m
                self._set_target(move_mode, tx, ty, map_size)

        del my_plant  # Might change later, don't confuse myself by caching it.

        if view.plant_views:
            best_plant = max(view.plant_views, key=lambda x: x.eff)
            self.my_plant = best_plant
            self.mode = MODE_NORMAL

        if self.mode == MODE_PREP:
            dist = max(abs(mx-self.target[0]),abs(my-self.target[1]))
            self.target_range = max(dist,self.target_range)
            if me.energy > dist*1.5:
                self.mode = self.next_mode

        if self.mode == MODE_COLONIZE or self.mode == MODE_ATTACK:
            dist = abs(mx-self.target[0]) + abs(my-self.target[1])
            my_team = me.team
            if (dist < 2 or
                (self.mode == MODE_COLONIZE and dist < 8 and
                 sum(1 for a in view.agent_views
                     if a.team == my_team) > 7)):
                self.my_plant = None
                self.mode = MODE_NORMAL
            else:
                return cells.Action(cells.ACT_MOVE,self.target)

        if me.energy < self.target_range:
            if view.energy_map.get(mx, my) > 0:
                return cells.Action(cells.ACT_EAT)
            elif self.my_plant is not None:
                mp = self.my_plant
                self._set_target(MODE_ATTACK, mp.x, mp.y, map_size)
            else:
                self._colonize_from(mx, my, map_size)

        my_plant = self.my_plant
        if my_plant is not None:
            dist = max(abs(mx-self.my_plant.get_pos()[0]),abs(my-self.my_plant.get_pos()[1]))
            if me.energy < dist*1.5:
                return cells.Action(cells.ACT_MOVE,
                                    (fuzz_coord(my_plant.x), fuzz_coord(my_plant.y)))
            if (random() < self.colonize_prob.val):
                self._colonize_from(my_plant.x, my_plant.y, map_size)

        if (random() < self.spawn_prob.val and
            me.energy >= self.spawn_energy.val):
            return cells.Action(cells.ACT_SPAWN,
                                (fuzz_coord(mx), fuzz_coord(my), self))
        else:
            return cells.Action(cells.ACT_MOVE,
                                (fuzz_coord(mx), fuzz_coord(my)))

########NEW FILE########
__FILENAME__ = genes
'''Genes in asexual reproduction.

Totally made-up, has no basis in genetic algorithms b/c I have no
background in that area.
'''

import random

class Gene(object):
    def __init__(self, parent):
        '''Clone this gene from the parent gene.'''
        self.val = parent.val

    def spawn(self):
        '''Copy this gene, introducing mutations probabilistically.'''
        new = self.__class__(self)
        new.mutate()
        return new

    def mutate(self):
        perturb = self.gen_perturb()
        val = self.val + perturb
        self.val = min(max(val, self.min_cap), self.max_cap)


def make_normally_perturbed_gene(sigma, minc=0, maxc=1):
    class NormallyPerturbedGene(Gene):
        min_cap = minc
        max_cap = maxc
        def gen_perturb(self):
            return random.gauss(0, sigma)
    return NormallyPerturbedGene


def make_drastic_mutation_gene(pr):
    '''Gene representing incompatible categories.'''
    class DrasticMutationGene(Gene):
        min_cap = 0
        max_cap = 100
        def gen_perturb(self):
            if random.random() < pr:
                return 1 if random.random() < 0.5 else -1
            else:
                return 0
    return DrasticMutationGene


class InitializerGene(object):
    '''A fake gene, used to initialize things.'''
    def __init__(self, val):
        self.val = val

########NEW FILE########
__FILENAME__ = japhet
"""
idea: spawn in waves.  everyone saves up food from the plant until a certain time at which everyone spawns soldiers as fast as possible.
Triggered by an attack.  Everyone set their spawn requirement according to the distance to the attack so that the spawn will all reach the spot at the same time.
idea: use avg pos for spawned soldier destination, local attack events for local maneuvering
idea: attack messages puts everone in 'report' state, everyone sends report on how ready they are to save up.  next tick everyone makes same decision based on reports
"""


import random,cells
import math

class Message:
	def __init__(self, pos):
		self.pos = pos

# inspired by zenergizer
diffs = [(1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1), (0, -1), (1, -1)]

class AgentMind:
	def __init__(self, args):
		if args:
			soldier = args[0]
		else:
			soldier = False

		self.my_plant = None
		self.mode = 1
		self.moved = 0
		#self.target_range = random.randrange(50,1000)
		self.setDirection()
		self.avgEnemyPos = (0,0)
		self.weight = 0
		self.soldier = (random.random() < .6) or soldier
		self.spawner = False
		self.spawnRequirement = 65
		self.soldierDirected = None
		self.distanceToFight = None

		if self.soldier:
			self.energyNeeded = 100 # how much energy we need before we ignore food
		else:
			self.energyNeeded = 25
		self.prevEnergy = None


	def setDirection(self, rad = None):
		if rad != None:
			self.direction = rad
		else:
			self.direction = random.random()*math.pi*2
		self.cos = math.cos(self.direction)
		self.sin = math.sin(self.direction)

		if self.cos < 0:
			self.dx = -1
		else:
			self.dx = 1

		if self.sin < 0:
			self.dy = -1
		else:
			self.dy = 1


	def act(self,view,msg):
		me = view.get_me()
		pos = me.get_pos()
		(mx, my) = pos

		if len(view.get_plants()):
			self.soldier = False
			self.spawner = True
			self.spawnRequirement = 55


		# respond to nearby battles
		if self.soldier and len(msg.get_messages()):
			newPos = (0, 0)
			nCloseBy = 0
			for message in msg.get_messages():
				enemyPos = message.pos
				cartesian = (enemyPos[0] - mx, enemyPos[1] - my)
				distance = max(abs(cartesian[0]), abs(cartesian[1]))
				if distance < 30:
					nCloseBy+=1
					newPos = (newPos[0] + enemyPos[0], newPos[1] + enemyPos[1])
				
				# does the soldier have orders?  any battle call will do
				if not self.soldierDirected:
					direction = math.atan2(cartesian[1], cartesian[0])
					self.setDirection(direction)
					self.soldierDirected = True

			if nCloseBy:
				# find average of all close-by battle calls
				self.avgEnemyPos = ((self.avgEnemyPos[0] * float(self.weight) + newPos[0]) / float(self.weight + nCloseBy),
					(self.avgEnemyPos[1] * float(self.weight) + newPos[1]) / float(self.weight + nCloseBy))
				self.weight = min(25, self.weight+nCloseBy)
						
				cartesian = (self.avgEnemyPos[0] - mx, self.avgEnemyPos[1] - my)
				direction = math.atan2(cartesian[1], cartesian[0])
				self.setDirection(direction)
				self.distanceToFight = max(abs(cartesian[0]), abs(cartesian[1]))
				self.spawnRequirement = 50 + self.distanceToFight + 10

		# are we stuck?
		if self.moved and self.prevPos == pos:
			self.setDirection()		
			self.soldierDirected = False
		self.moved = 0
		self.prevPos = None

		#attack?
		for a in view.get_agents():
			if (a.get_team()!=me.get_team()):				
				msg.send_message(Message(a.get_pos()))
				return cells.Action(cells.ACT_ATTACK,a.get_pos())

		# freeSpots = where we can move/spawn
		freeSpots = diffs[:]
		for a in view.get_agents():
			apos = a.get_pos()
			dpos = (apos[0] - pos[0], apos[1] - pos[1])
			if dpos in freeSpots:
				freeSpots.remove(dpos)

		# see a ton of food nearby?
		if not self.spawner:
			for diff in diffs:
				target = (mx+diff[0], my+diff[1])
				if view.get_energy().get(target[0], target[1]) > 50 and target in freeSpots:
					return cells.Action(cells.ACT_MOVE, (mx+diff[0], my+diff[1]))

		# spawn?
		if me.energy > self.spawnRequirement:
			if len(freeSpots):
				random.shuffle(freeSpots)
				spawn = freeSpots[0]
				spawnSoldier = None
				if self.distanceToFight and self.distanceToFight < 20:
					spawnSoldier = True
				else:
					spawnSoldier = False
				return cells.Action(cells.ACT_SPAWN, (mx+spawn[0], my+spawn[1], spawnSoldier))


		# eat?
		if self.spawner or view.get_energy().get(mx, my) > 1 and (me.energy < self.energyNeeded):
			self.prevEnergy = me.energy
			return cells.Action(cells.ACT_EAT)


		# move as directed
		elif not self.spawner:
			dx = dy = 0
			while not self.moved:
				if random.random() < abs(self.cos):
					dx += self.dx
				if random.random() < abs(self.sin):
					dy += self.dy
				self.moved = dx or dy
			self.prevPos = pos
			return cells.Action(cells.ACT_MOVE, (mx+dx, my+dy))


########NEW FILE########
__FILENAME__ = jayshoo
# seriously stupid bot
# eat, work out symmetric position, attack, lose to spreaded colonies

import cells, random

class AgentMind(object):
    def __init__(self, args):
        # init things
        self.home = None
        self.breeder = False

        # if called by a parent:
        if (args != None):
            self.home = args[0]

    def symmetricPos(self, pos):
        return (pos[1], pos[0])

    def get_dir(self, myX, myY, targX, targY):
        resultX = 0
        resultY = 0
        if (myX > targX): resultX = myX+1
        if (myX < targX): resultX = myX-1
        if (myY > targY): resultY = myY-1
        if (myY < targY): resultY = myY+1
        return (resultX, resultY)

    def act(self, view, msg):
        me = view.get_me()
        my_pos = (mx,my) = me.get_pos()

        # first cell only store home plant and work out direction to symmetric team
        # TODO: handle view.get_plants() somehow not working for the first cell
        if (self.home == None):
            self.home = (view.get_plants()[0].x, view.get_plants()[0].y)
            self.breeder = True

        # eat
        if (view.get_energy().get(mx, my) > 0):
            if (me.energy < 50):
                return cells.Action(cells.ACT_EAT)

        # breed if designated
        if (self.breeder):
            return cells.Action(cells.ACT_SPAWN, (mx + random.randrange(-1,2), my + random.randrange(-1,2), self.home))

        # fight if drunk
        nearby = view.get_agents()
        for a in nearby:
            if (a.team != me.team):
                return cells.Action(cells.ACT_ATTACK, a.get_pos())

        # leave home
        return cells.Action(cells.ACT_MOVE, self.symmetricPos(self.home))

        # die
        pass

########NEW FILE########
__FILENAME__ = mind1
'''
Defines an agent mind that attacks any opponent agents within its view,
attaches itself to the strongest plant it finds, eats when its hungry, 
'''

import random, cells
import math


class AgentMind(object):
    def __init__(self, junk):
        self.my_plant = None
        self.mode = 1
        self.target_range = random.randrange(50, 1000)

    def length(self, a, b):
        return int(math.sqrt((a * a) + (b * b)))

    def act(self, view, msg):
        x_sum = 0
        y_sum = 0
        dir = 1
        me = view.get_me()
        mp = (mx, my)= me.get_pos()

        # Attack any opponents.
        for a in view.get_agents():
            if a.get_team() != me.get_team():
                return cells.Action(cells.ACT_ATTACK, a.get_pos())

        # Attach to the strongest plant found.
        if view.get_plants():
            plant = view.get_plants()[0]
            if not self.my_plant:
                self.my_plant = plant
            elif self.my_plant.eff < plant.eff:
                self.my_plant = plant
        
        # Eat if hungry or if this is an exceptionally energy-rich spot.
        hungry = (me.energy < self.target_range)
        energy_here = view.get_energy().get(mx, my)
        food = (energy_here > 0)
        if hungry and food or energy_here > 100:
            return cells.Action(cells.ACT_EAT)

        if self.my_plant:
            plant_pos = self.my_plant.get_pos()
            plant_dist = self.length(
                abs(mx - plant_pos[0]), 
                abs(my - plant_pos[1]))
            
            if (not me.loaded and
                (plant_dist % 5 or abs(mx - plant_pos[0]) < 2)
                and random.random() > 0.5):
                return cells.Action(cells.ACT_LIFT)
            if me.loaded and plant_dist % 5 == 0 and abs(mx - plant_pos[0]) >= 2:
                return cells.Action(cells.ACT_DROP)
            if me.energy < plant_dist * 1.5:
                (mx, my) = plant_pos
                pos = (mx + random.randrange(-1, 2), my + random.randrange(-1, 2))
                return cells.Action(cells.ACT_MOVE, pos)

        pos = (mx + random.randrange(-1, 2), my + random.randrange(-1, 2))
        action = cells.ACT_SPAWN if random.random() > 0.9 else cells.ACT_MOVE
        return cells.Action(action, pos)

########NEW FILE########
__FILENAME__ = mind2
import random, cells


class AgentMind(object):
    def __init__(self, junk):
        self.my_plant = None
        self.mode = 1
        self.target_range = random.randrange(50,200)

    def act(self,view,msg):
        x_sum = 0
        y_sum = 0
        dir = 1
        n = len(view.get_plants())
        me = view.get_me()
        mp = (mx,my)= me.get_pos()
        for a in view.get_agents():
            if (a.get_team()!=me.get_team()):
                return cells.Action(cells.ACT_ATTACK,a.get_pos())

        for m in msg.get_messages():
            if (random.random()>0.6) and self.my_plant:
                self.mode = 5
                (tx,ty) = m
                self.target = (tx+random.randrange(-3,4),ty+random.randrange(-3,4))

        if(n>0):
            if (not self.my_plant):
                self.my_plant = view.get_plants()[0]
            elif self.my_plant.get_eff()<view.get_plants()[0].get_eff():
                self.my_plant = view.get_plants()[0]

        if self.mode == 5:
            dist = max(abs(mx-self.target[0]),abs(my-self.target[1]))
            self.target_range = max(dist,self.target_range)
            if me.energy > dist*1.5:
                self.mode = 6

        if self.mode == 6:
            dist = max(abs(mx-self.target[0]),abs(my-self.target[1]))
            if dist > 4:
                return cells.Action(cells.ACT_MOVE,self.target)
            else:
                self.my_plant = None
                self.mode = 0

        if (me.energy < self.target_range) and (view.get_energy().get(mx, my) > 0):
            return cells.Action(cells.ACT_EAT)

        if self.my_plant:
            dist = max(abs(mx-self.my_plant.get_pos()[0]),abs(my-self.my_plant.get_pos()[1]))
            if me.energy < dist*1.5:
                (mx,my) = self.my_plant.get_pos()
                return cells.Action(cells.ACT_MOVE,(mx+random.randrange(-1,2),my+random.randrange(-1,2)))
            if (random.random()>0.9999):
                (mx,my) = self.my_plant.get_pos()
                msg.send_message((my,mx))

        if (random.random()>0.9):
            return cells.Action(cells.ACT_SPAWN,(mx+random.randrange(-1,2),my+random.randrange(-1,2)))
        else:
            return cells.Action(cells.ACT_MOVE,(mx+random.randrange(-1,2),my+random.randrange(-1,2)))

########NEW FILE########
__FILENAME__ = mind3
import random,cells
#rylsan
#phreeza


##   Message Grammar
##sentence = [uniqueid,object_type,obj_instance)
##such that coords = (x,y)
##which means: "my name is uniqueid and I have found an obj_instance of an object"
##object_type=2 : plant
##object_type=3 : enemy
##2,3,5,7,11 are possible control vals

class AgentMind(object):
    def __init__(self,junk):
        self.my_plant = None
        self.mode = 1
        self.target_range = random.randrange(50,200)

        self.memory=[]
        self.outmemory=[]

        self.uniqueid = 0

    def act(self,view,msg):
        x_sum = 0
        y_sum = 0
        dir = 1
        n = len(view.get_plants())
        me = view.get_me()
        mp = (mx,my)= me.get_pos()

        #If I don't have an id yet, get one.
        if(self.uniqueid==0):
            self.uniqueid = self.GetID()

        for a in view.get_agents():
            if (a.get_team()!=me.get_team()):
                #If I see an enemy, broadcast it, then attack it.
                sentence = [self.uniqueid,3,a]
                self.outmemory.append(sentence)
                if sentence not in self.outmemory:
                    msg.send_message(sentence)
                return self.Attack(a)



        #Go through my messages, then memorize them
        for m in msg.get_messages():
            self.memory.append(m)



        #Choosing a plant
        if(n>0):
            #If I see a plant, broadcast it.
            sentence = [self.uniqueid,2,view.get_plants()[0]]
            self.outmemory.append(sentence)
            if sentence not in self.outmemory:
                msg.send_message(sentence)

            if (not self.my_plant):
                #If I don't have a plant, get one.
                self.my_plant = view.get_plants()[0]
            elif self.my_plant.get_eff()<view.get_plants()[0].get_eff():
                #If I see a plant that is better than my current one, get it.
                self.my_plant = view.get_plants()[0]
            else:
                #Otherwise, check my memory to see if someone else has found a plant
                for mem in self.memory:
                    if(mem[1]==2):
                        #Ok, go to the plant that I have in memory
                        self.my_plant=mem[2]
                        break



        if self.mode == 5:
            dist = max(abs(mx-self.target[0]),abs(my-self.target[1]))
            self.target_range = max(dist,self.target_range)
            if view.get_me().energy > dist*1.5:
                self.mode = 6

        if self.mode == 6:
            dist = max(abs(mx-self.target[0]),abs(my-self.target[1]))
            if dist > 4:
                return cells.Action(cells.ACT_MOVE,self.target)
            else:
                self.my_plant = None
                self.mode = 0


        if (view.get_me().energy < self.target_range) and (view.get_energy().get(mx,my) > 0):
            return self.Eat()

        #If I have a plant, move towards it if i need to.
        if self.my_plant:
            dist = max(abs(mx-self.my_plant.get_pos()[0]),abs(my-self.my_plant.get_pos()[1]))
            if view.get_me().energy < dist*1.5:
                (mx,my) = self.my_plant.get_pos()
                return self.Move(mx,my)

        #Spawn near my plant, or just move near it.
        if (random.random()>0.9):
            return self.Spawn(mx,my)
        else:
            return self.Move(mx,my)


    def Spawn(self,x,y):
        return cells.Action(cells.ACT_SPAWN,(x+random.randrange(-1,2),y+random.randrange(-1,2)))

    def Move(self,x,y):
        return cells.Action(cells.ACT_MOVE,(x+random.randrange(-1,2),y+random.randrange(-1,2)))

    def Attack(self,a):
        return cells.Action(cells.ACT_ATTACK,a.get_pos())

    def Eat(self):
        return cells.Action(cells.ACT_EAT)


    def GetID(self):
        ulist = [11,13,17,19,23,29,31,37,41,43,47,53,59,61,67,71,
                     73,79,83,89,97,101,103,107,109,113,127,131,137,139,149,151,157,163,167,173]

        r = random.randint(5,35)
        random.shuffle(ulist)
        uid = 1
        for i in range(0,r):
            uid *= ulist[i]
        uid=uid*3571
        return uid

########NEW FILE########
__FILENAME__ = seken
'''
Defines an agent mind that attacks any opponent agents within its view,
attaches itself to the strongest plant it finds, eats when its hungry, 
'''

import random, cells
import math, numpy

class AgentType(object):
	QUEEN = 0
	WORKER = 1
	FIGHTER = 2
	BUILDER = 3

class MessageType(object):
	FOUND = 0
	DEFEND = 1
	CLAIM = 2
	CLAIMED = 3

def dist(a, b):
	return int(math.sqrt((a[0]-b[0])**2 + (a[1]-b[1])**2))

def length(xy):
	return dist(xy, (0, 0))

def offset(i):
	i = i % 9
	x = 0
	y = 0
	if i < 3:
		y = -1
	if i > 5:
		y = 1
	
	if i == 0 or i == 5 or i == 6:
		x = -1
	if i == 2 or i == 3 or i == 8:
		x = 1

	return (x, y)

def get_available_space_grid(view, agent):
	grid = numpy.ones((3,3))
	for a in view.get_agents():
		grid[a.x - agent.x + 1, a.y - agent.y + 1] = 0
	for plant in view.get_plants():
		grid[plant.x - agent.x + 1, plant.y - agent.y + 1] = 0
	grid[1,1] = 0
	return grid

def spawnPos(i, type, view, agent):
	if type == AgentType.QUEEN:
		old = offset(i)
		return (-old[0], -old[1])
	grid = get_available_space_grid(view, agent)
	for x in xrange(3):
		for y in range(3):
			if grid[x,y]:
				return (x-1, y-1)
	return (-1, -1)

class AgentMind(object):

	def __init__(self, data):
		self.target_range = random.randrange(50, 1000)

		if data == None:
			self.type = AgentType.QUEEN
			self.ratios = (1,)
		else:
			self.type = data[0]
			self.ratios = (1, 1, 1, 2)

		if self.type == AgentType.QUEEN:
			self.plant = None
			self.claimed = False
			self.claiming = False
			self.position = 0
			self.count = 0
			self.directionOfAttack = None
			self.newborn = True
			self.age = 0

		if self.type == AgentType.WORKER:
			self.plantList = list()
			self.startPoint = data[1]

		if self.type == AgentType.BUILDER:
			self.radius = 10
			self.height = 4
			self.openings = 1

		self.skip = True

		if self.type == AgentType.FIGHTER and data[1]:
			self.direction = data[1]
		else:
			self.direction = (random.randrange(0, 300), random.randrange(0, 300))

	def act(self, view, msg):
		agent = view.get_me()
		position = (x, y)= agent.get_pos()

		if dist(self.direction, position) < 2:
			self.direction = (random.randrange(0, view.energy_map.width), random.randrange(0, view.energy_map.height))

		# Attack any opponents.
		for a in view.get_agents():
			if a.get_team() != agent.get_team():
				if self.type == AgentType.QUEEN:
					msg.send_message((MessageType.DEFEND, (x,y)))
					self.ratios = [0, 2, 2, 2]
				else:
					msg.send_message((MessageType.FOUND, a.get_pos()))
				return cells.Action(cells.ACT_ATTACK, a.get_pos())

		# Process messages
		alreadyClaimed = 0
		distance = 1000000
		for message in msg.get_messages():
			# Queen message behavior
			if message[0] == MessageType.CLAIM and self.type == AgentType.QUEEN:
				if self.plant != None and self.plant.get_pos() == message[1]:
					if self.claimed:
						self.newborn = False
						msg.send_message((MessageType.CLAIMED, message[1]))
			if message[0] == MessageType.CLAIMED and self.type == AgentType.QUEEN:
				if self.plant != None and self.plant.get_pos() == message[1]:
					if not self.claimed:
						alreadyClaimed += 1
			if message[0] == MessageType.FOUND and self.type == AgentType.QUEEN:
				if dist(message[1], position) < distance:
					self.directionOfAttack = message[1]
					distance = dist(message[1], position)

			# Worker message behavior
			if self.type == AgentType.WORKER:
				if message[0] == MessageType.CLAIM:
					found = False
					for p in self.plantList:
						if p == message[1]:
							found = True
							break
					if not found:
						self.plantList.append(message[1])

				if message[0] == MessageType.DEFEND or message[0] == MessageType.FOUND:
					aDistance = dist(position, message[1])
					if aDistance < 20 and aDistance < distance:
						self.type = AgentType.FIGHTER
						self.direction = message[1]
						distance = aDistance

			# Fighter message behavior
			if self.type == AgentType.FIGHTER:
				if message[0] == MessageType.DEFEND or message[0] == MessageType.FOUND:
					if distance > dist(position, message[1]):
						self.direction = message[1]
						distance = dist(position, message[1])

		if self.type == AgentType.WORKER:
			if dist(position, self.startPoint) > 2:
				plants = view.get_plants()
				if plants:
					found = False
					for p in self.plantList:
						if p == plants[0].get_pos():
							found = True
							break
					if not found:
						self.type = AgentType.QUEEN
						self.ratios = (1,1,1,2)
						self.newborn = True
						self.plant = None
						self.claimed = False
						self.claiming = False
						self.position = 0
						self.count = 0
						self.directionOfAttack = None
						self.age = 0
						del self.plantList

			# Eat if hungry.
			hungry = (agent.energy < 50)
			energy_here = view.get_energy().get(x, y)
			food = (energy_here > 0)
			if hungry and food:
				return cells.Action(cells.ACT_EAT)

			if agent.energy > 500:
				sp = spawnPos(0, AgentType.WORKER, view, agent)
				sp = (sp[0]+x, sp[1]+y, AgentType.WORKER, (x, y))
				return cells.Action(cells.ACT_SPAWN, sp)

			if random.random() < 0.65:
				if random.random() < 0.4:
					if view.get_energy().get(x, y) > 0:
						return cells.Action(cells.ACT_EAT)

				direction = [self.direction[0]-x, self.direction[1]-y]
				if direction[0] > 0:
					direction[0] = 1
				elif direction[0] == 0:
					direction[0] = 0
				else:
					direction[0] = -1

				if direction[1] > 0:
					direction[1] = 1
				elif direction[1] == 0:
					direction[1] = 0
				else:
					direction[1] = -1

				position = (position[0]+direction[0], position[1]+direction[1])
			else:
				position = (x + random.randrange(-1, 2), y + random.randrange(-1, 2))
			return cells.Action(cells.ACT_MOVE, position)

		if self.type == AgentType.FIGHTER:
			# Eat if hungry.
			hungry = (agent.energy < 100)
			energy_here = view.get_energy().get(x, y)
			food = (energy_here > 0)
			if hungry and food:
				return cells.Action(cells.ACT_EAT)

			if agent.energy > 1000:
				sp = spawnPos(0, AgentType.FIGHTER, view, agent)
				sp = (sp[0]+x, sp[1]+y, AgentType.FIGHTER, (x, y))
				return cells.Action(cells.ACT_SPAWN, sp)

			if random.random() < 0.85 or dist(position, self.direction) < 8:
				direction = [self.direction[0]-x, self.direction[1]-y]
				if direction[0] > 0:
					direction[0] = 1
				elif direction[0] == 0:
					direction[0] = 0
				else:
					direction[0] = -1

				if direction[1] > 0:
					direction[1] = 1
				elif direction[1] == 0:
					direction[1] = 0
				else:
					direction[1] = -1

				position = (position[0]+direction[0], position[1]+direction[1])
			else:
				position = (x + random.randrange(-1, 2), y + random.randrange(-1, 2))
			return cells.Action(cells.ACT_MOVE, position)


		# Queen Stuff
		if self.type == AgentType.QUEEN:
			# Check claim
			if self.claiming:
				if self.skip:
					self.skip = False
				else:
					if alreadyClaimed > 39:
						# Try again
						self.plant = None
						self.claiming = False
					else:
						# We have a throne
						self.claimed = True
						self.claiming = False
						self.position = alreadyClaimed
						print alreadyClaimed
					self.skip = True

			# Get a plant
			if self.plant == None and view.get_plants():
				self.age += 1
				if self.age > 5:
					self.type = AgentType.WORKER
					self.plantList = list()

				if view.get_plants():
					plants = view.get_plants()
					bestPlant = plants[0]
					distance = dist(position, bestPlant.get_pos())
					for plant in plants:
						if distance > dist(position, bestPlant.get_pos()):
							distance = dist(position, bestPlant.get_pos())
							bestPlant = plant
						
					self.plant = bestPlant
					self.claiming = True
					msg.send_message((MessageType.CLAIM, self.plant.get_pos()))

			# Check position
			if self.claimed == False and self.claiming == False:
				# Move randomly
				if random.random() > 0.75:
					direction = [self.direction[0]-x, self.direction[1]-y]
					if direction[0] > 0:
						direction[0] = 1
					elif direction[0] == 0:
						direction[0] = 0
					else:
						direction[0] = -1

					if direction[1] > 0:
						direction[1] = 1
					elif direction[1] == 0:
						direction[1] = 0
					else:
						direction[1] = -1

					position = (position[0]+direction[0], position[1]+direction[1])
				else:
					position = (x + random.randrange(-1, 2), y + random.randrange(-1, 2))
				return cells.Action(cells.ACT_MOVE, position)

			if self.claimed:
				# Move towards
				off = offset(self.position)
				pos = self.plant.get_pos()
				pos = (pos[0]+off[0], pos[1]+off[1])
				distance = dist(pos, position)
				
				if distance > 0:
					if agent.energy > distance * 1.1:
						if random.random() > 0.6:
							pos = (x + random.randrange(-1, 2), y + random.randrange(-1, 2))
						return cells.Action(cells.ACT_MOVE, pos)
					else:
						# Cannot move in one go eat if pos or move a bit
						if view.get_energy().get(x, y) > 0:
							return cells.Action(cells.ACT_EAT)
						mxy = [0, 0]
						if self.plant.get_pos()[0] > x:
							mxy[0] = 1
						elif self.plant.get_pos()[0] < x:
							mxy[0] = -1
						if self.plant.get_pos()[1] > y:
							mxy[1] = 1
						elif self.plant.get_pos()[1] < y:
							mxy[1] = -1

						mxy = (mxy[0]+x, mxy[1]+y)
						return cells.Action(cells.ACT_MOVE, mxy)
					
			# Breed or Eat
			nxt = self.ratios[self.count%len(self.ratios)]
			spawn = [x, y, nxt]
			spawning = False

			if self.newborn and agent.energy > 100:
				spawn = [x, y, AgentType.QUEEN]
				spawnOff = spawnPos(self.position, AgentType.QUEEN, view, agent)
				spawning = True
			if nxt == AgentType.QUEEN and agent.energy > 100:
				# Spawn new queen
				spawnOff = spawnPos(self.position, nxt, view, agent)
				spawning = True
			if nxt == AgentType.WORKER and agent.energy > 100:
				# Spawn new worker
				spawnOff = spawnPos(self.position, nxt, view, agent)
				spawn.append(position)
				spawning = True
			if nxt == AgentType.FIGHTER and agent.energy > 100:
				# Spawn new fighter
				spawnOff = spawnPos(self.position, nxt, view, agent)
				spawn.append(self.directionOfAttack)
				spawning = True
			if nxt == AgentType.BUILDER and agent.energy > 100:
				# Spawn new builder
				spawnOff = spawnPos(self.position, nxt, view, agent)
				spawning = True

			if spawning:
				spawn[0] += spawnOff[0]
				spawn[1] += spawnOff[1]
				self.count = self.count + 1
				return cells.Action(cells.ACT_SPAWN, spawn)

			# Must eat
			return cells.Action(cells.ACT_EAT)
			

		if random.random() > 0.75:
			direction = (self.direction[0]-x, self.direction[1]-y)
			if direction[0] > 0:
				direction[0] = 1
			elif direction[0] == 0:
				direction[0] = 0
			else:
				direction[0] = -1

			if direction[1] > 0:
				direction[1] = 1
			elif direction[1] == 0:
				direction[1] = 0
			else:
				direction[1] = -1

			position = (position[0]+direction[0], position[1]+direction[1])
		else:
			position = (x + random.randrange(-1, 2), y + random.randrange(-1, 2))
		return cells.Action(cells.ACT_MOVE, position)

########NEW FILE########
__FILENAME__ = zenergizer
#
# zenergizer.py
#
# Seth Zenz
# Email: cancatenate my first and last names, all lower case, at gmail.com
# June 2, 2010
#
# There is a lot of ugly machinery in this guy, I made him from tinkering 
# around and never cleaned him up completely.  Some of the things he does
# I don't really understand why.  Lost of numbers aren't tuned.
#
# But if you watch him work, you'll see that he demonstrates the value of
# going for the biggest pile of energy around and eating it -- both in
# exploration and in big melees.  This isn't obvious but it works. 
#

import random,cells

class AgentMind:
  def __init__(self, args):

    self.goto_war_at = 500
    self.diffs = [(-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)]
    self.mytime = 0 
    self.am_warrior = False
    self.lastattack = (-1,-1,-1)

    if not args:
      self.gen = 0
      self.war_time = -1
      self.startdiff = random.choice(self.diffs)
    else:
      self.gen = args[0]
      self.war_time = args[1]
      self.startdiff = args[2]
    self.target_range = 5
    self.spawn_min = 50
    self.migrate_min = 70

    if ((random.random() < 0.7 and not (self.war_time>0)) or self.gen == 0):
      self.mygoaldir = (0,0)
    else:
      if (self.war_time > 0) and (random.random() > 0.1):
        self.am_warrior = True
        self.mygoaldir = (0,0)
      else:
        self.mygoaldir = self.startdiff
        self.questtime = 0
        self.last_x = 999
        self.last_y = 999
    pass

  def act(self,view,msg):
    me = view.get_me()
    mp = (mx,my)= me.get_pos()

    # If I think it's time to go to war, sound out a message
    if self.mytime > self.goto_war_at and not (self.war_time > 0):
      msg.send_message(("war",self.mytime))

    # personal time counter      
    self.mytime += 1    

    # Interpret war-related messages
    for m in msg.get_messages():
      if m[0] == "war" and not self.am_warrior:
        self.am_warrior = True
        self.war_time = self.mytime
      if m[0] == "attack":
        self.lastattack = (m[1],m[2],self.mytime)

    # Attack nearby enemies.  This always gets done first    
    for a in view.get_agents():
      if (a.get_team()!=me.get_team()):
        msg.send_message(("attack",mx,my))
        return cells.Action(cells.ACT_ATTACK,a.get_pos())

    # Move if at war
    if self.am_warrior and (self.lastattack[2] > self.war_time - 50):
      go = True
      for plant in view.get_plants():
        if (mx == plant.x and abs(my-plant.y) < 2) or (my == plant.y and abs(mx-plant.x) < 2):
          go = False
      if go:
        tx,ty = (self.lastattack[0],self.lastattack[1])
        if mx != self.lastattack[0]: tx += random.randrange(15,40)*(self.lastattack[0]-mx)/abs((self.lastattack[0]-mx))
        if my != self.lastattack[1]: ty += random.randrange(15,40)*(self.lastattack[1]-my)/abs((self.lastattack[1]-my))
        tx += random.randrange(-4,5)
        ty += random.randrange(-4,5)
        return cells.Action(cells.ACT_MOVE,(tx,ty))

    # If very hungry, eat
    if ((me.energy < self.target_range) and (view.get_energy().get(mx, my) > 0)): 
      return cells.Action(cells.ACT_EAT)

    # If on a quest, move.  Stop for nearby goodies or if I couldn't move last time.
    if self.mygoaldir != (0,0):
      self.questtime += 1
      highenergy = False
      for diff in self.diffs:
        tx,ty = mx+diff[0],my+diff[1]
        if (view.get_energy().get(tx,ty) > 200): highenergy = True
      if ((len(view.get_plants()) > 0 or highenergy) and self.questtime > 5) or (mx == self.last_x and my == self.last_y):
        self.mygoaldir = (0,0)
      else:
        self.last_x = mx
        self.last_y = my
        for a in view.get_agents():
          if a.x == mx+self.mygoaldir[0] and a.y == my+self.mygoaldir[1]:
            self.mygoaldir = random.choice(self.diffs) # change destination if blocked
        if random.random() < 0.9:
          return cells.Action(cells.ACT_MOVE,(mx+self.mygoaldir[0],my+self.mygoaldir[1]))
        else:
          return cells.Action(cells.ACT_MOVE,(mx+self.mygoaldir[0]+random.randrange(-1,2),my+self.mygoaldir[1]+random.randrange(-1,2)))

    # Spawn if I have the energy    
    if me.energy > self.spawn_min:
      random.shuffle(self.diffs)
      for diff in self.diffs:
        sx,sy = (mx+diff[0],my+diff[1])
        occupied = False
        for a in view.get_agents():
          if a.x == sx and  a.y == sy:
            occupied = True
            break
        if not occupied:
          return cells.Action(cells.ACT_SPAWN,(sx,sy,self.gen+1,self.war_time,diff))

    # Start a quest if I have the energy and there's no war  
    if me.energy > self.migrate_min and not self.am_warrior:
      self.mygoaldir = random.choice(self.diffs)
      self.questtime = 0
      self.last_x = -999
      self.last_y = -999
      return cells.Action(cells.ACT_MOVE,(mx+self.mygoaldir[0],my+self.mygoaldir[1]))

    # Find the highest energy square I can see.  If I'm there, eat it.  Otherwise move there.
    maxenergy = view.get_energy().get(mx,my)
    fx,fy = (mx,my)
    random.shuffle(self.diffs)
    for diff in self.diffs:
      tx,ty = (mx+diff[0],my+diff[1])
      occupied = False
      for a in view.get_agents():
        if a.x == tx and  a.y == ty:
          occupied = True
          break
      if view.get_energy().get(tx,ty) > maxenergy and not occupied:
        maxenergy = view.get_energy().get(tx,ty)
        fx,fy = (tx,ty)
    if (mx,my) == (fx,fy):
      return cells.Action(cells.ACT_EAT)
    return cells.Action(cells.ACT_MOVE,(fx,fy))

########NEW FILE########
__FILENAME__ = generator
import numpy
import random
import math

class terrain_generator():
    def create_random(self, size, range, symmetric=False):
        """Creates a random terrain map"""
        ret = numpy.random.random_integers(0, range, size)

        if symmetric:
            ret = self.make_symmetric(ret)
        return ret

    def create_streak(self, size, range, symmetric=False):
        """Creates a terrain map containing streaks that run from north-west to south-east

           Starts with a single point [[a]] and converts it into [[a, b], [c, d]]
           where:
           b = a + (random change)
           c = a + (random change)
           d = b + (random change) and c + (random change)

           Repeat untill size matches required size"""
        add_random_range = self.add_random_range

        # Creates the top row
        ret = [[add_random_range(0, 0, range)]]
        for x in xrange(size[0] - 1):
            pos_west = ret[0][-1]
            if pos_west <= 0:
              ret[0].append(add_random_range(pos_west, 0, 1))
            elif pos_west >= range:
              ret[0].append(add_random_range(pos_west, -1, 0))
            else:
              ret[0].append(add_random_range(pos_west, -1, 1))

        # Create the next row down
        for y in xrange(size[1] - 1):
            pos_north = ret[-1][0]
            if pos_north <= 0:
                next_row = [add_random_range(pos_north, 0, 1)]
            elif pos_north >= range:
                next_row = [add_random_range(pos_north,-1, 0)]
            else:
                next_row = [add_random_range(pos_north, -1, 1)]

            for x in xrange(size[0] - 1):
                pos_north = ret[-1][x+1]
                pos_west = next_row[-1]
                if pos_west == pos_north:
                    if pos_west <= 0:
                        next_row.append(add_random_range(pos_west, 0, 1))
                    elif pos_west >= range:
                        next_row.append(add_random_range(pos_west, -1, 0))
                    else:
                        next_row.append(add_random_range(pos_west, -1, 1))
                elif abs(pos_west - pos_north) == 2:
                    next_row.append((pos_west + pos_north)/2)
                else:
                    next_row.append(random.choice((pos_west, pos_north)))
            ret.append(next_row)

        if symmetric:
            ret = self.make_symmetric(ret)
        return numpy.array(ret)

    def create_simple(self, size, range, symmetric=False):
        """Creates a procedural terrain map

           Starts with corner points [[a, b], [c, d]] and converts it into [[a, e, b], [f, g, h], [c, i, d]]
           where:
           e = (a+b)/2 + (random change)
           f = (a+c)/2 + (random change)
           g = (a+b+c+d)/4 + (random change)
           h = (b+d)/2 + (random change)
           i = (c+d)/2 + (random change)

           Repeat untill size is greater than required and truncate"""
        add_random_range = self.add_random_range

        ret = [[add_random_range(0, 0, range), add_random_range(0, 0, range)], [add_random_range(0, 0, range), add_random_range(0, 0, range)]]

        while len(ret) <= size[0]:
            new_ret = []

            for key_x, x in enumerate(ret):
                new_ret.append(x)

                if key_x != len(ret) - 1:
                    next_row = []
                    for key_y, pos_south in enumerate(x):
                        pos_north = ret[key_x+1][key_y]
                        pos_avg = (pos_north + pos_south)/2
                        if pos_avg <= 0:
                            next_row.append(add_random_range(pos_avg, 0, 1))
                        elif pos_avg >= range:
                            next_row.append(add_random_range(pos_avg, -1, 0))
                        else:
                            next_row.append(add_random_range(pos_avg, -1, 1))
                    new_ret.append(next_row)
            ret = new_ret

            new_ret = []
            for key_x, x in enumerate(ret):
                next_row = [x[0]]
                for key_y, pos_east in enumerate(x[1:]):
                    pos_west = next_row[-1]
                    if key_x % 2 and not key_y % 2:
                        pos_north = ret[key_x-1][key_y+1]
                        pos_south = ret[key_x+1][key_y+1]
                        pos_avg = (pos_north + pos_south + pos_east + pos_west)/4
                        if pos_avg <= 0:
                            next_row.append(add_random_range(pos_avg, 0, 1))
                        elif pos_avg >= range:
                            next_row.append(add_random_range(pos_avg, -1, 0))
                        else:
                            next_row.append(add_random_range(pos_avg, -1, 1))
                    else:
                        pos_avg = (pos_east + pos_west)/2
                        if pos_avg <= 0:
                            next_row.append(add_random_range(pos_avg, 0, 1))
                        elif pos_avg >= range:
                            next_row.append(add_random_range(pos_avg, -1, 0))
                        else:
                            next_row.append(add_random_range(pos_avg, -1, 1))
                    next_row.append(pos_east)
                new_ret.append(next_row)
            ret = new_ret

        ret = [x[:size[0]] for x in ret][:size[0]]

        if symmetric:
            ret = self.make_symmetric(ret)
        return numpy.array(ret)
    
    def create_perlin(self, size, roughness, symmetric = False):
        (width, height) = size
        values = numpy.zeros(size)
        noise = numpy.random.random_sample((width+1, height+1))
        octaves = (256, 8, 2)
        for y in range(height):
            for x in range(width):
                if symmetric and x < y:
                    values[x][y] = values[y][x]
                    continue
                nr = 1
                for i in octaves:
                    top = y/i
                    left = x/i
                    my = float(y % i) / i
                    mx = float(x % i) / i
                    values[x][y] += self.interpolate(noise[top][left], noise[top][left+1], noise[top+1][left], noise[top+1][left+1], mx, my) * math.pow(0.5, nr)
                    nr += 1
                values[x][y] = int(values[x][y] * roughness)
        return numpy.array(values,dtype=int)
    
    #Some helper functions.
    def interpolate(self, p1, p2, p3, p4, x, y):
        top = self.interpolate1d(p1, p2, x)
        bottom = self.interpolate1d(p3, p4, x)
        return self.interpolate1d(top, bottom, y)
        
    def interpolate1d(self, p1, p2, mu):
        return p1*(1-mu)+p2*mu

    def add_random_range(self, x, rand_min, rand_max):
        """Returns a number that is between x + rand_min and x + rand_max (inclusive)"""
        return x + random.randrange(rand_min, rand_max + 1)

    def make_symmetric(self, ret):
        """Takes a 2-dimentional list and makes it symmetrical about the north-west / south-east axis"""
        for x in xrange(len(ret)):
            for y in xrange(x):
                ret[x][y] = ret[y][x]

        return ret

########NEW FILE########
__FILENAME__ = tournament
#!/usr/bin/env python

import sys
import ConfigParser
from cells import Game

config = ConfigParser.RawConfigParser()

def get_mind(name):
    full_name = 'minds.' + name
    __import__(full_name)
    mind = sys.modules[full_name]
    mind.name = name
    return mind

bounds = None  # HACK
symmetric = None
mind_list = None

def main():
    global bounds, symmetric, mind_list
    try:
        config.read('tournament.cfg')
        bounds = config.getint('terrain', 'bounds')
        symmetric = config.getboolean('terrain', 'symmetric')
        minds_str = str(config.get('minds', 'minds'))

    except Exception as e:
        print 'Got error: %s' % e
        config.add_section('minds')
        config.set('minds', 'minds', 'mind1,mind2')
        config.add_section('terrain')
        config.set('terrain', 'bounds', '300')
        config.set('terrain', 'symmetric', 'true')

        with open('tournament.cfg', 'wb') as configfile:
            config.write(configfile)

        config.read('tournament.cfg')
        bounds = config.getint('terrain', 'bounds')
        symmetric = config.getboolean('terrain', 'symmetric')
        minds_str = str(config.get('minds', 'minds'))
    mind_list = [(n, get_mind(n)) for n in minds_str.split(',')]

    # accept command line arguments for the minds over those in the config
    try:
        if len(sys.argv)>2:
            mind_list = [(n,get_mind(n)) for n in sys.argv[1:] ]
    except (ImportError, IndexError):
        pass


if __name__ == "__main__":
    main()
    scores = [0 for x in mind_list]
    tournament_list = [[mind_list[a], mind_list[b]] for a in range(len(mind_list)) for b in range (a)]
    for n in range(4):
        for pair in tournament_list:
            game = Game(bounds, pair, symmetric, 5000, headless = True)
            while game.winner == None:
                game.tick()
            if game.winner >= 0:
                idx = mind_list.index(pair[game.winner])
                scores[idx] += 3
            if game.winner == -1:
                idx = mind_list.index(pair[0])
                scores[idx] += 1
                idx = mind_list.index(pair[1])
                scores[idx] += 1
            print scores
            print [m[0] for m in mind_list]
    names = [m[0] for m in mind_list]
    name_score = zip(names,scores)
    f = open("scores.csv",'w')
    srt = sorted(name_score,key=lambda ns: -ns[1])
    for x in srt:
        f.write("%s;%s\n" %(x[0],str(x[1])))
    f.close()

########NEW FILE########
