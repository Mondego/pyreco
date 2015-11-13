__FILENAME__ = histogram
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Plotting terminal based histograms
"""

import os
import sys
import math
import optparse
from os.path import dirname
from .utils.helpers import *
from .utils.commandhelp import hist


def calc_bins(n, min_val, max_val, h=None, binwidth=None):
    """
    Calculate number of bins for the histogram
    """
    if not h:
        h = max(10, math.log(n + 1, 2))
    if binwidth == 0:
        binwidth = 0.1
    if binwidth is None:
        binwidth = (max_val - min_val) / h
    for b in drange(min_val, max_val, step=binwidth, include_stop=True):
        if b.is_integer():
            yield int(b)
        else:
            yield b


def read_numbers(numbers):
    """
    Read the input data in the most optimal way
    """
    if isinstance(numbers, list):
        for number in numbers:
            yield float(str(number).strip())
    else:
        for number in open(numbers):
            yield float(number.strip())


def run_demo():
    """
    Run a demonstration
    """
    module_dir = dirname(dirname(os.path.realpath(__file__)))
    demo_file = os.path.join(module_dir, 'examples/data/exp.txt')

    if not os.path.isfile(demo_file):
        sys.stderr.write("demo input file not found!\n")
        sys.stderr.write("run the downloaddata.sh script in the example first\n")
        sys.exit(1)

    #plotting a histogram
    print "plotting a basic histogram"
    print "plot_hist('%s')" % demo_file
    print "hist -f %s" % demo_file
    print "cat %s | hist" % demo_file
    plot_hist(demo_file)
    print "*" * 80

    #with colours
    print "histogram with colours"
    print "plot_hist('%s', colour='blue')" % demo_file
    print "hist -f %s -c blue" % demo_file
    plot_hist(demo_file, colour='blue')
    print "*" * 80

    #changing the shape of the point
    print "changing the shape of the bars"
    print "plot_hist('%s', pch='.')" % demo_file
    print "hist -f %s -p ." % demo_file
    plot_hist(demo_file, pch='.')
    print "*" * 80

    #changing the size of the plot
    print "changing the size of the plot"
    print "plot_hist('%s', height=35.0, bincount=40)" % demo_file
    print "hist -f %s -s 35.0 -b 40" % demo_file
    plot_hist(demo_file, height=35.0, bincount=40)


def plot_hist(f, height=20.0, bincount=None, binwidth=None, pch="o", colour="default", title="", xlab=None, showSummary=False, regular=False):
    """
    Make a histogram

    Arguments:
        height -- the height of the histogram in # of lines
        bincount -- number of bins in the histogram
        binwidth -- width of bins in the histogram
        pch -- shape of the bars in the plot
        colour -- colour of the bars in the terminal
        title -- title at the top of the plot
        xlab -- boolen value for whether or not to display x-axis labels
        showSummary -- boolean value for whether or not to display a summary
        regular -- boolean value for whether or not to start y-labels at 0
    """
    if pch is None:
        pch = "o"

    min_val, max_val = None, None
    n, mean = 0.0, 0.0

    for number in read_numbers(f):
        n += 1
        if min_val is None or number < min_val:
            min_val = number
        if max_val is None or number > max_val:
            max_val = number
        mean += number

    mean /= n

    bins = list(calc_bins(n, min_val, max_val, bincount, binwidth))
    hist = {i: 0 for i in range(len(bins))}

    for number in read_numbers(f):
        for i, b in enumerate(bins):
            if number <= b:
                hist[i] += 1
                break
        if number == max_val and max_val > bins[len(bins) - 1]:
            hist[len(hist) - 1] += 1

    min_y, max_y = min(hist.values()), max(hist.values())

    start = max(min_y, 1)
    stop = max_y + 1

    if regular:
        start = 1

    if height is None:
        height = stop - start
        if height > 20:
            height = 20

    ys = list(drange(start, stop, float(stop - start)/height))
    ys.reverse()

    nlen = max(len(str(min_y)), len(str(max_y))) + 1

    if title:
        print box_text(title, max(len(hist)*2, len(title)), nlen)
    print

    used_labs = set()
    for y in ys:
        ylab = str(int(y))
        if ylab in used_labs:
            ylab = ""
        else:
            used_labs.add(ylab)
        ylab = " "*(nlen - len(ylab)) + ylab + "|"

        print ylab,

        for i in range(len(hist)):
            if int(y) <= hist[i]:
                printcolour(pch, True, colour)
            else:
                printcolour(" ", True, colour)
        print
    xs = hist.keys() * 2

    print " " * (nlen+1) + "-" * len(xs)

    if xlab:
        xlen = len(str(float((max_y)/height) + max_y))
        for i in range(0, xlen):
            printcolour(" " * (nlen+1), True, colour)
            for x in range(0, len(hist)):
                num = str(bins[x])
                if x % 2 == 0:
                    print " ",
                elif i < len(num):
                    print num[i],
                else:
                    print " ",
            print

    center = max(map(len, map(str, [n, min_val, mean, max_val])))
    center += 15

    if showSummary:
        print
        print "-" * (2 + center)
        print "|" + "Summary".center(center) + "|"
        print "-" * (2 + center)
        summary = "|" + ("observations: %d" % n).center(center) + "|\n"
        summary += "|" + ("min value: %f" % min_val).center(center) + "|\n"
        summary += "|" + ("mean : %f" % mean).center(center) + "|\n"
        summary += "|" + ("max value: %f" % max_val).center(center) + "|\n"
        summary += "-" * (2 + center)
        print summary


def main():

    parser = optparse.OptionParser(usage=hist['usage'])

    parser.add_option('-f', '--file', help='a file containing a column of numbers', default=None, dest='f')
    parser.add_option('-t', '--title', help='title for the chart', default="", dest='t')
    parser.add_option('-b', '--bins', help='number of bins in the histogram', type='int', default=None, dest='b')
    parser.add_option('-w', '--binwidth', help='width of bins in the histogram', type='float', default=None, dest='binwidth')
    parser.add_option('-s', '--height', help='height of the histogram (in lines)', type='int', default=None, dest='h')
    parser.add_option('-p', '--pch', help='shape of each bar', default='o', dest='p')
    parser.add_option('-x', '--xlab', help='label bins on x-axis', default=None, action="store_true", dest='x')
    parser.add_option('-c', '--colour', help='colour of the plot (%s)' % colour_help, default='default', dest='colour')
    parser.add_option('-d', '--demo', help='run demos', action='store_true', dest='demo')
    parser.add_option('-n', '--nosummary', help='hide summary', action='store_false', dest='showSummary', default=True)
    parser.add_option('-r', '--regular',
                      help='use regular y-scale (0 - maximum y value), instead of truncated y-scale (minimum y-value - maximum y-value)',
                      default=False, action="store_true", dest='regular')

    opts, args = parser.parse_args()

    if opts.f is None:
        if len(args) > 0:
            opts.f = args[0]
        elif opts.demo is None or opts.demo is False:
            opts.f = sys.stdin.readlines()

    if opts.demo:
        run_demo()
    elif opts.f:
        plot_hist(opts.f, opts.h, opts.b, opts.binwidth, opts.p, opts.colour, opts.t, opts.x, opts.showSummary, opts.regular)
    else:
        print "nothing to plot!"


if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = scatterplot
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Plotting terminal based scatterplots
"""

