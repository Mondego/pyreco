__FILENAME__ = animations
try:
    import _path
except NameError:
    pass
import spyral
from spyral.sprite import Sprite
from spyral.animation import Animation, DelayAnimation
from spyral.scene import Scene
import spyral.easing as easing
import math

SIZE = (640, 480)
FONT_SIZE = 42
BG_COLOR = (0, 0, 0)
FG_COLOR = (255, 255, 255)

DELAY = DelayAnimation(1.5)

ANIMATIONS = [
    ('Linear', Animation('x', easing.Linear(0, 600), duration = 3.0)),
    ('QuadraticIn', Animation('x', easing.QuadraticIn(0, 600), duration = 3.0)),
    ('QuadraticOut', Animation('x', easing.QuadraticOut(0, 600), duration = 3.0)),
    ('QuadraticInOut', Animation('x', easing.QuadraticInOut(0, 600), duration = 3.0)),
    ('CubicIn', Animation('x', easing.CubicIn(0, 600), duration = 3.0)),
    ('CubicOut', Animation('x', easing.CubicOut(0, 600), duration = 3.0)),
    ('CubicInOut', Animation('x', easing.CubicInOut(0, 600), duration = 3.0)),
    ('Custom (Using Polar)', Animation('pos', easing.Polar(center = (320, 240),
                                                           radius = lambda theta: 100.0+25.0*math.sin(5.0*theta)),
                                                           duration = 3.0)),
    ('Sine', Animation('x', easing.Sine(amplitude = 100.0), duration=3.0, shift=300)),
    ('Arc', Animation('pos', easing.Arc(center = (320, 240), radius = 100.0, theta_end = 1.4*math.pi))),
    ('Scale', Animation('scale', easing.LinearTuple((1.0, 1.0), (0.0, 2.0)), duration = 3.0)),
    ('Rotate', Animation('angle', easing.Linear(0, 2.0*math.pi), duration = 3.0))
]

class TextSprite(Sprite):
    def __init__(self, scene, font):
        Sprite.__init__(self, scene)
        self.font = font

    def render(self, text):
        self.image = self.font.render(text)

class AnimationExamples(Scene):
    def __init__(self):
        Scene.__init__(self, SIZE)
        bg = spyral.Image(size=SIZE)
        bg.fill(BG_COLOR)
        self.background = bg

        font = spyral.Font(None, FONT_SIZE, FG_COLOR)

        self.title = TextSprite(self, font)
        self.title.anchor = 'center'
        self.title.pos = (SIZE[0] / 2, 30)
        self.title.render("N")

        self.block = Sprite(self)
        self.block.image = spyral.Image(size=(40,40))
        self.block.image.fill(FG_COLOR)
        self.block.y = 300

        self.index = 0

        self.set_animation()

        instructions = TextSprite(self, font)
        instructions.anchor = 'midbottom'
        instructions.x = 320
        instructions.y = 470
        instructions.render("n: next example  p: previous example  q: quit")

        # Register all event handlers
        spyral.event.register('system.quit', spyral.director.quit)
        spyral.event.register('input.keyboard.down.p', self.previous)
        spyral.event.register('input.keyboard.down.n', self.next)
        spyral.event.register('input.keyboard.down.q', spyral.director.quit)
        spyral.event.register('input.keyboard.down.escape', spyral.director.quit)


    def set_animation(self):
        self.title.render(ANIMATIONS[self.index][0])
        self.block.stop_all_animations()
        self.block.y = 300 # Reset the y-coordinate.
        a = ANIMATIONS[self.index][1] + DELAY
        a.loop = True
        self.block.animate(a)

    def next(self):
        self.index += 1
        self.index %= len(ANIMATIONS)
        self.set_animation()

    def previous(self):
        self.index -= 1
        self.index %= len(ANIMATIONS)
        self.set_animation()

if __name__ == "__main__":
    spyral.director.init(SIZE)
    spyral.director.run(scene=AnimationExamples())

########NEW FILE########
__FILENAME__ = collisions
try:
    import _path
except NameError:
    pass
import spyral

SIZE = (640, 480)
BG_COLOR = (0, 0, 0)

class Square(spyral.Sprite):
    def __init__(self, scene, direction, color=(255, 0,0)):
        spyral.Sprite.__init__(self, scene)
        self.image = spyral.Image(size=(16, 16)).fill(color)
        self.direction = direction
        self.anchor = 'center'
        spyral.event.register("director.update", self.update)

    def update(self):
        self.x += self.direction * 4
        if not self.collide_rect(self.scene.rect):
            self.x -= self.direction * 4
            self.flip()

    def flip(self):
        self.direction *= -1

class Game(spyral.Scene):
    def __init__(self):
        spyral.Scene.__init__(self, SIZE)
        self.background = spyral.Image(size=SIZE).fill(BG_COLOR)

        self.left_square = Square(self, 1, (0,255,0))
        self.left_square.pos = self.rect.midleft
        self.right_square = Square(self, -1)
        self.right_square.pos = self.rect.midright

        spyral.event.register("system.quit", spyral.director.quit)
        spyral.event.register("director.update", self.update)

    def update(self):
        # Collision test
        if self.left_square.collide_sprite(self.right_square):
            self.right_square.flip()
            self.left_square.flip()

if __name__ == "__main__":
    spyral.director.init(SIZE) # the director is the manager for your scenes
    spyral.director.run(scene=Game()) # This will run your game. It will not return.

########NEW FILE########
__FILENAME__ = concurrent
try:
    import _path
except NameError:
    pass
import spyral
import time

WIDTH, HEIGHT = 600, 600
SIZE = (WIDTH, HEIGHT)
BG_COLOR = (0, 0, 0)

class DumbObject(spyral.Actor):
    def main(self, delta):
        while True:
            print "Awake!"
            self.wait()

class StupidSprite(spyral.Sprite, spyral.Actor):
    def __init__(self, scene):
        spyral.Sprite.__init__(self, scene)
        spyral.Actor.__init__(self)

        self.image = spyral.Image(size=(10, 10))
        self.image.fill((255, 255, 255))
        self.pos = (0, 0)
        self.anchor = 'center'

    def main(self, delta):
        right = spyral.Animation('x', spyral.easing.Linear(0, 600), duration = 1.0)
        down = spyral.Animation('y', spyral.easing.Linear(0, 600), duration = 1.0)
        left = spyral.Animation('x', spyral.easing.Linear(600, 0), duration = 1.0)
        up = spyral.Animation('y', spyral.easing.Linear(600, 0), duration = 1.0)
        while True:
            self.run_animation(right)
            self.run_animation(down)
            self.run_animation(left)
            self.run_animation(up)

class Game(spyral.Scene):
    def __init__(self):
        spyral.Scene.__init__(self, SIZE)
        self.clock.max_ups = 60.
        bg = spyral.Image(size=SIZE)
        bg.fill(BG_COLOR)
        self.background = bg

        self.counter = DumbObject()

        def add_new_box():
            StupidSprite(self)
        add_new_box()

        spyral.event.register('system.quit', spyral.director.quit)
        spyral.event.register('input.keyboard.down', add_new_box)

if __name__ == "__main__":
    spyral.director.init(SIZE)
    spyral.director.run(scene=Game())

########NEW FILE########
__FILENAME__ = cursors
try:
    import _path
except NameError:
    pass
import pygame
import spyral

SIZE = (640, 480)
BG_COLOR = (0, 128, 64)

# List of cursors from documentation
cursors = ["arrow", "diamond", "x", "left", "right"]

class Game(spyral.Scene):
    """
    A Scene represents a distinct state of your game. They could be menus,
    different subgames, or any other things which are mostly distinct.
    """
    def __init__(self):
        spyral.Scene.__init__(self, SIZE)
        back = spyral.Image(size=SIZE)
        back.fill(BG_COLOR)
        self.background = back
        self.mouse = iter(cursors) # iterator over the cursors!
        spyral.event.register("system.quit", spyral.director.quit)
        spyral.event.register("input.mouse.down.left", self.advance_mouse)
    
    def advance_mouse(self):
        try:
            # Change the cursor
            spyral.mouse.cursor = self.mouse.next()
        except StopIteration, e:
            self.mouse = iter(cursors)

if __name__ == "__main__":
    spyral.director.init(SIZE) # the director is the manager for your scenes
    spyral.director.run(scene=Game()) # This will run your game. It will not return.

########NEW FILE########
__FILENAME__ = events
try:
    import _path
except NameError:
    pass
import pygame
import spyral

resolution = (640, 480)

if __name__ == "__main__":
    spyral.director.init(resolution)

    my_scene = spyral.Scene(resolution)
    my_scene.background = spyral.Image(size=resolution).fill((0,0,0))
    my_sprite = spyral.Sprite(my_scene)
    my_sprite.image = spyral.Image(size=(50,50))

    spyral.event.register("system.quit", spyral.director.quit, scene=my_scene)

    # Can accept the keys directly
    def key_down(key, unicode, mod):
        print key, unicode, mod
    def mouse_down(pos, button):
        print type(pos)
        print pos.x
        print pos, button
    
    # Or maybe none or only some of them!
    def key_down_alt1(key, mod):
        print key, mod
    def mouse_down_alt1():
        print "Clicked"
    
    # Also can accept an "event" parameter instead
    def key_down_alt2(event):
        print event.key, event.unicode, event.mod
    def mouse_down_alt2(event):
        print event.pos, event.button

    # Note that we now need to pass in the scene!
    spyral.event.register("input.keyboard.down", key_down, scene=my_scene)
    spyral.event.register("input.mouse.down", mouse_down, scene=my_scene)

    spyral.director.run(scene=my_scene)

########NEW FILE########
__FILENAME__ = fonts
try:
    import _path
except NameError:
    pass
import spyral

SIZE = (640, 480)
BG_COLOR = (0, 0, 0)

class Text(spyral.Sprite):
    def __init__(self, scene, font, text):
        spyral.Sprite.__init__(self, scene)
        self.image = font.render(text)

class GuidedText(spyral.Sprite):
    def __init__(self, scene, font, text, y):
        spyral.Sprite.__init__(self, scene)
        big_font = spyral.Font(font, 36)
        small_font = spyral.Font(font, 11)
        self.image = big_font.render(text)

        self.anchor = 'center'
        self.pos = scene.rect.center
        self.y = y

        guides = [("baseline", big_font.ascent),
                  ("linesize", big_font.linesize)]
        for name, height in guides:
            self.image.draw_rect((0,0,0),
                                 (0,0),
                                 (self.width, height),
                                 border_width = 1,
                                 anchor= 'topleft')
            guide = Text(scene, small_font, name)
            guide.pos = self.pos
            guide.x += self.width / 2
            guide.y += - self.height / 2 + height
            guide.anchor = 'midleft'

class Game(spyral.Scene):
    """
    A Scene represents a distinct state of your game. They could be menus,
    different subgames, or any other things which are mostly distinct.
    """
    def __init__(self):
        spyral.Scene.__init__(self, SIZE)
        self.background = spyral.Image(size=SIZE).fill((255,255,255))

        text = GuidedText(self, "DejaVuSans.ttf", "ABCDEFGHIJKLM", self.height * 1. / 8)
        text = GuidedText(self, "DejaVuSans.ttf", "NOPQRSTUVWXYZ", self.height * 2. / 8)
        text = GuidedText(self, "DejaVuSans.ttf", "abcdefghijklm", self.height * 3. / 8)
        text = GuidedText(self, "DejaVuSans.ttf", "nopqrstuvwxyz", self.height * 4. / 8)
        text = GuidedText(self, "DejaVuSans.ttf", "1234567890-=,", self.height * 5. / 8)
        text = GuidedText(self, "DejaVuSans.ttf", "!@#$%^&*()_+<", self.height * 6. / 8)
        text = GuidedText(self, "DejaVuSans.ttf", ".>/?;:'\"[{]}|\\~`", self.height * 7. / 8)

        spyral.event.register("system.quit", spyral.director.quit)

if __name__ == "__main__":
    spyral.director.init(SIZE) # the director is the manager for your scenes
    spyral.director.run(scene=Game()) # This will run your game. It will not return.

########NEW FILE########
__FILENAME__ = forms
try:
    import _path
except NameError:
    pass
import spyral
from functools import partial

SIZE = (640, 480)

def make_box(color):
    return spyral.Image(size=(32,32)).fill(color)

class Game(spyral.Scene):
    def __init__(self):
        spyral.Scene.__init__(self)
        self.add_style_function("make_box", make_box)
        self.load_style("style.spys")

        class RegisterForm(spyral.Form):
            name = spyral.widgets.TextInput(100, "Current Name")
            password = spyral.widgets.TextInput(50, "*Pass*")
            remember_me = spyral.widgets.Checkbox()
            togglodyte = spyral.widgets.ToggleButton("Toggle me!")
            okay = spyral.widgets.Button("Okay Button")
        my_form = RegisterForm(self)
        my_form.focus()
        
        # Widgets can be accessed by name.
        my_form.name.pos = (50, 50)

        def test_print(event):
            if event.value == "down":
                print "Pressed!", event.widget.name

        spyral.event.register("system.quit", spyral.director.quit)
        spyral.event.register("form.RegisterForm.okay.changed", test_print)

if __name__ == "__main__":
    spyral.director.init(SIZE) # the director is the manager for your scenes
    spyral.keyboard.repeat = True
    spyral.keyboard.delay = 800
    spyral.keyboard.interval = 50
    spyral.director.run(scene=Game()) # This will run your game. It will not return.

########NEW FILE########
__FILENAME__ = kill
try:
    import _path
except NameError:
    pass
import objgraph
import gc
import types
from weakref import ref as _wref
import pygame
import spyral

SIZE = (640, 480)
BG_COLOR = (0, 0, 0)

first_scene = None
old_sprite = None
class Level2(spyral.Scene):
    def __init__(self):
        spyral.Scene.__init__(self, SIZE)
        self.background = spyral.Image(size=SIZE).fill(BG_COLOR)        
        test = Sprite(self)
        test.image = spyral.Image(size=(32,32)).fill((255, 255, 255))
        test.pos = (32, 32)
        
        spyral.event.register("input.keyboard.down.j", self.check_first)
        spyral.event.register("system.quit", spyral.director.quit)

    def check_first(self):
        global first_scene
        global old_sprite
        #first_scene.clear_all_events()
        gc.collect()
        objgraph.show_backrefs([old_sprite], filename='sprite-old.png', filter= lambda x: not isinstance(x, types.FrameType), extra_ignore = [id(locals()), id(globals())], max_depth=7)
        old_sprite.kill()
        objgraph.show_backrefs([old_sprite], filename='sprite-dead.png', filter= lambda x: not isinstance(x, types.FrameType), extra_ignore = [id(locals()), id(globals())], max_depth=7)


    def advance(self):
        spyral.director.replace(Game())

class Game(spyral.Scene):
    """
    A Scene represents a distinct state of your game. They could be menus,
    different subgames, or any other things which are mostly distinct.
    """
    def __init__(self):
        global first_scene
        global old_sprite
        spyral.Scene.__init__(self, SIZE)
        self.background = spyral.Image(size=SIZE).fill(BG_COLOR)
        first_scene = self

        v_top = spyral.View(self)
        v_bottom = spyral.View(v_top)

        over = spyral.Sprite(v_bottom)
        over.image = spyral.Image(size=(50,50)).fill((255, 0, 0))
        over.should_be_dead = lambda :  10
        old_sprite = over

        self.khan = over.should_be_dead
        spyral.event.register("system.quit", spyral.director.quit)
        spyral.event.register("input.keyboard.down.k", over.should_be_dead)
        spyral.event.register("input.keyboard.down.e", over._get_mask)
        spyral.event.register("input.keyboard.down.j", self.advance)

        objgraph.show_backrefs([old_sprite], filename='sprite-alive.png', filter= lambda x: not isinstance(x, types.FrameType), extra_ignore = [id(locals()), id(globals())], max_depth=7)

    def advance(self):
        spyral.director.push(Level2())

if __name__ == "__main__":
    spyral.director.init(SIZE) # the director is the manager for your scenes
    spyral.director.run(scene=Game()) # This will run your game. It will not return.

########NEW FILE########
__FILENAME__ = killing
try:
    import _path
except NameError:
    pass
import spyral
import random
import objgraph
import types
import gc

SIZE = (640, 480)
BG_COLOR = (0, 0, 0)

def global_simple():
    return 5
def global_bound(param, second, *objs, **obj):
    return lambda : (param, second, objs, obj)

class Game(spyral.Scene):
    """
    A Scene represents a distinct state of your game. They could be menus,
    different subgames, or any other things which are mostly distinct.
    """
    def __init__(self):
        spyral.Scene.__init__(self, SIZE)
        self.background = spyral.Image(size=SIZE).fill(BG_COLOR)

        spyral.event.register("system.quit", spyral.director.quit)
        spyral.event.register("input.keyboard.down.f", self.kill_sprite)
        spyral.event.register("input.keyboard.down.j", self.add_sprite)
        self.test = []
    
    def add_sprite(self):
        k = spyral.Sprite(self)
        k.image = spyral.Image(size=(50,50)).fill((255, 0, 0))
        k.x = random.randint(0, 100)
        k.y = random.randint(0, 100)
        k.gs = global_simple
        k.bb = lambda : spyral.director.quit
        k.gb = global_bound(k.image, k.rect, k, k, p=k.image, j=k)
        spyral.event.register("#.global.simple", k.gs)
        spyral.event.register("#.builtin.bound", k.bb)
        spyral.event.register("#.global.bound", k.gb)
        def local_simple():
            return 5
        def local_bound(obj):
            return lambda : obj
        def local_self():
            return lambda : k
        k.lsi = local_simple
        k.lb = local_bound(k)
        k.lse = local_self
        spyral.event.register("#.local.bound", k.lb)
        spyral.event.register("#.local.self", k.lse)
        spyral.event.register("#.local.simple", k.lsi)
        spyral.event.register("#.class.simple", k.kill)
        self.test.append(k)
        print "B", len(self._handlers)
        for name, handlers in self._handlers.iteritems():
            print "B", name, [h[0] for h in handlers]
        print "*" * 10
        #print "ADD", len(gc.get_objects())
    def kill_sprite(self):
        k = self.test.pop()
        k.kill()
        print "A", len(self._handlers)
        for name, handlers in self._handlers.iteritems():
            print "A", name, [h[0] for h in handlers]
        spyral.event.unregister("#.local.bound", k.lb)
        spyral.event.unregister("#.local.self", k.lse)
        spyral.event.unregister("#.local.simple", k.lsi)
        spyral.event.unregister("#.global.simple", k.gs)
        spyral.event.unregister("#.global.bound", k.gb)
        spyral.event.unregister("#.builtin.bound", k.bb)
        print "C", len(self._handlers)
        for name, handlers in self._handlers.iteritems():
            print "C", name, [h[0] for h in handlers]
        #print "KILL", len(gc.get_objects())
        #objgraph.show_backrefs([k], filename='killing-self.png', filter= lambda x: not isinstance(x, types.FrameType), extra_ignore = [id(locals()), id(globals())], max_depth=7)

if __name__ == "__main__":
    spyral.director.init(SIZE) # the director is the manager for your scenes
    spyral.director.run(scene=Game()) # This will run your game. It will not return.

########NEW FILE########
__FILENAME__ = minimal
try:
    import _path
except NameError:
    pass
import spyral

resolution = (640, 480)

# the director is the manager for your scenes
spyral.director.init(resolution)

# A Scene will hold sprites
my_scene = spyral.Scene(resolution)
my_scene.background = spyral.Image(size=resolution).fill((0,0,0))

# A Sprite is the simplest drawable item in Spyral
my_sprite = spyral.Sprite(my_scene)

# A Sprite needs to have an Image
my_sprite.image = spyral.Image(size=(16,16)).fill((255,255,255))

# You register events with functions
# The current scene should be passed in as a named parameter!
spyral.event.register("system.quit", spyral.director.quit, scene=my_scene)

# This will run your game. Execution will stop here until the game ends.
spyral.director.run(scene=my_scene) 
########NEW FILE########
__FILENAME__ = skel
try:
    import _path
except NameError:
    pass
import spyral

SIZE = (640, 480)
BG_COLOR = (0, 0, 0)

class Game(spyral.Scene):
    """
    A Scene represents a distinct state of your game. They could be menus,
    different subgames, or any other things which are mostly distinct.
    """
    def __init__(self):
        spyral.Scene.__init__(self, SIZE)
        self.background = spyral.Image(size=SIZE).fill(BG_COLOR)
        spyral.event.register("system.quit", spyral.director.quit)

if __name__ == "__main__":
    spyral.director.init(SIZE) # the director is the manager for your scenes
    spyral.director.run(scene=Game()) # This will run your game. It will not return.

########NEW FILE########
__FILENAME__ = style
try:
    import _path
except NameError:
    pass
import spyral

class CustomSprite(spyral.Sprite):
    def __init__(self, scene, style):
        self.__style__ = style
        spyral.Sprite.__init__(self, scene)

def make_box(color):
    return spyral.Image(size=(32,32)).fill(color)

class Game(spyral.Scene):
    def __init__(self):
        spyral.Scene.__init__(self)
        self.add_style_function("make_box", make_box)
        self.load_style("style.spys")

        CustomSprite(self, "Red")
        CustomSprite(self, "Blue")
        CustomSprite(self, "Green")

        spyral.event.register("system.quit", spyral.director.quit)


if __name__ == "__main__":
    SIZE = (640+140, 480+120)
    spyral.director.init(SIZE) # the director is the manager for your scenes
    spyral.director.push(Game()) # push means that this Game() instance is
                                 # on the stack to run
    spyral.director.run() # This will run your game. It will not return.

########NEW FILE########
__FILENAME__ = view
try:
    import _path
except NameError:
    pass
import spyral
from spyral.animation import Animation, DelayAnimation
import spyral.easing as easing
import math
import itertools

SIZE = (480, 480)
BG_COLOR = (0, 0, 0)
RED = (255, 0, 0)
YELLOW = (255, 255, 0)
BLUE = (0, 255, 0)
GREEN = (0, 0, 255)
SMALL = (40, 40)

go_down = spyral.Animation('y', easing.Linear(0, 80), duration = 1.0)
go_down += spyral.Animation('y', easing.Linear(80, 0), duration = 1.0)
go_down.loop = True

go_up = spyral.Animation('y', easing.Linear(160, 0), duration = 2.0)
go_left = spyral.Animation('x', easing.Linear(0, 160), duration = 2.0)
go_right = spyral.Animation('x', easing.Linear(160, 0), duration = 2.0)

# Object inside View
# Object shifted by View
# Object cropped by View
# Object scaled by View
# Object shifted and scaled by View
# Object shifted, scaled and cropped by View

# Object <- View <- View <- Scene
# Object <- View (Shifted) <- View <- Scene
# Object <- View (Shifted) <- View (Shifted) <- Scene
# Object <- View (Scaled up) <- View (Scaled up) <- Scene
# Object <- View (Cropped) <- View (Cropped) <- Scene
# Object <- View (Scaled) <- View (Cropped) <- Scene
# Object <- View (Cropped) <- View (Scaled) <- Scene

class Game(spyral.Scene):
    def __init__(self):
        spyral.Scene.__init__(self, SIZE)
        self.background = spyral.Image(size=SIZE).fill(BG_COLOR)
        screen = self.rect

        debug = spyral.DebugText(self, "1) Red square in middle of room", BLUE)
        debug.anchor = 'midbottom'
        debug.pos = self.rect.midbottom

        self.top_view = spyral.View(self)
        self.top_view.label = "TopV"
        self.top_view.pos = (0, 0)
        # TODO: To see it flip out, try commenting out the next line.
        self.top_view.crop = False
        self.top_view.crop_size = (40, 40)

        self.bottom_view = spyral.View(self.top_view)
        self.bottom_view.label = "BottomV"
        self.bottom_view.pos = (0,0)
        self.bottom_view.crop = False
        self.bottom_view.crop_size = (20, 20)

        self.red_block = spyral.Sprite(self.bottom_view)
        self.red_block.image = spyral.Image(size=SMALL).fill(RED)
        self.red_block.pos = screen.center
        self.red_block.anchor = "center"

        def tester():
            debug.text = "2) Red square partially offscreen"
            self.red_block.pos = screen.midtop
            yield
            debug.text = "3) Red square doubled in size"
            self.red_block.pos = screen.center
            self.red_block.scale = 2
            yield
            debug.text = "4) Red square angled .1 radians"
            self.red_block.angle = .1
            yield
            debug.text = "5) Red square shifted by bottom view 16px diagonal"
            self.bottom_view.pos = (16, 16)
            yield
            debug.text = "6) Red square half scaled by bottom view"
            self.bottom_view.scale = .5
            yield
            debug.text = "7) Red square doubled by top view"
            self.top_view.scale = 2
            yield
            debug.text = "8) Red square shifted by top view in other direction 8x"
            self.top_view.pos = (-8, -8)
            yield
            debug.text = "9) Bottom view cropping 16x16 pixels, no scaling"
            self.red_block.scale = 1
            self.bottom_view.scale = 1
            self.top_view.scale = 1
            self.bottom_view.crop = True
            self.bottom_view.crop_size = (16, 16)
            yield
            debug.text = "9) Top view cropping 16x16 pixels, no bottom crop"
            self.bottom_view.crop = False
            self.top_view.crop = True
            self.top_view.crop_size = (16, 16)
            yield
            debug.text = "9) Top crops 20px, bottom crops 10px"
            self.bottom_view.crop = True
            self.top_view.crop = True
            self.bottom_view.crop_size = (10, 10)
            self.top_view.crop_size = (20, 20)
            yield
            debug.text = "9) Top crops 10px, bottom crops 20px"
            self.bottom_view.crop_size = (20, 20)
            self.top_view.crop_size = (10, 10)
            yield

        def key_down(event):
            self.top_view.crop_height += 10
        def key_up(event):
            self.top_view.crop_height -= 10
        def key_left(event):
            self.top_view.crop_width -= 10
        def key_right(event):
            self.top_view.crop_width += 10
        def notify(event):
            pass
            #print self.blue_block.x

        spyral.event.register("input.keyboard.down.down", key_down)
        spyral.event.register("input.keyboard.down.up", key_up)
        spyral.event.register("input.keyboard.down.left", key_left)
        spyral.event.register("input.keyboard.down.right", key_right)
        tests = tester()
        def next_test():
            try:
                next(tests)
            except StopIteration:
                spyral.director.quit()
        spyral.event.register("input.keyboard.down.space", next_test)
        #self.register("director.update", )
        spyral.event.register("system.quit", spyral.director.quit)

if __name__ == "__main__":
    spyral.director.init(SIZE)
    spyral.director.run(scene=Game())

########NEW FILE########
__FILENAME__ = _path
import sys
import os
sys.path.insert(0, os.path.abspath('..'))
########NEW FILE########
__FILENAME__ = actor
"""Actors are tools for rapidly adding multiprocessing behavior to your game."""

import greenlet
import spyral

class Actor(object):
    """
    Actors are a powerful mechanism for quickly adding multiprocessing behavior
    to your game through `Greenlets <http://greenlet.readthedocs.org/>`_ .
    Any object that subclasses the Actor
    mixin can implement a `main` method that will run concurrently. You can put
    a non-terminating loop into it, and it will work like magic, allowing
    other actors and the main game itself to keep processing::
    
        class MyActor(spyral.Actor):
            def main(self, delta):
                while True:
                    print "Acting!"
                    
    When an instance of the above class is created in a scene, it will
    continuously print "Acting!" until the scene ends. Like a Sprite, An Actor
    belongs to the Scene that was currently active when it was created.
    """
    def __init__(self):
        self._greenlet = greenlet.greenlet(self.main)
        scene = spyral.director.get_scene()
        scene._register_actor(self, self._greenlet)

    def wait(self, delta=0):
        """
        Switches execution from this Actor for *delta* frames to the other
        Actors. Returns the amount of time that this actor was left waiting.

        :param delta: the number of frames(?) to wait.
        :type delta: number
        :rtype: float
        """
        if delta == 0:
            return self._greenlet.parent.switch(True)
        return self._greenlet.parent.switch(delta)

    def run_animation(self, animation):
        """
        Run this animation, without blocking other Actors, until the animation
        completes.
        """
        progress = 0.0
        delta = 0.0
        while progress < animation.duration:
            progress += delta

            if progress > animation.duration:
                extra = progress - animation.duration
                progress = animation.duration
            else:
                extra = 0
            values = animation.evaluate(self, progress)
            for property in animation.properties:
                if property in values:
                    setattr(self, property, values[property])
            delta = self.wait(extra)

    def main(self, delta):
        """
        The main function is executed continuously until either the program
        ends or the main function ends. While the Actor's scene is not on the
        top of the stack, the Actor is paused; it will continue when the Scene
        is back on the top of the Directory's stack.
        
        :param float delta: The amount of time that has passed since this
                            method was last invoked.
        """
        pass

########NEW FILE########
__FILENAME__ = animation
"""Animations interpolate a property between two values over a number of frames.
They can be combined to run at the same time, or directly after each other."""

