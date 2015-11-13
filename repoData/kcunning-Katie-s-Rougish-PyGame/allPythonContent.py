__FILENAME__ = admin
import sys
import os
import xml.etree.ElementTree as etree
from xml.dom.minidom import parseString

sys.path.append(os.path.join("roguey", "classes"))

from items import Treasure
from constants import *

def prettify(element):
	# Helper function to make XML look more prettier
    txt = etree.tostring(element)
    return parseString(txt).toprettyxml()

class Admin(object):
	def __init__(self):
		# Load the existing treasures
		f = open(
			os.path.join(
				"roguey",
				"resources",
				"items.xml",
				)
			)
		self.treasures = etree.fromstring(f.read())
		f.close()
		# trim the annoying whitespace...
		self.treasures.text = ""
		for element in self.treasures.iter():
			element.text = element.text.strip()
			element.tail = ""
		# Load the list of treasure type templates
		f = open(
			os.path.join(
				"roguey",
				"resources",
				"item_templates.xml",
				)
			)
		self.treasure_templates = etree.fromstring(f.read())
		f.close()
		# Enter main loop
		self.running = True
		self.main()		

	def new_treasure(self):
		item_attributes = {}  # This will hold optional stats only.

		template_options = [
			template.find("item_type").text for template in self.treasure_templates
		]

		# Gather the mandatory attributes
		selection = self.prompt_for_selection(
			prompt="Choose an item type",
			options=template_options
		)
		item_type = template_options[selection]
		template = self.treasure_templates[selection]

		title = raw_input("Give it a title: ")
		description = raw_input("Give it a description: ")

		# Check if this template requires any additional attributes
		for attr in template:
			if attr.tag == "item_type":
				continue
			prompt = attr.attrib["prompt"]
			value_type = attr.attrib.get("type", "string")  # type defaults to "string" if not specified
			item_attributes[attr.tag] = (raw_input("%s (%s): " % (prompt, value_type)), value_type)

		# finally we can add this new item to the list
		new_item = etree.SubElement(self.treasures, "item")
		etree.SubElement(new_item, "item_type").text = item_type
		etree.SubElement(new_item, "title").text = title
		etree.SubElement(new_item, "description").text = description
		for attrib, value in item_attributes.iteritems():
			optional_stat = etree.SubElement(new_item, attrib)
			optional_stat.text, optional_stat.attrib["type"] = value

	def list_treasures(self):
		for treasure in self.treasures:
			print treasure.find('title').text.strip()

	def save_and_quit(self):
		f = open("roguey/resources/items.xml", "w")
		f.write(prettify(self.treasures))
		f.close()
		self.running = False

	def quit_without_save(self):
		is_sure_about_quitting = self.yes_no_prompt(
			"Are you super sure you want to quit without saving?"
		)
		if is_sure_about_quitting:
			self.running = False

	def delete_treasure(self):
		options = [element.find('title').text for element in self.treasures]
		prompt = "Select a treasure to delete: "
		selection = self.prompt_for_selection(prompt, options)
		confirmation_prompt = (
			'Do you really want to delete "%s"?'
			% options[selection]
			)
		sure_about_deleting = self.yes_no_prompt(confirmation_prompt)
		if sure_about_deleting:
			self.treasures.remove(self.treasures[selection])

	def main(self):
		menu_options_with_actions = [
			("Make a new treasure", self.new_treasure),
			("List current treasures", self.list_treasures),
			("Delete a treasure", self.delete_treasure),
			("Save and quit", self.save_and_quit),
			("Quit without saving", self.quit_without_save)
		]
		menu_options = [x[0] for x in menu_options_with_actions]
		menu_prompt = "Make a choice"

		while self.running:
			selection = self.prompt_for_selection(menu_prompt, menu_options)
			# Call the appropriate action based on the user selection
			menu_options_with_actions[selection][1]()

	def prompt_for_selection(self, prompt, options):
		"""Given a list of options and a prompt,
		get the users selection and return the index of the selected option
		"""
		retval = None
		# Print out the numbered options
		for i, option in enumerate(options):
			print "%3s. %s" % (i+1, option)
		# Continue to prompt user until valid input is recieved.
		while retval == None:
			# Get the users selection
			selection = raw_input("%s: " % prompt)
			# Check that the input is valid integer
			try:
				retval = int(selection) - 1
			except ValueError:
				print "Invalid input. Please enter a number."
				continue
			# Ensure input is within the valid range
			if retval < 0 or retval >= len(options):
				print ("Please enter a number between 1 and %d inclusive." 
					% len(options))
				retval = None  # reset the illegal value
				continue
		return retval

	def yes_no_prompt(self, prompt):
		'''Prompt for a yes/no answer. 
		Will accept any response beginning with Y, N, y or n.
		Returns a bool.'''
		retval = None
		selection = raw_input("%s (Y/N): " % prompt)
		# Continue to prompt user until valid input starts with "Y" or "N".
		while retval == None:
			first_letter = selection.strip()[0].upper()
			try:
				retval = {
					"Y": True,
					"N": False
				}[first_letter]
			except KeyError:
				pass
		return retval


