__FILENAME__ = start
import sys
import pantograph
import random
import math
import itertools

class BouncingShape(object):
    def __init__(self, shape):
        self.shape = shape
        self.theta = 0
        self.xvel = random.randint(1, 5)
        self.yvel = random.randint(1, 5)
        self.rvel = (math.pi / 2) * random.random()

    def update(self, canvas):
        rect = self.shape.get_bounding_rect()

        if rect.left <= 0 or rect.right >= canvas.width:
            self.xvel *= -1
        if rect.top <= 0 or rect.bottom >= canvas.height:
            self.yvel *= -1

        self.theta += self.rvel
        if self.theta > math.pi:
            self.theta -= 2 * math.pi

        self.shape.translate(self.xvel, self.yvel)
        self.shape.rotate(self.theta)
        self.shape.draw(canvas)

class BouncingBallDemo(pantograph.PantographHandler):
    def setup(self):
        self.xvel = random.randint(1, 5)
        self.yvel = random.randint(1, 5)

        static_shapes = [
            pantograph.Image("baseball.jpg", 100, 100, 20, 20),
            pantograph.Rect(120, 150, 20, 20, "#f00"),
            pantograph.Circle(15, 300, 10, "#0f0"),
            pantograph.Polygon([
                (60, 10),
                (55, 20),
                (80, 30)
            ], "#00f"),
            pantograph.CompoundShape([
                pantograph.Rect(15, 15, 10, 10, "#0ff"),
                pantograph.Circle(20, 20, 5, "#ff0")
            ])
        ]

        self.shapes = [BouncingShape(shp) for shp in static_shapes]

    def update(self):
        self.clear_rect(0, 0, self.width, self.height)

        for shape in self.shapes:
            shape.update(self)

        for (a, b) in itertools.combinations(self.shapes, 2):
            if a.shape.intersects(b.shape):
                xveltmp = a.xvel
                yveltmp = a.yvel
                a.xvel = b.xvel
                a.yvel = b.yvel
                b.xvel = xveltmp
                b.yvel = yveltmp

if __name__ == '__main__':
    app = pantograph.SimplePantographApplication(BouncingBallDemo)
    app.run()

########NEW FILE########
__FILENAME__ = start
import pantograph
import math

# Animate a spinning wheel on the canvas 

class Rotary(pantograph.PantographHandler):
    def setup(self):
        self.angle = 0
        self.radius = min(self.width, self.height) / 2
    
    def update(self):
        cx = self.radius
        cy = self.radius

        self.clear_rect(0, 0, self.width, self.height)
        # draw the circle for the "rim" of the wheel
        self.draw_circle(self.radius, self.radius, self.radius, "#f00")
        
        # draw eight evenly-spaced "spokes" from the center to the edge
        for i in range(0, 8):
            angle = self.angle + i * math.pi / 4
            x = cx + self.radius * math.cos(angle)
            y = cy + self.radius * math.sin(angle)
            self.draw_line(cx, cy, x, y, "#f00")

        self.angle += math.pi / 64
    
if __name__ == '__main__':
    app = pantograph.SimplePantographApplication(Rotary)
    app.run()

########NEW FILE########
__FILENAME__ = application
import tornado.web
import tornado.ioloop
import json
import os
from .handlers import *
from . import js

class PantographApplication(tornado.web.Application):
    def __init__(self, websock_handlers, **settings):
        constr_args = dict(settings)
        
        if os.path.isfile("./config.json"):
            f = open("./config.json")
            constr_args.update(json.load(f))

        js_path = os.path.dirname(js.__file__)

        handlers = [
            (r"/js/(.*\.js)", tornado.web.StaticFileHandler, {"path":  js_path}),
            (r"/img/(.*)", tornado.web.StaticFileHandler, {"path": "./images"})
        ]

        for name, url, ws_handler in websock_handlers:
            handlers.append((url, MainPageHandler, 
                            {"name" : name, "url" : url}))
            handlers.append((os.path.join(url, "socket"), ws_handler,
                            {"name": name}))

        tornado.web.Application.__init__(self, handlers, **constr_args)

    def run(self, address = "127.0.0.1", port = 8080):
        self.listen(port, address)
        print("Pantograph now running at http://" + address + ":" + str(port))
        tornado.ioloop.IOLoop.instance().start()