class Animation(object):
    """
    Creates an animation on *property*, with the specified
    *easing*, to last *duration* in seconds.

    The following example shows a Sprite with an animation that will linearly
    change its 'x' property from 0 to 100 over 2 seconds.::

        from spyral import Sprite, Animation, easing
        ...
        my_sprite = Sprite(my_scene)
        my_animation = Animation('x', easing.Linear(0, 100), 2.0)
        my_sprite.animate(my_animation)

    Animations can be appended one after another with the `+`
    operator, and can be run in parallel with the `&` operator.

    >>> from spyral import Animation, easing
    >>> first  = Animation('x', easing.Linear(0, 100), 2.0)
    >>> second = Animation('y', easing.Linear(0, 100), 2.0)
    # Sequential animations
    >>> right_angle = first + second
    # Parallel animations
    >>> diagonal = first & second

    :param property: The property of the sprite to change (e.g., 'x')
    :type property: :class:`string`
    :param easing: The easing (rate of change) of the property.
    :type easing: :class:`Easing <spyral.Easing>`
    :param duration: How many seconds to play the animation
    :type duration: :class:`float`
    :param absolute: (**Unimplemented?**) Whether to position this relative
                     to the sprite's offset, or to absolutely position it on the
                     screen.
    :type absolute: :class:`boolean`
    :param shift: How much to offset the animation (a number if the property is
                  scalar, a :class:`Vec2D <spyral.Vec2D>` if the property is
                  "pos", and None if there is no offset.
    :type shift: None, a :class:`Vec2D <spyral.Vec2D>`, or a number
    :param loop: Whether to loop indefinitely
    :type loop: :class:`boolean`
    """

    def __init__(self, property,
                 easing,
                 duration=1.0,
                 absolute=True,
                 shift=None,
                 loop=False
                 ):
        # Idea: These easings could be used for camera control
        # at some point. Everything should work pretty much the same.
        self.absolute = absolute
        self.property = property
        self.easing = easing
        self.duration = duration
        self.loop = loop
        self.properties = set((property,))
        self._shift = shift

    def evaluate(self, sprite, progress):
        """
        For a given *sprite*, complete *progress*'s worth of this animation.
        Basically, complete a step of the animation. Returns a dictionary
        representing the changed property and its new value, e.g.:
        :code:`{"x": 100}`. Typically, you will use the sprite's animate function instead of calling
        this directly.

        :param sprite: The Sprite that will be manipulated.
        :type sprite: :class:`Sprite <spyral.Sprite>`
        :param float progress: The amount of progress to make on this animation.
        :rtype: :class:`dict`
        """
        progress = progress / self.duration
        value = self.easing(sprite, progress)
        if self._shift is not None:
            if self.property == 'pos':
                value = (value[0] + self._shift[0],
                         value[1] + self._shift[1])
            else:
                value = value + self._shift
        return {self.property: value}

    def __and__(self, second):
        return MultiAnimation(self, second)

    def __iand__(self, second):
        return MultiAnimation(self, second)

    def __add__(self, second):
        return SequentialAnimation(self, second)

    def __iadd__(self, second):
        return SequentialAnimation(self, second)


class MultiAnimation(Animation):
    """
    Class for creating parallel animation from two other animations.

    This does not respect the absolute setting on individual
    animations. Pass absolute as a keyword argument to change,
    default is True.
    Absolute applies only to numerical properties.

    loop is accepted as a kwarg, default is True if any child
    loops, or False otherwise.
    """
    def __init__(self, *animations, **kwargs):
        self.properties = set()
        self._animations = []
        self.duration = 0
        self.absolute = kwargs.get('absolute', True)
        self.loop = False
        for animation in animations:
            i = animation.properties.intersection(self.properties)
            if i:
                message = "Cannot animate on the same properties twice: %s"
                raise ValueError(message % i)
            self.properties.update(animation.properties)
            self._animations.append(animation)
            self.duration = max(self.duration, animation.duration)
            if animation.loop:
                self.loop = True
        # Ensure we don't clobber on properties
        clobbering_animations = [('scale', set(['scale_x', 'scale_y'])),
                                 ('pos', set(['x', 'y', 'position'])),
                                 ('position', set(['x', 'y', 'pos']))]
        for prop, others in clobbering_animations:
            overlapping_properties = self.properties.intersection(others)
            if prop in self.properties and overlapping_properties:
                message = "Cannot animate on %s and %s in the same animation."
                raise ValueError(message % (prop,
                                            overlapping_properties.pop()))
        self.loop = kwargs.get('loop', self.loop)

    def evaluate(self, sprite, progress):
        res = {}
        for animation in self._animations:
            if progress <= animation.duration:
                res.update(animation.evaluate(sprite, progress))
            else:
                res.update(animation.evaluate(sprite, animation.duration))
        return res


class SequentialAnimation(Animation):
    """
    An animation that represents the input animations in sequence.

    loop is accepted as a kwarg, default is False.

    If the last animation in a SequentialAnimation is set to loop,
    that animation will be looped indefinitely at the end, but not
    the entire SequentialAnimation. If loop is set to true, the
    entire SequentialAnimation will loop indefinitely.
    """
    def __init__(self, *animations, **kwargs):
        self.properties = set()
        self._animations = animations
        self.duration = 0
        self.absolute = True
        self.loop = kwargs.get('loop', False)
        for animation in animations:
            self.properties.update(animation.properties)
            self.duration += animation.duration
            if self.loop and animation.loop:
                raise ValueError("Looping sequential animation with a looping "
                                 "animation anywhere in the sequence "
                                 "is not allowed.")
            if animation.loop and animation is not animations[-1]:
                raise ValueError("Looping animation in the middle of a "
                                 "sequence is not allowed.")
        if animations[-1].loop is True:
            self.loop = self.duration - animations[-1].duration

    def evaluate(self, sprite, progress):
        res = {}
        if progress == self.duration:
            res.update(self._animations[-1].evaluate(sprite,
                       self._animations[-1].duration))
            return res
        i = 0
        while progress > self._animations[i].duration:
            progress -= self._animations[i].duration
            i += 1
        if i > 0:
            res.update(self._animations[i - 1].evaluate(sprite,
                       self._animations[i - 1].duration))
        res.update(self._animations[i].evaluate(sprite, progress))
        return res


class DelayAnimation(Animation):
    """
    Animation which performs no actions. Useful for lining up appended
    and parallel animations so that things run at the right times.
    """
    def __init__(self, duration=1.0):
        self.absolute = False
        self.properties = set([])
        self.duration = duration
        self.loop = False

    def evaluate(self, sprite, progress):
        return {}

########NEW FILE########
__FILENAME__ = clock
"""Clock to manage frame/cpu rate."""

# spyral uses a modified version of this file from Gummworld2
# and Trolls Outta Luckland, and thanks the authors for their great,
# reusable piece of code. It is licensed separately from spyral
# under the LGPLv3 or newer.

# This file is part of Gummworld2.
#
# Gummworld2 is free software: you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Gummworld2 is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with Gummworld2.  If not, see <http://www.gnu.org/licenses/>.


# CREDITS
#
# The inspiration for this module came from Koen Witters's superb article
# "deWiTTERS Game Loop", aka "Constant Game Speed independent of Variable FPS"
# at http://www.koonsolo.com/news/dewitters-gameloop/.
#
# The clock was changed to use a fixed time-step after many discussions with
# DR0ID, and a few readings of
# http://gafferongames.com/game-physics/fix-your-timestep/.
#
# Thanks to Koen Witters, DR0ID, and Glenn Fiedler for sharing.
#
# Pythonated by Gummbum. While the builtin demo requires pygame, the module
# does not. The GameClock class is purely Python and should be compatible with
# other Python-based multi-media and game development libraries.


__version__ = '$Id: gameclock.py$'
__author__ = 'Gummbum, (c) 2011-2012'


__doc__ = """

GameClock is a fixed time-step clock that keeps time in terms of game
time. It will attempt to keep game time close to real time, so if an
interval takes one second of game time then the user experiences one
second of real time. In the worst case where the CPU cannot keep up with
the game load, game time will subjectively take longer but still remain
accurate enough to keep game elements in synchronization.

GameClock manages time in the following ways:

    1.  Register special callback functions that will be run when they
        are due.
    2.  Schedule game logic updates at a constant speed, independent of
        frame rate.
    3.  Schedule frames at capped frames-per-second, or uncapped.
    4.  Invoke a pre-emptive pause callback when paused.
    5.  Schedule miscellaneous items at user-configurable intervals.
    6.  Optionally sleep between schedules to conserve CPU cycles.
    7.  Gracefully handles corner cases.

Note the Python Library docs mention that not all computer platforms'
time functions return time fractions of a second. This module will not
work on such platforms.

USAGE

Callback:

    clock = GameClock(
        update_callback=update_world,
        frame_callback=draw_scene,
        pause_callback=pause_game)
    while 1:
        clock.tick()

Special callbacks can be directly set and cleared at any time:

    clock.update_callback = my_new_update
    clock.frame_callback = my_new_draw
    clock.pause_callback = my_new_pause

    clock.update_callback = None
    clock.frame_callback = None
    clock.pause_callback = None

Scheduling miscellanous callbacks:

    def every_second_of_every_day(dt):
        "..."
    clock.schedule_interval(every_second_of_every_day, 1.0)

The update_callback receives a single DT argument, which is the time-step
in seconds since the last update.

The frame_callback receives a single INTERPOLATION argument, which is the
fractional position in time of the frame within the current update time-
step. It is a float in the range 0.0 to 1.0.

The pause_callback receives no arguments.

User-defined interval callbacks accept at least a DT argument, which is
the scheduled item's interval, and optional user-defined arguments. See
GameClock.schedule_interval.

"""

import time


class _IntervalItem(object):
    """An interval item runs after an elapsed interval."""
    __slots__ = ['func', 'interval', 'lasttime', 'life', 'args']
    def __init__(self, func, interval, curtime, life, args):
        self.func = func
        self.interval = float(interval)
        self.lasttime = curtime
        self.life = life
        self.args = args


class GameClock(object):
    """
    GameClock is an implementation of fixed-timestep clocks used for
    running the game.

    =============== ============
    Attribute       Description
    =============== ============
    get_ticks       The time source for the game. Should support at least
                    subsecond accuracy.
    max_ups         The maximum number of updates per second. The clock
                    will prioritize trying to keep the number of
                    updates per second at this level, at the cost of
                    frames per second
    max_fps         The maximum number of frames per second.
    use_wait        Boolean which represents whether the clock should
                    try to sleep when possible. Setting this to False
                    will give better game performance on lower end
                    hardware, but take more CPU power
    update_callback The function which should be called when for
                    updates
    frame_callback  The function which should be called for frame
                    rendering
    game_time       Virtual elapsed time in milliseconds
    paused          The game time at which the clock was paused
    =============== ============

    In addition to these attributes, the following read-only attributes
    provide some useful metrics on performance of the program.

    =============== ============
    Attribute       Description
    =============== ============
    num_updates     The number of updates run in the current one-second
                    interval
    num_frames      The number of frames run in the current one-second
                    interval
    dt_update       Duration of the previous update
    dt_frame        Duration of the previous update
    cost_of_update  How much real time the update callback takes
    cost_of_frame   How much real time the frame callback takes
    ups             Average number of updates per second over the last
                    five seconds
    fps             Average number of frames per second over the last
                    five seconds
    =============== ============
    """
    def __init__(self,
            max_ups=30,
            max_fps=0,
            use_wait=False,
            time_source=time.time,
            update_callback=None,
            frame_callback=None,
            paused_callback=None):

        # Configurables.
        self.get_ticks = time_source
        self.max_ups = max_ups
        self.max_fps = max_fps
        self.use_wait = use_wait
        self.update_callback = update_callback
        self.frame_callback = frame_callback
        self.paused_callback = paused_callback

        # Time keeping.
        CURRENT_TIME = self.get_ticks()
        self._real_time = CURRENT_TIME
        self._game_time = CURRENT_TIME
        self._last_update = CURRENT_TIME
        self._last_update_real = CURRENT_TIME
        self._next_update = CURRENT_TIME
        self._last_frame = CURRENT_TIME
        self._next_frame = CURRENT_TIME
        self._next_second = CURRENT_TIME
        self._update_ready = False
        self._frame_ready = False
#        self._frame_skip = 0
        self._paused = 0

        # Schedules
        self._need_sort = False
        self._schedules = []
        self._unschedules = []

        # Metrics: update and frame progress counter in the current one-second
        # interval.
        self.num_updates = 0
        self.num_frames = 0
        # Metrics: duration in seconds of the previous update and frame.
        self.dt_update = 0.0
        self.dt_frame = 0.0
        # Metrics: how much real time a callback consumes
        self.cost_of_update = 0.0
        self.cost_of_frame = 0.0
        # Metrics: average updates and frames per second over the last five
        # seconds.
        self.ups = 0.0
        self.fps = 0.0

    @property
    def max_ups(self):
        return self._max_ups
    @max_ups.setter
    def max_ups(self, val):
        self._max_ups = val
        self._update_interval = 1.0 / val

    @property
    def max_fps(self):
        return self._max_fps
    @max_fps.setter
    def max_fps(self, val):
        self._max_fps = val
        self._frame_interval = 1.0 / val if val > 0 else 0

    @property
    def game_time(self):
        return self._game_time
    @property
    def paused(self):
        return self._paused

    @property
    def interpolate(self):
        interp = (self._real_time - self._last_update_real)
        interp = interp / self._update_interval
        return interp if interp <= 1.0 else 1.0

    def tick(self):
        """
        Should be called in a loop, will run and handle timers.
        """
        # Now.
        real_time = self.get_ticks()
        self._real_time = real_time

        # Pre-emptive pause callback.
        if self._paused:
            if self.paused_callback:
                self.paused_callback()
            return

        # Check if update and frame are due.
        update_interval = self._update_interval
        game_time = self._game_time
        if real_time >= self._next_update:
            self.dt_update = real_time - self._last_update_real
            self._last_update_real = real_time
            game_time += update_interval
            self._game_time = game_time
            self._last_update = game_time
            self._next_update = real_time + update_interval
            self.num_updates += 1
            if self.update_callback:
                self._update_ready = True
#ORIG
#        if (real_time + self.cost_of_frame < self._next_update) and
#            (real_time >= self._next_frame):
#            self.dt_frame = real_time - self._last_frame
#            self._last_frame = real_time
#            self._next_frame = real_time + self._frame_interval
#            self.num_frames += 1
#            if self.frame_callback:
#                self._frame_ready = True
#END ORIG
#
#SACRIFICE FRAMES TO MAINTAIN UPDATES
        if real_time >= self._next_frame:
            do_frame = False
            if real_time + self.cost_of_frame <= self._next_update:
                do_frame = True
            elif self._frame_skip > 0:
                do_frame = True
            else:
                self._next_frame = self._next_update
                self._frame_skip += 1
            if do_frame:
                self._frame_skip = 0
                self.dt_frame = real_time - self._last_frame
                self._last_frame = real_time
                self._next_frame = real_time + self._frame_interval
                self.num_frames += 1
                if self.frame_callback:
                    self._frame_ready = True
#END SACRIFICE FRAMES TO MAINTAIN UPDATES
#
        if real_time - self._last_frame >= self._update_interval or (
                real_time + self.cost_of_frame < self._next_update and
                real_time >= self._next_frame):
            self.dt_frame = real_time - self._last_frame
            self._last_frame = real_time
            self._next_frame = real_time + self._frame_interval
            self.num_frames += 1
            if self.frame_callback:
                self._frame_ready = True

        # Check if a schedule is due, and when.
        sched_ready = False
        sched_due = 0
        if self._schedules:
            sched = self._schedules[0]
            sched_due = sched.lasttime + sched.interval
            if real_time >= sched_due:
                sched_ready = True

        # Run schedules if any are due.
        if self._update_ready or sched_ready:
            self._run_schedules()

        # Run the frame callback (moved inline to reduce function calls).
        if self.frame_callback and self._frame_ready:
            get_ticks = self.get_ticks
            ticks = get_ticks()
            self.frame_callback(self.interpolate)
            self.cost_of_frame = get_ticks() - ticks
            self._frame_ready = False

        # Flip metrics counters every second.
        if real_time >= self._next_second:
            self._flip(real_time)

        # Sleep to save CPU.
        if self.use_wait:
            upcoming_events = [
                self._next_frame,
                self._next_update,
                self._next_second,
            ]
            if sched_due != 0:
                upcoming_events.append(sched_due)
            next = reduce(min, upcoming_events)
            ticks = self.get_ticks()
            time_to_sleep = next - ticks
            if time_to_sleep >= 0.002:
                time.sleep(time_to_sleep)

    def pause(self):
        """Pause the clock so that time does not elapse.

        While the clock is paused, no schedules will fire and tick() returns
        immediately without progressing internal counters. Game loops that
        completely rely on the clock will need to take over timekeeping and
        handling events; otherwise, the game will appear to deadlock. There are
        many ways to solve this scenario. For instance, another clock can be
        created and used temporarily, and the original swapped back in and
        resumed when needed.
        """
        self._paused = self.get_ticks()

    def resume(self):
        """Resume the clock from the point that it was paused."""
        real_time = self.get_ticks()
        paused = self._paused
        for item in self._schedules:
            delta = paused - item.lasttime
            item.lasttime = real_time - delta
        self._last_update_real = real_time - (paused - self._last_update_real)
        self._paused = 0
        self._real_time = real_time

    def schedule_interval(self, func, interval, life=0, args=[]):
        """

        Schedule an item to be called back each time an interval elapses.

        While the clock is paused time does not pass.

        | *func*: The callback function.
        | *interval*: The time in seconds (float) between calls.
        | *life*: The number of times the callback will fire, after which the
          schedule will be removed. If the value 0 is specified, the event
          will persist until manually unscheduled.
        | *args*: A list that will be passed to the callback as an unpacked
          sequence, like so: item.func(\*[item.interval]+item.args).

        """
        self.unschedule(func)
        item = _IntervalItem(
            func, interval, self.get_ticks(), life, [interval]+list(args))
        self._schedules.append(item)
        self._need_sort = True

    def unschedule(self, func):
        """Unschedule a managed function."""
        sched = self._schedules
        for item in list(sched):
            if item.func == func:
                sched.remove(item)

    @staticmethod
    def _interval_item_sort_key(item):
        return item.lasttime + item.interval

    def _run_schedules(self):
        get_ticks = self.get_ticks

        # Run the update callback.
        if self.update_callback and self._update_ready:
            t = get_ticks()
            self.update_callback(self.dt_update)
            self.cost_of_update = get_ticks() - t
            self._update_ready = False

        # Run the interval callbacks.
        if self._need_sort:
            self._schedules.sort(key=self._interval_item_sort_key)
            self._need_sort = False
        real_time = self._real_time
        for sched in self._schedules:
            interval = sched.interval
            due = sched.lasttime + interval
            if real_time >= due:
                sched.func(*sched.args)
                sched.lasttime += interval
                need_sort = True
                if sched.life > 0:
                    if sched.life == 1:
                        self._unschedules.append(sched.func)
                        need_sort = False
                    else:
                        sched.life -= 1
                if need_sort:
                    self._need_sort = True
            else:
                break
        if self._unschedules:
            for func in self._unschedules:
                self.unschedule(func)
            del self._unschedules[:]

    def _flip(self, real_time):
        self.ups = self.num_updates
        self.fps = self.num_frames

        self.num_updates = 0
        self.num_frames = 0

        self._last_second = real_time
        self._next_second += 1.0

########NEW FILE########
__FILENAME__ = compat
# We use a patcher here to add some functionality from Python 2.6+ to 2.5
import sys
if sys.version_info[0] == 2 and sys.version_info[1] == 5:
    _property = property

    class property(property):
        """
        Custom class meant to implement Python 2.6+ property functionality into
        Python 2.5.
        """
        def __init__(self, fget, *args, **kwargs):
            self.__doc__ = fget.__doc__
            super(property, self).__init__(fget, *args, **kwargs)

        def setter(self, fset):
            cls_ns = sys._getframe(1).f_locals
            for key, value in cls_ns.iteritems():
                if value == self:
                    propname = key
                    break
            cls_ns[propname] = property(self.fget, fset,
                                        self.fdel, self.__doc__)
            return cls_ns[propname]

    __builtins__['property'] = property

########NEW FILE########
__FILENAME__ = core
"""Core functionality module - e.g., init, quit"""

import spyral
import pygame
import inspect

_inited = False

def _init():
    """
    This is the core Spyral code that is run on startup; not only does it setup
    spyral, but it also sets up pygame.
    """
    global _inited
    if _inited:
        return
    _inited = True
    spyral.event._init()
    spyral._style.init()
    pygame.display.init()
    pygame.font.init()

def _quit():
    """
    Cleanly quits pygame and empties the spyral stack.
    """
    pygame.quit()
    spyral.director._stack = []
    spyral.director._initialized = False
    raise spyral.exceptions.GameEndException("The game has ended correctly.")

def _get_executing_scene():
    """
    Returns the currently executing scene using Python introspection.

    This function should not be used lightly - it requires some dark magic.
    """
    for frame, _, _, _, _, _ in inspect.stack():
        args, _, _, local_data = inspect.getargvalues(frame)
        if len(args) > 0 and args[0] == 'self':
            obj = local_data['self']
            if isinstance(obj, spyral.Scene):
                return obj

########NEW FILE########
__FILENAME__ = debug
"""Various functions and classes meant for prototyping and debugging. These
should never show up in a production game."""

import os
import spyral
import pygame

class DebugText(spyral.Sprite):
    """
    A simple Sprite subclass for rapidly rendering text on the screen.

    :param scene: The parent View or Scene that this will live in.
    :type scene: :class:`View <spyral.View>` or :class:`Scene <spyral.Scene>`
    :param str text: The string that will be rendered.
    :param color: A three-tuple of RGB values ranging from 0-255. Defaults to
                  black (0, 0, 0).
    :type color: A three-tuple.

    .. attribute:: text

        The string that will be rendered. Line breaks ("\\\\n") and other
        special characters will not be rendered correctly. Set-only (as opposed
        to read-only).

    """
    def __init__(self, scene, text, color=(0, 0, 0)):
        spyral.Sprite.__init__(self, scene)
        self._font = spyral.Font(spyral._get_spyral_path() +
                                os.path.join("resources", "fonts",
                                             "DejaVuSans.ttf"),
                                15, color)
        self._render(text)

    def _render(self, text):
        """
        Updates the sprite's image based on the new text.
        :param str text: The string that will be rendered.
        """
        self.image = self._font.render(text)
    # Intentionally impossible to get text; don't rely on it!
    text = property(lambda self: "", _render)

class FPSSprite(spyral.Sprite):
    """
    A simple Sprite subclass for rapidly rendering the current frames-per-second
    and updates-per-second on the screen.

    :param scene: The parent View or Scene that this will live in.
    :type scene: :class:`View <spyral.View>` or :class:`Scene <spyral.Scene>`
    :param color: A three-tuple of RGB values ranging from 0-255. Defaults to
                  black (0, 0, 0).
    :type color: A three-tuple.

    """
    def __init__(self, scene, color):
        spyral.Sprite.__init__(self)
        self._font = spyral.Font(spyral._get_spyral_path() +
                                os.path.join("resources", "fonts",
                                             "DejaVuSans.ttf"),
                                15, color)
        self._render(0, 0)
        self._update_in = 5
        spyral.event.register("director.update", self._update, scene=scene)

    def _render(self, fps, ups):
        """
        Updates the sprite's image based on the current fps/ups.
        :param int fps: The string that will be rendered.
        """
        self.image = self._font.render("%d / %d" % (fps, ups))

    def _update(self):
        """
        Updates the clock with information about the FPS, every 5 seconds.
        """
        self._update_in -= 1
        if self._update_in == 0:
            self._update_in = 5
            clock = self.scene.clock
            self._render(clock.fps, clock.ups)

########NEW FILE########
__FILENAME__ = dev
import spyral
import os

def _get_spyral_path():
    return os.path.dirname(spyral.__file__) + '/'
########NEW FILE########
__FILENAME__ = director
import spyral
import pygame

_initialized = False
_stack = []
_screen = None
_tick = 0
_max_fps = 30
_max_ups = 30

def quit():
    """
    Cleanly quits out of spyral by emptying the stack.
    """
    spyral._quit()

def init(size=(0, 0),
         max_ups=30,
         max_fps=30,
         fullscreen=False,
         caption="My Spyral Game"):
    """
    Initializes the director. This should be called at the very beginning of
    your game.

    :param size: The resolution of the display window. (0,0) uses the screen
                 resolution
    :type size: :class:`Vec2D <spyral.Vec2D>`
    :param max_fps: The maximum number of times that the 
                    :func:`director.render` event will occur per second, i.e.,
                    the number of times your game will be rendered per second.
    :type max_fps: ``int``
    :param max_ups: The maximum number of times that the 
                    :func:`director.update` event will occur per second.
                    This will remain the same, even
                    if fps drops.
    :type max_ups: ``int``
    :param fullscreen: Whether your game should start in fullscreen mode.
    :type fullscreen: ``bool``
    :param caption: The caption that will be displayed in the window.
                    Typically the name of your game.
    :type caption: ``str``
    """
    global _initialized
    global _screen
    global _max_fps
    global _max_ups

    if _initialized:
        print 'Warning: Tried to initialize the director twice. Ignoring.'
    spyral._init()

    flags = 0
    # These flags are going to be managed better or elsewhere later
    resizable = False
    noframe = False

    if resizable:
        flags |= pygame.RESIZABLE
    if noframe:
        flags |= pygame.NOFRAME
    if fullscreen:
        flags |= pygame.FULLSCREEN
    _screen = pygame.display.set_mode(size, flags)

    _initialized = True
    pygame.display.set_caption(caption)

    _max_ups = max_ups
    _max_fps = max_fps

def get_scene():
    """
    Returns the currently running scene; this will be the Scene on the top of
    the director's stack.

    :rtype: :class:`Scene <spyral.Scene>`
    :returns: The currently running Scene, or `None`.
    """
    try:
        return _stack[-1]
    except IndexError:
        return None

def get_tick():
    """
    Returns the current tick number, where ticks happen on each update,
    not on each frame. A tick is a "tick of the clock", and will happen many
    (usually 30) times per second.

    :rtype: int
    :returns: The current number of ticks since the start of the game.
    """
    return _tick

def replace(scene):
    """
    Replace the currently running scene on the stack with *scene*.
    Execution will continue after this is called, so make sure you return;
    otherwise you may find unexpected behavior::

        spyral.director.replace(Scene())
        print "This will be printed!"
        return

    :param scene: The new scene.
    :type scene: :class:`Scene <spyral.Scene>`
    """
    if _stack:
        spyral.event.handle('director.scene.exit', scene=_stack[-1])
        old = _stack.pop()
        spyral.sprite._switch_scene()
    _stack.append(scene)
    spyral.event.handle('director.scene.enter',
                        event=spyral.Event(scene=scene),
                        scene=scene)
    # Empty all events!
    pygame.event.get()

def pop():
    """
    Pop the top scene off the stack, returning control to the next scene
    on the stack. If the stack is empty, the program will quit.
    This does return control, so remember to return immediately after
    calling it.
    """
    if len(_stack) < 1:
        return
    spyral.event.handle('director.scene.exit', scene=_stack[-1])
    scene = _stack.pop()
    spyral.sprite._switch_scene()
    if _stack:
        scene = _stack[-1]
        spyral.event.handle('director.scene.enter', scene=scene)
    else:
        exit(0)
    pygame.event.get()

def push(scene):
    """
    Place *scene* on the top of the stack, and move control to it. This does 
    return control, so remember to return immediately after calling it. 

    :param scene: The new scene.
    :type scene: :class:`Scene <spyral.Scene>`
    """
    if _stack:
        spyral.event.handle('director.scene.exit', scene=_stack[-1])
        old = _stack[-1]
        spyral.sprite._switch_scene()
    _stack.append(scene)
    spyral.event.handle('director.scene.enter', scene=scene)
    # Empty all events!
    pygame.event.get()

def run(sugar=False, profiling=False, scene=None):
    """
    Begins running the game, starting with the scene on top of the stack. You
    can also pass in a *scene* to push that scene on top of the stack. This
    function will run until your game ends, at which point execution will end
    too.

    :param bool sugar: Whether to run the game for Sugar. This is only
                       to the special XO Launcher; it is safe to ignore.
    :param bool profiling: Whether to enable profiling mode, where this function
                           will return on every scene change so that scenes can
                           be profiled independently.
    :param scene: The first scene.
    :type scene: :class:`Scene <spyral.Scene>`
    """
    if scene is not None:
        push(scene)
    if sugar:
        import gtk
    if not _stack:
        return
    old_scene = None
    scene = get_scene()
    clock = scene.clock
    stack = _stack
    try:
        while True:
            scene = stack[-1]
            if scene is not old_scene:
                if profiling and old_scene is not None:
                    return
                clock = scene.clock
                old_scene = scene

                def frame_callback(interpolation):
                    """
                    A closure for handling drawing, which includes forcing the
                    rendering-related events to be fired.
                    """
                    scene._handle_event("director.pre_render")
                    scene._handle_event("director.render")
                    scene._draw()
                    scene._handle_event("director.post_render")

                def update_callback(delta):
                    """
                    A closure for handling events, which includes firing the update
                    related events (e.g., pre_update, update, and post_update).
                    """
                    global _tick
                    if sugar:
                        while gtk.events_pending():
                            gtk.main_iteration()
                    if len(pygame.event.get([pygame.VIDEOEXPOSE])) > 0:
                        scene.redraw()
                        scene._handle_event("director.redraw")

                    scene._event_source.tick()
                    events = scene._event_source.get()
                    for event in events:
                        scene._queue_event(*spyral.event._pygame_to_spyral(event))
                    scene._handle_event("director.pre_update")
                    scene._handle_event("director.update",
                                        spyral.Event(delta=delta))
                    _tick += 1
                    scene._handle_event("director.post_update")
                clock.frame_callback = frame_callback
                clock.update_callback = update_callback
            clock.tick()
    except spyral.exceptions.GameEndException:
        pass

########NEW FILE########
__FILENAME__ = easing
"""
This module provides a set of built-in easings which can be used by any 
game. Additionally, custom easings can be built. An easing should be a 
function (or callable) which takes in a sprite, and a time delta which 
is normalized to [0,1], and returns the state of easing at that time. 
See the source code of this module for some example implementations. 
Built-in easings are stateless, so the same animation can be used many 
times or on many different objects. Custom easings do not have to be 
stateless. 

Visualizations of these easings are available at 
`http://easings.net <http://easings.net>`_ .
"""

import math

def Linear(start=0.0, finish=1.0):
    """
    Linearly increasing: f(x) = x
    """
    def linear_easing(sprite, delta):
        return (finish - start) * (delta) + start
    return linear_easing


