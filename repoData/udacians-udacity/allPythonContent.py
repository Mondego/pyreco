__FILENAME__ = classes
#!/usr/bin/env python
# game.py - simple game to demonstrate classes and objects
import random

CHR_PLAYER = "S"
CHR_ENEMY = "B"
CHR_WIZARD = "W"
CHR_ARCHER = "A"
CHR_DEAD = "X"

class StatusBar(object):
    def __init__(self, character = None):
        self.character = character
        self.msg = ''
    
    def set_character(self, character):
        self.character = character
        self.set_status()
        self.show()
        
    def set_status(self, msg = ''):
        self.msg = (msg, '::'.join((self.msg, msg)))[len(self.msg) > 0]
        status = "HP: %i/%i" % (self.character.hp, self.character.max_hp)
        msgs = self.msg.split('::')
        
        self.line1 = "%s + %s" % (status, msgs[0])
        if len(msgs) > 1:
            self.line2 = "%s + %s" % (' ' * len(status), msgs[1])
        else:
            self.line2 = "%s + %s" % (' ' * len(status), ' ' * len(msgs[0]))

    def format_line(self, txt, width):
        line = "+ %s" % txt
        line += " " * (width - (len(line))) + " +"
        return line

    def show(self):
        self.set_status()
        print "+" * (world.width + 2)
        print self.format_line(self.line1, world.width)
        print self.format_line(self.line2, world.width)
        self.msg = ''

statusbar = StatusBar()

class WorldMap(object):
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.map = [[None for y in range(self.height)] for x in range(self.width)]

    def is_occupied(self, x, y):
        ''' Checks if a given space on the map and returns True if occupied. '''
        return self.map[x][y] is not None

    def print_map(self):
        print '+' * (self.width + 2)
        for y in range(self.height - 1, 0, -1):
            line = '+'
            for x in range(self.width):
                cell = self.map[x][y]
                if cell is None:
                    line += ' '
                else:
                    line += cell.image
            print line + '+'
        print '+' * (self.width + 2)

world = WorldMap(60, 22)

#world = [[None for x in range(100)] for y in range(100)]

class Entity:
    def __init__(self, x, y, image):
        self.x = x
        self.y = y
        world.map[x][y] = self
        self.image = image
    
    def occupy(self, x, y):
        world.map[x][y] = self

    def remove(self):
        world.map[self.x][self.y] = None

    def distance(self, other):
        return abs(other.x - self.x), abs(other.y - self.y)