if __name__ == "__main__":
	a = Admin()

########NEW FILE########
__FILENAME__ = main
import pygame, math, sys, random
from pygame.locals import *

sys.path.append("roguey/classes")

from constants import *
from items import Treasure
from gamemap import Map
from monsters import Monster
from player import Inventory
from game import Game

def main():
    while 1:
        pygame.init()
        game = Game()

if __name__ == "__main__":
        main()

########NEW FILE########
__FILENAME__ = combat
from player import Player
from monsters import Derpy

from random import randint

class Combat(object):

	def __init__(self, player, monster):
		self.player = player
		self.monster = monster
		self.fight()

	def fight(self):
		'''For now, we'll always start with the player.'''
		# Player, try to hit the monster!
		hit_attempt = randint(0, self.player.attack)
		if hit_attempt > self.monster.defense:
			damage = self.player.strength
			self.monster.receive_damage(damage)

		# Monster, try to hit back.
		if self.monster.current_hp > 0:
			hit_attempt = randint(0, self.monster.attack)
			if hit_attempt > self.player.defense:
				damage = self.monster.strength
				self.player.receive_damage(damage)
########NEW FILE########
__FILENAME__ = constants
from os.path import abspath, dirname, join, sep

MOVEMENT_SIZE = 12
RADIUS = 2
BLACK = (0,0,0)
WHITE = (255, 255, 255)
COLUMNS = 16
ROWS = 21
TREASURES = 10
MAX_ROOMS = 10
MONSTERS = 12
TILE_SIZE = 48
DIRECTIONS = ['north', 'south', 'east', 'west']
LONG_STRING = "X" * 50

EQUIPMENT_TYPES = ('hat', 'shirt', 'pants', 'shoes', 'back', 'neck', 'hands', 'weapon')
START_EQUIPMENT = {}
for treasure in EQUIPMENT_TYPES:
	START_EQUIPMENT[treasure] = None

TREASURE_TYPES = ('hat', 'shirt', 'pants', 'shoes', 'back', 'neck', 'hands', 'weapon', 'trash')

IMG_DIR = join(
	dirname(dirname(abspath(__file__))),
	"images"
	) + sep

STATS = ('strength', 'attack', 'defense')

########NEW FILE########
__FILENAME__ = game
import pygame, sys, pickle
from pygame.locals import *

from constants import *
from items import Treasure
from gamemap import Map
from monsters import Derpy
from player import Inventory, Player
from combat import Combat
from gamescreen import GameScreen