def QuadraticIn(start=0.0, finish=1.0):
    """
    Quadratically increasing, starts slower : f(x) = x ^ 2
    """
    def quadratic_easing(sprite, delta):
        return start + (finish - start) * delta * delta
    return quadratic_easing


def QuadraticOut(start=0.0, finish=1.0):
    """
    Quadratically increasing, starts faster : f(x) = 2x - x^2
    """
    def quadratic_out_easing(sprite, delta):
        return start + (finish - start) * (2.0 * delta - delta * delta)
    return quadratic_out_easing


def QuadraticInOut(start=0.0, finish=1.0):
    """
    Quadratically increasing, starts and ends slowly but fast in the middle.
    """
    def quadratic_in_out_easing(sprite, delta):
        delta *= 2
        if delta < 1:
            return start + 0.5 * delta * delta * (finish - start)
        delta -= 1
        return start + (delta - 0.5 * delta * delta + 0.5) * (finish - start)
    return quadratic_in_out_easing


def CubicIn(start=0.0, finish=1.0):
    """
    Cubically increasing, starts very slow : f(x) = x^3
    """
    def cubic_in_easing(sprite, delta):
        return start + (delta * delta * delta) * (finish - start)
    return cubic_in_easing


def CubicOut(start=0.0, finish=1.0):
    """
    Cubically increasing, starts very fast : f(x) = 1 + (x-1)^3
    """
    def cubic_out_easing(sprite, delta):
        delta -= 1.0
        return start + (delta * delta * delta + 1.0) * (finish - start)
    return cubic_out_easing


def CubicInOut(start=0.1, finish=1.0):
    """
    Cubically increasing, starts and ends very slowly but very fast in the
    middle.
    """
    def cubic_in_out_easing(sprite, delta):
        delta *= 2.0
        if delta < 1.0:
            return start + 0.5 * delta * delta * delta * (finish - start)
        delta -= 2.0
        return ((1.0 + 0.5 * delta * delta * delta) *
                (finish - start) +
                2.0 * start)
    return cubic_in_out_easing


def Iterate(items, times=1):
    """
    Iterate over a list of items. This particular easing is very useful
    for creating image animations, e.g.::
    
        walk_images = [spyral.Image('f1.png'), spyral.Image('f2.png'), spyral.Image('f3.png')]
        walking_animation = Animation('image', easing.Iterate(walk_images), 2.0, loop=True)
        my_sprite.animate(walking_animation)
    
    :param list items: A list of items (e.g., a list of
                       :class:`Images <spyral.Image>`).
    :param int times: The number of times to iterate through the list.
    """
    def iterate_easing(sprite, delta):
        # We preturb the result slightly negative so that it ends on
        # the last frame instead of looping back to the first
        i = round(delta * len(items) * times)
        return items[int(i % len(items))]
    return iterate_easing


def Sine(amplitude=1.0, phase=0, end_phase=2.0 * math.pi):
    """
    Depending on the arguments, moves at a different pace according to the sine
    function.
    """
    def sin_easing(sprite, delta):
        return amplitude * math.sin(phase + delta * (2.0 * math.pi - phase))
    return sin_easing


def LinearTuple(start=(0, 0), finish=(0, 0)):
    """
    Linearly increasing, but with two properites instead of one.
    """
    def linear_easing(sprite, delta):
        return ((finish[0] - start[0]) * delta + start[0],
                (finish[1] - start[1]) * delta + start[1])
    return linear_easing


def Arc(center=(0, 0), radius=1, theta_start=0, theta_end=2 * math.pi):
    """
    Increasing according to a circular curve for two properties.
    """
    def arc_easing(sprite, delta):
        theta = (theta_end - theta_start) * delta
        return (center[0] + radius * math.cos(theta),
                center[1] + radius * math.sin(theta))
    return arc_easing


def Polar(center=(0, 0),
          radius=lambda theta: 1.0,
          theta_start=0,
          theta_end=2 * math.pi):
    """
    Similar to an Arc, except the radius should be a function of time.
    """
    def arc_easing(sprite, delta):
        theta = (theta_end - theta_start) * delta
        return (center[0] + radius(theta) * math.cos(theta),
                center[1] + radius(theta) * math.sin(theta))
    return arc_easing

########NEW FILE########
__FILENAME__ = event
"""This module contains functions and classes for creating and issuing events.
For a list of the events that are built into Spyral, check the
:ref:`Event List<ref.events>`.

    .. attribute:: keys

        A special attribute for accessing the constants associated with a given
        key. For instance, ``spyral.keys.down`` and ``spyral.keys.f``. This is
        useful for testing for keyboard events. A complete list of all the key
        constants can be found in the
        :ref:`Keyboard Keys <ref.keys>` appendix.

    .. attribute:: mods

        A special attribute for accessing the constants associated with a given
        mod key. For instance, ``spyral.mods.lshift`` (left shift) and
        ``spyral.mods.ralt`` (Right alt). This is useful for testing for keyboard
        events. A complete list of all the key
        constants can be found in the
        :ref:`Keyboard Modifiers <ref.mods>` appendix.

"""

import pygame
try:
    import json
except ImportError:
    import simplejson as json
import spyral
import os
import random
import base64
from weakmethod import WeakMethod as _wm

def WeakMethod(func):
    try:
        return _wm(func)
    except TypeError:
        return func

_TYPE_TO_ATTRS = None
_TYPE_TO_TYPE = None

class Event(object):
    """
    A class for building for attaching data to an event.
    Keyword arguments will be named attributes of the Event when it is passed
    into :func:`queue <spyral.event.queue>`::

        collision_event = Event(ball=ball, paddle=paddle)
        spyral.event.queue("ball.collides.paddle", collision_event)
    """
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

# This might actually be unused!
_EVENT_NAMES = ['QUIT', 'ACTIVEEVENT', 'KEYDOWN', 'KEYUP', 'MOUSEMOTION',
                'MOUSEBUTTONUP', 'VIDEORESIZE', 'VIDEOEXPOSE', 'USEREVENT',
                'MOUSEBUTTONDOWN']
MOUSE_MAP = ['left', 'middle', 'right', 'scroll_up', 'scroll_down']

def _init():
    """
    Initializes the Event system, which requires mapping the Pygame event
    constants to Spyral strings.
    """
    global _TYPE_TO_ATTRS
    global _TYPE_TO_TYPE

    _TYPE_TO_ATTRS = {
        pygame.QUIT: tuple(),
        pygame.ACTIVEEVENT: ('gain', 'state'),
        pygame.KEYDOWN: ('unicode', 'key', 'mod'),
        pygame.KEYUP: ('key', 'mod'),
        pygame.MOUSEMOTION: ('pos', 'rel', 'buttons'),
        pygame.MOUSEBUTTONUP: ('pos', 'button'),
        pygame.MOUSEBUTTONDOWN: ('pos', 'button'),
        pygame.VIDEORESIZE: ('size', 'w', 'h'),
        pygame.VIDEOEXPOSE: tuple(),
    }
    _TYPE_TO_TYPE = {
        pygame.QUIT: "system.quit",
        pygame.ACTIVEEVENT: "system.focus_change",
        pygame.KEYDOWN: "input.keyboard.down",
        pygame.KEYUP: "input.keyboard.up",
        pygame.MOUSEMOTION: "input.mouse.motion",
        pygame.MOUSEBUTTONUP: "input.mouse.up",
        pygame.MOUSEBUTTONDOWN: "input.mouse.down",
        pygame.VIDEORESIZE: "system.video_resize",
        pygame.VIDEOEXPOSE: "system.video_expose",
    }

def queue(event_name, event=None, scene=None):
    """
    Queues a new event in the system, meaning that it will be run at the next
    available opportunity.

    :param str event_name: The type of event (e.g., ``"system.quit"``,
                           ``"input.mouse.up"``, or ``"pong.score"``.
    :param event: An Event object that holds properties for the event.
    :type event: :class:`Event <spyral.event.Event>`
    :param scene: The scene to queue this event on; if `None` is given, the
                   currently executing scene will be used.
    :type scene: :class:`Scene <spyral.Scene>` or `None`.
    """
    if scene is None:
        scene = spyral._get_executing_scene()
    scene._queue_event(event_name, event)

def handle(event_name, event=None, scene=None):
    """
    Instructs spyral to execute the handlers for this event right now. When you
    have a custom event, this is the function you call to have the event occur.

    :param str event_name: The type of event (e.g., ``"system.quit"``,
                           ``"input.mouse.up"``, or ``"pong.score"``.
    :param event: An Event object that holds properties for the event.
    :type event: :class:`Event <spyral.event.Event>`
    :param scene: The scene to queue this event on; if ``None`` is given, the
                   currently executing scene will be used.
    :type scene: :class:`Scene <spyral.Scene>` or ``None``.
    """
    if scene is None:
        scene = spyral._get_executing_scene()
    scene._handle_event(event_name, event)

def register(event_namespace, handler,
             args=None, kwargs=None, priority=0, scene=None):
    """
    Registers an event `handler` to a namespace. Whenever an event in that
    `event_namespace` is fired, the event `handler` will execute with that
    event.

    :param event_namespace: the namespace of the event, e.g.
                            ``"input.mouse.left.click"`` or ``"pong.score"``.
    :type event_namespace: str
    :param handler: A function that will handle the event. The first
                    argument to the function will be the event.
    :type handler: function
    :param args: any additional arguments that need to be passed in
                 to the handler.
    :type args: sequence
    :param kwargs: any additional keyword arguments that need to be
                   passed into the handler.
    :type kwargs: dict
    :param int priority: the higher the `priority`, the sooner this handler will
                         be called in reaction to the event, relative to the
                         other event handlers registered.
    :param scene: The scene to register this event on; if it is ``None``, then
                  it will be attached to the currently running scene.
    :type scene: :class:`Scene <spyral.Scene>` or ``None``
    """
    if scene is None:
        scene = spyral._get_executing_scene()
    scene._reg_internal(event_namespace, (WeakMethod(handler),),
                        args, kwargs, priority, False)

def register_dynamic(event_namespace, handler_string,
                     args=None, kwargs=None, priority=0, scene=None):
    """
    Similar to :func:`spyral.event.register` function, except that instead
    of passing in a function, you pass in the name of a property of this
    scene that holds a function.

    Example::

        class MyScene(Scene):
            def __init__(self):
                ...
                self.register_dynamic("orc.dies", "future_function")
                ...

    :param str event_namespace: The namespace of the event, e.g.
                                ``"input.mouse.left.click"`` or ``"pong.score"``.
    :param str handler: The name of an attribute on this scene that will hold
                        a function. The first argument to the function will be
                        the event.
    :param args: any additional arguments that need to be passed in
                 to the handler.
    :type args: sequence
    :param kwargs: any additional keyword arguments that need to be
                   passed into the handler.
    :type kwargs: dict
    :param int priority: the higher the `priority`, the sooner this handler will
                         be called in reaction to the event, relative to the
                         other event handlers registered.
    :param scene: The scene to register this event on; if it is ``None``, then
                  it will be attached to the currently running scene.
    :type scene: :class:`Scene <spyral.Scene>` or ``None``
    """
    if scene is None:
        scene = spyral._get_executing_scene()
    scene._reg_internal(event_namespace, (handler_string,),
                        args, kwargs, priority, True)

def register_multiple(event_namespace, handlers, args=None,
                      kwargs=None, priority=0, scene=None):
    """
    Similar to :func:`spyral.event.register` function, except a sequence of
    `handlers` are be given instead of just one.

    :param str event_namespace: the namespace of the event, e.g.
                            ``"input.mouse.left.click"`` or ``"pong.score"``.
    :type event_namespace: string
    :param handler: A list of functions that will be run on this event.
    :type handler: list of functions
    :param args: any additional arguments that need to be passed in
                 to the handler.
    :type args: sequence
    :param kwargs: any additional keyword arguments that need to be
                   passed into the handler.
    :type kwargs: dict
    :param int priority: the higher the `priority`, the sooner this handler will
                         be called in reaction to the event, relative to the
                         other event handlers registered.
    :param scene: The scene to register this event on; if it is ``None``, then
                  it will be attached to the currently running scene.
    :type scene: :class:`Scene <spyral.Scene>` or ``None``
    """
    if scene is None:
        scene = spyral._get_executing_scene()
    scene._reg_internal(event_namespace, map(WeakMethod, handlers),
                        args, kwargs, priority, False)

def register_multiple_dynamic(event_namespace, handler_strings, args=None,
                              kwargs=None, priority=0, scene=None):
    """
    Similar to :func:`spyral.Scene.register` function, except a sequence of
    strings representing handlers can be given instead of just one.

    :param event_namespace: the namespace of the event, e.g.
                            ``"input.mouse.left.click"`` or ``"pong.score"``.
    :type event_namespace: string
    :param handler: A list of names of an attribute on this scene that will
                    hold a function. The first argument to the function will
                    be the event.
    :type handler: list of strings
    :param args: any additional arguments that need to be passed in
                 to the handler.
    :type args: sequence
    :param kwargs: any additional keyword arguments that need to be
                   passed into the handler.
    :type kwargs: dict
    :param int priority: the higher the `priority`, the sooner this handler will
                         be called in reaction to the event, relative to the
                         other event handlers registered.
    :param scene: The scene to register this event on; if it is ``None``, then
                  it will be attached to the currently running scene.
    :type scene: :class:`Scene <spyral.Scene>` or ``None``
    """
    if scene is None:
        scene = spyral._get_executing_scene()
    scene._reg_internal(event_namespace, handler_strings,
                        args, kwargs, priority, True)

def unregister(event_namespace, handler, scene=None):
    """
    Unregisters a registered handler for that namespace. Dynamic handler
    strings are supported as well.

    :param str event_namespace: An event namespace
    :param handler: The handler to unregister.
    :type handler: a function or string.
    :param scene: The scene to unregister the event; if it is ``None``, then
                  it will be attached to the currently running scene.
    :type scene: :class:`Scene <spyral.Scene>` or ``None``
    """
    if scene is None:
        scene = spyral._get_executing_scene()
    scene._unregister(event_namespace, handler)

def clear_namespace(namespace, scene=None):
    """
    Clears all handlers from namespaces that are at least as specific as the
    provided `namespace`.

    :param str namespace: The complete namespace.
    :param scene: The scene to clear the namespace of; if it is ``None``, then
                  it will be attached to the currently running scene.
    :type scene: :class:`Scene <spyral.Scene>` or ``None``
    """
    if scene is None:
        scene = spyral._get_executing_scene()
    scene._clear_namespace(namespace)

def _pygame_to_spyral(event):
    """
    Convert a Pygame event to a Spyral event, correctly converting arguments to
    attributes.
    """
    event_attrs = _TYPE_TO_ATTRS[event.type]
    event_type = _TYPE_TO_TYPE[event.type]
    e = Event()
    for attr in event_attrs:
        setattr(e, attr, getattr(event, attr))
    if event_type.startswith("input"):
        setattr(e, "type", event_type.split(".")[-1])
    if event_type.startswith('input.keyboard'):
        k = keys.reverse_map.get(event.key, 'unknown')
        event_type += '.' + k
    if event_type.startswith('input.mouse.motion'):
        e.left, e.middle, e.right = map(bool, event.buttons)
    elif event_type.startswith('input.mouse'):
        try:
            m = MOUSE_MAP[event.button-1]
            setattr(e, "button", m)
        except IndexError:
            m = str(event.button)
        event_type += '.' + m
    if event_type.startswith('input.mouse'):
        e.pos = spyral.Vec2D(e.pos) / spyral.director.get_scene()._scale
        
    return (event_type, e)

class EventHandler(object):
    """
    Base event handler class.
    """
    def __init__(self):
        self._events = []
        self._mouse_pos = (0, 0)

    def tick(self):
        """
        Should be called at the beginning of update cycle. For the
        event handler which is part of a scene, this function will be
        called automatically. For any additional event handlers, you
        must call this function manually.
        """
        pass

    def get(self, types=[]):
        """
        Gets events from the event handler. Types is an optional
        iterable which has types which you would like to get.
        """
        try:
            types[0]
        except IndexError:
            pass
        except TypeError:
            types = (types,)

        if types == []:
            ret = self._events
            self._events = []
            return ret

        ret = [e for e in self._events if e['type'] in types]
        self._events = [e for e in self._events if e['type'] not in types]
        return ret


class LiveEventHandler(EventHandler):
    """
    An event handler which pulls events from the operating system.

    The optional output_file argument specifies the path to a file
    where the event handler will save a custom json file that can
    be used with the `ReplayEventHandler` to show replays of a
    game in action, or be used for other clever purposes.

    .. note::

        If you use the output_file parameter, this function will
        reseed the random number generator, save the seed used. It
        will then be restored by the ReplayEventHandler.
    """
    def __init__(self, output_file=None):
        EventHandler.__init__(self)
        self._save = output_file is not None
        if self._save:
            self._file = open(output_file, 'w')
            seed = os.urandom(4)
            info = {'random_seed': base64.encodestring(seed)}
            random.seed(seed)
            self._file.write(json.dumps(info) + "\n")

    def tick(self):
        mouse = pygame.mouse.get_pos()
        events = pygame.event.get()
        self._mouse_pos = mouse
        self._events.extend(events)
        # if self._save:
        #     d = {'mouse': mouse, 'events': events}
        #     self._file.write(json.dumps(d) + "\n")

    def __del__(self):
        if self._save:
            self._file.close()


class ReplayEventHandler(EventHandler):
    """
    An event handler which replays the events from a custom json
    file saved by the `LiveEventHandler`.
    """
    def __init__(self, input_file):
        EventHandler.__init__(self)
        self._file = open(input_file)
        info = json.loads(self._file.readline())
        random.seed(base64.decodestring(info['random_seed']))
        self.paused = False

    def pause(self):
        """
        Pauses the replay of the events, making tick() a noop until
        resume is called.
        """
        self.paused = True

    def resume(self):
        """
        Resumes the replay of events.
        """
        self.paused = False

    def tick(self):
        if self.paused:
            return
        try:
            d = json.loads(self._file.readline())
        except ValueError:
            spyral.director.pop()
        events = d['events']
        events = [EventDict(e) for e in events]
        self._mouse_pos = d['mouse']
        self._events.extend(events)

class Mods(object):
    def __init__(self):
        self.none = pygame.KMOD_NONE
        self.lshift = pygame.KMOD_LSHIFT
        self.rshift = pygame.KMOD_RSHIFT
        self.shift = pygame.KMOD_SHIFT
        self.caps = pygame.KMOD_CAPS
        self.ctrl = pygame.KMOD_CTRL
        self.lctrl = pygame.KMOD_LCTRL
        self.rctrl = pygame.KMOD_RCTRL
        self.lalt = pygame.KMOD_LALT
        self.ralt = pygame.KMOD_RALT
        self.alt = pygame.KMOD_ALT

class Keys(object):

    def __init__(self):
        self.reverse_map = {}
        self.load_keys_from_file(spyral._get_spyral_path() +
                                 'resources/default_key_mappings.txt')
        self._fix_bad_names([("return", "enter"),
                             ("break", "brk")])

    def _fix_bad_names(self, renames):
        """
        Used to replace any binding names with non-python keywords.
        """
        for original, new in renames:
            setattr(self, new, getattr(self, original))
            delattr(self, original)


    def load_keys_from_file(self, filename):
        fp = open(filename)
        key_maps = fp.readlines()
        fp.close()
        for single_mapping in key_maps:
            mapping = single_mapping[:-1].split(' ')
            if len(mapping) == 2:
                if mapping[1][0:2] == '0x':
                    setattr(self, mapping[0], int(mapping[1], 16))
                    self.reverse_map[int(mapping[1], 16)] = mapping[0]
                else:
                    setattr(self, mapping[0], int(mapping[1]))
                    self.reverse_map[int(mapping[1])] = mapping[0]

    def add_key_mapping(self, name, number):
        setattr(self, name, number)

keys = Keys()
mods = Mods()

########NEW FILE########
__FILENAME__ = exceptions
"""
This module defines custom exceptions that are thrown throughout spyral.
"""

import warnings

class SceneHasNoSizeError(Exception):
    pass
class NotStylableError(Exception):
    pass
class NoImageError(Exception):
    pass
class BackgroundSizeError(Exception):
    pass
class LayersAlreadySetError(Exception):
    pass
class GameEndException(Exception):
    pass
    
# Warnings
class UnusedStyleWarning(Warning):
    pass
class ActorsNotAvailableWarning(Warning):
    pass


# Convenience Wrappers
def unused_style_warning(obj, properties):
    warnings.warn("%r does not understand style properties %s" %
                  (obj, ','.join(properties)),
                  UnusedStyleWarning)
def actors_not_available_warning():
    warnings.warn("You do not have Greenlets installed, so you cannot use Actors.", ActorsNotAvailableWarning)
########NEW FILE########
__FILENAME__ = font
"""
This module defines Font objects, used for rendering text into Images.
"""

import pygame
from spyral import Image, Vec2D

class _FontImage(Image):
    """
    A wrapper for Images that came from rendering a font. This is necessary
    since the rendering returns a surface, which the Image API is built to hide.

    :param surf: The pygame Surface that will be stored in this _FontImage.
    :type surf: :class:`pygame.Surface`
    """
    def __init__(self, surf):
        self._surf = surf
        self._name = None
        self._version = 1

class Font(object):
    """
    Font objects are how you get text onto the screen. They are loaded from
    TrueType Font files (\*.ttf); system fonts are not supported for asthetic
    reasons. If you need direction on what the different size-related
    properties of a Font object, check out the Font example.

    :param str font_path: The location of the \*.ttf file.
    :param int size: The size of the font; font sizes refer to the height of the
                     font in pixels.
    :param color: A three-tuple of RGB values ranging from 0-255. Defaults to
                  black ``(0, 0, 0)``.
    :type color: A three-tuple.
    """
    def __init__(self, font_path, size, default_color=(0, 0, 0)):
        self.size = int(size)
        self.font = pygame.font.Font(font_path, size)
        self.default_color = default_color

    def render(self, text, color=None, underline=False,
               italic=False, bold=False):
        """
        Renders the given *text*. Italicizing and bolding are artificially
        added, and may not look good for many fonts. It is preferable to load a
        bold or italic font where possible instead of using these options.

        :param str text: The text to render. Some characters might not be able
                         to be rendered (e.g., "\\\\n").
        :param color: A three-tuple of RGB values ranging from 0-255. Defaults
                      to the default Font color.
        :type color: A three-tuple.
        :param bool underline: Whether to underline this text. Note that the
                               line will always be 1 pixel wide, no matter the
                               font size.
        :param bool italic: Whether to artificially italicize this font by
                            angling it.
        :param bool bold: Whether to artificially embolden this font by
                          stretching it.
        :rtype: :class:`Image <spyral.Image>`
        """
        if color is None:
            color = self.default_color
        self.font.set_underline(underline)
        self.font.set_bold(bold)
        self.font.set_italic(italic)
        text_surface = self.font.render(text, True, color).convert_alpha()
        background_surface = pygame.Surface(text_surface.get_size(), pygame.SRCALPHA)
        background_surface.blit(text_surface, (0, 0))

        return _FontImage(background_surface.convert_alpha())

    def _get_height(self):
        return self.font.get_height()
    #: The average height in pixels for each glyph in the font. Read-only.
    height = property(_get_height)

    def _get_ascent(self):
        return self.font.get_ascent()
    #: The height in pixels from the font baseline to the top of the font.
    #: Read-only.
    ascent = property(_get_ascent)

    def _get_descent(self):
        return self.font.get_descent()
    #: The height in pixels from the font baseline to the bottom of the font.
    #: Read-only.
    descent = property(_get_descent)

    def _get_linesize(self):
        return self.font.get_linesize()
    #: The height in pixels for a line of text rendered with the font.
    #: Read-only.
    linesize = property(_get_linesize)

    def get_metrics(self, text):
        """
        Returns a list containing the font metrics for each character
        in the text. The metrics is a tuple containing the
        minimum x offset, maximum x offset, minimum y offset, maximum
        y offset, and the advance offset of the character. ``[(minx, maxx, miny,
        maxy, advance), (minx, maxx, miny, maxy, advance), ...]``

        :param str text: The text to gather metrics on.
        :rtype: `list` of tuples.
        """
        return self.font.get_metrics(text)

    def get_size(self, text):
        """
        Returns the size needed to render the text without actually
        rendering the text. Useful for word-wrapping. Remember to
        keep in mind font kerning may be used.

        :param str text: The text to get the size of.
        :returns: The size (width and height) of the text as it would be
                  rendered.
        :rtype: :class:`Vec2D <spyral.Vec2D>`
        """
        return Vec2D(self.font.size(text))

########NEW FILE########
__FILENAME__ = form
"""This module defines the Form class, a subclass of Views that can manage
widgets."""

import spyral
import operator
import inspect

class _FormFieldMeta(type):
    """
    Black magic for wrapping widgets defined as class attributes. See python
    documentation on overriding Python
    `__metaclass__ <http://docs.python.org/2/reference/datamodel.html#customizing-class-creation>`_
    for more information.
    """
    def __new__(meta, name, bases, dict):
        cls = type.__new__(meta, name, bases, dict)
        is_wrapper = lambda obj: isinstance(obj, spyral.widgets._WidgetWrapper)
        cls.fields = sorted(inspect.getmembers(cls, is_wrapper),
                            key=lambda i: i[1].creation_counter)
        return cls