class Character(Entity):
    def __init__(self, x, y, image, hp, damage = 10):
        Entity.__init__(self, x, y, image)
        self.hp, self.max_hp = hp, hp
        self.damage = damage
        self.items = []

    def _direction_to_dxdy(self, direction):
        """Convert a string representing movement direction into a tuple
        (dx, dy), where 'dx' is the size of step in the 'x' direction and
        'dy' is the size of step in the 'y' direction."""
        dx, dy = 0, 0
        if direction == 'left':
            dx = -1
        elif direction == 'right':
            dx = 1
        elif direction == 'up':
            dy = 1
        elif direction == 'down':
            dy = -1
        return dx, dy

    def new_pos(self, direction):
        '''
            Calculates a new position given a direction. Takes as input a 
            direction 'left', 'right', 'up' or 'down'. Allows wrapping of the 
            world map (eg. moving left from x = 0 moves you to x = -1)
        '''
        dx, dy = self._direction_to_dxdy(direction)
        new_x = (self.x + dx) % world.width
        new_y = (self.y + dy) % world.height
        return new_x, new_y

    def move(self, direction):
        """
            Moves the character to the new position.
        """
        new_x, new_y = self.new_pos(direction)
        if world.is_occupied(new_x, new_y):
            statusbar.set_status('Position is occupied, try another move.')
        else:
            self.remove()
            self.x, self.y = new_x, new_y
            self.occupy(self.x, self.y)

    def attack(self, enemy):
        dist = self.distance(enemy)
        if dist == (0, 1) or dist == (1, 0):
            if not enemy.hp:
                msgs = [
                    "This body doesn't look delicious at all.",
                    "You really want me to do this?",
                    "Yeah, whatever!",
                    "I killed it! What did you make me do!"
                    ]
                statusbar.set_status(random.choice(msgs))
            else:
                # Possible damage is depending on physical condition
                worst = int((self.condition() * 0.01) ** (1/2.) * self.damage + 0.5)
                best = int((self.condition() * 0.01) ** (1/4.) * self.damage + 0.5)
                damage = (worst == best) and best or random.randrange(worst, best)
                
                # Possible damage is also depending on sudden adrenaline
                # rushes and aiming accuracy or at least butterfly flaps
                damage = random.randrange(
                    (damage-1, 0)[not damage],
                    (damage+1, self.damage)[damage == self.damage])
                enemy.harm(damage)
                
                if enemy.image == CHR_PLAYER:
                    statusbar.set_status("You are being attacked: %i damage." % damage)
                elif self.image == CHR_PLAYER:
                    if enemy.image == CHR_DEAD:
                        statusbar.set_status("You make %i damage: your enemy is dead." % damage)
                    else:
                        statusbar.set_status("You make %i damage: %s has %i/%i hp left." % \
                            (damage, enemy.image, enemy.hp, enemy.max_hp))
        else:
            msgs = [
                "Woah! Kicking air really is fun!",
                "This would be totally ineffective!",
                "Just scaring the hiding velociraptors..."
                ]
            statusbar.set_status(random.choice(msgs))
            

    def condition(self):
        return (self.hp * 100) / self.max_hp

    def harm(self, damage):
        self.hp -= damage
        if self.hp <= 0:
            self.image = CHR_DEAD
            self.hp = 0

    def get_all_enemies_at_distance(self, dist):
        """Return a list of all enemies that are exactly 'dist' cells away
        either horizontally or vertically.
        """
        coords = [((self.x + dist) % world.width, self.y % world.height),
                  ((self.x - dist) % world.width, self.y % world.height),
                  (self.x % world.width, (self.y + dist) % world.height),
                  (self.x % world.width, (self.y - dist) % world.height)]
        enemies = []
        for x, y in coords:
            if world.is_occupied(x, y) and isinstance(world.map[x][y], Enemy):
                enemies.append(world.map[x][y])
        return enemies

    def get_all_enemies(self, max_dist=1):
        """Return a list of all enemies that are at most 'max_dist' cells away
        either horizontally or vertically.
        """
        enemies = []
        for dist in range(1, max_dist+1):
            enemies.extend(self.get_all_enemies_at_distance(dist))
        return enemies

    def get_alive_enemies_at_distance(self, dist):
        """Return a list of alive enemies that are exactly 'dist' cells away
        either horizontally or vertically.
        """
        enemies = self.get_all_enemies_at_distance(dist)
        return [enemy for enemy in enemies if enemy.hp > 0]

    def get_alive_enemies(self, max_dist=1):
        """Return a list of alive enemies that are at most 'max_dist' cells away
        either horizontally or vertically.
        """
        enemies = self.get_all_enemies(max_dist)
        return [enemy for enemy in enemies if enemy.hp > 0]

class Player(Character):
    def __init__(self, x, y, hp):
        Character.__init__(self, x, y, CHR_PLAYER, hp)
    
class Enemy(Character):
    def __init__(self, x, y, hp):
        Character.__init__(self, x, y, CHR_ENEMY, hp)

    # not used
    def challenge(self, other):
        print "Let's fight!"
        
    def act(self, character, directions):
        # No action if dead X-(
        if not self.hp:
            return False
            
        choices = [0, 1]
        
        dist = self.distance(character)
        if dist == (0, 1) or dist == (1, 0):
            choices.append(2)
        choice = random.choice(choices)
        
        if choice == 1:
            # Running away
            while (True):
                goto = directions[random.choice(directions.keys())]
                new_x, new_y = self.new_pos(goto)
                if not world.is_occupied(new_x, new_y):
                    self.move(goto)
                    break
        elif choice == 2:
            # Fighting back
            self.attack(character)

class Wizard(Character):
    def __init__(self, x, y, hp):
        Character.__init__(self, x, y, CHR_WIZARD, hp)

    def cast_spell(self, name, target):
        """Cast a spell on the given target."""
        if name == 'remove':
            self._cast_remove(target)
        elif name == 'hp-stealer':
            self._cast_hp_stealer(target)
        else:
            print "The wizard does not know the spell '{0}' yet.".format(name)

    def _cast_remove(self, enemy):
        dist = self.distance(enemy)
        if dist == (0, 1) or dist == (1, 0):
            enemy.remove()

    def _cast_hp_stealer(self, enemy):
        dist = self.distance(enemy)
        if dist == (0, 3) or dist == (3, 0):
            enemy.harm(3)
            self.hp += 3