class SimplePantographApplication(PantographApplication):
    def __init__(self, handler, **settings):
        PantographApplication.__init__(
            self, [(handler.__name__, "/", handler)], **settings)

########NEW FILE########
__FILENAME__ = handlers
import tornado.web
import tornado.websocket
import tornado.template
from tornado.ioloop import IOLoop

import random
import json
import os
import datetime
from collections import namedtuple

from . import templates

LOADER = tornado.template.Loader(os.path.dirname(templates.__file__))

class MainPageHandler(tornado.web.RequestHandler):
    def initialize(self, name, url):
        self.name = name
        self.url = url
    def get(self):
        t = LOADER.load("index.html")
        
        width = self.settings.get("canvasWidth", "fullWidth")
        height = self.settings.get("canvasHeight", "fullHeight")
        
        if self.name in self.settings:
            width = self.settings[self.name].get("canvasWidth", width)
            height = self.settings[self.name].get("canvasHeight", height)

        ws_url = os.path.join(self.url, "socket")
        
        self.write(t.generate(
            title = self.name, url = self.url, ws_url = ws_url,
            width = width, height = height))

DEFAULT_INTERVAL = 10

InputEvent = namedtuple("InputEvent", ["type", "x", "y", "button", 
                                       "alt_key", "ctrl_key", "meta_key",
                                       "shift_key", "key_code"])

class PantographHandler(tornado.websocket.WebSocketHandler):
    def initialize(self, name):
        self.name = name
        interval = self.settings.get("timer_interval", DEFAULT_INTERVAL)
        if self.name in self.settings:
            interval = self.settings[self.name].get("timer_interval", interval)
        self.interval = interval
    
    def on_canvas_init(self, message):
        self.width = message["width"]
        self.height = message["height"]
        self.setup()
        self.do_operation("refresh")
        # randomize the first timeout so we don't get every timer
        # expiring at the same time
        interval = random.randint(1, self.interval)
        delta = datetime.timedelta(milliseconds = interval)
        self.timeout = IOLoop.current().add_timeout(delta, self.timer_tick)

    def on_close(self):
        IOLoop.current().remove_timeout(self.timeout)

    def on_message(self, raw_message):
        message = json.loads(raw_message)
        event_type = message.get("type")

        if event_type == "setbounds":
            self.on_canvas_init(message)
        else:
            event_callbacks = {
                "mousedown": self.on_mouse_down,
                "mouseup": self.on_mouse_up,
                "mousemove": self.on_mouse_move,
                "click": self.on_click,
                "dblclick": self.on_dbl_click,
                "keydown": self.on_key_down,
                "keyup": self.on_key_up,
                "keypress": self.on_key_press
            }
            event_callbacks[event_type](InputEvent(**message))
    
    def do_operation(self, operation, **kwargs):
        message = dict(kwargs, operation=operation)
        raw_message = json.dumps(message)
        self.write_message(raw_message)
    
    def draw(self, shape_type, **kwargs):
        shape = dict(kwargs, type=shape_type)
        self.do_operation("draw", shape=shape)

    def draw_rect(self, x, y, width, height, color = "#000", **extra):
        self.draw("rect", x=x, y=y, width=width, height=height, 
                          lineColor=color, **extra)

    def fill_rect(self, x, y, width, height, color = "#000", **extra):
        self.draw("rect", x=x, y=y, width=width, height=height, 
                          fillColor=color, **extra)

    def clear_rect(self, x, y, width, height, **extra):
        self.draw("clear", x=x, y=y, width=width, height=height, **extra)
    
    def draw_oval(self, x, y, width, height, color = "#000", **extra):
        self.draw("oval", x=x, y=y, width=width, height=height, 
                          lineColor=color, **extra)
    
    def fill_oval(self, x, y, width, height, color = "#000", **extra):
        self.draw("oval", x=x, y=y, width=width, height=height, 
                          fillColor=color, **extra)

    def draw_circle(self, x, y, radius, color = "#000", **extra):
        self.draw("circle", x=x, y=y, radius=radius, 
                            lineColor=color, **extra)
    
    def fill_circle(self, x, y, radius, color = "#000", **extra):
        self.draw("circle", x=x, y=y, radius=radius, 
                           fillColor=color, **extra)

    def draw_line(self, startX, startY, endX, endY, color = "#000", **extra):
        self.draw("line", startX=startX, startY=startY, 
                          endX=endX, endY=endY, color=color, **extra)

    def fill_polygon(self, points, color = "#000", **extra):
        self.draw("polygon", points=points, fillColor=color, **extra)
    
    def draw_polygon(self, points, color = "#000", **extra):
        self.draw("polygon", points=points, lineColor=color, **extra)

    def draw_image(self, img_name, x, y, width=None, height=None, **extra):
        app_path = os.path.join("./images", img_name)
        handler_path = os.path.join("./images", self.name, img_name)

        if os.path.isfile(handler_path):
            img_src = os.path.join("/img", self.name, img_name)
        elif os.path.isfile(app_path):
            img_src = os.path.join("/img", img_name)
        else:
            raise FileNotFoundError("Could not find " + img_name)
        
        self.draw("image", src=img_src, x=x, y=y, 
                           width=width, height=height, **extra)


    def timer_tick(self):
        self.update()
        self.do_operation("refresh")
        delta = datetime.timedelta(milliseconds = self.interval)
        self.timeout = IOLoop.current().add_timeout(delta, self.timer_tick)

    def setup(self):
        pass

    def update(self):
        pass

    def on_mouse_down(self, event):
        pass

    def on_mouse_up(self, event):
        pass
    
    def on_mouse_move(self, event):
        pass

    def on_click(self, event):
        pass

    def on_dbl_click(self, event):
        pass

    def on_key_down(self, event):
        pass

    def on_key_up(self, event):
        pass

    def on_key_press(self, event):
        pass

