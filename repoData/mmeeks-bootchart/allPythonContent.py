__FILENAME__ = batch
#  This file is part of pybootchartgui.

#  pybootchartgui is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.

#  pybootchartgui is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.

#  You should have received a copy of the GNU General Public License
#  along with pybootchartgui. If not, see <http://www.gnu.org/licenses/>.

import cairo
from . import draw
from .draw import RenderOptions

def render(writer, trace, app_options, filename):
    handlers = {
        "png": (lambda w, h: cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h), \
                lambda sfc: sfc.write_to_png(filename)),
        "pdf": (lambda w, h: cairo.PDFSurface(filename, w, h), lambda sfc: 0),
        "svg": (lambda w, h: cairo.SVGSurface(filename, w, h), lambda sfc: 0)
    }

    if app_options.format is None:
        fmt = filename.rsplit('.', 1)[1]
    else:
        fmt = app_options.format

    if not (fmt in handlers):
        writer.error ("Unknown format '%s'." % fmt)
        return 10

    make_surface, write_surface = handlers[fmt]
    options = RenderOptions (app_options)
    (w, h) = draw.extents (options, 1.0, trace)
    w = max (w, draw.MIN_IMG_W)
    surface = make_surface (w, h)
    ctx = cairo.Context (surface)
    draw.render (ctx, options, 1.0, trace)
    write_surface (surface)
    writer.status ("bootchart written to '%s'" % filename)


########NEW FILE########
__FILENAME__ = draw
#  This file is part of pybootchartgui.

#  pybootchartgui is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.

#  pybootchartgui is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.

#  You should have received a copy of the GNU General Public License
#  along with pybootchartgui. If not, see <http://www.gnu.org/licenses/>.


import cairo
import math
import re
import random
import colorsys
from operator import itemgetter

class RenderOptions:

	def __init__(self, app_options):
		# should we render a cumulative CPU time chart
		self.cumulative = True
		self.charts = True
		self.kernel_only = False
		self.app_options = app_options

	def proc_tree (self, trace):
		if self.kernel_only:
			return trace.kernel_tree
		else:
			return trace.proc_tree

# Process tree background color.
BACK_COLOR = (1.0, 1.0, 1.0, 1.0)

WHITE = (1.0, 1.0, 1.0, 1.0)
# Process tree border color.
BORDER_COLOR = (0.63, 0.63, 0.63, 1.0)
# Second tick line color.
TICK_COLOR = (0.92, 0.92, 0.92, 1.0)
# 5-second tick line color.
TICK_COLOR_BOLD = (0.86, 0.86, 0.86, 1.0)
# Annotation colour
ANNOTATION_COLOR = (0.63, 0.0, 0.0, 0.5)
# Text color.
TEXT_COLOR = (0.0, 0.0, 0.0, 1.0)

# Font family
FONT_NAME = "Bitstream Vera Sans"
# Title text font.
TITLE_FONT_SIZE = 18
# Default text font.
TEXT_FONT_SIZE = 12
# Axis label font.
AXIS_FONT_SIZE = 11
# Legend font.
LEGEND_FONT_SIZE = 12

# CPU load chart color.
CPU_COLOR = (0.40, 0.55, 0.70, 1.0)
# IO wait chart color.
IO_COLOR = (0.76, 0.48, 0.48, 0.5)
# Disk throughput color.
DISK_TPUT_COLOR = (0.20, 0.71, 0.20, 1.0)
# CPU load chart color.
FILE_OPEN_COLOR = (0.20, 0.71, 0.71, 1.0)
# Mem cached color
MEM_CACHED_COLOR = CPU_COLOR
# Mem used color
MEM_USED_COLOR = IO_COLOR
# Buffers color
MEM_BUFFERS_COLOR = (0.4, 0.4, 0.4, 0.3)
# Swap color
MEM_SWAP_COLOR = DISK_TPUT_COLOR

# Process border color.
PROC_BORDER_COLOR = (0.71, 0.71, 0.71, 1.0)
# Waiting process color.
PROC_COLOR_D = (0.76, 0.48, 0.48, 0.5)
# Running process color.
PROC_COLOR_R = CPU_COLOR
# Sleeping process color.
PROC_COLOR_S = (0.94, 0.94, 0.94, 1.0)
# Stopped process color.
PROC_COLOR_T = (0.94, 0.50, 0.50, 1.0)
# Zombie process color.
PROC_COLOR_Z = (0.71, 0.71, 0.71, 1.0)
# Dead process color.
PROC_COLOR_X = (0.71, 0.71, 0.71, 0.125)
# Paging process color.
PROC_COLOR_W = (0.71, 0.71, 0.71, 0.125)

# Process label color.
PROC_TEXT_COLOR = (0.19, 0.19, 0.19, 1.0)
# Process label font.
PROC_TEXT_FONT_SIZE = 12

# Signature color.
SIG_COLOR = (0.0, 0.0, 0.0, 0.3125)
# Signature font.
SIG_FONT_SIZE = 14
# Signature text.
SIGNATURE = "http://github.com/mmeeks/bootchart"

# Process dependency line color.
DEP_COLOR = (0.75, 0.75, 0.75, 1.0)
# Process dependency line stroke.
DEP_STROKE = 1.0

# Process description date format.
DESC_TIME_FORMAT = "mm:ss.SSS"

# Cumulative coloring bits
HSV_MAX_MOD = 31
HSV_STEP = 7

# Process states
STATE_UNDEFINED = 0
STATE_RUNNING   = 1
STATE_SLEEPING  = 2
STATE_WAITING   = 3
STATE_STOPPED   = 4
STATE_ZOMBIE    = 5

STATE_COLORS = [(0, 0, 0, 0), PROC_COLOR_R, PROC_COLOR_S, PROC_COLOR_D, \
		PROC_COLOR_T, PROC_COLOR_Z, PROC_COLOR_X, PROC_COLOR_W]

# CumulativeStats Types
STAT_TYPE_CPU = 0
STAT_TYPE_IO = 1

# Convert ps process state to an int
def get_proc_state(flag):
	return "RSDTZXW".find(flag) + 1

def draw_text(ctx, text, color, x, y):
	ctx.set_source_rgba(*color)
	ctx.move_to(x, y)
	ctx.show_text(text)

def draw_fill_rect(ctx, color, rect):
	ctx.set_source_rgba(*color)
	ctx.rectangle(*rect)
	ctx.fill()

def draw_rect(ctx, color, rect):
	ctx.set_source_rgba(*color)
	ctx.rectangle(*rect)
	ctx.stroke()

def draw_legend_box(ctx, label, fill_color, x, y, s):
	draw_fill_rect(ctx, fill_color, (x, y - s, s, s))
	draw_rect(ctx, PROC_BORDER_COLOR, (x, y - s, s, s))
	draw_text(ctx, label, TEXT_COLOR, x + s + 5, y)

def draw_legend_line(ctx, label, fill_color, x, y, s):
	draw_fill_rect(ctx, fill_color, (x, y - s/2, s + 1, 3))
	ctx.arc(x + (s + 1)/2.0, y - (s - 3)/2.0, 2.5, 0, 2.0 * math.pi)
	ctx.fill()
	draw_text(ctx, label, TEXT_COLOR, x + s + 5, y)

def draw_label_in_box(ctx, color, label, x, y, w, maxx):
	label_w = ctx.text_extents(label)[2]
	label_x = x + w / 2 - label_w / 2
	if label_w + 10 > w:
		label_x = x + w + 5
	if label_x + label_w > maxx:
		label_x = x - label_w - 5
	draw_text(ctx, label, color, label_x, y)

def draw_sec_labels(ctx, rect, sec_w, nsecs):
	ctx.set_font_size(AXIS_FONT_SIZE)
	prev_x = 0
	for i in range(0, rect[2] + 1, sec_w):
		if ((i / sec_w) % nsecs == 0) :
			label = "%ds" % (i / sec_w)
			label_w = ctx.text_extents(label)[2]
			x = rect[0] + i - label_w/2
			if x >= prev_x:
				draw_text(ctx, label, TEXT_COLOR, x, rect[1] - 2)
				prev_x = x + label_w

def draw_box_ticks(ctx, rect, sec_w):
	draw_rect(ctx, BORDER_COLOR, tuple(rect))

	ctx.set_line_cap(cairo.LINE_CAP_SQUARE)

	for i in range(sec_w, rect[2] + 1, sec_w):
		if ((i / sec_w) % 5 == 0) :
			ctx.set_source_rgba(*TICK_COLOR_BOLD)
		else :
			ctx.set_source_rgba(*TICK_COLOR)
		ctx.move_to(rect[0] + i, rect[1] + 1)
		ctx.line_to(rect[0] + i, rect[1] + rect[3] - 1)
		ctx.stroke()

	ctx.set_line_cap(cairo.LINE_CAP_BUTT)

def draw_annotations(ctx, proc_tree, times, rect):
    ctx.set_line_cap(cairo.LINE_CAP_SQUARE)
    ctx.set_source_rgba(*ANNOTATION_COLOR)
    ctx.set_dash([4, 4])

    for time in times:
        if time is not None:
            x = ((time - proc_tree.start_time) * rect[2] / proc_tree.duration)

            ctx.move_to(rect[0] + x, rect[1] + 1)
            ctx.line_to(rect[0] + x, rect[1] + rect[3] - 1)
            ctx.stroke()

    ctx.set_line_cap(cairo.LINE_CAP_BUTT)
    ctx.set_dash([])

def draw_chart(ctx, color, fill, chart_bounds, data, proc_tree, data_range):
	ctx.set_line_width(0.5)
	x_shift = proc_tree.start_time

	def transform_point_coords(point, x_base, y_base, \
				   xscale, yscale, x_trans, y_trans):
		x = (point[0] - x_base) * xscale + x_trans
		y = (point[1] - y_base) * -yscale + y_trans + chart_bounds[3]
		return x, y

	max_x = max (x for (x, y) in data)
	max_y = max (y for (x, y) in data)
	# avoid divide by zero
	if max_y == 0:
		max_y = 1.0
	xscale = float (chart_bounds[2]) / max_x
	# If data_range is given, scale the chart so that the value range in
	# data_range matches the chart bounds exactly.
	# Otherwise, scale so that the actual data matches the chart bounds.
	if data_range:
		yscale = float(chart_bounds[3]) / (data_range[1] - data_range[0])
		ybase = data_range[0]
	else:
		yscale = float(chart_bounds[3]) / max_y
		ybase = 0

	first = transform_point_coords (data[0], x_shift, ybase, xscale, yscale, \
				        chart_bounds[0], chart_bounds[1])
	last =  transform_point_coords (data[-1], x_shift, ybase, xscale, yscale, \
				        chart_bounds[0], chart_bounds[1])

	ctx.set_source_rgba(*color)
	ctx.move_to(*first)
	for point in data:
		x, y = transform_point_coords (point, x_shift, ybase, xscale, yscale, \
					       chart_bounds[0], chart_bounds[1])
		ctx.line_to(x, y)
	if fill:
		ctx.stroke_preserve()
		ctx.line_to(last[0], chart_bounds[1]+chart_bounds[3])
		ctx.line_to(first[0], chart_bounds[1]+chart_bounds[3])
		ctx.line_to(first[0], first[1])
		ctx.fill()
	else:
		ctx.stroke()
	ctx.set_line_width(1.0)

