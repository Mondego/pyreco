__FILENAME__ = builder
#!/usr/bin/python

import codelibrary
import codeparameters
import outputter
import sys

def do_build(codename, inparams):
	params = { }

	# parse user args
	for keyval in inparams:
		if len(keyval.split("=")) == 2:
			(key, val) = keyval.split("=")
			params[key] = val

	if 'outformat' not in params:
		params['outformat'] = "c"

	codenames = codename.split(',')

	bincode = ''

	for curname in codenames:
		shellcode = codelibrary.get_by_name(curname)
		if "parameters" in shellcode:
			shellcode = codeparameters.handle_parameters(shellcode, params)

		bincode += outputter.hex_bin(shellcode['code'])


	outformat = params['outformat']
	sys.stdout.write(outputter.outfunc[ outformat ](bincode, fancy = True))

	if 'outfile' in params:
		rawoutput = outputter.outfunc[ outformat](bincode, fancy = False)
		f = open(params['outfile'], 'w')
		f.write(rawoutput)
		f.close()


def main(args):
	if len(args) < 1:
		print "usage: moneyshot build <shellcode_path> [params]"
	else:
		codelibrary.load_codes(sys.path[0] + "/codes")
		do_build(args[0], args[1:])

########NEW FILE########
__FILENAME__ = codelibrary
#!/usr/bin/env python

import colors
import json
import fnmatch
import os
import sys

codes = { }

def load_codes(dirname):
	global codes
	codes = load_codes_dir(dirname)

def load_codes_dir(dirname, depth = 0):
	shellcodes = { }

	entries = os.listdir(dirname)

	for entry in entries:
		if os.path.isdir(dirname + os.sep + entry):
			shellcodes[entry] = load_codes_dir(dirname + os.sep + entry, depth+1)
		else:
			basename, extension = os.path.splitext(entry)

			if extension == ".json":
				jstr = open(dirname + os.sep + entry).read()

				try:
					shellcodes[basename] = json.loads(jstr)

					# fixup multiline kodez
					shellcodes[basename]["code"] = ''.join(shellcodes[basename]["code"])
				except:
					print "Failed loading '%s/%s' :(" % (dirname, entry)
	
	return shellcodes

def find_codes(path = ''):
	global codes
	return_codes = codes

	if path == '' or path == '.':
		return return_codes

	for part in path.split(os.sep):
		if part in return_codes:
			if "description" in return_codes[part]:
				return False
			else:
				return_codes = return_codes[part]
		else:
			return False

	return return_codes

def get_by_name(path):
	global codes
	return_codes = codes

	for part in path.split(os.sep):
		if part in return_codes:
			if "description" in return_codes[part]:
				return return_codes[part]
			else:
				return_codes = return_codes[part]
		else:
			return False

def get_code_size(code_obj):
	return len(code_obj['code']) / 2


def print_codes(codes, depth = 0):
	for key in codes.keys():
		if "description" in codes[key]:
			second_col = "%s%4d%s bytes -- %s" % (colors.fg('green'), get_code_size(codes[key]), colors.end(), codes[key]['description'])
			print "  " * (depth+1) + key.ljust(40 - (depth*2)) + second_col
			
		else:
			print "  " * (depth+1) + colors.bold() + key + colors.end()
			print_codes(codes[key], depth+1)

def main(args):
	load_codes(sys.path[0] + "/codes")

	if len(args) == 0:
		path = ""
	else:
		path = args[0]

	codes = find_codes(path)
	print ""
	print_codes(codes)

########NEW FILE########
__FILENAME__ = codeparameters
#!/usr/bin/env python

import re
import sys
import colors
import struct

## wrapper
def validate(param, value):
	validators = {
		'u8'	 : validate_u8,
		'ip'     : validate_ip,
		'u16be'  : validate_u16,
		'u32be'  : validate_u32,
		'u16le'  : validate_u16,
		'u32le'  : validate_u32,
		'string' : validate_string,
		'stringn' : validate_string
	}

	ptype = type_name(param['type'])

	return validators[ ptype ](value)

def output(param, value):
	outfuncs = {
		'u8'	 : output_u8,
		'ip'     : output_ip,
		'u16be'  : output_u16be,
		'u32be'  : output_u32be,
		'u16le'  : output_u16le,
		'u32le'  : output_u32le,
		'string' : output_string,
		'stringn' : output_stringn
	}

	ptype  = type_name(param['type'])
	pmod   = type_modifier(param['type'])

	ret = outfuncs[ ptype ](value)

	if pmod == "not":
		newret = ''
		b = ret.decode("hex")
		for c in list(b):
			newret += "%02x" % (ord(c) ^ 0xff)	
	
		ret = newret

	return ret

## generic number parser
def parse_num(val):
	if val[0:2] == "0x":
		return int(val, 16)
	else:
		return int(val)

## fixed width int validators
def validate_u8(val):
	val = parse_num(val)
	if val >= 0 and val <= 0xff:
		return True
	else:
		return False

def validate_u16(val):
	val = parse_num(val)
	if val >= 0 and val <= 0xffff:
		return True
	else:
		return False

def validate_u32(val):
	val = parse_num(val)
	if val >= 0 and val <= 0xffffffff:
		return True
	else:
		return False

## string
def validate_string(val):
	return True

def output_string(instr):
	instr = instr.replace("\\n", "\n")

	return instr.encode('hex')

def output_stringn(instr):
	return output_string(instr+"\n")

## IP
def validate_ip(val):
	pattern = "^(([1-9]?[0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5]).){3}([1-9]?[0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])$"

	if re.match(pattern, val) is not None:
		return True
	else:
 		return False

def output_ip(instr):
	(a,b,c,d) = instr.split(".")
	return "%02x%02x%02x%02x" % (int(a), int(b), int(c), int(d))


## U8
def output_u8(val):
	val = parse_num(val)
	return struct.pack("B", val).encode("hex")

