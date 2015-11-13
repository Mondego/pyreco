__FILENAME__ = clearOldCache
#!/usr/bin/python

"""Deletes files from the old chunk-based cache"""


usage = "python contrib/%prog [OPTIONS] <World # / Name / Path to World>"

description = """
This script will delete files from the old chunk-based cache, a lot
like the old `overviewer.py -d World/` command. You should only use this if
you're updating from an older version of Overviewer, and you want to
clean up your world folder.
"""

from optparse import OptionParser
import sys
import re
import os.path

# incantation to be able to import overviewer_core
if not hasattr(sys, "frozen"):
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.split(__file__)[0], '..')))

from overviewer_core import world
from overviewer import list_worlds

def main():
    parser = OptionParser(usage=usage, description=description)
    parser.add_option("-d", "--dry-run", dest="dry", action="store_true",
                      help="Don't actually delete anything. Best used with -v.")
    parser.add_option("-k", "--keep-dirs", dest="keep", action="store_true",
                      help="Keep the world directories intact, even if they are empty.")
    parser.add_option("-v", "--verbose", dest="verbose", action="store_true",
                      help="Log each and every file that is deleted.")
    
    opt, args = parser.parse_args()
    
    if not len(args) == 1:
        parser.print_help()
        sys.exit(1)
        
    worlddir = args[0]

    if not os.path.exists(worlddir):
        # world given is either world number, or name
        worlds = world.get_worlds()
        
        # if there are no worlds found at all, exit now
        if not worlds:
            parser.print_help()
            print "\nInvalid world path"
            sys.exit(1)
        
        try:
            worldnum = int(worlddir)
            worlddir = worlds[worldnum]['path']
        except ValueError:
            # it wasn't a number or path, try using it as a name
            try:
                worlddir = worlds[worlddir]['path']
            except KeyError:
                # it's not a number, name, or path
                parser.print_help()
                print "Invalid world name or path"
                sys.exit(1)
        except KeyError:
            # it was an invalid number
            parser.print_help()
            print "Invalid world number"
            sys.exit(1)
    
    files_deleted = 0
    dirs_deleted = 0
    
    imgre = re.compile(r'img\.[^.]+\.[^.]+\.nocave\.\w+\.png$')
    for dirpath, dirnames, filenames in os.walk(worlddir, topdown=False):
        for f in filenames:
            if imgre.match(f):
                filepath = os.path.join(dirpath, f)
                if opt.verbose:
                    print "Deleting %s" % (filepath,)
                if not opt.dry:
                    os.unlink(filepath)
                    files_deleted += 1
        
        if not opt.keep:
            if len(os.listdir(dirpath)) == 0:
                if opt.verbose:
                    print "Deleting %s" % (dirpath,)
                if not opt.dry:
                    os.rmdir(dirpath)
                    dirs_deleted += 1
    
    print "%i files and %i directories deleted." % (files_deleted, dirs_deleted)

if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = contributors
#!/usr/bin/python2
"""Update the contributor list

Alias handling is done by git with .mailmap
New contributors are merged in the short-term list.
Moving them to a "higher" list should be a manual process.
"""

import fileinput
from subprocess import Popen, PIPE

def format_contributor(contributor):
    return " * {0} {1}".format(
            " ".join(contributor["name"]),
            contributor["email"])


def main():
    # generate list of contributors
    contributors = []
    p_git = Popen(["git", "shortlog", "-se"], stdout=PIPE)
    for line in p_git.stdout:
        contributors.append({
            'count': int(line.split("\t")[0].strip()),
            'name': line.split("\t")[1].split()[0:-1],
            'email': line.split("\t")[1].split()[-1]
            })

    # cache listed contributors
    old_contributors = []
    with open("CONTRIBUTORS.rst", "r") as contrib_file:
        for line in contrib_file:
            if "@" in line:
                old_contributors.append({
                    'name': line.split()[1:-1],
                    'email': line.split()[-1]
                    })

    old = map(lambda x: (x['name'], x['email']), old_contributors)
    old_emails = map(lambda x: x['email'], old_contributors)
    old_names = map(lambda x: x['name'], old_contributors)

    # check which contributors are new
    new_contributors = []
    update_mailmap = False
    for contributor in contributors:
        if (contributor['name'], contributor['email']) in old:
            # this exact combination already in the list
            pass
        elif (contributor['email'] not in old_emails
                and contributor['name'] not in old_names):
            # name AND email are not in the list
            new_contributors.append(contributor)
        elif contributor['email'] in old_emails:
            # email is listed, but with another name
            old_name = filter(lambda x: x['email'] == contributor['email'],
                    old_contributors)[0]['name']
            print "new alias %s for %s %s ?" % (
                    " ".join(contributor['name']),
                    " ".join(old_name),
                    contributor['email'])
            update_mailmap = True
        elif contributor['name'] in old_names:
            # probably a new email for a previous contributor
            other_mail = filter(lambda x: x['name'] == contributor['name'],
                old_contributors)[0]['email']
            print "new email %s for %s %s ?" % (
                contributor['email'],
                " ".join(contributor['name']),
                other_mail)
            update_mailmap = True
    if update_mailmap:
        print "Please update .mailmap"

    # sort on the last word of the name
    new_contributors = sorted(new_contributors,
            key=lambda x: x['name'][-1].lower())

    # show new contributors to be merged to the list
    if new_contributors:
        print "inserting:"
        for contributor in new_contributors:
            print format_contributor(contributor)

    # merge with alphabetical (by last part of name) contributor list
    i = 0
    short_term_found = False
    for line in fileinput.input("CONTRIBUTORS.rst", inplace=1):
        if not short_term_found:
            print line,
            if "Short-term" in line:
                short_term_found = True
        else:
            if i >= len(new_contributors) or "@" not in line:
                print line,
            else:
                listed_name = line.split()[-2].lower()
                contributor = new_contributors[i]
                # insert all new contributors that fit here
                while listed_name > contributor["name"][-1].lower():
                    print format_contributor(contributor)
                    i += 1
                    if i < len(new_contributors):
                        contributor = new_contributors[i]
                    else:
                        break
                print line,
    # append remaining contributors
    with open("CONTRIBUTORS.rst", "a") as contrib_file:
        while i < len(new_contributors):
            contrib_file.write(format_contributor(new_contributors[i]) + "\n")
            i += 1


if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = cyrillic_convert
#!/usr/bin/python

"""Convert gibberish back into Cyrillic"""

import fileinput
import os
import sys

usage = """
If you have signs that should be Cyrillic, but are instead gibberish,
this script will convert it back to proper Cyrillic.

usage: python %(script)s <markers.js>
ex. python %(script)s C:\\Inetpub\\www\\map\\markers.js
 or %(script)s /srv/http/map/markers.js
""" % {'script': os.path.basename(sys.argv[0])}

if len(sys.argv) < 2:
    sys.exit(usage)

gibberish_to_cyrillic = {
    r"\u00c0": r"\u0410",
    r"\u00c1": r"\u0411",
    r"\u00c2": r"\u0412",
    r"\u00c3": r"\u0413",
    r"\u00c4": r"\u0414",
    r"\u00c5": r"\u0415",
    r"\u00c6": r"\u0416",
    r"\u00c7": r"\u0417",
    r"\u00c8": r"\u0418",
    r"\u00c9": r"\u0419",
    r"\u00ca": r"\u041a",
    r"\u00cb": r"\u041b",
    r"\u00cc": r"\u041c",
    r"\u00cd": r"\u041d",
    r"\u00ce": r"\u041e",
    r"\u00cf": r"\u041f",
    r"\u00d0": r"\u0420",
    r"\u00d1": r"\u0421",
    r"\u00d2": r"\u0422",
    r"\u00d3": r"\u0423",
    r"\u00d4": r"\u0424",
    r"\u00d5": r"\u0425",
    r"\u00d6": r"\u0426",
    r"\u00d7": r"\u0427",
    r"\u00d8": r"\u0428",
    r"\u00d9": r"\u0429",
    r"\u00da": r"\u042a",
    r"\u00db": r"\u042b",
    r"\u00dc": r"\u042c",
    r"\u00dd": r"\u042d",
    r"\u00de": r"\u042e",
    r"\u00df": r"\u042f",
    r"\u00e0": r"\u0430",
    r"\u00e1": r"\u0431",
    r"\u00e2": r"\u0432",
    r"\u00e3": r"\u0433",
    r"\u00e4": r"\u0434",
    r"\u00e5": r"\u0435",
    r"\u00e6": r"\u0436",
    r"\u00e7": r"\u0437",
    r"\u00e8": r"\u0438",
    r"\u00e9": r"\u0439",
    r"\u00ea": r"\u043a",
    r"\u00eb": r"\u043b",
    r"\u00ec": r"\u043c",
    r"\u00ed": r"\u043d",
    r"\u00ee": r"\u043e",
    r"\u00ef": r"\u043f",
    r"\u00f0": r"\u0440",
    r"\u00f1": r"\u0441",
    r"\u00f2": r"\u0442",
    r"\u00f3": r"\u0443",
    r"\u00f4": r"\u0444",
    r"\u00f5": r"\u0445",
    r"\u00f6": r"\u0446",
    r"\u00f7": r"\u0447",
    r"\u00f8": r"\u0448",
    r"\u00f9": r"\u0449",
    r"\u00fa": r"\u044a",
    r"\u00fb": r"\u044b",
    r"\u00fc": r"\u044c",
    r"\u00fd": r"\u044d",
    r"\u00fe": r"\u044e",
    r"\u00ff": r"\u044f"
}

for line in fileinput.FileInput(inplace=1):
    for i, j in gibberish_to_cyrillic.iteritems():
        line = line.replace(i, j)
    sys.stdout.write(line)


########NEW FILE########
__FILENAME__ = findSigns
#!/usr/bin/python

'''
Updates overviewer.dat file sign info

This script will scan through every chunk looking for signs and write out an
updated overviewer.dat file.  This can be useful if your overviewer.dat file
is either out-of-date or non-existant.  

To run, simply give a path to your world directory and the path to your
output directory. For example:

    python contrib/findSigns.py ../world.test/ output_dir/ 

An optional north direction may be specified as follows:
    
    python contrib/findSigns.py ../world.test/ output_dir/ lower-right

Valid options are upper-left, upper-right, lower-left and lower-right.
If no direction is specified, lower-left is assumed

Once that is done, simply re-run the overviewer to generate markers.js:

    python overviewer.py ../world.test/ output_dir/

'''
import sys
import re
import os
import cPickle

# incantation to be able to import overviewer_core
if not hasattr(sys, "frozen"):
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.split(__file__)[0], '..')))

from overviewer_core import nbt

from pprint import pprint
if len(sys.argv) < 3:
    sys.exit("Usage: %s <worlddir> <outputdir> [north_direction]" % sys.argv[0])
    
worlddir = sys.argv[1]
outputdir = sys.argv[2]

directions=["upper-left","upper-right","lower-left","lower-right"]
if len(sys.argv) < 4:
    print "No north direction specified - assuming lower-left"
    north_direction="lower-left"
else:
    north_direction=sys.argv[3]

if (north_direction not in directions):
    print north_direction, " is not a valid direction"
    sys.exit("Bad north-direction")

if os.path.exists(worlddir):
    print "Scanning chunks in ", worlddir
else:
    sys.exit("Bad WorldDir")

if os.path.exists(outputdir):
    print "Output directory is ", outputdir
else:
    sys.exit("Bad OutputDir")

matcher = re.compile(r"^r\..*\.mcr$")

POI = []

for dirpath, dirnames, filenames in os.walk(worlddir):
    for f in filenames:
        if matcher.match(f):
            print f
            full = os.path.join(dirpath, f)
            # force lower-left so chunks are loaded in correct positions
            r = nbt.load_region(full, 'lower-left')
            chunks = r.get_chunks()
            for x,y in chunks:
                chunk = r.load_chunk(x,y).read_all()                
                data = chunk[1]['Level']['TileEntities']
                for entity in data:
                    if entity['id'] == 'Sign':
                        msg=' \n'.join([entity['Text1'], entity['Text2'], entity['Text3'], entity['Text4']])
                        #print "checking -->%s<--" % msg.strip()
                        if msg.strip():
                            newPOI = dict(type="sign",
                                            x= entity['x'],
                                            y= entity['y'],
                                            z= entity['z'],
                                            msg=msg,
                                            chunk= (entity['x']/16, entity['z']/16),
                                           )
                            POI.append(newPOI)
                            print "Found sign at (%d, %d, %d): %r" % (newPOI['x'], newPOI['y'], newPOI['z'], newPOI['msg'])


if os.path.isfile(os.path.join(worlddir, "overviewer.dat")):
    print "Overviewer.dat detected in WorldDir - this is no longer the correct location\n"
    print "You may wish to delete the old file. A new overviewer.dat will be created\n"
    print "Old file: ", os.path.join(worlddir, "overviewer.dat")

pickleFile = os.path.join(outputdir,"overviewer.dat")
with open(pickleFile,"wb") as f:
    cPickle.dump(dict(POI=POI,north_direction=north_direction), f)


########NEW FILE########
__FILENAME__ = gallery
"""
Outputs a huge image with all currently-supported block textures.
"""

from overviewer_core import textures
import sys
import Image

if len(sys.argv) != 2:
    print "usage: %s [output.png]" % (sys.argv[0],)
    sys.exit(1)

t = textures.Textures()
t.generate()

blocks = {}

for blockid in xrange(textures.max_blockid):
    for data in xrange(textures.max_data):
        tex = t.blockmap[blockid * textures.max_data + data]
        if tex:
            if not blockid in blocks:
                blocks[blockid] = {}
            blocks[blockid][data] = tex

columns = max(map(len, blocks.values()))
rows = len(blocks)
texsize = t.texture_size

gallery = Image.new("RGBA", (columns * texsize, rows * texsize), t.bgcolor)

row = 0
for blockid, textures in blocks.iteritems():
    column = 0
    for data, tex in textures.iteritems():
        gallery.paste(tex[0], (column * texsize, row * texsize))
        column += 1
    row += 1

gallery.save(sys.argv[1])

########NEW FILE########
__FILENAME__ = playerInspect
"""
Very basic player.dat inspection script
"""

import sys, os

# incantation to be able to import overviewer_core
if not hasattr(sys, "frozen"):
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.split(__file__)[0], '..')))

from overviewer_core.nbt import load
from overviewer_core import items

def print_player(data, sub_entry=False):

    indent = ""
    if sub_entry:
        indent = "\t"
    print "%sPosition:\t%i, %i, %i\t(dim: %i)" % (indent,
            data['Pos'][0], data['Pos'][1], data['Pos'][2], data['Dimension'])
    try:
        print "%sSpawn:\t\t%i, %i, %i" % (indent,
                data['SpawnX'], data['SpawnY'], data['SpawnZ'])
    except KeyError:
        pass
    print "%sHealth:\t%i\tLevel:\t\t%i\t\tGameType:\t%i" % (indent,
            data['Health'], data['XpLevel'], data['playerGameType'])
    print "%sFood:\t%i\tTotal XP:\t%i" % (indent,
            data['foodLevel'], data['XpTotal'])
    print "%sInventory: %d items" % (indent, len(data['Inventory']))
    if not sub_entry:
        for item in data['Inventory']:
            print "  %-3d %s" % (item['Count'], items.id2item(item['id']))

if __name__ == '__main__':
    print "Inspecting %s" % sys.argv[1]

    if os.path.isdir(sys.argv[1]):
        directory = sys.argv[1]
        if len(sys.argv) > 2:
            selected_player = sys.argv[2]
        else:
            selected_player = None
        for player_file in os.listdir(directory):
            player = player_file.split(".")[0]
            if selected_player in [None, player]:
                print
                print player
                data  = load(os.path.join(directory, player_file))[1]
                print_player(data, sub_entry=(selected_player is None))
    else:
        data  = load(sys.argv[1])[1]
        print_player(data)


########NEW FILE########
__FILENAME__ = png-it
"""
Outputs a huge PNG file using the tiles from a overviewer map.
"""

from optparse import OptionParser
from PIL import Image
from os.path import join, split, exists
from glob import glob
import sys

def main():
    
    usage = 'usage: %prog [options] <tile-set-folder>'

    parser = OptionParser(description='',\
    prog = 'png_it', version='0.0.1', usage=usage)

    parser.add_option('--memory-limit', '-m', help = 'Limit the amount of ram to use in MB. If it\'s expected to exceed the limit it won\'t do anything.',\
        metavar = '<memory>', type = int, dest = 'memory_limit', default = None)
    
    parser.add_option('--zoom-level', '-z', help = 'Which zoom level to use from the overviewer map. NOTE: the RAM usage will increase exponentially with the zoom level.',\
        metavar = '<zoom-level>', type = int, dest = 'zoom_level', default = None)

    parser.add_option('--crop', '-c', help = 'It will crop a frame around the image, give it in percentage. For example in a image of 1000x2000 pixels, a 10% crop will crop 100 pixels in the left, right sides and 200 pixels in the bottom and top sides. NOTE: this is no exact, it will be rounded to the nearest overviewer map tile.',\
        metavar = '<crop>', type = int, dest = 'crop', default = 0)

    parser.add_option('--center', '-e', help = 'Mark what will be the center of the image, two percentage values comma separated',\
        metavar = '<center>', type = str, dest = 'center', default = None)

    parser.add_option('--autocrop', '-a', help = 'Calculates the center and crop vales automatically to show all the tiles in the minimun image size.Unless you want a very specific image this options is very recommendedable.',\
         action = 'store_true', dest = 'autocrop', default = False)

    parser.add_option('--output', '-o', help = 'Path for the resulting PNG. It will save it as PNG, no matter what extension do you use.',\
        metavar = '<output>', type = str, dest = 'output', default = "output.png")

    (options, args) = parser.parse_args()
    tileset = args[0]

    # arg is overviewer tile set folder
    if len(args) > 1:
        parser.error("Error! Only one overviewer tile set accepted as input. Use --help for a complete list of options.")

    if not args:
        parser.error("Error! Need an overviewer tile set folder. Use --help for a complete list of options.")
    
    if not options.zoom_level:
        parser.error("Error! The option zoom-level is mandatory.")
    
    if options.autocrop and (options.center or options.crop):
        parser.error("Error! You can't mix --autocrop with --center or --crop.")
    
    # check for the output
    folder, filename = split(options.output)
    if folder != '' and not exists(folder):
        parser.error("The destination folder \'{0}\' doesn't exist.".format(folder))
        
    # calculate stuff
    n = options.zoom_level
    length_in_tiles = 2**n
    tile_size = (384,384)
    px_size = 4 # bytes

    # create a list with all the images in the zoom level
    path = tileset
    for i in range(options.zoom_level):
        path = join(path, "?")
    path += ".png"
    
    all_images = glob(path)
    if not all_images:
        print "Error! No images found in this zoom level. Is this really an overviewer tile set directory?"
        sys.exit(1)

    # autocrop will calculate the center and crop values automagically
    if options.autocrop:
        min_x = min_y = length_in_tiles
        max_x = max_y = 0
        counter = 0
        total = len(all_images)
        print "Checking tiles for autocrop calculations:"
        # get the maximun and minimun tiles coordinates of the map
        for path in all_images:
            t = get_tuple_coords(options, path)
            c = get_tile_coords_from_tuple(options, t)
            min_x = min(min_x, c[0])
            min_y = min(min_y, c[1])
            max_x = max(max_x, c[0])
            max_y = max(max_y, c[1])
            counter += 1
            if (counter % 100 == 0 or counter == total or counter == 1): print "Checked {0} of {1}".format(counter, total)
        
        # the center of the map will be in the middle of the occupied zone
        center = (int((min_x + max_x)/2.), int((min_y + max_y)/2.))
        # see the next next comment to know what's center_vector
        center_vector = (int(center[0] - (length_in_tiles/2. - 1)), int(center[1] - (length_in_tiles/2. - 1)))
        # I'm not completely sure why, but the - 1 factor in  ^  makes everything nicer.
        
        # min_x - center_vector[0] will be the unused amount of tiles in
        # the left and the right of the map (and this is true because we
        # are in the actual center of the map)
        crop = (min_x - center_vector[0], min_y - center_vector[1])
        
    else:
        # center_vector is the vector that joins the center tile with
        # the new center tile in tile coords
        #(tile coords are how many tile are on the left, x, and 
        # how many above, y. The top-left tile has coords (0,0)
        if options.center:
            center_x, center_y = options.center.split(",")
            center_x = int(center_x)
            center_y = int(center_y)
            center_tile_x = int(2**n*(center_x/100.))
            center_tile_y = int(2**n*(center_y/100.))
            center_vector = (int(center_tile_x - length_in_tiles/2.), int(center_tile_y - length_in_tiles/2.))
        else:
            center_vector = (0,0)

        # crop if needed
        tiles_to_crop = int(2**n*(options.crop/100.))
        crop = (tiles_to_crop, tiles_to_crop)

    final_img_size = (tile_size[0]*length_in_tiles,tile_size[1]*length_in_tiles)
    final_cropped_img_size = (final_img_size[0] - 2*crop[0]*tile_size[0],final_img_size[1] - 2*crop[1]*tile_size[1])

    mem = final_cropped_img_size[0]*final_cropped_img_size[1]*px_size # bytes!
    print "The image size will be {0}x{1}".format(final_cropped_img_size[0],final_cropped_img_size[1])
    print "A total of {0} MB of memory will be used.".format(mem/1024**2)
    if mem/1024.**2. > options.memory_limit:
        print "Warning! The expected RAM usage exceeds the spicifyed limit. Exiting."
        sys.exit(1)

    # Create a new huge image
    final_img = Image.new("RGBA", final_cropped_img_size, (26, 26, 26, 0))

    # Paste ALL the images
    total = len(all_images)
    counter = 0
    print "Pasting images:"
    for path in all_images:
        
        img = Image.open(path)
        t = get_tuple_coords(options, path)
        x, y = get_cropped_centered_img_coords(options, tile_size, center_vector, crop, t)
        final_img.paste(img, (x, y))
        counter += 1
        if (counter % 100 == 0 or counter == total or counter == 1): print "Pasted {0} of {1}".format(counter, total)
    print "Done!"
    print "Saving image... (this can take a while)"
    final_img.save(options.output, "PNG")


def get_cropped_centered_img_coords(options, tile_size, center_vector, crop, t):
    """ Returns the new image coords used to paste tiles in the big 
    image. Takes options, the size of tiles, center vector, crop value 
    (see calculate stuff) and a tuple from get_tuple_coords. """
    x, y = get_tile_coords_from_tuple(options, t)
    new_tile_x = x - crop[0] - center_vector[0]
    new_tile_y = y - crop[1] - center_vector[1]
    
    new_img_x = new_tile_x*tile_size[0]
    new_img_y = new_tile_y*tile_size[1]
    
    return new_img_x, new_img_y

def get_tile_coords_from_tuple(options, t):
    """ Gets a tuple of coords from get_tuple_coords and returns 
    the number of tiles from the top left corner to this tile.
    The top-left tile has coordinates (0,0) """
    x = 0
    y = 0
    z = options.zoom_level
    n = 1
    
    for i in t:
        if i == 1:
            x += 2**(z-n)
        elif i == 2:
            y += 2**(z-n)
        elif i == 3:
            x += 2**(z-n)
            y += 2**(z-n)
        n += 1
    return (x,y)

def get_tuple_coords(options, path):
    """ Extracts the "quadtree coordinates" (the numbers in the folder
    of the tile sets) from an image path. Returns a tuple with them.
    The upper most folder is in the left of the tuple."""
    l = []
    path, head = split(path)
    head = head.split(".")[0] # remove the .png
    l.append(int(head))
    for i in range(options.zoom_level - 1):
        path, head = split(path)
        l.append(int(head))
    # the list is reversed
    l.reverse()
    return tuple(l)

def get_image(tileset, t):
    """ Returns the path of an image, takes a tuple with the 
    "quadtree coordinates", these are the numbers in the folders of the
    tile set. """
    path = tileset
    for d in t:
        path = join(path, str(d))
    path += ".png"
    return path

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = regionTrimmer
#!/usr/bin/env python

"""Deletes outlying and unconnected regions"""

import logging
import os
import sys
import glob

import networkx

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

def get_region_file_from_node(regionset_path, node):
    return os.path.join(regionset_path, 'r.%d.%d.mca' % node)

def get_nodes(regionset_path):
    return [tuple(map(int, r.split('.')[1:3])) \
        for r in glob.glob(os.path.join(regionset_path, 'r.*.*.mca'))]

def generate_edges(graph):
    offsets = (-1, 1)
    nodes = graph.nodes()
    for node in nodes:
        for offset in offsets:
            graph.add_edges_from((node, offset_node) for offset_node in \
                [(node[0] + offset, node[1]), (node[0], node[1] + offset), \
                    (node[0] + offset, node[1] + offset)] \
                if offset_node in nodes)
    return graph

def generate_subgraphs(nodes):
    graph = networkx.Graph()
    graph.add_nodes_from(nodes)
    generate_edges(graph)
    return graph, networkx.connected_component_subgraphs(graph)

def get_graph_bounds(graph):
    nodes = graph.nodes()
    return (
        max(n[0] for n in nodes),
        min(n[0] for n in nodes),
        max(n[1] for n in nodes),
        min(n[1] for n in nodes),
    )

def get_graph_center_by_bounds(bounds):
    dx = bounds[0] - bounds[1]
    dy = bounds[2] - bounds[3]
    return (dx / 2 + bounds[1], dy / 2 + bounds[3])

def main(*args, **options):
    if len(args) < 1:
        logger.error('Missing region directory argument')
        return
    for path in args:
        logger.info('Using regionset path: %s', path)
        nodes = get_nodes(path)
        if not len(nodes):
            logger.error('Found no nodes, are you sure there are .mca files in %s ?',
                path)
            return
        logger.info('Found %d nodes', len(nodes))
        logger.info('Generating graphing nodes...')
        graph, subgraphs = generate_subgraphs(nodes)
        assert len(graph.nodes()) == sum(len(sg.nodes()) for sg in subgraphs)
        if len(subgraphs) == 1:
            logger.warn('All regions are contiguous, the needful is done!')
            return
        logger.info('Found %d discrete region sections', len(subgraphs))
        subgraphs = sorted(subgraphs, key=lambda sg: len(sg), reverse=True)
        for i, sg in enumerate(subgraphs):
            logger.info('Region section #%02d: %04d nodes', i+1, len(sg.nodes()))
            bounds = get_graph_bounds(sg)
            logger.info('Bounds: %d <-> %d x %d <-> %d', *get_graph_bounds(sg))
            center = get_graph_center_by_bounds(bounds)
            logger.info('Center: %d x %d', *center)

        main_section = subgraphs[0]
        main_section_bounds = get_graph_bounds(main_section)
        main_section_center = get_graph_center_by_bounds(main_section_bounds)
        logger.info('Using %d node graph as main section,', len(main_section.nodes()))
        satellite_sections = subgraphs[1:]
        for ss in satellite_sections:
            bounds = get_graph_bounds(ss)
            center = get_graph_center_by_bounds(bounds)
            logger.info('Checking satellite section with %d nodes, %d <-> %d x %d <-> %d bounds and %d x %d center',
                len(ss.nodes()), *(bounds + center))
            if options['trim_disconnected']:
                logger.info('Trimming regions: %s', ', '.join(
                    get_region_file_from_node(path, n) for n in ss.nodes()))
                for n, region_file in ((n, get_region_file_from_node(path, n)) \
                    for n in ss.nodes()):
                        ss.remove_node(n)
                        if not options['dry_run']:
                            unlink_file(region_file)
            if options['trim_outside_main']:
                if center[0] <= main_section_bounds[0] and center[0] >= main_section_bounds[1] and \
                        center[1] <= main_section_bounds[2] and center[1] >= main_section_bounds[3]:
                    logger.info('Section falls inside main section bounds, ignoring')
                else:
                    logger.info('Section is outside main section bounds')
                    logger.info('Trimming regions: %s', ', '.join(
                        get_region_file_from_node(path, n) for n in ss.nodes()))
                    for n, region_file in ((n, get_region_file_from_node(path, n)) \
                        for n in ss.nodes()):
                            ss.remove_node(n)
                            if not options['dry_run']:
                                unlink_file(region_file)
            if options['trim_outside_bounds']:
                x = map(int, options['trim_outside_bounds'].split(','))
                if len(x) == 4:
                    trim_center = x[:2]
                    trim_bounds = x[2:]
                elif len(x) == 2:
                    trim_center = main_section_center
                    trim_bounds = x
                else:
                    logger.error('Invalid center/bound value: %s',
                        options['trim_outside_bounds'])
                    continue
                for node in ss.nodes():
                    if node[0] >= trim_center[0] + trim_bounds[0] or \
                            node[0] <= trim_center[0] - trim_bounds[0] or \
                            node[1] >= trim_center[1] + trim_bounds[1] or \
                            node[1] <= trim_center[1] - trim_bounds[1]:
                        region_file = get_region_file_from_node(path, node)
                        logger.info('Region falls outside specified bounds, trimming: %s',
                            region_file)
                        ss.remove_node(node)
                        if not options['dry_run']:
                            unlink_file(region_file)

def unlink_file(path):
    try:
        os.unlink(path)
    except OSError as err:
        logger.warn('Unable to delete file: %s', path)
        logger.warn('Error recieved was: %s', err)


if __name__ == '__main__':
    import optparse
    logging.basicConfig()
    parser = optparse.OptionParser(
        usage='Usage: %prog [options] <path/to/region/directory>')
    parser.add_option('-D', '--trim-disconnected', action='store_true', default=False,
        help='Trim all disconnected regions')
    parser.add_option('-M', '--trim-outside-main', action='store_true', default=False,
        help='Trim disconnected regions outside main section bounds')
    parser.add_option('-B', '--trim-outside-bounds', default=False,
        metavar='[center_X,center_Y,]bound_X,bound_Y',
        help='Trim outside given bounds (given as [center_X,center_Y,]bound_X,bound_Y)')
    parser.add_option('-n', '--dry-run', action='store_true', default=False,
        help='Don\'t actually delete anything')
    opts, args = parser.parse_args()
    main(*args, **vars(opts))

########NEW FILE########
__FILENAME__ = rerenderBlocks
#!/usr/bin/python

'''
Generate a region list to rerender certain chunks

This is used to force the regeneration of any chunks that contain a certain
blockID.  The output is a chunklist file that is suitable to use with the
--chunklist option to overviewer.py.

Example:

python contrib/rerenderBlocks.py --ids=46,79,91 --world=world/> regionlist.txt
    python overviewer.py --regionlist=regionlist.txt world/ output_dir/

This will rerender any chunks that contain either TNT (46), Ice (79), or 
a Jack-O-Lantern (91)
'''

from optparse import OptionParser
import sys,os
import re

# incantation to be able to import overviewer_core
if not hasattr(sys, "frozen"):
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.split(__file__)[0], '..')))

from overviewer_core import nbt
from overviewer_core import world
from overviewer_core.chunk import get_blockarray

parser = OptionParser()
parser.add_option("--ids", dest="ids", type="string")
parser.add_option("--world", dest="world", type="string")


options, args = parser.parse_args()

if not options.world or not options.ids:
    parser.print_help()
    sys.exit(1)

if not os.path.exists(options.world):
    raise Exception("%s does not exist" % options.world)

ids = map(lambda x: int(x),options.ids.split(","))
sys.stderr.write("Searching for these blocks: %r...\n" % ids)


matcher = re.compile(r"^r\..*\.mcr$")

for dirpath, dirnames, filenames in os.walk(options.world):
    for f in filenames:
        if matcher.match(f):
            full = os.path.join(dirpath, f)
            r = nbt.load_region(full, 'lower-left')
            chunks = r.get_chunks()
            found = False
            for x,y in chunks:
                chunk = r.load_chunk(x,y).read_all()                
                blocks = get_blockarray(chunk[1]['Level'])
                for i in ids:
                    if chr(i) in blocks:
                        print full
                        found = True
                        break
                if found:
                    break



########NEW FILE########
__FILENAME__ = testRender
#!/usr/bin/python

"Test Render Script"

import os, shutil, tempfile, time, sys, math, re
from subprocess import Popen, PIPE, STDOUT, CalledProcessError
from optparse import OptionParser

overviewer_scripts = ['./overviewer.py', './gmap.py']

def check_call(*args, **kwargs):
    quiet = False
    if "quiet" in kwargs.keys():
        quiet = kwargs["quiet"]
        del kwargs["quiet"]
    if quiet:
        kwargs['stdout'] = PIPE
        kwargs['stderr'] = STDOUT
    p = Popen(*args, **kwargs)
    output = ""
    if quiet:
        while p.poll() == None:
            output += p.communicate()[0]
    returncode = p.wait()
    if returncode:
        if quiet:
            print output
        raise CalledProcessError(returncode, args)
    return returncode

def check_output(*args, **kwargs):
    kwargs['stdout'] = PIPE
    # will hang for HUGE output... you were warned
    p = Popen(*args, **kwargs)
    returncode = p.wait()
    if returncode:
        raise CalledProcessError(returncode, args)
    return p.communicate()[0]

def clean_render(overviewerargs, quiet):
    tempdir = tempfile.mkdtemp('mc-overviewer-test')
    overviewer_script = None
    for script in overviewer_scripts:
        if os.path.exists(script):
            overviewer_script = script
            break
    if overviewer_script is None:
        sys.stderr.write("could not find main overviewer script\n")
        sys.exit(1)
        
    try:
        # check_call raises CalledProcessError when overviewer.py exits badly
        check_call([sys.executable, 'setup.py', 'clean', 'build'], quiet=quiet)
        try:
            check_call([sys.executable, overviewer_script, '-d'] + overviewerargs, quiet=quiet)
        except CalledProcessError:
            pass
        starttime = time.time()
        check_call([sys.executable, overviewer_script,] + overviewerargs + [tempdir,], quiet=quiet)
        endtime = time.time()
        
        return endtime - starttime
    finally:
        shutil.rmtree(tempdir, True)

def get_stats(timelist):
    stats = {}
    
    stats['count'] = len(timelist)
    stats['minimum'] = min(timelist)
    stats['maximum'] = max(timelist)
    stats['average'] = sum(timelist) / float(len(timelist))
    
    meandiff = map(lambda x: (x - stats['average'])**2, timelist)
    stats['standard deviation'] = math.sqrt(sum(meandiff) / float(len(meandiff)))
    
    return stats

commitre = re.compile('^commit ([a-z0-9]{40})$', re.MULTILINE)
branchre = re.compile('^\\* (.+)$', re.MULTILINE)
def get_current_commit():
    gittext = check_output(['git', 'branch'])
    match = branchre.search(gittext)
    if match and not ("no branch" in match.group(1)):
        return match.group(1)
    gittext = check_output(['git', 'show', 'HEAD'])
    match = commitre.match(gittext)
    if match == None:
        return None
    return match.group(1)

def get_commits(gitrange):
    gittext = check_output(['git', 'log', '--raw', '--reverse', gitrange])
    for match in commitre.finditer(gittext):
        yield match.group(1)

def set_commit(commit):
    check_call(['git', 'checkout', commit], quiet=True)

parser = OptionParser(usage="usage: %prog [options] -- [overviewer options/world]")
parser.add_option("-n", "--number", metavar="N",
                  action="store", type="int", dest="number", default=3,
                  help="number of renders per commit [default: 3]")
parser.add_option("-c", "--commits", metavar="RANGE",
                  action="append", type="string", dest="commits", default=[],
                  help="the commit (or range of commits) to test [default: current]")
parser.add_option("-v", "--verbose",
                  action="store_false", dest="quiet", default=True,
                  help="don't suppress overviewer output")
parser.add_option("-k", "--keep-going",
                  action="store_false", dest="fatal_errors", default=True,
                  help="don't stop testing when Overviewer croaks")
parser.add_option("-l", "--log", dest="log", default="", metavar="FILE",
                  help="log all test results to a file")

(options, args) = parser.parse_args()

if len(args) == 0:
    parser.print_help()
    sys.exit(0)

commits = []
for commit in options.commits:
    if '..' in commit:
        commits = get_commits(commit)
    else:
        commits.append(commit)
if not commits:
    commits = [get_current_commit(),]

log = None
if options.log != "":
    log = open(options.log, "w")

reset_commit = get_current_commit()
try:
    for commit in commits:
        print "testing commit", commit
        set_commit(commit)
        timelist = []
        print " -- ",
        try:
            for i in range(options.number):
                sys.stdout.write(str(i+1)+" ")
                sys.stdout.flush()
                timelist.append(clean_render(args, options.quiet))
            print "... done"
            stats = get_stats(timelist)
            print stats
            if log:
                log.write("%s %s\n" % (commit, repr(stats)))
        except CalledProcessError, e:
            if options.fatal_errors:
                print
                print "Overviewer croaked, exiting..."
                print "(to avoid this, use --keep-going)"
                sys.exit(1)
finally:
    set_commit(reset_commit)
    if log:
        log.close()

########NEW FILE########
__FILENAME__ = validateRegionFile
#!/usr/bin/env python

'''
Validate a region file

TODO description here'''

import os
import sys

# incantation to be able to import overviewer_core
if not hasattr(sys, "frozen"):
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.split(__file__)[0], '..')))

from overviewer_core import nbt

def check_region(region_filename):
    chunk_errors = []
    if not os.path.exists(region_filename):
        raise Exception('Region file not found: %s' % region_filename)
    try:
        region = nbt.load_region(region_filename, 'lower-left')
    except IOError, e:
        raise Exception('Error loading region (%s): %s' % (region_filename, e))
    try:
        region.get_chunk_info(False)
        chunks = region.get_chunks()
    except IOError, e:
        raise Exception('Error reading region header (%s): %s' % (region_filename, e))
    except Exception, e:
        raise Exception('Error reading region (%s): %s' % (region_filename, e))
    for x,y in chunks:
        try:
            check_chunk(region, x, y)
        except Exception, e:
            chunk_errors.append(e)
    return (chunk_errors, len(chunks))
    
def check_chunk(region, x, y):
    try:
        data = region.load_chunk(x ,y)
    except Exception, e:
        raise Exception('Error reading chunk (%i, %i): %s' % (x, y, e))
    if data is None:
        raise Exception('Chunk (%i, %i) is unexpectedly empty' % (x, y))
    else:
        try:
            processed_data = data.read_all()
        except Exception, e:
            raise Exception('Error reading chunk (%i, %i) data: %s' % (x, y, e))
        if processed_data == []:
            raise Exception('Chunk (%i, %i) is an unexpectedly empty set' % (x, y))

if __name__ == '__main__':
    try:
        from optparse import OptionParser

        parser = OptionParser(usage='python contrib/%prog [OPTIONS] <path/to/regions|path/to/regions/*.mcr|regionfile1.mcr regionfile2.mcr ...>',
                              description='This script will valide a minecraft region file for errors.')
        parser.add_option('-v', dest='verbose', action='store_true', help='Print additional information.')
        opts, args = parser.parse_args()
        
        region_files = []
        for path in args:
            if os.path.isdir(path):
                for dirpath, dirnames, filenames in os.walk(path, True):
                    for filename in filenames:
                        if filename.startswith('r.') and filename.endswith('.mcr'):
                            if filename not in region_files:
                                region_files.append(os.path.join(dirpath, filename))
                        elif opts.verbose:
                            print('Ignoring non-region file: %s' % os.path.join(dirpath, filename))
            elif os.path.isfile(path):
                dirpath,filename = os.path.split(path)
                if filename.startswith('r.') and filename.endswith('.mcr'):
                    if path not in region_files:
                        region_files.append(path)
                else:
                    print('Ignoring non-region file: %s' % path)
            else:
                if opts.verbose:
                    print('Ignoring arg: %s' % path)
        if len(region_files) < 1:
            print 'You must list at least one region file.'
            parser.print_help()
            sys.exit(1)
        else:
            overall_chunk_total = 0
            bad_chunk_total = 0
            bad_region_total = 0
            for region_file in region_files:
                try:
                    (chunk_errors, region_chunks) = check_region(region_file)
                    bad_chunk_total += len(chunk_errors)
                    overall_chunk_total += region_chunks
                except Exception, e:
                    bad_region_total += 1
                    print('FAILED(%s): %s' % (region_file, e))
                else:
                    if len(chunk_errors) is not 0:
                        print('WARNING(%s) Chunks: %i/%' % (region_file, region_chunks - len(chunk_errors), region_chunks))
                        if opts.verbose:
                            for error in chunk_errors:
                                print(error)
                    elif opts.verbose:
                            print ('PASSED(%s) Chunks: %i/%i' % (region_file, region_chunks - len(chunk_errors), region_chunks))
            if opts.verbose:
                print 'REGIONS: %i/%i' % (len(region_files) - bad_region_total, len(region_files))
                print 'CHUNKS: %i/%i' % (overall_chunk_total - bad_chunk_total, overall_chunk_total)
    except KeyboardInterrupt:
        sys.exit(1)
    except Exception, e:
        print('ERROR: %s' % e)


########NEW FILE########
__FILENAME__ = contribManager
#!/usr/bin/env python

# The contrib manager is used to help control the contribs script 
# that are shipped with overviewer in Windows packages

import sys
import os.path
import ast

# incantation to be able to import overviewer_core
if not hasattr(sys, "frozen"):
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.split(__file__)[0], '.')))

from overviewer_core import nbt

scripts=dict( # keys are names, values are scripts
        clearOldCache   = "clearOldCache.py",
        convertCyrillic = "cyrillic_convert.py",
        findSigns       = "findSigns.py",
        playerInspect   = "playerInspect.py",
        rerenderBlocks  = "rerenderBlocks.py",
        testRender      = "testRender.py",
        validate        = "validateRegionFile.py",
        pngit           = "png-it.py",
        gallery         = "gallery.py",
        regionTrimmer   = "regionTrimmer.py",
        contributors    = "contributors.py"
        )

# you can symlink or hardlink contribManager.py to another name to have it
# automatically find the right script to run.  For example:
# > ln -s contribManager.py validate.exe
# > chmod +x validate.exe
# > ./validate.exe -h


# figure out what script to execute
argv=os.path.basename(sys.argv[0])

if argv[-4:] == ".exe":
    argv=argv[0:-4]
if argv[-3:] == ".py":
    argv=argv[0:-3]


usage="""Usage:
%s --list-contribs | <script name> <arguments>

Executes a contrib script.  

Options:
  --list-contribs           Lists the supported contrib scripts

""" % os.path.basename(sys.argv[0])

if argv in scripts.keys():
    script = scripts[argv]
    sys.argv[0] = script
else:
    if "--list-contribs" in sys.argv:
        for contrib in scripts.keys():
            # use an AST to extract the docstring for this module
            script = scripts[contrib]
            with open(os.path.join("contrib",script)) as f:
                d = f.read()
            node=ast.parse(d, script);
            docstring = ast.get_docstring(node)
            if docstring:
                docstring = docstring.strip().splitlines()[0]
            else:
                docstring="(no description found.  add one by adding a docstring to %s)" % script
            print "%s : %s" % (contrib, docstring)
        sys.exit(0)
    if len(sys.argv) > 1 and sys.argv[1] in scripts.keys():
        script = scripts[sys.argv[1]]
        sys.argv = [script] + sys.argv[2:]
    else:
        print usage
        sys.exit(1)


torun = os.path.join("contrib", script)

if not os.path.exists(torun):
    print "Script '%s' is missing!" % script
    sys.exit(1)

execfile(torun)


########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# Overviewer documentation build configuration file, created by
# sphinx-quickstart on Thu Sep 22 10:19:03 2011.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys, os

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
sys.path.insert(0, os.path.abspath('..'))

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'Overviewer'
copyright = u'2010-2012 The Overviewer Team'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = "0.10"
# The full version, including alpha/beta/rc tags.
release = "0.10"

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = ['_build']

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

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
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
html_static_path = ['_static']

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
#html_domain_indices = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
#html_show_sourcelink = True

# If true, "Created using Sphinx" is shown in the HTML footer. Default is True.
#html_show_sphinx = True

# If true, "(C) Copyright ..." is shown in the HTML footer. Default is True.
#html_show_copyright = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# This is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = None

# Output file base name for HTML help builder.
htmlhelp_basename = 'Overviewerdoc'


# -- Options for LaTeX output --------------------------------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'Overviewer.tex', u'Overviewer Documentation',
   u'The Overviewer Team', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# If true, show page references after internal links.
#latex_show_pagerefs = False

# If true, show URL addresses after external links.
#latex_show_urls = False

# Additional stuff for the LaTeX preamble.
#latex_preamble = ''

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_domain_indices = True


# -- Options for manual page output --------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'overviewer', u'Overviewer Documentation',
     [u'The Overviewer Team'], 1)
]

########NEW FILE########
__FILENAME__ = overviewer
#!/usr/bin/env python

#    This file is part of the Minecraft Overviewer.
#
#    Minecraft Overviewer is free software: you can redistribute it and/or
#    modify it under the terms of the GNU General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or (at
#    your option) any later version.
#
#    Minecraft Overviewer is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General
#    Public License for more details.
#
#    You should have received a copy of the GNU General Public License along
#    with the Overviewer.  If not, see <http://www.gnu.org/licenses/>.

import platform
import sys

# quick version check
if not (sys.version_info[0] == 2 and sys.version_info[1] >= 6):
    print("Sorry, the Overviewer requires at least Python 2.6 to run")
    if sys.version_info[0] >= 3:
        print("and will not run on Python 3.0 or later")
    sys.exit(1)

import os
import os.path
import re
import subprocess
import multiprocessing
import time
import logging
from optparse import OptionParser, OptionGroup

from overviewer_core import util
from overviewer_core import logger
from overviewer_core import textures
from overviewer_core import optimizeimages, world
from overviewer_core import configParser, tileset, assetmanager, dispatcher
from overviewer_core import cache
from overviewer_core import observer

helptext = """
%prog [--rendermodes=...] [options] <World> <Output Dir>
%prog --config=<config file> [options]"""

def main():
    # bootstrap the logger with defaults
    logger.configure()

    try:
        cpus = multiprocessing.cpu_count()
    except NotImplementedError:
        cpus = 1

    #avail_rendermodes = c_overviewer.get_render_modes()
    avail_north_dirs = ['lower-left', 'upper-left', 'upper-right', 'lower-right', 'auto']

    # Parse for basic options
    parser = OptionParser(usage=helptext, add_help_option=False)
    parser.add_option("-h", "--help", dest="help", action="store_true",
            help="show this help message and exit")
    parser.add_option("-c", "--config", dest="config", action="store", help="Specify the config file to use.")
    parser.add_option("-p", "--processes", dest="procs", action="store", type="int",
            help="The number of local worker processes to spawn. Defaults to the number of CPU cores your computer has")

    parser.add_option("--pid", dest="pid", action="store", help="Specify the pid file to use.")
    # Options that only apply to the config-less render usage
    parser.add_option("--rendermodes", dest="rendermodes", action="store",
            help="If you're not using a config file, specify which rendermodes to render with this option. This is a comma-separated list.")

    # Useful one-time render modifiers:
    parser.add_option("--forcerender", dest="forcerender", action="store_true",
            help="Force re-rendering the entire map.")
    parser.add_option("--check-tiles", dest="checktiles", action="store_true",
            help="Check each tile on disk and re-render old tiles")
    parser.add_option("--no-tile-checks", dest="notilechecks", action="store_true",
            help="Only render tiles that come from chunks that have changed since the last render (the default)")

    # Useful one-time debugging options:
    parser.add_option("--check-terrain", dest="check_terrain", action="store_true",
            help="Tries to locate the texture files. Useful for debugging texture problems.")
    parser.add_option("-V", "--version", dest="version",
            help="Displays version information and then exits", action="store_true")
    parser.add_option("--check-version", dest="checkversion",
            help="Fetchs information about the latest version of Overviewer", action="store_true")
    parser.add_option("--update-web-assets", dest='update_web_assets', action="store_true",
            help="Update web assets. Will *not* render tiles or update overviewerConfig.js")

    # Log level options:
    parser.add_option("-q", "--quiet", dest="quiet", action="count", default=0,
            help="Print less output. You can specify this option multiple times.")
    parser.add_option("-v", "--verbose", dest="verbose", action="count", default=0,
            help="Print more output. You can specify this option multiple times.")
    parser.add_option("--simple-output", dest="simple", action="store_true", default=False,
            help="Use a simple output format, with no colors or progress bars")

    # create a group for "plugin exes" (the concept of a plugin exe is only loosly defined at this point)
    exegroup = OptionGroup(parser, "Other Scripts",
            "These scripts may accept different arguments than the ones listed above")
    exegroup.add_option("--genpoi", dest="genpoi", action="store_true",
            help="Runs the genPOI script")
    exegroup.add_option("--skip-scan", dest="skipscan", action="store_true",
            help="When running GenPOI, don't scan for entities")

    parser.add_option_group(exegroup)

    options, args = parser.parse_args()

    # first thing to do is check for stuff in the exegroup:
    if options.genpoi:
        # remove the "--genpoi" option from sys.argv before running genPI
        sys.argv.remove("--genpoi")
        #sys.path.append(".")
        g = __import__("overviewer_core.aux_files", {}, {}, ["genPOI"])
        g.genPOI.main()
        return 0
    if options.help:
        parser.print_help()
        return 0

    # re-configure the logger now that we've processed the command line options
    logger.configure(logging.INFO + 10*options.quiet - 10*options.verbose,
                     verbose=options.verbose > 0,
                     simple=options.simple)

    ##########################################################################
    # This section of main() runs in response to any one-time options we have,
    # such as -V for version reporting
    if options.version:
        print("Minecraft Overviewer %s" % util.findGitVersion()),
        print("(%s)" % util.findGitHash()[:7])
        try:
            import overviewer_core.overviewer_version as overviewer_version
            print("built on %s" % overviewer_version.BUILD_DATE)
            if options.verbose > 0:
                print("Build machine: %s %s" % (overviewer_version.BUILD_PLATFORM, overviewer_version.BUILD_OS))
                print("Read version information from %r"% overviewer_version.__file__)
        except ImportError:
            print("(build info not found)")
        if options.verbose > 0:
            print("Python executable: %r" % sys.executable)
            print(sys.version)
        if not options.checkversion:
            return 0
    if options.checkversion:
        print("Currently running Minecraft Overviewer %s" % util.findGitVersion()),
        print("(%s)" % util.findGitHash()[:7])
        try:
            import urllib
            import json
            latest_ver = json.loads(urllib.urlopen("http://overviewer.org/download.json").read())['src']
            print("Latest version of Minecraft Overviewer %s (%s)" % (latest_ver['version'], latest_ver['commit'][:7]))
            print("See http://overviewer.org/downloads for more information")
        except Exception:
            print("Failed to fetch latest version info.")
            if options.verbose > 0:
                import traceback
                traceback.print_exc()
            else:
                print("Re-run with --verbose for more details")
            return 1
        return 0


    if options.pid:
        if os.path.exists(options.pid):
            try:
                with open(options.pid, 'r') as fpid:
                    pid = int(fpid.read())
                    if util.pid_exists(pid):
                        print("Already running (pid exists) - exiting..")
                        return 0
            except (IOError, ValueError):
                pass
        with open(options.pid,"w") as f:
            f.write(str(os.getpid()))
    # if --check-terrain was specified, but we have NO config file, then we cannot
    # operate on a custom texture path.  we do terrain checking with a custom texture
    # pack later on, after we've parsed the config file
    if options.check_terrain and not options.config:
        import hashlib
        from overviewer_core.textures import Textures
        tex = Textures()

        logging.info("Looking for a few common texture files...")
        try:
            f = tex.find_file("assets/minecraft/textures/blocks/sandstone_top.png", verbose=True)
            f = tex.find_file("assets/minecraft/textures/blocks/grass_top.png", verbose=True)
            f = tex.find_file("assets/minecraft/textures/blocks/diamond_ore.png", verbose=True)
            f = tex.find_file("assets/minecraft/textures/blocks/planks_acacia.png", verbose=True)
        except IOError:
            logging.error("Could not find any texture files.")
            return 1

        return 0

    # if no arguments are provided, print out a helpful message
    if len(args) == 0 and not options.config:
        # first provide an appropriate error for bare-console users
        # that don't provide any options
        if util.is_bare_console():
            print("\n")
            print("The Overviewer is a console program.  Please open a Windows command prompt")
            print("first and run Overviewer from there.   Further documentation is available at")
            print("http://docs.overviewer.org/\n")
            print("\n")
            print("For a quick-start guide on Windows, visit the following URL:\n")
            print("http://docs.overviewer.org/en/latest/win_tut/windowsguide/\n")

        else:
            # more helpful message for users who know what they're doing
            logging.error("You must either specify --config or give me a world directory and output directory")
            parser.print_help()
            list_worlds()
        return 1

    ##########################################################################
    # This section does some sanity checking on the command line options passed
    # in. It checks to see if --config was given that no worldname/destdir were
    # given, and vice versa
    if options.config and args:
        print()
        print("If you specify --config, you need to specify the world to render as well as")
        print("the destination in the config file, not on the command line.")
        print("Put something like this in your config file:")
        print("worlds['myworld'] = %r" % args[0])
        print("outputdir = %r" % (args[1] if len(args) > 1 else "/path/to/output"))
        print()
        logging.error("Cannot specify both --config AND a world + output directory on the command line.")
        parser.print_help()
        return 1

    if not options.config and len(args) < 2:
        logging.error("You must specify both the world directory and an output directory")
        parser.print_help()
        return 1
    if not options.config and len(args) > 2:
        # it's possible the user has a space in one of their paths but didn't
        # properly escape it attempt to detect this case
        for start in range(len(args)):
            if not os.path.exists(args[start]):
                for end in range(start+1, len(args)+1):
                    if os.path.exists(" ".join(args[start:end])):
                        logging.warning("It looks like you meant to specify \"%s\" as your world dir or your output\n\
dir but you forgot to put quotes around the directory, since it contains spaces." % " ".join(args[start:end]))
                        return 1
        logging.error("Too many command line arguments")
        parser.print_help()
        return 1

    #########################################################################
    # These two halfs of this if statement unify config-file mode and
    # command-line mode.
    mw_parser = configParser.MultiWorldParser()

    if not options.config:
        # No config file mode.
        worldpath, destdir = map(os.path.expanduser, args)
        logging.debug("Using %r as the world directory", worldpath)
        logging.debug("Using %r as the output directory", destdir)

        mw_parser.set_config_item("worlds", {'world': worldpath})
        mw_parser.set_config_item("outputdir", destdir)

        rendermodes = ['lighting']
        if options.rendermodes:
            rendermodes = options.rendermodes.replace("-","_").split(",")

        # Now for some good defaults
        renders = util.OrderedDict()
        for rm in rendermodes:
            renders["world-" + rm] = {
                    "world": "world",
                    "title": "Overviewer Render (%s)" % rm,
                    "rendermode": rm,
                    }
        mw_parser.set_config_item("renders", renders)

    else:
        if options.rendermodes:
            logging.error("You cannot specify --rendermodes if you give a config file. Configure your rendermodes in the config file instead")
            parser.print_help()
            return 1

        # Parse the config file
        try:
            mw_parser.parse(os.path.expanduser(options.config))
        except configParser.MissingConfigException as e:
            # this isn't a "bug", so don't print scary traceback
            logging.error(str(e))
            util.nice_exit(1)

    # Add in the command options here, perhaps overriding values specified in
    # the config
    if options.procs:
        mw_parser.set_config_item("processes", options.procs)

    # Now parse and return the validated config
    try:
        config = mw_parser.get_validated_config()
    except Exception as ex:
        if options.verbose:
            logging.exception("An error was encountered with your configuration. See the info below.")
        else: # no need to print scary traceback! just
            logging.error("An error was encountered with your configuration.")
            logging.error(str(ex))
        return 1

    if options.check_terrain: # we are already in the "if configfile" branch
        logging.info("Looking for a few common texture files...")
        for render_name, render in config['renders'].iteritems():
            logging.info("Looking at render %r", render_name)

            # find or create the textures object
            texopts = util.dict_subset(render, ["texturepath"])

            tex = textures.Textures(**texopts)
            f = tex.find_file("assets/minecraft/textures/blocks/sandstone_top.png", verbose=True)
            f = tex.find_file("assets/minecraft/textures/blocks/grass_top.png", verbose=True)
            f = tex.find_file("assets/minecraft/textures/blocks/diamond_ore.png", verbose=True)
            f = tex.find_file("assets/minecraft/textures/blocks/planks_oak.png", verbose=True)
        return 0

    ############################################################
    # Final validation steps and creation of the destination directory
    logging.info("Welcome to Minecraft Overviewer!")
    logging.debug("Current log level: {0}".format(logging.getLogger().level))

    # Override some render configdict options depending on one-time command line
    # modifiers
    if (
            bool(options.forcerender) +
            bool(options.checktiles) +
            bool(options.notilechecks)
            ) > 1:
        logging.error("You cannot specify more than one of --forcerender, "+
        "--check-tiles, and --no-tile-checks. These options conflict.")
        parser.print_help()
        return 1

    def set_renderchecks(checkname, num):
        for name, render in config['renders'].iteritems():
            if render.get('renderchecks', 0) == 3:
                logging.warning(checkname + " ignoring render " + repr(name) + " since it's marked as \"don't render\".")
            else:
                render['renderchecks'] = num
        
    if options.forcerender:
        logging.info("Forcerender mode activated. ALL tiles will be rendered")
        set_renderchecks("forcerender", 2)
    elif options.checktiles:
        logging.info("Checking all tiles for updates manually.")
        set_renderchecks("checktiles", 1)
    elif options.notilechecks:
        logging.info("Disabling all tile mtime checks. Only rendering tiles "+
        "that need updating since last render")
        set_renderchecks("notilechecks", 0)

    if not config['renders']:
        logging.error("You must specify at least one render in your config file. See the docs if you're having trouble")
        return 1

    #####################
    # Do a few last minute things to each render dictionary here
    for rname, render in config['renders'].iteritems():
        # Convert render['world'] to the world path, and store the original
        # in render['worldname_orig']
        try:
            worldpath = config['worlds'][render['world']]
        except KeyError:
            logging.error("Render %s's world is '%s', but I could not find a corresponding entry in the worlds dictionary.",
                    rname, render['world'])
            return 1
        render['worldname_orig'] = render['world']
        render['world'] = worldpath

        # If 'forcerender' is set, change renderchecks to 2
        if render.get('forcerender', False):
            render['renderchecks'] = 2

        # check if overlays are set, if so, make sure that those renders exist
        if render.get('overlay', []) != []:
            for x in render.get('overlay'):
                if x != rname:
                    try:
                        renderLink = config['renders'][x]
                    except KeyError:
                        logging.error("Render %s's overlay is '%s', but I could not find a corresponding entry in the renders dictionary.",
                                rname, x)
                        return 1
                else:
                    logging.error("Render %s's overlay contains itself.", rname)
                    return 1

    destdir = config['outputdir']
    if not destdir:
        logging.error("You must specify the output directory in your config file.")
        logging.error("e.g. outputdir = '/path/to/outputdir'")
        return 1
    if not os.path.exists(destdir):
        try:
            os.mkdir(destdir)
        except OSError:
            logging.exception("Could not create the output directory.")
            return 1

    ########################################################################
    # Now we start the actual processing, now that all the configuration has
    # been gathered and validated
    # create our asset manager... ASSMAN
    assetMrg = assetmanager.AssetManager(destdir, config.get('customwebassets', None))

    # If we've been asked to update web assets, do that and then exit 
    if options.update_web_assets:
        assetMrg.output_noconfig()
        logging.info("Web assets have been updated")
        return 0

    # The changelist support.
    changelists = {}
    for render in config['renders'].itervalues():
        if 'changelist' in render:
            path = render['changelist']
            if path not in changelists:
                out = open(path, "w")
                logging.debug("Opening changelist %s (%s)", out, out.fileno())
                changelists[path] = out
            else:
                out = changelists[path]
            render['changelist'] = out.fileno()

    tilesets = []

    # saves us from creating the same World object over and over again
    worldcache = {}
    # same for textures
    texcache = {}

    # Set up the cache objects to use
    caches = []
    caches.append(cache.LRUCache(size=100))
    if config.get("memcached_host", False):
        caches.append(cache.Memcached(config['memcached_host']))
    # TODO: optionally more caching layers here

    renders = config['renders']
    for render_name, render in renders.iteritems():
        logging.debug("Found the following render thing: %r", render)

        # find or create the world object
        try:
            w = worldcache[render['world']]
        except KeyError:
            w = world.World(render['world'])
            worldcache[render['world']] = w

        # find or create the textures object
        texopts = util.dict_subset(render, ["texturepath", "bgcolor", "northdirection"])
        texopts_key = tuple(texopts.items())
        if texopts_key not in texcache:
            tex = textures.Textures(**texopts)
            logging.info("Generating textures...")
            tex.generate()
            logging.debug("Finished generating textures")
            texcache[texopts_key] = tex
        else:
            tex = texcache[texopts_key]
    
        try:
            logging.debug("Asking for regionset %r" % render['dimension'][1])
            rset = w.get_regionset(render['dimension'][1])
        except IndexError:
            logging.error("Sorry, I can't find anything to render!  Are you sure there are .mca files in the world directory?")
            return 1
        if rset == None: # indicates no such dimension was found:
            logging.error("Sorry, you requested dimension '%s' for %s, but I couldn't find it", render['dimension'][0], render_name)
            return 1

        #################
        # Apply any regionset transformations here

        # Insert a layer of caching above the real regionset. Any world
        # tranformations will pull from this cache, but their results will not
        # be cached by this layer. This uses a common pool of caches; each
        # regionset cache pulls from the same underlying cache object.
        rset = world.CachedRegionSet(rset, caches)

        # If a crop is requested, wrap the regionset here
        if "crop" in render:
            rset = world.CroppedRegionSet(rset, *render['crop'])

        # If this is to be a rotated regionset, wrap it in a RotatedRegionSet
        # object
        if (render['northdirection'] > 0):
            rset = world.RotatedRegionSet(rset, render['northdirection'])
        logging.debug("Using RegionSet %r", rset)

        ###############################
        # Do the final prep and create the TileSet object

        # create our TileSet from this RegionSet
        tileset_dir = os.path.abspath(os.path.join(destdir, render_name))

        # only pass to the TileSet the options it really cares about
        render['name'] = render_name # perhaps a hack. This is stored here for the asset manager
        tileSetOpts = util.dict_subset(render, ["name", "imgformat", "renderchecks", "rerenderprob", "bgcolor", "defaultzoom", "imgquality", "optimizeimg", "rendermode", "worldname_orig", "title", "dimension", "changelist", "showspawn", "overlay", "base", "poititle", "maxzoom", "showlocationmarker", "minzoom"])
        tileSetOpts.update({"spawn": w.find_true_spawn()}) # TODO find a better way to do this
        tset = tileset.TileSet(w, rset, assetMrg, tex, tileSetOpts, tileset_dir)
        tilesets.append(tset)

    # Do tileset preprocessing here, before we start dispatching jobs
    logging.info("Preprocessing...")
    for ts in tilesets:
        ts.do_preprocessing()

    # Output initial static data and configuration
    assetMrg.initialize(tilesets)

    # multiprocessing dispatcher
    if config['processes'] == 1:
        dispatch = dispatcher.Dispatcher()
    else:
        dispatch = dispatcher.MultiprocessingDispatcher(
            local_procs=config['processes'])
    dispatch.render_all(tilesets, config['observer'])
    dispatch.close()

    assetMrg.finalize(tilesets)

    for out in changelists.itervalues():
        logging.debug("Closing %s (%s)", out, out.fileno())
        out.close()

    if config['processes'] == 1:
        logging.debug("Final cache stats:")
        for c in caches:
            logging.debug("\t%s: %s hits, %s misses", c.__class__.__name__, c.hits, c.misses)
    if options.pid:
        os.remove(options.pid)

    logging.info("Your render has been written to '%s', open index.html to view it" % destdir)    
        
    return 0

def list_worlds():
    "Prints out a brief summary of saves found in the default directory"
    print
    worlds = world.get_worlds()
    if not worlds:
        print('No world saves found in the usual place')
        return
    print("Detected saves:")

    # get max length of world name
    worldNameLen = max([len(x) for x in worlds] + [len("World")])

    formatString = "%-" + str(worldNameLen) + "s | %-8s | %-16s | %s "
    print(formatString % ("World", "Playtime", "Modified", "Path"))
    print(formatString % ("-"*worldNameLen, "-"*8, '-'*16, '-'*4))
    for name, info in sorted(worlds.iteritems()):
        if isinstance(name, basestring) and name.startswith("World") and len(name) == 6:
            try:
                world_n = int(name[-1])
                # we'll catch this one later, when it shows up as an
                # integer key
                continue
            except ValueError:
                pass
        timestamp = time.strftime("%Y-%m-%d %H:%M",
                                  time.localtime(info['LastPlayed'] / 1000))
        playtime = info['Time'] / 20
        playstamp = '%d:%02d' % (playtime / 3600, playtime / 60 % 60)
        path = info['path']
        print(formatString % (name, playstamp, timestamp, path))

if __name__ == "__main__":
    multiprocessing.freeze_support()
    try:
        ret = main()
        util.nice_exit(ret)
    except textures.TextureException as e:
        # this isn't a "bug", so don't print scary traceback
        logging.error(str(e))
        util.nice_exit(1)
    except Exception as e:
        logging.exception("""An error has occurred. This may be a bug. Please let us know!
See http://docs.overviewer.org/en/latest/index.html#help

This is the error that occurred:""")
        util.nice_exit(1)

########NEW FILE########
__FILENAME__ = assetmanager
#    This file is part of the Minecraft Overviewer.
#
#    Minecraft Overviewer is free software: you can redistribute it and/or
#    modify it under the terms of the GNU General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or (at
#    your option) any later version.
#
#    Minecraft Overviewer is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General
#    Public License for more details.
#
#    You should have received a copy of the GNU General Public License along
#    with the Overviewer.  If not, see <http://www.gnu.org/licenses/>.

import json
import os
import codecs
import locale
import time
import logging
import traceback

from PIL import Image

import world
import util
from files import FileReplacer, mirror_dir, get_fs_caps

class AssetManager(object):
    """\
These objects provide an interface to metadata and persistent data, and at the
same time, controls the generated javascript files in the output directory.
There should only be one instances of these per execution.
    """

    def __init__(self, outputdir, custom_assets_dir=None):
        """\
Initializes the AssetManager with the top-level output directory.  
It can read/parse and write/dump the overviewerConfig.js file into this top-level
directory. 
        """
        self.outputdir = outputdir
        self.custom_assets_dir = custom_assets_dir
        self.renders = dict()

        self.fs_caps = get_fs_caps(self.outputdir)

        # look for overviewerConfig in self.outputdir
        try:
            with open(os.path.join(self.outputdir, "overviewerConfig.js")) as c:
                overviewerConfig_str = "{" + "\n".join(c.readlines()[1:-1]) + "}"
            self.overviewerConfig = json.loads(overviewerConfig_str)
        except Exception, e:
            if os.path.exists(os.path.join(self.outputdir, "overviewerConfig.js")):
                logging.warning("A previous overviewerConfig.js was found, but I couldn't read it for some reason. Continuing with a blank config")
            logging.debug(traceback.format_exc())
            self.overviewerConfig = dict(tilesets=dict())

        # Make sure python knows the preferred encoding. If it does not, set it
        # to utf-8"
        self.preferredencoding = locale.getpreferredencoding()
        try:
            # We don't care what is returned, just that we can get a codec.
            codecs.lookup(self.preferredencoding)
        except LookupError:
            self.preferredencoding = "utf_8"
        logging.debug("Preferred enoding set to: %s", self.preferredencoding)

    def get_tileset_config(self, name):
        "Return the correct dictionary from the parsed overviewerConfig.js"
        for conf in self.overviewerConfig['tilesets']:
            if conf['path'] == name:
                return conf
        return dict()
        

    def initialize(self, tilesets):
        """Similar to finalize() but calls the tilesets' get_initial_data()
        instead of get_persistent_data() to compile the generated javascript
        config.

        """
        self._output_assets(tilesets, True)

    def finalize(self, tilesets):
        """Called to output the generated javascript and all static files to
        the output directory

        """
        self._output_assets(tilesets, False)

    def _output_assets(self, tilesets, initial):
        if not initial:
            get_data = lambda tileset: tileset.get_persistent_data()
        else:
            get_data = lambda tileset: tileset.get_initial_data()

        # dictionary to hold the overviewerConfig.js settings that we will dumps
        dump = dict()
        dump['CONST'] = dict(tileSize=384)
        dump['CONST']['image'] = {
                'defaultMarker':    'signpost.png',
                'signMarker':       'signpost_icon.png',
                'bedMarker':        'bed.png',
                'spawnMarker':      'https://google-maps-icons.googlecode.com/files/home.png',
                'queryMarker':      'https://google-maps-icons.googlecode.com/files/regroup.png'
                }
        dump['CONST']['mapDivId'] = 'mcmap'
        dump['CONST']['regionStrokeWeight'] = 2 # Obselete
        dump['CONST']['UPPERLEFT']  = world.UPPER_LEFT;
        dump['CONST']['UPPERRIGHT'] = world.UPPER_RIGHT;
        dump['CONST']['LOWERLEFT']  = world.LOWER_LEFT;
        dump['CONST']['LOWERRIGHT'] = world.LOWER_RIGHT;

        # based on the tilesets we have, group them by worlds
        worlds = []
        for tileset in tilesets:
            full_name = get_data(tileset)['world']
            if full_name not in worlds:
                worlds.append(full_name)

        dump['worlds'] = worlds
        dump['map'] = dict()
        dump['map']['debug'] = True
        dump['map']['cacheTag'] = str(int(time.time()))
        dump['map']['north_direction'] = 'lower-left' # only temporary
        dump['map']['center'] = [-314, 67, 94]
        dump['map']['controls'] = {
            'pan': True,
            'zoom': True,
            'spawn': True,
            'compass': True,
            'mapType': True,
            'overlays': True,
            'coordsBox': True,
            'searchBox': True   # Lolwat. Obselete
            }


        dump['tilesets'] = []


        for tileset in tilesets:
            dump['tilesets'].append(get_data(tileset))

            # write a blank image
            blank = Image.new("RGBA", (1,1), tileset.options.get('bgcolor'))
            blank.save(os.path.join(self.outputdir, tileset.options.get('name'), "blank." + tileset.options.get('imgformat')))

        # write out config
        jsondump = json.dumps(dump, indent=4)
        with FileReplacer(os.path.join(self.outputdir, "overviewerConfig.js"), capabilities=self.fs_caps) as tmpfile:
            with codecs.open(tmpfile, 'w', encoding='UTF-8') as f:
                f.write("var overviewerConfig = " + jsondump + ";\n")

        #Copy assets, modify index.html
        self.output_noconfig()        


    def output_noconfig(self):

        # copy web assets into destdir:
        global_assets = os.path.join(util.get_program_path(), "overviewer_core", "data", "web_assets")
        if not os.path.isdir(global_assets):
            global_assets = os.path.join(util.get_program_path(), "web_assets")
        mirror_dir(global_assets, self.outputdir, capabilities=self.fs_caps)

        if self.custom_assets_dir:
            # Could have done something fancy here rather than just overwriting
            # the global files, but apparently this what we used to do pre-rewrite.
            mirror_dir(self.custom_assets_dir, self.outputdir, capabilities=self.fs_caps)

	# write a dummy baseMarkers.js if none exists
        if not os.path.exists(os.path.join(self.outputdir, "baseMarkers.js")):
            with open(os.path.join(self.outputdir, "baseMarkers.js"), "w") as f:
                f.write("// if you wants signs, please see genPOI.py\n");


        # create overviewer.js from the source js files
        js_src = os.path.join(util.get_program_path(), "overviewer_core", "data", "js_src")
        if not os.path.isdir(js_src):
            js_src = os.path.join(util.get_program_path(), "js_src")
        with FileReplacer(os.path.join(self.outputdir, "overviewer.js"), capabilities=self.fs_caps) as tmpfile:
            with open(tmpfile, "w") as fout:
                # first copy in js_src/overviewer.js
                with open(os.path.join(js_src, "overviewer.js"), 'r') as f:
                    fout.write(f.read())
                # now copy in the rest
                for js in os.listdir(js_src):
                    if not js.endswith("overviewer.js") and js.endswith(".js"):
                        with open(os.path.join(js_src,js)) as f:
                            fout.write(f.read())
        
        # Add time and version in index.html
        indexpath = os.path.join(self.outputdir, "index.html")

        index = codecs.open(indexpath, 'r', encoding='UTF-8').read()
        index = index.replace("{title}", "Minecraft Overviewer")
        index = index.replace("{time}", time.strftime("%a, %d %b %Y %H:%M:%S %Z", time.localtime()).decode(self.preferredencoding))
        versionstr = "%s (%s)" % (util.findGitVersion(), util.findGitHash()[:7])
        index = index.replace("{version}", versionstr)

        with FileReplacer(indexpath, capabilities=self.fs_caps) as indexpath:
            with codecs.open(indexpath, 'w', encoding='UTF-8') as output:
                output.write(index)

########NEW FILE########
__FILENAME__ = genPOI
#!/usr/bin/python2

'''
genPOI.py

Scans regionsets for TileEntities and Entities, filters them, and writes out
POI/marker info.

A markerSet is list of POIs to display on a tileset.  It has a display name,
and a group name.

markersDB.js holds a list of POIs in each group
markers.js holds a list of which markerSets are attached to each tileSet


'''
import os
import logging
import json
import sys
import re
import urllib2
import Queue
import multiprocessing

from multiprocessing import Process
from multiprocessing import Pool
from optparse import OptionParser

from overviewer_core import logger
from overviewer_core import nbt
from overviewer_core import configParser, world

UUID_LOOKUP_URL = 'https://sessionserver.mojang.com/session/minecraft/profile/'

def replaceBads(s):
    "Replaces bad characters with good characters!"
    bads = [" ", "(", ")"]
    x=s
    for bad in bads:
        x = x.replace(bad,"_")
    return x

# yes there's a double parenthesis here
# see below for when this is called, and why we do this
# a smarter way would be functools.partial, but that's broken on python 2.6
# when used with multiprocessing
def parseBucketChunks((bucket, rset)):
    pid = multiprocessing.current_process().pid
    pois = dict(TileEntities=[], Entities=[]);
  
    i = 0
    cnt = 0
    l = len(bucket)
    for b in bucket:
        try:
            data = rset.get_chunk(b[0],b[1])
            pois['TileEntities'] += data['TileEntities']
            pois['Entities']     += data['Entities']
        except nbt.CorruptChunkError:
            logging.warning("Ignoring POIs in corrupt chunk %d,%d", b[0], b[1])

        # Perhaps only on verbose ?
        i = i + 1
        if i == 250:
            i = 0
            cnt = 250 + cnt
            logging.info("Found %d entities and %d tile entities in thread %d so far at %d chunks", len(pois['Entities']), len(pois['TileEntities']), pid, cnt);

    return pois

def handleEntities(rset, outputdir, render, rname, config):

    # if we're already handled the POIs for this region regionset, do nothing
    if hasattr(rset, "_pois"):
        return

    logging.info("Looking for entities in %r", rset)

    filters = render['markers']
    rset._pois = dict(TileEntities=[], Entities=[])

    numbuckets = config['processes'];
    if numbuckets < 0:
        numbuckets = multiprocessing.cpu_count()

    if numbuckets == 1:
        for (x,z,mtime) in rset.iterate_chunks():
            try:
                data = rset.get_chunk(x,z) 
                rset._pois['TileEntities'] += data['TileEntities']
                rset._pois['Entities']     += data['Entities']
            except nbt.CorruptChunkError:
                logging.warning("Ignoring POIs in corrupt chunk %d,%d", x,z)
  
    else:
        buckets = [[] for i in range(numbuckets)];
  
        for (x,z,mtime) in rset.iterate_chunks():
            i = x / 32 + z / 32
            i = i % numbuckets 
            buckets[i].append([x,z])
  
        for b in buckets:
            logging.info("Buckets has %d entries", len(b));
  
        # Create a pool of processes and run all the functions
        pool = Pool(processes=numbuckets)
        results = pool.map(parseBucketChunks, ((buck, rset) for buck in buckets))
  
        logging.info("All the threads completed")
  
        # Fix up all the quests in the reset
        for data in results:
            rset._pois['TileEntities'] += data['TileEntities']
            rset._pois['Entities']     += data['Entities']

    logging.info("Done.")

def handlePlayers(rset, render, worldpath):
    if not hasattr(rset, "_pois"):
        rset._pois = dict(TileEntities=[], Entities=[])

    # only handle this region set once
    if 'Players' in rset._pois:
        return
    dimension = None
    try:
        dimension = {None: 0,
                     'DIM-1': -1,
                     'DIM1': 1}[rset.get_type()]
    except KeyError, e:
        mystdim = re.match(r"^DIM_MYST(\d+)$", e.message)  # Dirty hack. Woo!
        if mystdim:
            dimension = int(mystdim.group(1))
        else:
            raise
    playerdir = os.path.join(worldpath, "playerdata")
    useUUIDs = True
    if not os.path.isdir(playerdir):
        playerdir = os.path.join(worldpath, "players")
        useUUIDs = False

    if os.path.isdir(playerdir):
        playerfiles = os.listdir(playerdir)
        playerfiles = [x for x in playerfiles if x.endswith(".dat")]
        isSinglePlayer = False

    else:
        playerfiles = [os.path.join(worldpath, "level.dat")]
        isSinglePlayer = True

    rset._pois['Players'] = []
    for playerfile in playerfiles:
        try:
            data = nbt.load(os.path.join(playerdir, playerfile))[1]
            if isSinglePlayer:
                data = data['Data']['Player']
        except IOError:
            logging.warning("Skipping bad player dat file %r", playerfile)
            continue
        playername = playerfile.split(".")[0]
        if useUUIDs:
            try:
                profile = json.loads(urllib2.urlopen(UUID_LOOKUP_URL + playername.replace('-','')).read())
                if 'name' in profile:
                    playername = profile['name']
            except (ValueError, urllib2.URLError):
                logging.warning("Unable to get player name for UUID %s", playername)
        if isSinglePlayer:
            playername = 'Player'
        if data['Dimension'] == dimension:
            # Position at last logout
            data['id'] = "Player"
            data['EntityId'] = playername
            data['x'] = int(data['Pos'][0])
            data['y'] = int(data['Pos'][1])
            data['z'] = int(data['Pos'][2])
            rset._pois['Players'].append(data)
        if "SpawnX" in data and dimension == 0:
            # Spawn position (bed or main spawn)
            spawn = {"id": "PlayerSpawn",
                     "EntityId": playername,
                     "x": data['SpawnX'],
                     "y": data['SpawnY'],
                     "z": data['SpawnZ']}
            rset._pois['Players'].append(spawn)

def handleManual(rset, manualpois):
    if not hasattr(rset, "_pois"):
        rset._pois = dict(TileEntities=[], Entities=[])
    
    rset._pois['Manual'] = []

    if manualpois:
        rset._pois['Manual'].extend(manualpois)

def main():

    if os.path.basename(sys.argv[0]) == """genPOI.py""":
        helptext = """genPOI.py
            %prog --config=<config file> [--quiet]"""
    else:
        helptext = """genPOI
            %prog --genpoi --config=<config file> [--quiet]"""

    logger.configure()

    parser = OptionParser(usage=helptext)
    parser.add_option("-c", "--config", dest="config", action="store", help="Specify the config file to use.")
    parser.add_option("--quiet", dest="quiet", action="count", help="Reduce logging output")
    parser.add_option("--skip-scan", dest="skipscan", action="store_true", help="Skip scanning for entities when using GenPOI")

    options, args = parser.parse_args()
    if not options.config:
        parser.print_help()
        return

    if options.quiet > 0:
        logger.configure(logging.WARN, False)

    # Parse the config file
    mw_parser = configParser.MultiWorldParser()
    mw_parser.parse(options.config)
    try:
        config = mw_parser.get_validated_config()
    except Exception:
        logging.exception("An error was encountered with your configuration. See the info below.")
        return 1

    destdir = config['outputdir']
    # saves us from creating the same World object over and over again
    worldcache = {}

    markersets = set()
    markers = dict()

    for rname, render in config['renders'].iteritems():
        try:
            worldpath = config['worlds'][render['world']]
        except KeyError:
            logging.error("Render %s's world is '%s', but I could not find a corresponding entry in the worlds dictionary.",
                    rname, render['world'])
            return 1
        render['worldname_orig'] = render['world']
        render['world'] = worldpath
        
        # find or create the world object
        if (render['world'] not in worldcache):
            w = world.World(render['world'])
            worldcache[render['world']] = w
        else:
            w = worldcache[render['world']]
        
        rset = w.get_regionset(render['dimension'][1])
        if rset == None: # indicates no such dimension was found:
            logging.error("Sorry, you requested dimension '%s' for the render '%s', but I couldn't find it", render['dimension'][0], rname)
            return 1
      
        for f in render['markers']:
            markersets.add(((f['name'], f['filterFunction']), rset))
            name = replaceBads(f['name']) + hex(hash(f['filterFunction']))[-4:] + "_" + hex(hash(rset))[-4:]
            to_append = dict(groupName=name, 
                    displayName = f['name'], 
                    icon=f.get('icon', 'signpost_icon.png'), 
                    createInfoWindow=f.get('createInfoWindow',True),
                    checked = f.get('checked', False))
            try:
                l = markers[rname]
                l.append(to_append)
            except KeyError:
                markers[rname] = [to_append]
        
        if not options.skipscan:
            handleEntities(rset, os.path.join(destdir, rname), render, rname, config)

        handlePlayers(rset, render, worldpath)
        handleManual(rset, render['manualpois'])

    logging.info("Done handling POIs")
    logging.info("Writing out javascript files")
    markerSetDict = dict()
    for (flter, rset) in markersets:
        # generate a unique name for this markerset.  it will not be user visible
        filter_name =     flter[0]
        filter_function = flter[1]

        name = replaceBads(filter_name) + hex(hash(filter_function))[-4:] + "_" + hex(hash(rset))[-4:]
        markerSetDict[name] = dict(created=False, raw=[], name=filter_name)
        for poi in rset._pois['Entities']:
            result = filter_function(poi)
            if result:
                if isinstance(result, basestring):
                    d = dict(x=poi['Pos'][0], y=poi['Pos'][1], z=poi['Pos'][2], text=result, hovertext=result)
                elif type(result) == tuple:
                    d = dict(x=poi['Pos'][0], y=poi['Pos'][1], z=poi['Pos'][2], text=result[1], hovertext=result[0])
                if "icon" in poi:
                    d.update({"icon": poi['icon']})
                if "createInfoWindow" in poi:
                    d.update({"createInfoWindow": poi['createInfoWindow']})
                markerSetDict[name]['raw'].append(d)
        for poi in rset._pois['TileEntities']:
            result = filter_function(poi)
            if result:
                if isinstance(result, basestring):
                    d = dict(x=poi['x'], y=poi['y'], z=poi['z'], text=result, hovertext=result)
                elif type(result) == tuple:
                    d = dict(x=poi['x'], y=poi['y'], z=poi['z'], text=result[1], hovertext=result[0])
                # Dict support to allow more flexible things in the future as well as polylines on the map.
                elif type(result) == dict:
                    d = dict(x=poi['x'], y=poi['y'], z=poi['z'], text=result['text'])
                    # Use custom hovertext if provided...
                    if 'hovertext' in result and isinstance(result['hovertext'], basestring):
                        d['hovertext'] = result['hovertext']
                    else: # ...otherwise default to display text.
                        d['hovertext'] = result['text']
                    if 'polyline' in result and type(result['polyline']) == tuple:  #if type(result.get('polyline', '')) == tuple:
                        d['polyline'] = []
                        for point in result['polyline']:
                            # This poor man's validation code almost definately needs improving.
                            if type(point) == dict:
                                d['polyline'].append(dict(x=point['x'],y=point['y'],z=point['z']))
                        if isinstance(result['color'], basestring):
                            d['strokeColor'] = result['color']
                if "icon" in poi:
                    d.update({"icon": poi['icon']})
                if "createInfoWindow" in poi:
                    d.update({"createInfoWindow": poi['createInfoWindow']})
                markerSetDict[name]['raw'].append(d)
        for poi in rset._pois['Players']:
            result = filter_function(poi)
            if result:
                if isinstance(result, basestring):
                    d = dict(x=poi['x'], y=poi['y'], z=poi['z'], text=result, hovertext=result)
                elif type(result) == tuple:
                    d = dict(x=poi['x'], y=poi['y'], z=poi['z'], text=result[1], hovertext=result[0])
                # Dict support to allow more flexible things in the future as well as polylines on the map.
                elif type(result) == dict:
                    d = dict(x=poi['x'], y=poi['y'], z=poi['z'], text=result['text'])
                    # Use custom hovertext if provided...
                    if 'hovertext' in result and isinstance(result['hovertext'], basestring):
                        d['hovertext'] = result['hovertext']
                    else: # ...otherwise default to display text.
                        d['hovertext'] = result['text']
                    if 'polyline' in result and type(result['polyline']) == tuple:  #if type(result.get('polyline', '')) == tuple:
                        d['polyline'] = []
                        for point in result['polyline']:
                            # This poor man's validation code almost definately needs improving.
                            if type(point) == dict:
                                d['polyline'].append(dict(x=point['x'],y=point['y'],z=point['z']))
                        if isinstance(result['color'], basestring):
                            d['strokeColor'] = result['color']
                if "icon" in poi:
                    d.update({"icon": poi['icon']})
                if "createInfoWindow" in poi:
                    d.update({"createInfoWindow": poi['createInfoWindow']})
                markerSetDict[name]['raw'].append(d)
        for poi in rset._pois['Manual']:
            result = filter_function(poi)
            if result:
                if isinstance(result, basestring):
                    d = dict(x=poi['x'], y=poi['y'], z=poi['z'], text=result, hovertext=result)
                elif type(result) == tuple:
                    d = dict(x=poi['x'], y=poi['y'], z=poi['z'], text=result[1], hovertext=result[0])
                # Dict support to allow more flexible things in the future as well as polylines on the map.
                elif type(result) == dict:
                    d = dict(x=poi['x'], y=poi['y'], z=poi['z'], text=result['text'])
                    # Use custom hovertext if provided...
                    if 'hovertext' in result and isinstance(result['hovertext'], basestring):
                        d['hovertext'] = result['hovertext']
                    else: # ...otherwise default to display text.
                        d['hovertext'] = result['text']
                    if 'polyline' in result and type(result['polyline']) == tuple:  #if type(result.get('polyline', '')) == tuple:
                        d['polyline'] = []
                        for point in result['polyline']:
                            # This poor man's validation code almost definately needs improving.
                            if type(point) == dict:
                                d['polyline'].append(dict(x=point['x'],y=point['y'],z=point['z']))
                        if isinstance(result['color'], basestring):
                            d['strokeColor'] = result['color']
                if "icon" in poi:
                    d.update({"icon": poi['icon']})
                if "createInfoWindow" in poi:
                    d.update({"createInfoWindow": poi['createInfoWindow']})
                markerSetDict[name]['raw'].append(d)
    #print markerSetDict

    with open(os.path.join(destdir, "markersDB.js"), "w") as output:
        output.write("var markersDB=")
        json.dump(markerSetDict, output, indent=2)
        output.write(";\n");
    with open(os.path.join(destdir, "markers.js"), "w") as output:
        output.write("var markers=")
        json.dump(markers, output, indent=2)
        output.write(";\n");
    with open(os.path.join(destdir, "baseMarkers.js"), "w") as output:
        output.write("overviewer.util.injectMarkerScript('markersDB.js');\n")
        output.write("overviewer.util.injectMarkerScript('markers.js');\n")
        output.write("overviewer.collections.haveSigns=true;\n")
    logging.info("Done")

if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = cache
#    This file is part of the Minecraft Overviewer.
#
#    Minecraft Overviewer is free software: you can redistribute it and/or
#    modify it under the terms of the GNU General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or (at
#    your option) any later version.
#
#    Minecraft Overviewer is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General
#    Public License for more details.
#
#    You should have received a copy of the GNU General Public License along
#    with the Overviewer.  If not, see <http://www.gnu.org/licenses/>.

"""This module has supporting functions for the caching logic used in world.py.

Each cache class should implement the standard container type interface
(__getitem__ and __setitem__), as well as provide a "hits" and "misses"
attribute.

"""
import functools
import logging
import cPickle

class LRUCache(object):
    """A simple, generic, in-memory LRU cache that implements the standard
    python container interface.

    An ordered dict type would simplify this implementation a bit, but we want
    Python 2.6 compatibility and the standard library ordereddict was added in
    2.7. It's probably okay because this implementation can be tuned for
    exactly what we need and nothing more.

    This implementation keeps a linked-list of cache keys and values, ordered
    in least-recently-used order. A dictionary maps keys to linked-list nodes.

    On cache hit, the link is moved to the end of the list. On cache miss, the
    first item of the list is evicted. All operations have constant time
    complexity (dict lookups are worst case O(n) time)

    """
    class _LinkNode(object):
        __slots__ = ['left', 'right', 'key', 'value']
        def __init__(self,l=None,r=None,k=None,v=None):
            self.left = l
            self.right = r
            self.key = k
            self.value = v

    def __init__(self, size=100, destructor=None):
        """Initialize a new LRU cache with the given size.

        destructor, if given, is a callable that is called upon an item being
        evicted from the cache. It takes one argument, the value stored in the
        cache.

        """
        self.cache = {}

        # Two sentinel nodes at the ends of the linked list simplify boundary
        # conditions in the code below.
        self.listhead = LRUCache._LinkNode()
        self.listtail = LRUCache._LinkNode()
        self.listhead.right = self.listtail
        self.listtail.left = self.listhead

        self.hits = 0
        self.misses = 0

        self.size = size

        self.destructor = destructor

    # Initialize an empty cache of the same size for worker processes
    def __getstate__(self):
        return self.size
    def __setstate__(self, size):
        self.__init__(size)

    def __getitem__(self, key):
        try:
            link = self.cache[key]
        except KeyError:
            self.misses += 1
            raise

        # Disconnect the link from where it is
        link.left.right = link.right
        link.right.left = link.left

        # Insert the link at the end of the list
        tail = self.listtail
        link.left = tail.left
        link.right = tail
        tail.left.right = link
        tail.left = link

        self.hits += 1
        return link.value

    def __setitem__(self, key, value):
        cache = self.cache
        if key in cache:
            # Shortcut this case
            cache[key].value = value
            return
        if len(cache) >= self.size:
            # Evict a node
            link = self.listhead.right
            del cache[link.key]
            link.left.right = link.right
            link.right.left = link.left
            d = self.destructor
            if d:
                d(link.value)
            del link

        # The node doesn't exist already, and we have room for it. Let's do this.
        tail = self.listtail
        link = LRUCache._LinkNode(tail.left, tail,key,value)
        tail.left.right = link
        tail.left = link

        cache[key] = link

    def __delitem__(self, key):
        # Used to flush the cache of this key
        cache = self.cache
        link = cache[key]
        del cache[key]
        link.left.right = link.right
        link.right.left = link.left
        
        # Call the destructor
        d = self.destructor
        if d:
            d(link.value)

# memcached is an option, but unless your IO costs are really high, it just
# ends up adding overhead and isn't worth it.
try:
    import memcache
except ImportError:
    class Memcached(object):
        def __init__(*args):
            raise ImportError("No module 'memcache' found. Please install python-memcached")
else:
    class Memcached(object):
        def __init__(self, conn='127.0.0.1:11211'):
            self.conn = conn
            self.mc = memcache.Client([conn], debug=0, pickler=cPickle.Pickler, unpickler=cPickle.Unpickler)

        def __getstate__(self):
            return self.conn
        def __setstate__(self, conn):
            self.__init__(conn)

        def __getitem__(self, key):
            v = self.mc.get(key)
            if not v:
                raise KeyError()
            return v

        def __setitem__(self, key, value):
            self.mc.set(key, value)

########NEW FILE########
__FILENAME__ = configParser
import optparse
import sys
import os.path
import logging
import traceback

import settingsDefinition
import settingsValidators

class MissingConfigException(Exception):
    "To be thrown when the config file can't be found"
    pass

class MultiWorldParser(object):
    """A class that is used to parse a settings.py file.
    
    This class's job is to compile and validate the configuration settings for
    a set of renders. It can read in configuration from the given file with the
    parse() method, and one can set configuration options directly with the
    set_config_item() method.

    get_validated_config() validates and returns the validated config

    """

    def __init__(self):
        """Initialize this parser object"""
        # This maps config names to their values
        self._config_state = {}

        # Scan the settings definition and build the config state heirarchy.
        # Also go ahead and set default values for non-required settings.
        # This maps setting names to their values as given in
        # settingsDefinition.py
        self._settings = {}
        for settingname in dir(settingsDefinition):
            setting = getattr(settingsDefinition, settingname)
            if not isinstance(setting, settingsValidators.Setting):
                continue

            self._settings[settingname] = setting
            
            # Set top level defaults. This is intended to be for container
            # types, so they can initialize a config file with an empty
            # container (like a dict)
            if setting.required and setting.default is not None:
                self._config_state[settingname] = setting.default

    def set_config_item(self, itemname, itemvalue):
        self._config_state[itemname] = itemvalue

    def set_renders_default(self, settingname, newdefault):
        """This method sets the default for one of the settings of the "renders"
        dictionary. This is hard-coded to expect a "renders" setting in the
        settings definition, and for its validator to be a dictValidator with
        its valuevalidator to be a configDictValidator

        """
        # If the structure of settingsDefinitions changes, you'll need to change
        # this to find the proper place to find the settings dictionary
        render_settings = self._settings['renders'].validator.valuevalidator.config
        render_settings[settingname].default = newdefault

    def parse(self, settings_file):
        """Reads in the named file and parses it, storing the results in an
        internal state awating to be validated and returned upon call to
        get_render_settings()

        Attributes defined in the file that do not match any setting are then
        matched against the renderdict setting, and if it does match, is used as
        the default for that setting.

        """
        if not os.path.exists(settings_file) and not os.path.isfile(settings_file):
            raise MissingConfigException("The settings file you specified (%r) does not exist, or is not a file" % settings_file)

        # The global environment should be the rendermode module, so the config
        # file has access to those resources.
        import rendermodes

        try:
            execfile(settings_file, rendermodes.__dict__, self._config_state)
        
        except Exception, ex:
            if isinstance(ex, SyntaxError):
                logging.error("Syntax error parsing %s" %  settings_file)
                logging.error("The traceback below will tell you which line triggered the syntax error\n")
            elif isinstance(ex, NameError):
                logging.error("NameError parsing %s" %  settings_file)
                logging.error("The traceback below will tell you which line referenced the non-existent variable\n")
            else:
                logging.error("Error parsing %s" %  settings_file)
                logging.error("The traceback below will tell you which line triggered the error\n")

            # skip the execfile part of the traceback
            exc_type, exc_value, exc_traceback = sys.exc_info()
            formatted_lines = traceback.format_exc().splitlines()
            print_rest = False
            lines = []
            for l in formatted_lines:
                if print_rest: lines.append(l)
                else:
                    if "execfile" in l: print_rest = True
            # on windows, our traceback as no 'execfile'.  in this case, print everything
            if print_rest: logging.error("Partial traceback:\n" + "\n".join(lines))
            else: logging.error("Partial traceback:\n" + "\n".join(formatted_lines))
            sys.exit(1)

        # At this point, make a pass through the file to possibly set global
        # render defaults
        render_settings = self._settings['renders'].validator.valuevalidator.config
        for key in self._config_state.iterkeys():
            if key not in self._settings:
                if key in render_settings:
                    setting = render_settings[key]
                    setting.default = self._config_state[key]


    def get_validated_config(self):
        """Validate and return the configuration. Raises a ValidationException
        if there was a problem validating the config.

        Could also raise a ValueError
        
        """
        # Okay, this is okay, isn't it? We're going to create the validation
        # routine right here, right now. I hope this works!
        validator = settingsValidators.make_configDictValidator(self._settings, ignore_undefined=True)
        # Woah. What just happened? No. WAIT, WHAT ARE YOU...
        validated_config = validator(self._config_state)
        # WHAT HAVE YOU DONE?
        return validated_config
        # WHAT HAVE YOU DOOOOOOOOOOONE????

########NEW FILE########
__FILENAME__ = dispatcher
#    This file is part of the Minecraft Overviewer.
#
#    Minecraft Overviewer is free software: you can redistribute it and/or
#    modify it under the terms of the GNU General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or (at
#    your option) any later version.
#
#    Minecraft Overviewer is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General
#    Public License for more details.
#
#    You should have received a copy of the GNU General Public License along
#    with the Overviewer.  If not, see <http://www.gnu.org/licenses/>.

import util
import multiprocessing
import multiprocessing.managers
import cPickle as pickle
import Queue
import time
from signals import Signal

class Dispatcher(object):
    """This class coordinates the work of all the TileSet objects
    among one worker process. By subclassing this class and
    implementing setup_tilesets(), dispatch(), and close(), it is
    possible to create a Dispatcher that distributes this work to many
    worker processes.
    """
    def __init__(self):
        super(Dispatcher, self).__init__()

        # list of (tileset, workitem) tuples
        # keeps track of dispatched but unfinished jobs
        self._running_jobs = []
        # list of (tileset, workitem, dependencies) tuples
        # keeps track of jobs waiting to run after dependencies finish
        self._pending_jobs = []

    def render_all(self, tilesetlist, observer):
        """Render all of the tilesets in the given
        tilesetlist. status_callback is called periodically to update
        status. The callback should take the following arguments:
        (phase, items_completed, total_items), where total_items may
        be none if there is no useful estimate.
        """
        # TODO use status callback

        # setup tilesetlist
        self.setup_tilesets(tilesetlist)

        # iterate through all possible phases
        num_phases = [tileset.get_num_phases() for tileset in tilesetlist]
        for phase in xrange(max(num_phases)):
            # construct a list of iterators to use for this phase
            work_iterators = []
            for i, tileset in enumerate(tilesetlist):
                if phase < num_phases[i]:
                    def make_work_iterator(tset, p):
                        return ((tset, workitem) for workitem in tset.iterate_work_items(p))
                    work_iterators.append(make_work_iterator(tileset, phase))

            # keep track of total jobs, and how many jobs are done
            total_jobs = 0
            for tileset, phases in zip(tilesetlist, num_phases):
                if phase < phases:
                    jobs_for_tileset = tileset.get_phase_length(phase)
                    # if one is unknown, the total is unknown
                    if jobs_for_tileset is None:
                        total_jobs = None
                        break
                    else:
                        total_jobs += jobs_for_tileset

            observer.start(total_jobs)
            # go through these iterators round-robin style
            for tileset, (workitem, deps) in util.roundrobin(work_iterators):
                self._pending_jobs.append((tileset, workitem, deps))
                observer.add(self._dispatch_jobs())

            # after each phase, wait for the work to finish
            while len(self._pending_jobs) > 0 or len(self._running_jobs) > 0:
                observer.add(self._dispatch_jobs())

            observer.finish()

    def _dispatch_jobs(self):
        # helper function to dispatch pending jobs when their
        # dependencies are met, and to manage self._running_jobs
        dispatched_jobs = []
        finished_jobs = []

        pending_jobs_nodeps = [(j[0], j[1]) for j in self._pending_jobs]

        for pending_job in self._pending_jobs:
            tileset, workitem, deps = pending_job

            # see if any of the deps are in _running_jobs or _pending_jobs
            for dep in deps:
                if (tileset, dep) in self._running_jobs or (tileset, dep) in pending_jobs_nodeps:
                    # it is! don't dispatch this item yet
                    break
            else:
                # it isn't! all dependencies are finished
                finished_jobs += self.dispatch(tileset, workitem)
                self._running_jobs.append((tileset, workitem))
                dispatched_jobs.append(pending_job)

        # make sure to at least get finished jobs, even if we don't
        # submit any new ones...
        if len(dispatched_jobs) == 0:
            finished_jobs += self.dispatch(None, None)

        # clean out the appropriate lists
        for job in finished_jobs:
            self._running_jobs.remove(job)
        for job in dispatched_jobs:
            self._pending_jobs.remove(job)

        return len(finished_jobs)

    def close(self):
        """Close the Dispatcher. This should be called when you are
        done with the dispatcher, to ensure that it cleans up any
        processes or connections it may still have around.
        """
        pass

    def setup_tilesets(self, tilesetlist):
        """Called whenever a new list of tilesets are being used. This
        lets subclasses distribute the whole list at once, instead of
        for each work item."""
        pass

    def dispatch(self, tileset, workitem):
        """Dispatch the given work item. The end result of this call
        should be running tileset.do_work(workitem) somewhere. This
        function should return a list of (tileset, workitem) tuples
        that have completed since the last call. If tileset is None,
        then returning completed jobs is all this function should do.
        """
        if not tileset is None:
            tileset.do_work(workitem)
            return [(tileset, workitem),]
        return []

class MultiprocessingDispatcherManager(multiprocessing.managers.BaseManager):
    """This multiprocessing manager is responsible for giving worker
    processes access to the communication Queues, and also gives
    workers access to the current tileset list.
    """
    def _get_job_queue(self):
        return self.job_queue
    def _get_results_queue(self):
        return self.result_queue
    def _get_signal_queue(self):
        return self.signal_queue
    def _get_tileset_data(self):
        return self.tileset_data

    def __init__(self, address=None, authkey=None):
        self.job_queue = multiprocessing.Queue()
        self.result_queue = multiprocessing.Queue()
        self.signal_queue = multiprocessing.Queue()

        self.tilesets = []
        self.tileset_version = 0
        self.tileset_data = [[], 0]

        self.register("get_job_queue", callable=self._get_job_queue)
        self.register("get_result_queue", callable=self._get_results_queue)
        self.register("get_signal_queue", callable=self._get_signal_queue)
        self.register("get_tileset_data", callable=self._get_tileset_data, proxytype=multiprocessing.managers.ListProxy)

        super(MultiprocessingDispatcherManager, self).__init__(address=address, authkey=authkey)

    @classmethod
    def from_address(cls, address, authkey, serializer):
        "Required to be implemented to make multiprocessing happy"
        c = cls(address=address, authkey=authkey)
        return c

    def set_tilesets(self, tilesets):
        """This is used in MultiprocessingDispatcher.setup_tilesets to
        update the tilesets each worker has access to. It also
        increments a `tileset_version` which is an easy way for
        workers to see if their tileset list is out-of-date without
        pickling and copying over the entire list.
        """
        self.tilesets = tilesets
        self.tileset_version += 1
        data = self.get_tileset_data()
        data[0] = self.tilesets
        data[1] = self.tileset_version


class MultiprocessingDispatcherProcess(multiprocessing.Process):
    """This class represents a single worker process. It is created
    automatically by MultiprocessingDispatcher, but it can even be
    used manually to spawn processes on different machines on the same
    network.
    """
    def __init__(self, manager):
        """Creates the process object. manager should be an instance
        of MultiprocessingDispatcherManager connected to the one
        created in MultiprocessingDispatcher.
        """
        super(MultiprocessingDispatcherProcess, self).__init__()
        self.job_queue = manager.get_job_queue()
        self.result_queue = manager.get_result_queue()
        self.signal_queue = manager.get_signal_queue()
        self.tileset_proxy = manager.get_tileset_data()

    def update_tilesets(self):
        """A convenience function to update our local tilesets to the
        current version in use by the MultiprocessingDispatcher.
        """
        self.tilesets, self.tileset_version = self.tileset_proxy._getvalue()

    def run(self):
        """The main work loop. Jobs are pulled from the job queue and
        executed, then the result is pushed onto the result
        queue. Updates to the tilesetlist are recognized and handled
        automatically. This is the method that actually runs in the
        new worker process.
        """
        # per-process job get() timeout
        timeout = 1.0

        # update our tilesets
        self.update_tilesets()

        # register for all available signals
        def register_signal(name, sig):
            def handler(*args, **kwargs):
                self.signal_queue.put((name, args, kwargs), False)
            sig.set_interceptor(handler)
        for name, sig in Signal.signals.iteritems():
            register_signal(name, sig)

        # notify that we're starting up
        self.result_queue.put(None, False)
        while True:
            try:
                job = self.job_queue.get(True, timeout)
                if job == None:
                    # this is a end-of-jobs sentinel
                    return

                # unpack job
                tv, ti, workitem = job

                if tv != self.tileset_version:
                    # our tilesets changed!
                    self.update_tilesets()
                    assert tv == self.tileset_version

                # do job
                ret = self.tilesets[ti].do_work(workitem)
                result = (ti, workitem, ret,)
                self.result_queue.put(result, False)
            except Queue.Empty:
                pass

class MultiprocessingDispatcher(Dispatcher):
    """A subclass of Dispatcher that spawns worker processes and
    distributes jobs to them to speed up processing.
    """
    def __init__(self, local_procs=-1, address=None, authkey=None):
        """Creates the dispatcher. local_procs should be the number of
        worker processes to spawn. If it's omitted (or negative)
        the number of available CPUs is used instead.
        """
        super(MultiprocessingDispatcher, self).__init__()

        # automatic local_procs handling
        if local_procs < 0:
            local_procs = multiprocessing.cpu_count()
        self.local_procs = local_procs

        self.outstanding_jobs = 0
        self.num_workers = 0
        self.manager = MultiprocessingDispatcherManager(address=address, authkey=authkey)
        self.manager.start()
        self.job_queue = self.manager.get_job_queue()
        self.result_queue = self.manager.get_result_queue()
        self.signal_queue = self.manager.get_signal_queue()

        # create and fill the pool
        self.pool = []
        for i in xrange(self.local_procs):
            proc = MultiprocessingDispatcherProcess(self.manager)
            proc.start()
            self.pool.append(proc)

    def close(self):
        # empty the queue
        self._handle_messages(timeout=0.0)
        while self.outstanding_jobs > 0:
            self._handle_messages()

        # send of the end-of-jobs sentinel
        for p in xrange(self.num_workers):
            self.job_queue.put(None, False)

        # TODO better way to be sure worker processes get the message
        time.sleep(1)

        # and close the manager
        self.manager.shutdown()
        self.manager = None
        self.pool = None

    def setup_tilesets(self, tilesets):
        self.manager.set_tilesets(tilesets)

    def dispatch(self, tileset, workitem):
        # handle the no-new-work case
        if tileset is None:
            return self._handle_messages()

        # create and submit the job
        tileset_index = self.manager.tilesets.index(tileset)
        self.job_queue.put((self.manager.tileset_version, tileset_index, workitem), False)
        self.outstanding_jobs += 1

        # make sure the queue doesn't fill up too much
        finished_jobs = self._handle_messages(timeout=0.0)
        while self.outstanding_jobs > self.num_workers * 10:
            finished_jobs += self._handle_messages()
        return finished_jobs

    def _handle_messages(self, timeout=0.01):
        # work function: takes results out of the result queue and
        # keeps track of how many outstanding jobs remain
        finished_jobs = []

        result_empty = False
        signal_empty = False
        while not (result_empty and signal_empty):
            if not result_empty:
                try:
                    result = self.result_queue.get(False)

                    if result != None:
                        # completed job
                        ti, workitem, ret = result
                        finished_jobs.append((self.manager.tilesets[ti], workitem))
                        self.outstanding_jobs -= 1
                    else:
                        # new worker
                        self.num_workers += 1
                except Queue.Empty:
                    result_empty = True
            if not signal_empty:
                try:
                    if timeout > 0.0:
                        name, args, kwargs = self.signal_queue.get(True, timeout)
                    else:
                        name, args, kwargs = self.signal_queue.get(False)
                    # timeout should only apply once
                    timeout = 0.0

                    sig = Signal.signals[name]
                    sig.emit_intercepted(*args, **kwargs)
                except Queue.Empty:
                    signal_empty = True

        return finished_jobs

    @classmethod
    def start_manual_process(cls, address, authkey):
        """A convenience method to start up a manual process, possibly
        on another machine. Address is a (hostname, port) tuple, and
        authkey must be the same as that provided to the
        MultiprocessingDispatcher constructor.
        """
        m = MultiprocessingDispatcherManager(address=address, authkey=authkey)
        m.connect()
        p = MultiprocessingDispatcherProcess(m)
        p.run()

########NEW FILE########
__FILENAME__ = files
#    This file is part of the Minecraft Overviewer.
#
#    Minecraft Overviewer is free software: you can redistribute it and/or
#    modify it under the terms of the GNU General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or (at
#    your option) any later version.
#
#    Minecraft Overviewer is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General
#    Public License for more details.
#
#    You should have received a copy of the GNU General Public License along
#    with the Overviewer.  If not, see <http://www.gnu.org/licenses/>.

import os
import os.path
import tempfile
import shutil
import logging
import stat

default_caps = {"chmod_works": True, "rename_works": True}

def get_fs_caps(dir_to_test):
    return {"chmod_works": does_chmod_work(dir_to_test),
            "rename_works": does_rename_work(dir_to_test)
            }

def does_chmod_work(dir_to_test):
    "Detects if chmod works in a given directory"
    # a CIFS mounted FS is the only thing known to reliably not provide chmod

    if not os.path.isdir(dir_to_test):
        return True

    f1 = tempfile.NamedTemporaryFile(dir=dir_to_test)
    try:
        f1_stat = os.stat(f1.name)
        os.chmod(f1.name, f1_stat.st_mode | stat.S_IRUSR)
        chmod_works = True
        logging.debug("Detected that chmods work in %r" % dir_to_test)
    except OSError:
        chmod_works = False
        logging.debug("Detected that chmods do NOT work in %r" % dir_to_test)
    return chmod_works

def does_rename_work(dir_to_test):
    with tempfile.NamedTemporaryFile(dir=dir_to_test) as f1:
        with tempfile.NamedTemporaryFile(dir=dir_to_test) as f2:
            try:
                os.rename(f1.name,f2.name)
            except OSError:
                renameworks = False
                logging.debug("Detected that overwriting renames do NOT work in %r" % dir_to_test)
            else:
                renameworks = True
                logging.debug("Detected that overwriting renames work in %r" % dir_to_test)
                # re-make this file so it can be deleted without error
                open(f1.name, 'w').close()
    return renameworks

## useful recursive copy, that ignores common OS cruft
def mirror_dir(src, dst, entities=None, capabilities=default_caps):
    '''copies all of the entities from src to dst'''
    chmod_works = capabilities.get("chmod_works")
    if not os.path.exists(dst):
        os.mkdir(dst)
    if entities and type(entities) != list: raise Exception("Expected a list, got a %r instead" % type(entities))
    
    # files which are problematic and should not be copied
    # usually, generated by the OS
    skip_files = ['Thumbs.db', '.DS_Store']
    
    for entry in os.listdir(src):
        if entry in skip_files:
            continue
        if entities and entry not in entities:
            continue
        
        if os.path.isdir(os.path.join(src,entry)):
            mirror_dir(os.path.join(src, entry), os.path.join(dst, entry), capabilities=capabilities)
        elif os.path.isfile(os.path.join(src,entry)):
            try:
                if chmod_works:
                    shutil.copy(os.path.join(src, entry), os.path.join(dst, entry))
                else:
                    shutil.copyfile(os.path.join(src, entry), os.path.join(dst, entry))
            except IOError as outer: 
                try:
                    # maybe permission problems?
                    src_stat = os.stat(os.path.join(src, entry))
                    os.chmod(os.path.join(src, entry), src_stat.st_mode | stat.S_IRUSR)
                    dst_stat = os.stat(os.path.join(dst, entry))
                    os.chmod(os.path.join(dst, entry), dst_stat.st_mode | stat.S_IWUSR)
                except OSError: # we don't care if this fails
                    pass
                # try again; if this stills throws an error, let it propagate up
                if chmod_works:
                    shutil.copy(os.path.join(src, entry), os.path.join(dst, entry))
                else:
                    shutil.copyfile(os.path.join(src, entry), os.path.join(dst, entry))

# Define a context manager to handle atomic renaming or "just forget it write
# straight to the file" depending on whether os.rename provides atomic
# overwrites.
# Detect whether os.rename will overwrite files
doc = """This class acts as a context manager for files that are to be written
out overwriting an existing file.

The parameter is the destination filename. The value returned into the context
is the filename that should be used. On systems that support an atomic
os.rename(), the filename will actually be a temporary file, and it will be
atomically replaced over the destination file on exit.

On systems that don't support an atomic rename, the filename returned is the
filename given.

If an error is encountered, the file is attempted to be removed, and the error
is propagated.

Example:

with FileReplacer("config") as configname:
    with open(configout, 'w') as configout:
        configout.write(newconfig)
"""
class FileReplacer(object):
    __doc__ = doc
    def __init__(self, destname, capabilities=default_caps):
        self.caps = capabilities
        self.destname = destname
        if self.caps.get("rename_works"):
            self.tmpname = destname + ".tmp"
    def __enter__(self):
        if self.caps.get("rename_works"):
            # rename works here. Return a temporary filename
            return self.tmpname
        return self.destname
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.caps.get("rename_works"):
            if exc_type:
                # error
                try:
                    os.remove(self.tmpname)
                except Exception, e:
                    logging.warning("An error was raised, so I was doing "
                            "some cleanup first, but I couldn't remove "
                            "'%s'!", self.tmpname)
            else:
                # copy permission bits, if needed
                if self.caps.get("chmod_works") and os.path.exists(self.destname):
                    shutil.copymode(self.destname, self.tmpname)
                # atomic rename into place
                os.rename(self.tmpname, self.destname)

########NEW FILE########
__FILENAME__ = items
items = {
    0: 'Air',
    1: 'Stone',
    2: 'Grass Block',
    3: 'Dirt',
    4: 'Cobblestone',
    5: 'Wooden Planks',
    6: 'Sapling',
    7: 'Bedrock',
    8: 'Water',
    9: 'Stationary Water',
    10: 'Lava',
    11: 'Stationary Lava',
    12: 'Sand',
    13: 'Gravel',
    14: 'Gold Ore',
    15: 'Iron Ore',
    16: 'Coal Ore',
    17: 'Wood',
    18: 'Leaves',
    19: 'Sponge',
    20: 'Glass',
    21: 'Lapis Lazuli Ore',
    22: 'Lapis Lazuli Block',
    23: 'Dispenser',
    24: 'Sandstone',
    25: 'Note Block',
    26: 'Bed',
    27: 'Powered Rail',
    28: 'Detector Rail',
    29: 'Sticky Piston',
    30: 'Cobweb',
    31: 'Shrub',
    32: 'Dead Bush',
    33: 'Piston',
    34: 'Piston Extension',
    35: 'Wool',
    36: 'Block moved by Piston',
    37: 'Dandelion',
    38: 'Poppy',
    39: 'Brown Mushroom',
    40: 'Red Mushroom',
    41: 'Block of Gold',
    42: 'Block of Iron',
    43: 'Double Stone Slab',
    44: 'Stone Slab',
    45: 'Bricks',
    46: 'TNT',
    47: 'Bookshelf',
    48: 'Moss Stone',
    49: 'Obsidian',
    50: 'Torch',
    51: 'Fire',
    52: 'Monster Spawner',
    53: 'Oak Wood Stairs',
    54: 'Chest',
    55: 'Redstone wire',
    56: 'Diamond ore',
    57: 'Block of Diamond',
    58: 'Crafting Table',
    59: 'Crops',
    60: 'Farmland',
    61: 'Furnace',
    62: 'Burning furnace',
    63: 'Sign',
    64: 'Wooden door',
    65: 'Ladder',
    66: 'Rail',
    67: 'Cobblestone Stairs',
    68: 'Wall sign',
    69: 'Lever',
    70: 'Stone Pressure Plate',
    71: 'Iron door',
    72: 'Wooden Pressure Plate',
    73: 'Redstone Ore',
    74: 'Glowing Redstone Ore',
    75: 'Redstone Torch (off)',
    76: 'Redstone Torch (on)',
    77: 'Stone Button',
    78: 'Snow',
    79: 'Ice',
    80: 'Snow Block',
    81: 'Cactus',
    82: 'Clay Block',
    83: 'Sugar Cane',
    84: 'Jukebox',
    85: 'Fence',
    86: 'Pumpkin',
    87: 'Netherrack',
    88: 'Soul Sand',
    89: 'Glowstone',
    90: 'Nether Portal',
    91: 'Jack o\'Lantern',
    92: 'Cake',
    93: 'Redstone Repeater (off)',
    94: 'Redstone Repeater (on)',
    95: 'Locked Chest',
    96: 'Trapdoor',
    97: 'Monster Egg',
    98: 'Stone Bricks',
    99: 'Huge Brown Mushroom',
    100: 'Huge Red Mushroom',
    101: 'Iron Bars',
    102: 'Glass Pane',
    103: 'Melon',
    104: 'Pumpkin Stem',
    105: 'Melon Stem',
    106: 'Vines',
    107: 'Fence Gate',
    108: 'Brick Stairs',
    109: 'Stone Brick Stairs',
    110: 'Mycelium',
    111: 'Lily Pad',
    112: 'Nether Brick',
    113: 'Nether Brick Fence',
    114: 'Nether Brick Stairs',
    115: 'Nether Wart',
    116: 'Enchantment Table',
    117: 'Brewing Stand',
    118: 'Cauldron',
    119: 'End Portal',
    120: 'End Portal Block',
    121: 'End Stone',
    122: 'Dragon Egg',
    123: 'Redstone Lamp (off)',
    124: 'Redstone Lamp (on)',
    125: 'Double Wooden Slab',
    126: 'Wooden Slab',
    127: 'Cocoa',
    128: 'Sandstone Stairs',
    129: 'Emerald Ore',
    130: 'Ender Chest',
    131: 'Tripwire Hook',
    132: 'Tripwire',
    133: 'Block of Emerald',
    134: 'Spruce Wood Stairs',
    135: 'Birch Wood Stairs',
    136: 'Jungle Wood Stairs',
    137: 'Command Block',
    138: 'Beacon',
    139: 'Cobblestone Wall',
    140: 'Flower Pot',
    141: 'Carrots',
    142: 'Potatoes',
    143: 'Wooden Button',
    144: 'Mob Head',
    145: 'Anvil',
    146: 'Trapped Chest',
    147: 'Weighted Pressure Plate (Light)',
    148: 'Weighted Pressure Plate (Heavy)',
    149: 'Redstone Comparator (off)',
    150: 'Redstone Comparator (on)',
    151: 'Daylight Sensor',
    152: 'Block of Redstone',
    153: 'Nether Quartz Ore',
    154: 'Hopper',
    155: 'Block of Quartz',
    156: 'Quartz Stairs',
    157: 'Activator Rail',
    158: 'Dropper',
    159: 'Stained Clay',
    170: 'Hay Block',
    171: 'Carpet',
    172: 'Hardened Clay',
    173: 'Block of Coal',
    174: 'Packed Ice',
    175: 'Large Flowers',
    256: 'Iron Shovel',
    257: 'Iron Pickaxe',
    258: 'Iron Axe',
    259: 'Flint and Steel',
    260: 'Apple',
    261: 'Bow',
    262: 'Arrow',
    263: 'Coal',
    264: 'Diamond',
    265: 'Iron Ingot',
    266: 'Gold Ingot',
    267: 'Iron Sword',
    268: 'Wooden Sword',
    269: 'Wooden Shovel',
    270: 'Wooden Pickaxe',
    271: 'Wooden Axe',
    272: 'Stone Sword',
    273: 'Stone Shovel',
    274: 'Stone Pickaxe',
    275: 'Stone Axe',
    276: 'Diamond Sword',
    277: 'Diamond Shovel',
    278: 'Diamond Pickaxe',
    279: 'Diamond Axe',
    280: 'Stick',
    281: 'Bowl',
    282: 'Mushroom Stew',
    283: 'Gold Sword',
    284: 'Gold Shovel',
    285: 'Gold Pickaxe',
    286: 'Gold Axe',
    287: 'String',
    288: 'Feather',
    289: 'Gunpowder',
    290: 'Wooden Hoe',
    291: 'Stone Hoe',
    292: 'Iron Hoe',
    293: 'Diamond Hoe',
    294: 'Gold Hoe',
    295: 'Seeds',
    296: 'Wheat',
    297: 'Bread',
    298: 'Leather Cap',
    299: 'Leather Tunic',
    300: 'Leather Pants',
    301: 'Leather Boots',
    302: 'Chain Helmet',
    303: 'Chain Chestplate',
    304: 'Chain Leggings',
    305: 'Chain Boots',
    306: 'Iron Helmet',
    307: 'Iron Chestplate',
    308: 'Iron Leggings',
    309: 'Iron Boots',
    310: 'Diamond Helmet',
    311: 'Diamond Chestplate',
    312: 'Diamond Leggings',
    313: 'Diamond Boots',
    314: 'Gold Helmet',
    315: 'Gold Chestplate',
    316: 'Gold Leggings',
    317: 'Gold Boots',
    318: 'Flint',
    319: 'Raw Porkchop',
    320: 'Cooked Porkchop',
    321: 'Painting',
    322: 'Golden Apple',
    323: 'Sign',
    324: 'Wooden Door',
    325: 'Bucket',
    326: 'Water Bucket',
    327: 'Lava Bucket',
    328: 'Minecart',
    329: 'Saddle',
    330: 'Iron Door',
    331: 'Redstone',
    332: 'Snowball',
    333: 'Boat',
    334: 'Leather',
    335: 'Milk',
    336: 'Brick',
    337: 'Clay',
    338: 'Sugar Canes',
    339: 'Paper',
    340: 'Book',
    341: 'Slimeball',
    342: 'Minecart with Chest',
    343: 'Minecart with Furnace',
    344: 'Egg',
    345: 'Compass',
    346: 'Fishing Rod',
    347: 'Clock',
    348: 'Glowstone Dust',
    349: 'Raw Fish',
    350: 'Cooked Fish',
    351: 'Dye',
    352: 'Bone',
    353: 'Sugar',
    354: 'Cake',
    355: 'Bed',
    356: 'Redstone Repeater',
    357: 'Cookie',
    358: 'Map',
    359: 'Shears',
    360: 'Melon',
    361: 'Pumpkin Seeds',
    362: 'Melon Seeds',
    363: 'Raw Beef',
    364: 'Steak',
    365: 'Raw Chicken',
    366: 'Cooked Chicken',
    367: 'Rotten Flesh',
    368: 'Ender Pearl',
    369: 'Blaze Rod',
    370: 'Ghast Tear',
    371: 'Gold Nugget',
    372: 'Nether Wart',
    373: 'Water Bottle / Potion',
    374: 'Glass Bottle',
    375: 'Spider Eye',
    376: 'Fermented Spider Eye',
    377: 'Blaze Powder',
    378: 'Magma Cream',
    379: 'Brewing Stand',
    380: 'Cauldron',
    381: 'Eye of Ender',
    382: 'Glistering Melon',
    383: 'Spawn Egg',
    384: 'Bottle o\' Enchanting',
    385: 'Fire Charge',
    386: 'Book and Quill',
    387: 'Written Book',
    388: 'Emerald',
    389: 'Item Frame',
    390: 'Flower Pot',
    391: 'Carrot',
    392: 'Potato',
    393: 'Baked Potato',
    394: 'Poisonous Potato',
    395: 'Empty Map',
    396: 'Golden Carrot',
    397: 'Mob Head',
    398: 'Carrot on a Stick',
    399: 'Nether Star',
    400: 'Pumpkin Pie',
    401: 'Firework Rocket',
    402: 'Firework Star',
    403: 'Enchanted Book',
    404: 'Redstone Comparator',
    405: 'Nether Brick',
    406: 'Nether Quartz',
    407: 'Minecart with TNT',
    408: 'Minecart with Hopper',
    417: 'Iron Horse Armor',
    418: 'Gold Horse Armor',
    419: 'Diamond Horse Armor',
    420: 'Lead',
    421: 'Name Tag',
    422: 'Minecart with Command Block',
    2256: 'C418 - 13 Music Disc',
    2257: 'C418 - Cat Music Disc',
    2258: 'C418 - blocks Music Disc',
    2259: 'C418 - chirp Music Disc',
    2260: 'C418 - far Music Disc',
    2261: 'C418 - mall Music Disc',
    2262: 'C418 - mellohi Music Disc',
    2263: 'C418 - stal Music Disc',
    2264: 'C418 - strad Music Disc',
    2265: 'C418 - ward Music Disc',
    2266: 'C418 - 11 Music Disc',
    2267: 'C418 - wait Music Disc',
}

def id2item(item_id):
    if item_id in items:
        return items[item_id]
    else:
        return item_id

########NEW FILE########
__FILENAME__ = logger
#    This file is part of the Minecraft Overviewer.
#
#    Minecraft Overviewer is free software: you can redistribute it and/or
#    modify it under the terms of the GNU General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or (at
#    your option) any later version.
#
#    Minecraft Overviewer is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General
#    Public License for more details.
#
#    You should have received a copy of the GNU General Public License along
#    with the Overviewer.  If not, see <http://www.gnu.org/licenses/>.

import sys
import os
import logging
import platform
import ctypes
from cStringIO import StringIO

# Some cool code for colored logging:
# For background, add 40. For foreground, add 30
BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE = range(8)

RESET_SEQ = "\033[0m"
COLOR_SEQ = "\033[1;%dm"
BOLD_SEQ = "\033[1m"

# Windows colors, taken from WinCon.h
FOREGROUND_BLUE   = 0x01
FOREGROUND_GREEN  = 0x02
FOREGROUND_RED    = 0x04
FOREGROUND_BOLD   = 0x08
FOREGROUND_WHITE  = FOREGROUND_BLUE | FOREGROUND_GREEN | FOREGROUND_RED

BACKGROUND_BLACK  = 0x00
BACKGROUND_BLUE   = 0x10
BACKGROUND_GREEN  = 0x20
BACKGROUND_RED    = 0x40

COLORIZE = {
    #'INFO': WHITe,
    'DEBUG': CYAN,
}
HIGHLIGHT = {
    'CRITICAL': RED,
    'ERROR': RED,
    'WARNING': YELLOW,
}


class WindowsOutputStream(object):
    """A file-like object that proxies sys.stderr and interprets simple ANSI
    escape codes for color, translating them to the appropriate Windows calls.

    """
    def __init__(self, stream=None):
        assert platform.system() == 'Windows'
        self.stream = stream or sys.stderr

        # go go gadget ctypes 
        self.GetStdHandle = ctypes.windll.kernel32.GetStdHandle
        self.SetConsoleTextAttribute = ctypes.windll.kernel32.SetConsoleTextAttribute
        self.STD_OUTPUT_HANDLE = ctypes.c_int(0xFFFFFFF5)
        self.output_handle = self.GetStdHandle(self.STD_OUTPUT_HANDLE)
        if self.output_handle == 0xFFFFFFFF:
            raise Exception("Something failed in WindowsColorFormatter")


        # default is white text on a black background
        self.currentForeground = FOREGROUND_WHITE
        self.currentBackground = BACKGROUND_BLACK
        self.currentBold       = 0

    def updateWinColor(self, Fore=None, Back=None, Bold=False):
        if Fore != None: self.currentForeground = Fore
        if Back != None: self.currentBackground = Back
        if Bold: 
            self.currentBold = FOREGROUND_BOLD
        else:
            self.currentBold = 0

        self.SetConsoleTextAttribute(self.output_handle,
                ctypes.c_int(self.currentForeground | self.currentBackground | self.currentBold))

    def write(self, s):

        msg_strm = StringIO(s) 
    
        while (True):
            c = msg_strm.read(1)
            if c == '': break
            if c == '\033':
                c1 = msg_strm.read(1)
                if c1 != '[': # 
                    sys.stream.write(c + c1)
                    continue
                c2 = msg_strm.read(2)
                if c2 == "0m": # RESET_SEQ
                    self.updateWinColor(Fore=FOREGROUND_WHITE, Back=BACKGROUND_BLACK)

                elif c2 == "1;":
                    color = ""
                    while(True):
                        nc = msg_strm.read(1)
                        if nc == 'm': break
                        color += nc
                    color = int(color) 
                    if (color >= 40): # background
                        color = color - 40
                        if color == BLACK:
                            self.updateWinColor(Back=BACKGROUND_BLACK)
                        if color == RED:
                            self.updateWinColor(Back=BACKGROUND_RED)
                        elif color == GREEN:
                            self.updateWinColor(Back=BACKGROUND_GREEN)
                        elif color == YELLOW:
                            self.updateWinColor(Back=BACKGROUND_RED | BACKGROUND_GREEN)
                        elif color == BLUE:
                            self.updateWinColor(Back=BACKGROUND_BLUE)
                        elif color == MAGENTA:
                            self.updateWinColor(Back=BACKGROUND_RED | BACKGROUND_BLUE)
                        elif color == CYAN:
                            self.updateWinColor(Back=BACKGROUND_GREEN | BACKGROUND_BLUE)
                        elif color == WHITE:
                            self.updateWinColor(Back=BACKGROUND_RED | BACKGROUND_GREEN | BACKGROUND_BLUE)
                    elif (color >= 30): # foreground
                        color = color - 30
                        if color == BLACK:
                            self.updateWinColor(Fore=FOREGROUND_BLACK)
                        if color == RED:
                            self.updateWinColor(Fore=FOREGROUND_RED)
                        elif color == GREEN:
                            self.updateWinColor(Fore=FOREGROUND_GREEN)
                        elif color == YELLOW:
                            self.updateWinColor(Fore=FOREGROUND_RED | FOREGROUND_GREEN)
                        elif color == BLUE:
                            self.updateWinColor(Fore=FOREGROUND_BLUE)
                        elif color == MAGENTA:
                            self.updateWinColor(Fore=FOREGROUND_RED | FOREGROUND_BLUE)
                        elif color == CYAN:
                            self.updateWinColor(Fore=FOREGROUND_GREEN | FOREGROUND_BLUE)
                        elif color == WHITE:
                            self.updateWinColor(Fore=FOREGROUND_WHITE)

                         
                    
                elif c2 == "1m": # BOLD_SEQ
                    pass
                
            else:
                self.stream.write(c)



    def flush(self):
        self.stream.flush()

class HighlightingFormatter(logging.Formatter):
    """Base class of our custom formatter
    
    """
    datefmt = "%Y-%m-%d %H:%M:%S"
    funcName_len = 15

    def __init__(self, verbose=False):
        if verbose:
            fmtstr = '%(fileandlineno)-18s %(pid)s %(asctime)s ' \
                    '%(levelname)-8s %(message)s'
        else:
            fmtstr = '%(asctime)s ' '%(shortlevelname)-1s%(message)s'

        logging.Formatter.__init__(self, fmtstr, self.datefmt)

    def format(self, record):
        """Add a few extra options to the record

        pid
            The process ID

        fileandlineno
            A combination filename:linenumber string, so it can be justified as
            one entry in a format string.

        funcName
            The function name truncated/padded to a fixed width characters

        shortlevelname
            The level name truncated to 1 character
        
        """

        record.shortlevelname = record.levelname[0] + ' ' 
        if record.levelname == 'INFO': record.shortlevelname = ''

        record.pid = os.getpid()
        record.fileandlineno = "%s:%s" % (record.filename, record.lineno)

        # Set the max length for the funcName field, and left justify
        l = self.funcName_len
        record.funcName = ("%-" + str(l) + 's') % record.funcName[:l]

        return self.highlight(record)

    def highlight(self, record):
        """This method applies any special effects such as colorization. It
        should modify the records in the record object, and should return the
        *formatted line*. This probably involves calling
        logging.Formatter.format()

        Override this in subclasses

        """
        return logging.Formatter.format(self, record)

class DumbFormatter(HighlightingFormatter):
    """Formatter for dumb terminals that don't support color, or log files.
    Prints a bunch of stars before a highlighted line.

    """
    def highlight(self, record):
        if record.levelname in HIGHLIGHT:
            line = logging.Formatter.format(self, record)
            line = "*" * min(79,len(line)) + "\n" + line
            return line
        else:
            return HighlightingFormatter.highlight(self, record)


class ANSIColorFormatter(HighlightingFormatter):
    """Uses ANSI escape sequences to enable GLORIOUS EXTRA-COLOR!

    """
    def highlight(self, record):
        if record.levelname in COLORIZE:
            # Colorize just the levelname
            # left justify again because the color sequence bumps the length up
            # above 8 chars
            levelname_color = COLOR_SEQ % (30 + COLORIZE[record.levelname]) + \
                    "%-8s" % record.levelname + RESET_SEQ
            record.levelname = levelname_color
            return logging.Formatter.format(self, record)

        elif record.levelname in HIGHLIGHT:
            # Colorize the entire line
            line = logging.Formatter.format(self, record)
            line = COLOR_SEQ % (40 + HIGHLIGHT[record.levelname]) + line + \
                    RESET_SEQ
            return line

        else:
            # No coloring if it's not to be highlighted or colored
            return logging.Formatter.format(self, record)

def configure(loglevel=logging.INFO, verbose=False, simple=False):
    """Configures the root logger to our liking

    For a non-standard loglevel, pass in the level with which to configure the handler.

    For a more verbose options line, pass in verbose=True

    This function may be called more than once.

    """

    logger = logging.getLogger()

    outstream = sys.stdout
    if simple:
        formatter = DumbFormatter(verbose)

    elif platform.system() == 'Windows':
        # Our custom output stream processor knows how to deal with select ANSI
        # color escape sequences
        outstream = WindowsOutputStream(outstream)
        formatter = ANSIColorFormatter(verbose)

    elif outstream.isatty():
        # terminal logging with ANSI color
        formatter = ANSIColorFormatter(verbose)

    else:
        # Let's not assume anything. Just text.
        formatter = DumbFormatter(verbose)

    if hasattr(logger, 'overviewerHandler'):
        # we have already set up logging so just replace the formatter
        # this time with the new values
        logger.overviewerHandler.setFormatter(formatter)
        logger.setLevel(loglevel)

    else:
        # Save our handler here so we can tell which handler was ours if the
        # function is called again
        logger.overviewerHandler = logging.StreamHandler(outstream)
        logger.overviewerHandler.setFormatter(formatter)
        logger.addHandler(logger.overviewerHandler)
        logger.setLevel(loglevel)

########NEW FILE########
__FILENAME__ = nbt
#    This file is part of the Minecraft Overviewer.
#
#    Minecraft Overviewer is free software: you can redistribute it and/or
#    modify it under the terms of the GNU General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or (at
#    your option) any later version.
#
#    Minecraft Overviewer is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General
#    Public License for more details.
#
#    You should have received a copy of the GNU General Public License along
#    with the Overviewer.  If not, see <http://www.gnu.org/licenses/>.

import gzip, zlib
import struct
import StringIO
import functools

# decorator that turns the first argument from a string into an open file
# handle
def _file_loader(func):
    @functools.wraps(func)
    def wrapper(fileobj, *args):
        if isinstance(fileobj, basestring):
            # Is actually a filename
            fileobj = open(fileobj, 'rb', 4096)
        return func(fileobj, *args)
    return wrapper

@_file_loader
def load(fileobj):
    """Reads in the given file as NBT format, parses it, and returns the
    result as a (name, data) tuple.    
    """
    return NBTFileReader(fileobj).read_all()

@_file_loader
def load_region(fileobj):
    """Reads in the given file as a MCR region, and returns an object
    for accessing the chunks inside."""
    return MCRFileReader(fileobj)


class CorruptionError(Exception):
    pass
class CorruptRegionError(CorruptionError):
    """An exception raised when the MCRFileReader class encounters an
    error during region file parsing.
    """
    pass
class CorruptChunkError(CorruptionError):
    pass
class CorruptNBTError(CorruptionError):
    """An exception raised when the NBTFileReader class encounters
    something unexpected in an NBT file."""
    pass

class NBTFileReader(object):
    """Low level class that reads the Named Binary Tag format used by Minecraft

    """
    
    # compile the unpacker's into a classes
    _byte   = struct.Struct("b")
    _short  = struct.Struct(">h")
    _int    = struct.Struct(">i")
    _long   = struct.Struct(">q")
    _float  = struct.Struct(">f")
    _double = struct.Struct(">d") 
 
    def __init__(self, fileobj, is_gzip=True):
        """Create a NBT parsing object with the given file-like
        object. Setting is_gzip to False parses the file as a zlib
        stream instead."""
        if is_gzip:
            self._file = gzip.GzipFile(fileobj=fileobj, mode='rb')
        else:
            # pure zlib stream -- maybe later replace this with
            # a custom zlib file object?
            data = zlib.decompress(fileobj.read())
            self._file = StringIO.StringIO(data)

        # mapping of NBT type ids to functions to read them out
        self._read_tagmap = {
            0: self._read_tag_end,
            1: self._read_tag_byte,
            2: self._read_tag_short,
            3: self._read_tag_int,
            4: self._read_tag_long,
            5: self._read_tag_float,
            6: self._read_tag_double,
            7: self._read_tag_byte_array,
            8: self._read_tag_string,
            9: self._read_tag_list,
            10:self._read_tag_compound,
            11:self._read_tag_int_array,
        }

    # These private methods read the payload only of the following types
    def _read_tag_end(self):
        # Nothing to read
        return 0

    def _read_tag_byte(self):
        byte = self._file.read(1)
        return self._byte.unpack(byte)[0]
    
    def _read_tag_short(self):
        bytes = self._file.read(2)
        return self._short.unpack(bytes)[0]

    def _read_tag_int(self):
        bytes = self._file.read(4)
        return self._int.unpack(bytes)[0]

    def _read_tag_long(self):
        bytes = self._file.read(8)
        return self._long.unpack(bytes)[0]

    def _read_tag_float(self):
        bytes = self._file.read(4)
        return self._float.unpack(bytes)[0]

    def _read_tag_double(self):
        bytes = self._file.read(8)
        return self._double.unpack(bytes)[0]

    def _read_tag_byte_array(self):
        length = self._read_tag_int()
        bytes = self._file.read(length)
        return bytes

    def _read_tag_int_array(self):
        length = self._read_tag_int()
        int_bytes = self._file.read(length*4)
        return struct.unpack(">%ii" % length, int_bytes)

    def _read_tag_string(self):
        length = self._read_tag_short()
        # Read the string
        string = self._file.read(length)
        # decode it and return
        return string.decode("UTF-8")

    def _read_tag_list(self):
        tagid = self._read_tag_byte()
        length = self._read_tag_int()

        read_method = self._read_tagmap[tagid]
        l = []
        for _ in xrange(length):
            l.append(read_method())
        return l

    def _read_tag_compound(self):
        # Build a dictionary of all the tag names mapping to their payloads
        tags = {}
        while True:
            # Read a tag
            tagtype = ord(self._file.read(1))

            if tagtype == 0:
                break

            name = self._read_tag_string()
            payload = self._read_tagmap[tagtype]()
            tags[name] = payload

        return tags
    
    def read_all(self):
        """Reads the entire file and returns (name, payload)
        name is the name of the root tag, and payload is a dictionary mapping
        names to their payloads

        """
        # Read tag type
        try:
            tagtype = ord(self._file.read(1))
            if tagtype != 10:
                raise Exception("Expected a tag compound")
            
            # Read the tag name
            name = self._read_tag_string()
            payload = self._read_tag_compound()
            
            return (name, payload)
        except (struct.error, ValueError), e:
            raise CorruptNBTError("could not parse nbt: %s" % (str(e),))

# For reference, the MCR format is outlined at
# <http://www.minecraftwiki.net/wiki/Beta_Level_Format>
class MCRFileReader(object):
    """A class for reading chunk region files, as introduced in the
    Beta 1.3 update. It provides functions for opening individual
    chunks (as (name, data) tuples), getting chunk timestamps, and for
    listing chunks contained in the file.
    """
    
    _location_table_format = struct.Struct(">1024I")
    _timestamp_table_format = struct.Struct(">1024i")
    _chunk_header_format = struct.Struct(">I B")
    
    def __init__(self, fileobj):
        """This creates a region object from the given file-like
        object. Chances are you want to use load_region instead."""
        self._file = fileobj
        
        # read in the location table
        location_data = self._file.read(4096)
        if not len(location_data) == 4096:
            raise CorruptRegionError("invalid location table")
        # read in the timestamp table
        timestamp_data = self._file.read(4096)
        if not len(timestamp_data) == 4096:
            raise CorruptRegionError("invalid timestamp table")

        # turn this data into a useful list
        self._locations = self._location_table_format.unpack(location_data)
        self._timestamps = self._timestamp_table_format.unpack(timestamp_data)

    def close(self):
        """Close the region file and free any resources associated
        with keeping it open. Using this object after closing it
        results in undefined behaviour.
        """
        
        self._file.close()
        self._file = None

    def get_chunks(self):    
        """Return an iterator of all chunks contained in this region
        file, as (x, z) coordinate tuples. To load these chunks,
        provide these coordinates to load_chunk()."""
        
        for x in xrange(32): 
            for z in xrange(32): 
                if self._locations[x + z * 32] >> 8 != 0:
                    yield (x,z)
        
    def get_chunk_timestamp(self, x, z):
        """Return the given chunk's modification time. If the given
        chunk doesn't exist, this number may be nonsense. Like
        load_chunk(), this will wrap x and z into the range [0, 31].
        """
        x = x % 32
        z = z % 32        
        return self._timestamps[x + z * 32]   
    
    def chunk_exists(self, x, z):
        """Determines if a chunk exists."""
        x = x % 32
        z = z % 32
        return self._locations[x + z * 32] >> 8 != 0

    def load_chunk(self, x, z):
        """Return a (name, data) tuple for the given chunk, or
        None if the given chunk doesn't exist in this region file. If
        you provide an x or z not between 0 and 31, it will be
        modulo'd into this range (x % 32, etc.) This is so you can
        provide chunk coordinates in global coordinates, and still
        have the chunks load out of regions properly."""
        x = x % 32
        z = z % 32
        location = self._locations[x + z * 32]
        offset = (location >> 8) * 4096;
        sectors = location & 0xff;
        
        if offset == 0:
            return None
        
        # seek to the data
        self._file.seek(offset)
        
        # read in the chunk data header
        header = self._file.read(5)
        if len(header) != 5:
            raise CorruptChunkError("chunk header is invalid")
        data_length, compression =  self._chunk_header_format.unpack(header)
        
        # figure out the compression
        is_gzip = True
        if compression == 1:
            # gzip -- not used by the official client, but trivial to support here so...
            is_gzip = True
        elif compression == 2:
            # deflate -- pure zlib stream
            is_gzip = False
        else:
            # unsupported!
            raise CorruptRegionError("unsupported chunk compression type: %i (should be 1 or 2)" % (compression,))
        
        # turn the rest of the data into a StringIO object
        # (using data_length - 1, as we already read 1 byte for compression)
        data = self._file.read(data_length - 1)
        if len(data) != data_length - 1:
            raise CorruptRegionError("chunk length is invalid")
        data = StringIO.StringIO(data)
        
        try:
            return NBTFileReader(data, is_gzip=is_gzip).read_all()
        except CorruptionError:
            raise
        except Exception, e:
            raise CorruptChunkError("Misc error parsing chunk: " + str(e))

########NEW FILE########
__FILENAME__ = observer
#    This file is part of the Minecraft Overviewer.
#
#    Minecraft Overviewer is free software: you can redistribute it and/or
#    modify it under the terms of the GNU General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or (at
#    your option) any later version.
#
#    Minecraft Overviewer is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General
#    Public License for more details.
#
#    You should have received a copy of the GNU General Public License along
#    with the Overviewer.  If not, see <http://www.gnu.org/licenses/>.

import time
import logging
import progressbar
import sys
import os
import json

class Observer(object):
    """Base class that defines the observer interface.
    """

    def __init__(self):
        self._current_value = None
        self._max_value = None
        self.start_time = None
        self.end_time = None

    def start(self, max_value):
        """Signals the start of whatever process. Must be called before update
        """
        self._set_max_value(max_value)
        self.start_time = time.time()
        self.update(0)
        return self

    def is_started(self):
        return self.start_time is not None

    def finish(self):
        """Signals the end of the processes, should be called after the
        process is done.
        """
        self.end_time = time.time()

    def is_finished(self):
        return self.end_time is not None

    def is_running(self):
        return self.is_started() and not self.is_finished()

    def add(self, amount):
        """Shortcut to update by increments instead of absolute values. Zero
        amounts are ignored.
        """
        if amount:
            self.update(self.get_current_value() + amount)

    def update(self, current_value):
        """Set the progress value. Should be between 0 and max_value. Returns
        whether this update is actually displayed.
        """
        self._current_value = current_value
        return False

    def get_percentage(self):
        """Get the current progress percentage. Assumes 100% if max_value is 0
        """
        if self.get_max_value() is 0:
            return 100.0
        else:
            return self.get_current_value() * 100.0 / self.get_max_value()

    def get_current_value(self):
        return self._current_value

    def get_max_value(self):
        return self._max_value

    def _set_max_value(self, max_value):
        self._max_value = max_value

class LoggingObserver(Observer):
    """Simple observer that just outputs status through logging.
    """
    def __init__(self):
        super(Observer, self).__init__()
        #this is an easy way to make the first update() call print a line
        self.last_update = -101

    def finish(self):
        logging.info("Rendered %d of %d.  %d%% complete", self.get_max_value(),
            self.get_max_value(), 100.0)
        super(LoggingObserver, self).finish()

    def update(self, current_value):
        super(LoggingObserver, self).update(current_value)
        if self._need_update():
            logging.info("Rendered %d of %d.  %d%% complete",
                self.get_current_value(), self.get_max_value(),
                self.get_percentage())
            self.last_update = current_value
            return True
        return False

    def _need_update(self):
        cur_val = self.get_current_value()
        if cur_val < 100:
            return cur_val - self.last_update > 10
        elif cur_val < 500:
            return cur_val - self.last_update > 50
        else:
            return cur_val - self.last_update > 100

default_widgets = [
    progressbar.Percentage(), ' ',
    progressbar.Bar(marker='=', left='[', right=']'), ' ',
    progressbar.CounterWidget(), ' ',
    progressbar.GenericSpeed(format='%.2ft/s'), ' ',
    progressbar.ETA(prefix='eta ')
]
class ProgressBarObserver(progressbar.ProgressBar, Observer):
    """Display progress through a progressbar.
    """

    #the progress bar is only updated in increments of this for performance
    UPDATE_INTERVAL = 25

    def __init__(self, widgets=default_widgets, term_width=None, fd=sys.stderr):
        super(ProgressBarObserver, self).__init__(widgets=widgets,
            term_width=term_width, fd=fd)
        self.last_update = 0 - (self.UPDATE_INTERVAL + 1)

    def start(self, max_value):
        self._set_max_value(max_value)
        logging.info("Rendering %d total tiles." % max_value)
        super(ProgressBarObserver, self).start()

    def is_started(self):
        return self.start_time is not None

    def finish(self):
        self._end_time = time.time()
        super(ProgressBarObserver, self).finish()
        self.fd.write('\n')
        logging.info("Rendering complete!")

    def update(self, current_value):
        # maxval is an estimate, and progressbar barfs if currval > maxval
        # so...
        current_value = min(current_value, self.maxval)
        if super(ProgressBarObserver, self).update(current_value):
            self.last_update = self.get_current_value()

    percentage = Observer.get_percentage

    def get_current_value(self):
        return self.currval

    def get_max_value(self):
        return self.maxval

    def _set_max_value(self, max_value):
        self.maxval = max_value

    def _need_update(self):
        return self.get_current_value() - self.last_update > self.UPDATE_INTERVAL

class JSObserver(Observer):
    """Display progress on index.html using JavaScript
    """

    def __init__(self, outputdir, minrefresh=5, messages=False):
        """Initialise observer
        outputdir must be set to the map output directory path
        minrefresh specifies the minimum gap between requests, in seconds [optional]
        messages is a dictionary which allows the displayed messages to be customised [optional]
        """
        self.last_update = -11
        self.last_update_time = -1 
        self._current_value = -1
        self.minrefresh = 1000*minrefresh
        self.json = dict()
        
        # function to print formatted eta
        self.format = lambda seconds: '%02ih %02im %02is' % \
            (seconds // 3600, (seconds % 3600) // 60, seconds % 60)

        if (messages == False):
            self.messages=dict(totalTiles="Rendering %d tiles", renderCompleted="Render completed in %02d:%02d:%02d", renderProgress="Rendered %d of %d tiles (%d%% ETA:%s)")
        elif (isinstance(messages, dict)):
            if ('totalTiles' in messages and 'renderCompleted' in messages and 'renderProgress' in messages):
                self.messages = messages
            else:
                raise Exception("JSObserver: messages parameter must be a dictionary with three entries: totalTiles, renderCompleted and renderProgress")
        else:
            raise Exception("JSObserver: messages parameter must be a dictionary with three entries: totalTiles, renderCompleted and renderProgress")
        if not os.path.exists(outputdir):
            raise Exception("JSObserver: Output directory specified (%s) doesn't appear to exist. This should be the same as the Overviewer output directory")

        self.logfile = open(os.path.join(outputdir, "progress.json"), "w+", 0)
        self.json["message"]="Render starting..."
        self.json["update"]=self.minrefresh
        self.json["messageTime"]=time.time()
        json.dump(self.json, self.logfile)
        self.logfile.flush()

    def start(self, max_value):
        self.logfile.seek(0)
        self.logfile.truncate()
        self.json["message"] = self.messages["totalTiles"] % (max_value)
        self.json["update"] = self.minrefresh
        self.json["messageTime"] = time.time()
        json.dump(self.json, self.logfile)
        self.logfile.flush()
        self.start_time=time.time()
        self._set_max_value(max_value)

    def is_started(self):
        return self.start_time is not None

    def finish(self):
        """Signals the end of the processes, should be called after the
        process is done.
        """
        self.end_time = time.time()
        duration = self.end_time - self.start_time
        self.logfile.seek(0)
        self.logfile.truncate()
        hours = duration // 3600
        duration = duration % 3600
        minutes = duration // 60
        seconds = duration % 60
        self.json["message"] = self.messages["renderCompleted"] % (hours, minutes, seconds)
        self.json["update"] = 60000 # The 'renderCompleted' message will always be visible (until the next render)
        self.json["messageTime"] = time.time()
        json.dump(self.json, self.logfile)
        self.logfile.close()

    def is_finished(self):
        return self.end_time is not None

    def is_running(self):
        return self.is_started() and not self.is_finished()

    def add(self, amount):
        """Shortcut to update by increments instead of absolute values. Zero
        amounts are ignored.
        """
        if amount:
            self.update(self.get_current_value() + amount)

    def update(self, current_value):
        """Set the progress value. Should be between 0 and max_value. Returns
        whether this update is actually displayed.
        """
        self._current_value = current_value
        if self._need_update():
            refresh = max(1500*(time.time() - self.last_update_time), self.minrefresh) // 1
            self.logfile.seek(0)
            self.logfile.truncate()
            if self.get_current_value():
                duration = time.time() - self.start_time
                eta = self.format(duration * self.get_max_value() / self.get_current_value() - duration)
            else:
                eta = "?"
            self.json["message"] = self.messages["renderProgress"] % (self.get_current_value(), self.get_max_value(), self.get_percentage(), str(eta))
            self.json["update"] = refresh
            self.json["messageTime"] = time.time()
            json.dump(self.json, self.logfile)
            self.logfile.flush()
            self.last_update_time = time.time()
            self.last_update = current_value
            return True
        return False

    def get_percentage(self):
        """Get the current progress percentage. Assumes 100% if max_value is 0
        """
        if self.get_max_value() is 0:
            return 100.0
        else:
            return self.get_current_value() * 100.0 / self.get_max_value()

    def get_current_value(self):
        return self._current_value

    def get_max_value(self):
        return self._max_value

    def _set_max_value(self, max_value):
        self._max_value = max_value 

    def _need_update(self):
        cur_val = self.get_current_value()
        if cur_val < 100:
            return cur_val - self.last_update > 10
        elif cur_val < 500:
            return cur_val - self.last_update > 50
        else:
            return cur_val - self.last_update > 100

class MultiplexingObserver(Observer):
    """Combine multiple observers into one.
    """
    def __init__(self, *components):
        self.components = components
        super(MultiplexingObserver, self).__init__()

    def start(self, max_value):
        for o in self.components:
            o.start(max_value)
        super(MultiplexingObserver, self).start(max_value)

    def finish(self):
        for o in self.components:
            o.finish()
        super(MultiplexingObserver, self).finish()

    def update(self, current_value):
        for o in self.components:
            o.update(current_value)
        super(MultiplexingObserver, self).update(current_value)

class ServerAnnounceObserver(Observer):
    """Send the output to a Minecraft server via FIFO or stdin"""
    def __init__(self, target='/dev/null', pct_interval=10):
        self.pct_interval = pct_interval
        self.target_handle = open(target, 'w')
        self.last_update = 0
        super(ServerAnnounceObserver, self).__init__()

    def start(self, max_value):
        self._send_output('Starting render of %d total tiles' % max_value)
        super(ServerAnnounceObserver, self).start(max_value)

    def finish(self):
        self._send_output('Render complete!')
        super(ServerAnnounceObserver, self).finish()
        self.target_handle.close()

    def update(self, current_value):
        super(ServerAnnounceObserver, self).update(current_value)
        if self._need_update():
            self._send_output('Rendered %d of %d tiles, %d%% complete' %
                (self.get_current_value(), self.get_max_value(),
                    self.get_percentage()))
            self.last_update = current_value

    def _need_update(self):
        return self.get_percentage() - \
            (self.last_update * 100.0 / self.get_max_value()) >= self.pct_interval

    def _send_output(self, output):
        self.target_handle.write('say %s\n' % output)
        self.target_handle.flush()


########NEW FILE########
__FILENAME__ = optimizeimages
#    This file is part of the Minecraft Overviewer.
#
#    Minecraft Overviewer is free software: you can redistribute it and/or
#    modify it under the terms of the GNU General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or (at
#    your option) any later version.
#
#    Minecraft Overviewer is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General
#    Public License for more details.
#
#    You should have received a copy of the GNU General Public License along
#    with the Overviewer.  If not, see <http://www.gnu.org/licenses/>.

import os
import subprocess
import shlex
import logging

class Optimizer:
    binaryname = ""

    def __init__(self):
        raise NotImplementedError("I can't let you do that, Dave.")

    def optimize(self, img):
        raise NotImplementedError("I can't let you do that, Dave.")
    
    def fire_and_forget(self, args):
        subprocess.check_call(args)

    def check_availability(self):
        path = os.environ.get("PATH").split(os.pathsep)
        
        def exists_in_path(prog):
            result = filter(lambda x: os.path.exists(os.path.join(x, prog)), path)
            return len(result) != 0

        if (not exists_in_path(self.binaryname)) and (not exists_in_path(self.binaryname + ".exe")):
            raise Exception("Optimization program '%s' was not found!" % self.binaryname)
    
    def is_crusher(self):
        """Should return True if the optimization is lossless, i.e. none of the actual image data will be changed."""
        raise NotImplementedError("I'm so abstract I can't even say whether I'm a crusher.")
        

class NonAtomicOptimizer(Optimizer):
    def cleanup(self, img):
        os.remove(img)
        os.rename(img + ".tmp", img)

    def fire_and_forget(self, args, img):
        subprocess.check_call(args)
        self.cleanup(img)

class PNGOptimizer:
    def __init__(self):
        raise NotImplementedError("I can't let you do that, Dave.")

class JPEGOptimizer:
    def __init__(self):
        raise NotImplementedError("I can't let you do that, Dave.")

class pngnq(NonAtomicOptimizer, PNGOptimizer):
    binaryname = "pngnq"

    def __init__(self, sampling=3, dither="n"):
        if sampling < 1 or sampling > 10:
            raise Exception("Invalid sampling value '%d' for pngnq!" % sampling)

        if dither not in ["n", "f"]:
            raise Exception("Invalid dither method '%s' for pngnq!" % dither)

        self.sampling = sampling
        self.dither = dither
    
    def optimize(self, img):
        if img.endswith(".tmp"):
            extension = ".tmp"
        else:
            extension = ".png.tmp"

        args = [self.binaryname, "-s", str(self.sampling), "-f", "-e", extension, img]
        # Workaround for poopbuntu 12.04 which ships an old broken pngnq
        if self.dither != "n":
            args.insert(1, "-Q")
            args.insert(2, self.dither)

        NonAtomicOptimizer.fire_and_forget(self, args, img)

    def is_crusher(self):
        return False

class pngcrush(NonAtomicOptimizer, PNGOptimizer):
    binaryname = "pngcrush"
    # really can't be bothered to add some interface for all
    # the pngcrush options, it sucks anyway
    def __init__(self, brute=False):
        self.brute = brute
        
    def optimize(self, img):
        args = [self.binaryname, img, img + ".tmp"]
        if self.brute == True:  # Was the user an idiot?
            args.insert(1, "-brute")

        NonAtomicOptimizer.fire_and_forget(self, args, img)

    def is_crusher(self):
        return True

class optipng(Optimizer, PNGOptimizer):
    binaryname = "optipng"

    def __init__(self, olevel=2):
        self.olevel = olevel
    
    def optimize(self, img):
        Optimizer.fire_and_forget(self, [self.binaryname, "-o" + str(self.olevel), "-quiet", img])

    def is_crusher(self):
        return True
        

def optimize_image(imgpath, imgformat, optimizers):
        for opt in optimizers:
            if imgformat == 'png':
                if isinstance(opt, PNGOptimizer):
                    opt.optimize(imgpath)
            elif imgformat == 'jpg':
                if isinstance(opt, JPEGOptimizer):
                    opt.optimize(imgpath)

########NEW FILE########
__FILENAME__ = progressbar
#!/usr/bin/python
# -*- coding: iso-8859-1 -*-
#
# progressbar  - Text progressbar library for python.
# Copyright (c) 2005 Nilton Volpato
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA


"""Text progressbar library for python.

This library provides a text mode progressbar. This is tipically used
to display the progress of a long running operation, providing a
visual clue that processing is underway.

The ProgressBar class manages the progress, and the format of the line
is given by a number of widgets. A widget is an object that may
display diferently depending on the state of the progress. There are
three types of widget:
- a string, which always shows itself;
- a ProgressBarWidget, which may return a diferent value every time
it's update method is called; and
- a ProgressBarWidgetHFill, which is like ProgressBarWidget, except it
expands to fill the remaining width of the line.

The progressbar module is very easy to use, yet very powerful. And
automatically supports features like auto-resizing when available.
"""

__author__ = "Nilton Volpato"
__author_email__ = "first-name dot last-name @ gmail.com"
__date__ = "2006-05-07"
__version__ = "2.2"

# Changelog
#
# 2006-05-07: v2.2 fixed bug in windows
# 2005-12-04: v2.1 autodetect terminal width, added start method
# 2005-12-04: v2.0 everything is now a widget (wow!)
# 2005-12-03: v1.0 rewrite using widgets
# 2005-06-02: v0.5 rewrite
# 2004-??-??: v0.1 first version


import sys, time
from array import array
try:
    from fcntl import ioctl
    import termios
except ImportError:
    pass
import signal

class ProgressBarWidget(object):
    """This is an element of ProgressBar formatting.

    The ProgressBar object will call it's update value when an update
    is needed. It's size may change between call, but the results will
    not be good if the size changes drastically and repeatedly.
    """
    def update(self, pbar):
        """Returns the string representing the widget.

        The parameter pbar is a reference to the calling ProgressBar,
        where one can access attributes of the class for knowing how
        the update must be made.

        At least this function must be overriden."""
        pass

class ProgressBarWidgetHFill(object):
    """This is a variable width element of ProgressBar formatting.

    The ProgressBar object will call it's update value, informing the
    width this object must the made. This is like TeX \\hfill, it will
    expand to fill the line. You can use more than one in the same
    line, and they will all have the same width, and together will
    fill the line.
    """
    def update(self, pbar, width):
        """Returns the string representing the widget.

        The parameter pbar is a reference to the calling ProgressBar,
        where one can access attributes of the class for knowing how
        the update must be made. The parameter width is the total
        horizontal width the widget must have.

        At least this function must be overriden."""
        pass


class ETA(ProgressBarWidget):
    "Widget for the Estimated Time of Arrival"
    def __init__(self, prefix='ETA: ', format=None):
        self.prefix = prefix
        if format:
            self.format = format
        else:
            self.format = lambda seconds: '%02ih %02im %02is' % \
                (seconds // 3600, (seconds % 3600) // 60, seconds % 60)

    def update(self, pbar):
        if pbar.finished:
            return 'Time: ' + self.format(pbar.seconds_elapsed)
        else:
            if pbar.currval:
                eta = pbar.seconds_elapsed * pbar.maxval / pbar.currval - pbar.seconds_elapsed
                return self.prefix + self.format(eta)
            else:
                return self.prefix + '-' * 6

class GenericSpeed(ProgressBarWidget):
    "Widget for showing the values/s"
    def __init__(self, format='%6.2f ?/s'):
        if callable(format):
            self.format = format
        else:
            self.format = lambda speed: format % speed
    def update(self, pbar):
        if pbar.seconds_elapsed < 2e-6:
            speed = 0.0
        else:
            speed = float(pbar.currval) / pbar.seconds_elapsed
        return self.format(speed)

class FileTransferSpeed(ProgressBarWidget):
    "Widget for showing the transfer speed (useful for file transfers)."
    def __init__(self):
        self.fmt = '%6.2f %s'
        self.units = ['B','K','M','G','T','P']
    def update(self, pbar):
        if pbar.seconds_elapsed < 2e-6:#== 0:
            bps = 0.0
        else:
            bps = float(pbar.currval) / pbar.seconds_elapsed
        spd = bps
        for u in self.units:
            if spd < 1000:
                break
            spd /= 1000
        return self.fmt % (spd, u+'/s')

class RotatingMarker(ProgressBarWidget):
    "A rotating marker for filling the bar of progress."
    def __init__(self, markers='|/-\\'):
        self.markers = markers
        self.curmark = -1
    def update(self, pbar):
        if pbar.finished:
            return self.markers[0]
        self.curmark = (self.curmark + 1)%len(self.markers)
        return self.markers[self.curmark]

class Percentage(ProgressBarWidget):
    "Just the percentage done."
    def __init__(self, format='%3d%%'):
        self.format = format

    def update(self, pbar):
        return self.format % pbar.percentage()

class CounterWidget(ProgressBarWidget):
    "Simple display of (just) the current value"
    def update(self, pbar):
        return str(pbar.currval)

class FractionWidget(ProgressBarWidget):
    def __init__(self, sep=' / '):
        self.sep = sep
    def update(self, pbar):
        return '%2d%s%2d' % (pbar.currval, self.sep, pbar.maxval)

class Bar(ProgressBarWidgetHFill):
    "The bar of progress. It will strech to fill the line."
    def __init__(self, marker='#', left='|', right='|'):
        self.marker = marker
        self.left = left
        self.right = right
    def _format_marker(self, pbar):
        if isinstance(self.marker, (str, unicode)):
            return self.marker
        else:
            return self.marker.update(pbar)
    def update(self, pbar, width):
        percent = pbar.percentage()
        cwidth = width - len(self.left) - len(self.right)
        marked_width = int(percent * cwidth / 100)
        m = self._format_marker(pbar)
        bar = (self.left + (m*marked_width).ljust(cwidth) + self.right)
        return bar

class ReverseBar(Bar):
    "The reverse bar of progress, or bar of regress. :)"
    def update(self, pbar, width):
        percent = pbar.percentage()
        cwidth = width - len(self.left) - len(self.right)
        marked_width = int(percent * cwidth / 100)
        m = self._format_marker(pbar)
        bar = (self.left + (m*marked_width).rjust(cwidth) + self.right)
        return bar

default_widgets = [Percentage(), ' ', Bar()]
class ProgressBar(object):
    """This is the ProgressBar class, it updates and prints the bar.

    The term_width parameter may be an integer. Or None, in which case
    it will try to guess it, if it fails it will default to 80 columns.

    The simple use is like this:
    >>> pbar = ProgressBar().start()
    >>> for i in xrange(100):
    ...    # do something
    ...    pbar.update(i+1)
    ...
    >>> pbar.finish()

    But anything you want to do is possible (well, almost anything).
    You can supply different widgets of any type in any order. And you
    can even write your own widgets! There are many widgets already
    shipped and you should experiment with them.

    When implementing a widget update method you may access any
    attribute or function of the ProgressBar object calling the
    widget's update method. The most important attributes you would
    like to access are:
    - currval: current value of the progress, 0 <= currval <= maxval
    - maxval: maximum (and final) value of the progress
    - finished: True if the bar is have finished (reached 100%), False o/w
    - start_time: first time update() method of ProgressBar was called
    - seconds_elapsed: seconds elapsed since start_time
    - percentage(): percentage of the progress (this is a method)
    """
    def __init__(self, maxval=100, widgets=default_widgets, term_width=None,
                 fd=sys.stderr):
        assert maxval > 0
        self.maxval = maxval
        self.widgets = widgets
        self.fd = fd
        self.signal_set = False
        if term_width is None:
            try:
                self.handle_resize(None,None)
                signal.signal(signal.SIGWINCH, self.handle_resize)
                signal.siginterrupt(signal.SIGWINCH, False)
                self.signal_set = True
            except:
                self.term_width = 79
        else:
            self.term_width = term_width

        self.currval = 0
        self.finished = False
        self.start_time = None
        self.seconds_elapsed = 0

    def handle_resize(self, signum, frame):
        h,w=array('h', ioctl(self.fd,termios.TIOCGWINSZ,'\0'*8))[:2]
        self.term_width = w

    def percentage(self):
        "Returns the percentage of the progress."
        return self.currval*100.0 / self.maxval

    def _format_widgets(self):
        r = []
        hfill_inds = []
        num_hfill = 0
        currwidth = 0
        for i, w in enumerate(self.widgets):
            if isinstance(w, ProgressBarWidgetHFill):
                r.append(w)
                hfill_inds.append(i)
                num_hfill += 1
            elif isinstance(w, (str, unicode)):
                r.append(w)
                currwidth += len(w)
            else:
                weval = w.update(self)
                currwidth += len(weval)
                r.append(weval)
        for iw in hfill_inds:
            r[iw] = r[iw].update(self, (self.term_width-currwidth)/num_hfill)
        return r

    def _format_line(self):
        return ''.join(self._format_widgets()).ljust(self.term_width)

    def _need_update(self):
        return True

    def update(self, value):
        "Updates the progress bar to a new value."
        assert 0 <= value <= self.maxval
        self.currval = value
        if not self._need_update() or self.finished:
            return False
        if not self.start_time:
            self.start_time = time.time()
        self.seconds_elapsed = time.time() - self.start_time
        if value != self.maxval:
            self.fd.write(self._format_line() + '\r')
        else:
            self.finished = True
            self.fd.write(self._format_line() + '\n')
        return True

    def start(self):
        """Start measuring time, and prints the bar at 0%.

        It returns self so you can use it like this:
        >>> pbar = ProgressBar().start()
        >>> for i in xrange(100):
        ...    # do something
        ...    pbar.update(i+1)
        ...
        >>> pbar.finish()
        """
        self.update(0)
        return self

    def finish(self):
        """Used to tell the progress is finished."""
        self.update(self.maxval)
        if self.signal_set:
            signal.signal(signal.SIGWINCH, signal.SIG_DFL)






if __name__=='__main__':
    import os

    def example1():
        widgets = ['Test: ', Percentage(), ' ', Bar(marker=RotatingMarker()),
                   ' ', ETA(), ' ', FileTransferSpeed()]
        pbar = ProgressBar(widgets=widgets, maxval=10000000).start()
        for i in range(1000000):
            # do something
            pbar.update(10*i+1)
        pbar.finish()
        print

    def example2():
        class CrazyFileTransferSpeed(FileTransferSpeed):
            "It's bigger between 45 and 80 percent"
            def update(self, pbar):
                if 45 < pbar.percentage() < 80:
                    return 'Bigger Now ' + FileTransferSpeed.update(self,pbar)
                else:
                    return FileTransferSpeed.update(self,pbar)

        widgets = [CrazyFileTransferSpeed(),' <<<', Bar(), '>>> ', Percentage(),' ', ETA()]
        pbar = ProgressBar(widgets=widgets, maxval=10000000)
        # maybe do something
        pbar.start()
        for i in range(2000000):
            # do something
            pbar.update(5*i+1)
        pbar.finish()
        print

    def example3():
        widgets = [Bar('>'), ' ', ETA(), ' ', ReverseBar('<')]
        pbar = ProgressBar(widgets=widgets, maxval=10000000).start()
        for i in range(1000000):
            # do something
            pbar.update(10*i+1)
        pbar.finish()
        print

    def example4():
        widgets = ['Test: ', Percentage(), ' ',
                   Bar(marker='0',left='[',right=']'),
                   ' ', ETA(), ' ', FileTransferSpeed()]
        pbar = ProgressBar(widgets=widgets, maxval=500)
        pbar.start()
        for i in range(100,500+1,50):
            time.sleep(0.2)
            pbar.update(i)
        pbar.finish()
        print


    example1()
    example2()
    example3()
    example4()


########NEW FILE########
__FILENAME__ = rendermodes
#    This file is part of the Minecraft Overviewer.
#
#    Minecraft Overviewer is free software: you can redistribute it and/or
#    modify it under the terms of the GNU General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or (at
#    your option) any later version.
#
#    Minecraft Overviewer is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General
#    Public License for more details.
#
#    You should have received a copy of the GNU General Public License along
#    with the Overviewer.  If not, see <http://www.gnu.org/licenses/>.

from PIL import Image
import textures

"""The contents of this file are imported into the namespace of config files.
It also defines the render primitive objects, which are used by the C code.
Each render primitive has a corresponding section of C code, so both places
must be changed simultaneously if you want to make any changes.

"""

class RenderPrimitive(object):
    options = {}
    name = None
    def __init__(self, **kwargs):
        if self.name is None:
            raise RuntimeError("RenderPrimitive cannot be used directly")
        
        self.option_values = {}
        for key, val in kwargs.iteritems():
            if not key in self.options:
                raise ValueError("primitive `{0}' has no option `{1}'".format(self.name, key))
            self.option_values[key] = val
        
        # set up defaults
        for name, (description, default) in self.options.iteritems():
            if not name in self.option_values:
                self.option_values[name] = default

class Base(RenderPrimitive):
    name = "base"
    options = {
        "biomes": ("whether or not to use biomes", True),
    }

class NetherOld(RenderPrimitive):
    name = "netherold"

class Nether(RenderPrimitive):
    name = "nether"

class HeightFading(RenderPrimitive):
    name = "height-fading"
    options = {
        # 128 is *WRONG*, it should be 64. but we're grandfathered in for now
        "sealevel": ("target sea level", 128),
    }
    
    black_color = Image.new("RGB", (24,24), (0,0,0))
    white_color = Image.new("RGB", (24,24), (255,255,255))

class Depth(RenderPrimitive):
    name = "depth"
    options = {
        "min": ("lowest level of blocks to render", 0),
        "max": ("highest level of blocks to render", 255),
    }
    
class Exposed(RenderPrimitive):
    name = "exposed"
    options = {
        "mode": ("0 = exposed blocks only, 1 = unexposed blocks only", 0),
    }
    
class NoFluids(RenderPrimitive):
    name = "no-fluids"

class EdgeLines(RenderPrimitive):
    name = "edge-lines"
    options = {
        "opacity": ("darkness of the edge lines, from 0.0 to 1.0", 0.15),
    }

class Cave(RenderPrimitive):
    name = "cave"
    options = {
        "only_lit": ("only render lit caves", False),
    }

class DepthTinting(RenderPrimitive):
    name = "depth-tinting"
    
    @property
    def depth_colors(self):
        depth_colors = getattr(self, "_depth_colors", [])
        if depth_colors:
            return depth_colors
        r = 255
        g = 0
        b = 0
        for z in range(128):
            depth_colors.append(r)
            depth_colors.append(g)
            depth_colors.append(b)
            
            if z < 32:
                g += 7
            elif z < 64:
                r -= 7
            elif z < 96:
                b += 7
            else:
                g -= 7

        self._depth_colors = depth_colors
        return depth_colors

class Lighting(RenderPrimitive):
    name = "lighting"
    options = {
        "strength": ("how dark to make the shadows, from 0.0 to 1.0", 1.0),
        "night": ("whether to use nighttime skylight settings", False),
        "color": ("whether to use colored light", False),
    }

    @property
    def facemasks(self):
        facemasks = getattr(self, "_facemasks", None)
        if facemasks:
            return facemasks
        
        white = Image.new("L", (24,24), 255)
        
        top = Image.new("L", (24,24), 0)
        left = Image.new("L", (24,24), 0)
        whole = Image.new("L", (24,24), 0)
        
        toppart = textures.Textures.transform_image_top(white)
        leftpart = textures.Textures.transform_image_side(white)
        
        # using the real PIL paste here (not alpha_over) because there is
        # no alpha channel (and it's mode "L")
        top.paste(toppart, (0,0))
        left.paste(leftpart, (0,6))
        right = left.transpose(Image.FLIP_LEFT_RIGHT)
        
        # Manually touch up 6 pixels that leave a gap, like in
        # textures._build_block()
        for x,y in [(13,23), (17,21), (21,19)]:
            right.putpixel((x,y), 255)
        for x,y in [(3,4), (7,2), (11,0)]:
            top.putpixel((x,y), 255)
    
        # special fix for chunk boundary stipple
        for x,y in [(13,11), (17,9), (21,7)]:
            right.putpixel((x,y), 0)
        
        self._facemasks = (top, left, right)
        return self._facemasks

class SmoothLighting(Lighting):
    name = "smooth-lighting"

class ClearBase(RenderPrimitive):
    name = "clear-base"

class Overlay(RenderPrimitive):
    name = "overlay"

    options = {
        'overlay_color' : ('a tuple of (r, g, b, a) for coloring the overlay', None),
    }

    @property
    def whitecolor(self):
        whitecolor = getattr(self, "_whitecolor", None)
        if whitecolor:
            return whitecolor
        white = Image.new("RGBA", (24,24), (255, 255, 255, 255))
        self._whitecolor = white
        return white
    
    @property
    def facemask_top(self):
        facemask_top = getattr(self, "_facemask_top", None)
        if facemask_top:
            return facemask_top
        
        white = Image.new("L", (24,24), 255)
        top = Image.new("L", (24,24), 0)
        toppart = textures.Textures.transform_image_top(white)
        top.paste(toppart, (0,0))
        for x,y in [(3,4), (7,2), (11,0)]:
            top.putpixel((x,y), 255)
        self._facemask_top = top
        return top

class SpawnOverlay(Overlay):
    name = "overlay-spawn"

class SlimeOverlay(Overlay):
    name = "overlay-slime"

class MineralOverlay(Overlay):
    name = "overlay-mineral"
    options = {
        'minerals' : ('a list of (blockid, (r, g, b)) tuples for coloring minerals', None),
    }

class BiomeOverlay(Overlay):
    name = "overlay-biomes"
    options = {
        'biomes' : ('a list of (biome, (r, g, b)) tuples for coloring biomes', None),
        'alpha'  : ('an integer value between 0 (transparent) and 255 (opaque)', None),
    }

class Hide(RenderPrimitive):
    name = "hide"
    options = {
        'blocks' : ('a list of blockids or (blockid, data) tuples of blocks to hide', []),
    }

# Built-in rendermodes for your convenience!
normal = [Base(), EdgeLines()]
lighting = [Base(), EdgeLines(), Lighting()]
smooth_lighting = [Base(), EdgeLines(), SmoothLighting()]
night = [Base(), EdgeLines(), Lighting(night=True)]
smooth_night = [Base(), EdgeLines(), SmoothLighting(night=True)]
netherold = [Base(), EdgeLines(), NetherOld()]
netherold_lighting = [Base(), EdgeLines(), NetherOld(), Lighting()]
netherold_smooth_lighting = [Base(), EdgeLines(), NetherOld(), SmoothLighting()]
nether = [Base(), EdgeLines(), Nether()]
nether_lighting = [Base(), EdgeLines(), Nether(), Lighting()]
nether_smooth_lighting = [Base(), EdgeLines(), Nether(), SmoothLighting()]
cave = [Base(), EdgeLines(), Cave(), DepthTinting()]

########NEW FILE########
__FILENAME__ = settingsDefinition
# This file describes the format of the config file. Each item defined in this
# module is expected to appear in the described format in a valid config file.
# The only difference is, instead of actual values for the settings, values are
# Setting objects which define how to validate a value as correct, and whether
# the value is required or not.

# Settings objects have this signature:
# Setting(required, validator, default)

# required
#   a boolean indicating that this value is required. A required setting will
#   always exist in a validated config. This option only has effect in the
#   event that a user doesn't provide a value and the default is None. In this
#   case, a required setting will raise an error. Otherwise, the situation will
#   result in the setting being omitted from the config with no error.

#   (If it wasn't obvious: a required setting does NOT mean that the user is
#   required to specify it, just that the setting is required to be set for the
#   operation of the program, either by the user or by using the default)

# validator
#   a callable that takes the provided value and returns a cleaned/normalized
#   value to replace it with. It should raise a ValidationException if there is
#   a problem parsing or validating the value given.

# default
#   This is used in the event that the user does not provide a value.  In this
#   case, the default value is passed into the validator just the same. If
#   default is None, then depending on the value of required, it is either an
#   error to omit this setting or the setting is skipped entirely and will not
#   appear in the resulting parsed options.

# The signature for validator callables is validator(value_given). Remember
# that the default is passed in as value_given if the user did not provide a
# value.

# This file doesn't specify the format or even the type of the setting values,
# it is up to the validators to ensure the values passed in are the right type,
# either by coercion or by raising an error.

# Oh, one other thing: For top level values whose required attribute is True,
# the default value is set initially, before the config file is parsed, and is
# available during the execution of the config file. This way, container types
# can be initialized and then appended/added to when the config file is parsed.

from settingsValidators import *
import util
from observer import ProgressBarObserver, LoggingObserver, JSObserver
from optimizeimages import pngnq, optipng, pngcrush
import platform
import sys

# renders is a dictionary mapping strings to dicts. These dicts describe the
# configuration for that render. Therefore, the validator for 'renders' is set
# to a dict validator configured to validate keys as strings and values as...

# values are set to validate as a "configdict", which is a dict mapping a set
# of strings to some value. the make_configdictvalidator() function creates a
# validator to use here configured with the given set of keys and Setting
# objects with their respective validators.

# config file.
renders = Setting(required=True, default=util.OrderedDict(),
        validator=make_dictValidator(validateStr, make_configDictValidator(
        {
            "world": Setting(required=True, validator=validateStr, default=None),
            "dimension": Setting(required=True, validator=validateDimension, default="default"),
            "title": Setting(required=True, validator=validateStr, default=None),
            "rendermode": Setting(required=True, validator=validateRenderMode, default='normal'),
            "northdirection": Setting(required=True, validator=validateNorthDirection, default=0),
            "forcerender": Setting(required=False, validator=validateBool, default=None),
            "imgformat": Setting(required=True, validator=validateImgFormat, default="png"),
            "imgquality": Setting(required=False, validator=validateImgQuality, default=95),
            "bgcolor": Setting(required=True, validator=validateBGColor, default="1a1a1a"),
            "defaultzoom": Setting(required=True, validator=validateDefaultZoom, default=1),
            "optimizeimg": Setting(required=True, validator=validateOptImg, default=[]),
            "nomarkers": Setting(required=False, validator=validateBool, default=None),
            "texturepath": Setting(required=False, validator=validateTexturePath, default=None),
            "renderchecks": Setting(required=False, validator=validateInt, default=None),
            "rerenderprob": Setting(required=True, validator=validateRerenderprob, default=0),
            "crop": Setting(required=False, validator=validateCrop, default=None),
            "changelist": Setting(required=False, validator=validateStr, default=None),
            "markers": Setting(required=False, validator=validateMarkers, default=[]),
            "overlay": Setting(required=False, validator=validateOverlays, default=[]),
            "showspawn": Setting(required=False, validator=validateBool, default=True),
            "base": Setting(required=False, validator=validateStr, default=""),
            "poititle": Setting(required=False, validator=validateStr, default="Markers"),
            "customwebassets": Setting(required=False, validator=validateWebAssetsPath, default=None),
            "maxzoom": Setting(required=False, validator=validateInt, default=None),
            "minzoom": Setting(required=False, validator=validateInt, default=0),
            "manualpois": Setting(required=False, validator=validateManualPOIs, default=[]),
            "showlocationmarker": Setting(required=False, validator=validateBool, default=True),
            # Remove this eventually (once people update their configs)
            "worldname": Setting(required=False, default=None,
                validator=error("The option 'worldname' is now called 'world'. Please update your config files")),
        }
        )))

# The worlds dict, mapping world names to world paths
worlds = Setting(required=True, validator=make_dictValidator(validateStr, validateWorldPath), default=util.OrderedDict())

outputdir = Setting(required=True, validator=validateOutputDir, default=None)

processes = Setting(required=True, validator=int, default=-1)

# memcached is an option, but unless your IO costs are really high, it just
# ends up adding overhead and isn't worth it.
memcached_host = Setting(required=False, validator=str, default=None)

# TODO clean up this ugly in sys.argv hack
if platform.system() == 'Windows' or not sys.stdout.isatty() or "--simple" in sys.argv:
    obs = LoggingObserver()
else:
    obs = ProgressBarObserver(fd=sys.stdout)

observer = Setting(required=True, validator=validateObserver, default=obs)

########NEW FILE########
__FILENAME__ = settingsValidators
# see settingsDefinition.py
import os
import os.path
from collections import namedtuple

import rendermodes
import util
from optimizeimages import Optimizer
from world import UPPER_LEFT, UPPER_RIGHT, LOWER_LEFT, LOWER_RIGHT
import logging

class ValidationException(Exception):
    pass

class Setting(object):
    __slots__ = ['required', 'validator', 'default']
    def __init__(self, required, validator, default):
        self.required = required
        self.validator = validator
        self.default = default

def expand_path(p):
    p = os.path.expanduser(p)
    p = os.path.expandvars(p)
    p = os.path.abspath(p)
    return p

def checkBadEscape(s):
    #If any of these weird characters are in the path, raise an exception instead of fixing
    #this should help us educate our users about pathslashes
    if "\a" in s:
        raise ValueError("Invalid character '\\a' in path.  Please use forward slashes ('/').  Please see our docs for more info.")
    if "\b" in s:
        raise ValueError("Invalid character '\\b' in path.  Please use forward slashes ('/').  Please see our docs for more info.")
    if "\t" in s:
        raise ValueError("Invalid character '\\t' in path.  Please use forward slashes ('/').  Please see our docs for more info.")
    if "\n" in s:
        raise ValueError("Invalid character '\\n' in path.  Please use forward slashes ('/').  Please see our docs for more info.")
    if "\v" in s:
        raise ValueError("Invalid character '\\v' in path.  Please use forward slashes ('/').  Please see our docs for more info.")
    if "\f" in s:
        raise ValueError("Invalid character '\\f' in path.  Please use forward slashes ('/').  Please see our docs for more info.")
    if "\r" in s:
        raise ValueError("Invalid character '\\r' in path.  Please use forward slashes ('/').  Please see our docs for more info.")
    for c in range(10):
        if chr(c) in s:
            raise ValueError("Invalid character '\\%s' in path.  Please use forward slashes ('/').  Please see our docs for more info." % c)
    return s

def validateMarkers(filterlist):
    if type(filterlist) != list:
        raise ValidationException("Markers must specify a list of filters.  This has recently changed, so check the docs.")
    for x in filterlist:
        if type(x) != dict:
            raise ValidationException("Markers must specify a list of dictionaries.  This has recently changed, so check the docs.")
        if "name" not in x:
            raise ValidationException("Must define a name")
        if "filterFunction" not in x:
            raise ValidationException("Must define a filter function")
        if not callable(x['filterFunction']):
            raise ValidationException("%r must be a function"% x['filterFunction'])
    return filterlist

def validateOverlays(renderlist):
    if type(renderlist) != list:
        raise ValidationException("Overlay must specify a list of renders")
    for x in renderlist:
        if validateStr(x) == '':
            raise ValidationException("%r must be a string"% x)
    return renderlist

def validateWorldPath(worldpath):
    checkBadEscape(worldpath)
    abs_path = expand_path(worldpath)
    if not os.path.exists(os.path.join(abs_path, "level.dat")):
        raise ValidationException("No level.dat file in '%s'. Are you sure you have the right path?" % (abs_path,))
    return abs_path


def validateRenderMode(mode):
    # make sure that mode is a list of things that are all rendermode primative
    if isinstance(mode, str):
        # Try and find an item named "mode" in the rendermodes module
        mode = mode.lower().replace("-","_")
        try:
            mode = getattr(rendermodes, mode)
        except AttributeError:
            raise ValidationException("You must specify a valid rendermode, not '%s'. See the docs for valid rendermodes." % mode)

    if isinstance(mode, rendermodes.RenderPrimitive):
        mode = [mode]

    if not isinstance(mode, list):
        raise ValidationException("%r is not a valid list of rendermodes.  It should be a list"% mode)

    for m in mode:
        if not isinstance(m, rendermodes.RenderPrimitive):
            raise ValidationException("%r is not a valid rendermode primitive." % m)


    return mode

def validateNorthDirection(direction):
    # normalize to integers
    intdir = 0 #default
    if type(direction) == int:
        intdir = direction
    elif isinstance(direction, str):
        direction = direction.lower().replace("-","").replace("_","")
        if direction == "upperleft": intdir = UPPER_LEFT
        elif direction == "upperright": intdir = UPPER_RIGHT
        elif direction == "lowerright": intdir = LOWER_RIGHT
        elif direction == "lowerleft": intdir = LOWER_LEFT
        else:
            raise ValidationException("'%s' is not a valid north direction" % direction)
    if intdir < 0 or intdir > 3:
        raise ValidationException("%r is not a valid north direction" % direction)
    return intdir

def validateRerenderprob(s):
    val = float(s)
    if val < 0 or val >= 1:
        raise ValidationException("%r is not a valid rerender probability value.  Should be between 0.0 and 1.0." % s)
    return val

def validateImgFormat(fmt):
    if fmt not in ("png", "jpg", "jpeg"):
        raise ValidationException("%r is not a valid image format" % fmt)
    if fmt == "jpeg": fmt = "jpg"
    return fmt

def validateImgQuality(qual):
    intqual = int(qual)
    if (intqual < 0 or intqual > 100):
        raise ValidationException("%r is not a valid image quality" % intqual)
    return intqual

def validateBGColor(color):
    """BG color must be an HTML color, with an option leading # (hash symbol)
    returns an (r,b,g) 3-tuple
    """
    if type(color) == str:
        if color[0] != "#":
            color = "#" + color
        if len(color) != 7:
            raise ValidationException("%r is not a valid color.  Expected HTML color syntax (i.e. #RRGGBB)" % color)
        try:
            r = int(color[1:3], 16)
            g = int(color[3:5], 16)
            b = int(color[5:7], 16)
            return (r,g,b,0)
        except ValueError:
            raise ValidationException("%r is not a valid color.  Expected HTML color syntax (i.e. #RRGGBB)" % color)
    elif type(color) == tuple:
        if len(color) != 4:
            raise ValidationException("%r is not a valid color.  Expected a 4-tuple" % (color,))
        return color


def validateOptImg(optimizers):
    if isinstance(optimizers, (int, long)):
        from optimizeimages import pngcrush
        logging.warning("You're using a deprecated definition of optimizeimg. "\
                        "We'll do what you say for now, but please fix this as soon as possible.")
        optimizers = [pngcrush()]
    if not isinstance(optimizers, list):
        raise ValidationException("What you passed to optimizeimg is not a list. "\
                                  "Make sure you specify them like [foo()], with square brackets.")

    if optimizers:
        for opt, next_opt in zip(optimizers, optimizers[1:]) + [(optimizers[-1], None)]:
            if not isinstance(opt, Optimizer):
                raise ValidationException("Invalid Optimizer!")

            opt.check_availability()

            # Check whether the chaining is somewhat sane
            if next_opt:
                if opt.is_crusher() and not next_opt.is_crusher():
                    logging.warning("You're feeding a crushed output into an optimizer that does not crush. "\
                                    "This is most likely pointless, and wastes time.")

    return optimizers

def validateTexturePath(path):
    # Expand user dir in directories strings
    path = expand_path(path)
    if not os.path.exists(path):
        raise ValidationException("%r does not exist" % path)
    return path


def validateBool(b):
    return bool(b)

def validateFloat(f):
    return float(f)

def validateInt(i):
    return int(i)

def validateStr(s):
    return str(s)

def validateDimension(d):
    # returns (original, argument to get_type)
    
    # these are provided as arguments to RegionSet.get_type()
    pretty_names = {
        "nether": "DIM-1",
        "overworld": None,
        "end": "DIM1",
        "default": 0,
    }
    
    try:
        return (d, pretty_names[d])
    except KeyError:
        return (d, d)

def validateOutputDir(d):
    checkBadEscape(d)
    if not d.strip():
        raise ValidationException("You must specify a valid output directory")
    return expand_path(d)

def validateCrop(value):
    if len(value) != 4:
        raise ValidationException("The value for the 'crop' setting must be a tuple of length 4")
    a, b, c, d = tuple(int(x) for x in value)

    if a >= c:
        a, c = c, a
    if b >= d:
        b, d = d, b
    return (a, b, c, d)

def validateObserver(observer):
    if all(map(lambda m: hasattr(observer, m), ['start', 'add', 'update', 'finish'])):
        return observer
    else:
        raise ValidationException("%r does not look like an observer" % repr(observer))

def validateDefaultZoom(z):
    if z > 0:
        return int(z)
    else:
        raise ValidationException("The default zoom is set below 1")

def validateWebAssetsPath(p):
    try:
        validatePath(p)
    except ValidationException as e:
        raise ValidationException("Bad custom web assets path: %s" % e.message)

def validatePath(p):
    checkBadEscape(p)
    abs_path = expand_path(p)
    if not os.path.exists(abs_path):
        raise ValidationException("'%s' does not exist. Path initially given as '%s'" % (abs_path,p))

def validateManualPOIs(d):
    for poi in d:
        if not 'x' in poi or not 'y' in poi or not 'z' in poi or not 'id' in poi:
            raise ValidationException("Not all POIs have x/y/z coordinates or an id: %r" % poi)
    return d

def make_dictValidator(keyvalidator, valuevalidator):
    """Compose and return a dict validator -- a validator that validates each
    key and value in a dictionary.

    The arguments are the validator function to use for the keys, and the
    validator function to use for the values.

    """
    def v(d):
        newd = util.OrderedDict()
        for key, value in d.iteritems():
            newd[keyvalidator(key)] = valuevalidator(value)
        return newd
    # Put these objects as attributes of the function so they can be accessed
    # externally later if need be
    v.keyvalidator = keyvalidator
    v.valuevalidator = valuevalidator
    return v

def make_configDictValidator(config, ignore_undefined=False):
    """Okay, stay with me here, this may get confusing. This function returns a
    validator that validates a "configdict". This is a term I just made up to
    refer to a dict that holds config information: keys are strings and values
    are whatever that config value is. The argument to /this/ function is a
    dictionary defining the valid keys for the configdict. It therefore maps
    those key names to Setting objects. When the returned validator function
    validates, it calls all the appropriate validators for each configdict
    setting

    I hope that makes sense.

    ignore_undefined, if True, will ignore any items in the dict to be
    validated which don't have a corresponding definition in the config.
    Otherwise, undefined entries will raise an error.

    """
    def configDictValidator(d):
        newdict = util.OrderedDict()

        # values are config keys that the user specified that don't match any
        # valid key
        # keys are the correct configuration key
        undefined_key_matches = {}

        # Go through the keys the user gave us and make sure they're all valid.
        for key in d.iterkeys():
            if key not in config:
                # Try to find a probable match
                match = _get_closest_match(key, config.iterkeys())
                if match and ignore_undefined:
                    # Save this for later. It only matters if this is a typo of
                    # some required key that wasn't specified. (If all required
                    # keys are specified, then this should be ignored)
                    undefined_key_matches[match] = key
                    newdict[key] = d[key]
                elif match:
                    raise ValidationException(
                            "'%s' is not a configuration item. Did you mean '%s'?"
                            % (key, match))
                elif not ignore_undefined:
                    raise ValidationException("'%s' is not a configuration item" % key)
                else:
                    # the key is to be ignored. Copy it as-is to the `newdict`
                    # to be returned. It shouldn't conflict, and may be used as
                    # a default value for a render configdict later on.
                    newdict[key] = d[key]

        # Iterate through the defined keys in the configuration (`config`),
        # checking each one to see if the user specified it (in `d`). Then
        # validate it and copy the result to `newdict`
        for configkey, configsetting in config.iteritems():
            if configkey in d:
                # This key /was/ specified in the user's dict. Make sure it validates.
                newdict[configkey] = configsetting.validator(d[configkey])
            elif configsetting.default is not None:
                # There is a default, use that instead
                newdict[configkey] = configsetting.validator(configsetting.default)
            elif configsetting.required:
                # The user did not give us this key, there is no default, AND
                # it's required. This is an error.
                if configkey in undefined_key_matches:
                    raise ValidationException("Key '%s' is not a valid "
                    "configuration item. Did you mean '%s'?"
                            % (undefined_key_matches[configkey], configkey))
                else:
                    raise ValidationException("Required key '%s' was not "
                    "specified. You must give a value for this setting"
                    % configkey)

        return newdict
    # Put these objects as attributes of the function so they can be accessed
    # externally later if need be
    configDictValidator.config = config
    configDictValidator.ignore_undefined = ignore_undefined
    return configDictValidator

def error(errstr):
    def validator(_):
        raise ValidationException(errstr)
    return validator

# Activestate recipe 576874
def _levenshtein(s1, s2):
  l1 = len(s1)
  l2 = len(s2)

  matrix = [range(l1 + 1)] * (l2 + 1)
  for zz in range(l2 + 1):
    matrix[zz] = range(zz,zz + l1 + 1)
  for zz in range(0,l2):
    for sz in range(0,l1):
      if s1[sz] == s2[zz]:
        matrix[zz+1][sz+1] = min(matrix[zz+1][sz] + 1, matrix[zz][sz+1] + 1, matrix[zz][sz])
      else:
        matrix[zz+1][sz+1] = min(matrix[zz+1][sz] + 1, matrix[zz][sz+1] + 1, matrix[zz][sz] + 1)
  return matrix[l2][l1]

def _get_closest_match(s, keys):
    """Returns a probable match for the given key `s` out of the possible keys in
    `keys`. Returns None if no matches are very close.

    """
    # Adjust this. 3 is probably a good number, it's probably not a typo if the
    # distance is >3
    threshold = 3

    minmatch = None
    mindist = threshold+1

    for key in keys:
        d = _levenshtein(s, key)
        if d < mindist:
            minmatch = key
            mindist = d

    if mindist <= threshold:
        return minmatch
    return None

########NEW FILE########
__FILENAME__ = signals
#    This file is part of the Minecraft Overviewer.
#
#    Minecraft Overviewer is free software: you can redistribute it and/or
#    modify it under the terms of the GNU General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or (at
#    your option) any later version.
#
#    Minecraft Overviewer is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General
#    Public License for more details.
#
#    You should have received a copy of the GNU General Public License along
#    with the Overviewer.  If not, see <http://www.gnu.org/licenses/>.

"""
This module provides a way to create named "signals" that, when
emitted, call a set of registered functions. These signals also have
the ability to be intercepted, which lets Dispatchers re-route signals
back to the main process.
"""

class Signal(object):
    """A mechanism for registering functions to be called whenever
    some specified event happens. This object is designed to work with
    Dispatcher so that functions can register to always run in the
    main Python instance."""
    
    # a global list of registered signals, indexed by name
    # this is used by JobManagers to register and relay signals
    signals = {}
    
    def __init__(self, namespace, name):
        """Creates a signal. Namespace and name should be the name of
        the class this signal is for, and the name of the signal. They
        are used to create a globally-unique name."""
        
        self.namespace = namespace
        self.name = name
        self.fullname = namespace + '.' + name
        self.interceptor = None
        self.local_functions = []
        self.functions = []
        
        # register this signal
        self.signals[self.fullname] = self
    
    def register(self, func):
        """Register a function to be called when this signal is
        emitted. Functions registered in this way will always run in
        the main Python instance."""
        self.functions.append(func)
        return func
    
    def register_local(self, func):
        """Register a function to be called when this signal is
        emitted. Functions registered in this way will always run in
        the Python instance in which they were emitted."""
        self.local_functions.append(func)
        return func
    
    def set_interceptor(self, func):
        """Sets an interceptor function. This function is called
        instead of all the non-locally registered functions if it is
        present, and should be used by JobManagers to intercept signal
        emissions."""
        self.interceptor = func
        
    def emit(self, *args, **kwargs):
        """Emits the signal with the given arguments. For convenience,
        you can also call the signal object directly.
        """
        for func in self.local_functions:
            func(*args, **kwargs)
        if self.interceptor:
            self.interceptor(*args, **kwargs)
            return
        for func in self.functions:
            func(*args, **kwargs)
    
    def emit_intercepted(self, *args, **kwargs):
        """Re-emits an intercepted signal, and finishes the work that
        would have been done during the original emission. This should
        be used by Dispatchers to re-emit signals intercepted in
        worker Python instances."""
        for func in self.functions:
            func(*args, **kwargs)
    
    # convenience
    def __call__(self, *args, **kwargs):
        self.emit(*args, **kwargs)
    
    # force pickled signals to redirect to existing signals
    def __getstate__(self):
        return self.fullname
    def __setstate__(self, fullname):
        for attr in dir(self.signals[fullname]):
            if attr.startswith('_'):
                continue
            setattr(self, attr, getattr(self.signals[fullname], attr))

########NEW FILE########
__FILENAME__ = textures
#    This file is part of the Minecraft Overviewer.
#
#    Minecraft Overviewer is free software: you can redistribute it and/or
#    modify it under the terms of the GNU General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or (at
#    your option) any later version.
#
#    Minecraft Overviewer is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General
#    Public License for more details.
#
#    You should have received a copy of the GNU General Public License along
#    with the Overviewer.  If not, see <http://www.gnu.org/licenses/>.

import sys
import imp
import os
import os.path
import zipfile
from cStringIO import StringIO
import math
from random import randint
import numpy
from PIL import Image, ImageEnhance, ImageOps, ImageDraw
import logging
import functools

import util
from c_overviewer import alpha_over

class TextureException(Exception):
    "To be thrown when a texture is not found."
    pass


color_map = ["white", "orange", "magenta", "light_blue", "yellow", "lime", "pink", "gray",
             "silver", "cyan", "purple", "blue", "brown", "green", "red", "black"]

##
## Textures object
##
class Textures(object):
    """An object that generates a set of block sprites to use while
    rendering. It accepts a background color, north direction, and
    local textures path.
    """
    def __init__(self, texturepath=None, bgcolor=(26, 26, 26, 0), northdirection=0):
        self.bgcolor = bgcolor
        self.rotation = northdirection
        self.find_file_local_path = texturepath
        
        # not yet configurable
        self.texture_size = 24
        self.texture_dimensions = (self.texture_size, self.texture_size)
        
        # this is set in in generate()
        self.generated = False

        # see load_image_texture()
        self.texture_cache = {}

        # once we find a jarfile that contains a texture, we cache the ZipFile object here
        self.jar = None
        self.jarpath = ""
    
    ##
    ## pickle support
    ##
    
    def __getstate__(self):
        # we must get rid of the huge image lists, and other images
        attributes = self.__dict__.copy()
        for attr in ['blockmap', 'biome_grass_texture', 'watertexture', 'lavatexture', 'firetexture', 'portaltexture', 'lightcolor', 'grasscolor', 'foliagecolor', 'watercolor', 'texture_cache']:
            try:
                del attributes[attr]
            except KeyError:
                pass
        return attributes
    def __setstate__(self, attrs):
        # regenerate textures, if needed
        for attr, val in attrs.iteritems():
            setattr(self, attr, val)
        self.texture_cache = {}
        if self.generated:
            self.generate()
    
    ##
    ## The big one: generate()
    ##
    
    def generate(self):
        
        # generate biome grass mask
        self.biome_grass_texture = self.build_block(self.load_image_texture("assets/minecraft/textures/blocks/grass_top.png"), self.load_image_texture("assets/minecraft/textures/blocks/grass_side_overlay.png"))
        
        # generate the blocks
        global blockmap_generators
        global known_blocks, used_datas
        self.blockmap = [None] * max_blockid * max_data
        
        for (blockid, data), texgen in blockmap_generators.iteritems():
            tex = texgen(self, blockid, data)
            self.blockmap[blockid * max_data + data] = self.generate_texture_tuple(tex)
        
        if self.texture_size != 24:
            # rescale biome grass
            self.biome_grass_texture = self.biome_grass_texture.resize(self.texture_dimensions, Image.ANTIALIAS)
            
            # rescale the rest
            for i, tex in enumerate(blockmap):
                if tex is None:
                    continue
                block = tex[0]
                scaled_block = block.resize(self.texture_dimensions, Image.ANTIALIAS)
                blockmap[i] = self.generate_texture_tuple(scaled_block)
        
        self.generated = True
    
    ##
    ## Helpers for opening textures
    ##
    
    def find_file(self, filename, mode="rb", verbose=False):
        """Searches for the given file and returns an open handle to it.
        This searches the following locations in this order:
        
        * In the directory textures_path given in the initializer
        * In the resource pack given by textures_path
        * The program dir (same dir as overviewer.py) for extracted textures
        * On Darwin, in /Applications/Minecraft for extracted textures
        * Inside a minecraft client jar. Client jars are searched for in the
          following location depending on platform:
        
            * On Windows, at %APPDATA%/.minecraft/versions/
            * On Darwin, at
                $HOME/Library/Application Support/minecraft/versions
            * at $HOME/.minecraft/versions/

          Only the latest non-snapshot version >1.6 is used

        * The overviewer_core/data/textures dir
        
        In all of these, files are searched for in '.', 'anim', 'misc/', and
        'environment/'.
        
        """
        if verbose: logging.info("Starting search for {0}".format(filename))

        # a list of subdirectories to search for a given file,
        # after the obvious '.'
        search_dirs = ['anim', 'misc', 'environment', 'item', 'item/chests', 'entity', 'entity/chest']
        search_zip_paths = [filename,] + [d + '/' + filename for d in search_dirs]
        def search_dir(base):
            """Search the given base dir for filename, in search_dirs."""
            for path in [os.path.join(base, d, filename) for d in ['',] + search_dirs]:
                if verbose: logging.info('filename: ' + filename + ' ; path: ' + path)
                if os.path.isfile(path):
                    return path

            return None
        if verbose: logging.info('search_zip_paths: ' +  ', '.join(search_zip_paths))

        # A texture path was given on the command line. Search this location
        # for the file first.
        if self.find_file_local_path:
            if os.path.isdir(self.find_file_local_path):
                path = search_dir(self.find_file_local_path)
                if path:
                    if verbose: logging.info("Found %s in '%s'", filename, path)
                    return open(path, mode)
            elif os.path.isfile(self.find_file_local_path):
                # Must be a resource pack. Look for the requested file within
                # it.
                try:
                    pack = zipfile.ZipFile(self.find_file_local_path)
                    for packfilename in search_zip_paths:
                        try:
                            # pack.getinfo() will raise KeyError if the file is
                            # not found.
                            pack.getinfo(packfilename)
                            if verbose: logging.info("Found %s in '%s'", packfilename, self.find_file_local_path)
                            return pack.open(packfilename)
                        except (KeyError, IOError):
                            pass
                        
                        try:
                            # 2nd try with completed path.
                            packfilename = 'assets/minecraft/textures/' + packfilename
                            pack.getinfo(packfilename)
                            if verbose: logging.info("Found %s in '%s'", packfilename, self.find_file_local_path)
                            return pack.open(packfilename)
                        except (KeyError, IOError):
                            pass
                except (zipfile.BadZipfile, IOError):
                    pass

        # If we haven't returned at this point, then the requested file was NOT
        # found in the user-specified texture path or resource pack.
        if verbose: logging.info("Did not find the file in specified texture path")


        # Look in the location of the overviewer executable for the given path
        programdir = util.get_program_path()
        path = search_dir(programdir)
        if path:
            if verbose: logging.info("Found %s in '%s'", filename, path)
            return open(path, mode)

        if sys.platform.startswith("darwin"):
            path = search_dir("/Applications/Minecraft")
            if path:
                if verbose: logging.info("Found %s in '%s'", filename, path)
                return open(path, mode)

        if verbose: logging.info("Did not find the file in overviewer executable directory")
        if verbose: logging.info("Looking for installed minecraft jar files...")

        # we've sucessfully loaded something from here before, so let's quickly try
        # this before searching again
        if self.jar is not None:
            for jarfilename in search_zip_paths:
                try:
                    self.jar.getinfo(jarfilename)
                    if verbose: logging.info("Found (cached) %s in '%s'", jarfilename, self.jarpath)
                    return self.jar.open(jarfilename)
                except (KeyError, IOError), e:
                    pass

        # Find an installed minecraft client jar and look in it for the texture
        # file we need.
        versiondir = ""
        if "APPDATA" in os.environ and sys.platform.startswith("win"):
            versiondir = os.path.join(os.environ['APPDATA'], ".minecraft", "versions")
        elif "HOME" in os.environ:
            # For linux:
            versiondir = os.path.join(os.environ['HOME'], ".minecraft", "versions")
            if not os.path.exists(versiondir) and sys.platform.startswith("darwin"):
                # For Mac:
                versiondir = os.path.join(os.environ['HOME'], "Library",
                    "Application Support", "minecraft", "versions")

        try:
            if verbose: logging.info("Looking in the following directory: \"%s\"" % versiondir)
            versions = os.listdir(versiondir)
            if verbose: logging.info("Found these versions: {0}".format(versions))
        except OSError:
            # Directory doesn't exist? Ignore it. It will find no versions and
            # fall through the checks below to the error at the bottom of the
            # method.
            versions = []

        most_recent_version = [0,0,0]
        for version in versions:
            # Look for the latest non-snapshot that is at least 1.6. This
            # version is only compatible with >=1.6, and we cannot in general
            # tell if a snapshot is more or less recent than a release.

            # Allow two component names such as "1.6" and three component names
            # such as "1.6.1"
            if version.count(".") not in (1,2):
                continue
            try:
                versionparts = [int(x) for x in version.split(".")]
            except ValueError:
                continue

            if versionparts < [1,7]:
                continue

            if versionparts > most_recent_version:
                most_recent_version = versionparts

        if most_recent_version != [0,0,0]:
            if verbose: logging.info("Most recent version >=1.7.0: {0}. Searching it for the file...".format(most_recent_version))

            jarname = ".".join(str(x) for x in most_recent_version)
            jarpath = os.path.join(versiondir, jarname, jarname + ".jar")

            if os.path.isfile(jarpath):
                jar = zipfile.ZipFile(jarpath)
                for jarfilename in search_zip_paths:
                    try:
                        jar.getinfo(jarfilename)
                        if verbose: logging.info("Found %s in '%s'", jarfilename, jarpath)
                        self.jar, self.jarpath = jar, jarpath
                        return jar.open(jarfilename)
                    except (KeyError, IOError), e:
                        pass

            if verbose: logging.info("Did not find file {0} in jar {1}".format(filename, jarpath))
        else:
            if verbose: logging.info("Did not find any non-snapshot minecraft jars >=1.7.0")
            
        # Last ditch effort: look for the file is stored in with the overviewer
        # installation. We include a few files that aren't included with Minecraft
        # textures. This used to be for things such as water and lava, since
        # they were generated by the game and not stored as images. Nowdays I
        # believe that's not true, but we still have a few files distributed
        # with overviewer.
        if verbose: logging.info("Looking for texture in overviewer_core/data/textures")
        path = search_dir(os.path.join(programdir, "overviewer_core", "data", "textures"))
        if path:
            if verbose: logging.info("Found %s in '%s'", filename, path)
            return open(path, mode)
        elif hasattr(sys, "frozen") or imp.is_frozen("__main__"):
            # windows special case, when the package dir doesn't exist
            path = search_dir(os.path.join(programdir, "textures"))
            if path:
                if verbose: logging.info("Found %s in '%s'", filename, path)
                return open(path, mode)

        raise TextureException("Could not find the textures while searching for '{0}'. Try specifying the 'texturepath' option in your config file.\nSet it to the path to a Minecraft Resource pack.\nAlternately, install the Minecraft client (which includes textures)\nAlso see <http://docs.overviewer.org/en/latest/running/#installing-the-textures>\n(Remember, this version of Overviewer requires a 1.7-compatible resource pack)\n(Also note that I won't automatically use snapshots; you'll have to use the texturepath option to use a snapshot jar)".format(filename))

    def load_image_texture(self, filename):
        # Textures may be animated or in a different resolution than 16x16.  
        # This method will always return a 16x16 image

        img = self.load_image(filename)

        w,h = img.size
        if w != h:
            img = img.crop((0,0,w,w))
        if w != 16:
            img = img.resize((16, 16), Image.ANTIALIAS)

        self.texture_cache[filename] = img
        return img

    def load_image(self, filename):
        """Returns an image object"""

        if filename in self.texture_cache:
            return self.texture_cache[filename]
        
        fileobj = self.find_file(filename)
        buffer = StringIO(fileobj.read())
        img = Image.open(buffer).convert("RGBA")
        self.texture_cache[filename] = img
        return img



    def load_water(self):
        """Special-case function for loading water, handles
        MCPatcher-compliant custom animated water."""
        watertexture = getattr(self, "watertexture", None)
        if watertexture:
            return watertexture
        try:
            # try the MCPatcher case first
            watertexture = self.load_image("custom_water_still.png")
            watertexture = watertexture.crop((0, 0, watertexture.size[0], watertexture.size[0]))
        except TextureException:
            watertexture = self.load_image_texture("assets/minecraft/textures/blocks/water_still.png")
        self.watertexture = watertexture
        return watertexture

    def load_lava(self):
        """Special-case function for loading lava, handles
        MCPatcher-compliant custom animated lava."""
        lavatexture = getattr(self, "lavatexture", None)
        if lavatexture:
            return lavatexture
        try:
            # try the MCPatcher lava first, in case it's present
            lavatexture = self.load_image("custom_lava_still.png")
            lavatexture = lavatexture.crop((0, 0, lavatexture.size[0], lavatexture.size[0]))
        except TextureException:
            lavatexture = self.load_image_texture("assets/minecraft/textures/blocks/lava_still.png")
        self.lavatexture = lavatexture
        return lavatexture
    
    def load_fire(self):
        """Special-case function for loading fire, handles
        MCPatcher-compliant custom animated fire."""
        firetexture = getattr(self, "firetexture", None)
        if firetexture:
            return firetexture
        try:
            # try the MCPatcher case first
            firetextureNS = self.load_image("custom_fire_n_s.png")
            firetextureNS = firetextureNS.crop((0, 0, firetextureNS.size[0], firetextureNS.size[0]))
            firetextureEW = self.load_image("custom_fire_e_w.png")
            firetextureEW = firetextureEW.crop((0, 0, firetextureEW.size[0], firetextureEW.size[0]))
            firetexture = (firetextureNS,firetextureEW)
        except TextureException:
            fireNS = self.load_image_texture("assets/minecraft/textures/blocks/fire_layer_0.png")
            fireEW = self.load_image_texture("assets/minecraft/textures/blocks/fire_layer_1.png")
            firetexture = (fireNS, fireEW)
        self.firetexture = firetexture
        return firetexture
    
    def load_portal(self):
        """Special-case function for loading portal, handles
        MCPatcher-compliant custom animated portal."""
        portaltexture = getattr(self, "portaltexture", None)
        if portaltexture:
            return portaltexture
        try:
            # try the MCPatcher case first
            portaltexture = self.load_image("custom_portal.png")
            portaltexture = portaltexture.crop((0, 0, portaltexture.size[0], portaltexture.size[1]))
        except TextureException:
            portaltexture = self.load_image_texture("assets/minecraft/textures/blocks/portal.png")
        self.portaltexture = portaltexture
        return portaltexture
    
    def load_light_color(self):
        """Helper function to load the light color texture."""
        if hasattr(self, "lightcolor"):
            return self.lightcolor
        try:
            lightcolor = list(self.load_image("light_normal.png").getdata())
        except Exception:
            logging.warning("Light color image could not be found.")
            lightcolor = None
        self.lightcolor = lightcolor
        return lightcolor
    
    def load_grass_color(self):
        """Helper function to load the grass color texture."""
        if not hasattr(self, "grasscolor"):
            self.grasscolor = list(self.load_image("grass.png").getdata())
        return self.grasscolor

    def load_foliage_color(self):
        """Helper function to load the foliage color texture."""
        if not hasattr(self, "foliagecolor"):
            self.foliagecolor = list(self.load_image("foliage.png").getdata())
        return self.foliagecolor

	#I guess "watercolor" is wrong. But I can't correct as my texture pack don't define water color.
    def load_water_color(self):
        """Helper function to load the water color texture."""
        if not hasattr(self, "watercolor"):
            self.watercolor = list(self.load_image("watercolor.png").getdata())
        return self.watercolor

    def _split_terrain(self, terrain):
        """Builds and returns a length 256 array of each 16x16 chunk
        of texture.
        """
        textures = []
        (terrain_width, terrain_height) = terrain.size
        texture_resolution = terrain_width / 16
        for y in xrange(16):
            for x in xrange(16):
                left = x*texture_resolution
                upper = y*texture_resolution
                right = left+texture_resolution
                lower = upper+texture_resolution
                region = terrain.transform(
                          (16, 16),
                          Image.EXTENT,
                          (left,upper,right,lower),
                          Image.BICUBIC)
                textures.append(region)

        return textures

    ##
    ## Image Transformation Functions
    ##

    @staticmethod
    def transform_image_top(img):
        """Takes a PIL image and rotates it left 45 degrees and shrinks the y axis
        by a factor of 2. Returns the resulting image, which will be 24x12 pixels

        """

        # Resize to 17x17, since the diagonal is approximately 24 pixels, a nice
        # even number that can be split in half twice
        img = img.resize((17, 17), Image.ANTIALIAS)

        # Build the Affine transformation matrix for this perspective
        transform = numpy.matrix(numpy.identity(3))
        # Translate up and left, since rotations are about the origin
        transform *= numpy.matrix([[1,0,8.5],[0,1,8.5],[0,0,1]])
        # Rotate 45 degrees
        ratio = math.cos(math.pi/4)
        #transform *= numpy.matrix("[0.707,-0.707,0;0.707,0.707,0;0,0,1]")
        transform *= numpy.matrix([[ratio,-ratio,0],[ratio,ratio,0],[0,0,1]])
        # Translate back down and right
        transform *= numpy.matrix([[1,0,-12],[0,1,-12],[0,0,1]])
        # scale the image down by a factor of 2
        transform *= numpy.matrix("[1,0,0;0,2,0;0,0,1]")

        transform = numpy.array(transform)[:2,:].ravel().tolist()

        newimg = img.transform((24,12), Image.AFFINE, transform)
        return newimg

    @staticmethod
    def transform_image_side(img):
        """Takes an image and shears it for the left side of the cube (reflect for
        the right side)"""

        # Size of the cube side before shear
        img = img.resize((12,12), Image.ANTIALIAS)

        # Apply shear
        transform = numpy.matrix(numpy.identity(3))
        transform *= numpy.matrix("[1,0,0;-0.5,1,0;0,0,1]")

        transform = numpy.array(transform)[:2,:].ravel().tolist()

        newimg = img.transform((12,18), Image.AFFINE, transform)
        return newimg

    @staticmethod
    def transform_image_slope(img):
        """Takes an image and shears it in the shape of a slope going up
        in the -y direction (reflect for +x direction). Used for minetracks"""

        # Take the same size as trasform_image_side
        img = img.resize((12,12), Image.ANTIALIAS)

        # Apply shear
        transform = numpy.matrix(numpy.identity(3))
        transform *= numpy.matrix("[0.75,-0.5,3;0.25,0.5,-3;0,0,1]")
        transform = numpy.array(transform)[:2,:].ravel().tolist()

        newimg = img.transform((24,24), Image.AFFINE, transform)

        return newimg


    @staticmethod
    def transform_image_angle(img, angle):
        """Takes an image an shears it in arbitrary angle with the axis of
        rotation being vertical.

        WARNING! Don't use angle = pi/2 (or multiplies), it will return
        a blank image (or maybe garbage).

        NOTE: angle is in the image not in game, so for the left side of a
        block angle = 30 degree.
        """

        # Take the same size as trasform_image_side
        img = img.resize((12,12), Image.ANTIALIAS)

        # some values
        cos_angle = math.cos(angle)
        sin_angle = math.sin(angle)

        # function_x and function_y are used to keep the result image in the 
        # same position, and constant_x and constant_y are the coordinates
        # for the center for angle = 0.
        constant_x = 6.
        constant_y = 6.
        function_x = 6.*(1-cos_angle)
        function_y = -6*sin_angle
        big_term = ( (sin_angle * (function_x + constant_x)) - cos_angle* (function_y + constant_y))/cos_angle

        # The numpy array is not really used, but is helpful to 
        # see the matrix used for the transformation.
        transform = numpy.array([[1./cos_angle, 0, -(function_x + constant_x)/cos_angle],
                                 [-sin_angle/(cos_angle), 1., big_term ],
                                 [0, 0, 1.]])

        transform = tuple(transform[0]) + tuple(transform[1])

        newimg = img.transform((24,24), Image.AFFINE, transform)

        return newimg


    def build_block(self, top, side):
        """From a top texture and a side texture, build a block image.
        top and side should be 16x16 image objects. Returns a 24x24 image

        """
        img = Image.new("RGBA", (24,24), self.bgcolor)

        original_texture = top.copy()
        top = self.transform_image_top(top)

        if not side:
            alpha_over(img, top, (0,0), top)
            return img

        side = self.transform_image_side(side)
        otherside = side.transpose(Image.FLIP_LEFT_RIGHT)

        # Darken the sides slightly. These methods also affect the alpha layer,
        # so save them first (we don't want to "darken" the alpha layer making
        # the block transparent)
        sidealpha = side.split()[3]
        side = ImageEnhance.Brightness(side).enhance(0.9)
        side.putalpha(sidealpha)
        othersidealpha = otherside.split()[3]
        otherside = ImageEnhance.Brightness(otherside).enhance(0.8)
        otherside.putalpha(othersidealpha)

        alpha_over(img, top, (0,0), top)
        alpha_over(img, side, (0,6), side)
        alpha_over(img, otherside, (12,6), otherside)

        # Manually touch up 6 pixels that leave a gap because of how the
        # shearing works out. This makes the blocks perfectly tessellate-able
        for x,y in [(13,23), (17,21), (21,19)]:
            # Copy a pixel to x,y from x-1,y
            img.putpixel((x,y), img.getpixel((x-1,y)))
        for x,y in [(3,4), (7,2), (11,0)]:
            # Copy a pixel to x,y from x+1,y
            img.putpixel((x,y), img.getpixel((x+1,y)))

        return img

    def build_full_block(self, top, side1, side2, side3, side4, bottom=None):
        """From a top texture, a bottom texture and 4 different side textures,
        build a full block with four differnts faces. All images should be 16x16 
        image objects. Returns a 24x24 image. Can be used to render any block.

        side1 is in the -y face of the cube     (top left, east)
        side2 is in the +x                      (top right, south)
        side3 is in the -x                      (bottom left, north)
        side4 is in the +y                      (bottom right, west)

        A non transparent block uses top, side 3 and side 4.

        If top is a tuple then first item is the top image and the second
        item is an increment (integer) from 0 to 16 (pixels in the
        original minecraft texture). This increment will be used to crop the
        side images and to paste the top image increment pixels lower, so if
        you use an increment of 8, it will draw a half-block.

        NOTE: this method uses the bottom of the texture image (as done in 
        minecraft with beds and cackes)

        """

        increment = 0
        if isinstance(top, tuple):
            increment = int(round((top[1] / 16.)*12.)) # range increment in the block height in pixels (half texture size)
            crop_height = increment
            top = top[0]
            if side1 is not None:
                side1 = side1.copy()
                ImageDraw.Draw(side1).rectangle((0, 0,16,crop_height),outline=(0,0,0,0),fill=(0,0,0,0))
            if side2 is not None:
                side2 = side2.copy()
                ImageDraw.Draw(side2).rectangle((0, 0,16,crop_height),outline=(0,0,0,0),fill=(0,0,0,0))
            if side3 is not None:
                side3 = side3.copy()
                ImageDraw.Draw(side3).rectangle((0, 0,16,crop_height),outline=(0,0,0,0),fill=(0,0,0,0))
            if side4 is not None:
                side4 = side4.copy()
                ImageDraw.Draw(side4).rectangle((0, 0,16,crop_height),outline=(0,0,0,0),fill=(0,0,0,0))

        img = Image.new("RGBA", (24,24), self.bgcolor)

        # first back sides
        if side1 is not None :
            side1 = self.transform_image_side(side1)
            side1 = side1.transpose(Image.FLIP_LEFT_RIGHT)

            # Darken this side.
            sidealpha = side1.split()[3]
            side1 = ImageEnhance.Brightness(side1).enhance(0.9)
            side1.putalpha(sidealpha)        

            alpha_over(img, side1, (0,0), side1)


        if side2 is not None :
            side2 = self.transform_image_side(side2)

            # Darken this side.
            sidealpha2 = side2.split()[3]
            side2 = ImageEnhance.Brightness(side2).enhance(0.8)
            side2.putalpha(sidealpha2)

            alpha_over(img, side2, (12,0), side2)

        if bottom is not None :
            bottom = self.transform_image_top(bottom)
            alpha_over(img, bottom, (0,12), bottom)

        # front sides
        if side3 is not None :
            side3 = self.transform_image_side(side3)

            # Darken this side
            sidealpha = side3.split()[3]
            side3 = ImageEnhance.Brightness(side3).enhance(0.9)
            side3.putalpha(sidealpha)

            alpha_over(img, side3, (0,6), side3)

        if side4 is not None :
            side4 = self.transform_image_side(side4)
            side4 = side4.transpose(Image.FLIP_LEFT_RIGHT)

            # Darken this side
            sidealpha = side4.split()[3]
            side4 = ImageEnhance.Brightness(side4).enhance(0.8)
            side4.putalpha(sidealpha)

            alpha_over(img, side4, (12,6), side4)

        if top is not None :
            top = self.transform_image_top(top)
            alpha_over(img, top, (0, increment), top)

        return img

    def build_sprite(self, side):
        """From a side texture, create a sprite-like texture such as those used
        for spiderwebs or flowers."""
        img = Image.new("RGBA", (24,24), self.bgcolor)

        side = self.transform_image_side(side)
        otherside = side.transpose(Image.FLIP_LEFT_RIGHT)

        alpha_over(img, side, (6,3), side)
        alpha_over(img, otherside, (6,3), otherside)
        return img

    def build_billboard(self, tex):
        """From a texture, create a billboard-like texture such as
        those used for tall grass or melon stems.
        """
        img = Image.new("RGBA", (24,24), self.bgcolor)

        front = tex.resize((14, 12), Image.ANTIALIAS)
        alpha_over(img, front, (5,9))
        return img

    def generate_opaque_mask(self, img):
        """ Takes the alpha channel of the image and generates a mask
        (used for lighting the block) that deprecates values of alpha
        smallers than 50, and sets every other value to 255. """

        alpha = img.split()[3]
        return alpha.point(lambda a: int(min(a, 25.5) * 10))

    def tint_texture(self, im, c):
        # apparently converting to grayscale drops the alpha channel?
        i = ImageOps.colorize(ImageOps.grayscale(im), (0,0,0), c)
        i.putalpha(im.split()[3]); # copy the alpha band back in. assuming RGBA
        return i

    def generate_texture_tuple(self, img):
        """ This takes an image and returns the needed tuple for the
        blockmap array."""
        if img is None:
            return None
        return (img, self.generate_opaque_mask(img))

##
## The other big one: @material and associated framework
##

# global variables to collate information in @material decorators
blockmap_generators = {}

known_blocks = set()
used_datas = set()
max_blockid = 0
max_data = 0

transparent_blocks = set()
solid_blocks = set()
fluid_blocks = set()
nospawn_blocks = set()
nodata_blocks = set()

# the material registration decorator
def material(blockid=[], data=[0], **kwargs):
    # mapping from property name to the set to store them in
    properties = {"transparent" : transparent_blocks, "solid" : solid_blocks, "fluid" : fluid_blocks, "nospawn" : nospawn_blocks, "nodata" : nodata_blocks}
    
    # make sure blockid and data are iterable
    try:
        iter(blockid)
    except:
        blockid = [blockid,]
    try:
        iter(data)
    except:
        data = [data,]
        
    def inner_material(func):
        global blockmap_generators
        global max_data, max_blockid

        # create a wrapper function with a known signature
        @functools.wraps(func)
        def func_wrapper(texobj, blockid, data):
            return func(texobj, blockid, data)
        
        used_datas.update(data)
        if max(data) >= max_data:
            max_data = max(data) + 1
        
        for block in blockid:
            # set the property sets appropriately
            known_blocks.update([block])
            if block >= max_blockid:
                max_blockid = block + 1
            for prop in properties:
                try:
                    if block in kwargs.get(prop, []):
                        properties[prop].update([block])
                except TypeError:
                    if kwargs.get(prop, False):
                        properties[prop].update([block])
            
            # populate blockmap_generators with our function
            for d in data:
                blockmap_generators[(block, d)] = func_wrapper
        
        return func_wrapper
    return inner_material

# shortcut function for pure blocks, default to solid, nodata
def block(blockid=[], top_image=None, side_image=None, **kwargs):
    new_kwargs = {'solid' : True, 'nodata' : True}
    new_kwargs.update(kwargs)
    
    if top_image is None:
        raise ValueError("top_image was not provided")
    
    if side_image is None:
        side_image = top_image
    
    @material(blockid=blockid, **new_kwargs)
    def inner_block(self, unused_id, unused_data):
        return self.build_block(self.load_image_texture(top_image), self.load_image_texture(side_image))
    return inner_block

# shortcut function for sprite blocks, defaults to transparent, nodata
def sprite(blockid=[], imagename=None, **kwargs):
    new_kwargs = {'transparent' : True, 'nodata' : True}
    new_kwargs.update(kwargs)
    
    if imagename is None:
        raise ValueError("imagename was not provided")
    
    @material(blockid=blockid, **new_kwargs)
    def inner_sprite(self, unused_id, unused_data):
        return self.build_sprite(self.load_image_texture(imagename))
    return inner_sprite

# shortcut function for billboard blocks, defaults to transparent, nodata
def billboard(blockid=[], imagename=None, **kwargs):
    new_kwargs = {'transparent' : True, 'nodata' : True}
    new_kwargs.update(kwargs)
    
    if imagename is None:
        raise ValueError("imagename was not provided")
    
    @material(blockid=blockid, **new_kwargs)
    def inner_billboard(self, unused_id, unused_data):
        return self.build_billboard(self.load_image_texture(imagename))
    return inner_billboard

##
## and finally: actual texture definitions
##

# stone
block(blockid=1, top_image="assets/minecraft/textures/blocks/stone.png")

@material(blockid=2, data=range(11)+[0x10,], solid=True)
def grass(self, blockid, data):
    # 0x10 bit means SNOW
    side_img = self.load_image_texture("assets/minecraft/textures/blocks/grass_side.png")
    if data & 0x10:
        side_img = self.load_image_texture("assets/minecraft/textures/blocks/grass_side_snowed.png")
    img = self.build_block(self.load_image_texture("assets/minecraft/textures/blocks/grass_top.png"), side_img)
    if not data & 0x10:
        alpha_over(img, self.biome_grass_texture, (0, 0), self.biome_grass_texture)
    return img

# dirt
@material(blockid=3, data=range(3), solid=True)
def dirt_blocks(self, blockid, data):
    side_img = self.load_image_texture("assets/minecraft/textures/blocks/dirt.png")
    if data == 0: # normal
        img =  self.build_block(self.load_image_texture("assets/minecraft/textures/blocks/dirt.png"), side_img)
    if data == 1: # grassless
        img = self.build_block(self.load_image_texture("assets/minecraft/textures/blocks/dirt.png"), side_img)
    if data == 2: # podzol
        side_img = self.load_image_texture("assets/minecraft/textures/blocks/dirt_podzol_side.png")
        img = self.build_block(self.load_image_texture("assets/minecraft/textures/blocks/dirt_podzol_top.png"), side_img)
    return img

# cobblestone
block(blockid=4, top_image="assets/minecraft/textures/blocks/cobblestone.png")

# wooden planks
@material(blockid=5, data=range(6), solid=True)
def wooden_planks(self, blockid, data):
    if data == 0: # normal
        return self.build_block(self.load_image_texture("assets/minecraft/textures/blocks/planks_oak.png"), self.load_image_texture("assets/minecraft/textures/blocks/planks_oak.png"))
    if data == 1: # pine
        return self.build_block(self.load_image_texture("assets/minecraft/textures/blocks/planks_spruce.png"),self.load_image_texture("assets/minecraft/textures/blocks/planks_spruce.png"))
    if data == 2: # birch
        return self.build_block(self.load_image_texture("assets/minecraft/textures/blocks/planks_birch.png"),self.load_image_texture("assets/minecraft/textures/blocks/planks_birch.png"))
    if data == 3: # jungle wood
        return self.build_block(self.load_image_texture("assets/minecraft/textures/blocks/planks_jungle.png"),self.load_image_texture("assets/minecraft/textures/blocks/planks_jungle.png"))
    if data == 4: # acacia
        return self.build_block(self.load_image_texture("assets/minecraft/textures/blocks/planks_acacia.png"),self.load_image_texture("assets/minecraft/textures/blocks/planks_acacia.png"))
    if data == 5: # dark oak
        return self.build_block(self.load_image_texture("assets/minecraft/textures/blocks/planks_big_oak.png"),self.load_image_texture("assets/minecraft/textures/blocks/planks_big_oak.png"))

@material(blockid=6, data=range(16), transparent=True)
def saplings(self, blockid, data):
    # usual saplings
    tex = self.load_image_texture("assets/minecraft/textures/blocks/sapling_oak.png")
    
    if data & 0x3 == 1: # spruce sapling
        tex = self.load_image_texture("assets/minecraft/textures/blocks/sapling_spruce.png")
    elif data & 0x3 == 2: # birch sapling
        tex = self.load_image_texture("assets/minecraft/textures/blocks/sapling_birch.png")
    elif data & 0x3 == 3: # jungle sapling
        tex = self.load_image_texture("assets/minecraft/textures/blocks/sapling_jungle.png")
    elif data & 0x3 == 4: # acacia sapling
        tex = self.load_image_texture("assets/minecraft/textures/blocks/sapling_acacia.png")
    elif data & 0x3 == 5: # dark oak/roofed oak/big oak sapling
        tex = self.load_image_texture("assets/minecraft/textures/blocks/sapling_roofed_oak.png")
    return self.build_sprite(tex)

# bedrock
block(blockid=7, top_image="assets/minecraft/textures/blocks/bedrock.png")

@material(blockid=8, data=range(16), fluid=True, transparent=True, nospawn=True)
def water(self, blockid, data):
    watertex = self.load_water()
    return self.build_block(watertex, watertex)

# other water, glass, and ice (no inner surfaces)
# uses pseudo-ancildata found in iterate.c
@material(blockid=[9, 20, 79, 95], data=range(512), fluid=(9,), transparent=True, nospawn=True, solid=(79, 20, 95))
def no_inner_surfaces(self, blockid, data):
    if blockid == 9:
        texture = self.load_water()
    elif blockid == 20:
        texture = self.load_image_texture("assets/minecraft/textures/blocks/glass.png")
    elif blockid == 95:
        texture = self.load_image_texture("assets/minecraft/textures/blocks/glass_%s.png" % color_map[data & 0x0f])
    else:
        texture = self.load_image_texture("assets/minecraft/textures/blocks/ice.png")

    # now that we've used the lower 4 bits to get color, shift down to get the 5 bits that encode face hiding
    if blockid != 9: # water doesn't have a shifted pseudodata
        data = data >> 4

    if (data & 0b10000) == 16:
        top = texture
    else:
        top = None
        
    if (data & 0b0001) == 1:
        side1 = texture    # top left
    else:
        side1 = None
    
    if (data & 0b1000) == 8:
        side2 = texture    # top right           
    else:
        side2 = None
    
    if (data & 0b0010) == 2:
        side3 = texture    # bottom left    
    else:
        side3 = None
    
    if (data & 0b0100) == 4:
        side4 = texture    # bottom right
    else:
        side4 = None
    
    # if nothing shown do not draw at all
    if top is None and side3 is None and side4 is None:
        return None
    
    img = self.build_full_block(top,None,None,side3,side4)
    return img

@material(blockid=[10, 11], data=range(16), fluid=True, transparent=False, nospawn=True)
def lava(self, blockid, data):
    lavatex = self.load_lava()
    return self.build_block(lavatex, lavatex)

# sand
@material(blockid=12, data=range(2), solid=True)
def sand_blocks(self, blockid, data):
    if data == 0: # normal
        img = self.build_block(self.load_image_texture("assets/minecraft/textures/blocks/sand.png"), self.load_image_texture("assets/minecraft/textures/blocks/sand.png"))
    if data == 1: # red
        img = self.build_block(self.load_image_texture("assets/minecraft/textures/blocks/red_sand.png"), self.load_image_texture("assets/minecraft/textures/blocks/red_sand.png"))
    return img

# gravel
block(blockid=13, top_image="assets/minecraft/textures/blocks/gravel.png")
# gold ore
block(blockid=14, top_image="assets/minecraft/textures/blocks/gold_ore.png")
# iron ore
block(blockid=15, top_image="assets/minecraft/textures/blocks/iron_ore.png")
# coal ore
block(blockid=16, top_image="assets/minecraft/textures/blocks/coal_ore.png")

@material(blockid=[17,162], data=range(12), solid=True)
def wood(self, blockid, data):
    # extract orientation and wood type frorm data bits
    wood_type = data & 3
    wood_orientation = data & 12
    if self.rotation == 1:
        if wood_orientation == 4: wood_orientation = 8
        elif wood_orientation == 8: wood_orientation = 4
    elif self.rotation == 3:
        if wood_orientation == 4: wood_orientation = 8
        elif wood_orientation == 8: wood_orientation = 4

    # choose textures
    if blockid == 17: # regular wood:
        if wood_type == 0: # normal
            top = self.load_image_texture("assets/minecraft/textures/blocks/log_oak_top.png")
            side = self.load_image_texture("assets/minecraft/textures/blocks/log_oak.png")
        if wood_type == 1: # spruce
            top = self.load_image_texture("assets/minecraft/textures/blocks/log_spruce_top.png")
            side = self.load_image_texture("assets/minecraft/textures/blocks/log_spruce.png")
        if wood_type == 2: # birch
            top = self.load_image_texture("assets/minecraft/textures/blocks/log_birch_top.png")
            side = self.load_image_texture("assets/minecraft/textures/blocks/log_birch.png")
        if wood_type == 3: # jungle wood
            top = self.load_image_texture("assets/minecraft/textures/blocks/log_jungle_top.png")
            side = self.load_image_texture("assets/minecraft/textures/blocks/log_jungle.png")
    elif blockid == 162: # acacia/dark wood:
        if wood_type == 0: # acacia
            top = self.load_image_texture("assets/minecraft/textures/blocks/log_acacia_top.png")
            side = self.load_image_texture("assets/minecraft/textures/blocks/log_acacia.png")
        elif wood_type == 1: # dark oak
            top = self.load_image_texture("assets/minecraft/textures/blocks/log_big_oak_top.png")
            side = self.load_image_texture("assets/minecraft/textures/blocks/log_big_oak.png")
        else:
            top = self.load_image_texture("assets/minecraft/textures/blocks/log_acacia_top.png")
            side = self.load_image_texture("assets/minecraft/textures/blocks/log_acacia.png")

    # choose orientation and paste textures
    if wood_orientation == 0:
        return self.build_block(top, side)
    elif wood_orientation == 4: # east-west orientation
        return self.build_full_block(side.rotate(90), None, None, top, side.rotate(90))
    elif wood_orientation == 8: # north-south orientation
        return self.build_full_block(side, None, None, side.rotate(270), top)

@material(blockid=[18, 161], data=range(16), transparent=True, solid=True)
def leaves(self, blockid, data):
    # mask out the bits 4 and 8
    # they are used for player placed and check-for-decay blocks
    data = data & 0x7
    t = self.load_image_texture("assets/minecraft/textures/blocks/leaves_oak.png")
    if (blockid, data) == (18, 1): # pine!
        t = self.load_image_texture("assets/minecraft/textures/blocks/leaves_spruce.png")
    elif (blockid, data) == (18, 2): # birth tree
        t = self.load_image_texture("assets/minecraft/textures/blocks/leaves_birch.png")
    elif (blockid, data) == (18, 3): # jungle tree
        t = self.load_image_texture("assets/minecraft/textures/blocks/leaves_jungle.png")
    elif (blockid, data) == (161, 4): # acacia tree
        t = self.load_image_texture("assets/minecraft/textures/blocks/leaves_acacia.png")
    elif (blockid, data) == (161, 5): 
        t = self.load_image_texture("assets/minecraft/textures/blocks/leaves_big_oak.png")
    return self.build_block(t, t)

# sponge
block(blockid=19, top_image="assets/minecraft/textures/blocks/sponge.png")
# lapis lazuli ore
block(blockid=21, top_image="assets/minecraft/textures/blocks/lapis_ore.png")
# lapis lazuli block
block(blockid=22, top_image="assets/minecraft/textures/blocks/lapis_block.png")

# dispensers, dropper, furnaces, and burning furnaces
@material(blockid=[23, 61, 62, 158], data=range(6), solid=True)
def furnaces(self, blockid, data):
    # first, do the rotation if needed
    if self.rotation == 1:
        if data == 2: data = 5
        elif data == 3: data = 4
        elif data == 4: data = 2
        elif data == 5: data = 3
    elif self.rotation == 2:
        if data == 2: data = 3
        elif data == 3: data = 2
        elif data == 4: data = 5
        elif data == 5: data = 4
    elif self.rotation == 3:
        if data == 2: data = 4
        elif data == 3: data = 5
        elif data == 4: data = 3
        elif data == 5: data = 2
    
    top = self.load_image_texture("assets/minecraft/textures/blocks/furnace_top.png")
    side = self.load_image_texture("assets/minecraft/textures/blocks/furnace_side.png")
    
    if blockid == 61:
        front = self.load_image_texture("assets/minecraft/textures/blocks/furnace_front_off.png")
    elif blockid == 62:
        front = self.load_image_texture("assets/minecraft/textures/blocks/furnace_front_on.png")
    elif blockid == 23:
        front = self.load_image_texture("assets/minecraft/textures/blocks/dispenser_front_horizontal.png")
        if data == 0: # dispenser pointing down
            return self.build_block(top, top)
        elif data == 1: # dispenser pointing up
            dispenser_top = self.load_image_texture("assets/minecraft/textures/blocks/dispenser_front_vertical.png")
            return self.build_block(dispenser_top, top)
    elif blockid == 158:
        front = self.load_image_texture("assets/minecraft/textures/blocks/dropper_front_horizontal.png")
        if data == 0: # dropper pointing down
            return self.build_block(top, top)
        elif data == 1: # dispenser pointing up
            dropper_top = self.load_image_texture("assets/minecraft/textures/blocks/dropper_front_vertical.png")
            return self.build_block(dropper_top, top)
    
    if data == 3: # pointing west
        return self.build_full_block(top, None, None, side, front)
    elif data == 4: # pointing north
        return self.build_full_block(top, None, None, front, side)
    else: # in any other direction the front can't be seen
        return self.build_full_block(top, None, None, side, side)

# sandstone
@material(blockid=24, data=range(3), solid=True)
def sandstone(self, blockid, data):
    top = self.load_image_texture("assets/minecraft/textures/blocks/sandstone_top.png")
    if data == 0: # normal
        return self.build_block(top, self.load_image_texture("assets/minecraft/textures/blocks/sandstone_normal.png"))
    if data == 1: # hieroglyphic
        return self.build_block(top, self.load_image_texture("assets/minecraft/textures/blocks/sandstone_carved.png"))
    if data == 2: # soft
        return self.build_block(top, self.load_image_texture("assets/minecraft/textures/blocks/sandstone_smooth.png"))

# note block
block(blockid=25, top_image="assets/minecraft/textures/blocks/noteblock.png")

@material(blockid=26, data=range(12), transparent=True, nospawn=True)
def bed(self, blockid, data):
    # first get rotation done
    # Masked to not clobber block head/foot info
    if self.rotation == 1:
        if (data & 0b0011) == 0: data = data & 0b1100 | 1
        elif (data & 0b0011) == 1: data = data & 0b1100 | 2
        elif (data & 0b0011) == 2: data = data & 0b1100 | 3
        elif (data & 0b0011) == 3: data = data & 0b1100 | 0
    elif self.rotation == 2:
        if (data & 0b0011) == 0: data = data & 0b1100 | 2
        elif (data & 0b0011) == 1: data = data & 0b1100 | 3
        elif (data & 0b0011) == 2: data = data & 0b1100 | 0
        elif (data & 0b0011) == 3: data = data & 0b1100 | 1
    elif self.rotation == 3:
        if (data & 0b0011) == 0: data = data & 0b1100 | 3
        elif (data & 0b0011) == 1: data = data & 0b1100 | 0
        elif (data & 0b0011) == 2: data = data & 0b1100 | 1
        elif (data & 0b0011) == 3: data = data & 0b1100 | 2
    
    increment = 8
    left_face = None
    right_face = None
    if data & 0x8 == 0x8: # head of the bed
        top = self.load_image_texture("assets/minecraft/textures/blocks/bed_head_top.png")
        if data & 0x00 == 0x00: # head pointing to West
            top = top.copy().rotate(270)
            left_face = self.load_image_texture("assets/minecraft/textures/blocks/bed_head_side.png")
            right_face = self.load_image_texture("assets/minecraft/textures/blocks/bed_head_end.png")
        if data & 0x01 == 0x01: # ... North
            top = top.rotate(270)
            left_face = self.load_image_texture("assets/minecraft/textures/blocks/bed_head_end.png")
            right_face = self.load_image_texture("assets/minecraft/textures/blocks/bed_head_side.png")
        if data & 0x02 == 0x02: # East
            top = top.rotate(180)
            left_face = self.load_image_texture("assets/minecraft/textures/blocks/bed_head_side.png").transpose(Image.FLIP_LEFT_RIGHT)
            right_face = None
        if data & 0x03 == 0x03: # South
            right_face = None
            right_face = self.load_image_texture("assets/minecraft/textures/blocks/bed_head_side.png").transpose(Image.FLIP_LEFT_RIGHT)
    
    else: # foot of the bed
        top = self.load_image_texture("assets/minecraft/textures/blocks/bed_feet_top.png")
        if data & 0x00 == 0x00: # head pointing to West
            top = top.rotate(270)
            left_face = self.load_image_texture("assets/minecraft/textures/blocks/bed_feet_side.png")
            right_face = None
        if data & 0x01 == 0x01: # ... North
            top = top.rotate(270)
            left_face = None
            right_face = self.load_image_texture("assets/minecraft/textures/blocks/bed_feet_side.png")
        if data & 0x02 == 0x02: # East
            top = top.rotate(180)
            left_face = self.load_image_texture("assets/minecraft/textures/blocks/bed_feet_side.png").transpose(Image.FLIP_LEFT_RIGHT)
            right_face = self.load_image_texture("assets/minecraft/textures/blocks/bed_feet_end.png").transpose(Image.FLIP_LEFT_RIGHT)
        if data & 0x03 == 0x03: # South
            left_face = self.load_image_texture("assets/minecraft/textures/blocks/bed_feet_end.png")
            right_face = self.load_image_texture("assets/minecraft/textures/blocks/bed_feet_side.png").transpose(Image.FLIP_LEFT_RIGHT)
    
    top = (top, increment)
    return self.build_full_block(top, None, None, left_face, right_face)

# powered, detector, activator and normal rails
@material(blockid=[27, 28, 66, 157], data=range(14), transparent=True)
def rails(self, blockid, data):
    # first, do rotation
    # Masked to not clobber powered rail on/off info
    # Ascending and flat straight
    if self.rotation == 1:
        if (data & 0b0111) == 0: data = data & 0b1000 | 1
        elif (data & 0b0111) == 1: data = data & 0b1000 | 0
        elif (data & 0b0111) == 2: data = data & 0b1000 | 5
        elif (data & 0b0111) == 3: data = data & 0b1000 | 4
        elif (data & 0b0111) == 4: data = data & 0b1000 | 2
        elif (data & 0b0111) == 5: data = data & 0b1000 | 3
    elif self.rotation == 2:
        if (data & 0b0111) == 2: data = data & 0b1000 | 3
        elif (data & 0b0111) == 3: data = data & 0b1000 | 2
        elif (data & 0b0111) == 4: data = data & 0b1000 | 5
        elif (data & 0b0111) == 5: data = data & 0b1000 | 4
    elif self.rotation == 3:
        if (data & 0b0111) == 0: data = data & 0b1000 | 1
        elif (data & 0b0111) == 1: data = data & 0b1000 | 0
        elif (data & 0b0111) == 2: data = data & 0b1000 | 4
        elif (data & 0b0111) == 3: data = data & 0b1000 | 5
        elif (data & 0b0111) == 4: data = data & 0b1000 | 3
        elif (data & 0b0111) == 5: data = data & 0b1000 | 2
    if blockid == 66: # normal minetrack only
        #Corners
        if self.rotation == 1:
            if data == 6: data = 7
            elif data == 7: data = 8
            elif data == 8: data = 6
            elif data == 9: data = 9
        elif self.rotation == 2:
            if data == 6: data = 8
            elif data == 7: data = 9
            elif data == 8: data = 6
            elif data == 9: data = 7
        elif self.rotation == 3:
            if data == 6: data = 9
            elif data == 7: data = 6
            elif data == 8: data = 8
            elif data == 9: data = 7
    img = Image.new("RGBA", (24,24), self.bgcolor)
    
    if blockid == 27: # powered rail
        if data & 0x8 == 0: # unpowered
            raw_straight = self.load_image_texture("assets/minecraft/textures/blocks/rail_golden.png")
            raw_corner = self.load_image_texture("assets/minecraft/textures/blocks/rail_normal_turned.png")    # they don't exist but make the code
                                                # much simplier
        elif data & 0x8 == 0x8: # powered
            raw_straight = self.load_image_texture("assets/minecraft/textures/blocks/rail_golden_powered.png")
            raw_corner = self.load_image_texture("assets/minecraft/textures/blocks/rail_normal_turned.png")    # leave corners for code simplicity
        # filter the 'powered' bit
        data = data & 0x7
            
    elif blockid == 28: # detector rail
        raw_straight = self.load_image_texture("assets/minecraft/textures/blocks/rail_detector.png")
        raw_corner = self.load_image_texture("assets/minecraft/textures/blocks/rail_normal_turned.png")    # leave corners for code simplicity
        
    elif blockid == 66: # normal rail
        raw_straight = self.load_image_texture("assets/minecraft/textures/blocks/rail_normal.png")
        raw_corner = self.load_image_texture("assets/minecraft/textures/blocks/rail_normal_turned.png")

    elif blockid == 157: # activator rail
        if data & 0x8 == 0: # unpowered
            raw_straight = self.load_image_texture("assets/minecraft/textures/blocks/rail_activator.png")
            raw_corner = self.load_image_texture("assets/minecraft/textures/blocks/rail_normal_turned.png")    # they don't exist but make the code
                                                # much simplier
        elif data & 0x8 == 0x8: # powered
            raw_straight = self.load_image_texture("assets/minecraft/textures/blocks/rail_activator_powered.png")
            raw_corner = self.load_image_texture("assets/minecraft/textures/blocks/rail_normal_turned.png")    # leave corners for code simplicity
        # filter the 'powered' bit
        data = data & 0x7
        
    ## use transform_image to scale and shear
    if data == 0:
        track = self.transform_image_top(raw_straight)
        alpha_over(img, track, (0,12), track)
    elif data == 6:
        track = self.transform_image_top(raw_corner)
        alpha_over(img, track, (0,12), track)
    elif data == 7:
        track = self.transform_image_top(raw_corner.rotate(270))
        alpha_over(img, track, (0,12), track)
    elif data == 8:
        # flip
        track = self.transform_image_top(raw_corner.transpose(Image.FLIP_TOP_BOTTOM).rotate(90))
        alpha_over(img, track, (0,12), track)
    elif data == 9:
        track = self.transform_image_top(raw_corner.transpose(Image.FLIP_TOP_BOTTOM))
        alpha_over(img, track, (0,12), track)
    elif data == 1:
        track = self.transform_image_top(raw_straight.rotate(90))
        alpha_over(img, track, (0,12), track)
        
    #slopes
    elif data == 2: # slope going up in +x direction
        track = self.transform_image_slope(raw_straight)
        track = track.transpose(Image.FLIP_LEFT_RIGHT)
        alpha_over(img, track, (2,0), track)
        # the 2 pixels move is needed to fit with the adjacent tracks
        
    elif data == 3: # slope going up in -x direction
        # tracks are sprites, in this case we are seeing the "side" of 
        # the sprite, so draw a line to make it beautiful.
        ImageDraw.Draw(img).line([(11,11),(23,17)],fill=(164,164,164))
        # grey from track texture (exterior grey).
        # the track doesn't start from image corners, be carefull drawing the line!
    elif data == 4: # slope going up in -y direction
        track = self.transform_image_slope(raw_straight)
        alpha_over(img, track, (0,0), track)
        
    elif data == 5: # slope going up in +y direction
        # same as "data == 3"
        ImageDraw.Draw(img).line([(1,17),(12,11)],fill=(164,164,164))
        
    return img

# sticky and normal piston body
@material(blockid=[29, 33], data=[0,1,2,3,4,5,8,9,10,11,12,13], transparent=True, solid=True, nospawn=True)
def piston(self, blockid, data):
    # first, rotation
    # Masked to not clobber block head/foot info
    if self.rotation == 1:
        if (data & 0b0111) == 2: data = data & 0b1000 | 5
        elif (data & 0b0111) == 3: data = data & 0b1000 | 4
        elif (data & 0b0111) == 4: data = data & 0b1000 | 2
        elif (data & 0b0111) == 5: data = data & 0b1000 | 3
    elif self.rotation == 2:
        if (data & 0b0111) == 2: data = data & 0b1000 | 3
        elif (data & 0b0111) == 3: data = data & 0b1000 | 2
        elif (data & 0b0111) == 4: data = data & 0b1000 | 5
        elif (data & 0b0111) == 5: data = data & 0b1000 | 4
    elif self.rotation == 3:
        if (data & 0b0111) == 2: data = data & 0b1000 | 4
        elif (data & 0b0111) == 3: data = data & 0b1000 | 5
        elif (data & 0b0111) == 4: data = data & 0b1000 | 3
        elif (data & 0b0111) == 5: data = data & 0b1000 | 2
    
    if blockid == 29: # sticky
        piston_t = self.load_image_texture("assets/minecraft/textures/blocks/piston_top_sticky.png").copy()
    else: # normal
        piston_t = self.load_image_texture("assets/minecraft/textures/blocks/piston_top_normal.png").copy()
        
    # other textures
    side_t = self.load_image_texture("assets/minecraft/textures/blocks/piston_side.png").copy()
    back_t = self.load_image_texture("assets/minecraft/textures/blocks/piston_bottom.png").copy()
    interior_t = self.load_image_texture("assets/minecraft/textures/blocks/piston_inner.png").copy()
    
    if data & 0x08 == 0x08: # pushed out, non full blocks, tricky stuff
        # remove piston texture from piston body
        ImageDraw.Draw(side_t).rectangle((0, 0,16,3),outline=(0,0,0,0),fill=(0,0,0,0))
        
        if data & 0x07 == 0x0: # down
            side_t = side_t.rotate(180)
            img = self.build_full_block(back_t ,None ,None ,side_t, side_t)
            
        elif data & 0x07 == 0x1: # up
            img = self.build_full_block((interior_t, 4) ,None ,None ,side_t, side_t)
            
        elif data & 0x07 == 0x2: # east
            img = self.build_full_block(side_t , None, None ,side_t.rotate(90), back_t)
            
        elif data & 0x07 == 0x3: # west
            img = self.build_full_block(side_t.rotate(180) ,None ,None ,side_t.rotate(270), None)
            temp = self.transform_image_side(interior_t)
            temp = temp.transpose(Image.FLIP_LEFT_RIGHT)
            alpha_over(img, temp, (9,5), temp)
            
        elif data & 0x07 == 0x4: # north
            img = self.build_full_block(side_t.rotate(90) ,None ,None , None, side_t.rotate(270))
            temp = self.transform_image_side(interior_t)
            alpha_over(img, temp, (3,5), temp)
            
        elif data & 0x07 == 0x5: # south
            img = self.build_full_block(side_t.rotate(270) ,None , None ,back_t, side_t.rotate(90))

    else: # pushed in, normal full blocks, easy stuff
        if data & 0x07 == 0x0: # down
            side_t = side_t.rotate(180)
            img = self.build_full_block(back_t ,None ,None ,side_t, side_t)
        elif data & 0x07 == 0x1: # up
            img = self.build_full_block(piston_t ,None ,None ,side_t, side_t)
        elif data & 0x07 == 0x2: # east 
            img = self.build_full_block(side_t ,None ,None ,side_t.rotate(90), back_t)
        elif data & 0x07 == 0x3: # west
            img = self.build_full_block(side_t.rotate(180) ,None ,None ,side_t.rotate(270), piston_t)
        elif data & 0x07 == 0x4: # north
            img = self.build_full_block(side_t.rotate(90) ,None ,None ,piston_t, side_t.rotate(270))
        elif data & 0x07 == 0x5: # south
            img = self.build_full_block(side_t.rotate(270) ,None ,None ,back_t, side_t.rotate(90))
            
    return img

# sticky and normal piston shaft
@material(blockid=34, data=[0,1,2,3,4,5,8,9,10,11,12,13], transparent=True, nospawn=True)
def piston_extension(self, blockid, data):
    # first, rotation
    # Masked to not clobber block head/foot info
    if self.rotation == 1:
        if (data & 0b0111) == 2: data = data & 0b1000 | 5
        elif (data & 0b0111) == 3: data = data & 0b1000 | 4
        elif (data & 0b0111) == 4: data = data & 0b1000 | 2
        elif (data & 0b0111) == 5: data = data & 0b1000 | 3
    elif self.rotation == 2:
        if (data & 0b0111) == 2: data = data & 0b1000 | 3
        elif (data & 0b0111) == 3: data = data & 0b1000 | 2
        elif (data & 0b0111) == 4: data = data & 0b1000 | 5
        elif (data & 0b0111) == 5: data = data & 0b1000 | 4
    elif self.rotation == 3:
        if (data & 0b0111) == 2: data = data & 0b1000 | 4
        elif (data & 0b0111) == 3: data = data & 0b1000 | 5
        elif (data & 0b0111) == 4: data = data & 0b1000 | 3
        elif (data & 0b0111) == 5: data = data & 0b1000 | 2
    
    if (data & 0x8) == 0x8: # sticky
        piston_t = self.load_image_texture("assets/minecraft/textures/blocks/piston_top_sticky.png").copy()
    else: # normal
        piston_t = self.load_image_texture("assets/minecraft/textures/blocks/piston_top_normal.png").copy()
    
    # other textures
    side_t = self.load_image_texture("assets/minecraft/textures/blocks/piston_side.png").copy()
    back_t = self.load_image_texture("assets/minecraft/textures/blocks/piston_top_normal.png").copy()
    # crop piston body
    ImageDraw.Draw(side_t).rectangle((0, 4,16,16),outline=(0,0,0,0),fill=(0,0,0,0))
    
    # generate the horizontal piston extension stick
    h_stick = Image.new("RGBA", (24,24), self.bgcolor)
    temp = self.transform_image_side(side_t)
    alpha_over(h_stick, temp, (1,7), temp)
    temp = self.transform_image_top(side_t.rotate(90))
    alpha_over(h_stick, temp, (1,1), temp)
    # Darken it
    sidealpha = h_stick.split()[3]
    h_stick = ImageEnhance.Brightness(h_stick).enhance(0.85)
    h_stick.putalpha(sidealpha)
    
    # generate the vertical piston extension stick
    v_stick = Image.new("RGBA", (24,24), self.bgcolor)
    temp = self.transform_image_side(side_t.rotate(90))
    alpha_over(v_stick, temp, (12,6), temp)
    temp = temp.transpose(Image.FLIP_LEFT_RIGHT)
    alpha_over(v_stick, temp, (1,6), temp)
    # Darken it
    sidealpha = v_stick.split()[3]
    v_stick = ImageEnhance.Brightness(v_stick).enhance(0.85)
    v_stick.putalpha(sidealpha)
    
    # Piston orientation is stored in the 3 first bits
    if data & 0x07 == 0x0: # down
        side_t = side_t.rotate(180)
        img = self.build_full_block((back_t, 12) ,None ,None ,side_t, side_t)
        alpha_over(img, v_stick, (0,-3), v_stick)
    elif data & 0x07 == 0x1: # up
        img = Image.new("RGBA", (24,24), self.bgcolor)
        img2 = self.build_full_block(piston_t ,None ,None ,side_t, side_t)
        alpha_over(img, v_stick, (0,4), v_stick)
        alpha_over(img, img2, (0,0), img2)
    elif data & 0x07 == 0x2: # east 
        img = self.build_full_block(side_t ,None ,None ,side_t.rotate(90), None)
        temp = self.transform_image_side(back_t).transpose(Image.FLIP_LEFT_RIGHT)
        alpha_over(img, temp, (2,2), temp)
        alpha_over(img, h_stick, (6,3), h_stick)
    elif data & 0x07 == 0x3: # west
        img = Image.new("RGBA", (24,24), self.bgcolor)
        img2 = self.build_full_block(side_t.rotate(180) ,None ,None ,side_t.rotate(270), piston_t)
        alpha_over(img, h_stick, (0,0), h_stick)
        alpha_over(img, img2, (0,0), img2)            
    elif data & 0x07 == 0x4: # north
        img = self.build_full_block(side_t.rotate(90) ,None ,None , piston_t, side_t.rotate(270))
        alpha_over(img, h_stick.transpose(Image.FLIP_LEFT_RIGHT), (0,0), h_stick.transpose(Image.FLIP_LEFT_RIGHT))
    elif data & 0x07 == 0x5: # south
        img = Image.new("RGBA", (24,24), self.bgcolor)
        img2 = self.build_full_block(side_t.rotate(270) ,None ,None ,None, side_t.rotate(90))
        temp = self.transform_image_side(back_t)
        alpha_over(img2, temp, (10,2), temp)
        alpha_over(img, img2, (0,0), img2)
        alpha_over(img, h_stick.transpose(Image.FLIP_LEFT_RIGHT), (-3,2), h_stick.transpose(Image.FLIP_LEFT_RIGHT))
        
    return img

# cobweb
sprite(blockid=30, imagename="assets/minecraft/textures/blocks/web.png", nospawn=True)

@material(blockid=31, data=range(3), transparent=True)
def tall_grass(self, blockid, data):
    if data == 0: # dead shrub
        texture = self.load_image_texture("assets/minecraft/textures/blocks/deadbush.png")
    elif data == 1: # tall grass
        texture = self.load_image_texture("assets/minecraft/textures/blocks/tallgrass.png")
    elif data == 2: # fern
        texture = self.load_image_texture("assets/minecraft/textures/blocks/fern.png")
    
    return self.build_billboard(texture)

# dead bush
billboard(blockid=32, imagename="assets/minecraft/textures/blocks/deadbush.png")

@material(blockid=35, data=range(16), solid=True)
def wool(self, blockid, data):
    texture = self.load_image_texture("assets/minecraft/textures/blocks/wool_colored_%s.png" % color_map[data])
    
    return self.build_block(texture, texture)

# dandelion
sprite(blockid=37, imagename="assets/minecraft/textures/blocks/flower_dandelion.png")

# flowers
@material(blockid=38, data=range(10), transparent=True)
def flower(self, blockid, data):
    flower_map = ["rose", "blue_orchid", "allium", "houstonia", "tulip_red", "tulip_orange",
                  "tulip_white", "tulip_pink", "oxeye_daisy", "dandelion"]
    texture = self.load_image_texture("assets/minecraft/textures/blocks/flower_%s.png" % flower_map[data])

    return self.build_billboard(texture)

# brown mushroom
sprite(blockid=39, imagename="assets/minecraft/textures/blocks/mushroom_brown.png")
# red mushroom
sprite(blockid=40, imagename="assets/minecraft/textures/blocks/mushroom_red.png")
# block of gold
block(blockid=41, top_image="assets/minecraft/textures/blocks/gold_block.png")
# block of iron
block(blockid=42, top_image="assets/minecraft/textures/blocks/iron_block.png")

# double slabs and slabs
# these wooden slabs are unobtainable without cheating, they are still
# here because lots of pre-1.3 worlds use this blocks
@material(blockid=[43, 44], data=range(16), transparent=(44,), solid=True)
def slabs(self, blockid, data):
    if blockid == 44: 
        texture = data & 7
    else: # data > 8 are special double slabs
        texture = data
    if texture== 0: # stone slab
        top = self.load_image_texture("assets/minecraft/textures/blocks/stone_slab_top.png")
        side = self.load_image_texture("assets/minecraft/textures/blocks/stone_slab_side.png")
    elif texture== 1: # smooth stone
        top = self.load_image_texture("assets/minecraft/textures/blocks/sandstone_top.png")
        side = self.load_image_texture("assets/minecraft/textures/blocks/sandstone_normal.png")
    elif texture== 2: # wooden slab
        top = side = self.load_image_texture("assets/minecraft/textures/blocks/planks_oak.png")
    elif texture== 3: # cobblestone slab
        top = side = self.load_image_texture("assets/minecraft/textures/blocks/cobblestone.png")
    elif texture== 4: # brick
        top = side = self.load_image_texture("assets/minecraft/textures/blocks/brick.png")
    elif texture== 5: # stone brick
        top = side = self.load_image_texture("assets/minecraft/textures/blocks/stonebrick.png")
    elif texture== 6: # nether brick slab
        top = side = self.load_image_texture("assets/minecraft/textures/blocks/nether_brick.png")
    elif texture== 7: #quartz        
        top = side = self.load_image_texture("assets/minecraft/textures/blocks/quartz_block_side.png")
    elif texture== 8: # special stone double slab with top texture only
        top = side = self.load_image_texture("assets/minecraft/textures/blocks/stone_slab_top.png")
    elif texture== 9: # special sandstone double slab with top texture only
        top = side = self.load_image_texture("assets/minecraft/textures/blocks/sandstone_top.png")
    else:
        return None
    
    if blockid == 43: # double slab
        return self.build_block(top, side)
    
    # cut the side texture in half
    mask = side.crop((0,8,16,16))
    side = Image.new(side.mode, side.size, self.bgcolor)
    alpha_over(side, mask,(0,0,16,8), mask)
    
    # plain slab
    top = self.transform_image_top(top)
    side = self.transform_image_side(side)
    otherside = side.transpose(Image.FLIP_LEFT_RIGHT)
    
    sidealpha = side.split()[3]
    side = ImageEnhance.Brightness(side).enhance(0.9)
    side.putalpha(sidealpha)
    othersidealpha = otherside.split()[3]
    otherside = ImageEnhance.Brightness(otherside).enhance(0.8)
    otherside.putalpha(othersidealpha)
    
    # upside down slab
    delta = 0
    if data & 8 == 8:
        delta = 6
    
    img = Image.new("RGBA", (24,24), self.bgcolor)
    alpha_over(img, side, (0,12 - delta), side)
    alpha_over(img, otherside, (12,12 - delta), otherside)
    alpha_over(img, top, (0,6 - delta), top)
    
    return img

# brick block
block(blockid=45, top_image="assets/minecraft/textures/blocks/brick.png")
# TNT
block(blockid=46, top_image="assets/minecraft/textures/blocks/tnt_top.png", side_image="assets/minecraft/textures/blocks/tnt_side.png", nospawn=True)
# bookshelf
block(blockid=47, top_image="assets/minecraft/textures/blocks/planks_oak.png", side_image="assets/minecraft/textures/blocks/bookshelf.png")
# moss stone
block(blockid=48, top_image="assets/minecraft/textures/blocks/cobblestone_mossy.png")
# obsidian
block(blockid=49, top_image="assets/minecraft/textures/blocks/obsidian.png")

# torch, redstone torch (off), redstone torch(on)
@material(blockid=[50, 75, 76], data=[1, 2, 3, 4, 5], transparent=True)
def torches(self, blockid, data):
    # first, rotations
    if self.rotation == 1:
        if data == 1: data = 3
        elif data == 2: data = 4
        elif data == 3: data = 2
        elif data == 4: data = 1
    elif self.rotation == 2:
        if data == 1: data = 2
        elif data == 2: data = 1
        elif data == 3: data = 4
        elif data == 4: data = 3
    elif self.rotation == 3:
        if data == 1: data = 4
        elif data == 2: data = 3
        elif data == 3: data = 1
        elif data == 4: data = 2
    
    # choose the proper texture
    if blockid == 50: # torch
        small = self.load_image_texture("assets/minecraft/textures/blocks/torch_on.png")
    elif blockid == 75: # off redstone torch
        small = self.load_image_texture("assets/minecraft/textures/blocks/redstone_torch_off.png")
    else: # on redstone torch
        small = self.load_image_texture("assets/minecraft/textures/blocks/redstone_torch_on.png")
        
    # compose a torch bigger than the normal
    # (better for doing transformations)
    torch = Image.new("RGBA", (16,16), self.bgcolor)
    alpha_over(torch,small,(-4,-3))
    alpha_over(torch,small,(-5,-2))
    alpha_over(torch,small,(-3,-2))
    
    # angle of inclination of the texture
    rotation = 15
    
    if data == 1: # pointing south
        torch = torch.rotate(-rotation, Image.NEAREST) # nearest filter is more nitid.
        img = self.build_full_block(None, None, None, torch, None, None)
        
    elif data == 2: # pointing north
        torch = torch.rotate(rotation, Image.NEAREST)
        img = self.build_full_block(None, None, torch, None, None, None)
        
    elif data == 3: # pointing west
        torch = torch.rotate(rotation, Image.NEAREST)
        img = self.build_full_block(None, torch, None, None, None, None)
        
    elif data == 4: # pointing east
        torch = torch.rotate(-rotation, Image.NEAREST)
        img = self.build_full_block(None, None, None, None, torch, None)
        
    elif data == 5: # standing on the floor
        # compose a "3d torch".
        img = Image.new("RGBA", (24,24), self.bgcolor)
        
        small_crop = small.crop((2,2,14,14))
        slice = small_crop.copy()
        ImageDraw.Draw(slice).rectangle((6,0,12,12),outline=(0,0,0,0),fill=(0,0,0,0))
        ImageDraw.Draw(slice).rectangle((0,0,4,12),outline=(0,0,0,0),fill=(0,0,0,0))
        
        alpha_over(img, slice, (7,5))
        alpha_over(img, small_crop, (6,6))
        alpha_over(img, small_crop, (7,6))
        alpha_over(img, slice, (7,7))
        
    return img

# fire
@material(blockid=51, data=range(16), transparent=True)
def fire(self, blockid, data):
    firetextures = self.load_fire()
    side1 = self.transform_image_side(firetextures[0])
    side2 = self.transform_image_side(firetextures[1]).transpose(Image.FLIP_LEFT_RIGHT)
    
    img = Image.new("RGBA", (24,24), self.bgcolor)

    alpha_over(img, side1, (12,0), side1)
    alpha_over(img, side2, (0,0), side2)

    alpha_over(img, side1, (0,6), side1)
    alpha_over(img, side2, (12,6), side2)
    
    return img

# monster spawner
block(blockid=52, top_image="assets/minecraft/textures/blocks/mob_spawner.png", transparent=True)

# wooden, cobblestone, red brick, stone brick, netherbrick, sandstone, spruce, birch, jungle and quartz stairs.
@material(blockid=[53,67,108,109,114,128,134,135,136,156,163,164], data=range(128), transparent=True, solid=True, nospawn=True)
def stairs(self, blockid, data):
    # preserve the upside-down bit
    upside_down = data & 0x4

    # find solid quarters within the top or bottom half of the block
    #                   NW           NE           SE           SW
    quarters = [data & 0x8, data & 0x10, data & 0x20, data & 0x40]

    # rotate the quarters so we can pretend northdirection is always upper-left
    numpy.roll(quarters, [0,1,3,2][self.rotation])
    nw,ne,se,sw = quarters

    if blockid == 53: # wooden
        texture = self.load_image_texture("assets/minecraft/textures/blocks/planks_oak.png").copy()
    elif blockid == 67: # cobblestone
        texture = self.load_image_texture("assets/minecraft/textures/blocks/cobblestone.png").copy()
    elif blockid == 108: # red brick stairs
        texture = self.load_image_texture("assets/minecraft/textures/blocks/brick.png").copy()
    elif blockid == 109: # stone brick stairs
        texture = self.load_image_texture("assets/minecraft/textures/blocks/stonebrick.png").copy()
    elif blockid == 114: # netherbrick stairs
        texture = self.load_image_texture("assets/minecraft/textures/blocks/nether_brick.png").copy()
    elif blockid == 128: # sandstone stairs
        texture = self.load_image_texture("assets/minecraft/textures/blocks/sandstone_normal.png").copy()
    elif blockid == 134: # spruce wood stairs
        texture = self.load_image_texture("assets/minecraft/textures/blocks/planks_spruce.png").copy()
    elif blockid == 135: # birch wood  stairs
        texture = self.load_image_texture("assets/minecraft/textures/blocks/planks_birch.png").copy()
    elif blockid == 136: # jungle good stairs
        texture = self.load_image_texture("assets/minecraft/textures/blocks/planks_jungle.png").copy()
    elif blockid == 156: # quartz block stairs
        texture = self.load_image_texture("assets/minecraft/textures/blocks/quartz_block_side.png").copy()
    elif blockid == 163: # acacia wood stairs
        texture = self.load_image_texture("assets/minecraft/textures/blocks/planks_acacia.png").copy()
    elif blockid == 164: # dark oak stairs
        texture = self.load_image_texture("assets/minecraft/textures/blocks/planks_big_oak.png").copy()

    outside_l = texture.copy()
    outside_r = texture.copy()
    inside_l = texture.copy()
    inside_r = texture.copy()

    # sandstone & quartz stairs have special top texture
    if blockid == 128:
        texture = self.load_image_texture("assets/minecraft/textures/blocks/sandstone_top.png").copy()
    elif blockid == 156:
        texture = self.load_image_texture("assets/minecraft/textures/blocks/quartz_block_top.png").copy()

    slab_top = texture.copy()

    push = 8 if upside_down else 0

    def rect(tex,coords):
        ImageDraw.Draw(tex).rectangle(coords,outline=(0,0,0,0),fill=(0,0,0,0))

    # cut out top or bottom half from inner surfaces
    rect(inside_l, (0,8-push,15,15-push))
    rect(inside_r, (0,8-push,15,15-push))

    # cut out missing or obstructed quarters from each surface
    if not nw:
        rect(outside_l, (0,push,7,7+push))
        rect(texture, (0,0,7,7))
    if not nw or sw:
        rect(inside_r, (8,push,15,7+push)) # will be flipped
    if not ne:
        rect(texture, (8,0,15,7))
    if not ne or nw:
        rect(inside_l, (0,push,7,7+push))
    if not ne or se:
        rect(inside_r, (0,push,7,7+push)) # will be flipped
    if not se:
        rect(outside_r, (0,push,7,7+push)) # will be flipped
        rect(texture, (8,8,15,15))
    if not se or sw:
        rect(inside_l, (8,push,15,7+push))
    if not sw:
        rect(outside_l, (8,push,15,7+push))
        rect(outside_r, (8,push,15,7+push)) # will be flipped
        rect(texture, (0,8,7,15))

    img = Image.new("RGBA", (24,24), self.bgcolor)

    if upside_down:
        # top should have no cut-outs after all
        texture = slab_top
    else:
        # render the slab-level surface
        slab_top = self.transform_image_top(slab_top)
        alpha_over(img, slab_top, (0,6))

    # render inner left surface
    inside_l = self.transform_image_side(inside_l)
    # Darken the vertical part of the second step
    sidealpha = inside_l.split()[3]
    # darken it a bit more than usual, looks better
    inside_l = ImageEnhance.Brightness(inside_l).enhance(0.8)
    inside_l.putalpha(sidealpha)
    alpha_over(img, inside_l, (6,3))

    # render inner right surface
    inside_r = self.transform_image_side(inside_r).transpose(Image.FLIP_LEFT_RIGHT)
    # Darken the vertical part of the second step
    sidealpha = inside_r.split()[3]
    # darken it a bit more than usual, looks better
    inside_r = ImageEnhance.Brightness(inside_r).enhance(0.7)
    inside_r.putalpha(sidealpha)
    alpha_over(img, inside_r, (6,3))

    # render outer surfaces
    alpha_over(img, self.build_full_block(texture, None, None, outside_l, outside_r))

    return img

# normal, locked (used in april's fool day), ender and trapped chest
# NOTE:  locked chest used to be id95 (which is now stained glass)
@material(blockid=[54,130,146], data=range(30), transparent = True)
def chests(self, blockid, data):
    # the first 3 bits are the orientation as stored in minecraft, 
    # bits 0x8 and 0x10 indicate which half of the double chest is it.
    
    # first, do the rotation if needed
    orientation_data = data & 7
    if self.rotation == 1:
        if orientation_data == 2: data = 5 | (data & 24)
        elif orientation_data == 3: data = 4 | (data & 24)
        elif orientation_data == 4: data = 2 | (data & 24)
        elif orientation_data == 5: data = 3 | (data & 24)
    elif self.rotation == 2:
        if orientation_data == 2: data = 3 | (data & 24)
        elif orientation_data == 3: data = 2 | (data & 24)
        elif orientation_data == 4: data = 5 | (data & 24)
        elif orientation_data == 5: data = 4 | (data & 24)
    elif self.rotation == 3:
        if orientation_data == 2: data = 4 | (data & 24)
        elif orientation_data == 3: data = 5 | (data & 24)
        elif orientation_data == 4: data = 3 | (data & 24)
        elif orientation_data == 5: data = 2 | (data & 24)
    
    if blockid == 130 and not data in [2,3,4,5]: return None
        # iterate.c will only return the ancil data (without pseudo 
        # ancil data) for locked and ender chests, so only 
        # ancilData = 2,3,4,5 are used for this blockids
    
    if data & 24 == 0:
        if blockid == 130: t = self.load_image("ender.png")
        else:
            try:
                t = self.load_image("normal.png")
            except (TextureException, IOError):
                t = self.load_image("chest.png")

        # the textures is no longer in terrain.png, get it from
        # item/chest.png and get by cropping all the needed stuff
        if t.size != (64,64): t = t.resize((64,64), Image.ANTIALIAS)
        # top
        top = t.crop((14,0,28,14))
        top.load() # every crop need a load, crop is a lazy operation
                   # see PIL manual
        img = Image.new("RGBA", (16,16), self.bgcolor)
        alpha_over(img,top,(1,1))
        top = img
        # front
        front_top = t.crop((14,14,28,19))
        front_top.load()
        front_bottom = t.crop((14,34,28,43))
        front_bottom.load()
        front_lock = t.crop((1,0,3,4))
        front_lock.load()
        front = Image.new("RGBA", (16,16), self.bgcolor)
        alpha_over(front,front_top, (1,1))
        alpha_over(front,front_bottom, (1,6))
        alpha_over(front,front_lock, (7,3))
        # left side
        # left side, right side, and back are esentially the same for
        # the default texture, we take it anyway just in case other
        # textures make use of it.
        side_l_top = t.crop((0,14,14,19))
        side_l_top.load()
        side_l_bottom = t.crop((0,34,14,43))
        side_l_bottom.load()
        side_l = Image.new("RGBA", (16,16), self.bgcolor)
        alpha_over(side_l,side_l_top, (1,1))
        alpha_over(side_l,side_l_bottom, (1,6))
        # right side
        side_r_top = t.crop((28,14,43,20))
        side_r_top.load()
        side_r_bottom = t.crop((28,33,42,43))
        side_r_bottom.load()
        side_r = Image.new("RGBA", (16,16), self.bgcolor)
        alpha_over(side_r,side_l_top, (1,1))
        alpha_over(side_r,side_l_bottom, (1,6))
        # back
        back_top = t.crop((42,14,56,18))
        back_top.load()
        back_bottom = t.crop((42,33,56,43))
        back_bottom.load()
        back = Image.new("RGBA", (16,16), self.bgcolor)
        alpha_over(back,side_l_top, (1,1))
        alpha_over(back,side_l_bottom, (1,6))

    else:
        # large chest
        # the textures is no longer in terrain.png, get it from 
        # item/chest.png and get all the needed stuff
        t = self.load_image("normal_double.png")
        if t.size != (128,64): t = t.resize((128,64), Image.ANTIALIAS)
        # top
        top = t.crop((14,0,44,14))
        top.load()
        img = Image.new("RGBA", (32,16), self.bgcolor)
        alpha_over(img,top,(1,1))
        top = img
        # front
        front_top = t.crop((14,14,44,18))
        front_top.load()
        front_bottom = t.crop((14,33,44,43))
        front_bottom.load()
        front_lock = t.crop((1,0,3,5))
        front_lock.load()
        front = Image.new("RGBA", (32,16), self.bgcolor)
        alpha_over(front,front_top,(1,1))
        alpha_over(front,front_bottom,(1,5))
        alpha_over(front,front_lock,(15,3))
        # left side
        side_l_top = t.crop((0,14,14,18))
        side_l_top.load()
        side_l_bottom = t.crop((0,33,14,43))
        side_l_bottom.load()
        side_l = Image.new("RGBA", (16,16), self.bgcolor)
        alpha_over(side_l,side_l_top, (1,1))
        alpha_over(side_l,side_l_bottom,(1,5))
        # right side
        side_r_top = t.crop((44,14,58,18))
        side_r_top.load()
        side_r_bottom = t.crop((44,33,58,43))
        side_r_bottom.load()
        side_r = Image.new("RGBA", (16,16), self.bgcolor)
        alpha_over(side_r,side_r_top, (1,1))
        alpha_over(side_r,side_r_bottom,(1,5))
        # back
        back_top = t.crop((58,14,88,18))
        back_top.load()
        back_bottom = t.crop((58,33,88,43))
        back_bottom.load()
        back = Image.new("RGBA", (32,16), self.bgcolor)
        alpha_over(back,back_top,(1,1))
        alpha_over(back,back_bottom,(1,5))
        

        if data & 24 == 8: # double chest, first half
            top = top.crop((0,0,16,16))
            top.load()
            front = front.crop((0,0,16,16))
            front.load()
            back = back.crop((0,0,16,16))
            back.load()
            #~ side = side_l

        elif data & 24 == 16: # double, second half
            top = top.crop((16,0,32,16))
            top.load()
            front = front.crop((16,0,32,16))
            front.load()
            back = back.crop((16,0,32,16))
            back.load()
            #~ side = side_r

        else: # just in case
            return None

    # compose the final block
    img = Image.new("RGBA", (24,24), self.bgcolor)
    if data & 7 == 2: # north
        side = self.transform_image_side(side_r)
        alpha_over(img, side, (1,7))
        back = self.transform_image_side(back)
        alpha_over(img, back.transpose(Image.FLIP_LEFT_RIGHT), (11,7))
        front = self.transform_image_side(front)
        top = self.transform_image_top(top.rotate(180))
        alpha_over(img, top, (0,2))

    elif data & 7 == 3: # south
        side = self.transform_image_side(side_l)
        alpha_over(img, side, (1,7))
        front = self.transform_image_side(front).transpose(Image.FLIP_LEFT_RIGHT)
        top = self.transform_image_top(top.rotate(180))
        alpha_over(img, top, (0,2))
        alpha_over(img, front,(11,7))

    elif data & 7 == 4: # west
        side = self.transform_image_side(side_r)
        alpha_over(img, side.transpose(Image.FLIP_LEFT_RIGHT), (11,7))
        front = self.transform_image_side(front)
        alpha_over(img, front,(1,7))
        top = self.transform_image_top(top.rotate(270))
        alpha_over(img, top, (0,2))

    elif data & 7 == 5: # east
        back = self.transform_image_side(back)
        side = self.transform_image_side(side_l).transpose(Image.FLIP_LEFT_RIGHT)
        alpha_over(img, side, (11,7))
        alpha_over(img, back, (1,7))
        top = self.transform_image_top(top.rotate(270))
        alpha_over(img, top, (0,2))
        
    else: # just in case
        img = None

    return img

# redstone wire
# uses pseudo-ancildata found in iterate.c
@material(blockid=55, data=range(128), transparent=True)
def wire(self, blockid, data):

    if data & 0b1000000 == 64: # powered redstone wire
        redstone_wire_t = self.load_image_texture("assets/minecraft/textures/blocks/redstone_dust_line.png")
        redstone_wire_t = self.tint_texture(redstone_wire_t,(255,0,0))

        redstone_cross_t = self.load_image_texture("assets/minecraft/textures/blocks/redstone_dust_cross.png")
        redstone_cross_t = self.tint_texture(redstone_cross_t,(255,0,0))

        
    else: # unpowered redstone wire
        redstone_wire_t = self.load_image_texture("assets/minecraft/textures/blocks/redstone_dust_line.png")
        redstone_wire_t = self.tint_texture(redstone_wire_t,(48,0,0))
        
        redstone_cross_t = self.load_image_texture("assets/minecraft/textures/blocks/redstone_dust_cross.png")
        redstone_cross_t = self.tint_texture(redstone_cross_t,(48,0,0))

    # generate an image per redstone direction
    branch_top_left = redstone_cross_t.copy()
    ImageDraw.Draw(branch_top_left).rectangle((0,0,4,15),outline=(0,0,0,0),fill=(0,0,0,0))
    ImageDraw.Draw(branch_top_left).rectangle((11,0,15,15),outline=(0,0,0,0),fill=(0,0,0,0))
    ImageDraw.Draw(branch_top_left).rectangle((0,11,15,15),outline=(0,0,0,0),fill=(0,0,0,0))
    
    branch_top_right = redstone_cross_t.copy()
    ImageDraw.Draw(branch_top_right).rectangle((0,0,15,4),outline=(0,0,0,0),fill=(0,0,0,0))
    ImageDraw.Draw(branch_top_right).rectangle((0,0,4,15),outline=(0,0,0,0),fill=(0,0,0,0))
    ImageDraw.Draw(branch_top_right).rectangle((0,11,15,15),outline=(0,0,0,0),fill=(0,0,0,0))
    
    branch_bottom_right = redstone_cross_t.copy()
    ImageDraw.Draw(branch_bottom_right).rectangle((0,0,15,4),outline=(0,0,0,0),fill=(0,0,0,0))
    ImageDraw.Draw(branch_bottom_right).rectangle((0,0,4,15),outline=(0,0,0,0),fill=(0,0,0,0))
    ImageDraw.Draw(branch_bottom_right).rectangle((11,0,15,15),outline=(0,0,0,0),fill=(0,0,0,0))

    branch_bottom_left = redstone_cross_t.copy()
    ImageDraw.Draw(branch_bottom_left).rectangle((0,0,15,4),outline=(0,0,0,0),fill=(0,0,0,0))
    ImageDraw.Draw(branch_bottom_left).rectangle((11,0,15,15),outline=(0,0,0,0),fill=(0,0,0,0))
    ImageDraw.Draw(branch_bottom_left).rectangle((0,11,15,15),outline=(0,0,0,0),fill=(0,0,0,0))
            
    # generate the bottom texture
    if data & 0b111111 == 0:
        bottom = redstone_cross_t.copy()
    
    elif data & 0b1111 == 10: #= 0b1010 redstone wire in the x direction
        bottom = redstone_wire_t.copy()
        
    elif data & 0b1111 == 5: #= 0b0101 redstone wire in the y direction
        bottom = redstone_wire_t.copy().rotate(90)
    
    else:
        bottom = Image.new("RGBA", (16,16), self.bgcolor)
        if (data & 0b0001) == 1:
            alpha_over(bottom,branch_top_left)
            
        if (data & 0b1000) == 8:
            alpha_over(bottom,branch_top_right)
            
        if (data & 0b0010) == 2:
            alpha_over(bottom,branch_bottom_left)
            
        if (data & 0b0100) == 4:
            alpha_over(bottom,branch_bottom_right)

    # check for going up redstone wire
    if data & 0b100000 == 32:
        side1 = redstone_wire_t.rotate(90)
    else:
        side1 = None
        
    if data & 0b010000 == 16:
        side2 = redstone_wire_t.rotate(90)
    else:
        side2 = None
        
    img = self.build_full_block(None,side1,side2,None,None,bottom)

    return img

# diamond ore
block(blockid=56, top_image="assets/minecraft/textures/blocks/diamond_ore.png")
# diamond block
block(blockid=57, top_image="assets/minecraft/textures/blocks/diamond_block.png")

# crafting table
# needs two different sides
@material(blockid=58, solid=True, nodata=True)
def crafting_table(self, blockid, data):
    top = self.load_image_texture("assets/minecraft/textures/blocks/crafting_table_top.png")
    side3 = self.load_image_texture("assets/minecraft/textures/blocks/crafting_table_side.png")
    side4 = self.load_image_texture("assets/minecraft/textures/blocks/crafting_table_front.png")
    
    img = self.build_full_block(top, None, None, side3, side4, None)
    return img

# crops
@material(blockid=59, data=range(8), transparent=True, nospawn=True)
def crops(self, blockid, data):
    raw_crop = self.load_image_texture("assets/minecraft/textures/blocks/wheat_stage_%d.png" % data)
    crop1 = self.transform_image_top(raw_crop)
    crop2 = self.transform_image_side(raw_crop)
    crop3 = crop2.transpose(Image.FLIP_LEFT_RIGHT)

    img = Image.new("RGBA", (24,24), self.bgcolor)
    alpha_over(img, crop1, (0,12), crop1)
    alpha_over(img, crop2, (6,3), crop2)
    alpha_over(img, crop3, (6,3), crop3)
    return img

# farmland
@material(blockid=60, data=range(9), solid=True)
def farmland(self, blockid, data):
    top = self.load_image_texture("assets/minecraft/textures/blocks/farmland_wet.png")
    if data == 0:
        top = self.load_image_texture("assets/minecraft/textures/blocks/farmland_dry.png")
    return self.build_block(top, self.load_image_texture("assets/minecraft/textures/blocks/dirt.png"))

# signposts
@material(blockid=63, data=range(16), transparent=True)
def signpost(self, blockid, data):

    # first rotations
    if self.rotation == 1:
        data = (data + 4) % 16
    elif self.rotation == 2:
        data = (data + 8) % 16
    elif self.rotation == 3:
        data = (data + 12) % 16

    texture = self.load_image_texture("assets/minecraft/textures/blocks/planks_oak.png").copy()
    # cut the planks to the size of a signpost
    ImageDraw.Draw(texture).rectangle((0,12,15,15),outline=(0,0,0,0),fill=(0,0,0,0))

    # If the signpost is looking directly to the image, draw some 
    # random dots, they will look as text.
    if data in (0,1,2,3,4,5,15):
        for i in range(15):
            x = randint(4,11)
            y = randint(3,7)
            texture.putpixel((x,y),(0,0,0,255))

    # Minecraft uses wood texture for the signpost stick
    texture_stick = self.load_image_texture("assets/minecraft/textures/blocks/log_oak.png")
    texture_stick = texture_stick.resize((12,12), Image.ANTIALIAS)
    ImageDraw.Draw(texture_stick).rectangle((2,0,12,12),outline=(0,0,0,0),fill=(0,0,0,0))

    img = Image.new("RGBA", (24,24), self.bgcolor)

    #         W                N      ~90       E                   S        ~270
    angles = (330.,345.,0.,15.,30.,55.,95.,120.,150.,165.,180.,195.,210.,230.,265.,310.)
    angle = math.radians(angles[data])
    post = self.transform_image_angle(texture, angle)

    # choose the position of the "3D effect"
    incrementx = 0
    if data in (1,6,7,8,9,14):
        incrementx = -1
    elif data in (3,4,5,11,12,13):
        incrementx = +1

    alpha_over(img, texture_stick,(11, 8),texture_stick)
    # post2 is a brighter signpost pasted with a small shift,
    # gives to the signpost some 3D effect.
    post2 = ImageEnhance.Brightness(post).enhance(1.2)
    alpha_over(img, post2,(incrementx, -3),post2)
    alpha_over(img, post, (0,-2), post)

    return img


# wooden and iron door
# uses pseudo-ancildata found in iterate.c
@material(blockid=[64,71], data=range(32), transparent=True)
def door(self, blockid, data):
    #Masked to not clobber block top/bottom & swung info
    if self.rotation == 1:
        if (data & 0b00011) == 0: data = data & 0b11100 | 1
        elif (data & 0b00011) == 1: data = data & 0b11100 | 2
        elif (data & 0b00011) == 2: data = data & 0b11100 | 3
        elif (data & 0b00011) == 3: data = data & 0b11100 | 0
    elif self.rotation == 2:
        if (data & 0b00011) == 0: data = data & 0b11100 | 2
        elif (data & 0b00011) == 1: data = data & 0b11100 | 3
        elif (data & 0b00011) == 2: data = data & 0b11100 | 0
        elif (data & 0b00011) == 3: data = data & 0b11100 | 1
    elif self.rotation == 3:
        if (data & 0b00011) == 0: data = data & 0b11100 | 3
        elif (data & 0b00011) == 1: data = data & 0b11100 | 0
        elif (data & 0b00011) == 2: data = data & 0b11100 | 1
        elif (data & 0b00011) == 3: data = data & 0b11100 | 2

    if data & 0x8 == 0x8: # top of the door
        raw_door = self.load_image_texture("assets/minecraft/textures/blocks/%s.png" % ("door_wood_upper" if blockid == 64 else "door_iron_upper"))
    else: # bottom of the door
        raw_door = self.load_image_texture("assets/minecraft/textures/blocks/%s.png" % ("door_wood_lower" if blockid == 64 else "door_iron_lower"))
    
    # if you want to render all doors as closed, then force
    # force closed to be True
    if data & 0x4 == 0x4:
        closed = False
    else:
        closed = True
    
    if data & 0x10 == 0x10:
        # hinge on the left (facing same door direction)
        hinge_on_left = True
    else:
        # hinge on the right (default single door)
        hinge_on_left = False

    # mask out the high bits to figure out the orientation 
    img = Image.new("RGBA", (24,24), self.bgcolor)
    if (data & 0x03) == 0: # facing west when closed
        if hinge_on_left:
            if closed:
                tex = self.transform_image_side(raw_door.transpose(Image.FLIP_LEFT_RIGHT))
                alpha_over(img, tex, (0,6), tex)
            else:
                # flip first to set the doornob on the correct side
                tex = self.transform_image_side(raw_door.transpose(Image.FLIP_LEFT_RIGHT))
                tex = tex.transpose(Image.FLIP_LEFT_RIGHT)
                alpha_over(img, tex, (12,6), tex)
        else:
            if closed:
                tex = self.transform_image_side(raw_door)    
                alpha_over(img, tex, (0,6), tex)
            else:
                # flip first to set the doornob on the correct side
                tex = self.transform_image_side(raw_door.transpose(Image.FLIP_LEFT_RIGHT))
                tex = tex.transpose(Image.FLIP_LEFT_RIGHT)
                alpha_over(img, tex, (0,0), tex)
    
    if (data & 0x03) == 1: # facing north when closed
        if hinge_on_left:
            if closed:
                tex = self.transform_image_side(raw_door).transpose(Image.FLIP_LEFT_RIGHT)
                alpha_over(img, tex, (0,0), tex)
            else:
                # flip first to set the doornob on the correct side
                tex = self.transform_image_side(raw_door)
                alpha_over(img, tex, (0,6), tex)

        else:
            if closed:
                tex = self.transform_image_side(raw_door).transpose(Image.FLIP_LEFT_RIGHT)
                alpha_over(img, tex, (0,0), tex)
            else:
                # flip first to set the doornob on the correct side
                tex = self.transform_image_side(raw_door)
                alpha_over(img, tex, (12,0), tex)

                
    if (data & 0x03) == 2: # facing east when closed
        if hinge_on_left:
            if closed:
                tex = self.transform_image_side(raw_door)
                alpha_over(img, tex, (12,0), tex)
            else:
                # flip first to set the doornob on the correct side
                tex = self.transform_image_side(raw_door)
                tex = tex.transpose(Image.FLIP_LEFT_RIGHT)
                alpha_over(img, tex, (0,0), tex)
        else:
            if closed:
                tex = self.transform_image_side(raw_door.transpose(Image.FLIP_LEFT_RIGHT))
                alpha_over(img, tex, (12,0), tex)
            else:
                # flip first to set the doornob on the correct side
                tex = self.transform_image_side(raw_door).transpose(Image.FLIP_LEFT_RIGHT)
                alpha_over(img, tex, (12,6), tex)

    if (data & 0x03) == 3: # facing south when closed
        if hinge_on_left:
            if closed:
                tex = self.transform_image_side(raw_door).transpose(Image.FLIP_LEFT_RIGHT)
                alpha_over(img, tex, (12,6), tex)
            else:
                # flip first to set the doornob on the correct side
                tex = self.transform_image_side(raw_door.transpose(Image.FLIP_LEFT_RIGHT))
                alpha_over(img, tex, (12,0), tex)
        else:
            if closed:
                tex = self.transform_image_side(raw_door.transpose(Image.FLIP_LEFT_RIGHT))
                tex = tex.transpose(Image.FLIP_LEFT_RIGHT)
                alpha_over(img, tex, (12,6), tex)
            else:
                # flip first to set the doornob on the correct side
                tex = self.transform_image_side(raw_door.transpose(Image.FLIP_LEFT_RIGHT))
                alpha_over(img, tex, (0,6), tex)

    return img

# ladder
@material(blockid=65, data=[2, 3, 4, 5], transparent=True)
def ladder(self, blockid, data):

    # first rotations
    if self.rotation == 1:
        if data == 2: data = 5
        elif data == 3: data = 4
        elif data == 4: data = 2
        elif data == 5: data = 3
    elif self.rotation == 2:
        if data == 2: data = 3
        elif data == 3: data = 2
        elif data == 4: data = 5
        elif data == 5: data = 4
    elif self.rotation == 3:
        if data == 2: data = 4
        elif data == 3: data = 5
        elif data == 4: data = 3
        elif data == 5: data = 2

    img = Image.new("RGBA", (24,24), self.bgcolor)
    raw_texture = self.load_image_texture("assets/minecraft/textures/blocks/ladder.png")

    if data == 5:
        # normally this ladder would be obsured by the block it's attached to
        # but since ladders can apparently be placed on transparent blocks, we 
        # have to render this thing anyway.  same for data == 2
        tex = self.transform_image_side(raw_texture)
        alpha_over(img, tex, (0,6), tex)
        return img
    if data == 2:
        tex = self.transform_image_side(raw_texture).transpose(Image.FLIP_LEFT_RIGHT)
        alpha_over(img, tex, (12,6), tex)
        return img
    if data == 3:
        tex = self.transform_image_side(raw_texture).transpose(Image.FLIP_LEFT_RIGHT)
        alpha_over(img, tex, (0,0), tex)
        return img
    if data == 4:
        tex = self.transform_image_side(raw_texture)
        alpha_over(img, tex, (12,0), tex)
        return img


# wall signs
@material(blockid=68, data=[2, 3, 4, 5], transparent=True)
def wall_sign(self, blockid, data): # wall sign

    # first rotations
    if self.rotation == 1:
        if data == 2: data = 5
        elif data == 3: data = 4
        elif data == 4: data = 2
        elif data == 5: data = 3
    elif self.rotation == 2:
        if data == 2: data = 3
        elif data == 3: data = 2
        elif data == 4: data = 5
        elif data == 5: data = 4
    elif self.rotation == 3:
        if data == 2: data = 4
        elif data == 3: data = 5
        elif data == 4: data = 3
        elif data == 5: data = 2

    texture = self.load_image_texture("assets/minecraft/textures/blocks/planks_oak.png").copy()
    # cut the planks to the size of a signpost
    ImageDraw.Draw(texture).rectangle((0,12,15,15),outline=(0,0,0,0),fill=(0,0,0,0))

    # draw some random black dots, they will look as text
    """ don't draw text at the moment, they are used in blank for decoration
    
    if data in (3,4):
        for i in range(15):
            x = randint(4,11)
            y = randint(3,7)
            texture.putpixel((x,y),(0,0,0,255))
    """
    
    img = Image.new("RGBA", (24,24), self.bgcolor)

    incrementx = 0
    if data == 2:  # east
        incrementx = +1
        sign = self.build_full_block(None, None, None, None, texture)
    elif data == 3:  # west
        incrementx = -1
        sign = self.build_full_block(None, texture, None, None, None)
    elif data == 4:  # north
        incrementx = +1
        sign = self.build_full_block(None, None, texture, None, None)
    elif data == 5:  # south
        incrementx = -1
        sign = self.build_full_block(None, None, None, texture, None)

    sign2 = ImageEnhance.Brightness(sign).enhance(1.2)
    alpha_over(img, sign2,(incrementx, 2),sign2)
    alpha_over(img, sign, (0,3), sign)

    return img

# levers
@material(blockid=69, data=range(16), transparent=True)
def levers(self, blockid, data):
    if data & 8 == 8: powered = True
    else: powered = False

    data = data & 7

    # first rotations
    if self.rotation == 1:
        # on wall levers
        if data == 1: data = 3
        elif data == 2: data = 4
        elif data == 3: data = 2
        elif data == 4: data = 1
        # on floor levers
        elif data == 5: data = 6
        elif data == 6: data = 5
    elif self.rotation == 2:
        if data == 1: data = 2
        elif data == 2: data = 1
        elif data == 3: data = 4
        elif data == 4: data = 3
        elif data == 5: data = 5
        elif data == 6: data = 6
    elif self.rotation == 3:
        if data == 1: data = 4
        elif data == 2: data = 3
        elif data == 3: data = 1
        elif data == 4: data = 2
        elif data == 5: data = 6
        elif data == 6: data = 5

    # generate the texture for the base of the lever
    t_base = self.load_image_texture("assets/minecraft/textures/blocks/stone.png").copy()

    ImageDraw.Draw(t_base).rectangle((0,0,15,3),outline=(0,0,0,0),fill=(0,0,0,0))
    ImageDraw.Draw(t_base).rectangle((0,12,15,15),outline=(0,0,0,0),fill=(0,0,0,0))
    ImageDraw.Draw(t_base).rectangle((0,0,4,15),outline=(0,0,0,0),fill=(0,0,0,0))
    ImageDraw.Draw(t_base).rectangle((11,0,15,15),outline=(0,0,0,0),fill=(0,0,0,0))

    # generate the texture for the stick
    stick = self.load_image_texture("assets/minecraft/textures/blocks/lever.png").copy()
    c_stick = Image.new("RGBA", (16,16), self.bgcolor)
    
    tmp = ImageEnhance.Brightness(stick).enhance(0.8)
    alpha_over(c_stick, tmp, (1,0), tmp)
    alpha_over(c_stick, stick, (0,0), stick)
    t_stick = self.transform_image_side(c_stick.rotate(45, Image.NEAREST))

    # where the lever will be composed
    img = Image.new("RGBA", (24,24), self.bgcolor)
    
    # wall levers
    if data == 1: # facing SOUTH
        # levers can't be placed in transparent blocks, so this
        # direction is almost invisible
        return None

    elif data == 2: # facing NORTH
        base = self.transform_image_side(t_base)
        
        # paste it twice with different brightness to make a fake 3D effect
        alpha_over(img, base, (12,-1), base)

        alpha = base.split()[3]
        base = ImageEnhance.Brightness(base).enhance(0.9)
        base.putalpha(alpha)
        
        alpha_over(img, base, (11,0), base)

        # paste the lever stick
        pos = (7,-7)
        if powered:
            t_stick = t_stick.transpose(Image.FLIP_TOP_BOTTOM)
            pos = (7,6)
        alpha_over(img, t_stick, pos, t_stick)

    elif data == 3: # facing WEST
        base = self.transform_image_side(t_base)
        
        # paste it twice with different brightness to make a fake 3D effect
        base = base.transpose(Image.FLIP_LEFT_RIGHT)
        alpha_over(img, base, (0,-1), base)

        alpha = base.split()[3]
        base = ImageEnhance.Brightness(base).enhance(0.9)
        base.putalpha(alpha)
        
        alpha_over(img, base, (1,0), base)
        
        # paste the lever stick
        t_stick = t_stick.transpose(Image.FLIP_LEFT_RIGHT)
        pos = (5,-7)
        if powered:
            t_stick = t_stick.transpose(Image.FLIP_TOP_BOTTOM)
            pos = (6,6)
        alpha_over(img, t_stick, pos, t_stick)

    elif data == 4: # facing EAST
        # levers can't be placed in transparent blocks, so this
        # direction is almost invisible
        return None

    # floor levers
    elif data == 5: # pointing south when off
        # lever base, fake 3d again
        base = self.transform_image_top(t_base)

        alpha = base.split()[3]
        tmp = ImageEnhance.Brightness(base).enhance(0.8)
        tmp.putalpha(alpha)
        
        alpha_over(img, tmp, (0,12), tmp)
        alpha_over(img, base, (0,11), base)

        # lever stick
        pos = (3,2)
        if not powered:
            t_stick = t_stick.transpose(Image.FLIP_LEFT_RIGHT)
            pos = (11,2)
        alpha_over(img, t_stick, pos, t_stick)

    elif data == 6: # pointing east when off
        # lever base, fake 3d again
        base = self.transform_image_top(t_base.rotate(90))

        alpha = base.split()[3]
        tmp = ImageEnhance.Brightness(base).enhance(0.8)
        tmp.putalpha(alpha)
        
        alpha_over(img, tmp, (0,12), tmp)
        alpha_over(img, base, (0,11), base)

        # lever stick
        pos = (2,3)
        if not powered:
            t_stick = t_stick.transpose(Image.FLIP_LEFT_RIGHT)
            pos = (10,2)
        alpha_over(img, t_stick, pos, t_stick)

    return img

# wooden and stone pressure plates, and weighted pressure plates
@material(blockid=[70, 72,147,148], data=[0,1], transparent=True)
def pressure_plate(self, blockid, data):
    if blockid == 70: # stone
        t = self.load_image_texture("assets/minecraft/textures/blocks/stone.png").copy()
    elif blockid == 72: # wooden
        t = self.load_image_texture("assets/minecraft/textures/blocks/planks_oak.png").copy()
    elif blockid == 147: # light golden
        t = self.load_image_texture("assets/minecraft/textures/blocks/gold_block.png").copy()
    else: # blockid == 148: # heavy iron
        t = self.load_image_texture("assets/minecraft/textures/blocks/iron_block.png").copy()
    
    # cut out the outside border, pressure plates are smaller
    # than a normal block
    ImageDraw.Draw(t).rectangle((0,0,15,15),outline=(0,0,0,0))
    
    # create the textures and a darker version to make a 3d by 
    # pasting them with an offstet of 1 pixel
    img = Image.new("RGBA", (24,24), self.bgcolor)
    
    top = self.transform_image_top(t)
    
    alpha = top.split()[3]
    topd = ImageEnhance.Brightness(top).enhance(0.8)
    topd.putalpha(alpha)
    
    #show it 3d or 2d if unpressed or pressed
    if data == 0:
        alpha_over(img,topd, (0,12),topd)
        alpha_over(img,top, (0,11),top)
    elif data == 1:
        alpha_over(img,top, (0,12),top)
    
    return img

# normal and glowing redstone ore
block(blockid=[73, 74], top_image="assets/minecraft/textures/blocks/redstone_ore.png")

# stone a wood buttons
@material(blockid=(77,143), data=range(16), transparent=True)
def buttons(self, blockid, data):

    # 0x8 is set if the button is pressed mask this info and render
    # it as unpressed
    data = data & 0x7

    if self.rotation == 1:
        if data == 1: data = 3
        elif data == 2: data = 4
        elif data == 3: data = 2
        elif data == 4: data = 1
    elif self.rotation == 2:
        if data == 1: data = 2
        elif data == 2: data = 1
        elif data == 3: data = 4
        elif data == 4: data = 3
    elif self.rotation == 3:
        if data == 1: data = 4
        elif data == 2: data = 3
        elif data == 3: data = 1
        elif data == 4: data = 2

    if blockid == 77:
        t = self.load_image_texture("assets/minecraft/textures/blocks/stone.png").copy()
    else:
        t = self.load_image_texture("assets/minecraft/textures/blocks/planks_oak.png").copy()

    # generate the texture for the button
    ImageDraw.Draw(t).rectangle((0,0,15,5),outline=(0,0,0,0),fill=(0,0,0,0))
    ImageDraw.Draw(t).rectangle((0,10,15,15),outline=(0,0,0,0),fill=(0,0,0,0))
    ImageDraw.Draw(t).rectangle((0,0,4,15),outline=(0,0,0,0),fill=(0,0,0,0))
    ImageDraw.Draw(t).rectangle((11,0,15,15),outline=(0,0,0,0),fill=(0,0,0,0))

    img = Image.new("RGBA", (24,24), self.bgcolor)

    button = self.transform_image_side(t)
    
    if data == 1: # facing SOUTH
        # buttons can't be placed in transparent blocks, so this
        # direction can't be seen
        return None

    elif data == 2: # facing NORTH
        # paste it twice with different brightness to make a 3D effect
        alpha_over(img, button, (12,-1), button)

        alpha = button.split()[3]
        button = ImageEnhance.Brightness(button).enhance(0.9)
        button.putalpha(alpha)
        
        alpha_over(img, button, (11,0), button)

    elif data == 3: # facing WEST
        # paste it twice with different brightness to make a 3D effect
        button = button.transpose(Image.FLIP_LEFT_RIGHT)
        alpha_over(img, button, (0,-1), button)

        alpha = button.split()[3]
        button = ImageEnhance.Brightness(button).enhance(0.9)
        button.putalpha(alpha)
        
        alpha_over(img, button, (1,0), button)

    elif data == 4: # facing EAST
        # buttons can't be placed in transparent blocks, so this
        # direction can't be seen
        return None

    return img

# snow
@material(blockid=78, data=range(16), transparent=True, solid=True)
def snow(self, blockid, data):
    # still not rendered correctly: data other than 0
    
    tex = self.load_image_texture("assets/minecraft/textures/blocks/snow.png")
    
    # make the side image, top 3/4 transparent
    mask = tex.crop((0,12,16,16))
    sidetex = Image.new(tex.mode, tex.size, self.bgcolor)
    alpha_over(sidetex, mask, (0,12,16,16), mask)
    
    img = Image.new("RGBA", (24,24), self.bgcolor)
    
    top = self.transform_image_top(tex)
    side = self.transform_image_side(sidetex)
    otherside = side.transpose(Image.FLIP_LEFT_RIGHT)
    
    alpha_over(img, side, (0,6), side)
    alpha_over(img, otherside, (12,6), otherside)
    alpha_over(img, top, (0,9), top)
    
    return img

# snow block
block(blockid=80, top_image="assets/minecraft/textures/blocks/snow.png")

# cactus
@material(blockid=81, data=range(15), transparent=True, solid=True, nospawn=True)
def cactus(self, blockid, data):
    top = self.load_image_texture("assets/minecraft/textures/blocks/cactus_top.png")
    side = self.load_image_texture("assets/minecraft/textures/blocks/cactus_side.png")

    img = Image.new("RGBA", (24,24), self.bgcolor)
    
    top = self.transform_image_top(top)
    side = self.transform_image_side(side)
    otherside = side.transpose(Image.FLIP_LEFT_RIGHT)

    sidealpha = side.split()[3]
    side = ImageEnhance.Brightness(side).enhance(0.9)
    side.putalpha(sidealpha)
    othersidealpha = otherside.split()[3]
    otherside = ImageEnhance.Brightness(otherside).enhance(0.8)
    otherside.putalpha(othersidealpha)

    alpha_over(img, side, (1,6), side)
    alpha_over(img, otherside, (11,6), otherside)
    alpha_over(img, top, (0,0), top)
    
    return img

# clay block
block(blockid=82, top_image="assets/minecraft/textures/blocks/clay.png")

# sugar cane
@material(blockid=83, data=range(16), transparent=True)
def sugar_cane(self, blockid, data):
    tex = self.load_image_texture("assets/minecraft/textures/blocks/reeds.png")
    return self.build_sprite(tex)

# jukebox
@material(blockid=84, data=range(16), solid=True)
def jukebox(self, blockid, data):
    return self.build_block(self.load_image_texture("assets/minecraft/textures/blocks/jukebox_top.png"), self.load_image_texture("assets/minecraft/textures/blocks/noteblock.png"))

# nether and normal fences
# uses pseudo-ancildata found in iterate.c
@material(blockid=[85, 113], data=range(16), transparent=True, nospawn=True)
def fence(self, blockid, data):
    # no need for rotations, it uses pseudo data.
    # create needed images for Big stick fence
    if blockid == 85: # normal fence
        fence_top = self.load_image_texture("assets/minecraft/textures/blocks/planks_oak.png").copy()
        fence_side = self.load_image_texture("assets/minecraft/textures/blocks/planks_oak.png").copy()
        fence_small_side = self.load_image_texture("assets/minecraft/textures/blocks/planks_oak.png").copy()
    else: # netherbrick fence
        fence_top = self.load_image_texture("assets/minecraft/textures/blocks/nether_brick.png").copy()
        fence_side = self.load_image_texture("assets/minecraft/textures/blocks/nether_brick.png").copy()
        fence_small_side = self.load_image_texture("assets/minecraft/textures/blocks/nether_brick.png").copy()

    # generate the textures of the fence
    ImageDraw.Draw(fence_top).rectangle((0,0,5,15),outline=(0,0,0,0),fill=(0,0,0,0))
    ImageDraw.Draw(fence_top).rectangle((10,0,15,15),outline=(0,0,0,0),fill=(0,0,0,0))
    ImageDraw.Draw(fence_top).rectangle((0,0,15,5),outline=(0,0,0,0),fill=(0,0,0,0))
    ImageDraw.Draw(fence_top).rectangle((0,10,15,15),outline=(0,0,0,0),fill=(0,0,0,0))

    ImageDraw.Draw(fence_side).rectangle((0,0,5,15),outline=(0,0,0,0),fill=(0,0,0,0))
    ImageDraw.Draw(fence_side).rectangle((10,0,15,15),outline=(0,0,0,0),fill=(0,0,0,0))

    # Create the sides and the top of the big stick
    fence_side = self.transform_image_side(fence_side)
    fence_other_side = fence_side.transpose(Image.FLIP_LEFT_RIGHT)
    fence_top = self.transform_image_top(fence_top)

    # Darken the sides slightly. These methods also affect the alpha layer,
    # so save them first (we don't want to "darken" the alpha layer making
    # the block transparent)
    sidealpha = fence_side.split()[3]
    fence_side = ImageEnhance.Brightness(fence_side).enhance(0.9)
    fence_side.putalpha(sidealpha)
    othersidealpha = fence_other_side.split()[3]
    fence_other_side = ImageEnhance.Brightness(fence_other_side).enhance(0.8)
    fence_other_side.putalpha(othersidealpha)

    # Compose the fence big stick
    fence_big = Image.new("RGBA", (24,24), self.bgcolor)
    alpha_over(fence_big,fence_side, (5,4),fence_side)
    alpha_over(fence_big,fence_other_side, (7,4),fence_other_side)
    alpha_over(fence_big,fence_top, (0,0),fence_top)
    
    # Now render the small sticks.
    # Create needed images
    ImageDraw.Draw(fence_small_side).rectangle((0,0,15,0),outline=(0,0,0,0),fill=(0,0,0,0))
    ImageDraw.Draw(fence_small_side).rectangle((0,4,15,6),outline=(0,0,0,0),fill=(0,0,0,0))
    ImageDraw.Draw(fence_small_side).rectangle((0,10,15,16),outline=(0,0,0,0),fill=(0,0,0,0))
    ImageDraw.Draw(fence_small_side).rectangle((0,0,4,15),outline=(0,0,0,0),fill=(0,0,0,0))
    ImageDraw.Draw(fence_small_side).rectangle((11,0,15,15),outline=(0,0,0,0),fill=(0,0,0,0))

    # Create the sides and the top of the small sticks
    fence_small_side = self.transform_image_side(fence_small_side)
    fence_small_other_side = fence_small_side.transpose(Image.FLIP_LEFT_RIGHT)
    
    # Darken the sides slightly. These methods also affect the alpha layer,
    # so save them first (we don't want to "darken" the alpha layer making
    # the block transparent)
    sidealpha = fence_small_other_side.split()[3]
    fence_small_other_side = ImageEnhance.Brightness(fence_small_other_side).enhance(0.9)
    fence_small_other_side.putalpha(sidealpha)
    sidealpha = fence_small_side.split()[3]
    fence_small_side = ImageEnhance.Brightness(fence_small_side).enhance(0.9)
    fence_small_side.putalpha(sidealpha)

    # Create img to compose the fence
    img = Image.new("RGBA", (24,24), self.bgcolor)

    # Position of fence small sticks in img.
    # These postitions are strange because the small sticks of the 
    # fence are at the very left and at the very right of the 16x16 images
    pos_top_left = (2,3)
    pos_top_right = (10,3)
    pos_bottom_right = (10,7)
    pos_bottom_left = (2,7)
    
    # +x axis points top right direction
    # +y axis points bottom right direction
    # First compose small sticks in the back of the image, 
    # then big stick and thecn small sticks in the front.

    if (data & 0b0001) == 1:
        alpha_over(img,fence_small_side, pos_top_left,fence_small_side)                # top left
    if (data & 0b1000) == 8:
        alpha_over(img,fence_small_other_side, pos_top_right,fence_small_other_side)    # top right
        
    alpha_over(img,fence_big,(0,0),fence_big)
        
    if (data & 0b0010) == 2:
        alpha_over(img,fence_small_other_side, pos_bottom_left,fence_small_other_side)      # bottom left    
    if (data & 0b0100) == 4:
        alpha_over(img,fence_small_side, pos_bottom_right,fence_small_side)                  # bottom right
    
    return img

# pumpkin
@material(blockid=[86, 91], data=range(4), solid=True)
def pumpkin(self, blockid, data): # pumpkins, jack-o-lantern
    # rotation
    if self.rotation == 1:
        if data == 0: data = 1
        elif data == 1: data = 2
        elif data == 2: data = 3
        elif data == 3: data = 0
    elif self.rotation == 2:
        if data == 0: data = 2
        elif data == 1: data = 3
        elif data == 2: data = 0
        elif data == 3: data = 1
    elif self.rotation == 3:
        if data == 0: data = 3
        elif data == 1: data = 0
        elif data == 2: data = 1
        elif data == 3: data = 2
    
    # texture generation
    top = self.load_image_texture("assets/minecraft/textures/blocks/pumpkin_top.png")
    frontName = "assets/minecraft/textures/blocks/pumpkin_face_off.png" if blockid == 86 else "assets/minecraft/textures/blocks/pumpkin_face_on.png"
    front = self.load_image_texture(frontName)
    side = self.load_image_texture("assets/minecraft/textures/blocks/pumpkin_side.png")

    if data == 0: # pointing west
        img = self.build_full_block(top, None, None, side, front)

    elif data == 1: # pointing north
        img = self.build_full_block(top, None, None, front, side)

    else: # in any other direction the front can't be seen
        img = self.build_full_block(top, None, None, side, side)

    return img

# netherrack
block(blockid=87, top_image="assets/minecraft/textures/blocks/netherrack.png")

# soul sand
block(blockid=88, top_image="assets/minecraft/textures/blocks/soul_sand.png")

# glowstone
block(blockid=89, top_image="assets/minecraft/textures/blocks/glowstone.png")

# portal
@material(blockid=90, data=[1, 2, 4, 5, 8, 10], transparent=True)
def portal(self, blockid, data):
    # no rotations, uses pseudo data
    portaltexture = self.load_portal()
    img = Image.new("RGBA", (24,24), self.bgcolor)

    side = self.transform_image_side(portaltexture)
    otherside = side.transpose(Image.FLIP_TOP_BOTTOM)

    if data in (1,4,5):
        alpha_over(img, side, (5,4), side)

    if data in (2,8,10):
        alpha_over(img, otherside, (5,4), otherside)

    return img

# cake!
@material(blockid=92, data=range(6), transparent=True, nospawn=True)
def cake(self, blockid, data):
    
    # cake textures
    top = self.load_image_texture("assets/minecraft/textures/blocks/cake_top.png").copy()
    side = self.load_image_texture("assets/minecraft/textures/blocks/cake_side.png").copy()
    fullside = side.copy()
    inside = self.load_image_texture("assets/minecraft/textures/blocks/cake_inner.png")
    
    img = Image.new("RGBA", (24,24), self.bgcolor)
    if data == 0: # unbitten cake
        top = self.transform_image_top(top)
        side = self.transform_image_side(side)
        otherside = side.transpose(Image.FLIP_LEFT_RIGHT)
        
        # darken sides slightly
        sidealpha = side.split()[3]
        side = ImageEnhance.Brightness(side).enhance(0.9)
        side.putalpha(sidealpha)
        othersidealpha = otherside.split()[3]
        otherside = ImageEnhance.Brightness(otherside).enhance(0.8)
        otherside.putalpha(othersidealpha)
        
        # composite the cake
        alpha_over(img, side, (1,6), side)
        alpha_over(img, otherside, (11,7), otherside) # workaround, fixes a hole
        alpha_over(img, otherside, (12,6), otherside)
        alpha_over(img, top, (0,6), top)
    
    else:
        # cut the textures for a bitten cake
        coord = int(16./6.*data)
        ImageDraw.Draw(side).rectangle((16 - coord,0,16,16),outline=(0,0,0,0),fill=(0,0,0,0))
        ImageDraw.Draw(top).rectangle((0,0,coord,16),outline=(0,0,0,0),fill=(0,0,0,0))

        # the bitten part of the cake always points to the west
        # composite the cake for every north orientation
        if self.rotation == 0: # north top-left
            # create right side
            rs = self.transform_image_side(side).transpose(Image.FLIP_LEFT_RIGHT)
            # create bitten side and its coords
            deltax = 2*data
            deltay = -1*data
            if data == 3: deltax += 1 # special case fixing pixel holes
            ls = self.transform_image_side(inside)
            # create top side
            t = self.transform_image_top(top)
            # darken sides slightly
            sidealpha = ls.split()[3]
            ls = ImageEnhance.Brightness(ls).enhance(0.9)
            ls.putalpha(sidealpha)
            othersidealpha = rs.split()[3]
            rs = ImageEnhance.Brightness(rs).enhance(0.8)
            rs.putalpha(othersidealpha)
            # compose the cake
            alpha_over(img, rs, (12,6), rs)
            alpha_over(img, ls, (1 + deltax,6 + deltay), ls)
            alpha_over(img, t, (0,6), t)

        elif self.rotation == 1: # north top-right
            # bitten side not shown
            # create left side
            ls = self.transform_image_side(side.transpose(Image.FLIP_LEFT_RIGHT))
            # create top
            t = self.transform_image_top(top.rotate(-90))
            # create right side
            rs = self.transform_image_side(fullside).transpose(Image.FLIP_LEFT_RIGHT)
            # darken sides slightly
            sidealpha = ls.split()[3]
            ls = ImageEnhance.Brightness(ls).enhance(0.9)
            ls.putalpha(sidealpha)
            othersidealpha = rs.split()[3]
            rs = ImageEnhance.Brightness(rs).enhance(0.8)
            rs.putalpha(othersidealpha)
            # compose the cake
            alpha_over(img, ls, (2,6), ls)
            alpha_over(img, t, (0,6), t)
            alpha_over(img, rs, (12,6), rs)

        elif self.rotation == 2: # north bottom-right
            # bitten side not shown
            # left side
            ls = self.transform_image_side(fullside)
            # top
            t = self.transform_image_top(top.rotate(180))
            # right side
            rs = self.transform_image_side(side.transpose(Image.FLIP_LEFT_RIGHT)).transpose(Image.FLIP_LEFT_RIGHT)
            # darken sides slightly
            sidealpha = ls.split()[3]
            ls = ImageEnhance.Brightness(ls).enhance(0.9)
            ls.putalpha(sidealpha)
            othersidealpha = rs.split()[3]
            rs = ImageEnhance.Brightness(rs).enhance(0.8)
            rs.putalpha(othersidealpha)
            # compose the cake
            alpha_over(img, ls, (2,6), ls)
            alpha_over(img, t, (1,6), t)
            alpha_over(img, rs, (12,6), rs)

        elif self.rotation == 3: # north bottom-left
            # create left side
            ls = self.transform_image_side(side)
            # create top
            t = self.transform_image_top(top.rotate(90))
            # create right side and its coords
            deltax = 12-2*data
            deltay = -1*data
            if data == 3: deltax += -1 # special case fixing pixel holes
            rs = self.transform_image_side(inside).transpose(Image.FLIP_LEFT_RIGHT)
            # darken sides slightly
            sidealpha = ls.split()[3]
            ls = ImageEnhance.Brightness(ls).enhance(0.9)
            ls.putalpha(sidealpha)
            othersidealpha = rs.split()[3]
            rs = ImageEnhance.Brightness(rs).enhance(0.8)
            rs.putalpha(othersidealpha)
            # compose the cake
            alpha_over(img, ls, (2,6), ls)
            alpha_over(img, t, (1,6), t)
            alpha_over(img, rs, (1 + deltax,6 + deltay), rs)

    return img

# redstone repeaters ON and OFF
@material(blockid=[93,94], data=range(16), transparent=True, nospawn=True)
def repeater(self, blockid, data):
    # rotation
    # Masked to not clobber delay info
    if self.rotation == 1:
        if (data & 0b0011) == 0: data = data & 0b1100 | 1
        elif (data & 0b0011) == 1: data = data & 0b1100 | 2
        elif (data & 0b0011) == 2: data = data & 0b1100 | 3
        elif (data & 0b0011) == 3: data = data & 0b1100 | 0
    elif self.rotation == 2:
        if (data & 0b0011) == 0: data = data & 0b1100 | 2
        elif (data & 0b0011) == 1: data = data & 0b1100 | 3
        elif (data & 0b0011) == 2: data = data & 0b1100 | 0
        elif (data & 0b0011) == 3: data = data & 0b1100 | 1
    elif self.rotation == 3:
        if (data & 0b0011) == 0: data = data & 0b1100 | 3
        elif (data & 0b0011) == 1: data = data & 0b1100 | 0
        elif (data & 0b0011) == 2: data = data & 0b1100 | 1
        elif (data & 0b0011) == 3: data = data & 0b1100 | 2
    
    # generate the diode
    top = self.load_image_texture("assets/minecraft/textures/blocks/repeater_off.png") if blockid == 93 else self.load_image_texture("assets/minecraft/textures/blocks/repeater_on.png")
    side = self.load_image_texture("assets/minecraft/textures/blocks/stone_slab_side.png")
    increment = 13
    
    if (data & 0x3) == 0: # pointing east
        pass
    
    if (data & 0x3) == 1: # pointing south
        top = top.rotate(270)

    if (data & 0x3) == 2: # pointing west
        top = top.rotate(180)

    if (data & 0x3) == 3: # pointing north
        top = top.rotate(90)

    img = self.build_full_block( (top, increment), None, None, side, side)

    # compose a "3d" redstone torch
    t = self.load_image_texture("assets/minecraft/textures/blocks/redstone_torch_off.png").copy() if blockid == 93 else self.load_image_texture("assets/minecraft/textures/blocks/redstone_torch_on.png").copy()
    torch = Image.new("RGBA", (24,24), self.bgcolor)
    
    t_crop = t.crop((2,2,14,14))
    slice = t_crop.copy()
    ImageDraw.Draw(slice).rectangle((6,0,12,12),outline=(0,0,0,0),fill=(0,0,0,0))
    ImageDraw.Draw(slice).rectangle((0,0,4,12),outline=(0,0,0,0),fill=(0,0,0,0))
    
    alpha_over(torch, slice, (6,4))
    alpha_over(torch, t_crop, (5,5))
    alpha_over(torch, t_crop, (6,5))
    alpha_over(torch, slice, (6,6))
    
    # paste redstone torches everywhere!
    # the torch is too tall for the repeater, crop the bottom.
    ImageDraw.Draw(torch).rectangle((0,16,24,24),outline=(0,0,0,0),fill=(0,0,0,0))
    
    # touch up the 3d effect with big rectangles, just in case, for other texture packs
    ImageDraw.Draw(torch).rectangle((0,24,10,15),outline=(0,0,0,0),fill=(0,0,0,0))
    ImageDraw.Draw(torch).rectangle((12,15,24,24),outline=(0,0,0,0),fill=(0,0,0,0))
    
    # torch positions for every redstone torch orientation.
    #
    # This is a horrible list of torch orientations. I tried to 
    # obtain these orientations by rotating the positions for one
    # orientation, but pixel rounding is horrible and messes the
    # torches.

    if (data & 0x3) == 0: # pointing east
        if (data & 0xC) == 0: # one tick delay
            moving_torch = (1,1)
            static_torch = (-3,-1)
            
        elif (data & 0xC) == 4: # two ticks delay
            moving_torch = (2,2)
            static_torch = (-3,-1)
            
        elif (data & 0xC) == 8: # three ticks delay
            moving_torch = (3,2)
            static_torch = (-3,-1)
            
        elif (data & 0xC) == 12: # four ticks delay
            moving_torch = (4,3)
            static_torch = (-3,-1)
    
    elif (data & 0x3) == 1: # pointing south
        if (data & 0xC) == 0: # one tick delay
            moving_torch = (1,1)
            static_torch = (5,-1)
            
        elif (data & 0xC) == 4: # two ticks delay
            moving_torch = (0,2)
            static_torch = (5,-1)
            
        elif (data & 0xC) == 8: # three ticks delay
            moving_torch = (-1,2)
            static_torch = (5,-1)
            
        elif (data & 0xC) == 12: # four ticks delay
            moving_torch = (-2,3)
            static_torch = (5,-1)

    elif (data & 0x3) == 2: # pointing west
        if (data & 0xC) == 0: # one tick delay
            moving_torch = (1,1)
            static_torch = (5,3)
            
        elif (data & 0xC) == 4: # two ticks delay
            moving_torch = (0,0)
            static_torch = (5,3)
            
        elif (data & 0xC) == 8: # three ticks delay
            moving_torch = (-1,0)
            static_torch = (5,3)
            
        elif (data & 0xC) == 12: # four ticks delay
            moving_torch = (-2,-1)
            static_torch = (5,3)

    elif (data & 0x3) == 3: # pointing north
        if (data & 0xC) == 0: # one tick delay
            moving_torch = (1,1)
            static_torch = (-3,3)
            
        elif (data & 0xC) == 4: # two ticks delay
            moving_torch = (2,0)
            static_torch = (-3,3)
            
        elif (data & 0xC) == 8: # three ticks delay
            moving_torch = (3,0)
            static_torch = (-3,3)
            
        elif (data & 0xC) == 12: # four ticks delay
            moving_torch = (4,-1)
            static_torch = (-3,3)
    
    # this paste order it's ok for east and south orientation
    # but it's wrong for north and west orientations. But using the
    # default texture pack the torches are small enough to no overlap.
    alpha_over(img, torch, static_torch, torch) 
    alpha_over(img, torch, moving_torch, torch)

    return img

# redstone comparator (149 is inactive, 150 is active)
@material(blockid=[149,150], data=range(16), transparent=True, nospawn=True)
def comparator(self, blockid, data):

    # rotation
    # add self.rotation to the lower 2 bits,  mod 4
    data = data & 0b1100 | (((data & 0b11) + self.rotation) % 4)


    top = self.load_image_texture("assets/minecraft/textures/blocks/comparator_off.png") if blockid == 149 else self.load_image_texture("assets/minecraft/textures/blocks/comparator_on.png")
    side = self.load_image_texture("assets/minecraft/textures/blocks/stone_slab_side.png")
    increment = 13

    if (data & 0x3) == 0: # pointing north
        pass
        static_torch = (-3,-1)
        torch = ((0,2),(6,-1))
    
    if (data & 0x3) == 1: # pointing east
        top = top.rotate(270)
        static_torch = (5,-1)
        torch = ((-4,-1),(0,2))

    if (data & 0x3) == 2: # pointing south
        top = top.rotate(180)
        static_torch = (5,3)
        torch = ((0,-4),(-4,-1))

    if (data & 0x3) == 3: # pointing west
        top = top.rotate(90)
        static_torch = (-3,3)
        torch = ((1,-4),(6,-1))


    def build_torch(active):
        # compose a "3d" redstone torch
        t = self.load_image_texture("assets/minecraft/textures/blocks/redstone_torch_off.png").copy() if not active else self.load_image_texture("assets/minecraft/textures/blocks/redstone_torch_on.png").copy()
        torch = Image.new("RGBA", (24,24), self.bgcolor)
        
        t_crop = t.crop((2,2,14,14))
        slice = t_crop.copy()
        ImageDraw.Draw(slice).rectangle((6,0,12,12),outline=(0,0,0,0),fill=(0,0,0,0))
        ImageDraw.Draw(slice).rectangle((0,0,4,12),outline=(0,0,0,0),fill=(0,0,0,0))
        
        alpha_over(torch, slice, (6,4))
        alpha_over(torch, t_crop, (5,5))
        alpha_over(torch, t_crop, (6,5))
        alpha_over(torch, slice, (6,6))

        return torch
    
    active_torch = build_torch(True)
    inactive_torch = build_torch(False)
    back_torch = active_torch if (blockid == 150 or data & 0b1000 == 0b1000) else inactive_torch
    static_torch_img = active_torch if (data & 0b100 == 0b100) else inactive_torch 

    img = self.build_full_block( (top, increment), None, None, side, side)

    alpha_over(img, static_torch_img, static_torch, static_torch_img) 
    alpha_over(img, back_torch, torch[0], back_torch) 
    alpha_over(img, back_torch, torch[1], back_torch) 
    return img
    
    
# trapdoor
# the trapdoor is looks like a sprite when opened, that's not good
@material(blockid=96, data=range(16), transparent=True, nospawn=True)
def trapdoor(self, blockid, data):

    # rotation
    # Masked to not clobber opened/closed info
    if self.rotation == 1:
        if (data & 0b0011) == 0: data = data & 0b1100 | 3
        elif (data & 0b0011) == 1: data = data & 0b1100 | 2
        elif (data & 0b0011) == 2: data = data & 0b1100 | 0
        elif (data & 0b0011) == 3: data = data & 0b1100 | 1
    elif self.rotation == 2:
        if (data & 0b0011) == 0: data = data & 0b1100 | 1
        elif (data & 0b0011) == 1: data = data & 0b1100 | 0
        elif (data & 0b0011) == 2: data = data & 0b1100 | 3
        elif (data & 0b0011) == 3: data = data & 0b1100 | 2
    elif self.rotation == 3:
        if (data & 0b0011) == 0: data = data & 0b1100 | 2
        elif (data & 0b0011) == 1: data = data & 0b1100 | 3
        elif (data & 0b0011) == 2: data = data & 0b1100 | 1
        elif (data & 0b0011) == 3: data = data & 0b1100 | 0

    # texture generation
    texture = self.load_image_texture("assets/minecraft/textures/blocks/trapdoor.png")
    if data & 0x4 == 0x4: # opened trapdoor
        if data & 0x3 == 0: # west
            img = self.build_full_block(None, None, None, None, texture)
        if data & 0x3 == 1: # east
            img = self.build_full_block(None, texture, None, None, None)
        if data & 0x3 == 2: # south
            img = self.build_full_block(None, None, texture, None, None)
        if data & 0x3 == 3: # north
            img = self.build_full_block(None, None, None, texture, None)
        
    elif data & 0x4 == 0: # closed trapdoor
        if data & 0x8 == 0x8: # is a top trapdoor
            img = Image.new("RGBA", (24,24), self.bgcolor)
            t = self.build_full_block((texture, 12), None, None, texture, texture)
            alpha_over(img, t, (0,-9),t)
        else: # is a bottom trapdoor
            img = self.build_full_block((texture, 12), None, None, texture, texture)
    
    return img

# block with hidden silverfish (stone, cobblestone and stone brick)
@material(blockid=97, data=range(3), solid=True)
def hidden_silverfish(self, blockid, data):
    if data == 0: # stone
        t = self.load_image_texture("assets/minecraft/textures/blocks/stone.png")
    elif data == 1: # cobblestone
        t = self.load_image_texture("assets/minecraft/textures/blocks/cobblestone.png")
    elif data == 2: # stone brick
        t = self.load_image_texture("assets/minecraft/textures/blocks/stonebrick.png")
    
    img = self.build_block(t, t)
    
    return img

# stone brick
@material(blockid=98, data=range(4), solid=True)
def stone_brick(self, blockid, data):
    if data == 0: # normal
        t = self.load_image_texture("assets/minecraft/textures/blocks/stonebrick.png")
    elif data == 1: # mossy
        t = self.load_image_texture("assets/minecraft/textures/blocks/stonebrick_mossy.png")
    elif data == 2: # cracked
        t = self.load_image_texture("assets/minecraft/textures/blocks/stonebrick_cracked.png")
    elif data == 3: # "circle" stone brick
        t = self.load_image_texture("assets/minecraft/textures/blocks/stonebrick_carved.png")

    img = self.build_full_block(t, None, None, t, t)

    return img

# huge brown and red mushroom
@material(blockid=[99,100], data= range(11) + [14,15], solid=True)
def huge_mushroom(self, blockid, data):
    # rotation
    if self.rotation == 1:
        if data == 1: data = 3
        elif data == 2: data = 6
        elif data == 3: data = 9
        elif data == 4: data = 2
        elif data == 6: data = 8
        elif data == 7: data = 1
        elif data == 8: data = 4
        elif data == 9: data = 7
    elif self.rotation == 2:
        if data == 1: data = 9
        elif data == 2: data = 8
        elif data == 3: data = 7
        elif data == 4: data = 6
        elif data == 6: data = 4
        elif data == 7: data = 3
        elif data == 8: data = 2
        elif data == 9: data = 1
    elif self.rotation == 3:
        if data == 1: data = 7
        elif data == 2: data = 4
        elif data == 3: data = 1
        elif data == 4: data = 2
        elif data == 6: data = 8
        elif data == 7: data = 9
        elif data == 8: data = 6
        elif data == 9: data = 3

    # texture generation
    if blockid == 99: # brown
        cap = self.load_image_texture("assets/minecraft/textures/blocks/mushroom_block_skin_brown.png")
    else: # red
        cap = self.load_image_texture("assets/minecraft/textures/blocks/mushroom_block_skin_red.png")

    stem = self.load_image_texture("assets/minecraft/textures/blocks/mushroom_block_skin_stem.png")
    porous = self.load_image_texture("assets/minecraft/textures/blocks/mushroom_block_inside.png")
    
    if data == 0: # fleshy piece
        img = self.build_full_block(porous, None, None, porous, porous)

    if data == 1: # north-east corner
        img = self.build_full_block(cap, None, None, cap, porous)

    if data == 2: # east side
        img = self.build_full_block(cap, None, None, porous, porous)

    if data == 3: # south-east corner
        img = self.build_full_block(cap, None, None, porous, cap)

    if data == 4: # north side
        img = self.build_full_block(cap, None, None, cap, porous)

    if data == 5: # top piece
        img = self.build_full_block(cap, None, None, porous, porous)

    if data == 6: # south side
        img = self.build_full_block(cap, None, None, cap, porous)

    if data == 7: # north-west corner
        img = self.build_full_block(cap, None, None, cap, cap)

    if data == 8: # west side
        img = self.build_full_block(cap, None, None, porous, cap)

    if data == 9: # south-west corner
        img = self.build_full_block(cap, None, None, porous, cap)

    if data == 10: # stem
        img = self.build_full_block(porous, None, None, stem, stem)

    if data == 14: # all cap
        img = self.build_block(cap,cap)

    if data == 15: # all stem
        img = self.build_block(stem,stem)

    return img

# iron bars and glass pane
# TODO glass pane is not a sprite, it has a texture for the side,
# at the moment is not used
@material(blockid=[101,102, 160], data=range(256), transparent=True, nospawn=True)
def panes(self, blockid, data):
    # no rotation, uses pseudo data
    if blockid == 101:
        # iron bars
        t = self.load_image_texture("assets/minecraft/textures/blocks/iron_bars.png")
    elif blockid == 160:
        t = self.load_image_texture("assets/minecraft/textures/blocks/glass_%s.png" % color_map[data & 0xf])
    else:
        # glass panes
        t = self.load_image_texture("assets/minecraft/textures/blocks/glass.png")
    left = t.copy()
    right = t.copy()

    # generate the four small pieces of the glass pane
    ImageDraw.Draw(right).rectangle((0,0,7,15),outline=(0,0,0,0),fill=(0,0,0,0))
    ImageDraw.Draw(left).rectangle((8,0,15,15),outline=(0,0,0,0),fill=(0,0,0,0))
    
    up_left = self.transform_image_side(left)
    up_right = self.transform_image_side(right).transpose(Image.FLIP_TOP_BOTTOM)
    dw_right = self.transform_image_side(right)
    dw_left = self.transform_image_side(left).transpose(Image.FLIP_TOP_BOTTOM)

    # Create img to compose the texture
    img = Image.new("RGBA", (24,24), self.bgcolor)

    # +x axis points top right direction
    # +y axis points bottom right direction
    # First compose things in the back of the image, 
    # then things in the front.

    # the lower 4 bits encode color, the upper 4 encode adjencies
    data = data >> 4

    if (data & 0b0001) == 1 or data == 0:
        alpha_over(img,up_left, (6,3),up_left)    # top left
    if (data & 0b1000) == 8 or data == 0:
        alpha_over(img,up_right, (6,3),up_right)  # top right
    if (data & 0b0010) == 2 or data == 0:
        alpha_over(img,dw_left, (6,3),dw_left)    # bottom left    
    if (data & 0b0100) == 4 or data == 0:
        alpha_over(img,dw_right, (6,3),dw_right)  # bottom right

    return img

# melon
block(blockid=103, top_image="assets/minecraft/textures/blocks/melon_top.png", side_image="assets/minecraft/textures/blocks/melon_side.png", solid=True)

# pumpkin and melon stem
# TODO To render it as in game needs from pseudo data and ancil data:
# once fully grown the stem bends to the melon/pumpkin block,
# at the moment only render the growing stem
@material(blockid=[104,105], data=range(8), transparent=True)
def stem(self, blockid, data):
    # the ancildata value indicates how much of the texture
    # is shown.

    # not fully grown stem or no pumpkin/melon touching it,
    # straight up stem
    t = self.load_image_texture("assets/minecraft/textures/blocks/melon_stem_disconnected.png").copy()
    img = Image.new("RGBA", (16,16), self.bgcolor)
    alpha_over(img, t, (0, int(16 - 16*((data + 1)/8.))), t)
    img = self.build_sprite(t)
    if data & 7 == 7:
        # fully grown stem gets brown color!
        # there is a conditional in rendermode-normal.c to not
        # tint the data value 7
        img = self.tint_texture(img, (211,169,116))
    return img
    

# vines
@material(blockid=106, data=range(16), transparent=True)
def vines(self, blockid, data):
    # rotation
    # vines data is bit coded. decode it first.
    # NOTE: the directions used in this function are the new ones used
    # in minecraft 1.0.0, no the ones used by overviewer 
    # (i.e. north is top-left by defalut)

    # rotate the data by bitwise shift
    shifts = 0
    if self.rotation == 1:
        shifts = 1
    elif self.rotation == 2:
        shifts = 2
    elif self.rotation == 3:
        shifts = 3
    
    for i in range(shifts):
        data = data * 2
        if data & 16:
            data = (data - 16) | 1

    # decode data and prepare textures
    raw_texture = self.load_image_texture("assets/minecraft/textures/blocks/vine.png")
    s = w = n = e = None

    if data & 1: # south
        s = raw_texture
    if data & 2: # west
        w = raw_texture
    if data & 4: # north
        n = raw_texture
    if data & 8: # east
        e = raw_texture

    # texture generation
    img = self.build_full_block(None, n, e, w, s)

    return img

# fence gates
@material(blockid=107, data=range(8), transparent=True, nospawn=True)
def fence_gate(self, blockid, data):

    # rotation
    opened = False
    if data & 0x4:
        data = data & 0x3
        opened = True
    if self.rotation == 1:
        if data == 0: data = 1
        elif data == 1: data = 2
        elif data == 2: data = 3
        elif data == 3: data = 0
    elif self.rotation == 2:
        if data == 0: data = 2
        elif data == 1: data = 3
        elif data == 2: data = 0
        elif data == 3: data = 1
    elif self.rotation == 3:
        if data == 0: data = 3
        elif data == 1: data = 0
        elif data == 2: data = 1
        elif data == 3: data = 2
    if opened:
        data = data | 0x4

    # create the closed gate side
    gate_side = self.load_image_texture("assets/minecraft/textures/blocks/planks_oak.png").copy()
    gate_side_draw = ImageDraw.Draw(gate_side)
    gate_side_draw.rectangle((7,0,15,0),outline=(0,0,0,0),fill=(0,0,0,0))
    gate_side_draw.rectangle((7,4,9,6),outline=(0,0,0,0),fill=(0,0,0,0))
    gate_side_draw.rectangle((7,10,15,16),outline=(0,0,0,0),fill=(0,0,0,0))
    gate_side_draw.rectangle((0,12,15,16),outline=(0,0,0,0),fill=(0,0,0,0))
    gate_side_draw.rectangle((0,0,4,15),outline=(0,0,0,0),fill=(0,0,0,0))
    gate_side_draw.rectangle((14,0,15,15),outline=(0,0,0,0),fill=(0,0,0,0))
    
    # darken the sides slightly, as with the fences
    sidealpha = gate_side.split()[3]
    gate_side = ImageEnhance.Brightness(gate_side).enhance(0.9)
    gate_side.putalpha(sidealpha)
    
    # create the other sides
    mirror_gate_side = self.transform_image_side(gate_side.transpose(Image.FLIP_LEFT_RIGHT))
    gate_side = self.transform_image_side(gate_side)
    gate_other_side = gate_side.transpose(Image.FLIP_LEFT_RIGHT)
    mirror_gate_other_side = mirror_gate_side.transpose(Image.FLIP_LEFT_RIGHT)
    
    # Create img to compose the fence gate
    img = Image.new("RGBA", (24,24), self.bgcolor)
    
    if data & 0x4:
        # opened
        data = data & 0x3
        if data == 0:
            alpha_over(img, gate_side, (2,8), gate_side)
            alpha_over(img, gate_side, (13,3), gate_side)
        elif data == 1:
            alpha_over(img, gate_other_side, (-1,3), gate_other_side)
            alpha_over(img, gate_other_side, (10,8), gate_other_side)
        elif data == 2:
            alpha_over(img, mirror_gate_side, (-1,7), mirror_gate_side)
            alpha_over(img, mirror_gate_side, (10,2), mirror_gate_side)
        elif data == 3:
            alpha_over(img, mirror_gate_other_side, (2,1), mirror_gate_other_side)
            alpha_over(img, mirror_gate_other_side, (13,7), mirror_gate_other_side)
    else:
        # closed
        
        # positions for pasting the fence sides, as with fences
        pos_top_left = (2,3)
        pos_top_right = (10,3)
        pos_bottom_right = (10,7)
        pos_bottom_left = (2,7)
        
        if data == 0 or data == 2:
            alpha_over(img, gate_other_side, pos_top_right, gate_other_side)
            alpha_over(img, mirror_gate_other_side, pos_bottom_left, mirror_gate_other_side)
        elif data == 1 or data == 3:
            alpha_over(img, gate_side, pos_top_left, gate_side)
            alpha_over(img, mirror_gate_side, pos_bottom_right, mirror_gate_side)
    
    return img

# mycelium
block(blockid=110, top_image="assets/minecraft/textures/blocks/mycelium_top.png", side_image="assets/minecraft/textures/blocks/mycelium_side.png")

# lilypad
# At the moment of writing this lilypads has no ancil data and their
# orientation depends on their position on the map. So it uses pseudo
# ancildata.
@material(blockid=111, data=range(4), transparent=True)
def lilypad(self, blockid, data):
    t = self.load_image_texture("assets/minecraft/textures/blocks/waterlily.png").copy()
    if data == 0:
        t = t.rotate(180)
    elif data == 1:
        t = t.rotate(270)
    elif data == 2:
        t = t
    elif data == 3:
        t = t.rotate(90)

    return self.build_full_block(None, None, None, None, None, t)

# nether brick
block(blockid=112, top_image="assets/minecraft/textures/blocks/nether_brick.png")

# nether wart
@material(blockid=115, data=range(4), transparent=True)
def nether_wart(self, blockid, data):
    if data == 0: # just come up
        t = self.load_image_texture("assets/minecraft/textures/blocks/nether_wart_stage_0.png")
    elif data in (1, 2):
        t = self.load_image_texture("assets/minecraft/textures/blocks/nether_wart_stage_1.png")
    else: # fully grown
        t = self.load_image_texture("assets/minecraft/textures/blocks/nether_wart_stage_2.png")
    
    # use the same technic as tall grass
    img = self.build_billboard(t)

    return img

# enchantment table
# TODO there's no book at the moment
@material(blockid=116, transparent=True, nodata=True)
def enchantment_table(self, blockid, data):
    # no book at the moment
    top = self.load_image_texture("assets/minecraft/textures/blocks/enchanting_table_top.png")
    side = self.load_image_texture("assets/minecraft/textures/blocks/enchanting_table_side.png")
    img = self.build_full_block((top, 4), None, None, side, side)

    return img

# brewing stand
# TODO this is a place holder, is a 2d image pasted
@material(blockid=117, data=range(5), transparent=True)
def brewing_stand(self, blockid, data):
    base = self.load_image_texture("assets/minecraft/textures/blocks/brewing_stand_base.png")
    img = self.build_full_block(None, None, None, None, None, base)
    t = self.load_image_texture("assets/minecraft/textures/blocks/brewing_stand.png")
    stand = self.build_billboard(t)
    alpha_over(img,stand,(0,-2))
    return img

# cauldron
@material(blockid=118, data=range(4), transparent=True)
def cauldron(self, blockid, data):
    side = self.load_image_texture("assets/minecraft/textures/blocks/cauldron_side.png")
    top = self.load_image_texture("assets/minecraft/textures/blocks/cauldron_top.png")
    bottom = self.load_image_texture("assets/minecraft/textures/blocks/cauldron_inner.png")
    water = self.transform_image_top(self.load_water())
    if data == 0: # empty
        img = self.build_full_block(top, side, side, side, side)
    if data == 1: # 1/3 filled
        img = self.build_full_block(None , side, side, None, None)
        alpha_over(img, water, (0,8), water)
        img2 = self.build_full_block(top , None, None, side, side)
        alpha_over(img, img2, (0,0), img2)
    if data == 2: # 2/3 filled
        img = self.build_full_block(None , side, side, None, None)
        alpha_over(img, water, (0,4), water)
        img2 = self.build_full_block(top , None, None, side, side)
        alpha_over(img, img2, (0,0), img2)
    if data == 3: # 3/3 filled
        img = self.build_full_block(None , side, side, None, None)
        alpha_over(img, water, (0,0), water)
        img2 = self.build_full_block(top , None, None, side, side)
        alpha_over(img, img2, (0,0), img2)

    return img

# end portal
@material(blockid=119, transparent=True, nodata=True)
def end_portal(self, blockid, data):
    img = Image.new("RGBA", (24,24), self.bgcolor)
    # generate a black texure with white, blue and grey dots resembling stars
    t = Image.new("RGBA", (16,16), (0,0,0,255))
    for color in [(155,155,155,255), (100,255,100,255), (255,255,255,255)]:
        for i in range(6):
            x = randint(0,15)
            y = randint(0,15)
            t.putpixel((x,y),color)

    t = self.transform_image_top(t)
    alpha_over(img, t, (0,0), t)

    return img

# end portal frame (data range 8 to get all orientations of filled)
@material(blockid=120, data=range(8), transparent=True)
def end_portal_frame(self, blockid, data):
    # The bottom 2 bits are oritation info but seems there is no
    # graphical difference between orientations
    top = self.load_image_texture("assets/minecraft/textures/blocks/endframe_top.png")
    eye_t = self.load_image_texture("assets/minecraft/textures/blocks/endframe_eye.png")
    side = self.load_image_texture("assets/minecraft/textures/blocks/endframe_side.png")
    img = self.build_full_block((top, 4), None, None, side, side)
    if data & 0x4 == 0x4: # ender eye on it
        # generate the eye
        eye_t = self.load_image_texture("assets/minecraft/textures/blocks/endframe_eye.png").copy()
        eye_t_s = self.load_image_texture("assets/minecraft/textures/blocks/endframe_eye.png").copy()
        # cut out from the texture the side and the top of the eye
        ImageDraw.Draw(eye_t).rectangle((0,0,15,4),outline=(0,0,0,0),fill=(0,0,0,0))
        ImageDraw.Draw(eye_t_s).rectangle((0,4,15,15),outline=(0,0,0,0),fill=(0,0,0,0))
        # trnasform images and paste
        eye = self.transform_image_top(eye_t)
        eye_s = self.transform_image_side(eye_t_s)
        eye_os = eye_s.transpose(Image.FLIP_LEFT_RIGHT)
        alpha_over(img, eye_s, (5,5), eye_s)
        alpha_over(img, eye_os, (9,5), eye_os)
        alpha_over(img, eye, (0,0), eye)

    return img

# end stone
block(blockid=121, top_image="assets/minecraft/textures/blocks/end_stone.png")

# dragon egg
# NOTE: this isn't a block, but I think it's better than nothing
block(blockid=122, top_image="assets/minecraft/textures/blocks/dragon_egg.png")

# inactive redstone lamp
block(blockid=123, top_image="assets/minecraft/textures/blocks/redstone_lamp_off.png")

# active redstone lamp
block(blockid=124, top_image="assets/minecraft/textures/blocks/redstone_lamp_on.png")

# daylight sensor.  
@material(blockid=151, transparent=True)
def daylight_sensor(self, blockid, data):
    top = self.load_image_texture("assets/minecraft/textures/blocks/daylight_detector_top.png")
    side = self.load_image_texture("assets/minecraft/textures/blocks/daylight_detector_side.png")

    # cut the side texture in half
    mask = side.crop((0,8,16,16))
    side = Image.new(side.mode, side.size, self.bgcolor)
    alpha_over(side, mask,(0,0,16,8), mask)

    # plain slab
    top = self.transform_image_top(top)
    side = self.transform_image_side(side)
    otherside = side.transpose(Image.FLIP_LEFT_RIGHT)
    
    sidealpha = side.split()[3]
    side = ImageEnhance.Brightness(side).enhance(0.9)
    side.putalpha(sidealpha)
    othersidealpha = otherside.split()[3]
    otherside = ImageEnhance.Brightness(otherside).enhance(0.8)
    otherside.putalpha(othersidealpha)
    
    img = Image.new("RGBA", (24,24), self.bgcolor)
    alpha_over(img, side, (0,12), side)
    alpha_over(img, otherside, (12,12), otherside)
    alpha_over(img, top, (0,6), top)
    
    return img


# wooden double and normal slabs
# these are the new wooden slabs, blockids 43 44 still have wooden
# slabs, but those are unobtainable without cheating
@material(blockid=[125, 126], data=range(16), transparent=(44,), solid=True)
def wooden_slabs(self, blockid, data):
    texture = data & 7
    if texture== 0: # oak 
        top = side = self.load_image_texture("assets/minecraft/textures/blocks/planks_oak.png")
    elif texture== 1: # spruce
        top = side = self.load_image_texture("assets/minecraft/textures/blocks/planks_spruce.png")
    elif texture== 2: # birch
        top = side = self.load_image_texture("assets/minecraft/textures/blocks/planks_birch.png")
    elif texture== 3: # jungle
        top = side = self.load_image_texture("assets/minecraft/textures/blocks/planks_jungle.png")
    elif texture== 4: # acacia
        top = side = self.load_image_texture("assets/minecraft/textures/blocks/planks_acacia.png")
    elif texture== 5: # dark wood
        top = side = self.load_image_texture("assets/minecraft/textures/blocks/planks_big_oak.png")
    else:
        return None
    
    if blockid == 125: # double slab
        return self.build_block(top, side)
    
    # cut the side texture in half
    mask = side.crop((0,8,16,16))
    side = Image.new(side.mode, side.size, self.bgcolor)
    alpha_over(side, mask,(0,0,16,8), mask)
    
    # plain slab
    top = self.transform_image_top(top)
    side = self.transform_image_side(side)
    otherside = side.transpose(Image.FLIP_LEFT_RIGHT)
    
    sidealpha = side.split()[3]
    side = ImageEnhance.Brightness(side).enhance(0.9)
    side.putalpha(sidealpha)
    othersidealpha = otherside.split()[3]
    otherside = ImageEnhance.Brightness(otherside).enhance(0.8)
    otherside.putalpha(othersidealpha)
    
    # upside down slab
    delta = 0
    if data & 8 == 8:
        delta = 6
    
    img = Image.new("RGBA", (24,24), self.bgcolor)
    alpha_over(img, side, (0,12 - delta), side)
    alpha_over(img, otherside, (12,12 - delta), otherside)
    alpha_over(img, top, (0,6 - delta), top)
    
    return img

# emerald ore
block(blockid=129, top_image="assets/minecraft/textures/blocks/emerald_ore.png")

# emerald block
block(blockid=133, top_image="assets/minecraft/textures/blocks/emerald_block.png")

# cocoa plant
@material(blockid=127, data=range(12), transparent=True)
def cocoa_plant(self, blockid, data):
    orientation = data & 3
    # rotation
    if self.rotation == 1:
        if orientation == 0: orientation = 1
        elif orientation == 1: orientation = 2
        elif orientation == 2: orientation = 3
        elif orientation == 3: orientation = 0
    elif self.rotation == 2:
        if orientation == 0: orientation = 2
        elif orientation == 1: orientation = 3
        elif orientation == 2: orientation = 0
        elif orientation == 3: orientation = 1
    elif self.rotation == 3:
        if orientation == 0: orientation = 3
        elif orientation == 1: orientation = 0
        elif orientation == 2: orientation = 1
        elif orientation == 3: orientation = 2

    size = data & 12
    if size == 8: # big
        t = self.load_image_texture("assets/minecraft/textures/blocks/cocoa_stage_2.png")
        c_left = (0,3)
        c_right = (8,3)
        c_top = (5,2)
    elif size == 4: # normal
        t = self.load_image_texture("assets/minecraft/textures/blocks/cocoa_stage_1.png")
        c_left = (-2,2)
        c_right = (8,2)
        c_top = (5,2)
    elif size == 0: # small
        t = self.load_image_texture("assets/minecraft/textures/blocks/cocoa_stage_0.png")
        c_left = (-3,2)
        c_right = (6,2)
        c_top = (5,2)

    # let's get every texture piece necessary to do this
    stalk = t.copy()
    ImageDraw.Draw(stalk).rectangle((0,0,11,16),outline=(0,0,0,0),fill=(0,0,0,0))
    ImageDraw.Draw(stalk).rectangle((12,4,16,16),outline=(0,0,0,0),fill=(0,0,0,0))
    
    top = t.copy() # warning! changes with plant size
    ImageDraw.Draw(top).rectangle((0,7,16,16),outline=(0,0,0,0),fill=(0,0,0,0))
    ImageDraw.Draw(top).rectangle((7,0,16,6),outline=(0,0,0,0),fill=(0,0,0,0))

    side = t.copy() # warning! changes with plant size
    ImageDraw.Draw(side).rectangle((0,0,6,16),outline=(0,0,0,0),fill=(0,0,0,0))
    ImageDraw.Draw(side).rectangle((0,0,16,3),outline=(0,0,0,0),fill=(0,0,0,0))
    ImageDraw.Draw(side).rectangle((0,14,16,16),outline=(0,0,0,0),fill=(0,0,0,0))
    
    # first compose the block of the cocoa plant
    block = Image.new("RGBA", (24,24), self.bgcolor)
    tmp = self.transform_image_side(side).transpose(Image.FLIP_LEFT_RIGHT)
    alpha_over (block, tmp, c_right,tmp) # right side
    tmp = tmp.transpose(Image.FLIP_LEFT_RIGHT)
    alpha_over (block, tmp, c_left,tmp) # left side
    tmp = self.transform_image_top(top)
    alpha_over(block, tmp, c_top,tmp)
    if size == 0:
        # fix a pixel hole
        block.putpixel((6,9), block.getpixel((6,10)))

    # compose the cocoa plant
    img = Image.new("RGBA", (24,24), self.bgcolor)
    if orientation in (2,3): # south and west
        tmp = self.transform_image_side(stalk).transpose(Image.FLIP_LEFT_RIGHT)
        alpha_over(img, block,(-1,-2), block)
        alpha_over(img, tmp, (4,-2), tmp)
        if orientation == 3:
            img = img.transpose(Image.FLIP_LEFT_RIGHT)
    elif orientation in (0,1): # north and east
        tmp = self.transform_image_side(stalk.transpose(Image.FLIP_LEFT_RIGHT))
        alpha_over(img, block,(-1,5), block)
        alpha_over(img, tmp, (2,12), tmp)
        if orientation == 0:
            img = img.transpose(Image.FLIP_LEFT_RIGHT)

    return img

# command block
block(blockid=137, top_image="assets/minecraft/textures/blocks/command_block.png")

# beacon block
# at the moment of writing this, it seems the beacon block doens't use
# the data values
@material(blockid=138, transparent=True, nodata = True)
def beacon(self, blockid, data):
    # generate the three pieces of the block
    t = self.load_image_texture("assets/minecraft/textures/blocks/glass.png")
    glass = self.build_block(t,t)
    t = self.load_image_texture("assets/minecraft/textures/blocks/obsidian.png")
    obsidian = self.build_full_block((t,12),None, None, t, t)
    obsidian = obsidian.resize((20,20), Image.ANTIALIAS)
    t = self.load_image_texture("assets/minecraft/textures/blocks/beacon.png")
    crystal = self.build_block(t,t)
    crystal = crystal.resize((16,16),Image.ANTIALIAS)
    
    # compose the block
    img = Image.new("RGBA", (24,24), self.bgcolor)
    alpha_over(img, obsidian, (2, 4), obsidian)
    alpha_over(img, crystal, (4,3), crystal)
    alpha_over(img, glass, (0,0), glass)
    
    return img

# cobblestone and mossy cobblestone walls
# one additional bit of data value added for mossy and cobblestone
@material(blockid=139, data=range(32), transparent=True, nospawn=True)
def cobblestone_wall(self, blockid, data):
    # no rotation, uses pseudo data
    if data & 0b10000 == 0:
        # cobblestone
        t = self.load_image_texture("assets/minecraft/textures/blocks/cobblestone.png").copy()
    else:
        # mossy cobblestone
        t = self.load_image_texture("assets/minecraft/textures/blocks/cobblestone_mossy.png").copy()

    wall_pole_top = t.copy()
    wall_pole_side = t.copy()
    wall_side_top = t.copy()
    wall_side = t.copy()
    # _full is used for walls without pole
    wall_side_top_full = t.copy()
    wall_side_full = t.copy()

    # generate the textures of the wall
    ImageDraw.Draw(wall_pole_top).rectangle((0,0,3,15),outline=(0,0,0,0),fill=(0,0,0,0))
    ImageDraw.Draw(wall_pole_top).rectangle((12,0,15,15),outline=(0,0,0,0),fill=(0,0,0,0))
    ImageDraw.Draw(wall_pole_top).rectangle((0,0,15,3),outline=(0,0,0,0),fill=(0,0,0,0))
    ImageDraw.Draw(wall_pole_top).rectangle((0,12,15,15),outline=(0,0,0,0),fill=(0,0,0,0))

    ImageDraw.Draw(wall_pole_side).rectangle((0,0,3,15),outline=(0,0,0,0),fill=(0,0,0,0))
    ImageDraw.Draw(wall_pole_side).rectangle((12,0,15,15),outline=(0,0,0,0),fill=(0,0,0,0))

    # Create the sides and the top of the pole
    wall_pole_side = self.transform_image_side(wall_pole_side)
    wall_pole_other_side = wall_pole_side.transpose(Image.FLIP_LEFT_RIGHT)
    wall_pole_top = self.transform_image_top(wall_pole_top)

    # Darken the sides slightly. These methods also affect the alpha layer,
    # so save them first (we don't want to "darken" the alpha layer making
    # the block transparent)
    sidealpha = wall_pole_side.split()[3]
    wall_pole_side = ImageEnhance.Brightness(wall_pole_side).enhance(0.8)
    wall_pole_side.putalpha(sidealpha)
    othersidealpha = wall_pole_other_side.split()[3]
    wall_pole_other_side = ImageEnhance.Brightness(wall_pole_other_side).enhance(0.7)
    wall_pole_other_side.putalpha(othersidealpha)

    # Compose the wall pole
    wall_pole = Image.new("RGBA", (24,24), self.bgcolor)
    alpha_over(wall_pole,wall_pole_side, (3,4),wall_pole_side)
    alpha_over(wall_pole,wall_pole_other_side, (9,4),wall_pole_other_side)
    alpha_over(wall_pole,wall_pole_top, (0,0),wall_pole_top)
    
    # create the sides and the top of a wall attached to a pole
    ImageDraw.Draw(wall_side).rectangle((0,0,15,2),outline=(0,0,0,0),fill=(0,0,0,0))
    ImageDraw.Draw(wall_side).rectangle((0,0,11,15),outline=(0,0,0,0),fill=(0,0,0,0))
    ImageDraw.Draw(wall_side_top).rectangle((0,0,11,15),outline=(0,0,0,0),fill=(0,0,0,0))
    ImageDraw.Draw(wall_side_top).rectangle((0,0,15,4),outline=(0,0,0,0),fill=(0,0,0,0))
    ImageDraw.Draw(wall_side_top).rectangle((0,11,15,15),outline=(0,0,0,0),fill=(0,0,0,0))
    # full version, without pole
    ImageDraw.Draw(wall_side_full).rectangle((0,0,15,2),outline=(0,0,0,0),fill=(0,0,0,0))
    ImageDraw.Draw(wall_side_top_full).rectangle((0,4,15,15),outline=(0,0,0,0),fill=(0,0,0,0))
    ImageDraw.Draw(wall_side_top_full).rectangle((0,4,15,15),outline=(0,0,0,0),fill=(0,0,0,0))

    # compose the sides of a wall atached to a pole
    tmp = Image.new("RGBA", (24,24), self.bgcolor)
    wall_side = self.transform_image_side(wall_side)
    wall_side_top = self.transform_image_top(wall_side_top)

    # Darken the sides slightly. These methods also affect the alpha layer,
    # so save them first (we don't want to "darken" the alpha layer making
    # the block transparent)
    sidealpha = wall_side.split()[3]
    wall_side = ImageEnhance.Brightness(wall_side).enhance(0.7)
    wall_side.putalpha(sidealpha)

    alpha_over(tmp,wall_side, (0,0),wall_side)
    alpha_over(tmp,wall_side_top, (-5,3),wall_side_top)
    wall_side = tmp
    wall_other_side = wall_side.transpose(Image.FLIP_LEFT_RIGHT)

    # compose the sides of the full wall
    tmp = Image.new("RGBA", (24,24), self.bgcolor)
    wall_side_full = self.transform_image_side(wall_side_full)
    wall_side_top_full = self.transform_image_top(wall_side_top_full.rotate(90))

    # Darken the sides slightly. These methods also affect the alpha layer,
    # so save them first (we don't want to "darken" the alpha layer making
    # the block transparent)
    sidealpha = wall_side_full.split()[3]
    wall_side_full = ImageEnhance.Brightness(wall_side_full).enhance(0.7)
    wall_side_full.putalpha(sidealpha)

    alpha_over(tmp,wall_side_full, (4,0),wall_side_full)
    alpha_over(tmp,wall_side_top_full, (3,-4),wall_side_top_full)
    wall_side_full = tmp
    wall_other_side_full = wall_side_full.transpose(Image.FLIP_LEFT_RIGHT)

    # Create img to compose the wall
    img = Image.new("RGBA", (24,24), self.bgcolor)

    # Position wall imgs around the wall bit stick
    pos_top_left = (-5,-2)
    pos_bottom_left = (-8,4)
    pos_top_right = (5,-3)
    pos_bottom_right = (7,4)
    
    # +x axis points top right direction
    # +y axis points bottom right direction
    # There are two special cases for wall without pole.
    # Normal case: 
    # First compose the walls in the back of the image, 
    # then the pole and then the walls in the front.
    if (data == 0b1010) or (data == 0b11010):
        alpha_over(img, wall_other_side_full,(0,2), wall_other_side_full)
    elif (data == 0b0101) or (data == 0b10101):
        alpha_over(img, wall_side_full,(0,2), wall_side_full)
    else:
        if (data & 0b0001) == 1:
            alpha_over(img,wall_side, pos_top_left,wall_side)                # top left
        if (data & 0b1000) == 8:
            alpha_over(img,wall_other_side, pos_top_right,wall_other_side)    # top right

        alpha_over(img,wall_pole,(0,0),wall_pole)
            
        if (data & 0b0010) == 2:
            alpha_over(img,wall_other_side, pos_bottom_left,wall_other_side)      # bottom left    
        if (data & 0b0100) == 4:
            alpha_over(img,wall_side, pos_bottom_right,wall_side)                  # bottom right
    
    return img

# carrots and potatoes
@material(blockid=[141,142], data=range(8), transparent=True, nospawn=True)
def crops(self, blockid, data):
    if data != 7: # when growing they look the same
        # data = 7 -> fully grown, everything else is growing
        # this seems to work, but still not sure
        raw_crop = self.load_image_texture("assets/minecraft/textures/blocks/potatoes_stage_%d.png" % (data % 3))
    elif blockid == 141: # carrots
        raw_crop = self.load_image_texture("assets/minecraft/textures/blocks/carrots_stage_3.png")
    else: # potatoes
        raw_crop = self.load_image_texture("assets/minecraft/textures/blocks/potatoes_stage_3.png")
    crop1 = self.transform_image_top(raw_crop)
    crop2 = self.transform_image_side(raw_crop)
    crop3 = crop2.transpose(Image.FLIP_LEFT_RIGHT)

    img = Image.new("RGBA", (24,24), self.bgcolor)
    alpha_over(img, crop1, (0,12), crop1)
    alpha_over(img, crop2, (6,3), crop2)
    alpha_over(img, crop3, (6,3), crop3)
    return img

# anvils
@material(blockid=145, data=range(12), transparent=True)
def anvil(self, blockid, data):
    
    # anvils only have two orientations, invert it for rotations 1 and 3
    orientation = data & 0x1
    if self.rotation in (1,3):
        if orientation == 1:
            orientation = 0
        else:
            orientation = 1

    # get the correct textures
    # the bits 0x4 and 0x8 determine how damaged is the anvil
    if (data & 0xc) == 0: # non damaged anvil
        top = self.load_image_texture("assets/minecraft/textures/blocks/anvil_top_damaged_0.png")
    elif (data & 0xc) == 0x4: # slightly damaged
        top = self.load_image_texture("assets/minecraft/textures/blocks/anvil_top_damaged_1.png")
    elif (data & 0xc) == 0x8: # very damaged
        top = self.load_image_texture("assets/minecraft/textures/blocks/anvil_top_damaged_2.png")
    # everything else use this texture
    big_side = self.load_image_texture("assets/minecraft/textures/blocks/anvil_base.png").copy()
    small_side = self.load_image_texture("assets/minecraft/textures/blocks/anvil_base.png").copy()
    base = self.load_image_texture("assets/minecraft/textures/blocks/anvil_base.png").copy()
    small_base = self.load_image_texture("assets/minecraft/textures/blocks/anvil_base.png").copy()
    
    # cut needed patterns
    ImageDraw.Draw(big_side).rectangle((0,8,15,15),outline=(0,0,0,0),fill=(0,0,0,0))
    ImageDraw.Draw(small_side).rectangle((0,0,2,15),outline=(0,0,0,0),fill=(0,0,0,0))
    ImageDraw.Draw(small_side).rectangle((13,0,15,15),outline=(0,0,0,0),fill=(0,0,0,0))
    ImageDraw.Draw(small_side).rectangle((0,8,15,15),outline=(0,0,0,0),fill=(0,0,0,0))
    ImageDraw.Draw(base).rectangle((0,0,15,15),outline=(0,0,0,0))
    ImageDraw.Draw(base).rectangle((1,1,14,14),outline=(0,0,0,0))
    ImageDraw.Draw(small_base).rectangle((0,0,15,15),outline=(0,0,0,0))
    ImageDraw.Draw(small_base).rectangle((1,1,14,14),outline=(0,0,0,0))
    ImageDraw.Draw(small_base).rectangle((2,2,13,13),outline=(0,0,0,0))
    ImageDraw.Draw(small_base).rectangle((3,3,12,12),outline=(0,0,0,0))
    
    # check orientation and compose the anvil
    if orientation == 1: # bottom-left top-right
        top = top.rotate(90)
        left_side = small_side
        left_pos = (1,7)
        right_side = big_side
        right_pos = (10,5)
    else: # top-left bottom-right
        right_side = small_side
        right_pos = (12,7)
        left_side = big_side
        left_pos = (3,5)
    
    img = Image.new("RGBA", (24,24), self.bgcolor)
    
    # darken sides
    alpha = big_side.split()[3]
    big_side = ImageEnhance.Brightness(big_side).enhance(0.8)
    big_side.putalpha(alpha)
    alpha = small_side.split()[3]
    small_side = ImageEnhance.Brightness(small_side).enhance(0.9)
    small_side.putalpha(alpha)
    alpha = base.split()[3]
    base_d = ImageEnhance.Brightness(base).enhance(0.8)
    base_d.putalpha(alpha)
    
    # compose
    base = self.transform_image_top(base)
    base_d = self.transform_image_top(base_d)
    small_base = self.transform_image_top(small_base)
    top = self.transform_image_top(top)
    
    alpha_over(img, base_d, (0,12), base_d)
    alpha_over(img, base_d, (0,11), base_d)
    alpha_over(img, base_d, (0,10), base_d)
    alpha_over(img, small_base, (0,10), small_base)
    
    alpha_over(img, top, (0,0), top)
    
    left_side = self.transform_image_side(left_side)
    right_side = self.transform_image_side(right_side).transpose(Image.FLIP_LEFT_RIGHT)
    
    alpha_over(img, left_side, left_pos, left_side)
    alpha_over(img, right_side, right_pos, right_side)
    
    return img


# block of redstone
block(blockid=152, top_image="assets/minecraft/textures/blocks/redstone_block.png")

# nether quartz ore
block(blockid=153, top_image="assets/minecraft/textures/blocks/quartz_ore.png")

# block of quartz
@material(blockid=155, data=range(5), solid=True)
def quartz_block(self, blockid, data):
    
    if data in (0,1): # normal and chiseled quartz block
        if data == 0:
            top = self.load_image_texture("assets/minecraft/textures/blocks/quartz_block_top.png")
            side = self.load_image_texture("assets/minecraft/textures/blocks/quartz_block_side.png")
        else:
            top = self.load_image_texture("assets/minecraft/textures/blocks/quartz_block_chiseled_top.png")
            side = self.load_image_texture("assets/minecraft/textures/blocks/quartz_block_chiseled.png")    
        return self.build_block(top, side)
    
    # pillar quartz block with orientation
    top = self.load_image_texture("assets/minecraft/textures/blocks/quartz_block_lines_top.png")
    side = self.load_image_texture("assets/minecraft/textures/blocks/quartz_block_lines.png").copy()
    if data == 2: # vertical
        return self.build_block(top, side)
    elif data == 3: # north-south oriented
        if self.rotation in (0,2):
            return self.build_full_block(side, None, None, top, side.rotate(90))
        return self.build_full_block(side.rotate(90), None, None, side.rotate(90), top)
        
    elif data == 4: # east-west oriented
        if self.rotation in (0,2):
            return self.build_full_block(side.rotate(90), None, None, side.rotate(90), top)
        return self.build_full_block(side, None, None, top, side.rotate(90))
    
# hopper
@material(blockid=154, data=range(4), transparent=True)
def hopper(self, blockid, data):
    #build the top
    side = self.load_image_texture("assets/minecraft/textures/blocks/hopper_outside.png")
    top = self.load_image_texture("assets/minecraft/textures/blocks/hopper_top.png")
    bottom = self.load_image_texture("assets/minecraft/textures/blocks/hopper_inside.png")
    hop_top = self.build_full_block((top,10), side, side, side, side, side)

    #build a solid block for mid/top
    hop_mid = self.build_full_block((top,5), side, side, side, side, side)
    hop_bot = self.build_block(side,side)

    hop_mid = hop_mid.resize((17,17),Image.ANTIALIAS)
    hop_bot = hop_bot.resize((10,10),Image.ANTIALIAS)
    
    #compose the final block
    img = Image.new("RGBA", (24,24), self.bgcolor)
    alpha_over(img, hop_bot, (7,14), hop_bot)
    alpha_over(img, hop_mid, (3,3), hop_mid)
    alpha_over(img, hop_top, (0,-6), hop_top)

    return img

# hay block
@material(blockid=170, data=range(9), solid=True)
def hayblock(self, blockid, data):
    top = self.load_image_texture("assets/minecraft/textures/blocks/hay_block_top.png")
    side = self.load_image_texture("assets/minecraft/textures/blocks/hay_block_side.png")

    if self.rotation == 1:
        if data == 4: data = 8
        elif data == 8: data = 4
    elif self.rotation == 3:
        if data == 4: data = 8
        elif data == 8: data = 4

    # choose orientation and paste textures
    if data == 4: # east-west orientation
        return self.build_full_block(side.rotate(90), None, None, top, side.rotate(90))
    elif data == 8: # north-south orientation
        return self.build_full_block(side, None, None, side.rotate(90), top)
    else:
        return self.build_block(top, side)


# carpet - wool block that's small?
@material(blockid=171, data=range(16), transparent=True)
def carpet(self, blockid, data):
    texture = self.load_image_texture("assets/minecraft/textures/blocks/wool_colored_%s.png" % color_map[data])

    return self.build_full_block((texture,15),texture,texture,texture,texture)

#clay block
block(blockid=172, top_image="assets/minecraft/textures/blocks/hardened_clay.png")

#stained hardened clay
@material(blockid=159, data=range(16), solid=True)
def stained_clay(self, blockid, data):
    texture = self.load_image_texture("assets/minecraft/textures/blocks/hardened_clay_stained_%s.png" % color_map[data])

    return self.build_block(texture,texture)

#coal block
block(blockid=173, top_image="assets/minecraft/textures/blocks/coal_block.png")

# packed ice block
block(blockid=174, top_image="assets/minecraft/textures/blocks/ice_packed.png")

@material(blockid=175, data=range(16), transparent=True)
def flower(self, blockid, data):
    double_plant_map = ["sunflower", "syringa", "grass", "fern", "rose", "paeonia", "paeonia", "paeonia"]
    plant = double_plant_map[data & 0x7]

    if data & 0x8:
        part = "top"
    else:
        part = "bottom"

    png = "assets/minecraft/textures/blocks/double_plant_%s_%s.png" % (plant,part)
    texture = self.load_image_texture(png)
    img = self.build_billboard(texture)

    #sunflower top
    if data == 8:
        bloom_tex = self.load_image_texture("assets/minecraft/textures/blocks/double_plant_sunflower_front.png")
        alpha_over(img, bloom_tex.resize((14, 11), Image.ANTIALIAS), (5,5))

    return img

########NEW FILE########
__FILENAME__ = tileset
#    This file is part of the Minecraft Overviewer.
#
#    Minecraft Overviewer is free software: you can redistribute it and/or
#    modify it under the terms of the GNU General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or (at
#    your option) any later version.
#
#    Minecraft Overviewer is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General
#    Public License for more details.
#
#    You should have received a copy of the GNU General Public License along
#    with the Overviewer.  If not, see <http://www.gnu.org/licenses/>.

import itertools
import logging
import os
import os.path
import sys
import shutil
import random
import functools
import time
import errno
import stat
import platform
from collections import namedtuple
from itertools import product, izip, chain

from PIL import Image

from .util import roundrobin
from . import nbt
from .files import FileReplacer, get_fs_caps
from .optimizeimages import optimize_image
import rendermodes
import c_overviewer
from c_overviewer import resize_half

"""

tileset.py contains the TileSet class, and in general, routines that manage a
set of output tiles corresponding to a requested rendermode for a world. In
general, there will be one TileSet object per world per rendermode requested by
the user.

The TileSet class implements the Worker interface. This interface has the
following methods:

do_preprocessing()
    This method is called before iterate_work_items(). It should do any work
    that needs to be done prior to iterate_work_items(). It is not called for
    instances that will not have iterate_work_items() called.

get_num_phases()
    This method returns an integer indicating how many phases of work this
    worker has to perform. Each phase of work is completed serially with the
    other phases... all work done by one phase is done before the next phase is
    started.

get_phase_length(phase)
    This method returns an integer indicating how many work items there are in
    this phase. This number is used for purely informational purposes. It can
    be exact, or an estimate. If there is no useful information on the size of
    a phase, return None.

iterate_work_items(phase)
    Takes a phase number (a non-negative integer). This method should return an
    iterator over work items and a list of dependencies i.e. (work_item, [d1,
    d2, ...]). The work items and dependencies can be any pickelable object;
    they are treated as opaque by the Dispatcher. The work item objects are
    passed back in to the do_work() method (perhaps in a different, identically
    configured instance).

    The dependency items are other work items that are compared for equality
    with work items that are already in the queue. The dispatcher guarantees
    that dependent items which are currently in the queue or in progress finish
    before the corresponding work item is started. Note that dependencies must
    have already been yielded as work items before they can be used as
    dependencies; the dispatcher requires this ordering or it cannot guarantee
    the dependencies are met.

do_work(workobj)
    Does the work for a given work object. This method is not expected to
    return anything, so the results of its work should be reflected on the
    filesystem or by sending signals.


"""

# small but useful
def iterate_base4(d):
    """Iterates over a base 4 number with d digits"""
    return product(xrange(4), repeat=d)

# A named tuple class storing the row and column bounds for the to-be-rendered
# world
Bounds = namedtuple("Bounds", ("mincol", "maxcol", "minrow", "maxrow"))

# A note about the implementation of the different rendercheck modes:
#
# For reference, here's what the rendercheck modes are:
#   0
#       Only render tiles that have chunks with a greater mtime than the last
#       render timestamp, and their ancestors.
#
#       In other words, only renders parts of the map that have changed since
#       last render, nothing more, nothing less.
#
#       This is the fastest option, but will not detect tiles that have e.g.
#       been deleted from the directory tree, or pick up where a partial
#       interrupted render left off.

#   1
#       For render-tiles, render all whose chunks have an mtime greater than
#       the mtime of the tile on disk, and their composite-tile ancestors.
#
#       Also rerender any tiles rendered before forcerendertime. It is nonzero
#       whenever a mode=2 render has been interrupted.
#
#       Also check all other composite-tiles and render any that have children
#       with more rencent mtimes than itself.
#
#       This is slower due to stat calls to determine tile mtimes, but safe if
#       the last render was interrupted.

#   2
#       Render all tiles unconditionally. This is a "forcerender" and is the
#       slowest, but SHOULD be specified if this is the first render because
#       the scan will forgo tile stat calls. It's also useful for changing
#       texture packs or other options that effect the output.

#   3
#       A very special mode. Using this will not actually render
#       anything, but will leave this tileset in the resulting
#       map. Useful for renders that you want to keep, but not
#       update. Since this mode is so simple, it's left out of the
#       rest of this discussion.

#
# For 0 our caller has explicitly requested not to check mtimes on disk to
# speed things up. So the mode 0 chunk scan only looks at chunk mtimes and the
# last render mtime from the asset manager, and marks only the tiles that need
# rendering based on that.  Mode 0 then iterates over all dirty render-tiles
# and composite-tiles that depend on them. It does not check mtimes of any
# tiles on disk, so this is only a good option if the last render was not
# interrupted.

# For mode 2, this is a forcerender, the caller has requested we render
# everything. The mode 2 chunk scan marks every tile as needing rendering, and
# disregards mtimes completely. Mode 2 then iterates over all render-tiles and
# composite-tiles that depend on them, which is every tile. It therefore
# renders everything.

# In both 0 and 2 the render iteration is the same: the dirtytile tree built is
# authoritive on every tile that needs rendering.

# In mode 1, things are most complicated. Mode 1 chunk scan is identical to a
# forcerender, or mode 2 scan: every render tile that should exist is marked in
# the dirtytile tree. But instead of iterating over that tree directly, a
# special recursive algorithm goes through and checks every tile that should
# exist and determines whether it needs rendering. This routine works in such a
# way so that every tile is stat()'d at most once, so it shouldn't be too bad.
# This logic happens in the iterate_work_items() method, and therefore in the
# master process, not the worker processes.

# In all three rendercheck modes, the results out of iterate_work_items() is
# authoritive on what needs rendering. The do_work() method does not need to do
# any additional checks.

__all__ = ["TileSet"]
class TileSet(object):
    """The TileSet object manages the work required to produce a set of tiles
    on disk. It calculates the work that needs to be done and tells the
    dipatcher (through the Worker interface) this information. The Dispatcher
    then tells this object when and where to do the work of rendering the tiles.

    """

    def __init__(self, worldobj, regionsetobj, assetmanagerobj, texturesobj, options, outputdir):
        """Construct a new TileSet object with the given configuration options
        dictionary.

        options is a dictionary of configuration parameters (strings mapping to
        values) that are interpreted by the rendering engine.
        
        worldobj is the World object that regionsetobj is from.

        regionsetobj is the RegionSet object that is used to render the tiles.

        assetmanagerobj is the AssetManager object that represents the
        destination directory where we'll put our tiles.

        texturesobj is the Textures object to pass into the rendering routine.
        This class does nothing with it except pass it through.

        outputdir is the absolute path to the tile output directory where the
        tiles are saved. It is created if it doesn't exist

        Current valid options for the options dictionary are shown below. All
        the options must be specified unless they are not relevant. If the
        given options do not conform to the specifications, behavior is
        undefined (this class does not do any error checking and assumes items
        are given in the correct form).

        bgcolor
            A hex string specifying the background color for jpeg output.
            e.g.: "#1A1A1A". Not relevant unless rendering jpeg.

        renderchecks
            An integer indicating how to determine which tiles need updating
            and which don't. This key is optional; if not specified, an
            appropriate mode is determined from the persistent config obtained
            from the asset manager. This is one of three levels:

            0
                Only render tiles that have chunks with a greater mtime than
                the last render timestamp, and their ancestors.

                In other words, only renders parts of the map that have changed
                since last render, nothing more, nothing less.

                This is the fastest option, but will not detect tiles that have
                e.g. been deleted from the directory tree, or pick up where a
                partial interrupted render left off.

            1
                "check-tiles" mode. For render-tiles, render all whose chunks
                have an mtime greater than the mtime of the tile on disk, and
                their upper-tile ancestors.

                Also check all other upper-tiles and render any that have
                children with more rencent mtimes than itself.

                Also remove tiles and directory trees that do exist but
                shouldn't.

                This is slower due to stat calls to determine tile mtimes, but
                safe if the last render was interrupted.

            2
                Render all tiles unconditionally. This is a "forcerender" and
                is the slowest, but SHOULD be specified if this is the first
                render because the scan will forgo tile stat calls. It's also
                useful for changing texture packs or other options that effect
                the output.

            3
                A very special mode. Using this will not actually render
                anything, but will leave this tileset in the resulting
                map. Useful for renders that you want to keep, but not
                update. Since this mode is so simple, it's left out of the
                rest of this discussion.

        imgformat
            A string indicating the output format. Must be one of 'png' or
            'jpeg'

        imgquality
            An integer 1-100 indicating the quality of the jpeg output. Only
            relevant in jpeg mode.

        optimizeimg
            A list of optimizer instances to use.

        rendermode
            Perhaps the most important/relevant option: a string indicating the
            render mode to render. This rendermode must have already been
            registered with the C extension module.

        rerenderprob
            A floating point number between 0 and 1 indicating the probability
            that a tile which is not marked for render by any mtime checks will
            be rendered anyways. 0 disables this option.

        changelist
            Optional: A file descriptor which will be opened and used as the
            changelist output: each tile written will get outputted to the
            specified fd.

        Other options that must be specified but aren't really documented
        (oops. consider it a TODO):
        * worldname_orig
        * dimension
        * title
        * name

        """
        self.options = options
        self.world = worldobj
        self.regionset = regionsetobj
        self.am = assetmanagerobj
        self.textures = texturesobj
        self.outputdir = os.path.abspath(outputdir)

        config = self.am.get_tileset_config(self.options.get("name"))
        self.config = config

        self.last_rendertime = config.get('last_rendertime', 0)
        self.forcerendertime = config.get('forcerendertime', 0)

        if "renderchecks" not in self.options:
            # renderchecks was not given, this indicates it was not specified
            # in either the config file or the command line. The following code
            # attempts to detect the most appropriate mode
            if not config:
                # No persistent config?
                if os.path.exists(self.outputdir):
                    # Somehow there's no config but the output dir DOES exist.
                    # That's strange!
                    logging.warning(
                        "For render '%s' I couldn't find any persistent config, "
                        "but I did find my tile directory already exists. This "
                        "shouldn't normally happen, something may be up, but I "
                        "think I can continue...", self.options['name'])
                    logging.info("Switching to --check-tiles mode")
                    self.options['renderchecks'] = 1
                else:
                    # This is the typical code path for an initial render, make
                    # this a "forcerender"
                    self.options['renderchecks'] = 2
                    logging.debug("This is the first time rendering %s. Doing" +
                            " a full-render",
                            self.options['name'])
            elif not os.path.exists(self.outputdir):
                # Somehow the outputdir got erased but the metadata file is
                # still there. That's strange!
                logging.warning(
                        "This is strange. There is metadata for render '%s' but "
                        "the output directory is missing. This shouldn't "
                        "normally happen. I guess we have no choice but to do a "
                        "--forcerender", self.options['name'])
                self.options['renderchecks'] = 2
            elif config.get("render_in_progress", False):
                # The last render must have been interrupted. The default should be
                # a check-tiles render then
                logging.warning(
                        "The last render for '%s' didn't finish. I'll be " +
                        "scanning all the tiles to make sure everything's up "+
                        "to date.",
                        self.options['name'],
                        )
                logging.warning("The total tile count will be (possibly "+
                        "wildly) inaccurate, because I don't know how many "+
                        "tiles need rendering. I'll be checking them as I go")
                if self.forcerendertime != 0:
                    logging.info(
                            "The unfinished render was a --forcerender. " +
                            "Rerendering any tiles older than %s",
                            time.strftime("%x %X", time.localtime(self.forcerendertime)),
                            )
                self.options['renderchecks'] = 1
            else:
                logging.debug("No rendercheck mode specified for %s. "+
                        "Rendering tile whose chunks have changed since %s",
                        self.options['name'],
                        time.strftime("%x %X", time.localtime(self.last_rendertime)),
                        )
                self.options['renderchecks'] = 0

        if not os.path.exists(self.outputdir):
            if self.options['renderchecks'] != 2:
                logging.warning(
                "The tile directory didn't exist, but you have specified "
                "explicitly not to do a --fullrender (which is the default for "
                "this situation). I'm overriding your decision and setting "
                "--fullrender for just this run")
                self.options['renderchecks'] = 2
            os.mkdir(self.outputdir)

        # must wait until outputdir exists
        self.fs_caps = get_fs_caps(self.outputdir)

        if self.options['renderchecks'] == 2:
            # Set forcerendertime so that upon an interruption the next render
            # will continue where we left off.
            self.forcerendertime = int(time.time())

        # Set the image format according to the options
        if self.options['imgformat'] == 'png':
            self.imgextension = 'png'
        elif self.options['imgformat'] in ('jpeg', 'jpg'):
            self.imgextension = 'jpg'
        else:
            raise ValueError("imgformat must be one of: 'png' or 'jpg'")

        # This sets self.treedepth, self.xradius, and self.yradius
        self._set_map_size()

    # Only pickle the initial state. Don't pickle anything resulting from the
    # do_preprocessing step
    def __getstate__(self):
        return self.world, self.regionset, self.am, self.textures, self.options, self.outputdir
    def __setstate__(self, state):
        self.__init__(*state)

    def do_preprocessing(self):
        """For the preprocessing step of the Worker interface, this does the
        chunk scan and stores the resulting tree as a private instance
        attribute for later use in iterate_work_items()

        """

        # skip if we're told to
        if self.options['renderchecks'] == 3:
            return
        
        # REMEMBER THAT ATTRIBUTES ASSIGNED IN THIS METHOD ARE NOT AVAILABLE IN
        # THE do_work() METHOD (because this is only called in the main process
        # not the workers)

        # This warning goes here so it's only shown once
        if self.treedepth >= 15:
            logging.warning("Just letting you know, your map requires %s zoom levels. This is REALLY big!",
                    self.treedepth)

        # Do any tile re-arranging if necessary. Skip if there was no config
        # from the asset-manager, which typically indicates this is a new
        # render
        if self.config:
            self._rearrange_tiles()

        # Do the chunk scan here
        self.dirtytree = self._chunk_scan()

    def get_num_phases(self):
        """Returns the number of levels in the quadtree, which is equal to the
        number of phases of work that need to be done.

        """
        return 1

    def get_phase_length(self, phase):
        """Returns the number of work items in a given phase.
        """
        # Yeah functional programming!
        # and by functional we mean a bastardized python switch statement
        return {
                0: lambda: self.dirtytree.count_all(),
                #there is no good way to guess this so just give total count
                1: lambda: (4**(self.treedepth+1)-1)/3,
                2: lambda: self.dirtytree.count_all(),
                3: lambda: 0,
                }[self.options['renderchecks']]()

    def iterate_work_items(self, phase):
        """Iterates over the dirty tiles in the tree and return them in the
        appropriate order with the appropriate dependencies.

        This method returns an iterator over (obj, [dependencies, ...])
        """

        # skip if asked to
        if self.options['renderchecks'] == 3:
            return
        
        # The following block of code implementes the changelist functionality.
        fd = self.options.get("changelist", None)
        if fd:
            logging.debug("Changelist activated for %s (fileno %s)", self, fd)
            # This re-implements some of the logic from do_work()
            def write_out(tilepath):
                if len(tilepath) == self.treedepth:
                    rt = RenderTile.from_path(tilepath)
                    imgpath = rt.get_filepath(self.outputdir, self.imgextension)
                elif len(tilepath) == 0:
                    imgpath = os.path.join(self.outputdir, "base."+self.imgextension)
                else:
                    dest = os.path.join(self.outputdir, *(str(x) for x in tilepath[:-1]))
                    name = str(tilepath[-1])
                    imgpath = os.path.join(dest, name) + "." + self.imgextension
                # We use low-level file output because we don't want open file
                # handles being passed to subprocesses. fd is just an integer.
                # This method is only called from the master process anyways.
                # We don't use os.fdopen() because this fd may be shared by
                # many tileset objects, and as soon as this method exists the
                # file object may be garbage collected, closing the file.
                os.write(fd, imgpath + "\n")


        # See note at the top of this file about the rendercheck modes for an
        # explanation of what this method does in different situations.
        #
        # For modes 0 and 2, self.dirtytree holds exactly the tiles we need to
        # render. Iterate over the tiles in using the posttraversal() method.
        # Yield each item. Easy.
        if self.options['renderchecks'] in (0,2):
            for tilepath in self.dirtytree.posttraversal(robin=True):
                dependencies = []
                # These tiles may or may not exist, but the dispatcher won't
                # care according to the worker interface protocol It will only
                # wait for the items that do exist and are in the queue.
                for i in range(4):
                    dependencies.append( tilepath + (i,) )
                if fd:
                    write_out(tilepath)
                yield tilepath, dependencies

        else:
            # For mode 1, self.dirtytree holds every tile that should exist,
            # but invoke _iterate_and_check_tiles() to determine which tiles
            # need rendering.
            for tilepath, mtime, needs_rendering in self._iterate_and_check_tiles(()):
                if needs_rendering:
                    dependencies = []
                    for i in range(4):
                        dependencies.append( tilepath + (i,) )
                    if fd:
                        write_out(tilepath)
                    yield tilepath, dependencies

    def do_work(self, tilepath):
        """Renders the given tile.

        tilepath is yielded by iterate_work_items and is an iterable of
        integers representing the path of the tile to render.

        """
        if len(tilepath) == self.treedepth:
            # A render-tile
            self._render_rendertile(RenderTile.from_path(tilepath))
        else:
            # A composite-tile
            if len(tilepath) == 0:
                # The base tile
                dest = self.outputdir
                name = "base"
            else:
                # All others
                dest = os.path.join(self.outputdir, *(str(x) for x in tilepath[:-1]))
                name = str(tilepath[-1])
            self._render_compositetile(dest, name)

    def get_initial_data(self):
        """This is called similarly to get_persistent_data, but is called after
        do_preprocessing but before any work is acutally done.

        """
        d = self.get_persistent_data()
        # This is basically the same as get_persistent_data() with the
        # following exceptions:
        # * last_rendertime is not changed
        # * A key "render_in_progress" is set to True
        # * forcerendertime is set so that an interrupted mode=2 render will
        #   finish properly.
        d['last_rendertime'] = self.last_rendertime
        d['render_in_progress'] = True
        d['forcerendertime'] = self.forcerendertime
        return d

    def get_persistent_data(self):
        """Returns a dictionary representing the persistent data of this
        TileSet. Typically this is called by AssetManager

        """
        def bgcolorformat(color):
            return "#%02x%02x%02x" % color[0:3]
        isOverlay = self.options.get("overlay") or (not any(isinstance(x, rendermodes.Base) for x in self.options.get("rendermode")))

        # don't update last render time if we're leaving this alone
        last_rendertime = self.last_rendertime
        if self.options['renderchecks'] != 3:
            last_rendertime = self.max_chunk_mtime        
        
        d = dict(name = self.options.get('title'),
                zoomLevels = self.treedepth,
                defaultZoom = self.options.get('defaultzoom'),
                maxZoom = self.options.get('maxzoom', self.treedepth) if self.options.get('maxzoom', self.treedepth) >= 0 else self.treedepth+self.options.get('maxzoom'),
                path = self.options.get('name'),
                base = self.options.get('base'),
                bgcolor = bgcolorformat(self.options.get('bgcolor')),
                world = self.options.get('worldname_orig') +
                    (" - " + self.options.get('dimension')[0] if self.options.get('dimension')[1] != 0 else ''),
                last_rendertime = last_rendertime,
                imgextension = self.imgextension,
                isOverlay = isOverlay,
                poititle = self.options.get("poititle"),
                showlocationmarker = self.options.get("showlocationmarker")
                )
        d['maxZoom'] = min(self.treedepth, d['maxZoom'])
        d['minZoom'] = min(max(0, self.options.get("minzoom", 0)), d['maxZoom'])
        d['defaultZoom'] = max(d['minZoom'], min(d['defaultZoom'], d['maxZoom']))

        if isOverlay:
            d.update({"tilesets": self.options.get("overlay")})

        # None means overworld
        if (self.regionset.get_type() == None and self.options.get("showspawn", True)):
            d.update({"spawn": self.options.get("spawn")})
        else:
            d.update({"spawn": "false"});

        try:
            d['north_direction'] = self.regionset.north_dir
        except AttributeError:
            d['north_direction'] = 0

        return d

    def _find_chunk_range(self):
        """Finds the chunk range in rows/columns and stores them in
        self.minrow, self.maxrow, self.mincol, self.maxcol

        """
        minrow = mincol = maxrow = maxcol = 0

        for c_x, c_z, _ in self.regionset.iterate_chunks():
            # Convert these coordinates to row/col
            col, row = convert_coords(c_x, c_z)

            minrow = min(minrow, row)
            maxrow = max(maxrow, row)
            mincol = min(mincol, col)
            maxcol = max(maxcol, col)
        return Bounds(mincol, maxcol, minrow, maxrow)

    def _set_map_size(self):
        """Finds and sets the depth of the map's quadtree, as well as the
        xradius and yradius of the resulting tiles.

        Sets self.treedepth, self.xradius, self.yradius

        """
        # Calculate the min and max column over all the chunks.
        # This returns a Bounds namedtuple
        bounds = self._find_chunk_range()

        # Calculate the depth of the tree
        for p in xrange(2,33): # max 32
            # Will 2^p tiles wide and high suffice?

            # X has twice as many chunks as tiles, then halved since this is a
            # radius
            xradius = 2**p
            # Y has 4 times as many chunks as tiles, then halved since this is
            # a radius
            yradius = 2*2**p
            # The +32 on the y bounds is because chunks are very tall, and in
            # rare cases when the bottom of the map is close to a border, it
            # could get cut off
            if xradius >= bounds.maxcol and -xradius <= bounds.mincol and \
                    yradius >= bounds.maxrow + 32 and -yradius <= bounds.minrow:
                break
        self.treedepth = p
        self.xradius = xradius
        self.yradius = yradius

    def _rearrange_tiles(self):
        """If the target size of the tree is not the same as the existing size
        on disk, do some re-arranging

        """
        try:
            curdepth = self.config['zoomLevels']
        except KeyError:
            return

        if curdepth == 1:
            # Skip a depth 1 tree. A depth 1 tree pretty much can't happen, so
            # when we detect this it usually means the tree is actually empty
            return
        logging.debug("Current tree depth for %s is reportedly %s. Target tree depth is %s",
                self.options['name'],
                curdepth, self.treedepth)
        if self.treedepth != curdepth:
            if self.treedepth > curdepth:
                logging.warning("Your map seems to have expanded beyond its previous bounds.")
                logging.warning( "Doing some tile re-arrangements... just a sec...")
                for _ in xrange(self.treedepth-curdepth):
                    self._increase_depth()
            elif self.treedepth < curdepth:
                logging.warning("Your map seems to have shrunk. Did you delete some chunks? No problem. Re-arranging tiles, just a sec...")
                for _ in xrange(curdepth - self.treedepth):
                    self._decrease_depth()
                logging.info(
                        "There done. I'm switching to --check-tiles mode for "
                        "this one render. This will make sure any old tiles that "
                        "should no longer exist are deleted.")
                self.options['renderchecks'] = 1

    def _increase_depth(self):
        """Moves existing tiles into place for a larger tree"""
        getpath = functools.partial(os.path.join, self.outputdir)

        # At top level of the tree:
        # quadrant 0 is now 0/3
        # 1 is now 1/2
        # 2 is now 2/1
        # 3 is now 3/0
        # then all that needs to be done is to regenerate the new top level
        for dirnum in range(4):
            newnum = (3,2,1,0)[dirnum]

            newdir = "new" + str(dirnum)
            newdirpath = getpath(newdir)

            files = [str(dirnum)+"."+self.imgextension, str(dirnum)]
            newfiles = [str(newnum)+"."+self.imgextension, str(newnum)]

            os.mkdir(newdirpath)
            for f, newf in zip(files, newfiles):
                p = getpath(f)
                if os.path.exists(p):
                    os.rename(p, getpath(newdir, newf))
            os.rename(newdirpath, getpath(str(dirnum)))

    def _decrease_depth(self):
        """If the map size decreases, or perhaps the user has a depth override
        in effect, re-arrange existing tiles for a smaller tree"""
        getpath = functools.partial(os.path.join, self.outputdir)

        # quadrant 0/3 goes to 0
        # 1/2 goes to 1
        # 2/1 goes to 2
        # 3/0 goes to 3
        # Just worry about the directories here, the files at the top two
        # levels are cheap enough to replace
        if os.path.exists(getpath("0", "3")):
            os.rename(getpath("0", "3"), getpath("new0"))
            shutil.rmtree(getpath("0"))
            os.rename(getpath("new0"), getpath("0"))

        if os.path.exists(getpath("1", "2")):
            os.rename(getpath("1", "2"), getpath("new1"))
            shutil.rmtree(getpath("1"))
            os.rename(getpath("new1"), getpath("1"))

        if os.path.exists(getpath("2", "1")):
            os.rename(getpath("2", "1"), getpath("new2"))
            shutil.rmtree(getpath("2"))
            os.rename(getpath("new2"), getpath("2"))

        if os.path.exists(getpath("3", "0")):
            os.rename(getpath("3", "0"), getpath("new3"))
            shutil.rmtree(getpath("3"))
            os.rename(getpath("new3"), getpath("3"))

        # Delete the files in the top directory to make sure they get re-created.
        files = [str(num)+"."+self.imgextension for num in xrange(4)] + ["base." + self.imgextension]
        for f in files:
            try:
                os.unlink(getpath(f))
            except OSError, e:
                # Ignore file doesn't exist errors
                if e.errno != errno.ENOENT:
                    raise

    def _chunk_scan(self):
        """Scans the chunks of this TileSet's world to determine which
        render-tiles need rendering. Returns a RendertileSet object.

        For rendercheck mode 0: only compares chunk mtimes against last render
        time of the map, and marks tiles as dirty if any chunk has a greater
        mtime than the last render time.

        For rendercheck modes 1 and 2: marks every tile in the tileset
        unconditionally, does not check any mtimes.

        As a side-effect, the scan sets self.max_chunk_mtime to the max of all
        the chunks' mtimes

        """
        # See note at the top of this file about the rendercheck modes for an
        # explanation of what this method does in different situations.

        # Local vars for slightly faster lookups
        depth = self.treedepth
        xradius = self.xradius
        yradius = self.yradius

        dirty = RendertileSet(depth)

        chunkcount = 0
        stime = time.time()

        rendercheck = self.options['renderchecks']
        markall = rendercheck in (1,2)

        rerender_prob = self.options['rerenderprob']

        last_rendertime = self.last_rendertime

        max_chunk_mtime = 0


        # For each chunk, do this:
        #   For each tile that the chunk touches, do this:
        #       Compare the last modified time of the chunk and tile. If the
        #       tile is older, mark it in a RendertileSet object as dirty.


        for chunkx, chunkz, chunkmtime in self.regionset.iterate_chunks() if (markall or platform.system() == 'Windows') else self.regionset.iterate_newer_chunks(last_rendertime): 
            chunkcount += 1

            if chunkmtime > max_chunk_mtime:
                max_chunk_mtime = chunkmtime

            # Convert to diagonal coordinates
            chunkcol, chunkrow = convert_coords(chunkx, chunkz)

            for c, r in get_tiles_by_chunk(chunkcol, chunkrow):

                # Make sure the tile is in the boundary we're rendering.
                # This can happen when rendering at lower treedepth than
                # can contain the entire map, but shouldn't happen if the
                # treedepth is correctly calculated.
                if (
                        c < -xradius or
                        c >= xradius or
                        r < -yradius or
                        r >= yradius
                        ):
                    continue

                # Computes the path in the quadtree from the col,row coordinates
                tile = RenderTile.compute_path(c, r, depth)

                if markall:
                    # markall mode: Skip all other checks, mark tiles
                    # as dirty unconditionally
                    dirty.add(tile.path)
                    continue

                # Check if this tile has already been marked dirty. If so,
                # no need to do any of the below.
                if dirty.query_path(tile.path):
                    continue

                # Stochastic check. Since we're scanning by chunks and not
                # by tiles, and the tiles get checked multiple times for
                # each chunk, this is only an approximation. The given
                # probability is for a particular tile that needs
                # rendering, but since a tile gets touched up to 32 times
                # (once for each chunk in it), divide the probability by
                # 32.
                if rerender_prob and rerender_prob/32 > random.random():
                    dirty.add(tile.path)
                    continue

                # Check mtimes and conditionally add tile to the set
                if chunkmtime > last_rendertime:
                    dirty.add(tile.path)

        t = int(time.time()-stime)
        logging.debug("Finished chunk scan for %s. %s chunks scanned in %s second%s",
                self.options['name'], chunkcount, t,
                "s" if t != 1 else "")

        self.max_chunk_mtime = max_chunk_mtime
        return dirty

    def __str__(self):
        return "<TileSet for %s>" % os.path.basename(self.outputdir)

    def _render_compositetile(self, dest, name):
        """
        Renders a tile at os.path.join(dest, name)+".ext" by taking tiles from
        os.path.join(dest, name, "{0,1,2,3}.png")

        If name is "base" then render tile at os.path.join(dest, "base.png") by
        taking tiles from os.path.join(dest, "{0,1,2,3}.png")
        """
        imgformat = self.imgextension
        imgpath = os.path.join(dest, name) + "." + imgformat

        if name == "base":
            # Special case for the base tile. Its children are in the same
            # directory instead of in a sub-directory
            quadPath = [
                    ((0,0),os.path.join(dest, "0." + imgformat)),
                    ((192,0),os.path.join(dest, "1." + imgformat)),
                    ((0, 192),os.path.join(dest, "2." + imgformat)),
                    ((192,192),os.path.join(dest, "3." + imgformat)),
                    ]
        else:
            quadPath = [
                    ((0,0),os.path.join(dest, name, "0." + imgformat)),
                    ((192,0),os.path.join(dest, name, "1." + imgformat)),
                    ((0, 192),os.path.join(dest, name, "2." + imgformat)),
                    ((192,192),os.path.join(dest, name, "3." + imgformat)),
                    ]

        # Check each of the 4 child tiles, getting their existance and mtime
        # infomation. Also keep track of the max mtime of all children
        max_mtime = 0
        quadPath_filtered = []
        for path in quadPath:
            try:
                quad_mtime = os.stat(path[1])[stat.ST_MTIME]
            except OSError:
                # This tile doesn't exist or some other error with the stat
                # call. Move on.
                continue
            # The tile exists, so we need to use it in our rendering of this
            # composite tile
            quadPath_filtered.append(path)
            if quad_mtime > max_mtime:
                max_mtime = quad_mtime

        # If no children exist, delete this tile
        if not quadPath_filtered:
            try:
                os.unlink(imgpath)
            except OSError, e:
                # Ignore errors if it's "file doesn't exist"
                if e.errno != errno.ENOENT:
                    raise
            logging.warning("Tile %s was requested for render, but no children were found! This is probably a bug", imgpath)
            return

        #logging.debug("writing out compositetile {0}".format(imgpath))

        # Create the actual image now
        img = Image.new("RGBA", (384, 384), self.options['bgcolor'])
		
        # we'll use paste (NOT alpha_over) for quadtree generation because
        # this is just straight image stitching, not alpha blending

        for path in quadPath_filtered:
            try:
                #quad = Image.open(path[1]).resize((192,192), Image.ANTIALIAS)
                src = Image.open(path[1])
                # optimizeimg may have converted them to a palette image in the meantime
                if src.mode != "RGB" and src.mode != "RGBA":
                    src = src.convert("RGBA")
                src.load()

                quad = Image.new("RGBA", (192, 192), self.options['bgcolor'])
                resize_half(quad, src)
                img.paste(quad, path[0])
            except Exception, e:
                logging.warning("Couldn't open %s. It may be corrupt. Error was '%s'", path[1], e)
                logging.warning("I'm going to try and delete it. You will need to run the render again and with --check-tiles")
                try:
                    os.unlink(path[1])
                except Exception, e:
                    logging.error("While attempting to delete corrupt image %s, an error was encountered. You will need to delete it yourself. Error was '%s'", path[1], e)

        # Save it
        with FileReplacer(imgpath, capabilities=self.fs_caps) as tmppath:
            if imgformat == 'jpg':
                img.save(tmppath, "jpeg", quality=self.options['imgquality'], subsampling=0)
            else: # png
                img.save(tmppath, "png")

            if self.options['optimizeimg']:
                optimize_image(tmppath, imgformat, self.options['optimizeimg'])

            os.utime(tmppath, (max_mtime, max_mtime))

    def _render_rendertile(self, tile):
        """Renders the given render-tile.

        This function is called from the public do_work() method in the child
        process. The tile is assumed to need rendering and is rendered
        unconditionally.

        The argument is a RenderTile object

        The image is rendered and saved to disk in the place this tileset is
        configured to save images.

        """

        imgpath = tile.get_filepath(self.outputdir, self.imgextension)

        # Calculate which chunks are relevant to this tile
        # This is a list of (col, row, chunkx, chunkz, chunk_mtime)
        chunks = list(get_chunks_by_tile(tile, self.regionset))

        if not chunks:
            # No chunks were found in this tile
            logging.warning("%s was requested for render, but no chunks found! This may be a bug", tile)
            try:
                os.unlink(imgpath)
            except OSError, e:
                # ignore only if the error was "file not found"
                if e.errno != errno.ENOENT:
                    raise
            else:
                logging.debug("%s deleted", tile)
            return

        # Create the directory if not exists
        dirdest = os.path.dirname(imgpath)
        if not os.path.exists(dirdest):
            try:
                os.makedirs(dirdest)
            except OSError, e:
                # Ignore errno EEXIST: file exists. Due to a race condition,
                # two processes could conceivably try and create the same
                # directory at the same time
                if e.errno != errno.EEXIST:
                    raise

        #logging.debug("writing out worldtile {0}".format(imgpath))

        # Compile this image
        tileimg = Image.new("RGBA", (384, 384), self.options['bgcolor'])

        colstart = tile.col
        rowstart = tile.row
        # col colstart will get drawn on the image starting at x coordinates -(384/2)
        # row rowstart will get drawn on the image starting at y coordinates -(192/2)
        max_chunk_mtime = 0
        for col, row, chunkx, chunky, chunkz, chunk_mtime in chunks:
            xpos = -192 + (col-colstart)*192
            ypos = -96 + (row-rowstart)*96 + (16-1 - chunky)*192

            if chunk_mtime > max_chunk_mtime:
                max_chunk_mtime = chunk_mtime

            # draw the chunk!
            try:
                c_overviewer.render_loop(self.world, self.regionset, chunkx, chunky,
                        chunkz, tileimg, xpos, ypos,
                        self.options['rendermode'], self.textures)
            except nbt.CorruptionError:
                # A warning and traceback was already printed by world.py's
                # get_chunk()
                logging.debug("Skipping the render of corrupt chunk at %s,%s and moving on.", chunkx, chunkz)
            except Exception, e:
                logging.error("Could not render chunk %s,%s for some reason. This is likely a render primitive option error.", chunkx, chunkz)
                logging.error("Full error was:", exc_info=1)
                sys.exit(1)

            ## Semi-handy routine for debugging the drawing routine
            ## Draw the outline of the top of the chunk
            #import ImageDraw
            #draw = ImageDraw.Draw(tileimg)
            ## Draw top outline
            #draw.line([(192,0), (384,96)], fill='red')
            #draw.line([(192,0), (0,96)], fill='red')
            #draw.line([(0,96), (192,192)], fill='red')
            #draw.line([(384,96), (192,192)], fill='red')
            ## Draw side outline
            #draw.line([(0,96),(0,96+192)], fill='red')
            #draw.line([(384,96),(384,96+192)], fill='red')
            ## Which chunk this is:
            #draw.text((96,48), "C: %s,%s" % (chunkx, chunkz), fill='red')
            #draw.text((96,96), "c,r: %s,%s" % (col, row), fill='red')

        # Save them
        with FileReplacer(imgpath, capabilities=self.fs_caps) as tmppath:
            if self.imgextension == 'jpg':
                tileimg.save(tmppath, "jpeg", quality=self.options['imgquality'], subsampling=0)
            else: # png
                tileimg.save(tmppath, "png")

            if self.options['optimizeimg']:
                optimize_image(tmppath, self.imgextension, self.options['optimizeimg'])
            
            os.utime(tmppath, (max_chunk_mtime, max_chunk_mtime))

    def _iterate_and_check_tiles(self, path):
        """A generator function over all tiles that should exist in the subtree
        identified by path. This yields, in order, all tiles that need
        rendering in a post-traversal order, including this node itself.

        This method takes one parameter:

        path
            The path of a tile that should exist


        This method yields tuples in this form:
            (path, mtime, needs_rendering)
        path
            is the path tuple of the tile that needs rendering
        mtime
            if the tile does not need rendering, the parent call determines if
            it should render itself by comparing its own mtime to the child
            mtimes. This should be set to the tile's mtime in the event that
            the tile does not need rendering, or None otherwise.
        needs_rendering
            is a boolean indicating this tile does in fact need rendering.

        (Since this is a recursive generator, tiles that don't need rendering
        are not propagated all the way out of the recursive stack, but are
        still yielded to the immediate parent because it needs to know its
        childs' mtimes)

        """
        if len(path) == self.treedepth:
            # Base case: a render-tile.
            # Render this tile if any of its chunks are greater than its mtime
            tileobj = RenderTile.from_path(path)
            imgpath = tileobj.get_filepath(self.outputdir, self.imgextension)
            try:
                tile_mtime = os.stat(imgpath)[stat.ST_MTIME]
            except OSError, e:
                if e.errno != errno.ENOENT:
                    raise
                tile_mtime = 0
            
            try:
                max_chunk_mtime = max(c[5] for c in get_chunks_by_tile(tileobj, self.regionset))
            except ValueError:
                # max got an empty sequence! something went horribly wrong
                logging.warning("tile %s expected contains no chunks! this may be a bug", path)
                max_chunk_mtime = 0

            if tile_mtime > 120 + max_chunk_mtime:
                # If a tile has been modified more recently than any of its
                # chunks, then this could indicate a potential issue with
                # this or future renders.
                logging.warning(
                        "I found a tile with a more recent modification time "
                        "than any of its chunks. This can happen when a tile has "
                        "been modified with an outside program, or by a copy "
                        "utility that doesn't preserve mtimes. Overviewer uses "
                        "the filesystem's mtimes to determine which tiles need "
                        "rendering and which don't, so it's important to "
                        "preserve the mtimes Overviewer sets. Please see our FAQ "
                        "page on docs.overviewer.org or ask us in IRC for more "
                        "information")
                logging.warning("Tile was: %s", imgpath)

            if max_chunk_mtime > tile_mtime or tile_mtime < self.forcerendertime:
                # chunks have a more recent mtime than the tile or the tile has
                # an older mtime than the forcerendertime from an interrupted
                # render. Render the tile.
                yield (path, None, True)
            else:
                # This doesn't need rendering. Return mtime to parent in case
                # its mtime is less, indicating the parent DOES need a render
                yield path, max_chunk_mtime, False

        else:
            # A composite-tile.
            render_me = False
            max_child_mtime = 0

            # First, recurse to each of our children
            for childnum in xrange(4):
                childpath = path + (childnum,)

                # Check if this sub-tree should actually exist, so that we only
                # end up checking tiles that actually exist
                if not self.dirtytree.query_path(childpath):
                    # Here check if it *does* exist, and if so, nuke it.
                    self._nuke_path(childpath)
                    continue

                for child_path, child_mtime, child_needs_rendering in \
                        self._iterate_and_check_tiles(childpath):
                    if len(child_path) == len(path)+1:
                        # Do these checks for our immediate children
                        if child_needs_rendering:
                            render_me = True
                        elif child_mtime > max_child_mtime:
                            max_child_mtime = child_mtime

                    # Pass this on up and out.
                    # Optimization: if it does not need rendering, we don't
                    # need to pass it any further. A tile that doesn't need
                    # rendering is only relevant to its immediate parent, and
                    # only for its mtime information.
                    if child_needs_rendering:
                        yield child_path, child_mtime, child_needs_rendering

            # Now that we're done with our children and descendents, see if
            # this tile needs rendering
            if render_me:
                # yes. yes we do. This is set when one of our children needs
                # rendering
                yield path, None, True
            else:
                # Check this tile's mtime
                imgpath = os.path.join(self.outputdir, *(str(x) for x in path))
                imgpath += "." + self.imgextension
                logging.debug("Testing mtime for composite-tile %s", imgpath)
                try:
                    tile_mtime = os.stat(imgpath)[stat.ST_MTIME]
                except OSError, e:
                    if e.errno != errno.ENOENT:
                        raise
                    tile_mtime = 0

                if tile_mtime < max_child_mtime:
                    # If any child was updated more recently than ourself, then
                    # we need rendering
                    yield path, None, True
                else:
                    # Nope.
                    yield path, max_child_mtime, False

    def _nuke_path(self, path):
        """Given a quadtree path, erase it from disk. This is called by
        _iterate_and_check_tiles() as a helper-method.

        """
        if len(path) == self.treedepth:
            # path referrs to a single tile
            tileobj = RenderTile.from_path(path)
            imgpath = tileobj.get_filepath(self.outputdir, self.imgextension)
            if os.path.exists(imgpath):
                # No need to catch ENOENT since this is only called from the
                # master process
                logging.debug("Found an image that shouldn't exist. Deleting it: %s", imgpath)
                os.remove(imgpath)
        else:
            # path referrs to a composite tile, and by extension a directory
            dirpath = os.path.join(self.outputdir, *(str(x) for x in path))
            imgpath = dirpath + "." + self.imgextension
            if os.path.exists(imgpath):
                logging.debug("Found an image that shouldn't exist. Deleting it: %s", imgpath)
                os.remove(imgpath)
            if os.path.exists(dirpath):
                logging.debug("Found a subtree that shouldn't exist. Deleting it: %s", dirpath)
                shutil.rmtree(dirpath)

##
## Functions for converting (x, z) to (col, row) and back
##

def convert_coords(chunkx, chunkz):
    """Takes a coordinate (chunkx, chunkz) where chunkx and chunkz are
    in the chunk coordinate system, and figures out the row and column
    in the image each one should be. Returns (col, row)."""

    # columns are determined by the sum of the chunk coords, rows are the
    # difference
    # change this function, and you MUST change unconvert_coords
    return (chunkx + chunkz, chunkz - chunkx)

def unconvert_coords(col, row):
    """Undoes what convert_coords does. Returns (chunkx, chunkz)."""

    # col + row = chunkz + chunkz => (col + row)/2 = chunkz
    # col - row = chunkx + chunkx => (col - row)/2 = chunkx
    return ((col - row) / 2, (col + row) / 2)

######################
# The following two functions define the mapping from chunks to tiles and back.
# The mapping from chunks to tiles (get_tiles_by_chunk()) is used during the
# chunk scan to determine which tiles need updating, while the mapping from a
# tile to chunks (get_chunks_by_tile()) is used by the tile rendering routines
# to get which chunks are needed.
def get_tiles_by_chunk(chunkcol, chunkrow):
    """For the given chunk, returns an iterator over Render Tiles that this
    chunk touches.  Iterates over (tilecol, tilerow)

    """
    # find tile coordinates. Remember tiles are identified by the
    # address of the chunk in their upper left corner.
    tilecol = chunkcol - chunkcol % 2
    tilerow = chunkrow - chunkrow % 4

    # If this chunk is in an /even/ column, then it spans two tiles.
    if chunkcol % 2 == 0:
        colrange = (tilecol-2, tilecol)
    else:
        colrange = (tilecol,)

    # If this chunk is in a row divisible by 4, then it touches the
    # tile above it as well. Also touches the next 4 tiles down (16
    # rows)
    if chunkrow % 4 == 0:
        rowrange = xrange(tilerow-4, tilerow+32+1, 4)
    else:
        rowrange = xrange(tilerow, tilerow+32+1, 4)

    return product(colrange, rowrange)

def get_chunks_by_tile(tile, regionset):
    """Get chunk sections that are relevant to the given render-tile. Only
    returns chunk sections that are in chunks that actually exist according to
    the given regionset object. (Does not check to see if the chunk section
    itself within the chunk exists)

    This function is expected to return the chunk sections in the correct order
    for rendering, i.e. back to front.

    Returns an iterator over chunks tuples where each item is
    (col, row, chunkx, chunky, chunkz, mtime)
    """

    # This is not a documented usage of this function and is used only for
    # debugging
    if regionset is None:
        get_mtime = lambda x,y: True
    else:
        get_mtime = regionset.get_chunk_mtime

    # Each tile has two even columns and an odd column of chunks.

    # First do the odd. For each chunk in the tile's odd column the tile
    # "passes through" three chunk sections.
    oddcol_sections = []
    for i, y in enumerate(reversed(xrange(16))):
        for row in xrange(tile.row + 3 - i*2, tile.row - 2 - i*2, -2):
            oddcol_sections.append((tile.col+1, row, y))

    evencol_sections = []
    for i, y in enumerate(reversed(xrange(16))):
        for row in xrange(tile.row + 4 - i*2, tile.row - 3 - i*2, -2):
            evencol_sections.append((tile.col+2, row, y))
            evencol_sections.append((tile.col, row, y))

    eveniter = reversed(evencol_sections)
    odditer = reversed(oddcol_sections)

    # There are 4 rows of chunk sections per Y value on even columns, but 3
    # rows on odd columns. This iteration order yields them in back-to-front
    # order appropriate for rendering
    for col, row, y in roundrobin((
            eveniter,eveniter,
            odditer,
            eveniter,eveniter,
            odditer,
            eveniter,eveniter,
            odditer,
            eveniter,eveniter,
            )):
        chunkx, chunkz = unconvert_coords(col, row)
        mtime = get_mtime(chunkx, chunkz)
        if mtime:
            yield (col, row, chunkx, y, chunkz, mtime)

class RendertileSet(object):
    """This object holds a set of render-tiles using a quadtree data structure.
    It is typically used to hold tiles that need rendering. This implementation
    collapses subtrees that are completely in or out of the set to save memory.

    An instance of this class holds a full tree.

    The instance knows its "level", which corresponds to the zoom level where 1
    is the inner-most (most zoomed in) tiles.

    Instances hold the state of their children (in or out of the set). Leaf
    nodes are images and do not physically exist in the tree as objects, but
    are represented as booleans held by the objects at the second-to-last
    level; level 1 nodes keep track of leaf image state. Level 2 nodes keep
    track of level 1 state, and so forth.

    """
    __slots__ = ("depth", "children", "num_tiles", "num_tiles_all")
    def __init__(self, depth):
        """Initialize a new tree with the specified depth. This actually
        initializes a node, which is the root of a subtree, with `depth` levels
        beneath it.

        """
        # Stores the depth of the tree according to this node. This is not the
        # depth of this node, but rather the number of levels below this node
        # (including this node).
        self.depth = depth

        # the self.children array holds the 4 children of this node. This
        # follows the same quadtree convention as elsewhere: children 0, 1, 2,
        # 3 are the upper-left, upper-right, lower-left, and lower-right
        # respectively
        # Values are:
        # False
        #   All children down this subtree are not in the set
        # True
        #   All children down this subtree are in the set
        # An array of the same format
        #   The array defines which children down that subtree are in the set
        # A node with depth=1 cannot have a RendertileSet instance in its
        # children since its children are leaves, representing images, not more
        # tree
        self.children = [False] * 4

        self.num_tiles     = 0
        self.num_tiles_all = 0

    def add(self, path):
        """Marks the requested leaf node as in this set

        Path is an iterable of integers representing the path to the leaf node
        that is to be added to the set

        """
        path = list(path)
        assert len(path) == self.depth

        if self.num_tiles == 0:
            # The first child is being added. A root composite tile will be
            # rendered.
            self.num_tiles_all += 1

        self._add_helper(self.children, list(reversed(path)))

    def _add_helper(self, children, path):
        """Recursive helper for add()
        """

        childnum = path.pop()

        if path:
            # We are not at the leaf, recurse.

            if children[childnum] == True:
                # The child is already in the tree.
                return
            elif children[childnum] == False:
                # Expand all-false.
                children[childnum] = [False]*4

                # This also means an additional composite tile.
                self.num_tiles_all += 1

            self._add_helper(children[childnum], path)

            if children[childnum] == [True]*4:
                # Collapse all-true.
                children[childnum] = True

        else:
            # We are at the leaf.
            if not children[childnum]:
                self.num_tiles     += 1
                self.num_tiles_all += 1

            children[childnum] = True

    def __iter__(self):
        return self.iterate()

    def iterate(self, level=None, robin=False, offset=(0,0)):
        """Returns an iterator over every tile in this set. Each item yielded
        is a sequence of integers representing the quadtree path to the tiles
        in the set. Yielded sequences are of length self.depth.

        If level is None, iterates over tiles of the highest level, i.e.
        worldtiles. If level is a value between 1 and the depth of this tree,
        this method iterates over tiles at that level. Zoom level 1 is zoomed
        all the way out, zoom level `depth` is all the way in.

        In other words, specifying level causes the tree to be iterated as if
        it was only that depth.

        If the `robin` parameter is True, recurses to the four top-level
        subtrees simultaneously in a round-robin manner.

        """
        if level is None:
            todepth = 1
        else:
            if not (level > 0 and level <= self.depth):
                raise ValueError("Level parameter must be between 1 and %s" % self.depth)
            todepth = self.depth - level + 1

        return (tuple(path) for path in self._iterate_helper([], self.children, self.depth, onlydepth=todepth, robin=robin, offset=offset))

    def posttraversal(self, robin=False, offset=(0,0)):
        """Returns an iterator over tile paths for every tile in the
        set, including the explictly marked render-tiles, as well as the
        implicitly marked ancestors of those render-tiles. Returns in
        post-traversal order, so that tiles with dependencies will always be
        yielded after their dependencies.

        If the `robin` parameter is True, recurses to the four top-level
        subtrees simultaneously in a round-robin manner.

        """
        return (tuple(path) for path in self._iterate_helper([], self.children, self.depth, robin=robin, offset=offset))

    def _iterate_helper(self, path, children, depth, onlydepth=None, robin=False, offset=(0,0)):
        """Returns an iterator over tile paths for every tile in the set."""

        # A variant of children with a collapsed False/True expanded to a list.
        children_list = [children] * 4 if isinstance(children, bool) else children

        targetdepth = 1 if onlydepth is None else onlydepth

        if depth == targetdepth:
            # Base case
            for (childnum, child), _ in distance_sort(enumerate(children_list), offset):
                if child:
                    yield path + [childnum]
        else:
            gens = []
            for (childnum_, child), childoffset_ in distance_sort(enumerate(children_list), offset):
                if child:
                    def go(childnum, childoffset):
                        for p in self._iterate_helper(path + [childnum], children_list[childnum], depth-1, onlydepth=onlydepth, offset=childoffset):
                            yield p
                    gens.append(go(childnum_, childoffset_))

            for p in roundrobin(gens) if robin else chain(*gens):
                yield p

        if onlydepth is None and any(children_list):
            yield path

    def query_path(self, path):
        """Queries for the state of the given tile in the tree.

        Returns True for items in the set, False otherwise. Works for
        rendertiles as well as upper tiles (which are True if they have a
        descendent that is in the set)

        """
        # Traverse the tree down the given path. If the tree has been
        # collapsed, then just return the stored boolean. Otherwise, if we find
        # the specific tree node requested, return its state using the
        # __nonzero__ call.
        treenode = self.children
        for pathelement in path:
            treenode = treenode[pathelement]
            if isinstance(treenode, bool):
                return treenode

        # If the method has not returned at this point, treenode is the
        # requested node, but it is an inner node. That will only happen if one
        # or more of the children down the tree are True.
        return True

    def __nonzero__(self):
        """Returns the boolean context of this particular node. If any
        descendent of this node is True return True. Otherwise, False.

        """
        # Any children that are True or are a list evaluate to True.
        return any(self.children)

    def count(self):
        """Returns the total number of render-tiles in this set.

        """
        # XXX There seems to be something wrong with the num_tiles calculation.
        # Calculate the number of tiles by iteration and emit a warning if it
        # does not match.
        from itertools import imap
        num = sum(imap(lambda _: 1, self.iterate()))
        if num != self.num_tiles:
            logging.error("Please report this to the developers: RendertileSet num_tiles=%r, count=%r, children=%r", self.num_tiles, num, self.children)
        return num

    def count_all(self):
        """Returns the total number of render-tiles plus implicitly marked
        upper-tiles in this set

        """
        # XXX There seems to be something wrong with the num_tiles calculation.
        # Calculate the number of tiles by iteration and emit a warning if it
        # does not match.
        from itertools import imap
        num = sum(imap(lambda _: 1, self.posttraversal()))
        if num != self.num_tiles_all:
            logging.error("Please report this to the developers: RendertileSet num_tiles_all=%r, count_all=%r, children=%r", self.num_tiles, num, self.children)
        return num

def distance_sort(children, (off_x, off_y)):
    order = []
    for child, (dx, dy) in izip(children, [(-1,-1), (1,-1), (-1,1), (1,1)]):
        x = off_x*2 + dx
        y = off_y*2 + dy
        order.append((child, (x,y)))

    return sorted(order, key=lambda (_, (x,y)): x*x + y*y)

class RenderTile(object):
    """A simple container class that represents a single render-tile.

    A render-tile is a tile that is rendered, not a tile composed of other
    tiles (composite-tile).

    """
    __slots__ = ("col", "row", "path")
    def __init__(self, col, row, path):
        """Initialize the tile obj with the given parameters. It's probably
        better to use one of the other constructors though

        """
        self.col = col
        self.row = row
        self.path = tuple(path)

    def __repr__(self):
        return "%s(%r,%r,%r)" % (self.__class__.__name__, self.col, self.row, self.path)

    def __eq__(self,other):
        return self.col == other.col and self.row == other.row and tuple(self.path) == tuple(other.path)

    def __ne__(self, other):
        return not self == other

    # To support pickling
    def __getstate__(self):
        return self.col, self.row, self.path
    def __setstate__(self, state):
        self.__init__(*state)

    def get_filepath(self, tiledir, imgformat):
        """Returns the path to this file given the directory to the tiles

        """
        # os.path.join would be the proper way to do this path concatenation,
        # but it is surprisingly slow, probably because it checks each path
        # element if it begins with a slash. Since we know these components are
        # all relative, just concatinate with os.path.sep
        pathcomponents = [tiledir]
        pathcomponents.extend(str(x) for x in self.path)
        path = os.path.sep.join(pathcomponents)
        imgpath = ".".join((path, imgformat))
        return imgpath


    @classmethod
    def from_path(cls, path):
        """Constructor that takes a path and computes the col,row address of
        the tile and constructs a new tile object.

        """
        path = tuple(path)

        depth = len(path)

        # Radius of the world in chunk cols/rows
        # (Diameter in X is 2**depth, divided by 2 for a radius, multiplied by
        # 2 for 2 chunks per tile. Similarly for Y)
        xradius = 2**depth
        yradius = 2*2**depth

        col = -xradius
        row = -yradius
        xsize = xradius
        ysize = yradius

        for p in path:
            if p in (1,3):
                col += xsize
            if p in (2,3):
                row += ysize
            xsize //= 2
            ysize //= 2

        return cls(col, row, path)

    @classmethod
    def compute_path(cls, col, row, depth):
        """Constructor that takes a col,row of a tile and computes the path.

        """
        assert col % 2 == 0
        assert row % 4 == 0

        xradius = 2**depth
        yradius = 2*2**depth

        colbounds = [-xradius, xradius]
        rowbounds = [-yradius, yradius]

        path = []

        for level in xrange(depth):
            # Strategy: Find the midpoint of this level, and determine which
            # quadrant this row/col is in. Then set the bounds to that level
            # and repeat

            xmid = (colbounds[1] + colbounds[0]) // 2
            ymid = (rowbounds[1] + rowbounds[0]) // 2

            if col < xmid:
                if row < ymid:
                    path.append(0)
                    colbounds[1] = xmid
                    rowbounds[1] = ymid
                else:
                    path.append(2)
                    colbounds[1] = xmid
                    rowbounds[0] = ymid
            else:
                if row < ymid:
                    path.append(1)
                    colbounds[0] = xmid
                    rowbounds[1] = ymid
                else:
                    path.append(3)
                    colbounds[0] = xmid
                    rowbounds[0] = ymid

        return cls(col, row, path)

########NEW FILE########
__FILENAME__ = util
#    This file is part of the Minecraft Overviewer.
#
#    Minecraft Overviewer is free software: you can redistribute it and/or
#    modify it under the terms of the GNU General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or (at
#    your option) any later version.
#
#    Minecraft Overviewer is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General
#    Public License for more details.
#
#    You should have received a copy of the GNU General Public License along
#    with the Overviewer.  If not, see <http://www.gnu.org/licenses/>.

"""
Misc utility routines used by multiple files that don't belong anywhere else
"""

import imp
import os.path
import sys
import platform
from string import hexdigits
from subprocess import Popen, PIPE
from itertools import cycle, islice, product
import errno
def get_program_path():
    if hasattr(sys, "frozen") or imp.is_frozen("__main__"):
        return os.path.dirname(sys.executable)
    else:
        try:
            # normally, we're in ./overviewer_core/util.py
            # we want ./
            return os.path.dirname(os.path.dirname(__file__))
        except NameError:
            return os.path.dirname(sys.argv[0])

def findGitHash():
    try:
        p = Popen('git rev-parse HEAD', stdout=PIPE, stderr=PIPE, shell=True)
        p.stderr.close()
        line = p.stdout.readlines()[0].strip()
        if line and len(line) == 40 and all(c in hexdigits for c in line):
            return line
    except Exception:
        try:
            import overviewer_version
            return overviewer_version.HASH
        except Exception:
            return "unknown"

def findGitVersion():
    try:
        p = Popen('git describe --tags --match "v*.*.*"', stdout=PIPE, stderr=PIPE, shell=True)
        p.stderr.close()
        line = p.stdout.readlines()[0]
        if line.startswith('release-'):
            line = line.split('-', 1)[1]
        if line.startswith('v'):
            line = line[1:]
        # turn 0.1.0-50-somehash into 0.1.50
        # and 0.1.0 into 0.1.0
        line = line.strip().replace('-', '.').split('.')
        if len(line) == 5:
            del line[4]
            del line[2]
        else:
            assert len(line) == 3
            line[2] = '0'
        line = '.'.join(line)
        return line
    except Exception:
        try:
            import overviewer_version
            return overviewer_version.VERSION
        except Exception:
            return "unknown"

def is_bare_console():
    """Returns true if Overviewer is running in a bare console in
    Windows, that is, if overviewer wasn't started in a cmd.exe
    session.
    """
    if platform.system() == 'Windows':
        try:
            import ctypes
            GetConsoleProcessList = ctypes.windll.kernel32.GetConsoleProcessList
            num = GetConsoleProcessList(ctypes.byref(ctypes.c_int(0)), ctypes.c_int(1))
            if (num == 1):
                return True
                
        except Exception:
            pass
    return False

def nice_exit(ret=0):
    """Drop-in replacement for sys.exit that will automatically detect
    bare consoles and wait for user input before closing.
    """
    if ret and is_bare_console():
        print
        print "Press [Enter] to close this window."
        raw_input()
    sys.exit(ret)

# http://docs.python.org/library/itertools.html
def roundrobin(iterables):
    "roundrobin('ABC', 'D', 'EF') --> A D E B F C"
    # Recipe credited to George Sakkis
    pending = len(iterables)
    nexts = cycle(iter(it).next for it in iterables)
    while pending:
        try:
            for next in nexts:
                yield next()
        except StopIteration:
            pending -= 1
            nexts = cycle(islice(nexts, pending))

def dict_subset(d, keys):
    "Return a new dictionary that is built from copying select keys from d"
    n = dict()
    for key in keys:
        if key in d:
            n[key] = d[key]
    return n

## (from http://code.activestate.com/recipes/576693/ [r9])
# Backport of OrderedDict() class that runs on Python 2.4, 2.5, 2.6, 2.7 and pypy.
# Passes Python2.7's test suite and incorporates all the latest updates.

try:
    from thread import get_ident as _get_ident
except ImportError:
    from dummy_thread import get_ident as _get_ident

try:
    from _abcoll import KeysView, ValuesView, ItemsView
except ImportError:
    pass

class OrderedDict(dict):
    'Dictionary that remembers insertion order'
    # An inherited dict maps keys to values.
    # The inherited dict provides __getitem__, __len__, __contains__, and get.
    # The remaining methods are order-aware.
    # Big-O running times for all methods are the same as for regular dictionaries.

    # The internal self.__map dictionary maps keys to links in a doubly linked list.
    # The circular doubly linked list starts and ends with a sentinel element.
    # The sentinel element never gets deleted (this simplifies the algorithm).
    # Each link is stored as a list of length three:  [PREV, NEXT, KEY].

    def __init__(self, *args, **kwds):
        '''Initialize an ordered dictionary.  Signature is the same as for
        regular dictionaries, but keyword arguments are not recommended
        because their insertion order is arbitrary.

        '''
        if len(args) > 1:
            raise TypeError('expected at most 1 arguments, got %d' % len(args))
        try:
            self.__root
        except AttributeError:
            self.__root = root = []                     # sentinel node
            root[:] = [root, root, None]
            self.__map = {}
        self.__update(*args, **kwds)

    def __setitem__(self, key, value, dict_setitem=dict.__setitem__):
        'od.__setitem__(i, y) <==> od[i]=y'
        # Setting a new item creates a new link which goes at the end of the linked
        # list, and the inherited dictionary is updated with the new key/value pair.
        if key not in self:
            root = self.__root
            last = root[0]
            last[1] = root[0] = self.__map[key] = [last, root, key]
        dict_setitem(self, key, value)

    def __delitem__(self, key, dict_delitem=dict.__delitem__):
        'od.__delitem__(y) <==> del od[y]'
        # Deleting an existing item uses self.__map to find the link which is
        # then removed by updating the links in the predecessor and successor nodes.
        dict_delitem(self, key)
        link_prev, link_next, key = self.__map.pop(key)
        link_prev[1] = link_next
        link_next[0] = link_prev

    def __iter__(self):
        'od.__iter__() <==> iter(od)'
        root = self.__root
        curr = root[1]
        while curr is not root:
            yield curr[2]
            curr = curr[1]

    def __reversed__(self):
        'od.__reversed__() <==> reversed(od)'
        root = self.__root
        curr = root[0]
        while curr is not root:
            yield curr[2]
            curr = curr[0]

    def clear(self):
        'od.clear() -> None.  Remove all items from od.'
        try:
            for node in self.__map.itervalues():
                del node[:]
            root = self.__root
            root[:] = [root, root, None]
            self.__map.clear()
        except AttributeError:
            pass
        dict.clear(self)

    def popitem(self, last=True):
        '''od.popitem() -> (k, v), return and remove a (key, value) pair.
        Pairs are returned in LIFO order if last is true or FIFO order if false.

        '''
        if not self:
            raise KeyError('dictionary is empty')
        root = self.__root
        if last:
            link = root[0]
            link_prev = link[0]
            link_prev[1] = root
            root[0] = link_prev
        else:
            link = root[1]
            link_next = link[1]
            root[1] = link_next
            link_next[0] = root
        key = link[2]
        del self.__map[key]
        value = dict.pop(self, key)
        return key, value

    # -- the following methods do not depend on the internal structure --

    def keys(self):
        'od.keys() -> list of keys in od'
        return list(self)

    def values(self):
        'od.values() -> list of values in od'
        return [self[key] for key in self]

    def items(self):
        'od.items() -> list of (key, value) pairs in od'
        return [(key, self[key]) for key in self]

    def iterkeys(self):
        'od.iterkeys() -> an iterator over the keys in od'
        return iter(self)

    def itervalues(self):
        'od.itervalues -> an iterator over the values in od'
        for k in self:
            yield self[k]

    def iteritems(self):
        'od.iteritems -> an iterator over the (key, value) items in od'
        for k in self:
            yield (k, self[k])

    def update(*args, **kwds):
        '''od.update(E, **F) -> None.  Update od from dict/iterable E and F.

        If E is a dict instance, does:           for k in E: od[k] = E[k]
        If E has a .keys() method, does:         for k in E.keys(): od[k] = E[k]
        Or if E is an iterable of items, does:   for k, v in E: od[k] = v
        In either case, this is followed by:     for k, v in F.items(): od[k] = v

        '''
        if len(args) > 2:
            raise TypeError('update() takes at most 2 positional '
                            'arguments (%d given)' % (len(args),))
        elif not args:
            raise TypeError('update() takes at least 1 argument (0 given)')
        self = args[0]
        # Make progressively weaker assumptions about "other"
        other = ()
        if len(args) == 2:
            other = args[1]
        if isinstance(other, dict):
            for key in other:
                self[key] = other[key]
        elif hasattr(other, 'keys'):
            for key in other.keys():
                self[key] = other[key]
        else:
            for key, value in other:
                self[key] = value
        for key, value in kwds.items():
            self[key] = value

    __update = update  # let subclasses override update without breaking __init__

    __marker = object()

    def pop(self, key, default=__marker):
        '''od.pop(k[,d]) -> v, remove specified key and return the corresponding value.
        If key is not found, d is returned if given, otherwise KeyError is raised.

        '''
        if key in self:
            result = self[key]
            del self[key]
            return result
        if default is self.__marker:
            raise KeyError(key)
        return default

    def setdefault(self, key, default=None):
        'od.setdefault(k[,d]) -> od.get(k,d), also set od[k]=d if k not in od'
        if key in self:
            return self[key]
        self[key] = default
        return default

    def __repr__(self, _repr_running={}):
        'od.__repr__() <==> repr(od)'
        call_key = id(self), _get_ident()
        if call_key in _repr_running:
            return '...'
        _repr_running[call_key] = 1
        try:
            if not self:
                return '%s()' % (self.__class__.__name__,)
            return '%s(%r)' % (self.__class__.__name__, self.items())
        finally:
            del _repr_running[call_key]

    def __reduce__(self):
        'Return state information for pickling'
        items = [[k, self[k]] for k in self]
        inst_dict = vars(self).copy()
        for k in vars(OrderedDict()):
            inst_dict.pop(k, None)
        if inst_dict:
            return (self.__class__, (items,), inst_dict)
        return self.__class__, (items,)

    def copy(self):
        'od.copy() -> a shallow copy of od'
        return self.__class__(self)

    @classmethod
    def fromkeys(cls, iterable, value=None):
        '''OD.fromkeys(S[, v]) -> New ordered dictionary with keys from S
        and values equal to v (which defaults to None).

        '''
        d = cls()
        for key in iterable:
            d[key] = value
        return d

    def __eq__(self, other):
        '''od.__eq__(y) <==> od==y.  Comparison to another OD is order-sensitive
        while comparison to a regular mapping is order-insensitive.

        '''
        if isinstance(other, OrderedDict):
            return len(self)==len(other) and self.items() == other.items()
        return dict.__eq__(self, other)

    def __ne__(self, other):
        return not self == other

    # -- the following methods are only used in Python 2.7 --

    def viewkeys(self):
        "od.viewkeys() -> a set-like object providing a view on od's keys"
        return KeysView(self)

    def viewvalues(self):
        "od.viewvalues() -> an object providing a view on od's values"
        return ValuesView(self)

    def viewitems(self):
        "od.viewitems() -> a set-like object providing a view on od's items"
        return ItemsView(self)

# now replace all that with the official version, if available
try:
    import collections
    OrderedDict = collections.OrderedDict
except (ImportError, AttributeError):
    pass

def pid_exists(pid): # http://stackoverflow.com/a/6940314/1318435
    """Check whether pid exists in the current process table."""
    if pid < 0:
        return False
    try:
        os.kill(pid, 0)
    except OSError, e:
        return e.errno != errno.ESRCH
    else:
        return True
########NEW FILE########
__FILENAME__ = world
#    This file is part of the Minecraft Overviewer.
#
#    Minecraft Overviewer is free software: you can redistribute it and/or
#    modify it under the terms of the GNU General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or (at
#    your option) any later version.
#
#    Minecraft Overviewer is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General
#    Public License for more details.
#
#    You should have received a copy of the GNU General Public License along
#    with the Overviewer.  If not, see <http://www.gnu.org/licenses/>.

import functools
import os
import os.path
import logging
import hashlib
import time
import random
import re
import locale

import numpy

from . import nbt
from . import cache

"""
This module has routines for extracting information about available worlds

"""

class ChunkDoesntExist(Exception):
    pass

def log_other_exceptions(func):
    """A decorator that prints out any errors that are not
    ChunkDoesntExist errors. This should decorate any functions or
    methods called by the C code, such as get_chunk(), because the C
    code is likely to swallow exceptions. This will at least make them
    visible.
    """
    functools.wraps(func)
    def newfunc(*args):
        try:
            return func(*args)
        except ChunkDoesntExist:
            raise
        except Exception, e:
            logging.exception("%s raised this exception", func.func_name)
            raise
    return newfunc


class World(object):
    """Encapsulates the concept of a Minecraft "world". A Minecraft world is a
    level.dat file, a players directory with info about each player, a data
    directory with info about that world's maps, and one or more "dimension"
    directories containing a set of region files with the actual world data.

    This class deals with reading all the metadata about the world.  Reading
    the actual world data for each dimension from the region files is handled
    by a RegionSet object.

    Note that vanilla Minecraft servers and single player games have a single
    world with multiple dimensions: one for the overworld, the nether, etc.

    On Bukkit enabled servers, to support "multiworld," the server creates
    multiple Worlds, each with a single dimension.

    In this file, the World objects act as an interface for RegionSet objects.
    The RegionSet objects are what's really important and are used for reading
    block data for rendering.  A RegionSet object will always correspond to a
    set of region files, or what is colloquially referred to as a "world," or
    more accurately as a dimension.

    The only thing this class actually stores is a list of RegionSet objects
    and the parsed level.dat data

    """
    
    def __init__(self, worlddir):
        self.worlddir = worlddir

        # This list, populated below, will hold RegionSet files that are in
        # this world
        self.regionsets = []
       
        # The level.dat file defines a minecraft world, so assert that this
        # object corresponds to a world on disk
        if not os.path.exists(os.path.join(self.worlddir, "level.dat")):
            raise ValueError("level.dat not found in %s" % self.worlddir)

        data = nbt.load(os.path.join(self.worlddir, "level.dat"))[1]['Data']
        # it seems that reading a level.dat file is unstable, particularly with respect
        # to the spawnX,Y,Z variables.  So we'll try a few times to get a good reading
        # empirically, it seems that 0,50,0 is a "bad" reading
        # update: 0,50,0 is the default spawn, and may be valid is some cases
        # more info is needed
        data = nbt.load(os.path.join(self.worlddir, "level.dat"))[1]['Data']
            

        # Hard-code this to only work with format version 19133, "Anvil"
        if not ('version' in data and data['version'] == 19133):
            logging.critical("Sorry, This version of Minecraft-Overviewer only works with the 'Anvil' chunk format")
            raise ValueError("World at %s is not compatible with Overviewer" % self.worlddir)

        # This isn't much data, around 15 keys and values for vanilla worlds.
        self.leveldat = data


        # Scan worlddir to try to identify all region sets. Since different
        # server mods like to arrange regions differently and there does not
        # seem to be any set standard on what dimensions are in each world,
        # just scan the directory heirarchy to find a directory with .mca
        # files.
        for root, dirs, files in os.walk(self.worlddir, followlinks=True):
            # any .mcr files in this directory?
            mcas = [x for x in files if x.endswith(".mca")]
            if mcas:
                # construct a regionset object for this
                rel = os.path.relpath(root, self.worlddir)
                rset = RegionSet(root, rel)
                if root == os.path.join(self.worlddir, "region"):
                    self.regionsets.insert(0, rset)
                else:
                    self.regionsets.append(rset)
        
        # TODO move a lot of the following code into the RegionSet


        try:
            # level.dat should have the LevelName attribute so we'll use that
            self.name = data['LevelName']
        except KeyError:
            # but very old ones might not? so we'll just go with the world dir name if they don't
            self.name = os.path.basename(os.path.realpath(self.worlddir))
        
        try:
            # level.dat also has a RandomSeed attribute
            self.seed = data['RandomSeed']
        except KeyError:
            self.seed = 0 # oh well
       
        # TODO figure out where to handle regionlists

    def get_regionsets(self):
        return self.regionsets
    def get_regionset(self, index):
        if type(index) == int:
            return self.regionsets[index]
        else: # assume a get_type() value
            candids = [x for x in self.regionsets if x.get_type() == index]
            logging.debug("You asked for %r, and I found the following candids: %r", index, candids)
            if len(candids) > 0:
                return candids[0]
            else: 
                return None


    def get_level_dat_data(self):
        # Return a copy
        return dict(self.data)
      
    def find_true_spawn(self):
        """Returns the spawn point for this world. Since there is one spawn
        point for a world across all dimensions (RegionSets), this method makes
        sense as a member of the World class.
        
        Returns (x, y, z)
        
        """
        # The spawn Y coordinate is almost always the default of 64.  Find the
        # first air block above the stored spawn location for the true spawn
        # location

        ## read spawn info from level.dat
        data = self.leveldat
        disp_spawnX = spawnX = data['SpawnX']
        spawnY = data['SpawnY']
        disp_spawnZ = spawnZ = data['SpawnZ']
   
        ## The chunk that holds the spawn location 
        chunkX = spawnX//16
        chunkZ = spawnZ//16
        
        ## clamp spawnY to a sane value, in-chunk value
        if spawnY < 0:
            spawnY = 0
        if spawnY > 255:
            spawnY = 255
        
        # Open up the chunk that the spawn is in
        regionset = self.get_regionset(None)
        if not regionset:
            return None
        try:
            chunk = regionset.get_chunk(chunkX, chunkZ)
        except ChunkDoesntExist:
            return (spawnX, spawnY, spawnZ)
    
        def getBlock(y):
            "This is stupid and slow but I don't care"
            targetSection = spawnY//16
            for section in chunk['Sections']:
                if section['Y'] == targetSection:
                    blockArray = section['Blocks']
                    return blockArray[inChunkX, inChunkZ, y % 16]
            return 0



        ## The block for spawn *within* the chunk
        inChunkX = spawnX - (chunkX*16)
        inChunkZ = spawnZ - (chunkZ*16)

        ## find the first air block
        while (getBlock(spawnY) != 0) and spawnY < 256:
            spawnY += 1

        return spawnX, spawnY, spawnZ

class RegionSet(object):
    """This object is the gateway to a particular Minecraft dimension within a
    world. It corresponds to a set of region files containing the actual
    world data. This object has methods for parsing and returning data from the
    chunks from its regions.

    See the docs for the World object for more information on the difference
    between Worlds and RegionSets.


    """

    def __init__(self, regiondir, rel):
        """Initialize a new RegionSet to access the region files in the given
        directory.

        regiondir is a path to a directory containing region files.
        
        rel is the relative path of this directory, with respect to the
        world directory.

        cachesize, if specified, is the number of chunks to keep parsed and
        in-memory.

        """
        self.regiondir = os.path.normpath(regiondir)
        self.rel = os.path.normpath(rel)
        logging.debug("regiondir is %r" % self.regiondir)
        logging.debug("rel is %r" % self.rel)
        
        # we want to get rid of /regions, if it exists
        if self.rel.endswith(os.path.normpath("/region")):
            self.type = self.rel[0:-len(os.path.normpath("/region"))]
        elif self.rel == "region":
            # this is the main world
            self.type = None
        else:
            logging.warning("Unkown region type in %r", regiondir)
            self.type = "__unknown"

        logging.debug("Scanning regions.  Type is %r" % self.type)
        
        # This is populated below. It is a mapping from (x,y) region coords to filename
        self.regionfiles = {}

        # This holds a cache of open regionfile objects
        self.regioncache = cache.LRUCache(size=16, destructor=lambda regionobj: regionobj.close())
        
        for x, y, regionfile in self._iterate_regionfiles():
            # regionfile is a pathname
            self.regionfiles[(x,y)] = (regionfile, os.path.getmtime(regionfile))

        self.empty_chunk = [None,None]
        logging.debug("Done scanning regions")

    # Re-initialize upon unpickling
    def __getstate__(self):
        return (self.regiondir, self.rel)
    def __setstate__(self, state):
        return self.__init__(*state)

    def __repr__(self):
        return "<RegionSet regiondir=%r>" % self.regiondir

    def get_type(self):
        """Attempts to return a string describing the dimension
        represented by this regionset.  Usually this is the relative
        path of the regionset within the world, minus the suffix
        /region, but for the main world it's None.
        """
        # path will be normalized in __init__
        return self.type

    def _get_regionobj(self, regionfilename):
        # Check the cache first. If it's not there, create the
        # nbt.MCRFileReader object, cache it, and return it
        # May raise an nbt.CorruptRegionError
        try:
            return self.regioncache[regionfilename]
        except KeyError:
            region = nbt.load_region(regionfilename)
            self.regioncache[regionfilename] = region
            return region
    
    #@log_other_exceptions
    def get_chunk(self, x, z):
        """Returns a dictionary object representing the "Level" NBT Compound
        structure for a chunk given its x, z coordinates. The coordinates given
        are chunk coordinates. Raises ChunkDoesntExist exception if the given
        chunk does not exist.

        The returned dictionary corresponds to the "Level" structure in the
        chunk file, with a few changes:

        * The Biomes array is transformed into a 16x16 numpy array

        * For each chunk section:

          * The "Blocks" byte string is transformed into a 16x16x16 numpy array
          * The Add array, if it exists, is bitshifted left 8 bits and
            added into the Blocks array
          * The "SkyLight" byte string is transformed into a 16x16x128 numpy
            array
          * The "BlockLight" byte string is transformed into a 16x16x128 numpy
            array
          * The "Data" byte string is transformed into a 16x16x128 numpy array

        Warning: the returned data may be cached and thus should not be
        modified, lest it affect the return values of future calls for the same
        chunk.
        """
        regionfile = self._get_region_path(x, z)
        if regionfile is None:
            raise ChunkDoesntExist("Chunk %s,%s doesn't exist (and neither does its region)" % (x,z))

        # Try a few times to load and parse this chunk before giving up and
        # raising an error
        tries = 5
        while True:
            try:
                region = self._get_regionobj(regionfile)
                data = region.load_chunk(x, z)
            except nbt.CorruptionError, e:
                tries -= 1
                if tries > 0:
                    # Flush the region cache to possibly read a new region file
                    # header
                    logging.debug("Encountered a corrupt chunk at %s,%s. Flushing cache and retrying", x, z)
                    #logging.debug("Error was:", exc_info=1)
                    del self.regioncache[regionfile]
                    time.sleep(0.5)
                    continue
                else:
                    if isinstance(e, nbt.CorruptRegionError):
                        logging.warning("Tried several times to read chunk %d,%d. Its region (%d,%d) may be corrupt. Giving up.",
                                x, z,x//32,z//32)
                    elif isinstance(e, nbt.CorruptChunkError):
                        logging.warning("Tried several times to read chunk %d,%d. It may be corrupt. Giving up.",
                                x, z)
                    else:
                        logging.warning("Tried several times to read chunk %d,%d. Unknown error. Giving up.",
                                x, z)
                    logging.debug("Full traceback:", exc_info=1)
                    # Let this exception propagate out through the C code into
                    # tileset.py, where it is caught and gracefully continues
                    # with the next chunk
                    raise
            else:
                # no exception raised: break out of the loop
                break


        if data is None:
            raise ChunkDoesntExist("Chunk %s,%s doesn't exist" % (x,z))

        level = data[1]['Level']
        chunk_data = level

        # Turn the Biomes array into a 16x16 numpy array
        try:
            biomes = numpy.frombuffer(chunk_data['Biomes'], dtype=numpy.uint8)
            biomes = biomes.reshape((16,16))
        except KeyError:
            # worlds converted by Jeb's program may be missing the Biomes key
            biomes = numpy.zeros((16, 16), dtype=numpy.uint8)
        chunk_data['Biomes'] = biomes

        for section in chunk_data['Sections']:

            # Turn the Blocks array into a 16x16x16 numpy matrix of shorts,
            # adding in the additional block array if included.
            blocks = numpy.frombuffer(section['Blocks'], dtype=numpy.uint8)
            # Cast up to uint16, blocks can have up to 12 bits of data
            blocks = blocks.astype(numpy.uint16)
            blocks = blocks.reshape((16,16,16))
            if "Add" in section:
                # This section has additional bits to tack on to the blocks
                # array. Add is a packed array with 4 bits per slot, so
                # it needs expanding
                additional = numpy.frombuffer(section['Add'], dtype=numpy.uint8)
                additional = additional.astype(numpy.uint16).reshape((16,16,8))
                additional_expanded = numpy.empty((16,16,16), dtype=numpy.uint16)
                additional_expanded[:,:,::2] = (additional & 0x0F) << 8
                additional_expanded[:,:,1::2] = (additional & 0xF0) << 4
                blocks += additional_expanded
                del additional
                del additional_expanded
                del section['Add'] # Save some memory
            section['Blocks'] = blocks

            # Turn the skylight array into a 16x16x16 matrix. The array comes
            # packed 2 elements per byte, so we need to expand it.
            try:
                skylight = numpy.frombuffer(section['SkyLight'], dtype=numpy.uint8)
                skylight = skylight.reshape((16,16,8))
                skylight_expanded = numpy.empty((16,16,16), dtype=numpy.uint8)
                skylight_expanded[:,:,::2] = skylight & 0x0F
                skylight_expanded[:,:,1::2] = (skylight & 0xF0) >> 4
                del skylight
                section['SkyLight'] = skylight_expanded

                # Turn the BlockLight array into a 16x16x16 matrix, same as SkyLight
                blocklight = numpy.frombuffer(section['BlockLight'], dtype=numpy.uint8)
                blocklight = blocklight.reshape((16,16,8))
                blocklight_expanded = numpy.empty((16,16,16), dtype=numpy.uint8)
                blocklight_expanded[:,:,::2] = blocklight & 0x0F
                blocklight_expanded[:,:,1::2] = (blocklight & 0xF0) >> 4
                del blocklight
                section['BlockLight'] = blocklight_expanded

                # Turn the Data array into a 16x16x16 matrix, same as SkyLight
                data = numpy.frombuffer(section['Data'], dtype=numpy.uint8)
                data = data.reshape((16,16,8))
                data_expanded = numpy.empty((16,16,16), dtype=numpy.uint8)
                data_expanded[:,:,::2] = data & 0x0F
                data_expanded[:,:,1::2] = (data & 0xF0) >> 4
                del data
                section['Data'] = data_expanded
            except ValueError:
                # iv'e seen at least 1 case where numpy raises a value error during the reshapes.  i'm not
                # sure what's going on here, but let's treat this as a corrupt chunk error
                logging.warning("There was a problem reading chunk %d,%d.  It might be corrupt.  I am giving up and will not render this particular chunk.", x, z)

                logging.debug("Full traceback:", exc_info=1)
                raise nbt.CorruptChunkError()
        
        return chunk_data      
    

    def iterate_chunks(self):
        """Returns an iterator over all chunk metadata in this world. Iterates
        over tuples of integers (x,z,mtime) for each chunk.  Other chunk data
        is not returned here.
        
        """

        for (regionx, regiony), (regionfile, filemtime) in self.regionfiles.iteritems():
            try:
                mcr = self._get_regionobj(regionfile)
            except nbt.CorruptRegionError:
                logging.warning("Found a corrupt region file at %s,%s. Skipping it.", regionx, regiony)
                continue
            for chunkx, chunky in mcr.get_chunks():
                yield chunkx+32*regionx, chunky+32*regiony, mcr.get_chunk_timestamp(chunkx, chunky)

    def iterate_newer_chunks(self, mtime):
        """Returns an iterator over all chunk metadata in this world. Iterates
        over tuples of integers (x,z,mtime) for each chunk.  Other chunk data
        is not returned here.
        
        """

        for (regionx, regiony), (regionfile, filemtime) in self.regionfiles.iteritems():
            """ SKIP LOADING A REGION WHICH HAS NOT BEEN MODIFIED! """
            if (filemtime < mtime):
                continue

            try:
                mcr = self._get_regionobj(regionfile)
            except nbt.CorruptRegionError:
                logging.warning("Found a corrupt region file at %s,%s. Skipping it.", regionx, regiony)
                continue

            for chunkx, chunky in mcr.get_chunks():
                yield chunkx+32*regionx, chunky+32*regiony, mcr.get_chunk_timestamp(chunkx, chunky)

    def get_chunk_mtime(self, x, z):
        """Returns a chunk's mtime, or False if the chunk does not exist.  This
        is therefore a dual purpose method. It corrects for the given north
        direction as described in the docs for get_chunk()
        
        """

        regionfile = self._get_region_path(x,z)
        if regionfile is None:
            return None
        try:
            data = self._get_regionobj(regionfile)
        except nbt.CorruptRegionError:
            logging.warning("Ignoring request for chunk %s,%s; region %s,%s seems to be corrupt",
                    x,z, x//32,z//32)
            return None
        if data.chunk_exists(x,z):
            return data.get_chunk_timestamp(x,z)
        return None

    def _get_region_path(self, chunkX, chunkY):
        """Returns the path to the region that contains chunk (chunkX, chunkY)
        Coords can be either be global chunk coords, or local to a region

        """
        (regionfile,filemtime) = self.regionfiles.get((chunkX//32, chunkY//32),(None, None))
        return regionfile
            
    def _iterate_regionfiles(self):
        """Returns an iterator of all of the region files, along with their 
        coordinates

        Returns (regionx, regiony, filename)"""

        logging.debug("regiondir is %s, has type %r", self.regiondir, self.type)

        for f in os.listdir(self.regiondir):
            if re.match(r"^r\.-?\d+\.-?\d+\.mca$", f):
                p = f.split(".")
                x = int(p[1])
                y = int(p[2])
                if abs(x) > 500000 or abs(y) > 500000:
                    logging.warning("Holy shit what is up with region file %s !?" % f)
                yield (x, y, os.path.join(self.regiondir, f))

class RegionSetWrapper(object):
    """This is the base class for all "wrappers" of RegionSet objects. A
    wrapper is an object that acts similarly to a subclass: some methods are
    overridden and functionality is changed, others may not be. The difference
    here is that these wrappers may wrap each other, forming chains.

    In fact, subclasses of this object may act exactly as if they've subclassed
    the original RegionSet object, except the first parameter of the
    constructor is a regionset object, not a regiondir.

    This class must implement the full public interface of RegionSet objects

    """
    def __init__(self, rsetobj):
        self._r = rsetobj

    def get_type(self):
        return self._r.get_type()
    def get_biome_data(self, x, z):
        return self._r.get_biome_data(x,z)
    def get_chunk(self, x, z):
        return self._r.get_chunk(x,z)
    def iterate_chunks(self):
        return self._r.iterate_chunks()
    def iterate_newer_chunks(self,filemtime):
        return self._r.iterate_newer_chunks(filemtime)
    def get_chunk_mtime(self, x, z):
        return self._r.get_chunk_mtime(x,z)
    
# see RegionSet.rotate.  These values are chosen so that they can be
# passed directly to rot90; this means that they're the number of
# times to rotate by 90 degrees CCW
UPPER_LEFT  = 0 ## - Return the world such that north is down the -Z axis (no rotation)
UPPER_RIGHT = 1 ## - Return the world such that north is down the +X axis (rotate 90 degrees counterclockwise)
LOWER_RIGHT = 2 ## - Return the world such that north is down the +Z axis (rotate 180 degrees)
LOWER_LEFT  = 3 ## - Return the world such that north is down the -X axis (rotate 90 degrees clockwise)

class RotatedRegionSet(RegionSetWrapper):
    """A regionset, only rotated such that north points in the given direction

    """
    
    # some class-level rotation constants
    _NO_ROTATION =               lambda x,z: (x,z)
    _ROTATE_CLOCKWISE =          lambda x,z: (-z,x)
    _ROTATE_COUNTERCLOCKWISE =   lambda x,z: (z,-x)
    _ROTATE_180 =                lambda x,z: (-x,-z)
    
    # These take rotated coords and translate into un-rotated coords
    _unrotation_funcs = [
        _NO_ROTATION,
        _ROTATE_COUNTERCLOCKWISE,
        _ROTATE_180,
        _ROTATE_CLOCKWISE,
    ]
    
    # These translate un-rotated coordinates into rotated coordinates
    _rotation_funcs = [
        _NO_ROTATION,
        _ROTATE_CLOCKWISE,
        _ROTATE_180,
        _ROTATE_COUNTERCLOCKWISE,
    ]
    
    def __init__(self, rsetobj, north_dir):
        self.north_dir = north_dir
        self.unrotate = self._unrotation_funcs[north_dir]
        self.rotate = self._rotation_funcs[north_dir]

        super(RotatedRegionSet, self).__init__(rsetobj)

    
    # Re-initialize upon unpickling. This is needed because we store a couple
    # lambda functions as instance variables
    def __getstate__(self):
        return (self._r, self.north_dir)
    def __setstate__(self, args):
        self.__init__(args[0], args[1])
    
    def get_chunk(self, x, z):
        x,z = self.unrotate(x,z)
        chunk_data = dict(super(RotatedRegionSet, self).get_chunk(x,z))
        newsections = []
        for section in chunk_data['Sections']:
            section = dict(section)
            newsections.append(section)
            for arrayname in ['Blocks', 'Data', 'SkyLight', 'BlockLight']:
                array = section[arrayname]
                # Since the anvil change, arrays are arranged with axes Y,Z,X
                # numpy.rot90 always rotates the first two axes, so for it to
                # work, we need to temporarily move the X axis to the 0th axis.
                array = numpy.swapaxes(array, 0,2)
                array = numpy.rot90(array, self.north_dir)
                array = numpy.swapaxes(array, 0,2)
                section[arrayname] = array
        chunk_data['Sections'] = newsections
        
        # same as above, for biomes (Z/X indexed)
        biomes = numpy.swapaxes(chunk_data['Biomes'], 0, 1)
        biomes = numpy.rot90(biomes, self.north_dir)
        chunk_data['Biomes'] = numpy.swapaxes(biomes, 0, 1)
        return chunk_data

    def get_chunk_mtime(self, x, z):
        x,z = self.unrotate(x,z)
        return super(RotatedRegionSet, self).get_chunk_mtime(x, z)

    def iterate_chunks(self):
        for x,z,mtime in super(RotatedRegionSet, self).iterate_chunks():
            x,z = self.rotate(x,z)
            yield x,z,mtime

    def iterate_newer_chunks(self, filemtime):
        for x,z,mtime in super(RotatedRegionSet, self).iterate_newer_chunks(filemtime):
            x,z = self.rotate(x,z)
            yield x,z,mtime

class CroppedRegionSet(RegionSetWrapper):
    def __init__(self, rsetobj, xmin, zmin, xmax, zmax):
        super(CroppedRegionSet, self).__init__(rsetobj)
        self.xmin = xmin//16
        self.xmax = xmax//16
        self.zmin = zmin//16
        self.zmax = zmax//16

    def get_chunk(self,x,z):
        if (
                self.xmin <= x <= self.xmax and
                self.zmin <= z <= self.zmax
                ):
            return super(CroppedRegionSet, self).get_chunk(x,z)
        else:
            raise ChunkDoesntExist("This chunk is out of the requested bounds")

    def iterate_chunks(self):
        return ((x,z,mtime) for (x,z,mtime) in super(CroppedRegionSet,self).iterate_chunks()
                if
                    self.xmin <= x <= self.xmax and
                    self.zmin <= z <= self.zmax
                )

    def iterate_newer_chunks(self, filemtime):
        return ((x,z,mtime) for (x,z,mtime) in super(CroppedRegionSet,self).iterate_newer_chunks(filemtime)
                if
                    self.xmin <= x <= self.xmax and
                    self.zmin <= z <= self.zmax
                )

    def get_chunk_mtime(self,x,z):
        if (
                self.xmin <= x <= self.xmax and
                self.zmin <= z <= self.zmax
                ):
            return super(CroppedRegionSet, self).get_chunk_mtime(x,z)
        else:
            return None

class CachedRegionSet(RegionSetWrapper):
    """A regionset wrapper that implements caching of the results from
    get_chunk()

    """
    def __init__(self, rsetobj, cacheobjects):
        """Initialize this wrapper around the given regionset object and with
        the given list of cache objects. The cache objects may be shared among
        other CachedRegionSet objects.

        """
        super(CachedRegionSet, self).__init__(rsetobj)
        self.caches = cacheobjects

        # Construct a key from the sequence of transformations and the real
        # RegionSet object, so that items we place in the cache don't conflict
        # with other worlds/transformation combinations.
        obj = self._r
        s = ""
        while isinstance(obj, RegionSetWrapper):
            s += obj.__class__.__name__ + "."
            obj = obj._r
        # obj should now be the actual RegionSet object
        try:
            s += obj.regiondir
        except AttributeError:
            s += repr(obj)

        logging.debug("Initializing a cache with key '%s'", s)

        s = hashlib.md5(s).hexdigest()

        self.key = s

    def get_chunk(self, x, z):
        key = hashlib.md5(repr((self.key, x, z))).hexdigest()
        for i, cache in enumerate(self.caches):
            try:
                retval = cache[key]
                # This did have it, no need to re-add it to this cache, just
                # the ones before it
                i -= 1
                break
            except KeyError:
                pass
        else:
            retval = super(CachedRegionSet, self).get_chunk(x,z)

        # Now add retval to all the caches that didn't have it, all the caches
        # up to and including index i
        for cache in self.caches[:i+1]:
            cache[key] = retval

        return retval
        

def get_save_dir():
    """Returns the path to the local saves directory
      * On Windows, at %APPDATA%/.minecraft/saves/
      * On Darwin, at $HOME/Library/Application Support/minecraft/saves/
      * at $HOME/.minecraft/saves/

    """
    
    savepaths = []
    if "APPDATA" in os.environ:
        savepaths += [os.path.join(os.environ['APPDATA'], ".minecraft", "saves")]
    if "HOME" in os.environ:
        savepaths += [os.path.join(os.environ['HOME'], "Library",
                "Application Support", "minecraft", "saves")]
        savepaths += [os.path.join(os.environ['HOME'], ".minecraft", "saves")]

    for path in savepaths:
        if os.path.exists(path):
            return path

def get_worlds():
    "Returns {world # or name : level.dat information}"
    ret = {}
    save_dir = get_save_dir()
    loc = locale.getpreferredencoding()

    # No dirs found - most likely not running from inside minecraft-dir
    if not save_dir is None:
        for dir in os.listdir(save_dir):
            world_dat = os.path.join(save_dir, dir, "level.dat")
            if not os.path.exists(world_dat): continue
            info = nbt.load(world_dat)[1]
            info['Data']['path'] = os.path.join(save_dir, dir).decode(loc)
            if dir.startswith("World") and len(dir) == 6:
                try:
                    world_n = int(dir[-1])
                    ret[world_n] = info['Data']
                except ValueError:
                    pass
            if 'LevelName' in info['Data'].keys():
                ret[info['Data']['LevelName']] = info['Data']
    
    for dir in os.listdir("."):
        world_dat = os.path.join(dir, "level.dat")
        if not os.path.exists(world_dat): continue
        info = nbt.load(world_dat)[1]
        info['Data']['path'] = os.path.join(".", dir).decode(loc)
        if 'LevelName' in info['Data'].keys():
            ret[info['Data']['LevelName']] = info['Data']

    return ret

########NEW FILE########
__FILENAME__ = sample_config
# This is a sample config file, meant to give you an idea of how to format your
# config file and what's possible.

# Define the path to your world here. 'My World' in this case will show up as
# the world name on the map interface. If you change it, be sure to also change
# the referenced world names in the render definitions below.
worlds['My World'] = "/path/to/your/world"

# Define where to put the output here.
outputdir = "/tmp/test_render"

# This is an item usually specified in a renders dictionary below, but if you
# set it here like this, it becomes the default for all renders that don't
# define it.
# Try "smooth_lighting" for even better looking maps!
rendermode = "lighting"

renders["render1"] = {
        'world': 'My World',
        'title': 'A regular render',
}

# This example is the same as above, but rotated
renders["render2"] = {
        'world': 'My World',
        'northdirection': 'upper-right',
        'title': 'Upper-right north direction',
}

# Here's how to do a nighttime render. Also try "smooth_night" instead of "night"
renders["render3"] = {
        'world': 'My World',
        'title': 'Nighttime',
        # Notice how this overrides the rendermode default specified above
        'rendermode': 'night',
}


########NEW FILE########
__FILENAME__ = settings_test_1
worlds['test'] = "test/data/settings/test_world"

renders["myworld"] = { 
    "title": "myworld title",
    "world": "test",
    "rendermode": normal,
    "northdirection": "upper-left",
}

renders["otherworld"] = {
    "title": "otherworld title",
    "world": "test",
    "rendermode": normal,
    "bgcolor": "#ffffff"
}

outputdir = "/tmp/fictional/outputdir"

########NEW FILE########
__FILENAME__ = settings_test_rendermode
worlds['test'] = "test/data/settings/test_world"

renders["world"] = { 
    "world": "test", 
    "title": "myworld title",
    "rendermode": "bad_rendermode",
    "northdirection": "upper-left",
}

outputdir = "/tmp/fictional/outputdir"

########NEW FILE########
__FILENAME__ = test_all
#!/usr/bin/env python
import unittest

# For convenience
import sys,os,logging
sys.path.insert(0, os.getcwd())
sys.path.insert(0, os.path.join(os.getcwd(), os.pardir))

# Import unit test cases or suites here
from test_tileobj import TileTest
from test_rendertileset import RendertileSetTest
from test_settings import SettingsTest
from test_tileset import TilesetTest
from test_cache import TestLRU

# DISABLE THIS BLOCK TO GET LOG OUTPUT FROM TILESET FOR DEBUGGING
if 0:
    root = logging.getLogger()
    class NullHandler(logging.Handler):
        def handle(self, record):
            pass
        def emit(self, record):
            pass
        def createLock(self):
            self.lock = None
    root.addHandler(NullHandler())
else:
    from overviewer_core import logger
    logger.configure(logging.DEBUG, True)


if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_cache
import unittest

from overviewer_core import cache

class TestLRU(unittest.TestCase):

    def setUp(self):
        self.lru = cache.LRUCache(size=5)

    def test_single_insert(self):
        self.lru[1] = 2
        self.assertEquals(self.lru[1], 2)

    def test_multiple_insert(self):
        self.lru[1] = 2
        self.lru[3] = 4
        self.lru[5] = 6
        self.assertEquals(self.lru[1], 2)
        self.assertEquals(self.lru[3], 4)
        self.assertEquals(self.lru[5], 6)

    def test_full(self):
        self.lru[1] = 'asdf'
        self.lru[2] = 'asdf'
        self.lru[3] = 'asdf'
        self.lru[4] = 'asdf'
        self.lru[5] = 'asdf'
        self.lru[6] = 'asdf'
        self.assertRaises(KeyError, self.lru.__getitem__, 1)
        self.assertEquals(self.lru[2], 'asdf')
        self.assertEquals(self.lru[3], 'asdf')
        self.assertEquals(self.lru[4], 'asdf')
        self.assertEquals(self.lru[5], 'asdf')
        self.assertEquals(self.lru[6], 'asdf')

    def test_lru(self):
        self.lru[1] = 'asdf'
        self.lru[2] = 'asdf'
        self.lru[3] = 'asdf'
        self.lru[4] = 'asdf'
        self.lru[5] = 'asdf'

        self.assertEquals(self.lru[1], 'asdf')
        self.assertEquals(self.lru[2], 'asdf')
        self.assertEquals(self.lru[4], 'asdf')
        self.assertEquals(self.lru[5], 'asdf')

        # 3 should be evicted now
        self.lru[6] = 'asdf'

        self.assertRaises(KeyError, self.lru.__getitem__, 3)
        self.assertEquals(self.lru[1], 'asdf')
        self.assertEquals(self.lru[2], 'asdf')
        self.assertEquals(self.lru[4], 'asdf')
        self.assertEquals(self.lru[5], 'asdf')
        self.assertEquals(self.lru[6], 'asdf')

########NEW FILE########
__FILENAME__ = test_rendertileset
import unittest

from itertools import chain, izip

from overviewer_core.tileset import iterate_base4, RendertileSet
from overviewer_core.util import roundrobin

class RendertileSetTest(unittest.TestCase):
    # If you change this definition, you must also change the hard-coded
    # results list in test_posttraverse()
    tile_paths = frozenset([
            # Entire subtree 0/0 is in the set, nothing else under 0
            (0,0,0),
            (0,0,1),
            (0,0,2),
            (0,0,3),
            # A few tiles under quadrant 1
            (1,0,3),
            (1,1,3),
            (1,2,0),
            # Entire subtree under quadrant 2 is in the set
            (2,0,0),
            (2,0,1),
            (2,0,2),
            (2,0,3),
            (2,1,0),
            (2,1,1),
            (2,1,2),
            (2,1,3),
            (2,2,0),
            (2,2,1),
            (2,2,2),
            (2,2,3),
            (2,3,0),
            (2,3,1),
            (2,3,2),
            (2,3,3),
            # Nothing under quadrant 3
            ])
    # The paths as yielded by posttraversal, in an expanding-from-the-center
    # order.
    tile_paths_posttraversal_lists = [
        [
            (0,0,3),
            (0,0,1),
            (0,0,2),
            (0,0,0),
            (0,0),
            (0,),
        ],
        [
            (1,2,0),
            (1,2),

            (1,0,3),
            (1,0),

            (1,1,3),
            (1,1),
            (1,),
        ],
        [
            (2,1,1),
            (2,1,0),
            (2,1,3),
            (2,1,2),
            (2,1),

            (2,0,1),
            (2,0,3),
            (2,0,0),
            (2,0,2),
            (2,0),

            (2,3,1),
            (2,3,0),
            (2,3,3),
            (2,3,2),
            (2,3),

            (2,2,1),
            (2,2,0),
            (2,2,3),
            (2,2,2),
            (2,2),
            (2,),
        ],
    ]
    # Non-round robin post-traversal: finish the first top-level quadrant
    # before moving to the second etc.
    tile_paths_posttraversal       = list(chain(*tile_paths_posttraversal_lists))     + [()]
    # Round-robin post-traversal: start rendering to all directions from the
    # center.
    tile_paths_posttraversal_robin = list(roundrobin(tile_paths_posttraversal_lists)) + [()]

    def setUp(self):
        self.tree = RendertileSet(3)
        for t in self.tile_paths:
            self.tree.add(t)

    def test_query(self):
        """Make sure the correct tiles in the set"""
        for path in iterate_base4(3):
            if path in self.tile_paths:
                self.assertTrue( self.tree.query_path(path) )
            else:
                self.assertFalse( self.tree.query_path(path) )

    def test_iterate(self):
        """Make sure iterating over the tree returns each tile exactly once"""
        dirty = set(self.tile_paths)
        for p in self.tree:
            # Can't use assertIn, was only added in 2.7
            self.assertTrue(p in dirty)

            # Should not see this one again
            dirty.remove(p)

        # Make sure they were all returned
        self.assertEqual(len(dirty), 0)

    def test_iterate_levelmax(self):
        """Same as test_iterate, but specifies the level explicitly"""
        dirty = set(self.tile_paths)
        for p in self.tree.iterate(3):
            # Can't use assertIn, was only added in 2.7
            self.assertTrue(p in dirty)

            # Should not see this one again
            dirty.remove(p)

        # Make sure they were all returned
        self.assertEqual(len(dirty), 0)

    def test_iterate_fail(self):
        """Meta-test: Make sure test_iterate() would actually fail"""
        # if an extra item were returned"""
        self.tree.add((1,1,1))
        self.assertRaises(AssertionError, self.test_iterate)

        # If something was supposed to be returned but wasn't
        tree = RendertileSet(3)
        c = len(self.tile_paths) // 2
        for t in self.tile_paths:
            tree.add(t)
            c -= 1
            if c <= 0:
                break
        self.tree = tree
        self.assertRaises(AssertionError, self.test_iterate)

    def test_count(self):
        self.assertEquals(self.tree.count(), len(self.tile_paths))

    def test_bool(self):
        "Tests the boolean status of a node"
        self.assertTrue(self.tree)
        t = RendertileSet(3)
        self.assertFalse(t)
        t.add((0,0,0))
        self.assertTrue(t)

    def test_query_level(self):
        "Tests querying at a level other than max"
        # level 2
        l2 = set()
        for p in self.tile_paths:
            l2.add(p[0:2])
        for path in iterate_base4(2):
            if path in l2:
                self.assertTrue( self.tree.query_path(path) )
            else:
                self.assertFalse( self.tree.query_path(path) )

        # level 1:
        self.assertTrue( self.tree.query_path((0,)))
        self.assertTrue( self.tree.query_path((1,)))
        self.assertTrue( self.tree.query_path((2,)))
        self.assertFalse( self.tree.query_path((3,)))

    def test_iterate_level(self):
        """Test iterating at a level other than max"""
        # level 2
        l2 = set()
        for p in self.tile_paths:
            l2.add(p[0:2])
        for p in self.tree.iterate(2):
            self.assertTrue(p in l2, "%s was not supposed to be returned!" % (p,))
            l2.remove(p)
        self.assertEqual(len(l2), 0, "Never iterated over these items: %s" % l2)

        # level 1
        l1 = set()
        for p in self.tile_paths:
            l1.add(p[0:1])
        for p in self.tree.iterate(1):
            self.assertTrue(p in l1, "%s was not supposed to be returned!" % (p,))
            l1.remove(p)
        self.assertEqual(len(l1), 0, "Never iterated over these items: %s" % l1)

    def test_posttraverse(self):
        """Test a post-traversal of the tree's dirty tiles"""
        # Expect the results in this proper order.
        iterator = iter(self.tree.posttraversal())
        for expected, actual in izip(self.tile_paths_posttraversal, iterator):
            self.assertEqual(actual, expected)

        self.assertRaises(StopIteration, next, iterator)

    def test_posttraverse_roundrobin(self):
        """Test a round-robin post-traversal of the tree's dirty tiles"""
        # Expect the results in this proper order.
        iterator = iter(self.tree.posttraversal(robin=True))
        for expected, actual in izip(self.tile_paths_posttraversal_robin, iterator):
            self.assertEqual(actual, expected)

        self.assertRaises(StopIteration, next, iterator)

    def test_count_all(self):
        """Tests getting a count of all tiles (render tiles plus upper tiles)

        """
        c = self.tree.count_all()
        self.assertEqual(c, 35)

if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_settings
import unittest

from overviewer_core import configParser
from overviewer_core.settingsValidators import ValidationException

from overviewer_core import world
from overviewer_core import rendermodes

from overviewer_core.util import OrderedDict

class SettingsTest(unittest.TestCase):
    
    def setUp(self):
        self.s = configParser.MultiWorldParser()
    
    def test_missing(self):
        "Validates that a non-existant settings.py causes an exception"
        self.assertRaises(configParser.MissingConfigException, self.s.parse, "doesnotexist.py")

    def test_existing_file(self):
        self.s.parse("test/data/settings/settings_test_1.py")
        things = self.s.get_validated_config()
        # no exceptions so far.  that's a good thing

        # Test the default
        self.assertEquals(things['renders']['myworld']['bgcolor'], (26,26,26,0))

        # Test a non-default
        self.assertEquals(things['renders']['otherworld']['bgcolor'], (255,255,255,0))

        self.assertEquals(things['renders']['myworld']['northdirection'],
               world.UPPER_LEFT) 

    def test_rendermode_validation(self):
        self.s.parse("test/data/settings/settings_test_rendermode.py")

        self.assertRaises(ValidationException,self.s.get_validated_config)

    def test_manual(self):
        """Tests that manually setting the config parser works, you don't have
        to do it from a file
        
        """
        fromfile = configParser.MultiWorldParser()
        fromfile.parse("test/data/settings/settings_test_1.py")

        self.s.set_config_item("worlds", {
            'test': "test/data/settings/test_world",
            })
        self.s.set_config_item("renders", OrderedDict([
                ("myworld", {
                    "title": "myworld title",
                    "world": "test",
                    "rendermode": rendermodes.normal,
                    "northdirection": "upper-left",
                }),

                ("otherworld", {
                    "title": "otherworld title",
                    "world": "test",
                    "rendermode": rendermodes.normal,
                    "bgcolor": "#ffffff"
                }),
            ]))
        self.s.set_config_item("outputdir", "/tmp/fictional/outputdir")
        self.assertEquals(fromfile.get_validated_config(), self.s.get_validated_config())

    def test_rendermode_string(self):
        self.s.set_config_item("worlds", {
            'test': "test/data/settings/test_world",
            })
        self.s.set_config_item("outputdir", "/tmp/fictional/outputdir")
        self.s.set_config_item("renders", {
                "myworld": { 
                    "title": "myworld title",
                    "world": "test",
                    "rendermode": "normal",
                    "northdirection": "upper-left",
                },
                })
        p = self.s.get_validated_config()
        self.assertEquals(p['renders']['myworld']['rendermode'], rendermodes.normal)

if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_tileobj
import unittest

from overviewer_core.tileset import iterate_base4, RenderTile

items = [
        ((-4,-8), (0,0)),
        ((-2,-8), (0,1)),
        ((0,-8), (1,0)),
        ((2,-8), (1,1)),
        ((-4,-4), (0,2)),
        ((-2,-4), (0,3)),
        ((0,-4), (1,2)),
        ((2,-4), (1,3)),
        ((-4,0), (2,0)),
        ((-2,0), (2,1)),
        ((0,0), (3,0)),
        ((2,0), (3,1)),
        ((-4,4), (2,2)),
        ((-2,4), (2,3)),
        ((0,4), (3,2)),
        ((2,4), (3,3)),
        ]

class TileTest(unittest.TestCase):
    def test_compute_path(self):
        """Tests that the correct path is computed when a col,row,depth is
        given to compute_path

        """
        for path in iterate_base4(7):
            t1 = RenderTile.from_path(path)
            col = t1.col
            row = t1.row
            depth = len(path)

            t2 = RenderTile.compute_path(col, row, depth)
            self.assertEqual(t1, t2)

    def test_equality(self):
        t1 = RenderTile(-6, -20, (0,1,2,3))
        
        self.assertEqual(t1, RenderTile(-6, -20, (0,1,2,3)))
        self.assertNotEqual(t1, RenderTile(-4, -20, (0,1,2,3)))
        self.assertNotEqual(t1, RenderTile(-6, -24, (0,1,2,3)))
        self.assertNotEqual(t1, RenderTile(-6, -20, (0,1,2,0)))

    def test_depth2_from_path(self):
        """Test frompath on all 16 tiles of a depth 2 tree"""
        for (col, row), path in items:
            t = RenderTile.from_path(path)
            self.assertEqual(t.col, col)
            self.assertEqual(t.row, row)

    def test_depth2_compute_path(self):
        """Test comptue_path on all 16 tiles of a depth 2 tree"""
        for (col, row), path in items:
            t = RenderTile.compute_path(col, row, 2)
            self.assertEqual(t.path, path)


if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_tileset
import unittest
import tempfile
import shutil
from collections import defaultdict
import os
import os.path
import random

from overviewer_core import tileset

# Supporing data
# chunks list: chunkx, chunkz mapping to chunkmtime
# In comments: col, row
chunks = {
        (0, 0): 5, # 0, 0
        (0, 1): 5, # 1, 1
        (0, 2): 5, # 2, 2
        (0, 3): 5, # 3, 3
        (0, 4): 5, # 4, 4
        (1, 0): 5, # 1, -1
        (1, 1): 5, # 2, 0
        (1, 2): 5, # 3, 1
        (1, 3): 5, # 4, 2
        (1, 4): 5, # 5, 3
        (2, 0): 5, # 2, -2
        (2, 1): 5, # 3, -1
        (2, 2): 5, # 4, 0
        (2, 3): 5, # 5, 1
        (2, 4): 5, # 6, 2
        (3, 0): 5, # 3, -3
        (3, 1): 5, # 4, -2
        (3, 2): 5, # 5, -1
        (3, 3): 5, # 6, 0
        (3, 4): 5, # 7, 1
        (4, 0): 5, # 4, -4
        (4, 1): 5, # 5, -3
        (4, 2): 5, # 6, -2
        (4, 3): 5, # 7, -1
        (4, 4): 5, # 8, 0
        }

# Supporting resources
######################

class FakeRegionset(object):
    def __init__(self, chunks):
        self.chunks = dict(chunks)

    def get_chunk(self, x,z):
        return NotImplementedError()

    def iterate_chunks(self):
        for (x,z),mtime in self.chunks.iteritems():
            yield x,z,mtime

    def iterate_newer_chunks(self, filemtime):
        for (x,z),mtime in self.chunks.iteritems():
            yield x,z,mtime

    def get_chunk_mtime(self, x, z):
        try:
            return self.chunks[x,z]
        except KeyError:
            return None

class FakeAssetmanager(object):
    def __init__(self, lastrendertime):
        self.lrm = lastrendertime

    def get_tileset_config(self, _):
        return {'lastrendertime': self.lrm}

def get_tile_set(chunks):
    """Given the dictionary mapping chunk coordinates their mtimes, returns a
    dict mapping the tiles that are to be rendered to their mtimes that are
    expected. Useful for passing into the create_fakedir() function. Used by
    the compare_iterate_to_expected() method.
    """
    tile_set = defaultdict(int)
    for (chunkx, chunkz), chunkmtime in chunks.iteritems():

        col, row = tileset.convert_coords(chunkx, chunkz)

        for tilec, tiler in tileset.get_tiles_by_chunk(col, row):
            tile = tileset.RenderTile.compute_path(tilec, tiler, 5)
            tile_set[tile.path] = max(tile_set[tile.path], chunkmtime)

    # At this point, tile_set holds all the render-tiles
    for tile, tile_mtime in tile_set.copy().iteritems():
        # All render-tiles are length 5. Hard-code its upper tiles
        for i in reversed(xrange(5)):
            tile_set[tile[:i]] = max(tile_set[tile[:i]], tile_mtime)
    return dict(tile_set)

def create_fakedir(outputdir, tiles):
    """Takes a base output directory and a tiles dict mapping tile paths to
    tile mtimes as returned by get_tile_set(), creates the "tiles" (empty
    files) and sets mtimes appropriately

    """
    for tilepath, tilemtime in tiles.iteritems():
        dirpath = os.path.join(outputdir, *(str(x) for x in tilepath[:-1]))
        if len(tilepath) == 0:
            imgname = "base.png"
        else:
            imgname = str(tilepath[-1]) + ".png"

        if not os.path.exists(dirpath):
            os.makedirs(dirpath)
        finalpath = os.path.join(dirpath, imgname)
        open(finalpath, 'w').close()
        os.utime(finalpath, (tilemtime, tilemtime))

# The test cases
################
class TilesetTest(unittest.TestCase):
    def setUp(self):
        # Set up the region set
        self.rs = FakeRegionset(chunks)

        self.tempdirs = []

        # Consistent random numbers
        self.r = random.Random(1)

    def tearDown(self):
        for d in self.tempdirs:
            shutil.rmtree(d)

    def get_outputdir(self):
        d = tempfile.mkdtemp(prefix="OVTEST")
        self.tempdirs.append(d)
        return d

    def get_tileset(self, options, outputdir, preprocess=None):
        """Returns a newly created TileSet object and return it.
        A set of default options are provided. Any options passed in will
        override the defaults. The output directory is passed in and it is
        recommended to use a directory from self.get_outputdir()

        preprocess, if given, is a function that takes the tileset object. It
        is called before do_preprocessing()
        """
        defoptions = {
                'name': 'world name',
                'bgcolor': '#000000',
                'imgformat': 'png',
                'optimizeimg': 0,
                'rendermode': 'normal',
                'rerenderprob': 0
                }
        defoptions.update(options)
        ts = tileset.TileSet(None, self.rs, FakeAssetmanager(0), None, defoptions, outputdir)
        if preprocess:
            preprocess(ts)
        ts.do_preprocessing()
        return ts

    def compare_iterate_to_expected(self, ts, chunks):
        """Runs iterate_work_items on the tileset object and compares its
        output to what we'd expect if it was run with the given chunks

        chunks is a dictionary whose keys are chunkx,chunkz. This method
        calculates from that set of chunks the tiles they touch and their
        parent tiles, and compares that to the output of ts.iterate_work_items().

        """
        paths = set(x[0] for x in ts.iterate_work_items(0))

        # Get what tiles we expect to be returned
        expected = get_tile_set(chunks)

        # Check that all paths returned are in the expected list
        for tilepath in paths:
            self.assertTrue(tilepath in expected, "%s was not expected to be returned. Expected %s" % (tilepath, expected))

        # Now check that all expected tiles were indeed returned
        for tilepath in expected.iterkeys():
            self.assertTrue(tilepath in paths, "%s was expected to be returned but wasn't: %s" % (tilepath, paths))

    def test_get_phase_length(self):
        ts = self.get_tileset({'renderchecks': 2}, self.get_outputdir())
        self.assertEqual(ts.get_num_phases(), 1)
        self.assertEqual(ts.get_phase_length(0), len(get_tile_set(chunks)))

    def test_forcerender_iterate(self):
        """Tests that a rendercheck mode 2 iteration returns every render-tile
        and upper-tile
        """
        ts = self.get_tileset({'renderchecks': 2}, self.get_outputdir())
        self.compare_iterate_to_expected(ts, self.rs.chunks)


    def test_update_chunk(self):
        """Tests that an update in one chunk properly updates just the
        necessary tiles for rendercheck mode 0, normal operation. This
        shouldn't touch the filesystem at all.

        """

        # Update one chunk with a newer mtime
        updated_chunks = {
                (0,0): 6
                }
        self.rs.chunks.update(updated_chunks)

        # Create the tileset and set its last render time to 5
        ts = self.get_tileset({'renderchecks': 0}, self.get_outputdir(),
                lambda ts: setattr(ts, 'last_rendertime', 5))

        # Now see if the return is what we expect
        self.compare_iterate_to_expected(ts, updated_chunks)

    def test_update_chunk2(self):
        """Same as above but with a different set of chunks
        """
        # Pick 3 random chunks to update
        chunks = self.rs.chunks.keys()
        self.r.shuffle(chunks)
        updated_chunks = {}
        for key in chunks[:3]:
            updated_chunks[key] = 6
        self.rs.chunks.update(updated_chunks)
        ts = self.get_tileset({'renderchecks': 0}, self.get_outputdir(),
                lambda ts: setattr(ts, 'last_rendertime', 5))
        self.compare_iterate_to_expected(ts, updated_chunks)

    def test_rendercheckmode_1(self):
        """Tests that an interrupted render will correctly pick up tiles that
        need rendering

        """
        # For this we actually need to set the tile mtimes on disk and have the
        # TileSet object figure out from that what it needs to render.
        # Strategy: set some tiles on disk to mtime 3, and TileSet needs to
        # find them and update them to mtime 5 as reported by the RegionSet
        # object.
        # Chosen at random:
        outdated_tiles = [
                (0,3,3,3,3),
                (1,2,2,2,1),
                (2,1,1),
                (3,)
                ]
        # These are the tiles that we also expect it to return, even though
        # they were not outdated, since they depend on the outdated tiles
        additional = [
                (0,3,3,3),
                (0,3,3),
                (0,3),
                (0,),
                (1,2,2,2),
                (1,2,2),
                (1,2),
                (1,),
                (2,1),
                (2,),
                (),
                ]

        outputdir = self.get_outputdir()
        # Fill the output dir with tiles
        all_tiles = get_tile_set(self.rs.chunks)
        all_tiles.update(dict((x,3) for x in outdated_tiles))
        create_fakedir(outputdir, all_tiles)

        # Create the tileset and do the scan
        ts = self.get_tileset({'renderchecks': 1}, outputdir)

        # Now see if it's right
        paths = set(x[0] for x in ts.iterate_work_items(0))
        expected = set(outdated_tiles) | set(additional)
        for tilepath in paths:
            self.assertTrue(tilepath in expected, "%s was not expected to be returned. Expected %s" % (tilepath, expected))

        for tilepath in expected:
            self.assertTrue(tilepath in paths, "%s was expected to be returned but wasn't: %s" % (tilepath, paths))

########NEW FILE########
__FILENAME__ = test_world
import unittest

import os

from overviewer_core import world

class ExampleWorldTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Make sure that test/data/worlds/example exists
        # if it doesn't, then give a little 
        if not os.path.exists("test/data/worlds/exmaple"):
            raise Exception("test data doesn't exist.  Maybe you need to init/update your submodule?")

    def test_basic(self):
        "Basic test of the world constructor and regionset constructor"
        w = world.World("test/data/worlds/exmaple")

        regionsets = w.get_regionsets()
        self.assertEquals(len(regionsets), 3)

        regionset = regionsets[0]
        self.assertEquals(regionset.get_region_path(0,0), 'test/data/worlds/exmaple/DIM-1/region/r.0.0.mcr')
        self.assertEquals(regionset.get_region_path(-1,0), 'test/data/worlds/exmaple/DIM-1/region/r.-1.0.mcr')
        self.assertEquals(regionset.get_region_path(1,1), 'test/data/worlds/exmaple/DIM-1/region/r.0.0.mcr')
        self.assertEquals(regionset.get_region_path(35,35), None)

        # a few random chunks.  reference timestamps fetched with libredstone
        self.assertEquals(regionset.get_chunk_mtime(0,0), 1316728885)
        self.assertEquals(regionset.get_chunk_mtime(-1,-1), 1316728886)
        self.assertEquals(regionset.get_chunk_mtime(5,0), 1316728905)
        self.assertEquals(regionset.get_chunk_mtime(-22,16), 1316786786)

        
         

if __name__ == "__main__":
    unittest.main()

########NEW FILE########
