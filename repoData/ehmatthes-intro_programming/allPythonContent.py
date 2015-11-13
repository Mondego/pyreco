__FILENAME__ = multiplying
# Save as multiplying.py

def double(x):
    return 2*x

def triple(x):
    return 3*x

def quadruple(x):
    return 4*x

########NEW FILE########
__FILENAME__ = rocket
from math import sqrt

class Rocket():
    # Rocket simulates a rocket ship for a game,
    #  or a physics simulation.
    
    def __init__(self, x=0, y=0):
        # Each rocket has an (x,y) position.
        self.x = x
        self.y = y
        
    def move_rocket(self, x_increment=0, y_increment=1):
        # Move the rocket according to the paremeters given.
        #  Default behavior is to move the rocket up one unit.
        self.x += x_increment
        self.y += y_increment
        
    def get_distance(self, other_rocket):
        # Calculates the distance from this rocket to another rocket,
        #  and returns that value.
        distance = sqrt((self.x-other_rocket.x)**2+(self.y-other_rocket.y)**2)
        return distance


class Shuttle(Rocket):
    # Shuttle simulates a space shuttle, which is really
    #  just a reusable rocket.
    
    def __init__(self, x=0, y=0, flights_completed=0):
        super().__init__(x, y)
        self.flights_completed = flights_completed

########NEW FILE########
__FILENAME__ = add_bootstrap
# This script runs through all the html files in notebooks/, and adds in 
#  bootstrap tags where appropriate.

import os
import subprocess
import sys

# Pull out navbar from custom index.html page
f = open('/srv/projects/intro_programming/intro_programming/html_resources/index.html', 'r')
lines = f.readlines()
f.close()

navbar_string = ''
in_navbar = False
num_open_divs = 0
num_closed_divs = 0
for line in lines:
    # Navbar is in first div for now, so at first div set True.
    #  Could start from 'Fixed navbar'
    if '<div' in line:
        in_navbar = True
        num_open_divs += 1

    if '</div' in line:
        num_closed_divs += 1

    if in_navbar:
        navbar_string += line

    if num_open_divs > 0 and num_open_divs == num_closed_divs:
        in_navbar = False
        break

# jquery is included in the header of each page, so I can use it elsewhere
#  ie for toggling output and exercises.
#    <script src="js/jquery.js"></script>
final_js_string = """
    <!-- Bootstrap core JavaScript
    ================================================== -->
    <!-- Placed at the end of the document so the pages load faster -->
    <script src="js/bootstrap.min.js"></script>
"""


# Find all files to work with.
path_to_notebooks = '/srv/projects/intro_programming/intro_programming/notebooks/'
filenames = []
for filename in os.listdir(path_to_notebooks):
    if '.html' in filename and filename != 'index.html':
        filenames.append(filename)

# Insert navbar into each file, right after opening body tag.
#  Then insert required js library at end of file.
for filename in filenames:

    f = open(path_to_notebooks + filename, 'r')
    lines = f.readlines()
    f.close()

    f = open(path_to_notebooks + filename, 'wb')
    for line in lines: 
       if '<body>' in line:
            f.write(line.encode('utf-8'))
            f.write(navbar_string.encode('utf-8'))
            f.write("\n\n".encode('utf-8'))
       elif '</body>' in line:
           f.write(final_js_string.encode('utf-8'))
           f.write(line.encode('utf-8'))
       else:
            f.write(line.encode('utf-8'))
    f.close()

########NEW FILE########
__FILENAME__ = build_all_exercises_page
# This script scrapes all html pages, pulls out the exercises
#  and challenges, and copies them to the all_exercises_challenges.html
#  page.

import os, sys, re

print("Building all_exercises_challenges.html...")

path_to_notebooks = '/srv/projects/intro_programming/intro_programming/notebooks/'

# Work through notebooks in the order listed here.
filenames = ['var_string_num.html', 'lists_tuples.html',
             'introducing_functions.html', 'if_statements.html',
             'while_input.html', 'terminal_apps.html',
             'dictionaries.html', 'classes.html',
             ]

