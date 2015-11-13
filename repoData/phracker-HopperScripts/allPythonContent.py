__FILENAME__ = Add CFString Inline Comments
# Go through CFString section, and add inline comments to any uses of those strings with the contents of the string
# This is only really needed on ARM.  It seems to happen already on x64
# bradenthomas@me.com

import struct,sys

# configuration parameters, adjust as needed:
ENDIANNESS = "<" # Little endian = <, Big endian = >

# helper methods
def read_data(segment, addr, dlen):
    if segment == None:
        segment = doc.getSegmentAtAddress(addr)
    return "".join([chr(segment.readByte(addr+x)) for x in range(0,dlen)])

# first, find the CFString segment
doc = Document.getCurrentDocument()
cfstring_seg = None
for seg_idx in range(0,doc.getSegmentCount()):
    cur_seg = doc.getSegment(seg_idx)
    if cur_seg.getName() == "__cfstring":
        cfstring_seg = cur_seg
        break
if not cfstring_seg:
    raise Exception("No CFString segment found")

# Run though CFStrings
ptr_size = 4
if doc.is64Bits():
    ptr_size = 8
for addr in xrange(cfstring_seg.getStartingAddress(), cfstring_seg.getStartingAddress()+cfstring_seg.getLength(), ptr_size*4):
    if doc.is64Bits():
        cstr_ptr, = struct.unpack(ENDIANNESS+"Q", read_data(cfstring_seg, addr + ptr_size*2, ptr_size))
    else:
        cstr_ptr, = struct.unpack(ENDIANNESS+"I", read_data(cfstring_seg, addr + ptr_size*2, ptr_size))
    if doc.is64Bits():
        cstr_len, = struct.unpack(ENDIANNESS+"Q", read_data(cfstring_seg, addr + ptr_size*3, ptr_size))
    else:
        cstr_len, = struct.unpack(ENDIANNESS+"I", read_data(cfstring_seg, addr + ptr_size*3, ptr_size))

    for xref in cfstring_seg.getReferencesOfAddress(addr):
        xref_seg = doc.getSegmentAtAddress(xref)
        existing_inline_comment = xref_seg.getInlineCommentAtAddress(xref)
        if existing_inline_comment == None or existing_inline_comment.startswith("0x"):
            cstr_data = str(read_data(None, cstr_ptr, cstr_len))
            doc.log("Set inline comment at 0x%x: %s"%(xref, cstr_data))
            xref_seg.setInlineCommentAtAddress(xref, "@\"%s\""%cstr_data)
########NEW FILE########
__FILENAME__ = Address To Clipboard
######### Copy Highlighted Address to Clipboard #########
import os
doc = Document.getCurrentDocument()
adr = doc.getCurrentAddress()
os.system("echo '%X' | tr -d '\n' | pbcopy" % adr)

########NEW FILE########
__FILENAME__ = Comment String XREFs
#
# Add a comment at every XREF to a string (from the __cstring segment).
# This only seems to be necessary on ARM.
#
# Samuel Groß <dev@samuel-gross.de> - github.com/saelo
#

def readString(addr):
    """Read and return a string at the given address"""
    seg = Document.getCurrentDocument().getSegmentAtAddress(addr)
    string = ""
    while not seg.readByte(addr) == 0:
        string += chr(seg.readByte(addr))
        addr += 1
    return string


doc = Document.getCurrentDocument()

# find __cstring segment
stringSegment = None
for i in range(doc.getSegmentCount()):
    cur = doc.getSegment(i)
    if cur.getName() == '__cstring':
        stringSegment = cur
        break
if not stringSegment:
    doc.log("No cstring section found!")
    raise Exception("No cstring segment found!")

# find all strings
for addr in range(stringSegment.getStartingAddress(), stringSegment.getStartingAddress() + stringSegment.getLength()):
    if stringSegment.getTypeAtAddress(addr) == Segment.TYPE_ASCII:
        string = readString(addr)

        xrefs = stringSegment.getReferencesOfAddress(addr)
        # if there are no XREFs the above method apparently
        # returns "None" instead of an empty list...
        if xrefs:
            for xref in xrefs:
                xrefSegment = doc.getSegmentAtAddress(xref)
                comment = xrefSegment.getInlineCommentAtAddress(xref)
                if comment is None or comment.startswith('0x'):
                    xrefSegment.setInlineCommentAtAddress(xref,
                            '"%s"%s @0x%x' % (string[:100], '..' if len(string) > 100 else '', addr))

        addr += len(string)

########NEW FILE########
__FILENAME__ = Copy Hexadecimal
######### Copy Highlighted Hexadecimal to Clipboard #########
import os
doc = Document.getCurrentDocument()
seg = doc.getCurrentSegment()
adr = doc.getCurrentAddress()
instr = seg.getInstructionAtAddress(adr)
len = instr.getInstructionLength()
hex = ""
for j in range(0, len):
   hex += str("%02X" % seg.readByte(adr + j))
os.system("echo '%s' | tr -d '\n' | pbcopy" % hex)