class Game(object):
    ''' The game object. Controls rendering the game and moving the player.
    '''
    def __init__(self):
        ''' Sets up the initial game board, with the player at a set position.
                Once everything is set up, starts the game.
        '''
        # Set up the screen
        self.screen = GameScreen()
        self.bg = pygame.image.load(IMG_DIR + 'rainbowbg.png')

        # Set up some game components
        self.inventory = Inventory()
        self.map = Map()
        self.map.player = (1*TILE_SIZE, 1*TILE_SIZE)
        self.player_stats = Player()
        treasure = self.map.clear_treasure(self.map.player)
        if treasure:
            self.add_treasure(treasure)

        self.clock = pygame.time.Clock()
        self.direction = 0
        
        self.map.clear_block(self.map.player)
        self.map.set_current_position(self.map.player)

        self.screen.draw_screen_layers(player_stats=self.player_stats, map=self.map)
        
        self.run()

    def add_treasure(self, treasure):
        ''' Adds the treasure to the player's inventory
        '''
        text = "You found a %s. %s" % (treasure.title, treasure.description)
        self.inventory.add_to_inventory(treasure, self.player_stats)
        self.screen.draw_alert(text)

    def move(self, hor, vert):
        ''' Moves the player, given a keypress. 
            Also evaluates if the player needs to fight or pick up some treasure.
        '''
        self.old_row, self.old_col = self.map.player
        row = self.old_row + hor
        col = self.old_col + vert
        if row > (ROWS-1) * TILE_SIZE or row < 0 or col > (COLUMNS-1) * TILE_SIZE or col < 0:
            return
        if self.map.has_wall(row, col):
            return
        if self.map.has_monster(row, col):
            Combat(self.player_stats, self.map.monsters[row/TILE_SIZE][col/TILE_SIZE])
            if self.map.monsters[row/TILE_SIZE][col/TILE_SIZE].current_hp <= 0:
                pass #put death throes here
            if self.player_stats.current_hp <= 0:
                self.end_game()
            self.move(0,0)
            return
        self.map.player = (row, col)
        self.map.player = (row, col)
        self.map.clear_block(self.map.player)
        self.map.set_current_position(self.map.player)
        treasure = self.map.clear_treasure(self.map.player)
        if treasure:
            self.add_treasure(treasure)
            self.screen.draw_inventory(self.inventory)
            self.screen.draw_equipment(self.player_stats.equipped)

    def refresh_screen(self):
        self.screen.draw_player(self.map.player)
        self.screen.draw_screen_layers(self.map, self.player_stats)

    def end_game(self):
        ''' The exit screen for when the player has died, or completed the game. 
            So far, all it does is exit the game.
        '''
        sys.exit()

    def run(self):
        ''' The main loop of the game.
        '''
        # Fix for double move from Joshua Grigonis! Thanks!
        hor = 0
        vert = 0
        while 1:
            self.clock.tick(30)
            for event in pygame.event.get():
                if event.type == QUIT:
                    sys.exit(0)
                if event.type == KEYDOWN:
                    if event.key == K_ESCAPE: 
                        sys.exit(0)
                    if event.key == K_LEFT:
                        hor = -TILE_SIZE
                        vert = 0
                    if event.key == K_RIGHT:
                        hor = TILE_SIZE
                        vert = 0
                    if event.key == K_UP:
                        vert = -TILE_SIZE
                        hor = 0
                    if event.key == K_DOWN:
                        vert = TILE_SIZE
                        hor = 0
                if event.type == KEYUP:
                    # updates only occur is player has moved.
                    if vert or hor:
                        self.move(hor, vert)
                        self.map.move_monsters()
                        hor = 0
                        vert = 0    
            self.refresh_screen()
########NEW FILE########
__FILENAME__ = gamemap
# INTIALISATION
import pygame, math, sys, random, pickle
from pygame.locals import *
from random import randint, choice
import xml.etree.ElementTree as etree

from constants import *
from items import Treasure
from monsters import Derpy