## U16be
def output_u16be(val):
	val = parse_num(val)
	return struct.pack(">H", val).encode("hex")

## U32be
def output_u32be(val):
	val = parse_num(val)
	return struct.pack(">L", val).encode("hex")

## U16le
def output_u16le(val):
	val = parse_num(val)
	return struct.pack("<H", val).encode("hex")

## U32le
def output_u32le(val):
	val = parse_num(val)
	return struct.pack("<L", val).encode("hex")

def param_stdin(parameter):
	print >>sys.stderr, "%s  >> [%s (%s)]: %s" % (colors.bold(), parameter['name'], parameter['type'], colors.end()),
	line = sys.stdin.readline()

	return line.replace("\n", "")

def type_name(in_string):
	return in_string.split("_")[0]	

def type_modifier(in_string):
	res = in_string.split("_")

	if len(res) > 1:
		return res[1]
	else:
		return False

def handle_parameters(shellcode, params):
	for param in shellcode["parameters"]:
		ok = False

		while ok == False:
			if param['name'] not in params:
				params[ param['name'] ] = param_stdin(param)

			ok = validate(param,  params[ param['name'] ])

			if ok == False:
				print "validation for parameter " + param['name'],
				print " (of type " + type_name(param['type']) + ") ",
				print "failed with input " +  params[ param['name'] ]

				del params [ param['name'] ]

		shellcode["code"] = shellcode["code"].replace(param['placeholder'], output(param, params[ param['name'] ]))

		print >>sys.stderr, "  " + colors.bold() + colors.fg('green') + "++" + colors.end(),
		print >>sys.stderr, " parameter " + colors.bold() + param['name'] + colors.end(),
		print >>sys.stderr, " set to '" + colors.bold() + params [ param['name'] ] + colors.end() + "'"

	return shellcode
	

########NEW FILE########
__FILENAME__ = colors
color_tbl  = [ 'black', 'red', 'green', 'yellow'  ]
color_tbl += [ 'blue', 'magenta', 'cyan', 'white' ]

def fg(col):
	return "\x1b[%dm" % (30 + color_tbl.index(col))

def bold():
	return "\x1b[1m"

def end():
	return "\x1b[0m"

########NEW FILE########
__FILENAME__ = dumpelf
#!/usr/bin/python

import sys
import elf
import struct

def main(args):
	if len(args) != 1 and len(args) != 2:
		print "usage: moneyshot dumpelf <filename> [filter]"
		return

	section_filter = ""

	if len(args) == 2:
		section_filter = args[1]

	myelf = elf.fromfile(args[0])

	if section_filter == "":
		myelf.print_header()

	myelf.print_section_headers(section_filter)

########NEW FILE########
__FILENAME__ = dumpsym
#!/usr/bin/python

import sys
import elf
import struct
import colors

def main(args):
	if len(args) != 1 and len(args) != 2:
		print "usage: moneyshot dumpsym <filename> [filter]"
		return

	myelf = elf.fromfile(args[0])

	sym_filter = ""

	if len(args) == 2:
		sym_filter = args[1]

	if myelf.data[0:4] != "\x7F"+"ELF":
		print "[!] '%s' is not a valid ELF file :(" % (file)
		sys.exit(-1)

	if myelf.elfwidth == 64:
		sixtyfour = True
	else:
		sixtyfour = False

	dynsym = myelf.section(".dynsym")

	if dynsym == False:
		print "ERROR: could not retrieve .dynsym section"
		exit()

	dynstr = myelf.section(".dynstr")
	
	if dynstr == False:
		print "ERROR: could not retrieve .dynstr section"
		exit()

	symbol_names = dynstr['data'].split("\x00")
	symbol_info = {}

	i = 0

	while i < len(dynsym['data']):
		if sixtyfour == True:
			# Elf64_Sym
			(
				st_name, st_info, st_other, st_shndx, st_value, st_size
			) = struct.unpack("<LBBHQQ", dynsym['data'][i:(i+24)])

			i = i+24

		else:
			# Elf32_Sym
			(
				st_name, st_value, st_size, st_info, st_other, st_shndx
			) = struct.unpack("<LLLBBH", dynsym['data'][i:(i+16)])

			i = i+16

		name_len = dynstr['data'][(st_name+1):].find("\x00")
		name = dynstr['data'][ st_name : (st_name+name_len+1) ]
		
		if sym_filter != "" and name.find(sym_filter) == -1:
			continue

		fstr  = colors.fg("green") + "[" + colors.bold() + "%08x" + colors.end()
		fstr += colors.fg("green") + "]" + colors.end() 
		fstr += " '" + colors.fg("red") + colors.bold() + "%s" + colors.end() + "'" 

		print fstr % (st_value, name)

########NEW FILE########
__FILENAME__ = dwords
#!/usr/bin/python

import struct
import sys

def main(args):
	# try read STDIN with 0 argz
	if len(args) == 0:
		lines = sys.stdin.readlines()

		args = []

		for line in lines:
			parts = line.split(" ")

			for part in parts:
				args.append(part)

	if len(args) == 0:
		print "usage: moneyshot rep dwords <dword1> [dword2] [dword..]"
		return

	buf = ""

	for arg in args:
		buf += struct.pack("<L", int(arg, 0))

	sys.stdout.write(buf)

########NEW FILE########
__FILENAME__ = elf
#!/usr/bin/python

import struct
import sys
import os

elf_types = {
	0: 'No file type',
	1: 'Relocatable file',
	2: 'Executable file',
	3: 'LSB shared object',
	4: 'Core file'
} 

elf_machines = {
	0: 'No machine',
	1: 'AT&T WE 32100',
	2: 'SPARC',
	3: 'Intel 80386',
	4: 'Motorola 68k',
	5: 'Morotola 88k',
	7: 'Intel 80860',
	8: 'MIPS RS3000',
	62: 'x86-64'
}

