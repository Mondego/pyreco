__FILENAME__ = example
import time
import pygame
import pygame.constants as c

score = 0

screenDimensions = pygame.Rect((0,0,400,100))

black = (0,0,0)
white = (255,255,255)
blue  = (0,0,255)
red   = (255,0,0)

class Monkey(pygame.sprite.Sprite):
    def __init__(self):
        self.stunTimeout = None
        self.velocity = 2
        super(Monkey, self).__init__()
        self.image = pygame.Surface((60,60))
        self.rect = self.image.get_rect()
        self.render(blue)

    def render(self, color):
        '''draw onto self.image the face of a monkey in the specified color'''
        self.image.fill(color)
        pygame.draw.circle(self.image, white, (10,10), 10, 2)
        pygame.draw.circle(self.image, white, (50,10), 10, 2)
        pygame.draw.circle(self.image, white, (30,60), 20, 2)

    def attempt_punch(self, pos):
        '''If the given position (pos) is inside the monkey's rect, the monkey
        has been "punched".  A successful punch will stun the monkey and
        increment the global score.
        The monkey cannot be punched if he is already stunned
        '''
        if self.stunTimeout:
            return # already stunned
        if self.rect.collidepoint(pos):
            # Argh!  The punch intersected with my face!
            self.stunTimeout = time.time() + 2 # 2 seconds from now
            global score
            score += 1
            self.render(red)

    def update(self):
        if self.stunTimeout:
            # If stunned, the monkey doesn't move
            if time.time() > self.stunTimeout:
                self.stunTimeout = None
                self.render(blue)
        else:
            # Move the monkey
            self.rect.x += self.velocity
            # Don't let the monkey run past the edge of the viewable area
            if self.rect.right > screenDimensions.right:
                self.velocity = -2
            elif self.rect.left < screenDimensions.left:
                self.velocity = 2


sprites = pygame.sprite.Group()

def init():
    # Necessary Pygame set-up...
    pygame.init()
    clock = pygame.time.Clock()
    displayImg = pygame.display.set_mode(screenDimensions.size)
    monkey = Monkey()
    sprites.add(monkey)

    return (clock, displayImg)

def handle_events(clock):
    for event in pygame.event.get():
        if event.type == c.QUIT:
            return False
        elif event.type == c.MOUSEBUTTONDOWN:
            for sprite in sprites:
                if isinstance(sprite, Monkey):
                    sprite.attempt_punch(event.pos)

    clock.tick(60) # aim for 60 frames per second
    for sprite in sprites:
        sprite.update()

    return True

def draw_to_display(displayImg):
    displayImg.fill(black)
    for sprite in sprites:
        displayImg.blit(sprite.image, sprite.rect)
    pygame.display.flip()

def main():
    clock, displayImg = init()

    keepGoing = True

    while keepGoing:
        keepGoing = handle_events(clock)
        draw_to_display(displayImg)

if __name__ == '__main__':
    main()
    print 'Your score was', score

########NEW FILE########
__FILENAME__ = example
import time
import pygame
import pygame.constants as c

score = 0

screenDimensions = pygame.Rect((0,0,400,100))

black = (0,0,0)
white = (255,255,255)
blue  = (0,0,255)
red   = (255,0,0)

class Monkey(pygame.sprite.Sprite):
    def __init__(self):
        self.stunTimeout = None
        self.velocity = 2
        super(Monkey, self).__init__()
        self.image = pygame.Surface((60,60))
        self.rect = self.image.get_rect()
        self.render(blue)

    def render(self, color):
        '''draw onto self.image the face of a monkey in the specified color'''
        self.image.fill(color)
        pygame.draw.circle(self.image, white, (10,10), 10, 2)
        pygame.draw.circle(self.image, white, (50,10), 10, 2)
        pygame.draw.circle(self.image, white, (30,60), 20, 2)

    def attempt_punch(self, pos):
        '''If the given position (pos) is inside the monkey's rect, the monkey
        has been "punched".  A successful punch will stun the monkey and
        increment the global score.
        The monkey cannot be punched if he is already stunned
        '''
        if self.stunTimeout:
            return # already stunned
        if self.rect.collidepoint(pos):
            # Argh!  The punch intersected with my face!
            self.stunTimeout = time.time() + 2 # 2 seconds from now
            global score
            score += 1
            self.render(red)

    def update(self):
        if self.stunTimeout:
            # If stunned, the monkey doesn't move
            if time.time() > self.stunTimeout:
                self.stunTimeout = None
                self.render(blue)
        else:
            # Move the monkey
            self.rect.x += self.velocity
            # Don't let the monkey run past the edge of the viewable area
            if self.rect.right > screenDimensions.right:
                self.velocity = -2
            elif self.rect.left < screenDimensions.left:
                self.velocity = 2

    def do_special(self):
        print 'monkey does special'

class Trap(pygame.sprite.Sprite):
    def __init__(self):
        self.image = pygame.Surface((20,20))
        self.rect = self.image.get_rect()
        self.render(red)

    def render(self, color):
        '''draw onto self.image the face of a monkey in the specified color'''
        self.image.fill(color)
        pygame.draw.circle(self.image, white, (10,10), 10, 2)
        pygame.draw.circle(self.image, white, (50,10), 10, 2)
        pygame.draw.circle(self.image, white, (30,60), 20, 2)

    def do_special(self):
        print 'trap does special'

sprites = pygame.sprite.Group()

def init():
    # Necessary Pygame set-up...
    pygame.init()
    clock = pygame.time.Clock()
    displayImg = pygame.display.set_mode(screenDimensions.size)
    monkey = Monkey()
    sprites.add(monkey)

    return (clock, displayImg)

def some_other_events():
    return []

def from_somewhere():
    return "yeah, this is pretty special alright"

def generate_events(clock):
    for event in pygame.event.get():
        yield event

    clock.tick(60) # aim for 60 frames per second
    yield 'ClockTick'

    for event in some_other_events():
        yield event

    specialEvent = from_somewhere()
    yield 'SpecialEvent'

event_type_B, event_type_C, event_type_D = 1,2,3

def handle_events(clock):
    for event in generate_events(clock):
        if event == 'ClockTick':
            for sprite in sprites:
                sprite.update()
        elif event == 'SpecialEvent':
            for sprite in sprites:
                sprite.do_special()
        # handle those events that came from some_other_events()
        elif event.type == c.QUIT:
            return False
        elif event.type == c.MOUSEBUTTONDOWN:
            for sprite in sprites:
                if isinstance(sprite, Monkey):
                    sprite.attempt_punch(event.pos)
        elif event.type == event_type_B:
            for sprite in sprites:
                if isinstance(sprite, Trap):
                     pass
        elif event.type == event_type_C:
            pass
        elif event.type == event_type_D:
            pass
    return True

def draw_to_display(displayImg):
    displayImg.fill(black)
    for sprite in sprites:
        displayImg.blit(sprite.image, sprite.rect)
    pygame.display.flip()

def main():
    clock, displayImg = init()

    keepGoing = True

    while keepGoing:
        keepGoing = handle_events(clock)
        draw_to_display(displayImg)

if __name__ == '__main__':
    main()
    print 'Your score was', score

########NEW FILE########
__FILENAME__ = example
import time
import pygame
import pygame.constants as c

score = 0

screenDimensions = pygame.Rect((0,0,400,100))

black = (0,0,0)
white = (255,255,255)
blue  = (0,0,255)
red   = (255,0,0)

class Monkey(pygame.sprite.Sprite):
    def __init__(self):
        self.stunTimeout = None
        self.velocity = 2
        super(Monkey, self).__init__()
        self.image = pygame.Surface((60,60))
        self.rect = self.image.get_rect()
        self.render(blue)

    def render(self, color):
        '''draw onto self.image the face of a monkey in the specified color'''
        self.image.fill(color)
        pygame.draw.circle(self.image, white, (10,10), 10, 2)
        pygame.draw.circle(self.image, white, (50,10), 10, 2)
        pygame.draw.circle(self.image, white, (30,60), 20, 2)

    def attempt_punch(self, pos):
        '''If the given position (pos) is inside the monkey's rect, the monkey
        has been "punched".  A successful punch will stun the monkey and
        increment the global score.
        The monkey cannot be punched if he is already stunned
        '''
        if self.stunTimeout:
            return # already stunned
        if self.rect.collidepoint(pos):
            # Argh!  The punch intersected with my face!
            self.stunTimeout = time.time() + 2 # 2 seconds from now
            global score
            score += 1
            self.render(red)

    def update(self):
        if self.stunTimeout:
            # If stunned, the monkey doesn't move
            if time.time() > self.stunTimeout:
                self.stunTimeout = None
                self.render(blue)
        else:
            # Move the monkey
            self.rect.x += self.velocity
            # Don't let the monkey run past the edge of the viewable area
            if self.rect.right > screenDimensions.right:
                self.velocity = -2
            elif self.rect.left < screenDimensions.left:
                self.velocity = 2

    def do_special(self):
        print 'monkey does special'

    def on_event(self, event):
        if event == 'ClockTick':
            self.update()
        elif event == 'SpecialEvent':
            self.do_special()
        elif event.type == c.MOUSEBUTTONDOWN:
            self.attempt_punch(event.pos)
        # notice that Monkey doesn't do anything on event_type_B
        elif event.type == event_type_C:
            pass
        elif event.type == event_type_D:
            pass


class Trap(pygame.sprite.Sprite):
    def __init__(self):
        self.image = pygame.Surface((20,20))
        self.rect = self.image.get_rect()
        self.render(red)

    def render(self, color):
        '''draw onto self.image the face of a monkey in the specified color'''
        self.image.fill(color)
        pygame.draw.circle(self.image, white, (10,10), 10, 2)
        pygame.draw.circle(self.image, white, (50,10), 10, 2)
        pygame.draw.circle(self.image, white, (30,60), 20, 2)

    def do_special(self):
        print 'trap does special'
    def add_some_honey(self):
        print 'trap adds honey'

    def on_event(self, event):
        if event == 'ClockTick':
            self.update()
        elif event == 'SpecialEvent':
            self.do_special()
        # notice that Trap doesn't do anything on MOUSEBUTTONDOWN
        elif event.type == event_type_B:
            self.add_some_honey()
        elif event.type == event_type_C:
            pass
        elif event.type == event_type_D:
            pass


sprites = pygame.sprite.Group()

def init():
    # Necessary Pygame set-up...
    pygame.init()
    clock = pygame.time.Clock()
    displayImg = pygame.display.set_mode(screenDimensions.size)
    monkey = Monkey()
    sprites.add(monkey)

    return (clock, displayImg)

def some_other_events():
    return []

def from_somewhere():
    return "yeah, this is pretty special alright"

def generate_events(clock):
    for event in pygame.event.get():
        yield event

    clock.tick(60) # aim for 60 frames per second
    yield 'ClockTick'

    for event in some_other_events():
        yield event

    specialEvent = from_somewhere()
    yield 'SpecialEvent'

event_type_B, event_type_C, event_type_D = 1,2,3

def handle_events(clock):
    for event in generate_events(clock):
        if hasattr(event, 'type') and event.type == c.QUIT:
            return False
        for sprite in sprites:
            sprite.on_event(event)
    return True

def draw_to_display(displayImg):
    displayImg.fill(black)
    for sprite in sprites:
        displayImg.blit(sprite.image, sprite.rect)
    pygame.display.flip()

def main():
    clock, displayImg = init()

    keepGoing = True

    while keepGoing:
        keepGoing = handle_events(clock)
        draw_to_display(displayImg)

if __name__ == '__main__':
    main()
    print 'Your score was', score

########NEW FILE########
__FILENAME__ = example
import time
import pygame
import pygame.constants as c

score = 0

screenDimensions = pygame.Rect((0,0,400,100))

black = (0,0,0)
white = (255,255,255)
blue  = (0,0,255)
red   = (255,0,0)

class EventHandlingSprite(pygame.sprite.Sprite):
    def on_ClockTick(self):
        self.update()
    def on_Special(self):
        'sprite got special'


class Monkey(EventHandlingSprite):
    def __init__(self):
        self.stunTimeout = None
        self.velocity = 2
        super(Monkey, self).__init__()
        self.image = pygame.Surface((60,60))
        self.rect = self.image.get_rect()
        self.render(blue)

    def render(self, color):
        '''draw onto self.image the face of a monkey in the specified color'''
        self.image.fill(color)
        pygame.draw.circle(self.image, white, (10,10), 10, 2)
        pygame.draw.circle(self.image, white, (50,10), 10, 2)
        pygame.draw.circle(self.image, white, (30,60), 20, 2)

    def attempt_punch(self, pos):
        '''If the given position (pos) is inside the monkey's rect, the monkey
        has been "punched".  A successful punch will stun the monkey and
        increment the global score.
        The monkey cannot be punched if he is already stunned
        '''
        if self.stunTimeout:
            return # already stunned
        if self.rect.collidepoint(pos):
            # Argh!  The punch intersected with my face!
            self.stunTimeout = time.time() + 2 # 2 seconds from now
            global score
            score += 1
            self.render(red)

    def update(self):
        if self.stunTimeout:
            # If stunned, the monkey doesn't move
            if time.time() > self.stunTimeout:
                self.stunTimeout = None
                self.render(blue)
        else:
            # Move the monkey
            self.rect.x += self.velocity
            # Don't let the monkey run past the edge of the viewable area
            if self.rect.right > screenDimensions.right:
                self.velocity = -2
            elif self.rect.left < screenDimensions.left:
                self.velocity = 2

    def on_PygameEvent(self, event):
        if event.type == c.MOUSEBUTTONDOWN:
            self.attempt_punch(event.pos)
        elif event.type == event_type_C:
            pass
        elif event.type == event_type_D:
            pass


class Trap(EventHandlingSprite):
    def __init__(self):
        self.image = pygame.Surface((20,20))
        self.rect = self.image.get_rect()
        self.render(red)

    def render(self, color):
        '''draw onto self.image the face of a monkey in the specified color'''
        self.image.fill(color)
        pygame.draw.circle(self.image, white, (10,10), 10, 2)
        pygame.draw.circle(self.image, white, (50,10), 10, 2)
        pygame.draw.circle(self.image, white, (30,60), 20, 2)

    def add_some_honey(self):
        print 'trap adds honey'

    def on_PygameEvent(self, event):
        if event.type == event_type_B:
            self.add_some_honey()
        elif event.type == event_type_C:
            pass
        elif event.type == event_type_D:
            pass

sprites = pygame.sprite.Group()

def init():
    # Necessary Pygame set-up...
    pygame.init()
    clock = pygame.time.Clock()
    displayImg = pygame.display.set_mode(screenDimensions.size)
    monkey = Monkey()
    sprites.add(monkey)

    return (clock, displayImg)

def some_other_events():
    return []

def from_somewhere():
    return "yeah, this is pretty special alright"

def generate_events(clock):
    for event in pygame.event.get():
        yield ('PygameEvent', event)

    clock.tick(60) # aim for 60 frames per second
    yield ('ClockTick', )

    for event in some_other_events():
        yield (event.__class__.__name__, event)

    specialEvent = from_somewhere()
    yield ('SpecialEvent', )

event_type_B, event_type_C, event_type_D = 1,2,3

def handle_events(clock):
    for eventTuple in generate_events(clock):
        if eventTuple[0] == 'PygameEvent' and eventTuple[1].type == c.QUIT:
            return False
        for sprite in sprites:
            methodName = 'on_' + eventTuple[0]
            if hasattr(sprite, methodName):
                method = getattr(sprite, methodName)
                method(*eventTuple[1:])
    return True

def draw_to_display(displayImg):
    displayImg.fill(black)
    for sprite in sprites:
        displayImg.blit(sprite.image, sprite.rect)
    pygame.display.flip()

def main():
    clock, displayImg = init()

    keepGoing = True

    while keepGoing:
        keepGoing = handle_events(clock)
        draw_to_display(displayImg)

if __name__ == '__main__':
    main()
    print 'Your score was', score

########NEW FILE########
__FILENAME__ = book_chapter1.example01
import time
import pygame
import pygame.constants as c

score = 0

screenDimensions = pygame.Rect((0,0,400,100))

black = (0,0,0)
white = (255,255,255)
blue  = (0,0,255)
red   = (255,0,0)

class Monkey(pygame.sprite.Sprite):
    def __init__(self):
        self.stunTimeout = None
        self.velocity = 2
        super(Monkey, self).__init__()
        self.image = pygame.Surface((60,60))
        self.rect = self.image.get_rect()
        self.render(blue)

    def render(self, color):
        '''draw onto self.image the face of a monkey in the specified color'''
        self.image.fill(color)
        pygame.draw.circle(self.image, white, (10,10), 10, 2)
        pygame.draw.circle(self.image, white, (50,10), 10, 2)
        pygame.draw.circle(self.image, white, (30,60), 20, 2)

    def attempt_punch(self, pos):
        '''If the given position (pos) is inside the monkey's rect, the monkey
        has been "punched".  A successful punch will stun the monkey and increment
        the global score.  The monkey cannot be punched if he is already stunned
        '''
        if self.stunTimeout:
            return # already stunned
        if self.rect.collidepoint(pos):
            # Argh!  The punch intersected with my face!
            self.stunTimeout = time.time() + 2 # 2 seconds from now
            global score
            score += 1
            self.render(red)

    def update(self):
        if self.stunTimeout:
            # If stunned, the monkey doesn't move
            if time.time() > self.stunTimeout:
                self.stunTimeout = None
                self.render(blue)
        else:
            # Move the monkey
            self.rect.x += self.velocity
            # Don't let the monkey run past the edge of the viewable area
            if self.rect.right > screenDimensions.right:
                self.velocity = -2
            elif self.rect.left < screenDimensions.left:
                self.velocity = 2


def main():
    pygame.init()
    clock = pygame.time.Clock()
    displayImg = pygame.display.set_mode(screenDimensions.size)
    monkey = Monkey()

    while True:
        for event in pygame.event.get():
            if event.type == c.QUIT:
                return
            elif event.type == c.MOUSEBUTTONDOWN:
                monkey.attempt_punch(event.pos)

        clock.tick(60) # aim for 60 FPS
        monkey.update()

        displayImg.fill(black)
        displayImg.blit(monkey.image, monkey.rect)
        pygame.display.flip()


if __name__ == '__main__':
    main()
    print 'Your score was', score

########NEW FILE########
__FILENAME__ = book_chapter3.example01
import time
import random
import pygame
import pygame.constants as c

score = 0

screenDimensions = pygame.Rect((0,0,400,60))

sprites = pygame.sprite.Group()

black = (0,0,0)
white = (255,255,255)
blue  = (0,0,255)
red   = (255,0,0)

class Monkey(pygame.sprite.Sprite):
    def __init__(self):
        self.stunTimeout = None
        self.origVelocity = 2
        self.velocity = 2
        super(Monkey, self).__init__()
        self.image = pygame.Surface((60,60))
        self.rect = self.image.get_rect()
        self.render(blue)

    def render(self, color):
        '''draw onto self.image the face of a monkey in the specified color'''
        self.image.fill(color)
        pygame.draw.circle(self.image, white, (10,10), 10, 2)
        pygame.draw.circle(self.image, white, (50,10), 10, 2)
        pygame.draw.circle(self.image, white, (30,60), 20, 2)

    def attempt_punch(self, pos):
        '''If the given position (pos) is inside the monkey's rect, the monkey
        has been "punched".  A successful punch will stun the monkey and increment
        the global score.  The monkey cannot be punched if he is already stunned
        '''
        if self.stunTimeout:
            return # already stunned
        if self.rect.collidepoint(pos):
            # Argh!  The punch intersected with my face!
            self.stunTimeout = time.time() + 2 # 2 seconds from now
            global score
            score += 1
            self.render(red)

    def adjust_speed(self, multiplier):
        if self.velocity > 0:
            self.velocity = multiplier * self.origVelocity
        if self.velocity < 0:
            self.velocity = multiplier * -self.origVelocity

    def update(self):
        if self.stunTimeout:
            # If stunned, the monkey doesn't move
            if time.time() > self.stunTimeout:
                self.stunTimeout = None
                self.render(blue)
        else:
            # Move the monkey
            self.rect.x += self.velocity
            # Don't let the monkey run past the edge of the viewable area
            if (self.rect.right > screenDimensions.right or
                self.rect.left < screenDimensions.left):
                self.velocity = -self.velocity


def init():
    # Necessary Pygame set-up...
    pygame.init()
    clock = pygame.time.Clock()
    displayImg = pygame.display.set_mode(screenDimensions.size)
    monkey = Monkey()
    sprites.add(monkey)

    return (clock, displayImg)

def get_opponent_score():
    time.sleep(random.random())
    return score # just for pretend

def handle_events(clock):
    monkeys = []
    for sprite in sprites:
        if isinstance(sprite, Monkey):
            monkeys.append(sprite)

    for event in pygame.event.get():
        if event.type == c.QUIT:
            return False
        elif event.type == c.MOUSEBUTTONDOWN:
            for monkey in monkeys:
                monkey.attempt_punch(event.pos)

    opponentScore = get_opponent_score()
    difference = opponentScore - score
    if difference > 0:
        multiplier = 1.0 + difference/10.0
    else:
        multiplier = 1.0
    for monkey in monkeys:
        monkey.adjust_speed(multiplier)

    clock.tick(60) # aim for 60 frames per second
    for sprite in sprites:
        sprite.update()

    return True

def draw_to_display(displayImg):
    displayImg.fill(black)
    for sprite in sprites:
        displayImg.blit(sprite.image, sprite.rect)
    pygame.display.flip()

def main():
    clock, displayImg = init()

    keepGoing = True

    while keepGoing:
        keepGoing = handle_events(clock)
        draw_to_display(displayImg)

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = client
import sys
import time
import network
from twisted.spread import pb
from twisted.internet.selectreactor import SelectReactor
from twisted.internet.main import installReactor
from twisted.cred import credentials
from events import *
from example import (EventManager,
                     Game,
                     Player,
                     KeyboardController,
                     CPUSpinnerController,
                     PygameView)

serverHost, serverPort = 'localhost', 8000
avatarID = None

#------------------------------------------------------------------------------
class NetworkServerView(pb.Root):
    """We SEND events to the server through this object"""
    STATE_PREPARING = 0
    STATE_CONNECTING = 1
    STATE_CONNECTED = 2
    STATE_DISCONNECTING = 3
    STATE_DISCONNECTED = 4

    #----------------------------------------------------------------------
    def __init__(self, evManager, sharedObjectRegistry):
        self.evManager = evManager
        self.evManager.RegisterListener( self )

        self.pbClientFactory = pb.PBClientFactory()
        self.state = NetworkServerView.STATE_PREPARING
        self.reactor = None
        self.server = None

        self.sharedObjs = sharedObjectRegistry

    #----------------------------------------------------------------------
    def AttemptConnection(self):
        print "attempting a connection to", serverHost, serverPort
        self.state = NetworkServerView.STATE_CONNECTING
        if self.reactor:
            self.reactor.stop()
            self.PumpReactor()
        else:
            self.reactor = SelectReactor()
            installReactor(self.reactor)
        connection = self.reactor.connectTCP(serverHost, serverPort,
                                             self.pbClientFactory)
        # TODO: make this anonymous login()
        #deferred = self.pbClientFactory.login(credentials.Anonymous())
        userCred = credentials.UsernamePassword(avatarID, 'pass1')
        controller = NetworkServerController( self.evManager )
        deferred = self.pbClientFactory.login(userCred, client=controller)
        deferred.addCallback(self.Connected)
        deferred.addErrback(self.ConnectFailed)
        self.reactor.startRunning()

    #----------------------------------------------------------------------
    def Disconnect(self):
        print "disconnecting"
        if not self.reactor:
            return
        print 'stopping the reactor'
        self.reactor.stop()
        self.PumpReactor()
        self.state = NetworkServerView.STATE_DISCONNECTING

    #----------------------------------------------------------------------
    def Connected(self, server):
        print "CONNECTED"
        self.server = server
        self.state = NetworkServerView.STATE_CONNECTED
        ev = ServerConnectEvent( server )
        self.evManager.Post( ev )

    #----------------------------------------------------------------------
    def ConnectFailed(self, server):
        print "CONNECTION FAILED"
        print server
        print 'quitting'
        self.evManager.Post( QuitEvent() )
        #self.state = NetworkServerView.STATE_PREPARING
        self.state = NetworkServerView.STATE_DISCONNECTED

    #----------------------------------------------------------------------
    def PumpReactor(self):
        self.reactor.runUntilCurrent()
        self.reactor.doIteration(0)

    #----------------------------------------------------------------------
    def Notify(self, event):
        NSV = NetworkServerView
        if isinstance( event, TickEvent ):
            if self.state == NSV.STATE_PREPARING:
                self.AttemptConnection()
            elif self.state in [NSV.STATE_CONNECTED,
                                NSV.STATE_DISCONNECTING,
                                NSV.STATE_CONNECTING]:
                self.PumpReactor()
            return

        if isinstance( event, QuitEvent ):
            self.Disconnect()
            return

        ev = event
        if not isinstance( event, pb.Copyable ):
            evName = event.__class__.__name__
            copyableClsName = "Copyable"+evName
            if not hasattr( network, copyableClsName ):
                return
            copyableClass = getattr( network, copyableClsName )
            #NOTE, never even construct an instance of an event that
            # is serverToClient, as a side effect is often adding a
            # key to the registry with the local id().
            if copyableClass not in network.clientToServerEvents:
                return
            #print 'creating instance of copyable class', copyableClsName
            ev = copyableClass( event, self.sharedObjs )

        if ev.__class__ not in network.clientToServerEvents:
            #print "CLIENT NOT SENDING: " +str(ev)
            return

        if self.server:
            print " ====   Client sending", str(ev)
            remoteCall = self.server.callRemote("EventOverNetwork", ev)
        else:
            print " =--= Cannot send while disconnected:", str(ev)


#------------------------------------------------------------------------------
class NetworkServerController(pb.Referenceable):
    """We RECEIVE events from the server through this object"""
    def __init__(self, evManager):
        self.evManager = evManager
        self.evManager.RegisterListener( self )

    #----------------------------------------------------------------------
    def remote_ServerEvent(self, event):
        print " ====  GOT AN EVENT FROM SERVER:", str(event)
        self.evManager.Post( event )
        return 1

    #----------------------------------------------------------------------
    def Notify(self, event):
        pass
        #if isinstance( event, ServerConnectEvent ):
            ##tell the server that we're listening to it and
            ##it can access this object
            #defrd = event.server.callRemote("ClientConnect", self)
            #defrd.addErrback(self.ServerErrorHandler)

    #----------------------------------------------------------------------
    def ServerErrorHandler(self, *args):
        print '\n **** ERROR REPORT **** '
        print 'Server threw us an error.  Args:', args
        ev = network.ServerErrorEvent()
        self.evManager.Post(ev)
        print ' ^*** ERROR REPORT ***^ \n'


#------------------------------------------------------------------------------
class PhonyEventManager(EventManager):
    """this object is responsible for coordinating most communication
    between the Model, View, and Controller."""
    #----------------------------------------------------------------------
    def Post( self, event ):
        pass

#------------------------------------------------------------------------------
class PhonyModel:
    '''This isn't the authouritative model.  That one exists on the
    server.  This is a model to store local state and to interact with
    the local EventManager.
    '''

    #----------------------------------------------------------------------
    def __init__(self, evManager, sharedObjectRegistry):
        self.sharedObjs = sharedObjectRegistry
        self.game = None
        self.server = None
        self.phonyEvManager = PhonyEventManager()
        self.realEvManager = evManager
        self.neededObjects = []
        self.waitingObjectStack = []

        self.realEvManager.RegisterListener( self )

    #----------------------------------------------------------------------
    def GameSyncReturned(self, response):
        gameID, gameDict = response
        print "GameSyncReturned : ", gameID
        self.sharedObjs[gameID] = self.game
        # StateReturned returns a deferred, pass it on to keep the
        # chain going.
        return self.StateReturned( response )

    #----------------------------------------------------------------------
    def StateReturned(self, response):
        """this is a callback that is called in response to
        invoking GetObjectState on the server"""

        #print "looking for ", response
        objID, objDict = response
        if objID == 0:
            print "GOT ZERO -- TODO: better error handler here"
            return None
        obj = self.sharedObjs[objID]

        success, neededObjIDs = obj.setCopyableState(objDict, self.sharedObjs)
        if success:
            #we successfully set the state and no further objects
            #are needed to complete the current object
            if objID in self.neededObjects:
                self.neededObjects.remove(objID)

        else:
            #to complete the current object, we need to grab the
            #state from some more objects on the server.  The IDs
            #for those needed objects were passed back 
            #in neededObjIDs
            for neededObjID in neededObjIDs:
                if neededObjID not in self.neededObjects:
                    self.neededObjects.append(neededObjID)
            print "failed.  still need ", self.neededObjects

        self.waitingObjectStack.append( (obj, objDict) )

        retval = self.GetAllNeededObjects()
        if retval:
            # retval is a Deferred - returning it causes a chain
            # to be formed.  The original deferred must wait for
            # this new one to return before it calls its next
            # callback
            return retval

    #----------------------------------------------------------------------
    def GetAllNeededObjects(self):
        if len(self.neededObjects) == 0:
            # this is the recursion-ending condition.  If there are
            # no more objects needed to be grabbed from the server
            # then we can try to setCopyableState on them again and
            # we should now have all the needed objects, ensuring
            # that setCopyableState succeeds
            return self.ConsumeWaitingObjectStack()

        # still in the recursion step.  Try to get the object state for
        # the objectID on the top of the stack.  Note that the 
        # recursion is done via a deferred, which may be confusing
        nextID = self.neededObjects[-1]
        print "next one to grab: ", nextID
        remoteResponse = self.server.callRemote("GetObjectState",nextID)
        remoteResponse.addCallback(self.StateReturned)
        remoteResponse.addErrback(self.ServerErrorHandler, 'allNeededObjs')
        return remoteResponse

    #----------------------------------------------------------------------
    def ConsumeWaitingObjectStack(self):
        # All the needed objects should be present now.  Just the
        # matter of setting the state on the waiting objects remains.
        while self.waitingObjectStack:
            obj, objDict = self.waitingObjectStack.pop()
            success, neededObjIDs =\
                                 obj.setCopyableState(objDict, self.sharedObjs)
            if not success:
                print "WEIRD!!!!!!!!!!!!!!!!!!"

    #----------------------------------------------------------------------
    def Notify(self, event):
        if isinstance( event, ServerConnectEvent ):
            self.server = event.server
            #when we connect to the server, we should get the
            #entire game state.  this also applies to RE-connecting
            if not self.game:
                self.game = Game( self.phonyEvManager )
                gameID = id(self.game)
                self.sharedObjs[gameID] = self.game
            remoteResponse = self.server.callRemote("GetGameSync")
            remoteResponse.addCallback(self.GameSyncReturned)
            remoteResponse.addCallback(self.GameSyncCallback, gameID)
            remoteResponse.addErrback(self.ServerErrorHandler, 'ServerConnect')


        elif isinstance( event, network.CopyableGameStartedEvent ):
            gameID = event.gameID
            if not self.game:
                self.game = Game( self.phonyEvManager )
            self.sharedObjs[gameID] = self.game
            ev = GameStartedEvent( self.game )
            self.realEvManager.Post( ev )

        elif isinstance( event, network.ServerErrorEvent ):
            from pprint import pprint
            print 'Client state at the time of server error:'
            pprint(self.sharedObjs)

        if isinstance( event, network.CopyableMapBuiltEvent ):
            mapID = event.mapID
            if not self.sharedObjs.has_key(mapID):
                self.sharedObjs[mapID] = self.game.map
            remoteResponse = self.server.callRemote("GetObjectState", mapID)
            remoteResponse.addCallback(self.StateReturned)
            remoteResponse.addCallback(self.MapBuiltCallback, mapID)
            remoteResponse.addErrback(self.ServerErrorHandler, 'MapBuilt')

        if isinstance( event, network.CopyablePlayerJoinEvent ):
            playerID = event.playerID
            if not self.sharedObjs.has_key(playerID):
                player = Player( self.phonyEvManager )
                self.sharedObjs[playerID] = player
            remoteResponse = self.server.callRemote("GetObjectState", playerID)
            remoteResponse.addCallback(self.StateReturned)
            remoteResponse.addCallback(self.PlayerJoinCallback, playerID)
            remoteResponse.addErrback(self.ServerErrorHandler, 'PlayerJoin')

        if isinstance( event, network.CopyableCharactorPlaceEvent ):
            charactorID = event.charactorID
            if not self.sharedObjs.has_key(charactorID):
                charactor = self.game.players[0].charactors[0]
                self.sharedObjs[charactorID] = charactor
            remoteResponse = self.server.callRemote("GetObjectState", charactorID)
            remoteResponse.addCallback(self.StateReturned)
            remoteResponse.addCallback(self.CharactorPlaceCallback, charactorID)
            remoteResponse.addErrback(self.ServerErrorHandler, 'CharPlace')

        if isinstance( event, network.CopyableCharactorMoveEvent ):
            charactorID = event.charactorID
            if not self.sharedObjs.has_key(charactorID):
                charactor = self.game.players[0].charactors[0]
                self.sharedObjs[charactorID] = charactor
            remoteResponse = self.server.callRemote("GetObjectState", charactorID)
            remoteResponse.addCallback(self.StateReturned)
            remoteResponse.addCallback(self.CharactorMoveCallback, charactorID)
            remoteResponse.addErrback(self.ServerErrorHandler, 'CharMove')

    #----------------------------------------------------------------------
    def CharactorPlaceCallback(self, deferredResult, charactorID):
        charactor = self.sharedObjs[charactorID]
        ev = CharactorPlaceEvent( charactor )
        self.realEvManager.Post( ev )
    #----------------------------------------------------------------------
    def MapBuiltCallback(self, deferredResult, mapID):
        gameMap = self.sharedObjs[mapID]
        ev = MapBuiltEvent( gameMap )
        self.realEvManager.Post( ev )
    #----------------------------------------------------------------------
    def CharactorMoveCallback(self, deferredResult, charactorID):
        charactor = self.sharedObjs[charactorID]
        ev = CharactorMoveEvent( charactor )
        self.realEvManager.Post( ev )
    #----------------------------------------------------------------------
    def GameSyncCallback(self, deferredResult, gameID):
        game = self.sharedObjs[gameID]
        ev = GameSyncEvent( game )
        self.realEvManager.Post( ev )
    #----------------------------------------------------------------------
    def PlayerJoinCallback(self, deferredResult, playerID):
        player = self.sharedObjs[playerID]
        self.game.AddPlayer( player )
        ev = PlayerJoinEvent( player )
        self.realEvManager.Post( ev )
    #----------------------------------------------------------------------
    def ServerErrorHandler(self, failure, *args):
        print '\n **** ERROR REPORT **** '
        print 'Server threw PhonyModel an error.  failure:', failure
        print 'failure traceback:', failure.getTraceback()
        print 'Server threw PhonyModel an error.  Args:', args
        ev = network.ServerErrorEvent()
        self.realEvManager.Post(ev)
        print ' ^*** ERROR REPORT ***^ \n'


#class DebugDict(dict):
    #def __setitem__(self, *args):
        #print ''
        #print '        set item', args
        #return dict.__setitem__(self, *args)

#------------------------------------------------------------------------------
def main():
    global avatarID
    if len(sys.argv) > 1:
        avatarID = sys.argv[1]
    else:
        print 'You should provide a username on the command line'
        print 'Defaulting to username "user1"'
        time.sleep(1)
        avatarID = 'user1'
        
    evManager = EventManager()
    sharedObjectRegistry = {}
    keybd = KeyboardController( evManager, playerName=avatarID )
    spinner = CPUSpinnerController( evManager )
    pygameView = PygameView( evManager )

    phonyModel = PhonyModel( evManager, sharedObjectRegistry  )

    serverView = NetworkServerView( evManager, sharedObjectRegistry )
    
    try:
        spinner.Run()
    except Exception, ex:
        print 'got exception (%s)' % ex, 'killing reactor'
        import logging
        logging.basicConfig()
        logging.exception(ex)
        serverView.Disconnect()


if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = events
#SECURITY NOTE: anything in here can be created simply by sending the 
# class name over the network.  This is a potential vulnerability
# I wouldn't suggest letting any of these classes DO anything, especially
# things like file system access, or allocating huge amounts of memory

class Event:
	"""this is a superclass for any events that might be generated by an
	object and sent to the EventManager"""
	def __init__(self):
		self.name = "Generic Event"
	def __str__(self):
		return '<%s %s>' % (self.__class__.__name__,
		                    id(self))
	    

class TickEvent(Event):
	def __init__(self):
		self.name = "CPU Tick Event"

class SecondEvent(Event):
	def __init__(self):
		self.name = "Clock One Second Event"

class QuitEvent(Event):
	def __init__(self):
		self.name = "Program Quit Event"

class FatalEvent(Event):
	def __init__(self, *args):
		self.name = "Fatal Error Event"
		self.args = args

class MapBuiltEvent(Event):
	def __init__(self, map):
		self.name = "Map Finished Building Event"
		self.map = map

class GameStartRequest(Event):
	def __init__(self):
		self.name = "Game Start Request"

class GameStartedEvent(Event):
	def __init__(self, game):
		self.name = "Game Started Event"
		self.game = game

class CharactorMoveRequest(Event):
	def __init__(self, player, charactor, direction):
		self.name = "Charactor Move Request"
		self.player = player
		self.charactor = charactor
		self.direction = direction

class CharactorMoveEvent(Event):
	def __init__(self, charactor):
		self.name = "Charactor Move Event"
		self.charactor = charactor

class CharactorPlaceEvent(Event):
	"""this event occurs when a Charactor is *placed* in a sector,
	ie it doesn't move there from an adjacent sector."""
	def __init__(self, charactor):
		self.name = "Charactor Placement Event"
		self.charactor = charactor

class ServerConnectEvent(Event):
	"""the client generates this when it detects that it has successfully
	connected to the server"""
	def __init__(self, serverReference):
		self.name = "Network Server Connection Event"
		self.server = serverReference

class ClientConnectEvent(Event):
	"""this event is generated by the Server whenever a client connects
	to it"""
	def __init__(self, client, avatarID):
		self.name = "Network Client Connection Event"
		self.client = client
		self.avatarID = avatarID

class ClientDisconnectEvent(Event):
	"""this event is generated by the Server when it finds that a client 
	is no longer connected"""
	def __init__(self, avatarID):
		self.name = "Network Client Disconnection Event"
		self.avatarID = avatarID

class GameSyncEvent(Event):
	"""..."""
	def __init__(self, game):
		self.name = "Game Synched to Authoritative State"
		self.game = game