class Map(object):
    ''' Stores the values for the map, but doesn't render it for the game. 

        Map.cleared = The cleared squares
    '''
    def __init__(self):
        ''' Sets all squares to uncleared.
        '''
        self.cleared = self.get_blank_map()
        self.current = self.get_blank_map()
        self.treasure = self.get_blank_map()
        self.walls = self.get_blank_map()
        self.monsters = self.get_blank_map()
        self.player = (0,0)
        self.floor = self.get_blank_map() 
        self.roomlist = []

        self.get_rooms()
        self.connect_rooms()

        all_treasures = self.get_all_treasures()
        for i in range(TREASURES):
            while 1:
                col = random.randint(0, COLUMNS-1)
                row = random.randint(0, ROWS-1)
                if not self.treasure[row][col] and self.floor[row][col]:
                    self.treasure[row][col] = choice(all_treasures)
                    break

        for i in range(MONSTERS):
            while 1:
                col = random.randint(0, COLUMNS-1)
                row = random.randint(0, COLUMNS-1)
                if not self.treasure[row][col] and self.floor[row][col]:
                    self.monsters[row][col] = Derpy()
                    break
        self.fill_map()

    def get_all_treasures(self):
        f = open("roguey/resources/items.xml")
        root = etree.fromstring(f.read())
        treasures = [Treasure.from_xml(t) for t in root]
        f.close()
        return treasures

    def fill_map(self):
        for i in range(ROWS):
            for j in range(COLUMNS):
                    if not self.floor[i][j]:
                        self.walls[i][j] = 1

    def get_rooms(self):
        # Set initial room
        room = self.check_room(coord=(0,0), height=5, length=5)
        self.roomlist.append(room)
        rooms = 1
        keep_going = 50
        while rooms <= MAX_ROOMS and keep_going:
            height = randint(4,10)
            length = randint(4,10)
            x = randint(0, COLUMNS-1)
            y = randint(0, ROWS)
            room = self.check_room(coord=(x,y), height=height, length=length)
            if room:
                rooms += 1
                self.roomlist.append(room)
            else:
                keep_going -=1
        for room in self.roomlist:
            self.make_random_door(room)

    def connect_rooms(self):
        for room in self.roomlist:
            i = self.roomlist.index(room)
            try:
                next = self.roomlist[i+1]
            except:
                next = self.roomlist[0]
            if room.door[0] < next.door[0]:
                start = room.door[0]
                end = next.door[0]
            else:
                start = next.door[0]
                end = room.door[0]
            for x in range(start, end):
                self.walls[x][room.door[1]] = 0
                self.floor[x][room.door[1]] = 1
            if room.door[1] < next.door[1]:
                start = room.door[1]
                end = next.door[1]
            else:
                start = next.door[1]
                end = room.door[1]
            for y in range(start, end):
                self.walls[next.door[0]][y] = 0
                self.floor[next.door[0]][y] = 1

    def check_room(self, coord, height, length):
        ''' Are all the spaces in a room free?
        '''
        for i in range(0, height):
            for j in range(0, length):
                if coord[1] + i > COLUMNS-1:
                    return False
                if coord[0] + j > ROWS-1:
                    return False
                if self.floor[coord[0]+j][coord[1]+i]:
                    return False
        room = Room(start=coord, height=height, width=length)
        self.create_room(room)
        return room

    def make_random_door(self, room):
        while True:
            wall = choice(DIRECTIONS)
            if wall in ['north', 'south']:
                block = randint(1, room.width-2)
            else:
                block = randint(1, room.height-2)
            if wall == 'north':
                coord = (room.start[0]+block,room.start[1])
                check = (coord[0], coord[1]-1)
                next = (coord[0], coord[1]-2)
            if wall == 'south':
                coord = (room.start[0]+block, room.start[1]+room.height-1)
                check = (coord[0], coord[1]+1)
                next = (coord[0], coord[1]+1)
            if wall == 'east':
                coord = (room.start[0],room.start[1]+block)
                check = (coord[0]-1, coord[1])
                next = (coord[0]-2, coord[1])
            if wall == 'west':
                coord = (room.start[0]+room.width-1, room.start[1]+block)
                check = (coord[0]+1, coord[1])
                next = (coord[0]+2, coord[1])
            door = self.check_door(coord, check, next)
            if door:
                self.walls[coord[0]][coord[1]] = 0
                self.floor[coord[0]][coord[1]] = 2
                room.door = (coord[0],coord[1])
                return

    def check_door(self, coord, check, next):
        # Is it at the bounds?
        if check[0] < 0 or check[1] < 0:
            return False
        # Is it next to a wall?
        try:
            if self.walls[check[0]][check[1]]:
                # Is that wall next to another wall?
                if self.walls[next[0]][next[1]]:
                    return False
                else:
                    try:
                        self.walls[check[0]][check[1]] = 0
                    except:
                        pass # Sometimes, we're one away from the border. That's okay.
        except:
            return False
        return True


    def create_room(self, room):
        # make top and bottom walls
        for i in range(0, room.width):
            self.walls[room.start[0]+i][room.start[1]] = 1
            self.walls[room.start[0]+i][room.start[1]+room.height-1] = 1
        # make side walls
        for i in range(0, room.height):
            self.walls[room.start[0]][room.start[1]+i] = 1
            self.walls[room.start[0]+room.width-1][room.start[1]+i] = 1
        # fill in the floor
        for x in range (1, room.width-1):
            for y in range (1, room.height-1):
                self.floor[room.start[0]+x][room.start[1]+y] = 1

        

    def get_blank_map(self):
        ''' Returns a map with all values set to 0
        '''
        map = []
        for i in range(ROWS):
                        row = []
                        for j in range(COLUMNS):
                                row.append(0)
                        map.append(row)
        return map
    
    def is_block_empty(self, row, col):
        if not self.treasure[row][col] and not self.monsters[row][col] and not self.walls[row][col]\
        and not (self.player[0]/TILE_SIZE, self.player[1]/TILE_SIZE) == (row, col):
            return True
        else:
            return False

    def has_wall(self, row, col):
        row = row/TILE_SIZE
        col = col/TILE_SIZE
        if self.walls[row][col]:
            return True
        else:
            return False

    def has_monster(self, row, col):
        row = row/TILE_SIZE
        col = col/TILE_SIZE
        if self.monsters[row][col]:
            return True
        else:
            return False
    
    def set_current_position(self, position):
        self.current = self.get_blank_map()
        row, col = position
        row = row/TILE_SIZE
        col = col/TILE_SIZE
        self.current[row][col] = 1
        for i in range(RADIUS):
            if row-i > 0:
                self.current[row-i-1][col] = 1
            if row+i < ROWS-1:
                self.current[row+i+1][col] = 1
            if col-i > 0:
                self.current[row][col-i-1] = 1
            if col+i < COLUMNS-1:
                self.current[row][col+i+1] = 1
        for i in range(RADIUS-1):
            if row-i > 0 and col-i > 0: self.current[row-i-1][col-i-1] = 1
            if row-i > 0 and col-i < COLUMNS-1: self.current[row-i-1][col+i+1] = 1
            if row+i < ROWS-1 and col-i > 0: self.current[row+i+1][col-i-1] = 1
            if row+i < ROWS-1 and col+i < COLUMNS-1: self.current[row+i+1][col+i+1] = 1

    def clear_block(self, position):
        ''' Given the current position of the player, sets the current square to completely cleared, 
                and the squares nearby to partially cleared.
        '''
        x, y = position
        col = y/TILE_SIZE
        row = x/TILE_SIZE
        
        self.cleared[row][col] = 1
        if row < ROWS-1:
            self.cleared[row+1][col] = 1
        if row > 0:
            self.cleared[row-1][col] = 1
        if col < COLUMNS-1:
            self.cleared[row][col+1] = 1
        if col > 0:
            self.cleared[row][col-1] = 1
    
    def get_all_monsters(self):
        monsters = {}
        for row in range(ROWS):
            for col in range(COLUMNS):
                if self.monsters[row][col]:
                    monsters[self.monsters[row][col]] = [row, col]
        return monsters

    def clear_treasure(self, position):
        ''' Given a position, clears the treasure from it, and returns the treasure.
        ''' 
        x, y = position
        row = x/TILE_SIZE
        col = y/TILE_SIZE
        treasure = self.treasure[row][col]
        self.treasure[row][col] = 0
        return treasure

    def print_ascii_map(self):
        ''' Prints an ascii map to the console. For troubleshooting only.
        '''
        for row in self.floor:
            print row, row.__len__()

    def move_monsters(self):
        monsters = self.get_all_monsters()
        for monster in monsters.keys():
            if monster.current_hp <= 0:
                r, c = monsters[monster]
                self.monsters[r][c] = 0
            else:
                d = random.sample(DIRECTIONS, 1)[0]
                new_row, new_col = row, col = monsters[monster]
                if d == "north":
                    new_row -= 1
                if d == "south":
                    new_row += 1
                if d == "east":
                    new_col += 1
                if d == "west":
                    new_col -= 1
                try:
                    if self.is_block_empty(new_row, new_col) and new_row > 0 and new_col > 0:
                        self.monsters[new_row][new_col] = monster
                        self.monsters[row][col] = 0
                except:
                    pass # Monsters can run into walls, edges, chests, etc. It consumes their turn.