bar_h = 55
meminfo_bar_h = 2 * bar_h
header_h = 110 + 2 * (30 + bar_h) + 1 * (30 + meminfo_bar_h)
# offsets
off_x, off_y = 10, 10
sec_w_base = 50 # the width of a second
proc_h = 16 # the height of a process
leg_s = 10
MIN_IMG_W = 800
CUML_HEIGHT = 2000 # Increased value to accomodate CPU and I/O Graphs
OPTIONS = None

def extents(options, xscale, trace):
	proc_tree = options.proc_tree(trace)
	w = int (proc_tree.duration * sec_w_base * xscale / 100) + 2*off_x
	h = proc_h * proc_tree.num_proc + 2 * off_y
	if options.charts:
		h += header_h
	if proc_tree.taskstats and options.cumulative:
		h += CUML_HEIGHT + 4 * off_y
	return (w, h)

def clip_visible(clip, rect):
	xmax = max (clip[0], rect[0])
	ymax = max (clip[1], rect[1])
	xmin = min (clip[0] + clip[2], rect[0] + rect[2])
	ymin = min (clip[1] + clip[3], rect[1] + rect[3])
	return (xmin > xmax and ymin > ymax)

def render_charts(ctx, options, clip, trace, curr_y, w, h, sec_w):
	proc_tree = options.proc_tree(trace)

	# render bar legend
	ctx.set_font_size(LEGEND_FONT_SIZE)

	draw_legend_box(ctx, "CPU (user+sys)", CPU_COLOR, off_x, curr_y+20, leg_s)
	draw_legend_box(ctx, "I/O (wait)", IO_COLOR, off_x + 120, curr_y+20, leg_s)

	# render I/O wait
	chart_rect = (off_x, curr_y+30, w, bar_h)
	if clip_visible (clip, chart_rect):
		draw_box_ticks (ctx, chart_rect, sec_w)
		draw_annotations (ctx, proc_tree, trace.times, chart_rect)
		draw_chart (ctx, IO_COLOR, True, chart_rect, \
			    [(sample.time, sample.user + sample.sys + sample.io) for sample in trace.cpu_stats], \
			    proc_tree, None)
		# render CPU load
		draw_chart (ctx, CPU_COLOR, True, chart_rect, \
			    [(sample.time, sample.user + sample.sys) for sample in trace.cpu_stats], \
			    proc_tree, None)

	curr_y = curr_y + 30 + bar_h

	# render second chart
	draw_legend_line(ctx, "Disk throughput", DISK_TPUT_COLOR, off_x, curr_y+20, leg_s)
	draw_legend_box(ctx, "Disk utilization", IO_COLOR, off_x + 120, curr_y+20, leg_s)

        # render I/O utilization
	chart_rect = (off_x, curr_y+30, w, bar_h)
	if clip_visible (clip, chart_rect):
		draw_box_ticks (ctx, chart_rect, sec_w)
		draw_annotations (ctx, proc_tree, trace.times, chart_rect)
		draw_chart (ctx, IO_COLOR, True, chart_rect, \
			    [(sample.time, sample.util) for sample in trace.disk_stats], \
			    proc_tree, None)

	# render disk throughput
	max_sample = max (trace.disk_stats, key = lambda s: s.tput)
	if clip_visible (clip, chart_rect):
		draw_chart (ctx, DISK_TPUT_COLOR, False, chart_rect, \
			    [(sample.time, sample.tput) for sample in trace.disk_stats], \
			    proc_tree, None)

	pos_x = off_x + ((max_sample.time - proc_tree.start_time) * w / proc_tree.duration)

	shift_x, shift_y = -20, 20
	if (pos_x < off_x + 245):
		shift_x, shift_y = 5, 40

	label = "%dMB/s" % round ((max_sample.tput) / 1024.0)
	draw_text (ctx, label, DISK_TPUT_COLOR, pos_x + shift_x, curr_y + shift_y)

	curr_y = curr_y + 30 + bar_h

	# render mem usage
	chart_rect = (off_x, curr_y+30, w, meminfo_bar_h)
	mem_stats = trace.mem_stats
	if mem_stats and clip_visible (clip, chart_rect):
		mem_scale = max(sample.records['MemTotal'] - sample.records['MemFree'] for sample in mem_stats)
		draw_legend_box(ctx, "Mem cached (scale: %u MiB)" % (float(mem_scale) / 1024), MEM_CACHED_COLOR, off_x, curr_y+20, leg_s)
		draw_legend_box(ctx, "Used", MEM_USED_COLOR, off_x + 240, curr_y+20, leg_s)
		draw_legend_box(ctx, "Buffers", MEM_BUFFERS_COLOR, off_x + 360, curr_y+20, leg_s)
		draw_legend_line(ctx, "Swap (scale: %u MiB)" % max([(sample.records['SwapTotal'] - sample.records['SwapFree'])/1024 for sample in mem_stats]), \
				 MEM_SWAP_COLOR, off_x + 480, curr_y+20, leg_s)
		draw_box_ticks(ctx, chart_rect, sec_w)
		draw_annotations(ctx, proc_tree, trace.times, chart_rect)
		draw_chart(ctx, MEM_BUFFERS_COLOR, True, chart_rect, \
			   [(sample.time, sample.records['MemTotal'] - sample.records['MemFree']) for sample in trace.mem_stats], \
			   proc_tree, [0, mem_scale])
		draw_chart(ctx, MEM_USED_COLOR, True, chart_rect, \
			   [(sample.time, sample.records['MemTotal'] - sample.records['MemFree'] - sample.records['Buffers']) for sample in mem_stats], \
			   proc_tree, [0, mem_scale])
		draw_chart(ctx, MEM_CACHED_COLOR, True, chart_rect, \
			   [(sample.time, sample.records['Cached']) for sample in mem_stats], \
			   proc_tree, [0, mem_scale])
		draw_chart(ctx, MEM_SWAP_COLOR, False, chart_rect, \
			   [(sample.time, float(sample.records['SwapTotal'] - sample.records['SwapFree'])) for sample in mem_stats], \
			   proc_tree, None)

		curr_y = curr_y + meminfo_bar_h

	return curr_y

#
# Render the chart.
#
def render(ctx, options, xscale, trace):
	(w, h) = extents (options, xscale, trace)
	global OPTIONS
	OPTIONS = options.app_options

	proc_tree = options.proc_tree (trace)

	# x, y, w, h
	clip = ctx.clip_extents()

	sec_w = int (xscale * sec_w_base)
	ctx.set_line_width(1.0)
	ctx.select_font_face(FONT_NAME)
	draw_fill_rect(ctx, WHITE, (0, 0, max(w, MIN_IMG_W), h))
	w -= 2*off_x
	# draw the title and headers
	if proc_tree.idle:
		duration = proc_tree.idle
	else:
		duration = proc_tree.duration

	if not options.kernel_only:
		curr_y = draw_header (ctx, trace.headers, duration)
	else:
		curr_y = off_y;

	if options.charts:
		curr_y = render_charts (ctx, options, clip, trace, curr_y, w, h, sec_w)

	# draw process boxes
	proc_height = h
	if proc_tree.taskstats and options.cumulative:
		proc_height -= CUML_HEIGHT

	draw_process_bar_chart(ctx, clip, options, proc_tree, trace.times,
			       curr_y, w, proc_height, sec_w)

	curr_y = proc_height
	ctx.set_font_size(SIG_FONT_SIZE)
	draw_text(ctx, SIGNATURE, SIG_COLOR, off_x + 5, proc_height - 8)

	# draw a cumulative CPU-time-per-process graph
	if proc_tree.taskstats and options.cumulative:
		cuml_rect = (off_x, curr_y + off_y, w, CUML_HEIGHT/2 - off_y * 2)
		if clip_visible (clip, cuml_rect):
			draw_cuml_graph(ctx, proc_tree, cuml_rect, duration, sec_w, STAT_TYPE_CPU)

	# draw a cumulative I/O-time-per-process graph
	if proc_tree.taskstats and options.cumulative:
		cuml_rect = (off_x, curr_y + off_y * 100, w, CUML_HEIGHT/2 - off_y * 2)
		if clip_visible (clip, cuml_rect):
			draw_cuml_graph(ctx, proc_tree, cuml_rect, duration, sec_w, STAT_TYPE_IO)

def draw_process_bar_chart(ctx, clip, options, proc_tree, times, curr_y, w, h, sec_w):
	header_size = 0
	if not options.kernel_only:
		draw_legend_box (ctx, "Running (%cpu)",
				 PROC_COLOR_R, off_x    , curr_y + 45, leg_s)
		draw_legend_box (ctx, "Unint.sleep (I/O)",
				 PROC_COLOR_D, off_x+120, curr_y + 45, leg_s)
		draw_legend_box (ctx, "Sleeping",
				 PROC_COLOR_S, off_x+240, curr_y + 45, leg_s)
		draw_legend_box (ctx, "Zombie",
				 PROC_COLOR_Z, off_x+360, curr_y + 45, leg_s)
		header_size = 45

	chart_rect = [off_x, curr_y + header_size + 15,
		      w, h - 2 * off_y - (curr_y + header_size + 15) + proc_h]
	ctx.set_font_size (PROC_TEXT_FONT_SIZE)

	draw_box_ticks (ctx, chart_rect, sec_w)
	if sec_w > 100:
		nsec = 1
	else:
		nsec = 5
	draw_sec_labels (ctx, chart_rect, sec_w, nsec)
	draw_annotations (ctx, proc_tree, times, chart_rect)

	y = curr_y + 60
	for root in proc_tree.process_tree:
		draw_processes_recursively(ctx, root, proc_tree, y, proc_h, chart_rect, clip)
		y = y + proc_h * proc_tree.num_nodes([root])


def draw_header (ctx, headers, duration):
    toshow = [
      ('system.uname', 'uname', lambda s: s),
      ('system.release', 'release', lambda s: s),
      ('system.cpu', 'CPU', lambda s: re.sub('model name\s*:\s*', '', s, 1)),
      ('system.kernel.options', 'kernel options', lambda s: s),
    ]

    header_y = ctx.font_extents()[2] + 10
    ctx.set_font_size(TITLE_FONT_SIZE)
    draw_text(ctx, headers['title'], TEXT_COLOR, off_x, header_y)
    ctx.set_font_size(TEXT_FONT_SIZE)

    for (headerkey, headertitle, mangle) in toshow:
        header_y += ctx.font_extents()[2]
        if headerkey in headers:
            value = headers.get(headerkey)
        else:
            value = ""
        txt = headertitle + ': ' + mangle(value)
        draw_text(ctx, txt, TEXT_COLOR, off_x, header_y)

    dur = duration / 100.0
    txt = 'time : %02d:%05.2f' % (math.floor(dur/60), dur - 60 * math.floor(dur/60))
    if headers.get('system.maxpid') is not None:
        txt = txt + '      max pid: %s' % (headers.get('system.maxpid'))

    header_y += ctx.font_extents()[2]
    draw_text (ctx, txt, TEXT_COLOR, off_x, header_y)

    return header_y