section_types = {
	0: 'NULL',
	1: 'PROGBITS',
	2: 'SYMTAB',
	3: 'STRTAB',
	4: 'RELA',
	5: 'HASH',
	6: 'DYNAMIC',
	7: 'NOTE',
	8: 'NOBITS',
	9: 'REL',
	10: 'SHLIB',
	11: 'DYNSYM'
}

def fromdata(data):
	return ElfObject(data)

def fromfile(filename):
	return ElfObject(open(filename, 'rb').read())

class ElfObject:
	data = ''
	strdata = ''
	elfwidth = 0
	header = { }
	section = { }
	strtable = []
	endianness = 0 # 1=le, 2=be
	unp_char = "<"

	def __init__(self, elf_content):
		self.data = elf_content

		if self.data[0:4] != "\x7F"+"ELF":
			return None

		if ord(self.data[4]) == 1:
			self.elfwidth = 32
		else:
			self.elfwidth = 64

		self.endianness = ord(self.data[5])

		if self.endianness == 1:
			self.unp_char = "<"
		else:
			self.unp_char = ">"

		self.parse_header()
		#self.print_header()

		sh_offset = self.header['shoff']
		sh_length = self.header['shnum'] * self.header['shentsize']
		sh_end    = sh_offset + sh_length
		sh_raw    = self.data[sh_offset:sh_end]

		self.parse_section_headers()

		self.strtable = [""]
		pos = 0

		if self.header['shstrnidx'] != 0:
			strstart = self.sections[ self.header['shstrnidx'] ]['offset']
			strend   = strstart + self.sections[ self.header['shstrnidx'] ]['size']
			self.strdata  = self.data[strstart:strend]


		for section in self.sections:
			if section['addr'] == 0:
				continue

			section_name = self.strdata[ section['name']:].split("\x00")[0]
			self.strtable.append(section_name)

		#self.print_section_headers()

	def section(self, name):
		for section in self.sections:
			section_name = self.strdata[ section['name']:].split("\x00")[0]
			if section_name == name:
				return section

		return False

	def parse_header(self):
		self.header['magic']   = struct.unpack("16c", self.data[0:16])

		if self.elfwidth == 32:
			ehdr_unpack = self.unp_char + "HHLLLLLHHHHHH"
			ehdr_end = 52
		else:
			ehdr_unpack = self.unp_char + "HHLQQQLHHHHHH"
			ehdr_end = 64

		(
			self.header['type'],
			self.header['machine'],
			self.header['version'],
			self.header['entry'],
			self.header['phoff'],
			self.header['shoff'],
			self.header['flags'],
			self.header['ehsize'],
			self.header['phentsize'],
			self.header['phnum'],
			self.header['shentsize'],
			self.header['shnum'],
			self.header['shstrnidx']
		) = struct.unpack(ehdr_unpack, self.data[16:ehdr_end])


	def print_header(self):
		print ""

		print "ELF Type               : %s" % (elf_types[ self.header['type'] ])
		print "Header size            : %d bytes" % (self.header['ehsize'])
		print "Machine Type           : %s" % (elf_machines[ self.header['machine'] ])
		print "ELF Version            : %d" % (self.header['version'])
		print "Entrypoint             : 0x%08x" % (self.header['entry'])
		print ""
		print "Program Headers offset : 0x%08x" % (self.header['phoff'])
		print "Program Header entsize : %d bytes" % (self.header['phentsize'])
		print "Program Header count   : %d" % (self.header['phnum'])
		print ""
		print "Section Headers offset : 0x%08x" % (self.header['shoff'])
		print "Section Header entsize : %d bytes" % (self.header['shentsize'])
		print "Section Header count   : %d" % (self.header['shnum'])
		print "Stringtable section idx: %08x" % (self.header['shstrnidx'])
		print ""

	def parse_section_headers(self):
		i = 0
		self.sections = [ ]

		while i < (self.header['shnum'] * self.header['shentsize']):
			start = self.header['shoff'] + i;
			end   = start + self.header['shentsize']
			sdata = self.data[start:end]
	
			section = { }

			if self.elfwidth == 32:
				shdr_end = 40
				shdr_unpack = self.unp_char + "LLLLLLLLLL"
			else:
				shdr_end = 64
				shdr_unpack = self.unp_char + "LLQQQQLLQQ"

			(
				section['name'],
				section['type'],
				section['flags'],
				section['addr'],
				section['offset'],
				section['size'],
				section['link'],
				section['info'],
				section['align'],
				section['entsz']
			) = struct.unpack(shdr_unpack, sdata[0:shdr_end])


			start = section['offset']
			end   = start + section['size']
			section['data'] = self.data[start:end]

			self.sections.append(section)
			i = i + self.header['shentsize']


	def print_section_headers(self, section_filter = ""):
		for section in self.sections:
			if section['addr'] == 0:
				continue

			section_name = self.strdata[ section['name']:].split("\x00")[0]
	
			if section['type'] in section_types:
				type_string = section_types[ section['type'] ]
			else:
				type_string = "UNKNOWN"

			if section_filter != "" and section_name.find(section_filter) == -1:
				continue

			print "%20s @ 0x%08x [%6d bytes] ** %s" % (section_name, section['addr'], section['size'], type_string)

########NEW FILE########
__FILENAME__ = fmt
#!/usr/bin/python

import sys
from lib.libformatstr import FormatStr