class PlayerJoinRequest(Event):
	"""..."""
	def __init__(self, playerDict):
		self.name = "Player Joining Game Request"
		self.playerDict = playerDict

class PlayerJoinEvent(Event):
	"""..."""
	def __init__(self, player):
		self.name = "Player Joined Game Event"
		self.player = player

class CharactorPlaceRequest(Event):
	"""..."""
	def __init__(self, player, charactor, sector):
		self.name = "Charactor Placement Request"
		self.player = player
		self.charactor = charactor
		self.sector = sector

########NEW FILE########
__FILENAME__ = ex1
#! /usr/bin/env python
'''
Example
'''


def Debug( msg ):
	print msg

DIRECTION_UP = 0
DIRECTION_DOWN = 1
DIRECTION_LEFT = 2
DIRECTION_RIGHT = 3

class Event:
    """this is a superclass for any events that might be generated by an
    object and sent to the EventManager"""
    def __init__(self):
        self.name = "Generic Event"

class TickEvent(Event):
	def __init__(self):
		self.name = "CPU Tick Event"

class QuitEvent(Event):
	def __init__(self):
		self.name = "Program Quit Event"

class MapBuiltEvent(Event):
	def __init__(self, gameMap):
		self.name = "Map Finished Building Event"
		self.map = gameMap

class GameStartedEvent(Event):
	def __init__(self, game):
		self.name = "Game Started Event"
		self.game = game

class CharactorMoveRequest(Event):
	def __init__(self, direction):
		self.name = "Charactor Move Request"
		self.direction = direction

class CharactorPlaceEvent(Event):
	"""this event occurs when a Charactor is *placed* in a sector,
	ie it doesn't move there from an adjacent sector."""
	def __init__(self, charactor):
		self.name = "Charactor Placement Event"
		self.charactor = charactor

class CharactorMoveEvent(Event):
	def __init__(self, charactor):
		self.name = "Charactor Move Event"
		self.charactor = charactor

#------------------------------------------------------------------------------
class EventManager:
	"""this object is responsible for coordinating most communication
	between the Model, View, and Controller."""
	def __init__(self):
		from weakref import WeakKeyDictionary
		self.listeners = WeakKeyDictionary()
		self.eventQueue= []

	#----------------------------------------------------------------------
	def RegisterListener( self, listener ):
		self.listeners[ listener ] = 1

	#----------------------------------------------------------------------
	def UnregisterListener( self, listener ):
		if listener in self.listeners:
			del self.listeners[ listener ]
		
	#----------------------------------------------------------------------
	def Post( self, event ):
		if not isinstance(event, TickEvent):
			Debug( "     Message: " + event.name )
		for listener in self.listeners:
			#NOTE: If the weakref has died, it will be 
			#automatically removed, so we don't have 
			#to worry about it.
			listener.Notify( event )

#------------------------------------------------------------------------------
class KeyboardController:
	"""KeyboardController takes Pygame events generated by the
	keyboard and uses them to control the model, by sending Requests
	or to control the Pygame display directly, as with the QuitEvent
	"""
	def __init__(self, evManager):
		self.evManager = evManager
		self.evManager.RegisterListener( self )

	#----------------------------------------------------------------------
	def Notify(self, event):
		if isinstance( event, TickEvent ):
			#Handle Input Events
			for event in pygame.event.get():
				ev = None
				if event.type == QUIT:
					ev = QuitEvent()
				elif event.type == KEYDOWN \
				     and event.key == K_ESCAPE:
					ev = QuitEvent()
				elif event.type == KEYDOWN \
				     and event.key == K_UP:
					direction = DIRECTION_UP
					ev = CharactorMoveRequest(direction)
				elif event.type == KEYDOWN \
				     and event.key == K_DOWN:
					direction = DIRECTION_DOWN
					ev = CharactorMoveRequest(direction)
				elif event.type == KEYDOWN \
				     and event.key == K_LEFT:
					direction = DIRECTION_LEFT
					ev = CharactorMoveRequest(direction)
				elif event.type == KEYDOWN \
				     and event.key == K_RIGHT:
					direction = DIRECTION_RIGHT
					ev = CharactorMoveRequest(direction)

				if ev:
					self.evManager.Post( ev )


#------------------------------------------------------------------------------
class CPUSpinnerController:
	"""..."""
	def __init__(self, evManager):
		self.evManager = evManager
		self.evManager.RegisterListener( self )

		self.keepGoing = 1

	#----------------------------------------------------------------------
	def Run(self):
		while self.keepGoing:
			event = TickEvent()
			self.evManager.Post( event )

	#----------------------------------------------------------------------
	def Notify(self, event):
		if isinstance( event, QuitEvent ):
			#this will stop the while loop from running
			self.keepGoing = False


import pygame
from pygame.locals import *
#------------------------------------------------------------------------------
class SectorSprite(pygame.sprite.Sprite):
	def __init__(self, sector, group=None):
		pygame.sprite.Sprite.__init__(self, group)
		self.image = pygame.Surface( (128,128) )
		self.image.fill( (0,255,128) )

		self.sector = sector

#------------------------------------------------------------------------------
class CharactorSprite(pygame.sprite.Sprite):
	def __init__(self, group=None):
		pygame.sprite.Sprite.__init__(self, group)

		charactorSurf = pygame.Surface( (64,64) )
		charactorSurf = charactorSurf.convert_alpha()
		charactorSurf.fill((0,0,0,0)) #make transparent
		pygame.draw.circle( charactorSurf, (255,0,0), (32,32), 32 )
		self.image = charactorSurf
		self.rect  = charactorSurf.get_rect()

		self.moveTo = None

	#----------------------------------------------------------------------
	def update(self):
		if self.moveTo:
			self.rect.center = self.moveTo
			self.moveTo = None

#------------------------------------------------------------------------------
class PygameView:
	def __init__(self, evManager):
		self.evManager = evManager
		self.evManager.RegisterListener( self )

		pygame.init()
		self.window = pygame.display.set_mode( (424,440) )
		pygame.display.set_caption( 'Example Game' )
		self.background = pygame.Surface( self.window.get_size() )
		self.background.fill( (0,0,0) )
		font = pygame.font.Font(None, 30)
		text = """Press SPACE BAR to start"""
		textImg = font.render( text, 1, (255,0,0))
		self.background.blit( textImg, (0,0) )
		self.window.blit( self.background, (0,0) )
		pygame.display.flip()

		self.backSprites = pygame.sprite.RenderUpdates()
		self.frontSprites = pygame.sprite.RenderUpdates()


	#----------------------------------------------------------------------
	def ShowMap(self, gameMap):
		# clear the screen first
		self.background.fill( (0,0,0) )
		self.window.blit( self.background, (0,0) )
		pygame.display.flip()

		# use this squareRect as a cursor and go through the
		# columns and rows and assign the rect 
		# positions of the SectorSprites
		squareRect = pygame.Rect( (-128,10, 128,128 ) )

		column = 0
		for sector in gameMap.sectors:
			if column < 3:
				squareRect = squareRect.move( 138,0 )
			else:
				column = 0
				squareRect = squareRect.move( -(138*2), 138 )
			column += 1
			newSprite = SectorSprite( sector, self.backSprites )
			newSprite.rect = squareRect
			newSprite = None

	#----------------------------------------------------------------------
	def ShowCharactor(self, charactor):
		sector = charactor.sector
		charactorSprite = CharactorSprite( self.frontSprites )
		sectorSprite = self.GetSectorSprite( sector )
		charactorSprite.rect.center = sectorSprite.rect.center

	#----------------------------------------------------------------------
	def MoveCharactor(self, charactor):
		charactorSprite = self.GetCharactorSprite( charactor )

		sector = charactor.sector
		sectorSprite = self.GetSectorSprite( sector )

		charactorSprite.moveTo = sectorSprite.rect.center

	#----------------------------------------------------------------------
	def GetCharactorSprite(self, charactor):
		#there will be only one
		for s in self.frontSprites:
			return s
		return None

	#----------------------------------------------------------------------
	def GetSectorSprite(self, sector):
		for s in self.backSprites:
			if hasattr(s, "sector") and s.sector == sector:
				return s


	#----------------------------------------------------------------------
	def Notify(self, event):
		if isinstance( event, TickEvent ):
			#Draw Everything
			self.backSprites.clear( self.window, self.background )
			self.frontSprites.clear( self.window, self.background )

			self.backSprites.update()
			self.frontSprites.update()

			dirtyRects1 = self.backSprites.draw( self.window )
			dirtyRects2 = self.frontSprites.draw( self.window )
			
			dirtyRects = dirtyRects1 + dirtyRects2
			pygame.display.update( dirtyRects )


		elif isinstance( event, MapBuiltEvent ):
			gameMap = event.map
			self.ShowMap( gameMap )

		elif isinstance( event, CharactorPlaceEvent ):
			self.ShowCharactor( event.charactor )

		elif isinstance( event, CharactorMoveEvent ):
			self.MoveCharactor( event.charactor )


#------------------------------------------------------------------------------
class Game:
	"""..."""

	STATE_PREPARING = 'preparing'
	STATE_RUNNING = 'running'
	STATE_PAUSED = 'paused'

	#----------------------------------------------------------------------
	def __init__(self, evManager):
		self.evManager = evManager
		self.evManager.RegisterListener( self )

		self.state = Game.STATE_PREPARING
		
		self.players = [ Player(evManager) ]
		self.map = Map( evManager )

	#----------------------------------------------------------------------
	def Start(self):
		self.map.Build()
		self.state = Game.STATE_RUNNING
		ev = GameStartedEvent( self )
		self.evManager.Post( ev )

	#----------------------------------------------------------------------
	def Notify(self, event):
		if isinstance( event, TickEvent ):
			if self.state == Game.STATE_PREPARING:
				self.Start()

#------------------------------------------------------------------------------
class Player(object):
	"""..."""
	def __init__(self, evManager):
		self.evManager = evManager
		self.game = None
		self.name = ""
		self.evManager.RegisterListener( self )

		self.charactors = [ Charactor(evManager) ]

	#----------------------------------------------------------------------
	def __str__(self):
		return '<Player %s %s>' % (self.name, id(self))


	#----------------------------------------------------------------------
	def Notify(self, event):
		pass

#------------------------------------------------------------------------------
class Charactor:
	"""..."""

	STATE_INACTIVE = 0
	STATE_ACTIVE = 1

	def __init__(self, evManager):
		self.evManager = evManager
		self.evManager.RegisterListener( self )

		self.sector = None
		self.state = Charactor.STATE_INACTIVE

	#----------------------------------------------------------------------
	def __str__(self):
		return '<Charactor %s>' % id(self)

	#----------------------------------------------------------------------
	def Move(self, direction):
		if self.state == Charactor.STATE_INACTIVE:
			return

		if self.sector.MovePossible( direction ):
			newSector = self.sector.neighbors[direction]
			self.sector = newSector
			ev = CharactorMoveEvent( self )
			self.evManager.Post( ev )

	#----------------------------------------------------------------------
	def Place(self, sector):
		self.sector = sector
		self.state = Charactor.STATE_ACTIVE

		ev = CharactorPlaceEvent( self )
		self.evManager.Post( ev )

	#----------------------------------------------------------------------
	def Notify(self, event):
		if isinstance( event, GameStartedEvent ):
			gameMap = event.game.map
			self.Place( gameMap.sectors[gameMap.startSectorIndex] )

		elif isinstance( event, CharactorMoveRequest ):
			self.Move( event.direction )

#------------------------------------------------------------------------------
class Map:
	"""..."""

	STATE_PREPARING = 0
	STATE_BUILT = 1


	#----------------------------------------------------------------------
	def __init__(self, evManager):
		self.evManager = evManager
		#self.evManager.RegisterListener( self )

		self.state = Map.STATE_PREPARING

		self.sectors = []
		self.startSectorIndex = 0

	#----------------------------------------------------------------------
	def Build(self):
		for i in range(9):
			self.sectors.append( Sector(self.evManager) )

		self.sectors[3].neighbors[DIRECTION_UP] = self.sectors[0]
		self.sectors[4].neighbors[DIRECTION_UP] = self.sectors[1]
		self.sectors[5].neighbors[DIRECTION_UP] = self.sectors[2]
		self.sectors[6].neighbors[DIRECTION_UP] = self.sectors[3]
		self.sectors[7].neighbors[DIRECTION_UP] = self.sectors[4]
		self.sectors[8].neighbors[DIRECTION_UP] = self.sectors[5]

		self.sectors[0].neighbors[DIRECTION_DOWN] = self.sectors[3]
		self.sectors[1].neighbors[DIRECTION_DOWN] = self.sectors[4]
		self.sectors[2].neighbors[DIRECTION_DOWN] = self.sectors[5]
		self.sectors[3].neighbors[DIRECTION_DOWN] = self.sectors[6]
		self.sectors[4].neighbors[DIRECTION_DOWN] = self.sectors[7]
		self.sectors[5].neighbors[DIRECTION_DOWN] = self.sectors[8]

		self.sectors[1].neighbors[DIRECTION_LEFT] = self.sectors[0]
		self.sectors[2].neighbors[DIRECTION_LEFT] = self.sectors[1]
		self.sectors[4].neighbors[DIRECTION_LEFT] = self.sectors[3]
		self.sectors[5].neighbors[DIRECTION_LEFT] = self.sectors[4]
		self.sectors[7].neighbors[DIRECTION_LEFT] = self.sectors[6]
		self.sectors[8].neighbors[DIRECTION_LEFT] = self.sectors[7]

		self.sectors[0].neighbors[DIRECTION_RIGHT] = self.sectors[1]
		self.sectors[1].neighbors[DIRECTION_RIGHT] = self.sectors[2]
		self.sectors[3].neighbors[DIRECTION_RIGHT] = self.sectors[4]
		self.sectors[4].neighbors[DIRECTION_RIGHT] = self.sectors[5]
		self.sectors[6].neighbors[DIRECTION_RIGHT] = self.sectors[7]
		self.sectors[7].neighbors[DIRECTION_RIGHT] = self.sectors[8]

		self.state = Map.STATE_BUILT

		ev = MapBuiltEvent( self )
		self.evManager.Post( ev )

#------------------------------------------------------------------------------
class Sector:
	"""..."""
	def __init__(self, evManager):
		self.evManager = evManager
		#self.evManager.RegisterListener( self )

		self.neighbors = range(4)

		self.neighbors[DIRECTION_UP] = None
		self.neighbors[DIRECTION_DOWN] = None
		self.neighbors[DIRECTION_LEFT] = None
		self.neighbors[DIRECTION_RIGHT] = None

	#----------------------------------------------------------------------
	def MovePossible(self, direction):
		if self.neighbors[direction]:
			return 1


#------------------------------------------------------------------------------
def main():
	"""..."""
	evManager = EventManager()

	keybd = KeyboardController( evManager )
	spinner = CPUSpinnerController( evManager )
	pygameView = PygameView( evManager )
	game = Game( evManager )
	
	spinner.Run()

if __name__ == "__main__":
	main()

########NEW FILE########
__FILENAME__ = example
#! /usr/bin/env python
'''
Example
'''


def Debug( msg ):
	print msg

DIRECTION_UP = 0
DIRECTION_DOWN = 1
DIRECTION_LEFT = 2
DIRECTION_RIGHT = 3

class Event:
    """this is a superclass for any events that might be generated by an
    object and sent to the EventManager"""
    def __init__(self):
        self.name = "Generic Event"

class TickEvent(Event):
	def __init__(self):
		self.name = "CPU Tick Event"

class QuitEvent(Event):
	def __init__(self):
		self.name = "Program Quit Event"

class MapBuiltEvent(Event):
	def __init__(self, gameMap):
		self.name = "Map Finished Building Event"
		self.map = gameMap

class GameStartedEvent(Event):
	def __init__(self, game):
		self.name = "Game Started Event"
		self.game = game

class CharactorMoveRequest(Event):
	def __init__(self, direction):
		self.name = "Charactor Move Request"
		self.direction = direction

class CharactorPlaceEvent(Event):
	"""this event occurs when a Charactor is *placed* in a sector,
	ie it doesn't move there from an adjacent sector."""
	def __init__(self, charactor):
		self.name = "Charactor Placement Event"
		self.charactor = charactor

class CharactorMoveEvent(Event):
	def __init__(self, charactor):
		self.name = "Charactor Move Event"
		self.charactor = charactor

#------------------------------------------------------------------------------
class EventManager:
	"""this object is responsible for coordinating most communication
	between the Model, View, and Controller."""
	def __init__(self):
		from weakref import WeakKeyDictionary
		self.listeners = WeakKeyDictionary()
		self.eventQueue= []

	#----------------------------------------------------------------------
	def RegisterListener( self, listener ):
		self.listeners[ listener ] = 1

	#----------------------------------------------------------------------
	def UnregisterListener( self, listener ):
		if listener in self.listeners:
			del self.listeners[ listener ]
		
	#----------------------------------------------------------------------
	def Post( self, event ):
		if not isinstance(event, TickEvent):
			Debug( "     Message: " + event.name )
		for listener in self.listeners:
			#NOTE: If the weakref has died, it will be 
			#automatically removed, so we don't have 
			#to worry about it.
			listener.Notify( event )

#------------------------------------------------------------------------------
class KeyboardController:
	"""KeyboardController takes Pygame events generated by the
	keyboard and uses them to control the model, by sending Requests
	or to control the Pygame display directly, as with the QuitEvent
	"""
	def __init__(self, evManager):
		self.evManager = evManager
		self.evManager.RegisterListener( self )

	#----------------------------------------------------------------------
	def Notify(self, event):
		if isinstance( event, TickEvent ):
			#Handle Input Events
			for event in pygame.event.get():
				ev = None
				if event.type == QUIT:
					ev = QuitEvent()
				elif event.type == KEYDOWN \
				     and event.key == K_ESCAPE:
					ev = QuitEvent()
				elif event.type == KEYDOWN \
				     and event.key == K_UP:
					direction = DIRECTION_UP
					ev = CharactorMoveRequest(direction)
				elif event.type == KEYDOWN \
				     and event.key == K_DOWN:
					direction = DIRECTION_DOWN
					ev = CharactorMoveRequest(direction)
				elif event.type == KEYDOWN \
				     and event.key == K_LEFT:
					direction = DIRECTION_LEFT
					ev = CharactorMoveRequest(direction)
				elif event.type == KEYDOWN \
				     and event.key == K_RIGHT:
					direction = DIRECTION_RIGHT
					ev = CharactorMoveRequest(direction)

				if ev:
					self.evManager.Post( ev )


#------------------------------------------------------------------------------
class CPUSpinnerController:
	"""..."""
	def __init__(self, evManager):
		self.evManager = evManager
		self.evManager.RegisterListener( self )

		self.keepGoing = 1

	#----------------------------------------------------------------------
	def Run(self):
		while self.keepGoing:
			event = TickEvent()
			self.evManager.Post( event )

	#----------------------------------------------------------------------
	def Notify(self, event):
		if isinstance( event, QuitEvent ):
			#this will stop the while loop from running
			self.keepGoing = False


import pygame
from pygame.locals import *
#------------------------------------------------------------------------------
class SectorSprite(pygame.sprite.Sprite):
	def __init__(self, sector, group=None):
		pygame.sprite.Sprite.__init__(self, group)
		self.image = pygame.Surface( (128,128) )
		self.image.fill( (0,255,128) )

		self.sector = sector

#------------------------------------------------------------------------------
class CharactorSprite(pygame.sprite.Sprite):
	def __init__(self, group=None):
		pygame.sprite.Sprite.__init__(self, group)

		charactorSurf = pygame.Surface( (64,64) )
		charactorSurf = charactorSurf.convert_alpha()
		charactorSurf.fill((0,0,0,0)) #make transparent
		pygame.draw.circle( charactorSurf, (255,0,0), (32,32), 32 )
		self.image = charactorSurf
		self.rect  = charactorSurf.get_rect()

		self.moveTo = None

	#----------------------------------------------------------------------
	def update(self):
		if self.moveTo:
			self.rect.center = self.moveTo
			self.moveTo = None

#------------------------------------------------------------------------------
class PygameView:
	def __init__(self, evManager):
		self.evManager = evManager
		self.evManager.RegisterListener( self )

		pygame.init()
		self.window = pygame.display.set_mode( (424,440) )
		pygame.display.set_caption( 'Example Game' )
		self.background = pygame.Surface( self.window.get_size() )
		self.background.fill( (0,0,0) )
		font = pygame.font.Font(None, 30)
		text = """Press SPACE BAR to start"""
		textImg = font.render( text, 1, (255,0,0))
		self.background.blit( textImg, (0,0) )
		self.window.blit( self.background, (0,0) )
		pygame.display.flip()

		self.backSprites = pygame.sprite.RenderUpdates()
		self.frontSprites = pygame.sprite.RenderUpdates()


	#----------------------------------------------------------------------
	def ShowMap(self, gameMap):
		# clear the screen first
		self.background.fill( (0,0,0) )
		self.window.blit( self.background, (0,0) )
		pygame.display.flip()

		# use this squareRect as a cursor and go through the
		# columns and rows and assign the rect 
		# positions of the SectorSprites
		squareRect = pygame.Rect( (-128,10, 128,128 ) )

		column = 0
		for sector in gameMap.sectors:
			if column < 3:
				squareRect = squareRect.move( 138,0 )
			else:
				column = 0
				squareRect = squareRect.move( -(138*2), 138 )
			column += 1
			newSprite = SectorSprite( sector, self.backSprites )
			newSprite.rect = squareRect
			newSprite = None

	#----------------------------------------------------------------------
	def ShowCharactor(self, charactor):
		sector = charactor.sector
		charactorSprite = CharactorSprite( self.frontSprites )
		sectorSprite = self.GetSectorSprite( sector )
		charactorSprite.rect.center = sectorSprite.rect.center

	#----------------------------------------------------------------------
	def MoveCharactor(self, charactor):
		charactorSprite = self.GetCharactorSprite( charactor )

		sector = charactor.sector
		sectorSprite = self.GetSectorSprite( sector )

		charactorSprite.moveTo = sectorSprite.rect.center

	#----------------------------------------------------------------------
	def GetCharactorSprite(self, charactor):
		#there will be only one
		for s in self.frontSprites:
			return s
		return None

	#----------------------------------------------------------------------
	def GetSectorSprite(self, sector):
		for s in self.backSprites:
			if hasattr(s, "sector") and s.sector == sector:
				return s


	#----------------------------------------------------------------------
	def Notify(self, event):
		if isinstance( event, TickEvent ):
			#Draw Everything
			self.backSprites.clear( self.window, self.background )
			self.frontSprites.clear( self.window, self.background )

			self.backSprites.update()
			self.frontSprites.update()

			dirtyRects1 = self.backSprites.draw( self.window )
			dirtyRects2 = self.frontSprites.draw( self.window )
			
			dirtyRects = dirtyRects1 + dirtyRects2
			pygame.display.update( dirtyRects )


		elif isinstance( event, MapBuiltEvent ):
			gameMap = event.map
			self.ShowMap( gameMap )

		elif isinstance( event, CharactorPlaceEvent ):
			self.ShowCharactor( event.charactor )

		elif isinstance( event, CharactorMoveEvent ):
			self.MoveCharactor( event.charactor )


#------------------------------------------------------------------------------
class Game:
	"""..."""

	STATE_PREPARING = 'preparing'
	STATE_RUNNING = 'running'
	STATE_PAUSED = 'paused'

	#----------------------------------------------------------------------
	def __init__(self, evManager):
		self.evManager = evManager
		self.evManager.RegisterListener( self )

		self.state = Game.STATE_PREPARING
		
		self.players = [ Player(evManager) ]
		self.map = Map( evManager )

	#----------------------------------------------------------------------
	def Start(self):
		self.map.Build()
		self.state = Game.STATE_RUNNING
		ev = GameStartedEvent( self )
		self.evManager.Post( ev )

	#----------------------------------------------------------------------
	def Notify(self, event):
		if isinstance( event, TickEvent ):
			if self.state == Game.STATE_PREPARING:
				self.Start()

#------------------------------------------------------------------------------
class Player(object):
	"""..."""
	def __init__(self, evManager):
		self.evManager = evManager
		self.game = None
		self.name = ""
		self.evManager.RegisterListener( self )

		self.charactors = [ Charactor(evManager) ]

	#----------------------------------------------------------------------
	def __str__(self):
		return '<Player %s %s>' % (self.name, id(self))


	#----------------------------------------------------------------------
	def Notify(self, event):
		pass

#------------------------------------------------------------------------------
class Charactor:
	"""..."""

	STATE_INACTIVE = 0
	STATE_ACTIVE = 1

	def __init__(self, evManager):
		self.evManager = evManager
		self.evManager.RegisterListener( self )

		self.sector = None
		self.state = Charactor.STATE_INACTIVE

	#----------------------------------------------------------------------
	def __str__(self):
		return '<Charactor %s>' % id(self)

	#----------------------------------------------------------------------
	def Move(self, direction):
		if self.state == Charactor.STATE_INACTIVE:
			return

		if self.sector.MovePossible( direction ):
			newSector = self.sector.neighbors[direction]
			self.sector = newSector
			ev = CharactorMoveEvent( self )
			self.evManager.Post( ev )

	#----------------------------------------------------------------------
	def Place(self, sector):
		self.sector = sector
		self.state = Charactor.STATE_ACTIVE

		ev = CharactorPlaceEvent( self )
		self.evManager.Post( ev )

	#----------------------------------------------------------------------
	def Notify(self, event):
		if isinstance( event, GameStartedEvent ):
			gameMap = event.game.map
			self.Place( gameMap.sectors[gameMap.startSectorIndex] )

		elif isinstance( event, CharactorMoveRequest ):
			self.Move( event.direction )

#------------------------------------------------------------------------------
class Map:
	"""..."""

	STATE_PREPARING = 0
	STATE_BUILT = 1


	#----------------------------------------------------------------------
	def __init__(self, evManager):
		self.evManager = evManager
		#self.evManager.RegisterListener( self )

		self.state = Map.STATE_PREPARING

		self.sectors = []
		self.startSectorIndex = 0

	#----------------------------------------------------------------------
	def Build(self):
		for i in range(9):
			self.sectors.append( Sector(self.evManager) )

		self.sectors[3].neighbors[DIRECTION_UP] = self.sectors[0]
		self.sectors[4].neighbors[DIRECTION_UP] = self.sectors[1]
		self.sectors[5].neighbors[DIRECTION_UP] = self.sectors[2]
		self.sectors[6].neighbors[DIRECTION_UP] = self.sectors[3]
		self.sectors[7].neighbors[DIRECTION_UP] = self.sectors[4]
		self.sectors[8].neighbors[DIRECTION_UP] = self.sectors[5]

		self.sectors[0].neighbors[DIRECTION_DOWN] = self.sectors[3]
		self.sectors[1].neighbors[DIRECTION_DOWN] = self.sectors[4]
		self.sectors[2].neighbors[DIRECTION_DOWN] = self.sectors[5]
		self.sectors[3].neighbors[DIRECTION_DOWN] = self.sectors[6]
		self.sectors[4].neighbors[DIRECTION_DOWN] = self.sectors[7]
		self.sectors[5].neighbors[DIRECTION_DOWN] = self.sectors[8]

		self.sectors[1].neighbors[DIRECTION_LEFT] = self.sectors[0]
		self.sectors[2].neighbors[DIRECTION_LEFT] = self.sectors[1]
		self.sectors[4].neighbors[DIRECTION_LEFT] = self.sectors[3]
		self.sectors[5].neighbors[DIRECTION_LEFT] = self.sectors[4]
		self.sectors[7].neighbors[DIRECTION_LEFT] = self.sectors[6]
		self.sectors[8].neighbors[DIRECTION_LEFT] = self.sectors[7]

		self.sectors[0].neighbors[DIRECTION_RIGHT] = self.sectors[1]
		self.sectors[1].neighbors[DIRECTION_RIGHT] = self.sectors[2]
		self.sectors[3].neighbors[DIRECTION_RIGHT] = self.sectors[4]
		self.sectors[4].neighbors[DIRECTION_RIGHT] = self.sectors[5]
		self.sectors[6].neighbors[DIRECTION_RIGHT] = self.sectors[7]
		self.sectors[7].neighbors[DIRECTION_RIGHT] = self.sectors[8]

		self.state = Map.STATE_BUILT

		ev = MapBuiltEvent( self )
		self.evManager.Post( ev )

#------------------------------------------------------------------------------
class Sector:
	"""..."""
	def __init__(self, evManager):
		self.evManager = evManager
		#self.evManager.RegisterListener( self )

		self.neighbors = range(4)

		self.neighbors[DIRECTION_UP] = None
		self.neighbors[DIRECTION_DOWN] = None
		self.neighbors[DIRECTION_LEFT] = None
		self.neighbors[DIRECTION_RIGHT] = None

	#----------------------------------------------------------------------
	def MovePossible(self, direction):
		if self.neighbors[direction]:
			return 1


#------------------------------------------------------------------------------
def main():
	"""..."""
	evManager = EventManager()

	keybd = KeyboardController( evManager )
	spinner = CPUSpinnerController( evManager )
	pygameView = PygameView( evManager )
	game = Game( evManager )
	
	spinner.Run()

if __name__ == "__main__":
	main()

########NEW FILE########
__FILENAME__ = network

from example import *
from twisted.spread import pb

# A list of ALL possible events that a server can send to a client
serverToClientEvents = []
# A list of ALL possible events that a client can send to a server
clientToServerEvents = []

#------------------------------------------------------------------------------
#Mix-In Helper Functions
#------------------------------------------------------------------------------
def MixInClass( origClass, addClass ):
	if addClass not in origClass.__bases__:
		origClass.__bases__ += (addClass,)

#------------------------------------------------------------------------------
def MixInCopyClasses( someClass ):
	MixInClass( someClass, pb.Copyable )
	MixInClass( someClass, pb.RemoteCopy )

#------------------------------------------------------------------------------
def serialize(obj, registry):
    objType = type(obj)
    if objType in [str, unicode, int, float, bool, type(None)]:
        return obj

    elif objType in [list, tuple]:
        new_obj = []
        for sub_obj in obj:
            new_obj.append(serialize(sub_obj, registry))
        return new_obj

    elif objType == dict:
        new_obj = {}
        for key, val in obj.items():
            new_obj[serialize(key, registry)] = serialize(val, registry)
        return new_obj

    else:
        objID = id(obj)
        registry[objID] = obj
        return objID
        
#------------------------------------------------------------------------------
class Serializable:
    '''The Serializable interface.
    All objects inheriting Serializable must have a .copyworthy_attrs member.
    '''
    def getStateToCopy(self, registry):
        d = {}
        for attr in self.copyworthy_attrs:
            val = getattr(self, attr)
            new_val = serialize(val, registry)
            d[attr] = new_val

        return d


#------------------------------------------------------------------------------
#------------------------------------------------------------------------------
# For each event class, if it is sendable over the network, we have 
# to Mix In the "copy classes", or make a replacement event class that is 
# copyable

#------------------------------------------------------------------------------
# TickEvent
# Direction: don't send.
#The Tick event happens hundreds of times per second.  If we think we need
#to send it over the network, we should REALLY re-evaluate our design

#------------------------------------------------------------------------------
# QuitEvent
# Direction: Client to Server only
MixInCopyClasses( QuitEvent )
pb.setUnjellyableForClass(QuitEvent, QuitEvent)
clientToServerEvents.append( QuitEvent )

#------------------------------------------------------------------------------
# GameStartRequest
# Direction: Client to Server only
MixInCopyClasses( GameStartRequest )
pb.setUnjellyableForClass(GameStartRequest, GameStartRequest)
clientToServerEvents.append( GameStartRequest )



#------------------------------------------------------------------------------
# ServerConnectEvent
# Direction: don't send.
# we don't need to send this over the network.

#------------------------------------------------------------------------------
# ClientConnectEvent
# Direction: don't send.
# we don't need to send this over the network.

#------------------------------------------------------------------------------
class ServerErrorEvent(object):
	def __init__(self):
		self.name = "Server Err Event"

#------------------------------------------------------------------------------
class ClientErrorEvent(object):
	def __init__(self):
		self.name = "Client Err Event"

#------------------------------------------------------------------------------
# GameStartedEvent
# Direction: Server to Client only
class CopyableGameStartedEvent(pb.Copyable, pb.RemoteCopy):
	def __init__(self, event, registry):
		self.name = "Copyable Game Started Event"
		self.gameID = id(event.game)
		registry[self.gameID] = event.game
		#TODO: put this in a Player Join Event or something
		for p in event.game.players:
			registry[id(p)] = p

pb.setUnjellyableForClass(CopyableGameStartedEvent, CopyableGameStartedEvent)
serverToClientEvents.append( CopyableGameStartedEvent )

#------------------------------------------------------------------------------
# MapBuiltEvent
# Direction: Server to Client only
class CopyableMapBuiltEvent( pb.Copyable, pb.RemoteCopy):
	def __init__(self, event, registry ):
		self.name = "Copyable Map Finished Building Event"
		self.mapID = id( event.map )
		registry[self.mapID] = event.map

pb.setUnjellyableForClass(CopyableMapBuiltEvent, CopyableMapBuiltEvent)
serverToClientEvents.append( CopyableMapBuiltEvent )

#------------------------------------------------------------------------------
# CharactorMoveEvent
# Direction: Server to Client only
class CopyableCharactorMoveEvent( pb.Copyable, pb.RemoteCopy):
	def __init__(self, event, registry ):
		self.name = "Copyable " + event.name
		self.charactorID = id( event.charactor )
		registry[self.charactorID] = event.charactor

pb.setUnjellyableForClass(CopyableCharactorMoveEvent, CopyableCharactorMoveEvent)
serverToClientEvents.append( CopyableCharactorMoveEvent )

#------------------------------------------------------------------------------
# CharactorPlaceEvent
# Direction: Server to Client only
class CopyableCharactorPlaceEvent( pb.Copyable, pb.RemoteCopy):
	def __init__(self, event, registry ):
		self.name = "Copyable " + event.name
		self.charactorID = id( event.charactor )
		registry[self.charactorID] = event.charactor

pb.setUnjellyableForClass(CopyableCharactorPlaceEvent, CopyableCharactorPlaceEvent)
serverToClientEvents.append( CopyableCharactorPlaceEvent )


#------------------------------------------------------------------------------
class CopyableCharactor(Serializable):
	copyworthy_attrs = ['sector', 'state']

	def setCopyableState(self, stateDict, registry):
		neededObjIDs = []
		success = True

		self.state = stateDict['state']

		if stateDict['sector'] == None:
			self.sector = None
		elif not registry.has_key( stateDict['sector'] ):
			registry[stateDict['sector']] = Sector(self.evManager)
			neededObjIDs.append( stateDict['sector'] )
			success = False
		else:
			self.sector = registry[stateDict['sector']]

		return [success, neededObjIDs]
		

MixInClass( Charactor, CopyableCharactor )

#------------------------------------------------------------------------------
# PlayerJoinRequest
# Direction: Client to Server only
MixInCopyClasses( PlayerJoinRequest )
pb.setUnjellyableForClass(PlayerJoinRequest, PlayerJoinRequest)
clientToServerEvents.append( PlayerJoinRequest )

#------------------------------------------------------------------------------
# PlayerJoinEvent
# Direction: Server to Client only
class CopyablePlayerJoinEvent( pb.Copyable, pb.RemoteCopy):
	def __init__(self, event, registry):
		self.name = "Copyable " + event.name
		self.playerID = id(event.player)
		registry[self.playerID] = event.player
pb.setUnjellyableForClass(CopyablePlayerJoinEvent, CopyablePlayerJoinEvent)
serverToClientEvents.append( CopyablePlayerJoinEvent )

#------------------------------------------------------------------------------
# CharactorPlaceRequest
# Direction: Client to Server only
class CopyableCharactorPlaceRequest( pb.Copyable, pb.RemoteCopy):
	def __init__(self, event, registry ):
		self.name = "Copyable " + event.name
		self.playerID = None
		self.charactorID = None
		self.sectorID = None
		for key,val in registry.iteritems():
			if val is event.player:
				print 'making char place request'
				print 'self.playerid', key
				self.playerID = key
			if val is event.charactor:
				self.charactorID = key
			if val is event.sector:
				self.sectorID = key
		if None in ( self.playerID, self.charactorID, self.sectorID):
			print "SOMETHING REALLY WRONG"
			print self.playerID, event.player
			print self.charactorID, event.charactor
			print self.sectorID, event.sector
pb.setUnjellyableForClass(CopyableCharactorPlaceRequest, CopyableCharactorPlaceRequest)
clientToServerEvents.append( CopyableCharactorPlaceRequest )

#------------------------------------------------------------------------------
# CharactorMoveRequest
# Direction: Client to Server only
class CopyableCharactorMoveRequest( pb.Copyable, pb.RemoteCopy):
	def __init__(self, event, registry ):
		self.name = "Copyable " + event.name
		self.direction = event.direction
		self.playerID = None
		self.charactorID = None
		for key,val in registry.iteritems():
			if val is event.player:
				self.playerID = key
			if val is event.charactor:
				self.charactorID = key
		if None in ( self.playerID, self.charactorID):
			print "SOMETHING REALLY WRONG"
			print self.playerID, event.player
			print self.charactorID, event.charactor
pb.setUnjellyableForClass(CopyableCharactorMoveRequest, CopyableCharactorMoveRequest)
clientToServerEvents.append( CopyableCharactorMoveRequest )

#------------------------------------------------------------------------------
#------------------------------------------------------------------------------
# For any objects that we need to send in our events, we have to give them
# getStateToCopy() and setCopyableState() methods so that we can send a 
# network-friendly representation of them over the network.

#------------------------------------------------------------------------------
class CopyableMap:
	def getStateToCopy(self, registry):
		sectorIDList = []
		for sect in self.sectors:
			sID = id(sect)
			sectorIDList.append( sID )
			registry[sID] = sect

		return {'ninegrid':1, 'sectorIDList':sectorIDList}


	def setCopyableState(self, stateDict, registry):
		neededObjIDs = []
		success = True

		if self.state != Map.STATE_BUILT:
			self.Build()

		for i, sectID in enumerate(stateDict['sectorIDList']):
			registry[sectID] = self.sectors[i]

		return [success, neededObjIDs]

MixInClass( Map, CopyableMap )


#------------------------------------------------------------------------------
class CopyableGame(Serializable):
	copyworthy_attrs = ['map', 'state', 'players']

	def setCopyableState(self, stateDict, registry):
		neededObjIDs = []
		success = True

		self.state = stateDict['state']

		if stateDict['map'] not in registry:
			registry[stateDict['map']] = Map( self.evManager )
			neededObjIDs.append( stateDict['map'] )
			success = False
		else:
			self.map = registry[stateDict['map']]

		self.players = []
		for pID in stateDict['players']:
			if pID not in registry:
				registry[pID] = Player( self.evManager )
				neededObjIDs.append( pID )
				success = False
			else:
				self.players.append( registry[pID] )

		return [success, neededObjIDs]