# one file for testing:
#filenames = ['var_string_num.html']


def add_contents(html_string):
    # Once all pages have been scraped, parse html_string and 
    #  build contents.
    toc_string = '<div class="text_cell_render border-box-sizing rendered_html">\n'
    toc_string += "<h1>Contents</h1>\n"

    new_html_string = ''
    section_num = 0
    ex_ch_num = 0
    for line in html_string.split("\n"):
        if '<h1>' in line:

            # Rewrite the html_string line to have id that I want.
            #  Pull out section title from line.
            section_anchor = '<a name="section_%d"></a>' % section_num
            new_line = line.replace('<h1>', '<h1>%s' % section_anchor)
            new_html_string += new_line + "\n"

            section_re = """(<h1.*>)(.*)(</a></h1>)"""
            p = re.compile(section_re)
            m = p.match(line)
            if m:
                toc_string += '<h2><a href="#section_%d">%s</a></h2>\n' % (section_num, m.group(2))

            section_num += 1

        elif ('id="exercises' in line 
            or 'id="challenges' in line
            or 'id="overall-exercises' in line
            or 'id="overall-challenges' in line):

            # Rewrite the html_string line to have id that I want.
            #  Pull out page title from line.
            ex_ch_anchor = '<a name="ex_ch_%d"></a>' % ex_ch_num
            new_line = re.sub(r"""<a name=['"].*?['"]></a>""", ex_ch_anchor, line)
            new_html_string += new_line + "\n"

            ex_ch_re = """<.*/a>(.*)<a href.*>(.*)</a>"""
            p = re.compile(ex_ch_re)
            m = p.match(line)
            if m:
                toc_string += '<h3 class="contents_level_two">%s<a href="#ex_ch_%d">%s</a></h3>\n' % (m.group(1), ex_ch_num, m.group(2))

            ex_ch_num += 1

        else:
            new_html_string += line + "\n"

    toc_string += "</div>\n"
    toc_string += "<hr />\n\n"

    return toc_string + new_html_string


def anchor_exercises(html_string):
    # Add an anchor link to each exercise, so people can share any
    #  individual exercise.
    # Use name of exercise as anchor, but watch for repeated names.
    #  If repeated name, add a number to anchor.
    anchors = []
    new_html_string = ''
    for line in html_string.split("\n"):
        ex_ch_re = """<h4 id="(.*?)">(.*?)</h4>"""
        p = re.compile(ex_ch_re)
        m = p.match(line)
        if m:
            anchor = m.group(1)
            name = m.group(2)
            if anchor in anchors:
                new_anchor = anchor
                append_num = 1
                while new_anchor in anchors:
                    new_anchor = anchor + '_%d' % append_num
                    append_num += 1
                anchor = new_anchor

            # Rewrite line to include anchor tag, and to link to this
            #  anchor tag.
            anchor_tag = '<a name="%s"></a>' % anchor
            new_line = '%s<h4 id="%s"><a href="all_exercises_challenges.html#%s">%s</a></h4>\n' % (anchor_tag, anchor, anchor, name)
            new_html_string += new_line
        else:
            new_html_string += line + "\n"

    return new_html_string


def add_intro(html_string):
    # Add an intro to html_string, before adding any exercises.
    intro_string  = '<div class="text_cell_render border-box-sizing rendered_html">\n'
    intro_string += '<h1>All Exercises and Challenges</h1>\n'
    intro_string += '<p>This page pulls together all of the exercises and challenges from throughout <a href="http://introtopython.org">introtopython.org</a>.</p>\n'
    intro_string += '<p>Each set of exercises has a link to the relevant section that explains what you need to know to complete those exercises. If you are struggling with an exercise, try reading through the linked material, and see if it helps you solve the exercise you are working on.</p>\n'
    intro_string += '<p>Exercises are short, specific tasks that ask you to apply a certain concept in a specific way. Challenges are longer, and they ask you to combine different ideas you have been working with. Challenges also ask you to be a little more creative in the programs you are starting to write.</p>\n'

    intro_string += '</div>\n'
    intro_string += '<hr />\n'
    return intro_string + html_string