import csv
import sys
import optparse
from .utils.helpers import *
from .utils.commandhelp import scatter 


def get_scale(series, is_y=False, steps=20):
    min_val = min(series)
    max_val = max(series)
    scaled_series = []
    for x in drange(min_val, max_val, (max_val-min_val)/steps):
        if x > 0 and scaled_series and max(scaled_series) < 0:
            scaled_series.append(0.0)
        scaled_series.append(x)
    
    if is_y:
        scaled_series.reverse()
    return scaled_series


def plot_scatter(f, xs, ys, size, pch, colour, title):
    """
    Form a complex number.
    
    Arguments:
        f -- comma delimited file w/ x,y coordinates
        xs -- if f not specified this is a file w/ x coordinates
        ys -- if f not specified this is a filew / y coordinates
        size -- size of the plot
        pch -- shape of the points (any character)
        colour -- colour of the points
        title -- title of the plot 
    """
    
    if f:
        if isinstance(f, str):
            f = open(f)
        
        data = [tuple(map(float, line.strip().split(','))) for line in f]
        xs = [i[0] for i in data]
        ys = [i[1] for i in data]
    else:
        xs = [float(str(row).strip()) for row in open(xs)]
        ys = [float(str(row).strip()) for row in open(ys)]

    plotted = set()
    
    if title:
        print box_text(title, 2*len(get_scale(xs, False, size))+1)
    
    print "-" * (2*len(get_scale(xs, False, size))+2)
    for y in get_scale(ys, True, size):
        print "|",
        for x in get_scale(xs, False, size):
            point = " "
            for (i, (xp, yp)) in enumerate(zip(xs, ys)):
                if xp <= x and yp >= y and (xp, yp) not in plotted:
                    point = pch
                    #point = str(i) 
                    plotted.add((xp, yp))
            if x==0 and y==0:
                point = "o"
            elif x==0:
                point = "|"
            elif y==0:
                point = "-"
            printcolour(point, True, colour)
        print "|"
    print "-"*(2*len(get_scale(xs, False, size))+2)


