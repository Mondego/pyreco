__FILENAME__ = canvas_bridge
try:
    from canvas import *
except ImportError:
    # We're in NodeBox
    def begin_updates():
        pass

    def end_updates():
        pass

    set_fill_color = fill
    fill_rect = rect
    fill_ellipse = oval
    set_stroke_color = stroke
    set_line_width = strokewidth
    move_to = moveto
    
    
    def draw_rect(x, y, width, height):
        """capture and reset current fill color"""
        clr = fill()
        nofill()
        rect(x, y, width, height)
        fill(clr)

    def draw_ellipse(x, y, size_x, size_y):
        """capture and reset current fill color"""
        clr = fill()
        nofill()
        oval(x, y, size_x, size_y)
        fill(clr)

    set_size = size


########NEW FILE########
__FILENAME__ = devices
# pythonista doubles pixels on a retina display, so you really only need half size
ipad = (512.0, 512.0)
ipad_r = (1024.0, 1024.0)
ipad_r_ios7 = (1262.0, 1262.0)
iphone = (160.0, 240.0)
iphone_r = (320.0, 480.0)
iphone_5 = (320.0, 568.0)
iphone_5_ios7 = (372.0, 696.0)
mbp_r = (1440.0, 900.0)
cinema = (1280.0, 800.0)

########NEW FILE########
__FILENAME__ = hexacircles
import canvas
import random
import math

from devices import *
from kuler import *

random.seed()

width, height = cinema
circle_size = 256.0
step = math.sqrt(circle_size**2 - (circle_size / 2.0)**2)

palette = random.choice(themes)

canvas.begin_updates()

canvas.set_size(width, height)
canvas.set_fill_color(*palette.darkest)
canvas.fill_rect(0, 0, width, height)

for x in range(100):
	r, g, b = random.choice(palette.colors)
	a = random.random() * 0.5 + 0.25
	canvas.set_fill_color(r, g, b, a)
	origin_x = random.random() * width
	origin_y = random.random() * height
	csize = random.random() * (width / 8.0) + (width / 16.0)
	canvas.fill_ellipse(origin_x, origin_y, csize, csize)

def rstrokedline(start_x, start_y, end_x, end_y):
	line_width = random.random() * 0.25 + 0.25
	canvas.set_line_width(line_width)
	r, g, b = palette.lightest
	a = random.random() * 0.25 + 0.05
	canvas.set_stroke_color(r, g, b, a)
	canvas.draw_line(start_x, start_y, end_x, end_y)

def hexacircle(start_x, start_y):
	r, g, b = random.choice(palette.colors)

	canvas.set_fill_color(r, g, b, random.random() * 0.75 + 0.25)
	s_r, s_g, s_b = palette.lightest
	canvas.set_stroke_color(s_r, s_g, s_b, random.random() * 0.50 + 0.50)
	canvas.set_line_width(random.random() * 0.25 + 0.25)
	circle = (start_x - (0.5 * circle_size),
	          start_y - (0.5 * circle_size),
	          circle_size, circle_size)
	canvas.draw_ellipse(*circle)
	canvas.fill_ellipse(*circle)

	# draw lines
	rstrokedline(start_x, start_y - circle_size, start_x, start_y + circle_size)
	rstrokedline(start_x - step, start_y, start_x + step, start_y)

	rstrokedline(start_x - step, start_y - (0.5 * circle_size), start_x + step, start_y + (0.5 * circle_size))
	rstrokedline(start_x - step, start_y + (0.5 * circle_size), start_x + step, start_y - (0.5 * circle_size))

	rstrokedline(start_x - step, start_y + (1.5 * circle_size), start_x + step, start_y - (1.5 * circle_size))
	rstrokedline(start_x - step, start_y - (1.5 * circle_size), start_x + step, start_y + (1.5 * circle_size))
    
	rstrokedline(start_x - step, start_y + (2.5 * circle_size), start_x + step, start_y - (2.5 * circle_size))
	rstrokedline(start_x - step, start_y - (2.5 * circle_size), start_x + step, start_y + (2.5 * circle_size))
    
	rstrokedline(start_x - (3.0 * step), start_y + (0.5 * circle_size), start_x + (3.0 * step), start_y - (0.5 * circle_size))
	rstrokedline(start_x - (3.0 * step), start_y - (0.5 * circle_size), start_x + (3.0 * step), start_y + (0.5 * circle_size))