def get_h1_label(line):
    # Pulls the label out of an h1 header line.
    #  This should be the label for what a set of exercises relates to.
    label_re = "(<h1.*>)(.*)(</h1)"
    p = re.compile(label_re)
    m = p.match(line)
    if m:
        return m.group(2)


def get_h1_link(filename, line):
    # Pulls the anchor link from the h1 line, and builds a link to
    #  the anchor on that page.
    link_re = """(.*)(<a name=['"])(.*)(['"].*)"""
    p = re.compile(link_re)
    m = p.match(line)
    if m:
        link = "%s#%s" % (filename, m.group(3))
        return link


def get_page_title(filename):
    # Pulls the page title from the notebook. It's in the first <h1>
    #  block in each notebook.
    for line in lines:
        if '<h1' in line:
            title_re = """(<h1.*>)(.*)(</h1)"""
            p = re.compile(title_re)
            m = p.match(line)
            if m:
                return m.group(2)


def get_new_notebook_header(filename, lines):
    # Creates an html string for a header for each notebook
    #  being scraped.
    page_title = get_page_title(filename)
    link = "%s" % filename
    header_html = '<div class="text_cell_render border-box-sizing rendered_html">\n'
    header_html += "<h1><a href='%s'>%s</a></h1>\n" % (link, page_title)
    header_html += "</div>\n"
    return header_html


def rebuild_anchor_links(filename, line):
    # Looks for an anchor tag. If present, rebuilds link to link
    #  back to place on page being scraped.
    anchor_re = """.*(<a href=['"]#(.*))['"].*"""
    anchor_re = """.*<a href=['"](#.*)['"].*"""
    p = re.compile(anchor_re)
    m = p.match(line)
    if m:
        anchor_link = m.group(1)
        new_link = "%s%s" % (filename, anchor_link)
        return line.replace(anchor_link, new_link)
    else:
        return line

def top_html():
    # Returns html for a link to top of page.
    top_string = '<div class="text_cell_render border-box-sizing rendered_html">\n'
    top_string += '<p><a href="#">top</a></p>\n'
    top_string += '</div>\n'
    top_string += '<hr />\n'
    return top_string

# Grab all exercises and challenges.
#  Start building html string.
html_string = ""
for filename in filenames:

    # Grab entire page
    f = open(path_to_notebooks + filename, 'r')
    lines = f.readlines()
    f.close()

    in_exercises_challenges = False
    # Will need to keep track of section that the exercises are part of.
    current_h1_label = ''
    h1_label_linked = ''

    # Add a header for each notebook that has exercises.
    html_string += get_new_notebook_header(filename, lines)

    for index, line in enumerate(lines):
        # Anchor links need to be rebuilt.
        #  Inefficient, runs for every line. Could be moved to just
        #  before a line is being written to html_string, 
        #  but not significant.
        line = rebuild_anchor_links(filename, line)

        if '<h1' in line:
            current_h1_label = get_h1_label(line)
            current_h1_link = get_h1_link(filename, line)
            h1_label_linked = "<a href='%s'>%s</a>" % (current_h1_link, current_h1_label)

            # If this is Overall Exercises or Overall Challenges,
            #  link to the notebook not the last h1 section.
            # Naming inconsistency; still calling these pieces ...h1...
            if 'verall' in line:
                current_h1_link = "%s" % filename
                current_h1_label = get_page_title(filename)
                h1_label_linked = "<a href='%s'>%s</a>" % (current_h1_link, current_h1_label)


        if ('<h2 id="exercises' in line 
            or '<h2 id="challenges' in line
            or '<h1 id="overall-challenges' in line
            or '<h1 id="overall-exercises' in line):
            # This is the signature of an exercise block.

            # Capture the previous line, which opens the div for the exercises.
            #  Current line will be captured in "if in_exercises" block.
            # Only do this if in_exercises_challenges currently False.
            if not in_exercises_challenges:
                html_string += lines[index-1]

            in_exercises_challenges = True
            html_string += "\n"

            # Add the most recent h1 label to this line.
            if 'Exercises' in line:
                line = line.replace('Exercises', 'Exercises - %s' % h1_label_linked)
            elif 'Challenges' in line:
                line = line.replace('Challenges', 'Challenges - %s' % h1_label_linked)

            # Make sure these elements are all written at the h2 level:
            line = line.replace('h1', 'h2')

        if in_exercises_challenges:
            # Stop adding lines when reach next 'top'.
            #  Remove div that was opened for the top line.
            #  This approach allows multiple cells to be part of
            #   exercises and challenges, but still be scraped.
            if '<div class="text_cell_render border-box-sizing rendered_html">' in line:
                # If next line has a link to top, stop here.
                if '<a href="#">top</a>' in lines[index+1]:
                    in_exercises_challenges = False
                    html_string += "\n"
                    continue

            # Store the current line
            html_string += line

    # Finished scraping a notebook, add a link to top of this page.
    html_string += top_html()

