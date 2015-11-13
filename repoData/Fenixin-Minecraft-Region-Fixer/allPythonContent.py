__FILENAME__ = interactive
#!/usr/bin/env python
# -*- coding: utf-8 -*-

#
#   Region Fixer.
#   Fix your region files with a backup copy of your Minecraft world.
#   Copyright (C) 2011  Alejandro Aguilera (Fenixin)
#   https://github.com/Fenixin/Minecraft-Region-Fixer
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#


# TODO needs big update!
import world

from cmd import Cmd
from scan import scan_world, scan_regionset

class interactive_loop(Cmd):
    def __init__(self, world_list, regionset, options, backup_worlds):
        Cmd.__init__(self)
        self.world_list = world_list
        self.regionset = regionset
        self.world_names = [str(i.name)  for i in self.world_list]
        # if there's only one world use it 
        if len(self.world_list) == 1 and len(self.regionset) == 0:
            self.current = world_list[0]
        elif len(self.world_list) == 0 and len(self.regionset) > 0:
            self.current = self.regionset
        else:
            self.current = None
        self.options = options
        self.backup_worlds = backup_worlds
        self.prompt = "#-> "
        self.intro = "Minecraft Region-Fixer interactive mode.\n(Use tab to autocomplete. Autocomplete doens't work on Windows. Type help for a list of commands.)\n"

        # other region-fixer stuff

        # possible args for chunks stuff
        possible_args = ""
        first = True
        for i in world.CHUNK_PROBLEMS_ARGS.values() + ['all']:
            if not first:
                possible_args += ", "
            possible_args += i 
            first = False
        self.possible_chunk_args_text = possible_args
        
        # possible args for region stuff
        possible_args = ""
        first = True
        for i in world.REGION_PROBLEMS_ARGS.values() + ['all']:
            if not first:
                possible_args += ", "
            possible_args += i 
            first = False
        self.possible_region_args_text = possible_args
        
    
    # do
    def do_set(self,arg):
        """ Command to change some options and variables in interactive
            mode """
        args = arg.split()
        if len(args) > 2:
            print "Error: too many parameters."
        elif len(args) == 0:
            print "Write \'help set\' to see a list of all possible variables"
        else:
            if args[0] == "entity-limit":
                if len(args) == 1:
                    print "entity-limit = {0}".format(self.options.entity_limit)
                else:
                    try:
                        if int(args[1]) >= 0:
                            self.options.entity_limit = int(args[1])
                            print "entity-limit = {0}".format(args[1])
                            print "Updating chunk status..."
                            self.current.rescan_entities(self.options)
                        else:
                            print "Invalid value. Valid values are positive integers and zero"
                    except ValueError:
                        print "Invalid value. Valid values are positive integers and zero"

            elif args[0] == "workload":

                if len(args) == 1:
                    if self.current:
                        print "Current workload:\n{0}\n".format(self.current.__str__())
                    print "List of possible worlds and region-sets (determined by the command used to run region-fixer):"
                    number = 1
                    for w in self.world_list:
                        print "   ### world{0} ###".format(number)
                        number += 1
                        # add a tab and print
                        for i in w.__str__().split("\n"): print "\t" + i
                        print 
                    print "   ### regionset ###"
                    for i in self.regionset.__str__().split("\n"): print "\t" + i
                    print "\n(Use \"set workload world1\" or name_of_the_world or regionset to choose one)"

                else:
                    a = args[1]
                    if len(a) == 6 and a[:5] == "world" and int(a[-1]) >= 1 :
                        # get the number and choos the correct world from the list
                        number = int(args[1][-1]) - 1
                        try:
                            self.current = self.world_list[number]
                            print "workload = {0}".format(self.current.world_path)
                        except IndexError:
                            print "This world is not in the list!"
                    elif a in self.world_names:
                        for w in self.world_list:
                            if w.name == args[1]:
                                self.current = w
                                print "workload = {0}".format(self.current.world_path)
                                break
                        else:
                            print "This world name is not on the list!"
                    elif args[1] == "regionset":
                        if len(self.regionset):
                            self.current = self.regionset
                            print "workload = set of region files"
                        else:
                            print "The region set is empty!"
                    else:
                        print "Invalid world number, world name or regionset."

            elif args[0] == "processes":
                if len(args) == 1:
                    print "processes = {0}".format(self.options.processes)
                else:
                    try:
                        if int(args[1]) > 0:
                            self.options.processes = int(args[1])
                            print "processes = {0}".format(args[1])
                        else:
                            print "Invalid value. Valid values are positive integers."
                    except ValueError:
                        print "Invalid value. Valid values are positive integers."

            elif args[0] == "verbose":
                if len(args) == 1:
                    print "verbose = {0}".format(str(self.options.verbose))
                else:
                    if args[1] == "True":
                        self.options.verbose = True
                        print "verbose = {0}".format(args[1])
                    elif args[1] == "False":
                        self.options.verbose = False
                        print "verbose = {0}".format(args[1])
                    else:
                        print "Invalid value. Valid values are True and False."
            else:
                print "Invalid argument! Write \'help set\' to see a list of valid variables."

    def do_summary(self, arg):
        """ Prints a summary of all the problems found in the region
            files. """
        if len(arg) == 0:
            if self.current:
                if self.current.scanned:
                    text = self.current.summary()
                    if text: print text
                    else: print "No problems found!"
                else:
                    print "The world hasn't be scanned (or it needs a rescan). Use \'scan\' to scan it."
            else:
                print "No world/region-set is set! Use \'set workload\' to set a world/regionset to work with."
        else:
            print "This command doesn't use any arguments."

    def do_current_workload(self, arg):
        """ Prints the info of the current workload """
        if len(arg) == 0:
            if self.current: print self.current
            else: print "No world/region-set is set! Use \'set workload\' to set a world/regionset to work with."
        else:
            print "This command doesn't use any arguments."

    def do_scan(self, arg):
        # TODO: what about scanning while deleting entities as done in non-interactive mode?
        # this would need an option to choose which of the two methods use
        """ Scans the current workload. """
        if len(arg.split()) > 0:
            print "Error: too many parameters."
        else:
            if self.current:
                if isinstance(self.current, world.World):
                    self.current = world.World(self.current.path)
                    scan_world(self.current, self.options)
                elif isinstance(self.current, world.RegionSet):
                    print "\n{0:-^60}".format(' Scanning region files ')
                    scan_regionset(self.current, self.options)
            else:
                print "No world set! Use \'set workload\'"

    def do_count_chunks(self, arg):
        """ Counts the number of chunks with the given problem and
            prints the result """
        if self.current and self.current.scanned:
            if len(arg.split()) == 0:
                print "Possible counters are: {0}".format(self.possible_chunk_args_text)
            elif len(arg.split()) > 1:
                print "Error: too many parameters."
            else:
                if arg in world.CHUNK_PROBLEMS_ARGS.values() or arg == 'all':
                    total = self.current.count_chunks(None)
                    for problem, status_text, a in world.CHUNK_PROBLEMS_ITERATOR:
                        if arg == 'all' or arg == a:
                            n = self.current.count_chunks(problem)
                            print "Chunks with status \'{0}\': {1}".format(status_text, n)
                    print "Total chunks: {0}".format(total)
                else:
                    print "Unknown counter."
        else:
            print "The world hasn't be scanned (or it needs a rescan). Use \'scan\' to scan it."

    def do_count_regions(self, arg):
        """ Counts the number of regions with the given problem and
            prints the result """
        if self.current and self.current.scanned:
            if len(arg.split()) == 0:
                print "Possible counters are: {0}".format(self.possible_region_args_text)
            elif len(arg.split()) > 1:
                print "Error: too many parameters."
            else:
                if arg in world.REGION_PROBLEMS_ARGS.values() or arg == 'all':
                    total = self.current.count_regions(None)
                    for problem, status_text, a in world.REGION_PROBLEMS_ITERATOR:
                        if arg == 'all' or arg == a:
                            n = self.current.count_regions(problem)
                            print "Regions with status \'{0}\': {1}".format(status_text, n)
                    print "Total regions: {0}".format(total)
                else:
                    print "Unknown counter."
        else:
            print "The world hasn't be scanned (or it needs a rescan). Use \'scan\' to scan it."

    def do_count_all(self, arg):
        """ Print all the counters for chunks and regions. """
        if self.current and self.current.scanned:
            if len(arg.split()) > 0:
                print "This command doesn't requiere any arguments"
            else:
                print "{0:#^60}".format("Chunk problems:")
                self.do_count_chunks('all')
                print "\n"
                print "{0:#^60}".format("Region problems:")
                self.do_count_regions('all')
        else:
            print "The world hasn't be scanned (or it needs a rescan). Use \'scan\' to scan it."

    def do_remove_entities(self, arg):
        if self.current and self.current.scanned:
            if len(arg.split()) > 0:
                print "Error: too many parameters."
            else:
                print "WARNING: This will delete all the entities in the chunks that have more entities than entity-limit, make sure you know what entities are!.\nAre you sure you want to continue? (yes/no):"
                answer = raw_input()
                if answer == 'yes':
                    counter = self.current.remove_entities()
                    print "Deleted {0} entities.".format(counter)
                    if counter:
                        self.current.scanned = False
                    self.current.rescan_entities(self.options)
                elif answer == 'no':
                    print "Ok!"
                else: print "Invalid answer, use \'yes\' or \'no\' the next time!."
        else:
            print "The world hasn't be scanned (or it needs a rescan). Use \'scan\' to scan it."

    def do_remove_chunks(self, arg):
        if self.current and self.current.scanned:
            if len(arg.split()) == 0:
                print "Possible arguments are: {0}".format(self.possible_chunk_args_text)
            elif len(arg.split()) > 1:
                print "Error: too many parameters."
            else:
                if arg in world.CHUNK_PROBLEMS_ARGS.values() or arg == 'all':
                    for problem, status_text, a in world.CHUNK_PROBLEMS_ITERATOR:
                        if arg == 'all' or arg == a:
                            n = self.current.remove_problematic_chunks(problem)
                            if n:
                                self.current.scanned = False
                            print "Removed {0} chunks with status \'{1}\'.\n".format(n, status_text)
                else:
                    print "Unknown argument."
        else:
            print "The world hasn't be scanned (or it needs a rescan). Use \'scan\' to scan it."

    def do_replace_chunks(self, arg):
        if self.current and self.current.scanned:
            if len(arg.split()) == 0:
                print "Possible arguments are: {0}".format(self.possible_chunk_args_text)
            elif len(arg.split()) > 1:
                print "Error: too many parameters."
            else:
                if arg in world.CHUNK_PROBLEMS_ARGS.values() or arg == 'all':
                    for problem, status_text, a in world.CHUNK_PROBLEMS_ITERATOR:
                        if arg == 'all' or arg == a:
                            n = self.current.replace_problematic_chunks(self.backup_worlds, problem, self.options)
                            if n:
                                self.current.scanned = False
                            print "\nReplaced {0} chunks with status \'{1}\'.".format(n, status_text)
                else:
                    print "Unknown argument."
        else:
            print "The world hasn't be scanned (or it needs a rescan). Use \'scan\' to scan it."

    def do_replace_regions(self, arg):
        if self.current and self.current.scanned:
            if len(arg.split()) == 0:
                print "Possible arguments are: {0}".format(self.possible_region_args_text)
            elif len(arg.split()) > 1:
                print "Error: too many parameters."
            else:
                if arg in world.REGION_PROBLEMS_ARGS.values() or arg == 'all':
                    for problem, status_text, a in world.REGION_PROBLEMS_ITERATOR:
                        if arg == 'all' or arg == a:
                            n = self.current.replace_problematic_regions(self.backup_worlds, problem, self.options)
                            if n:
                                self.current.scanned = False
                            print "\nReplaced {0} regions with status \'{1}\'.".format(n, status_text)
                else:
                    print "Unknown argument."
        else:
            print "The world hasn't be scanned (or it needs a rescan). Use \'scan\' to scan it."
        
    def do_remove_regions(self, arg):
        if self.current and self.current.scanned:
            if len(arg.split()) == 0:
                print "Possible arguments are: {0}".format(self.possible_region_args_text)
            elif len(arg.split()) > 1:
                print "Error: too many parameters."
            else:
                if arg in world.REGION_PROBLEMS_ARGS.values() or arg == 'all':
                    for problem, status_text, a in world.REGION_PROBLEMS_ITERATOR:
                        if arg == 'all' or arg == a:
                            n = self.current.remove_problematic_regions(problem)
                            if n:
                                self.current.scanned = False
                            print "\nRemoved {0} regions with status \'{1}\'.".format(n, status_text)
                else:
                    print "Unknown argument."
        else:
            print "The world hasn't be scanned (or it needs a rescan). Use \'scan\' to scan it."
        pass

    def do_quit(self, arg):
        print "Quitting."
        return True

    def do_exit(self, arg):
        print "Exiting."
        return True

    def do_EOF(self, arg):
        print "Quitting."
        return True

    # complete
    def complete_arg(self, text, possible_args):
        l = []
        for arg in possible_args:
            if text in arg and arg.find(text) == 0:
                l.append(arg + " ")
        return l

    def complete_set(self, text, line, begidx, endidx):
        if "workload " in line:
            # return the list of world names plus 'regionset' plus a list of world1, world2...
            possible_args = tuple(self.world_names) + ('regionset',) + tuple([ 'world' + str(i+1) for i in range(len(self.world_names))])
        elif 'verbose ' in line:
            possible_args = ('True','False')
        else:
            possible_args = ('entity-limit','verbose','processes','workload')
        return self.complete_arg(text, possible_args)

    def complete_count_chunks(self, text, line, begidx, endidx):
        possible_args = world.CHUNK_PROBLEMS_ARGS.values() + ['all']
        return self.complete_arg(text, possible_args)

    def complete_remove_chunks(self, text, line, begidx, endidx):
        possible_args = world.CHUNK_PROBLEMS_ARGS.values() + ['all']
        return self.complete_arg(text, possible_args)

    def complete_replace_chunks(self, text, line, begidx, endidx):
        possible_args = world.CHUNK_PROBLEMS_ARGS.values() + ['all']
        return self.complete_arg(text, possible_args)

    def complete_count_regions(self, text, line, begidx, endidx):
        possible_args = world.REGION_PROBLEMS_ARGS.values() + ['all']
        return self.complete_arg(text, possible_args)

    def complete_remove_regions(self, text, line, begidx, endidx):
        possible_args = world.REGION_PROBLEMS_ARGS.values() + ['all']
        return self.complete_arg(text, possible_args)

    def complete_replace_regions(self, text, line, begidx, endidx):
        possible_args = world.REGION_PROBLEMS_ARGS.values() + ['all']
        return self.complete_arg(text, possible_args)

    # help
    # TODO sería una buena idea poner un artículo de ayuda de como usar el programa en un caso típico.
    # TODO: the help texts need a normalize
    def help_set(self):
        print "\nSets some variables used for the scan in interactive mode. If you run this command without an argument for a variable you can see the current state of the variable. You can set:"
        print "   verbose" 
        print "If True prints a line per scanned region file instead of showing a progress bar."
        print "\n   entity-limit"
        print "If a chunk has more than this number of entities it will be added to the list of chunks with too many entities problem."
        print "\n   processes"
        print "Number of cores used while scanning the world."
        print "\n   workload"
        print "If you input a few worlds you can choose wich one will be scanned using this command.\n"
    def help_current_workload(self):
        print "\nPrints information of the current region-set/world. This will be the region-set/world to scan and fix.\n"
    def help_scan(self):
        print "\nScans the current world set or the region set.\n"

    def help_count_chunks(self):
        print "\n   Prints out the number of chunks with the given status. For example"
        print "\'count corrupted\' prints the number of corrupted chunks in the world."
        print 
        print "Possible status are: {0}\n".format(self.possible_chunk_args_text)
    def help_remove_entities(self):
        print "\nRemove all the entities in chunks that have more than entity-limit entities."
        print 
        print "This chunks are the ones with status \'too many entities\'.\n"
    def help_remove_chunks(self):
        print "\nRemoves bad chunks with the given problem."
        print
        print "Please, be careful, when used with the status too-many-entities this will" 
        print "REMOVE THE CHUNKS with too many entities problems, not the entities."
        print "To remove only the entities see the command remove_entities."
        print
        print "For example \'remove_chunks corrupted\' this will remove corrupted chunks."
        print
        print "Possible status are: {0}\n".format(self.possible_chunk_args_text)
        print
    def help_replace_chunks(self):
        print "\nReplaces bad chunks with the given status using the backups directories."
        print
        print "Exampe: \"replace_chunks corrupted\""
        print
        print "this will replace the corrupted chunks with the given backups."
        print
        print "Possible status are: {0}\n".format(self.possible_chunk_args_text)
        print
        print "Note: after replacing any chunks you have to rescan the world.\n"

    def help_count_regions(self):
        print "\n   Prints out the number of regions with the given status. For example "
        print "\'count_regions too-small\' prints the number of region with \'too-small\' status."
        print 
        print "Possible status are: {0}\n".format(self.possible_region_args_text)
    def help_remove_regions(self):
        print "\nRemoves regions with the given status."
        print
        print "Example: \'remove_regions too-small\'"
        print
        print "this will remove the region files with status \'too-small\'."
        print
        print "Possible status are: {0}".format(self.possible_region_args_text)
        print
        print "Note: after removing any regions you have to rescan the world.\n"
    def help_replace_regions(self):
        print "\nReplaces regions with the given status."
        print
        print "Example: \"replace_regions too-small\""
        print
        print "this will try to replace the region files with status \'too-small\'"
        print "with the given backups."
        print
        print "Possible status are: {0}".format(self.possible_region_args_text)
        print
        print "Note: after replacing any regions you have to rescan the world.\n"

    def help_summary(self):
        print "\nPrints a summary of all the problems found in the current workload.\n"
    def help_quit(self):
        print "\nQuits interactive mode, exits region-fixer. Same as \'EOF\' and \'exit\' commands.\n"
    def help_EOF(self):
        print "\nQuits interactive mode, exits region-fixer. Same as \'quit\' and \'exit\' commands\n"
    def help_exit(self):
        print "\nQuits interactive mode, exits region-fixer. Same as \'quit\' and \'EOF\' commands\n"
    def help_help(self):
        print "Prints help help."