class Room(object):

    def __init__(self, height=5, width=5, start=(0,0)):
        self.title = "Generic room"
        self.start = start
        self.width = width
        self.height = height
        self.end = (self.start[0]+self.width, self.start[1]+self.width)
        self.door = []
########NEW FILE########
__FILENAME__ = gamescreen
import pygame

from constants import *

class GameScreen(object):
    
    def __init__(self):
        ''' Does the initial drawing of the game screen.
        '''
        self.selected_tile = [0, 0]
        self.screen = pygame.display.set_mode((1280, 832))
        self.font = pygame.font.SysFont(None, 48)
        self.small_font = pygame.font.SysFont(None, 20)
        self.bg = pygame.image.load(IMG_DIR + 'rainbowbg.png')
        self.player_blit = pygame.image.load(IMG_DIR + 'dude.png')
        self.monster_blit = pygame.image.load(IMG_DIR + 'dumb_monster.png')
        self.selection_blit = pygame.image.load(IMG_DIR + 'selection.png')
        self.treasure_blit = pygame.image.load(IMG_DIR + 'chest.png')
        self.wall_tile = pygame.image.load(IMG_DIR + 'wall.png')
        self.floor_tile = pygame.image.load(IMG_DIR + 'floor.png')
        self.screen.blit(self.bg, (0,0))
        self.inventory_screen = self.small_font.render("Inventory", True, WHITE, BLACK)
        self.equipment_screen = self.small_font.render("Equipment", True, WHITE, BLACK)
        self.draw_alert("Welcome to Katie's Roguelike!")
        self.stats_screen = self.small_font.render("ARGH", True, WHITE, BLACK)
        self.draw_inventory()
        self.draw_equipment()
        pygame.display.flip()

    def draw_player(self, coord):
        ''' Draws the player at a specific coordinate
        '''
        self.screen.blit(self.player_blit, coord)

    def draw_stats(self, player_stats, color=WHITE):
        ''' Renders the stats for the player
        '''
        self.screen.blit(self.stats_screen, (1008, 0))
        self.stats_screen = self.small_font.render(player_stats.name, True, color, BLACK)
        self.screen.blit(self.stats_screen, (1008, 0))
        self.stats_screen = self.small_font.render("Level: " + str(player_stats.level), True, color, BLACK)
        self.screen.blit(self.stats_screen, (1008, 15))
        self.stats_screen = self.small_font.render("HP: %s/%s" % (str(player_stats.current_hp), str(player_stats.max_hp)), True, color, BLACK)
        self.screen.blit(self.stats_screen, (1008, 30))
        line = 30
        for stat in STATS:
            if hasattr(player_stats, stat):
                s = str(getattr(player_stats, stat))
            else:
                s = str(player_stats.stats[stat])
            self.stats_screen = self.small_font.render("%s: %s" % (stat, s), True, color, BLACK)
            self.screen.blit(self.stats_screen, (1008, line+15))
            line += 15
        self.stats_screen = self.small_font.render("Armor: %s" % player_stats.get_armor(), True, color, BLACK)
        self.screen.blit(self.stats_screen, (1008, line))
        line += 15

    def draw_alert(self, alert, color=WHITE):
        ''' Draws the alert box at the bottom 
        '''
        self.alert = self.font.render(LONG_STRING, True, BLACK, BLACK)
        self.screen.blit(self.alert, (0, 790))
        try:
            pygame.display.flip()
        except:
            pass
        self.alert = self.font.render(alert, True, color, BLACK)
        self.screen.blit(self.alert, (0, 790))
        pygame.display.flip()

    def draw_equipment(self, equipment=START_EQUIPMENT):
        ''' Renders the equipment. Expect it to be exchanged for something
            awesomer
        ''' 
        self.screen.blit(self.equipment_screen, (1008, 200))
        for i in range(equipment.keys().__len__()):
            line = self.small_font.render(LONG_STRING, True, BLACK, BLACK)
            self.screen.blit(line, (1008, ((i+1)*15)+200))
        pygame.display.flip()
        i = 1
        for slot in EQUIPMENT_TYPES:
            try:
                line_text = slot + ":   " + equipment[slot].title
            except:
                line_text = slot + ":   "
            line = self.small_font.render(line_text, True, WHITE, BLACK)
            self.screen.blit(line, (1008, i*15+200))
            i += 1
        pygame.display.flip()

    def draw_inventory(self, inventory=None):
        ''' Renders the inventory for the user
        '''
        self.screen.blit(self.inventory_screen, (1008, 400))
        if inventory:
            items = inventory.get_items()
        else:
            items = []
        for i in range(items.__len__()):
            line = self.small_font.render(LONG_STRING, True, BLACK, BLACK)
            self.screen.blit(line, (1008, ((i+1)*15)+400))
        pygame.display.flip()
        for item in items:
            line = self.small_font.render(item.title, True, WHITE, BLACK)
            self.screen.blit(line, (1008, (items.index(item)+1)*15+400))

    def draw_treasure(self, treasure_map):
        ''' Draws the treasure chests yet to be opened.
        '''
        for row in range(ROWS):
            for col in range(COLUMNS):
                if treasure_map[row][col] != 0:
                    self.screen.blit(
                        self.treasure_blit,
                        (row*TILE_SIZE, col*TILE_SIZE))
    
    def draw_monsters(self, map):
        ''' Draws monsters that appear in the area that the rogue can see
        '''
        for row in range(ROWS):
            for col in range(COLUMNS):
                #if map.monsters[row][col] != 0 and map.current[row][col] != 0:
                if map.monsters[row][col] != 0:
                    self.screen.blit(
                        self.monster_blit,
                        (row*TILE_SIZE, col*TILE_SIZE))
    
    def draw_walls(self, walls, tile):
        ''' Draws walls on the game map
        '''
        for row in range(ROWS):
            for col in range(COLUMNS):
                if walls[row][col] != 0:
                    self.screen.blit(tile, (row*TILE_SIZE, col*TILE_SIZE))

    def draw_darkness(self, map):
        ''' Draws the darkness and shadows on the board. 0 is dark, 1 is in shadows,
        '''
        for row in range(ROWS):
            for col in range(COLUMNS):
                if map.cleared[row][col] == 0:
                    if not map.current[row][col]:
                        pygame.draw.rect(self.screen, BLACK, (row*TILE_SIZE, col*TILE_SIZE, TILE_SIZE, TILE_SIZE))  
                if map.cleared[row][col] == 1:
                    if not map.current[row][col]:
                        shadow = pygame.Surface((TILE_SIZE, TILE_SIZE))
                        shadow.set_alpha(200)
                        shadow.fill(BLACK)
                        self.screen.blit(shadow, (row*TILE_SIZE, col*TILE_SIZE))

    def draw_background(self):
        ''' Draws my glorious background.
        '''
        self.screen.blit(self.bg, (0,0))

    def draw_selection_square(self):
        '''Draw a selection square at the current mouse position
        '''
        mouse_pos = pygame.mouse.get_pos()
        self.selected_tile = [c / TILE_SIZE for c in mouse_pos]
        selection_pos = [c * TILE_SIZE for c in self.selected_tile]
        self.screen.blit(self.selection_blit, selection_pos)

    def draw_selected_square_info(self, map):
        '''Draw some info regarding the contents of the currently selected square'''
        x, y = self.selected_tile
        try:
            if map.monsters[x][y]:
                self.stats_screen = self.small_font.render(str(map.monsters[x][y]), True, (0, 255, 0, 255))
                self.screen.blit(self.stats_screen, (0, 0))
        except IndexError:
            # mouse probably off the map
            pass

    def draw_screen_layers(self, map, player_stats):
        ''' Draws the layers of the game screen
        '''
        self.draw_background()
        self.draw_walls(map.floor, self.floor_tile)
        self.draw_walls(map.walls, self.wall_tile)
        self.draw_treasure(map.treasure)
        self.draw_monsters(map)
        #self.draw_darkness(map)
        self.draw_stats(player_stats=player_stats)
        self.draw_player(coord=map.player)
        self.draw_selection_square()
        self.draw_selected_square_info(map)
        pygame.display.flip()

    def animate_move(self, hor, vert, blit):
        ''' This function is NOT USED. In theory, it animates a blit, but it makes everything look awful.
        '''
        if vert:
            if vert > 0:
                for i in range(TILE_SIZE/MOVEMENT_SIZE):
                    self.draw_screen_layers()
                    self.screen.blit(self.__getattribute__(blit), [self.old_row, self.old_col+i*MOVEMENT_SIZE])
                    pygame.display.update()
            else:
                for i in range(TILE_SIZE/MOVEMENT_SIZE):
                    self.draw_screen_layers()
                    self.screen.blit(self.__getattribute__(blit), [self.old_row, self.old_col-i*MOVEMENT_SIZE])
                    pygame.display.update()
        if hor:
            if hor > 0:
                for i in range(TILE_SIZE/MOVEMENT_SIZE):
                    self.draw_screen_layers()
                    self.screen.blit(self.__getattribute__(blit), [self.old_row+i*MOVEMENT_SIZE, self.old_col])
                    pygame.display.update()
            else:
                for i in range(TILE_SIZE/MOVEMENT_SIZE):
                    self.draw_screen_layers()
                    self.screen.blit(self.__getattribute__(blit), [self.old_row-i*MOVEMENT_SIZE, self.old_col])
                    pygame.display.update()