# Pages have been scraped; build contents from html_string.
html_string = add_contents(html_string)
# Add an intro.
html_string = add_intro(html_string)
# Add anchor links to each exercise.
html_string = anchor_exercises(html_string)

# Read in all_exercises_challenges.html
f = open(path_to_notebooks + 'all_exercises_challenges.html', 'r')
lines = f.readlines()
f.close()

# Write html to all_exercises_challenges.html
f = open(path_to_notebooks + 'all_exercises_challenges.html', 'wb')

# Want to start writing this after <body>
for line in lines: 
    if '<body>' in line:
        # Write line, then html_string
        f.write(line.encode('utf-8'))
        f.write(html_string.encode('utf-8'))
        # Don't write this line twice.
        continue
    # Need to write each line back to the file.
    f.write(line.encode('utf-8'))

f.close()


print("Built all_exercises_challenges.html...")

########NEW FILE########
__FILENAME__ = highlight_code
# This script runs through all the html files in notebooks/, and 
#  converts `###highlight=[1,2,10,11,12]` directives to style directives
#  for highlighting lines of code in code cells.

# To highlight lines of code in a cell, add a comment on the first
#  line of the cell, starting with three pound symbols, the word
#  'highlight', and an equals sign with no space. Then write a Python
#  list, with each line to be highlighted listed. The script only reads
#  comma-separated values, not grouped values. 

# yes: '###highlight=[1,2,7,8,9]'
# no:  '###highlight=[1,2,7-9]'

# You can turn line numbering on in the notebook, and just use the line
#  numbers that are displayed. The script adjusts for the first line 
#  being taken up by the ###highlight= comment. The script also removes
#  the ###highlight= comment from the html file, but does not remove
#  the highlighting directive from the notebook itself.

# The script adds the style directive
# <div class="highlighted_code_line">...current code html...</div>
# to the selected code lines.

# The script assumes all html files are not nested, in a directory called
#  'notebooks'.

# You will need to specificy path_to_notebooks.
# I'm happy to hear feedback, and accept improvements:
# https://github.com/ehmatthes/intro_programming
# ehmatthes@gmail.com, @ehmatthes


import os, sys
import ast

print("\nHighlighting code...")

# Find all files to work with.
#  Replace with your path.
path_to_notebooks = '/srv/projects/intro_programming/intro_programming/notebooks/'

filenames = []
for filename in os.listdir(path_to_notebooks):
    if '.html' in filename and filename != 'index.html':
        filenames.append(filename)

# Uncomment to use just one file for testing:
#filenames = ['visualization_earthquakes.html']