def draw_processes_recursively(ctx, proc, proc_tree, y, proc_h, rect, clip) :
	x = rect[0] +  ((proc.start_time - proc_tree.start_time) * rect[2] / proc_tree.duration)
	w = ((proc.duration) * rect[2] / proc_tree.duration)

	draw_process_activity_colors(ctx, proc, proc_tree, x, y, w, proc_h, rect, clip)
	draw_rect(ctx, PROC_BORDER_COLOR, (x, y, w, proc_h))
	ipid = int(proc.pid)
	if not OPTIONS.show_all:
		cmdString = proc.cmd
	else:
		cmdString = ''
	if (OPTIONS.show_pid or OPTIONS.show_all) and ipid is not 0:
		cmdString = cmdString + " [" + str(ipid // 1000) + "]"
	if OPTIONS.show_all:
		if proc.args:
			cmdString = cmdString + " '" + "' '".join(proc.args) + "'"
		else:
			cmdString = cmdString + " " + proc.exe

	draw_label_in_box(ctx, PROC_TEXT_COLOR, cmdString, x, y + proc_h - 4, w, rect[0] + rect[2])

	next_y = y + proc_h
	for child in proc.child_list:
		if next_y > clip[1] + clip[3]:
			break
		child_x, child_y = draw_processes_recursively(ctx, child, proc_tree, next_y, proc_h, rect, clip)
		draw_process_connecting_lines(ctx, x, y, child_x, child_y, proc_h)
		next_y = next_y + proc_h * proc_tree.num_nodes([child])

	return x, y


def draw_process_activity_colors(ctx, proc, proc_tree, x, y, w, proc_h, rect, clip):

	if y > clip[1] + clip[3] or y + proc_h + 2 < clip[1]:
		return

	draw_fill_rect(ctx, PROC_COLOR_S, (x, y, w, proc_h))

	last_tx = -1
	for sample in proc.samples :
		tx = rect[0] + round(((sample.time - proc_tree.start_time) * rect[2] / proc_tree.duration))

		# samples are sorted chronologically
		if tx < clip[0]:
			continue
		if tx > clip[0] + clip[2]:
			break

		tw = round(proc_tree.sample_period * rect[2] / float(proc_tree.duration))
		if last_tx != -1 and abs(last_tx - tx) <= tw:
			tw -= last_tx - tx
			tx = last_tx
		tw = max (tw, 1) # nice to see at least something

		last_tx = tx + tw
		state = get_proc_state( sample.state )

		color = STATE_COLORS[state]
		if state == STATE_RUNNING:
			alpha = min (sample.cpu_sample.user + sample.cpu_sample.sys, 1.0)
			color = tuple(list(PROC_COLOR_R[0:3]) + [alpha])
#			print "render time %d [ tx %d tw %d ], sample state %s color %s alpha %g" % (sample.time, tx, tw, state, color, alpha)
		elif state == STATE_SLEEPING:
			continue

		draw_fill_rect(ctx, color, (tx, y, tw, proc_h))

def draw_process_connecting_lines(ctx, px, py, x, y, proc_h):
	ctx.set_source_rgba(*DEP_COLOR)
	ctx.set_dash([2, 2])
	if abs(px - x) < 3:
		dep_off_x = 3
		dep_off_y = proc_h / 4
		ctx.move_to(x, y + proc_h / 2)
		ctx.line_to(px - dep_off_x, y + proc_h / 2)
		ctx.line_to(px - dep_off_x, py - dep_off_y)
		ctx.line_to(px, py - dep_off_y)
	else:
		ctx.move_to(x, y + proc_h / 2)
		ctx.line_to(px, y + proc_h / 2)
		ctx.line_to(px, py)
	ctx.stroke()
	ctx.set_dash([])

# elide the bootchart collector - it is quite distorting
def elide_bootchart(proc):
	return proc.cmd == 'bootchartd' or proc.cmd == 'bootchart-colle'

class CumlSample:
	def __init__(self, proc):
		self.cmd = proc.cmd
		self.samples = []
		self.merge_samples (proc)
		self.color = None

	def merge_samples(self, proc):
		self.samples.extend (proc.samples)
		self.samples.sort (key = lambda p: p.time)

	def next(self):
		global palette_idx
		palette_idx += HSV_STEP
		return palette_idx

	def get_color(self):
		if self.color is None:
			i = self.next() % HSV_MAX_MOD
			h = 0.0
			if i is not 0:
				h = (1.0 * i) / HSV_MAX_MOD
			s = 0.5
			v = 1.0
			c = colorsys.hsv_to_rgb (h, s, v)
			self.color = (c[0], c[1], c[2], 1.0)
		return self.color


def draw_cuml_graph(ctx, proc_tree, chart_bounds, duration, sec_w, stat_type):
	global palette_idx
	palette_idx = 0

	time_hash = {}
	total_time = 0.0
	m_proc_list = {}

	if stat_type is STAT_TYPE_CPU:
		sample_value = 'cpu'
	else:
		sample_value = 'io'
	for proc in proc_tree.process_list:
		if elide_bootchart(proc):
			continue

		for sample in proc.samples:
			total_time += getattr(sample.cpu_sample, sample_value)
			if not sample.time in time_hash:
				time_hash[sample.time] = 1

		# merge pids with the same cmd
		if not proc.cmd in m_proc_list:
			m_proc_list[proc.cmd] = CumlSample (proc)
			continue
		s = m_proc_list[proc.cmd]
		s.merge_samples (proc)

	# all the sample times
	times = sorted(time_hash)
	if len (times) < 2:
		print("degenerate boot chart")
		return

	pix_per_ns = chart_bounds[3] / total_time
#	print "total time: %g pix-per-ns %g" % (total_time, pix_per_ns)

	# FIXME: we have duplicates in the process list too [!] - why !?

	# Render bottom up, left to right
	below = {}
	for time in times:
		below[time] = chart_bounds[1] + chart_bounds[3]

	# same colors each time we render
	random.seed (0)

	ctx.set_line_width(1)

	legends = []
	labels = []

	# render each pid in order
	for cs in m_proc_list.values():
		row = {}
		cuml = 0.0

		# print "pid : %s -> %g samples %d" % (proc.cmd, cuml, len (cs.samples))
		for sample in cs.samples:
			cuml += getattr(sample.cpu_sample, sample_value)
			row[sample.time] = cuml

		process_total_time = cuml

		# hide really tiny processes
		if cuml * pix_per_ns <= 2:
			continue

		last_time = times[0]
		y = last_below = below[last_time]
		last_cuml = cuml = 0.0

		ctx.set_source_rgba(*cs.get_color())
		for time in times:
			render_seg = False

			# did the underlying trend increase ?
			if below[time] != last_below:
				last_below = below[last_time]
				last_cuml = cuml
				render_seg = True

			# did we move up a pixel increase ?
			if time in row:
				nc = round (row[time] * pix_per_ns)
				if nc != cuml:
					last_cuml = cuml
					cuml = nc
					render_seg = True

#			if last_cuml > cuml:
#				assert fail ... - un-sorted process samples

			# draw the trailing rectangle from the last time to
			# before now, at the height of the last segment.
			if render_seg:
				w = math.ceil ((time - last_time) * chart_bounds[2] / proc_tree.duration) + 1
				x = chart_bounds[0] + round((last_time - proc_tree.start_time) * chart_bounds[2] / proc_tree.duration)
				ctx.rectangle (x, below[last_time] - last_cuml, w, last_cuml)
				ctx.fill()
#				ctx.stroke()
				last_time = time
				y = below [time] - cuml

			row[time] = y

		# render the last segment
		x = chart_bounds[0] + round((last_time - proc_tree.start_time) * chart_bounds[2] / proc_tree.duration)
		y = below[last_time] - cuml
		ctx.rectangle (x, y, chart_bounds[2] - x, cuml)
		ctx.fill()
#		ctx.stroke()

		# render legend if it will fit
		if cuml > 8:
			label = cs.cmd
			extnts = ctx.text_extents(label)
			label_w = extnts[2]
			label_h = extnts[3]
#			print "Text extents %g by %g" % (label_w, label_h)
			labels.append((label,
				       chart_bounds[0] + chart_bounds[2] - label_w - off_x * 2,
				       y + (cuml + label_h) / 2))
			if cs in legends:
				print("ARGH - duplicate process in list !")

		legends.append ((cs, process_total_time))

		below = row

	# render grid-lines over the top
	draw_box_ticks(ctx, chart_bounds, sec_w)

	# render labels
	for l in labels:
		draw_text(ctx, l[0], TEXT_COLOR, l[1], l[2])

	# Render legends
	font_height = 20
	label_width = 300
	LEGENDS_PER_COL = 15
	LEGENDS_TOTAL = 45
	ctx.set_font_size (TITLE_FONT_SIZE)
	dur_secs = duration / 100
	cpu_secs = total_time / 1000000000

	# misleading - with multiple CPUs ...
#	idle = ((dur_secs - cpu_secs) / dur_secs) * 100.0
	if stat_type is STAT_TYPE_CPU:
		label = "Cumulative CPU usage, by process; total CPU: " \
			" %.5g(s) time: %.3g(s)" % (cpu_secs, dur_secs)
	else:
		label = "Cumulative I/O usage, by process; total I/O: " \
			" %.5g(s) time: %.3g(s)" % (cpu_secs, dur_secs)

	draw_text(ctx, label, TEXT_COLOR, chart_bounds[0] + off_x,
		  chart_bounds[1] + font_height)

	i = 0
	legends = sorted(legends, key=itemgetter(1), reverse=True)
	ctx.set_font_size(TEXT_FONT_SIZE)
	for t in legends:
		cs = t[0]
		time = t[1]
		x = chart_bounds[0] + off_x + int (i/LEGENDS_PER_COL) * label_width
		y = chart_bounds[1] + font_height * ((i % LEGENDS_PER_COL) + 2)
		str = "%s - %.0f(ms) (%2.2f%%)" % (cs.cmd, time/1000000, (time/total_time) * 100.0)
		draw_legend_box(ctx, str, cs.color, x, y, leg_s)
		i = i + 1
		if i >= LEGENDS_TOTAL:
			break

########NEW FILE########
__FILENAME__ = gui
#  This file is part of pybootchartgui.

#  pybootchartgui is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.

#  pybootchartgui is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.

#  You should have received a copy of the GNU General Public License
#  along with pybootchartgui. If not, see <http://www.gnu.org/licenses/>.

import gobject
import gtk
import gtk.gdk
import gtk.keysyms
from . import draw
from .draw import RenderOptions

class PyBootchartWidget(gtk.DrawingArea):
    __gsignals__ = {
            'expose-event': 'override',
            'clicked' : (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_STRING, gtk.gdk.Event)),
            'position-changed' : (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_INT, gobject.TYPE_INT)),
            'set-scroll-adjustments' : (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gtk.Adjustment, gtk.Adjustment))
    }

    def __init__(self, trace, options, xscale):
        gtk.DrawingArea.__init__(self)

        self.trace = trace
        self.options = options

        self.set_flags(gtk.CAN_FOCUS)

        self.add_events(gtk.gdk.BUTTON_PRESS_MASK | gtk.gdk.BUTTON_RELEASE_MASK)
        self.connect("button-press-event", self.on_area_button_press)
        self.connect("button-release-event", self.on_area_button_release)
        self.add_events(gtk.gdk.POINTER_MOTION_MASK | gtk.gdk.POINTER_MOTION_HINT_MASK | gtk.gdk.BUTTON_RELEASE_MASK)
        self.connect("motion-notify-event", self.on_area_motion_notify)
        self.connect("scroll-event", self.on_area_scroll_event)
        self.connect('key-press-event', self.on_key_press_event)

        self.connect('set-scroll-adjustments', self.on_set_scroll_adjustments)
        self.connect("size-allocate", self.on_allocation_size_changed)
        self.connect("position-changed", self.on_position_changed)

        self.zoom_ratio = 1.0
        self.xscale = xscale
        self.x, self.y = 0.0, 0.0

        self.chart_width, self.chart_height = draw.extents(self.options, self.xscale, self.trace)
        self.hadj = None
        self.vadj = None
        self.hadj_changed_signal_id = None
        self.vadj_changed_signal_id = None

    def do_expose_event(self, event):
        cr = self.window.cairo_create()

        # set a clip region for the expose event
        cr.rectangle(
                event.area.x, event.area.y,
                event.area.width, event.area.height
        )
        cr.clip()
        self.draw(cr, self.get_allocation())
        return False

    def draw(self, cr, rect):
        cr.set_source_rgba(1.0, 1.0, 1.0, 1.0)
        cr.paint()
        cr.scale(self.zoom_ratio, self.zoom_ratio)
        cr.translate(-self.x, -self.y)
        draw.render(cr, self.options, self.xscale, self.trace)

    def position_changed(self):
        self.emit("position-changed", self.x, self.y)

    ZOOM_INCREMENT = 1.25

    def zoom_image (self, zoom_ratio):
        self.zoom_ratio = zoom_ratio
        self._set_scroll_adjustments (self.hadj, self.vadj)
        self.queue_draw()

    def zoom_to_rect (self, rect):
        zoom_ratio = float(rect.width)/float(self.chart_width)
        self.zoom_image(zoom_ratio)
        self.x = 0
        self.position_changed()

    def set_xscale(self, xscale):
        old_mid_x = self.x + self.hadj.page_size / 2
        self.xscale = xscale
        self.chart_width, self.chart_height = draw.extents(self.options, self.xscale, self.trace)
        new_x = old_mid_x
        self.zoom_image (self.zoom_ratio)

    def on_expand(self, action):
        self.set_xscale (self.xscale * 1.5)

    def on_contract(self, action):
        self.set_xscale (self.xscale / 1.5)

    def on_zoom_in(self, action):
        self.zoom_image(self.zoom_ratio * self.ZOOM_INCREMENT)

    def on_zoom_out(self, action):
        self.zoom_image(self.zoom_ratio / self.ZOOM_INCREMENT)

    def on_zoom_fit(self, action):
        self.zoom_to_rect(self.get_allocation())

    def on_zoom_100(self, action):
        self.zoom_image(1.0)
        self.set_xscale(1.0)

    def show_toggled(self, button):
        self.options.app_options.show_all = button.get_property ('active')
        self.queue_draw()

    POS_INCREMENT = 100

    def on_key_press_event(self, widget, event):
        if event.keyval == gtk.keysyms.Left:
            self.x -= self.POS_INCREMENT/self.zoom_ratio
        elif event.keyval == gtk.keysyms.Right:
            self.x += self.POS_INCREMENT/self.zoom_ratio
        elif event.keyval == gtk.keysyms.Up:
            self.y -= self.POS_INCREMENT/self.zoom_ratio
        elif event.keyval == gtk.keysyms.Down:
            self.y += self.POS_INCREMENT/self.zoom_ratio
        else:
            return False
        self.queue_draw()
        self.position_changed()
        return True

    def on_area_button_press(self, area, event):
        if event.button == 2 or event.button == 1:
            area.window.set_cursor(gtk.gdk.Cursor(gtk.gdk.FLEUR))
            self.prevmousex = event.x
            self.prevmousey = event.y
        if event.type not in (gtk.gdk.BUTTON_PRESS, gtk.gdk.BUTTON_RELEASE):
            return False
        return False

    def on_area_button_release(self, area, event):
        if event.button == 2 or event.button == 1:
            area.window.set_cursor(gtk.gdk.Cursor(gtk.gdk.ARROW))
            self.prevmousex = None
            self.prevmousey = None
            return True
        return False

    def on_area_scroll_event(self, area, event):
        if event.state & gtk.gdk.CONTROL_MASK:
            if event.direction == gtk.gdk.SCROLL_UP:
                self.zoom_image(self.zoom_ratio * self.ZOOM_INCREMENT)
                return True
            if event.direction == gtk.gdk.SCROLL_DOWN:
                self.zoom_image(self.zoom_ratio / self.ZOOM_INCREMENT)
                return True
            return False

    def on_area_motion_notify(self, area, event):
        state = event.state
        if state & gtk.gdk.BUTTON2_MASK or state & gtk.gdk.BUTTON1_MASK:
            x, y = int(event.x), int(event.y)
            # pan the image
            self.x += (self.prevmousex - x)/self.zoom_ratio
            self.y += (self.prevmousey - y)/self.zoom_ratio
            self.queue_draw()
            self.prevmousex = x
            self.prevmousey = y
            self.position_changed()
        return True

    def on_set_scroll_adjustments(self, area, hadj, vadj):
        self._set_scroll_adjustments (hadj, vadj)

    def on_allocation_size_changed(self, widget, allocation):
        self.hadj.page_size = allocation.width
        self.hadj.page_increment = allocation.width * 0.9
        self.vadj.page_size = allocation.height
        self.vadj.page_increment = allocation.height * 0.9

    def _set_adj_upper(self, adj, upper):
        changed = False
        value_changed = False

        if adj.upper != upper:
            adj.upper = upper
            changed = True

        max_value = max(0.0, upper - adj.page_size)
        if adj.value > max_value:
            adj.value = max_value
            value_changed = True

        if changed:
            adj.changed()
        if value_changed:
            adj.value_changed()

    def _set_scroll_adjustments(self, hadj, vadj):
        if hadj == None:
            hadj = gtk.Adjustment(0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        if vadj == None:
            vadj = gtk.Adjustment(0.0, 0.0, 0.0, 0.0, 0.0, 0.0)

        if self.hadj_changed_signal_id != None and \
           self.hadj != None and hadj != self.hadj:
            self.hadj.disconnect (self.hadj_changed_signal_id)
        if self.vadj_changed_signal_id != None and \
           self.vadj != None and vadj != self.vadj:
            self.vadj.disconnect (self.vadj_changed_signal_id)

        if hadj != None:
            self.hadj = hadj
            self._set_adj_upper (self.hadj, self.zoom_ratio * self.chart_width)
            self.hadj_changed_signal_id = self.hadj.connect('value-changed', self.on_adjustments_changed)

        if vadj != None:
            self.vadj = vadj
            self._set_adj_upper (self.vadj, self.zoom_ratio * self.chart_height)
            self.vadj_changed_signal_id = self.vadj.connect('value-changed', self.on_adjustments_changed)

    def on_adjustments_changed(self, adj):
        self.x = self.hadj.value / self.zoom_ratio
        self.y = self.vadj.value / self.zoom_ratio
        self.queue_draw()

    def on_position_changed(self, widget, x, y):
        self.hadj.value = x * self.zoom_ratio
        self.vadj.value = y * self.zoom_ratio

PyBootchartWidget.set_set_scroll_adjustments_signal('set-scroll-adjustments')

class PyBootchartShell(gtk.VBox):
    ui = '''
    <ui>
            <toolbar name="ToolBar">
                    <toolitem action="Expand"/>
                    <toolitem action="Contract"/>
                    <separator/>
                    <toolitem action="ZoomIn"/>
                    <toolitem action="ZoomOut"/>
                    <toolitem action="ZoomFit"/>
                    <toolitem action="Zoom100"/>
            </toolbar>
    </ui>
    '''
    def __init__(self, window, trace, options, xscale):
        gtk.VBox.__init__(self)

        self.widget = PyBootchartWidget(trace, options, xscale)

        # Create a UIManager instance
        uimanager = self.uimanager = gtk.UIManager()

        # Add the accelerator group to the toplevel window
        accelgroup = uimanager.get_accel_group()
        window.add_accel_group(accelgroup)

        # Create an ActionGroup
        actiongroup = gtk.ActionGroup('Actions')
        self.actiongroup = actiongroup

        # Create actions
        actiongroup.add_actions((
                ('Expand', gtk.STOCK_ADD, None, None, None, self.widget.on_expand),
                ('Contract', gtk.STOCK_REMOVE, None, None, None, self.widget.on_contract),
                ('ZoomIn', gtk.STOCK_ZOOM_IN, None, None, None, self.widget.on_zoom_in),
                ('ZoomOut', gtk.STOCK_ZOOM_OUT, None, None, None, self.widget.on_zoom_out),
                ('ZoomFit', gtk.STOCK_ZOOM_FIT, 'Fit Width', None, None, self.widget.on_zoom_fit),
                ('Zoom100', gtk.STOCK_ZOOM_100, None, None, None, self.widget.on_zoom_100),
        ))

        # Add the actiongroup to the uimanager
        uimanager.insert_action_group(actiongroup, 0)

        # Add a UI description
        uimanager.add_ui_from_string(self.ui)

        # Scrolled window
        scrolled = gtk.ScrolledWindow()
        scrolled.add(self.widget)

        # toolbar / h-box
        hbox = gtk.HBox(False, 8)

        # Create a Toolbar
        toolbar = uimanager.get_widget('/ToolBar')
        hbox.pack_start(toolbar, True, True)

        if not options.kernel_only:
            # Misc. options
            button = gtk.CheckButton("Show more")
            button.connect ('toggled', self.widget.show_toggled)
            hbox.pack_start (button, False, True)

        self.pack_start(hbox, False)
        self.pack_start(scrolled)
        self.show_all()

    def grab_focus(self, window):
        window.set_focus(self.widget)


class PyBootchartWindow(gtk.Window):

    def __init__(self, trace, app_options):
        gtk.Window.__init__(self)

        window = self
        window.set_title("Bootchart %s" % trace.filename)
        window.set_default_size(750, 550)

        tab_page = gtk.Notebook()
        tab_page.show()
        window.add(tab_page)

        full_opts = RenderOptions(app_options)
        full_tree = PyBootchartShell(window, trace, full_opts, 1.0)
        tab_page.append_page (full_tree, gtk.Label("Full tree"))

        if trace.kernel is not None and len (trace.kernel) > 2:
            kernel_opts = RenderOptions(app_options)
            kernel_opts.cumulative = False
            kernel_opts.charts = False
            kernel_opts.kernel_only = True
            kernel_tree = PyBootchartShell(window, trace, kernel_opts, 5.0)
            tab_page.append_page (kernel_tree, gtk.Label("Kernel boot"))

        full_tree.grab_focus(self)
        self.show()


def show(trace, options):
    win = PyBootchartWindow(trace, options)
    win.connect('destroy', gtk.main_quit)
    gtk.main()

########NEW FILE########
__FILENAME__ = parsing
#  This file is part of pybootchartgui.

#  pybootchartgui is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.

#  pybootchartgui is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.

#  You should have received a copy of the GNU General Public License
#  along with pybootchartgui. If not, see <http://www.gnu.org/licenses/>.


from __future__ import with_statement

import os
import string
import re
import sys
import tarfile
from time import clock
from collections import defaultdict
from functools import reduce

from .samples import *
from .process_tree import ProcessTree

if sys.version_info >= (3, 0):
    long = int

# Parsing produces as its end result a 'Trace'

class Trace:
    def __init__(self, writer, paths, options):
        self.headers = None
        self.disk_stats = None
        self.ps_stats = None
        self.taskstats = None
        self.cpu_stats = None
        self.cmdline = None
        self.kernel = None
        self.kernel_tree = None
        self.filename = None
        self.parent_map = None
        self.mem_stats = None

        parse_paths (writer, self, paths)
        if not self.valid():
            raise ParseError("empty state: '%s' does not contain a valid bootchart" % ", ".join(paths))

        # Turn that parsed information into something more useful
        # link processes into a tree of pointers, calculate statistics
        self.compile(writer)

        # Crop the chart to the end of the first idle period after the given
        # process
        if options.crop_after:
            idle = self.crop (writer, options.crop_after)
        else:
            idle = None

        # Annotate other times as the first start point of given process lists
        self.times = [ idle ]
        if options.annotate:
            for procnames in options.annotate:
                names = [x[:15] for x in procnames.split(",")]
                for proc in self.ps_stats.process_map.values():
                    if proc.cmd in names:
                        self.times.append(proc.start_time)
                        break
                    else:
                        self.times.append(None)

        self.proc_tree = ProcessTree(writer, self.kernel, self.ps_stats,
                                     self.ps_stats.sample_period,
                                     self.headers.get("profile.process"),
                                     options.prune, idle, self.taskstats,
                                     self.parent_map is not None)

        if self.kernel is not None:
            self.kernel_tree = ProcessTree(writer, self.kernel, None, 0,
                                           self.headers.get("profile.process"),
                                           False, None, None, True)

    def valid(self):
        return self.headers != None and self.disk_stats != None and \
               self.ps_stats != None and self.cpu_stats != None


    def compile(self, writer):

        def find_parent_id_for(pid):
            if pid is 0:
                return 0
            ppid = self.parent_map.get(pid)
            if ppid:
                # many of these double forks are so short lived
                # that we have no samples, or process info for them
                # so climb the parent hierarcy to find one
                if int (ppid * 1000) not in self.ps_stats.process_map:
#                    print "Pid '%d' short lived with no process" % ppid
                    ppid = find_parent_id_for (ppid)
#                else:
#                    print "Pid '%d' has an entry" % ppid
            else:
#                print "Pid '%d' missing from pid map" % pid
                return 0
            return ppid

        # merge in the cmdline data
        if self.cmdline is not None:
            for proc in self.ps_stats.process_map.values():
                rpid = int (proc.pid // 1000)
                if rpid in self.cmdline:
                    cmd = self.cmdline[rpid]
                    proc.exe = cmd['exe']
                    proc.args = cmd['args']
#                else:
#                    print "proc %d '%s' not in cmdline" % (rpid, proc.exe)

        # re-parent any stray orphans if we can
        if self.parent_map is not None:
            for process in self.ps_stats.process_map.values():
                ppid = find_parent_id_for (int(process.pid // 1000))
                if ppid:
                    process.ppid = ppid * 1000

        # stitch the tree together with pointers
        for process in self.ps_stats.process_map.values():
            process.set_parent (self.ps_stats.process_map)

        # count on fingers variously
        for process in self.ps_stats.process_map.values():
            process.calc_stats (self.ps_stats.sample_period)

    def crop(self, writer, crop_after):

        def is_idle_at(util, start, j):
            k = j + 1
            while k < len(util) and util[k][0] < start + 300:
                k += 1
            k = min(k, len(util)-1)

            if util[j][1] >= 0.25:
                return False

            avgload = sum(u[1] for u in util[j:k+1]) / (k-j+1)
            if avgload < 0.25:
                return True
            else:
                return False
        def is_idle(util, start):
            for j in range(0, len(util)):
                if util[j][0] < start:
                    continue
                return is_idle_at(util, start, j)
            else:
                return False

        names = [x[:15] for x in crop_after.split(",")]
        for proc in self.ps_stats.process_map.values():
            if proc.cmd in names or proc.exe in names:
                writer.info("selected proc '%s' from list (start %d)"
                            % (proc.cmd, proc.start_time))
                break
        if proc is None:
            writer.warn("no selected crop proc '%s' in list" % crop_after)


        cpu_util = [(sample.time, sample.user + sample.sys + sample.io) for sample in self.cpu_stats]
        disk_util = [(sample.time, sample.util) for sample in self.disk_stats]

        idle = None
        for i in range(0, len(cpu_util)):
            if cpu_util[i][0] < proc.start_time:
                continue
            if is_idle_at(cpu_util, cpu_util[i][0], i) \
               and is_idle(disk_util, cpu_util[i][0]):
                idle = cpu_util[i][0]
                break

        if idle is None:
            writer.warn ("not idle after proc '%s'" % crop_after)
            return None

        crop_at = idle + 300
        writer.info ("cropping at time %d" % crop_at)
        while len (self.cpu_stats) \
                    and self.cpu_stats[-1].time > crop_at:
            self.cpu_stats.pop()
        while len (self.disk_stats) \
                    and self.disk_stats[-1].time > crop_at:
            self.disk_stats.pop()

        self.ps_stats.end_time = crop_at

        cropped_map = {}
        for key, value in self.ps_stats.process_map.items():
            if (value.start_time <= crop_at):
                cropped_map[key] = value

        for proc in cropped_map.values():
            proc.duration = min (proc.duration, crop_at - proc.start_time)
            while len (proc.samples) \
                        and proc.samples[-1].time > crop_at:
                proc.samples.pop()

        self.ps_stats.process_map = cropped_map

        return idle



class ParseError(Exception):
    """Represents errors during parse of the bootchart."""
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return self.value

def _parse_headers(file):
    """Parses the headers of the bootchart."""
    def parse(acc, line):
        (headers, last) = acc
        if '=' in line:
            last, value = map (lambda x: x.strip(), line.split('=', 1))
        else:
            value = line.strip()
        headers[last] += value
        return headers, last
    return reduce(parse, file.read().decode('utf-8').split('\n'), (defaultdict(str),''))[0]

def _parse_timed_blocks(file):
    """Parses (ie., splits) a file into so-called timed-blocks. A
    timed-block consists of a timestamp on a line by itself followed
    by zero or more lines of data for that point in time."""
    def parse(block):
        lines = block.split('\n')
        if not lines:
            raise ParseError('expected a timed-block consisting a timestamp followed by data lines')
        try:
            return (int(lines[0]), lines[1:])
        except ValueError:
            raise ParseError("expected a timed-block, but timestamp '%s' is not an integer" % lines[0])
    blocks = file.read().decode('utf-8').split('\n\n')
    return [parse(block) for block in blocks if block.strip() and not block.endswith(' not running\n')]

def _parse_proc_ps_log(writer, file):
    """
     * See proc(5) for details.
     *
     * {pid, comm, state, ppid, pgrp, session, tty_nr, tpgid, flags, minflt, cminflt, majflt, cmajflt, utime, stime,
     *  cutime, cstime, priority, nice, 0, itrealvalue, starttime, vsize, rss, rlim, startcode, endcode, startstack,
     *  kstkesp, kstkeip}
    """
    processMap = {}
    ltime = 0
    timed_blocks = _parse_timed_blocks(file)
    for time, lines in timed_blocks:
        for line in lines:
            if not line: continue
            tokens = line.split(' ')
            if len(tokens) < 21:
                continue

            offset = [index for index, token in enumerate(tokens[1:]) if token[-1] == ')'][0]
            pid, cmd, state, ppid = int(tokens[0]), ' '.join(tokens[1:2+offset]), tokens[2+offset], int(tokens[3+offset])
            userCpu, sysCpu, stime = int(tokens[13+offset]), int(tokens[14+offset]), int(tokens[21+offset])

            # magic fixed point-ness ...
            pid *= 1000
            ppid *= 1000
            if pid in processMap:
                process = processMap[pid]
                process.cmd = cmd.strip('()') # why rename after latest name??
            else:
                process = Process(writer, pid, cmd.strip('()'), ppid, min(time, stime))
                processMap[pid] = process

            if process.last_user_cpu_time is not None and process.last_sys_cpu_time is not None and ltime is not None:
                userCpuLoad, sysCpuLoad = process.calc_load(userCpu, sysCpu, max(1, time - ltime))
                cpuSample = CPUSample('null', userCpuLoad, sysCpuLoad, 0.0)
                process.samples.append(ProcessSample(time, state, cpuSample))

            process.last_user_cpu_time = userCpu
            process.last_sys_cpu_time = sysCpu
        ltime = time

    if len (timed_blocks) < 2:
        return None

    startTime = timed_blocks[0][0]
    avgSampleLength = (ltime - startTime)/(len (timed_blocks) - 1)

    return ProcessStats (writer, processMap, len (timed_blocks), avgSampleLength, startTime, ltime)

def _parse_taskstats_log(writer, file):
    """
     * See bootchart-collector.c for details.
     *
     * { pid, ppid, comm, cpu_run_real_total, blkio_delay_total, swapin_delay_total }
     *
    """
    processMap = {}
    pidRewrites = {}
    ltime = None
    timed_blocks = _parse_timed_blocks(file)
    for time, lines in timed_blocks:
        # we have no 'stime' from taskstats, so prep 'init'
        if ltime is None:
            process = Process(writer, 1, '[init]', 0, 0)
            processMap[1000] = process
            ltime = time
#                       continue
        for line in lines:
            if not line: continue
            tokens = line.split(' ')
            if len(tokens) != 6:
                continue

            opid, ppid, cmd = int(tokens[0]), int(tokens[1]), tokens[2]
            cpu_ns, blkio_delay_ns, swapin_delay_ns = long(tokens[-3]), long(tokens[-2]), long(tokens[-1]),

            # make space for trees of pids
            opid *= 1000
            ppid *= 1000

            # when the process name changes, we re-write the pid.
            if opid in pidRewrites:
                pid = pidRewrites[opid]
            else:
                pid = opid

            cmd = cmd.strip('(').strip(')')
            if pid in processMap:
                process = processMap[pid]
                if process.cmd != cmd:
                    pid += 1
                    pidRewrites[opid] = pid
#                                       print "process mutation ! '%s' vs '%s' pid %s -> pid %s\n" % (process.cmd, cmd, opid, pid)
                    process = process.split (writer, pid, cmd, ppid, time)
                    processMap[pid] = process
                else:
                    process.cmd = cmd;
            else:
                process = Process(writer, pid, cmd, ppid, time)
                processMap[pid] = process

            delta_cpu_ns = (float) (cpu_ns - process.last_cpu_ns)
            delta_blkio_delay_ns = (float) (blkio_delay_ns - process.last_blkio_delay_ns)
            delta_swapin_delay_ns = (float) (swapin_delay_ns - process.last_swapin_delay_ns)

            # make up some state data ...
            if delta_cpu_ns > 0:
                state = "R"
            elif delta_blkio_delay_ns + delta_swapin_delay_ns > 0:
                state = "D"
            else:
                state = "S"

            # retain the ns timing information into a CPUSample - that tries
            # with the old-style to be a %age of CPU used in this time-slice.
            if delta_cpu_ns + delta_blkio_delay_ns + delta_swapin_delay_ns > 0:
#                               print "proc %s cpu_ns %g delta_cpu %g" % (cmd, cpu_ns, delta_cpu_ns)
                cpuSample = CPUSample('null', delta_cpu_ns, 0.0,
                                      delta_blkio_delay_ns,
                                      delta_swapin_delay_ns)
                process.samples.append(ProcessSample(time, state, cpuSample))

            process.last_cpu_ns = cpu_ns
            process.last_blkio_delay_ns = blkio_delay_ns
            process.last_swapin_delay_ns = swapin_delay_ns
        ltime = time

    if len (timed_blocks) < 2:
        return None

    startTime = timed_blocks[0][0]
    avgSampleLength = (ltime - startTime)/(len(timed_blocks)-1)

    return ProcessStats (writer, processMap, len (timed_blocks), avgSampleLength, startTime, ltime)

def _parse_proc_stat_log(file):
    samples = []
    ltimes = None
    for time, lines in _parse_timed_blocks(file):
        # skip emtpy lines
        if not lines:
            continue
        tokens = lines[0].split()
        if len(tokens) < 8:
            continue
        # CPU times {user, nice, system, idle, io_wait, irq, softirq}
        times = [ int(token) for token in tokens[1:] ]
        if ltimes:
            user = float((times[0] + times[1]) - (ltimes[0] + ltimes[1]))
            system = float((times[2] + times[5] + times[6]) - (ltimes[2] + ltimes[5] + ltimes[6]))
            idle = float(times[3] - ltimes[3])
            iowait = float(times[4] - ltimes[4])

            aSum = max(user + system + idle + iowait, 1)
            samples.append( CPUSample(time, user/aSum, system/aSum, iowait/aSum) )

        ltimes = times
        # skip the rest of statistics lines
    return samples

def _parse_proc_disk_stat_log(file, numCpu):
    """
    Parse file for disk stats, but only look at the whole device, eg. sda,
    not sda1, sda2 etc. The format of relevant lines should be:
    {major minor name rio rmerge rsect ruse wio wmerge wsect wuse running use aveq}
    """
    disk_regex_re = re.compile ('^([hsv]d.|mtdblock\d|mmcblk\d|cciss/c\d+d\d+.*)$')

    # this gets called an awful lot.
    def is_relevant_line(linetokens):
        if len(linetokens) != 14:
            return False
        disk = linetokens[2]
        return disk_regex_re.match(disk)

    disk_stat_samples = []

    for time, lines in _parse_timed_blocks(file):
        sample = DiskStatSample(time)
        relevant_tokens = [linetokens for linetokens in map (lambda x: x.split(),lines) if is_relevant_line(linetokens)]

        for tokens in relevant_tokens:
            disk, rsect, wsect, use = tokens[2], int(tokens[5]), int(tokens[9]), int(tokens[12])
            sample.add_diskdata([rsect, wsect, use])

        disk_stat_samples.append(sample)

    disk_stats = []
    for sample1, sample2 in zip(disk_stat_samples[:-1], disk_stat_samples[1:]):
        interval = sample1.time - sample2.time
        if interval == 0:
            interval = 1
        sums = [ a - b for a, b in zip(sample1.diskdata, sample2.diskdata) ]
        readTput = sums[0] / 2.0 * 100.0 / interval
        writeTput = sums[1] / 2.0 * 100.0 / interval
        util = float( sums[2] ) / 10 / interval / numCpu
        util = max(0.0, min(1.0, util))
        disk_stats.append(DiskSample(sample2.time, readTput, writeTput, util))

    return disk_stats

def _parse_proc_meminfo_log(file):
    """
    Parse file for global memory statistics.
    The format of relevant lines should be: ^key: value( unit)?
    """
    mem_stats = []
    meminfo_re = re.compile(r'(MemTotal|MemFree|Buffers|Cached|SwapTotal|SwapFree):\s*(\d+).*')

    for time, lines in _parse_timed_blocks(file):
        sample = MemSample(time)

        for line in lines:
            match = meminfo_re.match(line)
            if match:
                sample.add_value(match.group(1), int(match.group(2)))

        if sample.valid():
            mem_stats.append(sample)

    return mem_stats

# if we boot the kernel with: initcall_debug printk.time=1 we can
# get all manner of interesting data from the dmesg output
# We turn this into a pseudo-process tree: each event is
# characterised by a
# we don't try to detect a "kernel finished" state - since the kernel
# continues to do interesting things after init is called.
#
# sample input:
# [    0.000000] ACPI: FACP 3f4fc000 000F4 (v04 INTEL  Napa     00000001 MSFT 01000013)
# ...
# [    0.039993] calling  migration_init+0x0/0x6b @ 1
# [    0.039993] initcall migration_init+0x0/0x6b returned 1 after 0 usecs
def _parse_dmesg(writer, file):
    timestamp_re = re.compile ("^\[\s*(\d+\.\d+)\s*]\s+(.*)$")
    split_re = re.compile ("^(\S+)\s+([\S\+_-]+) (.*)$")
    processMap = {}
    idx = 0
    inc = 1.0 / 1000000
    kernel = Process(writer, idx, "k-boot", 0, 0.1)
    processMap['k-boot'] = kernel
    base_ts = False
    max_ts = 0
    for line in file.read().decode('utf-8').split('\n'):
        t = timestamp_re.match (line)
        if t is None:
#                       print "duff timestamp " + line
            continue

        time_ms = float (t.group(1)) * 1000
        # looks like we may have a huge diff after the clock
        # has been set up. This could lead to huge graph:
        # so huge we will be killed by the OOM.
        # So instead of using the plain timestamp we will
        # use a delta to first one and skip the first one
        # for convenience
        if max_ts == 0 and not base_ts and time_ms > 1000:
            base_ts = time_ms
            continue
        max_ts = max(time_ms, max_ts)
        if base_ts:
#                       print "fscked clock: used %f instead of %f" % (time_ms - base_ts, time_ms)
            time_ms -= base_ts
        m = split_re.match (t.group(2))

        if m is None:
            continue
#               print "match: '%s'" % (m.group(1))
        type = m.group(1)
        func = m.group(2)
        rest = m.group(3)

        if t.group(2).startswith ('Write protecting the') or \
           t.group(2).startswith ('Freeing unused kernel memory'):
            kernel.duration = time_ms / 10
            continue

#               print "foo: '%s' '%s' '%s'" % (type, func, rest)
        if type == "calling":
            ppid = kernel.pid
            p = re.match ("\@ (\d+)", rest)
            if p is not None:
                ppid = float (p.group(1)) // 1000
#                               print "match: '%s' ('%g') at '%s'" % (func, ppid, time_ms)
            name = func.split ('+', 1) [0]
            idx += inc
            processMap[func] = Process(writer, ppid + idx, name, ppid, time_ms / 10)
        elif type == "initcall":
#                       print "finished: '%s' at '%s'" % (func, time_ms)
            if func in processMap:
                process = processMap[func]
                process.duration = (time_ms / 10) - process.start_time
            else:
                print("corrupted init call for %s" % (func))

        elif type == "async_waiting" or type == "async_continuing":
            continue # ignore

    return processMap.values()

#
# Parse binary pacct accounting file output if we have one
# cf. /usr/include/linux/acct.h
#
def _parse_pacct(writer, file):
    # read LE int32
    def _read_le_int32(file):
        byts = file.read(4)
        return (ord(byts[0]))       | (ord(byts[1]) << 8) | \
               (ord(byts[2]) << 16) | (ord(byts[3]) << 24)

    parent_map = {}
    parent_map[0] = 0
    while file.read(1) != "": # ignore flags
        ver = file.read(1)
        if ord(ver) < 3:
            print("Invalid version 0x%x" % (ord(ver)))
            return None

        file.seek (14, 1)     # user, group etc.
        pid = _read_le_int32 (file)
        ppid = _read_le_int32 (file)
#               print "Parent of %d is %d" % (pid, ppid)
        parent_map[pid] = ppid
        file.seek (4 + 4 + 16, 1) # timings
        file.seek (16, 1)         # acct_comm
    return parent_map

def _parse_paternity_log(writer, file):
    parent_map = {}
    parent_map[0] = 0
    for line in file.read().decode('utf-8').split('\n'):
        if not line:
            continue
        elems = line.split(' ') # <Child> <Parent>
        if len (elems) >= 2:
#                       print "paternity of %d is %d" % (int(elems[0]), int(elems[1]))
            parent_map[int(elems[0])] = int(elems[1])
        else:
            print("Odd paternity line '%s'" % (line))
    return parent_map

def _parse_cmdline_log(writer, file):
    cmdLines = {}
    for block in file.read().decode('utf-8').split('\n\n'):
        lines = block.split('\n')
        if len (lines) >= 3:
#                       print "Lines '%s'" % (lines[0])
            pid = int (lines[0])
            values = {}
            values['exe'] = lines[1].lstrip(':')
            args = lines[2].lstrip(':').split('\0')
            args.pop()
            values['args'] = args
            cmdLines[pid] = values
    return cmdLines

def get_num_cpus(headers):
    """Get the number of CPUs from the system.cpu header property. As the
    CPU utilization graphs are relative, the number of CPUs currently makes
    no difference."""
    if headers is None:
        return 1
    if headers.get("system.cpu.num"):
        return max (int (headers.get("system.cpu.num")), 1)
    cpu_model = headers.get("system.cpu")
    if cpu_model is None:
        return 1
    mat = re.match(".*\\((\\d+)\\)", cpu_model)
    if mat is None:
        return 1
    return max (int(mat.group(1)), 1)

def _do_parse(writer, state, name, file):
    writer.status("parsing '%s'" % name)
    t1 = clock()
    if name == "header":
        state.headers = _parse_headers(file)
    elif name == "proc_diskstats.log":
        state.disk_stats = _parse_proc_disk_stat_log(file, get_num_cpus(state.headers))
    elif name == "taskstats.log":
        state.ps_stats = _parse_taskstats_log(writer, file)
        state.taskstats = True
    elif name == "proc_stat.log":
        state.cpu_stats = _parse_proc_stat_log(file)
    elif name == "proc_meminfo.log":
        state.mem_stats = _parse_proc_meminfo_log(file)
    elif name == "dmesg":
        state.kernel = _parse_dmesg(writer, file)
    elif name == "cmdline2.log":
        state.cmdline = _parse_cmdline_log(writer, file)
    elif name == "paternity.log":
        state.parent_map = _parse_paternity_log(writer, file)
    elif name == "proc_ps.log":  # obsoleted by TASKSTATS
        state.ps_stats = _parse_proc_ps_log(writer, file)
    elif name == "kernel_pacct": # obsoleted by PROC_EVENTS
        state.parent_map = _parse_pacct(writer, file)
    t2 = clock()
    writer.info("  %s seconds" % str(t2-t1))
    return state

def parse_file(writer, state, filename):
    if state.filename is None:
        state.filename = filename
    basename = os.path.basename(filename)
    with open(filename, "rb") as file:
        return _do_parse(writer, state, basename, file)

def parse_paths(writer, state, paths):
    for path in paths:
        root, extension = os.path.splitext(path)
        if not(os.path.exists(path)):
            writer.warn("warning: path '%s' does not exist, ignoring." % path)
            continue
        state.filename = path
        if os.path.isdir(path):
            files = [ f for f in [os.path.join(path, f) for f in os.listdir(path)] if os.path.isfile(f) ]
            files.sort()
            state = parse_paths(writer, state, files)
        elif extension in [".tar", ".tgz", ".gz"]:
            if extension == ".gz":
                root, extension = os.path.splitext(root)
                if extension != ".tar":
                    writer.warn("warning: can only handle zipped tar files, not zipped '%s'-files; ignoring" % extension)
                    continue
            tf = None
            try:
                writer.status("parsing '%s'" % path)
                tf = tarfile.open(path, 'r:*')
                for name in tf.getnames():
                    state = _do_parse(writer, state, name, tf.extractfile(name))
            except tarfile.ReadError as error:
                raise ParseError("error: could not read tarfile '%s': %s." % (path, error))
            finally:
                if tf != None:
                    tf.close()
        else:
            state = parse_file(writer, state, path)
    return state

########NEW FILE########
__FILENAME__ = process_tree
#  This file is part of pybootchartgui.

#  pybootchartgui is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.

#  pybootchartgui is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.

#  You should have received a copy of the GNU General Public License
#  along with pybootchartgui. If not, see <http://www.gnu.org/licenses/>.

class ProcessTree:
    """ProcessTree encapsulates a process tree.  The tree is built from log files
       retrieved during the boot process.  When building the process tree, it is
       pruned and merged in order to be able to visualize it in a comprehensible
       manner.

       The following pruning techniques are used:

        * idle processes that keep running during the last process sample
          (which is a heuristic for a background processes) are removed,
        * short-lived processes (i.e. processes that only live for the
          duration of two samples or less) are removed,
        * the processes used by the boot logger are removed,
        * exploders (i.e. processes that are known to spawn huge meaningless
          process subtrees) have their subtrees merged together,
        * siblings (i.e. processes with the same command line living
          concurrently -- thread heuristic) are merged together,
        * process runs (unary trees with processes sharing the command line)
          are merged together.

    """
    LOGGER_PROC = 'bootchart-colle'
    EXPLODER_PROCESSES = set(['hwup'])

    def __init__(self, writer, kernel, psstats, sample_period,
                 monitoredApp, prune, idle, taskstats,
                 accurate_parentage, for_testing = False):
        self.writer = writer
        self.process_tree = []
        self.taskstats = taskstats
        if psstats is None:
            process_list = kernel
        elif kernel is None:
            process_list = psstats.process_map.values()
        else:
            process_list = list(kernel) + list(psstats.process_map.values())
        self.process_list = sorted(process_list, key = lambda p: p.pid)
        self.sample_period = sample_period

        self.build()
        if not accurate_parentage:
            self.update_ppids_for_daemons(self.process_list)

        self.start_time = self.get_start_time(self.process_tree)
        self.end_time = self.get_end_time(self.process_tree)
        self.duration = self.end_time - self.start_time
        self.idle = idle

        if for_testing:
            return

        removed = self.merge_logger(self.process_tree, self.LOGGER_PROC, monitoredApp, False)
        writer.status("merged %i logger processes" % removed)

        if prune:
            p_processes = self.prune(self.process_tree, None)
            p_exploders = self.merge_exploders(self.process_tree, self.EXPLODER_PROCESSES)
            p_threads = self.merge_siblings(self.process_tree)
            p_runs = self.merge_runs(self.process_tree)
            writer.status("pruned %i process, %i exploders, %i threads, and %i runs" % (p_processes, p_exploders, p_threads, p_runs))

        self.sort(self.process_tree)

        self.start_time = self.get_start_time(self.process_tree)
        self.end_time = self.get_end_time(self.process_tree)
        self.duration = self.end_time - self.start_time

        self.num_proc = self.num_nodes(self.process_tree)

    def build(self):
        """Build the process tree from the list of top samples."""
        self.process_tree = []
        for proc in self.process_list:
            if not proc.parent:
                self.process_tree.append(proc)
            else:
                proc.parent.child_list.append(proc)

    def sort(self, process_subtree):
        """Sort process tree."""
        for p in process_subtree:
            p.child_list.sort(key = lambda p: p.pid)
            self.sort(p.child_list)

    def num_nodes(self, process_list):
        "Counts the number of nodes in the specified process tree."""
        nodes = 0
        for proc in process_list:
            nodes = nodes + self.num_nodes(proc.child_list)
        return nodes + len(process_list)

    def get_start_time(self, process_subtree):
        """Returns the start time of the process subtree.  This is the start
           time of the earliest process.

        """
        if not process_subtree:
            return 100000000
        return min( [min(proc.start_time, self.get_start_time(proc.child_list)) for proc in process_subtree] )

    def get_end_time(self, process_subtree):
        """Returns the end time of the process subtree.  This is the end time
           of the last collected sample.

        """
        if not process_subtree:
            return -100000000
        return max( [max(proc.start_time + proc.duration, self.get_end_time(proc.child_list)) for proc in process_subtree] )

    def get_max_pid(self, process_subtree):
        """Returns the max PID found in the process tree."""
        if not process_subtree:
            return -100000000
        return max( [max(proc.pid, self.get_max_pid(proc.child_list)) for proc in process_subtree] )

    def update_ppids_for_daemons(self, process_list):
        """Fedora hack: when loading the system services from rc, runuser(1)
           is used.  This sets the PPID of all daemons to 1, skewing
           the process tree.  Try to detect this and set the PPID of
           these processes the PID of rc.

        """
        rcstartpid = -1
        rcendpid = -1
        rcproc = None
        for p in process_list:
            if p.cmd == "rc" and p.ppid // 1000 == 1:
                rcproc = p
                rcstartpid = p.pid
                rcendpid = self.get_max_pid(p.child_list)
        if rcstartpid != -1 and rcendpid != -1:
            for p in process_list:
                if p.pid > rcstartpid and p.pid < rcendpid and p.ppid // 1000 == 1:
                    p.ppid = rcstartpid
                    p.parent = rcproc
            for p in process_list:
                p.child_list = []
            self.build()

    def prune(self, process_subtree, parent):
        """Prunes the process tree by removing idle processes and processes
           that only live for the duration of a single top sample.  Sibling
           processes with the same command line (i.e. threads) are merged
           together. This filters out sleepy background processes, short-lived
           processes and bootcharts' analysis tools.
        """
        def is_idle_background_process_without_children(p):
            process_end = p.start_time + p.duration
            return not p.active and \
                   process_end >= self.start_time + self.duration and \
                   p.start_time > self.start_time and \
                   p.duration > 0.9 * self.duration and \
                   self.num_nodes(p.child_list) == 0

        num_removed = 0
        idx = 0
        while idx < len(process_subtree):
            p = process_subtree[idx]
            if parent != None or len(p.child_list) == 0:

                prune = False
                if is_idle_background_process_without_children(p):
                    prune = True
                elif p.duration <= 2 * self.sample_period:
                    # short-lived process
                    prune = True

                if prune:
                    process_subtree.pop(idx)
                    for c in p.child_list:
                        process_subtree.insert(idx, c)
                    num_removed += 1
                    continue
                else:
                    num_removed += self.prune(p.child_list, p)
            else:
                num_removed += self.prune(p.child_list, p)
            idx += 1

        return num_removed

    def merge_logger(self, process_subtree, logger_proc, monitored_app, app_tree):
        """Merges the logger's process subtree.  The logger will typically
           spawn lots of sleep and cat processes, thus polluting the
           process tree.

        """
        num_removed = 0
        for p in process_subtree:
            is_app_tree = app_tree
            if logger_proc == p.cmd and not app_tree:
                is_app_tree = True
                num_removed += self.merge_logger(p.child_list, logger_proc, monitored_app, is_app_tree)
                # don't remove the logger itself
                continue

            if app_tree and monitored_app != None and monitored_app == p.cmd:
                is_app_tree = False

            if is_app_tree:
                for child in p.child_list:
                    self.merge_processes(p, child)
                    num_removed += 1
                p.child_list = []
            else:
                num_removed += self.merge_logger(p.child_list, logger_proc, monitored_app, is_app_tree)
        return num_removed

    def merge_exploders(self, process_subtree, processes):
        """Merges specific process subtrees (used for processes which usually
           spawn huge meaningless process trees).

        """
        num_removed = 0
        for p in process_subtree:
            if processes in processes and len(p.child_list) > 0:
                subtreemap = self.getProcessMap(p.child_list)
                for child in subtreemap.values():
                    self.merge_processes(p, child)
                    num_removed += len(subtreemap)
                    p.child_list = []
                    p.cmd += " (+)"
            else:
                num_removed += self.merge_exploders(p.child_list, processes)
        return num_removed

    def merge_siblings(self, process_subtree):
        """Merges thread processes.  Sibling processes with the same command
           line are merged together.

        """
        num_removed = 0
        idx = 0
        while idx < len(process_subtree)-1:
            p = process_subtree[idx]
            nextp = process_subtree[idx+1]
            if nextp.cmd == p.cmd:
                process_subtree.pop(idx+1)
                idx -= 1
                num_removed += 1
                p.child_list.extend(nextp.child_list)
                self.merge_processes(p, nextp)
            num_removed += self.merge_siblings(p.child_list)
            idx += 1
        if len(process_subtree) > 0:
            p = process_subtree[-1]
            num_removed += self.merge_siblings(p.child_list)
        return num_removed

    def merge_runs(self, process_subtree):
        """Merges process runs.  Single child processes which share the same
           command line with the parent are merged.

        """
        num_removed = 0
        idx = 0
        while idx < len(process_subtree):
            p = process_subtree[idx]
            if len(p.child_list) == 1 and p.child_list[0].cmd == p.cmd:
                child = p.child_list[0]
                p.child_list = list(child.child_list)
                self.merge_processes(p, child)
                num_removed += 1
                continue
            num_removed += self.merge_runs(p.child_list)
            idx += 1
        return num_removed

    def merge_processes(self, p1, p2):
        """Merges two process' samples."""
        p1.samples.extend(p2.samples)
        p1.samples.sort( key = lambda p: p.time )
        p1time = p1.start_time
        p2time = p2.start_time
        p1.start_time = min(p1time, p2time)
        pendtime = max(p1time + p1.duration, p2time + p2.duration)
        p1.duration = pendtime - p1.start_time

########NEW FILE########
__FILENAME__ = samples
#  This file is part of pybootchartgui.

#  pybootchartgui is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.

#  pybootchartgui is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.

#  You should have received a copy of the GNU General Public License
#  along with pybootchartgui. If not, see <http://www.gnu.org/licenses/>.


class DiskStatSample:
    def __init__(self, time):
        self.time = time
        self.diskdata = [0, 0, 0]
    def add_diskdata(self, new_diskdata):
        self.diskdata = [ a + b for a, b in zip(self.diskdata, new_diskdata) ]

class CPUSample:
    def __init__(self, time, user, sys, io = 0.0, swap = 0.0):
        self.time = time
        self.user = user
        self.sys = sys
        self.io = io
        self.swap = swap

    @property
    def cpu(self):
        return self.user + self.sys

    def __str__(self):
        return str(self.time) + "\t" + str(self.user) + "\t" + \
               str(self.sys) + "\t" + str(self.io) + "\t" + str (self.swap)

class MemSample:
    used_values = ('MemTotal', 'MemFree', 'Buffers', 'Cached', 'SwapTotal', 'SwapFree',)

    def __init__(self, time):
        self.time = time
        self.records = {}

    def add_value(self, name, value):
        self.records[name] = value

    def valid(self):
        keys = self.records.keys()
        # discard incomplete samples
        return [v for v in MemSample.used_values if v not in keys] == []

class ProcessSample:
    def __init__(self, time, state, cpu_sample):
        self.time = time
        self.state = state
        self.cpu_sample = cpu_sample

    def __str__(self):
        return str(self.time) + "\t" + str(self.state) + "\t" + str(self.cpu_sample)

class ProcessStats:
    def __init__(self, writer, process_map, sample_count, sample_period, start_time, end_time):
        self.process_map = process_map
        self.sample_count = sample_count
        self.sample_period = sample_period
        self.start_time = start_time
        self.end_time = end_time
        writer.info ("%d samples, avg. sample length %f" % (self.sample_count, self.sample_period))
        writer.info ("process list size: %d" % len (self.process_map.values()))

class Process:
    def __init__(self, writer, pid, cmd, ppid, start_time):
        self.writer = writer
        self.pid = pid
        self.cmd = cmd
        self.exe = cmd
        self.args = []
        self.ppid = ppid
        self.start_time = start_time
        self.duration = 0
        self.samples = []
        self.parent = None
        self.child_list = []

        self.active = None
        self.last_user_cpu_time = None
        self.last_sys_cpu_time = None

        self.last_cpu_ns = 0
        self.last_blkio_delay_ns = 0
        self.last_swapin_delay_ns = 0

    # split this process' run - triggered by a name change
    def split(self, writer, pid, cmd, ppid, start_time):
        split = Process (writer, pid, cmd, ppid, start_time)

        split.last_cpu_ns = self.last_cpu_ns
        split.last_blkio_delay_ns = self.last_blkio_delay_ns
        split.last_swapin_delay_ns = self.last_swapin_delay_ns

        return split

    def __str__(self):
        return " ".join([str(self.pid), self.cmd, str(self.ppid), '[ ' + str(len(self.samples)) + ' samples ]' ])

    def calc_stats(self, samplePeriod):
        if self.samples:
            firstSample = self.samples[0]
            lastSample = self.samples[-1]
            self.start_time = min(firstSample.time, self.start_time)
            self.duration = lastSample.time - self.start_time + samplePeriod

        activeCount = sum( [1 for sample in self.samples if sample.cpu_sample and sample.cpu_sample.sys + sample.cpu_sample.user + sample.cpu_sample.io > 0.0] )
        activeCount = activeCount + sum( [1 for sample in self.samples if sample.state == 'D'] )
        self.active = (activeCount>2)

    def calc_load(self, userCpu, sysCpu, interval):
        userCpuLoad = float(userCpu - self.last_user_cpu_time) / interval
        sysCpuLoad = float(sysCpu - self.last_sys_cpu_time) / interval
        cpuLoad = userCpuLoad + sysCpuLoad
        # normalize
        if cpuLoad > 1.0:
            userCpuLoad = userCpuLoad / cpuLoad
            sysCpuLoad = sysCpuLoad / cpuLoad
        return (userCpuLoad, sysCpuLoad)

    def set_parent(self, processMap):
        if self.ppid != None:
            self.parent = processMap.get (self.ppid)
            if self.parent == None and self.pid // 1000 > 1 and \
                not (self.ppid == 2000 or self.pid == 2000): # kernel threads: ppid=2
                self.writer.warn("Missing CONFIG_PROC_EVENTS: no parent for pid '%i' ('%s') with ppid '%i'" \
                                 % (self.pid,self.cmd,self.ppid))

    def get_end_time(self):
        return self.start_time + self.duration

class DiskSample:
    def __init__(self, time, read, write, util):
        self.time = time
        self.read = read
        self.write = write
        self.util = util
        self.tput = read + write

    def __str__(self):
        return "\t".join([str(self.time), str(self.read), str(self.write), str(self.util)])

########NEW FILE########
__FILENAME__ = parser_test
import sys, os, re, struct, operator, math
from collections import defaultdict
import unittest

sys.path.insert(0, os.getcwd())

import pybootchartgui.parsing as parsing
import pybootchartgui.main as main

debug = False

def floatEq(f1, f2):
	return math.fabs(f1-f2) < 0.00001

bootchart_dir = os.path.join(os.path.dirname(sys.argv[0]), '../../examples/1/')
parser = main._mk_options_parser()
options, args = parser.parse_args(['--q', bootchart_dir])
writer = main._mk_writer(options)

class TestBCParser(unittest.TestCase):
    
	def setUp(self):
		self.name = "My first unittest"
		self.rootdir = bootchart_dir

	def mk_fname(self,f):
		return os.path.join(self.rootdir, f)

	def testParseHeader(self):
		trace = parsing.Trace(writer, args, options)
		state = parsing.parse_file(writer, trace, self.mk_fname('header'))
		self.assertEqual(6, len(state.headers))
		self.assertEqual(2, parsing.get_num_cpus(state.headers))

	def test_parseTimedBlocks(self):
		trace = parsing.Trace(writer, args, options)
		state = parsing.parse_file(writer, trace, self.mk_fname('proc_diskstats.log'))
		self.assertEqual(141, len(state.disk_stats))		

	def testParseProcPsLog(self):
		trace = parsing.Trace(writer, args, options)
		state = parsing.parse_file(writer, trace, self.mk_fname('proc_ps.log'))
		samples = state.ps_stats
		processes = samples.process_map
		sorted_processes = [processes[k] for k in sorted(processes.keys())]

		ps_data = open(self.mk_fname('extract2.proc_ps.log'))
		for index, line in enumerate(ps_data):
			tokens = line.split();
			process = sorted_processes[index]
			if debug:
				print(tokens[0:4])
				print(process.pid / 1000, process.cmd, process.ppid, len(process.samples))
				print('-------------------')

			self.assertEqual(tokens[0], str(process.pid // 1000))
			self.assertEqual(tokens[1], str(process.cmd))
			self.assertEqual(tokens[2], str(process.ppid // 1000))
			self.assertEqual(tokens[3], str(len(process.samples)))
		ps_data.close()

	def testparseProcDiskStatLog(self):
		trace = parsing.Trace(writer, args, options)
		state_with_headers = parsing.parse_file(writer, trace, self.mk_fname('header'))
		state_with_headers.headers['system.cpu'] = 'xxx (2)'
		samples = parsing.parse_file(writer, state_with_headers, self.mk_fname('proc_diskstats.log')).disk_stats
		self.assertEqual(141, len(samples))

		diskstats_data = open(self.mk_fname('extract.proc_diskstats.log'))
		for index, line in enumerate(diskstats_data):
			tokens = line.split('\t')
			sample = samples[index]
			if debug:		
				print(line.rstrip())
				print(sample)
				print('-------------------')
			
			self.assertEqual(tokens[0], str(sample.time))
			self.assert_(floatEq(float(tokens[1]), sample.read))
			self.assert_(floatEq(float(tokens[2]), sample.write))
			self.assert_(floatEq(float(tokens[3]), sample.util))
		diskstats_data.close()
	
	def testparseProcStatLog(self):
		trace = parsing.Trace(writer, args, options)
		samples = parsing.parse_file(writer, trace, self.mk_fname('proc_stat.log')).cpu_stats
		self.assertEqual(141, len(samples))

		stat_data = open(self.mk_fname('extract.proc_stat.log'))
		for index, line in enumerate(stat_data):
			tokens = line.split('\t')
			sample = samples[index]
			if debug:
				print(line.rstrip())
				print(sample)
				print('-------------------')
			self.assert_(floatEq(float(tokens[0]), sample.time))
			self.assert_(floatEq(float(tokens[1]), sample.user))
			self.assert_(floatEq(float(tokens[2]), sample.sys))
			self.assert_(floatEq(float(tokens[3]), sample.io))
		stat_data.close()

if __name__ == '__main__':
    unittest.main()


########NEW FILE########
__FILENAME__ = process_tree_test
import sys
import os
import unittest

sys.path.insert(0, os.getcwd())

import pybootchartgui.parsing as parsing
import pybootchartgui.process_tree as process_tree
import pybootchartgui.main as main

if sys.version_info >= (3, 0):
    long = int

class TestProcessTree(unittest.TestCase):

    def setUp(self):
        self.name = "Process tree unittest"
        self.rootdir = os.path.join(os.path.dirname(sys.argv[0]), '../../examples/1/')

        parser = main._mk_options_parser()
        options, args = parser.parse_args(['--q', self.rootdir])
        writer = main._mk_writer(options)
        trace = parsing.Trace(writer, args, options)

        parsing.parse_file(writer, trace, self.mk_fname('proc_ps.log'))
        trace.compile(writer)
        self.processtree = process_tree.ProcessTree(writer, None, trace.ps_stats, \
            trace.ps_stats.sample_period, None, options.prune, None, None, False, for_testing = True)

    def mk_fname(self,f):
        return os.path.join(self.rootdir, f)

    def flatten(self, process_tree):
        flattened = []
        for p in process_tree:
            flattened.append(p)
            flattened.extend(self.flatten(p.child_list))
        return flattened

    def checkAgainstJavaExtract(self, filename, process_tree):
        test_data = open(filename)
        for expected, actual in zip(test_data, self.flatten(process_tree)):
            tokens = expected.split('\t')
            self.assertEqual(int(tokens[0]), actual.pid // 1000)
            self.assertEqual(tokens[1], actual.cmd)
            self.assertEqual(long(tokens[2]), 10 * actual.start_time)
            self.assert_(long(tokens[3]) - 10 * actual.duration < 5, "duration")
            self.assertEqual(int(tokens[4]), len(actual.child_list))
            self.assertEqual(int(tokens[5]), len(actual.samples))
        test_data.close()

    def testBuild(self):
        process_tree = self.processtree.process_tree
        self.checkAgainstJavaExtract(self.mk_fname('extract.processtree.1.log'), process_tree)

    def testMergeLogger(self):
        self.processtree.merge_logger(self.processtree.process_tree, 'bootchartd', None, False)
        process_tree = self.processtree.process_tree
        self.checkAgainstJavaExtract(self.mk_fname('extract.processtree.2.log'), process_tree)

    def testPrune(self):
        self.processtree.merge_logger(self.processtree.process_tree, 'bootchartd', None, False)
        self.processtree.prune(self.processtree.process_tree, None)
        process_tree = self.processtree.process_tree
        self.checkAgainstJavaExtract(self.mk_fname('extract.processtree.3b.log'), process_tree)

    def testMergeExploders(self):
        self.processtree.merge_logger(self.processtree.process_tree, 'bootchartd', None, False)
        self.processtree.prune(self.processtree.process_tree, None)
        self.processtree.merge_exploders(self.processtree.process_tree, set(['hwup']))
        process_tree = self.processtree.process_tree
        self.checkAgainstJavaExtract(self.mk_fname('extract.processtree.3c.log'), process_tree)

    def testMergeSiblings(self):
        self.processtree.merge_logger(self.processtree.process_tree, 'bootchartd', None, False)
        self.processtree.prune(self.processtree.process_tree, None)
        self.processtree.merge_exploders(self.processtree.process_tree, set(['hwup']))
        self.processtree.merge_siblings(self.processtree.process_tree)
        process_tree = self.processtree.process_tree
        self.checkAgainstJavaExtract(self.mk_fname('extract.processtree.3d.log'), process_tree)

    def testMergeRuns(self):
        self.processtree.merge_logger(self.processtree.process_tree, 'bootchartd', None, False)
        self.processtree.prune(self.processtree.process_tree, None)
        self.processtree.merge_exploders(self.processtree.process_tree, set(['hwup']))
        self.processtree.merge_siblings(self.processtree.process_tree)
        self.processtree.merge_runs(self.processtree.process_tree)
        process_tree = self.processtree.process_tree
        self.checkAgainstJavaExtract(self.mk_fname('extract.processtree.3e.log'), process_tree)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = pybootchartgui
#!/usr/bin/python
#
#  This file is part of pybootchartgui.

#  pybootchartgui is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.

#  pybootchartgui is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.

#  You should have received a copy of the GNU General Public License
#  along with pybootchartgui. If not, see <http://www.gnu.org/licenses/>.


import sys
from pybootchartgui.main import main

if __name__ == '__main__':
	sys.exit(main())

########NEW FILE########