class Archer(Character):
    def __init__(self, x, y, hp):
        Character.__init__(self, x, y, CHR_ARCHER, hp)
    
    def range_attack(self, enemy):
        dist = self.distance(enemy)
        if (dist[0] <= 5 and dist[1] == 0) or (dist[0] == 0 and dist[1] <= 5):
            enemy.harm(5)

########NEW FILE########
__FILENAME__ = game
#!/usr/bin/env python
# game.py - simple game to demonstrate classes and objects
from classes import *
        
DIRECTIONS = {
    "r": "right",
    "l": "left",
    "d": "down",
    "u": "up"
}

if __name__ == '__main__':

    print """Welcome to 'Hello, Class' game
    Available commands are:
    r - move right
    l - move left
    u - move up
    d - move down
    a - attack
    gps - print location
    x - exit
    
    There is a Bug 2 steps to the right from you.
    You should probably do something about it!
    """

    # initializing some entities

    #campus = World(100, 100)
    student = Player(10, 10, 100)
    engineer = Wizard(35, 14, 100)
    bug1 = Enemy(12, 10, 100)
    bug2 = Enemy(11, 11, 100)
    
    statusbar.set_character(student)
    world.print_map()

    while True:
        c = raw_input("You > ")
        
        if c == "x":
            break
        elif c in DIRECTIONS:
            student.move(DIRECTIONS[c])
            bug1.act(student, DIRECTIONS)
        elif c == "gps":
            statusbar.set_status("Your GPS location: %i %i" % (student.x, student.y))
            statusbar.set_status("Bug GPS location: %i %i" % (bug1.x, bug1.y))
        elif c == "a":
            enemies = student.get_alive_enemies(1)
            if enemies:
                student.attack(enemies[0])
                enemies[0].act(student, DIRECTIONS)
        else:
            statusbar.set_status("Unknown command. 'x' to exit game")
            
        statusbar.show()
        world.print_map()



########NEW FILE########
__FILENAME__ = pquiz
# Udacity tool to submit and download programming quizzes
# by: Karl-Aksel Puulmann, macobo@ut.ee

import cookielib
import urllib
import urllib2
import json
import re
import getpass
import os
import time

rootURL = r"http://www.udacity.com"
ajaxRoot = r"http://www.udacity.com/ajax"
cookieFile = r".\cookie.lwp"

coursePath = {
    # Intro to Computer Science. Building a Search Engine
    "cs101": r"Course/cs101/CourseRev/apr2012",
    # Web Application Engineering. How to Build a Blog
    "cs253": r"Course/cs253/CourseRev/apr2012",
    # Programming Languages. Building a Web Browser
    "cs262": r'Course/cs262/CourseRev/apr2012',
    # Artificial Intelligence. Programming a Robotic Car
    "cs373": r"Course/cs373/CourseRev/apr2012",
    # Design of Computer Programs. Programming Principles
    "cs212": r"Course/cs212/CourseRev/apr2012",
    # Algorithms. Crunching Social Networks
    "cs215": r"Course/cs215/CourseRev/1",
    # Applied Cryptography. Science of Secrets
    "cs387": r"Course/cs387/CourseRev/apr2012",
    # Software Testing. How to Make Software Fail
    "cs258": r"Course/cs258/CourseRev/1",
    # Statistics 101
    "st101": r"Course/st101/CourseRev/1"
}

courseCache = {}
csrf_token = None
uVersion = None
logged_in = False
cookie_jar = None

def log_in():
    """ Logs you in so you can submit a solution. Saves
        the cookie on disk. """
    global logged_in, cookie_jar
    email = raw_input("Email: ")
    # Try to ask for password in a way that shoulder-surfers can't handle
    pw = getpass.getpass("Password: ")
    print ("") # Empty line for clarity
    data = {"data":
                {"email":email,
                 "password":pw},
            "method":"account.sign_in",
            "version":uVersion,
            "csrf_token":csrf_token}
    try:
        answer = jsonFromURL(ajaxRoot, json.dumps(data))
    except urllib2.HTTPError, error:
        contents = error.read()
        print(contents)
        raise
    if 'error' in answer['payload']:
        raise ValueError("Failed to log in!")

    cookie_jar.save()
    print("Logged in successfully!\n")
    logged_in = True
        