# Process each file.
for filename in filenames:

    # Grab the lines from this html file.
    f = open(path_to_notebooks + filename, 'r')
    lines = f.readlines()
    f.close()

    # Open the file for rewriting.
    f = open(path_to_notebooks + filename, 'wb')

    # Create an empty list for the lines that will need to be highlighted.
    highlight_lines = []
    # True when in a code block that has some highlighting left to be done.
    highlighting_active = False

    # Next line to highlight; starts at 0 in each code block.
    #  This takes into account the ###highlight= line, so you don't have
    #  to do a bunch of subtracting while composing notebooks.
    highlight_line = None

    for line in lines: 
        if '###highlight' in line:
            # Get lines to highlight, stored as a list.
            #  Lines are in a list, after the equals sign.
            try:
                highlight_lines = ast.literal_eval(line[line.index('highlight=')+10:line.index(']')+1])
            except:
                print("Problem finding lines to highlight in %s near line %d" % (filename, lines.index(line)))
            
            # We have some lines to highlight. Start tracking lines,
            #  and highlight appropriate lines.
            line_number = 0
            highlighting_active = True

        if highlighting_active:
            # We are in a code block, with some lines left to highlight.
            if line_number == 0:
                # We are on the ###highlight= line, and we don't need this entire line.
                #  We do need some of the line, which sets up the code block.
                # sample line: <div class="highlight"><pre><span class="c">###highlight=[2,3]</span>
                # becomes: <div class="highlight"><pre>
                # keep until start of '<span'
                span_index = line.index('<span')
                f.write(line[:span_index].encode('utf-8'))
                line_number += 1
                # Next line to highlight:
                #  Minus 1 accounts for initial comment line ###highlight=...,
                #  which will be removed.
                highlight_line = highlight_lines.pop(0)-1
            elif line_number == highlight_line:
                # Change style so line is highlighted.
                line = "<div class='highlighted_code_line'>%s</div>" % line
                f.write(line.encode('utf-8'))
                line_number += 1
                try:
                    # Get next line to highlight.
                    highlight_line = highlight_lines.pop(0)-1
                except:
                    # No more lines to highlight in this code block.
                    highlight_line = None
                    highlighting_active = False
            else:
                # Write line of code as is.
                f.write(line.encode('utf-8'))
                line_number += 1
        else:
            # No highlighting left to do in this code block, or
            #  not in a code block with highlighting.
            #  Write line as is.
            f.write(line.encode('utf-8'))

    f.close()

print("Highlighted code.\n")

########NEW FILE########
__FILENAME__ = modify_facebook_urls
# This script runs through all the html files in notebooks/, and 
#  modifies data-href url to current page.
# Prefer this to blank data-href so button shows up on local dev env.

import os
import sys

print("Modifying facebook urls...")

# Find all files to work with.
path_to_notebooks = '/srv/projects/intro_programming/intro_programming/notebooks/'
filenames = []
for filename in os.listdir(path_to_notebooks):
    if '.html' in filename and filename != 'index.html':
        filenames.append(filename)

# one file for testing:
#filenames = ['hello_world.html']

# Modify url on each page:
old_fb_url = 'data-href="http://introtopython.org"'
for filename in filenames:

    new_fb_url = 'data-href="http://introtopython.org/%s"' % filename

    f = open(path_to_notebooks + filename, 'r')
    lines = f.readlines()
    f.close()

    f = open(path_to_notebooks + filename, 'wb')
    for line in lines: 
       if old_fb_url in line:
            new_line = line.replace(old_fb_url, new_fb_url)
            f.write(new_line.encode('utf-8'))
       else:
            f.write(line.encode('utf-8'))
    f.close()


print("Modified facebook urls.\n")



########NEW FILE########
__FILENAME__ = remove_input_references
# This script removes the input reference numbers from html pages.
#  They play a useful role in scientific notebooks, but they are really
#  just visual clutter in this project.
# Could be an nbconvert setting, but it's an easy enough scripting job.

import os
import sys

print("Stripping input reference numbers from code cells...")