MixInClass( Game, CopyableGame )

#------------------------------------------------------------------------------
class CopyablePlayer(Serializable):
	copyworthy_attrs = ['name', 'game', 'charactors']

	def setCopyableState(self, stateDict, registry):
		neededObjIDs = []
		success = True

		self.name = stateDict['name']

		if not registry.has_key( stateDict['game'] ):
			print "Something is wrong. should already be a game"
		else:
			self.game = registry[stateDict['game']]

		self.charactors = []
		for cID in stateDict['charactors']:
			if not cID in registry:
				registry[cID] = Charactor( self.evManager )
				neededObjIDs.append( cID )
				success = False
			else:
				self.charactors.append( registry[cID] )

		return [success, neededObjIDs]

MixInClass( Player, CopyablePlayer )

#------------------------------------------------------------------------------
# Copyable Sector is not necessary in this simple example because the sectors
# all get copied over in CopyableMap
#------------------------------------------------------------------------------
#------------------------------------------------------------------------------
class CopyableSector:
	def getStateToCopy(self, registry):
		return {}
		#d = self.__dict__.copy()
		#del d['evManager']
		#d['neighbors'][DIRECTION_UP] = id(d['neighbors'][DIRECTION_UP])
		#d['neighbors'][DIRECTION_DOWN] = id(d['neighbors'][DIRECTION_DOWN])
		#d['neighbors'][DIRECTION_LEFT] = id(d['neighbors'][DIRECTION_LEFT])
		#d['neighbors'][DIRECTION_RIGHT] = id(d['neighbors'][DIRECTION_RIGHT])
		#return d

	def setCopyableState(self, stateDict, registry):
		return [True, []]
		#neededObjIDs = []
		#success = True
		#if not registry.has_key( stateDict['neighbors'][DIRECTION_UP]):
			#neededObjIDs.append( stateDict['neighbors'][DIRECTION_UP] )
			#success = 0
		#else:
			#self.neighbors[DIRECTION_UP] = registry[stateDict['neighbors'][DIRECTION_UP]]
		#if not registry.has_key( stateDict['neighbors'][DIRECTION_DOWN]):
			#neededObjIDs.append( stateDict['neighbors'][DIRECTION_DOWN] )
			#success = 0
		#else:
			#self.neighbors[DIRECTION_DOWN] = registry[stateDict['neighbors'][DIRECTION_DOWN]]
		#if not registry.has_key( stateDict['neighbors'][DIRECTION_LEFT]):
			#neededObjIDs.append( stateDict['neighbors'][DIRECTION_LEFT] )
			#success = 0
		#else:
			#self.neighbors[DIRECTION_LEFT] = registry[stateDict['neighbors'][DIRECTION_LEFT]]
		#if not registry.has_key( stateDict['neighbors'][DIRECTION_RIGHT]):
			#neededObjIDs.append( stateDict['neighbors'][DIRECTION_RIGHT] )
			#success = 0
		#else:
			#self.neighbors[DIRECTION_RIGHT] = registry[stateDict['neighbors'][DIRECTION_RIGHT]]

		#return [success, neededObjIDs]

MixInClass( Sector, CopyableSector )

########NEW FILE########
__FILENAME__ = server
#! /usr/bin/env python
'''
Example server
'''

from twisted.spread import pb
from twisted.spread.pb import DeadReferenceError
from twisted.cred import checkers, portal
from zope.interface import implements
from example import EventManager, Game
from events import *
import network
from pprint import pprint

#------------------------------------------------------------------------------
class NoTickEventManager(EventManager):
    '''This subclass of EventManager doesn't wait for a Tick event before
    it starts consuming its event queue.  The server module doesn't have
    a CPUSpinnerController, so Ticks will not get generated.
    '''
    def __init__(self):
        EventManager.__init__(self)
        self._lock = False
    def Post(self, event):
        self.eventQueue.append(event)
        #print 'ev q is', self.eventQueue, 'lock is', self._lock
        if not self._lock:
            self._lock = True
            #print 'consuming queue'
            self.ActuallyUpdateListeners()
            self.ConsumeEventQueue()
            self._lock = False


#------------------------------------------------------------------------------
class TimerController:
    """A controller that sends an event every second"""
    def __init__(self, evManager, reactor):
        self.evManager = evManager
        self.evManager.RegisterListener( self )

        self.reactor = reactor
        self.numClients = 0

    #-----------------------------------------------------------------------
    def NotifyApplicationStarted( self ):
        self.reactor.callLater( 1, self.Tick )

    #-----------------------------------------------------------------------
    def Tick(self):
        if self.numClients == 0:
            return

        ev = SecondEvent()
        self.evManager.Post( ev )
        ev = TickEvent()
        self.evManager.Post( ev )
        self.reactor.callLater( 1, self.Tick )

    #----------------------------------------------------------------------
    def Notify(self, event):
        if isinstance( event, ClientConnectEvent ):
            # first client connected.  start the clock.
            self.numClients += 1
            if self.numClients == 1:
                self.Tick()
        if isinstance( event, ClientDisconnectEvent ):
            self.numClients -= 1
        if isinstance( event, FatalEvent ):
            PostMortem(event, self.reactor)

#------------------------------------------------------------------------------
def PostMortem(fatalEvent, reactor):
    print "\n\nFATAL EVENT.  STOPPING REACTOR"
    reactor.stop()
    from pprint import pprint
    print 'Shared Objects at the time of the fatal event:'
    pprint( sharedObjectRegistry )

#------------------------------------------------------------------------------
class RegularAvatar(pb.IPerspective): pass
#class DisallowedAvatar(pb.IPerspective): pass
#------------------------------------------------------------------------------
class MyRealm:
    implements(portal.IRealm)
    def __init__(self, evManager):
        self.evManager = evManager
        self.evManager.RegisterListener( self )
        # keep track of avatars that have been given out
        self.claimedAvatarIDs = []
        # we need to hold onto views so they don't get garbage collected
        self.clientViews = []
        # maps avatars to player(s) they control
        self.playersControlledByAvatar = {}

    #----------------------------------------------------------------------
    def requestAvatar(self, avatarID, mind, *interfaces):
        print ' v'*30
        print 'requesting avatar id: ', avatarID
        print ' ^'*30
        if pb.IPerspective not in interfaces:
            print 'TWISTED FAILURE'
            raise NotImplementedError
        avatarClass = RegularAvatar
        if avatarID in self.claimedAvatarIDs:
            #avatarClass = DisallowedAvatar
            raise Exception( 'Another client is already connected'
                             ' to this avatar (%s)' % avatarID )

        self.claimedAvatarIDs.append(avatarID)
        ev = ClientConnectEvent( mind, avatarID )
        self.evManager.Post( ev )

        # TODO: this should be ok when avatarID is checkers.ANONYMOUS
        if avatarID not in self.playersControlledByAvatar:
            self.playersControlledByAvatar[avatarID] = []
        view = NetworkClientView( self.evManager, avatarID, mind )
        controller = NetworkClientController(self.evManager,
                                             avatarID,
                                             self)
        self.clientViews.append(view)
        return avatarClass, controller, controller.clientDisconnect

    #----------------------------------------------------------------------
    def knownPlayers(self):
        allPlayers = []
        for pList in self.playersControlledByAvatar.values():
            allPlayers.extend(pList)
        return allPlayers

    #----------------------------------------------------------------------
    def Notify(self, event):
        if isinstance(event, ClientDisconnectEvent):
            print 'got cli disconnect'
            self.claimedAvatarIDs.remove(event.avatarID)
            removee = None
            for view in self.clientViews:
                if view.avatarID == event.avatarID:
                    removee = view
            if removee:
                self.clientViews.remove(removee)

            print 'after disconnect, state is:'
            pprint (self.__dict__)


#------------------------------------------------------------------------------
class NetworkClientController(pb.Avatar):
    """We RECEIVE events from the CLIENT through this object
    There is an instance of NetworkClientController for each connected
    client.
    """
    def __init__(self, evManager, avatarID, realm):
        self.evManager = evManager
        self.evManager.RegisterListener( self )
        self.avatarID = avatarID
        self.realm = realm

    #----------------------------------------------------------------------
    def clientDisconnect(self):
        '''When a client disconnect is detected, this method
        gets called
        '''
        ev = ClientDisconnectEvent( self.avatarID )
        self.evManager.Post( ev )

    #----------------------------------------------------------------------
    def perspective_GetGameSync(self):
        """this is usually called when a client first connects or
        when they reconnect after a drop
        """
        game = sharedObjectRegistry.getGame()
        if game == None:
            print 'GetGameSync: game was none'
            raise Exception('Game should be set by this point')
        gameID = id( game )
        gameDict = game.getStateToCopy( sharedObjectRegistry )

        return [gameID, gameDict]
    
    #----------------------------------------------------------------------
    def perspective_GetObjectState(self, objectID):
        #print "request for object state", objectID
        if not sharedObjectRegistry.has_key( objectID ):
            print "No key on the server"
            return [0,0]
        obj = sharedObjectRegistry[objectID]
        print 'getting state for object', obj
        print 'my registry is '
        pprint(sharedObjectRegistry)
        objDict = obj.getStateToCopy( sharedObjectRegistry )

        return [objectID, objDict]
    
    #----------------------------------------------------------------------
    def perspective_EventOverNetwork(self, event):
        if isinstance(event, network.CopyableCharactorPlaceRequest):
            try:
                player = sharedObjectRegistry[event.playerID]
            except KeyError, ex:
                self.evManager.Post( FatalEvent( ex ) )
                raise
            pName = player.name
            if pName not in self.PlayersIControl():
                print 'i do not control', player
                print 'see?', self.PlayersIControl()
                print 'so i will ignore', event
                return
            try:
                charactor = sharedObjectRegistry[event.charactorID]
                sector = sharedObjectRegistry[event.sectorID]
            except KeyError, ex:
                self.evManager.Post( FatalEvent( ex ) )
                raise
            ev = CharactorPlaceRequest( player, charactor, sector )
        elif isinstance(event, network.CopyableCharactorMoveRequest):
            try:
                player = sharedObjectRegistry[event.playerID]
            except KeyError, ex:
                self.evManager.Post( FatalEvent( ex ) )
                raise
            pName = player.name
            if pName not in self.PlayersIControl():
                return
            try:
                charactor = sharedObjectRegistry[event.charactorID]
            except KeyError, ex:
                print 'sharedObjs did not have key:', ex
                print 'current sharedObjs:', sharedObjectRegistry
                print 'Did a client try to poison me?'
                self.evManager.Post( FatalEvent( ex ) )
                raise
            direction = event.direction
            ev = CharactorMoveRequest(player, charactor, direction)

        elif isinstance(event, PlayerJoinRequest):
            pName = event.playerDict['name']
            print 'got player join req.  known players:', self.realm.knownPlayers()
            if pName in self.realm.knownPlayers():
                print 'this player %s has already joined' % pName
                return
            self.ControlPlayer(pName)
            ev = event
        else:
            ev = event

        self.evManager.Post( ev )

        return 1

    #----------------------------------------------------------------------
    def Notify(self, event):
        if isinstance( event, GameStartedEvent ):
            self.game = event.game

    #----------------------------------------------------------------------
    def PlayersIControl(self):
        return self.realm.playersControlledByAvatar[self.avatarID]

    #----------------------------------------------------------------------
    def ControlPlayer(self, playerName):
        '''Note: this modifies self.realm.playersControlledByAvatar'''
        players = self.PlayersIControl()
        players.append(playerName)
        

#------------------------------------------------------------------------------
class TextLogView(object):
    def __init__(self, evManager):
        self.evManager = evManager
        self.evManager.RegisterListener( self )

    #----------------------------------------------------------------------
    def Notify(self, event):
        if event.__class__ in [TickEvent, SecondEvent]:
            return

        print 'TEXTLOG <',
        
        if isinstance( event, CharactorPlaceEvent ):
            print event.name, " at ", event.charactor.sector

        elif isinstance( event, CharactorMoveEvent ):
            print event.name, " to ", event.charactor.sector
        else:
            print 'event:', event


#------------------------------------------------------------------------------
class NetworkClientView(object):
    """We SEND events to the CLIENT through this object"""
    def __init__(self, evManager, avatarID, client):
        print "\nADDING CLIENT", client

        self.evManager = evManager
        self.evManager.RegisterListener( self )

        self.avatarID = avatarID
        self.client = client

    #----------------------------------------------------------------------
    def RemoteCallError(self, failure):
        from twisted.internet.error import ConnectionLost
        #trap ensures that the rest will happen only 
        #if the failure was ConnectionLost
        failure.trap(ConnectionLost)
        self.HandleFailure(self.client)
        return failure

    #----------------------------------------------------------------------
    def HandleFailure(self):
        print "Failing Client", self.client

    #----------------------------------------------------------------------
    def RemoteCall( self, fnName, *args):
        try:
            remoteCall = self.client.callRemote(fnName, *args)
            remoteCall.addErrback(self.RemoteCallError)
        except DeadReferenceError:
            self.HandleFailure()

    #----------------------------------------------------------------------
    def EventThatShouldBeSent(self, event):
        ev = event

        #don't send events that aren't Copyable
        if not isinstance( ev, pb.Copyable ):
            evName = ev.__class__.__name__
            copyableClsName = "Copyable"+evName
            if not hasattr( network, copyableClsName ):
                return None
            copyableClass = getattr( network, copyableClsName )
            ev = copyableClass( ev, sharedObjectRegistry )

        if ev.__class__ not in network.serverToClientEvents:
            print "SERVER NOT SENDING: " +str(ev)
            return None

        return ev

    #----------------------------------------------------------------------
    def Notify(self, event):
        #NOTE: this is very "chatty".  We could restrict 
        #      the number of clients notified in the future

        ev = self.EventThatShouldBeSent(event)
        if not ev:
            return

        print "\n====server===sending: ", str(ev), 'to',
        print self.avatarID, '(', self.client, ')'
        self.RemoteCall( "ServerEvent", ev )


class Model(dict):
    def __init__(self, *args, **kwargs):
        dict.__init__(self, *args, **kwargs)
        self.gameKey = None

    def __setitem__(self, key, val):
        print 'setting', key, val
        dict.__setitem__(self, key, val)
        if isinstance(val, Game):
            self.gameKey = key

    def getGame(self):
        return self[self.gameKey]

evManager = None
sharedObjectRegistry = None
#------------------------------------------------------------------------------
def main():
    global evManager, sharedObjectRegistry
    from twisted.internet import reactor
    evManager = NoTickEventManager()
    sharedObjectRegistry = Model()

    log = TextLogView( evManager )
    timer = TimerController( evManager, reactor )
    game = Game( evManager )
    sharedObjectRegistry[id(game)] = game

    #factory = pb.PBServerFactory(clientController)
    #reactor.listenTCP( 8000, factory )

    realm = MyRealm(evManager)
    portl = portal.Portal(realm)
    checker = checkers.InMemoryUsernamePasswordDatabaseDontUse(
                                                           user1='pass1',
                                                           user2='pass1')
    portl.registerChecker(checker)
    reactor.listenTCP(8000, pb.PBServerFactory(portl))

    reactor.run()

if __name__ == "__main__":
    print 'starting server...'
    main()


########NEW FILE########
__FILENAME__ = events
#! /usr/bin/env python

#------------------------------------------------------------------------------
class EventManager:
    """this object is responsible for coordinating most communication
    between the Model, View, and Controller."""
    def __init__(self):
        from weakref import WeakKeyDictionary
        self.listeners = WeakKeyDictionary()
        self.eventQueue= []
        self.listenersToAdd = []
        self.listenersToRemove = []

    #----------------------------------------------------------------------
    def RegisterListener( self, listener ):
        self.listenersToAdd.append(listener)

    #----------------------------------------------------------------------
    def ActuallyUpdateListeners(self):
        for listener in self.listenersToAdd:
            self.listeners[ listener ] = 1
        for listener in self.listenersToRemove:
            if listener in self.listeners:
                del self.listeners[ listener ]

    #----------------------------------------------------------------------
    def UnregisterListener( self, listener ):
        self.listenersToRemove.append(listener)
        
    #----------------------------------------------------------------------
    def Post( self, event ):
        self.eventQueue.append(event)
        if isinstance(event, TickEvent):
            # Consume the event queue every Tick.
            self.ActuallyUpdateListeners()
            self.ConsumeEventQueue()

    #----------------------------------------------------------------------
    def ConsumeEventQueue(self):
        i = 0
        while i < len( self.eventQueue ):
            event = self.eventQueue[i]
            for listener in self.listeners:
                # Note: a side effect of notifying the listener
                # could be that more events are put on the queue
                # or listeners could Register / Unregister
                listener.Notify( event )
            i += 1
            if self.listenersToAdd:
                self.ActuallyUpdateListeners()
        #all code paths that could possibly add more events to 
        # the eventQueue have been exhausted at this point, so 
        # it's safe to empty the queue
        self.eventQueue= []

import Queue
class QueueEventManager(EventManager):
    def __init__(self):
        from weakref import WeakKeyDictionary
        self.listeners = WeakKeyDictionary()
        self.eventQueue = Queue.Queue()
        self.listenersToAdd = []
        self.listenersToRemove = []
        
    #----------------------------------------------------------------------
    def Post( self, event ):
        self.eventQueue.put(event)
        if isinstance(event, TickEvent):
            # Consume the event queue every Tick.
            self.ActuallyUpdateListeners()
            self.ConsumeEventQueue()

    #----------------------------------------------------------------------
    def ConsumeEventQueue(self):
        try:
            while True:
                event = self.eventQueue.get(block=False)
                for listener in self.listeners:
                    # Note: a side effect of notifying the listener
                    # could be that more events are put on the queue
                    # or listeners could Register / Unregister
                    listener.Notify( event )
                if self.listenersToAdd:
                    self.ActuallyUpdateListeners()
        except Queue.Empty:
            pass # print 'queue empty', self.eventQueue


class Event:
    """this is a superclass for any events that might be generated by an
    object and sent to the EventManager"""
    def __init__(self):
        self.name = "Generic Event"
    def __str__(self):
        return '<%10s %s>' % (self.__class__.__name__, id(self))
        
class TickEvent(Event):
    def __init__(self):
        self.name = "Tick"

class EventA(Event):
    def __init__(self):
        self.name = "Event A"

class EventB(Event):
    def __init__(self):
        self.name = "Event B"

class EventC(Event):
    def __init__(self):
        self.name = "Event C"

class Listener:
    def __init__(self, evManager):
        self.evManager = evManager
        self.evManager.RegisterListener(self)

    def __str__(self):
        return '<%20s %s>' % (self.__class__.__name__, id(self))

    def Notify(self, event):
        print self, 'got event', event

class ListenerAndPoster(Listener):
    def __init__(self, evManager):
        self.evManager = evManager
        self.evManager.RegisterListener(self)

    def Notify(self, event):
        print self, 'got event', event
        if isinstance(event, EventA):
            newEvent = EventC()
            self.evManager.Post(newEvent)

def main():
    evManager = EventManager()
    l1 = Listener(evManager)
    l2 = ListenerAndPoster(evManager)

    evManager.Post(EventA())
    evManager.Post(EventB())
    evManager.Post(TickEvent())

    evManager = QueueEventManager()
    l1 = Listener(evManager)
    l2 = ListenerAndPoster(evManager)

    evManager.Post(EventA())
    evManager.Post(EventB())
    evManager.Post(TickEvent())

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = example1
def Debug( msg ):
	print msg

DIRECTION_UP = 0
DIRECTION_DOWN = 1
DIRECTION_LEFT = 2
DIRECTION_RIGHT = 3

class Event:
	"""this is a superclass for any events that might be generated by an
	object and sent to the EventManager"""
	def __init__(self):
		self.name = "Generic Event"

class TickEvent(Event):
	def __init__(self):
		self.name = "CPU Tick Event"

class QuitEvent(Event):
	def __init__(self):
		self.name = "Program Quit Event"

class MapBuiltEvent(Event):
	def __init__(self, gameMap):
		self.name = "Map Finished Building Event"
		self.map = gameMap

class GameStartedEvent(Event):
	def __init__(self, game):
		self.name = "Game Started Event"
		self.game = game

class CharactorMoveRequest(Event):
	def __init__(self, direction):
		self.name = "Charactor Move Request"
		self.direction = direction

class CharactorPlaceEvent(Event):
	"""this event occurs when a Charactor is *placed* in a sector,
	ie it doesn't move there from an adjacent sector."""
	def __init__(self, charactor):
		self.name = "Charactor Placement Event"
		self.charactor = charactor

class CharactorMoveEvent(Event):
	def __init__(self, charactor):
		self.name = "Charactor Move Event"
		self.charactor = charactor

#------------------------------------------------------------------------------
class EventManager:
	"""this object is responsible for coordinating most communication
	between the Model, View, and Controller."""
	def __init__(self ):
		from weakref import WeakKeyDictionary
		self.listeners = WeakKeyDictionary()
		self.eventQueue= []

	#----------------------------------------------------------------------
	def RegisterListener( self, listener ):
		self.listeners[ listener ] = 1

	#----------------------------------------------------------------------
	def UnregisterListener( self, listener ):
		if listener in self.listeners:
			del self.listeners[ listener ]
		
	#----------------------------------------------------------------------
	def Post( self, event ):
		if not isinstance(event, TickEvent):
			Debug( "     Message: " + event.name )
		for listener in self.listeners:
			#NOTE: If the weakref has died, it will be 
			#automatically removed, so we don't have 
			#to worry about it.
			listener.Notify( event )

#------------------------------------------------------------------------------
class KeyboardController:
	"""..."""
	def __init__(self, evManager):
		self.evManager = evManager
		self.evManager.RegisterListener( self )

	#----------------------------------------------------------------------
	def Notify(self, event):
		if isinstance( event, TickEvent ):
			#Handle Input Events
			for event in pygame.event.get():
				ev = None
				if event.type == QUIT:
					ev = QuitEvent()
				elif event.type == KEYDOWN \
				     and event.key == K_ESCAPE:
					ev = QuitEvent()
				elif event.type == KEYDOWN \
				     and event.key == K_UP:
					direction = DIRECTION_UP
					ev = CharactorMoveRequest(direction)
				elif event.type == KEYDOWN \
				     and event.key == K_DOWN:
					direction = DIRECTION_DOWN
					ev = CharactorMoveRequest(direction)
				elif event.type == KEYDOWN \
				     and event.key == K_LEFT:
					direction = DIRECTION_LEFT
					ev = CharactorMoveRequest(direction)
				elif event.type == KEYDOWN \
				     and event.key == K_RIGHT:
					direction = DIRECTION_RIGHT
					ev = CharactorMoveRequest(direction)

				if ev:
					self.evManager.Post( ev )


#------------------------------------------------------------------------------
class CPUSpinnerController:
	"""..."""
	def __init__(self, evManager):
		self.evManager = evManager
		self.evManager.RegisterListener( self )

		self.keepGoing = 1

	#----------------------------------------------------------------------
	def Run(self):
		while self.keepGoing:
			event = TickEvent()
			self.evManager.Post( event )

	#----------------------------------------------------------------------
	def Notify(self, event):
		if isinstance( event, QuitEvent ):
			#this will stop the while loop from running
			self.keepGoing = False


import pygame
from pygame.locals import *
#------------------------------------------------------------------------------
class SectorSprite(pygame.sprite.Sprite):
	def __init__(self, sector, group=None):
		pygame.sprite.Sprite.__init__(self, group)
		self.image = pygame.Surface( (128,128) )
		self.image.fill( (0,255,128) )

		self.sector = sector

#------------------------------------------------------------------------------
class CharactorSprite(pygame.sprite.Sprite):
	def __init__(self, group=None):
		pygame.sprite.Sprite.__init__(self, group)

		charactorSurf = pygame.Surface( (64,64) )
		charactorSurf = charactorSurf.convert_alpha()
		charactorSurf.fill((0,0,0,0)) #make transparent
		pygame.draw.circle( charactorSurf, (255,0,0), (32,32), 32 )
		self.image = charactorSurf
		self.rect  = charactorSurf.get_rect()

		self.moveTo = None

	#----------------------------------------------------------------------
	def update(self):
		if self.moveTo:
			self.rect.center = self.moveTo
			self.moveTo = None

#------------------------------------------------------------------------------
class PygameView:
	"""..."""
	def __init__(self, evManager):
		self.evManager = evManager
		self.evManager.RegisterListener( self )

		pygame.init()
		self.window = pygame.display.set_mode( (424,440) )
		pygame.display.set_caption( 'Example Game' )
		self.background = pygame.Surface( self.window.get_size() )
		self.background.fill( (0,0,0) )

		self.backSprites = pygame.sprite.RenderUpdates()
		self.frontSprites = pygame.sprite.RenderUpdates()


	#----------------------------------------------------------------------
	def ShowMap(self, gameMap):
		squareRect = pygame.Rect( (-128,10, 128,128 ) )

		i = 0
		for sector in gameMap.sectors:
			if i < 3:
				squareRect = squareRect.move( 138,0 )
			else:
				i = 0
				squareRect = squareRect.move( -(138*2), 138 )
			i += 1
			newSprite = SectorSprite( sector, self.backSprites )
			newSprite.rect = squareRect
			newSprite = None

	#----------------------------------------------------------------------
	def ShowCharactor(self, charactor):
		charactorSprite = CharactorSprite( self.frontSprites )

		sector = charactor.sector
		sectorSprite = self.GetSectorSprite( sector )
		charactorSprite.rect.center = sectorSprite.rect.center

	#----------------------------------------------------------------------
	def MoveCharactor(self, charactor):
		charactorSprite = self.GetCharactorSprite( charactor )

		sector = charactor.sector
		sectorSprite = self.GetSectorSprite( sector )

		charactorSprite.moveTo = sectorSprite.rect.center

	#----------------------------------------------------------------------
	def GetCharactorSprite(self, charactor):
		#there will be only one
		for s in self.frontSprites:
			return s
		return None

	#----------------------------------------------------------------------
	def GetSectorSprite(self, sector):
		for s in self.backSprites:
			if hasattr(s, "sector") and s.sector == sector:
				return s


	#----------------------------------------------------------------------
	def Notify(self, event):
		if isinstance( event, TickEvent ):
			#Draw Everything
			self.backSprites.clear( self.window, self.background )
			self.frontSprites.clear( self.window, self.background )

			self.backSprites.update()
			self.frontSprites.update()

			dirtyRects1 = self.backSprites.draw( self.window )
			dirtyRects2 = self.frontSprites.draw( self.window )
			
			dirtyRects = dirtyRects1 + dirtyRects2
			pygame.display.update( dirtyRects )


		elif isinstance( event, MapBuiltEvent ):
			gameMap = event.map
			self.ShowMap( gameMap )

		elif isinstance( event, CharactorPlaceEvent ):
			self.ShowCharactor( event.charactor )

		elif isinstance( event, CharactorMoveEvent ):
			self.MoveCharactor( event.charactor )


#------------------------------------------------------------------------------
class Game:
	"""..."""

	STATE_PREPARING = 0
	STATE_RUNNING = 1
	STATE_PAUSED = 2

	#----------------------------------------------------------------------
	def __init__(self, evManager):
		self.evManager = evManager
		self.evManager.RegisterListener( self )

		self.state = Game.STATE_PREPARING
		
		self.players = [ Player(evManager) ]
		self.map = Map( evManager )

	#----------------------------------------------------------------------
	def Start(self):
		self.map.Build()
		self.state = Game.STATE_RUNNING
		ev = GameStartedEvent( self )
		self.evManager.Post( ev )

	#----------------------------------------------------------------------
	def Notify(self, event):
		if isinstance( event, TickEvent ):
			if self.state == Game.STATE_PREPARING:
				self.Start()

#------------------------------------------------------------------------------
class Player:
	"""..."""
	def __init__(self, evManager):
		self.evManager = evManager
		#self.evManager.RegisterListener( self )

		self.charactors = [ Charactor(evManager) ]

#------------------------------------------------------------------------------
class Charactor:
	"""..."""
	def __init__(self, evManager):
		self.evManager = evManager
		self.evManager.RegisterListener( self )
		self.sector = None

	#----------------------------------------------------------------------
	def Move(self, direction):
		if self.sector.MovePossible( direction ):
			newSector = self.sector.neighbors[direction]
			self.sector = newSector
			ev = CharactorMoveEvent( self )
			self.evManager.Post( ev )

	#----------------------------------------------------------------------
	def Place(self, sector):
		self.sector = sector
		ev = CharactorPlaceEvent( self )
		self.evManager.Post( ev )

	#----------------------------------------------------------------------
	def Notify(self, event):
		if isinstance( event, GameStartedEvent ):
			gameMap = event.game.map
			self.Place( gameMap.sectors[gameMap.startSectorIndex] )

		elif isinstance( event, CharactorMoveRequest ):
			self.Move( event.direction )

#------------------------------------------------------------------------------
class Map:
	"""..."""

	STATE_PREPARING = 0
	STATE_BUILT = 1


	#----------------------------------------------------------------------
	def __init__(self, evManager):
		self.evManager = evManager
		#self.evManager.RegisterListener( self )

		self.state = Map.STATE_PREPARING

		self.sectors = range(9)
		self.startSectorIndex = 0

	#----------------------------------------------------------------------
	def Build(self):
		for i in range(9):
			self.sectors[i] = Sector( self.evManager )

		self.sectors[3].neighbors[DIRECTION_UP] = self.sectors[0]
		self.sectors[4].neighbors[DIRECTION_UP] = self.sectors[1]
		self.sectors[5].neighbors[DIRECTION_UP] = self.sectors[2]
		self.sectors[6].neighbors[DIRECTION_UP] = self.sectors[3]
		self.sectors[7].neighbors[DIRECTION_UP] = self.sectors[4]
		self.sectors[8].neighbors[DIRECTION_UP] = self.sectors[5]

		self.sectors[0].neighbors[DIRECTION_DOWN] = self.sectors[3]
		self.sectors[1].neighbors[DIRECTION_DOWN] = self.sectors[4]
		self.sectors[2].neighbors[DIRECTION_DOWN] = self.sectors[5]
		self.sectors[3].neighbors[DIRECTION_DOWN] = self.sectors[6]
		self.sectors[4].neighbors[DIRECTION_DOWN] = self.sectors[7]
		self.sectors[5].neighbors[DIRECTION_DOWN] = self.sectors[8]

		self.sectors[1].neighbors[DIRECTION_LEFT] = self.sectors[0]
		self.sectors[2].neighbors[DIRECTION_LEFT] = self.sectors[1]
		self.sectors[4].neighbors[DIRECTION_LEFT] = self.sectors[3]
		self.sectors[5].neighbors[DIRECTION_LEFT] = self.sectors[4]
		self.sectors[7].neighbors[DIRECTION_LEFT] = self.sectors[6]
		self.sectors[8].neighbors[DIRECTION_LEFT] = self.sectors[7]

		self.sectors[0].neighbors[DIRECTION_RIGHT] = self.sectors[1]
		self.sectors[1].neighbors[DIRECTION_RIGHT] = self.sectors[2]
		self.sectors[3].neighbors[DIRECTION_RIGHT] = self.sectors[4]
		self.sectors[4].neighbors[DIRECTION_RIGHT] = self.sectors[5]
		self.sectors[6].neighbors[DIRECTION_RIGHT] = self.sectors[7]
		self.sectors[7].neighbors[DIRECTION_RIGHT] = self.sectors[8]

		self.state = Map.STATE_BUILT

		ev = MapBuiltEvent( self )
		self.evManager.Post( ev )

#------------------------------------------------------------------------------
class Sector:
	"""..."""
	def __init__(self, evManager):
		self.evManager = evManager
		#self.evManager.RegisterListener( self )

		self.neighbors = range(4)

		self.neighbors[DIRECTION_UP] = None
		self.neighbors[DIRECTION_DOWN] = None
		self.neighbors[DIRECTION_LEFT] = None
		self.neighbors[DIRECTION_RIGHT] = None

	#----------------------------------------------------------------------
	def MovePossible(self, direction):
		if self.neighbors[direction]:
			return 1


#------------------------------------------------------------------------------
def main():
	"""..."""
	evManager = EventManager()

	keybd = KeyboardController( evManager )
	spinner = CPUSpinnerController( evManager )
	pygameView = PygameView( evManager )
	game = Game( evManager )
	
	spinner.Run()

if __name__ == "__main__":
	main()

########NEW FILE########
__FILENAME__ = client
import network
from twisted.spread import pb
from twisted.internet.selectreactor import SelectReactor
from twisted.internet.main import installReactor
from events import *
from example1 import (EventManager,
                      Game,
                      KeyboardController,
                      CPUSpinnerController,
                      PygameView)

serverHost, serverPort = 'localhost', 8000

#------------------------------------------------------------------------------
class NetworkServerView(pb.Root):
	"""We SEND events to the server through this object"""
	STATE_PREPARING = 0
	STATE_CONNECTING = 1
	STATE_CONNECTED = 2
	STATE_DISCONNECTING = 3
	STATE_DISCONNECTED = 4

	#----------------------------------------------------------------------
	def __init__(self, evManager, sharedObjectRegistry):
		self.evManager = evManager
		self.evManager.RegisterListener( self )

		self.pbClientFactory = pb.PBClientFactory()
		self.state = NetworkServerView.STATE_PREPARING
		self.reactor = None
		self.server = None

		self.sharedObjs = sharedObjectRegistry

	#----------------------------------------------------------------------
	def AttemptConnection(self):
		print "attempting a connection to", serverHost, serverPort
		self.state = NetworkServerView.STATE_CONNECTING
		if self.reactor:
			self.reactor.stop()
			self.PumpReactor()
		else:
			self.reactor = SelectReactor()
			installReactor(self.reactor)
		connection = self.reactor.connectTCP(serverHost, serverPort,
		                                     self.pbClientFactory)
		deferred = self.pbClientFactory.getRootObject()
		deferred.addCallback(self.Connected)
		deferred.addErrback(self.ConnectFailed)
		self.reactor.startRunning()

	#----------------------------------------------------------------------
	def Disconnect(self):
		print "disconnecting"
		if not self.reactor:
			return
		print 'stopping the reactor'
		self.reactor.stop()
                self.PumpReactor()
		self.state = NetworkServerView.STATE_DISCONNECTING

	#----------------------------------------------------------------------
	def Connected(self, server):
		print "CONNECTED"
		self.server = server
		self.state = NetworkServerView.STATE_CONNECTED
		ev = ServerConnectEvent( server )
		self.evManager.Post( ev )

	#----------------------------------------------------------------------
	def ConnectFailed(self, server):
		print "CONNECTION FAILED"
		#self.state = NetworkServerView.STATE_PREPARING
		self.state = NetworkServerView.STATE_DISCONNECTED

	#----------------------------------------------------------------------
	def PumpReactor(self):
		self.reactor.runUntilCurrent()
		self.reactor.doIteration(0)

	#----------------------------------------------------------------------
	def Notify(self, event):
		NSV = NetworkServerView
		if isinstance( event, TickEvent ):
			if self.state == NSV.STATE_PREPARING:
				self.AttemptConnection()
			elif self.state in [NSV.STATE_CONNECTED,
			                    NSV.STATE_DISCONNECTING,
			                    NSV.STATE_CONNECTING]:
				self.PumpReactor()
			return

		if isinstance( event, QuitEvent ):
			self.Disconnect()
			return

		ev = event
		if not isinstance( event, pb.Copyable ):
			evName = event.__class__.__name__
			copyableClsName = "Copyable"+evName
			if not hasattr( network, copyableClsName ):
				return
			copyableClass = getattr( network, copyableClsName )
			ev = copyableClass( event, self.sharedObjs )

		if ev.__class__ not in network.clientToServerEvents:
			#print "CLIENT NOT SENDING: " +str(ev)
			return
			
		if self.server:
			print " ====   Client sending", str(ev)
			remoteCall = self.server.callRemote("EventOverNetwork",
			                                    ev)
		else:
			print " =--= Cannot send while disconnected:", str(ev)




#------------------------------------------------------------------------------
class NetworkServerController(pb.Referenceable):
	"""We RECEIVE events from the server through this object"""
	def __init__(self, evManager):
		self.evManager = evManager
		self.evManager.RegisterListener( self )

	#----------------------------------------------------------------------
	def remote_ServerEvent(self, event):
		print " ====  GOT AN EVENT FROM SERVER:", str(event)
		self.evManager.Post( event )
		return 1

	#----------------------------------------------------------------------
	def Notify(self, event):
		if isinstance( event, ServerConnectEvent ):
			#tell the server that we're listening to it and
			#it can access this object
			event.server.callRemote("ClientConnect", self)


#------------------------------------------------------------------------------
class PhonyEventManager(EventManager):
	#----------------------------------------------------------------------
	def Post( self, event ):
		pass