def main(args):
	if len(args) < 1:
		print "usage: moneyshot fmt <primitives>\n"
		print "availables primitives:"
		print "  * p:NNNN      - parameter position where user-controlled input starts"
		print "  * n:NNNN      - specify bytes already written (defaults to 0)"
		print "  * w:XXXX=YYYY - write value YYYY to address XXXX"
		print "  * o:format    - specify output format (base64, b64cmd, raw)\n"

		return

	valid_outformat = [ "base64", "b64cmd", "raw" ]

	out_format = "raw"

	p = FormatStr()

	param_pos = 0
	already_written = 0

	for param in args:
		if param[0:2] == "w:":
			(addr,val) = param[2:].split("=")
			p[ int(addr, 0) ] = int(val, 0);
		elif param[0:2] == "p:":
			param_pos = int(param[2:], 0)
		elif param[0:2] == "n:":
			already_written = int(param[2:], 0)
		elif param[0:2] == "o:":
			out_format = param[2:]

			if out_format not in valid_outformat:
				print "UNKNOWN FMT outformat: '%s'" % (out_format)
				exit()
		else:
			print "UNKNOWN FMT specifier: '%s'" % (param)
			exit()

	fmt_str = p.payload(param_pos, start_len=already_written)

	if out_format == "raw":
		sys.stdout.write(fmt_str)
	elif out_format == "base64":
		sys.stdout.write(fmt_str.encode("base64"))
	elif out_format == "b64cmd":
		sys.stdout.write("`echo "+fmt_str.encode("base64").strip()+"|base64 -d`")


########NEW FILE########
__FILENAME__ = lolsled
#!/usr/bin/python

import sys
import rop
import colors

# Yo DAWG, This is the most retarded
# and limitted x86 subset emulation 
# out in the wild! Only here to cater
# some LOLsled generation, heheheh.

func = {
	'@' : lambda x: inc(x, 'eax'),
	'A' : lambda x: inc(x, 'ecx'),
	'B' : lambda x: inc(x, 'edx'),
	'C' : lambda x: inc(x, 'ebx'),
	'D' : lambda x: inc(x, 'esp'),
	'E' : lambda x: inc(x, 'ebp'),
	'F' : lambda x: inc(x, 'esi'),
	'G' : lambda x: inc(x, 'edi'),
	'H' : lambda x: dec(x, 'eax'),
	'I' : lambda x: dec(x, 'ecx'),
	'J' : lambda x: dec(x, 'edx'),
	'K' : lambda x: dec(x, 'ebx'),
	'L' : lambda x: dec(x, 'esp'),
	'M' : lambda x: dec(x, 'ebp'),
	'N' : lambda x: dec(x, 'esi'),
	'O' : lambda x: dec(x, 'edi'),
	'P' : lambda x: dec(x, 'esp', 4),
	'Q' : lambda x: dec(x, 'esp', 4),
	'R' : lambda x: dec(x, 'esp', 4),
	'S' : lambda x: dec(x, 'esp', 4),
	'T' : lambda x: dec(x, 'esp', 4),
	'U' : lambda x: dec(x, 'esp', 4),
	'V' : lambda x: dec(x, 'esp', 4),
	'W' : lambda x: dec(x, 'esp', 4),
	'X' : lambda x: inc(x, 'esp', 4),
	'Y' : lambda x: inc(x, 'esp', 4),
	'Z' : lambda x: inc(x, 'esp', 4),
	'[' : lambda x: inc(x, 'esp', 4),
	'\\' : lambda x: inc(x, 'esp', 4),
	']' : lambda x: inc(x, 'esp', 4),
	'^' : lambda x: inc(x, 'esp', 4),
	'_' : lambda x: inc(x, 'esp', 4),
}

def inc(ctx, reg, n=1):
	ctx[reg] = ctx[reg]+n
	return ctx

def dec(ctx, reg, n=1):
	ctx[reg] = ctx[reg]-n
	return ctx;

def emu(input_code):
	regs = {
		'eax' : 0,
		'ebx' : 0,
		'ecx' : 0,
		'edx' : 0,
		'esi' : 0,
		'edi' : 0,
		'ebp' : 0,
		'esp' : 0
	}

	for c in input_code:
		if c not in func:
			print "*** ILLEGAL OPCODE '%c' *** :(" % (c)
			return

		regs = func[c](regs)

	#print regs

	return regs


def main(args):
	if len(args) != 1 and len(args) != 2:
		print "usage:"
		print "  moneyshot lolsled <length> <words>"
		print "  moneyshot lolsled <dictionary>"

		return 

	# some 'harmless' x86 insns, just inc's and dec's
	whitelist=[
		"A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O"
	]

	# length?
	if args[0].isdigit():
		rs = emu(args[1])
		fstr = " CLOBBER: "
		cl = False
		for reg in rs:
			if rs[reg] != 0:
				fstr += "%s=%08x " % (reg, rs[reg])
				cl = True

		if cl == False:
			fstr += "No clobbering, yay!"

		print fstr

	# assume dictfile (find mode)
	else:
		words = open(args[0]).readlines()
		for word in words:
			ok = True
			word = word.strip().upper()

			for c in word:
				if c not in whitelist:
					ok = False

			if not ok:
				continue

			fstr = colors.fg('cyan')
			fstr += ">> "
			fstr += colors.fg('green')
			fstr += "'%15s' %s--> " % (word, colors.fg('white')+colors.bold())
			fstr += colors.end() + colors.fg('red')
			r = rop.disas_str(0, word)
			fstr += ' ; '.join(r).lower()
			rs = emu(word)
			fstr += " CLOBBER: "
			cl = False
			for reg in rs:
				if rs[reg] != 0:
					fstr += "%s=%08x " % (reg, rs[reg])
					cl = True

			print fstr

	print colors.end()


########NEW FILE########
__FILENAME__ = moneyshot
#!/usr/bin/python

import sys
import colors, outputter, codelibrary, codeparameters
import lolsled, builder, pattern, rop, rop_arm, fmt
import shell, rep, dwords, dumpsym, dumpelf

def banner():
	asquee = """
    __   __  ______.___   __  _____._  __._______._ __  ____._________
   /  \ /  \/  __  |    \|  |/  ___| \/  /\  ___/  |  |/ __  \__   __/
  /    '    \   /  |  |\    |   _|_\    /__\   \|     |   /  |  |  |
 /___\  /    \_____|__|  \__|______||__||______/|__|__|\_____|  |__|
      \/ _____\\   """

	sys.stderr.write(colors.bold() + colors.fg('cyan') + asquee + colors.end() + "\n\n")