########NEW FILE########
__FILENAME__ = items
# INTIALISATION
import pygame, math, sys, random
from pygame.locals import *

from constants import *

class Treasure(object):
    ''' Not implemented yet. 
    '''
    def __init__(self, title, description, item_type, **kwargs):
        # These attributes are required for all Treasures
        self.title = title
        self.description = description
        self.item_type = item_type

        # The rest of the attibutes are optional depending on the item type
        [setattr(self, key, value) for key, value in kwargs.iteritems()]
        
    @classmethod
    def from_xml(cls, xml):
        """
        Creates a Treasure object from an etree XML object.
        Treasures can have abitrary attribute but must always have
        the required attributes, 'title', 'description', 'item_type'.
        If the XML element describing a Treasure attribute has
        a "type" attribute in its XML tag, this can be used to convert
        its value to int or float.
        """
        attribs = {}
        for element in xml:
            attribute = element.tag
            value = element.text.strip()

            # convert to appropriate type if that attribute is supplied
            if "type" in element.attrib:
                # the "type" attribute tells us what to convert this value to.
                attr_type = element.attrib["type"]
                try:
                    # Hopefully the "type" attribute is "int" or "float"
                    value = {
                        "int": int,
                        "float": float,
                        "string": str,
                    }[attr_type](value)
                except KeyError:
                    print "%s attribute has illegal 'type' attribute '%d'"
                    print "Supported conversion types: 'int', 'float', 'string'"

            attribs[attribute] = value

        # Now that we have all of the attribute, we can create the treasure
        # Note that if any of the required arguments of name, description and
        # item_type are absent, this will raise an exception
        return cls(**attribs)