#------------------------------------------------------------------------------
class PhonyModel(object):
	'''This isn't the authouritative model.  That one exists on the
	server.  This is a model to store local state and to interact with
	the local EventManager.
	'''
	def __init__(self, evManager, sharedObjectRegistry):
		self.sharedObjs = sharedObjectRegistry
		self.game = None
		self.server = None
		self.phonyEvManager = PhonyEventManager()
		self.realEvManager = evManager

		self.realEvManager.RegisterListener( self )

	#----------------------------------------------------------------------
	def StateReturned(self, response):
		if response[0] == 0:
			print "GOT ZERO -- better error handler here"
			return None
		objID = response[0]
		objDict = response[1]
		obj = self.sharedObjs[objID]

		retval = obj.setCopyableState(objDict, self.sharedObjs)
		if retval[0] == 1:
			return obj
		for remainingObjID in retval[1]:
			remoteResponse = self.server.callRemote("GetObjectState", remainingObjID)
			remoteResponse.addCallback(self.StateReturned)

		#TODO: look under the Twisted Docs for "Chaining Defferreds"
		retval = obj.setCopyableState(objDict, self.sharedObjs)
		if retval[0] == 0:
			print "WEIRD!!!!!!!!!!!!!!!!!!"
			return None

		return obj

	#----------------------------------------------------------------------
	def Notify(self, event):
		if isinstance( event, ServerConnectEvent ):
			self.server = event.server
		elif isinstance( event, network.CopyableGameStartedEvent ):
			gameID = event.gameID
			if not self.game:
				# give a phony event manager to the local game
				# object so it won't be able to fire events
				self.game = Game( self.phonyEvManager )
				self.sharedObjs[gameID] = self.game
			#------------------------
			#note: we shouldn't really be calling methods on our
			# phony model, instead we should be copying the state
			# from the server.
			#self.game.Start()
			#------------------------
			print 'sending the gse to the real em.'
			ev = GameStartedEvent( self.game )
			self.realEvManager.Post( ev )

		if isinstance( event, network.CopyableMapBuiltEvent ):
			mapID = event.mapID
			if not self.game:
				self.game = Game( self.phonyEvManager )
			if self.sharedObjs.has_key(mapID):
				map = self.sharedObjs[mapID]
				ev = MapBuiltEvent( map )
				self.realEvManager.Post( ev )
			else:
				map = self.game.map
				self.sharedObjs[mapID] = map
				remoteResponse = self.server.callRemote("GetObjectState", mapID)
				remoteResponse.addCallback(self.StateReturned)
				remoteResponse.addCallback(self.MapBuiltCallback)

		if isinstance( event, network.CopyableCharactorPlaceEvent ):
			charactorID = event.charactorID
			if self.sharedObjs.has_key(charactorID):
				charactor = self.sharedObjs[charactorID]
				ev = CharactorPlaceEvent( charactor )
				self.realEvManager.Post( ev )
			else:
				charactor = self.game.players[0].charactors[0]
				self.sharedObjs[charactorID] = charactor
				remoteResponse = self.server.callRemote("GetObjectState", charactorID)
				remoteResponse.addCallback(self.StateReturned)
				remoteResponse.addCallback(self.CharactorPlaceCallback)

		if isinstance( event, network.CopyableCharactorMoveEvent ):
			charactorID = event.charactorID
			if self.sharedObjs.has_key(charactorID):
				charactor = self.sharedObjs[charactorID]
			else:
				charactor = self.game.players[0].charactors[0]
				self.sharedObjs[charactorID] = charactor
			remoteResponse = self.server.callRemote("GetObjectState", charactorID)
			remoteResponse.addCallback(self.StateReturned)
			remoteResponse.addCallback(self.CharactorMoveCallback)

	#----------------------------------------------------------------------
	def CharactorPlaceCallback(self, charactor):
		ev = CharactorPlaceEvent( charactor )
		self.realEvManager.Post( ev )
	#----------------------------------------------------------------------
	def MapBuiltCallback(self, map):
		ev = MapBuiltEvent( map )
		self.realEvManager.Post( ev )
	#----------------------------------------------------------------------
	def CharactorMoveCallback(self, charactor):
		ev = CharactorMoveEvent( charactor )
		self.realEvManager.Post( ev )


#------------------------------------------------------------------------------
def main():
	evManager = EventManager()
	sharedObjectRegistry = {}

	keybd = KeyboardController( evManager )
	spinner = CPUSpinnerController( evManager )
	pygameView = PygameView( evManager )

	phonyModel = PhonyModel( evManager, sharedObjectRegistry )

	#from twisted.spread.jelly import globalSecurity
	#globalSecurity.allowModules( network )

	serverController = NetworkServerController( evManager )
	serverView = NetworkServerView( evManager, sharedObjectRegistry )
	
	spinner.Run()
	print 'Done Run'
	print evManager.eventQueue

if __name__ == "__main__":
	main()

########NEW FILE########
__FILENAME__ = events
#SECURITY NOTE: anything in here can be created simply by sending the 
# class name over the network.  This is a potential vulnerability
# I wouldn't suggest letting any of these classes DO anything, especially
# things like file system access, or allocating huge amounts of memory

class Event:
	"""this is a superclass for any events that might be generated by an
	object and sent to the EventManager"""
	def __init__(self):
		self.name = "Generic Event"

class TickEvent(Event):
	def __init__(self):
		self.name = "CPU Tick Event"

class QuitEvent(Event):
	def __init__(self):
		self.name = "Program Quit Event"

class MapBuiltEvent(Event):
	def __init__(self, map):
		self.name = "Map Finished Building Event"
		self.map = map

class GameStartRequest(Event):
	def __init__(self):
		self.name = "Game Start Request"

class GameStartedEvent(Event):
	def __init__(self, game):
		self.name = "Game Started Event"
		self.game = game

class CharactorMoveRequest(Event):
	def __init__(self, direction):
		self.name = "Charactor Move Request"
		self.direction = direction

class CharactorMoveEvent(Event):
	def __init__(self, charactor):
		self.name = "Charactor Move Event"
		self.charactor = charactor

class CharactorPlaceEvent(Event):
	"""this event occurs when a Charactor is *placed* in a sector, 
	ie it doesn't move there from an adjacent sector."""
	def __init__(self, charactor):
		self.name = "Charactor Placement Event"
		self.charactor = charactor

class ServerConnectEvent(Event):
	"""the client generates this when it detects that it has successfully
	connected to the server"""
	def __init__(self, serverReference):
		self.name = "Network Server Connection Event"
		self.server = serverReference

class ClientConnectEvent(Event):
	"""this event is generated by the Server whenever a client connects
	to it"""
	def __init__(self, client):
		self.name = "Network Client Connection Event"
		self.client = client



########NEW FILE########
__FILENAME__ = example1
def Debug( msg ):
	print msg

DIRECTION_UP = 0
DIRECTION_DOWN = 1
DIRECTION_LEFT = 2
DIRECTION_RIGHT = 3

from events import *

#------------------------------------------------------------------------------
class EventManager:
	"""this object is responsible for coordinating most communication
	between the Model, View, and Controller."""
	def __init__(self ):
		from weakref import WeakKeyDictionary
		self.listeners = WeakKeyDictionary()
		self.eventQueue= []

	#----------------------------------------------------------------------
	def RegisterListener( self, listener ):
		self.listeners[ listener ] = 1

	#----------------------------------------------------------------------
	def UnregisterListener( self, listener ):
		if listener in self.listeners:
			del self.listeners[ listener ]
		
	#----------------------------------------------------------------------
	def Post( self, event ):
		self.eventQueue.append(event)
		if isinstance(event, TickEvent):
			# Consume the event queue every Tick.
			self.ConsumeEventQueue()
		else:
			Debug( "     Message: " + event.name )

	#----------------------------------------------------------------------
	def ConsumeEventQueue(self):
		i = 0
		while i < len( self.eventQueue ):
			event = self.eventQueue[i]
			for listener in self.listeners:
				# Note: a side effect of notifying the listener
				# could be that more events are put on the queue
				listener.Notify( event )
			i += 1
		#all code paths that could possibly add more events to 
		# the eventQueue have been exhausted at this point, so 
		# it's safe to empty the queue
		self.eventQueue= []


#------------------------------------------------------------------------------
class KeyboardController:
	"""..."""
	def __init__(self, evManager):
		self.evManager = evManager
		self.evManager.RegisterListener( self )

	#----------------------------------------------------------------------
	def Notify(self, event):
		if isinstance( event, TickEvent ):
			#Handle Input Events
			for event in pygame.event.get():
				ev = None
				if event.type == QUIT:
					ev = QuitEvent()
				elif event.type == KEYDOWN \
				     and event.key == K_ESCAPE:
					ev = QuitEvent()
				elif event.type == KEYDOWN \
				     and event.key == K_UP:
					direction = DIRECTION_UP
					ev = CharactorMoveRequest(direction)
				elif event.type == KEYDOWN \
				     and event.key == K_DOWN:
					direction = DIRECTION_DOWN
					ev = CharactorMoveRequest(direction)
				elif event.type == KEYDOWN \
				     and event.key == K_LEFT:
					direction = DIRECTION_LEFT
					ev = CharactorMoveRequest(direction)
				elif event.type == KEYDOWN \
				     and event.key == K_RIGHT:
					direction = DIRECTION_RIGHT
					ev = CharactorMoveRequest(direction)
				elif event.type == KEYDOWN:
					ev = GameStartRequest()

				if ev:
					self.evManager.Post( ev )


#------------------------------------------------------------------------------
class CPUSpinnerController:
	"""..."""
	def __init__(self, evManager):
		self.evManager = evManager
		self.evManager.RegisterListener( self )

		self.keepGoing = 1

	#----------------------------------------------------------------------
	def Run(self):
		while self.keepGoing:
			event = TickEvent()
			self.evManager.Post( event )

	#----------------------------------------------------------------------
	def Notify(self, event):
		if isinstance( event, QuitEvent ):
			#this will stop the while loop from running
			self.keepGoing = False


import pygame
from pygame.locals import *
#------------------------------------------------------------------------------
class SectorSprite(pygame.sprite.Sprite):
	def __init__(self, sector, group=None):
		pygame.sprite.Sprite.__init__(self, group)
		self.image = pygame.Surface( (128,128) )
		self.image.fill( (0,255,128) )

		self.sector = sector

#------------------------------------------------------------------------------
class CharactorSprite(pygame.sprite.Sprite):
	def __init__(self, group=None):
		pygame.sprite.Sprite.__init__(self, group)

		charactorSurf = pygame.Surface( (64,64) )
		charactorSurf = charactorSurf.convert_alpha()
		charactorSurf.fill((0,0,0,0)) #make transparent
		pygame.draw.circle( charactorSurf, (255,0,0), (32,32), 32 )
		self.image = charactorSurf
		self.rect  = charactorSurf.get_rect()

		self.moveTo = None

	#----------------------------------------------------------------------
	def update(self):
		if self.moveTo:
			self.rect.center = self.moveTo
			self.moveTo = None

#------------------------------------------------------------------------------
class PygameView:
	"""..."""
	def __init__(self, evManager):
		self.evManager = evManager
		self.evManager.RegisterListener( self )

		pygame.init()
		self.window = pygame.display.set_mode( (424,440) )
		pygame.display.set_caption( 'Example Game' )
		self.background = pygame.Surface( self.window.get_size() )
		self.background.fill( (0,0,0) )
		font = pygame.font.Font(None, 30)
		textImg = font.render( "Press SPACE BAR to start", 1, (255,0,0))
		self.background.blit( textImg, (0,0) )
		self.window.blit( self.background, (0,0) )
		pygame.display.flip()

		self.backSprites = pygame.sprite.RenderUpdates()
		self.frontSprites = pygame.sprite.RenderUpdates()


	#----------------------------------------------------------------------
	def ShowMap(self, gameMap):
		squareRect = pygame.Rect( (-128,10, 128,128 ) )

		i = 0
		for sector in gameMap.sectors:
			if i < 3:
				squareRect = squareRect.move( 138,0 )
			else:
				i = 0
				squareRect = squareRect.move( -(138*2), 138 )
			i += 1
			newSprite = SectorSprite( sector, self.backSprites )
			newSprite.rect = squareRect
			newSprite = None

	#----------------------------------------------------------------------
	def ShowCharactor(self, charactor):
		charactorSprite = CharactorSprite( self.frontSprites )

		sector = charactor.sector
		sectorSprite = self.GetSectorSprite( sector )
		charactorSprite.rect.center = sectorSprite.rect.center

	#----------------------------------------------------------------------
	def MoveCharactor(self, charactor):
		charactorSprite = self.GetCharactorSprite( charactor )

		sector = charactor.sector
		sectorSprite = self.GetSectorSprite( sector )

		charactorSprite.moveTo = sectorSprite.rect.center

	#----------------------------------------------------------------------
	def GetCharactorSprite(self, charactor):
		#there will be only one
		for s in self.frontSprites:
			return s
		return None

	#----------------------------------------------------------------------
	def GetSectorSprite(self, sector):
		for s in self.backSprites:
			if hasattr(s, "sector") and s.sector == sector:
				return s


	#----------------------------------------------------------------------
	def Notify(self, event):
		if isinstance( event, TickEvent ):
			#Draw Everything
			self.backSprites.clear( self.window, self.background )
			self.frontSprites.clear( self.window, self.background )

			self.backSprites.update()
			self.frontSprites.update()

			dirtyRects1 = self.backSprites.draw( self.window )
			dirtyRects2 = self.frontSprites.draw( self.window )
			
			dirtyRects = dirtyRects1 + dirtyRects2
			pygame.display.update( dirtyRects )


		elif isinstance( event, MapBuiltEvent ):
			gameMap = event.map
			self.ShowMap( gameMap )

		elif isinstance( event, CharactorPlaceEvent ):
			self.ShowCharactor( event.charactor )

		elif isinstance( event, CharactorMoveEvent ):
			self.MoveCharactor( event.charactor )


#------------------------------------------------------------------------------
class Game:
	"""..."""

	STATE_PREPARING = 0
	STATE_RUNNING = 1
	STATE_PAUSED = 2

	#----------------------------------------------------------------------
	def __init__(self, evManager):
		self.evManager = evManager
		self.evManager.RegisterListener( self )

		self.state = Game.STATE_PREPARING
		
		self.players = [ Player(evManager) ]
		self.map = Map( evManager )

	#----------------------------------------------------------------------
	def Start(self):
		self.map.Build()
		self.state = Game.STATE_RUNNING
		ev = GameStartedEvent( self )
		self.evManager.Post( ev )

	#----------------------------------------------------------------------
	def Notify(self, event):
		if isinstance( event, GameStartRequest ):
			if self.state == Game.STATE_PREPARING:
				self.Start()

#------------------------------------------------------------------------------
class Player:
	"""..."""
	def __init__(self, evManager):
		self.evManager = evManager
		#self.evManager.RegisterListener( self )

		self.charactors = [ Charactor(evManager) ]

#------------------------------------------------------------------------------
class Charactor:
	"""..."""

	STATE_INACTIVE = 0
	STATE_ACTIVE = 1

	def __init__(self, evManager):
		self.evManager = evManager
		self.evManager.RegisterListener( self )

		self.sector = None
		self.state = Charactor.STATE_INACTIVE

	#----------------------------------------------------------------------
	def Move(self, direction):
		if self.state == Charactor.STATE_INACTIVE:
			return

		if self.sector.MovePossible( direction ):
			newSector = self.sector.neighbors[direction]
			self.sector = newSector
			ev = CharactorMoveEvent( self )
			self.evManager.Post( ev )

	#----------------------------------------------------------------------
	def Place(self, sector):
		self.sector = sector
		self.state = Charactor.STATE_ACTIVE

		ev = CharactorPlaceEvent( self )
		self.evManager.Post( ev )

	#----------------------------------------------------------------------
	def Notify(self, event):
		if isinstance( event, GameStartedEvent ):
			gameMap = event.game.map
			self.Place( gameMap.sectors[gameMap.startSectorIndex] )

		elif isinstance( event, CharactorMoveRequest ):
			self.Move( event.direction )

#------------------------------------------------------------------------------
class Map:
	"""..."""

	STATE_PREPARING = 0
	STATE_BUILT = 1


	#----------------------------------------------------------------------
	def __init__(self, evManager):
		self.evManager = evManager
		#self.evManager.RegisterListener( self )

		self.state = Map.STATE_PREPARING

		self.sectors = range(9)
		self.startSectorIndex = 0

	#----------------------------------------------------------------------
	def Build(self):
		for i in range(9):
			self.sectors[i] = Sector( self.evManager )

		self.sectors[3].neighbors[DIRECTION_UP] = self.sectors[0]
		self.sectors[4].neighbors[DIRECTION_UP] = self.sectors[1]
		self.sectors[5].neighbors[DIRECTION_UP] = self.sectors[2]
		self.sectors[6].neighbors[DIRECTION_UP] = self.sectors[3]
		self.sectors[7].neighbors[DIRECTION_UP] = self.sectors[4]
		self.sectors[8].neighbors[DIRECTION_UP] = self.sectors[5]

		self.sectors[0].neighbors[DIRECTION_DOWN] = self.sectors[3]
		self.sectors[1].neighbors[DIRECTION_DOWN] = self.sectors[4]
		self.sectors[2].neighbors[DIRECTION_DOWN] = self.sectors[5]
		self.sectors[3].neighbors[DIRECTION_DOWN] = self.sectors[6]
		self.sectors[4].neighbors[DIRECTION_DOWN] = self.sectors[7]
		self.sectors[5].neighbors[DIRECTION_DOWN] = self.sectors[8]

		self.sectors[1].neighbors[DIRECTION_LEFT] = self.sectors[0]
		self.sectors[2].neighbors[DIRECTION_LEFT] = self.sectors[1]
		self.sectors[4].neighbors[DIRECTION_LEFT] = self.sectors[3]
		self.sectors[5].neighbors[DIRECTION_LEFT] = self.sectors[4]
		self.sectors[7].neighbors[DIRECTION_LEFT] = self.sectors[6]
		self.sectors[8].neighbors[DIRECTION_LEFT] = self.sectors[7]

		self.sectors[0].neighbors[DIRECTION_RIGHT] = self.sectors[1]
		self.sectors[1].neighbors[DIRECTION_RIGHT] = self.sectors[2]
		self.sectors[3].neighbors[DIRECTION_RIGHT] = self.sectors[4]
		self.sectors[4].neighbors[DIRECTION_RIGHT] = self.sectors[5]
		self.sectors[6].neighbors[DIRECTION_RIGHT] = self.sectors[7]
		self.sectors[7].neighbors[DIRECTION_RIGHT] = self.sectors[8]

		self.state = Map.STATE_BUILT

		ev = MapBuiltEvent( self )
		self.evManager.Post( ev )

#------------------------------------------------------------------------------
class Sector:
	"""..."""
	def __init__(self, evManager):
		self.evManager = evManager
		#self.evManager.RegisterListener( self )

		self.neighbors = range(4)

		self.neighbors[DIRECTION_UP] = None
		self.neighbors[DIRECTION_DOWN] = None
		self.neighbors[DIRECTION_LEFT] = None
		self.neighbors[DIRECTION_RIGHT] = None

	#----------------------------------------------------------------------
	def MovePossible(self, direction):
		if self.neighbors[direction]:
			return 1


#------------------------------------------------------------------------------
def main():
	"""..."""
	evManager = EventManager()

	keybd = KeyboardController( evManager )
	spinner = CPUSpinnerController( evManager )
	pygameView = PygameView( evManager )
	game = Game( evManager )
	
	spinner.Run()

if __name__ == "__main__":
	main()

########NEW FILE########
__FILENAME__ = network

from example1 import *
from twisted.spread import pb

# A list of ALL possible events that a server can send to a client
serverToClientEvents = []
# A list of ALL possible events that a client can send to a server
clientToServerEvents = []

#------------------------------------------------------------------------------
#Mix-In Helper Functions
#------------------------------------------------------------------------------
def MixInClass( origClass, addClass ):
	if addClass not in origClass.__bases__:
		origClass.__bases__ += (addClass,)

#------------------------------------------------------------------------------
def MixInCopyClasses( someClass ):
	MixInClass( someClass, pb.Copyable )
	MixInClass( someClass, pb.RemoteCopy )




#------------------------------------------------------------------------------
#------------------------------------------------------------------------------
# For each event class, if it is sendable over the network, we have 
# to Mix In the "copy classes", or make a replacement event class that is 
# copyable

#------------------------------------------------------------------------------
# TickEvent
# Direction: don't send.
#The Tick event happens hundreds of times per second.  If we think we need
#to send it over the network, we should REALLY re-evaluate our design

#------------------------------------------------------------------------------
# QuitEvent
# Direction: Client to Server only
MixInCopyClasses( QuitEvent )
pb.setUnjellyableForClass(QuitEvent, QuitEvent)
clientToServerEvents.append( QuitEvent )

#------------------------------------------------------------------------------
# GameStartRequest
# Direction: Client to Server only
MixInCopyClasses( GameStartRequest )
pb.setUnjellyableForClass(GameStartRequest, GameStartRequest)
clientToServerEvents.append( GameStartRequest )

#------------------------------------------------------------------------------
# CharactorMoveRequest
# Direction: Client to Server only
# this has an additional attribute, direction.  it is an int, so it's safe
MixInCopyClasses( CharactorMoveRequest )
pb.setUnjellyableForClass(CharactorMoveRequest, CharactorMoveRequest)
clientToServerEvents.append( CharactorMoveRequest )


#------------------------------------------------------------------------------
# ServerConnectEvent
# Direction: don't send.
# we don't need to send this over the network.

#------------------------------------------------------------------------------
# ClientConnectEvent
# Direction: don't send.
# we don't need to send this over the network.


#------------------------------------------------------------------------------
# GameStartedEvent
# Direction: Server to Client only
class CopyableGameStartedEvent(pb.Copyable, pb.RemoteCopy):
	def __init__(self, event, registry):
		self.name = "Copyable Game Started Event"
		self.gameID = id(event.game)
		registry[self.gameID] = event.game

pb.setUnjellyableForClass(CopyableGameStartedEvent, CopyableGameStartedEvent)
serverToClientEvents.append( CopyableGameStartedEvent )

#------------------------------------------------------------------------------
# MapBuiltEvent
# Direction: Server to Client only
class CopyableMapBuiltEvent( pb.Copyable, pb.RemoteCopy):
	def __init__(self, event, registry ):
		self.name = "Copyable Map Finished Building Event"
		self.mapID = id( event.map )
		registry[self.mapID] = event.map

pb.setUnjellyableForClass(CopyableMapBuiltEvent, CopyableMapBuiltEvent)
serverToClientEvents.append( CopyableMapBuiltEvent )

#------------------------------------------------------------------------------
# CharactorMoveEvent
# Direction: Server to Client only
class CopyableCharactorMoveEvent( pb.Copyable, pb.RemoteCopy):
	def __init__(self, event, registry ):
		self.name = "Copyable Charactor Move Event"
		self.charactorID = id( event.charactor )
		registry[self.charactorID] = event.charactor

pb.setUnjellyableForClass(CopyableCharactorMoveEvent, CopyableCharactorMoveEvent)
serverToClientEvents.append( CopyableCharactorMoveEvent )

#------------------------------------------------------------------------------
# CharactorPlaceEvent
# Direction: Server to Client only
class CopyableCharactorPlaceEvent( pb.Copyable, pb.RemoteCopy):
	def __init__(self, event, registry ):
		self.name = "Copyable Charactor Placement Event"
		self.charactorID = id( event.charactor )
		registry[self.charactorID] = event.charactor

pb.setUnjellyableForClass(CopyableCharactorPlaceEvent, CopyableCharactorPlaceEvent)
serverToClientEvents.append( CopyableCharactorPlaceEvent )



#------------------------------------------------------------------------------
class CopyableCharactor:
	def getStateToCopy(self):
		d = self.__dict__.copy()
		del d['evManager']
		d['sector'] = id( self.sector )
		return d





	def setCopyableState(self, stateDict, registry):
		neededObjIDs = []
		success = 1
		if not registry.has_key( stateDict['sector'] ):
			neededObjIDs.append( stateDict['sector'] )
			success = 0
		else:
			self.sector = registry[stateDict['sector']]
		return [success, neededObjIDs]
		


MixInClass( Charactor, CopyableCharactor )

#------------------------------------------------------------------------------
class CopyableMap:
	def getStateToCopy(self):
		sectorIDList = []
		for sect in self.sectors:
			sectorIDList.append( id(sect) )
		return {'ninegrid':1, 'sectorIDList':sectorIDList}





	def setCopyableState(self, stateDict, registry):
		neededObjIDs = []
		success = 1

		if self.state != Map.STATE_BUILT:
			self.Build()

		for i, sectID in enumerate(stateDict['sectorIDList']):
			registry[sectID] = self.sectors[i]

		return [success, neededObjIDs]

MixInClass( Map, CopyableMap )



########NEW FILE########
__FILENAME__ = server
#! /usr/bin/env python
'''
Example server
'''

from twisted.spread import pb
from example1 import EventManager, Game
from events import *
import network

#------------------------------------------------------------------------------
class NoTickEventManager(EventManager):
	'''This subclass of EventManager doesn't wait for a Tick event before
	it starts consuming its event queue.  The server module doesn't have
	a CPUSpinnerController, so Ticks will not get generated.
	'''
	def __init__(self):
		EventManager.__init__(self)
		self._lock = False
	def Post(self, event):
		EventManager.Post(self,event)
		if not self._lock:
			self._lock = True
			self.ConsumeEventQueue()
			self._lock = False



#------------------------------------------------------------------------------
class NetworkClientController(pb.Root):
	"""We RECEIVE events from the CLIENT through this object"""
	def __init__(self, evManager, sharedObjectRegistry):
		self.evManager = evManager
		self.evManager.RegisterListener( self )
		self.sharedObjs = sharedObjectRegistry

	#----------------------------------------------------------------------
	def remote_ClientConnect(self, netClient):
		#print "CLIENT CONNECT"
		ev = ClientConnectEvent( netClient )
		self.evManager.Post( ev )
		return 1

	#----------------------------------------------------------------------
	def remote_GetObjectState(self, objectID):
		#print "request for object state", objectID
		if not self.sharedObjs.has_key( objectID ):
			return [0,0]
		objDict = self.sharedObjs[objectID].getStateToCopy()
		return [objectID, objDict]
	
	#----------------------------------------------------------------------
	def remote_EventOverNetwork(self, event):
		#print "Server just got an EVENT" + str(event)
		self.evManager.Post( event )
		return 1

	#----------------------------------------------------------------------
	def Notify(self, event):
		pass


#------------------------------------------------------------------------------
class TextLogView(object):
	def __init__(self, evManager):
		self.evManager = evManager
		self.evManager.RegisterListener( self )

	#----------------------------------------------------------------------
	def Notify(self, event):
		if isinstance( event, TickEvent ):
			return

		print 'TEXTLOG <',
		
		if isinstance( event, CharactorPlaceEvent ):
			print event.name, " at ", event.charactor.sector

		elif isinstance( event, CharactorMoveEvent ):
			print event.name, " to ", event.charactor.sector


#------------------------------------------------------------------------------
class NetworkClientView(object):
	"""We SEND events to the CLIENT through this object"""
	def __init__(self, evManager, sharedObjectRegistry):
		self.evManager = evManager
		self.evManager.RegisterListener( self )

		self.clients = []
		self.sharedObjs = sharedObjectRegistry


	#----------------------------------------------------------------------
	def Notify(self, event):
		if isinstance( event, ClientConnectEvent ):
			self.clients.append( event.client )

		ev = event

		#don't broadcast events that aren't Copyable
		if not isinstance( ev, pb.Copyable ):
			evName = ev.__class__.__name__
			copyableClsName = "Copyable"+evName
			if not hasattr( network, copyableClsName ):
				return
			copyableClass = getattr( network, copyableClsName )
			ev = copyableClass( ev, self.sharedObjs )

		if ev.__class__ not in network.serverToClientEvents:
			#print "SERVER NOT SENDING: " +str(ev)
			return

		#NOTE: this is very "chatty".  We could restrict 
		#      the number of clients notified in the future
		for client in self.clients:
			print "=====server sending: ", str(ev)
			remoteCall = client.callRemote("ServerEvent", ev)



		
#------------------------------------------------------------------------------
def main():
	evManager = NoTickEventManager()
	sharedObjectRegistry = {}

	log = TextLogView( evManager )
	clientController = NetworkClientController( evManager, sharedObjectRegistry )
	clientView = NetworkClientView( evManager, sharedObjectRegistry )
	game = Game( evManager )

	from twisted.internet import reactor
	reactor.listenTCP( 8000, pb.PBServerFactory(clientController) )

	reactor.run()

if __name__ == "__main__":
	main()

########NEW FILE########
__FILENAME__ = client
import network
from twisted.spread import pb
from twisted.internet.selectreactor import SelectReactor
from twisted.internet.main import installReactor
from events import *
from example1 import (EventManager,
                      Game,
                      KeyboardController,
                      CPUSpinnerController,
                      PygameView)

serverHost, serverPort = 'localhost', 8000

#------------------------------------------------------------------------------
class NetworkServerView(pb.Root):
    """We SEND events to the server through this object"""
    STATE_PREPARING = 0
    STATE_CONNECTING = 1
    STATE_CONNECTED = 2
    STATE_DISCONNECTING = 3
    STATE_DISCONNECTED = 4

    #----------------------------------------------------------------------
    def __init__(self, evManager, sharedObjectRegistry):
            self.evManager = evManager
            self.evManager.RegisterListener( self )

            self.pbClientFactory = pb.PBClientFactory()
            self.state = NetworkServerView.STATE_PREPARING
            self.reactor = None
            self.server = None

            self.sharedObjs = sharedObjectRegistry

    #----------------------------------------------------------------------
    def AttemptConnection(self):
            print "attempting a connection to", serverHost, serverPort
            self.state = NetworkServerView.STATE_CONNECTING
            if self.reactor:
                    self.reactor.stop()
                    self.PumpReactor()
            else:
                    self.reactor = SelectReactor()
                    installReactor(self.reactor)
            connection = self.reactor.connectTCP(serverHost, serverPort,
                                                 self.pbClientFactory)
            deferred = self.pbClientFactory.getRootObject()
            deferred.addCallback(self.Connected)
            deferred.addErrback(self.ConnectFailed)
            self.reactor.startRunning()

    #----------------------------------------------------------------------
    def Disconnect(self):
            print "disconnecting"
            if not self.reactor:
                    return
            print 'stopping the reactor'
            self.reactor.stop()
            self.PumpReactor()
            self.state = NetworkServerView.STATE_DISCONNECTING

    #----------------------------------------------------------------------
    def Connected(self, server):
            print "CONNECTED"
            self.server = server
            self.state = NetworkServerView.STATE_CONNECTED
            ev = ServerConnectEvent( server )
            self.evManager.Post( ev )

    #----------------------------------------------------------------------
    def ConnectFailed(self, server):
            print "CONNECTION FAILED"
            #self.state = NetworkServerView.STATE_PREPARING
            self.state = NetworkServerView.STATE_DISCONNECTED

    #----------------------------------------------------------------------
    def PumpReactor(self):
            self.reactor.runUntilCurrent()
            self.reactor.doIteration(0)

    #----------------------------------------------------------------------
    def Notify(self, event):
            NSV = NetworkServerView
            if isinstance( event, TickEvent ):
                    if self.state == NSV.STATE_PREPARING:
                            self.AttemptConnection()
                    elif self.state in [NSV.STATE_CONNECTED,
                                        NSV.STATE_DISCONNECTING,
                                        NSV.STATE_CONNECTING]:
                            self.PumpReactor()
                    return

            if isinstance( event, QuitEvent ):
                    self.Disconnect()
                    return

            ev = event
            if not isinstance( event, pb.Copyable ):
                    evName = event.__class__.__name__
                    copyableClsName = "Copyable"+evName
                    if not hasattr( network, copyableClsName ):
                            return
                    copyableClass = getattr( network, copyableClsName )
                    #NOTE, never even construct an instance of an event that
                    # is serverToClient, as a side effect is often adding a
                    # key to the registry with the local id().
                    if copyableClass not in network.clientToServerEvents:
                        return
                    print 'creating instance of copyable class', copyableClsName
                    ev = copyableClass( event, self.sharedObjs )

            if ev.__class__ not in network.clientToServerEvents:
                    #print "CLIENT NOT SENDING: " +str(ev)
                    return
                    
            if self.server:
                    print " ====   Client sending", str(ev)
                    remoteCall = self.server.callRemote("EventOverNetwork", ev)
            else:
                    print " =--= Cannot send while disconnected:", str(ev)


#------------------------------------------------------------------------------
class NetworkServerController(pb.Referenceable):
    """We RECEIVE events from the server through this object"""
    def __init__(self, evManager):
        self.evManager = evManager
        self.evManager.RegisterListener( self )

    #----------------------------------------------------------------------
    def remote_ServerEvent(self, event):
        print " ====  GOT AN EVENT FROM SERVER:", str(event)
        self.evManager.Post( event )
        return 1

    #----------------------------------------------------------------------
    def Notify(self, event):
        if isinstance( event, ServerConnectEvent ):
            #tell the server that we're listening to it and
            #it can access this object
            event.server.callRemote("ClientConnect", self)


#------------------------------------------------------------------------------
class PhonyEventManager(EventManager):
    """this object is responsible for coordinating most communication
    between the Model, View, and Controller."""
    #----------------------------------------------------------------------
    def Post( self, event ):
        pass

#------------------------------------------------------------------------------
class PhonyModel:
    '''This isn't the authouritative model.  That one exists on the
    server.  This is a model to store local state and to interact with
    the local EventManager.
    '''

    #----------------------------------------------------------------------
    def __init__(self, evManager, sharedObjectRegistry):
            self.sharedObjs = sharedObjectRegistry
            self.game = None
            self.server = None
            self.phonyEvManager = PhonyEventManager()
            self.realEvManager = evManager
            self.neededObjects = []
            self.waitingObjectStack = []

            self.realEvManager.RegisterListener( self )

    #----------------------------------------------------------------------
    def GameReturned(self, response):
            if response[0] == 0:
                    print "GameReturned : game HASNT started"
                    #the game has not been started on the server.
                    #we'll be informed of the gameID when we receive the
                    #GameStartedEvent
                    return None
            else:
                    gameID = response[0]
                    print "GameReturned : game started ", gameID

                    self.sharedObjs[gameID] = self.game
            return self.StateReturned( response, self.GameSyncCallback )

    #----------------------------------------------------------------------
    def StateReturned(self, response):
            """this is a callback that is called in response to
            invoking GetObjectState on the server"""

            print "looking for ", response
            objID, objDict = response
            if objID == 0:
                    print "GOT ZERO -- better error handler here"
                    return None
            obj = self.sharedObjs[objID]

            success, neededObjIDs =\
                             obj.setCopyableState(objDict, self.sharedObjs)
            if success:
                    #we successfully set the state and no further objects
                    #are needed to complete the current object
                    if objID in self.neededObjects:
                            self.neededObjects.remove(objID)

            else:
                    #to complete the current object, we need to grab the
                    #state from some more objects on the server.  The IDs
                    #for those needed objects were passed back 
                    #in neededObjIDs
                    for neededObjID in neededObjIDs:
                            if neededObjID not in self.neededObjects:
                                    self.neededObjects.append(neededObjID)
                    print "failed.  still need ", self.neededObjects
    
            self.waitingObjectStack.append( (obj, objDict) )

            retval = self.GetAllNeededObjects()
            if retval:
                    # retval is a Deferred - returning it causes a chain
                    # to be formed.  The original deferred must wait for
                    # this new one to return before it calls its next
                    # callback
                    return retval
    
    #----------------------------------------------------------------------
    def GetAllNeededObjects(self):
            if len(self.neededObjects) == 0:
                    # this is the recursion-ending condition.  If there are
                    # no more objects needed to be grabbed from the server
                    # then we can try to setCopyableState on them again and
                    # we should now have all the needed objects, ensuring
                    # that setCopyableState succeeds
                    return self.ConsumeWaitingObjectStack()

            # still in the recursion step.  Try to get the object state for
            # the objectID on the top of the stack.  Note that the 
            # recursion is done via a deferred, which may be confusing
            nextID = self.neededObjects[-1]
            print "next one to grab: ", nextID
            remoteResponse = self.server.callRemote("GetObjectState",nextID)
            remoteResponse.addCallback(self.StateReturned)
            return remoteResponse

    #----------------------------------------------------------------------
    def ConsumeWaitingObjectStack(self):
        # All the needed objects should be present now.  Just the
        # matter of setting the state on the waiting objects remains.
        while self.waitingObjectStack:
            obj, objDict = self.waitingObjectStack.pop()
            success, neededObjIDs =\
                                 obj.setCopyableState(objDict, self.sharedObjs)
            if not success:
                print "WEIRD!!!!!!!!!!!!!!!!!!"

    #----------------------------------------------------------------------
    def Notify(self, event):
        if isinstance( event, ServerConnectEvent ):
            self.server = event.server
            #when we connect to the server, we should get the
            #entire game state.  this also applies to RE-connecting
            if not self.game:
                self.game = Game( self.phonyEvManager )
            remoteResponse = self.server.callRemote("GetGame")
            remoteResponse.addCallback(self.GameReturned)

        elif isinstance( event, network.CopyableGameStartedEvent ):
            gameID = event.gameID
            if not self.game:
                self.game = Game( self.phonyEvManager )
            self.sharedObjs[gameID] = self.game
            ev = GameStartedEvent( self.game )
            self.realEvManager.Post( ev )

        if isinstance( event, network.CopyableMapBuiltEvent ):
            mapID = event.mapID
            if not self.sharedObjs.has_key(mapID):
                self.sharedObjs[mapID] = self.game.map
            remoteResponse = self.server.callRemote("GetObjectState", mapID)
            remoteResponse.addCallback(self.StateReturned)
            remoteResponse.addCallback(self.MapBuiltCallback, mapID)

        if isinstance( event, network.CopyableCharactorPlaceEvent ):
            charactorID = event.charactorID
            if not self.sharedObjs.has_key(charactorID):
                charactor = self.game.players[0].charactors[0]
                self.sharedObjs[charactorID] = charactor
            remoteResponse = self.server.callRemote("GetObjectState", charactorID)
            remoteResponse.addCallback(self.StateReturned)
            remoteResponse.addCallback(self.CharactorPlaceCallback, charactorID)

        if isinstance( event, network.CopyableCharactorMoveEvent ):
            charactorID = event.charactorID
            if not self.sharedObjs.has_key(charactorID):
                charactor = self.game.players[0].charactors[0]
                self.sharedObjs[charactorID] = charactor
            remoteResponse = self.server.callRemote("GetObjectState", charactorID)
            remoteResponse.addCallback(self.StateReturned)
            remoteResponse.addCallback(self.CharactorMoveCallback, charactorID)

    #----------------------------------------------------------------------
    def CharactorPlaceCallback(self, deferredResult, charactorID):
        charactor = self.sharedObjs[charactorID]
        ev = CharactorPlaceEvent( charactor )
        self.realEvManager.Post( ev )
    #----------------------------------------------------------------------
    def MapBuiltCallback(self, deferredResult, mapID):
        gameMap = self.sharedObjs[mapID]
        ev = MapBuiltEvent( gameMap )
        self.realEvManager.Post( ev )
    #----------------------------------------------------------------------
    def CharactorMoveCallback(self, deferredResult, charactorID):
        charactor = self.sharedObjs[charactorID]
        ev = CharactorMoveEvent( charactor )
        self.realEvManager.Post( ev )
    #----------------------------------------------------------------------
    def GameSyncCallback(self, game):
        print "sending out the GS EVENT------------------==========="
        ev = GameSyncEvent( game )
        self.realEvManager.Post( ev )

#------------------------------------------------------------------------------
def main():
    evManager = EventManager()
    sharedObjectRegistry = {}

    keybd = KeyboardController( evManager )
    spinner = CPUSpinnerController( evManager )
    pygameView = PygameView( evManager )

    phonyModel = PhonyModel( evManager, sharedObjectRegistry  )

    serverController = NetworkServerController( evManager )
    serverView = NetworkServerView( evManager, sharedObjectRegistry )
    
    spinner.Run()

