__FILENAME__ = updateArkcmake
#!/usr/bin/python
# Author: Lenna X. Peterson (github.com/lennax)
# Based on bash script by James Goppert (github.com/jgoppert)
#
# script used to update cmake modules from git repo, can't make this
# a submodule otherwise it won't know how to interpret the CMakeLists.txt
# # # # # # subprocess# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

import os # for os.path
import subprocess # for check_call()

clone_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
print clone_path
os.chdir(clone_path)
subprocess.check_call(["git", "clone", "git://github.com/arktools/arkcmake.git","arkcmake_tmp"])
subprocess.check_call(["rm", "-rf", "arkcmake_tmp/.git"])
if os.path.isdir("arkcmake"):
	subprocess.check_call(["rm", "-rf", "arkcmake"])
subprocess.check_call(["mv", "arkcmake_tmp", "arkcmake"])

########NEW FILE########
__FILENAME__ = mavgenerate
#!/usr/bin/env python
"""\
generate.py is a GUI front-end for mavgen, a python based MAVLink
header generation tool.

Notes:
-----
* 2012-7-16 -- dagoodman
    Working on Mac 10.6.8 darwin, with Python 2.7.1

* 2012-7-17 -- dagoodman
    Only GUI code working on Mac 10.6.8 darwin, with Python 3.2.3
    Working on Windows 7 SP1, with Python 2.7.3 and 3.2.3
    Mavgen doesn't work with Python 3.x yet

* 2012-9-25 -- dagoodman
    Passing error limit into mavgen to make output cleaner.

Copyright 2012 David Goodman (dagoodman@soe.ucsc.edu)
Released under GNU GPL version 3 or later

"""
import os
import re
import pprint

# Python 2.x and 3.x compatability
try:
    from tkinter import *
    import tkinter.filedialog
    import tkinter.messagebox
except ImportError as ex:
    # Must be using Python 2.x, import and rename
    from Tkinter import *
    import tkFileDialog
    import tkMessageBox

    tkinter.filedialog = tkFileDialog
    del tkFileDialog
    tkinter.messagebox = tkMessageBox
    del tkMessageBox

sys.path.append(os.path.join('pymavlink','generator'))
from mavgen import *

DEBUG = False
title = "MAVLink Generator"
error_limit = 5


class Application(Frame):
    def __init__(self, master=None):
        Frame.__init__(self, master)
        self.pack_propagate(0)
        self.grid( sticky=N+S+E+W)
        self.createWidgets()
        self.pp = pprint.PrettyPrinter(indent=4)

    """\
    Creates the gui and all of its content.
    """
    def createWidgets(self):


        #----------------------------------------
        # Create the XML entry

        self.xml_value = StringVar()
        self.xml_label = Label( self, text="XML" )
        self.xml_label.grid(row=0, column = 0)
        self.xml_entry = Entry( self, width = 26, textvariable=self.xml_value )
        self.xml_entry.grid(row=0, column = 1)
        self.xml_button = Button (self, text="Browse", command=self.browseXMLFile)
        self.xml_button.grid(row=0, column = 2)

        #----------------------------------------
        # Create the Out entry

        self.out_value = StringVar()
        self.out_label = Label( self, text="Out" )
        self.out_label.grid(row=1,column = 0)
        self.out_entry = Entry( self, width = 26, textvariable=self.out_value )
        self.out_entry.grid(row=1, column = 1)
        self.out_button = Button (self, text="Browse", command=self.browseOutDirectory)
        self.out_button.grid(row=1, column = 2)

        #----------------------------------------
        # Create the Lang box

        self.language_value = StringVar()
        self.language_choices = [ "C", "Python", "CS", "Javascript", "WLua" ]
        self.language_label = Label( self, text="Lang" )
        self.language_label.grid(row=2, column=0)
        self.language_menu = OptionMenu(self,self.language_value,*self.language_choices)
        self.language_value.set(self.language_choices[0])
        self.language_menu.config(width=10)
        self.language_menu.grid(row=2, column=1,sticky=W)

        #----------------------------------------
        # Create the Protocol box

        self.protocol_value = StringVar()
        self.protocol_choices = [ "v0.9", "v1.0" ]
        self.protocol_label = Label( self, text="Protocol")
        self.protocol_label.grid(row=3, column=0)
        self.protocol_menu = OptionMenu(self,self.protocol_value,*self.protocol_choices)
        self.protocol_value.set(self.protocol_choices[1])
        self.protocol_menu.config(width=10)
        self.protocol_menu.grid(row=3, column=1,sticky=W)

        #----------------------------------------
        # Create the generate button

        self.generate_button = Button ( self, text="Generate", command=self.generateHeaders)
        self.generate_button.grid(row=4,column=1)

    """\
    Open a file selection window to choose the XML message definition.
    """
    def browseXMLFile(self):
        # TODO Allow specification of multipe XML definitions
        xml_file = tkinter.filedialog.askopenfilename(parent=self, title='Choose a definition file')
        if DEBUG:
            print("XML: " + xml_file)
        if xml_file != None:
            self.xml_value.set(xml_file)

    """\
    Open a directory selection window to choose an output directory for
    headers.
    """
    def browseOutDirectory(self):
        mavlinkFolder = os.path.dirname(os.path.realpath(__file__))
        out_dir = tkinter.filedialog.askdirectory(parent=self,initialdir=mavlinkFolder,title='Please select an output directory')
        if DEBUG:
            print("Output: " + out_dir)
        if out_dir != None:
            self.out_value.set(out_dir)

    """\
    Generates the header files and place them in the output directory.
    """
    def generateHeaders(self):
        # Verify settings
        rex = re.compile(".*\\.xml$", re.IGNORECASE)
        if not self.xml_value.get():
            tkinter.messagebox.showerror('Error Generating Headers','An XML message defintion file must be specified.')
            return

        if not self.out_value.get():
            tkinter.messagebox.showerror('Error Generating Headers', 'An output directory must be specified.')
            return


        if os.path.isdir(self.out_value.get()):
            if not tkinter.messagebox.askokcancel('Overwrite Headers?','The output directory \'{0}\' already exists. Headers may be overwritten if they already exist.'.format(self.out_value.get())):
                return

        # Verify XML file with schema (or do this in mavgen)
        # TODO write XML schema (XDS)

        # Generate headers
        opts = MavgenOptions(self.language_value.get(), self.protocol_value.get()[1:], self.out_value.get(), error_limit);
        args = [self.xml_value.get()]
        if DEBUG:
            print("Generating headers")
            self.pp.pprint(opts)
            self.pp.pprint(args)
        try:
            mavgen(opts,args)
            tkinter.messagebox.showinfo('Successfully Generated Headers', 'Headers generated succesfully.')

        except Exception as ex:
            exStr = formatErrorMessage(str(ex));
            if DEBUG:
                print('An occurred while generating headers:\n\t{0!s}'.format(ex))
            tkinter.messagebox.showerror('Error Generating Headers','{0!s}'.format(exStr))
            return

"""\
Format the mavgen exceptions by removing "ERROR: ".
"""
def formatErrorMessage(message):
    reObj = re.compile(r'^(ERROR):\s+',re.M);
    matches = re.findall(reObj, message);
    prefix = ("An error occurred in mavgen:" if len(matches) == 1 else "Errors occured in mavgen:\n")
    message = re.sub(reObj, '\n', message);

    return prefix + message


# End of Application class
# ---------------------------------

"""\
This class mimicks an ArgumentParser Namespace since mavgen only
accepts an object for its opts argument.
"""
class MavgenOptions:
    def __init__(self,language,protocol,output,error_limit):
        self.language = language
        self.wire_protocol = protocol
        self.output = output
        self.error_limit = error_limit;
# End of MavgenOptions class 
# ---------------------------------


# ---------------------------------
# Start

if __name__ == '__main__':
  app = Application()
  app.master.title(title)
  app.mainloop()

########NEW FILE########
__FILENAME__ = DFReader
#!/usr/bin/env python
'''
APM DataFlash log file reader

Copyright Andrew Tridgell 2011
Released under GNU GPL version 3 or later

Partly based on SDLog2Parser by Anton Babushkin
'''

import struct, time, os
from pymavlink import mavutil

FORMAT_TO_STRUCT = {
    "b": ("b", None, int),
    "B": ("B", None, int),
    "h": ("h", None, int),
    "H": ("H", None, int),
    "i": ("i", None, int),
    "I": ("I", None, int),
    "f": ("f", None, float),
    "n": ("4s", None, str),
    "N": ("16s", None, str),
    "Z": ("64s", None, str),
    "c": ("h", 0.01, float),
    "C": ("H", 0.01, float),
    "e": ("i", 0.01, float),
    "E": ("I", 0.01, float),
    "L": ("i", 1.0e-7, float),
    "M": ("b", None, int),
    "q": ("q", None, int),
    "Q": ("Q", None, int),
    }

class DFFormat(object):
    def __init__(self, type, name, len, format, columns):
        self.type = type
        self.name = name
        self.len = len
        self.format = format
        self.columns = columns.split(',')

        msg_struct = "<"
        msg_mults = []
        msg_types = []
        for c in format:
            if ord(c) == 0:
                break
            try:
                (s, mul, type) = FORMAT_TO_STRUCT[c]
                msg_struct += s
                msg_mults.append(mul)
                msg_types.append(type)
            except KeyError as e:
                raise Exception("Unsupported format char: '%s' in message %s" % (c, name))

        self.msg_struct = msg_struct
        self.msg_types = msg_types
        self.msg_mults = msg_mults

def null_term(str):
    '''null terminate a string'''
    idx = str.find("\0")
    if idx != -1:
        str = str[:idx]
    return str

class DFMessage(object):
    def __init__(self, fmt, elements, apply_multiplier):
        self._d = {}
        self.fmt = fmt
        for i in range(len(fmt.columns)):
            mul = fmt.msg_mults[i]
            name = fmt.columns[i]
            self._d[name] = elements[i]
            if fmt.format[i] != 'M' or apply_multiplier:
                self._d[name] = fmt.msg_types[i](self._d[name])
            if fmt.msg_types[i] == str:
                self._d[name] = self._d[name]
                self._d[name] = null_term(self._d[name])
            if mul is not None and apply_multiplier:
                self._d[name] = self._d[name] * mul
        self._fieldnames = fmt.columns
        self.__dict__.update(self._d)

    def get_type(self):
        return self.fmt.name

    def __str__(self):
        ret = "%s {" % self.fmt.name
        for c in self.fmt.columns:
            ret += "%s : %s, " % (c, self._d[c])
        ret = ret[:-2] + "}"
        return ret

    def get_msgbuf(self):
        '''create a binary message buffer for a message'''
        values = []
        for i in range(len(self.fmt.columns)):
            mul = self.fmt.msg_mults[i]
            name = self.fmt.columns[i]
            if name == 'Mode' and 'ModeNum' in self.fmt.columns:
                name = 'ModeNum'
            v = self._d[name]
            if mul is not None:
                v /= mul
            values.append(v)
        return struct.pack("BBB", 0xA3, 0x95, self.fmt.type) + struct.pack(self.fmt.msg_struct, *values)
                

class DFReader(object):
    '''parse a generic dataflash file'''
    def __init__(self):
        # read the whole file into memory for simplicity
        self.msg_rate = {}
        self.new_timestamps = False
        self.interpolated_timestamps = False
        self.px4_timestamps = False
        self.px4_timebase = 0
        self.timestamp = 0
        self.mav_type = mavutil.mavlink.MAV_TYPE_FIXED_WING
        self.verbose = False
        self.params = {}
        
    def _rewind(self):
        '''reset counters on rewind'''
        self.counts = {}
        self.counts_since_gps = {}
        self.messages = { 'MAV' : self }
        self.flightmode = "UNKNOWN"
        self.percent = 0

    def _gpsTimeToTime(self, week, sec):
        '''convert GPS week and TOW to a time in seconds since 1970'''
        epoch = 86400*(10*365 + (1980-1969)/4 + 1 + 6 - 2)
        return epoch + 86400*7*week + sec - 15

    def _find_time_base_new(self, gps):
        '''work out time basis for the log - new style'''
        t = self._gpsTimeToTime(gps.Week, gps.TimeMS*0.001)
        self.timebase = t - gps.T*0.001
        self.new_timestamps = True

    def _find_time_base_px4(self, gps):
        '''work out time basis for the log - PX4 native'''
        t = gps.GPSTime * 1.0e-6
        self.timebase = t - self.px4_timebase
        self.px4_timestamps = True

    def _find_time_base(self):
        '''work out time basis for the log'''
        self.timebase = 0
        if self._zero_time_base:
            return
        gps1 = self.recv_match(type='GPS', condition='getattr(GPS,"Week",0)!=0 or getattr(GPS,"GPSTime",0)!=0')
        if gps1 is None:
            self._rewind()
            return

        if 'GPSTime' in gps1._fieldnames:
            self._find_time_base_px4(gps1)
            self._rewind()
            return
            
        if 'T' in gps1._fieldnames:
            # it is a new style flash log with full timestamps
            self._find_time_base_new(gps1)
            self._rewind()
            return
        
        counts1 = self.counts.copy()
        gps2 = self.recv_match(type='GPS', condition='GPS.Week!=0')
        counts2 = self.counts.copy()

        if gps1 is None or gps2 is None:
            self._rewind()
            return
        
        t1 = self._gpsTimeToTime(gps1.Week, gps1.TimeMS*0.001)
        t2 = self._gpsTimeToTime(gps2.Week, gps2.TimeMS*0.001)
        if t2 == t1:
            self._rewind()
            return
        for type in counts2:
            self.msg_rate[type] = (counts2[type] - counts1[type]) / float(t2-t1)
            if self.msg_rate[type] == 0:
                self.msg_rate[type] = 1
        self._rewind()
        
    def _adjust_time_base(self, m):
        '''adjust time base from GPS message'''
        if self._zero_time_base:
            return
        if self.new_timestamps and not self.interpolated_timestamps:
            return
        if self.px4_timestamps:
            return
        if getattr(m, 'Week', None) is None:
            return
        t = self._gpsTimeToTime(m.Week, m.TimeMS*0.001)
        deltat = t - self.timebase
        if deltat <= 0:
            return
        for type in self.counts_since_gps:
            rate = self.counts_since_gps[type] / deltat
            if rate > self.msg_rate.get(type, 0):
                self.msg_rate[type] = rate
        self.msg_rate['IMU'] = 50.0
        self.msg_rate['ATT'] = 50.0
        self.timebase = t
        self.counts_since_gps = {}        

    def _set_time(self, m):
        '''set time for a message'''
        if self.px4_timestamps:
            m._timestamp = self.timebase + self.px4_timebase
        elif self._zero_time_base or (self.new_timestamps and not self.interpolated_timestamps):
            if m.get_type() in ['ATT'] and not 'TimeMS' in m._fieldnames:
                # old copter logs without TimeMS on key messages
                self.interpolated_timestamps = True
            if m.get_type() in ['GPS','GPS2']:
                m._timestamp = self.timebase + m.T*0.001
            elif 'TimeMS' in m._fieldnames:
                m._timestamp = self.timebase + m.TimeMS*0.001
            else:
                m._timestamp = self.timestamp
        else:
            rate = self.msg_rate.get(m.fmt.name, 50.0)
            count = self.counts_since_gps.get(m.fmt.name, 0)
            m._timestamp = self.timebase + count/rate
        self.timestamp = m._timestamp

    def recv_msg(self):
        return self._parse_next()

    def _add_msg(self, m):
        '''add a new message'''
        type = m.get_type()
        self.messages[type] = m
        if not type in self.counts:
            self.counts[type] = 0
        else:
            self.counts[type] += 1
        if not type in self.counts_since_gps:
            self.counts_since_gps[type] = 0
        else:
            self.counts_since_gps[type] += 1

        if type == 'TIME' and 'StartTime' in m._fieldnames:
            self.px4_timebase = m.StartTime * 1.0e-6
            self.px4_timestamps = True
        if type == 'GPS':
            self._adjust_time_base(m)
        if type == 'MSG':
            if m.Message.startswith("ArduRover"):
                self.mav_type = mavutil.mavlink.MAV_TYPE_GROUND_ROVER
            elif m.Message.startswith("ArduPlane"):
                self.mav_type = mavutil.mavlink.MAV_TYPE_FIXED_WING
            elif m.Message.startswith("ArduCopter"):
                self.mav_type = mavutil.mavlink.MAV_TYPE_QUADROTOR
            elif m.Message.startswith("Antenna"):
                self.mav_type = mavutil.mavlink.MAV_TYPE_ANTENNA_TRACKER
        if type == 'MODE':
            if isinstance(m.Mode, str):
                self.flightmode = m.Mode.upper()
            elif 'ModeNum' in m._fieldnames:
                mapping = mavutil.mode_mapping_bynumber(self.mav_type)
                if mapping is not None and m.ModeNum in mapping:
                    self.flightmode = mapping[m.ModeNum]
            else:
                self.flightmode = mavutil.mode_string_acm(m.Mode)
        if type == 'STAT':
            if 'MainState' in m._fieldnames:
                self.flightmode = mavutil.mode_string_px4(m.MainState)
            else:
                self.flightmode = "UNKNOWN"
        if type == 'PARM' and getattr(m, 'Name', None) is not None:
            self.params[m.Name] = m.Value
        self._set_time(m)

    def recv_match(self, condition=None, type=None, blocking=False):
        '''recv the next message that matches the given condition
        type can be a string or a list of strings'''
        if type is not None and not isinstance(type, list):
            type = [type]
        while True:
            m = self.recv_msg()
            if m is None:
                return None
            if type is not None and not m.get_type() in type:
                continue
            if not mavutil.evaluate_condition(condition, self.messages):
                continue
            return m

    def check_condition(self, condition):
        '''check if a condition is true'''
        return mavutil.evaluate_condition(condition, self.messages)

    def param(self, name, default=None):
        '''convenient function for returning an arbitrary MAVLink
           parameter with a default'''
        if not name in self.params:
            return default
        return self.params[name]

class DFReader_binary(DFReader):
    '''parse a binary dataflash file'''
    def __init__(self, filename, zero_time_base):
        DFReader.__init__(self)
        # read the whole file into memory for simplicity
        f = open(filename, mode='rb')
        self.data = f.read()
        f.close()
        self.HEAD1 = 0xA3
        self.HEAD2 = 0x95
        self.formats = {
            0x80 : DFFormat(0x80, 'FMT', 89, 'BBnNZ', "Type,Length,Name,Format,Columns")
        }
        self._rewind()
        self._zero_time_base = zero_time_base
        self._find_time_base()
        self._rewind()

    def _rewind(self):
        '''rewind to start of log'''
        DFReader._rewind(self)
        self.offset = 0
        self.remaining = len(self.data)

    def _parse_next(self):
        '''read one message, returning it as an object'''
        if len(self.data) - self.offset < 3:
            return None
            
        hdr = self.data[self.offset:self.offset+3]
        skip_bytes = 0
        skip_type = None
        # skip over bad messages
        while (ord(hdr[0]) != self.HEAD1 or ord(hdr[1]) != self.HEAD2 or ord(hdr[2]) not in self.formats):
            if skip_type is None:
                skip_type = (ord(hdr[0]), ord(hdr[1]), ord(hdr[2]))
            skip_bytes += 1
            self.offset += 1
            if len(self.data) - self.offset < 3:
                return None
            hdr = self.data[self.offset:self.offset+3]
        msg_type = ord(hdr[2])
        if skip_bytes != 0:
            print("Skipped %u bad bytes in log %s" % (skip_bytes, skip_type))

        self.offset += 3
        self.remaining -= 3

        if not msg_type in self.formats:
            if self.verbose:
                print("unknown message type %02x" % msg_type)
            raise Exception("Unknown message type %02x" % msg_type)
        fmt = self.formats[msg_type]
        if self.remaining < fmt.len-3:
            # out of data - can often happen half way through a message
            if self.verbose:
                print("out of data")
            return None
        body = self.data[self.offset:self.offset+(fmt.len-3)]
        try:
            elements = list(struct.unpack(fmt.msg_struct, body))
        except Exception:
            print("Failed to parse %s/%s with len %u (remaining %u)" % (fmt.name, fmt.msg_struct, len(body), self.remaining))
            raise
        name = null_term(fmt.name)
        if name == 'FMT' and elements[0] not in self.formats:
            # add to formats
            # name, len, format, headings
            self.formats[elements[0]] = DFFormat(elements[0],
                                                 null_term(elements[2]), elements[1],
                                                 null_term(elements[3]), null_term(elements[4]))

        self.offset += fmt.len-3
        self.remaining -= fmt.len-3
        m = DFMessage(fmt, elements, True)
        self._add_msg(m)

        self.percent = 100.0 * (self.offset / float(len(self.data)))
        
        return m

def DFReader_is_text_log(filename):
    '''return True if a file appears to be a valid text log'''
    f = open(filename)
    ret = (f.read(8000).find('FMT, ') != -1)
    f.close()
    return ret

class DFReader_text(DFReader):
    '''parse a text dataflash file'''
    def __init__(self, filename, zero_time_base=False):
        DFReader.__init__(self)
        # read the whole file into memory for simplicity
        f = open(filename, mode='r')
        self.lines = f.readlines()
        f.close()
        self.formats = {
            'FMT' : DFFormat(0x80, 'FMT', 89, 'BBnNZ', "Type,Length,Name,Format,Columns")
        }
        self._rewind()
        self._zero_time_base = zero_time_base
        self._find_time_base()
        self._rewind()

    def _rewind(self):
        '''rewind to start of log'''
        DFReader._rewind(self)
        self.line = 0
        # find the first valid line
        while self.line < len(self.lines):
            if self.lines[self.line].startswith("FMT, "):
                break
            self.line += 1

    def _parse_next(self):
        '''read one message, returning it as an object'''
        while self.line < len(self.lines):
            s = self.lines[self.line].rstrip()
            elements = s.split(", ")
            # move to next line
            self.line += 1
            if len(elements) >= 2:
                break

        # cope with empty structures
        if len(elements) == 5 and elements[-1] == ',':
            elements[-1] = ''
            elements.append('')

        self.percent = 100.0 * (self.line / float(len(self.lines)))

        if self.line >= len(self.lines):
            return None

        msg_type = elements[0]

        if not msg_type in self.formats:
            return None
        
        fmt = self.formats[msg_type]

        if len(elements) < len(fmt.format)+1:
            # not enough columns
            return None

        elements = elements[1:]
        
        name = fmt.name.rstrip('\0')
        if name == 'FMT':
            # add to formats
            # name, len, format, headings
            self.formats[elements[2]] = DFFormat(int(elements[0]), elements[2], int(elements[1]), elements[3], elements[4])

        m = DFMessage(fmt, elements, False)
        self._add_msg(m)

        return m

if __name__ == "__main__":
    import sys
    filename = sys.argv[1]
    if filename.endswith('.log'):
        log = DFReader_text(filename)
    else:
        log = DFReader_binary(filename)
    while True:
        m = log.recv_msg()
        if m is None:
            break
        print(m)

########NEW FILE########
__FILENAME__ = apmsetrate
#!/usr/bin/env python

'''
set stream rate on an APM 
'''

import sys, struct, time, os

from optparse import OptionParser
parser = OptionParser("apmsetrate.py [options]")

parser.add_option("--baudrate", dest="baudrate", type='int',
                  help="master port baud rate", default=115200)
parser.add_option("--device", dest="device", default=None, help="serial device")
parser.add_option("--rate", dest="rate", default=4, type='int', help="requested stream rate")
parser.add_option("--source-system", dest='SOURCE_SYSTEM', type='int',
                  default=255, help='MAVLink source system for this GCS')
parser.add_option("--showmessages", dest="showmessages", action='store_true',
                  help="show incoming messages", default=False)
(opts, args) = parser.parse_args()

from pymavlink import mavutil

if opts.device is None:
    print("You must specify a serial device")
    sys.exit(1)

def wait_heartbeat(m):
    '''wait for a heartbeat so we know the target system IDs'''
    print("Waiting for APM heartbeat")
    m.wait_heartbeat()
    print("Heartbeat from APM (system %u component %u)" % (m.target_system, m.target_system))

def show_messages(m):
    '''show incoming mavlink messages'''
    while True:
        msg = m.recv_match(blocking=True)
        if not msg:
            return
        if msg.get_type() == "BAD_DATA":
            if mavutil.all_printable(msg.data):
                sys.stdout.write(msg.data)
                sys.stdout.flush()
        else:
            print(msg)                    
                
# create a mavlink serial instance
master = mavutil.mavlink_connection(opts.device, baud=opts.baudrate)

# wait for the heartbeat msg to find the system ID
wait_heartbeat(master)

print("Sending all stream request for rate %u" % opts.rate)
for i in range(0, 3):
    master.mav.request_data_stream_send(master.target_system, master.target_component,
                                        mavutil.mavlink.MAV_DATA_STREAM_ALL, opts.rate, 1)
if opts.showmessages:
    show_messages(master)

########NEW FILE########
__FILENAME__ = bwtest
#!/usr/bin/env python

'''
check bandwidth of link
'''

import sys, struct, time, os

from pymavlink import mavutil

from optparse import OptionParser
parser = OptionParser("bwtest.py [options]")

parser.add_option("--baudrate", dest="baudrate", type='int',
                  help="master port baud rate", default=115200)
parser.add_option("--device", dest="device", default=None, help="serial device")
(opts, args) = parser.parse_args()

if opts.device is None:
    print("You must specify a serial device")
    sys.exit(1)

# create a mavlink serial instance
master = mavutil.mavlink_connection(opts.device, baud=opts.baudrate)

t1 = time.time()

counts = {}

bytes_sent = 0
bytes_recv = 0

while True:
    master.mav.heartbeat_send(1, 1)
    master.mav.sys_status_send(1, 2, 3, 4, 5, 6, 7)
    master.mav.gps_raw_send(1, 2, 3, 4, 5, 6, 7, 8, 9)
    master.mav.attitude_send(1, 2, 3, 4, 5, 6, 7)
    master.mav.vfr_hud_send(1, 2, 3, 4, 5, 6)
    while master.port.inWaiting() > 0:
        m = master.recv_msg()
        if m == None: break
        if m.get_type() not in counts:
            counts[m.get_type()] = 0
        counts[m.get_type()] += 1
    t2 = time.time()
    if t2 - t1 > 1.0:
        print("%u sent, %u received, %u errors bwin=%.1f kB/s bwout=%.1f kB/s" % (
            master.mav.total_packets_sent,
            master.mav.total_packets_received,
            master.mav.total_receive_errors,
            0.001*(master.mav.total_bytes_received-bytes_recv)/(t2-t1),
            0.001*(master.mav.total_bytes_sent-bytes_sent)/(t2-t1)))
        bytes_sent = master.mav.total_bytes_sent
        bytes_recv = master.mav.total_bytes_received
        t1 = t2

########NEW FILE########
__FILENAME__ = magtest
#!/usr/bin/env python

'''
rotate APMs on bench to test magnetometers

'''

import sys, os, time
from math import radians

from pymavlink import mavutil

from optparse import OptionParser
parser = OptionParser("rotate.py [options]")

parser.add_option("--device1", dest="device1", default=None, help="mavlink device1")
parser.add_option("--device2", dest="device2", default=None, help="mavlink device2")
parser.add_option("--baudrate", dest="baudrate", type='int',
                  help="master port baud rate", default=115200)
(opts, args) = parser.parse_args()

if opts.device1 is None or opts.device2 is None:
    print("You must specify a mavlink device")
    sys.exit(1)

def set_attitude(rc3, rc4):
    global mav1, mav2
    values = [ 65535 ] * 8
    values[2] = rc3
    values[3] = rc4
    mav1.mav.rc_channels_override_send(mav1.target_system, mav1.target_component, *values)
    mav2.mav.rc_channels_override_send(mav2.target_system, mav2.target_component, *values)


# create a mavlink instance
mav1 = mavutil.mavlink_connection(opts.device1, baud=opts.baudrate)

# create a mavlink instance
mav2 = mavutil.mavlink_connection(opts.device2, baud=opts.baudrate)

print("Waiting for HEARTBEAT")
mav1.wait_heartbeat()
mav2.wait_heartbeat()
print("Heartbeat from APM (system %u component %u)" % (mav1.target_system, mav1.target_system))
print("Heartbeat from APM (system %u component %u)" % (mav2.target_system, mav2.target_system))

print("Waiting for MANUAL mode")
mav1.recv_match(type='SYS_STATUS', condition='SYS_STATUS.mode==2 and SYS_STATUS.nav_mode==4', blocking=True)
mav2.recv_match(type='SYS_STATUS', condition='SYS_STATUS.mode==2 and SYS_STATUS.nav_mode==4', blocking=True)

print("Setting declination")
mav1.mav.param_set_send(mav1.target_system, mav1.target_component,
                       'COMPASS_DEC', radians(12.33))
mav2.mav.param_set_send(mav2.target_system, mav2.target_component,
                       'COMPASS_DEC', radians(12.33))


set_attitude(1060, 1160)

event = mavutil.periodic_event(30)
pevent = mavutil.periodic_event(0.3)
rc3_min = 1060
rc3_max = 1850
rc4_min = 1080
rc4_max = 1500
rc3 = rc3_min
rc4 = 1160
delta3 = 2
delta4 = 1
use_pitch = 1

MAV_ACTION_CALIBRATE_GYRO = 17
mav1.mav.action_send(mav1.target_system, mav1.target_component, MAV_ACTION_CALIBRATE_GYRO)
mav2.mav.action_send(mav2.target_system, mav2.target_component, MAV_ACTION_CALIBRATE_GYRO)

print("Waiting for gyro calibration")
mav1.recv_match(type='ACTION_ACK')
mav2.recv_match(type='ACTION_ACK')

print("Resetting mag offsets")
mav1.mav.set_mag_offsets_send(mav1.target_system, mav1.target_component, 0, 0, 0)
mav2.mav.set_mag_offsets_send(mav2.target_system, mav2.target_component, 0, 0, 0)

def TrueHeading(SERVO_OUTPUT_RAW):
    p = float(SERVO_OUTPUT_RAW.servo3_raw - rc3_min) / (rc3_max - rc3_min)
    return 172 + p*(326 - 172)

while True:
    mav1.recv_msg()
    mav2.recv_msg()
    if event.trigger():
        if not use_pitch:
            rc4 = 1160
        set_attitude(rc3, rc4)
        rc3 += delta3
        if rc3 > rc3_max or rc3 < rc3_min:
            delta3 = -delta3
            use_pitch ^= 1
        rc4 += delta4
        if rc4 > rc4_max or rc4 < rc4_min:
            delta4 = -delta4
    if pevent.trigger():
        print "hdg1: %3u hdg2: %3u  ofs1: %4u, %4u, %4u  ofs2: %4u, %4u, %4u" % (
            mav1.messages['VFR_HUD'].heading,
            mav2.messages['VFR_HUD'].heading,
            mav1.messages['SENSOR_OFFSETS'].mag_ofs_x,
            mav1.messages['SENSOR_OFFSETS'].mag_ofs_y,
            mav1.messages['SENSOR_OFFSETS'].mag_ofs_z,
            mav2.messages['SENSOR_OFFSETS'].mag_ofs_x,
            mav2.messages['SENSOR_OFFSETS'].mag_ofs_y,
            mav2.messages['SENSOR_OFFSETS'].mag_ofs_z,
            )
    time.sleep(0.01)

# 314M 326G
# 160M 172G


########NEW FILE########
__FILENAME__ = mav2pcap
#!/usr/bin/env python

# Copyright 2012, Holger Steinhaus
# Released under the GNU GPL version 3 or later

# This program packetizes a binary MAVLink stream. The resulting packets are stored into a PCAP file, which is 
# compatible to tools like Wireshark. 

# The program tries to synchronize to the packet structure in a robust way, using the SOF magic, the potential
# packet length information and the next SOF magic. Additionally the CRC is verified. 

# Hint: A MAVLink protocol dissector (parser) for Wireshark may be generated by mavgen.py.

# dependency: Python construct library (python-construct on Debian/Ubuntu), "easy_install construct" elsewhere


import sys
import os

from pymavlink import mavutil

from construct import ULInt16, Struct, Byte, Bytes, Const
from construct.core import FieldError
from optparse import OptionParser

 
MAVLINK_MAGIC = 0xfe
write_junk = True

# copied from ardupilotmega.h (git changeset 694536afb882068f50da1fc296944087aa207f9f, Dec 02 2012
MAVLINK_MESSAGE_CRCS  = (50, 124, 137, 0, 237, 217, 104, 119, 0, 0, 0, 89, 0, 0, 0, 0, 0, 0, 0, 0, 214, 159, 220, 168, 24, 23, 170, 144, 67, 115, 39, 246, 185, 104, 237, 244, 242, 212, 9, 254, 230, 28, 28, 132, 221, 232, 11, 153, 41, 39, 214, 223, 141, 33, 15, 3, 100, 24, 239, 238, 30, 240, 183, 130, 130, 0, 148, 21, 0, 243, 124, 0, 0, 0, 20, 0, 152, 143, 0, 0, 127, 106, 0, 0, 0, 0, 0, 0, 0, 231, 183, 63, 54, 0, 0, 0, 0, 0, 0, 0, 175, 102, 158, 208, 56, 93, 0, 0, 0, 0, 235, 93, 124, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 42, 241, 15, 134, 219, 208, 188, 84, 22, 19, 21, 134, 0, 78, 68, 189, 127, 111, 21, 21, 144, 1, 234, 73, 181, 22, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 204, 49, 170, 44, 83, 46, 0)


import __builtin__
import struct

# Helper class for writing pcap files
class pcap:
    """
       Used under the terms of GNU GPL v3. 
       Original author: Neale Pickett
       see http://dirtbags.net/py-pcap.html
    """
    _MAGIC = 0xA1B2C3D4
    def __init__(self, stream, mode='rb', snaplen=65535, linktype=1):
        try:
            self.stream = __builtin__.open(stream, mode)
        except TypeError:
            self.stream = stream
        try:
            # Try reading
            hdr = self.stream.read(24)
        except IOError:
            hdr = None

        if hdr:
            # We're in read mode
            self._endian = pcap.None
            for endian in '<>':
                (self.magic,) = struct.unpack(endian + 'I', hdr[:4])
                if self.magic == pcap._MAGIC:
                    self._endian = endian
                    break
            if not self._endian:
                raise IOError('Not a pcap file')
            (self.magic, version_major, version_minor,
             self.thiszone, self.sigfigs,
             self.snaplen, self.linktype) = struct.unpack(self._endian + 'IHHIIII', hdr)
            if (version_major, version_minor) != (2, 4):
                raise IOError('Cannot handle file version %d.%d' % (version_major,
                                                                    version_minor))
        else:
            # We're in write mode
            self._endian = '='
            self.magic = pcap._MAGIC
            version_major = 2
            version_minor = 4
            self.thiszone = 0
            self.sigfigs = 0
            self.snaplen = snaplen
            self.linktype = linktype
            hdr = struct.pack(self._endian + 'IHHIIII',
                              self.magic, version_major, version_minor,
                              self.thiszone, self.sigfigs,
                              self.snaplen, self.linktype)
            self.stream.write(hdr)
        self.version = (version_major, version_minor)

    def read(self):
        hdr = self.stream.read(16)
        if not hdr:
            return
        (tv_sec, tv_usec, caplen, length) = struct.unpack(self._endian + 'IIII', hdr)
        datum = self.stream.read(caplen)
        return ((tv_sec, tv_usec, length), datum)

    def write(self, packet):
        (header, datum) = packet
        (tv_sec, tv_usec, length) = header
        hdr = struct.pack(self._endian + 'IIII', tv_sec, tv_usec, length, len(datum))
        self.stream.write(hdr)
        self.stream.write(datum)

    def __iter__(self):
        while True:
            r = self.read()
            if not r:
                break
            yield r


def find_next_frame(data):
    """
    find a potential start of frame
    """
    return data.find('\xfe')


def parse_header(data):
    """
    split up header information (using construct)
    """
    mavlink_header = Struct('header',
        Const(Byte('magic'), MAVLINK_MAGIC),
        Byte('plength'),
        Byte('sequence'),
        Byte('sysid'),
        Byte('compid'),
        Byte('msgid'),
    )
    return mavlink_header.parse(data[0:6])
    
    
def write_packet(number, data, flags, pkt_length):
    pcap_header = (number, flags, pkt_length)
    pcap_file.write((pcap_header, data))


def convert_file(mavlink_file, pcap_file):
    # the whole file is read in a bunch - room for improvement...
    data = mavlink_file.read()

    i=0
    done = False
    skipped_char = None
    junk = ''
    cnt_ok = 0
    cnt_junk = 0
    cnt_crc = 0
    
    while not done:
        i+=1
        # look for potential start of frame
        next_sof = find_next_frame(data)
        if next_sof > 0:
            print "skipped " + str(next_sof) + " bytes"
            if write_junk:
                if skipped_char != None:
                    junk = skipped_char + data[:next_sof]
                    skipped_char = None
                write_packet(i, junk, 0x03, len(junk))
            data = data[next_sof:]
            data[:6]
            cnt_junk += 1
    
        # assume, our 0xFE was the start of a packet
        header = parse_header(data)
        payload_len = header['plength']
        pkt_length = 6 + payload_len + 2
        try:
            pkt_crc = ULInt16('crc').parse(data[pkt_length-2:pkt_length])
        except FieldError:
            # ups, no more data
            done = True
            continue
    
        # peek for the next SOF
        try:
            cc = mavutil.x25crc(data[1:6+payload_len])
            cc.accumulate(chr(MAVLINK_MESSAGE_CRCS[header['msgid']])) 
            x25_crc = cc.crc
            if x25_crc != pkt_crc:
                crc_flag = 0x1
            else:
                crc_flag = 0
            next_magic = data[pkt_length]
            if chr(MAVLINK_MAGIC) != next_magic:
                # damn, retry
                print "packet %d has invalid length, crc error: %d" % (i, crc_flag)
                
                # skip one char to look for a new SOF next round, stow away skipped char
                skipped_char = data[0]
                data = data[1:]
                continue       
            
            # we can consider it a packet now
            pkt = data[:pkt_length]
            write_packet(i, pkt, crc_flag, len(pkt))
            print "packet %d ok, crc error: %d" % (i, crc_flag)
            data = data[pkt_length:]

            if crc_flag:
                cnt_crc += 1
            else:
                cnt_ok += 1
                
    
        except IndexError:
            # ups, no more packets
            done = True
    print "converted %d valid packets, %d crc errors, %d junk fragments (total %f%% of junk)" % (cnt_ok, cnt_crc, cnt_junk, 100.*float(cnt_junk+cnt_crc)/(cnt_junk+cnt_ok+cnt_crc))
    
###############################################################################    

parser = OptionParser("mav2pcap.py [options] <input file> <output file>")
(opts, args) = parser.parse_args()
    
if len(args) < 2:
    print("Usage: mav2pcap.py  <input file> <output file>")
    sys.exit(1)

mavlink_file = open(args[0], 'r')
pcap_file = pcap(args[1], 'w', linktype=147) # special trick: linktype USER0

convert_file(mavlink_file, pcap_file)        

mavlink_file.close()
#pcap_file.close()

########NEW FILE########
__FILENAME__ = mavgps
#!/usr/bin/python
"""
Allows connection of the uBlox u-Center software to
a uBlox GPS device connected to a PX4 or Pixhawk device,
using Mavlink's SERIAL_CONTROL support to route serial
traffic to/from the GPS, and exposing the data to u-Center
via a local TCP connection.

@author: Matthew Lloyd (github@matthewlloyd.net)
"""

from pymavlink import mavutil
from optparse import OptionParser
import socket


def main():
    parser = OptionParser("mavgps.py [options]")
    parser.add_option("--mavport", dest="mavport", default=None,
                      help="Mavlink port name")
    parser.add_option("--mavbaud", dest="mavbaud", type='int',
                      help="Mavlink port baud rate", default=115200)
    parser.add_option("--devnum", dest="devnum", default=2, type='int',
                      help="PX4 UART device number (defaults to GPS port)")
    parser.add_option("--devbaud", dest="devbaud", default=38400, type='int',
                      help="PX4 UART baud rate (defaults to u-Blox GPS baud)")
    parser.add_option("--tcpport", dest="tcpport", default=1001, type='int',
                      help="local TCP port (defaults to 1001)")
    parser.add_option("--debug", dest="debug", default=0, type='int',
                      help="debug level")
    parser.add_option("--buffsize", dest="buffsize", default=128, type='int',
                      help="buffer size")
    (opts, args) = parser.parse_args()

    if opts.mavport is None:
        parser.error("You must specify a Mavlink serial port (--mavport)")

    print "Connecting to MAVLINK..."
    mav_serialport = mavutil.MavlinkSerialPort(
        opts.mavport, opts.mavbaud,
        devnum=opts.devnum, devbaud=opts.devbaud, debug=opts.debug)

    listen_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listen_sock.bind(('127.0.0.1', opts.tcpport))
    listen_sock.listen(1)

    print "Waiting for a TCP connection."
    print "Use tcp://localhost:%d in u-Center." % opts.tcpport
    conn_sock, addr = listen_sock.accept()
    conn_sock.setblocking(0)  # non-blocking mode
    print "TCP connection accepted. Use Ctrl+C to exit."

    while True:
        try:
            data = conn_sock.recv(opts.buffsize)
            if data:
                if opts.debug >= 1:
                    print '>', len(data)
                mav_serialport.write(data)
        except socket.error:
            pass

        data = mav_serialport.read(opts.buffsize)
        if data:
            if opts.debug >= 1:
                print '<', len(data)
            conn_sock.send(data)


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = mavtcpsniff
#!/usr/bin/env python

'''
connect as a client to two tcpip ports on localhost with mavlink packets.    pass them both directions, and show packets in human-readable format on-screen.

this is useful if 
* you have two SITL instances you want to connect to each other and see the comms.
* you have any tcpip based mavlink happening, and want something better than tcpdump 

hint: 
* you can use netcat/nc to do interesting redorection things with each end if you want to.

Copyright Sept 2012 David "Buzz" Bussenschutt
Released under GNU GPL version 3 or later 
'''

import sys, time, os, struct

from pymavlink import mavutil
from pymavlink import mavlinkv10 as mavlink

from optparse import OptionParser
parser = OptionParser("mavfilter.py srcport dstport")

(opts, args) = parser.parse_args()

if len(args) < 1:
    print("Usage: mavfilter.py srcport dstport ")
    sys.exit(1)

srcport =  args[0]
dstport =  args[1]

# gee python string apend is stupid, whatever.  "tcp:localhost:" += srcport  gives: SyntaxError: invalid syntax
msrc = mavutil.mavlink_connection("".join(('tcp:localhost:',srcport)), planner_format=False,
                                  notimestamps=True,
                                  robust_parsing=True)

mdst = mavutil.mavlink_connection("".join(('tcp:localhost:',dstport)), planner_format=False,
                                  notimestamps=True,
                                  robust_parsing=True)


# simple basic byte pass through, no logging or viewing of packets, or analysis etc
#while True:
#  # L -> R
#    m = msrc.recv();
#    mdst.write(m);
#  # R -> L
#    m2 = mdst.recv();
#    msrc.write(m2);


# similar to the above, but with human-readable display of packets on stdout. 
# in this use case we abuse the self.logfile_raw() function to allow 
# us to use the recv_match function ( whch is then calling recv_msg ) , to still get the raw data stream
# which we pass off to the other mavlink connection without any interference.   
# because internally it will call logfile_raw.write() for us.

# here we hook raw output of one to the raw input of the other, and vice versa: 
msrc.logfile_raw = mdst
mdst.logfile_raw = msrc

while True:
  # L -> R
    l = msrc.recv_match();
    if l is not None:
       l_last_timestamp = 0
       if  l.get_type() != 'BAD_DATA':
           l_timestamp = getattr(l, '_timestamp', None)
           if not l_timestamp:
               l_timestamp = l_last_timestamp
           l_last_timestamp = l_timestamp
       
       print("--> %s.%02u: %s\n" % (
           time.strftime("%Y-%m-%d %H:%M:%S",
                         time.localtime(l._timestamp)),
           int(l._timestamp*100.0)%100, l))
           
  # R -> L
    r = mdst.recv_match();
    if r is not None:
       r_last_timestamp = 0
       if r.get_type() != 'BAD_DATA':
           r_timestamp = getattr(r, '_timestamp', None)
           if not r_timestamp:
               r_timestamp = r_last_timestamp
           r_last_timestamp = r_timestamp
   
       print("<-- %s.%02u: %s\n" % (
           time.strftime("%Y-%m-%d %H:%M:%S",
                         time.localtime(r._timestamp)),
           int(r._timestamp*100.0)%100, r))


 

########NEW FILE########
__FILENAME__ = mavtest
#!/usr/bin/env python

import sys, os

from pymavlink import mavlinkv10 as mavlink

class fifo(object):
    def __init__(self):
        self.buf = []
    def write(self, data):
        self.buf += data
        return len(data)
    def read(self):
        return self.buf.pop(0)

# we will use a fifo as an encode/decode buffer
f = fifo()

# create a mavlink instance, which will do IO on file object 'f'
mav = mavlink.MAVLink(f)

# set the WP_RADIUS parameter on the MAV at the end of the link
mav.param_set_send(7, 1, "WP_RADIUS", 101, mavlink.MAV_PARAM_TYPE_REAL32)

# alternatively, produce a MAVLink_param_set object 
# this can be sent via your own transport if you like
m = mav.param_set_encode(7, 1, "WP_RADIUS", 101, mavlink.MAV_PARAM_TYPE_REAL32)

# get the encoded message as a buffer
b = m.get_msgbuf()

# decode an incoming message
m2 = mav.decode(b)

# show what fields it has
print("Got a message with id %u and fields %s" % (m2.get_msgId(), m2.get_fieldnames()))

# print out the fields
print(m2)

########NEW FILE########
__FILENAME__ = mavtester
#!/usr/bin/env python

'''
test mavlink messages
'''

import sys, struct, time, os
from curses import ascii

from pymavlink import mavtest, mavutil

from optparse import OptionParser
parser = OptionParser("mavtester.py [options]")

parser.add_option("--baudrate", dest="baudrate", type='int',
                  help="master port baud rate", default=115200)
parser.add_option("--device", dest="device", default=None, help="serial device")
parser.add_option("--source-system", dest='SOURCE_SYSTEM', type='int',
                  default=255, help='MAVLink source system for this GCS')
(opts, args) = parser.parse_args()

if opts.device is None:
    print("You must specify a serial device")
    sys.exit(1)

def wait_heartbeat(m):
    '''wait for a heartbeat so we know the target system IDs'''
    print("Waiting for APM heartbeat")
    msg = m.recv_match(type='HEARTBEAT', blocking=True)
    print("Heartbeat from APM (system %u component %u)" % (m.target_system, m.target_system))

# create a mavlink serial instance
master = mavutil.mavlink_connection(opts.device, baud=opts.baudrate, source_system=opts.SOURCE_SYSTEM)

# wait for the heartbeat msg to find the system ID
wait_heartbeat(master)

print("Sending all message types")
mavtest.generate_outputs(master.mav)


########NEW FILE########
__FILENAME__ = mav_accel
#!/usr/bin/env python

'''
show accel calibration for a set of logs
'''

import sys, time, os

from optparse import OptionParser
parser = OptionParser("mav_accel.py [options]")
parser.add_option("--no-timestamps",dest="notimestamps", action='store_true', help="Log doesn't have timestamps")
parser.add_option("--planner",dest="planner", action='store_true', help="use planner file format")
parser.add_option("--robust",dest="robust", action='store_true', help="Enable robust parsing (skip over bad data)")

(opts, args) = parser.parse_args()

from pymavlink import mavutil

if len(args) < 1:
    print("Usage: mav_accel.py [options] <LOGFILE...>")
    sys.exit(1)

def process(logfile):
    '''display accel cal for a log file'''
    mlog = mavutil.mavlink_connection(filename,
                                      planner_format=opts.planner,
                                      notimestamps=opts.notimestamps,
                                      robust_parsing=opts.robust)

    m = mlog.recv_match(type='SENSOR_OFFSETS')
    if m is not None:
        z_sensor = (m.accel_cal_z - 9.805) * (4096/9.81)
        print("accel cal %5.2f %5.2f %5.2f %6u  %s" % (
            m.accel_cal_x, m.accel_cal_y, m.accel_cal_z,
            z_sensor,
            logfile))


total = 0.0
for filename in args:
    process(filename)

########NEW FILE########
__FILENAME__ = wptogpx
#!/usr/bin/env python

'''
example program to extract GPS data from a waypoint file, and create a GPX
file, for loading into google earth
'''

import sys, struct, time, os

from optparse import OptionParser
parser = OptionParser("wptogpx.py [options]")
(opts, args) = parser.parse_args()

from pymavlink import mavutil, mavwp

if len(args) < 1:
    print("Usage: wptogpx.py <WPFILE>")
    sys.exit(1)

def wp_to_gpx(infilename, outfilename):
    '''convert a wp file to a GPX file'''

    wp = mavwp.MAVWPLoader()
    wp.load(infilename)
    outf = open(outfilename, mode='w')

    def process_wp(w, i):
        t = time.localtime(i)
        outf.write('''<wpt lat="%s" lon="%s">
  <ele>%s</ele>
  <cmt>WP %u</cmt>
</wpt>
''' % (w.x, w.y, w.z, i))

    def add_header():
        outf.write('''<?xml version="1.0" encoding="UTF-8"?>
<gpx
  version="1.0"
  creator="pymavlink"
  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
  xmlns="http://www.topografix.com/GPX/1/0"
  xsi:schemaLocation="http://www.topografix.com/GPX/1/0 http://www.topografix.com/GPX/1/0/gpx.xsd">
''')

    def add_footer():
        outf.write('''
</gpx>
''')

    add_header()       

    count = 0
    for i in range(wp.count()):
        w = wp.wp(i)
        if w.frame == 3:
            w.z += wp.wp(0).z
        if w.command == 16:
            process_wp(w, i)
        count += 1
    add_footer()
    print("Created %s with %u points" % (outfilename, count))
    

for infilename in args:
    outfilename = infilename + '.gpx'
    wp_to_gpx(infilename, outfilename)

########NEW FILE########
__FILENAME__ = fgFDM
#!/usr/bin/env python
# parse and construct FlightGear NET FDM packets
# Andrew Tridgell, November 2011
# released under GNU GPL version 2 or later

import struct, math

class fgFDMError(Exception):
    '''fgFDM error class'''
    def __init__(self, msg):
        Exception.__init__(self, msg)
        self.message = 'fgFDMError: ' + msg

class fgFDMVariable(object):
    '''represent a single fgFDM variable'''
    def __init__(self, index, arraylength, units):
        self.index   = index
        self.arraylength = arraylength
        self.units = units

class fgFDMVariableList(object):
    '''represent a list of fgFDM variable'''
    def __init__(self):
        self.vars = {}
        self._nextidx = 0
        
    def add(self, varname, arraylength=1, units=None):
        self.vars[varname] = fgFDMVariable(self._nextidx, arraylength, units=units)
        self._nextidx += arraylength

class fgFDM(object):
    '''a flightgear native FDM parser/generator'''
    def __init__(self):
        '''init a fgFDM object'''
        self.FG_NET_FDM_VERSION = 24
        self.pack_string = '>I 4x 3d 6f 11f 3f 2f I 4I 4f 4f 4f 4f 4f 4f 4f 4f 4f I 4f I 3I 3f 3f 3f I i f 10f'
        self.values = [0]*98

        self.FG_MAX_ENGINES = 4
        self.FG_MAX_WHEELS  = 3
        self.FG_MAX_TANKS   = 4

        # supported unit mappings
        self.unitmap = {
            ('radians', 'degrees') : math.degrees(1),
            ('rps',     'dps')     : math.degrees(1),
            ('feet',    'meters')  : 0.3048,
            ('fps',     'mps')     : 0.3048,
            ('knots',   'mps')     : 0.514444444,
            ('knots',   'fps')     : 0.514444444/0.3048,
            ('fpss',    'mpss')    : 0.3048,
            ('seconds', 'minutes') : 60,
            ('seconds', 'hours')   : 3600,
            }

        # build a mapping between variable name and index in the values array
        # note that the order of this initialisation is critical - it must
        # match the wire structure
        self.mapping = fgFDMVariableList()
        self.mapping.add('version')

        # position
        self.mapping.add('longitude', units='radians')	# geodetic (radians)
        self.mapping.add('latitude', units='radians')	# geodetic (radians)
        self.mapping.add('altitude', units='meters')	# above sea level (meters)
        self.mapping.add('agl', units='meters')		# above ground level (meters)

        # attitude
        self.mapping.add('phi', units='radians')	# roll (radians)
        self.mapping.add('theta', units='radians')	# pitch (radians)
        self.mapping.add('psi', units='radians')	# yaw or true heading (radians)
        self.mapping.add('alpha', units='radians')      # angle of attack (radians)
        self.mapping.add('beta', units='radians')       # side slip angle (radians)

        # Velocities
        self.mapping.add('phidot', units='rps')		# roll rate (radians/sec)
        self.mapping.add('thetadot', units='rps')	# pitch rate (radians/sec)
        self.mapping.add('psidot', units='rps')		# yaw rate (radians/sec)
        self.mapping.add('vcas', units='fps')		# calibrated airspeed
        self.mapping.add('climb_rate', units='fps')	# feet per second
        self.mapping.add('v_north', units='fps')        # north velocity in local/body frame, fps
        self.mapping.add('v_east', units='fps')         # east velocity in local/body frame, fps
        self.mapping.add('v_down', units='fps')         # down/vertical velocity in local/body frame, fps
        self.mapping.add('v_wind_body_north', units='fps')   # north velocity in local/body frame
        self.mapping.add('v_wind_body_east', units='fps')    # east velocity in local/body frame
        self.mapping.add('v_wind_body_down', units='fps')    # down/vertical velocity in local/body

        # Accelerations
        self.mapping.add('A_X_pilot', units='fpss')	# X accel in body frame ft/sec^2
        self.mapping.add('A_Y_pilot', units='fpss')	# Y accel in body frame ft/sec^2
        self.mapping.add('A_Z_pilot', units='fpss')	# Z accel in body frame ft/sec^2

        # Stall
        self.mapping.add('stall_warning')               # 0.0 - 1.0 indicating the amount of stall
        self.mapping.add('slip_deg', units='degrees')	# slip ball deflection

        # Engine status
        self.mapping.add('num_engines')	                    # Number of valid engines
        self.mapping.add('eng_state', self.FG_MAX_ENGINES)  # Engine state (off, cranking, running)
        self.mapping.add('rpm',       self.FG_MAX_ENGINES)  # Engine RPM rev/min
        self.mapping.add('fuel_flow', self.FG_MAX_ENGINES)  # Fuel flow gallons/hr
        self.mapping.add('fuel_px',   self.FG_MAX_ENGINES)  # Fuel pressure psi
        self.mapping.add('egt',       self.FG_MAX_ENGINES)  # Exhuast gas temp deg F
        self.mapping.add('cht',       self.FG_MAX_ENGINES)  # Cylinder head temp deg F
        self.mapping.add('mp_osi',    self.FG_MAX_ENGINES)  # Manifold pressure
        self.mapping.add('tit',       self.FG_MAX_ENGINES)  # Turbine Inlet Temperature
        self.mapping.add('oil_temp',  self.FG_MAX_ENGINES)  # Oil temp deg F
        self.mapping.add('oil_px',    self.FG_MAX_ENGINES)  # Oil pressure psi
            
        # Consumables
        self.mapping.add('num_tanks')		            # Max number of fuel tanks
        self.mapping.add('fuel_quantity', self.FG_MAX_TANKS)

        # Gear status
        self.mapping.add('num_wheels')
        self.mapping.add('wow',              self.FG_MAX_WHEELS)
        self.mapping.add('gear_pos',         self.FG_MAX_WHEELS)
        self.mapping.add('gear_steer',       self.FG_MAX_WHEELS)
        self.mapping.add('gear_compression', self.FG_MAX_WHEELS)

        # Environment
        self.mapping.add('cur_time', units='seconds')       # current unix time
        self.mapping.add('warp',     units='seconds')       # offset in seconds to unix time
        self.mapping.add('visibility', units='meters')      # visibility in meters (for env. effects)

        # Control surface positions (normalized values)
        self.mapping.add('elevator')
        self.mapping.add('elevator_trim_tab')
        self.mapping.add('left_flap')
        self.mapping.add('right_flap')
        self.mapping.add('left_aileron')
        self.mapping.add('right_aileron')
        self.mapping.add('rudder')
        self.mapping.add('nose_wheel')
        self.mapping.add('speedbrake')
        self.mapping.add('spoilers')

        self._packet_size = struct.calcsize(self.pack_string)

        self.set('version', self.FG_NET_FDM_VERSION)

        if len(self.values) != self.mapping._nextidx:
            raise fgFDMError('Invalid variable list in initialisation')

    def packet_size(self):
        '''return expected size of FG FDM packets'''
        return self._packet_size

    def convert(self, value, fromunits, tounits):
        '''convert a value from one set of units to another'''
        if fromunits == tounits:
            return value
        if (fromunits,tounits) in self.unitmap:
            return value * self.unitmap[(fromunits,tounits)]
        if (tounits,fromunits) in self.unitmap:
            return value / self.unitmap[(tounits,fromunits)]
        raise fgFDMError("unknown unit mapping (%s,%s)" % (fromunits, tounits))


    def units(self, varname):
        '''return the default units of a variable'''
        if not varname in self.mapping.vars:
            raise fgFDMError('Unknown variable %s' % varname)
        return self.mapping.vars[varname].units


    def variables(self):
        '''return a list of available variables'''
        return sorted(self.mapping.vars.keys(),
                      key = lambda v : self.mapping.vars[v].index)


    def get(self, varname, idx=0, units=None):
        '''get a variable value'''
        if not varname in self.mapping.vars:
            raise fgFDMError('Unknown variable %s' % varname)
        if idx >= self.mapping.vars[varname].arraylength:
            raise fgFDMError('index of %s beyond end of array idx=%u arraylength=%u' % (
                varname, idx, self.mapping.vars[varname].arraylength))
        value = self.values[self.mapping.vars[varname].index + idx]
        if units:
            value = self.convert(value, self.mapping.vars[varname].units, units)
        return value

    def set(self, varname, value, idx=0, units=None):
        '''set a variable value'''
        if not varname in self.mapping.vars:
            raise fgFDMError('Unknown variable %s' % varname)
        if idx >= self.mapping.vars[varname].arraylength:
            raise fgFDMError('index of %s beyond end of array idx=%u arraylength=%u' % (
                varname, idx, self.mapping.vars[varname].arraylength))
        if units:
            value = self.convert(value, units, self.mapping.vars[varname].units)
        # avoid range errors when packing into 4 byte floats
        if math.isinf(value) or math.isnan(value) or math.fabs(value) > 3.4e38:
            value = 0
        self.values[self.mapping.vars[varname].index + idx] = value

    def parse(self, buf):
        '''parse a FD FDM buffer'''
        try:
            t = struct.unpack(self.pack_string, buf)
        except struct.error, msg:
            raise fgFDMError('unable to parse - %s' % msg)
        self.values = list(t)

    def pack(self):
        '''pack a FD FDM buffer from current values'''
        for i in range(len(self.values)):
            if math.isnan(self.values[i]):
                self.values[i] = 0
        return struct.pack(self.pack_string, *self.values)

########NEW FILE########
__FILENAME__ = gen_all
#!/usr/bin/env python

'''
Use mavgen.py on all available MAVLink XML definitions to generate
C and Python MAVLink routines for sending and parsing the protocol

Copyright Pete Hollands 2011
Released under GNU GPL version 3 or later
'''

import os, sys, glob, re
from mavgen import mavgen

class options:
    """ a class to simulate the options of mavgen OptionsParser"""
    def __init__(self, lang, output, wire_protocol, error_limit):
        self.language = lang
        self.wire_protocol = wire_protocol
        self.output = output
        self.error_limit = error_limit

protocols = [ '0.9', '1.0' ]

for protocol in protocols :
    xml_directory = './message_definitions/v'+protocol
    print "xml_directory is", xml_directory
    xml_file_names = glob.glob(xml_directory+'/*.xml')

    for xml_file in xml_file_names:
        print "xml file is ", xml_file
        opts = options(lang = "C", output = "C/include_v"+protocol, \
                       wire_protocol=protocol, error_limit=200)
        args = []
        args.append(xml_file)
        mavgen(opts, args)
        xml_file_base = os.path.basename(xml_file)
        xml_file_base = re.sub("\.xml","", xml_file_base)
        print "xml_file_base is", xml_file_base
        opts = options(lang = "python", \
                       output="python/mavlink_"+xml_file_base+"_v"+protocol+".py", \
                       wire_protocol=protocol, error_limit=200)
        mavgen(opts,args)
        
        opts = options(lang = "CS", \
                       output="CS/v" + protocol + "/mavlink_" + xml_file_base + "/mesages", \
                       wire_protocol=protocol, error_limit=200)
        mavgen(opts,args)

########NEW FILE########
__FILENAME__ = gen_MatrixPilot
'''
Use mavgen.py matrixpilot.xml definitions to generate
C and Python MAVLink routines for sending and parsing the protocol
This python script is soley for MatrixPilot MAVLink impoementations

Copyright Pete Hollands 2011, 2012
Released under GNU GPL version 3 or later
'''

import os, sys, glob, re
from shutil import copy
from mavgen import mavgen

# allow import from the parent directory, where mavutil.py is
# Under Windows, this script must be run from a DOS command window 
# sys.path.insert(0, os.path.join(os.path.dirname(os.path.realpath(__file__)), '..'))
sys.path.insert(0, os.path.join(os.getcwd(), '..'))

class options:
    """ a class to simulate the options of mavgen OptionsParser"""
    def __init__(self, lang, output, wire_protocol, error_limit):
        self.language = lang
        self.wire_protocol = wire_protocol
        self.output = output
        self.error_limit = error_limit

def remove_include_files(target_directory):
    search_pattern = target_directory+'/*.h'
    print "search pattern is", search_pattern
    files_to_remove = glob.glob(search_pattern)
    for afile in files_to_remove :
        try:
            print "removing", afile
            os.remove(afile)
        except:
            print "error while trying to remove", afile

def copy_include_files(source_directory,target_directory):
    search_pattern = source_directory+'/*.h'
    files_to_copy = glob.glob(search_pattern)
    for afile in files_to_copy:
        basename = os.path.basename(afile)
        print "Copying ...", basename
        copy(afile, target_directory)

def remove_xml_files(target_directory):
    search_pattern = target_directory+'/*.xml'
    print "search pattern is", search_pattern
    files_to_remove = glob.glob(search_pattern)
    for afile in files_to_remove :
        try:
            print "removing", afile
            os.remove(afile)
        except:
            print "error while trying to remove", afile

def copy_xml_files(source_directory,target_directory):
    search_pattern = source_directory+'/*.xml'
    files_to_copy = glob.glob(search_pattern)
    for afile in files_to_copy:
        basename = os.path.basename(afile)
        print "Copying ...", basename
        copy(afile, target_directory)


########### Generate MAVlink files for C and Python from XML definitions
protocol = "1.0"
 
xml_directory = '../../message_definitions/v'+protocol
print "xml_directory is", xml_directory

xml_file_names = []
xml_file_names.append(xml_directory+"/"+"common.xml")
xml_file_names.append(xml_directory+"/"+"matrixpilot.xml")

#Check to see if python directory exists ...
directory = 'python'
if not os.path.isdir(directory):
    os.makedirs(directory)

for xml_file in xml_file_names:
    print "xml file is ", xml_file   
    
    xml_file_base = os.path.basename(xml_file)
    xml_file_base = re.sub("\.xml","", xml_file_base)
    print "xml_file_base is", xml_file_base
    target_directory = "../../../../../MAVLink/include/"+xml_file_base
    source_directory = "C/include_v"+protocol+"/"+xml_file_base

    print "About to remove all files in",source_directory
    print "OK to continue ?[Yes / No]: ",
    line = sys.stdin.readline()
    if line == "Yes\n" or line == "yes\n" \
       or line == "Y\n" or line == "y\n":
        print "passed"
        remove_include_files(source_directory)
        print "Finished removing C include files for", xml_file_base
    else :
        print "Your answer is No. Exiting Program"
        sys.exit()

    opts = options(lang = "C", output = "C/include_v"+protocol, \
                   wire_protocol=protocol, error_limit=200)
    args = []
    args.append(xml_file)
    print "About to generate C include files"
    mavgen(opts, args)
    opts = options(lang = "python", \
                   output="python/mavlink_"+xml_file_base+"_v"+protocol+".py", \
                   wire_protocol=protocol, error_limit=200)
    print "About to generate python parsers"
    mavgen(opts,args)
    
    if os.access(source_directory, os.R_OK):
        if os.access(target_directory, os.W_OK):
            print "Preparing to copy over files..."
            print "About to remove all files in",target_directory
            print "OK to continue ?[Yes / No]: ",
            line = sys.stdin.readline()
            if line == "Yes\n" or line == "yes\n" \
               or line == "Y\n" or line == "y\n":
                print "passed"
                remove_include_files(target_directory)
                copy_include_files(source_directory,target_directory)
                print "Finished copying over xml derived include files"
            else :
                print "Your answer is No. Exiting Program"
                sys.exit()
        else :
           print "Cannot find " + target_directory + "in MatrixPilot"
           sys.exit() 
    else:
        print "Could not find files to copy at", source_directory
        print "Exiting Program."
        sys.exit()

# Copy newer versions of C header files 
header_files = ['checksum.h','mavlink_helpers.h', 'mavlink_protobuf_manager.hpp', \
                'mavlink_types.h', 'protocol.h' ]
target_directory = "../../../../../MAVLink/include/"
source_directory = "C/include_v"+protocol+"/"
print "Copying over upper level header files..."
for filename in header_files :
  print "Copying ... ", filename
  #print "About to copy source_file", source_directory+filename, "to",target_directory+filename
  if  os.access(source_directory+filename, os.R_OK):
    #print "Can read source file", source_directory+filename
    if  os.access(source_directory+filename, os.W_OK):
      copy(source_directory+filename, target_directory+filename)
      #print "Finished copying to", target_directory+filename
    else :
      print "Could not access", target_directory+filename, " for writing"
  else :
    print "Could not access file to copy called ", source_directory+filename


# Copy specific Mavlink wire protocol 1.0 python parsers for MatrixPilot
source_file =  "./python/mavlink_matrixpilot_v1.0.py"
target_files = "./mavlink.py" , "../mavlinkv10.py"
for target_name in target_files:
  print "About to copy source_file", source_file, "to",target_name
  if  os.access(source_file, os.R_OK):
    print "Can read source file", source_file
    if  os.access(source_file, os.W_OK):
      copy(source_file, target_name)
      print "Finished copying to", target_name
    else :
      print "Could not access", target_name, " for writing"
  else :
    print "Could not access file to copy called ", source_file

         
        
##### End of Main program to generate MAVLink C and Python files ####

##### Copy new XML message definitions to main trunk directories
source_directory = "../../message_definitions/V1.0"
target_directory = "../../../../../MAVLink/message_definitions"
if os.access(source_directory, os.R_OK):
    if os.access(target_directory, os.W_OK):
        print "Preparing to copy over xml files ..."
        print "About to remove files in ",target_directory
        print "OK to continue ?[Yes / No]: ",
        line = sys.stdin.readline()
        if line == "Yes\n" or line == "yes\n" \
           or line == "Y\n" or line == "y\n":
            print "passed"
            try:
                print "removing xml files in", target_directory
                remove_xml_files(target_directory)
            except:
                print "error while trying to remove files in ", target_directory
            print "Copying xml files from ", source_directory
            copy_xml_files(source_directory, target_directory) 
            print "Finished copying over python files"
        else :
            print "Your answer is No. Exiting Program"
            sys.exit()
    else :
       print "Cannot find " + target_directory 
       sys.exit() 
else:
    print "Could not find files to copy at", source_directory
    print "Exiting Program."
    sys.exit()
print "Program has finished, please press Return Key to exit"
line = sys.stdin.readline()



########NEW FILE########
__FILENAME__ = xmlif4Dom
#
# genxmlif, Release 0.9.0
# file: xmlif4Dom.py
#
# XML interface class to the 4DOM library
#
# history:
# 2005-04-25 rl   created
# 2008-07-01 rl   Limited support of XInclude added
#
# Copyright (c) 2005-2008 by Roland Leuthe.  All rights reserved.
#
# --------------------------------------------------------------------
# The generix XML interface is
#
# Copyright (c) 2005-2008 by Roland Leuthe
#
# By obtaining, using, and/or copying this software and/or its
# associated documentation, you agree that you have read, understood,
# and will comply with the following terms and conditions:
#
# Permission to use, copy, modify, and distribute this software and
# its associated documentation for any purpose and without fee is
# hereby granted, provided that the above copyright notice appears in
# all copies, and that both that copyright notice and this permission
# notice appear in supporting documentation, and that the name of
# the author not be used in advertising or publicity
# pertaining to distribution of the software without specific, written
# prior permission.
#
# THE AUTHOR DISCLAIMS ALL WARRANTIES WITH REGARD
# TO THIS SOFTWARE, INCLUDING ALL IMPLIED WARRANTIES OF MERCHANT-
# ABILITY AND FITNESS.  IN NO EVENT SHALL THE AUTHOR
# BE LIABLE FOR ANY SPECIAL, INDIRECT OR CONSEQUENTIAL DAMAGES OR ANY
# DAMAGES WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS,
# WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS
# ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR PERFORMANCE
# OF THIS SOFTWARE.
# --------------------------------------------------------------------

import urllib
from xml.dom.ext.reader.Sax2   import Reader, XmlDomGenerator
from xml.sax._exceptions       import SAXParseException
from ..genxmlif                  import XMLIF_4DOM, GenXmlIfError
from xmlifUtils                import convertToAbsUrl
from xmlifDom                  import XmlInterfaceDom, XmlIfBuilderExtensionDom, InternalDomTreeWrapper, InternalDomElementWrapper


class XmlInterface4Dom (XmlInterfaceDom):
    #####################################################
    # for description of the interface methods see xmlifbase.py
    #####################################################

    def __init__ (self, verbose, useCaching, processXInclude):
        XmlInterfaceDom.__init__ (self, verbose, useCaching, processXInclude)
        self.xmlIfType = XMLIF_4DOM
        if self.verbose:
            print "Using 4Dom interface module..."


    def parse (self, file, baseUrl="", internalOwnerDoc=None):
        absUrl = convertToAbsUrl (file, baseUrl)
        fp     = urllib.urlopen (absUrl)
        return self._parseStream (fp, file, absUrl, internalOwnerDoc)


    def parseString (self, text, baseUrl="", internalOwnerDoc=None):
        import cStringIO
        fp = cStringIO.StringIO(text)
        absUrl = convertToAbsUrl ("", baseUrl)
        return self._parseStream (fp, "", absUrl, internalOwnerDoc)


    def _parseStream (self, fp, file, absUrl, internalOwnerDoc):
        reader = Reader(validate=0, keepAllWs=0, catName=None, 
                        saxHandlerClass=ExtXmlDomGenerator, parser=None)
        reader.handler.extinit(file, absUrl, reader.parser, self)
        if internalOwnerDoc != None: 
            ownerDoc = internalOwnerDoc.document
        else:
            ownerDoc = None
        try:
            tree = reader.fromStream(fp, ownerDoc)
            fp.close()
        except SAXParseException, errInst:
            fp.close()
            raise GenXmlIfError, "%s: SAXParseException: %s" %(file, str(errInst))

        treeWrapper = reader.handler.treeWrapper
        
        # XInclude support
        if self.processXInclude:
            if internalOwnerDoc == None: 
                internalOwnerDoc = treeWrapper.getTree()
            self.xInclude (treeWrapper.getRootNode(), absUrl, internalOwnerDoc)
            
        return treeWrapper


###################################################
# Extended DOM generator class derived from XmlDomGenerator
# extended to store related line numbers, file/URL names and 
# defined namespaces in the node object

class ExtXmlDomGenerator(XmlDomGenerator, XmlIfBuilderExtensionDom):
    def __init__(self, keepAllWs=0):
        XmlDomGenerator.__init__(self, keepAllWs)
        self.treeWrapper = None


    def extinit (self, filePath, absUrl, parser, xmlIf):
        self.filePath = filePath
        self.absUrl = absUrl
        self.parser = parser
        self.xmlIf = xmlIf


    def startElement(self, name, attribs):
        XmlDomGenerator.startElement(self, name, attribs)

        if not self.treeWrapper:
            self.treeWrapper = self.xmlIf.treeWrapperClass(self, InternalDomTreeWrapper(self._rootNode), self.xmlIf.useCaching)
            XmlIfBuilderExtensionDom.__init__(self, self.filePath, self.absUrl, self.treeWrapper, self.xmlIf.elementWrapperClass)

        curNode = self._nodeStack[-1]
        internal4DomElementWrapper = InternalDomElementWrapper(curNode, self.treeWrapper.getTree())
        curNs = self._namespaces.items()
        try:
            curNs.remove( (None,None) )
        except:
            pass

        XmlIfBuilderExtensionDom.startElementHandler (self, internal4DomElementWrapper, self.parser.getLineNumber(), curNs)


    def endElement(self, name):
        curNode = self._nodeStack[-1]
        XmlIfBuilderExtensionDom.endElementHandler (self, curNode.xmlIfExtInternalWrapper, self.parser.getLineNumber())
        XmlDomGenerator.endElement(self, name)

########NEW FILE########
__FILENAME__ = xmlifApi
#
# genxmlif, Release 0.9.0
# file: xmlifapi.py
#
# API (interface) classes for generic interface package
#
# history:
# 2007-06-29 rl   created, classes extracted from xmlifbase.py
#
# Copyright (c) 2005-2008 by Roland Leuthe.  All rights reserved.
#
# --------------------------------------------------------------------
# The generic XML interface is
#
# Copyright (c) 2005-2008 by Roland Leuthe
#
# By obtaining, using, and/or copying this software and/or its
# associated documentation, you agree that you have read, understood,
# and will comply with the following terms and conditions:
#
# Permission to use, copy, modify, and distribute this software and
# its associated documentation for any purpose and without fee is
# hereby granted, provided that the above copyright notice appears in
# all copies, and that both that copyright notice and this permission
# notice appear in supporting documentation, and that the name of
# the author not be used in advertising or publicity
# pertaining to distribution of the software without specific, written
# prior permission.
#
# THE AUTHOR DISCLAIMS ALL WARRANTIES WITH REGARD
# TO THIS SOFTWARE, INCLUDING ALL IMPLIED WARRANTIES OF MERCHANT-
# ABILITY AND FITNESS.  IN NO EVENT SHALL THE AUTHOR
# BE LIABLE FOR ANY SPECIAL, INDIRECT OR CONSEQUENTIAL DAMAGES OR ANY
# DAMAGES WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS,
# WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS
# ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR PERFORMANCE
# OF THIS SOFTWARE.
# --------------------------------------------------------------------

__author__  = "Roland Leuthe <roland@leuthe-net.de>"
__date__    = "08. August 2008"
__version__ = "0.9.0"

import string
import os
import re
import copy
from types      import TupleType, StringTypes
from xml.dom    import EMPTY_PREFIX, EMPTY_NAMESPACE
from xmlifUtils import processWhitespaceAction, NsNameTupleFactory, splitQName, nsNameToQName, escapeCdata, escapeAttribute


########################################
# XML interface base class
# All not implemented methods have to be overloaded by the derived class!!
#

class XmlInterfaceBase:
    """XML interface base class.
    
    All not implemented methods have to be overloaded by the derived class!!
    """

    def __init__(self, verbose, useCaching, processXInclude):
        """Constructor of class XmlInterfaceBase.
        
        Input parameter:
            'verbose':         0 or 1: controls verbose print output for module genxmlif
            'useCaching':      0 or 1: controls usage of caching for module genxmlif
            'processXInclude': 0 or 1: controls XInclude processing during parsing
        """
        
        self.verbose         = verbose
        self.useCaching      = useCaching
        self.processXInclude = processXInclude

        # set default wrapper classes
        self.setTreeWrapperClass (XmlTreeWrapper)
        self.setElementWrapperClass (XmlElementWrapper)


    def createXmlTree (self, namespace, xmlRootTagName, attributeDict={}, publicId=None, systemId=None):
        """Create a new XML TreeWrapper object (wrapper for DOM document or elementtree).
        
        Input parameter:
            'namespace':      not yet handled (for future use)
            'xmlRootTagName': specifies the tag name of the root element
            'attributeDict':  contains the attributes of the root node (optional)
            'publicId':       forwarded to contained DOM tree (unused for elementtree)
            'systemId':       forwarded to contained DOM tree (unused for elementtree)
        Returns the created XML tree wrapper object.
        Method has to be implemented by derived classes!
        """
         
        raise NotImplementedError


    def parse (self, filePath, baseUrl="", ownerDoc=None):
        """Call the XML parser for 'file'.
        
        Input parameter:
            'filePath': a file path or an URI
            'baseUrl':  if specified, it is used e.g. as base path for schema files referenced inside the XML file.
            'ownerDoc': only used in case of 4DOM (forwarded to 4DOM parser). 
        Returns the respective XML tree wrapper object for the parsed XML file.
        Method has to be implemented by derived classes!
        """
        
        raise NotImplementedError


    def parseString (self, text, baseUrl="", ownerDoc=None):
        """Call the XML parser for 'text'.

        Input parameter:
            'text':     contains the XML string to be parsed
            'baseUrl':  if specified, it is used e.g. as base path for schema files referenced inside the XML string.
            'ownerDoc': only used in case of 4DOM (forwarded to 4DOM parser). 
        Returns the respective XML tree wrapper object for the parsed XML 'text' string.
        Method has to be implemented by derived classes!
        """
        raise NotImplementedError


    def setTreeWrapperClass (self, treeWrapperClass):
        """Set the tree wrapper class which shall be used by this interface.

        Input parameter:
            treeWrapperClass:     tree wrapper class
        """
        self.treeWrapperClass = treeWrapperClass


    def setElementWrapperClass (self, elementWrapperClass):
        """Set the element wrapper classes which shall be used by this interface.

        Input parameter:
            elementWrapperClass:  element wrapper class
        """
        self.elementWrapperClass = elementWrapperClass
        

    def getXmlIfType (self):
        """Retrieve the type of the XML interface."""
        return self.xmlIfType
    

########################################
# Tree wrapper API (interface class)
#

class XmlTreeWrapper:
    """XML tree wrapper API.

    Contains a DOM tree or an elementtree (depending on used XML parser)
    """

    def __init__(self, xmlIf, tree, useCaching):
        """Constructor of wrapper class XmlTreeWrapper.
        
        Input parameter:
            'xmlIf':      used XML interface class
            'tree':       DOM tree or elementtree which is wrapped by this object
            'useCaching': 1 if caching shall be used inside genxmlif, otherwise 0
        """
        self.xmlIf                   = xmlIf
        self.__tree                  = tree
        self.__useCaching            = useCaching


    def createElement (self, tupleOrLocalName, attributeDict=None, curNs=[]):
        """Create an ElementWrapper object.
        
        Input parameter:
            tupleOrLocalName: tag name of element node to be created 
                              (tuple of namespace and localName or only localName if no namespace is used)
            attributeDict:    attributes for this elements
            curNs:            namespaces for scope of this element
        Returns an ElementWrapper object containing the created element node.
        """
        nsName = NsNameTupleFactory(tupleOrLocalName)
        elementNode    = self.__tree.xmlIfExtCreateElement(nsName, attributeDict, curNs)
        return self.xmlIf.elementWrapperClass(elementNode, self, curNs)


    def cloneTree (self):
        """Creates a copy of a whole XML DOM tree."""
        rootElementWrapperCopy = self.getRootNode().cloneNode(deep=1)
        treeWrapperCopy = self.__class__(self.xmlIf, 
                                         self.__tree.xmlIfExtCloneTree(rootElementWrapperCopy.element), 
                                         self.__useCaching)
        for elementWrapper in rootElementWrapperCopy.getIterator():
            elementWrapper.treeWrapper = treeWrapperCopy
        return treeWrapperCopy
        
    
    def getRootNode (self):
        """Retrieve the wrapper object of the root element of the contained XML tree.
        
        Returns the ElementWrapper object of the root element.
        """
        return self.__tree.xmlIfExtGetRootNode().xmlIfExtElementWrapper


    def getTree (self):
        """Retrieve the contained XML tree.
        
        Returns the contained XML tree object (internal DOM tree wrapper or elementtree).
        """
        return self.__tree

    
    def printTree (self, prettyPrint=0, printElementValue=1, encoding=None):
        """Return the string representation of the contained XML tree.
        
        Input parameter:
            'prettyPrint':        aligns the columns of the attributes of childNodes
            'printElementValue':  controls if the lement values are printed or not.
        Returns a string with the string representation of the whole XML tree.
        """
        if not encoding:
            encoding = "utf-8"
        if encoding != "utf-8" and encoding != "us-ascii":
            text = "<?xml version='1.0' encoding='%s'?>\n" % encoding
        else:
            text = ""
        return text + self.getRootNode().printNode(deep=1, prettyPrint=prettyPrint, printElementValue=printElementValue, encoding=encoding)


    def useCaching (self):
        """Return 1 if caching should be used for the contained XML tree."""
        return self.__useCaching


    def setExternalCacheUsage (self, used):
        """Set external cache usage for the whole tree
           unlink commands are ignored if used by an external cache

           Input parameter:
               used:       0 or 1 (used by external cache)
        """
        self.getRootNode().setExternalCacheUsage (used, deep=1)

    
    def unlink (self):
        """Break circular references of the complete XML tree.
        
        To be called if the XML tree is not longer used => garbage collection!
        """
        self.getRootNode().unlink()
        

    def __str__ (self):
        """Return the string representation of the contained XML tree."""
        return self.printTree()



########################################
# Element wrapper API (interface class)
#

class XmlElementWrapper:
    """XML element wrapper API.

    Contains a XML element node
    All not implemented methods have to be overloaded by the derived class!!
    """

    def __init__(self, element, treeWrapper, curNs=[], initAttrSeq=1):
        """Constructor of wrapper class XmlElementWrapper.
        
        Input parameter:
            element:       XML element node which is wrapped by this object
            treeWrapper:   XML tree wrapper class the current element belongs to
            curNs:         namespaces for scope of this element
        """
        self.element                        = element
        self.element.xmlIfExtElementWrapper = self
        self.treeWrapper                    = treeWrapper
        self.nodeUsedByExternalCache        = 0
        
        if self.__useCaching():
            self.__childrenCache = {}
            self.__firstChildCache = {}
            self.__qNameAttrCache = {}

        self.baseUrl = None
        self.absUrl = None
        self.filePath = None
        self.startLineNumber = None
        self.endLineNumber = None
        self.curNs = curNs[:]
        self.attributeSequence = []

        if initAttrSeq:
            self.attributeSequence = self.getAttributeDict().keys()


    def unlink (self):
        """Break circular references of this element and its children."""
        for childWrapper in self.getChildren():
            childWrapper.unlink()
        if not self.isUsedByExternalCache():
            self.element.xmlIfExtUnlink()

        
    def cloneNode (self, deep, cloneCallback=None):
        """Create a copy of the current element wrapper.
           The reference to the parent node is set to None!"""
        elementCopy = self.element.xmlIfExtCloneNode()
        elementWrapperCopy = self.__class__(elementCopy, self.treeWrapper, initAttrSeq=0)
        elementWrapperCopy.treeWrapper = None
        elementWrapperCopy.baseUrl = self.baseUrl
        elementWrapperCopy.absUrl = self.absUrl
        elementWrapperCopy.filePath = self.filePath
        elementWrapperCopy.startLineNumber = self.startLineNumber
        elementWrapperCopy.endLineNumber = self.endLineNumber
        elementWrapperCopy.curNs = self.curNs[:]
        elementWrapperCopy.attributeSequence = self.attributeSequence[:]
        if cloneCallback: cloneCallback(elementWrapperCopy)
        if deep:
            for childElement in self.element.xmlIfExtGetChildren():
                childWrapperElementCopy = childElement.xmlIfExtElementWrapper.cloneNode(deep, cloneCallback)
                childWrapperElementCopy.element.xmlIfExtSetParentNode(elementWrapperCopy.element)
                elementWrapperCopy.element.xmlIfExtAppendChild(childWrapperElementCopy.element)
        return elementWrapperCopy
    
    
    def clearNodeCache (self):
        """Clear all caches used by this element wrapper which contains element wrapper references."""
        self.__clearChildrenCache()


    def isUsedByExternalCache (self):
        """Check if this node is used by an external cache.
           unlink commands are ignored if used by an external cache"""
        return self.nodeUsedByExternalCache
    
    
    def setExternalCacheUsage (self, used, deep=1):
        """Set external cache usage for this node and its children
           unlink commands are ignored if used by an external cache

           Input parameter:
               used:       0 or 1 (used by external cache)
               deep:       0 or 1: controls if the child elements are also marked as used by external cache
        """
        self.nodeUsedByExternalCache = used
        if deep:
            for childWrapper in self.getChildren():
                childWrapper.setExternalCacheUsage (used, deep)
        


    ##########################################################
    #  attributes of the current node can be accessed via key operator
    
    def __getitem__(self, tupleOrAttrName):
        """Attributes of the contained element node can be accessed via key operator.
        
        Input parameter:
            tupleOrAttrName: name of the attribute (tuple of namespace and attributeName or only attributeName)
        Returns the attribute value.
        """
        attrValue = self.getAttribute (tupleOrAttrName)
        if attrValue != None:
            return attrValue
        else:
            raise AttributeError, "Attribute %s not found!" %(repr(tupleOrAttrName))


    def __setitem__(self, tupleOrAttrName, attributeValue):
        """Attributes of the contained element node can be accessed via key operator.
        
        Input parameter:
            tupleOrAttrName: name of the attribute (tuple of namespace and attributeName or only attributeName)
            attributeValue:  attribute value to be set
        """
        self.setAttribute (tupleOrAttrName, attributeValue)


#++++++++++++ methods concerning the tag name ++++++++++++++++++++++++

    def getTagName (self):
        """Retrieve the (complete) tag name of the contained element node
        
        Returns the (complete) tag name of the contained element node
        """
        return self.element.xmlIfExtGetTagName()


    def getLocalName (self):
        """Retrieve the local name (without namespace) of the contained element node
        
        Returns the local name (without namespace) of the contained element node
        """
        
        try:
            return self.__localNameCache
        except:
            prefix, localName = splitQName (self.getTagName())
            if self.__useCaching():
                self.__localNameCache = localName
        return localName


    def getNamespaceURI (self):
        """Retrieve the namespace URI of the contained element node
        
        Returns the namespace URI of the contained element node (None if no namespace is used).
        """
        try:
            return self.__nsUriCache
        except:
            prefix = self.element.xmlIfExtGetNamespaceURI()
            if self.__useCaching():
                self.__nsUriCache = prefix 
            return prefix


    def getNsName (self):
        """Retrieve a tuple (namespace, localName) of the contained element node
        
        Returns a tuple (namespace, localName) of the contained element node (namespace is None if no namespace is used).
        """
        try:
            return self.__nsNameCache
        except:
            nsName = NsNameTupleFactory( (self.getNamespaceURI(), self.getLocalName()) )
            if self.__useCaching():
                self.__nsNameCache = nsName
            return nsName


    def getQName (self):
        """Retrieve a string prefix and localName of the contained element node

        Returns a string "prefix:localName" of the contained element node
        """
        return self.nsName2QName(self.getNsName())


    def getPrefix (self):
        """Retrieve the namespace prefix of the contained element node
        
        Returns the namespace prefix of the contained element node (None if no namespace is used).
        """
        return self.getNsPrefix(self.getNsName())


#++++++++++++ methods concerning print support ++++++++++++++++++++++++

    def __str__ (self):
        """Retrieve the textual representation of the contained element node."""
        return self.printNode()


    def printNode (self, indent="", deep=0, prettyPrint=0, attrMaxLengthDict={}, printElementValue=1, encoding=None):
        """Retrieve the textual representation of the contained element node.
        
        Input parameter:
            indent:             indentation to be used for string representation
            deep:               0 or 1: controls if the child element nodes are also printed
            prettyPrint:        aligns the columns of the attributes of childNodes
            attrMaxLengthDict:  dictionary containing the length of the attribute values (used for prettyprint)
            printElementValue:  0 or 1: controls if the element value is printed
        Returns the string representation
        """
        patternXmlTagShort = '''\
%(indent)s<%(qName)s%(attributeString)s/>%(tailText)s%(lf)s'''

        patternXmlTagLong = '''\
%(indent)s<%(qName)s%(attributeString)s>%(elementValueString)s\
%(lf)s%(subTreeString)s\
%(indent)s</%(qName)s>%(tailText)s%(lf)s'''
        
        subTreeStringList = []
        tailText = ""
        addIndent = ""
        lf = ""
        if deep:
            childAttrMaxLengthDict = {}
            if prettyPrint:
                for childNode in self.getChildren():
                    childNode.__updateAttrMaxLengthDict(childAttrMaxLengthDict)
                lf = "\n"
                addIndent = "    "
            for childNode in self.getChildren():
                subTreeStringList.append (childNode.printNode(indent + addIndent, deep, prettyPrint, childAttrMaxLengthDict, printElementValue))
            tailText = escapeCdata(self.element.xmlIfExtGetElementTailText(), encoding)
        
        attributeStringList = []
        for attrName in self.getAttributeList():
            attrValue = escapeAttribute(self.getAttribute(attrName), encoding)
            if prettyPrint:
                try:
                    align = attrMaxLengthDict[attrName]
                except:
                    align = len(attrValue)
            else:
                align = len(attrValue)
            qName = self.nsName2QName(attrName)
            attributeStringList.append (' %s="%s"%*s' %(qName, attrValue, align - len(attrValue), ""))
        attributeString = string.join (attributeStringList, "")

        qName = self.getQName()
        if printElementValue:
            if deep:
                elementValueString = escapeCdata(self.element.xmlIfExtGetElementText(), encoding)
            else:
                elementValueString = escapeCdata(self.getElementValue(ignoreEmtpyStringFragments=1), encoding)
        else:
            elementValueString = ""

        if subTreeStringList == [] and elementValueString == "":
            printPattern = patternXmlTagShort
        else:
            if subTreeStringList != []:
                subTreeString = string.join (subTreeStringList, "")
            else:
                subTreeString = ""
            printPattern = patternXmlTagLong
        return printPattern % vars()


#++++++++++++ methods concerning the parent of the current node ++++++++++++++++++++++++

    def getParentNode (self):
        """Retrieve the ElementWrapper object of the parent element node.

        Returns the ElementWrapper object of the parent element node.
        """
        parent = self.element.xmlIfExtGetParentNode()
        if parent != None:
            return parent.xmlIfExtElementWrapper
        else:
            return None


#++++++++++++ methods concerning the children of the current node ++++++++++++++++++++++++


    def getChildren (self, tagFilter=None):
        """Retrieve the ElementWrapper objects of the children element nodes.
        
        Input parameter:
            tagFilter: retrieve only the children with this tag name ('*' or None returns all children)
        Returns all children of this element node which match 'tagFilter' (list)
        """
        if tagFilter in (None, '*', (None, '*')):
            children = self.element.xmlIfExtGetChildren()
        elif tagFilter[1] == '*':
            # handle (namespace, '*')
            children = filter(lambda child:child.xmlIfExtElementWrapper.getNamespaceURI() == tagFilter[0], 
                              self.element.xmlIfExtGetChildren())
        else:
            nsNameFilter = NsNameTupleFactory(tagFilter)
            try:
                children = self.__childrenCache[nsNameFilter]
            except:
                children = self.element.xmlIfExtGetChildren(nsNameFilter)
                if self.__useCaching():
                    self.__childrenCache[nsNameFilter] = children

        return map(lambda child: child.xmlIfExtElementWrapper, children)


    def getChildrenNS (self, namespaceURI, tagFilter=None):
        """Retrieve the ElementWrapper objects of the children element nodes using a namespace.
        
        Input parameter:
            namespaceURI: the namespace URI of the children or None
            tagFilter:    retrieve only the children with this localName ('*' or None returns all children)
        Returns all children of this element node which match 'namespaceURI' and 'tagFilter' (list)
        """
        return self.getChildren((namespaceURI, tagFilter))


    def getChildrenWithKey (self, tagFilter=None, keyAttr=None, keyValue=None):
        """Retrieve the ElementWrapper objects of the children element nodes.
        
        Input parameter:
            tagFilter: retrieve only the children with this tag name ('*' or None returns all children)
            keyAttr:   name of the key attribute
            keyValue:  value of the key
        Returns all children of this element node which match 'tagFilter' (list)
        """
        children = self.getChildren(tagFilter)
        return filter(lambda child:child[keyAttr]==keyValue, children)
    
    
    def getFirstChild (self, tagFilter=None):
        """Retrieve the ElementWrapper objects of the first child element node.
        
        Input parameter:
            tagFilter: retrieve only the first child with this tag name ('*' or None: no filter)
        Returns the first child of this element node which match 'tagFilter'
        or None if no suitable child element was found
        """
        if tagFilter in (None, '*', (None, '*')):
            element = self.element.xmlIfExtGetFirstChild()
        elif tagFilter[1] == '*':
            # handle (namespace, '*')
            children = filter(lambda child:child.xmlIfExtElementWrapper.getNamespaceURI() == tagFilter[0], 
                              self.element.xmlIfExtGetChildren())
            try:
                element = children[0]
            except:
                element = None
        else:
            nsNameFilter = NsNameTupleFactory(tagFilter)
            try:
                element = self.__firstChildCache[nsNameFilter]
            except:
                element = self.element.xmlIfExtGetFirstChild(nsNameFilter)
                if self.__useCaching():
                    self.__firstChildCache[nsNameFilter] = element

        if element != None:
            return element.xmlIfExtElementWrapper
        else:
            return None


    def getFirstChildNS (self, namespaceURI, tagFilter=None):
        """Retrieve the ElementWrapper objects of the first child element node using a namespace.
        
        Input parameter:
            namespaceURI: the namespace URI of the children or None
            tagFilter:    retrieve only the first child with this localName ('*' or None: no filter)
        Returns the first child of this element node which match 'namespaceURI' and 'tagFilter'
        or None if no suitable child element was found
        """
        return self.getFirstChild ((namespaceURI, tagFilter))


    def getFirstChildWithKey (self, tagFilter=None, keyAttr=None, keyValue=None):
        """Retrieve the ElementWrapper objects of the children element nodes.
        
        Input parameter:
            tagFilter: retrieve only the children with this tag name ('*' or None returns all children)
            keyAttr:   name of the key attribute
            keyValue:  value of the key
        Returns all children of this element node which match 'tagFilter' (list)
        """
        children = self.getChildren(tagFilter)
        childrenWithKey = filter(lambda child:child[keyAttr]==keyValue, children)
        if childrenWithKey != []:
            return childrenWithKey[0]
        else:
            return None

    
    def getElementsByTagName (self, tagFilter=None):
        """Retrieve all descendant ElementWrapper object of current node whose tag name match 'tagFilter'.

        Input parameter:
            tagFilter: retrieve only the children with this tag name ('*' or None returns all descendants)
        Returns all descendants of this element node which match 'tagFilter' (list)
        """
        if tagFilter in (None, '*', (None, '*'), (None, None)):
            descendants = self.element.xmlIfExtGetElementsByTagName()
            
        elif tagFilter[1] == '*':
            # handle (namespace, '*')
            descendants = filter(lambda desc:desc.xmlIfExtElementWrapper.getNamespaceURI() == tagFilter[0], 
                                 self.element.xmlIfExtGetElementsByTagName())
        else:
            nsNameFilter = NsNameTupleFactory(tagFilter)
            descendants = self.element.xmlIfExtGetElementsByTagName(nsNameFilter)

        return map(lambda descendant: descendant.xmlIfExtElementWrapper, descendants)


    def getElementsByTagNameNS (self, namespaceURI, tagFilter=None):
        """Retrieve all descendant ElementWrapper object of current node whose tag name match 'namespaceURI' and 'tagFilter'.
        
        Input parameter:
            namespaceURI: the namespace URI of the descendants or None
            tagFilter:    retrieve only the descendants with this localName ('*' or None returns all descendants)
        Returns all descendants of this element node which match 'namespaceURI' and 'tagFilter' (list)
        """
        return self.getElementsByTagName((namespaceURI, tagFilter))


    def getIterator (self, tagFilter=None):
        """Creates a tree iterator.  The iterator loops over this element
           and all subelements, in document order, and returns all elements
           whose tag name match 'tagFilter'.

        Input parameter:
            tagFilter: retrieve only the children with this tag name ('*' or None returns all descendants)
        Returns all element nodes which match 'tagFilter' (list)
        """
        if tagFilter in (None, '*', (None, '*'), (None, None)):
            matchingElements = self.element.xmlIfExtGetIterator()
        elif tagFilter[1] == '*':
            # handle (namespace, '*')
            matchingElements = filter(lambda desc:desc.xmlIfExtElementWrapper.getNamespaceURI() == tagFilter[0], 
                                      self.element.xmlIfExtGetIterator())
        else:
            nsNameFilter = NsNameTupleFactory(tagFilter)
            matchingElements = self.element.xmlIfExtGetIterator(nsNameFilter)

        return map(lambda e: e.xmlIfExtElementWrapper, matchingElements)


    def appendChild (self, tupleOrLocalNameOrElement, attributeDict={}):
        """Append an element node to the children of the current node.

        Input parameter:
            tupleOrLocalNameOrElement: (namespace, localName) or tagName or ElementWrapper object of the new child
            attributeDict:             attribute dictionary containing the attributes of the new child (optional)
        If not an ElementWrapper object is given, a new ElementWrapper object is created with tupleOrLocalName
        Returns the ElementWrapper object of the new child.
        """
        if not isinstance(tupleOrLocalNameOrElement, self.__class__):
            childElementWrapper = self.__createElement (tupleOrLocalNameOrElement, attributeDict)
        else:
            childElementWrapper = tupleOrLocalNameOrElement
        self.element.xmlIfExtAppendChild (childElementWrapper.element)
        self.__clearChildrenCache(childElementWrapper.getNsName())
        return childElementWrapper


    def insertBefore (self, tupleOrLocalNameOrElement, refChild, attributeDict={}):
        """Insert an child element node before the given reference child of the current node.

        Input parameter:
            tupleOrLocalNameOrElement: (namespace, localName) or tagName or ElementWrapper object of the new child
            refChild:                  reference child ElementWrapper object
            attributeDict:             attribute dictionary containing the attributes of the new child (optional)
        If not an ElementWrapper object is given, a new ElementWrapper object is created with tupleOrLocalName
        Returns the ElementWrapper object of the new child.
        """
        if not isinstance(tupleOrLocalNameOrElement, self.__class__):
            childElementWrapper = self.__createElement (tupleOrLocalNameOrElement, attributeDict)
        else:
            childElementWrapper = tupleOrLocalNameOrElement
        if refChild == None:
            self.appendChild (childElementWrapper)
        else:
            self.element.xmlIfExtInsertBefore(childElementWrapper.element, refChild.element)
            self.__clearChildrenCache(childElementWrapper.getNsName())
        return childElementWrapper


    def removeChild (self, childElementWrapper):
        """Remove the given child element node from the children of the current node.

        Input parameter:
            childElementWrapper:  ElementWrapper object to be removed
        """
        self.element.xmlIfExtRemoveChild(childElementWrapper.element)
        self.__clearChildrenCache(childElementWrapper.getNsName())


    def insertSubtree (self, refChildWrapper, subTreeWrapper, insertSubTreeRootNode=1):
        """Insert the given subtree before 'refChildWrapper' ('refChildWrapper' is not removed!)
        
        Input parameter:
            refChildWrapper:       reference child ElementWrapper object
            subTreeWrapper:        subtree wrapper object which contains the subtree to be inserted
            insertSubTreeRootNode: if 1, root node of subtree is inserted into parent tree, otherwise not
        """ 
        if refChildWrapper != None:
            self.element.xmlIfExtInsertSubtree (refChildWrapper.element, subTreeWrapper.getTree(), insertSubTreeRootNode)
        else:
            self.element.xmlIfExtInsertSubtree (None, subTreeWrapper.getTree(), insertSubTreeRootNode)
        self.__clearChildrenCache()



    def replaceChildBySubtree (self, childElementWrapper, subTreeWrapper, insertSubTreeRootNode=1):
        """Replace child element node by XML subtree (e.g. expanding included XML files)

        Input parameter:
            childElementWrapper:   ElementWrapper object to be replaced
            subTreeWrapper:        XML subtree wrapper object to  be inserted
            insertSubTreeRootNode: if 1, root node of subtree is inserted into parent tree, otherwise not
        """
        self.insertSubtree (childElementWrapper, subTreeWrapper, insertSubTreeRootNode)
        self.removeChild(childElementWrapper)


#++++++++++++ methods concerning the attributes of the current node ++++++++++++++++++++++++

    def getAttributeDict (self):
        """Retrieve a dictionary containing all attributes of the current element node.
        
        Returns a dictionary (copy) containing all attributes of the current element node.
        """
        return self.element.xmlIfExtGetAttributeDict()


    def getAttributeList (self):
        """Retrieve a list containing all attributes of the current element node
           in the sequence specified in the input XML file.
        
        Returns a list (copy) containing all attributes of the current element node
        in the sequence specified in the input XML file (TODO: does currently not work for 4DOM/pyXML interface).
        """
        attrList = map(lambda a: NsNameTupleFactory(a), self.attributeSequence)
        return attrList


    def getAttribute (self, tupleOrAttrName):
        """Retrieve an attribute value of the current element node.
        
        Input parameter:
            tupleOrAttrName:  tuple '(namespace, attributeName)' or 'attributeName' if no namespace is used
        Returns the value of the specified attribute.
        """
        nsName = NsNameTupleFactory(tupleOrAttrName)
        return self.element.xmlIfExtGetAttribute(nsName)


    def getAttributeOrDefault (self, tupleOrAttrName, defaultValue):
        """Retrieve an attribute value of the current element node or the given default value if the attribute doesn't exist.
        
        Input parameter:
            tupleOrAttrName:  tuple '(namespace, attributeName)' or 'attributeName' if no namespace is used
        Returns the value of the specified attribute or the given default value if the attribute doesn't exist.
        """
        attributeValue = self.getAttribute (tupleOrAttrName)
        if attributeValue == None:
            attributeValue = defaultValue
        return attributeValue


    def getQNameAttribute (self, tupleOrAttrName):
        """Retrieve a QName attribute value of the current element node.
        
        Input parameter:
            tupleOrAttrName:  tuple '(namespace, attributeName)' or 'attributeName' if no namespace is used
        Returns the value of the specified QName attribute as tuple (namespace, localName),
        i.e. the prefix is converted into the corresponding namespace value.
        """
        nsNameAttrName = NsNameTupleFactory(tupleOrAttrName)
        try:
            return self.__qNameAttrCache[nsNameAttrName]
        except:
            qNameValue = self.getAttribute (nsNameAttrName)
            nsNameValue = self.qName2NsName(qNameValue, useDefaultNs=1)
            if self.__useCaching():
                self.__qNameAttrCache[nsNameAttrName] = nsNameValue
            return nsNameValue


    def hasAttribute (self, tupleOrAttrName):
        """Checks if the requested attribute exist for the current element node.
        
        Returns 1 if the attribute exists, otherwise 0.
        """
        nsName = NsNameTupleFactory(tupleOrAttrName)
        attrValue = self.element.xmlIfExtGetAttribute(nsName)
        if attrValue != None:
            return 1
        else:
            return 0


    def setAttribute (self, tupleOrAttrName, attributeValue):
        """Sets an attribute value of the current element node. 
        If the attribute does not yet exist, it will be created.
               
        Input parameter:
            tupleOrAttrName:  tuple '(namespace, attributeName)' or 'attributeName' if no namespace is used
            attributeValue:   attribute value to be set
        """
        if not isinstance(attributeValue, StringTypes):
            raise TypeError, "%s (attribute %s) must be a string!" %(repr(attributeValue), repr(tupleOrAttrName))

        nsNameAttrName = NsNameTupleFactory(tupleOrAttrName)
        if nsNameAttrName not in self.attributeSequence:
            self.attributeSequence.append(nsNameAttrName)

        if self.__useCaching():
            if self.__qNameAttrCache.has_key(nsNameAttrName):
                del self.__qNameAttrCache[nsNameAttrName]

        self.element.xmlIfExtSetAttribute(nsNameAttrName, attributeValue, self.getCurrentNamespaces())


    def setAttributeDefault (self, tupleOrAttrName, defaultValue):
        """Create attribute and set value to default if it does not yet exist for the current element node. 
        If the attribute is already existing nothing is done.
               
        Input parameter:
            tupleOrAttrName:  tuple '(namespace, attributeName)' or 'attributeName' if no namespace is used
            defaultValue:     default attribute value to be set
        """
        if not self.hasAttribute(tupleOrAttrName):
            self.setAttribute(tupleOrAttrName, defaultValue)


    def removeAttribute (self, tupleOrAttrName):
        """Removes an attribute from the current element node. 
        No exception is raised if there is no matching attribute.
               
        Input parameter:
            tupleOrAttrName:  tuple '(namespace, attributeName)' or 'attributeName' if no namespace is used
        """
        nsNameAttrName = NsNameTupleFactory(tupleOrAttrName)

        if self.__useCaching():
            if self.__qNameAttrCache.has_key(nsNameAttrName):
                del self.__qNameAttrCache[nsNameAttrName]

        self.element.xmlIfExtRemoveAttribute(nsNameAttrName)


    def processWsAttribute (self, tupleOrAttrName, wsAction):
        """Process white space action for the specified attribute according to requested 'wsAction'.
        
        Input parameter:
            tupleOrAttrName:  tuple '(namespace, attributeName)' or 'attributeName' if no namespace is used
            wsAction:         'collapse':  substitute multiple whitespace characters by a single ' '
                              'replace':   substitute each whitespace characters by a single ' '
        """
        attributeValue = self.getAttribute(tupleOrAttrName)
        newValue = processWhitespaceAction (attributeValue, wsAction)
        if newValue != attributeValue:
            self.setAttribute(tupleOrAttrName, newValue)
        return newValue
    

#++++++++++++ methods concerning the content of the current node ++++++++++++++++++++++++

    def getElementValue (self, ignoreEmtpyStringFragments=0):
        """Retrieve the content of the current element node.
        
        Returns the content of the current element node as string.
        The content of multiple text nodes / CDATA nodes are concatenated to one string.

        Input parameter:
            ignoreEmtpyStringFragments:   if 1, text nodes containing only whitespaces are ignored
        """
        return "".join (self.getElementValueFragments(ignoreEmtpyStringFragments))


    def getElementValueFragments (self, ignoreEmtpyStringFragments=0):
        """Retrieve the content of the current element node as value fragment list.
        
        Returns the content of the current element node as list of string fragments.
        Each list element represents one text nodes / CDATA node.

        Input parameter:
            ignoreEmtpyStringFragments:   if 1, text nodes containing only whitespaces are ignored
        
        Method has to be implemented by derived classes!
        """
        return self.element.xmlIfExtGetElementValueFragments (ignoreEmtpyStringFragments)


    def setElementValue (self, elementValue):
        """Set the content of the current element node.
        
        Input parameter:
            elementValue:   string containing the new element value
        If multiple text nodes / CDATA nodes are existing, 'elementValue' is set 
        for the first text node / CDATA node. All other text nodes /CDATA nodes are set to ''. 
        """
        self.element.xmlIfExtSetElementValue(elementValue)


    def processWsElementValue (self, wsAction):
        """Process white space action for the content of the current element node according to requested 'wsAction'.
        
        Input parameter:
            wsAction:         'collapse':  substitute multiple whitespace characters by a single ' '
                              'replace':   substitute each whitespace characters by a single ' '
        """
        self.element.xmlIfExtProcessWsElementValue(wsAction)
        return self.getElementValue()
        

#++++++++++++ methods concerning the info about the current node in the XML file ++++++++++++++++++++


    def getStartLineNumber (self):
        """Retrieve the start line number of the current element node.
        
        Returns the start line number of the current element node in the XML file
        """
        return self.startLineNumber


    def getEndLineNumber (self):
        """Retrieve the end line number of the current element node.
        
        Returns the end line number of the current element node in the XML file
        """
        return self.endLineNumber


    def getAbsUrl (self):
        """Retrieve the absolute URL of the XML file the current element node belongs to.
        
        Returns the absolute URL of the XML file the current element node belongs to.
        """
        return self.absUrl


    def getBaseUrl (self):
        """Retrieve the base URL of the XML file the current element node belongs to.
        
        Returns the base URL of the XML file the current element node belongs to.
        """
        return self.baseUrl


    def getFilePath (self):
        """Retrieve the file path of the XML file the current element node belongs to.
        
        Returns the file path of the XML file the current element node belongs to.
        """
        return self.filePath


    def getLocation (self, end=0, fullpath=0):
        """Retrieve a string containing file name and line number of the current element node.
        
        Input parameter:
            end:      1 if end line number shall be shown, 0 for start line number
            fullpath: 1 if the full path of the XML file shall be shown, 0 for only the file name
        Returns a string containing file name and line number of the current element node.
        (e.g. to be used for traces or error messages)
        """
        lineMethod = (self.getStartLineNumber, self.getEndLineNumber)
        pathFunc = (os.path.basename, os.path.abspath)
        return "%s, %d" % (pathFunc[fullpath](self.getFilePath()), lineMethod[end]())


#++++++++++++ miscellaneous methods concerning namespaces ++++++++++++++++++++


    def getCurrentNamespaces (self):
        """Retrieve the namespace prefixes visible for the current element node
        
        Returns a list of the namespace prefixes visible for the current node.
        """
        return self.curNs


    def qName2NsName (self, qName, useDefaultNs):
        """Convert a qName 'prefix:localName' to a tuple '(namespace, localName)'.
        
        Input parameter:
            qName:         qName to be converted
            useDefaultNs:  1 if default namespace shall be used
        Returns the corresponding tuple '(namespace, localName)' for 'qName'.
        """
        if qName != None:
            qNamePrefix, qNameLocalName = splitQName (qName)
            for prefix, namespaceURI in self.getCurrentNamespaces():
                if qNamePrefix == prefix:
                    if prefix != EMPTY_PREFIX or useDefaultNs:
                        nsName = (namespaceURI, qNameLocalName)
                        break
            else:
                if qNamePrefix == None:
                    nsName = (EMPTY_NAMESPACE, qNameLocalName)
                else:
                    raise ValueError, "Namespace prefix '%s' not bound to a namespace!" % (qNamePrefix)
        else:
            nsName = (None, None)
        return NsNameTupleFactory(nsName)


    def nsName2QName (self, nsLocalName):
        """Convert a tuple '(namespace, localName)' to a string 'prefix:localName'
        
        Input parameter:
            nsLocalName:   tuple '(namespace, localName)' to be converted
        Returns the corresponding string 'prefix:localName' for 'nsLocalName'.
        """
        qName = nsNameToQName (nsLocalName, self.getCurrentNamespaces())
        if qName == "xmlns:None": qName = "xmlns"
        return qName


    def getNamespace (self, qName):
        """Retrieve namespace for a qName 'prefix:localName'.
        
        Input parameter:
            qName:         qName 'prefix:localName'
        Returns the corresponding namespace for the prefix of 'qName'.
        """
        if qName != None:
            qNamePrefix, qNameLocalName = splitQName (qName)
            for prefix, namespaceURI in self.getCurrentNamespaces():
                if qNamePrefix == prefix:
                    namespace = namespaceURI
                    break
            else:
                if qNamePrefix == None:
                    namespace = EMPTY_NAMESPACE
                else:
                    raise LookupError, "Namespace for QName '%s' not found!" % (qName)
        else:
            namespace = EMPTY_NAMESPACE
        return namespace


    def getNsPrefix (self, nsLocalName):
        """Retrieve prefix for a tuple '(namespace, localName)'.
        
        Input parameter:
            nsLocalName:     tuple '(namespace, localName)'
        Returns the corresponding prefix for the namespace of 'nsLocalName'.
        """
        ns = nsLocalName[0]
        for prefix, namespace in self.getCurrentNamespaces():
            if ns == namespace:
                return prefix
        else:
            if ns == None:
                return None
            else:
                raise LookupError, "Prefix for namespaceURI '%s' not found!" % (ns)


#++++++++++++ limited XPath support ++++++++++++++++++++

    def getXPath (self, xPath, namespaceRef=None, useDefaultNs=1, attrIgnoreList=[]):
        """Retrieve node list or attribute list for specified XPath
        
        Input parameter:
            xPath:           string containing xPath specification
            namespaceRef:    scope for namespaces (default is own element node)
            useDefaultNs:    1, if default namespace shall be used if no prefix is available
            attrIgnoreList:  list of attributes to be ignored if wildcard is specified for attributes

        Returns all nodes which match xPath specification or
        list of attribute values if xPath specifies an attribute
        """
        return self.getXPathList(xPath, namespaceRef, useDefaultNs, attrIgnoreList)[0]


    def getXPathList (self, xPath, namespaceRef=None, useDefaultNs=1, attrIgnoreList=[]):
        """Retrieve node list or attribute list for specified XPath
        
        Input parameter:
            xPath:           string containing xPath specification
            namespaceRef:    scope for namespaces (default is own element node)
            useDefaultNs:    1, if default namespace shall be used if no prefix is available
            attrIgnoreList:  list of attributes to be ignored if wildcard is specified for attributes

        Returns tuple (completeChildList, attrNodeList, attrNsNameFirst).
        completeChildList: contains all child node which match xPath specification or
                           list of attribute values if xPath specifies an attribute
        attrNodeList:      contains all child nodes where the specified attribute was found
        attrNsNameFirst:   contains the name of the first attribute which was found
        TODO: Re-design namespace and attribute handling of this method
        """
        reChild     = re.compile('child *::')
        reAttribute = re.compile('attribute *::')
        if namespaceRef == None: namespaceRef = self
        xPath = reChild.sub('./', xPath)
        xPath = reAttribute.sub('@', xPath)
        xPathList = string.split (xPath, "|")
        completeChildDict = {}
        completeChildList = []
        attrNodeList = []
        attrNsNameFirst = None
        for xRelPath in xPathList:
            xRelPath = string.strip(xRelPath)
            descendantOrSelf = 0
            if xRelPath[:3] == ".//":
                descendantOrSelf = 1
                xRelPath = xRelPath[3:]
            xPathLocalStepList = string.split (xRelPath, "/")
            childList = [self, ]
            for localStep in xPathLocalStepList:
                localStep = string.strip(localStep)
                stepChildList = []
                if localStep == "":
                    raise IOError ("Invalid xPath '%s'!" %(xRelPath))
                elif localStep == ".":
                    continue
                elif localStep[0] == '@':
                    if len(localStep) == 1:
                        raise ValueError ("Attribute name is missing in xPath!")
                    if descendantOrSelf:
                        childList = self.getElementsByTagName()
                    attrName = localStep[1:]
                    for childNode in childList:
                        if attrName == '*':
                            attrNodeList.append (childNode)
                            attrDict = childNode.getAttributeDict()
                            for attrIgnore in attrIgnoreList:
                                if attrDict.has_key(attrIgnore):
                                    del attrDict[attrIgnore]
                            stepChildList.extend(attrDict.values())
                            try:
                                attrNsNameFirst = attrDict.keys()[0]
                            except:
                                pass
                        else:
                            attrNsName = namespaceRef.qName2NsName (attrName, useDefaultNs=0)
                            if attrNsName[1] == '*':
                                for attr in childNode.getAttributeDict().keys():
                                    if attr[0] == attrNsName[0]:
                                        if attrNodeList == []:
                                            attrNsNameFirst = attrNsName
                                        attrNodeList.append (childNode)
                                        stepChildList.append (childNode.getAttribute(attr))
                            elif childNode.hasAttribute(attrNsName):
                                if attrNodeList == []:
                                    attrNsNameFirst = attrNsName
                                attrNodeList.append (childNode)
                                stepChildList.append (childNode.getAttribute(attrNsName))
                    childList = stepChildList
                else:
                    nsLocalName = namespaceRef.qName2NsName (localStep, useDefaultNs=useDefaultNs)
                    if descendantOrSelf:
                        descendantOrSelf = 0
                        if localStep == "*":
                            stepChildList = self.getElementsByTagName()
                        else:
                            stepChildList = self.getElementsByTagName(nsLocalName)
                    else:
                        for childNode in childList:
                            if localStep == "*":
                                stepChildList.extend (childNode.getChildren())
                            else:
                                stepChildList.extend (childNode.getChildrenNS(nsLocalName[0], nsLocalName[1]))
                    childList = stepChildList
            # filter duplicated childs
            for child in childList:
                try:
                    childKey = child.element
                except:
                    childKey = child
                if not completeChildDict.has_key(childKey):
                    completeChildList.append(child)
                    completeChildDict[childKey] = 1
        return completeChildList, attrNodeList, attrNsNameFirst


    ###############################################################
    # PRIVATE methods
    ###############################################################

    def __createElement (self, tupleOrLocalName, attributeDict):
        """Create a new ElementWrapper object.
        
        Input parameter:
            tupleOrLocalName: tuple '(namespace, localName)' or 'localName' if no namespace is used
            attributeDict:    dictionary which contains the attributes and their values of the element node to be created
        Returns the created ElementWrapper object
        """
        childElementWrapper = self.treeWrapper.createElement (tupleOrLocalName, attributeDict, self.curNs[:]) # TODO: when to be adapted???)
        childElementWrapper.element.xmlIfExtSetParentNode(self.element)
        return childElementWrapper


    def __updateAttrMaxLengthDict (self, attrMaxLengthDict):
        """Update dictionary which contains the maximum length of node attributes.
        
        Used for pretty print to align the attributes of child nodes.
        attrMaxLengthDict is in/out parameter.
        """
        for attrName, attrValue in self.getAttributeDict().items():
            attrLength = len(attrValue)
            if not attrMaxLengthDict.has_key(attrName):
                attrMaxLengthDict[attrName] = attrLength
            else:
                attrMaxLengthDict[attrName] = max(attrMaxLengthDict[attrName], attrLength)


    def __clearChildrenCache (self, childNsName=None):
        """Clear children cache.
        """
        if self.__useCaching():
            if childNsName != None:
                if self.__childrenCache.has_key(childNsName):
                    del self.__childrenCache[childNsName]
                if self.__firstChildCache.has_key(childNsName):
                    del self.__firstChildCache[childNsName]
            else:
                self.__childrenCache.clear()
                self.__firstChildCache.clear()
                

    def __useCaching(self):
        return self.treeWrapper.useCaching()
    


########NEW FILE########
__FILENAME__ = xmlifBase
#
# genxmlif, Release 0.9.0
# file: xmlifbase.py
#
# XML interface base classes
#
# history:
# 2005-04-25 rl   created
# 2006-08-18 rl   some methods for XML schema validation support added
# 2007-05-25 rl   performance optimization (caching) added, bugfixes for XPath handling
# 2007-07-04 rl   complete re-design, API classes moved to xmlifApi.py
#
# Copyright (c) 2005-2008 by Roland Leuthe.  All rights reserved.
#
# --------------------------------------------------------------------
# The generic XML interface is
#
# Copyright (c) 2005-2008 by Roland Leuthe
#
# By obtaining, using, and/or copying this software and/or its
# associated documentation, you agree that you have read, understood,
# and will comply with the following terms and conditions:
#
# Permission to use, copy, modify, and distribute this software and
# its associated documentation for any purpose and without fee is
# hereby granted, provided that the above copyright notice appears in
# all copies, and that both that copyright notice and this permission
# notice appear in supporting documentation, and that the name of
# the author not be used in advertising or publicity
# pertaining to distribution of the software without specific, written
# prior permission.
#
# THE AUTHOR DISCLAIMS ALL WARRANTIES WITH REGARD
# TO THIS SOFTWARE, INCLUDING ALL IMPLIED WARRANTIES OF MERCHANT-
# ABILITY AND FITNESS.  IN NO EVENT SHALL THE AUTHOR
# BE LIABLE FOR ANY SPECIAL, INDIRECT OR CONSEQUENTIAL DAMAGES OR ANY
# DAMAGES WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS,
# WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS
# ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR PERFORMANCE
# OF THIS SOFTWARE.
# --------------------------------------------------------------------

__author__  = "Roland Leuthe <roland@leuthe-net.de>"
__date__    = "28 July 2008"
__version__ = "0.9"

from xml.dom    import XML_NAMESPACE, XMLNS_NAMESPACE
from xmlifUtils import NsNameTupleFactory, convertToAbsUrl



########################################
# XmlIf builder extension base class
# All not implemented methods have to be overloaded by the derived class!!
#

class XmlIfBuilderExtensionBase:
    """XmlIf builder extension base class.
    
    This class provides additional data (e.g. line numbers or caches) 
    for an element node which are stored in the element node object during parsing.
    """

    def __init__ (self, filePath, absUrl, treeWrapper, elementWrapperClass):
        """Constructor for this class
        
        Input parameter:
            filePath:      contains the file path of the corresponding XML file
            absUrl:        contains the absolute URL of the corresponding XML file
        """
        self.filePath            = filePath
        self.absUrl              = absUrl
        self.baseUrlStack        = [absUrl, ]
        self.treeWrapper         = treeWrapper
        self.elementWrapperClass = elementWrapperClass


    def startElementHandler (self, curNode, startLineNumber, curNs, attributes=[]):
        """Called by the XML parser at creation of an element node.
        
        Input parameter:
            curNode:          current element node
            startLineNumber:  first line number of the element tag in XML file
            curNs:            namespaces visible for this element node
            attributes:       list of attributes and their values for this element node 
                              (same sequence as int he XML file)
        """
        
        elementWrapper              = self.elementWrapperClass(curNode, self.treeWrapper, curNs, initAttrSeq=0)
        
        elementWrapper.baseUrl = self.__getBaseUrl(elementWrapper)
        elementWrapper.absUrl  = self.absUrl
        elementWrapper.filePath = self.filePath
        elementWrapper.startLineNumber = startLineNumber
        elementWrapper.curNs.extend ([("xml", XML_NAMESPACE), ("xmlns", XMLNS_NAMESPACE)])

        if attributes != []:
            for i in range (0, len(attributes), 2):
                elementWrapper.attributeSequence.append(attributes[i])
        else:
            attrList = elementWrapper.getAttributeDict().keys()
            attrList.sort()
            elementWrapper.attributeSequence.extend (attrList)

        self.baseUrlStack.insert (0, elementWrapper.baseUrl)


    def endElementHandler (self, curNode, endLineNumber):
        """Called by the XML parser after creation of an element node.
        
        Input parameter:
            curNode:          current element node
            endLineNumber:    last line number of the element tag in XML file
        """
        curNode.xmlIfExtElementWrapper.endLineNumber = endLineNumber
        self.baseUrlStack.pop (0)


    def __getBaseUrl (self, elementWrapper):
        """Retrieve base URL for the given element node.
        
        Input parameter:
            elementWrapper:    wrapper of current element node
        """
        nsNameBaseAttr = NsNameTupleFactory ((XML_NAMESPACE, "base"))
        if elementWrapper.hasAttribute(nsNameBaseAttr):
            return convertToAbsUrl (elementWrapper.getAttribute(nsNameBaseAttr), self.baseUrlStack[0])
        else:
            return self.baseUrlStack[0]


########NEW FILE########
__FILENAME__ = xmlifDom
#
# genxmlif, Release 0.9.0
# file: xmlifDom.py
#
# XML interface base class for Python DOM implementations
#
# history:
# 2005-04-25 rl   created
# 2007-07-02 rl   complete re-design, internal wrapper 
#                 for DOM trees and elements introduced
# 2008-07-01 rl   Limited support of XInclude added
#
# Copyright (c) 2005-2008 by Roland Leuthe.  All rights reserved.
#
# --------------------------------------------------------------------
# The generic XML interface is
#
# Copyright (c) 2005-2008 by Roland Leuthe
#
# By obtaining, using, and/or copying this software and/or its
# associated documentation, you agree that you have read, understood,
# and will comply with the following terms and conditions:
#
# Permission to use, copy, modify, and distribute this software and
# its associated documentation for any purpose and without fee is
# hereby granted, provided that the above copyright notice appears in
# all copies, and that both that copyright notice and this permission
# notice appear in supporting documentation, and that the name of
# the author not be used in advertising or publicity
# pertaining to distribution of the software without specific, written
# prior permission.
#
# THE AUTHOR DISCLAIMS ALL WARRANTIES WITH REGARD
# TO THIS SOFTWARE, INCLUDING ALL IMPLIED WARRANTIES OF MERCHANT-
# ABILITY AND FITNESS.  IN NO EVENT SHALL THE AUTHOR
# BE LIABLE FOR ANY SPECIAL, INDIRECT OR CONSEQUENTIAL DAMAGES OR ANY
# DAMAGES WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS,
# WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS
# ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR PERFORMANCE
# OF THIS SOFTWARE.
# --------------------------------------------------------------------

import string
import copy
import urllib
from types                import TupleType
from xml.dom              import Node, getDOMImplementation, XMLNS_NAMESPACE
from ..genxmlif             import XINC_NAMESPACE, GenXmlIfError
from xmlifUtils           import nsNameToQName, processWhitespaceAction, collapseString, NsNameTupleFactory, convertToAbsUrl
from xmlifBase            import XmlIfBuilderExtensionBase
from xmlifApi             import XmlInterfaceBase


class XmlInterfaceDom (XmlInterfaceBase):
    """Derived interface class for handling of DOM parsers.
    
    For description of the interface methods see xmlifbase.py.
    """
    
    def xInclude (self, elementWrapper, baseUrl, ownerDoc):
        filePath = elementWrapper.getFilePath()
        for childElementWrapper in elementWrapper.getChildren():
            line = childElementWrapper.getStartLineNumber()
            if childElementWrapper.getNsName() == (XINC_NAMESPACE, "include"):
                href = childElementWrapper["href"]
                parse = childElementWrapper.getAttributeOrDefault ("parse", "xml")
                encoding = childElementWrapper.getAttribute ("encoding")
                if self.verbose:
                    print "Xinclude: %s" %href
                try:
                    if parse == "xml":
                        subTreeWrapper = self.parse (href, baseUrl, ownerDoc)
                        elementWrapper.replaceChildBySubtree (childElementWrapper, subTreeWrapper)
                    elif parse == "text":
                        absUrl = convertToAbsUrl (href, baseUrl)
                        fp = urllib.urlopen (absUrl)
                        data = fp.read()
                        if encoding:
                            data = data.decode(encoding)
                        newTextNode = ownerDoc.xmlIfExtCreateTextNode(data)
                        elementWrapper.element.element.insertBefore (newTextNode, childElementWrapper.element.element)
                        elementWrapper.removeChild (childElementWrapper)
                        fp.close()
                    else:
                        raise GenXmlIfError, "%s: line %s: XIncludeError: Invalid 'parse' Attribut: '%s'" %(filePath, line, parse)
                except IOError, errInst:
                    raise GenXmlIfError, "%s: line %s: IOError: %s" %(filePath, line, str(errInst))
            elif childElementWrapper.getNsName() == (XINC_NAMESPACE, "fallback"):
                raise GenXmlIfError, "%s: line %s: XIncludeError: xi:fallback tag must be child of xi:include" %(filePath, line)
            else:
                self.xInclude(childElementWrapper, baseUrl, ownerDoc)



class InternalDomTreeWrapper:
    """Internal wrapper for a DOM Document class.
    """
    def __init__ (self, document):
        self.document   = document
    
    def xmlIfExtGetRootNode (self):
        domNode = self.document
        if domNode.nodeType == Node.DOCUMENT_NODE:
            return domNode.documentElement.xmlIfExtInternalWrapper
        elif domNode.nodeType == Node.DOCUMENT_FRAGMENT_NODE:
            for node in domNode.childNodes:
                if node.nodeType == Node.ELEMENT_NODE:
                    return node.xmlIfExtInternalWrapper
            else:
                return None
        else:
            return None


    def xmlIfExtCreateElement (self, nsName, attributeDict, curNs):
        elementNode = self.document.createElementNS (nsName[0], nsName[1])
        intElementWrapper = self.internalElementWrapperClass(elementNode, self)
        for attrName, attrValue in attributeDict.items():
            intElementWrapper.xmlIfExtSetAttribute (NsNameTupleFactory(attrName), attrValue, curNs)
        return intElementWrapper


    def xmlIfExtCreateTextNode (self, data):
        return self.document.createTextNode(data)
    

    def xmlIfExtImportNode (self, node):
        return self.document.importNode (node, 0) 
        

    def xmlIfExtCloneTree (self, rootElementCopy):
        domImpl = getDOMImplementation()
#        documentCopy = domImpl.createDocument(rootElementCopy.xmlIfExtGetNamespaceURI(), rootElementCopy.xmlIfExtGetTagName(), None)
        documentCopy = domImpl.createDocument(None, None, None)
#        documentCopy = copy.copy(self.document)
        documentCopy.documentElement = rootElementCopy.element
        return self.__class__(documentCopy)

    

#########################################################
# Internal Wrapper class for a Dom Element class

class InternalDomElementWrapper:
    """Internal Wrapper for a Dom Element class.
    """
    
    def __init__ (self, element, internalDomTreeWrapper):
        self.element = element
        element.xmlIfExtInternalWrapper = self
        self.internalDomTreeWrapper = internalDomTreeWrapper
        

    def xmlIfExtUnlink (self):
        self.xmlIfExtElementWrapper = None
        

    def xmlIfExtCloneNode (self):
        nodeCopy = self.__class__(self.element.cloneNode(deep=0), self.internalDomTreeWrapper)
        for childTextNode in self.__xmlIfExtGetChildTextNodes():
            childTextNodeCopy = childTextNode.cloneNode(0)
            nodeCopy.element.appendChild (childTextNodeCopy)
#        for nsAttrName, attrValue in self.xmlIfExtGetAttributeDict().items():
#            nodeCopy.xmlIfExtSetAttribute(nsAttrName, attrValue, self.xmlIfExtElementWrapper.getCurrentNamespaces())
        return nodeCopy

    
    def xmlIfExtGetTagName (self):
        return self.element.tagName


    def xmlIfExtGetNamespaceURI (self):
        return self.element.namespaceURI


    def xmlIfExtGetParentNode (self):
        parentNode = self.element.parentNode
        if parentNode.nodeType == Node.ELEMENT_NODE:
            return self.element.parentNode.xmlIfExtInternalWrapper
        else:
            return None

    
    def xmlIfExtSetParentNode (self, parentElement):
        pass # nothing to do since parent is provided by DOM interface
    

    def xmlIfExtGetChildren (self, tagFilter=None):
        # TODO: Handle also wildcard tagFilter = (namespace, None)
        children = filter (lambda e: (e.nodeType == Node.ELEMENT_NODE) and          # - only ELEMENTs
                                      (tagFilter == None or 
                                       (e.namespaceURI == tagFilter[0] and e.localName == tagFilter[1])), # - if tagFilter given --> check
                           self.element.childNodes )                                 # from element's nodes

        return map(lambda element: element.xmlIfExtInternalWrapper, children)


    def xmlIfExtGetFirstChild (self, tagFilter=None):
        children = self.xmlIfExtGetChildren (tagFilter)
        if children != []:
            return children[0]
        else:
            None


    def xmlIfExtGetElementsByTagName (self, tagFilter=('*','*')):
        elementList = self.element.getElementsByTagNameNS( tagFilter[0], tagFilter[1] )
        return map( lambda element: element.xmlIfExtInternalWrapper, elementList )


    def xmlIfExtGetIterator (self, tagFilter=('*','*')):
        elementList = []
        if tagFilter in (('*','*'), (self.element.namespaceURI, self.element.localName)):
            elementList.append(self.element)
        elementList.extend(self.element.getElementsByTagNameNS( tagFilter[0], tagFilter[1] ))
        return map( lambda element: element.xmlIfExtInternalWrapper, elementList )

    
    def xmlIfExtAppendChild (self, childElement):
        self.element.appendChild (childElement.element)


    def xmlIfExtInsertBefore (self, childElement, refChildElement):
        self.element.insertBefore (childElement.element, refChildElement.element)


    def xmlIfExtRemoveChild (self, childElement):
        self.element.removeChild (childElement.element)


    def xmlIfExtInsertSubtree (self, refChildElement, subTree, insertSubTreeRootNode):
        if insertSubTreeRootNode:
            childElementList = [subTree.xmlIfExtGetRootNode(),]
        else:
            childElementList = subTree.xmlIfExtGetRootNode().xmlIfExtGetChildren()

        for childElement in childElementList:
            if refChildElement != None:
                self.element.insertBefore(childElement.element, refChildElement.element)
            else:
                self.element.appendChild(childElement.element)


    def xmlIfExtGetAttributeDict (self):
        attribDict = {}
        for nsAttrName, attrNodeOrValue in self.element.attributes.items():
            attribDict[NsNameTupleFactory(nsAttrName)] = attrNodeOrValue.nodeValue
        return attribDict


    def xmlIfExtGetAttribute (self, nsAttrName):
        if self.element.attributes.has_key (nsAttrName):
            return self.element.getAttributeNS (nsAttrName[0], nsAttrName[1])
        elif nsAttrName[1] == "xmlns" and self.element.attributes.has_key(nsAttrName[1]):
            # workaround for minidom for correct access of xmlns attribute
            return self.element.getAttribute (nsAttrName[1])
        else:
            return None


    def xmlIfExtSetAttribute (self, nsAttrName, attributeValue, curNs):
        if nsAttrName[0] != None:
            qName = nsNameToQName (nsAttrName, curNs)
        else:
            qName = nsAttrName[1]
        
        self.element.setAttributeNS (nsAttrName[0], qName, attributeValue)


    def xmlIfExtRemoveAttribute (self, nsAttrName):
        self.element.removeAttributeNS (nsAttrName[0], nsAttrName[1])


    def xmlIfExtGetElementValueFragments (self, ignoreEmtpyStringFragments):
        elementValueList = []
        for childTextNode in self.__xmlIfExtGetChildTextNodes():
            elementValueList.append(childTextNode.data)
        if ignoreEmtpyStringFragments:
            elementValueList = filter (lambda s: collapseString(s) != "", elementValueList)
        if elementValueList == []:
            elementValueList = ["",]
        return elementValueList


    def xmlIfExtGetElementText (self):
        elementTextList = ["",]
        if self.element.childNodes != []:
            for childNode in self.element.childNodes:
                if childNode.nodeType in (Node.TEXT_NODE, Node.CDATA_SECTION_NODE):
                    elementTextList.append (childNode.data)
                else:
                    break
        return "".join(elementTextList)

    
    def xmlIfExtGetElementTailText (self):
        tailTextList = ["",]
        nextSib = self.element.nextSibling
        while nextSib:
            if nextSib.nodeType in (Node.TEXT_NODE, Node.CDATA_SECTION_NODE):
                tailTextList.append (nextSib.data)
                nextSib = nextSib.nextSibling
            else:
                break
        return "".join(tailTextList)
        

    def xmlIfExtSetElementValue (self, elementValue):
        if self.__xmlIfExtGetChildTextNodes() == []:
            textNode = self.internalDomTreeWrapper.xmlIfExtCreateTextNode (elementValue)
            self.element.appendChild (textNode)
        else:
            self.__xmlIfExtGetChildTextNodes()[0].data = elementValue
            if len (self.__xmlIfExtGetChildTextNodes()) > 1:
                for textNode in self.__xmlIfExtGetChildTextNodes()[1:]:
                    textNode.data = ""
            

    def xmlIfExtProcessWsElementValue (self, wsAction):
        textNodes = self.__xmlIfExtGetChildTextNodes()

        if len(textNodes) == 1:
            textNodes[0].data = processWhitespaceAction (textNodes[0].data, wsAction)
        elif len(textNodes) > 1:
            textNodes[0].data = processWhitespaceAction (textNodes[0].data, wsAction, rstrip=0)
            lstrip = 0
            if len(textNodes[0].data) > 0 and textNodes[0].data[-1] == " ":
                lstrip = 1
            for textNode in textNodes[1:-1]:
                textNode.data = processWhitespaceAction (textNode.data, wsAction, lstrip, rstrip=0)
                if len(textNode.data) > 0 and textNode.data[-1] == " ":
                    lstrip = 1
                else:
                    lstrip = 0
            textNodes[-1].data = processWhitespaceAction (textNodes[-1].data, wsAction, lstrip)


    ###############################################################
    # PRIVATE methods
    ###############################################################

    def __xmlIfExtGetChildTextNodes ( self ):
        """Return list of TEXT nodes."""
        return filter (lambda e: ( e.nodeType in (Node.TEXT_NODE, Node.CDATA_SECTION_NODE) ), # - only TEXT-NODES
                       self.element.childNodes)                         # from element's child nodes
        


class XmlIfBuilderExtensionDom (XmlIfBuilderExtensionBase):
    """XmlIf builder extension class for DOM parsers."""
    
    pass

########NEW FILE########
__FILENAME__ = xmlifElementTree
#
# genxmlif, Release 0.9.0
# file: xmlifElementTree.py
#
# XML interface class to elementtree toolkit by Fredrik Lundh
#
# history:
# 2005-04-25 rl   created
# 2007-05-25 rl   performance optimization (caching) added, some bugfixes
# 2007-06-29 rl   complete re-design, ElementExtension class introduced
# 2008-07-01 rl   Limited support of XInclude added
#
# Copyright (c) 2005-2008 by Roland Leuthe.  All rights reserved.
#
# --------------------------------------------------------------------
# The generic XML interface is
#
# Copyright (c) 2005-2008 by Roland Leuthe
#
# By obtaining, using, and/or copying this software and/or its
# associated documentation, you agree that you have read, understood,
# and will comply with the following terms and conditions:
#
# Permission to use, copy, modify, and distribute this software and
# its associated documentation for any purpose and without fee is
# hereby granted, provided that the above copyright notice appears in
# all copies, and that both that copyright notice and this permission
# notice appear in supporting documentation, and that the name of
# the author not be used in advertising or publicity
# pertaining to distribution of the software without specific, written
# prior permission.
#
# THE AUTHOR DISCLAIMS ALL WARRANTIES WITH REGARD
# TO THIS SOFTWARE, INCLUDING ALL IMPLIED WARRANTIES OF MERCHANT-
# ABILITY AND FITNESS.  IN NO EVENT SHALL THE AUTHOR
# BE LIABLE FOR ANY SPECIAL, INDIRECT OR CONSEQUENTIAL DAMAGES OR ANY
# DAMAGES WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS,
# WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS
# ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR PERFORMANCE
# OF THIS SOFTWARE.
# --------------------------------------------------------------------

import sys
import string
import urllib
from xml.dom           import EMPTY_NAMESPACE, XMLNS_NAMESPACE
from xml.parsers.expat import ExpatError
# from version 2.5 on the elementtree module is part of the standard python distribution
if sys.version_info[:2] >= (2,5):
    from xml.etree.ElementTree      import ElementTree, _ElementInterface, XMLTreeBuilder, TreeBuilder
    from xml.etree import ElementInclude 
else:
    from elementtree.ElementTree    import ElementTree, _ElementInterface, XMLTreeBuilder, TreeBuilder
    from elementtree import ElementInclude 
from ..genxmlif                   import XMLIF_ELEMENTTREE, GenXmlIfError
from xmlifUtils                 import convertToAbsUrl, processWhitespaceAction, collapseString, toClarkQName, splitQName
from xmlifBase                  import XmlIfBuilderExtensionBase
from xmlifApi                   import XmlInterfaceBase

#########################################################
# Derived interface class for elementtree toolkit

class XmlInterfaceElementTree (XmlInterfaceBase):
    #####################################################
    # for description of the interface methods see xmlifbase.py
    #####################################################

    def __init__ (self, verbose, useCaching, processXInclude):
        XmlInterfaceBase.__init__ (self, verbose, useCaching, processXInclude)
        self.xmlIfType = XMLIF_ELEMENTTREE
        if self.verbose:
            print "Using elementtree interface module..."


    def createXmlTree (self, namespace, xmlRootTagName, attributeDict={}, publicId=None, systemId=None):
        rootNode = ElementExtension(toClarkQName(xmlRootTagName), attributeDict)
        rootNode.xmlIfExtSetParentNode(None)
        treeWrapper = self.treeWrapperClass(self, ElementTreeExtension(rootNode), self.useCaching)
        rootNodeWrapper = self.elementWrapperClass (rootNode, treeWrapper, []) # TODO: namespace handling
        return treeWrapper


    def parse (self, file, baseUrl="", ownerDoc=None):
        absUrl = convertToAbsUrl (file, baseUrl)
        fp     = urllib.urlopen (absUrl)
        try:
            tree        = ElementTreeExtension()
            treeWrapper = self.treeWrapperClass(self, tree, self.useCaching)
            parser = ExtXMLTreeBuilder(file, absUrl, self, treeWrapper)
            treeWrapper.getTree().parse(fp, parser)
            fp.close()
            
            # XInclude support
            if self.processXInclude:
                loaderInst = ExtXIncludeLoader (self.parse, absUrl, ownerDoc)
                try:
                    ElementInclude.include(treeWrapper.getTree().getroot(), loaderInst.loader)
                except IOError, errInst:
                    raise GenXmlIfError, "%s: IOError: %s" %(file, str(errInst))
            
        except ExpatError, errstr:
            fp.close()
            raise GenXmlIfError, "%s: ExpatError: %s" %(file, str(errstr))
        except ElementInclude.FatalIncludeError, errInst:
            fp.close()
            raise GenXmlIfError, "%s: XIncludeError: %s" %(file, str(errInst))
            
        return treeWrapper


    def parseString (self, text, baseUrl="", ownerDoc=None):
        absUrl = convertToAbsUrl ("", baseUrl)
        tree        = ElementTreeExtension()
        treeWrapper = self.treeWrapperClass(self, tree, self.useCaching)
        parser = ExtXMLTreeBuilder("", absUrl, self, treeWrapper)
        parser.feed(text)
        treeWrapper.getTree()._setroot(parser.close())

        # XInclude support
        if self.processXInclude:
            loaderInst = ExtXIncludeLoader (self.parse, absUrl, ownerDoc)
            ElementInclude.include(treeWrapper.getTree().getroot(), loaderInst.loader)

        return treeWrapper


#########################################################
# Extension (derived) class for ElementTree class

class ElementTreeExtension (ElementTree):

    def xmlIfExtGetRootNode (self):
        return self.getroot()


    def xmlIfExtCreateElement (self, nsName, attributeDict, curNs):
        clarkQName = toClarkQName(nsName)
        return ElementExtension (clarkQName, attributeDict)


    def xmlIfExtCloneTree (self, rootElementCopy):
        return self.__class__(element=rootElementCopy)
        

#########################################################
# Wrapper class for Element class

class ElementExtension (_ElementInterface):

    def __init__ (self, xmlRootTagName, attributeDict):
        _ElementInterface.__init__(self, xmlRootTagName, attributeDict)


    def xmlIfExtUnlink (self):
        self.xmlIfExtElementWrapper = None
        self.__xmlIfExtParentElement = None
        

    def xmlIfExtCloneNode (self):
        nodeCopy = self.__class__(self.tag, self.attrib.copy())
        nodeCopy.text = self.text
        nodeCopy.tail = self.tail
        return nodeCopy
    

    def xmlIfExtGetTagName (self):
        return self.tag


    def xmlIfExtGetNamespaceURI (self):
        prefix, localName = splitQName(self.tag)
        return prefix


    def xmlIfExtGetParentNode (self):
        return self.__xmlIfExtParentElement


    def xmlIfExtSetParentNode (self, parentElement):
        self.__xmlIfExtParentElement = parentElement
    

    def xmlIfExtGetChildren (self, filterTag=None):
        if filterTag == None:
            return self.getchildren()
        else:
            clarkFilterTag = toClarkQName(filterTag)
            return self.findall(clarkFilterTag)


    def xmlIfExtGetFirstChild (self, filterTag=None):
        # replace base method (performance optimized)
        if filterTag == None:
            children = self.getchildren()
            if children != []:
                element = children[0]
            else:
                element = None
        else:
            clarkFilterTag = toClarkQName(filterTag)
            element = self.find(clarkFilterTag)

        return element


    def xmlIfExtGetElementsByTagName (self, filterTag=(None,None)):
        clarkFilterTag = toClarkQName(filterTag)
        descendants = []
        for node in self.xmlIfExtGetChildren():
            descendants.extend(node.getiterator(clarkFilterTag))
        return descendants


    def xmlIfExtGetIterator (self, filterTag=(None,None)):
        clarkFilterTag = toClarkQName(filterTag)
        return self.getiterator (clarkFilterTag)

    
    def xmlIfExtAppendChild (self, childElement):
        self.append (childElement)
        childElement.xmlIfExtSetParentNode(self)


    def xmlIfExtInsertBefore (self, childElement, refChildElement):
        self.insert (self.getchildren().index(refChildElement), childElement)
        childElement.xmlIfExtSetParentNode(self)


    def xmlIfExtRemoveChild (self, childElement):
        self.remove (childElement)


    def xmlIfExtInsertSubtree (self, refChildElement, subTree, insertSubTreeRootNode):
        if refChildElement != None:
            insertIndex = self.getchildren().index (refChildElement)
        else:
            insertIndex = 0
        if insertSubTreeRootNode:
            elementList = [subTree.xmlIfExtGetRootNode(),]
        else:
            elementList = subTree.xmlIfExtGetRootNode().xmlIfExtGetChildren()
        elementList.reverse()
        for element in elementList:
            self.insert (insertIndex, element)
            element.xmlIfExtSetParentNode(self)


    def xmlIfExtGetAttributeDict (self):
        attrDict = {}
        for attrName, attrValue in self.attrib.items():
            namespaceEndIndex = string.find (attrName, '}')
            if namespaceEndIndex != -1:
                attrName = (attrName[1:namespaceEndIndex], attrName[namespaceEndIndex+1:])
            else:
                attrName = (EMPTY_NAMESPACE, attrName)
            attrDict[attrName] = attrValue
        return attrDict


    def xmlIfExtGetAttribute (self, tupleOrAttrName):
        clarkQName = toClarkQName(tupleOrAttrName)
        if self.attrib.has_key(clarkQName):
            return self.attrib[clarkQName]
        else:
            return None


    def xmlIfExtSetAttribute (self, tupleOrAttrName, attributeValue, curNs):
        self.attrib[toClarkQName(tupleOrAttrName)] = attributeValue


    def xmlIfExtRemoveAttribute (self, tupleOrAttrName):
        clarkQName = toClarkQName(tupleOrAttrName)
        if self.attrib.has_key(clarkQName):
            del self.attrib[clarkQName]


    def xmlIfExtGetElementValueFragments (self, ignoreEmtpyStringFragments):
        elementValueList = []
        if self.text != None:
            elementValueList.append(self.text)
        for child in self.getchildren():
            if child.tail != None:
                elementValueList.append(child.tail)
        if ignoreEmtpyStringFragments:
            elementValueList = filter (lambda s: collapseString(s) != "", elementValueList)
        if elementValueList == []:
            elementValueList = ["",]
        return elementValueList


    def xmlIfExtGetElementText (self):
        if self.text != None:
            return self.text
        else:
            return ""

    
    def xmlIfExtGetElementTailText (self):
        if self.tail != None:
            return self.tail
        else:
            return ""
    

    def xmlIfExtSetElementValue (self, elementValue):
        self.text = elementValue
        for child in self.getchildren():
            child.tail = None
            

    def xmlIfExtProcessWsElementValue (self, wsAction):
        noOfTextFragments = reduce(lambda sum, child: sum + (child.tail != None), self.getchildren(), 0)
        noOfTextFragments += (self.text != None)
                
        rstrip = 0
        lstrip = 1
        if self.text != None:
            if noOfTextFragments == 1:
                rstrip = 1
            self.text = processWhitespaceAction (self.text, wsAction, lstrip, rstrip)
            noOfTextFragments -= 1
            lstrip = 0
        for child in self.getchildren():
            if child.tail != None:
                if noOfTextFragments == 1:
                    rstrip = 1
                child.tail = processWhitespaceAction (child.tail, wsAction, lstrip, rstrip)
                noOfTextFragments -= 1
                lstrip = 0


###################################################
# Element tree builder class derived from XMLTreeBuilder
# extended to store related line numbers in the Element object

class ExtXMLTreeBuilder (XMLTreeBuilder, XmlIfBuilderExtensionBase):
    def __init__(self, filePath, absUrl, xmlIf, treeWrapper):
        XMLTreeBuilder.__init__(self, target=TreeBuilder(element_factory=ElementExtension))
        self._parser.StartNamespaceDeclHandler = self._start_ns
        self._parser.EndNamespaceDeclHandler = self._end_ns
        self.namespaces = []
        XmlIfBuilderExtensionBase.__init__(self, filePath, absUrl, treeWrapper, xmlIf.elementWrapperClass)

    def _start(self, tag, attrib_in):
        elem = XMLTreeBuilder._start(self, tag, attrib_in)
        self.start(elem)

    def _start_list(self, tag, attrib_in):
        elem = XMLTreeBuilder._start_list(self, tag, attrib_in)
        self.start(elem, attrib_in)

    def _end(self, tag):
        elem = XMLTreeBuilder._end(self, tag)
        self.end(elem)

    def _start_ns(self, prefix, value):
        self.namespaces.insert(0, (prefix, value))

    def _end_ns(self, prefix):
        assert self.namespaces.pop(0)[0] == prefix, "implementation confused"


    def start(self, element, attributes):
        # bugfix for missing start '{'
        for i in range (0, len(attributes), 2):
            attrName = attributes[i]
            namespaceEndIndex = string.find (attrName, '}')
            if namespaceEndIndex != -1 and attrName[0] != "{":
                attributes[i] = '{' + attributes[i]
        # bugfix end

        XmlIfBuilderExtensionBase.startElementHandler (self, element, self._parser.ErrorLineNumber, self.namespaces[:], attributes)
        if len(self._target._elem) > 1:
            element.xmlIfExtSetParentNode (self._target._elem[-2])
        else:
            for namespace in self.namespaces:
                if namespace[1] != None:
                    element.xmlIfExtElementWrapper.setAttribute((XMLNS_NAMESPACE, namespace[0]), namespace[1])


    def end(self, element):
        XmlIfBuilderExtensionBase.endElementHandler (self, element, self._parser.ErrorLineNumber)


###################################################
# XInclude loader
# 

class ExtXIncludeLoader:

    def __init__(self, parser, baseUrl, ownerDoc):
        self.parser = parser
        self.baseUrl = baseUrl
        self.ownerDoc = ownerDoc
    
    def loader(self, href, parse, encoding=None):
        if parse == "xml":
            data = self.parser(href, self.baseUrl, self.ownerDoc).getTree().getroot()
        else:
            absUrl = convertToAbsUrl (href, self.baseUrl)
            fp     = urllib.urlopen (absUrl)
            data = fp.read()
            if encoding:
                data = data.decode(encoding)
            fp.close()
        return data

########NEW FILE########
__FILENAME__ = xmlifMinidom
#
# genxmlif, Release 0.9.0
# file: xmlifMinidom.py
#
# XML interface class to Python standard minidom
#
# history:
# 2005-04-25 rl   created
# 2007-07-02 rl   complete re-design, internal wrapper 
#                 for DOM trees and elements introduced
# 2008-07-01 rl   Limited support of XInclude added
#
# Copyright (c) 2005-2008 by Roland Leuthe.  All rights reserved.
#
# --------------------------------------------------------------------
# The generix XML interface is
#
# Copyright (c) 2005-2008 by Roland Leuthe
#
# By obtaining, using, and/or copying this software and/or its
# associated documentation, you agree that you have read, understood,
# and will comply with the following terms and conditions:
#
# Permission to use, copy, modify, and distribute this software and
# its associated documentation for any purpose and without fee is
# hereby granted, provided that the above copyright notice appears in
# all copies, and that both that copyright notice and this permission
# notice appear in supporting documentation, and that the name of
# the author not be used in advertising or publicity
# pertaining to distribution of the software without specific, written
# prior permission.
#
# THE AUTHOR DISCLAIMS ALL WARRANTIES WITH REGARD
# TO THIS SOFTWARE, INCLUDING ALL IMPLIED WARRANTIES OF MERCHANT-
# ABILITY AND FITNESS.  IN NO EVENT SHALL THE AUTHOR
# BE LIABLE FOR ANY SPECIAL, INDIRECT OR CONSEQUENTIAL DAMAGES OR ANY
# DAMAGES WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS,
# WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS
# ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR PERFORMANCE
# OF THIS SOFTWARE.
# --------------------------------------------------------------------

import string
import urllib
from xml.dom              import Node, XMLNS_NAMESPACE
from xml.dom.expatbuilder import ExpatBuilderNS
from xml.parsers.expat    import ExpatError
from ..genxmlif             import XMLIF_MINIDOM, GenXmlIfError
from xmlifUtils           import convertToAbsUrl, NsNameTupleFactory
from xmlifDom             import XmlInterfaceDom, InternalDomTreeWrapper, InternalDomElementWrapper, XmlIfBuilderExtensionDom


class XmlInterfaceMinidom (XmlInterfaceDom):
    """Derived interface class for handling of minidom parser.
    
    For description of the interface methods see xmlifbase.py.
    """

    def __init__ (self, verbose, useCaching, processXInclude):
        XmlInterfaceDom.__init__ (self, verbose, useCaching, processXInclude)
        self.xmlIfType = XMLIF_MINIDOM
        if self.verbose:
            print "Using minidom interface module..."


    def createXmlTree (self, namespace, xmlRootTagName, attributeDict={}, publicId=None, systemId=None):
        from xml.dom.minidom import getDOMImplementation
        domImpl = getDOMImplementation()
        doctype = domImpl.createDocumentType(xmlRootTagName, publicId, systemId)
        domTree = domImpl.createDocument(namespace, xmlRootTagName, doctype)
        treeWrapper = self.treeWrapperClass(self, InternalMinidomTreeWrapper(domTree), self.useCaching)

        intRootNodeWrapper = InternalMinidomElementWrapper(domTree.documentElement, treeWrapper.getTree())
        rootNodeWrapper = self.elementWrapperClass (intRootNodeWrapper, treeWrapper, []) # TODO: namespace handling
        for attrName, attrValue in attributeDict.items():
            rootNodeWrapper.setAttribute (attrName, attrValue)

        return treeWrapper


    def parse (self, file, baseUrl="", internalOwnerDoc=None):
        absUrl = convertToAbsUrl(file, baseUrl)
        fp     = urllib.urlopen (absUrl)
        try:
            builder = ExtExpatBuilderNS(file, absUrl, self)
            tree = builder.parseFile(fp)

            # XInclude support
            if self.processXInclude:
                if internalOwnerDoc == None: 
                    internalOwnerDoc = builder.treeWrapper.getTree()
                self.xInclude (builder.treeWrapper.getRootNode(), absUrl, internalOwnerDoc)

            fp.close()
        except ExpatError, errInst:
            fp.close()
            raise GenXmlIfError, "%s: ExpatError: %s" %(file, str(errInst))

        return builder.treeWrapper


    def parseString (self, text, baseUrl="", internalOwnerDoc=None):
        absUrl = convertToAbsUrl ("", baseUrl)
        try:
            builder = ExtExpatBuilderNS("", absUrl, self)
            builder.parseString (text)

            # XInclude support
            if self.processXInclude:
                if internalOwnerDoc == None: 
                    internalOwnerDoc = builder.treeWrapper.getTree()
                self.xInclude (builder.treeWrapper.getRootNode(), absUrl, internalOwnerDoc)
        except ExpatError, errInst:
            raise GenXmlIfError, "%s: ExpatError: %s" %(baseUrl, str(errInst))

        return builder.treeWrapper



class InternalMinidomTreeWrapper (InternalDomTreeWrapper):
    """Internal wrapper for a minidom Document class.
    """
    
    def __init__ (self, document):
        InternalDomTreeWrapper.__init__(self, document)
        self.internalElementWrapperClass = InternalMinidomElementWrapper



class InternalMinidomElementWrapper (InternalDomElementWrapper):
    """Internal Wrapper for a Dom Element class.
    """

    def xmlIfExtGetAttributeDict (self):
        """Return a dictionary with all attributes of this element."""
        attribDict = {}
        for attrNameNS, attrNodeOrValue in self.element.attributes.itemsNS():
            attribDict[NsNameTupleFactory(attrNameNS)] = attrNodeOrValue
                
        return attribDict



class ExtExpatBuilderNS (ExpatBuilderNS, XmlIfBuilderExtensionDom):
    """Extended Expat Builder class derived from ExpatBuilderNS.
    
    Extended to store related line numbers, file/URL names and 
    defined namespaces in the node object.
    """

    def __init__ (self, filePath, absUrl, xmlIf):
        ExpatBuilderNS.__init__(self)
        internalMinidomTreeWrapper = InternalMinidomTreeWrapper(self.document)
        self.treeWrapper = xmlIf.treeWrapperClass(self, internalMinidomTreeWrapper, xmlIf.useCaching)
        XmlIfBuilderExtensionDom.__init__(self, filePath, absUrl, self.treeWrapper, xmlIf.elementWrapperClass)

        # set EndNamespaceDeclHandler, currently not used by minidom
        self.getParser().EndNamespaceDeclHandler = self.end_namespace_decl_handler
        self.curNamespaces = []


    def start_element_handler(self, name, attributes):
        ExpatBuilderNS.start_element_handler(self, name, attributes)

        # use attribute format {namespace}localName
        attrList = []
        for i in range (0, len(attributes), 2):
            attrName = attributes[i]
            attrNameSplit = string.split(attrName, " ")
            if len(attrNameSplit) > 1:
                attrName = (attrNameSplit[0], attrNameSplit[1])
            attrList.extend([attrName, attributes[i+1]])
        
        internalMinidomElementWrapper = InternalMinidomElementWrapper(self.curNode, self.treeWrapper.getTree())
        XmlIfBuilderExtensionDom.startElementHandler (self, internalMinidomElementWrapper, self.getParser().ErrorLineNumber, self.curNamespaces[:], attrList)

        if self.curNode.parentNode.nodeType == Node.DOCUMENT_NODE:
            for namespace in self.curNamespaces:
                if namespace[0] != None:
                    internalMinidomElementWrapper.xmlIfExtElementWrapper.attributeSequence.append((XMLNS_NAMESPACE, namespace[0]))
                else:
                    internalMinidomElementWrapper.xmlIfExtElementWrapper.attributeSequence.append("xmlns")
#                internalMinidomElementWrapper.xmlIfExtElementWrapper.setAttribute((XMLNS_NAMESPACE, namespace[0]), namespace[1])


    def end_element_handler(self, name):
        XmlIfBuilderExtensionDom.endElementHandler (self, self.curNode.xmlIfExtInternalWrapper, self.getParser().ErrorLineNumber)
        ExpatBuilderNS.end_element_handler(self, name)


    def start_namespace_decl_handler(self, prefix, uri):
        ExpatBuilderNS.start_namespace_decl_handler(self, prefix, uri)
        self.curNamespaces.insert(0, (prefix, uri))


    def end_namespace_decl_handler(self, prefix):
        assert self.curNamespaces.pop(0)[0] == prefix, "implementation confused"


########NEW FILE########
__FILENAME__ = xmlifODict
from types    import DictType
from UserDict import UserDict

class odict(UserDict):
    def __init__(self, dictOrTuple = None):
        self._keys = []
        UserDict.__init__(self, dictOrTuple)

    def __delitem__(self, key):
        UserDict.__delitem__(self, key)
        self._keys.remove(key)

    def __setitem__(self, key, item):
        UserDict.__setitem__(self, key, item)
        if key not in self._keys: self._keys.append(key)

    def clear(self):
        UserDict.clear(self)
        self._keys = []

    def copy(self):
        newInstance = odict()
        newInstance.update(self)
        return newInstance

    def items(self):
        return zip(self._keys, self.values())

    def keys(self):
        return self._keys[:]

    def popitem(self):
        try:
            key = self._keys[-1]
        except IndexError:
            raise KeyError('dictionary is empty')

        val = self[key]
        del self[key]

        return (key, val)

    def setdefault(self, key, failobj = None):
        if key not in self._keys: 
            self._keys.append(key)
        return UserDict.setdefault(self, key, failobj)

    def update(self, dictOrTuple):
        if isinstance(dictOrTuple, DictType):
            itemList = dictOrTuple.items()
        else:
            itemList = dictOrTuple
        for key, val in itemList:
            self.__setitem__(key,val)

    def values(self):
        return map(self.get, self._keys)
########NEW FILE########
__FILENAME__ = xmliftest
from .. import genxmlif
from ..genxmlif.xmlifODict import odict

xmlIf = genxmlif.chooseXmlIf(genxmlif.XMLIF_ELEMENTTREE)
xmlTree = xmlIf.createXmlTree(None, "testTree", {"rootAttr1":"RootAttr1"})
xmlRootNode = xmlTree.getRootNode()
myDict = odict( (("childTag1","123"), ("childTag2","123")) )
xmlRootNode.appendChild("childTag", myDict)
xmlRootNode.appendChild("childTag", {"childTag1":"123456", "childTag2":"123456"})
xmlRootNode.appendChild("childTag", {"childTag1":"123456789", "childTag3":"1234", "childTag2":"123456789"})
xmlRootNode.appendChild("childTag", {"childTag1":"1", "childTag2":"1"})
print xmlTree.printTree(prettyPrint=1)
print xmlTree
print xmlTree.getRootNode()

########NEW FILE########
__FILENAME__ = xmlifUtils
#
# genxmlif, Release 0.9.0
# file: xmlifUtils.py
#
# utility module for genxmlif
#
# history:
# 2005-04-25 rl   created
# 2008-08-01 rl   encoding support added
#
# Copyright (c) 2005-2008 by Roland Leuthe.  All rights reserved.
#
# --------------------------------------------------------------------
# The generic XML interface is
#
# Copyright (c) 2005-2008 by Roland Leuthe
#
# By obtaining, using, and/or copying this software and/or its
# associated documentation, you agree that you have read, understood,
# and will comply with the following terms and conditions:
#
# Permission to use, copy, modify, and distribute this software and
# its associated documentation for any purpose and without fee is
# hereby granted, provided that the above copyright notice appears in
# all copies, and that both that copyright notice and this permission
# notice appear in supporting documentation, and that the name of
# the author not be used in advertising or publicity
# pertaining to distribution of the software without specific, written
# prior permission.
#
# THE AUTHOR DISCLAIMS ALL WARRANTIES WITH REGARD
# TO THIS SOFTWARE, INCLUDING ALL IMPLIED WARRANTIES OF MERCHANT-
# ABILITY AND FITNESS.  IN NO EVENT SHALL THE AUTHOR
# BE LIABLE FOR ANY SPECIAL, INDIRECT OR CONSEQUENTIAL DAMAGES OR ANY
# DAMAGES WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS,
# WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS
# ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR PERFORMANCE
# OF THIS SOFTWARE.
# --------------------------------------------------------------------

import string
import re
import os
import urllib
import urlparse
from types   import StringTypes, TupleType
from xml.dom import EMPTY_PREFIX, EMPTY_NAMESPACE

######################################################################
# DEFINITIONS
######################################################################

######################################################################
# REGULAR EXPRESSION OBJECTS
######################################################################

_reWhitespace  = re.compile('\s')
_reWhitespaces = re.compile('\s+')

_reSplitUrlApplication = re.compile (r"(file|http|ftp|gopher):(.+)") # "file:///d:\test.xml" => "file" + "///d:\test.xml"


######################################################################
# FUNCTIONS
######################################################################


########################################
# remove all whitespaces from a string
#
def removeWhitespaces (strValue):
    return _reWhitespaces.sub('', strValue)


########################################
# substitute multiple whitespace characters by a single ' '
#
def collapseString (strValue, lstrip=1, rstrip=1):
    collStr = _reWhitespaces.sub(' ', strValue)
    if lstrip and rstrip:
        return collStr.strip()
    elif lstrip:
        return collStr.lstrip()
    elif rstrip:
        return collStr.rstrip()
    else:
        return collStr
        


########################################
# substitute each whitespace characters by a single ' '
#
def normalizeString (strValue):
    return _reWhitespace.sub(' ', strValue)


########################################
# process whitespace action
#
def processWhitespaceAction (strValue, wsAction, lstrip=1, rstrip=1):
    if wsAction == "collapse":
        return collapseString(strValue, lstrip, rstrip)
    elif wsAction == "replace":
        return normalizeString(strValue)
    else:
        return strValue
    

##########################################################
#  convert input parameter 'fileOrUrl' into a valid URL

def convertToUrl (fileOrUrl):
    matchObject = _reSplitUrlApplication.match(fileOrUrl)
    if matchObject:
        # given fileOrUrl is an absolute URL
        if matchObject.group(1) == 'file':
            path = re.sub(':', '|', matchObject.group(2)) # replace ':' by '|' in the path string
            url = "file:" + path
        else:
            url = fileOrUrl
    elif not os.path.isfile(fileOrUrl):
        # given fileOrUrl is treated as a relative URL
        url = fileOrUrl
    else:
        # local filename
#        url = "file:" + urllib.pathname2url (fileOrUrl)
        url = urllib.pathname2url (fileOrUrl)

    return url


##########################################################
#  convert input parameter 'fileOrUrl' into a valid absolute URL

def convertToAbsUrl (fileOrUrl, baseUrl):
    if fileOrUrl == "" and baseUrl != "":
        absUrl = "file:" + urllib.pathname2url (os.path.join(os.getcwd(), baseUrl, "__NO_FILE__"))
    elif os.path.isfile(fileOrUrl):
        absUrl = "file:" + urllib.pathname2url (os.path.join(os.getcwd(), fileOrUrl))
    else:
        matchObject = _reSplitUrlApplication.match(fileOrUrl)
        if matchObject:
            # given fileOrUrl is an absolute URL
            if matchObject.group(1) == 'file':
                path = re.sub(':', '|', matchObject.group(2)) # replace ':' by '|' in the path string
                absUrl = "file:" + path
            else:
                absUrl = fileOrUrl
        else:
            # given fileOrUrl is treated as a relative URL
            if baseUrl != "":
                absUrl = urlparse.urljoin (baseUrl, fileOrUrl)
            else:
                absUrl = fileOrUrl
#                raise IOError, "File %s not found!" %(fileOrUrl)
    return absUrl


##########################################################
#  normalize filter
def normalizeFilter (filterVar):
    if filterVar == None or filterVar == '*':
        filterVar = ("*",)
    elif not isinstance(filterVar, TupleType):
        filterVar = (filterVar,)
    return filterVar


######################################################################
# Namespace handling
######################################################################

def nsNameToQName (nsLocalName, curNs):
    """Convert a tuple '(namespace, localName)' to a string 'prefix:localName'
    
    Input parameter:
        nsLocalName:   tuple '(namespace, localName)' to be converted
        curNs:         list of current namespaces
    Returns the corresponding string 'prefix:localName' for 'nsLocalName'.
    """
    ns = nsLocalName[0]
    for prefix, namespace in curNs:
        if ns == namespace:
            if prefix != None:
                return "%s:%s" %(prefix, nsLocalName[1])
            else:
                return "%s" %nsLocalName[1]
    else:
        if ns == None:
            return nsLocalName[1]
        else:
            raise LookupError, "Prefix for namespaceURI '%s' not found!" % (ns)


def splitQName (qName):
    """Split the given 'qName' into prefix/namespace and local name.

    Input parameter:
        'qName':  contains a string 'prefix:localName' or '{namespace}localName'
    Returns a tuple (prefixOrNamespace, localName)
    """
    namespaceEndIndex = string.find (qName, '}')
    if namespaceEndIndex != -1:
        prefix     = qName[1:namespaceEndIndex]
        localName  = qName[namespaceEndIndex+1:]
    else:
        namespaceEndIndex = string.find (qName, ':')
        if namespaceEndIndex != -1:
            prefix     = qName[:namespaceEndIndex]
            localName  = qName[namespaceEndIndex+1:]
        else:
            prefix     = None
            localName  = qName
    return prefix, localName


def toClarkQName (tupleOrLocalName):
    """converts a tuple (namespace, localName) into clark notation {namespace}localName
       qNames without namespace remain unchanged

    Input parameter:
        'tupleOrLocalName':  tuple '(namespace, localName)' to be converted
    Returns a string {namespace}localName
    """
    if isinstance(tupleOrLocalName, TupleType):
        if tupleOrLocalName[0] != EMPTY_NAMESPACE:
            return "{%s}%s" %(tupleOrLocalName[0], tupleOrLocalName[1])
        else:
            return tupleOrLocalName[1]
    else:
        return tupleOrLocalName
    
    
def splitClarkQName (qName):
    """converts clark notation {namespace}localName into a tuple (namespace, localName)

    Input parameter:
        'qName':  {namespace}localName to be converted
    Returns prefix and localName as separate strings
    """
    namespaceEndIndex = string.find (qName, '}')
    if namespaceEndIndex != -1:
        prefix     = qName[1:namespaceEndIndex]
        localName  = qName[namespaceEndIndex+1:]
    else:
        prefix     = None
        localName  = qName
    return prefix, localName
    
    
##################################################################
# XML serialization of text
# the following functions assume an ascii-compatible encoding
# (or "utf-16")

_escape = re.compile(eval(r'u"[&<>\"\u0080-\uffff]+"'))

_escapeDict = {
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
}


def _raiseSerializationError(text):
    raise TypeError("cannot serialize %r (type %s)" % (text, type(text).__name__))


def _encode(text, encoding):
    try:
        return text.encode(encoding)
    except AttributeError:
        return text # assume the string uses the right encoding


def _encodeEntity(text, pattern=_escape):
    # map reserved and non-ascii characters to numerical entities
    def escapeEntities(m, map=_escapeDict):
        out = []
        append = out.append
        for char in m.group():
            text = map.get(char)
            if text is None:
                text = "&#%d;" % ord(char)
            append(text)
        return string.join(out, "")
    try:
        return _encode(pattern.sub(escapeEntities, text), "ascii")
    except TypeError:
        _raise_serialization_error(text)


def escapeCdata(text, encoding=None, replace=string.replace):
    # escape character data
    try:
        if encoding:
            try:
                text = _encode(text, encoding)
            except UnicodeError:
                return _encodeEntity(text)
        text = replace(text, "&", "&amp;")
        text = replace(text, "<", "&lt;")
        text = replace(text, ">", "&gt;")
        return text
    except (TypeError, AttributeError):
        _raiseSerializationError(text)


def escapeAttribute(text, encoding=None, replace=string.replace):
    # escape attribute value
    try:
        if encoding:
            try:
                text = _encode(text, encoding)
            except UnicodeError:
                return _encodeEntity(text)
        text = replace(text, "&", "&amp;")
        text = replace(text, "'", "&apos;") # FIXME: overkill
        text = replace(text, "\"", "&quot;")
        text = replace(text, "<", "&lt;")
        text = replace(text, ">", "&gt;")
        return text
    except (TypeError, AttributeError):
        _raiseSerializationError(text)


######################################################################
# CLASSES
######################################################################

######################################################################
# class containing a tuple of namespace prefix and localName
#
class QNameTuple(tuple):
    def __str__(self):
        if self[0] != EMPTY_PREFIX:
            return "%s:%s" %(self[0],self[1])
        else:
            return self[1]
    

def QNameTupleFactory(initValue):
    if isinstance(initValue, StringTypes):
        separatorIndex = string.find (initValue, ':')
        if separatorIndex != -1:
            initValue = (initValue[:separatorIndex], initValue[separatorIndex+1:])
        else:
           initValue = (EMPTY_PREFIX, initValue)
    return QNameTuple(initValue)


######################################################################
# class containing a tuple of namespace and localName
#
class NsNameTuple(tuple):
    def __str__(self):
        if self[0] != EMPTY_NAMESPACE:
            return "{%s}%s" %(self[0],self[1])
        elif self[1] != None:
            return self[1]
        else:
            return "None"


def NsNameTupleFactory(initValue):
    if isinstance(initValue, StringTypes):
        initValue = splitClarkQName(initValue)
    elif initValue == None:
        initValue = (EMPTY_NAMESPACE, initValue)
    return NsNameTuple(initValue)



########NEW FILE########
__FILENAME__ = minixsvWrapper
#!/usr/local/bin/python

import sys
import getopt
from ..genxmlif          import GenXmlIfError
from xsvalErrorHandler import ErrorHandler, XsvalError
from ..minixsv           import *
from pyxsval           import parseAndValidate


##########################################
# minixsv Wrapper for calling minixsv from command line

validSyntaxText = '''\
minixsv XML Schema Validator
Syntax: minixsv [-h] [-?] [-p Parser] [-s XSD-Filename] XML-Filename

Options:
-h, -?:          Display this help text
-p Parser:       XML Parser to be used 
                 (XMLIF_MINIDOM, XMLIF_ELEMENTTREE, XMLIF_4DOM
                  default: XMLIF_ELEMENTTREE)
-s XSD-FileName: specify the schema file for validation 
                 (if not specified in XML-File)
'''

def checkShellInputParameter():
    """check shell input parameters."""
    xmlInputFilename = None
    xsdFilename = None
    xmlParser = "XMLIF_ELEMENTTREE"
    try:
        (options, arguments) = getopt.getopt(sys.argv[1:], '?hp:s:')

        if ('-?','') in options or ('-h','') in options:
            print validSyntaxText
            sys.exit(-1)
        else:
            if len (arguments) == 1:
                xmlInputFilename = arguments[0]
                for o, a in options:
                    if o == "-s":
                        xsdFilename = a
                    if o == "-p":
                        if a in (XMLIF_MINIDOM, XMLIF_ELEMENTTREE, XMLIF_4DOM):
                            xmlParser = a    
                        else:
                            print 'Invalid XML parser %s!' %(a)
                            sys.exit(-1)
            else:
                print 'minixsv needs one argument (XML input file)!'
                sys.exit(-1)

    except getopt.GetoptError, errstr:
        print errstr
        sys.exit(-1)
    return xmlInputFilename, xsdFilename, xmlParser


def main():
    xmlInputFilename, xsdFileName, xmlParser = checkShellInputParameter()
    try:
        parseAndValidate (xmlInputFilename, xsdFile=xsdFileName, xmlIfClass=xmlParser)
    except IOError, errstr:
        print errstr
        sys.exit(-1)
    except GenXmlIfError, errstr:
        print errstr
        sys.exit(-1)
    except XsvalError, errstr:
        print errstr
        sys.exit(-1)
    
if __name__ == "__main__":
    main()
    

########NEW FILE########
__FILENAME__ = pyxsval
#
# minixsv, Release 0.9.0
# file: pyxsval.py
#
# API for XML schema validator
#
# history:
# 2004-09-09 rl   created
# 2004-09-29 rl   adapted to re-designed XML interface classes,
#                 ErrorHandler separated, URL processing added, some bugs fixed
# 2004-10-07 rl   Validator classes extracted into separate files
# 2004-10-12 rl   API re-worked, XML text processing added
# 2007-05-15 rl   Handling of several schema files added,
#                 schema references in the input file have now priority (always used if available!)
# 2008-08-01 rl   New optional parameter 'useCaching=1' and 'processXInclude=1' to XsValidator class added
#
# Copyright (c) 2004-2008 by Roland Leuthe.  All rights reserved.
#
# --------------------------------------------------------------------
# The minixsv XML schema validator is
#
# Copyright (c) 2004-2008 by Roland Leuthe
#
# By obtaining, using, and/or copying this software and/or its
# associated documentation, you agree that you have read, understood,
# and will comply with the following terms and conditions:
#
# Permission to use, copy, modify, and distribute this software and
# its associated documentation for any purpose and without fee is
# hereby granted, provided that the above copyright notice appears in
# all copies, and that both that copyright notice and this permission
# notice appear in supporting documentation, and that the name of
# the author not be used in advertising or publicity
# pertaining to distribution of the software without specific, written
# prior permission.
#
# THE AUTHOR DISCLAIMS ALL WARRANTIES WITH REGARD
# TO THIS SOFTWARE, INCLUDING ALL IMPLIED WARRANTIES OF MERCHANT-
# ABILITY AND FITNESS.  IN NO EVENT SHALL THE AUTHOR
# BE LIABLE FOR ANY SPECIAL, INDIRECT OR CONSEQUENTIAL DAMAGES OR ANY
# DAMAGES WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS,
# WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS
# ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR PERFORMANCE
# OF THIS SOFTWARE.
# --------------------------------------------------------------------

__all__ = [
    # public symbols
    "addUserSpecXmlIfClass",
    "parseAndValidate",
    "parseAndValidateString",
    "parseAndValidateXmlInput",
    "parseAndValidateXmlInputString",
    "parseAndValidateXmlSchema",
    "parseAndValidateXmlSchemaString",
    "XsValidator",
    ]


import string
from .. import genxmlif
from ..minixsv           import *
from xsvalErrorHandler import ErrorHandler
from xsvalXmlIf        import XsvXmlElementWrapper
from xsvalBase         import XsValBase
from xsvalSchema       import XsValSchema


__author__  = "Roland Leuthe <roland@leuthe-net.de>"
__date__    = "08. August 2008"
__version__ = "0.9.0"


_XS_VAL_DEFAULT_ERROR_LIMIT = 20

rulesTreeWrapper = None   # XML tree cache for "XMLSchema.xsd"


########################################
# retrieve version of minixsv
#
def getVersion ():
    return __version__


########################################
# access function for adding a user specific XML interface class
#
def addUserSpecXmlIfClass (xmlIfKey, factory):
    if not _xmlIfDict.has_key(xmlIfKey):
        _xmlIfDict[xmlIfKey] = factory
    else:
        raise KeyError, "xmlIfKey %s already implemented!" %(xmlIfKey)


########################################
# convenience function for validating
# 1. XML schema file
# 2. XML input file
# If xsdFile is specified, it will ONLY be used for validation if no schema file 
# is specified in the input file
# If xsdFile=None, the schemaLocation attribute is expected in the root tag of the XML input file
#
def parseAndValidate (inputFile, xsdFile=None, **kw):
    return parseAndValidateXmlInput (inputFile, xsdFile, 1, **kw)


########################################
# convenience function for validating
# 1. text string containing the XML schema
# 2. text string containing the XML input
# If xsdText is given, it will ONLY be used for validation if no schema file
# is specified in the input text
# If xsdText=None, the schemaLocation attribute is expected in the root tag of the XML input
#
def parseAndValidateString (inputText, xsdText=None, **kw):
    return parseAndValidateXmlInputString (inputText, xsdText, 1, **kw)


########################################
# factory for validating
# 1. XML schema file (only if validateSchema=1)
# 2. XML input file
# If xsdFile is specified, it will ONLY be used for validation if no schema file 
# is specified in the input file
# If xsdFile=None, the schemaLocation attribute is expected in the root tag of the XML input file
#
def parseAndValidateXmlInput (inputFile, xsdFile=None, validateSchema=0, **kw):
    xsValidator = XsValidator (**kw)
    # parse XML input file
    inputTreeWrapper = xsValidator.parse (inputFile)
    # validate XML input file
    return xsValidator.validateXmlInput (inputFile, inputTreeWrapper, xsdFile, validateSchema)


########################################
# factory for validating
# 1. text string containing the XML schema (only if validateSchema=1)
# 2. text string containing the XML input
# If xsdText is given, it will ONLY be used for validation if no schema file
# is specified in the input text
# If xsdText=None, the schemaLocation attribute is expected in the root tag of the XML input
#
def parseAndValidateXmlInputString (inputText, xsdText=None, baseUrl="", validateSchema=0, **kw):
    xsValidator = XsValidator (**kw)
    # parse XML input text string
    inputTreeWrapper = xsValidator.parseString (inputText, baseUrl)
    # validate XML input text string
    return xsValidator.validateXmlInputString (inputTreeWrapper, xsdText, validateSchema)


########################################
# factory for validating only given XML schema file
#
def parseAndValidateXmlSchema (xsdFile, **kw):
    xsValidator = XsValidator (**kw)
    # parse XML schema file
    xsdTreeWrapper = xsValidator.parse (xsdFile)
    # validate XML schema file
    return xsValidator.validateXmlSchema (xsdFile, xsdTreeWrapper)


########################################
# factory for validating only given XML schema file
#
def parseAndValidateXmlSchemaString (xsdText, **kw):
    xsValidator = XsValidator (**kw)
    # parse XML schema
    xsdTreeWrapper = xsValidator.parseString (xsdText)
    # validate XML schema
    return xsValidator.validateXmlSchema ("", xsdTreeWrapper)


########################################
# XML schema validator class
#
class XsValidator:
    def __init__(self, xmlIfClass=XMLIF_MINIDOM,
                 elementWrapperClass=XsvXmlElementWrapper,
                 warningProc=IGNORE_WARNINGS, errorLimit=_XS_VAL_DEFAULT_ERROR_LIMIT, 
                 verbose=0, useCaching=1, processXInclude=1):

        self.warningProc    = warningProc
        self.errorLimit     = errorLimit
        self.verbose        = verbose

        # select XML interface class
        self.xmlIf = _xmlIfDict[xmlIfClass](verbose, useCaching, processXInclude)
        self.xmlIf.setElementWrapperClass (elementWrapperClass)

        # create error handler
        self.errorHandler  = ErrorHandler (errorLimit, warningProc, verbose)

        self.schemaDependancyList = []


    ########################################
    # retrieve current version
    #
    def getVersion (self):
        return __version__
        

    ########################################
    # parse XML file
    # 'file' may be a filepath or an URI
    #
    def parse (self, file, baseUrl="", ownerDoc=None):
        self._verbosePrint ("Parsing %s..." %(file))
        return self.xmlIf.parse(file, baseUrl, ownerDoc)


    ########################################
    # parse text string containing XML
    #
    def parseString (self, text, baseUrl=""):
        self._verbosePrint ("Parsing XML text string...")
        return self.xmlIf.parseString(text, baseUrl)


    ########################################
    # validate XML input
    #
    def validateXmlInput (self, xmlInputFile, inputTreeWrapper, xsdFile=None, validateSchema=0):
        # if the input file contains schema references => use these
        xsdTreeWrapperList = self._readReferencedXsdFiles(inputTreeWrapper, validateSchema)
        if xsdTreeWrapperList == []:
            # if the input file doesn't contain schema references => use given xsdFile
            if xsdFile != None:
                xsdTreeWrapper = self.parse (xsdFile)
                xsdTreeWrapperList.append(xsdTreeWrapper)
                # validate XML schema file if requested
                if validateSchema:
                    self.validateXmlSchema (xsdFile, xsdTreeWrapper)
            else:
                self.errorHandler.raiseError ("No schema file specified!")

        self._validateXmlInput (xmlInputFile, inputTreeWrapper, xsdTreeWrapperList)
        for xsdTreeWrapper in xsdTreeWrapperList:
            xsdTreeWrapper.unlink()
        return inputTreeWrapper

    ########################################
    # validate XML input
    #
    def validateXmlInputString (self, inputTreeWrapper, xsdText=None, validateSchema=0):
        # if the input file contains schema references => use these
        xsdTreeWrapperList = self._readReferencedXsdFiles(inputTreeWrapper, validateSchema)
        if xsdTreeWrapperList == []:
            # if the input file doesn't contain schema references => use given xsdText
            if xsdText != None:
                xsdFile = "schema text"
                xsdTreeWrapper = self.parseString (xsdText)
                xsdTreeWrapperList.append(xsdTreeWrapper)
                # validate XML schema file if requested
                if validateSchema:
                    self.validateXmlSchema (xsdFile, xsdTreeWrapper)
            else:
                self.errorHandler.raiseError ("No schema specified!")

        self._validateXmlInput ("input text", inputTreeWrapper, xsdTreeWrapperList)
        for xsdTreeWrapper in xsdTreeWrapperList:
            xsdTreeWrapper.unlink()
        return inputTreeWrapper


    ########################################
    # validate XML schema separately
    #
    def validateXmlSchema (self, xsdFile, xsdTreeWrapper):
        # parse minixsv internal schema
        global rulesTreeWrapper
        if rulesTreeWrapper == None:
            rulesTreeWrapper = self.parse(os.path.join (MINIXSV_DIR, "XMLSchema.xsd"))

        self._verbosePrint ("Validating %s..." %(xsdFile))
        xsvGivenXsdFile = XsValSchema (self.xmlIf, self.errorHandler, self.verbose)
        xsvGivenXsdFile.validate(xsdTreeWrapper, [rulesTreeWrapper,])
        self.schemaDependancyList.append (xsdFile)
        self.schemaDependancyList.extend (xsvGivenXsdFile.xsdIncludeDict.keys())
        xsvGivenXsdFile.unlink()
        self.errorHandler.flushOutput()
        return xsdTreeWrapper


    ########################################
    # validate XML input tree and xsd tree if requested
    #
    def _validateXmlInput (self, xmlInputFile, inputTreeWrapper, xsdTreeWrapperList):
        self._verbosePrint ("Validating %s..." %(xmlInputFile))
        xsvInputFile = XsValBase (self.xmlIf, self.errorHandler, self.verbose)
        xsvInputFile.validate(inputTreeWrapper, xsdTreeWrapperList)
        xsvInputFile.unlink()
        self.errorHandler.flushOutput()


    ########################################
    # retrieve XML schema location from XML input tree
    #
    def _readReferencedXsdFiles (self, inputTreeWrapper, validateSchema):
        xsdTreeWrapperList = []
        # a schemaLocation attribute is expected in the root tag of the XML input file
        xsdFileList = self._retrieveReferencedXsdFiles (inputTreeWrapper)
        for namespace, xsdFile in xsdFileList:
            try:
                xsdTreeWrapper = self.parse (xsdFile, inputTreeWrapper.getRootNode().getAbsUrl())
            except IOError, e:
                if e.errno == 2: # catch IOError: No such file or directory
                    self.errorHandler.raiseError ("XML schema file %s not found!" %(xsdFile), inputTreeWrapper.getRootNode())
                else:
                    raise IOError(e.errno, e.strerror, e.filename)

            xsdTreeWrapperList.append(xsdTreeWrapper)
            # validate XML schema file if requested
            if validateSchema:
                self.validateXmlSchema (xsdFile, xsdTreeWrapper)

            if namespace != xsdTreeWrapper.getRootNode().getAttributeOrDefault("targetNamespace", None):
                self.errorHandler.raiseError ("Namespace of 'schemaLocation' attribute doesn't match target namespace of %s!" %(xsdFile), inputTreeWrapper.getRootNode())
            
        return xsdTreeWrapperList


    ########################################
    # retrieve XML schema location from XML input tree
    #
    def _retrieveReferencedXsdFiles (self, inputTreeWrapper):
        # a schemaLocation attribute is expected in the root tag of the XML input file
        inputRootNode = inputTreeWrapper.getRootNode()
        xsdFileList = []

        if inputRootNode.hasAttribute((XSI_NAMESPACE, "schemaLocation")):
            attributeValue = inputRootNode.getAttribute((XSI_NAMESPACE, "schemaLocation"))
            attrValList = string.split(attributeValue)
            if len(attrValList) % 2 == 0:
                for i in range(0, len(attrValList), 2):
                    xsdFileList.append((attrValList[i], attrValList[i+1]))
            else:
                self.errorHandler.raiseError ("'schemaLocation' attribute must have even number of URIs (pairs of namespace and xsdFile)!")

        if inputRootNode.hasAttribute((XSI_NAMESPACE, "noNamespaceSchemaLocation")):
            attributeValue = inputRootNode.getAttribute((XSI_NAMESPACE, "noNamespaceSchemaLocation"))
            attrValList = string.split(attributeValue)
            for attrVal in attrValList:
                xsdFileList.append ((None, attrVal))

        return xsdFileList

    ########################################
    # print if verbose flag is set
    #
    def _verbosePrint (self, text):
        if self.verbose:
            print text


########################################
# factory functions for enabling the selected XML interface class
#
def _interfaceFactoryMinidom (verbose, useCaching, processXInclude):
    return genxmlif.chooseXmlIf(genxmlif.XMLIF_MINIDOM, verbose, useCaching, processXInclude)

def _interfaceFactory4Dom (verbose, useCaching, processXInclude):
    return genxmlif.chooseXmlIf(genxmlif.XMLIF_4DOM, verbose, useCaching, processXInclude)

def _interfaceFactoryElementTree (verbose, useCaching, processXInclude):
    return genxmlif.chooseXmlIf(genxmlif.XMLIF_ELEMENTTREE, verbose, useCaching, processXInclude)


_xmlIfDict = {XMLIF_MINIDOM    :_interfaceFactoryMinidom,
              XMLIF_4DOM       :_interfaceFactory4Dom,
              XMLIF_ELEMENTTREE:_interfaceFactoryElementTree}


########NEW FILE########
__FILENAME__ = xsvalBase
#
# minixsv, Release 0.9.0
# file: xsvalBase.py
#
# XML schema validator base class
#
# history:
# 2004-10-07 rl   created
# 2006-08-18 rl   W3C testsuite passed for supported features
# 2007-06-14 rl   Features for release 0.8 added, several bugs fixed
#
# Copyright (c) 2004-2008 by Roland Leuthe.  All rights reserved.
#
# --------------------------------------------------------------------
# The minixsv XML schema validator is
#
# Copyright (c) 2004-2008 by Roland Leuthe
#
# By obtaining, using, and/or copying this software and/or its
# associated documentation, you agree that you have read, understood,
# and will comply with the following terms and conditions:
#
# Permission to use, copy, modify, and distribute this software and
# its associated documentation for any purpose and without fee is
# hereby granted, provided that the above copyright notice appears in
# all copies, and that both that copyright notice and this permission
# notice appear in supporting documentation, and that the name of
# the author not be used in advertising or publicity
# pertaining to distribution of the software without specific, written
# prior permission.
#
# THE AUTHOR DISCLAIMS ALL WARRANTIES WITH REGARD
# TO THIS SOFTWARE, INCLUDING ALL IMPLIED WARRANTIES OF MERCHANT-
# ABILITY AND FITNESS.  IN NO EVENT SHALL THE AUTHOR
# BE LIABLE FOR ANY SPECIAL, INDIRECT OR CONSEQUENTIAL DAMAGES OR ANY
# DAMAGES WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS,
# WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS
# ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR PERFORMANCE
# OF THIS SOFTWARE.
# --------------------------------------------------------------------

import string
import copy
from ..minixsv             import *
from ..genxmlif.xmlifUtils import collapseString, convertToAbsUrl, NsNameTupleFactory, NsNameTuple
from xsvalSimpleTypes    import XsSimpleTypeVal, SimpleTypeError


wxsdTree = None
wxsdLookupDict = {}


##########################################################
#  Validator class for validating one input file against one XML schema file

class XsValBase:

    def __init__(self, xmlIf, errorHandler, verbose):
        self.xmlIf         = xmlIf
        self.errorHandler  = errorHandler
        self.verbose       = verbose

        self._raiseError   = self.errorHandler.raiseError
        self._addError     = self.errorHandler.addError
        self._addWarning   = self.errorHandler.addWarning
        self._addInfo      = self.errorHandler.addInfo

        self.checkKeyrefList = []


    def unlink(self):
        self.simpleTypeVal.unlink()
        

    ########################################
    # validate inputTree against xsdTree
    #
    def validate (self, inputTree, xsdTreeList):
        self.inputTree = inputTree

        self.inputRoot   = self.inputTree.getRootNode()

        self.inputNsURI  = self.inputRoot.getNamespaceURI()
        self.inputNsPrefix = self.inputRoot.getNsPrefix(self.inputRoot.getNsName())
        if self.inputNsPrefix != None:
            self.inputNsPrefixString = "%s:" %(self.inputNsPrefix)
        else:
            self.inputNsPrefixString = ""

        # initialise lookup dictionary
        global wxsdLookupDict
        if wxsdLookupDict == {}:
            wxsdLookupDict = {"ElementDict":{}, "TypeDict":{}, "GroupDict":{},
                              "AttrGroupDict":{}, "AttributeDict":{}, "IdentityConstrDict":{}}
            self._importWellknownSchemas(wxsdLookupDict)
   
        self.xsdLookupDict = {"ElementDict":        wxsdLookupDict["ElementDict"].copy(), 
                              "TypeDict":           wxsdLookupDict["TypeDict"].copy(), 
                              "GroupDict":          wxsdLookupDict["GroupDict"].copy(),
                              "AttrGroupDict":      wxsdLookupDict["AttrGroupDict"].copy(), 
                              "AttributeDict":      wxsdLookupDict["AttributeDict"].copy(), 
                              "IdentityConstrDict": wxsdLookupDict["IdentityConstrDict"].copy()}
        self.xsdElementDict        = self.xsdLookupDict["ElementDict"]
        self.xsdTypeDict           = self.xsdLookupDict["TypeDict"]
        self.xsdGroupDict          = self.xsdLookupDict["GroupDict"]
        self.xsdAttrGroupDict      = self.xsdLookupDict["AttrGroupDict"]
        self.xsdAttributeDict      = self.xsdLookupDict["AttributeDict"]
        self.xsdIdentityConstrDict = self.xsdLookupDict["IdentityConstrDict"]

        self.xsdIdDict = {}
        self.xsdIdRefDict = {}
        self.idAttributeForType = None

        for xsdTree in xsdTreeList:
            xsdRoot     = xsdTree.getRootNode()

            # TODO: The following member may differ if several schema files are used!!
            self.xsdNsURI    = xsdRoot.getNamespaceURI()

            self.xsdIncludeDict = {xsdRoot.getAbsUrl():1,}
            if xsdRoot.getFilePath() != os.path.join (MINIXSV_DIR, "XMLSchema.xsd"):
                self._initInternalAttributes (xsdRoot)
                self._updateLookupTables(xsdRoot, self.xsdLookupDict)
            
                self._includeAndImport (xsdTree, xsdTree, self.xsdIncludeDict, self.xsdLookupDict)
            

        self.simpleTypeVal = XsSimpleTypeVal(self)

        inputRootNsName = self.inputRoot.getNsName()
        if self.xsdElementDict.has_key(inputRootNsName):
            # start recursive schema validation
            try:
                self._checkElementTag (self.xsdElementDict[inputRootNsName], self.inputRoot, (self.inputRoot,), 0)
            except TagException, errInst:
                self._addError (errInst.errstr, errInst.node, errInst.endTag)

            if not self.errorHandler.hasErrors():
                # validate IDREFs
                for idref in self.xsdIdRefDict.keys():
                    if not self.xsdIdDict.has_key(idref):
                        self._addError ("There is no ID/IDREF binding for IDREF %s" %repr(idref), self.xsdIdRefDict[idref])

                # validate keyrefs
                for inputElement, keyrefNode in self.checkKeyrefList:
                    self._checkKeyRefConstraint (keyrefNode, inputElement)
        else:
            self._raiseError ("Used root tag %s not found in schema file(s)!"
                              %repr(inputRootNsName), self.inputRoot)
        

    ########################################
    # include/import all files specified in the schema file
    # import well-known schemas
    #
    def _includeAndImport (self, baseTree, tree, includeDict, lookupDict):
        self._expandIncludes (baseTree, tree, includeDict, lookupDict)
        self._expandRedefines (baseTree, tree, includeDict, lookupDict)
        self._expandImports (baseTree, tree, includeDict, lookupDict)


    ########################################
    # expand include directives
    #
    def _expandIncludes (self, baseTree, tree, includeDict, lookupDict):
        rootNode = tree.getRootNode()
        namespaceURI  = rootNode.getNamespaceURI()
        for includeNode in rootNode.getChildrenNS(namespaceURI, "include"):
            includeUrl = includeNode.getAttribute("schemaLocation")
            expNamespace = rootNode.getAttributeOrDefault("targetNamespace", None)
            self._includeSchemaFile (baseTree, tree, includeNode, expNamespace, includeUrl, includeNode.getBaseUrl(), includeDict, lookupDict,
                                     adaptTargetNamespace=1)
            rootNode.removeChild (includeNode)


    ########################################
    # expand redefine directives
    #
    def _expandRedefines (self, baseTree, tree, includeDict, lookupDict):
        rootNode = tree.getRootNode()
        namespaceURI  = rootNode.getNamespaceURI()

        for redefineNode in rootNode.getChildrenNS(namespaceURI, "redefine"):
            redefineUrl = redefineNode.getAttribute("schemaLocation")
            expNamespace = rootNode.getAttributeOrDefault("targetNamespace", None)
            self._includeSchemaFile (baseTree, tree, redefineNode, expNamespace, redefineUrl, redefineNode.getBaseUrl(), includeDict, lookupDict,
                                     adaptTargetNamespace=1)

            # fill lookup tables with redefined definitions
            for childNode in redefineNode.getChildren():
                redefineNode.removeChild(childNode)
                rootNode.insertBefore(childNode, redefineNode)

                if childNode.getLocalName() in ("complexType", "simpleType"):
                    xsdDict = self.xsdLookupDict["TypeDict"]
                elif childNode.getLocalName() in ("attributeGroup"):
                    xsdDict = self.xsdLookupDict["AttrGroupDict"]
                elif childNode.getLocalName() in ("group"):
                    xsdDict = self.xsdLookupDict["GroupDict"]
                elif childNode.getLocalName() in ("annotation"):
                    continue
                else:
                    self._addError ("%s not allowed as child of 'redefine'!" %repr(childNode.getLocalName()), childNode)
                    continue

                redefType = NsNameTuple ( (expNamespace, childNode.getAttribute("name")) )
                if xsdDict.has_key(redefType):
                    orgRedefType = NsNameTuple( (expNamespace, redefType[1]+"__ORG") )
                    if not xsdDict.has_key(orgRedefType):
                        xsdDict[orgRedefType] = xsdDict[redefType]
#                    else:
#                        self._addError ("Duplicate component %s found within 'redefine'!" %repr(redefType), childNode)
                    xsdDict[redefType] = childNode
                else:
                    self._addError ("Type %s not found in imported schema file!" %(repr(redefType)), childNode)

                dummy, attrNodes, attrNsNameFirst = childNode.getXPathList (".//@base | .//@ref" % vars())
                for attrNode in attrNodes:
                    if attrNode.hasAttribute("base"):
                        attribute = "base"
                    elif attrNode.hasAttribute("ref"):
                        attribute = "ref"
                    if attrNode.getQNameAttribute(attribute) == redefType:
                        attrNode[attribute] = attrNode[attribute] + "__ORG"
                
            rootNode.removeChild (redefineNode)


    ########################################
    # expand import directives
    #
    def _expandImports (self, baseTree, tree, includeDict, lookupDict):
        rootNode = tree.getRootNode()
        namespaceURI  = rootNode.getNamespaceURI()

        for includeNode in rootNode.getChildrenNS(namespaceURI, "import"):
            expNamespace = includeNode.getAttributeOrDefault("namespace", None)
            if expNamespace == self._getTargetNamespace(includeNode):
                self._addError ("Target namespace and target namespace of imported schema must not be the same!",  includeNode)
                continue

            includeUrl = includeNode.getAttributeOrDefault("schemaLocation", None)
            if expNamespace != None and includeUrl == None:
                includeUrl = expNamespace + ".xsd"
            if includeUrl != None:            
                if expNamespace not in (XML_NAMESPACE, XSI_NAMESPACE):
                    self._includeSchemaFile (baseTree, tree, includeNode, expNamespace, includeUrl, includeNode.getBaseUrl(), includeDict, lookupDict)
            else:
                self._addError ("schemaLocation attribute for import directive missing!",  includeNode)
            rootNode.removeChild (includeNode)


    ########################################
    # import well-known schema files
    #
    def _importWellknownSchemas (self, lookupDict):
        global wxsdTree
        file = os.path.join (MINIXSV_DIR, "XMLSchema.xsd")
        wxsdTree = self.xmlIf.parse (file)
        self._initInternalAttributes (wxsdTree.getRootNode())
        self._updateLookupTables (wxsdTree.getRootNode(), lookupDict)

        for schemaFile in ("datatypes.xsd", "xml.xsd", "XMLSchema-instance.xsd"):
            file = os.path.join (MINIXSV_DIR, schemaFile)
            subTree = self._parseIncludeSchemaFile(wxsdTree, wxsdTree, None, file, None)
            self._updateLookupTables (subTree.getRootNode(), lookupDict)


    ########################################
    # include/import a schema file
    #
    def _includeSchemaFile (self, baseTree, tree, nextSibling, expNamespace, includeUrl, baseUrl, includeDict, lookupDict, 
                            adaptTargetNamespace=0):
        if includeUrl == None:
            self._raiseError ("Schema location attribute missing!", nextSibling)
        absUrl = convertToAbsUrl (includeUrl, baseUrl)
        if includeDict.has_key (absUrl):
            # file already included
            return

        if self.verbose:
            print "including %s..." %(includeUrl)
        rootNode = tree.getRootNode()

        subTree = self._parseIncludeSchemaFile(baseTree, tree, nextSibling, includeUrl, baseUrl)
        includeDict[absUrl] = 1

        stRootNode = subTree.getRootNode()
        if rootNode.getNsName() != stRootNode.getNsName():
            self._raiseError ("Root tag of file %s does not match!" %repr(includeUrl), nextSibling)

        if stRootNode.hasAttribute("targetNamespace"):
            if expNamespace != stRootNode["targetNamespace"]:
                self._raiseError ("Target namespace of file %s does not match!" %repr(includeUrl), nextSibling)
        else:
           if expNamespace != None: 
               if adaptTargetNamespace:
                    # if no target namespace is specified in the included file
                    # the target namespace of the parent file is taken
                    stRootNode["targetNamespace"] = expNamespace
                    for stDescNode in stRootNode.getIterator():
                        stDescNode.curNs.append((EMPTY_PREFIX,expNamespace))
               else:
                   self._raiseError ("Target namespace of file %s does not match!" %repr(includeUrl), nextSibling)
                    
        self._updateLookupTables (subTree.getRootNode(), lookupDict)
        self._includeAndImport (baseTree, subTree, includeDict, lookupDict)
        if includeUrl not in (r"C:\Program Files\Python24\Lib\site-packages\minixsv\xml.xsd",
                              r"C:\Program Files\Python24\Lib\site-packages\minixsv\XMLSchema.xsd",
                              r"C:\Program Files\Python24\Lib\site-packages\minixsv\XMLSchema-instance.xsd"):
            rootNode.insertSubtree (nextSibling, subTree, insertSubTreeRootNode=0)


    def _parseIncludeSchemaFile (self, baseTree, tree, nextSibling, includeUrl, baseUrl):
        # try to parse included schema file
        try:
            subTree = self.xmlIf.parse (includeUrl, baseUrl, baseTree.getTree())
            self._initInternalAttributes (subTree.getRootNode())
        except IOError, errInst:
            self._raiseError ("%s" %str(errInst), nextSibling)
        except SyntaxError, e:
            # FIXME: sometimes an URLError is catched instead of a standard IOError
            try:
                dummy = e.errno
            except: 
                raise IOError, e
            
            if e.errno in (2, "socket error", "url error"): # catch IOError: No such file or directory
                self._raiseError ("%s: '%s'" %(e.strerror, e.filename), nextSibling)
            else:
                raise
        
        return subTree

    ########################################
    # update lookup dictionaries used during validation
    #
    def _updateLookupTables (self, rootNode, lookupDict):
        schemaTagDict = {"element"    : "ElementDict",
                         "complexType": "TypeDict",
                         "simpleType" : "TypeDict",
                         "group"      : "GroupDict",
                         "attributeGroup": "AttrGroupDict",
                         "attribute"     : "AttributeDict",
                        }

        # retrieve all schema tags
        for localName, lookupDictName in schemaTagDict.items():
            for node in rootNode.getChildrenNS(XSD_NAMESPACE, localName):
                targetNamespace = self._getTargetNamespace(node)
                if not lookupDict[lookupDictName].has_key((targetNamespace, node.getAttribute("name"))):
                    lookupDict[lookupDictName][(targetNamespace, node.getAttribute("name"))] = node
        
        # retrieve all identity constraints
        for identConstrTagName in ("unique", "key", "keyref"):
            identConstrNodeList = rootNode.getElementsByTagNameNS (XSD_NAMESPACE, identConstrTagName)
            for identConstrNode in identConstrNodeList:
                targetNamespace = self._getTargetNamespace(identConstrNode)
                identConstrNsLocalName = NsNameTupleFactory ( (targetNamespace, identConstrNode.getAttribute("name")) )
                if not lookupDict["IdentityConstrDict"].has_key(identConstrNsLocalName):
                    lookupDict["IdentityConstrDict"][identConstrNsLocalName] = {"Node": identConstrNode, "ValueDict":{}}

#                else:
#                    self._addError ("Duplicate identity constraint name %s found!"
#                                    %(repr(identConstrNsLocalName)), identConstrNode)

    ########################################
    # validate inputNode against complexType node
    #
    def _initInternalAttributes (self, rootNode):
        # set schema root node for all descendant nodes
        if not rootNode.getSchemaRootNode():
            for node in rootNode.getIterator():
                node.setSchemaRootNode(rootNode)


    ########################################
    # validate inputNode against complexType node
    #
    def _checkComplexTypeTag (self, xsdParentNode, xsdNode, inputNode, inputChildIndex, usedAsBaseType=None):
        baseTypeAttributes = {}

        complexContentNode = xsdNode.getFirstChildNS(self.xsdNsURI, "complexContent")
        simpleContentNode = xsdNode.getFirstChildNS(self.xsdNsURI, "simpleContent")
        if complexContentNode != None:
            inputChildIndex, baseTypeAttributes = self._checkComplexContentTag (xsdParentNode, complexContentNode, inputNode, inputChildIndex, usedAsBaseType, baseTypeAttributes)
        elif simpleContentNode != None:
            inputChildIndex, baseTypeAttributes = self._checkSimpleContentTag (xsdParentNode, simpleContentNode, inputNode, inputChildIndex, usedAsBaseType, baseTypeAttributes)
        else:
            inputChildIndex, baseTypeAttributes = self._checkComplexTypeContent (xsdParentNode, xsdNode, inputNode, inputChildIndex, usedAsBaseType, baseTypeAttributes)
            if usedAsBaseType == None:
                self._checkMixed (xsdParentNode, xsdNode, inputNode)
        return inputChildIndex, baseTypeAttributes

    def _checkComplexContentTag (self, xsdParentNode, xsdNode, inputNode, inputChildIndex, usedAsBaseType, baseTypeAttributes):
        extensionNode = xsdNode.getFirstChildNS(self.xsdNsURI, "extension")
        if extensionNode != None:
            inputChildIndex, baseTypeAttributes = self._checkExtensionComplexContent (xsdParentNode, extensionNode, inputNode, inputChildIndex, usedAsBaseType, baseTypeAttributes)
        else:
            restrictionNode = xsdNode.getFirstChildNS(self.xsdNsURI, "restriction")
            if restrictionNode != None:
                inputChildIndex, baseTypeAttributes = self._checkRestrictionComplexContent (xsdParentNode, restrictionNode, inputNode, inputChildIndex, usedAsBaseType, baseTypeAttributes)
            else:
                raise AttributeError, "RestrictionNode not found!"

#        if usedAsBaseType == None:
#            self._checkMixed (xsdNode, inputNode)
        return inputChildIndex, baseTypeAttributes

    def _checkSimpleContentTag (self, xsdParentNode, xsdNode, inputNode, inputChildIndex, usedAsBaseType, baseTypeAttributes):
        if inputNode.getAttribute( (XSI_NAMESPACE, "nil") ) == "true":
            if inputNode.getChildren() != [] or collapseString(inputNode.getElementValue()) != "":
                self._addError ("Element must be empty (xsi:nil='true')(1)!" , inputNode, 0)

        extensionNode = xsdNode.getFirstChildNS(self.xsdNsURI, "extension")
        if extensionNode != None:
            inputChildIndex, baseTypeAttributes = self._checkExtensionSimpleContent (xsdParentNode, extensionNode, inputNode, inputChildIndex, usedAsBaseType, baseTypeAttributes)
        else:
            restrictionNode = xsdNode.getFirstChildNS(self.xsdNsURI, "restriction")
            if restrictionNode != None:
                inputChildIndex, baseTypeAttributes = self._checkRestrictionSimpleContent (xsdParentNode, xsdNode, restrictionNode, inputNode, inputChildIndex, usedAsBaseType, baseTypeAttributes)
        return inputChildIndex, baseTypeAttributes

    def _checkExtensionComplexContent (self, xsdParentNode, xsdNode, inputNode, inputChildIndex, usedAsBaseType, baseTypeAttributes):
        baseNsName = xsdNode.getQNameAttribute("base")
        if usedAsBaseType == None: 
            extUsedAsBaseType = "extension"
        else:
            extUsedAsBaseType = usedAsBaseType
        inputChildIndex, baseTypeAttributes = self._checkComplexTypeTag (xsdParentNode, self.xsdTypeDict[baseNsName], inputNode, inputChildIndex, extUsedAsBaseType)

        inputChildIndex, baseTypeAttributes = self._checkComplexTypeContent (xsdParentNode, xsdNode, inputNode, inputChildIndex, usedAsBaseType, baseTypeAttributes)
        return inputChildIndex, baseTypeAttributes

    def _checkExtensionSimpleContent (self, xsdParentNode, xsdNode, inputNode, inputChildIndex, usedAsBaseType, baseTypeAttributes):
        self._checkSimpleType (xsdNode, "base", inputNode, inputNode.getTagName(), inputNode.getElementValue(), None, checkAttribute=0)
        if xsdNode.hasAttribute("BaseTypes"):
            xsdParentNode["BaseTypes"] = xsdNode["BaseTypes"]
        inputChildIndex, baseTypeAttributes = self._checkSimpleTypeContent (xsdParentNode, xsdNode, inputNode, inputChildIndex, usedAsBaseType, baseTypeAttributes)
        return inputChildIndex, baseTypeAttributes

    def _checkRestrictionComplexContent (self, xsdParentNode, xsdNode, inputNode, inputChildIndex, usedAsBaseType, baseTypeAttributes):
        # first check against base type (retrieve only the base type attributes)
        baseNsName = xsdNode.getQNameAttribute("base")
        inputChildIndex, baseTypeAttributes = self._checkComplexTypeTag (xsdParentNode, self.xsdTypeDict[baseNsName], inputNode, inputChildIndex, "restriction")

        # then check input against derived complex type
        inputChildIndex, baseTypeAttributes = self._checkComplexTypeContent (xsdParentNode, xsdNode, inputNode, inputChildIndex, usedAsBaseType, baseTypeAttributes)
        return inputChildIndex, baseTypeAttributes

    def _checkRestrictionSimpleContent (self, xsdParentNode, simpleContentNode, xsdNode, inputNode, inputChildIndex, usedAsBaseType, baseTypeAttributes):
        try:
            simpleTypeReturnDict = {"BaseTypes":[], "primitiveType":None}
            self.simpleTypeVal.checkSimpleTypeDef (inputNode, simpleContentNode, inputNode.getTagName(), inputNode.getElementValue(), simpleTypeReturnDict, idCheck=1)
            xsdNode["BaseTypes"] = string.join (simpleTypeReturnDict["BaseTypes"], " ")
        except SimpleTypeError, errInst:
            self._addError (errInst.args[0], inputNode)

        inputChildIndex, baseTypeAttributes = self._checkSimpleTypeContent (xsdParentNode, xsdNode, inputNode, inputChildIndex, usedAsBaseType, baseTypeAttributes)
        return inputChildIndex, baseTypeAttributes

    def _checkComplexTypeContent (self, xsdParentNode, xsdNode, inputNode, inputChildIndex, usedAsBaseType, baseTypeAttributes):
        if inputNode.getAttribute((XSI_NAMESPACE, "nil")) == "true":
            if inputNode.getChildren() != [] or collapseString(inputNode.getElementValue()) != "":
                self._addError ("Element must be empty (xsi:nil='true')(2)!" , inputNode, 0)
        else:
            childTags = inputNode.getChildren()
            if usedAsBaseType in (None, "extension"):
                validChildTags = xsdNode.getChildren()
                for validChildTag in validChildTags:
                    if validChildTag.getLocalName() not in ("attribute", "attributeGroup", "anyAttribute"):
                        inputChildIndex = self._checkParticle (validChildTag, inputNode, childTags, inputChildIndex)

                if usedAsBaseType == None and inputChildIndex < len (childTags):
                    inputNsName = inputNode.getNsName()
                    childNsName = childTags[inputChildIndex].getNsName()
                    self._addError ("Unexpected or invalid child tag %s found in tag %s!"
                                    %(repr(childNsName), repr(inputNsName)), childTags[inputChildIndex])

        if usedAsBaseType in (None,):
            self._checkAttributeTags (xsdParentNode, xsdNode, inputNode, baseTypeAttributes)

        if usedAsBaseType in ("restriction", "extension"):
            self._updateAttributeDict (xsdNode, baseTypeAttributes)

        return inputChildIndex, baseTypeAttributes

    def _checkSimpleTypeContent (self, xsdParentNode, xsdNode, inputNode, inputChildIndex, usedAsBaseType, baseTypeAttributes):
        if inputNode.getChildren() != []:
            raise TagException ("No child tags are allowed for element %s!" %repr(inputNode.getNsName()), inputNode)

        if usedAsBaseType in (None,):
            self._checkAttributeTags (xsdParentNode, xsdNode, inputNode, baseTypeAttributes)

        if usedAsBaseType in ("restriction", "extension"):
            self._updateAttributeDict (xsdNode, baseTypeAttributes)

        return inputChildIndex, baseTypeAttributes


    ########################################
    # validate mixed content (1)
    #
    def _checkMixed (self, xsdParentNode, xsdNode, inputNode):
        if xsdNode.getAttributeOrDefault ("mixed", "false") == "false":
            if not collapseString(inputNode.getElementValue()) in ("", " "):
                self._addError ("Mixed content not allowed for %s!" %repr(inputNode.getTagName()), inputNode)
        else: # mixed = true
            self._checkUrType(xsdParentNode, inputNode)


    ########################################
    # check ur-type
    #
    def _checkUrType (self, xsdNode, inputNode):
        prefix = xsdNode.getPrefix()
        if prefix:
            xsdNode["__CONTENTTYPE__"] = "%s:string" %xsdNode.getPrefix()
        else:
            xsdNode["__CONTENTTYPE__"] = "string"
        self._checkElementValue (xsdNode, "__CONTENTTYPE__", inputNode)
        xsdNode.removeAttribute("__CONTENTTYPE__")
    

    ########################################
    # validate inputNodeList against xsdNode
    #
    def _checkList (self, elementMethod, xsdNode, inputParentNode, inputNodeList, currIndex):
        minOccurs = string.atoi(xsdNode.getAttributeOrDefault("minOccurs", "1"))
        maxOccurs = xsdNode.getAttributeOrDefault("maxOccurs", "1")
        if maxOccurs != "unbounded":
            maxOccurs = string.atoi(maxOccurs)
        else:
            maxOccurs = -1
        occurs = 0
        while maxOccurs == -1 or occurs < maxOccurs:
            try:
                newIndex = elementMethod (xsdNode, inputParentNode, inputNodeList, currIndex)
                occurs += 1
                if newIndex > currIndex:
                    currIndex = newIndex
                else:
                    break # no suitable element found
            except TagException, errInst:
                break

        if occurs == 0 and minOccurs > 0:
            raise errInst
        elif occurs < minOccurs:
            expInputTagName = xsdNode.getAttribute("name")
            if expInputTagName == None:
                expInputTagName = xsdNode.getQNameAttribute("ref")
            raise TagException ("minOccurs (%d) of child tag %s in tag %s not available (only %d)!"
                                %(minOccurs, repr(expInputTagName), repr(inputParentNode.getTagName()), occurs), inputParentNode, 1)

        return currIndex

    ########################################
    # validate inputNode against element node
    #
    def _checkElementTag (self, xsdNode, inputParentNode, inputNodeList, currIndex):
        if xsdNode.hasAttribute("ref"):
            refNsName = xsdNode.getQNameAttribute("ref")
            currIndex = self._checkElementTag (self.xsdElementDict[refNsName], inputParentNode, inputNodeList, currIndex)
        else:
            nameAttr = xsdNode.getAttribute ("name")

            if currIndex >= len (inputNodeList):
                raise TagException ("Missing child tag %s in tag %s!" %(repr(nameAttr), repr(inputParentNode.getTagName())), inputParentNode, 1)

            inputNode = inputNodeList[currIndex]
            if nameAttr != inputNode.getLocalName():
                raise TagException ("Missing child tag %s in tag %s!" %(repr(nameAttr), repr(inputParentNode.getTagName())), inputNode, 0)

            # store reference to XSD definition node
            inputNode.setXsdNode(xsdNode)

            currIndex = currIndex + 1

            self._checkInputElementForm (xsdNode, nameAttr, inputNode)

            if (xsdNode.getFirstChild() == None and 
                not xsdNode.hasAttribute("type") and 
                not inputNode.hasAttribute((XSI_NAMESPACE, "type")) ):
                self._checkUrType(xsdNode, inputNode)
                # ur-type => try to check children of input node
                for inputChild in inputNode.getChildren():
                    try:
                        if self.xsdElementDict.has_key(inputChild.getNsName()):
                            self._checkElementTag (self.xsdElementDict[inputChild.getNsName()], inputNode, (inputChild,), 0)
                    except TagException, errInst:
                        self._addError (errInst.errstr, errInst.node, errInst.endTag)
                return currIndex
            
            complexTypeNode = xsdNode.getFirstChildNS (self.xsdNsURI, "complexType")
            if not inputNode.hasAttribute((XSI_NAMESPACE, "type")):
                typeNsName = xsdNode.getQNameAttribute ("type")
            else:
                # overloaded type is used
                typeNsName = inputNode.getQNameAttribute((XSI_NAMESPACE, "type"))
                if not self.xsdTypeDict.has_key(typeNsName):
                    self._addError ("Unknown overloaded type %s!" %(repr(typeNsName)), inputNode, 0)
                    return currIndex

            if self.xsdTypeDict.has_key (typeNsName):
                typeType = self.xsdTypeDict[typeNsName].getLocalName()
                if typeType == "complexType":
                    complexTypeNode = self.xsdTypeDict[typeNsName]
                # else simpleType => pass, handled later on

            if complexTypeNode != None:
                try:
                    self._checkComplexTypeTag (xsdNode, complexTypeNode, inputNode, 0)
                except TagException, errInst:
                    self._addError (errInst.errstr, errInst.node, errInst.endTag)
                    return currIndex
            else:
                self._checkElementSimpleType (xsdNode, "type", inputNode)

            # check unique attributes and keys
            childUniqueDefList = xsdNode.getChildrenNS (self.xsdNsURI, "unique")
            for childUniqueDef in childUniqueDefList:
                self._checkIdentityConstraint (childUniqueDef, inputNode)

            childKeyDefList = xsdNode.getChildrenNS (self.xsdNsURI, "key")
            for childKeyDef in childKeyDefList:
                self._checkIdentityConstraint (childKeyDef, inputNode)

            childKeyrefDefList = xsdNode.getChildrenNS (self.xsdNsURI, "keyref")
            for childKeyrefDef in childKeyrefDefList:
                self.checkKeyrefList.append ((inputNode, childKeyrefDef))

        return currIndex


    ########################################
    # validate element inputNode against simple type definition
    #
    def _checkElementSimpleType (self, xsdNode, xsdTypeAttr, inputNode):
        if inputNode.getChildren() != []:
            raise TagException ("No child tags are allowed for element %s!" %(repr(inputNode.getNsName())), inputNode)

        self._checkElementValue (xsdNode, xsdTypeAttr, inputNode)

        self._checkAttributeTags (xsdNode, xsdNode, inputNode, {})


    ########################################
    # validate inputNode against simple type definition
    #
    def _checkElementValue (self, xsdNode, xsdTypeAttr, inputNode):
        fixedValue = xsdNode.getAttribute("fixed")
        if inputNode.getAttribute((XSI_NAMESPACE, "nil")) == "true" and fixedValue != None:
            self._addError ("There must be no fixed value for Element because xsi:nil='true' is specified!" , inputNode)

        if inputNode.getAttribute((XSI_NAMESPACE, "nil")) != "true" and inputNode.getElementValue() == "":
            if xsdNode.hasAttribute("default"):
                inputNode.setElementValue(xsdNode["default"])
            if fixedValue != None:
                inputNode.setElementValue(fixedValue)

        self._checkSimpleType (xsdNode, xsdTypeAttr, inputNode, inputNode.getTagName(), inputNode.getElementValue(), fixedValue, checkAttribute=0)


    ########################################
    # validate inputNode against simple type definition
    #
    def _checkSimpleType (self, xsdNode, xsdTypeAttr, inputNode, attrName, attrValue, fixedValue, checkAttribute=0, checkId=1):
        retValue = None

        if checkAttribute == 0 and inputNode.hasAttribute((XSI_NAMESPACE, "nil")):
            if (inputNode[(XSI_NAMESPACE, "nil")] == "true" and
                collapseString(inputNode.getElementValue()) != ""):
                self._addError ("Element must be empty (xsi:nil='true')(3)!" , inputNode, 0)
            return retValue
        
        try:
            simpleTypeReturnDict = {"BaseTypes":[], "primitiveType":None}
            fixedValueReturnDict = {"BaseTypes":[], "primitiveType":None}
            simpleTypeNode  = xsdNode.getFirstChildNS (self.xsdNsURI, "simpleType")
            if simpleTypeNode != None:
                self.simpleTypeVal.checkSimpleTypeDef (inputNode, simpleTypeNode, attrName, attrValue, simpleTypeReturnDict, checkId)
                if fixedValue != None:
                    self.simpleTypeVal.checkSimpleTypeDef (inputNode, simpleTypeNode, attrName, fixedValue, fixedValueReturnDict, idCheck=0)
            elif (xsdNode.getFirstChildNS (self.xsdNsURI, "complexType") != None and
                  xsdNode.getFirstChildNS (self.xsdNsURI, "complexType").getAttribute("mixed") == "false"):
                self._addError ("Attribute %s requires a simple or mixed type!" %repr(attrName), inputNode)
            else:
                typeNsName = xsdNode.getQNameAttribute (xsdTypeAttr)
                if typeNsName != (None, None):
                    self.simpleTypeVal.checkSimpleType (inputNode, attrName, typeNsName, attrValue, simpleTypeReturnDict, checkId)
                # TODO: What to check if no type is specified for the element?
                    if fixedValue != None:
                        self.simpleTypeVal.checkSimpleType (inputNode, attrName, typeNsName, fixedValue, fixedValueReturnDict, idCheck=0)
            
            xsdNode["BaseTypes"] = string.join (simpleTypeReturnDict["BaseTypes"], " ")
            xsdNode["primitiveType"] = str(simpleTypeReturnDict["primitiveType"])

            retValue = simpleTypeReturnDict
            if simpleTypeReturnDict.has_key("wsAction"):
                if checkAttribute:
                    attrValue = inputNode.processWsAttribute(attrName, simpleTypeReturnDict["wsAction"])
                else:
                    attrValue = inputNode.processWsElementValue(simpleTypeReturnDict["wsAction"])

            if fixedValue != None:
                if fixedValueReturnDict.has_key("orderedValue"):
                    fixedValue = fixedValueReturnDict["orderedValue"]
                elif fixedValueReturnDict.has_key("adaptedAttrValue"):
                    fixedValue = fixedValueReturnDict["adaptedAttrValue"]
                if simpleTypeReturnDict.has_key("orderedValue"):
                    attrValue = simpleTypeReturnDict["orderedValue"]
                if attrValue != fixedValue:
                    if checkAttribute:
                        self._addError ("Attribute %s must have fixed value %s!" %(repr(attrName), repr(fixedValue)), inputNode)
                    else:
                        self._addError ("Element must have fixed value %s!" %repr(fixedValue), inputNode)
                        
        except SimpleTypeError, errInst:
            self._addError (errInst.args[0], inputNode)

        return retValue

    ########################################
    # validate inputNode against sequence node
    #
    def _checkSequenceTag (self, xsdNode, inputParentNode, inputNodeList, currIndex):
        for xsdChildNode in xsdNode.getChildren():
            currIndex = self._checkParticle (xsdChildNode, inputParentNode, inputNodeList, currIndex)
        return currIndex


    ########################################
    # validate inputNode against choice node
    #
    def _checkChoiceTag (self, xsdNode, inputParentNode, inputNodeList, currIndex):
        childFound = 0
        exceptionRaised = 0
        for xsdChildNode in xsdNode.getChildren():
            try:
                newIndex = self._checkParticle (xsdChildNode, inputParentNode, inputNodeList, currIndex)
                if newIndex > currIndex:
                    currIndex = newIndex
                    childFound = 1
                    break
                else:
                    exceptionRaised = 0
            except TagException, errInst:
                exceptionRaised = 1
        else:
            if not childFound and exceptionRaised:
                if currIndex < len(inputNodeList):
                    currNode = inputNodeList[currIndex]
                    endTag = 0
                else:
                    currNode = inputParentNode
                    endTag = 1
                raise TagException ("No suitable child tag for choice found!", currNode, endTag)

        return currIndex


    ########################################
    # validate inputNode against group node
    #
    def _checkGroupTag (self, xsdNode, inputParentNode, inputNodeList, currIndex):
        if xsdNode.hasAttribute("ref"):
            refNsName = xsdNode.getQNameAttribute("ref")
            currIndex = self._checkGroupTag (self.xsdGroupDict[refNsName], inputParentNode, inputNodeList, currIndex)
        else:
            for xsdChildNode in xsdNode.getChildren():
                currIndex = self._checkParticle (xsdChildNode, inputParentNode, inputNodeList, currIndex)
        return currIndex


    ########################################
    # validate inputNode against all node
    #
    def _checkAllTag (self, xsdNode, inputParentNode, inputNodeList, currIndex):
        oldIndex = currIndex
        xsdChildDict = {}
        for xsdChildNode in xsdNode.getChildren():
            if xsdChildNode.getNsName() != (XSD_NAMESPACE, "annotation"):
                xsdChildDict[xsdChildNode] = 0
        while (currIndex < len(inputNodeList)) and (0 in xsdChildDict.values()):
            currNode = inputNodeList[currIndex]
            for xsdChildNode in xsdChildDict.keys():
                try:
                    newIndex = self._checkParticle (xsdChildNode, inputParentNode, inputNodeList, currIndex)
                    if newIndex == currIndex:
                        continue
                except TagException, errInst:
                    continue

                if xsdChildDict[xsdChildNode] == 0:
                    xsdChildDict[xsdChildNode] = 1
                    currIndex = newIndex
                    break
                else:
                    raise TagException ("Ambiguous child tag %s found in all-group!" %repr(currNode.getTagName()), currNode)
            else:
                raise TagException ("Unexpected child tag %s for all-group found!" %repr(currNode.getTagName()), currNode)

        for xsdChildNode, occurs in xsdChildDict.items():
            if xsdChildNode.getAttributeOrDefault("minOccurs", "1") != "0" and occurs == 0:
                raise TagException ("Child tag %s missing in all-group (%s)" %(repr(xsdChildNode.getAttribute("name")), repr(inputParentNode.getTagName())), inputParentNode)

        return currIndex


    ########################################
    # validate inputNode against any node
    #
    def _checkAnyTag (self, xsdNode, inputParentNode, inputNodeList, currIndex):
        if currIndex >= len (inputNodeList):
            raise TagException ("Missing child tag (anyTag) in tag %s!" %repr(inputParentNode.getTagName()), inputParentNode, 1)

        inputNode = inputNodeList[currIndex]
        inputNamespace = inputNode.getNamespaceURI()
        self._checkWildcardElement (xsdNode, inputNode, inputNamespace)

        currIndex = currIndex + 1
        return currIndex


    ########################################
    # validate inputNode against particle
    #
    def _checkParticle (self, xsdNode, inputParentNode, inputNodeList, currIndex):
        xsdTagName = xsdNode.getLocalName()
        if xsdTagName == "element":
            currIndex = self._checkList (self._checkElementTag, xsdNode, inputParentNode, inputNodeList, currIndex)
        elif xsdTagName == "choice":
            currIndex = self._checkList (self._checkChoiceTag, xsdNode, inputParentNode, inputNodeList, currIndex)
        elif xsdTagName == "sequence":
            currIndex = self._checkList (self._checkSequenceTag, xsdNode, inputParentNode, inputNodeList, currIndex)
        elif xsdTagName == "group":
            currIndex = self._checkList (self._checkGroupTag, xsdNode, inputParentNode, inputNodeList, currIndex)
        elif xsdTagName == "all":
            currIndex = self._checkList (self._checkAllTag, xsdNode, inputParentNode, inputNodeList, currIndex)
        elif xsdTagName == "any":
            currIndex = self._checkList (self._checkAnyTag, xsdNode, inputParentNode, inputNodeList, currIndex)
        elif xsdTagName == "annotation":
            # TODO: really nothing to check??
            pass
        else:
            self._addError ("Internal error: Invalid tag %s found!" %repr(xsdTagName))
        return currIndex


    ########################################
    # validate attributes of inputNode against complexType node
    #
    def _checkAttributeTags (self, parentNode, xsdNode, inputNode, validAttrDict):
        # retrieve all valid attributes for this element from the schema file
        self._updateAttributeDict (xsdNode, validAttrDict)
        inputAttrDict = {}
        for iAttrName, iAttrValue in inputNode.getAttributeDict().items():
            # skip namespace declarations
            if iAttrName[0] != XMLNS_NAMESPACE and iAttrName[1] != "xmlns":
                inputAttrDict[iAttrName] = iAttrValue

        for qAttrName, validAttrEntry in validAttrDict.items():
            attrRefNode = validAttrEntry["RefNode"]
            # global attributes use always form "qualified"
            if self.xsdAttributeDict.has_key(qAttrName) and self.xsdAttributeDict[qAttrName] == attrRefNode:
                attributeForm = "qualified"
            else:
                attributeForm = attrRefNode.getAttributeOrDefault ("form", self._getAttributeFormDefault(xsdNode))
            attrRefNode.setAttribute ("form", attributeForm)
            self._checkAttributeTag (qAttrName, validAttrEntry["Node"], attrRefNode, inputNode, inputAttrDict)

        for inputAttribute in inputAttrDict.keys():
            if inputAttribute == (XSI_NAMESPACE, "type"):
                pass # for attribute xsi:type refer _checkElementTag
            elif inputAttribute == (XSI_NAMESPACE, "nil"):
                if parentNode.getAttributeOrDefault ("nillable", "false") == "false":
                    self._addError ("Tag %s hasn't been defined as nillable!" %repr(inputNode.getTagName()), inputNode)
            elif inputNode == self.inputRoot and inputAttribute in ((XSI_NAMESPACE, "noNamespaceSchemaLocation"), (XSI_NAMESPACE, "schemaLocation")):
                pass
            elif validAttrDict.has_key("__ANY_ATTRIBUTE__"):
                xsdNode = validAttrDict["__ANY_ATTRIBUTE__"]["Node"]
                try:
                    inputNamespace = inputAttribute[0]
                    if inputAttribute[0] == None and xsdNode.getAttribute("form") == "unqualified":
                        # TODO: Check: If only local namespace is allowed, do not use target namespace???
                        if xsdNode.getAttribute("namespace") != "##local":
                            inputNamespace = self._getTargetNamespace(xsdNode)
                    self._checkWildcardAttribute (xsdNode, inputNode, inputAttribute, inputNamespace, inputAttrDict)
                except TagException:
                    self._addError ("Unexpected attribute %s in Tag %s!" %(repr(inputAttribute), repr(inputNode.getTagName())), inputNode)
            else:
                self._addError ("Unexpected attribute %s in Tag %s!" %(repr(inputAttribute), repr(inputNode.getTagName())), inputNode)


    ########################################
    # validate one attribute (defined by xsdNode) of inputNode
    #
    def _checkAttributeTag (self, qAttrName, xsdAttrNode, xsdAttrRefNode, inputNode, inputAttrDict):
        targetNamespace = self._getTargetNamespace(xsdAttrNode)
        if qAttrName[0] == targetNamespace and xsdAttrRefNode.getAttribute("form") == "unqualified":
            qAttrName = NsNameTupleFactory( (None, qAttrName[1]) )
        
        use = xsdAttrNode.getAttribute("use")
        if use == None: use = xsdAttrRefNode.getAttributeOrDefault ("use", "optional")
        fixedValue = xsdAttrNode.getAttribute("fixed")
        if fixedValue == None: 
            fixedValue = xsdAttrRefNode.getAttribute("fixed")

        if inputAttrDict.has_key(qAttrName):
            if use == "prohibited":
                self._addError ("Attribute %s is prohibited in this context!" %repr(qAttrName[1]), inputNode)
        elif inputAttrDict.has_key((targetNamespace, qAttrName[1])):
            self._addError ("Local attribute %s must be unqualified!" %(repr(qAttrName)), inputNode)
            del inputAttrDict[(targetNamespace, qAttrName[1])]
        elif inputAttrDict.has_key((None, qAttrName[1])) and qAttrName[0] == targetNamespace:
            self._addError ("Attribute %s must be qualified!" %repr(qAttrName[1]), inputNode)
            del inputAttrDict[(None, qAttrName[1])]
        else:
            if use == "required":
                self._addError ("Attribute %s is missing!" %(repr(qAttrName)), inputNode)
            elif use == "optional":
                if xsdAttrRefNode.hasAttribute("default"):
                    if not (inputNode.getNsName() == (XSD_NAMESPACE, "element") and
                            inputNode.hasAttribute("ref") and
                            xsdAttrRefNode.getAttribute("name") == "nillable"):
                        defaultValue = xsdAttrRefNode.getAttribute("default")
                        inputNode.setAttribute(qAttrName, defaultValue)
                        inputAttrDict[qAttrName] = defaultValue
                elif fixedValue != None:
                    inputNode.setAttribute(qAttrName, fixedValue)
                    inputAttrDict[qAttrName] = fixedValue

        if inputAttrDict.has_key(qAttrName):
            attributeValue = inputAttrDict[qAttrName]
            self._checkSimpleType (xsdAttrRefNode, "type", inputNode, qAttrName, attributeValue, fixedValue, 1)
            del inputAttrDict[qAttrName]
            inputNode.setXsdAttrNode(qAttrName, xsdAttrRefNode)


    ########################################
    # update dictionary of valid attributes
    #
    def _updateAttributeDict (self, xsdNode, validAttrDict, checkForDuplicateAttr=0, recursionKeys=None):
        # TODO: Why can recursionKeys not be initialized by default variable??
        if recursionKeys == None: recursionKeys = {} 
        validAttributeNodes = xsdNode.getChildrenNS(self.xsdNsURI, "attribute")
        for validAttrGroup in xsdNode.getChildrenNS(self.xsdNsURI, "attributeGroup"):
            refNsName = validAttrGroup.getQNameAttribute("ref")
            if self.xsdAttrGroupDict.has_key(refNsName):
                if recursionKeys.has_key(refNsName):
                    self._addError ("Circular definition for attribute group %s detected!" %(repr(refNsName)), validAttrGroup)
                    continue
                recursionKeys[refNsName] = 1
                self._updateAttributeDict(self.xsdAttrGroupDict[refNsName], validAttrDict, checkForDuplicateAttr, recursionKeys)
               

        for validAttributeNode in validAttributeNodes:
            if validAttributeNode.hasAttribute("ref"):
                attrKey = validAttributeNode.getQNameAttribute("ref")
                attributeRefNode = self.xsdAttributeDict[attrKey]
            else:
                attrKey = validAttributeNode.getQNameAttribute("name")
                attrKey = (self._getTargetNamespace(validAttributeNode), validAttributeNode.getAttribute("name"))
                attributeRefNode = validAttributeNode
                
            if checkForDuplicateAttr and validAttrDict.has_key(attrKey):
                self._addError ("Duplicate attribute %s found!" %repr(attrKey), validAttributeNode)
            else:
                validAttrDict[attrKey] = {"Node":validAttributeNode, "RefNode":attributeRefNode}

        anyAttributeNode = xsdNode.getFirstChildNS(self.xsdNsURI, "anyAttribute")
        if anyAttributeNode != None:
            validAttrDict["__ANY_ATTRIBUTE__"] = {"Node":anyAttributeNode, "RefNode":anyAttributeNode}


    ########################################
    # validate wildcard specification of anyElement
    #
    def _checkWildcardElement (self, xsdNode, inputNode, inputNamespace):
        processContents = xsdNode.getAttributeOrDefault("processContents", "lax")

        self._checkInputNamespace (xsdNode, inputNode, inputNamespace)

        inputNsName = inputNode.getNsName()
        if processContents == "skip":
            pass
        else:
            if inputNode.hasAttribute((XSI_NAMESPACE, "type")):
                # overloaded type is used
                typeNsName = inputNode.getQNameAttribute((XSI_NAMESPACE, "type"))
                if not self.xsdTypeDict.has_key(typeNsName):
                    self._addError ("Unknown overloaded type %s!" %(repr(typeNsName)), inputNode, 0)
                else:
                    typeType = self.xsdTypeDict[typeNsName].getLocalName()
                    if typeType == "complexType":
                        try:
                            self._checkComplexTypeTag (None, self.xsdTypeDict[typeNsName], inputNode, 0)
                        except TagException, errInst:
                            self._addError (errInst.errstr, errInst.node, errInst.endTag)
                    else:
                        simpleTypeReturnDict = {"BaseTypes":[], "primitiveType":None}
                        try:
                            self.simpleTypeVal.checkSimpleType (inputNode, inputNode.getLocalName(), typeNsName, inputNode.getElementValue(), simpleTypeReturnDict, idCheck=1)
                        except SimpleTypeError, errInst:
                            self._addError (errInst.args[0], inputNode)

            elif self.xsdElementDict.has_key(inputNsName):
                self._checkElementTag (self.xsdElementDict[inputNsName], None, (inputNode,), 0)

            elif processContents == "strict":
                self._addError ("Element definition %s not found in schema file!" %repr(inputNsName), inputNode)
                

    ########################################
    # validate wildcard specification of anyElement/anyAttribute
    #
    def _checkWildcardAttribute (self, xsdNode, inputNode, qAttrName, inputNamespace, inputAttrDict):
        processContents = xsdNode.getAttributeOrDefault("processContents", "strict")

        self._checkInputNamespace (xsdNode, inputNode, inputNamespace)

        if processContents == "skip":
            pass
        elif processContents == "lax":
            if self.xsdAttributeDict.has_key(qAttrName):
                attrNode = self.xsdAttributeDict[qAttrName]
                self._checkAttributeTag (qAttrName, attrNode, attrNode, inputNode, inputAttrDict)
        elif processContents == "strict":
            if self.xsdAttributeDict.has_key(qAttrName):
                attrNode = self.xsdAttributeDict[qAttrName]
                self._checkAttributeTag (qAttrName, attrNode, attrNode, inputNode, inputAttrDict)
            else:
                self._addError ("Attribute definition %s not found in schema file!" %repr(qAttrName), inputNode)
                

    ########################################
    # validate wildcard specification of anyElement/anyAttribute
    #
    def _checkInputNamespace (self, xsdNode, inputNode, inputNamespace):
        targetNamespace = self._getTargetNamespace(xsdNode)
        namespaces = xsdNode.getAttributeOrDefault("namespace", "##any")
        if namespaces == "##any":
            pass   # nothing to check
        elif namespaces == "##other":
            if inputNamespace == targetNamespace or inputNamespace == None:
                raise TagException ("Node or attribute must not be part of target namespace or local!", inputNode)
        else:
            for namespace in string.split(collapseString(namespaces), " "):
                if namespace == "##local" and inputNamespace == None:
                    break
                elif namespace == "##targetNamespace" and inputNamespace == targetNamespace:
                    break
                elif namespace == inputNamespace:
                    break
            else:
                raise TagException ("Node or attribute is not part of namespace %s!" %repr(namespaces), inputNode)


    ########################################
    # validate unique and key definition
    #
    def _checkIdentityConstraint (self, identityConstrNode, inputNode):
        identConstrTag = identityConstrNode.getLocalName()
        identConstrName = identityConstrNode.getAttribute ("name")
        identConstrNsLocalName = (self._getTargetNamespace(identityConstrNode), identConstrName)
        selectorXPathNode = identityConstrNode.getFirstChildNS (self.xsdNsURI, "selector")
        selectorNodeList, dummy, dummy = self._getXPath (inputNode, selectorXPathNode)
        
        valueDict = {}
        for selectorNode in selectorNodeList:
            fieldXPathNodeList = identityConstrNode.getChildrenNS (self.xsdNsURI, "field")
            keyValue = []
            baseTypesList = []
            for fieldXPathNode in fieldXPathNodeList:
                fieldChildList, attrNodeList, attrName = self._getXPath (selectorNode, fieldXPathNode, identConstrTag)
                if len(fieldChildList) > 1:
                    self._addError ("The field xPath %s of %s %s must evaluate to exactly 0 or 1 node!" %(repr(fieldXPathNode["xpath"]), repr(identConstrTag), repr(identConstrName)), selectorNode)
                    return

                for fieldChild in fieldChildList:
                    if attrNodeList == []:
                        inputChild = fieldChild
                        try:
                            baseTypes = self._setBaseTypes(fieldChild.getXsdNode())
                        except:
                            baseTypes = ((XSD_NAMESPACE, "anyType"),)
                        value = fieldChild.getElementValue()
                    else:
                        inputChild = attrNodeList[0]
                        try:
                            baseTypes = self._setBaseTypes(attrNodeList[0].getXsdAttrNode(attrName))
                        except:
                            baseTypes = ((XSD_NAMESPACE, "anyType"),)
                        value = fieldChild
                    if baseTypes != None:
                        if baseTypes[0] in ((XSD_NAMESPACE, "anyType"), (XSD_NAMESPACE, "anySimpleType")):
                            overloadedType = inputChild.getQNameAttribute((XSI_NAMESPACE, "type"))
                            if overloadedType != (None, None):
                                baseTypes = [inputChild.getQNameAttribute((XSI_NAMESPACE, "type")),]
                    else:
                        self._addError ("Identity constraint does not have a simple type!", inputChild)
                        continue
                        
                    baseTypesList.append(baseTypes)
                    for baseType in baseTypes:
                        try:
                            value = self._getOrderedValue (inputChild, attrName, baseType, value)
                            break
                        except SimpleTypeError, errInst:
                            pass
                    keyValue.append (value)

            if keyValue != []:
                keyValue = tuple(keyValue)
                if not valueDict.has_key (keyValue):
                    valueDict[keyValue] = 1
                    self.xsdIdentityConstrDict[identConstrNsLocalName]["ValueDict"][keyValue] = baseTypesList
                else:
                    if len(keyValue) == 1:
                        self._addError ("Duplicate identity constraint values %s found for identity contraint %s!" %(repr(keyValue[0]), repr(identConstrName)), selectorNode)
                    else:
                        self._addError ("Duplicate identity constraint values %s found for identity contraint %s!" %(repr(keyValue), repr(identConstrName)), selectorNode)

    ########################################
    # validate unique and key definition
    #
    def _checkKeyRefConstraint (self, keyrefNode, inputNode):
        keyRefName = keyrefNode.getAttribute ("name")
        keyReference = keyrefNode.getQNameAttribute ("refer")

        selectorXPathNode = keyrefNode.getFirstChildNS (self.xsdNsURI, "selector")
        selectorNodeList, dummy, dummy = self._getXPath (inputNode, selectorXPathNode)
        for selectorNode in selectorNodeList:
            fieldXPathNodeList = keyrefNode.getChildrenNS(self.xsdNsURI, "field")
            keyValue = []
            for fieldXPathNode in fieldXPathNodeList:
                fieldChildList, attrNodeList, attrName = self._getXPath (selectorNode, fieldXPathNode, "keyref")
                if len(fieldChildList) > 1:
                    self._addError ("The field xPath of keyref %s must evaluate to exactly 0 or 1 node!" %repr(keyRefName), fieldXPathNode)
                    return

                for fieldChild in fieldChildList:
                    if attrNodeList == []:
                        inputChild = fieldChild
                        baseTypes = self._setBaseTypes(fieldChild.getXsdNode())
                        value = fieldChild.getElementValue()
                    else:
                        inputChild = attrNodeList[0]
                        baseTypes = self._setBaseTypes(attrNodeList[0].getXsdAttrNode(attrName))
                        value = fieldChild

                    if baseTypes != None:
                        for baseType in baseTypes:
                            try:
                                value = self._getOrderedValue (inputChild, attrName, baseType, value)
                                break
                            except SimpleTypeError, errInst:
                                pass
                    keyValue.append (value)

            keyValue = tuple(keyValue)
            if keyValue != ():
                if not self.xsdIdentityConstrDict[keyReference]["ValueDict"].has_key (keyValue):
                    self._addError ("Key reference value %s is undefined for key type %s!" %(repr(keyValue), repr(keyReference)), selectorNode)
                else:
                    baseTypesList = self.xsdIdentityConstrDict[keyReference]["ValueDict"][keyValue]
                    for fieldXPathNode, baseTypes in zip(fieldXPathNodeList, baseTypesList):
                        fieldChildList, attrNodeList, attrName = self._getXPath (selectorNode, fieldXPathNode, "keyref")
                        if attrNodeList == []:
                            inputChild = fieldChildList[0]
                            refBaseTypes = self._setBaseTypes(fieldChildList[0].getXsdNode())
                        else:
                            inputChild = attrNodeList[0]
                            refBaseTypes = self._setBaseTypes(inputChild.getXsdAttrNode(attrName))
                        if baseTypes[0] not in refBaseTypes and refBaseTypes[0] not in baseTypes:
                            if baseTypes[0] != (XSD_NAMESPACE, "anyType") and refBaseTypes[0] != (XSD_NAMESPACE, "anyType"):
                                self._addError ("Key type and key reference type does not match (%s != %s)!" %(repr(baseTypes[0]), repr(refBaseTypes[0])), inputChild)
                    
    
    ########################################
    # check input element form
    #
    def _checkInputElementForm (self, xsdNode, xsdNodeNameAttr, inputNode):
        targetNamespace = self._getTargetNamespace(xsdNode)
        nsNameAttr = (targetNamespace, xsdNodeNameAttr)
        if self.xsdElementDict.has_key(nsNameAttr) and self.xsdElementDict[nsNameAttr] == xsdNode:
            elementForm = "qualified"
        else:
            elementForm = xsdNode.getAttributeOrDefault ("form", self._getElementFormDefault(xsdNode))
        if elementForm == "qualified":
            if inputNode.getNamespaceURI() == None:
                if targetNamespace != None:
                    self._addError ("Element %s must be qualified!" %repr(xsdNodeNameAttr), inputNode)
            elif inputNode.getNamespaceURI() != targetNamespace:
                self._addError ("%s undefined in specified namespace!" %repr(xsdNodeNameAttr), inputNode)
        elif elementForm == "unqualified" and inputNode.getNamespaceURI() != None:
            self._addError ("Local element %s must be unqualified!" %repr(xsdNodeNameAttr), inputNode)


    ########################################
    # retrieve ordered value and base types of given typeNsName
    #
    def _getOrderedValue (self, inputNode, attrName, typeNsName, attrValue):
        simpleTypeReturnDict = {"BaseTypes":[], "primitiveType":None}
        self.simpleTypeVal.checkSimpleType (inputNode, attrName, typeNsName, attrValue, simpleTypeReturnDict, idCheck=1)
        if simpleTypeReturnDict.has_key("orderedValue"):
            attrValue = simpleTypeReturnDict["orderedValue"]
        return attrValue


    ########################################
    # retrieve nodes/attributes specified by given xPath
    #
    def _getXPath (self, node, xPathNode, identityConstraint=None):
        xPath = xPathNode.getAttribute("xpath")
        try:
            attrIgnoreList = [(XSI_NAMESPACE, "nil")]
            childList, attrNodeList, attrName = node.getXPathList (xPath, namespaceRef=xPathNode, useDefaultNs=0, attrIgnoreList=attrIgnoreList)
        except Exception, errInst:
            self._addError (errInst.args, node)
            childList = []
            attrNodeList = []
            attrName = None

        if childList == []:
            if identityConstraint == "key":
                self.errorHandler.addError ("Key is missing! XPath = %s!" %repr(xPath), node)
            elif identityConstraint in ("unique", "keyref"):
                self.errorHandler.addWarning ("Identity constraint is missing! XPath = %s!" %repr(xPath), node)
        return childList, attrNodeList, attrName


    ########################################
    # retrieve basetypes from XML attribute (string format)
    #
    def _setBaseTypes (self, xsdNode):
        if xsdNode.getAttribute("BaseTypes") != None:
            baseTypes = string.split(xsdNode["BaseTypes"])
            baseTypeList = map (lambda basetype: NsNameTupleFactory(basetype), baseTypes)
            if baseTypeList != []:
                return baseTypeList
            else:
                return None
        else:
            return None
    
    ########################################
    # retrieve target namespace attribute for given node
    #
    def _getTargetNamespace(self, node):
        schemaRootNode = node.getSchemaRootNode()
        return schemaRootNode.getAttribute("targetNamespace")


    ########################################
    # retrieve element form default attribute for given node
    #
    def _getElementFormDefault(self, node):
        schemaRootNode = node.getSchemaRootNode()
        return schemaRootNode.getAttributeOrDefault("elementFormDefault", "unqualified")

    ########################################
    # retrieve element form default attribute for given node
    #
    def _getAttributeFormDefault(self, node):
        schemaRootNode = node.getSchemaRootNode()
        return schemaRootNode.getAttributeOrDefault("attributeFormDefault", "unqualified")


########################################
# define own exception for XML schema validation errors
#
class TagException (StandardError):
    def __init__ (self, errstr="", node=None, endTag=0):
        self.node   = node
        self.errstr = errstr
        self.endTag = endTag
        StandardError.__init__(self)


########NEW FILE########
__FILENAME__ = xsvalErrorHandler
#
# minixsv, Release 0.9.0
# file: xsvalErrorHandler.py
#
# XML schema validator classes
#
# history:
# 2004-09-23 rl   created
#
# Copyright (c) 2004-2008 by Roland Leuthe.  All rights reserved.
#
# --------------------------------------------------------------------
# The minixsv XML schema validator is
#
# Copyright (c) 2004-2008 by Roland Leuthe
#
# By obtaining, using, and/or copying this software and/or its
# associated documentation, you agree that you have read, understood,
# and will comply with the following terms and conditions:
#
# Permission to use, copy, modify, and distribute this software and
# its associated documentation for any purpose and without fee is
# hereby granted, provided that the above copyright notice appears in
# all copies, and that both that copyright notice and this permission
# notice appear in supporting documentation, and that the name of
# the author not be used in advertising or publicity
# pertaining to distribution of the software without specific, written
# prior permission.
#
# THE AUTHOR DISCLAIMS ALL WARRANTIES WITH REGARD
# TO THIS SOFTWARE, INCLUDING ALL IMPLIED WARRANTIES OF MERCHANT-
# ABILITY AND FITNESS.  IN NO EVENT SHALL THE AUTHOR
# BE LIABLE FOR ANY SPECIAL, INDIRECT OR CONSEQUENTIAL DAMAGES OR ANY
# DAMAGES WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS,
# WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS
# ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR PERFORMANCE
# OF THIS SOFTWARE.
# --------------------------------------------------------------------

import string
import os

IGNORE_WARNINGS   = 0
PRINT_WARNINGS    = 1
STOP_ON_WARNINGS  = 2


########################################
# Error-Handler class for XML schema validator
# handles only validator errors, no parser errors!

class ErrorHandler:

    def __init__(self, errorLimit, warningProc, verbose):
        self.errorLimit  = errorLimit
        self.warningProc = warningProc
        self.verbose     = verbose
        
        self.errorList = []
        self.noOfErrors = 0
        self.warningList = []
        self.infoDict = {}


    ########################################
    # check if errors have already been reported

    def hasErrors (self):
        return self.errorList != []

    ########################################
    # add error to errorList (raise exception only if error limit is reached)

    def addError (self, errstr, element=None, endTag=0):
        filePath = ""
        lineNo = 0
        if element:
            filePath = element.getFilePath()
            if endTag:
                lineNo = element.getEndLineNumber()
            else:
                lineNo = element.getStartLineNumber()
        self.errorList.append ((filePath, lineNo, "ERROR", "%s" %errstr))
        self.noOfErrors += 1
        if self.noOfErrors == self.errorLimit:
            self._raiseXsvalException ("\nError Limit reached!!")


    ########################################
    # add warning to warningList

    def addWarning (self, warnstr, element=None):
        filePath = ""
        lineNo = 0
        if element:
            filePath = element.getFilePath()
            lineNo = element.getStartLineNumber()
        self.warningList.append ((filePath, lineNo, "WARNING", warnstr))


    ########################################
    # add info string to errorList

    def addInfo (self, infostr, element=None):
        self.infoDict.setdefault("INFO: %s" %infostr, 1)


    ########################################
    # add error to errorList (if given) and raise exception

    def raiseError (self, errstr, element=None):
        self.addError (errstr, element)
        self._raiseXsvalException ()


    ########################################
    # raise exception with complete errorList as exception string
    # (only if errors occurred)

    def flushOutput (self):
        if self.infoDict != {}:
            print string.join (self.infoDict.keys(), "\n")
            self.infoList = []

        if self.warningProc == PRINT_WARNINGS and self.warningList != []:
            print self._assembleOutputList(self.warningList, sorted=1)
            self.warningList = []
        elif self.warningProc == STOP_ON_WARNINGS:
            self.errorList.extend (self.warningList)

        if self.errorList != []:
            self._raiseXsvalException ()


    ########################################
    # Private methods

    def _raiseXsvalException (self, additionalInfo=""):
        output = self._assembleOutputList(self.errorList) + additionalInfo
        self.errorList = self.warningList = []
        raise XsvalError (output)


    def _assembleOutputList (self, outputList, sorted=0):
        if sorted:
            outputList.sort()
        outputStrList = []
        for outElement in outputList:
            outputStrList.append (self._assembleOutString(outElement))
        return string.join (outputStrList, "\n")
        
        
    def _assembleOutString (self, listElement):
        fileStr = ""
        lineStr = ""
        if listElement[0] != "":
            if self.verbose:
                fileStr = "%s: " %(listElement[0])
            else:
                fileStr = "%s: " %(os.path.basename(listElement[0]))
        if listElement[1] != 0:
            lineStr = "line %d: " %(listElement[1])
        return "%s: %s%s%s" %(listElement[2], fileStr, lineStr, listElement[3])
    

class XsvalError (StandardError):
    pass


########NEW FILE########
__FILENAME__ = xsvalSchema
#
# minixsv, Release 0.9.0
# file: xsvalSchema.py
#
# Derived validator class (for validation of schema files)
#
# history:
# 2004-10-07 rl   created
# 2006-08-18 rl   W3C testsuite passed for supported features
# 2007-05-24 rl   Features for release 0.8 added, several bugs fixed
#
# Copyright (c) 2004-2008 by Roland Leuthe.  All rights reserved.
#
# --------------------------------------------------------------------
# The minixsv XML schema validator is
#
# Copyright (c) 2004-2008 by Roland Leuthe
#
# By obtaining, using, and/or copying this software and/or its
# associated documentation, you agree that you have read, understood,
# and will comply with the following terms and conditions:
#
# Permission to use, copy, modify, and distribute this software and
# its associated documentation for any purpose and without fee is
# hereby granted, provided that the above copyright notice appears in
# all copies, and that both that copyright notice and this permission
# notice appear in supporting documentation, and that the name of
# the author not be used in advertising or publicity
# pertaining to distribution of the software without specific, written
# prior permission.
#
# THE AUTHOR DISCLAIMS ALL WARRANTIES WITH REGARD
# TO THIS SOFTWARE, INCLUDING ALL IMPLIED WARRANTIES OF MERCHANT-
# ABILITY AND FITNESS.  IN NO EVENT SHALL THE AUTHOR
# BE LIABLE FOR ANY SPECIAL, INDIRECT OR CONSEQUENTIAL DAMAGES OR ANY
# DAMAGES WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS,
# WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS
# ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR PERFORMANCE
# OF THIS SOFTWARE.
# --------------------------------------------------------------------


import string
import re
import os
from decimal             import Decimal
from ..genxmlif.xmlifUtils import collapseString
from ..minixsv             import *
from xsvalBase           import XsValBase, TagException
from xsvalUtils          import substituteSpecialEscChars

_localFacetDict = {(XSD_NAMESPACE,"list"): ("length", "minLength", "maxLength", "enumeration", "pattern", "whiteSpace"),
                   (XSD_NAMESPACE,"union"): ("enumeration", "pattern", "whiteSpace"),
                   (XSD_NAMESPACE,"anySimpleType"): ("whiteSpace"),}
###########################################################
#  Derived validator class for validating one input schema file against the XML rules file

class XsValSchema (XsValBase):

    ########################################
    # overloaded validate method
    #
    def validate (self, inputTree, xsdTree):
        XsValBase.validate(self, inputTree, xsdTree)
    
        self._initInternalAttributes (self.inputRoot)
        self._updateLookupTables (self.inputRoot, self.xsdLookupDict)

        self._includeAndImport (self.inputTree, self.inputTree, self.xsdIncludeDict, self.xsdLookupDict)

        if not self.errorHandler.hasErrors():
            # IDs must be unique within a schema file
            self.xsdIdDict = {}

            self._checkSchemaSecondLevel()

        # FIXME: Wellknown schemas are not included in the input tree although the internal attribute has been set!
        #        Better solution required than this workaround!
        self.inputRoot["__WellknownSchemasImported__"] = "false"


    ########################################
    # additional checks for schema files which are not covered by "xsStructs.xsd"
    #
    def _checkSchemaSecondLevel(self):

        targetNamespace = self.inputRoot.getAttribute("targetNamespace")
        if targetNamespace == "":
            self.errorHandler.raiseError("Empty string not allowed for target namespace!", self.inputRoot)

        self._checkElementNodesSecondLevel()
        self._checkNotationNodesSecondLevel()
        self._checkAnyNodesSecondLevel()
        self._checkGroupNodesSecondLevel()
        self._checkAttrGroupNodesSecondLevel()
        self._checkAttributeNodesSecondLevel()
        self._checkAnyAttributesSecondLevel()

        if self.errorHandler.hasErrors():
            return

        self._checkComplexTypesSecondLevel()
        self._checkSimpleTypesSecondLevel()

        self._checkParticlesSecondLevel()

        self._checkIdentityConstraintsSecondLevel()
        self._checkKeysSecondLevel()
        self._checkKeyRefsSecondLevel()

    ########################################
    # additional checks for element nodes
    #
    def _checkElementNodesSecondLevel(self):
        elementNodes = self.inputRoot.getElementsByTagNameNS (self.inputNsURI, "element")
        for elementNode in elementNodes:
            if not elementNode.hasAttribute("name") and not elementNode.hasAttribute("ref"):
                self._addError ("Element must have 'name' or 'ref' attribute!", elementNode)
                continue

            if elementNode.hasAttribute("ref"):
                for attrName in ("name", "type", "form"):
                    if elementNode.hasAttribute(attrName):
                        self._addError ("Element with 'ref' attribute must not have %s attribute!" %repr(attrName), elementNode)
                        continue

            complexTypeNode = elementNode.getFirstChildNS (self.inputNsURI, "complexType")
            simpleTypeNode = elementNode.getFirstChildNS (self.inputNsURI, "simpleType")
            if elementNode.hasAttribute("ref") and (complexTypeNode != None or simpleTypeNode != None):
                self._addError ("Element with 'ref' attribute must not have type definition!", elementNode)
                continue
            if elementNode.hasAttribute("type") and (complexTypeNode != None or simpleTypeNode != None):
                self._addError ("Element with 'type' attribute must not have type definition!", elementNode)
                continue
            
            if elementNode.hasAttribute("ref"):
                for forbiddenAttr in ("block", "nillable", "default", "fixed"):
                    if elementNode.hasAttribute(forbiddenAttr):
                        self._addError ("Element with 'ref' attribute must not have %s attribute!" %repr(forbiddenAttr), elementNode)

                self._checkReference (elementNode, self.xsdElementDict)

            if elementNode.hasAttribute("type"):
                self._checkType (elementNode, "type", self.xsdTypeDict)

            self._checkNodeId(elementNode)
            self._checkOccurs (elementNode)
            self._checkFixedDefault(elementNode)


    ########################################
    # additional checks for notation nodes
    #
    def _checkNotationNodesSecondLevel(self):
        notationNodes = self.inputRoot.getElementsByTagNameNS (self.inputNsURI, "notation")
        for notationNode in notationNodes:
            if not notationNode.hasAttribute("public") and not notationNode.hasAttribute("system"):
                self._addError ("Notation must have 'public' or 'system' attribute!", notationNode)
    
    
    ########################################
    # additional checks for anyNodes
    #
    def _checkAnyNodesSecondLevel(self):
        anyNodes = self.inputRoot.getElementsByTagNameNS (self.inputNsURI, "any")
        for anyNode in anyNodes:
            self._checkOccurs (anyNode)
            # check for unique ID
            self._checkNodeId (anyNode)


    ########################################
    # additional checks for group nodes
    #
    def _checkGroupNodesSecondLevel(self):
        groupNodes = self.inputRoot.getElementsByTagNameNS (self.inputNsURI, "group")
        for groupNode in groupNodes:
            self._checkNodeId(groupNode)
            if groupNode.hasAttribute("ref"):
                self._checkReference (groupNode, self.xsdGroupDict)
                self._checkOccurs (groupNode)
        if self.errorHandler.hasErrors():
            return
#        for groupNode in groupNodes:
#            if groupNode.hasAttribute("name"):
#                self._checkGroupNodeCircularDef(groupNode, {groupNode["name"]:1})
    
    def _checkGroupNodeCircularDef(self, groupNode, groupNameDict):
        childGroupsRefNodes, dummy, dummy = groupNode.getXPathList (".//%sgroup" %(self.inputNsPrefixString))
        for childGroupRefNode in childGroupsRefNodes:
            if childGroupRefNode.hasAttribute("ref"):
                childGroupNode = self.xsdGroupDict[childGroupRefNode.getQNameAttribute("ref")]
                if not groupNameDict.has_key(childGroupNode["name"]):
                    groupNameDict[childGroupNode["name"]] = 1
                    self._checkGroupNodeCircularDef(childGroupNode, groupNameDict)
                else:
                    self._addError ("Circular definition of group %s!" %repr(childGroupNode["name"]), childGroupNode)
                

    ########################################
    # additional checks for attributeGroup nodes
    #
    def _checkAttrGroupNodesSecondLevel(self):
        attributeGroupNodes = self.inputRoot.getElementsByTagNameNS (self.inputNsURI, "attributeGroup")
        for attributeGroupNode in attributeGroupNodes:
            if attributeGroupNode.hasAttribute("ref"):
                self._checkReference (attributeGroupNode, self.xsdAttrGroupDict)

            self._checkNodeId(attributeGroupNode)

    ########################################
    # additional checks for attribute nodes
    #
    def _checkAttributeNodesSecondLevel(self):
        attributeNodes = self.inputRoot.getElementsByTagNameNS (XSD_NAMESPACE, "attribute")
        for attributeNode in attributeNodes:
            if os.path.basename(attributeNode.getFilePath()) != "XMLSchema-instance.xsd":
                # global attributes must always be "qualified"
                if (attributeNode.getParentNode() == self.inputRoot or
                    self._getAttributeFormDefault(attributeNode) == "qualified"):
                    if self._getTargetNamespace(attributeNode) == XSI_NAMESPACE:
                        self._addError ("Target namespace of an attribute must not match '%s'!" %XSI_NAMESPACE, attributeNode)
                
            if not attributeNode.hasAttribute("name") and not attributeNode.hasAttribute("ref"):
                self._addError ("Attribute must have 'name' or 'ref' attribute!", attributeNode)
                continue

            if attributeNode.getAttribute("name") == "xmlns":
                self._addError ("Attribute must not match 'xmlns'!", attributeNode)

            if attributeNode.hasAttribute("ref"):
                if attributeNode.hasAttribute("name"):
                    self._addError ("Attribute may have 'name' OR 'ref' attribute!", attributeNode)
                if attributeNode.hasAttribute("type"):
                    self._addError ("Attribute may have 'type' OR 'ref' attribute!", attributeNode)
                if attributeNode.hasAttribute("form"):
                    self._addError ("Attribute 'form' is not allowed in this context!", attributeNode)

                if attributeNode.getFirstChildNS(XSD_NAMESPACE, "simpleType") != None:
                    self._addError ("Attribute may only have 'ref' attribute OR 'simpleType' child!", attributeNode)
                
                self._checkReference (attributeNode, self.xsdAttributeDict)

            if attributeNode.hasAttribute("type"):
                if attributeNode.getFirstChildNS(XSD_NAMESPACE, "simpleType") != None:
                    self._addError ("Attribute may only have 'type' attribute OR 'simpleType' child!", attributeNode)

                self._checkType (attributeNode, "type", self.xsdTypeDict, (XSD_NAMESPACE, "simpleType"))

            use = attributeNode.getAttribute("use")
            if use in ("required", "prohibited") and attributeNode.hasAttribute("default"):
                self._addError ("Attribute 'default' is not allowed, because 'use' is '%s'!" %(use), attributeNode)

            self._checkNodeId(attributeNode, unambiguousPerFile=0)

            self._checkFixedDefault(attributeNode)


    ########################################
    # additional checks for attribute wildcards
    #
    def _checkAnyAttributesSecondLevel(self):
        anyAttributeNodes, dummy, dummy = self.inputRoot.getXPathList (".//%sanyAttribute" %(self.inputNsPrefixString))
        for anyAttributeNode in anyAttributeNodes:
            # check for unique ID
            self._checkNodeId (anyAttributeNode)


    ########################################
    # additional checks for complex types
    #
    def _checkComplexTypesSecondLevel(self):
        prefix = self.inputNsPrefixString
        contentNodes, dummy, dummy = self.inputRoot.getXPathList (".//%(prefix)scomplexContent/%(prefix)srestriction | .//%(prefix)scomplexContent/%(prefix)sextension" % vars())
        for contentNode in contentNodes:
            self._checkType(contentNode, "base", self.xsdTypeDict, (XSD_NAMESPACE, "complexType"))

        contentNodes, dummy, dummy = self.inputRoot.getXPathList (".//%(prefix)ssimpleContent/%(prefix)srestriction | .//%(prefix)ssimpleContent/%(prefix)sextension" % vars())
        for contentNode in contentNodes:
            baseNsName = contentNode.getQNameAttribute("base")
            if baseNsName != (XSD_NAMESPACE, "anyType"):
                typeNsName = contentNode.getParentNode().getNsName()
                self._checkBaseType(contentNode, baseNsName, self.xsdTypeDict, typeNsName)
            else:
                self._addError ("Referred type must not be 'anyType'!", contentNode)
            # check for unique ID
            self._checkNodeId (contentNode)

        complexTypeNodes, dummy, dummy = self.inputRoot.getXPathList (".//%(prefix)scomplexType | .//%(prefix)sextension" % vars())
        for complexTypeNode in complexTypeNodes:
            validAttrDict = {}
            # check for duplicate attributes
            self._updateAttributeDict (complexTypeNode, validAttrDict, 1)
            # check for duplicate ID attributes
            idAttrNode = None
            for key, val in validAttrDict.items():
                attrType = val["RefNode"].getQNameAttribute("type")
                if attrType == (XSD_NAMESPACE, "ID"):
                    if not idAttrNode:
                        idAttrNode = val["Node"]
                    else:
                        # TODO: check also if attribute has a type which is derived from ID!
                        self._addError ("Two attribute declarations of complex type are IDs!", val["Node"])
                        
            # check for unique ID
            self._checkNodeId (complexTypeNode)

        contentNodes, dummy, dummy = self.inputRoot.getXPathList (".//%(prefix)scomplexType/%(prefix)s*" % vars())
        for contentNode in contentNodes:
            self._checkOccurs (contentNode)

        contentNodes, dummy, dummy = self.inputRoot.getXPathList (".//%(prefix)scomplexContent | .//%(prefix)ssimpleContent" % vars())
        for contentNode in contentNodes:
            # check for unique ID
            self._checkNodeId (contentNode)


    ########################################
    # additional checks for simple types
    #
    def _checkParticlesSecondLevel(self):
        prefix = self.inputNsPrefixString
        # check for duplicate element names
        particleNodes, dummy, dummy = self.inputRoot.getXPathList (".//%(prefix)sall | .//%(prefix)schoice | .//%(prefix)ssequence" % vars())
        for particleNode in particleNodes:
            elementTypeDict = {}
            elementNameDict = {}
            groupNameDict = {}
            self._checkContainedElements (particleNode, particleNode.getLocalName(), elementNameDict, elementTypeDict, groupNameDict)
            self._checkOccurs (particleNode)
            # check for unique ID
            self._checkNodeId (particleNode)
                

    def _checkContainedElements (self, node, particleType, elementNameDict, elementTypeDict, groupNameDict):
        prefix = self.inputNsPrefixString
        for childNode in node.getChildren():
            childParticleType = childNode.getLocalName()
            if childParticleType in ("sequence", "choice", "all"):
                dummy = {}
                self._checkContainedElements (childNode, childParticleType, dummy, elementTypeDict, groupNameDict)
            elif childParticleType in ("group"):
                if childNode["ref"] != None:
                    childGroupNode = self.xsdGroupDict[childNode.getQNameAttribute("ref")]
                    if not groupNameDict.has_key(childGroupNode["name"]):
                        groupNameDict[childGroupNode["name"]] = 1
                        for cChildNode in childGroupNode.getChildren():
                            if cChildNode.getLocalName() != "annotation":
                                self._checkContainedElements (cChildNode, particleType, elementNameDict, elementTypeDict, groupNameDict)
                    else:
                        self._addError ("Circular definition of group %s!" %repr(childGroupNode["name"]), childNode)
                else:
                    for cChildNode in childNode.getChildren():
                        if cChildNode.getLocalName() != "annotation":
                            self._checkContainedElements (cChildNode, particleType, elementNameDict, elementTypeDict, groupNameDict)
            else:
                if childNode.getLocalName() == "any":
                    elementName = childNode.getAttribute("namespace")
                else:
                    elementName = childNode.getAttributeOrDefault("name", childNode.getAttribute("ref"))

                if childNode.hasAttribute("type"):
                    if not elementTypeDict.has_key(elementName):
                        elementTypeDict[elementName] = childNode["type"]
                    elif childNode["type"] != elementTypeDict[elementName]:
                        self._addError ("Element %s has identical name and different types within %s!" %(repr(elementName), repr(particleType)), childNode)
                if particleType != "sequence":
                    if not elementNameDict.has_key(elementName):
                        elementNameDict[elementName] = 1
                    else:
                        self._addError ("Element %s is not unique within %s!" %(repr(elementName), repr(particleType)), childNode)


    ########################################
    # additional checks for simple types
    #
    def _checkSimpleTypesSecondLevel(self):
        prefix = self.inputNsPrefixString

        simpleTypeNodes, dummy, dummy = self.inputRoot.getXPathList (".//%(prefix)ssimpleType" % vars())
        for simpleTypeNode in simpleTypeNodes:
            # check for unique ID
            self._checkNodeId (simpleTypeNode)
        
        restrictionNodes, dummy, dummy = self.inputRoot.getXPathList (".//%(prefix)ssimpleType/%(prefix)srestriction" % vars())
        for restrictionNode in restrictionNodes:

            # check for unique ID
            self._checkNodeId (restrictionNode)

            if not restrictionNode.hasAttribute("base") and restrictionNode.getFirstChildNS (self.inputNsURI, "simpleType") == None:
                self._addError ("Simple type restriction must have 'base' attribute or 'simpleType' child tag!", restrictionNode)

            if restrictionNode.hasAttribute("base") and restrictionNode.getFirstChildNS (self.inputNsURI, "simpleType") != None:
                self._addError ("Simple type restriction must not have 'base' attribute and 'simpleType' child tag!", restrictionNode)

            if restrictionNode.hasAttribute("base"):
                self._checkType(restrictionNode, "base", self.xsdTypeDict)

            minExcl = restrictionNode.getFirstChildNS(self.inputNsURI, "minExclusive")
            minIncl = restrictionNode.getFirstChildNS(self.inputNsURI, "minInclusive")
            if minExcl != None and minIncl != None:
                self._addError ("Restriction attributes 'minExclusive' and 'minInclusive' cannot be defined together!", restrictionNode)
            maxExcl = restrictionNode.getFirstChildNS(self.inputNsURI, "maxExclusive")
            maxIncl = restrictionNode.getFirstChildNS(self.inputNsURI, "maxInclusive")
            if maxExcl != None and maxIncl != None:
                self._addError ("Restriction attributes 'maxExclusive' and 'maxInclusive' cannot be defined together!", restrictionNode)

        # check facets of associated primitive type
        for restrictionNode in restrictionNodes:
            try:
                if restrictionNode.hasAttribute("base"):
                    facetNsName = self._getFacetType (restrictionNode, [restrictionNode.getParentNode(),], self.xsdTypeDict)
                    if not facetNsName:
                        continue
                    if _localFacetDict.has_key(facetNsName):
                        suppFacets = _localFacetDict[facetNsName]
                    else:
                        suppFacets, dummy, dummy = self.xsdTypeDict[facetNsName].getXPathList (".//hfp:hasFacet/@name" % vars())

                    specifiedFacets = {"length":None, "minLength":None, "maxLength":None,
                                       "minExclusive":None, "minInclusive":None, "maxExclusive":None, "maxInclusive":None,
                                       "totalDigits": None, "fractionDigits":None}
                    for childNode in restrictionNode.getChildren():
                        if childNode.getLocalName() in suppFacets:
                            if specifiedFacets.has_key(childNode.getLocalName()):
                                specifiedFacets[childNode.getLocalName()] = childNode["value"]
                            facetElementNode = self.xsdElementDict[childNode.getNsName()]
                            try:
                                self._checkElementTag (facetElementNode, restrictionNode, (childNode,), 0)
                            except TagException, errInst:
                                self._addError (errInst.errstr, errInst.node, errInst.endTag)
                            if childNode.getLocalName() in ("enumeration", "minExclusive", "minInclusive", "maxExclusive", "maxInclusive"):
                                simpleTypeReturnDict = self._checkSimpleType (restrictionNode, "base", childNode, "value", childNode["value"], None, checkAttribute=1)
                                if simpleTypeReturnDict != None and simpleTypeReturnDict.has_key("orderedValue"):
                                    if childNode.getLocalName() != "enumeration":
                                        specifiedFacets[childNode.getLocalName()] = simpleTypeReturnDict["orderedValue"]
                        elif childNode.getLocalName() == "enumeration":
                            self._checkSimpleType (restrictionNode, "base", childNode, "value", childNode["value"], None, checkAttribute=1)
                        elif childNode.getLocalName() != "annotation":
                            self._addError ("Facet %s not allowed for base type %s!" %(childNode.getLocalName(), repr(restrictionNode["base"])), childNode)
                    if specifiedFacets["length"] != None:
                        if specifiedFacets["minLength"] != None or specifiedFacets["maxLength"] != None:
                            self._addError ("Facet 'minLength' and 'maxLength' not allowed if facet 'length' is specified!", restrictionNode)
                    else:
                        if specifiedFacets["maxLength"] != None and specifiedFacets["minLength"] != None:
                            if int(specifiedFacets["maxLength"]) < int(specifiedFacets["minLength"]):
                                self._addError ("Facet 'maxLength' < facet 'minLength'!", restrictionNode)

                    if specifiedFacets["totalDigits"] != None and specifiedFacets["fractionDigits"] != None:
                        if int(specifiedFacets["totalDigits"]) < int(specifiedFacets["fractionDigits"]):
                            self._addError ("Facet 'totalDigits' must be >= 'fractionDigits'!", restrictionNode)

                    if specifiedFacets["minExclusive"] != None and specifiedFacets["minInclusive"] != None:
                        self._addError ("Facets 'minExclusive' and 'minInclusive' are mutually exclusive!", restrictionNode)
                    if specifiedFacets["maxExclusive"] != None and specifiedFacets["maxInclusive"] != None:
                        self._addError ("Facets 'maxExclusive' and 'maxInclusive' are mutually exclusive!", restrictionNode)

                    minValue = specifiedFacets["minExclusive"]
                    if specifiedFacets["minInclusive"] != None:
                        minValue = specifiedFacets["minInclusive"]
                    maxValue = specifiedFacets["maxExclusive"]
                    if specifiedFacets["maxInclusive"] != None:
                        maxValue = specifiedFacets["maxInclusive"]
                    # TODO: use orderedValue for '<' check!!
                    if minValue != None and maxValue != None and maxValue < minValue:
                        self._addError ("maxValue facet < minValue facet!", restrictionNode)

            except TagException:
                self._addError ("Primitive type for base type not found!", restrictionNode)

        listNodes, dummy, dummy = self.inputRoot.getXPathList (".//%(prefix)slist" % vars())
        for listNode in listNodes:
            # check for unique ID
            self._checkNodeId (listNode)

            if not listNode.hasAttribute("itemType") and listNode.getFirstChildNS (self.inputNsURI, "simpleType") == None:
                self._addError ("List type must have 'itemType' attribute or 'simpleType' child tag!", listNode)
            elif listNode.hasAttribute("itemType") and listNode.getFirstChildNS (self.inputNsURI, "simpleType") != None:
                self._addError ("List type must not have 'itemType' attribute and 'simpleType' child tag!", listNode)
            elif listNode.hasAttribute("itemType"):
                itemType = self._checkType(listNode, "itemType", self.xsdTypeDict)
                if self.xsdTypeDict.has_key(itemType):
                    if self.xsdTypeDict[itemType].getLocalName() != "simpleType":
                        self._addError ("ItemType %s must be a simple type!" %(repr(itemType)), listNode)
                    elif self.xsdTypeDict[itemType].getFirstChild().getLocalName() == "list":
                        self._addError ("ItemType %s must not be a list type!" %(repr(itemType)), listNode)

        unionNodes, dummy, dummy = self.inputRoot.getXPathList (".//%(prefix)ssimpleType/%(prefix)sunion" % vars())
        for unionNode in unionNodes:
            # check for unique ID
            self._checkNodeId (unionNode)

            if not unionNode.hasAttribute("memberTypes"):
                for childNode in unionNode.getChildren():
                    if childNode.getLocalName() != "annotation":
                        break
                else:
                    self._addError ("Union must not be empty!", unionNode)
            else:
                for memberType in string.split(unionNode["memberTypes"]):
                    memberNsName = unionNode.qName2NsName(memberType, 1)
                    self._checkBaseType(unionNode, memberNsName, self.xsdTypeDict)
                    if self.xsdTypeDict.has_key(memberNsName):
                        if self.xsdTypeDict[memberNsName].getLocalName() != "simpleType":
                            self._addError ("MemberType %s must be a simple type!" %(repr(memberNsName)), unionNode)

        patternNodes, dummy, dummy = self.inputRoot.getXPathList (".//%(prefix)spattern" % vars())
        for patternNode in patternNodes:
            pattern = patternNode["value"]
            try:
                pattern = substituteSpecialEscChars (pattern)
                try:
                    test = re.compile(pattern)
                except Exception, errstr:
                    self._addError (str(errstr), patternNode)
                    self._addError ("%s is not a valid regular expression!" %(repr(patternNode["value"])), patternNode)
            except SyntaxError, errInst:
                    self._addError (repr(errInst[0]), patternNode)


    ########################################
    # additional checks for keyrefs
    #
    def _checkIdentityConstraintsSecondLevel(self):
        identityConstraintNodes, dummy, dummy = self.inputRoot.getXPathList (".//%sunique" %(self.inputNsPrefixString))
        for identityConstraintNode in identityConstraintNodes:
            # check for unique ID
            self._checkNodeId (identityConstraintNode)

            selectorNode = identityConstraintNode.getFirstChildNS(XSD_NAMESPACE, "selector")
            self._checkNodeId (selectorNode)
            try:
                completeChildList, attrNodeList, attrNsNameFirst = identityConstraintNode.getParentNode().getXPathList (selectorNode["xpath"], selectorNode)
                if attrNsNameFirst != None:
                    self._addError ("Selection of attributes is not allowed for selector!", selectorNode)
            except Exception, errstr:
                self._addError (errstr, selectorNode)

            try:
                fieldNode = identityConstraintNode.getFirstChildNS(XSD_NAMESPACE, "field")
                identityConstraintNode.getParentNode().getXPathList (fieldNode["xpath"], fieldNode)
                self._checkNodeId (fieldNode)
            except Exception, errstr:
                self._addError (errstr, fieldNode)


    ########################################
    # additional checks for keyrefs
    #
    def _checkKeysSecondLevel(self):
        keyNodes, dummy, dummy = self.inputRoot.getXPathList (".//%skey" %(self.inputNsPrefixString))
        for keyNode in keyNodes:
            # check for unique ID
            self._checkNodeId (keyNode)

            fieldNode = keyNode.getFirstChildNS(XSD_NAMESPACE, "field")
            if fieldNode != None:
                self._checkNodeId (fieldNode)
                

    ########################################
    # additional checks for keyrefs
    #
    def _checkKeyRefsSecondLevel(self):
        keyrefNodes, dummy, dummy = self.inputRoot.getXPathList (".//%skeyref" %(self.inputNsPrefixString))
        for keyrefNode in keyrefNodes:
            # check for unique ID
            self._checkNodeId (keyrefNode)

            self._checkKeyRef(keyrefNode, self.xsdIdentityConstrDict)
                

    ########################################
    # helper methods
    #

    def _checkFixedDefault(self, node):
        if node.hasAttribute("default") and node.hasAttribute("fixed"):
            self._addError ("%s may have 'default' OR 'fixed' attribute!" %repr(node.getLocalName()), node)
        if  node.hasAttribute("default"):
            self._checkSimpleType (node, "type", node, "default", node["default"], None, checkAttribute=1)
        if  node.hasAttribute("fixed"):
            self._checkSimpleType (node, "type", node, "fixed", node["fixed"], None, checkAttribute=1)
    
    
    def _checkReference(self, node, dict):
        baseNsName = node.getQNameAttribute("ref")
        if dict.has_key(baseNsName):
            refNode = dict[baseNsName]
            fixedValue = node.getAttribute("fixed")
            fixedRefValue = refNode.getAttribute("fixed")
            if fixedValue != None and fixedRefValue != None and fixedValue != fixedRefValue:
                self._addError ("Fixed value %s of attribute does not match fixed value %s of reference!" %(repr(fixedValue), repr(fixedRefValue)), node)
                
        else:
            self._addError ("Reference %s not found!" %(repr(baseNsName)), node)

    def _checkType(self, node, typeAttrName, dict, typeNsName=None):
        baseNsName = node.getQNameAttribute(typeAttrName)
        self._checkBaseType(node, baseNsName, dict, typeNsName)
        return baseNsName
    
    def _checkBaseType(self, node, baseNsName, dict, typeNsName=None):
        if not dict.has_key(baseNsName) and baseNsName != (XSD_NAMESPACE, "anySimpleType"):
            self._addError ("Definition of type %s not found!" %(repr(baseNsName)), node)
        elif typeNsName != None:
            if typeNsName == (XSD_NAMESPACE, "simpleContent"):
                if node.getNsName() == (XSD_NAMESPACE, "restriction"):
                    if (baseNsName != (XSD_NAMESPACE, "anySimpleType") and
                        dict[baseNsName].getNsName() == (XSD_NAMESPACE, "complexType") and
                        dict[baseNsName].getFirstChild().getNsName() == typeNsName):
                        pass
                    else:
                        self._addError ("Referred type %s must be a complex type with simple content!" %(repr(baseNsName)), node)
                else: # extension
                    if (baseNsName == (XSD_NAMESPACE, "anySimpleType") or
                        dict[baseNsName].getNsName() == (XSD_NAMESPACE, "simpleType") or
                       (dict[baseNsName].getNsName() == (XSD_NAMESPACE, "complexType") and
                        dict[baseNsName].getFirstChild().getNsName() == typeNsName)):
                        pass
                    else:
                        self._addError ("Referred type %s must be a simple type or a complex type with simple content!" %(repr(baseNsName)), node)
            else:
                if typeNsName == (XSD_NAMESPACE, "simpleType") and baseNsName == (XSD_NAMESPACE, "anySimpleType"):
                    pass
                elif dict[baseNsName].getNsName() != typeNsName:
                    self._addError ("Referred type %s must be a %s!" %(repr(baseNsName), repr(typeNsName)), node)


    def _checkKeyRef(self, keyrefNode, dict):
        baseNsName = keyrefNode.getQNameAttribute("refer")
        if not dict.has_key(baseNsName):
            self._addError ("keyref refers unknown key %s!" %(repr(baseNsName)), keyrefNode)
        else:
            keyNode = dict[baseNsName]["Node"]
            if keyNode.getNsName() not in ((XSD_NAMESPACE, "key"), (XSD_NAMESPACE, "unique")):
                self._addError ("reference to non-key constraint %s!" %(repr(baseNsName)), keyrefNode)
            if len(keyrefNode.getChildrenNS(XSD_NAMESPACE, "field")) != len(keyNode.getChildrenNS(XSD_NAMESPACE, "field")):
                self._addError ("key/keyref field size mismatch!", keyrefNode)
                
            
    def _checkOccurs (self, node):
        minOccurs = node.getAttributeOrDefault("minOccurs", "1")
        maxOccurs = node.getAttributeOrDefault("maxOccurs", "1")
        if maxOccurs != "unbounded":
            if string.atoi(minOccurs) > string.atoi(maxOccurs):
                self._addError ("Attribute minOccurs > maxOccurs!", node)


    def _checkNodeId (self, node, unambiguousPerFile=1):
        if node.hasAttribute("id"):
            # id must only be unambiguous within one file
            if unambiguousPerFile:
                nodeId = (node.getAbsUrl(), collapseString(node["id"]))
            else:
                nodeId = collapseString(node["id"])
            if not self.xsdIdDict.has_key(nodeId):
                self.xsdIdDict[nodeId] = node
            else:
                self._addError ("There are multiple occurences of ID value %s!" %repr(nodeId), node)


    def _getFacetType(self, node, parentNodeList, xsdTypeDict):
            baseNsName = node.getQNameAttribute("base")
            try:
                baseNode = xsdTypeDict[baseNsName]
            except:
                self._addError ("Base type %s must be an atomic simple type definition or a builtin type!" %repr(baseNsName), node)
                return None

            if baseNode in parentNodeList:
                self._addError ("Circular type definition (type is contained in its own type hierarchy)!", node)
                return None
                
            if baseNode.getNsName() == (XSD_NAMESPACE, "simpleType"):
                if baseNode.getAttribute("facetType") != None:
                    facetType = baseNode.qName2NsName(baseNode["facetType"], 1)
                    node.getParentNode()["facetType"] = node.nsName2QName(facetType)
                    return facetType
                else:
                    for baseNodeType in ("list", "union"):
                        if baseNode.getFirstChildNS (XSD_NAMESPACE, baseNodeType) != None:
                            return (XSD_NAMESPACE, baseNodeType)
                    else:
                        parentNodeList.append(node)
                        return self._getFacetType(baseNode.getFirstChildNS(XSD_NAMESPACE, "restriction"), parentNodeList, xsdTypeDict)    
            else:
                self._addError ("Base type %s must be an atomic simple type definition or a builtin type!" %repr(baseNsName), node)
                return None
            


########NEW FILE########
__FILENAME__ = xsvalSimpleTypes
#
# minixsv, Release 0.9.0
# file: xsvalSimpleTypes.py
#
# class for validation of XML schema simple types
#
# history:
# 2004-09-09 rl   created
# 2006-08-18 rl   W3C testsuite passed for supported features
# 2007-05-24 rl   Features for release 0.8 added, some bugs fixed
#
# Copyright (c) 2004-2007 by Roland Leuthe.  All rights reserved.
#
# --------------------------------------------------------------------
# The minixsv XML schema validator is
#
# Copyright (c) 2004-2007 by Roland Leuthe
#
# By obtaining, using, and/or copying this software and/or its
# associated documentation, you agree that you have read, understood,
# and will comply with the following terms and conditions:
#
# Permission to use, copy, modify, and distribute this software and
# its associated documentation for any purpose and without fee is
# hereby granted, provided that the above copyright notice appears in
# all copies, and that both that copyright notice and this permission
# notice appear in supporting documentation, and that the name of
# the author not be used in advertising or publicity
# pertaining to distribution of the software without specific, written
# prior permission.
#
# THE AUTHOR DISCLAIMS ALL WARRANTIES WITH REGARD
# TO THIS SOFTWARE, INCLUDING ALL IMPLIED WARRANTIES OF MERCHANT-
# ABILITY AND FITNESS.  IN NO EVENT SHALL THE AUTHOR
# BE LIABLE FOR ANY SPECIAL, INDIRECT OR CONSEQUENTIAL DAMAGES OR ANY
# DAMAGES WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS,
# WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS
# ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR PERFORMANCE
# OF THIS SOFTWARE.
# --------------------------------------------------------------------

import sys
import string
import re
import datetime
from decimal             import Decimal
from ..genxmlif.xmlifUtils import removeWhitespaces, collapseString, normalizeString, NsNameTupleFactory
from ..minixsv             import XSD_NAMESPACE
from xsvalUtils          import substituteSpecialEscChars

###################################################
# Validator class for simple types
###################################################
class XsSimpleTypeVal:

    def __init__ (self, parent):
        self.parent = parent
        self.xmlIf  = parent.xmlIf
        self.xsdNsURI = parent.xsdNsURI
        self.xsdIdDict = parent.xsdIdDict
        self.xsdIdRefDict = parent.xsdIdRefDict


    def unlink (self):
        self.parent = None
        

    ########################################
    # validate given value against simpleType
    #
    def checkSimpleType (self, inputNode, attrName, typeName, attributeValue, returnDict, idCheck):
        returnDict["adaptedAttrValue"] = attributeValue
        returnDict["BaseTypes"].append(str(typeName))
        if _suppBaseTypeDict.has_key(typeName):
            try:
                _suppBaseTypeDict[typeName] (inputNode, typeName, attributeValue, returnDict)
                returnDict["primitiveType"] = typeName
            except BaseTypeError, errstr:
                raise SimpleTypeError("Value of %s (%s) %s" %(repr(attrName), repr(attributeValue), errstr))

        elif self.parent.xsdTypeDict.has_key(typeName):
            typedefNode = self.parent.xsdTypeDict[typeName]
            if typedefNode.getNsName() == (XSD_NAMESPACE, "simpleType"):
                self.checkSimpleTypeDef (inputNode, typedefNode, attrName, attributeValue, returnDict, idCheck)
            elif (typedefNode.getNsName() == (XSD_NAMESPACE, "complexType") and
                  typedefNode.getFirstChild().getNsName() == (XSD_NAMESPACE, "simpleContent")):
                self.checkSimpleTypeDef (inputNode, typedefNode.getFirstChild(), attrName, attributeValue, returnDict, idCheck)
            elif typedefNode.getAttribute("mixed") == "true":
                self.checkSimpleType (inputNode, attrName, (XSD_NAMESPACE, "string"), attributeValue, returnDict, idCheck)
            elif typeName != (XSD_NAMESPACE, "anyType"):
                raise SimpleTypeError("Attribute %s requires a simple type!" %repr(attrName))
            
            if idCheck:
                adaptedAttrValue = returnDict["adaptedAttrValue"]
                if typeName == (XSD_NAMESPACE, "ID"):
                    if not self.xsdIdDict.has_key(adaptedAttrValue):
                        self.xsdIdDict[adaptedAttrValue] = inputNode
                    else:
                        raise SimpleTypeError("There are multiple occurences of ID value %s!" %repr(adaptedAttrValue))
                if typeName == (XSD_NAMESPACE, "IDREF"):
                    self.xsdIdRefDict[adaptedAttrValue] = inputNode
        else:
            # TODO: Fehler im XSD-File => Check muss an anderer Stelle erfolgen
            raise SimpleTypeError("%s uses unknown type %s!" %(repr(attrName), repr(typeName)))


    ########################################
    # validate given value against simpleType node
    #
    def checkSimpleTypeDef (self, inputNode, xsdElement, attrName, attributeValue, returnDict, idCheck):
        returnDict["adaptedAttrValue"] = attributeValue
        restrictionElement = xsdElement.getFirstChildNS(self.xsdNsURI, "restriction")
        extensionElement   = xsdElement.getFirstChildNS(self.xsdNsURI, "extension")
        listElement        = xsdElement.getFirstChildNS(self.xsdNsURI, "list")
        unionElement       = xsdElement.getFirstChildNS(self.xsdNsURI, "union")
        if restrictionElement != None:
            self._checkRestrictionTag (inputNode, restrictionElement, attrName, attributeValue, returnDict, idCheck)
        if extensionElement != None:
            self._checkExtensionTag (inputNode, extensionElement, attrName, attributeValue, returnDict, idCheck)
        elif listElement != None:
            self._checkListTag (inputNode, listElement, attrName, attributeValue, returnDict, idCheck)
        elif unionElement != None:
            self._checkUnionTag (inputNode, unionElement, attrName, attributeValue, returnDict, idCheck)


    ########################################
    # validate given value against base type
    #
    def checkBaseType (self, inputNode, xsdElement, attrName, attributeValue, returnDict, idCheck):
        baseType = xsdElement.getQNameAttribute("base")
        if baseType != NsNameTupleFactory(None):
            self.checkSimpleType (inputNode, attrName, baseType, attributeValue, returnDict, idCheck)
        else:
            baseTypeNode = xsdElement.getFirstChildNS(self.xsdNsURI, "simpleType")
            self.checkSimpleTypeDef (inputNode, baseTypeNode, attrName, attributeValue, returnDict, idCheck)
    
    
    ########################################
    # validate given value against restriction node
    #
    def _checkRestrictionTag (self, inputNode, xsdElement, attrName, attributeValue, returnDict, idCheck):
        savedAttrValue = attributeValue
        # first check against base type
        self.checkBaseType (inputNode, xsdElement, attrName, attributeValue, returnDict, idCheck)

        minExcl = xsdElement.getFirstChildNS(self.xsdNsURI, "minExclusive")
        minIncl = xsdElement.getFirstChildNS(self.xsdNsURI, "minInclusive")
        maxExcl = xsdElement.getFirstChildNS(self.xsdNsURI, "maxExclusive")
        maxIncl = xsdElement.getFirstChildNS(self.xsdNsURI, "maxInclusive")

        if minExcl != None:
            minExclReturnDict = {"BaseTypes":[], "primitiveType":None}
            minExclValue = minExcl.getAttribute("value")
            self.checkBaseType (inputNode, xsdElement, attrName, minExclValue, minExclReturnDict, idCheck=0)
            if returnDict.has_key("orderedValue") and minExclReturnDict.has_key("orderedValue"):
                if returnDict["orderedValue"] <= minExclReturnDict["orderedValue"]:
                    raise SimpleTypeError ("Value of %s (%s) is <= minExclusive (%s)" %(repr(attrName), repr(attributeValue), repr(minExclValue)))
        elif minIncl != None:
            minInclReturnDict = {"BaseTypes":[], "primitiveType":None}
            minInclValue = minIncl.getAttribute("value")
            self.checkBaseType (inputNode, xsdElement, attrName, minInclValue, minInclReturnDict, idCheck=0)
            if returnDict.has_key("orderedValue") and minInclReturnDict.has_key("orderedValue"):
                if returnDict["orderedValue"] < minInclReturnDict["orderedValue"]:
                    raise SimpleTypeError ("Value of %s (%s) is < minInclusive (%s)" %(repr(attrName), repr(attributeValue), repr(minInclValue)))
        if maxExcl != None:
            maxExclReturnDict = {"BaseTypes":[], "primitiveType":None}
            maxExclValue = maxExcl.getAttribute("value")
            self.checkBaseType (inputNode, xsdElement, attrName, maxExclValue, maxExclReturnDict, idCheck=0)
            if returnDict.has_key("orderedValue") and maxExclReturnDict.has_key("orderedValue"):
                if returnDict["orderedValue"] >= maxExclReturnDict["orderedValue"]:
                    raise SimpleTypeError ("Value of %s (%s) is >= maxExclusive (%s)" %(repr(attrName), repr(attributeValue), repr(maxExclValue)))
        elif maxIncl != None:
            maxInclReturnDict = {"BaseTypes":[], "primitiveType":None}
            maxInclValue = maxIncl.getAttribute("value")
            self.checkBaseType (inputNode, xsdElement, attrName, maxInclValue, maxInclReturnDict, idCheck=0)
            if returnDict.has_key("orderedValue") and maxInclReturnDict.has_key("orderedValue"):
                if returnDict["orderedValue"] > maxInclReturnDict["orderedValue"]:
                    raise SimpleTypeError ("Value of %s (%s) is > maxInclusive (%s)" %(repr(attrName), repr(attributeValue), repr(maxInclValue)))

        totalDigitsNode = xsdElement.getFirstChildNS(self.xsdNsURI, "totalDigits")
        if totalDigitsNode != None:
            orderedValueStr = repr(returnDict["orderedValue"])
            digits = re.findall("\d" ,orderedValueStr)
            if digits[0] == "0" and len(digits) > 1:
                digits = digits[1:]
            totalDigitsValue = totalDigitsNode.getAttribute("value")
            if totalDigitsNode.getAttribute("fixed") == "true":
                if len(digits) != string.atoi(totalDigitsValue):
                    raise SimpleTypeError ("Total number of digits != %s for %s (%s)" %(repr(totalDigitsValue), repr(attrName), repr(attributeValue)))
            else:
                if len(digits) > string.atoi(totalDigitsValue):
                    raise SimpleTypeError ("Total number of digits > %s for %s (%s)" %(repr(totalDigitsValue), repr(attrName), repr(attributeValue)))

        fractionDigitsNode = xsdElement.getFirstChildNS(self.xsdNsURI, "fractionDigits")
        if fractionDigitsNode != None:
            orderedValueStr = repr(returnDict["orderedValue"])
            fractionDigitsValue = fractionDigitsNode.getAttribute("value")
            result = re.search("(?P<intDigits>\d*)(?P<dot>\.)(?P<fracDigits>\d+)", orderedValueStr)
            if result != None:
                numberOfFracDigits = len (result.group('fracDigits'))
            else:
                numberOfFracDigits = 0
            if fractionDigitsNode.getAttribute("fixed") == "true" and numberOfFracDigits != string.atoi(fractionDigitsValue):
                raise SimpleTypeError ("Fraction number of digits != %s for %s (%s)" %(repr(fractionDigitsValue), repr(attrName), repr(attributeValue)))
            elif numberOfFracDigits > string.atoi(fractionDigitsValue):
                raise SimpleTypeError ("Fraction number of digits > %s for %s (%s)" %(repr(fractionDigitsValue), repr(attrName), repr(attributeValue)))

        if returnDict.has_key("length"):
            lengthNode = xsdElement.getFirstChildNS(self.xsdNsURI, "length")
            if lengthNode != None:
                length = string.atoi(lengthNode.getAttribute("value"))
                if returnDict["length"] != length:
                    raise SimpleTypeError ("Length of %s (%s) must be %d!" %(repr(attrName), repr(attributeValue), length))
            minLengthNode = xsdElement.getFirstChildNS(self.xsdNsURI, "minLength")
            if minLengthNode != None:
                minLength = string.atoi(minLengthNode.getAttribute("value"))
                if returnDict["length"] < minLength:
                    raise SimpleTypeError ("Length of %s (%s) must be >= %d!" %(repr(attrName), repr(attributeValue), minLength))
            maxLengthNode = xsdElement.getFirstChildNS(self.xsdNsURI, "maxLength")
            if maxLengthNode != None:
                maxLength = string.atoi(maxLengthNode.getAttribute("value"))
                if returnDict["length"] > maxLength:
                    raise SimpleTypeError ("Length of %s (%s) must be <= %d!" %(repr(attrName), repr(attributeValue), maxLength))

        whiteSpace = xsdElement.getFirstChildNS(self.xsdNsURI, "whiteSpace")
        if whiteSpace != None:
            returnDict["wsAction"] = whiteSpace.getAttribute("value")
            if returnDict["wsAction"] == "replace":
                normalizedValue = normalizeString(attributeValue)
                if normalizedValue != attributeValue:
                    returnDict["adaptedAttrValue"] = normalizedValue
            elif returnDict["wsAction"] == "collapse":
                collapsedValue = collapseString(attributeValue)
                if collapsedValue != attributeValue:
                    returnDict["adaptedAttrValue"] = collapsedValue

        enumerationElementList = xsdElement.getChildrenNS(self.xsdNsURI, "enumeration")
        if enumerationElementList != []:
            if returnDict.has_key("orderedValue"):
                attributeValue = returnDict["orderedValue"]
            elif returnDict.has_key("adaptedAttrValue"):
                attributeValue = returnDict["adaptedAttrValue"]

            for enumeration in enumerationElementList:
                enumReturnDict = {"BaseTypes":[], "primitiveType":None}
                enumValue = enumeration["value"]
                self.checkBaseType (inputNode, xsdElement, attrName, enumValue, enumReturnDict, idCheck=0)
                if enumReturnDict.has_key("orderedValue"):
                    enumValue = enumReturnDict["orderedValue"]
                elif enumReturnDict.has_key("adaptedAttrValue"):
                    enumValue = enumReturnDict["adaptedAttrValue"]
                
                if enumValue == attributeValue:
                    break
            else:
                raise SimpleTypeError ("Enumeration value %s not allowed!" %repr(attributeValue))

        
        if returnDict.has_key("adaptedAttrValue"):
            attributeValue = returnDict["adaptedAttrValue"]

        patternMatch = 1
        notMatchedPatternList = []
        for patternNode in xsdElement.getChildrenNS(self.xsdNsURI, "pattern"):
            rePattern = patternNode.getAttribute("value")
            intRePattern = rePattern
            try:
                intRePattern = substituteSpecialEscChars (intRePattern)
            except SyntaxError, errInst:
                raise SimpleTypeError, str(errInst)
            patternMatch = self._matchesPattern (intRePattern, attributeValue)

            if patternMatch:
                break
            else:
                notMatchedPatternList.append(rePattern)
        
        if not patternMatch:
            try:
                pattern = " nor ".join(notMatchedPatternList)
            except:
                pattern = ""
            raise SimpleTypeError ("Value of attribute %s (%s) does not match pattern %s!" %(repr(attrName), repr(attributeValue), repr(pattern)))


    ########################################
    # checks if 'value' matches 'rePattern' completely
    #
    def _matchesPattern (self, intRePattern, attributeValue):
        completePatternMatch = 0
        try:
            regexObj = re.match(intRePattern, attributeValue, re.U)
            if regexObj and regexObj.end() == len(attributeValue):
                completePatternMatch = 1
        except Exception:
            pass
        return completePatternMatch


    ########################################
    # validate given value against list node
    #
    def _checkListTag (self, inputNode, xsdElement, attrName, attributeValue, returnDict, idCheck):
        if attributeValue != "":
            itemType = xsdElement.getQNameAttribute ("itemType")
            # substitute multiple whitespace characters by a single ' '
            collapsedValue = collapseString(attributeValue)
            returnDict["wsAction"] = "collapse"
            returnDict["adaptedAttrValue"] = collapsedValue

            # divide up attributeValue => store it into list
            attributeList = string.split(collapsedValue, " ")
            for attrValue in attributeList:
                elementReturnDict = {"BaseTypes":[], "primitiveType":None}
                if itemType != (None, None):
                    self.checkSimpleType (inputNode, attrName, itemType, attrValue, elementReturnDict, idCheck)
                else:
                    itemTypeNode = xsdElement.getFirstChildNS(self.xsdNsURI, "simpleType")
                    self.checkSimpleTypeDef (inputNode, itemTypeNode, attrName, attrValue, elementReturnDict, idCheck)

            returnDict["BaseTypes"].extend(elementReturnDict["BaseTypes"])
            returnDict["length"] = len(attributeList)
        else:
            returnDict["length"] = 0


    ########################################
    # validate given value against extension node
    #
    def _checkExtensionTag (self, inputNode, xsdElement, attrName, attributeValue, returnDict, idCheck):
        # first check against base type
        self.checkBaseType (inputNode, xsdElement, attrName, attributeValue, returnDict, idCheck)


    ########################################
    # validate given value against union node
    #
    def _checkUnionTag (self, inputNode, xsdElement, attrName, attributeValue, returnDict, idCheck):
        memberTypes = xsdElement.getAttribute ("memberTypes")
        if memberTypes != None:
            # substitute multiple whitespace characters by a single ' '
            # divide up attributeValue => store it into list
            for memberType in string.split(collapseString(memberTypes), " "):
                try:
                    self.checkSimpleType (inputNode, attrName, xsdElement.qName2NsName(memberType, useDefaultNs=1), attributeValue, returnDict, idCheck)
                    return
                except SimpleTypeError, errstr:
                    pass

        # memberTypes and additional type definitions is legal!
        for childSimpleType in xsdElement.getChildrenNS(self.xsdNsURI, "simpleType"):
            try:
                self.checkSimpleTypeDef (inputNode, childSimpleType, attrName, attributeValue, returnDict, idCheck)
                return
            except SimpleTypeError, errstr:
                pass

        raise SimpleTypeError ("%s (%s) is no valid union member type!" %(repr(attrName), repr(attributeValue)))


###############################################################
#  Base type check functions
###############################################################

reDecimal      = re.compile("[+-]?[0-9]*\.?[0-9]+", re.U)
reInteger      = re.compile("[+-]?[0-9]+", re.U)
reDouble       = re.compile("([+-]?[0-9]*\.?[0-9]+([eE][+\-]?[0-9]+)?)|INF|-INF|NaN", re.U)
reHexBinary    = re.compile("([a-fA-F0-9]{2})*", re.U)
reBase64Binary = re.compile("(?P<validBits>[a-zA-Z0-9+/]*)={0,3}", re.U)
reQName        = re.compile(substituteSpecialEscChars("\i\c*"), re.U)
reDuration     = re.compile("-?P(?P<years>\d+Y)?(?P<months>\d+M)?(?P<days>\d+D)?(T(?P<hours>\d+H)?(?P<minutes>\d+M)?((?P<seconds>\d+)(?P<fracsec>\.\d+)?S)?)?", re.U)

reDateTime     = re.compile("(?P<date>\d{4}-\d{2}-\d{2})T(?P<time>\d{2}:\d{2}:\d{2}(\.\d+)?)(?P<offset>Z|[+-]\d{2}:\d{2})?", re.U)
reDate         = re.compile("\d{4}-\d{2}-\d{2}(?P<offset>Z|[+-]\d{2}:\d{2})?", re.U)
reTime         = re.compile("(?P<time>\d{2}:\d{2}:\d{2})(?P<fracsec>\.\d+)?(?P<offset>Z|[+-]\d{2}:\d{2})?", re.U)
reYearMonth    = re.compile("\d{4}-\d{2}(?P<offset>Z|[+-]\d{2}:\d{2})?", re.U)
reMonthDay     = re.compile("--\d{2}-\d{2}(?P<offset>Z|[+-]\d{2}:\d{2})?", re.U)
reYear         = re.compile("(?P<year>\d{1,4})(?P<offset>Z|[+-]\d{2}:\d{2})?", re.U)
reMonth        = re.compile("--\d{2}(--)?(?P<offset>Z|[+-]\d{2}:\d{2})?", re.U)
reDay          = re.compile("---\d{2}(?P<offset>Z|[+-]\d{2}:\d{2})?", re.U)


def _checkAnySimpleType (inputNode, simpleType, attributeValue, returnDict):
    # TODO: Nothing to check??
    returnDict["length"] = len(attributeValue)

def _checkStringType (inputNode, simpleType, attributeValue, returnDict):
    # TODO: all valid??
    returnDict["length"] = len(attributeValue)

def _checkAnyUriType (inputNode, simpleType, attributeValue, returnDict):
    # TODO: any checks??
    if attributeValue[0:2] == '##':
        raise BaseTypeError("is not a valid URI!")
    returnDict["adaptedAttrValue"] = collapseString(attributeValue)
    returnDict["wsAction"] = "collapse"
    returnDict["length"] = len(attributeValue)

def _checkDecimalType (inputNode, simpleType, attributeValue, returnDict):
    attributeValue = collapseString(attributeValue)
    regexObj = reDecimal.match(attributeValue)
    if not regexObj or regexObj.end() != len(attributeValue):
        raise BaseTypeError("is not a decimal value!")
    try:
        value = Decimal(attributeValue)
        returnDict["orderedValue"] = value.normalize()
        returnDict["adaptedAttrValue"] = attributeValue
        returnDict["wsAction"] = "collapse"
    except:
        raise BaseTypeError("is not a decimal value!")


def _checkIntegerType (inputNode, simpleType, attributeValue, returnDict):
    attributeValue = collapseString(attributeValue)
    regexObj = reInteger.match(attributeValue)
    if not regexObj or regexObj.end() != len(attributeValue):
        raise BaseTypeError("is not an integer value!")
    try:
        returnDict["orderedValue"] = Decimal(attributeValue)
        returnDict["adaptedAttrValue"] = attributeValue
        returnDict["wsAction"] = "collapse"
    except:
        raise BaseTypeError("is out of range for validation!")


def _checkFloatType (inputNode, simpleType, attributeValue, returnDict):
    attributeValue = collapseString(attributeValue)
    if attributeValue not in ("INF", "-INF", "NaN"):
        try:
            value = float(attributeValue)
            returnDict["orderedValue"] = value
            returnDict["adaptedAttrValue"] = attributeValue
            returnDict["wsAction"] = "collapse"
        except:
            raise BaseTypeError("is not a float value!")

def _checkDoubleType (inputNode, simpleType, attributeValue, returnDict):
    attributeValue = collapseString(attributeValue)
    regexObj = reDouble.match(attributeValue)
    if not regexObj or regexObj.end() != len(attributeValue):
        raise BaseTypeError("is not a double value!")
    try:
        value = Decimal(attributeValue)
        returnDict["orderedValue"] = value.normalize()
        returnDict["adaptedAttrValue"] = attributeValue
        returnDict["wsAction"] = "collapse"
    except:
        raise BaseTypeError("is not a double value!")

def _checkHexBinaryType (inputNode, simpleType, attributeValue, returnDict):
    attributeValue = removeWhitespaces(attributeValue)
    regexObj = reHexBinary.match(attributeValue)
    if not regexObj or regexObj.end() != len(attributeValue):
        raise BaseTypeError("is not a hexBinary value (each byte is represented by 2 characters)!")
    returnDict["length"] = len(attributeValue) / 2
    returnDict["adaptedAttrValue"] = attributeValue
    returnDict["wsAction"] = "collapse"

def _checkBase64BinaryType (inputNode, simpleType, attributeValue, returnDict):
    attributeValue = collapseString(attributeValue)
    regexObj = reBase64Binary.match(attributeValue)
    if not regexObj or regexObj.end() != len(attributeValue):
        raise BaseTypeError("is not a base64Binary value (6 bits are represented by 1 character)!")
    returnDict["length"] = (len(regexObj.group("validBits")) * 6) / 8
    returnDict["adaptedAttrValue"] = attributeValue
    returnDict["wsAction"] = "collapse"

def _checkBooleanType (inputNode, simpleType, attributeValue, returnDict):
    attributeValue = collapseString(attributeValue)
    if attributeValue not in ("true", "false", "1", "0"):
        raise BaseTypeError("is not a boolean value!")
    if attributeValue in ("true", "1"):
        returnDict["orderedValue"] = "__BOOLEAN_TRUE__"
    else:
        returnDict["orderedValue"] = "__BOOLEAN_FALSE__"
    returnDict["adaptedAttrValue"] = attributeValue
    returnDict["wsAction"] = "collapse"

def _checkQNameType (inputNode, simpleType, attributeValue, returnDict):
    attributeValue = collapseString(attributeValue)
    regexObj = reQName.match(attributeValue)
    if not regexObj or regexObj.end() != len(attributeValue):
        raise BaseTypeError("is not a QName!")
    
    try:
        inputNode.getNamespace(attributeValue)
    except LookupError:
        raise BaseTypeError("is not a valid QName (namespace prefix unknown)!")

    returnDict["length"] = len(attributeValue)
    returnDict["orderedValue"] = inputNode.qName2NsName(attributeValue, useDefaultNs=1)
    returnDict["adaptedAttrValue"] = attributeValue
    returnDict["wsAction"] = "collapse"

def _checkDurationType (inputNode, simpleType, attributeValue, returnDict):
    attributeValue = collapseString(attributeValue)
    regexObj = reDuration.match(attributeValue)
    if not regexObj or regexObj.end() != len(attributeValue) or attributeValue[-1] == "T" or attributeValue[-1] == "P":
        raise BaseTypeError("is not a valid duration value!")
    sign = ""
    if attributeValue[0] == "-": sign = "-"
    days = 0
    seconds = 0
    microseconds = 0
    if regexObj.group("years") != None:
        days = days + (int(sign + regexObj.group("years")[:-1]) * 365)
    if regexObj.group("months") != None:
        days = days + (int(sign + regexObj.group("months")[:-1]) * 30)
    if regexObj.group("days") != None:
        days = days + int(sign + regexObj.group("days")[:-1])
    if regexObj.group("hours") != None:
        seconds = seconds + int(sign + regexObj.group("hours")[:-1]) * 3600
    if regexObj.group("minutes") != None:
        seconds = seconds + (int(sign + regexObj.group("minutes")[:-1]) * 60)
    if regexObj.group("seconds") != None:
        seconds = seconds + int(sign + regexObj.group("seconds"))
    if regexObj.group("fracsec") != None:
        microseconds = int(Decimal(sign + regexObj.group("fracsec")) * 1000000)
    try:
        timeDeltaObj = datetime.timedelta(days=days, seconds=seconds, microseconds=microseconds)
    except ValueError, errstr:
        raise BaseTypeError("is invalid (%s)!" %(errstr))
    returnDict["orderedValue"] = timeDeltaObj
    returnDict["adaptedAttrValue"] = attributeValue
    returnDict["wsAction"] = "collapse"
    
def _checkDateTimeType (inputNode, simpleType, attributeValue, returnDict):
    attributeValue = collapseString(attributeValue)
    regexObj = reDateTime.match(attributeValue)
    if not regexObj or regexObj.end() != len(attributeValue):
        raise BaseTypeError("is not a dateTime value!")
    date = regexObj.group("date")
    time = regexObj.group("time")
    offset = regexObj.group("offset")
    try:
        if offset != None:
            tz = TimezoneFixedOffset(offset)
        else:
            tz = None
        dtObj = datetime.datetime(int(date[0:4]),int(date[5:7]),int(date[8:10]),
                                  int(time[0:2]),int(time[3:5]),int(time[6:8]), 0, tz)
    except ValueError, errstr:
        raise BaseTypeError("is invalid (%s)!" %(errstr))
    returnDict["orderedValue"] = dtObj
    returnDict["adaptedAttrValue"] = attributeValue
    returnDict["wsAction"] = "collapse"
    
def _checkDateType (inputNode, simpleType, attributeValue, returnDict):
    attributeValue = collapseString(attributeValue)
    regexObj = reDate.match(attributeValue)
    if not regexObj or regexObj.end() != len(attributeValue):
        raise BaseTypeError("is not a date value!")
    try:
        dateObj = datetime.date(int(attributeValue[0:4]),int(attributeValue[5:7]),int(attributeValue[8:10]))
    except ValueError, errstr:
        raise BaseTypeError("is invalid (%s)!" %(errstr))
    returnDict["orderedValue"] = dateObj
    returnDict["adaptedAttrValue"] = attributeValue
    returnDict["wsAction"] = "collapse"
    
def _checkTimeType (inputNode, simpleType, attributeValue, returnDict):
    attributeValue = collapseString(attributeValue)
    regexObj = reTime.match(attributeValue)
    if not regexObj or regexObj.end() != len(attributeValue):
        raise BaseTypeError("is not a time value!")
    time = regexObj.group("time")
    fracsec = regexObj.group("fracsec")
    offset = regexObj.group("offset")
    try:
        if offset != None:
            tz = TimezoneFixedOffset(offset)
        else:
            tz = None
        if fracsec != None:
            fracSec = int(fracsec[1:])
        else:
            fracSec = 0
        timeObj = datetime.time(int(time[0:2]),int(time[3:5]),int(time[6:8]), fracSec, tz)
    except ValueError, errstr:
        raise BaseTypeError("is invalid (%s)!" %(errstr))
    returnDict["orderedValue"] = timeObj
    returnDict["adaptedAttrValue"] = attributeValue
    returnDict["wsAction"] = "collapse"
    
def _checkYearMonth (inputNode, simpleType, attributeValue, returnDict):
    attributeValue = collapseString(attributeValue)
    regexObj = reYearMonth.match(attributeValue)
    if not regexObj or regexObj.end() != len(attributeValue):
        raise BaseTypeError("is not a gYearMonth value!")
    try:
        dateObj = datetime.date(int(attributeValue[0:4]),int(attributeValue[5:7]),1)
    except ValueError, errstr:
        raise BaseTypeError("is invalid (%s)!" %(errstr))
    returnDict["orderedValue"] = dateObj
    returnDict["adaptedAttrValue"] = attributeValue
    returnDict["wsAction"] = "collapse"

def _checkMonthDay (inputNode, simpleType, attributeValue, returnDict):
    attributeValue = collapseString(attributeValue)
    regexObj = reMonthDay.match(attributeValue)
    if not regexObj or regexObj.end() != len(attributeValue):
        raise BaseTypeError("is not a gMonthDay value!")
    try:
        dateObj = datetime.date(2004, int(attributeValue[2:4]),int(attributeValue[5:7]))
    except ValueError, errstr:
        raise BaseTypeError("is invalid (%s)!" %(errstr))
    returnDict["orderedValue"] = dateObj
    returnDict["adaptedAttrValue"] = attributeValue
    returnDict["wsAction"] = "collapse"
    
def _checkYear (inputNode, simpleType, attributeValue, returnDict):
    attributeValue = collapseString(attributeValue)
    regexObj = reYear.match(attributeValue)
    if not regexObj or regexObj.end() != len(attributeValue or regexObj.group("year") == None):
        raise BaseTypeError("is not a gYear value (1)!")
    try:
        year = int(regexObj.group("year"))
        if year < 1 or year > 9999:
            raise BaseTypeError("is not a valid gYear value!")
    except:
        raise BaseTypeError("is not a gYear value!")
    returnDict["orderedValue"] = year
    returnDict["adaptedAttrValue"] = attributeValue
    returnDict["wsAction"] = "collapse"

def _checkMonth (inputNode, simpleType, attributeValue, returnDict):
    attributeValue = collapseString(attributeValue)
    regexObj = reMonth.match(attributeValue)
    if not regexObj or regexObj.end() != len(attributeValue):
        raise BaseTypeError("is not a gMonth value!")
    month = int(attributeValue[2:4])
    if month < 1 or month > 12:
        raise BaseTypeError("is invalid (month must be in 1..12)!")
    returnDict["orderedValue"] = month
    returnDict["adaptedAttrValue"] = attributeValue
    returnDict["wsAction"] = "collapse"

def _checkDay (inputNode, simpleType, attributeValue, returnDict):
    attributeValue = collapseString(attributeValue)
    regexObj = reDay.match(attributeValue)
    if not regexObj or regexObj.end() != len(attributeValue):
        raise BaseTypeError("is not a gDay value!")
    day = int(attributeValue[3:5])
    if day < 1 or day > 31:
        raise BaseTypeError("is invalid (day must be in 1..31)!")
    returnDict["orderedValue"] = day
    returnDict["adaptedAttrValue"] = attributeValue
    returnDict["wsAction"] = "collapse"

########################################
# timezone class
#
class TimezoneFixedOffset(datetime.tzinfo):
    def __init__(self, offset):
        if offset == "Z":
            self.__offset = datetime.timedelta(0)
        else:
            self.__offset = datetime.timedelta(hours=int(offset[0:3]), 
                                               minutes=int(offset[0] + offset[4:5]))

    def utcoffset(self, dt):
        return self.__offset
    def tzname(self, dt):
        return None

    def dst(self, dt):
        return datetime.timedelta(0)

########################################
# define own exception for XML schema validation errors
#
class SimpleTypeError (StandardError):
    pass

class BaseTypeError (StandardError):
    pass


########################################
# Base type dictionaries
#
_suppBaseTypeDict = {(XSD_NAMESPACE, "anySimpleType"):    _checkAnySimpleType,
                     (XSD_NAMESPACE, "string"):           _checkStringType,
                     (XSD_NAMESPACE, "anyURI"):           _checkAnyUriType,
                     (XSD_NAMESPACE, "decimal"):          _checkDecimalType,
                     (XSD_NAMESPACE, "integer"):          _checkIntegerType,
                     (XSD_NAMESPACE, "float"):            _checkFloatType,
                     (XSD_NAMESPACE, "double"):           _checkDoubleType,
                     (XSD_NAMESPACE, "hexBinary"):        _checkHexBinaryType,
                     (XSD_NAMESPACE, "base64Binary"):     _checkBase64BinaryType,
                     (XSD_NAMESPACE, "boolean"):          _checkBooleanType,
                     (XSD_NAMESPACE, "QName"):            _checkQNameType,
                     (XSD_NAMESPACE, "NOTATION"):         _checkQNameType,
                     (XSD_NAMESPACE, "duration"):         _checkDurationType,
                     (XSD_NAMESPACE, "dateTime"):         _checkDateTimeType,
                     (XSD_NAMESPACE, "date"):             _checkDateType,
                     (XSD_NAMESPACE, "time"):             _checkTimeType,
                     (XSD_NAMESPACE, "gYearMonth"):       _checkYearMonth,
                     (XSD_NAMESPACE, "gMonthDay"):        _checkMonthDay,
                     (XSD_NAMESPACE, "gYear"):            _checkYear,
                     (XSD_NAMESPACE, "gMonth"):           _checkMonth,
                     (XSD_NAMESPACE, "gDay"):             _checkDay,
                    }


########NEW FILE########
__FILENAME__ = xsvalUtils
#
# minixsv, Release 0.9.0
# file: xsvalUtils.py
#
# utility functions for XML schema validation
#
# history:
# 2008-02-13 rl   created
#
# Copyright (c) 2004-2008 by Roland Leuthe.  All rights reserved.
#
# --------------------------------------------------------------------
# The minixsv XML schema validator is
#
# Copyright (c) 2004-2008 by Roland Leuthe
#
# By obtaining, using, and/or copying this software and/or its
# associated documentation, you agree that you have read, understood,
# and will comply with the following terms and conditions:
#
# Permission to use, copy, modify, and distribute this software and
# its associated documentation for any purpose and without fee is
# hereby granted, provided that the above copyright notice appears in
# all copies, and that both that copyright notice and this permission
# notice appear in supporting documentation, and that the name of
# the author not be used in advertising or publicity
# pertaining to distribution of the software without specific, written
# prior permission.
#
# THE AUTHOR DISCLAIMS ALL WARRANTIES WITH REGARD
# TO THIS SOFTWARE, INCLUDING ALL IMPLIED WARRANTIES OF MERCHANT-
# ABILITY AND FITNESS.  IN NO EVENT SHALL THE AUTHOR
# BE LIABLE FOR ANY SPECIAL, INDIRECT OR CONSEQUENTIAL DAMAGES OR ANY
# DAMAGES WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS,
# WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS
# ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR PERFORMANCE
# OF THIS SOFTWARE.
# --------------------------------------------------------------------

import string
import re

creWithinSet = re.compile(r"(^|.*[^\\])(?P<obr>\[)[^\]]*\Z")

creMultiCharEscP = re.compile(r"(?P<pbs>\\*)(?P<escSeq>(?P<inv>[\^])?\\(?P<pP>[pP]){(?P<id>[^}]*)})")

substMultiCharEscPDict = {
     r"Cc" : ur"\x00-\x1f\x7f-\x9f",
     r"Cf" : ur"\u06dd\u070f\u180e\u200c-\u200f\u202a-\u202e\u2060-\u2063\u206a-\u206f\ufeff\ufff9-\ufffb",
     r"Co" : ur"\ue000-\uf8ff",
     r"Cn" : ur"\ufdd0-\ufdef\ufffe\uffff",
     r"Cs" : ur"\ud800-\udfff",
     r"C" : ur"\x00-\x1f\x7f-\x9f\u06dd\u070f\u180e\u200c-\u200f\u202a-\u202e\u2060-\u2063\u206a-\u206f\ud800-\uf8ff\ufeff\ufff9-\ufffb",
                                    
     r"Ll" : ur"a-z\xaa\xb5\xba\xdf-\xf6\xf8-\xff\u0101\u0103\u0105\u0107\u0109\u010b\u010d\u010f\u0111\u0113\u0115\u0117\u0119\u011b\u011d\u011f\u0121\u0123\u0125\u0127\u0129\u012b\u012d\u012f\u0131\u0133\u0135\u0137-\u0138\u013a\u013c\u013e\u0140\u0142\u0144\u0146\u0148-\u0149\u014b\u014d\u014f\u0151\u0153\u0155\u0157\u0159\u015b\u015d\u015f\u0161\u0163\u0165\u0167\u0169\u016b\u016d\u016f\u0171\u0173\u0175\u0177\u017a\u017c\u017e-\u0180\u0183\u0185\u0188\u018c-\u018d\u0192\u0195\u0199-\u019b\u019e\u01a1\u01a3\u01a5\u01a8\u01aa-\u01ab\u01ad\u01b0\u01b4\u01b6\u01b9-\u01ba\u01bd-\u01bf\u01c6\u01c9\u01cc\u01ce\u01d0\u01d2\u01d4\u01d6\u01d8\u01da\u01dc-\u01dd\u01df\u01e1\u01e3\u01e5\u01e7\u01e9\u01eb\u01ed\u01ef-\u01f0\u01f3\u01f5\u01f9\u01fb\u01fd\u01ff\u0201\u0203\u0205\u0207\u0209\u020b\u020d\u020f\u0211\u0213\u0215\u0217\u0219\u021b\u021d\u021f\u0223\u0225\u0227\u0229\u022b\u022d\u022f\u0231\u0233\u0250-\u02ad\u0390\u03ac-\u03ce\u03d0-\u03d1\u03d5-\u03d7\u03d9\u03db\u03dd\u03df\u03e1\u03e3\u03e5\u03e7\u03e9\u03eb\u03ed\u03ef-\u03f3\u03f5\u0430-\u045f\u0461\u0463\u0465\u0467\u0469\u046b\u046d\u046f\u0471\u0473\u0475\u0477\u0479\u047b\u047d\u047f\u0481\u048b\u048d\u048f\u0491\u0493\u0495\u0497\u0499\u049b\u049d\u049f\u04a1\u04a3\u04a5\u04a7\u04a9\u04ab\u04ad\u04af\u04b1\u04b3\u04b5\u04b7\u04b9\u04bb\u04bd\u04bf\u04c2\u04c4\u04c6\u04c8\u04ca\u04cc\u04ce\u04d1\u04d3\u04d5\u04d7\u04d9\u04db\u04dd\u04df\u04e1\u04e3\u04e5\u04e7\u04e9\u04eb\u04ed\u04ef\u04f1\u04f3\u04f5\u04f9\u0501\u0503\u0505\u0507\u0509\u050b\u050d\u050f\u0561-\u0587\u1e01\u1e03\u1e05\u1e07\u1e09\u1e0b\u1e0d\u1e0f\u1e11\u1e13\u1e15\u1e17\u1e19\u1e1b\u1e1d\u1e1f\u1e21\u1e23\u1e25\u1e27\u1e29\u1e2b\u1e2d\u1e2f\u1e31\u1e33\u1e35\u1e37\u1e39\u1e3b\u1e3d\u1e3f\u1e41\u1e43\u1e45\u1e47\u1e49\u1e4b\u1e4d\u1e4f\u1e51\u1e53\u1e55\u1e57\u1e59\u1e5b\u1e5d\u1e5f\u1e61\u1e63\u1e65\u1e67\u1e69\u1e6b\u1e6d\u1e6f\u1e71\u1e73\u1e75\u1e77\u1e79\u1e7b\u1e7d\u1e7f\u1e81\u1e83\u1e85\u1e87\u1e89\u1e8b\u1e8d\u1e8f\u1e91\u1e93\u1e95-\u1e9b\u1ea1\u1ea3\u1ea5\u1ea7\u1ea9\u1eab\u1ead\u1eaf\u1eb1\u1eb3\u1eb5\u1eb7\u1eb9\u1ebb\u1ebd\u1ebf\u1ec1\u1ec3\u1ec5\u1ec7\u1ec9\u1ecb\u1ecd\u1ecf\u1ed1\u1ed3\u1ed5\u1ed7\u1ed9\u1edb\u1edd\u1edf\u1ee1\u1ee3\u1ee5\u1ee7\u1ee9\u1eeb\u1eed\u1eef\u1ef1\u1ef3\u1ef5\u1ef7\u1ef9\u1f00-\u1f07\u1f10-\u1f15\u1f20-\u1f27\u1f30-\u1f37\u1f40-\u1f45\u1f50-\u1f57\u1f60-\u1f67\u1f70-\u1f7d\u1f80-\u1f87\u1f90-\u1f97\u1fa0-\u1fa7\u1fb0-\u1fb4\u1fb6-\u1fb7\u1fbe\u1fc2-\u1fc4\u1fc6-\u1fc7\u1fd0-\u1fd3\u1fd6-\u1fd7\u1fe0-\u1fe7\u1ff2-\u1ff4\u1ff6-\u1ff7\u2071\u207f\u210a\u210e-\u210f\u2113\u212f\u2134\u2139\u213d\u2146-\u2149\ufb00-\ufb06\ufb13-\ufb17\uff41-\uff5a",
     r"Lm" : ur"\u02b0-\u02b8\u02bb-\u02c1\u02d0-\u02d1\u02e0-\u02e4\u02ee\u037a\u0559\u0640\u06e5-\u06e6\u0e46\u0ec6\u17d7\u1843\u3005\u3031-\u3035\u303b\u309d-\u309e\u30fc-\u30fe\uff70\uff9e-\uff9f",
     r"Lo" : ur"\u01bb\u01c0-\u01c3\u05d0-\u05ea\u05f0-\u05f2\u0621-\u063a\u0641-\u064a\u066e-\u066f\u0671-\u06d3\u06d5\u06fa-\u06fc\u0710\u0712-\u072c\u0780-\u07a5\u07b1\u0905-\u0939\u093d\u0950\u0958-\u0961\u0985-\u098c\u098f-\u0990\u0993-\u09a8\u09aa-\u09b0\u09b2\u09b6-\u09b9\u09dc-\u09dd\u09df-\u09e1\u09f0-\u09f1\u0a05-\u0a0a\u0a0f-\u0a10\u0a13-\u0a28\u0a2a-\u0a30\u0a32-\u0a33\u0a35-\u0a36\u0a38-\u0a39\u0a59-\u0a5c\u0a5e\u0a72-\u0a74\u0a85-\u0a8b\u0a8d\u0a8f-\u0a91\u0a93-\u0aa8\u0aaa-\u0ab0\u0ab2-\u0ab3\u0ab5-\u0ab9\u0abd\u0ad0\u0ae0\u0b05-\u0b0c\u0b0f-\u0b10\u0b13-\u0b28\u0b2a-\u0b30\u0b32-\u0b33\u0b36-\u0b39\u0b3d\u0b5c-\u0b5d\u0b5f-\u0b61\u0b83\u0b85-\u0b8a\u0b8e-\u0b90\u0b92-\u0b95\u0b99-\u0b9a\u0b9c\u0b9e-\u0b9f\u0ba3-\u0ba4\u0ba8-\u0baa\u0bae-\u0bb5\u0bb7-\u0bb9\u0c05-\u0c0c\u0c0e-\u0c10\u0c12-\u0c28\u0c2a-\u0c33\u0c35-\u0c39\u0c60-\u0c61\u0c85-\u0c8c\u0c8e-\u0c90\u0c92-\u0ca8\u0caa-\u0cb3\u0cb5-\u0cb9\u0cde\u0ce0-\u0ce1\u0d05-\u0d0c\u0d0e-\u0d10\u0d12-\u0d28\u0d2a-\u0d39\u0d60-\u0d61\u0d85-\u0d96\u0d9a-\u0db1\u0db3-\u0dbb\u0dbd\u0dc0-\u0dc6\u0e01-\u0e30\u0e32-\u0e33\u0e40-\u0e45\u0e81-\u0e82\u0e84\u0e87-\u0e88\u0e8a\u0e8d\u0e94-\u0e97\u0e99-\u0e9f\u0ea1-\u0ea3\u0ea5\u0ea7\u0eaa-\u0eab\u0ead-\u0eb0\u0eb2-\u0eb3\u0ebd\u0ec0-\u0ec4\u0edc-\u0edd\u0f00\u0f40-\u0f47\u0f49-\u0f6a\u0f88-\u0f8b\u1000-\u1021\u1023-\u1027\u1029-\u102a\u1050-\u1055\u10d0-\u10f8\u1100-\u1159\u115f-\u11a2\u11a8-\u11f9\u1200-\u1206\u1208-\u1246\u1248\u124a-\u124d\u1250-\u1256\u1258\u125a-\u125d\u1260-\u1286\u1288\u128a-\u128d\u1290-\u12ae\u12b0\u12b2-\u12b5\u12b8-\u12be\u12c0\u12c2-\u12c5\u12c8-\u12ce\u12d0-\u12d6\u12d8-\u12ee\u12f0-\u130e\u1310\u1312-\u1315\u1318-\u131e\u1320-\u1346\u1348-\u135a\u13a0-\u13f4\u1401-\u166c\u166f-\u1676\u1681-\u169a\u16a0-\u16ea\u1700-\u170c\u170e-\u1711\u1720-\u1731\u1740-\u1751\u1760-\u176c\u176e-\u1770\u1780-\u17b3\u17dc\u1820-\u1842\u1844-\u1877\u1880-\u18a8\u2135-\u2138\u3006\u303c\u3041-\u3096\u309f\u30a1-\u30fa\u30ff\u3105-\u312c\u3131-\u318e\u31a0-\u31b7\u31f0-\u31ff\u3400-\u4db5\u4e00-\u9fa5\ua000-\ua48c\uac00-\ud7a3\uf900-\ufa2d\ufa30-\ufa6a\ufb1d\ufb1f-\ufb28\ufb2a-\ufb36\ufb38-\ufb3c\ufb3e\ufb40-\ufb41\ufb43-\ufb44\ufb46-\ufbb1\ufbd3-\ufd3d\ufd50-\ufd8f\ufd92-\ufdc7\ufdf0-\ufdfb\ufe70-\ufe74\ufe76-\ufefc\uff66-\uff6f\uff71-\uff9d\uffa0-\uffbe\uffc2-\uffc7\uffca-\uffcf\uffd2-\uffd7\uffda-\uffdc",
     r"Lt" : ur"\u01c5\u01c8\u01cb\u01f2\u1f88-\u1f8f\u1f98-\u1f9f\u1fa8-\u1faf\u1fbc\u1fcc\u1ffc",
     r"Lu" : ur"A-Z\xc0-\xd6\xd8-\xde\u0100\u0102\u0104\u0106\u0108\u010a\u010c\u010e\u0110\u0112\u0114\u0116\u0118\u011a\u011c\u011e\u0120\u0122\u0124\u0126\u0128\u012a\u012c\u012e\u0130\u0132\u0134\u0136\u0139\u013b\u013d\u013f\u0141\u0143\u0145\u0147\u014a\u014c\u014e\u0150\u0152\u0154\u0156\u0158\u015a\u015c\u015e\u0160\u0162\u0164\u0166\u0168\u016a\u016c\u016e\u0170\u0172\u0174\u0176\u0178-\u0179\u017b\u017d\u0181-\u0182\u0184\u0186-\u0187\u0189-\u018b\u018e-\u0191\u0193-\u0194\u0196-\u0198\u019c-\u019d\u019f-\u01a0\u01a2\u01a4\u01a6-\u01a7\u01a9\u01ac\u01ae-\u01af\u01b1-\u01b3\u01b5\u01b7-\u01b8\u01bc\u01c4\u01c7\u01ca\u01cd\u01cf\u01d1\u01d3\u01d5\u01d7\u01d9\u01db\u01de\u01e0\u01e2\u01e4\u01e6\u01e8\u01ea\u01ec\u01ee\u01f1\u01f4\u01f6-\u01f8\u01fa\u01fc\u01fe\u0200\u0202\u0204\u0206\u0208\u020a\u020c\u020e\u0210\u0212\u0214\u0216\u0218\u021a\u021c\u021e\u0220\u0222\u0224\u0226\u0228\u022a\u022c\u022e\u0230\u0232\u0386\u0388-\u038a\u038c\u038e-\u038f\u0391-\u03a1\u03a3-\u03ab\u03d2-\u03d4\u03d8\u03da\u03dc\u03de\u03e0\u03e2\u03e4\u03e6\u03e8\u03ea\u03ec\u03ee\u03f4\u0400-\u042f\u0460\u0462\u0464\u0466\u0468\u046a\u046c\u046e\u0470\u0472\u0474\u0476\u0478\u047a\u047c\u047e\u0480\u048a\u048c\u048e\u0490\u0492\u0494\u0496\u0498\u049a\u049c\u049e\u04a0\u04a2\u04a4\u04a6\u04a8\u04aa\u04ac\u04ae\u04b0\u04b2\u04b4\u04b6\u04b8\u04ba\u04bc\u04be\u04c0-\u04c1\u04c3\u04c5\u04c7\u04c9\u04cb\u04cd\u04d0\u04d2\u04d4\u04d6\u04d8\u04da\u04dc\u04de\u04e0\u04e2\u04e4\u04e6\u04e8\u04ea\u04ec\u04ee\u04f0\u04f2\u04f4\u04f8\u0500\u0502\u0504\u0506\u0508\u050a\u050c\u050e\u0531-\u0556\u10a0-\u10c5\u1e00\u1e02\u1e04\u1e06\u1e08\u1e0a\u1e0c\u1e0e\u1e10\u1e12\u1e14\u1e16\u1e18\u1e1a\u1e1c\u1e1e\u1e20\u1e22\u1e24\u1e26\u1e28\u1e2a\u1e2c\u1e2e\u1e30\u1e32\u1e34\u1e36\u1e38\u1e3a\u1e3c\u1e3e\u1e40\u1e42\u1e44\u1e46\u1e48\u1e4a\u1e4c\u1e4e\u1e50\u1e52\u1e54\u1e56\u1e58\u1e5a\u1e5c\u1e5e\u1e60\u1e62\u1e64\u1e66\u1e68\u1e6a\u1e6c\u1e6e\u1e70\u1e72\u1e74\u1e76\u1e78\u1e7a\u1e7c\u1e7e\u1e80\u1e82\u1e84\u1e86\u1e88\u1e8a\u1e8c\u1e8e\u1e90\u1e92\u1e94\u1ea0\u1ea2\u1ea4\u1ea6\u1ea8\u1eaa\u1eac\u1eae\u1eb0\u1eb2\u1eb4\u1eb6\u1eb8\u1eba\u1ebc\u1ebe\u1ec0\u1ec2\u1ec4\u1ec6\u1ec8\u1eca\u1ecc\u1ece\u1ed0\u1ed2\u1ed4\u1ed6\u1ed8\u1eda\u1edc\u1ede\u1ee0\u1ee2\u1ee4\u1ee6\u1ee8\u1eea\u1eec\u1eee\u1ef0\u1ef2\u1ef4\u1ef6\u1ef8\u1f08-\u1f0f\u1f18-\u1f1d\u1f28-\u1f2f\u1f38-\u1f3f\u1f48-\u1f4d\u1f59\u1f5b\u1f5d\u1f5f\u1f68-\u1f6f\u1fb8-\u1fbb\u1fc8-\u1fcb\u1fd8-\u1fdb\u1fe8-\u1fec\u1ff8-\u1ffb\u2102\u2107\u210b-\u210d\u2110-\u2112\u2115\u2119-\u211d\u2124\u2126\u2128\u212a-\u212d\u2130-\u2131\u2133\u213e-\u213f\u2145\uff21-\uff3a",
     r"L" : ur"A-Za-z\xaa\xb5\xba\xc0-\xd6\xd8-\xf6\xf8-\u0220\u0222-\u0233\u0250-\u02ad\u02b0-\u02b8\u02bb-\u02c1\u02d0-\u02d1\u02e0-\u02e4\u02ee\u037a\u0386\u0388-\u038a\u038c\u038e-\u03a1\u03a3-\u03ce\u03d0-\u03f5\u0400-\u0481\u048a-\u04ce\u04d0-\u04f5\u04f8-\u04f9\u0500-\u050f\u0531-\u0556\u0559\u0561-\u0587\u05d0-\u05ea\u05f0-\u05f2\u0621-\u063a\u0640-\u064a\u066e-\u066f\u0671-\u06d3\u06d5\u06e5-\u06e6\u06fa-\u06fc\u0710\u0712-\u072c\u0780-\u07a5\u07b1\u0905-\u0939\u093d\u0950\u0958-\u0961\u0985-\u098c\u098f-\u0990\u0993-\u09a8\u09aa-\u09b0\u09b2\u09b6-\u09b9\u09dc-\u09dd\u09df-\u09e1\u09f0-\u09f1\u0a05-\u0a0a\u0a0f-\u0a10\u0a13-\u0a28\u0a2a-\u0a30\u0a32-\u0a33\u0a35-\u0a36\u0a38-\u0a39\u0a59-\u0a5c\u0a5e\u0a72-\u0a74\u0a85-\u0a8b\u0a8d\u0a8f-\u0a91\u0a93-\u0aa8\u0aaa-\u0ab0\u0ab2-\u0ab3\u0ab5-\u0ab9\u0abd\u0ad0\u0ae0\u0b05-\u0b0c\u0b0f-\u0b10\u0b13-\u0b28\u0b2a-\u0b30\u0b32-\u0b33\u0b36-\u0b39\u0b3d\u0b5c-\u0b5d\u0b5f-\u0b61\u0b83\u0b85-\u0b8a\u0b8e-\u0b90\u0b92-\u0b95\u0b99-\u0b9a\u0b9c\u0b9e-\u0b9f\u0ba3-\u0ba4\u0ba8-\u0baa\u0bae-\u0bb5\u0bb7-\u0bb9\u0c05-\u0c0c\u0c0e-\u0c10\u0c12-\u0c28\u0c2a-\u0c33\u0c35-\u0c39\u0c60-\u0c61\u0c85-\u0c8c\u0c8e-\u0c90\u0c92-\u0ca8\u0caa-\u0cb3\u0cb5-\u0cb9\u0cde\u0ce0-\u0ce1\u0d05-\u0d0c\u0d0e-\u0d10\u0d12-\u0d28\u0d2a-\u0d39\u0d60-\u0d61\u0d85-\u0d96\u0d9a-\u0db1\u0db3-\u0dbb\u0dbd\u0dc0-\u0dc6\u0e01-\u0e30\u0e32-\u0e33\u0e40-\u0e46\u0e81-\u0e82\u0e84\u0e87-\u0e88\u0e8a\u0e8d\u0e94-\u0e97\u0e99-\u0e9f\u0ea1-\u0ea3\u0ea5\u0ea7\u0eaa-\u0eab\u0ead-\u0eb0\u0eb2-\u0eb3\u0ebd\u0ec0-\u0ec4\u0ec6\u0edc-\u0edd\u0f00\u0f40-\u0f47\u0f49-\u0f6a\u0f88-\u0f8b\u1000-\u1021\u1023-\u1027\u1029-\u102a\u1050-\u1055\u10a0-\u10c5\u10d0-\u10f8\u1100-\u1159\u115f-\u11a2\u11a8-\u11f9\u1200-\u1206\u1208-\u1246\u1248\u124a-\u124d\u1250-\u1256\u1258\u125a-\u125d\u1260-\u1286\u1288\u128a-\u128d\u1290-\u12ae\u12b0\u12b2-\u12b5\u12b8-\u12be\u12c0\u12c2-\u12c5\u12c8-\u12ce\u12d0-\u12d6\u12d8-\u12ee\u12f0-\u130e\u1310\u1312-\u1315\u1318-\u131e\u1320-\u1346\u1348-\u135a\u13a0-\u13f4\u1401-\u166c\u166f-\u1676\u1681-\u169a\u16a0-\u16ea\u1700-\u170c\u170e-\u1711\u1720-\u1731\u1740-\u1751\u1760-\u176c\u176e-\u1770\u1780-\u17b3\u17d7\u17dc\u1820-\u1877\u1880-\u18a8\u1e00-\u1e9b\u1ea0-\u1ef9\u1f00-\u1f15\u1f18-\u1f1d\u1f20-\u1f45\u1f48-\u1f4d\u1f50-\u1f57\u1f59\u1f5b\u1f5d\u1f5f-\u1f7d\u1f80-\u1fb4\u1fb6-\u1fbc\u1fbe\u1fc2-\u1fc4\u1fc6-\u1fcc\u1fd0-\u1fd3\u1fd6-\u1fdb\u1fe0-\u1fec\u1ff2-\u1ff4\u1ff6-\u1ffc\u2071\u207f\u2102\u2107\u210a-\u2113\u2115\u2119-\u211d\u2124\u2126\u2128\u212a-\u212d\u212f-\u2131\u2133-\u2139\u213d-\u213f\u2145-\u2149\u3005-\u3006\u3031-\u3035\u303b-\u303c\u3041-\u3096\u309d-\u309f\u30a1-\u30fa\u30fc-\u30ff\u3105-\u312c\u3131-\u318e\u31a0-\u31b7\u31f0-\u31ff\u3400-\u4db5\u4e00-\u9fa5\ua000-\ua48c\uac00-\ud7a3\uf900-\ufa2d\ufa30-\ufa6a\ufb00-\ufb06\ufb13-\ufb17\ufb1d\ufb1f-\ufb28\ufb2a-\ufb36\ufb38-\ufb3c\ufb3e\ufb40-\ufb41\ufb43-\ufb44\ufb46-\ufbb1\ufbd3-\ufd3d\ufd50-\ufd8f\ufd92-\ufdc7\ufdf0-\ufdfb\ufe70-\ufe74\ufe76-\ufefc\uff21-\uff3a\uff41-\uff5a\uff66-\uffbe\uffc2-\uffc7\uffca-\uffcf\uffd2-\uffd7\uffda-\uffdc",
                                    
     r"Mc" : ur"\u0903\u093e-\u0940\u0949-\u094c\u0982-\u0983\u09be-\u09c0\u09c7-\u09c8\u09cb-\u09cc\u09d7\u0a3e-\u0a40\u0a83\u0abe-\u0ac0\u0ac9\u0acb-\u0acc\u0b02-\u0b03\u0b3e\u0b40\u0b47-\u0b48\u0b4b-\u0b4c\u0b57\u0bbe-\u0bbf\u0bc1-\u0bc2\u0bc6-\u0bc8\u0bca-\u0bcc\u0bd7\u0c01-\u0c03\u0c41-\u0c44\u0c82-\u0c83\u0cbe\u0cc0-\u0cc4\u0cc7-\u0cc8\u0cca-\u0ccb\u0cd5-\u0cd6\u0d02-\u0d03\u0d3e-\u0d40\u0d46-\u0d48\u0d4a-\u0d4c\u0d57\u0d82-\u0d83\u0dcf-\u0dd1\u0dd8-\u0ddf\u0df2-\u0df3\u0f3e-\u0f3f\u0f7f\u102c\u1031\u1038\u1056-\u1057\u17b4-\u17b6\u17be-\u17c5\u17c7-\u17c8",
     r"Me" : ur"\u0488-\u0489\u06de\u20dd-\u20e0\u20e2-\u20e4",
     r"Mn" : ur"\u0300-\u034f\u0360-\u036f\u0483-\u0486\u0591-\u05a1\u05a3-\u05b9\u05bb-\u05bd\u05bf\u05c1-\u05c2\u05c4\u064b-\u0655\u0670\u06d6-\u06dc\u06df-\u06e4\u06e7-\u06e8\u06ea-\u06ed\u0711\u0730-\u074a\u07a6-\u07b0\u0901-\u0902\u093c\u0941-\u0948\u094d\u0951-\u0954\u0962-\u0963\u0981\u09bc\u09c1-\u09c4\u09cd\u09e2-\u09e3\u0a02\u0a3c\u0a41-\u0a42\u0a47-\u0a48\u0a4b-\u0a4d\u0a70-\u0a71\u0a81-\u0a82\u0abc\u0ac1-\u0ac5\u0ac7-\u0ac8\u0acd\u0b01\u0b3c\u0b3f\u0b41-\u0b43\u0b4d\u0b56\u0b82\u0bc0\u0bcd\u0c3e-\u0c40\u0c46-\u0c48\u0c4a-\u0c4d\u0c55-\u0c56\u0cbf\u0cc6\u0ccc-\u0ccd\u0d41-\u0d43\u0d4d\u0dca\u0dd2-\u0dd4\u0dd6\u0e31\u0e34-\u0e3a\u0e47-\u0e4e\u0eb1\u0eb4-\u0eb9\u0ebb-\u0ebc\u0ec8-\u0ecd\u0f18-\u0f19\u0f35\u0f37\u0f39\u0f71-\u0f7e\u0f80-\u0f84\u0f86-\u0f87\u0f90-\u0f97\u0f99-\u0fbc\u0fc6\u102d-\u1030\u1032\u1036-\u1037\u1039\u1058-\u1059\u1712-\u1714\u1732-\u1734\u1752-\u1753\u1772-\u1773\u17b7-\u17bd\u17c6\u17c9-\u17d3\u180b-\u180d\u18a9\u20d0-\u20dc\u20e1\u20e5-\u20ea\u302a-\u302f\u3099-\u309a\ufb1e\ufe00-\ufe0f\ufe20-\ufe23",
     r"M" : ur"\u0300-\u034f\u0360-\u036f\u0483-\u0486\u0488-\u0489\u0591-\u05a1\u05a3-\u05b9\u05bb-\u05bd\u05bf\u05c1-\u05c2\u05c4\u064b-\u0655\u0670\u06d6-\u06dc\u06de-\u06e4\u06e7-\u06e8\u06ea-\u06ed\u0711\u0730-\u074a\u07a6-\u07b0\u0901-\u0903\u093c\u093e-\u094d\u0951-\u0954\u0962-\u0963\u0981-\u0983\u09bc\u09be-\u09c4\u09c7-\u09c8\u09cb-\u09cd\u09d7\u09e2-\u09e3\u0a02\u0a3c\u0a3e-\u0a42\u0a47-\u0a48\u0a4b-\u0a4d\u0a70-\u0a71\u0a81-\u0a83\u0abc\u0abe-\u0ac5\u0ac7-\u0ac9\u0acb-\u0acd\u0b01-\u0b03\u0b3c\u0b3e-\u0b43\u0b47-\u0b48\u0b4b-\u0b4d\u0b56-\u0b57\u0b82\u0bbe-\u0bc2\u0bc6-\u0bc8\u0bca-\u0bcd\u0bd7\u0c01-\u0c03\u0c3e-\u0c44\u0c46-\u0c48\u0c4a-\u0c4d\u0c55-\u0c56\u0c82-\u0c83\u0cbe-\u0cc4\u0cc6-\u0cc8\u0cca-\u0ccd\u0cd5-\u0cd6\u0d02-\u0d03\u0d3e-\u0d43\u0d46-\u0d48\u0d4a-\u0d4d\u0d57\u0d82-\u0d83\u0dca\u0dcf-\u0dd4\u0dd6\u0dd8-\u0ddf\u0df2-\u0df3\u0e31\u0e34-\u0e3a\u0e47-\u0e4e\u0eb1\u0eb4-\u0eb9\u0ebb-\u0ebc\u0ec8-\u0ecd\u0f18-\u0f19\u0f35\u0f37\u0f39\u0f3e-\u0f3f\u0f71-\u0f84\u0f86-\u0f87\u0f90-\u0f97\u0f99-\u0fbc\u0fc6\u102c-\u1032\u1036-\u1039\u1056-\u1059\u1712-\u1714\u1732-\u1734\u1752-\u1753\u1772-\u1773\u17b4-\u17d3\u180b-\u180d\u18a9\u20d0-\u20ea\u302a-\u302f\u3099-\u309a\ufb1e\ufe00-\ufe0f\ufe20-\ufe23",
                                    
     r"Nd" : ur"0-9\u0660-\u0669\u06f0-\u06f9\u0966-\u096f\u09e6-\u09ef\u0a66-\u0a6f\u0ae6-\u0aef\u0b66-\u0b6f\u0be7-\u0bef\u0c66-\u0c6f\u0ce6-\u0cef\u0d66-\u0d6f\u0e50-\u0e59\u0ed0-\u0ed9\u0f20-\u0f29\u1040-\u1049\u1369-\u1371\u17e0-\u17e9\u1810-\u1819\uff10-\uff19",
     r"Nl" : ur"\u16ee-\u16f0\u2160-\u2183\u3007\u3021-\u3029\u3038-\u303a",
     r"No" : ur"\xb2-\xb3\xb9\xbc-\xbe\u09f4-\u09f9\u0bf0-\u0bf2\u0f2a-\u0f33\u1372-\u137c\u2070\u2074-\u2079\u2080-\u2089\u2153-\u215f\u2460-\u249b\u24ea-\u24fe\u2776-\u2793\u3192-\u3195\u3220-\u3229\u3251-\u325f\u3280-\u3289\u32b1-\u32bf",
     r"N" : ur"0-9\xb2-\xb3\xb9\xbc-\xbe\u0660-\u0669\u06f0-\u06f9\u0966-\u096f\u09e6-\u09ef\u09f4-\u09f9\u0a66-\u0a6f\u0ae6-\u0aef\u0b66-\u0b6f\u0be7-\u0bf2\u0c66-\u0c6f\u0ce6-\u0cef\u0d66-\u0d6f\u0e50-\u0e59\u0ed0-\u0ed9\u0f20-\u0f33\u1040-\u1049\u1369-\u137c\u16ee-\u16f0\u17e0-\u17e9\u1810-\u1819\u2070\u2074-\u2079\u2080-\u2089\u2153-\u2183\u2460-\u249b\u24ea-\u24fe\u2776-\u2793\u3007\u3021-\u3029\u3038-\u303a\u3192-\u3195\u3220-\u3229\u3251-\u325f\u3280-\u3289\u32b1-\u32bf\uff10-\uff19",
                                    
     r"Pc" : ur"_\u203f-\u2040\u30fb\ufe33-\ufe34\ufe4d-\ufe4f\uff3f\uff65",
     r"Pd" : ur"-\xad\u058a\u1806\u2010-\u2015\u301c\u3030\u30a0\ufe31-\ufe32\ufe58\ufe63\uff0d",
     r"Pe" : ur")\]}\u0f3b\u0f3d\u169c\u2046\u207e\u208e\u232a\u23b5\u2769\u276b\u276d\u276f\u2771\u2773\u2775\u27e7\u27e9\u27eb\u2984\u2986\u2988\u298a\u298c\u298e\u2990\u2992\u2994\u2996\u2998\u29d9\u29db\u29fd\u3009\u300b\u300d\u300f\u3011\u3015\u3017\u3019\u301b\u301e-\u301f\ufd3f\ufe36\ufe38\ufe3a\ufe3c\ufe3e\ufe40\ufe42\ufe44\ufe5a\ufe5c\ufe5e\uff09\uff3d\uff5d\uff60\uff63",
     r"Pf" : ur"\xbb\u2019\u201d\u203a",
     r"Pi" : ur"\xab\u2018\u201b-\u201c\u201f\u2039",
     r"Po" : ur"!\"#%&'*,./:;?@\\\xa1\xb7\xbf\u037e\u0387\u055a-\u055f\u0589\u05be\u05c0\u05c3\u05f3-\u05f4\u060c\u061b\u061f\u066a-\u066d\u06d4\u0700-\u070d\u0964-\u0965\u0970\u0df4\u0e4f\u0e5a-\u0e5b\u0f04-\u0f12\u0f85\u104a-\u104f\u10fb\u1361-\u1368\u166d-\u166e\u16eb-\u16ed\u1735-\u1736\u17d4-\u17d6\u17d8-\u17da\u1800-\u1805\u1807-\u180a\u2016-\u2017\u2020-\u2027\u2030-\u2038\u203b-\u203e\u2041-\u2043\u2047-\u2051\u2057\u23b6\u3001-\u3003\u303d\ufe30\ufe45-\ufe46\ufe49-\ufe4c\ufe50-\ufe52\ufe54-\ufe57\ufe5f-\ufe61\ufe68\ufe6a-\ufe6b\uff01-\uff03\uff05-\uff07\uff0a\uff0c\uff0e-\uff0f\uff1a-\uff1b\uff1f-\uff20\uff3c\uff61\uff64",
     r"Ps" : ur"(\[{\u0f3a\u0f3c\u169b\u201a\u201e\u2045\u207d\u208d\u2329\u23b4\u2768\u276a\u276c\u276e\u2770\u2772\u2774\u27e6\u27e8\u27ea\u2983\u2985\u2987\u2989\u298b\u298d\u298f\u2991\u2993\u2995\u2997\u29d8\u29da\u29fc\u3008\u300a\u300c\u300e\u3010\u3014\u3016\u3018\u301a\u301d\ufd3e\ufe35\ufe37\ufe39\ufe3b\ufe3d\ufe3f\ufe41\ufe43\ufe59\ufe5b\ufe5d\uff08\uff3b\uff5b\uff5f\uff62",
     r"P" : ur"!\"#%&'()*,\-./:;?@\[\\\]_{}\xa1\xab\xad\xb7\xbb\xbf\u037e\u0387\u055a-\u055f\u0589-\u058a\u05be\u05c0\u05c3\u05f3-\u05f4\u060c\u061b\u061f\u066a-\u066d\u06d4\u0700-\u070d\u0964-\u0965\u0970\u0df4\u0e4f\u0e5a-\u0e5b\u0f04-\u0f12\u0f3a-\u0f3d\u0f85\u104a-\u104f\u10fb\u1361-\u1368\u166d-\u166e\u169b-\u169c\u16eb-\u16ed\u1735-\u1736\u17d4-\u17d6\u17d8-\u17da\u1800-\u180a\u2010-\u2027\u2030-\u2043\u2045-\u2051\u2057\u207d-\u207e\u208d-\u208e\u2329-\u232a\u23b4-\u23b6\u2768-\u2775\u27e6-\u27eb\u2983-\u2998\u29d8-\u29db\u29fc-\u29fd\u3001-\u3003\u3008-\u3011\u3014-\u301f\u3030\u303d\u30a0\u30fb\ufd3e-\ufd3f\ufe30-\ufe46\ufe49-\ufe52\ufe54-\ufe61\ufe63\ufe68\ufe6a-\ufe6b\uff01-\uff03\uff05-\uff0a\uff0c-\uff0f\uff1a-\uff1b\uff1f-\uff20\uff3b-\uff3d\uff3f\uff5b\uff5d\uff5f-\uff65",
                                    
     r"Sc" : ur"$\xa2-\xa5\u09f2-\u09f3\u0e3f\u17db\u20a0-\u20b1\ufdfc\ufe69\uff04\uffe0-\uffe1\uffe5-\uffe6",
     r"Sk" : ur"\^`\xa8\xaf\xb4\xb8\u02b9-\u02ba\u02c2-\u02cf\u02d2-\u02df\u02e5-\u02ed\u0374-\u0375\u0384-\u0385\u1fbd\u1fbf-\u1fc1\u1fcd-\u1fcf\u1fdd-\u1fdf\u1fed-\u1fef\u1ffd-\u1ffe\u309b-\u309c\uff3e\uff40\uffe3",
     r"Sm" : ur"+<=>|~\xac\xb1\xd7\xf7\u03f6\u2044\u2052\u207a-\u207c\u208a-\u208c\u2140-\u2144\u214b\u2190-\u2194\u219a-\u219b\u21a0\u21a3\u21a6\u21ae\u21ce-\u21cf\u21d2\u21d4\u21f4-\u22ff\u2308-\u230b\u2320-\u2321\u237c\u239b-\u23b3\u25b7\u25c1\u25f8-\u25ff\u266f\u27d0-\u27e5\u27f0-\u27ff\u2900-\u2982\u2999-\u29d7\u29dc-\u29fb\u29fe-\u2aff\ufb29\ufe62\ufe64-\ufe66\uff0b\uff1c-\uff1e\uff5c\uff5e\uffe2\uffe9-\uffec",
     r"So" : ur"\xa6-\xa7\xa9\xae\xb0\xb6\u0482\u06e9\u06fd-\u06fe\u09fa\u0b70\u0f01-\u0f03\u0f13-\u0f17\u0f1a-\u0f1f\u0f34\u0f36\u0f38\u0fbe-\u0fc5\u0fc7-\u0fcc\u0fcf\u2100-\u2101\u2103-\u2106\u2108-\u2109\u2114\u2116-\u2118\u211e-\u2123\u2125\u2127\u2129\u212e\u2132\u213a\u214a\u2195-\u2199\u219c-\u219f\u21a1-\u21a2\u21a4-\u21a5\u21a7-\u21ad\u21af-\u21cd\u21d0-\u21d1\u21d3\u21d5-\u21f3\u2300-\u2307\u230c-\u231f\u2322-\u2328\u232b-\u237b\u237d-\u239a\u23b7-\u23ce\u2400-\u2426\u2440-\u244a\u249c-\u24e9\u2500-\u25b6\u25b8-\u25c0\u25c2-\u25f7\u2600-\u2613\u2616-\u2617\u2619-\u266e\u2670-\u267d\u2680-\u2689\u2701-\u2704\u2706-\u2709\u270c-\u2727\u2729-\u274b\u274d\u274f-\u2752\u2756\u2758-\u275e\u2761-\u2767\u2794\u2798-\u27af\u27b1-\u27be\u2800-\u28ff\u2e80-\u2e99\u2e9b-\u2ef3\u2f00-\u2fd5\u2ff0-\u2ffb\u3004\u3012-\u3013\u3020\u3036-\u3037\u303e-\u303f\u3190-\u3191\u3196-\u319f\u3200-\u321c\u322a-\u3243\u3260-\u327b\u327f\u328a-\u32b0\u32c0-\u32cb\u32d0-\u32fe\u3300-\u3376\u337b-\u33dd\u33e0-\u33fe\ua490-\ua4c6\uffe4\uffe8\uffed-\uffee\ufffc-\ufffd",
     r"S" : ur"$+<=>\^`|~\xa2-\xa9\xac\xae-\xb1\xb4\xb6\xb8\xd7\xf7\u02b9-\u02ba\u02c2-\u02cf\u02d2-\u02df\u02e5-\u02ed\u0374-\u0375\u0384-\u0385\u03f6\u0482\u06e9\u06fd-\u06fe\u09f2-\u09f3\u09fa\u0b70\u0e3f\u0f01-\u0f03\u0f13-\u0f17\u0f1a-\u0f1f\u0f34\u0f36\u0f38\u0fbe-\u0fc5\u0fc7-\u0fcc\u0fcf\u17db\u1fbd\u1fbf-\u1fc1\u1fcd-\u1fcf\u1fdd-\u1fdf\u1fed-\u1fef\u1ffd-\u1ffe\u2044\u2052\u207a-\u207c\u208a-\u208c\u20a0-\u20b1\u2100-\u2101\u2103-\u2106\u2108-\u2109\u2114\u2116-\u2118\u211e-\u2123\u2125\u2127\u2129\u212e\u2132\u213a\u2140-\u2144\u214a-\u214b\u2190-\u2328\u232b-\u23b3\u23b7-\u23ce\u2400-\u2426\u2440-\u244a\u249c-\u24e9\u2500-\u2613\u2616-\u2617\u2619-\u267d\u2680-\u2689\u2701-\u2704\u2706-\u2709\u270c-\u2727\u2729-\u274b\u274d\u274f-\u2752\u2756\u2758-\u275e\u2761-\u2767\u2794\u2798-\u27af\u27b1-\u27be\u27d0-\u27e5\u27f0-\u2982\u2999-\u29d7\u29dc-\u29fb\u29fe-\u2aff\u2e80-\u2e99\u2e9b-\u2ef3\u2f00-\u2fd5\u2ff0-\u2ffb\u3004\u3012-\u3013\u3020\u3036-\u3037\u303e-\u303f\u309b-\u309c\u3190-\u3191\u3196-\u319f\u3200-\u321c\u322a-\u3243\u3260-\u327b\u327f\u328a-\u32b0\u32c0-\u32cb\u32d0-\u32fe\u3300-\u3376\u337b-\u33dd\u33e0-\u33fe\ua490-\ua4c6\ufb29\ufdfc\ufe62\ufe64-\ufe66\ufe69\uff04\uff0b\uff1c-\uff1e\uff3e\uff40\uff5c\uff5e\uffe0-\uffe6\uffe8-\uffee\ufffc-\ufffd",

     r"Zl" : ur"\u2028",
     r"Zp" : ur"\u2029",
     r"Zs" : ur" \xa0\u1680\u2000-\u200b\u202f\u205f\u3000",
     r"Z" : ur" \xa0\u1680\u2000-\u200b\u2028-\u2029\u202f\u205f\u3000",

     r"IsBasicLatin" : ur"\u0000-\u007f",
     r"IsLatin-1Supplement" : ur"\u0080-\u00ff",
     r"IsLatinExtended-A" : ur"\u0100-\u017f",
     r"IsLatinExtended-B" : ur"\u0180-\u024f",
     r"IsIPAExtensions" : ur"\u0250-\u02af",
     r"IsSpacingModifierLetters" : ur"\u02b0-\u02ff",
     r"IsCombiningDiacriticalMarks" : ur"\u0300-\u036f",
     r"IsGreek" : ur"\u0370-\u03ff",
     r"IsCyrillic" : ur"\u0400-\u04ff",
     r"IsArmenian" : ur"\u0530-\u058f",
     r"IsHebrew" : ur"\u0590-\u05ff",
     r"IsArabic" : ur"\u0600-\u06ff",
     r"IsSyriac" : ur"\u0700-\u074f",
     r"IsThaana" : ur"\u0780-\u07bf",
     r"IsDevanagari" : ur"\u0900-\u097f",
     r"IsBengali" : ur"\u0980-\u09ff",
     r"IsGurmukhi" : ur"\u0a00-\u0a7f",
     r"IsGujarati" : ur"\u0a80-\u0aff",
     r"IsOriya" : ur"\u0b00-\u0b7f",
     r"IsTamil" : ur"\u0b80-\u0bff",
     r"IsTelugu" : ur"\u0C00-\u0C7F",    
     r"IsKannada" : ur"\u0C80-\u0CFF",
     r"IsMalayalam" : ur"\u0D00-\u0D7F",
     r"IsSinhala" : ur"\u0D80-\u0DFF",
     r"IsThai" : ur"\u0E00-\u0E7F",
     r"IsLao" : ur"\u0E80-\u0EFF",
     r"IsTibetan" : ur"\u0F00-\u0FFF",
     r"IsMyanmar" : ur"\u1000-\u109F",
     r"IsGeorgian" : ur"\u10A0-\u10FF",
     r"IsHangulJamo" : ur"\u1100-\u11FF",
     r"IsEthiopic" : ur"\u1200-\u137F",
     r"IsCherokee" : ur"\u13A0-\u13FF",
     r"IsUnifiedCanadianAboriginalSyllabics" : ur"\u1400-\u167F",
     r"IsOgham" : ur"\u1680-\u169F",
     r"IsRunic" : ur"\u16A0-\u16FF",
     r"IsKhmer" : ur"\u1780-\u17FF",
     r"IsMongolian" : ur"\u1800-\u18AF",
     r"IsLatinExtendedAdditional" : ur"\u1E00-\u1EFF",
     r"IsGreekExtended" : ur"\u1F00-\u1FFF",
     r"IsGeneralPunctuation" : ur"\u2000-\u206F",
     r"IsSuperscriptsandSubscripts" : ur"\u2070-\u209F",
     r"IsCurrencySymbols" : ur"\u20A0-\u20CF",
     r"IsCombiningMarksforSymbols" : ur"\u20D0-\u20FF",
     r"IsLetterlikeSymbols" : ur"\u2100-\u214F",
     r"IsNumberForms" : ur"\u2150-\u218F",
     r"IsArrows" : ur"\u2190-\u21FF",
     r"IsMathematicalOperators" : ur"\u2200-\u22FF",
     r"IsMiscellaneousTechnical" : ur"\u2300-\u23FF",
     r"IsControlPictures" : ur"\u2400-\u243F",
     r"IsOpticalCharacterRecognition" : ur"\u2440-\u245F",
     r"IsEnclosedAlphanumerics" : ur"\u2460-\u24FF",
     r"IsBoxDrawing" : ur"\u2500-\u257F",
     r"IsBlockElements" : ur"\u2580-\u259F",
     r"IsGeometricShapes" : ur"\u25A0-\u25FF",
     r"IsMiscellaneousSymbols" : ur"\u2600-\u26FF",
     r"IsDingbats" : ur"\u2700-\u27BF",
     r"IsBraillePatterns" : ur"\u2800-\u28FF",
     r"IsCJKRadicalsSupplement" : ur"\u2E80-\u2EFF",
     r"IsKangxiRadicals" : ur"\u2F00-\u2FDF",
     r"IsIdeographicDescriptionCharacters" : ur"\u2FF0-\u2FFF",
     r"IsCJKSymbolsandPunctuation" : ur"\u3000-\u303F",
     r"IsHiragana" : ur"\u3040-\u309F",
     r"IsKatakana" : ur"\u30A0-\u30FF",
     r"IsBopomofo" : ur"\u3100-\u312F",
     r"IsHangulCompatibilityJamo" : ur"\u3130-\u318F",
     r"IsKanbun" : ur"\u3190-\u319F",
     r"IsBopomofoExtended" : ur"\u31A0-\u31BF",
     r"IsEnclosedCJKLettersandMonths" : ur"\u3200-\u32FF",
     r"IsCJKCompatibility" : ur"\u3300-\u33FF",
     r"IsCJKUnifiedIdeographsExtensionA" : ur"\u3400-\u4DB5",
     r"IsCJKUnifiedIdeographs" : ur"\u4E00-\u9FFF",
     r"IsYiSyllables" : ur"\uA000-\uA48F",
     r"IsYiRadicals" : ur"\uA490-\uA4CF",
     r"IsHangulSyllables" : ur"\uAC00-\uD7A3",
     r"IsHighSurrogates" : ur"\uD800-\uDB7F",
     r"IsHighPrivateUseSurrogates" : ur"\uDB80-\uDBFF",
     r"IsLowSurrogates" : ur"\uDC00-\uDFFF",
     r"IsPrivateUse" : ur"\uE000-\uF8FF",
     r"IsCJKCompatibilityIdeographs" : ur"\uF900-\uFAFF",
     r"IsAlphabeticPresentationForms" : ur"\uFB00-\uFB4F",
     r"IsArabicPresentationForms-A" : ur"\uFB50-\uFDFF",
     r"IsCombiningHalfMarks" : ur"\uFE20-\uFE2F",
     r"IsCJKCompatibilityForms" : ur"\uFE30-\uFE4F",
     r"IsSmallFormVariants" : ur"\uFE50-\uFE6F",
     r"IsArabicPresentationForms-B" : ur"\uFE70-\uFEFE",
     r"IsSpecials" : ur"\uFEFF-\uFEFF\uFFF0-\uFFFD",
     r"IsHalfwidthandFullwidthForms" : ur"\uFF00-\uFFEF",
# TODO: wide unicode characters are currently not supported!     
#     r"IsOldItalic" : ur"\U00010300-\U0001032F",
#     r"IsGothic" : ur"\U00010330-\U0001034F",
#     r"IsDeseret" : ur"\U00010400-\U0001044F",
#     r"IsByzantineMusicalSymbols" : ur"\U0001D000-\U0001D0FF",
#     r"IsMusicalSymbols" : ur"\U0001D100-\U0001D1FF",
#     r"IsMathematicalAlphanumericSymbols" : ur"\U0001D400-\U0001D7FF",
#     r"IsCJKUnifiedIdeographsExtensionB" : ur"\U00020000-\U0002A6D6",
#     r"IsCJKCompatibilityIdeographsSupplement" : ur"\U0002F800-\U0002FA1F",
#     r"IsTags" : ur"\U000E0000-\U000E007F",
#     r"IsPrivateUse" : ur"\U000F0000-\U000FFFFD\U00100000-\U0010FFFD",
     }


creSingleCharEsc = re.compile(r"(?P<pbs>\\*)(?P<escChar>\\[iIcC])")
                                      
substSingleCharEscDict = {             
     r"\i": ur"_:\u0041-\u005A\u0061-\u007A\u00C0-\u00D6\u00D8-\u00F6\u00F8-\u00FF\u0100-\u0131\u0134-\u013E\u0141-\u0148\u014A-\u017E\u0180-\u01C3\u01CD-\u01F0\u01F4-\u01F5\u01FA-\u0217\u0250-\u02A8\u02BB-\u02C1\u0386\u0388-\u038A\u038C\u038E-\u03A1\u03A3-\u03CE\u03D0-\u03D6\u03DA\u03DC\u03DE\u03E0\u03E2-\u03F3\u0401-\u040C\u040E-\u044F\u0451-\u045C\u045E-\u0481\u0490-\u04C4\u04C7-\u04C8\u04CB-\u04CC\u04D0-\u04EB\u04EE-\u04F5\u04F8-\u04F9\u0531-\u0556\u0559\u0561-\u0586\u05D0-\u05EA\u05F0-\u05F2\u0621-\u063A\u0641-\u064A\u0671-\u06B7\u06BA-\u06BE\u06C0-\u06CE\u06D0-\u06D3\u06D5\u06E5-\u06E6\u0905-\u0939\u093D\u0958-\u0961\u0985-\u098C\u098F-\u0990\u0993-\u09A8\u09AA-\u09B0\u09B2\u09B6-\u09B9\u09DC-\u09DD\u09DF-\u09E1\u09F0-\u09F1\u0A05-\u0A0A\u0A0F-\u0A10\u0A13-\u0A28\u0A2A-\u0A30\u0A32-\u0A33\u0A35-\u0A36\u0A38-\u0A39\u0A59-\u0A5C\u0A5E\u0A72-\u0A74\u0A85-\u0A8B\u0A8D\u0A8F-\u0A91\u0A93-\u0AA8\u0AAA-\u0AB0\u0AB2-\u0AB3\u0AB5-\u0AB9\u0ABD\u0AE0\u0B05-\u0B0C\u0B0F-\u0B10\u0B13-\u0B28\u0B2A-\u0B30\u0B32-\u0B33\u0B36-\u0B39\u0B3D\u0B5C-\u0B5D\u0B5F-\u0B61\u0B85-\u0B8A\u0B8E-\u0B90\u0B92-\u0B95\u0B99-\u0B9A\u0B9C\u0B9E-\u0B9F\u0BA3-\u0BA4\u0BA8-\u0BAA\u0BAE-\u0BB5\u0BB7-\u0BB9\u0C05-\u0C0C\u0C0E-\u0C10\u0C12-\u0C28\u0C2A-\u0C33\u0C35-\u0C39\u0C60-\u0C61\u0C85-\u0C8C\u0C8E-\u0C90\u0C92-\u0CA8\u0CAA-\u0CB3\u0CB5-\u0CB9\u0CDE\u0CE0-\u0CE1\u0D05-\u0D0C\u0D0E-\u0D10\u0D12-\u0D28\u0D2A-\u0D39\u0D60-\u0D61\u0E01-\u0E2E\u0E30\u0E32-\u0E33\u0E40-\u0E45\u0E81-\u0E82\u0E84\u0E87-\u0E88\u0E8A\u0E8D\u0E94-\u0E97\u0E99-\u0E9F\u0EA1-\u0EA3\u0EA5\u0EA7\u0EAA-\u0EAB\u0EAD-\u0EAE\u0EB0\u0EB2-\u0EB3\u0EBD\u0EC0-\u0EC4\u0F40-\u0F47\u0F49-\u0F69\u10A0-\u10C5\u10D0-\u10F6\u1100\u1102-\u1103\u1105-\u1107\u1109\u110B-\u110C\u110E-\u1112\u113C\u113E\u1140\u114C\u114E\u1150\u1154-\u1155\u1159\u115F-\u1161\u1163\u1165\u1167\u1169\u116D-\u116E\u1172-\u1173\u1175\u119E\u11A8\u11AB\u11AE-\u11AF\u11B7-\u11B8\u11BA\u11BC-\u11C2\u11EB\u11F0\u11F9\u1E00-\u1E9B\u1EA0-\u1EF9\u1F00-\u1F15\u1F18-\u1F1D\u1F20-\u1F45\u1F48-\u1F4D\u1F50-\u1F57\u1F59\u1F5B\u1F5D\u1F5F-\u1F7D\u1F80-\u1FB4\u1FB6-\u1FBC\u1FBE\u1FC2-\u1FC4\u1FC6-\u1FCC\u1FD0-\u1FD3\u1FD6-\u1FDB\u1FE0-\u1FEC\u1FF2-\u1FF4\u1FF6-\u1FFC\u2126\u212A-\u212B\u212E\u2180-\u2182\u3007\u3021-\u3029\u3041-\u3094\u30A1-\u30FA\u3105-\u312C\u4E00-\u9FA5\uAC00-\uD7A3",           
     r"\I": ur"^_:\u0041-\u005A\u0061-\u007A\u00C0-\u00D6\u00D8-\u00F6\u00F8-\u00FF\u0100-\u0131\u0134-\u013E\u0141-\u0148\u014A-\u017E\u0180-\u01C3\u01CD-\u01F0\u01F4-\u01F5\u01FA-\u0217\u0250-\u02A8\u02BB-\u02C1\u0386\u0388-\u038A\u038C\u038E-\u03A1\u03A3-\u03CE\u03D0-\u03D6\u03DA\u03DC\u03DE\u03E0\u03E2-\u03F3\u0401-\u040C\u040E-\u044F\u0451-\u045C\u045E-\u0481\u0490-\u04C4\u04C7-\u04C8\u04CB-\u04CC\u04D0-\u04EB\u04EE-\u04F5\u04F8-\u04F9\u0531-\u0556\u0559\u0561-\u0586\u05D0-\u05EA\u05F0-\u05F2\u0621-\u063A\u0641-\u064A\u0671-\u06B7\u06BA-\u06BE\u06C0-\u06CE\u06D0-\u06D3\u06D5\u06E5-\u06E6\u0905-\u0939\u093D\u0958-\u0961\u0985-\u098C\u098F-\u0990\u0993-\u09A8\u09AA-\u09B0\u09B2\u09B6-\u09B9\u09DC-\u09DD\u09DF-\u09E1\u09F0-\u09F1\u0A05-\u0A0A\u0A0F-\u0A10\u0A13-\u0A28\u0A2A-\u0A30\u0A32-\u0A33\u0A35-\u0A36\u0A38-\u0A39\u0A59-\u0A5C\u0A5E\u0A72-\u0A74\u0A85-\u0A8B\u0A8D\u0A8F-\u0A91\u0A93-\u0AA8\u0AAA-\u0AB0\u0AB2-\u0AB3\u0AB5-\u0AB9\u0ABD\u0AE0\u0B05-\u0B0C\u0B0F-\u0B10\u0B13-\u0B28\u0B2A-\u0B30\u0B32-\u0B33\u0B36-\u0B39\u0B3D\u0B5C-\u0B5D\u0B5F-\u0B61\u0B85-\u0B8A\u0B8E-\u0B90\u0B92-\u0B95\u0B99-\u0B9A\u0B9C\u0B9E-\u0B9F\u0BA3-\u0BA4\u0BA8-\u0BAA\u0BAE-\u0BB5\u0BB7-\u0BB9\u0C05-\u0C0C\u0C0E-\u0C10\u0C12-\u0C28\u0C2A-\u0C33\u0C35-\u0C39\u0C60-\u0C61\u0C85-\u0C8C\u0C8E-\u0C90\u0C92-\u0CA8\u0CAA-\u0CB3\u0CB5-\u0CB9\u0CDE\u0CE0-\u0CE1\u0D05-\u0D0C\u0D0E-\u0D10\u0D12-\u0D28\u0D2A-\u0D39\u0D60-\u0D61\u0E01-\u0E2E\u0E30\u0E32-\u0E33\u0E40-\u0E45\u0E81-\u0E82\u0E84\u0E87-\u0E88\u0E8A\u0E8D\u0E94-\u0E97\u0E99-\u0E9F\u0EA1-\u0EA3\u0EA5\u0EA7\u0EAA-\u0EAB\u0EAD-\u0EAE\u0EB0\u0EB2-\u0EB3\u0EBD\u0EC0-\u0EC4\u0F40-\u0F47\u0F49-\u0F69\u10A0-\u10C5\u10D0-\u10F6\u1100\u1102-\u1103\u1105-\u1107\u1109\u110B-\u110C\u110E-\u1112\u113C\u113E\u1140\u114C\u114E\u1150\u1154-\u1155\u1159\u115F-\u1161\u1163\u1165\u1167\u1169\u116D-\u116E\u1172-\u1173\u1175\u119E\u11A8\u11AB\u11AE-\u11AF\u11B7-\u11B8\u11BA\u11BC-\u11C2\u11EB\u11F0\u11F9\u1E00-\u1E9B\u1EA0-\u1EF9\u1F00-\u1F15\u1F18-\u1F1D\u1F20-\u1F45\u1F48-\u1F4D\u1F50-\u1F57\u1F59\u1F5B\u1F5D\u1F5F-\u1F7D\u1F80-\u1FB4\u1FB6-\u1FBC\u1FBE\u1FC2-\u1FC4\u1FC6-\u1FCC\u1FD0-\u1FD3\u1FD6-\u1FDB\u1FE0-\u1FEC\u1FF2-\u1FF4\u1FF6-\u1FFC\u2126\u212A-\u212B\u212E\u2180-\u2182\u3007\u3021-\u3029\u3041-\u3094\u30A1-\u30FA\u3105-\u312C\u4E00-\u9FA5\uAC00-\uD7A3",          
     r"\c": ur"_:\-.\u0041-\u005A\u0061-\u007A\u00C0-\u00D6\u00D8-\u00F6\u00F8-\u00FF\u0100-\u0131\u0134-\u013E\u0141-\u0148\u014A-\u017E\u0180-\u01C3\u01CD-\u01F0\u01F4-\u01F5\u01FA-\u0217\u0250-\u02A8\u02BB-\u02C1\u0386\u0388-\u038A\u038C\u038E-\u03A1\u03A3-\u03CE\u03D0-\u03D6\u03DA\u03DC\u03DE\u03E0\u03E2-\u03F3\u0401-\u040C\u040E-\u044F\u0451-\u045C\u045E-\u0481\u0490-\u04C4\u04C7-\u04C8\u04CB-\u04CC\u04D0-\u04EB\u04EE-\u04F5\u04F8-\u04F9\u0531-\u0556\u0559\u0561-\u0586\u05D0-\u05EA\u05F0-\u05F2\u0621-\u063A\u0641-\u064A\u0671-\u06B7\u06BA-\u06BE\u06C0-\u06CE\u06D0-\u06D3\u06D5\u06E5-\u06E6\u0905-\u0939\u093D\u0958-\u0961\u0985-\u098C\u098F-\u0990\u0993-\u09A8\u09AA-\u09B0\u09B2\u09B6-\u09B9\u09DC-\u09DD\u09DF-\u09E1\u09F0-\u09F1\u0A05-\u0A0A\u0A0F-\u0A10\u0A13-\u0A28\u0A2A-\u0A30\u0A32-\u0A33\u0A35-\u0A36\u0A38-\u0A39\u0A59-\u0A5C\u0A5E\u0A72-\u0A74\u0A85-\u0A8B\u0A8D\u0A8F-\u0A91\u0A93-\u0AA8\u0AAA-\u0AB0\u0AB2-\u0AB3\u0AB5-\u0AB9\u0ABD\u0AE0\u0B05-\u0B0C\u0B0F-\u0B10\u0B13-\u0B28\u0B2A-\u0B30\u0B32-\u0B33\u0B36-\u0B39\u0B3D\u0B5C-\u0B5D\u0B5F-\u0B61\u0B85-\u0B8A\u0B8E-\u0B90\u0B92-\u0B95\u0B99-\u0B9A\u0B9C\u0B9E-\u0B9F\u0BA3-\u0BA4\u0BA8-\u0BAA\u0BAE-\u0BB5\u0BB7-\u0BB9\u0C05-\u0C0C\u0C0E-\u0C10\u0C12-\u0C28\u0C2A-\u0C33\u0C35-\u0C39\u0C60-\u0C61\u0C85-\u0C8C\u0C8E-\u0C90\u0C92-\u0CA8\u0CAA-\u0CB3\u0CB5-\u0CB9\u0CDE\u0CE0-\u0CE1\u0D05-\u0D0C\u0D0E-\u0D10\u0D12-\u0D28\u0D2A-\u0D39\u0D60-\u0D61\u0E01-\u0E2E\u0E30\u0E32-\u0E33\u0E40-\u0E45\u0E81-\u0E82\u0E84\u0E87-\u0E88\u0E8A\u0E8D\u0E94-\u0E97\u0E99-\u0E9F\u0EA1-\u0EA3\u0EA5\u0EA7\u0EAA-\u0EAB\u0EAD-\u0EAE\u0EB0\u0EB2-\u0EB3\u0EBD\u0EC0-\u0EC4\u0F40-\u0F47\u0F49-\u0F69\u10A0-\u10C5\u10D0-\u10F6\u1100\u1102-\u1103\u1105-\u1107\u1109\u110B-\u110C\u110E-\u1112\u113C\u113E\u1140\u114C\u114E\u1150\u1154-\u1155\u1159\u115F-\u1161\u1163\u1165\u1167\u1169\u116D-\u116E\u1172-\u1173\u1175\u119E\u11A8\u11AB\u11AE-\u11AF\u11B7-\u11B8\u11BA\u11BC-\u11C2\u11EB\u11F0\u11F9\u1E00-\u1E9B\u1EA0-\u1EF9\u1F00-\u1F15\u1F18-\u1F1D\u1F20-\u1F45\u1F48-\u1F4D\u1F50-\u1F57\u1F59\u1F5B\u1F5D\u1F5F-\u1F7D\u1F80-\u1FB4\u1FB6-\u1FBC\u1FBE\u1FC2-\u1FC4\u1FC6-\u1FCC\u1FD0-\u1FD3\u1FD6-\u1FDB\u1FE0-\u1FEC\u1FF2-\u1FF4\u1FF6-\u1FFC\u2126\u212A-\u212B\u212E\u2180-\u2182\u3041-\u3094\u30A1-\u30FA\u3105-\u312C\uAC00-\uD7A3\u4E00-\u9FA5\u3007\u3021-\u3029\u0300-\u0345\u0360-\u0361\u0483-\u0486\u0591-\u05A1\u05A3-\u05B9\u05BB-\u05BD\u05BF\u05C1-\u05C2\u05C4\u064B-\u0652\u0670\u06D6-\u06DC\u06DD-\u06DF\u06E0-\u06E4\u06E7-\u06E8\u06EA-\u06ED\u0901-\u0903\u093C\u093E-\u094C\u094D\u0951-\u0954\u0962-\u0963\u0981-\u0983\u09BC\u09BE\u09BF\u09C0-\u09C4\u09C7-\u09C8\u09CB-\u09CD\u09D7\u09E2-\u09E3\u0A02\u0A3C\u0A3E\u0A3F\u0A40-\u0A42\u0A47-\u0A48\u0A4B-\u0A4D\u0A70-\u0A71\u0A81-\u0A83\u0ABC\u0ABE-\u0AC5\u0AC7-\u0AC9\u0ACB-\u0ACD\u0B01-\u0B03\u0B3C\u0B3E-\u0B43\u0B47-\u0B48\u0B4B-\u0B4D\u0B56-\u0B57\u0B82-\u0B83\u0BBE-\u0BC2\u0BC6-\u0BC8\u0BCA-\u0BCD\u0BD7\u0C01-\u0C03\u0C3E-\u0C44\u0C46-\u0C48\u0C4A-\u0C4D\u0C55-\u0C56\u0C82-\u0C83\u0CBE-\u0CC4\u0CC6-\u0CC8\u0CCA-\u0CCD\u0CD5-\u0CD6\u0D02-\u0D03\u0D3E-\u0D43\u0D46-\u0D48\u0D4A-\u0D4D\u0D57\u0E31\u0E34-\u0E3A\u0E47-\u0E4E\u0EB1\u0EB4-\u0EB9\u0EBB-\u0EBC\u0EC8-\u0ECD\u0F18-\u0F19\u0F35\u0F37\u0F39\u0F3E\u0F3F\u0F71-\u0F84\u0F86-\u0F8B\u0F90-\u0F95\u0F97\u0F99-\u0FAD\u0FB1-\u0FB7\u0FB9\u20D0-\u20DC\u20E1\u302A-\u302F\u3099\u309A\u0030-\u0039\u0660-\u0669\u06F0-\u06F9\u0966-\u096F\u09E6-\u09EF\u0A66-\u0A6F\u0AE6-\u0AEF\u0B66-\u0B6F\u0BE7-\u0BEF\u0C66-\u0C6F\u0CE6-\u0CEF\u0D66-\u0D6F\u0E50-\u0E59\u0ED0-\u0ED9\u0F20-\u0F29\u00B7\u02D0\u02D1\u0387\u0640\u0E46\u0EC6\u3005\u3031-\u3035\u309D-\u309E\u30FC-\u30FE",             
     r"\C": ur"^_:\-.\u0041-\u005A\u0061-\u007A\u00C0-\u00D6\u00D8-\u00F6\u00F8-\u00FF\u0100-\u0131\u0134-\u013E\u0141-\u0148\u014A-\u017E\u0180-\u01C3\u01CD-\u01F0\u01F4-\u01F5\u01FA-\u0217\u0250-\u02A8\u02BB-\u02C1\u0386\u0388-\u038A\u038C\u038E-\u03A1\u03A3-\u03CE\u03D0-\u03D6\u03DA\u03DC\u03DE\u03E0\u03E2-\u03F3\u0401-\u040C\u040E-\u044F\u0451-\u045C\u045E-\u0481\u0490-\u04C4\u04C7-\u04C8\u04CB-\u04CC\u04D0-\u04EB\u04EE-\u04F5\u04F8-\u04F9\u0531-\u0556\u0559\u0561-\u0586\u05D0-\u05EA\u05F0-\u05F2\u0621-\u063A\u0641-\u064A\u0671-\u06B7\u06BA-\u06BE\u06C0-\u06CE\u06D0-\u06D3\u06D5\u06E5-\u06E6\u0905-\u0939\u093D\u0958-\u0961\u0985-\u098C\u098F-\u0990\u0993-\u09A8\u09AA-\u09B0\u09B2\u09B6-\u09B9\u09DC-\u09DD\u09DF-\u09E1\u09F0-\u09F1\u0A05-\u0A0A\u0A0F-\u0A10\u0A13-\u0A28\u0A2A-\u0A30\u0A32-\u0A33\u0A35-\u0A36\u0A38-\u0A39\u0A59-\u0A5C\u0A5E\u0A72-\u0A74\u0A85-\u0A8B\u0A8D\u0A8F-\u0A91\u0A93-\u0AA8\u0AAA-\u0AB0\u0AB2-\u0AB3\u0AB5-\u0AB9\u0ABD\u0AE0\u0B05-\u0B0C\u0B0F-\u0B10\u0B13-\u0B28\u0B2A-\u0B30\u0B32-\u0B33\u0B36-\u0B39\u0B3D\u0B5C-\u0B5D\u0B5F-\u0B61\u0B85-\u0B8A\u0B8E-\u0B90\u0B92-\u0B95\u0B99-\u0B9A\u0B9C\u0B9E-\u0B9F\u0BA3-\u0BA4\u0BA8-\u0BAA\u0BAE-\u0BB5\u0BB7-\u0BB9\u0C05-\u0C0C\u0C0E-\u0C10\u0C12-\u0C28\u0C2A-\u0C33\u0C35-\u0C39\u0C60-\u0C61\u0C85-\u0C8C\u0C8E-\u0C90\u0C92-\u0CA8\u0CAA-\u0CB3\u0CB5-\u0CB9\u0CDE\u0CE0-\u0CE1\u0D05-\u0D0C\u0D0E-\u0D10\u0D12-\u0D28\u0D2A-\u0D39\u0D60-\u0D61\u0E01-\u0E2E\u0E30\u0E32-\u0E33\u0E40-\u0E45\u0E81-\u0E82\u0E84\u0E87-\u0E88\u0E8A\u0E8D\u0E94-\u0E97\u0E99-\u0E9F\u0EA1-\u0EA3\u0EA5\u0EA7\u0EAA-\u0EAB\u0EAD-\u0EAE\u0EB0\u0EB2-\u0EB3\u0EBD\u0EC0-\u0EC4\u0F40-\u0F47\u0F49-\u0F69\u10A0-\u10C5\u10D0-\u10F6\u1100\u1102-\u1103\u1105-\u1107\u1109\u110B-\u110C\u110E-\u1112\u113C\u113E\u1140\u114C\u114E\u1150\u1154-\u1155\u1159\u115F-\u1161\u1163\u1165\u1167\u1169\u116D-\u116E\u1172-\u1173\u1175\u119E\u11A8\u11AB\u11AE-\u11AF\u11B7-\u11B8\u11BA\u11BC-\u11C2\u11EB\u11F0\u11F9\u1E00-\u1E9B\u1EA0-\u1EF9\u1F00-\u1F15\u1F18-\u1F1D\u1F20-\u1F45\u1F48-\u1F4D\u1F50-\u1F57\u1F59\u1F5B\u1F5D\u1F5F-\u1F7D\u1F80-\u1FB4\u1FB6-\u1FBC\u1FBE\u1FC2-\u1FC4\u1FC6-\u1FCC\u1FD0-\u1FD3\u1FD6-\u1FDB\u1FE0-\u1FEC\u1FF2-\u1FF4\u1FF6-\u1FFC\u2126\u212A-\u212B\u212E\u2180-\u2182\u3041-\u3094\u30A1-\u30FA\u3105-\u312C\uAC00-\uD7A3\u4E00-\u9FA5\u3007\u3021-\u3029\u0300-\u0345\u0360-\u0361\u0483-\u0486\u0591-\u05A1\u05A3-\u05B9\u05BB-\u05BD\u05BF\u05C1-\u05C2\u05C4\u064B-\u0652\u0670\u06D6-\u06DC\u06DD-\u06DF\u06E0-\u06E4\u06E7-\u06E8\u06EA-\u06ED\u0901-\u0903\u093C\u093E-\u094C\u094D\u0951-\u0954\u0962-\u0963\u0981-\u0983\u09BC\u09BE\u09BF\u09C0-\u09C4\u09C7-\u09C8\u09CB-\u09CD\u09D7\u09E2-\u09E3\u0A02\u0A3C\u0A3E\u0A3F\u0A40-\u0A42\u0A47-\u0A48\u0A4B-\u0A4D\u0A70-\u0A71\u0A81-\u0A83\u0ABC\u0ABE-\u0AC5\u0AC7-\u0AC9\u0ACB-\u0ACD\u0B01-\u0B03\u0B3C\u0B3E-\u0B43\u0B47-\u0B48\u0B4B-\u0B4D\u0B56-\u0B57\u0B82-\u0B83\u0BBE-\u0BC2\u0BC6-\u0BC8\u0BCA-\u0BCD\u0BD7\u0C01-\u0C03\u0C3E-\u0C44\u0C46-\u0C48\u0C4A-\u0C4D\u0C55-\u0C56\u0C82-\u0C83\u0CBE-\u0CC4\u0CC6-\u0CC8\u0CCA-\u0CCD\u0CD5-\u0CD6\u0D02-\u0D03\u0D3E-\u0D43\u0D46-\u0D48\u0D4A-\u0D4D\u0D57\u0E31\u0E34-\u0E3A\u0E47-\u0E4E\u0EB1\u0EB4-\u0EB9\u0EBB-\u0EBC\u0EC8-\u0ECD\u0F18-\u0F19\u0F35\u0F37\u0F39\u0F3E\u0F3F\u0F71-\u0F84\u0F86-\u0F8B\u0F90-\u0F95\u0F97\u0F99-\u0FAD\u0FB1-\u0FB7\u0FB9\u20D0-\u20DC\u20E1\u302A-\u302F\u3099\u309A\u0030-\u0039\u0660-\u0669\u06F0-\u06F9\u0966-\u096F\u09E6-\u09EF\u0A66-\u0A6F\u0AE6-\u0AEF\u0B66-\u0B6F\u0BE7-\u0BEF\u0C66-\u0C6F\u0CE6-\u0CEF\u0D66-\u0D6F\u0E50-\u0E59\u0ED0-\u0ED9\u0F20-\u0F29\u00B7\u02D0\u02D1\u0387\u0640\u0E46\u0EC6\u3005\u3031-\u3035\u309D-\u309E\u30FC-\u30FE",            
      }

substSpecialEscList = (             
     (r"[\i-[:]]", ur"[_\u0041-\u005A\u0061-\u007A\u00C0-\u00D6\u00D8-\u00F6\u00F8-\u00FF\u0100-\u0131\u0134-\u013E\u0141-\u0148\u014A-\u017E\u0180-\u01C3\u01CD-\u01F0\u01F4-\u01F5\u01FA-\u0217\u0250-\u02A8\u02BB-\u02C1\u0386\u0388-\u038A\u038C\u038E-\u03A1\u03A3-\u03CE\u03D0-\u03D6\u03DA\u03DC\u03DE\u03E0\u03E2-\u03F3\u0401-\u040C\u040E-\u044F\u0451-\u045C\u045E-\u0481\u0490-\u04C4\u04C7-\u04C8\u04CB-\u04CC\u04D0-\u04EB\u04EE-\u04F5\u04F8-\u04F9\u0531-\u0556\u0559\u0561-\u0586\u05D0-\u05EA\u05F0-\u05F2\u0621-\u063A\u0641-\u064A\u0671-\u06B7\u06BA-\u06BE\u06C0-\u06CE\u06D0-\u06D3\u06D5\u06E5-\u06E6\u0905-\u0939\u093D\u0958-\u0961\u0985-\u098C\u098F-\u0990\u0993-\u09A8\u09AA-\u09B0\u09B2\u09B6-\u09B9\u09DC-\u09DD\u09DF-\u09E1\u09F0-\u09F1\u0A05-\u0A0A\u0A0F-\u0A10\u0A13-\u0A28\u0A2A-\u0A30\u0A32-\u0A33\u0A35-\u0A36\u0A38-\u0A39\u0A59-\u0A5C\u0A5E\u0A72-\u0A74\u0A85-\u0A8B\u0A8D\u0A8F-\u0A91\u0A93-\u0AA8\u0AAA-\u0AB0\u0AB2-\u0AB3\u0AB5-\u0AB9\u0ABD\u0AE0\u0B05-\u0B0C\u0B0F-\u0B10\u0B13-\u0B28\u0B2A-\u0B30\u0B32-\u0B33\u0B36-\u0B39\u0B3D\u0B5C-\u0B5D\u0B5F-\u0B61\u0B85-\u0B8A\u0B8E-\u0B90\u0B92-\u0B95\u0B99-\u0B9A\u0B9C\u0B9E-\u0B9F\u0BA3-\u0BA4\u0BA8-\u0BAA\u0BAE-\u0BB5\u0BB7-\u0BB9\u0C05-\u0C0C\u0C0E-\u0C10\u0C12-\u0C28\u0C2A-\u0C33\u0C35-\u0C39\u0C60-\u0C61\u0C85-\u0C8C\u0C8E-\u0C90\u0C92-\u0CA8\u0CAA-\u0CB3\u0CB5-\u0CB9\u0CDE\u0CE0-\u0CE1\u0D05-\u0D0C\u0D0E-\u0D10\u0D12-\u0D28\u0D2A-\u0D39\u0D60-\u0D61\u0E01-\u0E2E\u0E30\u0E32-\u0E33\u0E40-\u0E45\u0E81-\u0E82\u0E84\u0E87-\u0E88\u0E8A\u0E8D\u0E94-\u0E97\u0E99-\u0E9F\u0EA1-\u0EA3\u0EA5\u0EA7\u0EAA-\u0EAB\u0EAD-\u0EAE\u0EB0\u0EB2-\u0EB3\u0EBD\u0EC0-\u0EC4\u0F40-\u0F47\u0F49-\u0F69\u10A0-\u10C5\u10D0-\u10F6\u1100\u1102-\u1103\u1105-\u1107\u1109\u110B-\u110C\u110E-\u1112\u113C\u113E\u1140\u114C\u114E\u1150\u1154-\u1155\u1159\u115F-\u1161\u1163\u1165\u1167\u1169\u116D-\u116E\u1172-\u1173\u1175\u119E\u11A8\u11AB\u11AE-\u11AF\u11B7-\u11B8\u11BA\u11BC-\u11C2\u11EB\u11F0\u11F9\u1E00-\u1E9B\u1EA0-\u1EF9\u1F00-\u1F15\u1F18-\u1F1D\u1F20-\u1F45\u1F48-\u1F4D\u1F50-\u1F57\u1F59\u1F5B\u1F5D\u1F5F-\u1F7D\u1F80-\u1FB4\u1FB6-\u1FBC\u1FBE\u1FC2-\u1FC4\u1FC6-\u1FCC\u1FD0-\u1FD3\u1FD6-\u1FDB\u1FE0-\u1FEC\u1FF2-\u1FF4\u1FF6-\u1FFC\u2126\u212A-\u212B\u212E\u2180-\u2182\u3007\u3021-\u3029\u3041-\u3094\u30A1-\u30FA\u3105-\u312C\u4E00-\u9FA5\uAC00-\uD7A3]"),           
     (r"[\c-[:]]", ur"[_\-.\u0041-\u005A\u0061-\u007A\u00C0-\u00D6\u00D8-\u00F6\u00F8-\u00FF\u0100-\u0131\u0134-\u013E\u0141-\u0148\u014A-\u017E\u0180-\u01C3\u01CD-\u01F0\u01F4-\u01F5\u01FA-\u0217\u0250-\u02A8\u02BB-\u02C1\u0386\u0388-\u038A\u038C\u038E-\u03A1\u03A3-\u03CE\u03D0-\u03D6\u03DA\u03DC\u03DE\u03E0\u03E2-\u03F3\u0401-\u040C\u040E-\u044F\u0451-\u045C\u045E-\u0481\u0490-\u04C4\u04C7-\u04C8\u04CB-\u04CC\u04D0-\u04EB\u04EE-\u04F5\u04F8-\u04F9\u0531-\u0556\u0559\u0561-\u0586\u05D0-\u05EA\u05F0-\u05F2\u0621-\u063A\u0641-\u064A\u0671-\u06B7\u06BA-\u06BE\u06C0-\u06CE\u06D0-\u06D3\u06D5\u06E5-\u06E6\u0905-\u0939\u093D\u0958-\u0961\u0985-\u098C\u098F-\u0990\u0993-\u09A8\u09AA-\u09B0\u09B2\u09B6-\u09B9\u09DC-\u09DD\u09DF-\u09E1\u09F0-\u09F1\u0A05-\u0A0A\u0A0F-\u0A10\u0A13-\u0A28\u0A2A-\u0A30\u0A32-\u0A33\u0A35-\u0A36\u0A38-\u0A39\u0A59-\u0A5C\u0A5E\u0A72-\u0A74\u0A85-\u0A8B\u0A8D\u0A8F-\u0A91\u0A93-\u0AA8\u0AAA-\u0AB0\u0AB2-\u0AB3\u0AB5-\u0AB9\u0ABD\u0AE0\u0B05-\u0B0C\u0B0F-\u0B10\u0B13-\u0B28\u0B2A-\u0B30\u0B32-\u0B33\u0B36-\u0B39\u0B3D\u0B5C-\u0B5D\u0B5F-\u0B61\u0B85-\u0B8A\u0B8E-\u0B90\u0B92-\u0B95\u0B99-\u0B9A\u0B9C\u0B9E-\u0B9F\u0BA3-\u0BA4\u0BA8-\u0BAA\u0BAE-\u0BB5\u0BB7-\u0BB9\u0C05-\u0C0C\u0C0E-\u0C10\u0C12-\u0C28\u0C2A-\u0C33\u0C35-\u0C39\u0C60-\u0C61\u0C85-\u0C8C\u0C8E-\u0C90\u0C92-\u0CA8\u0CAA-\u0CB3\u0CB5-\u0CB9\u0CDE\u0CE0-\u0CE1\u0D05-\u0D0C\u0D0E-\u0D10\u0D12-\u0D28\u0D2A-\u0D39\u0D60-\u0D61\u0E01-\u0E2E\u0E30\u0E32-\u0E33\u0E40-\u0E45\u0E81-\u0E82\u0E84\u0E87-\u0E88\u0E8A\u0E8D\u0E94-\u0E97\u0E99-\u0E9F\u0EA1-\u0EA3\u0EA5\u0EA7\u0EAA-\u0EAB\u0EAD-\u0EAE\u0EB0\u0EB2-\u0EB3\u0EBD\u0EC0-\u0EC4\u0F40-\u0F47\u0F49-\u0F69\u10A0-\u10C5\u10D0-\u10F6\u1100\u1102-\u1103\u1105-\u1107\u1109\u110B-\u110C\u110E-\u1112\u113C\u113E\u1140\u114C\u114E\u1150\u1154-\u1155\u1159\u115F-\u1161\u1163\u1165\u1167\u1169\u116D-\u116E\u1172-\u1173\u1175\u119E\u11A8\u11AB\u11AE-\u11AF\u11B7-\u11B8\u11BA\u11BC-\u11C2\u11EB\u11F0\u11F9\u1E00-\u1E9B\u1EA0-\u1EF9\u1F00-\u1F15\u1F18-\u1F1D\u1F20-\u1F45\u1F48-\u1F4D\u1F50-\u1F57\u1F59\u1F5B\u1F5D\u1F5F-\u1F7D\u1F80-\u1FB4\u1FB6-\u1FBC\u1FBE\u1FC2-\u1FC4\u1FC6-\u1FCC\u1FD0-\u1FD3\u1FD6-\u1FDB\u1FE0-\u1FEC\u1FF2-\u1FF4\u1FF6-\u1FFC\u2126\u212A-\u212B\u212E\u2180-\u2182\u3041-\u3094\u30A1-\u30FA\u3105-\u312C\uAC00-\uD7A3\u4E00-\u9FA5\u3007\u3021-\u3029\u0300-\u0345\u0360-\u0361\u0483-\u0486\u0591-\u05A1\u05A3-\u05B9\u05BB-\u05BD\u05BF\u05C1-\u05C2\u05C4\u064B-\u0652\u0670\u06D6-\u06DC\u06DD-\u06DF\u06E0-\u06E4\u06E7-\u06E8\u06EA-\u06ED\u0901-\u0903\u093C\u093E-\u094C\u094D\u0951-\u0954\u0962-\u0963\u0981-\u0983\u09BC\u09BE\u09BF\u09C0-\u09C4\u09C7-\u09C8\u09CB-\u09CD\u09D7\u09E2-\u09E3\u0A02\u0A3C\u0A3E\u0A3F\u0A40-\u0A42\u0A47-\u0A48\u0A4B-\u0A4D\u0A70-\u0A71\u0A81-\u0A83\u0ABC\u0ABE-\u0AC5\u0AC7-\u0AC9\u0ACB-\u0ACD\u0B01-\u0B03\u0B3C\u0B3E-\u0B43\u0B47-\u0B48\u0B4B-\u0B4D\u0B56-\u0B57\u0B82-\u0B83\u0BBE-\u0BC2\u0BC6-\u0BC8\u0BCA-\u0BCD\u0BD7\u0C01-\u0C03\u0C3E-\u0C44\u0C46-\u0C48\u0C4A-\u0C4D\u0C55-\u0C56\u0C82-\u0C83\u0CBE-\u0CC4\u0CC6-\u0CC8\u0CCA-\u0CCD\u0CD5-\u0CD6\u0D02-\u0D03\u0D3E-\u0D43\u0D46-\u0D48\u0D4A-\u0D4D\u0D57\u0E31\u0E34-\u0E3A\u0E47-\u0E4E\u0EB1\u0EB4-\u0EB9\u0EBB-\u0EBC\u0EC8-\u0ECD\u0F18-\u0F19\u0F35\u0F37\u0F39\u0F3E\u0F3F\u0F71-\u0F84\u0F86-\u0F8B\u0F90-\u0F95\u0F97\u0F99-\u0FAD\u0FB1-\u0FB7\u0FB9\u20D0-\u20DC\u20E1\u302A-\u302F\u3099\u309A\u0030-\u0039\u0660-\u0669\u06F0-\u06F9\u0966-\u096F\u09E6-\u09EF\u0A66-\u0A6F\u0AE6-\u0AEF\u0B66-\u0B6F\u0BE7-\u0BEF\u0C66-\u0C6F\u0CE6-\u0CEF\u0D66-\u0D6F\u0E50-\u0E59\u0ED0-\u0ED9\u0F20-\u0F29\u00B7\u02D0\u02D1\u0387\u0640\u0E46\u0EC6\u3005\u3031-\u3035\u309D-\u309E\u30FC-\u30FE]"),
     )

########################################
# substitute some multichar escape characters
# which are not handled by the standard python re module
#
def substituteSpecialEscChars (intRePattern):
    for specialEsc, repl in substSpecialEscList:
        intRePattern = string.replace(intRePattern, specialEsc, repl)

    substituteDict = {}
    for regexObj in creMultiCharEscP.finditer(intRePattern):
        if not (len(regexObj.group('pbs')) & 1): # even number of preceding backslashes
            id = regexObj.group('id')
            pP = regexObj.group('pP')
            if not substMultiCharEscPDict.has_key(id):
                raise SyntaxError, r"Unknown MultiCharEscape sequence '\%s{%s}' found!" %(pP, id)
            else:
                inv = 0
                invstr = ""
                if pP == "P": inv ^= 1
                if regexObj.group('inv') == '^': 
                    inv ^= 1
                if inv: invstr = "^"
                if creWithinSet.match(intRePattern[:regexObj.start("escSeq")]):
                    substituteDict[(regexObj.start("escSeq"), regexObj.end("escSeq"))] = ur"%s%s" %(invstr, substMultiCharEscPDict[id])
                else:
                    substituteDict[(regexObj.start("escSeq"), regexObj.end("escSeq"))] = ur"[%s%s]" %(invstr, substMultiCharEscPDict[id])

    for regexObj in creSingleCharEsc.finditer(intRePattern):
        if not (len(regexObj.group('pbs')) & 1): # even number of preceding backslashes
            foundStr = regexObj.group("escChar")
            if not substSingleCharEscDict.has_key(foundStr):
                raise SyntaxError, "Unknown SingleCharEscape sequence '%s' found!" %(foundStr)
            else:
                regexObjWithinSet = creWithinSet.match(intRePattern[:regexObj.start("escChar")])
                if regexObjWithinSet:
                    substituteDict[(regexObj.start("escChar"), regexObj.end("escChar"))] = ur"%s" %substSingleCharEscDict[foundStr]
                else:
                    substituteDict[(regexObj.start("escChar"), regexObj.end("escChar"))] = ur"[%s]" %substSingleCharEscDict[foundStr]

    if substituteDict != {}:
        strFragList = []
        lastPos = 0
        keyList = substituteDict.keys()
        keyList.sort()
        for startPos, endPos in keyList:
            strFragList.append(intRePattern[lastPos:startPos])
            strFragList.append(substituteDict[(startPos,endPos)])
            lastPos = endPos
        strFragList.append(intRePattern[lastPos:])
        expandedPattern = "".join(strFragList)
    else:
        expandedPattern = intRePattern
        
    return expandedPattern


########NEW FILE########
__FILENAME__ = xsvalXmlIf
#
# minixsv, Release 0.9.0
# file: xsvalXmlIf.py
#
# XML interface classes (derived wrapper classes)
#
# history:
# 2007-07-04 rl   created
#
# Copyright (c) 2004-2008 by Roland Leuthe.  All rights reserved.
#
# --------------------------------------------------------------------
# The minixsv XML schema validator is
#
# Copyright (c) 2004-2008 by Roland Leuthe
#
# By obtaining, using, and/or copying this software and/or its
# associated documentation, you agree that you have read, understood,
# and will comply with the following terms and conditions:
#
# Permission to use, copy, modify, and distribute this software and
# its associated documentation for any purpose and without fee is
# hereby granted, provided that the above copyright notice appears in
# all copies, and that both that copyright notice and this permission
# notice appear in supporting documentation, and that the name of
# the author not be used in advertising or publicity
# pertaining to distribution of the software without specific, written
# prior permission.
#
# THE AUTHOR DISCLAIMS ALL WARRANTIES WITH REGARD
# TO THIS SOFTWARE, INCLUDING ALL IMPLIED WARRANTIES OF MERCHANT-
# ABILITY AND FITNESS.  IN NO EVENT SHALL THE AUTHOR
# BE LIABLE FOR ANY SPECIAL, INDIRECT OR CONSEQUENTIAL DAMAGES OR ANY
# DAMAGES WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS,
# WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS
# ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR PERFORMANCE
# OF THIS SOFTWARE.
# --------------------------------------------------------------------


from types import TupleType
from ..genxmlif.xmlifApi   import XmlElementWrapper


class XsvXmlElementWrapper (XmlElementWrapper):
    
#++++++++++++ special XSD validation support ++++++++++++++++++++
    def __init__(self, element, treeWrapper, curNs=[], initAttrSeq=1):
        XmlElementWrapper.__init__(self, element, treeWrapper, curNs, initAttrSeq)
        self.schemaRootNode = None
        self.xsdNode = None
        self.xsdAttrNodes = {}

    
    def cloneNode(self, deep, cloneCallback=None):
        return XmlElementWrapper.cloneNode(self, deep, self.cloneCallback)


    def cloneCallback(self, nodeCopy):
        nodeCopy.schemaRootNode = self.schemaRootNode
        nodeCopy.xsdNode = self.xsdNode
        nodeCopy.xsdAttrNodes = self.xsdAttrNodes.copy()


    def getSchemaRootNode (self):
        """Retrieve XML schema root node which this element node belongs to
           (e.g. for accessing target namespace attribute).
        
        Returns XML schema root node which this element node belongs to
        """
        return self.schemaRootNode
    

    def setSchemaRootNode (self, schemaRootNode):
        """Store XML schema root node which this element node belongs to.
        
        Input parameter:
            schemaRootNode:    schema root node which this element node belongs to
        """
        self.schemaRootNode = schemaRootNode


    def getXsdNode (self):
        """Retrieve XML schema node responsible for this element node.
        
        Returns XML schema node responsible for this element node.
        """
        return self.xsdNode
    

    def setXsdNode (self, xsdNode):
        """Store XML schema node responsible for this element node.
        
        Input parameter:
            xsdNode:    responsible XML schema ElementWrapper
        """
        self.xsdNode = xsdNode


    def getXsdAttrNode (self, tupleOrAttrName):
        """Retrieve XML schema node responsible for the requested attribute.

        Input parameter:
            tupleOrAttrName:  tuple '(namespace, attributeName)' or 'attributeName' if no namespace is used
        Returns XML schema node responsible for the requested attribute.
        """
        try:
            return self.xsdAttrNodes[tupleOrAttrName]
        except:
            if isinstance(tupleOrAttrName, TupleType):
                if tupleOrAttrName[1] == '*' and len(self.xsdAttrNodes) == 1:
                    return self.xsdAttrNodes.values()[0]
            return None
    

    def setXsdAttrNode (self, tupleOrAttrName, xsdAttrNode):
        """Store XML schema node responsible for the given attribute.
        
        Input parameter:
            tupleOrAttrName:  tuple '(namespace, attributeName)' or 'attributeName' if no namespace is used
            xsdAttrNode:      responsible XML schema ElementWrapper
        """
        self.xsdAttrNodes[tupleOrAttrName] = xsdAttrNode



########NEW FILE########
__FILENAME__ = mavcrc
'''MAVLink X25 CRC code'''


class x25crc(object):
    '''x25 CRC - based on checksum.h from mavlink library'''
    def __init__(self, buf=''):
        self.crc = 0xffff
        self.accumulate(buf)

    def accumulate(self, buf):
        '''add in some more bytes'''
        import array
        bytes = array.array('B')
        if isinstance(buf, array.array):
            bytes.extend(buf)
        else:
            bytes.fromstring(buf)
        accum = self.crc
        for b in bytes:
            tmp = b ^ (accum & 0xff)
            tmp = (tmp ^ (tmp<<4)) & 0xFF
            accum = (accum>>8) ^ (tmp<<8) ^ (tmp<<3) ^ (tmp>>4)
            accum = accum & 0xFFFF
        self.crc = accum


########NEW FILE########
__FILENAME__ = mavgen
#!/usr/bin/env python

'''
parse a MAVLink protocol XML file and generate a python implementation

Copyright Andrew Tridgell 2011
Released under GNU GPL version 3 or later

'''
import sys, textwrap, os
try:
    from . import mavparse
except Exception:
    from pymavlink.generator import mavparse

try:
    from lib.genxmlif import GenXmlIfError
    from lib.minixsv import pyxsval
    performValidation = True
except Exception:
    print("Unable to load XML validator libraries. XML validation will not be performed")
    performValidation = False
    
# XSD schema file
schemaFile = os.path.join(os.path.dirname(os.path.realpath(__file__)), "mavschema.xsd")


def mavgen(opts, args) :
    """Generate mavlink message formatters and parsers (C and Python ) using options
    and args where args are a list of xml files. This function allows python
    scripts under Windows to control mavgen using the same interface as
    shell scripts under Unix"""

    xml = []

    for fname in args:
        if performValidation:
            print("Validating %s" % fname)
            mavgen_validate(fname, schemaFile, opts.error_limit);
        else:
            print("Validation skipped for %s." % fname)

        print("Parsing %s" % fname)
        xml.append(mavparse.MAVXML(fname, opts.wire_protocol))

    # expand includes
    for x in xml[:]:
        for i in x.include:
            fname = os.path.join(os.path.dirname(x.filename), i)

            ## Validate XML file with XSD file if possible.
            if performValidation:
                print("Validating %s" % fname)
                mavgen_validate(fname, schemaFile, opts.error_limit);
            else:
                print("Validation skipped for %s." % fname)

            ## Parsing
            print("Parsing %s" % fname)
            xml.append(mavparse.MAVXML(fname, opts.wire_protocol))

            # include message lengths and CRCs too
            for idx in range(0, 256):
                if x.message_lengths[idx] == 0:
                    x.message_lengths[idx] = xml[-1].message_lengths[idx]
                    x.message_crcs[idx] = xml[-1].message_crcs[idx]
                    x.message_names[idx] = xml[-1].message_names[idx]

    # work out max payload size across all includes
    largest_payload = 0
    for x in xml:
        if x.largest_payload > largest_payload:
            largest_payload = x.largest_payload
    for x in xml:
        x.largest_payload = largest_payload

    if mavparse.check_duplicates(xml):
        sys.exit(1)

    print("Found %u MAVLink message types in %u XML files" % (
        mavparse.total_msgs(xml), len(xml)))

    # Convert language option to lowercase and validate
    opts.language = opts.language.lower()
    if opts.language == 'python':
        from . import mavgen_python
        mavgen_python.generate(opts.output, xml)
    elif opts.language == 'c':
        try:
            import mavgen_c
        except Exception:
            from pymavlink.generator import mavgen_c
        mavgen_c.generate(opts.output, xml)
    elif opts.language == 'wlua':
        import mavgen_wlua
        mavgen_wlua.generate(opts.output, xml)
    elif opts.language == 'cs':
        import mavgen_cs
        mavgen_cs.generate(opts.output, xml)
    elif opts.language == 'javascript':
        import mavgen_javascript
        mavgen_javascript.generate(opts.output, xml)
    else:
        print("Unsupported language %s" % opts.language)


# build all the dialects in the dialects subpackage
class Opts:
    def __init__(self, wire_protocol, output):
        self.wire_protocol = wire_protocol
        self.error_limit = 200
        self.language = 'Python'
        self.output = output

def mavgen_python_dialect(dialect, wire_protocol):
    '''generate the python code on the fly for a MAVLink dialect'''
    dialects = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', 'dialects')
    mdef = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', '..', 'message_definitions')
    if wire_protocol == mavparse.PROTOCOL_0_9:
        py = os.path.join(dialects, 'v09', dialect + '.py')
        xml = os.path.join(dialects, 'v09', dialect + '.xml')
        if not os.path.exists(xml):
            xml = os.path.join(mdef, 'v0.9', dialect + '.xml')
    else:
        py = os.path.join(dialects, 'v10', dialect + '.py')
        xml = os.path.join(dialects, 'v10', dialect + '.xml')
        if not os.path.exists(xml):
            xml = os.path.join(mdef, 'v1.0', dialect + '.xml')
    opts = Opts(wire_protocol, py)
    import StringIO

    # throw away stdout while generating
    stdout_saved = sys.stdout
    sys.stdout = StringIO.StringIO()
    try:
        xml = os.path.relpath(xml)
        mavgen( opts, [xml] )
    except Exception:
        sys.stdout = stdout_saved
        raise
    sys.stdout = stdout_saved
    

def mavgen_validate(fname, schema, errorLimitNumber) :
    """Uses minixsv to validate an XML file with a given XSD schema file."""
    # use default values of minixsv, location of the schema file must be specified in the XML file
    domTreeWrapper = pyxsval.parseAndValidate(fname, xsdFile=schema, errorLimit=errorLimitNumber)
            
    # domTree is a minidom document object
    domTree = domTreeWrapper.getTree()


if __name__ == "__main__":
    from optparse import OptionParser

    supportedLanguages = ["C", "CS", "JavaScript", "Python", "WLua"]
    parser = OptionParser("%prog [options] <XML files>")
    parser.add_option("-o", "--output", dest="output", default="mavlink", help="output directory.")
    parser.add_option("--lang", dest="language", choices=supportedLanguages, default="Python", help="language of generated code, one of: {0} [default: %default]".format(supportedLanguages))
    parser.add_option("--wire-protocol", dest="wire_protocol", choices=[mavparse.PROTOCOL_0_9, mavparse.PROTOCOL_1_0], default=mavparse.PROTOCOL_1_0, help="MAVLink protocol version: '0.9' or '1.0'. [default: %default]")
    parser.add_option("--error-limit", dest="error_limit", default=200, help="maximum number of validation errors.")
    (opts, args) = parser.parse_args()

    if len(args) < 1:
        parser.error("You must supply at least one MAVLink XML protocol definition")
    mavgen(opts, args)

########NEW FILE########
__FILENAME__ = mavgen_c
#!/usr/bin/env python
'''
parse a MAVLink protocol XML file and generate a C implementation

Copyright Andrew Tridgell 2011
Released under GNU GPL version 3 or later
'''

import sys, textwrap, os, time
import mavparse, mavtemplate

t = mavtemplate.MAVTemplate()

def generate_version_h(directory, xml):
    '''generate version.h'''
    f = open(os.path.join(directory, "version.h"), mode='w')
    t.write(f,'''
/** @file
 *	@brief MAVLink comm protocol built from ${basename}.xml
 *	@see http://pixhawk.ethz.ch/software/mavlink
 */
#ifndef MAVLINK_VERSION_H
#define MAVLINK_VERSION_H

#define MAVLINK_BUILD_DATE "${parse_time}"
#define MAVLINK_WIRE_PROTOCOL_VERSION "${wire_protocol_version}"
#define MAVLINK_MAX_DIALECT_PAYLOAD_SIZE ${largest_payload}
 
#endif // MAVLINK_VERSION_H
''', xml)
    f.close()

def generate_mavlink_h(directory, xml):
    '''generate mavlink.h'''
    f = open(os.path.join(directory, "mavlink.h"), mode='w')
    t.write(f,'''
/** @file
 *	@brief MAVLink comm protocol built from ${basename}.xml
 *	@see http://pixhawk.ethz.ch/software/mavlink
 */
#ifndef MAVLINK_H
#define MAVLINK_H

#ifndef MAVLINK_STX
#define MAVLINK_STX ${protocol_marker}
#endif

#ifndef MAVLINK_ENDIAN
#define MAVLINK_ENDIAN ${mavlink_endian}
#endif

#ifndef MAVLINK_ALIGNED_FIELDS
#define MAVLINK_ALIGNED_FIELDS ${aligned_fields_define}
#endif

#ifndef MAVLINK_CRC_EXTRA
#define MAVLINK_CRC_EXTRA ${crc_extra_define}
#endif

#include "version.h"
#include "${basename}.h"

#endif // MAVLINK_H
''', xml)
    f.close()

def generate_main_h(directory, xml):
    '''generate main header per XML file'''
    f = open(os.path.join(directory, xml.basename + ".h"), mode='w')
    t.write(f, '''
/** @file
 *	@brief MAVLink comm protocol generated from ${basename}.xml
 *	@see http://qgroundcontrol.org/mavlink/
 */
#ifndef ${basename_upper}_H
#define ${basename_upper}_H

#ifdef __cplusplus
extern "C" {
#endif

// MESSAGE LENGTHS AND CRCS

#ifndef MAVLINK_MESSAGE_LENGTHS
#define MAVLINK_MESSAGE_LENGTHS {${message_lengths_array}}
#endif

#ifndef MAVLINK_MESSAGE_CRCS
#define MAVLINK_MESSAGE_CRCS {${message_crcs_array}}
#endif

#ifndef MAVLINK_MESSAGE_INFO
#define MAVLINK_MESSAGE_INFO {${message_info_array}}
#endif

#include "../protocol.h"

#define MAVLINK_ENABLED_${basename_upper}

// ENUM DEFINITIONS

${{enum:
/** @brief ${description} */
#ifndef HAVE_ENUM_${name}
#define HAVE_ENUM_${name}
typedef enum ${name}
{
${{entry:	${name}=${value}, /* ${description} |${{param:${description}| }} */
}}
} ${name};
#endif
}}

${{include_list:#include "../${base}/${base}.h"
}}

// MAVLINK VERSION

#ifndef MAVLINK_VERSION
#define MAVLINK_VERSION ${version}
#endif

#if (MAVLINK_VERSION == 0)
#undef MAVLINK_VERSION
#define MAVLINK_VERSION ${version}
#endif

// MESSAGE DEFINITIONS
${{message:#include "./mavlink_msg_${name_lower}.h"
}}

#ifdef __cplusplus
}
#endif // __cplusplus
#endif // ${basename_upper}_H
''', xml)

    f.close()
             

def generate_message_h(directory, m):
    '''generate per-message header for a XML file'''
    f = open(os.path.join(directory, 'mavlink_msg_%s.h' % m.name_lower), mode='w')
    t.write(f, '''
// MESSAGE ${name} PACKING

#define MAVLINK_MSG_ID_${name} ${id}

typedef struct __mavlink_${name_lower}_t
{
${{ordered_fields: ${type} ${name}${array_suffix}; ///< ${description}
}}
} mavlink_${name_lower}_t;

#define MAVLINK_MSG_ID_${name}_LEN ${wire_length}
#define MAVLINK_MSG_ID_${id}_LEN ${wire_length}

#define MAVLINK_MSG_ID_${name}_CRC ${crc_extra}
#define MAVLINK_MSG_ID_${id}_CRC ${crc_extra}

${{array_fields:#define MAVLINK_MSG_${msg_name}_FIELD_${name_upper}_LEN ${array_length}
}}

#define MAVLINK_MESSAGE_INFO_${name} { \\
	"${name}", \\
	${num_fields}, \\
	{ ${{ordered_fields: { "${name}", ${c_print_format}, MAVLINK_TYPE_${type_upper}, ${array_length}, ${wire_offset}, offsetof(mavlink_${name_lower}_t, ${name}) }, \\
        }} } \\
}


/**
 * @brief Pack a ${name_lower} message
 * @param system_id ID of this system
 * @param component_id ID of this component (e.g. 200 for IMU)
 * @param msg The MAVLink message to compress the data into
 *
${{arg_fields: * @param ${name} ${description}
}}
 * @return length of the message in bytes (excluding serial stream start sign)
 */
static inline uint16_t mavlink_msg_${name_lower}_pack(uint8_t system_id, uint8_t component_id, mavlink_message_t* msg,
						      ${{arg_fields: ${array_const}${type} ${array_prefix}${name},}})
{
#if MAVLINK_NEED_BYTE_SWAP || !MAVLINK_ALIGNED_FIELDS
	char buf[MAVLINK_MSG_ID_${name}_LEN];
${{scalar_fields:	_mav_put_${type}(buf, ${wire_offset}, ${putname});
}}
${{array_fields:	_mav_put_${type}_array(buf, ${wire_offset}, ${name}, ${array_length});
}}
        memcpy(_MAV_PAYLOAD_NON_CONST(msg), buf, MAVLINK_MSG_ID_${name}_LEN);
#else
	mavlink_${name_lower}_t packet;
${{scalar_fields:	packet.${name} = ${putname};
}}
${{array_fields:	mav_array_memcpy(packet.${name}, ${name}, sizeof(${type})*${array_length});
}}
        memcpy(_MAV_PAYLOAD_NON_CONST(msg), &packet, MAVLINK_MSG_ID_${name}_LEN);
#endif

	msg->msgid = MAVLINK_MSG_ID_${name};
#if MAVLINK_CRC_EXTRA
    return mavlink_finalize_message(msg, system_id, component_id, MAVLINK_MSG_ID_${name}_LEN, MAVLINK_MSG_ID_${name}_CRC);
#else
    return mavlink_finalize_message(msg, system_id, component_id, MAVLINK_MSG_ID_${name}_LEN);
#endif
}

/**
 * @brief Pack a ${name_lower} message on a channel
 * @param system_id ID of this system
 * @param component_id ID of this component (e.g. 200 for IMU)
 * @param chan The MAVLink channel this message will be sent over
 * @param msg The MAVLink message to compress the data into
${{arg_fields: * @param ${name} ${description}
}}
 * @return length of the message in bytes (excluding serial stream start sign)
 */
static inline uint16_t mavlink_msg_${name_lower}_pack_chan(uint8_t system_id, uint8_t component_id, uint8_t chan,
							   mavlink_message_t* msg,
						           ${{arg_fields:${array_const}${type} ${array_prefix}${name},}})
{
#if MAVLINK_NEED_BYTE_SWAP || !MAVLINK_ALIGNED_FIELDS
	char buf[MAVLINK_MSG_ID_${name}_LEN];
${{scalar_fields:	_mav_put_${type}(buf, ${wire_offset}, ${putname});
}}
${{array_fields:	_mav_put_${type}_array(buf, ${wire_offset}, ${name}, ${array_length});
}}
        memcpy(_MAV_PAYLOAD_NON_CONST(msg), buf, MAVLINK_MSG_ID_${name}_LEN);
#else
	mavlink_${name_lower}_t packet;
${{scalar_fields:	packet.${name} = ${putname};
}}
${{array_fields:	mav_array_memcpy(packet.${name}, ${name}, sizeof(${type})*${array_length});
}}
        memcpy(_MAV_PAYLOAD_NON_CONST(msg), &packet, MAVLINK_MSG_ID_${name}_LEN);
#endif

	msg->msgid = MAVLINK_MSG_ID_${name};
#if MAVLINK_CRC_EXTRA
    return mavlink_finalize_message_chan(msg, system_id, component_id, chan, MAVLINK_MSG_ID_${name}_LEN, MAVLINK_MSG_ID_${name}_CRC);
#else
    return mavlink_finalize_message_chan(msg, system_id, component_id, chan, MAVLINK_MSG_ID_${name}_LEN);
#endif
}

/**
 * @brief Encode a ${name_lower} struct
 *
 * @param system_id ID of this system
 * @param component_id ID of this component (e.g. 200 for IMU)
 * @param msg The MAVLink message to compress the data into
 * @param ${name_lower} C-struct to read the message contents from
 */
static inline uint16_t mavlink_msg_${name_lower}_encode(uint8_t system_id, uint8_t component_id, mavlink_message_t* msg, const mavlink_${name_lower}_t* ${name_lower})
{
	return mavlink_msg_${name_lower}_pack(system_id, component_id, msg,${{arg_fields: ${name_lower}->${name},}});
}

/**
 * @brief Encode a ${name_lower} struct on a channel
 *
 * @param system_id ID of this system
 * @param component_id ID of this component (e.g. 200 for IMU)
 * @param chan The MAVLink channel this message will be sent over
 * @param msg The MAVLink message to compress the data into
 * @param ${name_lower} C-struct to read the message contents from
 */
static inline uint16_t mavlink_msg_${name_lower}_encode_chan(uint8_t system_id, uint8_t component_id, uint8_t chan, mavlink_message_t* msg, const mavlink_${name_lower}_t* ${name_lower})
{
	return mavlink_msg_${name_lower}_pack_chan(system_id, component_id, chan, msg,${{arg_fields: ${name_lower}->${name},}});
}

/**
 * @brief Send a ${name_lower} message
 * @param chan MAVLink channel to send the message
 *
${{arg_fields: * @param ${name} ${description}
}}
 */
#ifdef MAVLINK_USE_CONVENIENCE_FUNCTIONS

static inline void mavlink_msg_${name_lower}_send(mavlink_channel_t chan,${{arg_fields: ${array_const}${type} ${array_prefix}${name},}})
{
#if MAVLINK_NEED_BYTE_SWAP || !MAVLINK_ALIGNED_FIELDS
	char buf[MAVLINK_MSG_ID_${name}_LEN];
${{scalar_fields:	_mav_put_${type}(buf, ${wire_offset}, ${putname});
}}
${{array_fields:	_mav_put_${type}_array(buf, ${wire_offset}, ${name}, ${array_length});
}}
#if MAVLINK_CRC_EXTRA
    _mav_finalize_message_chan_send(chan, MAVLINK_MSG_ID_${name}, buf, MAVLINK_MSG_ID_${name}_LEN, MAVLINK_MSG_ID_${name}_CRC);
#else
    _mav_finalize_message_chan_send(chan, MAVLINK_MSG_ID_${name}, buf, MAVLINK_MSG_ID_${name}_LEN);
#endif
#else
	mavlink_${name_lower}_t packet;
${{scalar_fields:	packet.${name} = ${putname};
}}
${{array_fields:	mav_array_memcpy(packet.${name}, ${name}, sizeof(${type})*${array_length});
}}
#if MAVLINK_CRC_EXTRA
    _mav_finalize_message_chan_send(chan, MAVLINK_MSG_ID_${name}, (const char *)&packet, MAVLINK_MSG_ID_${name}_LEN, MAVLINK_MSG_ID_${name}_CRC);
#else
    _mav_finalize_message_chan_send(chan, MAVLINK_MSG_ID_${name}, (const char *)&packet, MAVLINK_MSG_ID_${name}_LEN);
#endif
#endif
}

#if MAVLINK_MSG_ID_${name}_LEN <= MAVLINK_MAX_PAYLOAD_LEN
/*
  This varient of _send() can be used to save stack space by re-using
  memory from the receive buffer.  The caller provides a
  mavlink_message_t which is the size of a full mavlink message. This
  is usually the receive buffer for the channel, and allows a reply to an
  incoming message with minimum stack space usage.
 */
static inline void mavlink_msg_${name_lower}_send_buf(mavlink_message_t *msgbuf, mavlink_channel_t chan, ${{arg_fields: ${array_const}${type} ${array_prefix}${name},}})
{
#if MAVLINK_NEED_BYTE_SWAP || !MAVLINK_ALIGNED_FIELDS
	char *buf = (char *)msgbuf;
${{scalar_fields:	_mav_put_${type}(buf, ${wire_offset}, ${putname});
}}
${{array_fields:	_mav_put_${type}_array(buf, ${wire_offset}, ${name}, ${array_length});
}}
#if MAVLINK_CRC_EXTRA
    _mav_finalize_message_chan_send(chan, MAVLINK_MSG_ID_${name}, buf, MAVLINK_MSG_ID_${name}_LEN, MAVLINK_MSG_ID_${name}_CRC);
#else
    _mav_finalize_message_chan_send(chan, MAVLINK_MSG_ID_${name}, buf, MAVLINK_MSG_ID_${name}_LEN);
#endif
#else
	mavlink_${name_lower}_t *packet = (mavlink_${name_lower}_t *)msgbuf;
${{scalar_fields:	packet->${name} = ${putname};
}}
${{array_fields:	mav_array_memcpy(packet->${name}, ${name}, sizeof(${type})*${array_length});
}}
#if MAVLINK_CRC_EXTRA
    _mav_finalize_message_chan_send(chan, MAVLINK_MSG_ID_${name}, (const char *)packet, MAVLINK_MSG_ID_${name}_LEN, MAVLINK_MSG_ID_${name}_CRC);
#else
    _mav_finalize_message_chan_send(chan, MAVLINK_MSG_ID_${name}, (const char *)packet, MAVLINK_MSG_ID_${name}_LEN);
#endif
#endif
}
#endif

#endif

// MESSAGE ${name} UNPACKING

${{fields:
/**
 * @brief Get field ${name} from ${name_lower} message
 *
 * @return ${description}
 */
static inline ${return_type} mavlink_msg_${name_lower}_get_${name}(const mavlink_message_t* msg${get_arg})
{
	return _MAV_RETURN_${type}${array_tag}(msg, ${array_return_arg} ${wire_offset});
}
}}

/**
 * @brief Decode a ${name_lower} message into a struct
 *
 * @param msg The message to decode
 * @param ${name_lower} C-struct to decode the message contents into
 */
static inline void mavlink_msg_${name_lower}_decode(const mavlink_message_t* msg, mavlink_${name_lower}_t* ${name_lower})
{
#if MAVLINK_NEED_BYTE_SWAP
${{ordered_fields:	${decode_left}mavlink_msg_${name_lower}_get_${name}(msg${decode_right});
}}
#else
	memcpy(${name_lower}, _MAV_PAYLOAD(msg), MAVLINK_MSG_ID_${name}_LEN);
#endif
}
''', m)
    f.close()


def generate_testsuite_h(directory, xml):
    '''generate testsuite.h per XML file'''
    f = open(os.path.join(directory, "testsuite.h"), mode='w')
    t.write(f, '''
/** @file
 *	@brief MAVLink comm protocol testsuite generated from ${basename}.xml
 *	@see http://qgroundcontrol.org/mavlink/
 */
#ifndef ${basename_upper}_TESTSUITE_H
#define ${basename_upper}_TESTSUITE_H

#ifdef __cplusplus
extern "C" {
#endif

#ifndef MAVLINK_TEST_ALL
#define MAVLINK_TEST_ALL
${{include_list:static void mavlink_test_${base}(uint8_t, uint8_t, mavlink_message_t *last_msg);
}}
static void mavlink_test_${basename}(uint8_t, uint8_t, mavlink_message_t *last_msg);

static void mavlink_test_all(uint8_t system_id, uint8_t component_id, mavlink_message_t *last_msg)
{
${{include_list:	mavlink_test_${base}(system_id, component_id, last_msg);
}}
	mavlink_test_${basename}(system_id, component_id, last_msg);
}
#endif

${{include_list:#include "../${base}/testsuite.h"
}}

${{message:
static void mavlink_test_${name_lower}(uint8_t system_id, uint8_t component_id, mavlink_message_t *last_msg)
{
	mavlink_message_t msg;
        uint8_t buffer[MAVLINK_MAX_PACKET_LEN];
        uint16_t i;
	mavlink_${name_lower}_t packet_in = {
		${{ordered_fields:${c_test_value},
	}}};
	mavlink_${name_lower}_t packet1, packet2;
        memset(&packet1, 0, sizeof(packet1));
        ${{scalar_fields:	packet1.${name} = packet_in.${name};
        }}
        ${{array_fields:	mav_array_memcpy(packet1.${name}, packet_in.${name}, sizeof(${type})*${array_length});
        }}

        memset(&packet2, 0, sizeof(packet2));
	mavlink_msg_${name_lower}_encode(system_id, component_id, &msg, &packet1);
	mavlink_msg_${name_lower}_decode(&msg, &packet2);
        MAVLINK_ASSERT(memcmp(&packet1, &packet2, sizeof(packet1)) == 0);

        memset(&packet2, 0, sizeof(packet2));
	mavlink_msg_${name_lower}_pack(system_id, component_id, &msg ${{arg_fields:, packet1.${name} }});
	mavlink_msg_${name_lower}_decode(&msg, &packet2);
        MAVLINK_ASSERT(memcmp(&packet1, &packet2, sizeof(packet1)) == 0);

        memset(&packet2, 0, sizeof(packet2));
	mavlink_msg_${name_lower}_pack_chan(system_id, component_id, MAVLINK_COMM_0, &msg ${{arg_fields:, packet1.${name} }});
	mavlink_msg_${name_lower}_decode(&msg, &packet2);
        MAVLINK_ASSERT(memcmp(&packet1, &packet2, sizeof(packet1)) == 0);

        memset(&packet2, 0, sizeof(packet2));
        mavlink_msg_to_send_buffer(buffer, &msg);
        for (i=0; i<mavlink_msg_get_send_buffer_length(&msg); i++) {
        	comm_send_ch(MAVLINK_COMM_0, buffer[i]);
        }
	mavlink_msg_${name_lower}_decode(last_msg, &packet2);
        MAVLINK_ASSERT(memcmp(&packet1, &packet2, sizeof(packet1)) == 0);
        
        memset(&packet2, 0, sizeof(packet2));
	mavlink_msg_${name_lower}_send(MAVLINK_COMM_1 ${{arg_fields:, packet1.${name} }});
	mavlink_msg_${name_lower}_decode(last_msg, &packet2);
        MAVLINK_ASSERT(memcmp(&packet1, &packet2, sizeof(packet1)) == 0);
}
}}

static void mavlink_test_${basename}(uint8_t system_id, uint8_t component_id, mavlink_message_t *last_msg)
{
${{message:	mavlink_test_${name_lower}(system_id, component_id, last_msg);
}}
}

#ifdef __cplusplus
}
#endif // __cplusplus
#endif // ${basename_upper}_TESTSUITE_H
''', xml)

    f.close()

def copy_fixed_headers(directory, xml):
    '''copy the fixed protocol headers to the target directory'''
    import shutil
    hlist = [ 'protocol.h', 'mavlink_helpers.h', 'mavlink_types.h', 'checksum.h', 'mavlink_conversions.h', 'mavlink_protobuf_manager.hpp' ]
    basepath = os.path.dirname(os.path.realpath(__file__))
    srcpath = os.path.join(basepath, 'C/include_v%s' % xml.wire_protocol_version)
    print("Copying fixed headers")
    for h in hlist:
        if (not (h == 'mavlink_protobuf_manager.hpp' and xml.wire_protocol_version == '0.9')):
           src = os.path.realpath(os.path.join(srcpath, h))
           dest = os.path.realpath(os.path.join(directory, h))
           if src == dest:
               continue
           shutil.copy(src, dest)
    # XXX This is a hack - to be removed
    if (xml.basename == 'pixhawk' and xml.wire_protocol_version == '1.0'):
        h = 'pixhawk/pixhawk.pb.h'
        src = os.path.realpath(os.path.join(srcpath, h))
        dest = os.path.realpath(os.path.join(directory, h))
        if src != dest:
            shutil.copy(src, dest)
        
def copy_fixed_sources(directory, xml):
    # XXX This is a hack - to be removed
    import shutil
    basepath = os.path.dirname(os.path.realpath(__file__))
    srcpath = os.path.join(basepath, 'C/src_v%s' % xml.wire_protocol_version)
    if (xml.basename == 'pixhawk' and xml.wire_protocol_version == '1.0'):
        print("Copying fixed sources")
        src = os.path.realpath(os.path.join(srcpath, 'pixhawk/pixhawk.pb.cc'))
        dest = os.path.realpath(os.path.join(directory, '../../../share/mavlink/src/v%s/pixhawk/pixhawk.pb.cc' % xml.wire_protocol_version))
        destdir = os.path.realpath(os.path.join(directory, '../../../share/mavlink/src/v%s/pixhawk' % xml.wire_protocol_version))
        try:
           os.makedirs(destdir)
        except:
           print("Not re-creating directory")
        shutil.copy(src, dest)
        print("Copied to"),
        print(dest)

class mav_include(object):
    def __init__(self, base):
        self.base = base

def generate_one(basename, xml):
    '''generate headers for one XML file'''

    directory = os.path.join(basename, xml.basename)

    print("Generating C implementation in directory %s" % directory)
    mavparse.mkdir_p(directory)

    if xml.little_endian:
        xml.mavlink_endian = "MAVLINK_LITTLE_ENDIAN"
    else:
        xml.mavlink_endian = "MAVLINK_BIG_ENDIAN"

    if xml.crc_extra:
        xml.crc_extra_define = "1"
    else:
        xml.crc_extra_define = "0"

    if xml.sort_fields:
        xml.aligned_fields_define = "1"
    else:
        xml.aligned_fields_define = "0"

    # work out the included headers
    xml.include_list = []
    for i in xml.include:
        base = i[:-4]
        xml.include_list.append(mav_include(base))

    # form message lengths array
    xml.message_lengths_array = ''
    for mlen in xml.message_lengths:
        xml.message_lengths_array += '%u, ' % mlen
    xml.message_lengths_array = xml.message_lengths_array[:-2]

    # and message CRCs array
    xml.message_crcs_array = ''
    for crc in xml.message_crcs:
        xml.message_crcs_array += '%u, ' % crc
    xml.message_crcs_array = xml.message_crcs_array[:-2]

    # form message info array
    xml.message_info_array = ''
    for name in xml.message_names:
        if name is not None:
            xml.message_info_array += 'MAVLINK_MESSAGE_INFO_%s, ' % name
        else:
            # Several C compilers don't accept {NULL} for
            # multi-dimensional arrays and structs
            # feed the compiler a "filled" empty message
            xml.message_info_array += '{"EMPTY",0,{{"","",MAVLINK_TYPE_CHAR,0,0,0}}}, '
    xml.message_info_array = xml.message_info_array[:-2]

    # add some extra field attributes for convenience with arrays
    for m in xml.message:
        m.msg_name = m.name
        if xml.crc_extra:
            m.crc_extra_arg = ", %s" % m.crc_extra
        else:
            m.crc_extra_arg = ""
        for f in m.fields:
            if f.print_format is None:
                f.c_print_format = 'NULL'
            else:
                f.c_print_format = '"%s"' % f.print_format
            if f.array_length != 0:
                f.array_suffix = '[%u]' % f.array_length
                f.array_prefix = '*'
                f.array_tag = '_array'
                f.array_arg = ', %u' % f.array_length
                f.array_return_arg = '%s, %u, ' % (f.name, f.array_length)
                f.array_const = 'const '
                f.decode_left = ''
                f.decode_right = ', %s->%s' % (m.name_lower, f.name)
                f.return_type = 'uint16_t'
                f.get_arg = ', %s *%s' % (f.type, f.name)
                if f.type == 'char':
                    f.c_test_value = '"%s"' % f.test_value
                else:
                    test_strings = []
                    for v in f.test_value:
                        test_strings.append(str(v))
                    f.c_test_value = '{ %s }' % ', '.join(test_strings)
            else:
                f.array_suffix = ''
                f.array_prefix = ''
                f.array_tag = ''
                f.array_arg = ''
                f.array_return_arg = ''
                f.array_const = ''
                f.decode_left = "%s->%s = " % (m.name_lower, f.name)
                f.decode_right = ''
                f.get_arg = ''
                f.return_type = f.type
                if f.type == 'char':
                    f.c_test_value = "'%s'" % f.test_value
                elif f.type == 'uint64_t':
                    f.c_test_value = "%sULL" % f.test_value                    
                elif f.type == 'int64_t':
                    f.c_test_value = "%sLL" % f.test_value                    
                else:
                    f.c_test_value = f.test_value

    # cope with uint8_t_mavlink_version
    for m in xml.message:
        m.arg_fields = []
        m.array_fields = []
        m.scalar_fields = []
        for f in m.ordered_fields:
            if f.array_length != 0:
                m.array_fields.append(f)
            else:
                m.scalar_fields.append(f)
        for f in m.fields:
            if not f.omit_arg:
                m.arg_fields.append(f)
                f.putname = f.name
            else:
                f.putname = f.const_value

    generate_mavlink_h(directory, xml)
    generate_version_h(directory, xml)
    generate_main_h(directory, xml)
    for m in xml.message:
        generate_message_h(directory, m)
    generate_testsuite_h(directory, xml)


def generate(basename, xml_list):
    '''generate complete MAVLink C implemenation'''

    for xml in xml_list:
        generate_one(basename, xml)
    copy_fixed_headers(basename, xml_list[0])
    copy_fixed_sources(basename, xml_list[0])

########NEW FILE########
__FILENAME__ = mavgen_cs
#!/usr/bin/env python
'''
parse a MAVLink protocol XML file and generate a CSharp implementation


'''
import sys, textwrap, os, time, platform
import mavparse, mavtemplate

t = mavtemplate.MAVTemplate()

# todo - refactor this in to the other array
map = {
        'float'    : 'float',
        'double'   : 'double',
        'char'     : 'byte',
        'int8_t'   : 'sbyte',
        'uint8_t'  : 'byte',
        'uint8_t_mavlink_version'  : 'B',
        'int16_t'  : 'Int16',
        'uint16_t' : 'UInt16',
        'int32_t'  : 'Int32',
        'uint32_t' : 'UInt32',
        'int64_t'  : 'Int64',
        'uint64_t' : 'UInt64',
        }

# Map of field type to bitconverter bytedecoding function, and number of bytes used for the encoding
mapType = {
        'float'    : ('ToSingle', 4),
        'double'   : ('ToDouble', 8),
        'int8_t'   : ('ToInt8', 1),
        'uint8_t'   : ('ToUInt8', 1),
        'char'   :   ('ToChar', 1),
        'int16_t'  : ('ToInt16', 2),
        'uint16_t' : ('ToUInt16', 2),
        'int32_t'  : ('ToInt32', 4),
        'uint32_t' : ('ToUInt32', 4),
        'int64_t'  : ('ToInt64', 8),
        'uint64_t' : ('ToUInt64', 8),
        }        

# Map of field names to names that are C# compatible and not illegal class field names
mapFieldName = {
        'fixed'    : '@fixed'
        }                
        
def generate_preamble(outf, msgs, args, xml):
    print("Generating preamble")
    t.write(outf, """
/*
MAVLink protocol implementation (auto-generated by mavgen.py)

Generated from: ${FILELIST}

Note: this file has been auto-generated. DO NOT EDIT
*/

using System;
""", {'FILELIST' : ",".join(args)})

def generate_xmlDocSummary(outf, summaryText, tabDepth):
    indent = '\t' * tabDepth
    escapedText = summaryText.replace("\n","\n%s///" % indent)
    outf.write("\n%s/// <summary>\n" % indent)
    outf.write("%s/// %s\n" % (indent, escapedText))
    outf.write("%s/// </summary>\n" % indent)
    
    
def generate_enums(outf, enums):
    print("Generating enums")
    outf.write("namespace MavLink\n{\n")
    for e in enums:
            #if len(e.description) > 0:
        generate_xmlDocSummary(outf, e.description, 1)
        outf.write("\tpublic enum %s : ushort\n\t{\n" % e.name)

        for entry in e.entry:
            if len(entry.description) > 0:
                generate_xmlDocSummary(outf, entry.description, 2)
            outf.write("\t\t%s = %u,\n" % (entry.name, entry.value))

        outf.write("\n\t}\n\n")
    outf.write("\n}\n")
        
def generate_classes(outf, msgs):
    print("Generating class definitions")

    outf.write("""
    
   
namespace MavLink\n{

    public abstract class MavlinkMessage
    {
        public abstract int Serialize(byte[] bytes, ref int offset);
    }
""")

    for m in msgs:
        if (len(m.description) >0):
            generate_xmlDocSummary(outf, m.description, 1)
        outf.write("""\tpublic class Msg_%s : MavlinkMessage
    {
""" % m.name.lower())
    
        for f in m.fields:
            if (f.description.upper() != f.name.upper()):
                generate_xmlDocSummary(outf, f.description, 2)
            if (f.array_length):
                outf.write("\t\tpublic %s[] %s; // Array size %s\n" % (map[f.type], mapFieldName.get(f.name, f.name), f.array_length))
            else:
                outf.write("\t\tpublic %s %s;\n" % (map[f.type], mapFieldName.get(f.name, f.name)))
        
        outf.write("""
        public override int Serialize(byte[] bytes, ref int offset)
            {
                return MavLinkSerializer.Serialize_%s(this, bytes, ref offset);
            }        
""" % m.name.upper())

        outf.write("\t}\n\n")    
    outf.write("}\n\n")

    
   
def generate_Deserialization(outf, messages):
    
    # Create the deserialization funcs 
    for m in messages:
        classname="Msg_%s" % m.name.lower()
        outf.write("\n\t\tinternal static MavlinkMessage Deserialize_%s(byte[] bytes, int offset)\n\t\t{\n" % (m.name))
        offset = 0
    
        outf.write("\t\t\treturn new %s\n" % classname)
        outf.write("\t\t\t{\n")
		
        for f in m.ordered_fields:
            if (f.array_length):
                outf.write("\t\t\t\t%s =  ByteArrayUtil.%s(bytes, offset + %s, %s),\n" % (mapFieldName.get(f.name, f.name), mapType[f.type][0], offset, f.array_length))
                offset += f.array_length
                continue
          
            # mapping 'char' to byte here since there is no real equivalent in the CLR
            if (f.type == 'uint8_t' or f.type == 'char' ):
                    outf.write("\t\t\t\t%s = bytes[offset + %s],\n" % (mapFieldName.get(f.name, f.name),offset))
                    offset+=1          
            else:             
                outf.write("\t\t\t\t%s = bitconverter.%s(bytes, offset + %s),\n" % (mapFieldName.get(f.name, f.name), mapType[f.type][0] ,  offset))
                offset += mapType[f.type][1]
				
        outf.write("\t\t\t};\n")
        outf.write("\t\t}\n") 

    
def generate_Serialization(outf, messages):
    
    # Create the table of serialization delegates
    for m in messages:
        classname="Msg_%s" % m.name.lower()

        outf.write("\n\t\tinternal static int Serialize_%s(this %s msg, byte[] bytes, ref int offset)\n\t\t{\n" % (m.name, classname))
        offset=0
        
		# Now (since Mavlink 1.0) we need to deal with ordering of fields
        for f in m.ordered_fields:
        
            if (f.array_length):
                outf.write("\t\t\tByteArrayUtil.ToByteArray(msg.%s, bytes, offset + %s, %s);\n" % (f.name, offset, f.array_length))
                offset += f.array_length * mapType[f.type][1]
                continue

            if (f.type == 'uint8_t'):
                outf.write("\t\t\tbytes[offset + %s] = msg.%s;\n" % (offset,mapFieldName.get(f.name, f.name)))
                offset+=1
            elif (f.type == 'int8_t'):
                outf.write("\t\t\tbytes[offset + %s] = unchecked((byte)msg.%s);\n" % (offset,mapFieldName.get(f.name, f.name)))
                offset+=1
            elif (f.type == 'char'):
                outf.write("\t\t\tbytes[offset + %s] = msg.%s; // todo: check int8_t and char are compatible\n" % (offset,mapFieldName.get(f.name, f.name)))
                offset+=1
            else:
                outf.write("\t\t\tbitconverter.GetBytes(msg.%s, bytes, offset + %s);\n" % (mapFieldName.get(f.name, f.name),offset))
                offset += mapType[f.type][1]
          
        outf.write("\t\t\toffset += %s;\n" % offset)
        outf.write("\t\t\treturn %s;\n" % m.id)
        outf.write("\t\t}\n") 


def generate_CodecIndex(outf, messages, xml):
    
    outf.write("""

/*
MAVLink protocol implementation (auto-generated by mavgen.py)

Note: this file has been auto-generated. DO NOT EDIT
*/

using System;
using System.Collections;
using System.Collections.Generic;
    
namespace MavLink
{
    public static class MavlinkSettings
    {
""")
    outf.write('\t\tpublic const string WireProtocolVersion = "%s";' % xml[0].wire_protocol_version)
    outf.write('\n\t\tpublic const byte ProtocolMarker = 0x%x;' % xml[0].protocol_marker)
    outf.write('\n\t\tpublic const bool CrcExtra = %s;' % str(xml[0].crc_extra).lower())
    outf.write('\n\t\tpublic const bool IsLittleEndian = %s;' % str(xml[0].little_endian).lower())
    
    outf.write("""
    }
    
    public delegate MavlinkMessage MavlinkPacketDeserializeFunc(byte[] bytes, int offset);

    //returns the message ID, offset is advanced by the number of bytes used to serialize
    public delegate int MavlinkPacketSerializeFunc(byte[] bytes, ref int offset, object mavlinkPacket);
 
    public class MavPacketInfo
    {
        public MavlinkPacketDeserializeFunc Deserializer;
        public int [] OrderMap;
        public byte CrcExtra;

         public MavPacketInfo(MavlinkPacketDeserializeFunc deserializer, byte crcExtra)
         {
             this.Deserializer = deserializer;
             this.CrcExtra = crcExtra;
         }
    }
 
    public static class MavLinkSerializer
    {
        public static void SetDataIsLittleEndian(bool isLittle)
        {
            bitconverter.SetDataIsLittleEndian(isLittle);
        }
    
        private static readonly FrameworkBitConverter bitconverter = new FrameworkBitConverter(); 
    
        public static Dictionary<int, MavPacketInfo> Lookup = new Dictionary<int, MavPacketInfo>
        {""")

    for m in messages:
        classname="Msg_%s" % m.name.lower()
        outf.write("\n\t\t\t{%s, new MavPacketInfo(Deserialize_%s, %s)}," % (m.id, m.name, m.crc_extra))
    outf.write("\n\t\t};\n")
   

def generate(basename, xml):
    '''generate complete MAVLink CSharp implemenation'''
    structsfilename = basename + '.generated.cs'

     # Some build commands depend on the platform - eg MS .NET Windows Vs Mono on Linux
    if platform.system() == "Windows":
        winpath=os.environ['WinDir']
        cscCommand = winpath + "\\Microsoft.NET\\Framework\\v4.0.30319\\csc.exe"
        
        if (os.path.exists(cscCommand)==False):
            print("\nError: CS compiler not found. .Net Assembly generation skipped")
            return   
    else:
        print("Error:.Net Assembly generation not yet supported on non Windows platforms")
        return
        cscCommand = "csc"
    
    
    
    
    msgs = []
    enums = []
    filelist = []
    for x in xml:
        msgs.extend(x.message)
        enums.extend(x.enum)
        filelist.append(os.path.basename(x.filename))

    for m in msgs:
        m.order_map = [ 0 ] * len(m.fieldnames)
        for i in range(0, len(m.fieldnames)):
            m.order_map[i] = m.ordered_fieldnames.index(m.fieldnames[i])
        
        m.fields_in_order = []
        for i in range(0, len(m.fieldnames)):
            m.order_map[i] = m.ordered_fieldnames.index(m.fieldnames[i])
        
    print("Generating messages file: %s" % structsfilename)
    dir = os.path.dirname(structsfilename)
    if not os.path.exists(dir):
        os.makedirs(dir)
    outf = open(structsfilename, "w")
    generate_preamble(outf, msgs, filelist, xml[0])
    
    outf.write("""
    
using System.Reflection;    
    
[assembly: AssemblyTitle("Mavlink Classes")]
[assembly: AssemblyDescription("Generated Message Classes for Mavlink. See http://qgroundcontrol.org/mavlink/start")]
[assembly: AssemblyProduct("Mavlink")]
[assembly: AssemblyVersion("1.0.0.0")]
[assembly: AssemblyFileVersion("1.0.0.0")]

    """)
    
    generate_enums(outf, enums)
    generate_classes(outf, msgs)
    outf.close()
    
    print("Generating the (De)Serializer classes")
    serfilename = basename + '_codec.generated.cs'
    outf = open(serfilename, "w")
    generate_CodecIndex(outf, msgs, xml)
    generate_Deserialization(outf, msgs)
    generate_Serialization(outf, msgs)
    
    outf.write("\t}\n\n")
    outf.write("}\n\n")
    
    outf.close()
    
   

    print("Compiling Assembly for .Net Framework 4.0")
    
    generatedCsFiles = [ serfilename, structsfilename]
    
    includedCsFiles =  [ 'CS/common/ByteArrayUtil.cs', 'CS/common/FrameworkBitConverter.cs', 'CS/common/Mavlink.cs'  ]
    
    outputLibraryPath = os.path.normpath(dir + "/mavlink.dll")
    
    compileCommand = "%s %s" % (cscCommand, "/target:library /debug /out:" + outputLibraryPath)
    compileCommand = compileCommand + " /doc:" + os.path.normpath(dir + "/mavlink.xml")  
    
    
    for csFile in generatedCsFiles + includedCsFiles:
        compileCommand = compileCommand + " " + os.path.normpath(csFile)
    
    #print("Cmd:" + compileCommand)
    res = os.system (compileCommand)
    
    if res == '0':
        print("Generated %s OK" % filename)
    else:
        print("Error")

########NEW FILE########
__FILENAME__ = mavgen_javascript
#!/usr/bin/env python
'''
parse a MAVLink protocol XML file and generate a Node.js javascript module implementation

Based on original work Copyright Andrew Tridgell 2011
Released under GNU GPL version 3 or later
'''

import sys, textwrap, os
import mavparse, mavtemplate

t = mavtemplate.MAVTemplate()

def generate_preamble(outf, msgs, args, xml):
    print("Generating preamble")
    t.write(outf, """
/*
MAVLink protocol implementation for node.js (auto-generated by mavgen_javascript.py)

Generated from: ${FILELIST}

Note: this file has been auto-generated. DO NOT EDIT
*/

jspack = require("jspack").jspack,
    _ = require("underscore"),
    events = require("events"),
    util = require("util");

// Add a convenience method to Buffer
Buffer.prototype.toByteArray = function () {
  return Array.prototype.slice.call(this, 0)
}

mavlink = function(){};

// Implement the X25CRC function (present in the Python version through the mavutil.py package)
mavlink.x25Crc = function(buffer, crc) {

    var bytes = buffer;
    var crc = crc || 0xffff;
    _.each(bytes, function(e) {
        var tmp = e ^ (crc & 0xff);
        tmp = (tmp ^ (tmp << 4)) & 0xff;
        crc = (crc >> 8) ^ (tmp << 8) ^ (tmp << 3) ^ (tmp >> 4);
        crc = crc & 0xffff;
    });
    return crc;

}

mavlink.WIRE_PROTOCOL_VERSION = "${WIRE_PROTOCOL_VERSION}";

mavlink.MAVLINK_TYPE_CHAR     = 0
mavlink.MAVLINK_TYPE_UINT8_T  = 1
mavlink.MAVLINK_TYPE_INT8_T   = 2
mavlink.MAVLINK_TYPE_UINT16_T = 3
mavlink.MAVLINK_TYPE_INT16_T  = 4
mavlink.MAVLINK_TYPE_UINT32_T = 5
mavlink.MAVLINK_TYPE_INT32_T  = 6
mavlink.MAVLINK_TYPE_UINT64_T = 7
mavlink.MAVLINK_TYPE_INT64_T  = 8
mavlink.MAVLINK_TYPE_FLOAT    = 9
mavlink.MAVLINK_TYPE_DOUBLE   = 10

// Mavlink headers incorporate sequence, source system (platform) and source component. 
mavlink.header = function(msgId, mlen, seq, srcSystem, srcComponent) {

    this.mlen = ( typeof mlen === 'undefined' ) ? 0 : mlen;
    this.seq = ( typeof seq === 'undefined' ) ? 0 : seq;
    this.srcSystem = ( typeof srcSystem === 'undefined' ) ? 0 : srcSystem;
    this.srcComponent = ( typeof srcComponent === 'undefined' ) ? 0 : srcComponent;
    this.msgId = msgId

}

mavlink.header.prototype.pack = function() {
    return jspack.Pack('BBBBBB', [${PROTOCOL_MARKER}, this.mlen, this.seq, this.srcSystem, this.srcComponent, this.msgId]);
}

// Base class declaration: mavlink.message will be the parent class for each
// concrete implementation in mavlink.messages.
mavlink.message = function() {};

// Convenience setter to facilitate turning the unpacked array of data into member properties
mavlink.message.prototype.set = function(args) {
    _.each(this.fieldnames, function(e, i) {
        this[e] = args[i];
    }, this);
};

// This pack function builds the header and produces a complete MAVLink message,
// including header and message CRC.
mavlink.message.prototype.pack = function(crc_extra, payload) {

    this.payload = payload;
    this.header = new mavlink.header(this.id, payload.length, this.seq, this.srcSystem, this.srcComponent);    
    this.msgbuf = this.header.pack().concat(payload);
    var crc = mavlink.x25Crc(this.msgbuf.slice(1));

    // For now, assume always using crc_extra = True.  TODO: check/fix this.
    crc = mavlink.x25Crc([crc_extra], crc);
    this.msgbuf = this.msgbuf.concat(jspack.Pack('<H', [crc] ) );
    return this.msgbuf;

}

""", {'FILELIST' : ",".join(args),
      'PROTOCOL_MARKER' : xml.protocol_marker,
      'crc_extra' : xml.crc_extra,
      'WIRE_PROTOCOL_VERSION' : xml.wire_protocol_version })

def generate_enums(outf, enums):
    print("Generating enums")
    outf.write("\n// enums\n")
    wrapper = textwrap.TextWrapper(initial_indent="", subsequent_indent="                        // ")
    for e in enums:
        outf.write("\n// %s\n" % e.name)
        for entry in e.entry:
            outf.write("mavlink.%s = %u // %s\n" % (entry.name, entry.value, wrapper.fill(entry.description)))

def generate_message_ids(outf, msgs):
    print("Generating message IDs")
    outf.write("\n// message IDs\n")
    outf.write("mavlink.MAVLINK_MSG_ID_BAD_DATA = -1\n")
    for m in msgs:
        outf.write("mavlink.MAVLINK_MSG_ID_%s = %u\n" % (m.name.upper(), m.id))

def generate_classes(outf, msgs):
    """
    Generate the implementations of the classes representing MAVLink messages.

    """
    print("Generating class definitions")
    wrapper = textwrap.TextWrapper(initial_indent="", subsequent_indent="")
    outf.write("\nmavlink.messages = {};\n\n");

    def field_descriptions(fields):
        ret = ""
        for f in fields:
            ret += "                %-18s        : %s (%s)\n" % (f.name, f.description.strip(), f.type)
        return ret

    for m in msgs:

        comment = "%s\n\n%s" % (wrapper.fill(m.description.strip()), field_descriptions(m.fields))

        selffieldnames = 'self, '
        for f in m.fields:
            # if f.omit_arg:
            #    selffieldnames += '%s=%s, ' % (f.name, f.const_value)
            #else:
            # -- Omitting the code above because it is rarely used (only once?) and would need some special handling
            # in javascript.  Specifically, inside the method definition, it needs to check for a value then assign
            # a default.
            selffieldnames += '%s, ' % f.name
        selffieldnames = selffieldnames[:-2]

        sub = {'NAMELOWER'      : m.name.lower(),
               'SELFFIELDNAMES' : selffieldnames,
               'COMMENT'        : comment,
               'FIELDNAMES'     : ", ".join(m.fieldnames)}

        t.write(outf, """
/* 
${COMMENT}
*/
""", sub)

        # function signature + declaration
        outf.write("mavlink.messages.%s = function(" % (m.name.lower()))
        if len(m.fields) != 0:
                outf.write(", ".join(m.fieldnames))
        outf.write(") {")

        # body: set message type properties    
        outf.write("""

    this.format = '%s';
    this.id = mavlink.MAVLINK_MSG_ID_%s;
    this.order_map = %s;
    this.crc_extra = %u;
    this.name = '%s';

""" % (m.fmtstr, m.name.upper(), m.order_map, m.crc_extra, m.name.upper()))
        
        # body: set own properties
        if len(m.fieldnames) != 0:
                outf.write("    this.fieldnames = ['%s'];\n" % "', '".join(m.fieldnames))
        outf.write("""

    this.set(arguments);

}
        """)

        # inherit methods from the base message class
        outf.write("""
mavlink.messages.%s.prototype = new mavlink.message;
""" % m.name.lower())

        # Implement the pack() function for this message
        outf.write("""
mavlink.messages.%s.prototype.pack = function() {
    return mavlink.message.prototype.pack.call(this, this.crc_extra, jspack.Pack(this.format""" % m.name.lower())
        if len(m.fields) != 0:
                outf.write(", [ this." + ", this.".join(m.ordered_fieldnames) + ']')
        outf.write("));\n}\n\n")

def mavfmt(field):
    '''work out the struct format for a type'''
    map = {
        'float'    : 'f',
        'double'   : 'd',
        'char'     : 'c',
        'int8_t'   : 'b',
        'uint8_t'  : 'B',
        'uint8_t_mavlink_version'  : 'B',
        'int16_t'  : 'h',
        'uint16_t' : 'H',
        'int32_t'  : 'i',
        'uint32_t' : 'I',
        'int64_t'  : 'd',
        'uint64_t' : 'd',
        }

    if field.array_length:
        if field.type in ['char', 'int8_t', 'uint8_t']:
            return str(field.array_length)+'s'
        return str(field.array_length)+map[field.type]
    return map[field.type]

def generate_mavlink_class(outf, msgs, xml):
    print("Generating MAVLink class")

    # Write mapper to enable decoding based on the integer message type
    outf.write("\n\nmavlink.map = {\n");
    for m in msgs:
        outf.write("        %s: { format: '%s', type: mavlink.messages.%s, order_map: %s, crc_extra: %u },\n" % (
            m.id, m.fmtstr, m.name.lower(), m.order_map, m.crc_extra))
    outf.write("}\n\n")
    
    t.write(outf, """

// Special mavlink message to capture malformed data packets for debugging
mavlink.messages.bad_data = function(data, reason) {
    this.id = mavlink.MAVLINK_MSG_ID_BAD_DATA;
    this.data = data;
    this.reason = reason;
}

/* MAVLink protocol handling class */
MAVLink = function(logger, srcSystem, srcComponent) {

    this.logger = logger;

    this.seq = 0;
    this.buf = new Buffer(0);
   
    this.srcSystem = (typeof srcSystem === 'undefined') ? 0 : srcSystem;
    this.srcComponent =  (typeof srcComponent === 'undefined') ? 0 : srcComponent;

    // The first packet we expect is a valid header, 6 bytes.
    this.expected_length = 6;

    this.have_prefix_error = false;

    this.protocol_marker = 254;
    this.little_endian = true;

    this.crc_extra = true;
    this.sort_fields = true;
    this.total_packets_sent = 0;
    this.total_bytes_sent = 0;
    this.total_packets_received = 0;
    this.total_bytes_received = 0;
    this.total_receive_errors = 0;
    this.startup_time = Date.now();
    
}

// Implements EventEmitter
util.inherits(MAVLink, events.EventEmitter);

// If the logger exists, this function will add a message to it.
// Assumes the logger is a winston object.
MAVLink.prototype.log = function(message) {
    if(this.logger) {
        this.logger.info(message);
    }
}

MAVLink.prototype.send = function(mavmsg) {
        buf = mavmsg.pack(this);
        this.file.write(buf);
        this.seq = (this.seq + 1) % 255;
        this.total_packets_sent +=1;
        this.total_bytes_sent += buf.length;
}

// return number of bytes needed for next parsing stage
MAVLink.prototype.bytes_needed = function() {
    ret = this.expected_length - this.buf.length;
    return ( ret <= 0 ) ? 1 : ret;
}

// add data to the local buffer
MAVLink.prototype.pushBuffer = function(data) {
    if(data) {
        this.buf = Buffer.concat([this.buf, data]);
        this.total_bytes_received += data.length;
    }
}

// Decode prefix.  Elides the prefix.
MAVLink.prototype.parsePrefix = function() {

    // Test for a message prefix.
    if( this.buf.length >= 1 && this.buf[0] != 254 ) {

        // Strip the offending initial byte and throw an error.
        var badPrefix = this.buf[0];
        this.buf = this.buf.slice(1);
        this.expected_length = 6;
        this.total_receive_errors +=1;
        throw new Error("Bad prefix ("+badPrefix+")");

    }

}

// Determine the length.  Leaves buffer untouched.
MAVLink.prototype.parseLength = function() {
    
    if( this.buf.length >= 3 ) {
        var unpacked = jspack.Unpack('BB', this.buf.slice(1, 3));
        this.expected_length = unpacked[0] + 8; // length of message + header + CRC
    }

}

// input some data bytes, possibly returning a new message
MAVLink.prototype.parseChar = function(c) {

    var m;
    try {

        this.pushBuffer(c);
        this.parsePrefix();
        this.parseLength();
        m = this.parsePayload();

    } catch(e) {

       // w.info("Got a bad data message ("+e.message+")");
        this.total_receive_errors += 1;
        m = new mavlink.messages.bad_data(this.buf, e.message);
        
    }

    return m;

}

MAVLink.prototype.parsePayload = function() {

    // If we have enough bytes to try and read it, read it.
    if( this.expected_length >= 8 && this.buf.length >= this.expected_length ) {

        // Slice off the expected packet length, reset expectation to be to find a header.
        var mbuf = this.buf.slice(0, this.expected_length);

        // w.info("Attempting to parse packet, message candidate buffer is ["+mbuf.toByteArray()+"]");

        try {

            var m = this.decode(mbuf);
            this.total_packets_received += 1;
            this.buf = this.buf.slice(this.expected_length);
            this.expected_length = 6;
            this.emit(m.name, m);
            this.emit('message', m);
            return m;

        } catch(e) {

            // In this case, we thought we'd have a valid packet, but
            // didn't.  It could be that the packet was structurally present
            // but malformed, or, it could be that random line noise
            // made this look like a packet.  Consume the first symbol in the buffer and continue parsing.
            this.buf = this.buf.slice(1);
            this.expected_length = 6;
            
            // Log.
            //w.info(e);

            // bubble
            throw e;
        }
    }
    return null;

}

// input some data bytes, possibly returning an array of new messages
MAVLink.prototype.parseBuffer = function(s) {
    
    // Get a message, if one is available in the stream.
    var m = this.parseChar(s);

    // No messages available, bail.
    if ( null === m ) {
        return null;
    }
    
    // While more valid messages can be read from the existing buffer, add
    // them to the array of new messages and return them.
    var ret = [m];
    while(true) {
        m = this.parseChar();
        if ( null === m ) {
            // No more messages left.
            return ret;
        }
        ret.push(m);
    }
    return ret;

}

/* decode a buffer as a MAVLink message */
MAVLink.prototype.decode = function(msgbuf) {

    var magic, mlen, seq, srcSystem, srcComponent, unpacked, msgId;

    // decode the header
    try {
        unpacked = jspack.Unpack('cBBBBB', msgbuf.slice(0, 6));
        magic = unpacked[0];
        mlen = unpacked[1];
        seq = unpacked[2];
        srcSystem = unpacked[3];
        srcComponent = unpacked[4];
        msgId = unpacked[5];
    }
    catch(e) {
        throw new Error('Unable to unpack MAVLink header: ' + e.message);
    }

    if (magic.charCodeAt(0) != 254) {
        throw new Error("Invalid MAVLink prefix ("+magic.charCodeAt(0)+")");
    }

    if( mlen != msgbuf.length - 8 ) {
        throw new Error("Invalid MAVLink message length.  Got " + (msgbuf.length - 8) + " expected " + mlen + ", msgId=" + msgId);
    }

    if( false === _.has(mavlink.map, msgId) ) {
        throw new Error("Unknown MAVLink message ID (" + msgId + ")");
    }

    // decode the payload
    // refs: (fmt, type, order_map, crc_extra) = mavlink.map[msgId]
    var decoder = mavlink.map[msgId];

    // decode the checksum
    try {
        var receivedChecksum = jspack.Unpack('<H', msgbuf.slice(msgbuf.length - 2));
    } catch (e) {
        throw new Error("Unable to unpack MAVLink CRC: " + e.message);
    }

    var messageChecksum = mavlink.x25Crc(msgbuf.slice(1, msgbuf.length - 2));

    // Assuming using crc_extra = True.  See the message.prototype.pack() function.
    messageChecksum = mavlink.x25Crc([decoder.crc_extra], messageChecksum);
    
    if ( receivedChecksum != messageChecksum ) {
        throw new Error('invalid MAVLink CRC in msgID ' +msgId+ ', got 0x' + receivedChecksum + ' checksum, calculated payload checkum as 0x'+messageChecksum );
    }

    // Decode the payload and reorder the fields to match the order map.
    try {
        var t = jspack.Unpack(decoder.format, msgbuf.slice(6, msgbuf.length));
    }
    catch (e) {
        throw new Error('Unable to unpack MAVLink payload type='+decoder.type+' format='+decoder.format+' payloadLength='+ msgbuf.slice(6, -2).length +': '+ e.message);
    }

    // Reorder the fields to match the order map
    var args = [];
    _.each(t, function(e, i, l) {
        args[i] = t[decoder.order_map[i]]
    });

    // construct the message object
    try {
        var m = new decoder.type(args);
        m.set.call(m, args);
    }
    catch (e) {
        throw new Error('Unable to instantiate MAVLink message of type '+decoder.type+' : ' + e.message);
    }
    m.msgbuf = msgbuf;
    m.payload = msgbuf.slice(6);
    m.crc = receivedChecksum;
    m.header = new mavlink.header(msgId, mlen, seq, srcSystem, srcComponent);
    this.log(m);
    return m;
}

""", xml)

def generate_footer(outf):
    t.write(outf, """

// Expose this code as a module
module.exports = mavlink;

""")

def generate(basename, xml):
    '''generate complete javascript implementation'''

    print basename;
    if basename.endswith('.js'):
        filename = basename
    else:
        filename = basename + '.js'

    msgs = []
    enums = []
    filelist = []
    for x in xml:
        msgs.extend(x.message)
        enums.extend(x.enum)
        filelist.append(os.path.basename(x.filename))

    for m in msgs:
        if xml[0].little_endian:
            m.fmtstr = '<'
        else:
            m.fmtstr = '>'
        for f in m.ordered_fields:
            m.fmtstr += mavfmt(f)
        m.order_map = [ 0 ] * len(m.fieldnames)
        for i in range(0, len(m.fieldnames)):
            m.order_map[i] = m.ordered_fieldnames.index(m.fieldnames[i])

    print("Generating %s" % filename)
    outf = open(filename, "w")
    generate_preamble(outf, msgs, filelist, xml[0])
    generate_enums(outf, enums)
    generate_message_ids(outf, msgs)
    generate_classes(outf, msgs)
    generate_mavlink_class(outf, msgs, xml[0])
    generate_footer(outf)
    outf.close()
    print("Generated %s OK" % filename)

########NEW FILE########
__FILENAME__ = mavgen_python
#!/usr/bin/env python
'''
parse a MAVLink protocol XML file and generate a python implementation

Copyright Andrew Tridgell 2011
Released under GNU GPL version 3 or later
'''

import sys, textwrap, os
from . import mavparse, mavtemplate

t = mavtemplate.MAVTemplate()

def generate_preamble(outf, msgs, args, xml):
    print("Generating preamble")
    t.write(outf, """
'''
MAVLink protocol implementation (auto-generated by mavgen.py)

Generated from: ${FILELIST}

Note: this file has been auto-generated. DO NOT EDIT
'''

import struct, array, time, json
from ...generator.mavcrc import x25crc

WIRE_PROTOCOL_VERSION = "${WIRE_PROTOCOL_VERSION}"


# some base types from mavlink_types.h
MAVLINK_TYPE_CHAR     = 0
MAVLINK_TYPE_UINT8_T  = 1
MAVLINK_TYPE_INT8_T   = 2
MAVLINK_TYPE_UINT16_T = 3
MAVLINK_TYPE_INT16_T  = 4
MAVLINK_TYPE_UINT32_T = 5
MAVLINK_TYPE_INT32_T  = 6
MAVLINK_TYPE_UINT64_T = 7
MAVLINK_TYPE_INT64_T  = 8
MAVLINK_TYPE_FLOAT    = 9
MAVLINK_TYPE_DOUBLE   = 10


class MAVLink_header(object):
    '''MAVLink message header'''
    def __init__(self, msgId, mlen=0, seq=0, srcSystem=0, srcComponent=0):
        self.mlen = mlen
        self.seq = seq
        self.srcSystem = srcSystem
        self.srcComponent = srcComponent
        self.msgId = msgId

    def pack(self):
        return struct.pack('BBBBBB', ${PROTOCOL_MARKER}, self.mlen, self.seq,
                          self.srcSystem, self.srcComponent, self.msgId)

class MAVLink_message(object):
    '''base MAVLink message class'''
    def __init__(self, msgId, name):
        self._header     = MAVLink_header(msgId)
        self._payload    = None
        self._msgbuf     = None
        self._crc        = None
        self._fieldnames = []
        self._type       = name

    def get_msgbuf(self):
        if isinstance(self._msgbuf, str):
            return self._msgbuf
        return self._msgbuf.tostring()

    def get_header(self):
        return self._header

    def get_payload(self):
        return self._payload

    def get_crc(self):
        return self._crc

    def get_fieldnames(self):
        return self._fieldnames

    def get_type(self):
        return self._type

    def get_msgId(self):
        return self._header.msgId

    def get_srcSystem(self):
        return self._header.srcSystem

    def get_srcComponent(self):
        return self._header.srcComponent

    def get_seq(self):
        return self._header.seq

    def __str__(self):
        ret = '%s {' % self._type
        for a in self._fieldnames:
            v = getattr(self, a)
            ret += '%s : %s, ' % (a, v)
        ret = ret[0:-2] + '}'
        return ret

    def to_dict(self):
        d = dict({})
        d['mavpackettype'] = self._type
        for a in self._fieldnames:
          d[a] = getattr(self, a)
        return d

    def to_json(self):
        return json.dumps(self.to_dict())

    def pack(self, mav, crc_extra, payload):
        self._payload = payload
        self._header  = MAVLink_header(self._header.msgId, len(payload), mav.seq,
                                       mav.srcSystem, mav.srcComponent)
        self._msgbuf = self._header.pack() + payload
        crc = x25crc(self._msgbuf[1:])
        if ${crc_extra}: # using CRC extra
            crc.accumulate(chr(crc_extra))
        self._crc = crc.crc
        self._msgbuf += struct.pack('<H', self._crc)
        return self._msgbuf

""", {'FILELIST' : ",".join(args),
      'PROTOCOL_MARKER' : xml.protocol_marker,
      'crc_extra' : xml.crc_extra,
      'WIRE_PROTOCOL_VERSION' : xml.wire_protocol_version })


def generate_enums(outf, enums):
    print("Generating enums")
    outf.write("\n# enums\n")
    wrapper = textwrap.TextWrapper(initial_indent="", subsequent_indent="                        # ")
    for e in enums:
        outf.write("\n# %s\n" % e.name)
        for entry in e.entry:
            outf.write("%s = %u # %s\n" % (entry.name, entry.value, wrapper.fill(entry.description)))

def generate_message_ids(outf, msgs):
    print("Generating message IDs")
    outf.write("\n# message IDs\n")
    outf.write("MAVLINK_MSG_ID_BAD_DATA = -1\n")
    for m in msgs:
        outf.write("MAVLINK_MSG_ID_%s = %u\n" % (m.name.upper(), m.id))

def generate_classes(outf, msgs):
    print("Generating class definitions")
    wrapper = textwrap.TextWrapper(initial_indent="        ", subsequent_indent="        ")
    for m in msgs:
        outf.write("""
class MAVLink_%s_message(MAVLink_message):
        '''
%s
        '''
        def __init__(self""" % (m.name.lower(), wrapper.fill(m.description.strip())))
        if len(m.fields) != 0:
                outf.write(", " + ", ".join(m.fieldnames))
        outf.write("):\n")
        outf.write("                MAVLink_message.__init__(self, MAVLINK_MSG_ID_%s, '%s')\n" % (m.name.upper(), m.name.upper()))
        if len(m.fieldnames) != 0:
                outf.write("                self._fieldnames = ['%s']\n" % "', '".join(m.fieldnames))
        for f in m.fields:
                outf.write("                self.%s = %s\n" % (f.name, f.name))
        outf.write("""
        def pack(self, mav):
                return MAVLink_message.pack(self, mav, %u, struct.pack('%s'""" % (m.crc_extra, m.fmtstr))
        for field in m.ordered_fields:
                if (field.type != "char" and field.array_length > 1):
                        for i in range(field.array_length):
                                outf.write(", self.{0:s}[{1:d}]".format(field.name,i))
                else:
                        outf.write(", self.{0:s}".format(field.name))
        outf.write("))\n")


def mavfmt(field):
    '''work out the struct format for a type'''
    map = {
        'float'    : 'f',
        'double'   : 'd',
        'char'     : 'c',
        'int8_t'   : 'b',
        'uint8_t'  : 'B',
        'uint8_t_mavlink_version'  : 'B',
        'int16_t'  : 'h',
        'uint16_t' : 'H',
        'int32_t'  : 'i',
        'uint32_t' : 'I',
        'int64_t'  : 'q',
        'uint64_t' : 'Q',
        }

    if field.array_length:
        if field.type == 'char':
            return str(field.array_length)+'s'
        return str(field.array_length)+map[field.type]
    return map[field.type]

def generate_mavlink_class(outf, msgs, xml):
    print("Generating MAVLink class")

    outf.write("\n\nmavlink_map = {\n");
    for m in msgs:
        outf.write("        MAVLINK_MSG_ID_%s : ( '%s', MAVLink_%s_message, %s, %s, %u ),\n" % (
            m.name.upper(), m.fmtstr, m.name.lower(), m.order_map, m.len_map, m.crc_extra))
    outf.write("}\n\n")

    t.write(outf, """
class MAVError(Exception):
        '''MAVLink error class'''
        def __init__(self, msg):
            Exception.__init__(self, msg)
            self.message = msg

class MAVString(str):
        '''NUL terminated string'''
        def __init__(self, s):
                str.__init__(self)
        def __str__(self):
            i = self.find(chr(0))
            if i == -1:
                return self[:]
            return self[0:i]

class MAVLink_bad_data(MAVLink_message):
        '''
        a piece of bad data in a mavlink stream
        '''
        def __init__(self, data, reason):
                MAVLink_message.__init__(self, MAVLINK_MSG_ID_BAD_DATA, 'BAD_DATA')
                self._fieldnames = ['data', 'reason']
                self.data = data
                self.reason = reason
                self._msgbuf = data

        def __str__(self):
            '''Override the __str__ function from MAVLink_messages because non-printable characters are common in to be the reason for this message to exist.'''
            return '%s {%s, data:%s}' % (self._type, self.reason, [('%x' % ord(i) if isinstance(i, str) else '%x' % i) for i in self.data])

class MAVLink(object):
        '''MAVLink protocol handling class'''
        def __init__(self, file, srcSystem=0, srcComponent=0):
                self.seq = 0
                self.file = file
                self.srcSystem = srcSystem
                self.srcComponent = srcComponent
                self.callback = None
                self.callback_args = None
                self.callback_kwargs = None
                self.send_callback = None
                self.send_callback_args = None
                self.send_callback_kwargs = None
                self.buf = array.array('B')
                self.expected_length = 6
                self.have_prefix_error = False
                self.robust_parsing = False
                self.protocol_marker = ${protocol_marker}
                self.little_endian = ${little_endian}
                self.crc_extra = ${crc_extra}
                self.sort_fields = ${sort_fields}
                self.total_packets_sent = 0
                self.total_bytes_sent = 0
                self.total_packets_received = 0
                self.total_bytes_received = 0
                self.total_receive_errors = 0
                self.startup_time = time.time()

        def set_callback(self, callback, *args, **kwargs):
            self.callback = callback
            self.callback_args = args
            self.callback_kwargs = kwargs

        def set_send_callback(self, callback, *args, **kwargs):
            self.send_callback = callback
            self.send_callback_args = args
            self.send_callback_kwargs = kwargs

        def send(self, mavmsg):
                '''send a MAVLink message'''
                buf = mavmsg.pack(self)
                self.file.write(buf)
                self.seq = (self.seq + 1) % 256
                self.total_packets_sent += 1
                self.total_bytes_sent += len(buf)
                if self.send_callback:
                    self.send_callback(mavmsg, *self.send_callback_args, **self.send_callback_kwargs)

        def bytes_needed(self):
            '''return number of bytes needed for next parsing stage'''
            ret = self.expected_length - len(self.buf)
            if ret <= 0:
                return 1
            return ret

        def parse_char(self, c):
            '''input some data bytes, possibly returning a new message'''
            if isinstance(c, str):
                self.buf.fromstring(c)
            else:
                self.buf.extend(c)
            self.total_bytes_received += len(c)
            if len(self.buf) >= 1 and self.buf[0] != ${protocol_marker}:
                magic = self.buf[0]
                self.buf = self.buf[1:]
                if self.robust_parsing:
                    m = MAVLink_bad_data(chr(magic), "Bad prefix")
                    if self.callback:
                        self.callback(m, *self.callback_args, **self.callback_kwargs)
                    self.expected_length = 6
                    self.total_receive_errors += 1
                    return m
                if self.have_prefix_error:
                    return None
                self.have_prefix_error = True
                self.total_receive_errors += 1
                raise MAVError("invalid MAVLink prefix '%s'" % magic)
            self.have_prefix_error = False
            if len(self.buf) >= 2:
                (magic, self.expected_length) = struct.unpack('BB', self.buf[0:2])
                self.expected_length += 8
            if self.expected_length >= 8 and len(self.buf) >= self.expected_length:
                mbuf = self.buf[0:self.expected_length]
                self.buf = self.buf[self.expected_length:]
                self.expected_length = 6
                if self.robust_parsing:
                    try:
                        m = self.decode(mbuf)
                        self.total_packets_received += 1
                    except MAVError as reason:
                        m = MAVLink_bad_data(mbuf, reason.message)
                        self.total_receive_errors += 1
                else:
                    m = self.decode(mbuf)
                    self.total_packets_received += 1
                if self.callback:
                    self.callback(m, *self.callback_args, **self.callback_kwargs)
                return m
            return None

        def parse_buffer(self, s):
            '''input some data bytes, possibly returning a list of new messages'''
            m = self.parse_char(s)
            if m is None:
                return None
            ret = [m]
            while True:
                m = self.parse_char("")
                if m is None:
                    return ret
                ret.append(m)
            return ret

        def decode(self, msgbuf):
                '''decode a buffer as a MAVLink message'''
                # decode the header
                try:
                    magic, mlen, seq, srcSystem, srcComponent, msgId = struct.unpack('cBBBBB', msgbuf[:6])
                except struct.error as emsg:
                    raise MAVError('Unable to unpack MAVLink header: %s' % emsg)
                if ord(magic) != ${protocol_marker}:
                    raise MAVError("invalid MAVLink prefix '%s'" % magic)
                if mlen != len(msgbuf)-8:
                    raise MAVError('invalid MAVLink message length. Got %u expected %u, msgId=%u' % (len(msgbuf)-8, mlen, msgId))

                if not msgId in mavlink_map:
                    raise MAVError('unknown MAVLink message ID %u' % msgId)

                # decode the payload
                (fmt, type, order_map, len_map, crc_extra) = mavlink_map[msgId]

                # decode the checksum
                try:
                    crc, = struct.unpack('<H', msgbuf[-2:])
                except struct.error as emsg:
                    raise MAVError('Unable to unpack MAVLink CRC: %s' % emsg)
                crc2 = x25crc(msgbuf[1:-2])
                if ${crc_extra}: # using CRC extra
                    crc2.accumulate(chr(crc_extra))
                if crc != crc2.crc:
                    raise MAVError('invalid MAVLink CRC in msgID %u 0x%04x should be 0x%04x' % (msgId, crc, crc2.crc))

                try:
                    t = struct.unpack(fmt, msgbuf[6:-2])
                except struct.error as emsg:
                    raise MAVError('Unable to unpack MAVLink payload type=%s fmt=%s payloadLength=%u: %s' % (
                        type, fmt, len(msgbuf[6:-2]), emsg))

                tlist = list(t)
                # handle sorted fields
                if ${sort_fields}:
                    t = tlist[:]
                    if sum(len_map) == len(len_map):
                        # message has no arrays in it
                        for i in range(0, len(tlist)):
                            tlist[i] = t[order_map[i]]
                    else:
                        # message has some arrays
                        tlist = []
                        for i in range(0, len(order_map)):
                            order = order_map[i]
                            L = len_map[order]
                            tip = sum(len_map[:order])
                            field = t[tip]
                            if L == 1 or isinstance(field, str):
                                tlist.append(field)
                            else:
                                tlist.append(t[tip:(tip + L)])

                # terminate any strings
                for i in range(0, len(tlist)):
                    if isinstance(tlist[i], str):
                        tlist[i] = MAVString(tlist[i])
                t = tuple(tlist)
                # construct the message object
                try:
                    m = type(*t)
                except Exception as emsg:
                    raise MAVError('Unable to instantiate MAVLink message of type %s : %s' % (type, emsg))
                m._msgbuf = msgbuf
                m._payload = msgbuf[6:-2]
                m._crc = crc
                m._header = MAVLink_header(msgId, mlen, seq, srcSystem, srcComponent)
                return m
""", xml)

def generate_methods(outf, msgs):
    print("Generating methods")

    def field_descriptions(fields):
        ret = ""
        for f in fields:
            ret += "                %-18s        : %s (%s)\n" % (f.name, f.description.strip(), f.type)
        return ret

    wrapper = textwrap.TextWrapper(initial_indent="", subsequent_indent="                ")

    for m in msgs:
        comment = "%s\n\n%s" % (wrapper.fill(m.description.strip()), field_descriptions(m.fields))

        selffieldnames = 'self, '
        for f in m.fields:
            if f.omit_arg:
                selffieldnames += '%s=%s, ' % (f.name, f.const_value)
            else:
                selffieldnames += '%s, ' % f.name
        selffieldnames = selffieldnames[:-2]

        sub = {'NAMELOWER'      : m.name.lower(),
               'SELFFIELDNAMES' : selffieldnames,
               'COMMENT'        : comment,
               'FIELDNAMES'     : ", ".join(m.fieldnames)}

        t.write(outf, """
        def ${NAMELOWER}_encode(${SELFFIELDNAMES}):
                '''
                ${COMMENT}
                '''
                msg = MAVLink_${NAMELOWER}_message(${FIELDNAMES})
                msg.pack(self)
                return msg

""", sub)

        t.write(outf, """
        def ${NAMELOWER}_send(${SELFFIELDNAMES}):
                '''
                ${COMMENT}
                '''
                return self.send(self.${NAMELOWER}_encode(${FIELDNAMES}))

""", sub)


def generate(basename, xml):
    '''generate complete python implemenation'''
    if basename.endswith('.py'):
        filename = basename
    else:
        filename = basename + '.py'

    msgs = []
    enums = []
    filelist = []
    for x in xml:
        msgs.extend(x.message)
        enums.extend(x.enum)
        filelist.append(os.path.basename(x.filename))

    for m in msgs:
        if xml[0].little_endian:
            m.fmtstr = '<'
        else:
            m.fmtstr = '>'
        for f in m.ordered_fields:
            m.fmtstr += mavfmt(f)
        m.order_map = [ 0 ] * len(m.fieldnames)
        m.len_map = [ 0 ] * len(m.fieldnames)
        for i in range(0, len(m.fieldnames)):
            m.order_map[i] = m.ordered_fieldnames.index(m.fieldnames[i])
        for i in range(0, len(m.fieldnames)):
            n = m.order_map[i]
            m.len_map[n] = m.fieldlengths[i]

    print("Generating %s" % filename)
    outf = open(filename, "w")
    generate_preamble(outf, msgs, filelist, xml[0])
    generate_enums(outf, enums)
    generate_message_ids(outf, msgs)
    generate_classes(outf, msgs)
    generate_mavlink_class(outf, msgs, xml[0])
    generate_methods(outf, msgs)
    outf.close()
    print("Generated %s OK" % filename)

########NEW FILE########
__FILENAME__ = mavgen_wlua
#!/usr/bin/env python
'''
parse a MAVLink protocol XML file and generate a Wireshark LUA dissector

Copyright Holger Steinhaus 2012
Released under GNU GPL version 3 or later

Instructions for use: 
1. ./mavgen --lang=wlua mymavlink.xml -o ~/.wireshark/plugins/mymavlink.lua 
2. convert binary stream int .pcap file format (see examples/mavcap.py)
3. open the pcap file in Wireshark
'''

import sys, textwrap, os, re
import mavparse, mavtemplate

t = mavtemplate.MAVTemplate()


def lua_type(mavlink_type):
    # qnd typename conversion
    if (mavlink_type=='char'):
        lua_t = 'uint8'
    else:
        lua_t = mavlink_type.replace('_t', '')
    return lua_t

def type_size(mavlink_type):
    # infer size of mavlink types
    re_int = re.compile('^(u?)int(8|16|32|64)_t$')
    int_parts = re_int.findall(mavlink_type)
    if len(int_parts):
        return int(int_parts[0][1])/8
    elif mavlink_type == 'float':
        return 4
    elif mavlink_type == 'double':
        return 8
    elif mavlink_type == 'char':
        return 1
    else:
        raise Exception('unsupported MAVLink type - please fix me')
    

def mavfmt(field):
    '''work out the struct format for a type'''
    map = {
        'float'    : 'f',
        'double'   : 'd',
        'char'     : 'c',
        'int8_t'   : 'b',
        'uint8_t'  : 'B',
        'uint8_t_mavlink_version'  : 'B',
        'int16_t'  : 'h',
        'uint16_t' : 'H',
        'int32_t'  : 'i',
        'uint32_t' : 'I',
        'int64_t'  : 'q',
        'uint64_t' : 'Q',
        }

    if field.array_length:
        if field.type in ['char', 'int8_t', 'uint8_t']:
            return str(field.array_length)+'s'
        return str(field.array_length)+map[field.type]
    return map[field.type]


def generate_preamble(outf):
    print("Generating preamble")
    t.write(outf, 
"""
-- Wireshark dissector for the MAVLink protocol (please see http://qgroundcontrol.org/mavlink/start for details) 

mavlink_proto = Proto("mavlink_proto", "MAVLink protocol")
f = mavlink_proto.fields

""" )
    
    
def generate_body_fields(outf):
    t.write(outf, 
"""
f.magic = ProtoField.uint8("mavlink_proto.magic", "Magic value / version", base.HEX)
f.length = ProtoField.uint8("mavlink_proto.length", "Payload length")
f.sequence = ProtoField.uint8("mavlink_proto.sequence", "Packet sequence")
f.sysid = ProtoField.uint8("mavlink_proto.sysid", "System id", base.HEX)
f.compid = ProtoField.uint8("mavlink_proto.compid", "Component id", base.HEX)
f.msgid = ProtoField.uint8("mavlink_proto.msgid", "Message id", base.HEX)
f.crc = ProtoField.uint16("mavlink_proto.crc", "Message CRC", base.HEX)
f.payload = ProtoField.uint8("mavlink_proto.crc", "Payload", base.DEC, messageName)
f.rawheader = ProtoField.bytes("mavlink_proto.rawheader", "Unparsable header fragment")
f.rawpayload = ProtoField.bytes("mavlink_proto.rawpayload", "Unparsable payload")

""")


def generate_msg_table(outf, msgs):
    t.write(outf, """
messageName = {
""")
    for msg in msgs:
        assert isinstance(msg, mavparse.MAVType)
        t.write(outf, """
    [${msgid}] = '${msgname}',
""", {'msgid':msg.id, 'msgname':msg.name})

    t.write(outf, """
}

""")
        

def generate_msg_fields(outf, msg):
    assert isinstance(msg, mavparse.MAVType)
    for f in msg.fields:
        assert isinstance(f, mavparse.MAVField)
        mtype = f.type
        ltype = lua_type(mtype)
        count = f.array_length if f.array_length>0 else 1

        # string is no array, but string of chars
        if mtype == 'char' and count > 1: 
            count = 1
            ltype = 'string'
        
        for i in range(0,count):
            if count>1: 
                array_text = '[' + str(i) + ']'
                index_text = '_' + str(i)
            else:
                array_text = ''
                index_text = ''
                
            t.write(outf,
"""
f.${fmsg}_${fname}${findex} = ProtoField.${ftype}("mavlink_proto.${fmsg}_${fname}${findex}", "${fname}${farray} (${ftype})")
""", {'fmsg':msg.name, 'ftype':ltype, 'fname':f.name, 'findex':index_text, 'farray':array_text})        

    t.write(outf, '\n\n')

def generate_field_dissector(outf, msg, field):
    assert isinstance(field, mavparse.MAVField)
    
    mtype = field.type
    size = type_size(mtype)
    ltype = lua_type(mtype)
    count = field.array_length if field.array_length>0 else 1

    # string is no array but string of chars
    if mtype == 'char': 
        size = count
        count = 1
    
    # handle arrays, but not strings
    
    for i in range(0,count):
        if count>1: 
            index_text = '_' + str(i)
        else:
            index_text = ''
        t.write(outf,
"""
    tree:add_le(f.${fmsg}_${fname}${findex}, buffer(offset, ${fbytes}))
    offset = offset + ${fbytes}
    
""", {'fname':field.name, 'ftype':mtype, 'fmsg': msg.name, 'fbytes':size, 'findex':index_text})
    

def generate_payload_dissector(outf, msg):
    assert isinstance(msg, mavparse.MAVType)
    t.write(outf, 
"""
-- dissect payload of message type ${msgname}
function dissect_payload_${msgid}(buffer, tree, msgid, offset)
""", {'msgid':msg.id, 'msgname':msg.name})
    
    for f in msg.fields:
        generate_field_dissector(outf, msg, f)


    t.write(outf, 
"""
    return offset
end


""")
    

def generate_packet_dis(outf):
    t.write(outf, 
"""
-- dissector function
function mavlink_proto.dissector(buffer,pinfo,tree)
    local offset = 0
            
    local subtree = tree:add (mavlink_proto, buffer(), "MAVLink Protocol ("..buffer:len()..")")

    -- decode protocol version first
    local version = buffer(offset,1):uint()
    local protocolString = ""
    
    if (version == 0xfe) then
            protocolString = "MAVLink 1.0"
    elseif (version == 0x55) then
            protocolString = "MAVLink 0.9"
    else
            protocolString = "unknown"
    end	

    -- some Wireshark decoration
    pinfo.cols.protocol = protocolString
    local ts = pinfo.abs_ts
    local flags = math.floor(((ts - math.floor(ts))*1000000) + 0.5)
    
    local crc_error = bit.band(flags, 0x01)
    local length_error = bit.band(flags, 0x02)
    
    if length_error > 0 then
        pinfo.cols.info:append ("Invalid message length   ")
        subtree:add_expert_info(PI_MALFORMED, PI_ERROR, "Invalid message length")
    end
    if crc_error > 0 then
        pinfo.cols.info:append ("Invalid CRC   ")
        subtree:add_expert_info(PI_CHECKSUM, PI_WARN, "Invalid message CRC")
    end

    -- HEADER ----------------------------------------
    
    local msgid
    if (buffer:len() - 2 - offset > 6) then
        -- normal header
        local header = subtree:add("Header")
        header:add(f.magic,version)
        offset = offset + 1
        
        local length = buffer(offset,1)
        header:add(f.length, length)
        offset = offset + 1
        
        local sequence = buffer(offset,1)
        header:add(f.sequence, sequence)
        offset = offset + 1
        
        local sysid = buffer(offset,1)
        header:add(f.sysid, sysid)
        offset = offset + 1
    
        local compid = buffer(offset,1)
        header:add(f.compid, compid)
        offset = offset + 1
        
        pinfo.cols.src = "System: "..tostring(sysid:uint())..', Component: '..tostring(compid:uint())
    
        msgid = buffer(offset,1)
        header:add(f.msgid, msgid)
        offset = offset + 1
    else 
        -- handle truncated header
        local hsize = buffer:len() - 2 - offset
        subtree:add(f.rawheader, buffer(offset, hsize))
        offset = offset + hsize
    end


    -- BODY ----------------------------------------
    
    -- dynamically call the type-specific payload dissector    
    local msgnr = msgid:uint()
    local dissect_payload_fn = "dissect_payload_"..tostring(msgnr)
    local fn = _G[dissect_payload_fn]
    
    if (fn == nil) then
        pinfo.cols.info:append ("Unkown message type   ")
        subtree:add_expert_info(PI_MALFORMED, PI_ERROR, "Unkown message type")
    end

    -- do not stumble into exceptions while trying to parse junk
    if (fn == nil) or (length_error ~= 0) then
        size = buffer:len() - 2 - offset
        subtree:add(f.rawpayload, buffer(offset,size))
        offset = offset + size
    else
        local payload = subtree:add(f.payload, msgid)
        pinfo.cols.dst:set(messageName[msgid:uint()])
        offset = fn(buffer, payload, msgid, offset)
    end

    -- CRC ----------------------------------------
    local crc = buffer(offset,2)
    subtree:add_le(f.crc, crc)
    offset = offset + 2

end


""")
    


def generate_epilog(outf):
    print ("Generating epilog")
    t.write(outf, 
"""   
-- bind protocol dissector to USER0 linktype

wtap_encap = DissectorTable.get("wtap_encap")
wtap_encap:add(wtap.USER0, mavlink_proto)
""")

def generate(basename, xml):
    '''generate complete python implemenation'''
    if basename.endswith('.lua'):
        filename = basename
    else:
        filename = basename + '.lua'

    msgs = []
    enums = []
    filelist = []
    for x in xml:
        msgs.extend(x.message)
        enums.extend(x.enum)
        filelist.append(os.path.basename(x.filename))

    for m in msgs:
        if xml[0].little_endian:
            m.fmtstr = '<'
        else:
            m.fmtstr = '>'
        for f in m.ordered_fields:
            m.fmtstr += mavfmt(f)
        m.order_map = [ 0 ] * len(m.fieldnames)
        for i in range(0, len(m.fieldnames)):
            m.order_map[i] = m.ordered_fieldnames.index(m.fieldnames[i])

    print("Generating %s" % filename)
    outf = open(filename, "w")
    generate_preamble(outf)
    generate_msg_table(outf, msgs)
    generate_body_fields(outf)
    
    for m in msgs:
        generate_msg_fields(outf, m)
    
    for m in msgs:
        generate_payload_dissector(outf, m)
    
    generate_packet_dis(outf)
#    generate_enums(outf, enums)
#    generate_message_ids(outf, msgs)
#    generate_classes(outf, msgs)
#    generate_mavlink_class(outf, msgs, xml[0])
#    generate_methods(outf, msgs)
    generate_epilog(outf)
    outf.close()
    print("Generated %s OK" % filename)


########NEW FILE########
__FILENAME__ = mavparse
#!/usr/bin/env python
'''
mavlink python parse functions

Copyright Andrew Tridgell 2011
Released under GNU GPL version 3 or later
'''

import xml.parsers.expat, os, errno, time, sys, operator

PROTOCOL_0_9 = "0.9"
PROTOCOL_1_0 = "1.0"

class MAVParseError(Exception):
    def __init__(self, message, inner_exception=None):
        self.message = message
        self.inner_exception = inner_exception
        self.exception_info = sys.exc_info()
    def __str__(self):
        return self.message

class MAVField(object):
    def __init__(self, name, type, print_format, xml, description='', enum=''):
        self.name = name
        self.name_upper = name.upper()
        self.description = description
        self.array_length = 0
        self.enum = enum
        self.omit_arg = False
        self.const_value = None
        self.print_format = print_format
        lengths = {
        'float'    : 4,
        'double'   : 8,
        'char'     : 1,
        'int8_t'   : 1,
        'uint8_t'  : 1,
        'uint8_t_mavlink_version'  : 1,
        'int16_t'  : 2,
        'uint16_t' : 2,
        'int32_t'  : 4,
        'uint32_t' : 4,
        'int64_t'  : 8,
        'uint64_t' : 8,
        }

        if type=='uint8_t_mavlink_version':
            type = 'uint8_t'
            self.omit_arg = True
            self.const_value = xml.version

        aidx = type.find("[")
        if aidx != -1:
            assert type[-1:] == ']'
            self.array_length = int(type[aidx+1:-1])
            type = type[0:aidx]
            if type == 'array':
                type = 'int8_t'
        if type in lengths:
            self.type_length = lengths[type]
            self.type = type
        elif (type+"_t") in lengths:
            self.type_length = lengths[type+"_t"]
            self.type = type+'_t'
        else:
            raise MAVParseError("unknown type '%s'" % type)
        if self.array_length != 0:
            self.wire_length = self.array_length * self.type_length
        else:
            self.wire_length = self.type_length
        self.type_upper = self.type.upper()

    def gen_test_value(self, i):
        '''generate a testsuite value for a MAVField'''
        if self.const_value:
            return self.const_value
        elif self.type == 'float':
            return 17.0 + self.wire_offset*7 + i
        elif self.type == 'double':
            return 123.0 + self.wire_offset*7 + i
        elif self.type == 'char':
            return chr(ord('A') + (self.wire_offset + i)%26)
        elif self.type in [ 'int8_t', 'uint8_t' ]:
            return (5 + self.wire_offset*67 + i) & 0xFF
        elif self.type in ['int16_t', 'uint16_t']:
            return (17235 + self.wire_offset*52 + i) & 0xFFFF
        elif self.type in ['int32_t', 'uint32_t']:
            return (963497464 + self.wire_offset*52 + i)&0xFFFFFFFF
        elif self.type in ['int64_t', 'uint64_t']:
            return 93372036854775807 + self.wire_offset*63 + i
        else:
            raise MAVError('unknown type %s' % self.type)

    def set_test_value(self):
        '''set a testsuite value for a MAVField'''
        if self.array_length:
            self.test_value = []
            for i in range(self.array_length):
                self.test_value.append(self.gen_test_value(i))
        else:
                self.test_value = self.gen_test_value(0)
        if self.type == 'char' and self.array_length:
            v = ""
            for c in self.test_value:
                v += c
            self.test_value = v[:-1]


class MAVType(object):
    def __init__(self, name, id, linenumber, description=''):
        self.name = name
        self.name_lower = name.lower()
        self.linenumber = linenumber
        self.id = int(id)
        self.description = description
        self.fields = []
        self.fieldnames = []

class MAVEnumParam(object):
    def __init__(self, index, description=''):
        self.index = index
        self.description = description

class MAVEnumEntry(object):
    def __init__(self, name, value, description='', end_marker=False):
        self.name = name
        self.value = value
        self.description = description
        self.param = []
        self.end_marker = end_marker

class MAVEnum(object):
    def __init__(self, name, linenumber, description=''):
        self.name = name
        self.description = description
        self.entry = []
        self.highest_value = 0
        self.linenumber = linenumber

class MAVXML(object):
    '''parse a mavlink XML file'''
    def __init__(self, filename, wire_protocol_version=PROTOCOL_0_9):
        self.filename = filename
        self.basename = os.path.basename(filename)
        if self.basename.lower().endswith(".xml"):
            self.basename = self.basename[:-4]
        self.basename_upper = self.basename.upper()
        self.message = []
        self.enum = []
        self.parse_time = time.asctime()
        self.version = 2
        self.include = []
        self.wire_protocol_version = wire_protocol_version

        if wire_protocol_version == PROTOCOL_0_9:
            self.protocol_marker = ord('U')
            self.sort_fields = False
            self.little_endian = False
            self.crc_extra = False
        elif wire_protocol_version == PROTOCOL_1_0:
            self.protocol_marker = 0xFE
            self.sort_fields = True
            self.little_endian = True
            self.crc_extra = True
        else:
            print("Unknown wire protocol version")
            print("Available versions are: %s %s" % (PROTOCOL_0_9, PROTOCOL_1_0))
            raise MAVParseError('Unknown MAVLink wire protocol version %s' % wire_protocol_version)

        in_element_list = []

        def check_attrs(attrs, check, where):
            for c in check:
                if not c in attrs:
                    raise MAVParseError('expected missing %s "%s" attribute at %s:%u' % (
                        where, c, filename, p.CurrentLineNumber))

        def start_element(name, attrs):
            in_element_list.append(name)
            in_element = '.'.join(in_element_list)
            #print in_element
            if in_element == "mavlink.messages.message":
                check_attrs(attrs, ['name', 'id'], 'message')
                self.message.append(MAVType(attrs['name'], attrs['id'], p.CurrentLineNumber))
            elif in_element == "mavlink.messages.message.field":
                check_attrs(attrs, ['name', 'type'], 'field')
                if 'print_format' in attrs:
                    print_format = attrs['print_format']
                else:
                    print_format = None
                if 'enum' in attrs:
                    enum = attrs['enum']
                else:
                    enum = ''
                self.message[-1].fields.append(MAVField(attrs['name'], attrs['type'],
                                                        print_format, self, enum=enum))
            elif in_element == "mavlink.enums.enum":
                check_attrs(attrs, ['name'], 'enum')
                self.enum.append(MAVEnum(attrs['name'], p.CurrentLineNumber))
            elif in_element == "mavlink.enums.enum.entry":
                check_attrs(attrs, ['name'], 'enum entry')
                if 'value' in attrs:
                    value = eval(attrs['value'])
                else:
                    value = self.enum[-1].highest_value + 1
                if (value > self.enum[-1].highest_value):
                    self.enum[-1].highest_value = value
                self.enum[-1].entry.append(MAVEnumEntry(attrs['name'], value))
            elif in_element == "mavlink.enums.enum.entry.param":
                check_attrs(attrs, ['index'], 'enum param')
                self.enum[-1].entry[-1].param.append(MAVEnumParam(attrs['index']))

        def end_element(name):
            in_element = '.'.join(in_element_list)
            if in_element == "mavlink.enums.enum":
                # add a ENUM_END
                self.enum[-1].entry.append(MAVEnumEntry("%s_ENUM_END" % self.enum[-1].name,
                                                        self.enum[-1].highest_value+1, end_marker=True))
            in_element_list.pop()

        def char_data(data):
            in_element = '.'.join(in_element_list)
            if in_element == "mavlink.messages.message.description":
                self.message[-1].description += data
            elif in_element == "mavlink.messages.message.field":
                self.message[-1].fields[-1].description += data
            elif in_element == "mavlink.enums.enum.description":
                self.enum[-1].description += data
            elif in_element == "mavlink.enums.enum.entry.description":
                self.enum[-1].entry[-1].description += data
            elif in_element == "mavlink.enums.enum.entry.param":
                self.enum[-1].entry[-1].param[-1].description += data
            elif in_element == "mavlink.version":
                self.version = int(data)
            elif in_element == "mavlink.include":
                self.include.append(data)

        f = open(filename, mode='rb')
        p = xml.parsers.expat.ParserCreate()
        p.StartElementHandler = start_element
        p.EndElementHandler = end_element
        p.CharacterDataHandler = char_data
        p.ParseFile(f)
        f.close()

        self.message_lengths = [ 0 ] * 256
        self.message_crcs = [ 0 ] * 256
        self.message_names = [ None ] * 256
        self.largest_payload = 0

        for m in self.message:
            m.wire_length = 0
            m.fieldnames = []
            m.fieldlengths = []
            m.ordered_fieldnames = []
            if self.sort_fields:
                m.ordered_fields = sorted(m.fields,
                                          key=operator.attrgetter('type_length'),
                                          reverse=True)
            else:
                m.ordered_fields = m.fields
            for f in m.fields:
                m.fieldnames.append(f.name)
                L = f.array_length
                if L == 0:
                    m.fieldlengths.append(1)
                elif L > 1 and f.type == 'char':
                    m.fieldlengths.append(1)
                else:
                    m.fieldlengths.append(L)
            for f in m.ordered_fields:
                f.wire_offset = m.wire_length
                m.wire_length += f.wire_length
                m.ordered_fieldnames.append(f.name)
                f.set_test_value()
            m.num_fields = len(m.fieldnames)
            if m.num_fields > 64:
                raise MAVParseError("num_fields=%u : Maximum number of field names allowed is" % (
                    m.num_fields, 64))
            m.crc_extra = message_checksum(m)
            self.message_lengths[m.id] = m.wire_length
            self.message_names[m.id] = m.name
            self.message_crcs[m.id] = m.crc_extra
            if m.wire_length > self.largest_payload:
                self.largest_payload = m.wire_length

            if m.wire_length+8 > 64:
                print("Note: message %s is longer than 64 bytes long (%u bytes), which can cause fragmentation since many radio modems use 64 bytes as maximum air transfer unit." % (m.name, m.wire_length+8))

    def __str__(self):
        return "MAVXML for %s from %s (%u message, %u enums)" % (
            self.basename, self.filename, len(self.message), len(self.enum))


def message_checksum(msg):
    '''calculate a 8-bit checksum of the key fields of a message, so we
       can detect incompatible XML changes'''
    from .mavcrc import x25crc
    crc = x25crc(msg.name + ' ')
    for f in msg.ordered_fields:
        crc.accumulate(f.type + ' ')
        crc.accumulate(f.name + ' ')
        if f.array_length:
            crc.accumulate(chr(f.array_length))
    return (crc.crc&0xFF) ^ (crc.crc>>8)

def merge_enums(xml):
    '''merge enums between XML files'''
    emap = {}
    for x in xml:
        newenums = []
        for enum in x.enum:
            if enum.name in emap:
                emap[enum.name].entry.pop() # remove end marker
                emap[enum.name].entry.extend(enum.entry)
                print("Merged enum %s" % enum.name)
            else:
                newenums.append(enum)
                emap[enum.name] = enum
        x.enum = newenums
    # sort by value
    for e in emap:
        emap[e].entry = sorted(emap[e].entry,
                               key=operator.attrgetter('value'),
                               reverse=False)


def check_duplicates(xml):
    '''check for duplicate message IDs'''

    merge_enums(xml)

    msgmap = {}
    enummap = {}
    for x in xml:
        for m in x.message:
            if m.id in msgmap:
                print("ERROR: Duplicate message id %u for %s (%s:%u) also used by %s" % (
                    m.id, m.name,
                    x.filename, m.linenumber,
                    msgmap[m.id]))
                return True
            fieldset = set()
            for f in m.fields:
                if f.name in fieldset:
                    print("ERROR: Duplicate field %s in message %s (%s:%u)" % (
                        f.name, m.name,
                        x.filename, m.linenumber))
                    return True
                fieldset.add(f.name)
            msgmap[m.id] = '%s (%s:%u)' % (m.name, x.filename, m.linenumber)
        for enum in x.enum:
            for entry in enum.entry:
                s1 = "%s.%s" % (enum.name, entry.name)
                s2 = "%s.%s" % (enum.name, entry.value)
                if s1 in enummap or s2 in enummap:
                    print("ERROR: Duplicate enums %s/%s at %s:%u and %s" % (
                        s1, entry.value, x.filename, enum.linenumber,
                        enummap.get(s1) or enummap.get(s2)))
                    return True
                enummap[s1] = "%s:%u" % (x.filename, enum.linenumber)
                enummap[s2] = "%s:%u" % (x.filename, enum.linenumber)

    return False



def total_msgs(xml):
    '''count total number of msgs'''
    count = 0
    for x in xml:
        count += len(x.message)
    return count

def mkdir_p(dir):
    try:
        os.makedirs(dir)
    except OSError as exc:
        if exc.errno == errno.EEXIST:
            pass
        else: raise

# check version consistent
# add test.xml
# finish test suite
# printf style error macro, if defined call errors

########NEW FILE########
__FILENAME__ = mavtemplate
#!/usr/bin/env python
'''
simple templating system for mavlink generator

Copyright Andrew Tridgell 2011
Released under GNU GPL version 3 or later
'''

from .mavparse import MAVParseError

class MAVTemplate(object):
    '''simple templating system'''
    def __init__(self,
                 start_var_token="${", 
                 end_var_token="}", 
                 start_rep_token="${{", 
                 end_rep_token="}}",
                 trim_leading_lf=True,
                 checkmissing=True):
        self.start_var_token = start_var_token
        self.end_var_token = end_var_token
        self.start_rep_token = start_rep_token
        self.end_rep_token = end_rep_token
        self.trim_leading_lf = trim_leading_lf
        self.checkmissing = checkmissing

    def find_end(self, text, start_token, end_token, ignore_end_token=None):
        '''find the of a token.
        Returns the offset in the string immediately after the matching end_token'''
        if not text.startswith(start_token):
            raise MAVParseError("invalid token start")
        offset = len(start_token)
        nesting = 1
        while nesting > 0:
            idx1 = text[offset:].find(start_token)
            idx2 = text[offset:].find(end_token)
            # Check for false positives due to another similar token
            # For example, make sure idx2 points to the second '}' in ${{field: ${name}}}
            if ignore_end_token:
                combined_token = ignore_end_token + end_token
                if text[offset+idx2:offset+idx2+len(combined_token)] == combined_token:
                    idx2 += len(ignore_end_token)
            if idx1 == -1 and idx2 == -1:
                raise MAVParseError("token nesting error")
            if idx1 == -1 or idx1 > idx2:
                offset += idx2 + len(end_token)
                nesting -= 1
            else:
                offset += idx1 + len(start_token)
                nesting += 1
        return offset

    def find_var_end(self, text):
        '''find the of a variable'''
        return self.find_end(text, self.start_var_token, self.end_var_token)

    def find_rep_end(self, text):
        '''find the of a repitition'''
        return self.find_end(text, self.start_rep_token, self.end_rep_token, ignore_end_token=self.end_var_token)

    def substitute(self, text, subvars={},
                   trim_leading_lf=None, checkmissing=None):
        '''substitute variables in a string'''

        if trim_leading_lf is None:
            trim_leading_lf = self.trim_leading_lf
        if checkmissing is None:
            checkmissing = self.checkmissing

        # handle repititions
        while True:
            subidx = text.find(self.start_rep_token)
            if subidx == -1:
                break
            endidx = self.find_rep_end(text[subidx:])
            if endidx == -1:
                raise MAVParseError("missing end macro in %s" % text[subidx:])
            part1 = text[0:subidx]
            part2 = text[subidx+len(self.start_rep_token):subidx+(endidx-len(self.end_rep_token))]
            part3 = text[subidx+endidx:]
            a = part2.split(':')
            field_name = a[0]
            rest = ':'.join(a[1:])
            v = getattr(subvars, field_name, None)
            if v is None:
                raise MAVParseError('unable to find field %s' % field_name)
            t1 = part1
            for f in v:
                t1 += self.substitute(rest, f, trim_leading_lf=False, checkmissing=False)
            if len(v) != 0 and t1[-1] in ["\n", ","]:
                t1 = t1[:-1]
            t1 += part3
            text = t1
                
        if trim_leading_lf:
            if text[0] == '\n':
                text = text[1:]
        while True:
            idx = text.find(self.start_var_token)
            if idx == -1:
                return text
            endidx = text[idx:].find(self.end_var_token)
            if endidx == -1:
                raise MAVParseError('missing end of variable: %s' % text[idx:idx+10])
            varname = text[idx+2:idx+endidx]
            if isinstance(subvars, dict):
                if not varname in subvars:
                    if checkmissing:
                        raise MAVParseError("unknown variable in '%s%s%s'" % (
                            self.start_var_token, varname, self.end_var_token))
                    return text[0:idx+endidx] + self.substitute(text[idx+endidx:], subvars,
                                                                trim_leading_lf=False, checkmissing=False)
                value = subvars[varname]
            else:
                value = getattr(subvars, varname, None)
                if value is None:
                    if checkmissing:
                        raise MAVParseError("unknown variable in '%s%s%s'" % (
                            self.start_var_token, varname, self.end_var_token))
                    return text[0:idx+endidx] + self.substitute(text[idx+endidx:], subvars,
                                                                trim_leading_lf=False, checkmissing=False)
            text = text.replace("%s%s%s" % (self.start_var_token, varname, self.end_var_token), str(value))
        return text

    def write(self, file, text, subvars={}, trim_leading_lf=True):
        '''write to a file with variable substitution'''
        file.write(self.substitute(text, subvars=subvars, trim_leading_lf=trim_leading_lf))

########NEW FILE########
__FILENAME__ = mavtestgen
#!/usr/bin/env python
'''
generate a MAVLink test suite

Copyright Andrew Tridgell 2011
Released under GNU GPL version 3 or later
'''

import sys, textwrap
from optparse import OptionParser

# mavparse is up a directory level
sys.path.append('..')
import mavparse

def gen_value(f, i, language):
    '''generate a test value for the ith field of a message'''
    type = f.type

    # could be an array
    if type.find("[") != -1:
        aidx = type.find("[")
        basetype = type[0:aidx]
        if basetype == "array":
            basetype = "int8_t"
        if language == 'C':
            return '(const %s *)"%s%u"' % (basetype, f.name, i)
        return '"%s%u"' % (f.name, i)

    if type == 'float':
        return 17.0 + i*7
    if type == 'char':
        return 'A' + i
    if type == 'int8_t':
        return 5 + i
    if type in ['int8_t', 'uint8_t']:
        return 5 + i
    if type in ['uint8_t_mavlink_version']:
        return 2
    if type in ['int16_t', 'uint16_t']:
        return 17235 + i*52
    if type in ['int32_t', 'uint32_t']:
        v = 963497464 + i*52
        if language == 'C':
            return "%sL" % v
        return v
    if type in ['int64_t', 'uint64_t']:
        v = 9223372036854775807 + i*63
        if language == 'C':
            return "%sLL" % v
        return v



def generate_methods_python(outf, msgs):
    outf.write("""
'''
MAVLink protocol test implementation (auto-generated by mavtestgen.py)

Generated from: %s

Note: this file has been auto-generated. DO NOT EDIT
'''

import mavlink

def generate_outputs(mav):
    '''generate all message types as outputs'''
""")
    for m in msgs:
        if m.name == "HEARTBEAT": continue
        outf.write("\tmav.%s_send(" % m.name.lower())
        for i in range(0, len(m.fields)):
            f = m.fields[i]
            outf.write("%s=%s" % (f.name, gen_value(f, i, 'py')))
            if i != len(m.fields)-1:
                outf.write(",")
        outf.write(")\n")


def generate_methods_C(outf, msgs):
    outf.write("""
/*
MAVLink protocol test implementation (auto-generated by mavtestgen.py)

Generated from: %s

Note: this file has been auto-generated. DO NOT EDIT
*/

static void mavtest_generate_outputs(mavlink_channel_t chan)
{
""")
    for m in msgs:
        if m.name == "HEARTBEAT": continue
        outf.write("\tmavlink_msg_%s_send(chan," % m.name.lower())
        for i in range(0, len(m.fields)):
            f = m.fields[i]
            outf.write("%s" % gen_value(f, i, 'C'))
            if i != len(m.fields)-1:
                outf.write(",")
        outf.write(");\n")
    outf.write("}\n")



######################################################################
'''main program'''

parser = OptionParser("%prog [options] <XML files>")
parser.add_option("-o", "--output", dest="output", default="mavtest", help="output folder [default: %default]")
(opts, args) = parser.parse_args()

if len(args) < 1:
    parser.error("You must supply at least one MAVLink XML protocol definition")
    

msgs = []
enums = []

for fname in args:
    (m, e) = mavparse.parse_mavlink_xml(fname)
    msgs.extend(m)
    enums.extend(e)


if mavparse.check_duplicates(msgs):
    sys.exit(1)

print("Found %u MAVLink message types" % len(msgs))

print("Generating python %s" % (opts.output+'.py'))
outf = open(opts.output + '.py', "w")
generate_methods_python(outf, msgs)
outf.close()

print("Generating C %s" % (opts.output+'.h'))
outf = open(opts.output + '.h', "w")
generate_methods_C(outf, msgs)
outf.close()

print("Generated %s OK" % opts.output)

########NEW FILE########
__FILENAME__ = mavextra
#!/usr/bin/env python
'''
useful extra functions for use by mavlink clients

Copyright Andrew Tridgell 2011
Released under GNU GPL version 3 or later
'''

import os, sys
from math import *

try:
    # rotmat doesn't work on Python3.2 yet
    from rotmat import Vector3, Matrix3
except Exception:
    pass


def kmh(mps):
    '''convert m/s to Km/h'''
    return mps*3.6

def altitude(SCALED_PRESSURE, ground_pressure=None, ground_temp=None):
    '''calculate barometric altitude'''
    from pymavlink import mavutil
    self = mavutil.mavfile_global
    if ground_pressure is None:
        if self.param('GND_ABS_PRESS', None) is None:
            return 0
        ground_pressure = self.param('GND_ABS_PRESS', 1)
    if ground_temp is None:
        ground_temp = self.param('GND_TEMP', 0)
    scaling = ground_pressure / (SCALED_PRESSURE.press_abs*100.0)
    temp = ground_temp + 273.15
    return log(scaling) * temp * 29271.267 * 0.001

def altitude2(SCALED_PRESSURE, ground_pressure=None, ground_temp=None):
    '''calculate barometric altitude'''
    from pymavlink import mavutil
    self = mavutil.mavfile_global
    if ground_pressure is None:
        if self.param('GND_ABS_PRESS', None) is None:
            return 0
        ground_pressure = self.param('GND_ABS_PRESS', 1)
    if ground_temp is None:
        ground_temp = self.param('GND_TEMP', 0)
    scaling = SCALED_PRESSURE.press_abs*100.0 / ground_pressure
    temp = ground_temp + 273.15
    return 153.8462 * temp * (1.0 - exp(0.190259 * log(scaling)))

def mag_heading(RAW_IMU, ATTITUDE, declination=None, SENSOR_OFFSETS=None, ofs=None):
    '''calculate heading from raw magnetometer'''
    if declination is None:
        import mavutil
        declination = degrees(mavutil.mavfile_global.param('COMPASS_DEC', 0))
    mag_x = RAW_IMU.xmag
    mag_y = RAW_IMU.ymag
    mag_z = RAW_IMU.zmag
    if SENSOR_OFFSETS is not None and ofs is not None:
        mag_x += ofs[0] - SENSOR_OFFSETS.mag_ofs_x
        mag_y += ofs[1] - SENSOR_OFFSETS.mag_ofs_y
        mag_z += ofs[2] - SENSOR_OFFSETS.mag_ofs_z

    # go via a DCM matrix to match the APM calculation
    dcm_matrix = rotation(ATTITUDE)
    cos_pitch_sq = 1.0-(dcm_matrix.c.x*dcm_matrix.c.x)
    headY = mag_y * dcm_matrix.c.z - mag_z * dcm_matrix.c.y
    headX = mag_x * cos_pitch_sq - dcm_matrix.c.x * (mag_y * dcm_matrix.c.y + mag_z * dcm_matrix.c.z)

    heading = degrees(atan2(-headY,headX)) + declination
    if heading < 0:
        heading += 360
    return heading

def mag_heading_motors(RAW_IMU, ATTITUDE, declination, SENSOR_OFFSETS, ofs, SERVO_OUTPUT_RAW, motor_ofs):
    '''calculate heading from raw magnetometer'''
    ofs = get_motor_offsets(SERVO_OUTPUT_RAW, ofs, motor_ofs)

    if declination is None:
        import mavutil
        declination = degrees(mavutil.mavfile_global.param('COMPASS_DEC', 0))
    mag_x = RAW_IMU.xmag
    mag_y = RAW_IMU.ymag
    mag_z = RAW_IMU.zmag
    if SENSOR_OFFSETS is not None and ofs is not None:
        mag_x += ofs[0] - SENSOR_OFFSETS.mag_ofs_x
        mag_y += ofs[1] - SENSOR_OFFSETS.mag_ofs_y
        mag_z += ofs[2] - SENSOR_OFFSETS.mag_ofs_z

    headX = mag_x*cos(ATTITUDE.pitch) + mag_y*sin(ATTITUDE.roll)*sin(ATTITUDE.pitch) + mag_z*cos(ATTITUDE.roll)*sin(ATTITUDE.pitch)
    headY = mag_y*cos(ATTITUDE.roll) - mag_z*sin(ATTITUDE.roll)
    heading = degrees(atan2(-headY,headX)) + declination
    if heading < 0:
        heading += 360
    return heading

def mag_field(RAW_IMU, SENSOR_OFFSETS=None, ofs=None):
    '''calculate magnetic field strength from raw magnetometer'''
    mag_x = RAW_IMU.xmag
    mag_y = RAW_IMU.ymag
    mag_z = RAW_IMU.zmag
    if SENSOR_OFFSETS is not None and ofs is not None:
        mag_x += ofs[0] - SENSOR_OFFSETS.mag_ofs_x
        mag_y += ofs[1] - SENSOR_OFFSETS.mag_ofs_y
        mag_z += ofs[2] - SENSOR_OFFSETS.mag_ofs_z
    return sqrt(mag_x**2 + mag_y**2 + mag_z**2)

def mag_field_df(MAG, mofs=True):
    '''calculate magnetic field strength from raw magnetometer (dataflash version)'''
    mag_x = MAG.MagX - MAG.OfsX
    mag_y = MAG.MagY - MAG.OfsY
    mag_z = MAG.MagZ - MAG.OfsZ

    if mofs:
        mag_x += MAG.MOfsX
        mag_y += MAG.MOfsY
        mag_z += MAG.MOfsZ

    return sqrt(mag_x**2 + mag_y**2 + mag_z**2)

def get_motor_offsets(SERVO_OUTPUT_RAW, ofs, motor_ofs):
    '''calculate magnetic field strength from raw magnetometer'''
    import mavutil
    self = mavutil.mavfile_global

    m = SERVO_OUTPUT_RAW
    motor_pwm = m.servo1_raw + m.servo2_raw + m.servo3_raw + m.servo4_raw
    motor_pwm *= 0.25
    rc3_min = self.param('RC3_MIN', 1100)
    rc3_max = self.param('RC3_MAX', 1900)
    motor = (motor_pwm - rc3_min) / (rc3_max - rc3_min)
    if motor > 1.0:
        motor = 1.0
    if motor < 0.0:
        motor = 0.0

    motor_offsets0 = motor_ofs[0] * motor
    motor_offsets1 = motor_ofs[1] * motor
    motor_offsets2 = motor_ofs[2] * motor
    ofs = (ofs[0] + motor_offsets0, ofs[1] + motor_offsets1, ofs[2] + motor_offsets2)

    return ofs

def mag_field_motors(RAW_IMU, SENSOR_OFFSETS, ofs, SERVO_OUTPUT_RAW, motor_ofs):
    '''calculate magnetic field strength from raw magnetometer'''
    mag_x = RAW_IMU.xmag
    mag_y = RAW_IMU.ymag
    mag_z = RAW_IMU.zmag

    ofs = get_motor_offsets(SERVO_OUTPUT_RAW, ofs, motor_ofs)

    if SENSOR_OFFSETS is not None and ofs is not None:
        mag_x += ofs[0] - SENSOR_OFFSETS.mag_ofs_x
        mag_y += ofs[1] - SENSOR_OFFSETS.mag_ofs_y
        mag_z += ofs[2] - SENSOR_OFFSETS.mag_ofs_z
    return sqrt(mag_x**2 + mag_y**2 + mag_z**2)

def angle_diff(angle1, angle2):
    '''show the difference between two angles in degrees'''
    ret = angle1 - angle2
    if ret > 180:
        ret -= 360;
    if ret < -180:
        ret += 360
    return ret

average_data = {}

def average(var, key, N):
    '''average over N points'''
    global average_data
    if not key in average_data:
        average_data[key] = [var]*N
        return var
    average_data[key].pop(0)
    average_data[key].append(var)
    return sum(average_data[key])/N

derivative_data = {}

def second_derivative_5(var, key):
    '''5 point 2nd derivative'''
    global derivative_data
    import mavutil
    tnow = mavutil.mavfile_global.timestamp

    if not key in derivative_data:
        derivative_data[key] = (tnow, [var]*5)
        return 0
    (last_time, data) = derivative_data[key]
    data.pop(0)
    data.append(var)
    derivative_data[key] = (tnow, data)
    h = (tnow - last_time)
    # N=5 2nd derivative from
    # http://www.holoborodko.com/pavel/numerical-methods/numerical-derivative/smooth-low-noise-differentiators/
    ret = ((data[4] + data[0]) - 2*data[2]) / (4*h**2)
    return ret

def second_derivative_9(var, key):
    '''9 point 2nd derivative'''
    global derivative_data
    import mavutil
    tnow = mavutil.mavfile_global.timestamp

    if not key in derivative_data:
        derivative_data[key] = (tnow, [var]*9)
        return 0
    (last_time, data) = derivative_data[key]
    data.pop(0)
    data.append(var)
    derivative_data[key] = (tnow, data)
    h = (tnow - last_time)
    # N=5 2nd derivative from
    # http://www.holoborodko.com/pavel/numerical-methods/numerical-derivative/smooth-low-noise-differentiators/
    f = data
    ret = ((f[8] + f[0]) + 4*(f[7] + f[1]) + 4*(f[6]+f[2]) - 4*(f[5]+f[3]) - 10*f[4])/(64*h**2)
    return ret

lowpass_data = {}

def lowpass(var, key, factor):
    '''a simple lowpass filter'''
    global lowpass_data
    if not key in lowpass_data:
        lowpass_data[key] = var
    else:
        lowpass_data[key] = factor*lowpass_data[key] + (1.0 - factor)*var
    return lowpass_data[key]

last_diff = {}

def diff(var, key):
    '''calculate differences between values'''
    global last_diff
    ret = 0
    if not key in last_diff:
        last_diff[key] = var
        return 0
    ret = var - last_diff[key]
    last_diff[key] = var
    return ret

last_delta = {}

def delta(var, key, tusec=None):
    '''calculate slope'''
    global last_delta
    if tusec is not None:
        tnow = tusec * 1.0e-6
    else:
        import mavutil
        tnow = mavutil.mavfile_global.timestamp
    dv = 0
    ret = 0
    if key in last_delta:
        (last_v, last_t, last_ret) = last_delta[key]
        if last_t == tnow:
            return last_ret
        if tnow == last_t:
            ret = 0
        else:
            ret = (var - last_v) / (tnow - last_t)
    last_delta[key] = (var, tnow, ret)
    return ret

def delta_angle(var, key, tusec=None):
    '''calculate slope of an angle'''
    global last_delta
    if tusec is not None:
        tnow = tusec * 1.0e-6
    else:
        import mavutil
        tnow = mavutil.mavfile_global.timestamp
    dv = 0
    ret = 0
    if key in last_delta:
        (last_v, last_t, last_ret) = last_delta[key]
        if last_t == tnow:
            return last_ret
        if tnow == last_t:
            ret = 0
        else:
            dv = var - last_v
            if dv > 180:
                dv -= 360
            if dv < -180:
                dv += 360
            ret = dv / (tnow - last_t)
    last_delta[key] = (var, tnow, ret)
    return ret

def roll_estimate(RAW_IMU,GPS_RAW_INT=None,ATTITUDE=None,SENSOR_OFFSETS=None, ofs=None, mul=None,smooth=0.7):
    '''estimate roll from accelerometer'''
    rx = RAW_IMU.xacc * 9.81 / 1000.0
    ry = RAW_IMU.yacc * 9.81 / 1000.0
    rz = RAW_IMU.zacc * 9.81 / 1000.0
    if ATTITUDE is not None and GPS_RAW_INT is not None:
        ry -= ATTITUDE.yawspeed * GPS_RAW_INT.vel*0.01
        rz += ATTITUDE.pitchspeed * GPS_RAW_INT.vel*0.01
    if SENSOR_OFFSETS is not None and ofs is not None:
        rx += SENSOR_OFFSETS.accel_cal_x
        ry += SENSOR_OFFSETS.accel_cal_y
        rz += SENSOR_OFFSETS.accel_cal_z
        rx -= ofs[0]
        ry -= ofs[1]
        rz -= ofs[2]
        if mul is not None:
            rx *= mul[0]
            ry *= mul[1]
            rz *= mul[2]
    return lowpass(degrees(-asin(ry/sqrt(rx**2+ry**2+rz**2))),'_roll',smooth)

def pitch_estimate(RAW_IMU, GPS_RAW_INT=None,ATTITUDE=None, SENSOR_OFFSETS=None, ofs=None, mul=None, smooth=0.7):
    '''estimate pitch from accelerometer'''
    rx = RAW_IMU.xacc * 9.81 / 1000.0
    ry = RAW_IMU.yacc * 9.81 / 1000.0
    rz = RAW_IMU.zacc * 9.81 / 1000.0
    if ATTITUDE is not None and GPS_RAW_INT is not None:
        ry -= ATTITUDE.yawspeed * GPS_RAW_INT.vel*0.01
        rz += ATTITUDE.pitchspeed * GPS_RAW_INT.vel*0.01
    if SENSOR_OFFSETS is not None and ofs is not None:
        rx += SENSOR_OFFSETS.accel_cal_x
        ry += SENSOR_OFFSETS.accel_cal_y
        rz += SENSOR_OFFSETS.accel_cal_z
        rx -= ofs[0]
        ry -= ofs[1]
        rz -= ofs[2]
        if mul is not None:
            rx *= mul[0]
            ry *= mul[1]
            rz *= mul[2]
    return lowpass(degrees(asin(rx/sqrt(rx**2+ry**2+rz**2))),'_pitch',smooth)

def rotation(ATTITUDE):
    '''return the current DCM rotation matrix'''
    r = Matrix3()
    r.from_euler(ATTITUDE.roll, ATTITUDE.pitch, ATTITUDE.yaw)
    return r

def mag_rotation(RAW_IMU, inclination, declination):
    '''return an attitude rotation matrix that is consistent with the current mag
       vector'''
    m_body = Vector3(RAW_IMU.xmag, RAW_IMU.ymag, RAW_IMU.zmag)
    m_earth = Vector3(m_body.length(), 0, 0)

    r = Matrix3()
    r.from_euler(0, -radians(inclination), radians(declination))
    m_earth = r * m_earth

    r.from_two_vectors(m_earth, m_body)
    return r

def mag_yaw(RAW_IMU, inclination, declination):
    '''estimate yaw from mag'''
    m = mag_rotation(RAW_IMU, inclination, declination)
    (r, p, y) = m.to_euler()
    y = degrees(y)
    if y < 0:
        y += 360
    return y

def mag_pitch(RAW_IMU, inclination, declination):
    '''estimate pithc from mag'''
    m = mag_rotation(RAW_IMU, inclination, declination)
    (r, p, y) = m.to_euler()
    return degrees(p)

def mag_roll(RAW_IMU, inclination, declination):
    '''estimate roll from mag'''
    m = mag_rotation(RAW_IMU, inclination, declination)
    (r, p, y) = m.to_euler()
    return degrees(r)

def expected_mag(RAW_IMU, ATTITUDE, inclination, declination):
    '''return expected mag vector'''
    m_body = Vector3(RAW_IMU.xmag, RAW_IMU.ymag, RAW_IMU.zmag)
    field_strength = m_body.length()

    m = rotation(ATTITUDE)

    r = Matrix3()
    r.from_euler(0, -radians(inclination), radians(declination))
    m_earth = r * Vector3(field_strength, 0, 0)

    return m.transposed() * m_earth

def mag_discrepancy(RAW_IMU, ATTITUDE, inclination, declination=None):
    '''give the magnitude of the discrepancy between observed and expected magnetic field'''
    if declination is None:
        import mavutil
        declination = degrees(mavutil.mavfile_global.param('COMPASS_DEC', 0))
    expected = expected_mag(RAW_IMU, ATTITUDE, inclination, declination)
    mag = Vector3(RAW_IMU.xmag, RAW_IMU.ymag, RAW_IMU.zmag)
    return degrees(expected.angle(mag))


def mag_inclination(RAW_IMU, ATTITUDE, declination=None):
    '''give the magnitude of the discrepancy between observed and expected magnetic field'''
    if declination is None:
        import mavutil
        declination = degrees(mavutil.mavfile_global.param('COMPASS_DEC', 0))
    r = rotation(ATTITUDE)
    mag1 = Vector3(RAW_IMU.xmag, RAW_IMU.ymag, RAW_IMU.zmag)
    mag1 = r * mag1
    mag2 = Vector3(cos(radians(declination)), sin(radians(declination)), 0)
    inclination = degrees(mag1.angle(mag2))
    if RAW_IMU.zmag < 0:
        inclination = -inclination
    return inclination

def expected_magx(RAW_IMU, ATTITUDE, inclination, declination):
    '''estimate  from mag'''
    v = expected_mag(RAW_IMU, ATTITUDE, inclination, declination)
    return v.x

def expected_magy(RAW_IMU, ATTITUDE, inclination, declination):
    '''estimate  from mag'''
    v = expected_mag(RAW_IMU, ATTITUDE, inclination, declination)
    return v.y

def expected_magz(RAW_IMU, ATTITUDE, inclination, declination):
    '''estimate  from mag'''
    v = expected_mag(RAW_IMU, ATTITUDE, inclination, declination)
    return v.z

def gravity(RAW_IMU, SENSOR_OFFSETS=None, ofs=None, mul=None, smooth=0.7):
    '''estimate pitch from accelerometer'''
    rx = RAW_IMU.xacc * 9.81 / 1000.0
    ry = RAW_IMU.yacc * 9.81 / 1000.0
    rz = RAW_IMU.zacc * 9.81 / 1000.0
    if SENSOR_OFFSETS is not None and ofs is not None:
        rx += SENSOR_OFFSETS.accel_cal_x
        ry += SENSOR_OFFSETS.accel_cal_y
        rz += SENSOR_OFFSETS.accel_cal_z
        rx -= ofs[0]
        ry -= ofs[1]
        rz -= ofs[2]
        if mul is not None:
            rx *= mul[0]
            ry *= mul[1]
            rz *= mul[2]
    return lowpass(sqrt(rx**2+ry**2+rz**2),'_gravity',smooth)



def pitch_sim(SIMSTATE, GPS_RAW):
    '''estimate pitch from SIMSTATE accels'''
    xacc = SIMSTATE.xacc - lowpass(delta(GPS_RAW.v,"v")*6.6, "v", 0.9)
    zacc = SIMSTATE.zacc
    zacc += SIMSTATE.ygyro * GPS_RAW.v;
    if xacc/zacc >= 1:
        return 0
    if xacc/zacc <= -1:
        return -0
    return degrees(-asin(xacc/zacc))

def distance_two(GPS_RAW1, GPS_RAW2):
    '''distance between two points'''
    if hasattr(GPS_RAW1, 'Lat'):
        lat1 = radians(GPS_RAW1.Lat)
        lat2 = radians(GPS_RAW2.Lat)
        lon1 = radians(GPS_RAW1.Lng)
        lon2 = radians(GPS_RAW2.Lng)
    elif hasattr(GPS_RAW1, 'cog'):
        lat1 = radians(GPS_RAW1.lat)*1.0e-7
        lat2 = radians(GPS_RAW2.lat)*1.0e-7
        lon1 = radians(GPS_RAW1.lon)*1.0e-7
        lon2 = radians(GPS_RAW2.lon)*1.0e-7
    else:
        lat1 = radians(GPS_RAW1.lat)
        lat2 = radians(GPS_RAW2.lat)
        lon1 = radians(GPS_RAW1.lon)
        lon2 = radians(GPS_RAW2.lon)
    dLat = lat2 - lat1
    dLon = lon2 - lon1

    a = sin(0.5*dLat)**2 + sin(0.5*dLon)**2 * cos(lat1) * cos(lat2)
    c = 2.0 * atan2(sqrt(a), sqrt(1.0-a))
    return 6371 * 1000 * c


first_fix = None

def distance_home(GPS_RAW):
    '''distance from first fix point'''
    global first_fix
    if (hasattr(GPS_RAW, 'fix_type') and GPS_RAW.fix_type < 2) or \
       (hasattr(GPS_RAW, 'Status')   and GPS_RAW.Status   < 2):
        return 0

    if first_fix == None:
        first_fix = GPS_RAW
        return 0
    return distance_two(GPS_RAW, first_fix)

def sawtooth(ATTITUDE, amplitude=2.0, period=5.0):
    '''sawtooth pattern based on uptime'''
    mins = (ATTITUDE.usec * 1.0e-6)/60
    p = fmod(mins, period*2)
    if p < period:
        return amplitude * (p/period)
    return amplitude * (period - (p-period))/period

def rate_of_turn(speed, bank):
    '''return expected rate of turn in degrees/s for given speed in m/s and
       bank angle in degrees'''
    if abs(speed) < 2 or abs(bank) > 80:
        return 0
    ret = degrees(9.81*tan(radians(bank))/speed)
    return ret

def wingloading(bank):
    '''return expected wing loading factor for a bank angle in radians'''
    return 1.0/cos(bank)

def airspeed(VFR_HUD, ratio=None, used_ratio=None):
    '''recompute airspeed with a different ARSPD_RATIO'''
    import mavutil
    mav = mavutil.mavfile_global
    if ratio is None:
        ratio = 1.9936 # APM default
    if used_ratio is None:
        if 'ARSPD_RATIO' in mav.params:
            used_ratio = mav.params['ARSPD_RATIO']
        else:
            print("no ARSPD_RATIO in mav.params")
            used_ratio = ratio
    airspeed_pressure = (VFR_HUD.airspeed**2) / used_ratio
    airspeed = sqrt(airspeed_pressure * ratio)
    return airspeed

def airspeed_ratio(VFR_HUD):
    '''recompute airspeed with a different ARSPD_RATIO'''
    import mavutil
    mav = mavutil.mavfile_global
    airspeed_pressure = (VFR_HUD.airspeed**2) / ratio
    airspeed = sqrt(airspeed_pressure * ratio)
    return airspeed

def airspeed_voltage(VFR_HUD, ratio=None):
    '''back-calculate the voltage the airspeed sensor must have seen'''
    import mavutil
    mav = mavutil.mavfile_global
    if ratio is None:
        ratio = 1.9936 # APM default
    if 'ARSPD_RATIO' in mav.params:
        used_ratio = mav.params['ARSPD_RATIO']
    else:
        used_ratio = ratio
    if 'ARSPD_OFFSET' in mav.params:
        offset = mav.params['ARSPD_OFFSET']
    else:
        return -1
    airspeed_pressure = (pow(VFR_HUD.airspeed,2)) / used_ratio
    raw = airspeed_pressure + offset
    SCALING_OLD_CALIBRATION = 204.8
    voltage = 5.0 * raw / 4096
    return voltage


def earth_rates(ATTITUDE):
    '''return angular velocities in earth frame'''
    from math import sin, cos, tan, fabs

    p     = ATTITUDE.rollspeed
    q     = ATTITUDE.pitchspeed
    r     = ATTITUDE.yawspeed
    phi   = ATTITUDE.roll
    theta = ATTITUDE.pitch
    psi   = ATTITUDE.yaw

    phiDot   = p + tan(theta)*(q*sin(phi) + r*cos(phi))
    thetaDot = q*cos(phi) - r*sin(phi)
    if fabs(cos(theta)) < 1.0e-20:
        theta += 1.0e-10
    psiDot   = (q*sin(phi) + r*cos(phi))/cos(theta)
    return (phiDot, thetaDot, psiDot)

def roll_rate(ATTITUDE):
    '''return roll rate in earth frame'''
    (phiDot, thetaDot, psiDot) = earth_rates(ATTITUDE)
    return phiDot

def pitch_rate(ATTITUDE):
    '''return pitch rate in earth frame'''
    (phiDot, thetaDot, psiDot) = earth_rates(ATTITUDE)
    return thetaDot

def yaw_rate(ATTITUDE):
    '''return yaw rate in earth frame'''
    (phiDot, thetaDot, psiDot) = earth_rates(ATTITUDE)
    return psiDot


def gps_velocity(GLOBAL_POSITION_INT):
    '''return GPS velocity vector'''
    return Vector3(GLOBAL_POSITION_INT.vx, GLOBAL_POSITION_INT.vy, GLOBAL_POSITION_INT.vz) * 0.01


def gps_velocity_old(GPS_RAW_INT):
    '''return GPS velocity vector'''
    return Vector3(GPS_RAW_INT.vel*0.01*cos(radians(GPS_RAW_INT.cog*0.01)),
                   GPS_RAW_INT.vel*0.01*sin(radians(GPS_RAW_INT.cog*0.01)), 0)

def gps_velocity_body(GPS_RAW_INT, ATTITUDE):
    '''return GPS velocity vector in body frame'''
    r = rotation(ATTITUDE)
    return r.transposed() * Vector3(GPS_RAW_INT.vel*0.01*cos(radians(GPS_RAW_INT.cog*0.01)),
                                    GPS_RAW_INT.vel*0.01*sin(radians(GPS_RAW_INT.cog*0.01)),
                                    -tan(ATTITUDE.pitch)*GPS_RAW_INT.vel*0.01)

def earth_accel(RAW_IMU,ATTITUDE):
    '''return earth frame acceleration vector'''
    r = rotation(ATTITUDE)
    accel = Vector3(RAW_IMU.xacc, RAW_IMU.yacc, RAW_IMU.zacc) * 9.81 * 0.001
    return r * accel

def earth_gyro(RAW_IMU,ATTITUDE):
    '''return earth frame gyro vector'''
    r = rotation(ATTITUDE)
    accel = Vector3(degrees(RAW_IMU.xgyro), degrees(RAW_IMU.ygyro), degrees(RAW_IMU.zgyro)) * 0.001
    return r * accel

def airspeed_energy_error(NAV_CONTROLLER_OUTPUT, VFR_HUD):
    '''return airspeed energy error matching APM internals
    This is positive when we are going too slow
    '''
    aspeed_cm = VFR_HUD.airspeed*100
    target_airspeed = NAV_CONTROLLER_OUTPUT.aspd_error + aspeed_cm
    airspeed_energy_error = ((target_airspeed*target_airspeed) - (aspeed_cm*aspeed_cm))*0.00005
    return airspeed_energy_error


def energy_error(NAV_CONTROLLER_OUTPUT, VFR_HUD):
    '''return energy error matching APM internals
    This is positive when we are too low or going too slow
    '''
    aspeed_energy_error = airspeed_energy_error(NAV_CONTROLLER_OUTPUT, VFR_HUD)
    alt_error = NAV_CONTROLLER_OUTPUT.alt_error*100
    energy_error = aspeed_energy_error + alt_error*0.098
    return energy_error

def rover_turn_circle(SERVO_OUTPUT_RAW):
    '''return turning circle (diameter) in meters for steering_angle in degrees
    '''

    # this matches Toms slash
    max_wheel_turn = 35
    wheelbase      = 0.335
    wheeltrack     = 0.296

    steering_angle = max_wheel_turn * (SERVO_OUTPUT_RAW.servo1_raw - 1500) / 400.0
    theta = radians(steering_angle)
    return (wheeltrack/2) + (wheelbase/sin(theta))

def rover_yaw_rate(VFR_HUD, SERVO_OUTPUT_RAW):
    '''return yaw rate in degrees/second given steering_angle and speed'''
    max_wheel_turn=35
    speed = VFR_HUD.groundspeed
    # assume 1100 to 1900 PWM on steering
    steering_angle = max_wheel_turn * (SERVO_OUTPUT_RAW.servo1_raw - 1500) / 400.0
    if abs(steering_angle) < 1.0e-6 or abs(speed) < 1.0e-6:
        return 0
    d = rover_turn_circle(SERVO_OUTPUT_RAW)
    c = pi * d
    t = c / speed
    rate = 360.0 / t
    return rate

def rover_lat_accel(VFR_HUD, SERVO_OUTPUT_RAW):
    '''return lateral acceleration in m/s/s'''
    speed = VFR_HUD.groundspeed
    yaw_rate = rover_yaw_rate(VFR_HUD, SERVO_OUTPUT_RAW)
    accel = radians(yaw_rate) * speed
    return accel


def demix1(servo1, servo2):
    '''de-mix a mixed servo output'''
    s1 = servo1 - 1500
    s2 = servo2 - 1500
    out1 = (s1+s2)/2
    out2 = (s1-s2)/2
    return out1+1500

def demix2(servo1, servo2):
    '''de-mix a mixed servo output'''
    s1 = servo1 - 1500
    s2 = servo2 - 1500
    out1 = (s1+s2)/2
    out2 = (s1-s2)/2
    return out2+1500

def wrap_180(angle):
    if angle > 180:
        angle -= 360.0
    if angle < -180:
        angle += 360.0
    return angle

    
def wrap_360(angle):
    if angle > 360:
        angle -= 360.0
    if angle < 0:
        angle += 360.0
    return angle

class DCM_State(object):
    '''DCM state object'''
    def __init__(self, roll, pitch, yaw):
        self.dcm = Matrix3()
        self.dcm2 = Matrix3()
        self.dcm.from_euler(radians(roll), radians(pitch), radians(yaw))
        self.dcm2.from_euler(radians(roll), radians(pitch), radians(yaw))
        self.mag = Vector3()
        self.gyro = Vector3()
        self.accel = Vector3()
        self.gps = None
        self.rate = 50.0
        self.kp = 0.2
        self.kp_yaw = 0.3
        self.omega_P = Vector3()
        self.omega_P_yaw = Vector3()
        self.omega_I = Vector3() # (-0.00199045287445, -0.00653007719666, -0.00714212376624)
        self.omega_I_sum = Vector3()
        self.omega_I_sum_time = 0
        self.omega = Vector3()
        self.ra_sum = Vector3()
        self.last_delta_angle = Vector3()
        self.last_velocity = Vector3()
        (self.roll, self.pitch, self.yaw) = self.dcm.to_euler()
        (self.roll2, self.pitch2, self.yaw2) = self.dcm2.to_euler()
        
    def update(self, gyro, accel, mag, GPS):
        if self.gyro != gyro or self.accel != accel:
            delta_angle = (gyro+self.omega_I) / self.rate
            self.dcm.rotate(delta_angle)
            correction = self.last_delta_angle % delta_angle
            #print (delta_angle - self.last_delta_angle) * 58.0
            corrected_delta = delta_angle + 0.0833333 * correction
            self.dcm2.rotate(corrected_delta)
            self.last_delta_angle = delta_angle

            self.dcm.normalize()
            self.dcm2.normalize()

            self.gyro = gyro
            self.accel = accel
            (self.roll, self.pitch, self.yaw) = self.dcm.to_euler()
            (self.roll2, self.pitch2, self.yaw2) = self.dcm2.to_euler()

dcm_state = None

def DCM_update(IMU, ATT, MAG, GPS):
    '''implement full DCM system'''
    global dcm_state
    if dcm_state is None:
        dcm_state = DCM_State(ATT.Roll, ATT.Pitch, ATT.Yaw)

    mag   = Vector3(MAG.MagX, MAG.MagY, MAG.MagZ)
    gyro  = Vector3(IMU.GyrX, IMU.GyrY, IMU.GyrZ)
    accel = Vector3(IMU.AccX, IMU.AccY, IMU.AccZ)
    accel2 = Vector3(IMU.AccX, IMU.AccY, IMU.AccZ)
    dcm_state.update(gyro, accel, mag, GPS)
    return dcm_state

class PX4_State(object):
    '''PX4 DCM state object'''
    def __init__(self, roll, pitch, yaw, timestamp):
        self.dcm = Matrix3()
        self.dcm.from_euler(radians(roll), radians(pitch), radians(yaw))
        self.gyro = Vector3()
        self.accel = Vector3()
        self.timestamp = timestamp
        (self.roll, self.pitch, self.yaw) = self.dcm.to_euler()
        
    def update(self, gyro, accel, timestamp):
        if self.gyro != gyro or self.accel != accel:
            delta_angle = gyro * (timestamp - self.timestamp)
            self.timestamp = timestamp
            self.dcm.rotate(delta_angle)
            self.dcm.normalize()
            self.gyro = gyro
            self.accel = accel
            (self.roll, self.pitch, self.yaw) = self.dcm.to_euler()

px4_state = None

def PX4_update(IMU, ATT):
    '''implement full DCM using PX4 native SD log data'''
    global px4_state
    if px4_state is None:
        px4_state = PX4_State(degrees(ATT.Roll), degrees(ATT.Pitch), degrees(ATT.Yaw), IMU._timestamp)

    gyro  = Vector3(IMU.GyroX, IMU.GyroY, IMU.GyroZ)
    accel = Vector3(IMU.AccX, IMU.AccY, IMU.AccZ)
    px4_state.update(gyro, accel, IMU._timestamp)
    return px4_state

_downsample_N = 0

def downsample(N):
    '''conditional that is true on every Nth sample'''
    global _downsample_N
    _downsample_N = (_downsample_N + 1) % N
    return _downsample_N == 0

def armed(HEARTBEAT):
    '''return 1 if armed, 0 if not'''
    from pymavlink import mavutil
    if HEARTBEAT.type == mavutil.mavlink.MAV_TYPE_GCS:
        self = mavutil.mavfile_global
        if self.motors_armed():
            return 1
        return 0
    if HEARTBEAT.base_mode & mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED:
        return 1
    return 0

def rotation_df(ATT):
    '''return the current DCM rotation matrix'''
    r = Matrix3()
    r.from_euler(radians(ATT.Roll), radians(ATT.Pitch), radians(ATT.Yaw))
    return r

def rotation2(AHRS2):
    '''return the current DCM rotation matrix'''
    r = Matrix3()
    r.from_euler(AHRS2.roll, AHRS2.pitch, AHRS2.yaw)
    return r

def earth_accel2(RAW_IMU,ATTITUDE):
    '''return earth frame acceleration vector from AHRS2'''
    r = rotation2(ATTITUDE)
    accel = Vector3(RAW_IMU.xacc, RAW_IMU.yacc, RAW_IMU.zacc) * 9.81 * 0.001
    return r * accel

def earth_accel_df(IMU,ATT):
    '''return earth frame acceleration vector from df log'''
    r = rotation_df(ATT)
    accel = Vector3(IMU.AccX, IMU.AccY, IMU.AccZ)
    return r * accel

def earth_accel2_df(IMU,IMU2,ATT):
    '''return earth frame acceleration vector from df log'''
    r = rotation_df(ATT)
    accel1 = Vector3(IMU.AccX, IMU.AccY, IMU.AccZ)
    accel2 = Vector3(IMU2.AccX, IMU2.AccY, IMU2.AccZ)
    accel = 0.5 * (accel1 + accel2)
    return r * accel

def gps_velocity_df(GPS):
    '''return GPS velocity vector'''
    vx = GPS.Spd * cos(radians(GPS.GCrs))
    vy = GPS.Spd * sin(radians(GPS.GCrs))
    return Vector3(vx, vy, GPS.VZ)

def distance_gps2(GPS, GPS2):
    '''distance between two points'''
    if GPS.TimeMS != GPS2.TimeMS:
        # reject messages not time aligned
        return None
    return distance_two(GPS, GPS2)


radius_of_earth = 6378100.0 # in meters

def wrap_valid_longitude(lon):
  ''' wrap a longitude value around to always have a value in the range
      [-180, +180) i.e 0 => 0, 1 => 1, -1 => -1, 181 => -179, -181 => 179
  '''
  return (((lon + 180.0) % 360.0) - 180.0)

def gps_newpos(lat, lon, bearing, distance):
  '''extrapolate latitude/longitude given a heading and distance
  thanks to http://www.movable-type.co.uk/scripts/latlong.html
  '''
  import math
  lat1 = math.radians(lat)
  lon1 = math.radians(lon)
  brng = math.radians(bearing)
  dr = distance/radius_of_earth
  
  lat2 = math.asin(math.sin(lat1)*math.cos(dr) +
                   math.cos(lat1)*math.sin(dr)*math.cos(brng))
  lon2 = lon1 + math.atan2(math.sin(brng)*math.sin(dr)*math.cos(lat1), 
                           math.cos(dr)-math.sin(lat1)*math.sin(lat2))
  return (math.degrees(lat2), wrap_valid_longitude(math.degrees(lon2)))

def gps_offset(lat, lon, east, north):
  '''return new lat/lon after moving east/north
  by the given number of meters'''
  import math
  bearing = math.degrees(math.atan2(east, north))
  distance = math.sqrt(east**2 + north**2)
  return gps_newpos(lat, lon, bearing, distance)

ekf_home = None

def ekf1_pos(EKF1):
  '''calculate EKF position when EKF disabled'''
  global ekf_home
  from pymavlink import mavutil
  self = mavutil.mavfile_global
  if ekf_home is None:
      if not 'GPS' in self.messages or self.messages['GPS'].Status != 3:
          return None
      ekf_home = self.messages['GPS']
      (ekf_home.Lat, ekf_home.Lng) = gps_offset(ekf_home.Lat, ekf_home.Lng, -EKF1.PE, -EKF1.PN)
  (lat,lon) = gps_offset(ekf_home.Lat, ekf_home.Lng, EKF1.PE, EKF1.PN)
  return (lat, lon)


########NEW FILE########
__FILENAME__ = mavparm
'''
module for loading/saving sets of mavlink parameters
'''

import fnmatch, math, time

class MAVParmDict(dict):
    def __init__(self, *args):
        dict.__init__(self, args)
        # some parameters should not be loaded from files
        self.exclude_load = ['SYSID_SW_MREV', 'SYS_NUM_RESETS', 'ARSPD_OFFSET', 'GND_ABS_PRESS',
                             'GND_TEMP', 'CMD_TOTAL', 'CMD_INDEX', 'LOG_LASTFILE', 'FENCE_TOTAL',
                             'FORMAT_VERSION' ]
        self.mindelta = 0.000001


    def mavset(self, mav, name, value, retries=3):
        '''set a parameter on a mavlink connection'''
        got_ack = False
        while retries > 0 and not got_ack:
            retries -= 1
            mav.param_set_send(name.upper(), float(value))
            tstart = time.time()
            while time.time() - tstart < 1:
                ack = mav.recv_match(type='PARAM_VALUE', blocking=False)
                if ack == None:
                    time.sleep(0.1)
                    continue
                if str(name).upper() == str(ack.param_id).upper():
                    got_ack = True
                    self.__setitem__(name, float(value))
                    break
        if not got_ack:
            print("timeout setting %s to %f" % (name, float(value)))
            return False
        return True


    def save(self, filename, wildcard='*', verbose=False):
        '''save parameters to a file'''
        f = open(filename, mode='w')
        k = self.keys()
        k.sort()
        count = 0
        for p in k:
            if p and fnmatch.fnmatch(str(p).upper(), wildcard.upper()):
                f.write("%-16.16s %f\n" % (p, self.__getitem__(p)))
                count += 1
        f.close()
        if verbose:
            print("Saved %u parameters to %s" % (count, filename))


    def load(self, filename, wildcard='*', mav=None, check=True):
        '''load parameters from a file'''
        try:
            f = open(filename, mode='r')
        except:
            print("Failed to open file '%s'" % filename)
            return False
        count = 0
        changed = 0
        for line in f:
            line = line.strip()
            if not line or line[0] == "#":
                continue
            line = line.replace(',',' ')
            a = line.split()
            if len(a) != 2:
                print("Invalid line: %s" % line)
                continue
            # some parameters should not be loaded from files
            if a[0] in self.exclude_load:
                continue
            if not fnmatch.fnmatch(a[0].upper(), wildcard.upper()):
                continue
            if mav is not None:
                if check:
                    if a[0] not in self.keys():
                        print("Unknown parameter %s" % a[0])
                        continue
                    old_value = self.__getitem__(a[0])
                    if math.fabs(old_value - float(a[1])) <= self.mindelta:
                        count += 1
                        continue
                    if self.mavset(mav, a[0], a[1]):
                        print("changed %s from %f to %f" % (a[0], old_value, float(a[1])))
                else:
                    print("set %s to %f" % (a[0], float(a[1])))
                    self.mavset(mav, a[0], a[1])
                changed += 1
            else:
                self.__setitem__(a[0], float(a[1]))
            count += 1
        f.close()
        if mav is not None:
            print("Loaded %u parameters from %s (changed %u)" % (count, filename, changed))
        else:
            print("Loaded %u parameters from %s" % (count, filename))
        return True

    def show(self, wildcard='*'):
        '''show parameters'''
        k = sorted(self.keys())
        for p in k:
            if fnmatch.fnmatch(str(p).upper(), wildcard.upper()):
                print("%-16.16s %f" % (str(p), self.get(p)))

    def diff(self, filename, wildcard='*'):
        '''show differences with another parameter file'''
        other = MAVParmDict()
        if not other.load(filename):
            return
        keys = sorted(list(set(self.keys()).union(set(other.keys()))))
        for k in keys:
            if not fnmatch.fnmatch(str(k).upper(), wildcard.upper()):
                continue
            if not k in other:
                print("%-16.16s              %12.4f" % (k, self[k]))
            elif not k in self:
                print("%-16.16s %12.4f" % (k, other[k]))
            elif abs(self[k] - other[k]) > self.mindelta:
                print("%-16.16s %12.4f %12.4f" % (k, other[k], self[k]))
                
        

########NEW FILE########
__FILENAME__ = mavutil
#!/usr/bin/env python
'''
mavlink python utility functions

Copyright Andrew Tridgell 2011
Released under GNU GPL version 3 or later
'''

import socket, math, struct, time, os, fnmatch, array, sys, errno

# adding these extra imports allows pymavlink to be used directly with pyinstaller
# without having complex spec files
import json
from pymavlink.dialects.v10 import ardupilotmega

# these imports allow for mavgraph and mavlogdump to use maths expressions more easily
from math import *
from .mavextra import *

'''
Support having a $HOME/.pymavlink/mavextra.py for extra graphing functions
'''
home = os.getenv('HOME')
if home is not None:
    extra = os.path.join(home, '.pymavlink', 'mavextra.py')
    if os.path.exists(extra):
        import imp
        mavuser = imp.load_source('pymavlink.mavuser', extra)
        from pymavlink.mavuser import *

mavlink = None

def mavlink10():
    '''return True if using MAVLink 1.0'''
    return not 'MAVLINK09' in os.environ

def evaluate_expression(expression, vars):
    '''evaluation an expression'''
    try:
        v = eval(expression, globals(), vars)
    except NameError:
        return None
    except ZeroDivisionError:
        return None
    return v

def evaluate_condition(condition, vars):
    '''evaluation a conditional (boolean) statement'''
    if condition is None:
        return True
    v = evaluate_expression(condition, vars)
    if v is None:
        return False
    return v

mavfile_global = None

class location(object):
    '''represent a GPS coordinate'''
    def __init__(self, lat, lng, alt=0, heading=0):
        self.lat = lat
        self.lng = lng
        self.alt = alt
        self.heading = heading

    def __str__(self):
        return "lat=%.6f,lon=%.6f,alt=%.1f" % (self.lat, self.lng, self.alt)

def set_dialect(dialect):
    '''set the MAVLink dialect to work with.
    For example, set_dialect("ardupilotmega")
    '''
    global mavlink, current_dialect
    from .generator import mavparse
    if mavlink is None or mavlink.WIRE_PROTOCOL_VERSION == "1.0" or not 'MAVLINK09' in os.environ:
        wire_protocol = mavparse.PROTOCOL_1_0
        modname = "pymavlink.dialects.v10." + dialect
    else:
        wire_protocol = mavparse.PROTOCOL_0_9
        modname = "pymavlink.dialects.v09." + dialect

    try:
        mod = __import__(modname)
    except Exception:
        # auto-generate the dialect module
        from generator.mavgen import mavgen_python_dialect
        mavgen_python_dialect(dialect, wire_protocol)
        mod = __import__(modname)
    components = modname.split('.')
    for comp in components[1:]:
        mod = getattr(mod, comp)
    current_dialect = dialect
    mavlink = mod

# allow for a MAVLINK_DIALECT environment variable
if not 'MAVLINK_DIALECT' in os.environ:
    os.environ['MAVLINK_DIALECT'] = 'ardupilotmega'
set_dialect(os.environ['MAVLINK_DIALECT'])

class mavfile(object):
    '''a generic mavlink port'''
    def __init__(self, fd, address, source_system=255, notimestamps=False, input=True):
        global mavfile_global
        if input:
            mavfile_global = self
        self.fd = fd
        self.address = address
        self.messages = { 'MAV' : self }
        if mavlink.WIRE_PROTOCOL_VERSION == "1.0":
            self.messages['HOME'] = mavlink.MAVLink_gps_raw_int_message(0,0,0,0,0,0,0,0,0,0)
            mavlink.MAVLink_waypoint_message = mavlink.MAVLink_mission_item_message
        else:
            self.messages['HOME'] = mavlink.MAVLink_gps_raw_message(0,0,0,0,0,0,0,0,0)
        self.params = {}
        self.target_system = 0
        self.target_component = 0
        self.source_system = source_system
        self.first_byte = True
        self.robust_parsing = True
        self.mav = mavlink.MAVLink(self, srcSystem=self.source_system)
        self.mav.robust_parsing = self.robust_parsing
        self.logfile = None
        self.logfile_raw = None
        self.param_fetch_in_progress = False
        self.param_fetch_complete = False
        self.start_time = time.time()
        self.flightmode = "UNKNOWN"
        self.vehicle_type = "UNKNOWN"
        self.mav_type = mavlink.MAV_TYPE_FIXED_WING
        self.base_mode = 0
        self.timestamp = 0
        self.message_hooks = []
        self.idle_hooks = []
        self.uptime = 0.0
        self.notimestamps = notimestamps
        self._timestamp = None
        self.ground_pressure = None
        self.ground_temperature = None
        self.altitude = 0
        self.WIRE_PROTOCOL_VERSION = mavlink.WIRE_PROTOCOL_VERSION
        self.last_seq = {}
        self.mav_loss = 0
        self.mav_count = 0
        self.stop_on_EOF = False

    def auto_mavlink_version(self, buf):
        '''auto-switch mavlink protocol version'''
        global mavlink
        if len(buf) == 0:
            return
        if not ord(buf[0]) in [ 85, 254 ]:
            return
        self.first_byte = False
        if self.WIRE_PROTOCOL_VERSION == "0.9" and ord(buf[0]) == 254:
            self.WIRE_PROTOCOL_VERSION = "1.0"
            set_dialect(current_dialect)
        elif self.WIRE_PROTOCOL_VERSION == "1.0" and ord(buf[0]) == 85:
            self.WIRE_PROTOCOL_VERSION = "0.9"
            set_dialect(current_dialect)
            os.environ['MAVLINK09'] = '1'
        else:
            return
        # switch protocol 
        (callback, callback_args, callback_kwargs) = (self.mav.callback,
                                                      self.mav.callback_args,
                                                      self.mav.callback_kwargs)
        self.mav = mavlink.MAVLink(self, srcSystem=self.source_system)
        self.mav.robust_parsing = self.robust_parsing
        self.WIRE_PROTOCOL_VERSION = mavlink.WIRE_PROTOCOL_VERSION
        (self.mav.callback, self.mav.callback_args, self.mav.callback_kwargs) = (callback,
                                                                                 callback_args,
                                                                                 callback_kwargs)

    def recv(self, n=None):
        '''default recv method'''
        raise RuntimeError('no recv() method supplied')

    def close(self, n=None):
        '''default close method'''
        raise RuntimeError('no close() method supplied')

    def write(self, buf):
        '''default write method'''
        raise RuntimeError('no write() method supplied')

    def pre_message(self):
        '''default pre message call'''
        return

    def set_rtscts(self, enable):
        '''enable/disable RTS/CTS if applicable'''
        return

    def post_message(self, msg):
        '''default post message call'''
        if '_posted' in msg.__dict__:
            return
        msg._posted = True
        msg._timestamp = time.time()
        type = msg.get_type()
        if type != 'HEARTBEAT' or msg.type != mavlink.MAV_TYPE_GCS:
            self.messages[type] = msg

        if 'usec' in msg.__dict__:
            self.uptime = msg.usec * 1.0e-6
        if 'time_boot_ms' in msg.__dict__:
            self.uptime = msg.time_boot_ms * 1.0e-3

        if self._timestamp is not None:
            if self.notimestamps:
                msg._timestamp = self.uptime
            else:
                msg._timestamp = self._timestamp

        src_system = msg.get_srcSystem()
        if not (
            # its the radio or planner
            (src_system == ord('3') and msg.get_srcComponent() == ord('D')) or
            msg.get_type() == 'BAD_DATA'):
            if not src_system in self.last_seq:
                last_seq = -1
            else:
                last_seq = self.last_seq[src_system]
            seq = (last_seq+1) % 256
            seq2 = msg.get_seq()
            if seq != seq2 and last_seq != -1:
                diff = (seq2 - seq) % 256
                self.mav_loss += diff
                #print("lost %u seq=%u seq2=%u last_seq=%u src_system=%u %s" % (diff, seq, seq2, last_seq, src_system, msg.get_type()))
            self.last_seq[src_system] = seq2
            self.mav_count += 1
        
        self.timestamp = msg._timestamp
        if type == 'HEARTBEAT':
            self.target_system = msg.get_srcSystem()
            self.target_component = msg.get_srcComponent()
            if mavlink.WIRE_PROTOCOL_VERSION == '1.0' and msg.type != mavlink.MAV_TYPE_GCS:
                self.flightmode = mode_string_v10(msg)
                self.mav_type = msg.type
                self.base_mode = msg.base_mode
        elif type == 'PARAM_VALUE':
            s = str(msg.param_id)
            self.params[str(msg.param_id)] = msg.param_value
            if msg.param_index+1 == msg.param_count:
                self.param_fetch_in_progress = False
                self.param_fetch_complete = True
        elif type == 'SYS_STATUS' and mavlink.WIRE_PROTOCOL_VERSION == '0.9':
            self.flightmode = mode_string_v09(msg)
        elif type == 'GPS_RAW':
            if self.messages['HOME'].fix_type < 2:
                self.messages['HOME'] = msg
        elif type == 'GPS_RAW_INT':
            if self.messages['HOME'].fix_type < 3:
                self.messages['HOME'] = msg
        for hook in self.message_hooks:
            hook(self, msg)


    def packet_loss(self):
        '''packet loss as a percentage'''
        if self.mav_count == 0:
            return 0
        return (100.0*self.mav_loss)/(self.mav_count+self.mav_loss)


    def recv_msg(self):
        '''message receive routine'''
        self.pre_message()
        while True:
            n = self.mav.bytes_needed()
            s = self.recv(n)
            if len(s) == 0 and (len(self.mav.buf) == 0 or self.stop_on_EOF):
                return None
            if self.logfile_raw:
                self.logfile_raw.write(str(s))
            if self.first_byte:
                self.auto_mavlink_version(s)
            msg = self.mav.parse_char(s)
            if msg:
                if self.logfile and  msg.get_type() != 'BAD_DATA' :
                    usec = int(time.time() * 1.0e6) & ~3
                    self.logfile.write(str(struct.pack('>Q', usec) + msg.get_msgbuf()))
                self.post_message(msg)
                return msg
                
    def recv_match(self, condition=None, type=None, blocking=False, timeout=None):
        '''recv the next MAVLink message that matches the given condition
        type can be a string or a list of strings'''
        if type is not None and not isinstance(type, list):
            type = [type]
        start_time = time.time()
        while True:
            if timeout is not None:
                if start_time + timeout < time.time():
                    return None
            m = self.recv_msg()
            if m is None:
                if blocking:
                    for hook in self.idle_hooks:
                        hook(self)
                    if timeout is None:
                        time.sleep(0.01)
                    else:
                        time.sleep(timeout/2)
                    continue
                return None
            if type is not None and not m.get_type() in type:
                continue
            if not evaluate_condition(condition, self.messages):
                continue
            return m

    def check_condition(self, condition):
        '''check if a condition is true'''
        return evaluate_condition(condition, self.messages)

    def mavlink10(self):
        '''return True if using MAVLink 1.0'''
        return self.WIRE_PROTOCOL_VERSION == "1.0"

    def setup_logfile(self, logfile, mode='w'):
        '''start logging to the given logfile, with timestamps'''
        self.logfile = open(logfile, mode=mode)

    def setup_logfile_raw(self, logfile, mode='w'):
        '''start logging raw bytes to the given logfile, without timestamps'''
        self.logfile_raw = open(logfile, mode=mode)

    def wait_heartbeat(self, blocking=True):
        '''wait for a heartbeat so we know the target system IDs'''
        return self.recv_match(type='HEARTBEAT', blocking=blocking)

    def param_fetch_all(self):
        '''initiate fetch of all parameters'''
        if time.time() - getattr(self, 'param_fetch_start', 0) < 2.0:
            # don't fetch too often
            return
        self.param_fetch_start = time.time()
        self.param_fetch_in_progress = True
        self.mav.param_request_list_send(self.target_system, self.target_component)

    def param_fetch_one(self, name):
        '''initiate fetch of one parameter'''
        try:
            idx = int(name)
            self.mav.param_request_read_send(self.target_system, self.target_component, "", idx)
        except Exception:
            self.mav.param_request_read_send(self.target_system, self.target_component, name, -1)

    def time_since(self, mtype):
        '''return the time since the last message of type mtype was received'''
        if not mtype in self.messages:
            return time.time() - self.start_time
        return time.time() - self.messages[mtype]._timestamp

    def param_set_send(self, parm_name, parm_value, parm_type=None):
        '''wrapper for parameter set'''
        if self.mavlink10():
            if parm_type == None:
                parm_type = mavlink.MAVLINK_TYPE_FLOAT
            self.mav.param_set_send(self.target_system, self.target_component,
                                    parm_name, parm_value, parm_type)
        else:
            self.mav.param_set_send(self.target_system, self.target_component,
                                    parm_name, parm_value)

    def waypoint_request_list_send(self):
        '''wrapper for waypoint_request_list_send'''
        if self.mavlink10():
            self.mav.mission_request_list_send(self.target_system, self.target_component)
        else:
            self.mav.waypoint_request_list_send(self.target_system, self.target_component)

    def waypoint_clear_all_send(self):
        '''wrapper for waypoint_clear_all_send'''
        if self.mavlink10():
            self.mav.mission_clear_all_send(self.target_system, self.target_component)
        else:
            self.mav.waypoint_clear_all_send(self.target_system, self.target_component)

    def waypoint_request_send(self, seq):
        '''wrapper for waypoint_request_send'''
        if self.mavlink10():
            self.mav.mission_request_send(self.target_system, self.target_component, seq)
        else:
            self.mav.waypoint_request_send(self.target_system, self.target_component, seq)

    def waypoint_set_current_send(self, seq):
        '''wrapper for waypoint_set_current_send'''
        if self.mavlink10():
            self.mav.mission_set_current_send(self.target_system, self.target_component, seq)
        else:
            self.mav.waypoint_set_current_send(self.target_system, self.target_component, seq)

    def waypoint_current(self):
        '''return current waypoint'''
        if self.mavlink10():
            m = self.recv_match(type='MISSION_CURRENT', blocking=True)
        else:
            m = self.recv_match(type='WAYPOINT_CURRENT', blocking=True)
        return m.seq

    def waypoint_count_send(self, seq):
        '''wrapper for waypoint_count_send'''
        if self.mavlink10():
            self.mav.mission_count_send(self.target_system, self.target_component, seq)
        else:
            self.mav.waypoint_count_send(self.target_system, self.target_component, seq)

    def set_mode_flag(self, flag, enable):
        '''
        Enables/ disables MAV_MODE_FLAG
        @param flag The mode flag, 
          see MAV_MODE_FLAG enum
        @param enable Enable the flag, (True/False)
        '''
        if self.mavlink10():
            mode = self.base_mode
            if (enable == True):
                mode = mode | flag
            elif (enable == False):
                mode = mode & ~flag
            self.mav.command_long_send(self.target_system, self.target_component,
                                           mavlink.MAV_CMD_DO_SET_MODE, 0,
                                           mode,
                                           0, 0, 0, 0, 0, 0)
        else:
            print("Set mode flag not supported")

    def set_mode_auto(self):
        '''enter auto mode'''
        if self.mavlink10():
            self.mav.command_long_send(self.target_system, self.target_component,
                                       mavlink.MAV_CMD_MISSION_START, 0, 0, 0, 0, 0, 0, 0, 0)
        else:
            MAV_ACTION_SET_AUTO = 13
            self.mav.action_send(self.target_system, self.target_component, MAV_ACTION_SET_AUTO)

    def mode_mapping(self):
        '''return dictionary mapping mode names to numbers, or None if unknown'''
        mav_type = self.field('HEARTBEAT', 'type', self.mav_type)
        if mav_type is None:
            return None
        map = None
        if mav_type in [mavlink.MAV_TYPE_QUADROTOR,
                        mavlink.MAV_TYPE_HELICOPTER,
                        mavlink.MAV_TYPE_HEXAROTOR,
                        mavlink.MAV_TYPE_OCTOROTOR,
                        mavlink.MAV_TYPE_TRICOPTER]:
            map = mode_mapping_acm
        if mav_type == mavlink.MAV_TYPE_FIXED_WING:
            map = mode_mapping_apm
        if mav_type == mavlink.MAV_TYPE_GROUND_ROVER:
            map = mode_mapping_rover
        if mav_type == mavlink.MAV_TYPE_ANTENNA_TRACKER:
            map = mode_mapping_tracker
        if map is None:
            return None
        inv_map = dict((a, b) for (b, a) in map.items())
        return inv_map

    def set_mode(self, mode):
        '''enter arbitrary mode'''
        if isinstance(mode, str):
            map = self.mode_mapping()
            if map is None or mode not in map:
                print("Unknown mode '%s'" % mode)
                return
            mode = map[mode]
        self.mav.set_mode_send(self.target_system,
                               mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED,
                               mode)

    def set_mode_rtl(self):
        '''enter RTL mode'''
        if self.mavlink10():
            self.mav.command_long_send(self.target_system, self.target_component,
                                       mavlink.MAV_CMD_NAV_RETURN_TO_LAUNCH, 0, 0, 0, 0, 0, 0, 0, 0)
        else:
            MAV_ACTION_RETURN = 3
            self.mav.action_send(self.target_system, self.target_component, MAV_ACTION_RETURN)

    def set_mode_manual(self):
        '''enter MANUAL mode'''
        if self.mavlink10():
            self.mav.command_long_send(self.target_system, self.target_component,
                                       mavlink.MAV_CMD_DO_SET_MODE, 0,
                                       mavlink.MAV_MODE_MANUAL_ARMED,
                                       0, 0, 0, 0, 0, 0)
        else:
            MAV_ACTION_SET_MANUAL = 12
            self.mav.action_send(self.target_system, self.target_component, MAV_ACTION_SET_MANUAL)

    def set_mode_fbwa(self):
        '''enter FBWA mode'''
        if self.mavlink10():
            self.mav.command_long_send(self.target_system, self.target_component,
                                       mavlink.MAV_CMD_DO_SET_MODE, 0,
                                       mavlink.MAV_MODE_STABILIZE_ARMED,
                                       0, 0, 0, 0, 0, 0)
        else:
            print("Forcing FBWA not supported")

    def set_mode_loiter(self):
        '''enter LOITER mode'''
        if self.mavlink10():
            self.mav.command_long_send(self.target_system, self.target_component,
                                       mavlink.MAV_CMD_NAV_LOITER_UNLIM, 0, 0, 0, 0, 0, 0, 0, 0)
        else:
            MAV_ACTION_LOITER = 27
            self.mav.action_send(self.target_system, self.target_component, MAV_ACTION_LOITER)

    def set_servo(self, channel, pwm):
        '''set a servo value'''
        self.mav.command_long_send(self.target_system, self.target_component,
                                   mavlink.MAV_CMD_DO_SET_SERVO, 0,
                                   channel, pwm,
                                   0, 0, 0, 0, 0)

    def calibrate_imu(self):
        '''calibrate IMU'''
        if self.mavlink10():
            self.mav.command_long_send(self.target_system, self.target_component,
                                       mavlink.MAV_CMD_PREFLIGHT_CALIBRATION, 0,
                                       1, 1, 1, 1, 0, 0, 0)
        else:
            MAV_ACTION_CALIBRATE_GYRO = 17
            self.mav.action_send(self.target_system, self.target_component, MAV_ACTION_CALIBRATE_GYRO)

    def calibrate_level(self):
        '''calibrate accels'''
        if self.mavlink10():
            self.mav.command_long_send(self.target_system, self.target_component,
                                       mavlink.MAV_CMD_PREFLIGHT_CALIBRATION, 0,
                                       1, 1, 1, 1, 0, 0, 0)
        else:
            MAV_ACTION_CALIBRATE_ACC = 19
            self.mav.action_send(self.target_system, self.target_component, MAV_ACTION_CALIBRATE_ACC)

    def calibrate_pressure(self):
        '''calibrate pressure'''
        if self.mavlink10():
            self.mav.command_long_send(self.target_system, self.target_component,
                                       mavlink.MAV_CMD_PREFLIGHT_CALIBRATION, 0,
                                       0, 0, 1, 0, 0, 0, 0)
        else:
            MAV_ACTION_CALIBRATE_PRESSURE = 20
            self.mav.action_send(self.target_system, self.target_component, MAV_ACTION_CALIBRATE_PRESSURE)

    def reboot_autopilot(self, hold_in_bootloader=False):
        '''reboot the autopilot'''
        if self.mavlink10():
            if hold_in_bootloader:
                param1 = 3
            else:
                param1 = 1
            self.mav.command_long_send(self.target_system, self.target_component,
                                       mavlink.MAV_CMD_PREFLIGHT_REBOOT_SHUTDOWN, 0,
                                       param1, 0, 0, 0, 0, 0, 0)
            # send an old style reboot immediately afterwards in case it is an older firmware
            # that doesn't understand the new convention
            self.mav.command_long_send(self.target_system, self.target_component,
                                       mavlink.MAV_CMD_PREFLIGHT_REBOOT_SHUTDOWN, 0,
                                       1, 0, 0, 0, 0, 0, 0)

    def wait_gps_fix(self):
        self.recv_match(type='VFR_HUD', blocking=True)
        if self.mavlink10():
            self.recv_match(type='GPS_RAW_INT', blocking=True,
                            condition='GPS_RAW_INT.fix_type==3 and GPS_RAW_INT.lat != 0 and GPS_RAW_INT.alt != 0')
        else:
            self.recv_match(type='GPS_RAW', blocking=True,
                            condition='GPS_RAW.fix_type==2 and GPS_RAW.lat != 0 and GPS_RAW.alt != 0')

    def location(self, relative_alt=False):
        '''return current location'''
        self.wait_gps_fix()
        # wait for another VFR_HUD, to ensure we have correct altitude
        self.recv_match(type='VFR_HUD', blocking=True)
        self.recv_match(type='GLOBAL_POSITION_INT', blocking=True)
        if relative_alt:
            alt = self.messages['GLOBAL_POSITION_INT'].relative_alt*0.001
        else:
            alt = self.messages['VFR_HUD'].alt
        return location(self.messages['GPS_RAW_INT'].lat*1.0e-7,
                        self.messages['GPS_RAW_INT'].lon*1.0e-7,
                        alt,
                        self.messages['VFR_HUD'].heading)

    def arducopter_arm(self):
        '''arm motors (arducopter only)'''
        if self.mavlink10():
            self.mav.command_long_send(
                self.target_system,  # target_system
                mavlink.MAV_COMP_ID_SYSTEM_CONTROL, # target_component
                mavlink.MAV_CMD_COMPONENT_ARM_DISARM, # command
                0, # confirmation
                1, # param1 (1 to indicate arm)
                0, # param2 (all other params meaningless)
                0, # param3
                0, # param4
                0, # param5
                0, # param6
                0) # param7

    def arducopter_disarm(self):
        '''calibrate pressure'''
        if self.mavlink10():
            self.mav.command_long_send(
                self.target_system,  # target_system
                mavlink.MAV_COMP_ID_SYSTEM_CONTROL, # target_component
                mavlink.MAV_CMD_COMPONENT_ARM_DISARM, # command
                0, # confirmation
                0, # param1 (0 to indicate disarm)
                0, # param2 (all other params meaningless)
                0, # param3
                0, # param4
                0, # param5
                0, # param6
                0) # param7

    def motors_armed(self):
        '''return true if motors armed'''
        if not 'HEARTBEAT' in self.messages:
            return False
        m = self.messages['HEARTBEAT']
        return (m.base_mode & mavlink.MAV_MODE_FLAG_SAFETY_ARMED) != 0

    def motors_armed_wait(self):
        '''wait for motors to be armed'''
        while True:
            m = self.wait_heartbeat()
            if self.motors_armed():
                return

    def motors_disarmed_wait(self):
        '''wait for motors to be disarmed'''
        while True:
            m = self.wait_heartbeat()
            if not self.motors_armed():
                return


    def field(self, type, field, default=None):
        '''convenient function for returning an arbitrary MAVLink
           field with a default'''
        if not type in self.messages:
            return default
        return getattr(self.messages[type], field, default)

    def param(self, name, default=None):
        '''convenient function for returning an arbitrary MAVLink
           parameter with a default'''
        if not name in self.params:
            return default
        return self.params[name]

def set_close_on_exec(fd):
    '''set the clone on exec flag on a file descriptor. Ignore exceptions'''
    try:
        import fcntl
        flags = fcntl.fcntl(fd, fcntl.F_GETFD)
        flags |= fcntl.FD_CLOEXEC
        fcntl.fcntl(fd, fcntl.F_SETFD, flags)
    except Exception:
        pass

class mavserial(mavfile):
    '''a serial mavlink port'''
    def __init__(self, device, baud=115200, autoreconnect=False, source_system=255):
        import serial
        self.baud = baud
        self.device = device
        self.autoreconnect = autoreconnect
        # we rather strangely set the baudrate initially to 1200, then change to the desired
        # baudrate. This works around a kernel bug on some Linux kernels where the baudrate
        # is not set correctly
        self.port = serial.Serial(self.device, 1200, timeout=0,
                                  dsrdtr=False, rtscts=False, xonxoff=False)
        try:
            fd = self.port.fileno()
            set_close_on_exec(fd)
        except Exception:
            fd = None
        self.set_baudrate(self.baud)
        mavfile.__init__(self, fd, device, source_system=source_system)
        self.rtscts = False

    def set_rtscts(self, enable):
        '''enable/disable RTS/CTS if applicable'''
        self.port.setRtsCts(enable)
        self.rtscts = enable

    def set_baudrate(self, baudrate):
        '''set baudrate'''
        self.port.setBaudrate(baudrate)
    
    def close(self):
        self.port.close()

    def recv(self,n=None):
        if n is None:
            n = self.mav.bytes_needed()
        if self.fd is None:
            waiting = self.port.inWaiting()
            if waiting < n:
                n = waiting
        ret = self.port.read(n)
        if len(ret) == 0:
            time.sleep(0.01)
        return ret

    def write(self, buf):
        try:
            return self.port.write(buf)
        except Exception:
            if self.autoreconnect:
                self.reset()
            return -1
            
    def reset(self):
        import serial
        self.port.close()
        while True:
            try:
                self.port = serial.Serial(self.device, self.baud, timeout=0,
                                          dsrdtr=False, rtscts=False, xonxoff=False)
                try:
                    self.fd = self.port.fileno()
                except Exception:
                    self.fd = None
                if self.rtscts:
                    self.set_rtscts(self.rtscts)
                return
            except Exception:
                print("Failed to reopen %s" % self.device)
                time.sleep(0.5)
        

class mavudp(mavfile):
    '''a UDP mavlink socket'''
    def __init__(self, device, input=True, broadcast=False, source_system=255):
        a = device.split(':')
        if len(a) != 2:
            print("UDP ports must be specified as host:port")
            sys.exit(1)
        self.port = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_server = input
        if input:
            self.port.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.port.bind((a[0], int(a[1])))
        else:
            self.destination_addr = (a[0], int(a[1]))
            if broadcast:
                self.port.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        set_close_on_exec(self.port.fileno())
        self.port.setblocking(0)
        self.last_address = None
        mavfile.__init__(self, self.port.fileno(), device, source_system=source_system, input=input)

    def close(self):
        self.port.close()

    def recv(self,n=None):
        try:
            data, self.last_address = self.port.recvfrom(300)
        except socket.error as e:
            if e.errno in [ errno.EAGAIN, errno.EWOULDBLOCK, errno.ECONNREFUSED ]:
                return ""
            raise
        return data

    def write(self, buf):
        try:
            if self.udp_server:
                if self.last_address:
                    self.port.sendto(buf, self.last_address)
            else:
                self.port.sendto(buf, self.destination_addr)
        except socket.error:
            pass

    def recv_msg(self):
        '''message receive routine for UDP link'''
        self.pre_message()
        s = self.recv()
        if len(s) == 0:
            return None
        if self.first_byte:
            self.auto_mavlink_version(s)
        msg = self.mav.parse_buffer(s)
        if msg is not None:
            for m in msg:
                self.post_message(m)
            return msg[0]
        return None


class mavtcp(mavfile):
    '''a TCP mavlink socket'''
    def __init__(self, device, source_system=255, retries=3):
        a = device.split(':')
        if len(a) != 2:
            print("TCP ports must be specified as host:port")
            sys.exit(1)
        self.port = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.destination_addr = (a[0], int(a[1]))
        while retries > 0:
            retries -= 1
            if retries == 0:
                self.port.connect(self.destination_addr)
            else:
                try:
                    self.port.connect(self.destination_addr)
                    break
                except Exception:
                    time.sleep(1)
                    continue
        self.port.setblocking(0)
        set_close_on_exec(self.port.fileno())
        self.port.setsockopt(socket.SOL_TCP, socket.TCP_NODELAY, 1)
        mavfile.__init__(self, self.port.fileno(), device, source_system=source_system)

    def close(self):
        self.port.close()

    def recv(self,n=None):
        if n is None:
            n = self.mav.bytes_needed()
        try:
            data = self.port.recv(n)
        except socket.error as e:
            if e.errno in [ errno.EAGAIN, errno.EWOULDBLOCK ]:
                return ""
            raise
        return data

    def write(self, buf):
        try:
            self.port.send(buf)
        except socket.error:
            pass


class mavlogfile(mavfile):
    '''a MAVLink logfile reader/writer'''
    def __init__(self, filename, planner_format=None,
                 write=False, append=False,
                 robust_parsing=True, notimestamps=False, source_system=255):
        self.filename = filename
        self.writeable = write
        self.robust_parsing = robust_parsing
        self.planner_format = planner_format
        self._two64 = math.pow(2.0, 63)
        mode = 'rb'
        if self.writeable:
            if append:
                mode = 'ab'
            else:
                mode = 'wb'
        self.f = open(filename, mode)
        self.filesize = os.path.getsize(filename)
        self.percent = 0
        mavfile.__init__(self, None, filename, source_system=source_system, notimestamps=notimestamps)
        if self.notimestamps:
            self._timestamp = 0
        else:
            self._timestamp = time.time()
        self.stop_on_EOF = True
        self._last_message = None
        self._last_timestamp = None

    def close(self):
        self.f.close()

    def recv(self,n=None):
        if n is None:
            n = self.mav.bytes_needed()
        return self.f.read(n)

    def write(self, buf):
        self.f.write(buf)

    def scan_timestamp(self, tbuf):
        '''scan forward looking in a tlog for a timestamp in a reasonable range'''
        while True:
            (tusec,) = struct.unpack('>Q', tbuf)
            t = tusec * 1.0e-6
            if abs(t - self._last_timestamp) <= 3*24*60*60:
                break
            c = self.f.read(1)
            if len(c) != 1:
                break
            tbuf = tbuf[1:] + c
        return t


    def pre_message(self):
        '''read timestamp if needed'''
        # read the timestamp
        if self.filesize != 0:
            self.percent = (100.0 * self.f.tell()) / self.filesize
        if self.notimestamps:
            return
        if self.planner_format:
            tbuf = self.f.read(21)
            if len(tbuf) != 21 or tbuf[0] != '-' or tbuf[20] != ':':
                raise RuntimeError('bad planner timestamp %s' % tbuf)
            hnsec = self._two64 + float(tbuf[0:20])
            t = hnsec * 1.0e-7         # convert to seconds
            t -= 719163 * 24 * 60 * 60 # convert to 1970 base
            self._link = 0
        else:
            tbuf = self.f.read(8)
            if len(tbuf) != 8:
                return
            (tusec,) = struct.unpack('>Q', tbuf)
            t = tusec * 1.0e-6
            if (self._last_timestamp is not None and
                self._last_message.get_type() == "BAD_DATA" and
                abs(t - self._last_timestamp) > 3*24*60*60):
                t = self.scan_timestamp(tbuf)
            self._link = tusec & 0x3
        self._timestamp = t

    def post_message(self, msg):
        '''add timestamp to message'''
        # read the timestamp
        super(mavlogfile, self).post_message(msg)
        if self.planner_format:
            self.f.read(1) # trailing newline
        self.timestamp = msg._timestamp
        self._last_message = msg
        if msg.get_type() != "BAD_DATA":
            self._last_timestamp = msg._timestamp

class mavchildexec(mavfile):
    '''a MAVLink child processes reader/writer'''
    def __init__(self, filename, source_system=255):
        from subprocess import Popen, PIPE
        import fcntl
        
        self.filename = filename
        self.child = Popen(filename, shell=True, stdout=PIPE, stdin=PIPE)
        self.fd = self.child.stdout.fileno()

        fl = fcntl.fcntl(self.fd, fcntl.F_GETFL)
        fcntl.fcntl(self.fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)

        fl = fcntl.fcntl(self.child.stdout.fileno(), fcntl.F_GETFL)
        fcntl.fcntl(self.child.stdout.fileno(), fcntl.F_SETFL, fl | os.O_NONBLOCK)

        mavfile.__init__(self, self.fd, filename, source_system=source_system)

    def close(self):
        self.child.close()

    def recv(self,n=None):
        try:
            x = self.child.stdout.read(1)
        except Exception:
            return ''
        return x

    def write(self, buf):
        self.child.stdin.write(buf)


def mavlink_connection(device, baud=115200, source_system=255,
                       planner_format=None, write=False, append=False,
                       robust_parsing=True, notimestamps=False, input=True,
                       dialect=None, autoreconnect=False, zero_time_base=False):
    '''open a serial, UDP, TCP or file mavlink connection'''
    if dialect is not None:
        set_dialect(dialect)
    if device.startswith('tcp:'):
        return mavtcp(device[4:], source_system=source_system)
    if device.startswith('udp:'):
        return mavudp(device[4:], input=input, source_system=source_system)

    if device.lower().endswith('.bin'):
        # support dataflash logs
        from pymavlink import DFReader
        m = DFReader.DFReader_binary(device, zero_time_base=zero_time_base)
        global mavfile_global
        mavfile_global = m
        return m

    if device.endswith('.log'):
        # support dataflash text logs
        from pymavlink import DFReader
        if DFReader.DFReader_is_text_log(device):
            global mavfile_global
            m = DFReader.DFReader_text(device, zero_time_base=zero_time_base)
            mavfile_global = m
            return m    

    # list of suffixes to prevent setting DOS paths as UDP sockets
    logsuffixes = [ 'log', 'raw', 'tlog' ]
    suffix = device.split('.')[-1].lower()
    if device.find(':') != -1 and not suffix in logsuffixes:
        return mavudp(device, source_system=source_system, input=input)
    if os.path.isfile(device):
        if device.endswith(".elf") or device.find("/bin/") != -1:
            print("executing '%s'" % device)
            return mavchildexec(device, source_system=source_system)
        else:
            return mavlogfile(device, planner_format=planner_format, write=write,
                              append=append, robust_parsing=robust_parsing, notimestamps=notimestamps,
                              source_system=source_system)
    return mavserial(device, baud=baud, source_system=source_system, autoreconnect=autoreconnect)

class periodic_event(object):
    '''a class for fixed frequency events'''
    def __init__(self, frequency):
        self.frequency = float(frequency)
        self.last_time = time.time()

    def force(self):
        '''force immediate triggering'''
        self.last_time = 0
        
    def trigger(self):
        '''return True if we should trigger now'''
        tnow = time.time()
        if self.last_time + (1.0/self.frequency) <= tnow:
            self.last_time = tnow
            return True
        return False


try:
    from curses import ascii
    have_ascii = True
except:
    have_ascii = False

def is_printable(c):
    '''see if a character is printable'''
    global have_ascii
    if have_ascii:
        return ascii.isprint(c)
    if isinstance(c, int):
        ic = c
    else:
        ic = ord(c)
    return ic >= 32 and ic <= 126

def all_printable(buf):
    '''see if a string is all printable'''
    for c in buf:
        if not is_printable(c) and not c in ['\r', '\n', '\t']:
            return False
    return True

class SerialPort(object):
    '''auto-detected serial port'''
    def __init__(self, device, description=None, hwid=None):
        self.device = device
        self.description = description
        self.hwid = hwid

    def __str__(self):
        ret = self.device
        if self.description is not None:
            ret += " : " + self.description
        if self.hwid is not None:
            ret += " : " + self.hwid
        return ret

def auto_detect_serial_win32(preferred_list=['*']):
    '''try to auto-detect serial ports on win32'''
    try:
        import scanwin32
        list = sorted(scanwin32.comports())
    except:
        return []
    ret = []
    for order, port, desc, hwid in list:
        for preferred in preferred_list:
            if fnmatch.fnmatch(desc, preferred) or fnmatch.fnmatch(hwid, preferred):
                ret.append(SerialPort(port, description=desc, hwid=hwid))
    if len(ret) > 0:
        return ret
    # now the rest
    for order, port, desc, hwid in list:
        ret.append(SerialPort(port, description=desc, hwid=hwid))
    return ret
        

        

def auto_detect_serial_unix(preferred_list=['*']):
    '''try to auto-detect serial ports on win32'''
    import glob
    glist = glob.glob('/dev/ttyS*') + glob.glob('/dev/ttyUSB*') + glob.glob('/dev/ttyACM*') + glob.glob('/dev/serial/by-id/*')
    ret = []
    # try preferred ones first
    for d in glist:
        for preferred in preferred_list:
            if fnmatch.fnmatch(d, preferred):
                ret.append(SerialPort(d))
    if len(ret) > 0:
        return ret
    # now the rest
    for d in glist:
        ret.append(SerialPort(d))
    return ret



def auto_detect_serial(preferred_list=['*']):
    '''try to auto-detect serial port'''
    # see if 
    if os.name == 'nt':
        return auto_detect_serial_win32(preferred_list=preferred_list)
    return auto_detect_serial_unix(preferred_list=preferred_list)

def mode_string_v09(msg):
    '''mode string for 0.9 protocol'''
    mode = msg.mode
    nav_mode = msg.nav_mode

    MAV_MODE_UNINIT = 0
    MAV_MODE_MANUAL = 2
    MAV_MODE_GUIDED = 3
    MAV_MODE_AUTO = 4
    MAV_MODE_TEST1 = 5
    MAV_MODE_TEST2 = 6
    MAV_MODE_TEST3 = 7

    MAV_NAV_GROUNDED = 0
    MAV_NAV_LIFTOFF = 1
    MAV_NAV_HOLD = 2
    MAV_NAV_WAYPOINT = 3
    MAV_NAV_VECTOR = 4
    MAV_NAV_RETURNING = 5
    MAV_NAV_LANDING = 6
    MAV_NAV_LOST = 7
    MAV_NAV_LOITER = 8
    
    cmode = (mode, nav_mode)
    mapping = {
        (MAV_MODE_UNINIT, MAV_NAV_GROUNDED)  : "INITIALISING",
        (MAV_MODE_MANUAL, MAV_NAV_VECTOR)    : "MANUAL",
        (MAV_MODE_TEST3,  MAV_NAV_VECTOR)    : "CIRCLE",
        (MAV_MODE_GUIDED, MAV_NAV_VECTOR)    : "GUIDED",
        (MAV_MODE_TEST1,  MAV_NAV_VECTOR)    : "STABILIZE",
        (MAV_MODE_TEST2,  MAV_NAV_LIFTOFF)   : "FBWA",
        (MAV_MODE_AUTO,   MAV_NAV_WAYPOINT)  : "AUTO",
        (MAV_MODE_AUTO,   MAV_NAV_RETURNING) : "RTL",
        (MAV_MODE_AUTO,   MAV_NAV_LOITER)    : "LOITER",
        (MAV_MODE_AUTO,   MAV_NAV_LIFTOFF)   : "TAKEOFF",
        (MAV_MODE_AUTO,   MAV_NAV_LANDING)   : "LANDING",
        (MAV_MODE_AUTO,   MAV_NAV_HOLD)      : "LOITER",
        (MAV_MODE_GUIDED, MAV_NAV_VECTOR)    : "GUIDED",
        (MAV_MODE_GUIDED, MAV_NAV_WAYPOINT)  : "GUIDED",
        (100,             MAV_NAV_VECTOR)    : "STABILIZE",
        (101,             MAV_NAV_VECTOR)    : "ACRO",
        (102,             MAV_NAV_VECTOR)    : "ALT_HOLD",
        (107,             MAV_NAV_VECTOR)    : "CIRCLE",
        (109,             MAV_NAV_VECTOR)    : "LAND",
        }
    if cmode in mapping:
        return mapping[cmode]
    return "Mode(%s,%s)" % cmode

mode_mapping_apm = {
    0 : 'MANUAL',
    1 : 'CIRCLE',
    2 : 'STABILIZE',
    3 : 'TRAINING',
    4 : 'ACRO',
    5 : 'FBWA',
    6 : 'FBWB',
    7 : 'CRUISE',
    8 : 'AUTOTUNE',
    10 : 'AUTO',
    11 : 'RTL',
    12 : 'LOITER',
    14 : 'LAND',
    15 : 'GUIDED',
    16 : 'INITIALISING'
    }
mode_mapping_acm = {
    0 : 'STABILIZE',
    1 : 'ACRO',
    2 : 'ALT_HOLD',
    3 : 'AUTO',
    4 : 'GUIDED',
    5 : 'LOITER',
    6 : 'RTL',
    7 : 'CIRCLE',
    8 : 'POSITION',
    9 : 'LAND',
    10 : 'OF_LOITER',
    11 : 'APPROACH'
    }
mode_mapping_rover = {
    0 : 'MANUAL',
    2 : 'LEARNING',
    3 : 'STEERING',
    4 : 'HOLD',
    10 : 'AUTO',
    11 : 'RTL',
    15 : 'GUIDED',
    16 : 'INITIALISING'
    }

mode_mapping_tracker = {
    0 : 'MANUAL',
    1 : 'STOP',
    2 : 'SCAN',
    10 : 'AUTO',
    16 : 'INITIALISING'
    }

mode_mapping_px4 = {
    0 : 'MANUAL',
    1 : 'ATTITUDE',
    2 : 'EASY',
    3 : 'AUTO'
    }


def mode_mapping_byname(mav_type):
    '''return dictionary mapping mode names to numbers, or None if unknown'''
    map = None
    if mav_type in [mavlink.MAV_TYPE_QUADROTOR,
                    mavlink.MAV_TYPE_HELICOPTER,
                    mavlink.MAV_TYPE_HEXAROTOR,
                    mavlink.MAV_TYPE_OCTOROTOR,
                    mavlink.MAV_TYPE_TRICOPTER]:
        map = mode_mapping_acm
    if mav_type == mavlink.MAV_TYPE_FIXED_WING:
        map = mode_mapping_apm
    if mav_type == mavlink.MAV_TYPE_GROUND_ROVER:
        map = mode_mapping_rover
    if mav_type == mavlink.MAV_TYPE_ANTENNA_TRACKER:
        map = mode_mapping_tracker
    if map is None:
        return None
    inv_map = dict((a, b) for (b, a) in map.items())
    return inv_map

def mode_mapping_bynumber(mav_type):
    '''return dictionary mapping mode numbers to name, or None if unknown'''
    map = None
    if mav_type in [mavlink.MAV_TYPE_QUADROTOR,
                    mavlink.MAV_TYPE_HELICOPTER,
                    mavlink.MAV_TYPE_HEXAROTOR,
                    mavlink.MAV_TYPE_OCTOROTOR,
                    mavlink.MAV_TYPE_TRICOPTER]:
        map = mode_mapping_acm
    if mav_type == mavlink.MAV_TYPE_FIXED_WING:
        map = mode_mapping_apm
    if mav_type == mavlink.MAV_TYPE_GROUND_ROVER:
        map = mode_mapping_rover
    if mav_type == mavlink.MAV_TYPE_ANTENNA_TRACKER:
        map = mode_mapping_tracker
    if map is None:
        return None
    return map


def mode_string_v10(msg):
    '''mode string for 1.0 protocol, from heartbeat'''
    if not msg.base_mode & mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED:
        return "Mode(0x%08x)" % msg.base_mode
    if msg.type in [ mavlink.MAV_TYPE_QUADROTOR, mavlink.MAV_TYPE_HEXAROTOR, mavlink.MAV_TYPE_OCTOROTOR, mavlink.MAV_TYPE_TRICOPTER, mavlink.MAV_TYPE_COAXIAL ]:
        if msg.custom_mode in mode_mapping_acm:
            return mode_mapping_acm[msg.custom_mode]
    if msg.type == mavlink.MAV_TYPE_FIXED_WING:
        if msg.custom_mode in mode_mapping_apm:
            return mode_mapping_apm[msg.custom_mode]
    if msg.type == mavlink.MAV_TYPE_GROUND_ROVER:
        if msg.custom_mode in mode_mapping_rover:
            return mode_mapping_rover[msg.custom_mode]
    if msg.type == mavlink.MAV_TYPE_ANTENNA_TRACKER:
        if msg.custom_mode in mode_mapping_tracker:
            return mode_mapping_tracker[msg.custom_mode]
    return "Mode(%u)" % msg.custom_mode

def mode_string_apm(mode_number):
    '''return mode string for APM:Plane'''
    if mode_number in mode_mapping_apm:
        return mode_mapping_apm[mode_number]
    return "Mode(%u)" % mode_number

def mode_string_acm(mode_number):
    '''return mode string for APM:Copter'''
    if mode_number in mode_mapping_acm:
        return mode_mapping_acm[mode_number]
    return "Mode(%u)" % mode_number

def mode_string_px4(mode_number):
    '''return mode string for PX4 flight stack'''
    if mode_number in mode_mapping_px4:
        return mode_mapping_px4[mode_number]
    return "Mode(%u)" % mode_number

class x25crc(object):
    '''x25 CRC - based on checksum.h from mavlink library'''
    def __init__(self, buf=''):
        self.crc = 0xffff
        self.accumulate(buf)

    def accumulate(self, buf):
        '''add in some more bytes'''
        bytes = array.array('B')
        if isinstance(buf, array.array):
            bytes.extend(buf)
        else:
            bytes.fromstring(buf)
        accum = self.crc
        for b in bytes:
            tmp = b ^ (accum & 0xff)
            tmp = (tmp ^ (tmp<<4)) & 0xFF
            accum = (accum>>8) ^ (tmp<<8) ^ (tmp<<3) ^ (tmp>>4)
            accum = accum & 0xFFFF
        self.crc = accum

class MavlinkSerialPort():
        '''an object that looks like a serial port, but
        transmits using mavlink SERIAL_CONTROL packets'''
        def __init__(self, portname, baudrate, devnum=0, devbaud=0, timeout=3, debug=0):
                from pymavlink import mavutil

                self.baudrate = 0
                self.timeout = timeout
                self._debug = debug
                self.buf = ''
                self.port = devnum
                self.debug("Connecting with MAVLink to %s ..." % portname)
                self.mav = mavutil.mavlink_connection(portname, autoreconnect=True, baud=baudrate)
                self.mav.wait_heartbeat()
                self.debug("HEARTBEAT OK\n")
                if devbaud != 0:
                    self.setBaudrate(devbaud)
                self.debug("Locked serial device\n")

        def debug(self, s, level=1):
                '''write some debug text'''
                if self._debug >= level:
                        print(s)

        def write(self, b):
                '''write some bytes'''
                from pymavlink import mavutil
                self.debug("sending '%s' (0x%02x) of len %u\n" % (b, ord(b[0]), len(b)), 2)
                while len(b) > 0:
                        n = len(b)
                        if n > 70:
                                n = 70
                        buf = [ord(x) for x in b[:n]]
                        buf.extend([0]*(70-len(buf)))
                        self.mav.mav.serial_control_send(self.port,
                                                         mavutil.mavlink.SERIAL_CONTROL_FLAG_EXCLUSIVE |
                                                         mavutil.mavlink.SERIAL_CONTROL_FLAG_RESPOND,
                                                         0,
                                                         0,
                                                         n,
                                                         buf)
                        b = b[n:]

        def _recv(self):
                '''read some bytes into self.buf'''
                from pymavlink import mavutil
                start_time = time.time()
                while time.time() < start_time + self.timeout:
                        m = self.mav.recv_match(condition='SERIAL_CONTROL.count!=0',
                                                type='SERIAL_CONTROL', blocking=False, timeout=0)
                        if m is not None and m.count != 0:
                                break
                        self.mav.mav.serial_control_send(self.port,
                                                         mavutil.mavlink.SERIAL_CONTROL_FLAG_EXCLUSIVE |
                                                         mavutil.mavlink.SERIAL_CONTROL_FLAG_RESPOND,
                                                         0,
                                                         0,
                                                         0, [0]*70)
                        m = self.mav.recv_match(condition='SERIAL_CONTROL.count!=0',
                                                type='SERIAL_CONTROL', blocking=True, timeout=0.01)
                        if m is not None and m.count != 0:
                                break
                        time.sleep(0.01)
                if m is not None:
                        if self._debug > 2:
                                print(m)
                        data = m.data[:m.count]
                        self.buf += ''.join(str(chr(x)) for x in data)

        def read(self, n):
                '''read some bytes'''
                if len(self.buf) == 0:
                        self._recv()
                if len(self.buf) > 0:
                        if n > len(self.buf):
                                n = len(self.buf)
                        ret = self.buf[:n]
                        self.buf = self.buf[n:]
                        if self._debug >= 2:
                            for b in ret:
                                self.debug("read 0x%x" % ord(b), 2)
                        return ret
                return ''

        def flushInput(self):
                '''flush any pending input'''
                self.buf = ''
                saved_timeout = self.timeout
                self.timeout = 0.5
                self._recv()
                self.timeout = saved_timeout
                self.buf = ''
                self.debug("flushInput")

        def setBaudrate(self, baudrate):
                '''set baudrate'''
                from pymavlink import mavutil
                if self.baudrate == baudrate:
                        return
                self.baudrate = baudrate
                self.mav.mav.serial_control_send(self.port,
                                                 mavutil.mavlink.SERIAL_CONTROL_FLAG_EXCLUSIVE,
                                                 0,
                                                 self.baudrate,
                                                 0, [0]*70)
                self.flushInput()
                self.debug("Changed baudrate %u" % self.baudrate)

########NEW FILE########
__FILENAME__ = mavwp
'''
module for loading/saving waypoints
'''

import time, copy
import logging
from . import mavutil
try:
    from google.protobuf import text_format
    import mission_pb2
    HAVE_PROTOBUF = True
except ImportError:
    HAVE_PROTOBUF = False


class MAVWPError(Exception):
    '''MAVLink WP error class'''
    def __init__(self, msg):
        Exception.__init__(self, msg)
        self.message = msg


class MAVWPLoader(object):
    '''MAVLink waypoint loader'''
    def __init__(self, target_system=0, target_component=0):
        self.wpoints = []
        self.target_system = target_system
        self.target_component = target_component
        self.last_change = time.time()

    def count(self):
        '''return number of waypoints'''
        return len(self.wpoints)

    def wp(self, i):
        '''return a waypoint'''
        return self.wpoints[i]

    def add(self, w, comment=''):
        '''add a waypoint'''
        w = copy.copy(w)
        if comment:
            w.comment = comment
        w.seq = self.count()
        self.wpoints.append(w)
        self.last_change = time.time()

    def reindex(self):
        '''reindex waypoints'''
        for i in range(self.count()):
            w = self.wpoints[i]
            w.seq = i
        self.last_change = time.time()

    def add_latlonalt(self, lat, lon, altitude):
        '''add a point via latitude/longitude/altitude'''
        p = mavutil.mavlink.MAVLink_mission_item_message(self.target_system,
                                                         self.target_component,
                                                         0,
                                                         mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT,
                                                         mavutil.mavlink.MAV_CMD_NAV_WAYPOINT,
                                                         0, 0, 0, 0, 0, 0,
                                                         lat, lon, altitude)
        self.add(p)

    def set(self, w, idx):
        '''set a waypoint'''
        w.seq = idx
        if w.seq == self.count():
            return self.add(w)
        if self.count() <= idx:
            raise MAVWPError('adding waypoint at idx=%u past end of list (count=%u)' % (idx, self.count()))
        self.wpoints[idx] = w
        self.last_change = time.time()

    def remove(self, w):
        '''remove a waypoint'''
        self.wpoints.remove(w)
        self.last_change = time.time()
        self.reindex()

    def clear(self):
        '''clear waypoint list'''
        self.wpoints = []
        self.last_change = time.time()

    def _read_waypoints_v100(self, file):
        '''read a version 100 waypoint'''
        cmdmap = {
            2 : mavutil.mavlink.MAV_CMD_NAV_TAKEOFF,
            3 : mavutil.mavlink.MAV_CMD_NAV_RETURN_TO_LAUNCH,
            4 : mavutil.mavlink.MAV_CMD_NAV_LAND,
            24: mavutil.mavlink.MAV_CMD_NAV_TAKEOFF,
            26: mavutil.mavlink.MAV_CMD_NAV_LAND,
            25: mavutil.mavlink.MAV_CMD_NAV_WAYPOINT ,
            27: mavutil.mavlink.MAV_CMD_NAV_LOITER_UNLIM
            }
        comment = ''
        for line in file:
            if line.startswith('#'):
                comment = line[1:].lstrip()
                continue
            line = line.strip()
            if not line:
                continue
            a = line.split()
            if len(a) != 13:
                raise MAVWPError("invalid waypoint line with %u values" % len(a))
            if mavutil.mavlink10():
                fn = mavutil.mavlink.MAVLink_mission_item_message
            else:
                fn = mavutil.mavlink.MAVLink_waypoint_message
            w = fn(self.target_system, self.target_component,
                   int(a[0]),    # seq
                   int(a[1]),    # frame
                   int(a[2]),    # action
                   int(a[7]),    # current
                   int(a[12]),   # autocontinue
                   float(a[5]),  # param1,
                   float(a[6]),  # param2,
                   float(a[3]),  # param3
                   float(a[4]),  # param4
                   float(a[9]),  # x, latitude
                   float(a[8]),  # y, longitude
                   float(a[10])  # z
                   )
            if not w.command in cmdmap:
                raise MAVWPError("Unknown v100 waypoint action %u" % w.command)

            w.command = cmdmap[w.command]
            self.add(w, comment)
            comment = ''

    def _read_waypoints_v110(self, file):
        '''read a version 110 waypoint'''
        comment = ''
        for line in file:
            if line.startswith('#'):
                comment = line[1:].lstrip()
                continue
            line = line.strip()
            if not line:
                continue
            a = line.split()
            if len(a) != 12:
                raise MAVWPError("invalid waypoint line with %u values" % len(a))
            if mavutil.mavlink10():
                fn = mavutil.mavlink.MAVLink_mission_item_message
            else:
                fn = mavutil.mavlink.MAVLink_waypoint_message
            w = fn(self.target_system, self.target_component,
                   int(a[0]),    # seq
                   int(a[2]),    # frame
                   int(a[3]),    # command
                   int(a[1]),    # current
                   int(a[11]),   # autocontinue
                   float(a[4]),  # param1,
                   float(a[5]),  # param2,
                   float(a[6]),  # param3
                   float(a[7]),  # param4
                   float(a[8]),  # x (latitude)
                   float(a[9]),  # y (longitude)
                   float(a[10])  # z (altitude)
                   )
            if w.command == 0 and w.seq == 0 and self.count() == 0:
                # special handling for Mission Planner created home wp
                w.command = mavutil.mavlink.MAV_CMD_NAV_WAYPOINT
            self.add(w, comment)
            comment = ''

    def _read_waypoints_pb_110(self, file):
        if not HAVE_PROTOBUF:
            raise MAVWPError(
                'Cannot read mission file in protobuf format without protobuf '
                'library. Try "easy_install protobuf".')
        explicit_seq = False
        warned_seq = False
        mission = mission_pb2.Mission()
        text_format.Merge(file.read(), mission)
        defaults = mission_pb2.Waypoint()
        # Set defaults (may be overriden in file).
        defaults.current = False
        defaults.autocontinue = True
        defaults.param1 = 0.0
        defaults.param2 = 0.0
        defaults.param3 = 0.0
        defaults.param4 = 0.0
        defaults.x = 0.0
        defaults.y = 0.0
        defaults.z = 0.0
        # Use defaults specified in mission file, if there are any.
        if mission.defaults:
            defaults.MergeFrom(mission.defaults)
        for seq, waypoint in enumerate(mission.waypoint):
            # Consecutive sequence numbers are automatically assigned
            # UNLESS the mission file specifies sequence numbers of
            # its own.
            if waypoint.seq:
                explicit_seq = True
            else:
                if explicit_seq and not warned_seq:
                    logging.warn(
                            'Waypoint file %s: mixes explicit and implicit '
                            'sequence numbers' % (file,))
                    warned_seq = True
            # The first command has current=True, the rest have current=False.
            if seq > 0:
                current = defaults.current
            else:
                current = True
            w = mavutil.mavlink.MAVLink_mission_item_message(
                self.target_system, self.target_component,
                   waypoint.seq or seq,
                   waypoint.frame,
                   waypoint.command,
                   waypoint.current or current,
                   waypoint.autocontinue or defaults.autocontinue,
                   waypoint.param1 or defaults.param1,
                   waypoint.param2 or defaults.param2,
                   waypoint.param3 or defaults.param3,
                   waypoint.param4 or defaults.param4,
                   waypoint.x or defaults.x,
                   waypoint.y or defaults.y,
                   waypoint.z or defaults.z)
            self.add(w)

    def load(self, filename):
        '''load waypoints from a file.
        returns number of waypoints loaded'''
        f = open(filename, mode='r')
        version_line = f.readline().strip()
        if version_line == "QGC WPL 100":
            readfn = self._read_waypoints_v100
        elif version_line == "QGC WPL 110":
            readfn = self._read_waypoints_v110
        elif version_line == "QGC WPL PB 110":
            readfn = self._read_waypoints_pb_110
        else:
            f.close()
            raise MAVWPError("Unsupported waypoint format '%s'" % version_line)

        self.clear()
        readfn(f)
        f.close()

        return len(self.wpoints)

    def save_as_pb(self, filename):
        mission = mission_pb2.Mission()
        for w in self.wpoints:
            waypoint = mission.waypoint.add()
            waypoint.command = w.command
            waypoint.frame = w.frame
            waypoint.seq = w.seq
            waypoint.current = w.current
            waypoint.autocontinue = w.autocontinue
            waypoint.param1 = w.param1
            waypoint.param2 = w.param2
            waypoint.param3 = w.param3
            waypoint.param4 = w.param4
            waypoint.x = w.x
            waypoint.y = w.y
            waypoint.z = w.z
        with open(filename, 'w') as f:
            f.write('QGC WPL PB 110\n')
            f.write(text_format.MessageToString(mission))

    def save(self, filename):
        '''save waypoints to a file'''
        f = open(filename, mode='w')
        f.write("QGC WPL 110\n")
        for w in self.wpoints:
            if getattr(w, 'comment', None):
                f.write("# %s\n" % w.comment)
            f.write("%u\t%u\t%u\t%u\t%f\t%f\t%f\t%f\t%f\t%f\t%f\t%u\n" % (
                w.seq, w.current, w.frame, w.command,
                w.param1, w.param2, w.param3, w.param4,
                w.x, w.y, w.z, w.autocontinue))
        f.close()

    def view_indexes(self, done=None):
        '''return a list waypoint indexes in view order'''
        ret = []
        if done is None:
            done = set()
        idx = 0

        # find first point not done yet
        while idx < self.count():
            if not idx in done:
                break
            idx += 1
            
        while idx < self.count():
            w = self.wp(idx)
            if idx in done:
                if w.x != 0 or w.y != 0:
                    ret.append(idx)
                break
            done.add(idx)
            if w.command == mavutil.mavlink.MAV_CMD_DO_JUMP:
                idx = int(w.param1)
                w = self.wp(idx)
                if w.x != 0 or w.y != 0:
                    ret.append(idx)
                continue
            if (w.x != 0 or w.y != 0) and w.command in [mavutil.mavlink.MAV_CMD_NAV_WAYPOINT,
                                                        mavutil.mavlink.MAV_CMD_NAV_LOITER_UNLIM,
                                                        mavutil.mavlink.MAV_CMD_NAV_LOITER_TURNS,
                                                        mavutil.mavlink.MAV_CMD_NAV_LOITER_TIME,
                                                        mavutil.mavlink.MAV_CMD_NAV_LAND,
                                                        mavutil.mavlink.MAV_CMD_NAV_TAKEOFF,
                                                        mavutil.mavlink.MAV_CMD_NAV_SPLINE_WAYPOINT]:
                ret.append(idx)
            idx += 1
        return ret

    def polygon(self, done=None):
        '''return a polygon for the waypoints'''
        indexes = self.view_indexes(done)
        points = []
        for idx in indexes:
            w = self.wp(idx)
            points.append((w.x, w.y))
        return points

    def polygon_list(self):
        '''return a list of polygons for the waypoints'''
        done = set()
        ret = []
        while len(done) != self.count():
            p = self.polygon(done)
            if len(p) > 0:
                ret.append(p)
        return ret

    def view_list(self):
        '''return a list of polygon indexes lists for the waypoints'''
        done = set()
        ret = []
        while len(done) != self.count():
            p = self.view_indexes(done)
            if len(p) > 0:
                ret.append(p)
        return ret

class MAVRallyError(Exception):
    '''MAVLink rally point error class'''
    def __init__(self, msg):
        Exception.__init__(self, msg)
        self.message = msg

class MAVRallyLoader(object):
    '''MAVLink Rally points and Rally Land ponts loader'''
    def __init__(self, target_system=0, target_component=0):
        self.rally_points = []
        self.target_system = target_system
        self.target_component = target_component
        self.last_change = time.time()

    def rally_count(self):
        '''return number of rally points'''
        return len(self.rally_points)

    def rally_point(self, i):
        '''return rally point i'''
        return self.rally_points[i]

    def reindex(self):
        '''reset counters and indexes'''
        for i in range(self.rally_count()):
            self.rally_points[i].count = self.rally_count()
            self.rally_points[i].idx = i
        self.last_change = time.time()
            
    def append_rally_point(self, p):
        '''add rallypoint to end of list'''
        if (self.rally_count() > 9):
           print("Can't have more than 10 rally points, not adding.")
           return

        self.rally_points.append(p)
        self.reindex()

    def create_and_append_rally_point(self, lat, lon, alt, break_alt, land_dir, flags):
        '''add a point via latitude/longitude'''
        p = mavutil.mavlink.MAVLink_rally_point_message(self.target_system, self.target_component,
                                                        self.rally_count(), 0, lat, lon, alt, break_alt, land_dir, flags)
        self.append_rally_point(p)

    def clear(self):
        '''clear all point lists (rally and rally_land)'''
        self.rally_points = []
        self.last_change = time.time()

    def remove(self, i):
        '''remove a rally point'''
        if i < 1 or i > self.rally_count():
            print("Invalid rally point number %u" % i)
        self.rally_points.pop(i-1)
        self.reindex()

    def move(self, i, lat, lng, change_time=True):
        '''move a rally point'''
        if i < 1 or i > self.rally_count():
            print("Invalid rally point number %u" % i)
        self.rally_points[i-1].lat = int(lat*1e7)
        self.rally_points[i-1].lng = int(lng*1e7)
        if change_time:
            self.last_change = time.time()

    def load(self, filename):
        '''load rally and rally_land points from a file.
         returns number of points loaded'''
        f = open(filename, mode='r')
        self.clear()
        for line in f:
            if line.startswith('#'):
                continue
            line = line.strip()
            if not line:
                continue
            a = line.split()
            if len(a) != 7:
                raise MAVRallyError("invalid rally file line: %s" % line)

            if (a[0].lower() == "rally"):
                self.create_and_append_rally_point(float(a[1]) * 1e7, float(a[2]) * 1e7,
                                                   float(a[3]), float(a[4]), float(a[5]) * 100.0, int(a[6]))
        f.close()
        return len(self.rally_points)

    def save(self, filename):
        '''save fence points to a file'''
        f = open(filename, mode='w')
        for p in self.rally_points:
            f.write("RALLY %f\t%f\t%f\t%f\t%f\t%d\n" % (p.lat * 1e-7, p.lng * 1e-7, p.alt,
                                                        p.break_alt, p.land_dir, p.flags))
        f.close()

class MAVFenceError(Exception):
        '''MAVLink fence error class'''
        def __init__(self, msg):
            Exception.__init__(self, msg)
            self.message = msg

class MAVFenceLoader(object):
    '''MAVLink geo-fence loader'''
    def __init__(self, target_system=0, target_component=0):
        self.points = []
        self.target_system = target_system
        self.target_component = target_component
        self.last_change = time.time()

    def count(self):
        '''return number of points'''
        return len(self.points)

    def point(self, i):
        '''return a point'''
        return self.points[i]

    def add(self, p):
        '''add a point'''
        self.points.append(p)
        self.reindex()

    def reindex(self):
        '''reindex waypoints'''
        for i in range(self.count()):
            w = self.points[i]
            w.idx = i
            w.count = self.count()
            w.target_system = self.target_system
            w.target_component = self.target_component
        self.last_change = time.time()

    def add_latlon(self, lat, lon):
        '''add a point via latitude/longitude'''
        p = mavutil.mavlink.MAVLink_fence_point_message(self.target_system, self.target_component,
                                                        self.count(), 0, lat, lon)
        self.add(p)

    def clear(self):
        '''clear point list'''
        self.points = []
        self.last_change = time.time()

    def load(self, filename):
        '''load points from a file.
        returns number of points loaded'''
        f = open(filename, mode='r')
        self.clear()
        for line in f:
            if line.startswith('#'):
                continue
            line = line.strip()
            if not line:
                continue
            a = line.split()
            if len(a) != 2:
                raise MAVFenceError("invalid fence point line: %s" % line)
            self.add_latlon(float(a[0]), float(a[1]))
        f.close()
        return len(self.points)

    def save(self, filename):
        '''save fence points to a file'''
        f = open(filename, mode='w')
        for p in self.points:
            f.write("%f\t%f\n" % (p.lat, p.lng))
        f.close()

    def move(self, i, lat, lng, change_time=True):
        '''move a fence point'''
        if i < 0 or i >= self.count():
            print("Invalid fence point number %u" % i)
        self.points[i].lat = lat
        self.points[i].lng = lng
        # ensure we close the polygon
        if i == 1:
                self.points[self.count()-1].lat = lat
                self.points[self.count()-1].lng = lng
        if i == self.count() - 1:
                self.points[1].lat = lat
                self.points[1].lng = lng
        if change_time:
            self.last_change = time.time()

    def remove(self, i, change_time=True):
        '''remove a fence point'''
        if i < 0 or i >= self.count():
            print("Invalid fence point number %u" % i)
        self.points.pop(i)
         # ensure we close the polygon
        if i == 1:
                self.points[self.count()-1].lat = self.points[1].lat
                self.points[self.count()-1].lng = self.points[1].lng
        if i == self.count():
                self.points[1].lat = self.points[self.count()-1].lat
                self.points[1].lng = self.points[self.count()-1].lng
        if change_time:
            self.last_change = time.time()

    def polygon(self):
            '''return a polygon for the fence'''
            points = []
            for fp in self.points[1:]:
                    points.append((fp.lat, fp.lng))
            return points

########NEW FILE########
__FILENAME__ = rotmat
#!/usr/bin/env python
#
# vector3 and rotation matrix classes
# This follows the conventions in the ArduPilot code,
# and is essentially a python version of the AP_Math library
#
# Andrew Tridgell, March 2012
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

'''rotation matrix class
'''

from math import sin, cos, sqrt, asin, atan2, pi, radians, acos, degrees

class Vector3:
    '''a vector'''
    def __init__(self, x=None, y=None, z=None):
        if x != None and y != None and z != None:
            self.x = float(x)
            self.y = float(y)
            self.z = float(z)
        elif x != None and len(x) == 3:
            self.x = float(x[0])
            self.y = float(x[1])
            self.z = float(x[2])
        elif x != None:
            raise ValueError('bad initialiser')
        else:
            self.x = float(0)
            self.y = float(0)
            self.z = float(0)

    def __repr__(self):
        return 'Vector3(%.2f, %.2f, %.2f)' % (self.x,
                                              self.y,
                                              self.z)

    def __eq__(self, v):
        return self.x == v.x and self.y == v.y and self.z == v.z

    def __ne__(self, v):
        return not self == v

    def __add__(self, v):
        return Vector3(self.x + v.x,
                       self.y + v.y,
                       self.z + v.z)

    __radd__ = __add__

    def __sub__(self, v):
        return Vector3(self.x - v.x,
                       self.y - v.y,
                       self.z - v.z)

    def __neg__(self):
        return Vector3(-self.x, -self.y, -self.z)

    def __rsub__(self, v):
        return Vector3(v.x - self.x,
                       v.y - self.y,
                       v.z - self.z)

    def __mul__(self, v):
        if isinstance(v, Vector3):
            '''dot product'''
            return self.x*v.x + self.y*v.y + self.z*v.z
        return Vector3(self.x * v,
                       self.y * v,
                       self.z * v)

    __rmul__ = __mul__

    def __div__(self, v):
        return Vector3(self.x / v,
                       self.y / v,
                       self.z / v)

    def __mod__(self, v):
        '''cross product'''
        return Vector3(self.y*v.z - self.z*v.y,
                       self.z*v.x - self.x*v.z,
                       self.x*v.y - self.y*v.x)

    def __copy__(self):
        return Vector3(self.x, self.y, self.z)

    copy = __copy__

    def length(self):
        return sqrt(self.x**2 + self.y**2 + self.z**2)

    def zero(self):
        self.x = self.y = self.z = 0

    def angle(self, v):
        '''return the angle between this vector and another vector'''
        return acos((self * v) / (self.length() * v.length()))

    def normalized(self):
        return self.__div__(self.length())
    
    def normalize(self):
        v = self.normalized()
        self.x = v.x
        self.y = v.y
        self.z = v.z
        
class Matrix3:
    '''a 3x3 matrix, intended as a rotation matrix'''
    def __init__(self, a=None, b=None, c=None):
        if a is not None and b is not None and c is not None:
            self.a = a.copy()
            self.b = b.copy()
            self.c = c.copy()
        else:
            self.identity()

    def __repr__(self):
        return 'Matrix3((%.2f, %.2f, %.2f), (%.2f, %.2f, %.2f), (%.2f, %.2f, %.2f))' % (
            self.a.x, self.a.y, self.a.z,
            self.b.x, self.b.y, self.b.z,
            self.c.x, self.c.y, self.c.z)

    def identity(self):
        self.a = Vector3(1,0,0)
        self.b = Vector3(0,1,0)
        self.c = Vector3(0,0,1)

    def transposed(self):
        return Matrix3(Vector3(self.a.x, self.b.x, self.c.x),
                       Vector3(self.a.y, self.b.y, self.c.y),
                       Vector3(self.a.z, self.b.z, self.c.z))

        
    def from_euler(self, roll, pitch, yaw):
        '''fill the matrix from Euler angles in radians'''
        cp = cos(pitch)
        sp = sin(pitch)
        sr = sin(roll)
        cr = cos(roll)
        sy = sin(yaw)
        cy = cos(yaw)

        self.a.x = cp * cy
        self.a.y = (sr * sp * cy) - (cr * sy)
        self.a.z = (cr * sp * cy) + (sr * sy)
        self.b.x = cp * sy
        self.b.y = (sr * sp * sy) + (cr * cy)
        self.b.z = (cr * sp * sy) - (sr * cy)
        self.c.x = -sp
        self.c.y = sr * cp
        self.c.z = cr * cp


    def to_euler(self):
        '''find Euler angles for the matrix'''
        if self.c.x >= 1.0:
            pitch = pi
        elif self.c.x <= -1.0:
            pitch = -pi
        else:
            pitch = -asin(self.c.x)
        roll = atan2(self.c.y, self.c.z)
        yaw  = atan2(self.b.x, self.a.x)
        return (roll, pitch, yaw)

    def __add__(self, m):
        return Matrix3(self.a + m.a, self.b + m.b, self.c + m.c)

    __radd__ = __add__

    def __sub__(self, m):
        return Matrix3(self.a - m.a, self.b - m.b, self.c - m.c)

    def __rsub__(self, m):
        return Matrix3(m.a - self.a, m.b - self.b, m.c - self.c)
    
    def __mul__(self, other):
        if isinstance(other, Vector3):
            v = other
            return Vector3(self.a.x * v.x + self.a.y * v.y + self.a.z * v.z,
                           self.b.x * v.x + self.b.y * v.y + self.b.z * v.z,
                           self.c.x * v.x + self.c.y * v.y + self.c.z * v.z)
        elif isinstance(other, Matrix3):
            m = other
            return Matrix3(Vector3(self.a.x * m.a.x + self.a.y * m.b.x + self.a.z * m.c.x,
                                   self.a.x * m.a.y + self.a.y * m.b.y + self.a.z * m.c.y,
                                   self.a.x * m.a.z + self.a.y * m.b.z + self.a.z * m.c.z),
                           Vector3(self.b.x * m.a.x + self.b.y * m.b.x + self.b.z * m.c.x,
                                   self.b.x * m.a.y + self.b.y * m.b.y + self.b.z * m.c.y,
                                   self.b.x * m.a.z + self.b.y * m.b.z + self.b.z * m.c.z),
                           Vector3(self.c.x * m.a.x + self.c.y * m.b.x + self.c.z * m.c.x,
                                   self.c.x * m.a.y + self.c.y * m.b.y + self.c.z * m.c.y,
                                   self.c.x * m.a.z + self.c.y * m.b.z + self.c.z * m.c.z))
        v = other
        return Matrix3(self.a * v, self.b * v, self.c * v)

    def __div__(self, v):
        return Matrix3(self.a / v, self.b / v, self.c / v)

    def __neg__(self):
        return Matrix3(-self.a, -self.b, -self.c)

    def __copy__(self):
        return Matrix3(self.a, self.b, self.c)

    copy = __copy__

    def rotate(self, g):
        '''rotate the matrix by a given amount on 3 axes'''
        temp_matrix = Matrix3()
        a = self.a
        b = self.b
        c = self.c
        temp_matrix.a.x = a.y * g.z - a.z * g.y
        temp_matrix.a.y = a.z * g.x - a.x * g.z
        temp_matrix.a.z = a.x * g.y - a.y * g.x
        temp_matrix.b.x = b.y * g.z - b.z * g.y
        temp_matrix.b.y = b.z * g.x - b.x * g.z
        temp_matrix.b.z = b.x * g.y - b.y * g.x
        temp_matrix.c.x = c.y * g.z - c.z * g.y
        temp_matrix.c.y = c.z * g.x - c.x * g.z
        temp_matrix.c.z = c.x * g.y - c.y * g.x
        self.a += temp_matrix.a
        self.b += temp_matrix.b
        self.c += temp_matrix.c

    def normalize(self):
        '''re-normalise a rotation matrix'''
        error = self.a * self.b
        t0 = self.a - (self.b * (0.5 * error))
        t1 = self.b - (self.a * (0.5 * error))
        t2 = t0 % t1
        self.a = t0 * (1.0 / t0.length())
        self.b = t1 * (1.0 / t1.length())
        self.c = t2 * (1.0 / t2.length())

    def trace(self):
        '''the trace of the matrix'''
        return self.a.x + self.b.y + self.c.z

    def from_axis_angle(self, axis, angle):
        '''create a rotation matrix from axis and angle'''
        ux = axis.x
        uy = axis.y
        uz = axis.z
        ct = cos(angle)
        st = sin(angle)
        self.a.x = ct + (1-ct) * ux**2
        self.a.y = ux*uy*(1-ct) - uz*st
        self.a.z = ux*uz*(1-ct) + uy*st
        self.b.x = uy*ux*(1-ct) + uz*st
        self.b.y = ct + (1-ct) * uy**2
        self.b.z = uy*uz*(1-ct) - ux*st
        self.c.x = uz*ux*(1-ct) - uy*st
        self.c.y = uz*uy*(1-ct) + ux*st
        self.c.z = ct + (1-ct) * uz**2


    def from_two_vectors(self, vec1, vec2):
        '''get a rotation matrix from two vectors.
           This returns a rotation matrix which when applied to vec1
           will produce a vector pointing in the same direction as vec2'''
        angle = vec1.angle(vec2)
        cross = vec1 % vec2
        if cross.length() == 0:
            # the two vectors are colinear
            return self.from_euler(0,0,angle)
        cross.normalize()
        return self.from_axis_angle(cross, angle)


class Plane:
    '''a plane in 3 space, defined by a point and a vector normal'''
    def __init__(self, point=None, normal=None):
        if point is None:
            point = Vector3(0,0,0)
        if normal is None:
            normal = Vector3(0, 0, 1)
        self.point = point
        self.normal = normal

class Line:
    '''a line in 3 space, defined by a point and a vector'''
    def __init__(self, point=None, vector=None):
        if point is None:
            point = Vector3(0,0,0)
        if vector is None:
            vector = Vector3(0, 0, 1)
        self.point = point
        self.vector = vector

    def plane_intersection(self, plane, forward_only=False):
        '''return point where line intersects with a plane'''
        l_dot_n = self.vector * plane.normal
        if l_dot_n == 0.0:
            # line is parallel to the plane
            return None
        d = ((plane.point - self.point) * plane.normal) / l_dot_n
        if forward_only and d < 0:
            return None
        return (self.vector * d) + self.point
        


def test_euler():
    '''check that from_euler() and to_euler() are consistent'''
    m = Matrix3()
    from math import radians, degrees
    for r in range(-179, 179, 3):
        for p in range(-89, 89, 3):
            for y in range(-179, 179, 3):
                m.from_euler(radians(r), radians(p), radians(y))
                (r2, p2, y2) = m.to_euler()
                v1 = Vector3(r,p,y)
                v2 = Vector3(degrees(r2),degrees(p2),degrees(y2))
                diff = v1 - v2
                if diff.length() > 1.0e-12:
                    print('EULER ERROR:', v1, v2, diff.length())


def test_two_vectors():
    '''test the from_two_vectors() method'''
    import random
    for i in range(1000):
        v1 = Vector3(1, 0.2, -3)
        v2 = Vector3(random.uniform(-5,5), random.uniform(-5,5), random.uniform(-5,5))
        m = Matrix3()
        m.from_two_vectors(v1, v2)
        v3 = m * v1
        diff = v3.normalized() - v2.normalized()
        (r, p, y) = m.to_euler()
        if diff.length() > 0.001:
            print('err=%f' % diff.length())
            print("r/p/y = %.1f %.1f %.1f" % (
                degrees(r), degrees(p), degrees(y)))
            print(v1.normalized(), v2.normalized(), v3.normalized())

def test_plane():
    '''testing line/plane intersection'''
    print("testing plane/line maths")
    plane = Plane(Vector3(0,0,0), Vector3(0,0,1))
    line = Line(Vector3(0,0,100), Vector3(10, 10, -90))
    p = line.plane_intersection(plane)
    print(p)
    
if __name__ == "__main__":
    import doctest
    doctest.testmod()
    test_euler()
    test_two_vectors()
    
    

########NEW FILE########
__FILENAME__ = scanwin32
#!/usr/bin/env python

# this is taken from the pySerial documentation at
# http://pyserial.sourceforge.net/examples.html
import ctypes
import re

def ValidHandle(value):
    if value == 0:
        raise ctypes.WinError()
    return value

NULL = 0
HDEVINFO = ctypes.c_int
BOOL = ctypes.c_int
CHAR = ctypes.c_char
PCTSTR = ctypes.c_char_p
HWND = ctypes.c_uint
DWORD = ctypes.c_ulong
PDWORD = ctypes.POINTER(DWORD)
ULONG = ctypes.c_ulong
ULONG_PTR = ctypes.POINTER(ULONG)
#~ PBYTE = ctypes.c_char_p
PBYTE = ctypes.c_void_p

class GUID(ctypes.Structure):
    _fields_ = [
        ('Data1', ctypes.c_ulong),
        ('Data2', ctypes.c_ushort),
        ('Data3', ctypes.c_ushort),
        ('Data4', ctypes.c_ubyte*8),
    ]
    def __str__(self):
        return "{%08x-%04x-%04x-%s-%s}" % (
            self.Data1,
            self.Data2,
            self.Data3,
            ''.join(["%02x" % d for d in self.Data4[:2]]),
            ''.join(["%02x" % d for d in self.Data4[2:]]),
        )

class SP_DEVINFO_DATA(ctypes.Structure):
    _fields_ = [
        ('cbSize', DWORD),
        ('ClassGuid', GUID),
        ('DevInst', DWORD),
        ('Reserved', ULONG_PTR),
    ]
    def __str__(self):
        return "ClassGuid:%s DevInst:%s" % (self.ClassGuid, self.DevInst)
PSP_DEVINFO_DATA = ctypes.POINTER(SP_DEVINFO_DATA)

class SP_DEVICE_INTERFACE_DATA(ctypes.Structure):
    _fields_ = [
        ('cbSize', DWORD),
        ('InterfaceClassGuid', GUID),
        ('Flags', DWORD),
        ('Reserved', ULONG_PTR),
    ]
    def __str__(self):
        return "InterfaceClassGuid:%s Flags:%s" % (self.InterfaceClassGuid, self.Flags)

PSP_DEVICE_INTERFACE_DATA = ctypes.POINTER(SP_DEVICE_INTERFACE_DATA)

PSP_DEVICE_INTERFACE_DETAIL_DATA = ctypes.c_void_p

class dummy(ctypes.Structure):
    _fields_=[("d1", DWORD), ("d2", CHAR)]
    _pack_ = 1
SIZEOF_SP_DEVICE_INTERFACE_DETAIL_DATA_A = ctypes.sizeof(dummy)

SetupDiDestroyDeviceInfoList = ctypes.windll.setupapi.SetupDiDestroyDeviceInfoList
SetupDiDestroyDeviceInfoList.argtypes = [HDEVINFO]
SetupDiDestroyDeviceInfoList.restype = BOOL

SetupDiGetClassDevs = ctypes.windll.setupapi.SetupDiGetClassDevsA
SetupDiGetClassDevs.argtypes = [ctypes.POINTER(GUID), PCTSTR, HWND, DWORD]
SetupDiGetClassDevs.restype = ValidHandle # HDEVINFO

SetupDiEnumDeviceInterfaces = ctypes.windll.setupapi.SetupDiEnumDeviceInterfaces
SetupDiEnumDeviceInterfaces.argtypes = [HDEVINFO, PSP_DEVINFO_DATA, ctypes.POINTER(GUID), DWORD, PSP_DEVICE_INTERFACE_DATA]
SetupDiEnumDeviceInterfaces.restype = BOOL

SetupDiGetDeviceInterfaceDetail = ctypes.windll.setupapi.SetupDiGetDeviceInterfaceDetailA
SetupDiGetDeviceInterfaceDetail.argtypes = [HDEVINFO, PSP_DEVICE_INTERFACE_DATA, PSP_DEVICE_INTERFACE_DETAIL_DATA, DWORD, PDWORD, PSP_DEVINFO_DATA]
SetupDiGetDeviceInterfaceDetail.restype = BOOL

SetupDiGetDeviceRegistryProperty = ctypes.windll.setupapi.SetupDiGetDeviceRegistryPropertyA
SetupDiGetDeviceRegistryProperty.argtypes = [HDEVINFO, PSP_DEVINFO_DATA, DWORD, PDWORD, PBYTE, DWORD, PDWORD]
SetupDiGetDeviceRegistryProperty.restype = BOOL


GUID_CLASS_COMPORT = GUID(0x86e0d1e0L, 0x8089, 0x11d0,
    (ctypes.c_ubyte*8)(0x9c, 0xe4, 0x08, 0x00, 0x3e, 0x30, 0x1f, 0x73))

DIGCF_PRESENT = 2
DIGCF_DEVICEINTERFACE = 16
INVALID_HANDLE_VALUE = 0
ERROR_INSUFFICIENT_BUFFER = 122
SPDRP_HARDWAREID = 1
SPDRP_FRIENDLYNAME = 12
SPDRP_LOCATION_INFORMATION = 13
ERROR_NO_MORE_ITEMS = 259

def comports(available_only=True):
    """This generator scans the device registry for com ports and yields
    (order, port, desc, hwid).  If available_only is true only return currently
    existing ports. Order is a helper to get sorted lists. it can be ignored
    otherwise."""
    flags = DIGCF_DEVICEINTERFACE
    if available_only:
        flags |= DIGCF_PRESENT
    g_hdi = SetupDiGetClassDevs(ctypes.byref(GUID_CLASS_COMPORT), None, NULL, flags);
    #~ for i in range(256):
    for dwIndex in range(256):
        did = SP_DEVICE_INTERFACE_DATA()
        did.cbSize = ctypes.sizeof(did)

        if not SetupDiEnumDeviceInterfaces(
            g_hdi,
            None,
            ctypes.byref(GUID_CLASS_COMPORT),
            dwIndex,
            ctypes.byref(did)
        ):
            if ctypes.GetLastError() != ERROR_NO_MORE_ITEMS:
                raise ctypes.WinError()
            break

        dwNeeded = DWORD()
        # get the size
        if not SetupDiGetDeviceInterfaceDetail(
            g_hdi,
            ctypes.byref(did),
            None, 0, ctypes.byref(dwNeeded),
            None
        ):
            # Ignore ERROR_INSUFFICIENT_BUFFER
            if ctypes.GetLastError() != ERROR_INSUFFICIENT_BUFFER:
                raise ctypes.WinError()
        # allocate buffer
        class SP_DEVICE_INTERFACE_DETAIL_DATA_A(ctypes.Structure):
            _fields_ = [
                ('cbSize', DWORD),
                ('DevicePath', CHAR*(dwNeeded.value - ctypes.sizeof(DWORD))),
            ]
            def __str__(self):
                return "DevicePath:%s" % (self.DevicePath,)
        idd = SP_DEVICE_INTERFACE_DETAIL_DATA_A()
        idd.cbSize = SIZEOF_SP_DEVICE_INTERFACE_DETAIL_DATA_A
        devinfo = SP_DEVINFO_DATA()
        devinfo.cbSize = ctypes.sizeof(devinfo)
        if not SetupDiGetDeviceInterfaceDetail(
            g_hdi,
            ctypes.byref(did),
            ctypes.byref(idd), dwNeeded, None,
            ctypes.byref(devinfo)
        ):
            raise ctypes.WinError()

        # hardware ID
        szHardwareID = ctypes.create_string_buffer(250)
        if not SetupDiGetDeviceRegistryProperty(
            g_hdi,
            ctypes.byref(devinfo),
            SPDRP_HARDWAREID,
            None,
            ctypes.byref(szHardwareID), ctypes.sizeof(szHardwareID) - 1,
            None
        ):
            # Ignore ERROR_INSUFFICIENT_BUFFER
            if ctypes.GetLastError() != ERROR_INSUFFICIENT_BUFFER:
                raise ctypes.WinError()

        # friendly name
        szFriendlyName = ctypes.create_string_buffer(1024)
        if not SetupDiGetDeviceRegistryProperty(
            g_hdi,
            ctypes.byref(devinfo),
            SPDRP_FRIENDLYNAME,
            None,
            ctypes.byref(szFriendlyName), ctypes.sizeof(szFriendlyName) - 1,
            None
        ):
            # Ignore ERROR_INSUFFICIENT_BUFFER
            if ctypes.GetLastError() != ERROR_INSUFFICIENT_BUFFER:
                #~ raise ctypes.WinError()
                # not getting friendly name for com0com devices, try something else
                szFriendlyName = ctypes.create_string_buffer(1024)
                if SetupDiGetDeviceRegistryProperty(
                    g_hdi,
                    ctypes.byref(devinfo),
                    SPDRP_LOCATION_INFORMATION,
                    None,
                    ctypes.byref(szFriendlyName), ctypes.sizeof(szFriendlyName) - 1,
                    None
                ):
                    port_name = "\\\\.\\" + szFriendlyName.value
                    order = None
                else:
                    port_name = szFriendlyName.value
                    order = None
        else:
            try:
                m = re.search(r"\((.*?(\d+))\)", szFriendlyName.value)
                #~ print szFriendlyName.value, m.groups()
                port_name = m.group(1)
                order = int(m.group(2))
            except AttributeError, msg:
                port_name = szFriendlyName.value
                order = None
        yield order, port_name, szFriendlyName.value, szHardwareID.value

    SetupDiDestroyDeviceInfoList(g_hdi)


if __name__ == '__main__':
    import serial
    print("-"*78)
    print("Serial ports")
    print("-"*78)
    for order, port, desc, hwid in sorted(comports()):
        print("%-10s: %s (%s) ->" % (port, desc, hwid))
        try:
            serial.Serial(port) # test open
        except serial.serialutil.SerialException:
            print("can't be openend")
        else:
            print("Ready")
    print("")
    # list of all ports the system knows
    print("-"*78)
    print "All serial ports (registry)"
    print("-"*78)
    for order, port, desc, hwid in sorted(comports(False)):
        print("%-10s: %s (%s)" % (port, desc, hwid))

########NEW FILE########
__FILENAME__ = AccelSearch
#!/usr/bin/env python

'''
search a set of log files for bad accel values
'''

import sys, time, os, glob
import zipfile

from pymavlink import mavutil

# extra imports for pyinstaller
import json
from pymavlink.dialects.v10 import ardupilotmega

search_dirs = ['c:\Program Files\APM Planner', 
               'c:\Program Files\Mission Planner', 
               'c:\Program Files (x86)\APM Planner',
               'c:\Program Files (x86)\Mission Planner']
results = 'SearchResults.zip'
email = 'Craig Elder <craig@3drobotics.com>'

from optparse import OptionParser
parser = OptionParser("AccelSearch.py [options]")
parser.add_option("--directory", action='append', default=search_dirs, help="directories to search")
parser.add_option("--post-boot", action='store_true', help="post boot only")
parser.add_option("--init-only", action='store_true', help="init only")
parser.add_option("--single-axis", action='store_true', help="single axis only")

(opts, args) = parser.parse_args()

logcount = 0

def AccelSearch(filename):
    global logcount
    mlog = mavutil.mavlink_connection(filename)
    badcount = 0
    badval = None
    have_ok = False
    last_t = 0
    while True:
        m = mlog.recv_match(type=['PARAM_VALUE','RAW_IMU'])
        if m is None:
            if last_t != 0:
                logcount += 1
            return False
        if m.get_type() == 'PARAM_VALUE':
            if m.param_id.startswith('INS_PRODUCT_ID'):
                if m.param_value not in [0.0, 5.0]:
                    return False
        if m.get_type() == 'RAW_IMU':
            if m.time_usec < last_t:
                have_ok = False
            last_t = m.time_usec
            if abs(m.xacc) >= 3000 and abs(m.yacc) > 3000 and abs(m.zacc) > 3000 and not opts.single_axis:
                if opts.post_boot and not have_ok:
                    continue
                if opts.init_only and have_ok:
                    continue
                print have_ok, last_t, m
                break
            # also look for a single axis that stays nearly constant at a large value
            for axes in ['xacc', 'yacc', 'zacc']:
                value1 = getattr(m, axes)
                if abs(value1) > 2000:
                    if badval is None:
                        badcount = 1
                        badval = m
                        continue
                    value2 = getattr(badval, axes)
                    if abs(value1 - value2) < 30:
                        badcount += 1
                        badval = m
                        if badcount > 5:
                            logcount += 1
                            if opts.init_only and have_ok:
                                continue
                            print have_ok, badcount, badval, m
                            return True
                    else:
                        badcount = 1
                        badval = m
            if badcount == 0:
                have_ok = True
    if last_t != 0:
        logcount += 1
    return True
        
found = []
directories = opts.directory

# allow drag and drop
if len(sys.argv) > 1:
    directories = sys.argv[1:]

filelist = []

for d in directories:
    if not os.path.exists(d):
        continue
    if os.path.isdir(d):
        print("Searching in %s" % d)
        for (root, dirs, files) in os.walk(d):
            for f in files:
                if not f.endswith('.tlog'):
                    continue
                path = os.path.join(root, f)
                filelist.append(path)
    elif d.endswith('.tlog'):
        filelist.append(d)

for i in range(len(filelist)):
    f = filelist[i]
    print("Checking %s ... [found=%u logcount=%u i=%u/%u]" % (f, len(found), logcount, i, len(filelist)))
    if AccelSearch(f):
        found.append(f)
        

if len(found) == 0:
    print("No matching files found - all OK!")
    raw_input('Press enter to close')
    sys.exit(0)

print("Creating zip file %s" % results)
try:
    zip = zipfile.ZipFile(results, 'w')
except Exception:
    print("Unable to create zip file %s" % results)
    print("Please send matching files manually")
    for f in found:
        print('MATCHED: %s' % f)
    raw_input('Press enter to close')
    sys.exit(1)

for f in found:
    zip.write(f, arcname=os.path.basename(f))
zip.close()

print('==============================================')
print("Created %s with %u of %u matching logs" % (results, len(found), logcount))
print("Please send this file to %s" % email)
print('==============================================')

raw_input('Press enter to close')
sys.exit(0)

########NEW FILE########
__FILENAME__ = magfit
#!/usr/bin/env python

'''
fit best estimate of magnetometer offsets
'''

import sys, time, os, math

from optparse import OptionParser
parser = OptionParser("magfit.py [options]")
parser.add_option("--no-timestamps",dest="notimestamps", action='store_true', help="Log doesn't have timestamps")
parser.add_option("--condition",dest="condition", default=None, help="select packets by condition")
parser.add_option("--noise", type='float', default=0, help="noise to add")

(opts, args) = parser.parse_args()

from pymavlink import mavutil
from pymavlink.rotmat import Vector3

if len(args) < 1:
    print("Usage: magfit.py [options] <LOGFILE...>")
    sys.exit(1)

def noise():
    '''a noise vector'''
    from random import gauss
    v = Vector3(gauss(0, 1), gauss(0, 1), gauss(0, 1))
    v.normalize()
    return v * opts.noise

def select_data(data):
    ret = []
    counts = {}
    for d in data:
        mag = d
        key = "%u:%u:%u" % (mag.x/20,mag.y/20,mag.z/20)
        if key in counts:
            counts[key] += 1
        else:
            counts[key] = 1
        if counts[key] < 3:
            ret.append(d)
    print(len(data), len(ret))
    return ret

def radius(mag, offsets):
    '''return radius give data point and offsets'''
    return (mag + offsets).length()

def radius_cmp(a, b, offsets):
    '''return radius give data point and offsets'''
    diff = radius(a, offsets) - radius(b, offsets)
    if diff > 0:
        return 1
    if diff < 0:
        return -1
    return 0

def sphere_error(p, data):
    from scipy import sqrt
    x,y,z,r = p
    ofs = Vector3(x,y,z)
    ret = []
    for d in data:
        mag = d
        err = r - radius(mag, ofs)
        ret.append(err)
    return ret

def fit_data(data):
    import numpy, scipy
    from scipy import optimize

    p0 = [0.0, 0.0, 0.0, 0.0]
    p1, ier = optimize.leastsq(sphere_error, p0[:], args=(data))
    if not ier in [1, 2, 3, 4]:
        raise RuntimeError("Unable to find solution")
    return (Vector3(p1[0], p1[1], p1[2]), p1[3])

def magfit(logfile):
    '''find best magnetometer offset fit to a log file'''

    print("Processing log %s" % filename)
    mlog = mavutil.mavlink_connection(filename, notimestamps=opts.notimestamps)

    data = []

    last_t = 0
    offsets = Vector3(0,0,0)

    # now gather all the data
    while True:
        m = mlog.recv_match(condition=opts.condition)
        if m is None:
            break
        if m.get_type() == "SENSOR_OFFSETS":
            # update current offsets
            offsets = Vector3(m.mag_ofs_x, m.mag_ofs_y, m.mag_ofs_z)
        if m.get_type() == "RAW_IMU":
            mag = Vector3(m.xmag, m.ymag, m.zmag)
            # add data point after subtracting the current offsets
            data.append(mag - offsets + noise())

    print("Extracted %u data points" % len(data))
    print("Current offsets: %s" % offsets)

    data = select_data(data)

    # remove initial outliers
    data.sort(lambda a,b : radius_cmp(a,b,offsets))
    data = data[len(data)/16:-len(data)/16]

    # do an initial fit
    (offsets, field_strength) = fit_data(data)

    for count in range(3):
        # sort the data by the radius
        data.sort(lambda a,b : radius_cmp(a,b,offsets))

        print("Fit %u    : %s  field_strength=%6.1f to %6.1f" % (
            count, offsets,
            radius(data[0], offsets), radius(data[-1], offsets)))
        
        # discard outliers, keep the middle 3/4
        data = data[len(data)/8:-len(data)/8]

        # fit again
        (offsets, field_strength) = fit_data(data)

    print("Final    : %s  field_strength=%6.1f to %6.1f" % (
        offsets,
        radius(data[0], offsets), radius(data[-1], offsets)))

total = 0.0
for filename in args:
    magfit(filename)

########NEW FILE########
__FILENAME__ = magfit_delta
#!/usr/bin/env python

'''
fit best estimate of magnetometer offsets using the algorithm from
Bill Premerlani
'''

import sys, time, os, math

# command line option handling
from optparse import OptionParser
parser = OptionParser("magfit_delta.py [options]")
parser.add_option("--no-timestamps",dest="notimestamps", action='store_true', help="Log doesn't have timestamps")
parser.add_option("--condition",dest="condition", default=None, help="select packets by condition")
parser.add_option("--verbose", action='store_true', default=False, help="verbose offset output")
parser.add_option("--gain", type='float', default=0.01, help="algorithm gain")
parser.add_option("--noise", type='float', default=0, help="noise to add")
parser.add_option("--max-change", type='float', default=10, help="max step change")
parser.add_option("--min-diff", type='float', default=50, help="min mag vector delta")
parser.add_option("--history", type='int', default=20, help="how many points to keep")
parser.add_option("--repeat", type='int', default=1, help="number of repeats through the data")

(opts, args) = parser.parse_args()

from pymavlink import mavutil
from pymavlink.rotmat import Vector3, Matrix3

if len(args) < 1:
    print("Usage: magfit_delta.py [options] <LOGFILE...>")
    sys.exit(1)

def noise():
    '''a noise vector'''
    from random import gauss
    v = Vector3(gauss(0, 1), gauss(0, 1), gauss(0, 1))
    v.normalize()
    return v * opts.noise

def find_offsets(data, ofs):
    '''find mag offsets by applying Bills "offsets revisited" algorithm
       on the data

       This is an implementation of the algorithm from:
          http://gentlenav.googlecode.com/files/MagnetometerOffsetNullingRevisited.pdf
       '''

    # a limit on the maximum change in each step
    max_change = opts.max_change

    # the gain factor for the algorithm
    gain = opts.gain

    data2 = []
    for d in data:
        d = d.copy() + noise()
        d.x = float(int(d.x + 0.5))
        d.y = float(int(d.y + 0.5))
        d.z = float(int(d.z + 0.5))
        data2.append(d)
    data = data2

    history_idx = 0
    mag_history = data[0:opts.history]
    
    for i in range(opts.history, len(data)):
        B1 = mag_history[history_idx] + ofs
        B2 = data[i] + ofs
        
        diff = B2 - B1
        diff_length = diff.length()
        if diff_length <= opts.min_diff:
            # the mag vector hasn't changed enough - we don't get any
            # information from this
            history_idx = (history_idx+1) % opts.history
            continue

        mag_history[history_idx] = data[i]
        history_idx = (history_idx+1) % opts.history

        # equation 6 of Bills paper
        delta = diff * (gain * (B2.length() - B1.length()) / diff_length)

        # limit the change from any one reading. This is to prevent
        # single crazy readings from throwing off the offsets for a long
        # time
        delta_length = delta.length()
        if max_change != 0 and delta_length > max_change:
            delta *= max_change / delta_length

        # set the new offsets
        ofs = ofs - delta

        if opts.verbose:
            print ofs
    return ofs


def magfit(logfile):
    '''find best magnetometer offset fit to a log file'''

    print("Processing log %s" % filename)

    # open the log file
    mlog = mavutil.mavlink_connection(filename, notimestamps=opts.notimestamps)

    data = []
    mag = None
    offsets = Vector3(0,0,0)
    
    # now gather all the data
    while True:
        # get the next MAVLink message in the log
        m = mlog.recv_match(condition=opts.condition)
        if m is None:
            break
        if m.get_type() == "SENSOR_OFFSETS":
            # update offsets that were used during this flight
            offsets = Vector3(m.mag_ofs_x, m.mag_ofs_y, m.mag_ofs_z)
        if m.get_type() == "RAW_IMU" and offsets != None:
            # extract one mag vector, removing the offsets that were
            # used during that flight to get the raw sensor values
            mag = Vector3(m.xmag, m.ymag, m.zmag) - offsets
            data.append(mag)

    print("Extracted %u data points" % len(data))
    print("Current offsets: %s" % offsets)

    # run the fitting algorithm
    ofs = offsets
    ofs = Vector3(0,0,0)
    for r in range(opts.repeat):
        ofs = find_offsets(data, ofs)
        print('Loop %u offsets %s' % (r, ofs))
        sys.stdout.flush()
    print("New offsets: %s" % ofs)

total = 0.0
for filename in args:
    magfit(filename)

########NEW FILE########
__FILENAME__ = magfit_gps
#!/usr/bin/env python

'''
fit best estimate of magnetometer offsets
'''

import sys, time, os, math

from optparse import OptionParser
parser = OptionParser("magfit.py [options]")
parser.add_option("--no-timestamps",dest="notimestamps", action='store_true', help="Log doesn't have timestamps")
parser.add_option("--minspeed", type='float', default=5.0, help="minimum ground speed to use")

(opts, args) = parser.parse_args()

from pymavlink import mavutil

if len(args) < 1:
    print("Usage: magfit.py [options] <LOGFILE...>")
    sys.exit(1)

class vec3(object):
    def __init__(self, x, y, z):
        self.x = x
        self.y = y
        self.z = z
    def __str__(self):
        return "%.1f %.1f %.1f" % (self.x, self.y, self.z)

def heading_error1(parm, data):
    from math import sin, cos, atan2, degrees
    from numpy import dot
    xofs,yofs,zofs,a1,a2,a3,a4,a5,a6,a7,a8,a9,declination = parm

    ret = []
    for d in data:
        x = d[0] + xofs
        y = d[1] + yofs
        z = d[2] + zofs
        r = d[3]
        p = d[4]
        h = d[5]

        headX = x*cos(p) + y*sin(r)*sin(p) + z*cos(r)*sin(p)
        headY = y*cos(r) - z*sin(r)
        heading = degrees(atan2(-headY,headX)) + declination
        if heading < 0:
            heading += 360
        herror = h - heading
        if herror > 180:
            herror -= 360
        if herror < -180:
            herror += 360
        ret.append(herror)
    return ret

def heading_error(parm, data):
    from math import sin, cos, atan2, degrees
    from numpy import dot
    xofs,yofs,zofs,a1,a2,a3,a4,a5,a6,a7,a8,a9,declination = parm

    a = [[1.0,a2,a3],[a4,a5,a6],[a7,a8,a9]]

    ret = []
    for d in data:
        x = d[0] + xofs
        y = d[1] + yofs
        z = d[2] + zofs
        r = d[3]
        p = d[4]
        h = d[5]
        mv = [x, y, z]
        mv2 = dot(a, mv)
        x = mv2[0]
        y = mv2[1]
        z = mv2[2]

        headX = x*cos(p) + y*sin(r)*sin(p) + z*cos(r)*sin(p)
        headY = y*cos(r) - z*sin(r)
        heading = degrees(atan2(-headY,headX)) + declination
        if heading < 0:
            heading += 360
        herror = h - heading
        if herror > 180:
            herror -= 360
        if herror < -180:
            herror += 360
        ret.append(herror)
    return ret

def fit_data(data):
    import numpy, scipy
    from scipy import optimize

    p0 = [0.0, 0.0, 0.0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0]
    p1, ier = optimize.leastsq(heading_error1, p0[:], args=(data))

#    p0 = p1[:]
#    p1, ier = optimize.leastsq(heading_error, p0[:], args=(data))

    print(p1)
    if not ier in [1, 2, 3, 4]:
        raise RuntimeError("Unable to find solution")
    return p1

def magfit(logfile):
    '''find best magnetometer offset fit to a log file'''
    print("Processing log %s" % filename)
    mlog = mavutil.mavlink_connection(filename, notimestamps=opts.notimestamps)

    flying = False
    gps_heading = 0.0

    data = []

    # get the current mag offsets
    m = mlog.recv_match(type='SENSOR_OFFSETS')
    offsets = vec3(m.mag_ofs_x, m.mag_ofs_y, m.mag_ofs_z)

    attitude = mlog.recv_match(type='ATTITUDE')

    # now gather all the data
    while True:
        m = mlog.recv_match()
        if m is None:
            break
        if m.get_type() == "GPS_RAW":
            # flying if groundspeed more than 5 m/s
            flying = (m.v > opts.minspeed and m.fix_type == 2)
            gps_heading = m.hdg
        if m.get_type() == "GPS_RAW_INT":
            # flying if groundspeed more than 5 m/s
            flying = (m.vel/100 > opts.minspeed and m.fix_type == 3)
            gps_heading = m.cog/100
        if m.get_type() == "ATTITUDE":
            attitude = m
        if m.get_type() == "SENSOR_OFFSETS":
            # update current offsets
            offsets = vec3(m.mag_ofs_x, m.mag_ofs_y, m.mag_ofs_z)
        if not flying:
            continue
        if m.get_type() == "RAW_IMU":
            data.append((m.xmag - offsets.x, m.ymag - offsets.y, m.zmag - offsets.z, attitude.roll, attitude.pitch, gps_heading))
    print("Extracted %u data points" % len(data))
    print("Current offsets: %s" % offsets)
    ofs2 = fit_data(data)
    print("Declination estimate: %.1f" % ofs2[-1])
    new_offsets = vec3(ofs2[0], ofs2[1], ofs2[2])
    a = [[ofs2[3], ofs2[4], ofs2[5]],
         [ofs2[6], ofs2[7], ofs2[8]],
         [ofs2[9], ofs2[10], ofs2[11]]]
    print(a)
    print("New offsets    : %s" % new_offsets)

total = 0.0
for filename in args:
    magfit(filename)

########NEW FILE########
__FILENAME__ = magfit_motors
#!/usr/bin/env python

'''
fit best estimate of magnetometer offsets, trying to take into account motor interference
'''

import sys, time, os, math

from optparse import OptionParser
parser = OptionParser("magfit.py [options]")
parser.add_option("--no-timestamps",dest="notimestamps", action='store_true', help="Log doesn't have timestamps")
parser.add_option("--condition",dest="condition", default=None, help="select packets by condition")
parser.add_option("--noise", type='float', default=0, help="noise to add")

(opts, args) = parser.parse_args()

from pymavlink import mavutil
from pymavlink.rotmat import Vector3

if len(args) < 1:
    print("Usage: magfit.py [options] <LOGFILE...>")
    sys.exit(1)

def noise():
    '''a noise vector'''
    from random import gauss
    v = Vector3(gauss(0, 1), gauss(0, 1), gauss(0, 1))
    v.normalize()
    return v * opts.noise

def select_data(data):
    ret = []
    counts = {}
    for d in data:
        (mag,motor) = d
        key = "%u:%u:%u" % (mag.x/20,mag.y/20,mag.z/20)
        if key in counts:
            counts[key] += 1
        else:
            counts[key] = 1
        if counts[key] < 3:
            ret.append(d)
    print(len(data), len(ret))
    return ret

def radius(d, offsets, motor_ofs):
    '''return radius give data point and offsets'''
    (mag, motor) = d
    return (mag + offsets + motor*motor_ofs).length()

def radius_cmp(a, b, offsets, motor_ofs):
    '''return radius give data point and offsets'''
    diff = radius(a, offsets, motor_ofs) - radius(b, offsets, motor_ofs)
    if diff > 0:
        return 1
    if diff < 0:
        return -1
    return 0

def sphere_error(p, data):
    from scipy import sqrt
    x,y,z,mx,my,mz,r = p
    ofs = Vector3(x,y,z)
    motor_ofs = Vector3(mx,my,mz)
    ret = []
    for d in data:
        (mag,motor) = d
        err = r - radius((mag,motor), ofs, motor_ofs)
        ret.append(err)
    return ret

def fit_data(data):
    import numpy, scipy
    from scipy import optimize

    p0 = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    p1, ier = optimize.leastsq(sphere_error, p0[:], args=(data))
    if not ier in [1, 2, 3, 4]:
        raise RuntimeError("Unable to find solution")
    return (Vector3(p1[0], p1[1], p1[2]), Vector3(p1[3], p1[4], p1[5]), p1[6])

def magfit(logfile):
    '''find best magnetometer offset fit to a log file'''

    print("Processing log %s" % filename)
    mlog = mavutil.mavlink_connection(filename, notimestamps=opts.notimestamps)

    data = []

    last_t = 0
    offsets = Vector3(0,0,0)
    motor_ofs = Vector3(0,0,0)
    motor = 0.0

    # now gather all the data
    while True:
        m = mlog.recv_match(condition=opts.condition)
        if m is None:
            break
        if m.get_type() == "PARAM_VALUE" and m.param_id == "RC3_MIN":
            rc3_min = float(m.param_value)
        if m.get_type() == "SENSOR_OFFSETS":
            # update current offsets
            offsets = Vector3(m.mag_ofs_x, m.mag_ofs_y, m.mag_ofs_z)
        if m.get_type() == "SERVO_OUTPUT_RAW":
            motor_pwm = m.servo1_raw + m.servo2_raw + m.servo3_raw + m.servo4_raw
            motor_pwm *= 0.25
            rc3_min = mlog.param('RC3_MIN', 1100)
            rc3_max = mlog.param('RC3_MAX', 1900)
            motor = (motor_pwm - rc3_min) / (rc3_max - rc3_min)
            if motor > 1.0:
                motor = 1.0
            if motor < 0.0:
                motor = 0.0                
        if m.get_type() == "RAW_IMU":
            mag = Vector3(m.xmag, m.ymag, m.zmag)
            # add data point after subtracting the current offsets
            data.append((mag - offsets + noise(), motor))

    print("Extracted %u data points" % len(data))
    print("Current offsets: %s" % offsets)

    data = select_data(data)

    # do an initial fit with all data
    (offsets, motor_ofs, field_strength) = fit_data(data)

    for count in range(3):
        # sort the data by the radius
        data.sort(lambda a,b : radius_cmp(a,b,offsets,motor_ofs))

        print("Fit %u    : %s  %s field_strength=%6.1f to %6.1f" % (
            count, offsets, motor_ofs,
            radius(data[0], offsets, motor_ofs), radius(data[-1], offsets, motor_ofs)))
        
        # discard outliers, keep the middle 3/4
        data = data[len(data)/8:-len(data)/8]

        # fit again
        (offsets, motor_ofs, field_strength) = fit_data(data)

    print("Final    : %s  %s field_strength=%6.1f to %6.1f" % (
        offsets, motor_ofs, 
        radius(data[0], offsets, motor_ofs), radius(data[-1], offsets, motor_ofs)))
    print "mavgraph.py '%s' 'mag_field(RAW_IMU)' 'mag_field_motors(RAW_IMU,SENSOR_OFFSETS,(%f,%f,%f),SERVO_OUTPUT_RAW,(%f,%f,%f))'" % (
        filename,
        offsets.x,offsets.y,offsets.z,
        motor_ofs.x, motor_ofs.y, motor_ofs.z)

total = 0.0
for filename in args:
    magfit(filename)

########NEW FILE########
__FILENAME__ = magfit_rotation_gps
#!/usr/bin/env python

'''
fit best estimate of magnetometer rotation to GPS data
'''

import sys, time, os, math

from optparse import OptionParser
parser = OptionParser("magfit_rotation_gps.py [options]")
parser.add_option("--no-timestamps",dest="notimestamps", action='store_true', help="Log doesn't have timestamps")
parser.add_option("--declination", default=0.0, type='float', help="magnetic declination")
parser.add_option("--min-speed", default=4.0, type='float', help="minimum GPS speed")

(opts, args) = parser.parse_args()

from pymavlink import mavutil
from pymavlink.rotmat import Vector3, Matrix3
from math import radians, degrees, sin, cos, atan2

if len(args) < 1:
    print("Usage: magfit_rotation.py [options] <LOGFILE...>")
    sys.exit(1)

class Rotation(object):
    def __init__(self, roll, pitch, yaw, r):
        self.roll = roll
        self.pitch = pitch
        self.yaw = yaw
        self.r = r

def in_rotations_list(rotations, m):
    for r in rotations:
        m2 = m.transposed() * r.r
        (r, p, y) = m2.to_euler()
        if (abs(r) < radians(1) and
            abs(p) < radians(1) and
            abs(y) < radians(1)):
            return True
    return False

def generate_rotations():
    '''generate all 90 degree rotations'''
    rotations = []
    for yaw in [0, 90, 180, 270]:
        for pitch in [0, 90, 180, 270]:
            for roll in [0, 90, 180, 270]:
                m = Matrix3()
                m.from_euler(radians(roll), radians(pitch), radians(yaw))
                if not in_rotations_list(rotations, m):
                    rotations.append(Rotation(roll, pitch, yaw, m))
    return rotations

def angle_diff(angle1, angle2):
    '''give the difference between two angles in degrees'''
    ret = angle1 - angle2
    if ret > 180:
        ret -= 360;
    if ret < -180:
        ret += 360
    return ret

def heading_difference(mag, attitude, declination):
    r = attitude.roll
    p = attitude.pitch
    headX = mag.x*cos(p) + mag.y*sin(r)*sin(p) + mag.z*cos(r)*sin(p)
    headY = mag.y*cos(r) - mag.z*sin(r)
    heading = degrees(atan2(-headY,headX)) + declination
    heading2 = degrees(attitude.yaw)
    return abs(angle_diff(heading, heading2))

def add_errors(mag, attitude, total_error, rotations):
    for i in range(len(rotations)):
        r = rotations[i].r
        rmag = r * mag
        total_error[i] += heading_difference(rmag, attitude, opts.declination)
        

def magfit(logfile):
    '''find best magnetometer rotation fit to a log file'''

    print("Processing log %s" % filename)
    mlog = mavutil.mavlink_connection(filename, notimestamps=opts.notimestamps)

    # generate 90 degree rotations
    rotations = generate_rotations()
    print("Generated %u rotations" % len(rotations))

    count = 0
    total_error = [0]*len(rotations)
    attitude = None
    gps = None

    # now gather all the data
    while True:
        m = mlog.recv_match()
        if m is None:
            break
        if m.get_type() == "ATTITUDE":
            attitude = m
        if m.get_type() == "GPS_RAW_INT":
            gps = m
        if m.get_type() == "RAW_IMU":
            mag = Vector3(m.xmag, m.ymag, m.zmag)
            if attitude is not None and gps is not None and gps.vel > opts.min_speed*100 and gps.fix_type>=3:
                add_errors(mag, attitude, total_error, rotations)
            count += 1

    best_i = 0
    best_err = total_error[0]
    for i in range(len(rotations)):
        r = rotations[i]
        print("(%u,%u,%u) err=%.2f" % (
            r.roll,
            r.pitch,
            r.yaw,
            total_error[i]/count))
        if total_error[i] < best_err:
            best_i = i
            best_err = total_error[i]
    r = rotations[best_i]
    print("Best rotation (%u,%u,%u) err=%.2f" % (
        r.roll,
        r.pitch,
        r.yaw,
        best_err/count))

for filename in args:
    magfit(filename)

########NEW FILE########
__FILENAME__ = magfit_rotation_gyro
#!/usr/bin/env python

'''
fit best estimate of magnetometer rotation to gyro data
'''

import sys, time, os, math

from optparse import OptionParser
parser = OptionParser("magfit_rotation_gyro.py [options]")
parser.add_option("--no-timestamps",dest="notimestamps", action='store_true', help="Log doesn't have timestamps")
parser.add_option("--verbose", action='store_true', help="verbose output")
parser.add_option("--min-rotation", default=5.0, type='float', help="min rotation to add point")

(opts, args) = parser.parse_args()

from pymavlink import mavutil
from pymavlink.rotmat import Vector3, Matrix3
from math import radians, degrees

if len(args) < 1:
    print("Usage: magfit_rotation_gyro.py [options] <LOGFILE...>")
    sys.exit(1)

class Rotation(object):
    def __init__(self, name, roll, pitch, yaw):
        self.name = name
        self.roll = roll
        self.pitch = pitch
        self.yaw = yaw
        self.r = Matrix3()
        self.r.from_euler(self.roll, self.pitch, self.yaw)

    def is_90_degrees(self):
        return (self.roll % 90 == 0) and (self.pitch % 90 == 0) and (self.yaw % 90 == 0)

    def __str__(self):
        return self.name

# the rotations used in APM
rotations = [
    Rotation("ROTATION_NONE",                      0,   0,   0),
    Rotation("ROTATION_YAW_45",                    0,   0,  45),
    Rotation("ROTATION_YAW_90",                    0,   0,  90),
    Rotation("ROTATION_YAW_135",                   0,   0, 135),
    Rotation("ROTATION_YAW_180",                   0,   0, 180),
    Rotation("ROTATION_YAW_225",                   0,   0, 225),
    Rotation("ROTATION_YAW_270",                   0,   0, 270),
    Rotation("ROTATION_YAW_315",                   0,   0, 315),
    Rotation("ROTATION_ROLL_180",                180,   0,   0),
    Rotation("ROTATION_ROLL_180_YAW_45",         180,   0,  45),
    Rotation("ROTATION_ROLL_180_YAW_90",         180,   0,  90),
    Rotation("ROTATION_ROLL_180_YAW_135",        180,   0, 135),
    Rotation("ROTATION_PITCH_180",                 0, 180,   0),
    Rotation("ROTATION_ROLL_180_YAW_225",        180,   0, 225),
    Rotation("ROTATION_ROLL_180_YAW_270",        180,   0, 270),
    Rotation("ROTATION_ROLL_180_YAW_315",        180,   0, 315),
    Rotation("ROTATION_ROLL_90",                  90,   0,   0),
    Rotation("ROTATION_ROLL_90_YAW_45",           90,   0,  45),
    Rotation("ROTATION_ROLL_90_YAW_90",           90,   0,  90),
    Rotation("ROTATION_ROLL_90_YAW_135",          90,   0, 135),
    Rotation("ROTATION_ROLL_270",                270,   0,   0),
    Rotation("ROTATION_ROLL_270_YAW_45",         270,   0,  45),
    Rotation("ROTATION_ROLL_270_YAW_90",         270,   0,  90),
    Rotation("ROTATION_ROLL_270_YAW_135",        270,   0, 135),
    Rotation("ROTATION_PITCH_90",                  0,  90,   0),
    Rotation("ROTATION_PITCH_270",                 0, 270,   0),    
    Rotation("ROTATION_PITCH_180_YAW_90",          0, 180,  90),    
    Rotation("ROTATION_PITCH_180_YAW_270",         0, 180, 270),    
    Rotation("ROTATION_ROLL_90_PITCH_90",         90,  90,   0),    
    Rotation("ROTATION_ROLL_180_PITCH_90",       180,  90,   0),    
    Rotation("ROTATION_ROLL_270_PITCH_90",       270,  90,   0),    
    Rotation("ROTATION_ROLL_90_PITCH_180",        90, 180,   0),    
    Rotation("ROTATION_ROLL_270_PITCH_180",      270, 180,   0),    
    Rotation("ROTATION_ROLL_90_PITCH_270",        90, 270,   0),    
    Rotation("ROTATION_ROLL_180_PITCH_270",      180, 270,   0),    
    Rotation("ROTATION_ROLL_270_PITCH_270",      270, 270,   0),    
    Rotation("ROTATION_ROLL_90_PITCH_180_YAW_90", 90, 180,  90),    
    Rotation("ROTATION_ROLL_90_YAW_270",          90,   0, 270)
    ]

def mag_fixup(mag, AHRS_ORIENTATION, COMPASS_ORIENT, COMPASS_EXTERNAL):
    '''fixup a mag vector back to original value using AHRS and Compass orientation parameters'''
    if COMPASS_EXTERNAL == 0 and AHRS_ORIENTATION != 0:
        # undo any board orientation
        mag = rotations[AHRS_ORIENTATION].r.transposed() * mag
    # undo any compass orientation
    if COMPASS_ORIENT != 0:
        mag = rotations[COMPASS_ORIENT].r.transposed() * mag
    return mag

def add_errors(mag, gyr, last_mag, deltat, total_error, rotations):
    for i in range(len(rotations)):
        if not rotations[i].is_90_degrees():
            continue
        r = rotations[i].r
        m = Matrix3()
        m.rotate(gyr * deltat)
        rmag1 = r * last_mag
        rmag2 = r * mag
        rmag3 = m.transposed() * rmag1
        err = rmag3 - rmag2
        total_error[i] += err.length()
        

def magfit(logfile):
    '''find best magnetometer rotation fit to a log file'''

    print("Processing log %s" % filename)
    mlog = mavutil.mavlink_connection(filename, notimestamps=opts.notimestamps)

    last_mag = None
    last_usec = 0
    count = 0
    total_error = [0]*len(rotations)

    AHRS_ORIENTATION = 0
    COMPASS_ORIENT = 0
    COMPASS_EXTERNAL = 0

    # now gather all the data
    while True:
        m = mlog.recv_match()
        if m is None:
            break
        if m.get_type() == "PARAM_VALUE":
            if str(m.param_id) == 'AHRS_ORIENTATION':
                AHRS_ORIENTATION = int(m.param_value)
            if str(m.param_id) == 'COMPASS_ORIENT':
                COMPASS_ORIENT = int(m.param_value)
            if str(m.param_id) == 'COMPASS_EXTERNAL':
                COMPASS_EXTERNAL = int(m.param_value)
        if m.get_type() == "RAW_IMU":
            mag = Vector3(m.xmag, m.ymag, m.zmag)
            mag = mag_fixup(mag, AHRS_ORIENTATION, COMPASS_ORIENT, COMPASS_EXTERNAL)
            gyr = Vector3(m.xgyro, m.ygyro, m.zgyro) * 0.001
            usec = m.time_usec
            if last_mag is not None and gyr.length() > radians(opts.min_rotation):
                add_errors(mag, gyr, last_mag, (usec - last_usec)*1.0e-6, total_error, rotations)
                count += 1
            last_mag = mag
            last_usec = usec

    best_i = 0
    best_err = total_error[0]
    for i in range(len(rotations)):
        r = rotations[i]
        if not r.is_90_degrees():
            continue
        if opts.verbose:
            print("%s err=%.2f" % (r, total_error[i]/count))
        if total_error[i] < best_err:
            best_i = i
            best_err = total_error[i]
    r = rotations[best_i]
    print("Current rotation is AHRS_ORIENTATION=%s COMPASS_ORIENT=%s COMPASS_EXTERNAL=%u" % (
        rotations[AHRS_ORIENTATION],
        rotations[COMPASS_ORIENT],
        COMPASS_EXTERNAL))
    print("Best rotation is %s err=%.2f from %u points" % (r, best_err/count, count))
    print("Please set AHRS_ORIENTATION=%s COMPASS_ORIENT=%s COMPASS_EXTERNAL=1" % (
        rotations[AHRS_ORIENTATION],
        r))

for filename in args:
    magfit(filename)

########NEW FILE########
__FILENAME__ = mavextract
#!/usr/bin/env python

'''
extract one mode type from a log
'''

import sys, time, os, struct

from optparse import OptionParser
parser = OptionParser("mavextract.py [options]")

parser.add_option("--no-timestamps",dest="notimestamps", action='store_true', help="Log doesn't have timestamps")
parser.add_option("--robust",dest="robust", action='store_true', help="Enable robust parsing (skip over bad data)")
parser.add_option("--condition",dest="condition", default=None, help="select packets by condition")
parser.add_option("--mode",  default='auto', help="mode to extract")
(opts, args) = parser.parse_args()

from pymavlink import mavutil

if len(args) < 1:
    print("Usage: mavextract.py [options] <LOGFILE>")
    sys.exit(1)

def process(filename):
    '''process one logfile'''
    print("Processing %s" % filename)
    mlog = mavutil.mavlink_connection(filename, notimestamps=opts.notimestamps,
                                      robust_parsing=opts.robust)


    ext = os.path.splitext(filename)[1]
    isbin = ext in ['.bin', '.BIN']
    islog = ext in ['.log', '.LOG']
    output = None
    count = 1
    dirname = os.path.dirname(filename)

    if isbin or islog:
        extension = "bin"
    else:
        extension = "tlog"

    file_header = ''

    while True:
        m = mlog.recv_match()
        if m is None:
            break
        if (isbin or islog) and m.get_type() in ["FMT", "PARM", "CMD"]:
            file_header += m.get_msgbuf()
        if (isbin or islog) and m.get_type() == 'MSG' and m.Message.startswith("Ardu"):
            file_header += m.get_msgbuf()
        if m.get_type() in ['PARAM_VALUE','MISSION_ITEM']:
            timestamp = getattr(m, '_timestamp', None)
            file_header += struct.pack('>Q', timestamp*1.0e6) + m.get_msgbuf()
            
        if not mavutil.evaluate_condition(opts.condition, mlog.messages):
            continue

        if mlog.flightmode.upper() == opts.mode.upper():
            if output is None:
                path = os.path.join(dirname, "%s%u.%s" % (opts.mode, count, extension))
                count += 1
                print("Creating %s" % path)
                output = open(path, mode='wb')
                output.write(file_header)
        else:
            if output is not None:
                output.close()
                output = None
            
        if output and m.get_type() != 'BAD_DATA':
            timestamp = getattr(m, '_timestamp', None)
            if not isbin:
                output.write(struct.pack('>Q', timestamp*1.0e6))
            output.write(m.get_msgbuf())

for filename in args:
    process(filename)


########NEW FILE########
__FILENAME__ = mavflightmodes
#!/usr/bin/env python

'''
show changes in flight modes
'''

import sys, time, os

from optparse import OptionParser
parser = OptionParser("flightmodes.py [options]")

(opts, args) = parser.parse_args()

from pymavlink import mavutil

if len(args) < 1:
    print("Usage: flightmodes.py [options] <LOGFILE...>")
    sys.exit(1)

def flight_modes(logfile):
    '''show flight modes for a log file'''
    print("Processing log %s" % filename)
    mlog = mavutil.mavlink_connection(filename)

    mode = -1
    nav_mode = -1

    filesize = os.path.getsize(filename)

    while True:
        m = mlog.recv_match(type=['SYS_STATUS','HEARTBEAT','MODE'],
                            condition='MAV.flightmode!="%s"' % mlog.flightmode)
        if m is None:
            return
        print('%s MAV.flightmode=%-12s (MAV.timestamp=%u %u%%)' % (
            time.asctime(time.localtime(m._timestamp)),
            mlog.flightmode,
            m._timestamp, mlog.percent))

for filename in args:
    flight_modes(filename)



########NEW FILE########
__FILENAME__ = mavflighttime
#!/usr/bin/env python

'''
work out total flight time for a mavlink log
'''

import sys, time, os, glob

from optparse import OptionParser
parser = OptionParser("flighttime.py [options]")
parser.add_option("--condition", default=None, help="condition for packets")
parser.add_option("--groundspeed", type='float', default=3.0, help="groundspeed threshold")

(opts, args) = parser.parse_args()

from pymavlink import mavutil
from pymavlink.mavextra import distance_two

if len(args) < 1:
    print("Usage: flighttime.py [options] <LOGFILE...>")
    sys.exit(1)

def flight_time(logfile):
    '''work out flight time for a log file'''
    print("Processing log %s" % filename)
    mlog = mavutil.mavlink_connection(filename)

    in_air = False
    start_time = 0.0
    total_time = 0.0
    total_dist = 0.0
    t = None
    last_msg = None

    while True:
        m = mlog.recv_match(type=['GPS','GPS_RAW_INT'], condition=opts.condition)
        if m is None:
            if in_air:
                total_time += time.mktime(t) - start_time
            if total_time > 0:
                print("Flight time : %u:%02u" % (int(total_time)/60, int(total_time)%60))
            return (total_time, total_dist)
        if m.get_type() == 'GPS_RAW_INT':
            groundspeed = m.vel*0.01
            status = m.fix_type
        else:
            groundspeed = m.Spd
            status = m.Status
        if status < 3:
            continue
        t = time.localtime(m._timestamp)
        if groundspeed > opts.groundspeed and not in_air:
            print("In air at %s (percent %.0f%% groundspeed %.1f)" % (time.asctime(t), mlog.percent, groundspeed))
            in_air = True
            start_time = time.mktime(t)
        elif groundspeed < opts.groundspeed and in_air:
            print("On ground at %s (percent %.1f%% groundspeed %.1f  time=%.1f seconds)" % (
                time.asctime(t), mlog.percent, groundspeed, time.mktime(t) - start_time))
            in_air = False
            total_time += time.mktime(t) - start_time

        if last_msg is not None:
            total_dist += distance_two(last_msg, m)
        last_msg = m
    return (total_time, total_dist)

total_time = 0.0
total_dist = 0.0
for filename in args:
    for f in glob.glob(filename):
        (ftime, fdist) = flight_time(f)
        total_time += ftime
        total_dist += fdist

print("Total time in air: %u:%02u" % (int(total_time)/60, int(total_time)%60))
print("Total distance trevelled: %.1f meters" % total_dist)

########NEW FILE########
__FILENAME__ = mavgpslag
#!/usr/bin/env python

'''
calculate GPS lag from DF log
'''

import sys, time, os

from optparse import OptionParser
parser = OptionParser("mavgpslag.py [options]")
parser.add_option("--plot", action='store_true', default=False, help="plot errors")
parser.add_option("--minspeed", type='float', default=6, help="minimum speed")

(opts, args) = parser.parse_args()

from pymavlink import mavutil
from pymavlink.mavextra import *
from pymavlink.rotmat import Vector3, Matrix3

'''
Support having a $HOME/.pymavlink/mavextra.py for extra graphing functions
'''
home = os.getenv('HOME')
if home is not None:
    extra = os.path.join(home, '.pymavlink', 'mavextra.py')
    if os.path.exists(extra):
        import imp
        mavuser = imp.load_source('pymavlink.mavuser', extra)
        from pymavlink.mavuser import *

if len(args) < 1:
    print("Usage: mavgpslag.py [options] <LOGFILE...>")
    sys.exit(1)

def velocity_error(timestamps, vel, gaccel, accel_indexes, imu_dt, shift=0):
    '''return summed velocity error'''
    sum = 0
    count = 0
    for i in range(0, len(vel)-1):
        dv = vel[i+1] - vel[i]
        da = Vector3()
        for idx in range(1+accel_indexes[i]-shift, 1+accel_indexes[i+1]-shift):
            da += gaccel[idx]
        dt1 = timestamps[i+1] - timestamps[i]
        dt2 = (accel_indexes[i+1] - accel_indexes[i]) * imu_dt
        da *= imu_dt
        da *= dt1/dt2
        #print(accel_indexes[i+1] - accel_indexes[i])
        ex = abs(dv.x - da.x)
        ey = abs(dv.y - da.y)
        sum += 0.5*(ex+ey)
        count += 1
    if count == 0:
        return None
    return sum/count

def gps_lag(logfile):
    '''work out gps velocity lag times for a log file'''
    print("Processing log %s" % filename)
    mlog = mavutil.mavlink_connection(filename)

    timestamps = []
    vel = []
    gaccel = []
    accel_indexes = []
    ATT = None
    IMU = None

    dtsum = 0
    dtcount = 0
    
    while True:
        m = mlog.recv_match(type=['GPS','IMU','ATT'])
        if m is None:
            break
        t = m.get_type()
        if t == 'GPS' and m.Status==3 and m.Spd>opts.minspeed:
            v = Vector3(m.Spd*cos(radians(m.GCrs)), m.Spd*sin(radians(m.GCrs)), m.VZ)
            vel.append(v)
            timestamps.append(m._timestamp)
            accel_indexes.append(max(len(gaccel)-1,0))
        elif t == 'ATT':
            ATT = m
        elif t == 'IMU':
            if ATT is not None:
                gaccel.append(earth_accel_df(m, ATT))
                if IMU is not None:
                    dt = m._timestamp - IMU._timestamp
                    dtsum += dt
                    dtcount += 1
                IMU = m

    imu_dt = dtsum / dtcount

    print("Loaded %u samples imu_dt=%.3f" % (len(vel), imu_dt))
    besti = -1
    besterr = 0
    delays = []
    errors = []
    for i in range(0,100):
        err = velocity_error(timestamps, vel, gaccel, accel_indexes, imu_dt, shift=i)
        if err is None:
            break
        errors.append(err)
        delays.append(i*imu_dt)
        if besti == -1 or err < besterr:
            besti = i
            besterr = err
    print("Best %u (%.3fs) %f" % (besti, besti*imu_dt, besterr))

    if opts.plot:
        import matplotlib.pyplot as plt
        plt.plot(delays, errors, 'bo-')
        x1,x2,y1,y2 = plt.axis()
        plt.axis((x1,x2,0,y2))
        plt.ylabel('Error')
        plt.xlabel('Delay(s)')
        plt.show()
    

for filename in args:
    gps_lag(filename)


########NEW FILE########
__FILENAME__ = mavgpslock
#!/usr/bin/env python

'''
show GPS lock events in a MAVLink log
'''

import sys, time, os

from optparse import OptionParser
parser = OptionParser("gpslock.py [options]")
parser.add_option("--condition", default=None, help="condition for packets")

(opts, args) = parser.parse_args()

from pymavlink import mavutil

if len(args) < 1:
    print("Usage: gpslock.py [options] <LOGFILE...>")
    sys.exit(1)

def lock_time(logfile):
    '''work out gps lock times for a log file'''
    print("Processing log %s" % filename)
    mlog = mavutil.mavlink_connection(filename)

    locked = False
    start_time = 0.0
    total_time = 0.0
    t = None
    m = mlog.recv_match(type=['GPS_RAW_INT','GPS_RAW'], condition=opts.condition)
    if m is None:
        return 0

    unlock_time = time.mktime(time.localtime(m._timestamp))

    while True:
        m = mlog.recv_match(type=['GPS_RAW_INT','GPS_RAW'], condition=opts.condition)
        if m is None:
            if locked:
                total_time += time.mktime(t) - start_time
            if total_time > 0:
                print("Lock time : %u:%02u" % (int(total_time)/60, int(total_time)%60))
            return total_time
        t = time.localtime(m._timestamp)
        if m.fix_type >= 2 and not locked:
            print("Locked at %s after %u seconds" % (time.asctime(t),
                                                     time.mktime(t) - unlock_time))
            locked = True
            start_time = time.mktime(t)
        elif m.fix_type == 1 and locked:
            print("Lost GPS lock at %s" % time.asctime(t))
            locked = False
            total_time += time.mktime(t) - start_time
            unlock_time = time.mktime(t)
        elif m.fix_type == 0 and locked:
            print("Lost protocol lock at %s" % time.asctime(t))
            locked = False
            total_time += time.mktime(t) - start_time
            unlock_time = time.mktime(t)
    return total_time

total = 0.0
for filename in args:
    total += lock_time(filename)

print("Total time locked: %u:%02u" % (int(total)/60, int(total)%60))

########NEW FILE########
__FILENAME__ = mavgraph
#!/usr/bin/env python
'''
graph a MAVLink log file
Andrew Tridgell August 2011
'''

import sys, struct, time, os, datetime
import math, re
import pylab, matplotlib
from math import *

from pymavlink.mavextra import *

locator = None
formatter = None

colourmap = {
    'apm' : {
        'MANUAL'    : (1.0,   0,   0),
        'AUTO'      : (  0, 1.0,   0),
        'LOITER'    : (  0,   0, 1.0),
        'FBWA'      : (1.0, 0.5,   0),
        'RTL'       : (  1,   0, 0.5),
        'STABILIZE' : (0.5, 1.0,   0),
        'LAND'      : (  0, 1.0, 0.5),
        'STEERING'  : (0.5,   0, 1.0),
        'HOLD'      : (  0, 0.5, 1.0),
        'ALT_HOLD'  : (1.0, 0.5, 0.5),
        'CIRCLE'    : (0.5, 1.0, 0.5),
        'POSITION'  : (1.0, 0.0, 1.0),
        'GUIDED'    : (0.5, 0.5, 1.0),
        'ACRO'      : (1.0, 1.0,   0),
        'CRUISE'    : (  0, 1.0, 1.0)
        },
    'px4' : {
        'MANUAL'    : (1.0,   0,   0),
        'SEATBELT'  : (  0.5, 0.5,   0),
        'EASY'      : (  0, 1.0,   0),
        'AUTO'    : (  0,   0, 1.0),
        'UNKNOWN'    : (  1.0,   1.0, 1.0)
        }
    }

edge_colour = (0.1, 0.1, 0.1)

def plotit(x, y, fields, colors=[]):
    '''plot a set of graphs using date for x axis'''
    global locator, formatter
    pylab.ion()
    fig = pylab.figure(num=1, figsize=(12,6))
    ax1 = fig.gca()
    ax2 = None
    xrange = 0.0
    for i in range(0, len(fields)):
        if len(x[i]) == 0: continue
        if x[i][-1] - x[i][0] > xrange:
            xrange = x[i][-1] - x[i][0]
    xrange *= 24 * 60 * 60
    if formatter is None:
        formatter = matplotlib.dates.DateFormatter('%H:%M:%S')
        interval = 1
        intervals = [ 1, 2, 5, 10, 15, 30, 60, 120, 240, 300, 600,
                      900, 1800, 3600, 7200, 5*3600, 10*3600, 24*3600 ]
        for interval in intervals:
            if xrange / interval < 15:
                break
        locator = matplotlib.dates.SecondLocator(interval=interval)
    if not opts.xaxis:
        ax1.xaxis.set_major_locator(locator)
        ax1.xaxis.set_major_formatter(formatter)
    empty = True
    ax1_labels = []
    ax2_labels = []
    for i in range(0, len(fields)):
        if len(x[i]) == 0:
            print("Failed to find any values for field %s" % fields[i])
            continue
        if i < len(colors):
            color = colors[i]
        else:
            color = 'red'
        (tz, tzdst) = time.tzname
        if axes[i] == 2:
            if ax2 == None:
                ax2 = ax1.twinx()
            ax = ax2
            if not opts.xaxis:
                ax2.xaxis.set_major_locator(locator)
                ax2.xaxis.set_major_formatter(formatter)
            label = fields[i]
            if label.endswith(":2"):
                label = label[:-2]
            ax2_labels.append(label)
        else:
            ax1_labels.append(fields[i])
            ax = ax1
        if opts.xaxis:
            if opts.marker is not None:
                marker = opts.marker
            else:
                marker = '+'
            if opts.linestyle is not None:
                linestyle = opts.linestyle
            else:
                linestyle = 'None'
            ax.plot(x[i], y[i], color=color, label=fields[i],
                    linestyle=linestyle, marker=marker)
        else:
            if opts.marker is not None:
                marker = opts.marker
            else:
                marker = 'None'
            if opts.linestyle is not None:
                linestyle = opts.linestyle
            else:
                linestyle = '-'
            ax.plot_date(x[i], y[i], color=color, label=fields[i],
                         linestyle=linestyle, marker=marker, tz=None)
        pylab.draw()
        empty = False
    if opts.flightmode is not None:
        for i in range(len(modes)-1):
            c = colourmap[opts.flightmode].get(modes[i][1], edge_colour) 
            ax1.axvspan(modes[i][0], modes[i+1][0], fc=c, ec=edge_colour, alpha=0.1)
        c = colourmap[opts.flightmode].get(modes[-1][1], edge_colour)
        ax1.axvspan(modes[-1][0], ax1.get_xlim()[1], fc=c, ec=edge_colour, alpha=0.1)
    if ax1_labels != []:
        ax1.legend(ax1_labels,loc=opts.legend)
    if ax2_labels != []:
        ax2.legend(ax2_labels,loc=opts.legend2)
    if empty:
        print("No data to graph")
        return


from optparse import OptionParser
parser = OptionParser("mavgraph.py [options] <filename> <fields>")

parser.add_option("--no-timestamps",dest="notimestamps", action='store_true', help="Log doesn't have timestamps")
parser.add_option("--planner",dest="planner", action='store_true', help="use planner file format")
parser.add_option("--condition",dest="condition", default=None, help="select packets by a condition")
parser.add_option("--labels",dest="labels", default=None, help="comma separated field labels")
parser.add_option("--legend",  default='upper left', help="default legend position")
parser.add_option("--legend2",  default='upper right', help="default legend2 position")
parser.add_option("--marker",  default=None, help="point marker")
parser.add_option("--linestyle",  default=None, help="line style")
parser.add_option("--xaxis",  default=None, help="X axis expression")
parser.add_option("--zero-time-base",  action='store_true', help="use Z time base for DF logs")
parser.add_option("--flightmode", default=None,
                    help="Choose the plot background according to the active flight mode of the specified type, e.g. --flightmode=apm for ArduPilot or --flightmode=px4 for PX4 stack logs.  Cannot be specified with --xaxis.")
(opts, args) = parser.parse_args()

from pymavlink import mavutil

if len(args) < 2:
    print("Usage: mavlogdump.py [options] <LOGFILES...> <fields...>")
    sys.exit(1)

if opts.flightmode is not None and opts.xaxis:
    print("Cannot request flightmode backgrounds with an x-axis expression")
    sys.exit(1)

if opts.flightmode is not None and opts.flightmode not in colourmap:
    print("Unknown flight controller '%s' in specification of --flightmode" % opts.flightmode)
    sys.exit(1)

filenames = []
fields = []
for f in args:
    if os.path.exists(f):
        filenames.append(f)
    else:
        fields.append(f)
msg_types = set()
multiplier = []
field_types = []

colors = [ 'red', 'green', 'blue', 'orange', 'olive', 'black', 'grey', 'yellow' ]

# work out msg types we are interested in
x = []
y = []
modes = []
axes = []
first_only = []
re_caps = re.compile('[A-Z_][A-Z0-9_]+')
for f in fields:
    caps = set(re.findall(re_caps, f))
    msg_types = msg_types.union(caps)
    field_types.append(caps)
    y.append([])
    x.append([])
    axes.append(1)
    first_only.append(False)

def add_data(t, msg, vars, flightmode):
    '''add some data'''
    mtype = msg.get_type()
    if opts.flightmode is not None and (len(modes) == 0 or modes[-1][1] != flightmode):
        modes.append((t, flightmode))
    if mtype not in msg_types:
        return
    for i in range(0, len(fields)):
        if mtype not in field_types[i]:
            continue
        f = fields[i]
        if f.endswith(":2"):
            axes[i] = 2
            f = f[:-2]
        if f.endswith(":1"):
            first_only[i] = True
            f = f[:-2]
        v = mavutil.evaluate_expression(f, vars)
        if v is None:
            continue
        if opts.xaxis is None:
            xv = t
        else:
            xv = mavutil.evaluate_expression(opts.xaxis, vars)
            if xv is None:
                continue
        y[i].append(v)            
        x[i].append(xv)

def process_file(filename):
    '''process one file'''
    print("Processing %s" % filename)
    mlog = mavutil.mavlink_connection(filename, notimestamps=opts.notimestamps, zero_time_base=opts.zero_time_base)
    vars = {}
    
    while True:
        msg = mlog.recv_match(opts.condition)
        if msg is None: break
        tdays = matplotlib.dates.date2num(datetime.datetime.fromtimestamp(msg._timestamp))
        add_data(tdays, msg, mlog.messages, mlog.flightmode)

if len(filenames) == 0:
    print("No files to process")
    sys.exit(1)

if opts.labels is not None:
    labels = opts.labels.split(',')
    if len(labels) != len(fields)*len(filenames):
        print("Number of labels (%u) must match number of fields (%u)" % (
            len(labels), len(fields)*len(filenames)))
        sys.exit(1)
else:
    labels = None

for fi in range(0, len(filenames)):
    f = filenames[fi]
    process_file(f)
    for i in range(0, len(x)):
        if first_only[i] and fi != 0:
            x[i] = []
            y[i] = []
    if labels:
        lab = labels[fi*len(fields):(fi+1)*len(fields)]
    else:
        lab = fields[:]
    plotit(x, y, lab, colors=colors[fi*len(fields):])
    for i in range(0, len(x)):
        x[i] = []
        y[i] = []
pylab.show()
pylab.draw()
raw_input('press enter to exit....')

########NEW FILE########
__FILENAME__ = mavkml
#!/usr/bin/env python

'''
simple kml export for logfiles
Thomas Gubler <thomasgubler@gmail.com>
'''

from optparse import OptionParser
import simplekml
from pymavlink.mavextra import *
from pymavlink import mavutil
import time
import re

mainstate_field = 'STAT.MainState'
position_field_types = ['Lon', 'Lat', 'Alt'] #kml order is lon, lat

colors = [simplekml.Color.red, simplekml.Color.green, simplekml.Color.blue, simplekml.Color.violet]

kml = simplekml.Kml()
kml_linestrings = []

def add_to_linestring(position_data, kml_linestring):
    '''add a point to the kml file'''
    global kml

    #add altitude offset
    position_data[2] += float(opts.aoff)
    kml_linestring.coords.addcoordinates([position_data])
    
def save_kml(filename):
    '''saves the kml file'''
    global kml
    kml.save(filename)
    print("KML written to %s" % filename)

def add_data(t, msg, vars, fields, field_types):
    '''add some data'''
        
    mtype = msg.get_type()
    if mtype not in msg_types:
        return
    
    for i in range(0, len(fields)):
        if mtype not in field_types[i]:
            continue
        f = fields[i]
        v = mavutil.evaluate_expression(f, vars)
        if v is None:
            continue
        
        # Check if we have position or state information
        if f == mainstate_field:
            # Handle main state information
            if v != add_data.mainstate_current and add_data.mainstate_current >= 0: # add_data.mainstate_current >= 0 : avoid starting a new linestring when mainstate comes after the first position data in the log
                add_data.new_linestring = True
            add_data.mainstate_current = v
        else:
            # Handle position information
            add_data.position_data[i] = v # make sure lon, lat, alt is saved in the correct order in position_data (the same as in position_field_types)
    
    #check if we have a full gps measurement
    gps_measurement_ready = True;
    for v in add_data.position_data:
        if v == None:
            gps_measurement_ready = False
            
    if gps_measurement_ready:
        #if new line string is needed (because of state change): add previous linestring to kml_linestrings list, add a new linestring to the kml multigeometry and append to the new linestring
        #else: append to current linestring
        if add_data.new_linestring:
            if add_data.current_kml_linestring != None:
                kml_linestrings.append(add_data.current_kml_linestring)
            
            add_data.current_kml_linestring = kml.newlinestring(name=opts.source  + ":" + str(add_data.mainstate_current), altitudemode='absolute')
            
            #set rendering options
            if opts.extrude:
                add_data.current_kml_linestring.extrude = 1
            add_data.current_kml_linestring.style.linestyle.color =  colors[max([add_data.mainstate_current, 0])]
            
            add_data.new_linestring = False
        
        add_to_linestring(add_data.position_data, add_data.current_kml_linestring)
        
        #reset position_data
        add_data.position_data = [None for n in position_field_types] 
        
            

def process_file(filename, fields, field_types):
    '''process one file'''
    print("Processing %s" % filename)
    mlog = mavutil.mavlink_connection(filename, notimestamps=opts.notimestamps)
    vars = {}
    position_data = [None for n in position_field_types]
    mainstate_current = -1
    add_data.new_linestring = True
    add_data.mainstate_current = -1
    add_data.current_kml_linestring = None
    add_data.position_data = [None for n in position_field_types]
    
    while True:
        msg = mlog.recv_match(opts.condition)
        if msg is None: break
        tdays = (msg._timestamp - time.timezone) / (24 * 60 * 60)
        tdays += 719163 # pylab wants it since 0001-01-01
        add_data(tdays, msg, mlog.messages, fields, field_types)

if __name__ == '__main__':
    parser = OptionParser("mavkml.py [options] <filename>")
    parser.add_option("--no-timestamps",dest="notimestamps", action='store_true', help="Log doesn't have timestamps")
    parser.add_option("--condition",dest="condition", default=None, help="select packets by a condition [default: %default]")
    parser.add_option("--aoff",dest="aoff", default=0., help="Altitude offset for paths that go through the ground in google earth [default: %default]")
    parser.add_option("-o", "--output",dest="filename_out", default="mav.kml", help="Output filename [default: %default] ")
    parser.add_option("-s", "--source", dest="source", default="GPOS", help="Select position data source (GPOS or GPS) [default: %default]")
    parser.add_option("-e", "--extrude", dest="extrude", default=False, action='store_true', help="Extrude paths to ground [default: %default]")
    
    
    (opts, args) = parser.parse_args()
        
    if len(args) < 1:
        print("Usage: mavkml.py <LOGFILES...>")
        sys.exit(1)
    
    filenames = []
    for f in args:
        if os.path.exists(f):
            filenames.append(f)
        
    #init fields and field_types lists
    fields = [opts.source + "." + s for s in position_field_types]
    fields.append(mainstate_field)
    field_types = []
    
    msg_types = set()
    re_caps = re.compile('[A-Z_][A-Z0-9_]+')
    
    for f in fields:
        caps = set(re.findall(re_caps, f))
        msg_types = msg_types.union(caps)
        field_types.append(caps)
 
    if len(filenames) == 0:
        print("No files to process")
        sys.exit(1)
     
    for fi in range(0, len(filenames)):
        f = filenames[fi]
        process_file(f, fields, field_types)
    
    save_kml(opts.filename_out)
########NEW FILE########
__FILENAME__ = mavlogdump
#!/usr/bin/env python

'''
example program that dumps a Mavlink log file. The log file is
assumed to be in the format that qgroundcontrol uses, which consists
of a series of MAVLink packets, each with a 64 bit timestamp
header. The timestamp is in microseconds since 1970 (unix epoch)
'''

import sys, time, os, struct, json

from optparse import OptionParser
parser = OptionParser("mavlogdump.py [options] <LOGFILE>")

parser.add_option("--no-timestamps",dest="notimestamps", action='store_true', help="Log doesn't have timestamps")
parser.add_option("--planner",dest="planner", action='store_true', help="use planner file format")
parser.add_option("--robust",dest="robust", action='store_true', help="Enable robust parsing (skip over bad data)")
parser.add_option("-f", "--follow",dest="follow", action='store_true', help="keep waiting for more data at end of file")
parser.add_option("--condition",dest="condition", default=None, help="select packets by condition")
parser.add_option("-q", "--quiet", dest="quiet", action='store_true', help="don't display packets")
parser.add_option("-o", "--output", default=None, help="output matching packets to give file")
parser.add_option("-p", "--parms",  action='store_true', help="preserve parameters in output with -o")
parser.add_option("--format", dest="format", default=None, help="Change the output format between 'standard', 'json', and 'csv'. For the CSV output, you must supply types that you want.")
parser.add_option("--csv_sep", dest="csv_sep", default=",", help="Select the delimiter between columns for the output CSV file. Use 'tab' to specify tabs. Only applies when --format=csv")
parser.add_option("--types",  default=None, help="types of messages (comma separated)")
parser.add_option("--dialect",  default="ardupilotmega", help="MAVLink dialect")
parser.add_option("--zero-time-base",  action='store_true', help="use Z time base for DF logs")
(opts, args) = parser.parse_args()

import inspect

from pymavlink import mavutil


if len(args) < 1:
    parser.print_help()
    sys.exit(1)

filename = args[0]
mlog = mavutil.mavlink_connection(filename, planner_format=opts.planner,
                                  notimestamps=opts.notimestamps,
                                  robust_parsing=opts.robust,
                                  dialect=opts.dialect,
                                  zero_time_base=opts.zero_time_base)

output = None
if opts.output:
    output = open(opts.output, mode='wb')

types = opts.types
if types is not None:
    types = types.split(',')

ext = os.path.splitext(filename)[1]
isbin = ext in ['.bin', '.BIN']
islog = ext in ['.log', '.LOG']

if opts.csv_sep == "tab":
    opts.csv_sep = "\t"

# Write out a header row as we're outputting in CSV format.
fields = ['timestamp']
offsets = {}
if opts.format == 'csv':
    try:
        currentOffset = 1 # Store how many fields in we are for each message.
        for type in types:
            try:
                typeClass = "MAVLink_{0}_message".format(type.lower())
                fields += [type + '.' + x for x in inspect.getargspec(getattr(mavutil.mavlink, typeClass).__init__).args[1:]]
                offsets[type] = currentOffset
                currentOffset += len(fields)
            except IndexError:
                quit()
    except TypeError:
        print("You must specify a list of message types if outputting CSV format via the --types argument.")
        exit()
    
    # The first line output are names for all columns
    print(','.join(fields))

# Track the last timestamp value. Used for compressing data for the CSV output format.
last_timestamp = None 

# Keep track of data from the current timestep. If the following timestep has the same data, it's stored in here as well. Output should therefore have entirely unique timesteps.
csv_out = ["" for x in fields]
while True:
    m = mlog.recv_match(blocking=opts.follow)
    if m is None:
        # FIXME: Make sure to output the last CSV message before dropping out of this loop
        break
    if output is not None:
        if (isbin or islog) and m.get_type() == "FMT":
            output.write(m.get_msgbuf())
            continue
        if (isbin or islog) and (m.get_type() == "PARM" and opts.parms):
            output.write(m.get_msgbuf())
            continue
        if m.get_type() == 'PARAM_VALUE' and opts.parms:
            timestamp = getattr(m, '_timestamp', None)
            output.write(struct.pack('>Q', timestamp*1.0e6) + m.get_msgbuf())
            continue
    if not mavutil.evaluate_condition(opts.condition, mlog.messages):
        continue

    if types is not None and m.get_type() not in types and m.get_type() != 'BAD_DATA':
        continue

    if m.get_type() == 'BAD_DATA' and m.reason == "Bad prefix":
        continue

    # Grab the timestamp.
    timestamp = getattr(m, '_timestamp', None)

    # If we're just logging, pack in the timestamp and data into the output file.
    if output:
        if not (isbin or islog):
            output.write(struct.pack('>Q', timestamp*1.0e6))
        output.write(m.get_msgbuf())

    # If quiet is specified, don't display output to the terminal.
    if opts.quiet:
        continue

    # If JSON was ordered, serve it up. Split it nicely into metadata and data.
    if opts.format == 'json':
        # Format our message as a Python dict, which gets us almost to proper JSON format
        data = m.to_dict()
        
        # Remove the mavpackettype value as we specify that later.
        del data['mavpackettype']
        
        # Also, if it's a BAD_DATA message, make it JSON-compatible by removing array objects
        if 'data' in data and type(data['data']) is not dict:
            data['data'] = list(data['data'])
        
        # Prepare the message as a single object with 'meta' and 'data' keys holding
        # the message's metadata and actual data respectively.
        outMsg = {"meta": {"msgId": m.get_msgId(), "type": m.get_type(), "timestamp": m._timestamp}, "data": data}
        
        # Now print out this object with stringified properly.
        print(json.dumps(outMsg))
    # CSV format outputs columnar data with a user-specified delimiter
    elif opts.format == 'csv':
        data = m.to_dict()
        type = m.get_type()

        # If this message has a duplicate timestamp, copy its data into the existing data list. Also
        # do this if it's the first message encountered.
        if timestamp == last_timestamp or last_timestamp is None:
            newData = [str(data[y.split('.')[-1]]) if y.split('.')[0] == type and y.split('.')[-1] in data else "" for y in [type + '.' + x for x in fields]]
            for i, val in enumerate(newData):
                if val:
                    csv_out[i] = val

        # Otherwise if this is a new timestamp, print out the old output data, and store the current message for later output.
        else:
            csv_out[0] = str(last_timestamp)
            print(opts.csv_sep.join(csv_out))
            csv_out = [str(data[y.split('.')[-1]]) if y.split('.')[0] == type and y.split('.')[-1] in data else "" for y in [type + '.' + x for x in fields]]
    # Otherwise we output in a standard Python dict-style format
    else:
        print("%s.%02u: %s" % (
            time.strftime("%Y-%m-%d %H:%M:%S",
                          time.localtime(timestamp)),
                          int(timestamp*100.0)%100, m))

    # Update our last timestamp value.
    last_timestamp = timestamp


########NEW FILE########
__FILENAME__ = mavloss
#!/usr/bin/env python

'''
show MAVLink packet loss
'''

import sys, time, os

from optparse import OptionParser
parser = OptionParser("sigloss.py [options]")
parser.add_option("--no-timestamps",dest="notimestamps", action='store_true', help="Log doesn't have timestamps")
parser.add_option("--planner",dest="planner", action='store_true', help="use planner file format")
parser.add_option("--robust",dest="robust", action='store_true', help="Enable robust parsing (skip over bad data)")
parser.add_option("--condition", default=None, help="condition for packets")

(opts, args) = parser.parse_args()

from pymavlink import mavutil

if len(args) < 1:
    print("Usage: mavloss.py [options] <LOGFILE...>")
    sys.exit(1)

def mavloss(logfile):
    '''work out signal loss times for a log file'''
    print("Processing log %s" % filename)
    mlog = mavutil.mavlink_connection(filename,
                                      planner_format=opts.planner,
                                      notimestamps=opts.notimestamps,
                                      robust_parsing=opts.robust)

    m = mlog.recv_match(condition=opts.condition)

    while True:
        m = mlog.recv_match()
        if m is None:
            break
    print("%u packets, %u lost %.1f%%" % (
            mlog.mav_count, mlog.mav_loss, mlog.packet_loss()))


total = 0.0
for filename in args:
    mavloss(filename)

########NEW FILE########
__FILENAME__ = mavmission
#!/usr/bin/env python

'''
extract mavlink mission from log
'''

import sys, time, os

from optparse import OptionParser
parser = OptionParser("mavmission.py [options]")
parser.add_option("--output", default='mission.txt', help="output file")

(opts, args) = parser.parse_args()

from pymavlink import mavutil, mavwp

if len(args) < 1:
    print("Usage: mavmission.py [options] <LOGFILE...>")
    sys.exit(1)

parms = {}

def mavmission(logfile):
    '''extract mavlink mission'''
    mlog = mavutil.mavlink_connection(filename)

    wp = mavwp.MAVWPLoader()

    while True:
        if mlog.mavlink10():
            m = mlog.recv_match(type='MISSION_ITEM')
        else:
            m = mlog.recv_match(type='WAYPOINT')
        if m is None:
            break
        wp.set(m, m.seq)
    wp.save(opts.output)
    print("Saved %u waypoints to %s" % (wp.count(), opts.output))


total = 0.0
for filename in args:
    mavmission(filename)

########NEW FILE########
__FILENAME__ = mavparmdiff
#!/usr/bin/env python
'''
compare two MAVLink parameter files
'''

import sys, os

from pymavlink import mavutil, mavparm

from optparse import OptionParser
parser = OptionParser("mavparmdiff.py [options]")
(opts, args) = parser.parse_args()

if len(args) < 2:
    print("Usage: mavparmdiff.py FILE1 FILE2")
    sys.exit(1)

file1 = args[0]
file2 = args[1]

p1 = mavparm.MAVParmDict()
p2 = mavparm.MAVParmDict()
p1.load(file2)
p1.diff(file1)


########NEW FILE########
__FILENAME__ = mavparms
#!/usr/bin/env python

'''
extract mavlink parameter values
'''

import sys, time, os

from optparse import OptionParser
parser = OptionParser("mavparms.py [options]")
parser.add_option("-c", "--changes", dest="changesOnly", default=False, action="store_true", help="Show only changes to parameters.")

(opts, args) = parser.parse_args()

from pymavlink import mavutil

if len(args) < 1:
    print("Usage: mavparms.py [options] <LOGFILE...>")
    sys.exit(1)

parms = {}

def mavparms(logfile):
    '''extract mavlink parameters'''
    mlog = mavutil.mavlink_connection(filename)

    while True:
        try:
            m = mlog.recv_match(type=['PARAM_VALUE', 'PARM'])
            if m is None:
                return
        except Exception:
            return
        if m.get_type() == 'PARAM_VALUE':
            pname = str(m.param_id).strip()
            value = m.param_value
        else:
            pname = m.Name
            value = m.Value
        if len(pname) > 0:
            if opts.changesOnly is True and pname in parms and parms[pname] != value:
                print("%s %-15s %.6f -> %.6f" % (time.asctime(time.localtime(m._timestamp)), pname, parms[pname], value))
            
            parms[pname] = value

total = 0.0
for filename in args:
    mavparms(filename)

if (opts.changesOnly is False):
    keys = parms.keys()
    keys.sort()
    for p in keys:
        print("%-15s %.6f" % (p, parms[p]))

########NEW FILE########
__FILENAME__ = mavplayback
#!/usr/bin/env python

'''
play back a mavlink log as a FlightGear FG NET stream, and as a
realtime mavlink stream

Useful for visualising flights
'''

import sys, time, os, struct
import Tkinter

from pymavlink import fgFDM

from optparse import OptionParser
parser = OptionParser("mavplayback.py [options]")

parser.add_option("--planner",dest="planner", action='store_true', help="use planner file format")
parser.add_option("--condition",dest="condition", default=None, help="select packets by condition")
parser.add_option("--gpsalt", action='store_true', default=False, help="Use GPS altitude")
parser.add_option("--mav10", action='store_true', default=False, help="Use MAVLink protocol 1.0")
parser.add_option("--out",   help="MAVLink output port (IP:port)",
                  action='append', default=['127.0.0.1:14550'])
parser.add_option("--fgout", action='append', default=['127.0.0.1:5503'],
                  help="flightgear FDM NET output (IP:port)")
parser.add_option("--baudrate", type='int', default=57600, help='baud rate')
(opts, args) = parser.parse_args()

if opts.mav10:
    os.environ['MAVLINK10'] = '1'
from pymavlink import mavutil

if len(args) < 1:
    parser.print_help()
    sys.exit(1)

filename = args[0]


def LoadImage(filename):
    '''return an image from the images/ directory'''
    app_dir = os.path.dirname(os.path.realpath(__file__))
    path = os.path.join(app_dir, 'images', filename)
    return Tkinter.PhotoImage(file=path)


class App():
    def __init__(self, filename):
        self.root = Tkinter.Tk()

        self.filesize = os.path.getsize(filename)
        self.filepos = 0.0

        self.mlog = mavutil.mavlink_connection(filename, planner_format=opts.planner,
                                               robust_parsing=True)
        self.mout = []
        for m in opts.out:
            self.mout.append(mavutil.mavlink_connection(m, input=False, baud=opts.baudrate))

        self.fgout = []
        for f in opts.fgout:
            self.fgout.append(mavutil.mavudp(f, input=False))
    
        self.fdm = fgFDM.fgFDM()

        self.msg = self.mlog.recv_match(condition=opts.condition)
        if self.msg is None:
            sys.exit(1)
        self.last_timestamp = getattr(self.msg, '_timestamp')

        self.paused = False

        self.topframe = Tkinter.Frame(self.root)
        self.topframe.pack(side=Tkinter.TOP)

        self.frame = Tkinter.Frame(self.root)
        self.frame.pack(side=Tkinter.LEFT)

        self.slider = Tkinter.Scale(self.topframe, from_=0, to=1.0, resolution=0.01,
                                    orient=Tkinter.HORIZONTAL, command=self.slew)
        self.slider.pack(side=Tkinter.LEFT)

        self.clock = Tkinter.Label(self.topframe,text="")
        self.clock.pack(side=Tkinter.RIGHT)

        self.playback = Tkinter.Spinbox(self.topframe, from_=0, to=20, increment=0.1, width=3)
        self.playback.pack(side=Tkinter.BOTTOM)
        self.playback.delete(0, "end")
        self.playback.insert(0, 1)

        self.buttons = {}
        self.button('quit', 'gtk-quit.gif', self.frame.quit)
        self.button('pause', 'media-playback-pause.gif', self.pause)
        self.button('rewind', 'media-seek-backward.gif', self.rewind)
        self.button('forward', 'media-seek-forward.gif', self.forward)
        self.button('status', 'Status', self.status)
        self.flightmode = Tkinter.Label(self.frame,text="")
        self.flightmode.pack(side=Tkinter.RIGHT)

        self.next_message()
        self.root.mainloop()

    def button(self, name, filename, command):
        '''add a button'''
        try:
            img = LoadImage(filename)
            b = Tkinter.Button(self.frame, image=img, command=command)
            b.image = img
        except Exception:
            b = Tkinter.Button(self.frame, text=filename, command=command)
        b.pack(side=Tkinter.LEFT)
        self.buttons[name] = b
        

    def pause(self):
        '''pause playback'''
        self.paused = not self.paused

    def rewind(self):
        '''rewind 10%'''
        pos = int(self.mlog.f.tell() - 0.1*self.filesize)
        if pos < 0:
            pos = 0
        self.mlog.f.seek(pos)
        self.find_message()

    def forward(self):
        '''forward 10%'''
        pos = int(self.mlog.f.tell() + 0.1*self.filesize)
        if pos > self.filesize:
            pos = self.filesize - 2048
        self.mlog.f.seek(pos)
        self.find_message()

    def status(self):
        '''show status'''
        for m in sorted(self.mlog.messages.keys()):
            print(str(self.mlog.messages[m]))
        


    def find_message(self):
        '''find the next valid message'''
        while True:
            self.msg = self.mlog.recv_match(condition=opts.condition)
            if self.msg is not None and self.msg.get_type() != 'BAD_DATA':
                break
            if self.mlog.f.tell() > self.filesize - 10:
                self.paused = True
                break
        self.last_timestamp = getattr(self.msg, '_timestamp')

    def slew(self, value):
        '''move to a given position in the file'''
        if float(value) != self.filepos:
            pos = float(value) * self.filesize
            self.mlog.f.seek(int(pos))
            self.find_message()


    def next_message(self):
        '''called as each msg is ready'''
        
        msg = self.msg
        if msg is None:
            self.paused = True

        if self.paused:
            self.root.after(100, self.next_message)
            return

        speed = float(self.playback.get())
        timestamp = getattr(msg, '_timestamp')

        now = time.strftime("%H:%M:%S", time.localtime(timestamp))
        self.clock.configure(text=now)

        if speed == 0.0:
            self.root.after(200, self.next_message)
        else:
            self.root.after(int(1000*(timestamp - self.last_timestamp) / speed), self.next_message)
        self.last_timestamp = timestamp

        while True:
            self.msg = self.mlog.recv_match(condition=opts.condition)
            if self.msg is None and self.mlog.f.tell() > self.filesize - 10:
                self.paused = True
                return
            if self.msg is not None and self.msg.get_type() != "BAD_DATA":
                break
        
        pos = float(self.mlog.f.tell()) / self.filesize
        self.slider.set(pos)
        self.filepos = self.slider.get()

        if msg.get_type() != "BAD_DATA":
            for m in self.mout:
                m.write(msg.get_msgbuf())

        if msg.get_type() == "GPS_RAW":
            self.fdm.set('latitude', msg.lat, units='degrees')
            self.fdm.set('longitude', msg.lon, units='degrees')
            if opts.gpsalt:
                self.fdm.set('altitude', msg.alt, units='meters')

        if msg.get_type() == "GPS_RAW_INT":
            self.fdm.set('latitude', msg.lat/1.0e7, units='degrees')
            self.fdm.set('longitude', msg.lon/1.0e7, units='degrees')
            if opts.gpsalt:
                self.fdm.set('altitude', msg.alt/1.0e3, units='meters')

        if msg.get_type() == "VFR_HUD":
            if not opts.gpsalt:
                self.fdm.set('altitude', msg.alt, units='meters')
            self.fdm.set('num_engines', 1)
            self.fdm.set('vcas', msg.airspeed, units='mps')

        if msg.get_type() == "ATTITUDE":
            self.fdm.set('phi', msg.roll, units='radians')
            self.fdm.set('theta', msg.pitch, units='radians')
            self.fdm.set('psi', msg.yaw, units='radians')
            self.fdm.set('phidot', msg.rollspeed, units='rps')
            self.fdm.set('thetadot', msg.pitchspeed, units='rps')
            self.fdm.set('psidot', msg.yawspeed, units='rps')

        if msg.get_type() == "RC_CHANNELS_SCALED":
            self.fdm.set("right_aileron", msg.chan1_scaled*0.0001)
            self.fdm.set("left_aileron", -msg.chan1_scaled*0.0001)
            self.fdm.set("rudder",        msg.chan4_scaled*0.0001)
            self.fdm.set("elevator",      msg.chan2_scaled*0.0001)
            self.fdm.set('rpm',           msg.chan3_scaled*0.01)

        if msg.get_type() == 'STATUSTEXT':
            print("APM: %s" % msg.text)

        if msg.get_type() == 'SYS_STATUS':
            self.flightmode.configure(text=self.mlog.flightmode)

        if msg.get_type() == "BAD_DATA":
            if mavutil.all_printable(msg.data):
                sys.stdout.write(msg.data)
                sys.stdout.flush()

        if self.fdm.get('latitude') != 0:
            for f in self.fgout:
                f.write(self.fdm.pack())


app=App(filename)

########NEW FILE########
__FILENAME__ = mavsearch
#!/usr/bin/env python

'''
search a set of log files for a condition
'''

import sys, time, os

from pymavlink import mavutil

from optparse import OptionParser
parser = OptionParser("mavsearch.py [options]")
parser.add_option("--condition", default=None, help="conditional check on log")
parser.add_option("--types", default=None, help="message types to look for (comma separated)")
parser.add_option("--stop", action='store_true', help="stop when message type found")
parser.add_option("--stopcondition", action='store_true', help="stop when condition met")

(opts, args) = parser.parse_args()

def mavsearch(filename):
    print("Loading %s ..." % filename)
    mlog = mavutil.mavlink_connection(filename)
    if opts.types is not None:
        types = opts.types.split(',')
    else:
        types = None
    while True:
        m = mlog.recv_match(type=types)
        if m is None:
            break
        if mlog.check_condition(opts.condition):
            print m
            if opts.stopcondition:
                break
        if opts.stop:
            break

if len(args) < 1:
    print("Usage: mavsearch.py [options] <LOGFILE...>")
    sys.exit(1)

for f in args:
    mavsearch(f)

########NEW FILE########
__FILENAME__ = mavsigloss
#!/usr/bin/env python

'''
show times when signal is lost
'''

import sys, time, os

from optparse import OptionParser
parser = OptionParser("sigloss.py [options]")
parser.add_option("--no-timestamps",dest="notimestamps", action='store_true', help="Log doesn't have timestamps")
parser.add_option("--planner",dest="planner", action='store_true', help="use planner file format")
parser.add_option("--robust",dest="robust", action='store_true', help="Enable robust parsing (skip over bad data)")
parser.add_option("--deltat", type='float', default=1.0, help="loss threshold in seconds")
parser.add_option("--condition",dest="condition", default=None, help="select packets by condition")
parser.add_option("--types",  default=None, help="types of messages (comma separated)")

(opts, args) = parser.parse_args()

from pymavlink import mavutil

if len(args) < 1:
    print("Usage: sigloss.py [options] <LOGFILE...>")
    sys.exit(1)

def sigloss(logfile):
    '''work out signal loss times for a log file'''
    print("Processing log %s" % filename)
    mlog = mavutil.mavlink_connection(filename,
                                      planner_format=opts.planner,
                                      notimestamps=opts.notimestamps,
                                      robust_parsing=opts.robust)

    last_t = 0

    types = opts.types
    if types is not None:
        types = types.split(',')

    while True:
        m = mlog.recv_match(condition=opts.condition)
        if m is None:
            return
        if types is not None and m.get_type() not in types:
            continue
        if opts.notimestamps:
            if not 'usec' in m._fieldnames:
                continue
            t = m.usec / 1.0e6
        else:
            t = m._timestamp
        if last_t != 0:
            if t - last_t > opts.deltat:
                print("Sig lost for %.1fs at %s" % (t-last_t, time.asctime(time.localtime(t))))
        last_t = t

total = 0.0
for filename in args:
    sigloss(filename)

########NEW FILE########
__FILENAME__ = mavtogpx
#!/usr/bin/env python

'''
example program to extract GPS data from a mavlink log, and create a GPX
file, for loading into google earth
'''

import sys, struct, time, os

from optparse import OptionParser
parser = OptionParser("mavtogpx.py [options]")
parser.add_option("--condition",dest="condition", default=None, help="select packets by a condition")
parser.add_option("--nofixcheck", default=False, action='store_true', help="don't check for GPS fix")
(opts, args) = parser.parse_args()

from pymavlink import mavutil

if len(args) < 1:
    print("Usage: mavtogpx.py <LOGFILE>")
    sys.exit(1)

def mav_to_gpx(infilename, outfilename):
    '''convert a mavlink log file to a GPX file'''

    mlog = mavutil.mavlink_connection(infilename)
    outf = open(outfilename, mode='w')

    def process_packet(timestamp, lat, lon, alt, hdg, v):
        t = time.localtime(timestamp)
        outf.write('''<trkpt lat="%s" lon="%s">
  <ele>%s</ele>
  <time>%s</time>
  <course>%s</course>
  <speed>%s</speed>
  <fix>3d</fix>
</trkpt>
''' % (lat, lon, alt,
       time.strftime("%Y-%m-%dT%H:%M:%SZ", t),
       hdg, v))

    def add_header():
        outf.write('''<?xml version="1.0" encoding="UTF-8"?>
<gpx
  version="1.0"
  creator="pymavlink"
  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
  xmlns="http://www.topografix.com/GPX/1/0"
  xsi:schemaLocation="http://www.topografix.com/GPX/1/0 http://www.topografix.com/GPX/1/0/gpx.xsd">
<trk>
<trkseg>
''')

    def add_footer():
        outf.write('''</trkseg>
</trk>
</gpx>
''')

    add_header()       

    count=0
    while True:
        m = mlog.recv_match(type=['GPS_RAW', 'GPS_RAW_INT'], condition=opts.condition)
        if m is None:
            break
        if m.get_type() == 'GPS_RAW_INT':
            lat = m.lat/1.0e7
            lon = m.lon/1.0e7
            alt = m.alt/1.0e3
            v = m.vel/100.0
            hdg = m.cog/100.0
            timestamp = m._timestamp
        else:
            lat = m.lat
            lon = m.lon
            alt = m.alt
            v = m.v
            hdg = m.hdg
            timestamp = m._timestamp

        if m.fix_type < 2 and not opts.nofixcheck:
            continue
        if m.lat == 0.0 or m.lon == 0.0:
            continue
        process_packet(timestamp, lat, lon, alt, hdg, v)
        count += 1
    add_footer()
    print("Created %s with %u points" % (outfilename, count))
    

for infilename in args:
    outfilename = infilename + '.gpx'
    mav_to_gpx(infilename, outfilename)

########NEW FILE########
__FILENAME__ = mavtomfile
#!/usr/bin/env python

'''
convert a MAVLink tlog file to a MATLab mfile
'''

import sys, os
import re
from pymavlink import mavutil

def process_tlog(filename):
    '''convert a tlog to a .m file'''

    print("Processing %s" % filename)
    
    mlog = mavutil.mavlink_connection(filename, dialect=opts.dialect, zero_time_base=True)
    
    # first walk the entire file, grabbing all messages into a hash of lists,
    #and the first message of each type into a hash
    msg_types = {}
    msg_lists = {}

    types = opts.types
    if types is not None:
        types = types.split(',')

    # note that Octave doesn't like any extra '.', '*', '-', characters in the filename
    (head, tail) = os.path.split(filename)
    basename = '.'.join(tail.split('.')[:-1])
    mfilename = re.sub('[\.\-\+\*]','_', basename) + '.m'
    # Octave also doesn't like files that don't start with a letter
    if (re.match('^[a-zA-z]', mfilename) == None):
        mfilename = 'm_' + mfilename

    if head is not None:
        mfilename = os.path.join(head, mfilename)
    print("Creating %s" % mfilename)

    f = open(mfilename, "w")

    type_counters = {}

    while True:
        m = mlog.recv_match(condition=opts.condition)
        if m is None:
            break

        if types is not None and m.get_type() not in types:
            continue
        if m.get_type() == 'BAD_DATA':
            continue
        
        fieldnames = m._fieldnames
        mtype = m.get_type()
        if mtype in ['FMT', 'PARM']:
            continue

        if mtype not in type_counters:
            type_counters[mtype] = 0
            f.write("%s.heading = {'timestamp'" % mtype)
            for field in fieldnames:
                val = getattr(m, field)
                if not isinstance(val, str):
                    f.write(",'%s'" % field)
            f.write("};\n")

        type_counters[mtype] += 1
        f.write("%s.data(%u,:) = [%f" % (mtype, type_counters[mtype], m._timestamp))
        for field in m._fieldnames:
            val = getattr(m, field)
            if not isinstance(val, str):
                f.write(",%f" % val)
        f.write("];\n")
    f.close()

from optparse import OptionParser
parser = OptionParser("mavtomfile.py [options]")

parser.add_option("--condition",dest="condition", default=None, help="select packets by condition")
parser.add_option("-o", "--output", default=None, help="output filename")
parser.add_option("--types",  default=None, help="types of messages (comma separated)")
parser.add_option("--dialect",  default="ardupilotmega", help="MAVLink dialect")
(opts, args) = parser.parse_args()

if len(args) < 1:
    print("Usage: mavtomfile.py [options] <LOGFILE>")
    sys.exit(1)

for filename in args:
    process_tlog(filename)

########NEW FILE########
__FILENAME__ = python_array_test_recv
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from pymavlink import mavutil

master = mavutil.mavlink_connection("udp::14555", dialect="array_test")

while True:
    m = master.recv_msg()
    if m is not None:
        print m

########NEW FILE########
__FILENAME__ = python_array_test_send
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time
from pymavlink import mavutil

master = mavutil.mavlink_connection("udp::14555", input=False, dialect="array_test")
while True:
    master.mav.system_time_send(1,2)
    master.mav.array_test_0_send(1, [-3, -2, -1, 0], [1,2,3,4], [5,6,7,8], [9,10,11,12])
    master.mav.array_test_1_send([1,2,3,4])
    master.mav.array_test_3_send(1, [2,3,4,5])
    master.mav.array_test_4_send([1,2,3,4], 5)
    master.mav.array_test_5_send("test1", "test2")
    master.mav.array_test_6_send(1,2,3, [4,5], [6,7], [8,9], [10,11], [12,13], [14,15], "long value", [1.1, 2.2], [3.3, 4.4])
    master.mav.array_test_7_send([1.1, 2.2], [3.3, 4.4],
            [4,5], [6,7], [8,9], [10,11], [12,13], [14,15], "long value")
    master.mav.array_test_8_send(1, [2.2, 3.3], [14,15])
    time.sleep(1)

master.close()


########NEW FILE########