########NEW FILE########
__FILENAME__ = monsters
# INTIALISATION
import pygame, math, sys, random
from pygame.locals import *

class Monster(object):
	def __init__(self):
		pass

	@property
	def attack(self):
		return self.stats['attack']

	def receive_damage(self, damage):
		self.current_hp -= damage

	@property
	def defense(self):
		return self.stats['defense']

	@property
	def strength(self):
		return self.stats['strength']

	def __str__(self):
		return (
			"%s | Level %d | HP (%d/%d) | attack %d | defense %d | strength %d" %
			(
				self.title,
				self.level,
				self.current_hp,
				self.max_hp,
				self.stats['attack'],
				self.stats['defense'],
				self.stats['strength']
				)
			)

class Derpy(Monster):
	def __init__(self):
		self.title = "Derpy Slime"
		self.level = 1
		self.stats ={
			'attack': 5,
			'defense': 1,
			'strength': 1,
		}
		self.current_hp = 3
		self.max_hp = 3
		
class RatBird(Monster):
	def __init__(self):
		self.title = "Ratbird"
		self.level = 2
		self.stats = {
			'attack': 7,
			'defense': 2,
			'strength': 2,
		}
		self.max_hp = 5
		self.current_hp = self.max_hp
########NEW FILE########
__FILENAME__ = player
from constants import *