def usage():
	print ""
	print "  usage: moneyshot <action> [options]\n"
	print "  actions:"
	print "    * list     - list shellcodes"
	print "    * build    - build shellcodes"
	print "    * pattern  - build patterns"
	print "    * lolsled  - build a lolsled"
	print "    * format   - format input"
	print "    * fmt      - formatstring helper"
	print "    * rop      - ROP helper"
	print "    * rop-arm  - ARM ROP helper"
	print "    * rep      - String repeater"
	print "    * dwords   - binary format dwords"
	print "    * dumpsym  - dump symbols for given binary"
	print "    * dumpelf  - dump information for given binary"

if len(sys.argv) == 1:
	banner()
	usage()
	exit()

action = sys.argv[1]

valid_actions = [
	"list", "build", "pattern", "lolsled", "format", "fmt", 
	"rop", "rop-arm", "rep", "dwords", "dumpsym", "dumpelf"
]

if action not in valid_actions:
	banner()
	usage()
	exit()

action = action.replace("-", "_")

if action == "list":
	action = "codelibrary"

if action == "format":
	action = "outputter"

if action == "build":
	action = "builder"

globals()[ action ].main(sys.argv[2:])

exit()

########NEW FILE########
__FILENAME__ = outputter
#!/usr/bin/python

import colors
import distorm3
import optparse
import sys
import struct

from lib.darm import darm

def disas(buf, array_name = '', row_width = 16, fancy = False, sixtyfour = False):
	parser = optparse.OptionParser()

	if sixtyfour == True:
		parser.set_defaults(dt=distorm3.Decode64Bits)
	else:
		parser.set_defaults(dt=distorm3.Decode32Bits)

	options, args = parser.parse_args([])

	disas = distorm3.Decode(0, buf, options.dt)
	out = ''

	for (offset, size, instruction, hexdump) in disas:
		tmp = ''

		if fancy:
			tmp += colors.fg('cyan')

		tmp += "%.8x: " % (offset)

		if fancy:
			tmp += colors.fg('red')

		tmp += hexdump
		tmp += " " * (20-len(hexdump))

		if fancy:
			tmp += colors.fg('green')

		tmp += instruction

		if fancy:
			tmp += colors.end()

		out += "  " + tmp + "\n"

	return out.lower()

def disas64(buf, array_name = '', row_width = 16, fancy = False):
	return disas(buf, array_name, row_width, fancy, True)

def disas_arm(buf, array_name = '', row_width = 16, fancy = False):
	insns = struct.unpack("I"*(len(buf)/4), buf)
	out = ""
	pos = 0
	for insn in insns:
		tmp = ""

		if fancy:
			tmp += colors.fg('cyan')

		tmp += "%.8x: " % (pos)

		if fancy:
			tmp += colors.fg('red') + colors.bold()

		tmp += "%08x " % (insn)

		if fancy:
			tmp += colors.end() + colors.fg('green')

		tmp += str(darm.disasm_armv7(insn))

		if fancy:
			tmp += colors.end()

		out += "  " + tmp + "\n"

		pos = pos+4

	return out

def disas_thumb(buf, array_name = '', row_width = 16, fancy = False):
	insns = struct.unpack("H"*(len(buf)/2), buf)
	out = ""
	pos = 0
	for insn in insns:
		tmp = ""

		if fancy:
			tmp += colors.fg('cyan')

		tmp += "%.8x: " % (pos)

		if fancy:
			tmp += colors.fg('red') + colors.bold()

		tmp += "%08x " % (insn)

		if fancy:
			tmp += colors.end() + colors.fg('green')

		tmp += str(darm.disasm_thumb(insn))

		if fancy:
			tmp += colors.end()

		out += "  " + tmp + "\n"

		pos = pos+2

	return out

def bash(buf, array_name = 'shellcode', row_width = 16, fancy = False):
	out = "$'"
	badchars = [ 0x27, 0x5c ]
	for c in buf:
		o = ord(c)
		if o >= 0x20 and o <= 0x7E and o not in badchars:
			out += c
		else:
			out += "\\x%02x" % (o)

	out += "'"
	return out

def hexdump(buf, array_name = 'shellcode', row_width = 16, fancy = False):
	# build horizontal marker
	out = "           | "

	for i in range(0, row_width):
		if fancy:
			out += "%02x " % (i)
			#out += colors.bold() + colors.fg('yellow') + ("%02x " % (i)) + colors.end()
		else:
			out += "%02x " % (i)

	out += "|\n"

	delim_row  = "  +--------+";
	delim_row += "-" * (row_width*3 + 1) + "+" + "-" * (row_width+1) + "-+"

	if fancy:
		out += colors.bold() + delim_row + colors.end() + "\n"
	else:
		out += delim_row + "\n"

	for i in range(0, len(buf), row_width):
		if fancy:
			out += colors.bold() + "  | " + colors.fg("cyan") + ("%06x" % (i)) + " | " + colors.end()
		else:
			out += "  | %06x | " % (i)

		for j in range(0, row_width):
			if i+j < len(buf):
				if fancy:
					str = colors.fg('red') + ("%02x " % (ord(buf[i+j])))

					if (i+j)%8 >= 4:
						out += colors.bold() + str + colors.end()
					else:
						out += str + colors.end()
				else:
					out += "%02x " % (ord(buf[i+j]))
			else:
				out += "   "

		asciiz = ''

		for j in range(0, row_width):
			if i+j < len(buf):
				c = ord(buf[i+j])

				if c >= 0x20 and c <= 0x7e:
					asciiz += buf[i+j]
				else:
					asciiz += '.'
			else:
				asciiz += ' '

		if fancy:
			out += colors.bold() + "| " + colors.fg('green') + asciiz + colors.end() + colors.bold() + " |" + colors.end() + "\n"
		else:
			out += "| " + asciiz + " |\n"

	if fancy:
		out += colors.bold() + delim_row + colors.end() + "\n"
	else:
		out += delim_row + "\n"

	return out