########NEW FILE########
__FILENAME__ = shapes
from collections import namedtuple

BoundingRect = namedtuple('BoundingRect', ['left', 'top', 'right', 'bottom'])
Point = namedtuple('Point', ['x', 'y'])

class Shape(object):
    def get_bounding_rect(self):
        raise NotImplementedError

    def draw(self, canvas):
        canvas.draw(self.shape_type(), **self.to_dict())

    def translate(self, dx, dy):
        raise NotImplementedError

    def to_dict(self):
        raise NotImplementedError

    def rotate(self, theta):
        if theta == 0:
            self.rotation = None
        else:
            rect = self.get_bounding_rect()
            rotx = (rect.left + rect.right) / 2
            roty = (rect.top + rect.bottom) / 2
            self.rotation = dict(x=rotx, y=roty, theta=theta)

    def intersects(self, other):
        recta = self.get_bounding_rect()
        rectb = other.get_bounding_rect()
        
        if (recta.left < rectb.left):
            cleft = rectb.left
            cright = recta.right
        elif (recta.left > rectb.left):
            cleft = recta.left
            cright = rectb.right
        elif (recta.right < rectb.right):
            cleft = recta.left
            cright = recta.right
        else:
            cleft = rectb.left
            cright = rectb.right

        if (recta.top < rectb.top):
            ctop = rectb.top
            cbottom = recta.bottom
        elif (recta.top > rectb.top):
            ctop = recta.top
            cbottom = rectb.bottom
        elif (recta.bottom < rectb.bottom):
            ctop = recta.top
            cbottom = recta.bottom
        else:
            ctop = rectb.top
            cbottom = rectb.bottom

        return cleft < cright and ctop < cbottom

    def contains(self, other):
        if isinstance(other, Point):
            rect = self.get_bounding_rect()
            return rect.left < x and rect.right > x and \
                    rect.top < y and rect.bottom > y

        recta = self.get_bounding_rect()

        if isinstance(other, Shape):
            rectb = other.get_bounding_rect()
        elif isinstance(other, BoundingRect):
            rectb = other
        else:
            raise ValueError("other must be a Shape, BoundingRect, or Point")

        return recta.left < rectb.left and recta.right > rectb.right and \
                recta.top < rectb.top and recta.bottom > rectb.bottom

    def shape_type(self):
        return type(self).__name__.lower()