########NEW FILE########
__FILENAME__ = Create Procedures ARM
# Based off of the Create Procedures sample script, but for ARM
# bradenthomas@me.com

import struct,sys

# configuration parameters, adjust as needed:
ENDIANNESS = "<" # Little endian = <, Big endian = >

# helper methods
def read_data(segment, addr, dlen):
    return "".join([chr(segment.readByte(addr+x)) for x in range(0,dlen)])

# First, we disassemble the whole segment
doc = Document.getCurrentDocument()
seg = doc.getCurrentSegment()
if not seg:
    raise Exception("No segment selected")
seg.disassembleWholeSegment()

# Get segment starting address
addr = seg.getStartingAddress()
last = addr + seg.getLength()
while addr < last:
    # Find the next unexplored area
    addr=seg.getNextAddressWithType(addr,Segment.TYPE_CODE)
    if addr == Segment.BAD_ADDRESS:
        break

    # Copy a 16-bit value to see if it is in thumb mode
    try:
        halfword_value, = struct.unpack(ENDIANNESS+"H", read_data(seg, addr, 2))
    except:
        continue

    # Look for the push in thumb mode
    if halfword_value & 0xff00 == 0xb500: # PUSH (A7.1.50) with link register in the list.  Will not find every procedure, but low on false positives
        seg.markAsProcedure(addr)
    else:
        # Look for push in ARM mode
        try:
            word_value, = struct.unpack(ENDIANNESS+"I", read_data(seg, addr, 4))
        except:
            continue
        if word_value & 0xffffff00 == 0xe92d4000: # PUSH with link register in list, as above
            seg.markAsProcedure(addr)

    addr += 2
########NEW FILE########
__FILENAME__ = Demangle Strings
doc = Document.getCurrentDocument()
seg = doc.getCurrentSegment()
adr = seg.getStartingAddress()
last = adr + seg.getLength()

PIC = 0

#Loop through the whole code segment
#if you want to do a single proceedure
#it should be trivial to add in
while adr < last:
  instr = seg.getInstructionAtAddress(adr)
  #If the instruction sets the PIC Register value in a register
  if instr.getInstructionString() == "mov":
    register = instr.getFormattedArgument(0)
    value = instr.getFormattedArgument(1)
    if value.endswith("+_PIC_register_"):
      adr += instr.getInstructionLength()
      instr = seg.getInstructionAtAddress(adr)
      value = instr.getFormattedArgument(1)
      #And if it uses the newly set register in the next insturction
      if register in value:
        register += "+"
        value = value.replace(register,"")
        if value.startswith("0x"):
          offset = int(value, 0)
          offset = offset+PIC
          #Extract the comment
          segment = doc.getSegmentAtAddress(offset)
          comment = "\""
          while segment.readByte(offset) != 0:
            comment += chr(segment.readByte(offset))
            offset += 1
          comment += "\" at " + hex(offset)
          #Set it
          seg.setInlineCommentAtAddress(adr, comment)
          doc.log("[0x%X] Found calculated address of string %s" % (adr, comment))
  #if we call the address of the next instruction
  else:
    if instr.getInstructionString() == "call":
      value = instr.getFormattedArgument(0)
      if value.startswith("0x"):
        callTo = int(value, 0)
        adr += instr.getInstructionLength()
        #And if te call was to the next address, which was a pop
        if callTo == adr:
          instr = seg.getInstructionAtAddress(adr)
          if instr.getInstructionString() == "pop":
            #Reset our PIC
            PIC = callTo
  adr += instr.getInstructionLength()

########NEW FILE########
__FILENAME__ = Hopper GDB to GDB
# Hopper gdb script.  Effectively the same as the "HopperGDBServer" program that ships with Hopper, but works cross-platform
# Note that if you use this to debug a Linux process on another system, and you "override executable path", you may get an annoying error asking you select the file.
#      If you just hit cancel, it will continue to work anyway.
# bradenthomas@me.com

from twisted.internet import reactor,protocol,defer
import pybonjour,struct,socket,os,sys

HOPPER_GDB_PROTOCOL_VERSION = 1
VERBOSE = (os.getenv("VERBOSE") != None)

class HopperBonjour(object):
   def __init__(self, name, port):
      self.rsock = pybonjour.DNSServiceRegister(name=name, 
               regtype="_hopper._tcp",
               port=port,
               callBack=self.register_callback,
               domain="local.")
      reactor.addReader(self)
   def register_callback(self,sdRef,flags,err,name,regtype,domain):
      if err==pybonjour.kDNSServiceErr_NoError:
         print "Registered %s/%s/%s" % (name,regtype,domain)
   def logPrefix(self): return "HopperBonjour"
   def fileno(self): return self.rsock.fileno()
   def doRead(self): pybonjour.DNSServiceProcessResult(self.rsock)
   def connectionLost(self, reason): pass