def code_array(buf, array_name = 'shellcode', row_width = 16, line_delimiter = '', fancy = False):
	lines = []
	out = array_name +" = \n"

	for i in range(0, len(buf), row_width):
		j = 0
		linebuf = ''
		while (j < row_width and (i+j) < len(buf)):
			linebuf += "\\x%02x" % ( ord(buf[i+j]) )
			j = j + 1

		lines.append(linebuf);

	for i in range(0, len(lines)-1):
		if fancy:
			out += "\t" + colors.bold() + colors.fg('magenta') + "\""
			out += colors.fg("red") + lines[i]
			out += colors.fg('magenta') + "\"" + colors.end()
			out += line_delimiter + "\n"
		else:
			out += "\t\"%s\"%s\n" % ( lines[i], line_delimiter )

	if fancy:
		out += "\t" + colors.bold() + colors.fg('magenta') + "\""
		out += colors.fg("red") + lines[len(lines)-1]
		out += colors.fg('magenta') + "\"" + colors.end() + ";"
		out += "\n\n"
		# out += "\t\"%s\";\n\n" % ( lines[len(lines)-1] )
	else:
		out += "\t\"%s\";\n\n" % ( lines[len(lines)-1] )

	return out

def c(buf, array_name = 'shellcode', row_width = 16, fancy = False):
	if fancy:
		name  = colors.fg('green') + "unsigned " + colors.bold() + "char " + colors.end()
		name += colors.bold() + array_name + "[]" +  colors.end()
	else:
		name = "unsigned char " + array_name + "[]"

	return code_array(buf, name, row_width, '', fancy);

def carray(buf, array_name = 'shellcode', row_width = 16, fancy = False):
	out = "unsigned char %s[%d]={\n" % (array_name, len(buf))

	n = 0

	for c in buf:
		if n == len(buf)-1:
			out += "0x%02x " % (ord(c))
		else:
			out += "0x%02x, " % (ord(c))

		n=n+1

		if (n % row_width) == 0:
			out += "\n"

	out += "};\n"

	return out

def python(buf, array_name = 'shellcode', row_width = 16, fancy = False):
	lines = []
	out = ""

	for i in range(0, len(buf), row_width):
		j = 0
		linebuf = ''
		while (j < row_width and (i+j) < len(buf)):
			linebuf += "\\x%02x" % ( ord(buf[i+j]) )
			j = j + 1

		lines.append(linebuf);

	for i in range(0, len(lines)-1):
		if fancy:
			if i == 0:
				out += array_name + " =  " + colors.bold() + colors.fg('magenta') + "\""
			else:
				out += array_name + " += " + colors.bold() + colors.fg('magenta') + "\""

			out += colors.fg("red") + lines[i]
			out += colors.fg('magenta') + "\"\n" + colors.end()
		else:
			if i == 0:
				out += array_name + "  = \"%s\"\n" % ( lines[i] )
			else:
				out += array_name + " += \"%s\"\n" % ( lines[i] )

	if fancy:
		out += array_name + " += " + colors.bold() + colors.fg('magenta') + "\""
		out += colors.fg("red") + lines[len(lines)-1]
		out += colors.fg('magenta') + "\"" + colors.end() + ";"
		out += "\n\n"
		# out += "\t\"%s\";\n\n" % ( lines[len(lines)-1] )
	else:
		out += array_name + " += \"%s\";\n\n" % ( lines[len(lines)-1] )

	return out

def perl(buf, array_name = 'shellcode', row_width = 16, fancy = False):
	return code_array(buf, '$' + array_name, row_width, ' . ', fancy)

def php(buf, array_name = 'shellcode', row_width = 16, fancy = False):
	return perl(buf, array_name, row_width, fancy)

def raw(buf, array_name = '', row_width = 16, fancy = False):
	if fancy:
		return hexdump(buf, array_name, row_width, fancy)
	else:
		return buf

def hhex(buf, array_name = '', row_width = 16, fancy = False):
	return buf.encode("hex")

def dwords(buf, array_name = '', row_width = 16, fancy = False):
	i = 0

	out = ""

	if len(buf) % 4 != 0:
		buf += "\x00" * (4 - (len(buf)%4))

	while i < len(buf):
		v = struct.unpack("<L", buf[i:i+4])
		out += "%08x: 0x%08x\n" % (i, v[0])
		i = i+4

	return out

def hex_bin(str):
	return str.decode('hex')

outfunc = {
	'c'       : c,
	'carray'  : carray,
	'php'     : php,
	'perl'    : perl,
	'hexdump' : hexdump,
	'hex'     : hhex,
	'disas'   : disas,
	'disas64' : disas64,
	'disas-arm' : disas_arm,
	'disas-thumb' : disas_thumb,
	'python'  : python,
	'bash'    : bash,
	'raw'     : raw,
	'dwords'  : dwords
}

def main(args):
	if len(args) > 2:
		print "usage: moneyshot format [outformat] [fancy=0]"
		return

	if len(args) >= 1:
		lang = args[0]
	else:
		lang = "c"

	if lang not in outfunc:
		print "Invalid outformat given: '%s' :(" % (lang)
		return False

	data = sys.stdin.readlines()
	data = ''.join(data)

	if len(args) == 2 and args[1] == "1":
		do_fancy = True
	else:
		do_fancy = False

	print outfunc[ lang ](data, fancy = do_fancy),

########NEW FILE########
__FILENAME__ = pattern
#!/usr/bin/python