if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = events
#SECURITY NOTE: anything in here can be created simply by sending the 
# class name over the network.  This is a potential vulnerability
# I wouldn't suggest letting any of these classes DO anything, especially
# things like file system access, or allocating huge amounts of memory

class Event:
	"""this is a superclass for any events that might be generated by an
	object and sent to the EventManager"""
	def __init__(self):
		self.name = "Generic Event"

class TickEvent(Event):
	def __init__(self):
		self.name = "CPU Tick Event"

class SecondEvent(Event):
	def __init__(self):
		self.name = "Clock One Second Event"

class QuitEvent(Event):
	def __init__(self):
		self.name = "Program Quit Event"

class MapBuiltEvent(Event):
	def __init__(self, map):
		self.name = "Map Finished Building Event"
		self.map = map

class GameStartRequest(Event):
	def __init__(self):
		self.name = "Game Start Request"

class GameStartedEvent(Event):
	def __init__(self, game):
		self.name = "Game Started Event"
		self.game = game

class CharactorMoveRequest(Event):
	def __init__(self, direction):
		self.name = "Charactor Move Request"
		self.direction = direction

class CharactorMoveEvent(Event):
	def __init__(self, charactor):
		self.name = "Charactor Move Event"
		self.charactor = charactor

class CharactorPlaceEvent(Event):
	"""this event occurs when a Charactor is *placed* in a sector, 
	ie it doesn't move there from an adjacent sector."""
	def __init__(self, charactor):
		self.name = "Charactor Placement Event"
		self.charactor = charactor

class ServerConnectEvent(Event):
	"""the client generates this when it detects that it has successfully
	connected to the server"""
	def __init__(self, serverReference):
		self.name = "Network Server Connection Event"
		self.server = serverReference

class ClientConnectEvent(Event):
	"""this event is generated by the Server whenever a client connects
	to it"""
	def __init__(self, client):
		self.name = "Network Client Connection Event"
		self.client = client

class ClientDisconnectEvent(Event):
	"""this event is generated by the Server when it finds that a client 
	is no longer connected"""
	def __init__(self, client):
		self.name = "Network Client Disconnection Event"
		self.client = client

class GameSyncEvent(Event):
	"""..."""
	def __init__(self, game):
		self.name = "Game Synched to Authoritative State"
		self.game = game

########NEW FILE########
__FILENAME__ = example1
def Debug( msg ):
	print msg

DIRECTION_UP = 0
DIRECTION_DOWN = 1
DIRECTION_LEFT = 2
DIRECTION_RIGHT = 3

from events import *

#------------------------------------------------------------------------------
class EventManager:
	"""this object is responsible for coordinating most communication
	between the Model, View, and Controller."""
	def __init__(self):
		from weakref import WeakKeyDictionary
		self.listeners = WeakKeyDictionary()
		self.eventQueue= []
		self.listenersToAdd = []
		self.listenersToRemove = []

	#----------------------------------------------------------------------
	def RegisterListener( self, listener ):
		self.listenersToAdd.append(listener)

	#----------------------------------------------------------------------
	def ActuallyUpdateListeners(self):
		for listener in self.listenersToAdd:
			self.listeners[ listener ] = 1
		for listener in self.listenersToRemove:
			if listener in self.listeners:
				del self.listeners[ listener ]

	#----------------------------------------------------------------------
	def UnregisterListener( self, listener ):
		self.listenersToRemove.append(listener)
		
	#----------------------------------------------------------------------
	def Post( self, event ):
		self.eventQueue.append(event)
		if isinstance(event, TickEvent):
			# Consume the event queue every Tick.
			self.ActuallyUpdateListeners()
			self.ConsumeEventQueue()
		else:
			Debug( "     Message: " + event.name )

	#----------------------------------------------------------------------
	def ConsumeEventQueue(self):
		i = 0
		while i < len( self.eventQueue ):
			event = self.eventQueue[i]
			for listener in self.listeners:
				# Note: a side effect of notifying the listener
				# could be that more events are put on the queue
				# or listeners could Register / Unregister
				old = len(self.eventQueue)
				listener.Notify( event )
			i += 1
			if self.listenersToAdd:
				self.ActuallyUpdateListeners()
		#all code paths that could possibly add more events to 
		# the eventQueue have been exhausted at this point, so 
		# it's safe to empty the queue
		self.eventQueue= []


#------------------------------------------------------------------------------
class KeyboardController:
	"""..."""
	def __init__(self, evManager):
		self.evManager = evManager
		self.evManager.RegisterListener( self )

	#----------------------------------------------------------------------
	def Notify(self, event):
		if isinstance( event, TickEvent ):
			#Handle Input Events
			for event in pygame.event.get():
				ev = None
				if event.type == QUIT:
					ev = QuitEvent()
				elif event.type == KEYDOWN \
				     and event.key == K_ESCAPE:
					ev = QuitEvent()
				elif event.type == KEYDOWN \
				     and event.key == K_UP:
					direction = DIRECTION_UP
					ev = CharactorMoveRequest(direction)
				elif event.type == KEYDOWN \
				     and event.key == K_DOWN:
					direction = DIRECTION_DOWN
					ev = CharactorMoveRequest(direction)
				elif event.type == KEYDOWN \
				     and event.key == K_LEFT:
					direction = DIRECTION_LEFT
					ev = CharactorMoveRequest(direction)
				elif event.type == KEYDOWN \
				     and event.key == K_RIGHT:
					direction = DIRECTION_RIGHT
					ev = CharactorMoveRequest(direction)
				elif event.type == KEYDOWN:
					ev = GameStartRequest()

				if ev:
					self.evManager.Post( ev )


#------------------------------------------------------------------------------
class CPUSpinnerController:
	"""..."""
	def __init__(self, evManager):
		self.evManager = evManager
		self.evManager.RegisterListener( self )

		self.keepGoing = 1

	#----------------------------------------------------------------------
	def Run(self):
		while self.keepGoing:
			event = TickEvent()
			self.evManager.Post( event )

	#----------------------------------------------------------------------
	def Notify(self, event):
		if isinstance( event, QuitEvent ):
			#this will stop the while loop from running
			self.keepGoing = False


import pygame
from pygame.locals import *
#------------------------------------------------------------------------------
class SectorSprite(pygame.sprite.Sprite):
	def __init__(self, sector, group=None):
		pygame.sprite.Sprite.__init__(self, group)
		self.image = pygame.Surface( (128,128) )
		self.image.fill( (0,255,128) )

		self.sector = sector

#------------------------------------------------------------------------------
class CharactorSprite(pygame.sprite.Sprite):
	def __init__(self, group=None):
		pygame.sprite.Sprite.__init__(self, group)

		charactorSurf = pygame.Surface( (64,64) )
		charactorSurf = charactorSurf.convert_alpha()
		charactorSurf.fill((0,0,0,0)) #make transparent
		pygame.draw.circle( charactorSurf, (255,0,0), (32,32), 32 )
		self.image = charactorSurf
		self.rect  = charactorSurf.get_rect()

		self.moveTo = None

	#----------------------------------------------------------------------
	def update(self):
		if self.moveTo:
			self.rect.center = self.moveTo
			self.moveTo = None

#------------------------------------------------------------------------------
class PygameView:
	"""..."""
	def __init__(self, evManager):
		self.evManager = evManager
		self.evManager.RegisterListener( self )

		pygame.init()
		self.window = pygame.display.set_mode( (424,440) )
		pygame.display.set_caption( 'Example Game' )
		self.background = pygame.Surface( self.window.get_size() )
		self.background.fill( (0,0,0) )
		font = pygame.font.Font(None, 30)
		textImg = font.render( "Press SPACE BAR to start", 1, (255,0,0))
		self.background.blit( textImg, (0,0) )
		self.window.blit( self.background, (0,0) )
		pygame.display.flip()

		self.backSprites = pygame.sprite.RenderUpdates()
		self.frontSprites = pygame.sprite.RenderUpdates()


	#----------------------------------------------------------------------
	def ShowMap(self, gameMap):
		squareRect = pygame.Rect( (-128,10, 128,128 ) )

		i = 0
		for sector in gameMap.sectors:
			if i < 3:
				squareRect = squareRect.move( 138,0 )
			else:
				i = 0
				squareRect = squareRect.move( -(138*2), 138 )
			i += 1
			newSprite = SectorSprite( sector, self.backSprites )
			newSprite.rect = squareRect
			newSprite = None

	#----------------------------------------------------------------------
 	def ShowCharactor(self, charactor):
		sector = charactor.sector
		if not sector:
			print "Charactor is not in a sector.  cannot show"
			return

		charactorSprite = self.GetCharactorSprite( charactor )
		if not charactorSprite:
			charactorSprite = CharactorSprite( self.frontSprites )
		sectorSprite = self.GetSectorSprite( sector )
		charactorSprite.rect.center = sectorSprite.rect.center

	#----------------------------------------------------------------------
	def MoveCharactor(self, charactor):
		charactorSprite = self.GetCharactorSprite( charactor )

		sector = charactor.sector
		sectorSprite = self.GetSectorSprite( sector )

		charactorSprite.moveTo = sectorSprite.rect.center

	#----------------------------------------------------------------------
	def GetCharactorSprite(self, charactor):
		#there will be only one
		for s in self.frontSprites:
			return s
		return None

	#----------------------------------------------------------------------
	def GetSectorSprite(self, sector):
		for s in self.backSprites:
			if hasattr(s, "sector") and s.sector == sector:
				return s


	#----------------------------------------------------------------------
	def Notify(self, event):
		if isinstance( event, TickEvent ):
			#Draw Everything
			self.backSprites.clear( self.window, self.background )
			self.frontSprites.clear( self.window, self.background )

			self.backSprites.update()
			self.frontSprites.update()

			dirtyRects1 = self.backSprites.draw( self.window )
			dirtyRects2 = self.frontSprites.draw( self.window )
			
			dirtyRects = dirtyRects1 + dirtyRects2
			pygame.display.update( dirtyRects )


		elif isinstance( event, MapBuiltEvent ):
			gameMap = event.map
			self.ShowMap( gameMap )

		elif isinstance( event, CharactorPlaceEvent ):
			self.ShowCharactor( event.charactor )

		elif isinstance( event, CharactorMoveEvent ):
			self.MoveCharactor( event.charactor )

		elif isinstance( event, GameSyncEvent ):
			print "VIEW gets SYNC event"
			game = event.game
			self.ShowMap( game.map )
			for player in game.players:
				for charactor in player.charactors:
					self.ShowCharactor( charactor )

#------------------------------------------------------------------------------
class Game:
	"""..."""

	STATE_PREPARING = 0
	STATE_RUNNING = 1
	STATE_PAUSED = 2

	#----------------------------------------------------------------------
	def __init__(self, evManager):
		self.evManager = evManager
		self.evManager.RegisterListener( self )

		self.state = Game.STATE_PREPARING
		
		self.players = [ Player(evManager) ]
		self.map = Map( evManager )

	#----------------------------------------------------------------------
	def Start(self):
		self.map.Build()
		self.state = Game.STATE_RUNNING
		ev = GameStartedEvent( self )
		self.evManager.Post( ev )

	#----------------------------------------------------------------------
	def Notify(self, event):
		if isinstance( event, GameStartRequest ):
		        print 'Game object gets game start req'
			if self.state == Game.STATE_PREPARING:
				self.Start()

#------------------------------------------------------------------------------
class Player:
	"""..."""
	def __init__(self, evManager):
		self.evManager = evManager
		#self.evManager.RegisterListener( self )

		self.charactors = [ Charactor(evManager) ]

#------------------------------------------------------------------------------
class Charactor:
	"""..."""

	STATE_INACTIVE = 0
	STATE_ACTIVE = 1

	def __init__(self, evManager):
		self.evManager = evManager
		self.evManager.RegisterListener( self )

		self.sector = None
		self.state = Charactor.STATE_INACTIVE

	#----------------------------------------------------------------------
	def Move(self, direction):
		if self.state == Charactor.STATE_INACTIVE:
			return

		if self.sector.MovePossible( direction ):
			newSector = self.sector.neighbors[direction]
			self.sector = newSector
			ev = CharactorMoveEvent( self )
			self.evManager.Post( ev )

	#----------------------------------------------------------------------
	def Place(self, sector):
		self.sector = sector
		self.state = Charactor.STATE_ACTIVE

		ev = CharactorPlaceEvent( self )
		self.evManager.Post( ev )

	#----------------------------------------------------------------------
	def Notify(self, event):
		if isinstance( event, GameStartedEvent ):
			gameMap = event.game.map
			self.Place( gameMap.sectors[gameMap.startSectorIndex] )

		elif isinstance( event, CharactorMoveRequest ):
			self.Move( event.direction )

#------------------------------------------------------------------------------
class Map:
	"""..."""

	STATE_PREPARING = 0
	STATE_BUILT = 1


	#----------------------------------------------------------------------
	def __init__(self, evManager):
		self.evManager = evManager
		#self.evManager.RegisterListener( self )

		self.state = Map.STATE_PREPARING

		self.sectors = range(9)
		self.startSectorIndex = 0

	#----------------------------------------------------------------------
	def Build(self):
		for i in range(9):
			self.sectors[i] = Sector( self.evManager )

		self.sectors[3].neighbors[DIRECTION_UP] = self.sectors[0]
		self.sectors[4].neighbors[DIRECTION_UP] = self.sectors[1]
		self.sectors[5].neighbors[DIRECTION_UP] = self.sectors[2]
		self.sectors[6].neighbors[DIRECTION_UP] = self.sectors[3]
		self.sectors[7].neighbors[DIRECTION_UP] = self.sectors[4]
		self.sectors[8].neighbors[DIRECTION_UP] = self.sectors[5]

		self.sectors[0].neighbors[DIRECTION_DOWN] = self.sectors[3]
		self.sectors[1].neighbors[DIRECTION_DOWN] = self.sectors[4]
		self.sectors[2].neighbors[DIRECTION_DOWN] = self.sectors[5]
		self.sectors[3].neighbors[DIRECTION_DOWN] = self.sectors[6]
		self.sectors[4].neighbors[DIRECTION_DOWN] = self.sectors[7]
		self.sectors[5].neighbors[DIRECTION_DOWN] = self.sectors[8]

		self.sectors[1].neighbors[DIRECTION_LEFT] = self.sectors[0]
		self.sectors[2].neighbors[DIRECTION_LEFT] = self.sectors[1]
		self.sectors[4].neighbors[DIRECTION_LEFT] = self.sectors[3]
		self.sectors[5].neighbors[DIRECTION_LEFT] = self.sectors[4]
		self.sectors[7].neighbors[DIRECTION_LEFT] = self.sectors[6]
		self.sectors[8].neighbors[DIRECTION_LEFT] = self.sectors[7]

		self.sectors[0].neighbors[DIRECTION_RIGHT] = self.sectors[1]
		self.sectors[1].neighbors[DIRECTION_RIGHT] = self.sectors[2]
		self.sectors[3].neighbors[DIRECTION_RIGHT] = self.sectors[4]
		self.sectors[4].neighbors[DIRECTION_RIGHT] = self.sectors[5]
		self.sectors[6].neighbors[DIRECTION_RIGHT] = self.sectors[7]
		self.sectors[7].neighbors[DIRECTION_RIGHT] = self.sectors[8]

		self.state = Map.STATE_BUILT

		ev = MapBuiltEvent( self )
		self.evManager.Post( ev )

#------------------------------------------------------------------------------
class Sector:
	"""..."""
	def __init__(self, evManager):
		self.evManager = evManager
		#self.evManager.RegisterListener( self )

		self.neighbors = range(4)

		self.neighbors[DIRECTION_UP] = None
		self.neighbors[DIRECTION_DOWN] = None
		self.neighbors[DIRECTION_LEFT] = None
		self.neighbors[DIRECTION_RIGHT] = None

	#----------------------------------------------------------------------
	def MovePossible(self, direction):
		if self.neighbors[direction]:
			return 1


#------------------------------------------------------------------------------
def main():
	"""..."""
	evManager = EventManager()

	keybd = KeyboardController( evManager )
	spinner = CPUSpinnerController( evManager )
	pygameView = PygameView( evManager )
	game = Game( evManager )
	
	spinner.Run()

if __name__ == "__main__":
	main()

########NEW FILE########
__FILENAME__ = network

from example1 import *
from twisted.spread import pb

# A list of ALL possible events that a server can send to a client
serverToClientEvents = []
# A list of ALL possible events that a client can send to a server
clientToServerEvents = []

#------------------------------------------------------------------------------
#Mix-In Helper Functions
#------------------------------------------------------------------------------
def MixInClass( origClass, addClass ):
	if addClass not in origClass.__bases__:
		origClass.__bases__ += (addClass,)

#------------------------------------------------------------------------------
def MixInCopyClasses( someClass ):
	MixInClass( someClass, pb.Copyable )
	MixInClass( someClass, pb.RemoteCopy )




#------------------------------------------------------------------------------
#------------------------------------------------------------------------------
# For each event class, if it is sendable over the network, we have 
# to Mix In the "copy classes", or make a replacement event class that is 
# copyable

#------------------------------------------------------------------------------
# TickEvent
# Direction: don't send.
#The Tick event happens hundreds of times per second.  If we think we need
#to send it over the network, we should REALLY re-evaluate our design

#------------------------------------------------------------------------------
# QuitEvent
# Direction: Client to Server only
MixInCopyClasses( QuitEvent )
pb.setUnjellyableForClass(QuitEvent, QuitEvent)
clientToServerEvents.append( QuitEvent )

#------------------------------------------------------------------------------
# GameStartRequest
# Direction: Client to Server only
MixInCopyClasses( GameStartRequest )
pb.setUnjellyableForClass(GameStartRequest, GameStartRequest)
clientToServerEvents.append( GameStartRequest )

#------------------------------------------------------------------------------
# CharactorMoveRequest
# Direction: Client to Server only
# this has an additional attribute, direction.  it is an int, so it's safe
MixInCopyClasses( CharactorMoveRequest )
pb.setUnjellyableForClass(CharactorMoveRequest, CharactorMoveRequest)
clientToServerEvents.append( CharactorMoveRequest )


#------------------------------------------------------------------------------
# ServerConnectEvent
# Direction: don't send.
# we don't need to send this over the network.

#------------------------------------------------------------------------------
# ClientConnectEvent
# Direction: don't send.
# we don't need to send this over the network.


#------------------------------------------------------------------------------
# GameStartedEvent
# Direction: Server to Client only
class CopyableGameStartedEvent(pb.Copyable, pb.RemoteCopy):
	def __init__(self, event, registry):
		self.name = "Copyable Game Started Event"
		self.gameID = id(event.game)
		registry[self.gameID] = event.game
		#TODO: put this in a Player Join Event or something
		for p in event.game.players:
			registry[id(p)] = p

pb.setUnjellyableForClass(CopyableGameStartedEvent, CopyableGameStartedEvent)
serverToClientEvents.append( CopyableGameStartedEvent )

#------------------------------------------------------------------------------
# MapBuiltEvent
# Direction: Server to Client only
class CopyableMapBuiltEvent( pb.Copyable, pb.RemoteCopy):
	def __init__(self, event, registry ):
		self.name = "Copyable Map Finished Building Event"
		self.mapID = id( event.map )
		registry[self.mapID] = event.map

pb.setUnjellyableForClass(CopyableMapBuiltEvent, CopyableMapBuiltEvent)
serverToClientEvents.append( CopyableMapBuiltEvent )

#------------------------------------------------------------------------------
# CharactorMoveEvent
# Direction: Server to Client only
class CopyableCharactorMoveEvent( pb.Copyable, pb.RemoteCopy):
	def __init__(self, event, registry ):
		self.name = "Copyable Charactor Move Event"
		self.charactorID = id( event.charactor )
		registry[self.charactorID] = event.charactor

pb.setUnjellyableForClass(CopyableCharactorMoveEvent, CopyableCharactorMoveEvent)
serverToClientEvents.append( CopyableCharactorMoveEvent )

#------------------------------------------------------------------------------
# CharactorPlaceEvent
# Direction: Server to Client only
class CopyableCharactorPlaceEvent( pb.Copyable, pb.RemoteCopy):
	def __init__(self, event, registry ):
		self.name = "Copyable Charactor Placement Event"
		self.charactorID = id( event.charactor )
		registry[self.charactorID] = event.charactor

pb.setUnjellyableForClass(CopyableCharactorPlaceEvent, CopyableCharactorPlaceEvent)
serverToClientEvents.append( CopyableCharactorPlaceEvent )



#------------------------------------------------------------------------------
class CopyableCharactor:
	def getStateToCopy(self, registry):
		d = self.__dict__.copy()
		del d['evManager']

		sID = id( self.sector )
		d['sector'] = sID
		registry[sID] = self.sector

		return d

	def setCopyableState(self, stateDict, registry):
		neededObjIDs = []
		success = 1
		if stateDict['sector'] not in registry:
			registry[stateDict['sector']] = Sector(self.evManager)
			neededObjIDs.append( stateDict['sector'] )
			success = 0
		else:
			self.sector = registry[stateDict['sector']]
		return [success, neededObjIDs]


MixInClass( Charactor, CopyableCharactor )

#------------------------------------------------------------------------------
class CopyableMap:
	def getStateToCopy(self, registry):
		sectorIDList = []
		for sect in self.sectors:
			sID = id(sect)
			sectorIDList.append( sID )
			registry[sID] = sect

		return {'ninegrid':1, 'sectorIDList':sectorIDList}


	def setCopyableState(self, stateDict, registry):
		neededObjIDs = []
		success = 1

		if self.state != Map.STATE_BUILT:
			self.Build()

		for i, sectID in enumerate(stateDict['sectorIDList']):
			registry[sectID] = self.sectors[i]

		return [success, neededObjIDs]

MixInClass( Map, CopyableMap )

#------------------------------------------------------------------------------
class CopyableGame:
	def getStateToCopy(self, registry):
		d = self.__dict__.copy()
		del d['evManager']

		mID = id( self.map )
		d['map'] = mID
		registry[mID] = self.map

		playerIDList = []
		for player in self.players:
			pID = id( player )
			playerIDList.append( pID )
			registry[pID] = player
		d['players'] = playerIDList

		return d

	def setCopyableState(self, stateDict, registry):
		neededObjIDs = []
		success = 1

		if stateDict['map'] not in registry:
			registry[stateDict['map']] = Map( self.evManager )
			neededObjIDs.append( stateDict['map'] )
			success = 0
		else:
			self.map = registry[stateDict['map']]

		for pID in stateDict['players']:
			if pID not in registry:
				registry[pID] = Player( self.evManager )
				neededObjIDs.append( pID )
				success = 0
			else:
				self.players.append( registry[pID] )

		return [success, neededObjIDs]

MixInClass( Game, CopyableGame )

#------------------------------------------------------------------------------
class CopyablePlayer:
	def getStateToCopy(self, registry):
		d = self.__dict__.copy()
		del d['evManager']

		charactorIDList = []
		for charactor in self.charactors:
			cID = id( charactor )
			charactorIDList.append( cID )
			registry[cID] = charactor
		d['charactors'] = charactorIDList

		return d

	def setCopyableState(self, stateDict, registry):
		neededObjIDs = []
		success = 1

		for cID in stateDict['charactors']:
			if not cID in registry:
				registry[cID] = Charactor( self.evManager )
				neededObjIDs.append( cID )
				success = 0
			else:
				self.charactors.append( registry[cID] )

		return [success, neededObjIDs]

MixInClass( Player, CopyablePlayer )

########NEW FILE########
__FILENAME__ = server
#! /usr/bin/env python
'''
Example server
'''

from twisted.spread import pb
from twisted.spread.pb import DeadReferenceError
from example1 import EventManager, Game
from events import *
import network

#------------------------------------------------------------------------------
class NoTickEventManager(EventManager):
	'''This subclass of EventManager doesn't wait for a Tick event before
	it starts consuming its event queue.  The server module doesn't have
	a CPUSpinnerController, so Ticks will not get generated.
	'''
	def __init__(self):
		EventManager.__init__(self)
		self._lock = False
	def Post(self, event):
		self.eventQueue.append(event)
		if not self._lock:
			self._lock = True
			self.ActuallyUpdateListeners()
			self.ConsumeEventQueue()
			self._lock = False



#------------------------------------------------------------------------------
class TimerController:
	"""A controller that sends of an event every second"""
	def __init__(self, evManager, reactor):
		self.evManager = evManager
		self.evManager.RegisterListener( self )

		self.reactor = reactor
		self.numClients = 0

	#-----------------------------------------------------------------------
	def NotifyApplicationStarted( self ):
		self.reactor.callLater( 1, self.Tick )

	#-----------------------------------------------------------------------
	def Tick(self):
		if self.numClients == 0:
			return

		ev = SecondEvent()
		self.evManager.Post( ev )
		ev = TickEvent()
		self.evManager.Post( ev )
		self.reactor.callLater( 1, self.Tick )

	#----------------------------------------------------------------------
	def Notify(self, event):
		if isinstance( event, ClientConnectEvent ):
			self.numClients += 1
			if self.numClients == 1:
				self.Tick()
		if isinstance( event, ClientDisconnectEvent ):
			self.numClients -= 1

#------------------------------------------------------------------------------
class NetworkClientController(pb.Root):
	"""We RECEIVE events from the CLIENT through this object"""
	def __init__(self, evManager, sharedObjectRegistry):
		self.evManager = evManager
		self.evManager.RegisterListener( self )
		self.sharedObjs = sharedObjectRegistry

		#this is needed for GetEntireState()
		self.game = None

	#----------------------------------------------------------------------
	def remote_ClientConnect(self, netClient):
		print "\nremote_CLIENT CONNECT"
		ev = ClientConnectEvent( netClient )
		self.evManager.Post( ev )
		if self.game == None:
			gameID = 0
		else:
			gameID = id(self.game)
		return gameID

	#----------------------------------------------------------------------
	def remote_GetGame(self):
		"""this is usually called when a client first connects or
		when they had dropped and reconnect"""
		if self.game == None:
			return [0,0]
		gameID = id( self.game )
		gameDict = self.game.getStateToCopy( self.sharedObjs )

		print "returning: ", gameID
		return [gameID, gameDict]
	
	#----------------------------------------------------------------------
	def remote_GetObjectState(self, objectID):
		#print "request for object state", objectID
		if not self.sharedObjs.has_key( objectID ):
			return [0,0]
		obj = self.sharedObjs[objectID]
		objDict = obj.getStateToCopy( self.sharedObjs )

		return [objectID, objDict]
	
	#----------------------------------------------------------------------
	def remote_EventOverNetwork(self, event):
		#print "Server just got an EVENT" + str(event)
		self.evManager.Post( event )
		return 1

	#----------------------------------------------------------------------
	def Notify(self, event):
		if isinstance( event, GameStartedEvent ):
			self.game = event.game


#------------------------------------------------------------------------------
class TextLogView(object):
	def __init__(self, evManager):
		self.evManager = evManager
		self.evManager.RegisterListener( self )

	#----------------------------------------------------------------------
	def Notify(self, event):
		if isinstance( event, TickEvent ):
			return

		print 'TEXTLOG <',
		
		if isinstance( event, CharactorPlaceEvent ):
			print event.name, " at ", event.charactor.sector

		elif isinstance( event, CharactorMoveEvent ):
			print event.name, " to ", event.charactor.sector
		else:
			print 'event:', event


#------------------------------------------------------------------------------
class NetworkClientView(object):
	"""We SEND events to the CLIENT through this object"""
	def __init__(self, evManager, sharedObjectRegistry):
		self.evManager = evManager
		self.evManager.RegisterListener( self )

		self.clients = []
		self.sharedObjs = sharedObjectRegistry
		#TODO:
		#every 5 seconds, the server should poll the clients to see if
		# they're still connected
		self.pollSeconds = 0

	#----------------------------------------------------------------------
	def Pong(self ):
		pass

	#----------------------------------------------------------------------
	def RemoteCallError(self, failure, client):
		from twisted.internet.error import ConnectionLost
		#trap ensures that the rest will happen only 
		#if the failure was ConnectionLost
		failure.trap(ConnectionLost)
		self.DisconnectClient(client)
		return failure

	#----------------------------------------------------------------------
	def DisconnectClient(self, client):
		print "Disconnecting Client", client
		self.clients.remove( client )
		ev = ClientDisconnectEvent( client ) #client id in here
		self.evManager.Post( ev )

	#----------------------------------------------------------------------
	def RemoteCall( self, client, fnName, *args):

		try:
			remoteCall = client.callRemote(fnName, *args)
			#remoteCall.addCallback( self.Pong )
			remoteCall.addErrback( self.RemoteCallError, client )
		except DeadReferenceError:
			self.DisconnectClient(client)


	#----------------------------------------------------------------------
	def Notify(self, event):
		if isinstance( event, ClientConnectEvent ):
			print "\nADDING CLIENT", event.client
			self.clients.append( event.client )
			#TODO tell the client what it's ID is

		if isinstance( event, SecondEvent ):
			self.pollSeconds +=1
			if self.pollSeconds == 10:
				self.pollSeconds = 0
				for client in self.clients:
					self.RemoteCall( client, "Ping" )


		ev = event

		#don't broadcast events that aren't Copyable
		if not isinstance( ev, pb.Copyable ):
			evName = ev.__class__.__name__
			copyableClsName = "Copyable"+evName
			if not hasattr( network, copyableClsName ):
				return
			copyableClass = getattr( network, copyableClsName )
			ev = copyableClass( ev, self.sharedObjs )

		if ev.__class__ not in network.serverToClientEvents:
			#print "SERVER NOT SENDING: " +str(ev)
			return

		#NOTE: this is very "chatty".  We could restrict 
		#      the number of clients notified in the future
		for client in self.clients:
			print "\n====server===sending: ", str(ev), 'to', client
			self.RemoteCall( client, "ServerEvent", ev )



		
#------------------------------------------------------------------------------
def main():
	from twisted.internet import reactor
	evManager = NoTickEventManager()
	sharedObjectRegistry = {}

	log = TextLogView( evManager )
	timer = TimerController( evManager, reactor )
	clientController = NetworkClientController( evManager, sharedObjectRegistry )
	clientView = NetworkClientView( evManager, sharedObjectRegistry )
	game = Game( evManager )

	reactor.listenTCP( 8000, pb.PBServerFactory(clientController) )

	reactor.run()

if __name__ == "__main__":
	main()

########NEW FILE########
__FILENAME__ = client
import sys
import time
import network
from twisted.spread import pb
from twisted.internet.selectreactor import SelectReactor
from twisted.internet.main import installReactor
from twisted.cred import credentials
from events import *
from example1 import (EventManager,
                      Game,
                      Player,
                      KeyboardController,
                      CPUSpinnerController,
                      PygameView)

serverHost, serverPort = 'localhost', 8000
avatarID = None

#------------------------------------------------------------------------------
class NetworkServerView(pb.Root):
    """We SEND events to the server through this object"""
    STATE_PREPARING = 0
    STATE_CONNECTING = 1
    STATE_CONNECTED = 2
    STATE_DISCONNECTING = 3
    STATE_DISCONNECTED = 4

    #----------------------------------------------------------------------
    def __init__(self, evManager, sharedObjectRegistry):
            self.evManager = evManager
            self.evManager.RegisterListener( self )

            self.pbClientFactory = pb.PBClientFactory()
            self.state = NetworkServerView.STATE_PREPARING
            self.reactor = None
            self.server = None

            self.sharedObjs = sharedObjectRegistry

    #----------------------------------------------------------------------
    def AttemptConnection(self):
            print "attempting a connection to", serverHost, serverPort
            self.state = NetworkServerView.STATE_CONNECTING
            if self.reactor:
                    self.reactor.stop()
                    self.PumpReactor()
            else:
                    self.reactor = SelectReactor()
                    installReactor(self.reactor)
            connection = self.reactor.connectTCP(serverHost, serverPort,
                                                 self.pbClientFactory)
            # TODO: make this anonymous login()
            #deferred = self.pbClientFactory.login(credentials.Anonymous())
            userCred = credentials.UsernamePassword(avatarID, 'pass1')
            controller = NetworkServerController( self.evManager )
            deferred = self.pbClientFactory.login(userCred, client=controller)
            deferred.addCallback(self.Connected)
            deferred.addErrback(self.ConnectFailed)
            self.reactor.startRunning()

    #----------------------------------------------------------------------
    def Disconnect(self):
            print "disconnecting"
            if not self.reactor:
                    return
            print 'stopping the reactor'
            self.reactor.stop()
            self.PumpReactor()
            self.state = NetworkServerView.STATE_DISCONNECTING

    #----------------------------------------------------------------------
    def Connected(self, server):
            print "CONNECTED"
            self.server = server
            self.state = NetworkServerView.STATE_CONNECTED
            ev = ServerConnectEvent( server )
            self.evManager.Post( ev )

    #----------------------------------------------------------------------
    def ConnectFailed(self, server):
            print "CONNECTION FAILED"
            print server
            print 'quitting'
            self.evManager.Post( QuitEvent() )
            #self.state = NetworkServerView.STATE_PREPARING
            self.state = NetworkServerView.STATE_DISCONNECTED

    #----------------------------------------------------------------------
    def PumpReactor(self):
            self.reactor.runUntilCurrent()
            self.reactor.doIteration(0)

    #----------------------------------------------------------------------
    def Notify(self, event):
            NSV = NetworkServerView
            if isinstance( event, TickEvent ):
                    if self.state == NSV.STATE_PREPARING:
                            self.AttemptConnection()
                    elif self.state in [NSV.STATE_CONNECTED,
                                        NSV.STATE_DISCONNECTING,
                                        NSV.STATE_CONNECTING]:
                            self.PumpReactor()
                    return

            if isinstance( event, QuitEvent ):
                    self.Disconnect()
                    return

            ev = event
            if not isinstance( event, pb.Copyable ):
                    evName = event.__class__.__name__
                    copyableClsName = "Copyable"+evName
                    if not hasattr( network, copyableClsName ):
                            return
                    copyableClass = getattr( network, copyableClsName )
                    #NOTE, never even construct an instance of an event that
                    # is serverToClient, as a side effect is often adding a
                    # key to the registry with the local id().
                    if copyableClass not in network.clientToServerEvents:
                        return
                    #print 'creating instance of copyable class', copyableClsName
                    ev = copyableClass( event, self.sharedObjs )

            if ev.__class__ not in network.clientToServerEvents:
                    #print "CLIENT NOT SENDING: " +str(ev)
                    return
                    
            if self.server:
                    print " ====   Client sending", str(ev)
                    remoteCall = self.server.callRemote("EventOverNetwork", ev)
            else:
                    print " =--= Cannot send while disconnected:", str(ev)


#------------------------------------------------------------------------------
class NetworkServerController(pb.Referenceable):
    """We RECEIVE events from the server through this object"""
    def __init__(self, evManager):
        self.evManager = evManager
        self.evManager.RegisterListener( self )

    #----------------------------------------------------------------------
    def remote_ServerEvent(self, event):
        print " ====  GOT AN EVENT FROM SERVER:", str(event)
        self.evManager.Post( event )
        return 1

    #----------------------------------------------------------------------
    def Notify(self, event):
        pass
        #if isinstance( event, ServerConnectEvent ):
            ##tell the server that we're listening to it and
            ##it can access this object
            #defrd = event.server.callRemote("ClientConnect", self)
            #defrd.addErrback(self.ServerErrorHandler)

    #----------------------------------------------------------------------
    def ServerErrorHandler(self, *args):
        print '\n **** ERROR REPORT **** '
        print 'Server threw us an error.  Args:', args
        ev = network.ServerErrorEvent()
        self.evManager.Post(ev)
        print ' ^*** ERROR REPORT ***^ \n'


#------------------------------------------------------------------------------
class PhonyEventManager(EventManager):
    """this object is responsible for coordinating most communication
    between the Model, View, and Controller."""
    #----------------------------------------------------------------------
    def Post( self, event ):
        pass