########NEW FILE########
__FILENAME__ = chunk
"""
Handles a single chunk of data (16x16x128 blocks) from a Minecraft save.
Chunk is currently McRegion only.
"""
from io import BytesIO
from struct import pack, unpack
import array, math

class Chunk(object):
    """Class for representing a single chunk."""
    def __init__(self, nbt):
        chunk_data = nbt['Level']
        self.coords = chunk_data['xPos'],chunk_data['zPos']
        self.blocks = BlockArray(chunk_data['Blocks'].value, chunk_data['Data'].value)

    def get_coords(self):
        """Return the coordinates of this chunk."""
        return (self.coords[0].value,self.coords[1].value)

    def __repr__(self):
        """Return a representation of this Chunk."""
        return "Chunk("+str(self.coords[0])+","+str(self.coords[1])+")"


class BlockArray(object):
    """Convenience class for dealing with a Block/data byte array."""
    def __init__(self, blocksBytes=None, dataBytes=None):
        """Create a new BlockArray, defaulting to no block or data bytes."""
        if isinstance(blocksBytes, (bytearray, array.array)):
            self.blocksList = list(blocksBytes)
        else:
            self.blocksList = [0]*32768 # Create an empty block list (32768 entries of zero (air))

        if isinstance(dataBytes, (bytearray, array.array)):
            self.dataList = list(dataBytes)
        else:
            self.dataList = [0]*16384 # Create an empty data list (32768 4-bit entries of zero make 16384 byte entries)

    # Get all block entries
    def get_all_blocks(self):
        """Return the blocks that are in this BlockArray."""
        return self.blocksList

    # Get all data entries
    def get_all_data(self):
        """Return the data of all the blocks in this BlockArray."""
        bits = []
        for b in self.dataList:
            # The first byte of the Blocks arrays correspond
            # to the LEAST significant bits of the first byte of the Data.
            # NOT to the MOST significant bits, as you might expected.
            bits.append(b & 15) # Little end of the byte
            bits.append((b >> 4) & 15) # Big end of the byte
        return bits

    # Get all block entries and data entries as tuples
    def get_all_blocks_and_data(self):
        """Return both blocks and data, packed together as tuples."""
        return list(zip(self.get_all_blocks(), self.get_all_data()))

    def get_blocks_struct(self):
        """Return a dictionary with block ids keyed to (x, y, z)."""
        cur_x = 0
        cur_y = 0
        cur_z = 0
        blocks = {}
        for block_id in self.blocksList:
            blocks[(cur_x,cur_y,cur_z)] = block_id
            cur_y += 1
            if (cur_y > 127):
                cur_y = 0
                cur_z += 1
                if (cur_z > 15):
                    cur_z = 0
                    cur_x += 1
        return blocks

    # Give blockList back as a byte array
    def get_blocks_byte_array(self, buffer=False):
        """Return a list of all blocks in this chunk."""
        if buffer:
            length = len(self.blocksList)
            return BytesIO(pack(">i", length)+self.get_blocks_byte_array())
        else:
            return array.array('B', self.blocksList).tostring()

    def get_data_byte_array(self, buffer=False):
        """Return a list of data for all blocks in this chunk."""
        if buffer:
            length = len(self.dataList)
            return BytesIO(pack(">i", length)+self.get_data_byte_array())
        else:
            return array.array('B', self.dataList).tostring()

    def generate_heightmap(self, buffer=False, as_array=False):
        """Return a heightmap, representing the highest solid blocks in this chunk."""
        non_solids = [0, 8, 9, 10, 11, 38, 37, 32, 31]
        if buffer:
            return BytesIO(pack(">i", 256)+self.generate_heightmap()) # Length + Heightmap, ready for insertion into Chunk NBT
        else:
            bytes = []
            for z in range(16):
                for x in range(16):
                    for y in range(127, -1, -1):
                        offset = y + z*128 + x*128*16
                        if (self.blocksList[offset] not in non_solids or y == 0):
                            bytes.append(y+1)
                            break
            if (as_array):
                return bytes
            else:
                return array.array('B', bytes).tostring()

    def set_blocks(self, list=None, dict=None, fill_air=False):
        """
        Sets all blocks in this chunk, using either a list or dictionary.  
        Blocks not explicitly set can be filled to air by setting fill_air to True.
        """
        if list:
            # Inputting a list like self.blocksList
            self.blocksList = list
        elif dict:
            # Inputting a dictionary like result of self.get_blocks_struct()
            list = []
            for x in range(16):
                for z in range(16):
                    for y in range(128):
                        coord = x,y,z
                        offset = y + z*128 + x*128*16
                        if (coord in dict):
                            list.append(dict[coord])
                        else:
                            if (self.blocksList[offset] and not fill_air):
                                list.append(self.blocksList[offset])
                            else:
                                list.append(0) # Air
            self.blocksList = list
        else:
            # None of the above...
            return False
        return True

    def set_block(self, x,y,z, id, data=0):
        """Sets the block a x, y, z to the specified id, and optionally data."""
        offset = y + z*128 + x*128*16
        self.blocksList[offset] = id
        if (offset % 2 == 1):
            # offset is odd
            index = (offset-1)//2
            b = self.dataList[index]
            self.dataList[index] = (b & 240) + (data & 15) # modify lower bits, leaving higher bits in place
        else:
            # offset is even
            index = offset//2
            b = self.dataList[index]
            self.dataList[index] = (b & 15) + (data << 4 & 240) # modify ligher bits, leaving lower bits in place

    # Get a given X,Y,Z or a tuple of three coordinates
    def get_block(self, x,y,z, coord=False):
        """Return the id of the block at x, y, z."""
        """
        Laid out like:
        (0,0,0), (0,1,0), (0,2,0) ... (0,127,0), (0,0,1), (0,1,1), (0,2,1) ... (0,127,1), (0,0,2) ... (0,127,15), (1,0,0), (1,1,0) ... (15,127,15)
        
        ::
        
          blocks = []
          for x in range(15):
            for z in range(15):
              for y in range(127):
                blocks.append(Block(x,y,z))
        """

        offset = y + z*128 + x*128*16 if (coord == False) else coord[1] + coord[2]*128 + coord[0]*128*16
        return self.blocksList[offset]

    # Get a given X,Y,Z or a tuple of three coordinates
    def get_data(self, x,y,z, coord=False):
        """Return the data of the block at x, y, z."""
        offset = y + z*128 + x*128*16 if (coord == False) else coord[1] + coord[2]*128 + coord[0]*128*16
        # The first byte of the Blocks arrays correspond
        # to the LEAST significant bits of the first byte of the Data.
        # NOT to the MOST significant bits, as you might expected.
        if (offset % 2 == 1):
            # offset is odd
            index = (offset-1)//2
            b = self.dataList[index]
            return b & 15 # Get little (last 4 bits) end of byte
        else:
            # offset is even
            index = offset//2
            b = self.dataList[index]
            return (b >> 4) & 15 # Get big end (first 4 bits) of byte

    def get_block_and_data(self, x,y,z, coord=False):
        """Return the tuple of (id, data) for the block at x, y, z"""
        return (self.get_block(x,y,z,coord),self.get_data(x,y,z,coord))


########NEW FILE########
__FILENAME__ = nbt
"""
Handle the NBT (Named Binary Tag) data format
"""

from struct import Struct, error as StructError
from gzip import GzipFile
import zlib
from collections import MutableMapping, MutableSequence, Sequence
import os, io

try:
    unicode
    basestring
except NameError:
    unicode = str  # compatibility for Python 3
    basestring = str  # compatibility for Python 3


TAG_END = 0
TAG_BYTE = 1
TAG_SHORT = 2
TAG_INT = 3
TAG_LONG = 4
TAG_FLOAT = 5
TAG_DOUBLE = 6
TAG_BYTE_ARRAY = 7
TAG_STRING = 8
TAG_LIST = 9
TAG_COMPOUND = 10
TAG_INT_ARRAY = 11

class MalformedFileError(Exception):
    """Exception raised on parse error."""
    pass

class TAG(object):
    """TAG, a variable with an intrinsic name."""
    id = None

    def __init__(self, value=None, name=None):
        self.name = name
        self.value = value

    #Parsers and Generators
    def _parse_buffer(self, buffer):
        raise NotImplementedError(self.__class__.__name__)

    def _render_buffer(self, buffer):
        raise NotImplementedError(self.__class__.__name__)

    #Printing and Formatting of tree
    def tag_info(self):
        """Return Unicode string with class, name and unnested value."""
        return self.__class__.__name__ + \
                ('(%r)' % self.name if self.name else "") + \
                ": " + self.valuestr()
    def valuestr(self):
        """Return Unicode string of unnested value. For iterators, this returns a summary."""
        return unicode(self.value)

    def pretty_tree(self, indent=0):
        """Return formated Unicode string of self, where iterable items are recursively listed in detail."""
        return ("\t"*indent) + self.tag_info()

    # Python 2 compatibility; Python 3 uses __str__ instead.
    def __unicode__(self):
        """Return a unicode string with the result in human readable format. Unlike valuestr(), the result is recursive for iterators till at least one level deep."""
        return unicode(self.value)

    def __str__(self):
        """Return a string (ascii formated for Python 2, unicode for Python 3) with the result in human readable format. Unlike valuestr(), the result is recursive for iterators till at least one level deep."""
        return str(self.value)
    # Unlike regular iterators, __repr__() is not recursive.
    # Use pretty_tree for recursive results.
    # iterators should use __repr__ or tag_info for each item, like regular iterators
    def __repr__(self):
        """Return a string (ascii formated for Python 2, unicode for Python 3) describing the class, name and id for debugging purposes."""
        return "<%s(%r) at 0x%x>" % (self.__class__.__name__,self.name,id(self))

class _TAG_Numeric(TAG):
    """_TAG_Numeric, comparable to int with an intrinsic name"""
    def __init__(self, value=None, name=None, buffer=None):
        super(_TAG_Numeric, self).__init__(value, name)
        if buffer:
            self._parse_buffer(buffer)

    #Parsers and Generators
    def _parse_buffer(self, buffer):
        # Note: buffer.read() may raise an IOError, for example if buffer is a corrupt gzip.GzipFile
        self.value = self.fmt.unpack(buffer.read(self.fmt.size))[0]

    def _render_buffer(self, buffer):
        buffer.write(self.fmt.pack(self.value))

class _TAG_End(TAG):
    id = TAG_END
    fmt = Struct(">b")

    def _parse_buffer(self, buffer):
        # Note: buffer.read() may raise an IOError, for example if buffer is a corrupt gzip.GzipFile
        value = self.fmt.unpack(buffer.read(1))[0]
        if value != 0:
            raise ValueError("A Tag End must be rendered as '0', not as '%d'." % (value))

    def _render_buffer(self, buffer):
        buffer.write(b'\x00')

#== Value Tags ==#
class TAG_Byte(_TAG_Numeric):
    """Represent a single tag storing 1 byte."""
    id = TAG_BYTE
    fmt = Struct(">b")

class TAG_Short(_TAG_Numeric):
    """Represent a single tag storing 1 short."""
    id = TAG_SHORT
    fmt = Struct(">h")

class TAG_Int(_TAG_Numeric):
    """Represent a single tag storing 1 int."""
    id = TAG_INT
    fmt = Struct(">i")
    """Struct(">i"), 32-bits integer, big-endian"""

class TAG_Long(_TAG_Numeric):
    """Represent a single tag storing 1 long."""
    id = TAG_LONG
    fmt = Struct(">q")

class TAG_Float(_TAG_Numeric):
    """Represent a single tag storing 1 IEEE-754 floating point number."""
    id = TAG_FLOAT
    fmt = Struct(">f")

class TAG_Double(_TAG_Numeric):
    """Represent a single tag storing 1 IEEE-754 double precision floating point number."""
    id = TAG_DOUBLE
    fmt = Struct(">d")

class TAG_Byte_Array(TAG, MutableSequence):
    """
    TAG_Byte_Array, comparable to a collections.UserList with
    an intrinsic name whose values must be bytes
    """
    id = TAG_BYTE_ARRAY
    def __init__(self, name=None, buffer=None):
        super(TAG_Byte_Array, self).__init__(name=name)
        if buffer:
            self._parse_buffer(buffer)

    #Parsers and Generators
    def _parse_buffer(self, buffer):
        length = TAG_Int(buffer=buffer)
        self.value = bytearray(buffer.read(length.value))

    def _render_buffer(self, buffer):
        length = TAG_Int(len(self.value))
        length._render_buffer(buffer)
        buffer.write(bytes(self.value))

    # Mixin methods
    def __len__(self):
        return len(self.value)

    def __iter__(self):
        return iter(self.value)

    def __contains__(self, item):
        return item in self.value

    def __getitem__(self, key):
        return self.value[key]

    def __setitem__(self, key, value):
        # TODO: check type of value
        self.value[key] = value

    def __delitem__(self, key):
        del(self.value[key])

    def insert(self, key, value):
        # TODO: check type of value, or is this done by self.value already?
        self.value.insert(key, value)

    #Printing and Formatting of tree
    def valuestr(self):
        return "[%i byte(s)]" % len(self.value)

    def __unicode__(self):
        return '['+",".join([unicode(x) for x in self.value])+']'
    def __str__(self):
        return '['+",".join([str(x) for x in self.value])+']'

class TAG_Int_Array(TAG, MutableSequence):
    """
    TAG_Int_Array, comparable to a collections.UserList with
    an intrinsic name whose values must be integers
    """
    id = TAG_INT_ARRAY
    def __init__(self, name=None, buffer=None):
        super(TAG_Int_Array, self).__init__(name=name)
        if buffer:
            self._parse_buffer(buffer)

    def update_fmt(self, length):
        """ Adjust struct format description to length given """
        self.fmt = Struct(">" + str(length) + "i")

    #Parsers and Generators
    def _parse_buffer(self, buffer):
        length = TAG_Int(buffer=buffer).value
        self.update_fmt(length)
        self.value = list(self.fmt.unpack(buffer.read(self.fmt.size)))

    def _render_buffer(self, buffer):
        length = len(self.value)
        self.update_fmt(length)
        TAG_Int(length)._render_buffer(buffer)
        buffer.write(self.fmt.pack(*self.value))

    # Mixin methods
    def __len__(self):
        return len(self.value)

    def __iter__(self):
        return iter(self.value)

    def __contains__(self, item):
        return item in self.value

    def __getitem__(self, key):
        return self.value[key]

    def __setitem__(self, key, value):
        self.value[key] = value

    def __delitem__(self, key):
        del(self.value[key])

    def insert(self, key, value):
        self.value.insert(key, value)

    #Printing and Formatting of tree
    def valuestr(self):
        return "[%i int(s)]" % len(self.value)


class TAG_String(TAG, Sequence):
    """
    TAG_String, comparable to a collections.UserString with an
    intrinsic name
    """
    id = TAG_STRING
    def __init__(self, value=None, name=None, buffer=None):
        super(TAG_String, self).__init__(value, name)
        if buffer:
            self._parse_buffer(buffer)

    #Parsers and Generators
    def _parse_buffer(self, buffer):
        length = TAG_Short(buffer=buffer)
        read = buffer.read(length.value)
        if len(read) != length.value:
            raise StructError()
        self.value = read.decode("utf-8")

    def _render_buffer(self, buffer):
        save_val = self.value.encode("utf-8")
        length = TAG_Short(len(save_val))
        length._render_buffer(buffer)
        buffer.write(save_val)

    # Mixin methods
    def __len__(self):
        return len(self.value)

    def __iter__(self):
        return iter(self.value)

    def __contains__(self, item):
        return item in self.value

    def __getitem__(self, key):
        return self.value[key]

    #Printing and Formatting of tree
    def __repr__(self):
        return self.value

#== Collection Tags ==#
class TAG_List(TAG, MutableSequence):
    """
    TAG_List, comparable to a collections.UserList with an intrinsic name
    """
    id = TAG_LIST
    def __init__(self, type=None, value=None, name=None, buffer=None):
        super(TAG_List, self).__init__(value, name)
        if type:
            self.tagID = type.id
        else:
            self.tagID = None
        self.tags = []
        if buffer:
            self._parse_buffer(buffer)
        if self.tagID == None:
            raise ValueError("No type specified for list: %s" % (name))

    #Parsers and Generators
    def _parse_buffer(self, buffer):
        self.tagID = TAG_Byte(buffer=buffer).value
        self.tags = []
        length = TAG_Int(buffer=buffer)
        for x in range(length.value):
            self.tags.append(TAGLIST[self.tagID](buffer=buffer))

    def _render_buffer(self, buffer):
        TAG_Byte(self.tagID)._render_buffer(buffer)
        length = TAG_Int(len(self.tags))
        length._render_buffer(buffer)
        for i, tag in enumerate(self.tags):
            if tag.id != self.tagID:
                raise ValueError("List element %d(%s) has type %d != container type %d" %
                         (i, tag, tag.id, self.tagID))
            tag._render_buffer(buffer)

    # Mixin methods
    def __len__(self):
        return len(self.tags)

    def __iter__(self):
        return iter(self.tags)

    def __contains__(self, item):
        return item in self.tags

    def __getitem__(self, key):
        return self.tags[key]

    def __setitem__(self, key, value):
        self.tags[key] = value

    def __delitem__(self, key):
        del(self.tags[key])

    def insert(self, key, value):
        self.tags.insert(key, value)

    #Printing and Formatting of tree
    def __repr__(self):
        return "%i entries of type %s" % (len(self.tags), TAGLIST[self.tagID].__name__)

    #Printing and Formatting of tree
    def valuestr(self):
        return "[%i %s(s)]" % (len(self.tags), TAGLIST[self.tagID].__name__)
    def __unicode__(self):
        return "["+", ".join([tag.tag_info() for tag in self.tags])+"]"
    def __str__(self):
        return "["+", ".join([tag.tag_info() for tag in self.tags])+"]"

    def pretty_tree(self, indent=0):
        output = [super(TAG_List, self).pretty_tree(indent)]
        if len(self.tags):
            output.append(("\t"*indent) + "{")
            output.extend([tag.pretty_tree(indent + 1) for tag in self.tags])
            output.append(("\t"*indent) + "}")
        return '\n'.join(output)