for x in xrange(int(math.ceil(width/circle_size))+1):
	for y in xrange(int(math.ceil(height/circle_size))+1):
		center_x = x * (2.0 * step)
		center_y = y * circle_size
		hexacircle(center_x, center_y)
		hexacircle(center_x + step, center_y + (0.5 * circle_size))

canvas.end_updates()

########NEW FILE########
__FILENAME__ = kuler
import random

from canvas import *

def shade_of(color):
	r, g, b = color
	return r, g, b, random.random() * 0.25 + 0.25

def gen_color(r, g, b):
    return (r/255.0, g/255.0, b/255.0)

def avg(color):
	return float(sum(color) / len(color))

class Theme:
	
	def __init__(self, name, colors):
		self.name = name
		self.colors = [gen_color(*color) for color in colors]
		self.lightest = self.determine_lightest()
		self.darkest = self.determine_darkest()
		
	def determine_lightest(self):
		avgs = [(avg(color), color) for color in self.colors]
		return max(avgs)[1]
		
	def determine_darkest(self):
		avgs = [(avg(color), color) for color in self.colors]
		return min(avgs)[1]

mucha_winter = Theme(
    name='Mucha Winter',
    colors=(
        (242.0, 212.0, 155.0),
        (242.0, 178.0, 102.0),
        (191.0, 111.0, 65.0),
        (89.0, 18.0, 2.0),
        (55.0, 69.0, 65.0),
    ))

mabelis = Theme(
    name='Mabelis',
    colors=(
        (88.0, 0.0, 34.0),
        (170.0, 44.0, 48.0),
        (255.0, 190.0, 141.0),
        (72.0, 123.0, 127.0),
        (1.0, 29.0, 36.0),
    ))

full_of_life = Theme(
    name='Full of Life',
    colors=(
        (2.0, 115.0, 115.0),
        (3.0, 140.0, 127.0),
        (217.0, 179.0, 67.0),
        (242.0, 140.0, 58.0),
        (191.0, 63.0, 52.0),
    ))

let_the_rays_fall_on_the_earth = Theme(
    name='Let the Rays Fall on the Earth',
    colors=(
        (64.0, 39.0, 104.0),
        (127.0, 83.0, 112.0),
        (191.0, 117.0, 96.0),
        (229.0, 141.0, 0.0),
        (255.0, 183.0, 0.0),
    ))

robots_are_cool = Theme(
    name='Robots Are Cool',
    colors=(
        (30.0, 58.0, 64.0),
        (104.0, 140.0, 140.0),
        (217.0, 209.0, 186.0),
        (242.0, 209.0, 148.0),
        (242.0, 160.0, 87.0),
    ))

def draw_block(x, y, theme):
    start_x, start_y = x, y
    for palette_color in theme.colors:
        set_fill_color(*palette_color)
        fill_rect(start_x, start_y, 25.0, 50.0)
        start_x += 25.0
    
    start_x += 10.0
    set_fill_color(*theme.darkest)
    fill_rect(start_x, start_y, 25.0, 50.0)

    start_x += 35.0
    set_fill_color(*theme.lightest)
    fill_rect(start_x, start_y, 25.0, 50.0)

themes = (mucha_winter, mabelis, full_of_life, let_the_rays_fall_on_the_earth, robots_are_cool)

if __name__ == 'main':
	set_size(1024.0, 1024.0)

	start_x = 10.0
	start_y = 10.0

	for theme in themes:
	    draw_block(start_x, start_y, theme)
	    start_y += 60.0

########NEW FILE########
__FILENAME__ = lollipops
import canvas
import random
import math

from devices import *
from kuler import *

random.seed()

width, height = ipad_r_ios7
palette = random.choice(themes)