class GDBProtocol(protocol.ProcessProtocol):
   def __init__(self, hopper):
      self.hopper = hopper
   def connectionMade(self):
      if VERBOSE: print "gdb connection made"
      self.hopper.gdbConnectionMade()
   def outReceived(self, data):
      if VERBOSE: print "GDB OUT RECEIVED",repr(data)
      self.hopper.transport.write(data)
   def errReceived(self, data):
      if VERBOSE: print "GDB ERR RECEIVED",repr(data)
      sys.stderr.write(data)
      sys.stderr.flush()
   def processExited(self, status):
      if VERBOSE: print "GDB EXIT",status
      self.hopper.transport.loseConnection()

class HopperProtocol(protocol.Protocol):
   def __init__(self, override_file, override_args):
      self.state = 0
      self.gdb = None
      self.override_file = override_file
      self.override_args = override_args
   def connectionMade(self):
      if VERBOSE: print "Connection made"
      self.transport.write("HopperGDBServer")
   def gdbConnectionMade(self):
      self.state = 4
      self.transport.write(chr(1))
   def modifyCommand(self, data):
      out = data
      try:
         (command_no, command_data) = data.split("-",1)
         if command_data.startswith("file-exec-file") and self.override_file:
            out = "%s-file-exec-file \"%s\"\n"%(command_no,self.override_file)
      except:
         pass
      if VERBOSE and out != data: print "MODIFIED",repr(out)
      return out
   def dataReceived(self, data):
      #if VERBOSE: print "Received",repr(data)
      if self.state == 0 and data == "Hopper":
         self.state = 1
         data = data[6:]
         self.transport.write(struct.pack("<H", HOPPER_GDB_PROTOCOL_VERSION))
      if self.state == 1 and len(data) >= 2:
         self.state = 2
         remote_version, = struct.unpack("<H", data[:2])
         data = data[2:]
         if remote_version != HOPPER_GDB_PROTOCOL_VERSION:
            if VERBOSE: print "Unsupported version",remote_version
            self.transport.loseConnection()
            return
      if self.state == 2 and len(data) > 0:
         self.gdb_arch = data.strip("\x00")
         self.state = 3
         data = ""
      if self.state == 3:
         if sys.platform == "darwin":
            launch_args = ["gdb", "--arch=%s"%self.gdb_arch, "--quiet", "--nx", "--interpreter=mi1"]
         else:
            launch_args = ["gdb", "--quiet", "--nx", "--interpreter=mi1"]
         if self.override_args and len(self.override_args):
            launch_args.extend(["--args", self.override_file]+self.override_args)
         elif self.override_file:
            launch_args.append(self.override_file)         
         if VERBOSE: print "Launch:",str(launch_args)
         self.gdb = GDBProtocol(self)
         reactor.spawnProcess(self.gdb, "/usr/bin/gdb", args=launch_args)
      if self.state == 4 and self.gdb != None:
         if VERBOSE: print "WRITE TO GDB",repr(data)
         data = self.modifyCommand(data)
         self.gdb.transport.write(data)


class HopperFactory(protocol.ServerFactory):
   protocol = HopperProtocol
   def __init__(self, override_file, override_args):
      self.override_file = override_file
      self.override_args = override_args
   def buildProtocol(self, addr):
      return self.protocol(self.override_file, self.override_args)

argc = len(sys.argv)-1
if argc == 1 and sys.argv[1] == "-h":
   print "Usage: hoppergdb_to_gdb.py [override executable path]"
   sys.exit(0)
override_file = None
override_args = []
if argc > 1 and os.path.exists(sys.argv[1]):
   override_file = sys.argv[1]
   override_args = sys.argv[1:]

p = reactor.listenTCP(0, HopperFactory(override_file, override_args))
HopperBonjour(socket.gethostname(), p.getHost().port)
reactor.run()
########NEW FILE########
__FILENAME__ = Insert NOP
#
# Written by Moloch
# v0.1
#
### Opcodes
nop_opcodes = {
    1: 0x90, # 1 i386
    2: 0x90, # 2 x86_64
    3: 0x0000a0e1, # 3 ARM
}

### Functions
def write_nop(adr, arch):
    doc.log("Writing NOP to 0x%08x" % adr)
    seg.writeByte(adr, nop_opcodes[arch])
    seg.markAsCode(adr)

def overwrite_instruction(adr):
    instr = seg.getInstructionAtAddress(adr)
    arch = instr.getArchitecture()
    if arch not in nop_opcodes:
        doc.log("Error: CPU Architecture not supported")
    else:
        arch_name = Instruction.stringForArchitecture(instr.getArchitecture())
        doc.log("--- Inserting %s opcodes ---" % arch_name)
        if arch != 3:  # Ignore ARM
            for index in range(instr.getInstructionLength()):
                write_nop(adr + index, arch)
### Main
doc = Document.getCurrentDocument()
seg = doc.getCurrentSegment()
adr = doc.getCurrentAddress()

resp = doc.message("What do you want to NOP?", [
    " Current Instruction (0x%08x) " % adr,
    " Alternate Address ",
    " Cancel "
])
if resp == 0:
    overwrite_instruction(adr)