class Form(spyral.View):
    """
    Forms are a subclass of :class:`Views <spyral.View>` that hold a set of
    :ref:`Widgets <api.widgets>`. Forms will manage focus and event delegation between the widgets,
    ensuring that only one widget is active at a given time. Forms are defined 
    using a special class-based syntax::

        class MyForm(spyral.Form):
            name = spyral.widgets.TextInput(100, "Current Name")
            remember_me = spyral.widgets.Checkbox()
            save = spyral.widgets.ToggleButton("Save")

        my_form = MyForm()

    When referencing widgets in this way, the "Widget" part of the widget's name
    is dropped: ``spyral.widgets.ButtonWidget`` becomes ``spyral.widgets.Button``.
    Every widget in a form is accessible as an attribute of the form:

        >>> print my_form.remember_me.value
        "up"

    :param scene: The Scene or View that this Form belongs to.
    :type scene: :class:`Scene <spyral.Scene>` or :class:`View <spyral.View>`.
    """
    __metaclass__ = _FormFieldMeta

    def __init__(self, scene):
        spyral.View.__init__(self, scene)
        class Fields(object):
            pass

        # Maintain a list of all the widget instances
        self._widgets = []
        # Map each widget instance to its tab order
        self._tab_orders = {}
        # The instance of the currently focused widget
        self._current_focus = None
        # The instance of the currently mouse-overed widget
        self._mouse_currently_over = None
        # The instance of the currently mouse-downed widget
        self._mouse_down_on = None

        spyral.event.register("input.mouse.up.left", self._handle_mouse_up,
                              scene=scene)
        spyral.event.register("input.mouse.down.left", self._handle_mouse_down,
                              scene=scene)
        spyral.event.register("input.mouse.motion", self._handle_mouse_motion,
                              scene=scene)
        spyral.event.register("input.keyboard.down.tab", self._handle_tab,
                              scene=scene)
        spyral.event.register("input.keyboard.up.tab", self._handle_tab,
                              scene=scene)
        spyral.event.register("input.keyboard.up", self._handle_key_up,
                              scene=scene)
        spyral.event.register("input.keyboard.down", self._handle_key_down,
                              scene=scene)

        fields = self.fields
        self.fields = Fields()
        for name, widget in fields:
            w = widget(self, name)
            setattr(w, "name", name)
            setattr(self, name, w)
            self.add_widget(name, w)
        self.focus()

    def _handle_mouse_up(self, event):
        """
        Delegate the mouse being released to the widget that is currently being
        clicked.

        :param event: The associated event data.
        :type event: :class:`Event <spyral.Event>`
        """
        if self._mouse_down_on is None:
            return False
        self._mouse_down_on._handle_mouse_up(event)
        self._mouse_down_on = None

    def _handle_mouse_down(self, event):
        """
        Delegate the mouse being clicked down to any widget that it is currently
        hovering over.

        :param event: The associated event data.
        :type event: :class:`Event <spyral.Event>`
        """
        for widget in self._widgets:
            if widget.collide_point(event.pos):
                self.focus(widget)
                self._mouse_down_on = widget
                widget._handle_mouse_down(event)
                return True
        return False

    def _handle_mouse_motion(self, event):
        """
        Delegate the mouse being hovered over any widget that it is currently
        hovering over. If the widget being hovered over is no longer the
        previous widget that was being hovered over, it notifies the old widget
        (mouse out event) and the new widget (mouse over event).

        :param event: The associated event data.
        :type event: :class:`Event <spyral.Event>`
        """
        if self._mouse_down_on is not None:
            self._mouse_down_on._handle_mouse_motion(event)
        now_hover = None
        for widget in self._widgets:
            if widget.collide_point(event.pos):
                widget._handle_mouse_motion(event)
                now_hover = widget
        if now_hover != self._mouse_currently_over:
            if self._mouse_currently_over is not None:
                self._mouse_currently_over._handle_mouse_out(event)
            self._mouse_currently_over = now_hover
            if now_hover is not None:
                now_hover._handle_mouse_over(event)

    def _handle_tab(self, event):
        """
        If this form has focus, advances to the next widget in the tab order.
        Unless the shift key is held, in which case the previous widget is
        focused.

        :param event: The associated event data.
        :type event: :class:`Event <spyral.Event>`
        """
        if self._current_focus is None:
            return
        if event.type == 'down':
            return True
        if event.mod & spyral.mods.shift:
            self.previous()
            return True
        self.next()
        return True

    def _handle_key_down(self, event):
        """
        Notifies the currently focused widget that a key has been pressed.

        :param event: The associated event data.
        :type event: :class:`Event <spyral.Event>`
        """
        if self._current_focus is not None:
            self._current_focus._handle_key_down(event)

    def _handle_key_up(self, event):
        """
        Notifies the currently focused widget that a key has been released.

        :param event: The associated event data.
        :type event: :class:`Event <spyral.Event>`
        """
        if self._current_focus is not None:
            self._current_focus._handle_key_up(event)


    def add_widget(self, name, widget, tab_order=None):
        """
        Adds a new widget to this form. When this method is used to add a Widget
        to a Form, you create the Widget as you would create a normal Sprite. It
        is preferred to use the class-based method instead of this; consider
        carefully whether you can achieve dynamicity through visibility and
        disabling.

        >>> my_widget = spyral.widgets.ButtonWidget(my_form, "save")
        >>> my_form.add_widget("save", my_widget)

        :param str name: A unique name for this widget.
        :param widget: The new Widget.
        :type widget: :ref:`Widget <api.widgets>`
        :param int tab_order: Sets the tab order for this widget explicitly. If
                              tab-order is None, it is set to one higher than
                              the highest tab order.
        """
        if tab_order is None:
            if len(self._tab_orders) > 0:
                tab_order = max(self._tab_orders.itervalues())+1
            else:
                tab_order = 0
            self._tab_orders[widget] = tab_order
        self._widgets.append(widget)
        #self.add_child(widget)
        setattr(self.fields, name, widget)

    def _get_values(self):
        """
        A dictionary of the values for all the fields, mapping the name
        of each widget with the value associated with that widget. Read-only.
        """
        return dict((widget.name, widget.value) for widget in self._widgets)
    
    values = property(_get_values)
    
    def _blur(self, widget):
        """
        Queues an event indicating that a widget has lost focus.

        :param widget: The widget that is losing focus.
        :type widget: :ref:`Widget <api.widgets>`
        """
        e = spyral.Event(name="blurred", widget=widget, form=self)
        self.scene._queue_event("form.%(form_name)s.%(widget)s.blurred" %
                                    {"form_name": self.__class__.__name__,
                                     "widget": widget.name},
                                e)
        widget._handle_blur(e)

    def focus(self, widget=None):
        """
        Sets the focus to be on a specific widget. Focus by default goes
        to the first widget added to the form.

        :param widget: The widget that is gaining focus; if None, then the first
                       widget gains focus.
        :type widget: :ref:`Widget <api.widgets>`
        """
        # By default, we focus on the first widget added to the form
        if widget is None:
            if not self._widgets:
                return
            widget = min(self._tab_orders.iteritems(),
                         key=operator.itemgetter(1))[0]

        # If we'd focused on something before, we blur it
        if self._current_focus is not None:
            self._blur(self._current_focus)

        # We keep track of our newly focused thing
        self._current_focus = widget

        # Make and send the "focused" event
        e = spyral.Event(name="focused", widget=widget, form=self)
        self.scene._queue_event("form.%(form_name)s.%(widget)s.focused" %
                                    {"form_name": self.__class__.__name__,
                                     "widget": widget.name},
                                e)
        widget._handle_focus(e)
        return

    def blur(self):
        """
        Defocuses the entire form.
        """
        if self._current_focus is not None:
            self._blur(self._current_focus)
            self._current_focus = None

    def next(self, wrap=True):
        """
        Focuses on the next widget in tab order.

        :param bool wrap: Whether to continue to the first widget when the end
                          of the tab order is reached.
        """
        if self._current_focus is None:
            self.focus()
            return
        if not self._widgets:
            return
        cur = self._tab_orders[self._current_focus]
        candidates = [(widget, order) for (widget, order)
                                      in self._tab_orders.iteritems()
                                      if order > cur]
        if len(candidates) == 0:
            if not wrap:
                return
            widget = None
        else:
            widget = min(candidates, key=operator.itemgetter(1))[0]

        self._blur(self._current_focus)
        self._current_focus = None
        self.focus(widget)

    def previous(self, wrap=True):
        """
        Focuses the previous widget in tab order.

        :param bool wrap: Whether to continue to the last widget when the first
                          of the tab order is reached.
        """
        if self._current_focus is None:
            self.focus()
            return
        if not self._widgets:
            return
        cur = self._tab_orders[self._current_focus]
        candidates = [(widget, order) for (widget, order)
                                      in self._tab_orders.iteritems()
                                      if order < cur]
        if len(candidates) == 0:
            if not wrap:
                return
            widget = max(self._tab_orders.iteritems(),
                         key=operator.itemgetter(1))[0]
        else:
            widget = max(candidates, key=operator.itemgetter(1))[0]

        self._blur(self._current_focus)
        self._current_focus = None
        self.focus(widget)

########NEW FILE########
__FILENAME__ = image
"""A module for manipulating Images, which are specially wrapped Pygame
surfaces.
"""

import pygame
import spyral
import copy

def _new_spyral_surface(size):
    """
    Internal method for creating a new Spyral-compliant Pygame surface.
    """
    return pygame.Surface((int(size[0]),
                           int(size[1])),
                          pygame.SRCALPHA, 32).convert_alpha()

def from_sequence(images, orientation="right", padding=0):
    """
    A function that returns a new Image from a list of images by
    placing them next to each other.

    :param images: A list of images to lay out.
    :type images: List of :class:`Image <spyral.Image>`
    :param str orientation: Either 'left', 'right', 'above', 'below', or
                            'square' (square images will be placed in a grid
                            shape, like a chess board).
    :param padding: The padding between each image. Can be specified as a
                    scalar number (for constant padding between all images)
                    or a list (for different paddings between each image).
    :type padding: int or a list of ints.
    :returns: A new :class:`Image <spyral.Image>`
    """
    if orientation == 'square':
        length = int(math.ceil(math.sqrt(len(images))))
        max_height = 0
        for index, image in enumerate(images):
            if index % length == 0:
                x = 0
                y += max_height
                max_height = 0
            else:
                x += image.width
                max_height = max(max_height, image.height)
            sequence.append((image, (x, y)))
    else:
        if orientation in ('left', 'right'):
            selector = spyral.Vec2D(1, 0)
        else:
            selector = spyral.Vec2D(0, 1)

        if orientation in ('left', 'above'):
            reversed(images)

        if type(padding) in (float, int, long):
            padding = [padding] * len(images)
        else:
            padding = list(padding)
            padding.append(0)
        base = spyral.Vec2D(0, 0)
        sequence = []
        for image, padding in zip(images, padding):
            sequence.append((image, base))
            base = base + selector * (image.size + (padding, padding))
    return from_conglomerate(sequence)

def from_conglomerate(sequence):
    """
    A function that generates a new image from a sequence of
    (image, position) pairs. These images will be placed onto a singe image
    large enough to hold all of them. More explicit and less convenient than
    :func:`from_seqeuence <spyral.image.from_sequence>`.

    :param sequence: A list of (image, position) pairs, where the positions
                     are :class:`Vec2D <spyral.Vec2D>` s.
    :type sequence: List of image, position pairs.
    :returns: A new :class:`Image <spyral.Image>`
    """
    width, height = 0, 0
    for image, (x, y) in sequence:
        width = max(width, x+image.width)
        height = max(height, y+image.height)
    new = Image(size=(width, height))
    for image, (x, y) in sequence:
        new.draw_image(image, (x, y))
    return new

def render_nine_slice(image, size):
    """
    Creates a new image by dividing the given image into a 3x3 grid, and stretching
    the sides and center while leaving the corners the same size. This is ideal
    for buttons and other rectangular shapes.

    :param image: The image to stretch.
    :type image: :class:`Image <spyral.Image>`
    :param size: The new (width, height) of this image.
    :type size: :class:`Vec2D <spyral.Vec2D>`
    :returns: A new :class:`Image <spyral.Image>` similar to the old one.
    """
    bs = spyral.Vec2D(size)
    bw = size[0]
    bh = size[1]
    ps = image.size / 3
    pw = int(ps[0])
    ph = int(ps[1])
    surf = image._surf
    # Hack: If we don't make it one px large things get cut
    image = spyral.Image(size=bs + (1, 1))
    s = image._surf
    # should probably fix the math instead, but it works for now

    topleft = surf.subsurface(pygame.Rect((0, 0), ps))
    left = surf.subsurface(pygame.Rect((0, ph), ps))
    bottomleft = surf.subsurface(pygame.Rect((0, 2*ph), ps))
    top = surf.subsurface(pygame.Rect((pw, 0), ps))
    mid = surf.subsurface(pygame.Rect((pw, ph), ps))
    bottom = surf.subsurface(pygame.Rect((pw, 2*ph), ps))
    topright = surf.subsurface(pygame.Rect((2*pw, 0), ps))
    right = surf.subsurface(pygame.Rect((2*pw, ph), ps))
    bottomright = surf.subsurface(pygame.Rect((2*pw, 2*ph), ps))

    # corners
    s.blit(topleft, (0, 0))
    s.blit(topright, (bw - pw, 0))
    s.blit(bottomleft, (0, bh - ph))
    s.blit(bottomright, bs - ps)

    # left and right border
    for y in range(ph, bh - ph - ph, ph):
        s.blit(left, (0, y))
        s.blit(right, (bw - pw, y))
    s.blit(left, (0, bh - ph - ph))
    s.blit(right, (bw - pw, bh - ph - ph))
    # top and bottom border
    for x in range(pw, bw - pw - pw, pw):
        s.blit(top, (x, 0))
        s.blit(bottom, (x, bh - ph))
    s.blit(top, (bw - pw - pw, 0))
    s.blit(bottom, (bw - pw - pw, bh - ph))

    # center
    for x in range(pw, bw - pw - pw, pw):
        for y in range(ph, bh - ph - ph, ph):
            s.blit(mid, (x, y))

    for x in range(pw, bw - pw - pw, pw):
        s.blit(mid, (x, bh - ph - ph))
    for y in range(ph, bh - ph - ph, ph):
        s.blit(mid, (bw - pw - pw, y))
    s.blit(mid, (bw - pw - pw, bh - ph - ph))
    return image

class Image(object):
    """
    The image is the basic drawable item in spyral. They can be created
    either by loading from common file formats, or by creating a new
    image and using some of the draw methods. Images are not drawn on
    their own, they are placed as the *image* attribute on Sprites to
    be drawn.

    Almost all of the methods of an Image instance return the Image itself,
    enabling commands to be chained in a
    `fluent interface <http://en.wikipedia.org/wiki/Fluent_interface>`_.

    :param size: If size is passed, creates a new blank image of that size to
                 draw on. If you do not specify a size, you *must* pass in a
                 filename.
    :type size: :class:`Vec2D <spyral.Vec2D>`
    :param str filename:  If filename is set, the file with that name is loaded.
                          The appendix has a list of the 
                          :ref:`valid image formats<ref.image_formats>`. If you do
                          not specify a filename, you *must* pass in a size.

    """

    def __init__(self, filename=None, size=None):
        if size is not None and filename is not None:
            raise ValueError("Must specify exactly one of size and filename. See http://platipy.org/en/latest/spyral_docs.html#spyral.image.Image")
        if size is None and filename is None:
            raise ValueError("Must specify exactly one of size and filename. See http://platipy.org/en/latest/spyral_docs.html#spyral.image.Image")

        if size is not None:
            self._surf = _new_spyral_surface(size)
            self._name = None
        else:
            self._surf = pygame.image.load(filename).convert_alpha()
            self._name = filename
        self._version = 1

    def _get_width(self):
        return self._surf.get_width()

    #: The width of this image in pixels (int). Read-only.
    width = property(_get_width)

    def _get_height(self):
        return self._surf.get_height()

    #: The height of this image in pixels (int). Read-only.
    height = property(_get_height)

    def _get_size(self):
        return spyral.Vec2D(self._surf.get_size())

    #: The (width, height) of the image (:class:`Vec2D <spyral.Vec2D`).
    #: Read-only.
    size = property(_get_size)

    def fill(self, color):
        """
        Fills the entire image with the specified color.

        :param color: a three-tuple of RGB values ranging from 0-255. Example:
                      (255, 128, 0) is orange.
        :type color: a three-tuple of ints.
        :returns: This image.
        """
        self._surf.fill(color)
        self._version += 1
        spyral.util.scale_surface.clear(self._surf)
        return self

    def draw_rect(self, color, position, size=None,
                  border_width=0, anchor='topleft'):
        """
        Draws a rectangle on this image.

        :param color: a three-tuple of RGB values ranging from 0-255. Example:
                      (255, 128, 0) is orange.
        :type color: a three-tuple of ints.
        :param position: The starting position of the rect (top-left corner). If
                         position is a Rect, then size should be `None`.
        :type position: :class:`Vec2D <spyral.Vec2D>` or
                        :class:`Rect <spyral.Rect>`
        :param size: The size of the rectangle; should not be given if position
                     is a rect.
        :type size: :class:`Vec2D <spyral.Vec2D>`
        :param int border_width: The width of the border to draw. If it is 0,
                                 the rectangle is filled with the color
                                 specified.
        :param str anchor: The anchor parameter is an
                           :ref:`anchor position <ref.anchors>`.
        :returns: This image.
        """
        if size is None:
            rect = spyral.Rect(position)
        else:
            rect = spyral.Rect(position, size)
        offset = self._calculate_offset(anchor, rect.size)
        pygame.draw.rect(self._surf, color,
                             (rect.pos + offset, rect.size), border_width)
        self._version += 1
        spyral.util.scale_surface.clear(self._surf)
        return self

    def draw_lines(self, color, points, width=1, closed=False):
        """
        Draws a series of connected lines on a image, with the
        vertices specified by points. This does not draw any sort of
        end caps on lines.

        :param color: a three-tuple of RGB values ranging from 0-255. Example:
                      (255, 128, 0) is orange.
        :type color: a three-tuple of ints.
        :param points: A list of points that will be connected, one to another.
        :type points: A list of :class:`Vec2D <spyral.Vec2D>` s.
        :param int width: The width of the lines.
        :param bool closed: If closed is True, the first and last point will be
                            connected. If closed is True and width is 0, the
                            shape will be filled.
        :returns: This image.
        """
        if width == 1:
            pygame.draw.aalines(self._surf, color, closed, points)
        else:
            pygame.draw.lines(self._surf, color, closed, points, width)
        self._version += 1
        spyral.util.scale_surface.clear(self._surf)
        return self

    def draw_circle(self, color, position, radius, width=0, anchor='topleft'):
        """
        Draws a circle on this image.

        :param color: a three-tuple of RGB values ranging from 0-255. Example:
                      (255, 128, 0) is orange.
        :type color: a three-tuple of ints.
        :param position: The center of this circle
        :type position: :class:`Vec2D <spyral.Vec2D>`
        :param int radius: The radius of this circle
        :param int width: The width of the circle. If it is 0, the circle is
                          filled with the color specified.
        :param str anchor: The anchor parameter is an
                           :ref:`anchor position <ref.anchors>`.
        :returns: This image.
        """
        offset = self._calculate_offset(anchor)
        pygame.draw.circle(self._surf, color, (position + offset).floor(),
                           radius, width)
        self._version += 1
        spyral.util.scale_surface.clear(self._surf)
        return self

    def draw_ellipse(self, color, position, size=None,
                     border_width=0, anchor='topleft'):
        """
        Draws an ellipse on this image.

        :param color: a three-tuple of RGB values ranging from 0-255. Example:
                      (255, 128, 0) is orange.
        :type color: a three-tuple of ints.
        :param position: The starting position of the ellipse (top-left corner).
                         If position is a Rect, then size should be `None`.
        :type position: :class:`Vec2D <spyral.Vec2D>` or
                        :class:`Rect <spyral.Rect>`
        :param size: The size of the ellipse; should not be given if position is
                     a rect.
        :type size: :class:`Vec2D <spyral.Vec2D>`
        :param int border_width: The width of the ellipse. If it is 0, the
                          ellipse is filled with the color specified.
        :param str anchor: The anchor parameter is an
                           :ref:`anchor position <ref.anchors>`.
        :returns: This image.
        """
        if size is None:
            rect = spyral.Rect(position)
        else:
            rect = spyral.Rect(position, size)
        offset = self._calculate_offset(anchor, rect.size)
        pygame.draw.ellipse(self._surf, color,
                            (rect.pos + offset, rect.size), border_width)
        self._version += 1
        spyral.util.scale_surface.clear(self._surf)
        return self

    def draw_point(self, color, position, anchor='topleft'):
        """
        Draws a point on this image.

        :param color: a three-tuple of RGB values ranging from 0-255. Example:
                      (255, 128, 0) is orange.
        :type color: a three-tuple of ints.
        :param position: The position of this point.
        :type position: :class:`Vec2D <spyral.Vec2D>`
        :param str anchor: The anchor parameter is an
                           :ref:`anchor position <ref.anchors>`.
        :returns: This image.
        """
        offset = self._calculate_offset(anchor)
        self._surf.set_at(position + offset, color)
        self._version += 1
        spyral.util.scale_surface.clear(self._surf)
        return self

    def draw_arc(self, color, start_angle, end_angle,
                 position, size=None, border_width=0, anchor='topleft'):
        """
        Draws an elliptical arc on this image.

        :param color: a three-tuple of RGB values ranging from 0-255. Example:
                      (255, 128, 0) is orange.
        :type color: a three-tuple of ints.
        :param float start_angle: The starting angle, in radians, of the arc.
        :param float end_angle: The ending angle, in radians, of the arc.
        :param position: The starting position of the ellipse (top-left corner).
                         If position is a Rect, then size should be `None`.
        :type position: :class:`Vec2D <spyral.Vec2D>` or
                        :class:`Rect <spyral.Rect>`
        :param size: The size of the ellipse; should not be given if position is
                     a rect.
        :type size: :class:`Vec2D <spyral.Vec2D>`
        :param int border_width: The width of the ellipse. If it is 0, the
                          ellipse is filled with the color specified.
        :param str anchor: The anchor parameter is an
                           :ref:`anchor position <ref.anchors>`.
        :returns: This image.
        """
        if size is None:
            rect = spyral.Rect(position)
        else:
            rect = spyral.Rect(position, size)
        offset = self._calculate_offset(anchor, rect.size)
        pygame.draw.arc(self._surf, color, (rect.pos + offset, rect.size),
                        start_angle, end_angle, border_width)
        self._version += 1
        spyral.util.scale_surface.clear(self._surf)
        return self

    def draw_image(self, image, position=(0, 0), anchor='topleft'):
        """
        Draws another image over this one.

        :param image: The image to overlay on top of this one.
        :type image: :class:`Image <spyral.Image>`
        :param position: The position of this image.
        :type position: :class:`Vec2D <spyral.Vec2D>`
        :param str anchor: The anchor parameter is an
                           :ref:`anchor position <ref.anchors>`.
        :returns: This image.
        """
        offset = self._calculate_offset(anchor, image._surf.get_size())
        self._surf.blit(image._surf, position + offset)
        self._version += 1
        spyral.util.scale_surface.clear(self._surf)
        return self

    def rotate(self, angle):
        """
        Rotates the image by angle degrees clockwise. This may change the image
        dimensions if the angle is not a multiple of 90.

        Successive rotations degrate image quality. Save a copy of the
        original if you plan to do many rotations.

        :param float angle: The number of degrees to rotate.
        :returns: This image.
        """
        self._surf = pygame.transform.rotate(self._surf, angle).convert_alpha()
        self._version += 1
        return self

    def scale(self, size):
        """
        Scales the image to the destination size.

        :param size: The new size of the image.
        :type size: :class:`Vec2D <spyral.Vec2D>`
        :returns: This image.
        """
        self._surf = pygame.transform.smoothscale(self._surf,
                                                  size).convert_alpha()
        self._version += 1
        return self

    def flip(self, flip_x=True, flip_y=True):
        """
        Flips the image horizontally, vertically, or both.

        :param bool flip_x: whether to flip horizontally.
        :param bool flip_y: whether to flip vertically.
        :returns: This image.
        """
        self._version += 1
        self._surf = pygame.transform.flip(self._surf,
                                           flip_x, flip_y).convert_alpha()
        return self

    def copy(self):
        """
        Returns a copy of this image that can be changed while preserving the
        original.

        :returns: A new image.
        """
        new = copy.copy(self)
        new._surf = self._surf.copy()
        return new

    def crop(self, position, size=None):
        """
        Removes the edges of an image, keeping the internal rectangle specified
        by position and size.

        :param position: The upperleft corner of the internal rectangle that
                         will be preserved.
        :type position: a :class:`Vec2D <spyral.Vec2D>` or a
                        :class:`Rect <spyral.Rect>`.
        :param size: The size of the internal rectangle to preserve. If a Rect
                     was passed in for position, this should be None.
        :type size: :class:`Vec2D <spyral.Vec2D>` or None.
        :returns: This image.
        """
        if size is None:
            rect = spyral.Rect(position)
        else:
            rect = spyral.Rect(position, size)
        new = _new_spyral_surface(size)
        new.blit(self._surf, (0, 0), (rect.pos, rect.size))
        self._surf = new
        self._version += 1
        return self

    def _calculate_offset(self, anchor_type, size=(0, 0)):
        """
        Internal method for calculating the offset associated with an
        anchor type.

        :param anchor_type: A string indicating the position of the anchor,
                            taken from :ref:`anchor position <ref.anchors>`. A
                            numerical offset can also be specified.
        :type anchor_type: str or a :class:`Vec2D <spyral.Vec2D>`.
        :param size: The size of the region to offset in.
        :type size: :class:`Vec2D <spyral.Vec2D>`.
        """
        w, h = self._surf.get_size()
        w2, h2 = size

        if anchor_type == 'topleft':
            return spyral.Vec2D(0, 0)
        elif anchor_type == 'topright':
            return spyral.Vec2D(w - w2, 0)
        elif anchor_type == 'midtop':
            return spyral.Vec2D((w - w2) / 2., 0)
        elif anchor_type == 'bottomleft':
            return spyral.Vec2D(0, h - h2)
        elif anchor_type == 'bottomright':
            return spyral.Vec2D(w - w2, h - h2)
        elif anchor_type == 'midbottom':
            return spyral.Vec2D((w - w2) / 2., h - h2)
        elif anchor_type == 'midleft':
            return spyral.Vec2D(0, (h - h2) / 2.)
        elif anchor_type == 'midright':
            return spyral.Vec2D(w - w2, (h - h2) / 2.)
        elif anchor_type == 'center':
            return spyral.Vec2D((w - w2) / 2., (h - h2) / 2.)
        else:
            return spyral.Vec2D(anchor_type) - spyral.Vec2D(w2, h2)

########NEW FILE########
__FILENAME__ = keyboard
"""The keyboard modules provides an interface to adjust the keyboard's repeat
rate.

.. attribute:: repeat

    When the keyboard repeat is enabled, keys that are held down will keep
    generating new events over time. Defaults to `False`.

.. attribute:: delay

    `int` to control how many milliseconds before the repeats start.

.. attribute:: interval

    `int` to control how many milliseconds to wait between repeated events.

"""

import sys
import types
import pygame

old = sys.modules[__name__]

class _KeyboardModule(types.ModuleType):
    def __init__(self, *args):
        types.ModuleType.__init__(self, *args)
        self._repeat = False
        self._delay = 600
        self._interval = 100

    def _update_repeat_status(self):
        if self._repeat:
            pygame.key.set_repeat(self._delay, self._interval)
        else:
            pygame.key.set_repeat()

    def _set_repeat(self, repeat):
        self._repeat = repeat
        self._update_repeat_status()

    def _get_repeat(self):
        return self._repeat

    def _set_interval(self, interval):
        self._interval = interval
        self._update_repeat_status()

    def _get_interval(self):
        return self._interval

    def _set_delay(self, delay):
        self._delay = delay
        if delay == 0:
            self._repeat = False
        self._update_repeat_status()

    def _get_delay(self):
        return self._delay

    repeat = property(_get_repeat, _set_repeat)
    delay = property(_get_delay, _set_delay)
    interval = property(_get_interval, _set_interval)

# Keep the refcount from going to 0
keyboard = _KeyboardModule(__name__)
sys.modules[__name__] = keyboard
keyboard.__dict__.update(old.__dict__)

########NEW FILE########
__FILENAME__ = layertree
"""
The LayerTree class manages the layers for a Scene; this is a complicated
problem, because we need to know the depth order for sprites extremely quickly
when we draw. All layers are precalculated by converting Relative Depth Chains
into an Absolute Position Value.

Important concepts:
    Relative Depth Chain - a list of numbers indicating the current relative
    position of this layer. If we had four layers like so:
        Scene -> View : [0,0]
        Scene -> View -> "top" : [0, 0, 0]
        Scene -> View -> "top" -> View : [0, 0, 1, 0]
        Scene -> View -> "bottom" : [0, 0, 1]
    Absolute Position Value
        A number representing a Relative Depth Chain collapsed into a single
        integer (or long, possibly)
"""

from weakref import ref as _wref

class _LayerTree(object):
    """
    Starts keeping track of the entity as a child of this view.

    :param scene: The scene that owns this LayerTree.
    :type scene: Scene (not a weakref).
    """
    #: The maximum number of layers for any given view/scene. After this, depth
    #: calculations will be messed up. It is an artificially chosen number, it
    #: should eventually be possible to change it.
    MAX_LAYERS = 40
    def __init__(self, scene):
        self.layers = {_wref(scene) : []}
        self.child_views = {_wref(scene) : []}
        self.layer_location = {_wref(scene) : [0]}
        self.scene = _wref(scene)
        self.tree_height = {_wref(scene) : 1}
        self._precompute_positions()
        self.maximum_height = 1

    def remove_view(self, view):
        """
        Removes all references to this view; it must have previously been added
        to the LayerTree.

        :param view: the View to remove
        :type view: View (not a weakref)
        """
        view = _wref(view)
        del self.tree_height[view]
        del self.layers[view]
        self.child_views[view()._parent].remove(view)
        del self.child_views[view]
        self._precompute_positions()

    def add_view(self, view):
        """
        Starts keeping track of this view in the LayerTree.

        :param view: the new View to add
        :type view: View (not a weakref)
        """
        parent = view._parent
        view = _wref(view)
        self.layers[view] = []
        self.child_views[view] = []
        self.child_views[parent].append(view)
        self.tree_height[view] = 1
        if len(self.child_views[parent]) == 1:
            self.tree_height[parent] += 1
            while parent != self.scene:
                parent = parent()._parent
                self.tree_height[parent] += 1
        self._precompute_positions()

    def set_view_layer(self, view, layer):
        """
        Set the layer that this View is on. Behavior is undefined if that layer
        does not exist in the parent, so make sure you eventually add that layer
        to the parent.

        :param view: the view have its layer set
        :type view: View (not a weakref)
        :param layer: the name of the layer on the parent
        :type layer: string
        """
        view.layer = layer
        self._precompute_positions()

    def set_view_layers(self, view, layers):
        """
        Set the layers that will be available for this view or scene.

        :param view: the view have its layer set
        :type view: View (not a weakref) or a Scene (not a weakref)
        :param layers: the name of the layer on the parent
        :type layers: a list of strings
        """
        self.layers[_wref(view)] = list(layers)
        self._precompute_positions()

    def _compute_positional_chain(self, chain):
        """
        From a list of numbers indicating the location of the View/layer within
        the current level, compute an absolute number in base MAX_LAYERS that
        can quickly and easily compared.

        :param chain: The relative positions at this level
        :type chain: a list of numbers
        :returns: An `int` representing the absolute position depth.
        """
        total = 0
        for index, value in enumerate(chain):
            power = self.maximum_height - index - 1
            total += value * (self.MAX_LAYERS ** power)
        return total

    def _precompute_positions(self):
        """
        Runs through the entire LayerTree and calculates an absolute number for
        each possible view/layer, which can be easily compared.
        """
        self.maximum_height = self.tree_height[self.scene]
        self.layer_location = {}
        self._precompute_position_for_layer(self.scene, [])
        for layer_key, v in self.layer_location.iteritems():
            self.layer_location[layer_key] = self._compute_positional_chain(v)

    def _precompute_position_for_layer(self, view, current_position):
        """
        For a given view, and the current depth in the layer heirarchy, compute
        what its relative depth chain should look like. Sets this entry for
        layer_location to be a list of numbers indicating the relative depth.
        Note that this is called in a recursive manner to move down the entire
        LayerTree.

        :param view: The current view to explore
        :type view: a weakref to a View!
        :param current_position: The current relative depth chain
        :type current_position: list of numbers
        """
        position = 0
        for position, layer in enumerate(self.layers[view], 1):
            self.layer_location[(view, layer)] = current_position + [position]
        self.layer_location[view] = current_position + [1+position]
        for subview in self.child_views[view]:
            if subview().layer is None:
                new_position = self.layer_location[view]
            else:
                new_position = self.layer_location[(view, subview().layer)]
            self._precompute_position_for_layer(subview, new_position)

    def get_layer_position(self, parent, layer):
        """
        For a given layer (and also that layer's parent/owner, since layer
        alone is ambiguous), identify what the Absolute Position Value is from
        the precomputed cache, allowing for :above and :below modifiers.

        :param parent: The view or scene that has this layer
        :type parent: a View or a Scene (not weakrefs!)
        :param layer: The name of the layer that we're interested in.
        :type layer: string
        :returns: A `float` representing where this layer is relative to others.
        """
        parent = _wref(parent)
        s = layer.split(':')
        layer = s[0]
        offset = 0
        if len(s) > 1:
            mod = s[1]
            if mod == 'above':
                offset = 0.5
            if mod == 'below':
                offset = -0.5
        if (parent, layer) in self.layer_location:
            position = self.layer_location[(parent, layer)]
        elif parent in self.layer_location:
            position = self.layer_location[parent]
        else:
            position = self.layer_location[self.scene]
        return position + offset

########NEW FILE########
__FILENAME__ = memoize
"""This module contains classes to handle memoization, a time-saving method that
caches previously seen results from function calls."""