canvas.begin_updates()

canvas.set_size(width, height)
canvas.set_fill_color(*palette.darkest)
canvas.fill_rect(0, 0, width, height)

canvas.set_fill_color(*random.choice(palette.colors))
canvas.set_stroke_color(*palette.lightest)
start_x, start_y = (width / 2.0, height / 2.0)

lollipop_points = []

for x in xrange(64):
	end_x, end_y = (random.random() * (width * 0.8) + (width * 0.1), random.random() * (height * 0.8) + (height * 0.1))
	lollipop_points.append((end_x, end_y))
	canvas.set_line_width(random.random() * 0.75 + 0.25)
	canvas.draw_line(start_x, start_y, end_x, end_y)
	
size = random.random() * (width * 0.10)
canvas.fill_ellipse(start_x - (size / 2.0), start_y - (size / 2.0), size, size)
canvas.set_line_width(1.25)
canvas.draw_ellipse(start_x - (size / 2.0), start_y - (size / 2.0), size, size)

for x in xrange(64):
	end_x, end_y = lollipop_points[x]
	size = random.random() * (width * 0.10)
	canvas.fill_ellipse(end_x - (size / 2.0), end_y - (size / 2.0), size, size)
	canvas.set_line_width(1.25)
	canvas.draw_ellipse(end_x - (size / 2.0), end_y - (size / 2.0), size, size)

canvas.end_updates()

########NEW FILE########
__FILENAME__ = pixelstorm
import canvas
import random
import math

from devices import *
from kuler import *

random.seed()

width, height = ipad_r
palette = random.choice(themes)

canvas.begin_updates()

canvas.set_size(width, height)
canvas.set_fill_color(*palette.darkest)
canvas.fill_rect(0, 0, width, height)

square_size = 32.0

def fill_square(x, y, size, theme):
	canvas.set_fill_color(*shade_of(random.choice(theme.colors)))
	canvas.draw_rect(x, y, x + size, y + size)
	
def fill_triangles(x, y, size, theme):
	# fill upper triangle
	canvas.set_fill_color(*shade_of(random.choice(theme.colors)))
	canvas.begin_path()
	canvas.move_to(x, y)
	canvas.add_line(x, y + size)
	canvas.add_line(x + size, y + size)
	canvas.add_line(x, y)
	canvas.fill_path()
	
	# fill lower triangle
	canvas.set_fill_color(*shade_of(random.choice(theme.colors)))
	canvas.begin_path()
	canvas.move_to(x, y)
	canvas.add_line(x + size, y + size)
	canvas.add_line(x + size, y)
	canvas.add_line(x, y)
	canvas.fill_path()
	
for gx in xrange(int(width / square_size) + 1):
	for gy in xrange(int(height / square_size) + 1):
		#func = random.choice((fill_square, fill_triangles, fill_triangles, fill_triangles))
		fill_triangles(gx * square_size, gy * square_size, square_size, palette)

canvas.end_updates()

########NEW FILE########
__FILENAME__ = triangles
import canvas
import random
import math

from devices import *
from kuler import *

random.seed()

width, height = iphone_5_ios7
triangle_side = 256.0
palette = random.choice(themes)

canvas.begin_updates()

canvas.set_size(width, height)
canvas.set_fill_color(*palette.darkest)
canvas.fill_rect(0, 0, width, height)