elif resp == 1:
    user_adr = Document.ask("Enter alternate address:")
    if user_adr is not None:
        if user_adr.startswith("0x"):
            user_adr = user_adr[2:]
        user_adr = int(user_adr, 16)
        doc.log("New address is: 0x%08x" % user_adr)
        if user_adr is not None and user_adr != Segment.BAD_ADDRESS:
            overwrite_instruction(user_adr)
        else:
            doc.log("Error: Bad Address %s" % user_adr)
########NEW FILE########
__FILENAME__ = list-pe-exports
#!/usr/bin/python
import pefile
import sys
import os

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print >>sys.stderr, "Usage: %s DLL" % sys.argv[0]
        sys.exit(1)

    filename = sys.argv[1]
    if not os.path.exists(filename):
        print >>sys.stderr, "'%s' does not exist" % filename
        sys.exit(1)

    d = [pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_EXPORT"]]
    pe = pefile.PE(filename, fast_load=True)
    pe.parse_data_directories(directories=d)

    print "# %s exports for 'Ordinals to Names' Hopper Script" % os.path.basename(filename)
    print "# Ordinal        Name"

    exports = [(e.ordinal, e.name) for e in pe.DIRECTORY_ENTRY_EXPORT.symbols]
    for export in sorted(exports):
        print "imp_ordinal_%-4d imp_%s" % export

########NEW FILE########
__FILENAME__ = Make JMP unconditional
doc = Document.getCurrentDocument()
seg = doc.getCurrentSegment()
adr = doc.getCurrentAddress()
ins = seg.getInstructionAtAddress(adr)
arch = ins.getArchitecture()

if not arch in [1, 2]:
	doc.log('Unsupported arch!')
else:
	if not ins.isAConditionalJump():
		doc.log('Not a conditional jump!')
	else:
		b = seg.readByte(adr)
		if 0x70 <= b <= 0x7F:
			# rel8
			seg.writeByte(adr, 0xEB)
			seg.markAsCode(adr)
		elif b == 0x0F:
			b = seg.readByte(adr + 1)
			if 0x80 <= b <= 0x8F:
				# rel16/32
				seg.writeByte(adr, 0x90)
				seg.writeByte(adr + 1, 0xE9)
				seg.markAsCode(adr)
			else:
				doc.log('Unknown conditional jump!')
		else:
			doc.log('Unknown conditional jump!')

########NEW FILE########
__FILENAME__ = NOP Selection
######### NOP Selection #########
doc = Document.getCurrentDocument()
seg = doc.getCurrentSegment()
adr = doc.getCurrentAddress()
start, end = doc.getSelectionAddressRange()
for x in range(start,end):
  seg.writeByte(x,0x90)
  seg.markAsCode(x)

########NEW FILE########
__FILENAME__ = Ordinals to Names
import os
import re
import traceback

def get_hopper_script_dir():
    """Detect the Hopper script directory and return it if found"""

    dirs = [os.path.expanduser("~/.local/share/data/Hopper/scripts"),
            os.path.expandvars("%LOCALAPPDATA%/Hopper/scripts"),
            os.path.expanduser("~/Library/Application Support/Hopper/Scripts/HopperScripts")]
    for directory in dirs:
        if os.path.exists(directory):
            return directory
    return None

def find_import_before(doc, start_address, max_bytes=200):
    """Find the last import comment before an address, return the library name if found."""
    for adr in range(start_address, start_address - max_bytes, -1):
        lib = get_import_at(doc, adr)
        if lib:
            return lib
    return None

def get_import_at(doc, address):
    """Check the comment at address for a import library name and return it if found."""
    segment = doc.getSegmentAtAddress(address)
    if segment is not None:
        comment = segment.getCommentAtAddress(address)
        if comment.startswith("Imports from"):
            return comment[13:]
    return None

# Regular expression to match lines in our symbol files.
symbol_line = re.compile(r"^\s*(?:(\w+)\s+(\w+))?\s*([;#].*)?$")

def get_symbols(doc, lib):
    """Load symbols from library.txt and return them as a dictionary."""

    basename = lib.replace(".dll", "").lower()
    filename = os.path.join(get_hopper_script_dir(), basename + ".txt")
    if not os.path.exists(filename):
        doc.log("Symbol file not found: %s" % filename)
        return None

    symbols = {}
    with open(filename, "r") as fp:
        for i, line in enumerate(fp, 1):
            match = symbol_line.match(line)
            if not match:
                doc.log("Skipping line %d: Malformed" % i)
                continue

            ordinal, name = match.group(1), match.group(2)
            if ordinal and name:
                symbols[ordinal] = name

    return symbols

def main(doc):
    lower, upper = doc.getSelectionAddressRange()
    doc.log("Selection: %x - %x" % (lower, upper))

    # Hopper renames duplicate imports with their address, this regex matches those.
    imp_address = re.compile(r"(imp_ordinal_\d+)_[0-9a-f]+")

    # Find the last library name before the selection and load it's symbols.
    current_lib = find_import_before(doc, lower)
    if current_lib:
        doc.log("Loading symbols for %s" % current_lib)
        symbols = get_symbols(doc, current_lib)
    else:
        symbols = None

    for adr in range(lower, upper, 4):
        # See if this address has a comment indicating a library name.
        lib = get_import_at(doc, adr)
        if lib is not None and lib != current_lib:
            current_lib = lib
            doc.log("Loading symbols for %s" % current_lib)
            symbols = get_symbols(doc, current_lib)

        # If the current address indicates a name, and we have symbols,
        # see if we can replace it with a name from the symbol file.
        name = doc.getNameAtAddress(adr)
        if symbols and name is not None:
            # If the name ends with an address, strip that off.
            match = imp_address.match(name)
            if match: name = match.group(1)

            if name in symbols:
                doc.log("Renaming %s to %s" % (name, symbols[name]))
                doc.setNameAtAddress(adr, symbols[name])

    doc.log("Done")
    doc.refreshView()

doc = Document.getCurrentDocument()
try:
    main(doc)
except:
    # Exceptions seem to get lost in Hopper somewhere, so make sure we log a
    # traceback if anything goes wrong.
    doc.log("Unhandled Exception in Ordinals to Names")
    doc.log(traceback.format_exc())

########NEW FILE########
__FILENAME__ = Read Class Dump
# coding=utf-8
"""Reads output of class-dump to label procedures in Hopper"""

import ctypes
import ctypes.util
import os
import re
from subprocess import Popen, PIPE


def get_original_file_name(doc_obj_addr):
    """Read original path of the binary from private Hopper document.

    May cause crashes"""
    objc = ctypes.cdll.LoadLibrary(ctypes.util.find_library('objc'))
    objc.objc_getClass.restype = ctypes.c_void_p
    objc.sel_registerName.restype = ctypes.c_void_p
    objc.objc_msgSend.restype = ctypes.c_void_p
    objc.objc_msgSend.argtypes = [ctypes.c_void_p, ctypes.c_void_p]

    NSAutoreleasePool = objc.objc_getClass('NSAutoreleasePool')
    pool = objc.objc_msgSend(NSAutoreleasePool, objc.sel_registerName('alloc'))
    pool = objc.objc_msgSend(pool, objc.sel_registerName('init'))

    originalFilePath = ctypes.cast(
        objc.objc_msgSend(
            objc.objc_msgSend(
                objc.objc_msgSend(doc_obj_addr, objc.sel_registerName("disassembledFile")),
                objc.sel_registerName("originalFilePath")),
            objc.sel_registerName("UTF8String")),
        ctypes.c_char_p).value

    objc.objc_msgSend(pool, objc.sel_registerName('release'))
    return originalFilePath


def read_command(cmd, cwd=None, encoding='utf-8'):
    """Run shell command and read output.

    @param cmd: Command to be executed.
    @type cmd: string

    @param cwd: Working directory.
    @type cwd: string

    @param encoding: Encoding used to decode bytes returned by Popen into string.
    @type encoding: string

    @return: Output of the command: (<returncode>, <output>)
    @rtype: tuple"""
    p = Popen(cmd, shell=True, stdout=PIPE, cwd=cwd)
    output = p.communicate()[0]
    output = output.decode(encoding)
    return p.returncode, output


def read_class_dump(binary_path):
    """Read class dump (both class-dump and class-dump-z) and return list of lines.

    @param binary_path: Path to the binary for class-dump.
    @type binary_path: unicode

    @return: List of lines
    @rtype: list"""
    class_dump_path = None
    class_dump_z_path = None
    for prefix in os.getenv("PATH",os.defpath).split(os.pathsep) + ["/usr/local/bin", "/opt/bin"]:
        if os.path.exists(os.path.join(prefix, "class-dump")):
            class_dump_path = os.path.join(prefix, "class-dump")

        if os.path.exists(os.path.join(prefix, "class-dump-z")):
            class_dump_z_path = os.path.join(prefix, "class-dump-z")

    if not class_dump_path and not class_dump_z_path:
        doc.log("ERROR: Cannot find class-dump or class-dump-z")
        raise Exception("Missing class-dump")

    class_dump = []
    cwd = os.path.dirname(binary_path)

    if class_dump_path:
        returncode, output = read_command("{0} -a -A \"{1}\"".format(class_dump_path, binary_path), cwd)
        class_dump += output.splitlines()

    if class_dump_z_path:
        returncode, output = read_command("{0} -A \"{1}\"".format(class_dump_z_path, binary_path), cwd)
        class_dump += output.splitlines()

    return class_dump


def process(lines, doc):
    def on_method(address, name):
        doc.setNameAtAddress(address, name)
        if doc.getSegmentAtAddress(address) is not None:
            doc.getSegmentAtAddress(address).markAsProcedure(address)
            #doc.log("Method: {0} at 0x{1:x}".format(name, address))

    def on_ivar(address, name):
        segment = doc.getSegmentAtAddress(address)
        if segment is not None and segment.getName() == "__objc_ivar":
            doc.setNameAtAddress(address, name)
            #doc.log("Ivar: {0} at 0x{1:x} (2}".format(name), address, segment.getName())

    in_methods = False
    in_ivars = False
    interface_name = None

    for line in lines:
        line = line.strip()

        if not line:
            continue

        if line.startswith("@interface"):
            m = re.match("^@interface +(?P<name>.*):(?P<rest>.*)", line)
            if m is not None:
                interface_name = m.group('name').strip()
                in_ivars = True
                in_methods = False
                #doc.log(line)
        if line.startswith("@end"):
            in_methods = False
            in_ivars = False
        elif in_ivars and line.startswith("}"):
            in_ivars = False
            in_methods = True
        elif in_ivars:
            m = re.match("^(?P<type>.*(\*| ))(?P<name>[a-zA-Z].*);.*(?P<address>0[xX][0-9a-fA-F]+).*", line)
            if m is not None:
                ivar_type = m.group('type').strip()
                ivar_name = m.group('name').strip()
                ivar_address = int(m.group('address'), 16)
                ivar_info_name = "({0}) {1}.{2}".format(ivar_type, interface_name, ivar_name)
                on_ivar(ivar_address, ivar_info_name)
        elif in_methods:
            m = re.match("(?P<scope>^(\+|\-)) *\((?P<type>.*?)\) *(?P<signature>.*);.*(?P<address>0[xX][0-9a-fA-F]+).*", line)
            if m is not None:
                method_scope = m.group('scope')
                method_type = m.group('type').strip()
                method_signature = m.group('signature').strip()
                method_address = int(m.group('address'), 16)
                method_info_name = "{0} ({1}) [{2} {3}]".format(method_scope, method_type, interface_name, method_signature)
                on_method(method_address, method_info_name)
            else:
                m = re.match("^@property *(?P<attributes>\(.*?\))? *(?P<type>[a-zA-Z].*(\*| ))(?P<name>[a-zA-Z].*);(?P<rest>.*)", line)
                if m is not None:
                    property_attributes = m.group('attributes')
                    property_type = m.group('type').strip()
                    property_name = m.group('name').strip()
                    rest = m.group('rest')

                    m = re.match(".*G=(?P<getter>0[xX][0-9a-fA-F]+).*", rest)
                    if m is not None:
                        property_getter_address = int(m.group('getter'), 16)

                        m = re.match(".*getter=(?P<name>[a-zA-Z][a-zA-Z0-9]*).*", property_attributes)
                        if m is not None:
                            property_getter_name = m.group('name')
                        else:
                            property_getter_name = property_name

                        property_getter_info_name = "- ({0}) [{1} {2}]".format(property_type, interface_name, property_getter_name)
                        on_method(property_getter_address, property_getter_info_name)

                    m = re.match(".*S=(?P<setter>0[xX][0-9a-fA-F]+).*", rest)
                    if m is not None:
                        property_setter_address = int(m.group('setter'), 16)

                        m = re.match(".*setter=(?P<name>[a-zA-Z][a-zA-Z0-9]*).*", property_attributes)
                        if m is not None:
                            property_setter_name = m.group('name')
                        else:
                            property_setter_name = "set{0}".format(property_name[0].upper() + property_name[1:])

                        property_setter_info_name = "- (void) [{0} {1}]".format(interface_name, property_setter_name)
                        on_method(property_setter_address, property_setter_info_name)
                else:
                    doc.log("INFO: Unknown \"{0}\"".format(line))


doc = Document.getCurrentDocument()
binary_path = get_original_file_name(doc.__internal_document_addr__)
process(read_class_dump(binary_path), doc)
doc.refreshView()

########NEW FILE########
__FILENAME__ = Return False
######### Return False #########
bytes = [0xB8,0x00,0x00,0x00,0x00,0xC3]
doc = Document.getCurrentDocument()
seg = doc.getCurrentSegment()
adr = doc.getCurrentAddress()
i = seg.getInstructionAtAddress(adr)
for x in range(0, len(bytes)):
  seg.writeByte(adr + x, bytes[x])

########NEW FILE########
__FILENAME__ = Return True
######### Return True #########
bytes = [0xB8,0x01,0x00,0x00,0x00,0xC3]
doc = Document.getCurrentDocument()
seg = doc.getCurrentSegment()
adr = doc.getCurrentAddress()
i = seg.getInstructionAtAddress(adr)
for x in range(0, len(bytes)): seg.writeByte(adr + x, bytes[x])

########NEW FILE########
__FILENAME__ = To String
#
# Turn the current selection into an ASCII string.
#
# Samuel Groß <dev@samuel-gross.de> - github.com/saelo
#

doc = Document.getCurrentDocument()
seg = doc.getCurrentSegment()
start, end = doc.getSelectionAddressRange()
bytes = [seg.readByte(addr) for addr in range(start, end)]

# check if selection is a valid ASCII string
if not bytes[-1] == 0:
    doc.log("Selection must include terminating null character")
    raise Exception("Invalid selection")
# maybe not the best way but the following should work with python 2.x and 3.x
if not all(0x20 <= byte <= 0x7e or byte == 0x0a or byte == 0x0d for byte in bytes[:-1]):
    doc.log("Selection is not a valid ASCII string")
    raise Exception("Invalid selection")
string = "".join([chr(b) for b in bytes[:-1]])

# mark bytes as string
seg.setTypeAtAddress(start, end - start, Segment.TYPE_ASCII)

# add comments to the addresses where the string is referenced
xrefs = seg.getReferencesOfAddress(start)
if xrefs:
    for xref in xrefs:
        xrefSegment = doc.getSegmentAtAddress(xref)
        comment = xrefSegment.getInlineCommentAtAddress(xref)
        if comment is None or comment.startswith('0x'):
            xrefSegment.setInlineCommentAtAddress(xref,
                    '"%s"%s' % (string[:100], '..' if len(string) > 100 else ''))

########NEW FILE########
__FILENAME__ = WS2_32.dll Ordinals to Names
doc = Document.getCurrentDocument()

doc.log("# WS2_32.dll ordinals to names v1.0")
doc.log("# Author: @chort0")
doc.log("# Greetz: @abad1dea @bsr43")
doc.log("# Ord => Name mapping from http://www.winasm.net/forum/index.php?showtopic=2362")

ordinals = {'imp_ordinal_1' : 'imp_accept',
'imp_ordinal_2' : 'imp_bind',
'imp_ordinal_3' : 'imp_closesocket',
'imp_ordinal_4' : 'imp_connect',
'imp_ordinal_5' : 'imp_getpeername',
'imp_ordinal_6' : 'imp_getsockname',
'imp_ordinal_7' : 'imp_getsockopt',
'imp_ordinal_8' : 'imp_htonl',
'imp_ordinal_9' : 'imp_htons',
'imp_ordinal_10' : 'imp_ioctlsocket',
'imp_ordinal_11' : 'imp_inet_addr',
'imp_ordinal_12' : 'imp_inet_ntoa',
'imp_ordinal_13' : 'imp_listen',
'imp_ordinal_14' : 'imp_ntohl',
'imp_ordinal_15' : 'imp_ntohs',
'imp_ordinal_16' : 'imp_recv',
'imp_ordinal_17' : 'imp_recvfrom',
'imp_ordinal_18' : 'imp_select',
'imp_ordinal_19' : 'imp_send',
'imp_ordinal_20' : 'imp_sendto',
'imp_ordinal_21' : 'imp_setsockopt',
'imp_ordinal_22' : 'imp_shutdown',
'imp_ordinal_23' : 'imp_socket',
'imp_ordinal_24' : 'imp_GetAddrInfoW',
'imp_ordinal_25' : 'imp_GetNameInfoW',
'imp_ordinal_26' : 'imp_WSApSetPostRoutine',
'imp_ordinal_27' : 'imp_FreeAddrInfoW',
'imp_ordinal_28' : 'imp_WPUCompleteOverlappedRequest',
'imp_ordinal_29' : 'imp_WSAAccept',
'imp_ordinal_30' : 'imp_WSAAddressToStringA',
'imp_ordinal_31' : 'imp_WSAAddressToStringW',
'imp_ordinal_32' : 'imp_WSACloseEvent',
'imp_ordinal_33' : 'imp_WSAConnect',
'imp_ordinal_34' : 'imp_WSACreateEvent',
'imp_ordinal_35' : 'imp_WSADuplicateSocketA',
'imp_ordinal_36' : 'imp_WSADuplicateSocketW',
'imp_ordinal_37' : 'imp_WSAEnumNameSpaceProvidersA',
'imp_ordinal_38' : 'imp_WSAEnumNameSpaceProvidersW',
'imp_ordinal_39' : 'imp_WSAEnumNetworkEvents',
'imp_ordinal_40' : 'imp_WSAEnumProtocolsA',
'imp_ordinal_41' : 'imp_WSAEnumProtocolsW',
'imp_ordinal_42' : 'imp_WSAEventSelect',
'imp_ordinal_43' : 'imp_WSAGetOverlappedResult',
'imp_ordinal_44' : 'imp_WSAGetQOSByName',
'imp_ordinal_45' : 'imp_WSAGetServiceClassInfoA',
'imp_ordinal_46' : 'imp_WSAGetServiceClassInfoW',
'imp_ordinal_47' : 'imp_WSAGetServiceClassNameByClassIdA',
'imp_ordinal_48' : 'imp_WSAGetServiceClassNameByClassIdW',
'imp_ordinal_49' : 'imp_WSAHtonl',
'imp_ordinal_50' : 'imp_WSAHtons',
'imp_ordinal_51' : 'imp_gethostbyaddr',
'imp_ordinal_52' : 'imp_gethostbyname',
'imp_ordinal_53' : 'imp_getprotobyname',
'imp_ordinal_54' : 'imp_getprotobynumber',
'imp_ordinal_55' : 'imp_getservbyname',
'imp_ordinal_56' : 'imp_getservbyport',
'imp_ordinal_57' : 'imp_gethostname',
'imp_ordinal_58' : 'imp_WSAInstallServiceClassA',
'imp_ordinal_59' : 'imp_WSAInstallServiceClassW',
'imp_ordinal_60' : 'imp_WSAIoctl',
'imp_ordinal_61' : 'imp_WSAJoinLeaf',
'imp_ordinal_62' : 'imp_WSALookupServiceBeginA',
'imp_ordinal_63' : 'imp_WSALookupServiceBeginW',
'imp_ordinal_64' : 'imp_WSALookupServiceEnd',
'imp_ordinal_65' : 'imp_WSALookupServiceNextA',
'imp_ordinal_66' : 'imp_WSALookupServiceNextW',
'imp_ordinal_67' : 'imp_WSANSPIoctl',
'imp_ordinal_68' : 'imp_WSANtohl',
'imp_ordinal_69' : 'imp_WSANtohs',
'imp_ordinal_70' : 'imp_WSAProviderConfigChange',
'imp_ordinal_71' : 'imp_WSARecv',
'imp_ordinal_72' : 'imp_WSARecvDisconnect',
'imp_ordinal_73' : 'imp_WSARecvFrom',
'imp_ordinal_74' : 'imp_WSARemoveServiceClass',
'imp_ordinal_75' : 'imp_WSAResetEvent',
'imp_ordinal_76' : 'imp_WSASend',
'imp_ordinal_77' : 'imp_WSASendDisconnect',
'imp_ordinal_78' : 'imp_WSASendTo',
'imp_ordinal_79' : 'imp_WSASetEvent',
'imp_ordinal_80' : 'imp_WSASetServiceA',
'imp_ordinal_81' : 'imp_WSASetServiceW',
'imp_ordinal_82' : 'imp_WSASocketA',
'imp_ordinal_83' : 'imp_WSASocketW',
'imp_ordinal_84' : 'imp_WSAStringToAddressA',
'imp_ordinal_85' : 'imp_WSAStringToAddressW',
'imp_ordinal_86' : 'imp_WSAWaitForMultipleEvents',
'imp_ordinal_87' : 'imp_WSCDeinstallProvider',
'imp_ordinal_88' : 'imp_WSCEnableNSProvider',
'imp_ordinal_89' : 'imp_WSCEnumProtocols',
'imp_ordinal_90' : 'imp_WSCGetProviderPath',
'imp_ordinal_91' : 'imp_WSCInstallNameSpace',
'imp_ordinal_92' : 'imp_WSCInstallProvider',
'imp_ordinal_93' : 'imp_WSCUnInstallNameSpace',
'imp_ordinal_94' : 'imp_WSCUpdateProvider',
'imp_ordinal_95' : 'imp_WSCWriteNameSpaceOrder',
'imp_ordinal_96' : 'imp_WSCWriteProviderOrder',
'imp_ordinal_97' : 'imp_freeaddrinfo',
'imp_ordinal_98' : 'imp_getaddrinfo',
'imp_ordinal_99' : 'imp_getnameinfo',
'imp_ordinal_101' : 'imp_WSAAsyncSelect',
'imp_ordinal_102' : 'imp_WSAAsyncGetHostByAddr',
'imp_ordinal_103' : 'imp_WSAAsyncGetHostByName',
'imp_ordinal_104' : 'imp_WSAAsyncGetProtoByNumber',
'imp_ordinal_105' : 'imp_WSAAsyncGetProtoByName',
'imp_ordinal_106' : 'imp_WSAAsyncGetServByPort',
'imp_ordinal_107' : 'imp_WSAAsyncGetServByName',
'imp_ordinal_108' : 'imp_WSACancelAsyncRequest',
'imp_ordinal_109' : 'imp_WSASetBlockingHook',
'imp_ordinal_110' : 'imp_WSAUnhookBlockingHook',
'imp_ordinal_111' : 'imp_WSAGetLastError',
'imp_ordinal_112' : 'imp_WSASetLastError',
'imp_ordinal_113' : 'imp_WSACancelBlockingCall',
'imp_ordinal_114' : 'imp_WSAIsBlocking',
'imp_ordinal_115' : 'imp_WSAStartup',
'imp_ordinal_116' : 'imp_WSACleanup',
'imp_ordinal_151' : 'imp___WSAFDIsSet',
'imp_ordinal_500' : 'imp_WEP'
}
theRange = doc.getSelectionAddressRange()
lower = theRange[0]
upper = theRange[1]

doc.log("Renaming in range %s to %s" % (hex(lower), hex(upper)))

adr = lower
while adr <= upper:
	doc.log("Address: %d" % adr)
	name = doc.getNameAtAddress(adr)
	if name != None:
		doc.log("Name: %s" % name)
		newName = ordinals[name]
		if newName != None:
			doc.log("Renaming %s to %s" % (name, newName))
			doc.setNameAtAddress(adr, newName)
	adr = adr + 4
	name = ''
doc.log("# end of script")
doc.refreshView()
########NEW FILE########
