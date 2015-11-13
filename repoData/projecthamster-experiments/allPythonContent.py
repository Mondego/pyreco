__FILENAME__ = base
#!/usr/bin/env python
# - coding: utf-8 -
# Copyright (C) 2014 Toms Baugis <toms.baugis@gmail.com>

"""Base template"""

from gi.repository import Gtk as gtk
from lib import graphics

class Scene(graphics.Scene):
    def __init__(self):
        graphics.Scene.__init__(self)

        self.connect("on-enter-frame", self.on_enter_frame)

    def on_enter_frame(self, scene, context):
        # you could do all your drawing here, or you could add some sprites
        g = graphics.Graphics(context)

        # self.redraw() # this is how to get a constant redraw loop (say, for animation)



class BasicWindow:
    def __init__(self):
        window = gtk.Window()
        window.set_default_size(600, 500)
        window.connect("delete_event", lambda *args: gtk.main_quit())
        window.add(Scene())
        window.show_all()


if __name__ == '__main__':
    window = BasicWindow()
    import signal
    signal.signal(signal.SIGINT, signal.SIG_DFL) # gtk3 screws up ctrl+c
    gtk.main()

########NEW FILE########
__FILENAME__ = bitmap_caching
#!/usr/bin/env python
# - coding: utf-8 -
# Copyright (C) 2010 Toms Bauģis <toms.baugis at gmail.com>

"""Punishing cairo for expensive non-pixel-aligned stroking"""


from gi.repository import Gtk as gtk
from gi.repository import Gdk as gdk
from lib import graphics
from lib.pytweener import Easing
import random

class Wonky(graphics.Sprite):
    def __init__(self, x, y, radius, cache_as_bitmap):
        graphics.Sprite.__init__(self, x=x, y=y, interactive=True, cache_as_bitmap = cache_as_bitmap)
        self.radius = radius
        self.fill = "#aaa"
        self.connect("on-render", self.on_render)

    def on_render(self, sprite):
        self.graphics.circle(0, 0, self.radius)
        self.graphics.fill_stroke(self.fill, "#222")



class Scene(graphics.Scene):
    def __init__(self):
        graphics.Scene.__init__(self)

        self.connect("on-mouse-over", self.on_mouse_over)
        self.connect("on-mouse-out", self.on_mouse_out)
        self.connect("on-mouse-up", self.on_mouse_up)
        self.connect("on-mouse-move", self.on_mouse_move)
        self.connect("on-enter-frame", self.on_enter_frame)
        self.cache_as_bitmap = True
        self.paint_color = None
        self.add_child(graphics.Rectangle(600, 40, 4, "#666", opacity = 0.8, z_order = 999998))
        self.fps_label = graphics.Label(size = 20, color = "#fff", z_order=999999, x = 10, y = 4)
        self.add_child(self.fps_label)
        self.bubbles = []
        self.max_zorder = 1

    def on_mouse_move(self, scene, event):
        sprite = self.get_sprite_at_position(event.x, event.y)

        if sprite and gdk.ModifierType.BUTTON1_MASK & event.state:
            if self.paint_color is None:
                if sprite.fill == "#f00":
                    self.paint_color =  "#aaa"
                elif sprite.fill == "#aaa":
                    self.paint_color = "#f00"
            self.animate(sprite, fill=self.paint_color)

    def on_mouse_up(self, scene, event):
        self.paint_color = None

    def on_mouse_over(self, scene, sprite):
        sprite.original_radius = sprite.radius
        self.animate(sprite, radius = sprite.radius * 1.3, easing = Easing.Elastic.ease_out, duration = 1)
        self.max_zorder +=1
        sprite.z_order = self.max_zorder


    def on_mouse_out(self, scene, sprite):
        self.animate(sprite, radius = sprite.original_radius, easing = Easing.Elastic.ease_out)

    def on_enter_frame(self, scene, context):
        self.fps_label.text = "Hold mouse down and drag to paint. FPS: %.2f" % self.fps

        if not self.bubbles:
            for x in range(30, self.width, 50):
                for y in range(30, self.height, 50):
                    wonky = Wonky(x, y, 20, self.cache_as_bitmap)
                    self.bubbles.append(wonky)
                    self.add_child(wonky)
                    self.animate(wonky,
                                 radius = wonky.radius * 1.3,
                                 easing = Easing.Elastic.ease_out,
                                 duration=2)




class BasicWindow:
    def __init__(self):
        window = gtk.Window()
        window.set_size_request(800, 500)
        window.connect("delete_event", lambda *args: gtk.main_quit())

        vbox = gtk.VBox()

        self.scene = Scene()
        vbox.pack_start(self.scene, True, True, 0)

        self.button = gtk.Button("Cache as bitmap = True")

        def on_click(event):
            self.scene.cache_as_bitmap = not self.scene.cache_as_bitmap
            self.scene.remove_child(*self.scene.bubbles)
            self.scene.bubbles = []
            self.button.set_label("Cache as bitmap = %s" % str(self.scene.cache_as_bitmap))
            self.scene.redraw()


        self.button.connect("clicked", on_click)
        vbox.pack_start(self.button, False, False, 0)

        window.add(vbox)
        window.show_all()

example = BasicWindow()
import signal
signal.signal(signal.SIGINT, signal.SIG_DFL) # gtk3 screws up ctrl+c
gtk.main()

########NEW FILE########
__FILENAME__ = blur
#!/usr/bin/env python
# - coding: utf-8 -
# Copyright (C) 2010 Toms Bauģis <toms.baugis at gmail.com>
"""
 * Blur.
 *
 * Bluring half of an image by processing it through a
 * low-pass filter.

 Ported from processing (http://processing.org)
 --
 Blur from processing, only million times slower or something in the lines.
 Right now slowness primarily is in getting pixel and determining it's color.
 The get_pixels_array of gtk.Pixbuf does not make things faster either as
 one has to unpack structures, which again is tad expensive.
"""

from gi.repository import Gtk as gtk
from lib import graphics
import math
import random
import datetime as dt
import cairo
import struct

class Canvas(graphics.Scene):
    def __init__(self):
        graphics.Scene.__init__(self)
        self.tile_size = 30

        self.connect("on-enter-frame", self.on_enter_frame)


    def on_enter_frame(self, scene, context):
        g = graphics.Graphics(context)

        self.two_tile_random(context)

        g.move_to(0,0)
        g.show_label("Hello", size=48, color="#33a")

        # creating a in-memory image of current context
        image_surface = cairo.ImageSurface(cairo.FORMAT_RGB24, self.width, self.height)
        image_context = cairo.Context(image_surface)

        # copying
        image_context.set_source_surface(context.get_target())
        image_context.paint()

        # buffer allows us to manipulate the pixels directly
        buffer = image_surface.get_data()

        # blur
        self.blur(buffer)

        # and paint it back
        context.set_source_surface(image_surface)
        context.paint()


        self.redraw()



    def blur(self, buffer):
        t = dt.datetime.now()

        def get_pixel(x, y):
            pos = (x * self.height + y) * 4
            (b, g, r, a) = struct.unpack('BBBB', buffer[pos:pos+4])
            return (r, g, b, a)

        v = 1.0 / 9.0
        kernel = ((v, v, v),
                  (v, v, v),
                  (v, v, v))

        kernel_range = range(-1, 2) # surrounding the pixel



        height, width = self.height, self.width


        # we will need all the pixel colors anyway, so let's grab them once
        pixel_colors = struct.unpack_from('BBBB' * width * height, buffer)

        new_pixels = [0] * width * height * 4 # target matrix

        for x in range(1, width - 1):
            for y in range(1, height - 1):
                r,g,b = 0,0,0
                pos = (x * height + y) * 4

                for ky in kernel_range:
                    for kx in kernel_range:
                        k = kernel[kx][ky]
                        k_pos = pos + kx * height * 4 + ky * 4

                        pixel_r,pixel_g,pixel_b = pixel_colors[k_pos:k_pos + 3]

                        r += k * pixel_r
                        g += k * pixel_g
                        b += k * pixel_b

                new_pixels[pos:pos+3] = (r,g,b)

        struct.pack_into('BBBB' * self.width * self.height, buffer, 0, *new_pixels)
        print "%d x %d," %(self.width, self.height), dt.datetime.now() - t



    def two_tile_random(self, context):
        """stroke area with non-filed truchet (since non filed, all match and
           there are just two types"""
        context.set_source_rgb(0,0,0)
        context.set_line_width(1)

        for y in range(0, self.height, self.tile_size):
            for x in range(0, self.width, self.tile_size):
                self.stroke_tile(context, x, y, self.tile_size, random.choice([1, 2]))
        context.stroke()


    def stroke_tile(self, context, x, y, size, orient):
        # draws a tile, there are just two orientations
        arc_radius = size / 2
        x2, y2 = x + size, y + size

        # i got lost here with all the Pi's
        if orient == 1:
            context.move_to(x + arc_radius, y)
            context.arc(x, y, arc_radius, 0, math.pi / 2);

            context.move_to(x2 - arc_radius, y2)
            context.arc(x2, y2, arc_radius, math.pi, math.pi + math.pi / 2);
        elif orient == 2:
            context.move_to(x2, y + arc_radius)
            context.arc(x2, y, arc_radius, math.pi - math.pi / 2, math.pi);

            context.move_to(x, y2 - arc_radius)
            context.arc(x, y2, arc_radius, math.pi + math.pi / 2, 0);


class BasicWindow:
    def __init__(self):
        window = gtk.Window()
        window.set_size_request(200, 200)
        window.connect("delete_event", lambda *args: gtk.main_quit())
        window.add(Canvas())
        window.show_all()


if __name__ == "__main__":
    example = BasicWindow()
    import signal
    signal.signal(signal.SIGINT, signal.SIG_DFL) # gtk3 screws up ctrl+c
    gtk.main()

########NEW FILE########
__FILENAME__ = bouncy_bubbles
#!/usr/bin/env python
# - coding: utf-8 -
# Copyright (C) 2010 Toms Bauģis <toms.baugis at gmail.com>

"""
 * Bouncy Bubbles.
 * Based on code from Keith Peters (www.bit-101.com).
 *
 * Multiple-object collision.

 Ported from processing (http://processing.org/).
 Also added mass to the ball that is equal to the radius.
"""

from gi.repository import Gtk as gtk
from lib import graphics

import math
from random import randint


SPRING = 0.05;
GRAVITY = 0.1;
FRICTION = -0.3;


class Ball(graphics.Circle):
    def __init__(self, x, y, radius):
        graphics.Circle.__init__(self, radius * 2, radius * 2, fill="#aaa", x = x, y = y)

        self.width = self.height = radius * 2

        self.radius = radius

        # just for kicks add mass, so bigger balls would not bounce as easy as little ones
        self.mass = float(self.radius) * 2

        # velocity
        self.vx = 0
        self.vy = 0

    def move(self, width, height):
        self.vy += GRAVITY
        self.x += self.vx
        self.y += self.vy

        # bounce of the walls
        if self.x - self.width < 0 or self.x + self.width > width:
            self.vx = self.vx * FRICTION

        if self.y - self.height < 0 or self.y + self.height > height:
            self.vy = self.vy * FRICTION

        self.x = max(self.width, min(self.x, width - self.width))
        self.y = max(self.height, min(self.y, height - self.height))


    def colide(self, others):
        for ball in others:
            if ball == self:
                continue

            dx = ball.x - self.x
            dy = ball.y - self.y

            # we are using square as root is bit expensive
            min_distance = (self.radius + ball.radius) * (self.radius + ball.radius)

            if (dx * dx + dy * dy) < min_distance:
                min_distance = self.radius + ball.radius
                angle = math.atan2(dy, dx)
                target_x = self.x + math.cos(angle) * min_distance
                target_y = self.y + math.sin(angle) * min_distance

                ax = (target_x - ball.x) * SPRING
                ay = (target_y - ball.y) * SPRING

                mass_ratio = self.mass / ball.mass

                self.vx -= ax / mass_ratio
                self.vy -= ay / mass_ratio

                # repulse
                ball.vx += ax * mass_ratio
                ball.vy += ay * mass_ratio


class Scene(graphics.Scene):
    def __init__(self):
        graphics.Scene.__init__(self)
        self.balls = []
        self.window_pos = None

        self.connect("on-enter-frame", self.on_enter_frame)

    def on_enter_frame(self, scene, context):
        # render and update positions of the balls
        if not self.balls:
            for i in range(15):
                radius = randint(10, 30)
                ball = Ball(randint(radius, self.width - radius),
                                    randint(radius, self.height - radius),
                                    radius)
                self.balls.append(ball)
                self.add_child(ball)


        for ball in self.balls:
            ball.move(self.width, self.height)
            ball.colide(self.balls)


        window_pos = self.get_toplevel().get_position()
        if self.window_pos and window_pos != self.window_pos:
            dx = window_pos[0] - self.window_pos[0]
            dy = window_pos[1] - self.window_pos[1]
            for ball in self.balls:
                ball.x -= dx
                ball.y -= dy
        self.window_pos = window_pos

        self.redraw()


class BasicWindow:
    def __init__(self):
        window = gtk.Window()
        window.set_size_request(700, 300)
        window.connect("delete_event", lambda *args: gtk.main_quit())
        window.add(Scene())
        window.show_all()


if __name__ == "__main__":
    example = BasicWindow()
    gtk.main()

########NEW FILE########
__FILENAME__ = braile
#!/usr/bin/env python
# - coding: utf-8 -
# Copyright (C) 2011 Toms Bauģis <toms.baugis at gmail.com>

"""Braile letter toy - inspired by GSOC project
   http://srishtisethi.blogspot.com/2011/05/hallo-gnome-weekly-report-1-gsoc.html
"""

import string
from gi.repository import Gtk as gtk
from gi.repository import Pango as pango
from lib import graphics

braile_letters = {
    "a": (1,), "b": (1, 2), "c": (1, 4), "d": (1, 4, 5), "e": (1, 5),
    "f": (1, 2, 4), "g": (1, 2, 4, 5), "h": (1, 2, 5), "i": (2, 4),
    "j": (2, 4, 5), "k": (1, 3), "l": (1, 2, 3), "m": (1, 3, 4),
    "n": (1, 3, 4, 5), "o": (1, 3, 5), "p": (1, 2, 3, 4), "q": (1, 2, 3, 4, 5),
    "r": (1, 2, 3, 5), "s": (2, 3, 4), "t": (2, 3, 4, 5), "u": (1, 3, 6),
    "v": (1, 2, 3, 6), "w": (2, 4, 5, 6), "x": (1, 3, 4, 6), "y": (1, 3, 4, 5, 6),
    "z": (1, 3, 5, 6),
}


class BrailCell(graphics.Sprite):
    """a cell displaying braile character"""

    def __init__(self, letter = "", width = None, interactive = False, border = False, **kwargs):
        graphics.Sprite.__init__(self, **kwargs)
        self.interactive = interactive

        self.width = width

        padding = self.width * 0.1
        cell_size = self.width / 2 - padding

        inner_padding = self.width * 0.08
        cell_radius = cell_size - inner_padding * 2

        self.cells = []
        for x in range(2):
            for y in range(3):
                cell = graphics.Circle(cell_radius,
                                       cell_radius,
                                       interactive = interactive,
                                       stroke = "#333",
                                       x = padding + x * cell_size + inner_padding,
                                       y = padding + y * cell_size + inner_padding)
                if interactive:
                    cell.connect("on-mouse-over", self.on_mouse_over)
                    cell.connect("on-mouse-out", self.on_mouse_out)

                self.add_child(cell)
                self.cells.append(cell) # keep a separate track so we don't mix up with other sprites


        if border:
            self.add_child(graphics.Rectangle(cell_size * 2 + padding * 2,
                                              cell_size * 3 + padding * 2,
                                              stroke="#000"))

        self.letter = letter

    def on_mouse_over(self, cell):
        cell.original_fill = cell.fill
        cell.fill = "#080"

    def on_mouse_out(self, cell):
        cell.fill = cell.original_fill

    def fill_cells(self):
        fillings = braile_letters.get(self.letter.lower())
        for i in range(6):
            if (i + 1) in fillings:
                self.cells[i].fill = "#333"
            else:
                self.cells[i].fill = None

    def __setattr__(self, key, val):
        graphics.Sprite.__setattr__(self, key, val)
        if key == "letter":
            self.fill_cells()


class BrailTile(graphics.Sprite):
    """an interactive brail tile that e"""

    def __init__(self, letter, cell_width, **kwargs):
        graphics.Sprite.__init__(self, **kwargs)

        self.letter = letter

        mouse_rectangle = graphics.Rectangle(cell_width, cell_width * 1.4, 7, stroke="#000", interactive = True)
        self.add_child(mouse_rectangle)

        mouse_rectangle.connect("on-mouse-over", self.on_mouse_over)
        mouse_rectangle.connect("on-mouse-out", self.on_mouse_out)
        mouse_rectangle.connect("on-click", self.on_click)

        self.add_child(BrailCell(letter, width = cell_width))
        self.add_child(graphics.Label(letter, size = 14, color="#000",
                                      x = 12, y = cell_width * 1.4 + 5))

    def on_mouse_over(self, sprite):
        sprite.fill = "#ccc"

    def on_mouse_out(self, sprite):
        sprite.fill = None

    def on_click(self, sprite, event):
        self.emit("on-click", event)



class Scene(graphics.Scene):
    def __init__(self):
        graphics.Scene.__init__(self)


        # letter display
        letter_display = graphics.Sprite(x=100)
        self.letter = graphics.Label(x=30, y = 40, text="F", size=200, color="#333")
        letter_display.add_child(self.letter)

        self.add_child(letter_display)


        # cell board
        cellboard = graphics.Sprite(x=450)
        self.letter_cell = BrailCell("f", x = 50, y=50, width = 200, interactive = True)
        cellboard.add_child(self.letter_cell)

        for i in range(2):
            for j in range(3):
                cellboard.add_child(graphics.Label(str(j + 1 + i * 3),
                                                   size = 50,
                                                   color = "#333",
                                                   x = i * 230 + 20,
                                                   y = j * 90 + 60))

        self.add_child(cellboard)

        # lowerboard
        lowerboard = graphics.Sprite(x=50, y = 450)
        cell_width = 40
        for i, letter in enumerate(string.ascii_uppercase[:13]):
            tile = BrailTile(letter = letter, cell_width = cell_width, x = i * (cell_width + 10) + 10)
            tile.connect("on-click", self.on_tile_click)
            lowerboard.add_child(tile)

        self.add_child(lowerboard)

    def on_tile_click(self, tile, event):
        self.letter.text = tile.letter
        self.letter_cell.letter = tile.letter



class BasicWindow:
    def __init__(self):
        window = gtk.Window()
        window.set_default_size(800, 600)
        window.connect("delete_event", lambda *args: gtk.main_quit())
        window.add(Scene())
        window.show_all()

if __name__ == '__main__':
    window = BasicWindow()
    import signal
    signal.signal(signal.SIGINT, signal.SIG_DFL) # gtk3 screws up ctrl+c
    gtk.main()

########NEW FILE########
__FILENAME__ = buzz
#!/usr/bin/env python
# - coding: utf-8 -
# Copyright (C) 2014 Toms Baugis <toms.baugis@gmail.com>

"""A quick stab."""
import math
import random

from gi.repository import Gtk as gtk
from lib import graphics
from lib import layout
from lib.pytweener import Easing

class Rattle(graphics.Sprite):
    def __init__(self, **kwargs):
        graphics.Sprite.__init__(self, **kwargs)
        self.connect("on-render", self.on_render)
        self.snap_to_pixel = False

        self._intensity = 0

        self.shake_range = 5
        self.easing = Easing.Sine
        self.duration = 1.3
        self.fill = "#ddd"


    def buzz(self, sprite=None):
        graphics.chain([
            [self, {"_intensity": self.shake_range,
                    "duration": self.duration,
                    "easing": self.easing.ease_in,
                    "on_update": self._update_buzz}],
            [self, {"_intensity": 0,
                    "duration": self.duration,
                    "easing": self.easing.ease_out,
                    "on_update": self._update_buzz,
                    "on_complete": self.buzz}]
        ])


    def _update_buzz(self, sprite):
        self.update_buzz()

    def rattle(self):
        pass

    def on_render(self, sprite):
        self.graphics.rectangle(-25, -25, 50, 50)
        self.graphics.fill(self.fill)

class RattleRandomXY(Rattle):
    def update_buzz(self):
        shake_range = self._intensity
        self.x = (1 - 2 * random.random()) * shake_range
        self.y = (1 - 2 * random.random()) * shake_range


class RattleRandomAngle(Rattle):
    def update_buzz(self):
        shake_range = self._intensity
        angle = random.randint(0, 360)
        self.x = math.cos(math.radians(angle)) * shake_range
        self.y = math.sin(math.radians(angle)) * shake_range


class RattleRandomAngleShadow(RattleRandomAngle):
    def __init__(self, **kwargs):
        RattleRandomAngle.__init__(self, **kwargs)
        self.prev_x, self.prev_y = 0, 0

    def update_buzz(self):
        self.prev_x, self.prev_y = self.x, self.y
        RattleRandomAngle.update_buzz(self)

    def on_render(self, sprite):
        self.graphics.rectangle(-25 - self.prev_x + self.x, -25 - self.prev_y + self.y, 50, 50)
        self.graphics.fill(self.fill, 0.3)

        self.graphics.rectangle(-25, -25, 50, 50)
        self.graphics.fill(self.fill)

class RattleRandomAngle2Shadow(RattleRandomAngleShadow):
    def on_render(self, sprite):
        self.graphics.rectangle(-25 + self.prev_x - self.x, -25 + self.prev_y - self.y, 50, 50)
        self.graphics.fill(self.fill, 0.3)

        self.graphics.rectangle(-25 - self.prev_x + self.x, -25 - self.prev_y + self.y, 50, 50)
        self.graphics.fill(self.fill, 0.3)

        self.graphics.rectangle(-25, -25, 50, 50)
        self.graphics.fill(self.fill)



class RattleWithEase(graphics.Sprite):
    """
        Want to go from prev random to next random using animation.
        It will be super-short steps, the intensity updated on completion of
        each step
    """
    def __init__(self, **kwargs):
        graphics.Sprite.__init__(self, **kwargs)
        self.connect("on-render", self.on_render)
        self.snap_to_pixel = False

        self._intensity = 0

        self.shake_range = 4
        self.easing = Easing.Sine

        self.step_duration = 0.01
        self.duration = 0.75
        self.fill = "#ddd"
        self.prev_x, self.prev_y = 0, 0
        self.next_x, self.next_y = 0, 0
        self.current_step = 0

    def buzz(self):
        self.buzz_in()

    def buzz_in(self, sprite=None):
        self.current_step += 1 / (self.duration / self.step_duration)
        if self.current_step > 1:
            self.current_step = 1
            self.buzz_out()
            return

        shake_range = self.easing.ease_in(self.current_step) * self.shake_range
        angle = random.randint(0, 360)

        self.next_x = (1 - 2 * random.random()) * shake_range
        self.next_y = (1 - 2 * random.random()) * shake_range

        self.animate(x=self.next_x, y=self.next_y,
                     duration=self.step_duration,
                     easing=Easing.Linear.ease_in,
                     on_update=self.on_render,
                     on_complete=self.buzz_in)

    def buzz_out(self, sprite=None):
        self.current_step -= 1 / (self.duration / self.step_duration)
        if self.current_step < 0:
            self.current_step = 0
            self.buzz_in()
            return

        shake_range = self.easing.ease_in(self.current_step) * self.shake_range
        angle = random.randint(0, 360)
        self.next_x = (1 - 2 * random.random()) * shake_range
        self.next_y = (1 - 2 * random.random()) * shake_range

        self.animate(x=self.next_x, y=self.next_y,
                     duration=self.step_duration,
                     easing=Easing.Linear.ease_in,
                     on_update=self.on_render,
                     on_complete=self.buzz_out)


    def on_render(self, sprite):
        self.graphics.rectangle(-25 + self.prev_x - self.x, -25 + self.prev_y - self.y, 50, 50)
        self.graphics.fill(self.fill, 0.3)

        self.graphics.rectangle(-25 - self.prev_x + self.x, -25 - self.prev_y + self.y, 50, 50)
        self.graphics.fill(self.fill, 0.3)

        self.graphics.rectangle(-25, -25, 50, 50)
        self.graphics.fill(self.fill)
        self.prev_x, self.prev_y = self.x, self.y


class Scene(graphics.Scene):
    def __init__(self):
        graphics.Scene.__init__(self, background_color="#333")


        self.rattles = [
            RattleRandomXY(),
            RattleRandomAngle(),
            RattleRandomAngleShadow(),
            RattleRandomAngle2Shadow(),
            RattleWithEase(),
        ]

        box = layout.HBox()
        self.add_child(box)

        for rattle in self.rattles:
            container = layout.VBox(
                rattle,
                fill=False
            )
            box.add_child(container)

        self.rattling = False
        self.connect("on-first-frame", self.on_first_frame)

    def on_first_frame(self, scene, context):
        for rattle in self.rattles:
            rattle.buzz()



class BasicWindow:
    def __init__(self):
        window = gtk.Window()
        window.set_default_size(600, 500)
        window.connect("delete_event", lambda *args: gtk.main_quit())
        window.add(Scene())
        window.show_all()


if __name__ == '__main__':
    window = BasicWindow()
    import signal
    signal.signal(signal.SIGINT, signal.SIG_DFL) # gtk3 screws up ctrl+c
    gtk.main()

########NEW FILE########
__FILENAME__ = clipping
#!/usr/bin/env python
# - coding: utf-8 -
# Copyright (C) 2010 Toms Bauģis <toms.baugis at gmail.com>

"""
Clipping demo - two labels in different colors are put on each other
but before painting the area is clipped so that first label gets 0 -> mouse_x
width and the other mouse_x -> window width
"""


from gi.repository import Gtk as gtk
from lib import graphics


class Scene(graphics.Scene):
    def __init__(self):
        graphics.Scene.__init__(self, framerate=30)
        self.connect("on-enter-frame", self.on_enter_frame)

    def on_enter_frame(self, scene, context):
        g = graphics.Graphics(context)

        g.save_context()


        g.rectangle(0, 0, self.mouse_x, self.height)
        g.clip()
        g.move_to(20, 100)
        g.show_label("Hello", font_desc="Sans Serif 150", color="#fff")

        g.restore_context()

        g.save_context()
        g.rectangle(self.mouse_x, 0, self.width, self.height)
        g.clip()
        g.move_to(20, 100)
        g.show_label("Hello", font_desc="Sans Serif 150", color="#000")
        g.restore_context()

        self.redraw()






class BasicWindow:
    def __init__(self):
        window = gtk.Window()
        window.set_default_size(600, 500)
        window.connect("delete_event", lambda *args: gtk.main_quit())
        window.add(Scene())
        window.show_all()

if __name__ == '__main__':
    window = BasicWindow()
    import signal
    signal.signal(signal.SIGINT, signal.SIG_DFL) # gtk3 screws up ctrl+c
    gtk.main()

########NEW FILE########
__FILENAME__ = cogs
#!/usr/bin/env python
# - coding: utf-8 -
# Copyright (C) 2014 You <your.email@someplace>

"""Base template"""

import math
from gi.repository import Gtk as gtk
from lib import graphics

class Cog(graphics.Sprite):
    def __init__(self, radius=None, teeth=None, axis_distance = None, tooth_height=None,
                 tooth_width=None, inset=None, fill=None, **kwargs):
        graphics.Sprite.__init__(self, **kwargs)
        self.connect("on-render", self.on_render)

        self.radius = radius

        self.teeth = teeth or int(radius / 5)

        self.fill = fill or "#999"

        self.tooth_width = tooth_width or int(radius / 8)
        self.tooth_height = tooth_height or self.tooth_width * 1.5

        self.axis_distance = axis_distance or 20
        self.inset = inset or False

        self.interactive = True

    def on_render(self, sprite):
        direction = -1 if self.inset else 1

        radius = self.radius - direction * self.tooth_height / 2


        self.graphics.move_to(100, 0)

        steps = int(self.teeth)
        degrees = 360 * 1.0 / self.teeth

        if self.inset:
            self.graphics.move_to(radius - direction * self.axis_distance, 0)
            self.graphics.circle(0, 0, radius - direction * self.axis_distance)
            self.graphics.fill_stroke("#fafafa", "#333")

        self.graphics.save_context()
        for i in range(steps):
            self.graphics.rotate(math.radians(degrees))


            if i == 0:
                self.graphics.move_to(-self.tooth_width/2, -radius)
            self.graphics.line_to(-self.tooth_width/2, -radius)

            self.graphics.line_to(-self.tooth_width/2 + self.tooth_width/3,
                                  -radius - direction * self.tooth_height)

            self.graphics.line_to(self.tooth_width/2 - self.tooth_width/3,
                                  -radius - direction * self.tooth_height)

            self.graphics.line_to(self.tooth_width/2, -radius)

        self.graphics.set_line_style(width=1)
        self.graphics.rotate(math.radians(degrees))
        self.graphics.line_to(-self.tooth_width/2, -radius)
        self.graphics.restore_context()
        self.graphics.fill_stroke(self.fill, "#666")

        if not self.inset:
            self.graphics.circle(0, 0, radius - direction * self.axis_distance)
            self.graphics.fill_stroke("#fafafa", "#333")




class Scene(graphics.Scene):
    def __init__(self):
        graphics.Scene.__init__(self)

        self.container = graphics.Sprite(x=300, y=250)
        self.add_child(self.container)

        width, height = 10, 10

        self.inner = Cog(radius=40, teeth=20, rotation=-0.114,
                         fill="#D5C439",
                         tooth_width=width, tooth_height=height)
        self.outer = Cog(radius=200, teeth=100,
                         fill="#CEE2A6",
                         inset=True, tooth_height=height, tooth_width=width, axis_distance=10)

        radius, teeth = 75, 37


        self.middles = []
        distance, angle = -120, 0
        for i in range(3):
            angle += 120
            x, y = (math.sin(math.radians(angle)) * distance,
                    math.cos(math.radians(angle)) * distance)
            middle = Cog(x=x, y=y, rotation=-0.114,
                         radius=75, teeth=37,
                         fill="#3D699B",
                         tooth_width=width, tooth_height=height,
                         axis_distance=50)
            self.middles.append(middle)


        self.container.add_child(self.outer, self.inner)
        self.container.add_child(*self.middles)

        self.reference_point = None
        self.connect("on-click", self.on_click)

        self.connect("on-enter-frame", self.on_enter_frame)

    def on_click(self, scene, event, sprite):
        self.reference_point = sprite

    def on_enter_frame(self, scene, context):
        speed = 0.005

        self.inner.rotation += speed * 5
        self.outer.rotation -= speed

        for middle in self.middles:
            middle.rotation -= speed * 2.7

        if self.reference_point:
            self.container.rotation = -self.reference_point.rotation
        else:
            self.container.rotation = 0

        self.redraw()



class BasicWindow:
    def __init__(self):
        window = gtk.Window()
        window.set_default_size(600, 500)
        window.connect("delete_event", lambda *args: gtk.main_quit())
        window.add(Scene())
        window.show_all()

if __name__ == '__main__':
    window = BasicWindow()
    import signal
    signal.signal(signal.SIGINT, signal.SIG_DFL) # gtk3 screws up ctrl+c
    gtk.main()

########NEW FILE########
__FILENAME__ = euclid
#!/usr/bin/env python
#
# euclid graphics maths module
#
# Copyright (c) 2006 Alex Holkner
# Alex.Holkner@mail.google.com
#
# This library is free software; you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published by the
# Free Software Foundation; either version 2.1 of the License, or (at your
# option) any later version.
#
# This library is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License
# for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this library; if not, write to the Free Software Foundation,
# Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301 USA

'''euclid graphics maths module

Documentation and tests are included in the file "euclid.txt", or online
at http://code.google.com/p/pyeuclid
'''

__docformat__ = 'restructuredtext'
__version__ = '$Id$'
__revision__ = '$Revision$'

import math
import operator
import types



class Vector2(object):
    __slots__ = ['x', 'y']

    def __init__(self, x=0, y=0):
        self.x = x
        self.y = y

    def __copy__(self):
        return self.__class__(self.x, self.y)

    copy = __copy__

    def __repr__(self):
        return 'Vector2(%.2f, %.2f)' % (self.x, self.y)

    def __eq__(self, other):
        if not other: return False

        if isinstance(other, Vector2):
            return self.x == other.x and \
                   self.y == other.y
        else:
            if hasattr(other, '__len__') and len(other) == 2:
                return self.x == other[0] and \
                       self.y == other[1]
            else:
                return False

    def __neq__(self, other):
        return not self.__eq__(other)

    def __nonzero__(self):
        return self.x != 0 or self.y != 0

    def __len__(self):
        return 2

    def __getitem__(self, key):
        return (self.x, self.y)[key]

    def __setitem__(self, key, value):
        l = [self.x, self.y]
        l[key] = value
        self.x, self.y = l

    def __iter__(self):
        return iter((self.x, self.y))

    def __getattr__(self, name):
        try:
            return tuple([(self.x, self.y)['xy'.index(c)] \
                          for c in name])
        except ValueError:
            raise AttributeError, name

    def __add__(self, other):
        return Vector2(self.x + other.x, self.y + other.y)

    __radd__ = __add__

    def __iadd__(self, other):
        self.x += other.x
        self.y += other.y
        return self

    def __sub__(self, other):
        return Vector2(self.x - other.x, self.y - other.y)

    def __rsub__(self, other):
        return Vector2(other.x - self.x, other.y - self.y)

    def __mul__(self, other):
        return Vector2(self.x * other, self.y * other)

    __rmul__ = __mul__

    def __imul__(self, other):
        self.x *= other
        self.y *= other
        return self

    def __div__(self, other):
        return Vector2(operator.div(self.x, other),
                       operator.div(self.y, other))


    def __rdiv__(self, other):
        return Vector2(operator.div(other, self.x),
                       operator.div(other, self.y))

    def __floordiv__(self, other):
        return Vector2(operator.floordiv(self.x, other),
                       operator.floordiv(self.y, other))


    def __rfloordiv__(self, other):
        return Vector2(operator.floordiv(other, self.x),
                       operator.floordiv(other, self.y))

    def __truediv__(self, other):
        return Vector2(operator.truediv(self.x, other),
                       operator.truediv(self.y, other))

    def __rtruediv__(self, other):
        return Vector2(operator.truediv(other, self.x),
                       operator.truediv(other, self.y))

    def __neg__(self):
        return Vector2(-self.x, -self.y)

    __pos__ = __copy__

    def __abs__(self):
        return math.sqrt(self.x * self.x + self.y * self.y)

    magnitude = __abs__

    def magnitude_squared(self):
        return self.x * self.x + self.y * self.y

    def normalize(self):
        d = self.magnitude()
        if d:
            self.x /= d
            self.y /= d
        return self

    def normalized(self):
        d = self.magnitude()
        if d:
            return Vector2(self.x / d, self.y / d)
        return self.copy()

    def dot(self, other):
        assert isinstance(other, Vector2)
        return self.x * other.x + \
               self.y * other.y

    def cross(self):
        return Vector2(self.y, -self.x)

    def product(self, v2):
        # product of our vector and the other vector's perpendicular
        return self.x * v2.y - self.y * v2.x

    def reflect(self, normal):
        # assume normal is normalized
        assert isinstance(normal, Vector2)
        d = 2 * (self.x * normal.x + self.y * normal.y)
        return Vector2(self.x - d * normal.x,
                       self.y - d * normal.y)

    def limit(self, max_magnitude):
        if self.magnitude() > max_magnitude:
            self.normalize()
            self *= max_magnitude

    def heading(self):
        return math.atan2(self.y, self.x)

    def angle(self, other):
        """angle between this and the other vector in radians"""
        if self == -other:  # same vector facing the opposite way will kill acos on float precision
            return math.pi

        return math.acos(self.normalized().dot(other.normalized()))


# Geometry
# Much maths thanks to Paul Bourke, http://astronomy.swin.edu.au/~pbourke
# ---------------------------------------------------------------------------

class Geometry(object):
    def _connect_unimplemented(self, other):
        raise AttributeError, 'Cannot connect %s to %s' % \
            (self.__class__, other.__class__)

    def _intersect_unimplemented(self, other):
        raise AttributeError, 'Cannot intersect %s and %s' % \
            (self.__class__, other.__class__)

    _intersect_point2 = _intersect_unimplemented
    _intersect_line2 = _intersect_unimplemented
    _intersect_circle = _intersect_unimplemented
    _connect_point2 = _connect_unimplemented
    _connect_line2 = _connect_unimplemented
    _connect_circle = _connect_unimplemented


    def intersect(self, other):
        raise NotImplementedError

    def connect(self, other):
        raise NotImplementedError

    def distance(self, other):
        c = self.connect(other)
        if c:
            return c.length
        return 0.0

def _intersect_point2_circle(P, C):
    return (P - C.c).magnitude_squared() <= C.r * C.r

def _intersect_line2_line2(A, B):
    d = B.v.y * A.v.x - B.v.x * A.v.y
    if d == 0:
        return None

    dy = A.p.y - B.p.y
    dx = A.p.x - B.p.x
    ua = (B.v.x * dy - B.v.y * dx) / d
    if not A._u_in(ua):
        return None
    ub = (A.v.x * dy - A.v.y * dx) / d
    if not B._u_in(ub):
        return None

    return Point2(A.p.x + ua * A.v.x,
                  A.p.y + ua * A.v.y)

def _intersect_line2_circle(L, C):
    a = L.v.magnitude_squared()
    b = 2 * (L.v.x * (L.p.x - C.c.x) + \
             L.v.y * (L.p.y - C.c.y))
    c = C.c.magnitude_squared() + \
        L.p.magnitude_squared() - \
        2 * C.c.dot(L.p) - \
        C.r * C.r
    det = b * b - 4 * a * c
    if det < 0:
        return None
    sq = math.sqrt(det)
    u1 = (-b + sq) / (2 * a)
    u2 = (-b - sq) / (2 * a)
    if not L._u_in(u1):
        u1 = max(min(u1, 1.0), 0.0)
    if not L._u_in(u2):
        u2 = max(min(u2, 1.0), 0.0)

    # Tangent
    if u1 == u2:
        return Point2(L.p.x + u1 * L.v.x,
                      L.p.y + u1 * L.v.y)

    return LineSegment2(Point2(L.p.x + u1 * L.v.x,
                               L.p.y + u1 * L.v.y),
                        Point2(L.p.x + u2 * L.v.x,
                               L.p.y + u2 * L.v.y))

def _connect_point2_line2(P, L):
    d = L.v.magnitude_squared()
    assert d != 0
    u = ((P.x - L.p.x) * L.v.x + \
         (P.y - L.p.y) * L.v.y) / d
    if not L._u_in(u):
        u = max(min(u, 1.0), 0.0)
    return LineSegment2(P,
                        Point2(L.p.x + u * L.v.x,
                               L.p.y + u * L.v.y))

def _connect_point2_circle(P, C):
    v = P - C.c
    v.normalize()
    v *= C.r
    return LineSegment2(P, Point2(C.c.x + v.x, C.c.y + v.y))

def _connect_line2_line2(A, B):
    d = B.v.y * A.v.x - B.v.x * A.v.y
    if d == 0:
        # Parallel, connect an endpoint with a line
        if isinstance(B, Ray2) or isinstance(B, LineSegment2):
            p1, p2 = _connect_point2_line2(B.p, A)
            return p2, p1
        # No endpoint (or endpoint is on A), possibly choose arbitrary point
        # on line.
        return _connect_point2_line2(A.p, B)

    dy = A.p.y - B.p.y
    dx = A.p.x - B.p.x
    ua = (B.v.x * dy - B.v.y * dx) / d
    if not A._u_in(ua):
        ua = max(min(ua, 1.0), 0.0)
    ub = (A.v.x * dy - A.v.y * dx) / d
    if not B._u_in(ub):
        ub = max(min(ub, 1.0), 0.0)

    return LineSegment2(Point2(A.p.x + ua * A.v.x, A.p.y + ua * A.v.y),
                        Point2(B.p.x + ub * B.v.x, B.p.y + ub * B.v.y))

def _connect_circle_line2(C, L):
    d = L.v.magnitude_squared()
    assert d != 0
    u = ((C.c.x - L.p.x) * L.v.x + (C.c.y - L.p.y) * L.v.y) / d
    if not L._u_in(u):
        u = max(min(u, 1.0), 0.0)
    point = Point2(L.p.x + u * L.v.x, L.p.y + u * L.v.y)
    v = (point - C.c)
    v.normalize()
    v *= C.r
    return LineSegment2(Point2(C.c.x + v.x, C.c.y + v.y), point)

def _connect_circle_circle(A, B):
    v = B.c - A.c
    v.normalize()
    return LineSegment2(Point2(A.c.x + v.x * A.r, A.c.y + v.y * A.r),
                        Point2(B.c.x - v.x * B.r, B.c.y - v.y * B.r))


class Point2(Vector2, Geometry):
    def __repr__(self):
        return 'Point2(%.2f, %.2f)' % (self.x, self.y)

    def intersect(self, other):
        return other._intersect_point2(self)

    def _intersect_circle(self, other):
        return _intersect_point2_circle(self, other)

    def connect(self, other):
        return other._connect_point2(self)

    def _connect_point2(self, other):
        return LineSegment2(other, self)

    def _connect_line2(self, other):
        c = _connect_point2_line2(self, other)
        if c:
            return c._swap()

    def _connect_circle(self, other):
        c = _connect_point2_circle(self, other)
        if c:
            return c._swap()

class Line2(Geometry):
    __slots__ = ['p', 'v']

    def __init__(self, *args):
        if len(args) == 3:
            assert isinstance(args[0], Point2) and \
                   isinstance(args[1], Vector2) and \
                   type(args[2]) == float
            self.p = args[0].copy()
            self.v = args[1] * args[2] / abs(args[1])
        elif len(args) == 2:
            if isinstance(args[0], Point2) and isinstance(args[1], Point2):
                self.p = args[0].copy()
                self.v = args[1] - args[0]
            elif isinstance(args[0], Point2) and isinstance(args[1], Vector2):
                self.p = args[0].copy()
                self.v = args[1].copy()
            else:
                raise AttributeError, '%r' % (args,)
        elif len(args) == 1:
            if isinstance(args[0], Line2):
                self.p = args[0].p.copy()
                self.v = args[0].v.copy()
            else:
                raise AttributeError, '%r' % (args,)
        else:
            raise AttributeError, '%r' % (args,)

        if not self.v:
            raise AttributeError, 'Line has zero-length vector'

    def __copy__(self):
        return self.__class__(self.p, self.v)

    copy = __copy__

    def __repr__(self):
        return 'Line2(<%.2f, %.2f> + u<%.2f, %.2f>)' % \
            (self.p.x, self.p.y, self.v.x, self.v.y)

    p1 = property(lambda self: self.p)
    p2 = property(lambda self: Point2(self.p.x + self.v.x,
                                      self.p.y + self.v.y))

    def _apply_transform(self, t):
        self.p = t * self.p
        self.v = t * self.v

    def _u_in(self, u):
        return True

    def intersect(self, other):
        return other._intersect_line2(self)

    def _intersect_line2(self, other):
        return _intersect_line2_line2(self, other)

    def _intersect_circle(self, other):
        return _intersect_line2_circle(self, other)

    def connect(self, other):
        return other._connect_line2(self)

    def _connect_point2(self, other):
        return _connect_point2_line2(other, self)

    def _connect_line2(self, other):
        return _connect_line2_line2(other, self)

    def _connect_circle(self, other):
        return _connect_circle_line2(other, self)

class Ray2(Line2):
    def __repr__(self):
        return 'Ray2(<%.2f, %.2f> + u<%.2f, %.2f>)' % \
            (self.p.x, self.p.y, self.v.x, self.v.y)

    def _u_in(self, u):
        return u >= 0.0

class LineSegment2(Line2):
    def __repr__(self):
        return 'LineSegment2(<%.2f, %.2f> to <%.2f, %.2f>)' % \
            (self.p.x, self.p.y, self.p.x + self.v.x, self.p.y + self.v.y)

    def _u_in(self, u):
        return u >= 0.0 and u <= 1.0

    def __abs__(self):
        return abs(self.v)

    def magnitude_squared(self):
        return self.v.magnitude_squared()

    def _swap(self):
        # used by connect methods to switch order of points
        self.p = self.p2
        self.v *= -1
        return self

    length = property(lambda self: abs(self.v))

class Circle(Geometry):
    __slots__ = ['c', 'r']

    def __init__(self, center, radius):
        assert isinstance(center, Vector2) and type(radius) == float
        self.c = center.copy()
        self.r = radius

    def __copy__(self):
        return self.__class__(self.c, self.r)

    copy = __copy__

    def __repr__(self):
        return 'Circle(<%.2f, %.2f>, radius=%.2f)' % \
            (self.c.x, self.c.y, self.r)

    def _apply_transform(self, t):
        self.c = t * self.c

    def intersect(self, other):
        return other._intersect_circle(self)

    def _intersect_point2(self, other):
        return _intersect_point2_circle(other, self)

    def _intersect_line2(self, other):
        return _intersect_line2_circle(other, self)

    def connect(self, other):
        return other._connect_circle(self)

    def _connect_point2(self, other):
        return _connect_point2_circle(other, self)

    def _connect_line2(self, other):
        c = _connect_circle_line2(self, other)
        if c:
            return c._swap()

    def _connect_circle(self, other):
        return _connect_circle_circle(other, self)

########NEW FILE########
__FILENAME__ = proximity
#!/usr/bin/env python
# - coding: utf-8 -
# Copyright (C) 2010 Toms Bauģis <toms.baugis at gmail.com>

"""
 Proximity calculations
"""

from bisect import bisect

class ProximityStore(object):
    def __init__(self):
        self.positions = {}
        self.reverse_positions = {}

    def update_position(position):
        """Update position of the element"""
        pass

    def find_neighbours(location, radius):
        pass


# A AbstractProximityDatabase-style wrapper for the LQ bin lattice system
class LQProximityStore(ProximityStore):
    __slots__ = ['point1', 'point2', 'stride', 'grid_x', 'grid_y']
    def __init__(self, point1, point2, stride):
        ProximityStore.__init__(self)
        self.point1, self.point2, self.stride = point1, point2, stride

        # create the bin grid where we will be throwing in our friends
        self.grid_x = range(point1.x, point2.x, stride)
        self.grid_y = range(point1.y, point2.y, stride)

        self.velocity_weight = 10


    def update_position(self, boid):
        bin = (bisect(self.grid_x, boid.location.x), bisect(self.grid_y, boid.location.y))
        old_bin = self.reverse_positions.setdefault(boid, [])

        #if bin has changed, move
        if old_bin != bin:
            if old_bin:
                self.positions[old_bin].remove(boid)

            self.positions.setdefault(bin, [])
            self.positions[bin].append(boid)
            self.reverse_positions[boid] = bin


    def find_bins(self, boid, radius):
        # TODO, would be neat to operate with vectors here
        # create a bounding box and return all bins within it
        velocity_weight = self.velocity_weight
        min_x = bisect(self.grid_x, min(boid.location.x - radius,
                                        boid.location.x + boid.velocity.x * velocity_weight - radius))
        min_y = bisect(self.grid_y, min(boid.location.y - radius,
                                        boid.location.y + boid.velocity.y * velocity_weight - radius))
        max_x = bisect(self.grid_x, max(boid.location.x + radius,
                                        boid.location.x + boid.velocity.x * velocity_weight + radius))
        max_y = bisect(self.grid_y, max(boid.location.y + radius,
                                        boid.location.y + boid.velocity.y * velocity_weight + radius))

        bins = []
        for x in range(min_x, max_x + 1):
            for y in range(min_y, max_y + 1):
                bins.append(self.positions.setdefault((x,y), []))
        return bins


    def find_neighbours(self, boid, radius):
        bins = self.find_bins(boid, radius)

        neighbours = []

        for bin in bins:
            for boid2 in bin:
                if boid is boid2:
                    continue

                dx = boid.location.x - boid2.location.x
                dy = boid.location.y - boid2.location.y
                d = dx * dx + dy * dy
                if d < radius * radius:
                    neighbours.append((boid2, d))

        return neighbours

########NEW FILE########
__FILENAME__ = convex_hull
#!/usr/bin/env python
# - coding: utf-8 -
# Copyright (C) 2010 Toms Bauģis <toms.baugis at gmail.com>

"""
 Games with points, implemented following Dr. Mike's Maths
 http://www.dr-mikes-maths.com/

 Also this is an example how to handle mouse
"""

from gi.repository import Gtk as gtk
from lib import graphics

import math
from contrib.euclid import Point2

class Node(graphics.Rectangle):
    def __init__(self, x, y):
        graphics.Rectangle.__init__(self, 10, 10, x=x, y=y,
                                    fill = "#999",
                                    corner_radius = 3,
                                    pivot_x = 5, pivot_y = 5,
                                    interactive=True,
                                    draggable = True)

        # TODO - remember how the drag model has changed and fix the math
        #self.connect("on-drag-start", self.on_drag_start)
        #self.connect("on-drag-finish", self.on_drag_finish)

    def on_drag_start(self, sprite, event):
        self.animate(width=50, height=50,
                     pivot_x = 25, pivot_y = 25,
                     drag_x = sprite.x - 25, drag_y = sprite.y - 25)

    def on_drag_finish(self, sprite, event):
        self.animate(width=10, height=10, pivot_x = 5, pivot_y = 5)

class Canvas(graphics.Scene):
    def __init__(self):
        graphics.Scene.__init__(self)
        self.nodes = []
        self.connect("on-click", self.on_mouse_click)
        self.connect("on-enter-frame", self.on_enter_frame)

    def on_mouse_click(self, area, event, target):
        if not target:
            node = Node(event.x, event.y)

            self.nodes.append(node)
            self.add_child(node)
        else:
            target.fill = "#f00"

    def on_enter_frame(self, scene, context):
        g = graphics.Graphics(context)
        g.set_color("#999")

        for node, node2 in self.convex_hull():
            g.move_to(node.x + node.pivot_x, node.y + node.pivot_y)
            g.line_to(node2.x + node2.pivot_x, node2.y + node2.pivot_y)

            node.rotation += 0.01

        g.stroke()
        self.redraw()




    def convex_hull(self):
        """self brewn lame algorithm to find hull, following dr mike's math.
           Basically we find the topmost edge and from there go looking
           for line that would form the smallest angle
        """

        if len(self.nodes) < 2: return []

        # grab the topmost node (the one with the least y)
        topmost = sorted(self.nodes, key=lambda node:node.y)[0]

        segments = []
        # initially the current line is looking upwards
        current_line = Point2(topmost.x, topmost.y) - Point2(topmost.x, topmost.y - 1)
        current_node = topmost
        smallest = None

        node_list = list(self.nodes)

        while current_node and smallest != topmost:
            # calculate angles between current line
            angles = [(node, current_line.angle(current_node - Point2(node.x, node.y))) for node in node_list if node != current_node]

            if angles:
                smallest = sorted(angles, key = lambda x: x[1])[0][0]
                segments.append((current_node, smallest)) # add to the results

                # now we will be looking for next connection
                current_line = Point2(current_node.x, current_node.y) - Point2(smallest.x, smallest.y)
                current_node = smallest
                node_list.remove(smallest) # tiny optimization
            else:
                current_node = None


        return segments




class BasicWindow:
    def __init__(self):
        window = gtk.Window()
        window.set_size_request(600, 500)
        window.connect("delete_event", lambda *args: gtk.main_quit())

        self.canvas = Canvas()

        box = gtk.VBox()
        box.add(self.canvas)

        button = gtk.Button("Redo")
        def on_click(*args):
            self.canvas.nodes = []
            self.canvas.clear()
            self.canvas.redraw()

        button.connect("clicked", on_click)
        box.pack_start(button, False, False, 0)



        window.add(box)
        window.show_all()


if __name__ == "__main__":
    example = BasicWindow()
    import signal
    signal.signal(signal.SIGINT, signal.SIG_DFL) # gtk3 screws up ctrl+c
    gtk.main()

########NEW FILE########
__FILENAME__ = delaunay
#!/usr/bin/env python
# - coding: utf-8 -
# Copyright (C) 2010 Toms Bauģis <toms.baugis at gmail.com>

"""
 Games with points, implemented following Dr. Mike's Maths
 http://www.dr-mikes-maths.com/
"""


from gi.repository import Gtk as gtk
from lib import graphics

import math
from contrib.euclid import Vector2
import itertools


EPSILON = 0.00001

class Node(graphics.Sprite):
    def __init__(self, x, y):
        graphics.Sprite.__init__(self, x=x, y=y, interactive=True, draggable=True)
        self.graphics.rectangle(-5, -5, 10, 10, 3)
        self.graphics.fill("#999")

class Canvas(graphics.Scene):
    def __init__(self):
        graphics.Scene.__init__(self)
        self.nodes = []
        self.centres = []
        self.segments = []

        self.connect("on-enter-frame", self.on_enter_frame)
        self.connect("on-click", self.on_mouse_click)
        self.connect("on-drag", self.on_node_drag)

        self.draw_circles = False

    def on_mouse_click(self, area, event, target):
        if not target:
            node = Node(event.x, event.y)
            self.nodes.append(node)
            self.add_child(node)
            self.centres = []

            self.redraw()


    def on_node_drag(self, scene, node, event):
        self.centres = []
        self.redraw()


    def on_enter_frame(self, scene, context):
        c_graphics = graphics.Graphics(context)
        c_graphics.set_line_style(width = 0.5)

        if not self.centres:  #reset when adding nodes
            self.centres, self.segments = self.delauney()

        c_graphics.set_color("#666")
        for node, node2 in self.segments:
            context.move_to(node.x, node.y)
            context.line_to(node2.x, node2.y)
        context.stroke()

        if self.draw_circles:
            for node, radius in self.centres:
                c_graphics.set_color("#f00", 0.3)
                context.arc(node[0], node[1], radius, 0, 2.0 * math.pi)
                context.fill_preserve()
                context.stroke()

                c_graphics.set_color("#a00")
                context.rectangle(node[0]-1, node[1]-1, 2, 2)
                context.stroke()



    def triangle_circumcenter(self, a, b, c):
        """shockingly, the circumcenter math has been taken from wikipedia
           we move the triangle to 0,0 coordinates to simplify math"""

        p_a = Vector2(a.x, a.y)
        p_b = Vector2(b.x, b.y) - p_a
        p_c = Vector2(c.x, c.y) - p_a

        p_b2 = p_b.magnitude_squared()
        p_c2 = p_c.magnitude_squared()

        d = 2 * (p_b.x * p_c.y - p_b.y * p_c.x)

        if d < 0:
            d = min(d, EPSILON)
        else:
            d = max(d, EPSILON)


        centre_x = (p_c.y * p_b2 - p_b.y * p_c2) / d
        centre_y = (p_b.x * p_c2 - p_c.x * p_b2) / d

        centre = p_a + Vector2(centre_x, centre_y)
        return centre


    def delauney(self):
        segments = []
        centres = []
        combos = list(itertools.combinations(self.nodes, 3))
        print "combinations: ", len(combos)
        for a, b, c in combos:
            centre = self.triangle_circumcenter(a, b, c)

            distance2 = (Vector2(a.x, a.y) - centre).magnitude_squared()

            smaller_found = False
            for node in self.nodes:
                if node in [a,b,c]:
                    continue

                if (Vector2(node.x, node.y) - centre).magnitude_squared() < distance2:
                    smaller_found = True
                    break

            if not smaller_found:
                segments.extend(list(itertools.combinations([a,b,c], 2)))

                if 0 < centre.x < self.width and 0 < centre.y < self.height:
                    centres.append((centre, math.sqrt(distance2)))

        for segment in segments:
            order = sorted(segment, key = lambda node: node.x+node.y)
            segment = (order[0], order[1])

        segments = set(segments)

        return set(centres), segments



class BasicWindow:
    def __init__(self):
        window = gtk.Window()
        window.set_size_request(600, 500)
        window.connect("delete_event", lambda *args: gtk.main_quit())


        vbox = gtk.VBox()
        window.add(vbox)

        box = gtk.HBox()
        box.set_border_width(10)
        box.add(gtk.Label("Add some points and observe Delauney triangulation"))
        vbox.pack_start(box, False, False, 0)

        self.canvas = Canvas()
        vbox.add(self.canvas)

        box = gtk.HBox(False, 4)
        box.set_border_width(10)

        vbox.pack_start(box, False, False, 0)

        button = gtk.Button("Generate points in centers")
        def on_click(*args):
            for centre, radius in self.canvas.centres:
                if abs(centre) < 2000:
                    node = Node(*centre)
                    self.canvas.nodes.append(node)
                    self.canvas.add_child(node)
            self.canvas.centres = []
            self.canvas.redraw()

        button.connect("clicked", on_click)
        box.pack_end(button, False, False, 0)

        button = gtk.Button("Clear")
        def on_click(*args):
            self.canvas.nodes = []
            self.canvas.mouse_node, self.canvas.prev_mouse_node = None, None
            self.canvas.centres = []
            self.canvas.clear()
            self.canvas.redraw()

        button.connect("clicked", on_click)
        box.pack_end(button, False, False, 0)

        button = gtk.CheckButton("show circumcenter")
        def on_click(button):
            self.canvas.draw_circles = button.get_active()
            self.canvas.redraw()

        button.connect("clicked", on_click)
        box.pack_start(button, False, False, 0)


        window.show_all()


if __name__ == "__main__":
    example = BasicWindow()
    import signal
    signal.signal(signal.SIGINT, signal.SIG_DFL) # gtk3 screws up ctrl+c
    gtk.main()

########NEW FILE########
__FILENAME__ = delaunay2
#!/usr/bin/env python
# - coding: utf-8 -
# Copyright (C) 2010 Toms Bauģis <toms.baugis at gmail.com>

"""
 This one is based on code by Geoff Leach <gl@cs.rmit.edu.au> (29/3/96)
 Same delaunay triangulation, just much more efficient.
 See here for original source and description:
 http://goanna.cs.rmit.edu.au/~gl/research/comp_geom/delaunay/delaunay.html
"""


from gi.repository import Gtk as gtk
from lib import graphics
from contrib.euclid import Point2, Vector2

import math
import itertools
import collections

EPSILON = 0.00001

class Node(graphics.Sprite):
    def __init__(self, x, y, point):
        graphics.Sprite.__init__(self, x, y, interactive=True, draggable=True)

        self.draw_node()
        self.point = point
        self.connect("on-drag", self.on_drag)

    def on_drag(self, sprite, event):
        self.point.x = event.x
        self.point.y = event.y
        self.draw_node()

    def draw_node(self):
        self.graphics.clear()
        self.graphics.set_color("#999")
        self.graphics.rectangle(-5,-5, 10, 10, 3)
        self.graphics.fill()


class Edge(object):
    def __init__(self, point1, point2):
        self.point1 = point1
        self.point2 = point2
        self.left_face = None
        self.right_face = None

    def update_left_face(self, point1, point2, face):
        if set((self.point1, self.point2)) - set((point1, point2)):
            return # have been asked to update, but these are not our points

        if point1 == self.point1 and self.left_face is None:
            self.left_face = face
        elif point1 == self.point2 and self.right_face is None:
            self.right_face = face




class Circle(Point2):
    def __init__(self, x = 0, y = 0, radius = 0):
        Point2.__init__(self, x, y)
        self.radius = radius

    def covers(self, point):
        return (self - point).magnitude_squared() < self.radius * self.radius


    def circumcircle(self, p1, p2, p3):
        v1 = p2 - p1
        v2 = p3 - p1

        cross = (p2 - p1).product(p3 - p1)

        if cross != 0:
            p1_sq = p1.magnitude_squared()
            p2_sq = p2.magnitude_squared()
            p3_sq = p3.magnitude_squared()

            num = p1_sq * (p2.y - p3.y) + p2_sq * (p3.y - p1.y) + p3_sq * (p1.y - p2.y)
            cx = num / (2.0 * cross)

            num = p1_sq * (p3.x - p2.x) + p2_sq * (p1.x - p3.x) + p3_sq * (p2.x - p1.x)
            cy = num / (2.0 * cross);

            self.x, self.y = cx, cy

        self.radius = (self - p1).magnitude()

        return self


class Canvas(graphics.Scene):
    def __init__(self):
        graphics.Scene.__init__(self)
        self.nodes = []
        self.centres = []

        self.edges = []

        self.edge_dict = {}

        self.points = [] # [Vector2(-10000, -10000), Vector2(10000, -10000), Vector2(0, 10000)]



        self.connect("on-enter-frame", self.on_enter_frame)
        self.connect("on-click", self.on_mouse_click)
        self.connect("on-drag", self.on_node_drag)


        self.add_child(graphics.Label("Add some points and observe Delaunay triangulation", x = 5, y = 5, color = "#666"))

        self.draw_circles = False


    def add_edge(self, p1, p2):
        exists = self.edge_dict.get((p1, p2), self.edge_dict.get((p2, p1)))
        if not exists:
            edge = Edge(p1, p2)

            self.edges.append(edge)
            self.edge_dict[(p1, p2)] = edge
            return edge, True
        else:
            return exists, False


    def find_triangles(self):
        # run through edges and detect triangles
        for edge in self.edges:
            pass

    def triangulate(self):
        self.edges = []
        self.edge_dict = {}
        self.centres = []

        # find closest neighbours for the seed
        neighbours = None
        min_distance = None

        for p1 in self.points:
            for p2 in self.points:
                if p1 == p2: continue

                d = (p1 - p2).magnitude_squared()
                if not min_distance or d < min_distance:
                    neighbours = p1, p2
                    min_distance = d

        if not neighbours:
            return

        seed, new = self.add_edge(*neighbours)


        edges = collections.deque([seed])
        self.face_num = 0
        while edges:
            current = edges.popleft()

            if not current.left_face:
                edges.extend(self.check_edge(current, current.point1, current.point2))

            if not current.right_face:
                edges.extend(self.check_edge(current, current.point2, current.point1))


    def check_edge(self, edge, point1, point2):
        """
         * Complete a facet by looking for the circle free point to the left
         * of the edge.  Add the facet to the triangulation.
        """

        positive_products = (point for point in self.points if point not in (point1, point2) \
                                                           and (point2 - point1).product(point - point1) > 0)

        # Find a point on left of edge.
        try:
            left_point = positive_products.next()
            left_point_circumcentre = Circle()
            left_point_circumcentre.circumcircle(point1, point2, left_point)
        except StopIteration:
            edge.update_left_face(point1, point2, 0)
            return [] #did not find anything

        # now from all the left side points find the one that is circle-free
        for point in positive_products:
            if left_point_circumcentre.covers(point):
                # move centre
                left_point_circumcentre.circumcircle(point1, point2, point)
                left_point = point

        # now that we are done, add our successful candidate to the centres
        if left_point_circumcentre not in self.centres:
            self.centres.append(left_point_circumcentre)
            self.face_num +=1


        # Add new triangle or update edge info if s-t is on hull.
        # Update face information of edge being completed.
        edge.update_left_face(point1, point2, self.face_num)

        # connect the dots
        res = []

        edge1, new = self.add_edge(left_point, point1)
        edge1.update_left_face(left_point, point1, self.face_num)
        if new: res.append(edge1)


        edge2, new = self.add_edge(point2, left_point)
        edge2.update_left_face(point2, left_point, self.face_num)
        if new: res.append(edge2)


        return res


    def on_mouse_click(self, area, event, target):
        if not target:
            point = Vector2(event.x, event.y)
            self.points.append(point)

            node = Node(event.x, event.y, point)
            self.nodes.append(node)
            self.add_child(node)
            self.centres = []

            self.triangulate()

            self.redraw()

    def on_node_drag(self, scene, node, event):
        self.centres = []
        self.redraw()


    def on_enter_frame(self, scene, context):
        g = graphics.Graphics(context)
        g.set_line_style(width = 0.5)

        self.triangulate()

        g.set_color("#666")
        for edge in self.edges:
            context.move_to(edge.point1.x, edge.point1.y)
            context.line_to(edge.point2.x, edge.point2.y)

            context.save()
            context.translate((edge.point1.x + edge.point2.x) / 2, (edge.point1.y + edge.point2.y) / 2)
            context.save()
            context.rotate((edge.point2 - edge.point1).heading())
            context.move_to(-5, 0)
            g.show_label(str(edge.left_face))
            context.restore()

            context.save()
            context.rotate((edge.point1 - edge.point2).heading())
            context.move_to(-5, 0)
            g.show_label(str(edge.right_face))
            context.restore()

            context.restore()

        context.stroke()

        if self.draw_circles:
            for centre in self.centres:
                g.set_color("#f00", 0.1)
                context.arc(centre.x, centre.y, centre.radius, 0, 2.0 * math.pi)
                context.fill_preserve()
                context.stroke()

                g.set_color("#a00")
                context.rectangle(centre.x-1, centre.y-1, 2, 2)
                context.stroke()



class BasicWindow:
    def __init__(self):
        window = gtk.Window()
        window.set_default_size(600, 500)
        window.connect("delete_event", lambda *args: gtk.main_quit())


        vbox = gtk.VBox()
        window.add(vbox)

        box = gtk.HBox()
        vbox.pack_start(box, False, False, 0)

        self.canvas = Canvas()
        vbox.add(self.canvas)

        box = gtk.HBox(False, 4)

        vbox.pack_start(box, False, False, 0)

        button = gtk.Button("Generate points in centers")
        def on_click(*args):
            for centre in self.canvas.centres:
                if abs(centre) < 2000:
                    point = Vector2(centre.x, centre.y)
                    self.canvas.points.append(point)
                    node = Node(point.x, point.y, point)
                    self.canvas.nodes.append(node)
                    self.canvas.add_child(node)
            self.canvas.centres = []
            self.canvas.redraw()


        button.connect("clicked", on_click)
        box.pack_end(button, False, False, 0)

        button = gtk.Button("Clear")
        def on_click(*args):
            self.canvas.points = []
            self.canvas.clear()
            self.canvas.redraw()

        button.connect("clicked", on_click)
        box.pack_end(button, False, False, 0)




        button = gtk.CheckButton("show circumcenter")
        def on_click(button):
            self.canvas.draw_circles = button.get_active()
            self.canvas.redraw()

        button.connect("clicked", on_click)
        box.pack_start(button, False, False, 0)


        window.show_all()


if __name__ == "__main__":
    example = BasicWindow()
    import signal
    signal.signal(signal.SIGINT, signal.SIG_DFL) # gtk3 screws up ctrl+c
    gtk.main()

########NEW FILE########
__FILENAME__ = delayed_chains
#!/usr/bin/env python
# - coding: utf-8 -
# Copyright (C) 2014 Toms Bauģis <toms.baugis at gmail.com>

"""
    The delayed chains makes an animation where each next sprite animates a
    fraction later.
    Play with get_delay and get_duration functions to get very different effects.
"""

import math

from gi.repository import Gtk as gtk
from lib import graphics
from lib.pytweener import Easing

class FiddlyBit(graphics.Sprite):
    def __init__(self, **kwargs):
        graphics.Sprite.__init__(self, **kwargs)
        self.connect("on-render", self.on_render)

    def on_render(self, sprite):
        self.graphics.set_line_style(width=1)
        self.graphics.move_to(0.5, -150)
        self.graphics.line_to(0.5, 150)
        self.graphics.stroke("#999")




class Scene(graphics.Scene):
    def __init__(self):
        graphics.Scene.__init__(self)
        self.fiddly_bits = []
        self.fiddly_bits_container = graphics.Sprite(interactive=True)
        self.add_child(self.fiddly_bits_container)

        self.current_angle, self.current_reverse = math.pi, True

        self.fiddly_bits_container.connect("on-mouse-over", self.on_fiddly_over)
        self.fiddly_bits_container.connect("on-mouse-out", self.on_fiddly_out)
        self.fiddly_bits_container.connect("on-mouse-move", self.on_fiddly_mouse_move)

        self.connect("on-resize", self.on_resize)
        self.connect("on-enter-frame", self.on_enter_frame)

    def on_fiddly_over(self, sprite):
        self.stop_animation(self.fiddly_bits)

    def on_fiddly_out(self, sprite):
        self.roll(self.current_angle, self.current_reverse)

    def on_fiddly_mouse_move(self, sprite, event):
        width = self.width
        def normalized(x):
            return (x - 50) * 1.0 / 600

        # find position in range 0..1
        pos = normalized(event.x)
        for bit in self.fiddly_bits:
            bit_pos = normalized(bit.x)
            bit.rotation = (bit_pos - pos - 0.5) * math.pi

    def on_resize(self, scene, event):
        self.stop_animation(self.fiddly_bits)
        self.populate_fiddlybits()
        self.current_angle = math.pi
        self.roll(self.current_angle, self.current_reverse)

    def populate_fiddlybits(self):
        self.fiddly_bits_container.clear()

        width = self.width
        self.fiddly_bits = [FiddlyBit() for i in range(width / 10)]

        step = (width - 100) *1.0 / len(self.fiddly_bits)



        x, y = 50, self.height / 2
        self.fiddly_bits_container.graphics.fill_area(0, y-150, width, 300, "#000", 0)


        delay = 0
        for i, bit in enumerate(self.fiddly_bits):
            self.fiddly_bits_container.add_child(bit)
            bit.x, bit.y, bit.rotation = int(x), y, 0
            x += step

    def get_duration(self, i, elems):
        # 1..0 - duration shrinks as we go towards the end
        return 2 + 2.0 * (1 - i * 1.0 / elems)

    def get_delay(self, i, elems):
        # 0..1 - delay grows as we go towards the end
        return 3.0 * i * 1.0 / elems

    def roll(self, angle, reverse=True):
        self.current_angle, self.current_reverse = angle, reverse

        delay = 0
        bits = self.fiddly_bits
        if reverse:
            bits = reversed(bits)

        for i, bit in enumerate(bits):
            on_complete = None
            if i == len(self.fiddly_bits) - 1:
                next_angle = math.pi - angle
                next_reverse = next_angle == math.pi
                on_complete = lambda sprite: sprite.get_scene().roll(next_angle, next_reverse)

            delay = self.get_delay(i, len(self.fiddly_bits))
            duration = self.get_duration(i, len(self.fiddly_bits))

            bit.animate(rotation=angle,
                        duration=duration,
                        delay=delay,
                        easing=Easing.Sine.ease_in_out,
                        on_complete=on_complete)


    def on_enter_frame(self, scene, context):
        if not self.fiddly_bits:
            self.populate_fiddlybits()
            self.roll(self.current_angle, self.current_reverse)


class BasicWindow:
    def __init__(self):
        window = gtk.Window()
        window.set_default_size(600, 500)
        window.connect("delete_event", lambda *args: gtk.main_quit())
        window.add(Scene())
        window.show_all()

if __name__ == '__main__':
    window = BasicWindow()
    import signal
    signal.signal(signal.SIGINT, signal.SIG_DFL) # gtk3 screws up ctrl+c
    gtk.main()

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# hamster graphics documentation build configuration file, created by
# sphinx-quickstart on Fri Feb 19 17:39:37 2010.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys, os

sys.path.append(os.path.abspath(os.path.join('..', 'lib')))
sys.path.append(os.path.abspath(os.path.join('..')))

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#sys.path.append(os.path.abspath('.'))

# -- General configuration -----------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc']

# Add any paths that contain templates here, relative to this directory.
#templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'hamster graphics'
copyright = u'2010-2012, Toms Bauģis'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '0.1'
# The full version, including alpha/beta/rc tags.
release = '0.1'

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of documents that shouldn't be included in the build.
#unused_docs = []

# List of directories, relative to source directory, that shouldn't be searched
# for source files.
exclude_trees = ['_build']

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

# The theme to use for HTML and HTML Help pages.  Major themes that come with
# Sphinx are currently 'default' and 'sphinxdoc'.
html_theme = 'default'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.
#html_theme_path = []

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
#html_title = None

# A shorter title for the navigation bar.  Default is the same as html_title.
#html_short_title = None

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
#html_static_path = ['_static']

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
html_use_modindex = False

# If false, no index is generated.
html_use_index = False

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
#html_show_sourcelink = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# If nonempty, this is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = ''

# Output file base name for HTML help builder.
htmlhelp_basename = 'hamstergraphicsdoc'


# -- Options for LaTeX output --------------------------------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'hamstergraphics.tex', u'hamster graphics Documentation',
   u'Toms Bauģis', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# Additional stuff for the LaTeX preamble.
#latex_preamble = ''

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_use_modindex = True

########NEW FILE########
__FILENAME__ = sphinxtogithub
#! /usr/bin/env python
 
from optparse import OptionParser
import os
import sys
import shutil


class NoDirectoriesError(Exception):
    "Error thrown when no directories starting with an underscore are found"

class DirHelper(object):

    def __init__(self, is_dir, list_dir, walk, rmtree):

        self.is_dir = is_dir
        self.list_dir = list_dir
        self.walk = walk
        self.rmtree = rmtree

class FileSystemHelper(object):

    def __init__(self, open_, path_join, move, exists):

        self.open_ = open_
        self.path_join = path_join
        self.move = move
        self.exists = exists

class Replacer(object):
    "Encapsulates a simple text replace"

    def __init__(self, from_, to):

        self.from_ = from_
        self.to = to

    def process(self, text):

        return text.replace( self.from_, self.to )

class FileHandler(object):
    "Applies a series of replacements the contents of a file inplace"

    def __init__(self, name, replacers, opener):

        self.name = name
        self.replacers = replacers
        self.opener = opener

    def process(self):

        text = self.opener(self.name).read()

        for replacer in self.replacers:
            text = replacer.process( text )

        self.opener(self.name, "w").write(text)

class Remover(object):

    def __init__(self, exists, remove):
        self.exists = exists
        self.remove = remove

    def __call__(self, name):

        if self.exists(name):
            self.remove(name)

class ForceRename(object):

    def __init__(self, renamer, remove):

        self.renamer = renamer
        self.remove = remove

    def __call__(self, from_, to):

        self.remove(to)
        self.renamer(from_, to)

class VerboseRename(object):

    def __init__(self, renamer, stream):

        self.renamer = renamer
        self.stream = stream

    def __call__(self, from_, to):

        self.stream.write(
                "Renaming directory '%s' -> '%s'\n"
                    % (os.path.basename(from_), os.path.basename(to))
                )

        self.renamer(from_, to)


class DirectoryHandler(object):
    "Encapsulates renaming a directory by removing its first character"

    def __init__(self, name, root, renamer):

        self.name = name
        self.new_name = name[1:]
        self.root = root + os.sep
        self.renamer = renamer

    def path(self):
        
        return os.path.join(self.root, self.name)

    def relative_path(self, directory, filename):

        path = directory.replace(self.root, "", 1)
        return os.path.join(path, filename)

    def new_relative_path(self, directory, filename):

        path = self.relative_path(directory, filename)
        return path.replace(self.name, self.new_name, 1)

    def process(self):

        from_ = os.path.join(self.root, self.name)
        to = os.path.join(self.root, self.new_name)
        self.renamer(from_, to)


class HandlerFactory(object):

    def create_file_handler(self, name, replacers, opener):

        return FileHandler(name, replacers, opener)

    def create_dir_handler(self, name, root, renamer):

        return DirectoryHandler(name, root, renamer)


class OperationsFactory(object):

    def create_force_rename(self, renamer, remover):

        return ForceRename(renamer, remover)

    def create_verbose_rename(self, renamer, stream):

        return VerboseRename(renamer, stream)

    def create_replacer(self, from_, to):

        return Replacer(from_, to)

    def create_remover(self, exists, remove):

        return Remover(exists, remove)


class Layout(object):
    """
    Applies a set of operations which result in the layout
    of a directory changing
    """

    def __init__(self, directory_handlers, file_handlers):

        self.directory_handlers = directory_handlers
        self.file_handlers = file_handlers

    def process(self):

        for handler in self.file_handlers:
            handler.process()

        for handler in self.directory_handlers:
            handler.process()


class LayoutFactory(object):
    "Creates a layout object"

    def __init__(self, operations_factory, handler_factory, file_helper, dir_helper, verbose, stream, force):

        self.operations_factory = operations_factory
        self.handler_factory = handler_factory

        self.file_helper = file_helper
        self.dir_helper = dir_helper

        self.verbose = verbose
        self.output_stream = stream
        self.force = force

    def create_layout(self, path):

        contents = self.dir_helper.list_dir(path)

        renamer = self.file_helper.move

        if self.force:
            remove = self.operations_factory.create_remover(self.file_helper.exists, self.dir_helper.rmtree)
            renamer = self.operations_factory.create_force_rename(renamer, remove) 

        if self.verbose:
            renamer = self.operations_factory.create_verbose_rename(renamer, self.output_stream) 

        # Build list of directories to process
        directories = [d for d in contents if self.is_underscore_dir(path, d)]
        underscore_directories = [
                self.handler_factory.create_dir_handler(d, path, renamer)
                    for d in directories
                ]

        if not underscore_directories:
            raise NoDirectoriesError()

        # Build list of files that are in those directories
        replacers = []
        for handler in underscore_directories:
            for directory, dirs, files in self.dir_helper.walk(handler.path()):
                for f in files:
                    replacers.append(
                            self.operations_factory.create_replacer(
                                handler.relative_path(directory, f),
                                handler.new_relative_path(directory, f)
                                )
                            )

        # Build list of handlers to process all files
        filelist = []
        for root, dirs, files in self.dir_helper.walk(path):
            for f in files:
                if f.endswith(".html"):
                    filelist.append(
                            self.handler_factory.create_file_handler(
                                self.file_helper.path_join(root, f),
                                replacers,
                                self.file_helper.open_)
                            )
                if f.endswith(".js"):
                    filelist.append(
                            self.handler_factory.create_file_handler(
                                self.file_helper.path_join(root, f),
                                [self.operations_factory.create_replacer("'_sources/'", "'sources/'")],
                                self.file_helper.open_
                                )
                            )

        return Layout(underscore_directories, filelist)

    def is_underscore_dir(self, path, directory):

        return (self.dir_helper.is_dir(self.file_helper.path_join(path, directory))
            and directory.startswith("_"))



def sphinx_extension(app, exception):
    "Wrapped up as a Sphinx Extension"

    # This code is sadly untestable in its current state
    # It would be helped if there was some function for loading extension
    # specific data on to the app object and the app object providing 
    # a file-like object for writing to standard out.
    # The former is doable, but not officially supported (as far as I know)
    # so I wouldn't know where to stash the data. 

    if app.builder.name != "html":
        return

    if not app.config.sphinx_to_github:
        if app.config.sphinx_to_github_verbose:
            print "Sphinx-to-github: Disabled, doing nothing."
        return

    if exception:
        if app.config.sphinx_to_github_verbose:
            print "Sphinx-to-github: Exception raised in main build, doing nothing."
        return

    dir_helper = DirHelper(
            os.path.isdir,
            os.listdir,
            os.walk,
            shutil.rmtree
            )

    file_helper = FileSystemHelper(
            open,
            os.path.join,
            shutil.move,
            os.path.exists
            )
    
    operations_factory = OperationsFactory()
    handler_factory = HandlerFactory()

    layout_factory = LayoutFactory(
            operations_factory,
            handler_factory,
            file_helper,
            dir_helper,
            app.config.sphinx_to_github_verbose,
            sys.stdout,
            force=True
            )

    layout = layout_factory.create_layout(app.outdir)
    layout.process()


def setup(app):
    "Setup function for Sphinx Extension"

    app.add_config_value("sphinx_to_github", True, '')
    app.add_config_value("sphinx_to_github_verbose", True, '')

    app.connect("build-finished", sphinx_extension)


def main(args):

    usage = "usage: %prog [options] <html directory>"
    parser = OptionParser(usage=usage)
    parser.add_option("-v","--verbose", action="store_true",
            dest="verbose", default=False, help="Provides verbose output")
    opts, args = parser.parse_args(args)

    try:
        path = args[0]
    except IndexError:
        sys.stderr.write(
                "Error - Expecting path to html directory:"
                "sphinx-to-github <path>\n"
                )
        return

    dir_helper = DirHelper(
            os.path.isdir,
            os.listdir,
            os.walk,
            shutil.rmtree
            )

    file_helper = FileSystemHelper(
            open,
            os.path.join,
            shutil.move,
            os.path.exists
            )
    
    operations_factory = OperationsFactory()
    handler_factory = HandlerFactory()

    layout_factory = LayoutFactory(
            operations_factory,
            handler_factory,
            file_helper,
            dir_helper,
            opts.verbose,
            sys.stdout,
            force=False
            )

    try:
        layout = layout_factory.create_layout(path)
    except NoDirectoriesError:
        sys.stderr.write(
                "Error - No top level directories starting with an underscore "
                "were found in '%s'\n" % path
                )
        return

    layout.process()
    


if __name__ == "__main__":
    main(sys.argv[1:])




########NEW FILE########
__FILENAME__ = drop_shadow
#!/usr/bin/env python
# - coding: utf-8 -
# Copyright (C) 2010 Toms Bauģis <toms.baugis at gmail.com>

"""Base template"""


from gi.repository import Gtk as gtk
from lib import graphics
import cairo
import struct

class DropShadow(graphics.Sprite):
    def __init__(self, sprite):
        graphics.Sprite.__init__(self)
        self.original_sprite = sprite
        self.us = False
        #self.original_sprite.connect("on-render", self.on_prev_sprite_render)


    def render(self):
        if self.us:
            return

        if self.original_sprite.graphics.extents:
            x, y, x2, y2 = self.original_sprite.graphics.extents
            print x, y, x2, y2


        self.us = True

        # first we will measure extents (lame)
        image_surface = cairo.ImageSurface(cairo.FORMAT_A1, 0, 0)
        image_context = cairo.Context(image_surface)
        self.original_sprite._draw(image_context)

        extents = self.original_sprite.get_extents()
        width  = int(extents.width) + 10
        height = int(extents.height) + 10


        # creating a in-memory image of current context
        image_surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
        image_context = cairo.Context(image_surface)


        self.original_sprite._draw(image_context)

        self.us = False

        # now create shadow
        self.blur(image_surface)

        self.graphics.clear()
        self.graphics.set_source_surface(image_surface)
        self.graphics.paint()



    def blur(self, surface):
        buffer = surface.get_data()

        v = 1.0 / 9.0
        kernel = ((v, v, v),
                  (v, v, v),
                  (v, v, v))

        kernel_range = range(-1, 2) # surrounding the pixel


        extents = self.original_sprite.get_extents()
        width  = int(extents.width) + 10
        height = int(extents.height) + 10



        # we will need all the pixel colors anyway, so let's grab them once
        pixel_colors = struct.unpack_from('BBBB' * width * height, buffer)

        new_pixels = [0] * width * height * 4 # target matrix

        for x in range(1, width - 1):
            for y in range(1, height - 1):
                r,g,b,a = 0,0,0,0
                pos = (y * width + x) * 4

                for ky in kernel_range:
                    for kx in kernel_range:
                        k = kernel[kx][ky]
                        k_pos = pos + ky * width * 4 + kx * 4

                        pixel_r,pixel_g,pixel_b,pixel_a = pixel_colors[k_pos:k_pos + 4]

                        r += k * pixel_r
                        g += k * pixel_g
                        b += k * pixel_b
                        a += k * pixel_a

                avg = min((r + g + b) / 3.0 * 0.6, 255)
                new_pixels[pos:pos+4] = (avg, avg, avg, a)

        struct.pack_into('BBBB' * width * height, buffer, 0, *new_pixels)

class SomeShape(graphics.Sprite):
    def __init__(self):
        graphics.Sprite.__init__(self, interactive=True, draggable=True)

        #self.graphics.circle(25, 25, 15)
        label = graphics.Label("", 24, "#fff")
        label.markup = "<b>Drag me around!</b>"
        self.add_child(label)

        self.graphics.rectangle(0, 0, label.width, label.height)
        self.graphics.new_path()

        #self.graphics.fill_area(5, 5, 80, 80, "#fff")

        self.connect("on-render", self.on_render)

    def on_render(self, sprite):
        self.shadow.render()

class Scene(graphics.Scene):
    def __init__(self):
        graphics.Scene.__init__(self)

        self.shape = SomeShape()

        shadow = DropShadow(self.shape)
        shadow.x, shadow.y = -4, -4

        self.shape.shadow = shadow

        self.add_child(shadow)
        self.add_child(self.shape)

        self.connect("on-drag", self.on_sprite_drag)
        #self.animate(self.shape, opacity=1, duration=1.0)
        self.redraw()

    def on_sprite_drag(self, scene, sprite, event):
        extents = sprite.get_extents()
        width, height = extents.width, extents.height

        sprite.shadow.x = sprite.x + (sprite.x + (width - self.width) / 2.0) / float(self.width) * 8
        sprite.shadow.y = sprite.y + (sprite.y + (height - self.height) / 2.0) / float(self.height) * 8



class BasicWindow:
    def __init__(self):
        window = gtk.Window()
        window.set_size_request(600, 500)
        window.connect("delete_event", lambda *args: gtk.main_quit())
        window.add(Scene())
        window.show_all()

example = BasicWindow()
import signal
signal.signal(signal.SIGINT, signal.SIG_DFL) # gtk3 screws up ctrl+c
gtk.main()

########NEW FILE########
__FILENAME__ = easing_demo
#!/usr/bin/env python
# - coding: utf-8 -
# Copyright (C) 2010 Toms Bauģis <toms.baugis at gmail.com>

import colorsys

from gi.repository import Gtk as gtk
from lib import graphics
from lib.pytweener import Easing
from random import randint
import datetime as dt


class EasingBox(graphics.Rectangle):
    def __init__(self, name, x, y, easing_method):
        graphics.Rectangle.__init__(self, 40, 40, 3, fill = "#aaa")
        self.name = name
        self.x = x
        self.y = y
        self.easing_method = easing_method
        self.left_side = True
        self.interactive = True


class Scene(graphics.Scene):
    def __init__(self):
        graphics.Scene.__init__(self)

        self.boxes = []

        classes = Easing()
        for i, easing_class in enumerate(dir(Easing)):
            if easing_class.startswith("__") == False:
                the_class = classes.__getattribute__(easing_class)

                label = graphics.Label(easing_class, color = "#333", x = 10, y = i * 49 + 40)
                self.add_child(label)

                box = EasingBox(easing_class, 90, i * 49 + 30, the_class)
                self.add_child(box)
                self.boxes.append(box)

                label = graphics.Label(easing_class, color = "#333", x = 350, y = i * 49 + 40)
                self.add_child(label)


        self.connect("on-click", self.on_click)


    def on_click(self, area, event, clicked):
        if not clicked:
            return

        easing = clicked.easing_method

        if clicked.left_side:
            self.animate(clicked, x = 300, easing = easing.__getattribute__("ease_out"), fill="#0f0")
        else:
            self.animate(clicked, x = 90, easing = easing.__getattribute__("ease_in"), fill="#aaa")

        clicked.left_side = not clicked.left_side



class BasicWindow:
    def __init__(self):
        window = gtk.Window()
        window.set_size_request(450, 630)
        window.connect("delete_event", lambda *args: gtk.main_quit())
        window.add(Scene())
        window.show_all()


if __name__ == "__main__":
    example = BasicWindow()
    import signal
    signal.signal(signal.SIGINT, signal.SIG_DFL) # gtk3 screws up ctrl+c
    gtk.main()

########NEW FILE########
__FILENAME__ = flat_treemap
#!/usr/bin/env python
# - coding: utf-8 -
# Copyright (C) 2014 Toms Baugis <toms.baugis@gmail.com>

"""Base template"""


from gi.repository import Gtk as gtk
from lib import graphics
import random


class FlatMap(object):
    def paint(self, g, w, h):
        numbers = self.norm(0)

        for depth, normalized in enumerate(numbers):
            # we will split the dimension where we have more space
            x, y = round(w * normalized), round(h * normalized)
            y = 0 if x >= y else y
            x = 0 if y > x else x

            g.fill_area(0, 0, x or w, y or h, graphics.Colors.category20c[depth % 20])
            g.translate(x, y)
            w = w - x
            h = h - y


class Fibonacci(FlatMap):
    description = "Fibonacci"
    def __init__(self):
        self.numbers = [] # generate numbers

        # don't drink and math
        j, k = 0, 1
        for i in range(1, 20):
            res = j + k
            self.numbers.append(res)
            j, k = k, k + j

        self.numbers = sorted(self.numbers, reverse=True)



    def norm(self, depth):
        numbers = self.numbers[depth:]
        if len(numbers) < 2:
            return []

        top = numbers[0] * 1.0 / (numbers[1] + numbers[0])
        return [top] + self.norm(depth+1)




class Sum2D(FlatMap):
    description = "Current against the remaining sum"

    def __init__(self):
        self.numbers = [random.randint(1, 900) for i in range(10)]
        #self.numbers = [i for i in range(10, 100, 30)]
        self.numbers = sorted(self.numbers, reverse=True)

    def norm(self, depth):
        """we will find out how much space we have and then start dividing
        up the area accordingly"""
        numbers = self.numbers[depth:]
        if not numbers:
            return []

        total = sum(numbers) * 1.0
        top = numbers[0] * 1.0 / total
        return [top] + self.norm(depth+1)


class Max2D(FlatMap):
    description = "Current against max value"

    def __init__(self):
        self.numbers = [random.randint(10, 100) for i in range(50)]
        self.numbers = sorted(self.numbers, reverse=True)

    def norm(self, depth):
        """we will find out how much space we have and then start dividing
        up the area accordingly"""
        numbers = self.numbers
        if depth == len(self.numbers):
            return []

        total = max(numbers) * 1.0
        top = numbers[0] * 1.0 / total * 0.5
        return [top] + self.norm(depth+1)



class Scene(graphics.Scene):
    def __init__(self):
        graphics.Scene.__init__(self)
        self.experiments = [
            Fibonacci(),
            Sum2D(),
            Max2D(),
        ]

        self.current_experiment = self.experiments[0]

        self.connect("on-enter-frame", self.on_enter_frame)

    def toggles(self):
        idx = self.experiments.index(self.current_experiment)
        self.current_experiment = self.experiments[(idx + 1) % len(self.experiments)]
        self.redraw()

    def on_enter_frame(self, scene, context):
        # you could do all your drawing here, or you could add some sprites
        g = graphics.Graphics(context)
        self.current_experiment.paint(g, self.width, self.height)



class BasicWindow:
    def __init__(self):
        window = gtk.Window()
        window.set_default_size(600, 500)
        window.connect("delete_event", lambda *args: gtk.main_quit())
        box = gtk.VBox(border_width=10, spacing=10)
        window.add(box)

        self.scene = Scene()
        box.pack_start(self.scene, True, True, 0)

        button = gtk.Button("Toggles")
        box.pack_end(button, False, True, 0)
        button.connect("clicked", self.on_button_clicked)
        self.on_button_clicked(button)

        window.show_all()

        print "The morale of the story is that flat treemaps are boring with a simplified layout algo"


    def on_button_clicked(self, button):
        self.scene.toggles()
        button.set_label(self.scene.current_experiment.description + ". Click for Next")

if __name__ == '__main__':
    window = BasicWindow()
    import signal
    signal.signal(signal.SIGINT, signal.SIG_DFL) # gtk3 screws up ctrl+c
    gtk.main()

########NEW FILE########
__FILENAME__ = flocking
#!/usr/bin/env python
# - coding: utf-8 -
# Copyright (C) 2010 Toms Bauģis <toms.baugis at gmail.com>

"""
 * Flocking
 * by Daniel Shiffman.
 *
 * An implementation of Craig Reynold's Boids program to simulate
 * the flocking behavior of birds. Each boid steers itself based on
 * rules of avoidance, alignment, and coherence.

    See flocking2 for better performance.
"""

from gi.repository import Gtk as gtk
from lib import graphics

import math
from random import random

from contrib.euclid import Vector2, Point2

class Boid(object):
    radius = 3 # boid radius

    def __init__(self, location, max_speed, max_force):
        self.acceleration = Vector2()
        self.velocity = Vector2(random() * 2 - 1, random() * 2 - 1)
        self.location = location;
        self.max_speed = max_speed
        self.max_force = max_force


    def run(self, flock_boids, context):
        self.flock(flock_boids)
        self.update()
        self.borders()
        self.draw(context)


    def borders(self):
        # wrapping around
        if self.location.x < -self.radius:
            self.location.x = 600 + self.radius

        if self.location.y < -self.radius:
            self.location.y = 400 + self.radius

        if self.location.x > 600 + self.radius:
            self.location.x = -self.radius

        if self.location.y > 400 + self.radius:
            self.location.y = -self.radius



    def draw(self, context):
        context.save()
        context.translate(self.location.x, self.location.y)

        theta = self.velocity.heading() + math.pi / 2
        context.rotate(theta)

        context.move_to(0, -self.radius*2)
        context.line_to(-self.radius, self.radius*2)
        context.line_to(self.radius, self.radius*2)
        context.close_path()

        context.restore()


    def flock(self, boids):
        # We accumulate a new acceleration each time based on three rules

        separation = self.separate(boids)
        alignment = self.align(boids)
        cohesion = self.cohesion(boids)

        # Arbitrarily weight these forces
        separation = separation * 2
        alignment = alignment * 1
        cohesion = cohesion * 1

        # Add the force vectors to acceleration
        self.acceleration += separation
        self.acceleration += alignment
        self.acceleration += cohesion


    def update(self):
        self.velocity += self.acceleration
        self.velocity.limit(self.max_speed)

        self.location += self.velocity
        # Reset accelertion to 0 each cycle
        self.acceleration *= 0

    def separate(self, boids):
        desired_separation = 25.0
        sum = Vector2()
        in_zone = 0.0

        for boid in boids:
            d = (self.location - boid.location).magnitude()

            if 0 < d < desired_separation:
                diff = self.location - boid.location
                diff.normalize()
                diff = diff / d  # Weight by distance
                sum += diff
                in_zone += 1

        if in_zone:
            sum = sum / in_zone

        return sum

    def align(self, boids):
        neighbour_distance = 50.0
        sum = Vector2()
        in_zone = 0.0

        for boid in boids:
            d = (self.location - boid.location).magnitude()
            if 0 < d < neighbour_distance:
                sum += boid.velocity
                in_zone += 1

        if in_zone:
            sum = sum / in_zone # weight by neighbour count
            sum.limit(self.max_force)

        return sum

    def cohesion(self, boids):
        """ For the average location (i.e. center) of all nearby boids,
            calculate steering vector towards that location"""

        neighbour_distance = 50.0
        sum = Vector2()
        in_zone = 0.0

        for boid in boids:
            d = (self.location - boid.location).magnitude()

            if 0 < d < neighbour_distance:
                sum += boid.location
                in_zone +=1

        if in_zone:
            sum = sum / in_zone
            return self.steer(sum, False)

        return sum


    def steer(self, target, slow_down):
        steer = Vector2()

        desired = target - self.location # A vector pointing from the location to the target

        d = desired.magnitude()

        if d > 0:
            desired.normalize()

            # Two options for desired vector magnitude (1 -- based on distance, 2 -- maxspeed)
            if slow_down and d < 100:
                desired *= self.max_speed * (d / 100.0) # This damping is somewhat arbitrary
            else:
                desired *= self.max_speed

            steer = desired - self.velocity # Steering = Desired minus Velocity
            steer.limit(self.max_force) # Limit to maximum steering force
        else:
            steer = Vector2()

        return steer


class Scene(graphics.Scene):
    def __init__(self):
        graphics.Scene.__init__(self)
        self.flock = []
        self.connect("on-enter-frame", self.on_enter_frame)

    def on_enter_frame(self, scene, context):
        c_graphics = graphics.Graphics(context)
        c_graphics.set_line_style(width = 0.5)
        c_graphics.set_color("#AA00FF")


        if len(self.flock) < 40:
            self.flock.append(Boid(Vector2(100, 100), 2.0, 0.05))

        for boid in self.flock:
            boid.run(self.flock, context)

        context.stroke()
        context.fill()
        self.redraw()


class BasicWindow:
    def __init__(self):
        window = gtk.Window()
        window.set_size_request(600, 400)
        window.connect("delete_event", lambda *args: gtk.main_quit())
        window.add(Scene())
        window.show_all()


if __name__ == "__main__":
    example = BasicWindow()
    import signal
    signal.signal(signal.SIGINT, signal.SIG_DFL) # gtk3 screws up ctrl+c
    gtk.main()

########NEW FILE########
__FILENAME__ = flocking2
#!/usr/bin/env python
# - coding: utf-8 -
# Copyright (C) 2010 Toms Bauģis <toms.baugis at gmail.com>

"""
 Flocking 2 - based on flocking and added the bin-latice spatial clustering
 with all the optimizations we are still way behind the processing version.
 Help me fixing the slow parts!

 * An implementation of Craig Reynold's Boids program to simulate
 * the flocking behavior of birds. Each boid steers itself based on
 * rules of avoidance, alignment, and coherence.
 *
 Parts of code ported from opensteer (http://sourceforge.net/projects/opensteer/)
 Other parts ported from processing (http://processing.org)
"""

from gi.repository import Gtk as gtk
from lib import graphics

import math
from random import random

from contrib.euclid import Vector2, Point2
from contrib.proximity import LQProximityStore


class Boid(object):
    radius = 2 # boid radius

    # distances are squared to avoid roots (slower)
    neighbour_distance = float(50**2)
    desired_separation = float(25**2)
    braking_distance = float(100**2)

    def __init__(self, location, max_speed, max_force):
        self.acceleration = Vector2()
        self.velocity = Vector2(random() * 2 - 1, random() * 2 - 1)
        self.location = location;
        self.max_speed = max_speed
        self.max_force = max_force


    def run(self, flock_boids):
        self.flock(flock_boids)

        self.velocity += self.acceleration
        self.velocity.limit(self.max_speed)
        self.location += self.velocity

    def flock(self, boids):
        if not boids:
            return

        # We accumulate a new acceleration each time based on three rules
        # and weight them
        separation = self.separate(boids) * 2
        alignment = self.align(boids) * 1
        cohesion = self.cohesion(boids) * 1

        # The sum is the wanted acceleration
        self.acceleration = separation + alignment + cohesion


    def separate(self, boids):
        sum = Vector2()
        in_zone = 0.0

        for boid, d in boids:
            if 0 < d < self.desired_separation:
                diff = self.location - boid.location
                diff.normalize()
                diff = diff / math.sqrt(d)  # Weight by distance
                sum += diff
                in_zone += 1

        if in_zone:
            sum = sum / in_zone

        return sum

    def align(self, boids):
        sum = Vector2()
        in_zone = 0.0

        for boid, d in boids:
            if 0 < d < self.neighbour_distance:
                sum += boid.velocity
                in_zone += 1

        if in_zone:
            sum = sum / in_zone # weight by neighbour count
            sum.limit(self.max_force)

        return sum

    def cohesion(self, boids,):
        """ For the average location (i.e. center) of all nearby boids,
            calculate steering vector towards that location"""

        sum = Vector2()
        in_zone = 0

        for boid, d in boids:
            if 0 < d < self.neighbour_distance:
                sum = sum + boid.location
                in_zone +=1

        if in_zone:
            sum = sum / float(in_zone)
            return self.steer(sum, True)

        return sum

    def seek(target):
        self.acceleration += self.steer(target, False)

    def arrive(target):
        self.acceleration += self.steer(target, True)

    def steer(self, target, slow_down):
        desired = target - self.location # A vector pointing from the location to the target

        d = desired.magnitude_squared()
        if d > 0:  # this means that we have a target
            desired.normalize()


            # Two options for desired vector magnitude (1 -- based on distance, 2 -- maxspeed)
            if  slow_down and d > self.braking_distance:
                desired *= self.max_speed * d / self.braking_distance # This damping is somewhat arbitrary
            else:
                desired *= self.max_speed

            steer = desired - self.velocity # Steering = Desired minus Velocity
            steer.limit(self.max_force) # Limit to maximum steering force
            return steer
        else:
            return Vector2()



class Canvas(graphics.Scene):
    def __init__(self):
        graphics.Scene.__init__(self)
        self.segments = []

        # we should redo the boxes when window gets resized
        self.proximity_radius = 10
        self.proximities = LQProximityStore(Vector2(0,0), Vector2(600,400), self.proximity_radius)
        self.flock = []
        self.frame = 0

        self.connect("on-click", self.on_mouse_click)
        self.connect("on-enter-frame", self.on_enter_frame)


    def on_enter_frame(self, scene, context):
        c_graphics = graphics.Graphics(context)

        if len(self.flock) < 80:
            for i in range(2):
                self.flock.append(Boid(Vector2(self.width / 2, self.height / 2), 2.0, 0.05))

        # main loop (i should rename this to something more obvious)
        c_graphics.set_line_style(width = 0.8)
        c_graphics.set_color("#666")


        for boid in self.flock:
            neighbours = []
            if self.frame % 2 == 0: #recalculate direction every second frame
                neighbours = self.proximities.find_neighbours(boid, 40)

            boid.run(neighbours)
            self.wrap(boid)
            self.proximities.update_position(boid)

            self.draw_boid(context, boid)


        self.frame +=1

        context.stroke()

        self.redraw()


    def wrap(self, boid):
        "wraps boid around the edges (teleportation)"
        if boid.location.x < -boid.radius:
            boid.location.x = self.width + boid.radius

        if boid.location.y < -boid.radius:
            boid.location.y = self.height + boid.radius

        if boid.location.x > self.width + boid.radius:
            boid.location.x = -boid.radius

        if boid.location.y > self.height + boid.radius:
            boid.location.y = -boid.radius


    def draw_boid(self, context, boid):
        context.save()
        context.translate(boid.location.x, boid.location.y)

        theta = boid.velocity.heading() + math.pi / 2
        context.rotate(theta)

        context.move_to(0, -boid.radius*2)
        context.line_to(-boid.radius, boid.radius*2)
        context.line_to(boid.radius, boid.radius*2)
        context.line_to(0, -boid.radius*2)

        context.restore()


    def on_mouse_click(self, widget, event, target):
        self.flock.append(Boid(Vector2(event.x, event.y), 2.0, 0.05))




class BasicWindow:
    def __init__(self):
        window = gtk.Window()
        window.set_size_request(600, 400)
        window.connect("delete_event", lambda *args: gtk.main_quit())
        window.add(Canvas())
        window.show_all()


if __name__ == "__main__":
    example = BasicWindow()
    import signal
    signal.signal(signal.SIGINT, signal.SIG_DFL) # gtk3 screws up ctrl+c
    gtk.main()

########NEW FILE########
__FILENAME__ = flood_fill
#!/usr/bin/env python
# - coding: utf-8 -
# Copyright (C) 2010 Toms Bauģis <toms.baugis at gmail.com>
"""
    Draws initial canvas to play flood filling on (based on truchet.py).
    Then on mouse click performs queue-based flood fill.
    We are combining cairo with gdk.Image here to operate on pixel level (yay!)
"""

import gtk
from lib import graphics
import math
import random
import datetime as dt
import collections


class Canvas(graphics.Scene):
    def __init__(self):
        graphics.Scene.__init__(self)
        self.tile_size = 60
        self.image = None

        self.connect("on-click", self.on_mouse_click)
        self.connect("on-enter-frame", self.on_enter_frame)

        # don't care about anything but spraycan
        self.connect("on-mouse-move", lambda *args: self.window.set_cursor(gtk.gdk.Cursor(gtk.gdk.SPRAYCAN)))

    def on_mouse_click(self, area, event, target):
        x, y = event.x, event.y

        colormap = self.image.get_colormap()
        color1 = colormap.alloc_color(self.colors.gdk("#ff0000"))

        self.flood_fill(self.image, x, y, color1.pixel)
        self.redraw()


    def stroke_tile(self, context, x, y, size, orient):
        # draws a tile, there are just two orientations
        arc_radius = size / 2
        x2, y2 = x + size, y + size

        # i got lost here with all the Pi's
        if orient == 1:
            context.move_to(x + arc_radius, y)
            context.arc(x, y, arc_radius, 0, math.pi / 2);

            context.move_to(x2 - arc_radius, y2)
            context.arc(x2, y2, arc_radius, math.pi, math.pi + math.pi / 2);
        elif orient == 2:
            context.move_to(x2, y + arc_radius)
            context.arc(x2, y, arc_radius, math.pi - math.pi / 2, math.pi);

            context.move_to(x, y2 - arc_radius)
            context.arc(x, y2, arc_radius, math.pi + math.pi / 2, 0);

    def on_enter_frame(self, scene, context):
        """here happens all the drawing"""
        if not self.height: return

        if not self.image:
            self.two_tile_random(context)
            self.image = self.window.get_image(0, 0, self.width, self.height)

        self.window.draw_image(self.get_style().black_gc, self.image, 0, 0, 0, 0, -1, -1)



    def two_tile_random(self, context):
        """stroke area with non-filed truchet (since non filed, all match and
           there are just two types"""
        context.set_source_rgb(0,0,0)
        context.set_line_width(1)

        for y in range(0, self.height, self.tile_size):
            for x in range(0, self.width, self.tile_size):
                self.stroke_tile(context, x, y, self.tile_size, random.choice([1, 2]))
        context.stroke()

    @staticmethod
    def paint_check(color1, color2):
        return color1 != color2 and abs(color1 - color2) < 3000000


    def flood_fill(self, image, x, y, new_color, old_color = None):
        """from starting point finds left and right bounds, paint them all
           and adds any point above and below the line that is in the old color
           to the queue
        """
        x, y = int(x), int(y)
        old_color = old_color or image.get_pixel(x, y)

        queue = collections.deque()
        queue.append((x, y))

        pixels, longest_queue = 0, 0
        paint_check = self.paint_check


        t = dt.datetime.now()
        while queue:
            longest_queue = max(longest_queue, len(queue))
            x, y = queue.popleft()
            if image.get_pixel(x, y) != old_color:
                continue

            west, east = x,x  #up and down

            # find bounds
            while west > 0 and paint_check(image.get_pixel(west - 1, y), new_color):
                west -= 1

            while east < self.width - 1 and paint_check(image.get_pixel(east + 1, y), new_color):
                east += 1

            for x in range(west, east):
                pixels +=1
                image.put_pixel(x, y, new_color)
                if y > 0 and paint_check(image.get_pixel(x, y - 1), new_color):
                    queue.append((x, y - 1))

                if y < self.height - 1 and paint_check(image.get_pixel(x, y + 1), new_color):
                    queue.append((x, y + 1))


        delta = dt.datetime.now() - t
        delta_ms = delta.seconds * 1000000 + delta.microseconds
        print "%d pixels in %.2f (%.2f/s). Longest queue: %d" % \
                                          (pixels,
                                           delta_ms / 1000000.0,
                                           float(pixels) / delta_ms * 1000000.0,
                                           longest_queue)


class BasicWindow:
    def __init__(self):
        window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        window.set_size_request(500, 500)
        window.connect("delete_event", lambda *args: gtk.main_quit())

        canvas = Canvas()

        box = gtk.VBox()
        box.pack_start(canvas)


        window.add(box)
        window.show_all()


if __name__ == "__main__":
    example = BasicWindow()
    gtk.main()

########NEW FILE########
__FILENAME__ = follow3
#!/usr/bin/env python
# - coding: utf-8 -
# Copyright (C) 2010 Toms Bauģis <toms.baugis at gmail.com>

"""
 * Follow 3.
 * Based on code from Keith Peters (www.bit-101.com).
 *
 * A segmented line follows the mouse. The relative angle from
 * each segment to the next is calculated with atan2() and the
 * position of the next is calculated with sin() and cos().
 *
 Ported from processing (http://processing.org/) examples.
"""

import math
from gi.repository import Gtk as gtk
from lib import graphics

PARTS = 40
SEGMENT_LENGTH = 20

class Segment(graphics.Sprite):
    def __init__(self, x, y, color):
        graphics.Sprite.__init__(self, x, y, interactive = False, snap_to_pixel = False)
        self.angle = 1
        self.color = color

        self.graphics.rectangle(-5, -5, 10, 10, 3)
        self.graphics.move_to(0, 0)
        self.graphics.line_to(SEGMENT_LENGTH, 0)
        self.graphics.set_color("#666")
        self.graphics.fill_preserve()
        self.graphics.stroke_preserve()


    def drag(self, x, y):
        # moves segment towards x, y, keeping the original angle and preset length
        dx = x - self.x
        dy = y - self.y

        self.angle = math.atan2(dy, dx)

        self.x = x - math.cos(self.angle) * SEGMENT_LENGTH
        self.y = y - math.sin(self.angle) * SEGMENT_LENGTH
        self.rotation = self.angle


class Scene(graphics.Scene):
    def __init__(self):
        graphics.Scene.__init__(self)


        self.segments = []

        for i in range(PARTS):
            # for segment initial positions we use sinus. could as well
            # just set 0,0.
            segment = Segment(500 - (i / float(PARTS)) * 500,
                              math.sin((i / float(PARTS)) * 30) * 150 + 150,
                              "#666666")
            if self.segments:
                segment.drag(self.segments[-1].x, self.segments[-1].y)
            self.segments.append(segment)
            self.add_child(segment)

        self.connect("on-mouse-move", self.on_mouse_move)


    def on_mouse_move(self, scene, event):
        x, y = event.x, event.y

        self.segments[0].drag(x, y)
        for prev, segment in zip(self.segments, self.segments[1:]):
            segment.drag(prev.x, prev.y)

        self.redraw()


class BasicWindow:
    def __init__(self):
        window = gtk.Window()
        window.set_size_request(600, 400)
        window.connect("delete_event", lambda *args: gtk.main_quit())

        window.add(Scene())
        window.show_all()


if __name__ == "__main__":
    example = BasicWindow()
    import signal
    signal.signal(signal.SIGINT, signal.SIG_DFL) # gtk3 screws up ctrl+c
    gtk.main()

########NEW FILE########
__FILENAME__ = fruchterman_reingold
#!/usr/bin/env python
# - coding: utf-8 -
# Copyright (C) 2010 Toms Bauģis <toms.baugis at gmail.com>

"""
 Frankensteined together from everywhere, including prefuse (http://prefuse.org/),
 heygraph (http://www.heychinaski.com/blog/?p=288) and this monstrosity
 (http://www.mathiasbader.de/studium/bioinformatics/)
"""


from gi.repository import Gtk as gtk
from lib import graphics
from lib.pytweener import Easing

import math
from random import random, randint
from copy import deepcopy

class Node(object):
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.vx = 0
        self.vy = 0
        self.fixed = False #to pin down
        self.cluster = None
        self.neighbours = []


class Graph(object):
    """graph lives on it's own, separated from display"""
    def __init__(self, area_w, area_h):
        self.nodes = []
        self.edges = []
        self.clusters = []
        self.iteration = 0
        self.force_constant = 0
        self.init_layout(area_w, area_h)
        self.graph_bounds = None

    def populate_nodes(self, area_w, area_h):
        self.nodes, self.edges, self.clusters = [], [], []

        # nodes
        for i in range(randint(5, 30)):
            x, y = area_w / 2, area_h / 2
            scale_w = x * 0.2;
            scale_h = y * 0.2

            node = Node(x + (random() - 0.5) * 2 * scale_w,
                        y + (random() - 0.5) * 2 * scale_h)
            self.nodes.append(node)

        # edges
        node_count = len(self.nodes) - 1

        for i in range(randint(node_count / 3, node_count)):  #connect random nodes
            idx1, idx2 = randint(0, node_count), randint(0, node_count)
            node1 = self.nodes[idx1]
            node2 = self.nodes[idx2]

            self.add_edge(node1, node2)

    def add_edge(self, node, node2):
        if node == node2 or (node, node2) in self.edges or (node2, node) in self.edges:
            return

        self.edges.append((node, node2))
        node.neighbours.append(node2)
        node2.neighbours.append(node)

    def remove_edge(self, node, node2):
        if (node, node2) in self.edges:
            self.edges.remove((node, node2))
            node.neighbours.remove(node2)
            node2.neighbours.remove(node)

    def init_layout(self, area_w, area_h):
        if not self.nodes:
            self.nodes.append(Node(area_w / 2, area_h / 2))

        # cluster
        self.clusters = []
        for node in self.nodes:
            node.cluster = None

        all_nodes = list(self.nodes)

        def set_cluster(node, cluster):
            if not node.cluster:
                node.cluster = cluster
                cluster.append(node)
                all_nodes.remove(node)
                for node2 in node.neighbours:
                    set_cluster(node2, cluster)

        while all_nodes:
            node = all_nodes[0]
            if not node.cluster:
                new_cluster = []
                self.clusters.append(new_cluster)
                set_cluster(node, new_cluster)
        # init forces
        self.force_constant = math.sqrt(area_h * area_w / float(len(self.nodes)))
        self.temperature = len(self.nodes) + math.floor(math.sqrt(len(self.edges)))
        self.minimum_temperature = 1
        self.initial_temperature = self.temperature
        self.iteration = 0


    def update(self, area_w, area_h):
        self.node_repulsion()
        self.atraction()
        self.cluster_repulsion()
        self.position()

        self.iteration +=1
        self.temperature = max(self.temperature - (self.initial_temperature / 100), self.minimum_temperature)


        # update temperature every ten iterations
        if self.iteration % 10 == 0:
            min_x, min_y, max_x, max_y = self.graph_bounds

            graph_w, graph_h = max_x - min_x, max_y - min_y
            graph_magnitude = math.sqrt(graph_w * graph_w + graph_h * graph_h)
            canvas_magnitude = math.sqrt(area_w * area_w + area_h * area_h)

            self.minimum_temperature = graph_magnitude / canvas_magnitude

    def cluster_repulsion(self):
        """push around unconnected nodes on overlap"""
        for cluster in self.clusters:
            ax1, ay1, ax2, ay2 = self.bounds(cluster)

            for cluster2 in self.clusters:
                if cluster == cluster2:
                    continue

                bx1, by1, bx2, by2 = self.bounds(cluster2)

                if (bx1 <= ax1 <= bx2 or bx1 <= ax2 <= bx2) \
                and (by1 <= ay1 <= by2 or by1 <= ay2 <= by2):

                    dx = (ax1 + ax2) / 2 - (bx1 + bx2) / 2
                    dy = (ay1 + ay2) / 2 - (by1 + by2) / 2

                    max_d = float(max(abs(dx), abs(dy)))

                    dx, dy = dx / max_d, dy / max_d

                    force_x = dx * random() * 100
                    force_y = dy * random() * 100

                    for node in cluster:
                        node.x += force_x
                        node.y += force_y

                    for node in cluster2:
                        node.x -= force_x
                        node.y -= force_y

    def node_repulsion(self):
        """calculate repulsion for the node"""

        for node in self.nodes:
            node.vx, node.vy = 0, 0 # reset velocity back to zero

            for node2 in node.cluster:
                if node == node2: continue

                dx = node.x - node2.x
                dy = node.y - node2.y

                magnitude = math.sqrt(dx * dx + dy * dy)


                if magnitude:
                    force = self.force_constant * self.force_constant / magnitude
                    node.vx += dx / magnitude * force
                    node.vy += dy / magnitude * force



    def atraction(self):
        for edge in self.edges:
            node1, node2 = edge

            dx = node1.x - node2.x
            dy = node1.y - node2.y

            distance = math.sqrt(dx * dx + dy * dy)
            if distance:
                force = distance * distance / self.force_constant

                node1.vx -= dx / distance * force
                node1.vy -= dy / distance * force

                node2.vx += dx / distance * force
                node2.vy += dy / distance * force



    def position(self):
        biggest_move = -1

        x1, y1, x2, y2 = 100000, 100000, -100000, -100000

        for node in self.nodes:
            if node.fixed:
                node.fixed = False
                continue

            distance = math.sqrt(node.vx * node.vx + node.vy * node.vy)

            if distance:
                node.x += node.vx / distance * min(abs(node.vx), self.temperature)
                node.y += node.vy / distance * min(abs(node.vy), self.temperature)

            x1, y1 = min(x1, node.x), min(y1, node.y)
            x2, y2 = max(x2, node.x), max(y2, node.y)

        self.graph_bounds = (x1,y1,x2,y2)

    def bounds(self, nodes):
        x1, y1, x2, y2 = 100000, 100000, -100000, -100000
        for node in nodes:
            x1, y1 = min(x1, node.x), min(y1, node.y)
            x2, y2 = max(x2, node.x), max(y2, node.y)

        return (x1, y1, x2, y2)



class DisplayNode(graphics.Sprite):
    def __init__(self, x, y, real_node):
        graphics.Sprite.__init__(self, x=x, y=y, interactive=True, draggable=True)
        self.real_node = real_node
        self.fill = "#999"

        self.connect("on-mouse-over", self.on_mouse_over)
        self.connect("on-mouse-out", self.on_mouse_out)
        self.connect("on-render", self.on_render)

    def on_mouse_over(self, sprite):
        self.fill = "#000"

    def on_mouse_out(self, sprite):
        self.fill = "#999"

    def on_render(self, sprite):
        self.graphics.clear()
        self.graphics.arc(0, 0, 5, 0, math.pi * 2)
        self.graphics.fill(self.fill)

        # adding invisible circle with bigger radius for easier targeting
        self.graphics.arc(0, 0, 10, 0, math.pi * 2)
        self.graphics.stroke("#000", 0)



class Canvas(graphics.Scene):
    def __init__(self):
        graphics.Scene.__init__(self)
        self.edge_buffer = []
        self.clusters = []

        self.connect("on-enter-frame", self.on_enter_frame)
        self.connect("on-finish-frame", self.on_finish_frame)
        self.connect("on-click", self.on_node_click)
        self.connect("on-drag", self.on_node_drag)
        self.connect("on-mouse-move", self.on_mouse_move)

        self.mouse_node = None
        self.mouse = None
        self.graph = None
        self.redo_layout = False
        self.display_nodes = []


    def on_node_click(self, scene, event,  sprite):

        mouse_node = sprite

        if mouse_node:
            if self.mouse_node:
                if mouse_node == self.mouse_node:
                    self.mouse_node = None
                    return


                #check if maybe there is an edge already - in that case remove it
                if (self.mouse_node.real_node, mouse_node.real_node) in self.graph.edges:
                    self.graph.remove_edge(self.mouse_node.real_node, mouse_node.real_node)

                elif (mouse_node.real_node, self.mouse_node.real_node) in self.graph.edges:
                    self.graph.remove_edge(mouse_node.real_node, self.mouse_node.real_node)

                else:
                    self.graph.add_edge(self.mouse_node.real_node, mouse_node.real_node)

                self.update_buffer()

                if event.button != 3:
                    self.mouse_node = mouse_node
                else:
                    self.mouse_node = None

                self.queue_relayout()
            else:
                self.mouse_node = mouse_node
        else:
            if event.button == 3:
                self.mouse_node = None
            else:
                new_node = Node(*self.screen_to_graph(event.x, event.y))
                self.graph.nodes.append(new_node)
                display_node = self.add_node(event.x, event.y, new_node)

                if self.mouse_node:
                    self.graph.add_edge(self.mouse_node.real_node, new_node)
                    self.update_buffer()

                self.mouse_node = display_node


            self.queue_relayout()

    def on_node_drag(self, scene, node, event):
        node.real_node.x, node.real_node.y = self.screen_to_graph(event.x, event.y)
        node.real_node.fixed = True
        self.redraw()


    def on_mouse_move(self, scene, event):
        self.mouse = (event.x, event.y)
        self.queue_relayout()


    def delauney(self):
        pass

    def add_node(self, x, y, real_node):
        display_node = DisplayNode(x, y, real_node)
        self.add_child(display_node)
        self.display_nodes.append(display_node)
        return display_node


    def new_graph(self):
        self.clear()
        self.display_nodes = []
        self.add_child(graphics.Label("Click on screen to add node. Right-click to stop the thread from going on", color="#666", x=10, y=10))


        self.edge_buffer = []

        if not self.graph:
            self.graph = Graph(self.width, self.height)
        else:
            self.graph.populate_nodes(self.width, self.height)
            self.queue_relayout()

        for node in self.graph.nodes:
            self.add_node(node.x, node.y, node)

        self.update_buffer()

        self.redraw()

    def queue_relayout(self):
        self.redo_layout = True
        self.redraw()

    def update_buffer(self):
        self.edge_buffer = []

        for edge in self.graph.edges:
            self.edge_buffer.append((
                self.display_nodes[self.graph.nodes.index(edge[0])],
                self.display_nodes[self.graph.nodes.index(edge[1])],
            ))


    def on_finish_frame(self, scene, context):
        if self.mouse_node and self.mouse:
            c_graphics = graphics.Graphics(context)
            c_graphics.set_color("#666")
            c_graphics.move_to(self.mouse_node.x, self.mouse_node.y)
            c_graphics.line_to(*self.mouse)
            c_graphics.stroke()


    def on_enter_frame(self, scene, context):
        c_graphics = graphics.Graphics(context)

        if not self.graph:
            self.new_graph()
            self.graph.update(self.width, self.height)


        if self.redo_layout:
            self.redo_layout = False
            self.graph.init_layout(self.width, self.height)


        # first draw
        c_graphics.set_line_style(width = 0.5)

        done = abs(self.graph.minimum_temperature - self.graph.temperature) < 0.05


        if not done:
            c_graphics.set_color("#aaa")
        else:
            c_graphics.set_color("#666")

        for edge in self.edge_buffer:
            context.move_to(edge[0].x, edge[0].y)
            context.line_to(edge[1].x, edge[1].y)
        context.stroke()


        if not done:
            # then recalculate positions
            self.graph.update(self.width, self.height)

            # find bounds
            min_x, min_y, max_x, max_y = self.graph.graph_bounds
            graph_w, graph_h = max_x - min_x, max_y - min_y

            factor_x = self.width / float(graph_w)
            factor_y = self.height / float(graph_h)
            graph_mid_x = (min_x + max_x) / 2.0
            graph_mid_y = (min_y + max_y) / 2.0

            mid_x, mid_y = self.width / 2.0, self.height / 2.0

            factor = min(factor_x, factor_y) * 0.9 # just have the smaller scale, avoid deformations

            for i, node in enumerate(self.display_nodes):
                self.tweener.kill_tweens(node)
                self.animate(node,
                             x = mid_x + (self.graph.nodes[i].x - graph_mid_x) * factor,
                             y = mid_y + (self.graph.nodes[i].y - graph_mid_y) * factor,
                             easing = Easing.Expo.ease_out,
                             duration = 3)


            self.redraw()

    def screen_to_graph(self,x, y):
        if len(self.graph.nodes) <= 1:
            return x, y



        min_x, min_y, max_x, max_y = self.graph.graph_bounds
        graph_w, graph_h = max_x - min_x, max_y - min_y

        factor_x = self.width / float(graph_w)
        factor_y = self.height / float(graph_h)
        graph_mid_x = (min_x + max_x) / 2.0
        graph_mid_y = (min_y + max_y) / 2.0

        mid_x, mid_y = self.width / 2.0, self.height / 2.0

        factor = min(factor_x, factor_y) * 0.9 # just have the smaller scale, avoid deformations

        graph_x = (x - mid_x) / factor + graph_mid_x
        graph_y = (y - mid_y) / factor + graph_mid_y

        return graph_x, graph_y


    def graph_to_screen(self,x, y):
        pass


class BasicWindow:
    def __init__(self):
        window = gtk.Window()
        window.set_size_request(600, 500)
        window.connect("delete_event", lambda *args: gtk.main_quit())

        self.canvas = Canvas()

        box = gtk.VBox()
        box.add(self.canvas)

        """
        hbox = gtk.HBox(False, 5)
        hbox.set_border_width(12)

        box.pack_start(hbox, False)

        hbox.pack_start(gtk.HBox()) # filler
        button = gtk.Button("Random Nodes")
        button.connect("clicked", lambda *args: self.canvas.new_graph())
        hbox.pack_start(button, False)
        """

        window.add(box)
        window.show_all()


if __name__ == "__main__":
    example = BasicWindow()
    import signal
    signal.signal(signal.SIGINT, signal.SIG_DFL) # gtk3 screws up ctrl+c
    gtk.main()

########NEW FILE########
__FILENAME__ = fruchterman_reingold_delauney
#!/usr/bin/env python
# - coding: utf-8 -
# Copyright (C) 2010 Toms Bauģis <toms.baugis at gmail.com>

"""
 Crossing the FDL with delauney triangulation. Right now does not scale at all
 and the drag is broken.
"""


from gi.repository import Gtk as gtk
from lib import graphics
from lib.pytweener import Easing

import math
from random import random, randint
from copy import deepcopy

from contrib.euclid import Vector2
import itertools

EPSILON = 0.00001

class Node(object):
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.vx = 0
        self.vy = 0
        self.fixed = False #to pin down
        self.cluster = None
        self.neighbours = []


class Graph(object):
    """graph lives on it's own, separated from display"""
    def __init__(self, area_w, area_h):
        self.nodes = []
        self.edges = []
        self.clusters = []
        self.iteration = 0
        self.force_constant = 0
        self.init_layout(area_w, area_h)
        self.graph_bounds = None

    def populate_nodes(self, area_w, area_h):
        self.nodes, self.edges, self.clusters = [], [], []

        # nodes
        for i in range(randint(5, 30)):
            x, y = area_w / 2, area_h / 2
            scale_w = x * 0.2;
            scale_h = y * 0.2

            node = Node(x + (random() - 0.5) * 2 * scale_w,
                        y + (random() - 0.5) * 2 * scale_h)
            self.nodes.append(node)

        # edges
        node_count = len(self.nodes) - 1

        for i in range(randint(node_count / 3, node_count)):  #connect random nodes
            idx1, idx2 = randint(0, node_count), randint(0, node_count)
            node1 = self.nodes[idx1]
            node2 = self.nodes[idx2]

            self.add_edge(node1, node2)

    def add_edge(self, node, node2):
        if node == node2 or (node, node2) in self.edges or (node2, node) in self.edges:
            return

        self.edges.append((node, node2))
        node.neighbours.append(node2)
        node2.neighbours.append(node)

    def remove_edge(self, node, node2):
        if (node, node2) in self.edges:
            self.edges.remove((node, node2))
            node.neighbours.remove(node2)
            node2.neighbours.remove(node)

    def init_layout(self, area_w, area_h):
        if not self.nodes:
            self.nodes.append(Node(area_w / 2, area_h / 2))

        # cluster
        self.clusters = []
        for node in self.nodes:
            node.cluster = None

        all_nodes = list(self.nodes)

        def set_cluster(node, cluster):
            if not node.cluster:
                node.cluster = cluster
                cluster.append(node)
                all_nodes.remove(node)
                for node2 in node.neighbours:
                    set_cluster(node2, cluster)

        while all_nodes:
            node = all_nodes[0]
            if not node.cluster:
                new_cluster = []
                self.clusters.append(new_cluster)
                set_cluster(node, new_cluster)
        # init forces
        self.force_constant = math.sqrt(area_h * area_w / float(len(self.nodes)))
        self.temperature = (len(self.nodes) + math.floor(math.sqrt(len(self.edges)))) * 1
        self.minimum_temperature = 1
        self.initial_temperature = self.temperature
        self.iteration = 0


    def update(self, area_w, area_h):
        self.node_repulsion()
        self.atraction()
        self.cluster_repulsion()
        self.position()

        self.iteration +=1
        self.temperature = max(self.temperature - (self.initial_temperature / 100), self.minimum_temperature)


        # update temperature every ten iterations
        if self.iteration % 10 == 0:
            min_x, min_y, max_x, max_y = self.graph_bounds

            graph_w, graph_h = max_x - min_x, max_y - min_y
            graph_magnitude = math.sqrt(graph_w * graph_w + graph_h * graph_h)
            canvas_magnitude = math.sqrt(area_w * area_w + area_h * area_h)

            self.minimum_temperature = graph_magnitude / canvas_magnitude

    def cluster_repulsion(self):
        """push around unconnected nodes on overlap"""
        for cluster in self.clusters:
            ax1, ay1, ax2, ay2 = self.bounds(cluster)

            for cluster2 in self.clusters:
                if cluster == cluster2:
                    continue

                bx1, by1, bx2, by2 = self.bounds(cluster2)

                if (bx1 <= ax1 <= bx2 or bx1 <= ax2 <= bx2) \
                and (by1 <= ay1 <= by2 or by1 <= ay2 <= by2):

                    dx = (ax1 + ax2) / 2 - (bx1 + bx2) / 2
                    dy = (ay1 + ay2) / 2 - (by1 + by2) / 2

                    max_d = float(max(abs(dx), abs(dy)))

                    dx, dy = dx / max_d, dy / max_d

                    force_x = dx * random() * 100
                    force_y = dy * random() * 100

                    for node in cluster:
                        node.x += force_x
                        node.y += force_y

                    for node in cluster2:
                        node.x -= force_x
                        node.y -= force_y

    def node_repulsion(self):
        """calculate repulsion for the node"""

        for node in self.nodes:
            node.vx, node.vy = 0, 0 # reset velocity back to zero

            for node2 in node.cluster:
                if node == node2: continue

                dx = node.x - node2.x
                dy = node.y - node2.y

                magnitude = math.sqrt(dx * dx + dy * dy)


                if magnitude:
                    force = self.force_constant * self.force_constant / magnitude
                    node.vx += dx / magnitude * force
                    node.vy += dy / magnitude * force



    def atraction(self):
        for edge in self.edges:
            node1, node2 = edge

            dx = node1.x - node2.x
            dy = node1.y - node2.y

            distance = math.sqrt(dx * dx + dy * dy)
            if distance:
                force = distance * distance / self.force_constant

                node1.vx -= dx / distance * force
                node1.vy -= dy / distance * force

                node2.vx += dx / distance * force
                node2.vy += dy / distance * force



    def position(self):
        biggest_move = -1

        x1, y1, x2, y2 = 100000, 100000, -100000, -100000

        for node in self.nodes:
            distance = math.sqrt(node.vx * node.vx + node.vy * node.vy)

            if distance:
                node.x += node.vx / distance * min(abs(node.vx), self.temperature)
                node.y += node.vy / distance * min(abs(node.vy), self.temperature)

            x1, y1 = min(x1, node.x), min(y1, node.y)
            x2, y2 = max(x2, node.x), max(y2, node.y)

        self.graph_bounds = (x1,y1,x2,y2)

    def bounds(self, nodes):
        x1, y1, x2, y2 = 100000, 100000, -100000, -100000
        for node in nodes:
            x1, y1 = min(x1, node.x), min(y1, node.y)
            x2, y2 = max(x2, node.x), max(y2, node.y)

        return (x1, y1, x2, y2)



class DisplayNode(graphics.Sprite):
    def __init__(self, x, y, real_node):
        graphics.Sprite.__init__(self, x=x, y=y, pivot_x=5, pivot_y=5,
                                 interactive=True, draggable=True)
        self.real_node = real_node
        self.fill = "#999"

        self.connect("on-mouse-over", self.on_mouse_over)
        self.connect("on-mouse-out", self.on_mouse_out)
        self.draw_graphics()

    def on_mouse_over(self, sprite):
        self.fill = "#000"
        self.draw_graphics()

    def on_mouse_out(self, sprite):
        self.fill = "#999"
        self.draw_graphics()


    def draw_graphics(self):
        self.graphics.clear()
        self.graphics.set_color(self.fill)
        self.graphics.circle(0, 0, 5)
        self.graphics.fill()

        # adding invisible circle with bigger radius for easier targeting
        self.graphics.set_color("#000", 0)
        self.graphics.circle(0, 0, 10)
        self.graphics.stroke()



class Canvas(graphics.Scene):
    def __init__(self):
        graphics.Scene.__init__(self)
        self.edge_buffer = []
        self.clusters = []

        self.connect("on-enter-frame", self.on_enter_frame)
        self.connect("on-finish-frame", self.on_finish_frame)
        self.connect("on-click", self.on_node_click)
        self.connect("on-drag", self.on_node_drag)
        self.connect("on-mouse-move", self.on_mouse_move)

        self.mouse_node = None
        self.mouse = None
        self.graph = None
        self.redo_layout = False
        self.display_nodes = []
        #self.framerate = 10


    def on_node_click(self, scene, event,  sprite):
        new_node = Node(*self.screen_to_graph(event.x, event.y))
        self.graph.nodes.append(new_node)
        display_node = self.add_node(event.x, event.y, new_node)

        self.queue_relayout()

    def on_node_drag(self, scene, node, event):
        node.real_node.x, node.real_node.y = self.screen_to_graph(event.x, event.y)
        node.real_node.fixed = True
        self.redraw()


    def on_mouse_move(self, scene, event):
        self.mouse = (event.x, event.y)
        self.queue_relayout()



    def triangle_circumcenter(self, a, b, c):
        """shockingly, the circumcenter math has been taken from wikipedia
           we move the triangle to 0,0 coordinates to simplify math"""

        p_a = Vector2(a.x, a.y)
        p_b = Vector2(b.x, b.y) - p_a
        p_c = Vector2(c.x, c.y) - p_a

        p_b2 = p_b.magnitude_squared()
        p_c2 = p_c.magnitude_squared()

        d = 2 * (p_b.x * p_c.y - p_b.y * p_c.x)

        if d < 0:
            d = min(d, EPSILON)
        else:
            d = max(d, EPSILON)


        centre_x = (p_c.y * p_b2 - p_b.y * p_c2) / d
        centre_y = (p_b.x * p_c2 - p_c.x * p_b2) / d

        centre = p_a + Vector2(centre_x, centre_y)
        return centre


    def delauney(self):
        segments = []
        combos = list(itertools.combinations(self.graph.nodes, 3))
        #print "combinations: ", len(combos)
        for a, b, c in combos:
            centre = self.triangle_circumcenter(a, b, c)

            distance2 = (Vector2(a.x, a.y) - centre).magnitude_squared()

            smaller_found = False
            for node in self.graph.nodes:
                if node in [a,b,c]:
                    continue

                if (Vector2(node.x, node.y) - centre).magnitude_squared() < distance2:
                    smaller_found = True
                    break

            if not smaller_found:
                segments.extend(list(itertools.combinations([a,b,c], 2)))

        for segment in segments:
            order = sorted(segment, key = lambda node: node.x+node.y)
            segment = (order[0], order[1])

        segments = set(segments)

        return segments



    def add_node(self, x, y, real_node):
        display_node = DisplayNode(x, y, real_node)
        self.add_child(display_node)
        self.display_nodes.append(display_node)
        return display_node


    def new_graph(self):
        self.clear()
        self.display_nodes = []
        self.add_child(graphics.Label("Click on screen to add nodes. After that you can drag them around", color="#666", x=10, y=10))


        self.edge_buffer = []

        if not self.graph:
            self.graph = Graph(self.width, self.height)
        else:
            self.graph.populate_nodes(self.width, self.height)
            self.queue_relayout()

        for node in self.graph.nodes:
            self.add_node(node.x, node.y, node)

        self.update_buffer()

        self.redraw()

    def queue_relayout(self):
        self.redo_layout = True
        self.redraw()

    def update_buffer(self):
        self.edge_buffer = set()

        for edge in self.graph.edges:
            self.edge_buffer.add((
                self.display_nodes[self.graph.nodes.index(edge[0])],
                self.display_nodes[self.graph.nodes.index(edge[1])],
            ))


    def on_finish_frame(self, scene, context):
        if self.mouse_node and self.mouse:
            c_graphics = graphics.Graphics(context)
            c_graphics.set_color("#666")
            c_graphics.move_to(self.mouse_node.x, self.mouse_node.y)
            c_graphics.line_to(*self.mouse)
            c_graphics.stroke()


    def on_enter_frame(self, scene, context):
        c_graphics = graphics.Graphics(context)

        if not self.graph:
            self.new_graph()
            self.graph.update(self.width, self.height)


        if self.redo_layout:
            self.redo_layout = False
            self.graph.init_layout(self.width, self.height)


        #rewire nodes using delauney
        segments = self.delauney()
        if segments:
            self.graph.clusters = []
            self.graph.edges = []
            for node in self.graph.nodes:
                node.cluster = None
                node.neighbours = []

            for node, node2 in segments:
                self.graph.add_edge(node, node2)

            self.update_buffer()

            self.graph.init_layout(self.width, self.height)




        c_graphics.set_line_style(width = 0.5)
        done = abs(self.graph.minimum_temperature - self.graph.temperature) < 0.05

        if not done:
            c_graphics.set_color("#aaa")
        else:
            c_graphics.set_color("#666")

        if not done:
            # then recalculate positions
            self.graph.update(self.width, self.height)

            # find bounds
            min_x, min_y, max_x, max_y = self.graph.graph_bounds
            graph_w, graph_h = max_x - min_x, max_y - min_y

            factor_x = self.width / float(graph_w)
            factor_y = self.height / float(graph_h)
            graph_mid_x = (min_x + max_x) / 2.0
            graph_mid_y = (min_y + max_y) / 2.0

            mid_x, mid_y = self.width / 2.0, self.height / 2.0

            factor = min(factor_x, factor_y) * 0.9 # just have the smaller scale, avoid deformations

            for i, node in enumerate(self.display_nodes):
                self.tweener.kill_tweens(node)
                self.animate(node,
                             x = mid_x + (self.graph.nodes[i].x - graph_mid_x) * factor,
                             y = mid_y + (self.graph.nodes[i].y - graph_mid_y) * factor,
                             easing = Easing.Expo.ease_out,
                             duration = 3)


            for edge in self.edge_buffer:
                context.move_to(edge[0].x, edge[0].y)
                context.line_to(edge[1].x, edge[1].y)
            context.stroke()


            self.redraw()

    def screen_to_graph(self,x, y):
        if len(self.graph.nodes) <= 1:
            return x, y



        min_x, min_y, max_x, max_y = self.graph.graph_bounds
        graph_w, graph_h = max_x - min_x, max_y - min_y

        factor_x = self.width / float(graph_w)
        factor_y = self.height / float(graph_h)
        graph_mid_x = (min_x + max_x) / 2.0
        graph_mid_y = (min_y + max_y) / 2.0

        mid_x, mid_y = self.width / 2.0, self.height / 2.0

        factor = min(factor_x, factor_y) * 0.9 # just have the smaller scale, avoid deformations

        graph_x = (x - mid_x) / factor + graph_mid_x
        graph_y = (y - mid_y) / factor + graph_mid_y

        return graph_x, graph_y

    def graph_to_screen(self,x, y):
        pass


class BasicWindow:
    def __init__(self):
        window = gtk.Window()
        window.set_size_request(600, 500)
        window.connect("delete_event", lambda *args: gtk.main_quit())

        self.canvas = Canvas()

        box = gtk.VBox()
        box.add(self.canvas)

        """
        hbox = gtk.HBox(False, 5)
        hbox.set_border_width(12)

        box.pack_start(hbox, False)

        hbox.pack_start(gtk.HBox()) # filler
        button = gtk.Button("Random Nodes")
        button.connect("clicked", lambda *args: self.canvas.new_graph())
        hbox.pack_start(button, False)
        """

        window.add(box)
        window.show_all()


if __name__ == "__main__":
    example = BasicWindow()
    import signal
    signal.signal(signal.SIGINT, signal.SIG_DFL) # gtk3 screws up ctrl+c
    gtk.main()

########NEW FILE########
__FILENAME__ = geyes
#!/usr/bin/env python
# - coding: utf-8 -
# Copyright (C) 2010 Toms Bauģis <toms.baugis at gmail.com>

"""Guess what, haha. Oh and the math is way wrong here
   Morale of the story though is that the coordinates are given even when
   outside the window
"""


from gi.repository import Gtk as gtk
from lib import graphics
import math

class Eye(graphics.Sprite):
    def __init__(self, x, y, width, height):
        graphics.Sprite.__init__(self, x=x, y=y, interactive=True, draggable=True)
        self.angle = 0
        self.pupil_distance = 0
        self.width = width
        self.height = height
        self.connect("on-render", self.on_render)

    def update(self, mouse_x, mouse_y):
        distance_x, distance_y = (mouse_x - self.x), (mouse_y - self.y)
        self.pointer_distance = math.sqrt(distance_x**2 + distance_y**2)
        self.pupil_rotation = math.atan2(distance_x, distance_y)

    def on_render(self, sprite):
        width, height = self.width, self.height
        self.graphics.ellipse(-width / 2, -height / 2, width, height)
        self.graphics.fill("#fff")

        rotation = self.pupil_rotation

        pupil_radius = min(width / 4.0, height / 4.0)

        pupil_x = min((width / 2.0 - pupil_radius), self.pointer_distance) * math.sin(rotation)
        pupil_y = min((height / 2.0 - pupil_radius), self.pointer_distance) * math.cos(rotation)


        self.graphics.circle(pupil_x, pupil_y, pupil_radius)
        self.graphics.fill("#000")



class Scene(graphics.Scene):
    def __init__(self):
        graphics.Scene.__init__(self, framerate = 20)
        self.eyes = [Eye(50, 100, 70, 100),
                     Eye(150, 100, 70, 100)]
        self.add_child(*self.eyes)
        self.connect("on-enter-frame", self.on_enter_frame)

    def on_enter_frame(self, scene, context):
        for eye in self.eyes:
            eye.update(self.mouse_x, self.mouse_y)

        self.redraw()

class BasicWindow:
    def __init__(self):
        window = gtk.Window()
        window.set_size_request(200, 200)
        window.connect("delete_event", lambda *args: gtk.main_quit())
        window.add(Scene())
        window.show_all()

example = BasicWindow()
import signal
signal.signal(signal.SIGINT, signal.SIG_DFL) # gtk3 screws up ctrl+c
gtk.main()

########NEW FILE########
__FILENAME__ = graphs
#!/usr/bin/env python
# - coding: utf-8 -
# Copyright (C) 2014 Toms Baugis <toms.baugis@gmail.com>

"""Base template"""

from gi.repository import Gtk as gtk
from lib import graphics
from lib.pytweener import Easing

import datetime
import datetime as dt


def full_pixels(space, data, gap_pixels=1):
    """returns the given data distributed in the space ensuring it's full pixels
    and with the given gap.
    this will result in minor sub-pixel inaccuracies.
    """
    available = space - (len(data) - 1) * gap_pixels # 8 recs 7 gaps

    res = []
    for i, val in enumerate(data):
        # convert data to 0..1 scale so we deal with fractions
        data_sum = sum(data[i:])
        norm = val * 1.0 / data_sum


        w = max(int(round(available * norm)), 1)
        res.append(w)
        available -= w
    return res


class Scene(graphics.Scene):
    def __init__(self):
        graphics.Scene.__init__(self)
        self.connect("on-enter-frame", self.on_enter_frame)
        self.background_color = "#333"

    def time_volume(self, g, data):
        total_claimed = sum((rec['claimed'] for rec in data))
        max_claimed = max((rec['claimed'] for rec in data))

        total_duration = dt.timedelta()
        for rec in data:
            total_duration += rec['time']
        total_duration = total_duration.total_seconds()

        h = 100
        w = (self.width - 50) / 100.0 * total_claimed

        colors = {
            "slow": "#63623F",
            "fast": "#3F5B63",
        }

        g.move_to(0, h / 2)
        g.line_to(w, h / 2)
        g.stroke("#eee")

        for rec in data:
            rec_x = w * rec['time'].total_seconds() / total_duration
            rec_h = int(h / 2.0 * (rec['claimed'] / max_claimed))
            rec_h = max(rec_h, 1)

            g.circle(rec_x, h / 2, rec_h)
            g.fill(graphics.Colors.contrast(colors[rec['speed']], 50), 0.5)
            """
            g.fill_area(0, h-rec_h,
                        int(rec_w), rec_h,
                        graphics.Colors.contrast(colors[rec['speed']], 50))
            """

            g.translate(rec_x, 0)

    def just_volume(self, g, data):
        """a stacked bar of just volumes up to claimed"""
        total_claimed = sum((rec['claimed'] for rec in data))

        h = 50
        w = int(self.width / 100.0 * total_claimed)

        colors = {
            "slow": "#63623F",
            "fast": "#3F5B63",
        }

        g.save_context()

        gap = 3
        widths = full_pixels(w, [rec['claimed'] for rec in data], gap)
        for rec_w, rec in zip(widths, data):
            g.fill_area(-0.5, -0.5,
                        rec_w, h + 1,
                        graphics.Colors.contrast(colors[rec['speed']], 50))

            g.translate(rec_w + gap, 0)

            g.move_to(-gap+1, -0.5)
            g.line_to(-gap+1, h + 1)
            g.stroke(graphics.Colors.contrast(colors[rec['speed']], 0))
        g.restore_context()


        g.rectangle(-2, -2, self.width-14, h+4)
        g.move_to(int(w), -20)
        g.line_to(int(w), h + 20)
        g.stroke("#eee")



    def duration_vs_volume(self, g, data):
        """a scatterplot of claim patterns"""
        total_claimed = sum((rec['claimed'] for rec in data))
        max_claimed = max((rec['claimed'] for rec in data))



        durations = [data[0]["time"]]
        max_duration = durations[0]
        for prev, next in zip(data, data[1:]):
            durations.append(next['time']-prev['time'])
            max_duration = max(max_duration, durations[-1])

        max_duration = max_duration.total_seconds()

        h = 200
        w = self.width - 20

        colors = {
            "slow": "#63623F",
            "fast": "#3F5B63",
        }

        g.move_to(0, 0)
        g.line_to([(0, h), (w, h)])
        g.stroke("#aaa")

        for rec, duration in zip(data, durations):
            x = w * 0.8 * duration.total_seconds() / max_duration
            y = h - h * 0.8 * rec['claimed'] / max_claimed

            g.fill_area(x-5, y-5,
                        10, 10,
                        graphics.Colors.contrast(colors[rec['speed']], 50))





    def on_enter_frame(self, scene, context):
        g = graphics.Graphics(context)

        data = [{'claimed': 0.7466666666666667, 'speed': 'fast', 'time': datetime.timedelta(0, 2, 52537)},
                {'claimed': 1.7813333333333334, 'speed': 'fast', 'time': datetime.timedelta(0, 4, 449440)}, {'claimed': 2.965333333333333, 'speed': 'fast', 'time': datetime.timedelta(0, 9, 171014)}, {'claimed': 45.424, 'speed': 'slow', 'time': datetime.timedelta(0, 16, 733329)}, {'claimed': 0.8, 'speed': 'fast', 'time': datetime.timedelta(0, 19, 697931)}, {'claimed': 1.44, 'speed': 'fast', 'time': datetime.timedelta(0, 21, 693617)}, {'claimed': 0.4053333333333333, 'speed': 'fast', 'time': datetime.timedelta(0, 23, 404403)}, {'claimed': 0.6453333333333333, 'speed': 'fast', 'time': datetime.timedelta(0, 25, 592150)}, {'claimed': 13.530666666666667, 'speed': 'slow', 'time': datetime.timedelta(0, 28, 753307)}, {'claimed': 0.7253333333333334, 'speed': 'fast', 'time': datetime.timedelta(0, 30, 684011)}, {'claimed': 0.192, 'speed': 'fast', 'time': datetime.timedelta(0, 32, 345738)}, {'claimed': 1.2906666666666666, 'speed': 'fast', 'time': datetime.timedelta(0, 34, 676201)}, {'claimed': 24.528, 'speed': 'slow', 'time': datetime.timedelta(0, 39, 406208)}]
        #data = [{'claimed': 0.21333333333333335, 'speed': 'fast', 'time': datetime.timedelta(0, 0, 873499)}, {'claimed': 0.4, 'speed': 'fast', 'time': datetime.timedelta(0, 2, 281331)}, {'claimed': 1.3226666666666667, 'speed': 'fast', 'time': datetime.timedelta(0, 4, 116499)}, {'claimed': 3.008, 'speed': 'fast', 'time': datetime.timedelta(0, 6, 930709)}, {'claimed': 0.896, 'speed': 'fast', 'time': datetime.timedelta(0, 8, 921856)}, {'claimed': 0.608, 'speed': 'fast', 'time': datetime.timedelta(0, 9, 936559)}, {'claimed': 51.19466666666667, 'speed': 'fast', 'time': datetime.timedelta(0, 17, 55576)}, {'claimed': 15.829333333333333, 'speed': 'fast', 'time': datetime.timedelta(0, 20, 666332)}, {'claimed': 3.8026666666666666, 'speed': 'fast', 'time': datetime.timedelta(0, 24, 745785)}]

        g.set_line_style(3)
        g.translate(0.5, 0.5)

        g.translate(10, 50)
        g.save_context()
        self.time_volume(g, data)
        g.restore_context()

        g.translate(0, 150)
        g.save_context()
        self.just_volume(g, data)
        g.restore_context()

        g.translate(0, 100)
        g.save_context()
        self.duration_vs_volume(g, data)
        g.restore_context()


class BasicWindow:
    def __init__(self):
        window = gtk.Window()
        window.set_default_size(600, 600)
        window.connect("delete_event", lambda *args: gtk.main_quit())
        window.add(Scene())
        window.show_all()


if __name__ == '__main__':
    window = BasicWindow()
    import signal
    signal.signal(signal.SIGINT, signal.SIG_DFL) # gtk3 screws up ctrl+c
    gtk.main()

########NEW FILE########
__FILENAME__ = grid
#!/usr/bin/env python
# - coding: utf-8 -

# Copyright 2013 Bryce W. Harrington <bryce@bryceharrington.org>
# Dual licensed under the MIT or GPL Version 2 licenses.

from gi.repository import Gtk as gtk
from lib import graphics

class GridElement(object):
    def __init__(self, i, j, height,width, **args):
        self.__graphic = None
        self.i = i
        self.j = j
        self.height = height
        self.width = width
        self.stroke_width = args.get('stroke_width', 2)
        self.color_foreground = args.get('color_foreground', "#fff")
        self.color_stroke = args.get('color_stroke', "#000")
        self.on_click = args.get('on_click', None)
        self.args = args

    def set_origin(self, x, y):
        '''Move this element to the given x,y location'''
        self.graphic.x = x
        self.graphic.y = y

    def create_sprite(self):
        '''Returns a new GridElementSprite for this element's location'''
        t = GridElementSprite(self.i, self.j, self.width, self.height, **self.args)
        t.interactive = True
        t.on_click = self.on_click
        t.connect('on-render', self.on_render)
        t.connect('on-mouse-over', self.on_over)
        t.connect('on-mouse-out', self.on_out)
        if t.on_click:
            t.connect('on-click', t.on_click)
        return t

    def on_over(self, sprite):
        '''Highlight the cell element when hovering over the element'''
        self.color_foreground, self.color_stroke = self.color_stroke, self.color_foreground

    def on_out(self, sprite):
        '''Unhighlight element when mouse no longer over the element'''
        self.color_foreground, self.color_stroke = self.color_stroke, self.color_foreground

    def on_render(self, sprite):
        '''Draw the shape for this element'''
        assert False, "Override this with your own drawing code"

    @property
    def graphic(self):
        if self.__graphic is None:
            self.__graphic = self.create_sprite()
        assert(self.__graphic is not None)
        return self.__graphic


class GridElementSprite(graphics.Sprite):
    def __init__(self, i, j, width=100, height=100, color_foreground="#333",
                 color_stroke="#000", stroke_width=2):
        graphics.Sprite.__init__(self)
        self.i = i
        self.j = j
        self.width = width
        self.height = height
        self.stroke_width = stroke_width
        self.color_foreground = color_foreground
        self.color_stroke = color_stroke
        self.on_click = None


class Grid(graphics.Sprite):
    '''Infinite 2D array of grid elements'''
    def __init__(self, x_spacing=50, y_spacing=50, **kwargs):
        '''
        The x,y coordinates is the canvas location for the top left
        origin of the grid.  The x_spacing and y_spacing are the offsets
        of each subsequent grid element's location.  The spacings should
        be equal to the grid element dimensions to make a regular packed grid.
        '''
        graphics.Sprite.__init__(self, **kwargs)
        self.x_spacing = x_spacing
        self.y_spacing = y_spacing
        self.__elements = {}
        self.connect("on-render", self.on_render)

    def add(self, e):
        '''Adds an element to the grid at the element's i, j coordinate'''
        if e.i not in self.__elements.keys():
            self.__elements[e.i] = {}
        self.__elements[e.i][e.j] = e

    def get(self, i, j):
        '''Returns the element at the given i,j coordinate'''
        if (i not in self.__elements.keys() or
            j not in self.__elements[i].keys()):
            return None
        return self.__elements[i][j]

    def set(self, i, j, e):
        '''Insert element e at location i, j'''
        self.__elements[i][j] = e

    def remove(self, i, j):
        '''Delete the element at the given i, j location'''
        del self.__elements[i][j]

    def on_render(self, widget):
        '''Repopulate the grid'''
        self.clear()

        x = 0
        for column in self.__elements.values():
            y = 0
            for e in column.values():
                e.set_origin(x, y)
                e.on_render(e.graphic)
                self.add_child(e.graphic)
                y += self.y_spacing

            x += self.x_spacing

    def elements(self):
        '''Sequentially yields all grid elements'''
        for row in self.__elements.values():
            for col in row.values():
                yield col


class TriangularGridElement(GridElement):
    x_spacing_factor = 0.5
    y_spacing_factor = 1

    def set_origin(self, x,y):
        if self.i % 2 == 0:
            GridElement.set_origin(self, x, y)
        else:
            GridElement.set_origin(self, x, y+self.height)

    def on_render(self, sprite):
        sprite.graphics.clear()
        if self.i % 2 == 1:
            sprite.graphics.triangle(0,0, self.width,-1 * self.height)
        else:
            sprite.graphics.triangle(0,0, self.width,self.height)
        sprite.graphics.set_line_style(self.stroke_width)
        sprite.graphics.fill_preserve(self.color_foreground)
        sprite.graphics.stroke(self.color_stroke)

    def create_sprite(self):
        t = GridElement.create_sprite(self)
        if self.i % 2 == 1:
            t.height = -1 * t.height
        return t


class RectangularGridElement(GridElement):
    x_spacing_factor = 1
    y_spacing_factor = 1

    def set_origin(self, x,y):
        GridElement.set_origin(self, x, y)

    def on_render(self, sprite):
        sprite.graphics.clear()
        sprite.graphics.rectangle(0, 0, self.width, self.height)
        sprite.graphics.set_line_style(self.stroke_width)
        sprite.graphics.fill_preserve(self.color_foreground)
        sprite.graphics.stroke(self.color_stroke)


class HexagonalGridElement(GridElement):
    x_spacing_factor = 0.75
    y_spacing_factor = 0.866

    def set_origin(self, x, y):
        if self.i % 2 == 1:
            GridElement.set_origin(self, x, y + self.height / 2.0 * 0.866)
        else:
            GridElement.set_origin(self, x, y)

    def on_render(self, sprite):
        sprite.graphics.clear()
        sprite.graphics.hexagon(0, 0, self.height)
        sprite.graphics.set_line_style(self.stroke_width)
        sprite.graphics.fill_preserve(self.color_foreground)
        sprite.graphics.stroke(self.color_stroke)


class Scene(graphics.Scene):
    '''
    '''
    ELEMENT_CLASSES = [
        RectangularGridElement,
        HexagonalGridElement,
        TriangularGridElement,
    ]

    def __init__(self):
        graphics.Scene.__init__(self)
        self.background_color = "#333"
        self.element_number = 0
        self.size = 60
        self.margin = 30
        self.cols = 0
        self.rows = 0

        self.grid = None

        self.connect('on-mouse-over', self.on_mouse_over)
        self.connect('on-mouse-out', self.on_mouse_out)
        self.connect('on-resize', self.on_resize)


    def on_resize(self, scene, event):
        if not self.grid:
            self.create_grid(self.margin,
                             self.margin,
                             self.width - self.margin * 2,
                             self.height - self.margin * 2)

        self._resize_grid()
        self.grid.on_render(scene)

    def cols_visible(self):
        '''Calculate the number of cols that should fit in the current window dimensions'''
        return int((self.width - 2 * self.margin) / self.grid.x_spacing)

    def rows_visible(self):
        '''Calculate the number of cols that should fit in the current window dimensions'''
        return int((self.height - 2 * self.margin) / self.grid.y_spacing)

    def create_element(self, cls, i, j):
        '''Create a sprite element of type cls at the given location'''
        if j % 2 == i % 2:
            color = "#060"
        else:
            color = "#666"
        e = cls(i, j, height=self.size, width=self.size,
                color_foreground=color,
                color_stroke="#000",
                stroke_width=2)
        self.grid.add(e)

    def set_action(self, i, j, on_click):
        '''Hook a handler to the on-click event of the object at the given coordinates'''
        e = self.grid.get(i, j)
        if not e:
            return
        e.on_click = on_click
        if e.on_click:
            e.color_foreground = "#0a0"
        elif j % 2 == i % 2:
            e.color_foreground = "#060"
        else:
            e.color_foreground = "#666"

    def create_grid(self, x, y, width, height):
        '''Builds a new width x height sized grid at the given screen position'''
        self.grid = Grid(x=x, y=y)
        cls = self.ELEMENT_CLASSES[0]
        self.grid.x_spacing = self.size * cls.x_spacing_factor
        self.grid.y_spacing = self.size * cls.y_spacing_factor
        self.add_child(self.grid)

        self.cols = self.cols_visible()
        self.rows = self.rows_visible()

        for i in range(0, self.cols):
            for j in range(0, self.rows):
                self.create_element(cls, i, j)

        # Add next and forward links
        self.set_action(0, 0, self.prev_grid_type)
        self.set_action(self.cols-1, 0, self.next_grid_type)

    def _set_grid_type(self, element_number):
        '''Switch to different type of grid, and redraw'''
        self.element_number = element_number
        cls = self.ELEMENT_CLASSES[self.element_number]
        self.grid.clear()
        for e in self.grid.elements():
            new_e = cls(e.i, e.j, self.size, self.size, **e.args)
            new_e.on_click = e.on_click
            self.grid.set(e.i, e.j, new_e)

        self.grid.x_spacing = self.size * new_e.x_spacing_factor
        self.grid.y_spacing = self.size * new_e.y_spacing_factor
        self._resize_grid()
        self.grid.on_render(new_e)

    def prev_grid_type(self, widget, event):
        self._set_grid_type((self.element_number - 1) % len(self.ELEMENT_CLASSES))

    def next_grid_type(self, widget, event):
        self._set_grid_type((self.element_number + 1) % len(self.ELEMENT_CLASSES))

    def _resize_grid(self):
        '''Add or remove cols and rows to fill window'''
        cls = self.ELEMENT_CLASSES[self.element_number]

        # Remove all the links
        self.set_action(0, 0, None)
        self.set_action(self.cols-1, 0, None)

        # Resize X
        old_cols = self.cols
        new_cols = self.cols_visible()
        if new_cols > old_cols:
            # Add more columns to the grid
            for i in range(old_cols, new_cols):
                for j in range(0, self.rows):
                    self.create_element(cls, i,j)
        elif new_cols < old_cols:
            # Remove unneeded columns
            for i in range(new_cols, old_cols):
                for j in range(0, self.rows):
                    self.grid.remove(i, j)
        self.cols = new_cols

        # Resize Y
        old_rows = self.rows
        new_rows = self.rows_visible()
        if new_rows > old_rows:
            # Add more rows to the grid
            for j in range(old_rows, new_rows):
                for i in range(0, self.cols):
                    self.create_element(cls, i, j)
        elif new_rows < old_rows:
            # Remove unneeded rows
            for j in range(new_rows, old_rows):
                for i in range(0, self.cols):
                    self.grid.remove(i, j)
        self.rows = new_rows

        # Re-add links in their new locations
        self.set_action(0, 0, self.prev_grid_type)
        self.set_action(self.cols-1, 0, self.next_grid_type)

    def on_mouse_over(self, scene, sprite):
        if not sprite: return # ignore blank clicks
        if self.tweener.get_tweens(sprite): return
        tmp = sprite.color_foreground
        sprite.color_foreground = sprite.color_stroke
        sprite.color_stroke = tmp

    def on_mouse_out(self, scene, sprite):
        if not sprite: return
        tmp = sprite.color_foreground
        sprite.color_foreground = sprite.color_stroke
        sprite.color_stroke = tmp


if __name__ == '__main__':
    class BasicWindow:
        def __init__(self):
            window = gtk.Window()
            window.set_default_size(600, 600)
            window.connect("delete_event", lambda *args: gtk.main_quit())
            window.add(Scene())
            window.show_all()


    window = BasicWindow()
    import signal
    signal.signal(signal.SIGINT, signal.SIG_DFL) # gtk3 screws up ctrl+c
    gtk.main()

########NEW FILE########
__FILENAME__ = grid_layout
#!/usr/bin/env python
# - coding: utf-8 -
# Copyright (C) 2010 Toms Bauģis <toms.baugis at gmail.com>

"""Base template"""

import math

from gi.repository import Gtk as gtk
from lib import graphics
from lib import layout
from lib.pytweener import Easing


def tiles(items):
    """looks for the most rectangular grid for the given number of items,
       prefers horizontal"""
    if not items:
        return (0, 0)

    if isinstance(items, list):
        items = len(items)

    y = int(math.sqrt(items))
    x = items / y + (1 if items % y else 0)
    return (x, y)



class FiddlyBit(graphics.Sprite):
    def __init__(self, **kwargs):
        graphics.Sprite.__init__(self, **kwargs)
        self.interactive = True
        self.draggable = True

        self.connect("on-render", self.on_render)

    def on_render(self, sprite):
        self.graphics.fill_area(-10, -10, 20, 20, "#f0f")
        #self.graphics.move_to(0, -50)
        #self.graphics.line_to(0, 50)
        #self.graphics.stroke("#aaa")




class Scene(graphics.Scene):
    def __init__(self):
        graphics.Scene.__init__(self)

        base = layout.VBox()
        self.add_child(base)

        self.fiddly_bits_container = layout.VBox()
        base.add_child(self.fiddly_bits_container)

        button_box = layout.VBox(expand=False, padding=10)
        base.add_child(button_box)

        self.fiddly_bits = [FiddlyBit() for i in range(4)]
        self.populate_fiddlybits()

        self.connect("on-drag", self.on_drag_sprite)


    def on_drag_sprite(self, scene, sprite, event):
        for bit in self.fiddly_bits:
            if bit != sprite:
                bit.animate(x=sprite.x, y=sprite.y,
                            easing=Easing.Expo.ease_out)

    def gimme_mo(self, button):
        self.fiddly_bits.append(FiddlyBit())
        self.populate_fiddlybits()

    def populate_fiddlybits(self):
        self.fiddly_bits_container.clear()
        x, y = tiles(self.fiddly_bits)
        k = 0
        for i in range(y):
            box = layout.HBox()
            self.fiddly_bits_container.add_child(box)
            for j in range(x):
                internal_box = layout.HBox()
                box.add_child(internal_box)

                fixed = layout.Fixed(fill=False)
                internal_box.add_child(fixed)
                bit = self.fiddly_bits[k]
                fixed.add_child(bit)
                bit.x, bit.y = 0, 0 # addchild we do coords recalc

                k += 1
                if k >= len(self.fiddly_bits):
                    break




class BasicWindow:
    def __init__(self):
        window = gtk.Window()
        window.set_default_size(600, 500)
        window.connect("delete_event", lambda *args: gtk.main_quit())

        box = gtk.VBox(border_width=10)
        scene = Scene()
        box.pack_start(scene, True, True, 0)

        gimme_mo = gtk.Button("Gimme Mo")
        box.pack_end(gimme_mo, False, True, 0)
        gimme_mo.connect("clicked", scene.gimme_mo)
        window.add(box)

        window.show_all()

if __name__ == '__main__':
    window = BasicWindow()
    import signal
    signal.signal(signal.SIGINT, signal.SIG_DFL) # gtk3 screws up ctrl+c
    gtk.main()

########NEW FILE########
__FILENAME__ = guilloche
#!/usr/bin/env python
# - coding: utf-8 -
# Copyright (C) 2010 Toms Bauģis <toms.baugis at gmail.com>
""" guilloches, following.  observe how detail grows and your cpu melts.
    move mouse horizontally and vertically to change parameters
    http://ministryoftype.co.uk/words/article/guilloches/
"""

from gi.repository import Gtk as gtk
from lib import graphics

import math


class Scene(graphics.Scene):
    def __init__(self):
        graphics.Scene.__init__(self)

        self.theta_step = 0.01
        self.R = 60 # big steps
        self.r = 0.08 # little steps
        self.p = 35 # size of the ring
        self.connect("on-mouse-move", self.on_mouse_move)
        self.connect("on-enter-frame", self.on_enter_frame)

    def on_mouse_move(self, area, event):
        self.R = event.x / float(self.width) * 50
        self.r = event.y / float(self.height) * 0.08


    def on_enter_frame(self, scene, context):
        R, r, p = self.R, self.r, self.p

        theta = 0

        context.set_source_rgb(0, 0, 0)
        context.set_line_width(0.2)

        first = True
        while theta < 2 * math.pi:
            theta += self.theta_step
            x = (R + r) * math.cos(theta) + (r + p) * math.cos((R+r)/r * theta)
            y = (R + r) * math.sin(theta) + (r + p) * math.sin((R+r)/r * theta)

            x = x * 4 + self.width / 2
            y = y * 4 + self.height / 2
            if first:
                context.move_to(x, y)
                first = False

            context.line_to(x, y)

        context.stroke()

        self.theta_step = self.theta_step - 0.0000002
        self.redraw()



class BasicWindow:
    def __init__(self):
        window = gtk.Window()
        window.set_size_request(600, 600)
        window.connect("delete_event", lambda *args: gtk.main_quit())

        window.add(Scene())
        window.show_all()


if __name__ == "__main__":
    example = BasicWindow()
    import signal
    signal.signal(signal.SIGINT, signal.SIG_DFL) # gtk3 screws up ctrl+c
    gtk.main()

########NEW FILE########
__FILENAME__ = hamster_brains1
#!/usr/bin/env python
# - coding: utf-8 -
# Copyright (C) 2014 Toms Baugis <toms.baugis@gmail.com>

"""Base template"""
import datetime as dt

from gi.repository import Gtk as gtk
from gi.repository import GObject as gobject

from collections import defaultdict

from lib import graphics
from lib import layout

from hamster.client import Storage
from hamster_stats import Stats, minutes


class SparkBars(layout.Widget):
    def __init__(self, items=None, width = None, height=None, color=None, gap=1, **kwargs):
        layout.Widget.__init__(self, **kwargs)

        self.width = width or 100
        self.height = height or 20
        self.bar_width = 10
        self.gap = gap
        self.color = color or "#777"
        self.items = items or []

        self.connect("on-render", self.on_render)


    def on_render(self, sprite):
        # simplify math by rolling down to the bottom
        self.graphics.save_context()
        self.graphics.translate(0, self.height)

        max_width = min(self.width, len(self.items) * (self.bar_width + self.gap))
        pixels = graphics.full_pixels(max_width, [1] * len(self.items), self.gap)

        max_val = max(self.items)

        for val, width in zip(self.items, pixels):
            height = max(1, round(val * 1.0 / max_val * self.height))

            self.graphics.rectangle(0, 0, width, -height)
            self.graphics.translate(width + self.gap, 0)
        self.graphics.fill(self.color)

        self.graphics.restore_context()


class Scene(graphics.Scene):
    def __init__(self):
        graphics.Scene.__init__(self)
        self.storage = Storage()

        self._load_end_date = dt.datetime.now()
        self.facts = []

        self.label = layout.Label("Loading...", y=100,
                                    color="#666",
                                    size=50)
        self.add_child(layout.VBox(self.label))

        gobject.timeout_add(10, self.load_facts)


    def load_facts(self):
        # chunk size
        end = self._load_end_date
        start = end - dt.timedelta(days=30)
        self.facts = self.storage.get_facts(start, end) + self.facts

        self._load_end_date = start - dt.timedelta(days=1)

        # limiter
        if end > dt.datetime.now() - dt.timedelta(days=565):
            self.label.text = "Loading %d..." % len(self.facts)
            gobject.timeout_add(10, self.load_facts)
        else:
            self.on_facts_loaded()

    def on_facts_loaded(self):
        self.clear()
        main = layout.VBox(padding=10, spacing=10)
        self.add_child(main)

        first_row = layout.HBox(spacing=10, expand=False)
        main.add_child(first_row)

        # add sparkbars of activity by weekday
        row = layout.HBox([layout.VBox(spacing=20, expand=False),
                                       layout.VBox(spacing=15, expand=False),
                                       layout.VBox(spacing=15)
                           ], spacing=20)
        first_row.add_child(row)

        row[0].add_child(layout.Label("Category", expand=False, x_align=0))
        row[1].add_child(layout.Label("Weekdays", expand=False, x_align=0))
        row[2].add_child(layout.Label("By week", expand=False, x_align=0))
        self._add_stats(row, lambda fact: (fact.category, ""))

        row[0].add_child(layout.Label("Activity", expand=False, x_align=0, margin_top=20))
        row[1].add_child(layout.Label("Weekdays", expand=False, x_align=0, margin_top=20))
        row[2].add_child(layout.Label("By week", expand=False, x_align=0, margin_top=20))
        self._add_stats(row, lambda fact: (fact.category, fact.activity))



    def _add_stats(self, container, toplevel_group):
        stats = Stats(self.facts, toplevel_group)
        by_week = stats.by_week()

        # group by weekday
        by_weekday = stats.by_weekday()

        # group by workday / holiday
        by_work_hobby = stats.group(lambda fact: "weekend" if fact.date.weekday() in  (5, 6) else "workday")
        for activity, group in by_work_hobby.iteritems():
            work, non_work = group.get("workday", []), group.get("weekend", [])
            total = minutes(work) + minutes(non_work)
            by_work_hobby[activity] = "workday" if minutes(work) / total > 0.8 and len(work) > 10 else "other"



        for activity in sorted(stats.groups.keys()):
            label = layout.Label("%s@%s" % (activity[1], activity[0]),
                                 color="#333",
                                 size=12, x_align=0, y_align=0.5)
            label.max_width = 150
            container[0].add_child(label)

            if by_work_hobby[activity] == "workday":
                color = graphics.Colors.category10[0]
            else:
                color = graphics.Colors.category10[2]

            hours = [rec for rec in by_weekday[activity]]
            container[1].add_child(SparkBars(hours, color=color))

            weeks = by_week[activity]
            container[2].add_child(SparkBars(weeks, width=200, color=color))





class BasicWindow:
    def __init__(self):
        window = gtk.Window()
        window.set_default_size(600, 500)
        window.connect("delete_event", lambda *args: gtk.main_quit())
        window.add(Scene())
        window.show_all()


if __name__ == '__main__':
    window = BasicWindow()
    import signal
    signal.signal(signal.SIGINT, signal.SIG_DFL) # gtk3 screws up ctrl+c
    gtk.main()

########NEW FILE########
__FILENAME__ = hamster_brains2
#!/usr/bin/env python
# - coding: utf-8 -
# Copyright (C) 2014 Toms Baugis <toms.baugis@gmail.com>

"""Base template"""
import datetime as dt
import itertools

from gi.repository import Gtk as gtk
from gi.repository import GObject as gobject

from collections import defaultdict

from lib import graphics
from lib import layout

from hamster.client import Storage
from hamster_stats import Stats, minutes



class SparkBars(layout.Widget):
    def __init__(self, items=None, width = None, height=None, **kwargs):
        layout.Widget.__init__(self, **kwargs)

        self.width = width or 100
        self.height = height or 20
        self.bar_width = 10
        self.fill_color = "#777"
        self.items = items or []

        self.connect("on-render", self.on_render)


    def on_render(self, sprite):
        # simplify math by rolling down to the bottom
        self.graphics.save_context()
        self.graphics.translate(0, self.height)

        gap = 1

        max_width = min(self.width, len(self.items) * (self.bar_width + gap))
        pixels = graphics.full_pixels(max_width, [1] * len(self.items), gap)

        max_val = max(self.items)

        for val, width in zip(self.items, pixels):
            height = max(1, round(val * 1.0 / max_val * self.height))

            self.graphics.rectangle(0, 0, width, -height)
            self.graphics.translate(width + gap, 0)
        self.graphics.fill(self.fill_color)

        self.graphics.restore_context()


class Scene(graphics.Scene):
    def __init__(self):
        graphics.Scene.__init__(self)
        self.storage = Storage()

        self._load_end_date = dt.datetime.now()
        self.facts = []

        self.label = layout.Label("Loading...", y=100,
                                    color="#666",
                                    size=50)
        self.add_child(layout.VBox(self.label))

        gobject.timeout_add(10, self.load_facts)


    def load_facts(self):
        # chunk size
        end = self._load_end_date
        start = end - dt.timedelta(days=30)
        self.facts = self.storage.get_facts(start, end) + self.facts

        self._load_end_date = start - dt.timedelta(days=1)

        # limiter
        if end > dt.datetime.now() - dt.timedelta(days=365):
            self.label.text = "Loading %d..." % len(self.facts)
            gobject.timeout_add(10, self.load_facts)
        else:
            self.on_facts_loaded()


    def on_facts_loaded(self):
        stats = Stats(self.facts, lambda fact: (fact.category, fact.activity))
        by_hour = stats.by_hour()


        self.clear()
        main = layout.VBox(padding=10, spacing=10)
        self.add_child(main)

        first_row = layout.HBox(spacing=10, expand=False)
        main.add_child(first_row)

        activity_weekdays = layout.HBox([layout.VBox(spacing=15, expand=False),
                                         layout.VBox(spacing=15, expand=False),
                                         layout.VBox(spacing=15)
                                        ], spacing=20)
        first_row.add_child(activity_weekdays)

        activity_weekdays[0].add_child(layout.Label("Activity", expand=False, x_align=0))
        activity_weekdays[1].add_child(layout.Label("Hour of the day", expand=False, x_align=0))


        for activity in sorted(stats.groups.keys()):
            label = layout.Label("%s@%s" % (activity[1], activity[0]),
                                 color="#333", size=12, x_align=0, y_align=0.5)
            label.max_width = 150
            activity_weekdays[0].add_child(label)
            activity_weekdays[1].add_child(SparkBars(by_hour[activity], 150))


class BasicWindow:
    def __init__(self):
        window = gtk.Window()
        window.set_default_size(600, 500)
        window.connect("delete_event", lambda *args: gtk.main_quit())
        window.add(Scene())
        window.show_all()


if __name__ == '__main__':
    window = BasicWindow()
    import signal
    signal.signal(signal.SIGINT, signal.SIG_DFL) # gtk3 screws up ctrl+c
    gtk.main()

########NEW FILE########
__FILENAME__ = hamster_day
#!/usr/bin/env python
# - coding: utf-8 -
# Copyright (C) 2012 Toms Bauģis <toms.baugis at gmail.com>

"""Potential edit activities replacement"""

from gi.repository import Gtk as gtk
from gi.repository import Gdk as gdk
from gi.repository import GObject as gobject

from lib import graphics
import hamster.client
from hamster.lib import stuff
from hamster import widgets


import datetime as dt

colors = ["#95CACF", "#A2CFB6", "#D1DEA1", "#E4C384", "#DE9F7B"]
connector_colors = ["#51868C", "#76A68B", "#ADBF69", "#D9A648", "#BF6A39"]
entry_colors = ["#95CACF", "#A2CFB6", "#D1DEA1", "#E4C384", "#DE9F7B"]

fact_names = []


def delta_minutes(start, end):
    end = end or dt.datetime.now()
    return (end - start).days * 24 * 60 + (end - start).seconds / 60

class Container(graphics.Sprite):
    def __init__(self, width = 100, **kwargs):
        graphics.Sprite.__init__(self, **kwargs)
        self.width = width

        self.connect("on-render", self.on_render)

    def on_render(self, sprite):
        self.graphics.rectangle(0, 0, self.width, 500)
        self.graphics.fill("#fff")


class Entry(graphics.Sprite):
    __gsignals__ = {
        #: fires when any of the child widgets are clicked
        "on-activate": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
    }

    def __init__(self, width, fact, color, **kwargs):
        graphics.Sprite.__init__(self, **kwargs)
        self.width = width
        self.height = 27
        self.natural_height = 27
        self.fact = fact
        self.color = color

        self.interactive = True
        self.mouse_cursor = gdk.CursorType.XTERM

        self.fact_labels = graphics.Sprite()

        self.start_label = graphics.Label("", color="#333", size=11, x=10, y=5, interactive=True,
                                          mouse_cursor=gdk.CursorType.XTERM)
        self.start_label.text = "%s - " % fact.start_time.strftime("%H:%M")
        self.fact_labels.add_child(self.start_label)

        self.end_label = graphics.Label("", color="#333", size=11, x=65, y=5, interactive=True,
                                        mouse_cursor=gdk.CursorType.XTERM)
        if fact.end_time:
            self.end_label.text = fact.end_time.strftime("%H:%M")
        self.fact_labels.add_child(self.end_label)

        self.activity_label = graphics.Label(fact.activity, color="#333", size=11, x=120, y=5, interactive=True,
                                             mouse_cursor=gdk.CursorType.XTERM)
        self.fact_labels.add_child(self.activity_label)

        self.category_label = graphics.Label("", color="#333", size=9, y=7, interactive=True,
                                             mouse_cursor=gdk.CursorType.XTERM)
        self.category_label.text = stuff.escape_pango(" - %s" % fact.category)
        self.category_label.x = self.activity_label.x + self.activity_label.width
        self.fact_labels.add_child(self.category_label)


        self.duration_label = graphics.Label(stuff.format_duration(fact.delta), size=11, color="#333", interactive=True,
                                             mouse_cursor=gdk.CursorType.XTERM)
        self.duration_label.x = self.width - self.duration_label.width - 5
        self.duration_label.y = 5
        self.fact_labels.add_child(self.duration_label)

        self.add_child(self.fact_labels)

        self.edit_links = graphics.Sprite(x=10, y = 110, opacity=0)

        self.delete_link = graphics.Label("Delete", size=11, color="#555", interactive=True)
        self.save_link = graphics.Label("Save", size=11, x=390, color="#555", interactive=True)
        self.cancel_link = graphics.Label("Cancel", size=11, x=440, color="#555", interactive=True)
        self.edit_links.add_child(self.delete_link, self.save_link, self.cancel_link)

        self.add_child(self.edit_links)

        for sprite in self.fact_labels.sprites:
            sprite.connect("on-click", self.on_sprite_click)

        self.connect("on-render", self.on_render)
        self.connect("on-click", self.on_click)

    def on_sprite_click(self, sprite, event):
        self.emit("on-activate", sprite)

    def on_click(self, sprite, event):
        self.emit("on-activate", self.activity_label)

    def set_edit(self, edit_mode):
        self.edit_mode = edit_mode
        if edit_mode:
            self.fact_labels.animate(opacity=0)
            self.edit_links.animate(opacity=1)
        else:
            self.fact_labels.animate(opacity=1)
            self.edit_links.animate(opacity=0)

    def on_render(self, sprite):
        self.graphics.rectangle(0, 0, self.width, self.height)
        self.graphics.fill_preserve(self.color)
        self.graphics.clip()



class Scene(graphics.Scene):
    def __init__(self):
        graphics.Scene.__init__(self)

        self.tweener.default_duration = 0.1

        self.total_hours = 24
        self.height = 500
        self.pixels_in_minute =  float(self.height) / (self.total_hours * 60)

        self.spacing = 1

        self.fact_list = graphics.Sprite(x=40, y=50)
        self.add_child(self.fact_list)

        self.fragments = Container(30)

        self.connectors = graphics.Sprite(x=self.fragments.x + self.fragments.width)
        self.connectors.width = 30

        self.entries = Container(500, x=self.connectors.x + self.connectors.width)

        self.fact_list.add_child(self.fragments, self.connectors, self.entries)

        self.storage = hamster.client.Storage()

        self._date = dt.datetime.combine(dt.date.today(), dt.time()) + dt.timedelta(hours=5)


        self.date_label = graphics.Label("", size=18, y = 10, color="#444")
        self.add_child(self.date_label)


        self.entry_positions = []

        self.set_size_request(610, 500)

        self.current_entry = None

        self.connect("on-enter-frame", self.on_enter_frame)


    def render_facts(self, date = None):
        date = date or self._date

        self.container.edit_box.hide()
        facts = self.storage.get_facts(date)
        self.fragments.sprites = []
        self.connectors.sprites = []
        self.entries.sprites = []

        self.date_label.text = date.strftime("%d. %b %Y")

        for i, fact in enumerate(facts):
            if fact.activity not in fact_names:
                fact_names.append(fact.activity)

            color_index = fact_names.index(fact.activity) % len(colors)
            color = colors[color_index]

            fragment_height = int(delta_minutes(fact.start_time, fact.end_time) * self.pixels_in_minute)
            self.fragments.add_child(graphics.Rectangle(self.fragments.width, fragment_height, fill=color))

            entry = Entry(self.entries.width, fact, entry_colors[color_index])
            self.entries.add_child(entry)
            entry.connect("on-activate", self.on_entry_click)

        self.position_entries(date)


    def position_entries(self, date):
        entry_y = 0

        for fragment, entry in zip(self.fragments.sprites, self.entries.sprites):
            fragment.y = int(delta_minutes(date, entry.fact.start_time) * self.pixels_in_minute)

            entry.y = entry_y
            entry_y += entry.height


        # then try centering them with the fragments
        for entry in reversed(self.entries.sprites):
            idx = self.entries.sprites.index(entry)
            fragment = self.fragments.sprites[idx]

            min_y = 0
            if idx > 0:
                prev_sprite = self.entries.sprites[idx-1]
                min_y = prev_sprite.y + prev_sprite.height + 1

            entry.y = fragment.y + (fragment.height - entry.height) / 2
            entry.y = max(entry.y, min_y)

            if idx < len(self.entries.sprites) - 1:
                next_sprite = self.entries.sprites[idx+1]
                max_y = next_sprite.y - entry.height - self.spacing

                entry.y = min(entry.y, max_y)

        self.entry_positions = [entry.y for entry in self.entries.sprites]
        self.draw_connectors()


    def on_entry_click(self, clicked_entry, target):
        self.select(clicked_entry, target)

    def select(self, clicked_entry, target):
        prev_entry = None
        #self.container.edit_box.hide()
        idx = self.entries.sprites.index(clicked_entry)

        def get(widget_name):
            return getattr(self.container, widget_name)


        def on_update(sprite):
            self.draw_connectors()

            if sprite.height < 65 and prev_entry:
                sprite = prev_entry
            else:
                if self.current_entry != clicked_entry:
                    self.current_entry = clicked_entry
                    clicked_entry.set_edit(True)
                    if prev_entry:
                        prev_entry.set_edit(False)


                show_edit(clicked_entry)


            scene_y = int(sprite.parent.to_scene_coords(0, sprite.y)[1])
            self.container.fixed.move(self.container.edit_box, 100, scene_y)
            self.container.edit_box.set_size_request(int(sprite.width - 10), int(sprite.height))

            get("edit_box").set_visible(sprite.height > 35)
            get("description_entry").set_visible(sprite.height > 65)


        def on_complete(sprite):
            self.draw_connectors()

            clicks = {clicked_entry.start_label: "start_entry",
                      clicked_entry.end_label: "end_entry",
                      clicked_entry.activity_label: "activity_entry",
                      clicked_entry.category_label: "activity_entry",
                      clicked_entry.duration_label: "activity_entry",
            }
            get(clicks[target]).grab_focus()



        def show_edit(entry):
            get("start_entry").set_time(entry.fact.start_time)
            get("end_entry").set_start_time(entry.fact.start_time)
            if entry.fact.end_time:
                get("end_entry").set_time(entry.fact.end_time)
            get("activity_entry").set_text("%s@%s" % (entry.fact.activity, entry.fact.category))
            get("tags_entry").set_text(", ".join(entry.fact.tags))
            get("description_entry").set_text(entry.fact.description or "")

            scene_y = int(clicked_entry.parent.to_scene_coords(0, clicked_entry.y)[1])
            self.container.fixed.move(self.container.edit_box, 100, scene_y)



        for entry in self.entries.sprites:
            if entry != clicked_entry and entry.height != entry.natural_height:
                prev_entry = entry
                entry.animate(height = entry.natural_height)


        target_height = 135
        fragment = self.fragments.sprites[idx]
        y = fragment.y + (fragment.height - target_height) / 2




        clicked_entry.animate(height=target_height, y=y,
                              on_update=on_update,
                              on_complete=on_complete)

        # entries above current move upwards when necessary
        prev_entries = self.entries.sprites[:idx]
        max_y = y - 1
        for entry in reversed(prev_entries):
            pos = self.entry_positions[self.entries.sprites.index(entry)]
            target_y = min(pos, max_y - entry.natural_height)
            entry.animate(y=target_y)
            max_y = max_y - entry.natural_height - 1


        # entries below current move down when necessary
        next_entries = self.entries.sprites[idx+1:]
        min_y = y + target_height + 1
        for entry in next_entries:
            pos = self.entry_positions[self.entries.sprites.index(entry)]
            target_y = max(pos, min_y)
            entry.animate(y = target_y)
            min_y += entry.natural_height + 1



    def draw_connectors(self):
        # draw connectors
        g = self.connectors.graphics
        g.clear()
        g.set_line_style(width=1)
        g.clear()

        for fragment, entry in zip(self.fragments.sprites, self.entries.sprites):
            x2 = self.connectors.width

            g.move_to(0, fragment.y)
            g.line_to([(x2, entry.y),
                       (x2, entry.y + entry.height),
                       (0, fragment.y + fragment.height),
                       (0, fragment.y)])
            g.fill(connector_colors[colors.index(fragment.fill)])



    def on_enter_frame(self, scene, context):
        g = graphics.Graphics(context)
        for i in range (self.total_hours):
            hour = self._date + dt.timedelta(hours=i)
            y = delta_minutes(self._date, hour) * self.pixels_in_minute
            g.move_to(0, self.fact_list.y + y)
            g.show_label(hour.strftime("%H:%M"), 10, "#666")




class BasicWindow:
    def __init__(self):
        window = gtk.Window()
        window.set_default_size(600, 500)
        window.connect("delete_event", lambda *args: gtk.main_quit())

        vbox = gtk.VBox(spacing=10)
        vbox.set_border_width(12)
        self.scene = Scene()

        self.fixed = gtk.Fixed()
        self.fixed.put(self.scene, 0, 0)

        self.scene.container = self


        self.edit_box = gtk.HBox()
        self.edit_box.set_border_width(6)
        self.fixed.put(self.edit_box, 100, 0)


        container = gtk.HBox(spacing=5)
        self.edit_box.add(container)

        start_entry = widgets.TimeInput()
        self.start_entry = start_entry
        box = gtk.VBox()
        box.add(start_entry)
        container.add(box)

        end_entry = widgets.TimeInput()
        self.end_entry = end_entry
        box = gtk.VBox()
        box.add(end_entry)
        container.add(box)

        entry_box = gtk.VBox(spacing=5)
        container.add(entry_box)

        activity_entry = widgets.ActivityEntry()
        activity_entry.set_width_chars(35)
        self.activity_entry = activity_entry
        entry_box.add(activity_entry)

        tags_entry = widgets.TagsEntry()
        self.tags_entry = tags_entry
        entry_box.add(tags_entry)

        description_entry = gtk.Entry()
        description_entry.set_width_chars(35)
        self.description_entry = description_entry
        entry_box.add(description_entry)

        save_button = gtk.Button("Save")
        entry_box.add(save_button)


        container.add(gtk.HBox())
        vbox.add(self.fixed)

        button_box = gtk.HBox(spacing=5)
        vbox.add(button_box)
        window.add(vbox)

        prev_day = gtk.Button("Previous day")
        next_day = gtk.Button("Next day")
        button_box.add(gtk.HBox())
        button_box.add(prev_day)
        button_box.add(next_day)

        prev_day.connect("clicked", self.on_prev_day_click)
        next_day.connect("clicked", self.on_next_day_click)

        self.scene.render_facts()

        window.show_all()
        self.edit_box.hide()

    def on_prev_day_click(self, button):
        self.scene._date -= dt.timedelta(days=1)
        self.scene.render_facts()

    def on_next_day_click(self, button):
        self.scene._date += dt.timedelta(days=1)
        self.scene.render_facts()

if __name__ == '__main__':
    from hamster.lib import i18n
    i18n.setup_i18n()

    window = BasicWindow()
    import signal
    signal.signal(signal.SIGINT, signal.SIG_DFL) # gtk3 screws up ctrl+c
    gtk.main()

########NEW FILE########
__FILENAME__ = hamster_spiral
#!/usr/bin/env python
# - coding: utf-8 -
# Copyright (C) 2010 Toms Bauģis <toms.baugis at gmail.com>

"""Base template"""


from gi.repository import Gtk as gtk
from gi.repository import Gdk as gdk
from lib import graphics, pytweener
import math
import hamster.client
import datetime as dt
from collections import defaultdict
import itertools


class TimeRing(graphics.Sprite):
    def __init__(self, days, start_date, fill):
        graphics.Sprite.__init__(self, interactive = False)
        self.days = days
        self.start_date = start_date

        self.end_date = max([day for day, hours in self.days])

        self.fill = fill

        self.width = 45
        self.height = 15
        self.min_radius = 35

        self.connect("on-render", self.on_render)


    def on_render(self, sprite):
        self.graphics.clear()
        start_date = dt.date(2010, 1, 1) #dt.datetime.today()
        step = (360 / 364.0 / 180 * math.pi)

        height = self.height

        for i in range((self.end_date - self.start_date).days):
            day = i
            angle = day * step - math.pi / 2  # -math.pi is so that we start at 12'o'clock instead of 3
            distance = float(day) / 365 * self.width + self.min_radius

            self.graphics.line_to(math.cos(angle) * (distance + height / 2),
                                  math.sin(angle) * (distance + height / 2))

        self.graphics.set_line_style(width = height * 1)
        self.graphics.stroke(self.fill, 0.05)


        for day, hours in self.days:
            delta_days = (day - self.start_date).days
            if delta_days < 0:
                continue




            angle = delta_days * step - math.pi / 2  # -math.pi is so that we start at 12'o'clock instead of 3

            distance = float(delta_days) / 365 * self.width + self.min_radius

            #self.graphics.move_to(0, 0)
            #height = hours / 12.0 * self.height
            height = self.height

            self.graphics.move_to(math.cos(angle) * distance,
                                  math.sin(angle) * distance)
            self.graphics.line_to(math.cos(angle) * (distance + height),
                                  math.sin(angle) * (distance + height))


            self.graphics.line_to(math.cos(angle+step) * (distance + height),
                                  math.sin(angle+step) * (distance + height))

            self.graphics.line_to(math.cos(angle+step) * distance,
                                  math.sin(angle+step) * distance)
            self.graphics.close_path()

        self.graphics.fill(self.fill)


class Scene(graphics.Scene):
    def __init__(self):
        graphics.Scene.__init__(self)

        storage = hamster.client.Storage()

        self.day_counts = {}
        categories = defaultdict(int)

        self.colors = ("#20b6de", "#fff", "#333", "#ff0", "#0ff", "#aaa")

        self.container = graphics.Sprite()
        self.add_child(self.container)

        self.start_date_label = graphics.Label(color = "#000")
        self.add_child(self.start_date_label)


        facts = storage.get_facts(dt.date(2006,1,1), dt.datetime.now())
        facts_per_category = defaultdict(list)
        categories = defaultdict(int)

        #facts = [fact for fact in facts if fact.category in ('work', 'hacking')]

        for category, facts in itertools.groupby(sorted(facts, key=lambda fact:fact.category), lambda fact:fact.category):
            for day, day_facts in itertools.groupby(sorted(facts, key=lambda fact:fact.date), lambda fact:fact.date):
                delta = dt.timedelta()
                for fact in day_facts:
                    delta += fact.delta
                delta = delta.seconds / 60 / 60 + delta.days * 24

                facts_per_category[category].append((day, delta))

            categories[category] += 1


        self.categories = categories.keys()


        self.spirals = []
        self.start_date = dt.date(2006, 1, 1)

        for i, category in enumerate(categories):
            ring = TimeRing(facts_per_category[category],
                            self.start_date,
                            self.colors[i + 1])
            ring.min_radius = i * 20 + 0
            ring.width = len(self.categories) * 30

            #self.animate(ring, 3, width = len(self.categories) * 30, easing = pytweener.Easing.Expo.ease_out)
            self.container.add_child(ring)
            self.spirals.append(ring)

        self.connect("on-enter-frame", self.on_enter_frame)
        self.connect("on-mouse-move", self.on_mouse_move)
        self.connect("on-mouse-scroll", self.on_scroll)


    def on_scroll(self, scene, event):
        if event.direction == gdk.ScrollDirection.UP:
            self.start_date -= dt.timedelta(days = 7)
        elif event.direction == gdk.ScrollDirection.DOWN:
            self.start_date += dt.timedelta(days = 7)
        else:
            print "other scroll"

        for spiral in self.spirals:
            spiral.start_date = self.start_date

        self.redraw()

    def on_mouse_move(self, scene, event):
        self.redraw()

    def on_enter_frame(self, scene, context):
        g = graphics.Graphics(context)
        g.fill_area(0, 0, self.width, self.height, self.colors[0])

        self.container.x = self.width / 2
        self.container.y = self.height / 2

        #print self.start_date.strftime("%d %b, %Y")
        self.start_date_label.text = self.start_date.strftime("%d %b, %Y")
        self.start_date_label.x = self.width / 2 - self.start_date_label.width
        self.start_date_label.y = self.height / 2

        g.move_to(self.width / 2, self.height / 2)
        g.line_to(self.mouse_x, self.mouse_y)
        g.set_line_style(width=0.5)
        g.stroke("#fff")





class BasicWindow:
    def __init__(self):
        window = gtk.Window()
        window.set_size_request(700, 600)
        window.connect("delete_event", lambda *args: gtk.main_quit())
        window.add(Scene())
        window.show_all()


example = BasicWindow()
import signal
signal.signal(signal.SIGINT, signal.SIG_DFL) # gtk3 screws up ctrl+c
gtk.main()

########NEW FILE########
__FILENAME__ = hamster_stats
import datetime as dt
import itertools

from collections import defaultdict


def minutes(facts):
    time = dt.timedelta()
    for fact in facts:
        time += fact.delta
    return time.total_seconds() / 60.0

class Stats(object):
    def __init__(self, facts, toplevel_group=None):
        self.groups = None # we run top-level groups on first call
        self.toplevel_group = toplevel_group
        self._facts = facts

        self._range_start = None
        self._range_end = None
        self._update_groups()


    @property
    def facts(self):
        return self._facts

    @facts.setter
    def set_facts(self, facts):
        self._facts = facts
        self._update_groups()

    def _update_groups(self):
        for fact in self.facts:
            self._range_start = min(fact.date, self._range_start or fact.date)
            self._range_end = max(fact.date, self._range_end or fact.date)

        if not self.toplevel_group:
            # in case when we have no grouping, we are looking for totals
            self.groups = facts
        else:
            key_func = self.toplevel_group
            self.groups = {key: list(facts) for key, facts in
                               itertools.groupby(sorted(self.facts, key=key_func), key_func)}


    def group(self, key_func):
        # return the nested thing
        res = {}
        for key, facts in self.groups.iteritems():
            res[key] = {nested_key: list(nested_facts) for nested_key, nested_facts in
                         itertools.groupby(sorted(facts, key=key_func), key_func)}
        return res



    def by_week(self):
        """return series by week, fills gaps"""
        year_week = lambda date: (date.year, int(date.strftime("%W")))

        weeks = []
        start, end = self._range_start, self._range_end
        for i in range(0, (end - start).days, 7):
            weeks.append(year_week(start + dt.timedelta(days=i)))

        # group and then fill gaps and turn into a list
        res = self.group(lambda fact: year_week(fact.date))
        for key, group in res.iteritems():
            res[key] = [minutes(group.get(week, [])) for week in weeks]

        return res


    def by_weekday(self):
        """return series by weekday, fills gaps"""
        res = self.group(lambda fact: fact.date.weekday())
        for key, group in res.iteritems():
            res[key] = [minutes(group.get(weekday, [])) for weekday in range(7)]
        return res


    def by_hour(self):
        """return series by hour, stretched for the duration"""
        res = defaultdict(lambda: defaultdict(float))
        for key, facts in self.groups.iteritems():
            for fact in facts:
                minutes = fact.delta.total_seconds() / 60.0
                hours = int(minutes // 60)
                minutes = round(minutes - hours * 60)

                for i in range(hours):
                    res[key][(fact.start_time + dt.timedelta(hours=i)).hour] += 1

                res[key][(fact.start_time + dt.timedelta(hours=hours)).hour] += minutes / 60.0

        hours = range(24)
        hours = hours[6:] + hours[:6]
        for key in res.keys():
            res[key] = [res[key][i] for i in hours]

        return res

    def sum_durations(self, keys):
        """returns summed durations of the specified keys iterable"""
        res = []
        for key in keys:
            res_delta = dt.timedelta()
            for fact in (facts_dict.get(key) or []):
                res_delta += fact.delta
            res.append(round(res_delta.total_seconds() / 60.0))
        return res

########NEW FILE########
__FILENAME__ = hamster_sun
#!/usr/bin/env python
# - coding: utf-8 -
# Copyright (C) 2010 Toms Bauģis <toms.baugis at gmail.com>

"""Base template"""


from gi.repository import Gtk as gtk
from lib import graphics
import math
import hamster.client
import datetime as dt
from collections import defaultdict
import itertools


class Chart(graphics.Sprite):
    def __init__(self):
        graphics.Sprite.__init__(self, interactive = False)

    def do_stuff(self, years, categories):
        step = (360.0 / 365) * math.pi / 180.0

        g = self.graphics


        g.set_color("#999")
        g.set_line_style(width = 1)


        # em
        colors = ["#009966", "#33cc00", "#9933cc", "#aaaaaa", "#ff9999", "#99cccc"]
        colors.reverse()

        # em contrast
        colors = ["#00a05f", "#1ee100", "#a0a000", "#ffa000", "#a01ee1", "#a0a0a0", "#ffa0a0", "#a0e1e1"]
        colors.reverse()


        # tango light
        colors = ["#fce94f", "#89e034", "#fcaf3e", "#729fcf", "#ad7fa8", "#e9b96e", "#ef2929", "#eeeeec", "#888a85"]

        # tango medium
        colors =["#edd400", "#73d216", "#f57900", "#3465a4", "#75507b", "#c17d11", "#cc0000", "#d3d7cf", "#555753"]
        #colors = colors[1:]


        #colors = ("#ff0000", "#00ff00", "#0000ff", "#aaa000")


        hour_step = 15
        spacing = 20
        current_pixel = 1220

        g.set_line_style(width = 1)
        g.circle(0, 0, current_pixel - 2)
        g.stroke("#fff", 0.2)
        g.set_line_style(width=1)

        for year in sorted(years.keys()):
            for category in categories:
                ring_height = hour_step * 3

                for day, hours in years[year][category]:
                    year_day = day.isocalendar()[1] * 7 + day.weekday()
                    angle = year_day * step - math.pi / 2

                    distance = current_pixel

                    height = ring_height


                    #bar per category
                    g.move_to(math.cos(angle) * distance + 0,
                              math.sin(angle) * distance + 0)
                    g.line_to(math.cos(angle) * (distance + height),
                              math.sin(angle) * (distance + height))

                    g.line_to(math.cos(angle+step) * (distance + height),
                              math.sin(angle+step) * (distance + height))

                    g.line_to(math.cos(angle+step) * distance,
                              math.sin(angle+step) * distance)
                    g.close_path()

                if years[year][category]:
                    current_pixel += ring_height + 7 + spacing

                color = "#fff" #colors[categories.index(category)]
                g.set_color(color)
                g.fill()

            current_pixel += spacing * 3


            g.set_line_style(width = 4)
            g.circle(0, 0, current_pixel - spacing * 2)
            g.stroke("#fff", 0.5)

            current_pixel += 3





class Scene(graphics.Scene):
    def __init__(self):
        graphics.Scene.__init__(self)


        storage = hamster.client.Storage()

        self.facts = storage.get_facts(dt.date(2009,1,1), dt.date(2009,12,31))
        print len(self.facts)

        self.day_counts = {}
        categories = defaultdict(int)


        self.years = {}
        for year, facts in itertools.groupby(sorted(self.facts, key=lambda fact:fact.date), lambda fact:fact.date.year):
            self.years[year] = defaultdict(list)
            for category, category_facts in itertools.groupby(sorted(facts, key=lambda fact:fact.category), lambda fact:fact.category):
                for day, day_facts in itertools.groupby(sorted(category_facts, key=lambda fact:fact.date), lambda fact:fact.date):
                    delta = dt.timedelta()
                    for fact in day_facts:
                        delta += fact.delta
                    delta = delta.seconds / 60 / 60 + delta.days * 24

                    self.years[year][category].append((day, delta))

                categories[category] += 1

        self.categories = categories.keys()


        self.chart = Chart()

        self.add_child(self.chart)

        self.chart.do_stuff(self.years, self.categories)

        self.connect("on-enter-frame", self.on_enter_frame)
        self.connect("on-mouse-move", self.on_mouse_move)

        #self.animate(self.chart, rotation=math.pi * 2, duration = 3)

    def on_mouse_move(self, scene, event):
        x, y = self.width / 2, self.height / 2

        max_distance = math.sqrt((self.width / 2) ** 2 + (self.height / 2) ** 2)

        distance = math.sqrt((x - event.x) ** 2 + (y - event.y) ** 2)

        #self.chart.scale_x = 2 - 2 * (distance / float(max_distance))
        #self.chart.scale_y = 2 - 2 * (distance / float(max_distance))
        #self.redraw()

    def on_enter_frame(self, scene, context):
        g = graphics.Graphics(context)
        g.fill_area(0, 0, self.width, self.height, "#20b6de")

        self.chart.x = self.width / 2
        self.chart.y = self.height / 2
        self.chart.scale_x = 0.18
        self.chart.scale_y = 0.18





class BasicWindow:
    def __init__(self):
        window = gtk.Window()
        window.set_size_request(700, 600)
        window.connect("delete_event", lambda *args: gtk.main_quit())
        window.add(Scene())
        window.show_all()


example = BasicWindow()
import signal
signal.signal(signal.SIGINT, signal.SIG_DFL) # gtk3 screws up ctrl+c
gtk.main()

########NEW FILE########
__FILENAME__ = hamster_tracks
#!/usr/bin/env python
# - coding: utf-8 -
# Copyright (C) 2010 Toms Bauģis <toms.baugis at gmail.com>

"""An attempt to make an overview visualization. Consumes hamster d-bus API"""


from gi.repository import Gtk as gtk
from lib import graphics

import time, datetime as dt
from collections import defaultdict
import hamster.client


class Scene(graphics.Scene):
    def __init__(self):
        graphics.Scene.__init__(self)

        storage = hamster.client.Storage()

        self.facts = storage.get_facts(dt.date(2009,1,1), dt.date.today())

        self.day_counts = defaultdict(list)
        activities, categories = defaultdict(int), defaultdict(int)

        print len(self.facts)

        for fact in self.facts:
            self.day_counts[fact.start_time.date()].append(fact)
            activities[fact.activity] += 1
            categories[fact.category] += 1

            if fact.end_time and fact.start_time.date() != fact.end_time.date():
                self.day_counts[fact.end_time.date()].append(fact)



        self.activities = [activity[0] for activity in sorted(activities.items(), key=lambda item:item[1], reverse=True)]
        self.categories = categories.keys()

        self.connect("on-enter-frame", self.on_enter_frame)



    def on_enter_frame(self, scene, context):
        if not self.facts:
            return

        g = graphics.Graphics(context)
        g.set_line_style(width=1)

        start_date = self.facts[0].start_time.date()
        end_date = (self.facts[-1].start_time + self.facts[-1].delta).date()

        days = (end_date - start_date).days





        full_days = []
        for day in range(days):
            current_date = start_date + dt.timedelta(days=day)
            if not self.day_counts[current_date]:
                continue
            full_days.append(self.day_counts[current_date])

        day_pixel = float(self.width) / len(full_days)



        cur_x = 0
        pixel_width = max(round(day_pixel), 1)

        for day in full_days:
            cur_x += round(day_pixel)

            for j, fact in enumerate(day):

                #bar per category
                g.rectangle(cur_x, 27 + self.categories.index(fact.category) * 6, pixel_width, 6)

                #bar per activity
                g.rectangle(cur_x, 102 + self.activities.index(fact.activity) * 6, pixel_width, 6)

                #number of activities
                g.rectangle(cur_x, self.height - 3 * j, pixel_width, 3)

            g.fill("#aaa")




class BasicWindow:
    def __init__(self):
        window = gtk.Window()
        window.set_size_request(600, 300)
        window.connect("delete_event", lambda *args: gtk.main_quit())
        window.add(Scene())
        window.show_all()


example = BasicWindow()
import signal
signal.signal(signal.SIGINT, signal.SIG_DFL) # gtk3 screws up ctrl+c
gtk.main()

########NEW FILE########
__FILENAME__ = hello
#!/usr/bin/env python
# - coding: utf-8 -
# Copyright (C) 2010 Toms Bauģis <toms.baugis at gmail.com>
# Last example from the turorial
# http://wiki.github.com/tbaugis/hamster_experiments/tutorial

from gi.repository import Gtk as gtk
from lib import graphics
from lib.pytweener import Easing


class Scene(graphics.Scene):
    def __init__(self):
        graphics.Scene.__init__(self)

        for i in range(14):
            self.add_child(graphics.Rectangle(40, 40, 3,
                                              y = 420, x = i * 45 + 6,
                                              fill = "#999", stroke="#444", interactive = True))

        self.connect("on-mouse-over", self.on_mouse_over)
        #self.connect("on-enter-frame", self.on_enter_frame)

    def on_enter_frame(self, scene, context):
        self.redraw()

    def on_mouse_over(self, scene, sprite):
        if not sprite: return #ignore blank clicks

        if self.tweener.get_tweens(sprite): #must be busy
            return

        def bring_back(sprite):
            self.animate(sprite, y = 420, scale_x = 1, scale_y = 1, x = sprite.original_x, easing = Easing.Bounce.ease_out)

        sprite.original_x = sprite.x
        self.animate(sprite, y = 150, scale_x = 2, x = sprite.x - 20, scale_y = 2, on_complete = bring_back)


window = gtk.Window()
window.set_size_request(640, 480)
window.connect("delete_event", lambda *args: gtk.main_quit())
window.add(Scene())
window.show_all()
import signal
signal.signal(signal.SIGINT, signal.SIG_DFL) # gtk3 screws up ctrl+c
gtk.main()

########NEW FILE########
__FILENAME__ = i_thing
#!/usr/bin/env python
# - coding: utf-8 -
# Copyright (C) 2010 Toms Bauģis <toms.baugis at gmail.com>

"""Emulating the wheel from apple products"""


from gi.repository import Gtk as gtk
from gi.repository import Gdk as gdk
from lib import graphics
from contrib import euclid

import cairo
import math

class Scene(graphics.Scene):
    def __init__(self, progress):
        graphics.Scene.__init__(self, scale=True, keep_aspect=True)
        self.progress = progress


        self.wheel = graphics.Circle(200, 200, "#aaa", x = 20, y=20, interactive=True, pivot_x=100, pivot_y=100)
        self.add_child(self.wheel)
        self.add_child(graphics.Circle(50, 50, "#fafafa", x=95, y=95, interactive=True))

        self.ticker = graphics.Label("*tick*", size=24, color="#000", x=5, y=220, opacity=0)
        self.ticker.last_degrees = 0
        self.add_child(self.ticker)

        self.connect("on-mouse-move", self.on_mouse_move)
        self.connect("on-mouse-down", self.on_mouse_down)
        self.connect("on-mouse-up", self.on_mouse_up)

        self.drag_point = None
        self.start_rotation = None

    def on_mouse_down(self, scene, event):
        sprite = self.get_sprite_at_position(event.x, event.y)
        if sprite == self.wheel:
            self.drag_point = euclid.Point2(event.x, event.y)
            self.start_rotation = self.wheel.rotation

    def on_mouse_up(self, scene, event):
        self.drag_point = None
        self.start_rotation = None


    def flash_tick(self):
        if self.ticker.opacity < 0.5:
            self.ticker.opacity = 1
            self.ticker.animate(opacity=0, duration=0.2)

    def on_mouse_move(self, scene, event):
        mouse_down = gdk.ModifierType.BUTTON1_MASK & event.state
        if not mouse_down:
            return
        sprite = self.get_sprite_at_position(event.x, event.y)

        if sprite == self.wheel:
            if not self.drag_point:
                self.on_mouse_down(scene, event)

            pivot_x, pivot_y = self.wheel.get_matrix().transform_point(self.wheel.pivot_x, self.wheel.pivot_y)

            pivot_point = euclid.Point2(pivot_x, pivot_y)
            drag_vector = euclid.Point2(event.x, event.y) - pivot_point

            start_vector = self.drag_point - pivot_point

            angle = math.atan2(start_vector.y, start_vector.x) - math.atan2(drag_vector.y, drag_vector.x)


            delta = (self.start_rotation - angle) - self.wheel.rotation

            # full revolution jumps from -180 to 180 degrees
            if abs(delta) >= math.pi:
                delta = 0
            else:
                degrees = int(math.degrees(self.wheel.rotation))
                self.ticker.last_degrees = self.ticker.last_degrees or degrees
                if abs(self.ticker.last_degrees - degrees) >= 30:
                    self.ticker.last_degrees = degrees
                    self.flash_tick()


            progress = min(1, max(0, self.progress.get_fraction() + delta / (math.pi * 2 * 10)))
            self.progress.set_fraction(progress)

            self.wheel.rotation = self.start_rotation - angle

        else:
            self.drag_point = None




class BasicWindow:
    def __init__(self):
        window = gtk.Window()
        window.set_default_size(240, 280)
        window.set_title("iThing")
        window.connect("delete_event", lambda *args: gtk.main_quit())
        vbox = gtk.VBox()

        progress_bar = gtk.ProgressBar()
        vbox.pack_start(Scene(progress_bar), True, True, 0)
        vbox.pack_start(progress_bar, False, False, 0)
        window.add(vbox)
        window.show_all()

if __name__ == '__main__':
    window = BasicWindow()
    import signal
    signal.signal(signal.SIGINT, signal.SIG_DFL) # gtk3 screws up ctrl+c
    gtk.main()

########NEW FILE########
__FILENAME__ = graphics
# - coding: utf-8 -

# Copyright (c) 2008-2012 Toms Bauģis <toms.baugis at gmail.com>
# Copyright (c) 2011-2012 Media Modifications, Ltd.
# Dual licensed under the MIT or GPL Version 2 licenses.
# See http://github.com/tbaugis/hamster_experiments/blob/master/README.textile

from collections import defaultdict
import math
import datetime as dt


from gi.repository import Gtk as gtk
from gi.repository import Gdk as gdk
from gi.repository import GObject as gobject
from gi.repository import Pango as pango
from gi.repository import PangoCairo as pangocairo

import cairo
from gi.repository import GdkPixbuf

import re

try:
    import pytweener
except: # we can also live without tweener. Scene.animate will not work
    pytweener = None

import colorsys
from collections import deque

# lemme know if you know a better way how to get default font
_test_label = gtk.Label("Hello")
_font_desc = _test_label.get_style().font_desc.to_string()


class ColorUtils(object):
    hex_color_normal = re.compile("#([a-fA-F0-9]{2})([a-fA-F0-9]{2})([a-fA-F0-9]{2})")
    hex_color_short = re.compile("#([a-fA-F0-9])([a-fA-F0-9])([a-fA-F0-9])")
    hex_color_long = re.compile("#([a-fA-F0-9]{4})([a-fA-F0-9]{4})([a-fA-F0-9]{4})")

    # d3 colors
    category10 = ("#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
                  "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf")
    category20 = ("#1f77b4", "#aec7e8", "#ff7f0e", "#ffbb78", "#2ca02c",
                  "#98df8a", "#d62728", "#ff9896", "#9467bd", "#c5b0d5",
                  "#8c564b", "#c49c94", "#e377c2", "#f7b6d2", "#7f7f7f",
                  "#c7c7c7", "#bcbd22", "#dbdb8d", "#17becf", "#9edae5")
    category20b = ("#393b79", "#5254a3", "#6b6ecf", "#9c9ede", "#637939",
                   "#8ca252", "#b5cf6b", "#cedb9c", "#8c6d31", "#bd9e39",
                   "#e7ba52", "#e7cb94", "#843c39", "#ad494a", "#d6616b",
                   "#e7969c", "#7b4173", "#a55194", "#ce6dbd", "#de9ed6")
    category20c = ("#3182bd", "#6baed6", "#9ecae1", "#c6dbef", "#e6550d",
                   "#fd8d3c", "#fdae6b", "#fdd0a2", "#31a354", "#74c476",
                   "#a1d99b", "#c7e9c0", "#756bb1", "#9e9ac8", "#bcbddc",
                   "#dadaeb", "#636363", "#969696", "#bdbdbd", "#d9d9d9")

    def parse(self, color):
        """parse string or a color tuple into color usable for cairo (all values
        in the normalized (0..1) range"""
        assert color is not None

        #parse color into rgb values
        if isinstance(color, basestring):
            match = self.hex_color_long.match(color)
            if match:
                color = [int(color, 16) / 65535.0 for color in match.groups()]
            else:
                match = self.hex_color_normal.match(color)
                if match:
                    color = [int(color, 16) / 255.0 for color in match.groups()]
                else:
                    match = self.hex_color_short.match(color)
                    color = [int(color + color, 16) / 255.0 for color in match.groups()]

        elif isinstance(color, gdk.Color):
            color = [color.red / 65535.0,
                     color.green / 65535.0,
                     color.blue / 65535.0]

        elif isinstance(color, (list, tuple)):
            # otherwise we assume we have color components in 0..255 range
            if color[0] > 1 or color[1] > 1 or color[2] > 1:
                color = [c / 255.0 for c in color]
        else:
            color = [color.red, color.green, color.blue]


        return color

    def rgb(self, color):
        """returns rgb[a] tuple of the color with values in range 0.255"""
        return [c * 255 for c in self.parse(color)]

    def gdk(self, color):
        """returns gdk.Color object of the given color"""
        c = self.parse(color)
        return gdk.Color.from_floats(c)

    def hex(self, color):
        c = self.parse(color)
        return "#" + "".join(["%02x" % (color * 255) for color in c])

    def is_light(self, color):
        """tells you if color is dark or light, so you can up or down the
        scale for improved contrast"""
        return colorsys.rgb_to_hls(*self.rgb(color))[1] > 150

    def darker(self, color, step):
        """returns color darker by step (where step is in range 0..255)"""
        hls = colorsys.rgb_to_hls(*self.rgb(color))
        return colorsys.hls_to_rgb(hls[0], hls[1] - step, hls[2])

    def contrast(self, color, step):
        """if color is dark, will return a lighter one, otherwise darker"""
        hls = colorsys.rgb_to_hls(*self.rgb(color))
        if self.is_light(color):
            return colorsys.hls_to_rgb(hls[0], hls[1] - step, hls[2])
        else:
            return colorsys.hls_to_rgb(hls[0], hls[1] + step, hls[2])
        # returns color darker by step (where step is in range 0..255)

Colors = ColorUtils() # this is a static class, so an instance will do

def get_gdk_rectangle(x, y, w, h):
    rect = gdk.Rectangle()
    rect.x, rect.y, rect.width, rect.height = x or 0, y or 0, w or 0, h or 0
    return rect




def chain(*steps):
    """chains the given list of functions and object animations into a callback string.

        Expects an interlaced list of object and params, something like:
            object, {params},
            callable, {params},
            object, {},
            object, {params}
    Assumes that all callees accept on_complete named param.
    The last item in the list can omit that.
    XXX - figure out where to place these guys as they are quite useful
    """
    if not steps:
        return

    def on_done(sprite=None):
        chain(*steps[2:])

    obj, params = steps[:2]

    if len(steps) > 2:
        params['on_complete'] = on_done
    if callable(obj):
        obj(**params)
    else:
        obj.animate(**params)

def full_pixels(space, data, gap_pixels=1):
    """returns the given data distributed in the space ensuring it's full pixels
    and with the given gap.
    this will result in minor sub-pixel inaccuracies.
    XXX - figure out where to place these guys as they are quite useful
    """
    available = space - (len(data) - 1) * gap_pixels # 8 recs 7 gaps

    res = []
    for i, val in enumerate(data):
        # convert data to 0..1 scale so we deal with fractions
        data_sum = sum(data[i:])
        norm = val * 1.0 / data_sum


        w = max(int(round(available * norm)), 1)
        res.append(w)
        available -= w
    return res


class Graphics(object):
    """If context is given upon contruction, will perform drawing
       operations on context instantly. Otherwise queues up the drawing
       instructions and performs them in passed-in order when _draw is called
       with context.

       Most of instructions are mapped to cairo functions by the same name.
       Where there are differences, documenation is provided.

       See http://cairographics.org/documentation/pycairo/2/reference/context.html
       for detailed description of the cairo drawing functions.
    """
    __slots__ = ('context', 'colors', 'extents', 'paths', '_last_matrix',
                 '__new_instructions', '__instruction_cache', 'cache_surface',
                 '_cache_layout')
    colors = Colors # pointer to the color utilities instance

    def __init__(self, context = None):
        self.context = context
        self.extents = None     # bounds of the object, only if interactive
        self.paths = None       # paths for mouse hit checks
        self._last_matrix = None
        self.__new_instructions = [] # instruction set until it is converted into path-based instructions
        self.__instruction_cache = []
        self.cache_surface = None
        self._cache_layout = None

    def clear(self):
        """clear all instructions"""
        self.__new_instructions = []
        self.__instruction_cache = []
        self.paths = []

    def stroke(self, color=None, alpha=1):
        if color or alpha < 1:
            self.set_color(color, alpha)
        self._add_instruction("stroke")

    def fill(self, color = None, alpha = 1):
        if color or alpha < 1:
            self.set_color(color, alpha)
        self._add_instruction("fill")

    def mask(self, pattern):
        self._add_instruction("mask", pattern)

    def stroke_preserve(self, color = None, alpha = 1):
        if color or alpha < 1:
            self.set_color(color, alpha)
        self._add_instruction("stroke_preserve")

    def fill_preserve(self, color = None, alpha = 1):
        if color or alpha < 1:
            self.set_color(color, alpha)
        self._add_instruction("fill_preserve")

    def new_path(self):
        self._add_instruction("new_path")

    def paint(self):
        self._add_instruction("paint")

    def set_font_face(self, face):
        self._add_instruction("set_font_face", face)

    def set_font_size(self, size):
        self._add_instruction("set_font_size", size)

    def set_source(self, image, x = 0, y = 0):
        self._add_instruction("set_source", image)

    def set_source_surface(self, surface, x = 0, y = 0):
        self._add_instruction("set_source_surface", surface, x, y)

    def set_source_pixbuf(self, pixbuf, x = 0, y = 0):
        self._add_instruction("set_source_pixbuf", pixbuf, x, y)

    def save_context(self):
        self._add_instruction("save")

    def restore_context(self):
        self._add_instruction("restore")

    def clip(self):
        self._add_instruction("clip")

    def rotate(self, radians):
        self._add_instruction("rotate", radians)

    def translate(self, x, y):
        self._add_instruction("translate", x, y)

    def scale(self, x_factor, y_factor):
        self._add_instruction("scale", x_factor, y_factor)

    def move_to(self, x, y):
        self._add_instruction("move_to", x, y)

    def line_to(self, x, y = None):
        if y is not None:
            self._add_instruction("line_to", x, y)
        elif isinstance(x, list) and y is None:
            for x2, y2 in x:
                self._add_instruction("line_to", x2, y2)


    def rel_line_to(self, x, y = None):
        if x is not None and y is not None:
            self._add_instruction("rel_line_to", x, y)
        elif isinstance(x, list) and y is None:
            for x2, y2 in x:
                self._add_instruction("rel_line_to", x2, y2)

    def curve_to(self, x, y, x2, y2, x3, y3):
        """draw a curve. (x2, y2) is the middle point of the curve"""
        self._add_instruction("curve_to", x, y, x2, y2, x3, y3)

    def close_path(self):
        self._add_instruction("close_path")

    def set_line_style(self, width = None, dash = None, dash_offset = 0):
        """change width and dash of a line"""
        if width is not None:
            self._add_instruction("set_line_width", width)

        if dash is not None:
            self._add_instruction("set_dash", dash, dash_offset)



    def _set_color(self, context, r, g, b, a):
        """the alpha has to changed based on the parent, so that happens at the
        time of drawing"""
        if a < 1:
            context.set_source_rgba(r, g, b, a)
        else:
            context.set_source_rgb(r, g, b)

    def set_color(self, color, alpha = 1):
        """set active color. You can use hex colors like "#aaa", or you can use
        normalized RGB tripplets (where every value is in range 0..1), or
        you can do the same thing in range 0..65535.
        also consider skipping this operation and specify the color on stroke and
        fill.
        """
        color = self.colors.parse(color) # parse whatever we have there into a normalized triplet
        if len(color) == 4 and alpha is None:
            alpha = color[3]
        r, g, b = color[:3]
        self._add_instruction("set_color", r, g, b, alpha)


    def arc(self, x, y, radius, start_angle, end_angle):
        """draw arc going counter-clockwise from start_angle to end_angle"""
        self._add_instruction("arc", x, y, radius, start_angle, end_angle)

    def circle(self, x, y, radius):
        """draw circle"""
        self._add_instruction("arc", x, y, radius, 0, math.pi * 2)

    def ellipse(self, x, y, width, height, edges = None):
        """draw 'perfect' ellipse, opposed to squashed circle. works also for
           equilateral polygons"""
        # the automatic edge case is somewhat arbitrary
        steps = edges or max((32, width, height)) / 2

        angle = 0
        step = math.pi * 2 / steps
        points = []
        while angle < math.pi * 2:
            points.append((width / 2.0 * math.cos(angle),
                           height / 2.0 * math.sin(angle)))
            angle += step

        min_x = min((point[0] for point in points))
        min_y = min((point[1] for point in points))

        self.move_to(points[0][0] - min_x + x, points[0][1] - min_y + y)
        for p_x, p_y in points:
            self.line_to(p_x - min_x + x, p_y - min_y + y)
        self.line_to(points[0][0] - min_x + x, points[0][1] - min_y + y)

    def arc_negative(self, x, y, radius, start_angle, end_angle):
        """draw arc going clockwise from start_angle to end_angle"""
        self._add_instruction("arc_negative", x, y, radius, start_angle, end_angle)

    def triangle(self, x, y, width, height):
        self.move_to(x, y)
        self.line_to(width/2 + x, height + y)
        self.line_to(width + x, y)
        self.line_to(x, y)

    def rectangle(self, x, y, width, height, corner_radius = 0):
        """draw a rectangle. if corner_radius is specified, will draw
        rounded corners. corner_radius can be either a number or a tuple of
        four items to specify individually each corner, starting from top-left
        and going clockwise"""
        if corner_radius <= 0:
            self._add_instruction("rectangle", x, y, width, height)
            return

        # convert into 4 border and  make sure that w + h are larger than 2 * corner_radius
        if isinstance(corner_radius, (int, float)):
            corner_radius = [corner_radius] * 4
        corner_radius = [min(r, min(width, height) / 2) for r in corner_radius]

        x2, y2 = x + width, y + height
        self._rounded_rectangle(x, y, x2, y2, corner_radius)

    def _rounded_rectangle(self, x, y, x2, y2, corner_radius):
        if isinstance(corner_radius, (int, float)):
            corner_radius = [corner_radius] * 4

        self._add_instruction("move_to", x + corner_radius[0], y)
        self._add_instruction("line_to", x2 - corner_radius[1], y)
        self._add_instruction("curve_to", x2 - corner_radius[1] / 2, y, x2, y + corner_radius[1] / 2, x2, y + corner_radius[1])
        self._add_instruction("line_to", x2, y2 - corner_radius[2])
        self._add_instruction("curve_to", x2, y2 - corner_radius[2] / 2, x2 - corner_radius[2] / 2, y2, x2 - corner_radius[2], y2)
        self._add_instruction("line_to", x + corner_radius[3], y2)
        self._add_instruction("curve_to", x + corner_radius[3] / 2, y2, x, y2 - corner_radius[3] / 2, x, y2 - corner_radius[3])
        self._add_instruction("line_to", x, y + corner_radius[0])
        self._add_instruction("curve_to", x, y + corner_radius[0] / 2, x + corner_radius[0] / 2, y, x + corner_radius[0], y)

    def hexagon(self, x, y, height):
        side = height * 0.5
        angle_x = side * 0.5
        angle_y = side * 0.8660254
        self.move_to(x, y)
        self.line_to(x + side, y)
        self.line_to(x + side + angle_x, y + angle_y)
        self.line_to(x + side, y + 2*angle_y)
        self.line_to(x, y + 2*angle_y)
        self.line_to(x - angle_x, y + angle_y)
        self.line_to(x, y)
        self.close_path()

    def fill_area(self, x, y, width, height, color, opacity = 1):
        """fill rectangular area with specified color"""
        self.save_context()
        self.rectangle(x, y, width, height)
        self._add_instruction("clip")
        self.rectangle(x, y, width, height)
        self.fill(color, opacity)
        self.restore_context()

    def fill_stroke(self, fill = None, stroke = None, opacity = 1, line_width = None):
        """fill and stroke the drawn area in one go"""
        if line_width: self.set_line_style(line_width)

        if fill and stroke:
            self.fill_preserve(fill, opacity)
        elif fill:
            self.fill(fill, opacity)

        if stroke:
            self.stroke(stroke)

    def create_layout(self, size = None):
        """utility function to create layout with the default font. Size and
        alignment parameters are shortcuts to according functions of the
        pango.Layout"""
        if not self.context:
            # TODO - this is rather sloppy as far as exception goes
            #        should explain better
            raise "Can not create layout without existing context!"

        layout = pangocairo.create_layout(self.context)
        font_desc = pango.FontDescription(_font_desc)
        if size: font_desc.set_absolute_size(size * pango.SCALE)

        layout.set_font_description(font_desc)
        return layout

    def show_label(self, text, size = None, color = None, font_desc = None):
        """display text. unless font_desc is provided, will use system's default font"""
        font_desc = pango.FontDescription(font_desc or _font_desc)
        if color: self.set_color(color)
        if size: font_desc.set_absolute_size(size * pango.SCALE)
        self.show_layout(text, font_desc)

    def show_text(self, text):
        self._add_instruction("show_text", text)

    def text_path(self, text):
        """this function is most likely to change"""
        self._add_instruction("text_path", text)

    def _show_layout(self, context, layout, text, font_desc, alignment, width, wrap,
                     ellipsize, single_paragraph_mode):
        layout.set_font_description(font_desc)
        layout.set_markup(text)
        layout.set_width(int(width or -1))
        layout.set_single_paragraph_mode(single_paragraph_mode)
        if alignment is not None:
            layout.set_alignment(alignment)

        if width > 0:
            if wrap is not None:
                layout.set_wrap(wrap)
            else:
                layout.set_ellipsize(ellipsize or pango.EllipsizeMode.END)

        pangocairo.show_layout(context, layout)


    def show_layout(self, text, font_desc, alignment = pango.Alignment.LEFT,
                    width = -1, wrap = None, ellipsize = None,
                    single_paragraph_mode = False):
        """display text. font_desc is string of pango font description
           often handier than calling this function directly, is to create
           a class:Label object
        """
        layout = self._cache_layout = self._cache_layout or pangocairo.create_layout(cairo.Context(cairo.ImageSurface(cairo.FORMAT_A1, 0, 0)))
        self._add_instruction("show_layout", layout, text, font_desc,
                              alignment, width, wrap, ellipsize, single_paragraph_mode)


    def _add_instruction(self, function, *params):
        if self.context:
            if function == "set_color":
                self._set_color(self.context, *params)
            elif function == "show_layout":
                self._show_layout(self.context, *params)
            else:
                getattr(self.context, function)(*params)
        else:
            self.paths = None
            self.__new_instructions.append((function, params))


    def _draw(self, context, opacity):
        """draw accumulated instructions in context"""

        # if we have been moved around, we should update bounds
        fresh_draw = len(self.__new_instructions or []) > 0
        if fresh_draw: #new stuff!
            self.paths = []
            self.__instruction_cache = self.__new_instructions
            self.__new_instructions = []
        else:
            if not self.__instruction_cache:
                return

        for instruction, args in self.__instruction_cache:
            if fresh_draw:
                if instruction in ("new_path", "stroke", "fill", "clip"):
                    self.paths.append((instruction, "path", context.copy_path()))

                elif instruction in ("save", "restore", "translate", "scale", "rotate"):
                    self.paths.append((instruction, "transform", args))

            if instruction == "set_color":
                self._set_color(context, args[0], args[1], args[2], args[3] * opacity)
            elif instruction == "show_layout":
                self._show_layout(context, *args)
            elif opacity < 1 and instruction == "paint":
                context.paint_with_alpha(opacity)
            else:
                getattr(context, instruction)(*args)



    def _draw_as_bitmap(self, context, opacity):
        """
            instead of caching paths, this function caches the whole drawn thing
            use cache_as_bitmap on sprite to enable this mode
        """
        matrix = context.get_matrix()
        matrix_changed = matrix != self._last_matrix
        new_instructions = self.__new_instructions is not None and len(self.__new_instructions) > 0

        if not new_instructions and not matrix_changed:
            context.save()
            context.identity_matrix()
            context.translate(self.extents.x, self.extents.y)
            context.set_source_surface(self.cache_surface)
            if opacity < 1:
                context.paint_with_alpha(opacity)
            else:
                context.paint()
            context.restore()
            return


        if new_instructions:
            self.__instruction_cache = list(self.__new_instructions)
            self.__new_instructions = deque()

        self.paths = []
        self.extents = None

        if not self.__instruction_cache:
            # no instructions - nothing to do
            return

        # instructions that end path
        path_end_instructions = ("new_path", "clip", "stroke", "fill", "stroke_preserve", "fill_preserve")

        # measure the path extents so we know the size of cache surface
        # also to save some time use the context to paint for the first time
        extents = gdk.Rectangle()
        for instruction, args in self.__instruction_cache:
            if instruction in path_end_instructions:
                self.paths.append((instruction, "path", context.copy_path()))
                exts = context.path_extents()
                exts = get_gdk_rectangle(int(exts[0]), int(exts[1]),
                                         int(exts[2]-exts[0]), int(exts[3]-exts[1]))
                if extents.width and extents.height:
                    extents = gdk.rectangle_union(extents, exts)
                else:
                    extents = exts
            elif instruction in ("save", "restore", "translate", "scale", "rotate"):
                self.paths.append((instruction, "transform", args))


            if instruction in ("set_source_pixbuf", "set_source_surface"):
                # draw a rectangle around the pathless instructions so that the extents are correct
                pixbuf = args[0]
                x = args[1] if len(args) > 1 else 0
                y = args[2] if len(args) > 2 else 0
                context.rectangle(x, y, pixbuf.get_width(), pixbuf.get_height())
                context.clip()

            if instruction == "paint" and opacity < 1:
                context.paint_with_alpha(opacity)
            elif instruction == "set_color":
                self._set_color(context, args[0], args[1], args[2], args[3] * opacity)
            elif instruction == "show_layout":
                self._show_layout(context, *args)
            else:
                getattr(context, instruction)(*args)


        # avoid re-caching if we have just moved
        just_transforms = new_instructions == False and \
                          matrix and self._last_matrix \
                          and all([matrix[i] == self._last_matrix[i] for i in range(4)])

        # TODO - this does not look awfully safe
        extents.x += matrix[4] - 5
        extents.y += matrix[5] - 5
        self.extents = extents

        if not just_transforms:
            # now draw the instructions on the caching surface
            w = int(extents.width) + 10
            h = int(extents.height) + 10
            self.cache_surface = context.get_target().create_similar(cairo.CONTENT_COLOR_ALPHA, w, h)
            ctx = cairo.Context(self.cache_surface)
            ctx.translate(-extents.x, -extents.y)

            ctx.transform(matrix)
            for instruction, args in self.__instruction_cache:
                if instruction == "set_color":
                    self._set_color(ctx, args[0], args[1], args[2], args[3])
                elif instruction == "show_layout":
                    self._show_layout(ctx, *args)
                else:
                    getattr(ctx, instruction)(*args)

        self._last_matrix = matrix


class Parent(object):
    """shared functions across scene and sprite"""

    def find(self, id):
        """breadth-first sprite search by ID"""
        for sprite in self.sprites:
            if sprite.id == id:
                return sprite

        for sprite in self.sprites:
            found = sprite.find(id)
            if found:
                return found

    def __getitem__(self, i):
        return self.sprites[i]

    def traverse(self, attr_name = None, attr_value = None):
        """traverse the whole sprite tree and return child sprites which have the
        attribute and it's set to the specified value.
        If falue is None, will return all sprites that have the attribute
        """
        for sprite in self.sprites:
            if (attr_name is None) or \
               (attr_value is None and hasattr(sprite, attr_name)) or \
               (attr_value is not None and getattr(sprite, attr_name, None) == attr_value):
                yield sprite

            for child in sprite.traverse(attr_name, attr_value):
                yield child

    def log(self, *lines):
        """will print out the lines in console if debug is enabled for the
           specific sprite"""
        if getattr(self, "debug", False):
            print dt.datetime.now().time(),
            for line in lines:
                print line,
            print

    def _add(self, sprite, index = None):
        """add one sprite at a time. used by add_child. split them up so that
        it would be possible specify the index externally"""
        if sprite == self:
            raise Exception("trying to add sprite to itself")

        if sprite.parent:
            sprite.x, sprite.y = self.from_scene_coords(*sprite.to_scene_coords())
            sprite.parent.remove_child(sprite)

        if index is not None:
            self.sprites.insert(index, sprite)
        else:
            self.sprites.append(sprite)
        sprite.parent = self


    def _sort(self):
        """sort sprites by z_order"""
        self.__dict__['_z_ordered_sprites'] = sorted(self.sprites, key=lambda sprite:sprite.z_order)

    def add_child(self, *sprites):
        """Add child sprite. Child will be nested within parent"""
        for sprite in sprites:
            self._add(sprite)
        self._sort()
        self.redraw()

    def remove_child(self, *sprites):
        """Remove one or several :class:`Sprite` sprites from scene """

        # first drop focus
        scene = self.get_scene()

        if scene:
            child_sprites = list(self.all_child_sprites())
            if scene._focus_sprite in child_sprites:
                scene._focus_sprite = None


        for sprite in sprites:
            if sprite in self.sprites:
                self.sprites.remove(sprite)
                sprite._scene = None
                sprite.parent = None
            self.disconnect_child(sprite)
        self._sort()
        self.redraw()


    def clear(self):
        """Remove all child sprites"""
        self.remove_child(*self.sprites)


    def destroy(self):
        """recursively removes all sprite children so that it is freed from
        any references and can be garbage collected"""
        for sprite in self.sprites:
            sprite.destroy()
        self.clear()


    def all_child_sprites(self):
        """returns all child and grandchild sprites in a flat list"""
        for sprite in self.sprites:
            for child_sprite in sprite.all_child_sprites():
                yield child_sprite
            yield sprite


    def get_mouse_sprites(self):
        """returns list of child sprites that the mouse can interact with.
        by default returns all visible sprites, but override
        to define your own rules"""
        return (sprite for sprite in self._z_ordered_sprites if sprite.visible)


    def connect_child(self, sprite, event, *args, **kwargs):
        """connect to a child event so that will disconnect if the child is
        removed from this sprite. this is the recommended way to connect to
        child events. syntax is same as for the .connect itself, just you
        prepend the child sprite as the first element"""
        handler = sprite.connect(event, *args, **kwargs)
        self._child_handlers[sprite].append(handler)
        return handler

    def connect_child_after(self, sprite, event, *args, **kwargs):
        """connect to a child event so that will disconnect if the child is
        removed from this sprite. this is the recommended way to connect to
        child events. syntax is same as for the .connect itself, just you
        prepend the child sprite as the first element"""
        handler = sprite.connect_after(event, *args, **kwargs)
        self._child_handlers[sprite].append(handler)
        return handler

    def disconnect_child(self, sprite, *handlers):
        """disconnects from child event. if handler is not specified, will
        disconnect from all the child sprite events"""
        handlers = handlers or self._child_handlers.get(sprite, [])
        for handler in list(handlers):
            if sprite.handler_is_connected(handler):
                sprite.disconnect(handler)
            if handler in self._child_handlers.get(sprite, []):
                self._child_handlers[sprite].remove(handler)

        if not self._child_handlers[sprite]:
            del self._child_handlers[sprite]

    def __repr__(self):
        return "<%s %s>" % (self.__class__.__name__, getattr(self, "id", None) or str(id(self)))


class Sprite(Parent, gobject.GObject):
    """The Sprite class is a basic display list building block: a display list
       node that can display graphics and can also contain children.
       Once you have created the sprite, use Scene's add_child to add it to
       scene
    """

    __gsignals__ = {
        "on-mouse-over": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, ()),
        "on-mouse-move": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
        "on-mouse-out": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, ()),
        "on-mouse-down": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
        "on-double-click": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
        "on-triple-click": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
        "on-mouse-up": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
        "on-mouse-scroll": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
        "on-click": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
        "on-drag-start": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
        "on-drag": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
        "on-drag-finish": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
        "on-focus": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, ()),
        "on-blur": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, ()),
        "on-key-press": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
        "on-key-release": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
        "on-render": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, ()),
    }

    transformation_attrs = set(('x', 'y', 'rotation', 'scale_x', 'scale_y', 'pivot_x', 'pivot_y'))

    visibility_attrs = set(('opacity', 'visible', 'z_order'))

    cache_attrs = set(('_stroke_context', '_matrix', '_prev_parent_matrix', '_scene'))

    graphics_unrelated_attrs = set(('drag_x', 'drag_y', 'sprites', 'mouse_cursor', '_sprite_dirty', 'id'))

    #: mouse-over cursor of the sprite. Can be either a gdk cursor
    #: constants, or a pixbuf or a pixmap. If set to False, will be using
    #: scene's cursor. in order to have the cursor displayed, the sprite has
    #: to be interactive
    mouse_cursor = None

    #: whether the widget can gain focus
    can_focus = None

    def __init__(self, x = 0, y = 0, opacity = 1, visible = True, rotation = 0,
                 pivot_x = 0, pivot_y = 0, scale_x = 1, scale_y = 1,
                 interactive = False, draggable = False, z_order = 0,
                 mouse_cursor = None, cache_as_bitmap = False,
                 snap_to_pixel = True, debug = False, id = None,
                 can_focus = False):
        gobject.GObject.__init__(self)

        # a place where to store child handlers
        self.__dict__['_child_handlers'] = defaultdict(list)

        self._scene = None

        self.debug = debug

        self.id = id

        #: list of children sprites. Use :func:`add_child` to add sprites
        self.sprites = []

        self._z_ordered_sprites = []

        #: instance of :ref:`graphics` for this sprite
        self.graphics = Graphics()

        #: boolean denoting whether the sprite responds to mouse events
        self.interactive = interactive

        #: boolean marking if sprite can be automatically dragged
        self.draggable = draggable

        #: relative x coordinate of the sprites' rotation point
        self.pivot_x = pivot_x

        #: relative y coordinates of the sprites' rotation point
        self.pivot_y = pivot_y

        #: sprite opacity
        self.opacity = opacity

        #: boolean visibility flag
        self.visible = visible

        #: pointer to parent :class:`Sprite` or :class:`Scene`
        self.parent = None

        #: sprite coordinates
        self.x, self.y = x, y

        #: rotation of the sprite in radians (use :func:`math.degrees` to convert to degrees if necessary)
        self.rotation = rotation

        #: scale X
        self.scale_x = scale_x

        #: scale Y
        self.scale_y = scale_y

        #: drawing order between siblings. The one with the highest z_order will be on top.
        self.z_order = z_order

        #: x position of the cursor within mouse upon drag. change this value
        #: in on-drag-start to adjust drag point
        self.drag_x = 0

        #: y position of the cursor within mouse upon drag. change this value
        #: in on-drag-start to adjust drag point
        self.drag_y = 0

        #: Whether the sprite should be cached as a bitmap. Default: true
        #: Generally good when you have many static sprites
        self.cache_as_bitmap = cache_as_bitmap

        #: Should the sprite coordinates always rounded to full pixel. Default: true
        #: Mostly this is good for performance but in some cases that can lead
        #: to rounding errors in positioning.
        self.snap_to_pixel = snap_to_pixel

        #: focus state
        self.focused = False


        if mouse_cursor is not None:
            self.mouse_cursor = mouse_cursor

        if can_focus is not None:
            self.can_focus = can_focus



        self.__dict__["_sprite_dirty"] = True # flag that indicates that the graphics object of the sprite should be rendered

        self._matrix = None
        self._prev_parent_matrix = None

        self._stroke_context = None

        self.connect("on-click", self.__on_click)



    def __setattr__(self, name, val):
        if isinstance(getattr(type(self), name, None), property) and \
           getattr(type(self), name).fset is not None:
            getattr(type(self), name).fset(self, val)
            return

        prev = self.__dict__.get(name, "hamster_graphics_no_value_really")
        if type(prev) == type(val) and prev == val:
            return
        self.__dict__[name] = val

        # prev parent matrix walks downwards
        if name == '_prev_parent_matrix' and self.visible:
            # downwards recursive invalidation of parent matrix
            for sprite in self.sprites:
                sprite._prev_parent_matrix = None


        if name in self.cache_attrs or name in self.graphics_unrelated_attrs:
            return

        """all the other changes influence cache vars"""

        if name == 'visible' and self.visible == False:
            # when transforms happen while sprite is invisible
            for sprite in self.sprites:
                sprite._prev_parent_matrix = None


        # on moves invalidate our matrix, child extent cache (as that depends on our transforms)
        # as well as our parent's child extents as we moved
        # then go into children and invalidate the parent matrix down the tree
        if name in self.transformation_attrs:
            self._matrix = None
            for sprite in self.sprites:
                sprite._prev_parent_matrix = None
        elif name not in self.visibility_attrs:
            # if attribute is not in transformation nor visibility, we conclude
            # that it must be causing the sprite needs re-rendering
            self.__dict__["_sprite_dirty"] = True

        # on parent change invalidate the matrix
        if name == 'parent':
            self._prev_parent_matrix = None
            return

        if name == 'opacity' and getattr(self, "cache_as_bitmap", None) and hasattr(self, "graphics"):
            # invalidating cache for the bitmap version as that paints opacity in the image
            self.graphics._last_matrix = None

        if name == 'z_order' and getattr(self, "parent", None):
            self.parent._sort()


        self.redraw()


    def _get_mouse_cursor(self):
        """Determine mouse cursor.
        By default look for self.mouse_cursor is defined and take that.
        Otherwise use gdk.CursorType.FLEUR for draggable sprites and gdk.CursorType.HAND2 for
        interactive sprites. Defaults to scenes cursor.
        """
        if self.mouse_cursor is not None:
            return self.mouse_cursor
        elif self.interactive and self.draggable:
            return gdk.CursorType.FLEUR
        elif self.interactive:
            return gdk.CursorType.HAND2

    def bring_to_front(self):
        """adjusts sprite's z-order so that the sprite is on top of it's
        siblings"""
        if not self.parent:
            return
        self.z_order = self.parent._z_ordered_sprites[-1].z_order + 1

    def send_to_back(self):
        """adjusts sprite's z-order so that the sprite is behind it's
        siblings"""
        if not self.parent:
            return
        self.z_order = self.parent._z_ordered_sprites[0].z_order - 1

    def has_focus(self):
        """True if the sprite has the global input focus, False otherwise."""
        scene = self.get_scene()
        return scene and scene._focus_sprite == self

    def grab_focus(self):
        """grab window's focus. Keyboard and scroll events will be forwarded
        to the sprite who has the focus. Check the 'focused' property of sprite
        in the on-render event to decide how to render it (say, add an outline
        when focused=true)"""
        scene = self.get_scene()
        if scene and scene._focus_sprite != self:
            scene._focus_sprite = self

    def blur(self):
        """removes focus from the current element if it has it"""
        scene = self.get_scene()
        if scene and scene._focus_sprite == self:
            scene._focus_sprite = None

    def __on_click(self, sprite, event):
        if self.interactive and self.can_focus:
            self.grab_focus()

    def get_parents(self):
        """returns all the parent sprites up until scene"""
        res = []
        parent = self.parent
        while parent and isinstance(parent, Scene) == False:
            res.insert(0, parent)
            parent = parent.parent

        return res


    def get_extents(self):
        """measure the extents of the sprite's graphics."""
        if self._sprite_dirty:
            # redrawing merely because we need fresh extents of the sprite
            context = cairo.Context(cairo.ImageSurface(cairo.FORMAT_A1, 0, 0))
            context.transform(self.get_matrix())
            self.emit("on-render")
            self.__dict__["_sprite_dirty"] = False
            self.graphics._draw(context, 1)


        if not self.graphics.paths:
            self.graphics._draw(cairo.Context(cairo.ImageSurface(cairo.FORMAT_A1, 0, 0)), 1)

        if not self.graphics.paths:
            return None

        context = cairo.Context(cairo.ImageSurface(cairo.FORMAT_A1, 0, 0))

        # bit of a hack around the problem - looking for clip instructions in parent
        # so extents would not get out of it
        clip_extents = None
        for parent in self.get_parents():
            context.transform(parent.get_local_matrix())
            if parent.graphics.paths:
                clip_regions = []
                for instruction, type, path in parent.graphics.paths:
                    if instruction == "clip":
                        context.append_path(path)
                        context.save()
                        context.identity_matrix()

                        clip_regions.append(context.fill_extents())
                        context.restore()
                        context.new_path()
                    elif instruction == "restore" and clip_regions:
                        clip_regions.pop()

                for ext in clip_regions:
                    ext = get_gdk_rectangle(int(ext[0]), int(ext[1]), int(ext[2] - ext[0]), int(ext[3] - ext[1]))
                    intersect, clip_extents = gdk.rectangle_intersect((clip_extents or ext), ext)

        context.transform(self.get_local_matrix())

        for instruction, type, path in self.graphics.paths:
            if type == "path":
                context.append_path(path)
            else:
                getattr(context, instruction)(*path)

        context.identity_matrix()


        ext = context.path_extents()
        ext = get_gdk_rectangle(int(ext[0]), int(ext[1]),
                                int(ext[2] - ext[0]), int(ext[3] - ext[1]))
        if clip_extents:
            intersect, ext = gdk.rectangle_intersect(clip_extents, ext)

        if not ext.width and not ext.height:
            ext = None

        self.__dict__['_stroke_context'] = context

        return ext


    def check_hit(self, x, y):
        """check if the given coordinates are inside the sprite's fill or stroke path"""
        extents = self.get_extents()

        if not extents:
            return False

        if extents.x <= x <= extents.x + extents.width and extents.y <= y <= extents.y + extents.height:
            return self._stroke_context is None or self._stroke_context.in_fill(x, y)
        else:
            return False

    def get_scene(self):
        """returns class:`Scene` the sprite belongs to"""
        if self._scene is None:
            parent = getattr(self, "parent", None)
            if parent:
                self._scene = parent.get_scene()
        return self._scene

    def redraw(self):
        """queue redraw of the sprite. this function is called automatically
           whenever a sprite attribute changes. sprite changes that happen
           during scene redraw are ignored in order to avoid echoes.
           Call scene.redraw() explicitly if you need to redraw in these cases.
        """
        scene = self.get_scene()
        if scene:
            scene.redraw()

    def animate(self, duration = None, easing = None, on_complete = None,
                on_update = None, round = False, **kwargs):
        """Request parent Scene to Interpolate attributes using the internal tweener.
           Specify sprite's attributes that need changing.
           `duration` defaults to 0.4 seconds and `easing` to cubic in-out
           (for others see pytweener.Easing class).

           Example::
             # tween some_sprite to coordinates (50,100) using default duration and easing
             self.animate(x = 50, y = 100)
        """
        scene = self.get_scene()
        if scene:
            return scene.animate(self, duration, easing, on_complete,
                                 on_update, round, **kwargs)
        else:
            for key, val in kwargs.items():
                setattr(self, key, val)
            return None

    def stop_animation(self):
        """stop animation without firing on_complete"""
        scene = self.get_scene()
        if scene:
            scene.stop_animation(self)

    def get_local_matrix(self):
        if self._matrix is None:
            matrix, x, y, pivot_x, pivot_y = cairo.Matrix(), self.x, self.y, self.pivot_x, self.pivot_y

            if self.snap_to_pixel:
                matrix.translate(int(x) + int(pivot_x), int(y) + int(pivot_y))
            else:
                matrix.translate(x + pivot_x, self.y + pivot_y)

            if self.rotation:
                matrix.rotate(self.rotation)


            if self.snap_to_pixel:
                matrix.translate(int(-pivot_x), int(-pivot_y))
            else:
                matrix.translate(-pivot_x, -pivot_y)


            if self.scale_x != 1 or self.scale_y != 1:
                matrix.scale(self.scale_x, self.scale_y)

            self._matrix = matrix

        return cairo.Matrix() * self._matrix


    def get_matrix(self):
        """return sprite's current transformation matrix"""
        if self.parent:
            return self.get_local_matrix() * (self._prev_parent_matrix or self.parent.get_matrix())
        else:
            return self.get_local_matrix()


    def from_scene_coords(self, x=0, y=0):
        """Converts x, y given in the scene coordinates to sprite's local ones
        coordinates"""
        matrix = self.get_matrix()
        matrix.invert()
        return matrix.transform_point(x, y)

    def to_scene_coords(self, x=0, y=0):
        """Converts x, y from sprite's local coordinates to scene coordinates"""
        return self.get_matrix().transform_point(x, y)

    def _draw(self, context, opacity = 1, parent_matrix = None):
        if self.visible is False:
            return

        if (self._sprite_dirty): # send signal to redo the drawing when sprite is dirty
            self.emit("on-render")
            self.__dict__["_sprite_dirty"] = False


        no_matrix = parent_matrix is None
        parent_matrix = parent_matrix or cairo.Matrix()

        # cache parent matrix
        self._prev_parent_matrix = parent_matrix

        matrix = self.get_local_matrix()

        context.save()
        context.transform(matrix)


        if self.cache_as_bitmap:
            self.graphics._draw_as_bitmap(context, self.opacity * opacity)
        else:
            self.graphics._draw(context, self.opacity * opacity)

        context.new_path() #forget about us

        if self.debug:
            exts = self.get_extents()
            if exts:
                debug_colors = ["#c17d11", "#73d216", "#3465a4",
                                "#75507b", "#cc0000", "#edd400", "#f57900"]
                depth = len(self.get_parents())
                color = debug_colors[depth % len(debug_colors)]
                context.save()
                context.identity_matrix()

                scene = self.get_scene()
                if scene:
                    # go figure - seems like the context we are given starts
                    # in window coords when calling identity matrix
                    scene_alloc = self.get_scene().get_allocation()
                    context.translate(scene_alloc.x, scene_alloc.y)


                context.rectangle(exts.x, exts.y, exts.width, exts.height)
                context.set_source_rgb(*Colors.parse(color))
                context.stroke()
                context.restore()

        for sprite in self._z_ordered_sprites:
            sprite._draw(context, self.opacity * opacity, matrix * parent_matrix)


        context.restore()

        # having parent and not being given parent matrix means that somebody
        # is calling draw directly - avoid caching matrix for such a case
        # because when we will get called properly it won't be respecting
        # the parent's transformations otherwise
        if isinstance(self.parent, Sprite) and no_matrix:
            self._prev_parent_matrix = None

    # using _do functions so that subclassees can override these
    def _do_mouse_down(self, event): self.emit("on-mouse-down", event)
    def _do_double_click(self, event): self.emit("on-double-click", event)
    def _do_triple_click(self, event): self.emit("on-triple-click", event)
    def _do_mouse_up(self, event): self.emit("on-mouse-up", event)
    def _do_click(self, event): self.emit("on-click", event)
    def _do_mouse_over(self): self.emit("on-mouse-over")
    def _do_mouse_move(self, event): self.emit("on-mouse-move", event)
    def _do_mouse_out(self): self.emit("on-mouse-out")
    def _do_focus(self): self.emit("on-focus")
    def _do_blur(self): self.emit("on-blur")
    def _do_key_press(self, event):
        self.emit("on-key-press", event)
        return False

    def _do_key_release(self, event):
        self.emit("on-key-release", event)
        return False


class BitmapSprite(Sprite):
    """Caches given image data in a surface similar to targets, which ensures
       that drawing it will be quick and low on CPU.
       Image data can be either :class:`cairo.ImageSurface` or :class:`GdkPixbuf.Pixbuf`
    """
    def __init__(self, image_data = None, cache_mode = None, **kwargs):
        Sprite.__init__(self, **kwargs)

        self.width, self.height = 0, 0
        self.cache_mode = cache_mode or cairo.CONTENT_COLOR_ALPHA
        #: image data
        self.image_data = image_data

        self._surface = None

        self.connect("on-render", self.on_render)


    def on_render(self, sprite):
        if not self._surface:
            self.graphics.rectangle(0, 0, self.width, self.height)
            self.graphics.new_path()

    def update_surface_cache(self):
        """for efficiency the image data is cached on a surface similar to the
        target one. so if you do custom drawing after setting the image data,
        it won't be reflected as the sprite has no idea about what is going on
        there. call this function to trigger cache refresh."""
        self._surface = None


    def __setattr__(self, name, val):
        if self.__dict__.get(name, "hamster_graphics_no_value_really") == val:
            return

        Sprite.__setattr__(self, name, val)
        if name == 'image_data':
            self._surface = None
            if self.image_data:
                self.__dict__['width'] = self.image_data.get_width()
                self.__dict__['height'] = self.image_data.get_height()

    def _draw(self, context, opacity = 1, parent_matrix = None):
        if self.image_data is None or self.width is None or self.height is None:
            return

        if not self._surface:
            # caching image on surface similar to the target
            surface = context.get_target().create_similar(self.cache_mode,
                                                          self.width,
                                                          self.height)

            local_context = cairo.Context(surface)
            if isinstance(self.image_data, GdkPixbuf.Pixbuf):
                gdk.cairo_set_source_pixbuf(local_context, self.image_data, 0, 0)
            else:
                local_context.set_source_surface(self.image_data)
            local_context.paint()

            # add instructions with the resulting surface
            self.graphics.clear()
            self.graphics.rectangle(0, 0, self.width, self.height)
            self.graphics.clip()
            self.graphics.set_source_surface(surface)
            self.graphics.paint()
            self.__dict__['_surface'] = surface


        Sprite._draw(self,  context, opacity, parent_matrix)


class Image(BitmapSprite):
    """Displays image by path. Currently supports only PNG images."""
    def __init__(self, path, **kwargs):
        BitmapSprite.__init__(self, **kwargs)

        #: path to the image
        self.path = path

    def __setattr__(self, name, val):
        BitmapSprite.__setattr__(self, name, val)
        if name == 'path': # load when the value is set to avoid penalty on render
            self.image_data = cairo.ImageSurface.create_from_png(self.path)



class Icon(BitmapSprite):
    """Displays icon by name and size in the theme"""
    def __init__(self, name, size=24, **kwargs):
        BitmapSprite.__init__(self, **kwargs)
        self.theme = gtk.IconTheme.get_default()

        #: icon name from theme
        self.name = name

        #: icon size in pixels
        self.size = size

    def __setattr__(self, name, val):
        BitmapSprite.__setattr__(self, name, val)
        if name in ('name', 'size'): # no other reason to discard cache than just on path change
            if self.__dict__.get('name') and self.__dict__.get('size'):
                self.image_data = self.theme.load_icon(self.name, self.size, 0)
            else:
                self.image_data = None


class Label(Sprite):
    __gsignals__ = {
        "on-change": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, ()),
    }

    cache_attrs = Sprite.cache_attrs | set(("_letter_sizes", "__surface", "_ascent", "_bounds_width", "_measures"))

    def __init__(self, text = "", size = None, color = None,
                 alignment = pango.Alignment.LEFT, single_paragraph = False,
                 max_width = None, wrap = None, ellipsize = None, markup = "",
                 font_desc = None, **kwargs):
        Sprite.__init__(self, **kwargs)
        self.width, self.height = None, None


        self._test_context = cairo.Context(cairo.ImageSurface(cairo.FORMAT_A8, 0, 0))
        self._test_layout = pangocairo.create_layout(self._test_context)


        #: absolute font size in pixels. this will execute set_absolute_size
        #: instead of set_size, which is fractional
        self.size = size

        #: pango.FontDescription, defaults to system font
        self.font_desc = pango.FontDescription(font_desc or _font_desc)

        #: color of label either as hex string or an (r,g,b) tuple
        self.color = color

        self._bounds_width = None

        #: wrapping method. Can be set to pango. [WRAP_WORD, WRAP_CHAR,
        #: WRAP_WORD_CHAR]
        self.wrap = wrap


        #: Ellipsize mode. Can be set to pango.[EllipsizeMode.NONE,
        #: EllipsizeMode.START, EllipsizeMode.MIDDLE, EllipsizeMode.END]
        self.ellipsize = ellipsize

        #: alignment. one of pango.[Alignment.LEFT, Alignment.RIGHT, Alignment.CENTER]
        self.alignment = alignment

        #: If setting is True, do not treat newlines and similar characters as
        #: paragraph separators; instead, keep all text in a single paragraph,
        #: and display a glyph for paragraph separator characters. Used when you
        #: want to allow editing of newlines on a single text line.
        #: Defaults to False
        self.single_paragraph = single_paragraph


        #: maximum  width of the label in pixels. if specified, the label
        #: will be wrapped or ellipsized depending on the wrap and ellpisize settings
        self.max_width = max_width

        self.__surface = None

        #: label text. upon setting will replace markup
        self.text = text

        #: label contents marked up using pango markup. upon setting will replace text
        self.markup = markup

        self._measures = {}

        self.connect("on-render", self.on_render)

        self.graphics_unrelated_attrs = self.graphics_unrelated_attrs | set(("__surface", "_bounds_width", "_measures"))

    def __setattr__(self, name, val):
        if name == "font_desc":
            if isinstance(val, basestring):
                val = pango.FontDescription(val)
            elif isinstance(val, pango.FontDescription):
                val = val.copy()

        if self.__dict__.get(name, "hamster_graphics_no_value_really") != val:
            if name == "width" and val and self.__dict__.get('_bounds_width') and val * pango.SCALE == self.__dict__['_bounds_width']:
                return

            Sprite.__setattr__(self, name, val)


            if name == "width":
                # setting width means consumer wants to contrain the label
                if val is None or val == -1:
                    self.__dict__['_bounds_width'] = None
                else:
                    self.__dict__['_bounds_width'] = val * pango.SCALE


            if name in ("width", "text", "markup", "size", "font_desc", "wrap", "ellipsize", "max_width"):
                self._measures = {}
                # avoid chicken and egg
                if hasattr(self, "size") and (hasattr(self, "text") or hasattr(self, "markup")):
                    if self.size:
                        self.font_desc.set_absolute_size(self.size * pango.SCALE)
                    markup = getattr(self, "markup", "")
                    self.__dict__['width'], self.__dict__['height'] = self.measure(markup or getattr(self, "text", ""), escape = len(markup) == 0)



            if name == 'text':
                if val:
                    self.__dict__['markup'] = ""
                self.emit('on-change')
            elif name == 'markup':
                if val:
                    self.__dict__['text'] = ""
                self.emit('on-change')


    def measure(self, text, escape = True, max_width = None):
        """measures given text with label's font and size.
        returns width, height and ascent. Ascent's null in case if the label
        does not have font face specified (and is thusly using pango)"""

        if escape:
            text = text.replace ("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

        if (max_width, text) in self._measures:
            return self._measures[(max_width, text)]

        width, height = None, None

        context = self._test_context

        layout = self._test_layout
        layout.set_font_description(self.font_desc)
        layout.set_markup(text)
        layout.set_single_paragraph_mode(self.single_paragraph)

        if self.alignment:
            layout.set_alignment(self.alignment)

        if self.wrap is not None:
            layout.set_wrap(self.wrap)
            layout.set_ellipsize(pango.EllipsizeMode.NONE)
        else:
            layout.set_ellipsize(self.ellipsize or pango.EllipsizeMode.END)

        if max_width is not None:
            layout.set_width(max_width * pango.SCALE)
        else:
            if self.max_width:
                max_width = self.max_width * pango.SCALE

            layout.set_width(int(self._bounds_width or max_width or -1))

        width, height = layout.get_pixel_size()

        self._measures[(max_width, text)] = width, height
        return self._measures[(max_width, text)]


    def on_render(self, sprite):
        if not self.text and not self.markup:
            self.graphics.clear()
            return

        self.graphics.set_color(self.color)

        rect_width = self.width

        max_width = 0
        if self.max_width:
            max_width = self.max_width * pango.SCALE

            # when max width is specified and we are told to align in center
            # do that (the pango instruction takes care of aligning within
            # the lines of the text)
            if self.alignment == pango.Alignment.CENTER:
                self.graphics.move_to(-(self.max_width - self.width)/2, 0)

        bounds_width = max_width or self._bounds_width or -1

        text = ""
        if self.markup:
            text = self.markup
        else:
            # otherwise escape pango
            text = self.text.replace ("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

        self.graphics.show_layout(text, self.font_desc,
                                  self.alignment,
                                  bounds_width,
                                  self.wrap,
                                  self.ellipsize,
                                  self.single_paragraph)

        if self._bounds_width:
            rect_width = self._bounds_width / pango.SCALE

        self.graphics.rectangle(0, 0, rect_width, self.height)
        self.graphics.clip()



class Rectangle(Sprite):
    def __init__(self, w, h, corner_radius = 0, fill = None, stroke = None, line_width = 1, **kwargs):
        Sprite.__init__(self, **kwargs)

        #: width
        self.width = w

        #: height
        self.height = h

        #: fill color
        self.fill = fill

        #: stroke color
        self.stroke = stroke

        #: stroke line width
        self.line_width = line_width

        #: corner radius. Set bigger than 0 for rounded corners
        self.corner_radius = corner_radius
        self.connect("on-render", self.on_render)

    def on_render(self, sprite):
        self.graphics.set_line_style(width = self.line_width)
        self.graphics.rectangle(0, 0, self.width, self.height, self.corner_radius)
        self.graphics.fill_stroke(self.fill, self.stroke, line_width = self.line_width)


class Polygon(Sprite):
    def __init__(self, points, fill = None, stroke = None, line_width = 1, **kwargs):
        Sprite.__init__(self, **kwargs)

        #: list of (x,y) tuples that the line should go through. Polygon
        #: will automatically close path.
        self.points = points

        #: fill color
        self.fill = fill

        #: stroke color
        self.stroke = stroke

        #: stroke line width
        self.line_width = line_width

        self.connect("on-render", self.on_render)

    def on_render(self, sprite):
        if not self.points:
            self.graphics.clear()
            return

        self.graphics.move_to(*self.points[0])
        self.graphics.line_to(self.points)

        if self.fill:
            self.graphics.close_path()

        self.graphics.fill_stroke(self.fill, self.stroke, line_width = self.line_width)


class Circle(Sprite):
    def __init__(self, width, height, fill = None, stroke = None, line_width = 1, **kwargs):
        Sprite.__init__(self, **kwargs)

        #: circle width
        self.width = width

        #: circle height
        self.height = height

        #: fill color
        self.fill = fill

        #: stroke color
        self.stroke = stroke

        #: stroke line width
        self.line_width = line_width

        self.connect("on-render", self.on_render)

    def on_render(self, sprite):
        if self.width == self.height:
            radius = self.width / 2.0
            self.graphics.circle(radius, radius, radius)
        else:
            self.graphics.ellipse(0, 0, self.width, self.height)

        self.graphics.fill_stroke(self.fill, self.stroke, line_width = self.line_width)


class Scene(Parent, gtk.DrawingArea):
    """ Drawing area for displaying sprites.
        Add sprites to the Scene by calling :func:`add_child`.
        Scene is descendant of `gtk.DrawingArea <http://www.pygtk.org/docs/pygtk/class-gtkdrawingarea.html>`_
        and thus inherits all it's methods and everything.
    """

    __gsignals__ = {
       # "draw": "override",
       # "configure_event": "override",
        "on-first-frame": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT, )),
        "on-enter-frame": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT, )),
        "on-finish-frame": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT, )),
        "on-resize": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT, )),

        "on-click": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT, gobject.TYPE_PYOBJECT)),
        "on-drag": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT, gobject.TYPE_PYOBJECT)),
        "on-drag-start": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT, gobject.TYPE_PYOBJECT)),
        "on-drag-finish": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT, gobject.TYPE_PYOBJECT)),

        "on-mouse-move": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
        "on-mouse-down": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
        "on-double-click": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
        "on-triple-click": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
        "on-mouse-up": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
        "on-mouse-over": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
        "on-mouse-out": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
        "on-mouse-scroll": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),

        "on-key-press": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
        "on-key-release": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
    }

    def __init__(self, interactive = True, framerate = 60,
                       background_color = None, scale = False, keep_aspect = True,
                       style_class=None):
        gtk.DrawingArea.__init__(self)

        self._style = self.get_style_context()

        #: widget style. One of gtk.STYLE_CLASS_*. By default it's BACKGROUND
        self.style_class = style_class or gtk.STYLE_CLASS_BACKGROUND
        self._style.add_class(self.style_class) # so we know our colors

        #: list of sprites in scene. use :func:`add_child` to add sprites
        self.sprites = []

        self._z_ordered_sprites = []

        # a place where to store child handlers
        self.__dict__['_child_handlers'] = defaultdict(list)

        #: framerate of animation. This will limit how often call for
        #: redraw will be performed (that is - not more often than the framerate). It will
        #: also influence the smoothness of tweeners.
        self.framerate = framerate

        #: Scene width. Will be `None` until first expose (that is until first
        #: on-enter-frame signal below).
        self.width = None

        #: Scene height. Will be `None` until first expose (that is until first
        #: on-enter-frame signal below).
        self.height = None

        #: instance of :class:`pytweener.Tweener` that is used by
        #: :func:`animate` function, but can be also accessed directly for advanced control.
        self.tweener = False
        if pytweener:
            self.tweener = pytweener.Tweener(0.4, pytweener.Easing.Cubic.ease_in_out)

        #: instance of :class:`ColorUtils` class for color parsing
        self.colors = Colors

        #: read only info about current framerate (frames per second)
        self.fps = None # inner frames per second counter

        self._window = None # scenes don't really get reparented

        #: Last known x position of the mouse (set on expose event)
        self.mouse_x = None

        #: Last known y position of the mouse (set on expose event)
        self.mouse_y = None

        #: Background color of the scene. Use either a string with hex color or an RGB triplet.
        self.background_color = background_color

        #: Mouse cursor appearance.
        #: Replace with your own cursor or set to False to have no cursor.
        #: None will revert back the default behavior
        self.mouse_cursor = None

        #: in contrast to the mouse cursor, this one is merely a suggestion and
        #: can be overidden by child sprites
        self.default_mouse_cursor = None

        self._blank_cursor = gdk.Cursor(gdk.CursorType.BLANK_CURSOR)

        self.__previous_mouse_signal_time = None


        #: Miminum distance in pixels for a drag to occur
        self.drag_distance = 1

        self._last_frame_time = None
        self._mouse_sprite = None
        self._drag_sprite = None
        self._mouse_down_sprite = None
        self.__drag_started = False
        self.__drag_start_x, self.__drag_start_y = None, None

        self._mouse_in = False
        self.__last_cursor = None

        self.__drawing_queued = False

        #: When specified, upon window resize the content will be scaled
        #: relative to original window size. Defaults to False.
        self.scale = scale

        #: Should the stage maintain aspect ratio upon scale if
        #: :attr:`Scene.scale` is enabled. Defaults to true.
        self.keep_aspect = keep_aspect

        self._original_width, self._original_height = None,  None

        self._focus_sprite = None # our internal focus management

        self.__last_mouse_move = None

        if interactive:
            self.set_can_focus(True)
            self.set_events(gdk.EventMask.POINTER_MOTION_MASK
                            | gdk.EventMask.LEAVE_NOTIFY_MASK | gdk.EventMask.ENTER_NOTIFY_MASK
                            | gdk.EventMask.BUTTON_PRESS_MASK | gdk.EventMask.BUTTON_RELEASE_MASK
                            | gdk.EventMask.SCROLL_MASK
                            | gdk.EventMask.KEY_PRESS_MASK)
            self.connect("motion-notify-event", self.__on_mouse_move)
            self.connect("enter-notify-event", self.__on_mouse_enter)
            self.connect("leave-notify-event", self.__on_mouse_leave)
            self.connect("button-press-event", self.__on_button_press)
            self.connect("button-release-event", self.__on_button_release)
            self.connect("scroll-event", self.__on_scroll)
            self.connect("key-press-event", self.__on_key_press)
            self.connect("key-release-event", self.__on_key_release)



    def __setattr__(self, name, val):
        if self.__dict__.get(name, "hamster_graphics_no_value_really") == val:
            return

        if name == '_focus_sprite':
            prev_focus = getattr(self, '_focus_sprite', None)
            if prev_focus:
                prev_focus.focused = False
                self.__dict__['_focus_sprite'] = val # drop cache to avoid echoes
                prev_focus._do_blur()

            if val:
                val.focused = True
                val._do_focus()
        elif name == "style_class":
            if hasattr(self, "style_class"):
                self._style.remove_class(self.style_class)
            self._style.add_class(val)
        elif name == "background_color":
            if val:
                self.override_background_color(gtk.StateType.NORMAL,
                                               gdk.RGBA(*Colors.parse(val)))
            else:
                self.override_background_color(gtk.StateType.NORMAL, None)

        self.__dict__[name] = val

    # these two mimic sprite functions so parent check can be avoided
    def from_scene_coords(self, x, y): return x, y
    def to_scene_coords(self, x, y): return x, y
    def get_matrix(self): return cairo.Matrix()
    def get_scene(self): return self


    def animate(self, sprite, duration = None, easing = None, on_complete = None,
                on_update = None, round = False, **kwargs):
        """Interpolate attributes of the given object using the internal tweener
           and redrawing scene after every tweener update.
           Specify the sprite and sprite's attributes that need changing.
           `duration` defaults to 0.4 seconds and `easing` to cubic in-out
           (for others see pytweener.Easing class).

           Redraw is requested right after creating the animation.
           Example::

             # tween some_sprite to coordinates (50,100) using default duration and easing
             scene.animate(some_sprite, x = 50, y = 100)
        """
        if not self.tweener: # here we complain
            raise Exception("pytweener was not found. Include it to enable animations")

        tween = self.tweener.add_tween(sprite,
                                       duration=duration,
                                       easing=easing,
                                       on_complete=on_complete,
                                       on_update=on_update,
                                       round=round,
                                       **kwargs)
        self.redraw()
        return tween


    def stop_animation(self, sprites):
        """stop animation without firing on_complete"""
        if isinstance(sprites, list) is False:
            sprites = [sprites]

        for sprite in sprites:
            self.tweener.kill_tweens(sprite)


    def redraw(self):
        """Queue redraw. The redraw will be performed not more often than
           the `framerate` allows"""
        if self.__drawing_queued == False: #if we are moving, then there is a timeout somewhere already
            self.__drawing_queued = True
            self._last_frame_time = dt.datetime.now()
            gobject.timeout_add(1000 / self.framerate, self.__redraw_loop)

    def __redraw_loop(self):
        """loop until there is nothing more to tween"""
        self.queue_draw() # this will trigger do_expose_event when the current events have been flushed

        self.__drawing_queued = self.tweener and self.tweener.has_tweens()
        return self.__drawing_queued


    def do_draw(self, context):
        if self.scale:
            aspect_x = self.width / self._original_width
            aspect_y = self.height / self._original_height
            if self.keep_aspect:
                aspect_x = aspect_y = min(aspect_x, aspect_y)
            context.scale(aspect_x, aspect_y)

        if self.fps is None:
            self._window = self.get_window()
            self.emit("on-first-frame", context)

        cursor, self.mouse_x, self.mouse_y, mods = self._window.get_pointer()


        # update tweens
        now = dt.datetime.now()
        delta = (now - (self._last_frame_time or dt.datetime.now())).total_seconds()
        self._last_frame_time = now
        if self.tweener:
            self.tweener.update(delta)

        self.fps = 1 / delta

        # start drawing
        self.emit("on-enter-frame", context)
        for sprite in self._z_ordered_sprites:
            sprite._draw(context)

        self.__check_mouse(self.mouse_x, self.mouse_y)
        self.emit("on-finish-frame", context)

        # reset the mouse signal time as redraw means we are good now
        self.__previous_mouse_signal_time = None


    def do_configure_event(self, event):
        if self._original_width is None:
            self._original_width = float(event.width)
            self._original_height = float(event.height)

        width, height = self.width, self.height
        self.width, self.height = event.width, event.height

        if width != event.width or height != event.height:
            self.emit("on-resize", event) # so that sprites can listen to it



    def all_mouse_sprites(self):
        """Returns flat list of the sprite tree for simplified iteration"""
        def all_recursive(sprites):
            if not sprites:
                return

            for sprite in sprites:
                if sprite.visible:
                    yield sprite

                    for child in all_recursive(sprite.get_mouse_sprites()):
                        yield child

        return all_recursive(self.get_mouse_sprites())


    def get_sprite_at_position(self, x, y):
        """Returns the topmost visible interactive sprite for given coordinates"""
        over = None
        for sprite in self.all_mouse_sprites():
            if sprite.interactive and sprite.check_hit(x, y):
                over = sprite

        return over


    def __check_mouse(self, x, y):
        if x is None or self._mouse_in == False:
            return

        cursor = None
        over = None

        if self.mouse_cursor is not None:
            cursor = self.mouse_cursor

        if cursor is None and self._drag_sprite:
            drag_cursor = self._drag_sprite._get_mouse_cursor()
            if drag_cursor:
                cursor = drag_cursor

        #check if we have a mouse over
        if self._drag_sprite is None:
            over = self.get_sprite_at_position(x, y)
            if self._mouse_sprite and self._mouse_sprite != over:
                self._mouse_sprite._do_mouse_out()
                self.emit("on-mouse-out", self._mouse_sprite)

            if over and cursor is None:
                sprite_cursor = over._get_mouse_cursor()
                if sprite_cursor:
                    cursor = sprite_cursor

            if over and over != self._mouse_sprite:
                over._do_mouse_over()
                self.emit("on-mouse-over", over)

            self._mouse_sprite = over

        if cursor is None:
            cursor = self.default_mouse_cursor or gdk.CursorType.ARROW # default
        elif cursor is False:
            cursor = self._blank_cursor

        if self.__last_cursor is None or cursor != self.__last_cursor:
            if isinstance(cursor, gdk.Cursor):
                self._window.set_cursor(cursor)
            else:
                self._window.set_cursor(gdk.Cursor(cursor))

            self.__last_cursor = cursor


    """ mouse events """
    def __on_mouse_move(self, scene, event):
        if self.__last_mouse_move:
            gobject.source_remove(self.__last_mouse_move)

        self.mouse_x, self.mouse_y = event.x, event.y

        # don't emit mouse move signals more often than every 0.05 seconds
        timeout = dt.timedelta(seconds=0.05)
        if self.__previous_mouse_signal_time and dt.datetime.now() - self.__previous_mouse_signal_time < timeout:
            self.__last_mouse_move = gobject.timeout_add((timeout - (dt.datetime.now() - self.__previous_mouse_signal_time)).microseconds / 1000,
                                                         self.__on_mouse_move,
                                                         scene,
                                                         event.copy())
            return

        state = event.state


        if self._mouse_down_sprite and self._mouse_down_sprite.interactive \
           and self._mouse_down_sprite.draggable and gdk.ModifierType.BUTTON1_MASK & event.state:
            # dragging around
            if not self.__drag_started:
                drag_started = (self.__drag_start_x is not None and \
                               (self.__drag_start_x - event.x) ** 2 + \
                               (self.__drag_start_y - event.y) ** 2 > self.drag_distance ** 2)

                if drag_started:
                    self._drag_sprite = self._mouse_down_sprite
                    self._mouse_down_sprite.emit("on-drag-start", event)
                    self.emit("on-drag-start", self._drag_sprite, event)
                    self.start_drag(self._drag_sprite, self.__drag_start_x, self.__drag_start_y)

        else:
            # avoid double mouse checks - the redraw will also check for mouse!
            if not self.__drawing_queued:
                self.__check_mouse(event.x, event.y)

        if self._drag_sprite:
            diff_x, diff_y = event.x - self.__drag_start_x, event.y - self.__drag_start_y
            if isinstance(self._drag_sprite.parent, Sprite):
                matrix = self._drag_sprite.parent.get_matrix()
                matrix.invert()
                diff_x, diff_y = matrix.transform_distance(diff_x, diff_y)

            self._drag_sprite.x, self._drag_sprite.y = self._drag_sprite.drag_x + diff_x, self._drag_sprite.drag_y + diff_y

            self._drag_sprite.emit("on-drag", event)
            self.emit("on-drag", self._drag_sprite, event)

        if self._mouse_sprite:
            sprite_event = gdk.Event.copy(event)
            sprite_event.x, sprite_event.y = self._mouse_sprite.from_scene_coords(event.x, event.y)
            self._mouse_sprite._do_mouse_move(sprite_event)

        self.emit("on-mouse-move", event)
        self.__previous_mouse_signal_time = dt.datetime.now()


    def start_drag(self, sprite, cursor_x = None, cursor_y = None):
        """start dragging given sprite"""
        cursor_x, cursor_y = cursor_x or sprite.x, cursor_y or sprite.y

        self._mouse_down_sprite = self._drag_sprite = sprite
        sprite.drag_x, sprite.drag_y = self._drag_sprite.x, self._drag_sprite.y
        self.__drag_start_x, self.__drag_start_y = cursor_x, cursor_y
        self.__drag_started = True


    def __on_mouse_enter(self, scene, event):
        self._mouse_in = True

    def __on_mouse_leave(self, scene, event):
        self._mouse_in = False
        if self._mouse_sprite:
            self._mouse_sprite._do_mouse_out()
            self.emit("on-mouse-out", self._mouse_sprite)
            self._mouse_sprite = None


    def __on_button_press(self, scene, event):
        target = self.get_sprite_at_position(event.x, event.y)
        if not self.__drag_started:
            self.__drag_start_x, self.__drag_start_y = event.x, event.y

        self._mouse_down_sprite = target

        # differentiate between the click count!
        if event.type == gdk.EventType.BUTTON_PRESS:
            self.emit("on-mouse-down", event)
            if target:
                target_event = gdk.Event.copy(event)
                target_event.x, target_event.y = target.from_scene_coords(event.x, event.y)
                target._do_mouse_down(target_event)
            else:
                scene._focus_sprite = None  # lose focus if mouse ends up nowhere
        elif event.type == gdk.EventType._2BUTTON_PRESS:
            self.emit("on-double-click", event)
            if target:
                target_event = gdk.Event.copy(event)
                target_event.x, target_event.y = target.from_scene_coords(event.x, event.y)
                target._do_double_click(target_event)
        elif event.type == gdk.EventType._3BUTTON_PRESS:
            self.emit("on-triple-click", event)
            if target:
                target_event = gdk.Event.copy(event)
                target_event.x, target_event.y = target.from_scene_coords(event.x, event.y)
                target._do_triple_click(target_event)

        self.__check_mouse(event.x, event.y)
        return True


    def __on_button_release(self, scene, event):
        target = self.get_sprite_at_position(event.x, event.y)

        if target:
            target._do_mouse_up(event)
        self.emit("on-mouse-up", event)

        # trying to not emit click and drag-finish at the same time
        click = not self.__drag_started or (event.x - self.__drag_start_x) ** 2 + \
                                           (event.y - self.__drag_start_y) ** 2 < self.drag_distance
        if (click and self.__drag_started == False) or not self._drag_sprite:
            if target and target == self._mouse_down_sprite:
                target_event = gdk.Event.copy(event)
                target_event.x, target_event.y = target.from_scene_coords(event.x, event.y)
                target._do_click(target_event)

            self.emit("on-click", event, target)

        self._mouse_down_sprite = None
        self.__drag_started = False
        self.__drag_start_x, self__drag_start_y = None, None

        if self._drag_sprite:
            self._drag_sprite.drag_x, self._drag_sprite.drag_y = None, None
            drag_sprite, self._drag_sprite = self._drag_sprite, None
            drag_sprite.emit("on-drag-finish", event)
            self.emit("on-drag-finish", drag_sprite, event)
        self.__check_mouse(event.x, event.y)
        return True


    def __on_scroll(self, scene, event):
        target = self.get_sprite_at_position(event.x, event.y)
        if target:
            target.emit("on-mouse-scroll", event)
        self.emit("on-mouse-scroll", event)
        return True

    def __on_key_press(self, scene, event):
        handled = False
        if self._focus_sprite:
            handled = self._focus_sprite._do_key_press(event)
        if not handled:
            self.emit("on-key-press", event)
        return True

    def __on_key_release(self, scene, event):
        handled = False
        if self._focus_sprite:
            handled = self._focus_sprite._do_key_release(event)
        if not handled:
            self.emit("on-key-release", event)
        return True

########NEW FILE########
__FILENAME__ = layout
# - coding: utf-8 -

# Copyright (c) 2011-2012 Media Modifications, Ltd.
# Copyright (c) 2014 Toms Baugis <toms.baugis@gmail.com>
# Dual licensed under the MIT or GPL Version 2 licenses.

import datetime as dt
import math
from gi.repository import Gtk as gtk
from gi.repository import Gdk as gdk
from gi.repository import GObject as gobject
from gi.repository import Pango as pango
from collections import defaultdict

import graphics


class Widget(graphics.Sprite):
    """Base class for all widgets. You can use the width and height attributes
    to request a specific width."""

    _sizing_attributes = set(("visible", "min_width", "min_height",
                              "expand", "fill", "spacing",
                              "horizontal_spacing", "vertical_spacing", "x_align",
                              "y_align"))

    min_width = None  #: minimum width of the widget
    min_height = None #: minimum height of the widget

    #: Whether the child should receive extra space when the parent grows.
    expand = True

    #: Whether extra space given to the child should be allocated to the
    #: child or used as padding. Edit :attr:`x_align` and
    #: :attr:`y_align` properties to adjust alignment when fill is set to False.
    fill = True

    #: horizontal alignment within the parent. Works when :attr:`fill` is False
    x_align = 0.5

    #: vertical alignment within the parent. Works when :attr:`fill` is False
    y_align = 0.5

    #: child padding - shorthand to manipulate padding in pixels ala CSS. tuple
    #: of one to four elements. Setting this value overwrites values of
    #: :attr:`padding_top`, :attr:`padding_right`, :attr:`padding_bottom`
    #: and :attr:`padding_left`
    padding = None
    padding_top = None    #: child padding - top
    padding_right = None  #: child padding - right
    padding_bottom = None #: child padding - bottom
    padding_left = None   #: child padding - left

    #: widget margins - shorthand to manipulate margin in pixels ala CSS. tuple
    #: of one to four elements. Setting this value overwrites values of
    #: :attr:`margin_top`, :attr:`margin_right`, :attr:`margin_bottom` and
    #: :attr:`margin_left`
    margin = 0
    margin_top = 0     #: top margin
    margin_right = 0   #: right margin
    margin_bottom = 0  #: bottom margin
    margin_left = 0    #: left margin

    enabled = True #: whether the widget is enabled

    mouse_cursor = False #: Mouse cursor. see :attr:`graphics.Sprite.mouse_cursor` for values

    def __init__(self, width = None, height = None, expand = None, fill = None,
                 x_align = None, y_align = None,
                 padding_top = None, padding_right = None,
                 padding_bottom = None, padding_left = None, padding = None,
                 margin_top = None, margin_right = None,
                 margin_bottom = None, margin_left = None, margin = None,
                 enabled = None, **kwargs):
        graphics.Sprite.__init__(self, **kwargs)

        def set_if_not_none(name, val):
            # set values - avoid pitfalls of None vs 0/False
            if val is not None:
                setattr(self, name, val)

        set_if_not_none("min_width", width)
        set_if_not_none("min_height", height)

        self._enabled = enabled if enabled is not None else self.__class__.enabled

        set_if_not_none("fill", fill)
        set_if_not_none("expand", expand)
        set_if_not_none("x_align", x_align)
        set_if_not_none("y_align", y_align)

        # set padding
        # (class, subclass, instance, and constructor)
        if padding is not None or self.padding is not None:
            self.padding = padding if padding is not None else self.padding
        self.padding_top = padding_top or self.__class__.padding_top or self.padding_top or 0
        self.padding_right = padding_right or self.__class__.padding_right or self.padding_right or 0
        self.padding_bottom = padding_bottom or self.__class__.padding_bottom or self.padding_bottom or 0
        self.padding_left = padding_left or self.__class__.padding_left or self.padding_left or 0

        if margin is not None or self.margin is not None:
            self.margin = margin if margin is not None else self.margin
        self.margin_top = margin_top or self.__class__.margin_top or self.margin_top or 0
        self.margin_right = margin_right or self.__class__.margin_right or self.margin_right or 0
        self.margin_bottom = margin_bottom or self.__class__.margin_bottom or self.margin_bottom or 0
        self.margin_left = margin_left or self.__class__.margin_left or self.margin_left or 0


        #: width in pixels that have been allocated to the widget by parent
        self.alloc_w = width if width is not None else self.min_width

        #: height in pixels that have been allocated to the widget by parent
        self.alloc_h = height if height is not None else self.min_height

        self.connect_after("on-render", self.__on_render)
        self.connect("on-mouse-over", self.__on_mouse_over)
        self.connect("on-mouse-out", self.__on_mouse_out)
        self.connect("on-mouse-down", self.__on_mouse_down)
        self.connect("on-key-press", self.__on_key_press)

        self._children_resize_queued = True
        self._scene_resize_handler = None


    def __setattr__(self, name, val):
        # forward width and height to min_width and min_height as i've ruined the setters a bit i think
        if name == "width":
            name = "min_width"
        elif name == "height":
            name = "min_height"
        elif name == 'enabled':
            name = '_enabled'
        elif name == "padding":
            val = val or 0
            if isinstance(val, int):
                val = (val, )

            if len(val) == 1:
                self.padding_top = self.padding_right = self.padding_bottom = self.padding_left = val[0]
            elif len(val) == 2:
                self.padding_top = self.padding_bottom = val[0]
                self.padding_right = self.padding_left = val[1]

            elif len(val) == 3:
                self.padding_top = val[0]
                self.padding_right = self.padding_left = val[1]
                self.padding_bottom = val[2]
            elif len(val) == 4:
                self.padding_top, self.padding_right, self.padding_bottom, self.padding_left = val
            return

        elif name == "margin":
            val = val or 0
            if isinstance(val, int):
                val = (val, )

            if len(val) == 1:
                self.margin_top = self.margin_right = self.margin_bottom = self.margin_left = val[0]
            elif len(val) == 2:
                self.margin_top = self.margin_bottom = val[0]
                self.margin_right = self.margin_left = val[1]
            elif len(val) == 3:
                self.margin_top = val[0]
                self.margin_right = self.margin_left = val[1]
                self.margin_bottom = val[2]
            elif len(val) == 4:
                self.margin_top, self.margin_right, self.margin_bottom, self.margin_left = val
            return


        if self.__dict__.get(name, "hamster_graphics_no_value_really") == val:
            return

        graphics.Sprite.__setattr__(self, name, val)

        # in widget case visibility affects placement and everything so request repositioning from parent
        if name == 'visible' and getattr(self, "parent", None) and getattr(self.parent, "resize_children", None):
            self.parent.resize_children()

        elif name == '_enabled' and getattr(self, "sprites", None):
            self._propagate_enabledness()

        if name in self._sizing_attributes:
            self.queue_resize()

    def _propagate_enabledness(self):
        # runs down the tree and marks all child sprites as dirty as
        # enabledness is inherited
        self._sprite_dirty = True
        for sprite in self.sprites:
            next_call = getattr(sprite, "_propagate_enabledness", None)
            if next_call:
                next_call()

    def _with_rotation(self, w, h):
        """calculate the actual dimensions after rotation"""
        res_w = abs(w * math.cos(self.rotation) + h * math.sin(self.rotation))
        res_h = abs(h * math.cos(self.rotation) + w * math.sin(self.rotation))
        return res_w, res_h

    @property
    def horizontal_padding(self):
        """total calculated horizontal padding. A read-only property."""
        return self.padding_left + self.padding_right

    @property
    def vertical_padding(self):
        """total calculated vertical padding.  A read-only property."""
        return self.padding_top + self.padding_bottom

    def __on_mouse_over(self, sprite):
        cursor, mouse_x, mouse_y, mods = sprite.get_scene().get_window().get_pointer()
        if self.tooltip and not gdk.ModifierType.BUTTON1_MASK & mods:
            self._set_tooltip(self.tooltip)


    def __on_mouse_out(self, sprite):
        if self.tooltip:
            self._set_tooltip(None)

    def __on_mouse_down(self, sprite, event):
        if self.can_focus:
            self.grab_focus()
        if self.tooltip:
            self._set_tooltip(None)

    def __on_key_press(self, sprite, event):
        if event.keyval in (gdk.KEY_Tab, gdk.KEY_ISO_Left_Tab):
            idx = self.parent.sprites.index(self)

            if event.state & gdk.ModifierType.SHIFT_MASK: # going backwards
                if idx > 0:
                    idx -= 1
                    self.parent.sprites[idx].grab_focus()
            else:
                if idx < len(self.parent.sprites) - 1:
                    idx += 1
                    self.parent.sprites[idx].grab_focus()


    def queue_resize(self):
        """request the element to re-check it's child sprite sizes"""
        self._children_resize_queued = True
        parent = getattr(self, "parent", None)
        if parent and isinstance(parent, graphics.Sprite) and hasattr(parent, "queue_resize"):
            parent.queue_resize()


    def get_min_size(self):
        """returns size required by the widget"""
        if self.visible == False:
            return 0, 0
        else:
            return ((self.min_width or 0) + self.horizontal_padding + self.margin_left + self.margin_right,
                    (self.min_height or 0) + self.vertical_padding + self.margin_top + self.margin_bottom)

    def get_height_for_width_size(self):
        return self.get_min_size()


    def insert(self, index = 0, *widgets):
        """insert widget in the sprites list at the given index.
        by default will prepend."""
        for widget in widgets:
            self._add(widget, index)
            index +=1 # as we are moving forwards
        self._sort()


    def insert_before(self, target):
        """insert this widget into the targets parent before the target"""
        if not target.parent:
            return
        target.parent.insert(target.parent.sprites.index(target), self)

    def insert_after(self, target):
        """insert this widget into the targets parent container after the target"""
        if not target.parent:
            return
        target.parent.insert(target.parent.sprites.index(target) + 1, self)


    @property
    def width(self):
        """width in pixels"""
        alloc_w = self.alloc_w

        if self.parent and isinstance(self.parent, graphics.Scene):
            alloc_w = self.parent.width

            def res(scene, event):
                if self.parent:
                    self.queue_resize()
                else:
                    scene.disconnect(self._scene_resize_handler)
                    self._scene_resize_handler = None


            if not self._scene_resize_handler:
                # TODO - disconnect on reparenting
                self._scene_resize_handler = self.parent.connect("on-resize", res)


        min_width = (self.min_width or 0) + self.margin_left + self.margin_right
        w = alloc_w if alloc_w is not None and self.fill else min_width
        w = max(w or 0, self.get_min_size()[0])
        return w - self.margin_left - self.margin_right

    @property
    def height(self):
        """height in pixels"""
        alloc_h = self.alloc_h

        if self.parent and isinstance(self.parent, graphics.Scene):
            alloc_h = self.parent.height

        min_height = (self.min_height or 0) + self.margin_top + self.margin_bottom
        h = alloc_h if alloc_h is not None and self.fill else min_height
        h = max(h or 0, self.get_min_size()[1])
        return h - self.margin_top - self.margin_bottom

    @property
    def enabled(self):
        """whether the user is allowed to interact with the
        widget. Item is enabled only if all it's parent elements are"""
        enabled = self._enabled
        if not enabled:
            return False

        if self.parent and isinstance(self.parent, Widget):
            if self.parent.enabled == False:
                return False

        return True


    def __on_render(self, sprite):
        self.do_render()
        if self.debug:
            self.graphics.save_context()

            w, h = self.width, self.height
            if hasattr(self, "get_height_for_width_size"):
                w2, h2 = self.get_height_for_width_size()
                w2 = w2 - self.margin_left - self.margin_right
                h2 = h2 - self.margin_top - self.margin_bottom
                w, h = max(w, w2), max(h, h2)

            self.graphics.rectangle(0.5, 0.5, w, h)
            self.graphics.set_line_style(3)
            self.graphics.stroke("#666", 0.5)
            self.graphics.restore_context()

            if self.pivot_x or self.pivot_y:
                self.graphics.fill_area(self.pivot_x - 3, self.pivot_y - 3, 6, 6, "#666")


    def do_render(self):
        """this function is called in the on-render event. override it to do
           any drawing. subscribing to the "on-render" event will work too, but
           overriding this method is preferred for easier subclassing.
        """
        pass





def get_min_size(sprite):
    if hasattr(sprite, "get_min_size"):
        min_width, min_height = sprite.get_min_size()
    else:
        min_width, min_height = getattr(sprite, "width", 0), getattr(sprite, "height", 0)

    min_width = min_width * sprite.scale_x
    min_height = min_height * sprite.scale_y

    return min_width, min_height

def get_props(sprite):
    # gets all the relevant info for containers and puts it in a uniform dict.
    # this way we can access any object without having to check types and such
    keys = ("margin_top", "margin_right", "margin_bottom", "margin_left",
            "padding_top", "padding_right", "padding_bottom", "padding_left")
    res = dict((key, getattr(sprite, key, 0)) for key in keys)
    res["expand"] = getattr(sprite, "expand", True)

    return sprite, res


class Container(Widget):
    """The base container class that all other containers inherit from.
       You can insert any sprite in the container, just make sure that it either
       has width and height defined so that the container can do alignment, or
       for more sophisticated cases, make sure it has get_min_size function that
       returns how much space is needed.

       Normally while performing layout the container will update child sprites
       and set their alloc_h and alloc_w properties. The `alloc` part is short
       for allocated. So use that when making rendering decisions.
    """
    cache_attrs = Widget.cache_attrs | set(('_cached_w', '_cached_h'))
    _sizing_attributes = Widget._sizing_attributes | set(('padding_top', 'padding_right', 'padding_bottom', 'padding_left'))

    def __init__(self, contents = None, **kwargs):
        Widget.__init__(self, **kwargs)

        #: contents of the container - either a widget or a list of widgets
        self.contents = contents
        self._cached_w, self._cached_h = None, None


    def __setattr__(self, name, val):
        if self.__dict__.get(name, "hamster_graphics_no_value_really") == val:
            return

        Widget.__setattr__(self, name, val)
        if name == 'contents':
            if val:
                if isinstance(val, graphics.Sprite):
                    val = [val]
                self.add_child(*val)
            if self.sprites and self.sprites != val:
                self.remove_child(*list(set(self.sprites) ^ set(val or [])))

        if name in ("alloc_w", "alloc_h") and val:
            self.__dict__['_cached_w'], self.__dict__['_cached_h'] = None, None
            self._children_resize_queued = True


    @property
    def contents(self):
        return self.sprites


    def _Widget__on_render(self, sprite):
        if self._children_resize_queued:
            self.resize_children()
            self.__dict__['_children_resize_queued'] = False
        Widget._Widget__on_render(self, sprite)


    def _add(self, *sprites):
        Widget._add(self, *sprites)
        self.queue_resize()

    def remove_child(self, *sprites):
        Widget.remove_child(self, *sprites)
        self.queue_resize()

    def queue_resize(self):
        self.__dict__['_cached_w'], self.__dict__['_cached_h'] = None, None
        Widget.queue_resize(self)

    def get_min_size(self):
        # by default max between our requested size and the biggest child
        if self.visible == False:
            return 0, 0

        if self._cached_w is None:
            sprites = [sprite for sprite in self.sprites if sprite.visible]
            width = max([get_min_size(sprite)[0] for sprite in sprites] or [0])
            width += self.horizontal_padding  + self.margin_left + self.margin_right

            height = max([get_min_size(sprite)[1] for sprite in sprites] or [0])
            height += self.vertical_padding + self.margin_top + self.margin_bottom

            self._cached_w, self._cached_h = max(width, self.min_width or 0), max(height, self.min_height or 0)

        return self._cached_w, self._cached_h

    def resize_children(self):
        """default container alignment is to pile stuff just up, respecting only
        padding, margin and element's alignment properties"""
        width = self.width - self.horizontal_padding
        height = self.height - self.vertical_padding

        for sprite, props in (get_props(sprite) for sprite in self.sprites if sprite.visible):
            sprite.alloc_w = width
            sprite.alloc_h = height

            w, h = getattr(sprite, "width", 0), getattr(sprite, "height", 0)
            if hasattr(sprite, "get_height_for_width_size"):
                w2, h2 = sprite.get_height_for_width_size()
                w, h = max(w, w2), max(h, h2)

            w = w * sprite.scale_x + props["margin_left"] + props["margin_right"]
            h = h * sprite.scale_y + props["margin_top"] + props["margin_bottom"]

            sprite.x = self.padding_left + props["margin_left"] + (max(sprite.alloc_w * sprite.scale_x, w) - w) * getattr(sprite, "x_align", 0)
            sprite.y = self.padding_top + props["margin_top"] + (max(sprite.alloc_h * sprite.scale_y, h) - h) * getattr(sprite, "y_align", 0)


        self.__dict__['_children_resize_queued'] = False


class Bin(Container):
    """A container with only one child. Adding new children will throw the
    previous ones out"""
    def __init__(self, contents = None, **kwargs):
        Container.__init__(self, contents, **kwargs)

    @property
    def child(self):
        """child sprite. shorthand for self.sprites[0]"""
        return self.sprites[0] if self.sprites else None

    def get_height_for_width_size(self):
        if self._children_resize_queued:
            self.resize_children()

        sprites = [sprite for sprite in self.sprites if sprite.visible]
        width, height = 0, 0
        for sprite in sprites:
            if hasattr(sprite, "get_height_for_width_size"):
                w, h = sprite.get_height_for_width_size()
            else:
                w, h = getattr(sprite, "width", 0), getattr(sprite, "height", 0)

            w, h = w * sprite.scale_x, h * sprite.scale_y

            width = max(width, w)
            height = max(height, h)

        #width = width + self.horizontal_padding + self.margin_left + self.margin_right
        #height = height + self.vertical_padding + self.margin_top + self.margin_bottom

        return width, height


    def add_child(self, *sprites):
        if not sprites:
            return

        sprite = sprites[-1] # there can be just one

        # performing add then remove to not screw up coordinates in
        # a strange reparenting case
        Container.add_child(self, sprite)
        if self.sprites and self.sprites[0] != sprite:
            self.remove_child(*list(set(self.sprites) ^ set([sprite])))



class Fixed(Container):
    """Basic container that does not care about child positions. Handy if
       you want to place stuff yourself or do animations.
    """
    def __init__(self, contents = None, **kwargs):
        Container.__init__(self, contents, **kwargs)

    def resize_children(self):
        # don't want
        pass



class Box(Container):
    """Align children either horizontally or vertically.
        Normally you would use :class:`HBox` or :class:`VBox` to be
        specific but this one is suited so you can change the packing direction
        dynamically.
    """
    #: spacing in pixels between children
    spacing = 5

    #: whether the box is packing children horizontally (from left to right) or vertically (from top to bottom)
    orient_horizontal = True

    def __init__(self, contents = None, horizontal = None, spacing = None, **kwargs):
        Container.__init__(self, contents, **kwargs)

        if horizontal is not None:
            self.orient_horizontal = horizontal

        if spacing is not None:
            self.spacing = spacing

    def get_total_spacing(self):
        # now lay them out
        padding_sprites = 0
        for sprite in self.sprites:
            if sprite.visible:
                if getattr(sprite, "expand", True):
                    padding_sprites += 1
                else:
                    if hasattr(sprite, "get_min_size"):
                        size = sprite.get_min_size()[0] if self.orient_horizontal else sprite.get_min_size()[1]
                    else:
                        size = getattr(sprite, "width", 0) * sprite.scale_x if self.orient_horizontal else getattr(sprite, "height", 0) * sprite.scale_y

                    if size > 0:
                        padding_sprites +=1
        return self.spacing * max(padding_sprites - 1, 0)


    def resize_children(self):
        if not self.parent:
            return

        width = self.width - self.padding_left - self.padding_right
        height = self.height - self.padding_top - self.padding_bottom

        sprites = [get_props(sprite) for sprite in self.sprites if sprite.visible]

        # calculate if we have any spare space
        sprite_sizes = []
        for sprite, props in sprites:
            if self.orient_horizontal:
                sprite.alloc_h = height / sprite.scale_y
                size = get_min_size(sprite)[0]
                size = size + props["margin_left"] + props["margin_right"]
            else:
                sprite.alloc_w = width / sprite.scale_x
                size = get_min_size(sprite)[1]

                if hasattr(sprite, "get_height_for_width_size"):
                    size = max(size, sprite.get_height_for_width_size()[1] * sprite.scale_y)
                size = size + props["margin_top"] + props["margin_bottom"]
            sprite_sizes.append(size)


        remaining_space = width if self.orient_horizontal else height
        if sprite_sizes:
            remaining_space = remaining_space - sum(sprite_sizes) - self.get_total_spacing()


        interested_sprites = [sprite for sprite, props in sprites if getattr(sprite, "expand", True)]


        # in order to stay pixel sharp we will recalculate remaining bonus
        # each time we give up some of the remaining space
        remaining_interested = len(interested_sprites)
        bonus = 0
        if remaining_space > 0 and interested_sprites:
            bonus = int(remaining_space / remaining_interested)

        actual_h = 0
        x_pos, y_pos = 0, 0

        for (sprite, props), min_size in zip(sprites, sprite_sizes):
            sprite_bonus = 0
            if sprite in interested_sprites:
                sprite_bonus = bonus
                remaining_interested -= 1
                remaining_space -= bonus
                if remaining_interested:
                    bonus = int(float(remaining_space) / remaining_interested)


            if self.orient_horizontal:
                sprite.alloc_w = (min_size + sprite_bonus) / sprite.scale_x
            else:
                sprite.alloc_h = (min_size + sprite_bonus) / sprite.scale_y

            w, h = getattr(sprite, "width", 0), getattr(sprite, "height", 0)
            if hasattr(sprite, "get_height_for_width_size"):
                w2, h2 = sprite.get_height_for_width_size()
                w, h = max(w, w2), max(h, h2)

            w = w * sprite.scale_x + props["margin_left"] + props["margin_right"]
            h = h * sprite.scale_y + props["margin_top"] + props["margin_bottom"]


            sprite.x = self.padding_left + x_pos + props["margin_left"] + (max(sprite.alloc_w * sprite.scale_x, w) - w) * getattr(sprite, "x_align", 0.5)
            sprite.y = self.padding_top + y_pos + props["margin_top"] + (max(sprite.alloc_h * sprite.scale_y, h) - h) * getattr(sprite, "y_align", 0.5)


            actual_h = max(actual_h, h * sprite.scale_y)

            if (min_size + sprite_bonus) > 0:
                if self.orient_horizontal:
                    x_pos += int(max(w, sprite.alloc_w * sprite.scale_x)) + self.spacing
                else:
                    y_pos += max(h, sprite.alloc_h * sprite.scale_y) + self.spacing


        if self.orient_horizontal:
            for sprite, props in sprites:
                sprite.__dict__['alloc_h'] = actual_h

        self.__dict__['_children_resize_queued'] = False

    def get_height_for_width_size(self):
        if self._children_resize_queued:
            self.resize_children()

        sprites = [sprite for sprite in self.sprites if sprite.visible]
        width, height = 0, 0
        for sprite in sprites:
            if hasattr(sprite, "get_height_for_width_size"):
                w, h = sprite.get_height_for_width_size()
            else:
                w, h = getattr(sprite, "width", 0), getattr(sprite, "height", 0)

            w, h = w * sprite.scale_x, h * sprite.scale_y


            if self.orient_horizontal:
                width += w
                height = max(height, h)
            else:
                width = max(width, w)
                height = height + h

        if self.orient_horizontal:
            width = width + self.get_total_spacing()
        else:
            height = height + self.get_total_spacing()

        width = width + self.horizontal_padding + self.margin_left + self.margin_right
        height = height + self.vertical_padding + self.margin_top + self.margin_bottom

        return width, height



    def get_min_size(self):
        if self.visible == False:
            return 0, 0

        if self._cached_w is None:
            sprites = [sprite for sprite in self.sprites if sprite.visible]

            width, height = 0, 0
            for sprite in sprites:
                if hasattr(sprite, "get_min_size"):
                    w, h = sprite.get_min_size()
                else:
                    w, h = getattr(sprite, "width", 0), getattr(sprite, "height", 0)

                w, h = w * sprite.scale_x, h * sprite.scale_y

                if self.orient_horizontal:
                    width += w
                    height = max(height, h)
                else:
                    width = max(width, w)
                    height = height + h

            if self.orient_horizontal:
                width = width + self.get_total_spacing()
            else:
                height = height + self.get_total_spacing()

            width = width + self.horizontal_padding + self.margin_left + self.margin_right
            height = height + self.vertical_padding + self.margin_top + self.margin_bottom

            w, h = max(width, self.min_width or 0), max(height, self.min_height or 0)
            self._cached_w, self._cached_h = w, h

        return self._cached_w, self._cached_h


class HBox(Box):
    """A horizontally aligned box. identical to ui.Box(horizontal=True)"""
    def __init__(self, contents = None, **kwargs):
        Box.__init__(self, contents, **kwargs)
        self.orient_horizontal = True


class VBox(Box):
    """A vertically aligned box. identical to ui.Box(horizontal=False)"""
    def __init__(self, contents = None, **kwargs):
        Box.__init__(self, contents, **kwargs)
        self.orient_horizontal = False



class _DisplayLabel(graphics.Label):
    cache_attrs = Box.cache_attrs | set(('_cached_w', '_cached_h'))

    def __init__(self, text="", **kwargs):
        graphics.Label.__init__(self, text, **kwargs)
        self._cached_w, self._cached_h = None, None
        self._cached_wh_w, self._cached_wh_h = None, None

    def __setattr__(self, name, val):
        graphics.Label.__setattr__(self, name, val)

        if name in ("text", "markup", "size", "wrap", "ellipsize", "max_width"):
            if name != "max_width":
                self._cached_w, self._cached_h = None, None
            self._cached_wh_w, self._cached_wh_h = None, None


    def get_min_size(self):
        if self._cached_w:
            return self._cached_w, self._cached_h

        text = self.markup or self.text
        escape = len(self.markup) == 0

        if self.wrap is not None or self.ellipsize is not None:
            self._cached_w = self.measure(text, escape, 1)[0]
            self._cached_h = self.measure(text, escape, -1)[1]
        else:
            self._cached_w, self._cached_h = self.measure(text, escape, -1)
        return self._cached_w, self._cached_h

    def get_height_for_width_size(self):
        if self._cached_wh_w:
            return self._cached_wh_w, self._cached_wh_h

        text = self.markup or self.text
        escape = len(self.markup) == 0
        self._cached_wh_w, self._cached_wh_h = self.measure(text, escape, self.max_width)

        return self._cached_wh_w, self._cached_wh_h


class Label(Bin):
    """a widget that displays a limited amount of read-only text"""
    #: pango.FontDescription to use for the label
    font_desc = None

    #: image attachment. one of top, right, bottom, left
    image_position = "left"

    #: font size
    size = None

    fill = False
    padding = 0
    x_align = 0.5

    def __init__(self, text = "", markup = "", spacing = 5, image = None,
                 image_position = None, size = None, font_desc = None,
                 max_width = None, overflow = False, color = "#000",
                 background_color = None, **kwargs):

        # TODO - am initiating table with fill = false but that yields suboptimal label placement and the 0,0 points to whatever parent gave us
        Bin.__init__(self, **kwargs)

        #: image to put next to the label
        self.image = image

        # the actual container that contains the label and/or image
        self.container = Box(spacing = spacing, fill = False,
                             x_align = self.x_align, y_align = self.y_align)

        if image_position is not None:
            self.image_position = image_position

        self.display_label = _DisplayLabel(text = text, markup = markup, color=color, size = size)
        self.display_label.x_align = 0 # the default is 0.5 which makes label align incorrectly on wrapping

        if font_desc or self.font_desc:
            self.display_label.font_desc = font_desc or self.font_desc

        self.display_label.size = size or self.size

        self.background_color = background_color

        #: either the pango `wrap <http://www.pygtk.org/pygtk2reference/pango-constants.html#pango-wrap-mode-constants>`_
        #: or `ellipsize <http://www.pygtk.org/pygtk2reference/pango-constants.html#pango-ellipsize-mode-constants>`_ constant.
        #: if set to False will refuse to become smaller
        self.overflow = overflow

        #: when specified, will deal with label with as specified in overflow
        self.max_width = max_width

        self.add_child(self.container)

        self._position_contents()
        self.connect_after("on-render", self.__on_render)

    def get_mouse_sprites(self):
        return None

    @property
    def text(self):
        """label text. This attribute and :attr:`markup` are mutually exclusive."""
        return self.display_label.text

    @property
    def markup(self):
        """pango markup to use in the label.
        This attribute and :attr:`text` are mutually exclusive."""
        return self.display_label.markup

    @property
    def color(self):
        """label color"""
        return self.display_label.color

    def __setattr__(self, name, val):
        if name in ("text", "markup", "color", "size", "max_width"):
            if self.display_label.__dict__.get(name, "hamster_graphics_no_value_really") == val:
                return
            setattr(self.display_label, name, val)
        elif name in ("spacing"):
            setattr(self.container, name, val)
        else:
            if self.__dict__.get(name, "hamster_graphics_no_value_really") == val:
                return
            Bin.__setattr__(self, name, val)


        if name in ('x_align', 'y_align') and hasattr(self, "container"):
            setattr(self.container, name, val)

        elif name == "alloc_w" and hasattr(self, "display_label") and getattr(self, "overflow") is not False:
            self._update_max_width()

        elif name == "min_width" and hasattr(self, "display_label"):
            self.display_label.width = val - self.horizontal_padding

        elif name == "overflow" and hasattr(self, "display_label"):
            if val is False:
                self.display_label.wrap = None
                self.display_label.ellipsize = None
            elif isinstance(val, pango.WrapMode) and val in (pango.WrapMode.WORD, pango.WrapMode.WORD_CHAR, pango.WrapMode.CHAR):
                self.display_label.wrap = val
                self.display_label.ellipsize = None
            elif isinstance(val, pango.EllipsizeMode) and val in (pango.EllipsizeMode.START, pango.EllipsizeMode.MIDDLE, pango.EllipsizeMode.END):
                self.display_label.wrap = None
                self.display_label.ellipsize = val

            self._update_max_width()
        elif name in ("font_desc", "size"):
            setattr(self.display_label, name, val)

        if name in ("text", "markup", "image", "image_position", "overflow", "size"):
            if hasattr(self, "overflow"):
                self._position_contents()
                self.container.queue_resize()

    def get_min_size(self):
        w, h = self.display_label.width, self.display_label.height
        if self.display_label.max_width:
            return min(w, self.display_label.max_width), h

        return w, h

    def _update_max_width(self):
        # updates labels max width, respecting image and spacing
        if self.overflow is False:
            self.display_label.max_width = -1
        else:
            w = (self.alloc_w or 0) - self.horizontal_padding - self.container.spacing
            if self.image and self.image_position in ("left", "right"):
                w -= self.image.width - self.container.spacing
            self.display_label.max_width = w

        self.container.queue_resize()


    def _position_contents(self):
        if self.image and (self.text or self.markup):
            self.image.expand = False
            self.container.orient_horizontal = self.image_position in ("left", "right")

            if self.image_position in ("top", "left"):
                if self.container.sprites != [self.image, self.display_label]:
                    self.container.clear()
                    self.container.add_child(self.image, self.display_label)
            else:
                if self.container.sprites != [self.display_label, self.image]:
                    self.container.clear()
                    self.container.add_child(self.display_label, self.image)
        elif self.image or (self.text or self.markup):
            sprite = self.image or self.display_label
            if self.container.sprites != [sprite]:
                self.container.clear()
                self.container.add_child(sprite)


    def __on_render(self, sprite):
        w, h = self.width, self.height
        w2, h2 = self.get_height_for_width_size()
        w, h = max(w, w2), max(h, h2)
        self.graphics.rectangle(0, 0, w, h)

        if self.background_color:
            self.graphics.fill(self.background_color)
        else:
            self.graphics.new_path()

########NEW FILE########
__FILENAME__ = pytweener
# pyTweener
#
# Tweening functions for python
#
# Heavily based on caurina Tweener: http://code.google.com/p/tweener/
#
# Released under M.I.T License - see above url
# Python version by Ben Harling 2009
# All kinds of slashing and dashing by Toms Baugis 2010, 2014
import math
import collections
import datetime as dt
import time
import re

class Tweener(object):
    def __init__(self, default_duration = None, tween = None):
        """Tweener
        This class manages all active tweens, and provides a factory for
        creating and spawning tween motions."""
        self.current_tweens = collections.defaultdict(set)
        self.default_easing = tween or Easing.Cubic.ease_in_out
        self.default_duration = default_duration or 1.0

    def has_tweens(self):
        return len(self.current_tweens) > 0


    def add_tween(self, obj, duration = None, easing = None, on_complete = None,
                  on_update = None, round = False, delay = None, **kwargs):
        """
            Add tween for the object to go from current values to set ones.
            Example: add_tween(sprite, x = 500, y = 200, duration = 0.4)
            This will move the sprite to coordinates (500, 200) in 0.4 seconds.
            For parameter "easing" you can use one of the pytweener.Easing
            functions, or specify your own.
            The tweener can handle numbers, dates and color strings in hex ("#ffffff").
            This function performs overwrite style conflict solving - in case
            if a previous tween operates on same attributes, the attributes in
            question are removed from that tween.
        """
        if duration is None:
            duration = self.default_duration

        easing = easing or self.default_easing

        tw = Tween(obj, duration, delay, easing, on_complete, on_update, round, **kwargs )

        if obj in self.current_tweens:
            for current_tween in tuple(self.current_tweens[obj]):
                prev_keys = set((key for (key, tweenable) in current_tween.tweenables))
                dif = prev_keys & set(kwargs.keys())

                for key, tweenable in tuple(current_tween.tweenables):
                    if key in dif:
                        current_tween.tweenables.remove((key, tweenable))

                if not current_tween.tweenables:
                    current_tween.finish()
                    self.current_tweens[obj].remove(current_tween)


        self.current_tweens[obj].add(tw)
        return tw


    def get_tweens(self, obj):
        """Get a list of all tweens acting on the specified object
        Useful for manipulating tweens on the fly"""
        return self.current_tweens.get(obj, None)

    def kill_tweens(self, obj = None):
        """Stop tweening an object, without completing the motion or firing the
        on_complete"""
        if obj is not None:
            try:
                del self.current_tweens[obj]
            except:
                pass
        else:
            self.current_tweens = collections.defaultdict(set)

    def remove_tween(self, tween):
        """"remove given tween without completing the motion or firing the on_complete"""
        if tween.target in self.current_tweens and tween in self.current_tweens[tween.target]:
            self.current_tweens[tween.target].remove(tween)
            if not self.current_tweens[tween.target]:
                del self.current_tweens[tween.target]

    def finish(self):
        """jump the the last frame of all tweens"""
        for obj in self.current_tweens:
            for tween in self.current_tweens[obj]:
                tween.finish()
        self.current_tweens = {}

    def update(self, delta_seconds):
        """update tweeners. delta_seconds is time in seconds since last frame"""

        for obj in tuple(self.current_tweens):
            for tween in tuple(self.current_tweens[obj]):
                done = tween.update(delta_seconds)
                if done:
                    self.current_tweens[obj].remove(tween)
                    if tween.on_complete: tween.on_complete(tween.target)

            if not self.current_tweens[obj]:
                del self.current_tweens[obj]

        return self.current_tweens


class Tween(object):
    __slots__ = ('tweenables', 'target', 'delta', 'duration', 'delay',
                 'ease', 'delta', 'complete', 'round',
                 'on_complete', 'on_update')

    def __init__(self, obj, duration, delay, easing, on_complete, on_update, round,
                 **kwargs):
        """Tween object use Tweener.add_tween( ... ) to create"""

        #: should the tween values truncated to integers or not. Default is False.
        self.round = round

        #: duration of the tween
        self.duration = duration

        #: delay before the animation should be started
        self.delay = delay or 0

        self.target = obj

        #: easing function
        self.ease = easing

        # list of (property, start_value, delta)
        self.tweenables = set()
        for key, value in kwargs.items():
            self.tweenables.add((key, Tweenable(getattr(self.target, key), value)))

        self.delta = 0

        #: callback to execute on complete
        self.on_complete = on_complete

        #: callback to execute on update
        self.on_update = on_update

        self.complete = False

    def finish(self):
        self.update(self.duration)

    def update(self, ptime):
        """Update tween with the time since the last frame"""
        delta = self.delta + ptime
        total_duration = self.delay + self.duration

        if delta > total_duration:
            delta = total_duration

        if delta < self.delay:
            pass
        elif delta == total_duration:
            for key, tweenable in self.tweenables:
                setattr(self.target, key, tweenable.target_value)
        else:
            fraction = self.ease((delta - self.delay) / (total_duration - self.delay))

            for key, tweenable in self.tweenables:
                res = tweenable.update(fraction)
                if isinstance(res, float) and self.round:
                    res = int(res)
                setattr(self.target, key, res)

        if delta == total_duration or len(self.tweenables) == 0:
            self.complete = True

        self.delta = delta

        if self.on_update:
            self.on_update(self.target)

        return self.complete




class Tweenable(object):
    """a single attribute that has to be tweened from start to target"""
    __slots__ = ('start_value', 'change', 'decode_func', 'target_value', 'update')

    hex_color_normal = re.compile("#([a-fA-F0-9]{2})([a-fA-F0-9]{2})([a-fA-F0-9]{2})")
    hex_color_short = re.compile("#([a-fA-F0-9])([a-fA-F0-9])([a-fA-F0-9])")


    def __init__(self, start_value, target_value):
        self.decode_func = lambda x: x
        self.target_value = target_value

        def float_update(fraction):
            return self.start_value + self.change * fraction

        def date_update(fraction):
            return dt.date.fromtimestamp(self.start_value + self.change * fraction)

        def datetime_update(fraction):
            return dt.datetime.fromtimestamp(self.start_value + self.change * fraction)

        def color_update(fraction):
            val = [max(min(self.start_value[i] + self.change[i] * fraction, 255), 0)  for i in range(3)]
            return "#%02x%02x%02x" % (val[0], val[1], val[2])


        if isinstance(start_value, int) or isinstance(start_value, float):
            self.start_value = start_value
            self.change = target_value - start_value
            self.update = float_update
        else:
            if isinstance(start_value, dt.datetime) or isinstance(start_value, dt.date):
                if isinstance(start_value, dt.datetime):
                    self.update = datetime_update
                else:
                    self.update = date_update

                self.decode_func = lambda x: time.mktime(x.timetuple())
                self.start_value = self.decode_func(start_value)
                self.change = self.decode_func(target_value) - self.start_value

            elif isinstance(start_value, basestring) \
             and (self.hex_color_normal.match(start_value) or self.hex_color_short.match(start_value)):
                self.update = color_update
                if self.hex_color_normal.match(start_value):
                    self.decode_func = lambda val: [int(match, 16)
                                                    for match in self.hex_color_normal.match(val).groups()]

                elif self.hex_color_short.match(start_value):
                    self.decode_func = lambda val: [int(match + match, 16)
                                                    for match in self.hex_color_short.match(val).groups()]

                if self.hex_color_normal.match(target_value):
                    target_value = [int(match, 16)
                                    for match in self.hex_color_normal.match(target_value).groups()]
                else:
                    target_value = [int(match + match, 16)
                                    for match in self.hex_color_short.match(target_value).groups()]

                self.start_value = self.decode_func(start_value)
                self.change = [target - start for start, target in zip(self.start_value, target_value)]



"""Robert Penner's classes stripped from the repetetive c,b,d mish-mash
(discovery of Patryk Zawadzki). This way we do the math once and apply to
all the tweenables instead of repeating it for each attribute
"""

def inverse(method):
    def real_inverse(t, *args, **kwargs):
        t = 1 - t
        return 1 - method(t, *args, **kwargs)
    return real_inverse

def symmetric(ease_in, ease_out):
    def real_symmetric(t, *args, **kwargs):
        if t < 0.5:
            return ease_in(t * 2, *args, **kwargs) / 2

        return ease_out((t - 0.5) * 2, *args, **kwargs) / 2 + 0.5
    return real_symmetric

class Symmetric(object):
    def __init__(self, ease_in = None, ease_out = None):
        self.ease_in = ease_in or inverse(ease_out)
        self.ease_out = ease_out or inverse(ease_in)
        self.ease_in_out = symmetric(self.ease_in, self.ease_out)


class Easing(object):
    """Class containing easing classes to use together with the tweener.
       All of the classes have :func:`ease_in`, :func:`ease_out` and
       :func:`ease_in_out` functions."""

    Linear = Symmetric(lambda t: t, lambda t: t)
    Quad = Symmetric(lambda t: t*t)
    Cubic = Symmetric(lambda t: t*t*t)
    Quart = Symmetric(lambda t: t*t*t*t)
    Quint = Symmetric(lambda t: t*t*t*t*t)
    Strong = Quint #oh i wonder why but the ported code is the same as in Quint

    Circ = Symmetric(lambda t: 1 - math.sqrt(1 - t * t))
    Sine = Symmetric(lambda t: 1 - math.cos(t * (math.pi / 2)))


    def _back_in(t, s=1.70158):
        return t * t * ((s + 1) * t - s)
    Back = Symmetric(_back_in)


    def _bounce_out(t):
        if t < 1 / 2.75:
            return 7.5625 * t * t
        elif t < 2 / 2.75:
            t = t - 1.5 / 2.75
            return 7.5625 * t * t + 0.75
        elif t < 2.5 / 2.75:
            t = t - 2.25 / 2.75
            return 7.5625 * t * t + .9375
        else:
            t = t - 2.625 / 2.75
            return 7.5625 * t * t + 0.984375
    Bounce = Symmetric(ease_out = _bounce_out)


    def _elastic_in(t, springiness = 0, wave_length = 0):
        if t in(0, 1):
            return t

        wave_length = wave_length or (1 - t) * 0.3

        if springiness <= 1:
            springiness = t
            s = wave_length / 4
        else:
            s = wave_length / (2 * math.pi) * math.asin(t / springiness)

        t = t - 1
        return -(springiness * math.pow(2, 10 * t) * math.sin((t * t - s) * (2 * math.pi) / wave_length))
    Elastic = Symmetric(_elastic_in)


    def _expo_in(t):
        if t in (0, 1): return t
        return math.pow(2, 10 * t) * 0.001
    Expo = Symmetric(_expo_in)



class _Dummy(object):
    def __init__(self, a, b, c):
        self.a = a
        self.b = b
        self.c = c

if __name__ == "__main__":
    import datetime as dt

    tweener = Tweener()
    objects = []

    object_count, update_times = 1000, 100

    for i in range(object_count):
        objects.append(_Dummy(i-100, i-100, i-100))


    total = dt.datetime.now()

    t = dt.datetime.now()
    print "Adding %d tweens..." % object_count
    for i, o in enumerate(objects):
        tweener.add_tween(o, a = i,
                             b = i,
                             c = i,
                             duration = 0.1 * update_times,
                             easing=Easing.Circ.ease_in_out)
    print dt.datetime.now() - t

    t = dt.datetime.now()
    print "Updating %d times......" % update_times
    for i in range(update_times):  #update 1000 times
        tweener.update(0.1)
    print dt.datetime.now() - t

########NEW FILE########
__FILENAME__ = many_lines
#!/usr/bin/env python
# - coding: utf-8 -
# Copyright (C) 2010 Toms Bauģis <toms.baugis at gmail.com>

"""
  Ported from javascript via chrome experiments.
  Most addictive. There are some params to adjust in the Scene class.
  Color and number of particles reduced due to performance
  Without fadeout this becomes a mess soon, drawing/storing whole window seems
  to be bit expensive though. Although scales lineary. Check earlier code of this
  same file for some snippets, if you want to go that way.

  Super Simple Particle System
  Eric Ishii Eckhardt for Adapted
  http://adaptedstudio.com
"""


from gi.repository import Gtk as gtk
from lib import graphics
from random import random
import collections


class Particle(object):
    def __init__(self, x, y, color):
        self.x, self.y = x, y
        self.color = color
        self.prev_x, self.prev_y = x, y

        # bouncyness - set to 1 to disable
        self.speed_mod_x = random() * 20 + 8
        self.speed_mod_y = random() * 20 + 8

        # random force of atraction towards target (0.1 .. 0.5)
        self.accel_mod_x = random() * 0.5 + 0.1
        self.accel_mod_y = random() * 0.5 + 0.1

        self.speed_x, self.speed_y = 0, 0

    def update(self, mouse_x, mouse_y):
        self.prev_x, self.prev_y = self.x, self.y

        # two random x/y directions make the motion square
        # should be angle diff and spead instead
        target_accel_x = (mouse_x - self.x) * self.accel_mod_x
        target_accel_y = (mouse_y - self.y) * self.accel_mod_y


        self.speed_x = self.speed_x + (target_accel_x - self.speed_x) / self.speed_mod_x
        self.speed_y = self.speed_y + (target_accel_y - self.speed_y) / self.speed_mod_y



        self.x = self.x + self.speed_x * 0.5 #TODO should fix the speed math instead
        self.y = self.y + self.speed_y * 0.5

class Scene(graphics.Scene):
    def __init__(self):
        graphics.Scene.__init__(self)
        self.set_double_buffered(False) # cheap way how to get to continuous draw!

        self.connect("on-enter-frame", self.on_enter_frame)
        self.particles = []
        self.paths = collections.deque()

        self.particle_count = 50 # these are the flies


    def on_enter_frame(self, scene, context):
        g = graphics.Graphics(context)
        g.fill_area(0, 0, self.width, self.height, "#fff", 0.08)

        if not self.particles:
            for i in range(self.particle_count):
                color = (random() * 0.8, random() * 0.8, random() * 0.8)
                self.particles.append(Particle(random() * self.width, random() * self.height, color))

        g.set_line_style(width=0.3)

        for particle in self.particles:
            particle.update(self.mouse_x, self.mouse_y)
            g.move_to(particle.prev_x, particle.prev_y)
            g.line_to(particle.x, particle.y)
            g.stroke(particle.color)

        self.redraw()




class BasicWindow:
    def __init__(self):
        window = gtk.Window()
        window.set_size_request(1000, 650)
        window.connect("delete_event", lambda *args: gtk.main_quit())
        window.add(Scene())
        window.show_all()

example = BasicWindow()
import signal
signal.signal(signal.SIGINT, signal.SIG_DFL) # gtk3 screws up ctrl+c
gtk.main()

########NEW FILE########
__FILENAME__ = many_lines2
#!/usr/bin/env python
# - coding: utf-8 -
# Copyright (C) 2010 Toms Bauģis <toms.baugis at gmail.com>

"""
  Ported from javascript via chrome experiments.
  Most addictive. There are some params to adjust in the Scene class.
  Color and number of particles reduced due to performance
  Without fadeout this becomes a mess soon, drawing/storing whole window seems
  to be bit expensive though. Although scales lineary. Check earlier code of this
  same file for some snippets, if you want to go that way.

  Super Simple Particle System
  Eric Ishii Eckhardt for Adapted
  http://adaptedstudio.com
"""


from gi.repository import Gtk as gtk
from lib import graphics
from contrib.euclid import Vector2
from random import random, randint
import collections

class Boid(object):
    def __init__(self):
        self.acceleration = Vector2()
        self.velocity = Vector2()
        self.location = Vector2(150, 150)

class Boid3(Boid):
    """Sir Boid from random_movement.py"""
    def __init__(self):
        Boid.__init__(self)
        self.target = None
        self.prev_distance = None

    def update_position(self, w, h):
        distance = 0
        if self.target:
            distance = (self.target - self.location).magnitude_squared()

        if not self.target or self.prev_distance and distance > self.prev_distance:
            self.prev_distance = w * w + h * h
            self.target = Vector2(randint(0, w), randint(0, h))

        target = (self.target - self.location)

        self.acceleration = (target - self.velocity).normalize() * 2
        self.velocity += self.acceleration

        self.velocity.limit(20)

        self.prev_distance = distance

        self.location += self.velocity

class Particle(object):
    def __init__(self, x, y):
        self.x, self.y = x, y


        self.prev_x, self.prev_y = x, y

        # bouncyness - set to 1 to disable
        self.speed_mod_x = random() * 20 + 8
        self.speed_mod_y = random() * 20 + 8

        # random force of atraction towards target (0.1 .. 0.5)
        self.accel_mod_x = random() * 0.5 + 0.2
        self.accel_mod_y = random() * 0.5 + 0.2

        self.speed_x, self.speed_y = 0, 0

    def update(self, mouse_x, mouse_y):
        self.prev_x, self.prev_y = self.x, self.y

        target_accel_x = (mouse_x - self.x) * self.accel_mod_x
        target_accel_y = (mouse_y - self.y) * self.accel_mod_y


        self.speed_x = self.speed_x + (target_accel_x - self.speed_x) / self.speed_mod_x
        self.speed_y = self.speed_y + (target_accel_y - self.speed_y) / self.speed_mod_y



        self.x = self.x + self.speed_x * 0.1
        self.y = self.y + self.speed_y * 0.1

class Scene(graphics.Scene):
    def __init__(self):
        graphics.Scene.__init__(self)

        self.connect("on-enter-frame", self.on_enter_frame)
        #self.set_double_buffered(False) # cheap way how to get to continuous draw!

        self.particles = []

        self.particle_count = 40 # these are the flies
        self.fade_step = 2         # the smaller is this the "ghostier" it looks (and slower too)

        self.target = Boid3()



    def on_enter_frame(self, scene, context):
        g = graphics.Graphics(context)
        g.fill_area(0, 0, self.width, self.height, "#fff", 0.08)

        if not self.particles:
            for i in range(self.particle_count):
                self.particles.append(Particle(random() * self.width, random() * self.height))

        self.target.update_position(self.width, self.height)

        g.set_line_style(width=0.3)

        for particle in self.particles:
            particle.update(self.target.location.x, self.target.location.y)
            g.move_to(particle.prev_x, particle.prev_y)
            g.line_to(particle.x, particle.y)

        g.set_color("#000")
        g.stroke()

        self.redraw()




class BasicWindow:
    def __init__(self):
        window = gtk.Window()
        window.set_size_request(1000, 650)
        window.connect("delete_event", lambda *args: gtk.main_quit())
        window.add(Scene())
        window.show_all()

example = BasicWindow()
import signal
signal.signal(signal.SIGINT, signal.SIG_DFL) # gtk3 screws up ctrl+c
gtk.main()

########NEW FILE########
__FILENAME__ = moire_circular
#!/usr/bin/env python
# - coding: utf-8 -
# Copyright (C) 2014 Toms Bauģis <toms.baugis at gmail.com>

"""Circular moire, epilepse your heart out!
   Move mouse left and right to adjust the circle disposition
   and up and down to increase and decrease the number of circles and line
   thickness
"""
import math

from gi.repository import Gtk as gtk
from lib import graphics

class Circles(graphics.Sprite):
    def __init__(self, color, **kwargs):
        graphics.Sprite.__init__(self, **kwargs)
        self.color = color
        self.connect("on-render", self.on_render)
        self.cache_as_bitmap = True
        self.distance = 5

    def on_render(self, sprite):
        self.graphics.set_line_style(width=1)

        circles = 500 / self.distance
        line_width = max(self.distance / 2, 1)

        for i in range(circles):
            radius = i * self.distance + 1
            self.graphics.move_to(radius, 0)
            self.graphics.circle(0, 0, radius)
        self.graphics.set_line_style(width = line_width)
        self.graphics.stroke(self.color)


class Scene(graphics.Scene):
    def __init__(self):
        graphics.Scene.__init__(self)

        self.base = Circles("#f00", x=400, y=300)
        self.sattelite = Circles("#00f", x=500, y=300)
        self.add_child(self.base, self.sattelite)

        self.distance = 20

        self.connect("on-enter-frame", self.on_enter_frame)
        self.connect("on-mouse-move", self.on_mouse_move)

    def on_mouse_move(self, sprite, event):
        middle = self.width / 2.0
        distance = (event.x - middle) * 1.0 / middle
        self.distance = int(distance * 250)

        middle = self.height / 2.0
        circle_distance = abs((event.y - middle) * 1.0 / middle)
        circle_distance = circle_distance * 20 + 5
        for circle in (self.base, self.sattelite):
            circle.distance = int(circle_distance)


        self.redraw()

    def on_enter_frame(self, scene, context):
        self.base.x, self.base.y = self.width / 2, self.height / 2

        distance = self.distance
        self.sattelite.x, self.sattelite.y = self.base.x + distance, self.base.y



class BasicWindow:
    def __init__(self):
        window = gtk.Window()
        window.set_default_size(800, 500)
        window.connect("delete_event", lambda *args: gtk.main_quit())
        window.add(Scene())
        window.show_all()

if __name__ == '__main__':
    window = BasicWindow()
    import signal
    signal.signal(signal.SIGINT, signal.SIG_DFL) # gtk3 screws up ctrl+c
    gtk.main()

########NEW FILE########
__FILENAME__ = mouse_fade_out
#!/usr/bin/env python
# - coding: utf-8 -
# Copyright (C) 2010 Toms Bauģis <toms.baugis at gmail.com>
"""
    this was an attempt to achieve motion blur
    hoping that fading out will do the job.
    this is not quite motion blur - to see what i mean, try moving the mouse
    around for a longer while - instead of motion blur what you get is motion
    tail, which is unwanted.
    still this example teaches something too.
"""

from gi.repository import Gtk as gtk
from lib import graphics

class Scene(graphics.Scene):
    def __init__(self):
        graphics.Scene.__init__(self)
        self.mouse_cursor = False

        self.coords = []
        self.x, self.y = 0, 0
        self.radius = 30
        self.connect("on-mouse-move", self.on_mouse_move)
        self.connect("on-enter-frame", self.on_enter_frame)
        self.fade_tick = 0


    def on_mouse_move(self, area, event):
        # oh i know this should not be performed using tweeners, but hey - a demo!
        self.coords.insert(0, (event.x, event.y))
        self.coords = self.coords[:10]  # limit trail length

    def on_enter_frame(self, scene, context):
        g = graphics.Graphics(context)

        for i, coords in enumerate(reversed(self.coords)):
            x, y = coords

            if i == len(self.coords) - 1:
                alpha = 1
            else:
                alpha = float(i+1) / len(self.coords) / 2

            g.rectangle(x - self.radius,
                            y - self.radius,
                            self.radius * 2,
                            self.radius * 2, 3)
            #print alpha
            g.fill("#999", alpha)

        self.fade_tick += 1
        if len(self.coords) > 1 and self.fade_tick > 2:
            self.fade_tick = 0
            self.coords.pop(-1)

        self.redraw() # constant redraw (maintaining the requested frame rate)


class BasicWindow:
    def __init__(self):
        window = gtk.Window()
        window.set_default_size(300, 300)
        window.connect("delete_event", lambda *args: gtk.main_quit())

        window.add(Scene())
        window.show_all()


if __name__ == "__main__":
    example = BasicWindow()
    import signal
    signal.signal(signal.SIGINT, signal.SIG_DFL) # gtk3 screws up ctrl+c
    gtk.main()

########NEW FILE########
__FILENAME__ = pacing
#!/usr/bin/env python
# - coding: utf-8 -
# Copyright (C) 2014 You <your.email@someplace>

"""Base template"""
import math

from gi.repository import Gtk as gtk
from lib import graphics
from lib.pytweener import Easing

class Rect(graphics.Sprite):
    def __init__(self, **kwargs):
        graphics.Sprite.__init__(self, **kwargs)
        self.connect("on-render", self.on_render)

    def on_render(self, sprite):
        self.graphics.rectangle(0, 0, 100, 100)
        self.graphics.fill_stroke("#444", "#444")

class Scene(graphics.Scene):
    def __init__(self):
        graphics.Scene.__init__(self)

        pair = graphics.Sprite(x=200, y=200)
        pair.add_child(Rect(),
                       Rect(rotation=math.radians(-90)))
        self.add_child(pair)
        self.kick(pair.sprites[0], 180)


        triplet = graphics.Sprite(x=500, y=200)
        triplet.add_child(Rect(),
                          Rect(rotation=math.radians(-90)),
                          Rect(rotation=math.radians(-180)),
                         )
        self.add_child(triplet)
        self.kick(triplet.sprites[0], 90)


    def kick(self, sprite, angle):
        def kick_next(sprite):
            #sprite.parent.rotation += math.radians(20)
            sprites = sprite.parent.sprites
            next_sprite = sprites[(sprites.index(sprite) + 1) % len(sprites)]
            self.kick(next_sprite, angle)

        def punch_parent(sprite):
            return
            sprite.parent.rotation += math.radians(.2)

        sprite.animate(rotation = sprite.rotation + math.radians(angle),
                       duration=1,
                       #easing=Easing.Expo.ease_in,
                       on_update=punch_parent,
                       on_complete=kick_next)



class BasicWindow:
    def __init__(self):
        window = gtk.Window()
        window.set_default_size(700, 400)
        window.connect("delete_event", lambda *args: gtk.main_quit())
        window.add(Scene())
        window.show_all()

if __name__ == '__main__':
    window = BasicWindow()
    import signal
    signal.signal(signal.SIGINT, signal.SIG_DFL) # gtk3 screws up ctrl+c
    gtk.main()

########NEW FILE########
__FILENAME__ = perfect_ellipse
#!/usr/bin/env python
# - coding: utf-8 -
# Copyright (C) 2010 Toms Bauģis <toms.baugis at gmail.com>

"""
    Inspired by Karl Lattimer's perfect ellipse (http://www.qdh.org.uk/wordpress/?p=286)
"""


from gi.repository import Gtk as gtk
from lib import graphics
import math

class Ellipse(graphics.Sprite):
    def __init__(self, x, y, width, height):
        graphics.Sprite.__init__(self, x = x, y = y, snap_to_pixel = False)
        self.width, self.height = width, height
        self.connect("on-render", self.on_render)

    def on_render(self, sprite):
        self.graphics.clear()
        """you can also use graphics.ellipse() here"""
        steps = max((32, self.width, self.height)) / 3

        angle = 0
        step = math.pi * 2 / steps
        points = []
        while angle < math.pi * 2:
            points.append((self.width / 2.0 * math.cos(angle),
                           self.height / 2.0 * math.sin(angle)))
            angle += step

        # move to the top-left corner
        min_x = min((point[0] for point in points))
        min_y = min((point[1] for point in points))

        self.graphics.move_to(points[0][0] - min_x, points[0][1] - min_y)
        for x, y in points:
            self.graphics.line_to(x - min_x, y - min_y)
        self.graphics.line_to(points[0][0] - min_x, points[0][1] - min_y)

        self.graphics.stroke("#666")


class Scene(graphics.Scene):
    def __init__(self):
        graphics.Scene.__init__(self)

        self.add_child(graphics.Label("Move mouse to change the size of the ellipse",
                                      12, "#666", x = 5, y = 5))

        self.ellipse = Ellipse(50, 50, 100, 200)
        self.ellipse.pivot_x, self.ellipse.pivot_y = 50, 100 #center
        self.add_child(self.ellipse)


        self.connect("on-enter-frame", self.on_enter_frame)
        self.connect("on-mouse-move", self.on_mouse_move)

    def on_mouse_move(self, scene, event):
        """adjust ellipse dimensions on mouse move"""
        self.ellipse.width = event.x
        self.ellipse.height = event.y
        self.ellipse.pivot_x, self.ellipse.pivot_y = self.ellipse.width / 2, self.ellipse.height / 2


    def on_enter_frame(self, scene, context):
        """on redraw center and rotate"""
        self.ellipse.x, self.ellipse.y = self.width / 2 - self.ellipse.pivot_x, self.height / 2 - self.ellipse.pivot_y
        self.ellipse.rotation += 0.01

        self.redraw()

class BasicWindow:
    def __init__(self):
        window = gtk.Window()
        window.set_size_request(600, 500)
        window.connect("delete_event", lambda *args: gtk.main_quit())
        window.add(Scene())
        window.show_all()

example = BasicWindow()
import signal
signal.signal(signal.SIGINT, signal.SIG_DFL) # gtk3 screws up ctrl+c
gtk.main()

########NEW FILE########
__FILENAME__ = pie_menu
#!/usr/bin/env python
# - coding: utf-8 -
# Copyright (C) 2010 Toms Bauģis <toms.baugis at gmail.com>
"""
    Bit of pie in progress.
"""

from gi.repository import Gtk as gtk
from lib import graphics
from contrib.euclid import Vector2
import math

class Sector(graphics.Sprite):
    def __init__(self, inner_radius, outer_radius, start_angle = 0, end_angle = 0):
        graphics.Sprite.__init__(self, interactive = True)
        self.inner_radius = inner_radius
        self.outer_radius = outer_radius
        self.start_angle = start_angle
        self.end_angle = end_angle

        self.fill = None
        self.stroke = "#aaa"

        self.connect("on-render", self.on_render)

    def on_render(self, sprite):
        angle = self.start_angle - self.end_angle

        self.graphics.arc(0, 0, self.inner_radius, angle, 0)
        if abs(angle) >= math.pi * 2:
            self.graphics.move_to(self.outer_radius, 0)
        else:
            self.graphics.line_to(self.outer_radius, 0)
        self.graphics.arc_negative(0, 0, self.outer_radius, 0, angle)
        if self.fill:
            self.graphics.close_path()

        # just for fun
        self.graphics.move_to(150, -15)
        self.graphics.rectangle(150,-15,10,10)

        self.graphics.fill_stroke(self.fill, self.stroke)


class Menu(graphics.Sprite):
    def __init__(self, x, y):
        graphics.Sprite.__init__(self, x, y, interactive=True, draggable=True)

        self.graphics.arc(0, 0, 10, 0, math.pi * 2)
        self.graphics.fill("#aaa")

        self.menu = []
        for i in range(20):
            self.add_item()

    def on_mouse_over(self, sprite):
        sprite.fill = "#ddd"

    def on_mouse_out(self, sprite):
        sprite.fill = ""

    def on_click(self, sprite, event):
        self.add_item()

    def add_item(self):
        item = Sector(25, 50, math.pi / 2, 0)
        item.connect("on-mouse-over", self.on_mouse_over)
        item.connect("on-mouse-out", self.on_mouse_out)
        item.connect("on-click", self.on_click)


        self.menu.append(item)
        self.add_child(item)


        current_angle = 0
        angle = math.pi * 2 / len(self.menu)
        for i, item in enumerate(self.menu):
            item.start_angle = current_angle
            item.rotation = item.start_angle

            item.end_angle = current_angle + angle #- angle * 0.1
            item.inner_radius = 25 + len(self.menu) / 2.0 #+ i * 2
            item.outer_radius = 50 + len(self.menu) * 2 #+ i * 2

            current_angle += angle


class Scene(graphics.Scene):
    def __init__(self):
        graphics.Scene.__init__(self)
        self.max_width = 50
        self.menu = Menu(200, 200)
        self.add_child(self.menu)
        self.connect("on-enter-frame", self.on_enter_frame)
        self.framerate = 30

    def on_enter_frame(self, scene, context):
        # turn the menu a bit and queue redraw
        self.menu.rotation += 0.004
        self.redraw()


class BasicWindow:
    def __init__(self):
        window = gtk.Window()
        window.set_size_request(400, 400)
        window.connect("delete_event", lambda *args: gtk.main_quit())
        self.scene = Scene()
        window.add(self.scene)
        window.show_all()


if __name__ == "__main__":
    example = BasicWindow()
    import signal
    signal.signal(signal.SIGINT, signal.SIG_DFL) # gtk3 screws up ctrl+c
    gtk.main()

########NEW FILE########
__FILENAME__ = pulse
#!/usr/bin/env python
# - coding: utf-8 -
# Copyright (C) 2010 Toms Bauģis <toms.baugis at gmail.com>

"""
    Demo of a a timer based ripple running through nodes and initiating
    sub-animations. Not sure where this could come handy.
"""


from gi.repository import Gtk as gtk
from lib import graphics
from lib.pytweener import Easing
from random import random
import math

class Node(graphics.Sprite):
    def __init__(self, angle, distance):
        graphics.Sprite.__init__(self)

        self.angle = angle
        self.distance = distance
        self.base_angle = 0
        self.distance_scale = 1
        self.radius = 4.0
        self.phase = 0
        self.connect("on-render", self.on_render)

    def on_render(self, sprite):
        self.graphics.clear()
        self.x = math.cos(self.angle + self.base_angle) * self.distance * self.distance_scale
        self.y = math.sin(self.angle + self.base_angle) * self.distance * self.distance_scale

        self.graphics.circle(0, 0, self.radius)
        self.graphics.fill("#aaa")


class Scene(graphics.Scene):
    def __init__(self):
        graphics.Scene.__init__(self)

        self.nodes = []
        self.tick = 0
        self.phase = 0
        self.container = graphics.Sprite()
        self.add_child(self.container)
        self.framerate = 30

        self.connect("on-enter-frame", self.on_enter_frame)
        self.connect("on-mouse-move", self.on_mouse_move)

    def on_mouse_move(self, scene, event):
        if gdk.ModifierType.BUTTON1_MASK & event.state:
            # rotate and scale on mouse
            base_angle = math.pi * 2 * ((self.width / 2 - event.x) / self.width) / 3
            distance_scale = math.sqrt((self.width / 2 - event.x) ** 2 + (self.height / 2 - event.y) ** 2) \
                             / math.sqrt((self.width / 2) ** 2 + (self.height / 2) ** 2)

            for node in self.nodes:
                node.base_angle = base_angle
                node.distance_scale = distance_scale

    def on_enter_frame(self, scene, context):
        self.container.x = self.width / 2
        self.container.y = self.height / 2

        if len(self.nodes) < 100:
            for i in range(100 - len(self.nodes)):
                angle = random() * math.pi * 2
                distance = random() * 500

                node = Node(angle, distance)
                node.phase = self.phase
                self.container.add_child(node)
                self.nodes.append(node)

        if not self.tick:
            self.phase +=1
            self.animate(self,
                         tick = 550,
                         duration = 3,
                         on_complete = self.reset_tick,
                         easing = Easing.Expo.ease_in_out)

        for node in self.nodes:
            if node.phase < self.phase and node.distance < self.tick:
                node.phase = self.phase
                self.tweener.kill_tweens(node)
                self.animate(node,
                             duration = 0.5,
                             radius = 20,
                             easing = Easing.Expo.ease_in,
                             on_complete = self.slide_back)


    def reset_tick(self, target):
        self.tick = 0

    def slide_back(self, node):
        self.animate(node,
                     radius = 4,
                     duration = 0.5,
                     easing = Easing.Expo.ease_out)

class BasicWindow:
    def __init__(self):
        window = gtk.Window()
        window.set_size_request(600, 500)
        window.connect("delete_event", lambda *args: gtk.main_quit())
        window.add(Scene())
        window.show_all()

example = BasicWindow()
import signal
signal.signal(signal.SIGINT, signal.SIG_DFL) # gtk3 screws up ctrl+c
gtk.main()

########NEW FILE########
__FILENAME__ = random_movement
#!/usr/bin/env python
# - coding: utf-8 -
# Copyright (C) 2010 Toms Bauģis <toms.baugis at gmail.com>

"""
    Looking into random movement. Specifically looking for something elegant.
    These are just beginnings.
"""


from gi.repository import Gtk as gtk
from lib import graphics
from contrib.euclid import Vector2
import math
from random import random, randint

class Boid(graphics.Sprite):
    def __init__(self):
        graphics.Sprite.__init__(self)
        self.stroke = "#666"
        self.visible = True
        self.radius = 4
        self.acceleration = Vector2()
        self.velocity = Vector2()

        self.location = Vector2(150, 150)
        self.positions = []
        self.message = None # a message that waypoint has set perhaps
        self.flight_angle = 0

        self.connect("on-render", self.on_render)

    def update_position(self, w, h):
        raise TableSpoon # forgot the name of the real exception, so can as well raise a table spoon

    def on_render(self, sprite):
        self.graphics.clear()
        #draw boid triangle
        if self.flight_angle:
            theta = self.flight_angle
        else:
            theta = self.velocity.heading() + math.pi / 2

        self.rotation = theta
        self.x, self.y = self.location.x, self.location.y
        self.graphics.set_line_style(width = 1)

        self.graphics.move_to(0, -self.radius*2)
        self.graphics.line_to(-self.radius, self.radius * 2)
        self.graphics.line_to(self.radius, self.radius * 2)
        self.graphics.line_to(0, -self.radius*2)

        self.graphics.stroke(self.stroke)


class Boid1(Boid):
    """purely random acceleration plus gravitational pull towards the center"""
    def __init__(self):
        Boid.__init__(self)

    def update_position(self, w, h):
        self.acceleration = Vector2(random() * 2 - 1, random() * 2 - 1)

        self.acceleration += (Vector2(w/2, h/2) - self.location) / 4000

        self.velocity += self.acceleration
        self.velocity.limit(2)
        self.location += self.velocity


class Boid2(Boid):
    """acceleration is in slight angular deviation of velocity
       maintaining in screen with the gravitational pull
    """
    def __init__(self):
        Boid.__init__(self)
        self.stroke = "#0f0"

    def update_position(self, w, h):
        acc_angle = self.velocity.heading() + (random() * 2 - 1)

        max_distance = w/2 * w/2 + h/2 * h/2
        current_centre_distance = (Vector2(w/2, h/2) - self.location).magnitude_squared()

        self.acceleration = Vector2(math.cos(acc_angle), math.sin(acc_angle)) * 0.8
        self.acceleration += (Vector2(w/2, h/2) - self.location) / 500 * (1 - (current_centre_distance / float(max_distance)))

        self.velocity += self.acceleration
        self.velocity.limit(5)
        self.location += self.velocity

        self.location.x = max(min(self.location.x, w + 100), -100)
        self.location.y = max(min(self.location.y, h + 100), -100)


class Boid3(Boid):
    """waypoint oriented - once reached, picks another random waypoint
       alternatively another random waypoint is picked, if the boid keeps
       moving away from the current one - this way we can keep the speed constant
       and discard waypoint instead
    """
    def __init__(self):
        Boid.__init__(self)
        self.stroke = "#00f"
        self.target = None
        self.prev_distance = None

    def update_position(self, w, h):
        distance = 0
        if self.target:
            distance = (self.target - self.location).magnitude_squared()

        if not self.target or self.prev_distance and distance > self.prev_distance:
            self.prev_distance = w * w + h * h
            self.target = Vector2(randint(0, w), randint(0, h))

        target = (self.target - self.location)

        self.acceleration = (target - self.velocity).normalize() * 0.25
        self.velocity += self.acceleration

        self.velocity.limit(6)

        self.prev_distance = distance

        self.location += self.velocity


class Scene(graphics.Scene):
    def __init__(self):
        graphics.Scene.__init__(self)

        self.boids = [Boid1(), Boid2(), Boid3(), Boid3(), Boid3()]
        self.add_child(*self.boids)
        self.connect("on-enter-frame", self.on_enter_frame)

    def on_enter_frame(self, scene, context):
        for boid in self.boids:
            boid.update_position(self.width, self.height)

        self.redraw()


class BasicWindow:
    def __init__(self):
        window = gtk.Window()
        window.set_size_request(600, 500)
        window.connect("delete_event", lambda *args: gtk.main_quit())
        window.add(Scene())
        window.show_all()

example = BasicWindow()
import signal
signal.signal(signal.SIGINT, signal.SIG_DFL) # gtk3 screws up ctrl+c
gtk.main()

########NEW FILE########
__FILENAME__ = reach2
#!/usr/bin/env python
# - coding: utf-8 -
# Copyright (C) 2010 Toms Bauģis <toms.baugis at gmail.com>

"""
 * Reach 2.
 * Based on code from Keith Peters (www.bit-101.com).
 *
 * The arm follows the position of the mouse by
 * calculating the angles with atan2().
 *
 Ported from processing (http://processing.org/) examples.
"""

import math
from gi.repository import Gtk as gtk
from lib import graphics

SEGMENT_LENGTH = 25

class Segment(graphics.Sprite):
    def __init__(self, x, y, width):
        graphics.Sprite.__init__(self, x, y, snap_to_pixel = False)

        self.graphics.move_to(0, 0)
        self.graphics.line_to(SEGMENT_LENGTH, 0)

        self.graphics.set_color("#999")
        self.graphics.set_line_style(width = width)
        self.graphics.stroke()


class Scene(graphics.Scene):
    def __init__(self):
        graphics.Scene.__init__(self)


        self.segments = []

        parts = 20
        for i in range(parts):
            segment = Segment(0, 0, i)
            self.segments.append(segment)
            self.add_child(segment)

        self.connect("on-mouse-move", self.on_mouse_move)
        self.connect("on-enter-frame", self.on_enter_frame)


    def on_mouse_move(self, scene, event):
        x, y = event.x, event.y

        def get_angle(segment, x, y):
            dx = x - segment.x
            dy = y - segment.y
            return math.atan2(dy, dx)

        # point each segment to it's predecessor
        for segment in self.segments:
            angle = get_angle(segment, x, y)
            segment.angle = angle
            segment.rotation = angle

            x = x - math.cos(angle) * SEGMENT_LENGTH
            y = y - math.sin(angle) * SEGMENT_LENGTH

        # and now move the pointed nodes, starting from the last one
        # (that is the beginning of the arm)
        for prev, segment in reversed(list(zip(self.segments, self.segments[1:]))):
            prev.x = segment.x + math.cos(segment.angle) * SEGMENT_LENGTH
            prev.y = segment.y + math.sin(segment.angle) * SEGMENT_LENGTH


        self.redraw()

    def on_enter_frame(self, scene, context):
        self.segments[-1].y = self.height



class BasicWindow:
    def __init__(self):
        window = gtk.Window()
        window.set_size_request(600, 400)
        window.connect("delete_event", lambda *args: gtk.main_quit())
        window.add(Scene())
        window.show_all()


if __name__ == "__main__":
    example = BasicWindow()
    import signal
    signal.signal(signal.SIGINT, signal.SIG_DFL) # gtk3 screws up ctrl+c
    gtk.main()

########NEW FILE########
__FILENAME__ = roll
#!/usr/bin/env python
# - coding: utf-8 -
# Copyright (C) 2014 Toms Baugis <toms.baugis@gmail.com>

"""Base template"""
import math

from gi.repository import Gtk as gtk
from lib import graphics


class Roller(graphics.Sprite):
    def __init__(self, poly=[], **kwargs):
        graphics.Sprite.__init__(self, **kwargs)

        # the inner radius of the square
        self.inner_radius = 20

        self.poly = poly or [(10, 250), (500, 150)]

        self.vector = self.poly[:2]

        self.snap_to_pixel = False


        # roll directoin - clockwise or counter-clockwise
        self.direction = 1
        self.outside = False # if outside is set to true, will flip to the other side of the vector

        self._abs_distance_to_b = 0

        self.roller = graphics.Sprite()
        self.add_child(self.roller)
        self.roller.connect("on-render", self.on_render_roller)

        self.connect("on-render", self.on_render)

    def on_render(self, sprite):
        if not self.debug:
            return

        self.graphics.move_to(0, 0)
        self.graphics.line_to(self.roller.x, self.roller.y)
        self.graphics.stroke("#eee")

        self.graphics.move_to(-self.outer_radius, 0)
        self.graphics.line_to(self.outer_radius, 0)
        self.graphics.stroke("#f00")

    def on_render_roller(self, roller):
        # square has 4 sides, so our waves have to be shorter
        roller.graphics.rectangle(-self.inner_radius, -self.inner_radius,
                                self.inner_radius * 2, self.inner_radius * 2)
        roller.graphics.stroke("#eee")


    def roll(self, base_angle=0):
        # adjust the outer radius here
        self.outer_radius = math.sqrt(2 * ((self.inner_radius) ** 2))
        step = 3


        rotation_step = self.direction * math.radians(step) * (-1 if self.outside else 1)

        # no point going over 360 degrees
        self.roller.rotation = (self.roller.rotation + rotation_step) % (math.pi * 2)

        # y has to variate between inner and outer radius based on the phase
        diff = self.outer_radius - self.inner_radius
        distance = self.inner_radius + abs(diff * math.sin((self.roller.rotation) * 2))
        self.roller.y = -distance * (-1 if self.outside else 1)


        # determine base tilt on the vector we are sitting
        a, b = self.vector
        dx, dy = b[0] - a[0], b[1] - a[1]
        base_tilt = math.atan2(dy, dx)
        self.rotation = base_tilt

        x_step = (math.pi * self.outer_radius) * step / 180.0
        self.x += self.direction * x_step * math.cos(base_tilt)

        # adjust our position
        y_step = (math.pi * self.outer_radius) * step / 180.0
        self.y += self.direction * y_step * math.sin(base_tilt)


        # are we there yet?
        remaining = abs(b[0] - self.x - abs(distance) * math.cos(base_tilt))
        remaining += abs(b[1] - self.y - abs(distance) * math.sin(base_tilt))
        if self._abs_distance_to_b and self._abs_distance_to_b < remaining:
            self._abs_distance_to_b = 0
            next_dot = self.poly.index(self.vector[1])

            self.vector = self.poly[next_dot:next_dot+2]

            # the whole approach has issues - it might be cheaper to actually
            # immitate physics than to do all these calcs. alas, not impossible

            # there are two cardinal - cases - whether we go inside of the next
            # turn or on the outside

            # if it is inside, we have to stop our traverse as soon as we are
            # crossing the next line

            # if it's outside, we do our animation till the very last point and
            # then we do a rather magical switch
            self.x, self.y = self.vector[0]
        else:
            self._abs_distance_to_b = remaining



class Scene(graphics.Scene):
    def __init__(self):
        graphics.Scene.__init__(self)
        self.background_color = "#333"

        self.poly = [
            (100, 100), (250, 50), (500, 100), (500, 500), (100, 500), (100, 100)
        ]


        self.roller = Roller(self.poly)
        self.roller2 = Roller(list(reversed(self.poly)))
        #self.roller2.outside=True

        self.add_child(self.roller, self.roller2)

        # distance from the surface
        self.roller.x, self.roller.y = self.roller.vector[0]
        self.roller2.x, self.roller2.y = self.roller.vector[0]

        self.connect("on-enter-frame", self.on_enter_frame)

    def on_enter_frame(self, scene, context):
        self.roller.roll()
        self.roller2.roll()

        g = graphics.Graphics(context)
        g.move_to(*self.poly[0])

        for dot in self.poly[1:]:
            g.line_to(*dot)

        g.stroke("#f0f")

        self.redraw() # this is how to get a constant redraw loop (say, for animation)



class BasicWindow:
    def __init__(self):
        window = gtk.Window()
        window.set_default_size(600, 600)
        window.connect("delete_event", lambda *args: gtk.main_quit())
        window.add(Scene())
        window.show_all()


if __name__ == '__main__':
    window = BasicWindow()
    import signal
    signal.signal(signal.SIGINT, signal.SIG_DFL) # gtk3 screws up ctrl+c
    gtk.main()

########NEW FILE########
__FILENAME__ = roll2
#!/usr/bin/env python
# - coding: utf-8 -
# Copyright (C) 2014 Toms Baugis <toms.baugis@gmail.com>

"""Base template"""
import math

from gi.repository import Gtk as gtk
from lib import graphics


class Roller(graphics.Sprite):
    def __init__(self, **kwargs):
        graphics.Sprite.__init__(self, **kwargs)
        self.inner_radius = 60

        self.y = -self.inner_radius
        self.direction = 1

        self.vector = []

        self.connect("on-render", self.on_render)

    def on_render(self, sprite):
        # square has 4 sides, so our waves have to be shorter
        self.graphics.rectangle(-self.inner_radius, -self.inner_radius,
                                self.inner_radius * 2, self.inner_radius * 2)
        self.graphics.stroke("#eee")

        """
        # here's bit of behind the scenes - faking stuff like a boss
        self.graphics.move_to(self.inner_radius, 0)
        self.graphics.circle(0, 0, self.inner_radius)

        self.graphics.move_to(self.outer_radius, 0)
        self.graphics.circle(0, 0, self.outer_radius)

        self.graphics.move_to(0, 0)
        self.graphics.line_to(math.cos(self.rotation) * self.inner_radius,
                              math.sin(self.rotation) * self.inner_radius)

        self.graphics.stroke("#777")
        """



    def roll(self):
        # adjust the outer radius here
        self.outer_radius = math.sqrt(2 * ((self.inner_radius) ** 2))
        step = 3

        """
        # based on the phase we can also do a little extra pushing
        step_push = math.cos((self.rotation + math.radians(0)) * 4)
        step += step_push * 1.5
        """
        self.rotation += self.direction * math.radians(step)

        # y has to variate between inner and outer radius based on the phase
        diff = self.outer_radius - self.inner_radius
        self.y = -self.inner_radius - abs(diff * math.sin(self.rotation * 2))



class MovingRoller(Roller):
    def __init__(self, size=100, **kwargs):
        Roller.__init__(self, **kwargs)
        self.size = size
        self._prev_angle = 0

    def roll(self):
        Roller.roll(self)

        angle = math.degrees(self.rotation)
        step = abs(self._prev_angle - angle)
        self._prev_angle = angle

        self.x += self.direction * (math.pi * self.outer_radius) * step / 180.0
        if (self.x > self.size - self.outer_radius and self.direction > 0) or \
           (self.x < self.outer_radius and self.direction < 0):
            self.direction = -self.direction




class Scene(graphics.Scene):
    def __init__(self):
        graphics.Scene.__init__(self)
        self.background_color = "#333"


        self.roller = Roller()
        self.roller_container = graphics.Sprite(y=200, x=300)
        self.roller_container.add_child(self.roller)

        self.roller2 = Roller()
        self.roller_container2 = graphics.Sprite(y=200, x=300, scale_y=-1)
        self.roller_container2.add_child(self.roller2)

        self.add_child(self.roller_container, self.roller_container2)

        self.connect("on-enter-frame", self.on_enter_frame)

    def on_enter_frame(self, scene, context):
        # you could do all your drawing here, or you could add some sprites
        g = graphics.Graphics(context)

        #g.move_to(10, 200)
        #g.line_to(self.width - 10, 200)
        #g.stroke("#eee")

        self.roller_container.rotation += 0.01
        self.roller_container2.rotation += 0.01

        self.roller_container.x = self.roller_container2.x = self.width / 2
        self.roller_container.y = self.roller_container2.y = self.height / 2

        self.roller.size = self.width
        self.roller.roll()

        self.roller2.size = self.width
        self.roller2.roll()

        self.redraw() # this is how to get a constant redraw loop (say, for animation)



class BasicWindow:
    def __init__(self):
        window = gtk.Window()
        window.set_default_size(500, 500)
        window.connect("delete_event", lambda *args: gtk.main_quit())
        window.add(Scene())
        window.show_all()


if __name__ == '__main__':
    window = BasicWindow()
    import signal
    signal.signal(signal.SIGINT, signal.SIG_DFL) # gtk3 screws up ctrl+c
    gtk.main()

########NEW FILE########
__FILENAME__ = rotation
#!/usr/bin/env python
# - coding: utf-8 -
# Copyright (C) 2010 Toms Bauģis <toms.baugis at gmail.com>

"""Demonstrating pivot_x and pivot_y"""


from gi.repository import Gtk as gtk
from gi.repository import Gdk as gdk
from lib import graphics
from contrib import euclid

import cairo
import math

class Rotator(graphics.Sprite):
    def __init__(self, x=100, y=100, radius=10):
        graphics.Sprite.__init__(self, x, y, interactive=True, draggable=True)
        self.radius = radius

        self.graphics.circle(0, 0, radius)
        self.graphics.fill("#aaa")

        def sector():
            self.graphics.move_to(radius, 0)
            self.graphics.line_to(0, 0)
            self.graphics.line_to(0, -radius)
            self.graphics.arc(0, 0, radius, -math.pi / 2, 0)

        self.graphics.save_context()
        sector()
        self.graphics.rotate(math.pi)
        sector()
        self.graphics.fill("#f6f6f6")
        self.graphics.restore_context()

        self.graphics.circle(0, 0, radius)
        self.graphics.move_to(-radius, 0.5)
        self.graphics.line_to(radius, 0.5)
        self.graphics.move_to(-0.5, -radius)
        self.graphics.line_to(-0.5, radius)

        self.graphics.set_line_style(width = 1)
        self.graphics.stroke("#333")

class Thing(graphics.Sprite):
    def __init__(self):
        graphics.Sprite.__init__(self, 200, 200, pivot_x=100, pivot_y=25, snap_to_pixel=False, interactive=True)

        # add some shapes
        self.graphics.rectangle(0.5, 0.5, 200, 50, 5)
        self.graphics.stroke("#000")

        self.rotator = Rotator(x=self.pivot_x, y=self.pivot_y)
        self.add_child(self.rotator)

        self.rotator.connect("on-drag", self.on_drag)

    def on_drag(self, sprite, event):
        matrix = cairo.Matrix()

        # the pivot point change causes the sprite to be at different location after
        # rotation so we are compensating that
        # this is bit lame as i could not figure out how to properly
        # transform the matrix so that it would give me back the new delta
        matrix.translate(self.x + self.rotator.x, self.y + self.rotator.y)
        matrix.rotate(self.rotation)
        matrix.translate(-self.rotator.x, -self.rotator.y)
        new_x, new_y =  matrix.transform_point(0,0)

        prev_x, prev_y = self.get_matrix().transform_point(0,0)

        self.x -= new_x - prev_x
        self.y -= new_y - prev_y

        # setting the pivot point
        self.pivot_x, self.pivot_y = self.rotator.x, self.rotator.y


class Scene(graphics.Scene):
    def __init__(self):
        graphics.Scene.__init__(self)

        self.thing = Thing()
        self.rotator = Rotator(x=self.thing.pivot_x, y=self.thing.pivot_y)

        self.add_child(self.thing)

        self.add_child(graphics.Label("Drag to rotate", size=24, color="#999"))
        self.rotating = True

        self.connect("on-drag-start", self.on_drag_start)
        self.connect("on-drag-finish", self.on_drag_finish)

        self.connect("on-mouse-move", self.on_mouse_move)
        self.connect("on-mouse-down", self.on_mouse_down)
        self.connect("on-mouse-up", self.on_mouse_up)

        self.drag_point = None
        self.start_rotation = None

    def on_mouse_down(self, scene, event):
        sprite = self.get_sprite_at_position(event.x, event.y)
        if sprite == self.thing:
            self.drag_point = euclid.Point2(event.x, event.y)
            self.start_rotation = self.thing.rotation

    def on_mouse_up(self, scene, event):
        self.drag_point = None
        self.start_rotation = None

    def on_mouse_move(self, scene, event):
        mouse_down = gdk.ModifierType.BUTTON1_MASK & event.state
        if mouse_down and self.drag_point:
            pivot_x, pivot_y = self.thing.get_matrix().transform_point(self.thing.pivot_x, self.thing.pivot_y)

            pivot_point = euclid.Point2(pivot_x, pivot_y)
            drag_vector = euclid.Point2(event.x, event.y) - pivot_point

            start_vector = self.drag_point - pivot_point

            angle = math.atan2(start_vector.y, start_vector.x) - math.atan2(drag_vector.y, drag_vector.x)


            delta = (self.start_rotation - angle) - self.thing.rotation

            # full revolution jumps from -180 to 180 degrees
            if abs(delta) >= math.pi:
                delta = 0

            self.thing.rotation = self.start_rotation - angle


    def on_drag_start(self, scene, sprite, event):
        self.rotating = False

    def on_drag_finish(self, scene, sprite, event):
        self.rotating = True




class BasicWindow:
    def __init__(self):
        window = gtk.Window()
        window.set_default_size(600, 500)
        window.connect("delete_event", lambda *args: gtk.main_quit())
        window.add(Scene())
        window.show_all()

if __name__ == '__main__':
    window = BasicWindow()
    import signal
    signal.signal(signal.SIGINT, signal.SIG_DFL) # gtk3 screws up ctrl+c
    gtk.main()

########NEW FILE########
__FILENAME__ = slice9
#!/usr/bin/env python
# - coding: utf-8 -
# Copyright (C) 2010 Erik Blankinship <jedierikb at gmail.com>
# Copyright (C) 2010 Toms Bauģis <toms.baugis at gmail.com>

"""
 An example of slice9 scaling where the center rows and columns get stretched.
 As seen in CSS3 and all other good frameworks.
 This most probably will go into graphics.py eventually.
"""

from gi.repository import Gtk as gtk
import cairo

from lib import graphics

class Slice9(graphics.Sprite):
    def __init__(self, file_name, x1, x2, y1, y2, width = None, height = None):
        graphics.Sprite.__init__(self)

        image = cairo.ImageSurface.create_from_png(file_name)
        image_width, image_height = image.get_width(), image.get_height()

        self.width = width or image_width
        self.height = height or image_height

        self.left, self.right = x1, image_width - x2
        self.top, self.bottom = y1, image_height - y2

        image_content = image.get_content()
        self.slices = []
        def get_slice(x, y, w, h):
            img = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
            ctx = cairo.Context(img)
            ctx.set_source_surface(image, -x, -y)
            ctx.rectangle(0, 0, w, h)
            ctx.fill()
            return img

        exes = (0, x1, x2, image_width)
        ys = (0, y1, y2, image_height)
        for y1, y2 in zip(ys, ys[1:]):
            for x1, x2 in zip(exes, exes[1:]):
                self.slices.append(get_slice(x1, y1, x2 - x1, y2 - y1))

        self.corners = [
            graphics.BitmapSprite(self.slices[0]),
            graphics.BitmapSprite(self.slices[2]),
            graphics.BitmapSprite(self.slices[6]),
            graphics.BitmapSprite(self.slices[8]),
        ]
        self.add_child(*self.corners)


        self.connect("on-render", self.on_render)

    def get_center_bounds(self):
        return (self.left,
                self.top,
                self.width - self.left - self.right,
                self.height - self.top - self.bottom)

    def on_render(self, sprite):
        def put_pattern(image, x, y, w, h):
            pattern = cairo.SurfacePattern(image)
            pattern.set_extend(cairo.EXTEND_REPEAT)
            self.graphics.save_context()
            self.graphics.translate(x, y)
            self.graphics.set_source(pattern)
            self.graphics.rectangle(0, 0, w, h)
            self.graphics.fill()
            self.graphics.restore_context()

        # top center - repeat width
        put_pattern(self.slices[1],
                    self.left, 0,
                    self.width - self.left - self.right, self.top)

        # top right
        self.corners[1].x = self.width - self.right


        # left - repeat height
        put_pattern(self.slices[3],
                    0, self.top,
                    self.left, self.height - self.top - self.bottom)

        # center - repeat width and height
        put_pattern(self.slices[4],
                    self.left, self.top,
                    self.width - self.left - self.right,
                    self.height - self.top - self.bottom)

        # right - repeat height
        put_pattern(self.slices[5],
                    self.width - self.right, self.top,
                    self.right, self.height - self.top - self.bottom)

        # bottom left
        self.corners[2].y = self.height - self.bottom

        # bottom center - repeat width
        put_pattern(self.slices[7],
                    self.left, self.height - self.bottom,
                    self.width - self.left - self.right, self.bottom)

        # bottom right
        self.corners[3].x = self.width - self.right
        self.corners[3].y = self.height - self.bottom




class Scene(graphics.Scene):
    def __init__(self):
        graphics.Scene.__init__(self)
        self.slice = Slice9('assets/slice9.png', 35, 230, 35, 220)
        self.add_child(self.slice)
        self.connect("on-enter-frame", self.on_enter_frame)

    def on_enter_frame(self, scene, context):
        self.slice.x, self.slice.y = 5, 5
        self.slice.width = self.width - 10
        self.slice.height = self.height - 10

class BasicWindow:
    def __init__(self):
        window = gtk.Window()
        window.set_default_size(640, 516)
        window.connect("delete_event", lambda *args: gtk.main_quit())
        window.add(Scene())
        window.show_all()


if __name__ == "__main__":
    example = BasicWindow()
    import signal
    signal.signal(signal.SIGINT, signal.SIG_DFL) # gtk3 screws up ctrl+c
    gtk.main()

########NEW FILE########
__FILENAME__ = space
#!/usr/bin/env python
# - coding: utf-8 -
# Copyright (C) 2014 Toms Baugis <toms.baugis@gmail.com>

"""Base template"""
import math

from gi.repository import Gtk as gtk
from gi.repository import GObject as gobject
from lib import graphics

"""wanna look into the third dimensions
 * can't use scale_x, scale_y as those will mess up the stroke
 * should be operating with points in 3d
 * assuming horizon at specific coordinates (middle)
 * at depth 0, x=screen_x, y=screen_y
"""

class Point3D(gobject.GObject):
    __gsignals__ = {
        "on-point-changed": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, ()),
    }
    def __init__(self, x=0, y=0, depth=0, perspective_skew=0):
        gobject.GObject.__init__(self)
        self.perspective_skew = perspective_skew or 0
        self.max_depth = 1000.0

        self._x = x
        self._y = y
        self.z = 1

    @property
    def z_skew(self):
        skew = (self.z / self.max_depth)
        return skew ** 0.3 if skew > 0 else 0

    @property
    def angle(self):
        return math.atan2(self._x, self._y) - math.radians(90)

    @property
    def from_center(self):
        return math.sqrt(self._x ** 2 + self._y ** 2)

    @property
    def x(self):
        x = math.cos(self.angle) * self.from_center
        return x - x * self.z_skew * self.perspective_skew

    @x.setter
    def x(self, val):
        self._x = val
        self.emit("on-point-changed")

    @property
    def y(self):
        y = math.sin(self.angle) * self.from_center
        return -y + y * self.z_skew

    @y.setter
    def y(self, val):
        self._y = val
        self.emit("on-point-changed")


    def __setattr__(self, name, val):
        if isinstance(getattr(type(self), name, None), property) and \
           getattr(type(self), name).fset is not None:
            getattr(type(self), name).fset(self, val)
            return
        gobject.GObject.__setattr__(self, name, val)


    def __iter__(self):
        yield self.x
        yield self.y

    def __repr__(self):
        return "<%s x=%d, y=%d, z=%d>" % (self.__class__.__name__, self.x, self.y, self.z)



class Scene(graphics.Scene):
    def __init__(self):
        graphics.Scene.__init__(self, background_color="#333")
        self.a, self.b = Point3D(-800, 500), Point3D(800, 500)

        self.viewport_depth = 0

        self.connect("on-enter-frame", self.on_enter_frame)
        self.connect("on-mouse-move", self.on_mouse_move)

    def on_mouse_move(self, scene, event):
        x = event.x * 1.0 / scene.width
        self.a.perspective_skew = 1 - x
        self.b.perspective_skew = 1 - x

    def on_enter_frame(self, scene, context):
        # you could do all your drawing here, or you could add some sprites
        g = graphics.Graphics(context)

        g.translate(self.width / 2, self.height / 2 - 100)

        g.move_to(-500, 0)
        g.line_to(500, 0)
        g.stroke("#33F2F0", 0.2)

        for z in range(-10, 1000, 50):
            for dot in (self.a, self.b):
                dot.z = z - self.viewport_depth

            g.move_to(*self.a)
            g.line_to(*self.b)

            #g.set_line_style(int(30 * (1 - z / 1000.0)))
            g.stroke("#33F2F0", 1 - z / 1000.0 * 0.8)

        self.viewport_depth += 1
        if self.viewport_depth > 50:
            self.viewport_depth = 0

        self.redraw()
        #self.a.z += 0.01
        #self.b.z += 0.01


        #self.redraw()



class BasicWindow:
    def __init__(self):
        window = gtk.Window()
        window.set_default_size(700, 600)
        window.connect("delete_event", lambda *args: gtk.main_quit())
        window.add(Scene())
        window.show_all()


if __name__ == '__main__':
    window = BasicWindow()
    import signal
    signal.signal(signal.SIGINT, signal.SIG_DFL) # gtk3 screws up ctrl+c
    gtk.main()

########NEW FILE########
__FILENAME__ = sprite_balls
#!/usr/bin/env python
# - coding: utf-8 -

from gi.repository import Gtk as gtk
from lib import graphics
from themes import utils

import cairo

class Scene(graphics.Scene):
    def __init__(self):
        graphics.Scene.__init__(self)

        self.sprite_sheet = graphics.Image("assets/spritesheet.png")
        self.frame = 0

        self.connect("on-enter-frame", self.on_enter_frame)

        x, y = 0, 0
        step = 60
        self.coords = []
        for i in range(60):
            self.coords.append((x, y))

            self.add_child(utils.SpriteSheetImage(self.sprite_sheet, x, y, 60, 60, x=x, y=y))

            x += step
            if x > 420:
                x = 0
                y += step

        print self.coords

    def on_enter_frame(self, scene, context):
        for (x, y), sprite in zip(self.coords, self.sprites[self.frame:] + self.sprites[:self.frame]):
            sprite.offset_x, sprite.offset_y = x, y


        self.frame +=1
        if self.frame > 59:
            self.frame = 0


        self.redraw()




class BasicWindow:
    def __init__(self):
        window = gtk.Window()
        window.set_default_size(800, 600)
        window.connect("delete_event", lambda *args: gtk.main_quit())

        scene = Scene()
        window.add(scene)
        window.show_all()

if __name__ == '__main__':
    window = BasicWindow()
    import signal
    signal.signal(signal.SIGINT, signal.SIG_DFL) # gtk3 screws up ctrl+c
    gtk.main()

########NEW FILE########
__FILENAME__ = storing_input
#!/usr/bin/env python
# - coding: utf-8 -
# Copyright (C) 2010 Toms Bauģis <toms.baugis at gmail.com>

"""
 Move the mouse across the screen to change the position of the rectangles.
 The positions of the mouse are recorded into a list and played back every frame.
 Between each frame, the newest value are added to the start of the list.

 Ported from processing.js (http://processingjs.org/learning/basic/storinginput)
"""

from gi.repository import Gtk as gtk
from lib import graphics
from lib.pytweener import Easing

import math


class Segment(object):
    def __init__(self, x, y, color, width):
        self.x = x
        self.y = y
        self.color = color
        self.width = width


class Scene(graphics.Scene):
    def __init__(self):
        graphics.Scene.__init__(self)
        self.segments = []
        self.connect("on-mouse-move", self.on_mouse_move)
        self.connect("on-enter-frame", self.on_enter_frame)


    def on_mouse_move(self, widget, event):
        x, y = event.x, event.y

        segment = Segment(x, y, "#666666", 50)
        self.tweener.add_tween(segment, easing = Easing.Cubic.ease_out, duration=1.5, width = 0)
        self.segments.insert(0, segment)

    def on_enter_frame(self, scene, context):
        g = graphics.Graphics(context)


        # on expose is called when we are ready to draw
        for i, segment in reversed(list(enumerate(self.segments))):
            if segment.width:
                g.rectangle(segment.x - segment.width / 2.0,
                            segment.y - segment.width / 2.0,
                            segment.width,
                            segment.width, 3)
                g.fill(segment.color, 0.5)

            else:
                del self.segments[i]

        self.redraw()


class BasicWindow:
    def __init__(self):
        window = gtk.Window()
        window.set_size_request(600, 400)
        window.connect("delete_event", lambda *args: gtk.main_quit())

        window.add(Scene())
        window.show_all()


if __name__ == "__main__":
    example = BasicWindow()
    import signal
    signal.signal(signal.SIGINT, signal.SIG_DFL) # gtk3 screws up ctrl+c
    gtk.main()

########NEW FILE########
__FILENAME__ = strange_attractor
#!/usr/bin/env python
# - coding: utf-8 -
# Copyright (C) 2010 Toms Bauģis <toms.baugis at gmail.com>
""" guilloches, following.  observe how detail grows and your cpu melts.
    move mouse horizontally and vertically to change parameters
    http://ministryoftype.co.uk/words/article/guilloches/

    TODO - this is now brokeh, need to find how to get back canvas-like behavior
    which wouldn't repaint at each frame
"""

from gi.repository import Gtk as gtk
from lib import graphics
import colorsys
import math
import cairo


class Scene(graphics.Scene):
    def __init__(self):
        graphics.Scene.__init__(self)
        self.set_double_buffered(False)

        self.a = 1.4191403
        self.b = -2.2841523
        self.c = 2.4275403
        self.d = -2.177196
        self.points = 2000

        self.x, self.y = 0,0
        self.image = None
        self.prev_width, self.prev_height = 0, 0

        self.connect("on-enter-frame", self.on_enter_frame)

    def on_enter_frame(self, scene, context):
        g = graphics.Graphics(context)

        if self.prev_width != self.width or self.prev_height != self.height:
            self.x, self.y = 0,0

        if self.x == 0 and self.y ==0:
            g.fill_area(0,0, self.width, self.height, "#fff")


        for i in range(1000):
            self.x = math.sin(self.a * self.y) - math.cos(self.b * self.x)
            self.y = math.sin(self.c * self.x) - math.cos(self.d * self.y)

            x = int(self.x * self.width * 0.2 + self.width / 2)
            y = int(self.y * self.height * 0.2  + self.height / 2)

            g.rectangle(x, y, 1, 1)

        g.fill("#000", 0.08)

        self.prev_width, self.prev_height = self.width, self.height
        self.redraw()

class BasicWindow:
    def __init__(self):
        window = gtk.Window()
        window.set_default_size(800, 500)
        window.connect("delete_event", lambda *args: gtk.main_quit())

        window.add(Scene())
        window.show_all()


if __name__ == "__main__":
    example = BasicWindow()
    import signal
    signal.signal(signal.SIGINT, signal.SIG_DFL) # gtk3 screws up ctrl+c
    gtk.main()

########NEW FILE########
__FILENAME__ = sun
#!/usr/bin/env python
# - coding: utf-8 -
# Copyright (C) 2010 Toms Bauģis <toms.baugis at gmail.com>

from gi.repository import Gtk as gtk
from lib import graphics
import math

class Scene(graphics.Scene):
    def __init__(self):
        graphics.Scene.__init__(self)
        self.connect("on-finish-frame", self.on_enter_frame)
        self.start_angle = 0
        self.framerate = 120

    def on_enter_frame(self, scene, context):
        self.start_angle += 0.01 * 60 / self.framerate # good way to keep the speed constant when overriding frame rate

        g = graphics.Graphics(context)

        g.fill_area(0, 0, self.width, self.height, "#f00")
        g.set_line_style(width = 0.5)
        g.set_color("#fff")

        x, y = self.width / 2, self.height / 2

        x = x + math.sin(self.start_angle * 0.3) * self.width / 4

        center_distance = math.cos(self.start_angle) * self.width / 8

        angle = self.start_angle
        step = math.pi * 2 / 64

        distance = max(self.width, self.height)

        while angle < self.start_angle + math.pi * 2:
            g.move_to(x + math.cos(angle) * center_distance, y + math.sin(angle) * center_distance)
            g.line_to(x + math.cos(angle) * distance, y + math.sin(angle) * distance)
            g.line_to(x + math.cos(angle+step) * distance, y + math.sin(angle+step) * distance)
            g.line_to(x + math.cos(angle) * center_distance,y + math.sin(angle) * center_distance)

            angle += step * 2

        g.fill()
        self.redraw()

class BasicWindow:
    def __init__(self):
        window = gtk.Window()
        window.set_size_request(600, 500)
        window.connect("delete_event", lambda *args: gtk.main_quit())
        window.add(Scene())
        window.show_all()

example = BasicWindow()
import signal
signal.signal(signal.SIGINT, signal.SIG_DFL) # gtk3 screws up ctrl+c
gtk.main()

########NEW FILE########
__FILENAME__ = symmetry
#!/usr/bin/env python
# - coding: utf-8 -
# Copyright (C) 2014 Toms Baugis <toms.baugis@gmail.com>

"""Exploring symmetry. Feel free to add more handles!"""
import math
from gi.repository import Gtk as gtk
from lib import graphics


class SymmetricalRepeater(graphics.Sprite):
    def __init__(self, sides, master_poly=None, **kwargs):
        graphics.Sprite.__init__(self, **kwargs)
        self.sides = sides #: number of sides this symmetrical dude will have

        self.master_poly = master_poly or []

        # duplicates the poly N times and you can control wether the
        # changes that happen to the master poly are distributed at once
        # or one-by-one

        self.connect("on-render", self.on_render)

    def on_render(self, sprite):
        angle = 360.0 / self.sides

        # debug
        self.graphics.save_context()
        for i in range(self.sides):
            self.graphics.move_to(0, 0)
            self.graphics.line_to(1000, 0)
            self.graphics.rotate(math.radians(angle))
        self.graphics.stroke("#3d3d3d")
        self.graphics.restore_context()


        for i in range(self.sides):
            self.graphics.move_to(*self.master_poly[0])
            for dot in self.master_poly[1:]:
                self.graphics.line_to(*dot)
            self.graphics.rotate(math.radians(angle))
        self.graphics.stroke("#fff")


class Handle(graphics.Sprite):
    def __init__(self, **kwargs):
        graphics.Sprite.__init__(self, **kwargs)
        self.interactive=True
        self.draggable=True

        self.connect("on-render", self.on_render)

    def on_render(self, sprite):
        self.graphics.rectangle(-5, -5, 10, 10, 3)
        self.graphics.fill("#eee")


class Scene(graphics.Scene):
    def __init__(self):
        graphics.Scene.__init__(self, background_color="#333")
        self.handles = graphics.Sprite()
        self.add_child(self.handles)
        self.repeater = None
        self.connect("on-resize", self.on_resize)
        self.connect("on-first-frame", self.on_first_frame)

    def on_first_frame(self, scene, context):
        self.create_repeater(4)

    def on_resize(self, scene, event):
        for sprite in self.sprites:
            sprite.x, sprite.y = self.width / 2, self.height / 2


    def create_repeater(self, sides):
        self.clear()
        master_poly = [(100, 0), (150, 0), (200, 0)]
        self.repeater = SymmetricalRepeater(sides, master_poly=master_poly, x=self.width/2, y=self.height/2)
        self.add_child(self.repeater)

        self.add_child(self.handles)
        self.handles.x, self.handles.y = self.repeater.x, self.repeater.y


        self.handles.clear()
        for dot in master_poly:
            handle = Handle(x=dot[0], y=dot[1])
            self.handles.add_child(handle)
            handle.connect("on-drag", self.adjust_master_poly)


    def adjust_master_poly(self, sprite, event):
        self.repeater.master_poly = [(handle.x, handle.y) for handle in self.handles.sprites]



class BasicWindow:
    def __init__(self):
        window = gtk.Window()
        window.set_default_size(600, 550)
        window.connect("delete_event", lambda *args: gtk.main_quit())

        self.scene = Scene()

        box = gtk.VBox()
        box.pack_start(self.scene, True, True, 0)

        hbox = gtk.HBox(spacing=10)
        mo = gtk.Button("More")
        less = gtk.Button("Less")
        for button in (less, mo):
            hbox.add(button)
            button.connect("clicked", self.on_button_click)

        hbox.set_border_width(12)
        box.pack_end(hbox, False, True, 0)

        window.add(box)
        window.show_all()

    def on_button_click(self, button):
        delta = 1 if button.get_label() == "More" else -1
        sides = max(1, self.scene.repeater.sides + delta)
        self.scene.create_repeater(sides)


if __name__ == '__main__':
    window = BasicWindow()
    import signal
    signal.signal(signal.SIGINT, signal.SIG_DFL) # gtk3 screws up ctrl+c
    gtk.main()

########NEW FILE########
__FILENAME__ = tangent_arcs
#!/usr/bin/env python
# - coding: utf-8 -
# Copyright (C) 2010 Toms Bauģis <toms.baugis at gmail.com>
""" guilloches, following.  observe how detail grows and your cpu melts.
    move mouse horizontally and vertically to change parameters
    http://ministryoftype.co.uk/words/article/guilloches/
"""

from gi.repository import Gtk as gtk
from lib import graphics
from contrib.euclid import Vector2

import math

class CenteredCircle(graphics.Sprite):
    """we don't have alignment yet and the pivot model is such that it does not
       alter anchor so the positioning would be predictable"""
    def __init__(self, x, y, radius):
        graphics.Sprite.__init__(self, x, y, interactive=True,draggable=True)
        self.radius = radius

        self.graphics.circle(0, 0, self.radius)
        self.graphics.fill_stroke("#ccc", "#999", 1)

class Scene(graphics.Scene):
    def __init__(self):
        graphics.Scene.__init__(self)

        self.circle1 = CenteredCircle(100, 300, 90)
        self.circle2 = CenteredCircle(350, 300, 50)

        self.add_child(self.circle1)
        self.add_child(self.circle2)

        self.tangent = graphics.Sprite(interactive = False)
        self.add_child(self.tangent)

        self.draw_tangent()

        self.connect("on-drag", self.on_drag_circle)


    def on_drag_circle(self, scene, drag_sprite, event):
        self.draw_tangent()

    def draw_tangent(self):
        tangent = self.tangent
        tangent.graphics.clear()

        tangent.graphics.set_line_style(width = 0.5)

        band_radius = 30

        v1 = Vector2(self.circle1.x, self.circle1.y)
        v2 = Vector2(self.circle2.x, self.circle2.y)

        distance = abs(v1 - v2)



        tangent.graphics.set_color("#000")
        #tangent.graphics.move_to(v1.x, v1.y)
        #tangent.graphics.line_to(v2.x, v2.y)

        c = distance
        distance = 100

        a = distance + self.circle2.radius
        b = distance + self.circle1.radius


        orientation = (v2-v1).heading()

        # errrm, well, basically the one is in the other
        if (b**2 + c**2 - a**2) / (2.0 * b * c) >= 1:
            tangent.graphics.arc(v1.x, v1.y, max(self.circle1.radius, self.circle2.radius) + band_radius, 0, math.pi * 2)
            tangent.graphics.stroke()
            return


        # we have to figure out the angle for the vector that is pointing
        # towards the point C (which will help as to draw that tangent)
        left_angle = math.acos((b**2 + c**2 - a**2) / (2.0 * b * c))
        arc_angle = math.acos((a**2 + b**2 - c**2) / (2.0 * a * b))

        # arc on the one side
        a1 = left_angle + orientation
        x, y = math.cos(a1) * b, math.sin(a1) * b

        v3_1 = Vector2(v1.x+x, v1.y+y)
        tangent.graphics.arc(v3_1.x, v3_1.y, distance - band_radius, (v1 - v3_1).heading(), (v2 - v3_1).heading())
        tangent.graphics.stroke()



        # arc on the other side (could as well flip at the orientation axis, too dumb to do that though)
        a2 = -left_angle + orientation
        x, y = math.cos(a2) * b, math.sin(a2) * b
        v3_2 = Vector2(v1.x+x, v1.y+y)

        tangent.graphics.arc(v3_2.x, v3_2.y, distance - band_radius, (v2 - v3_2).heading(), (v1 - v3_2).heading())
        tangent.graphics.stroke()



        # the rest of the circle
        tangent.graphics.arc(v1.x, v1.y, self.circle1.radius + band_radius, (v3_1-v1).heading(), (v3_2-v1).heading())
        tangent.graphics.stroke()

        tangent.graphics.arc_negative(v2.x, v2.y, self.circle2.radius + band_radius, (v3_1-v2).heading(), (v3_2-v2).heading())
        tangent.graphics.stroke()


class BasicWindow:
    def __init__(self):
        window = gtk.Window()
        window.set_size_request(800, 600)
        window.connect("delete_event", lambda *args: gtk.main_quit())
        window.add(Scene())
        window.show_all()


if __name__ == "__main__":
    example = BasicWindow()
    import signal
    signal.signal(signal.SIGINT, signal.SIG_DFL) # gtk3 screws up ctrl+c
    gtk.main()

########NEW FILE########
__FILENAME__ = bitmaps
from gi.repository import Gtk as gtk
from gi.repository import Gdk as gdk
from gi.repository import Pango as pango

import cairo
from lib import graphics
import ui
from utils import override, get_image


"""
@override(ui.VBox)
def do_render(self, *args):
    self.graphics.rectangle(0, 0, self.width, self.height)
    image_data = cairo.ImageSurface.create_from_png("themes/assets/background.png")


    pattern = cairo.SurfacePattern(image_data)
    pattern.set_extend(cairo.EXTEND_REPEAT)

    self.graphics.set_source(pattern)
    self.graphics.fill()
"""


""" The theme starts here """

#ui.Entry.font_desc = pango.FontDescription('Danube 8')
#ui.Label.font_desc = pango.FontDescription('Danube 8')

@override(ui.Label)
def do_render(self):
    """the label is looking for an background_image attribute and if it is found
    it paints it"""
    if getattr(self, "background_image", None):
        self.background_image.render(self.graphics, self.width, self.height)

ui.Button.images = {
    "normal": get_image("themes/assets/button_normal.png", 3, 3, 3, 3),
    "highlight": get_image("themes/assets/button_highlight.png", 3, 3, 3, 3),
    "pressed": get_image("themes/assets/button_pressed.png", 3, 3, 3, 3),
    "disabled": get_image("themes/assets/button_disabled.png", 3, 3, 3, 3),
}

ui.Button.font_desc = pango.FontDescription('Serif 10')
@override(ui.Button)
def do_render(self, state=None):
    """ Properties that affect rendering:
        state:   normal / highlight / pressed
        focused: True / False
        enabled: True / False
    """
    state = state or self.state

    if self.enabled:
        self.display_label.color = "#000"
        self.display_label.background_image = None
        image = self.images.get(state)
    else:
        self.display_label.color = "#999"
        image = self.images["disabled"]

    image.render(self.graphics, self.width, self.height)


@override(ui.ToggleButton)
def do_render(self, *args):
    """this example of togglebutton does not sort out the button-group, where
    you would have different graphics for first and last item"""
    state = self.state
    if self.toggled:
        state = "pressed"
    ui.Button.do_render(self, state = state)


ui.Entry.images = {
    "normal": get_image("themes/assets/input_normal.png", 5, 5, 5, 5),
    "disabled":  get_image("themes/assets/input_disabled.png", 5, 5, 5, 5)
}
@override(ui.Entry)
def do_render(self):
    """ Properties that affect rendering:
        state:   normal / highlight / pressed
        focused: True / False
        enabled: True / False
    """
    if self.draw_border:
        image = self.images["normal"] if self.enabled else self.images["disabled"]
        image.render(self.graphics, self.width, self.height)


ui.CheckMark.images = {
    # toggled, enabled - all combinations
    (False, True): get_image("themes/assets/checkbox_normal.png"),
    (True, True):  get_image("themes/assets/checkbox_toggled.png"),
    (False, False): get_image("themes/assets/checkbox_disabled.png"),
    (True, False):  get_image("themes/assets/checkbox_disabled_toggled.png")
}
@override(ui.CheckMark)
def do_render(self, *args):
    """ Properties that affect rendering:
        state:   normal / highlight / pressed
        focused: True / False
        enabled: True / False
    """

    image = self.images[(self.toggled, self.enabled)]
    image.render(self.graphics)




@override(ui.SliderSnapPoint)
def do_render(self):
    """the label is looking for an background_image attribute and if it is found
    it paints it"""
    pass



ui.SliderGrip.grip_image = get_image("themes/assets/slider_knob.png")
ui.SliderGrip.width = ui.SliderGrip.grip_image.width

@override(ui.SliderGrip)
def do_render(self):
    w, h = self.width, self.height
    self.grip_image.render(self.graphics)


ui.Slider.images = {
    "background": get_image("themes/assets/slider_bg.png", 4, 4, 4, 4),
    "fill": get_image("themes/assets/slider_fill.png", 4, 4, 4, 4),
}

@override(ui.Slider)
def do_render(self):
    x = 0
    y = self.start_grip.grip_image.height

    w = self.width
    h = self.images["background"].height

    self.images["background"].render(self.graphics, w, h, x, 3)

    start_x, end_x = self.start_grip.x, self.end_grip.x
    if self.range is True and start_x > end_x:
        start_x, end_x = end_x, start_x


    if self.range == "start":
        self.images['fill'].render(self.graphics, int(start_x) + 9, 9, 0, 3)
    elif self.range == "end":
        self.images['fill'].render(self.graphics, self.width - int(start_x) , 9, int(start_x), 3)
    elif self.range is True:
        if not self.inverse:
            # middle
            self.images['fill'].render(self.graphics, end_x - start_x + 6, 9, int(start_x), 3)
        else:
            self.images['fill'].render(self.graphics, int(start_x) + 9, 9, 0, 3)
            self.images['fill'].render(self.graphics, self.width - int(end_x) , 9, int(end_x), 3)





ui.ScrollBar.images = {
    "normal": get_image("themes/assets/scrollbar/gutter_s9.png", 1,1,1,1),
    "disabled": get_image("themes/assets/scrollbar/gutter_s9_disabled.png", 1,1,1,1),
}
ui.ScrollBar.thickness = 10

@override(ui.ScrollBar)
def do_render(self):
    image = self.images["normal"] if self.enabled else self.images["disabled"]
    image.render(self.graphics, self.width, self.height)


ui.ScrollBarSlider.images = {
    "normal": get_image("themes/assets/scrollbar/knob.png", 2, 2, 2, 2),
    "highlight": get_image("themes/assets/scrollbar/knob_hot.png", 2, 2, 2, 2),
    "pressed": get_image("themes/assets/scrollbar/knob_down.png", 2, 2, 2, 2),
    "disabled": get_image("themes/assets/scrollbar/knob_disabled.png", 2, 2, 2, 2),
}
@override(ui.ScrollBarSlider)
def do_render(self):
    state = self.state
    if not self.enabled:
        state = "disabled"
    elif self.get_scene() and self.get_scene()._drag_sprite == self:
        state = "pressed"

    self.images[state].render(self.graphics, self.width, self.height)


ui.ScrollBarButton.images = {
    "up_normal": get_image("themes/assets/scrollbar/up.png"),
    "up_pressed": get_image("themes/assets/scrollbar/up_down.png"),
    "up_disabled": get_image("themes/assets/scrollbar/up_disabled.png"),
    "down_normal": get_image("themes/assets/scrollbar/dn.png"),
    "down_pressed": get_image("themes/assets/scrollbar/dn_down.png"),
    "down_disabled": get_image("themes/assets/scrollbar/dn_disabled.png"),
}
@override(ui.ScrollBarButton)
def do_render(self):
    state = self.state
    if not self.enabled:
        state = "disabled"

    direction = self.direction
    if direction in ("left", "right"): #haven't rotated the left/right ones yet
        direction = "up" if direction == "left" else "down"

    image = self.images.get("%s_%s" % (direction, state)) or self.images["%s_normal" % direction]

    image.render(self.graphics, self.width, self.height)

########NEW FILE########
__FILENAME__ = plain
import cairo

from lib import graphics
import ui
from utils import override, vertical_gradient


""" here starts the theme """
@override(ui.Button)
def do_render(self, *args):
    """ Properties that affect rendering:
        state:   normal / highlight / pressed
        focused: True / False
        enabled: True / False
    """

    self.graphics.set_line_style(width=1)
    self.graphics.rectangle(0.5, 0.5, self.width, self.height, 4)

    if self.state == "highlight":
        vertical_gradient(self, "#fff", "#edeceb", 0, self.height)
        self.graphics.fill_preserve()
    elif self.state == "pressed":
        vertical_gradient(self, "#B9BBC0", "#ccc", 0, self.height)
        self.graphics.fill_preserve()
    else:
        # normal
        vertical_gradient(self, "#fcfcfc", "#e8e7e6", 0, self.height)
        self.graphics.fill_preserve()


    if self.focused:
        self.graphics.stroke("#89ADDA")
    elif self.state == "pressed":
        self.graphics.stroke("#aaa")
    else:
        self.graphics.stroke("#cdcdcd")



@override(ui.ToggleButton)
def do_render(self):
    self.graphics.set_line_style(width=1)

    x, y, x2, y2 = 0.5, 0.5, 0.5 + self.width, 0.5 + self.height
    if isinstance(self.parent, ui.Group) == False or len(self.parent.sprites) == 1:
        # normal button
        self.graphics.rectangle(0.5, 0.5, self.width, self.height, 4)
    elif self.parent.sprites.index(self) == 0:
        self._rounded_line([(x2, y), (x, y), (x, y2), (x2, y2)], 4)
        self.graphics.line_to(x2, y)
    elif self.parent.sprites.index(self) == len(self.parent.sprites) - 1:
        self._rounded_line([(x, y), (x2, y), (x2, y2), (x, y2)], 4)
        self.graphics.line_to(x, y)
    else:
        self.graphics.rectangle(x, y, x2 - 0.5, y2 - 0.5)

    state = self.state
    if self.toggled:
        state = "pressed"

    # move the label when pressed a bit
    self.label_container.padding_left = 1 if state == "pressed" else 0
    self.label_container.padding_right = -1 if state == "pressed" else 0
    self.label_container.padding_top = 1 if state == "pressed" else 0
    self.label_container.padding_bottom = -1 if state == "pressed" else 0

    if state == "highlight":
        vertical_gradient(self, "#fff", "#edeceb", 0, self.height)
        self.graphics.fill_preserve()
    elif state == "pressed":
        vertical_gradient(self, "#B9BBC0", "#ccc", 0, self.height)
        self.graphics.fill_preserve()
    else:
        # normal
        vertical_gradient(self, "#fcfcfc", "#e8e7e6", 0, self.height)
        self.graphics.fill_preserve()


    if self.focused:
        self.graphics.stroke("#89ADDA")
    elif state == "pressed":
        self.graphics.stroke("#aaa")
    else:
        self.graphics.stroke("#cdcdcd")




@override(ui.CheckButton)
def do_render(self):
    tick_box_size = 12

    x, y = tick_box_size + self.padding_left + 1, (self.height - tick_box_size) / 2.0
    x, y = int(x) + 0.5, int(y) + 0.5

    stroke = "#999"
    if self.state in ("highlight", "pressed"):
        stroke = "#333"

    self.graphics.rectangle(x, y, tick_box_size, tick_box_size)
    vertical_gradient(self, "#fff", "#edeceb", y, y + tick_box_size)
    self.graphics.fill_preserve()

    self.graphics.stroke(stroke)


    if self.toggled:
        self.graphics.set_line_style(1)
        self.graphics.move_to(x + 2, y + tick_box_size * 0.5)
        self.graphics.line_to(x + tick_box_size * 0.4, y + tick_box_size - 3)
        self.graphics.line_to(x + tick_box_size - 2, y + 2)
        self.graphics.stroke("#333")

    self.graphics.rectangle(0, 0, self.width, self.height)
    self.graphics.new_path()



@override(ui.RadioButton)
def do_render(self):
    radio_radius = 5.5

    x, y = self._radio_radius + self.padding_left + 1, self.height / 2.0
    x, y = int(x) + 0.5, int(y) + 0.5

    stroke = "#999"
    if self.state in ("highlight", "pressed"):
        stroke = "#333"

    self.graphics.circle(x, y, self._radio_radius)
    self.graphics.fill_stroke("#fff", stroke)


    if self.toggled:
        self.graphics.circle(x, y, self._radio_radius - 2)
        self.graphics.fill("#999")

    self.graphics.rectangle(0, 0, self.width, self.height)
    self.graphics.new_path()

########NEW FILE########
__FILENAME__ = utils
import os, shutil
import cairo
from gi.repository import Gtk as gtk
from gi.repository import Gdk as gdk
from gi.repository import GdkPixbuf

from lib import graphics

def install_font(font_filename):
    fonts_dir = os.path.join(os.environ['HOME'], '.fonts')
    if not os.path.exists(fonts_dir):
        os.makedirs(fonts_dir)

    font_path = os.path.join(fonts_dir, font_filename)
    if not os.path.exists(font_path):
        shutil.copyfile(os.path.join("assets", font_filename), font_path)


class override(object):
    """decorator that replaces do_render with the declared function and
    stores the original _do_render in case we might want it bit later"""
    def __init__(self, target_class):
        self.target_class = target_class

    def __call__(self, fn):
        name = fn.__name__
        # backup original
        setattr(self.target_class, "_original_%s" % name, getattr(self.target_class, name))
        # replace with the new one
        setattr(self.target_class, name, fn)



images = {}
def get_image(path, left = None, right = None, top = None, bottom = None):
    """returns image sliced up in margins as specified by left, right, top, bottom.
    The result is a Slice9 object below that has .render function for simplified
    rendering"""
    image = images.get((path, left, right, top, bottom))
    if not image:
        if any((left is not None, right is not None, top is not None, bottom is not None)):
            image = Slice9(path, left, right, top, bottom)
        else:
            image = Image(path)
    return image


# TODO - figure if perhaps this belongs to graphics
def vertical_gradient(sprite, start_color, end_color, start_y, end_y):
    linear = cairo.LinearGradient(0, start_y, 0, end_y)
    linear.add_color_stop_rgb(0, *graphics.Colors.parse(start_color))
    linear.add_color_stop_rgb(1, *graphics.Colors.parse(end_color))
    sprite.graphics.set_source(linear)



class Image(object):
    def __init__(self, image):
        if image is None:
            return
        elif isinstance(image, basestring):
            # in case of string we think it's a path - try opening it!
            if os.path.exists(image) == False:
                return

            if os.path.splitext(image)[1].lower() == ".png":
                image = cairo.ImageSurface.create_from_png(image)
            else:
                image = gdk.pixbuf_new_from_file(image)

        self.image_data, self.width, self.height = image, image.get_width(), image.get_height()

    def render(self, graphics, width = None, height = None, x_offset = 0, y_offset = 0):
        graphics.save_context( )
        graphics.translate( x_offset, y_offset )
        graphics.rectangle( 0, 0, width or self.width, height or self.height)
        graphics.clip()
        graphics.set_source_surface(self.image_data)
        graphics.paint()
        graphics.restore_context()


class Slice9(object):
    def __init__(self, image, left=0, right=0, top=0, bottom=0,
                 stretch_w = True, stretch_h = True):

        if isinstance(image, basestring):
            image = get_image(image)
        else:
            image = Image(image)

        self.width, self.height = image.width, image.height

        self.left, self.right = left, right
        self.top, self.bottom = top, bottom
        self.slices = []
        def get_slice(x, y, w, h):
            # we are grabbing bigger area and when painting will crop out to
            # just the actual needed pixels. This is done because otherwise when
            # stretching border, it uses white pixels to blend in
            x, y = x - 1, y - 1
            img = cairo.ImageSurface(cairo.FORMAT_ARGB32, w+2, h+2)
            ctx = cairo.Context(img)

            if isinstance(image.image_data, GdkPixbuf.Pixbuf):
                ctx.set_source_pixbuf(image.image_data, -x, -y)
            else:
                ctx.set_source_surface(image.image_data, -x, -y)

            ctx.rectangle(0, 0, w+2, h+2)
            ctx.clip()
            ctx.paint()
            return img, w, h

        # run left-right, top-down and slice image into 9 pieces
        exes = (0, left, image.width - right, image.width)
        ys = (0, top, image.height - bottom, image.height)
        for y1, y2 in zip(ys, ys[1:]):
            for x1, x2 in zip(exes, exes[1:]):
                self.slices.append(get_slice(x1, y1, x2 - x1, y2 - y1))

        self.stretch_w, self.stretch_h = stretch_w, stretch_h
        self.stretch_filter_mode = cairo.FILTER_BEST


    def render(self, graphics, width, height, x_offset=0, y_offset=0):
        """renders the image in the given graphics context with the told width
        and height"""
        def put_pattern(image, x, y, w, h):
            if w <= 0 or h <= 0:
                return

            graphics.save_context()


            if not self.stretch_w or not self.stretch_h:
                # if we repeat then we have to cut off the top-left margin
                # that we put in there so that stretching does not borrow white
                # pixels
                img = cairo.ImageSurface(cairo.FORMAT_ARGB32, image[1], image[2])
                ctx = cairo.Context(img)
                ctx.set_source_surface(image[0],
                                       0 if self.stretch_w else -1,
                                       0 if self.stretch_h else -1)
                ctx.rectangle(0, 0, image[1], image[2])
                ctx.clip()
                ctx.paint()
            else:
                img = image[0]

            pattern = cairo.SurfacePattern(img)
            pattern.set_extend(cairo.EXTEND_REPEAT)
            pattern.set_matrix(cairo.Matrix(x0 = 1 if self.stretch_w else 0,
                                            y0 = 1 if self.stretch_h else 0,
                                            xx = (image[1]) / float(w) if self.stretch_w else 1,
                                            yy = (image[2]) / float(h) if self.stretch_h else 1))
            pattern.set_filter(self.stretch_filter_mode)

            # truncating as fill on half pixel will lead to nasty gaps
            graphics.translate(int(x + x_offset), int(y + y_offset))
            graphics.set_source(pattern)
            graphics.rectangle(0, 0, int(w), int(h))
            graphics.clip()
            graphics.paint()
            graphics.restore_context()


        graphics.save_context()

        left, right, = self.left, self.right
        top, bottom = self.top, self.bottom

        # top-left
        put_pattern(self.slices[0], 0, 0, left, top)

        # top center - repeat width
        put_pattern(self.slices[1], left, 0, width - left - right, top)

        # top-right
        put_pattern(self.slices[2], width - right, 0, right, top)

        # left - repeat height
        put_pattern(self.slices[3], 0, top, left, height - top - bottom)

        # center - repeat width and height
        put_pattern(self.slices[4], left, top, width - left - right, height - top - bottom)

        # right - repeat height
        put_pattern(self.slices[5], width - right, top, right, height - top - bottom)

        # bottom-left
        put_pattern(self.slices[6], 0, height - bottom, left, bottom)

        # bottom center - repeat width
        put_pattern(self.slices[7], left, height - bottom, width - left - right, bottom)

        # bottom-right
        put_pattern(self.slices[8], width - right, height - bottom, right, bottom)

        graphics.rectangle(x_offset, y_offset, width, height)
        graphics.new_path()

        graphics.restore_context()




class SpriteSheetImage(graphics.Sprite):
    def __init__(self, sheet, offset_x, offset_y, width, height, **kwargs):
        graphics.Sprite.__init__(self, **kwargs)

        #: Image or BitmapSprite object that has the graphics on it
        self.sheet = sheet

        self.offset_x = offset_x
        self.offset_y = offset_y
        self.width = width
        self.height = height

    def _draw(self, context, opacity = 1, parent_matrix = None):
        if not getattr(self.sheet, "cache_surface", None):
            # create cache surface similar to context and paint the image if not there
            # the cache surface is/was essential to performance
            # this somewhat upside down as ideally one might want to have a "cache surface instruction"
            surface = context.get_target().create_similar(self.sheet.cache_mode,
                                                          self.sheet.width,
                                                          self.sheet.height)
            local_context = cairo.Context(surface)
            if isinstance(self.sheet.image_data, GdkPixbuf.Pixbuf):
                local_context.set_source_pixbuf(self.sheet.image_data, 0, 0)
            else:
                local_context.set_source_surface(self.sheet.image_data)
            local_context.paint()
            self.sheet.cache_surface = surface


        # add instructions with the resulting surface
        if self._sprite_dirty:
            self.graphics.save_context()
            self.graphics.set_source_surface(self.sheet.cache_surface, -self.offset_x, -self.offset_y)
            self.graphics.rectangle(0, 0, self.width, self.height)
            self.graphics.clip()
            self.graphics.paint()
            self.graphics.restore_context()

        graphics.Sprite._draw(self,  context, opacity, parent_matrix)

########NEW FILE########
__FILENAME__ = truchet
#!/usr/bin/env python
# - coding: utf-8 -
# Copyright (C) 2010 Toms Bauģis <toms.baugis at gmail.com>
"""
    Truchet pasta tiling (http://mathworld.wolfram.com/TruchetTiling.html)
    Most entertaining.
    Basically there are two types of tiles - "/" and "\" and we just randomly
    generate the whole thing
"""

from gi.repository import Gtk as gtk
from lib import graphics
import math
import random

class Tile(graphics.Sprite):
    def __init__(self, x, y, size, orient):
        graphics.Sprite.__init__(self, x, y, interactive = False)

        if orient % 2 == 0: # tiles 2 and 4 are flipped 1 and 3
            self.rotation = math.pi / 2
            self.x = self.x + size

        arc_radius = size / 2
        front, back = "#999", "#ccc"
        if orient > 2:
            front, back = back, front

        self.graphics.fill_area(0, 0, size, size, back)
        self.graphics.set_color(front)

        self.graphics.move_to(0, 0)
        self.graphics.line_to(arc_radius, 0)
        self.graphics.arc(0, 0, arc_radius, 0, math.pi / 2);
        self.graphics.close_path()

        self.graphics.move_to(size, size)
        self.graphics.line_to(size - arc_radius, size)
        self.graphics.arc(size, size, arc_radius, math.pi, math.pi + math.pi / 2);
        self.graphics.close_path()
        self.graphics.fill()


class Scene(graphics.Scene):
    def __init__(self):
        graphics.Scene.__init__(self)
        self.tile_size = 40
        self.connect("on-mouse-move", self.on_mouse_move)
        self.connect("on-enter-frame", self.on_enter_frame)

    def checker_fill(self):
        """fill area with 4-type matching tiles, where the other two have same
           shapes as first two, but colors are inverted"""
        self.clear()

        for y in range(0, self.height / self.tile_size + 1):
            for x in range(0, self.width / self.tile_size + 1):
                if (x + y) % 2:
                    tile = random.choice([1, 4])
                else:
                    tile = random.choice([2, 3])

                self.add_child(Tile(x * self.tile_size, y * self.tile_size, self.tile_size, tile))

    def on_mouse_move(self, area, event):
        self.tile_size = int(event.x / float(self.width) * 200 + 5) # x changes size of tile from 20 to 200(+20)
        self.tile_size = min([max(self.tile_size, 10), self.width, self.height])
        self.redraw()

    def on_enter_frame(self, scene, context):
        self.checker_fill()





class BasicWindow:
    def __init__(self):
        window = gtk.Window()
        window.set_size_request(500, 500)
        window.connect("delete_event", lambda *args: gtk.main_quit())
        window.add(Scene())
        window.show_all()


if __name__ == "__main__":
    example = BasicWindow()
    import signal
    signal.signal(signal.SIGINT, signal.SIG_DFL) # gtk3 screws up ctrl+c
    gtk.main()

########NEW FILE########
__FILENAME__ = truchet_saver
#!/usr/bin/env python
# - coding: utf-8 -
# Copyright (C) 2010 Toms Bauģis <toms.baugis at gmail.com>
"""
    Truchet pasta tiling (http://mathworld.wolfram.com/TruchetTiling.html)
    Most entertaining.
    Basically there are two types of tiles - "/" and "\" and we just randomly
    generate the whole thing
"""

import gtk
from lib import graphics
import math
import random
from lib.pytweener import Easing

class Scene(graphics.Scene):
    def __init__(self):
        graphics.Scene.__init__(self)
        self.tile_size = 40
        self.tile_map = {}
        self.x, self.y = 0, 0
        self.dx, self.dy = -1, -1
        #self.framerate = 40
        self.pattern = []
        self.pattern_tiles = 2
        self.connect("configure-event", self.on_window_reconfigure)
        self.connect("on-enter-frame", self.on_enter_frame)

    def on_window_reconfigure(self, area, stuff):
        self.tile_map = {}

    def on_enter_frame(self, scene, context):
        tile_size = int(self.tile_size)
        pattern_tiles = self.pattern_tiles
        #we move, and then we change the tile
        if not self.pattern:
            self.generate_tile_map(pattern_tiles, pattern_tiles)

        pattern_size = tile_size * pattern_tiles

        # draw the tile that we will clone
        for y, row in enumerate(self.pattern):
            for x, col in enumerate(self.pattern[y]):
                self.fill_tile(context, x * tile_size, y * tile_size, tile_size, self.pattern[y][x])

        # now get our pixmap
        tile_image = self.window.get_image(0, 0, min(pattern_size, self.width), min(pattern_size, self.height))

        for y in range(-pattern_size - int(abs(self.y)), self.height + pattern_size + int(abs(self.y)), pattern_size):
            for x in range(-pattern_size - int(abs(self.x)), self.width+pattern_size + int(abs(self.y)), pattern_size):
                self.window.draw_image(self.get_style().black_gc, tile_image, 0, 0, int(x + self.x), int(y + self.y), -1, -1)

        self.x += self.dx
        self.y -= self.dy

        if self.x > pattern_size or self.x < -pattern_size or \
           self.y > pattern_size or self.y < -pattern_size:
            self.randomize()

        self.redraw()

    def randomize(self):
        self.x = 0
        self.y = 0

        def switch_tiles(sprite):
            self.pattern = None
            self.pattern_tiles = random.randint(1, 5) * 2

        new_dx = (random.random() * 0.8 + 0.1) * random.choice([-1,1])
        new_dy = (random.random() * 0.8 + 0.1) * random.choice([-1,1])
        #new_tile_size = random.randint(4, min([self.width / self.pattern_tiles, self.height / self.pattern_tiles]))

        self.tweener.add_tween(self,
                              easing = Easing.Expo.ease_in_out,
                              duration = 1,
                              dx = new_dx,
                              dy = new_dy,
                              on_complete = switch_tiles)


    def generate_tile_map(self, horizontal, vertical):
        """generate a 2x2 square and then see tile it"""
        pattern = []
        for y in range(vertical):
            pattern.append([])
            for x in range(horizontal):
                if (x + y) % 2:
                    tile = random.choice([1, 4])
                else:
                    tile = random.choice([2, 3])

                pattern[y].append(tile)

        self.pattern = pattern


    def fill_tile(self, context, x, y, size, orient):
        # draws a tile, there are just two orientations
        arc_radius = size / 2

        front, back = "#666", "#aaa"
        if orient > 2:
            front, back = back, front

        context.set_source_rgb(*self.colors.parse(back))
        context.rectangle(x, y, size, size)
        context.fill()

        context.set_source_rgb(*self.colors.parse(front))


        context.save()
        context.translate(x, y)
        if orient % 2 == 0: # tiles 2 and 4 are flipped 1 and 3
            context.rotate(math.pi / 2)
            context.translate(0, -size)

        context.move_to(0, 0)
        context.line_to(arc_radius, 0)
        context.arc(0, 0, arc_radius, 0, math.pi / 2);
        context.close_path()

        context.move_to(size, size)
        context.line_to(size - arc_radius, size)
        context.arc(size, size, arc_radius, math.pi, math.pi + math.pi / 2);
        context.close_path()

        context.fill()
        context.restore()



class BasicWindow:
    def __init__(self):
        window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        window.set_size_request(500, 500)
        window.connect("delete_event", lambda *args: gtk.main_quit())

        window.add(Scene())
        window.show_all()


if __name__ == "__main__":
    example = BasicWindow()
    gtk.main()

########NEW FILE########
__FILENAME__ = tween_chain
#!/usr/bin/env python
# - coding: utf-8 -
# Copyright (C) 2010 Toms Bauģis <toms.baugis at gmail.com>

# This is intentionally slow to test how well the lib behaves on many sprites
# moving.
# It could be easily (and totally appropriately) improved by doing all the
# drawing in on_enter_frame and forgetting about sprites.

import colorsys

from gi.repository import Gtk as gtk
from lib import graphics
from lib.pytweener import Easing
from math import floor


class TailParticle(graphics.Sprite):
    def __init__(self, x, y, color, follow = None):
        graphics.Sprite.__init__(self, x = x, y = y)
        self.follow = follow
        self.color = color
        self.add_child(graphics.Rectangle(20, 20, 3, color, x=-10, y=-10))
        self.graphics.fill(color)


class Scene(graphics.Scene):
    def __init__(self):
        graphics.Scene.__init__(self)

        self.tail = []
        parts = 30
        for i in range(parts):
            previous = self.tail[-1] if self.tail else None
            color = colorsys.hls_to_rgb(0.6, i / float(parts), 1)

            self.tail.append(TailParticle(10, 10, color, previous))

        for tail in reversed(self.tail):
            self.add_child(tail) # add them to scene other way round


        self.mouse_moving = False

        self.connect("on-mouse-move", self.on_mouse_move)
        self.connect("on-enter-frame", self.on_enter_frame)


    def on_mouse_move(self, area, event):
        self.redraw()


    def on_enter_frame(self, scene, context):
        g = graphics.Graphics(context)
        for particle in reversed(self.tail):
            if particle.follow:
                new_x, new_y = particle.follow.x, particle.follow.y
                g.move_to(particle.x, particle.y)
                g.line_to(particle.follow.x, particle.follow.y)
                g.stroke(particle.color)
            else:
                new_x, new_y = self.mouse_x, self.mouse_y


            if abs(particle.x - new_x) + abs(particle.y - new_y) > 0.01:
                self.animate(particle, x = new_x, y = new_y, duration = 0.3, easing = Easing.Cubic.ease_out)


        if abs(self.tail[0].x - self.tail[-1].x) + abs(self.tail[0].y - self.tail[-1].y) > 1:
            self.redraw() # redraw if the tail is not on the head


class BasicWindow:
    def __init__(self):
        window = gtk.Window()
        window.set_default_size(500, 300)
        window.connect("delete_event", lambda *args: gtk.main_quit())

        scene = Scene()
        window.add(scene)
        window.show_all()


if __name__ == "__main__":
    example = BasicWindow()
    import signal
    signal.signal(signal.SIGINT, signal.SIG_DFL) # gtk3 screws up ctrl+c
    gtk.main()

########NEW FILE########
__FILENAME__ = accordion
# - coding: utf-8 -

# Copyright (c) 2011-2012 Media Modifications, Ltd.
# Dual licensed under the MIT or GPL Version 2 licenses.

from gi.repository import Gtk as gtk
from gi.repository import Gdk as gdk
from gi.repository import GObject as gobject

from ui import VBox, Button, ScrollArea

from lib.pytweener import Easing

class Accordion(VBox):
    """another way to hide content"""

    def __init__(self, pages = [], spacing = 0, animation_duration = None,
                 easing_function = Easing.Quad.ease_out, **kwargs):
        VBox.__init__(self, spacing=spacing, **kwargs)

        #: currently selected page
        self.current_page = None

        self.reclick_to_close = True

        #: duration of the sliding animation. Defaults to scene's settings.
        #: Set 0 to disable
        self.animation_duration = animation_duration

        #: Tweening method to use for the animation
        self.easing_function = easing_function

        if pages:
            self.add_child(*pages)

    def add_child(self, *pages):
        VBox.add_child(self, *pages)

        for page in pages:
            self.connect_child(page, "on-caption-mouse-down", self.on_caption_mouse_down)


    def on_caption_mouse_down(self, new_page):
        if self.reclick_to_close and new_page == self.current_page:
            new_page = None
        self.select_page(new_page)

    def select_page(self, new_page):
        """show chosen page"""
        if isinstance(new_page, int):
            new_page = self.sprites[new_page]

        if new_page == self.current_page:
            return

        # calculate available space
        taken_by_captions = 0
        for page in self.sprites:
            taken_by_captions += page._caption.height + self.spacing

        if self.current_page:
            taken_by_captions += self.current_page.spacing # this counts too!

        available = self.height - taken_by_captions - self.vertical_padding

        def round_size(container):
            container.min_height = int(container.min_height)

        def hide_container(container):
            container.visible = False

        if self.current_page:
            self.current_page.container.height = available
            self.current_page.container.opacity = 1
            self.current_page.container.scroll_vertical = False
            self.current_page.expand = False
            self.current_page.container.animate(height = 1, opacity=0,
                                                easing = self.easing_function,
                                                duration = self.animation_duration,
                                                on_complete = hide_container,
                                                on_update=round_size)


        def expand_page(container):
            container.parent.expand = True
            container.min_height = None
            container.scroll_vertical = "auto"

        if new_page is not None:
            new_page.container.height = 1
            new_page.container.opacity = 0
            new_page.container.visible = True
            new_page.container.animate(height = available, opacity=1,
                                       easing = self.easing_function,
                                       duration = self.animation_duration,
                                       on_complete = expand_page,
                                       on_update=round_size)


        self.current_page = new_page


        for page in self.sprites:
            page.expanded = page == new_page


class AccordionPageTitle(Button):
    def __init__(self, label="", pressed_offset = 0, expanded = False, **kwargs):
        Button.__init__(self, label=label, pressed_offset = pressed_offset, **kwargs)
        self.expanded = expanded

    def do_render(self):
        state = self.state

        if self.expanded:
            state = "current"

        colors = {
            'normal': ("#eee", "#999"),
            'highlight': ("#fff", "#999"),
            'current': ("#fafafa", "#aaa"),
        }

        color = colors.get(state, colors['normal'])

        self.graphics.set_line_style(1)

        self.graphics.fill_area(0, 0, self.width, self.height, color[0])

        self.graphics.move_to(0, self.height - 0.5)
        self.graphics.line_to(self.width,self.height -  0.5)
        self.graphics.stroke(color[1])


class AccordionPage(VBox):
    __gsignals__ = {
        "on-caption-mouse-down": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, ()),
    }

    caption_class = AccordionPageTitle

    def __init__(self, label = "", contents = [], expand = False, spacing = 0, expanded = False, **kwargs):
        VBox.__init__(self, expand=expand, spacing=spacing, **kwargs)
        self.expanded = expanded
        self._caption = self.caption_class(label, x_align=0, expanded = self.expanded, expand=False)
        self.connect_child(self._caption, "on-click", self.on_caption_mouse_down)

        self.container = ScrollArea(scroll_vertical=False, scroll_horizontal=False, visible=False, border=0)
        self.add_child(self._caption, self.container)
        self.add_child(*contents)

    def add_child(self, *sprites):
        for sprite in sprites:
            if sprite in (self._caption, self.container):
                VBox.add_child(self, sprite)
            else:
                self.container.add_child(sprite)

    def __setattr__(self, name, val):
        if name in ("label", "markup") and hasattr(self, "_caption"):
            setattr(self._caption, name, val)
        else:
            VBox.__setattr__(self, name, val)
            if name == "expanded" and hasattr(self, "_caption"):
                self._caption.expanded = val

    def on_caption_mouse_down(self, sprite, event):
        self.emit("on-caption-mouse-down")

########NEW FILE########
__FILENAME__ = buttons
# - coding: utf-8 -

# Copyright (c) 2011-2012 Media Modifications, Ltd.
# Dual licensed under the MIT or GPL Version 2 licenses.

from gi.repository import Gtk as gtk
from gi.repository import Gdk as gdk
from gi.repository import GObject as gobject

from lib import graphics
from ui.containers import Widget, Container, Bin, Table, Box, HBox, VBox, Fixed, Viewport, Group
from ui.widgets import Label
import math

class Button(Label):
    """A simple button"""
    __gsignals__ = {
        "on-state-change": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
    }
    fill = True
    padding = (6, 8)
    x_align = 0.5

    def __init__(self, label = "", bevel = True, repeat_down_delay = 0, pressed_offset = 1,**kwargs):
        Label.__init__(self, **kwargs)
        self.interactive, self.can_focus = True, True

        #: current state
        self.state = "normal"

        #: label
        self.label = label

        #: if set, will repeat the on-mouse-down signal every specified miliseconds while the button is pressed
        #: when setting: 100 is a good initial value
        self.repeat_down_delay = repeat_down_delay

        #: draw border
        self.bevel = bevel

        #: by how many pixels should the label move towards bottom right when pressed
        #: defaults to 1
        self.pressed_offset = pressed_offset


        #: a rather curious figure telling how many times the button has been
        #: pressed since gaining focus. resets on losing the focus
        self.times_clicked = 0

        self.colors = {
            # fill, fill, stroke, outer stroke
            "normal": ("#fcfcfc", "#efefef", "#dedcda", "#918e8c"),
            "highlight": ("#fff", "#f4f3f2", "#dedcda", "#918e8c"),
            "pressed": ("#cfd1d3", "#b9bbc0", "#e0dedd", "#5b7aa1"),
            "focused": ("#fcfcfc", "#efefef", "#52749e", "#89adda")
        }

        self.connect("on-mouse-over", self.__on_mouse_over)
        self.connect("on-mouse-out", self.__on_mouse_out)
        self.connect("on-mouse-down", self.__on_mouse_down)
        self.connect("on-render", self.__on_render)

        self._pressed = False
        self._scene_mouse_up = None

        self._timeout = None


    def __setattr__(self, name, val):
        if name == "label":
            name = "text"
        Label.__setattr__(self, name, val)

        if name == "focused" and val == False:
            self.times_clicked = 0

    @property
    def label(self):
        return self.text



    def __on_render(self, sprite):
        """we want the button to be clickable"""
        self.graphics.rectangle(0, 0, self.width, self.height)
        self.graphics.new_path()


    def __on_mouse_over(self, button):
        if self._pressed:
            self._set_state("pressed")
            if self.repeat_down_delay > 0:
                self._repeat_mouse_down()
        else:
            cursor, mouse_x, mouse_y, mods = button.get_scene().get_window().get_pointer()
            if gdk.ModifierType.BUTTON1_MASK & mods:
                if self._scene_mouse_up: # having scene_mouse_up means the mouse-down came from us
                    self._set_state("pressed")
            else:
                self._set_state("highlight")

    def __on_mouse_out(self, sprite):
        self.__cancel_timeout()
        self._set_state("normal")

    def __cancel_timeout(self):
        if self._timeout:
            gobject.source_remove(self._timeout)
            self._timeout = None


    def __on_mouse_down(self, sprite, event):
        self._set_state("pressed")
        if not self._scene_mouse_up:
            self._scene_mouse_up = self.get_scene().connect("on-mouse-up", self._on_scene_mouse_up)

        if event and self.repeat_down_delay > 0 and self._timeout is None:
            self._repeat_mouse_down()

    def _repeat_mouse_down(self):
        # responsible for repeating mouse-down every repeat_down_delay miliseconds
        def repeat_mouse_down():
            self._do_mouse_down(None)
            return True

        if not self._timeout:
            self._timeout = gobject.timeout_add(self.repeat_down_delay, repeat_mouse_down)


    def _on_scene_mouse_up(self, sprite, event):
        self.__cancel_timeout()

        if self.check_hit(event.x, event.y):
            self._set_state("highlight")
        else:
            self._set_state("normal")

        self._pressed = False
        if self._scene_mouse_up:
            self.get_scene().disconnect(self._scene_mouse_up)
            self._scene_mouse_up = None

    def _set_state(self, state):
        if state != self.state:
            if state == "pressed" or self.state == "pressed":
                offset = self.pressed_offset if state == "pressed" else 0
                self.container.padding_left = self.container.padding_top = offset
                self.container.padding_right = self.container.padding_bottom = -offset

            if state == "pressed":
                self.times_clicked += 1


            self.state = state
            self.emit("on-state-change", self.state)

    def do_render(self, colors = None):
        self.graphics.set_line_style(width = 1)
        width, height = self.width, self.height

        x, y, x2, y2 = 0.5, 0.5, width - 1, height - 1
        corner_radius = 4

        state = self.state



        colors = colors or self.colors[self.state]

        if self.focused:
            colors = colors[:2] + self.colors["focused"][2:]


        # upper half of the highlight
        self.graphics.fill_area(x, y, x2, y2 / 2.0, colors[0])

        # lower_half
        self.graphics.fill_area(x, y2 / 2.0, x2, y2 / 2.0, colors[1])


        if self.bevel:
            # outline
            self.graphics.rectangle(0, 0, width, height, corner_radius)
            self.graphics.stroke(colors[2])

            # main line
            self.graphics.rectangle(0.5, 0.5, width - 1, height - 1, corner_radius)
            self.graphics.stroke(colors[3])



class ToggleButton(Button):
    """A button that retains its state. If you pack toggle buttons in
       :class:`~ui.containers.Group` then toggle one button will untoggle all the others in
       that group.
    """
    __gsignals__ = {
        "on-toggle": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, ()),
    }
    def __init__(self, label = "", toggled = False, group = None, **kwargs):
        Button.__init__(self, label = label, **kwargs)

        #: whether the button currently is toggled or not
        self.toggled = toggled

        self.group = group

        self.connect("on-click", self.on_click)
        self.connect("on-key-press", self.on_key_press)


    def __setattr__(self, name, val):
        if val == self.__dict__.get(name, "hamster_graphics_no_value_really"):
            return

        if name == 'group':
            # add ourselves to group
            prev_group = getattr(self, 'group', None)
            if prev_group:
                prev_group._remove_item(self)
            if val:
                val._add_item(self)

        Button.__setattr__(self, name, val)


    def on_click(self, sprite, event):
        self.toggle()

    def on_key_press(self, sprite, event):
        if event.keyval == gdk.KEY_Return or event.keyval == gdk.KEY_space:
            self.toggle()

    def toggle(self):
        """toggle button state"""
        self.toggled = not self.toggled
        self.emit("on-toggle")


    def do_render(self):
        state = self.state
        if self.toggled:
            state = "pressed"

        colors = self.colors[state]

        if self.focused:
            colors = self.colors[state][:2] + self.colors["focused"][2:]


        if isinstance(self.parent, Group) == False or len(self.parent.sprites) == 1:
            # normal button
            Button.do_render(self, colors)
        else:
            # otherwise check how many are there, am i the first etc.
            width, height = self.width, self.height

            x, y, x2, y2 = 0.5, 0.5, 0.5 + width, 0.5 + height
            corner_radius = 4


            # bit of sphagetti code - will clean up later with gradients and such
            # TODO - add gradients to graphics
            if self.parent.sprites.index(self) == 0:
                # upper half of the highlight
                self._rounded_line([(x2, y), (x, y), (x, y2 / 2.0)], corner_radius)
                self.graphics.line_to([(x2, y2 / 2.0), (x2, y)])
                self.graphics.fill(colors[0])

                # lower half
                self._rounded_line([(x, y2 / 2.0), (x, y2), (x2, y2)], corner_radius)
                self.graphics.line_to([(x2, y2 / 2.0), (x, y2 / 2.0)])
                self.graphics.fill(colors[1])

                # outline
                self._rounded_line([(x2+0.5, 0), (0, 0), (0, y2+0.5), (x2+0.5, y2+0.5)], corner_radius)
                self.graphics.line_to(x2+0.5, 0)
                self.graphics.stroke(colors[2])


                # main line
                self._rounded_line([(x2, y), (x, y), (x, y2), (x2, y2)], corner_radius)
                self.graphics.line_to(x2, y)
                self.graphics.stroke(colors[3])

            elif self.parent.sprites.index(self) == len(self.parent.sprites) - 1:
                # upper half of the highlight
                self._rounded_line([(x, y), (x2, y), (x2, y2 / 2.0)], corner_radius)
                self.graphics.line_to([(x, y2 / 2.0), (x, y)])
                self.graphics.fill(colors[0])

                # lower half
                self._rounded_line([(x2, y2 / 2.0), (x2, y2), (x, y2)], corner_radius)
                self.graphics.line_to([(x, y2 / 2.0), (x2, y2 / 2.0)])
                self.graphics.fill(colors[1])

                # outline
                self._rounded_line([(0, 0), (x2 + 0.5, 0), (x2 + 0.5, y2+0.5), (0, y2+0.5)], corner_radius)
                self.graphics.line_to(0, 0)
                self.graphics.stroke(colors[2])


                # main line
                self._rounded_line([(x, y), (x2, y), (x2, y2), (x, y2)], corner_radius)
                self.graphics.line_to(x, y)
                self.graphics.stroke(colors[3])

            else:
                # upper half of the highlight
                self.graphics.fill_area(x, y, x2, y2 / 2.0, colors[0])

                # lower half of the highlight
                self.graphics.fill_area(x, y2 / 2.0, x2, y2 / 2.0, colors[1])

                # outline
                self.graphics.rectangle(0, 0, x2 + 0.5, y2 + 0.5)
                self.graphics.stroke(colors[2])

                # outline
                self._rounded_line([(x2+0.5, 0), (0, 0), (0, y2+0.5), (x2+0.5, y2+0.5)], corner_radius)
                self.graphics.line_to(x2+0.5, 0)
                self.graphics.stroke(colors[2])

                # main line
                self.graphics.rectangle(x, y, x2 - 0.5, y2 - 0.5)
                self.graphics.stroke(colors[3])



class RadioMark(Widget):
    def __init__(self, state="normal", toggled=False, **kwargs):
        Widget.__init__(self, **kwargs)
        self.state = state
        self.toggled = toggled

    def do_render(self):
        """tickmark rendering function. override to render your own visuals"""
        size = self.min_height

        fill, stroke = "#fff", "#444"
        if self.state == "highlight":
            fill, stroke = "#ECF2F4", "#6A7D96"
        elif self.state == "pressed":
            fill, stroke = "#BDCDE2", "#6A7D96"

        self.graphics.set_line_style(width=1)
        self.graphics.ellipse(0, 0, size, size)
        self.graphics.fill_stroke(fill, stroke)

        if self.toggled:
            self.graphics.ellipse(2, 2, size - 4, size - 4)
            self.graphics.fill("#444")

class RadioButton(ToggleButton):
    """A choice of one of multiple check buttons. Pack radiobuttons in
       :class:`ui.containers.Group`.
    """
    #: class that renders the checkmark
    Mark = RadioMark

    padding = 0

    def __init__(self, label = "", pressed_offset = 0, spacing = 10, **kwargs):
        ToggleButton.__init__(self, label = label, pressed_offset = pressed_offset,
                              spacing=spacing, **kwargs)

        #: visual tick mark. it replaces the label's image
        self.tick_mark = self.Mark(state=self.state, toggled=self.toggled, width=11, height=11, fill=False)

        self.image = self.tick_mark
        self.container.x_align = 0

    def __setattr__(self, name, val):
        ToggleButton.__setattr__(self, name, val)
        if name in ("state", "toggled") and hasattr(self, "tick_mark"):
            setattr(self.tick_mark, name, val)

    def do_render(self):
        self.graphics.rectangle(0, 0, self.width, self.height)
        self.graphics.new_path()



class CheckMark(RadioMark):
    def do_render(self):
        size = self.min_height

        fill, stroke = "#fff", "#999"
        if self.state in ("highlight", "pressed"):
            fill, stroke = "#BDCDE2", "#6A7D96"

        self.graphics.set_line_style(1)
        self.graphics.rectangle(0.5, 0.5, size, size)
        self.graphics.fill_stroke(fill, stroke)

        if self.toggled:
            self.graphics.set_line_style(2)
            self.graphics.move_to(2, size * 0.5)
            self.graphics.line_to(size * 0.4, size - 3)
            self.graphics.line_to(size - 2, 2)
            self.graphics.stroke("#000")

class CheckButton(RadioButton):
    """a toggle button widget styled as a checkbox and label"""
    Mark = CheckMark




class ScrollButton(Button):
    """a button well suited for scrollbars and other scrollies"""
    def __init__(self, direction = "up", repeat_down_delay=50, **kwargs):
        Button.__init__(self, repeat_down_delay = repeat_down_delay, **kwargs)

        #: which way is the arrow looking. one of "up", "down", "left", "right"
        self.direction = direction


    def do_render(self):
        w, h = self.width, self.height
        size = min(self.width, self.height) - 1
        self.graphics.rectangle(int((w - size) / 2) + 0.5, int((h - size) / 2) + 0.5, size, size, 2)

        if self.enabled == False:
            colors = "#fff", "#ccc"
        else:
            colors = "#fff", "#a8aca8"

        self.graphics.fill_stroke(*colors)


        self.graphics.save_context()
        arrow_size = 6
        self.graphics.translate(w / 2.0, h / 2.0 + 0.5)
        #self.graphics.fill_area(-1, -1, 2, 2, "#000")

        if self.direction == "left":
            self.graphics.rotate(math.pi)
        elif self.direction == "up":
            self.graphics.rotate(-math.pi / 2)
        elif self.direction == "down":
            self.graphics.rotate(math.pi / 2)

        self.graphics.move_to(-1, -3)
        self.graphics.line_to(2, 0)
        self.graphics.line_to(-1, 3)


        if self.enabled == False:
            color = "#ccc"
        else:
            color = "#444"
        self.graphics.stroke(color)

        self.graphics.restore_context()

########NEW FILE########
__FILENAME__ = combobox
# - coding: utf-8 -

# Copyright (c) 2011-2012 Media Modifications, Ltd.
# Dual licensed under the MIT or GPL Version 2 licenses.

from gi.repository import Gtk as gtk
from gi.repository import Gdk as gdk
from gi.repository import GObject as gobject
from gi.repository import Pango as pango

from lib import graphics

from ui import ScrollArea, ListView, ToggleButton

class ComboBox(ToggleButton):
    """a button with a drop down menu.

    **Signals**:

    **on-change** *(sprite, new_val)*
    - fired after selecting a new value.
    """
    __gsignals__ = {
        "on-change": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
    }

    #: how much space will the dropmark occupy
    drop_mark_width = 20

    #: maximum height of the dropdown
    dropdown_height = 200

    x_align = 0

    #: class to use for the dropdown
    DropdownClass = ListView

    def __init__(self, rows = [], dropdown_height=None, open_below = True,
                 overflow = pango.EllipsizeMode.END, **kwargs):
        ToggleButton.__init__(self, overflow = overflow, **kwargs)

        if dropdown_height:
            self.dropdown_height = dropdown_height

        self.padding_right = self.drop_mark_width
        self._scene_mouse_down = None # scene mouse down listener to hide our window if clicked anywhere else
        self._echo = False

        self.listitem = self.DropdownClass(select_on_drag = True)
        self.connect_child(self.listitem, "on-mouse-move", self._on_listitem_mouse_move)
        self.connect_child(self.listitem, "on-mouse-up", self._on_listitem_mouse_up)
        self.connect_child(self.listitem, "on-select", self._on_listitem_select)

        #: the list of text strings available for selection
        self.rows = rows

        #: Whether the dropdown should appear below or over the input element
        self.open_below = open_below

        if rows:
            self._set_label(self.label or rows[0])

        self.scrollbox = ScrollArea(fill=False)
        self.scrollbox.add_child(self.listitem)

        self.connect("on-mouse-move", self.__on_mouse_move)
        self.connect("on-mouse-down", self.__on_mouse_down)
        self.connect("on-click", self.__on_click)
        self.connect("on-toggle", self._on_toggle)
        self.connect("on-key-press", self._on_key_press)

        self._echo_up = False

    def __setattr__(self, name, val):
        if name == "label":
            self._set_label(val)
            return

        if name == "rows":
            self.listitem.rows = val
            if val and hasattr(self, "label"):
                if self.label in val:
                    self.listitem.select(self.listitem.rows[self.listitem.find(self.label)])
                else:
                    self._set_label(val[0])

            # make sure we get pointer to the listitems treemodel
            ToggleButton.__setattr__(self, name, self.listitem.rows)
            return

        ToggleButton.__setattr__(self, name, val)
        if name == "drop_mark_width":
            self.padding_right = val

    def _set_label(self, item):
        if isinstance(item, (dict)):
            label = item.get("text", pango.parse_markup(item.get("markup", ""), -1, "0")[2])
        else:
            label = item

        if label == self.label:
            return #have it already!

        idx = self.listitem.find(label)

        if idx != -1:
            ToggleButton.__setattr__(self, 'label', label)

            # mark current row
            if not self.listitem.current_row or self.listitem.current_row[0] != self.label:
                self.listitem.select(self.listitem.rows[idx])

            self.emit("on-change", item)



    def _on_toggle(self, sprite):
        # our state strictly depends on whether the dropdown is visible or not
        self.toggled = self.scrollbox in self.get_scene().sprites

    def _on_key_press(self, sprite, event):
        if event.keyval == gdk.KEY_Return:
            self.toggle_display()

    def __on_mouse_down(self, sprite, event):
        self._echo = True
        if self.open_below is False:
            self._echo_up = True
        self.toggle_display()


    def resize_children(self):
        ToggleButton.resize_children(self)
        self.display_label.max_width = self.width - self.horizontal_padding


    def toggle_display(self):
        if self.scrollbox not in self.get_scene().sprites:
            self.listitem.select(self.label)
            self.show_dropdown()
            self.listitem.grab_focus()
        else:
            self.hide_dropdown()


    def __on_click(self, sprite, event):
        if self.toggled:
            self.listitem.grab_focus()


    def __on_scene_mouse_down(self, scene, event):
        if self._echo == False and (self.scrollbox.check_hit(event.x, event.y) == False and \
                                    self.check_hit(event.x, event.y) == False):
            self.hide_dropdown()
        self._echo = False


    def __on_scene_mouse_up(self, sprite, event):
        self._echo = False
        self._echo_up = False

    def __on_mouse_move(self, sprite, event):
        self._echo_up = False
        self._echo = False

    def _on_listitem_mouse_up(self, sprite, event):
        if self._echo_up:
            self._echo_up = False
            return

        if self.listitem.current_row:
            self._set_label(self.listitem.current_row[0])
        self.toggle_display()

    def _on_listitem_mouse_move(self, sprite, event):
        self._echo_up = False

    def _on_listitem_select(self, sprite, event=None):
        if self.listitem.current_row:
            self._set_label(self.listitem.current_row[0])
        self.hide_dropdown()


    def show_dropdown(self):
        """show the dropdown"""
        if not self.rows:
            return
        scene = self.get_scene()
        self.__scene_mouse_down = scene.connect_after("on-mouse-down", self.__on_scene_mouse_down)
        self.__scene_mouse_up = scene.connect("on-mouse-up", self.__on_scene_mouse_up)

        scene.add_child(self.scrollbox)
        self.scrollbox.x, self.scrollbox.y = self.to_scene_coords()

        self.scrollbox.width, self.scrollbox.height = self.width, min(self.listitem.height, self.dropdown_height)

        if self.open_below:
            self.scrollbox.y += self.height + 1
        else:
            if self.listitem.current_row:
                self.scrollbox.y -= self.listitem.get_row_position(self.listitem.current_row)


        if self.open_below:
            self.scrollbox.y = min(max(self.scrollbox.y, 0), scene.height - self.height - self.scrollbox.height - 1)
            self._echo_up = False
        else:
            self.scrollbox.y = min(max(self.scrollbox.y, 0), scene.height - self.scrollbox.height - 1)

        self.toggled = True


    def hide_dropdown(self):
        """hide the dropdown"""
        scene = self.get_scene()
        if self.__scene_mouse_down:
            scene.disconnect(self.__scene_mouse_down)
            scene.disconnect(self.__scene_mouse_up)
            self.__scene_mouse_down, self.__scene_mouse_up = None, None
        scene.remove_child(self.scrollbox)
        self.toggled = False
        self._echo_up = False
        self._echo = False

    def do_render(self):
        ToggleButton.do_render(self)
        w, h = self.drop_mark_width, self.height

        self.graphics.save_context()
        self.graphics.translate(self.width - self.drop_mark_width + 0.5, 0)

        self.graphics.move_to(0, 5)
        self.graphics.line_to(0, h - 5)
        self.graphics.stroke("#888")

        self.graphics.translate((w - 8) / 2.0, (h - 10) / 2.0 - 5)

        self.graphics.move_to(0, 8)
        self.graphics.line_to(3, 5)
        self.graphics.line_to(6, 8)

        self.graphics.move_to(0, 12)
        self.graphics.line_to(3, 15)
        self.graphics.line_to(6, 12)
        self.graphics.stroke("#666")

        self.graphics.restore_context()

########NEW FILE########
__FILENAME__ = containers
# - coding: utf-8 -

# Copyright (c) 2011-2012 Media Modifications, Ltd.
# Dual licensed under the MIT or GPL Version 2 licenses.

from gi.repository import Gtk as gtk
from gi.repository import Gdk as gdk
from gi.repository import GObject as gobject

import math
from collections import defaultdict

from lib import graphics
from ui import Widget


def get_min_size(sprite):
    if hasattr(sprite, "get_min_size"):
        min_width, min_height = sprite.get_min_size()
    else:
        min_width, min_height = getattr(sprite, "width", 0), getattr(sprite, "height", 0)

    min_width = min_width * sprite.scale_x
    min_height = min_height * sprite.scale_y

    return min_width, min_height

def get_props(sprite):
    # gets all the relevant info for containers and puts it in a uniform dict.
    # this way we can access any object without having to check types and such
    keys = ("margin_top", "margin_right", "margin_bottom", "margin_left",
            "padding_top", "padding_right", "padding_bottom", "padding_left")
    res = dict((key, getattr(sprite, key, 0)) for key in keys)
    res["expand"] = getattr(sprite, "expand", True)

    return sprite, res


class Container(Widget):
    """The base container class that all other containers inherit from.
       You can insert any sprite in the container, just make sure that it either
       has width and height defined so that the container can do alignment, or
       for more sophisticated cases, make sure it has get_min_size function that
       returns how much space is needed.

       Normally while performing layout the container will update child sprites
       and set their alloc_h and alloc_w properties. The `alloc` part is short
       for allocated. So use that when making rendering decisions.
    """
    cache_attrs = Widget.cache_attrs | set(('_cached_w', '_cached_h'))
    _sizing_attributes = Widget._sizing_attributes | set(('padding_top', 'padding_right', 'padding_bottom', 'padding_left'))

    def __init__(self, contents = None, **kwargs):
        Widget.__init__(self, **kwargs)

        #: contents of the container - either a widget or a list of widgets
        self.contents = contents
        self._cached_w, self._cached_h = None, None


    def __setattr__(self, name, val):
        if self.__dict__.get(name, "hamster_graphics_no_value_really") == val:
            return

        Widget.__setattr__(self, name, val)
        if name == 'contents':
            if val:
                if isinstance(val, graphics.Sprite):
                    val = [val]
                self.add_child(*val)
            if self.sprites and self.sprites != val:
                self.remove_child(*list(set(self.sprites) ^ set(val or [])))

        if name in ("alloc_w", "alloc_h") and val:
            self.__dict__['_cached_w'], self.__dict__['_cached_h'] = None, None
            self._children_resize_queued = True


    @property
    def contents(self):
        return self.sprites


    def _Widget__on_render(self, sprite):
        if self._children_resize_queued:
            self.resize_children()
            self.__dict__['_children_resize_queued'] = False
        Widget._Widget__on_render(self, sprite)


    def _add(self, *sprites):
        Widget._add(self, *sprites)
        self.queue_resize()

    def remove_child(self, *sprites):
        Widget.remove_child(self, *sprites)
        self.queue_resize()

    def queue_resize(self):
        self.__dict__['_cached_w'], self.__dict__['_cached_h'] = None, None
        Widget.queue_resize(self)

    def get_min_size(self):
        # by default max between our requested size and the biggest child
        if self.visible == False:
            return 0, 0

        if self._cached_w is None:
            sprites = [sprite for sprite in self.sprites if sprite.visible]
            width = max([get_min_size(sprite)[0] for sprite in sprites] or [0])
            width += self.horizontal_padding  + self.margin_left + self.margin_right

            height = max([get_min_size(sprite)[1] for sprite in sprites] or [0])
            height += self.vertical_padding + self.margin_top + self.margin_bottom

            self._cached_w, self._cached_h = max(width, self.min_width or 0), max(height, self.min_height or 0)

        return self._cached_w, self._cached_h

    def get_height_for_width_size(self):
        return self.get_min_size()


    def resize_children(self):
        """default container alignment is to pile stuff just up, respecting only
        padding, margin and element's alignment properties"""
        width = self.width - self.horizontal_padding
        height = self.height - self.vertical_padding

        for sprite, props in (get_props(sprite) for sprite in self.sprites if sprite.visible):
            sprite.alloc_w = width
            sprite.alloc_h = height

            w, h = getattr(sprite, "width", 0), getattr(sprite, "height", 0)
            if hasattr(sprite, "get_height_for_width_size"):
                w2, h2 = sprite.get_height_for_width_size()
                w, h = max(w, w2), max(h, h2)

            w = w * sprite.scale_x + props["margin_left"] + props["margin_right"]
            h = h * sprite.scale_y + props["margin_top"] + props["margin_bottom"]

            sprite.x = self.padding_left + props["margin_left"] + (max(sprite.alloc_w * sprite.scale_x, w) - w) * getattr(sprite, "x_align", 0)
            sprite.y = self.padding_top + props["margin_top"] + (max(sprite.alloc_h * sprite.scale_y, h) - h) * getattr(sprite, "y_align", 0)


        self.__dict__['_children_resize_queued'] = False

class Bin(Container):
    """A container with only one child. Adding new children will throw the
    previous ones out"""
    def __init__(self, contents = None, **kwargs):
        Container.__init__(self, contents, **kwargs)

    @property
    def child(self):
        """child sprite. shorthand for self.sprites[0]"""
        return self.sprites[0] if self.sprites else None

    def get_height_for_width_size(self):
        if self._children_resize_queued:
            self.resize_children()

        sprites = [sprite for sprite in self.sprites if sprite.visible]
        width, height = 0, 0
        for sprite in sprites:
            if hasattr(sprite, "get_height_for_width_size"):
                w, h = sprite.get_height_for_width_size()
            else:
                w, h = getattr(sprite, "width", 0), getattr(sprite, "height", 0)

            w, h = w * sprite.scale_x, h * sprite.scale_y

            width = max(width, w)
            height = max(height, h)

        #width = width + self.horizontal_padding + self.margin_left + self.margin_right
        #height = height + self.vertical_padding + self.margin_top + self.margin_bottom

        return width, height


    def add_child(self, *sprites):
        if not sprites:
            return

        sprite = sprites[-1] # there can be just one

        # performing add then remove to not screw up coordinates in
        # a strange reparenting case
        Container.add_child(self, sprite)
        if self.sprites and self.sprites[0] != sprite:
            self.remove_child(*list(set(self.sprites) ^ set([sprite])))



class Fixed(Container):
    """Basic container that does not care about child positions. Handy if
       you want to place stuff yourself or do animations.
    """
    def __init__(self, contents = None, **kwargs):
        Container.__init__(self, contents, **kwargs)

    def resize_children(self):
        # don't want
        pass



class Box(Container):
    """Align children either horizontally or vertically.
        Normally you would use :class:`HBox` or :class:`VBox` to be
        specific but this one is suited so you can change the packing direction
        dynamically.
    """
    #: spacing in pixels between children
    spacing = 5

    #: whether the box is packing children horizontally (from left to right) or vertically (from top to bottom)
    orient_horizontal = True

    def __init__(self, contents = None, horizontal = None, spacing = None, **kwargs):
        Container.__init__(self, contents, **kwargs)

        if horizontal is not None:
            self.orient_horizontal = horizontal

        if spacing is not None:
            self.spacing = spacing

    def get_total_spacing(self):
        # now lay them out
        padding_sprites = 0
        for sprite in self.sprites:
            if sprite.visible:
                if getattr(sprite, "expand", True):
                    padding_sprites += 1
                else:
                    if hasattr(sprite, "get_min_size"):
                        size = sprite.get_min_size()[0] if self.orient_horizontal else sprite.get_min_size()[1]
                    else:
                        size = getattr(sprite, "width", 0) * sprite.scale_x if self.orient_horizontal else getattr(sprite, "height", 0) * sprite.scale_y

                    if size > 0:
                        padding_sprites +=1
        return self.spacing * max(padding_sprites - 1, 0)


    def resize_children(self):
        if not self.parent:
            return

        width = self.width - self.padding_left - self.padding_right
        height = self.height - self.padding_top - self.padding_bottom

        sprites = [get_props(sprite) for sprite in self.sprites if sprite.visible]

        # calculate if we have any spare space
        sprite_sizes = []
        for sprite, props in sprites:
            if self.orient_horizontal:
                sprite.alloc_h = height / sprite.scale_y
                size = get_min_size(sprite)[0]
                size = size + props["margin_left"] + props["margin_right"]
            else:
                sprite.alloc_w = width / sprite.scale_x
                size = get_min_size(sprite)[1]
                if hasattr(sprite, "get_height_for_width_size"):
                    size = max(size, sprite.get_height_for_width_size()[1] * sprite.scale_y)
                size = size + props["margin_top"] + props["margin_bottom"]
            sprite_sizes.append(size)


        remaining_space = width if self.orient_horizontal else height
        if sprite_sizes:
            remaining_space = remaining_space - sum(sprite_sizes) - self.get_total_spacing()


        interested_sprites = [sprite for sprite, props in sprites if getattr(sprite, "expand", True)]


        # in order to stay pixel sharp we will recalculate remaining bonus
        # each time we give up some of the remaining space
        remaining_interested = len(interested_sprites)
        bonus = 0
        if remaining_space > 0 and interested_sprites:
            bonus = int(remaining_space / remaining_interested)

        actual_h = 0
        x_pos, y_pos = 0, 0

        for (sprite, props), min_size in zip(sprites, sprite_sizes):
            sprite_bonus = 0
            if sprite in interested_sprites:
                sprite_bonus = bonus
                remaining_interested -= 1
                remaining_space -= bonus
                if remaining_interested:
                    bonus = int(float(remaining_space) / remaining_interested)


            if self.orient_horizontal:
                sprite.alloc_w = (min_size + sprite_bonus) / sprite.scale_x
            else:
                sprite.alloc_h = (min_size + sprite_bonus) / sprite.scale_y

            w, h = getattr(sprite, "width", 0), getattr(sprite, "height", 0)
            if hasattr(sprite, "get_height_for_width_size"):
                w2, h2 = sprite.get_height_for_width_size()
                w, h = max(w, w2), max(h, h2)

            w = w * sprite.scale_x + props["margin_left"] + props["margin_right"]
            h = h * sprite.scale_y + props["margin_top"] + props["margin_bottom"]


            sprite.x = self.padding_left + x_pos + props["margin_left"] + (max(sprite.alloc_w * sprite.scale_x, w) - w) * getattr(sprite, "x_align", 0.5)
            sprite.y = self.padding_top + y_pos + props["margin_top"] + (max(sprite.alloc_h * sprite.scale_y, h) - h) * getattr(sprite, "y_align", 0.5)


            actual_h = max(actual_h, h * sprite.scale_y)

            if (min_size + sprite_bonus) > 0:
                if self.orient_horizontal:
                    x_pos += int(max(w, sprite.alloc_w * sprite.scale_x)) + self.spacing
                else:
                    y_pos += max(h, sprite.alloc_h * sprite.scale_y) + self.spacing


        if self.orient_horizontal:
            for sprite, props in sprites:
                sprite.__dict__['alloc_h'] = actual_h

        self.__dict__['_children_resize_queued'] = False

    def get_height_for_width_size(self):
        if self._children_resize_queued:
            self.resize_children()

        sprites = [sprite for sprite in self.sprites if sprite.visible]
        width, height = 0, 0
        for sprite in sprites:
            if hasattr(sprite, "get_height_for_width_size"):
                w, h = sprite.get_height_for_width_size()
            else:
                w, h = getattr(sprite, "width", 0), getattr(sprite, "height", 0)

            w, h = w * sprite.scale_x, h * sprite.scale_y


            if self.orient_horizontal:
                width += w
                height = max(height, h)
            else:
                width = max(width, w)
                height = height + h

        if self.orient_horizontal:
            width = width + self.get_total_spacing()
        else:
            height = height + self.get_total_spacing()

        width = width + self.horizontal_padding + self.margin_left + self.margin_right
        height = height + self.vertical_padding + self.margin_top + self.margin_bottom

        return width, height



    def get_min_size(self):
        if self.visible == False:
            return 0, 0

        if self._cached_w is None:
            sprites = [sprite for sprite in self.sprites if sprite.visible]

            width, height = 0, 0
            for sprite in sprites:
                if hasattr(sprite, "get_min_size"):
                    w, h = sprite.get_min_size()
                else:
                    w, h = getattr(sprite, "width", 0), getattr(sprite, "height", 0)

                w, h = w * sprite.scale_x, h * sprite.scale_y

                if self.orient_horizontal:
                    width += w
                    height = max(height, h)
                else:
                    width = max(width, w)
                    height = height + h

            if self.orient_horizontal:
                width = width + self.get_total_spacing()
            else:
                height = height + self.get_total_spacing()

            width = width + self.horizontal_padding + self.margin_left + self.margin_right
            height = height + self.vertical_padding + self.margin_top + self.margin_bottom

            w, h = max(width, self.min_width or 0), max(height, self.min_height or 0)
            self._cached_w, self._cached_h = w, h

        return self._cached_w, self._cached_h


class HBox(Box):
    """A horizontally aligned box. identical to ui.Box(horizontal=True)"""
    def __init__(self, contents = None, **kwargs):
        Box.__init__(self, contents, **kwargs)
        self.orient_horizontal = True


class VBox(Box):
    """A vertically aligned box. identical to ui.Box(horizontal=False)"""
    def __init__(self, contents = None, **kwargs):
        Box.__init__(self, contents, **kwargs)
        self.orient_horizontal = False


class Flow(Container):
    """container that flows the child sprites either horizontally or vertically.
       Currently it does not support any smart width/height sizing and so labels
       and other height-for-width-for-height type of containers should be told
       a fixed size in order to work properly
    """
    horizontal = True #: flow direction
    horizontal_spacing = 0 #: horizontal spacing
    vertical_spacing = 0 #: vertical spacing

    wrap = True #: should the items wrap when not fitting in the direction

    def __init__(self, horizontal = None, horizontal_spacing = None,
                 vertical_spacing = None, wrap = True, **kwargs):
        Container.__init__(self, **kwargs)

        if wrap is not None:
            self.wrap = wrap

        if horizontal is not None:
            self.horizontal = horizontal

        if horizontal_spacing is not None:
            self.horizontal_spacing = horizontal_spacing

        if vertical_spacing is not None:
            self.vertical_spacing = vertical_spacing


    def get_height_for_width_size(self):
        if self._children_resize_queued:
            self.resize_children()

        sprites = [sprite for sprite in self.sprites if sprite.visible]
        width, height = 0, 0
        for sprite in sprites:
            if hasattr(sprite, "get_height_for_width_size"):
                w, h = sprite.get_height_for_width_size()
            else:
                w, h = getattr(sprite, "width", 0), getattr(sprite, "height", 0)

            w = sprite.x + (w + sprite.horizontal_padding) * sprite.scale_x
            h = sprite.y + (h + sprite.horizontal_padding) * sprite.scale_y

            width = max(width, w)
            height = max(height, h)

        width = width + self.padding_right
        height = height + self.padding_bottom

        return width, height


    def get_rows(self):
        """returns extents of each row (x, y, x2, y2) and the sprites it
        contains"""
        sprites = [sprite for sprite in self.sprites if sprite.visible]

        width = self.width - self.padding_left - self.padding_right
        height = self.height - self.padding_top - self.padding_bottom

        x, y = self.padding_left, self.padding_top
        row_size = 0

        rows = []
        row_x, row_y, row_sprites = x, y, []
        for sprite in sprites:
            if self.horizontal:
                if self.wrap == False or x == self.padding_left or x + sprite.width < width:
                    row_size = max(row_size, sprite.height)
                    row_sprites.append(sprite)
                else:
                    #wrap
                    rows.append(((row_x, row_y, width, row_y + row_size), row_sprites))

                    y = y + row_size + self.vertical_spacing
                    x = self.padding_left
                    row_size = sprite.height

                    row_x, row_y, row_sprites = x, y, [sprite]

                x = x + sprite.width + self.horizontal_spacing
            else:
                if self.wrap == False or y == self.padding_top or y + sprite.height < height:
                    row_size = max(row_size, sprite.width)
                    row_sprites.append(sprite)
                else:
                    #wrap
                    rows.append(((row_x, row_y, row_x + row_size, height), row_sprites))

                    x = x + row_size + self.spacing
                    y = self.padding_top
                    row_size = sprite.width

                    row_x, row_y, row_sprites = x, y, [sprite]

                y = y + sprite.height + self.vertical_spacing

        if row_sprites:
            if self.horizontal:
                rows.append(((row_x, row_y, width, row_y + row_size), row_sprites))
            else:
                rows.append(((row_x, row_y, row_x + row_size, height), row_sprites))


        return rows


    def resize_children(self):
        for (x, y, x2, y2), sprites in self.get_rows():
            for sprite in sprites:
                sprite.x, sprite.y = x, y
                if self.horizontal:
                    x += sprite.width + self.horizontal_spacing
                else:
                    y += sprite.height + self.vertical_spacing
        self.__dict__['_children_resize_queued'] = False


class Table(Container):
    """Table allows aligning children in a grid. Elements can span several
    rows or columns"""
    def __init__(self, cols=1, rows=1, horizontal_spacing = 0, vertical_spacing = 0, **kwargs):
        Container.__init__(self, **kwargs)

        #: number of rows
        self.rows = rows

        #: number of columns
        self.cols = cols

        #: vertical spacing in pixels between the elements
        self.vertical_spacing = vertical_spacing

        #: horizontal spacing in pixels between the elements
        self.horizontal_spacing = horizontal_spacing

        self._horiz_attachments, self._vert_attachments = {}, {}


    def attach(self, sprite, left, right, top, bottom):
        """Attach a widget to the table. Use the left, right, top and bottom
        attributes to specify the attachment. Use this function instead of
        :py:func:`graphics.Sprite.add_child` to add sprites to the table"""
        self._horiz_attachments[sprite] = (left, right)
        self._vert_attachments[sprite] = (top, bottom)
        if sprite not in self.sprites:
            self.add_child(sprite)


    def get_min_size(self):
        if self._cached_w is None:
            if self.visible == False:
                return 0, 0

            w, h = sum(self.get_col_sizes()), sum(self.get_row_sizes())
            w = w + self.horizontal_spacing * (self.cols - 1) + self.horizontal_padding + self.margin_left + self.margin_right
            h = h + self.vertical_spacing * (self.rows - 1) + self.vertical_padding + self.margin_top + self.margin_bottom

            w, h = max(self.min_width, w), max(self.min_height, h)
            self._cached_w, self._cached_h = w, h

        return self._cached_w, self._cached_h

    def get_col_sizes(self):
        return self._get_section_sizes()

    def get_row_sizes(self):
        return self._get_section_sizes(horizontal = False)

    def _get_section_sizes(self, horizontal = True):
        if horizontal:
            sections, attachments, attr = self.cols, self._horiz_attachments, "x"
        else:
            sections, attachments, attr = self.rows, self._vert_attachments, "y"

        remaining, section_sizes = {}, []

        for i in range(sections):
            min_size = 0

            for sprite in attachments:
                if sprite.visible == False or attachments[sprite][0] > i or attachments[sprite][1] <= i:
                    continue

                start, end = attachments[sprite]

                if sprite not in remaining:
                    remaining_sections = end - start
                    sprite_size = get_min_size(sprite)[0] if attr =="x" else get_min_size(sprite)[1]

                    remaining[sprite] = remaining_sections, sprite_size
                else:
                    remaining_sections, sprite_size = remaining[sprite]

                min_size = max(min_size, sprite_size / remaining_sections)
                remaining[sprite] = remaining_sections - 1, sprite_size - min_size

            section_sizes.append(min_size)

        return section_sizes


    def resize_children(self):
        if not self.get_scene() or not self.get_scene().get_window():
            return

        width = self.width - self.padding_left - self.padding_right
        height = self.height - self.padding_top - self.padding_bottom

        def align(space, sections, attachments, attr):
            spacing = self.horizontal_spacing if attr == "x" else self.vertical_spacing
            expand_sections = defaultdict(list)
            section_sizes = self._get_section_sizes(attr == "x")

            """"
            # this code can tell you the actual partitions and which ones should be collapse
            # of potential used if we decide to implement the table more properly
            real_sections = set()
            for part in attachments.values():
                real_sections = real_sections | set(part)
            real_sections = list(real_sections)
            partitions = zip(real_sections, real_sections[1:])

            self.log(partitions, section_sizes)

            collapsed_sections = [i for start, end in partitions for i in range(start+1, end)]
            self.log("collapsed sections", collapsed_sections)
            """



            for i, min_size in enumerate(section_sizes):
                for sprite in attachments:
                    if attachments[sprite][0] > i or attachments[sprite][1] <= i:
                        continue

                    expand_sections[i].append((attr =="x" and  getattr(sprite, "expand", True)) or (attr == "y" and getattr(sprite, "expand_vert", True)))

                if min_size == 0:
                    expand_sections[i].append(True)

            # distribute the remaining space
            available_space = space - sum(section_sizes) - (sections - 1) * spacing

            # expand only those sections everybody agrees on
            expand_sections = [expand[0] for expand in expand_sections.items() if all(expand[1])]

            expand_sections = expand_sections or [sections-1] # if nobody wants to expand we tell the last partition to do that

            if available_space > 0 and expand_sections:
                bonus = available_space / len(expand_sections)
                for section in expand_sections:
                    section_sizes[section] += bonus

            positions = []
            pos = 0
            for s in section_sizes:
                positions.append(pos)
                pos += s + spacing

            positions.append(pos)

            for i, (sprite, (start, end)) in enumerate(attachments.iteritems()):
                if attr == "x":
                    sprite.alloc_w = positions[end] - positions[start] - spacing
                    sprite.x = positions[start] + (sprite.alloc_w - sprite.width) * getattr(sprite, "x_align", 0.5) + self.padding_left
                else:
                    sprite.alloc_h = positions[end] - positions[start] - spacing
                    sprite.y = positions[start] + (sprite.alloc_h - sprite.height) * getattr(sprite, "y_align", 0.5) + self.padding_top


            if self.debug:
                for i, p in enumerate(positions):
                    if i == sections:
                        p = p - spacing

                    if attr == "x":
                        self.graphics.move_to(p + self.padding_left, 0 + self.padding_top)
                        self.graphics.line_to(p + self.padding_left, height + self.padding_top)
                        self.graphics.stroke("#0f0")
                    else:
                        self.graphics.move_to(0 + self.padding_left, p + self.padding_top)
                        self.graphics.line_to(width + self.padding_left, p + self.padding_top)
                        self.graphics.stroke("#f00")


        align(width, self.cols, self._horiz_attachments, "x")
        align(height, self.rows, self._vert_attachments, "y")
        self.__dict__['_children_resize_queued'] = False

class Viewport(Bin):
    """View a fragment of the child. Most commonly seen in
    :class:`~ui.scroll.ScrollArea`"""
    def __init__(self, contents=None, **kwargs):
        Bin.__init__(self, contents, **kwargs)
        self.connect("on-render", self.__on_render)

    def get_container_size(self):
        """returns the size of inner contents"""
        if not self.child:
            return 0,0

        if hasattr(self.child, "get_height_for_width_size"):
            self.resize_children()
            return self.child.get_height_for_width_size()
        else:
            return self.child.width, self.child.height

    def get_min_size(self):
        w, h = (self.min_width or 0, self.min_height or 0) if self.visible else (0, 0)
        return w, h

    def get_height_for_width_size(self):
        return self.get_min_size()

    def resize_children(self):
        """ help sprites a bit and tell them how much space we have in
            case they care (which they mostly should not as in fixed you can do
            anything """
        if not self.child: return

        w, h = self.width, self.height
        # invalidate child extents as the viewport is clipping to it's extents
        self._prev_parent_matrix = None

        self.child.alloc_w = w - max(self.child.x, 0)
        self.child.alloc_h = h - max(self.child.y, 0)
        self.__dict__['_children_resize_queued'] = False


    def __on_render(self, sprite):
        self.graphics.rectangle(0, 0, self.width+1, self.height)
        self.graphics.clip()



class Group(Box):
    """A container for radio and toggle buttons.

    **Signals**:

    **on-change** *(sprite, toggled_item)*
    - fired after the toggle.
    """
    __gsignals__ = {
        "on-change": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
    }
    spacing = 0

    def __init__(self, contents = None, allow_no_selection = False, **kwargs):
        Box.__init__(self, contents = contents, **kwargs)
        self.current_item = None

        #: If set to true, repeat toggle of the selected item will un-toggle it
        #: and thus there will be no current item
        self.allow_no_selection = allow_no_selection

        #: all group elements, not necessarily packed in the group
        self.elements = []

        self._add_item(*(contents or []))

    def add_child(self, *sprites):
        Box.add_child(self, *sprites)
        if hasattr(self, "elements"):
            self._add_item(*sprites)

    def remove_child(self, *sprites):
        Box.remove_child(self, *sprites)
        self._remove_item(*sprites)


    def _add_item(self, *elements):
        """adds item to group. this is called from the toggle button classes"""
        for item in elements:
            if item in self.elements:
                continue
            self.connect_child(item, "on-toggle", self.on_toggle)
            self.connect_child(item, "on-mouse-down", self.on_mouse_down)
            self.elements.append(item)
            item.group = self

    def _remove_item(self, *elements):
        """removes item from group. this is called from the toggle button classes"""
        for item in elements:
            self.disconnect_child(item)
            if item in self.elements:
                self.elements.remove(item)

    def on_mouse_down(self, button, event):
        if button.enabled == False:
            return
        if self.allow_no_selection:
            # avoid echoing out in the no-select cases
            return

        button.toggle()


    def on_toggle(self, sprite):
        changed = sprite != self.current_item or self.allow_no_selection
        sprite = sprite or self.current_item
        if sprite.toggled:
            self.current_item = sprite
        elif self.allow_no_selection:
            self.current_item = None

        for item in self.elements:
            item.toggled = item == self.current_item

        if changed:
            self.emit("on-change", self.current_item)

    def get_selected( self ):
        selected = None
        for item in self.elements:
            if item.toggled:
                selected = item
                break
        return selected


class Panes(Box):
    """a container that has a grip area between elements that allows to change
    the space allocated to each one"""
    spacing = 10
    def __init__(self, position = 150, **kwargs):
        Box.__init__(self, **kwargs)

        #: current position of the grip
        self.split_position = position

        self.grips = []

    def add_child(self, *sprites):
        for sprite in sprites:
            if sprite not in self.grips and len(self.sprites) > 0:
                grip = PanesGrip(x = self.split_position)
                self.connect_child(grip, "on-drag", self.__on_drag)
                self.grips.append(grip)
                self.add_child(grip)

            Box.add_child(self, sprite)

    def __on_drag(self, sprite, event):
        sprite.y = 0
        self.split_position = sprite.x
        self.resize_children()


    def resize_children(self):
        if not self.get_scene() or not self.get_scene().get_window():
            return

        if not self.sprites:
            return

        self.sprites[0].x = self.padding_left

        for sprite in self.sprites:
            sprite.y = self.padding_top
            sprite.alloc_h = self.height - self.vertical_padding

        prev_grip_x = self.padding_left
        for grip in self.grips:
            self.sprites[self.sprites.index(grip)-1].alloc_w = grip.x - prev_grip_x - self.spacing
            self.sprites[self.sprites.index(grip)+1].x = grip.x + grip.width + self.spacing

            prev_grip_x = grip.x

        self.sprites[-1].alloc_w = self.width - self.sprites[-1].x - self.padding_left
        self.__dict__['_children_resize_queued'] = False


class PanesGrip(Widget):
    """a grip element between panes"""
    mouse_cursor = gdk.CursorType.SB_H_DOUBLE_ARROW

    def __init__(self, width=1, **kwargs):
        Widget.__init__(self, **kwargs)
        self.width = width
        self.draggable = True

    def do_render(self):
        self.graphics.rectangle(0, 0, self.width, self.height)
        self.graphics.fill("#aaa")

########NEW FILE########
__FILENAME__ = data
# - coding: utf-8 -

# Copyright (c) 2011-2012 Media Modifications, Ltd.
# Dual licensed under the MIT or GPL Version 2 licenses.
from gi.repository import GObject as gobject

class TreeModel(gobject.GObject):
    """A helper structure that is used by treeviews and listitems - our version
        of a tree model, based on list.
        Pass in either simple list for single-column data or a nested list for
        multi-column
    """

    __gsignals__ = {
        "row-changed": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
        "row-deleted": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, ()),
        "row-inserted": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
    }

    def __init__(self, iterable = None):
        # we will wrap every row in an object that will listen to setters and getters. can't go beyond that though
        # which means data[row][col]['imagine we have a dictionary here so this is a key'] = 'a' will go by unnoticed!
        # is that ok? - TODO

        self._data = []

        gobject.GObject.__init__(self)
        if iterable:
            self.extend(iterable)

    def __setitem__(self, row_idx, val):
        self._data.__setitem__(row_idx, TreeModelRow(self, val))
        self._on_row_changed(self._data[row_idx]._row)

    def __getitem__(self, row_idx):
        return self._data.__getitem__(row_idx)

    def __delitem__(self, idx):
        del self._data[idx]
        self._on_row_deleted()

    def __len__(self):
        return len(self._data)

    def index(self, item):
        return self._data.index(item)

    def append(self, row):
        if isinstance(row, list) == False:
            row = [row]
        self._data.append(TreeModelRow(self, row))
        self._on_row_changed(None)

    def remove(self, target_row):
        """remove the given row"""
        if target_row in self._data:
            self.__delitem__(self._data.index(target_row))
        else:
            # TODO - figure out a better way
            if isinstance(target_row, list) == False:
                target_row = [target_row]

            for i, row in enumerate(self._data):
                if row._row == target_row:
                    self.__delitem__(i)
                    return

    def pop(self, idx):
        row = self._data.pop(idx)
        self._on_row_deleted()
        return row

    def insert(self, i, row):
        if isinstance(row, list) == False:
            row = [row]
        self._data.insert(i, TreeModelRow(self, row))
        self._on_row_changed(None)

    def extend(self, rows):
        for row in rows:
            if isinstance(row, list) == False:
                row = [row]
            self._data.append(TreeModelRow(self, row))
        self._on_row_changed(None)

    def _on_row_changed(self, row = None, col = None):
        self.emit("row-changed", self._data.index(row) if row else None)

    def _on_row_deleted(self):
        self.emit("row-deleted")


class TreeModelRow(object):
    def __init__(self, parent = None, row = None):
        self._parent = parent

        if hasattr(row, "__getitem__") == False:
            row = [row]

        self._row = row or []

    def __setitem__(self, col, val):
        self._row[col] = val
        self._parent._on_row_changed(self, col)

    def __getitem__(self, col):
        return self._row[col]

    def __iter__(self):
        return iter(self._row)

    def __repr__(self):
        return "<TreeModelRow %s %s>" % (getattr(self, "id", None) or str(id(self)), str(self._row))

########NEW FILE########
__FILENAME__ = dialog
# - coding: utf-8 -

# Copyright (c) 2011-2012 Media Modifications, Ltd.
# Dual licensed under the MIT or GPL Version 2 licenses.

from gi.repository import Gtk as gtk
from gi.repository import Gdk as gdk
from gi.repository import GObject as gobject

from ui import VBox, HBox, Fixed, Label, Button, ScrollArea
from gi.repository import Pango as pango


class DialogTitle(Label):
    """dialog title - an ordinary label classed out for themeing.
    set the dialog's title_class to use your class"""
    x_align = 0
    y_align = 0
    padding = 10
    margin = [0, 2]
    fill = True
    expand = False

    def __init__(self, markup="", size=16, background_color = "#999", **kwargs):
        Label.__init__(self, markup=markup, size=size,
                       background_color=background_color,
                       **kwargs)

class DialogBox(VBox):
    """the container with dialog title, contents and buttons, classed out for
    themeing. set the dialog's dialog_box_class to use your class"""
    def __init__(self, contents=None, spacing = 0, **kwargs):
        VBox.__init__(self, contents=contents, spacing=spacing, **kwargs)

    def do_render(self):
        self.graphics.rectangle(-0.5, -0.5, self.width, self.height, 5)
        self.graphics.fill_stroke("#eee", "#999", line_width = 5)


class Dialog(Fixed):
    """An in-window message box

    **Signals**

        **on-close** *(sprite, pressed_button)*
        - fired when the window is closed. returns back the label of the button that triggered closing
    """
    __gsignals__ = {
        "on-close": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
    }

    title_class = DialogTitle
    dialog_box_class = DialogBox

    def __init__(self, contents = None,
                 title = None, draggable = True,
                 width = 500,
                 modal = False,
                 **kwargs):
        Fixed.__init__(self, **kwargs)
        self.interactive, self.mouse_cursor = True, False

        #: whether the dialog is modal or not. in case of modality won't be able
        #: to click on other interface elements while dialog is being displayed
        self.modal = modal

        #: dialog content - message and such like
        self.contents = contents

        #: container for description and buttons
        # setting it interactive and filling extents so that they can't be clicked through
        self.box = VBox(contents, interactive=True, mouse_cursor = False)
        def fill_blank():
            self.box.graphics.rectangle(0, 0, self.box.width, self.box.height)
            self.box.graphics.new_path()
        self.box.do_render = fill_blank

        #: the main container box that contains title and contents
        components = []
        self.title_label = None
        if title:
            self.title_label = self.title_class(title)
            components.append(self.title_label)
        components.append(self.box)

        self.main_box = self.dialog_box_class(components, interactive=draggable, draggable=draggable, width=width, padding=0)

        self.connect_child(self.main_box, "on-drag", self.on_drag)
        self._dragged = False

        self.add_child(self.main_box)

        #: fill color for the background when the dialog is modal
        self.background_fill = "#fff"

        #: opacity of the background fill when the dialog is modal
        self.background_opacity = .5

        #: initial centered position as a tuple in lieu of scale_x, scale_y
        self.pre_dragged_absolute_position = None


    def on_drag(self, sprite, event):
        self.main_box.x = max(min(self.main_box.x, self.width - 10), -self.main_box.width + 10 )
        self.main_box.y = max(min(self.main_box.y, self.height - 10), -self.main_box.height + 10 )
        self._dragged = True


    def __setattr__(self, name, val):
        if name in ("width",) and hasattr(self, "main_box"):
            self.main_box.__setattr__(name, val)
        else:
            Fixed.__setattr__(self, name, val)

        if name == "contents" and hasattr(self, "box"):
            self.box.add_child(val)

    def show(self, scene):
        """show the dialog"""
        scene.add_child(self)

    def resize_children(self):
        if not self._dragged:
            if not self.pre_dragged_absolute_position:
                self.main_box.x = (self.width - self.main_box.width) * self.x_align
                self.main_box.y = (self.height - self.main_box.height) * self.y_align
            else:
                #put it right where we want it
                self.main_box.x = self.pre_dragged_absolute_position[0] - (self.main_box.width * 0.5)
                self.main_box.y = self.pre_dragged_absolute_position[1] - (self.main_box.height * 0.5)
                #but ensure it is in bounds, cause if it ain't you could be in a world of modal pain
                self.on_drag( None, None )
        else:
            self.on_drag(self.main_box, None)

    def close(self, label = ""):
        self.emit("on-close", label)
        scene = self.get_scene()
        if scene:
            scene.remove_child(self)


    def do_render(self):
        if self.modal:
            self.graphics.rectangle(0, 0, self.width + 1, self.height + 1)
            self.graphics.fill(self.background_fill, self.background_opacity)
        else:
            self.graphics.clear()



class ConfirmationDialog(Dialog):
    def __init__(self, title, message, affirmative_label,
                 decline_label = "Cancel", width=500, modal = False):
        Dialog.__init__(self, title = title, width = width, modal=modal)

        scrollbox = ScrollArea(Label(markup=message, padding=5, overflow=pango.WrapMode.WORD),
                                    scroll_horizontal = False,
                                    border = 0,
                                    margin=2, margin_right=3,
                                    height = 150)

        affirmative = Button(affirmative_label, id="affirmative_button")
        affirmative.connect("on-click", self._on_button_click)
        decline = Button(decline_label, id="decline_button")
        decline.connect("on-click", self._on_button_click)

        self.box.contents = VBox([scrollbox, HBox([HBox(), decline, affirmative], expand=False, padding=10)])

    def _on_button_click(self, button, event):
        approved = button.id == "affirmative_button"
        self.close(approved)

########NEW FILE########
__FILENAME__ = entry
# - coding: utf-8 -

# Copyright (c) 2011-2012 Media Modifications, Ltd.
# Dual licensed under the MIT or GPL Version 2 licenses.

from gi.repository import Gtk as gtk
from gi.repository import Gdk as gdk
from gi.repository import GObject as gobject

import re
from lib import graphics

from ui import Bin, Viewport, ScrollArea, Button, Table, Label, Widget
from gi.repository import Pango as pango


class Entry(Bin):
    """A text entry field"""
    __gsignals__ = {
        "on-change": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
        "on-position-change": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
    }

    padding = 5

    mouse_cursor = gdk.CursorType.XTERM

    font_desc = "Sans Serif 10" #: pango.FontDescription to use for the label

    color = "#000" #: font color
    cursor_color = "#000" #: cursor color
    selection_color = "#A8C2E0" #: fill color of the selection region

    def __init__(self, text="", draw_border = True,  valid_chars = None,
                 validate_on_type = True, single_paragraph = True,
                 text_formatter = None, alignment = None,
                 font_desc = None, **kwargs):
        Bin.__init__(self, **kwargs)

        self.display_label = graphics.Label(color=self.color)

        self.viewport = Viewport(self.display_label)
        self.viewport.connect("on-render", self.__on_viewport_render)

        self.add_child(self.viewport)

        self.can_focus = True

        self.interactive = True

        self.editable = True

        #: current cursor position
        self.cursor_position = None

        #: start position of the selection
        self.selection_start = 0

        #: end position of the selection
        self.selection_end = 0

        if font_desc is not None:
            self.font_desc = font_desc
        self.display_label.font_desc = self.font_desc

        #: text alignment in the entry
        self.alignment = alignment

        #: if True, a border will be drawn around the input element
        self.draw_border = draw_border

        #self.connect("on-key-press", self.__on_key_press)
        self.connect("on-mouse-down", self.__on_mouse_down)
        self.connect("on-double-click", self.__on_double_click)
        self.connect("on-triple-click", self.__on_triple_click)
        self.connect("on-blur", self.__on_blur)
        self.connect("on-focus", self.__on_focus)

        self.connect_after("on-render", self.__on_render)

        self._scene_mouse_move = None
        self._scene_mouse_up = None
        self._selection_start_position = None
        self._letter_positions = []

        #: a string, function or regexp or valid chars for the input
        #: in case of function, it will receive the string to be tested
        #: as input and expects to receive back a boolean of whether the string
        #: is valid or not
        self.valid_chars = valid_chars

        #: should the content be validate right when typing and invalid version prohibited
        self.validate_on_type = validate_on_type

        #: function to style the entry text - change color and such
        #: the function receives one param - the text, and must return
        #: processed text back. will be using original text if the function
        #: does not return anything.
        #: Note: this function can change only the style, not the actual content
        #: as the latter will mess up text selection because of off-sync between
        #: the label value and what is displayed
        self.text_formatter = text_formatter if text_formatter else self.text_formatter


        #: should the text input support multiple lines
        self.single_paragraph = single_paragraph

        self.update_text(text)
        self._last_good_value = text # last known good value of the input


    def __setattr__(self, name, val):
        if name == "cursor_position" and not self.editable:
            val = None

        if self.__dict__.get(name, "hamster_graphics_no_value_really") == val:
            return

        if name == "text":
            val = val or ""
            if getattr(self, "text_formatter", None):
                markup = self.text_formatter(val.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))

            if markup:
                self.display_label.markup = markup
            else:
                self.display_label.text = val

        Bin.__setattr__(self, name, val)

        if name == "text":
            self.emit("on-change", val)

        if name in("font_desc", "alignment", "single_paragraph", "color"):
            setattr(self.display_label, name, val)

        elif name == "alloc_w" and getattr(self, "overflow", False) != False and hasattr(self, "display_label"):
            self.display_label.width = val - self.horizontal_padding

        elif name == "overflow" and val != False and hasattr(self, "display_label"):
            if val in (pango.WrapMode.WORD, pango.WrapMode.WORD_CHAR, pango.WrapMode.CHAR):
                self.display_label.wrap = val
                self.display_label.ellipsize = None
            elif val in (pango.EllipsizeMode.START, pango.EllipsizeMode.END):
                self.display_label.wrap = None
                self.display_label.ellipsize = val

        if name == "cursor_position":
            self.emit("on-position-change", val)

    def get_min_size(self):
        return self.min_width or 0, max(self.min_height, self.display_label.height + self.vertical_padding)

    def text_formatter(self, text):
        return None

    def test_value(self, text):
        if not self.valid_chars:
            return True
        elif isinstance(self.valid_chars, basestring):
            return set(text) - set(self.valid_chars) == set([])
        elif hasattr(self.valid_chars, '__call__'):
            return self.valid_chars(text)
        else:
            return False

    def get_height_for_width_size(self):
        return self.get_min_size()


    def update_text(self, text):
        """updates the text field value and the last good known value,
        respecting the valid_chars and validate_on_type flags"""
        text = text or ""

        if self.test_value(text):
            self.text = text
            if self.validate_on_type:
                self._last_good_value = text
        elif not self.validate_on_type:
            self.text = text
        else:
            return False

        self.viewport.height = self.display_label.height
        if self.cursor_position is None:
            self.cursor_position = len(text)

        return True


    def _index_to_pos(self, index):
        """give coordinates for the position in text. maps to the
        display_label's pango function"""
        ext = self.display_label._test_layout.index_to_pos(index)
        extents = [e / pango.SCALE for e in (ext.x, ext.y, ext.width, ext.height)]
        return extents

    def _xy_to_index(self, x, y):
        """from coordinates caluculate position in text. maps to the
        display_label's pango function"""
        x = x - self.display_label.x - self.viewport.x
        index = self.display_label._test_layout.xy_to_index(int(x*pango.SCALE), int(y*pango.SCALE))
        return index[0] + index[1]


    def __on_focus(self, sprite):
        self._last_good_value = self.text

    def __on_blur(self, sprite):
        self._edit_done()

    def _edit_done(self):
        if self.test_value(self.text):
            self._last_good_value = self.text
        else:
            self.update_text(self._last_good_value)

    def __on_mouse_down(self, sprite, event):
        i = self._xy_to_index(event.x, event.y)

        self.selection_start = self.selection_end = self.cursor_position = i
        self._selection_start_position = self.selection_start

        scene = self.get_scene()
        if not self._scene_mouse_up:
            self._scene_mouse_up = scene.connect("on-mouse-up", self._on_scene_mouse_up)
            self._scene_mouse_move = scene.connect("on-mouse-move", self._on_scene_mouse_move)

    def __on_double_click(self, sprite, event):
        # find the word
        cursor = self.cursor_position
        self.selection_start = self.text.rfind(" ", 0, cursor) + 1

        end = self.text.find(" ", cursor)
        self.cursor_position = self.selection_end = end if end > 0 else len(self.text)


    def __on_triple_click(self, sprite, event):
        self.selection_start = 0
        self.cursor_position = self.selection_end = len(self.text)

    def _on_scene_mouse_up(self, scene, event):
        scene.disconnect(self._scene_mouse_up)
        scene.disconnect(self._scene_mouse_move)
        self._scene_mouse_up = self._scene_mouse_move = None

    def _on_scene_mouse_move(self, scene, event):
        if self.focused == False:
            return

        # now try to derive cursor position
        x, y = self.display_label.from_scene_coords(event.x, event.y)
        x = x + self.display_label.x + self.viewport.x
        i = self._xy_to_index(x, y)

        self.cursor_position = i
        if self.cursor_position < self._selection_start_position:
            self.selection_start = self.cursor_position
            self.selection_end = self._selection_start_position
        else:
            self.selection_start = self._selection_start_position
            self.selection_end = self.cursor_position

    def _get_iter(self, index = 0):
        """returns iterator that has been run till the specified index"""
        iter = self.display_label._test_layout.get_iter()
        for i in range(index):
            iter.next_char()
        return iter

    def _do_key_press(self, event):
        """responding to key events"""
        key = event.keyval
        shift = event.state & gdk.ModifierType.SHIFT_MASK
        control = event.state & gdk.ModifierType.CONTROL_MASK

        if not self.editable:
            return

        def emit_and_return():
            self.emit("on-key-press", event)
            return


        if self.single_paragraph and key == gdk.KEY_Return:
            self._edit_done()
            return emit_and_return()

        self._letter_positions = []

        if key == gdk.KEY_Left:
            if shift and self.cursor_position == 0:
                return emit_and_return()

            if control:
                self.cursor_position = self.text[:self.cursor_position].rstrip().rfind(" ") + 1
            else:
                self.cursor_position -= 1

            if shift:
                if self.cursor_position < self.selection_start:
                    self.selection_start = self.cursor_position
                else:
                    self.selection_end = self.cursor_position
            elif self.selection_start != self.selection_end:
                self.cursor_position = self.selection_start

        elif key == gdk.KEY_Right:
            if shift and self.cursor_position == len(self.text):
                return emit_and_return()

            if control:
                prev_pos = self.cursor_position
                self.cursor_position = self.text[self.cursor_position:].lstrip().find(" ")
                if self.cursor_position == -1:
                    self.cursor_position = len(self.text)
                else:
                    self.cursor_position += prev_pos + 1
            else:
                self.cursor_position += 1

            if shift:
                if self.cursor_position > self.selection_end:
                    self.selection_end = self.cursor_position
                else:
                    self.selection_start = self.cursor_position
            elif self.selection_start != self.selection_end:
                self.cursor_position = self.selection_end

        elif key == gdk.KEY_Up and self.single_paragraph == False:
            iter = self._get_iter(self.cursor_position)

            if str(iter.get_line_readonly()) != str(self.display_label._test_layout.get_line_readonly(0)):
                char_pos = iter.get_char_extents().x
                char_line = str(iter.get_line_readonly())

                # now we run again to run until previous line
                prev_iter, iter = self._get_iter(), self._get_iter()
                prev_line = None
                while str(iter.get_line_readonly()) != char_line:
                    if str(prev_line) != str(iter.get_line_readonly()):
                        prev_iter = iter.copy()
                        prev_line = iter.get_line_readonly()
                    iter.next_char()

                index = prev_iter.get_line_readonly().x_to_index(char_pos - prev_iter.get_char_extents().x)
                index = index[1] + index[2]

                self.cursor_position = index

                if shift:
                    if self.cursor_position < self.selection_start:
                        self.selection_start = self.cursor_position
                    else:
                        self.selection_end = self.cursor_position
                elif self.selection_start != self.selection_end:
                    self.cursor_position = self.selection_start


        elif key == gdk.KEY_Down and self.single_paragraph == False:
            iter = self._get_iter(self.cursor_position)
            char_pos = iter.get_char_extents().x

            if iter.next_line():
                index = iter.get_line_readonly().x_to_index(char_pos - iter.get_char_extents().x)
                index = index[1] + index[2]
                self.cursor_position = index

                if shift:
                    if self.cursor_position > self.selection_end:
                        self.selection_end = self.cursor_position
                    else:
                        self.selection_start = self.cursor_position
                elif self.selection_start != self.selection_end:
                    self.cursor_position = self.selection_end


        elif key == gdk.KEY_Home:
            if self.single_paragraph or control:
                self.cursor_position = 0
                if shift:
                    self.selection_end = self.selection_start
                    self.selection_start = self.cursor_position
            else:
                iter = self._get_iter(self.cursor_position)
                line = str(iter.get_line_readonly())

                # find the start of the line
                iter = self._get_iter()
                while str(iter.get_line_readonly()) != line:
                    iter.next_char()
                self.cursor_position = iter.get_index()

                if shift:
                    start_iter = self._get_iter(self.selection_start)
                    end_iter = self._get_iter(self.selection_end)
                    if str(start_iter.get_line_readonly()) == str(end_iter.get_line_readonly()):
                        self.selection_end = self.selection_start
                        self.selection_start = self.cursor_position
                    else:
                        if self.cursor_position < self.selection_start:
                            self.selection_start = self.cursor_position
                        else:
                            self.selection_end = self.cursor_position

        elif key == gdk.KEY_End:
            if self.single_paragraph or control:
                self.cursor_position = len(self.text)
                if shift:
                    self.selection_start = self.selection_end
                    self.selection_end = self.cursor_position
            else:
                iter = self._get_iter(self.cursor_position)

                #find the end of the line
                line = str(iter.get_line_readonly())
                prev_iter = None

                while str(iter.get_line_readonly()) == line:
                    prev_iter = iter.copy()
                    moved = iter.next_char()
                    if not moved:
                        prev_iter = iter
                        break

                self.cursor_position = prev_iter.get_index()

                if shift:
                    start_iter = self._get_iter(self.selection_start)
                    end_iter = self._get_iter(self.selection_end)
                    if str(start_iter.get_line_readonly()) == str(end_iter.get_line_readonly()):
                        self.selection_start = self.selection_end
                        self.selection_end = self.cursor_position
                    else:
                        if self.cursor_position > self.selection_end:
                            self.selection_end = self.cursor_position
                        else:
                            self.selection_start = self.cursor_position


        elif key == gdk.KEY_BackSpace:
            if self.selection_start != self.selection_end:
                if not self.update_text(self.text[:self.selection_start] + self.text[self.selection_end:]):
                    return emit_and_return()
            elif self.cursor_position > 0:
                if not self.update_text(self.text[:self.cursor_position-1] + self.text[self.cursor_position:]):
                    return emit_and_return()
                self.cursor_position -= 1

        elif key == gdk.KEY_Delete:
            if self.selection_start != self.selection_end:
                if not self.update_text(self.text[:self.selection_start] + self.text[self.selection_end:]):
                    return emit_and_return()
            elif self.cursor_position < len(self.text):
                if not self.update_text(self.text[:self.cursor_position] + self.text[self.cursor_position+1:]):
                    return emit_and_return()
        elif key == gdk.KEY_Escape:
            return emit_and_return()

        #prevent garbage from common save file mneumonic
        elif control and key in (gdk.KEY_s, gdk.KEY_S):
            return emit_and_return()

        # copying and pasting
        elif control and key in (gdk.KEY_c, gdk.KEY_C): # copy
            clipboard = gtk.Clipboard()
            clipboard.set_text(self.text[self.selection_start:self.selection_end])
            return emit_and_return()

        elif control and key in (gdk.KEY_x, gdk.KEY_X): # cut
            text = self.text[self.selection_start:self.selection_end]
            if self.update_text(self.text[:self.selection_start] + self.text[self.selection_end:]):
                clipboard = gtk.Clipboard()
                clipboard.set_text(text)

        elif control and key in (gdk.KEY_v, gdk.KEY_V): # paste
            clipboard = gtk.Clipboard()
            clipboard.request_text(self._on_clipboard_text)
            return emit_and_return()

        elif control and key in (gdk.KEY_a, gdk.KEY_A): # select all
            self.selection_start = 0
            self.cursor_position = self.selection_end = len(self.text)
            return emit_and_return()

        # normal letters
        elif event.string:
            if self.update_text(self.text[:self.selection_start] + event.string + self.text[self.selection_end:]):
                self.cursor_position = self.selection_start + 1
                self.selection_start = self.selection_end = self.cursor_position
            return emit_and_return()
        else: # in case of anything else just go home
            return emit_and_return()


        self.cursor_position = min(max(0, self.cursor_position), len(self.text))
        self.selection_start = min(max(0, self.selection_start), len(self.text))
        self.selection_end = min(max(0, self.selection_end), len(self.text))

        if shift == False:
            self.selection_start = self.selection_end = self.cursor_position

        return emit_and_return()

    def _on_clipboard_text(self, clipboard, text, data):
        if self.update_text(self.text[:self.selection_start] + text + self.text[self.selection_end:]):
            self.selection_start = self.selection_end = self.cursor_position = self.selection_start + len(text)

    def do_render(self):
        self.graphics.set_line_style(width=1)
        self.graphics.rectangle(0.5, -1.5, self.width, self.height + 2, 3)
        if self.draw_border:
            self.graphics.fill_preserve("#fff")
            self.graphics.stroke("#aaa")


    def __on_render(self, sprite):
        self.graphics.rectangle(0, 0, self.width, self.height)
        self.graphics.new_path()

        if self.cursor_position is not None:
            cur_x, cur_y, cur_w, cur_h = self._index_to_pos(self.cursor_position)
            if self.display_label.x + cur_x > self.viewport.width:
                self.display_label.x = min(0, self.viewport.width - cur_x) # cursor visible at the right side
            elif self.display_label.x + cur_x < 0:
                self.display_label.x -= (self.display_label.x + cur_x) # cursor visible at the left side
            elif self.display_label.x < 0 and self.display_label.x + self.display_label.width < self.viewport.width:
                self.display_label.x = min(self.viewport.width - self.display_label.width, 0)

        # align the label within the entry
        if self.display_label.width < self.viewport.width:
            if self.alignment == pango.Alignment.RIGHT:
                self.display_label.x = self.viewport.width - self.display_label.width
            elif self.alignment == pango.Alignment.CENTER:
                self.display_label.x = (self.viewport.width - self.display_label.width) / 2

        #if self.single_paragraph:
        #    self.display_label.y = (self.viewport.height - self.display_label.height) / 2.0
        self.viewport._sprite_dirty = True # so that we get the cursor drawn


    def __on_viewport_render(self, viewport):
        if self.focused == False:
            return

        if self.cursor_position is None:
            return

        cur_x, cur_y, cur_w, cur_h = self._index_to_pos(self.cursor_position)
        cur_x = cur_x + self.display_label.x
        cur_y += self.display_label.y

        viewport.graphics.move_to(cur_x + 0.5, cur_y)
        viewport.graphics.line_to(cur_x + 0.5, cur_y + cur_h)
        viewport.graphics.stroke(self.cursor_color)

        if self.selection_start == self.selection_end:
            return # all done!


        start_x, start_y, start_w, start_h = self._index_to_pos(self.selection_start)
        end_x, end_y, end_w, end_h = self._index_to_pos(self.selection_end)


        iter = self._get_iter(self.selection_start)

        char_exts = iter.get_char_extents()
        cur_x, cur_y = char_exts.x / pango.SCALE, char_exts.y / pango.SCALE + self.display_label.y

        cur_line = None
        for i in range(self.selection_end - self.selection_start):
            prev_iter = pango.LayoutIter.copy(iter)
            iter.next_char()

            line = iter.get_line_readonly()
            if str(cur_line) != str(line): # can't compare layout lines for some reason
                exts = prev_iter.get_char_extents()
                char_exts = [ext / pango.SCALE for ext in (exts.x, exts.y, exts.width, exts.height)]
                viewport.graphics.rectangle(cur_x + self.display_label.x, cur_y,
                                            char_exts[0] + char_exts[2] - cur_x, char_exts[3])

                char_exts = iter.get_char_extents()
                cur_x, cur_y = char_exts.x / pango.SCALE, char_exts.y / pango.SCALE + self.display_label.y

            cur_line = line

        exts = iter.get_char_extents()
        char_exts = [ext / pango.SCALE for ext in  (exts.x, exts.y, exts.width, exts.height)]

        viewport.graphics.rectangle(cur_x + self.display_label.x, cur_y,
                                    char_exts[0] - cur_x, self.display_label.y + char_exts[1] - cur_y + char_exts[3])
        viewport.graphics.fill(self.selection_color)



class TextArea(ScrollArea):
    """A text input field that displays scrollbar when text does not fit anymore"""
    padding = 5

    mouse_cursor = gdk.CursorType.XTERM

    font_desc = "Sans Serif 10" #: pango.FontDescription to use for the label

    color = "#000" #: font color
    cursor_color = "#000" #: cursor color
    selection_color = "#A8C2E0" #: fill color of the selection region

    def __init__(self, text="", valid_chars = None,
                 validate_on_type = True, text_formatter = None,
                 alignment = None, font_desc = None, **kwargs):
        ScrollArea.__init__(self, **kwargs)


        self._entry = Entry(text, single_paragraph=False,
                            draw_border=False, padding=0,
                            valid_chars=valid_chars,
                            validate_on_type=validate_on_type,
                            text_formatter=text_formatter,
                            alignment=alignment,
                            font_desc=font_desc)
        self._entry.get_min_size = self.entry_get_min_size

        self._entry.connect("on-change", self.on_entry_change)
        self._entry.connect("on-position-change", self.on_entry_position_change)
        self.viewport.add_child(self._entry)


    def __setattr__(self, name, val):
        if name in ("text", "valid_chars", "validate_on_type", "text_formatter",
                    "alignment", "font_desc"):
            self._entry.__setattr__(name, val)
        else:
            ScrollArea.__setattr__(self, name, val)


    def on_entry_change(self, entry, text):
        self._entry.viewport.width = self._entry.display_label.width
        #self.display_label.max_width = self.viewport.width
        self._entry.queue_resize()
        self._scroll_to_cursor()

    def on_entry_position_change(self, entry, new_position):
        self._scroll_to_cursor()

    def _scroll_to_cursor(self):
        if self._entry.cursor_position is None or self._entry.cursor_position < 0:
            return

        x, y, w, h = self._entry._index_to_pos(self._entry.cursor_position)

        if x + self._entry.x < 0:
            self.scroll_x(-x)
        if x + self._entry.x + w > self.viewport.width:
            self.scroll_x(self.viewport.width - x - w)

        if y + self._entry.y < 0:
            self.scroll_y(-y)
        if y + self._entry.y + h > self.viewport.height:
            self.scroll_y(self.viewport.height - y - h)


    def entry_get_min_size(self):
        return max(self.min_width, self._entry.display_label.width + self.horizontal_padding), \
               max(self.min_height, self._entry.display_label.height + self.vertical_padding)






class SpinButton(Table):
    """retrieve an integer or floating-point number from the user"""
    padding = 1
    def __init__(self, val = 0, min_val = 0, max_val = 99, **kwargs):
        Table.__init__(self, cols = 2, rows = 2, horizontal_spacing = 2, vertical_spacing = 2, **kwargs)

        self.input = Entry("", draw_border=False)
        self.input.test_value = self._input_test_value
        self.input.connect("on-change", self.on_input_change)
        self.input.fill = True

        self.input.width = 30

        self.up = SpinButtonButton(up=True)
        self.down = SpinButtonButton(up=False)

        #: current value
        self.val = val

        #: minimum allowed value
        self.min_val = min_val

        #: maximum valid value
        self.max_val = max_val

        self.attach(self.input, 0, 1, 0, 2)
        self.attach(self.up, 1, 2, 0, 1)
        self.attach(self.down, 1, 2, 1, 2)

        self.connect_child(self.up, "on-mouse-down", self.on_up_pressed)
        self.connect_child(self.down, "on-mouse-down", self.on_down_pressed)
        self._direction = 0

    def __setattr__(self, name, val):
        Table.__setattr__(self, name, val)
        if name == "val" and val is not None:
            self.input.text = str(val)

    def _input_test_value(self, val):
        try:
            val = int(val)
            return self.min_val <= val <= self.max_val
        except:
            return False

    def on_up_pressed(self, sprite = None, event = None):
        val = self.val + 1 if self.val is not None else 0
        if self._input_test_value(val):
            self.val = val

    def on_down_pressed(self, sprite = None, event = None):
        val = self.val - 1 if self.val is not None else 0

        if self._input_test_value(val):
            self.val = val

    def on_input_change(self, input, val):
        if val:
            self.val = int(val)
        else:
            self.val = None

    def do_render(self):
        self.resize_children()

        self.graphics.rectangle(0.5, 0.5, self.width, self.height, 4)

        self.graphics.move_to(self.up.x - 0.5, 0)
        self.graphics.line_to(self.up.x - 0.5, self.height)

        self.graphics.move_to(self.up.x - 0.5, self.down.y - 0.5)
        self.graphics.line_to(self.width, self.down.y - 0.5)

        self.graphics.stroke("#999")


class SpinButtonButton(Button):
    def __init__(self, up=True, expand=False, width = 15, padding=0, repeat_down_delay = 100, **kwargs):

        Button.__init__(self, expand=expand, width=width, padding=padding,
                        repeat_down_delay=repeat_down_delay, **kwargs)
        self.up = up

    def do_render(self):
        self.graphics.rectangle(0, 0, self.width+1, self.height+1, 3)
        self.graphics.fill("#eee");

        self.graphics.translate((self.width - 5) / 2, (self.height - 2) / 2)

        if self.up:
            self.graphics.move_to(0, 3)
            self.graphics.line_to(3, 0)
            self.graphics.line_to(6, 3)
        else:
            self.graphics.move_to(0, 0)
            self.graphics.line_to(3, 3)
            self.graphics.line_to(6, 0)

        self.graphics.stroke("#000" if self.state in ("highlight", "pressed") else "#444")

########NEW FILE########
__FILENAME__ = image
# - coding: utf-8 -

# Copyright (c) 2011-2012 Media Modifications, Ltd.
# Dual licensed under the MIT or GPL Version 2 licenses.

from gi.repository import Gtk as gtk
from gi.repository import Gdk as gdk
from gi.repository import GdkPixbuf
from gi.repository import GObject as gobject

import cairo
from lib import graphics
from ui import Widget

class Image(Widget):
    """An image widget that can scale smartly. Use slice_* params to control
    how the image scales.
    """


    def __init__(self, path = None, slice_left=0, slice_right=0, slice_top=0, slice_bottom=0, fill = False, **kwargs):
        Widget.__init__(self, fill = fill, **kwargs)

        #: path to the image file
        self.path = path
        self.image_data, self.image_w, self.image_h = None, None, None

        if path:
            self.image_data = cairo.ImageSurface.create_from_png(self.path)
            self.image_w, self.image_h = self.image_data.get_width(), self.image_data.get_height()

        self.min_width, self.min_height = self.min_width or self.image_w, self.min_height or self.image_h

        #: pixels from left that should not be scaled upon image scale
        self.slice_left = slice_left

        #: pixels from right that should not be scaled upon image scale
        self.slice_right = slice_right

        #: pixels from top that should not be scaled upon image scale
        self.slice_top = slice_top

        #: pixels from bottom that should not be scaled upon image scale
        self.slice_bottom = slice_bottom

        self._slices = []
        self._slice()


    def __setattr__(self, name, val):
        Widget.__setattr__(self, name, val)
        if self.__dict__.get(name, "hamster_graphics_no_value_really") == val:
            return

        # reslice when params change
        if name in ("slice_left", "slice_top", "slice_right", "slice_bottom") and hasattr(self, "_slices"):
            self._slice()

        if name == "path" and val and hasattr(self, "image_data"):
            self.image_data = cairo.ImageSurface.create_from_png(val)
            self.image_w, self.image_h = self.image_data.get_width(), self.image_data.get_height()
            self._slice()


    def _slice(self):
        if not self.image_data:
            return

        self._slices = []

        def get_slice(x, y, w, h):
            # we are grabbing bigger area and when painting will crop out to
            # just the actual needed pixels. This is done because otherwise when
            # stretching border, it uses white pixels to blend in
            x, y = x - 1, y - 1
            image = cairo.ImageSurface(cairo.FORMAT_ARGB32, w+2, h+2)
            ctx = cairo.Context(image)
            if isinstance(self.image_data, GdkPixbuf.Pixbuf):
                ctx.set_source_pixbuf(self.image_data, -x, -y)
            else:
                ctx.set_source_surface(self.image_data, -x, -y)

            ctx.rectangle(0, 0, w+2, h+2)
            ctx.fill()
            return image, w, h

        exes = (0, self.slice_left or 0, self.slice_right or self.image_w, self.image_w)
        ys = (0, self.slice_top or 0, self.slice_bottom or self.image_h, self.image_h)
        for y1, y2 in zip(ys, ys[1:]):
            for x1, x2 in zip(exes, exes[1:]):
                self._slices.append(get_slice(x1, y1, x2 - x1, y2 - y1))

    def get_center_bounds(self):
        return (self.slice_left,
                self.slice_top,
                self.width - self.slice_left - (self.image_w - self.slice_right),
                self.height - self.slice_top - (self.image_h - self.slice_bottom))


    def do_render(self):
        if not self.image_data:
            return

        graphics, width, height = self.graphics, self.width, self.height

        def put_pattern(image, x, y, w, h):
            pattern = cairo.SurfacePattern(image[0])

            if w > 0 and h > 0:
                pattern.set_matrix(cairo.Matrix(x0=1, y0=1, xx = (image[1]) / float(w), yy = (image[2]) / float(h)))
                graphics.save_context()
                graphics.translate(x, y)
                graphics.set_source(pattern)
                graphics.rectangle(0, 0, w, h)
                graphics.fill()
                graphics.restore_context()


        # top-left
        put_pattern(self._slices[0], 0, 0, self.slice_left, self.slice_top)


        # top center - repeat width
        put_pattern(self._slices[1],
                    self.slice_left, 0,
                    width - self.slice_left - self.slice_right, self.slice_top)

        # top-right
        put_pattern(self._slices[2], width - self.slice_right, 0, self.slice_left, self.slice_top)


        # left - repeat height
        put_pattern(self._slices[3],
                    0, self.slice_top,
                    self.slice_left, height - self.slice_top - self.slice_bottom)

        # center - repeat width and height
        put_pattern(self._slices[4],
                    self.slice_left, self.slice_top,
                    width - self.slice_left - self.slice_right,
                    height - self.slice_top - self.slice_bottom)

        # right - repeat height
        put_pattern(self._slices[5],
                    width - self.slice_right, self.slice_top,
                    self.slice_right, height - self.slice_top - self.slice_bottom)

        # bottom-left
        put_pattern(self._slices[6], 0, height - self.slice_top, self.slice_left, self.slice_top)

        # bottom center - repeat width
        put_pattern(self._slices[7],
                    self.slice_left, height - self.slice_bottom,
                    width - self.slice_left - self.slice_right, self.slice_bottom)

        # bottom-right
        put_pattern(self._slices[8],
                    width - self.slice_right, height - self.slice_top,
                    self.slice_right, self.slice_top)

        graphics.rectangle(0, 0, width, height)
        graphics.new_path()

########NEW FILE########
__FILENAME__ = listitem
# - coding: utf-8 -

# Copyright (c) 2011-2012 Media Modifications, Ltd.
# Dual licensed under the MIT or GPL Version 2 licenses.

from gi.repository import Gtk as gtk
from gi.repository import Gdk as gdk
from gi.repository import GObject as gobject

from ui import Widget, Label, TreeModel, TreeModelRow, Entry, VBox, HBox, Button, ScrollArea, Fixed
from lib import graphics
from bisect import bisect
from gi.repository import Pango as pango

class Renderer(Widget):
    x_align = 0   #: horizontal alignment of the cell contents
    y_align = 0.5 #: vertical alignment of the cell contents

    def __init__(self, editable = False, **kwargs):
        Widget.__init__(self, **kwargs)
        self.editable = editable

        self._target = None
        self._cell = None

    def get_min_size(self, row):
        return max(self.min_width or 0, 10), max(self.min_height or 0, 10)

    def get_mouse_cursor(self):
        return False

    def show_editor(self, target, cell, event = None):
        pass

    def hide_editor(self):
        pass

    def set_data(self, data):
        pass

    def restore_data(self):
        pass

class ImageRenderer(Renderer):
    def __init__(self, **kwargs):
        Renderer.__init__(self, **kwargs)

    def render(self, context, w, h, data, state, enabled):
        if data:
            context.save()
            context.translate((w - data.width) * self.x_align, (h - data.height) * self.y_align)
            data._draw(context)
            context.restore()



class LabelRenderer(Renderer):
    padding = 5
    expand = True

    color = "#333" #: font color
    color_current = "#fff" #: font color when the row is selected

    color_disabled = "#aaa" #: color of the text when item is disabled
    color_disabled_current = "#fff" #: selected row font color when item is disabled

    def __init__(self, **kwargs):
        Renderer.__init__(self, **kwargs)
        self.label = Label(padding = self.padding, overflow = pango.EllipsizeMode.END)
        self.label.graphics = self.graphics
        self._prev_dict = {}

        self._editor = Entry()


    def __setattr__(self, name, val):
        Widget.__setattr__(self, name, val)
        if name.startswith("padding") and hasattr(self, "label"):
            setattr(self.label, name, val)

    def get_min_size(self, row):
        return max(self.min_width or 0, 10), max(self.min_height or 0, self.label.vertical_padding + 15)

    def get_mouse_cursor(self):
        if self.editable:
            return gdk.CursorType.XTERM
        return False

    def show_editor(self, target, cell, event = None):
        if not self.editable:
            return

        self._target, self._cell = target, cell
        target.add_child(self._editor)

        self._editor.x, self._editor.y = cell['x'], cell['y']
        self._editor.alloc_w, self._editor.alloc_h = cell['width'], cell['height']
        self._editor.text = cell['data']

        if event:
            event.x, event.y = self._editor.from_scene_coords(event.x, event.y)
            self._editor._Entry__on_mouse_down(self._editor, event)
        self._target = target
        self._editor.grab_focus()

    def hide_editor(self):
        if self._target:
            self._target.remove_child(self._editor)
            self._target.rows[self._cell['row']][self._cell['col']] = self._editor.text
            self._target = self._cell = None

    def set_data(self, data):
        # apply data to the renderer
        self._prev_dict = {}
        if isinstance(data, dict):
            for key, val in data.iteritems():
                self._prev_dict[key] = getattr(self.label, key, "") #store original state
                setattr(self.label, key, val)
        else:
            self.label.text = data

    def restore_data(self):
        # restore renderer's data representation to the original state
        for key, val in self._prev_dict.iteritems():
            setattr(self.label, key, val)


    def render(self, context, w, h, data, state, enabled=True):
        self.label.alloc_w = w
        if enabled:
            self.label.color = self.color_current if state == "current" else self.color
        else:
            self.label.color = self.color_disabled_current if state == "current" else self.color_disabled

        context.save()
        context.translate((w - self.label.width) * self.x_align, (h - self.label.height) * self.y_align)
        self.label._draw(context)
        context.restore()



class ListView(Widget):
    """a widget for displaying selection lists"""
    __gsignals__ = {
        "on-select": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
        "on-change": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
    }

    #: renderer classes that get initiated upon listitem construction
    renderers = [LabelRenderer]

    padding = 5

    background_current = "#7AA1D2" #: color of the selected row
    background_current_disabled = "#ddd"   #: background of disabled row
    background_hover =  "#efefef"  #: color of the mouse hovered row
    background_odd =  ""           #: background of the odd rows. Set to None to avoid painting
    background_even = "#f9f9f9"    #: background of the even rows. Set to None to avoid painting

    tooltip_position = "mouse"

    def __init__(self, rows = [], renderers = None,
                 select_on_drag = False, spacing=0,
                 row_height = None, **kwargs):
        Widget.__init__(self, **kwargs)
        self.interactive, self.can_focus = True, True
        self.mouse_cursor = False

        #: should an item be select upon drag motion. By default select happens
        #: only when clicking
        self.select_on_drag = select_on_drag

        #: the list of text strings available for selection
        self.rows = rows

        #: row height in pixels. if specified, will be using that instead of
        #: asking cell renderers. defaults to None.
        self.row_height = row_height

        self._search_string = ""
        self._search_timeout = None

        self._row_pos = None # cache of row positions

        self._hover_row = None

        #: currently selected item
        self.current_row = None


        if renderers is not None:
            self.renderers = renderers
        else:
            self.renderers = [renderer() for renderer in self.renderers]

        self.connect("on-mouse-move", self.__on_mouse_move)
        self.connect("on-mouse-down", self.__on_mouse_down)
        self.connect("on-mouse-out", self.__on_mouse_out)


        self.connect("on-mouse-scroll", self.on_mouse_scroll)
        self.connect("on-double-click", self.on_doubleclick)
        self.connect("on-key-press", self.__on_key_press)

        self.connect("on-render", self.__on_render)


    def __setattr__(self, name, val):
        new_rows = False
        if name == "rows":
            if isinstance(val, TreeModel) == False:
                val = TreeModel(val)

            if getattr(self, "rows", None):
                for listener in getattr(self, "_data_change_listeners", []):
                    self.rows.disconnect(listener)
            if getattr(self, "rows", None):
                new_rows = True
            self.queue_resize()

        row_changed = name == "current_row" and val != self.__dict__.get(name, 'hamster_no_value_really')
        Widget.__setattr__(self, name, val)

        if new_rows:
            self._on_row_deleted(self.rows)

        if row_changed:
            self.emit("on-change", val if val else None)

        if name == "rows":
            changed = self.rows.connect("row-changed", self._on_row_changed)
            deleted = self.rows.connect("row-deleted", self._on_row_deleted)
            inserted = self.rows.connect("row-inserted", self._on_row_inserted)
            self._data_change_listeners = [changed, deleted, inserted]
        elif name == "padding":
            for renderer in self.renderers:
                renderer.padding = val
        elif name == "current_row" and val:
            self.scroll_to_row(val)

    @property
    def current_index(self):
        """returns index of the current row, or -1 if no row is selected"""
        if not self.rows or not self.current_row:
            return -1
        return self.rows.index(self.current_row)

    def get_min_size(self):
        if not self.rows:
            return 0, 0

        # ask for 10 * <wherever the last row is> + height
        w = 0
        for renderer in self.renderers:
            renderer_w, renderer_h = renderer.get_min_size(None)
            w += renderer_w

        return w, self._get_row_pos()[-1] + self.get_row_height()

    def get_col_at_x(self, x):
        col_x, mouse_cursor = 0, False
        for renderer, width in zip(self.renderers, self._get_col_widths()):
            if col_x <= x <= col_x + width:
                return renderer
            col_x += width


    def select(self, row):
        """select row. accepts either the row object or the label of it's first column"""
        if isinstance(row, TreeModelRow):
            self.current_row = row
            return

        # otherwise go for search
        for row in self.rows:
            if row[0] == row:
                self.current_row = row
                return

    def __on_mouse_move(self, sprite, event):
        if not self.rows:
            return

        self._hover_row = self.rows[self.get_row_at_y(event.y)]
        if self.select_on_drag and gdk.ModifierType.BUTTON1_MASK & event.state:
            self.current_row = self._hover_row

        # determine mouse cursor
        col = self.get_col_at_x(event.x)
        if col:
            self.mouse_cursor = col.get_mouse_cursor()


    def __on_mouse_down(self, sprite, event):
        if not self.rows:
            return

        self.current_row = self.rows[self.get_row_at_y(event.y)]
        for renderer in self.renderers:
            renderer.hide_editor()

        cell = self.get_cell(event.x, event.y)

        event.x, event.y = self.to_scene_coords(event.x, event.y)
        cell['renderer'].show_editor(self, cell, event)

    def __on_mouse_out(self, sprite):
        self._hover_row = None

    def select_cell(self, row_num, col_num):
        if not self.enabled:
            return

        self.grab_focus()
        self.current_row = self.rows[row_num]
        if 0 < col_num < len(self.renderers):
            if self.renderers[col_num].editable:
                col_x = 0
                for i, w in enumerate(self._get_col_widths()):
                    if i == col_num:
                        break
                    col_x += w

                # somewhat a mad way to get the cell data for editor
                cell = self.get_cell(col_x + 1,
                                     row_num * self.get_row_height() + 1)

                self.renderers[col_num].show_editor(self, cell)

    def get_cell(self, x, y):
        """get row number, col number, renderer, and extents"""

        target_renderer = self.get_col_at_x(x)

        col_x = 0
        for col, width in zip(self.renderers, self._get_col_widths()):
            if col == target_renderer:
                break
            col_x += width

        row = self.get_row_at_y(y)
        col = self.renderers.index(target_renderer)

        row_height = self.get_row_height()

        return {
            'data': self.rows[row][col],
            'renderer': target_renderer,
            'row': row,
            'col': col,
            'x': col_x,
            'y': self.get_row_position(self.rows[row]),
            'width': width,
            'height': row_height
        }



    def on_mouse_scroll(self, sprite, event):
        direction  = 1 if event.direction == gdk.ScrollDirection.DOWN else -1
        parent = self.parent
        while parent and hasattr(parent, "vscroll") == False:
            parent = parent.parent

        y = self.y if hasattr(self.parent.parent, "vscroll") else self.parent.y

        if parent:
            parent.scroll_y(y - parent.step_size * direction)


    def _get_col_widths(self):
        """determine column widths and minimum row height"""
        widths = []

        remaining_space = self.width
        interested_cols = []
        for renderer in self.renderers:
            remaining_space = remaining_space - renderer.get_min_size(None)[0]

            if renderer.expand:
                interested_cols.append(renderer)

        # in order to stay pixel sharp we will recalculate remaining bonus
        # each time we give up some of the remaining space
        bonus = 0
        if remaining_space > 0 and interested_cols:
            bonus = int(remaining_space / len(interested_cols))

        for renderer in self.renderers:
            w = renderer.get_min_size(None)[0]
            if renderer in interested_cols:
                w += bonus

                interested_cols.remove(renderer)
                remaining_space -= bonus
                if interested_cols:
                    bonus = int(float(remaining_space) / len(interested_cols))

            widths.append(w)

        return widths

    def get_row_height(self):
        row_height = self.row_height or 0
        if not row_height:
            for renderer in self.renderers:
                row_height = max(row_height, renderer.get_min_size(None)[1])
        return row_height

    def get_visible_range(self):
        """returns index of the first and last row visible"""
        # suboptimal workaround for case when the list is packed in a vbox and then in a scrollbox
        # TODO - generalize and sniff out the actual crop area
        if self.parent and self.parent.parent and self.parent.parent and isinstance(self.parent.parent.parent, ScrollArea):
            scrollbox = self.parent.parent
            list_y = self.y + self.parent.y
        else:
            list_y = self.y
            scrollbox = self.parent

        row_height = self.get_row_height()
        first_row = int(-list_y / row_height)
        last_row = int((-list_y + scrollbox.height) / row_height)

        return max(first_row, 0), min(last_row + 1, len(self.rows))


    def _draw(self, context, opacity=1, *args, **kwargs):

        self.get_visible_range()

        col_widths = self._get_col_widths()
        width = self.width

        row_height = self.get_row_height()

        g = graphics.Graphics(context)

        x, y = 0, 0
        Widget._draw(self, context, opacity, *args, **kwargs)
        editor = None

        # suboptimal workaround for case when the list is packed in a vbox and then in a scrollbox
        # TODO - generalize and sniff out the actual crop area
        if self.parent and self.parent.parent and self.parent.parent and isinstance(self.parent.parent.parent, ScrollArea):
            scrollbox = self.parent.parent
            list_y = self.y + self.parent.y
        else:
            list_y = self.y
            scrollbox = self.parent

        g.rectangle(0, 0, scrollbox.width, scrollbox.height)
        g.clip()

        for row_idx in range(*self.get_visible_range()):
            y = row_idx * row_height
            row = self.rows[row_idx]


            state = "normal"
            if row == self.current_row:
                state = "current"
            elif row == self._hover_row:
                state = "highlight"

            context.save()
            context.translate(x, y + self.y)
            context.rectangle(0, 0, width, row_height)

            self.paint_row_background(g, row_idx, state, self.enabled)
            context.clip()

            col_x = 0
            for i, (data, renderer, col_width) in enumerate(zip(row, self.renderers, col_widths)):
                renderer.set_data(data)
                renderer.render(context, col_width, row_height, row[i], state, self.enabled)
                renderer.restore_data()
                context.translate(col_width, 0)

                # TODO - put some place else
                if renderer._cell and hasattr(renderer, "_editor") and renderer._cell['col'] == i:
                    renderer._editor.x, renderer._editor.alloc_w = col_x, col_width - 1
                    editor = renderer._editor

                col_x += col_width

            context.restore()


        if editor:
            # repaint editor as it is stepped all over
            context.save()
            context.translate(0, self.y)
            editor._draw(context, parent_matrix = self.get_matrix())
            context.restore()


    def paint_row_background(self, graphics, row_idx, state, enabled=True):
        """this function fills row background. the rectangle has been already
        drawn, so all that is left is fill. The graphics property is instance
        of graphics.Graphics for the current context, and state is one of
        normal, highlight and current"""
        if self.background_hover and state == "highlight" and self.enabled:
            graphics.fill_preserve(self.background_hover)
        elif self.background_current and state == "current" and self.enabled:
            graphics.fill_preserve(self.background_current)
        elif self.background_current_disabled and state == "current" and not self.enabled:
            graphics.fill_preserve(self.background_current_disabled)
        elif row_idx % 2 == 1 and self.background_even:
            graphics.fill_preserve(self.background_even)
        elif row_idx % 2 == 0 and self.background_odd:
            graphics.fill_preserve(self.background_odd)


    def _get_row_pos(self):
        if self._row_pos:
            return self._row_pos
        row_height = self.get_row_height()

        w, h, pos = 0, 0, []
        for row in self.rows:
            pos.append(h)
            h = h + row_height

        self._row_pos = pos

        return pos

    def get_row_at_y(self, y):
        return bisect(self._get_row_pos(), y) - 1

    def get_row_position(self, row):
        if row in self.rows:
            return self._get_row_pos()[self.rows.index(row)]
        return 0

    def on_doubleclick(self, sprite, event):
        if self.current_row:
            self.emit("on-select", self.current_row)

    def _on_row_changed(self, model, row_idx):
        self._row_pos = None
        if self.parent:
            self.parent.queue_resize()

    def _on_row_deleted(self, model):
        if self.current_row and self.current_row not in self.rows:
            self.current_row = None
        if self._hover_row and self._hover_row not in self.rows:
            self._hover_row = None

        self._row_pos = None
        self.parent.queue_resize()

    def _on_row_inserted(self, row_idx):
        self._row_pos = None
        self.parent.queue_resize()

    def __on_key_press(self, sprite, event):
        if self.current_row:
            idx = self.rows.index(self.current_row)
        else:
            idx = -1

        if event.keyval == gdk.KEY_Down:
            idx = min(idx + 1, len(self.rows) - 1)
        elif event.keyval == gdk.KEY_Up:
            idx = max(idx - 1, 0)
        elif event.keyval == gdk.KEY_Home:
            idx = 0
        elif event.keyval == gdk.KEY_End:
            idx = len(self.rows) - 1
        elif event.keyval == gdk.KEY_Return:
            self.emit("on-select", self.current_row)

        elif event.string:
            if self._search_timeout: # cancel the previous one!
                gobject.source_remove(self._search_timeout)
            self._search_string += event.string

            def clear_search():
                self._search_string = ""

            self._search_timeout = gobject.timeout_add(500, clear_search)
            idx = self.find(self._search_string, fragment=True)


        if 0 <= idx < len(self.rows):
            self.current_row = self.rows[idx]



    def find(self, label, fragment = False):
        """looks for a label in the list item. starts from current position including.
           if does not find anything, will wrap around.
           if an item matches, will select it.
        """
        start = self.rows.index(self.current_row) if self.current_row else None
        i = start + 1 if start is not None and start + 1 < len(self.rows) else 0

        def label_matches(row, label):
            row_label = self.rows[i][0]
            if isinstance(row_label, dict):
                row_label = row_label.get("text", pango.parse_markup(row_label.get("markup", ""), -1, "0")[2])
            if fragment:
                return row_label.lower().startswith(label.lower())
            else:
                return row_label.lower() == label.lower()

        while i != start:
            if label_matches(self.rows[i], label):
                return i

            i += 1
            if i >= len(self.rows):
                i = 0
                if start == None:
                    break

        # checking if we have wrapped around (so this is the only match
        if label_matches(self.rows[i], label):
            return i

        return -1


    def scroll_to_row(self, label):
        # find the scroll area if any and scroll where the row is
        parent = self.parent
        while parent and hasattr(parent, "vscroll") == False:
            parent = parent.parent

        if not parent:
            return

        area, viewport = parent, parent.viewport
        label_y = self.get_row_position(label)

        label_h = 0

        # if parent has not been allocated height yet, there is something funky going on
        # TODO - demistify
        if self.parent.height > 0:
            for renderer in self.renderers:
                label_h = max(label_h, renderer.get_min_size(label)[1])

        y = 0 if hasattr(self.parent.parent, "vscroll") else self.y
        if label_y + self.y + self.parent.y < 0:
            area.scroll_y(-label_y - y)

        if label_y + label_h + self.y + self.parent.y > parent.height:
            area.scroll_y(-label_y - label_h - y + parent.height)


    def __on_render(self, widget):
        # mark that the whole thing can be interacted with
        self.graphics.rectangle(0, 0, self.width, self.height)
        self.graphics.new_path()


class ListHeader(Fixed):
    padding = 0
    def __init__(self, expand=False, **kwargs):
        Fixed.__init__(self, expand=expand, **kwargs)
        self.connect("on-render", self.__on_render)

    def get_min_size(self):
        w, h = self.min_width or 0, self.min_height or 0
        for widget in self.sprites:
            min_w, min_h = widget.get_min_size()
            w = w + min_w
            h = max(h, min_h)
        return w, h

    def size_cols(self, col_widths):
        if not self.visible:
            return

        x = 0
        for i, w, in enumerate(col_widths):

            if i >= len(self.sprites):
                break

            self.sprites[i].x = x
            self.sprites[i].alloc_w = min(w, self.width - x)
            self.sprites[i].alloc_h = self.height
            x += w

    def __on_render(self, widget):
        if not self.parent:
            return

        # TODO - wrong control distribution, but the headers are lagging one
        # step behind in width otherwise

        if hasattr(self.parent, "list_view"):
            list_view = self.parent.list_view
        else:
            list_view = self.parent.parent.parent.parent.list_view

        self.size_cols(list_view._get_col_widths())

class ListHeaderCol(Button):
    x_align = 0

    def __init__(self, text):
        Button.__init__(self, text)
        self.color = "#444"
        self.get_min_size = lambda: (0, Label.get_min_size(self)[1])

    def do_render(self):
        if self.state == "normal":
            self.graphics.fill_area(0, 0, self.width, self.height, "#EDECEB")
        else:
            Button.do_render(self)


class ListItem(VBox):
    """a list view with headers and an optional scroll when rows don't fit"""
    __gsignals__ = {
        "on-select": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
        "on-change": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
        "on-header-click": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT, gobject.TYPE_PYOBJECT,)),
    }

    fixed_headers = True

    class_headers_container = ListHeader #: list headers container class
    class_header_col = ListHeaderCol #: list headers column class
    class_list_view = ListView #: list view class
    class_scroll_area = ScrollArea #: scroll area class


    def __init__(self, rows = [], renderers = None, headers = None,
                 select_on_drag = False, spacing = 0, scroll_border = 1,
                 row_height = None, fixed_headers = None, **kwargs):
        VBox.__init__(self, **kwargs)

        self.list_view = self.class_list_view(rows=rows)
        self.list_view.connect("on-render", self._on_list_render)

        for event in ("on-select", "on-change", "on-mouse-down",
                      "on-mouse-up", "on-click"):
            self.list_view.connect(event, self._forward_event, event)


        if renderers is not None:
            self.renderers = renderers
        self.select_on_drag = select_on_drag
        self.spacing = spacing
        self.row_height = row_height

        self.header_container = self.class_headers_container()
        self.headers = headers

        if fixed_headers is not None:
            self.fixed_headers = fixed_headers

        self.scrollbox = self.class_scroll_area(border = scroll_border)

        if self.fixed_headers:
            self.scrollbox.add_child(self.list_view)
            self.add_child(self.header_container, self.scrollbox)
        else:
            self.scrollbox.add_child(VBox([self.header_container, self.list_view], spacing=0))
            self.add_child(self.scrollbox)

    def __setattr__(self, name, val):
        # forward useful attributes to the list view
        if name in ("rows", "renderers", "select_on_drag", "spacing",
                    "row_height", "current_row", "_hover_row"):
            setattr(self.list_view, name, val)
            return


        if self.__dict__.get(name, 'hamster_no_value_really') == val:
            return
        VBox.__setattr__(self, name, val)


        if name == "scroll_border":
            self.scrollbox.border = val
        elif name == "headers":
            self._update_headers()

    def __getattr__(self, name):
        if name in ("rows", "renderers", "select_on_drag", "spacing",
                    "row_height", "current_row", "_hover_row",
                    "current_index", "_hover_row", "grab_focus",
                    "select_cell", "rows"):
            return getattr(self.list_view, name)

        if name in self.__dict__:
            return self.__dict__.get(name)
        else:
            raise AttributeError, "ListItem has no attribute '%s'" % name


    def resize_children(self):
        self.scrollbox.alloc_w = self.width
        self.scrollbox.resize_children()
        self.scrollbox.viewport.resize_children()
        VBox.resize_children(self)


    def get_list_size(self):
        return self.list_view.width, self.list_view.height

    def _update_headers(self):
        self.header_container.clear()
        for header in self.headers or []:
            if isinstance(header, basestring):
                header = self.class_header_col(header)
            self.header_container.add_child(header)
            self.header_container.connect_child(header, "on-click", self._on_header_clicked)
        self.header_container.size_cols(self.list_view._get_col_widths())

    def _on_list_render(self, list):
        self.header_container.size_cols(self.list_view._get_col_widths())

    def _on_header_clicked(self, header_col, event):
        self.emit("on-header-click", header_col, event)

    def _forward_event(self, list, info, event_name):
        self.emit(event_name, info)

########NEW FILE########
__FILENAME__ = menu
# - coding: utf-8 -

# Copyright (c) 2011-2012 Media Modifications, Ltd.
# Dual licensed under the MIT or GPL Version 2 licenses.

from gi.repository import Gtk as gtk
from gi.repository import Gdk as gdk
from gi.repository import GObject as gobject

from ui import Widget, Box, Bin, Label, Button

class Menu(Box):
    """menu contains menuitems. menuitems can contain anything they want

    **Signals**:

    **selected** *(sprite, selected_item)*
    - fired when a menu item is selected.
    """
    __gsignals__ = {
        "selected": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT, gobject.TYPE_PYOBJECT)),
    }

    def __init__(self, contents = None, padding = 1, horizontal = False, owner = None,
                 open_on_hover = None, spacing = 0, hide_on_leave = False, hide_on_interstitial = False,
                 disable_toggling = False, **kwargs):
        Box.__init__(self, contents = contents, padding = padding, horizontal = horizontal, spacing = spacing, **kwargs)
        self.expand, self.expand_vert = False, False
        self.x_align = 0

        #: in case of a sub menu - a menu item that this menu belongs to
        self.owner = owner

        #: if specified, will open submenus menu after cursor has been over the item for the specified seconds
        self.open_on_hover = open_on_hover

        #: if set, will hide the menu when mouse moves out. defaults to False
        self._hide_on_leave = hide_on_leave

        #: if set, will hide the menu when mouse moves between menuitems.  defaults to False
        self._hide_on_interstitial = hide_on_interstitial

        #: if set, clicking on menu items with submenus will only show them instead of toggling
        #: this way the menu becomes more persistent
        self.disable_toggling = disable_toggling

        self._toggled = False
        self._scene_mouse_down = None
        self._scene_mouse_move = None
        self._scene_key_press = None
        self._echo = False

        self._timeout = None
        self.connect("on-render", self.__on_render)
        self.connect("on-mouse-down", self.__on_mouse_down)
        self.interactive = True


    def __setattr__(self, name, val):
        if name == "hide_on_leave":
            name = "_hide_on_leave"
        Box.__setattr__(self, name, val)

    @property
    def hide_on_leave(self):
        res = self._hide_on_leave
        owner = self.owner
        while owner and self.owner.parent:
            res = res or self.owner.parent._hide_on_leave
            owner = owner.parent.owner
        return res


    def add_child(self, *sprites):
        for sprite in sprites:
            Box.add_child(self, sprite)
            self.connect_child(sprite, "on-click", self.on_item_click)
            self.connect_child(sprite, "on-mouse-down", self.on_item_mouse_down)
            self.connect_child(sprite, "on-mouse-over", self.on_item_mouse_over)
            self.connect_child(sprite, "on-mouse-out", self.on_item_mouse_out)
        self.resize_children()

    def get_min_size(self):
        w, h = Box.get_min_size(self)
        if self.orient_horizontal:
            return w, h
        else:
            # for vertical ones give place to the submenu indicator
            return w + 8, h

    def __on_mouse_down(self, item, event):
        if self._toggled:
            self.collapse_submenus()
            self._toggled = False

    def on_item_mouse_down(self, item, event):
        self._on_item_mouse_down( item, event )

    def _on_item_mouse_down(self, item, event ):
        self._echo = True

        if not item.menu or self.disable_toggling == False:
            self._toggled = not self._toggled
        else:
            self._toggled = True

        if item.menu:
            if self._toggled:
                item.show_menu()
            else:
                item.hide_menu()
        self._on_item_mouse_over(item)


        # only top menu will be watching so we don't get anarchy and such
        if self.owner is None and not self._scene_mouse_down:
            self._scene_mouse_down = self.get_scene().connect_after("on-mouse-down", self.on_scene_mouse_down)
            self._scene_mouse_move = self.get_scene().connect_after("on-mouse-move", self.on_scene_mouse_move)

    def on_scene_mouse_down(self, scene, event):
        if self._scene_mouse_down and self._echo == False:
            ours = False
            for menu in list(self.get_submenus()) + [self]:
                ours = ours or (menu.parent and menu.check_hit(event.x, event.y))
                if ours:
                    break

            if not ours:
                self.collapse_submenus()
                self._toggled = False
        self._echo = False

    def on_scene_mouse_move(self, scene, event):

        ours = False
        for menu in [menu for menu in self.get_submenus() if menu.parent] + [self]:
            in_menu = menu.check_hit(event.x, event.y)
            if in_menu:
                if menu._hide_on_interstitial:
                    for item in menu.sprites:
                        ours = ours or (item.visible and item.check_hit(event.x, event.y))
                        if ours:
                            break
                else:
                    ours = True
            else:
                if menu.hide_on_leave:
                    #check if you are in your owner menu... don't be hasty
                    if not menu.owner or ( menu.owner and not menu.owner.check_hit(event.x, event.y) ):
                        ours = False
                        break
                else:
                    ours = True

            if ours:
                break

        if not ours:
            self.collapse_submenus()
            self._toggled = False

    @property
    def mnemonic_items(self):
        # returns list of all items that have mnemonics
        for menu in ([self] + list(self.get_submenus())):
            for item in menu.traverse("mnemonic"):
                if item.mnemonic:
                    yield item

    def get_submenus(self):
        """return a flattened list of submenus of this menu"""
        for item in self.sprites:
            if item.menu:
                yield item.menu
                for submenu in item.menu.get_submenus():
                    yield submenu

    def collapse_submenus(self):
        """collapses all sub menus, if there are any"""
        scene = self.get_scene()
        for menu in self.get_submenus():
            if menu.parent == scene:
                scene.remove_child(menu)

        for item in self.sprites:
            item.selected = False

        if self._scene_mouse_down:
            scene.disconnect(self._scene_mouse_down)
            scene.disconnect(self._scene_mouse_move)
            self._scene_mouse_down = None
            self._scene_mouse_move = None


    def on_item_click(self, item, event):
        if self._timeout:
            gobject.source_remove(self._timeout)

        if item.menu:
            return

        top_menu = item.parent
        while top_menu.owner:
            top_menu = top_menu.owner.parent

        for menuitem in top_menu.sprites:
            menuitem.selected = False
            menuitem.hide_menu()
        top_menu._toggled = False

        top_menu.emit("selected", item, event)

        #if you open on hover and you are still there.. open back up
        if not self.owner and self.open_on_hover:
            self._on_item_mouse_over( item )

    def on_item_mouse_over(self, item):
        self._on_item_mouse_over(item)

    def _on_item_mouse_over(self, item):
        for menuitem in self.sprites:
            menuitem.selected = False

        cursor, mouse_x, mouse_y, mods = item.get_scene().get_window().get_pointer()

        if self.open_on_hover and not self._toggled and not gdk.ModifierType.BUTTON1_MASK & mods:
            # show menu after specified seconds. we are emulating a click
            def show_menu():
                self._on_item_mouse_down(item, None)
                self._echo = False

            if self._timeout:
                gobject.source_remove(self._timeout)
            self._timeout = gobject.timeout_add(int(self.open_on_hover * 1000), show_menu)



        if self._toggled:
            item.selected = True
            # hide everybody else
            scene = self.get_scene()
            for sprite in self.sprites:
                if sprite.menu and sprite.menu.parent == scene:
                    sprite.menu._toggled = False
                    sprite.hide_menu()

            # show mine
            if item.menu:
                item.show_menu()
                item.menu._toggled = True

                # deal with going up the tree - hiding submenus and selected items
                for subitem in item.menu.sprites:
                    subitem.selected = False
                    if subitem.menu:
                        subitem.hide_menu()

    def on_item_mouse_out(self, sprite):
        if self._timeout:
            gobject.source_remove(self._timeout)
        self._timeout = None


    def __on_render(self, sprite):
        """if we are place with an offset, make sure the mouse still thinks
        it belongs to us (draw an invisible rectangle from parent till us"""
        if self.owner:
            x_offset, y_offset = self.owner.submenu_offset_x, self.owner.submenu_offset_y
        else:
            x_offset, y_offset = 0, 0

        self.graphics.rectangle(-x_offset, -y_offset,
                                self.width + x_offset, self.height + y_offset)
        self.graphics.new_path()


    def do_render(self):
        if self.owner:
            w, h = self.width, self.height
        else:
            w, h = self.width, self.height

        self.graphics.set_line_style(width = 1)
        self.graphics.rectangle(0.5, 0.5, w-1, h-1)
        self.graphics.fill_stroke("#eee", "#ddd")


class MenuItem(Button):
    """a menu item that can also own a menu"""

    secondary_label_class = Label
    def __init__(self, menu = None, padding = 5, submenu_offset_x = 2, submenu_offset_y = 2,
                 x_align = 0, y_align = 0.5, pressed_offset = 0,
                 secondary_label = "", mnemonic = "", **kwargs):
        Button.__init__(self, padding=padding, pressed_offset = pressed_offset, x_align = x_align, y_align = y_align, **kwargs)

        self.expand = False

        #: submenu of the item
        self.menu = menu

        self.selected = False

        #: if specified will push the submeny by the given pixels
        self.submenu_offset_x = submenu_offset_x

        #: if specified will push the submeny by the given pixels
        self.submenu_offset_y = submenu_offset_y

        #: the secondary label element
        self.secondary_display_label = self.secondary_label_class("",
                                                                  color = "#666",
                                                                  fill=True,
                                                                  x_align=1,
                                                                  padding_right = 5,
                                                                  visible = True)
        self.container.add_child(self.secondary_display_label)

        #: text of the secondary label that is placed to the right of the primary
        self.secondary_label = secondary_label

        #: keypress that can also triger activation of this menu item
        #: This is string in for "Key+Key+Key". For example: "Shift+c"
        self.mnemonic = mnemonic

        self.connect("on-mnemonic-activated", self.on_mnemonic_activated)


    def _position_contents(self):
        Button._position_contents(self)
        if hasattr(self, "secondary_display_label"):
            self.container.add_child(self.secondary_display_label)


    def __setattr__(self, name, val):
        if name == "menu":
            # make sure we re-parent also the submenu
            if getattr(self, "menu", None):
                self.menu.owner = None
            if val:
                val.owner = self
        elif name == "secondary_label":
            self.secondary_display_label.text = val
            if val:
                self.container.fill = self.secondary_display_label.visible = True
            else:
                self.container.fill = self.secondary_display_label.visible = False
            return
        elif name == "mnemonic":
            # trample over the secondary label. one can set it back if wants
            self.secondary_label = val

        Button.__setattr__(self, name, val)

    def on_mnemonic_activated(self, sprite, event):
        self._do_click(None)

    def show_menu(self):
        """display submenu"""
        if not self.menu: return

        self.menu.fill = False # submenus never fill to avoid stretching the whole screen

        scene = self.get_scene()
        scene.add_child(self.menu)
        self.menu.x, self.menu.y = self.to_scene_coords()
        self.menu.x += self.submenu_offset_x
        self.menu.y += self.submenu_offset_y
        #todo: this assumes the menuitems in this menu will pop down left || top aligned.. need to make a flag
        if self.parent.orient_horizontal:
            self.menu.y += self.height
        else:
            self.menu.x += self.width


    def hide_menu(self):
        """hide submenu"""
        if not self.menu: return

        for item in self.menu.sprites:
            if item.menu:
                item.hide_menu()

        scene = self.get_scene()
        if scene and self.menu in scene.sprites:
            scene.remove_child(self.menu)


    def do_render(self):
        selected = self.selected or self.state == "pressed"
        if selected:
            self.graphics.rectangle(0, 0, self.width, self.height)
            self.graphics.fill("#4A90D9")


        self.color = "#fff" if selected else "#333"

        # add submenu indicators
        if self.menu and self.parent and self.parent.orient_horizontal == False:
            self.graphics.move_to(self.width - 7, self.height / 2.0 - 3)
            self.graphics.line_to(self.width - 4, self.height / 2.0)
            self.graphics.line_to(self.width - 7, self.height / 2.0 + 3)

            self.graphics.stroke("#fff" if self.selected else "#999")


class MenuSeparator(Widget):
    """A simple menu item that is not selectable and is rendered as a separator"""
    spacing = 1
    def __init__(self, spacing=None, **kwargs):
        Widget.__init__(self)
        if spacing:
            self.spacing = spacing
        self.menu = None

    def get_min_size(self):
        if self.parent and self.parent.orient_horizontal:
            return self.spacing * 2 + 1, 1
        else:
            return 1, self.spacing * 2 + 1

    def do_render(self):
        self.graphics.rectangle(0, 0, self.width, self.height)
        self.graphics.new_path()

        if self.parent and self.parent.orient_horizontal:
            x = round(self.width / 2.0) - 0.5
            self.graphics.move_to(x, 0)
            self.graphics.line_to(x, self.height)
            self.graphics.stroke("#ccc")

            self.graphics.move_to(x+1, 0)
            self.graphics.line_to(x+1, self.height)
            self.graphics.stroke("#fff")
        else:
            y = round(self.height / 2.0) - 0.5
            self.graphics.move_to(0, y)
            self.graphics.line_to(self.width, y)
            self.graphics.stroke("#ccc")

            self.graphics.move_to(0, y+1)
            self.graphics.line_to(self.width, y+1)
            self.graphics.stroke("#fff")

########NEW FILE########
__FILENAME__ = notebook
# - coding: utf-8 -

# Copyright (c) 2011-2012 Media Modifications, Ltd.
# Dual licensed under the MIT or GPL Version 2 licenses.

import math

import cairo
from gi.repository import Gtk as gtk
from gi.repository import Gdk as gdk
from gi.repository import GObject as gobject

from lib import graphics
from ui import Label, Container, Table, Box, HBox, Viewport, ToggleButton, Group, ScrollButton, Bin

class Notebook(Box):
    """Container that allows grouping children in tab pages"""

    __gsignals__ = {
        "on-tab-change": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
    }

    #: class to use for constructing the overflow buttons that appear on overflow
    scroll_buttons_class = ScrollButton

    #: class for the wrapping container
    tabbox_class = HBox

    #: class for the pages container
    pages_container_class = Container


    def __init__(self, labels = None, tab_position="top", tab_spacing = 0,
                 scroll_position = None, show_scroll = "auto", scroll_selects_tab = True, **kwargs):
        Box.__init__(self, horizontal=False, spacing=0, **kwargs)

        #: list of tabs in the order of appearance
        self.tabs = []

        #: list of pages in the order of appearance
        self.pages = []

        #: container of the pages
        self.pages_container = self.pages_container_class(padding=1)

        #: container of tabs. useful if you want to adjust padding/placement
        self.tabs_container = Group(fill=False, spacing=tab_spacing)
        self.tabs_container.on_mouse_over = lambda button: False  # ignore select-on-drag

        # viewport so that tabs don't go out of their area
        self._tabs_viewport = Viewport()
        self._tabs_viewport.get_min_size = self._tabs_viewport_get_min_size
        self._tabs_viewport.resize_children = self._tabs_viewport_resize_children
        self._tabs_viewport.add_child(self.tabs_container)

        #: wether scroll buttons should select next/previos tab or show the
        #: next/previos tab out of the view
        self.scroll_selects_tab = scroll_selects_tab

        #: container for custom content before tabs
        self.before_tabs = HBox(expand=False)

        #: container for custom content after tabs
        self.after_tabs = HBox(expand=False)

        #: button to scroll tabs back
        self.tabs_back = self.scroll_buttons_class("left",
                                                   expand=False,
                                                   visible=False,
                                                   enabled=False,
                                                   repeat_down_delay = 150)
        self.tabs_back.connect("on-mouse-down", self.on_back_press)

        #: button to scroll tabs forward
        self.tabs_forward = self.scroll_buttons_class("right",
                                                      expand=False,
                                                      visible=False,
                                                      enabled=False,
                                                      repeat_down_delay = 150)
        self.tabs_forward.connect("on-mouse-down", self.on_forward_press)


        #: the wrapping container that holds also the scroll buttons and everyting
        self.tabbox = self.tabbox_class(expand = False, expand_vert = False)
        self.tabbox.get_min_size = self.tabbox_get_min_size
        self.tabbox.get_height_for_width_size = self.tabbox_get_height_for_width_size


        self.tabbox.add_child(self.before_tabs, self.tabs_back,
                              self._tabs_viewport,
                              self.tabs_forward, self.after_tabs)

        #: current page
        self.current_page = 0

        #: tab position: top, right, bottom, left and combinations: "top-right", "left-bottom", etc.
        self.tab_position = tab_position


        for label in labels or []:
            self.add_page(label)

        #: where to place the scroll buttons on tab overflow. one of "start"
        #: (both at the start), "end" (both at the end) or "around" (on left
        #: and right of the tabs)
        self.scroll_position = scroll_position

        #: determines when to show scroll buttons. True for always, False for
        #: never, "auto" for auto appearing and disappearing, and
        #: "auto_invisible" for going transparent instead of disappearing
        #: (the latter avoids tab toggle)
        self.show_scroll = show_scroll



    def __setattr__(self, name, val):
        if name == "tab_spacing":
            self.tabs_container.spacing = val
        else:
            if name == "current_page":
                val = self.find_page(val)

            if self.__dict__.get(name, "hamster_graphics_no_value_really") == val:
                return
            Box.__setattr__(self, name, val)

            if name == "tab_position" and hasattr(self, "tabs_container"):
                self.tabs_container.x = 0
                self._position_contents()

            elif name == "scroll_position":
                # reorder sprites based on scroll position
                if val == "start":
                    sprites = [self.before_tabs, self.tabs_back, self.tabs_forward, self._tabs_viewport, self.after_tabs]
                elif val == "end":
                    sprites = [self.before_tabs, self._tabs_viewport, self.tabs_back, self.tabs_forward, self.after_tabs]
                else:
                    sprites = [self.before_tabs, self.tabs_back, self._tabs_viewport, self.tabs_forward, self.after_tabs]
                self.tabbox.sprites = sprites
            elif name == "current_page":
                self._select_current_page()


    def add_page(self, tab, contents = None, index = None):
        """inserts a new page with the given label
        will perform insert if index is specified. otherwise will append the
        new tab to the end.
        tab can be either a string or a widget. if it is a string, a
        ui.NootebookTab will be created.

        Returns: added page and tab
        """
        if isinstance(tab, basestring):
            tab = NotebookTab(tab)

        tab.attachment = "bottom" if self.tab_position.startswith("bottom") else "top"
        self.tabs_container.connect_child(tab, "on-mouse-down", self.on_tab_down)

        page = Container(contents, visible=False)
        page.tab = tab
        self.pages_container.connect_child(page, "on-render", self.on_page_render)

        if index is None:
            self.tabs.append(tab)
            self.pages.append(page)
            self.tabs_container.add_child(tab)
            self.pages_container.add_child(page)
        else:
            self.tabs.insert(index, tab)
            self.pages.insert(index, page)
            self.tabs_container.insert(index, tab)
            self.pages_container.insert(index, tab)


        self.current_page = self.current_page or page
        self._position_contents()

        if self.get_scene():
            self.tabs_container.queue_resize()
            self.tabbox.resize_children()

        return page, tab


    def remove_page(self, page):
        """remove given page. can also pass in the page index"""
        page = self.find_page(page)
        if not page:
            return

        idx = self.pages.index(page)

        self.pages_container.remove_child(page)
        del self.pages[idx]

        self.tabs_container.remove_child(self.tabs[idx])
        del self.tabs[idx]

        if page == self.current_page:
            self.current_page = idx

        self.tabs_container.resize_children()
        self._position_contents()


    def find_page(self, page):
        """find page by index, tab label or tab object"""
        if not self.pages:
            return None

        if page in self.pages:
            return page
        elif isinstance(page, int):
            page = min(len(self.pages)-1, max(page, 0))
            return self.pages[page]
        elif isinstance(page, basestring) or isinstance(page, NotebookTab):
            for i, tab in enumerate(self.tabs):
                if tab == page or tab.label == page:
                    found_page = self.pages[i]
                    return found_page
        return None

    def _select_current_page(self):
        self.emit("on-tab-change", self.current_page)

        if not self.current_page:
            return

        self.tabs[self.pages.index(self.current_page)].toggle()
        for page in self.pages:
            page.visible = page == self.current_page

        self.current_page.grab_focus()


    def scroll_to_tab(self, tab):
        """scroll the tab list so that the specified tab is visible
        you can pass in the tab object, index or label"""
        if isinstance(tab, int):
            tab = self.tabs[tab]

        if isinstance(tab, basestring):
            for target_tab in self.tabs:
                if target_tab.label == tab:
                    tab = target_tab
                    break

        if self.tabs_container.x + tab.x < 0:
            self.tabs_container.x = -tab.x
        elif self.tabs_container.x + tab.x + tab.width > self._tabs_viewport.width:
            self.tabs_container.x = -(tab.x + tab.width - self._tabs_viewport.width) - 1
        self._position_tabs()


    """resizing and positioning"""
    def resize_children(self):
        Box.resize_children(self)

        pos = self.tab_position
        horizontal = pos.startswith("right") or pos.startswith("left")
        if horizontal:
            self.tabbox.alloc_w, self.tabbox.alloc_h = self.tabbox.alloc_h, self.tabbox.alloc_w

        if pos.startswith("right"):
            self.tabbox.x += self.tabbox.height
        elif pos.startswith("left"):
            self.tabbox.y += self.tabbox.width


        # show/hide thes croll buttons
        # doing it here to avoid recursion as changing visibility calls parent resize
        self.tabs_back.visible = self.tabs_forward.visible = self.show_scroll in (True, "auto_invisible")
        self.tabbox.resize_children()
        self.tabs_container.resize_children()


        if self.show_scroll == "auto_invisible":
            self.tabs_back.visible = self.tabs_forward.visible = True
            if self.tabs_container.width < self._tabs_viewport.width:
                self.tabs_back.opacity = self.tabs_forward.opacity = 0
            else:
                self.tabs_back.opacity = self.tabs_forward.opacity = 1

        else:
            self.tabs_back.opacity = self.tabs_forward.opacity = 1
            self.tabs_back.visible = self.tabs_forward.visible = self.show_scroll is True or \
                                                                (self.show_scroll == "auto" and \
                                                                 self.tabs_container.width > self._tabs_viewport.width)

        self.tabbox.resize_children()
        self._position_tabs()



    def tabbox_get_min_size(self):
        w, h = HBox.get_min_size(self.tabbox)
        return h, h

    def tabbox_get_height_for_width_size(self):
        w, h = HBox.get_min_size(self.tabbox)

        if self.tab_position.startswith("right") or self.tab_position.startswith("left"):
            w, h = h, w

        return w, h

    def _tabs_viewport_get_min_size(self):
        # viewport has no demands on size, so we ask the tabs container
        # when positioned on top, tell that we need at least the height
        # when on the side tell that we need at least the width
        w, h = self.tabs_container.get_min_size()
        return 50, h


    def _tabs_viewport_resize_children(self):
        # allow x_align to take effect only if tabs fit.
        x = max(self.tabs_container.x, self._tabs_viewport.width - self.tabs_container.width - 1)

        Bin.resize_children(self._tabs_viewport)

        if self.tabs_container.width > self._tabs_viewport.width:
            self.tabs_container.x = x

        self._position_tabs()


    """utilities"""
    def _position_tabs(self):
        if self.scroll_selects_tab and self.current_page:
            tab = self.current_page.tab
            if self.tabs_container.x + tab.x + tab.width > self._tabs_viewport.width:
                self.tabs_container.x = -(tab.x + tab.width - self._tabs_viewport.width)
            elif self.tabs_container.x + tab.x < 0:
                self.tabs_container.x = -tab.x


        # find first good tab if we all don't fit
        if self.tabs_container.width > self._tabs_viewport.width:
            for tab in self.tabs:
                if tab.x + self.tabs_container.x >= 0:
                    self.tabs_container.x = -tab.x
                    break

        # update opacity so we are not showing partial tabs
        for tab in self.tabs:
            if self.tabs_container.x + tab.x < 0 or self.tabs_container.x + tab.x + tab.width > self._tabs_viewport.width:
                tab.opacity = 0
            else:
                tab.opacity = 1


        # set scroll buttons clickable
        if self.scroll_selects_tab:
            self.tabs_back.enabled = self.current_page and self.pages.index(self.current_page) > 0
            self.tabs_forward.enabled = self.current_page and self.pages.index(self.current_page) < len(self.pages) - 1
        else:
            self.tabs_back.enabled = self.tabs_container.x  < -self.tabs_container.padding_left
            self.tabs_forward.enabled = self.tabs_container.x + self.tabs_container.width > self._tabs_viewport.width


    def _position_contents(self):
        attachment, alignment = self.tab_position or "top", "left"
        if "-" in self.tab_position:
            attachment, alignment = self.tab_position.split("-")

        self.orient_horizontal = attachment in ("right", "left")

        if alignment == "center":
            self.tabs_container.x_align = 0.5
        elif alignment in ("right", "bottom"):
            self.tabs_container.x_align = 1
        else:
            self.tabs_container.x_align = 0

        # on left side the rotation is upside down
        if attachment == "left":
            self.tabs_container.x_align = 1 - self.tabs_container.x_align

        if attachment == "bottom":
            self.tabs_container.y_align = 0
        else:
            self.tabs_container.y_align = 1

        for tab in self.tabs:
            tab.attachment = attachment

        self.clear()
        if attachment == "right":
            self.add_child(self.pages_container, self.tabbox)
            self.tabbox.rotation = math.pi / 2
        elif attachment == "left":
            self.add_child(self.tabbox, self.pages_container)
            self.tabbox.rotation = -math.pi / 2
        elif attachment == "bottom":
            self.add_child(self.pages_container, self.tabbox)
            self.tabbox.rotation = 0
        else: # defaults to top
            self.add_child(self.tabbox, self.pages_container)
            self.tabbox.rotation = 0


        for tab in self.tabs:
            tab.pivot_x = tab.width / 2
            tab.pivot_y = tab.height / 2

            tab.container.pivot_x = tab.container.width / 2
            tab.container.pivot_y = tab.container.height / 2
            if attachment == "bottom":
                tab.rotation = math.pi
                tab.container.rotation = math.pi
            else:
                tab.rotation = 0
                tab.container.rotation = 0


            if tab.force_vertical_image and tab.image:
                tab.image.pivot_x = tab.image.width / 2
                tab.image.pivot_y = tab.image.height / 2

                if attachment == "right":
                    tab.image.rotation = -math.pi / 2
                elif attachment == "left":
                    tab.image.rotation = math.pi / 2
                else:
                    tab.image.rotation = 0

        self.queue_resize()


    """mouse events"""
    def on_back_press(self, button, event):
        if self.scroll_selects_tab:
            if self.pages.index(self.current_page) > 0:
                self.current_page = self.pages.index(self.current_page) - 1
        else:
            # find the first elem before 0:
            for tab in reversed(self.tabs):
                if self.tabs_container.x + tab.x < 0:
                    self.tabs_container.x = -tab.x
                    break
        self._position_tabs()


    def on_forward_press(self, button, event):
        if self.scroll_selects_tab:
            if self.pages.index(self.current_page) < len(self.pages):
                self.current_page = self.pages.index(self.current_page) + 1
        else:
            if self.tabs_container.x + self.tabs_container.width > self._tabs_viewport.width:
                # find the first which doesn't fit:
                found = None
                for tab in self.tabs:
                    if self.tabs_container.x + tab.x + tab.width > self._tabs_viewport.width:
                        found = True
                        break

                if found:
                    self.tabs_container.x = -(tab.x + tab.width - self._tabs_viewport.width) - 1
            else:
                self.tabs_container.x = -(self.tabs_container.width - self._tabs_viewport.width)
        self._position_tabs()

    def on_tab_down(self, tab, event):
        self.current_page = tab


    """rendering"""
    def on_page_render(self, page):
        page.graphics.rectangle(0, 0, page.width, page.height)
        page.graphics.clip()

    def do_render(self):
        self.graphics.set_line_style(width = 1)

        x, y, w, h = (self.pages_container.x + 0.5,
                      self.pages_container.y + 0.5,
                      self.pages_container.width-1,
                      self.pages_container.height-1)

        self.graphics.rectangle(x, y, w, h)
        self.graphics.fill_stroke("#fafafa", "#999")


class NotebookTab(ToggleButton):
    padding = 5
    def __init__(self, label="", attachment = "top", pressed_offset = 0, **kwargs):
        ToggleButton.__init__(self, label=label, pressed_offset = pressed_offset, **kwargs)
        self.attachment = attachment

        self.interactive = True

        self.force_vertical_image = True

    def do_render(self):
        x, y, x2, y2 = 0.5, 0.5, self.width, self.height

        self._rounded_line([(x, y2), (x, y), (x2, y), (x2, y2)], 4)

        if self.toggled:
            self.graphics.fill_stroke("#fafafa", "#999")
        elif self.state == "highlight":
            self.graphics.fill_stroke("#ddd", "#999")
        else:
            self.graphics.fill_stroke("#ccc", "#999")

########NEW FILE########
__FILENAME__ = scroll
# - coding: utf-8 -

# Copyright (c) 2011-2012 Media Modifications, Ltd.
# Dual licensed under the MIT or GPL Version 2 licenses.

from gi.repository import Gtk as gtk
from gi.repository import Gdk as gdk
from gi.repository import GObject as gobject

from lib import graphics
from ui import Widget, Table, Box, Viewport, Button
import math

class ScrollArea(Table):
    """Container that will display scroll bars (either horizontal or vertical or
    both) if the space occupied by child is larger than the available.
    """

    #: scroll step size in pixels
    step_size = 30

    def __init__(self, contents=None, border=1, step_size=None,
                 scroll_horizontal="auto", scroll_vertical="auto",
                 **kwargs):
        Table.__init__(self, rows=2, cols=2, padding=[border, 0, 0, border], **kwargs)

        self.viewport = Viewport(x_align=0, y_align=0)
        self.interactive, self.can_focus = True, True

        if step_size:
            self.step_size = step_siz

        #: with of the surrounding border in pixels
        self.border = border

        #: visibility of the horizontal scroll bar. True for always, False for never and "auto" for auto
        self.scroll_horizontal = scroll_horizontal

        #: visibility of the vertical scroll bar. True for always, False for never and "auto" for auto
        self.scroll_vertical = scroll_vertical

        #even if we are don't need the scrollbar, do we reserve space for it?
        self.reserve_space_vertical = False
        self.reserve_space_horizontal = False


        #: vertical scroll bar widget
        self.vscroll = ScrollBar()

        #: horizontal scroll bar widget
        self.hscroll = ScrollBar(horizontal = True)

        self.attach(self.viewport, 0, 1, 0, 1)
        self.attach(self.vscroll, 1, 2, 0, 1)
        self.attach(self.hscroll, 0, 1, 1, 2)


        if contents:
            if isinstance(contents, graphics.Sprite):
                contents = [contents]

            for sprite in contents:
                self.add_child(sprite)

        self.connect("on-mouse-scroll", self.__on_mouse_scroll)
        for bar in (self.vscroll, self.hscroll):
            self.connect_child(bar, "on-scroll", self.on_scroll)
            self.connect_child(bar, "on-scroll-step", self.on_scroll_step)
            self.connect_child(bar, "on-scroll-page", self.on_scroll_page)


    def __setattr__(self, name, val):
        Table.__setattr__(self, name, val)
        if name in ("scroll_horizontal", "scroll_vertical"):
            self.queue_resize()

    def add_child(self, *sprites):
        for sprite in sprites:
            if sprite in (self.viewport, self.vscroll, self.hscroll):
                Table.add_child(self, sprite)
            else:
                self.viewport.add_child(*sprites)

    def get_min_size(self):
        return self.min_width or 0, self.min_height or 0

    def resize_children(self):
        # give viewport all our space
        w, h = self.viewport.alloc_w, self.viewport.alloc_w
        self.viewport.alloc_w = self.width - self.horizontal_padding
        self.viewport.alloc_h = self.height - self.vertical_padding

        # then check if it fits
        area_w, area_h = self.viewport.get_container_size()
        hvis = self.scroll_horizontal is True or (self.scroll_horizontal == "auto" and self.width < area_w)
        if hvis:
            if self.reserve_space_horizontal:
                self.hscroll.opacity = 1
            else:
                self.hscroll.visible = True
        else:
            if self.reserve_space_horizontal:
                self.hscroll.opacity = 0
            else:
                self.hscroll.visible = False
        vvis = self.scroll_vertical is True or (self.scroll_vertical == "auto" and self.height < area_h)
        if vvis:
            if self.reserve_space_vertical:
                self.vscroll.opacity = 1
            else:
                self.vscroll.visible = True
        else:
            if self.reserve_space_vertical:
                self.vscroll.opacity = 0
            else:
                self.vscroll.visible = False

        Table.resize_children(self)


        if self.viewport.child:
            self.scroll_x(self.viewport.child.x)
            self.scroll_y(self.viewport.child.y)


    def _scroll_y(self, y):
        # these are split into two to avoid echoes
        # check if we have anything to scroll
        area_h = self.viewport.get_container_size()[1]
        viewport_h = self.viewport.height

        if y < 0:
            y = max(y, viewport_h - area_h)
        y = min(y, 0)
        self.viewport.child.y = y

    def scroll_y(self, y):
        """scroll to y position"""
        self._scroll_y(y)
        self._update_sliders()

    def _scroll_x(self, x):
        area_w = self.viewport.get_container_size()[0]
        viewport_w = self.viewport.width
        if not viewport_w:
            return

        # when window grows pull in the viewport if it's out of the bounds
        if x < 0:
            x = max(x, viewport_w - area_w)
        x = min(x, 0)

        self.viewport.child.x = x

    def scroll_x(self, x):
        """scroll to x position"""
        self._scroll_x(x)
        self._update_sliders()


    def _update_sliders(self):
        area_w, area_h = self.viewport.get_container_size()
        area_w = area_w or 1 # avoid division by zero
        area_h = area_h or 1

        if self.vscroll.visible:
            v_aspect = min(float(self.viewport.height) / area_h, 1)
            self.vscroll.size = min(float(self.viewport.height) / area_h, 1)

            if v_aspect == 1:
                self.vscroll.offset = 0
            else:
                self.vscroll.offset = -1 * self.viewport.child.y / (area_h * (1 - v_aspect))

        if self.hscroll.visible:
            h_aspect = min(float(self.viewport.width) / area_w, 1)
            self.hscroll.size = min(float(self.viewport.width) / area_w, 1)
            if h_aspect == 1:
                self.hscroll.offset = 0
            else:
                self.hscroll.offset = -1 * self.viewport.child.x / (area_w * (1 - h_aspect))


    """events"""
    def __on_mouse_scroll(self, sprite, event):
        direction  = 1 if event.direction == gdk.ScrollDirection.DOWN else -1
        self.scroll_y(self.viewport.child.y - self.step_size * direction)

    def on_scroll(self, bar, offset):
        area_w, area_h = self.viewport.get_container_size()
        viewport_w, viewport_h = self.viewport.width, self.viewport.height

        if bar == self.vscroll:
            aspect = float(area_h - viewport_h) / area_h
            self._scroll_y(-1 * (area_h * aspect) * offset)
        else:
            aspect = float(area_w - viewport_w) / area_w
            self._scroll_x(-1 * (area_w * aspect) * offset)

    def on_scroll_step(self, bar, direction):
        if bar == self.vscroll:
            self.scroll_y(self.viewport.child.y - self.step_size * direction)
        else:
            self.scroll_x(self.viewport.child.x - self.step_size * direction)

    def on_scroll_page(self, bar, direction):
        if bar == self.vscroll:
            self.scroll_y(self.viewport.child.y - (self.viewport.height + self.step_size) * direction)
        else:
            self.scroll_x(self.viewport.child.y - (self.viewport.width + self.step_size) * direction)


    def do_render(self):
        if self.border:
            self.graphics.rectangle(0.5, 0.5, self.width, self.height)
            self.graphics.set_line_style(width=self.border)
            stroke_color = "#333" if self.focused else "#999"
            self.graphics.fill_stroke("#fff", stroke_color)
        else:
            self.graphics.rectangle(0, 0, self.width, self.height)
            self.graphics.fill("#fff")



class ScrollBar(Box):
    """A scroll bar.

    **Signals**:

    **on-scroll** *(sprite, current_normalized_position)*
    - fired after scrolling.
    """
    __gsignals__ = {
        "on-scroll": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
        "on-scroll-step": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
        "on-scroll-page": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
    }

    #: thickness of the bar in pixels
    thickness = 20

    def __init__(self, horizontal = False, thickness = None, size = 0, offset = 0, **kwargs):
        Box.__init__(self, **kwargs)
        self.interactive, self.cursor = True, False

        self.spacing = 0

        self.thickness = thickness if thickness else self.thickness

        #: whether the scroll bar is vertical or horizontal
        self.orient_horizontal = horizontal

        #: width of the bar in pixels
        self.size = size

        #: scroll position in range 0..1
        self.offset = offset

        if horizontal:
            self.expand_vert = False
            self.min_height = thickness
        else:
            self.expand = False
            self.min_width = thickness

        #: slider container
        self.slider_zone = Widget()

        #: slider widget
        self.slider = ScrollBarSlider()
        self.slider_zone.add_child(self.slider)

        #: the scroll up button
        self.up = ScrollBarButton(direction="left" if self.orient_horizontal else "up")

        #: the scroll down button
        self.down = ScrollBarButton(direction="right" if self.orient_horizontal else "down")

        self.add_child(self.up, self.slider_zone, self.down)

        self._timeout = None

        for button in (self.up, self.down):
            self.connect_child(button, "on-mouse-down", self.on_scrollbutton_pressed)
            self.connect_child(button, "on-mouse-up", self.on_scrollbutton_released)
            self.connect_child(button, "on-mouse-out", self.on_scrollbutton_released)

        self.connect_child(self.slider, "on-drag", self.on_slider_drag)
        self.connect("on-click", self.on_click)


    def get_min_size(self):
        return self.thickness, self.thickness

    def resize_children(self):
        Box.resize_children(self)
        self._size_slider()


    def _size_slider(self):
        if self.orient_horizontal:
            self.slider.alloc_h = self.slider_zone.alloc_h
            size = max(self.slider_zone.width * self.size, self.slider_zone.height)
            if self.slider_zone.width < self.slider_zone.height:
                size = self.slider_zone.width
            self.slider.width = round(size)
        else:
            self.slider.alloc_w = self.slider_zone.alloc_w
            size = max(self.slider_zone.height * self.size, self.slider_zone.width)
            if self.slider_zone.height < self.slider_zone.width:
                size = self.slider_zone.height
            self.slider.height = round(size)
        self._position_slider()


    def __setattr__(self, name, val):
        if self.__dict__.get(name, "hamster_graphics_no_value_really") == val:
            return

        Box.__setattr__(self, name, val)

        if name == "orient_horizontal" and hasattr(self, "up"):
            self.up.direction="left" if val else "up"
            self.down.direction="right" if val else "down"
        elif name == "size" and hasattr(self, "slider"):
            self._size_slider()
        elif name == "offset" and hasattr(self, "slider_zone"):
            self._position_slider()

    def _position_slider(self):
        if self.orient_horizontal:
            size = max(self.slider_zone.width - self.slider.width, 1)
            self.slider.x = size * self.offset
        else:
            size = max(self.slider_zone.height - self.slider.height, 1)
            self.slider.y = size * self.offset


    def on_slider_drag(self, slider, event):
        if self.orient_horizontal:
            size = max(self.slider_zone.width - self.slider.width, 0)
            self.slider.y = 0
            self.slider.x = int(max(min(self.slider.x, size), 0))
            self.__dict__['offset'] = self.slider.x / size if size > 0 else 0
        else:
            size = max(self.slider_zone.height - self.slider.height, 0)
            self.slider.x = 0
            self.slider.y = int(max(min(self.slider.y, size), 0))
            self.__dict__['offset'] = self.slider.y / size if size > 0 else 0


        self.emit("on-scroll", self.offset)


    def on_scrollbutton_pressed(self, button, event = None):
        if self._timeout: return  #something's going on already

        # scroll right away and set a timeout to come again after 50 milisecs
        self._emit_scroll(button)
        self._timeout = gobject.timeout_add(100, self._emit_scroll, button)

    def on_scrollbutton_released(self, button, event = None):
        if self._timeout:
            gobject.source_remove(self._timeout)
            self._timeout = None

    def _emit_scroll(self, button):
        direction = -1 if button == self.up else 1
        self.emit("on-scroll-step", direction)
        return True

    def on_click(self, sprite, event):
        direction = -1 if event.y < self.slider.y else 1
        self.emit("on-scroll-page", direction)


    def do_render(self):
        self.graphics.rectangle(0, 0, self.width, self.height)
        if self.enabled:
            self.graphics.fill("#D6D4D2")
        else:
            self.graphics.fill("#eee")


class ScrollBarSlider(Button):
    def __init__(self, padding = 0, **kwargs):
        Button.__init__(self, padding = padding, **kwargs)
        self.draggable = True
        self.expand = False
        self.connect("on-drag", self.on_drag)

    def on_drag(self, sprite, event):
        if self.enabled == False:
            self.x, self.y = self.drag_x, self.drag_y
            return

    def do_render(self):
        if self.parent.parent.orient_horizontal:
            self.graphics.rectangle(0.5, 1.5, self.width - 1, self.height - 3, 2)
        else:
            self.graphics.rectangle(1.5, 0.5, self.width - 3, self.height - 1, 2)

        self.graphics.fill_stroke("#fff", "#a8aca8")



class ScrollBarButton(Button):
    def __init__(self, padding = 0, direction = "up", **kwargs):
        Button.__init__(self, padding = padding, **kwargs)
        self.expand = False

        #: button direction - one of "up", "down", "left", "right"
        self.direction = direction

    def get_min_size(self):
        # require a square
        dimension = self.alloc_w if self.direction in ("up", "down") else self.alloc_h
        return (dimension, dimension)


    def do_render(self):
        self.graphics.set_line_style(1)

        self.graphics.rectangle(1.5, 1.5, self.width - 3, self.height - 3, 2)
        self.graphics.fill_stroke("#fff", "#a8aca8")


        self.graphics.save_context()
        self.graphics.translate(7.5, 9.5)

        if self.direction == "left":
            self.graphics.rotate(-math.pi / 2)
            self.graphics.translate(-4, 0)
        elif self.direction == "right":
            self.graphics.rotate(math.pi / 2)
            self.graphics.translate(-1, -4)
        elif self.direction == "down":
            self.graphics.rotate(math.pi)
            self.graphics.translate(-6, -3)


        self.graphics.move_to(0, 3)
        self.graphics.line_to(3, 0)
        self.graphics.line_to(6, 3)

        if self.enabled:
            self.graphics.stroke("#333")
        else:
            self.graphics.stroke("#aaa")

        self.graphics.restore_context()

########NEW FILE########
__FILENAME__ = slider
# - coding: utf-8 -

# Copyright (c) 2011-2012 Media Modifications, Ltd.
# Dual licensed under the MIT or GPL Version 2 licenses.

from gi.repository import Gtk as gtk
from gi.repository import Gdk as gdk
from gi.repository import GObject as gobject

from lib import graphics
from ui import Widget, Button, Fixed

class SliderGrip(Button):
    width = 20
    def __init__(self, **kwargs):
        Button.__init__(self, **kwargs)
        self.padding = 0
        self.margin = 0
        self.draggable = True
        self.connect("on-drag-finish", self.__on_drag_finish)

    def do_render(self):
        w, h = self.width, self.height
        self.graphics.rectangle(0.5, 0.5, int(w), int(h), 3)
        self.graphics.fill_stroke("#999", "#333")

    def __on_drag_finish(self, sprite, event):
        # re-trigger the state change as we override it in the set_state
        self._on_scene_mouse_up(self, event)

    def _set_state(self, state):
        if state == self.state:
            return

        if state == "normal":
            scene = self.get_scene()
            if scene._drag_sprite == self:
                state = "pressed"


        self.state = state
        self.emit("on-state-change", self.state)




class SliderSnapPoint(Widget):
    def __init__(self, value, label = None, **kwargs):
        Widget.__init__(self, **kwargs)

        #: value
        self.value = value

        #: label
        self.label = label


    def do_render(self):
        self.graphics.move_to(0.5, 0)
        self.graphics.line_to(0.5, self.height)
        self.graphics.stroke("#555")



class Slider(Fixed):
    """ a slider widget that allows the user to select a value by dragging
    a slider along a rail

    **Signals**:

    **on-change** *(sprite, val)*
    - fired when the current value of the widget is changed. brings the new
    current value with the event.
    """


    #: class for the slidergrip
    slidergrip_class = SliderGrip

    #: class for the slidersnappoint
    slidersnappoint_class = SliderSnapPoint

    __gsignals__ = {
        "on-change": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
    }
    def __init__(self, values = [], selection = None,
                 snap_to_ticks = True, range = False, grips_can_cross = True,
                 snap_points = None, snap_distance = 20, inverse = False,
                 snap_on_release = False, **kwargs):
        Fixed.__init__(self, **kwargs)

        self.scale_width = 10.5

        #: list of available items. It can be list of either strings or numbers
        #: for number ranges use the python `range <http://docs.python.org/library/functions.html#range>`_ generator.
        self.values = values

        #: Possible values: [True, "start", "end"]. When set to true will add
        #: second handler to select range.
        #: if "start" the selection range will be from start till current position
        #: if "end", the selection range will be from current position till end
        #: Defaults is False which means that a single value is selected instead
        self.range = range

        #: if set to true, the selection will be painted on the outer range
        self.inverse = inverse

        #: should the slider snap to the exact tick position
        self.snap_to_ticks = snap_to_ticks

        self._snap_sprites = []
        #: list of specially highlighted points
        self.snap_points = snap_points

        #: distance in pixels at which the snap points should start attracting
        self.snap_distance = snap_distance

        #: Normally the grip snaps to the snap points when dragged.
        #: This changes behaviour so that dragging is free, but upon release,
        #: if a snap point is in the distance, snaps to that.
        self.snap_on_release = snap_on_release

        #: works for ranges. if set to False, then it won't be possible to move
        #: start grip after end grip and vice versa
        self.grips_can_cross = grips_can_cross

        self._prev_value = None

        self.start_grip = self.slidergrip_class( )
        self.end_grip = self.slidergrip_class(visible = range == True)

        for grip in (self.start_grip, self.end_grip):
            self.connect_child(grip, "on-drag", self.on_grip_drag)
            self.connect_child(grip, "on-drag-finish", self.on_grip_drag_finish)

        self.add_child(self.start_grip, self.end_grip)

        self._selection = selection

        self._mark_selection = True

        self.connect("on-render", self.__on_render)


    def __setattr__(self, name, val):
        if name == 'selection':
            name = "_selection"
            self._mark_selection = True

        if self.__dict__.get(name, "hamster_graphics_no_value_really") == val:
            return


        Fixed.__setattr__(self, name, val)
        if name == 'range' and hasattr(self, "end_grip"):
            self.end_grip.visible = val == True
        elif name in ("alloc_w", "min_width") and hasattr(self, "range"):
            self._adjust_grips()
        elif name == "snap_points":
            self._rebuild_snaps()
        elif name == "_selection":
            self._adjust_grips()


    def resize_children(self):
        self.start_grip.alloc_h = self.end_grip.alloc_h = self.scale_width
        self.start_grip.y = self.end_grip.y = self.padding_top

        for snap in self._snap_sprites:
            snap.x = (self.width - self.end_grip.width) * float(self.values.index(snap.value)) / (len(self.values) - 1) + self.start_grip.width / 2
            snap.y = self.start_grip.y + self.start_grip.height + 3
            snap.alloc_h = self.height - self.padding_bottom - snap.y

        # XXX - resize children should not be called when dragging
        if self.get_scene() and self.get_scene()._drag_sprite not in (self.start_grip, self.end_grip):
            self._adjust_grips()


    def get_min_size(self):
        w, h = self.start_grip.width * 3, self.scale_width
        if self.snap_points:
            h = h * 2
        return int(w), int(h)


    @property
    def selection(self):
        """current selection"""
        # make sure that in case of range start is always lower than end
        res = self._selection
        if self.range is True:
            start, end = res
            if start > end:
                start, end = end, start
            return (start, end)
        else:
            return res


    def _rebuild_snaps(self):
        self.remove_child(*(self._snap_sprites))
        self._snap_sprites = []
        if self.snap_points is not None:
            for point in self.snap_points:
                snap_sprite = self.slidersnappoint_class(point)
                self.add_child(snap_sprite)
                self._snap_sprites.append(snap_sprite)


    def _adjust_grips(self):
        """position grips according to their value"""
        start_x, end_x = self.start_grip.x, self.end_grip.x
        if self.range is True:
            start_val, end_val = self.selection or (None, None)
        else:
            start_val, end_val = self.selection, None

        if start_val is not None:
            self.start_grip.x = (self.width - self.start_grip.width) * float(self.values.index(start_val)) / (len(self.values) - 1)

        if end_val is not None:
            self.end_grip.x = (self.width - self.end_grip.width) * float(self.values.index(end_val)) / (len(self.values) - 1)

        if start_x != self.start_grip.x or end_x != self.end_grip.x:
            self._sprite_dirty = True


    def _snap_grips(self, grip):
        """move grips to the snap points if any snap point is in the proximity"""
        prev_pos = grip.x

        candidates = []
        grip_x = grip.x + grip.width / 2
        for snap in self._snap_sprites:
            if abs(grip_x - snap.x) < self.snap_distance:
                candidates.append((snap, abs(grip_x - snap.x)))

        if candidates:
            closest, proximity = list(sorted(candidates, key=lambda cand:cand[1]))[0]
            grip.x = closest.x - grip.width / 2

        if prev_pos != grip.x:
            self._update_selection(grip)
            self._sprite_dirty = True

    def _update_selection(self, grip = None):
        pixels = float(self.width - self.start_grip.width - self.horizontal_padding)

        start_val, end_val = None, None

        if self.range is True:
            if grip in (None, self.start_grip):
                normalized = (self.start_grip.x - self.padding_left) / pixels # get into 0..1
                pos = int(normalized * (len(self.values) - 1))
                start_val = self.values[pos]
            else:
                start_val = self.selection[0] if self.start_grip.x < self.end_grip.x else self.selection[1]


            if grip in (None, self.end_grip):
                normalized = (self.end_grip.x - self.padding_left) / pixels # get into 0..1
                pos = int(normalized * (len(self.values) - 1))
                end_val = self.values[pos]
            else:
                end_val = self.selection[1] if self.start_grip.x < self.end_grip.x else self.selection[0]
        else:
            normalized = (self.start_grip.x - self.padding_left) / pixels # get into 0..1
            pos = int(normalized * (len(self.values) - 1))
            start_val = self.values[pos]


        if self.range is True:
            selection = (start_val, end_val)
        else:
            selection = start_val

        self.__dict__['_selection'] = selection # avoid echoing

        if self._prev_value != selection:
            self._prev_value = selection
            self.emit("on-change", self.selection)




    def on_grip_drag(self, grip, event):
        if self.enabled is False or self.interactive is False:
            grip.x, grip.y = grip.drag_x, grip.drag_y
            return

        grip.y = self.padding_top

        if grip == self.start_grip:
            min_x, max_x = self.padding_left, self.width - grip.width - self.padding_right
        else:
            min_x, max_x = self.padding_left, self.width - grip.width - self.padding_right

        grip.x = min(max(grip.x, min_x), max_x)


        if not self.snap_on_release:
            self._snap_grips(grip)

        if self.range is True and self.grips_can_cross == False:
            if grip == self.start_grip:
                grip.x = min(grip.x, self.end_grip.x - 1)
            else:
                grip.x = max(grip.x, self.start_grip.x + 1)


        if self.snap_to_ticks:
            pixels = float(self.width - self.start_grip.width - self.horizontal_padding)
            normalized = (grip.x - self.padding_left) / float(pixels) # get into 0..1
            pos = int(normalized * (len(self.values) - 1))
            # restrict just to tick position
            grip.x = min_x + (max_x - min_x) * (float(pos) / (len(self.values) - 1))

        self._update_selection(grip)
        self._sprite_dirty = True # dragging grips changes fill and we paint the fill

    def on_grip_drag_finish(self, grip, event):
        if self.snap_on_release:
            self._snap_grips(grip)


    def __on_render(self, sprite):
        if self._mark_selection:
            self._adjust_grips()
            self._mark_selection = False

    def do_render(self):
        scale_h = int(self.scale_width * 0.5)
        x = self.padding_left + 0.5 + self.start_grip.width / 2
        y = self.padding_top + (self.scale_width - scale_h) / 2 + 0.5
        w = self.width - self.horizontal_padding - x - self.start_grip.width / 2
        h = scale_h

        # the whole slide
        self.graphics.rectangle(x, y, w, h, 3)
        self.graphics.fill_stroke("#eee", "#888")

        start_x, end_x = self.start_grip.x, self.end_grip.x
        if self.range is True and start_x > end_x:
            start_x, end_x = end_x, start_x


        if self.range == "start":
            self.graphics.rectangle(x, y, start_x, h, 3)
        elif self.range == "end":
            self.graphics.rectangle(start_x, y, w - start_x + self.start_grip.width / 2, h, 3)
        elif self.range is True:
            if not self.inverse:
                # middle
                self.graphics.rectangle(start_x, y, end_x - start_x, h, 3)
            else:
                self.graphics.rectangle(x, y, start_x, h, 3)
                self.graphics.rectangle(end_x, y, w - end_x + self.end_grip.width / 2, h, 3)


        self.graphics.fill_stroke("#A1AFD0", "#888")

########NEW FILE########
__FILENAME__ = widget
# - coding: utf-8 -

# Copyright (c) 2011-2012 Media Modifications, Ltd.
# Dual licensed under the MIT or GPL Version 2 licenses.

import math
from gi.repository import Gtk as gtk
from gi.repository import Gdk as gdk
from gi.repository import GObject as gobject

from lib import graphics
import datetime as dt

class Widget(graphics.Sprite):
    """Base class for all widgets. You can use the width and height attributes
    to request a specific width.
    """
    __gsignals__ = {
        "on-mnemonic-activated": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT,)),
    }

    _sizing_attributes = set(("visible", "min_width", "min_height",
                              "expand", "expand_vert", "fill", "spacing",
                              "horizontal_spacing", "vertical_spacing", "x_align",
                              "y_align"))

    min_width = None  #: minimum width of the widget
    min_height = None #: minimum height of the widget

    #: Whether the child should receive extra space when the parent grows.
    expand = True

    #: whether the child should receive extra space when the parent grows
    #: vertically. Applicable to only when the widget is in a table.
    expand_vert = True

    #: Whether extra space given to the child should be allocated to the
    #: child or used as padding. Edit :attr:`x_align` and
    #: :attr:`y_align` properties to adjust alignment when fill is set to False.
    fill = True

    #: horizontal alignment within the parent. Works when :attr:`fill` is False
    x_align = 0.5

    #: vertical alignment within the parent. Works when :attr:`fill` is False
    y_align = 0.5

    #: child padding - shorthand to manipulate padding in pixels ala CSS. tuple
    #: of one to four elements. Setting this value overwrites values of
    #: :attr:`padding_top`, :attr:`padding_right`, :attr:`padding_bottom`
    #: and :attr:`padding_left`
    padding = None
    padding_top = None    #: child padding - top
    padding_right = None  #: child padding - right
    padding_bottom = None #: child padding - bottom
    padding_left = None   #: child padding - left

    #: widget margins - shorthand to manipulate margin in pixels ala CSS. tuple
    #: of one to four elements. Setting this value overwrites values of
    #: :attr:`margin_top`, :attr:`margin_right`, :attr:`margin_bottom` and
    #: :attr:`margin_left`
    margin = 0
    margin_top = 0     #: top margin
    margin_right = 0   #: right margin
    margin_bottom = 0  #: bottom margin
    margin_left = 0    #: left margin

    enabled = True #: whether the widget is enabled

    mouse_cursor = False #: Mouse cursor. see :attr:`graphics.Sprite.mouse_cursor` for values

    #: tooltip position - currently supports only "auto" and "mouse"
    #: "auto" positions the tooltip below the widget and "mouse" positions at
    #: the mouse cursor position
    tooltip_position = "auto"

    #: (x, y) offset from the calculated position of the tooltip to appear
    tooltip_offset = None


    def __init__(self, width = None, height = None, expand = None, fill = None,
                 expand_vert = None, x_align = None, y_align = None,
                 padding_top = None, padding_right = None,
                 padding_bottom = None, padding_left = None, padding = None,
                 margin_top = None, margin_right = None,
                 margin_bottom = None, margin_left = None, margin = None,
                 enabled = None, tooltip = None, **kwargs):
        graphics.Sprite.__init__(self, **kwargs)

        def set_if_not_none(name, val):
            # set values - avoid pitfalls of None vs 0/False
            if val is not None:
                setattr(self, name, val)

        set_if_not_none("min_width", width)
        set_if_not_none("min_height", height)

        self._enabled = enabled if enabled is not None else self.__class__.enabled

        set_if_not_none("fill", fill)
        set_if_not_none("expand", expand)
        set_if_not_none("expand_vert", expand_vert)
        set_if_not_none("x_align", x_align)
        set_if_not_none("y_align", y_align)

        # set padding
        # (class, subclass, instance, and constructor)
        if padding is not None or self.padding is not None:
            self.padding = padding if padding is not None else self.padding
        self.padding_top = padding_top or self.__class__.padding_top or self.padding_top or 0
        self.padding_right = padding_right or self.__class__.padding_right or self.padding_right or 0
        self.padding_bottom = padding_bottom or self.__class__.padding_bottom or self.padding_bottom or 0
        self.padding_left = padding_left or self.__class__.padding_left or self.padding_left or 0

        if margin is not None or self.margin is not None:
            self.margin = margin if margin is not None else self.margin
        self.margin_top = margin_top or self.__class__.margin_top or self.margin_top or 0
        self.margin_right = margin_right or self.__class__.margin_right or self.margin_right or 0
        self.margin_bottom = margin_bottom or self.__class__.margin_bottom or self.margin_bottom or 0
        self.margin_left = margin_left or self.__class__.margin_left or self.margin_left or 0


        #: width in pixels that have been allocated to the widget by parent
        self.alloc_w = width if width is not None else self.min_width

        #: height in pixels that have been allocated to the widget by parent
        self.alloc_h = height if height is not None else self.min_height

        #: tooltip data (normally string). See :class:`Tooltip` for details
        self.tooltip = tooltip

        self.connect_after("on-render", self.__on_render)
        self.connect("on-mouse-over", self.__on_mouse_over)
        self.connect("on-mouse-out", self.__on_mouse_out)
        self.connect("on-mouse-down", self.__on_mouse_down)
        self.connect("on-key-press", self.__on_key_press)

        self._children_resize_queued = True
        self._scene_resize_handler = None


    def __setattr__(self, name, val):
        # forward width and height to min_width and min_height as i've ruined the setters a bit i think
        if name == "width":
            name = "min_width"
        elif name == "height":
            name = "min_height"
        elif name == 'enabled':
            name = '_enabled'
        elif name == "padding":
            val = val or 0
            if isinstance(val, int):
                val = (val, )

            if len(val) == 1:
                self.padding_top = self.padding_right = self.padding_bottom = self.padding_left = val[0]
            elif len(val) == 2:
                self.padding_top = self.padding_bottom = val[0]
                self.padding_right = self.padding_left = val[1]

            elif len(val) == 3:
                self.padding_top = val[0]
                self.padding_right = self.padding_left = val[1]
                self.padding_bottom = val[2]
            elif len(val) == 4:
                self.padding_top, self.padding_right, self.padding_bottom, self.padding_left = val
            return

        elif name == "margin":
            val = val or 0
            if isinstance(val, int):
                val = (val, )

            if len(val) == 1:
                self.margin_top = self.margin_right = self.margin_bottom = self.margin_left = val[0]
            elif len(val) == 2:
                self.margin_top = self.margin_bottom = val[0]
                self.margin_right = self.margin_left = val[1]
            elif len(val) == 3:
                self.margin_top = val[0]
                self.margin_right = self.margin_left = val[1]
                self.margin_bottom = val[2]
            elif len(val) == 4:
                self.margin_top, self.margin_right, self.margin_bottom, self.margin_left = val
            return


        if self.__dict__.get(name, "hamster_graphics_no_value_really") == val:
            return

        graphics.Sprite.__setattr__(self, name, val)

        # in widget case visibility affects placement and everything so request repositioning from parent
        if name == 'visible'and getattr(self, "parent", None):
            self.parent.resize_children()

        elif name == '_enabled' and getattr(self, "sprites", None):
            self._propagate_enabledness()

        if name in self._sizing_attributes:
            self.queue_resize()

    def _propagate_enabledness(self):
        # runs down the tree and marks all child sprites as dirty as
        # enabledness is inherited
        self._sprite_dirty = True
        for sprite in self.sprites:
            next_call = getattr(sprite, "_propagate_enabledness", None)
            if next_call:
                next_call()

    def _with_rotation(self, w, h):
        """calculate the actual dimensions after rotation"""
        res_w = abs(w * math.cos(self.rotation) + h * math.sin(self.rotation))
        res_h = abs(h * math.cos(self.rotation) + w * math.sin(self.rotation))
        return res_w, res_h

    @property
    def horizontal_padding(self):
        """total calculated horizontal padding. A read-only property."""
        return self.padding_left + self.padding_right

    @property
    def vertical_padding(self):
        """total calculated vertical padding.  A read-only property."""
        return self.padding_top + self.padding_bottom

    def __on_mouse_over(self, sprite):
        cursor, mouse_x, mouse_y, mods = sprite.get_scene().get_window().get_pointer()
        if self.tooltip and not gdk.ModifierType.BUTTON1_MASK & mods:
            self._set_tooltip(self.tooltip)


    def __on_mouse_out(self, sprite):
        if self.tooltip:
            self._set_tooltip(None)

    def __on_mouse_down(self, sprite, event):
        if self.can_focus:
            self.grab_focus()
        if self.tooltip:
            self._set_tooltip(None)


    def _set_tooltip(self, tooltip):
        scene = self.get_scene()
        if not scene:
            return

        if hasattr(scene, "_tooltip") == False:
            scene._tooltip = TooltipWindow()

        scene._tooltip.show(self, tooltip)


    def __on_key_press(self, sprite, event):
        if event.keyval in (gdk.KEY_Tab, gdk.KEY_ISO_Left_Tab):
            idx = self.parent.sprites.index(self)

            if event.state & gdk.ModifierType.SHIFT_MASK: # going backwards
                if idx > 0:
                    idx -= 1
                    self.parent.sprites[idx].grab_focus()
            else:
                if idx < len(self.parent.sprites) - 1:
                    idx += 1
                    self.parent.sprites[idx].grab_focus()


    def queue_resize(self):
        """request the element to re-check it's child sprite sizes"""
        self._children_resize_queued = True
        parent = getattr(self, "parent", None)
        if parent and isinstance(parent, graphics.Sprite) and hasattr(parent, "queue_resize"):
            parent.queue_resize()


    def get_min_size(self):
        """returns size required by the widget"""
        if self.visible == False:
            return 0, 0
        else:
            return ((self.min_width or 0) + self.horizontal_padding + self.margin_left + self.margin_right,
                    (self.min_height or 0) + self.vertical_padding + self.margin_top + self.margin_bottom)



    def insert(self, index = 0, *widgets):
        """insert widget in the sprites list at the given index.
        by default will prepend."""
        for widget in widgets:
            self._add(widget, index)
            index +=1 # as we are moving forwards
        self._sort()


    def insert_before(self, target):
        """insert this widget into the targets parent before the target"""
        if not target.parent:
            return
        target.parent.insert(target.parent.sprites.index(target), self)

    def insert_after(self, target):
        """insert this widget into the targets parent container after the target"""
        if not target.parent:
            return
        target.parent.insert(target.parent.sprites.index(target) + 1, self)


    @property
    def width(self):
        """width in pixels"""
        alloc_w = self.alloc_w

        if self.parent and self.parent == self.get_scene():
            alloc_w = self.parent.width

            def res(scene, event):
                if self.parent:
                    self.queue_resize()
                else:
                    scene.disconnect(self._scene_resize_handler)
                    self._scene_resize_handler = None


            if not self._scene_resize_handler:
                # TODO - disconnect on reparenting
                self._scene_resize_handler = self.parent.connect("on-resize", res)

            if hasattr(self.parent, '_global_shortcuts') is False:
                self.parent._global_shortcuts = GlobalShortcuts(self.parent)

        min_width = (self.min_width or 0) + self.margin_left + self.margin_right
        w = alloc_w if alloc_w is not None and self.fill else min_width
        w = max(w or 0, self.get_min_size()[0])
        return w - self.margin_left - self.margin_right

    @property
    def height(self):
        """height in pixels"""
        alloc_h = self.alloc_h

        if self.parent and self.parent == self.get_scene():
            alloc_h = self.parent.height

        min_height = (self.min_height or 0) + self.margin_top + self.margin_bottom
        h = alloc_h if alloc_h is not None and self.fill else min_height
        h = max(h or 0, self.get_min_size()[1])
        return h - self.margin_top - self.margin_bottom

    @property
    def enabled(self):
        """whether the user is allowed to interact with the
        widget. Item is enabled only if all it's parent elements are"""
        enabled = self._enabled
        if not enabled:
            return False

        if self.parent and isinstance(self.parent, Widget):
            if self.parent.enabled == False:
                return False

        return True


    def __on_render(self, sprite):
        self.do_render()
        if self.debug:
            self.graphics.save_context()

            w, h = self.width, self.height
            if hasattr(self, "get_height_for_width_size"):
                w2, h2 = self.get_height_for_width_size()
                w2 = w2 - self.margin_left - self.margin_right
                h2 = h2 - self.margin_top - self.margin_bottom
                w, h = max(w, w2), max(h, h2)

            self.graphics.rectangle(0.5, 0.5, w, h)
            self.graphics.set_line_style(5)
            self.graphics.stroke("#666", 0.5)
            self.graphics.restore_context()

            if self.pivot_x or self.pivot_y:
                self.graphics.fill_area(self.pivot_x - 3, self.pivot_y - 3, 6, 6, "#666")

    def __emit(self, event_name, *args):
        if (self.enabled and self.opacity > 0):
            self.emit(event_name, *args)

    # emit events only if enabled
    def _do_click(self, event):
        self.__emit("on-click", event)
    def _do_double_click(self, event):
        self.__emit("on-double-click", event)
    def _do_triple_click(self, event):
        self.__emit("on-triple-click", event)
    def _do_mouse_down(self, event):
        self.__emit("on-mouse-down", event)
    def _do_mouse_up(self, event):
        self.__emit("on-mouse-up", event)
    def _do_mouse_over(self):
        self.__emit("on-mouse-over")
    def _do_mouse_move(self, event):
        self.__emit("on-mouse-move", event)
    def _do_mouse_out(self):
        self.__emit("on-mouse-out")
    def _do_key_press(self, event):
        self.__emit("on-key-press", event)
    def _do_mnemonic_activated(self, event):
        self.__emit("on-mnemonic-activated", event)

    def do_render(self):
        """this function is called in the on-render event. override it to do
           any drawing. subscribing to the "on-render" event will work too, but
           overriding this method is preferred for easier subclassing.
        """
        pass


    def _rounded_line(self, coords, corner_radius = 4):
        # draws a line that is rounded in the corners
        half_corner = corner_radius / 2

        current_x, current_y = coords[0]
        self.graphics.move_to(current_x, current_y)

        for (x1, y1), (x2, y2) in zip(coords[1:], coords[2:]):
            if current_x == x1:
                #vertically starting curve going somewhere
                dy = (y1 < current_y) * 2 - 1
                dx = (x1 < x2) * 2 - 1

                self.graphics.line_to(x1, y1 + corner_radius * dy)
                self.graphics.curve_to(x1, y1 + half_corner * dy, x1 + half_corner * dx, y1, x1 + corner_radius * dx, y1)


            elif current_y == y1:
                #horizontally starting curve going somewhere
                dx = (x1 < current_x) * 2 - 1
                dy = (y1 < y2) * 2 - 1

                self.graphics.line_to(x1 + corner_radius * dx, y1)
                self.graphics.curve_to(x1 + half_corner * dx, y1, x1, y1 + half_corner * dy, x1, y1 + corner_radius * dy)


            current_x, current_y = x1, y1
        self.graphics.line_to(*coords[-1])



class Tooltip(object):
    """There is a single tooltip object per whole application and it is
    automatically created on the first call. The class attributes (color,
    padding, size, etc.) allow basic modifications of the looks.
    If you would like to have full control over the tooltip, you can set your
    own class in :class:`TooltipWindow`.

    Example::

        # make tooltip background red for the whole application and add more padding
        import ui
        ui.Tooltip.background_color = "#f00"
        ui.Tooltip.padding = 20
    """
    #: font description
    font_desc = "Sans serif 10"

    #: default font size
    size = None

    #: padding around the label in pixels
    padding = 5

    #: background color
    background_color = "#333"

    #: font color
    color = "#eee"


    def __init__(self):
        from ui.widgets import Label # unfortunately otherwise we run into a circular dependency
        self.label = Label(size=self.size,
                           font_desc=self.font_desc,
                           padding=self.padding,
                           background_color=self.background_color,
                           color=self.color)

    def __getattr__(self, name):
        # forward all getters to label (this way we walk around the label circular loop)
        # no need to repeat this when overriding, because at that point you already
        # have access to label and can inherit from that
        if name == 'label':
            return self.__dict__['label']
        else:
            return getattr(self.label, name)

    def set_tooltip(self, tooltip):
        """set_tooltip is internally called by the framework. Implement this
        function if you are creating a custom tooltip class.
        The `tooltip` parameter normally contains text, but you can set the
        :class:`Widget.tooltip` to anything (even sprites)"""
        self.label.text = tooltip


class TooltipWindow(object):
    """Object that contains the actual tooltip :class:`gtk.Window`.
    By setting class attributes here you can control the tooltip class and
    the timespan before showing the tooltip"""

    #: class that renders tooltip contents. override this attribute if you
    #: want to use your own tooltip class
    TooltipClass = Tooltip

    #: delay before showing the tooltip
    first_appearance_milis = 300


    def __init__(self):
        self.label = None
        self.popup = gtk.Window(type = gtk.WindowType.POPUP)
        self.popup_scene = graphics.Scene(interactive=False)
        self.popup.add(self.popup_scene)

        self.tooltip = self.TooltipClass()
        self.popup_scene.add_child(self.tooltip)

        self._display_timeout = None
        self._last_display_time = None
        self._current_widget = None
        self._prev_tooltip = None


    def show(self, widget, tooltip):
        """Show tooltip. This function is called automatically by the library."""
        if not tooltip:
            self._prev_tooltip = tooltip
            self.popup.hide()

            if self._display_timeout:
                gobject.source_remove(self._display_timeout)
            return


        if widget == self._current_widget and tooltip == self._prev_tooltip:
            return


        if not self._last_display_time or (dt.datetime.now() - self._last_display_time) > dt.timedelta(milliseconds = self.first_appearance_milis):
            self._display_timeout = gobject.timeout_add(self.first_appearance_milis,
                                                        self._display, widget, tooltip)
        else:
            self._display(widget, tooltip)


    def _display(self, widget, tooltip):
        self._current_widget, self._prev_tooltip = widget, tooltip

        self._last_display_time = dt.datetime.now()

        scene = widget.get_scene()

        parent_window = scene.get_parent_window()
        dummy, window_x, window_y = parent_window.get_origin()

        exts = widget.get_extents()
        widget_x, widget_y, widget_w, widget_h = exts.x, exts.y, exts.width, exts.height


        screen = parent_window.get_screen()
        screen_w, screen_h = screen.get_width(), screen.get_height()

        #set label to determine dimensions
        self.tooltip.set_tooltip(tooltip)
        popup_w, popup_h = self.tooltip.width, self.tooltip.height
        if hasattr(self.tooltip, "get_height_for_width_size"):
            popup_w, popup_h = self.tooltip.get_height_for_width_size()
            popup_w += self.tooltip.horizontal_padding
            popup_h += self.tooltip.vertical_padding


        self.popup.resize(popup_w, popup_h)

        if widget.tooltip_position == "mouse":
            cursor_size = parent_window.get_display().get_default_cursor_size()
            tooltip_x = scene.mouse_x + (cursor_size - popup_w) / 2
            tooltip_y = scene.mouse_y + cursor_size
        else:
            tooltip_x = widget_x + (widget_w - popup_w) / 2
            tooltip_y = widget_y + widget_h

        if widget.tooltip_offset:
            tooltip_x += widget.tooltip_offset[0]
            tooltip_y += widget.tooltip_offset[1]

        popup_x = window_x + tooltip_x
        popup_x = max(0, min(popup_x, screen_w - popup_w))

        # show below the widget if possible. otherwise - on top
        popup_y = window_y + tooltip_y
        if popup_y + popup_h > screen_h:
            popup_y = window_y + widget_y - popup_h


        self.popup.move(int(popup_x), int(popup_y))
        self.popup.show_all()


class GlobalShortcuts(object):
    def __init__(self, target):
        self.target = target
        target.connect("on-key-press", self.on_key_press)
        target.connect("on-key-release", self.on_key_release)
        self._pressed_key = None


    def on_key_press(self, target, event):
        if self._pressed_key:
            return

        for widget in target.traverse():
            items = [widget] if hasattr(widget, 'mnemonic') else getattr(widget, 'mnemonic_items', [])
            for item in items:
                if item.mnemonic and self._check_mnemonic(item.mnemonic, event):
                    item._do_mnemonic_activated(event)
                    self._pressed_key = chr(event.keyval).lower() if chr < 256 else event.keyval
                    return #grab the first and go home. TODO - we are doing depth-first. consider doing width-first


    def on_key_release(self, target, event):
        if not event.string:
            return
        event_key = chr(event.keyval).lower() if chr < 256 else event.keyval
        if event_key == self._pressed_key:
            self._pressed_key = None


    def _check_mnemonic(self, mnemonic_string, event):
        pressed_key = event.string
        if not pressed_key:
            return

        mask_states = {
            'Shift': event.state & gdk.ModifierType.SHIFT_MASK,
            'Ctrl': event.state & gdk.ModifierType.CONTROL_MASK,
            'Alt': event.state & gdk.ModifierType.MOD1_MASK,
            'Super': event.state & gdk.ModifierType.SUPER_MASK,
        }
        keys = mnemonic_string.split("+")

        # check for modifiers
        for mask in mask_states.keys():
            if mask in keys:
                keys.remove(mask)
                if not mask_states[mask]:
                    return False
            else:
                if mask_states[mask]: # we have a modifier that was not asked for
                    return False

        # examine pressed key
        # have it case insensitive as we request the modifiers explicitly
        # and so have to avoid impossible cases like Ctrl+Shift+c  (lowercase c)
        return chr(event.keyval).lower() == keys[0].lower()

########NEW FILE########
__FILENAME__ = widgets
# - coding: utf-8 -

# Copyright (c) 2011-2012 Media Modifications, Ltd.
# Dual licensed under the MIT or GPL Version 2 licenses.

from gi.repository import Gtk as gtk
from gi.repository import Gdk as gdk
from gi.repository import GObject as gobject

from lib import graphics

from ui import Widget, Container, Bin, Table, Box, HBox, VBox, Fixed, Viewport, Group, TreeModel
import math
from gi.repository import Pango as pango

class _DisplayLabel(graphics.Label):
    cache_attrs = Box.cache_attrs | set(('_cached_w', '_cached_h'))

    def __init__(self, text="", **kwargs):
        graphics.Label.__init__(self, text, **kwargs)
        self._cached_w, self._cached_h = None, None
        self._cached_wh_w, self._cached_wh_h = None, None

    def __setattr__(self, name, val):
        graphics.Label.__setattr__(self, name, val)

        if name in ("text", "markup", "size", "wrap", "ellipsize", "max_width"):
            if name != "max_width":
                self._cached_w, self._cached_h = None, None
            self._cached_wh_w, self._cached_wh_h = None, None


    def get_min_size(self):
        if self._cached_w:
            return self._cached_w, self._cached_h

        text = self.markup or self.text
        escape = len(self.markup) == 0

        if self.wrap is not None or self.ellipsize is not None:
            self._cached_w = self.measure(text, escape, 1)[0]
            self._cached_h = self.measure(text, escape, -1)[1]
        else:
            self._cached_w, self._cached_h = self.measure(text, escape, -1)
        return self._cached_w, self._cached_h

    def get_weight_for_width_size(self):
        if self._cached_wh_w:
            return self._cached_wh_w, self._cached_wh_h

        text = self.markup or self.text
        escape = len(self.markup) == 0
        self._cached_wh_w, self._cached_wh_h = self.measure(text, escape, self.max_width)

        return self._cached_wh_w, self._cached_wh_h

class Label(Bin):
    """a widget that displays a limited amount of read-only text"""
    #: pango.FontDescription to use for the label
    font_desc = "Sans Serif 10"

    #: image attachment. one of top, right, bottom, left
    image_position = "left"

    #: font size
    size = None

    fill = False
    padding = 0
    x_align = 0

    def __init__(self, text = "", markup = "", spacing = 5, image = None,
                 image_position = None, size = None, font_desc = None,
                 overflow = False,
                 color = "#000", background_color = None, **kwargs):

        # TODO - am initiating table with fill = false but that yields suboptimal label placement and the 0,0 points to whatever parent gave us
        Bin.__init__(self, **kwargs)

        #: image to put next to the label
        self.image = image

        # the actual container that contains the label and/or image
        self.container = Box(spacing = spacing, fill = False,
                             x_align = self.x_align, y_align = self.y_align)

        if image_position is not None:
            self.image_position = image_position

        self.display_label = _DisplayLabel(text = text, markup = markup, color=color, size = size)
        self.display_label.x_align = 0 # the default is 0.5 which makes label align incorrectly on wrapping

        if font_desc or self.font_desc:
            self.display_label.font_desc = font_desc or self.font_desc

        self.display_label.size = size or self.size

        self.background_color = background_color

        #: either the pango `wrap <http://www.pygtk.org/pygtk2reference/pango-constants.html#pango-wrap-mode-constants>`_
        #: or `ellipsize <http://www.pygtk.org/pygtk2reference/pango-constants.html#pango-ellipsize-mode-constants>`_ constant.
        #: if set to False will refuse to become smaller
        self.overflow = overflow

        self.add_child(self.container)

        self._position_contents()
        self.connect_after("on-render", self.__on_render)

    def get_mouse_sprites(self):
        return None

    @property
    def text(self):
        """label text. This attribute and :attr:`markup` are mutually exclusive."""
        return self.display_label.text

    @property
    def markup(self):
        """pango markup to use in the label.
        This attribute and :attr:`text` are mutually exclusive."""
        return self.display_label.markup

    @property
    def color(self):
        """label color"""
        return self.display_label.color

    def __setattr__(self, name, val):
        if name in ("text", "markup", "color", "size"):
            if self.display_label.__dict__.get(name, "hamster_graphics_no_value_really") == val:
                return
            setattr(self.display_label, name, val)
        elif name in ("spacing"):
            setattr(self.container, name, val)
        else:
            if self.__dict__.get(name, "hamster_graphics_no_value_really") == val:
                return
            Bin.__setattr__(self, name, val)


        if name in ('x_align', 'y_align') and hasattr(self, "container"):
            setattr(self.container, name, val)

        elif name == "alloc_w" and hasattr(self, "display_label") and getattr(self, "overflow") is not False:
            self._update_max_width()

        elif name == "min_width" and hasattr(self, "display_label"):
            self.display_label.width = val - self.horizontal_padding

        elif name == "overflow" and hasattr(self, "display_label"):
            if val is False:
                self.display_label.wrap = None
                self.display_label.ellipsize = None
            elif isinstance(val, pango.WrapMode) and val in (pango.WrapMode.WORD, pango.WrapMode.WORD_CHAR, pango.WrapMode.CHAR):
                self.display_label.wrap = val
                self.display_label.ellipsize = None
            elif isinstance(val, pango.EllipsizeMode) and val in (pango.EllipsizeMode.START, pango.EllipsizeMode.MIDDLE, pango.EllipsizeMode.END):
                self.display_label.wrap = None
                self.display_label.ellipsize = val

            self._update_max_width()
        elif name in ("font_desc", "size"):
            setattr(self.display_label, name, val)

        if name in ("text", "markup", "image", "image_position", "overflow", "size"):
            if hasattr(self, "overflow"):
                self._position_contents()
                self.container.queue_resize()


    def _update_max_width(self):
        # updates labels max width, respecting image and spacing
        if self.overflow is False:
            self.display_label.max_width = -1
        else:
            w = (self.alloc_w or 0) - self.horizontal_padding - self.container.spacing
            if self.image and self.image_position in ("left", "right"):
                w -= self.image.width - self.container.spacing
            self.display_label.max_width = w

        self.container.queue_resize()


    def _position_contents(self):
        if self.image and (self.text or self.markup):
            self.image.expand = False
            self.container.orient_horizontal = self.image_position in ("left", "right")

            if self.image_position in ("top", "left"):
                if self.container.sprites != [self.image, self.display_label]:
                    self.container.clear()
                    self.container.add_child(self.image, self.display_label)
            else:
                if self.container.sprites != [self.display_label, self.image]:
                    self.container.clear()
                    self.container.add_child(self.display_label, self.image)
        elif self.image or (self.text or self.markup):
            sprite = self.image or self.display_label
            if self.container.sprites != [sprite]:
                self.container.clear()
                self.container.add_child(sprite)


    def __on_render(self, sprite):
        w, h = self.width, self.height
        w2, h2 = self.get_height_for_width_size()
        w, h = max(w, w2), max(h, h2)
        self.graphics.rectangle(0, 0, w, h)

        if self.background_color:
            self.graphics.fill(self.background_color)
        else:
            self.graphics.new_path()



class Spinner(Container):
    """an indeterminate progress indicator"""
    def __init__(self, active = True, **kwargs):
        Container.__init__(self, **kwargs)

        #: whether the spinner is spinning or not
        self.active = active

        self._scene = None
        self.expose_handler = None

        #: number of beams in the progress indicator
        self.edges = 11

        self.inner_radius = 6
        self.outer_radius = 13
        self.tick_thickness = 3

        #: motion speed. the higher the number the slower the redraw is performed
        self.speed = 2
        self._frame = 0

        self._spinner = graphics.Sprite(cache_as_bitmap = False)
        self.connect_child(self._spinner, "on-render", self.on_spinner_render)
        self.add_child(self._spinner)


    def get_min_size(self):
        need = max(self.min_height or 20, self.min_width or 20)
        return need, need

    def resize_children(self):
        self.outer_radius = min(self.alloc_h / 2.0, self.alloc_w / 2.0)
        self.inner_radius = self.outer_radius * 0.3
        self.tick_thickness = self.inner_radius * 0.5
        self._spinner.x, self._spinner.y = self.outer_radius / 2.0 + (self.width - self.outer_radius) * self.x_align, \
                                         self.outer_radius / 2.0 + (self.height - self.outer_radius) * self.y_align

    def on_finish_frame(self, scene, context):
        if self.active:
            if self._frame % self.speed == 0:
                self._spinner.rotation += math.pi * 2 / self.edges

            self._frame +=1
            scene.redraw()

    def on_spinner_render(self, spinner):
        spinner.graphics.save_context()
        if not self.expose_handler:
            self._scene = self.get_scene()
            self.expose_handler = self._scene.connect("on-finish-frame", self.on_finish_frame)

        spinner.graphics.rectangle(-self.outer_radius, -self.outer_radius, self.outer_radius * 2, self.outer_radius * 2)
        spinner.graphics.new_path()
        for i in range(self.edges):
            spinner.graphics.rectangle(-self.tick_thickness / 2, self.inner_radius, self.tick_thickness, self.outer_radius - self.inner_radius, 4)
            spinner.graphics.fill(graphics.Colors.darker("#fff", i * 15))
            spinner.graphics.rotate(math.pi * 2 / self.edges)

        spinner.graphics.restore_context()

########NEW FILE########
__FILENAME__ = ui_demo
#!/usr/bin/env python
# - coding: utf-8 -
# Copyright (C) 2011 Toms Bauģis <toms.baugis at gmail.com>

sample_text = "And now for something totally different! A label that not only supports newlines but also wraps and perhaps even triggers scroll. All we essentially want here, is a lot of text to play with. A few lines. Five or seven or seventeen. Well i think you should have caught the drift by now!"
accordion_text = "My contents - merely a label, nothing impressive. But i'll still try to pack lots of text in it. My contents - merely a label, nothing impressive. But i'll still try to pack lots of text in it. My contents - merely a label, nothing impressive. But i'll still try to pack lots of text in it. My contents - merely a label, nothing impressive. But i'll still try to pack lots of text in it. My contents - merely a label, nothing impressive. But i'll still try to pack lots of text in it. My contents - merely a label, nothing impressive. But i'll still try to pack lots of text in it. My contents - merely a label, nothing impressive. But i'll still try to pack lots of text in it. My contents - merely a label, nothing impressive. But i'll still try to pack lots of text in it."

from themes import utils
utils.install_font("danube_regular.ttf")

from gi.repository import Gtk as gtk
from gi.repository import Pango as pango

from lib import graphics
import ui
from themes import bitmaps
import datetime as dt


class Rectangle(ui.Container):
    """rectangle is good for forgetting it's dimensions"""
    def __init__(self, width = 10, height = 10, fill_color = "#ccc", **kwargs):
        ui.Container.__init__(self, width = width, height = height, **kwargs)

        self.interactive = True
        self.fill_color = fill_color

        self.connect("on-render", self.on_render)

    def on_render(self, sprite):
        self.graphics.set_line_style(width = 1)
        self.graphics.rectangle(0.5, 0.5, self.width, self.height)
        self.graphics.fill_stroke(self.fill_color, "#666")




class Scene(graphics.Scene):
    def __init__(self):
        now = dt.datetime.now()

        graphics.Scene.__init__(self)

        self.notebook = ui.Notebook(tab_position = "top-left", scroll_position="end", show_scroll = "auto_invisible", scroll_selects_tab = False)

        # boxes packed and nested horizontally and vertically, with a draggable corner
        self.box = ui.HBox(spacing = 3, x=10, y=10)
        self.button = ui.Button("My image changes position", image = graphics.Image("assets/hamster.png"), fill = False)
        self.button.connect("on-click", self.on_button_click)

        self.box.add_child(*[ui.VBox([self.button,
                                      ui.ToggleButton("I'm a toggle button! Have a tooltip too!", image = graphics.Image("assets/day.png"), fill = True, tooltip="Oh hey there, i'm a tooltip!"),
                                      ui.Label("I'm a label \nand we all can wrap", image = graphics.Image("assets/week.png"), spacing = 5, padding = 5, x_align = 0),
                                      ui.Entry("Feel free to edit me! I'm a rather long text that will scroll nicely perhaps. No guarantees though!", expand = False),
                                      ui.Entry("And me too perhaps", expand = False)],
                                     spacing = 5, padding = 10),
                             Rectangle(20, expand = False),
                             graphics.Label("rrrr", color="#666"),
                             Rectangle(20, expand = False),
                             ui.VBox([Rectangle(fill = False), Rectangle(), Rectangle()], spacing = 3)
                             ])


        box_w, box_h = self.box.get_min_size()
        self.corner = graphics.Rectangle(10, 10, fill="#666",
                                         x = self.box.x + box_w,
                                         y = self.box.y + box_h,
                                         draggable=True,
                                         interactive=True,
                                         z_order = 100)
        self.corner.connect("on-drag", self.on_corner_drag)


        # a table
        self.table = ui.Table(3, 3, snap_to_pixel = False, padding=10)
        self.table.attach(Rectangle(fill_color = "#f00", expand_vert = False), 0, 3, 0, 1) # top
        self.table.attach(Rectangle(fill_color = "#0f0", expand = False), 2, 3, 1, 2)      # right
        self.table.attach(Rectangle(fill_color = "#f0f", expand_vert = False), 0, 3, 2, 3) # bottom
        self.table.attach(Rectangle(fill_color = "#0ff", expand = False), 0, 1, 1, 2)      # left
        center = Rectangle()
        center.connect("on-mouse-over", self.on_table_mouse_over)
        center.connect("on-mouse-out", self.on_table_mouse_out)
        self.table.attach(center, 1, 2, 1, 2)


        # a scroll area with something to scroll in it
        self.scroll = ui.ScrollArea(border = 0)
        self.scroll.add_child(ui.Container(ui.Button("Scroll me if you can!", width = 1000, height = 300, fill=False), fill = False, padding=15))


        # bunch of different input elements
        inputs = ui.Panes(padding=10)
        listitem = ui.ListItem(["Sugar", "Spice", "Everything Nice", "--", "Feel",
                                "Free", "To", "Click", "On", "Me", {'markup': "<span color='red'>And</span>"},
                                "Use", "The", "Arrows!", "Ah", "And", "It", "Seems",
                                "That", "There", "Are", "So", "Many", "Elements"])

        def print_selection(listitem, item):
            print "selection", item

        def print_change(listitem, item):
            print "change", item

        listitem.connect("on-change", print_change)
        listitem.connect("on-select", print_selection)
        inputs.add_child(listitem)

        one = ui.ToggleButton("One", margin=[15, 10, 20, 30], id="one")

        group1 = ui.Group([one,
                           ui.ToggleButton("Two", scale_x = 0.5, scale_y = 0.5, expand=False, id="two"),
                           ui.ToggleButton("Three", id="three"),
                           ui.ToggleButton("Four", id="four")],
                          expand = False, allow_no_selection=True)
        label1 = ui.Label("Current value: none selected", x_align=0, expand = False)
        def on_toggle1(group, current_item):
            if current_item:
                label1.text = "Current value: %s" % current_item.label
            else:
                label1.text = "No item selected"
        group1.connect("on-change", on_toggle1)

        group2 = ui.Group([ui.RadioButton("One"),
                           ui.RadioButton("Two"),
                           ui.RadioButton("Three"),
                           ui.RadioButton("Four")],
                          horizontal = False)
        label2 = ui.Label("Current value: none selected", x_align = 0, expand=False)
        def on_toggle2(group, current_item):
            label2.text = "Current value: %s" % current_item.label
        group2.connect("on-change", on_toggle2)

        slider = ui.Slider(range(100),
                           expand = False,
                           snap_to_ticks = False,
                           range=True,
                           selection=(23, 80),
                           grips_can_cross = False,
                           snap_points = [5, 20, 50, 75],
                           snap_on_release = True)
        slider_value = ui.Label(" ")
        def on_slider_change(slider, value):
            slider_value.text = str(value)
        slider.connect("on_change", on_slider_change)

        spinner = ui.Spinner(active = False, expand=False, width = 40)
        spinner_button = ui.Button("Toggle spin", expand=False)
        spinner_button.spinner = spinner

        def on_spinner_button_click(button, event):
            button.spinner.active = not button.spinner.active
        spinner_button.connect("on-click", on_spinner_button_click)

        combo = ui.ComboBox(["Sugar", "Spice", "Everything Nice", "And", "Other", "Nice", "Things"],
                             open_below=True,
                             expand = False)
        inputs.add_child(ui.VBox([combo,
                                  group1, label1,
                                  ui.HBox([group2,
                                           ui.VBox([ui.CheckButton("And a few of those", expand = False),
                                                    ui.CheckButton("Check boxes", expand = False),
                                                    ui.CheckButton("Which don't work for groups", expand = False)])
                                          ]),
                                  label2,
                                  slider,
                                  slider_value,
                                  ui.HBox([spinner, spinner_button], expand=False, spacing = 10),
                                  ui.HBox([ui.ScrollArea(ui.Label(sample_text * 3, overflow = pango.WrapMode.WORD, fill=True, padding=[2, 5]), height=45, scroll_horizontal=False),
                                           ui.SpinButton(expand = False, fill=False)], expand = False),
                                  ],
                                 expand = False, spacing = 10))

        combo.rows = ["some", "things", "are", "made", "of", "bananas", "and", "icecream"]


        menu = ui.Menu([ui.MenuItem(label="One", menu=ui.Menu([ui.MenuItem(label="One one", menu=ui.Menu([ui.MenuItem(label="One one one"),
                                                                                                          ui.MenuItem(label="One one two"),
                                                                                                          ui.MenuSeparator(),
                                                                                                          ui.MenuItem(label="One one three")])),
                                                               ui.MenuSeparator(),
                                                               ui.MenuItem(label="One two", mnemonic="Ctrl+1"),
                                                               ui.MenuItem(label="One three", mnemonic="Alt+1")])),

                        ui.MenuItem(label="Two", menu=ui.Menu([ui.MenuItem(label="Two one", mnemonic="Ctrl+Alt+2"),
                                                               ui.MenuItem(label="Two two", mnemonic="Ctrl+2"),
                                                               ui.MenuSeparator(),
                                                               ui.MenuItem(label="Two three", mnemonic="Alt+2")])),

                        ui.MenuItem(label="Three", menu=ui.Menu([ui.MenuItem(label="Three one", mnemonic="Ctrl+Alt+3"),
                                                                 ui.MenuItem(label="Three two", mnemonic="Ctrl+3"),
                                                                 ui.MenuSeparator(),
                                                                 ui.MenuItem(label="Three three", mnemonic="Alt+3")])),
                        ui.MenuItem(label="Four", menu=ui.Menu([ui.MenuItem(label="Four one", mnemonic="Ctrl+Alt+4"),
                                                                ui.MenuItem(label="Four two", mnemonic="Ctrl+4"),
                                                                ui.MenuSeparator(),
                                                                ui.MenuItem(label="Four three", mnemonic="Alt+4")])),
                       ], horizontal=True)

        self.menu_selection_label = ui.Label("Pick a menu item!", expand = False, x_align = 1)
        def on_menuitem_selected(menu, item, event):
            self.menu_selection_label.text = item.label
        menu.connect("selected", on_menuitem_selected)

        # adding notebook and attaching pages
        self.notebook.add_page(ui.NotebookTab(image=graphics.Image("assets/day.png"), label="boxes", padding=[1,5]),
                               ui.Fixed([self.box, self.corner], x = 10, y = 10))
        self.notebook.add_page(ui.NotebookTab("Table", tooltip="Oh hey, i'm a table!"), self.table)
        self.notebook.add_page("Scroll Area", self.scroll)
        self.notebook.add_page("Input Elements", inputs)

        self.notebook.add_page("Menu", ui.VBox([menu, self.menu_selection_label,
                                                ui.HBox(ui.Menu([ui.MenuItem(label="", image = graphics.Image("assets/day.png"), submenu_offset_x = 0, submenu_offset_y = 0,
                                                                       menu=ui.Menu([ui.MenuItem(label="", image = graphics.Image("assets/month.png")),
                                                                                     ui.MenuItem(label="", image = graphics.Image("assets/hamster.png")),
                                                                                     ui.MenuSeparator(),
                                                                                     ui.MenuItem(label="", image = graphics.Image("assets/hamster.png")),
                                                                                     ui.MenuItem(label="", image = graphics.Image("assets/month.png"))], horizontal=True)),
                                                                 ui.MenuItem(label="", image = graphics.Image("assets/hamster.png"),submenu_offset_x = 0, submenu_offset_y = 0,
                                                                       menu=ui.Menu([ui.MenuItem(label="", image = graphics.Image("assets/month.png")),
                                                                                     ui.MenuItem(label="", image = graphics.Image("assets/month.png")),
                                                                                     ui.MenuItem(label="", image = graphics.Image("assets/week.png")),
                                                                                     ui.MenuSeparator(),
                                                                                     ui.MenuItem(label="", image = graphics.Image("assets/month.png"))], horizontal=True)),
                                                                 ui.MenuItem(label="", image = graphics.Image("assets/month.png"), submenu_offset_x = 0, submenu_offset_y = 0,
                                                                       menu=ui.Menu([ui.MenuItem(label="", image = graphics.Image("assets/week.png")),
                                                                                     ui.MenuItem(label="", image = graphics.Image("assets/week.png")),
                                                                                     ui.MenuSeparator(),
                                                                                     ui.MenuItem(label="", image = graphics.Image("assets/week.png")),
                                                                                     ui.MenuItem(label="", image = graphics.Image("assets/month.png"))], horizontal=True)),
                                                                ], horizontal=False, spacing=50, hide_on_leave = True, open_on_hover = 0.01), expand=False),
                                                ui.Box()], padding=10))



        self.slice_image = ui.Image('assets/slice9.png', fill=True, slice_left = 35, slice_right = 230, slice_top = 35, slice_bottom = 220)

        data = []
        image = graphics.Image("assets/day.png")
        for i in range(10):
            data.append(["aasdf asdfasdf asdfasdf", "basdfasdf asdfasdf asdfasdf", image, "rrr"])
            data.append(["1", "2", None, "rrr"])
            data.append(["4", "5", None, "rrr"])

        tree = ui.ListItem(data,
                           [ui.LabelRenderer(editable=True),
                            ui.LabelRenderer(editable=True),
                            ui.ImageRenderer(expand=False, width=90)],
                           headers=["Text", "More text", "An icon!"],
                           fixed_headers = False,
                           scroll_border = 0
                           )
        self.notebook.add_page("Tree View", tree)

        #tree.data[0][1] = "I was actually modified afterwards!"


        self.notebook.add_page("Accordion", ui.Accordion([
            ui.AccordionPage("I'm am the first in the row", [ui.Label(accordion_text, overflow = pango.WrapMode.WORD, padding=5)]),
            ui.AccordionPage("I'm am the first in the row", [ui.Label(accordion_text, overflow = pango.WrapMode.WORD, padding=5)]),
            ui.AccordionPage("I'm am the first in the row", [ui.Label(accordion_text, overflow = pango.WrapMode.WORD, padding=5)]),
            ui.AccordionPage("I'm am the first in the row", [ui.Label(accordion_text, overflow = pango.WrapMode.WORD, padding=5)]),
            ui.AccordionPage("I'm am the first in the row", [ui.Label(accordion_text, overflow = pango.WrapMode.WORD, padding=5)]),
            ui.AccordionPage("I'm am the first in the row", [ui.Label(accordion_text, overflow = pango.WrapMode.WORD, padding=5)]),
            ui.AccordionPage("I'm am the first in the row", [ui.Label(accordion_text, overflow = pango.WrapMode.WORD, padding=5)]),
            ui.AccordionPage("I'm am the first in the row", [ui.Label(accordion_text, overflow = pango.WrapMode.WORD, padding=5)]),
            ui.AccordionPage("I'm am the first in the row", [ui.Label(accordion_text, overflow = pango.WrapMode.WORD, padding=5)]),
            ui.AccordionPage("I'm am the first in the row", [ui.Label(accordion_text, overflow = pango.WrapMode.WORD, padding=5)]),
            ui.AccordionPage("I'm am the first in the row", [ui.Label(accordion_text, overflow = pango.WrapMode.WORD, padding=5)]),
            ui.AccordionPage("I'm different!", [
                ui.VBox([
                    ui.Button("I'm a button", fill=False, expand=False),
                    ui.Button("I'm another one", fill=False, expand=False),
                    ui.Group([
                        ui.ToggleButton("We"),
                        ui.ToggleButton("Are"),
                        ui.ToggleButton("Brothers"),
                        ui.ToggleButton("Radio Brothers"),
                    ], expand=False)
                ], expand=False)
            ]),
        ], padding_top = 1, padding_left = 1))

        from pie_menu import Menu
        pie_menu = Menu(0, 0)
        pie_menu.y_align = 0.45

        self.magic_box = ui.VBox([ui.HBox([ui.Button("Hello", expand=False),
                                           ui.Button("Thar", expand=False),
                                           ui.Label("Drag the white area around", x_align=1)], expand=False, padding=5),
                                  pie_menu], x=50, y=50, spacing=50, draggable=True)
        self.magic_box.width = 500
        self.magic_box.height = 400
        def just_fill():
            box = self.magic_box
            box.graphics.fill_area(0, 0, box.width, box.height, "#fefefe")
        self.magic_box.do_render = just_fill
        self.notebook.add_page("Ordinary Sprite", ui.Fixed(self.magic_box))

        for i in range(5):
            self.notebook.add_page("Tab %d" % i)


        self.notebook.current_page = 3


        # a little button to change tab orientation
        self.tab_orient_switch = ui.Button("Change tab attachment", expand=False, tooltip="change")
        self.tab_orient_switch.connect("on-click", self.on_tab_orient_click)

        self.page_disablist = ui.Button("Enable/Disable current tab", expand=False, tooltip="disable")
        self.page_disablist.connect("on-click", self.on_page_disablist_click)

        self.dialog_button = ui.Button("Show a dialog", expand=False, tooltip="show")
        self.dialog_button.connect("on-click", self.on_dialog_button_click)


        top_menu = ui.Menu([ui.MenuItem(label="One", menu=ui.Menu([ui.MenuItem(label="One one oh one oh one etc etc",
                                                                               menu=ui.Menu([ui.MenuItem(label="One one one"),
                                                                                    ui.MenuItem(label="One one two"),
                                                                                    ui.MenuItem(label="One one three")])),
                                                                   ui.MenuItem(label="One two"),
                                                                   ui.MenuItem(label="One three")])),
                            ui.MenuItem(label="Two", menu=ui.Menu([ui.MenuItem(label="Two one"),
                                                        ui.MenuItem(label="Two two"),
                                                        ui.MenuItem(label="Two three")])),
                            ui.MenuItem(label="Three", menu=ui.Menu([ui.MenuItem(label="Three one"),
                                                          ui.MenuItem(label="Three two"),
                                                          ui.MenuItem(label="Three three")])),
                            ui.MenuItem(label="Four", menu=ui.Menu([ui.MenuItem(label="Four one"),
                                                         ui.MenuItem(label="Four two"),
                                                         ui.MenuItem(label="Four three")])),
                            ui.MenuItem(label="Five")
                            ], horizontal=True, disable_toggling=True)


        # not sure how elegant but let's override the flow for now for demo purposes!
        dummy_flow = ui.Flow()
        def flow_resize():
            dummy_flow.alloc_w, dummy_flow.alloc_h = top_menu.alloc_w, top_menu.alloc_h
            dummy_flow.sprites = top_menu.sprites
            dummy_flow.resize_children()
            top_menu.height = top_menu.sprites[-1].y + top_menu.sprites[-1].height

        def flow_height_for_width_size():
            dummy_flow.alloc_w, dummy_flow.alloc_h = top_menu.alloc_w, top_menu.alloc_h
            dummy_flow.sprites = top_menu.sprites
            w, h = dummy_flow.get_height_for_width_size()
            return w, h

        def flow_min_size():
            dummy_flow.sprites = top_menu.sprites
            w, h = dummy_flow.get_min_size()
            return w+ top_menu.horizontal_padding, h  + top_menu.vertical_padding

        # flow if b0rken ATM
        for i in range(20):
            top_menu.add_child(ui.MenuItem(label="flow %d" % i))
        top_menu.resize_children = flow_resize
        #top_menu.get_height_for_width_size = flow_height_for_width_size
        top_menu.get_min_size = flow_min_size





        self.add_child(ui.VBox([top_menu, ui.VBox([self.notebook,
                                                   ui.HBox([self.tab_orient_switch,
                                                            self.page_disablist,
                                                            self.dialog_button], expand = False, fill=False, x_align=1),
                               ], padding=20, spacing=10)], spacing = 10))






        self.connect("on-click", self.on_click)

        self.notebook.after_tabs.add_child(ui.Button("Yohoho"))
        print dt.datetime.now() - now

    def on_tab_orient_click(self, button, event):
        orient = ["left-top", "left-center", "left-bottom",
                  "bottom-left", "bottom-center", "bottom-right",
                  "right-bottom", "right-center", "right-top",
                  "top-right", "top-center", "top-left"]
        self.notebook.tab_position = orient[orient.index(self.notebook.tab_position) -1]
        self.notebook._position_contents()

    def on_page_disablist_click(self, button, event):
        self.notebook.current_page.enabled = not self.notebook.current_page.enabled

    def on_dialog_button_click(self, button, event):
        dialog = ui.ConfirmationDialog("It's friday",
                                       "If you agree, Rebecca will be taking the back seat this time ah noes i'll never fit here. I should wrap for sure, but will that happen? Oh who knows! If you agree, Rebecca will be taking the back seat this time ah noes i'll never fit here. I should wrap for sure, but will that happen? Oh who knows! I should wrap for sure, but will that happen? Oh who knows! If you agree, Rebecca will be taking the back seat this time ah noes i'll never fit here. I should wrap for sure, but will that happen? Oh who knows!",
                                       "Cancel", "I'm fine with that!")
        dialog.show(self)


    def on_button_click(self, button, event):
        orient = ["left", "bottom", "right", "top"]
        button.image_position = orient[orient.index(button.image_position) -1]


    def on_table_mouse_over(self, sprite):
        self.table.animate(vertical_spacing = 10, horizontal_spacing = 10)

    def on_table_mouse_out(self, sprite):
        self.table.animate(vertical_spacing = 0, horizontal_spacing = 0)


    def on_click(self, scene, event, elem):
        if elem and isinstance(elem, Rectangle):
            elem.expand = not elem.expand
            self.redraw()


    def on_corner_drag(self, corner, event):
        min_x, min_y = self.box.get_min_size()

        self.box.alloc_w = max(corner.x - self.box.x + 5, min_x)
        self.box.alloc_h = max(corner.y - self.box.y + 5, min_y)

        self.corner.x = self.box.x + self.box.alloc_w - 5
        self.corner.y = self.box.y + self.box.alloc_h - 5
        self.redraw()



class BasicWindow:
    def __init__(self):
        window = gtk.Window()
        window.set_default_size(800, 600)
        window.connect("delete_event", lambda *args: gtk.main_quit())

        scene = Scene()
        w, h = scene.notebook.get_min_size()
        window.set_size_request(int(w), int(h))
        window.add(scene)
        window.show_all()


if __name__ == '__main__':
    window = BasicWindow()
    import signal
    signal.signal(signal.SIGINT, signal.SIG_DFL) # gtk3 screws up ctrl+c
    gtk.main()

########NEW FILE########
__FILENAME__ = voronoi
#!/usr/bin/env python
# - coding: utf-8 -
# Copyright (C) 2010 Toms Bauģis <toms.baugis at gmail.com>

"""
 Games with points, implemented following Dr. Mike's Maths
 http://www.dr-mikes-maths.com/
"""

from gi.repository import Gtk as gtk
from lib import graphics

import math
from contrib.euclid import Vector2, Point2
import itertools


EPSILON = 0.00001

class Node(graphics.Sprite):
    def __init__(self, x, y):
        graphics.Sprite.__init__(self, x, y, interactive=True, draggable=True)
        self.graphics.rectangle(-5, -5, 10, 10, 3)
        self.graphics.fill("#999")

class Scene(graphics.Scene):
    def __init__(self):
        graphics.Scene.__init__(self)
        self.nodes = [Node(-10000, -10000), Node(10000, -10000), Node(0, 10000)]

        self.connect("on-enter-frame", self.on_enter_frame)
        self.connect("on-click", self.on_mouse_click)
        self.connect("on-drag", self.on_node_drag)

        self.draw_circles = False

    def on_mouse_click(self, area, event, target):
        if not target:
            node = Node(event.x, event.y)
            self.nodes.append(node)
            self.add_child(node)

            self.redraw()


    def on_node_drag(self, scene, node, event):
        self.redraw()


    def on_enter_frame(self, scene, context):

        # voronoi diagram
        context.set_source_rgb(0.7, 0.7, 0.7)
        segments = list(self.voronoi())
        for node, node2 in segments:
            context.move_to(node.x, node.y)
            context.line_to(node2.x, node2.y)
        context.stroke()


    def triangle_circumcenter(self, a, b, c):
        """shockingly, the circumcenter math has been taken from wikipedia
           we move the triangle to 0,0 coordinates to simplify math"""

        p_a = Vector2(a.x, a.y)
        p_b = Vector2(b.x, b.y) - p_a
        p_c = Vector2(c.x, c.y) - p_a

        p_b2 = p_b.magnitude_squared()
        p_c2 = p_c.magnitude_squared()

        d = 2 * (p_b.x * p_c.y - p_b.y * p_c.x)

        if d < 0:
            d = min(d, EPSILON)
        else:
            d = max(d, EPSILON)


        centre_x = (p_c.y * p_b2 - p_b.y * p_c2) / d
        centre_y = (p_b.x * p_c2 - p_c.x * p_b2) / d

        centre = p_a + Vector2(centre_x, centre_y)
        return centre


    def voronoi(self):
        segments = []
        centres = {}
        for a, b, c in itertools.combinations(self.nodes, 3):
            centre = self.triangle_circumcenter(a, b, c)

            distance2 = (Vector2(a.x, a.y) - centre).magnitude_squared()

            smaller_found = False
            for node in self.nodes:
                if node in [a,b,c]:
                    continue

                if (Vector2(node.x, node.y) - centre).magnitude_squared() < distance2:
                    smaller_found = True
                    break

            if not smaller_found:
                order = sorted([a,b,c], key = lambda node: node.x+node.y)
                for a1,b1 in itertools.combinations(order, 2):
                    centres.setdefault((a1,b1), []).append(centre)


        #return centres for all points that share more than one
        #centres = set([c[0] for c in centres.values() if len(c) > 1])

        res = []
        for key in centres:
            if len(centres[key]) > 1:
                for node, node2 in zip(centres[key], centres[key][1:]):
                    res.append((node, node2))

                if len(centres[key]) > 2:
                    res.append((centres[key][-1], centres[key][0]))

        res = set(res)

        return res


class BasicWindow:
    def __init__(self):
        window = gtk.Window()
        window.set_size_request(600, 500)
        window.connect("delete_event", lambda *args: gtk.main_quit())

        self.scene = Scene()

        box = gtk.VBox()
        box.pack_start(self.scene, True, True, 0)

        button = gtk.Button("Clear")
        def on_click(*args):
            self.canvas.nodes = []
            self.canvas.mouse_node, self.canvas.prev_mouse_node = None, None
            self.canvas.redraw()

        button.connect("clicked", on_click)
        box.pack_start(button, False, False, 0)



        window.add(box)
        window.show_all()


if __name__ == "__main__":
    example = BasicWindow()
    import signal
    signal.signal(signal.SIGINT, signal.SIG_DFL) # gtk3 screws up ctrl+c
    gtk.main()

########NEW FILE########
__FILENAME__ = waypoints
#!/usr/bin/env python
# - coding: utf-8 -
# Copyright (C) 2010 Toms Bauģis <toms.baugis at gmail.com>

"""
 Extending the flocking code with different kinds of waypoints.
 Work in progress.
"""

from gi.repository import Gtk as gtk

from lib import graphics

import math
import random

from contrib.euclid import Vector2, Point2
from contrib.proximity import LQProximityStore

class Waypoint(graphics.Sprite):
    def __init__(self, x, y):
        graphics.Sprite.__init__(self, x, y, interactive=True, draggable=True)

        self.graphics.set_color("#999")
        self.graphics.rectangle(-4, -4, 8, 8, 2)
        self.graphics.fill()

        self.connect("on-drag", self.on_drag)

        self.location = Vector2(x, y)
        self.debug = False

    def on_drag(self, sprite, event):
        self.location.x, self.location.y  = event.x, event.y


    def see_you(self, boid):
        # boid calls waypoint when he sees it
        # normally we just tell it to go on
        if boid.data and "reverse" in boid.data:
            boid.target(self.previous)
        else:
            boid.target(self.next)

    def move_on(self, boid):
        boid.visible = True #moves are always visible
        if boid.data and "reverse" in boid.data:
            boid.target(self.previous)
        else:
            boid.target(self.next)

        boid.velocity *= 4

    def update(self, context):
        pass

    def get_next(self, boid):
        if boid.data and "reverse" in boid.data:
            return self.previous
        else:
            return self.next

class QueueingWaypoint(Waypoint):
    """waypoint that eats boids and then releases them after a set period"""
    def __init__(self, x, y, frames):
        Waypoint.__init__(self, x, y)
        self.frames = frames
        self.current_frame = 0
        self.boids = []
        self.boid_scales = {}

    def see_you(self, boid):
        distance = (self.location - boid.location).magnitude_squared()
        if boid not in self.boids and distance < 400:
            if not self.boids:
                self.current_frame = 0

            self.boids.append(boid)
            boid.visible = False


        for boid in self.boids:
            boid.velocity *= 0


    def update(self, context):
        self.current_frame +=1
        if self.current_frame == self.frames:
            self.current_frame = 0
            if self.boids:
                boid = self.boids.pop(0)
                boid.location = Vector2(self.location.x, self.location.y)
                self.move_on(boid)



class BucketWaypoint(Waypoint):
    """waypoint that will queue our friends until required number
       arrives and then let them go"""
    def __init__(self, x, y, bucket_size):
        Waypoint.__init__(self, x, y)
        self.bucket_size = bucket_size
        self.boids = []
        self.boids_out = []
        self.rotation_angle = 0
        self.radius = 80
        self.incremental_angle = False



    def see_you(self, boid):
        # boid calls waypoint when he sees it
        # normally we just tell it to go on
        if boid not in self.boids:
            if (boid.location - self.location).magnitude_squared() < self.radius * self.radius:
                if self.incremental_angle:
                    self.rotation_angle = (boid.location - self.location).heading()
                self.boids.append(boid)


    def update(self, context):
        if len(self.boids) == self.bucket_size:
            self.boids_out = list(self.boids)
            self.boids = []


        self.rotation_angle += 0.02

        if self.incremental_angle:
            nodes = len(self.boids) or 1
        else:
            nodes = self.bucket_size - 1

        angle_step = math.pi * 2 / nodes
        current_angle = 0

        i = 0

        points = []
        while i < (math.pi * 2):
            x = self.location.x + math.cos(self.rotation_angle + i) * self.radius
            y = self.location.y + math.sin(self.rotation_angle + i) * self.radius

            points.append(Vector2(x,y))
            i += angle_step



        context.stroke()

        for boid in self.boids:
            distance = None
            closest_point = None
            for point in points:
                point_distance = (boid.location - point).magnitude_squared()
                if not distance or point_distance < distance:
                    closest_point = point
                    distance = point_distance

            if closest_point:
                target = boid.seek(closest_point)
                #if target.magnitude_squared() < 1:
                #    boid.flight_angle = (self.location - boid.location).cross().heading()

                boid.acceleration *= 8
                points.remove(closest_point) # taken
            else:
                boid.velocity *= .9

        context.stroke()

        if self.boids_out:
            for boid in self.boids_out:
                self.move_on(boid)
                boid.acceleration = -(self.location - boid.location) * 2
                boid.flight_angle = 0

            self.boids_out = []


class RotatingBucketWaypoint(BucketWaypoint):
    def update(self, context):
        BucketWaypoint.update(self, context)
        for boid in self.boids:
            boid.flight_angle += 0.2


class GrowWaypoint(Waypoint):
    """waypoint that will queue our friends until required number
       arrives and then let them go"""
    def __init__(self, x, y, scale):
        Waypoint.__init__(self, x, y)
        self.scale = scale
        self.boid_scales = {}



    def see_you(self, boid):
        # boid calls waypoint when he sees it
        # normally we just tell it to go on
        distance = (self.location - boid.location).magnitude_squared()
        if distance < 400:
            self.move_on(boid)
            del self.boid_scales[boid]
        else: #start braking
            boid.radius = (self.scale * 400 / distance) + (self.boid_scales.setdefault(boid, boid.radius) * (1 - 400 / distance))   #at 400 full scale has been achieved



class ShakyWaypoint(Waypoint):
    def __init__(self, x, y):
        Waypoint.__init__(self, x, y)

    @staticmethod
    def virus(boid, data):
        frame = data.setdefault('frame', 0)
        frame += 1

        if frame > 20:
            seizure = random.random() > 0.4
            if seizure:
                boid.radius = data.setdefault('radius', boid.radius) * (random.random() * 4)
        if frame > 25:
            frame = 0

        data['frame'] = frame


    def see_you(self, boid):

        if boid.virus:
            boid.virus = None
            boid.radius = boid.data['radius']
        else:
            boid.virus = self.virus
        self.move_on(boid)


class Boid(graphics.Sprite):
    def __init__(self, location, max_speed = 2.0):
        graphics.Sprite.__init__(self, snap_to_pixel=False)

        self.visible = True
        self.radius = 3
        self.acceleration = Vector2()
        self.brake = Vector2()
        self.velocity = Vector2(random.random() * 2 - 1, random.random() * 2 - 1)
        self.location = location
        self.max_speed = max_speed
        self.max_force = 0.03
        self.positions = []
        self.message = None # a message that waypoint has set perhaps
        self.flight_angle = 0

        self.data = {}
        self.virus = None

        self.radio = self.radius * 5

        self.target_waypoint = None

        self.connect("on-render", self.on_render)

    def target(self, waypoint):
        self.radio = self.radius * 5
        self.target_waypoint = waypoint

    def run(self, flock_boids):
        if flock_boids:
            self.acceleration += self.separate(flock_boids) * 2

        self.seek(self.target_waypoint.location)

        self.velocity += self.acceleration




        if (self.location - self.target_waypoint.location).magnitude_squared() < self.radio * self.radio:
            self.target_waypoint.see_you(self) #tell waypoint that we see him and hope that he will direct us further

        self.radio += 0.3

        self.velocity.limit(self.max_speed)
        self.location += self.velocity

        self.acceleration *= 0

        if self.virus:
            self.virus(self, self.data)

        self.x, self.y = self.location.x, self.location.y

        #draw boid triangle
        if self.flight_angle:
            self.rotation = self.flight_angle
        else:
            self.rotation = self.velocity.heading() + math.pi / 2



    def on_render(self, context):
        self.graphics.move_to(0, 0)
        self.graphics.line_to(self.acceleration.x * 50, self.acceleration.y * 50)
        self.graphics.stroke()


        self.graphics.move_to(0, -self.radius*2)
        self.graphics.line_to(-self.radius, self.radius * 2)
        self.graphics.line_to(self.radius, self.radius * 2)
        self.graphics.line_to(0, -self.radius*2)

        self.graphics.fill("#aaa")




    def separate(self, boids):
        sum = Vector2()
        in_zone = 0.0

        for boid, d in boids:
            if not boid.visible:
                continue

            if 0 < d < self.radius * 5 * self.radius * 5:
                diff = self.location - boid.location
                diff.normalize()
                diff = diff / math.sqrt(d)  # Weight by distance
                sum += diff
                in_zone += 1

        if in_zone:
            sum = sum / in_zone

        sum.limit(self.max_force)
        return sum


    def seek(self, target):
        steer_vector = self.steer(target, False)
        self.acceleration += steer_vector
        return steer_vector


    def arrive(self, target):
        self.acceleration += self.steer(target, True)

    def steer(self, target, slow_down):
        desired = target - self.location # A vector pointing from the location to the target

        d = desired.magnitude()
        if d > 0:  # this means that we have a target
            desired.normalize()


            # Two options for desired vector magnitude (1 -- based on distance, 2 -- maxspeed)
            if  slow_down and d < self.radius * 5 * self.radius * 5:
                desired *= self.max_speed * (math.sqrt(d) / self.radius * 5) # This damping is somewhat arbitrary
            else:
                desired *= self.max_speed

            steer = desired - self.velocity # Steering = Desired minus Velocity
            steer.limit(self.max_force) # Limit to maximum steering force
            return steer
        else:
            return Vector2()



class Scene(graphics.Scene):
    def __init__(self):
        graphics.Scene.__init__(self)


        # we should redo the boxes when window gets resized
        box_size = 10
        self.proximities = LQProximityStore(Vector2(0,0), Vector2(600,400), box_size)

        self.waypoints = []
        self.waypoints = [QueueingWaypoint(100, 100, 70),
                          BucketWaypoint(500, 100, 10),
                          GrowWaypoint(500, 500, 10),
                          QueueingWaypoint(300, 500, 70),
                          BucketWaypoint(100, 500, 10),
                          GrowWaypoint(100, 300, 3),
                          ]

        for waypoint in self.waypoints:
            self.add_child(waypoint)

        # link them together
        for curr, next in zip(self.waypoints, self.waypoints[1:]):
            curr.next = next
            next.previous = curr

        self.waypoints[0].previous = self.waypoints[-1]
        self.waypoints[-1].next = self.waypoints[0]



        self.boids = [Boid(Vector2(100,100), 2.0) for i in range(15)]

        for i, boid in enumerate(self.boids):
            boid.target(self.waypoints[0])
            self.add_child(boid)

        self.mouse_node = None

        # some debug variables
        self.debug_radius = False
        self.debug_awareness = False

        self.connect("on-enter-frame", self.on_enter_frame)




    def on_enter_frame(self, scene, context):
        c_graphics = graphics.Graphics(context)
        c_graphics.set_line_style(width = 0.8)

        for waypoint in self.waypoints:
            waypoint.update(context)

        for boid in self.boids:
            # the growing antennae circle
            if self.debug_radius:
                c_graphics.set_color("#aaa", 0.3)
                context.arc(boid.location.x,
                            boid.location.y,
                            boid.radio,
                            -math.pi, math.pi)
                context.fill()


            # obstacle awareness circle
            if self.debug_awareness:
                c_graphics.set_color("#aaa", 0.5)
                context.arc(boid.location.x,
                            boid.location.y,
                            boid.awareness,
                            -math.pi, math.pi)
                context.fill()



        for boid in self.boids:
            neighbours = self.proximities.find_neighbours(boid, 40)

            boid.run(neighbours)

            self.proximities.update_position(boid)


            # debug trail (if enabled)
            c_graphics.set_color("#0f0")
            for position1, position2 in zip(boid.positions, boid.positions[1:]):
                context.move_to(position1.x, position1.y)
                context.line_to(position2.x, position2.y)
            context.stroke()


            # line between boid and it's target
            """
            c_graphics.set_color("#999")
            context.move_to(boid.location.x, boid.location.y)
            context.line_to(boid.target_waypoint.location.x,
                                 boid.target_waypoint.location.y)
            context.stroke()
            """


        self.redraw()



class BasicWindow:
    def __init__(self):
        window = gtk.Window()
        window.set_size_request(600, 600)
        window.connect("delete_event", lambda *args: gtk.main_quit())

        scene = Scene()
        window.add(scene)
        window.show_all()


if __name__ == "__main__":
    example = BasicWindow()
    import signal
    signal.signal(signal.SIGINT, signal.SIG_DFL) # gtk3 screws up ctrl+c
    gtk.main()

########NEW FILE########