def gen_pattern(length):
	n = 0
	out = ''

	for x in range(0,26):
		for y in range(0,26):
			for z in range(0,10):
				out += "%c%c%c" % (chr(0x41+x), chr(0x61+y), chr(0x30+z))
				n = n + 3
				if n >= length:
					return out[0:length]

def main(args):
	if len(args) == 1:
		length = int(args[0])
		pat = gen_pattern(length)
		print pat
	elif len(args) == 2:
		length = int(args[0])
		pat = gen_pattern(length)

		if args[1][0:2] == "0x":
			hexval = int(args[1], 16)
			str  = chr(hexval & 0xff)
			str += chr((hexval >> 8) & 0xff)
			str += chr((hexval >> 16) & 0xff)
			str += chr((hexval >> 24) & 0xff)
			res = pat.find(str, 0)
		else:
			res = pat.find(args[1], 0)

		if res == -1:
			print "Value not found in pattern"
		else:
			print res
	else:
		print "usage: moneyshot pattern <length> [hexval]"

########NEW FILE########
__FILENAME__ = rep
#!/usr/bin/python

import sys

def main(args):
	if len(args) != 2:
		print "usage: moneyshot rep <str> <length>"
		return

	sys.stdout.write(args[0] * int(args[1]))

########NEW FILE########
__FILENAME__ = rop
#!/usr/bin/python

import os
import sys
import elf
import distorm3
import optparse
import colors
import re
import binascii
from distorm3 import Decode, Decode16Bits, Decode32Bits, Decode64Bits

def match_disas(disas, match):
	for (offset, size, instruction, hexdump) in disas:
		if instruction.find(match) != -1:
			return True

	return False

def ok_disas(disas):
	for (offset, size, instruction, hexdump) in disas:
		if instruction.find("DB ") != -1:
			return False

		if instruction.find("CALL") != -1:
			return False

	return True

def findstr(section, matchstring):
	ropmatches = []

	matchstring = matchstring.replace("?", ".")

	p = re.compile(matchstring)
	for m in p.finditer(section.encode("hex")):
		if (m.start() % 2) != 0:
			continue

		ropmatches.append([ m.start() / 2, m.group() ])

	return ropmatches

def assemble_str(code, sixtyfour = False):
	code = code.replace(";","\n")
	code = "_start:\n" + code + "\n"
	f = open("tmp.s", 'w')
	f.write(code)
	f.close()

	if sixtyfour:
		machine = "-m64"
	else:
		machine = "-m32"

	ret = os.system("gcc "+machine+" -s -o tmp.elf tmp.s -nostartfiles -nodefaultlibs 2>/dev/null")

	if ret != 0:
		print ">> Assemble fail :("
		os.system("rm -rf tmp.s tmp.elf tmp.bin")
		exit()

	os.system("objcopy -O binary -j .text tmp.elf tmp.bin")
	pattern = binascii.hexlify(open("tmp.bin").read())
	os.system("rm -rf tmp.s tmp.elf tmp.bin")

	return pattern
	

def disas_str(addr, data, sixtyfour = False):
	parser = optparse.OptionParser()

	if sixtyfour == True:
		parser.set_defaults(dt=distorm3.Decode64Bits)
	else:
		parser.set_defaults(dt=distorm3.Decode32Bits)

	options, args = parser.parse_args(sys.argv)

	out_insn = []

	disas = distorm3.Decode(addr, data, options.dt)

	for (offset, size, instruction, hexdump) in disas:
		out_insn.append(instruction)

	return out_insn
		

def do_ropfind(file, match_string):
	gadgets = []

	myelf = elf.fromfile(file)

	if myelf.data[0:4] != "\x7F"+"ELF":
		print "[!] '%s' is not a valid ELF file :(" % (file)
		sys.exit(-1)

	if myelf.elfwidth == 64:
		print "[+] 64bit ELF"
		sixtyfour = True
	else:
		print "[+] 32bit ELF"
		sixtyfour = False


	# figure out parameter
	if re.search("^[0-9a-f\?]+$", match_string) != None:
		pattern = match_string
	else:
		pattern = assemble_str(match_string, sixtyfour)


	print "[!] pattern: '%s'" % pattern

	for section_name in myelf.strtable:
		if section_name == "":
			continue

		section = myelf.section(section_name)

		# check for PROGBITS type
		if section['type'] != 1:
			continue

		matches = findstr(section['data'], pattern)

		if len(matches) == 0:
			continue

		pstr  = colors.fg('cyan') + ">> section '" + colors.bold() + section_name + colors.end()
		pstr += colors.fg('cyan') + "' [" + colors.bold() + str(len(matches)) + colors.end()
		pstr += colors.fg('cyan') + " hits]"

		m = 0

		for match in matches:
			if match[1] in gadgets:
				continue

			if m == 0:
				print pstr
				m = 1

			disas = disas_str(section['addr'] + match[0], binascii.unhexlify(match[1]), sixtyfour)
			fstr =  colors.fg('cyan') + " \_ " + colors.fg('green') + "%08x [" + colors.bold() + match[1] + colors.end()
			fstr += colors.fg('green') + "] "+ colors.bold() + "-> " + colors.end()
			fstr += colors.fg('red') + ' ; '.join(disas).lower() + colors.end()
			print fstr % (section['addr'] + match[0])

			gadgets.append(match[1])


		if m == 1:
			print ""


def do_ezrop(text):
	i = 0
	while i < len(text['data']):
		if text['data'][i] == "\xc3":
			block_len = 10

			while block_len > 1:
				start = i - block_len
				end   = start + block_len + 1
				disas = distorm3.Decode(text['addr'] + start, text['data'][start:end], options.dt)

				if disas[len(disas)-1][2] == "RET" and match_disas(disas, sys.argv[2]) and ok_disas(disas):
					found_start = False

					for (offset, size, instruction, hexdump) in disas:
						if instruction.find(sys.argv[2]) != -1:
							found_start = True

						if found_start == True:
							out = colors.fg('cyan')
							out += "%.8x: " % (offset)
							out += colors.fg('red')
							out += hexdump
							out += " " * (20-len(hexdump))
							out += colors.fg('green')
							out += instruction + colors.end()
							print out

					print "=" * 50

					i = i + block_len
					break

				block_len = block_len - 1

		i = i + 1