class SimpleShape(Shape):
    def __init__(self, x, y, width, height, fill_color=None, line_color=None):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.fill_color = fill_color
        self.line_color = line_color
        self.rotation = None
    
    def get_bounding_rect(self):
        return BoundingRect(self.x, self.y, 
                            self.x + self.width, 
                            self.y + self.height)
    
    def translate(self, dx, dy):
        self.x += dx
        self.y += dy

    def to_dict(self):
        return dict(x = self.x, y = self.y,
                    width = self.width, height = self.height,
                    fillColor = self.fill_color, lineColor = self.line_color,
                    rotate = self.rotation)
        
class Rect(SimpleShape):
    pass
    
class Oval(SimpleShape):
    pass

class Circle(SimpleShape):
    def __init__(self, x, y, radius, fill_color=None, line_color=None):
        self.x = x
        self.y = y
        self.radius = radius
        self.fill_color = fill_color
        self.line_color = line_color
    
    def get_bounding_rect(self):
        return BoundingRect(self.x - self.radius, self.y - self.radius,
                            self.x + self.radius, self.y + self.radius)

    def to_dict(self):
        return dict(x = self.x, y = self.y, radius = self.radius,
                    fillColor = self.fill_color, lineColor = self.line_color)

class Image(SimpleShape):
    def __init__(self, img_name, x, y, width=None, height=None):
        self.img_name = img_name
        super(Image, self).__init__(x, y, width, height)

    def draw(self, canvas):
        canvas.draw_image(self.img_name, self.x, self.y, 
                          self.width, self.height,
                          rotate = self.rotation)

class Line(Shape):
    def __init__(self, startx, starty, endx, endy, color = None):
        self.startx = startx
        self.starty = starty
        self.endx = endx
        self.endy = endy
        self.color = color

    def to_dict(self):
        return dict(startX = self.startx, startY = self.starty,
                    endX = self.endx, endY = self.endy, 
                    color = self.color, rotate = self.rotation)

    def get_bounding_rect(self):
        if self.startx < self.endx:
            left = self.startx
            right = self.endx
        else:
            left = self.endx
            right = self.startx

        if self.starty < self.endy:
            top = self.starty
            bottom = self.endy
        else:
            top = self.endy
            bottom = self.starty

        return BoundingRect(left, top, right, bottom)

    def translate(self, dx, dy):
        self.startx += dx
        self.starty += dy
        self.endx += dx
        self.endy += dy

class Polygon(Shape):
    def __init__(self, points, fill_color=None, line_color=None):
        self.points = [Point(x, y) for (x, y) in points]
        self.line_color = line_color
        self.fill_color = fill_color
        
        self.minx = min(pt[0] for pt in points)
        self.maxx = max(pt[0] for pt in points)
        self.miny = min(pt[1] for pt in points)
        self.maxy = max(pt[1] for pt in points)

    def translate(self, dx, dy):
        self.minx += dx
        self.maxx += dx
        self.miny += dy
        self.maxy += dy

        self.points = [Point(p.x + dx, p.y + dy) for p in self.points]

    def to_dict(self):
        return dict(points = self.points, 
                    fillColor = self.fill_color,
                    lineColor = self.line_color,
                    rotate = self.rotation)

    def get_bounding_rect(self):
        return BoundingRect(self.minx, self.miny, self.maxx, self.maxy)

class CompoundShape(Shape):
    def __init__(self, shapes):
        self.shapes = shapes
        rects = [shp.get_bounding_rect() for shp in shapes]
        
        self.left = min(rct.left for rct in rects)
        self.right = max(rct.right for rct in rects)
        self.top = min(rct.top for rct in rects)
        self.bottom = max(rct.bottom for rct in rects)

    def translate(self, dx, dy):
        for shp in self.shapes:
            shp.translate(dx, dy)
        self.left += dx
        self.right += dx
        self.top += dy
        self.bottom += dy

    def get_bounding_rect(self):
        return BoundingRect(self.left, self.top, self.right, self.bottom)

    def to_dict(self):
        return dict(shapes=[dict(shp.to_dict(), type=shp.shape_type()) 
                            for shp in self.shapes],
                    rotate = self.rotation)

    def shape_type(self):
        return "compound"

########NEW FILE########