class TAG_Compound(TAG, MutableMapping):
    """
    TAG_Compound, comparable to a collections.OrderedDict with an
    intrinsic name
    """
    id = TAG_COMPOUND
    def __init__(self, buffer=None):
        super(TAG_Compound, self).__init__()
        self.tags = []
        self.name = ""
        if buffer:
            self._parse_buffer(buffer)

    #Parsers and Generators
    def _parse_buffer(self, buffer):
        while True:
            type = TAG_Byte(buffer=buffer)
            if type.value == TAG_END:
                #print("found tag_end")
                break
            else:
                name = TAG_String(buffer=buffer).value
                try:
                    tag = TAGLIST[type.value](buffer=buffer)
                    tag.name = name
                    self.tags.append(tag)
                except KeyError:
                    raise ValueError("Unrecognised tag type")

    def _render_buffer(self, buffer):
        for tag in self.tags:
            TAG_Byte(tag.id)._render_buffer(buffer)
            TAG_String(tag.name)._render_buffer(buffer)
            tag._render_buffer(buffer)
        buffer.write(b'\x00') #write TAG_END

    # Mixin methods
    def __len__(self):
        return len(self.tags)

    def __iter__(self):
        for key in self.tags:
            yield key.name

    def __contains__(self, key):
        if isinstance(key, int):
            return key <= len(self.tags)
        elif isinstance(key, basestring):
            for tag in self.tags:
                if tag.name == key:
                    return True
            return False
        elif isinstance(key, TAG):
            return key in self.tags
        return False

    def __getitem__(self, key):
        if isinstance(key, int):
            return self.tags[key]
        elif isinstance(key, basestring):
            for tag in self.tags:
                if tag.name == key:
                    return tag
            else:
                raise KeyError("Tag %s does not exist" % key)
        else:
            raise TypeError("key needs to be either name of tag, or index of tag, not a %s" % type(key).__name__)

    def __setitem__(self, key, value):
        assert isinstance(value, TAG), "value must be an nbt.TAG"
        if isinstance(key, int):
            # Just try it. The proper error will be raised if it doesn't work.
            self.tags[key] = value
        elif isinstance(key, basestring):
            value.name = key
            for i, tag in enumerate(self.tags):
                if tag.name == key:
                    self.tags[i] = value
                    return
            self.tags.append(value)

    def __delitem__(self, key):
        if isinstance(key, int):
            del(self.tags[key])
        elif isinstance(key, basestring):
            self.tags.remove(self.__getitem__(key))
        else:
            raise ValueError("key needs to be either name of tag, or index of tag")

    def keys(self):
        return [tag.name for tag in self.tags]

    def iteritems(self):
        for tag in self.tags:
            yield (tag.name, tag)

    #Printing and Formatting of tree
    def __unicode__(self):
        return "{"+", ".join([tag.tag_info() for tag in self.tags])+"}"
    def __str__(self):
        return "{"+", ".join([tag.tag_info() for tag in self.tags])+"}"

    def valuestr(self):
        return '{%i Entries}' % len(self.tags)

    def pretty_tree(self, indent=0):
        output = [super(TAG_Compound, self).pretty_tree(indent)]
        if len(self.tags):
            output.append(("\t"*indent) + "{")
            output.extend([tag.pretty_tree(indent + 1) for tag in self.tags])
            output.append(("\t"*indent) + "}")
        return '\n'.join(output)


TAGLIST = {TAG_END: _TAG_End, TAG_BYTE:TAG_Byte, TAG_SHORT:TAG_Short, TAG_INT:TAG_Int, TAG_LONG:TAG_Long, TAG_FLOAT:TAG_Float, TAG_DOUBLE:TAG_Double, TAG_BYTE_ARRAY:TAG_Byte_Array, TAG_STRING:TAG_String, TAG_LIST:TAG_List, TAG_COMPOUND:TAG_Compound, TAG_INT_ARRAY:TAG_Int_Array}

class NBTFile(TAG_Compound):
    """Represent an NBT file object."""
    def __init__(self, filename=None, buffer=None, fileobj=None):
        super(NBTFile, self).__init__()
        self.filename = filename
        self.type = TAG_Byte(self.id)
        closefile = True
        #make a file object
        if filename:
            self.file = GzipFile(filename, 'rb')
        elif buffer:
            if hasattr(buffer, 'name'):
                self.filename = buffer.name
            self.file = buffer
            closefile = False
        elif fileobj:
            if hasattr(fileobj, 'name'):
                self.filename = fileobj.name
            self.file = GzipFile(fileobj=fileobj)
        else:
            self.file = None
            closefile = False
        #parse the file given initially
        if self.file:
            self.parse_file()
            if closefile:
                # Note: GzipFile().close() does NOT close the fileobj, 
                # So the caller is still responsible for closing that.
                try:
                    self.file.close()
                except (AttributeError, IOError):
                    pass
            self.file = None

    def parse_file(self, filename=None, buffer=None, fileobj=None):
        """Completely parse a file, extracting all tags."""
        if filename:
            self.file = GzipFile(filename, 'rb')
        elif buffer:
            if hasattr(buffer, 'name'):
                self.filename = buffer.name
            self.file = buffer
        elif fileobj:
            if hasattr(fileobj, 'name'):
                self.filename = fileobj.name
            self.file = GzipFile(fileobj=fileobj)
        if self.file:
            try:
                type = TAG_Byte(buffer=self.file)
                if type.value == self.id:
                    name = TAG_String(buffer=self.file).value
                    self._parse_buffer(self.file)
                    self.name = name
                    self.file.close()
                else:
                    raise MalformedFileError("First record is not a Compound Tag")
            except StructError as e:
                raise MalformedFileError("Partial File Parse: file possibly truncated.")
        else:
            raise ValueError("NBTFile.parse_file(): Need to specify either a filename or a file object")

    def write_file(self, filename=None, buffer=None, fileobj=None):
        """Write this NBT file to a file."""
        closefile = True
        if buffer:
            self.filename = None
            self.file = buffer
            closefile = False
        elif filename:
            self.filename = filename
            self.file = GzipFile(filename, "wb")
        elif fileobj:
            self.filename = None
            self.file = GzipFile(fileobj=fileobj, mode="wb")
        elif self.filename:
            self.file = GzipFile(self.filename, "wb")
        elif not self.file:
            raise ValueError("NBTFile.write_file(): Need to specify either a filename or a file object")
        #Render tree to file
        TAG_Byte(self.id)._render_buffer(self.file)
        TAG_String(self.name)._render_buffer(self.file)
        self._render_buffer(self.file)
        #make sure the file is complete
        try:
            self.file.flush()
        except (AttributeError, IOError):
            pass
        if closefile:
            try:
                self.file.close()
            except (AttributeError, IOError):
                pass

    def __repr__(self):
        """
        Return a string (ascii formated for Python 2, unicode
        for Python 3) describing the class, name and id for
        debugging purposes.
        """
        if self.filename:
            return "<%s(%r) with %s(%r) at 0x%x>" % (self.__class__.__name__, self.filename, \
                    TAG_Compound.__name__, self.name, id(self))
        else:
            return "<%s with %s(%r) at 0x%x>" % (self.__class__.__name__, \
                    TAG_Compound.__name__, self.name, id(self))

########NEW FILE########
__FILENAME__ = region
"""
Handle a region file, containing 32x32 chunks.
For more info of the region file format look:
http://www.minecraftwiki.net/wiki/Region_file_format
"""

from .nbt import NBTFile, MalformedFileError
from struct import pack, unpack
from gzip import GzipFile
from collections import Mapping
import zlib
import gzip
from io import BytesIO
import math, time
from os.path import getsize
from os import SEEK_END

# constants

SECTOR_LENGTH = 4096
"""Constant indicating the length of a sector. A Region file is divided in sectors of 4096 bytes each."""

# Status is a number representing:
# -5 = Error, the chunk is overlapping with another chunk
# -4 = Error, the chunk length is too large to fit in the sector length in the region header
# -3 = Error, chunk header has a 0 length
# -2 = Error, chunk inside the header of the region file
# -1 = Error, chunk partially/completely outside of file
#  0 = Ok
#  1 = Chunk non-existant yet
STATUS_CHUNK_OVERLAPPING = -5
"""Constant indicating an error status: the chunk is allocated a sector already occupied by another chunk"""
STATUS_CHUNK_MISMATCHED_LENGTHS = -4
"""Constant indicating an error status: the region header length and the chunk length are incompatible"""
STATUS_CHUNK_ZERO_LENGTH = -3
"""Constant indicating an error status: chunk header has a 0 length"""
STATUS_CHUNK_IN_HEADER = -2
"""Constant indicating an error status: chunk inside the header of the region file"""
STATUS_CHUNK_OUT_OF_FILE = -1
"""Constant indicating an error status: chunk partially/completely outside of file"""
STATUS_CHUNK_OK = 0
"""Constant indicating an normal status: the chunk exists and the metadata is valid"""
STATUS_CHUNK_NOT_CREATED = 1
"""Constant indicating an normal status: the chunk does not exist"""

COMPRESSION_NONE = 0
"""Constant indicating tha tthe chunk is not compressed."""
COMPRESSION_GZIP = 1
"""Constant indicating tha tthe chunk is GZip compressed."""
COMPRESSION_ZLIB = 2
"""Constant indicating tha tthe chunk is zlib compressed."""


# TODO: reconsider these errors. where are they catched? Where would an implementation make a difference in handling the different exceptions.

class RegionFileFormatError(Exception):
    """Base class for all file format errors.
    Note: InconceivedChunk is not a child class, because it is not considered a format error."""
    def __init__(self, msg=""):
        self.msg = msg
    def __str__(self):
        return self.msg

class NoRegionHeader(RegionFileFormatError):
    """The size of the region file is too small to contain a header."""

class RegionHeaderError(RegionFileFormatError):
    """Error in the header of the region file for a given chunk."""

class ChunkHeaderError(RegionFileFormatError):
    """Error in the header of a chunk, included the bytes of length and byte version."""

class ChunkDataError(RegionFileFormatError):
    """Error in the data of a chunk."""

class InconceivedChunk(LookupError):
    """Specified chunk has not yet been generated."""
    def __init__(self, msg=""):
        self.msg = msg


class ChunkMetadata(object):
    """
    Metadata for a particular chunk found in the 8 kiByte header and 5-byte chunk header.
    """

    def __init__(self, x, z):
        self.x = x
        """x-coordinate of the chunk in the file"""
        self.z = z
        """z-coordinate of the chunk in the file"""
        self.blockstart = 0
        """start of the chunk block, counted in 4 kiByte sectors from the
        start of the file. (24 bit int)"""
        self.blocklength = 0
        """amount of 4 kiBytes sectors in the block (8 bit int)"""
        self.timestamp = 0
        """a Unix timestamps (seconds since epoch) (32 bits), found in the
        second sector in the file."""
        self.length = 0
        """length of the block in bytes. This excludes the 4-byte length header,
        and includes the 1-byte compression byte. (32 bit int)"""
        self.compression = None
        """type of compression used for the chunk block. (8 bit int).
    
        - 0: uncompressed
        - 1: gzip compression
        - 2: zlib compression"""
        self.status = STATUS_CHUNK_NOT_CREATED
        """status as determined from blockstart, blocklength, length, file size
        and location of other chunks in the file.
        
        - STATUS_CHUNK_OVERLAPPING
        - STATUS_CHUNK_MISMATCHED_LENGTHS
        - STATUS_CHUNK_ZERO_LENGTH
        - STATUS_CHUNK_IN_HEADER
        - STATUS_CHUNK_OUT_OF_FILE
        - STATUS_CHUNK_OK
        - STATUS_CHUNK_NOT_CREATED"""
    def __str__(self):
        return "%s(%d, %d, sector=%s, length=%s, timestamp=%s, lenght=%s, compression=%s, status=%s)" % \
            (self.__class__.__name__, self.x, self.z, self.blockstart, self.blocklength, self.timestamp, \
            self.length, self.compression, self.status)
    def __repr__(self):
        return "%s(%d,%d)" % (self.__class__.__name__, self.x, self.z)
    def requiredblocks(self):
        # slightly faster variant of: floor(self.length + 4) / 4096))
        return (self.length + 3 + SECTOR_LENGTH) // SECTOR_LENGTH
    def is_created(self):
        """return True if this chunk is created according to the header.
        This includes chunks which are not readable for other reasons."""
        return self.blockstart != 0

class _HeaderWrapper(Mapping):
    """Wrapper around self.metadata to emulate the old self.header variable"""
    def __init__(self, metadata):
        self.metadata = metadata
    def __getitem__(self, xz):
        m = self.metadata[xz]
        return (m.blockstart, m.blocklength, m.timestamp, m.status)
    def __iter__(self):
        return iter(self.metadata) # iterates of the keys
    def __len__(self):
        return len(self.metadata)
class _ChunkHeaderWrapper(Mapping):
    """Wrapper around self.metadata to emulate the old self.chunk_headers variable"""
    def __init__(self, metadata):
        self.metadata = metadata
    def __getitem__(self, xz):
        m = self.metadata[xz]
        return (m.length if m.length > 0 else None, m.compression, m.status)
    def __iter__(self):
        return iter(self.metadata) # iterates of the keys
    def __len__(self):
        return len(self.metadata)