def draw_triangle(x, y, size, num_remaining):
	if num_remaining > 0:
		canvas.set_fill_color(*shade_of(random.choice(palette.colors)))
		canvas.set_stroke_color(*shade_of(random.choice(palette.colors)))
		canvas.set_line_width(random.random() * 0.5 + 0.5)
		step = math.sqrt(size**2 - (size / 2.0)**2)
		canvas.move_to(x - step, y - (size / 2.0))
		canvas.add_line(x, y + size)
		canvas.add_line(x + step, y - (size / 2.0))
		canvas.add_line(x - step, y - (size / 2.0))
		canvas.fill_path()
		canvas.draw_line(x - step, y - (size / 2.0), x, y + size)
		canvas.draw_line(x, y + size, x + step, y - (size / 2.0))
		canvas.draw_line(x + step, y - (size / 2.0), x - step, y - (size / 2.0))
		canvas.draw_line(x, y, x - (step / 2.0), y + (size / 4.0))
		canvas.draw_line(x, y, x + (step / 2.0), y + (size / 4.0))
		canvas.draw_line(x, y, x, y - (size / 2.0))
		canvas.draw_line(x - (step / 2.0), y + (size / 4.0), x + (step / 2.0), y + (size / 4.0))
		canvas.draw_line(x + (step / 2.0), y + (size / 4.0), x, y - (size / 2.0))
		canvas.draw_line(x, y - (size / 2.0), x - (step / 2.0), y + (size / 4.0))
		draw_triangle(random.random() * width, random.random() * height, random.random() * triangle_side, num_remaining - 1)

x = width / 2.0
y = height / 3.0 # figger
draw_triangle(x, y, triangle_side, 100)

canvas.end_updates()

########NEW FILE########
__FILENAME__ = tron_lines
import random
import math

from canvas import *
from kuler import *
from devices import *

random.seed()

def calculate_control_point(radius):
    return (4 * radius * (math.sqrt(2) - 1)) / 3


def calculate_center_square(width, height):
	is_square = is_portrait = is_landscape = False
	is_square = width / height == 1
	if not is_square:
		is_portrait = width / height < 1
		if not is_portrait:
			is_landscape = True
	square_size = min(width, height) / 2.0
	if is_square:
		offset = (square_size / 2.0, square_size / 2.0)
	if is_portrait:
		offset = (square_size / 2.0, (height - square_size) / 2.0)
	if is_landscape:
		offset = ((width - square_size) / 2.0, square_size / 2.0)
	return offset[0], offset[1], square_size


def draw_circle(x, y, size):
	radius = size / 2.0
	offset = calculate_control_point(radius)

	point1 = (x + radius, y)
	point2 = (x + size, y + radius)
	point3 = (x + radius, y + size)
	point4 = (x, y + radius)
	
	main_color = theme.lightest
	main_width = random.random() * 4.5 + 0.5
	off_color = shade_of(theme.lightest)
	off_width = random.random() * 0.75 + 0.5
	
	off = int(random.random() * 4)
	
	segment_colors = [main_color, main_color, main_color, main_color]
	segment_widths = [main_width, main_width, main_width, main_width]
	
	segment_colors[off] = off_color
	segment_widths[off] = off_width
	
	# stroke the circle
	begin_path()
	move_to(*point1)
	set_line_width(segment_widths[0])
	set_stroke_color(*segment_colors[0])
	add_curve(point1[0] + offset, point1[1], point2[0], point2[1] - offset, *point2)
	draw_path()
	begin_path()
	move_to(*point2)
	set_line_width(segment_widths[1])
	set_stroke_color(*segment_colors[1])
	add_curve(point2[0], point2[1] + offset, point3[0] + offset, point3[1], *point3)
	draw_path()
	begin_path()
	move_to(*point3)
	set_line_width(segment_widths[2])
	set_stroke_color(*segment_colors[2])
	add_curve(point3[0] - offset, point3[1], point4[0], point4[1] + offset, *point4)
	draw_path()
	begin_path()
	move_to(*point4)
	set_line_width(segment_widths[3])
	set_stroke_color(*segment_colors[3])
	add_curve(point4[0], point4[1] - offset, point1[0] - offset, point1[1], *point1)
	draw_path()


width, height = ipad_r
grid_x, grid_y, size = calculate_center_square(width, height)

theme = random.choice(themes)

set_size(width, height)

begin_updates()
set_fill_color(*theme.darkest)
fill_rect(0.0, 0.0, width, height)
number_of_circles = 25
for x in xrange(number_of_circles):
	step = size / (number_of_circles * 1.0)
	step += random.random() * step
	draw_circle(grid_x, grid_y, size)
	grid_x += step * 0.20
	grid_y += step * 0.80
	size -= step * 2
end_updates()


########NEW FILE########