#------------------------------------------------------------------------------
class PhonyModel:
    '''This isn't the authouritative model.  That one exists on the
    server.  This is a model to store local state and to interact with
    the local EventManager.
    '''

    #----------------------------------------------------------------------
    def __init__(self, evManager, sharedObjectRegistry):
            self.sharedObjs = sharedObjectRegistry
            self.game = None
            self.server = None
            self.phonyEvManager = PhonyEventManager()
            self.realEvManager = evManager
            self.neededObjects = []
            self.waitingObjectStack = []

            self.realEvManager.RegisterListener( self )

    #----------------------------------------------------------------------
    def GameSyncReturned(self, response):
            gameID, gameDict = response
            print "GameSyncReturned : ", gameID
            self.sharedObjs[gameID] = self.game
            # StateReturned returns a deferred, pass it on to keep the
            # chain going.
            return self.StateReturned( response )

    #----------------------------------------------------------------------
    def StateReturned(self, response):
            """this is a callback that is called in response to
            invoking GetObjectState on the server"""

            #print "looking for ", response
            objID, objDict = response
            if objID == 0:
                    print "GOT ZERO -- TODO: better error handler here"
                    return None
            obj = self.sharedObjs[objID]

            success, neededObjIDs =\
                             obj.setCopyableState(objDict, self.sharedObjs)
            if success:
                    #we successfully set the state and no further objects
                    #are needed to complete the current object
                    if objID in self.neededObjects:
                            self.neededObjects.remove(objID)

            else:
                    #to complete the current object, we need to grab the
                    #state from some more objects on the server.  The IDs
                    #for those needed objects were passed back 
                    #in neededObjIDs
                    for neededObjID in neededObjIDs:
                            if neededObjID not in self.neededObjects:
                                    self.neededObjects.append(neededObjID)
                    print "failed.  still need ", self.neededObjects
    
            self.waitingObjectStack.append( (obj, objDict) )

            retval = self.GetAllNeededObjects()
            if retval:
                    # retval is a Deferred - returning it causes a chain
                    # to be formed.  The original deferred must wait for
                    # this new one to return before it calls its next
                    # callback
                    return retval
    
    #----------------------------------------------------------------------
    def GetAllNeededObjects(self):
            if len(self.neededObjects) == 0:
                    # this is the recursion-ending condition.  If there are
                    # no more objects needed to be grabbed from the server
                    # then we can try to setCopyableState on them again and
                    # we should now have all the needed objects, ensuring
                    # that setCopyableState succeeds
                    return self.ConsumeWaitingObjectStack()

            # still in the recursion step.  Try to get the object state for
            # the objectID on the top of the stack.  Note that the 
            # recursion is done via a deferred, which may be confusing
            nextID = self.neededObjects[-1]
            print "next one to grab: ", nextID
            remoteResponse = self.server.callRemote("GetObjectState",nextID)
            remoteResponse.addCallback(self.StateReturned)
            remoteResponse.addErrback(self.ServerErrorHandler, 'allNeededObjs')
            return remoteResponse

    #----------------------------------------------------------------------
    def ConsumeWaitingObjectStack(self):
        # All the needed objects should be present now.  Just the
        # matter of setting the state on the waiting objects remains.
        while self.waitingObjectStack:
            obj, objDict = self.waitingObjectStack.pop()
            success, neededObjIDs =\
                                 obj.setCopyableState(objDict, self.sharedObjs)
            if not success:
                print "WEIRD!!!!!!!!!!!!!!!!!!"

    #----------------------------------------------------------------------
    def Notify(self, event):
        if isinstance( event, ServerConnectEvent ):
            self.server = event.server
            #when we connect to the server, we should get the
            #entire game state.  this also applies to RE-connecting
            if not self.game:
                self.game = Game( self.phonyEvManager )
                gameID = id(self.game)
                self.sharedObjs[gameID] = self.game
            remoteResponse = self.server.callRemote("GetGameSync")
            remoteResponse.addCallback(self.GameSyncReturned)
            remoteResponse.addCallback(self.GameSyncCallback, gameID)
            remoteResponse.addErrback(self.ServerErrorHandler, 'ServerConnect')


        elif isinstance( event, network.CopyableGameStartedEvent ):
            gameID = event.gameID
            if not self.game:
                self.game = Game( self.phonyEvManager )
            self.sharedObjs[gameID] = self.game
            ev = GameStartedEvent( self.game )
            self.realEvManager.Post( ev )

        elif isinstance( event, network.ServerErrorEvent ):
            from pprint import pprint
            print 'Client state at the time of server error:'
            pprint(self.sharedObjs)

        if isinstance( event, network.CopyableMapBuiltEvent ):
            mapID = event.mapID
            if not self.sharedObjs.has_key(mapID):
                self.sharedObjs[mapID] = self.game.map
            remoteResponse = self.server.callRemote("GetObjectState", mapID)
            remoteResponse.addCallback(self.StateReturned)
            remoteResponse.addCallback(self.MapBuiltCallback, mapID)
            remoteResponse.addErrback(self.ServerErrorHandler, 'MapBuilt')

        if isinstance( event, network.CopyablePlayerJoinEvent ):
            playerID = event.playerID
            if not self.sharedObjs.has_key(playerID):
                player = Player( self.phonyEvManager )
                self.sharedObjs[playerID] = player
            remoteResponse = self.server.callRemote("GetObjectState", playerID)
            remoteResponse.addCallback(self.StateReturned)
            remoteResponse.addCallback(self.PlayerJoinCallback, playerID)
            remoteResponse.addErrback(self.ServerErrorHandler, 'PlayerJoin')

        if isinstance( event, network.CopyableCharactorPlaceEvent ):
            charactorID = event.charactorID
            if not self.sharedObjs.has_key(charactorID):
                charactor = self.game.players[0].charactors[0]
                self.sharedObjs[charactorID] = charactor
            remoteResponse = self.server.callRemote("GetObjectState", charactorID)
            remoteResponse.addCallback(self.StateReturned)
            remoteResponse.addCallback(self.CharactorPlaceCallback, charactorID)
            remoteResponse.addErrback(self.ServerErrorHandler, 'CharPlace')

        if isinstance( event, network.CopyableCharactorMoveEvent ):
            charactorID = event.charactorID
            if not self.sharedObjs.has_key(charactorID):
                charactor = self.game.players[0].charactors[0]
                self.sharedObjs[charactorID] = charactor
            remoteResponse = self.server.callRemote("GetObjectState", charactorID)
            remoteResponse.addCallback(self.StateReturned)
            remoteResponse.addCallback(self.CharactorMoveCallback, charactorID)
            remoteResponse.addErrback(self.ServerErrorHandler, 'CharMove')

    #----------------------------------------------------------------------
    def CharactorPlaceCallback(self, deferredResult, charactorID):
        charactor = self.sharedObjs[charactorID]
        ev = CharactorPlaceEvent( charactor )
        self.realEvManager.Post( ev )
    #----------------------------------------------------------------------
    def MapBuiltCallback(self, deferredResult, mapID):
        gameMap = self.sharedObjs[mapID]
        ev = MapBuiltEvent( gameMap )
        self.realEvManager.Post( ev )
    #----------------------------------------------------------------------
    def CharactorMoveCallback(self, deferredResult, charactorID):
        charactor = self.sharedObjs[charactorID]
        ev = CharactorMoveEvent( charactor )
        self.realEvManager.Post( ev )
    #----------------------------------------------------------------------
    def GameSyncCallback(self, deferredResult, gameID):
        game = self.sharedObjs[gameID]
        ev = GameSyncEvent( game )
        self.realEvManager.Post( ev )
    #----------------------------------------------------------------------
    def PlayerJoinCallback(self, deferredResult, playerID):
        player = self.sharedObjs[playerID]
        self.game.AddPlayer( player )
        ev = PlayerJoinEvent( player )
        self.realEvManager.Post( ev )
    #----------------------------------------------------------------------
    def ServerErrorHandler(self, failure, *args):
        print '\n **** ERROR REPORT **** '
        print 'Server threw PhonyModel an error.  failure:', failure
        print 'failure traceback:', failure.getTraceback()
        print 'Server threw PhonyModel an error.  Args:', args
        ev = network.ServerErrorEvent()
        self.realEvManager.Post(ev)
        print ' ^*** ERROR REPORT ***^ \n'


#class DebugDict(dict):
    #def __setitem__(self, *args):
        #print ''
        #print '        set item', args
        #return dict.__setitem__(self, *args)

#------------------------------------------------------------------------------
def main():
    global avatarID
    if len(sys.argv) > 1:
        avatarID = sys.argv[1]
    else:
        print 'You should provide a username on the command line'
        print 'Defaulting to username "user1"'
        time.sleep(1)
        avatarID = 'user1'
        
    evManager = EventManager()
    sharedObjectRegistry = {}
    #sharedObjectRegistry = DebugDict()
    keybd = KeyboardController( evManager, playerName=avatarID )
    spinner = CPUSpinnerController( evManager )
    pygameView = PygameView( evManager )

    phonyModel = PhonyModel( evManager, sharedObjectRegistry  )

    serverView = NetworkServerView( evManager, sharedObjectRegistry )
    
    try:
        spinner.Run()
    except Exception, ex:
        print 'got exception (%s)' % ex, 'killing reactor'
        import logging
        logging.basicConfig()
        logging.exception(ex)
        serverView.Disconnect()


if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = events
#SECURITY NOTE: anything in here can be created simply by sending the 
# class name over the network.  This is a potential vulnerability
# I wouldn't suggest letting any of these classes DO anything, especially
# things like file system access, or allocating huge amounts of memory

class Event:
	"""this is a superclass for any events that might be generated by an
	object and sent to the EventManager"""
	def __init__(self):
		self.name = "Generic Event"
	def __str__(self):
		return '<%s %s>' % (self.__class__.__name__,
		                    id(self))
	    

class TickEvent(Event):
	def __init__(self):
		self.name = "CPU Tick Event"

class SecondEvent(Event):
	def __init__(self):
		self.name = "Clock One Second Event"

class QuitEvent(Event):
	def __init__(self):
		self.name = "Program Quit Event"

class FatalEvent(Event):
	def __init__(self, *args):
		self.name = "Fatal Error Event"
		self.args = args

class MapBuiltEvent(Event):
	def __init__(self, map):
		self.name = "Map Finished Building Event"
		self.map = map

class GameStartRequest(Event):
	def __init__(self):
		self.name = "Game Start Request"

class GameStartedEvent(Event):
	def __init__(self, game):
		self.name = "Game Started Event"
		self.game = game

class CharactorMoveRequest(Event):
	def __init__(self, player, charactor, direction):
		self.name = "Charactor Move Request"
		self.player = player
		self.charactor = charactor
		self.direction = direction

class CharactorMoveEvent(Event):
	def __init__(self, charactor):
		self.name = "Charactor Move Event"
		self.charactor = charactor

class CharactorPlaceEvent(Event):
	"""this event occurs when a Charactor is *placed* in a sector, 
	ie it doesn't move there from an adjacent sector."""
	def __init__(self, charactor):
		self.name = "Charactor Placement Event"
		self.charactor = charactor

class ServerConnectEvent(Event):
	"""the client generates this when it detects that it has successfully
	connected to the server"""
	def __init__(self, serverReference):
		self.name = "Network Server Connection Event"
		self.server = serverReference

class ClientConnectEvent(Event):
	"""this event is generated by the Server whenever a client connects
	to it"""
	def __init__(self, client, avatarID):
		self.name = "Network Client Connection Event"
		self.client = client
		self.avatarID = avatarID

class ClientDisconnectEvent(Event):
	"""this event is generated by the Server when it finds that a client 
	is no longer connected"""
	def __init__(self, avatarID):
		self.name = "Network Client Disconnection Event"
		self.avatarID = avatarID

class GameSyncEvent(Event):
	"""..."""
	def __init__(self, game):
		self.name = "Game Synched to Authoritative State"
		self.game = game

class PlayerJoinRequest(Event):
	"""..."""
	def __init__(self, playerDict):
		self.name = "Player Joining Game Request"
		self.playerDict = playerDict

class PlayerJoinEvent(Event):
	"""..."""
	def __init__(self, player):
		self.name = "Player Joined Game Event"
		self.player = player

class CharactorPlaceRequest(Event):
	"""..."""
	def __init__(self, player, charactor, sector):
		self.name = "Charactor Placement Request"
		self.player = player
		self.charactor = charactor
		self.sector = sector

########NEW FILE########
__FILENAME__ = example1
def Debug( msg ):
	print msg

DIRECTION_UP = 0
DIRECTION_DOWN = 1
DIRECTION_LEFT = 2
DIRECTION_RIGHT = 3

from events import *

#------------------------------------------------------------------------------
class EventManager:
	"""this object is responsible for coordinating most communication
	between the Model, View, and Controller."""
	def __init__(self):
		from weakref import WeakKeyDictionary
		self.listeners = WeakKeyDictionary()
		self.eventQueue= []
		self.listenersToAdd = []
		self.listenersToRemove = []

	#----------------------------------------------------------------------
	def RegisterListener( self, listener ):
		self.listenersToAdd.append(listener)

	#----------------------------------------------------------------------
	def ActuallyUpdateListeners(self):
		for listener in self.listenersToAdd:
			self.listeners[ listener ] = 1
		for listener in self.listenersToRemove:
			if listener in self.listeners:
				del self.listeners[ listener ]

	#----------------------------------------------------------------------
	def UnregisterListener( self, listener ):
		self.listenersToRemove.append(listener)
		
	#----------------------------------------------------------------------
	def Post( self, event ):
		self.eventQueue.append(event)
		if isinstance(event, TickEvent):
			# Consume the event queue every Tick.
			self.ActuallyUpdateListeners()
			self.ConsumeEventQueue()
		else:
			Debug( "     Message: " + event.name )

	#----------------------------------------------------------------------
	def ConsumeEventQueue(self):
		i = 0
		while i < len( self.eventQueue ):
			event = self.eventQueue[i]
			for listener in self.listeners:
				# Note: a side effect of notifying the listener
				# could be that more events are put on the queue
				# or listeners could Register / Unregister
				old = len(self.eventQueue)
				listener.Notify( event )
			i += 1
			if self.listenersToAdd:
				self.ActuallyUpdateListeners()
		#all code paths that could possibly add more events to 
		# the eventQueue have been exhausted at this point, so 
		# it's safe to empty the queue
		self.eventQueue= []


#------------------------------------------------------------------------------
class KeyboardController:
	"""KeyboardController takes Pygame events generated by the
	keyboard and uses them to control the model, by sending Requests
	or to control the Pygame display directly, as with the QuitEvent
	"""
	def __init__(self, evManager, playerName=None):
		'''playerName is an optional argument; when given, this
		keyboardController will control only the specified player
		'''
		self.evManager = evManager
		self.evManager.RegisterListener( self )

		self.activePlayer = None
		self.playerName = playerName
		self.players = []

	#----------------------------------------------------------------------
	def Notify(self, event):
		if isinstance( event, PlayerJoinEvent ):
			self.players.append( event.player )
			if event.player.name == self.playerName:
				self.activePlayer = event.player
			if not self.playerName and not self.activePlayer:
				self.activePlayer = event.player

		if isinstance( event, GameSyncEvent ):
			game = event.game
			self.players = game.players[:] # copy the list
			if self.playerName and self.players:
				self.activePlayer = [p for p in self.players
				              if p.name == self.playerName][0]

		if isinstance( event, TickEvent ):
			#Handle Input Events
			for event in pygame.event.get():
				ev = None
				if event.type == QUIT:
					ev = QuitEvent()
				elif event.type == KEYDOWN \
				     and event.key == K_ESCAPE:
					ev = QuitEvent()
				elif event.type == KEYDOWN \
				     and event.key == K_p:
					import random
					rng = random.Random()
					name = str( rng.randrange(1,100) )
					if self.playerName:
						name = self.playerName
					playerData = {'name':name}
					ev = PlayerJoinRequest(playerData)

				elif event.type == KEYDOWN \
				     and event.key == K_o:
					self.activePlayer = self.players[1]
					self.players.reverse()

				elif event.type == KEYDOWN \
				     and event.key == K_c:
					if not self.activePlayer:
						continue
					charactor, sector = self.activePlayer.GetPlaceData()
					ev = CharactorPlaceRequest( 
					  self.activePlayer, 
					  charactor,
					  sector )

				elif event.type == KEYDOWN \
				     and event.key == K_UP:
					if not self.activePlayer:
						continue
					direction = DIRECTION_UP
					data = self.activePlayer.GetMoveData()
					ev = CharactorMoveRequest( 
					  self.activePlayer, 
					  data[0], 
					  direction )

				elif event.type == KEYDOWN \
				     and event.key == K_DOWN:
					if not self.activePlayer:
						continue
					direction = DIRECTION_DOWN
					data = self.activePlayer.GetMoveData()
					ev = CharactorMoveRequest( 
					  self.activePlayer, 
					  data[0], 
					  direction )

				elif event.type == KEYDOWN \
				     and event.key == K_LEFT:
					if not self.activePlayer:
						continue
					direction = DIRECTION_LEFT
					data = self.activePlayer.GetMoveData()
					ev = CharactorMoveRequest( 
					  self.activePlayer, 
					  data[0], 
					  direction )

				elif event.type == KEYDOWN \
				     and event.key == K_RIGHT:
					if not self.activePlayer:
						continue
					direction = DIRECTION_RIGHT
					data = self.activePlayer.GetMoveData()
					ev = CharactorMoveRequest( 
					  self.activePlayer, 
					  data[0], 
					  direction )

				elif event.type == KEYDOWN:
					ev = GameStartRequest()

				if ev:
					self.evManager.Post( ev )


#------------------------------------------------------------------------------
class CPUSpinnerController:
	"""..."""
	def __init__(self, evManager):
		self.evManager = evManager
		self.evManager.RegisterListener( self )

		self.keepGoing = 1

	#----------------------------------------------------------------------
	def Run(self):
		while self.keepGoing:
			event = TickEvent()
			self.evManager.Post( event )

	#----------------------------------------------------------------------
	def Notify(self, event):
		if isinstance( event, QuitEvent ):
			#this will stop the while loop from running
			self.keepGoing = False


import pygame
from pygame.locals import *

#------------------------------------------------------------------------------
class StatusBarSprite(pygame.sprite.Sprite):
	def __init__(self, evManager, group=None):
		pygame.sprite.Sprite.__init__(self, group)

		self.evManager = evManager
		self.evManager.RegisterListener( self )

		self.font = pygame.font.Font(None, 30)
		self.text = '.'
		self.image = self.font.render( self.text, 1, (255,0,0))
		self.rect  = self.image.get_rect()
		self.rect.move_ip( (0, 414) )

	#----------------------------------------------------------------------
	def update(self):
		self.image = self.font.render( self.text, 1, (255,0,0))
		self.rect  = self.image.get_rect()
		self.rect.move_ip( (0, 414) )

	#----------------------------------------------------------------------
	def Notify(self, event):
		if not isinstance( event, TickEvent ):
			self.text = event.name

#------------------------------------------------------------------------------
class SectorSprite(pygame.sprite.Sprite):
	def __init__(self, sector, group=None):
		pygame.sprite.Sprite.__init__(self, group)
		self.image = pygame.Surface( (128,128) )
		self.image.fill( (0,255,128) )

		self.sector = sector

#------------------------------------------------------------------------------
class CharactorSprite(pygame.sprite.Sprite):
	counter = 0
	def __init__(self, charactor, group=None, color=(0,0,0)):
		pygame.sprite.Sprite.__init__(self, group)

		charactorSurf = pygame.Surface( (64,64) )
		charactorSurf = charactorSurf.convert_alpha()
		charactorSurf.fill((0,0,0,0)) #make transparent
		pygame.draw.circle( charactorSurf, color, (32,32), 32 )
		self.image = charactorSurf
		self.rect  = charactorSurf.get_rect()

		self.order = CharactorSprite.counter
		CharactorSprite.counter += 1

		self.charactor = charactor
		self.moveTo = None

	#----------------------------------------------------------------------
	def update(self):
		if self.moveTo:
			self.rect.center = self.moveTo
			self.moveTo = None
			# offset the rect so that charactors don't draw exactly on
			# top of each other.
			self.rect.move_ip(self.order, self.order)

#------------------------------------------------------------------------------
class PygameView:
	def __init__(self, evManager):
		self.evManager = evManager
		self.evManager.RegisterListener( self )

		self.charactorColors = [ (255,0,0), (0,0,255) ]

		pygame.init()
		self.window = pygame.display.set_mode( (424,440) )
		pygame.display.set_caption( 'Example Game' )
		self.background = pygame.Surface( self.window.get_size() )
		self.background.fill( (0,0,0) )

		font = pygame.font.Font(None, 30)
		text = """Press SPACE BAR to start"""
		textImg = font.render( text, 1, (255,0,0))
		self.background.blit( textImg, (0,0) )
		text = """      P for new player"""
		textImg = font.render( text, 1, (255,0,0))
		self.background.blit( textImg, (0,1*font.get_linesize()) )
		text = """      C for new charactor"""
		textImg = font.render( text, 1, (255,0,0))
		self.background.blit( textImg, (0,2*font.get_linesize()) )
		text = """      O to switch players"""
		textImg = font.render( text, 1, (255,0,0))
		self.background.blit( textImg, (0,3*font.get_linesize()) )

		self.window.blit( self.background, (0,0) )
		pygame.display.flip()

		self.backSprites = pygame.sprite.RenderUpdates()
		self.frontSprites = pygame.sprite.RenderUpdates()


	#----------------------------------------------------------------------
	def ShowMap(self, gameMap):
		# clear the screen first
		self.background.fill( (0,0,0) )
		self.window.blit( self.background, (0,0) )
		pygame.display.flip()

		# use this squareRect as a cursor and go through the
		# columns and rows and assign the rect 
		# positions of the SectorSprites
		squareRect = pygame.Rect( (-128,10, 128,128 ) )

		column = 0
		for sector in gameMap.sectors:
			if column < 3:
				squareRect = squareRect.move( 138,0 )
			else:
				column = 0
				squareRect = squareRect.move( -(138*2), 138 )
			column += 1
			newSprite = SectorSprite( sector, self.backSprites )
			newSprite.rect = squareRect
			newSprite = None

		statusBarSprite = StatusBarSprite(self.evManager,self.backSprites)

	#----------------------------------------------------------------------
	def ShowCharactor(self, charactor):
		sector = charactor.sector
		if not sector:
			print "Charactor is not in a sector.  cannot show"
			return

		charactorSprite = self.GetCharactorSprite( charactor )
		if not charactorSprite:
			charactorSprite = CharactorSprite( self.frontSprites )
		sectorSprite = self.GetSectorSprite( sector )
		charactorSprite.rect.center = sectorSprite.rect.center

	#----------------------------------------------------------------------
	def MoveCharactor(self, charactor):
		charactorSprite = self.GetCharactorSprite( charactor )

		sector = charactor.sector
		sectorSprite = self.GetSectorSprite( sector )

		charactorSprite.moveTo = sectorSprite.rect.center

	#----------------------------------------------------------------------
	def GetCharactorSprite(self, charactor):
		#there will be only one
		for s in self.frontSprites.sprites():
			if s.charactor is charactor:
				return s

		col = self.charactorColors[0]
		print "new color: ", col
		self.charactorColors.reverse()
		return CharactorSprite(charactor, self.frontSprites, col)

	#----------------------------------------------------------------------
	def GetSectorSprite(self, sector):
		for s in self.backSprites:
			if hasattr(s, "sector") and s.sector == sector:
				return s


	#----------------------------------------------------------------------
	def Notify(self, event):
		if isinstance( event, TickEvent ):
			#Draw Everything
			self.backSprites.clear( self.window, self.background )
			self.frontSprites.clear( self.window, self.background )

			self.backSprites.update()
			self.frontSprites.update()

			dirtyRects1 = self.backSprites.draw( self.window )
			dirtyRects2 = self.frontSprites.draw( self.window )
			
			dirtyRects = dirtyRects1 + dirtyRects2
			pygame.display.update( dirtyRects )


		elif isinstance( event, MapBuiltEvent ):
			gameMap = event.map
			self.ShowMap( gameMap )

		elif isinstance( event, CharactorPlaceEvent ):
			self.ShowCharactor( event.charactor )

		elif isinstance( event, CharactorMoveEvent ):
			self.MoveCharactor( event.charactor )

		elif isinstance( event, GameSyncEvent ):
			print 'Pygame View syncing to game state', event, event.game.__dict__
			game = event.game
			if game.state == Game.STATE_PREPARING:
				return
			print 'Pygame View syncing to game state'
			self.ShowMap( game.map )
			for player in game.players:
				for charactor in player.charactors:
					self.ShowCharactor( charactor )

#------------------------------------------------------------------------------
class Game:
	"""..."""

	STATE_PREPARING = 'preparing'
	STATE_RUNNING = 'running'
	STATE_PAUSED = 'paused'

	#----------------------------------------------------------------------
	def __init__(self, evManager):
		self.evManager = evManager
		self.evManager.RegisterListener( self )

		self.state = Game.STATE_PREPARING
		
		self.players = [ ]
		self.maxPlayers = 2
		self.map = Map( evManager )

	#----------------------------------------------------------------------
	def Start(self):
		self.map.Build()
		self.state = Game.STATE_RUNNING
		ev = GameStartedEvent( self )
		self.evManager.Post( ev )

	#----------------------------------------------------------------------
	def AddPlayer(self, player):
		self.players.append( player )
		player.SetGame( self )
		ev = PlayerJoinEvent( player )
		self.evManager.Post( ev )


	#----------------------------------------------------------------------
	def Notify(self, event):
		if isinstance( event, GameStartRequest ):
			if self.state == Game.STATE_PREPARING:
				self.Start()

		if isinstance( event, PlayerJoinRequest ):
			if self.state != Game.STATE_PREPARING:
				print "Players can not join after Game start"
				return
			if len(self.players) >= self.maxPlayers:
				print "Maximum players already joined"
				return
			player = Player( self.evManager )
			player.SetData( event.playerDict )
			self.AddPlayer( player )


#------------------------------------------------------------------------------
class Player(object):
	"""..."""
	def __init__(self, evManager):
		self.evManager = evManager
		self.game = None
		self.name = ""
		self.evManager.RegisterListener( self )

		self.charactors = [ Charactor(evManager) ]

	#----------------------------------------------------------------------
	def __str__(self):
		return '<Player %s %s>' % (self.name, id(self))

	#----------------------------------------------------------------------
	def GetPlaceData( self ):
		charactor = self.charactors[0]
		gameMap = self.game.map
		sector =  gameMap.sectors[gameMap.startSectorIndex]
		return [charactor, sector]

	#----------------------------------------------------------------------
	def GetMoveData( self ):
		return [self.charactors[0]]

	#----------------------------------------------------------------------
	def SetGame( self, game ):
		self.game = game

	#----------------------------------------------------------------------
	def SetData( self, playerDict ):
		self.name = playerDict['name']

	#----------------------------------------------------------------------
	def Notify(self, event):
		pass
		#if isinstance( event, PlayerJoinEvent):
			#if event.player is self:

#------------------------------------------------------------------------------
class Charactor:
	"""..."""

	STATE_INACTIVE = 0
	STATE_ACTIVE = 1

	def __init__(self, evManager):
		self.evManager = evManager
		self.evManager.RegisterListener( self )

		self.sector = None
		self.state = Charactor.STATE_INACTIVE

	#----------------------------------------------------------------------
	def __str__(self):
		return '<Charactor %s>' % id(self)

	#----------------------------------------------------------------------
	def Move(self, direction):
		if self.state == Charactor.STATE_INACTIVE:
			return

		if self.sector.MovePossible( direction ):
			newSector = self.sector.neighbors[direction]
			self.sector = newSector
			ev = CharactorMoveEvent( self )
			self.evManager.Post( ev )

	#----------------------------------------------------------------------
	def Place(self, sector):
		self.sector = sector
		self.state = Charactor.STATE_ACTIVE

		ev = CharactorPlaceEvent( self )
		self.evManager.Post( ev )

	#----------------------------------------------------------------------
	def Notify(self, event):
		if isinstance( event, CharactorPlaceRequest ) \
		 and event.charactor == self:
			self.Place( event.sector )

		elif isinstance( event, CharactorMoveRequest ) \
		  and event.charactor == self:
			self.Move( event.direction )

#------------------------------------------------------------------------------
class Map:
	"""..."""

	STATE_PREPARING = 0
	STATE_BUILT = 1


	#----------------------------------------------------------------------
	def __init__(self, evManager):
		self.evManager = evManager
		#self.evManager.RegisterListener( self )

		self.state = Map.STATE_PREPARING

		self.sectors = []
		self.startSectorIndex = 0

	#----------------------------------------------------------------------
	def Build(self):
		for i in range(9):
			self.sectors.append( Sector(self.evManager) )

		self.sectors[3].neighbors[DIRECTION_UP] = self.sectors[0]
		self.sectors[4].neighbors[DIRECTION_UP] = self.sectors[1]
		self.sectors[5].neighbors[DIRECTION_UP] = self.sectors[2]
		self.sectors[6].neighbors[DIRECTION_UP] = self.sectors[3]
		self.sectors[7].neighbors[DIRECTION_UP] = self.sectors[4]
		self.sectors[8].neighbors[DIRECTION_UP] = self.sectors[5]

		self.sectors[0].neighbors[DIRECTION_DOWN] = self.sectors[3]
		self.sectors[1].neighbors[DIRECTION_DOWN] = self.sectors[4]
		self.sectors[2].neighbors[DIRECTION_DOWN] = self.sectors[5]
		self.sectors[3].neighbors[DIRECTION_DOWN] = self.sectors[6]
		self.sectors[4].neighbors[DIRECTION_DOWN] = self.sectors[7]
		self.sectors[5].neighbors[DIRECTION_DOWN] = self.sectors[8]

		self.sectors[1].neighbors[DIRECTION_LEFT] = self.sectors[0]
		self.sectors[2].neighbors[DIRECTION_LEFT] = self.sectors[1]
		self.sectors[4].neighbors[DIRECTION_LEFT] = self.sectors[3]
		self.sectors[5].neighbors[DIRECTION_LEFT] = self.sectors[4]
		self.sectors[7].neighbors[DIRECTION_LEFT] = self.sectors[6]
		self.sectors[8].neighbors[DIRECTION_LEFT] = self.sectors[7]

		self.sectors[0].neighbors[DIRECTION_RIGHT] = self.sectors[1]
		self.sectors[1].neighbors[DIRECTION_RIGHT] = self.sectors[2]
		self.sectors[3].neighbors[DIRECTION_RIGHT] = self.sectors[4]
		self.sectors[4].neighbors[DIRECTION_RIGHT] = self.sectors[5]
		self.sectors[6].neighbors[DIRECTION_RIGHT] = self.sectors[7]
		self.sectors[7].neighbors[DIRECTION_RIGHT] = self.sectors[8]

		self.state = Map.STATE_BUILT

		ev = MapBuiltEvent( self )
		self.evManager.Post( ev )

#------------------------------------------------------------------------------
class Sector:
	"""..."""
	def __init__(self, evManager):
		self.evManager = evManager
		#self.evManager.RegisterListener( self )

		self.neighbors = range(4)

		self.neighbors[DIRECTION_UP] = None
		self.neighbors[DIRECTION_DOWN] = None
		self.neighbors[DIRECTION_LEFT] = None
		self.neighbors[DIRECTION_RIGHT] = None

	#----------------------------------------------------------------------
	def MovePossible(self, direction):
		if self.neighbors[direction]:
			return 1


#------------------------------------------------------------------------------
def main():
	"""..."""
	evManager = EventManager()

	keybd = KeyboardController( evManager )
	spinner = CPUSpinnerController( evManager )
	pygameView = PygameView( evManager )
	game = Game( evManager )
	
	spinner.Run()

if __name__ == "__main__":
	main()

########NEW FILE########
__FILENAME__ = network

from example1 import *
from twisted.spread import pb

# A list of ALL possible events that a server can send to a client
serverToClientEvents = []
# A list of ALL possible events that a client can send to a server
clientToServerEvents = []

#------------------------------------------------------------------------------
#Mix-In Helper Functions
#------------------------------------------------------------------------------
def MixInClass( origClass, addClass ):
	if addClass not in origClass.__bases__:
		origClass.__bases__ += (addClass,)

#------------------------------------------------------------------------------
def MixInCopyClasses( someClass ):
	MixInClass( someClass, pb.Copyable )
	MixInClass( someClass, pb.RemoteCopy )

#------------------------------------------------------------------------------
def serialize(obj, registry):
    objType = type(obj)
    if objType in [str, unicode, int, float, bool, type(None)]:
        return obj

    elif objType in [list, tuple]:
        new_obj = []
        for sub_obj in obj:
            new_obj.append(serialize(sub_obj, registry))
        return new_obj

    elif objType == dict:
        new_obj = {}
        for key, val in obj.items():
            new_obj[serialize(key, registry)] = serialize(val, registry)
        return new_obj

    else:
        objID = id(obj)
        registry[objID] = obj
        return objID
        
#------------------------------------------------------------------------------
class Serializable:
    '''The Serializable interface.
    All objects inheriting Serializable must have a .copyworthy_attrs member.
    '''
    def getStateToCopy(self, registry):
        d = {}
        for attr in self.copyworthy_attrs:
            val = getattr(self, attr)
            new_val = serialize(val, registry)
            d[attr] = new_val

        return d


#------------------------------------------------------------------------------
#------------------------------------------------------------------------------
# For each event class, if it is sendable over the network, we have 
# to Mix In the "copy classes", or make a replacement event class that is 
# copyable

#------------------------------------------------------------------------------
# TickEvent
# Direction: don't send.
#The Tick event happens hundreds of times per second.  If we think we need
#to send it over the network, we should REALLY re-evaluate our design

#------------------------------------------------------------------------------
# QuitEvent
# Direction: Client to Server only
MixInCopyClasses( QuitEvent )
pb.setUnjellyableForClass(QuitEvent, QuitEvent)
clientToServerEvents.append( QuitEvent )

#------------------------------------------------------------------------------
# GameStartRequest
# Direction: Client to Server only
MixInCopyClasses( GameStartRequest )
pb.setUnjellyableForClass(GameStartRequest, GameStartRequest)
clientToServerEvents.append( GameStartRequest )



#------------------------------------------------------------------------------
# ServerConnectEvent
# Direction: don't send.
# we don't need to send this over the network.

#------------------------------------------------------------------------------
# ClientConnectEvent
# Direction: don't send.
# we don't need to send this over the network.

#------------------------------------------------------------------------------
class ServerErrorEvent(object):
	def __init__(self):
		self.name = "Server Err Event"

#------------------------------------------------------------------------------
class ClientErrorEvent(object):
	def __init__(self):
		self.name = "Client Err Event"

#------------------------------------------------------------------------------
# GameStartedEvent
# Direction: Server to Client only
class CopyableGameStartedEvent(pb.Copyable, pb.RemoteCopy):
	def __init__(self, event, registry):
		self.name = "Copyable Game Started Event"
		self.gameID = id(event.game)
		registry[self.gameID] = event.game
		#TODO: put this in a Player Join Event or something
		for p in event.game.players:
			registry[id(p)] = p

pb.setUnjellyableForClass(CopyableGameStartedEvent, CopyableGameStartedEvent)
serverToClientEvents.append( CopyableGameStartedEvent )

#------------------------------------------------------------------------------
# MapBuiltEvent
# Direction: Server to Client only
class CopyableMapBuiltEvent( pb.Copyable, pb.RemoteCopy):
	def __init__(self, event, registry ):
		self.name = "Copyable Map Finished Building Event"
		self.mapID = id( event.map )
		registry[self.mapID] = event.map

pb.setUnjellyableForClass(CopyableMapBuiltEvent, CopyableMapBuiltEvent)
serverToClientEvents.append( CopyableMapBuiltEvent )

#------------------------------------------------------------------------------
# CharactorMoveEvent
# Direction: Server to Client only
class CopyableCharactorMoveEvent( pb.Copyable, pb.RemoteCopy):
	def __init__(self, event, registry ):
		self.name = "Copyable " + event.name
		self.charactorID = id( event.charactor )
		registry[self.charactorID] = event.charactor

pb.setUnjellyableForClass(CopyableCharactorMoveEvent, CopyableCharactorMoveEvent)
serverToClientEvents.append( CopyableCharactorMoveEvent )

#------------------------------------------------------------------------------
# CharactorPlaceEvent
# Direction: Server to Client only
class CopyableCharactorPlaceEvent( pb.Copyable, pb.RemoteCopy):
	def __init__(self, event, registry ):
		self.name = "Copyable " + event.name
		self.charactorID = id( event.charactor )
		registry[self.charactorID] = event.charactor

pb.setUnjellyableForClass(CopyableCharactorPlaceEvent, CopyableCharactorPlaceEvent)
serverToClientEvents.append( CopyableCharactorPlaceEvent )


#------------------------------------------------------------------------------
# PlayerJoinRequest
# Direction: Client to Server only
MixInCopyClasses( PlayerJoinRequest )
pb.setUnjellyableForClass(PlayerJoinRequest, PlayerJoinRequest)
clientToServerEvents.append( PlayerJoinRequest )

#------------------------------------------------------------------------------
# PlayerJoinEvent
# Direction: Server to Client only
class CopyablePlayerJoinEvent( pb.Copyable, pb.RemoteCopy):
	def __init__(self, event, registry):
		self.name = "Copyable " + event.name
		self.playerID = id(event.player)
		registry[self.playerID] = event.player
pb.setUnjellyableForClass(CopyablePlayerJoinEvent, CopyablePlayerJoinEvent)
serverToClientEvents.append( CopyablePlayerJoinEvent )

#------------------------------------------------------------------------------
# CharactorPlaceRequest
# Direction: Client to Server only
class CopyableCharactorPlaceRequest( pb.Copyable, pb.RemoteCopy):
	def __init__(self, event, registry ):
		self.name = "Copyable " + event.name
		self.playerID = None
		self.charactorID = None
		self.sectorID = None
		for key,val in registry.iteritems():
			if val is event.player:
				print 'making char place request'
				print 'self.playerid', key
				self.playerID = key
			if val is event.charactor:
				self.charactorID = key
			if val is event.sector:
				self.sectorID = key
		if None in ( self.playerID, self.charactorID, self.sectorID):
			print "SOMETHING REALLY WRONG"
			print self.playerID, event.player
			print self.charactorID, event.charactor
			print self.sectorID, event.sector
pb.setUnjellyableForClass(CopyableCharactorPlaceRequest, CopyableCharactorPlaceRequest)
clientToServerEvents.append( CopyableCharactorPlaceRequest )

#------------------------------------------------------------------------------
# CharactorMoveRequest
# Direction: Client to Server only
class CopyableCharactorMoveRequest( pb.Copyable, pb.RemoteCopy):
	def __init__(self, event, registry ):
		self.name = "Copyable " + event.name
		self.direction = event.direction
		self.playerID = None
		self.charactorID = None
		for key,val in registry.iteritems():
			if val is event.player:
				self.playerID = key
			if val is event.charactor:
				self.charactorID = key
		if None in ( self.playerID, self.charactorID):
			print "SOMETHING REALLY WRONG"
			print self.playerID, event.player
			print self.charactorID, event.charactor
pb.setUnjellyableForClass(CopyableCharactorMoveRequest, CopyableCharactorMoveRequest)
clientToServerEvents.append( CopyableCharactorMoveRequest )

#------------------------------------------------------------------------------
#------------------------------------------------------------------------------
# For any objects that we need to send in our events, we have to give them
# getStateToCopy() and setCopyableState() methods so that we can send a 
# network-friendly representation of them over the network.

#------------------------------------------------------------------------------
class CopyableMap:
	def getStateToCopy(self, registry):
		sectorIDList = []
		for sect in self.sectors:
			sID = id(sect)
			sectorIDList.append( sID )
			registry[sID] = sect

		return {'ninegrid':1, 'sectorIDList':sectorIDList}


	def setCopyableState(self, stateDict, registry):
		neededObjIDs = []
		success = True

		if self.state != Map.STATE_BUILT:
			self.Build()

		for i, sectID in enumerate(stateDict['sectorIDList']):
			registry[sectID] = self.sectors[i]

		return [success, neededObjIDs]

MixInClass( Map, CopyableMap )


#------------------------------------------------------------------------------
class CopyableGame(Serializable):
	copyworthy_attrs = ['map', 'state', 'players']

	def setCopyableState(self, stateDict, registry):
		neededObjIDs = []
		success = True

		self.state = stateDict['state']

		if not registry.has_key( stateDict['map'] ):
			registry[stateDict['map']] = Map( self.evManager )
			neededObjIDs.append( stateDict['map'] )
			success = False
		else:
			self.map = registry[stateDict['map']]

		self.players = []
		for pID in stateDict['players']:
			if not registry.has_key( pID ):
				registry[pID] = Player( self.evManager )
				neededObjIDs.append( pID )
				success = False
			else:
				self.players.append( registry[pID] )

		return [success, neededObjIDs]

MixInClass( Game, CopyableGame )

#------------------------------------------------------------------------------
class CopyablePlayer(Serializable):
	copyworthy_attrs = ['name', 'game', 'charactors']

	def setCopyableState(self, stateDict, registry):
		neededObjIDs = []
		success = True

		self.name = stateDict['name']

		if not registry.has_key( stateDict['game'] ):
			print "Something is wrong. should already be a game"
		else:
			self.game = registry[stateDict['game']]

		self.charactors = []
		for cID in stateDict['charactors']:
			if not registry.has_key( cID ):
				registry[cID] = Charactor( self.evManager )
				neededObjIDs.append( cID )
				success = False
			else:
				self.charactors.append( registry[cID] )

		return [success, neededObjIDs]