# Find all files to work with.
path_to_notebooks = '/srv/projects/intro_programming/intro_programming/notebooks/'
filenames = []
for filename in os.listdir(path_to_notebooks):
    if '.html' in filename and filename != 'index.html':
        filenames.append(filename)

# one file for testing:
#filenames = ['hello_world.html']

for filename in filenames:

    f = open(path_to_notebooks + filename, 'r')
    lines = f.readlines()
    f.close()

    f = open(path_to_notebooks + filename, 'wb')
    in_input_prompt = False
    skipped_lines = 0
    for line in lines: 
        if '<div class="prompt input_prompt">' in line:
            # Don't write this line, or the next two lines.
            in_input_prompt = True
            skipped_lines = 1
            continue
        elif in_input_prompt:
            # Run this block exactly twice.
            skipped_lines += 1
            if skipped_lines > 3:
                # Write current line, and reset relevant flags.
                f.write(line.encode('utf-8'))
                in_input_prompt = False
                skipped_lines = 0
        else:
            # Regular line, write it.
            f.write(line.encode('utf-8'))
                
    f.close()


print("Stripped input reference numbers.\n")


########NEW FILE########
__FILENAME__ = show_hide_output
# This script runs through all the html files in notebooks/, and adds
#  in code to allow toggling of output.

import os
import re
import sys

# Find all files to work with.
path_to_notebooks = '/srv/projects/intro_programming/intro_programming/notebooks/'
filenames = []
for filename in os.listdir(path_to_notebooks):
    if '.html' in filename and filename != 'index.html':
        filenames.append(filename)

# Test with one simple file.
#filenames = ['hello_world.html']



def generate_button(id_number):
    # Generate the button code to place before each div.output
    button_string =  "<div class='text-right'>\n"
    button_string += "    <button id='show_output_%d' class='btn btn-success btn-xs show_output' target='%d'>show output</button>\n" % (id_number, id_number)
    button_string += "    <button id='hide_output_%d' class='btn btn-success btn-xs hide_output' target='%d'>hide output</button>\n" % (id_number, id_number)
    button_string += "</div>\n"
    return button_string

def generate_show_hide_all_buttons():
    # Generate the buttons that show or hide all output.
    button_string =  "<div class='text-right'>\n"
    button_string += "    <button id='show_output_all' class='btn btn-success btn-xs show_output_all'>Show all output</button>\n"
    button_string += "    <button id='hide_output_all' class='btn btn-success btn-xs hide_output_all'>Hide all output</button>\n"
    button_string += "</div>\n"
    return button_string

# Determine which files have output. Only add buttons to files with output.
files_with_output = []
for filename in filenames:
    f = open(path_to_notebooks + filename, 'r')
    lines = f.readlines()
    f.close()

    target_string = '<div class="output '
    for line in lines:
        if target_string in line:
            files_with_output.append(filename)
            break


# Find all div.output, and add an id to each.
#  Add show/ hide buttons to each output
#  For each file, add show_all, hide_all buttons just under navbar
#    This is after second div.container element
for filename in files_with_output:
    container_number = 0
    f = open(path_to_notebooks + filename, 'r')
    lines = f.readlines()
    f.close()

    target_string = '<div class="output '
    f = open(path_to_notebooks + filename, 'wb')
    replacement_num = 0
    for line in lines:

        if "<div class='container'>" in line or '<div class="container">' in line:
            # Add show_all hide_all buttons in second container.
            container_number += 1
            f.write(line.encode('utf-8'))
            if container_number == 2:
                f.write(generate_show_hide_all_buttons().encode('utf-8'))
        elif target_string in line:
            # If this line has a div.output, add an id
            replacement_string = '<div id="output_%d" class="output ' % replacement_num
            
            # Add a pair of show/ hide buttons right before div.output
            f.write(generate_button(replacement_num).encode('utf-8'))
            f.write(line.replace(target_string, replacement_string).encode('utf-8'))
            replacement_num += 1
        else:
            # Otherwise, rewrite the line.
            f.write(line.encode('utf-8'))