def setSessionHandler():
    """ Gets information from udacity home page to successfully
        query courses.
        If user has saved a cookie on disk, tries to use that. """
    global uVersion, csrf_token, cookie_jar, logged_in

    cookie_jar = cookielib.LWPCookieJar(cookieFile)
    if os.access(cookieFile, os.F_OK):
        logged_in = True
        cookie_jar.load()
        print("Found a cookie!")
        
    opener = urllib2.build_opener(
            urllib2.HTTPCookieProcessor(cookie_jar))
    urllib2.install_opener(opener)

    print("Accessing udacity main page...\n")
    uMainSiteHTML = urllib2.urlopen(rootURL).read()
    # get uVersion - used when querying
    uVersion = re.findall(r"js/udacity.js[?]([0-9]+)", uMainSiteHTML)[0]
    uVersion = "dacity-"+uVersion
    # get csrf_token - used for logging in
    csrf_token = re.findall(r'csrf_token = "([^"]+)', uMainSiteHTML)[0]

# -- Utility functions --
def jsonFromURL(url, data=None):
    return json.loads(urllib2.urlopen(url, data).read())

def findPair(key, value, json_array):
    """ Finds first dictionary that where key corresponds to value
        in an array of dictionaries """
    for x in json_array:
        if x is not None and key in x and x[key] == value:
            return x
    raise ValueError("(key, value) pair not in list")

def ajaxURL(query):
    return ajaxRoot + "?" + urllib.quote(json.dumps(query))

def sanitize(path):
    """ Sanitizes unit names so they can be used as folder paths """
    illegalChars = r'<>:"/\|?*'
    for ch in illegalChars:
        path = path.replace(ch, "")
    return path

def stripHTML(text):
    return re.sub(r"<.*?>", "", text)

# -- Functions related to getting course-related info --
def courseJSON(courseID):
    """ Returns the JSON-formatted info about this course """
    if courseID not in courseCache:
        query = {"data":{"path":coursePath[courseID]},
                 "method": "course.get",
                 "version": uVersion}
        print("Getting course info...")
        url = ajaxURL(query)
        courseCache[courseID] = jsonFromURL(url)['payload']
    return courseCache[courseID]
        

def unitJSON(courseID, unitName):
    """ Returns the JSON of this unit from the API """
    courseJS = courseJSON(courseID)
    for unit in courseJS['course_rev']['units']: 
        if unit['name'] == unitName:
            return unit
    raise ValueError("No unit named {0} found!".format(unitName))

def programPath(unitJSON, n):
    """ Given the JSON covering the unit, returns the nth part programming quiz path """
    partKeys = unitJSON['nuggetLayout'][n-1] # The keys to parts of part n
    nuggets = unitJSON['nuggets']
    for v in partKeys: # one of the parts should be a programming quiz
        if v is not None:
            part = findPair('key', v['nugget_key'], nuggets)
            type_of_lecture = part['nuggetType']
            if type_of_lecture == "program":
                return part['path']
    raise ValueError("Found no programming quiz for this part")

def programmingQuiz(courseID, unit, part):
    """ Returns the program text for Udacity cs-courseID unit part quiz """
    print("Getting default program text...")
    path = programPath(unitJSON(courseID, unit), part)
    query = {"data":{"path": path},
             "method":"assignment.ide.get",
             "version": uVersion}
    url = ajaxURL(query)
    queryAnswer = jsonFromURL(url)
    return queryAnswer['payload']['nugget']['suppliedCode']


def downloadProgram(courseID, unit, part):  
    """ Downloads the specific program and places it as
        ./courseID/Unit/part.py in the file tree
        (./ means current folder)
        Places a token on the first line to identify the file. """
    text = programmingQuiz(courseID, unit, part)
    coursePath = os.path.join(os.curdir, str(courseID))
    if not os.path.exists(coursePath):
        os.mkdir(coursePath)

    unitSanitized = sanitize(unit)
    unitPath = os.path.join(coursePath, unitSanitized)
        
    if not os.path.exists(unitPath):
        os.mkdir(unitPath)
    fileName = "{0}.py".format(part)
    filePath = os.path.join(unitPath, fileName)
    if os.path.exists(filePath):
        raise ValueError("File already exists")
    with open(filePath, "w") as out:
        # Add info to help identify file
        out.write("# {0} ; {1} ; {2}\n".format(courseID, unit, part))
        out.write('\n'.join(text.split("\r\n")))