def main():

    parser = optparse.OptionParser(usage=scatter['usage'])

    parser.add_option('-f', '--file', help='a csv w/ x and y coordinates', default=None, dest='f')
    parser.add_option('-t', '--title', help='title for the chart', default="", dest='t')
    parser.add_option('-x', help='x coordinates', default=None, dest='x')
    parser.add_option('-y', help='y coordinates', default=None, dest='y')
    parser.add_option('-s', '--size',help='y coordinates', default=20, dest='size', type='int')
    parser.add_option('-p', '--pch',help='shape of point', default="x", dest='pch') 
    parser.add_option('-c', '--colour', help='colour of the plot (%s)' % colour_help, default='default', dest='colour')

    opts, args = parser.parse_args()

    if opts.f is None and (opts.x is None or opts.y is None):
        opts.f = sys.stdin.readlines()

    if opts.f or (opts.x and opts.y):
        plot_scatter(opts.f, opts.x, opts.y, opts.size, opts.pch, opts.colour, opts.t)
    else:
        print "nothing to plot!"


if __name__=="__main__":
    main()

########NEW FILE########
__FILENAME__ = commandhelp
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Usage messages for bashplotlib system commands
"""

hist = {
    "usage": """hist is a command for making histograms. it accepts a series of values in one of the following formats:
        1) txt file w/ 1 column of numbers
        2) standard in piped from another command line cat or curl

    for some examples of how to use hist, you can type the command:
        hist --demo
    or visit https://github.com/glamp/bashplotlib/blob/master/examples/sample.sh
    """
}

scatter = {
    "usage": """scatterplot is a command for making xy plots. it accepts a series of x values and a series of y values in the
    following formats:
        1) a txt file or standard in value w/ 2 comma seperated columns of x,y values
        2) 2 txt files. 1 w/ designated x values and another with designated y values.

    scatter -x <xcoords> -y <ycoords>
    cat <file_with_x_and_y_coords> | scatter
    """
}

########NEW FILE########
__FILENAME__ = helpers
#!/usr/bin/evn python
# -*- coding: utf-8 -*-

"""
Various helpful function for bashplotlib
"""

import sys

bcolours = {
    "white":   '\033[97m',
    "aqua":    '\033[96m',
    "pink":    '\033[95m',
    "blue":    '\033[94m',
    "yellow":  '\033[93m',
    "green":   '\033[92m',
    "red":     '\033[91m',
    "grey":    '\033[90m',
    "black":   '\033[30m',
    "default": '\033[39m',
    "ENDC":    '\033[39m',
}

colour_help = ', '.join([colour for colour in bcolours if colour != "ENDC"])


def get_colour(colour):
    """
    Get the escape code sequence for a colour
    """
    return bcolours.get(colour, bcolours['ENDC'])


def printcolour(text, sameline=False, colour=get_colour("ENDC")):
    """
    Print color text using escape codes
    """
    if sameline:
        sep = ''
    else:
        sep = '\n'
    sys.stdout.write(get_colour(colour) + text + bcolours["ENDC"] + sep)


def drange(start, stop, step=1.0, include_stop=False):
    """
    Generate between 2 numbers w/ optional step, optionally include upper bound
    """
    if step == 0:
        step = 0.01
    r = start

    if include_stop:
        while r <= stop:
            yield r
            r += step
            r = round(r, 10)
    else:
        while r < stop:
            yield r
            r += step
            r = round(r, 10)


def box_text(text, width, offset=0):
    """
    Return text inside an ascii textbox
    """
    box = " " * offset + "-" * (width+2) + "\n"
    box += " " * offset + "|" + text.center(width) + "|" + "\n"
    box += " " * offset + "-" * (width+2)
    return box

########NEW FILE########