########NEW FILE########
__FILENAME__ = test_links
import requests
import re
import os, subprocess, signal, sys
from getopt import getopt
from time import sleep

# This test runs through all html files in /notebooks,
#  and verifies that links are working.

# to do
#  check anchor tags as well
#  accept flag to check deployed pages
#  should I be using beautifulsoup to parse html?

# Get command-line arguments
#  -r --root: The root directory that files are served from
#  (not yet implemented) -d --directory: The directory where files are stored locally
#  Should clarify that this test currently pulls links from local files,
#   but can test deployed version of files. That only makes sense
#   if deployed version matches current local version.
#  Should either pull links locally, and test locally, or
#   pull from deployed site, and test deployed site.

root = 'http://localhost:8000/'
opts, args = getopt(sys.argv[1:], "r:", ["root=",])
for opt, arg in opts:
    if opt in ('--root', '-r'):
        root = arg + '/'
print("Using root: ", root)


def get_links_in_line(line):
    # Returns a list of links contained in a line of code.
    links = []

    # Split lines so they start with links.
    #  ie, segments will be ~ ="hello_world.html">blah
    link_re = """=(["'])(.*?)(["'].*)"""
    p = re.compile(link_re)
    for segment in line.split('a href'):
        m = p.match(segment)
        if m:
            #print 'match: ', m.group(2)
            links.append(m.group(2))
    return links

def get_links_in_file(root_dir, filename):
    # Returns a list of all the links in a file.
    f = open(root_dir + filename, 'r')
    lines = f.readlines()
    f.close()

    links_to_check = []
    for line in lines:
        if 'a href' in line:
            for link in get_links_in_line(line):
                # Ignore anchor tags for now
                if 'html' in link:
                    links_to_check.append(link)
    return links_to_check

def check_links(filename, links, bad_links, links_tested):
    # Checks all links given, and adds bad links to bad_links.
    print("links to check: ", links)
    for link in links:
        print("Checking link: %s..." % link)

        # Only check links that haven't already been checked:
        if link in links_tested:
            continue
        
        # External links don't need our root.
        if 'http' in link:
            url = link
        else:
            url = root + link
        print('checking url: ', url)
        r = requests.get(url)
        print('Status code: ', r.status_code)
        if r.status_code != 200:
            bad_links[filename + '---' + link] = r.status_code
        else:
            links_tested.append(link)

# Location of html files
#  Assume all files in this directory, no nesting
root_dir = '/srv/projects/intro_programming/intro_programming/notebooks/'

# Get all html filenames in this directory.
#  Use os.walk if files end up nested.
filenames = []
for filename in os.listdir(root_dir):
    if 'html' in filename:
        filenames.append(filename)


# Start a server locally, in the notebooks directory.
print("Starting server...")
cmd = 'chdir /srv/projects/intro_programming/intro_programming/notebooks/ && '
cmd += 'python -m SimpleHTTPServer'
pro = subprocess.Popen(cmd, shell=True, preexec_fn=os.setsid)

# Make sure server has a chance to start before making request.
print("SLEEPING...")
sleep(1)

# Report on progress as test runs, but store bad links for final report.
#  dict: {page---link: status_code}
bad_links = {}

# Only test each unique link once.
links_tested = []
num_links_checked = 0

# Check links in all files.
#filenames = ['var_string_num.html']
for filename in filenames:
    links_to_check = get_links_in_file(root_dir, filename)
    check_links(filename, links_to_check, bad_links, links_tested)
    num_links_checked += len(links_to_check)

# Kill the server process
os.killpg(pro.pid, signal.SIGTERM)

# Report on bad links.
print("\n\n*** Bad Links ***")
if bad_links:
    for link in bad_links:
        print('\n', bad_links[link], link)
else:
    print("Congratulations, all links are working.")
print("\n")

print("Checked %d links." % num_links_checked)
print("Tested %d unique links." % len(links_tested))

########NEW FILE########