class Memoize(object):
    """
    This is a decorator to allow memoization of function calls. It is a
    completely dumb cache, and will cache anything given to it indefinitely.

    :param object func: Any function (although any object will work).
    .. warning:: This may be deprecated.
    """
    def __init__(self, func):
        self.func = func
        self.cache = {}

    def __call__(self, *args):
        """
        Attempts to return the results of this function call from the cache;
        if it can't find it, then it will execute the function and add it to the
        cache.
        """
        try:
            return self.cache[args]
        except KeyError:
            res = self.func(*args)
            self.cache[args] = res
            return res
        except TypeError:
            print ("WARNING: Unhashable type passed to memoize."
                   "Reconsider using this decorator.")
            return self.func(*args)

class SmartMemoize(object):
    """
    This is a decorator to allow memoization of function calls. Its cache
    is cleared on scene changes, and also clears items from the cache which
    haven't been used in at least 250 frames.

    :param object func: Any function (although any object will work).
    """
    def __init__(self, func):
        self.func = func
        self.cache = {}
        self.scene = None
        self.last_clear = 0

    def __call__(self, *args):
        """
        Attempts to return the results of this function call from the cache;
        if it can't find it, then it will execute the function and add it to the
        cache.
        """
        from spyral import director
        frame = director.get_tick()
        if director.get_scene() is not self.scene:
            self.scene = director.get_scene()
            self.cache = {}
        if frame - self.last_clear > 100:
            for key, value in self.cache.items():
                data, oldframe = value
                if frame - oldframe > 250:
                    self.cache.pop(key)
            self.last_clear = frame
        try:
            data, oldframe = self.cache[args]
            self.cache[args] = (data, frame)
            return data
        except KeyError:
            res = self.func(*args)
            self.cache[args] = (res, frame)
            return res
        except TypeError:
            print ("WARNING: Unhashable type passed to SmartMemoize."
                   "Reconsider using this decorator")
            return self.func(*args)

class _ImageMemoize(SmartMemoize):
    """
    A subclass of SmartMemoise that is built explicitly for image related calls.
    It allows images to be cleared from its cache when they are updated.
    """
    def clear(self, clear_image):
        """
        Removes the given image from the cache.
        :param clear_image: The image to remove.
        :type clear_image: :class:`Image <spyral.Image>`
        """
        self.cache = dict(((image, scale) for (image, scale)
                                          in self.cache.iteritems()
                                          if image is clear_image))

########NEW FILE########
__FILENAME__ = mouse
"""The mouse modules provides an interface to adjust the mouse cursor.

.. attribute:: visible

    `Bool` that adjust whether the mouse cursor should be shown. This is useful
    if you want to, for example, use a Sprite instead of the regular mouse
    cursor.

.. attribute:: cursor

    `str` value that lets you choose from among the built-in options for
    cursors. The options are:

        * ``"arrow"`` : the regular arrow-shaped cursor
        * ``"diamond"`` : a diamond shaped cursor
        * ``"x"`` : a broken X, useful for indicating disabled states.
        * ``"left"``: a triangle pointing to the left
        * ``"right"``: a triangle pointing to the right

    .. warning:: Custom non-Sprite mouse cursors are currently not supported.

"""

import sys
import types
import pygame

old = sys.modules[__name__]

cursors = {"arrow": pygame.cursors.arrow,
           "diamond": pygame.cursors.diamond,
           "x": pygame.cursors.broken_x,
           "left": pygame.cursors.tri_left,
           "right": pygame.cursors.tri_right}

class _MouseModule(types.ModuleType):
    def __init__(self, *args):
        types.ModuleType.__init__(self, *args)
        self._visible = True
    def _get_cursor(self):
        return pygame.mouse.get_cursor()
    def _set_cursor(self, cursor):
        if cursor in cursors:
            pygame.mouse.set_cursor(*cursors[cursor])
        else:
            pygame.mouse.set_cursor(*cursor)
    def _get_visible(self):
        return self._visible
    def _set_visible(self, visiblity):
        pygame.mouse.set_visible(visiblity)
        self._visible = visiblity
    cursor = property(_get_cursor, _set_cursor)
    visible = property(_get_visible, _set_visible)

# Keep the refcount from going to 0
mouse = _MouseModule(__name__)
sys.modules[__name__] = mouse
mouse.__dict__.update(old.__dict__)

########NEW FILE########
__FILENAME__ = rect
"""
Rects are a convenience class for managing rectangular regions.
"""

import pygame
import spyral

class Rect(object):
    """
    Rect represents a rectangle and provides some useful features. Rects can 
    be specified 3 ways in the constructor:

    #. Four numbers, ``x``, ``y``, ``width``, ``height``
    #. Two tuples, ``(x, y)`` and `(width, height)`
    #. Another rect, which is copied

    >>> rect1 = spyral.Rect(10, 10, 64, 64)               # Method 1
    >>> rect2 = spyral.Rect((10, 10), (64, 64))           # Method 2
    >>> rect3 = spyral.Rect(rect1.topleft, rect1.size)    # Method 2
    >>> rect4 = spyral.Rect(rect3)                        # Method 3

    Rects support all the usual :ref:`anchor points <ref.anchors>` as
    attributes, so you can both get ``rect.center`` and assign to it.
    Rects also support attributes of ``right``, ``left``, ``top``, ``bottom``,
    ``x``, and ``y``.

    >>> rect1.x
    10
    >>> rect1.centerx
    42.0
    >>> rect1.width
    64
    >>> rect1.topleft
    Vec2D(10, 10)
    >>> rect1.bottomright
    Vec2D(74, 74)
    >>> rect1.center
    Vec2D(42.0, 42.0)
    >>> rect1.size
    Vec2D(64, 64)

    """
    def __init__(self, *args):
        if len(args) == 1:
            r = args[0]
            self._x, self._y = r.x, r.y
            self._w, self._h = r.w, r.h
        elif len(args) == 2:
            self._x, self._y = args[0]
            self._w, self._h = args[1]
        elif len(args) == 4:
            self.left, self.top, self.width, self.height = args
        else:
            raise ValueError("You done goofed.")

    def __getattr__(self, name):
        v = spyral.Vec2D
        if name == "right":
            return self._x + self._w
        if name == "left" or name == "x":
            return self._x
        if name == "top" or name == "y":
            return self._y
        if name == "bottom":
            return self._y + self._h
        if name == "topright":
            return v(self._x + self._w, self._y)
        if name == "bottomleft":
            return v(self._x, self._y + self._h)
        if name == "topleft" or name == "pos":
            return v(self._x, self._y)
        if name == "bottomright":
            return v(self._x + self._w, self._y + self._h)
        if name == "centerx":
            return self._x + self._w / 2.
        if name == "centery":
            return self._y + self._h / 2.
        if name == "center":
            return v(self._x + self._w / 2., self._y + self._h / 2.)
        if name == "midleft":
            return v(self._x, self._y + self._h / 2.)
        if name == "midright":
            return v(self._x + self._w, self._y + self._h / 2.)
        if name == "midtop":
            return v(self._x + self._w / 2., self._y)
        if name == "midbottom":
            return v(self._x + self._w / 2., self._y + self._h)
        if name == "size":
            return v(self._w, self._h)
        if name == "width" or name == "w":
            return self._w
        if name == "height" or name == "h":
            return self._h

        raise AttributeError("type object 'rect' "
                             "has no attribute '%s'" % name)

    def __setattr__(self, name, val):
        # This could use _a lot_ more error checking
        if name[0] == "_":
            self.__dict__[name] = int(val)
            return
        if name == "right":
            self._x = val - self._w
        elif name == "left":
            self._x = val
        elif name == "top":
            self._y = val
        elif name == "bottom":
            self._y = val - self._h
        elif name == "topleft" or name == "pos":
            self._x, self._y = val
        elif name == "topright":
            self._x = val[0] - self._w
            self._y = val[1]
        elif name == "bottomleft":
            self._x = val[0]
            self._y = val[1] - self._h
        elif name == "bottomright":
            self._x = val[0] - self._w
            self._y = val[0] - self._h
        elif name == "width" or name == "w":
            self._w = val
        elif name == "height" or name == "h":
            self._h = val
        elif name == "size":
            self._w, self._h = val
        elif name == "centerx":
            self._x = val - self._w / 2.
        elif name == "centery":
            self._y = val - self._h / 2.
        elif name == "center":
            self._x = val[0] - self._w / 2.
            self._y = val[1] - self._h / 2.
        elif name == "midtop":
            self._x = val[0] - self._w / 2.
            self._y = val[1]
        elif name == "midleft":
            self._x = val[0]
            self._y = val[1] - self._h / 2.
        elif name == "midbottom":
            self._x = val[0] - self._w / 2.
            self._y = val[1] - self._h
        elif name == "midright":
            self._x = val[0] - self._w
            self._y = val[1] - self._h / 2.
        else:
            raise AttributeError("You done goofed!")

    def copy(self):
        """
        Returns a copy of this rect

        :returns: A new :class:`Rect <spyral.Rect>`
        """
        return Rect(self._x, self._y, self._w, self._h)

    def move(self, x, y):
        """
        Returns a copy of this rect offset by *x* and *y*.

        :param float x: The horizontal offset.
        :param float y: The vertical offset.
        :returns: A new :class:`Rect <spyral.Rect>`
        """
        return Rect(x, y, self._w, self._h)

    def move_ip(self, x, y):
        """
        Moves this rect by *x* and *y*.

        :param float x: The horizontal offset.
        :param float y: The vertical offset.
        """
        self._x, self._y = self._x + x, self._y + y

    def inflate(self, width, height):
        """
        Returns a copy of this rect inflated by *width* and *height*.

        :param float width: The amount to add horizontally.
        :param float height: The amount to add vertically.
        :returns: A new :class:`Rect <spyral.Rect>`
        """
        c = self.center
        n = self.copy()
        n.size = (self._w + width, self._h + height)
        n.center = c
        return n

    def inflate_ip(self, width, height):
        """
        Inflates this rect by *width*, *height*.

        :param float width: The amount to add horizontally.
        :param float height: The amount to add vertically.
        """
        c = self.center
        self.size = (self._w + width, self._h + height)
        self.center = c

    def union(self, other):
        """
        Returns a new rect which represents the union of this rect
        with other -- in other words, a new rect is created that can fit both
        original rects.

        :param other: The other Rect.
        :type other: :class:`Rect <spyral.Rect>`
        :returns: A new :class:`Rect <spyral.Rect>`
        """
        top = min(self.top, other.top)
        left = min(self.left, other.left)
        bottom = max(self.bottom, other.bottom)
        right = max(self.right, other.right)
        return Rect((left, top), (right - left, bottom - top))

    def union_ip(self, other):
        """
        Modifies this rect to be the union of it and the other -- in other
        words, this rect will expand to include the other rect.

        :param other: The other Rect.
        :type other: :class:`Rect <spyral.Rect>`
        """
        top = min(self.top, other.top)
        left = min(self.left, other.left)
        bottom = max(self.bottom, other.bottom)
        right = max(self.right, other.right)
        self.top, self.left = top, left
        self.bottom, self.right = bottom, right

    # @test: Rect(10,10,50,50).clip(Rect(0,0,20,20)) -> Rect(10,10,10,10)
    def clip(self, other):
        """
        Returns a Rect which is cropped to be completely inside of other.
        If the other does not overlap with this rect, a rect of size 0 is
        returned.

        :param other: The other Rect.
        :type other: :class:`Rect <spyral.Rect>`
        :returns: A new :class:`Rect <spyral.Rect>`
        """
        B = other
        A = self
        try:
            B._x
        except TypeError:
            B = Rect(B)

        if A._x >= B._x and A._x < (B._x + B._w):
            x = A._x
        elif B._x >= A._x and B._x < (A._x + A._w):
            x = B._x
        else:
            return Rect(A._x, A._y, 0, 0)

        if ((A._x + A._w) > B._x) and ((A._x + A._w) <= (B._x + B._w)):
            w = A._x + A._w - x
        elif ((B._x + B._w) > A._x) and ((B._x + B._w) <= (A._x + A._w)):
            w = B._x + B._w - x
        else:
            return Rect(A._x, A._y, 0, 0)

        if A._y >= B._y and A._y < (B._y + B._h):
            y = A._y
        elif B._y >= A._y and B._y < (A._y + A._h):
            y = B._y
        else:
            return Rect(A._x, A._y, 0, 0)

        if ((A._y + A._h) > B._y) and ((A._y + A._h) <= (B._y + B._h)):
            h = A._y + A._h - y
        elif ((B._y + B._h) > A._y) and ((B._y + B._h) <= (A._y + A._h)):
            h = B._y + B._h - y
        else:
            return Rect(A._x, A._y, 0, 0)

        return Rect(x, y, w, h)

    def clip_ip(self, other):
        """
        Modifies this rect to be cropped completely inside of other.
        If the other does not overlap with this rect, this rect will have a size
        of 0.

        :param other: The other Rect.
        :type other: :class:`Rect <spyral.Rect>`
        """
        new_rect = self.clip(other)
        self.topleft, self.size = new_rect.topleft, new_rect.size

    def contains(self, other):
        """
        Returns `True` if the other rect is contained inside this rect.

        :param other: The other Rect.
        :type other: :class:`Rect <spyral.Rect>`
        :returns: A `bool` indicating whether this rect is contained within
                  another.
        """
        return (other.collide_point(self.topleft) and
                other.collide_point(self.bottomright))

    def collide_rect(self, other):
        """
        Returns `True` if this rect collides with the other rect.

        :param other: The other Rect.
        :type other: :class:`Rect <spyral.Rect>`
        :returns: A `bool` indicating whether this rect is contained within
                  another.
        """
        return (self.clip(other).size != (0, 0) or
                other.clip(self).size != (0, 0))

    def collide_point(self, point):
        """
        :param point: The point.
        :type point: :class:`Vec2D <spyral.Vec2D>`
        :returns: A `bool` indicating whether the point is contained within this
                  rect.
        """
        # This could probably be optimized as well
        return point[0] > self.left and point[0] < self.right and \
            point[1] > self.top and point[1] < self.bottom

    def _to_pygame(self):
        """
        Internal method for creating a Pygame compatible rect from this rect.

        :returns: A :class:`pygame.Rect`
        """
        return pygame.Rect(((self.left, self.top), (self.width, self.height)))

    def __str__(self):
        return ''.join(['<rect(',
                        str(self._x),
                        ',',
                        str(self._y),
                        ',',
                        str(self._w),
                        ',',
                        str(self._h),
                        ')>'])

    def __repr__(self):
        return self.__str__()

########NEW FILE########
__FILENAME__ = scene
from __future__ import division
import spyral
import pygame
import time
import operator
import inspect
import sys
import types
try:
    import greenlet
    _GREENLETS_AVAILABLE = True
except ImportError:
    spyral.exceptions.actors_not_available_warning()
    _GREENLETS_AVAILABLE = False
    
from itertools import chain
from layertree import _LayerTree
from collections import defaultdict
from weakref import ref as _wref
from weakmethod import WeakMethodBound

def _has_value(obj, collect):
    for item in collect:
        if obj is item:
            return True
        elif isinstance(item, dict) and obj in item.values():
            return True
        elif isinstance(item, tuple) and obj in item:
            return True
    return False

class Scene(object):
    """
    Creates a new Scene. When a scene is not active, no events will be processed
    for it. Scenes are the basic units that are executed by spyral for your game,
    and should be subclassed and filled in with code which is relevant to your
    game. The :class:`Director <spyral.director>`, is a manager for Scenes,
    which maintains a stacks and actually executes the code.


    :param size: The `size` of the scene internally (or "virtually"). This is
                 the coordinate space that you place Sprites in, but it does
                 not have to match up 1:1 to the window (which could be scaled).
    :type size: width, height
    :param int max_ups: Maximum updates to process per second. By default,
                        `max_ups` is pulled from the director.
    :param int max_fps: Maximum frames to draw per second. By default,
                        `max_fps` is pulled from the director.
    """
    def __init__(self, size = None, max_ups=None, max_fps=None):
        time_source = time.time
        self.clock = spyral.GameClock(
            time_source=time_source,
            max_fps=max_fps or spyral.director._max_fps,
            max_ups=max_ups or spyral.director._max_ups)
        self.clock.use_wait = True

        self._handlers = defaultdict(lambda: [])
        self._namespaces = set()
        self._event_source = spyral.event.LiveEventHandler()
        self._handling_events = False
        self._events = []
        self._pending = []
        self._greenlets = {} # Maybe need to weakref dict

        self._style_symbols = {}
        self._style_classes = []
        self._style_properties = defaultdict(lambda: {})
        self._style_functions = {}

        self._style_functions['_get_spyral_path'] = spyral._get_spyral_path

        self._size = None
        self._scale = spyral.Vec2D(1.0, 1.0) #None
        self._surface = pygame.display.get_surface()
        if size is not None:
            self._set_size(size)
        display_size = self._surface.get_size()
        self._background = spyral.image._new_spyral_surface(display_size)
        self._background.fill((255, 255, 255))
        self._background_version = 0
        self._surface.blit(self._background, (0, 0))
        self._blits = []
        self._dirty_rects = []
        self._clear_this_frame = []
        self._clear_next_frame = []
        self._soft_clear = []
        self._static_blits = {}
        self._invalidating_views = {}
        self._collision_boxes = {}
        self._rect = self._surface.get_rect()

        self._layers = []
        self._child_views = []
        self._layer_tree = _LayerTree(self)
        self._sprites = set()

        spyral.event.register('director.scene.enter', self.redraw,
                              scene=self)
        spyral.event.register('director.update', self._handle_events,
                              scene=self)
        if _GREENLETS_AVAILABLE:
            spyral.event.register('director.update', self._run_actors, 
                                  ('delta',), scene=self)
        spyral.event.register('system.focus_change', self.redraw)
        spyral.event.register('system.video_resize', self.redraw)
        spyral.event.register('system.video_expose', self.redraw)
        spyral.event.register('spyral.internal.view.changed',
                              self._invalidate_views, scene=self)

        # View interface
        self._scene = _wref(self)
        self._views = []

        # Loading default styles
        self.load_style(spyral._get_spyral_path() +
                        'resources/form_defaults.spys')

    # Actor Handling
    def _register_actor(self, actor, greenlet):
        """
        Internal method to add a new :class:`Actor <spyral.Actor>` to this
        scene.

        :param actor: The name of the actor object.
        :type actor: :class:`Actor <spyral.Actor>`
        :param greenlet greenlet: The greenlet context for this actor.
        """
        self._greenlets[actor] = greenlet

    def _run_actors_greenlet(self, delta, _):
        """
        Helper method for running the actors.

        :param float delta: The amount of time progressed.
        """
        for actor, greenlet in self._greenlets.iteritems():
            delta, rerun = greenlet.switch(delta)
            while rerun:
                delta, rerun = greenlet.switch(delta)
        return False

    def _run_actors(self, delta):
        """
        Main loop for running actors, switching between their different
        contexts.

        :param float delta: The amount of time progressed.
        """
        g = greenlet.greenlet(self._run_actors_greenlet)
        while True:
            d = g.switch(delta, False)
            if d is True:
                continue
            if d is False:
                break
            g.switch(d, True)

    # Event Handling
    def _queue_event(self, type, event=None):
        """
        Internal method to add a new `event` to be handled by this scene.

        :param str type: The name of the event to queue
        :param event: Metadata about this event.
        :type event: :class:`Event <spyral.Event>`
        """
        if self._handling_events:
            self._pending.append((type, event))
        else:
            self._events.append((type, event))

    def _reg_internal(self, namespace, handlers, args,
                      kwargs, priority, dynamic):
        """
        Convenience method for registering a new event; other variations
        exist to keep the signature convenient and easy.
        """
        if namespace.endswith(".*"):
            namespace = namespace[:-2]
        self._namespaces.add(namespace)
        for handler in handlers:
            self._handlers[namespace].append((handler, args, kwargs,
                                              priority, dynamic))
        self._handlers[namespace].sort(key=operator.itemgetter(3))

    def _get_namespaces(self, namespace):
        """
        Internal method for returning all the registered namespaces that are in
        the given namespace.
        """
        return [n for n in self._namespaces if (namespace == n or
                                        n.rsplit(".",1)[0].startswith(namespace) or
                                        namespace.rsplit(".",1)[0].startswith(n))]

    def _send_event_to_handler(self, event, type, handler, args,
                               kwargs, priority, dynamic):
        """
        Internal method to dispatch events to their handlers.
        """
        fillval = "__spyral_itertools_fillvalue__"
        def _get_arg_val(arg, default = fillval):
            if arg == 'event':
                return event
            elif hasattr(event, arg):
                return getattr(event, arg)
            else:
                if default != fillval:
                    return default
                raise TypeError("Handler expects an argument named "
                                "%s, %s does not have that." %
                                (arg, str(type)))
        if dynamic is True:
            h = handler
            handler = self
            for piece in h.split("."):
                handler = getattr(handler, piece, None)
                if handler is None:
                    return
        if handler is sys.exit and args is None and kwargs is None:
            # Dirty hack to deal with python builtins
            args = []
            kwargs = {}
        elif args is None and kwargs is None:
            # Autodetect the arguments
            try:
                funct = handler.func
            except AttributeError, e:
                funct = handler
            try:
                h_argspec = inspect.getargspec(funct)
            except Exception, e:
                raise Exception(("Unfortunate Python Problem! "
                                 "%s isn't supported by Python's "
                                 "inspect module! Oops.") % str(handler))
            h_args = h_argspec.args
            h_defaults = h_argspec.defaults or tuple()
            if len(h_args) > 0 and 'self' == h_args[0]:
                h_args.pop(0)
            d = len(h_args) - len(h_defaults)
            if d > 0:
                h_defaults = [fillval] * d + list(*h_defaults)
            args = [_get_arg_val(arg, default) for arg, default
                                               in zip(h_args, h_defaults)]
            kwargs = {}
        elif args is None:
            args = []
            kwargs = dict([(arg, _get_arg_val(arg)) for arg in kwargs])
        else:
            args = [_get_arg_val(arg) for arg in args]
            kwargs = {}
        if handler is not None:
            handler(*args, **kwargs)

    def _handle_event(self, type, event = None):
        """
        For a given event, send the event information to all registered handlers
        """
        handlers = chain.from_iterable(self._handlers[namespace]
                                            for namespace
                                            in self._get_namespaces(type))
        for handler_info in handlers:
            if self._send_event_to_handler(event, type, *handler_info):
                break

    def _handle_events(self):
        """
        Run through all the events and handle them.
        """
        self._handling_events = True
        do = True
        while do or len(self._pending) > 0:
            do = False
            for (type, event) in self._events:
                self._handle_event(type, event)
            self._events = self._pending
            self._pending = []
    
    def _unregister_sprite_events(self, sprite):
        for name, handlers in self._handlers.items():
            self._handlers[name] = [h for h in handlers
                                        if (not isinstance(h[0], WeakMethodBound)
                                            or h[0].weak_object_ref() is not sprite)]
            if not self._handlers[name]:
                del self._handlers[name]

    def _unregister(self, event_namespace, handler):
        """
        Unregisters a registered handler for that namespace. Dynamic handler
        strings are supported as well. For more information, see
        `Event Namespaces`_.

        :param str event_namespace: An event namespace
        :param handler: The handler to unregister.
        :type handler: a function or string.
        """
        if event_namespace.endswith(".*"):
            event_namespace = event_namespace[:-2]
        self._handlers[event_namespace] = [h for h
                                             in self._handlers[event_namespace]
                                             if ((not isinstance(h[0], WeakMethodBound) and handler != h[0])
                                             or (isinstance(h[0], WeakMethodBound)
                                                and ((h[0].func is not handler.im_func) 
                                                or (h[0].weak_object_ref() is not handler.im_self))))]
        if not self._handlers[event_namespace]:
            del self._handlers[event_namespace]

    def _clear_namespace(self, namespace):
        """
        Clears all handlers from namespaces that are at least as specific as the
        provided `namespace`. For more information, see `Event Namespaces`_.

        :param str namespace: The complete namespace.
        """
        if namespace.endswith(".*"):
            namespace = namespace[:-2]
        ns = [n for n in self._namespaces if n.startswith(namespace)]
        for namespace in ns:
            del self._handlers[namespace]

    def _clear_all_events(self):
        """
        Completely clear all registered events for this scene. This is a very
        dangerous function, and should almost never be used.
        """
        self._handlers.clear()

    def _get_event_source(self):
        """
        The event source can be used to control event playback. Although
        normally events are given through the operating system, you can enforce
        events being played from a file; there is also a mechanism for recording
        events to a file.
        """
        return self._event_source

    def _set_event_source(self, source):
        self._event_source = source


    # Style Handling
    def __stylize__(self, properties):
        """
        Applies the *properties* to this scene. This is called when a style
        is applied.

        :param properties: a mapping of property names (strings) to values.
        :type properties: dict
        """
        if 'size' in properties:
            size = properties.pop('size')
            self._set_size(size)
        if 'background' in properties:
            background = properties.pop('background')
            if isinstance(background, (tuple, list)):
                bg = spyral.Image(size=self.size)
                bg.fill(background)
            else:
                bg = spyral.Image(background)
            self._set_background(bg)
        if 'layers' in properties:
            layers = properties.pop('layers')
            self._set_layers(layers)
        if len(properties) > 0:
            spyral.exceptions.unused_style_warning(self, properties.iterkeys())

    def load_style(self, path):
        """
        Loads the style file in *path* and applies it to this Scene and any
        Sprites and Views that it contains. Most properties are stylable.

        :param path: The location of the style file to load. Should have the
                     extension ".spys".
        :type path: str
        """
        spyral._style.parse(open(path, "r").read(), self)
        self._apply_style(self)

    def _apply_style(self, obj):
        """
        Applies any loaded styles from this scene to the object.

        :param object obj: Any object
        """
        if not hasattr(obj, "__stylize__"):
            raise spyral.NotStylableError(("%r is not an object"
                                           "which can be styled.") % obj)
        properties = {}
        for cls in reversed(obj.__class__.__mro__[:-1]):
            name = cls.__name__
            if name not in self._style_properties:
                continue
            properties.update(self._style_properties[name])
        if hasattr(obj, "__style__"):
            name = getattr(obj, "__style__")
            if name in self._style_properties:
                properties.update(self._style_properties[name])
        if properties != {}:
            obj.__stylize__(properties)

    def add_style_function(self, name, function):
        """
        Adds a new function that will then be available to be used in a
        stylesheet file.

        Example::

            import random
            class MyScene(spyral.Scene):
                def __init__(self):
                    ...
                    self.load_style("my_style.spys")
                    self.add_style_function("randint", random.randint)
                    # inside of style file you can now use the randint function!
                    ...


        :param name: The name the function will go by in the style file.
        :type name: string
        :param function: The actual function to add to the style file.
        :type function: function
        """
        self._style_functions[name] = function


    # Rendering
    def _get_size(self):
        """
        Read-only property that returns a :class:`Vec2D <spyral.Vec2D>` of the
        width and height of the Scene's size.  This is the coordinate space that
        you place Sprites in, but it does not have to match up 1:1 to the window
        (which could be scaled). This property can only be set once.
        """
        if self._size is None:
            raise spyral.SceneHasNoSizeException("You should specify a size in "
                                                 "the constructor or in a "
                                                 "style file before other "
                                                 "operations.")
        return self._size

    def _set_size(self, size):
        # This can only be called once.
        rsize = self._surface.get_size()
        self._size = size
        self._scale = (rsize[0] / size[0],
                       rsize[1] / size[1])

    def _get_width(self):
        """
        The width of this scene. Read-only number.
        """
        return self._get_size()[0]

    def _get_height(self):
        """
        The height of this scene. Read-only number.
        """
        return self._get_size()[1]

    def _get_rect(self):
        """
        Returns a :class:`Rect <spyral.Rect>` representing the position (0, 0)
        and size of this Scene.
        """
        return spyral.Rect((0,0), self.size)

    def _get_scene(self):
        """
        Returns this scene. Read-only.
        """
        return self._scene()

    def _get_parent(self):
        """
        Returns this scene. Read-only.
        """
        return self._scene()


    size = property(_get_size)
    width = property(_get_width)
    height = property(_get_height)
    scene = property(_get_scene)
    parent = property(_get_parent)
    rect = property(_get_rect)

    def _set_background(self, image):
        self._background_image = image
        self._background_version = image._version
        surface = image._surf
        scene = spyral._get_executing_scene()
        if surface.get_size() != self.size:
            raise spyral.BackgroundSizeError("Background size must match "
                                             "the scene's size.")
        size = self._surface.get_size()
        self._background = pygame.transform.smoothscale(surface, size)
        self._clear_this_frame.append(self._background.get_rect())

    def _get_background(self):
        """
        The background of this scene. The given :class:`Image <spyral.Image>`
        must be the same size as the Scene. A background will be handled
        intelligently by Spyral; it knows to only redraw portions of it rather
        than the whole thing, unlike a Sprite.
        """
        return self._background_image

    background = property(_get_background, _set_background)

    def _register_sprite(self, sprite):
        """
        Internal method to add this sprite to the scene
        """
        self._sprites.add(sprite)
        # Add the view and its parents to the invalidating_views for the sprite
        parent_view = sprite._parent()
        while parent_view != self:
            if parent_view not in self._invalidating_views:
                self._invalidating_views[parent_view] = set()
            self._invalidating_views[parent_view].add(sprite)
            parent_view = parent_view.parent

    def _unregister_sprite(self, sprite):
        """
        Internal method to remove this sprite from the scene
        """
        if sprite in self._sprites:
            self._sprites.remove(sprite)
        if sprite in self._collision_boxes:
            del self._collision_boxes[sprite]
        for view in self._invalidating_views.keys():
            self._invalidating_views[view].discard(sprite)
        self._unregister_sprite_events(sprite)

    def _kill_view(self, view):
        """
        Remove all references to the view from within this Scene.
        """
        if view in self._invalidating_views:
            del self._invalidating_views[view]
        if view in self._collision_boxes:
            del self._collision_boxes[view]
        self._layer_tree.remove_view(view)

    def _blit(self, blit):
        """
        Apply any scaling associated with the Scene to the Blit, then finalize
        it. Note that Scene's don't apply cropping.
        """
        blit.apply_scale(self._scale)
        blit.finalize()
        self._blits.append(blit)

    def _static_blit(self, key, blit):
        """
        Identifies that this sprite will be statically blit from now, and
        applies scaling and finalization to the blit.
        """
        blit.apply_scale(self._scale)
        blit.finalize()
        self._static_blits[key] = blit
        self._clear_this_frame.append(blit.rect)

    def _invalidate_views(self, view):
        """
        Expire any sprites that belong to the view being invalidated.
        """
        if view in self._invalidating_views:
            for sprite in self._invalidating_views[view]:
                sprite._expire_static()

    def _remove_static_blit(self, key):
        """
        Removes this sprite from the static blit list
        """
        try:
            x = self._static_blits.pop(key)
            self._clear_this_frame.append(x.rect)
        except:
            pass

    def _draw(self):
        """
        Internal method that is called by the
        :class:`Director <spyral.Director>` at the end of every .render() call
        to do the actual drawing.
        """

        # This function sits in a potential hot loop
        # For that reason, some . lookups are optimized away
        screen = self._surface
        
        # First we test if the background has been updated
        if self._background_version != self._background_image._version:
            self._set_background(self._background_image)

        # Let's finish up any rendering from the previous frame
        # First, we put the background over all blits
        x = self._background.get_rect()
        for i in self._clear_this_frame + self._soft_clear:
            i = x.clip(i)
            b = self._background.subsurface(i)
            screen.blit(b, i)

        # Now, we need to blit layers, while simultaneously re-blitting
        # any static blits which were obscured
        static_blits = len(self._static_blits)
        dynamic_blits = len(self._blits)
        blits = self._blits + list(self._static_blits.values())
        blits.sort(key=operator.attrgetter('layer'))

        # Clear this is a list of things which need to be cleared
        # on this frame and marked dirty on the next
        clear_this = self._clear_this_frame
        # Clear next is a list which will become clear_this on the next
        # draw cycle. We use this for non-static blits to say to clear
        # That spot on the next frame
        clear_next = self._clear_next_frame
        # Soft clear is a list of things which need to be cleared on
        # this frame, but unlike clear_this, they won't be cleared
        # on future frames. We use soft_clear to make things static
        # as they are drawn and then no longer cleared
        soft_clear = self._soft_clear
        self._soft_clear = []
        screen_rect = screen.get_rect()
        drawn_static = 0

        blit_flags_available = pygame.version.vernum < (1, 8)

        for blit in blits:
            blit_rect = blit.rect
            blit_flags = blit.flags if blit_flags_available else 0
            # If a blit is entirely off screen, we can ignore it altogether
            if not screen_rect.contains(blit_rect) and not screen_rect.colliderect(blit_rect):
                continue
            if blit.static:
                skip_soft_clear = False
                for rect in clear_this:
                    if blit_rect.colliderect(rect):
                        screen.blit(blit.surface, blit_rect, None, blit_flags)
                        skip_soft_clear = True
                        clear_this.append(blit_rect)
                        self._soft_clear.append(blit_rect)
                        drawn_static += 1
                        break
                if skip_soft_clear:
                    continue
                for rect in soft_clear:
                    if blit_rect.colliderect(rect):
                        screen.blit(blit.surface, blit_rect, None, blit_flags)
                        soft_clear.append(blit.rect)
                        drawn_static += 1
                        break
            else:
                if screen_rect.contains(blit_rect):
                    r = screen.blit(blit.surface, blit_rect, None, blit_flags)
                    clear_next.append(r)
                elif screen_rect.colliderect(blit_rect):
                    # Todo: See if this is ever called. Shouldn't be.
                    x = blit.rect.clip(screen_rect)
                    y = x.move(-blit_rect.left, -blit_rect.top)
                    b = blit.surface.subsurface(y)
                    r = screen.blit(blit.surface, blit_rect, None, blit_flags)
                    clear_next.append(r)

        #pygame.display.set_caption("%d / %d static, %d dynamic. %d ups, %d fps" %
        #                           (drawn_static, static_blits,
        #                            dynamic_blits, self.clock.ups,
        #                            self.clock.fps))
        # Do the display update
        pygame.display.update(self._clear_next_frame + self._clear_this_frame)
        # Get ready for the next call
        self._clear_this_frame = self._clear_next_frame
        self._clear_next_frame = []
        self._blits = []

    def redraw(self):
        """
        Force the entire visible window to be completely redrawn.

        This is particularly useful for Sugar, which loves to put artifacts over
        our window.
        """
        self._clear_this_frame.append(pygame.Rect(self._rect))

    def _get_layer_position(self, view, layer):
        """
        For the given view and layer, calculate its position in the depth order.
        """
        return self._layer_tree.get_layer_position(view, layer)

    def _set_view_layer(self, view, layer):
        """
        Set the layer that the view is on within layer tree.
        """
        self._layer_tree.set_view_layer(view, layer)

    def _set_view_layers(self, view, layers):
        """
        Set the view's layers within the layer tree.
        """
        self._layer_tree.set_view_layers(view, layers)

    def _add_view(self, view):
        """
        Register the given view within this scene.
        """
        self._layer_tree.add_view(view)

    def _set_layers(self, layers):
        """
        Potential caveat: If you change layers after blitting, previous blits
        may be wrong for a frame, static ones wrong until they expire
        """
        if self._layers == []:
            self._layer_tree.set_view_layers(self, layers)
            self._layers = layers
        elif self._layers == layers:
            pass
        else:
            raise spyral.LayersAlreadySetError("You can only define the layers "
                                               "for a scene once.")

    def _get_layers(self):
        """
        A list of strings representing the layers that are available for this
        scene. The first layer is at the bottom, and the last is at the top.

        Note that the layers can only be set once.
        """
        return self._layers

    layers = property(_get_layers, _set_layers)

    def _add_child(self, entity):
        """
        Add this child to the Scene; since only Views care about their children,
        this function does nothing.
        """
        pass

    def _remove_child(self, entity):
        """
        Remove this child to the Scene; since only Views care about their
        children, this function does nothing.
        """
        pass

    def _warp_collision_box(self, box):
        """
        Finalize the collision box. Don't apply scaling, because that's only
        for external rendering purposes.
        """
        box.finalize()
        return box

    def _set_collision_box(self, entity, box):
        """
        Registers the given entity (a View or Sprite) with the given
        CollisionBox.
        """
        self._collision_boxes[entity] = box

    def collide_sprites(self, first, second):
        """
        Returns whether the first sprite is colliding with the second.

        :param first: A sprite or view
        :type first: :class:`Sprite <spyral.Sprite>` or a
                     :class:`View <spyral.View>`
        :param second: Another sprite or view
        :type second: :class:`Sprite <spyral.Sprite>` or a
                      :class:`View <spyral.View>`
        :returns: A ``bool``
        """
        if first not in self._collision_boxes or second not in self._collision_boxes:
            return False
        first_box = self._collision_boxes[first]
        second_box = self._collision_boxes[second]
        return first_box.collide_rect(second_box)

    def collide_point(self, sprite, point):
        """
        Returns whether the sprite is colliding with the point.

        :param sprite: A sprite
        :type sprite: :class:`Sprite <spyral.Sprite>`
        :param point: A point
        :type point: :class:`Vec2D <spyral.Vec2D>`
        :returns: A ``bool``
        """
        if sprite not in self._collision_boxes:
            return False
        sprite_box = self._collision_boxes[sprite]
        return sprite_box.collide_point(point)

    def collide_rect(self, sprite, rect):
        """
        Returns whether the sprite is colliding with the rect.

        :param sprite: A sprite
        :type sprite: :class:`Sprite <spyral.Sprite>`
        :param rect: A rect
        :type rect: :class:`Rect <spyral.Rect>`
        :returns: A ``bool``
        """
        if sprite not in self._collision_boxes:
            return False
        sprite_box = self._collision_boxes[sprite]
        return sprite_box.collide_rect(rect)