def downloadUnit(courseID, unit):
    unitJS = unitJSON(courseID, unit)
    parts = len(unitJS['nuggetLayout'])
    for part in range(1, parts+1):
        print('{0}: {1} part {2}'.format(courseID, unit, part))
        try:
            downloadProgram(courseID, unit, part)
        except ValueError:
            pass

def downloadCourse(courseID):
    """ Downloads all units in this course """
    courseJS = courseJSON(courseID)
    for unit in courseJS['course_rev']['units']:
        unitName = unit['name']
        print('{0}: {1}'.format(courseID, unitName))
        downloadUnit(courseID, unitName)


# -- Functions related to submitting a file --
def identifyFile(first_line):
    """ Tries to identify file by its first line, which must
        be in the following form: "# CourseID ; Unit ; Part" """
    if first_line[:2] != '# ':
        raise ValueError("First line doesn't identify file")
    try:
        course, unit, part = first_line[2:].strip().split(' ; ')
    except:
        raise ValueError("First line doesn't identify file")
    return course, unit, int(part)

def submit(program_file):
    """ Submits a file, trying to identify it by its first line """
    with open(program_file) as f:
        first_line = f.readline() # identifier line
        program_text = f.read()
    course, unit, part = identifyFile(first_line)
    status = submitSolution(program_text, course, unit, part)

def submitSolution(program_text, courseID, unit, part):
    print("Submitting your solution for {0} {1} Part {2}\n".format(
                                                    courseID, unit, part))
    global logged_in
    if not logged_in:
        log_in()
    path = programPath(unitJSON(courseID, unit), part)
    # Send the program as a query
    print("Sending sending your program to the servers...\n")
    query = {"data":{"usercode":program_text,
                     "op":"submit",
                     "path":path},
             "method":"assignment.ide.exe",
             "version":uVersion,
             "csrf_token":csrf_token}
    req = urllib2.Request(ajaxRoot, json.dumps(query))
    response1 = json.loads(urllib2.urlopen(req).read())
    # Ask from the server how we did
    query = {"data": {"ps_key": response1['payload']['ps_key']},
             "method":"assignment.ide.result",
             "version":uVersion}
    queryURL = ajaxURL(query)
    for _ in range(20):
        specifics = jsonFromURL(queryURL)
        if specifics['payload']['status'] != 'queued':
            print("\nThe server responded:")
            print(stripHTML(specifics['payload']['comment']))
            return specifics['payload']
        print("Your program is still being graded. Trying again in 1 second")
        time.sleep(1)
    print("Your program didn't recieve a response in 20 tries. :(")

def main():
    import argparse

    epilog = """Example:
    pquiz.py --submit --file 1.py OR
    pquiz.py -s -f 1.py
    pquiz.py --download --course 212"""
    parser = argparse.ArgumentParser(description= \
                "Tool to help download and upload programming quizzes "+
                "from Udacity's CS courses", 
                epilog = epilog,
                formatter_class = argparse.RawDescriptionHelpFormatter)
    parser.add_argument("-s", "--submit",
                        action='store_true',
                        help="submit a file")
    parser.add_argument("-d", "--download",
                        action='store_true',
                        help="download a programming quiz")
    parser.add_argument("-c", "--course",
                        metavar="CID",
                        help="Course ID (eg cs262, st101)")
    parser.add_argument("-u", "--unit",
                        help='Unit title (eg "Unit 5", "Homework 2")')
    parser.add_argument("-p", "--part",
                        type=int,
                        help="part number")
    parser.add_argument("-f", "--file",
                        help="path to file")
    
    args = parser.parse_args()

    if args.course and args.course not in coursePath:
        print "Course " + args.course + " is not supported!"
        return
    
    if args.submit and not args.download:
        setSessionHandler()
        if args.course and args.unit and args.part and args.file:
            program_text = open(args.file).read()
            submitSolution(program_text, args.course, args.unit, args.part)
        elif args.file:
            submit(args.file)
        else:
            parser.print_help()
    elif args.download and not args.submit:
        setSessionHandler()
        if args.course and args.unit and args.part:
            downloadProgram(args.course, args.unit, args.part)
        elif args.course and args.unit:
            downloadUnit(args.course, args.unit)
        elif args.course:
            downloadCourse(args.course)
        else:
            parser.print_help()
    else:
        parser.print_help()

if __name__ == "__main__":
    main()

########NEW FILE########