MixInClass( Player, CopyablePlayer )

#------------------------------------------------------------------------------
class CopyableCharactor(Serializable):
	copyworthy_attrs = ['sector', 'state']

	def setCopyableState(self, stateDict, registry):
		neededObjIDs = []
		success = True

		self.state = stateDict['state']

		if stateDict['sector'] == None:
			self.sector = None
		elif not registry.has_key( stateDict['sector'] ):
			registry[stateDict['sector']] = Sector(self.evManager)
			neededObjIDs.append( stateDict['sector'] )
			success = False
		else:
			self.sector = registry[stateDict['sector']]

		return [success, neededObjIDs]
		

MixInClass( Charactor, CopyableCharactor )

#------------------------------------------------------------------------------
# Copyable Sector is not necessary in this simple example because the sectors
# all get copied over in CopyableMap
#------------------------------------------------------------------------------
#------------------------------------------------------------------------------
class CopyableSector:
	def getStateToCopy(self, registry):
		return {}
		#d = self.__dict__.copy()
		#del d['evManager']
		#d['neighbors'][DIRECTION_UP] = id(d['neighbors'][DIRECTION_UP])
		#d['neighbors'][DIRECTION_DOWN] = id(d['neighbors'][DIRECTION_DOWN])
		#d['neighbors'][DIRECTION_LEFT] = id(d['neighbors'][DIRECTION_LEFT])
		#d['neighbors'][DIRECTION_RIGHT] = id(d['neighbors'][DIRECTION_RIGHT])
		#return d

	def setCopyableState(self, stateDict, registry):
		return [True, []]
		#neededObjIDs = []
		#success = True
		#if not registry.has_key( stateDict['neighbors'][DIRECTION_UP]):
			#neededObjIDs.append( stateDict['neighbors'][DIRECTION_UP] )
			#success = 0
		#else:
			#self.neighbors[DIRECTION_UP] = registry[stateDict['neighbors'][DIRECTION_UP]]
		#if not registry.has_key( stateDict['neighbors'][DIRECTION_DOWN]):
			#neededObjIDs.append( stateDict['neighbors'][DIRECTION_DOWN] )
			#success = 0
		#else:
			#self.neighbors[DIRECTION_DOWN] = registry[stateDict['neighbors'][DIRECTION_DOWN]]
		#if not registry.has_key( stateDict['neighbors'][DIRECTION_LEFT]):
			#neededObjIDs.append( stateDict['neighbors'][DIRECTION_LEFT] )
			#success = 0
		#else:
			#self.neighbors[DIRECTION_LEFT] = registry[stateDict['neighbors'][DIRECTION_LEFT]]
		#if not registry.has_key( stateDict['neighbors'][DIRECTION_RIGHT]):
			#neededObjIDs.append( stateDict['neighbors'][DIRECTION_RIGHT] )
			#success = 0
		#else:
			#self.neighbors[DIRECTION_RIGHT] = registry[stateDict['neighbors'][DIRECTION_RIGHT]]

		#return [success, neededObjIDs]

MixInClass( Sector, CopyableSector )

########NEW FILE########
__FILENAME__ = server
#! /usr/bin/env python
'''
Example server
'''

from twisted.spread import pb
from twisted.spread.pb import DeadReferenceError
from twisted.cred import checkers, portal
from zope.interface import implements
from example1 import EventManager, Game
from events import *
import network
from pprint import pprint

#------------------------------------------------------------------------------
class NoTickEventManager(EventManager):
    '''This subclass of EventManager doesn't wait for a Tick event before
    it starts consuming its event queue.  The server module doesn't have
    a CPUSpinnerController, so Ticks will not get generated.
    '''
    def __init__(self):
        EventManager.__init__(self)
        self._lock = False
    def Post(self, event):
        self.eventQueue.append(event)
        #print 'ev q is', self.eventQueue, 'lock is', self._lock
        if not self._lock:
            self._lock = True
            #print 'consuming queue'
            self.ActuallyUpdateListeners()
            self.ConsumeEventQueue()
            self._lock = False


#------------------------------------------------------------------------------
class TimerController:
    """A controller that sends of an event every second"""
    def __init__(self, evManager, reactor):
        self.evManager = evManager
        self.evManager.RegisterListener( self )

        self.reactor = reactor
        self.numClients = 0

    #-----------------------------------------------------------------------
    def NotifyApplicationStarted( self ):
        self.reactor.callLater( 1, self.Tick )

    #-----------------------------------------------------------------------
    def Tick(self):
        if self.numClients == 0:
            return

        ev = SecondEvent()
        self.evManager.Post( ev )
        ev = TickEvent()
        self.evManager.Post( ev )
        self.reactor.callLater( 1, self.Tick )

    #----------------------------------------------------------------------
    def Notify(self, event):
        if isinstance( event, ClientConnectEvent ):
            # first client connected.  start the clock.
            self.numClients += 1
            if self.numClients == 1:
                self.Tick()
        if isinstance( event, ClientDisconnectEvent ):
            self.numClients -= 1
        if isinstance( event, FatalEvent ):
            PostMortem(event, self.reactor)

#------------------------------------------------------------------------------
def PostMortem(fatalEvent, reactor):
    print "\n\nFATAL EVENT.  STOPPING REACTOR"
    reactor.stop()
    from pprint import pprint
    print 'Shared Objects at the time of the fatal event:'
    pprint( sharedObjectRegistry )

#------------------------------------------------------------------------------
class RegularAvatar(pb.IPerspective): pass
#class DisallowedAvatar(pb.IPerspective): pass
#------------------------------------------------------------------------------
class MyRealm:
    implements(portal.IRealm)
    def __init__(self, evManager):
        self.evManager = evManager
        self.evManager.RegisterListener( self )
        # keep track of avatars that have been given out
        self.claimedAvatarIDs = []
        # we need to hold onto views so they don't get garbage collected
        self.clientViews = []
        # maps avatars to player(s) they control
        self.playersControlledByAvatar = {}

    #----------------------------------------------------------------------
    def requestAvatar(self, avatarID, mind, *interfaces):
        print ' v'*30
        print 'requesting avatar id: ', avatarID
        print ' ^'*30
        if pb.IPerspective not in interfaces:
            print 'TWISTED FAILURE'
            raise NotImplementedError
        avatarClass = RegularAvatar
        if avatarID in self.claimedAvatarIDs:
            #avatarClass = DisallowedAvatar
            raise Exception( 'Another client is already connected'
                             ' to this avatar (%s)' % avatarID )

        self.claimedAvatarIDs.append(avatarID)
        ev = ClientConnectEvent( mind, avatarID )
        self.evManager.Post( ev )

        # TODO: this should be ok when avatarID is checkers.ANONYMOUS
        if avatarID not in self.playersControlledByAvatar:
            self.playersControlledByAvatar[avatarID] = []
        view = NetworkClientView( self.evManager, avatarID, mind )
        controller = NetworkClientController(self.evManager,
                                             avatarID,
                                             self)
        self.clientViews.append(view)
        return avatarClass, controller, controller.clientDisconnect

    #----------------------------------------------------------------------
    def knownPlayers(self):
        allPlayers = []
        for pList in self.playersControlledByAvatar.values():
            allPlayers.extend(pList)
        return allPlayers

    #----------------------------------------------------------------------
    def Notify(self, event):
        if isinstance(event, ClientDisconnectEvent):
            print 'got cli disconnect'
            self.claimedAvatarIDs.remove(event.avatarID)
            removee = None
            for view in self.clientViews:
                if view.avatarID == event.avatarID:
                    removee = view
            if removee:
                self.clientViews.remove(removee)

            print 'after disconnect, state is:'
            pprint (self.__dict__)


#------------------------------------------------------------------------------
class NetworkClientController(pb.Avatar):
    """We RECEIVE events from the CLIENT through this object
    There is an instance of NetworkClientController for each connected
    client.
    """
    def __init__(self, evManager, avatarID, realm):
        self.evManager = evManager
        self.evManager.RegisterListener( self )
        self.avatarID = avatarID
        self.realm = realm

    #----------------------------------------------------------------------
    def clientDisconnect(self):
        '''When a client disconnect is detected, this method
        gets called
        '''
        ev = ClientDisconnectEvent( self.avatarID )
        self.evManager.Post( ev )

    #----------------------------------------------------------------------
    def perspective_GetGameSync(self):
        """this is usually called when a client first connects or
        when they reconnect after a drop
        """
        game = sharedObjectRegistry.getGame()
        if game == None:
            print 'GetGameSync: game was none'
            raise Exception('Game should be set by this point')
        gameID = id( game )
        gameDict = game.getStateToCopy( sharedObjectRegistry )

        return [gameID, gameDict]
    
    #----------------------------------------------------------------------
    def perspective_GetObjectState(self, objectID):
        #print "request for object state", objectID
        if not sharedObjectRegistry.has_key( objectID ):
            print "No key on the server"
            return [0,0]
        obj = sharedObjectRegistry[objectID]
        print 'getting state for object', obj
        print 'my registry is '
        pprint(sharedObjectRegistry)
        objDict = obj.getStateToCopy( sharedObjectRegistry )

        return [objectID, objDict]
    
    #----------------------------------------------------------------------
    def perspective_EventOverNetwork(self, event):
        if isinstance(event, network.CopyableCharactorPlaceRequest):
            try:
                player = sharedObjectRegistry[event.playerID]
            except KeyError, ex:
                self.evManager.Post( FatalEvent( ex ) )
                raise
            pName = player.name
            if pName not in self.PlayersIControl():
                print 'i do not control', player
                print 'see?', self.PlayersIControl()
                print 'so i will ignore', event
                return
            try:
                charactor = sharedObjectRegistry[event.charactorID]
                sector = sharedObjectRegistry[event.sectorID]
            except KeyError, ex:
                self.evManager.Post( FatalEvent( ex ) )
                raise
            ev = CharactorPlaceRequest( player, charactor, sector )
        elif isinstance(event, network.CopyableCharactorMoveRequest):
            try:
                player = sharedObjectRegistry[event.playerID]
            except KeyError, ex:
                self.evManager.Post( FatalEvent( ex ) )
                raise
            pName = player.name
            if pName not in self.PlayersIControl():
                return
            try:
                charactor = sharedObjectRegistry[event.charactorID]
            except KeyError, ex:
                print 'sharedObjs did not have key:', ex
                print 'current sharedObjs:', sharedObjectRegistry
                print 'Did a client try to poison me?'
                self.evManager.Post( FatalEvent( ex ) )
                raise
            direction = event.direction
            ev = CharactorMoveRequest(player, charactor, direction)

        elif isinstance(event, PlayerJoinRequest):
            pName = event.playerDict['name']
            print 'got player join req.  known players:', self.realm.knownPlayers()
            if pName in self.realm.knownPlayers():
                print 'this player %s has already joined' % pName
                return
            self.ControlPlayer(pName)
            ev = event
        else:
            ev = event

        self.evManager.Post( ev )

        return 1

    #----------------------------------------------------------------------
    def Notify(self, event):
        if isinstance( event, GameStartedEvent ):
            self.game = event.game

    #----------------------------------------------------------------------
    def PlayersIControl(self):
        return self.realm.playersControlledByAvatar[self.avatarID]

    #----------------------------------------------------------------------
    def ControlPlayer(self, playerName):
        '''Note: this modifies self.realm.playersControlledByAvatar'''
        players = self.PlayersIControl()
        players.append(playerName)
        

#------------------------------------------------------------------------------
class TextLogView(object):
    def __init__(self, evManager):
        self.evManager = evManager
        self.evManager.RegisterListener( self )

    #----------------------------------------------------------------------
    def Notify(self, event):
        if event.__class__ in [TickEvent, SecondEvent]:
            return

        print 'TEXTLOG <',
        
        if isinstance( event, CharactorPlaceEvent ):
            print event.name, " at ", event.charactor.sector

        elif isinstance( event, CharactorMoveEvent ):
            print event.name, " to ", event.charactor.sector
        else:
            print 'event:', event


#------------------------------------------------------------------------------
class NetworkClientView(object):
    """We SEND events to the CLIENT through this object"""
    def __init__(self, evManager, avatarID, client):
        print "\nADDING CLIENT", client

        self.evManager = evManager
        self.evManager.RegisterListener( self )

        self.avatarID = avatarID
        self.client = client

    #----------------------------------------------------------------------
    def RemoteCallError(self, failure):
        from twisted.internet.error import ConnectionLost
        #trap ensures that the rest will happen only 
        #if the failure was ConnectionLost
        failure.trap(ConnectionLost)
        self.HandleFailure(self.client)
        return failure

    #----------------------------------------------------------------------
    def HandleFailure(self):
        print "Failing Client", self.client

    #----------------------------------------------------------------------
    def RemoteCall( self, fnName, *args):
        try:
            remoteCall = self.client.callRemote(fnName, *args)
            remoteCall.addErrback(self.RemoteCallError)
        except DeadReferenceError:
            self.HandleFailure()

    #----------------------------------------------------------------------
    def EventThatShouldBeSent(self, event):
        ev = event

        #don't send events that aren't Copyable
        if not isinstance( ev, pb.Copyable ):
            evName = ev.__class__.__name__
            copyableClsName = "Copyable"+evName
            if not hasattr( network, copyableClsName ):
                return None
            copyableClass = getattr( network, copyableClsName )
            ev = copyableClass( ev, sharedObjectRegistry )

        if ev.__class__ not in network.serverToClientEvents:
            print "SERVER NOT SENDING: " +str(ev)
            return None

        return ev

    #----------------------------------------------------------------------
    def Notify(self, event):
        #NOTE: this is very "chatty".  We could restrict 
        #      the number of clients notified in the future

        ev = self.EventThatShouldBeSent(event)
        if not ev:
            return

        print "\n====server===sending: ", str(ev), 'to',
        print self.avatarID, '(', self.client, ')'
        self.RemoteCall( "ServerEvent", ev )


class Model(dict):
    def __init__(self, *args, **kwargs):
        dict.__init__(self, *args, **kwargs)
        self.gameKey = None

    def __setitem__(self, key, val):
        print 'setting', key, val
        dict.__setitem__(self, key, val)
        if isinstance(val, Game):
            self.gameKey = key

    def getGame(self):
        return self[self.gameKey]

evManager = None
sharedObjectRegistry = None
#------------------------------------------------------------------------------
def main():
    global evManager, sharedObjectRegistry
    from twisted.internet import reactor
    evManager = NoTickEventManager()
    sharedObjectRegistry = Model()

    log = TextLogView( evManager )
    timer = TimerController( evManager, reactor )
    game = Game( evManager )
    sharedObjectRegistry[id(game)] = game

    #factory = pb.PBServerFactory(clientController)
    #reactor.listenTCP( 8000, factory )

    realm = MyRealm(evManager)
    portl = portal.Portal(realm)
    checker = checkers.InMemoryUsernamePasswordDatabaseDontUse(
                                                           user1='pass1',
                                                           user2='pass1')
    portl.registerChecker(checker)
    reactor.listenTCP(8000, pb.PBServerFactory(portl))

    reactor.run()

if __name__ == "__main__":
    print 'starting server...'
    main()


########NEW FILE########
__FILENAME__ = client
import network
import twisted.internet
from twisted.spread import pb
from twisted.internet.task import LoopingCall
from twisted.internet.selectreactor import SelectReactor
from twisted.internet.main import installReactor
from events import *
import example1
from example1 import (EventManager,
                      MenuKeyboardController,
                      GameKeyboardController,
                      PygameView)

serverHost, serverPort = 'localhost', 8000

#------------------------------------------------------------------------------
class CPUSpinnerController:
	def __init__(self, evManager):
		self.evManager = evManager
		self.evManager.RegisterListener( self )

		self.keepGoing = 1
		self.replacementSpinner = None

	#----------------------------------------------------------------------
	def Run(self):
		while self.keepGoing:
			event = TickEvent()
			self.evManager.Post( event )
		print 'CPU spinner done'
		if self.replacementSpinner:
			print 'replacement spinner run()'
			self.replacementSpinner.Run()

	#----------------------------------------------------------------------
	def SwitchToReactorSpinner(self):
		self.keepGoing = False
		self.replacementSpinner = ReactorSpinController(self.evManager)

	#----------------------------------------------------------------------
	def Notify(self, event):
		if isinstance( event, QuitEvent ):
			self.keepGoing = False


#------------------------------------------------------------------------------
class ReactorSpinController:
	STATE_STOPPED = 0
	STATE_STARTED = 1
	STATE_SHUTTING_DOWN = 2

	def __init__(self, evManager):
		self.state = ReactorSpinController.STATE_STOPPED
		self.evManager = evManager
		self.evManager.RegisterListener( self )
		self.reactor = SelectReactor()
		installReactor(self.reactor)
		self.loopingCall = LoopingCall(self.FireTick)

	#----------------------------------------------------------------------
	def FireTick(self):
		self.evManager.Post( TickEvent() )

	#----------------------------------------------------------------------
	def Run(self):
		self.state = ReactorSpinController.STATE_STARTED
		framesPerSecond = 10
		interval = 1.0 / framesPerSecond
		self.loopingCall.start(interval)
		self.reactor.run()

	#----------------------------------------------------------------------
	def Stop(self):
		print 'stopping the reactor'
		self.state = ReactorSpinController.STATE_SHUTTING_DOWN
		self.reactor.addSystemEventTrigger('after', 'shutdown',
		                                   self.onReactorStop)
		self.reactor.stop()

	#----------------------------------------------------------------------
	def onReactorStop(self):
		print 'reactor is now totally stopped'
		self.state = ReactorSpinController.STATE_STOPPED
		self.reactor = None

	#----------------------------------------------------------------------
	def Notify(self, event):
		if isinstance( event, QuitEvent ):
			self.Stop()


#------------------------------------------------------------------------------
class NetworkServerView(pb.Root):
	"""We SEND events to the server through this object"""
	STATE_PREPARING = 0
	STATE_CONNECTING = 1
	STATE_CONNECTED = 2
	STATE_DISCONNECTING = 3
	STATE_DISCONNECTED = 4

	#----------------------------------------------------------------------
	def __init__(self, evManager, sharedObjectRegistry):
		self.evManager = evManager
		self.evManager.RegisterListener( self )

		self.pbClientFactory = pb.PBClientFactory()
		self.state = NetworkServerView.STATE_PREPARING
		self.server = None
		self.connection = None

		self.sharedObjs = sharedObjectRegistry

	#----------------------------------------------------------------------
	def AttemptConnection(self):
		print "attempting a connection to", serverHost, serverPort
		try:
			reactor = twisted.internet.reactor
		except AttributeError:
			print 'Reactor not yet installed!'
			return
		self.state = NetworkServerView.STATE_CONNECTING
		self.connection = reactor.connectTCP(serverHost, serverPort,
		                                     self.pbClientFactory)
		deferred = self.pbClientFactory.getRootObject()
		deferred.addCallback(self.Connected)
		deferred.addErrback(self.ConnectFailed)

	#----------------------------------------------------------------------
	def Disconnect(self):
		print 'disconnecting', self.connection
		self.connection.disconnect()
		self.state = NetworkServerView.STATE_DISCONNECTED

	#----------------------------------------------------------------------
	def Connected(self, server):
		print "CONNECTED"
		self.server = server
		self.state = NetworkServerView.STATE_CONNECTED
		ev = ServerConnectEvent( server )
		self.evManager.Post( ev )

	#----------------------------------------------------------------------
	def ConnectFailed(self, server):
		print "CONNECTION FAILED"
		self.state = NetworkServerView.STATE_DISCONNECTED
		self.evManager.Post(ConnectFail(server))

	#----------------------------------------------------------------------
	def Notify(self, event):
		if isinstance( event, RequestServerConnectEvent ):
			if self.state == NetworkServerView.STATE_PREPARING:
				self.AttemptConnection()
			return

		if isinstance( event, QuitEvent ):
			self.Disconnect()
			return

		ev = event
		if not isinstance( event, pb.Copyable ):
			evName = event.__class__.__name__
			copyableClsName = "Copyable"+evName
			if not hasattr( network, copyableClsName ):
				return
			copyableClass = getattr( network, copyableClsName )
			ev = copyableClass( event, self.sharedObjs )

		if ev.__class__ not in network.clientToServerEvents:
			print "CLIENT NOT SENDING: " +str(ev)
			return
			
		if self.server:
			print " ====   Client sending", str(ev)
			remoteCall = self.server.callRemote("EventOverNetwork",
			                                    ev)
		else:
			print " =--= Cannot send while disconnected:", str(ev)



#------------------------------------------------------------------------------
class NetworkServerController(pb.Referenceable):
	"""We RECEIVE events from the server through this object"""
	def __init__(self, evManager):
		self.server = None
		self.evManager = evManager
		self.evManager.RegisterListener( self )

	#----------------------------------------------------------------------
	def remote_ServerEvent(self, event):
		print " ====  GOT AN EVENT FROM SERVER:", str(event)
		self.evManager.Post( event )
		return 1

	#----------------------------------------------------------------------
	def OnSelfAddedToServer(self, *args):
		print 'success callback triggered'
		event = BothSidesConnectedEvent()
		self.evManager.Post( event )

	#----------------------------------------------------------------------
	def OnServerAddSelfFailed(self, *args):
		print 'fail callback triggered', args
		print dir(args[0])
		print args[0].printDetailedTraceback()
		event = ConnectFail( self.server )
		self.evManager.Post( event )

	#----------------------------------------------------------------------
	def Notify(self, event):
		if isinstance( event, ServerConnectEvent ):
			print 'connecting serv controller'
			#tell the server that we're listening to it and
			#it can access this object
			self.server = event.server
			d = self.server.callRemote("ClientConnect", self)
			d.addCallback(self.OnSelfAddedToServer)
			d.addErrback(self.OnServerAddSelfFailed)


#------------------------------------------------------------------------------
class PhonyEventManager(EventManager):
	#----------------------------------------------------------------------
	def Post( self, event ):
		pass

#------------------------------------------------------------------------------
class PhonyModel(object):
	'''This isn't the authouritative model.  That one exists on the
	server.  This is a model to store local state and to interact with
	the local EventManager.
	'''
	def __init__(self, evManager, sharedObjectRegistry,
	             controller, spinner):
		self.sharedObjs = sharedObjectRegistry
		self.controller = controller
		self.spinner = spinner
		self.game = None
		self.server = None
		self.phonyEvManager = PhonyEventManager()
		self.realEvManager = evManager
		self.onConnectEvents = []

		self.realEvManager.RegisterListener( self )

	#----------------------------------------------------------------------
	def StateReturned(self, response):
		if response[0] == 0:
			print "GOT ZERO -- better error handler here"
			return None
		objID = response[0]
		objDict = response[1]
		obj = self.sharedObjs[objID]

		retval = obj.setCopyableState(objDict, self.sharedObjs)
		if retval[0] == 1:
			return obj
		for remainingObjID in retval[1]:
			remoteResponse = self.server.callRemote("GetObjectState", remainingObjID)
			remoteResponse.addCallback(self.StateReturned)

		#TODO: look under the Twisted Docs for "Chaining Defferreds"
		retval = obj.setCopyableState(objDict, self.sharedObjs)
		if retval[0] == 0:
			print "WEIRD!!!!!!!!!!!!!!!!!!"
			return None

		return obj

	#----------------------------------------------------------------------
	def Notify(self, event):
		if isinstance( event, ServerConnectEvent ):
			self.server = event.server
		elif isinstance( event, network.CopyableGameStartedEvent ):
			gameID = event.gameID
			if not self.game:
				# give a phony event manager to the local game
				# object so it won't be able to fire events
				self.game = example1.Game( self.phonyEvManager )
				self.sharedObjs[gameID] = self.game
			print 'sending the gse to the real em.'
			ev = GameStartedEvent( self.game )
			self.realEvManager.Post( ev )

		if isinstance( event, network.CopyableMapBuiltEvent ):
			mapID = event.mapID
			if not self.game:
				self.game = example1.Game( self.phonyEvManager )
			if self.sharedObjs.has_key(mapID):
				map = self.sharedObjs[mapID]
				ev = MapBuiltEvent( map )
				self.realEvManager.Post( ev )
			else:
				map = self.game.map
				self.sharedObjs[mapID] = map
				remoteResponse = self.server.callRemote("GetObjectState", mapID)
				remoteResponse.addCallback(self.StateReturned)
				remoteResponse.addCallback(self.MapBuiltCallback)

		if isinstance( event, network.CopyableCharactorPlaceEvent ):
			charactorID = event.charactorID
			if self.sharedObjs.has_key(charactorID):
				charactor = self.sharedObjs[charactorID]
				ev = CharactorPlaceEvent( charactor )
				self.realEvManager.Post( ev )
			else:
				charactor = self.game.players[0].charactors[0]
				self.sharedObjs[charactorID] = charactor
				remoteResponse = self.server.callRemote("GetObjectState", charactorID)
				remoteResponse.addCallback(self.StateReturned)
				remoteResponse.addCallback(self.CharactorPlaceCallback)

		if isinstance( event, network.CopyableCharactorMoveEvent ):
			charactorID = event.charactorID
			if self.sharedObjs.has_key(charactorID):
				charactor = self.sharedObjs[charactorID]
			else:
				charactor = self.game.players[0].charactors[0]
				self.sharedObjs[charactorID] = charactor
			remoteResponse = self.server.callRemote("GetObjectState", charactorID)
			remoteResponse.addCallback(self.StateReturned)
			remoteResponse.addCallback(self.CharactorMoveCallback)

		if isinstance( event, MenuMultiPlayerEvent ):
			self.StartMultiplayer()

		if isinstance( event, BothSidesConnectedEvent ):
			self.OnServerConnectSuccess()

	#----------------------------------------------------------------------
	def CharactorPlaceCallback(self, charactor):
		ev = CharactorPlaceEvent( charactor )
		self.realEvManager.Post( ev )
	#----------------------------------------------------------------------
	def MapBuiltCallback(self, map):
		ev = MapBuiltEvent( map )
		self.realEvManager.Post( ev )
	#----------------------------------------------------------------------
	def CharactorMoveCallback(self, charactor):
		ev = CharactorMoveEvent( charactor )
		self.realEvManager.Post( ev )

	#----------------------------------------------------------------------
	def OnServerConnectSuccess(self):
		# now that we're connected, post all the queued events
		while self.onConnectEvents:
			ev = self.onConnectEvents.pop(0)
			self.realEvManager.Post(ev)

	#----------------------------------------------------------------------
	def OnServerConnectFail(self):
		self.onConnectEvents = []

	#----------------------------------------------------------------------
	def StartMultiplayer(self):
		self.spinner.SwitchToReactorSpinner()
		self.serverController = \
		                    NetworkServerController(self.realEvManager)
		self.serverView = \
		    NetworkServerView(self.realEvManager, self.sharedObjs)
		self.controller = GameKeyboardController( self.realEvManager )
		self.realEvManager.Post(RequestServerConnectEvent())
		self.onConnectEvents.append(GameStartRequest())


#------------------------------------------------------------------------------
def main():
	sharedObjectRegistry = {}
	evManager = EventManager()

	spinner = CPUSpinnerController( evManager )
	pygameView = PygameView( evManager )
	controller = MenuKeyboardController( evManager )
	phonyModel = PhonyModel( evManager, sharedObjectRegistry,
	                         controller, spinner )

	#from twisted.spread.jelly import globalSecurity
	#globalSecurity.allowModules( network )
	
	spinner.Run()
	print 'Done Run'
	print evManager.eventQueue

if __name__ == "__main__":
	main()

########NEW FILE########
__FILENAME__ = events
#SECURITY NOTE: anything in here can be created simply by sending the 
# class name over the network.  This is a potential vulnerability
# I wouldn't suggest letting any of these classes DO anything, especially
# things like file system access, or allocating huge amounts of memory

class Event:
	"""this is a superclass for any events that might be generated by an
	object and sent to the EventManager"""
	def __init__(self):
		self.name = "Generic Event"

class TickEvent(Event):
	def __init__(self):
		self.name = "CPU Tick Event"

class QuitEvent(Event):
	def __init__(self):
		self.name = "Program Quit Event"

class MapBuiltEvent(Event):
	def __init__(self, map):
		self.name = "Map Finished Building Event"
		self.map = map

class GameStartRequest(Event):
	def __init__(self):
		self.name = "Game Start Request"

class GameStartedEvent(Event):
	def __init__(self, game):
		self.name = "Game Started Event"
		self.game = game

class CharactorMoveRequest(Event):
	def __init__(self, direction):
		self.name = "Charactor Move Request"
		self.direction = direction

class CharactorMoveEvent(Event):
	def __init__(self, charactor):
		self.name = "Charactor Move Event"
		self.charactor = charactor

class CharactorPlaceEvent(Event):
	"""this event occurs when a Charactor is *placed* in a sector, 
	ie it doesn't move there from an adjacent sector."""
	def __init__(self, charactor):
		self.name = "Charactor Placement Event"
		self.charactor = charactor

class ServerConnectEvent(Event):
	"""the client generates this when it detects that it has successfully
	connected to the server"""
	def __init__(self, serverReference):
		self.name = "Network Server Connection Event"
		self.server = serverReference

class ClientConnectEvent(Event):
	"""this event is generated by the Server whenever a client connects
	to it"""
	def __init__(self, client):
		self.name = "Network Client Connection Event"
		self.client = client

class MenuMultiPlayerEvent(Event):
	def __init__(self):
		self.name = "Multi Player Selected From Menu"

class RequestServerConnectEvent(Event):
	def __init__(self):
		self.name = "Connect to Remote Server"

class BothSidesConnectedEvent(Event):
	def __init__(self):
		self.name = "Controller and View Connected to Remote Server"

class ConnectFail(Event):
	def __init__(self, host):
		self.name = "Controller or View Failed Connected to Host"
		self.host = host

########NEW FILE########
__FILENAME__ = example1
def Debug( msg ):
	print msg

DIRECTION_UP = 0
DIRECTION_DOWN = 1
DIRECTION_LEFT = 2
DIRECTION_RIGHT = 3

from events import *

#------------------------------------------------------------------------------
class EventManager:
	"""this object is responsible for coordinating most communication
	between the Model, View, and Controller."""
	def __init__(self ):
		from weakref import WeakKeyDictionary
		self.listeners = WeakKeyDictionary()
		self.eventQueue= []

	#----------------------------------------------------------------------
	def RegisterListener( self, listener ):
		self.listeners[ listener ] = 1

	#----------------------------------------------------------------------
	def UnregisterListener( self, listener ):
		if listener in self.listeners:
			del self.listeners[ listener ]
		
	#----------------------------------------------------------------------
	def Post( self, event ):
		self.eventQueue.append(event)
		if isinstance(event, TickEvent):
			# Consume the event queue every Tick.
			self.ConsumeEventQueue()
		else:
			Debug( "     Message: " + event.name )

	#----------------------------------------------------------------------
	def ConsumeEventQueue(self):
		i = 0
		while i < len( self.eventQueue ):
			event = self.eventQueue[i]
			# copy the keys before iterating, as new listeners 
			# can be added or removed as a side effect of notifying.
			listeners = self.listeners.keys()
			for listener in listeners:
				# Note: a side effect of notifying the listener
				# could be that more events are put on the queue
				listener.Notify( event )
			i += 1
		#all code paths that could possibly add more events to 
		# the eventQueue have been exhausted at this point, so 
		# it's safe to empty the queue
		self.eventQueue= []


#------------------------------------------------------------------------------
class GameKeyboardController:
	"""..."""
	def __init__(self, evManager):
		self.evManager = evManager
		self.evManager.RegisterListener( self )

	#----------------------------------------------------------------------
	def Notify(self, event):
		if isinstance( event, TickEvent ):
			#Handle Input Events
			for event in pygame.event.get():
				ev = None
				if event.type == QUIT:
					ev = QuitEvent()
				elif event.type == KEYDOWN \
				     and event.key == K_ESCAPE:
					ev = QuitEvent()
				elif event.type == KEYDOWN \
				     and event.key == K_UP:
					direction = DIRECTION_UP
					ev = CharactorMoveRequest(direction)
				elif event.type == KEYDOWN \
				     and event.key == K_DOWN:
					direction = DIRECTION_DOWN
					ev = CharactorMoveRequest(direction)
				elif event.type == KEYDOWN \
				     and event.key == K_LEFT:
					direction = DIRECTION_LEFT
					ev = CharactorMoveRequest(direction)
				elif event.type == KEYDOWN \
				     and event.key == K_RIGHT:
					direction = DIRECTION_RIGHT
					ev = CharactorMoveRequest(direction)

				if ev:
					self.evManager.Post( ev )


#------------------------------------------------------------------------------
class CPUSpinnerController:
	"""..."""
	def __init__(self, evManager):
		self.evManager = evManager
		self.evManager.RegisterListener( self )

		self.keepGoing = 1

	#----------------------------------------------------------------------
	def Run(self):
		while self.keepGoing:
			event = TickEvent()
			self.evManager.Post( event )

	#----------------------------------------------------------------------
	def Notify(self, event):
		if isinstance( event, QuitEvent ):
			#this will stop the while loop from running
			self.keepGoing = False


import pygame
from pygame.locals import *
#------------------------------------------------------------------------------
class SectorSprite(pygame.sprite.Sprite):
	def __init__(self, sector, group=None):
		pygame.sprite.Sprite.__init__(self, group)
		self.image = pygame.Surface( (128,128) )
		self.image.fill( (0,255,128) )

		self.sector = sector

#------------------------------------------------------------------------------
class CharactorSprite(pygame.sprite.Sprite):
	def __init__(self, group=None):
		pygame.sprite.Sprite.__init__(self, group)

		charactorSurf = pygame.Surface( (64,64) )
		charactorSurf = charactorSurf.convert_alpha()
		charactorSurf.fill((0,0,0,0)) #make transparent
		pygame.draw.circle( charactorSurf, (255,0,0), (32,32), 32 )
		self.image = charactorSurf
		self.rect  = charactorSurf.get_rect()

		self.moveTo = None

	#----------------------------------------------------------------------
	def update(self):
		if self.moveTo:
			self.rect.center = self.moveTo
			self.moveTo = None


#------------------------------------------------------------------------------
class MenuSprite(pygame.sprite.Sprite):
	def __init__(self, text):
		pygame.sprite.Sprite.__init__(self)
		font = pygame.font.Font(None, 30)
		self.image = font.render(text, 1, (255,0,0))
		self.rect = self.image.get_rect()


#------------------------------------------------------------------------------
class MenuKeyboardController:
	def __init__(self, evManager):
		self.evManager = evManager
		self.evManager.RegisterListener( self )

	#----------------------------------------------------------------------
	def Notify(self, event):
		if isinstance( event, TickEvent ):
			#Handle Input Events
			for event in pygame.event.get():
				ev = None
				if event.type == QUIT:
					ev = QuitEvent()
				elif event.type == KEYDOWN \
				     and event.key == K_ESCAPE:
					ev = QuitEvent()
				elif event.type == KEYDOWN \
				     and event.key == K_s:
					ev = GameStartRequest()
				elif event.type == KEYDOWN \
				     and event.key == K_m:
					ev = MenuMultiPlayerEvent()

				if ev:
					self.evManager.Post( ev )


#------------------------------------------------------------------------------
class Menu:
	def __init__(self, evManager):
		self.evManager = evManager
		self.evManager.RegisterListener( self )

#------------------------------------------------------------------------------
class PygameView:
	"""..."""
	def __init__(self, evManager):
		self.evManager = evManager
		self.evManager.RegisterListener( self )

		pygame.init()
		self.window = pygame.display.set_mode( (424,440) )
		pygame.display.set_caption( 'Example Game' )
		self.background = pygame.Surface( self.window.get_size() )
		self.background.fill( (0,0,0) )

		self.backSprites = pygame.sprite.RenderUpdates()
		self.frontSprites = pygame.sprite.RenderUpdates()

		self.ShowMenu()

	#----------------------------------------------------------------------
	def ShowMenu(self):
		options = [
		     'Press S for single-player',
		     'Press M for multi-player',
		]
		yLocation = 0
		for option in options:
			newSprite = MenuSprite(option)
			newSprite.rect.y = yLocation
			yLocation += 50
			self.backSprites.add(newSprite)

	#----------------------------------------------------------------------
	def ShowMap(self, gameMap):
		self.backSprites.empty()

		squareRect = pygame.Rect( (-128,10, 128,128 ) )

		i = 0
		for sector in gameMap.sectors:
			if i < 3:
				squareRect = squareRect.move( 138,0 )
			else:
				i = 0
				squareRect = squareRect.move( -(138*2), 138 )
			i += 1
			newSprite = SectorSprite( sector, self.backSprites )
			newSprite.rect = squareRect
			newSprite = None

	#----------------------------------------------------------------------
	def ShowCharactor(self, charactor):
		charactorSprite = CharactorSprite( self.frontSprites )

		sector = charactor.sector
		sectorSprite = self.GetSectorSprite( sector )
		charactorSprite.rect.center = sectorSprite.rect.center

	#----------------------------------------------------------------------
	def MoveCharactor(self, charactor):
		charactorSprite = self.GetCharactorSprite( charactor )

		sector = charactor.sector
		sectorSprite = self.GetSectorSprite( sector )

		charactorSprite.moveTo = sectorSprite.rect.center

	#----------------------------------------------------------------------
	def GetCharactorSprite(self, charactor):
		#there will be only one
		for s in self.frontSprites:
			return s

	#----------------------------------------------------------------------
	def GetSectorSprite(self, sector):
		for s in self.backSprites:
			if hasattr(s, "sector") and s.sector == sector:
				return s


	#----------------------------------------------------------------------
	def Notify(self, event):
		if isinstance( event, TickEvent ):
			#Draw Everything
			self.backSprites.clear( self.window, self.background )
			self.frontSprites.clear( self.window, self.background )

			self.backSprites.update()
			self.frontSprites.update()

			dirtyRects1 = self.backSprites.draw( self.window )
			dirtyRects2 = self.frontSprites.draw( self.window )
			
			dirtyRects = dirtyRects1 + dirtyRects2
			pygame.display.update( dirtyRects )

		elif isinstance( event, MapBuiltEvent ):
			gameMap = event.map
			self.ShowMap( gameMap )

		elif isinstance( event, CharactorPlaceEvent ):
			self.ShowCharactor( event.charactor )

		elif isinstance( event, CharactorMoveEvent ):
			self.MoveCharactor( event.charactor )