########NEW FILE########
__FILENAME__ = sprite
import spyral
import pygame
from weakref import ref as _wref
import math


_all_sprites = []

def _switch_scene():
    """
    Ensure that dead sprites are removed from the list and that sprites are
    redrawn on a scene change.
    """
    global _all_sprites
    _all_sprites = [s for s in _all_sprites
                      if s() is not None and s()._expire_static()]


class Sprite(object):
    """
    Sprites are how images are positioned and drawn onto the screen.
    They aggregate together information such as where to be drawn,
    layering information, and more.

    :param parent: The parent that this Sprite will belong to.
    :type parent: :class:`View <spyral.View>` or :class:`Scene <spyral.Scene>`
    """

    def __stylize__(self, properties):
        """
        The __stylize__ function is called during initialization to set up
        properties taken from a style function. Sprites that want to override
        default styling behavior should implement this class, although that
        should rarely be necessary.
        """
        if 'image' in properties:
            image = properties.pop('image')
            if isinstance(image, str):
                image = spyral.Image(image)
            setattr(self, 'image', image)
        simple = ['pos', 'x', 'y', 'position', 'anchor', 'layer', 'visible',
                  'scale', 'scale_x', 'scale_y', 'flip_x', 'flip_y', 'angle',
                  'mask']
        for property in simple:
            if property in properties:
                value = properties.pop(property)
                setattr(self, property, value)
        if len(properties) > 0:
            spyral.exceptions.unused_style_warning(self, properties.iterkeys())

    def __init__(self, parent):
        _all_sprites.append(_wref(self))
        self._age = 0
        self._static = False
        self._image = None
        self._image_version = None
        self._layer = None
        self._computed_layer = 1
        self._make_static = False
        self._pos = spyral.Vec2D(0, 0)
        self._blend_flags = 0
        self._visible = True
        self._anchor = 'topleft'
        self._offset = spyral.Vec2D(0, 0)
        self._scale = spyral.Vec2D(1.0, 1.0)
        self._scaled_image = None
        self._parent = _wref(parent)
        self._scene = _wref(parent.scene)
        self._angle = 0
        self._crop = None
        self._transform_image = None
        self._transform_offset = spyral.Vec2D(0, 0)
        self._flip_x = False
        self._flip_y = False
        self._animations = []
        self._progress = {}
        self._mask = None

        parent._add_child(self)

        self._scene()._register_sprite(self)
        self._scene()._apply_style(self)
        spyral.event.register('director.render', self._draw,
                              scene=self._scene())

    def _set_static(self):
        """
        Forces this class to be static, indicating that it will not be redrawn
        every frame.
        """
        self._make_static = True
        self._static = True

    def _expire_static(self):
        """
        Force this class to no longer be static; it will be redrawn for a few
        frames, until it has sufficiently aged. This also triggers the collision
        box to be recomputed.
        """
        # Expire static is part of the private API which must
        # be implemented by Sprites that wish to be static.
        if self._static:
            self._scene()._remove_static_blit(self)
        self._static = False
        self._age = 0
        self._set_collision_box()
        return True

    def _recalculate_offset(self):
        """
        Recalculates this sprite's offset based on its position, transform
        offset, anchor, its image, and the image's scaling.
        """
        if self.image is None:
            return
        size = self._scale * self._image.size

        offset = spyral.util._anchor_offset(self._anchor, size[0], size[1])

        self._offset = spyral.Vec2D(offset) - self._transform_offset

    def _recalculate_transforms(self):
        """
        Calculates the transforms that need to be applied to this sprite's
        image. In order: flipping, scaling, and rotation.
        """
        source = self._image._surf

        # flip
        if self._flip_x or self._flip_y:
            source = pygame.transform.flip(source, self._flip_x, self._flip_y)

        # scale
        if self._scale != (1.0, 1.0):
            new_size = self._scale * self._image.size
            new_size = (int(new_size[0]), int(new_size[1]))
            if 0 in new_size:
                self._transform_image = spyral.image._new_spyral_surface((1,1))
                self._recalculate_offset()
                self._expire_static()
                return
            new_surf = spyral.image._new_spyral_surface(new_size)
            source = pygame.transform.smoothscale(source, new_size, new_surf)

        # rotate
        if self._angle != 0:
            angle = 180.0 / math.pi * self._angle % 360
            old = spyral.Vec2D(source.get_rect().center)
            source = pygame.transform.rotate(source, angle).convert_alpha()
            new = source.get_rect().center
            self._transform_offset = old - new

        self._transform_image = source
        self._recalculate_offset()
        self._expire_static()

    def _evaluate(self, animation, progress):
        """
        Performs a step of the given animation, setting any properties that will
        change as a result of the animation (e.g., x position).
        """        
        values = animation.evaluate(self, progress)
        for property in animation.properties:
            if property in values:
                setattr(self, property, values[property])

    def _run_animations(self, delta):
        """
        For a given time-step (delta), perform a step of all the animations
        associated with this sprite.
        """
        completed = []
        for animation in self._animations:
            self._progress[animation] += delta
            progress = self._progress[animation]
            if progress > animation.duration:
                self._evaluate(animation, animation.duration)
                if animation.loop is True:
                    self._evaluate(animation, progress - animation.duration)
                    self._progress[animation] = progress - animation.duration
                elif animation.loop:
                    current = progress - animation.duration + animation.loop
                    self._evaluate(animation, current)
                    self._progress[animation] = current
                else:
                    completed.append(animation)
            else:
                self._evaluate(animation, progress)

        for animation in completed:
            self.stop_animation(animation)


    # Getters and Setters
    def _get_rect(self):
        """
        Returns a :class:`Rect <spyral.Rect>` representing the position and size
        of this Sprite's image. Note that if you change a property of this rect
        that it will not actually update this sprite's properties:
        
        >>> my_sprite.rect.top = 10
        
        Does not adjust the y coordinate of `my_sprite`. Changing the rect will
        adjust the sprite however
        
        >>> my_sprite.rect = spyral.Rect(10, 10, 64, 64)
        """
        return spyral.Rect(self._pos, self.size)

    def _set_rect(self, *rect):
        if len(rect) == 1:
            r = rect[0]
            self.x, self.y = r.x, r.y
            self.width, self.height = r.w, r.h
        elif len(rect) == 2:
            self.pos = rect[0]
            self.size = rect[1]
        elif len(args) == 4:
            self.x, self.y, self.width, self.height = args
        else:
            raise ValueError("TODO: You done goofed.")

    def _get_pos(self):
        """
        The position of a sprite in 2D coordinates, represented as a
        :class:`Vec2D <spyral.Vec2D>`
        """
        return self._pos

    def _set_pos(self, pos):
        if pos == self._pos:
            return
        self._pos = spyral.Vec2D(pos)
        self._expire_static()

    def _get_layer(self):
        """
        String. The name of the layer this sprite belongs to. See
        :ref:`layering <ref.layering>` for more.
        """
        return self._layer

    def _set_layer(self, layer):
        if layer == self._layer:
            return
        self._layer = layer
        self._computed_layer = self._scene()._get_layer_position(self._parent(),
                                                                 layer)
        self._expire_static()

    def _get_image(self):
        """
        The :class:`Image <spyral.Image>` for this sprite.
        """
        return self._image

    def _set_image(self, image):
        if self._image is image:
            return
        self._image = image
        self._image_version = image._version
        self._recalculate_transforms()
        self._expire_static()

    def _get_x(self):
        """
        The x coordinate of the sprite, which will remain synced with the
        position. Number.
        """
        return self._get_pos()[0]

    def _set_x(self, x):
        self._set_pos((x, self._get_y()))

    def _get_y(self):
        """
        The y coordinate of the sprite, which will remain synced with the
        position. Number
        """
        return self._get_pos()[1]

    def _set_y(self, y):
        self._set_pos((self._get_x(), y))

    def _get_anchor(self):
        """
        Defines an :ref:`anchor point <ref.anchors>` where coordinates are relative to
        on the image. String.
        """
        return self._anchor

    def _set_anchor(self, anchor):
        if anchor == self._anchor:
            return
        self._anchor = anchor
        self._recalculate_offset()
        self._expire_static()

    def _get_width(self):
        """
        The width of the image after all transforms. Number.
        """
        if self._transform_image:
            return self._transform_image.get_width()

    def _set_width(self, width):
        self._set_scale((width / self._get_width(), self._scale[1]))

    def _get_height(self):
        """
        The height of the image after all transforms. Number.
        """
        if self._transform_image:
            return self._transform_image.get_height()

    def _set_height(self, height):
        self._set_scale((self._scale[0], height / self._get_height()))

    def _get_size(self):
        """
        The size of the image after all transforms (:class:`Vec2D <spyral.Vec2D>`).
        """
        if self._transform_image:
            return spyral.Vec2D(self._transform_image.get_size())
        return spyral.Vec2D(0, 0)

    def _set_size(self, size):
        self._set_scale((width / self._get_width(),
                         height / self._get_height()))

    def _get_scale(self):
        """
        A scale factor for resizing the image. When read, it will always contain
        a :class:`spyral.Vec2D` with an x factor and a y factor, but it can be
        set to a numeric value which wil ensure identical scaling along both
        axes.
        """
        return self._scale

    def _set_scale(self, scale):
        if isinstance(scale, (int, float)):
            scale = spyral.Vec2D(scale, scale)
        if self._scale == scale:
            return
        self._scale = spyral.Vec2D(scale)
        self._recalculate_transforms()
        self._expire_static()

    def _get_scale_x(self):
        """
        The x factor of the scaling that's kept in sync with scale. Number.
        """
        return self._scale[0]

    def _set_scale_x(self, x):
        self._set_scale((x, self._scale[1]))

    def _get_scale_y(self):
        """
        The y factor of the scaling that's kept in sync with scale. Number.
        """
        return self._scale[1]

    def _set_scale_y(self, y):
        self._set_scale((self._scale[0], y))

    def _get_angle(self):
        """
        An angle to rotate the image by. Rotation is computed after scaling and
        flipping, and keeps the center of the original image aligned with the
        center of the rotated image.
        """
        return self._angle

    def _set_angle(self, angle):
        if self._angle == angle:
            return
        self._angle = angle
        self._recalculate_transforms()

    def _get_flip_x(self):
        """
        A boolean that determines whether the image should be flipped
        horizontally.
        """
        return self._flip_x

    def _set_flip_x(self, flip_x):
        if self._flip_x == flip_x:
            return
        self._flip_x = flip_x
        self._recalculate_transforms()

    def _get_flip_y(self):
        """
        A boolean that determines whether the image should be flipped
        vertically.
        """
        return self._flip_y

    def _set_flip_y(self, flip_y):
        if self._flip_y == flip_y:
            return
        self._flip_y = flip_y
        self._recalculate_transforms()

    def _get_visible(self):
        """
        A boolean indicating whether this sprite should be drawn.
        """
        return self._visible

    def _set_visible(self, visible):
        if self._visible == visible:
            return
        self._visible = visible
        self._expire_static()

    def _get_scene(self):
        """
        The top-level scene that this sprite belongs to. Read-only.
        """
        return self._scene()

    def _get_parent(self):
        """
        The parent of this sprite, either a :class:`View <spyral.View>` or a
        :class:`Scene <spyral.Scene>`. Read-only.
        """
        return self._parent()

    def _get_mask(self):
        """
        A :class:`Rect <spyral.Rect>` to use instead of the current image's rect
        for computing collisions. `None` if the image's rect should be used.
        """
        return self._mask

    def _set_mask(self, mask):
        self._mask = mask
        self._set_collision_box()

    pos = property(_get_pos, _set_pos)
    layer = property(_get_layer, _set_layer)
    image = property(_get_image, _set_image)
    x = property(_get_x, _set_x)
    y = property(_get_y, _set_y)
    anchor = property(_get_anchor, _set_anchor)
    scale = property(_get_scale, _set_scale)
    scale_x = property(_get_scale_x, _set_scale_x)
    scale_y = property(_get_scale_y, _set_scale_y)
    width = property(_get_width, _set_width)
    height = property(_get_height, _set_height)
    size = property(_get_size, _set_size)
    angle = property(_get_angle, _set_angle)
    flip_x = property(_get_flip_x, _set_flip_x)
    flip_y = property(_get_flip_y, _set_flip_y)
    visible = property(_get_visible, _set_visible)
    rect = property(_get_rect, _set_rect)
    scene = property(_get_scene)
    parent = property(_get_parent)
    mask = property(_get_mask, _set_mask)

    def _draw(self):
        """
        Internal method for generating this sprite's blit, unless it is
        invisible or currently static. If it has aged sufficiently or is being
        forced, it will become static; otherwise, it ages one step.
        """
        if not self.visible:
            return
        if self._image is None:
            raise spyral.NoImageError("A sprite must have an image"
                                      " set before it can be drawn.")
        if self._image_version != self._image._version:
            self._image_version = self._image._version
            self._recalculate_transforms()
            self._expire_static()
        if self._static:
            return

        area = spyral.Rect(self._transform_image.get_rect())
        b = spyral.util._Blit(self._transform_image,
                              self._pos - self._offset,
                              area,
                              self._computed_layer,
                              self._blend_flags,
                              False)

        if self._make_static or self._age > 4:
            b.static = True
            self._make_static = False
            self._static = True
            self._parent()._static_blit(self, b)
            return
        self._parent()._blit(b)
        self._age += 1

    def _set_collision_box(self):
        """
        Updates this sprite's collision box.
        """
        if self.image is None:
            return
        if self._mask is None:
            area = spyral.Rect(self._transform_image.get_rect())
        else:
            area = self._mask
        c = spyral.util._CollisionBox(self._pos - self._offset, area)
        warped_box = self._parent()._warp_collision_box(c)
        self._scene()._set_collision_box(self, warped_box.rect)

    def kill(self):
        """
        When you no longer need a Sprite, you can call this method to have it
        removed from the Scene. This will not remove the sprite entirely from
        memory if there are other references to it; if you need to do that,
        remember to ``del`` the reference to it.
        """
        self._scene()._unregister_sprite(self)
        self._scene()._remove_static_blit(self)
        self._parent()._remove_child(self)

    def animate(self, animation):
        """
        Animates this sprite given an animation. Read more about
        :class:`animation <spyral.animation>`.

        :param animation: The animation to run.
        :type animation: :class:`Animation <spyral.Animation>`
        """
        for a in self._animations:
            repeats = a.properties.intersection(animation.properties)
            if repeats:
                # Loop over all repeats
                raise ValueError("Cannot animate on propies %s twice" %
                                 (str(repeats),))
        if len(self._animations) == 0:
            spyral.event.register('director.update',
                                  self._run_animations,
                                  ('delta', ),
                                  scene=self._scene())
        self._animations.append(animation)
        self._progress[animation] = 0
        self._evaluate(animation, 0.0)
        e = spyral.Event(animation=animation, sprite=self)
        # Loop over all possible properties
        for property in animation.properties:
            spyral.event.handle("%s.%s.animation.start" % (self.__class__.__name__,
                                                           property),
                                e)

    def stop_animation(self, animation):
        """
        Stops a given animation currently running on this sprite.

        :param animation: The animation to stop.
        :type animation: :class:`Animation <spyral.Animation>`
        """
        if animation in self._animations:
            self._animations.remove(animation)
            del self._progress[animation]
            e = spyral.Event(animation=animation, sprite=self)
            for property in animation.properties:
                spyral.event.handle("%s.%s.animation.end" % (self.__class__.__name__,
                                                            property),
                                    e)
            if len(self._animations) == 0:
                spyral.event.unregister('director.update',
                                        self._run_animations,
                                        scene=self._scene())


    def stop_all_animations(self):
        """
        Stops all animations currently running on this sprite.
        """
        for animation in self._animations:
            self.stop_animation(animation)

    def collide_sprite(self, other):
        """
        Returns whether this sprite is currently colliding with the other
        sprite. This collision will be computed correctly regarding the sprites
        offsetting and scaling within their views.

        :param other: The other sprite
        :type other: :class:`Sprite <spyral.Sprite>`
        :returns: ``bool`` indicating whether this sprite is colliding with the
                  other sprite.
        """
        return self._scene().collide_sprites(self, other)

    def collide_point(self, point):
        """
        Returns whether this sprite is currently colliding with the position.
        This uses the appropriate offsetting for the sprite within its views.

        :param point: The point (relative to the window dimensions).
        :type point: :class:`Vec2D <spyral.Vec2D>`
        :returns: ``bool`` indicating whether this sprite is colliding with the
                  position.
        """
        return self._scene().collide_point(self, point)

    def collide_rect(self, rect):
        """
        Returns whether this sprite is currently colliding with the rect. This
        uses the appropriate offsetting for the sprite within its views.

        :param rect: The rect (relative to the window dimensions).
        :type rect: :class:`Rect <spyral.Rect>`
        :returns: ``bool`` indicating whether this sprite is colliding with the
                  rect.
        """
        return self._scene().collide_rect(self, rect)
        
########NEW FILE########
__FILENAME__ = util
"""When they have no other home, functions and classes are added here.
Eventually, they should be refactored to a more permanent home."""

import spyral
import math
import pygame

def _anchor_offset(anchor, width, height):
    """
    Given an `anchor` position (either a string or a 2-tuple position), finds
    the correct offset in a rectangle of size (`width`, `height`). If the
    `anchor` is a 2-tuple (or Vec2D), then it multiplies both components by -1.

    >>> anchor_offset("topleft", 100, 100)
    Vec2D(0,0)
    >>> anchor_offset("bottomright", 100, 100)
    Vec2D(100,100)
    >>> anchor_offset("center", 100, 100)
    Vec2D(50,50)
    >>> anchor_offset((10, 10), 100, 100)
    Vec2D(-10,-10)

    For a complete list of the anchor positions, see `Anchor Offset Lists`_.

    :param anchor: The (possibly named) position to offset by.
    :type anchor: string or :class:`Vec2D <spyral.Vec2D>`
    :param width: the width of the rectangle to offset in.
    :type width: int
    :param height: the height of the rectangle to offset in.
    :type height: int
    :rtype: :class:`Vec2D <spyral.Vec2D>`
    """
    w = width
    h = height
    a = anchor
    if a == 'topleft':
        offset = (0, 0)
    elif a == 'topright':
        offset = (w, 0)
    elif a == 'midtop':
        offset = (w / 2., 0)
    elif a == 'bottomleft':
        offset = (0, h)
    elif a == 'bottomright':
        offset = (w, h)
    elif a == 'midbottom':
        offset = (w / 2., h)
    elif a == 'midleft':
        offset = (0, h / 2.)
    elif a == 'midright':
        offset = (w, h / 2.)
    elif a == 'center':
        offset = (w / 2., h / 2.)
    else:
        offset = a * spyral.Vec2D(-1, -1)
    return spyral.Vec2D(offset)

@spyral.memoize._ImageMemoize
def scale_surface(s, target_size):
    """
    Internal method to scale a surface `s` by a float `factor`. Uses memoization
    to improve performance.

    :param target_size: The end size of the surface
    :type target_size: :class:`Vec2D <spyral.Vec2D>`
    :returns: A new surface, or the original (both pygame surfaces).
    """
    new_size = (int(math.ceil(target_size[0])),
                int(math.ceil(target_size[1])))
    if new_size == s.get_size():
        return s
    t = pygame.transform.smoothscale(s, new_size,
                                     spyral.image._new_spyral_surface(new_size))
    return t

class _Blit(object):
    """
    An internal class to represent a drawable `surface` with additional data
    (e.g. `rect` representing its location on screen, whether it's `static`).

    .. attribute::surface

        The internal Pygame source surface use to render this blit.

    .. attribute::position

        The current position of this Blit (:class:`Vec2D <spyral.Vec2D>`).

    .. attribute::area

        The portion of the surface to be drawn to the screen
        (:class:`Rect <spyral.Rect>`).

    .. attribute::layer

        The layer of this blit within the scene (`str).

    .. attribute::flags

        Any drawing flags (presently unused).

    .. attribute::static

        Whether this Blit is static.

    .. attribute::final_size

        The final size, set seperately to defer scaling.

    .. attribute::rect

        A rect representing the final position and size of this blit
        (:class:`Rect <spyral.Rect>`).

    """
    __slots__ = ['surface', 'position', 'rect', 'area', 'layer',
                 'flags', 'static', 'clipping', 'final_size']
    def __init__(self, surface, position, area, layer, flags, static):
        self.surface = surface   # pygame surface
        self.position = position # coordinates to draw at
        self.area = area         # portion of the surface to be drawn to screen
        self.layer = layer       # layer in scene
        self.flags = flags       # any drawing flags (currently unusued)
        self.static = static     # static blits haven't changed

        # Final size of the surface, the scaling will happen late
        self.final_size = spyral.Vec2D(surface.get_size())
        # Rect is only for finalized sprites
        self.rect = None

    def apply_scale(self, scale):
        """
        Applies the scaling factor to this blit.

        :param scale: The scaling factor
        :type scale: :class:`Vec2D <spyral.Vec2D>`
        """
        self.position = self.position * scale
        self.final_size = self.final_size * scale
        self.area = spyral.Rect(self.area.topleft * scale,
                                self.area.size * scale)

    def clip(self, rect):
        """
        Applies any necessary cropping to this blit

        :param rect: The new maximal size of the blit.
        :type rect: :class:`Rect <spyral.Rect>`
        """
        self.area = self.area.clip(spyral.Rect(rect))

    def finalize(self):
        """
        Performs all the final calculations for this blit and calculates the
        rect.
        """
        self.surface = scale_surface(self.surface, self.final_size)
        self.surface = self.surface.subsurface(self.area._to_pygame())
        self.rect = pygame.Rect((self.position[0], self.position[1]),
                                self.surface.get_size())