class RegionFile(object):
    """A convenience class for extracting NBT files from the Minecraft Beta Region Format."""
    
    # Redefine constants for backward compatibility.
    STATUS_CHUNK_OVERLAPPING = STATUS_CHUNK_OVERLAPPING
    """Constant indicating an error status: the chunk is allocated a sector
    already occupied by another chunk. 
    Deprecated. Use :const:`nbt.region.STATUS_CHUNK_OVERLAPPING` instead."""
    STATUS_CHUNK_MISMATCHED_LENGTHS = STATUS_CHUNK_MISMATCHED_LENGTHS
    """Constant indicating an error status: the region header length and the chunk
    length are incompatible. Deprecated. Use :const:`nbt.region.STATUS_CHUNK_MISMATCHED_LENGTHS` instead."""
    STATUS_CHUNK_ZERO_LENGTH = STATUS_CHUNK_ZERO_LENGTH
    """Constant indicating an error status: chunk header has a 0 length.
    Deprecated. Use :const:`nbt.region.STATUS_CHUNK_ZERO_LENGTH` instead."""
    STATUS_CHUNK_IN_HEADER = STATUS_CHUNK_IN_HEADER
    """Constant indicating an error status: chunk inside the header of the region file.
    Deprecated. Use :const:`nbt.region.STATUS_CHUNK_IN_HEADER` instead."""
    STATUS_CHUNK_OUT_OF_FILE = STATUS_CHUNK_OUT_OF_FILE
    """Constant indicating an error status: chunk partially/completely outside of file.
    Deprecated. Use :const:`nbt.region.STATUS_CHUNK_OUT_OF_FILE` instead."""
    STATUS_CHUNK_OK = STATUS_CHUNK_OK
    """Constant indicating an normal status: the chunk exists and the metadata is valid.
    Deprecated. Use :const:`nbt.region.STATUS_CHUNK_OK` instead."""
    STATUS_CHUNK_NOT_CREATED = STATUS_CHUNK_NOT_CREATED
    """Constant indicating an normal status: the chunk does not exist.
    Deprecated. Use :const:`nbt.region.STATUS_CHUNK_NOT_CREATED` instead."""
    
    def __init__(self, filename=None, fileobj=None):
        """
        Read a region file by filename of file object. 
        If a fileobj is specified, it is not closed after use; it is the callers responibility to close that.
        """
        self.file = None
        self.filename = None
        self._closefile = False
        if filename:
            self.filename = filename
            self.file = open(filename, 'r+b') # open for read and write in binary mode
            self._closefile = True
        elif fileobj:
            if hasattr(fileobj, 'name'):
                self.filename = fileobj.name
            self.file = fileobj
        elif not self.file:
            raise ValueError("RegionFile(): Need to specify either a filename or a file object")

        # Some variables
        self.metadata = {}
        """
        dict containing ChunkMetadata objects, gathered from metadata found in the
        8 kiByte header and 5-byte chunk header.
        
        ``metadata[x, z]: ChunkMetadata()``
        """
        self.header = _HeaderWrapper(self.metadata)
        """
        dict containing the metadata found in the 8 kiByte header:
        
        ``header[x, z]: (offset, sectionlength, timestamp, status)``
        
        :offset: counts in 4 kiByte sectors, starting from the start of the file. (24 bit int)
        :blocklength: is in 4 kiByte sectors (8 bit int)
        :timestamp: is a Unix timestamps (seconds since epoch) (32 bits)
        :status: can be any of:
        
            - STATUS_CHUNK_OVERLAPPING
            - STATUS_CHUNK_MISMATCHED_LENGTHS
            - STATUS_CHUNK_ZERO_LENGTH
            - STATUS_CHUNK_IN_HEADER
            - STATUS_CHUNK_OUT_OF_FILE
            - STATUS_CHUNK_OK
            - STATUS_CHUNK_NOT_CREATED
        
        Deprecated. Use :attr:`metadata` instead.
        """
        self.chunk_headers = _ChunkHeaderWrapper(self.metadata)
        """
        dict containing the metadata found in each chunk block:
        
        ``chunk_headers[x, z]: (length, compression, chunk_status)``
        
        :chunk length: in bytes, starting from the compression byte (32 bit int)
        :compression: is 1 (Gzip) or 2 (bzip) (8 bit int)
        :chunk_status: is equal to status in :attr:`header`.
        
        If the chunk is not defined, the tuple is (None, None, STATUS_CHUNK_NOT_CREATED)
        
        Deprecated. Use :attr:`metadata` instead.
        """

        self._init_header()
        self._parse_header()
        self._parse_chunk_headers()

    def get_size(self):
        """ Returns the file size in bytes. """
        # seek(0,2) jumps to 0-bytes from the end of the file.
        # Python 2.6 support: seek does not yet return the position.
        self.file.seek(0, SEEK_END)
        return self.file.tell()

    @staticmethod
    def _bytes_to_sector(bsize, sectorlength=SECTOR_LENGTH):
        """Given a size in bytes, return how many sections of length sectorlen are required to contain it.
        This is equivalent to ceil(bsize/sectorlen), if Python would use floating
        points for division, and integers for ceil(), rather than the other way around."""
        sectors, remainder = divmod(bsize, sectorlength)
        return sectors if remainder == 0 else sectors + 1
    
    def __del__(self):
        if self._closefile:
            self.file.close()
        # Parent object() has no __del__ method, otherwise it should be called here.

    def _init_file(self):
        """Initialise the file header. This will erase any data previously in the file."""
        header_length = 2*SECTOR_LENGTH
        if self.size > header_length:
            self.file.truncate(header_length)
        self.file.seek(0)
        self.file.write(header_length*b'\x00')
        self.size = header_length

    def _init_header(self):
        for x in range(32):
            for z in range(32):
                self.metadata[x,z] = ChunkMetadata(x, z)

    def _parse_header(self):
        """Read the region header and stores: offset, length and status."""
        # update the file size, needed when parse_header is called after
        # we have unlinked a chunk or writed a new one
        self.size = self.get_size()

        if self.size == 0:
            # Some region files seems to have 0 bytes of size, and
            # Minecraft handle them without problems. Take them
            # as empty region files.
            return
        elif self.size < 2*SECTOR_LENGTH:
            raise NoRegionHeader('The region file is %d bytes, too small in size to have a header.' % self.size)
        
        for index in range(0, SECTOR_LENGTH, 4):
            x = int(index//4) % 32
            z = int(index//4)//32
            m = self.metadata[x, z]
            
            self.file.seek(index)
            offset, length = unpack(">IB", b"\0"+self.file.read(4))
            m.blockstart, m.blocklength = offset, length
            self.file.seek(index + SECTOR_LENGTH)
            m.timestamp = unpack(">I", self.file.read(4))[0]
            
            if offset == 0 and length == 0:
                m.status = STATUS_CHUNK_NOT_CREATED
            elif length == 0:
                m.status = STATUS_CHUNK_ZERO_LENGTH
            elif offset < 2 and offset != 0:
                m.status = STATUS_CHUNK_IN_HEADER
            elif SECTOR_LENGTH * offset + 5 > self.size:
                # Chunk header can't be read.
                m.status = STATUS_CHUNK_OUT_OF_FILE
            else:
                m.status = STATUS_CHUNK_OK
        
        # Check for chunks overlapping in the file
        for chunks in self._sectors()[2:]:
            if len(chunks) > 1:
                # overlapping chunks
                for m in chunks:
                    # Update status, unless these more severe errors take precedence
                    if m.status not in (STATUS_CHUNK_ZERO_LENGTH, STATUS_CHUNK_IN_HEADER, 
                                        STATUS_CHUNK_OUT_OF_FILE):
                        m.status = STATUS_CHUNK_OVERLAPPING

    def _parse_chunk_headers(self):
        for x in range(32):
            for z in range(32):
                m = self.metadata[x, z]
                if m.status not in (STATUS_CHUNK_OK, STATUS_CHUNK_OVERLAPPING, \
                                    STATUS_CHUNK_MISMATCHED_LENGTHS):
                    continue
                try:
                    self.file.seek(m.blockstart*SECTOR_LENGTH) # offset comes in sectors of 4096 bytes
                    length = unpack(">I", self.file.read(4))
                    m.length = length[0] # unpack always returns a tuple, even unpacking one element
                    compression = unpack(">B",self.file.read(1))
                    m.compression = compression[0]
                except IOError:
                    m.status = STATUS_CHUNK_OUT_OF_FILE
                    continue
                if m.length <= 1: # chunk can't be zero length
                    m.status = STATUS_CHUNK_ZERO_LENGTH
                elif m.length + 4 > m.blocklength * SECTOR_LENGTH:
                    # There are not enough sectors allocated for the whole block
                    m.status = STATUS_CHUNK_MISMATCHED_LENGTHS

    def _sectors(self, ignore_chunk=None):
        """
        Return a list of all sectors, each sector is a list of chunks occupying the block.
        """
        sectorsize = self._bytes_to_sector(self.size)
        sectors = [[] for s in range(sectorsize)]
        sectors[0] = True # locations
        sectors[1] = True # timestamps
        for m in self.metadata.values():
            if not m.is_created():
                continue
            if ignore_chunk == m:
                continue
            if m.blocklength and m.blockstart:
                for b in range(m.blockstart, m.blockstart + max(m.blocklength, m.requiredblocks())):
                    if 2 <= b < sectorsize:
                        sectors[b].append(m)
        return sectors

    def _locate_free_sectors(self, ignore_chunk=None):
        """Return a list of booleans, indicating the free sectors."""
        sectors = self._sectors(ignore_chunk=ignore_chunk)
        # Sectors are considered free, if the value is an empty list.
        return [not i for i in sectors]

    def _find_free_location(self, free_locations, required_sectors=1, preferred=None):
        """
        Given a list of booleans, find a list of <required_sectors> consecutive True values.
        If no such list is found, return length(free_locations).
        Assumes first two values are always False.
        """
        # check preferred (current) location
        if preferred and all(free_locations[preferred:preferred+required_sectors]):
            return preferred
        
        # check other locations
        # Note: the slicing may exceed the free_location boundary.
        # This implementation relies on the fact that slicing will work anyway,
        # and the any() function returns True for an empty list. This ensures
        # that blocks outside the file are considered Free as well.
        
        i = 2 # First two sectors are in use by the header
        while i < len(free_locations):
            if all(free_locations[i:i+required_sectors]):
                break
            i += 1
        return i

    def get_metadata(self):
        """
        Return a list of the metadata of each chunk that is defined in te regionfile.
        This includes chunks which may not be readable for whatever reason,
        but excludes chunks that are not yet defined.
        """
        return [m for m in self.metadata.values() if m.is_created()]

    def get_chunks(self):
        """
        Return the x,z coordinates and length of the chunks that are defined in te regionfile.
        This includes chunks which may not be readable for whatever reason.

        Warning: despite the name, this function does not actually return the chunk,
        but merely it's metadata. Use get_chunk(x,z) to get the NBTFile, and then Chunk()
        to get the actual chunk.
        
        This method is deprecated. Use :meth:`get_metadata` instead.
        """
        return self.get_chunk_coords()

    def get_chunk_coords(self):
        """
        Return the x,z coordinates and length of the chunks that are defined in te regionfile.
        This includes chunks which may not be readable for whatever reason.
        
        This method is deprecated. Use :meth:`get_metadata` instead.
        """
        chunks = []
        for x in range(32):
            for z in range(32):
                m = self.metadata[x,z]
                if m.is_created():
                    chunks.append({'x': x, 'z': z, 'length': m.blocklength})
        return chunks

    def iter_chunks(self):
        """
        Yield each readable chunk present in the region.
        Chunks that can not be read for whatever reason are silently skipped.
        Warning: this function returns a :class:`nbt.nbt.NBTFile` object, use ``Chunk(nbtfile)`` to get a
        :class:`nbt.chunk.Chunk` instance.
        """
        for m in self.get_metadata():
            try:
                yield self.get_chunk(m.x, m.z)
            except RegionFileFormatError:
                pass
    
    def __iter__(self):
        return self.iter_chunks()

    def get_timestamp(self, x, z):
        """Return the timestamp of when this region file was last modified."""
        # TODO: raise an exception if chunk does not exist?
        # TODO: return a datetime.datetime object using datetime.fromtimestamp()
        return self.metadata[x,z].timestamp

    def chunk_count(self):
        """Return the number of defined chunks. This includes potentially corrupt chunks."""
        return len(self.get_metadata())

    def get_blockdata(self, x, z):
        """Return the decompressed binary data representing a chunk."""
        # read metadata block
        m = self.metadata[x, z]
        if m.status == STATUS_CHUNK_NOT_CREATED:
            raise InconceivedChunk("Chunk is not created")
        elif m.status == STATUS_CHUNK_IN_HEADER:
            raise RegionHeaderError('Chunk %d,%d is in the region header' % (x,z))
        elif m.status == STATUS_CHUNK_OUT_OF_FILE:
            raise RegionHeaderError('Chunk %d,%d is partially/completely outside the file' % (x,z))
        elif m.status == STATUS_CHUNK_ZERO_LENGTH:
            if m.blocklength == 0:
                raise RegionHeaderError('Chunk %d,%d has zero length' % (x,z))
            else:
                raise ChunkHeaderError('Chunk %d,%d has zero length' % (x,z))

        # status is STATUS_CHUNK_OK, STATUS_CHUNK_MISMATCHED_LENGTHS or STATUS_CHUNK_OVERLAPPING.
        # The chunk is always read, but in case of an error, the exception may be different 
        # based on the status.

        # offset comes in sectors of 4096 bytes + length bytes + compression byte
        self.file.seek(m.blockstart * SECTOR_LENGTH + 5)
        chunk = self.file.read(m.length-1) # the length in the file includes the compression byte

        err = None
        if m.compression > 2:
            raise ChunkDataError('Unknown chunk compression/format (%d)' % m.compression)
        try:
            if (m.compression == COMPRESSION_GZIP):
                # Python 3.1 and earlier do not yet support gzip.decompress(chunk)
                f = gzip.GzipFile(fileobj=BytesIO(chunk))
                chunk = bytes(f.read())
                f.close()
            elif (m.compression == COMPRESSION_ZLIB):
                chunk = zlib.decompress(chunk)
            return chunk
        except Exception as e:
            # Deliberately catch the Exception and re-raise.
            # The details in gzip/zlib/nbt are irrelevant, just that the data is garbled.
            err = str(e)
        if err:
            # don't raise during exception handling to avoid the warning 
            # "During handling of the above exception, another exception occurred".
            # Python 3.3 solution (see PEP 409 & 415): "raise ChunkDataError(str(e)) from None"
            if m.status == STATUS_CHUNK_MISMATCHED_LENGTHS:
                raise ChunkHeaderError('The length in region header and the length in the header of chunk %d,%d are incompatible' % (x,z))
            elif m.status == STATUS_CHUNK_OVERLAPPING:
                raise ChunkHeaderError('Chunk %d,%d is overlapping with another chunk' % (x,z))
            else:
                raise ChunkDataError(err)

    def get_nbt(self, x, z):
        """
        Return a NBTFile of the specified chunk.
        Raise InconceivedChunk if the chunk is not included in the file.
        """
        data = self.get_blockdata(x, z) # This may raise a RegionFileFormatError.
        data = BytesIO(data)
        err = None
        try:
            return NBTFile(buffer=data)
            # this may raise a MalformedFileError. Convert to ChunkDataError.
        except MalformedFileError as e:
            err = str(e)
        if err:
            raise ChunkDataError(err)

    def get_chunk(self, x, z):
        """
        Return a NBTFile of the specified chunk.
        Raise InconceivedChunk if the chunk is not included in the file.
        
        Note: this function may be changed later to return a Chunk() rather 
        than a NBTFile() object. To keep the old functionality, use get_nbt().
        """
        return self.get_nbt(x, z)

    def write_blockdata(self, x, z, data):
        """
        Compress the data, write it to file, and add pointers in the header so it 
        can be found as chunk(x,z).
        """
        data = zlib.compress(data) # use zlib compression, rather than Gzip
        length = len(data)

        # 5 extra bytes are required for the chunk block header
        nsectors = self._bytes_to_sector(length + 5)

        if nsectors >= 256:
            raise ChunkDataError("Chunk is too large (%d sectors exceeds 255 maximum)" % (nsectors))

        # Ensure file has a header
        if self.size < 2*SECTOR_LENGTH:
            self._init_file()

        # search for a place where to write the chunk:
        current = self.metadata[x, z]
        free_sectors = self._locate_free_sectors(ignore_chunk=current)
        sector = self._find_free_location(free_sectors, nsectors, preferred=current.blockstart)

        # write out chunk to region
        self.file.seek(sector*SECTOR_LENGTH)
        self.file.write(pack(">I", length + 1)) #length field
        self.file.write(pack(">B", COMPRESSION_ZLIB)) #compression field
        self.file.write(data) #compressed data

        # Write zeros up to the end of the chunk
        remaining_length = SECTOR_LENGTH * nsectors - length - 5
        self.file.write(remaining_length * b"\x00")

        #seek to header record and write offset and length records
        self.file.seek(4 * (x + 32*z))
        self.file.write(pack(">IB", sector, nsectors)[1:])

        #write timestamp
        self.file.seek(SECTOR_LENGTH + 4 * (x + 32*z))
        timestamp = int(time.time())
        self.file.write(pack(">I", timestamp))

        # Update free_sectors with newly written block
        # This is required for calculating file truncation and zeroing freed blocks.
        free_sectors.extend((sector + nsectors - len(free_sectors)) * [True])
        for s in range(sector, sector + nsectors):
            free_sectors[s] = False
        
        # Check if file should be truncated:
        truncate_count = list(reversed(free_sectors)).index(False)
        if truncate_count > 0:
            self.size = SECTOR_LENGTH * (len(free_sectors) - truncate_count)
            self.file.truncate(self.size)
            free_sectors = free_sectors[:-truncate_count]
        
        # Calculate freed sectors
        for s in range(current.blockstart, min(current.blockstart + current.blocklength, len(free_sectors))):
            if free_sectors[s]:
                # zero sector s
                self.file.seek(SECTOR_LENGTH*s)
                self.file.write(SECTOR_LENGTH*b'\x00')
        
        # update file size and header information
        self.size = self.get_size()
        current.blockstart = sector
        current.blocklength = nsectors
        current.status = STATUS_CHUNK_OK
        current.timestamp = timestamp
        current.length = length + 1
        current.compression = COMPRESSION_ZLIB

        # self.parse_header()
        # self.parse_chunk_headers()

    def write_chunk(self, x, z, nbt_file):
        """
        Pack the NBT file as binary data, and write to file in a compressed format.
        """
        data = BytesIO()
        nbt_file.write_file(buffer=data) # render to buffer; uncompressed
        self.write_blockdata(x, z, data.getvalue())

    def unlink_chunk(self, x, z):
        """
        Remove a chunk from the header of the region file.
        Fragmentation is not a problem, chunks are written to free sectors when possible.
        """
        # This function fails for an empty file. If that is the case, just return.
        if self.size < 2*SECTOR_LENGTH:
            return

        # zero the region header for the chunk (offset length and time)
        self.file.seek(4 * (x + 32*z))
        self.file.write(pack(">IB", 0, 0)[1:])
        self.file.seek(SECTOR_LENGTH + 4 * (x + 32*z))
        self.file.write(pack(">I", 0))

        # Check if file should be truncated:
        current = self.metadata[x, z]
        free_sectors = self._locate_free_sectors(ignore_chunk=current)
        truncate_count = list(reversed(free_sectors)).index(False)
        if truncate_count > 0:
            self.size = SECTOR_LENGTH * (len(free_sectors) - truncate_count)
            self.file.truncate(self.size)
            free_sectors = free_sectors[:-truncate_count]
        
        # Calculate freed sectors
        for s in range(current.blockstart, min(current.blockstart + current.blocklength, len(free_sectors))):
            if free_sectors[s]:
                # zero sector s
                self.file.seek(SECTOR_LENGTH*s)
                self.file.write(SECTOR_LENGTH*b'\x00')

        # update the header
        self.metadata[x, z] = ChunkMetadata(x, z)

    def _classname(self):
        """Return the fully qualified class name."""
        if self.__class__.__module__ in (None,):
            return self.__class__.__name__
        else:
            return "%s.%s" % (self.__class__.__module__, self.__class__.__name__)

    def __str__(self):
        if self.filename:
            return "<%s(%r)>" % (self._classname(), self.filename)
        else:
            return '<%s object at %d>' % (self._classname(), id(self))
    
    def __repr__(self):
        if self.filename:
            return "%s(%r)" % (self._classname(), self.filename)
        else:
            return '<%s object at %d>' % (self._classname(), id(self))

########NEW FILE########
__FILENAME__ = world
"""
Handles a Minecraft world save using either the Anvil or McRegion format.
"""

import os, glob, re
from . import region
from . import chunk
from .region import InconceivedChunk

class UnknownWorldFormat(Exception):
    """Unknown or invalid world folder."""
    def __init__(self, msg=""):
        self.msg = msg



class _BaseWorldFolder(object):
    """
    Abstract class, representing either a McRegion or Anvil world folder.
    This class will use either Anvil or McRegion, with Anvil the preferred format.
    Simply calling WorldFolder() will do this automatically.
    """
    type = "Generic"

    def __init__(self, world_folder):
        """Initialize a WorldFolder."""
        self.worldfolder = world_folder
        self.regionfiles = {}
        self.regions     = {}
        self.chunks  = None
        # os.listdir triggers an OSError for non-existant directories or permission errors.
        # This is needed, because glob.glob silently returns no files.
        os.listdir(world_folder)
        self.set_regionfiles(self.get_filenames())

    def get_filenames(self):
        # Warning: glob returns a empty list if the directory is unreadable, without raising an Exception
        return list(glob.glob(os.path.join(self.worldfolder,'region','r.*.*.'+self.extension)))

    def set_regionfiles(self, filenames):
        """
        This method directly sets the region files for this instance to use.
        It assumes the filenames are in the form r.<x-digit>.<z-digit>.<extension>
        """
        for filename in filenames:
            # Assume that filenames have the name r.<x-digit>.<z-digit>.<extension>
            m = re.match(r"r.(\-?\d+).(\-?\d+)."+self.extension, os.path.basename(filename))
            if m:
                x = int(m.group(1))
                z = int(m.group(2))
            else:
                # Only raised if a .mca of .mcr file exists which does not comply to the
                #  r.<x-digit>.<z-digit>.<extension> filename format. This may raise false
                # errors if a copy is made, e.g. "r.0.-1 copy.mca". If this is an issue, override
                # get_filenames(). In most cases, it is an error, and we like to raise that.
                # Changed, no longer raise error, because we want to continue the loop.
                # raise UnknownWorldFormat("Unrecognized filename format %s" % os.path.basename(filename))
                # TODO: log to stderr using logging facility.
                pass
            self.regionfiles[(x,z)] = filename

    def nonempty(self):
        """Return True is the world is non-empty."""
        return len(self.regionfiles) > 0

    def get_regionfiles(self):
        """Return a list of full path of all region files."""
        return list(self.regionfiles.values())

    def get_region(self, x,z):
        """Get a region using x,z coordinates of a region. Cache results."""
        if (x,z) not in self.regions:
            if (x,z) in self.regionfiles:
                self.regions[(x,z)] = region.RegionFile(self.regionfiles[(x,z)])
            else:
                # Return an empty RegionFile object
                # TODO: this does not yet allow for saving of the region file
                self.regions[(x,z)] = region.RegionFile()
        return self.regions[(x,z)]

    def iter_regions(self):
        for x,z in self.regionfiles.keys():
            yield self.get_region(x,z)

    def iter_nbt(self):
        """
        Return an iterable list of all NBT. Use this function if you only
        want to loop through the chunks once, and don't need the block or data arrays.
        """
        # TODO: Implement BoundingBox
        # TODO: Implement sort order
        for region in self.iter_regions():
            for c in region.iter_chunks():
                yield c

    def iter_chunks(self):
        """
        Return an iterable list of all chunks. Use this function if you only
        want to loop through the chunks once or have a very large world.
        Use get_chunks() if you access the chunk list frequently and want to cache
        the results. Use iter_nbt() if you are concerned about speed and don't want
        to parse the block data.
        """
        # TODO: Implement BoundingBox
        # TODO: Implement sort order
        for c in self.iter_nbt():
            yield self.chunkclass(c)

    def get_nbt(self,x,z):
        """
        Return a NBT specified by the chunk coordinates x,z. Raise InconceivedChunk
        if the NBT file is not yet generated. To get a Chunk object, use get_chunk.
        """
        rx,x = divmod(x,32)
        rz,z = divmod(z,32)
        nbt = self.get_region(rx,rz).get_chunk(x,z)
        if nbt == None:
            raise InconceivedChunk("Chunk %s,%s not present in world" % (32*rx+x,32*rz+z))
        return nbt

    def set_nbt(self,x,z,nbt):
        """
        Set a chunk. Overrides the NBT if it already existed. If the NBT did not exists,
        adds it to the Regionfile. May create a new Regionfile if that did not exist yet.
        nbt must be a nbt.NBTFile instance, not a Chunk or regular TAG_Compound object.
        """
        raise NotImplemented()
        # TODO: implement

    def get_chunk(self,x,z):
        """
        Return a chunk specified by the chunk coordinates x,z. Raise InconceivedChunk
        if the chunk is not yet generated. To get the raw NBT data, use get_nbt.
        """
        return self.chunkclass(self.get_nbt(x, z))

    def get_chunks(self, boundingbox=None):
        """
        Return a list of all chunks. Use this function if you access the chunk
        list frequently and want to cache the result.
        Use iter_chunks() if you only want to loop through the chunks once or have a
        very large world.
        """
        if self.chunks == None:
            self.chunks = list(self.iter_chunks())
        return self.chunks

    def chunk_count(self):
        """Return a count of the chunks in this world folder."""
        c = 0
        for r in self.iter_regions():
            c += r.chunk_count()
        return c

    def get_boundingbox(self):
        """
        Return minimum and maximum x and z coordinates of the chunks that
        make up this world save
        """
        b = BoundingBox()
        for rx,rz in self.regionfiles.keys():
            region = self.get_region(rx,rz)
            rx,rz = 32*rx,32*rz
            for cc in region.get_chunk_coords():
                x,z = (rx+cc['x'],rz+cc['z'])
                b.expand(x,None,z)
        return b

    def cache_test(self):
        """
        Debug routine: loop through all chunks, fetch them again by coordinates,
        and check if the same object is returned.
        """
        # TODO: make sure this test succeeds (at least True,True,False, preferable True,True,True)
        # TODO: Move this function to test class.
        for rx,rz in self.regionfiles.keys():
            region = self.get_region(rx,rz)
            rx,rz = 32*rx,32*rz
            for cc in region.get_chunk_coords():
                x,z = (rx+cc['x'],rz+cc['z'])
                c1 = self.chunkclass(region.get_chunk(cc['x'],cc['z']))
                c2 = self.get_chunk(x,z)
                correct_coords = (c2.get_coords() == (x,z))
                is_comparable = (c1 == c2) # test __eq__ function
                is_equal = (id(c1) == id(c2)) # test if they point to the same memory location
                # DEBUG (prints a tuple)
                print((x,z,c1,c2,correct_coords,is_comparable,is_equal))

    def __repr__(self):
        return "%s(%r)" % (self.__class__.__name__,self.worldfolder)


class McRegionWorldFolder(_BaseWorldFolder):
    """Represents a world save using the old McRegion format."""
    type = "McRegion"
    extension = 'mcr'
    chunkclass = chunk.Chunk
    # chunkclass = chunk.McRegionChunk  # TODO: change to McRegionChunk when done

class AnvilWorldFolder(_BaseWorldFolder):
    """Represents a world save using the new Anvil format."""
    type = "Anvil"
    extension = 'mca'
    chunkclass = chunk.Chunk
    # chunkclass = chunk.AnvilChunk  # TODO: change to AnvilChunk when done


class _WorldFolderFactory():
    """Factory class: instantiate the subclassses in order, and the first instance 
    whose nonempty() method returns True is returned. If no nonempty() returns True,
    a UnknownWorldFormat exception is raised."""
    def __init__(self, subclasses):
        self.subclasses = subclasses
    def __call__(self, *args, **kwargs):
        for cls in self.subclasses:
            wf = cls(*args, **kwargs)
            if wf.nonempty(): # Check if the world is non-empty
                return wf
        raise UnknownWorldFormat("Empty world or unknown format: %r" % world_folder)

WorldFolder = _WorldFolderFactory([AnvilWorldFolder, McRegionWorldFolder])
"""
Factory instance that returns a AnvilWorldFolder or McRegionWorldFolder
instance, or raise a UnknownWorldFormat.
"""



class BoundingBox(object):
    """A bounding box of x,y,z coordinates."""
    def __init__(self, minx=None, maxx=None, miny=None, maxy=None, minz=None, maxz=None):
        self.minx,self.maxx = minx, maxx
        self.miny,self.maxy = miny, maxy
        self.minz,self.maxz = minz, maxz
    def expand(self,x,y,z):
        """
        Expands the bounding
        """
        if x != None:
            if self.minx is None or x < self.minx:
                self.minx = x
            if self.maxx is None or x > self.maxx:
                self.maxx = x
        if y != None:
            if self.miny is None or y < self.miny:
                self.miny = y
            if self.maxy is None or y > self.maxy:
                self.maxy = y
        if z != None:
            if self.minz is None or z < self.minz:
                self.minz = z
            if self.maxz is None or z > self.maxz:
                self.maxz = z
    def lenx(self):
        return self.maxx-self.minx+1
    def leny(self):
        return self.maxy-self.miny+1
    def lenz(self):
        return self.maxz-self.minz+1
    def __repr__(self):
        return "%s(%s,%s,%s,%s,%s,%s)" % (self.__class__.__name__,self.minx,self.maxx,
                self.miny,self.maxy,self.minz,self.maxz)

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
    def format_time(self, seconds):
        return time.strftime('%H:%M:%S', time.gmtime(seconds))
    def update(self, pbar):
        if pbar.currval == 0:
            return 'ETA:  --:--:--'
        elif pbar.finished:
            return 'Time: %s' % self.format_time(pbar.seconds_elapsed)
        else:
            elapsed = pbar.seconds_elapsed
            eta = elapsed * pbar.maxval / pbar.currval - elapsed
            return 'ETA:  %s' % self.format_time(eta)

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
    def update(self, pbar):
        return '%3d%%' % pbar.percentage()

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
                self.signal_set = True
            except:
                self.term_width = 79
        else:
            self.term_width = term_width

        self.currval = 0
        self.finished = False
        self.prev_percentage = -1
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
        return int(self.percentage()) != int(self.prev_percentage)

    def update(self, value):
        "Updates the progress bar to a new value."
        assert 0 <= value <= self.maxval
        self.currval = value
        if not self._need_update() or self.finished:
            return
        if not self.start_time:
            self.start_time = time.time()
        self.seconds_elapsed = time.time() - self.start_time
        self.prev_percentage = self.percentage()
        if value != self.maxval:
            self.fd.write(self._format_line() + '\r')
        else:
            self.finished = True
            self.fd.write(self._format_line() + '\n')

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
__FILENAME__ = region-fixer
#!/usr/bin/env python
# -*- coding: utf-8 -*-

#
#   Region Fixer.
#   Fix your region files with a backup copy of your Minecraft world.
#   Copyright (C) 2011  Alejandro Aguilera (Fenixin)
#   https://github.com/Fenixin/Minecraft-Region-Fixer
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

from multiprocessing import freeze_support
from optparse import OptionParser, OptionGroup
from getpass import getpass
import sys

import world
from scan import scan_regionset, scan_world
from interactive import interactive_loop
from util import entitle, is_bare_console, parse_world_list, parse_paths, parse_backup_list

def delete_bad_chunks(options, scanned_obj):
    """ Takes a scanned object (world object or regionset object) and 
    the options given to region-fixer, it deletes all the chunks with
    problems iterating through all the possible problems. """
    print # a blank line
    options_delete = [options.delete_corrupted, options.delete_wrong_located, options.delete_entities, options.delete_shared_offset]
    deleting = zip(options_delete, world.CHUNK_PROBLEMS)
    for delete, problem in deleting:
        status = world.CHUNK_STATUS_TEXT[problem]
        total = scanned_obj.count_chunks(problem)
        if delete:
            if total:
                text = ' Deleting chunks with status: {0} '.format(status)
                print "{0:#^60}".format(text)
                counter = scanned_obj.remove_problematic_chunks(problem)

                print "\nDeleted {0} chunks with status: {1}".format(counter,status)
            else:
                print "No chunks to delete with status: {0}".format(status)

def delete_bad_regions(options, scanned_obj):
    """ Takes an scanned object (world object or regionset object) and 
    the options give to region-fixer, it deletes all the region files
    with problems iterating through all the possible problems. """
    print # a blank line
    options_delete = [options.delete_too_small]
    deleting = zip(options_delete, world.REGION_PROBLEMS)
    for delete, problem in deleting:
        status = world.REGION_STATUS_TEXT[problem]
        total = scanned_obj.count_regions(problem)
        if delete:
            if total:
                text = ' Deleting regions with status: {0} '.format(status)
                print "{0:#^60}".format(text)
                counter = scanned_obj.remove_problematic_regions(problem)

                print "Deleted {0} regions with status: {1}".format(counter,status)
            else:
                print "No regions to delete with status: {0}".format(status)

def main():

    usage = 'usage: %prog [options] <world-path> <other-world-path> ... <region-files> ...'
    epilog = 'Copyright (C) 2011  Alejandro Aguilera (Fenixin) \
    https://github.com/Fenixin/Minecraft-Region-Fixer                                        \
    This program comes with ABSOLUTELY NO WARRANTY; for details see COPYING.txt. This is free software, and you are welcome to redistribute it under certain conditions; see COPYING.txt for details.'

    parser = OptionParser(description='Script to check the integrity of Minecraft worlds and fix them when possible. It uses NBT by twoolie. Author: Alejandro Aguilera (Fenixin)',\
    prog = 'region-fixer', version='0.1.3', usage=usage, epilog=epilog)

    parser.add_option('--backups', '-b', help = 'List of backup directories of the Minecraft world to use to fix corrupted chunks and/or wrong located chunks. Warning! Region-Fixer is not going to check if it\'s the same world, be careful! This argument can be a comma separated list (but never with spaces between elements!). This option can be only used scanning one world.',\
        metavar = '<backups>', type = str, dest = 'backups', default = None)

    parser.add_option('--replace-corrupted','--rc', help = 'Tries to replace the corrupted chunks using the backup directories. This option can be only used scanning one world.',\
        default = False, dest = 'replace_corrupted', action='store_true')

    parser.add_option('--replace-wrong-located','--rw', help = 'Tries to replace the wrong located chunks using the backup directories. This option can be only used scanning one world.',\
        default = False, dest = 'replace_wrong_located', action='store_true')

    parser.add_option('--replace-entities','--re', help = 'Tries to replace the chunks with too many entities using the backup directories. This option can be only used scanning one world.',\
        default = False, dest = 'replace_entities', action='store_true')

    parser.add_option('--replace-shared-offset','--rs', help = 'Tries to replace the chunks with a shared offset using the backup directories. This option can be only used scanning one world.',\
        default = False, dest = 'replace_shared_offset', action='store_true')

    parser.add_option('--replace-too-small','--rt', help = 'Tries to replace the region files that are too small to be actually be a region file using the backup directories. This option can be only used scanning one world.',\
        default = False, dest = 'replace_too_small', action='store_true')

    parser.add_option('--delete-corrupted', '--dc', help = '[WARNING!] This option deletes! This option will delete all the corrupted chunks. Used with --replace-corrupted or --replace-wrong-located it will delete all the non-replaced chunks.',\
        action = 'store_true', default = False)

    parser.add_option('--delete-wrong-located', '--dw', help = '[WARNING!] This option deletes! The same as --delete-corrupted but for wrong located chunks',\
        action = 'store_true', default = False, dest='delete_wrong_located')

    parser.add_option('--delete-entities', '--de', help = '[WARNING!] This option deletes! This option deletes ALL the entities in chunks with more entities than --entity-limit (300 by default). In a Minecraft entities are mostly mobs and items dropped in the grond, items in chests and other stuff won\'t be touched. Read the README for more info. Region-Fixer will delete the entities while scanning so you can stop and resume the process',\
        action = 'store_true', default = False, dest = 'delete_entities')

    parser.add_option('--delete-shared-offset', '--ds', help = '[WARNING!] This option deletes! This option will delete all the chunk with status shared offset. It will remove the region header for the false chunk, note that you don\'t loos any chunk doing this.',\
        action = 'store_true', default = False, dest = 'delete_shared_offset')

    parser.add_option('--delete-too-small', '--dt', help = '[WARNING!] This option deletes! Removes any region files found to be too small to actually be a region file.',\
        dest ='delete_too_small', default = False, action = 'store_true')

    parser.add_option('--entity-limit', '--el', help = 'Specify the limit for the --delete-entities option (default = 300).',\
        dest = 'entity_limit', default = 300, action = 'store', type = int)

    parser.add_option('--processes', '-p',  help = 'Set the number of workers to use for scanning. (defaulta = 1, not use multiprocessing at all)',\
        action = 'store', type = int, default = 1)

    parser.add_option('--verbose', '-v', help='Don\'t use a progress bar, instead print a line per scanned region file with results information. The letters mean c: corrupted; w: wrong located; t: total of chunksm; tme: too many entities problem',\
        action='store_true', default = False)

    parser.add_option('--interactive', '-i',help='Enter in interactive mode, where you can scan, see the problems, and fix them in a terminal like mode',\
        dest = 'interactive',default = False, action='store_true',)

    parser.add_option('--log', '-l',help='Saves a log of all the problems found in the spicifyed file. The log file contains all the problems found with this information: region file, chunk coordinates and problem. Use \'-\' as name to show the log at the end of the scan.',\
        type = str, default = None, dest = 'summary')

    (options, args) = parser.parse_args()

    if is_bare_console():
        print
        print "Minecraft Region Fixer is a command line aplication, if you want to run it"
        print "you need to open a command line (cmd.exe in the start menu in windows 7)."
        print 
        getpass("Press enter to continue:")
        return 1

    # Args are world_paths and region files
    if not args:
        parser.error("No world paths or region files specified! Use --help for a complete list of options.")

    world_list, region_list = parse_paths(args)

    if not (world_list or region_list):
        print ("Error: No worlds or region files to scan!")
        return 1

    # Check basic options compatibilities
    any_chunk_replace_option = options.replace_corrupted or options.replace_wrong_located or options.replace_entities or options.replace_shared_offset
    any_chunk_delete_option = options.delete_corrupted or options.delete_wrong_located or options.delete_entities or options.delete_shared_offset
    any_region_replace_option = options.replace_too_small
    any_region_delete_option = options.delete_too_small

    if options.interactive or options.summary:
        if any_chunk_replace_option or any_region_replace_option:
            parser.error("Can't use the options --replace-* , --delete-* and --log with --interactive. You can choose all this while in the interactive mode.")

    else: # not options.interactive
        if options.backups:
            if not any_chunk_replace_option and not any_region_replace_option:
                parser.error("The option --backups needs at least one of the --replace-* options")
            else:
                if (len(region_list.regions) > 0):
                    parser.error("You can't use the replace options while scanning sparate region files. The input should be only one world and you intruduced {0} individual region files.".format(len(region_list.regions)))
                elif (len(world_list) > 1):
                    parser.error("You can't use the replace options while scanning multiple worlds. The input should be only one world and you intruduced {0} worlds.".format(len(world_list)))

        if not options.backups and any_chunk_replace_option:
            parser.error("The options --replace-* need the --backups option")

    if options.entity_limit < 0:
        parser.error("The entity limit must be at least 0!")

    print "\nWelcome to Region Fixer!"
    print "(version: {0})".format(parser.version)

    # do things with the option options args
    if options.backups: # create a list of worlds containing the backups of the region files
        backup_worlds = parse_backup_list(options.backups)
        if not backup_worlds:
            print "[WARNING] No valid backup directories found, won't fix any chunk."
    else:
        backup_worlds = []


    # The program starts
    if options.interactive:
        # TODO: WARNING, NEEDS CHANGES FOR WINDOWS. check while making the windows exe
        c = interactive_loop(world_list, region_list, options, backup_worlds)
        c.cmdloop()

    else:
        summary_text = ""
        # scan the separate region files
        if len(region_list.regions) > 0:
            print entitle("Scanning separate region files", 0)
            scan_regionset(region_list, options)

            print region_list.generate_report(True)
            
            # delete chunks
            delete_bad_chunks(options, region_list)

            # delete region files
            delete_bad_regions(options, region_list)

            # verbose log
            if options.summary:
                summary_text += "\n"
                summary_text += entitle("Separate region files")
                summary_text += "\n"
                t = region_list.summary()
                if t:
                    summary_text += t
                else:
                    summary_text += "No problems found.\n\n"

        # scan all the world folders
        for world_obj in world_list:
            print entitle(' Scanning world: {0} '.format(world_obj.get_name()),0)

            scan_world(world_obj, options)
            
            print world_obj.generate_report(standalone = True)
            corrupted, wrong_located, entities_prob, shared_prob, total_chunks, too_small_region, unreadable_region, total_regions = world_obj.generate_report(standalone = False)
            print 
            
            # replace chunks
            if backup_worlds and not len(world_list) > 1:
                options_replace = [options.replace_corrupted, options.replace_wrong_located, options.replace_entities, options.replace_shared_offset]
                replacing = zip(options_replace, world.CHUNK_PROBLEMS_ITERATOR)
                for replace, (problem, status, arg) in replacing:
                    if replace:
                        total = world_obj.count_chunks(problem)
                        if total:
                            text = " Replacing chunks with status: {0} ".format(status)
                            print "{0:#^60}".format(text)
                            fixed = world_obj.replace_problematic_chunks(backup_worlds, problem, options)
                            print "\n{0} replaced of a total of {1} chunks with status: {2}".format(fixed, total, status)
                        else: print "No chunks to replace with status: {0}".format(status)

            elif any_chunk_replace_option and not backup_worlds:
                print "Info: Won't replace any chunk."
                print "No backup worlds found, won't replace any chunks/region files!"
            elif any_chunk_replace_option and backup_worlds and len(world_list) > 1:
                print "Info: Won't replace any chunk."
                print "Can't use the replace options while scanning more than one world!"

            # replace region files
            if backup_worlds and not len(world_list) > 1:
                options_replace = [options.replace_too_small]
                replacing = zip(options_replace, world.REGION_PROBLEMS_ITERATOR)
                for replace, (problem, status, arg) in replacing:
                    if replace:
                        total = world_obj.count_regions(problem)
                        if total:
                            text = " Replacing regions with status: {0} ".format(status)
                            print "{0:#^60}".format(text)
                            fixed = world_obj.replace_problematic_regions(backup_worlds, problem, options)
                            print "\n{0} replaced of a total of {1} regions with status: {2}".format(fixed, total, status)
                        else: print "No region to replace with status: {0}".format(status)

            elif any_region_replace_option and not backup_worlds:
                print "Info: Won't replace any regions."
                print "No valid backup worlds found, won't replace any chunks/region files!"
                print "Note: You probably inserted some backup worlds with the backup option but they are probably no valid worlds, the most common issue is wrong path."
            elif any_region_replace_option and backup_worlds and len(world_list) > 1:
                print "Info: Won't replace any regions."
                print "Can't use the replace options while scanning more than one world!"

            # delete chunks
            delete_bad_chunks(options, world_obj)
            
            # delete region files
            delete_bad_regions(options, world_obj)

            # print a summary for this world
            if options.summary:
                summary_text += world_obj.summary()

        # verbose log text
        if options.summary == '-':
            print "\nPrinting log:\n"
            print summary_text
        elif options.summary != None:
            try:
                f = open(options.summary, 'w')
                f.write(summary_text)
                f.write('\n')
                f.close()
                print "Log file saved in \'{0}\'.".format(options.summary)
            except:
                print "Something went wrong while saving the log file!"

    return 0


if __name__ == '__main__':
    freeze_support()
    value = main()
    sys.exit(value)

########NEW FILE########
__FILENAME__ = scan
#!/usr/bin/env python
# -*- coding: utf-8 -*-

#
#   Region Fixer.
#   Fix your region files with a backup copy of your Minecraft world.
#   Copyright (C) 2011  Alejandro Aguilera (Fenixin)
#   https://github.com/Fenixin/Minecraft-Region-Fixer
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import nbt.region as region
import nbt.nbt as nbt
#~ from nbt.region import STATUS_CHUNK_OVERLAPPING, STATUS_CHUNK_MISMATCHED_LENGTHS
        #~ - STATUS_CHUNK_ZERO_LENGTH
        #~ - STATUS_CHUNK_IN_HEADER
        #~ - STATUS_CHUNK_OUT_OF_FILE
        #~ - STATUS_CHUNK_OK
        #~ - STATUS_CHUNK_NOT_CREATED
from os.path import split, join
import progressbar
import multiprocessing
from multiprocessing import queues
import world
import time

import sys
import traceback

class ChildProcessException(Exception):
    """Takes the child process traceback text and prints it as a
    real traceback with asterisks everywhere."""
    def __init__(self, error):
        # Helps to see wich one is the child process traceback
        traceback = error[2]
        print "*"*10
        print "*** Error while scanning:"
        print "*** ", error[0]
        print "*"*10
        print "*** Printing the child's Traceback:"
        print "*** Exception:", traceback[0], traceback[1]
        for tb in traceback[2]:
            print "*"*10
            print "*** File {0}, line {1}, in {2} \n***   {3}".format(*tb)
        print "*"*10

class FractionWidget(progressbar.ProgressBarWidget):
    """ Convenience class to use the progressbar.py """
    def __init__(self, sep=' / '):
        self.sep = sep

    def update(self, pbar):
        return '%2d%s%2d' % (pbar.currval, self.sep, pbar.maxval)

def scan_world(world_obj, options):
    """ Scans a world folder including players, region folders and
        level.dat. While scanning prints status messages. """
    w = world_obj
    # scan the world dir
    print "Scanning directory..."

    if not w.scanned_level.path:
        print "Warning: No \'level.dat\' file found!"

    if w.players:
        print "There are {0} region files and {1} player files in the world directory.".format(\
            w.get_number_regions(), len(w.players))
    else:
        print "There are {0} region files in the world directory.".format(\
            w.get_number_regions())

    # check the level.dat file and the *.dat files in players directory
    print "\n{0:-^60}".format(' Checking level.dat ')

    if not w.scanned_level.path:
        print "[WARNING!] \'level.dat\' doesn't exist!"
    else:
        if w.scanned_level.readable == True:
            print "\'level.dat\' is readable"
        else:
            print "[WARNING!]: \'level.dat\' is corrupted with the following error/s:"
            print "\t {0}".format(w.scanned_level.status_text)

    print "\n{0:-^60}".format(' Checking player files ')
    # TODO multiprocessing!
    # Probably, create a scanner object with a nice buffer of logger for text and logs and debugs
    if not w.players:
        print "Info: No player files to scan."
    else:
        scan_all_players(w)
        all_ok = True
        for name in w.players:
            if w.players[name].readable == False:
                print "[WARNING]: Player file {0} has problems.\n\tError: {1}".format(w.players[name].filename, w.players[name].status_text)
                all_ok = False
        if all_ok:
            print "All player files are readable."

    # SCAN ALL THE CHUNKS!
    if w.get_number_regions == 0:
        print "No region files to scan!"
    else:
        for r in w.regionsets:
            if r.regions:
                print "\n{0:-^60}".format(' Scanning the {0} '.format(r.get_name()))
                scan_regionset(r, options)
    w.scanned = True


def scan_player(scanned_dat_file):
    """ At the moment only tries to read a .dat player file. It returns
    0 if it's ok and 1 if has some problem """

    s = scanned_dat_file
    try:
        player_dat = nbt.NBTFile(filename = s.path)
        s.readable = True
    except Exception, e:
        s.readable = False
        s.status_text = e


def scan_all_players(world_obj):
    """ Scans all the players using the scan_player function. """

    for name in world_obj.players:
        scan_player(world_obj.players[name])


def scan_region_file(scanned_regionfile_obj, options):
    """ Given a scanned region file object with the information of a 
        region files scans it and returns the same obj filled with the
        results.
        
        If delete_entities is True it will delete entities while
        scanning
        
        entiti_limit is the threshold tof entities to conisder a chunk
        with too much entities problems.
    """
    o = options
    delete_entities = o.delete_entities
    entity_limit = o.entity_limit
    try:
        r = scanned_regionfile_obj
        # counters of problems
        chunk_count = 0
        corrupted = 0
        wrong = 0
        entities_prob = 0
        shared = 0
        # used to detect chunks sharing headers
        offsets = {}
        filename = r.filename
        # try to open the file and see if we can parse the header
        try:
            region_file = region.RegionFile(r.path)
        except region.NoRegionHeader: # the region has no header
            r.status = world.REGION_TOO_SMALL
            return r
        except IOError, e:
            print "\nWARNING: I can't open the file {0} !\nThe error is \"{1}\".\nTypical causes are file blocked or problems in the file system.\n".format(filename,e)
            r.status = world.REGION_UNREADABLE
            r.scan_time = time.time()
            print "Note: this region file won't be scanned and won't be taken into acount in the summaries"
            # TODO count also this region files
            return r
        except: # whatever else print an error and ignore for the scan
                # not really sure if this is a good solution...
            print "\nWARNING: The region file \'{0}\' had an error and couldn't be parsed as region file!\nError:{1}\n".format(join(split(split(r.path)[0])[1], split(r.path)[1]),sys.exc_info()[0])
            print "Note: this region file won't be scanned and won't be taken into acount."
            print "Also, this may be a bug. Please, report it if you have the time.\n"
            return None

        try:# start the scanning of chunks
            
            for x in range(32):
                for z in range(32):

                    # start the actual chunk scanning
                    g_coords = r.get_global_chunk_coords(x, z)
                    chunk, c = scan_chunk(region_file, (x,z), g_coords, o)
                    if c != None: # chunk not created
                        r.chunks[(x,z)] = c
                        chunk_count += 1
                    else: continue
                    if c[TUPLE_STATUS] == world.CHUNK_OK:
                        continue
                    elif c[TUPLE_STATUS] == world.CHUNK_TOO_MANY_ENTITIES:
                        # deleting entities is in here because parsing a chunk with thousands of wrong entities
                        # takes a long time, and once detected is better to fix it at once.
                        if delete_entities:
                            world.delete_entities(region_file, x, z)
                            print "Deleted {0} entities in chunk ({1},{2}) of the region file: {3}".format(c[TUPLE_NUM_ENTITIES], x, z, r.filename)
                            # entities removed, change chunk status to OK
                            r.chunks[(x,z)] = (0, world.CHUNK_OK)

                        else:
                            entities_prob += 1
                            # This stores all the entities in a file,
                            # comes handy sometimes.
                            #~ pretty_tree = chunk['Level']['Entities'].pretty_tree()
                            #~ name = "{2}.chunk.{0}.{1}.txt".format(x,z,split(region_file.filename)[1])
                            #~ archivo = open(name,'w')
                            #~ archivo.write(pretty_tree)

                    elif c[TUPLE_STATUS] == world.CHUNK_CORRUPTED:
                        corrupted += 1
                    elif c[TUPLE_STATUS] == world.CHUNK_WRONG_LOCATED:
                        wrong += 1
            
            # Now check for chunks sharing offsets:
            # Please note! region.py will mark both overlapping chunks
            # as bad (the one stepping outside his territory and the
            # good one). Only wrong located chunk with a overlapping
            # flag are really BAD chunks! Use this criterion to 
            # discriminate
            metadata = region_file.metadata
            sharing = [k for k in metadata if (
                metadata[k].status == region.STATUS_CHUNK_OVERLAPPING and
                r[k][TUPLE_STATUS] == world.CHUNK_WRONG_LOCATED)]
            shared_counter = 0
            for k in sharing:
                r[k] = (r[k][TUPLE_NUM_ENTITIES], world.CHUNK_SHARED_OFFSET)
                shared_counter += 1

        except KeyboardInterrupt:
            print "\nInterrupted by user\n"
            # TODO this should't exit
            sys.exit(1)

        r.chunk_count = chunk_count
        r.corrupted_chunks = corrupted
        r.wrong_located_chunks = wrong
        r.entities_prob = entities_prob
        r.shared_offset = shared_counter
        r.scan_time = time.time()
        r.status = world.REGION_OK
        return r 

        # Fatal exceptions:
    except:
        # anything else is a ChildProcessException
        except_type, except_class, tb = sys.exc_info()
        r = (r.path, r.coords, (except_type, except_class, traceback.extract_tb(tb)))
        return r

def multithread_scan_regionfile(region_file):
    """ Does the multithread stuff for scan_region_file """
    r = region_file
    o = multithread_scan_regionfile.options

    # call the normal scan_region_file with this parameters
    r = scan_region_file(r,o)

    # exceptions will be handled in scan_region_file which is in the
    # single thread land
    multithread_scan_regionfile.q.put(r)



def scan_chunk(region_file, coords, global_coords, options):
    """ Takes a RegionFile obj and the local coordinatesof the chunk as
        inputs, then scans the chunk and returns all the data."""
    try:
        chunk = region_file.get_chunk(*coords)
        data_coords = world.get_chunk_data_coords(chunk)
        num_entities = len(chunk["Level"]["Entities"])
        if data_coords != global_coords:
            status = world.CHUNK_WRONG_LOCATED
            status_text = "Mismatched coordinates (wrong located chunk)."
            scan_time = time.time()
        elif num_entities > options.entity_limit:
            status = world.CHUNK_TOO_MANY_ENTITIES
            status_text = "The chunks has too many entities (it has {0}, and it's more than the limit {1})".format(num_entities, options.entity_limit)
            scan_time = time.time()
        else:
            status = world.CHUNK_OK
            status_text = "OK"
            scan_time = time.time()

    except region.InconceivedChunk as e:
        chunk = None
        data_coords = None
        num_entities = None
        status = world.CHUNK_NOT_CREATED
        status_text = "The chunk doesn't exist"
        scan_time = time.time()

    except region.RegionHeaderError as e:
        error = "Region header error: " + e.msg
        status = world.CHUNK_CORRUPTED
        status_text = error
        scan_time = time.time()
        chunk = None
        data_coords = None
        global_coords = world.get_global_chunk_coords(split(region_file.filename)[1], coords[0], coords[1])
        num_entities = None

    except region.ChunkDataError as e:
        error = "Chunk data error: " + e.msg
        status = world.CHUNK_CORRUPTED
        status_text = error
        scan_time = time.time()
        chunk = None
        data_coords = None
        global_coords = world.get_global_chunk_coords(split(region_file.filename)[1], coords[0], coords[1])
        num_entities = None

    except region.ChunkHeaderError as e:
        error = "Chunk herader error: " + e.msg
        status = world.CHUNK_CORRUPTED
        status_text = error
        scan_time = time.time()
        chunk = None
        data_coords = None
        global_coords = world.get_global_chunk_coords(split(region_file.filename)[1], coords[0], coords[1])
        num_entities = None

    return chunk, (num_entities, status) if status != world.CHUNK_NOT_CREATED else None

#~ TUPLE_COORDS = 0
#~ TUPLE_DATA_COORDS = 0
#~ TUPLE_GLOBAL_COORDS = 2
TUPLE_NUM_ENTITIES = 0
TUPLE_STATUS = 1

#~ def scan_and_fill_chunk(region_file, scanned_chunk_obj, options):
    #~ """ Takes a RegionFile obj and a ScannedChunk obj as inputs,
        #~ scans the chunk, fills the ScannedChunk obj and returns the chunk
        #~ as a NBT object."""
#~
    #~ c = scanned_chunk_obj
    #~ chunk, region_file, c.h_coords, c.d_coords, c.g_coords, c.num_entities, c.status, c.status_text, c.scan_time, c.region_path = scan_chunk(region_file, c.h_coords, options)
    #~ return chunk

def _mp_pool_init(regionset,options,q):
    """ Function to initialize the multiprocessing in scan_regionset.
    Is used to pass values to the child process. """
    multithread_scan_regionfile.regionset = regionset
    multithread_scan_regionfile.q = q
    multithread_scan_regionfile.options = options


def scan_regionset(regionset, options):
    """ This function scans all te region files in a regionset object
    and fills the ScannedRegionFile obj with the results
    """

    total_regions = len(regionset.regions)
    total_chunks = 0
    corrupted_total = 0
    wrong_total = 0
    entities_total = 0
    too_small_total = 0
    unreadable = 0

    # init progress bar
    if not options.verbose:
        pbar = progressbar.ProgressBar(
            widgets=['Scanning: ', FractionWidget(), ' ', progressbar.Percentage(), ' ', progressbar.Bar(left='[',right=']'), ' ', progressbar.ETA()],
            maxval=total_regions)

    # queue used by processes to pass finished stuff
    q = queues.SimpleQueue()
    pool = multiprocessing.Pool(processes=options.processes,
            initializer=_mp_pool_init,initargs=(regionset,options,q))

    if not options.verbose:
        pbar.start()

    # start the pool
    # Note to self: every child process has his own memory space,
    # that means every obj recived by them will be a copy of the
    # main obj
    result = pool.map_async(multithread_scan_regionfile, regionset.list_regions(None), max(1,total_regions//options.processes))

    # printing status
    region_counter = 0

    while not result.ready() or not q.empty():
        time.sleep(0.01)
        if not q.empty():
            r = q.get()
            if r == None: # something went wrong scanning this region file
                          # probably a bug... don't know if it's a good
                          # idea to skip it
                continue
            if not isinstance(r,world.ScannedRegionFile):
                raise ChildProcessException(r)
            else:
                corrupted, wrong, entities_prob, shared_offset, num_chunks = r.get_counters()
                filename = r.filename
                # the obj returned is a copy, overwrite it in regionset
                regionset[r.get_coords()] = r
                corrupted_total += corrupted
                wrong_total += wrong
                total_chunks += num_chunks
                entities_total += entities_prob
                if r.status == world.REGION_TOO_SMALL:
                    too_small_total += 1
                elif r.status == world.REGION_UNREADABLE:
                    unreadable += 1
                region_counter += 1
                if options.verbose:
                  if r.status == world.REGION_OK:
                    stats = "(c: {0}, w: {1}, tme: {2}, so: {3}, t: {4})".format( corrupted, wrong, entities_prob, shared_offset, num_chunks)
                  elif r.status == world.REGION_TOO_SMALL:
                    stats = "(Error: not a region file)"
                  elif r.status == world.REGION_UNREADABLE:
                    stats = "(Error: unreadable region file)"
                  print "Scanned {0: <12} {1:.<43} {2}/{3}".format(filename, stats, region_counter, total_regions)
                else:
                    pbar.update(region_counter)

    if not options.verbose: pbar.finish()

    regionset.scanned = True

########NEW FILE########
__FILENAME__ = util
#!/usr/bin/env python
# -*- coding: utf-8 -*-

#
#   Region Fixer.
#   Fix your region files with a backup copy of your Minecraft world.
#   Copyright (C) 2011  Alejandro Aguilera (Fenixin)
#   https://github.com/Fenixin/Minecraft-Region-Fixer
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import platform
from os.path import join, split, exists, isfile
import world

# stolen from minecraft overviewer 
# https://github.com/overviewer/Minecraft-Overviewer/
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

def entitle(text, level = 0):
    """ Put the text in a title with lot's of hashes everywhere. """
    t = ''
    if level == 0:
        t += "\n"
        t += "{0:#^60}\n".format('')
        t += "{0:#^60}\n".format(' ' + text + ' ')
        t += "{0:#^60}\n".format('')
    return t
        

def table(columns):
    """ Gets a list with lists in which each list is a column,
        returns a text string with a table. """

    def get_max_len(l):
        """ Takes a list and returns the length of the biggest
            element """
        m = 0
        for e in l:
            if len(str(e)) > m:
                m = len(e)
        return m

    text = ""
    # stores the size of the biggest element in that column
    ml = []
    # fill up ml
    for c in columns:
        m = 0
        t = get_max_len(c)
        if t > m:
            m = t
        ml.append(m)
    # get the total width of the table:
    ml_total = 0
    for i in range(len(ml)):
        ml_total += ml[i] + 2 # size of each word + 2 spaces
    ml_total += 1 + 2# +1 for the separator | and +2 for the borders
    text += "-"*ml_total + "\n"
    # all the columns have the same number of rows
    row = get_max_len(columns)
    for r in range(row):
        line = "|"
        # put all the elements in this row together with spaces
        for i in range(len(columns)):
            line += "{0: ^{width}}".format(columns[i][r],width = ml[i] + 2)
            # add a separator for the first column
            if i == 0:
                line += "|"

        text += line + "|" + "\n"
        if r == 0:
            text += "-"*ml_total + "\n"
    text += "-"*ml_total
    return text


def parse_chunk_list(chunk_list, world_obj):
    """ Generate a list of chunks to use with world.delete_chunk_list.

    It takes a list of global chunk coordinates and generates a list of
    tuples containing:

    (region fullpath, chunk X, chunk Z)

    """
    # this is not used right now
    parsed_list = []
    for line in chunk_list:
        try:
            chunk = eval(line)
        except:
            print "The chunk {0} is not valid.".format(line)
            continue
        region_name = world.get_chunk_region(chunk[0], chunk[1])
        fullpath = join(world_obj.world_path, "region", region_name)
        if fullpath in world_obj.all_mca_files:
            parsed_list.append((fullpath, chunk[0], chunk[1]))
        else:
            print "The chunk {0} should be in the region file {1} and this region files doesn't extist!".format(chunk, fullpath)

    return parsed_list

def parse_paths(args):
    """ Parse the list of args passed to region-fixer.py and returns a 
    RegionSet object with the list of regions and a list of World 
    objects. """
    # parese the list of region files and worlds paths
    world_list = []
    region_list = []
    warning = False
    for arg in args:
        if arg[-4:] == ".mca":
            region_list.append(arg)
        elif arg[-4:] == ".mcr": # ignore pre-anvil region files
            if not warning:
                print "Warning: Region-Fixer only works with anvil format region files. Ignoring *.mcr files"
                warning = True
        else:
            world_list.append(arg)

    # check if they exist
    region_list_tmp = []
    for f in region_list:
        if exists(f):
            if isfile(f):
                region_list_tmp.append(f)
            else:
                print "Warning: \"{0}\" is not a file. Skipping it and scanning the rest.".format(f)
        else:
            print "Warning: The region file {0} doesn't exists. Skipping it and scanning the rest.".format(f)
    region_list = region_list_tmp

    # init the world objects
    world_list = parse_world_list(world_list)

    return world_list, world.RegionSet(region_list = region_list)

def parse_world_list(world_path_list):
    """ Parses a world list checking if they exists and are a minecraft
        world folders. Returns a list of World objects. """
    
    tmp = []
    for d in world_path_list:
        if exists(d):
            w = world.World(d)
            if w.isworld:
                tmp.append(w)
            else:
                print "Warning: The folder {0} doesn't look like a minecraft world. I'll skip it.".format(d)
        else:
            print "Warning: The folder {0} doesn't exist. I'll skip it.".format(d)
    return tmp



def parse_backup_list(world_backup_dirs):
    """ Generates a list with the input of backup dirs containing the
    world objects of valid world directories."""

    directories = world_backup_dirs.split(',')
    backup_worlds = parse_world_list(directories)
    return backup_worlds

########NEW FILE########
__FILENAME__ = world
#!/usr/bin/env python
# -*- coding: utf-8 -*-

#
#   Region Fixer.
#   Fix your region files with a backup copy of your Minecraft world.
#   Copyright (C) 2011  Alejandro Aguilera (Fenixin)
#   https://github.com/Fenixin/Minecraft-Region-Fixer
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import nbt.region as region
import nbt.nbt as nbt
from util import table

from glob import glob
from os.path import join, split, exists
from os import remove
from shutil import copy

import time

# Constants:
# Used to mark the status of a chunks:
CHUNK_NOT_CREATED = -1
CHUNK_OK = 0
CHUNK_CORRUPTED = 1
CHUNK_WRONG_LOCATED = 2
CHUNK_TOO_MANY_ENTITIES = 3
CHUNK_SHARED_OFFSET = 4
CHUNK_STATUS_TEXT = {CHUNK_NOT_CREATED:"Not created",
                    CHUNK_OK:"OK",
                    CHUNK_CORRUPTED:"Corrupted",
                    CHUNK_WRONG_LOCATED:"Wrong located",
                    CHUNK_TOO_MANY_ENTITIES:"Too many entities",
                    CHUNK_SHARED_OFFSET:"Sharing offset"}

CHUNK_PROBLEMS = [CHUNK_CORRUPTED, CHUNK_WRONG_LOCATED, CHUNK_TOO_MANY_ENTITIES, CHUNK_SHARED_OFFSET]

CHUNK_PROBLEMS_ARGS = {CHUNK_CORRUPTED:'corrupted',CHUNK_WRONG_LOCATED:'wrong',CHUNK_TOO_MANY_ENTITIES:'entities',CHUNK_SHARED_OFFSET:'sharing'}
# list with problem status-text tuples
CHUNK_PROBLEMS_ITERATOR = []
for problem in CHUNK_PROBLEMS:
    CHUNK_PROBLEMS_ITERATOR.append((problem, CHUNK_STATUS_TEXT[problem], CHUNK_PROBLEMS_ARGS[problem]))



# Used to mark the status of region files:
REGION_OK = 10
REGION_TOO_SMALL = 11
REGION_UNREADABLE = 12
REGION_STATUS_TEXT = {REGION_OK: "Ok", REGION_TOO_SMALL: "Too small", REGION_UNREADABLE: "Unreadable"}

REGION_PROBLEMS = [REGION_TOO_SMALL]
REGION_PROBLEMS_ARGS = {REGION_TOO_SMALL: 'too-small'}

# list with problem status-text tuples
REGION_PROBLEMS_ITERATOR = []
for problem in REGION_PROBLEMS:
    try:
        REGION_PROBLEMS_ITERATOR.append((problem, REGION_STATUS_TEXT[problem], REGION_PROBLEMS_ARGS[problem]))
    except KeyError:
        pass

REGION_PROBLEMS_ARGS = {REGION_TOO_SMALL:'too-small'}

# Used to know where to look in a chunk status tuple
#~ TUPLE_COORDS = 0
#~ TUPLE_DATA_COORDS = 0
#~ TUPLE_GLOBAL_COORDS = 2
TUPLE_NUM_ENTITIES = 0
TUPLE_STATUS = 1

# Dimension names:
DIMENSION_NAMES = { "region":"Overworld", "DIM1":"The End", "DIM-1":"Nether" }

class ScannedDatFile(object):
    def __init__(self, path = None, readable = None, status_text = None):
        self.path = path
        if self.path and exists(self.path):
            self.filename = split(path)[1]
        else:
            self.filename = None
        self.readable = readable
        self.status_text = status_text

    def __str__(self):
        text = "NBT file:" + str(self.path) + "\n"
        text += "\tReadable:" + str(self.readable) + "\n"
        return text

class ScannedChunk(object):
    """ Stores all the results of the scan. Not used at the moment, it
        prette nice but takes an huge amount of memory. """
        # WARNING: not used at the moment, it probably has bugs ans is
        # outdated
        # The problem with it was it took too much memory. It has been
        # remplaced with a tuple
    def __init__(self, header_coords, global_coords = None, data_coords = None, status = None, num_entities = None, scan_time = None, region_path = None):
        """ Inits the object with all the scan information. """
        self.h_coords = header_coords
        self.g_coords = global_coords
        self.d_coords = data_coords
        self.status = status
        self.status_text = None
        self.num_entities = num_entities
        self.scan_time = scan_time
        self.region_path = region_path

    def __str__(self):
        text = "Chunk with header coordinates:" + str(self.h_coords) + "\n"
        text += "\tData coordinates:" + str(self.d_coords) + "\n"
        text +="\tGlobal coordinates:" + str(self.g_coords) + "\n"
        text += "\tStatus:" + str(self.status_text) + "\n"
        text += "\tNumber of entities:" + str(self.num_entities) + "\n"
        text += "\tScan time:" + time.ctime(self.scan_time) + "\n"
        return text

    def get_path():
        """ Returns the path of the region file. """
        return self.region_path

    def rescan_entities(self, options):
        """ Updates the status of the chunk when the the option
            entity limit is changed. """
        if self.num_entities >= options.entity_limit:
            self.status = CHUNK_TOO_MANY_ENTITIES
            self.status_text = CHUNK_STATUS_TEXT[CHUNK_TOO_MANY_ENTITIES]
        else:
            self.status = CHUNK_OK
            self.status_text = CHUNK_STATUS_TEXT[CHUNK_OK]

class ScannedRegionFile(object):
    """ Stores all the scan information for a region file """
    def __init__(self, filename, corrupted = 0, wrong = 0, entities_prob = 0, shared_offset = 0, chunks = 0, status = 0, time = None):
        # general region file info
        self.path = filename
        self.filename = split(filename)[1]
        self.folder = split(filename)[0]
        self.x = self.z = None
        self.x, self.z = self.get_coords()
        self.coords = (self.x, self.z)

        # dictionary storing all the state tuples of all the chunks
        # in the region file
        self.chunks = {}

        # TODO: these values aren't really used.
        # count_chunks() is used instead.
        # counters with the number of chunks
        self.corrupted_chunks = corrupted
        self.wrong_located_chunks = wrong
        self.entities_prob = entities_prob
        self.shared_offset = shared_offset
        self.chunk_count = chunks

        # time when the scan for this file finished
        self.scan_time = time

        # The status of the region file. At the moment can be OK,
        # TOO SMALL or UNREADABLE see the constants at the start
        # of the file.
        self.status = status

    def __str__(self):
        text = "Path: {0}".format(self.path)
        scanned = False
        if time:
            scanned = True
        text += "\nScanned: {0}".format(scanned)

        return text

    def __getitem__(self, key):
        return self.chunks[key]

    def __setitem__(self, key, value):
        self.chunks[key] = value

    def keys(self):
        return self.chunks.keys()

    def get_counters(self):
        """ Returns integers with all the problem counters in this
            region file. The order is corrupted, wrong located, entities
            shared header, total chunks """
        return self.corrupted_chunks, self.wrong_located_chunks, self.entities_prob, self.shared_offset, self.count_chunks() 

    def get_path(self):
        """ Returns the path of the region file. """
        return self.path

    def count_chunks(self, problem = None):
        """ Counts chunks in the region file with the given problem.
            If problem is omited or None, counts all the chunks. Returns
            an integer with the counter. """
        counter = 0
        for coords in self.keys():
            if self[coords] and (self[coords][TUPLE_STATUS] == problem or problem == None):
                counter += 1

        return counter

    def get_global_chunk_coords(self, chunkX, chunkZ):
        """ Takes the region filename and the chunk local
            coords and returns the global chunkcoords as integerss """

        regionX, regionZ = self.get_coords()
        chunkX += regionX*32
        chunkZ += regionZ*32

        return chunkX, chunkZ

    def get_coords(self):
        """ Splits the region filename (full pathname or just filename)
            and returns his region X and Z coordinates as integers. """
        if self.x != None and self.z != None:
            return self.x, self.z
        else:
            splited = split(self.filename)
            filename = splited[1]
            l = filename.split('.')
            coordX = int(l[1])
            coordZ = int(l[2])

            return coordX, coordZ

    def list_chunks(self, status = None):
        """ Returns a list of all the ScannedChunk objects of the chunks
            with the given status, if no status is omited or None,
            returns all the existent chunks in the region file """

        l = []
        for c in self.keys():
            t = self[c]
            if status == t[TUPLE_STATUS]:
                l.append((self.get_global_chunk_coords(*c),t))
            elif status == None:
                l.append((self.get_global_chunk_coords(*c),t))
        return l

    def summary(self):
        """ Returns a summary of the problematic chunks. The summary
            is a string with region file, global coords, local coords,
            and status of every problematic chunk. """
        text = ""
        if self.status == REGION_TOO_SMALL:
            text += " |- This region file is too small in size to actually be a region file.\n"
        else:
            for c in self.keys():
                if self[c][TUPLE_STATUS] == CHUNK_OK or self[c][TUPLE_STATUS] == CHUNK_NOT_CREATED: continue
                status = self[c][TUPLE_STATUS]
                h_coords = c
                g_coords = self.get_global_chunk_coords(*h_coords)
                text += " |-+-Chunk coords: header {0}, global {1}.\n".format(h_coords, g_coords)
                text += " | +-Status: {0}\n".format(CHUNK_STATUS_TEXT[status])
                if self[c][TUPLE_STATUS] == CHUNK_TOO_MANY_ENTITIES:
                    text += " | +-Nº entities: {0}\n".format(self[c][TUPLE_NUM_ENTITIES])
                text += " |\n"

        return text

    def remove_problematic_chunks(self, problem):
        """ Removes all the chunks with the given problem, returns a
            counter with the number of deleted chunks. """

        counter = 0
        bad_chunks = self.list_chunks(problem)
        for c in bad_chunks:
            global_coords = c[0]
            status_tuple = c[1]
            local_coords = _get_local_chunk_coords(*global_coords)
            region_file = region.RegionFile(self.path)
            region_file.unlink_chunk(*local_coords)
            counter += 1
            # create the new status tuple
            #                    (num_entities, chunk status)
            self[local_coords] = (0           , CHUNK_NOT_CREATED)

        return counter

    def remove_entities(self):
        """ Removes all the entities in chunks with the problematic
            status CHUNK_TOO_MANY_ENTITIES that are in this region file.
            Returns a counter of all the removed entities. """
        problem = CHUNK_TOO_MANY_ENTITIES
        counter = 0
        bad_chunks = self.list_chunks(problem)
        for c in bad_chunks:
            global_coords = c[0]
            status_tuple = c[1]
            local_coords = _get_local_chunk_coords(*global_coords)
            counter += self.remove_chunk_entities(*local_coords)
            # create new status tuple:
            #                    (num_entities, chunk status)
            self[local_coords] = (0           , CHUNK_OK)
        return counter

    def remove_chunk_entities(self, x, z):
        """ Takes a chunk coordinates, opens the chunk and removes all
            the entities in it. Return an integer with the number of
            entities removed"""
        region_file = region.RegionFile(self.path)
        chunk = region_file.get_chunk(x,z)
        counter = len(chunk['Level']['Entities'])
        empty_tag_list = nbt.TAG_List(nbt.TAG_Byte,'','Entities')
        chunk['Level']['Entities'] = empty_tag_list
        region_file.write_chunk(x, z, chunk)

        return counter

    def rescan_entities(self, options):
        """ Updates the status of all the chunks in the region file when
            the the option entity limit is changed. """
        for c in self.keys():
            # for safety reasons use a temporary list to generate the
            # new tuple
            t = [0,0]
            if self[c][TUPLE_STATUS] in (CHUNK_TOO_MANY_ENTITIES, CHUNK_OK):
                # only touch the ok chunks and the too many entities chunk
                if self[c][TUPLE_NUM_ENTITIES] > options.entity_limit:
                    # now it's a too many entities problem
                    t[TUPLE_NUM_ENTITIES] = self[c][TUPLE_NUM_ENTITIES]
                    t[TUPLE_STATUS] = CHUNK_TOO_MANY_ENTITIES

                elif self[c][TUPLE_NUM_ENTITIES] <= options.entity_limit:
                    # the new limit says it's a normal chunk
                    t[TUPLE_NUM_ENTITIES] = self[c][TUPLE_NUM_ENTITIES]
                    t[TUPLE_STATUS] = CHUNK_OK

                self[c] = tuple(t)


class RegionSet(object):
    """Stores an arbitrary number of region files and the scan results.
        Inits with a list of region files. The regions dict is filled
        while scanning with ScannedRegionFiles and ScannedChunks."""
    def __init__(self, regionset_path = None, region_list = []):
        if regionset_path:
            self.path = regionset_path
            self.region_list = glob(join(self.path, "r.*.*.mca"))
        else:
            self.path = None
            self.region_list = region_list
        self.regions = {}
        for path in self.region_list:
            r = ScannedRegionFile(path)
            self.regions[r.get_coords()] = r
        self.corrupted_chunks = 0
        self.wrong_located_chunks = 0
        self.entities_problems = 0
        self.shared_header = 0
        self.bad_list = []
        self.scanned = False

    def get_name(self):
        """ Return a string with the name of the dimension, the
        directory if there is no name or "" if there's nothing """

        dim_directory = self._get_dimension_directory()
        if dim_directory:
            try: return DIMENSION_NAMES[dim_directory]
            except: return dim_directory
        else:
            return ""

    def _get_dimension_directory(self):
        """ Returns a string with the directory of the dimension, None
        if there is no such a directory and the regionset is composed
        of sparse region files. """
        if self.path:
            rest, region = split(self.path)
            rest, dim_path = split(rest)
            if dim_path == "": dim_path = split(rest)[1]
            return dim_path

        else: return None

    def __str__(self):
        text = "Region-set information:\n"
        if self.path:
            text += "   Regionset path: {0}\n".format(self.path)
        text += "   Region files: {0}\n".format(len(self.regions))
        text += "   Scanned: {0}".format(str(self.scanned))
        return text

    def __getitem__(self, key):
        return self.regions[key]

    def __setitem__(self, key, value):
        self.regions[key] = value

    def __delitem__(self, key):
        del self.regions[key]

    def __len__(self):
        return len(self.regions)

    def keys(self):
        return self.regions.keys()

    def list_regions(self, status = None):
        """ Returns a list of all the ScannedRegionFile objects stored
            in the RegionSet with status. If status = None it returns
            all the objects."""

        if status == None:
            #~ print "Estamos tras pasar el if para status None"
            #~ print "Los valores de el dict son:"
            #~ print self.regions.values()
            #~ print "El diccionario es si es:"
            #~ print self.regions
            return self.regions.values()
        t = []
        for coords in self.regions.keys():
            r = self.regions[coords]
            if r.status == status:
                t.append(r)
        return t

    def count_regions(self, status = None):
        """ Return the number of region files with status. If none
            returns the number of region files in this regionset.
            Possible status are: empty, too_small """

        counter = 0
        for r in self.keys():
            if status == self[r].status: counter += 1
            elif status == None: counter += 1
        return counter

    def count_chunks(self, problem = None):
        """ Returns the number of chunks with the given problem. If
            problem is None returns the number of chunks. """
        counter = 0
        for r in self.keys():
            counter += self[r].count_chunks(problem)
        return counter

    def list_chunks(self, status = None):
        """ Returns a list of the ScannedChunk objects of the chunks
            with the given status. If status = None returns all the
            chunks. """
        l = []
        for r in self.keys():
            l.extend(self[r].list_chunks(status))
        return l

    def summary(self):
        """ Returns a summary of the problematic chunks in this 
            regionset. The summary is a string with global coords,
            local coords, data coords and status. """
        text = ""
        for r in self.keys():
            if not (self[r].count_chunks(CHUNK_CORRUPTED) or self[r].count_chunks(CHUNK_TOO_MANY_ENTITIES) or self[r].count_chunks(CHUNK_WRONG_LOCATED) or self[r].count_chunks(CHUNK_SHARED_OFFSET) or self[r].status == REGION_TOO_SMALL):
                continue
            text += "Region file: {0}\n".format(self[r].filename)
            text += self[r].summary()
            text += " +\n\n"
        return text

    def locate_chunk(self, global_coords):
        """ Takes the global coordinates of a chunk and returns the
            region filename and the local coordinates of the chunk or
            None if it doesn't exits in this RegionSet """

        filename = self.path + get_chunk_region(*global_coords)
        local_coords = _get_local_chunk_coords(*global_coords)

        return filename, local_coords

    def locate_region(self, coords):
        """ Returns a string with the path of the region file with
            the given coords in this regionset or None if not found. """

        x, z = coords
        region_name = 'r.' + str(x) + '.' + str(z) + '.mca'

        return region_name


    def remove_problematic_chunks(self, problem):
        """ Removes all the chunks with the given problem, returns a
            counter with the number of deleted chunks. """

        counter = 0
        if self.count_chunks():
            print ' Deleting chunks in region set \"{0}\":'.format(self._get_dimension_directory())
            for r in self.regions.keys():
                counter += self.regions[r].remove_problematic_chunks(problem)
            print "Removed {0} chunks in this regionset.\n".format(counter)

        return counter

    def remove_entities(self):
        """ Removes entities in chunks with the status
            TOO_MANY_ENTITIES. """
        counter = 0
        for r in self.regions.keys():
            counter += self.regions[r].remove_entities()
        return counter

    def rescan_entities(self, options):
        """ Updates the status of all the chunks in the regionset when
            the option entity limit is changed. """
        for r in self.keys():
            self[r].rescan_entities(options)

    def generate_report(self, standalone):
        """ Generates a report of the last scan. If standalone is True
        it will generate a report to print in a terminal. If it's False
        it will returns the counters of every problem. """

        # collect data
        corrupted = self.count_chunks(CHUNK_CORRUPTED)
        wrong_located = self.count_chunks(CHUNK_WRONG_LOCATED)
        entities_prob = self.count_chunks(CHUNK_TOO_MANY_ENTITIES)
        shared_prob = self.count_chunks(CHUNK_SHARED_OFFSET)
        total_chunks = self.count_chunks()

        too_small_region = self.count_regions(REGION_TOO_SMALL)
        unreadable_region = self.count_regions(REGION_UNREADABLE)
        total_regions = self.count_regions()
        
        if standalone:
            text = ""
        
            # Print all this info in a table format
            # chunks
            chunk_errors = ("Problem","Corrupted","Wrong l.","Etities","Shared o.", "Total chunks")
            chunk_counters = ("Counts",corrupted, wrong_located, entities_prob, shared_prob, total_chunks)
            table_data = []
            for i, j in zip(chunk_errors, chunk_counters):
                table_data.append([i,j])
            text += "\nChunk problems:"
            if corrupted or wrong_located or entities_prob or shared_prob:
                text += table(table_data)
            else:
                text += "\nNo problems found.\n"

            # regions
            text += "\n\nRegion problems:\n"
            region_errors = ("Problem","Too small","Unreadable","Total regions")
            region_counters = ("Counts", too_small_region,unreadable_region, total_regions)
            table_data = []
            # compose the columns for the table
            for i, j in zip(region_errors, region_counters):
                table_data.append([i,j])
            if too_small_region:
                text += table(table_data)
            else:
                text += "No problems found."
                
            return text
        else:
            return corrupted, wrong_located, entities_prob, shared_prob, total_chunks, too_small_region, unreadable_region, total_regions

    def remove_problematic_regions(self, problem):
        """ Removes all the regions files with the given problem.
            This is NOT the same as removing chunks, this WILL DELETE
            the region files from the hard drive. """
        counter = 0
        for r in self.list_regions(problem):
            remove(r.get_path())
            counter += 1
        return counter

class World(object):
    """ This class stores all the info needed of a world, and once
    scanned, stores all the problems found. It also has all the tools
    needed to modify the world."""

    def __init__(self, world_path):
        self.path = world_path

        # list with RegionSets
        self.regionsets = []

        self.regionsets.append(RegionSet(join(self.path, "region/")))
        for directory in glob(join(self.path, "DIM*/region")):
            self.regionsets.append(RegionSet(join(self.path, directory)))

        # level.dat
        # let's scan level.dat here so we can extract the world name
        # right now
        level_dat_path = join(self.path, "level.dat")
        if exists(level_dat_path):
            try:
                self.level_data = nbt.NBTFile(level_dat_path)["Data"]
                self.name = self.level_data["LevelName"].value
                self.scanned_level = ScannedDatFile(level_dat_path, readable = True, status_text = "OK")
            except Exception, e:
                self.name = None
                self.scanned_level = ScannedDatFile(level_dat_path, readable = False, status_text = e)
        else:
            self.level_file = None
            self.level_data = None
            self.name = None
            self.scanned_level = ScannedDatFile(None, False, "The file doesn't exist")

        # player files
        player_paths = glob(join(join(self.path, "players"), "*.dat"))
        self.players = {}
        for path in player_paths:
            name = split(path)[1].split(".")[0]
            self.players[name] = ScannedDatFile(path)

        # does it look like a world folder?
        region_files = False
        for region_directory in self.regionsets:
            if region_directory:
                region_files = True
        if region_files:
            self.isworld = True
        else:
            self.isworld = False

        # set in scan.py, used in interactive.py
        self.scanned = False

    def __str__(self):
        text = "World information:\n"
        text += "   World path: {0}\n".format(self.path)
        text += "   World name: {0}\n".format(self.name)
        text += "   Region files: {0}\n".format(self.get_number_regions())
        text += "   Scanned: {0}".format(str(self.scanned))
        return text

    def get_number_regions(self):
        """ Returns a integer with the number of regions in this world"""
        counter = 0
        for dim in self.regionsets:
            counter += len(dim)
        
        return counter

    def summary(self):
        """ Returns a text string with a summary of all the problems
            found in the world object."""
        final = ""

        # intro with the world name
        final += "{0:#^60}\n".format('')
        final += "{0:#^60}\n".format(" World name: {0} ".format(self.name))
        final += "{0:#^60}\n".format('')

        # dat files info
        final += "\nlevel.dat:\n"
        if self.scanned_level.readable:
            final += "\t\'level.dat\' is readable\n"
        else:
            final += "\t[WARNING]: \'level.dat\' isn't readable, error: {0}\n".format(self.scanned_level.status_text)

        all_ok = True
        final += "\nPlayer files:\n"
        for name in self.players:
            if not self.players[name].readable:
                all_ok = False
                final += "\t-[WARNING]: Player file {0} has problems.\n\t\tError: {1}\n\n".format(self.players[name].filename, self.players[name].status_text)
        if all_ok:
            final += "\tAll player files are readable.\n\n"

        # chunk info
        chunk_info = ""
        for regionset in self.regionsets:
            
            title = regionset.get_name()
            
            # don't add text if there aren't broken chunks
            text = regionset.summary()
            chunk_info += (title + text) if text else ""
        final += chunk_info if chunk_info else "All the chunks are ok."

        return final

    def get_name(self):
        """ Returns a string with the name as found in level.dat or
            with the world folder's name. """
        if self.name:
            return self.name
        else:
            n = split(self.path) 
            if n[1] == '':
                n = split(n[0])[1]
            return n

    def count_regions(self, status = None):
        """ Returns a number with the count of region files with
            status. """
        counter = 0
        for r in self.regionsets:
            counter += r.count_regions(status)
        return counter

    def count_chunks(self, status = None):
        """ Counts problems  """
        counter = 0
        for r in self.regionsets:
            count = r.count_chunks(status)
            counter += count
        return counter

    def replace_problematic_chunks(self, backup_worlds, problem, options):
        """ Takes a list of world objects and a problem value and try
            to replace every chunk with that problem using a working
            chunk from the list of world objects. It uses the world
            objects in left to riht order. """

        counter = 0
        for regionset in self.regionsets:
            for backup in backup_worlds:
                # choose the correct regionset based on the dimension
                # folder name
                for temp_regionset in backup.regionsets:
                    if temp_regionset._get_dimension_directory() == regionset._get_dimension_directory():
                        b_regionset = temp_regionset
                        break

                # this don't need to be aware of region status, it just
                # iterates the list returned by list_chunks()
                bad_chunks = regionset.list_chunks(problem)
                
                if bad_chunks and b_regionset._get_dimension_directory() != regionset._get_dimension_directory():
                    print "The regionset \'{0}\' doesn't exist in the backup directory. Skipping this backup directory.".format(regionset._get_dimension_directory())
                else:
                    for c in bad_chunks:
                        global_coords = c[0]
                        status_tuple = c[1]
                        local_coords = _get_local_chunk_coords(*global_coords)
                        print "\n{0:-^60}".format(' New chunk to replace. Coords: x = {0}; z = {1} '.format(*global_coords))

                        # search for the region file
                        backup_region_path, local_coords = b_regionset.locate_chunk(global_coords)
                        tofix_region_path, _ = regionset.locate_chunk(global_coords)
                        if exists(backup_region_path):
                            print "Backup region file found in:\n  {0}".format(backup_region_path)
                            
                            # scan the whole region file, pretty slow, but completely needed to detec sharing offset chunks
                            from scan import scan_region_file
                            r = scan_region_file(ScannedRegionFile(backup_region_path),options)
                            try:
                                status_tuple = r[local_coords]
                            except KeyError:
                                status_tuple = None
                            
                            # retrive the status from status_tuple
                            if status_tuple == None:
                                status = CHUNK_NOT_CREATED
                            else:
                                status = status_tuple[TUPLE_STATUS]
                            
                            if status == CHUNK_OK:
                                backup_region_file = region.RegionFile(backup_region_path)
                                working_chunk = backup_region_file.get_chunk(local_coords[0],local_coords[1])

                                print "Replacing..."
                                # the chunk exists and is healthy, fix it!
                                tofix_region_file = region.RegionFile(tofix_region_path)
                                # first unlink the chunk, second write the chunk.
                                # unlinking the chunk is more secure and the only way to replace chunks with 
                                # a shared offset withou overwriting the good chunk
                                tofix_region_file.unlink_chunk(*local_coords)
                                tofix_region_file.write_chunk(local_coords[0], local_coords[1],working_chunk)
                                counter += 1
                                print "Chunk replaced using backup dir: {0}".format(backup.path)

                            else:
                                print "Can't use this backup directory, the chunk has the status: {0}".format(CHUNK_STATUS_TEXT[status])
                                continue

                        else:
                            print "The region file doesn't exist in the backup directory: {0}".format(backup_region_path)

        return counter


    def remove_problematic_chunks(self, problem):
        """ Removes all the chunks with the given problem. """
        counter = 0
        for regionset in self.regionsets:
            counter += regionset.remove_problematic_chunks(problem)
        return counter

    def replace_problematic_regions(self, backup_worlds, problem, options):
        """ Replaces region files with the given problem using a backup
            directory. """
        counter = 0
        for regionset in self.regionsets:
            for backup in backup_worlds:
                # choose the correct regionset based on the dimension
                # folder name
                for temp_regionset in backup.regionsets:
                    if temp_regionset._get_dimension_directory() == regionset._get_dimension_directory():
                        b_regionset = temp_regionset
                        break
                
                bad_regions = regionset.list_regions(problem)
                if bad_regions and b_regionset._get_dimension_directory() != regionset._get_dimension_directory():
                    print "The regionset \'{0}\' doesn't exist in the backup directory. Skipping this backup directory.".format(regionset._get_dimension_directory())
                else:
                    for r in bad_regions:
                        print "\n{0:-^60}".format(' New region file to replace! Coords {0} '.format(r.get_coords()))

                        # search for the region file
                        
                        try:
                            backup_region_path = b_regionset[r.get_coords()].get_path()
                        except:
                            backup_region_path = None
                        tofix_region_path = r.get_path()
                        
                        if backup_region_path != None and exists(backup_region_path):
                            print "Backup region file found in:\n  {0}".format(backup_region_path)
                            # check the region file, just open it.
                            try:
                                backup_region_file = region.RegionFile(backup_region_path)
                            except region.NoRegionHeader as e:
                                print "Can't use this backup directory, the error while opening the region file: {0}".format(e)
                                continue
                            except Exception as e:
                                print "Can't use this backup directory, unknown error: {0}".format(e)
                                continue
                            copy(backup_region_path, tofix_region_path)
                            print "Region file replaced!"
                            counter += 1
                        else:
                            print "The region file doesn't exist in the backup directory: {0}".format(backup_region_path)

        return counter
        

    def remove_problematic_regions(self, problem):
        """ Removes all the regions files with the given problem.
            This is NOT the same as removing chunks, this WILL DELETE
            the region files from the hard drive. """
        counter = 0
        for regionset in self.regionsets:
            counter += regionset.remove_problematic_regions(problem)
        return counter

    def remove_entities(self):
        """ Delete all the entities in the chunks that have more than
            entity-limit entities. """
        counter = 0
        for regionset in self.regionsets:
            counter += regionset.remove_entities()
        return counter

    def rescan_entities(self, options):
        """ Updates the status of all the chunks in the world when the
            option entity limit is changed. """
        for regionset in self.regionsets:
            regionset.rescan_entities(options)
    
    def generate_report(self, standalone):
        
        # collect data
        corrupted = self.count_chunks(CHUNK_CORRUPTED)
        wrong_located = self.count_chunks(CHUNK_WRONG_LOCATED)
        entities_prob = self.count_chunks(CHUNK_TOO_MANY_ENTITIES)
        shared_prob = self.count_chunks(CHUNK_SHARED_OFFSET)
        total_chunks = self.count_chunks()

        too_small_region = self.count_regions(REGION_TOO_SMALL)
        unreadable_region = self.count_regions(REGION_UNREADABLE)
        total_regions = self.count_regions()
        
        if standalone:
            text = ""
        
            # Print all this info in a table format
            chunk_errors = ("Problem","Corrupted","Wrong l.","Etities","Shared o.", "Total chunks")
            chunk_counters = ("Counts",corrupted, wrong_located, entities_prob, shared_prob, total_chunks)
            table_data = []
            for i, j in zip(chunk_errors, chunk_counters):
                table_data.append([i,j])
            text += "\nChunk problems:\n"
            if corrupted or wrong_located or entities_prob or shared_prob:
                text += table(table_data)
            else:
                text += "No problems found.\n"

            text += "\n\nRegion problems:\n"
            region_errors = ("Problem","Too small","Unreadable","Total regions")
            region_counters = ("Counts", too_small_region,unreadable_region, total_regions)
            table_data = []
            # compose the columns for the table
            for i, j in zip(region_errors, region_counters):
                table_data.append([i,j])
            if too_small_region:
                text += table(table_data)
            else:
                text += "No problems found."
                
            return text
        else:
            return corrupted, wrong_located, entities_prob, shared_prob, total_chunks, too_small_region, unreadable_region, total_regions



def delete_entities(region_file, x, z):
    """ This function is used while scanning the world in scan.py! Takes
        a region file obj and a local chunks coords and deletes all the
        entities in that chunk. """
    chunk = region_file.get_chunk(x,z)
    counter = len(chunk['Level']['Entities'])
    empty_tag_list = nbt.TAG_List(nbt.TAG_Byte,'','Entities')
    chunk['Level']['Entities'] = empty_tag_list
    region_file.write_chunk(x, z, chunk)

    return counter


def _get_local_chunk_coords(chunkx, chunkz):
    """ Takes the chunk global coords and returns the local coords """
    return chunkx % 32, chunkz % 32

def get_chunk_region(chunkX, chunkZ):
    """ Returns the name of the region file given global chunk
        coords """

    regionX = chunkX / 32
    regionZ = chunkZ / 32

    region_name = 'r.' + str(regionX) + '.' + str(regionZ) + '.mca'

    return region_name

def get_chunk_data_coords(nbt_file):
    """ Gets the coords stored in the NBT structure of the chunk.

        Takes an nbt obj and returns the coords as integers.
        Don't confuse with get_global_chunk_coords! """

    level = nbt_file.__getitem__('Level')

    coordX = level.__getitem__('xPos').value
    coordZ = level.__getitem__('zPos').value

    return coordX, coordZ

def get_region_coords(filename):
    """ Splits the region filename (full pathname or just filename)
        and returns his region X and Z coordinates as integers. """

    l = filename.split('.')
    coordX = int(l[1])
    coordZ = int(l[2])

    return coordX, coordZ

def get_global_chunk_coords(region_name, chunkX, chunkZ):
    """ Takes the region filename and the chunk local
        coords and returns the global chunkcoords as integerss. This 
        version does exactly the same as the method in 
        ScannedRegionFile. """

    regionX, regionZ = get_region_coords(region_name)
    chunkX += regionX*32
    chunkZ += regionZ*32

    return chunkX, chunkZ

########NEW FILE########