def main(args):
	if len(args) < 2:
		print "usage: moneyshot rop <binary> <pattern/code>"
	else:
		do_ropfind(args[0], " ".join(args[1:]))

########NEW FILE########
__FILENAME__ = rop_arm
#!/usr/bin/python

from lib.darm import darm

import os
import sys
import elf
import colors
import re
import struct
import binascii

def match_disas(disas, match):
	for (offset, size, instruction, hexdump) in disas:
		if instruction.find(match) != -1:
			return True

	return False

def ok_disas(disas):
	for (offset, size, instruction, hexdump) in disas:
		if instruction.find("DB ") != -1:
			return False

		if instruction.find("CALL") != -1:
			return False

	return True

def findstr(section, matchstring):
	ropmatches = []

	matchstring = matchstring.replace("?", ".")

	p = re.compile(matchstring)
	for m in p.finditer(section.encode("hex")):
		if (m.start() % 4) != 0:
			continue

		ropmatches.append([ m.start() / 2, m.group() ])

	return ropmatches

def assemble_str(code):
	code = code.replace(";","\n")
	code = "_start:\n" + code + "\n"
	f = open("tmp.s", 'w')
	f.write(code)
	f.close()

	ret = os.system("arm-none-eabi-gcc -s -o tmp.elf tmp.s -nostartfiles -nodefaultlibs 2>/dev/null")

	if ret != 0:
		print ">> Assemble fail :("
		#os.system("rm -rf tmp.s tmp.elf tmp.bin")
		exit()

	os.system("arm-none-eabi-objcopy -O binary -j .text tmp.elf tmp.bin")
	pattern = binascii.hexlify(open("tmp.bin").read())
	os.system("rm -rf tmp.s tmp.elf tmp.bin")

	return pattern
	

def disas_str(addr, data, thumb_mode):
	out_insn = []


	if thumb_mode == True:
		insns = struct.unpack("H"*(len(data)/2), data)

		for insn in insns:
			out_insn.append(str(darm.disasm_thumb(insn)))
	else:
		insns = struct.unpack("I"*(len(data)/4), data)

		for insn in insns:
			out_insn.append(str(darm.disasm_armv7(insn)))

	return out_insn

def do_ropfind(file, match_string):
	gadgets = []

	myelf = elf.fromfile(file)

	if myelf.data[0:4] != "\x7F"+"ELF":
		print "[!] '%s' is not a valid ELF file :(" % (file)
		sys.exit(-1)


	# figure out parameter
	if re.search("^[0-9a-f\?]+$", match_string) != None:
		pattern = match_string
	else:
		pattern = assemble_str(match_string)


	print "[!] pattern: '%s'" % pattern

	for section_name in myelf.strtable:
		if section_name == "":
			continue

		section = myelf.section(section_name)

		# check for PROGBITS type
		if section['type'] != 1:
			continue

		matches = findstr(section['data'], pattern)

		if len(matches) == 0:
			continue

		pstr  = colors.fg('cyan') + ">> section '" + colors.bold() + section_name + colors.end()
		pstr += colors.fg('cyan') + "' [" + colors.bold() + str(len(matches)) + colors.end()
		pstr += colors.fg('cyan') + " hits]"

		m = 0

		for match in matches:
			if match[1] in gadgets:
				continue

			if m == 0:
				print pstr
				m = 1

			disas = disas_str(section['addr'] + match[0], binascii.unhexlify(match[1]), True)
			fstr =  colors.fg('cyan') + " \_ " + colors.fg('green') + "%08x [" + colors.bold() + match[1] + colors.end()
			fstr += colors.fg('green') + "] "+ colors.bold() + "-> " + colors.end()
			fstr += colors.fg('red') + "("+colors.bold()+"Thumb"+colors.end()+colors.fg('red')+") "  + ' ; '.join(disas).lower() + colors.end()
			print fstr % (section['addr'] + match[0] + 1)

			gadgets.append(match[1])
			if (len(binascii.unhexlify(match[1])) % 4) == 0:
				disas = disas_str(section['addr'] + match[0], binascii.unhexlify(match[1]), False)
				fstr =  colors.fg('cyan') + " \_ " + colors.fg('green') + "%08x [" + colors.bold() + match[1] + colors.end()
				fstr += colors.fg('green') + "] "+ colors.bold() + "-> " + colors.end()
				fstr += colors.fg('red') + "("+colors.bold()+"ARM"+colors.end()+colors.fg('red')+"  ) " + ' ; '.join(disas).lower() + colors.end()

				if not (len(disas) == 1 and (disas[0] == "" or disas[0] == "None")):
					print fstr % (section['addr'] + match[0])

					gadgets.append(match[1])

		if m == 1:
			print ""


def main(args):
	if len(args) < 2:
		print "usage: moneyshot rop-arm <binary> <pattern/code>"
	else:
		do_ropfind(args[0], " ".join(args[1:]))

########NEW FILE########
__FILENAME__ = shell
#!/usr/bin/python

import socket, termios, tty, select, os

def main(args):
	if (len(args) != 2):
		print "usage: moneyshot shell <host> <port>"
		exit()	

	target = (args[0], int(args[1]))

	s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	s.connect(target)

	old_settings = termios.tcgetattr(0)
	try:
		tty.setcbreak(0)
		c = True
		while c:
			for i in select.select([0, s.fileno()], [], [], 0)[0]:
				c = os.read(i, 1024)
				if c: os.write(s.fileno() if i == 0 else 1, c)
	except KeyboardInterrupt: pass
	finally: termios.tcsetattr(0, termios.TCSADRAIN, old_settings)

########NEW FILE########