class _CollisionBox(object):
    """
    An internal class for managing the collidable area for a sprite or view.
    In many ways, this is a reduced form of a _Blit.

    .. attribute::position

        The current position of this CollisionBox
        (:class:`Vec2D <spyral.Vec2D>`).

    .. attribute::area

        The current offset and size of this CollisionBox.
        (:class:`Rect <spyral.Rect>`).

    .. attribute::rect

        A rect representing the final position and size of this CollisionBox.
        (:class:`Rect <spyral.Rect>`).

    """
    __slots__ = ['position', 'rect', 'area']
    def __init__(self, position, area):
        self.position = position
        self.area = area
        self.rect = None

    def apply_scale(self, scale):
        self.position = self.position * scale
        self.area = spyral.Rect(self.area.topleft * scale,
                                self.area.size * scale)

    def clip(self, rect):
        self.area = self.area.clip(spyral.Rect(rect))

    def finalize(self):
        self.rect = spyral.Rect(self.position, self.area.size)
        
########NEW FILE########
__FILENAME__ = vector
"""A vector is a class that behaves like a 2-tuple, but with convenient
methods."""

from __future__ import division
import math

class Vec2D(object):
    """
    Vec2D is a class that behaves like a 2-tuple, but with a number
    of convenient methods for vector calculation and manipulation.
    It can be created with two arguments for x,y, or by passing a
    2-tuple.

    In addition to the methods documented below, Vec2D supports
    the following:

    >>> from spyral import Vec2D
    >>> v1 = Vec2D(1,0)
    >>> v2 = Vec2D((0,1))    # Note 2-tuple argument!

    Tuple access, or x,y attribute access

    >>> v1.x
    1
    >>> v1.y
    0
    >>> v1[0]
    1
    >>> v1[1]
    0

    Addition, subtraction, and multiplication

    >>> v1 + v2
    Vec2D(1, 1)
    >>> v1 - v2
    Vec2D(1, -1)
    >>> 3 * v1
    Vec2D(3, 0)
    >>> (3, 4) * (v1+v2)
    Vec2D(3, 4)

    Compatibility with standard tuples

    >>> v1 + (1,1)
    Vec2D(2, 1)
    >>> (1,1) + v1
    Vec2D(2, 1)

    """
    __slots__ = ['x', 'y']

    def __init__(self, *args):
        if len(args) == 1:
            self.x, self.y = args[0]
        elif len(args) == 2:
            self.x, self.y = args[0], args[1]
        else:
            raise ValueError("Invalid Vec2D arguments")

    def __len__(self):
        return 2

    def __getitem__(self, key):
        if key == 0:
            return self.x
        if key == 1:
            return self.y
        raise IndexError("Invalid subscript %s" % (str(key)))

    def __repr__(self):
        return 'Vec2D(%s, %s)' % (str(self.x), str(self.y))

    def __eq__(self, o):
        try:
            return self.x == o[0] and self.y == o[1]
        except (IndexError, TypeError):
            return False

    def __ne__(self, o):
        return not self.__eq__(o)

    def __add__(self, o):
        try:
            return Vec2D(self.x + o[0], self.y + o[1])
        except (IndexError, TypeError):
            return NotImplemented

    __radd__ = __add__

    def __sub__(self, o):
        try:
            return Vec2D(self.x - o[0], self.y - o[1])
        except (IndexError, TypeError):
            print self, o
            return NotImplemented

    __isub__ = __sub__

    def __rsub__(self, o):
        try:
            return Vec2D(o[0] - self.x, o[1] - self.y)
        except (IndexError, TypeError):
            return NotImplemented

    def __mul__(self, o):
        try:
            return Vec2D(self.x * o[0], self.y * o[1])
        except (IndexError, TypeError):
            pass

        if isinstance(o, (int, long, float)):
            return Vec2D(self.x * o, self.y * o)

        return NotImplemented

    __rmul__ = __mul__
    __imul__ = __mul__

    def __div__(self, o):
        try:
            return Vec2D(self.x / o[0], self.y / o[1])
        except (IndexError, TypeError):
            pass

        if isinstance(o, (int, long, float)):
            return Vec2D(self.x / o, self.y / o)

    __truediv__ = __div__

    def __neg__(self):
        return (-self.x, -self.y)

    def __pos__(self):
        return self

    def get_length(self):
        """
        Return the length of this vector.

        :rtype: float
        """
        return math.sqrt(self.x * self.x + self.y * self.y)

    def get_length_squared(self):
        """
        Return the squared length of this vector.

        :rtype: int
        """
        return self.x * self.x + self.y * self.y

    def get_angle(self):
        """
        Return the angle this vector makes with the positive x axis.

        :rtype: float
        """
        return math.atan2(self.y, self.x)

    def perpendicular(self):
        """
        Returns a new :class:`Vec2D <spyral.Vec2D>` perpendicular to this one.

        :rtype: :class:`Vec2D <spyral.Vec2D>`
        """
        return Vec2D(-self.y, self.x)

    def dot(self, other):
        """
        Returns the `dot product <http://en.wikipedia.org/wiki/Dot_product>`_
        of this point with another.

        :param other: the other point
        :type other: 2-tuple or :class:`Vec2D <spyral.Vec2D>`
        :rtype: int
        """
        return self.x * other[0] + self.y * other[1]

    def distance(self, other):
        """
        Returns the distance from this :class:`Vec2D <spyral.Vec2D>` to the
        other point.

        :param other: the other point
        :type other: 2-tuple or :class:`Vec2D <spyral.Vec2D>`
        :rtype: float
        """
        return (other - self).get_length()

    def angle(self, other):
        """
        Returns the angle between this point and another point.

        :param other: the other point
        :type other: 2-tuple or :class:`Vec2D <spyral.Vec2D>`
        :rtype: float
        """
        x = self.x*other[1] - self.y*other[0]
        d = self.x*other[0] + self.y*other[1]
        return math.atan2(x, d)

    def projection(self, other):
        """
        Returns the
        `projection <http://en.wikipedia.org/wiki/Vector_projection>`_
        of this :class:`Vec2D <spyral.Vec2D>` onto another point.

        :param other: the other point
        :type other: 2-tuple or :class:`Vec2D <spyral.Vec2D>`
        :rtype: float
        """
        other = Vec2D(other)
        l2 = float(other.x*other.x + other.y*other.y)
        d = self.x*other.x + self.y*other.y
        return (d/l2)*other

    def rotated(self, angle, center=(0, 0)):
        """
        Returns a new vector from the old point rotated by `angle` radians about
        the optional `center`.

        :param angle: angle in radians.
        :type angle: float
        :param center: an optional center
        :type center: 2-tuple or :class:`Vec2D <spyral.Vec2D>`
        :rtype: :class:`Vec2D <spyral.Vec2D>`
        """
        p = self - center
        c = math.cos(angle)
        s = math.sin(angle)
        x = p.x*c - p.y*s
        y = p.x*s + p.y*c
        return Vec2D(x, y) + center

    def normalized(self):
        """
        Returns a new vector based on this one, normalized to length 1. That is,
        it keeps the same angle, but its length is now 1.

        :rtype: :class:`Vec2D <spyral.Vec2D>`
        """
        l = self.get_length()
        if self.get_length() == 0:
            return None
        return Vec2D(self.x/l, self.y/l)

    def floor(self):
        """
        Converts the components of this vector into ints, discarding anything
        past the decimal place.

        :returns: this :class:`Vec2D <spyral.Vec2D>`
        """
        self.x = int(self.x)
        self.y = int(self.y)
        return self

    def to_polar(self):
        """
        Returns `Vec2D(radius, theta)` for this vector, where `radius` is the
        length and `theta` is the angle.

        :rtype: :class:`Vec2D <spyral.Vec2D>`
        """
        return Vec2D(self.get_length(), self.get_angle())

    @staticmethod
    def from_polar(*args):
        """
        Takes in radius, theta or (radius, theta) and returns rectangular
        :class:`Vec2D <spyral.Vec2D>`.

        :rtype: :class:`Vec2D <spyral.Vec2D>`
        """
        v = Vec2D(*args)
        return Vec2D(v.x*math.cos(v.y), v.x*math.sin(v.y))

    def __hash__(self):
        return self.x + self.y

########NEW FILE########
__FILENAME__ = view
import spyral
from weakref import ref as _wref

class View(object):
    """
    Creates a new view with a scene or view as a parent. A view is a collection
    of Sprites and Views that can be collectively transformed - e.g., flipped,
    cropped, scaled, offset, hidden, etc. A View can also have a ``mask``, in
    order to treat it as a single collidable object. Like a Sprite, a View cannot
    be moved between Scenes.
    
    :param parent: The view or scene that this View belongs in.
    :type parent: :func:`View <spyral.View>` or :func:`Scene <spyral.Scene>`
    """
    def __init__(self, parent):

        self._size = spyral.Vec2D(parent.size)
        self._output_size = spyral.Vec2D(parent.size)
        self._crop_size = spyral.Vec2D(parent.size)
        self._pos = spyral.Vec2D(0,0)
        self._crop = False
        self._visible = True
        self._parent = _wref(parent)
        self._anchor = 'topleft'
        self._offset = spyral.Vec2D(0,0)
        self._layers = []
        self._layer = None
        self._mask = None

        self._children = set()
        self._child_views = set()
        self._scene = _wref(parent.scene)
        self._scene()._add_view(self)
        self._parent()._add_child(self)
        self._scene()._apply_style(self)

    def _add_child(self, entity):
        """
        Starts keeping track of the entity as a child of this view.

        :param entity: The new entity to keep track of.
        :type entity: a View or a Sprite.
        """
        self._children.add(entity)
        if isinstance(entity, View):
            self._child_views.add(entity)

    def _remove_child(self, entity):
        """
        Stops keeping track of the entity as a child of this view, if it exists.

        :param entity: The entity to keep track of.
        :type entity: a View or a Sprite.
        """
        self._children.discard(entity)
        self._child_views.discard(entity)

    def kill(self):
        """
        Completely remove any parent's links to this view. When you want to
        remove a View, you should call this function.
        """
        for child in list(self._children):
            child.kill()
        self._children.clear()
        self._child_views.clear()
        self._scene()._kill_view(self)

    def _get_mask(self):
        """
        Return this View's mask, a spyral.Rect representing the collidable area.
        
        :rtype: :class:`Rect <spyral.Rect>` if this value has been set,
                otherwise it will be ``None``.
        """
        return self._mask

    def _set_mask(self, mask):
        """
        Set this View's mask. Triggers a recomputation of the collision box.
        :param mask: The region that this View collides with, or None
        (indicating that the default should be used).
        :type mask: a :class:`Rect <spyral.Rect>`, or None.
        """
        self._mask = mask
        self._set_collision_box()

    def _set_collision_box_tree(self):
        """
        Set this View's collision box, and then also recursively recompute
        the collision box for any child Views.
        """
        self._set_collision_box()
        for view in self._child_views:
            view._set_collision_box_tree()

    def _changed(self):
        """
        Called when this View has changed a visual property, ensuring that the
        offset and collision box are recomputed; also triggers a
        `spyral.internal.view.changed` event.
        """
        self._recalculate_offset()
        self._set_collision_box_tree()
        # Notify any listeners (probably children) that I have changed
        changed_event = spyral.Event(name="changed", view=self)
        spyral.event.handle("spyral.internal.view.changed",
                            changed_event,
                            self.scene)

    def _recalculate_offset(self):
        """
        Recalculates the offset of this View.
        """
        if self._mask:
            self._offset = spyral.util._anchor_offset(self._anchor, 
                                                     self._mask.size[0], 
                                                     self._mask.size[1])
        else:
            self._offset = spyral.util._anchor_offset(self._anchor, 
                                                     self._size[0], 
                                                     self._size[1])

    # Properties
    def _get_pos(self):
        """
        Returns the position (:func:`Vec2D <spyral.Vec2D>`) of this View within its
        parent.
        """
        return self._pos

    def _set_pos(self, pos):
        if pos == self._pos:
            return
        self._pos = spyral.Vec2D(pos)
        self._changed()

    def _get_layer(self):
        """
        The layer (a ``str``) that this View is on, within its parent.
        """
        return self._layer

    def _set_layer(self, layer):
        if layer == self._layer:
            return
        self._layer = layer
        self._scene()._set_view_layer(self, layer)
        self._changed()

    def _get_layers(self):
        """
        A list of strings representing the layers that are available for this
        view. The first layer is at the bottom, and the last is at the top. For
        more information on layers, check out the :ref:`layers <ref.layering>`
        appendix.

        .. note:
            
            Layers can only be set once.
        """
        return tuple(self._layers)

    def _set_layers(self, layers):
        if not self._layers:
            self._layers = layers[:]
            self._scene()._set_view_layers(self, layers)
        elif self._layers == layers:
            pass
        else:
            raise spyral.LayersAlreadySetError("You can only define the "
                                               "layers for a view once.")

    def _get_x(self):
        """
        The x coordinate of the view, which will remain synced with the
        position. Number.
        """
        return self._get_pos()[0]

    def _set_x(self, x):
        self._set_pos((x, self._get_y()))

    def _get_y(self):
        """
        The y coordinate of the view, which will remain synced with the
        position. Number.
        """
        return self._get_pos()[1]

    def _set_y(self, y):
        self._set_pos((self._get_x(), y))

    def _get_anchor(self):
        """
        Defines an :ref:`anchor point <ref.anchors>` where coordinates are relative to
        on the view. String.
        """
        return self._anchor

    def _set_anchor(self, anchor):
        if anchor == self._anchor:
            return
        self._anchor = anchor
        self._recalculate_offset()
        self._changed()

    def _get_width(self):
        """
        The width of the view. Number.
        """
        return self._size[0]

    def _set_width(self, width):
        self._set_size(width, self._get_height())

    def _get_height(self):
        """
        The height of the view. Number.
        """
        return self._size[1]

    def _set_height(self, height):
        self._set_size(self._get_width(), height)

    def _get_output_width(self):
        """
        The width of this view when drawn on the parent. Number.
        """
        return self._output_size[0]

    def _set_output_width(self, width):
        self._set_output_size((width, self._get_output_height()))

    def _get_output_height(self):
        """
        The height of this view when drawn on the parent. Number.
        """
        return self._output_size[1]

    def _set_output_height(self, height):
        self._set_output_size((self._get_output_width(), height))

    def _get_crop_width(self):
        """
        The width of the cropped area. Number.
        """
        return self._crop_size[0]

    def _set_crop_width(self, width):
        self._set_crop_size((width, self._get_crop_height()))

    def _get_crop_height(self):
        """
        The height of the cropped area. Number.
        """
        return self._crop_size[1]

    def _set_crop_height(self, height):
        self._set_crop_size((self._get_crop_width(), height))

    def _get_size(self):
        """
        The (width, height) of this view's coordinate space
        (:class:`Vec2D <spyral.Vec2d>`). Defaults to size of the parent.
        """
        return self._size

    def _set_size(self, size):
        if size == self._size:
            return
        self._size = spyral.Vec2D(size)
        self._changed()

    def _get_output_size(self):
        """
        The (width, height) of this view when drawn on the parent
        (:class:`Vec2D <spyral.Vec2d>`). Defaults to size of the parent.
        """
        return self._output_size

    def _set_output_size(self, size):
        if size == self._output_size:
            return
        self._output_size = spyral.Vec2D(size)
        self._changed()

    def _get_crop_size(self):
        """
        The (width, height) of the area that will be cropped; anything outside
        of this region will be removed when the crop is active.
        """
        return self._crop_size

    def _set_crop_size(self, size):
        if size == self._crop_size:
            return
        self._crop_size = spyral.Vec2D(size)
        self._changed()

    def _get_scale(self):
        """
        A scale factor from the size to the output_size for the view. It will
        always contain a :class:`Vec2D <spyral.Vec2D>` with an x factor and a
        y factor, but it can be set to a numeric value which will be set for
        both coordinates.
        """
        return self._output_size / self._size

    def _set_scale(self, scale):
        if isinstance(scale, (int, float)):
            scale = spyral.Vec2D(scale, scale)
        if scale == self._get_scale():
            return
        self._output_size = self._size * spyral.Vec2D(scale)
        self._changed()

    def _get_scale_x(self):
        """
        The x factor of the scaling. Kept in sync with scale. Number.
        """
        return self._get_scale()[0]

    def _get_scale_y(self):
        """
        The y factor of the scaling. Kept in sync with scale. Number.
        """
        return self._get_scale()[1]

    def _set_scale_x(self, x):
        self._set_scale((x, self._get_scale()[1]))

    def _set_scale_y(self, y):
        self._set_scale((self._get_scale()[0], y))

    def _get_visible(self):
        """
        Whether or not this View and its children will be drawn (``bool``).
        Defaults to ``False``.
        """
        return self._visible

    def _set_visible(self, visible):
        if self._visible == visible:
            return
        self._visible = visible
        self._changed()

    def _get_crop(self):
        """
        A ``bool`` that determines whether the view should crop anything
        outside of it's size (default: True).
        """
        return self._crop

    def _set_crop(self, crop):
        if self._crop == crop:
            return
        self._crop = crop
        self._changed()


    def _get_parent(self):
        """
        The first parent :class:`View <spyral.View>` or 
        :class:`Scene <spyral.Scene>` that this View belongs to. Read-only.
        """
        return self._parent()
        
    def _get_scene(self):
        """
        The top-most parent :class:`Scene <spyral.Scene>` that this View
        belongs to. Read-only.
        """
        return self._scene()

    def _get_rect(self):
        """
        A :class:`Rect <spyral.Rect>` representing the position and size of
        this View. Can be set through a ``Rect``, a 2-tuple of position and
        size, or a 4-tuple.
        """
        return spyral.Rect(self._pos, self.size)

    def _set_rect(self, *rect):
        if len(rect) == 1:
            r = rect[0]
            self.x, self.y = r.x, r.y
            self.width, self.height = r.w, r.h
        elif len(rect) == 2:
            self.pos = rect[0]
            self.size = rect[1]
        elif len(args) == 4:
            self.x, self.y, self.width, self.height = args
        else:
            raise ValueError("TODO: You done goofed.")

    pos = property(_get_pos, _set_pos)
    layer = property(_get_layer, _set_layer)
    layers = property(_get_layers, _set_layers)
    x = property(_get_x, _set_x)
    y = property(_get_y, _set_y)
    anchor = property(_get_anchor, _set_anchor)
    scale = property(_get_scale, _set_scale)
    scale_x = property(_get_scale_x, _set_scale_x)
    scale_y = property(_get_scale_y, _set_scale_y)
    width = property(_get_width, _set_width)
    height = property(_get_height, _set_height)
    size = property(_get_size, _set_size)
    mask = property(_get_mask, _set_mask)
    output_width = property(_get_output_width, _set_output_width)
    output_height = property(_get_output_height, _set_output_height)
    output_size = property(_get_output_size, _set_output_size)
    crop_width = property(_get_crop_width, _set_crop_width)
    crop_height = property(_get_crop_height, _set_crop_height)
    crop_size = property(_get_crop_size, _set_crop_size)
    visible = property(_get_visible, _set_visible)
    crop = property(_get_crop, _set_crop)
    parent = property(_get_parent)
    scene = property(_get_scene)
    rect = property(_get_rect, _set_rect)

    def _blit(self, blit):
        """
        If this View is visible, applies offseting, scaling, and cropping
        before passing it up the transformation chain.
        """
        if self.visible:
            blit.position += self.pos
            blit.apply_scale(self.scale)
            if self.crop:
                blit.clip(spyral.Rect((0, 0), self.crop_size))
            self._parent()._blit(blit)

    def _static_blit(self, key, blit):
        """
        If this View is visible, applies offseting, scaling, and cropping
        before passing it up the transformation chain.
        """
        if self.visible:
            blit.position += self.pos
            blit.apply_scale(self.scale)
            if self.crop:
                blit.clip(spyral.Rect((0, 0), self.crop_size))
            self._parent()._static_blit(key, blit)

    def _warp_collision_box(self, box):
        """
        Transforms the given collision box according to this view's scaling,
        cropping, and offset; then passes the box to this boxes parent.
        """
        box.position += self.pos
        box.apply_scale(self.scale)
        if self.crop:
            box.clip(spyral.Rect((0, 0), self.crop_size))
        return self._parent()._warp_collision_box(box)

    def _set_collision_box(self):
        """
        Updates this View's collision box.
        """
        if self._mask is not None:
            pos = self._mask.topleft - self._offset
            area = spyral.Rect((0,0), self._mask.size)
        else:
            pos = self._pos - self._offset
            area = spyral.Rect((0,0), self.size)
        c = spyral.util._CollisionBox(pos, area)
        warped_box = self._parent()._warp_collision_box(c)
        self._scene()._set_collision_box(self, warped_box.rect)

    def __stylize__(self, properties):
        """
        Applies the *properties* to this scene. This is called when a style
        is applied.

        :param properties: a mapping of property names (strings) to values.
        :type properties: ``dict``
        """
        simple = ['pos', 'x', 'y', 'position',
                  'width', 'height', 'size',
                  'output_width', 'output_height', 'output_size',
                  'anchor', 'layer', 'layers', 'visible',
                  'scale', 'scale_x', 'scale_y',
                  'crop', 'crop_width', 'crop_height', 'crop_size']
        for property in simple:
            if property in properties:
                value = properties.pop(property)
                setattr(self, property, value)
        if len(properties) > 0:
            spyral.exceptions.unused_style_warning(self, properties.iterkeys())

    def collide_sprite(self, other):
        """
        Returns whether this view is colliding with the sprite or view.

        :param other: A sprite or a view
        :type other: :class:`Sprite <spyral.Sprite>` or a 
                     :class:`View <spyral.View>`
        :returns: A ``bool``
        """
        return self._scene().collide_sprite(self, other)
        
    def collide_point(self, pos):
        """
        Returns whether this view is colliding with the point.

        :param point: A point
        :type point: :class:`Vec2D <spyral.Vec2D>`
        :returns: A ``bool``
        """
        return self._scene().collide_point(self, pos)
        
    def collide_rect(self, rect):
        """
        Returns whether this view is colliding with the rect.

        :param rect: A rect
        :type rect: :class:`Rect <spyral.Rect>`
        :returns: A ``bool``
        """
        return self._scene().collide_rect(self, rect)

########NEW FILE########
__FILENAME__ = weakmethod
"""
This magic was taken from
http://code.activestate.com/recipes/81253-weakmethod/#c4

This module provides classes and methods for weakly referencing functions and
bound methods; it turns out this is a non-trivial problem.
"""

import weakref

class WeakMethodBound(object):
    """
    Holds a weak reference to a bound method for an object.

    .. attribute::method

        The function being called.
    """
    def __init__(self, func):
        self.func = func.im_func
        self.weak_object_ref = weakref.ref(func.im_self)
    def _func(self):
        return self.func
    method = property(_func)
    def __call__(self, *arg):
        if self.weak_object_ref() == None:
            raise TypeError('Method called on dead object')
        return apply(self.func, (self.weak_object_ref(), ) + arg)

class WeakMethodFree(object):
    """
    Holds a weak reference to an unbound function. Included only for
    completeness.

    .. attribute::method

        The function being called.
    """
    def __init__(self, func):
        self.func = weakref.ref(func)
    def _func(self):
        return self.func()
    method = property(_func)
    def __call__(self, *arg):
        if self.func() == None:
            raise TypeError('Function no longer exist')
        return apply(self.func(), arg)

def WeakMethod(func):
    """
    Attempts to create a weak reference to this function; only bound methods
    require a weakreference.
    """
    try:
        func.im_func
    except AttributeError:
        return func
    return WeakMethodBound(func)

########NEW FILE########
__FILENAME__ = widgets
import spyral
import types
import sys
import functools
import math
import string
import pygame
from bisect import bisect_right
from weakref import ref as _wref

class BaseWidget(spyral.View):
    """
    The BaseWidget is the simplest possible widget that all other widgets
    must subclass. It handles tracking its owning form and the styling that
    should be applied.
    """
    def __init__(self, form, name):
        self.__style__ = form.__class__.__name__ + '.' + name
        self.name = name
        self._form = _wref(form)
        spyral.View.__init__(self, form)
        self.mask = spyral.Rect(self.pos, self.size)
        
    def _get_form(self):
        """
        The parent form that this Widget belongs to. Read-only.
        """
        return self._form()
        
    form = property(_get_form)

    def _changed(self):
        """
        Called when the Widget is changed; since Widget's masks are a function
        of their component widgets, it needs to be notified.
        """
        self._recalculate_mask()
        spyral.View._changed(self)

    def _recalculate_mask(self):
        """
        Recalculate this widget's mask based on its size, position, and padding.
        """
        self.mask = spyral.Rect(self.pos, self.size + self.padding)

# Widget Implementations

class MultiStateWidget(BaseWidget):
    """
    The MultiStateWidget is an abstract widget with multiple states. It should
    be subclassed and implemented to have different behavior based on its
    states.

    In addition, it supports having a Nine Slice image; it will cut a given
    image into a 3x3 grid of images that can be stretched into a button. This
    is a boolean property.

    :param form: The parent form that this Widget belongs to.
    :type form: :class:`Form <spyral.Form>`
    :param str name: The name of this widget.
    :param states: A list of the possible states that the widget can be in.
    :type states: A ``list`` of ``str``.
    """
    def __init__(self, form, name, states):
        self._states = states
        self._state = self._states[0]
        self.button = None # Hack for now; TODO need to be able to set properties on it even though it doesn't exist yet

        BaseWidget.__init__(self, form, name)
        self.layers = ["base", "content"]

        self._images = {}
        self._content_size = (0, 0)
        self.button = spyral.Sprite(self)
        self.button.layer = "base"

    def _render_images(self):
        """
        Recreates the cached images of this widget (based on the
        **self._image_locations** internal variabel) and sets the widget's image
        based on its current state.
        """
        for state in self._states:
            if self._nine_slice:
                size = self._padding + self._content_size
                nine_slice_image = spyral.Image(self._image_locations[state])
                self._images[state] = spyral.image.render_nine_slice(nine_slice_image, size)
            else:
                self._images[state] = spyral.Image(self._image_locations[state])
        self.button.image = self._images[self._state]
        self.mask = spyral.Rect(self.pos, self.button.size)
        self._on_state_change()

    def _set_state(self, state):
        old_value = self.value
        self._state = state
        if self.value != old_value:
            e = spyral.Event(name="changed", widget=self, form=self.form, value=self._get_value())
            self.scene._queue_event("form.%(form_name)s.%(widget)s.changed" %
                                        {"form_name": self.form.__class__.__name__,
                                         "widget": self.name},
                                    e)
        self.button.image = self._images[state]
        self.mask = spyral.Rect(self.pos, self.button.size)
        self._on_state_change()

    def _get_value(self):
        """
        Returns the current value of this widget; defaults to the ``state`` of
        the widget.
        """
        return self._state

    def _get_state(self):
        """
        This widget's state; when changed, a form.<name>.<widget>.changed
        event will be triggered. Represented as a ``str``.
        """
        return self._state

    def _set_nine_slice(self, nine_slice):
        self._nine_slice = nine_slice
        self._render_images()

    def _get_nine_slice(self):
        """
        The :class:`Image <spyral.Image>` that will be nine-sliced into this
        widget's background.
        """
        return self._nine_slice

    def _set_padding(self, padding):
        if isinstance(padding, spyral.Vec2D):
            self._padding = padding
        else:
            self._padding = spyral.Vec2D(padding, padding)
        self._render_images()

    def _get_padding(self):
        """
        A :class:`Vec2D <spyral.Vec2D>` that represents the horizontal and
        vertical padding associated with this button. Can also be set with a
        ``int`` for equal amounts of padding, although it will always return a
        :class:`Vec2D <spyral.Vec2D>`.
        """
        return self._padding

    def _set_content_size(self, size):
        """
        The size of the content within this button, used to calculate the mask.
        A :class:`Vec2D <spyral.Vec2D>`

        ..todo:: It's most likely the case that this needs to be refactored into
        the mask property, since they're probably redundant with each other.
        """
        self._content_size = size
        self._render_images()

    def _get_content_size(self):
        return self._get_content_size

    def _on_size_change(self):
        """
        A function triggered whenever this widget changes size.
        """
        pass

    def _get_anchor(self):
        """
        Defines an `anchor point <anchors>` where coordinates are relative to
        on the widget. ``str``.
        """
        return self._anchor

    def _set_anchor(self, anchor):
        if self.button is not None:
            self.button.anchor = anchor
            self._text_sprite.anchor = anchor
        BaseWidget._set_anchor(self, anchor)

    anchor = property(_get_anchor, _set_anchor)
    value = property(_get_value)
    padding = property(_get_padding, _set_padding)
    nine_slice = property(_get_nine_slice, _set_nine_slice)
    state = property(_get_state, _set_state)
    content_size = property(_get_content_size, _set_content_size)

    def __stylize__(self, properties):
        """
        Applies the *properties* to this scene. This is called when a style
        is applied.

        :param properties: a mapping of property names (strings) to values.
        :type properties: ``dict``
        """
        self._padding = properties.pop('padding', 4)
        if not isinstance(self._padding, spyral.Vec2D):
            self._padding = spyral.Vec2D(self._padding, self._padding)
        self._nine_slice = properties.pop('nine_slice', False)
        self._image_locations = {}
        for state in self._states:
            # TODO: try/catch to ensure that the property is set?
            self._image_locations[state] = properties.pop('image_%s' % (state,))
        spyral.View.__stylize__(self, properties)