#------------------------------------------------------------------------------
class Game:
	"""..."""

	STATE_PREPARING = 0
	STATE_RUNNING = 1
	STATE_PAUSED = 2

	#----------------------------------------------------------------------
	def __init__(self, evManager):
		self.evManager = evManager
		self.evManager.RegisterListener( self )

		self.state = Game.STATE_PREPARING
		self.map = Map( self.evManager )
		
		self.players = [ Player(evManager) ]
		self.controller = MenuKeyboardController(self.evManager)

	#----------------------------------------------------------------------
	def Start(self):
		self.controller = GameKeyboardController(self.evManager)
		self.map.Build()
		self.state = Game.STATE_RUNNING
		ev = GameStartedEvent( self )
		self.evManager.Post( ev )

	#----------------------------------------------------------------------
	def Notify(self, event):
		if isinstance( event, GameStartRequest ):
			if self.state == Game.STATE_PREPARING:
				self.Start()


#------------------------------------------------------------------------------
class Player:
	"""..."""
	def __init__(self, evManager):
		self.evManager = evManager
		#self.evManager.RegisterListener( self )

		self.charactors = [ Charactor(evManager) ]

#------------------------------------------------------------------------------
class Charactor:
	"""..."""

	STATE_INACTIVE = 0
	STATE_ACTIVE = 1

	def __init__(self, evManager):
		self.evManager = evManager
		self.evManager.RegisterListener( self )

		self.sector = None
		self.state = Charactor.STATE_INACTIVE

	#----------------------------------------------------------------------
	def Move(self, direction):
		if self.state == Charactor.STATE_INACTIVE:
			return

		if self.sector.MovePossible( direction ):
			newSector = self.sector.neighbors[direction]
			self.sector = newSector
			ev = CharactorMoveEvent( self )
			self.evManager.Post( ev )

	#----------------------------------------------------------------------
	def Place(self, sector):
		self.sector = sector
		self.state = Charactor.STATE_ACTIVE

		ev = CharactorPlaceEvent( self )
		self.evManager.Post( ev )

	#----------------------------------------------------------------------
	def Notify(self, event):
		if isinstance( event, GameStartedEvent ):
			gameMap = event.game.map
			self.Place( gameMap.sectors[gameMap.startSectorIndex] )

		elif isinstance( event, CharactorMoveRequest ):
			self.Move( event.direction )

#------------------------------------------------------------------------------
class Map:
	"""..."""

	STATE_PREPARING = 0
	STATE_BUILT = 1


	#----------------------------------------------------------------------
	def __init__(self, evManager):
		self.evManager = evManager
		#self.evManager.RegisterListener( self )

		self.state = Map.STATE_PREPARING

		self.sectors = range(9)
		self.startSectorIndex = 0

	#----------------------------------------------------------------------
	def Build(self):
		for i in range(9):
			self.sectors[i] = Sector( self.evManager )

		self.sectors[3].neighbors[DIRECTION_UP] = self.sectors[0]
		self.sectors[4].neighbors[DIRECTION_UP] = self.sectors[1]
		self.sectors[5].neighbors[DIRECTION_UP] = self.sectors[2]
		self.sectors[6].neighbors[DIRECTION_UP] = self.sectors[3]
		self.sectors[7].neighbors[DIRECTION_UP] = self.sectors[4]
		self.sectors[8].neighbors[DIRECTION_UP] = self.sectors[5]

		self.sectors[0].neighbors[DIRECTION_DOWN] = self.sectors[3]
		self.sectors[1].neighbors[DIRECTION_DOWN] = self.sectors[4]
		self.sectors[2].neighbors[DIRECTION_DOWN] = self.sectors[5]
		self.sectors[3].neighbors[DIRECTION_DOWN] = self.sectors[6]
		self.sectors[4].neighbors[DIRECTION_DOWN] = self.sectors[7]
		self.sectors[5].neighbors[DIRECTION_DOWN] = self.sectors[8]

		self.sectors[1].neighbors[DIRECTION_LEFT] = self.sectors[0]
		self.sectors[2].neighbors[DIRECTION_LEFT] = self.sectors[1]
		self.sectors[4].neighbors[DIRECTION_LEFT] = self.sectors[3]
		self.sectors[5].neighbors[DIRECTION_LEFT] = self.sectors[4]
		self.sectors[7].neighbors[DIRECTION_LEFT] = self.sectors[6]
		self.sectors[8].neighbors[DIRECTION_LEFT] = self.sectors[7]

		self.sectors[0].neighbors[DIRECTION_RIGHT] = self.sectors[1]
		self.sectors[1].neighbors[DIRECTION_RIGHT] = self.sectors[2]
		self.sectors[3].neighbors[DIRECTION_RIGHT] = self.sectors[4]
		self.sectors[4].neighbors[DIRECTION_RIGHT] = self.sectors[5]
		self.sectors[6].neighbors[DIRECTION_RIGHT] = self.sectors[7]
		self.sectors[7].neighbors[DIRECTION_RIGHT] = self.sectors[8]

		self.state = Map.STATE_BUILT

		ev = MapBuiltEvent( self )
		self.evManager.Post( ev )

#------------------------------------------------------------------------------
class Sector:
	"""..."""
	def __init__(self, evManager):
		self.evManager = evManager
		#self.evManager.RegisterListener( self )

		self.neighbors = range(4)

		self.neighbors[DIRECTION_UP] = None
		self.neighbors[DIRECTION_DOWN] = None
		self.neighbors[DIRECTION_LEFT] = None
		self.neighbors[DIRECTION_RIGHT] = None

	#----------------------------------------------------------------------
	def MovePossible(self, direction):
		if self.neighbors[direction]:
			return 1


#------------------------------------------------------------------------------
def main():
	"""..."""
	evManager = EventManager()

	spinner = CPUSpinnerController( evManager )
	pygameView = PygameView( evManager )
	game = Game( evManager )
	
	spinner.Run()

if __name__ == "__main__":
	main()

########NEW FILE########
__FILENAME__ = network

from example1 import *
from twisted.spread import pb

# A list of ALL possible events that a server can send to a client
serverToClientEvents = []
# A list of ALL possible events that a client can send to a server
clientToServerEvents = []

#------------------------------------------------------------------------------
#Mix-In Helper Functions
#------------------------------------------------------------------------------
def MixInClass( origClass, addClass ):
	if addClass not in origClass.__bases__:
		origClass.__bases__ += (addClass,)

#------------------------------------------------------------------------------
def MixInCopyClasses( someClass ):
	MixInClass( someClass, pb.Copyable )
	MixInClass( someClass, pb.RemoteCopy )



#------------------------------------------------------------------------------
class CopyableCharactor:
	def getStateToCopy(self):
		d = self.__dict__.copy()
		del d['evManager']
		d['sector'] = id( self.sector )
		return d
	def setCopyableState(self, stateDict, registry):
		neededObjIDs = []
		success = 1
		if not registry.has_key( stateDict['sector'] ):
			neededObjIDs.append( stateDict['sector'] )
			success = 0
		else:
			self.sector = registry[stateDict['sector']]
		return [success, neededObjIDs]
		

MixInClass( Charactor, CopyableCharactor )

#------------------------------------------------------------------------------
# Copyable Sector is not necessary in this simple example because the sectors
# all get copied over in CopyableMap
#------------------------------------------------------------------------------
#------------------------------------------------------------------------------
#class CopyableSector:
	#def getStateToCopy(self):
		#d = self.__dict__.copy()
		#del d['evManager']
		#d['neighbors'][DIRECTION_UP] = id(d['neighbors'][DIRECTION_UP])
		#d['neighbors'][DIRECTION_DOWN] = id(d['neighbors'][DIRECTION_DOWN])
		#d['neighbors'][DIRECTION_LEFT] = id(d['neighbors'][DIRECTION_LEFT])
		#d['neighbors'][DIRECTION_RIGHT] = id(d['neighbors'][DIRECTION_RIGHT])
		#return d
#
	#def setCopyableState(self, stateDict, registry):
		#neededObjIDs = []
		#success = 1
		#if not registry.has_key( stateDict['neighbors'][DIRECTION_UP]):
			#neededObjIDs.append( stateDict['neighbors'][DIRECTION_UP] )
			#success = 0
		#else:
			#self.neighbors[DIRECTION_UP] = registry[stateDict['neighbors'][DIRECTION_UP]]
		#if not registry.has_key( stateDict['neighbors'][DIRECTION_DOWN]):
			#neededObjIDs.append( stateDict['neighbors'][DIRECTION_DOWN] )
			#success = 0
		#else:
			#self.neighbors[DIRECTION_DOWN] = registry[stateDict['neighbors'][DIRECTION_DOWN]]
		#if not registry.has_key( stateDict['neighbors'][DIRECTION_LEFT]):
			#neededObjIDs.append( stateDict['neighbors'][DIRECTION_LEFT] )
			#success = 0
		#else:
			#self.neighbors[DIRECTION_LEFT] = registry[stateDict['neighbors'][DIRECTION_LEFT]]
		#if not registry.has_key( stateDict['neighbors'][DIRECTION_RIGHT]):
			#neededObjIDs.append( stateDict['neighbors'][DIRECTION_RIGHT] )
			#success = 0
		#else:
			#self.neighbors[DIRECTION_RIGHT] = registry[stateDict['neighbors'][DIRECTION_RIGHT]]
#
		#return [success, neededObjIDs]
#
#MixInClass( Sector, CopyableSector )

#------------------------------------------------------------------------------
class CopyableMap:
	def getStateToCopy(self):
		sectorIDList = []
		for sect in self.sectors:
			sectorIDList.append( id(sect) )
		return {'ninegrid':1, 'sectorIDList':sectorIDList}


	def setCopyableState(self, stateDict, registry):
		neededObjIDs = []
		success = 1

		if self.state != Map.STATE_BUILT:
			self.Build()

		i = 0
		for sectID in stateDict['sectorIDList']:
			registry[sectID] = self.sectors[i]
			i += 1

		return [success, neededObjIDs]

MixInClass( Map, CopyableMap )



#------------------------------------------------------------------------------
#------------------------------------------------------------------------------
# For each event class, if it is sendable over the network, we have 
# to Mix In the "copy classes", or make a replacement event class that is 
# copyable

#------------------------------------------------------------------------------
# TickEvent
# Direction: don't send.
#The Tick event happens hundreds of times per second.  If we think we need
#to send it over the network, we should REALLY re-evaluate our design

#------------------------------------------------------------------------------
# QuitEvent
# Direction: Client to Server only
MixInCopyClasses( QuitEvent )
pb.setUnjellyableForClass(QuitEvent, QuitEvent)
clientToServerEvents.append( QuitEvent )

#------------------------------------------------------------------------------
# GameStartRequest
# Direction: Client to Server only
MixInCopyClasses( GameStartRequest )
pb.setUnjellyableForClass(GameStartRequest, GameStartRequest)
clientToServerEvents.append( GameStartRequest )

#------------------------------------------------------------------------------
# CharactorMoveRequest
# Direction: Client to Server only
# this has an additional attribute, direction.  it is an int, so it's safe
MixInCopyClasses( CharactorMoveRequest )
pb.setUnjellyableForClass(CharactorMoveRequest, CharactorMoveRequest)
clientToServerEvents.append( CharactorMoveRequest )


#------------------------------------------------------------------------------
# ServerConnectEvent
# Direction: don't send.
# we don't need to send this over the network.

#------------------------------------------------------------------------------
# ClientConnectEvent
# Direction: don't send.
# we don't need to send this over the network.


#------------------------------------------------------------------------------
# GameStartedEvent
# Direction: Server to Client only
class CopyableGameStartedEvent(pb.Copyable, pb.RemoteCopy):
	def __init__(self, event, registry):
		#self.game = netwrap.WrapInstance(event.game)
		self.name = "Copyable Game Started Event"
		self.gameID =  id(event.game)
		registry[self.gameID] = event.game

pb.setUnjellyableForClass(CopyableGameStartedEvent, CopyableGameStartedEvent)
serverToClientEvents.append( CopyableGameStartedEvent )

#------------------------------------------------------------------------------
# MapBuiltEvent
# Direction: Server to Client only
class CopyableMapBuiltEvent( pb.Copyable, pb.RemoteCopy):
	def __init__(self, event, registry ):
		self.name = "Copyable Map Finished Building Event"
		self.mapID = id( event.map )
		registry[self.mapID] = event.map

pb.setUnjellyableForClass(CopyableMapBuiltEvent, CopyableMapBuiltEvent)
serverToClientEvents.append( CopyableMapBuiltEvent )

#------------------------------------------------------------------------------
# CharactorMoveEvent
# Direction: Server to Client only
class CopyableCharactorMoveEvent( pb.Copyable, pb.RemoteCopy):
	def __init__(self, event, registry ):
		self.name = "Copyable Charactor Move Event"
		self.charactorID = id( event.charactor )
		registry[self.charactorID] = event.charactor

pb.setUnjellyableForClass(CopyableCharactorMoveEvent, CopyableCharactorMoveEvent)
serverToClientEvents.append( CopyableCharactorMoveEvent )

#------------------------------------------------------------------------------
# CharactorPlaceEvent
# Direction: Server to Client only
class CopyableCharactorPlaceEvent( pb.Copyable, pb.RemoteCopy):
	def __init__(self, event, registry ):
		self.name = "Copyable Charactor Placement Event"
		self.charactorID = id( event.charactor )
		registry[self.charactorID] = event.charactor

pb.setUnjellyableForClass(CopyableCharactorPlaceEvent, CopyableCharactorPlaceEvent)
serverToClientEvents.append( CopyableCharactorPlaceEvent )



########NEW FILE########
__FILENAME__ = server
#! /usr/bin/env python
'''
Example server
'''

from twisted.spread import pb
from example1 import EventManager, Game
from events import *
import network

#------------------------------------------------------------------------------
class NoTickEventManager(EventManager):
	'''This subclass of EventManager doesn't wait for a Tick event before
	it starts consuming its event queue.  The server module doesn't have
	a CPUSpinnerController, so Ticks will not get generated.
	'''
	def __init__(self):
		EventManager.__init__(self)
		self._lock = False
	def Post(self, event):
		EventManager.Post(self,event)
		if not self._lock:
			self._lock = True
			self.ConsumeEventQueue()
			self._lock = False



#------------------------------------------------------------------------------
class NetworkClientController(pb.Root):
	"""We RECEIVE events from the CLIENT through this object"""
	def __init__(self, evManager, sharedObjectRegistry):
		self.evManager = evManager
		self.evManager.RegisterListener( self )
		self.sharedObjs = sharedObjectRegistry

	#----------------------------------------------------------------------
	def remote_ClientConnect(self, netClient):
		print "CLIENT CONNECT"
		ev = ClientConnectEvent( netClient )
		self.evManager.Post( ev )

	#----------------------------------------------------------------------
	def remote_GetObjectState(self, objectID):
		print "request for object state", objectID
		if not self.sharedObjs.has_key( objectID ):
			return [0,0]
		objDict = self.sharedObjs[objectID].getStateToCopy()
		return [objectID, objDict]
	
	#----------------------------------------------------------------------
	def remote_EventOverNetwork(self, event):
		print "Server just got an EVENT" + str(event)
		self.evManager.Post( event )
		return 1

	#----------------------------------------------------------------------
	def Notify(self, event):
		pass


#------------------------------------------------------------------------------
class NetworkClientView(object):
	"""We SEND events to the CLIENT through this object"""
	def __init__(self, evManager, sharedObjectRegistry):
		self.evManager = evManager
		self.evManager.RegisterListener( self )

		self.clients = []
		self.sharedObjs = sharedObjectRegistry


	#----------------------------------------------------------------------
	def Notify(self, event):
		if isinstance( event, ClientConnectEvent ):
			print '== adding a client', event.client
			self.clients.append( event.client )

		ev = event

		#don't broadcast events that aren't Copyable
		if not isinstance( ev, pb.Copyable ):
			evName = ev.__class__.__name__
			copyableClsName = "Copyable"+evName
			if not hasattr( network, copyableClsName ):
				return
			copyableClass = getattr( network, copyableClsName )
			ev = copyableClass( ev, self.sharedObjs )

		if ev.__class__ not in network.serverToClientEvents:
			print "SERVER NOT SENDING: " +str(ev)
			return

		#NOTE: this is very "chatty".  We could restrict 
		#      the number of clients notified in the future
		for client in self.clients:
			print "=====server sending: ", str(ev)
			remoteCall = client.callRemote("ServerEvent", ev)


#------------------------------------------------------------------------------
class TextLogView(object):
	def __init__(self, evManager):
		self.evManager = evManager
		self.evManager.RegisterListener( self )

	#----------------------------------------------------------------------
	def Notify(self, event):
		if isinstance( event, TickEvent ):
			return

		print 'TEXTLOG <',
		
		if isinstance( event, CharactorPlaceEvent ):
			print event.name, " at ", event.charactor.sector

		elif isinstance( event, CharactorMoveEvent ):
			print event.name, " to ", event.charactor.sector


		
#------------------------------------------------------------------------------
def main():
	evManager = NoTickEventManager()
	sharedObjectRegistry = {}

	log = TextLogView( evManager )
	clientController = NetworkClientController( evManager, sharedObjectRegistry )
	clientView = NetworkClientView( evManager, sharedObjectRegistry )
	game = Game( evManager )

	from twisted.internet import reactor
	reactor.listenTCP( 8000, pb.PBServerFactory(clientController) )

	reactor.run()

if __name__ == "__main__":
	main()

########NEW FILE########
__FILENAME__ = server1
#! /usr/bin/env python
'''
Example server
'''

from twisted.spread import pb

def Debug( msg ):
	return
	#print msg

DIRECTION_UP = 0
DIRECTION_RIGHT = 1
DIRECTION_LEFT = 2
DIRECTION_DOWN = 3

class Event:
	"""this is a superclass for any events that might be generated by an
	object and sent to the EventManager"""
	def __init__(self):
		self.name = "Generic Event"

class TickEvent(Event):
	def __init__(self):
		self.name = "CPU Tick Event"

class QuitEvent(Event):
	def __init__(self):
		self.name = "Program Quit Event"

class MapBuiltEvent(Event):
	def __init__(self, gameMap):
		self.name = "Map Finished Building Event"
		self.map = gameMap

class GameStartRequest(Event):
	def __init__(self):
		self.name = "Game Start Request"

class GameStartedEvent(Event):
	def __init__(self, game):
		self.name = "Game Started Event"
		self.game = game

class CharactorMoveRequest(Event):
	def __init__(self, direction):
		self.name = "Charactor Move Request"
		self.direction = direction

class CharactorPlaceEvent(Event):
	"""this event occurs when a Charactor is *placed* in a sector,
	ie it doesn't move there from an adjacent sector."""
	def __init__(self, charactor):
		self.name = "Charactor Placement Event"
		self.charactor = charactor

class CharactorMoveEvent(Event):
	def __init__(self, charactor):
		self.name = "Charactor Move Event"
		self.charactor = charactor

#------------------------------------------------------------------------------
class EventManager:
	"""this object is responsible for coordinating most communication
	between the Model, View, and Controller."""
	def __init__(self ):
		from weakref import WeakKeyDictionary
		self.listeners = WeakKeyDictionary()
		self.eventQueue= []

	#----------------------------------------------------------------------
	def RegisterListener( self, listener ):
		self.listeners[ listener ] = 1

	#----------------------------------------------------------------------
	def UnregisterListener( self, listener ):
		if listener in self.listeners:
			del self.listeners[ listener ]
		
	#----------------------------------------------------------------------
	def Notify( self, event ):
		if not isinstance(event, TickEvent):
	                Debug( "     Message: " + event.name )
		for listener in self.listeners:
			#NOTE: If the weakref has died, it will be
			#automatically removed, so we don't have 
			#to worry about it.
			listener.Notify( event )


#------------------------------------------------------------------------------
class NetworkClientController(pb.Root):
	"""We RECEIVE events from the CLIENT through this object"""
	def __init__(self, evManager):
		self.evManager = evManager
		self.evManager.RegisterListener( self )

	#----------------------------------------------------------------------
	def remote_GameStartRequest(self):
		ev = GameStartRequest( )
		self.evManager.Notify( ev )
		return 1

	#----------------------------------------------------------------------
	def remote_CharactorMoveRequest(self, direction):
		ev = CharactorMoveRequest( direction )
		self.evManager.Notify( ev )
		return 1

	#----------------------------------------------------------------------
	def Notify(self, event):
		pass


#------------------------------------------------------------------------------
class TextLogView:
	"""..."""
	def __init__(self, evManager):
		self.evManager = evManager
		self.evManager.RegisterListener( self )


	#----------------------------------------------------------------------
	def Notify(self, event):

		if isinstance( event, CharactorPlaceEvent ):
			print event.name, " at ", event.charactor.sector

		elif isinstance( event, CharactorMoveEvent ):
			print event.name, " to ", event.charactor.sector

		elif not isinstance( event, TickEvent ):
			print event.name

#------------------------------------------------------------------------------
class Game:
	"""..."""

	STATE_PREPARING = 0
	STATE_RUNNING = 1
	STATE_PAUSED = 2

	#----------------------------------------------------------------------
	def __init__(self, evManager):
		self.evManager = evManager
		self.evManager.RegisterListener( self )

		self.state = Game.STATE_PREPARING
		
		self.players = [ Player(evManager) ]
		self.map = Map( evManager )

	#----------------------------------------------------------------------
	def Start(self):
		self.map.Build()
		self.state = Game.STATE_RUNNING
		ev = GameStartedEvent( self )
		self.evManager.Notify( ev )

	#----------------------------------------------------------------------
	def Notify(self, event):
		if isinstance( event, GameStartRequest ):
			if self.state == Game.STATE_PREPARING:
				self.Start()

#------------------------------------------------------------------------------
class Player:
	"""..."""
	def __init__(self, evManager):
		self.evManager = evManager
		#self.evManager.RegisterListener( self )

		self.charactors = [ Charactor(evManager) ]

#------------------------------------------------------------------------------
class Charactor:
	"""..."""

	STATE_INACTIVE = 0
	STATE_ACTIVE = 1

	def __init__(self, evManager):
		self.evManager = evManager
		self.evManager.RegisterListener( self )
		self.sector = None
		self.state = Charactor.STATE_INACTIVE

	#----------------------------------------------------------------------
	def Move(self, direction):
		if self.state == Charactor.STATE_INACTIVE:
			return

		if self.sector.MovePossible( direction ):
			newSector = self.sector.neighbors[direction]
			self.sector = newSector
			ev = CharactorMoveEvent( self )
			self.evManager.Notify( ev )

	#----------------------------------------------------------------------
	def Place(self, sector):
		self.sector = sector
		ev = CharactorPlaceEvent( self )
		self.evManager.Notify( ev )

	#----------------------------------------------------------------------
	def Notify(self, event):
		if isinstance( event, GameStartedEvent ):
			gameMap = event.game.map
			self.Place( gameMap.sectors[gameMap.startSectorIndex] )
			self.state = Charactor.STATE_ACTIVE

		elif isinstance( event, CharactorMoveRequest ):
			self.Move( event.direction )

#------------------------------------------------------------------------------
class Map:
	"""..."""
	def __init__(self, evManager):
		self.evManager = evManager
		#self.evManager.RegisterListener( self )

		self.sectors = range(9)
		self.startSectorIndex = 0

	#----------------------------------------------------------------------
	def Build(self):
		for i in range(9):
			self.sectors[i] = Sector( self.evManager )

		self.sectors[3].neighbors[DIRECTION_UP] = self.sectors[0]
		self.sectors[4].neighbors[DIRECTION_UP] = self.sectors[1]
		self.sectors[5].neighbors[DIRECTION_UP] = self.sectors[2]
		self.sectors[6].neighbors[DIRECTION_UP] = self.sectors[3]
		self.sectors[7].neighbors[DIRECTION_UP] = self.sectors[4]
		self.sectors[8].neighbors[DIRECTION_UP] = self.sectors[5]

		self.sectors[0].neighbors[DIRECTION_RIGHT] = self.sectors[1]
		self.sectors[1].neighbors[DIRECTION_RIGHT] = self.sectors[2]
		self.sectors[3].neighbors[DIRECTION_RIGHT] = self.sectors[4]
		self.sectors[4].neighbors[DIRECTION_RIGHT] = self.sectors[5]
		self.sectors[6].neighbors[DIRECTION_RIGHT] = self.sectors[7]
		self.sectors[7].neighbors[DIRECTION_RIGHT] = self.sectors[8]

		self.sectors[0].neighbors[DIRECTION_DOWN] = self.sectors[3]
		self.sectors[1].neighbors[DIRECTION_DOWN] = self.sectors[4]
		self.sectors[2].neighbors[DIRECTION_DOWN] = self.sectors[5]
		self.sectors[3].neighbors[DIRECTION_DOWN] = self.sectors[6]
		self.sectors[4].neighbors[DIRECTION_DOWN] = self.sectors[7]
		self.sectors[5].neighbors[DIRECTION_DOWN] = self.sectors[8]

		self.sectors[1].neighbors[DIRECTION_LEFT] = self.sectors[0]
		self.sectors[2].neighbors[DIRECTION_LEFT] = self.sectors[1]
		self.sectors[4].neighbors[DIRECTION_LEFT] = self.sectors[3]
		self.sectors[5].neighbors[DIRECTION_LEFT] = self.sectors[4]
		self.sectors[7].neighbors[DIRECTION_LEFT] = self.sectors[6]
		self.sectors[8].neighbors[DIRECTION_LEFT] = self.sectors[7]

		ev = MapBuiltEvent( self )
		self.evManager.Notify( ev )

#------------------------------------------------------------------------------
class Sector:
	"""..."""
	def __init__(self, evManager):
		self.evManager = evManager
		#self.evManager.RegisterListener( self )

		self.neighbors = range(4)

		self.neighbors[DIRECTION_UP] = None
		self.neighbors[DIRECTION_RIGHT] = None
		self.neighbors[DIRECTION_DOWN] = None
		self.neighbors[DIRECTION_LEFT] = None

	#----------------------------------------------------------------------
	def MovePossible(self, direction):
		if self.neighbors[direction]:
			return 1


		
#------------------------------------------------------------------------------
def main():
	"""..."""
	evManager = EventManager()

	log = TextLogView( evManager )
	clientController = NetworkClientController( evManager )
	game = Game( evManager )
	
	from twisted.internet import reactor

	reactor.listenTCP( 8000, pb.PBServerFactory(clientController) )

	reactor.run()

if __name__ == "__main__":
	main()

########NEW FILE########
__FILENAME__ = make
#! /usr/bin/env python
import os
s = os.system

def create_table_of_contents():
    s('egrep "<h1|<h2" writing-games.html > /tmp/table.html')
    s('''sed -i 's/name=./href="writing-games.html#/g' /tmp/table.html''')

    fp = file('table.html', 'w')
    fp.write('''\
    <html>
    <head>
    <style>
    h1 {
            font-size: small;
    }
    h2 {
            font-size: smaller;
            text-indent: 4em;
    }
    h3 {
            font-size: normal;
            text-indent: 8em;
    }
    </style>
    </head>
    <body>
    ''')
    fp.close()
    s('cat /tmp/table.html >> ./table.html')


def create_targz_from_example(name):
    targen = ('git checkout %(name)s; '
              'cp -a code_examples %(name)s; '
              'tar -cv --exclude-vcs %(name)s > %(name)s.tar; '
              'rm -rf /tmp/%(name)s; '
              'mv %(name)s /tmp/%(name)s; '
              'gzip %(name)s.tar; '
             )
    s(targen % {'name': name})

create_table_of_contents()
create_targz_from_example('example2')
create_targz_from_example('example3')
create_targz_from_example('example4')

print 'Setting git branch to *master*'
s('git checkout master')

# always append a '/' on the src directory when rsyncing
s('rsync -r ./ $DREAMHOST_USERNAME@ezide.com:/home/$DREAMHOST_USERNAME/ezide.com/games')

########NEW FILE########
__FILENAME__ = make_chapter
import os, sys
import re
import cgi

def parse(c):
    start_code = '----'
    end_code = '----'

    prompt_aside = '[ASIDE]'
    start_aside = '['
    end_aside = ']'

    pState = 'out'
    codeState = 'out'
    asideState = 'out'
    listState = 'out'
    promptState = None

    lines = c.splitlines()

    sections = []
    currentPara = ''
    currentCode = ''
    currentAside = ''
    currentList = ''

    for line in lines:
        sline = line.strip()
        if pState == 'in':
            if sline in ['', start_code, start_aside, prompt_aside]:
                pState = 'out'
                if currentPara:
                    sections.append(('p', currentPara))
            else:
                currentPara += ' ' + sline
        else:
            if (not (codeState == 'in'
                    or asideState == 'in'
                    or listState == 'in')
               and sline not in ['', start_code, start_aside, prompt_aside]):
                pState = 'in'
                currentPara = sline

        if codeState == 'in':
            if sline == end_code:
                codeState = 'out'
                if currentCode:
                    sections.append(('code', currentCode))
            else:
                currentCode += line + '\n'
        else:
            if sline == start_code:
                codeState = 'in'
                currentCode = ''

        if asideState == 'in':
            if sline == end_aside:
                asideState = 'out'
                if currentAside:
                    aside = parse(currentAside)
                    sections.append(('aside', aside))
            else:
                currentAside += line + '\n'
        else:
            if sline == start_aside:
                asideState = 'in'
                currentAside = ''

    # clean up at the EOF
    if pState == 'in':
        if currentPara:
            sections.append(('p', currentPara))

    if codeState == 'in':
        if currentCode:
            sections.append(('code', currentCode))

    if asideState == 'in':
        if currentAside:
            aside = parse(currentAside)
            sections.append(('aside', aside))

    return sections

def render_dumb_html(sections):
    for sect in sections:
        if sect[0] == 'p':
            print '<p>'
            print sect[1]
            print '</p>'
        elif sect[0] == 'code':
            print '<pre>'
            print sect[1]
            print '</pre>'
        elif sect[0] == 'aside':
            print '<blockquote>'
            render_dumb_html(sect[1])
            print '</blockquote>'

def render_fodt(sections):
    fp = file('fodt_head.txt')
    c = fp.read()
    fp.close()
    write = sys.stdout.write
    write(c + '\n')
    def highlight_author_notes(text):
        s = '<text:span text:style-name="red_text">'
        e = '</text:span>'
        start_todo = text.find('[TODO')
        if start_todo == -1:
            return text
        end_todo = text.find(']', start_todo)
        text = (text[:start_todo] + s +
                text[start_todo:end_todo+1]
                + e + text[end_todo+1:])
        return text

    def render_sections(sections, paraStyle="Body"):
        for sect in sections:
            if sect[0] == 'p':
                body = sect[1]
                body = cgi.escape(body)
                body = highlight_author_notes(body)
                write('<text:p text:style-name="%s">' % paraStyle)
                write(body)
                write('</text:p>\n')
            elif sect[0] == 'code':
                body = sect[1]
                body = cgi.escape(body)
                for line in body.splitlines():
                    result = re.split('\S', line, 1)
                    if len(result) > 1:
                        spaces = result[0]
                    else:
                        spaces = ''
                    write('<text:p text:style-name="CodeB">')
                    write('<text:s text:c="%d"/>' % len(spaces))
                    write(line[len(spaces):])
                    write('</text:p>\n')
            elif sect[0] == 'aside':
                #write('<text:p text:style-name="Note">')
                write('\n')
                render_sections(sect[1], 'Note')
                write('\n')
                #write('</text:p>\n')
    render_sections(sections)
    fp = file('fodt_tail.txt')
    c = fp.read()
    fp.close()
    write(c + '\n')


def main():
    chfile = sys.argv[1]
    chfile = file(chfile)
    chapter = chfile.read()
    chfile.close()

    sections = parse(chapter)
    #render_dumb_html(sections)
    render_fodt(sections)

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = multi_controller_test
import pygame
from twisted.internet.selectreactor import SelectReactor
from twisted.spread import pb
from twisted.internet.main import installReactor
import pygame_test
import time

FRAMES_PER_SECOND = 4

class ReactorController(SelectReactor):
    def __init__(self):
        SelectReactor.__init__(self)
        connection = self.connectTCP('localhost', 8000, factory)
        pygame_test.prepare()
        installReactor(self)

    def doIteration(self, delay):
        print 'calling doIteration'
        SelectReactor.doIteration(self,delay)
        retval = pygame_test.iterate()
        if retval == False:
            thingInControl.stop()
            
        

class ReactorSlaveController(object):
    def __init__(self):
        self.keepGoing = True
        self.reactor = SelectReactor()
        installReactor(self.reactor)
        connection = self.reactor.connectTCP('localhost', 8000, factory)
        self.reactor.startRunning()
        self.futureCall = None
        self.futureCallTimeout = None
        pygame_test.prepare()
        
    def iterate(self):
        print 'in iterate'
        self.reactor.runUntilCurrent()
        self.reactor.doIteration(0)
        #t2 = self.reactor.timeout()
        #print 'timeout', t2
        #t = self.reactor.running and t2
        #self.reactor.doIteration(t)

    def run(self):
	clock = pygame.time.Clock()
        self.reactor.callLater(20, stupidTest)
        while self.keepGoing:
            timeChange = clock.tick(FRAMES_PER_SECOND)
            if self.futureCall:
                self.futureCallTimeout -= timeChange
                print 'future call in', self.futureCallTimeout
                if self.futureCallTimeout <= 0:
                    self.futureCall()
                    self.futureCallTimeout = None
                    self.futureCall= None
            retval = pygame_test.iterate()
            if retval == False:
                thingInControl.stop()
            self.iterate()

    def stop(self):
        print 'stopping'
        self.reactor.stop()
        self.keepGoing = False

    def callLater(self, when, fn):
        self.futureCallTimeout = when*1000
        self.futureCall = fn
        print 'future call in', self.futureCallTimeout


class LoopingCallController(object):
    def __init__(self):
        from twisted.internet import reactor
        from twisted.internet.task import LoopingCall
        self.reactor = reactor
        connection = self.reactor.connectTCP('localhost', 8000, factory)
        self.loopingCall = LoopingCall(self.iterate)
        pygame_test.prepare()

    def iterate(self):
        print 'looping call controller in iterate'
        retval = pygame_test.iterate()
        if retval == False:
            thingInControl.stop()

    def run(self):
        interval = 1.0 / FRAMES_PER_SECOND
        self.loopingCall.start(interval)
        self.reactor.run()

    def stop(self):
        self.reactor.stop()

    def callLater(self, when, fn):
        self.reactor.callLater(when, fn)

def stupidTest():
    print 'stupid test!'

server = None
def gotServer(serv):
    print '-'*79
    print 'got server', serv
    global server
    server = serv
    # stop in exactly 5 seconds
    thingInControl.callLater(65.0, stopLoop)

def stopLoop():
    print '-'*79
    print 'stopping the loop'
    thingInControl.stop()

factory = pb.PBClientFactory()
d = factory.getRootObject()
d.addCallback(gotServer)

import sys
if len(sys.argv) < 2:
    print 'usage: test.py 1|2|3'
    sys.exit(1)
elif sys.argv[1] == '1':
    thingInControl = ReactorController()
elif sys.argv[1] == '2':
    thingInControl = ReactorSlaveController()
else:
    thingInControl = LoopingCallController()

thingInControl.run()

print server

print 'end'

########NEW FILE########
__FILENAME__ = pygame_test
#! /usr/bin/env python
'''
An example of using the collision_resolver module

Pops up a window populated by randomly placed little squares.
You control the big square with the direction keys.
'''

from random import randint
import pygame
from pygame.locals import *

RESOLUTION = (600,400)
green = (5,255,5)
avatar = None
avatarGroup = None
sceen = None
background = None
origBackground = None
screen = None

def main():
    clock = pygame.time.Clock()

    prepare()
    while True:
        clock.tick(2)
        retval = iterate()
        if not retval:
            return

def prepare():
    global screen
    pygame.init()
    screen = pygame.display.set_mode(RESOLUTION)
    Start()

def iterate():
    avatar.moveState[0] = randint(-9,9)
    avatar.moveState[1] = randint(-9,9)

    for ev in pygame.event.get():
        if ev.type == QUIT:
            return False
        if ev.type == KEYDOWN and ev.key == K_ESCAPE:
            return False

    #clear
    avatarGroup.clear( screen, background )

    #update
    avatarGroup.update()

    #draw
    avatarGroup.draw(screen)
    pygame.display.update()

    return True

def Start():
    global avatar, avatarGroup, background, origBackground, screen
    background = pygame.Surface( RESOLUTION )
    off_black = (40,10,0)
    background.fill( off_black )

    # avatar will be a green square in the center of the screen
    avatar = Avatar()

    fixedBackgroundSprites = pygame.sprite.Group()
    for block in GenerateRandomBlocks(30, RESOLUTION):
        if not block.rect.colliderect(avatar.rect):
            fixedBackgroundSprites.add( block )
    fixedBackgroundSprites.draw( background )

    avatar.collidables = fixedBackgroundSprites

    avatarGroup = pygame.sprite.Group()
    avatarGroup.add( avatar )

    screen.blit( background, (0,0) )
    pygame.display.flip()
    origBackground = background.copy()


class Avatar(pygame.sprite.Sprite):
    def __init__(self):
        pygame.sprite.Sprite.__init__(self)
        self.image = pygame.Surface( (100,100) )
        self.image.fill( green )
        self.rect = self.image.get_rect()
        self.rect.center = (RESOLUTION[0]/2, RESOLUTION[1]/2)
        self.moveState = [0,0]
        self.collidables = None

    def update(self):
        if self.moveState[0] or self.moveState[1]:
            screen = pygame.display.get_surface()
            screen.blit( origBackground, (0,0) )
        self.rect.move_ip(*self.moveState)
        
class SimpleSprite(pygame.sprite.Sprite):
    def __init__(self, surface):
        pygame.sprite.Sprite.__init__(self)
        self.image = surface
        self.rect = self.image.get_rect()

def GenerateRandomBlocks( howMany, positionBounds ):
    lowerColorBound = (100,100,100)
    upperColorBound = (200,200,200)

    lowerXBound, lowerYBound = 0,0
    upperXBound, upperYBound = positionBounds

    lowerWidthBound, lowerHeightBound = 30,30
    upperWidthBound, upperHeightBound = 60,60

    for i in range(howMany):
        color = [ randint(lowerColorBound[i],upperColorBound[i])
                  for i in range(3) ]
        pos = [ randint(lowerXBound, upperXBound),
                randint(lowerYBound,upperYBound) ]
        size = [ randint(lowerWidthBound, upperWidthBound),
                 randint(lowerHeightBound, upperHeightBound) ]

        s = SimpleSprite( pygame.Surface(size) )
        s.image.fill( color )
        s.rect.topleft = pos
        yield s
    
if __name__ == '__main__':
    main()

########NEW FILE########