class Inventory(object):
    ''' The inventory for the player.
    '''

    def __init__(self):
        ''' Sets up the initial blank inventory.
        '''
        self.inventory = {}

    def get_items(self):
        return self.inventory.keys()

    def add_to_inventory(self, item, player):
        ''' Adds an item to the inventory
        '''
        if item.item_type == "trash":
            return
        if player.equipped[item.item_type ]:
            try:
                self.inventory[item] += 1
            except:
                self.inventory[item] = 1
        else:
            player.equip_item(item)


class Player(object):
    """The player class. Contains level, HP, stats, and deals with combat."""
    def __init__(self):
        self.level = 1
        self.stats = {
            'strength': 1,
            'attack': 1,
            'defense': 5
        }
        self.current_hp = 10
        self.name = "Dudeguy McAwesomesauce"
        self.equipped = {}

        for treasure in EQUIPMENT_TYPES:
            self.equipped[treasure] = None

    @property
    def max_hp(self):
        return 10 + (self.level-1)*5

    @property
    def defense(self):
        return self.stats['defense'] + self.get_armor()

    @property
    def strength(self):
        return self.stats['strength']

    def get_armor(self):
        armor = 0
        for slot in self.equipped.keys():
            if self.equipped[slot]:
                try:
                    armor += self.equipped[slot].armor
                except AttributeError:
                    # The Treasure in this slot doesn't have an 'armor' attribute
                    pass
                except TypeError:
                    # The Treasure in this slot has an armor stat, however it
                    # appears to be a non numeric type. Make sure this Treasures armor stat
                    # has the attribute type="int" in its XML definition.
                    # This sort of error should probably get properly logged somewhere
                    print (
                        'Please make sure the armor stat for the "%s" weapon '
                        'has the type="int" attribute in its XML definition' % self.equipped[slot].title
                    )

        return armor

    def receive_damage(self, damage):
        self.current_hp -= damage

    def attempt_block(self, attack):
        pass

    @property
    def attack(self):
        atk = 0
        if self.equipped['weapon']:
            try:
                atk += self.equipped['weapon'].damage
            except AttributeError:
                # This weapon does not have a "damage" attribute. This may not
                # be an error; it may just suck.
                pass
            except TypeError:
                # The weapon has a damage attribute, however it
                # appears to be non numeric type. Make sure this damage stat
                # has the attribute type="int" in its XML definition.
                # This sort of error should probably get properly logged somewhere
                print (
                    'Please make sure the armor stat for the "%s" weapon '
                    'has the type="int" attribute in its XML definition' % self.equipped['weapon'].title
                )
        return self.stats['attack'] + atk

    def equip_item(self, item):
        self.equipped[item.item_type] = item


        
########NEW FILE########