class ButtonWidget(MultiStateWidget):
    """
    A ButtonWidget is a simple button that can be pressed. It can have some
    text. If you don't specify an explicit width, then it will be sized
    according to it's text.

    :param form: The parent form that this Widget belongs to.
    :type form: :class:`Form <spyral.Form>`
    :param str name: The name of this widget.
    :param str text: The text that will be rendered on this button.
    """
    def __init__(self, form, name, text = "Okay"):
        MultiStateWidget.__init__(self, form, name,
                                  ['up', 'down', 'down_focused', 'down_hovered',
                                   'up_focused', 'up_hovered'])

        self._text_sprite = spyral.Sprite(self)
        self._text_sprite.layer = "content"

        self.text = text

    def _get_value(self):
        """
        Whether or not this widget is currently ``"up"`` or ``"down"``.
        """
        if "up" in self._state:
            return "up"
        else:
            return "down"

    def _get_text(self):
        """
        The text rendered on this button (``str``).
        """
        return self._text

    def _set_text(self, text):
        self._text = text
        self._text_sprite.image = self.font.render(self._text)
        self._content_size = self._text_sprite.image.size
        self._render_images()

    def _on_state_change(self):
        """
        A function triggered whenever this widget changes size.
        """
        self._text_sprite.pos = spyral.util._anchor_offset(self._anchor,
                                                          self._padding[0] / 2,
                                                          self._padding[1] / 2)

    value = property(_get_value)
    text = property(_get_text, _set_text)

    def _handle_mouse_up(self, event):
        """
        The function called when the mouse is released while on this widget.
        """
        if self.state.startswith('down'):
            self.state = self.state.replace('down', 'up')
            e = spyral.Event(name="clicked", widget=self, form=self.form, value=self._get_value())
            self.scene._queue_event("form.%(form_name)s.%(widget)s.clicked" %
                                        {"form_name": self.form.__class__.__name__,
                                         "widget": self.name},
                                    e)

    def _handle_mouse_down(self, event):
        """
        The function called when the mouse is pressed while on this widget.
        Fires a ``clicked`` event.
        """
        if self.state.startswith('up'):
            self.state = self.state.replace('up', 'down')

    def _handle_mouse_out(self, event):
        """
        The function called when this button is no longer being hovered over.
        """
        if "_hovered" in self.state:
            self.state = self.state.replace('_hovered', '')

    def _handle_mouse_over(self, event):
        """
        The function called when the mouse starts hovering over this button.
        """
        if not "_hovered" in self.state:
            self.state = self.state.replace('_focused', '') + "_hovered"

    def _handle_mouse_motion(self, event):
        """
        The function called when the mouse moves while over this button.
        """
        pass

    def _handle_focus(self, event):
        """
        Applies the focus state to this widget
        """
        if self.state in ('up', 'down'):
            self.state+= '_focused'

    def _handle_blur(self, event):
        """
        Removes the focused state from this widget.
        """
        if self.state in ('up_focused', 'down_focused'):
            self.state = self.state.replace('_focused', '')

    def _handle_key_down(self, event):
        """
        When the enter or space key is pressed, triggers this button being
        pressed.
        """
        if event.key in (spyral.keys.enter, spyral.keys.space):
            self._handle_mouse_down(event)

    def _handle_key_up(self, event):
        """
        When the enter or space key is pressed, triggers this button being
        released.
        """
        if event.key in (spyral.keys.enter, spyral.keys.space):
            self._handle_mouse_up(event)

    def __stylize__(self, properties):
        """
        Applies the *properties* to this scene. This is called when a style
        is applied.

        :param properties: a mapping of property names (strings) to values.
        :type properties: ``dict``
        """
        self.font = spyral.Font(*properties.pop('font'))
        self._text = properties.pop('text', "Button")
        MultiStateWidget.__stylize__(self, properties)


class ToggleButtonWidget(ButtonWidget):
    """
    A ToggleButtonWidget is similar to a Button, except that it will stay down
    after it's been clicked, until it is clicked again.

    :param form: The parent form that this Widget belongs to.
    :type form: :class:`Form <spyral.Form>`
    :param str name: The name of this widget.
    :param str text: The text that will be rendered on this button.
    """
    def __init__(self, form, name, text = "Okay"):
        ButtonWidget.__init__(self, form, name, text)

    def _handle_mouse_up(self, event):
        """
        The function called when the mouse is released while on this widget.
        """
        pass

    def _handle_mouse_down(self, event):
        """
        Triggers the mouse to change states.
        """
        if self.state.startswith('down'):
            self.state = self.state.replace('down', 'up')
        elif self.state.startswith('up'):
            self.state = self.state.replace('up', 'down')


class CheckboxWidget(ToggleButtonWidget):
    """
    A CheckboxWidget is identical to a ToggleButtonWidget, only it doesn't have
    any text.
    """
    def __init__(self, form, name):
        ToggleButtonWidget.__init__(self, form, name, "")

class RadioButtonWidget(ToggleButtonWidget):
    """
    A RadioButton is similar to a CheckBox, except it is to be placed into a
    RadioGroup, which will ensure that only one RadioButton in it's group is
    selected at a time.

    ..warning:: This widget is incomplete.
    """
    def __init__(self, form, name, group):
        ToggleButtonWidget.__init__(self, form, name, _view_x)

class RadioGroupWidget(object):
    """
    Only one RadioButton in a RadioGroup can be selected at a time.

    ..warning:: This widget is incomplete.
    """
    def __init__(self, buttons, selected = None):
        pass


class TextInputWidget(BaseWidget):
    """
    The TextInputWidget is used to get text data from the user, through an
    editable textbox.

    :param form: The parent form that this Widget belongs to.
    :type form: :class:`Form <spyral.Form>`
    :param str name: The name of this widget.
    :param int width: The rendered width in pixels of this widget.
    :param str value: The initial value of this widget.
    :param bool default_value: Whether to clear the text of this widget the
                               first time it gains focus.
    :param int text_length: The maximum number of characters that can be entered
                            into this box. If ``None``, then there is no
                            maximum.
    :param set validator: A set of characters that are allowed to be printed.
                          Defaults to all regularly printable characters (which
                          does not include tab and newlines).
    """
    def __init__(self, form, name, width, value='', default_value=True,
                 text_length=None, validator=None):
        self.box_width, self._box_height = 0, 0
        BaseWidget.__init__(self, form, name)

        self.layers = ["base", "content"]

        child_anchor = (self._padding, self._padding)
        self._back = spyral.Sprite(self)
        self._back.layer = "base"
        self._cursor = spyral.Sprite(self)
        self._cursor.anchor = child_anchor
        self._cursor.layer = "content:above"
        self._text = spyral.Sprite(self)
        self._text.pos = child_anchor
        self._text.layer = "content"

        self._focused = False
        self._cursor.visible = False
        self._selection_pos = 0
        self._selecting = False
        self._shift_was_down = False
        self._mouse_is_down = False

        self._cursor_time = 0.
        self._cursor_blink_interval = self._cursor_blink_interval

        self.default_value = default_value
        self._default_value_permanant = default_value

        self._view_x = 0
        self.box_width = width - 2*self._padding
        self.text_length = text_length

        self._box_height = int(math.ceil(self.font.linesize))
        self._recalculate_mask()

        self._cursor.image = spyral.Image(size=(2,self._box_height))
        self._cursor.image.fill(self._cursor_color)

        if validator is None:
            self.validator = str(set(string.printable).difference("\n\t"))
        else:
            self.validator = validator

        if text_length is not None and len(value) < text_length:
            value = value[:text_length]
        self._value = None
        self.value = value

        self._render_backs()
        self._back.image = self._image_plain

        spyral.event.register("director.update", self._update, scene=self.scene)

    def _recalculate_mask(self):
        """
        Forces a recomputation of the widget's mask, based on the position,
        internal boxes size, and the padding.
        """
        self.mask = spyral.Rect(self.x+self.padding, self.y+self.padding,
                                self.box_width+self.padding,
                                self._box_height+self.padding)

    def _render_backs(self):
        """
        Recreates the nine-slice box used to back this widget.
        """
        padding = self._padding
        width = self.box_width + 2*padding + 2
        height = self._box_height + 2*padding + 2
        self._image_plain = spyral.Image(self._image_locations['focused'])
        self._image_focused = spyral.Image(self._image_locations['unfocused'])
        if self._nine_slice:
            render_nine_slice = spyral.image.render_nine_slice
            self._image_plain = render_nine_slice(self._image_plain,
                                                  (width, height))
            self._image_focused = render_nine_slice(self._image_focused,
                                                    (width, height))

    def __stylize__(self, properties):
        """
        Applies the *properties* to this scene. This is called when a style
        is applied.

        :param properties: a mapping of property names (strings) to values.
        :type properties: ``dict``
        """
        pop = properties.pop
        self._padding = pop('padding', 4)
        self._nine_slice = pop('nine_slice', False)
        self._image_locations = {}
        self._image_locations['focused'] = pop('image_focused')
        self._image_locations['unfocused'] = pop('image_unfocused')
        self._cursor_blink_interval = pop('cursor_blink_interval', .5)
        self._cursor_color = pop('cursor_color', (0, 0, 0))
        self._highlight_color = pop('highlight_color', (0, 140, 255))
        self._highlight_background_color = pop('highlight_background_color',
                                               (0, 140, 255))
        self.font = spyral.Font(*pop('font'))
        spyral.View.__stylize__(self, properties)

    def _compute_letter_widths(self):
        """
        Compute and store the width for each substring in text. I.e., the first
        character, the first two characters, the first three characters, etc.
        """
        self._letter_widths = []
        running_sum = 0
        for index in range(len(self._value)+1):
            running_sum= self.font.get_size(self._value[:index])[0]
            self._letter_widths.append(running_sum)

    def _insert_char(self, position, char):
        """
        Insert the given *char* into the text at *position*.

        Also triggers a form.<name>.<widget>.changed event.
        """
        if position == len(self._value):
            self._value += char
            new_width= self.font.get_size(self._value)[0]
            self._letter_widths.append(new_width)
        else:
            self._value = self._value[:position] + char + self._value[position:]
            self._compute_letter_widths()
        self._render_text()
        e = spyral.Event(name="changed", widget=self,
                         form=self.form, value=self._value)
        self.scene._queue_event("form.%(form_name)s.%(widget)s.changed" %
                                    {"form_name": self.form.__class__.__name__,
                                     "widget": self.name},
                                e)

    def _remove_char(self, position, end=None):
        """
        Remove the characters from *position* to *end* within the text. If *end*
        is None, it removes only a single character.

        Also triggers a form.<name>.<widget>.changed event.
        """
        if end is None:
            end = position+1
        if position == len(self._value):
            pass
        else:
            self._value = self._value[:position]+self._value[end:]
            self._compute_letter_widths()
        self._render_text()
        self._render_cursor()
        e = spyral.Event(name="changed", widget=self, form=self.form, value=self._value)
        self.scene._queue_event("form.%(form_name)s.%(widget)s.changed" %
                                    {"form_name": self.form.__class__.__name__,
                                     "widget": self.name},
                                e)


    def _compute_cursor_pos(self, mouse_pos):
        """
        Given a mouse position, computes the closest index in the string.

        :returns: The index in the string (an ``int).
        """
        x = mouse_pos[0] + self._view_x - self.x - self._padding
        index = bisect_right(self._letter_widths, x)
        if index >= len(self._value):
            return len(self._value)
        elif index:
            diff = self._letter_widths[index] - self._letter_widths[index-1]
            x -= self._letter_widths[index-1]
            if diff > x*2:
                return index-1
            else:
                return index
        else:
            return 0

    def _stop_blinking(self):
        """
        Stops the cursor from blinking.
        """
        self._cursor_time = 0
        self._cursor.visible = True

    def _get_value(self):
        """
        The current value of this widget, i.e, the text the user has input. When
        this value is changed, it triggers a ``form.<name>.<widget>.changed``
        event. A ``str``.
        """
        return self._value

    def _set_value(self, value):
        if self._value is not None:
            e = spyral.Event(name="changed", widget=self,
                             form=self.form, value=value)
            self.scene._queue_event("form.%(form_name)s.%(widget)s.changed" %
                                        {"form_name": self.form.__class__.__name__,
                                         "widget": self.name},
                                    e)
        self._value = value
        self._compute_letter_widths()
        self._cursor_pos = 0#len(value)
        self._render_text()
        self._render_cursor()

    def _get_cursor_pos(self):
        """
        The current index of the text cursor within this widget. A ``int``.
        """
        return self._cursor_pos

    def _set_cursor_pos(self, position):
        self._cursor_pos = position
        self._move_rendered_text()
        self._render_cursor()

    def _validate(self, char):
        """
        Tests whether the given character is a valid one and that there is room
        for the character within the textbox.
        """
        valid_length = (self.text_length is None or
                        (self.text_length is not None
                         and len(self._value) < self.text_length))
        valid_char = str(char) in self.validator
        return valid_length and valid_char

    def _set_nine_slice(self, nine_slice):
        self._nine_slice = nine_slice
        self._render_backs()

    def _get_nine_slice(self):
        """
        The :class:`Image <spyral.Image>` used to build the internal nine-slice
        image.
        """
        return self._nine_slice

    def _set_padding(self, padding):
        self._padding = padding
        self._render_backs()

    def _get_padding(self):
        """
        A single ``int`` representing both the vertical and horizontal padding
        within this widget.
        """
        return self._padding

    def _get_anchor(self):
        """
        Defines an `anchor point <anchors>` where coordinates are relative to
        on the view. String.
        """
        return self._anchor

    def _set_anchor(self, anchor):
        self._back.anchor = anchor
        self._text.anchor = anchor
        self._cursor.anchor = anchor
        BaseWidget._set_anchor(self, anchor)

    anchor = property(_get_anchor, _set_anchor)
    value = property(_get_value, _set_value)
    cursor_pos = property(_get_cursor_pos, _set_cursor_pos)
    padding = property(_get_padding, _set_padding)
    nine_slice = property(_get_nine_slice, _set_nine_slice)

    def _render_text(self):
        """
        Causes the text to be redrawn on the internal image.
        """
        if self._selecting and (self._cursor_pos != self._selection_pos):
            start, end = sorted((self._cursor_pos, self._selection_pos))

            pre = self.font.render(self._value[:start])
            highlight = self.font.render(self._value[start:end], color=self._highlight_color)
            post = self.font.render(self._value[end:])

            pre_missed = self.font.get_size(self._value[:end])[0] - pre.width - highlight.width + 1
            if self._value[:start]:
                post_missed = self.font.get_size(self._value)[0] - post.width - pre.width - highlight.width - 1
                self._rendered_text = spyral.image.from_sequence((pre, highlight, post), 'right', [pre_missed, post_missed])
            else:
                post_missed = self.font.get_size(self._value)[0] - post.width - highlight.width
                self._rendered_text = spyral.image.from_sequence((highlight, post), 'right', [post_missed])

        else:
            self._rendered_text = self.font.render(self._value)
        self._move_rendered_text()

    def _move_rendered_text(self):
        """
        Offsets the text within the image. This could probably be reimplemented
        using the new cropping mechanism within Views.
        """
        width = self._letter_widths[self.cursor_pos]
        max_width = self._letter_widths[len(self._value)]
        cursor_width = 2
        x = width - self._view_x
        if x < 0:
            self._view_x += x
        if x+cursor_width > self.box_width:
            self._view_x += x + cursor_width - self.box_width
        if self._view_x+self.box_width> max_width and max_width > self.box_width:
            self._view_x = max_width - self.box_width
        image = self._rendered_text.copy()
        image.crop((self._view_x, 0),
                   (self.box_width, self._box_height))
        self._text.image = image

    def _render_cursor(self):
        """
        Moves the text cursor to the right position.
        """
        self._cursor.x = min(max(self._letter_widths[self.cursor_pos] - self._view_x, 0), self.box_width)
        self._cursor.y = 0

    _non_insertable_keys =(spyral.keys.up, spyral.keys.down,
                           spyral.keys.left, spyral.keys.right,
                           spyral.keys.home, spyral.keys.end,
                           spyral.keys.pageup, spyral.keys.pagedown,
                           spyral.keys.numlock, spyral.keys.capslock,
                           spyral.keys.scrollock, spyral.keys.rctrl,
                           spyral.keys.rshift, spyral.keys.lshift,
                           spyral.keys.lctrl, spyral.keys.rmeta,
                           spyral.keys.ralt, spyral.keys.lalt,
                           spyral.keys.lmeta, spyral.keys.lsuper,
                           spyral.keys.rsuper, spyral.keys.mode)
    _non_skippable_keys = (' ', '.', '?', '!', '@', '#', '$',
                           '%', '^', '&', '*', '(', ')', '+',
                           '=', '{', '}', '[', ']', ';', ':',
                           '<', '>', ',', '/', '\\', '|', '"',
                           "'", '~', '`')
    _non_printable_keys = ('\t', '')+_non_insertable_keys

    def _find_next_word(self, text, start=0, end=None):
        """
        Returns the index of the next word in the given text.
        """
        if end is None:
            end = len(text)
        for index, letter in enumerate(text[start:end]):
            if letter in self._non_skippable_keys:
                return start+(index+1)
        return end

    def _find_previous_word(self, text, start=0, end=None):
        """
        Returns the index of the previous word in the given text.
        """
        if end is None:
            end = len(text)
        for index, letter in enumerate(reversed(text[start:end])):
            if letter in self._non_skippable_keys:
                return end-(index+1)
        return start

    def _delete(self, by_word = False):
        """
        Deletes the currently selected text, or the text at the current
        cursor position. If *by_word* is specified, the rest of the word is
        deleted too.
        """
        if self._selecting:
            start, end = sorted((self.cursor_pos, self._selection_pos))
            self.cursor_pos = start
            self._remove_char(start, end)
        elif by_word:
            start = self.cursor_pos
            end = self._find_next_word(self.value, self.cursor_pos, len(self._value))
            self._remove_char(start, end)
        else:
            self._remove_char(self.cursor_pos)

    def _backspace(self, by_word = False):
        """
        Deletes the currently selected text, or the character behind the current
        cursor position. If *by_word* is specified, the beginning of the word is
        deleted too.
        """
        if self._selecting:
            start, end = sorted((self.cursor_pos, self._selection_pos))
            self.cursor_pos = start
            self._remove_char(start, end)
        elif not self._cursor_pos:
            pass
        elif by_word:
            start = self._find_previous_word(self.value, 0, self.cursor_pos-1)
            end = self.cursor_pos
            self.cursor_pos= start
            self._remove_char(start, end)
        elif self._cursor_pos:
            self.cursor_pos-= 1
            self._remove_char(self.cursor_pos)

    def _move_cursor_left(self, by_word = False):
        """
        Moves the cursor left one character; if *by_word* is selected, then the
        cursor is moved to the start of the current word.
        """
        if by_word:
            self.cursor_pos = self._find_previous_word(self.value, 0, self.cursor_pos)
        else:
            self.cursor_pos= max(self.cursor_pos-1, 0)

    def _move_cursor_right(self, by_word = False):
        """
        Moves the cursor right one character; if *by_word* is selected, then the
        cursor is moved to the end of the current word.
        """
        if by_word:
            self.cursor_pos = self._find_next_word(self.value, self.cursor_pos, len(self.value))
        else:
            self.cursor_pos= min(self.cursor_pos+1, len(self.value))

    def _update(self, delta):
        """
        Make the cursor blink every blink_interval.
        """
        if self._focused:
            self._cursor_time += delta
            if self._cursor_time > self._cursor_blink_interval:
                self._cursor_time -= self._cursor_blink_interval
                self._cursor.visible = not self._cursor.visible

    def _handle_key_down(self, event):
        """
        Process a key input.
        """
        key = event.key
        mods = event.mod
        shift_is_down= (mods & spyral.mods.shift) or (key in (spyral.keys.lshift, spyral.keys.rshift))
        shift_clicked = not self._shift_was_down and shift_is_down
        self._shift_was_down = shift_is_down

        if shift_clicked or (shift_is_down and not
                             self._selecting and
                             key in TextInputWidget._non_insertable_keys):
            self._selection_pos = self.cursor_pos
            self._selecting = True

        if key == spyral.keys.left:
            self._move_cursor_left(mods & spyral.mods.ctrl)
        elif key == spyral.keys.right:
            self._move_cursor_right(mods & spyral.mods.ctrl)
        elif key == spyral.keys.home:
            self.cursor_pos = 0
        elif key == spyral.keys.end:
            self.cursor_pos = len(self.value)
        elif key == spyral.keys.delete:
            self._delete(mods & spyral.mods.ctrl)
        elif key == spyral.keys.backspace:
            self._backspace(mods & spyral.mods.ctrl)
        else:
            if key not in TextInputWidget._non_printable_keys:
                if self._selecting:
                    self._delete()
                unicode = chr(event.key)
                if self._validate(unicode):
                    self._insert_char(self.cursor_pos, unicode)
                    self.cursor_pos+= 1

        if not shift_is_down or (shift_is_down and key not in TextInputWidget._non_insertable_keys):
            self._selecting = False
            self._render_text()
        if self._selecting:
            self._render_text()

    # TODO: This is old style event handling, very clumsy!
    def _handle_mouse_over(self, event): pass
    def _handle_mouse_out(self, event): pass
    def _handle_key_up(self, event): pass

    def _handle_mouse_up(self, event):
        """
        Update the position of the text cursor when the mouse is released.
        """
        self.cursor_pos = self._compute_cursor_pos(event.pos)

    def _handle_mouse_down(self, event):
        """
        Handle mouse being pressed: start or stop selecting text, update the
        text cursor, and halt blinking.
        """
        if not self._selecting:
            if pygame.key.get_mods() & pygame.KMOD_SHIFT:
                self._selection_pos = self.cursor_pos
                self._selecting = True
        elif not (pygame.key.get_mods() & pygame.KMOD_SHIFT):
            self._selecting = False
        self.cursor_pos = self._compute_cursor_pos(event.pos)
        # set cursor position to mouse position
        if self.default_value:
            self.value = ''
            self.default_value = False
        self._render_text()
        self._stop_blinking()

    def _handle_mouse_motion(self, event):
        """
        Handle the text cursor being dragged.
        """
        left, center, right = event.buttons
        if left:
            if not self._selecting:
                self._selecting = True
                self._selection_pos = self.cursor_pos
            self.cursor_pos = self._compute_cursor_pos(event.pos)
            self._render_text()
            self._stop_blinking()

    def _handle_focus(self, event):
        """
        Handle this widget receiving focus.
        """
        self._focused = True
        self._back.image = self._image_focused
        if self.default_value:
            self._selecting = True
            self._selection_pos = 0
        else:
            self._selecting = False
        self.cursor_pos= len(self._value)
        self._render_text()

    def _handle_blur(self, event):
        """
        Handle this widget losing focus.
        """
        self._back.image = self._image_plain
        self._focused = False
        self._cursor.visible = False
        self.default_value = self._default_value_permanant


# Module Magic

old = sys.modules[__name__]

class _WidgetWrapper(object):
    creation_counter = 0
    def __init__(self, cls, *args, **kwargs):
        _WidgetWrapper.creation_counter += 1
        self.cls = cls
        self.args = args
        self.kwargs = kwargs

    def __call__(self, form, name):
        return self.cls(form, name, *self.args, **self.kwargs)
    def __setattr__(self, item, value):
        if item not in ('cls', 'args', 'kwargs'):
            raise AttributeError("Can't set properties in the class definition of a Widget! Set outside of the declarative region. See http://platipy.org/en/latest/spyral_docs.html#spyral.Form")
        else:
            super(_WidgetWrapper, self).__setattr__(item, value)

class module(types.ModuleType):
    def register(self, name, cls):
        setattr(self, name, functools.partial(_WidgetWrapper, cls))

# Keep the refcount from going to 0
widgets = module(__name__)
sys.modules[__name__] = widgets
widgets.__dict__.update(old.__dict__)

widgets.register('TextInput', TextInputWidget)
widgets.register('RadioButton', RadioButtonWidget)
widgets.register('Checkbox', CheckboxWidget)
widgets.register('ToggleButton', ToggleButtonWidget)
widgets.register('Button', ButtonWidget)
########NEW FILE########
__FILENAME__ = bezier
def calculate_bezier(p, steps=30):
    """calculate a bezier curve from 4 control points
    
    Returns a list of the resulting points.
    
    The function uses the forward differencing algorithm described here: 
    http://www.niksula.cs.hut.fi/~hkankaan/Homepages/bezierfast.html
    
    This code taken from www.pygame.org/wiki/BezierCurve.
    """
    #
    t = 1.0 / steps
    temp = t*t
    #
    f = p[0]
    fd = 3 * (p[1] - p[0]) * t
    fdd_per_2 = 3 * (p[0] - 2 * p[1] + p[2]) * temp
    fddd_per_2 = 3 * (3 * (p[1] - p[2]) + p[3] - p[0]) * temp * t
    #
    fddd = fddd_per_2 + fddd_per_2
    fdd = fdd_per_2 + fdd_per_2
    fddd_per_6 = fddd_per_2 * (1.0 / 3)
    #
    points = []
    for x in range(steps):
        points.append(f)
        f = f + fd + fdd_per_2 + fddd_per_6
        fd = fd + fdd + fddd_per_2
        fdd = fdd + fddd
        fdd_per_2 = fdd_per_2 + fddd_per_2
    points.append(f)
    return points
########NEW FILE########
__FILENAME__ = _style
"""Styling offers a way to offshore static data from your game into a .spys
file, improving the separation of code and data."""

import spyral
import parsley
import string
from ast import literal_eval

parser = None

def init():
    """
    Initializes the Styler.
    """
    global parser
    parser = StyleParser()
    style_file = open(spyral._get_spyral_path() +
                      'resources/style.parsley').read()
    parser.parser = parsley.makeGrammar(style_file,
                                        {"string": string,
                                         "parser": parser,
                                         "leval": literal_eval,
                                         "Vec2D": spyral.Vec2D})

def parse(style, scene):
    """
    Parses a style and applies it to the scene.

    :param str style: The style definition
    :param scene: The scene to apply this definition to.
    :type scene: :class:`Scene <spyral.Scene>`
    """
    parser.scene = scene
    parser.parse(style)

class StyleParser(object):
    """
    The style parser is a single instance class that converts a style file into
    attributes to be applied to an object (e.g., a Scene, View, or Sprite).
    """
    def __init__(self):
        self.scene = None
        self.classes = []

    def assign(self, identifier, value):
        """
        Assigns the identifier to the particular style symbol.

        :param str identifier: The identifier (?)
        :param ? value: ?
        """
        self.scene._style_symbols[identifier] = value

    def lookup(self, identifier):
        """
        Return the style symbols associated with this identifier in the scene.

        :param str identifier: The identifier (e.g., ?)
        """
        if identifier not in self.scene._style_symbols:
            raise NameError("%s is not a previously defined name in the styles"
                            % identifier)
        return self.scene._style_symbols[identifier]

    def calculate(self, ret, ops):
        for op in ops:
            if op[0] == '+':
                ret += op[1]
            elif op[0] == '-':
                ret -= op[1]
            elif op[0] == '*':
                ret *= op[1]
            elif op[0] == '/':
                ret /= op[1]
        return ret

    def push(self, classes):
        self.classes = classes

    def pop(self):
        self.classes = []

    def set_property(self, property, value):
        for cls in self.classes:
            if property == 'inherit':
                if value not in self.scene._style_properties:
                    raise ValueError(("Requested to inherit from "
                                     "'%s' which has no style") % value)
                self.scene._style_properties[cls].update(self.properties[value])
            else:
                self.scene._style_properties[cls][property] = value

    def apply_func(self, f, args):
        if f not in self.scene._style_functions:
            raise ValueError("Function '%s' is undefined" % f)
        return self.scene._style_functions[f](*args)

    def parse(self, style):
        parse = self.parser(style).all()

        # print 'Input Style:'
        # print style
        # print 'At the end of the parse, symbol table:'
        # import pprint
        # pprint.pprint(self.symbols)
        # print 'Now the properties'
        # pprint.pprint(dict(self.properties))

########NEW FILE########
__FILENAME__ = event_dispatching
try:
    import _path
except NameError:
    pass
import spyral

resolution = (640, 480)
spyral.director.init(resolution)
my_scene = spyral.Scene(resolution)
my_scene.background = spyral.Image(size=resolution).fill((0,0,0))
my_scene._namespaces = ("input.keyboard.down.q", "input.keyboard.down",
                        "input.keyboard.down.quoteright", "input.mouse.down",
                        "input.mouse", "animation.Sprite.x.end")

def test(key, *correct_namespaces):
    assert set(my_scene._get_namespaces(key)) == set(correct_namespaces) , \
           "Expected {}, got {}".format(set(correct_namespaces),
                                        set(my_scene._get_namespaces(key)))

test("input.keyboard", "input.keyboard.down.q", "input.keyboard.down", 
                       "input.keyboard.down.quoteright")            
test("input.keyboard.down.q", "input.keyboard.down.q", "input.keyboard.down")
test("input.keyboard.down", "input.keyboard.down.q", "input.keyboard.down",
                            "input.keyboard.down.quoteright")
test("input.keyboard.down.quoteright", "input.keyboard.down", 
                                       "input.keyboard.down.quoteright")
test("input.mouse.down", "input.mouse.down", "input.mouse")
test("animation.Sprite.x.end", "animation.Sprite.x.end")
########NEW FILE########
__FILENAME__ = view
import unittest
import spyral

class TestView(spyral.Scene):
    def __init__(self):
        spyral.init()
        spyral.director.init((100, 100))
        spyral.Scene.__init__(self, (100, 100))

    def test_properties(self):
        v = spyral.View(self)
        assert v.size == (100, 100)
        assert v.output_size == (100, 100)

        v.size = (150, 150)
        assert v.size == (150, 150)
        assert v.output_size == (100, 100)

        v.scale = 2
        assert v.size == (150, 150)
        assert v.output_size == (300, 300)

        v.scale = (2, 3)
        assert v.size == (150, 150)
        assert v.output_size == (300, 450)

        # Test Aliases
        v.pos = (20, 30)
        assert v.position == (20, 30)
        assert v.x == 20
        assert v.y == 30

        v.size = (1, 2)
        v.scale = 10
        assert v.width == 1
        assert v.output_width == 10
        assert v.height == 2
        assert v.output_height == 20

        assert v.anchor == 'topleft'
        v.anchor = 'center'
########NEW FILE########
__FILENAME__ = _path
import sys
import os
sys.path.insert(0, os.path.abspath('..'))
########NEW FILE########
