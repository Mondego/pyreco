__FILENAME__ = build_app
# coding=utf-8
import sys
import os

if sys.platform.startswith('darwin'):
    from setuptools import setup

    version = os.environ['BUILD_NAME']

    APP = ['Cura/cura.py']
    DATA_FILES = ['Cura/LICENSE', 'resources/images', 'resources/meshes', 'resources/example', 'resources/firmware', 'resources/locale', 'resources/machine_profiles', 'plugins']
    PLIST = {
        u'CFBundleName': u'Cura',
        u'CFBundleShortVersionString': version,
        u'CFBundleVersion': version,
        u'CFBundleIdentifier': u'com.ultimaker.Cura-'+version,
        u'LSMinimumSystemVersion': u'10.6',
        u'LSApplicationCategoryType': u'public.app-category.graphics-design',
        u'CFBundleDocumentTypes': [
            {
                u'CFBundleTypeRole': u'Viewer',
                u'LSItemContentTypes': [u'com.pleasantsoftware.uti.stl'],
                u'LSHandlerRank': u'Owner',
                },
            {
                u'CFBundleTypeRole': u'Viewer',
                u'LSItemContentTypes': [u'org.khronos.collada.digital-asset-exchange'],
                u'LSHandlerRank': u'Owner'
            },
            {
                u'CFBundleTypeName': u'Wavefront 3D Object',
                u'CFBundleTypeExtensions': [u'obj'],
                u'CFBundleTypeMIMETypes': [u'application/obj-3d'],
                u'CFBundleTypeRole': u'Viewer',
                u'LSHandlerRank': u'Owner'
            }
        ],
        u'UTImportedTypeDeclarations': [
            {
                u'UTTypeIdentifier': u'com.pleasantsoftware.uti.stl',
                u'UTTypeConformsTo': [u'public.data'],
                u'UTTypeDescription': u'Stereo Lithography 3D object',
                u'UTTypeReferenceURL': u'http://en.wikipedia.org/wiki/STL_(file_format)',
                u'UTTypeTagSpecification': {u'public.filename-extension': [u'stl'], u'public.mime-type': [u'text/plain']}
            },
            {
                u'UTTypeIdentifier': u'org.khronos.collada.digital-asset-exchange',
                u'UTTypeConformsTo': [u'public.xml', u'public.audiovisual-content'],
                u'UTTypeDescription': u'Digital Asset Exchange (DAE)',
                u'UTTypeTagSpecification': {u'public.filename-extension': [u'dae'], u'public.mime-type': [u'model/vnd.collada+xml']}
            },
            {
                u'UTTypeIdentifier': u'com.ultimaker.obj',
                u'UTTypeConformsTo': [u'public.data'],
                u'UTTypeDescription': u'Wavefront OBJ',
                u'UTTypeReferenceURL': u'https://en.wikipedia.org/wiki/Wavefront_.obj_file',
                u'UTTypeTagSpecification': {u'public.filename-extension': [u'obj'], u'public.mime-type': [u'text/plain']}
            },
            {
                u'UTTypeIdentifier': u'com.ultimaker.amf',
                u'UTTypeConformsTo': [u'public.data'],
                u'UTTypeDescription': u'Additive Manufacturing File',
                u'UTTypeReferenceURL': u'https://en.wikipedia.org/wiki/Additive_Manufacturing_File_Format',
                u'UTTypeTagSpecification': {u'public.filename-extension': [u'amf'], u'public.mime-type': [u'text/plain']}
            }
        ]
    }
    OPTIONS = {
        'argv_emulation': True,
        'iconfile': 'resources/Cura.icns',
        'includes': ['objc', 'Foundation'],
        'resources': DATA_FILES,
        'optimize': '2',
        'plist': PLIST,
        'bdist_base': 'scripts/darwin/build',
        'dist_dir': 'scripts/darwin/dist'
    }

    setup(
        name="Cura",
        app=APP,
        data_files=DATA_FILES,
        options={'py2app': OPTIONS},
        setup_requires=['py2app']
    )
else:
   print 'No build_app implementation for your system.'

########NEW FILE########
__FILENAME__ = chipDB
"""
Database of AVR chips for avr_isp programming. Contains signatures and flash sizes from the AVR datasheets.
To support more chips add the relevant data to the avrChipDB list.
"""
__copyright__ = "Copyright (C) 2013 David Braam - Released under terms of the AGPLv3 License"

avrChipDB = {
	'ATMega1280': {
		'signature': [0x1E, 0x97, 0x03],
		'pageSize': 128,
		'pageCount': 512,
	},
	'ATMega2560': {
		'signature': [0x1E, 0x98, 0x01],
		'pageSize': 128,
		'pageCount': 1024,
	},
}

def getChipFromDB(sig):
	for chip in avrChipDB.values():
		if chip['signature'] == sig:
			return chip
	return False


########NEW FILE########
__FILENAME__ = intelHex
"""
Module to read intel hex files into binary data blobs.
IntelHex files are commonly used to distribute firmware
See: http://en.wikipedia.org/wiki/Intel_HEX
"""
__copyright__ = "Copyright (C) 2013 David Braam - Released under terms of the AGPLv3 License"
import io

def readHex(filename):
	"""
	Read an verify an intel hex file. Return the data as an list of bytes.
	"""
	data = []
	extraAddr = 0
	f = io.open(filename, "r")
	for line in f:
		line = line.strip()
		if line[0] != ':':
			raise Exception("Hex file has a line not starting with ':'")
		recLen = int(line[1:3], 16)
		addr = int(line[3:7], 16) + extraAddr
		recType = int(line[7:9], 16)
		if len(line) != recLen * 2 + 11:
			raise Exception("Error in hex file: " + line)
		checkSum = 0
		for i in xrange(0, recLen + 5):
			checkSum += int(line[i*2+1:i*2+3], 16)
		checkSum &= 0xFF
		if checkSum != 0:
			raise Exception("Checksum error in hex file: " + line)
		
		if recType == 0:#Data record
			while len(data) < addr + recLen:
				data.append(0)
			for i in xrange(0, recLen):
				data[addr + i] = int(line[i*2+9:i*2+11], 16)
		elif recType == 1:	#End Of File record
			pass
		elif recType == 2:	#Extended Segment Address Record
			extraAddr = int(line[9:13], 16) * 16
		else:
			print(recType, recLen, addr, checkSum, line)
	f.close()
	return data

########NEW FILE########
__FILENAME__ = ispBase
"""
General interface for Isp based AVR programmers.
The ISP AVR programmer can load firmware into AVR chips. Which are commonly used on 3D printers.

 Needs to be subclassed to support different programmers.
 Currently only the stk500v2 subclass exists.
"""
__copyright__ = "Copyright (C) 2013 David Braam - Released under terms of the AGPLv3 License"

import chipDB

class IspBase():
	"""
	Base class for ISP based AVR programmers.
	Functions in this class raise an IspError when something goes wrong.
	"""
	def programChip(self, flashData):
		""" Program a chip with the given flash data. """
		self.curExtAddr = -1
		self.chip = chipDB.getChipFromDB(self.getSignature())
		if not self.chip:
			raise IspError("Chip with signature: " + str(self.getSignature()) + "not found")
		self.chipErase()
		
		print("Flashing %i bytes" % len(flashData))
		self.writeFlash(flashData)
		print("Verifying %i bytes" % len(flashData))
		self.verifyFlash(flashData)

	def getSignature(self):
		"""
		Get the AVR signature from the chip. This is a 3 byte array which describes which chip we are connected to.
		This is important to verify that we are programming the correct type of chip and that we use proper flash block sizes.
		"""
		sig = []
		sig.append(self.sendISP([0x30, 0x00, 0x00, 0x00])[3])
		sig.append(self.sendISP([0x30, 0x00, 0x01, 0x00])[3])
		sig.append(self.sendISP([0x30, 0x00, 0x02, 0x00])[3])
		return sig
	
	def chipErase(self):
		"""
		Do a full chip erase, clears all data, and lockbits.
		"""
		self.sendISP([0xAC, 0x80, 0x00, 0x00])

	def writeFlash(self, flashData):
		"""
		Write the flash data, needs to be implemented in a subclass.
		"""
		raise IspError("Called undefined writeFlash")

	def verifyFlash(self, flashData):
		"""
		Verify the flash data, needs to be implemented in a subclass.
		"""
		raise IspError("Called undefined verifyFlash")

class IspError():
	def __init__(self, value):
		self.value = value
	def __str__(self):
		return repr(self.value)

########NEW FILE########
__FILENAME__ = stk500v2
"""
STK500v2 protocol implementation for programming AVR chips.
The STK500v2 protocol is used by the ArduinoMega2560 and a few other Arduino platforms to load firmware.
"""
__copyright__ = "Copyright (C) 2013 David Braam - Released under terms of the AGPLv3 License"
import os, struct, sys, time

from serial import Serial
from serial import SerialException

import ispBase, intelHex

class Stk500v2(ispBase.IspBase):
	def __init__(self):
		self.serial = None
		self.seq = 1
		self.lastAddr = -1
		self.progressCallback = None
	
	def connect(self, port = 'COM22', speed = 115200):
		if self.serial is not None:
			self.close()
		try:
			self.serial = Serial(str(port), speed, timeout=1, writeTimeout=10000)
		except SerialException as e:
			raise ispBase.IspError("Failed to open serial port")
		except:
			raise ispBase.IspError("Unexpected error while connecting to serial port:" + port + ":" + str(sys.exc_info()[0]))
		self.seq = 1
		
		#Reset the controller
		self.serial.setDTR(1)
		time.sleep(0.1)
		self.serial.setDTR(0)
		time.sleep(0.2)

		self.serial.flushInput()
		self.serial.flushOutput()
		self.sendMessage([1])
		if self.sendMessage([0x10, 0xc8, 0x64, 0x19, 0x20, 0x00, 0x53, 0x03, 0xac, 0x53, 0x00, 0x00]) != [0x10, 0x00]:
			self.close()
			raise ispBase.IspError("Failed to enter programming mode")
		self.serial.timeout = 5

	def close(self):
		if self.serial is not None:
			self.serial.close()
			self.serial = None

	#Leave ISP does not reset the serial port, only resets the device, and returns the serial port after disconnecting it from the programming interface.
	#	This allows you to use the serial port without opening it again.
	def leaveISP(self):
		if self.serial is not None:
			if self.sendMessage([0x11]) != [0x11, 0x00]:
				raise ispBase.IspError("Failed to leave programming mode")
			ret = self.serial
			self.serial = None
			return ret
		return None
	
	def isConnected(self):
		return self.serial is not None
	
	def sendISP(self, data):
		recv = self.sendMessage([0x1D, 4, 4, 0, data[0], data[1], data[2], data[3]])
		return recv[2:6]
	
	def writeFlash(self, flashData):
		#Set load addr to 0, in case we have more then 64k flash we need to enable the address extension
		pageSize = self.chip['pageSize'] * 2
		flashSize = pageSize * self.chip['pageCount']
		if flashSize > 0xFFFF:
			self.sendMessage([0x06, 0x80, 0x00, 0x00, 0x00])
		else:
			self.sendMessage([0x06, 0x00, 0x00, 0x00, 0x00])
		
		loadCount = (len(flashData) + pageSize - 1) / pageSize
		for i in xrange(0, loadCount):
			recv = self.sendMessage([0x13, pageSize >> 8, pageSize & 0xFF, 0xc1, 0x0a, 0x40, 0x4c, 0x20, 0x00, 0x00] + flashData[(i * pageSize):(i * pageSize + pageSize)])
			if self.progressCallback != None:
				self.progressCallback(i + 1, loadCount*2)
	
	def verifyFlash(self, flashData):
		#Set load addr to 0, in case we have more then 64k flash we need to enable the address extension
		flashSize = self.chip['pageSize'] * 2 * self.chip['pageCount']
		if flashSize > 0xFFFF:
			self.sendMessage([0x06, 0x80, 0x00, 0x00, 0x00])
		else:
			self.sendMessage([0x06, 0x00, 0x00, 0x00, 0x00])
		
		loadCount = (len(flashData) + 0xFF) / 0x100
		for i in xrange(0, loadCount):
			recv = self.sendMessage([0x14, 0x01, 0x00, 0x20])[2:0x102]
			if self.progressCallback != None:
				self.progressCallback(loadCount + i + 1, loadCount*2)
			for j in xrange(0, 0x100):
				if i * 0x100 + j < len(flashData) and flashData[i * 0x100 + j] != recv[j]:
					raise ispBase.IspError('Verify error at: 0x%x' % (i * 0x100 + j))

	def sendMessage(self, data):
		message = struct.pack(">BBHB", 0x1B, self.seq, len(data), 0x0E)
		for c in data:
			message += struct.pack(">B", c)
		checksum = 0
		for c in message:
			checksum ^= ord(c)
		message += struct.pack(">B", checksum)
		try:
			self.serial.write(message)
			self.serial.flush()
		except Serial.SerialTimeoutException:
			raise ispBase.IspError('Serial send timeout')
		self.seq = (self.seq + 1) & 0xFF
		return self.recvMessage()
	
	def recvMessage(self):
		state = 'Start'
		checksum = 0
		while True:
			s = self.serial.read()
			if len(s) < 1:
				raise ispBase.IspError("Timeout")
			b = struct.unpack(">B", s)[0]
			checksum ^= b
			#print(hex(b))
			if state == 'Start':
				if b == 0x1B:
					state = 'GetSeq'
					checksum = 0x1B
			elif state == 'GetSeq':
				state = 'MsgSize1'
			elif state == 'MsgSize1':
				msgSize = b << 8
				state = 'MsgSize2'
			elif state == 'MsgSize2':
				msgSize |= b
				state = 'Token'
			elif state == 'Token':
				if b != 0x0E:
					state = 'Start'
				else:
					state = 'Data'
					data = []
			elif state == 'Data':
				data.append(b)
				if len(data) == msgSize:
					state = 'Checksum'
			elif state == 'Checksum':
				if checksum != 0:
					state = 'Start'
				else:
					return data

def portList():
	ret = []
	import _winreg
	key=_winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE,"HARDWARE\\DEVICEMAP\\SERIALCOMM")
	i=0
	while True:
		try:
			values = _winreg.EnumValue(key, i)
		except:
			return ret
		if 'USBSER' in values[0]:
			ret.append(values[1])
		i+=1
	return ret

def runProgrammer(port, filename):
	""" Run an STK500v2 program on serial port 'port' and write 'filename' into flash. """
	programmer = Stk500v2()
	programmer.connect(port = port)
	programmer.programChip(intelHex.readHex(filename))
	programmer.close()

def main():
	""" Entry point to call the stk500v2 programmer from the commandline. """
	import threading
	if sys.argv[1] == 'AUTO':
		print portList()
		for port in portList():
			threading.Thread(target=runProgrammer, args=(port,sys.argv[2])).start()
			time.sleep(5)
	else:
		programmer = Stk500v2()
		programmer.connect(port = sys.argv[1])
		programmer.programChip(intelHex.readHex(sys.argv[2]))
		sys.exit(1)

if __name__ == '__main__':
	main()

########NEW FILE########
__FILENAME__ = cura
#!/usr/bin/python
"""
This page is in the table of contents.
==Overview==
===Introduction===
Cura is a AGPL tool chain to generate a GCode path for 3D printing. Older versions of Cura where based on Skeinforge.
Versions up from 13.05 are based on a C++ engine called CuraEngine.
"""
__copyright__ = "Copyright (C) 2013 David Braam - Released under terms of the AGPLv3 License"

from optparse import OptionParser

from Cura.util import profile

def main():
	"""
	Main Cura entry point. Parses arguments, and starts GUI or slicing process depending on the arguments.
	"""
	parser = OptionParser(usage="usage: %prog [options] <filename>.stl")
	parser.add_option("-i", "--ini", action="store", type="string", dest="profileini",
		help="Load settings from a profile ini file")
	parser.add_option("-r", "--print", action="store", type="string", dest="printfile",
		help="Open the printing interface, instead of the normal cura interface.")
	parser.add_option("-p", "--profile", action="store", type="string", dest="profile",
		help="Internal option, do not use!")
	parser.add_option("-s", "--slice", action="store_true", dest="slice",
		help="Slice the given files instead of opening them in Cura")
	parser.add_option("-o", "--output", action="store", type="string", dest="output",
		help="path to write sliced file to")
	parser.add_option("--serialCommunication", action="store", type="string", dest="serialCommunication",
		help="Start commandline serial monitor")

	(options, args) = parser.parse_args()

	if options.serialCommunication:
		from Cura import serialCommunication
		port, baud = options.serialCommunication.split(':')
		serialCommunication.startMonitor(port, baud)
		return

	print "load preferences from " + profile.getPreferencePath()
	profile.loadPreferences(profile.getPreferencePath())

	if options.profile is not None:
		profile.setProfileFromString(options.profile)
	elif options.profileini is not None:
		profile.loadProfile(options.profileini)
	else:
		profile.loadProfile(profile.getDefaultProfilePath(), True)

	if options.printfile is not None:
		from Cura.gui import printWindow
		printWindow.startPrintInterface(options.printfile)
	elif options.slice is not None:
		from Cura.util import sliceEngine
		from Cura.util import objectScene
		from Cura.util import meshLoader
		import shutil

		def commandlineProgressCallback(progress):
			if progress >= 0:
				#print 'Preparing: %d%%' % (progress * 100)
				pass
		scene = objectScene.Scene()
		scene.updateMachineDimensions()
		engine = sliceEngine.Engine(commandlineProgressCallback)
		for m in meshLoader.loadMeshes(args[0]):
			scene.add(m)
		engine.runEngine(scene)
		engine.wait()

		if not options.output:
			options.output = args[0] + profile.getGCodeExtension()
		with open(options.output, "wb") as f:
			f.write(engine.getResult().getGCode())
		print 'GCode file saved : %s' % options.output

		engine.cleanup()
	else:
		from Cura.gui import app
		app.CuraApp(args).MainLoop()

if __name__ == '__main__':
	main()

########NEW FILE########
__FILENAME__ = doctest
"""
A helper file to check which parts of the code have documentation and which are lacking documentation.
This because much of the Cura code is currently undocumented which needs to be improved.
"""
import os
import traceback
import glob
import sys
import inspect
import types
import random

def treeWalk(moduleList, dirname, fnames):
	""" Callback from the os.path.walk function, see if the given path is a module and import it to put it in the moduleList """
	dirname = dirname.replace("\\", ".").replace("/", ".")
	if dirname.startswith('Cura.gui'):
		return
	if dirname == 'Cura.util.pymclevel':
		return
	if dirname == 'Cura.util.Power':
		return
	if dirname == 'Cura.plugins':
		return
	if dirname == 'Cura.resouces':
		return
	for moduleName in filter(lambda f: f.endswith('.py'), fnames):
		moduleName = moduleName[:-3]
		if moduleName == '__init__':
			continue
		fullName = '%s.%s' % (dirname, moduleName)
		try:
			module = __import__(fullName, fromlist=['Cura'], level=1)
			moduleList.append(module)
		except:
			#traceback.print_exc()
			print "Failed to load: %s" % (fullName)

def main():
	"""
	Main doctest function.
	Calculate how many things are documented and not documented yet.
	And report a random selection of undocumented functions/ modules.
	"""
	moduleList = []
	os.path.walk("Cura", treeWalk, moduleList)
	moduleDocCount = 0
	functionCount = 0
	functionDocCount = 0
	memberCount = 0
	memberDocCount = 0
	typeCount = 0
	typeDocCount = 0
	undocList = []
	for module in moduleList:
		if inspect.getdoc(module):
			moduleDocCount += 1
		else:
			undocList.append(module.__name__)
		for name in dir(module):
			a = getattr(module, name)
			try:
				if not inspect.getfile(a).startswith('Cura'):
					continue
			except:
				continue
			if type(a) is types.FunctionType:
				functionCount += 1
				if inspect.getdoc(a):
					functionDocCount += 1
				else:
					undocList.append('%s.%s' % (module.__name__, name))
			elif type(a) is types.TypeType:
				typeCount += 1
				if inspect.getdoc(a):
					typeDocCount += 1
				else:
					undocList.append('%s.%s' % (module.__name__, name))
				for name2 in dir(a):
					a2 = getattr(a, name2)
					if type(a2) is types.MethodType:
						if hasattr(a.__bases__[0], name2):
							continue
						memberCount += 1
						if inspect.getdoc(a2):
							memberDocCount += 1
						# else:
						# 	undocList.append('%s.%s.%s' % (module.__name__, name, name2))

	print '%d/%d modules have documentation.' % (moduleDocCount, len(moduleList))
	print '%d/%d types have documentation.' % (typeDocCount, typeCount)
	print '%d/%d functions have documentation.' % (functionDocCount, functionCount)
	print '%d/%d member functions have documentation.' % (memberDocCount, memberCount)
	print '%.1f%% documented.' % (float(moduleDocCount + functionDocCount + typeDocCount + memberDocCount) / float(len(moduleList) + functionCount + typeCount + memberCount) * 100.0)
	print ''
	print 'You might want to document:'
	for n in xrange(0, 10):
		print random.Random().choice(undocList)

if __name__ == '__main__':
	main()

########NEW FILE########
__FILENAME__ = aboutWindow
__copyright__ = "Copyright (C) 2013 David Braam - Released under terms of the AGPLv3 License"

import wx
import platform

class aboutWindow(wx.Frame):
	def __init__(self):
		super(aboutWindow, self).__init__(None, title="About", style = wx.DEFAULT_DIALOG_STYLE)

		wx.EVT_CLOSE(self, self.OnClose)

		p = wx.Panel(self)
		self.panel = p
		s = wx.BoxSizer()
		self.SetSizer(s)
		s.Add(p, flag=wx.ALL, border=15)
		s = wx.BoxSizer(wx.VERTICAL)
		p.SetSizer(s)

		title = wx.StaticText(p, -1, 'Cura')
		title.SetFont(wx.Font(18, wx.SWISS, wx.NORMAL, wx.BOLD))
		s.Add(title, flag=wx.ALIGN_CENTRE|wx.EXPAND|wx.BOTTOM, border=5)

		s.Add(wx.StaticText(p, -1, 'End solution for Open Source Fused Filament Fabrication 3D printing.'))
		s.Add(wx.StaticText(p, -1, 'Cura is currently developed and maintained by Ultimaker.'))

		s.Add(wx.StaticText(p, -1, 'Cura is build with the following components:'), flag=wx.TOP, border=10)
		self.addComponent('Cura', 'Graphical user interface', 'AGPLv3', 'https://github.com/daid/Cura')
		self.addComponent('CuraEngine', 'GCode Generator', 'AGPLv3', 'https://github.com/Ultimaker/CuraEngine')
		self.addComponent('Clipper', 'Polygon clipping library', 'Boost', 'http://www.angusj.com/delphi/clipper.php')

		self.addComponent('Python 2.7', 'Framework', 'Python', 'http://python.org/')
		self.addComponent('wxPython', 'GUI Framework', 'wxWindows', 'http://www.wxpython.org/')
		self.addComponent('PyOpenGL', '3D Rendering Framework', 'BSD', 'http://pyopengl.sourceforge.net/')
		self.addComponent('PySerial', 'Serial communication library', 'Python license', 'http://pyserial.sourceforge.net/')
		self.addComponent('NumPy', 'Support library for faster math', 'BSD', 'http://www.numpy.org/')
		if platform.system() == "Windows":
			self.addComponent('VideoCapture', 'Library for WebCam capture on windows', 'LGPLv2.1', 'http://videocapture.sourceforge.net/')
			#self.addComponent('ffmpeg', 'Support for making timelaps video files', 'GPL', 'http://www.ffmpeg.org/')
			self.addComponent('comtypes', 'Library to help with windows taskbar features on Windows 7', 'MIT', 'http://starship.python.net/crew/theller/comtypes/')
			self.addComponent('EjectMedia', 'Utility to safe-remove SD cards', 'Freeware', 'http://www.uwe-sieber.de/english.html')
		self.addComponent('Pymclevel', 'Python library for reading Minecraft levels.', 'ISC', 'https://github.com/mcedit/pymclevel')

		#Translations done by:
		#Dutch: Charlotte Jansen
		#German: Gregor Luetolf, Lars Potter
		#Polish: Piotr Paczynski
		#French: Jeremie Francois
		#Spanish: Jose Gemez
		self.Fit()

	def addComponent(self, name, description, license, url):
		p = self.panel
		s = p.GetSizer()
		s.Add(wx.StaticText(p, -1, '* %s - %s' % (name, description)), flag=wx.TOP, border=5)
		s.Add(wx.StaticText(p, -1, '   License: %s - Website: %s' % (license, url)))

	def OnClose(self, e):
		self.Destroy()

########NEW FILE########
__FILENAME__ = alterationPanel
__copyright__ = "Copyright (C) 2013 David Braam - Released under terms of the AGPLv3 License"

import wx, wx.stc

from Cura.gui.util import gcodeTextArea
from Cura.util import profile
#Panel to change the start & endcode of the gcode.
class alterationPanel(wx.Panel):
	def __init__(self, parent, callback):
		wx.Panel.__init__(self, parent,-1)

		self.callback = callback
		self.alterationFileList = ['start.gcode', 'end.gcode']#, 'nextobject.gcode', 'replace.csv'
		if int(profile.getMachineSetting('extruder_amount')) > 1:
			self.alterationFileList += ['preSwitchExtruder.gcode', 'postSwitchExtruder.gcode']
			self.alterationFileList += ['start2.gcode', 'end2.gcode']
		if int(profile.getMachineSetting('extruder_amount')) > 2:
			self.alterationFileList += ['start3.gcode', 'end3.gcode']
		if int(profile.getMachineSetting('extruder_amount')) > 3:
			self.alterationFileList += ['start4.gcode', 'end4.gcode']
		self.currentFile = None

		self.textArea = gcodeTextArea.GcodeTextArea(self)
		self.list = wx.ListBox(self, choices=self.alterationFileList, style=wx.LB_SINGLE)
		self.list.SetSelection(0)
		self.Bind(wx.EVT_LISTBOX, self.OnSelect, self.list)
		self.textArea.Bind(wx.EVT_KILL_FOCUS, self.OnFocusLost, self.textArea)
		self.textArea.Bind(wx.stc.EVT_STC_CHANGE, self.OnFocusLost, self.textArea)
		
		sizer = wx.GridBagSizer()
		sizer.Add(self.list, (0,0), span=(5,1), flag=wx.EXPAND)
		sizer.Add(self.textArea, (5,0), span=(5,1), flag=wx.EXPAND)
		sizer.AddGrowableCol(0)
		sizer.AddGrowableRow(0)
		sizer.AddGrowableRow(5)
		sizer.AddGrowableRow(6)
		sizer.AddGrowableRow(7)
		self.SetSizer(sizer)
		
		self.loadFile(self.alterationFileList[self.list.GetSelection()])
		self.currentFile = self.list.GetSelection()

	def OnSelect(self, e):
		self.loadFile(self.alterationFileList[self.list.GetSelection()])
		self.currentFile = self.list.GetSelection()

	def loadFile(self, filename):
		self.textArea.SetValue(profile.getAlterationFile(filename))

	def OnFocusLost(self, e):
		if self.currentFile == self.list.GetSelection():
			profile.setAlterationFile(self.alterationFileList[self.list.GetSelection()], self.textArea.GetValue())
			self.callback()

	def updateProfileToControls(self):
		self.OnSelect(None)

########NEW FILE########
__FILENAME__ = app
__copyright__ = "Copyright (C) 2013 David Braam - Released under terms of the AGPLv3 License"

import sys
import os
import platform
import shutil
import glob
import warnings

try:
    #Only try to import the _core to save import time
    import wx._core
except ImportError:
    import wx


class CuraApp(wx.App):
	def __init__(self, files):
		if platform.system() == "Windows" and not 'PYCHARM_HOSTED' in os.environ:
			super(CuraApp, self).__init__(redirect=True, filename='output.txt')
		else:
			super(CuraApp, self).__init__(redirect=False)

		self.mainWindow = None
		self.splash = None
		self.loadFiles = files

		self.Bind(wx.EVT_ACTIVATE_APP, self.OnActivate)

		if sys.platform.startswith('win'):
			#Check for an already running instance, if another instance is running load files in there
			from Cura.util import version
			from ctypes import windll
			import ctypes
			import socket
			import threading

			portNr = 0xCA00 + sum(map(ord, version.getVersion(False)))
			if len(files) > 0:
				try:
					other_hwnd = windll.user32.FindWindowA(None, ctypes.c_char_p('Cura - ' + version.getVersion()))
					if other_hwnd != 0:
						sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
						sock.sendto('\0'.join(files), ("127.0.0.1", portNr))

						windll.user32.SetForegroundWindow(other_hwnd)
						return
				except:
					pass

			socketListener = threading.Thread(target=self.Win32SocketListener, args=(portNr,))
			socketListener.daemon = True
			socketListener.start()

		if sys.platform.startswith('darwin'):
			#Do not show a splashscreen on OSX, as by Apple guidelines
			self.afterSplashCallback()
		else:
			from Cura.gui import splashScreen
			self.splash = splashScreen.splashScreen(self.afterSplashCallback)

	def MacOpenFile(self, path):
		try:
			self.mainWindow.OnDropFiles([path])
		except Exception as e:
			warnings.warn("File at {p} cannot be read: {e}".format(p=path, e=str(e)))

	def MacReopenApp(self, event):
		self.GetTopWindow().Raise()

	def MacHideApp(self, event):
		self.GetTopWindow().Show(False)

	def MacNewFile(self):
		pass

	def MacPrintFile(self, file_path):
		pass

	def OnActivate(self, e):
		if e.GetActive():
			self.GetTopWindow().Raise()
		e.Skip()

	def Win32SocketListener(self, port):
		import socket
		try:
			sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
			sock.bind(("127.0.0.1", port))
			while True:
				data, addr = sock.recvfrom(2048)
				self.mainWindow.OnDropFiles(data.split('\0'))
		except:
			pass

	def afterSplashCallback(self):
		#These imports take most of the time and thus should be done after showing the splashscreen
		import webbrowser
		from Cura.gui import mainWindow
		from Cura.gui import configWizard
		from Cura.gui import newVersionDialog
		from Cura.util import profile
		from Cura.util import resources
		from Cura.util import version

		resources.setupLocalization(profile.getPreference('language'))  # it's important to set up localization at very beginning to install _

		#If we do not have preferences yet, try to load it from a previous Cura install
		if profile.getMachineSetting('machine_type') == 'unknown':
			try:
				otherCuraInstalls = profile.getAlternativeBasePaths()
				otherCuraInstalls.sort()
				if len(otherCuraInstalls) > 0:
					profile.loadPreferences(os.path.join(otherCuraInstalls[-1], 'preferences.ini'))
					profile.loadProfile(os.path.join(otherCuraInstalls[-1], 'current_profile.ini'))
			except:
				import traceback
				print traceback.print_exc()

		#If we haven't run it before, run the configuration wizard.
		if profile.getMachineSetting('machine_type') == 'unknown':
			if platform.system() == "Windows":
				exampleFile = os.path.normpath(os.path.join(resources.resourceBasePath, 'example', 'UltimakerRobot_support.stl'))
			else:
				#Check if we need to copy our examples
				exampleFile = os.path.expanduser('~/CuraExamples/UltimakerRobot_support.stl')
				if not os.path.isfile(exampleFile):
					try:
						os.makedirs(os.path.dirname(exampleFile))
					except:
						pass
					for filename in glob.glob(os.path.normpath(os.path.join(resources.resourceBasePath, 'example', '*.*'))):
						shutil.copy(filename, os.path.join(os.path.dirname(exampleFile), os.path.basename(filename)))
			self.loadFiles = [exampleFile]
			if self.splash is not None:
				self.splash.Show(False)
			configWizard.configWizard()

		if profile.getPreference('check_for_updates') == 'True':
			newVersion = version.checkForNewerVersion()
			if newVersion is not None:
				if self.splash is not None:
					self.splash.Show(False)
				if wx.MessageBox(_("A new version of Cura is available, would you like to download?"), _("New version available"), wx.YES_NO | wx.ICON_INFORMATION) == wx.YES:
					webbrowser.open(newVersion)
					return
		if profile.getMachineSetting('machine_name') == '':
			return
		self.mainWindow = mainWindow.mainWindow()
		if self.splash is not None:
			self.splash.Show(False)
		self.SetTopWindow(self.mainWindow)
		self.mainWindow.Show()
		self.mainWindow.OnDropFiles(self.loadFiles)
		if profile.getPreference('last_run_version') != version.getVersion(False):
			profile.putPreference('last_run_version', version.getVersion(False))
			newVersionDialog.newVersionDialog().Show()

		setFullScreenCapable(self.mainWindow)

		if sys.platform.startswith('darwin'):
			wx.CallAfter(self.StupidMacOSWorkaround)

	def StupidMacOSWorkaround(self):
		"""
		On MacOS for some magical reason opening new frames does not work until you opened a new modal dialog and closed it.
		If we do this from software, then, as if by magic, the bug which prevents opening extra frames is gone.
		"""
		dlg = wx.Dialog(None)
		wx.PostEvent(dlg, wx.CommandEvent(wx.EVT_CLOSE.typeId))
		dlg.ShowModal()
		dlg.Destroy()

if platform.system() == "Darwin": #Mac magic. Dragons live here. THis sets full screen options.
	try:
		import ctypes, objc
		_objc = ctypes.PyDLL(objc._objc.__file__)

		# PyObject *PyObjCObject_New(id objc_object, int flags, int retain)
		_objc.PyObjCObject_New.restype = ctypes.py_object
		_objc.PyObjCObject_New.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int]

		def setFullScreenCapable(frame):
			frameobj = _objc.PyObjCObject_New(frame.GetHandle(), 0, 1)

			NSWindowCollectionBehaviorFullScreenPrimary = 1 << 7
			window = frameobj.window()
			newBehavior = window.collectionBehavior() | NSWindowCollectionBehaviorFullScreenPrimary
			window.setCollectionBehavior_(newBehavior)
	except:
		def setFullScreenCapable(frame):
			pass

else:
	def setFullScreenCapable(frame):
		pass

########NEW FILE########
__FILENAME__ = configBase
from __future__ import division
__copyright__ = "Copyright (C) 2013 David Braam - Released under terms of the AGPLv3 License"

import wx, wx.lib.stattext, types
from wx.lib.agw import floatspin

from Cura.util import validators
from Cura.util import profile

class configPanelBase(wx.Panel):
	"A base class for configuration dialogs. Handles creation of settings, and popups"
	def __init__(self, parent, changeCallback = None):
		super(configPanelBase, self).__init__(parent)
		
		self.settingControlList = []
		
		#Create the popup window
		self.popup = wx.PopupWindow(self, flags=wx.BORDER_SIMPLE)
		self.popup.SetBackgroundColour(wx.SystemSettings.GetColour(wx.SYS_COLOUR_INFOBK))
		self.popup.setting = None
		self.popup.text = wx.StaticText(self.popup, -1, '')
		self.popup.text.SetForegroundColour(wx.SystemSettings.GetColour(wx.SYS_COLOUR_INFOTEXT))
		self.popup.sizer = wx.BoxSizer()
		self.popup.sizer.Add(self.popup.text, flag=wx.EXPAND|wx.ALL, border=1)
		self.popup.SetSizer(self.popup.sizer)

		self._callback = changeCallback
	
	def CreateConfigTab(self, nb, name):
		leftConfigPanel, rightConfigPanel, configPanel = self.CreateConfigPanel(nb)
		nb.AddPage(configPanel, name)
		return leftConfigPanel, rightConfigPanel
	
	def CreateConfigPanel(self, parent):
		configPanel = wx.Panel(parent);
		leftConfigPanel = wx.Panel(configPanel)
		rightConfigPanel = wx.Panel(configPanel)

		sizer = wx.GridBagSizer(2, 2)
		leftConfigPanel.SetSizer(sizer)
		sizer = wx.GridBagSizer(2, 2)
		rightConfigPanel.SetSizer(sizer)

		sizer = wx.BoxSizer(wx.HORIZONTAL)
		configPanel.SetSizer(sizer)
		sizer.Add(leftConfigPanel, border=35, flag=wx.RIGHT)
		sizer.Add(rightConfigPanel)
		leftConfigPanel.main = self
		rightConfigPanel.main = self
		return leftConfigPanel, rightConfigPanel, configPanel

	def CreateDynamicConfigTab(self, nb, name):
		configPanel = wx.lib.scrolledpanel.ScrolledPanel(nb)	
		#configPanel = wx.Panel(nb);
		leftConfigPanel = wx.Panel(configPanel)
		rightConfigPanel = wx.Panel(configPanel)

		sizer = wx.GridBagSizer(2, 2)
		leftConfigPanel.SetSizer(sizer)
		#sizer.AddGrowableCol(1)

		sizer = wx.GridBagSizer(2, 2)
		rightConfigPanel.SetSizer(sizer)
		#sizer.AddGrowableCol(1)

		sizer = wx.BoxSizer(wx.HORIZONTAL)
		sizer.Add(leftConfigPanel, proportion=1, border=35, flag=wx.EXPAND)
		sizer.Add(rightConfigPanel, proportion=1, flag=wx.EXPAND)
		configPanel.SetSizer(sizer)

		configPanel.SetAutoLayout(1)
		configPanel.SetupScrolling(scroll_x=False, scroll_y=True)

		leftConfigPanel.main = self
		rightConfigPanel.main = self

		configPanel.leftPanel = leftConfigPanel
		configPanel.rightPanel = rightConfigPanel

		nb.AddPage(configPanel, name)

		return leftConfigPanel, rightConfigPanel, configPanel

	def OnPopupDisplay(self, setting):
		self.popup.setting = setting
		self.UpdatePopup(setting)
		self.popup.Show(True)
		
	def OnPopupHide(self, e):
		self.popup.Show(False)
	
	def UpdatePopup(self, setting):
		if self.popup.setting == setting:
			if setting.validationMsg != '':
				self.popup.text.SetLabel(setting.validationMsg + '\n\n' + setting.setting.getTooltip())
			else:
				self.popup.text.SetLabel(setting.setting.getTooltip())
			self.popup.text.Wrap(350)
			self.popup.Fit()
			x, y = setting.ctrl.ClientToScreenXY(0, 0)
			sx, sy = setting.ctrl.GetSizeTuple()
			#if platform.system() == "Windows":
			#	for some reason, under windows, the popup is relative to the main window... in some cases. (Wierd ass bug)
			#	wx, wy = self.ClientToScreenXY(0, 0)
			#	x -= wx
			#	y -= wy
			self.popup.SetPosition((x, y+sy))
	
	def updateProfileToControls(self):
		"Update the configuration wx controls to show the new configuration settings"
		for setting in self.settingControlList:
			setting.SetValue(setting.setting.getValue())
		self.Update()

	def _validate(self):
		for setting in self.settingControlList:
			setting._validate()
		if self._callback is not None:
			self._callback()

	def getLabelColumnWidth(self, panel):
		maxWidth = 0
		for child in panel.GetChildren():
			if isinstance(child, wx.lib.stattext.GenStaticText):
				maxWidth = max(maxWidth, child.GetSize()[0])
		return maxWidth
	
	def setLabelColumnWidth(self, panel, width):
		for child in panel.GetChildren():
			if isinstance(child, wx.lib.stattext.GenStaticText):
				size = child.GetSize()
				size[0] = width
				child.SetBestSize(size)
	
class TitleRow(object):
	def __init__(self, panel, name):
		"Add a title row to the configuration panel"
		sizer = panel.GetSizer()
		x = sizer.GetRows()
		self.title = wx.StaticText(panel, -1, name.replace('&', '&&'))
		self.title.SetFont(wx.Font(wx.SystemSettings.GetFont(wx.SYS_ANSI_VAR_FONT).GetPointSize(), wx.FONTFAMILY_DEFAULT, wx.NORMAL, wx.FONTWEIGHT_BOLD))
		sizer.Add(self.title, (x,0), (1,3), flag=wx.EXPAND|wx.TOP|wx.LEFT, border=10)
		sizer.Add(wx.StaticLine(panel), (x+1,0), (1,3), flag=wx.EXPAND|wx.LEFT,border=10)
		sizer.SetRows(x + 2)

class SettingRow(object):
	def __init__(self, panel, configName, valueOverride = None, index = None):
		"Add a setting to the configuration panel"
		sizer = panel.GetSizer()
		x = sizer.GetRows()
		y = 0
		flag = 0

		self.setting = profile.settingsDictionary[configName]
		self.settingIndex = index
		self.validationMsg = ''
		self.panel = panel

		self.label = wx.lib.stattext.GenStaticText(panel, -1, self.setting.getLabel())
		self.label.Bind(wx.EVT_ENTER_WINDOW, self.OnMouseEnter)
		self.label.Bind(wx.EVT_LEAVE_WINDOW, self.OnMouseExit)

		#if self.setting.getType() is types.FloatType and False:
		#	digits = 0
		#	while 1 / pow(10, digits) > defaultValue:
		#		digits += 1
		#	self.ctrl = floatspin.FloatSpin(panel, -1, value=float(getSettingFunc(configName)), increment=defaultValue, digits=digits, min_val=0.0)
		#	self.ctrl.Bind(floatspin.EVT_FLOATSPIN, self.OnSettingChange)
		#	flag = wx.EXPAND
		if self.setting.getType() is types.BooleanType:
			self.ctrl = wx.CheckBox(panel, -1, style=wx.ALIGN_RIGHT)
			self.SetValue(self.setting.getValue(self.settingIndex))
			self.ctrl.Bind(wx.EVT_CHECKBOX, self.OnSettingChange)
		elif valueOverride is not None and valueOverride is wx.Colour:
			self.ctrl = wx.ColourPickerCtrl(panel, -1)
			self.SetValue(self.setting.getValue(self.settingIndex))
			self.ctrl.Bind(wx.EVT_COLOURPICKER_CHANGED, self.OnSettingChange)
		elif type(self.setting.getType()) is list or valueOverride is not None:
			value = self.setting.getValue(self.settingIndex)
			choices = self.setting.getType()
			if valueOverride is not None:
				choices = valueOverride
			self._englishChoices = choices[:]
			if value not in choices and len(choices) > 0:
				value = choices[0]
			for n in xrange(0, len(choices)):
				choices[n] = _(choices[n])
			value = _(value)
			self.ctrl = wx.ComboBox(panel, -1, value, choices=choices, style=wx.CB_DROPDOWN|wx.CB_READONLY)
			self.ctrl.Bind(wx.EVT_COMBOBOX, self.OnSettingChange)
			self.ctrl.Bind(wx.EVT_LEFT_DOWN, self.OnMouseExit)
			flag = wx.EXPAND
		else:
			self.ctrl = wx.TextCtrl(panel, -1, self.setting.getValue(self.settingIndex))
			self.ctrl.Bind(wx.EVT_TEXT, self.OnSettingChange)
			flag = wx.EXPAND

		sizer.Add(self.label, (x,y), flag=wx.ALIGN_CENTER_VERTICAL|wx.LEFT,border=10)
		sizer.Add(self.ctrl, (x,y+1), flag=wx.ALIGN_BOTTOM|flag)
		sizer.SetRows(x+1)

		self.ctrl.Bind(wx.EVT_ENTER_WINDOW, self.OnMouseEnter)
		self.ctrl.Bind(wx.EVT_LEAVE_WINDOW, self.OnMouseExit)
		if isinstance(self.ctrl, floatspin.FloatSpin):
			self.ctrl.GetTextCtrl().Bind(wx.EVT_ENTER_WINDOW, self.OnMouseEnter)
			self.ctrl.GetTextCtrl().Bind(wx.EVT_LEAVE_WINDOW, self.OnMouseExit)
			self.defaultBGColour = self.ctrl.GetTextCtrl().GetBackgroundColour()
		else:
			self.defaultBGColour = self.ctrl.GetBackgroundColour()
		
		panel.main.settingControlList.append(self)

	def OnMouseEnter(self, e):
		self.panel.main.OnPopupDisplay(self)

	def OnMouseExit(self, e):
		self.panel.main.OnPopupHide(self)
		e.Skip()

	def OnSettingChange(self, e):
		self.setting.setValue(self.GetValue(), self.settingIndex)
		self.panel.main._validate()

	def _validate(self):
		result, msg = self.setting.validate()

		ctrl = self.ctrl
		if isinstance(ctrl, floatspin.FloatSpin):
			ctrl = ctrl.GetTextCtrl()
		if result == validators.ERROR:
			ctrl.SetBackgroundColour('Red')
		elif result == validators.WARNING:
			ctrl.SetBackgroundColour('Yellow')
		else:
			ctrl.SetBackgroundColour(self.defaultBGColour)
		ctrl.Refresh()

		self.validationMsg = msg
		self.panel.main.UpdatePopup(self)

	def GetValue(self):
		if isinstance(self.ctrl, wx.ColourPickerCtrl):
			return str(self.ctrl.GetColour().GetAsString(wx.C2S_HTML_SYNTAX))
		elif isinstance(self.ctrl, wx.ComboBox):
			value = str(self.ctrl.GetValue())
			for ret in self._englishChoices:
				if _(ret) == value:
					return ret
			return value
		else:
			return str(self.ctrl.GetValue())

	def SetValue(self, value):
		if isinstance(self.ctrl, wx.CheckBox):
			self.ctrl.SetValue(str(value) == "True")
		elif isinstance(self.ctrl, wx.ColourPickerCtrl):
			self.ctrl.SetColour(value)
		elif isinstance(self.ctrl, floatspin.FloatSpin):
			try:
				self.ctrl.SetValue(float(value))
			except ValueError:
				pass
		elif isinstance(self.ctrl, wx.ComboBox):
			self.ctrl.SetValue(_(value))
		else:
			self.ctrl.SetValue(value)

########NEW FILE########
__FILENAME__ = configWizard
__copyright__ = "Copyright (C) 2013 David Braam - Released under terms of the AGPLv3 License"

import os
import webbrowser
import threading
import time
import math

import wx
import wx.wizard

from Cura.gui import firmwareInstall
from Cura.gui import printWindow
from Cura.util import machineCom
from Cura.util import profile
from Cura.util import gcodeGenerator
from Cura.util import resources


class InfoBox(wx.Panel):
	def __init__(self, parent):
		super(InfoBox, self).__init__(parent)
		self.SetBackgroundColour('#FFFF80')

		self.sizer = wx.GridBagSizer(5, 5)
		self.SetSizer(self.sizer)

		self.attentionBitmap = wx.Bitmap(resources.getPathForImage('attention.png'))
		self.errorBitmap = wx.Bitmap(resources.getPathForImage('error.png'))
		self.readyBitmap = wx.Bitmap(resources.getPathForImage('ready.png'))
		self.busyBitmap = [
			wx.Bitmap(resources.getPathForImage('busy-0.png')),
			wx.Bitmap(resources.getPathForImage('busy-1.png')),
			wx.Bitmap(resources.getPathForImage('busy-2.png')),
			wx.Bitmap(resources.getPathForImage('busy-3.png'))
		]

		self.bitmap = wx.StaticBitmap(self, -1, wx.EmptyBitmapRGBA(24, 24, red=255, green=255, blue=255, alpha=1))
		self.text = wx.StaticText(self, -1, '')
		self.extraInfoButton = wx.Button(self, -1, 'i', style=wx.BU_EXACTFIT)
		self.sizer.Add(self.bitmap, pos=(0, 0), flag=wx.ALL, border=5)
		self.sizer.Add(self.text, pos=(0, 1), flag=wx.TOP | wx.BOTTOM | wx.ALIGN_CENTER_VERTICAL, border=5)
		self.sizer.Add(self.extraInfoButton, pos=(0,2), flag=wx.ALL|wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL, border=5)
		self.sizer.AddGrowableCol(1)

		self.extraInfoButton.Show(False)

		self.extraInfoUrl = ''
		self.busyState = None
		self.timer = wx.Timer(self)
		self.Bind(wx.EVT_TIMER, self.doBusyUpdate, self.timer)
		self.Bind(wx.EVT_BUTTON, self.doExtraInfo, self.extraInfoButton)
		self.timer.Start(100)

	def SetInfo(self, info):
		self.SetBackgroundColour('#FFFF80')
		self.text.SetLabel(info)
		self.extraInfoButton.Show(False)
		self.Refresh()

	def SetError(self, info, extraInfoUrl):
		self.extraInfoUrl = extraInfoUrl
		self.SetBackgroundColour('#FF8080')
		self.text.SetLabel(info)
		self.extraInfoButton.Show(True)
		self.Layout()
		self.SetErrorIndicator()
		self.Refresh()

	def SetAttention(self, info):
		self.SetBackgroundColour('#FFFF80')
		self.text.SetLabel(info)
		self.extraInfoButton.Show(False)
		self.SetAttentionIndicator()
		self.Layout()
		self.Refresh()

	def SetBusy(self, info):
		self.SetInfo(info)
		self.SetBusyIndicator()

	def SetBusyIndicator(self):
		self.busyState = 0
		self.bitmap.SetBitmap(self.busyBitmap[self.busyState])

	def doExtraInfo(self, e):
		webbrowser.open(self.extraInfoUrl)

	def doBusyUpdate(self, e):
		if self.busyState is None:
			return
		self.busyState += 1
		if self.busyState >= len(self.busyBitmap):
			self.busyState = 0
		self.bitmap.SetBitmap(self.busyBitmap[self.busyState])

	def SetReadyIndicator(self):
		self.busyState = None
		self.bitmap.SetBitmap(self.readyBitmap)

	def SetErrorIndicator(self):
		self.busyState = None
		self.bitmap.SetBitmap(self.errorBitmap)

	def SetAttentionIndicator(self):
		self.busyState = None
		self.bitmap.SetBitmap(self.attentionBitmap)


class InfoPage(wx.wizard.WizardPageSimple):
	def __init__(self, parent, title):
		wx.wizard.WizardPageSimple.__init__(self, parent)

		sizer = wx.GridBagSizer(5, 5)
		self.sizer = sizer
		self.SetSizer(sizer)

		title = wx.StaticText(self, -1, title)
		title.SetFont(wx.Font(18, wx.SWISS, wx.NORMAL, wx.BOLD))
		sizer.Add(title, pos=(0, 0), span=(1, 2), flag=wx.ALIGN_CENTRE | wx.ALL)
		sizer.Add(wx.StaticLine(self, -1), pos=(1, 0), span=(1, 2), flag=wx.EXPAND | wx.ALL)
		sizer.AddGrowableCol(1)

		self.rowNr = 2

	def AddText(self, info):
		text = wx.StaticText(self, -1, info)
		self.GetSizer().Add(text, pos=(self.rowNr, 0), span=(1, 2), flag=wx.LEFT | wx.RIGHT)
		self.rowNr += 1
		return text

	def AddSeperator(self):
		self.GetSizer().Add(wx.StaticLine(self, -1), pos=(self.rowNr, 0), span=(1, 2), flag=wx.EXPAND | wx.ALL)
		self.rowNr += 1

	def AddHiddenSeperator(self):
		self.AddText("")

	def AddInfoBox(self):
		infoBox = InfoBox(self)
		self.GetSizer().Add(infoBox, pos=(self.rowNr, 0), span=(1, 2), flag=wx.LEFT | wx.RIGHT | wx.EXPAND)
		self.rowNr += 1
		return infoBox

	def AddRadioButton(self, label, style=0):
		radio = wx.RadioButton(self, -1, label, style=style)
		self.GetSizer().Add(radio, pos=(self.rowNr, 0), span=(1, 2), flag=wx.EXPAND | wx.ALL)
		self.rowNr += 1
		return radio

	def AddCheckbox(self, label, checked=False):
		check = wx.CheckBox(self, -1)
		text = wx.StaticText(self, -1, label)
		check.SetValue(checked)
		self.GetSizer().Add(text, pos=(self.rowNr, 0), span=(1, 1), flag=wx.LEFT | wx.RIGHT)
		self.GetSizer().Add(check, pos=(self.rowNr, 1), span=(1, 2), flag=wx.ALL)
		self.rowNr += 1
		return check

	def AddButton(self, label):
		button = wx.Button(self, -1, label)
		self.GetSizer().Add(button, pos=(self.rowNr, 0), span=(1, 2), flag=wx.LEFT)
		self.rowNr += 1
		return button

	def AddDualButton(self, label1, label2):
		button1 = wx.Button(self, -1, label1)
		self.GetSizer().Add(button1, pos=(self.rowNr, 0), flag=wx.RIGHT)
		button2 = wx.Button(self, -1, label2)
		self.GetSizer().Add(button2, pos=(self.rowNr, 1))
		self.rowNr += 1
		return button1, button2

	def AddTextCtrl(self, value):
		ret = wx.TextCtrl(self, -1, value)
		self.GetSizer().Add(ret, pos=(self.rowNr, 0), span=(1, 2), flag=wx.LEFT)
		self.rowNr += 1
		return ret

	def AddLabelTextCtrl(self, info, value):
		text = wx.StaticText(self, -1, info)
		ret = wx.TextCtrl(self, -1, value)
		self.GetSizer().Add(text, pos=(self.rowNr, 0), span=(1, 1), flag=wx.LEFT)
		self.GetSizer().Add(ret, pos=(self.rowNr, 1), span=(1, 1), flag=wx.LEFT)
		self.rowNr += 1
		return ret

	def AddTextCtrlButton(self, value, buttonText):
		text = wx.TextCtrl(self, -1, value)
		button = wx.Button(self, -1, buttonText)
		self.GetSizer().Add(text, pos=(self.rowNr, 0), span=(1, 1), flag=wx.LEFT)
		self.GetSizer().Add(button, pos=(self.rowNr, 1), span=(1, 1), flag=wx.LEFT)
		self.rowNr += 1
		return text, button

	def AddBitmap(self, bitmap):
		bitmap = wx.StaticBitmap(self, -1, bitmap)
		self.GetSizer().Add(bitmap, pos=(self.rowNr, 0), span=(1, 2), flag=wx.LEFT | wx.RIGHT)
		self.rowNr += 1
		return bitmap

	def AddCheckmark(self, label, bitmap):
		check = wx.StaticBitmap(self, -1, bitmap)
		text = wx.StaticText(self, -1, label)
		self.GetSizer().Add(text, pos=(self.rowNr, 0), span=(1, 1), flag=wx.LEFT | wx.RIGHT)
		self.GetSizer().Add(check, pos=(self.rowNr, 1), span=(1, 1), flag=wx.ALL)
		self.rowNr += 1
		return check

	def AllowNext(self):
		return True

	def AllowBack(self):
		return True

	def StoreData(self):
		pass


class FirstInfoPage(InfoPage):
	def __init__(self, parent, addNew):
		if addNew:
			super(FirstInfoPage, self).__init__(parent, _("Add new machine wizard"))
		else:
			super(FirstInfoPage, self).__init__(parent, _("First time run wizard"))
			self.AddText(_("Welcome, and thanks for trying Cura!"))
			self.AddSeperator()
		self.AddText(_("This wizard will help you in setting up Cura for your machine."))
		# self.AddText(_("This wizard will help you with the following steps:"))
		# self.AddText(_("* Configure Cura for your machine"))
		# self.AddText(_("* Optionally upgrade your firmware"))
		# self.AddText(_("* Optionally check if your machine is working safely"))
		# self.AddText(_("* Optionally level your printer bed"))

		#self.AddText('* Calibrate your machine')
		#self.AddText('* Do your first print')

	def AllowBack(self):
		return False


class OtherMachineSelectPage(InfoPage):
	def __init__(self, parent):
		super(OtherMachineSelectPage, self).__init__(parent, "Other machine information")
		self.AddText(_("The following pre-defined machine profiles are available"))
		self.AddText(_("Note that these profiles are not guaranteed to give good results,\nor work at all. Extra tweaks might be required.\nIf you find issues with the predefined profiles,\nor want an extra profile.\nPlease report it at the github issue tracker."))
		self.options = []
		machines = resources.getDefaultMachineProfiles()
		machines.sort()
		for filename in machines:
			name = os.path.splitext(os.path.basename(filename))[0]
			item = self.AddRadioButton(name)
			item.filename = filename
			item.Bind(wx.EVT_RADIOBUTTON, self.OnProfileSelect)
			self.options.append(item)
		self.AddSeperator()
		item = self.AddRadioButton('Custom...')
		item.SetValue(True)
		item.Bind(wx.EVT_RADIOBUTTON, self.OnOtherSelect)

	def OnProfileSelect(self, e):
		wx.wizard.WizardPageSimple.Chain(self, self.GetParent().otherMachineInfoPage)

	def OnOtherSelect(self, e):
		wx.wizard.WizardPageSimple.Chain(self, self.GetParent().customRepRapInfoPage)

	def StoreData(self):
		for option in self.options:
			if option.GetValue():
				profile.loadProfile(option.filename)
				profile.loadMachineSettings(option.filename)

class OtherMachineInfoPage(InfoPage):
	def __init__(self, parent):
		super(OtherMachineInfoPage, self).__init__(parent, "Cura Ready!")
		self.AddText(_("Cura is now ready to be used!"))

class CustomRepRapInfoPage(InfoPage):
	def __init__(self, parent):
		super(CustomRepRapInfoPage, self).__init__(parent, "Custom RepRap information")
		self.AddText(_("RepRap machines can be vastly different, so here you can set your own settings."))
		self.AddText(_("Be sure to review the default profile before running it on your machine."))
		self.AddText(_("If you like a default profile for your machine added,\nthen make an issue on github."))
		self.AddSeperator()
		self.AddText(_("You will have to manually install Marlin or Sprinter firmware."))
		self.AddSeperator()
		self.machineName = self.AddLabelTextCtrl(_("Machine name"), "RepRap")
		self.machineWidth = self.AddLabelTextCtrl(_("Machine width (mm)"), "80")
		self.machineDepth = self.AddLabelTextCtrl(_("Machine depth (mm)"), "80")
		self.machineHeight = self.AddLabelTextCtrl(_("Machine height (mm)"), "55")
		self.nozzleSize = self.AddLabelTextCtrl(_("Nozzle size (mm)"), "0.5")
		self.heatedBed = self.AddCheckbox(_("Heated bed"))
		self.HomeAtCenter = self.AddCheckbox(_("Bed center is 0,0,0 (RoStock)"))

	def StoreData(self):
		profile.putMachineSetting('machine_name', self.machineName.GetValue())
		profile.putMachineSetting('machine_width', self.machineWidth.GetValue())
		profile.putMachineSetting('machine_depth', self.machineDepth.GetValue())
		profile.putMachineSetting('machine_height', self.machineHeight.GetValue())
		profile.putProfileSetting('nozzle_size', self.nozzleSize.GetValue())
		profile.putProfileSetting('wall_thickness', float(profile.getProfileSettingFloat('nozzle_size')) * 2)
		profile.putMachineSetting('has_heated_bed', str(self.heatedBed.GetValue()))
		profile.putMachineSetting('machine_center_is_zero', str(self.HomeAtCenter.GetValue()))
		profile.putMachineSetting('extruder_head_size_min_x', '0')
		profile.putMachineSetting('extruder_head_size_min_y', '0')
		profile.putMachineSetting('extruder_head_size_max_x', '0')
		profile.putMachineSetting('extruder_head_size_max_y', '0')
		profile.putMachineSetting('extruder_head_size_height', '0')
		profile.checkAndUpdateMachineName()

class MachineSelectPage(InfoPage):
	def __init__(self, parent):
		super(MachineSelectPage, self).__init__(parent, _("Select your machine"))
		self.AddText(_("What kind of machine do you have:"))

		self.Ultimaker2Radio = self.AddRadioButton("Ultimaker2", style=wx.RB_GROUP)
		self.Ultimaker2Radio.SetValue(True)
		self.Ultimaker2Radio.Bind(wx.EVT_RADIOBUTTON, self.OnUltimaker2Select)
		self.UltimakerRadio = self.AddRadioButton("Ultimaker Original")
		self.UltimakerRadio.Bind(wx.EVT_RADIOBUTTON, self.OnUltimakerSelect)
		self.OtherRadio = self.AddRadioButton(_("Other (Ex: RepRap, MakerBot)"))
		self.OtherRadio.Bind(wx.EVT_RADIOBUTTON, self.OnOtherSelect)
		self.AddSeperator()
		self.AddText(_("The collection of anonymous usage information helps with the continued improvement of Cura."))
		self.AddText(_("This does NOT submit your models online nor gathers any privacy related information."))
		self.SubmitUserStats = self.AddCheckbox(_("Submit anonymous usage information:"))
		self.AddText(_("For full details see: http://wiki.ultimaker.com/Cura:stats"))
		self.SubmitUserStats.SetValue(True)

	def OnUltimaker2Select(self, e):
		wx.wizard.WizardPageSimple.Chain(self, self.GetParent().ultimaker2ReadyPage)

	def OnUltimakerSelect(self, e):
		wx.wizard.WizardPageSimple.Chain(self, self.GetParent().ultimakerSelectParts)

	def OnOtherSelect(self, e):
		wx.wizard.WizardPageSimple.Chain(self, self.GetParent().otherMachineSelectPage)

	def AllowNext(self):
		wx.wizard.WizardPageSimple.Chain(self, self.GetParent().ultimaker2ReadyPage)
		return True

	def StoreData(self):
		profile.putProfileSetting('retraction_enable', 'True')
		if self.Ultimaker2Radio.GetValue():
			profile.putMachineSetting('machine_width', '230')
			profile.putMachineSetting('machine_depth', '225')
			profile.putMachineSetting('machine_height', '205')
			profile.putMachineSetting('machine_name', 'ultimaker2')
			profile.putMachineSetting('machine_type', 'ultimaker2')
			profile.putMachineSetting('machine_center_is_zero', 'False')
			profile.putMachineSetting('has_heated_bed', 'True')
			profile.putMachineSetting('gcode_flavor', 'UltiGCode')
			profile.putMachineSetting('extruder_head_size_min_x', '40.0')
			profile.putMachineSetting('extruder_head_size_min_y', '10.0')
			profile.putMachineSetting('extruder_head_size_max_x', '60.0')
			profile.putMachineSetting('extruder_head_size_max_y', '30.0')
			profile.putMachineSetting('extruder_head_size_height', '55.0')
			profile.putProfileSetting('nozzle_size', '0.4')
			profile.putProfileSetting('fan_full_height', '5.0')
			profile.putMachineSetting('extruder_offset_x1', '18.0')
			profile.putMachineSetting('extruder_offset_y1', '0.0')
		elif self.UltimakerRadio.GetValue():
			profile.putMachineSetting('machine_width', '205')
			profile.putMachineSetting('machine_depth', '205')
			profile.putMachineSetting('machine_height', '200')
			profile.putMachineSetting('machine_name', 'ultimaker original')
			profile.putMachineSetting('machine_type', 'ultimaker')
			profile.putMachineSetting('machine_center_is_zero', 'False')
			profile.putMachineSetting('gcode_flavor', 'RepRap (Marlin/Sprinter)')
			profile.putProfileSetting('nozzle_size', '0.4')
			profile.putMachineSetting('extruder_head_size_min_x', '75.0')
			profile.putMachineSetting('extruder_head_size_min_y', '18.0')
			profile.putMachineSetting('extruder_head_size_max_x', '18.0')
			profile.putMachineSetting('extruder_head_size_max_y', '35.0')
			profile.putMachineSetting('extruder_head_size_height', '55.0')
		else:
			profile.putMachineSetting('machine_width', '80')
			profile.putMachineSetting('machine_depth', '80')
			profile.putMachineSetting('machine_height', '60')
			profile.putMachineSetting('machine_name', 'reprap')
			profile.putMachineSetting('machine_type', 'reprap')
			profile.putMachineSetting('gcode_flavor', 'RepRap (Marlin/Sprinter)')
			profile.putPreference('startMode', 'Normal')
			profile.putProfileSetting('nozzle_size', '0.5')
		profile.checkAndUpdateMachineName()
		profile.putProfileSetting('wall_thickness', float(profile.getProfileSetting('nozzle_size')) * 2)
		if self.SubmitUserStats.GetValue():
			profile.putPreference('submit_slice_information', 'True')
		else:
			profile.putPreference('submit_slice_information', 'False')


class SelectParts(InfoPage):
	def __init__(self, parent):
		super(SelectParts, self).__init__(parent, _("Select upgraded parts you have"))
		self.AddText(_("To assist you in having better default settings for your Ultimaker\nCura would like to know which upgrades you have in your machine."))
		self.AddSeperator()
		self.springExtruder = self.AddCheckbox(_("Extruder drive upgrade"))
		self.heatedBedKit = self.AddCheckbox(_("Heated printer bed (kit)"))
		self.heatedBed = self.AddCheckbox(_("Heated printer bed (self built)"))
		self.dualExtrusion = self.AddCheckbox(_("Dual extrusion (experimental)"))
		self.AddSeperator()
		self.AddText(_("If you have an Ultimaker bought after october 2012 you will have the\nExtruder drive upgrade. If you do not have this upgrade,\nit is highly recommended to improve reliability."))
		self.AddText(_("This upgrade can be bought from the Ultimaker webshop\nor found on thingiverse as thing:26094"))
		self.springExtruder.SetValue(True)

	def StoreData(self):
		profile.putMachineSetting('ultimaker_extruder_upgrade', str(self.springExtruder.GetValue()))
		if self.heatedBed.GetValue() or self.heatedBedKit.GetValue():
			profile.putMachineSetting('has_heated_bed', 'True')
		else:
			profile.putMachineSetting('has_heated_bed', 'False')
		if self.dualExtrusion.GetValue():
			profile.putMachineSetting('extruder_amount', '2')
			profile.putMachineSetting('machine_depth', '195')
		else:
			profile.putMachineSetting('extruder_amount', '1')
		if profile.getMachineSetting('ultimaker_extruder_upgrade') == 'True':
			profile.putProfileSetting('retraction_enable', 'True')
		else:
			profile.putProfileSetting('retraction_enable', 'False')


class UltimakerFirmwareUpgradePage(InfoPage):
	def __init__(self, parent):
		super(UltimakerFirmwareUpgradePage, self).__init__(parent, _("Upgrade Ultimaker Firmware"))
		self.AddText(_("Firmware is the piece of software running directly on your 3D printer.\nThis firmware controls the step motors, regulates the temperature\nand ultimately makes your printer work."))
		self.AddHiddenSeperator()
		self.AddText(_("The firmware shipping with new Ultimakers works, but upgrades\nhave been made to make better prints, and make calibration easier."))
		self.AddHiddenSeperator()
		self.AddText(_("Cura requires these new features and thus\nyour firmware will most likely need to be upgraded.\nYou will get the chance to do so now."))
		upgradeButton, skipUpgradeButton = self.AddDualButton('Upgrade to Marlin firmware', 'Skip upgrade')
		upgradeButton.Bind(wx.EVT_BUTTON, self.OnUpgradeClick)
		skipUpgradeButton.Bind(wx.EVT_BUTTON, self.OnSkipClick)
		self.AddHiddenSeperator()
		self.AddText(_("Do not upgrade to this firmware if:"))
		self.AddText(_("* You have an older machine based on ATMega1280 (Rev 1 machine)"))
		self.AddText(_("* Have other changes in the firmware"))
#		button = self.AddButton('Goto this page for a custom firmware')
#		button.Bind(wx.EVT_BUTTON, self.OnUrlClick)

	def AllowNext(self):
		return False

	def OnUpgradeClick(self, e):
		if firmwareInstall.InstallFirmware():
			self.GetParent().FindWindowById(wx.ID_FORWARD).Enable()

	def OnSkipClick(self, e):
		self.GetParent().FindWindowById(wx.ID_FORWARD).Enable()
		self.GetParent().ShowPage(self.GetNext())

	def OnUrlClick(self, e):
		webbrowser.open('http://marlinbuilder.robotfuzz.com/')

class UltimakerCheckupPage(InfoPage):
	def __init__(self, parent):
		super(UltimakerCheckupPage, self).__init__(parent, "Ultimaker Checkup")

		self.checkBitmap = wx.Bitmap(resources.getPathForImage('checkmark.png'))
		self.crossBitmap = wx.Bitmap(resources.getPathForImage('cross.png'))
		self.unknownBitmap = wx.Bitmap(resources.getPathForImage('question.png'))
		self.endStopNoneBitmap = wx.Bitmap(resources.getPathForImage('endstop_none.png'))
		self.endStopXMinBitmap = wx.Bitmap(resources.getPathForImage('endstop_xmin.png'))
		self.endStopXMaxBitmap = wx.Bitmap(resources.getPathForImage('endstop_xmax.png'))
		self.endStopYMinBitmap = wx.Bitmap(resources.getPathForImage('endstop_ymin.png'))
		self.endStopYMaxBitmap = wx.Bitmap(resources.getPathForImage('endstop_ymax.png'))
		self.endStopZMinBitmap = wx.Bitmap(resources.getPathForImage('endstop_zmin.png'))
		self.endStopZMaxBitmap = wx.Bitmap(resources.getPathForImage('endstop_zmax.png'))

		self.AddText(
			_("It is a good idea to do a few sanity checks now on your Ultimaker.\nYou can skip these if you know your machine is functional."))
		b1, b2 = self.AddDualButton(_("Run checks"), _("Skip checks"))
		b1.Bind(wx.EVT_BUTTON, self.OnCheckClick)
		b2.Bind(wx.EVT_BUTTON, self.OnSkipClick)
		self.AddSeperator()
		self.commState = self.AddCheckmark(_("Communication:"), self.unknownBitmap)
		self.tempState = self.AddCheckmark(_("Temperature:"), self.unknownBitmap)
		self.stopState = self.AddCheckmark(_("Endstops:"), self.unknownBitmap)
		self.AddSeperator()
		self.infoBox = self.AddInfoBox()
		self.machineState = self.AddText("")
		self.temperatureLabel = self.AddText("")
		self.errorLogButton = self.AddButton(_("Show error log"))
		self.errorLogButton.Show(False)
		self.AddSeperator()
		self.endstopBitmap = self.AddBitmap(self.endStopNoneBitmap)
		self.comm = None
		self.xMinStop = False
		self.xMaxStop = False
		self.yMinStop = False
		self.yMaxStop = False
		self.zMinStop = False
		self.zMaxStop = False

		self.Bind(wx.EVT_BUTTON, self.OnErrorLog, self.errorLogButton)

	def __del__(self):
		if self.comm is not None:
			self.comm.close()

	def AllowNext(self):
		self.endstopBitmap.Show(False)
		return False

	def OnSkipClick(self, e):
		self.GetParent().FindWindowById(wx.ID_FORWARD).Enable()
		self.GetParent().ShowPage(self.GetNext())

	def OnCheckClick(self, e=None):
		self.errorLogButton.Show(False)
		if self.comm is not None:
			self.comm.close()
			del self.comm
			self.comm = None
			wx.CallAfter(self.OnCheckClick)
			return
		self.infoBox.SetBusy(_("Connecting to machine."))
		self.commState.SetBitmap(self.unknownBitmap)
		self.tempState.SetBitmap(self.unknownBitmap)
		self.stopState.SetBitmap(self.unknownBitmap)
		self.checkupState = 0
		self.checkExtruderNr = 0
		self.comm = machineCom.MachineCom(callbackObject=self)

	def OnErrorLog(self, e):
		printWindow.LogWindow('\n'.join(self.comm.getLog()))

	def mcLog(self, message):
		pass

	def mcTempUpdate(self, temp, bedTemp, targetTemp, bedTargetTemp):
		if not self.comm.isOperational():
			return
		if self.checkupState == 0:
			self.tempCheckTimeout = 20
			if temp[self.checkExtruderNr] > 70:
				self.checkupState = 1
				wx.CallAfter(self.infoBox.SetInfo, _("Cooldown before temperature check."))
				self.comm.sendCommand("M104 S0 T%d" % (self.checkExtruderNr))
				self.comm.sendCommand('M104 S0 T%d' % (self.checkExtruderNr))
			else:
				self.startTemp = temp[self.checkExtruderNr]
				self.checkupState = 2
				wx.CallAfter(self.infoBox.SetInfo, _("Checking the heater and temperature sensor."))
				self.comm.sendCommand('M104 S200 T%d' % (self.checkExtruderNr))
				self.comm.sendCommand('M104 S200 T%d' % (self.checkExtruderNr))
		elif self.checkupState == 1:
			if temp < 60:
				self.startTemp = temp[self.checkExtruderNr]
				self.checkupState = 2
				wx.CallAfter(self.infoBox.SetInfo, _("Checking the heater and temperature sensor."))
				self.comm.sendCommand('M104 S200 T%d' % (self.checkExtruderNr))
				self.comm.sendCommand('M104 S200 T%d' % (self.checkExtruderNr))
		elif self.checkupState == 2:
			#print "WARNING, TEMPERATURE TEST DISABLED FOR TESTING!"
			if temp[self.checkExtruderNr] > self.startTemp + 40:
				self.comm.sendCommand('M104 S0 T%d' % (self.checkExtruderNr))
				self.comm.sendCommand('M104 S0 T%d' % (self.checkExtruderNr))
				if self.checkExtruderNr < int(profile.getMachineSetting('extruder_amount')):
					self.checkExtruderNr = 0
					self.checkupState = 3
					wx.CallAfter(self.infoBox.SetAttention, _("Please make sure none of the endstops are pressed."))
					wx.CallAfter(self.endstopBitmap.Show, True)
					wx.CallAfter(self.Layout)
					self.comm.sendCommand('M119')
					wx.CallAfter(self.tempState.SetBitmap, self.checkBitmap)
				else:
					self.checkupState = 0
					self.checkExtruderNr += 1
			else:
				self.tempCheckTimeout -= 1
				if self.tempCheckTimeout < 1:
					self.checkupState = -1
					wx.CallAfter(self.tempState.SetBitmap, self.crossBitmap)
					wx.CallAfter(self.infoBox.SetError, _("Temperature measurement FAILED!"), 'http://wiki.ultimaker.com/Cura:_Temperature_measurement_problems')
					self.comm.sendCommand('M104 S0 T%d' % (self.checkExtruderNr))
					self.comm.sendCommand('M104 S0 T%d' % (self.checkExtruderNr))
		elif self.checkupState >= 3 and self.checkupState < 10:
			self.comm.sendCommand('M119')
		wx.CallAfter(self.temperatureLabel.SetLabel, _("Head temperature: %d") % (temp[self.checkExtruderNr]))

	def mcStateChange(self, state):
		if self.comm is None:
			return
		if self.comm.isOperational():
			wx.CallAfter(self.commState.SetBitmap, self.checkBitmap)
			wx.CallAfter(self.machineState.SetLabel, _("Communication State: %s") % (self.comm.getStateString()))
		elif self.comm.isError():
			wx.CallAfter(self.commState.SetBitmap, self.crossBitmap)
			wx.CallAfter(self.infoBox.SetError, _("Failed to establish connection with the printer."), 'http://wiki.ultimaker.com/Cura:_Connection_problems')
			wx.CallAfter(self.endstopBitmap.Show, False)
			wx.CallAfter(self.machineState.SetLabel, '%s' % (self.comm.getErrorString()))
			wx.CallAfter(self.errorLogButton.Show, True)
			wx.CallAfter(self.Layout)
		else:
			wx.CallAfter(self.machineState.SetLabel, _("Communication State: %s") % (self.comm.getStateString()))

	def mcMessage(self, message):
		if self.checkupState >= 3 and self.checkupState < 10 and ('_min' in message or '_max' in message):
			for data in message.split(' '):
				if ':' in data:
					tag, value = data.split(':', 1)
					if tag == 'x_min':
						self.xMinStop = (value == 'H' or value == 'TRIGGERED')
					if tag == 'x_max':
						self.xMaxStop = (value == 'H' or value == 'TRIGGERED')
					if tag == 'y_min':
						self.yMinStop = (value == 'H' or value == 'TRIGGERED')
					if tag == 'y_max':
						self.yMaxStop = (value == 'H' or value == 'TRIGGERED')
					if tag == 'z_min':
						self.zMinStop = (value == 'H' or value == 'TRIGGERED')
					if tag == 'z_max':
						self.zMaxStop = (value == 'H' or value == 'TRIGGERED')
			if ':' in message:
				tag, value = map(str.strip, message.split(':', 1))
				if tag == 'x_min':
					self.xMinStop = (value == 'H' or value == 'TRIGGERED')
				if tag == 'x_max':
					self.xMaxStop = (value == 'H' or value == 'TRIGGERED')
				if tag == 'y_min':
					self.yMinStop = (value == 'H' or value == 'TRIGGERED')
				if tag == 'y_max':
					self.yMaxStop = (value == 'H' or value == 'TRIGGERED')
				if tag == 'z_min':
					self.zMinStop = (value == 'H' or value == 'TRIGGERED')
				if tag == 'z_max':
					self.zMaxStop = (value == 'H' or value == 'TRIGGERED')
			if 'z_max' in message:
				self.comm.sendCommand('M119')

			if self.checkupState == 3:
				if not self.xMinStop and not self.xMaxStop and not self.yMinStop and not self.yMaxStop and not self.zMinStop and not self.zMaxStop:
					self.checkupState = 4
					wx.CallAfter(self.infoBox.SetAttention, _("Please press the right X endstop."))
					wx.CallAfter(self.endstopBitmap.SetBitmap, self.endStopXMaxBitmap)
			elif self.checkupState == 4:
				if not self.xMinStop and self.xMaxStop and not self.yMinStop and not self.yMaxStop and not self.zMinStop and not self.zMaxStop:
					self.checkupState = 5
					wx.CallAfter(self.infoBox.SetAttention, _("Please press the left X endstop."))
					wx.CallAfter(self.endstopBitmap.SetBitmap, self.endStopXMinBitmap)
			elif self.checkupState == 5:
				if self.xMinStop and not self.xMaxStop and not self.yMinStop and not self.yMaxStop and not self.zMinStop and not self.zMaxStop:
					self.checkupState = 6
					wx.CallAfter(self.infoBox.SetAttention, _("Please press the front Y endstop."))
					wx.CallAfter(self.endstopBitmap.SetBitmap, self.endStopYMinBitmap)
			elif self.checkupState == 6:
				if not self.xMinStop and not self.xMaxStop and self.yMinStop and not self.yMaxStop and not self.zMinStop and not self.zMaxStop:
					self.checkupState = 7
					wx.CallAfter(self.infoBox.SetAttention, _("Please press the back Y endstop."))
					wx.CallAfter(self.endstopBitmap.SetBitmap, self.endStopYMaxBitmap)
			elif self.checkupState == 7:
				if not self.xMinStop and not self.xMaxStop and not self.yMinStop and self.yMaxStop and not self.zMinStop and not self.zMaxStop:
					self.checkupState = 8
					wx.CallAfter(self.infoBox.SetAttention, _("Please press the top Z endstop."))
					wx.CallAfter(self.endstopBitmap.SetBitmap, self.endStopZMinBitmap)
			elif self.checkupState == 8:
				if not self.xMinStop and not self.xMaxStop and not self.yMinStop and not self.yMaxStop and self.zMinStop and not self.zMaxStop:
					self.checkupState = 9
					wx.CallAfter(self.infoBox.SetAttention, _("Please press the bottom Z endstop."))
					wx.CallAfter(self.endstopBitmap.SetBitmap, self.endStopZMaxBitmap)
			elif self.checkupState == 9:
				if not self.xMinStop and not self.xMaxStop and not self.yMinStop and not self.yMaxStop and not self.zMinStop and self.zMaxStop:
					self.checkupState = 10
					self.comm.close()
					wx.CallAfter(self.infoBox.SetInfo, _("Checkup finished"))
					wx.CallAfter(self.infoBox.SetReadyIndicator)
					wx.CallAfter(self.endstopBitmap.Show, False)
					wx.CallAfter(self.stopState.SetBitmap, self.checkBitmap)
					wx.CallAfter(self.OnSkipClick, None)

	def mcProgress(self, lineNr):
		pass

	def mcZChange(self, newZ):
		pass


class UltimakerCalibrationPage(InfoPage):
	def __init__(self, parent):
		super(UltimakerCalibrationPage, self).__init__(parent, "Ultimaker Calibration")

		self.AddText("Your Ultimaker requires some calibration.")
		self.AddText("This calibration is needed for a proper extrusion amount.")
		self.AddSeperator()
		self.AddText("The following values are needed:")
		self.AddText("* Diameter of filament")
		self.AddText("* Number of steps per mm of filament extrusion")
		self.AddSeperator()
		self.AddText("The better you have calibrated these values, the better your prints\nwill become.")
		self.AddSeperator()
		self.AddText("First we need the diameter of your filament:")
		self.filamentDiameter = self.AddTextCtrl(profile.getProfileSetting('filament_diameter'))
		self.AddText(
			"If you do not own digital Calipers that can measure\nat least 2 digits then use 2.89mm.\nWhich is the average diameter of most filament.")
		self.AddText("Note: This value can be changed later at any time.")

	def StoreData(self):
		profile.putProfileSetting('filament_diameter', self.filamentDiameter.GetValue())


class UltimakerCalibrateStepsPerEPage(InfoPage):
	def __init__(self, parent):
		super(UltimakerCalibrateStepsPerEPage, self).__init__(parent, "Ultimaker Calibration")

		#if profile.getMachineSetting('steps_per_e') == '0':
		#	profile.putMachineSetting('steps_per_e', '865.888')

		self.AddText(_("Calibrating the Steps Per E requires some manual actions."))
		self.AddText(_("First remove any filament from your machine."))
		self.AddText(_("Next put in your filament so the tip is aligned with the\ntop of the extruder drive."))
		self.AddText(_("We'll push the filament 100mm"))
		self.extrudeButton = self.AddButton(_("Extrude 100mm filament"))
		self.AddText(_("Now measure the amount of extruded filament:\n(this can be more or less then 100mm)"))
		self.lengthInput, self.saveLengthButton = self.AddTextCtrlButton("100", _("Save"))
		self.AddText(_("This results in the following steps per E:"))
		self.stepsPerEInput = self.AddTextCtrl(profile.getMachineSetting('steps_per_e'))
		self.AddText(_("You can repeat these steps to get better calibration."))
		self.AddSeperator()
		self.AddText(
			_("If you still have filament in your printer which needs\nheat to remove, press the heat up button below:"))
		self.heatButton = self.AddButton(_("Heatup for filament removal"))

		self.saveLengthButton.Bind(wx.EVT_BUTTON, self.OnSaveLengthClick)
		self.extrudeButton.Bind(wx.EVT_BUTTON, self.OnExtrudeClick)
		self.heatButton.Bind(wx.EVT_BUTTON, self.OnHeatClick)

	def OnSaveLengthClick(self, e):
		currentEValue = float(self.stepsPerEInput.GetValue())
		realExtrudeLength = float(self.lengthInput.GetValue())
		newEValue = currentEValue * 100 / realExtrudeLength
		self.stepsPerEInput.SetValue(str(newEValue))
		self.lengthInput.SetValue("100")

	def OnExtrudeClick(self, e):
		t = threading.Thread(target=self.OnExtrudeRun)
		t.daemon = True
		t.start()

	def OnExtrudeRun(self):
		self.heatButton.Enable(False)
		self.extrudeButton.Enable(False)
		currentEValue = float(self.stepsPerEInput.GetValue())
		self.comm = machineCom.MachineCom()
		if not self.comm.isOpen():
			wx.MessageBox(
				_("Error: Failed to open serial port to machine\nIf this keeps happening, try disconnecting and reconnecting the USB cable"),
				'Printer error', wx.OK | wx.ICON_INFORMATION)
			self.heatButton.Enable(True)
			self.extrudeButton.Enable(True)
			return
		while True:
			line = self.comm.readline()
			if line == '':
				return
			if 'start' in line:
				break
			#Wait 3 seconds for the SD card init to timeout if we have SD in our firmware but there is no SD card found.
		time.sleep(3)

		self.sendGCommand('M302') #Disable cold extrusion protection
		self.sendGCommand("M92 E%f" % (currentEValue))
		self.sendGCommand("G92 E0")
		self.sendGCommand("G1 E100 F600")
		time.sleep(15)
		self.comm.close()
		self.extrudeButton.Enable()
		self.heatButton.Enable()

	def OnHeatClick(self, e):
		t = threading.Thread(target=self.OnHeatRun)
		t.daemon = True
		t.start()

	def OnHeatRun(self):
		self.heatButton.Enable(False)
		self.extrudeButton.Enable(False)
		self.comm = machineCom.MachineCom()
		if not self.comm.isOpen():
			wx.MessageBox(
				_("Error: Failed to open serial port to machine\nIf this keeps happening, try disconnecting and reconnecting the USB cable"),
				'Printer error', wx.OK | wx.ICON_INFORMATION)
			self.heatButton.Enable(True)
			self.extrudeButton.Enable(True)
			return
		while True:
			line = self.comm.readline()
			if line == '':
				self.heatButton.Enable(True)
				self.extrudeButton.Enable(True)
				return
			if 'start' in line:
				break
			#Wait 3 seconds for the SD card init to timeout if we have SD in our firmware but there is no SD card found.
		time.sleep(3)

		self.sendGCommand('M104 S200') #Set the temperature to 200C, should be enough to get PLA and ABS out.
		wx.MessageBox(
			'Wait till you can remove the filament from the machine, and press OK.\n(Temperature is set to 200C)',
			'Machine heatup', wx.OK | wx.ICON_INFORMATION)
		self.sendGCommand('M104 S0')
		time.sleep(1)
		self.comm.close()
		self.heatButton.Enable(True)
		self.extrudeButton.Enable(True)

	def sendGCommand(self, cmd):
		self.comm.sendCommand(cmd) #Disable cold extrusion protection
		while True:
			line = self.comm.readline()
			if line == '':
				return
			if line.startswith('ok'):
				break

	def StoreData(self):
		profile.putPreference('steps_per_e', self.stepsPerEInput.GetValue())

class Ultimaker2ReadyPage(InfoPage):
	def __init__(self, parent):
		super(Ultimaker2ReadyPage, self).__init__(parent, "Ultimaker2")
		self.AddText('Congratulations on your the purchase of your brand new Ultimaker2.')
		self.AddText('Cura is now ready to be used with your Ultimaker2.')
		self.AddSeperator()

class configWizard(wx.wizard.Wizard):
	def __init__(self, addNew = False):
		super(configWizard, self).__init__(None, -1, "Configuration Wizard")

		self.Bind(wx.wizard.EVT_WIZARD_PAGE_CHANGED, self.OnPageChanged)
		self.Bind(wx.wizard.EVT_WIZARD_PAGE_CHANGING, self.OnPageChanging)

		self.firstInfoPage = FirstInfoPage(self, addNew)
		self.machineSelectPage = MachineSelectPage(self)
		self.ultimakerSelectParts = SelectParts(self)
		self.ultimakerFirmwareUpgradePage = UltimakerFirmwareUpgradePage(self)
		self.ultimakerCheckupPage = UltimakerCheckupPage(self)
		self.ultimakerCalibrationPage = UltimakerCalibrationPage(self)
		self.ultimakerCalibrateStepsPerEPage = UltimakerCalibrateStepsPerEPage(self)
		self.bedLevelPage = bedLevelWizardMain(self)
		self.headOffsetCalibration = headOffsetCalibrationPage(self)
		self.otherMachineSelectPage = OtherMachineSelectPage(self)
		self.customRepRapInfoPage = CustomRepRapInfoPage(self)
		self.otherMachineInfoPage = OtherMachineInfoPage(self)

		self.ultimaker2ReadyPage = Ultimaker2ReadyPage(self)

		wx.wizard.WizardPageSimple.Chain(self.firstInfoPage, self.machineSelectPage)
		#wx.wizard.WizardPageSimple.Chain(self.machineSelectPage, self.ultimaker2ReadyPage)
		wx.wizard.WizardPageSimple.Chain(self.machineSelectPage, self.ultimakerSelectParts)
		wx.wizard.WizardPageSimple.Chain(self.ultimakerSelectParts, self.ultimakerFirmwareUpgradePage)
		wx.wizard.WizardPageSimple.Chain(self.ultimakerFirmwareUpgradePage, self.ultimakerCheckupPage)
		wx.wizard.WizardPageSimple.Chain(self.ultimakerCheckupPage, self.bedLevelPage)
		#wx.wizard.WizardPageSimple.Chain(self.ultimakerCalibrationPage, self.ultimakerCalibrateStepsPerEPage)
		wx.wizard.WizardPageSimple.Chain(self.otherMachineSelectPage, self.customRepRapInfoPage)

		self.FitToPage(self.firstInfoPage)
		self.GetPageAreaSizer().Add(self.firstInfoPage)

		self.RunWizard(self.firstInfoPage)
		self.Destroy()

	def OnPageChanging(self, e):
		e.GetPage().StoreData()

	def OnPageChanged(self, e):
		if e.GetPage().AllowNext():
			self.FindWindowById(wx.ID_FORWARD).Enable()
		else:
			self.FindWindowById(wx.ID_FORWARD).Disable()
		if e.GetPage().AllowBack():
			self.FindWindowById(wx.ID_BACKWARD).Enable()
		else:
			self.FindWindowById(wx.ID_BACKWARD).Disable()

class bedLevelWizardMain(InfoPage):
	def __init__(self, parent):
		super(bedLevelWizardMain, self).__init__(parent, "Bed leveling wizard")

		self.AddText('This wizard will help you in leveling your printer bed')
		self.AddSeperator()
		self.AddText('It will do the following steps')
		self.AddText('* Move the printer head to each corner')
		self.AddText('  and let you adjust the height of the bed to the nozzle')
		self.AddText('* Print a line around the bed to check if it is level')
		self.AddSeperator()

		self.connectButton = self.AddButton('Connect to printer')
		self.comm = None

		self.infoBox = self.AddInfoBox()
		self.resumeButton = self.AddButton('Resume')
		self.upButton, self.downButton = self.AddDualButton('Up 0.2mm', 'Down 0.2mm')
		self.upButton2, self.downButton2 = self.AddDualButton('Up 10mm', 'Down 10mm')
		self.resumeButton.Enable(False)

		self.upButton.Enable(False)
		self.downButton.Enable(False)
		self.upButton2.Enable(False)
		self.downButton2.Enable(False)

		self.Bind(wx.EVT_BUTTON, self.OnConnect, self.connectButton)
		self.Bind(wx.EVT_BUTTON, self.OnResume, self.resumeButton)
		self.Bind(wx.EVT_BUTTON, self.OnBedUp, self.upButton)
		self.Bind(wx.EVT_BUTTON, self.OnBedDown, self.downButton)
		self.Bind(wx.EVT_BUTTON, self.OnBedUp2, self.upButton2)
		self.Bind(wx.EVT_BUTTON, self.OnBedDown2, self.downButton2)

	def OnConnect(self, e = None):
		if self.comm is not None:
			self.comm.close()
			del self.comm
			self.comm = None
			wx.CallAfter(self.OnConnect)
			return
		self.connectButton.Enable(False)
		self.comm = machineCom.MachineCom(callbackObject=self)
		self.infoBox.SetBusy('Connecting to machine.')
		self._wizardState = 0

	def OnBedUp(self, e):
		feedZ = profile.getProfileSettingFloat('print_speed') * 60
		self.comm.sendCommand('G92 Z10')
		self.comm.sendCommand('G1 Z9.8 F%d' % (feedZ))
		self.comm.sendCommand('M400')

	def OnBedDown(self, e):
		feedZ = profile.getProfileSettingFloat('print_speed') * 60
		self.comm.sendCommand('G92 Z10')
		self.comm.sendCommand('G1 Z10.2 F%d' % (feedZ))
		self.comm.sendCommand('M400')

	def OnBedUp2(self, e):
		feedZ = profile.getProfileSettingFloat('print_speed') * 60
		self.comm.sendCommand('G92 Z10')
		self.comm.sendCommand('G1 Z0 F%d' % (feedZ))
		self.comm.sendCommand('M400')

	def OnBedDown2(self, e):
		feedZ = profile.getProfileSettingFloat('print_speed') * 60
		self.comm.sendCommand('G92 Z10')
		self.comm.sendCommand('G1 Z20 F%d' % (feedZ))
		self.comm.sendCommand('M400')

	def AllowNext(self):
		if self.GetParent().headOffsetCalibration is not None and int(profile.getMachineSetting('extruder_amount')) > 1:
			wx.wizard.WizardPageSimple.Chain(self, self.GetParent().headOffsetCalibration)
		return True

	def OnResume(self, e):
		feedZ = profile.getProfileSettingFloat('print_speed') * 60
		feedTravel = profile.getProfileSettingFloat('travel_speed') * 60
		if self._wizardState == -1:
			wx.CallAfter(self.infoBox.SetInfo, 'Homing printer...')
			wx.CallAfter(self.upButton.Enable, False)
			wx.CallAfter(self.downButton.Enable, False)
			wx.CallAfter(self.upButton2.Enable, False)
			wx.CallAfter(self.downButton2.Enable, False)
			self.comm.sendCommand('M105')
			self.comm.sendCommand('G28')
			self._wizardState = 1
		elif self._wizardState == 2:
			if profile.getMachineSetting('has_heated_bed') == 'True':
				wx.CallAfter(self.infoBox.SetBusy, 'Moving head to back center...')
				self.comm.sendCommand('G1 Z3 F%d' % (feedZ))
				self.comm.sendCommand('G1 X%d Y%d F%d' % (profile.getMachineSettingFloat('machine_width') / 2.0, profile.getMachineSettingFloat('machine_depth'), feedTravel))
				self.comm.sendCommand('G1 Z0 F%d' % (feedZ))
				self.comm.sendCommand('M400')
				self._wizardState = 3
			else:
				wx.CallAfter(self.infoBox.SetBusy, 'Moving head to back left corner...')
				self.comm.sendCommand('G1 Z3 F%d' % (feedZ))
				self.comm.sendCommand('G1 X%d Y%d F%d' % (0, profile.getMachineSettingFloat('machine_depth'), feedTravel))
				self.comm.sendCommand('G1 Z0 F%d' % (feedZ))
				self.comm.sendCommand('M400')
				self._wizardState = 3
		elif self._wizardState == 4:
			if profile.getMachineSetting('has_heated_bed') == 'True':
				wx.CallAfter(self.infoBox.SetBusy, 'Moving head to front right corner...')
				self.comm.sendCommand('G1 Z3 F%d' % (feedZ))
				self.comm.sendCommand('G1 X%d Y%d F%d' % (profile.getMachineSettingFloat('machine_width') - 5.0, 5, feedTravel))
				self.comm.sendCommand('G1 Z0 F%d' % (feedZ))
				self.comm.sendCommand('M400')
				self._wizardState = 7
			else:
				wx.CallAfter(self.infoBox.SetBusy, 'Moving head to back right corner...')
				self.comm.sendCommand('G1 Z3 F%d' % (feedZ))
				self.comm.sendCommand('G1 X%d Y%d F%d' % (profile.getMachineSettingFloat('machine_width') - 5.0, profile.getMachineSettingFloat('machine_depth') - 25, feedTravel))
				self.comm.sendCommand('G1 Z0 F%d' % (feedZ))
				self.comm.sendCommand('M400')
				self._wizardState = 5
		elif self._wizardState == 6:
			wx.CallAfter(self.infoBox.SetBusy, 'Moving head to front right corner...')
			self.comm.sendCommand('G1 Z3 F%d' % (feedZ))
			self.comm.sendCommand('G1 X%d Y%d F%d' % (profile.getMachineSettingFloat('machine_width') - 5.0, 20, feedTravel))
			self.comm.sendCommand('G1 Z0 F%d' % (feedZ))
			self.comm.sendCommand('M400')
			self._wizardState = 7
		elif self._wizardState == 8:
			wx.CallAfter(self.infoBox.SetBusy, 'Heating up printer...')
			self.comm.sendCommand('G1 Z15 F%d' % (feedZ))
			self.comm.sendCommand('M104 S%d' % (profile.getProfileSettingFloat('print_temperature')))
			self.comm.sendCommand('G1 X%d Y%d F%d' % (0, 0, feedTravel))
			self._wizardState = 9
		elif self._wizardState == 10:
			self._wizardState = 11
			wx.CallAfter(self.infoBox.SetInfo, 'Printing a square on the printer bed at 0.3mm height.')
			feedZ = profile.getProfileSettingFloat('print_speed') * 60
			feedPrint = profile.getProfileSettingFloat('print_speed') * 60
			feedTravel = profile.getProfileSettingFloat('travel_speed') * 60
			w = profile.getMachineSettingFloat('machine_width') - 10
			d = profile.getMachineSettingFloat('machine_depth')
			filamentRadius = profile.getProfileSettingFloat('filament_diameter') / 2
			filamentArea = math.pi * filamentRadius * filamentRadius
			ePerMM = (profile.calculateEdgeWidth() * 0.3) / filamentArea
			eValue = 0.0

			gcodeList = [
				'G1 Z2 F%d' % (feedZ),
				'G92 E0',
				'G1 X%d Y%d F%d' % (5, 5, feedTravel),
				'G1 Z0.3 F%d' % (feedZ)]
			eValue += 5.0
			gcodeList.append('G1 E%f F%d' % (eValue, profile.getProfileSettingFloat('retraction_speed') * 60))

			for i in xrange(0, 3):
				dist = 5.0 + 0.4 * float(i)
				eValue += (d - 2.0*dist) * ePerMM
				gcodeList.append('G1 X%f Y%f E%f F%d' % (dist, d - dist, eValue, feedPrint))
				eValue += (w - 2.0*dist) * ePerMM
				gcodeList.append('G1 X%f Y%f E%f F%d' % (w - dist, d - dist, eValue, feedPrint))
				eValue += (d - 2.0*dist) * ePerMM
				gcodeList.append('G1 X%f Y%f E%f F%d' % (w - dist, dist, eValue, feedPrint))
				eValue += (w - 2.0*dist) * ePerMM
				gcodeList.append('G1 X%f Y%f E%f F%d' % (dist, dist, eValue, feedPrint))

			gcodeList.append('M400')
			self.comm.printGCode(gcodeList)
		self.resumeButton.Enable(False)

	def mcLog(self, message):
		print 'Log:', message

	def mcTempUpdate(self, temp, bedTemp, targetTemp, bedTargetTemp):
		if self._wizardState == 1:
			self._wizardState = 2
			wx.CallAfter(self.infoBox.SetAttention, 'Adjust the front left screw of your printer bed\nSo the nozzle just hits the bed.')
			wx.CallAfter(self.resumeButton.Enable, True)
		elif self._wizardState == 3:
			self._wizardState = 4
			if profile.getMachineSetting('has_heated_bed') == 'True':
				wx.CallAfter(self.infoBox.SetAttention, 'Adjust the back screw of your printer bed\nSo the nozzle just hits the bed.')
			else:
				wx.CallAfter(self.infoBox.SetAttention, 'Adjust the back left screw of your printer bed\nSo the nozzle just hits the bed.')
			wx.CallAfter(self.resumeButton.Enable, True)
		elif self._wizardState == 5:
			self._wizardState = 6
			wx.CallAfter(self.infoBox.SetAttention, 'Adjust the back right screw of your printer bed\nSo the nozzle just hits the bed.')
			wx.CallAfter(self.resumeButton.Enable, True)
		elif self._wizardState == 7:
			self._wizardState = 8
			wx.CallAfter(self.infoBox.SetAttention, 'Adjust the front right screw of your printer bed\nSo the nozzle just hits the bed.')
			wx.CallAfter(self.resumeButton.Enable, True)
		elif self._wizardState == 9:
			if temp[0] < profile.getProfileSettingFloat('print_temperature') - 5:
				wx.CallAfter(self.infoBox.SetInfo, 'Heating up printer: %d/%d' % (temp[0], profile.getProfileSettingFloat('print_temperature')))
			else:
				wx.CallAfter(self.infoBox.SetAttention, 'The printer is hot now. Please insert some PLA filament into the printer.')
				wx.CallAfter(self.resumeButton.Enable, True)
				self._wizardState = 10

	def mcStateChange(self, state):
		if self.comm is None:
			return
		if self.comm.isOperational():
			if self._wizardState == 0:
				wx.CallAfter(self.infoBox.SetAttention, 'Use the up/down buttons to move the bed and adjust your Z endstop.')
				wx.CallAfter(self.upButton.Enable, True)
				wx.CallAfter(self.downButton.Enable, True)
				wx.CallAfter(self.upButton2.Enable, True)
				wx.CallAfter(self.downButton2.Enable, True)
				wx.CallAfter(self.resumeButton.Enable, True)
				self._wizardState = -1
			elif self._wizardState == 11 and not self.comm.isPrinting():
				self.comm.sendCommand('G1 Z15 F%d' % (profile.getProfileSettingFloat('print_speed') * 60))
				self.comm.sendCommand('G92 E0')
				self.comm.sendCommand('G1 E-10 F%d' % (profile.getProfileSettingFloat('retraction_speed') * 60))
				self.comm.sendCommand('M104 S0')
				wx.CallAfter(self.infoBox.SetInfo, 'Calibration finished.\nThe squares on the bed should slightly touch each other.')
				wx.CallAfter(self.infoBox.SetReadyIndicator)
				wx.CallAfter(self.GetParent().FindWindowById(wx.ID_FORWARD).Enable)
				wx.CallAfter(self.connectButton.Enable, True)
				self._wizardState = 12
		elif self.comm.isError():
			wx.CallAfter(self.infoBox.SetError, 'Failed to establish connection with the printer.', 'http://wiki.ultimaker.com/Cura:_Connection_problems')

	def mcMessage(self, message):
		pass

	def mcProgress(self, lineNr):
		pass

	def mcZChange(self, newZ):
		pass

class headOffsetCalibrationPage(InfoPage):
	def __init__(self, parent):
		super(headOffsetCalibrationPage, self).__init__(parent, "Printer head offset calibration")

		self.AddText('This wizard will help you in calibrating the printer head offsets of your dual extrusion machine')
		self.AddSeperator()

		self.connectButton = self.AddButton('Connect to printer')
		self.comm = None

		self.infoBox = self.AddInfoBox()
		self.textEntry = self.AddTextCtrl('')
		self.textEntry.Enable(False)
		self.resumeButton = self.AddButton('Resume')
		self.resumeButton.Enable(False)

		self.Bind(wx.EVT_BUTTON, self.OnConnect, self.connectButton)
		self.Bind(wx.EVT_BUTTON, self.OnResume, self.resumeButton)

	def AllowBack(self):
		return True

	def OnConnect(self, e = None):
		if self.comm is not None:
			self.comm.close()
			del self.comm
			self.comm = None
			wx.CallAfter(self.OnConnect)
			return
		self.connectButton.Enable(False)
		self.comm = machineCom.MachineCom(callbackObject=self)
		self.infoBox.SetBusy('Connecting to machine.')
		self._wizardState = 0

	def OnResume(self, e):
		if self._wizardState == 2:
			self._wizardState = 3
			wx.CallAfter(self.infoBox.SetBusy, 'Printing initial calibration cross')

			w = profile.getMachineSettingFloat('machine_width')
			d = profile.getMachineSettingFloat('machine_depth')

			gcode = gcodeGenerator.gcodeGenerator()
			gcode.setExtrusionRate(profile.getProfileSettingFloat('nozzle_size') * 1.5, 0.2)
			gcode.setPrintSpeed(profile.getProfileSettingFloat('bottom_layer_speed'))
			gcode.addCmd('T0')
			gcode.addPrime(15)
			gcode.addCmd('T1')
			gcode.addPrime(15)

			gcode.addCmd('T0')
			gcode.addMove(w/2, 5)
			gcode.addMove(z=0.2)
			gcode.addPrime()
			gcode.addExtrude(w/2, d-5.0)
			gcode.addRetract()
			gcode.addMove(5, d/2)
			gcode.addPrime()
			gcode.addExtrude(w-5.0, d/2)
			gcode.addRetract(15)

			gcode.addCmd('T1')
			gcode.addMove(w/2, 5)
			gcode.addPrime()
			gcode.addExtrude(w/2, d-5.0)
			gcode.addRetract()
			gcode.addMove(5, d/2)
			gcode.addPrime()
			gcode.addExtrude(w-5.0, d/2)
			gcode.addRetract(15)
			gcode.addCmd('T0')

			gcode.addMove(z=25)
			gcode.addMove(0, 0)
			gcode.addCmd('M400')

			self.comm.printGCode(gcode.list())
			self.resumeButton.Enable(False)
		elif self._wizardState == 4:
			try:
				float(self.textEntry.GetValue())
			except ValueError:
				return
			profile.putPreference('extruder_offset_x1', self.textEntry.GetValue())
			self._wizardState = 5
			self.infoBox.SetAttention('Please measure the distance between the horizontal lines in millimeters.')
			self.textEntry.SetValue('0.0')
			self.textEntry.Enable(True)
		elif self._wizardState == 5:
			try:
				float(self.textEntry.GetValue())
			except ValueError:
				return
			profile.putPreference('extruder_offset_y1', self.textEntry.GetValue())
			self._wizardState = 6
			self.infoBox.SetBusy('Printing the fine calibration lines.')
			self.textEntry.SetValue('')
			self.textEntry.Enable(False)
			self.resumeButton.Enable(False)

			x = profile.getMachineSettingFloat('extruder_offset_x1')
			y = profile.getMachineSettingFloat('extruder_offset_y1')
			gcode = gcodeGenerator.gcodeGenerator()
			gcode.setExtrusionRate(profile.getProfileSettingFloat('nozzle_size') * 1.5, 0.2)
			gcode.setPrintSpeed(25)
			gcode.addHome()
			gcode.addCmd('T0')
			gcode.addMove(50, 40, 0.2)
			gcode.addPrime(15)
			for n in xrange(0, 10):
				gcode.addExtrude(50 + n * 10, 150)
				gcode.addExtrude(50 + n * 10 + 5, 150)
				gcode.addExtrude(50 + n * 10 + 5, 40)
				gcode.addExtrude(50 + n * 10 + 10, 40)
			gcode.addMove(40, 50)
			for n in xrange(0, 10):
				gcode.addExtrude(150, 50 + n * 10)
				gcode.addExtrude(150, 50 + n * 10 + 5)
				gcode.addExtrude(40, 50 + n * 10 + 5)
				gcode.addExtrude(40, 50 + n * 10 + 10)
			gcode.addRetract(15)

			gcode.addCmd('T1')
			gcode.addMove(50 - x, 30 - y, 0.2)
			gcode.addPrime(15)
			for n in xrange(0, 10):
				gcode.addExtrude(50 + n * 10.2 - 1.0 - x, 140 - y)
				gcode.addExtrude(50 + n * 10.2 - 1.0 + 5.1 - x, 140 - y)
				gcode.addExtrude(50 + n * 10.2 - 1.0 + 5.1 - x, 30 - y)
				gcode.addExtrude(50 + n * 10.2 - 1.0 + 10 - x, 30 - y)
			gcode.addMove(30 - x, 50 - y, 0.2)
			for n in xrange(0, 10):
				gcode.addExtrude(160 - x, 50 + n * 10.2 - 1.0 - y)
				gcode.addExtrude(160 - x, 50 + n * 10.2 - 1.0 + 5.1 - y)
				gcode.addExtrude(30 - x, 50 + n * 10.2 - 1.0 + 5.1 - y)
				gcode.addExtrude(30 - x, 50 + n * 10.2 - 1.0 + 10 - y)
			gcode.addRetract(15)
			gcode.addMove(z=15)
			gcode.addCmd('M400')
			gcode.addCmd('M104 T0 S0')
			gcode.addCmd('M104 T1 S0')
			self.comm.printGCode(gcode.list())
		elif self._wizardState == 7:
			try:
				n = int(self.textEntry.GetValue()) - 1
			except:
				return
			x = profile.getMachineSettingFloat('extruder_offset_x1')
			x += -1.0 + n * 0.1
			profile.putPreference('extruder_offset_x1', '%0.2f' % (x))
			self.infoBox.SetAttention('Which horizontal line number lays perfect on top of each other? Front most line is zero.')
			self.textEntry.SetValue('10')
			self._wizardState = 8
		elif self._wizardState == 8:
			try:
				n = int(self.textEntry.GetValue()) - 1
			except:
				return
			y = profile.getMachineSettingFloat('extruder_offset_y1')
			y += -1.0 + n * 0.1
			profile.putPreference('extruder_offset_y1', '%0.2f' % (y))
			self.infoBox.SetInfo('Calibration finished. Offsets are: %s %s' % (profile.getMachineSettingFloat('extruder_offset_x1'), profile.getMachineSettingFloat('extruder_offset_y1')))
			self.infoBox.SetReadyIndicator()
			self._wizardState = 8
			self.comm.close()
			self.resumeButton.Enable(False)

	def mcLog(self, message):
		print 'Log:', message

	def mcTempUpdate(self, temp, bedTemp, targetTemp, bedTargetTemp):
		if self._wizardState == 1:
			if temp[0] >= 210 and temp[1] >= 210:
				self._wizardState = 2
				wx.CallAfter(self.infoBox.SetAttention, 'Please load both extruders with PLA.')
				wx.CallAfter(self.resumeButton.Enable, True)
				wx.CallAfter(self.resumeButton.SetFocus)

	def mcStateChange(self, state):
		if self.comm is None:
			return
		if self.comm.isOperational():
			if self._wizardState == 0:
				wx.CallAfter(self.infoBox.SetInfo, 'Homing printer and heating up both extruders.')
				self.comm.sendCommand('M105')
				self.comm.sendCommand('M104 S220 T0')
				self.comm.sendCommand('M104 S220 T1')
				self.comm.sendCommand('G28')
				self.comm.sendCommand('G1 Z15 F%d' % (profile.getProfileSettingFloat('print_speed') * 60))
				self._wizardState = 1
			if not self.comm.isPrinting():
				if self._wizardState == 3:
					self._wizardState = 4
					wx.CallAfter(self.infoBox.SetAttention, 'Please measure the distance between the vertical lines in millimeters.')
					wx.CallAfter(self.textEntry.SetValue, '0.0')
					wx.CallAfter(self.textEntry.Enable, True)
					wx.CallAfter(self.resumeButton.Enable, True)
					wx.CallAfter(self.resumeButton.SetFocus)
				elif self._wizardState == 6:
					self._wizardState = 7
					wx.CallAfter(self.infoBox.SetAttention, 'Which vertical line number lays perfect on top of each other? Leftmost line is zero.')
					wx.CallAfter(self.textEntry.SetValue, '10')
					wx.CallAfter(self.textEntry.Enable, True)
					wx.CallAfter(self.resumeButton.Enable, True)
					wx.CallAfter(self.resumeButton.SetFocus)

		elif self.comm.isError():
			wx.CallAfter(self.infoBox.SetError, 'Failed to establish connection with the printer.', 'http://wiki.ultimaker.com/Cura:_Connection_problems')

	def mcMessage(self, message):
		pass

	def mcProgress(self, lineNr):
		pass

	def mcZChange(self, newZ):
		pass

class bedLevelWizard(wx.wizard.Wizard):
	def __init__(self):
		super(bedLevelWizard, self).__init__(None, -1, "Bed leveling wizard")

		self.Bind(wx.wizard.EVT_WIZARD_PAGE_CHANGED, self.OnPageChanged)
		self.Bind(wx.wizard.EVT_WIZARD_PAGE_CHANGING, self.OnPageChanging)

		self.mainPage = bedLevelWizardMain(self)
		self.headOffsetCalibration = None

		self.FitToPage(self.mainPage)
		self.GetPageAreaSizer().Add(self.mainPage)

		self.RunWizard(self.mainPage)
		self.Destroy()

	def OnPageChanging(self, e):
		e.GetPage().StoreData()

	def OnPageChanged(self, e):
		if e.GetPage().AllowNext():
			self.FindWindowById(wx.ID_FORWARD).Enable()
		else:
			self.FindWindowById(wx.ID_FORWARD).Disable()
		if e.GetPage().AllowBack():
			self.FindWindowById(wx.ID_BACKWARD).Enable()
		else:
			self.FindWindowById(wx.ID_BACKWARD).Disable()

class headOffsetWizard(wx.wizard.Wizard):
	def __init__(self):
		super(headOffsetWizard, self).__init__(None, -1, "Head offset wizard")

		self.Bind(wx.wizard.EVT_WIZARD_PAGE_CHANGED, self.OnPageChanged)
		self.Bind(wx.wizard.EVT_WIZARD_PAGE_CHANGING, self.OnPageChanging)

		self.mainPage = headOffsetCalibrationPage(self)

		self.FitToPage(self.mainPage)
		self.GetPageAreaSizer().Add(self.mainPage)

		self.RunWizard(self.mainPage)
		self.Destroy()

	def OnPageChanging(self, e):
		e.GetPage().StoreData()

	def OnPageChanged(self, e):
		if e.GetPage().AllowNext():
			self.FindWindowById(wx.ID_FORWARD).Enable()
		else:
			self.FindWindowById(wx.ID_FORWARD).Disable()
		if e.GetPage().AllowBack():
			self.FindWindowById(wx.ID_BACKWARD).Enable()
		else:
			self.FindWindowById(wx.ID_BACKWARD).Disable()

########NEW FILE########
__FILENAME__ = expertConfig
__copyright__ = "Copyright (C) 2013 David Braam - Released under terms of the AGPLv3 License"

import wx

from Cura.gui import configBase
from Cura.util import profile

class expertConfigWindow(wx.Dialog):
	"Expert configuration window"
	def _addSettingsToPanels(self, category, left, right):
		count = len(profile.getSubCategoriesFor(category)) + len(profile.getSettingsForCategory(category))

		p = left
		n = 0
		for title in profile.getSubCategoriesFor(category):
			n += 1 + len(profile.getSettingsForCategory(category, title))
			if n > count / 2:
				p = right
			configBase.TitleRow(p, title)
			for s in profile.getSettingsForCategory(category, title):
				if s.checkConditions():
					configBase.SettingRow(p, s.getName())

	def __init__(self, callback):
		super(expertConfigWindow, self).__init__(None, title='Expert config', style=wx.DEFAULT_DIALOG_STYLE)

		wx.EVT_CLOSE(self, self.OnClose)
		self.panel = configBase.configPanelBase(self, callback)

		left, right, main = self.panel.CreateConfigPanel(self)
		self._addSettingsToPanels('expert', left, right)

		self.okButton = wx.Button(right, -1, 'Ok')
		right.GetSizer().Add(self.okButton, (right.GetSizer().GetRows(), 0))
		self.Bind(wx.EVT_BUTTON, lambda e: self.Close(), self.okButton)
		
		main.Fit()
		self.Fit()

	def OnClose(self, e):
		self.Destroy()

########NEW FILE########
__FILENAME__ = firmwareInstall
__copyright__ = "Copyright (C) 2013 David Braam - Released under terms of the AGPLv3 License"

import os
import wx
import threading
import sys
import time

from Cura.avr_isp import stk500v2
from Cura.avr_isp import ispBase
from Cura.avr_isp import intelHex

from Cura.util import machineCom
from Cura.util import profile
from Cura.util import resources

def getDefaultFirmware(machineIndex = None):
	if profile.getMachineSetting('machine_type', machineIndex) == 'ultimaker':
		name = 'MarlinUltimaker'
		if profile.getMachineSettingFloat('extruder_amount', machineIndex) > 2:
			return None
		if profile.getMachineSetting('has_heated_bed', machineIndex) == 'True':
			name += '-HBK'
		if sys.platform.startswith('linux'):
			name += '-115200'
		else:
			name += '-250000'
		if profile.getMachineSettingFloat('extruder_amount', machineIndex) > 1:
			name += '-dual'
		return resources.getPathForFirmware(name + '.hex')

	if profile.getMachineSetting('machine_type', machineIndex) == 'ultimaker2':
		return resources.getPathForFirmware("MarlinUltimaker2.hex")
	return None

class InstallFirmware(wx.Dialog):
	def __init__(self, filename = None, port = None, machineIndex = None):
		super(InstallFirmware, self).__init__(parent=None, title="Firmware install for %s" % (profile.getMachineSetting('machine_name', machineIndex).title()), size=(250, 100))
		if port is None:
			port = profile.getMachineSetting('serial_port')
		if filename is None:
			filename = getDefaultFirmware(machineIndex)
		if filename is None:
			wx.MessageBox(_("I am sorry, but Cura does not ship with a default firmware for your machine configuration."), _("Firmware update"), wx.OK | wx.ICON_ERROR)
			self.Destroy()
			return
		if profile.getMachineSetting('machine_type', machineIndex) == 'reprap':
			wx.MessageBox(_("Cura only supports firmware updates for ATMega2560 based hardware.\nSo updating your RepRap with Cura might or might not work."), _("Firmware update"), wx.OK | wx.ICON_INFORMATION)

		sizer = wx.BoxSizer(wx.VERTICAL)

		self.progressLabel = wx.StaticText(self, -1, 'XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX\nX')
		sizer.Add(self.progressLabel, 0, flag=wx.ALIGN_CENTER|wx.ALL, border=5)
		self.progressGauge = wx.Gauge(self, -1)
		sizer.Add(self.progressGauge, 0, flag=wx.EXPAND)
		self.okButton = wx.Button(self, -1, _("OK"))
		self.okButton.Disable()
		self.okButton.Bind(wx.EVT_BUTTON, self.OnOk)
		sizer.Add(self.okButton, 0, flag=wx.ALIGN_CENTER|wx.ALL, border=5)
		self.SetSizer(sizer)

		self.filename = filename
		self.port = port

		self.Layout()
		self.Fit()

		self.thread = threading.Thread(target=self.OnRun)
		self.thread.daemon = True
		self.thread.start()

		self.ShowModal()
		self.Destroy()
		return

	def OnRun(self):
		wx.CallAfter(self.updateLabel, _("Reading firmware..."))
		hexFile = intelHex.readHex(self.filename)
		wx.CallAfter(self.updateLabel, _("Connecting to machine..."))
		programmer = stk500v2.Stk500v2()
		programmer.progressCallback = self.OnProgress
		if self.port == 'AUTO':
			wx.CallAfter(self.updateLabel, _("Please connect the printer to\nyour computer with the USB cable."))
			while not programmer.isConnected():
				for self.port in machineCom.serialList(True):
					try:
						programmer.connect(self.port)
						break
					except ispBase.IspError:
						pass
				time.sleep(1)
				if not self:
					#Window destroyed
					return
		else:
			try:
				programmer.connect(self.port)
			except ispBase.IspError:
				pass

		if not programmer.isConnected():
			wx.MessageBox(_("Failed to find machine for firmware upgrade\nIs your machine connected to the PC?"),
						  _("Firmware update"), wx.OK | wx.ICON_ERROR)
			wx.CallAfter(self.Close)
			return

		wx.CallAfter(self.updateLabel, _("Uploading firmware..."))
		try:
			programmer.programChip(hexFile)
			wx.CallAfter(self.updateLabel, _("Done!\nInstalled firmware: %s") % (os.path.basename(self.filename)))
		except ispBase.IspError as e:
			wx.CallAfter(self.updateLabel, _("Failed to write firmware.\n") + str(e))

		programmer.close()
		wx.CallAfter(self.okButton.Enable)

	def updateLabel(self, text):
		self.progressLabel.SetLabel(text)
		#self.Layout()

	def OnProgress(self, value, max):
		wx.CallAfter(self.progressGauge.SetRange, max)
		wx.CallAfter(self.progressGauge.SetValue, value)

	def OnOk(self, e):
		self.Close()

	def OnClose(self, e):
		self.Destroy()


########NEW FILE########
__FILENAME__ = mainWindow
__copyright__ = "Copyright (C) 2013 David Braam - Released under terms of the AGPLv3 License"

import wx
import os
import webbrowser
import sys


from Cura.gui import configBase
from Cura.gui import expertConfig
from Cura.gui import alterationPanel
from Cura.gui import pluginPanel
from Cura.gui import preferencesDialog
from Cura.gui import configWizard
from Cura.gui import firmwareInstall
from Cura.gui import simpleMode
from Cura.gui import sceneView
from Cura.gui import aboutWindow
from Cura.gui.util import dropTarget
#from Cura.gui.tools import batchRun
from Cura.gui.tools import pidDebugger
from Cura.gui.tools import minecraftImport
from Cura.util import profile
from Cura.util import version
import platform
from Cura.util import meshLoader

class mainWindow(wx.Frame):
	def __init__(self):
		super(mainWindow, self).__init__(None, title='Cura - ' + version.getVersion())

		wx.EVT_CLOSE(self, self.OnClose)

		# allow dropping any file, restrict later
		self.SetDropTarget(dropTarget.FileDropTarget(self.OnDropFiles))

		# TODO: wxWidgets 2.9.4 has a bug when NSView does not register for dragged types when wx drop target is set. It was fixed in 2.9.5
		if sys.platform.startswith('darwin'):
			try:
				import objc
				nswindow = objc.objc_object(c_void_p=self.MacGetTopLevelWindowRef())
				view = nswindow.contentView()
				view.registerForDraggedTypes_([u'NSFilenamesPboardType'])
			except:
				pass

		self.normalModeOnlyItems = []

		mruFile = os.path.join(profile.getBasePath(), 'mru_filelist.ini')
		self.config = wx.FileConfig(appName="Cura",
						localFilename=mruFile,
						style=wx.CONFIG_USE_LOCAL_FILE)

		self.ID_MRU_MODEL1, self.ID_MRU_MODEL2, self.ID_MRU_MODEL3, self.ID_MRU_MODEL4, self.ID_MRU_MODEL5, self.ID_MRU_MODEL6, self.ID_MRU_MODEL7, self.ID_MRU_MODEL8, self.ID_MRU_MODEL9, self.ID_MRU_MODEL10 = [wx.NewId() for line in xrange(10)]
		self.modelFileHistory = wx.FileHistory(10, self.ID_MRU_MODEL1)
		self.config.SetPath("/ModelMRU")
		self.modelFileHistory.Load(self.config)

		self.ID_MRU_PROFILE1, self.ID_MRU_PROFILE2, self.ID_MRU_PROFILE3, self.ID_MRU_PROFILE4, self.ID_MRU_PROFILE5, self.ID_MRU_PROFILE6, self.ID_MRU_PROFILE7, self.ID_MRU_PROFILE8, self.ID_MRU_PROFILE9, self.ID_MRU_PROFILE10 = [wx.NewId() for line in xrange(10)]
		self.profileFileHistory = wx.FileHistory(10, self.ID_MRU_PROFILE1)
		self.config.SetPath("/ProfileMRU")
		self.profileFileHistory.Load(self.config)

		self.menubar = wx.MenuBar()
		self.fileMenu = wx.Menu()
		i = self.fileMenu.Append(-1, _("Load model file...\tCTRL+L"))
		self.Bind(wx.EVT_MENU, lambda e: self.scene.showLoadModel(), i)
		i = self.fileMenu.Append(-1, _("Save model...\tCTRL+S"))
		self.Bind(wx.EVT_MENU, lambda e: self.scene.showSaveModel(), i)
		i = self.fileMenu.Append(-1, _("Reload platform\tF5"))
		self.Bind(wx.EVT_MENU, lambda e: self.scene.reloadScene(e), i)
		i = self.fileMenu.Append(-1, _("Clear platform"))
		self.Bind(wx.EVT_MENU, lambda e: self.scene.OnDeleteAll(e), i)

		self.fileMenu.AppendSeparator()
		i = self.fileMenu.Append(-1, _("Print...\tCTRL+P"))
		self.Bind(wx.EVT_MENU, lambda e: self.scene.OnPrintButton(1), i)
		i = self.fileMenu.Append(-1, _("Save GCode..."))
		self.Bind(wx.EVT_MENU, lambda e: self.scene.showSaveGCode(), i)
		i = self.fileMenu.Append(-1, _("Show slice engine log..."))
		self.Bind(wx.EVT_MENU, lambda e: self.scene._showEngineLog(), i)

		self.fileMenu.AppendSeparator()
		i = self.fileMenu.Append(-1, _("Open Profile..."))
		self.normalModeOnlyItems.append(i)
		self.Bind(wx.EVT_MENU, self.OnLoadProfile, i)
		i = self.fileMenu.Append(-1, _("Save Profile..."))
		self.normalModeOnlyItems.append(i)
		self.Bind(wx.EVT_MENU, self.OnSaveProfile, i)
		i = self.fileMenu.Append(-1, _("Load Profile from GCode..."))
		self.normalModeOnlyItems.append(i)
		self.Bind(wx.EVT_MENU, self.OnLoadProfileFromGcode, i)
		self.fileMenu.AppendSeparator()
		i = self.fileMenu.Append(-1, _("Reset Profile to default"))
		self.normalModeOnlyItems.append(i)
		self.Bind(wx.EVT_MENU, self.OnResetProfile, i)

		self.fileMenu.AppendSeparator()
		i = self.fileMenu.Append(-1, _("Preferences...\tCTRL+,"))
		self.Bind(wx.EVT_MENU, self.OnPreferences, i)
		i = self.fileMenu.Append(-1, _("Machine settings..."))
		self.Bind(wx.EVT_MENU, self.OnMachineSettings, i)
		self.fileMenu.AppendSeparator()

		# Model MRU list
		modelHistoryMenu = wx.Menu()
		self.fileMenu.AppendMenu(wx.NewId(), '&' + _("Recent Model Files"), modelHistoryMenu)
		self.modelFileHistory.UseMenu(modelHistoryMenu)
		self.modelFileHistory.AddFilesToMenu()
		self.Bind(wx.EVT_MENU_RANGE, self.OnModelMRU, id=self.ID_MRU_MODEL1, id2=self.ID_MRU_MODEL10)

		# Profle MRU list
		profileHistoryMenu = wx.Menu()
		self.fileMenu.AppendMenu(wx.NewId(), _("Recent Profile Files"), profileHistoryMenu)
		self.profileFileHistory.UseMenu(profileHistoryMenu)
		self.profileFileHistory.AddFilesToMenu()
		self.Bind(wx.EVT_MENU_RANGE, self.OnProfileMRU, id=self.ID_MRU_PROFILE1, id2=self.ID_MRU_PROFILE10)

		self.fileMenu.AppendSeparator()
		i = self.fileMenu.Append(wx.ID_EXIT, _("Quit"))
		self.Bind(wx.EVT_MENU, self.OnQuit, i)
		self.menubar.Append(self.fileMenu, '&' + _("File"))

		toolsMenu = wx.Menu()
		#i = toolsMenu.Append(-1, 'Batch run...')
		#self.Bind(wx.EVT_MENU, self.OnBatchRun, i)
		#self.normalModeOnlyItems.append(i)

		if minecraftImport.hasMinecraft():
			i = toolsMenu.Append(-1, _("Minecraft map import..."))
			self.Bind(wx.EVT_MENU, self.OnMinecraftImport, i)

		if version.isDevVersion():
			i = toolsMenu.Append(-1, _("PID Debugger..."))
			self.Bind(wx.EVT_MENU, self.OnPIDDebugger, i)

		i = toolsMenu.Append(-1, _("Copy profile to clipboard"))
		self.Bind(wx.EVT_MENU, self.onCopyProfileClipboard,i)

		toolsMenu.AppendSeparator()
		self.allAtOnceItem = toolsMenu.Append(-1, _("Print all at once"), kind=wx.ITEM_RADIO)
		self.Bind(wx.EVT_MENU, self.onOneAtATimeSwitch, self.allAtOnceItem)
		self.oneAtATime = toolsMenu.Append(-1, _("Print one at a time"), kind=wx.ITEM_RADIO)
		self.Bind(wx.EVT_MENU, self.onOneAtATimeSwitch, self.oneAtATime)
		if profile.getPreference('oneAtATime') == 'True':
			self.oneAtATime.Check(True)
		else:
			self.allAtOnceItem.Check(True)

		self.menubar.Append(toolsMenu, _("Tools"))

		#Machine menu for machine configuration/tooling
		self.machineMenu = wx.Menu()
		self.updateMachineMenu()

		self.menubar.Append(self.machineMenu, _("Machine"))

		expertMenu = wx.Menu()
		i = expertMenu.Append(-1, _("Switch to quickprint..."), kind=wx.ITEM_RADIO)
		self.switchToQuickprintMenuItem = i
		self.Bind(wx.EVT_MENU, self.OnSimpleSwitch, i)

		i = expertMenu.Append(-1, _("Switch to full settings..."), kind=wx.ITEM_RADIO)
		self.switchToNormalMenuItem = i
		self.Bind(wx.EVT_MENU, self.OnNormalSwitch, i)
		expertMenu.AppendSeparator()

		i = expertMenu.Append(-1, _("Open expert settings...\tCTRL+E"))
		self.normalModeOnlyItems.append(i)
		self.Bind(wx.EVT_MENU, self.OnExpertOpen, i)
		expertMenu.AppendSeparator()
		i = expertMenu.Append(-1, _("Run first run wizard..."))
		self.Bind(wx.EVT_MENU, self.OnFirstRunWizard, i)
		self.bedLevelWizardMenuItem = expertMenu.Append(-1, _("Run bed leveling wizard..."))
		self.Bind(wx.EVT_MENU, self.OnBedLevelWizard, self.bedLevelWizardMenuItem)
		self.headOffsetWizardMenuItem = expertMenu.Append(-1, _("Run head offset wizard..."))
		self.Bind(wx.EVT_MENU, self.OnHeadOffsetWizard, self.headOffsetWizardMenuItem)

		self.menubar.Append(expertMenu, _("Expert"))

		helpMenu = wx.Menu()
		i = helpMenu.Append(-1, _("Online documentation..."))
		self.Bind(wx.EVT_MENU, lambda e: webbrowser.open('http://daid.github.com/Cura'), i)
		i = helpMenu.Append(-1, _("Report a problem..."))
		self.Bind(wx.EVT_MENU, lambda e: webbrowser.open('https://github.com/daid/Cura/issues'), i)
		i = helpMenu.Append(-1, _("Check for update..."))
		self.Bind(wx.EVT_MENU, self.OnCheckForUpdate, i)
		i = helpMenu.Append(-1, _("Open YouMagine website..."))
		self.Bind(wx.EVT_MENU, lambda e: webbrowser.open('https://www.youmagine.com/'), i)
		i = helpMenu.Append(-1, _("About Cura..."))
		self.Bind(wx.EVT_MENU, self.OnAbout, i)
		self.menubar.Append(helpMenu, _("Help"))
		self.SetMenuBar(self.menubar)

		self.splitter = wx.SplitterWindow(self, style = wx.SP_3D | wx.SP_LIVE_UPDATE)
		self.leftPane = wx.Panel(self.splitter, style=wx.BORDER_NONE)
		self.rightPane = wx.Panel(self.splitter, style=wx.BORDER_NONE)
		self.splitter.Bind(wx.EVT_SPLITTER_DCLICK, lambda evt: evt.Veto())

		##Gui components##
		self.simpleSettingsPanel = simpleMode.simpleModePanel(self.leftPane, lambda : self.scene.sceneUpdated())
		self.normalSettingsPanel = normalSettingsPanel(self.leftPane, lambda : self.scene.sceneUpdated())

		self.leftSizer = wx.BoxSizer(wx.VERTICAL)
		self.leftSizer.Add(self.simpleSettingsPanel, 1)
		self.leftSizer.Add(self.normalSettingsPanel, 1, wx.EXPAND)
		self.leftPane.SetSizer(self.leftSizer)

		#Preview window
		self.scene = sceneView.SceneView(self.rightPane)

		#Main sizer, to position the preview window, buttons and tab control
		sizer = wx.BoxSizer()
		self.rightPane.SetSizer(sizer)
		sizer.Add(self.scene, 1, flag=wx.EXPAND)

		# Main window sizer
		sizer = wx.BoxSizer(wx.VERTICAL)
		self.SetSizer(sizer)
		sizer.Add(self.splitter, 1, wx.EXPAND)
		sizer.Layout()
		self.sizer = sizer

		self.updateProfileToAllControls()

		self.SetBackgroundColour(self.normalSettingsPanel.GetBackgroundColour())

		self.simpleSettingsPanel.Show(False)
		self.normalSettingsPanel.Show(False)

		# Set default window size & position
		self.SetSize((wx.Display().GetClientArea().GetWidth()/2,wx.Display().GetClientArea().GetHeight()/2))
		self.Centre()

		#Timer set; used to check if profile is on the clipboard
		self.timer = wx.Timer(self)
		self.Bind(wx.EVT_TIMER, self.onTimer)
		self.timer.Start(1000)
		self.lastTriedClipboard = profile.getProfileString()

		# Restore the window position, size & state from the preferences file
		try:
			if profile.getPreference('window_maximized') == 'True':
				self.Maximize(True)
			else:
				posx = int(profile.getPreference('window_pos_x'))
				posy = int(profile.getPreference('window_pos_y'))
				width = int(profile.getPreference('window_width'))
				height = int(profile.getPreference('window_height'))
				if posx > 0 or posy > 0:
					self.SetPosition((posx,posy))
				if width > 0 and height > 0:
					self.SetSize((width,height))

			self.normalSashPos = int(profile.getPreference('window_normal_sash'))
		except:
			self.normalSashPos = 0
			self.Maximize(True)
		if self.normalSashPos < self.normalSettingsPanel.printPanel.GetBestSize()[0] + 5:
			self.normalSashPos = self.normalSettingsPanel.printPanel.GetBestSize()[0] + 5

		self.splitter.SplitVertically(self.leftPane, self.rightPane, self.normalSashPos)

		if wx.Display.GetFromPoint(self.GetPosition()) < 0:
			self.Centre()
		if wx.Display.GetFromPoint((self.GetPositionTuple()[0] + self.GetSizeTuple()[1], self.GetPositionTuple()[1] + self.GetSizeTuple()[1])) < 0:
			self.Centre()
		if wx.Display.GetFromPoint(self.GetPosition()) < 0:
			self.SetSize((800,600))
			self.Centre()

		self.updateSliceMode()
		self.scene.SetFocus()

	def onTimer(self, e):
		#Check if there is something in the clipboard
		profileString = ""
		try:
			if not wx.TheClipboard.IsOpened():
				if not wx.TheClipboard.Open():
					return
				do = wx.TextDataObject()
				if wx.TheClipboard.GetData(do):
					profileString = do.GetText()
				wx.TheClipboard.Close()

				startTag = "CURA_PROFILE_STRING:"
				if startTag in profileString:
					#print "Found correct syntax on clipboard"
					profileString = profileString.replace("\n","").strip()
					profileString = profileString[profileString.find(startTag)+len(startTag):]
					if profileString != self.lastTriedClipboard:
						print profileString
						self.lastTriedClipboard = profileString
						profile.setProfileFromString(profileString)
						self.scene.notification.message("Loaded new profile from clipboard.")
						self.updateProfileToAllControls()
		except:
			print "Unable to read from clipboard"


	def updateSliceMode(self):
		isSimple = profile.getPreference('startMode') == 'Simple'

		self.normalSettingsPanel.Show(not isSimple)
		self.simpleSettingsPanel.Show(isSimple)
		self.leftPane.Layout()

		for i in self.normalModeOnlyItems:
			i.Enable(not isSimple)
		if isSimple:
			self.switchToQuickprintMenuItem.Check()
		else:
			self.switchToNormalMenuItem.Check()

		# Set splitter sash position & size
		if isSimple:
			# Save normal mode sash
			self.normalSashPos = self.splitter.GetSashPosition()

			# Change location of sash to width of quick mode pane
			(width, height) = self.simpleSettingsPanel.GetSizer().GetSize()
			self.splitter.SetSashPosition(width, True)

			# Disable sash
			self.splitter.SetSashSize(0)
		else:
			self.splitter.SetSashPosition(self.normalSashPos, True)
			# Enabled sash
			self.splitter.SetSashSize(4)
		self.defaultFirmwareInstallMenuItem.Enable(firmwareInstall.getDefaultFirmware() is not None)
		if profile.getMachineSetting('machine_type') == 'ultimaker2':
			self.bedLevelWizardMenuItem.Enable(False)
			self.headOffsetWizardMenuItem.Enable(False)
		if int(profile.getMachineSetting('extruder_amount')) < 2:
			self.headOffsetWizardMenuItem.Enable(False)
		self.scene.updateProfileToControls()
		self.scene._scene.pushFree()

	def onOneAtATimeSwitch(self, e):
		profile.putPreference('oneAtATime', self.oneAtATime.IsChecked())
		if self.oneAtATime.IsChecked() and profile.getMachineSettingFloat('extruder_head_size_height') < 1:
			wx.MessageBox(_('For "One at a time" printing, you need to have entered the correct head size and gantry height in the machine settings'), _('One at a time warning'), wx.OK | wx.ICON_WARNING)
		self.scene.updateProfileToControls()
		self.scene._scene.pushFree()
		self.scene.sceneUpdated()

	def OnPreferences(self, e):
		prefDialog = preferencesDialog.preferencesDialog(self)
		prefDialog.Centre()
		prefDialog.Show()
		prefDialog.Raise()
		wx.CallAfter(prefDialog.Show)

	def OnMachineSettings(self, e):
		prefDialog = preferencesDialog.machineSettingsDialog(self)
		prefDialog.Centre()
		prefDialog.Show()
		prefDialog.Raise()

	def OnDropFiles(self, files):
		if len(files) > 0:
			self.updateProfileToAllControls()
		self.scene.loadFiles(files)

	def OnModelMRU(self, e):
		fileNum = e.GetId() - self.ID_MRU_MODEL1
		path = self.modelFileHistory.GetHistoryFile(fileNum)
		# Update Model MRU
		self.modelFileHistory.AddFileToHistory(path)  # move up the list
		self.config.SetPath("/ModelMRU")
		self.modelFileHistory.Save(self.config)
		self.config.Flush()
		# Load Model
		profile.putPreference('lastFile', path)
		filelist = [ path ]
		self.scene.loadFiles(filelist)

	def addToModelMRU(self, file):
		self.modelFileHistory.AddFileToHistory(file)
		self.config.SetPath("/ModelMRU")
		self.modelFileHistory.Save(self.config)
		self.config.Flush()

	def OnProfileMRU(self, e):
		fileNum = e.GetId() - self.ID_MRU_PROFILE1
		path = self.profileFileHistory.GetHistoryFile(fileNum)
		# Update Profile MRU
		self.profileFileHistory.AddFileToHistory(path)  # move up the list
		self.config.SetPath("/ProfileMRU")
		self.profileFileHistory.Save(self.config)
		self.config.Flush()
		# Load Profile
		profile.loadProfile(path)
		self.updateProfileToAllControls()

	def addToProfileMRU(self, file):
		self.profileFileHistory.AddFileToHistory(file)
		self.config.SetPath("/ProfileMRU")
		self.profileFileHistory.Save(self.config)
		self.config.Flush()

	def updateProfileToAllControls(self):
		self.scene.updateProfileToControls()
		self.normalSettingsPanel.updateProfileToControls()
		self.simpleSettingsPanel.updateProfileToControls()

	def reloadSettingPanels(self):
		self.leftSizer.Detach(self.simpleSettingsPanel)
		self.leftSizer.Detach(self.normalSettingsPanel)
		self.simpleSettingsPanel.Destroy()
		self.normalSettingsPanel.Destroy()
		self.simpleSettingsPanel = simpleMode.simpleModePanel(self.leftPane, lambda : self.scene.sceneUpdated())
		self.normalSettingsPanel = normalSettingsPanel(self.leftPane, lambda : self.scene.sceneUpdated())
		self.leftSizer.Add(self.simpleSettingsPanel, 1)
		self.leftSizer.Add(self.normalSettingsPanel, 1, wx.EXPAND)
		self.updateSliceMode()
		self.updateProfileToAllControls()

	def updateMachineMenu(self):
		#Remove all items so we can rebuild the menu. Inserting items seems to cause crashes, so this is the safest way.
		for item in self.machineMenu.GetMenuItems():
			self.machineMenu.RemoveItem(item)

		#Add a menu item for each machine configuration.
		for n in xrange(0, profile.getMachineCount()):
			i = self.machineMenu.Append(n + 0x1000, profile.getMachineSetting('machine_name', n).title(), kind=wx.ITEM_RADIO)
			if n == int(profile.getPreferenceFloat('active_machine')):
				i.Check(True)
			self.Bind(wx.EVT_MENU, lambda e: self.OnSelectMachine(e.GetId() - 0x1000), i)

		self.machineMenu.AppendSeparator()

		i = self.machineMenu.Append(-1, _("Machine settings..."))
		self.Bind(wx.EVT_MENU, self.OnMachineSettings, i)

		#Add tools for machines.
		self.machineMenu.AppendSeparator()

		self.defaultFirmwareInstallMenuItem = self.machineMenu.Append(-1, _("Install default firmware..."))
		self.Bind(wx.EVT_MENU, self.OnDefaultMarlinFirmware, self.defaultFirmwareInstallMenuItem)

		i = self.machineMenu.Append(-1, _("Install custom firmware..."))
		self.Bind(wx.EVT_MENU, self.OnCustomFirmware, i)

	def OnLoadProfile(self, e):
		dlg=wx.FileDialog(self, _("Select profile file to load"), os.path.split(profile.getPreference('lastFile'))[0], style=wx.FD_OPEN|wx.FD_FILE_MUST_EXIST)
		dlg.SetWildcard("ini files (*.ini)|*.ini")
		if dlg.ShowModal() == wx.ID_OK:
			profileFile = dlg.GetPath()
			profile.loadProfile(profileFile)
			self.updateProfileToAllControls()

			# Update the Profile MRU
			self.addToProfileMRU(profileFile)
		dlg.Destroy()

	def OnLoadProfileFromGcode(self, e):
		dlg=wx.FileDialog(self, _("Select gcode file to load profile from"), os.path.split(profile.getPreference('lastFile'))[0], style=wx.FD_OPEN|wx.FD_FILE_MUST_EXIST)
		dlg.SetWildcard("gcode files (*%s)|*%s;*%s" % (profile.getGCodeExtension(), profile.getGCodeExtension(), profile.getGCodeExtension()[0:2]))
		if dlg.ShowModal() == wx.ID_OK:
			gcodeFile = dlg.GetPath()
			f = open(gcodeFile, 'r')
			hasProfile = False
			for line in f:
				if line.startswith(';CURA_PROFILE_STRING:'):
					profile.setProfileFromString(line[line.find(':')+1:].strip())
					if ';{profile_string}' not in profile.getProfileSetting('end.gcode'):
						profile.putProfileSetting('end.gcode', profile.getProfileSetting('end.gcode') + '\n;{profile_string}')
					hasProfile = True
			if hasProfile:
				self.updateProfileToAllControls()
			else:
				wx.MessageBox(_("No profile found in GCode file.\nThis feature only works with GCode files made by Cura 12.07 or newer."), _("Profile load error"), wx.OK | wx.ICON_INFORMATION)
		dlg.Destroy()

	def OnSaveProfile(self, e):
		dlg=wx.FileDialog(self, _("Select profile file to save"), os.path.split(profile.getPreference('lastFile'))[0], style=wx.FD_SAVE)
		dlg.SetWildcard("ini files (*.ini)|*.ini")
		if dlg.ShowModal() == wx.ID_OK:
			profileFile = dlg.GetPath()
			if platform.system() == 'Linux': #hack for linux, as for some reason the .ini is not appended.
				profileFile += '.ini'
			profile.saveProfile(profileFile)
		dlg.Destroy()

	def OnResetProfile(self, e):
		dlg = wx.MessageDialog(self, _("This will reset all profile settings to defaults.\nUnless you have saved your current profile, all settings will be lost!\nDo you really want to reset?"), _("Profile reset"), wx.YES_NO | wx.ICON_QUESTION)
		result = dlg.ShowModal() == wx.ID_YES
		dlg.Destroy()
		if result:
			profile.resetProfile()
			self.updateProfileToAllControls()

	def OnSimpleSwitch(self, e):
		profile.putPreference('startMode', 'Simple')
		self.updateSliceMode()

	def OnNormalSwitch(self, e):
		profile.putPreference('startMode', 'Normal')
		self.updateSliceMode()

	def OnDefaultMarlinFirmware(self, e):
		firmwareInstall.InstallFirmware()

	def OnCustomFirmware(self, e):
		if profile.getMachineSetting('machine_type').startswith('ultimaker'):
			wx.MessageBox(_("Warning: Installing a custom firmware does not guarantee that you machine will function correctly, and could damage your machine."), _("Firmware update"), wx.OK | wx.ICON_EXCLAMATION)
		dlg=wx.FileDialog(self, _("Open firmware to upload"), os.path.split(profile.getPreference('lastFile'))[0], style=wx.FD_OPEN|wx.FD_FILE_MUST_EXIST)
		dlg.SetWildcard("HEX file (*.hex)|*.hex;*.HEX")
		if dlg.ShowModal() == wx.ID_OK:
			filename = dlg.GetPath()
			if not(os.path.exists(filename)):
				return
			#For some reason my Ubuntu 10.10 crashes here.
			firmwareInstall.InstallFirmware(filename)

	def OnFirstRunWizard(self, e):
		self.Hide()
		configWizard.configWizard()
		self.Show()
		self.reloadSettingPanels()

	def OnSelectMachine(self, index):
		profile.setActiveMachine(index)
		self.reloadSettingPanels()

	def OnBedLevelWizard(self, e):
		configWizard.bedLevelWizard()

	def OnHeadOffsetWizard(self, e):
		configWizard.headOffsetWizard()

	def OnExpertOpen(self, e):
		ecw = expertConfig.expertConfigWindow(lambda : self.scene.sceneUpdated())
		ecw.Centre()
		ecw.Show()

	def OnMinecraftImport(self, e):
		mi = minecraftImport.minecraftImportWindow(self)
		mi.Centre()
		mi.Show(True)

	def OnPIDDebugger(self, e):
		debugger = pidDebugger.debuggerWindow(self)
		debugger.Centre()
		debugger.Show(True)

	def onCopyProfileClipboard(self, e):
		try:
			if not wx.TheClipboard.IsOpened():
				wx.TheClipboard.Open()
				clipData = wx.TextDataObject()
				self.lastTriedClipboard = profile.getProfileString()
				profileString = profile.insertNewlines("CURA_PROFILE_STRING:" + self.lastTriedClipboard)
				clipData.SetText(profileString)
				wx.TheClipboard.SetData(clipData)
				wx.TheClipboard.Close()
		except:
			print "Could not write to clipboard, unable to get ownership. Another program is using the clipboard."

	def OnCheckForUpdate(self, e):
		newVersion = version.checkForNewerVersion()
		if newVersion is not None:
			if wx.MessageBox(_("A new version of Cura is available, would you like to download?"), _("New version available"), wx.YES_NO | wx.ICON_INFORMATION) == wx.YES:
				webbrowser.open(newVersion)
		else:
			wx.MessageBox(_("You are running the latest version of Cura!"), _("Awesome!"), wx.ICON_INFORMATION)

	def OnAbout(self, e):
		aboutBox = aboutWindow.aboutWindow()
		aboutBox.Centre()
		aboutBox.Show()

	def OnClose(self, e):
		profile.saveProfile(profile.getDefaultProfilePath(), True)

		# Save the window position, size & state from the preferences file
		profile.putPreference('window_maximized', self.IsMaximized())
		if not self.IsMaximized() and not self.IsIconized():
			(posx, posy) = self.GetPosition()
			profile.putPreference('window_pos_x', posx)
			profile.putPreference('window_pos_y', posy)
			(width, height) = self.GetSize()
			profile.putPreference('window_width', width)
			profile.putPreference('window_height', height)

			# Save normal sash position.  If in normal mode (!simple mode), get last position of sash before saving it...
			isSimple = profile.getPreference('startMode') == 'Simple'
			if not isSimple:
				self.normalSashPos = self.splitter.GetSashPosition()
			profile.putPreference('window_normal_sash', self.normalSashPos)

		#HACK: Set the paint function of the glCanvas to nothing so it won't keep refreshing. Which can keep wxWidgets from quiting.
		print "Closing down"
		self.scene.OnPaint = lambda e : e
		self.scene._engine.cleanup()
		self.Destroy()

	def OnQuit(self, e):
		self.Close()

class normalSettingsPanel(configBase.configPanelBase):
	"Main user interface window"
	def __init__(self, parent, callback = None):
		super(normalSettingsPanel, self).__init__(parent, callback)

		#Main tabs
		self.nb = wx.Notebook(self)
		self.SetSizer(wx.BoxSizer(wx.HORIZONTAL))
		self.GetSizer().Add(self.nb, 1, wx.EXPAND)

		(left, right, self.printPanel) = self.CreateDynamicConfigTab(self.nb, 'Basic')
		self._addSettingsToPanels('basic', left, right)
		self.SizeLabelWidths(left, right)

		(left, right, self.advancedPanel) = self.CreateDynamicConfigTab(self.nb, 'Advanced')
		self._addSettingsToPanels('advanced', left, right)
		self.SizeLabelWidths(left, right)

		#Plugin page
		self.pluginPanel = pluginPanel.pluginPanel(self.nb, callback)
		self.nb.AddPage(self.pluginPanel, _("Plugins"))

		#Alteration page
		if profile.getMachineSetting('gcode_flavor') == 'UltiGCode':
			self.alterationPanel = None
		else:
			self.alterationPanel = alterationPanel.alterationPanel(self.nb, callback)
			self.nb.AddPage(self.alterationPanel, "Start/End-GCode")

		self.Bind(wx.EVT_SIZE, self.OnSize)

		self.nb.SetSize(self.GetSize())
		self.UpdateSize(self.printPanel)
		self.UpdateSize(self.advancedPanel)

	def _addSettingsToPanels(self, category, left, right):
		count = len(profile.getSubCategoriesFor(category)) + len(profile.getSettingsForCategory(category))

		p = left
		n = 0
		for title in profile.getSubCategoriesFor(category):
			n += 1 + len(profile.getSettingsForCategory(category, title))
			if n > count / 2:
				p = right
			configBase.TitleRow(p, _(title))
			for s in profile.getSettingsForCategory(category, title):
				configBase.SettingRow(p, s.getName())

	def SizeLabelWidths(self, left, right):
		leftWidth = self.getLabelColumnWidth(left)
		rightWidth = self.getLabelColumnWidth(right)
		maxWidth = max(leftWidth, rightWidth)
		self.setLabelColumnWidth(left, maxWidth)
		self.setLabelColumnWidth(right, maxWidth)

	def OnSize(self, e):
		# Make the size of the Notebook control the same size as this control
		self.nb.SetSize(self.GetSize())

		# Propegate the OnSize() event (just in case)
		e.Skip()

		# Perform out resize magic
		self.UpdateSize(self.printPanel)
		self.UpdateSize(self.advancedPanel)

	def UpdateSize(self, configPanel):
		sizer = configPanel.GetSizer()

		# Pseudocde
		# if horizontal:
		#     if width(col1) < best_width(col1) || width(col2) < best_width(col2):
		#         switch to vertical
		# else:
		#     if width(col1) > (best_width(col1) + best_width(col1)):
		#         switch to horizontal
		#

		col1 = configPanel.leftPanel
		colSize1 = col1.GetSize()
		colBestSize1 = col1.GetBestSize()
		col2 = configPanel.rightPanel
		colSize2 = col2.GetSize()
		colBestSize2 = col2.GetBestSize()

		orientation = sizer.GetOrientation()

		if orientation == wx.HORIZONTAL:
			if (colSize1[0] <= colBestSize1[0]) or (colSize2[0] <= colBestSize2[0]):
				configPanel.Freeze()
				sizer = wx.BoxSizer(wx.VERTICAL)
				sizer.Add(configPanel.leftPanel, flag=wx.EXPAND)
				sizer.Add(configPanel.rightPanel, flag=wx.EXPAND)
				configPanel.SetSizer(sizer)
				#sizer.Layout()
				configPanel.Layout()
				self.Layout()
				configPanel.Thaw()
		else:
			if max(colSize1[0], colSize2[0]) > (colBestSize1[0] + colBestSize2[0]):
				configPanel.Freeze()
				sizer = wx.BoxSizer(wx.HORIZONTAL)
				sizer.Add(configPanel.leftPanel, proportion=1, border=35, flag=wx.EXPAND)
				sizer.Add(configPanel.rightPanel, proportion=1, flag=wx.EXPAND)
				configPanel.SetSizer(sizer)
				#sizer.Layout()
				configPanel.Layout()
				self.Layout()
				configPanel.Thaw()

	def updateProfileToControls(self):
		super(normalSettingsPanel, self).updateProfileToControls()
		if self.alterationPanel is not None:
			self.alterationPanel.updateProfileToControls()
		self.pluginPanel.updateProfileToControls()

########NEW FILE########
__FILENAME__ = newVersionDialog
__copyright__ = "Copyright (C) 2013 David Braam - Released under terms of the AGPLv3 License"

import wx
from Cura.gui import firmwareInstall
from Cura.util import version
from Cura.util import profile

class newVersionDialog(wx.Dialog):
	def __init__(self):
		super(newVersionDialog, self).__init__(None, title="Welcome to the new version!")

		wx.EVT_CLOSE(self, self.OnClose)

		p = wx.Panel(self)
		self.panel = p
		s = wx.BoxSizer()
		self.SetSizer(s)
		s.Add(p, flag=wx.ALL, border=15)
		s = wx.BoxSizer(wx.VERTICAL)
		p.SetSizer(s)

		title = wx.StaticText(p, -1, 'Cura - ' + version.getVersion())
		title.SetFont(wx.Font(18, wx.SWISS, wx.NORMAL, wx.BOLD))
		s.Add(title, flag=wx.ALIGN_CENTRE|wx.EXPAND|wx.BOTTOM, border=5)
		s.Add(wx.StaticText(p, -1, 'Welcome to the new version of Cura.'))
		s.Add(wx.StaticText(p, -1, '(This dialog is only shown once)'))
		s.Add(wx.StaticLine(p), flag=wx.EXPAND|wx.TOP|wx.BOTTOM, border=10)
		s.Add(wx.StaticText(p, -1, 'New in this version:'))
		s.Add(wx.StaticText(p, -1, '* Updated drivers for Windows 8.1.'))
		s.Add(wx.StaticText(p, -1, '* Added better raft support with surface layers and an air-gap. Special thanks to Gregoire Passault.'))
		s.Add(wx.StaticText(p, -1, '* Improved outer surface quality on high detail prints.'))
		s.Add(wx.StaticText(p, -1, '* Fixed bug with multiple machines and different start/end GCode.'))
		s.Add(wx.StaticText(p, -1, '* Added initial support for BitsFromBytes machines.'))
		s.Add(wx.StaticText(p, -1, '* Improved the Pronterface UI with buttons to set temperature and extrusion buttons.'))
		s.Add(wx.StaticText(p, -1, '* Improved bridging detection.'))

		self.hasUltimaker = None
		self.hasUltimaker2 = None
		for n in xrange(0, profile.getMachineCount()):
			if profile.getMachineSetting('machine_type', n) == 'ultimaker':
				self.hasUltimaker = n
			if profile.getMachineSetting('machine_type', n) == 'ultimaker2':
				self.hasUltimaker2 = n
		if self.hasUltimaker is not None and False:
			s.Add(wx.StaticLine(p), flag=wx.EXPAND|wx.TOP|wx.BOTTOM, border=10)
			s.Add(wx.StaticText(p, -1, 'New firmware for your Ultimaker Original:'))
			s.Add(wx.StaticText(p, -1, '* .'))
			button = wx.Button(p, -1, 'Install now')
			self.Bind(wx.EVT_BUTTON, self.OnUltimakerFirmware, button)
			s.Add(button, flag=wx.TOP, border=5)
		if self.hasUltimaker2 is not None:
			s.Add(wx.StaticLine(p), flag=wx.EXPAND|wx.TOP|wx.BOTTOM, border=10)
			s.Add(wx.StaticText(p, -1, 'New firmware for your Ultimaker2: (14.04.1)'))
			s.Add(wx.StaticText(p, -1, '* Improved the start of the print, first moves the bed up before moving to the print.'))
			s.Add(wx.StaticText(p, -1, '* Made sure the head does not bump into the front of the casing at first startup.'))
			s.Add(wx.StaticText(p, -1, '* Fixed support for the PauseAtZ plugin.'))
			button = wx.Button(p, -1, 'Install now')
			self.Bind(wx.EVT_BUTTON, self.OnUltimaker2Firmware, button)
			s.Add(button, flag=wx.TOP, border=5)

		s.Add(wx.StaticLine(p), flag=wx.EXPAND|wx.TOP|wx.BOTTOM, border=10)
		button = wx.Button(p, -1, 'Ok')
		self.Bind(wx.EVT_BUTTON, self.OnOk, button)
		s.Add(button, flag=wx.TOP|wx.ALIGN_RIGHT, border=5)

		self.Fit()
		self.Centre()

	def OnUltimakerFirmware(self, e):
		firmwareInstall.InstallFirmware(machineIndex=self.hasUltimaker)

	def OnUltimaker2Firmware(self, e):
		firmwareInstall.InstallFirmware(machineIndex=self.hasUltimaker2)

	def OnOk(self, e):
		self.Close()

	def OnClose(self, e):
		self.Destroy()

########NEW FILE########
__FILENAME__ = pluginPanel
__copyright__ = "Copyright (C) 2013 David Braam - Released under terms of the AGPLv3 License"

import wx
import os
import webbrowser
from wx.lib import scrolledpanel

from Cura.util import profile
from Cura.util import pluginInfo
from Cura.util import explorer

class pluginPanel(wx.Panel):
	def __init__(self, parent, callback):
		wx.Panel.__init__(self, parent,-1)
		#Plugin page
		self.pluginList = pluginInfo.getPluginList("postprocess")
		self.callback = callback

		sizer = wx.GridBagSizer(2, 2)
		self.SetSizer(sizer)

		pluginStringList = []
		for p in self.pluginList:
			pluginStringList.append(p.getName())

		self.listbox = wx.ListBox(self, -1, choices=pluginStringList)
		title = wx.StaticText(self, -1, _("Plugins:"))
		title.SetFont(wx.Font(wx.SystemSettings.GetFont(wx.SYS_ANSI_VAR_FONT).GetPointSize(), wx.FONTFAMILY_DEFAULT, wx.NORMAL, wx.FONTWEIGHT_BOLD))
		helpButton = wx.Button(self, -1, '?', style=wx.BU_EXACTFIT)
		addButton = wx.Button(self, -1, 'V', style=wx.BU_EXACTFIT)
		openPluginLocationButton = wx.Button(self, -1, _("Open plugin location"))
		sb = wx.StaticBox(self, label=_("Enabled plugins"))
		boxsizer = wx.StaticBoxSizer(sb, wx.VERTICAL)
		self.pluginEnabledPanel = scrolledpanel.ScrolledPanel(self)
		self.pluginEnabledPanel.SetupScrolling(False, True)

		sizer.Add(title, (0,0), border=10, flag=wx.ALIGN_CENTER_VERTICAL|wx.LEFT|wx.TOP)
		sizer.Add(helpButton, (0,1), border=10, flag=wx.ALIGN_RIGHT|wx.RIGHT|wx.TOP)
		sizer.Add(self.listbox, (1,0), span=(2,2), border=10, flag=wx.EXPAND|wx.LEFT|wx.RIGHT)
		sizer.Add(addButton, (3,0), span=(1,2), border=5, flag=wx.ALIGN_CENTER_HORIZONTAL|wx.ALIGN_BOTTOM)
		sizer.Add(boxsizer, (4,0), span=(4,2), border=10, flag=wx.EXPAND|wx.LEFT|wx.RIGHT)
		sizer.Add(openPluginLocationButton, (8, 0), border=10, flag=wx.LEFT|wx.BOTTOM)
		boxsizer.Add(self.pluginEnabledPanel, 1, flag=wx.EXPAND)

		sizer.AddGrowableCol(0)
		sizer.AddGrowableRow(1) # Plugins list box
		sizer.AddGrowableRow(4) # Enabled plugins
		sizer.AddGrowableRow(5) # Enabled plugins
		sizer.AddGrowableRow(6) # Enabled plugins

		sizer = wx.BoxSizer(wx.VERTICAL)
		self.pluginEnabledPanel.SetSizer(sizer)

		self.Bind(wx.EVT_BUTTON, self.OnAdd, addButton)
		self.Bind(wx.EVT_BUTTON, self.OnGeneralHelp, helpButton)
		self.Bind(wx.EVT_BUTTON, self.OnOpenPluginLocation, openPluginLocationButton)
		self.listbox.Bind(wx.EVT_LEFT_DCLICK, self.OnAdd)
		self.panelList = []
		self.updateProfileToControls()

	def updateProfileToControls(self):
		self.pluginConfig = pluginInfo.getPostProcessPluginConfig()
		for p in self.panelList:
			p.Show(False)
			self.pluginEnabledPanel.GetSizer().Detach(p)
		self.panelList = []
		for pluginConfig in self.pluginConfig:
			self._buildPluginPanel(pluginConfig)

	def _buildPluginPanel(self, pluginConfig):
		plugin = None
		for pluginTest in self.pluginList:
			if pluginTest.getFilename() == pluginConfig['filename']:
				plugin = pluginTest
		if plugin is None:
			return False

		pluginPanel = wx.Panel(self.pluginEnabledPanel)
		s = wx.GridBagSizer(2, 2)
		pluginPanel.SetSizer(s)
		title = wx.StaticText(pluginPanel, -1, plugin.getName())
		title.SetFont(wx.Font(wx.SystemSettings.GetFont(wx.SYS_ANSI_VAR_FONT).GetPointSize(), wx.FONTFAMILY_DEFAULT, wx.NORMAL, wx.FONTWEIGHT_BOLD))
		remButton = wx.Button(pluginPanel, -1, 'X', style=wx.BU_EXACTFIT)
		helpButton = wx.Button(pluginPanel, -1, '?', style=wx.BU_EXACTFIT)
		s.Add(title, pos=(0,1), span=(1,2), flag=wx.ALIGN_BOTTOM|wx.TOP|wx.LEFT|wx.RIGHT, border=5)
		s.Add(helpButton, pos=(0,0), span=(1,1), flag=wx.TOP|wx.LEFT|wx.ALIGN_RIGHT, border=5)
		s.Add(remButton, pos=(0,3), span=(1,1), flag=wx.TOP|wx.RIGHT|wx.ALIGN_RIGHT, border=5)
		s.Add(wx.StaticLine(pluginPanel), pos=(1,0), span=(1,4), flag=wx.EXPAND|wx.LEFT|wx.RIGHT,border=3)
		info = wx.StaticText(pluginPanel, -1, plugin.getInfo())
		info.Wrap(300)
		s.Add(info, pos=(2,0), span=(1,4), flag=wx.EXPAND|wx.LEFT|wx.RIGHT,border=3)

		pluginPanel.paramCtrls = {}
		i = 0
		for param in plugin.getParams():
			value = param['default']
			if param['name'] in pluginConfig['params']:
				value = pluginConfig['params'][param['name']]

			ctrl = wx.TextCtrl(pluginPanel, -1, value)
			s.Add(wx.StaticText(pluginPanel, -1, param['description']), pos=(3+i,0), span=(1,2), flag=wx.LEFT|wx.RIGHT|wx.ALIGN_CENTER_VERTICAL,border=3)
			s.Add(ctrl, pos=(3+i,2), span=(1,2), flag=wx.EXPAND|wx.LEFT|wx.RIGHT,border=3)

			ctrl.Bind(wx.EVT_TEXT, self.OnSettingChange)

			pluginPanel.paramCtrls[param['name']] = ctrl

			i += 1
		s.Add(wx.StaticLine(pluginPanel), pos=(3+i,0), span=(1,4), flag=wx.EXPAND|wx.LEFT|wx.RIGHT,border=3)

		self.Bind(wx.EVT_BUTTON, self.OnRem, remButton)
		self.Bind(wx.EVT_BUTTON, self.OnHelp, helpButton)

		s.AddGrowableCol(1)
		pluginPanel.SetBackgroundColour(self.GetParent().GetBackgroundColour())
		self.pluginEnabledPanel.GetSizer().Add(pluginPanel, flag=wx.EXPAND)
		self.pluginEnabledPanel.Layout()
		self.pluginEnabledPanel.SetSize((1,1))
		self.Layout()
		self.pluginEnabledPanel.ScrollChildIntoView(pluginPanel)
		self.panelList.append(pluginPanel)
		return True

	def OnSettingChange(self, e):
		for panel in self.panelList:
			idx = self.panelList.index(panel)
			for k in panel.paramCtrls.keys():
				self.pluginConfig[idx]['params'][k] = panel.paramCtrls[k].GetValue()
		pluginInfo.setPostProcessPluginConfig(self.pluginConfig)
		self.callback()

	def OnAdd(self, e):
		if self.listbox.GetSelection() < 0:
			wx.MessageBox(_("You need to select a plugin before you can add anything."), _("Error: no plugin selected"), wx.OK | wx.ICON_INFORMATION)
			return
		p = self.pluginList[self.listbox.GetSelection()]
		newConfig = {'filename': p.getFilename(), 'params': {}}
		if not self._buildPluginPanel(newConfig):
			return
		self.pluginConfig.append(newConfig)
		pluginInfo.setPostProcessPluginConfig(self.pluginConfig)
		self.callback()

	def OnRem(self, e):
		panel = e.GetEventObject().GetParent()
		sizer = self.pluginEnabledPanel.GetSizer()
		idx = self.panelList.index(panel)

		panel.Show(False)
		for p in self.panelList:
			sizer.Detach(p)
		self.panelList.pop(idx)
		for p in self.panelList:
				sizer.Add(p, flag=wx.EXPAND)

		self.pluginEnabledPanel.Layout()
		self.pluginEnabledPanel.SetSize((1,1))
		self.Layout()

		self.pluginConfig.pop(idx)
		pluginInfo.setPostProcessPluginConfig(self.pluginConfig)
		self.callback()

	def OnHelp(self, e):
		panel = e.GetEventObject().GetParent()
		idx = self.panelList.index(panel)

		fname = self.pluginConfig[idx]['filename'].lower()
		fname = fname[0].upper() + fname[1:]
		fname = fname[:fname.rfind('.')]
		webbrowser.open('http://wiki.ultimaker.com/CuraPlugin:_' + fname)

	def OnGeneralHelp(self, e):
		webbrowser.open('http://wiki.ultimaker.com/Category:CuraPlugin')

	def OnOpenPluginLocation(self, e):
		if not os.path.exists(pluginInfo.getPluginBasePaths()[0]):
			os.mkdir(pluginInfo.getPluginBasePaths()[0])
		explorer.openExplorerPath(pluginInfo.getPluginBasePaths()[0])

########NEW FILE########
__FILENAME__ = preferencesDialog
__copyright__ = "Copyright (C) 2013 David Braam - Released under terms of the AGPLv3 License"

import wx

from Cura.gui import configWizard
from Cura.gui import configBase
from Cura.util import machineCom
from Cura.util import profile
from Cura.util import pluginInfo
from Cura.util import resources

class preferencesDialog(wx.Dialog):
	def __init__(self, parent):
		super(preferencesDialog, self).__init__(None, title="Preferences")

		wx.EVT_CLOSE(self, self.OnClose)

		self.parent = parent
		extruderCount = int(profile.getMachineSetting('extruder_amount'))

		self.panel = configBase.configPanelBase(self)

		left, right, main = self.panel.CreateConfigPanel(self)

		printWindowTypes = ['Basic']
		for p in pluginInfo.getPluginList('printwindow'):
			printWindowTypes.append(p.getName())
		configBase.TitleRow(left, _("Print window"))
		configBase.SettingRow(left, 'printing_window', printWindowTypes)

		configBase.TitleRow(left, _("Colours"))
		configBase.SettingRow(left, 'model_colour', wx.Colour)
		for i in xrange(1, extruderCount):
			configBase.SettingRow(left, 'model_colour%d' % (i+1), wx.Colour)

		if len(resources.getLanguageOptions()) > 1:
			configBase.TitleRow(left, _("Language"))
			configBase.SettingRow(left, 'language', map(lambda n: n[1], resources.getLanguageOptions()))

		configBase.TitleRow(right, _("Filament settings"))
		configBase.SettingRow(right, 'filament_physical_density')
		configBase.SettingRow(right, 'filament_cost_kg')
		configBase.SettingRow(right, 'filament_cost_meter')

		#configBase.TitleRow(right, 'Slicer settings')
		#configBase.SettingRow(right, 'save_profile')

		#configBase.TitleRow(right, 'SD Card settings')

		configBase.TitleRow(right, _("Cura settings"))
		configBase.SettingRow(right, 'auto_detect_sd')
		configBase.SettingRow(right, 'check_for_updates')
		configBase.SettingRow(right, 'submit_slice_information')

		self.okButton = wx.Button(right, -1, 'Ok')
		right.GetSizer().Add(self.okButton, (right.GetSizer().GetRows(), 0), flag=wx.BOTTOM, border=5)
		self.okButton.Bind(wx.EVT_BUTTON, lambda e: self.Close())

		main.Fit()
		self.Fit()

	def OnClose(self, e):
		#self.parent.reloadSettingPanels()
		self.Destroy()

class machineSettingsDialog(wx.Dialog):
	def __init__(self, parent):
		super(machineSettingsDialog, self).__init__(None, title="Machine settings")

		wx.EVT_CLOSE(self, self.OnClose)

		self.parent = parent

		self.panel = configBase.configPanelBase(self)
		self.SetSizer(wx.BoxSizer(wx.HORIZONTAL))
		self.GetSizer().Add(self.panel, 1, wx.EXPAND)
		self.nb = wx.Notebook(self.panel)
		self.panel.SetSizer(wx.BoxSizer(wx.VERTICAL))
		self.panel.GetSizer().Add(self.nb, 1, wx.EXPAND)

		for idx in xrange(0, profile.getMachineCount()):
			extruderCount = int(profile.getMachineSetting('extruder_amount', idx))
			left, right, main = self.panel.CreateConfigPanel(self.nb)
			configBase.TitleRow(left, _("Machine settings"))
			configBase.SettingRow(left, 'steps_per_e', index=idx)
			configBase.SettingRow(left, 'machine_width', index=idx)
			configBase.SettingRow(left, 'machine_depth', index=idx)
			configBase.SettingRow(left, 'machine_height', index=idx)
			configBase.SettingRow(left, 'extruder_amount', index=idx)
			configBase.SettingRow(left, 'has_heated_bed', index=idx)
			configBase.SettingRow(left, 'machine_center_is_zero', index=idx)
			configBase.SettingRow(left, 'machine_shape', index=idx)
			configBase.SettingRow(left, 'gcode_flavor', index=idx)

			configBase.TitleRow(right, _("Printer head size"))
			configBase.SettingRow(right, 'extruder_head_size_min_x', index=idx)
			configBase.SettingRow(right, 'extruder_head_size_min_y', index=idx)
			configBase.SettingRow(right, 'extruder_head_size_max_x', index=idx)
			configBase.SettingRow(right, 'extruder_head_size_max_y', index=idx)
			configBase.SettingRow(right, 'extruder_head_size_height', index=idx)

			for i in xrange(1, extruderCount):
				configBase.TitleRow(left, _("Extruder %d") % (i+1))
				configBase.SettingRow(left, 'extruder_offset_x%d' % (i), index=idx)
				configBase.SettingRow(left, 'extruder_offset_y%d' % (i), index=idx)

			configBase.TitleRow(right, _("Communication settings"))
			configBase.SettingRow(right, 'serial_port', ['AUTO'] + machineCom.serialList(), index=idx)
			configBase.SettingRow(right, 'serial_baud', ['AUTO'] + map(str, machineCom.baudrateList()), index=idx)

			self.nb.AddPage(main, profile.getMachineSetting('machine_name', idx).title())

		self.nb.SetSelection(int(profile.getPreferenceFloat('active_machine')))

		self.buttonPanel = wx.Panel(self.panel)
		self.panel.GetSizer().Add(self.buttonPanel)

		self.buttonPanel.SetSizer(wx.BoxSizer(wx.HORIZONTAL))
		self.okButton = wx.Button(self.buttonPanel, -1, 'Ok')
		self.okButton.Bind(wx.EVT_BUTTON, lambda e: self.Close())
		self.buttonPanel.GetSizer().Add(self.okButton, flag=wx.ALL, border=5)

		self.addButton = wx.Button(self.buttonPanel, -1, 'Add new machine')
		self.addButton.Bind(wx.EVT_BUTTON, self.OnAddMachine)
		self.buttonPanel.GetSizer().Add(self.addButton, flag=wx.ALL, border=5)

		self.remButton = wx.Button(self.buttonPanel, -1, 'Remove machine')
		self.remButton.Bind(wx.EVT_BUTTON, self.OnRemoveMachine)
		self.buttonPanel.GetSizer().Add(self.remButton, flag=wx.ALL, border=5)

		main.Fit()
		self.Fit()

	def OnAddMachine(self, e):
		self.Hide()
		self.parent.Hide()
		profile.setActiveMachine(profile.getMachineCount())
		configWizard.configWizard(True)
		self.parent.Show()
		self.parent.reloadSettingPanels()
		self.parent.updateMachineMenu()

		prefDialog = machineSettingsDialog(self.parent)
		prefDialog.Centre()
		prefDialog.Show()
		wx.CallAfter(self.Close)

	def OnRemoveMachine(self, e):
		if profile.getMachineCount() < 2:
			wx.MessageBox(_("Cannot remove the last machine configuration in Cura"), _("Machine remove error"), wx.OK | wx.ICON_ERROR)
			return

		self.Hide()
		profile.removeMachine(self.nb.GetSelection())
		self.parent.reloadSettingPanels()
		self.parent.updateMachineMenu()

		prefDialog = machineSettingsDialog(self.parent)
		prefDialog.Centre()
		prefDialog.Show()
		wx.CallAfter(self.Close)

	def OnClose(self, e):
		self.parent.reloadSettingPanels()
		self.Destroy()

########NEW FILE########
__FILENAME__ = printWindow
__copyright__ = "Copyright (C) 2013 David Braam - Released under terms of the AGPLv3 License"

import wx
import power
import time
import sys
import os
import ctypes

#TODO: This does not belong here!
if sys.platform.startswith('win'):
	def preventComputerFromSleeping(prevent):
		"""
		Function used to prevent the computer from going into sleep mode.
		:param prevent: True = Prevent the system from going to sleep from this point on.
		:param prevent: False = No longer prevent the system from going to sleep.
		"""
		ES_CONTINUOUS = 0x80000000
		ES_SYSTEM_REQUIRED = 0x00000001
		#SetThreadExecutionState returns 0 when failed, which is ignored. The function should be supported from windows XP and up.
		if prevent:
			ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED)
		else:
			ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS)

else:
	def preventComputerFromSleeping(prevent):
		#No preventComputerFromSleeping for MacOS and Linux yet.
		pass

class printWindowPlugin(wx.Frame):
	def __init__(self, parent, printerConnection, filename):
		super(printWindowPlugin, self).__init__(parent, -1, style=wx.CLOSE_BOX|wx.CLIP_CHILDREN|wx.CAPTION|wx.SYSTEM_MENU|wx.FRAME_FLOAT_ON_PARENT|wx.MINIMIZE_BOX, title=_("Printing on %s") % (printerConnection.getName()))
		self._printerConnection = printerConnection
		self._basePath = os.path.dirname(filename)
		self._backgroundImage = None
		self._colorCommandMap = {}
		self._buttonList = []
		self._termLog = None
		self._termInput = None
		self._termHistory = []
		self._termHistoryIdx = 0
		self._progressBar = None
		self._tempGraph = None
		self._infoText = None
		self._lastUpdateTime = time.time()

		variables = {
			'setImage': self.script_setImage,
			'addColorCommand': self.script_addColorCommand,
			'addTerminal': self.script_addTerminal,
			'addTemperatureGraph': self.script_addTemperatureGraph,
			'addProgressbar': self.script_addProgressbar,
			'addButton': self.script_addButton,
			'addSpinner': self.script_addSpinner,

			'sendGCode': self.script_sendGCode,
			'connect': self.script_connect,
			'startPrint': self.script_startPrint,
			'pausePrint': self.script_pausePrint,
			'cancelPrint': self.script_cancelPrint,
			'showErrorLog': self.script_showErrorLog,
		}
		execfile(filename, variables, variables)

		self.Bind(wx.EVT_ERASE_BACKGROUND, self.OnEraseBackground)
		self.Bind(wx.EVT_PAINT, self.OnDraw)
		self.Bind(wx.EVT_LEFT_DOWN, self.OnLeftClick)
		self.Bind(wx.EVT_CLOSE, self.OnClose)

		self._updateButtonStates()

		self._printerConnection.addCallback(self._doPrinterConnectionUpdate)

		if self._printerConnection.hasActiveConnection() and not self._printerConnection.isActiveConnectionOpen():
			self._printerConnection.openActiveConnection()
		preventComputerFromSleeping(True)

	def script_setImage(self, guiImage, mapImage):
		self._backgroundImage = wx.BitmapFromImage(wx.Image(os.path.join(self._basePath, guiImage)))
		self._mapImage = wx.Image(os.path.join(self._basePath, mapImage))
		self.SetClientSize(self._mapImage.GetSize())

	def script_addColorCommand(self, r, g, b, command, data = None):
		self._colorCommandMap[(r, g, b)] = (command, data)

	def script_addTerminal(self, r, g, b):
		x, y, w, h = self._getColoredRect(r, g, b)
		if x < 0 or self._termLog is not None:
			return
		f = wx.Font(8, wx.FONTFAMILY_MODERN, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, False)
		self._termLog = wx.TextCtrl(self, style=wx.TE_MULTILINE | wx.TE_DONTWRAP)
		self._termLog.SetFont(f)
		self._termLog.SetEditable(0)
		self._termInput = wx.TextCtrl(self, style=wx.TE_PROCESS_ENTER)
		self._termInput.SetFont(f)

		self._termLog.SetPosition((x, y))
		self._termLog.SetSize((w, h - self._termInput.GetSize().GetHeight()))
		self._termInput.SetPosition((x, y + h - self._termInput.GetSize().GetHeight()))
		self._termInput.SetSize((w, self._termInput.GetSize().GetHeight()))
		self.Bind(wx.EVT_TEXT_ENTER, self.OnTermEnterLine, self._termInput)
		self._termInput.Bind(wx.EVT_CHAR, self.OnTermKey)

	def script_addTemperatureGraph(self, r, g, b):
		x, y, w, h = self._getColoredRect(r, g, b)
		if x < 0 or self._tempGraph is not None:
			return
		self._tempGraph = TemperatureGraph(self)

		self._tempGraph.SetPosition((x, y))
		self._tempGraph.SetSize((w, h))

	def script_addProgressbar(self, r, g, b):
		x, y, w, h = self._getColoredRect(r, g, b)
		if x < 0:
			return
		self._progressBar = wx.Gauge(self, -1, range=1000)

		self._progressBar.SetPosition((x, y))
		self._progressBar.SetSize((w, h))

	def script_addButton(self, r, g, b, text, command, data = None):
		x, y, w, h = self._getColoredRect(r, g, b)
		if x < 0:
			return
		button = wx.Button(self, -1, _(text))
		button.SetPosition((x, y))
		button.SetSize((w, h))
		button.command = command
		button.data = data
		self._buttonList.append(button)
		self.Bind(wx.EVT_BUTTON, lambda e: command(data), button)

	def script_addSpinner(self, r, g, b, command, data):
		x, y, w, h = self._getColoredRect(r, g, b)
		if x < 0:
			return
		spinner = wx.SpinCtrl(self, -1, style=wx.TE_PROCESS_ENTER)
		spinner.SetRange(0, 300)
		spinner.SetPosition((x, y))
		spinner.SetSize((w, h))
		spinner.command = command
		spinner.data = data
		self._buttonList.append(spinner)
		self.Bind(wx.EVT_SPINCTRL, lambda e: command(data % (spinner.GetValue())), spinner)

	def _getColoredRect(self, r, g, b):
		for x in xrange(0, self._mapImage.GetWidth()):
			for y in xrange(0, self._mapImage.GetHeight()):
				if self._mapImage.GetRed(x, y) == r and self._mapImage.GetGreen(x, y) == g and self._mapImage.GetBlue(x, y) == b:
					w = 0
					while x+w < self._mapImage.GetWidth() and self._mapImage.GetRed(x + w, y) == r and self._mapImage.GetGreen(x + w, y) == g and self._mapImage.GetBlue(x + w, y) == b:
						w += 1
					h = 0
					while y+h < self._mapImage.GetHeight() and self._mapImage.GetRed(x, y + h) == r and self._mapImage.GetGreen(x, y + h) == g and self._mapImage.GetBlue(x, y + h) == b:
						h += 1
					return x, y, w, h
		print "Failed to find color: ", r, g, b
		return -1, -1, 1, 1

	def script_sendGCode(self, data = None):
		for line in data.split(';'):
			line = line.strip()
			if len(line) > 0:
				self._printerConnection.sendCommand(line)

	def script_connect(self, data = None):
		self._printerConnection.openActiveConnection()

	def script_startPrint(self, data = None):
		self._printerConnection.startPrint()

	def script_cancelPrint(self, e):
		self._printerConnection.cancelPrint()

	def script_pausePrint(self, e):
		self._printerConnection.pause(not self._printerConnection.isPaused())

	def script_showErrorLog(self, e):
		LogWindow(self._printerConnection.getErrorLog())

	def OnEraseBackground(self, e):
		pass

	def OnDraw(self, e):
		dc = wx.BufferedPaintDC(self, self._backgroundImage)

	def OnLeftClick(self, e):
		r = self._mapImage.GetRed(e.GetX(), e.GetY())
		g = self._mapImage.GetGreen(e.GetX(), e.GetY())
		b = self._mapImage.GetBlue(e.GetX(), e.GetY())
		if (r, g, b) in self._colorCommandMap:
			command = self._colorCommandMap[(r, g, b)]
			command[0](command[1])

	def OnClose(self, e):
		if self._printerConnection.hasActiveConnection():
			if self._printerConnection.isPrinting():
				pass #TODO: Give warning that the close will kill the print.
			self._printerConnection.closeActiveConnection()
		self._printerConnection.removeCallback(self._doPrinterConnectionUpdate)
		#TODO: When multiple printer windows are open, closing one will enable sleeping again.
		preventComputerFromSleeping(False)
		self.Destroy()

	def OnTermEnterLine(self, e):
		if not self._printerConnection.isAbleToSendDirectCommand():
			return
		line = self._termInput.GetValue()
		if line == '':
			return
		self._addTermLog('> %s\n' % (line))
		self._printerConnection.sendCommand(line)
		self._termHistory.append(line)
		self._termHistoryIdx = len(self._termHistory)
		self._termInput.SetValue('')

	def OnTermKey(self, e):
		if len(self._termHistory) > 0:
			if e.GetKeyCode() == wx.WXK_UP:
				self._termHistoryIdx -= 1
				if self._termHistoryIdx < 0:
					self._termHistoryIdx = len(self._termHistory) - 1
				self._termInput.SetValue(self._termHistory[self._termHistoryIdx])
			if e.GetKeyCode() == wx.WXK_DOWN:
				self._termHistoryIdx -= 1
				if self._termHistoryIdx >= len(self._termHistory):
					self._termHistoryIdx = 0
				self._termInput.SetValue(self._termHistory[self._termHistoryIdx])
		e.Skip()

	def _addTermLog(self, line):
		if self._termLog is not None:
			if len(self._termLog.GetValue()) > 10000:
				self._termLog.SetValue(self._termLog.GetValue()[-10000:])
			self._termLog.SetInsertionPointEnd()
			if type(line) != unicode:
				line = unicode(line, 'utf-8', 'replace')
			self._termLog.AppendText(line.encode('utf-8', 'replace'))

	def _updateButtonStates(self):
		for button in self._buttonList:
			if button.command == self.script_connect:
				button.Show(self._printerConnection.hasActiveConnection())
				button.Enable(not self._printerConnection.isActiveConnectionOpen() and not self._printerConnection.isActiveConnectionOpening())
			elif button.command == self.script_pausePrint:
				button.Show(self._printerConnection.hasPause())
				if not self._printerConnection.hasActiveConnection() or self._printerConnection.isActiveConnectionOpen():
					button.Enable(self._printerConnection.isPrinting() or self._printerConnection.isPaused())
				else:
					button.Enable(False)
			elif button.command == self.script_startPrint:
				if not self._printerConnection.hasActiveConnection() or self._printerConnection.isActiveConnectionOpen():
					button.Enable(not self._printerConnection.isPrinting())
				else:
					button.Enable(False)
			elif button.command == self.script_cancelPrint:
				if not self._printerConnection.hasActiveConnection() or self._printerConnection.isActiveConnectionOpen():
					button.Enable(self._printerConnection.isPrinting())
				else:
					button.Enable(False)
			elif button.command == self.script_showErrorLog:
				button.Show(self._printerConnection.isInErrorState())
		if self._termInput is not None:
			self._termInput.Enable(self._printerConnection.isAbleToSendDirectCommand())

	def _doPrinterConnectionUpdate(self, connection, extraInfo = None):
		wx.CallAfter(self.__doPrinterConnectionUpdate, connection, extraInfo)
		if self._tempGraph is not None:
			temp = []
			for n in xrange(0, 4):
				t = connection.getTemperature(0)
				if t is not None:
					temp.append(t)
				else:
					break
			self._tempGraph.addPoint(temp, [0] * len(temp), connection.getBedTemperature(), 0)

	def __doPrinterConnectionUpdate(self, connection, extraInfo):
		t = time.time()
		if self._lastUpdateTime + 0.5 > t and extraInfo is None:
			return
		self._lastUpdateTime = t

		if extraInfo is not None:
			self._addTermLog('< %s\n' % (extraInfo))

		self._updateButtonStates()
		if self._progressBar is not None:
			if connection.isPrinting():
				self._progressBar.SetValue(connection.getPrintProgress() * 1000)
			else:
				self._progressBar.SetValue(0)
		info = connection.getStatusString()
		info += '\n'
		if self._printerConnection.getTemperature(0) is not None:
			info += 'Temperature: %d' % (self._printerConnection.getTemperature(0))
		if self._printerConnection.getBedTemperature() > 0:
			info += ' Bed: %d' % (self._printerConnection.getBedTemperature())
		if self._infoText is not None:
			self._infoText.SetLabel(info)
		else:
			self.SetTitle(info.replace('\n', ', '))

class printWindowBasic(wx.Frame):
	"""
	Printing window for USB printing, network printing, and any other type of printer connection we can think off.
	This is only a basic window with minimal information.
	"""
	def __init__(self, parent, printerConnection):
		super(printWindowBasic, self).__init__(parent, -1, style=wx.CLOSE_BOX|wx.CLIP_CHILDREN|wx.CAPTION|wx.SYSTEM_MENU|wx.FRAME_TOOL_WINDOW|wx.FRAME_FLOAT_ON_PARENT, title=_("Printing on %s") % (printerConnection.getName()))
		self._printerConnection = printerConnection
		self._lastUpdateTime = 0

		self.SetSizer(wx.BoxSizer())
		self.panel = wx.Panel(self)
		self.GetSizer().Add(self.panel, 1, flag=wx.EXPAND)
		self.sizer = wx.GridBagSizer(2, 2)
		self.panel.SetSizer(self.sizer)

		self.powerWarningText = wx.StaticText(parent=self.panel,
			id=-1,
			label=_("Your computer is running on battery power.\nConnect your computer to AC power or your print might not finish."),
			style=wx.ALIGN_CENTER)
		self.powerWarningText.SetBackgroundColour('red')
		self.powerWarningText.SetForegroundColour('white')
		self.powerManagement = power.PowerManagement()
		self.powerWarningTimer = wx.Timer(self)
		self.Bind(wx.EVT_TIMER, self.OnPowerWarningChange, self.powerWarningTimer)
		self.OnPowerWarningChange(None)
		self.powerWarningTimer.Start(10000)

		self.statsText = wx.StaticText(self.panel, -1, _("InfoLine from printer connection\nInfoLine from dialog\nExtra line\nMore lines for layout\nMore lines for layout\nMore lines for layout"))

		self.connectButton = wx.Button(self.panel, -1, _("Connect"))
		#self.loadButton = wx.Button(self.panel, -1, 'Load')
		self.printButton = wx.Button(self.panel, -1, _("Print"))
		self.pauseButton = wx.Button(self.panel, -1, _("Pause"))
		self.cancelButton = wx.Button(self.panel, -1, _("Cancel print"))
		self.errorLogButton = wx.Button(self.panel, -1, _("Error log"))
		self.progress = wx.Gauge(self.panel, -1, range=1000)

		self.sizer.Add(self.powerWarningText, pos=(0, 0), span=(1, 5), flag=wx.EXPAND|wx.BOTTOM, border=5)
		self.sizer.Add(self.statsText, pos=(1, 0), span=(1, 5), flag=wx.LEFT, border=5)
		self.sizer.Add(self.connectButton, pos=(2, 0))
		#self.sizer.Add(self.loadButton, pos=(2,1))
		self.sizer.Add(self.printButton, pos=(2, 1))
		self.sizer.Add(self.pauseButton, pos=(2, 2))
		self.sizer.Add(self.cancelButton, pos=(2, 3))
		self.sizer.Add(self.errorLogButton, pos=(2, 4))
		self.sizer.Add(self.progress, pos=(3, 0), span=(1, 5), flag=wx.EXPAND)

		self.Bind(wx.EVT_CLOSE, self.OnClose)
		self.connectButton.Bind(wx.EVT_BUTTON, self.OnConnect)
		#self.loadButton.Bind(wx.EVT_BUTTON, self.OnLoad)
		self.printButton.Bind(wx.EVT_BUTTON, self.OnPrint)
		self.pauseButton.Bind(wx.EVT_BUTTON, self.OnPause)
		self.cancelButton.Bind(wx.EVT_BUTTON, self.OnCancel)
		self.errorLogButton.Bind(wx.EVT_BUTTON, self.OnErrorLog)

		self.Layout()
		self.Fit()
		self.Centre()

		self.progress.SetMinSize(self.progress.GetSize())
		self.statsText.SetLabel('\n\n\n\n\n\n')
		self._updateButtonStates()

		self._printerConnection.addCallback(self._doPrinterConnectionUpdate)

		if self._printerConnection.hasActiveConnection() and not self._printerConnection.isActiveConnectionOpen():
			self._printerConnection.openActiveConnection()
		preventComputerFromSleeping(True)

	def OnPowerWarningChange(self, e):
		type = self.powerManagement.get_providing_power_source_type()
		if type == power.POWER_TYPE_AC and self.powerWarningText.IsShown():
			self.powerWarningText.Hide()
			self.panel.Layout()
			self.Layout()
			self.Fit()
			self.Refresh()
		elif type != power.POWER_TYPE_AC and not self.powerWarningText.IsShown():
			self.powerWarningText.Show()
			self.panel.Layout()
			self.Layout()
			self.Fit()
			self.Refresh()

	def OnClose(self, e):
		if self._printerConnection.hasActiveConnection():
			if self._printerConnection.isPrinting():
				pass #TODO: Give warning that the close will kill the print.
			self._printerConnection.closeActiveConnection()
		self._printerConnection.removeCallback(self._doPrinterConnectionUpdate)
		#TODO: When multiple printer windows are open, closing one will enable sleeping again.
		preventComputerFromSleeping(False)
		self.Destroy()

	def OnConnect(self, e):
		self._printerConnection.openActiveConnection()

	def OnLoad(self, e):
		pass

	def OnPrint(self, e):
		self._printerConnection.startPrint()

	def OnCancel(self, e):
		self._printerConnection.cancelPrint()

	def OnPause(self, e):
		self._printerConnection.pause(not self._printerConnection.isPaused())

	def OnErrorLog(self, e):
		LogWindow(self._printerConnection.getErrorLog())

	def _doPrinterConnectionUpdate(self, connection, extraInfo = None):
		wx.CallAfter(self.__doPrinterConnectionUpdate, connection, extraInfo)
		#temp = [connection.getTemperature(0)]
		#self.temperatureGraph.addPoint(temp, [0], connection.getBedTemperature(), 0)

	def __doPrinterConnectionUpdate(self, connection, extraInfo):
		t = time.time()
		if self._lastUpdateTime + 0.5 > t and extraInfo is None:
			return
		self._lastUpdateTime = t

		if extraInfo is not None:
			self._addTermLog('< %s\n' % (extraInfo))

		self._updateButtonStates()
		if connection.isPrinting():
			self.progress.SetValue(connection.getPrintProgress() * 1000)
		else:
			self.progress.SetValue(0)
		info = connection.getStatusString()
		info += '\n'
		if self._printerConnection.getTemperature(0) is not None:
			info += 'Temperature: %d' % (self._printerConnection.getTemperature(0))
		if self._printerConnection.getBedTemperature() > 0:
			info += ' Bed: %d' % (self._printerConnection.getBedTemperature())
		info += '\n\n'
		self.statsText.SetLabel(info)

	def _updateButtonStates(self):
		self.connectButton.Show(self._printerConnection.hasActiveConnection())
		self.connectButton.Enable(not self._printerConnection.isActiveConnectionOpen() and not self._printerConnection.isActiveConnectionOpening())
		self.pauseButton.Show(self._printerConnection.hasPause())
		if not self._printerConnection.hasActiveConnection() or self._printerConnection.isActiveConnectionOpen():
			self.printButton.Enable(not self._printerConnection.isPrinting())
			self.pauseButton.Enable(self._printerConnection.isPrinting())
			self.cancelButton.Enable(self._printerConnection.isPrinting())
		else:
			self.printButton.Enable(False)
			self.pauseButton.Enable(False)
			self.cancelButton.Enable(False)
		self.errorLogButton.Show(self._printerConnection.isInErrorState())

class TemperatureGraph(wx.Panel):
	def __init__(self, parent):
		super(TemperatureGraph, self).__init__(parent)

		self.Bind(wx.EVT_ERASE_BACKGROUND, self.OnEraseBackground)
		self.Bind(wx.EVT_SIZE, self.OnSize)
		self.Bind(wx.EVT_PAINT, self.OnDraw)

		self._lastDraw = time.time() - 1.0
		self._points = []
		self._backBuffer = None
		self.addPoint([0]*16, [0]*16, 0, 0)

	def OnEraseBackground(self, e):
		pass

	def OnSize(self, e):
		if self._backBuffer is None or self.GetSize() != self._backBuffer.GetSize():
			self._backBuffer = wx.EmptyBitmap(*self.GetSizeTuple())
			self.UpdateDrawing(True)

	def OnDraw(self, e):
		dc = wx.BufferedPaintDC(self, self._backBuffer)

	def UpdateDrawing(self, force=False):
		now = time.time()
		if (not force and now - self._lastDraw < 1.0) or self._backBuffer is None:
			return
		self._lastDraw = now
		dc = wx.MemoryDC()
		dc.SelectObject(self._backBuffer)
		dc.Clear()
		dc.SetFont(wx.SystemSettings.GetFont(wx.SYS_SYSTEM_FONT))
		w, h = self.GetSizeTuple()
		bgLinePen = wx.Pen('#A0A0A0')
		tempPen = wx.Pen('#FF4040')
		tempSPPen = wx.Pen('#FFA0A0')
		tempPenBG = wx.Pen('#FFD0D0')
		bedTempPen = wx.Pen('#4040FF')
		bedTempSPPen = wx.Pen('#A0A0FF')
		bedTempPenBG = wx.Pen('#D0D0FF')

		#Draw the background up to the current temperatures.
		x0 = 0
		t0 = []
		bt0 = 0
		tSP0 = 0
		btSP0 = 0
		for temp, tempSP, bedTemp, bedTempSP, t in self._points:
			x1 = int(w - (now - t))
			for x in xrange(x0, x1 + 1):
				for n in xrange(0, min(len(t0), len(temp))):
					t = float(x - x0) / float(x1 - x0 + 1) * (temp[n] - t0[n]) + t0[n]
					dc.SetPen(tempPenBG)
					dc.DrawLine(x, h, x, h - (t * h / 300))
				bt = float(x - x0) / float(x1 - x0 + 1) * (bedTemp - bt0) + bt0
				dc.SetPen(bedTempPenBG)
				dc.DrawLine(x, h, x, h - (bt * h / 300))
			t0 = temp
			bt0 = bedTemp
			tSP0 = tempSP
			btSP0 = bedTempSP
			x0 = x1 + 1

		#Draw the grid
		for x in xrange(w, 0, -30):
			dc.SetPen(bgLinePen)
			dc.DrawLine(x, 0, x, h)
		tmpNr = 0
		for y in xrange(h - 1, 0, -h * 50 / 300):
			dc.SetPen(bgLinePen)
			dc.DrawLine(0, y, w, y)
			dc.DrawText(str(tmpNr), 0, y - dc.GetFont().GetPixelSize().GetHeight())
			tmpNr += 50
		dc.DrawLine(0, 0, w, 0)
		dc.DrawLine(0, 0, 0, h)

		#Draw the main lines
		x0 = 0
		t0 = []
		bt0 = 0
		tSP0 = []
		btSP0 = 0
		for temp, tempSP, bedTemp, bedTempSP, t in self._points:
			x1 = int(w - (now - t))
			for x in xrange(x0, x1 + 1):
				for n in xrange(0, min(len(t0), len(temp))):
					t = float(x - x0) / float(x1 - x0 + 1) * (temp[n] - t0[n]) + t0[n]
					tSP = float(x - x0) / float(x1 - x0 + 1) * (tempSP[n] - tSP0[n]) + tSP0[n]
					dc.SetPen(tempSPPen)
					dc.DrawPoint(x, h - (tSP * h / 300))
					dc.SetPen(tempPen)
					dc.DrawPoint(x, h - (t * h / 300))
				bt = float(x - x0) / float(x1 - x0 + 1) * (bedTemp - bt0) + bt0
				btSP = float(x - x0) / float(x1 - x0 + 1) * (bedTempSP - btSP0) + btSP0
				dc.SetPen(bedTempSPPen)
				dc.DrawPoint(x, h - (btSP * h / 300))
				dc.SetPen(bedTempPen)
				dc.DrawPoint(x, h - (bt * h / 300))
			t0 = temp
			bt0 = bedTemp
			tSP0 = tempSP
			btSP0 = bedTempSP
			x0 = x1 + 1

		del dc
		self.Refresh(eraseBackground=False)
		self.Update()

		if len(self._points) > 0 and (time.time() - self._points[0][4]) > w + 20:
			self._points.pop(0)

	def addPoint(self, temp, tempSP, bedTemp, bedTempSP):
		if len(self._points) > 0 and time.time() - self._points[-1][4] < 0.5:
			return
		for n in xrange(0, len(temp)):
			if temp[n] is None:
				temp[n] = 0
		for n in xrange(0, len(tempSP)):
			if tempSP[n] is None:
				tempSP[n] = 0
		if bedTemp is None:
			bedTemp = 0
		if bedTempSP is None:
			bedTempSP = 0
		self._points.append((temp[:], tempSP[:], bedTemp, bedTempSP, time.time()))
		wx.CallAfter(self.UpdateDrawing)


class LogWindow(wx.Frame):
	def __init__(self, logText):
		super(LogWindow, self).__init__(None, title="Error log")
		self.textBox = wx.TextCtrl(self, -1, logText, style=wx.TE_MULTILINE | wx.TE_DONTWRAP | wx.TE_READONLY)
		self.SetSize((500, 400))
		self.Show(True)

########NEW FILE########
__FILENAME__ = sceneView
__copyright__ = "Copyright (C) 2013 David Braam - Released under terms of the AGPLv3 License"

import wx
import numpy
import time
import os
import traceback
import threading
import math
import sys
import cStringIO as StringIO

import OpenGL
OpenGL.ERROR_CHECKING = False
from OpenGL.GLU import *
from OpenGL.GL import *

from Cura.gui import printWindow
from Cura.util import profile
from Cura.util import meshLoader
from Cura.util import objectScene
from Cura.util import resources
from Cura.util import sliceEngine
from Cura.util import pluginInfo
from Cura.util import removableStorage
from Cura.util import explorer
from Cura.util.printerConnection import printerConnectionManager
from Cura.gui.util import previewTools
from Cura.gui.util import openglHelpers
from Cura.gui.util import openglGui
from Cura.gui.util import engineResultView
from Cura.gui.tools import youmagineGui
from Cura.gui.tools import imageToMesh

class SceneView(openglGui.glGuiPanel):
	def __init__(self, parent):
		super(SceneView, self).__init__(parent)

		self._yaw = 30
		self._pitch = 60
		self._zoom = 300
		self._scene = objectScene.Scene()
		self._objectShader = None
		self._objectLoadShader = None
		self._focusObj = None
		self._selectedObj = None
		self._objColors = [None,None,None,None]
		self._mouseX = -1
		self._mouseY = -1
		self._mouseState = None
		self._viewTarget = numpy.array([0,0,0], numpy.float32)
		self._animView = None
		self._animZoom = None
		self._platformMesh = {}
		self._platformTexture = None
		self._isSimpleMode = True
		self._printerConnectionManager = printerConnectionManager.PrinterConnectionManager()

		self._viewport = None
		self._modelMatrix = None
		self._projMatrix = None
		self.tempMatrix = None

		self.openFileButton      = openglGui.glButton(self, 4, _("Load"), (0,0), self.showLoadModel)
		self.printButton         = openglGui.glButton(self, 6, _("Print"), (1,0), self.OnPrintButton)
		self.printButton.setDisabled(True)

		group = []
		self.rotateToolButton = openglGui.glRadioButton(self, 8, _("Rotate"), (0,-1), group, self.OnToolSelect)
		self.scaleToolButton  = openglGui.glRadioButton(self, 9, _("Scale"), (1,-1), group, self.OnToolSelect)
		self.mirrorToolButton  = openglGui.glRadioButton(self, 10, _("Mirror"), (2,-1), group, self.OnToolSelect)

		self.resetRotationButton = openglGui.glButton(self, 12, _("Reset"), (0,-2), self.OnRotateReset)
		self.layFlatButton       = openglGui.glButton(self, 16, _("Lay flat"), (0,-3), self.OnLayFlat)

		self.resetScaleButton    = openglGui.glButton(self, 13, _("Reset"), (1,-2), self.OnScaleReset)
		self.scaleMaxButton      = openglGui.glButton(self, 17, _("To max"), (1,-3), self.OnScaleMax)

		self.mirrorXButton       = openglGui.glButton(self, 14, _("Mirror X"), (2,-2), lambda button: self.OnMirror(0))
		self.mirrorYButton       = openglGui.glButton(self, 18, _("Mirror Y"), (2,-3), lambda button: self.OnMirror(1))
		self.mirrorZButton       = openglGui.glButton(self, 22, _("Mirror Z"), (2,-4), lambda button: self.OnMirror(2))

		self.rotateToolButton.setExpandArrow(True)
		self.scaleToolButton.setExpandArrow(True)
		self.mirrorToolButton.setExpandArrow(True)

		self.scaleForm = openglGui.glFrame(self, (2, -2))
		openglGui.glGuiLayoutGrid(self.scaleForm)
		openglGui.glLabel(self.scaleForm, _("Scale X"), (0,0))
		self.scaleXctrl = openglGui.glNumberCtrl(self.scaleForm, '1.0', (1,0), lambda value: self.OnScaleEntry(value, 0))
		openglGui.glLabel(self.scaleForm, _("Scale Y"), (0,1))
		self.scaleYctrl = openglGui.glNumberCtrl(self.scaleForm, '1.0', (1,1), lambda value: self.OnScaleEntry(value, 1))
		openglGui.glLabel(self.scaleForm, _("Scale Z"), (0,2))
		self.scaleZctrl = openglGui.glNumberCtrl(self.scaleForm, '1.0', (1,2), lambda value: self.OnScaleEntry(value, 2))
		openglGui.glLabel(self.scaleForm, _("Size X (mm)"), (0,4))
		self.scaleXmmctrl = openglGui.glNumberCtrl(self.scaleForm, '0.0', (1,4), lambda value: self.OnScaleEntryMM(value, 0))
		openglGui.glLabel(self.scaleForm, _("Size Y (mm)"), (0,5))
		self.scaleYmmctrl = openglGui.glNumberCtrl(self.scaleForm, '0.0', (1,5), lambda value: self.OnScaleEntryMM(value, 1))
		openglGui.glLabel(self.scaleForm, _("Size Z (mm)"), (0,6))
		self.scaleZmmctrl = openglGui.glNumberCtrl(self.scaleForm, '0.0', (1,6), lambda value: self.OnScaleEntryMM(value, 2))
		openglGui.glLabel(self.scaleForm, _("Uniform scale"), (0,8))
		self.scaleUniform = openglGui.glCheckbox(self.scaleForm, True, (1,8), None)

		self.viewSelection = openglGui.glComboButton(self, _("View mode"), [7,19,11,15,23], [_("Normal"), _("Overhang"), _("Transparent"), _("X-Ray"), _("Layers")], (-1,0), self.OnViewChange)

		self.youMagineButton = openglGui.glButton(self, 26, _("Share on YouMagine"), (2,0), lambda button: youmagineGui.youmagineManager(self.GetTopLevelParent(), self._scene))
		self.youMagineButton.setDisabled(True)

		self.notification = openglGui.glNotification(self, (0, 0))

		self._engine = sliceEngine.Engine(self._updateEngineProgress)
		self._engineResultView = engineResultView.engineResultView(self)
		self._sceneUpdateTimer = wx.Timer(self)
		self.Bind(wx.EVT_TIMER, self._onRunEngine, self._sceneUpdateTimer)
		self.Bind(wx.EVT_MOUSEWHEEL, self.OnMouseWheel)
		self.Bind(wx.EVT_LEAVE_WINDOW, self.OnMouseLeave)

		self.OnViewChange()
		self.OnToolSelect(0)
		self.updateToolButtons()
		self.updateProfileToControls()

	def loadGCodeFile(self, filename):
		self.OnDeleteAll(None)
		#Cheat the engine results to load a GCode file into it.
		self._engine._result = sliceEngine.EngineResult()
		with open(filename, "r") as f:
			self._engine._result.setGCode(f.read())
		self._engine._result.setFinished(True)
		self._engineResultView.setResult(self._engine._result)
		self.printButton.setBottomText('')
		self.viewSelection.setValue(4)
		self.printButton.setDisabled(False)
		self.youMagineButton.setDisabled(True)
		self.OnViewChange()

	def loadSceneFiles(self, filenames):
		self.youMagineButton.setDisabled(False)
		#if self.viewSelection.getValue() == 4:
		#	self.viewSelection.setValue(0)
		#	self.OnViewChange()
		self.loadScene(filenames)

	def loadFiles(self, filenames):
		mainWindow = self.GetParent().GetParent().GetParent()
		# only one GCODE file can be active
		# so if single gcode file, process this
		# otherwise ignore all gcode files
		gcodeFilename = None
		if len(filenames) == 1:
			filename = filenames[0]
			ext = os.path.splitext(filename)[1].lower()
			if ext == '.g' or ext == '.gcode':
				gcodeFilename = filename
				mainWindow.addToModelMRU(filename)
		if gcodeFilename is not None:
			self.loadGCodeFile(gcodeFilename)
		else:
			# process directories and special file types
			# and keep scene files for later processing
			scene_filenames = []
			ignored_types = dict()
			# use file list as queue
			# pop first entry for processing and append new files at end
			while filenames:
				filename = filenames.pop(0)
				if os.path.isdir(filename):
					# directory: queue all included files and directories
					filenames.extend(os.path.join(filename, f) for f in os.listdir(filename))
				else:
					ext = os.path.splitext(filename)[1].lower()
					if ext == '.ini':
						profile.loadProfile(filename)
						mainWindow.addToProfileMRU(filename)
					elif ext in meshLoader.loadSupportedExtensions() or ext in imageToMesh.supportedExtensions():
						scene_filenames.append(filename)
						mainWindow.addToModelMRU(filename)
					else:
						ignored_types[ext] = 1
			if ignored_types:
				ignored_types = ignored_types.keys()
				ignored_types.sort()
				self.notification.message("ignored: " + " ".join("*" + type for type in ignored_types))
			mainWindow.updateProfileToAllControls()
			# now process all the scene files
			if scene_filenames:
				self.loadSceneFiles(scene_filenames)
				self._selectObject(None)
				self.sceneUpdated()
				newZoom = numpy.max(self._machineSize)
				self._animView = openglGui.animation(self, self._viewTarget.copy(), numpy.array([0,0,0], numpy.float32), 0.5)
				self._animZoom = openglGui.animation(self, self._zoom, newZoom, 0.5)

	def reloadScene(self, e):
		# Copy the list before DeleteAll clears it
		fileList = []
		for obj in self._scene.objects():
			fileList.append(obj.getOriginFilename())
		self.OnDeleteAll(None)
		self.loadScene(fileList)

	def showLoadModel(self, button = 1):
		if button == 1:
			dlg=wx.FileDialog(self, _("Open 3D model"), os.path.split(profile.getPreference('lastFile'))[0], style=wx.FD_OPEN|wx.FD_FILE_MUST_EXIST|wx.FD_MULTIPLE)

			wildcardList = ';'.join(map(lambda s: '*' + s, meshLoader.loadSupportedExtensions() + imageToMesh.supportedExtensions() + ['.g', '.gcode']))
			wildcardFilter = "All (%s)|%s;%s" % (wildcardList, wildcardList, wildcardList.upper())
			wildcardList = ';'.join(map(lambda s: '*' + s, meshLoader.loadSupportedExtensions()))
			wildcardFilter += "|Mesh files (%s)|%s;%s" % (wildcardList, wildcardList, wildcardList.upper())
			wildcardList = ';'.join(map(lambda s: '*' + s, imageToMesh.supportedExtensions()))
			wildcardFilter += "|Image files (%s)|%s;%s" % (wildcardList, wildcardList, wildcardList.upper())
			wildcardList = ';'.join(map(lambda s: '*' + s, ['.g', '.gcode']))
			wildcardFilter += "|GCode files (%s)|%s;%s" % (wildcardList, wildcardList, wildcardList.upper())

			dlg.SetWildcard(wildcardFilter)
			if dlg.ShowModal() != wx.ID_OK:
				dlg.Destroy()
				return
			filenames = dlg.GetPaths()
			dlg.Destroy()
			if len(filenames) < 1:
				return False
			profile.putPreference('lastFile', filenames[0])
			self.loadFiles(filenames)

	def showSaveModel(self):
		if len(self._scene.objects()) < 1:
			return
		dlg=wx.FileDialog(self, _("Save 3D model"), os.path.split(profile.getPreference('lastFile'))[0], style=wx.FD_SAVE|wx.FD_OVERWRITE_PROMPT)
		fileExtensions = meshLoader.saveSupportedExtensions()
		wildcardList = ';'.join(map(lambda s: '*' + s, fileExtensions))
		wildcardFilter = "Mesh files (%s)|%s;%s" % (wildcardList, wildcardList, wildcardList.upper())
		dlg.SetWildcard(wildcardFilter)
		if dlg.ShowModal() != wx.ID_OK:
			dlg.Destroy()
			return
		filename = dlg.GetPath()
		dlg.Destroy()
		meshLoader.saveMeshes(filename, self._scene.objects())

	def OnPrintButton(self, button):
		if button == 1:
			connectionGroup = self._printerConnectionManager.getAvailableGroup()
			if len(removableStorage.getPossibleSDcardDrives()) > 0 and (connectionGroup is None or connectionGroup.getPriority() < 0):
				drives = removableStorage.getPossibleSDcardDrives()
				if len(drives) > 1:
					dlg = wx.SingleChoiceDialog(self, "Select SD drive", "Multiple removable drives have been found,\nplease select your SD card drive", map(lambda n: n[0], drives))
					if dlg.ShowModal() != wx.ID_OK:
						dlg.Destroy()
						return
					drive = drives[dlg.GetSelection()]
					dlg.Destroy()
				else:
					drive = drives[0]
				filename = self._scene._objectList[0].getName() + profile.getGCodeExtension()
				threading.Thread(target=self._saveGCode,args=(drive[1] + filename, drive[1])).start()
			elif connectionGroup is not None:
				connections = connectionGroup.getAvailableConnections()
				if len(connections) < 2:
					connection = connections[0]
				else:
					dlg = wx.SingleChoiceDialog(self, "Select the %s connection to use" % (connectionGroup.getName()), "Multiple %s connections found" % (connectionGroup.getName()), map(lambda n: n.getName(), connections))
					if dlg.ShowModal() != wx.ID_OK:
						dlg.Destroy()
						return
					connection = connections[dlg.GetSelection()]
					dlg.Destroy()
				self._openPrintWindowForConnection(connection)
			else:
				self.showSaveGCode()
		if button == 3:
			menu = wx.Menu()
			connections = self._printerConnectionManager.getAvailableConnections()
			menu.connectionMap = {}
			for connection in connections:
				i = menu.Append(-1, _("Print with %s") % (connection.getName()))
				menu.connectionMap[i.GetId()] = connection
				self.Bind(wx.EVT_MENU, lambda e: self._openPrintWindowForConnection(e.GetEventObject().connectionMap[e.GetId()]), i)
			self.Bind(wx.EVT_MENU, lambda e: self.showSaveGCode(), menu.Append(-1, _("Save GCode...")))
			self.Bind(wx.EVT_MENU, lambda e: self._showEngineLog(), menu.Append(-1, _("Slice engine log...")))
			self.PopupMenu(menu)
			menu.Destroy()

	def _openPrintWindowForConnection(self, connection):
		if connection.window is None or not connection.window:
			connection.window = None
			windowType = profile.getPreference('printing_window')
			for p in pluginInfo.getPluginList('printwindow'):
				if p.getName() == windowType:
					connection.window = printWindow.printWindowPlugin(self, connection, p.getFullFilename())
					break
			if connection.window is None:
				connection.window = printWindow.printWindowBasic(self, connection)
		connection.window.Show()
		connection.window.Raise()
		if not connection.loadGCodeData(StringIO.StringIO(self._engine.getResult().getGCode())):
			if connection.isPrinting():
				self.notification.message("Cannot start print, because other print still running.")
			else:
				self.notification.message("Failed to start print...")

	def showSaveGCode(self):
		if len(self._scene._objectList) < 1:
			return
		dlg=wx.FileDialog(self, _("Save toolpath"), os.path.dirname(profile.getPreference('lastFile')), style=wx.FD_SAVE|wx.FD_OVERWRITE_PROMPT)
		filename = self._scene._objectList[0].getName() + profile.getGCodeExtension()
		dlg.SetFilename(filename)
		dlg.SetWildcard('Toolpath (*%s)|*%s;*%s' % (profile.getGCodeExtension(), profile.getGCodeExtension(), profile.getGCodeExtension()[0:2]))
		if dlg.ShowModal() != wx.ID_OK:
			dlg.Destroy()
			return
		filename = dlg.GetPath()
		dlg.Destroy()

		threading.Thread(target=self._saveGCode,args=(filename,)).start()

	def _saveGCode(self, targetFilename, ejectDrive = False):
		data = self._engine.getResult().getGCode()
		try:
			size = float(len(data))
			fsrc = StringIO.StringIO(data)
			with open(targetFilename, 'wb') as fdst:
				while 1:
					buf = fsrc.read(16*1024)
					if not buf:
						break
					fdst.write(buf)
					self.printButton.setProgressBar(float(fsrc.tell()) / size)
					self._queueRefresh()
		except:
			import sys, traceback
			traceback.print_exc()
			self.notification.message("Failed to save")
		else:
			if ejectDrive:
				self.notification.message("Saved as %s" % (targetFilename), lambda : self._doEjectSD(ejectDrive), 31, 'Eject')
			elif explorer.hasExplorer():
				self.notification.message("Saved as %s" % (targetFilename), lambda : explorer.openExplorer(targetFilename), 4, 'Open folder')
			else:
				self.notification.message("Saved as %s" % (targetFilename))
		self.printButton.setProgressBar(None)
		self._engine.getResult().submitInfoOnline()

	def _doEjectSD(self, drive):
		if removableStorage.ejectDrive(drive):
			self.notification.message('You can now eject the card.')
		else:
			self.notification.message('Safe remove failed...')

	def _showEngineLog(self):
		dlg = wx.TextEntryDialog(self, _("The slicing engine reported the following"), _("Engine log..."), '\n'.join(self._engine.getResult().getLog()), wx.TE_MULTILINE | wx.OK | wx.CENTRE)
		dlg.ShowModal()
		dlg.Destroy()

	def OnToolSelect(self, button):
		if self.rotateToolButton.getSelected():
			self.tool = previewTools.toolRotate(self)
		elif self.scaleToolButton.getSelected():
			self.tool = previewTools.toolScale(self)
		elif self.mirrorToolButton.getSelected():
			self.tool = previewTools.toolNone(self)
		else:
			self.tool = previewTools.toolNone(self)
		self.resetRotationButton.setHidden(not self.rotateToolButton.getSelected())
		self.layFlatButton.setHidden(not self.rotateToolButton.getSelected())
		self.resetScaleButton.setHidden(not self.scaleToolButton.getSelected())
		self.scaleMaxButton.setHidden(not self.scaleToolButton.getSelected())
		self.scaleForm.setHidden(not self.scaleToolButton.getSelected())
		self.mirrorXButton.setHidden(not self.mirrorToolButton.getSelected())
		self.mirrorYButton.setHidden(not self.mirrorToolButton.getSelected())
		self.mirrorZButton.setHidden(not self.mirrorToolButton.getSelected())

	def updateToolButtons(self):
		if self._selectedObj is None:
			hidden = True
		else:
			hidden = False
		self.rotateToolButton.setHidden(hidden)
		self.scaleToolButton.setHidden(hidden)
		self.mirrorToolButton.setHidden(hidden)
		if hidden:
			self.rotateToolButton.setSelected(False)
			self.scaleToolButton.setSelected(False)
			self.mirrorToolButton.setSelected(False)
			self.OnToolSelect(0)

	def OnViewChange(self):
		if self.viewSelection.getValue() == 4:
			self.viewMode = 'gcode'
			self.tool = previewTools.toolNone(self)
		elif self.viewSelection.getValue() == 1:
			self.viewMode = 'overhang'
		elif self.viewSelection.getValue() == 2:
			self.viewMode = 'transparent'
		elif self.viewSelection.getValue() == 3:
			self.viewMode = 'xray'
		else:
			self.viewMode = 'normal'
		self._engineResultView.setEnabled(self.viewMode == 'gcode')
		self.QueueRefresh()

	def OnRotateReset(self, button):
		if self._selectedObj is None:
			return
		self._selectedObj.resetRotation()
		self._scene.pushFree(self._selectedObj)
		self._selectObject(self._selectedObj)
		self.sceneUpdated()

	def OnLayFlat(self, button):
		if self._selectedObj is None:
			return
		self._selectedObj.layFlat()
		self._scene.pushFree(self._selectedObj)
		self._selectObject(self._selectedObj)
		self.sceneUpdated()

	def OnScaleReset(self, button):
		if self._selectedObj is None:
			return
		self._selectedObj.resetScale()
		self._selectObject(self._selectedObj)
		self.updateProfileToControls()
		self.sceneUpdated()

	def OnScaleMax(self, button):
		if self._selectedObj is None:
			return
		machine = profile.getMachineSetting('machine_type')
		self._selectedObj.setPosition(numpy.array([0.0, 0.0]))
		self._scene.pushFree(self._selectedObj)
		#self.sceneUpdated()
		if machine == "ultimaker2":
			#This is bad and Jaime should feel bad!
			self._selectedObj.setPosition(numpy.array([0.0,-10.0]))
			self._selectedObj.scaleUpTo(self._machineSize - numpy.array(profile.calculateObjectSizeOffsets() + [0.0], numpy.float32) * 2 - numpy.array([3,3,3], numpy.float32))
			self._selectedObj.setPosition(numpy.array([0.0,0.0]))
			self._scene.pushFree(self._selectedObj)
		else:
			self._selectedObj.setPosition(numpy.array([0.0, 0.0]))
			self._scene.pushFree(self._selectedObj)
			self._selectedObj.scaleUpTo(self._machineSize - numpy.array(profile.calculateObjectSizeOffsets() + [0.0], numpy.float32) * 2 - numpy.array([3,3,3], numpy.float32))
		self._scene.pushFree(self._selectedObj)
		self._selectObject(self._selectedObj)
		self.updateProfileToControls()
		self.sceneUpdated()

	def OnMirror(self, axis):
		if self._selectedObj is None:
			return
		self._selectedObj.mirror(axis)
		self.sceneUpdated()

	def OnScaleEntry(self, value, axis):
		if self._selectedObj is None:
			return
		try:
			value = float(value)
		except:
			return
		self._selectedObj.setScale(value, axis, self.scaleUniform.getValue())
		self.updateProfileToControls()
		self._scene.pushFree(self._selectedObj)
		self._selectObject(self._selectedObj)
		self.sceneUpdated()

	def OnScaleEntryMM(self, value, axis):
		if self._selectedObj is None:
			return
		try:
			value = float(value)
		except:
			return
		self._selectedObj.setSize(value, axis, self.scaleUniform.getValue())
		self.updateProfileToControls()
		self._scene.pushFree(self._selectedObj)
		self._selectObject(self._selectedObj)
		self.sceneUpdated()

	def OnDeleteAll(self, e):
		while len(self._scene.objects()) > 0:
			self._deleteObject(self._scene.objects()[0])
		self._animView = openglGui.animation(self, self._viewTarget.copy(), numpy.array([0,0,0], numpy.float32), 0.5)
		self._engineResultView.setResult(None)

	def OnMultiply(self, e):
		if self._focusObj is None:
			return
		obj = self._focusObj
		dlg = wx.NumberEntryDialog(self, _("How many copies do you want?"), _("Number of copies"), _("Multiply"), 1, 1, 100)
		if dlg.ShowModal() != wx.ID_OK:
			dlg.Destroy()
			return
		cnt = dlg.GetValue()
		dlg.Destroy()
		n = 0
		while True:
			n += 1
			newObj = obj.copy()
			self._scene.add(newObj)
			self._scene.centerAll()
			if not self._scene.checkPlatform(newObj):
				break
			if n > cnt:
				break
		if n <= cnt:
			self.notification.message("Could not create more than %d items" % (n - 1))
		self._scene.remove(newObj)
		self._scene.centerAll()
		self.sceneUpdated()

	def OnSplitObject(self, e):
		if self._focusObj is None:
			return
		self._scene.remove(self._focusObj)
		for obj in self._focusObj.split(self._splitCallback):
			if numpy.max(obj.getSize()) > 2.0:
				self._scene.add(obj)
		self._scene.centerAll()
		self._selectObject(None)
		self.sceneUpdated()

	def OnCenter(self, e):
		if self._focusObj is None:
			return
		self._focusObj.setPosition(numpy.array([0.0, 0.0]))
		self._scene.pushFree(self._selectedObj)
		newViewPos = numpy.array([self._focusObj.getPosition()[0], self._focusObj.getPosition()[1], self._focusObj.getSize()[2] / 2])
		self._animView = openglGui.animation(self, self._viewTarget.copy(), newViewPos, 0.5)
		self.sceneUpdated()

	def _splitCallback(self, progress):
		print progress

	def OnMergeObjects(self, e):
		if self._selectedObj is None or self._focusObj is None or self._selectedObj == self._focusObj:
			if len(self._scene.objects()) == 2:
				self._scene.merge(self._scene.objects()[0], self._scene.objects()[1])
				self.sceneUpdated()
			return
		self._scene.merge(self._selectedObj, self._focusObj)
		self.sceneUpdated()

	def sceneUpdated(self):
		self._sceneUpdateTimer.Start(500, True)
		self._engine.abortEngine()
		self._scene.updateSizeOffsets()
		self.QueueRefresh()

	def _onRunEngine(self, e):
		if self._isSimpleMode:
			self.GetTopLevelParent().simpleSettingsPanel.setupSlice()
		self._engine.runEngine(self._scene)
		if self._isSimpleMode:
			profile.resetTempOverride()

	def _updateEngineProgress(self, progressValue):
		result = self._engine.getResult()
		finished = result is not None and result.isFinished()
		if not finished:
			if self.printButton.getProgressBar() is not None and progressValue >= 0.0 and abs(self.printButton.getProgressBar() - progressValue) < 0.01:
				return
		self.printButton.setDisabled(not finished)
		if progressValue >= 0.0:
			self.printButton.setProgressBar(progressValue)
		else:
			self.printButton.setProgressBar(None)
		self._engineResultView.setResult(result)
		if finished:
			self.printButton.setProgressBar(None)
			text = '%s' % (result.getPrintTime())
			for e in xrange(0, int(profile.getMachineSetting('extruder_amount'))):
				amount = result.getFilamentAmount(e)
				if amount is None:
					continue
				text += '\n%s' % (amount)
				cost = result.getFilamentCost(e)
				if cost is not None:
					text += '\n%s' % (cost)
			self.printButton.setBottomText(text)
		else:
			self.printButton.setBottomText('')
		self.QueueRefresh()

	def loadScene(self, fileList):
		for filename in fileList:
			try:
				ext = os.path.splitext(filename)[1].lower()
				if ext in imageToMesh.supportedExtensions():
					imageToMesh.convertImageDialog(self, filename).Show()
					objList = []
				else:
					objList = meshLoader.loadMeshes(filename)
			except:
				traceback.print_exc()
			else:
				for obj in objList:
					if self._objectLoadShader is not None:
						obj._loadAnim = openglGui.animation(self, 1, 0, 1.5)
					else:
						obj._loadAnim = None
					self._scene.add(obj)
					if not self._scene.checkPlatform(obj):
						self._scene.centerAll()
					self._selectObject(obj)
					if obj.getScale()[0] < 1.0:
						self.notification.message("Warning: Object scaled down.")
		self.sceneUpdated()

	def _deleteObject(self, obj):
		if obj == self._selectedObj:
			self._selectObject(None)
		if obj == self._focusObj:
			self._focusObj = None
		self._scene.remove(obj)
		for m in obj._meshList:
			if m.vbo is not None and m.vbo.decRef():
				self.glReleaseList.append(m.vbo)
		if len(self._scene.objects()) == 0:
			self._engineResultView.setResult(None)
		import gc
		gc.collect()
		self.sceneUpdated()

	def _selectObject(self, obj, zoom = True):
		if obj != self._selectedObj:
			self._selectedObj = obj
			self.updateModelSettingsToControls()
			self.updateToolButtons()
		if zoom and obj is not None:
			newViewPos = numpy.array([obj.getPosition()[0], obj.getPosition()[1], obj.getSize()[2] / 2])
			self._animView = openglGui.animation(self, self._viewTarget.copy(), newViewPos, 0.5)
			newZoom = obj.getBoundaryCircle() * 6
			if newZoom > numpy.max(self._machineSize) * 3:
				newZoom = numpy.max(self._machineSize) * 3
			self._animZoom = openglGui.animation(self, self._zoom, newZoom, 0.5)

	def updateProfileToControls(self):
		oldSimpleMode = self._isSimpleMode
		self._isSimpleMode = profile.getPreference('startMode') == 'Simple'
		if self._isSimpleMode != oldSimpleMode:
			self._scene.arrangeAll()
			self.sceneUpdated()
		self._scene.updateSizeOffsets(True)
		self._machineSize = numpy.array([profile.getMachineSettingFloat('machine_width'), profile.getMachineSettingFloat('machine_depth'), profile.getMachineSettingFloat('machine_height')])
		self._objColors[0] = profile.getPreferenceColour('model_colour')
		self._objColors[1] = profile.getPreferenceColour('model_colour2')
		self._objColors[2] = profile.getPreferenceColour('model_colour3')
		self._objColors[3] = profile.getPreferenceColour('model_colour4')
		self._scene.updateMachineDimensions()
		self.updateModelSettingsToControls()

	def updateModelSettingsToControls(self):
		if self._selectedObj is not None:
			scale = self._selectedObj.getScale()
			size = self._selectedObj.getSize()
			self.scaleXctrl.setValue(round(scale[0], 2))
			self.scaleYctrl.setValue(round(scale[1], 2))
			self.scaleZctrl.setValue(round(scale[2], 2))
			self.scaleXmmctrl.setValue(round(size[0], 2))
			self.scaleYmmctrl.setValue(round(size[1], 2))
			self.scaleZmmctrl.setValue(round(size[2], 2))

	def OnKeyChar(self, keyCode):
		if self._engineResultView.OnKeyChar(keyCode):
			return
		if keyCode == wx.WXK_DELETE or keyCode == wx.WXK_NUMPAD_DELETE or (keyCode == wx.WXK_BACK and sys.platform.startswith("darwin")):
			if self._selectedObj is not None:
				self._deleteObject(self._selectedObj)
				self.QueueRefresh()
		if keyCode == wx.WXK_UP:
			if wx.GetKeyState(wx.WXK_SHIFT):
				self._zoom /= 1.2
				if self._zoom < 1:
					self._zoom = 1
			else:
				self._pitch -= 15
			self.QueueRefresh()
		elif keyCode == wx.WXK_DOWN:
			if wx.GetKeyState(wx.WXK_SHIFT):
				self._zoom *= 1.2
				if self._zoom > numpy.max(self._machineSize) * 3:
					self._zoom = numpy.max(self._machineSize) * 3
			else:
				self._pitch += 15
			self.QueueRefresh()
		elif keyCode == wx.WXK_LEFT:
			self._yaw -= 15
			self.QueueRefresh()
		elif keyCode == wx.WXK_RIGHT:
			self._yaw += 15
			self.QueueRefresh()
		elif keyCode == wx.WXK_NUMPAD_ADD or keyCode == wx.WXK_ADD or keyCode == ord('+') or keyCode == ord('='):
			self._zoom /= 1.2
			if self._zoom < 1:
				self._zoom = 1
			self.QueueRefresh()
		elif keyCode == wx.WXK_NUMPAD_SUBTRACT or keyCode == wx.WXK_SUBTRACT or keyCode == ord('-'):
			self._zoom *= 1.2
			if self._zoom > numpy.max(self._machineSize) * 3:
				self._zoom = numpy.max(self._machineSize) * 3
			self.QueueRefresh()
		elif keyCode == wx.WXK_HOME:
			self._yaw = 30
			self._pitch = 60
			self.QueueRefresh()
		elif keyCode == wx.WXK_PAGEUP:
			self._yaw = 0
			self._pitch = 0
			self.QueueRefresh()
		elif keyCode == wx.WXK_PAGEDOWN:
			self._yaw = 0
			self._pitch = 90
			self.QueueRefresh()
		elif keyCode == wx.WXK_END:
			self._yaw = 90
			self._pitch = 90
			self.QueueRefresh()

		if keyCode == wx.WXK_F3 and wx.GetKeyState(wx.WXK_SHIFT):
			shaderEditor(self, self.ShaderUpdate, self._objectLoadShader.getVertexShader(), self._objectLoadShader.getFragmentShader())
		if keyCode == wx.WXK_F4 and wx.GetKeyState(wx.WXK_SHIFT):
			from collections import defaultdict
			from gc import get_objects
			self._beforeLeakTest = defaultdict(int)
			for i in get_objects():
				self._beforeLeakTest[type(i)] += 1
		if keyCode == wx.WXK_F5 and wx.GetKeyState(wx.WXK_SHIFT):
			from collections import defaultdict
			from gc import get_objects
			self._afterLeakTest = defaultdict(int)
			for i in get_objects():
				self._afterLeakTest[type(i)] += 1
			for k in self._afterLeakTest:
				if self._afterLeakTest[k]-self._beforeLeakTest[k]:
					print k, self._afterLeakTest[k], self._beforeLeakTest[k], self._afterLeakTest[k] - self._beforeLeakTest[k]

	def ShaderUpdate(self, v, f):
		s = openglHelpers.GLShader(v, f)
		if s.isValid():
			self._objectLoadShader.release()
			self._objectLoadShader = s
			for obj in self._scene.objects():
				obj._loadAnim = openglGui.animation(self, 1, 0, 1.5)
			self.QueueRefresh()

	def OnMouseDown(self,e):
		self._mouseX = e.GetX()
		self._mouseY = e.GetY()
		self._mouseClick3DPos = self._mouse3Dpos
		self._mouseClickFocus = self._focusObj
		if e.ButtonDClick():
			self._mouseState = 'doubleClick'
		else:
			if self._mouseState == 'dragObject' and self._selectedObj is not None:
				self._scene.pushFree(self._selectedObj)
				self.sceneUpdated()
			self._mouseState = 'dragOrClick'
		p0, p1 = self.getMouseRay(self._mouseX, self._mouseY)
		p0 -= self.getObjectCenterPos() - self._viewTarget
		p1 -= self.getObjectCenterPos() - self._viewTarget
		if self.tool.OnDragStart(p0, p1):
			self._mouseState = 'tool'
		if self._mouseState == 'dragOrClick':
			if e.GetButton() == 1:
				if self._focusObj is not None:
					self._selectObject(self._focusObj, False)
					self.QueueRefresh()

	def OnMouseUp(self, e):
		if e.LeftIsDown() or e.MiddleIsDown() or e.RightIsDown():
			return
		if self._mouseState == 'dragOrClick':
			if e.GetButton() == 1:
				self._selectObject(self._focusObj)
			if e.GetButton() == 3:
					menu = wx.Menu()
					if self._focusObj is not None:

						self.Bind(wx.EVT_MENU, self.OnCenter, menu.Append(-1, _("Center on platform")))
						self.Bind(wx.EVT_MENU, lambda e: self._deleteObject(self._focusObj), menu.Append(-1, _("Delete object")))
						self.Bind(wx.EVT_MENU, self.OnMultiply, menu.Append(-1, _("Multiply object")))
						self.Bind(wx.EVT_MENU, self.OnSplitObject, menu.Append(-1, _("Split object into parts")))
					if ((self._selectedObj != self._focusObj and self._focusObj is not None and self._selectedObj is not None) or len(self._scene.objects()) == 2) and int(profile.getMachineSetting('extruder_amount')) > 1:
						self.Bind(wx.EVT_MENU, self.OnMergeObjects, menu.Append(-1, _("Dual extrusion merge")))
					if len(self._scene.objects()) > 0:
						self.Bind(wx.EVT_MENU, self.OnDeleteAll, menu.Append(-1, _("Delete all objects")))
						self.Bind(wx.EVT_MENU, self.reloadScene, menu.Append(-1, _("Reload all objects")))
					if menu.MenuItemCount > 0:
						self.PopupMenu(menu)
					menu.Destroy()
		elif self._mouseState == 'dragObject' and self._selectedObj is not None:
			self._scene.pushFree(self._selectedObj)
			self.sceneUpdated()
		elif self._mouseState == 'tool':
			if self.tempMatrix is not None and self._selectedObj is not None:
				self._selectedObj.applyMatrix(self.tempMatrix)
				self._scene.pushFree(self._selectedObj)
				self._selectObject(self._selectedObj)
			self.tempMatrix = None
			self.tool.OnDragEnd()
			self.sceneUpdated()
		self._mouseState = None

	def OnMouseMotion(self,e):
		p0, p1 = self.getMouseRay(e.GetX(), e.GetY())
		p0 -= self.getObjectCenterPos() - self._viewTarget
		p1 -= self.getObjectCenterPos() - self._viewTarget

		if e.Dragging() and self._mouseState is not None:
			if self._mouseState == 'tool':
				self.tool.OnDrag(p0, p1)
			elif not e.LeftIsDown() and e.RightIsDown():
				self._mouseState = 'drag'
				if wx.GetKeyState(wx.WXK_SHIFT):
					a = math.cos(math.radians(self._yaw)) / 3.0
					b = math.sin(math.radians(self._yaw)) / 3.0
					self._viewTarget[0] += float(e.GetX() - self._mouseX) * -a
					self._viewTarget[1] += float(e.GetX() - self._mouseX) * b
					self._viewTarget[0] += float(e.GetY() - self._mouseY) * b
					self._viewTarget[1] += float(e.GetY() - self._mouseY) * a
				else:
					self._yaw += e.GetX() - self._mouseX
					self._pitch -= e.GetY() - self._mouseY
				if self._pitch > 170:
					self._pitch = 170
				if self._pitch < 10:
					self._pitch = 10
			elif (e.LeftIsDown() and e.RightIsDown()) or e.MiddleIsDown():
				self._mouseState = 'drag'
				self._zoom += e.GetY() - self._mouseY
				if self._zoom < 1:
					self._zoom = 1
				if self._zoom > numpy.max(self._machineSize) * 3:
					self._zoom = numpy.max(self._machineSize) * 3
			elif e.LeftIsDown() and self._selectedObj is not None and self._selectedObj == self._mouseClickFocus:
				self._mouseState = 'dragObject'
				z = max(0, self._mouseClick3DPos[2])
				p0, p1 = self.getMouseRay(self._mouseX, self._mouseY)
				p2, p3 = self.getMouseRay(e.GetX(), e.GetY())
				p0[2] -= z
				p1[2] -= z
				p2[2] -= z
				p3[2] -= z
				cursorZ0 = p0 - (p1 - p0) * (p0[2] / (p1[2] - p0[2]))
				cursorZ1 = p2 - (p3 - p2) * (p2[2] / (p3[2] - p2[2]))
				diff = cursorZ1 - cursorZ0
				self._selectedObj.setPosition(self._selectedObj.getPosition() + diff[0:2])
		if not e.Dragging() or self._mouseState != 'tool':
			self.tool.OnMouseMove(p0, p1)

		self._mouseX = e.GetX()
		self._mouseY = e.GetY()

	def OnMouseWheel(self, e):
		delta = float(e.GetWheelRotation()) / float(e.GetWheelDelta())
		delta = max(min(delta,4),-4)
		self._zoom *= 1.0 - delta / 10.0
		if self._zoom < 1.0:
			self._zoom = 1.0
		if self._zoom > numpy.max(self._machineSize) * 3:
			self._zoom = numpy.max(self._machineSize) * 3
		self.Refresh()

	def OnMouseLeave(self, e):
		#self._mouseX = -1
		pass

	def getMouseRay(self, x, y):
		if self._viewport is None:
			return numpy.array([0,0,0],numpy.float32), numpy.array([0,0,1],numpy.float32)
		p0 = openglHelpers.unproject(x, self._viewport[1] + self._viewport[3] - y, 0, self._modelMatrix, self._projMatrix, self._viewport)
		p1 = openglHelpers.unproject(x, self._viewport[1] + self._viewport[3] - y, 1, self._modelMatrix, self._projMatrix, self._viewport)
		p0 -= self._viewTarget
		p1 -= self._viewTarget
		return p0, p1

	def _init3DView(self):
		# set viewing projection
		size = self.GetSize()
		glViewport(0, 0, size.GetWidth(), size.GetHeight())
		glLoadIdentity()

		glLightfv(GL_LIGHT0, GL_POSITION, [0.2, 0.2, 1.0, 0.0])

		glDisable(GL_RESCALE_NORMAL)
		glDisable(GL_LIGHTING)
		glDisable(GL_LIGHT0)
		glEnable(GL_DEPTH_TEST)
		glDisable(GL_CULL_FACE)
		glDisable(GL_BLEND)
		glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

		glClearColor(0.8, 0.8, 0.8, 1.0)
		glClearStencil(0)
		glClearDepth(1.0)

		glMatrixMode(GL_PROJECTION)
		glLoadIdentity()
		aspect = float(size.GetWidth()) / float(size.GetHeight())
		gluPerspective(45.0, aspect, 1.0, numpy.max(self._machineSize) * 4)

		glMatrixMode(GL_MODELVIEW)
		glLoadIdentity()
		glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT | GL_STENCIL_BUFFER_BIT)

	def OnPaint(self,e):
		connectionGroup = self._printerConnectionManager.getAvailableGroup()
		if len(removableStorage.getPossibleSDcardDrives()) > 0 and (connectionGroup is None or connectionGroup.getPriority() < 0):
			self.printButton._imageID = 2
			self.printButton._tooltip = _("Toolpath to SD")
		elif connectionGroup is not None:
			self.printButton._imageID = connectionGroup.getIconID()
			self.printButton._tooltip = _("Print with %s") % (connectionGroup.getName())
		else:
			self.printButton._imageID = 3
			self.printButton._tooltip = _("Save toolpath")

		if self._animView is not None:
			self._viewTarget = self._animView.getPosition()
			if self._animView.isDone():
				self._animView = None
		if self._animZoom is not None:
			self._zoom = self._animZoom.getPosition()
			if self._animZoom.isDone():
				self._animZoom = None
		if self._objectShader is None: #TODO: add loading shaders from file(s)
			if openglHelpers.hasShaderSupport():
				self._objectShader = openglHelpers.GLShader("""
					varying float light_amount;

					void main(void)
					{
						gl_Position = gl_ModelViewProjectionMatrix * gl_Vertex;
						gl_FrontColor = gl_Color;

						light_amount = abs(dot(normalize(gl_NormalMatrix * gl_Normal), normalize(gl_LightSource[0].position.xyz)));
						light_amount += 0.2;
					}
									""","""
					varying float light_amount;

					void main(void)
					{
						gl_FragColor = vec4(gl_Color.xyz * light_amount, gl_Color[3]);
					}
				""")
				self._objectOverhangShader = openglHelpers.GLShader("""
					uniform float cosAngle;
					uniform mat3 rotMatrix;
					varying float light_amount;

					void main(void)
					{
						gl_Position = gl_ModelViewProjectionMatrix * gl_Vertex;
						gl_FrontColor = gl_Color;

						light_amount = abs(dot(normalize(gl_NormalMatrix * gl_Normal), normalize(gl_LightSource[0].position.xyz)));
						light_amount += 0.2;
						if (normalize(rotMatrix * gl_Normal).z < -cosAngle)
						{
							light_amount = -10.0;
						}
					}
				""","""
					varying float light_amount;

					void main(void)
					{
						if (light_amount == -10.0)
						{
							gl_FragColor = vec4(1.0, 0.0, 0.0, gl_Color[3]);
						}else{
							gl_FragColor = vec4(gl_Color.xyz * light_amount, gl_Color[3]);
						}
					}
									""")
				self._objectLoadShader = openglHelpers.GLShader("""
					uniform float intensity;
					uniform float scale;
					varying float light_amount;

					void main(void)
					{
						vec4 tmp = gl_Vertex;
						tmp.x += sin(tmp.z/5.0+intensity*30.0) * scale * intensity;
						tmp.y += sin(tmp.z/3.0+intensity*40.0) * scale * intensity;
						gl_Position = gl_ModelViewProjectionMatrix * tmp;
						gl_FrontColor = gl_Color;

						light_amount = abs(dot(normalize(gl_NormalMatrix * gl_Normal), normalize(gl_LightSource[0].position.xyz)));
						light_amount += 0.2;
					}
			""","""
				uniform float intensity;
				varying float light_amount;

				void main(void)
				{
					gl_FragColor = vec4(gl_Color.xyz * light_amount, 1.0-intensity);
				}
				""")
			if self._objectShader is None or not self._objectShader.isValid(): #Could not make shader.
				self._objectShader = openglHelpers.GLFakeShader()
				self._objectOverhangShader = openglHelpers.GLFakeShader()
				self._objectLoadShader = None
		self._init3DView()
		glTranslate(0,0,-self._zoom)
		glRotate(-self._pitch, 1,0,0)
		glRotate(self._yaw, 0,0,1)
		glTranslate(-self._viewTarget[0],-self._viewTarget[1],-self._viewTarget[2])

		self._viewport = glGetIntegerv(GL_VIEWPORT)
		self._modelMatrix = glGetDoublev(GL_MODELVIEW_MATRIX)
		self._projMatrix = glGetDoublev(GL_PROJECTION_MATRIX)

		glClearColor(1,1,1,1)
		glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT | GL_STENCIL_BUFFER_BIT)

		if self.viewMode != 'gcode':
			for n in xrange(0, len(self._scene.objects())):
				obj = self._scene.objects()[n]
				glColor4ub((n >> 16) & 0xFF, (n >> 8) & 0xFF, (n >> 0) & 0xFF, 0xFF)
				self._renderObject(obj)

		if self._mouseX > -1: # mouse has not passed over the opengl window.
			glFlush()
			n = glReadPixels(self._mouseX, self.GetSize().GetHeight() - 1 - self._mouseY, 1, 1, GL_RGBA, GL_UNSIGNED_INT_8_8_8_8)[0][0] >> 8
			if n < len(self._scene.objects()):
				self._focusObj = self._scene.objects()[n]
			else:
				self._focusObj = None
			f = glReadPixels(self._mouseX, self.GetSize().GetHeight() - 1 - self._mouseY, 1, 1, GL_DEPTH_COMPONENT, GL_FLOAT)[0][0]
			#self.GetTopLevelParent().SetTitle(hex(n) + " " + str(f))
			self._mouse3Dpos = openglHelpers.unproject(self._mouseX, self._viewport[1] + self._viewport[3] - self._mouseY, f, self._modelMatrix, self._projMatrix, self._viewport)
			self._mouse3Dpos -= self._viewTarget

		self._init3DView()
		glTranslate(0,0,-self._zoom)
		glRotate(-self._pitch, 1,0,0)
		glRotate(self._yaw, 0,0,1)
		glTranslate(-self._viewTarget[0],-self._viewTarget[1],-self._viewTarget[2])

		self._objectShader.unbind()
		self._engineResultView.OnDraw()
		if self.viewMode != 'gcode':
			glStencilFunc(GL_ALWAYS, 1, 1)
			glStencilOp(GL_INCR, GL_INCR, GL_INCR)

			if self.viewMode == 'overhang':
				self._objectOverhangShader.bind()
				self._objectOverhangShader.setUniform('cosAngle', math.cos(math.radians(90 - profile.getProfileSettingFloat('support_angle'))))
			else:
				self._objectShader.bind()
			for obj in self._scene.objects():
				if obj._loadAnim is not None:
					if obj._loadAnim.isDone():
						obj._loadAnim = None
					else:
						continue
				brightness = 1.0
				if self._focusObj == obj:
					brightness = 1.2
				elif self._focusObj is not None or self._selectedObj is not None and obj != self._selectedObj:
					brightness = 0.8

				if self._selectedObj == obj or self._selectedObj is None:
					#If we want transparent, then first render a solid black model to remove the printer size lines.
					if self.viewMode == 'transparent':
						glColor4f(0, 0, 0, 0)
						self._renderObject(obj)
						glEnable(GL_BLEND)
						glBlendFunc(GL_ONE, GL_ONE)
						glDisable(GL_DEPTH_TEST)
						brightness *= 0.5
					if self.viewMode == 'xray':
						glColorMask(GL_FALSE, GL_FALSE, GL_FALSE, GL_FALSE)
					glStencilOp(GL_INCR, GL_INCR, GL_INCR)
					glEnable(GL_STENCIL_TEST)

				if self.viewMode == 'overhang':
					if self._selectedObj == obj and self.tempMatrix is not None:
						self._objectOverhangShader.setUniform('rotMatrix', obj.getMatrix() * self.tempMatrix)
					else:
						self._objectOverhangShader.setUniform('rotMatrix', obj.getMatrix())

				if not self._scene.checkPlatform(obj):
					glColor4f(0.5 * brightness, 0.5 * brightness, 0.5 * brightness, 0.8 * brightness)
					self._renderObject(obj)
				else:
					self._renderObject(obj, brightness)
				glDisable(GL_STENCIL_TEST)
				glDisable(GL_BLEND)
				glEnable(GL_DEPTH_TEST)
				glColorMask(GL_TRUE, GL_TRUE, GL_TRUE, GL_TRUE)

			if self.viewMode == 'xray':
				glPushMatrix()
				glLoadIdentity()
				glEnable(GL_STENCIL_TEST)
				glStencilOp(GL_KEEP, GL_KEEP, GL_KEEP) #Keep values
				glDisable(GL_DEPTH_TEST)
				for i in xrange(2, 15, 2): #All even values
					glStencilFunc(GL_EQUAL, i, 0xFF)
					glColor(float(i)/10, float(i)/10, float(i)/5)
					glBegin(GL_QUADS)
					glVertex3f(-1000,-1000,-10)
					glVertex3f( 1000,-1000,-10)
					glVertex3f( 1000, 1000,-10)
					glVertex3f(-1000, 1000,-10)
					glEnd()
				for i in xrange(1, 15, 2): #All odd values
					glStencilFunc(GL_EQUAL, i, 0xFF)
					glColor(float(i)/10, 0, 0)
					glBegin(GL_QUADS)
					glVertex3f(-1000,-1000,-10)
					glVertex3f( 1000,-1000,-10)
					glVertex3f( 1000, 1000,-10)
					glVertex3f(-1000, 1000,-10)
					glEnd()
				glPopMatrix()
				glDisable(GL_STENCIL_TEST)
				glEnable(GL_DEPTH_TEST)

			self._objectShader.unbind()

			glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
			glEnable(GL_BLEND)
			if self._objectLoadShader is not None:
				self._objectLoadShader.bind()
				glColor4f(0.2, 0.6, 1.0, 1.0)
				for obj in self._scene.objects():
					if obj._loadAnim is None:
						continue
					self._objectLoadShader.setUniform('intensity', obj._loadAnim.getPosition())
					self._objectLoadShader.setUniform('scale', obj.getBoundaryCircle() / 10)
					self._renderObject(obj)
				self._objectLoadShader.unbind()
				glDisable(GL_BLEND)

		self._drawMachine()

		if self.viewMode != 'gcode':
			#Draw the object box-shadow, so you can see where it will collide with other objects.
			if self._selectedObj is not None:
				glEnable(GL_BLEND)
				glEnable(GL_CULL_FACE)
				glColor4f(0,0,0,0.16)
				glDepthMask(False)
				for obj in self._scene.objects():
					glPushMatrix()
					glTranslatef(obj.getPosition()[0], obj.getPosition()[1], 0)
					glBegin(GL_TRIANGLE_FAN)
					for p in obj._boundaryHull[::-1]:
						glVertex3f(p[0], p[1], 0)
					glEnd()
					glPopMatrix()
				if self._scene.isOneAtATime(): #Check print sequence mode.
					glPushMatrix()
					glColor4f(0,0,0,0.06)
					glTranslatef(self._selectedObj.getPosition()[0], self._selectedObj.getPosition()[1], 0)
					glBegin(GL_TRIANGLE_FAN)
					for p in self._selectedObj._printAreaHull[::-1]:
						glVertex3f(p[0], p[1], 0)
					glEnd()
					glBegin(GL_TRIANGLE_FAN)
					for p in self._selectedObj._headAreaMinHull[::-1]:
						glVertex3f(p[0], p[1], 0)
					glEnd()
					glPopMatrix()
				glDepthMask(True)
				glDisable(GL_CULL_FACE)

			#Draw the outline of the selected object on top of everything else except the GUI.
			if self._selectedObj is not None and self._selectedObj._loadAnim is None:
				glDisable(GL_DEPTH_TEST)
				glEnable(GL_CULL_FACE)
				glEnable(GL_STENCIL_TEST)
				glDisable(GL_BLEND)
				glStencilFunc(GL_EQUAL, 0, 255)

				glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)
				glLineWidth(2)
				glColor4f(1,1,1,0.5)
				self._renderObject(self._selectedObj)
				glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)

				glViewport(0, 0, self.GetSize().GetWidth(), self.GetSize().GetHeight())
				glDisable(GL_STENCIL_TEST)
				glDisable(GL_CULL_FACE)
				glEnable(GL_DEPTH_TEST)

			if self._selectedObj is not None:
				glPushMatrix()
				pos = self.getObjectCenterPos()
				glTranslate(pos[0], pos[1], pos[2])
				self.tool.OnDraw()
				glPopMatrix()
		if self.viewMode == 'overhang' and not openglHelpers.hasShaderSupport():
			glDisable(GL_DEPTH_TEST)
			glPushMatrix()
			glLoadIdentity()
			glTranslate(0,-4,-10)
			glColor4ub(60,60,60,255)
			openglHelpers.glDrawStringCenter(_("Overhang view not working due to lack of OpenGL shaders support."))
			glPopMatrix()

	def _renderObject(self, obj, brightness = 0, addSink = True):
		glPushMatrix()
		if addSink:
			glTranslate(obj.getPosition()[0], obj.getPosition()[1], obj.getSize()[2] / 2 - profile.getProfileSettingFloat('object_sink'))
		else:
			glTranslate(obj.getPosition()[0], obj.getPosition()[1], obj.getSize()[2] / 2)

		if self.tempMatrix is not None and obj == self._selectedObj:
			glMultMatrixf(openglHelpers.convert3x3MatrixTo4x4(self.tempMatrix))

		offset = obj.getDrawOffset()
		glTranslate(-offset[0], -offset[1], -offset[2] - obj.getSize()[2] / 2)

		glMultMatrixf(openglHelpers.convert3x3MatrixTo4x4(obj.getMatrix()))

		n = 0
		for m in obj._meshList:
			if m.vbo is None:
				m.vbo = openglHelpers.GLVBO(GL_TRIANGLES, m.vertexes, m.normal)
			if brightness != 0:
				glColor4fv(map(lambda idx: idx * brightness, self._objColors[n]))
				n += 1
			m.vbo.render()
		glPopMatrix()

	def _drawMachine(self):
		glEnable(GL_CULL_FACE)
		glEnable(GL_BLEND)

		size = [profile.getMachineSettingFloat('machine_width'), profile.getMachineSettingFloat('machine_depth'), profile.getMachineSettingFloat('machine_height')]

		machine = profile.getMachineSetting('machine_type')
		if machine.startswith('ultimaker'):
			if machine not in self._platformMesh:
				meshes = meshLoader.loadMeshes(resources.getPathForMesh(machine + '_platform.stl'))
				if len(meshes) > 0:
					self._platformMesh[machine] = meshes[0]
				else:
					self._platformMesh[machine] = None
				if machine == 'ultimaker2':
					self._platformMesh[machine]._drawOffset = numpy.array([0,-37,145], numpy.float32)
				else:
					self._platformMesh[machine]._drawOffset = numpy.array([0,0,2.5], numpy.float32)
			glColor4f(1,1,1,0.5)
			self._objectShader.bind()
			self._renderObject(self._platformMesh[machine], False, False)
			self._objectShader.unbind()

			#For the Ultimaker 2 render the texture on the back plate to show the Ultimaker2 text.
			if machine == 'ultimaker2':
				if not hasattr(self._platformMesh[machine], 'texture'):
					self._platformMesh[machine].texture = openglHelpers.loadGLTexture('Ultimaker2backplate.png')
				glBindTexture(GL_TEXTURE_2D, self._platformMesh[machine].texture)
				glEnable(GL_TEXTURE_2D)
				glPushMatrix()
				glColor4f(1,1,1,1)

				glTranslate(0,150,-5)
				h = 50
				d = 8
				w = 100
				glEnable(GL_BLEND)
				glBlendFunc(GL_DST_COLOR, GL_ZERO)
				glBegin(GL_QUADS)
				glTexCoord2f(1, 0)
				glVertex3f( w, 0, h)
				glTexCoord2f(0, 0)
				glVertex3f(-w, 0, h)
				glTexCoord2f(0, 1)
				glVertex3f(-w, 0, 0)
				glTexCoord2f(1, 1)
				glVertex3f( w, 0, 0)

				glTexCoord2f(1, 0)
				glVertex3f(-w, d, h)
				glTexCoord2f(0, 0)
				glVertex3f( w, d, h)
				glTexCoord2f(0, 1)
				glVertex3f( w, d, 0)
				glTexCoord2f(1, 1)
				glVertex3f(-w, d, 0)
				glEnd()
				glDisable(GL_TEXTURE_2D)
				glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
				glPopMatrix()
		else:
			glColor4f(0,0,0,1)
			glLineWidth(3)
			glBegin(GL_LINES)
			glVertex3f(-size[0] / 2, -size[1] / 2, 0)
			glVertex3f(-size[0] / 2, -size[1] / 2, 10)
			glVertex3f(-size[0] / 2, -size[1] / 2, 0)
			glVertex3f(-size[0] / 2+10, -size[1] / 2, 0)
			glVertex3f(-size[0] / 2, -size[1] / 2, 0)
			glVertex3f(-size[0] / 2, -size[1] / 2+10, 0)
			glEnd()

		glDepthMask(False)

		polys = profile.getMachineSizePolygons()
		height = profile.getMachineSettingFloat('machine_height')
		circular = profile.getMachineSetting('machine_shape') == 'Circular'
		glBegin(GL_QUADS)
		# Draw the sides of the build volume.
		for n in xrange(0, len(polys[0])):
			if not circular:
				if n % 2 == 0:
					glColor4ub(5, 171, 231, 96)
				else:
					glColor4ub(5, 171, 231, 64)
			else:
				glColor4ub(5, 171, 231, 96)

			glVertex3f(polys[0][n][0], polys[0][n][1], height)
			glVertex3f(polys[0][n][0], polys[0][n][1], 0)
			glVertex3f(polys[0][n-1][0], polys[0][n-1][1], 0)
			glVertex3f(polys[0][n-1][0], polys[0][n-1][1], height)
		glEnd()

		#Draw top of build volume.
		glColor4ub(5, 171, 231, 128)
		glBegin(GL_TRIANGLE_FAN)
		for p in polys[0][::-1]:
			glVertex3f(p[0], p[1], height)
		glEnd()

		#Draw checkerboard
		if self._platformTexture is None:
			self._platformTexture = openglHelpers.loadGLTexture('checkerboard.png')
			glBindTexture(GL_TEXTURE_2D, self._platformTexture)
			glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
			glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
		glColor4f(1,1,1,0.5)
		glBindTexture(GL_TEXTURE_2D, self._platformTexture)
		glEnable(GL_TEXTURE_2D)
		glBegin(GL_TRIANGLE_FAN)
		for p in polys[0]:
			glTexCoord2f(p[0]/20, p[1]/20)
			glVertex3f(p[0], p[1], 0)
		glEnd()

		#Draw no-go zones. (clips in case of UM2)
		glDisable(GL_TEXTURE_2D)
		glColor4ub(127, 127, 127, 200)
		for poly in polys[1:]:
			glBegin(GL_TRIANGLE_FAN)
			for p in poly:
				glTexCoord2f(p[0]/20, p[1]/20)
				glVertex3f(p[0], p[1], 0)
			glEnd()

		glDepthMask(True)
		glDisable(GL_BLEND)
		glDisable(GL_CULL_FACE)

	def getObjectCenterPos(self):
		if self._selectedObj is None:
			return [0.0, 0.0, 0.0]
		pos = self._selectedObj.getPosition()
		size = self._selectedObj.getSize()
		return [pos[0], pos[1], size[2]/2 - profile.getProfileSettingFloat('object_sink')]

	def getObjectBoundaryCircle(self):
		if self._selectedObj is None:
			return 0.0
		return self._selectedObj.getBoundaryCircle()

	def getObjectSize(self):
		if self._selectedObj is None:
			return [0.0, 0.0, 0.0]
		return self._selectedObj.getSize()

	def getObjectMatrix(self):
		if self._selectedObj is None:
			return numpy.matrix(numpy.identity(3))
		return self._selectedObj.getMatrix()

#TODO: Remove this or put it in a seperate file
class shaderEditor(wx.Frame):
	def __init__(self, parent, callback, v, f):
		super(shaderEditor, self).__init__(parent, title="Shader editor", style=wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER)
		self._callback = callback
		s = wx.BoxSizer(wx.VERTICAL)
		self.SetSizer(s)
		self._vertex = wx.TextCtrl(self, -1, v, style=wx.TE_MULTILINE)
		self._fragment = wx.TextCtrl(self, -1, f, style=wx.TE_MULTILINE)
		s.Add(self._vertex, 1, flag=wx.EXPAND)
		s.Add(self._fragment, 1, flag=wx.EXPAND)

		self._vertex.Bind(wx.EVT_TEXT, self.OnText, self._vertex)
		self._fragment.Bind(wx.EVT_TEXT, self.OnText, self._fragment)

		self.SetPosition(self.GetParent().GetPosition())
		self.SetSize((self.GetSize().GetWidth(), self.GetParent().GetSize().GetHeight()))
		self.Show()

	def OnText(self, e):
		self._callback(self._vertex.GetValue(), self._fragment.GetValue())

########NEW FILE########
__FILENAME__ = simpleMode
__copyright__ = "Copyright (C) 2013 David Braam - Released under terms of the AGPLv3 License"

import wx

from Cura.util import profile

class simpleModePanel(wx.Panel):
	"Main user interface window for Quickprint mode"
	def __init__(self, parent, callback):
		super(simpleModePanel, self).__init__(parent)
		self._callback = callback

		#toolsMenu = wx.Menu()
		#i = toolsMenu.Append(-1, 'Switch to Normal mode...')
		#self.Bind(wx.EVT_MENU, self.OnNormalSwitch, i)
		#self.menubar.Insert(1, toolsMenu, 'Normal mode')

		printTypePanel = wx.Panel(self)
		self.printTypeHigh = wx.RadioButton(printTypePanel, -1, _("High quality print"), style=wx.RB_GROUP)
		self.printTypeNormal = wx.RadioButton(printTypePanel, -1, _("Normal quality print"))
		self.printTypeLow = wx.RadioButton(printTypePanel, -1, _("Fast low quality print"))
		self.printTypeJoris = wx.RadioButton(printTypePanel, -1, _("Thin walled cup or vase"))
		self.printTypeJoris.Hide()

		printMaterialPanel = wx.Panel(self)
		self.printMaterialPLA = wx.RadioButton(printMaterialPanel, -1, 'PLA', style=wx.RB_GROUP)
		self.printMaterialABS = wx.RadioButton(printMaterialPanel, -1, 'ABS')
		self.printMaterialDiameter = wx.TextCtrl(printMaterialPanel, -1, profile.getProfileSetting('filament_diameter'))
		if profile.getMachineSetting('gcode_flavor') == 'UltiGCode':
			printMaterialPanel.Show(False)
		
		self.printSupport = wx.CheckBox(self, -1, _("Print support structure"))

		sizer = wx.GridBagSizer()
		self.SetSizer(sizer)

		sb = wx.StaticBox(printTypePanel, label=_("Select a quickprint profile:"))
		boxsizer = wx.StaticBoxSizer(sb, wx.VERTICAL)
		boxsizer.Add(self.printTypeHigh)
		boxsizer.Add(self.printTypeNormal)
		boxsizer.Add(self.printTypeLow)
		boxsizer.Add(self.printTypeJoris, border=5, flag=wx.TOP)
		printTypePanel.SetSizer(wx.BoxSizer(wx.VERTICAL))
		printTypePanel.GetSizer().Add(boxsizer, flag=wx.EXPAND)
		sizer.Add(printTypePanel, (0,0), flag=wx.EXPAND)

		sb = wx.StaticBox(printMaterialPanel, label=_("Material:"))
		boxsizer = wx.StaticBoxSizer(sb, wx.VERTICAL)
		boxsizer.Add(self.printMaterialPLA)
		boxsizer.Add(self.printMaterialABS)
		boxsizer.Add(wx.StaticText(printMaterialPanel, -1, _("Diameter:")))
		boxsizer.Add(self.printMaterialDiameter)
		printMaterialPanel.SetSizer(wx.BoxSizer(wx.VERTICAL))
		printMaterialPanel.GetSizer().Add(boxsizer, flag=wx.EXPAND)
		sizer.Add(printMaterialPanel, (1,0), flag=wx.EXPAND)

		sb = wx.StaticBox(self, label=_("Other:"))
		boxsizer = wx.StaticBoxSizer(sb, wx.VERTICAL)
		boxsizer.Add(self.printSupport)
		sizer.Add(boxsizer, (2,0), flag=wx.EXPAND)

		self.printTypeNormal.SetValue(True)
		self.printMaterialPLA.SetValue(True)

		self.printTypeHigh.Bind(wx.EVT_RADIOBUTTON, lambda e: self._callback())
		self.printTypeNormal.Bind(wx.EVT_RADIOBUTTON, lambda e: self._callback())
		self.printTypeLow.Bind(wx.EVT_RADIOBUTTON, lambda e: self._callback())
		#self.printTypeJoris.Bind(wx.EVT_RADIOBUTTON, lambda e: self._callback())

		self.printMaterialPLA.Bind(wx.EVT_RADIOBUTTON, lambda e: self._callback())
		self.printMaterialABS.Bind(wx.EVT_RADIOBUTTON, lambda e: self._callback())
		self.printMaterialDiameter.Bind(wx.EVT_TEXT, lambda e: self._callback())

		self.printSupport.Bind(wx.EVT_CHECKBOX, lambda e: self._callback())

	def setupSlice(self):
		put = profile.setTempOverride
		get = profile.getProfileSetting
		for setting in profile.settingsList:
			if not setting.isProfile():
				continue
			profile.setTempOverride(setting.getName(), setting.getDefault())

		if self.printSupport.GetValue():
			put('support', _("Exterior Only"))

		nozzle_size = float(get('nozzle_size'))
		if self.printTypeNormal.GetValue():
			put('layer_height', '0.2')
			put('wall_thickness', nozzle_size * 2.0)
			put('layer_height', '0.10')
			put('fill_density', '20')
		elif self.printTypeLow.GetValue():
			put('wall_thickness', nozzle_size * 2.5)
			put('layer_height', '0.20')
			put('fill_density', '10')
			put('print_speed', '60')
			put('cool_min_layer_time', '3')
			put('bottom_layer_speed', '30')
		elif self.printTypeHigh.GetValue():
			put('wall_thickness', nozzle_size * 2.0)
			put('layer_height', '0.06')
			put('fill_density', '20')
			put('bottom_layer_speed', '15')
		elif self.printTypeJoris.GetValue():
			put('wall_thickness', nozzle_size * 1.5)

		put('filament_diameter', self.printMaterialDiameter.GetValue())
		if self.printMaterialPLA.GetValue():
			pass
		if self.printMaterialABS.GetValue():
			put('print_bed_temperature', '100')
			put('platform_adhesion', 'Brim')
			put('filament_flow', '107')
			put('print_temperature', '245')
		put('plugin_config', '')

	def updateProfileToControls(self):
		pass

########NEW FILE########
__FILENAME__ = splashScreen
__copyright__ = "Copyright (C) 2013 David Braam - Released under terms of the AGPLv3 License"

import wx._core #We only need the core here, which speeds up the import. As we want to show the splashscreen ASAP.

from Cura.util.resources import getPathForImage

class splashScreen(wx.SplashScreen):
	def __init__(self, callback):
		self.callback = callback
		bitmap = wx.Bitmap(getPathForImage('splash.png'))
		super(splashScreen, self).__init__(bitmap, wx.SPLASH_CENTRE_ON_SCREEN, 0, None)
		wx.CallAfter(self.DoCallback)

	def DoCallback(self):
		self.callback()
		self.Destroy()

########NEW FILE########
__FILENAME__ = imageToMesh
__copyright__ = "Copyright (C) 2013 David Braam - Released under terms of the AGPLv3 License"

import wx
import numpy

from Cura.util import printableObject

def supportedExtensions():
	return ['.bmp', '.jpg', '.jpeg', '.png']

class convertImageDialog(wx.Dialog):
	def __init__(self, parent, filename):
		super(convertImageDialog, self).__init__(None, title="Convert image...")
		wx.EVT_CLOSE(self, self.OnClose)
		self.parent = parent
		self.filename = filename

		image = wx.Image(filename)
		w, h = image.GetWidth() - 1, image.GetHeight() - 1
		self.aspectRatio = float(w) / float(h)

		p = wx.Panel(self)
		self.SetSizer(wx.BoxSizer())
		self.GetSizer().Add(p, 1, flag=wx.EXPAND)

		s = wx.GridBagSizer(2, 2)
		p.SetSizer(s)
		s.Add(wx.StaticText(p, -1, _('Height (mm)')), pos=(0, 0), flag=wx.LEFT|wx.TOP|wx.RIGHT, border=5)
		self.heightInput = wx.TextCtrl(p, -1, '10.0')
		s.Add(self.heightInput, pos=(0, 1), flag=wx.LEFT|wx.TOP|wx.RIGHT|wx.EXPAND, border=5)

		s.Add(wx.StaticText(p, -1, _('Base (mm)')), pos=(1, 0), flag=wx.LEFT|wx.TOP|wx.RIGHT, border=5)
		self.baseHeightInput = wx.TextCtrl(p, -1, '1.0')
		s.Add(self.baseHeightInput, pos=(1, 1), flag=wx.LEFT|wx.TOP|wx.RIGHT|wx.EXPAND, border=5)

		s.Add(wx.StaticText(p, -1, _('Width (mm)')), pos=(2, 0), flag=wx.LEFT|wx.TOP|wx.RIGHT, border=5)
		self.widthInput = wx.TextCtrl(p, -1, str(w * 0.3))
		s.Add(self.widthInput, pos=(2, 1), flag=wx.LEFT|wx.TOP|wx.RIGHT|wx.EXPAND, border=5)

		s.Add(wx.StaticText(p, -1, _('Depth (mm)')), pos=(3, 0), flag=wx.LEFT|wx.TOP|wx.RIGHT, border=5)
		self.depthInput = wx.TextCtrl(p, -1, str(h * 0.3))
		s.Add(self.depthInput, pos=(3, 1), flag=wx.LEFT|wx.TOP|wx.RIGHT|wx.EXPAND, border=5)

		options = ['Darker is higher', 'Lighter is higher']
		self.invertInput = wx.ComboBox(p, -1, options[0], choices=options, style=wx.CB_DROPDOWN|wx.CB_READONLY)
		s.Add(self.invertInput, pos=(4, 1), flag=wx.LEFT|wx.TOP|wx.RIGHT|wx.EXPAND, border=5)
		self.invertInput.SetSelection(0)

		options = ['No smoothing', 'Light smoothing', 'Heavy smoothing']
		self.smoothInput = wx.ComboBox(p, -1, options[0], choices=options, style=wx.CB_DROPDOWN|wx.CB_READONLY)
		s.Add(self.smoothInput, pos=(5, 1), flag=wx.LEFT|wx.TOP|wx.RIGHT|wx.EXPAND, border=5)
		self.smoothInput.SetSelection(0)

		self.okButton = wx.Button(p, -1, 'Ok')
		s.Add(self.okButton, pos=(6, 1), flag=wx.ALL, border=5)

		self.okButton.Bind(wx.EVT_BUTTON, self.OnOkClick)
		self.widthInput.Bind(wx.EVT_TEXT, self.OnWidthEnter)
		self.depthInput.Bind(wx.EVT_TEXT, self.OnDepthEnter)

		self.Fit()
		self.Centre()

	def OnClose(self, e):
		self.Destroy()

	def OnOkClick(self, e):
		self.Close()
		height = float(self.heightInput.GetValue())
		width = float(self.widthInput.GetValue())
		blur = self.smoothInput.GetSelection()
		blur *= blur
		invert = self.invertInput.GetSelection() == 0
		baseHeight = float(self.baseHeightInput.GetValue())

		obj = convertImage(self.filename, height, width, blur, invert, baseHeight)
		self.parent._scene.add(obj)
		self.parent._scene.centerAll()
		self.parent.sceneUpdated()

	def OnWidthEnter(self, e):
		try:
			w = float(self.widthInput.GetValue())
		except ValueError:
			return
		h = w / self.aspectRatio
		self.depthInput.SetValue(str(h))

	def OnDepthEnter(self, e):
		try:
			h = float(self.depthInput.GetValue())
		except ValueError:
			return
		w = h * self.aspectRatio
		self.widthInput.SetValue(str(w))

def convertImage(filename, height=20.0, width=100.0, blur=0, invert=False, baseHeight=1.0):
	image = wx.Image(filename)
	image.ConvertToGreyscale()
	if image.GetHeight() > 512:
		image.Rescale(image.GetWidth() * 512 / image.GetHeight(), 512, wx.IMAGE_QUALITY_HIGH)
	if image.GetWidth() > 512:
		image.Rescale(512, image.GetHeight() * 512 / image.GetWidth(), wx.IMAGE_QUALITY_HIGH)
	if blur > 0:
		image = image.Blur(blur)
	z = numpy.fromstring(image.GetData(), numpy.uint8)
	z = numpy.array(z[::3], numpy.float32)	#Only get the R values (as we are grayscale), and convert to float values
	if invert:
		z = 255 - z
	pMin, pMax = numpy.min(z), numpy.max(z)
	if pMax == pMin:
		pMax += 1.0
	z = ((z - pMin) * height / (pMax - pMin)) + baseHeight

	w, h = image.GetWidth(), image.GetHeight()
	scale = width / (image.GetWidth() - 1)
	n = w * h
	y, x = numpy.mgrid[0:h,0:w]
	x = numpy.array(x, numpy.float32, copy=False) * scale
	y = numpy.array(y, numpy.float32, copy=False) *-scale
	v0 = numpy.concatenate((x.reshape((n, 1)), y.reshape((n, 1)), z.reshape((n, 1))), 1)
	v0 = v0.reshape((h, w, 3))
	v1 = v0[0:-1,0:-1,:]
	v2 = v0[0:-1,1:,:]
	v3 = v0[1:,0:-1,:]
	v4 = v0[1:,1:,:]

	obj = printableObject.printableObject(filename)
	m = obj._addMesh()
	m._prepareFaceCount((w-1) * (h-1) * 2 + 2 + (w-1)*4 + (h-1)*4)
	m.vertexes = numpy.array(numpy.concatenate((v1,v3,v2,v2,v3,v4), 2).reshape(((w-1) * (h-1) * 6, 3)), numpy.float32, copy=False)
	m.vertexes = numpy.concatenate((m.vertexes, numpy.zeros(((2+(w-1)*4+(h-1)*4)*3, 3), numpy.float32)))
	m.vertexCount = (w-1) * (h-1) * 6
	x = (w-1)* scale
	y = (h-1)*-scale
	m._addFace(0,0,0, x,0,0, 0,y,0)
	m._addFace(x,y,0, 0,y,0, x,0,0)
	for n in xrange(0, w-1):
		x = n* scale
		i = w*h-w+n
		m._addFace(x+scale,0,0, x,0,0, x,0,z[n])
		m._addFace(x+scale,0,0, x,0,z[n], x+scale,0,z[n+1])
		m._addFace(x+scale,y,0, x,y,z[i], x,y,0)
		m._addFace(x+scale,y,0, x+scale,y,z[i+1], x,y,z[i])

	x = (w-1)*scale
	for n in xrange(0, h-1):
		y = n*-scale
		i = n*w+w-1
		m._addFace(0,y-scale,0, 0,y,z[n*w], 0,y,0)
		m._addFace(0,y-scale,0, 0,y-scale,z[n*w+w], 0,y,z[n*w])
		m._addFace(x,y-scale,0, x,y,0, x,y,z[i])
		m._addFace(x,y-scale,0, x,y,z[i], x,y-scale,z[i+w])
	obj._postProcessAfterLoad()
	return obj

########NEW FILE########
__FILENAME__ = minecraftImport
"""
Tool to import sections of minecraft levels into Cura.
This makes use of the pymclevel module from David Rio Vierra
"""
__copyright__ = "Copyright (C) 2013 David Braam - Released under terms of the AGPLv3 License"

import wx
import glob
import os
import numpy

from Cura.util import printableObject
from Cura.util.meshLoaders import stl
from Cura.util.pymclevel import mclevel

def hasMinecraft():
	return os.path.isdir(mclevel.saveFileDir)

class minecraftImportWindow(wx.Frame):
	def __init__(self, parent):
		super(minecraftImportWindow, self).__init__(parent, title='Cura - Minecraft import')

		saveFileList = map(os.path.basename, glob.glob(mclevel.saveFileDir + "/*"))

		self.panel = wx.Panel(self, -1)
		self.SetSizer(wx.BoxSizer())
		self.GetSizer().Add(self.panel, 1, wx.EXPAND)

		sizer = wx.GridBagSizer(2, 2)

		self.saveListBox = wx.ListBox(self.panel, -1, choices=saveFileList)
		sizer.Add(self.saveListBox, (0,0), span=(2,1), flag=wx.EXPAND)
		self.playerListBox = wx.ListBox(self.panel, -1, choices=[])
		sizer.Add(self.playerListBox, (0,1), span=(2,1), flag=wx.EXPAND)

		self.previewPanel = wx.Panel(self.panel, -1)
		self.previewPanel.SetMinSize((512, 512))
		sizer.Add(self.previewPanel, (0,2), flag=wx.EXPAND)

		self.importButton = wx.Button(self.panel, -1, 'Import')
		sizer.Add(self.importButton, (1,2))

		sizer.AddGrowableRow(1)

		self.panel.SetSizer(sizer)

		self.saveListBox.Bind(wx.EVT_LISTBOX, self.OnSaveSelect)
		self.playerListBox.Bind(wx.EVT_LISTBOX, self.OnPlayerSelect)
		self.importButton.Bind(wx.EVT_BUTTON, self.OnImport)

		self.previewPanel.Bind(wx.EVT_PAINT, self.OnPaintPreview)
		self.previewPanel.Bind(wx.EVT_SIZE, self.OnSizePreview)
		self.previewPanel.Bind(wx.EVT_ERASE_BACKGROUND, self.OnEraseBackgroundPreview)
		self.previewPanel.Bind(wx.EVT_MOTION, self.OnMotion)

		self.level = None
		self.previewImage = None
		self.renderList = []
		self.selectArea = None
		self.draggingArea = False

		self.Layout()
		self.Fit()

		self.gravelPen = wx.Pen(wx.Colour(128, 128, 128))
		self.sandPen = wx.Pen(wx.Colour(192, 192, 0))
		self.grassPen = []
		self.waterPen = []
		for z in xrange(0, 256):
			self.waterPen.append(wx.Pen(wx.Colour(0,0,min(z+64, 255))))
			self.grassPen.append(wx.Pen(wx.Colour(0,min(64+z,255),0)))

		self.isSolid = [True] * 256
		self.isSolid[0] = False #Air
		self.isSolid[8] = False #Water
		self.isSolid[9] = False #Water
		self.isSolid[10] = False #Lava
		self.isSolid[11] = False #Lava
		self.isSolid[50] = False #Torch
		self.isSolid[51] = False #Fire

	def OnSaveSelect(self, e):
		if self.saveListBox.Selection < 0:
			return
		self.level = mclevel.loadWorld(self.saveListBox.GetItems()[self.saveListBox.Selection])
		self.playerListBox.Clear()
		for player in self.level.players:
			self.playerListBox.Append(player)

	def OnPlayerSelect(self, e):
		playerName = self.playerListBox.GetItems()[self.playerListBox.Selection]
		self.playerPos = map(lambda n: int(n / 16), self.level.getPlayerPosition(playerName))[0::2]

		self.previewImage = wx.EmptyBitmap(512, 512)
		for i in xrange(0, 16):
			for j in xrange(1, i * 2 + 1):
				self.renderList.insert(0, (15 - i, 16 + i - j))
			for j in xrange(0, i * 2 + 1):
				self.renderList.insert(0, (15 + j - i, 15 - i))
			for j in xrange(0, i * 2 + 1):
				self.renderList.insert(0, (16 + i, 15 + j - i))
			for j in xrange(0, i * 2 + 2):
				self.renderList.insert(0, (16 + i - j, 16 + i))
		self.previewPanel.Refresh()

	def OnPaintPreview(self, e):
		if len(self.renderList) > 0:
			cx, cy = self.renderList.pop()
			dc = wx.MemoryDC()
			dc.SelectObject(self.previewImage)
			chunk = self.level.getChunk(cx + self.playerPos[0] - 16, cy + self.playerPos[1] - 16)
			dc.SetPen(wx.Pen(wx.Colour(255,0,0)))
			for x in xrange(0, 16):
				for y in xrange(0, 16):
					z = numpy.max(numpy.where(chunk.Blocks[x, y] != 0))
					type = chunk.Blocks[x, y, z]
					if type == 1:    #Stone
						dc.SetPen(wx.Pen(wx.Colour(z,z,z)))
					elif type == 2:    #Grass
						dc.SetPen(self.grassPen[z])
					elif type == 8 or type == 9: #Water
						dc.SetPen(self.waterPen[z])
					elif type == 10 or type == 11: #Lava
						dc.SetPen(wx.Pen(wx.Colour(min(z+64, 255),0,0)))
					elif type == 12 or type == 24: #Sand/Standstone
						dc.SetPen(self.sandPen)
					elif type == 13: #Gravel
						dc.SetPen(self.gravelPen)
					elif type == 18: #Leaves
						dc.SetPen(wx.Pen(wx.Colour(0,max(z-32, 0),0)))
					else:
						dc.SetPen(wx.Pen(wx.Colour(z,z,z)))
					dc.DrawPoint(cx * 16 + x, cy * 16 + y)
			dc.SelectObject(wx.NullBitmap)
			wx.CallAfter(self.previewPanel.Refresh)

		dc = wx.BufferedPaintDC(self.previewPanel)
		dc.SetBackground(wx.Brush(wx.BLACK))
		dc.Clear()
		if self.previewImage is not None:
			dc.DrawBitmap(self.previewImage, 0, 0)
		if self.selectArea is not None:
			dc.SetPen(wx.Pen(wx.Colour(255,0,0)))
			dc.SetBrush(wx.Brush(None, style=wx.TRANSPARENT))
			dc.DrawRectangle(self.selectArea[0], self.selectArea[1], self.selectArea[2] - self.selectArea[0] + 1, self.selectArea[3] - self.selectArea[1] + 1)

	def OnSizePreview(self, e):
		self.previewPanel.Refresh()
		self.previewPanel.Update()

	def OnEraseBackgroundPreview(self, e):
		pass

	def OnMotion(self, e):
		if e.Dragging():
			if not self.draggingArea:
				self.draggingArea = True
				self.selectArea = [e.GetX(), e.GetY(), e.GetX(), e.GetY()]
			self.selectArea[2] = e.GetX()
			self.selectArea[3] = e.GetY()
			self.previewPanel.Refresh()
		else:
			self.draggingArea = False

	def OnImport(self, e):
		if self.level is None or self.selectArea is None:
			return

		xMin = min(self.selectArea[0], self.selectArea[2]) + (self.playerPos[0] - 16) * 16
		xMax = max(self.selectArea[0], self.selectArea[2]) + (self.playerPos[0] - 16) * 16
		yMin = min(self.selectArea[1], self.selectArea[3]) + (self.playerPos[1] - 16) * 16
		yMax = max(self.selectArea[1], self.selectArea[3]) + (self.playerPos[1] - 16) * 16

		sx = (xMax - xMin + 1)
		sy = (yMax - yMin + 1)
		blocks = numpy.zeros((sx, sy, 256), numpy.int32)

		cxMin = int(xMin / 16)
		cxMax = int((xMax + 15) / 16)
		cyMin = int(yMin / 16)
		cyMax = int((yMax + 15) / 16)

		for cx in xrange(cxMin, cxMax + 1):
			for cy in xrange(cyMin, cyMax + 1):
				chunk = self.level.getChunk(cx, cy)
				for x in xrange(0, 16):
					bx = x + cx * 16
					if xMin <= bx <= xMax:
						for y in xrange(0, 16):
							by = y + cy * 16
							if yMin <= by <= yMax:
								blocks[bx - xMin, by - yMin] = chunk.Blocks[x, y]
		minZ = 256
		maxZ = 0
		for x in xrange(0, sx):
			for y in xrange(0, sy):
				minZ = min(minZ, numpy.max(numpy.where(blocks[x, y] != 0)))
				maxZ = max(maxZ, numpy.max(numpy.where(blocks[x, y] != 0)))
		minZ += 1

		faceCount = 0
		for x in xrange(0, sx):
			for y in xrange(0, sy):
				for z in xrange(minZ, maxZ + 1):
					if self.isSolid[blocks[x, y, z]]:
						if z == maxZ or not self.isSolid[blocks[x, y, z + 1]]:
							faceCount += 1
						if z == minZ or not self.isSolid[blocks[x, y, z - 1]]:
							faceCount += 1
						if x == 0 or not self.isSolid[blocks[x - 1, y, z]]:
							faceCount += 1
						if x == sx - 1 or not self.isSolid[blocks[x + 1, y, z]]:
							faceCount += 1
						if y == 0 or not self.isSolid[blocks[x, y - 1, z]]:
							faceCount += 1
						if y == sy - 1 or not self.isSolid[blocks[x, y + 1, z]]:
							faceCount += 1

		obj = printableObject.printableObject(None)
		m = obj._addMesh()
		m._prepareFaceCount(faceCount * 2)
		for x in xrange(0, sx):
			for y in xrange(0, sy):
				for z in xrange(minZ, maxZ + 1):
					if self.isSolid[blocks[x, y, z]]:
						if z == maxZ or not self.isSolid[blocks[x, y, z + 1]]:
							m._addFace(x, y, z+1, x+1, y, z+1, x, y+1, z+1)

							m._addFace(x+1, y+1, z+1, x, y+1, z+1, x+1, y, z+1)

						if z == minZ or not self.isSolid[blocks[x, y, z - 1]]:
							m._addFace(x, y, z, x, y+1, z, x+1, y, z)

							m._addFace(x+1, y+1, z, x+1, y, z, x, y+1, z)

						if x == 0 or not self.isSolid[blocks[x - 1, y, z]]:
							m._addFace(x, y, z, x, y, z+1, x, y+1, z)

							m._addFace(x, y+1, z+1, x, y+1, z, x, y, z+1)

						if x == sx - 1 or not self.isSolid[blocks[x + 1, y, z]]:
							m._addFace(x+1, y, z, x+1, y+1, z, x+1, y, z+1)

							m._addFace(x+1, y+1, z+1, x+1, y, z+1, x+1, y+1, z)

						if y == 0 or not self.isSolid[blocks[x, y - 1, z]]:
							m._addFace(x, y, z, x+1, y, z, x, y, z+1)

							m._addFace(x+1, y, z+1, x, y, z+1, x+1, y, z)

						if y == sy - 1 or not self.isSolid[blocks[x, y + 1, z]]:
							m._addFace(x, y+1, z, x, y+1, z+1, x+1, y+1, z)

							m._addFace(x+1, y+1, z+1, x+1, y+1, z, x, y+1, z+1)

		obj._postProcessAfterLoad()
		self.GetParent().scene._scene.add(obj)

########NEW FILE########
__FILENAME__ = pidDebugger
__copyright__ = "Copyright (C) 2013 David Braam - Released under terms of the AGPLv3 License"

import wx
import time

from Cura.util import machineCom

class debuggerWindow(wx.Frame):
	def __init__(self, parent):
		super(debuggerWindow, self).__init__(parent, title='Cura - PID Debugger')

		self.machineCom = None
		self.machineCom = machineCom.MachineCom(callbackObject=self)
		self.coolButton = wx.Button(self, -1, '0C')
		self.heatupButton = wx.Button(self, -1, '200C')
		self.heatupButton2 = wx.Button(self, -1, '260C')
		self.heatupButton3 = wx.Button(self, -1, '300C')
		self.fanOn = wx.Button(self, -1, 'Fan ON')
		self.fanOn50 = wx.Button(self, -1, 'Fan ON 50%')
		self.fanOff = wx.Button(self, -1, 'Fan OFF')
		self.graph = temperatureGraph(self)
		self.targetTemp = 0
		self.pValue = wx.TextCtrl(self, -1, '0')
		self.iValue = wx.TextCtrl(self, -1, '0')
		self.dValue = wx.TextCtrl(self, -1, '0')

		self.sizer = wx.GridBagSizer(0, 0)
		self.SetSizer(self.sizer)
		self.sizer.Add(self.graph, pos=(0, 0), span=(1, 8), flag=wx.EXPAND)
		self.sizer.Add(self.coolButton, pos=(1, 0), flag=wx.EXPAND)
		self.sizer.Add(self.heatupButton, pos=(1, 1), flag=wx.EXPAND)
		self.sizer.Add(self.heatupButton2, pos=(1, 2), flag=wx.EXPAND)
		self.sizer.Add(self.heatupButton3, pos=(1, 3), flag=wx.EXPAND)
		self.sizer.Add(self.fanOn, pos=(1, 4), flag=wx.EXPAND)
		self.sizer.Add(self.fanOn50, pos=(1, 5), flag=wx.EXPAND)
		self.sizer.Add(self.fanOff, pos=(1, 6), flag=wx.EXPAND)
		self.sizer.Add(self.pValue, pos=(2, 0), flag=wx.EXPAND)
		self.sizer.Add(self.iValue, pos=(2, 1), flag=wx.EXPAND)
		self.sizer.Add(self.dValue, pos=(2, 2), flag=wx.EXPAND)
		self.sizer.AddGrowableCol(7)
		self.sizer.AddGrowableRow(0)

		wx.EVT_CLOSE(self, self.OnClose)
		self.Bind(wx.EVT_BUTTON, lambda e: self.setTemp(0), self.coolButton)
		self.Bind(wx.EVT_BUTTON, lambda e: self.setTemp(200), self.heatupButton)
		self.Bind(wx.EVT_BUTTON, lambda e: self.setTemp(260), self.heatupButton2)
		self.Bind(wx.EVT_BUTTON, lambda e: self.setTemp(300), self.heatupButton3)
		self.Bind(wx.EVT_BUTTON, lambda e: self.machineCom.sendCommand('M106'), self.fanOn)
		self.Bind(wx.EVT_BUTTON, lambda e: self.machineCom.sendCommand('M106 S128'), self.fanOn50)
		self.Bind(wx.EVT_BUTTON, lambda e: self.machineCom.sendCommand('M107'), self.fanOff)
		self.Bind(wx.EVT_TEXT, self.updatePID, self.pValue)
		self.Bind(wx.EVT_TEXT, self.updatePID, self.iValue)
		self.Bind(wx.EVT_TEXT, self.updatePID, self.dValue)

		self.Layout()
		self.Fit()

	def updatePID(self, e):
		try:
			p = float(self.pValue.GetValue())
			i = float(self.iValue.GetValue())
			d = float(self.dValue.GetValue())
		except:
			return
		self.machineCom.sendCommand("M301 P%f I%f D%f" % (p, i, d))

	def setTemp(self, temp):
		self.targetTemp = temp
		self.machineCom.sendCommand("M104 S%d" % (temp))

	def OnClose(self, e):
		self.machineCom.close()
		self.Destroy()

	def mcLog(self, message):
		pass

	def mcTempUpdate(self, temp, bedTemp, targetTemp, bedTargetTemp):
		pass

	def mcStateChange(self, state):
		if self.machineCom is not None and self.machineCom.isOperational():
			self.machineCom.sendCommand("M503\n")
			self.machineCom.sendCommand("M503\n")

	def mcMessage(self, message):
		if 'PIDDEBUG' in message:
			#echo: PIDDEBUG 0: Input 40.31 Output 0.00 pTerm 0.00 iTerm 0.00 dTerm 0.00
			message = message.strip().split()
			temperature = float(message[message.index("Input")+1])
			heater_output = float(message[message.index("Output")+1])
			pTerm = float(message[message.index("pTerm")+1])
			iTerm = float(message[message.index("iTerm")+1])
			dTerm = float(message[message.index("dTerm")+1])

			self.graph.addPoint(temperature, heater_output, pTerm, iTerm, dTerm, self.targetTemp)
		elif 'M301' in message:
			for m in message.strip().split():
				if m[0] == 'P':
					wx.CallAfter(self.pValue.SetValue, m[1:])
				if m[0] == 'I':
					wx.CallAfter(self.iValue.SetValue, m[1:])
				if m[0] == 'D':
					wx.CallAfter(self.dValue.SetValue, m[1:])

	def mcProgress(self, lineNr):
		pass

	def mcZChange(self, newZ):
		pass

class temperatureGraph(wx.Panel):
	def __init__(self, parent):
		super(temperatureGraph, self).__init__(parent)

		self.Bind(wx.EVT_ERASE_BACKGROUND, self.OnEraseBackground)
		self.Bind(wx.EVT_SIZE, self.OnSize)
		self.Bind(wx.EVT_PAINT, self.OnDraw)

		self.lastDraw = time.time() - 1.0
		self.points = []
		self.backBuffer = None
		self.SetMinSize((320, 200))
		self.addPoint(0,0,0,0,0,0)

	def OnEraseBackground(self, e):
		pass

	def OnSize(self, e):
		if self.backBuffer is None or self.GetSize() != self.backBuffer.GetSize():
			self.backBuffer = wx.EmptyBitmap(*self.GetSizeTuple())
			self.UpdateDrawing(True)

	def OnDraw(self, e):
		dc = wx.BufferedPaintDC(self, self.backBuffer)

	def _drawBackgroundForLine(self, dc, color, f):
		w, h = self.GetSizeTuple()
		color = wx.Pen(color)
		dc.SetPen(color)
		x0 = 0
		v0 = 0
		for p in self.points:
			x1 = int(w - (self.now - p[0]) * self.timeScale)
			value = f(p)
			for x in xrange(x0, x1 + 1):
				v = float(x - x0) / float(x1 - x0 + 1) * (value - v0) + v0
				dc.DrawLine(x, h, x, h - (v * h / 300))
			v0 = value
			x0 = x1 + 1

	def _drawLine(self, dc, color, f):
		w, h = self.GetSizeTuple()
		color = wx.Pen(color)
		dc.SetPen(color)
		x0 = 0
		v0 = 0
		for p in self.points:
			x1 = int(w - (self.now - p[0]) * self.timeScale)
			value = f(p)
			dc.DrawLine(x0, h - (v0 * h / 300), x1, h - (value * h / 300), )
			dc.DrawPoint(x1, h - (value * h / 300), )
			v0 = value
			x0 = x1 + 1

	def UpdateDrawing(self, force=False):
		now = time.time()
		self.timeScale = 10
		self.now = now
		if not force and now - self.lastDraw < 0.1:
			return
		self.lastDraw = now
		dc = wx.MemoryDC()
		dc.SelectObject(self.backBuffer)
		dc.Clear()
		dc.SetFont(wx.SystemSettings.GetFont(wx.SYS_SYSTEM_FONT))
		w, h = self.GetSizeTuple()
		bgLinePen = wx.Pen('#A0A0A0')

		#Draw the background up to the current temperatures.
		self._drawBackgroundForLine(dc, '#FFD0D0', lambda p: p[1])#temp
		self._drawBackgroundForLine(dc, '#D0D0FF', lambda p: p[3])#pTerm
		self._drawBackgroundForLine(dc, '#D0FFD0', lambda p: abs(p[5]))#dTerm

		#Draw the grid
		for x in xrange(w, 0, -5 * self.timeScale):
			dc.SetPen(bgLinePen)
			dc.DrawLine(x, 0, x, h)
		tmpNr = 0
		for y in xrange(h - 1, 0, -h * 50 / 300):
			dc.SetPen(bgLinePen)
			dc.DrawLine(0, y, w, y)
			dc.DrawText(str(tmpNr), 0, y - dc.GetFont().GetPixelSize().GetHeight())
			tmpNr += 50
		dc.DrawLine(0, 0, w, 0)
		dc.DrawLine(0, 0, 0, h)
		if len(self.points) > 10:
			tempAvg = 0.0
			heaterAvg = 0.0
			for n in xrange(0, 10):
				tempAvg += self.points[-n-1][1]
				heaterAvg += self.points[-n-1][2]
			dc.DrawText("Temp: %d Heater: %d" % (tempAvg / 10, heaterAvg * 100 / 255 / 10), 0, 0)

		#Draw the main lines
		self._drawLine(dc, '#404040', lambda p: p[6])#target
		self._drawLine(dc, '#40FFFF', lambda p: p[3])#pTerm
		self._drawLine(dc, '#FF40FF', lambda p: p[4])#iTerm
		self._drawLine(dc, '#FFFF40', lambda p: p[5])#dTerm
		self._drawLine(dc, '#4040FF', lambda p: -p[5])#dTerm
		self._drawLine(dc, '#FF4040', lambda p: p[1])#temp
		self._drawLine(dc, '#40FF40', lambda p: p[2])#heater

		del dc
		self.Refresh(eraseBackground=False)
		self.Update()

		if len(self.points) > 0 and (time.time() - self.points[0][0]) > (w + 20) / self.timeScale:
			self.points.pop(0)

	def addPoint(self, temperature, heater_output, pTerm, iTerm, dTerm, targetTemp):
		self.points.append([time.time(), temperature, heater_output, pTerm, iTerm, dTerm, targetTemp])
		wx.CallAfter(self.UpdateDrawing)

########NEW FILE########
__FILENAME__ = youmagineGui
__copyright__ = "Copyright (C) 2013 David Braam - Released under terms of the AGPLv3 License"

import wx
import threading
import time
import re
import os
import types
import webbrowser
import cStringIO as StringIO

from Cura.util import profile
from Cura.util import youmagine
from Cura.util.meshLoaders import stl
from Cura.util.meshLoaders import amf
from Cura.util.resources import getPathForImage

from Cura.gui.util import webcam

DESIGN_FILE_EXT = ['.scad', '.blend', '.max', '.stp', '.step', '.igs', '.iges', '.sldasm', '.sldprt', '.skp', '.iam', '.prt', '.x_t', '.ipt', '.dwg', '.123d', '.wings', '.fcstd', '.top']

def getClipboardText():
	ret = ''
	try:
		if not wx.TheClipboard.IsOpened():
			wx.TheClipboard.Open()
			do = wx.TextDataObject()
			if wx.TheClipboard.GetData(do):
				ret = do.GetText()
			wx.TheClipboard.Close()
		return ret
	except:
		return ret

def getAdditionalFiles(objects, onlyExtChanged):
	names = set()
	for obj in objects:
		name = obj.getOriginFilename()
		if name is None:
			continue
		names.add(name[:name.rfind('.')])
	ret = []
	for name in names:
		for ext in DESIGN_FILE_EXT:
			if os.path.isfile(name + ext):
				ret.append(name + ext)
	if onlyExtChanged:
		return ret
	onlyExtList = ret
	ret = []
	for name in names:
		for ext in DESIGN_FILE_EXT:
			for filename in os.listdir(os.path.dirname(name)):
				filename = os.path.join(os.path.dirname(name), filename)
				if filename.endswith(ext) and filename not in ret and filename not in onlyExtList:
					ret.append(filename)
	return ret

class youmagineManager(object):
	def __init__(self, parent, objectScene):
		self._mainWindow = parent
		self._scene = objectScene
		self._ym = youmagine.Youmagine(profile.getPreference('youmagine_token'), self._progressCallback)

		self._indicatorWindow = workingIndicatorWindow(self._mainWindow)
		self._getAuthorizationWindow = getAuthorizationWindow(self._mainWindow, self._ym)
		self._newDesignWindow = newDesignWindow(self._mainWindow, self, self._ym)

		thread = threading.Thread(target=self.checkAuthorizationThread)
		thread.daemon = True
		thread.start()

	def _progressCallback(self, progress):
		self._indicatorWindow.progress(progress)

	#Do all the youmagine communication in a background thread, because it can take a while and block the UI thread otherwise
	def checkAuthorizationThread(self):
		wx.CallAfter(self._indicatorWindow.showBusy, _("Checking token"))
		if not self._ym.isAuthorized():
			wx.CallAfter(self._indicatorWindow.Hide)
			if not self._ym.isHostReachable():
				wx.CallAfter(wx.MessageBox, _("Failed to contact YouMagine.com"), _("YouMagine error."), wx.OK | wx.ICON_ERROR)
				return
			wx.CallAfter(self._getAuthorizationWindow.Show)
			lastTriedClipboard = ''
			while not self._ym.isAuthorized():
				time.sleep(0.1)
				if self._getAuthorizationWindow.abort:
					wx.CallAfter(self._getAuthorizationWindow.Destroy)
					return
				#TODO: Bug, this should not be called from a python thread but a wx.Timer (wx.TheClipboard does not function from threads on Linux)
				clipboard = getClipboardText()
				if len(clipboard) == 20:
					if clipboard != lastTriedClipboard and re.match('[a-zA-Z0-9]*', clipboard):
						lastTriedClipboard = clipboard
						self._ym.setAuthToken(clipboard)
			profile.putPreference('youmagine_token', self._ym.getAuthToken())
			wx.CallAfter(self._getAuthorizationWindow.Hide)
			wx.CallAfter(self._getAuthorizationWindow.Destroy)
			wx.MessageBox(_("Cura is now authorized to share on YouMagine"), _("YouMagine."), wx.OK | wx.ICON_INFORMATION)
		wx.CallAfter(self._indicatorWindow.Hide)

		#TODO: Would you like to create a new design or add the model to an existing design?
		wx.CallAfter(self._newDesignWindow.Show)

	def createNewDesign(self, name, description, category, license, imageList, extraFileList, publish):
		thread = threading.Thread(target=self.createNewDesignThread, args=(name, description, category, license, imageList, extraFileList, publish))
		thread.daemon = True
		thread.start()

	def createNewDesignThread(self, name, description, category, license, imageList, extraFileList, publish):
		wx.CallAfter(self._indicatorWindow.showBusy, _("Creating new design on YouMagine..."))
		id = self._ym.createDesign(name, description, category, license)
		wx.CallAfter(self._indicatorWindow.Hide)
		if id is None:
			wx.CallAfter(wx.MessageBox, _("Failed to create a design, nothing uploaded!"), _("YouMagine error."), wx.OK | wx.ICON_ERROR)
			return

		for obj in self._scene.objects():
			wx.CallAfter(self._indicatorWindow.showBusy, _("Building model %s...") % (obj.getName()))
			time.sleep(0.1)
			s = StringIO.StringIO()
			filename = obj.getName()
			if obj.canStoreAsSTL():
				stl.saveSceneStream(s, [obj])
				filename += '.stl'
			else:
				amf.saveSceneStream(s, filename, [obj])
				filename += '.amf'

			wx.CallAfter(self._indicatorWindow.showBusy, _("Uploading model %s...") % (filename))
			if self._ym.createDocument(id, filename, s.getvalue()) is None:
				wx.CallAfter(wx.MessageBox, _("Failed to upload %s!") % (filename), _("YouMagine error."), wx.OK | wx.ICON_ERROR)
			s.close()

		for extra in extraFileList:
			wx.CallAfter(self._indicatorWindow.showBusy, _("Uploading file %s...") % (os.path.basename(extra)))
			with open(extra, "rb") as f:
				if self._ym.createDocument(id, os.path.basename(extra), f.read()) is None:
					wx.CallAfter(wx.MessageBox, _("Failed to upload %s!") % (os.path.basename(extra)), _("YouMagine error."), wx.OK | wx.ICON_ERROR)

		for image in imageList:
			if type(image) in types.StringTypes:
				filename = os.path.basename(image)
				wx.CallAfter(self._indicatorWindow.showBusy, _("Uploading image %s...") % (filename))
				with open(image, "rb") as f:
					if self._ym.createImage(id, filename, f.read()) is None:
						wx.CallAfter(wx.MessageBox, _("Failed to upload %s!") % (filename), _("YouMagine error."), wx.OK | wx.ICON_ERROR)
			elif type(image) is wx.Bitmap:
				s = StringIO.StringIO()
				if wx.ImageFromBitmap(image).SaveStream(s, wx.BITMAP_TYPE_JPEG):
					if self._ym.createImage(id, "snapshot.jpg", s.getvalue()) is None:
						wx.CallAfter(wx.MessageBox, _("Failed to upload snapshot!"), _("YouMagine error."), wx.OK | wx.ICON_ERROR)
			else:
				print type(image)

		if publish:
			wx.CallAfter(self._indicatorWindow.showBusy, _("Publishing design..."))
			if not self._ym.publishDesign(id):
				#If publishing failed try again after 1 second, this might help when you need to wait for the renderer. But does not always work.
				time.sleep(1)
				self._ym.publishDesign(id)
		wx.CallAfter(self._indicatorWindow.Hide)

		webbrowser.open(self._ym.viewUrlForDesign(id))


class workingIndicatorWindow(wx.Frame):
	def __init__(self, parent):
		super(workingIndicatorWindow, self).__init__(parent, title='YouMagine', style=wx.FRAME_TOOL_WINDOW|wx.FRAME_FLOAT_ON_PARENT|wx.FRAME_NO_TASKBAR|wx.CAPTION)
		self._panel = wx.Panel(self)
		self.SetSizer(wx.BoxSizer())
		self.GetSizer().Add(self._panel, 1, wx.EXPAND)

		self._busyBitmaps = [
			wx.Bitmap(getPathForImage('busy-0.png')),
			wx.Bitmap(getPathForImage('busy-1.png')),
			wx.Bitmap(getPathForImage('busy-2.png')),
			wx.Bitmap(getPathForImage('busy-3.png'))
		]

		self._indicatorBitmap = wx.StaticBitmap(self._panel, -1, wx.EmptyBitmapRGBA(24, 24, red=255, green=255, blue=255, alpha=1))
		self._statusText = wx.StaticText(self._panel, -1, '...')
		self._progress = wx.Gauge(self._panel, -1)
		self._progress.SetRange(1000)
		self._progress.SetMinSize((250, 30))

		self._panel._sizer = wx.GridBagSizer(2, 2)
		self._panel.SetSizer(self._panel._sizer)
		self._panel._sizer.Add(self._indicatorBitmap, (0, 0), flag=wx.ALL, border=5)
		self._panel._sizer.Add(self._statusText, (0, 1), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALL, border=5)
		self._panel._sizer.Add(self._progress, (1, 0), span=(1,2), flag=wx.EXPAND|wx.ALL, border=5)

		self._busyState = 0
		self._busyTimer = wx.Timer(self)
		self.Bind(wx.EVT_TIMER, self._busyUpdate, self._busyTimer)
		self._busyTimer.Start(100)

	def _busyUpdate(self, e):
		if self._busyState is None:
			return
		self._busyState += 1
		if self._busyState >= len(self._busyBitmaps):
			self._busyState = 0
		self._indicatorBitmap.SetBitmap(self._busyBitmaps[self._busyState])

	def progress(self, progressAmount):
		wx.CallAfter(self._progress.Show)
		wx.CallAfter(self._progress.SetValue, progressAmount*1000)
		wx.CallAfter(self.Layout)
		wx.CallAfter(self.Fit)

	def showBusy(self, text):
		self._statusText.SetLabel(text)
		self._progress.Hide()
		self.Layout()
		self.Fit()
		self.Centre()
		self.Show()

class getAuthorizationWindow(wx.Frame):
	def __init__(self, parent, ym):
		super(getAuthorizationWindow, self).__init__(parent, title='YouMagine')
		self._panel = wx.Panel(self)
		self.SetSizer(wx.BoxSizer())
		self.GetSizer().Add(self._panel, 1, wx.EXPAND)
		self._ym = ym
		self.abort = False

		self._requestButton = wx.Button(self._panel, -1, _("Request authorization from YouMagine"))
		self._authToken = wx.TextCtrl(self._panel, -1, _("Paste token here"))

		self._panel._sizer = wx.GridBagSizer(5, 5)
		self._panel.SetSizer(self._panel._sizer)

		self._panel._sizer.Add(wx.StaticBitmap(self._panel, -1, wx.Bitmap(getPathForImage('youmagine-text.png'))), (0,0), span=(1,4), flag=wx.ALIGN_CENTRE | wx.ALL, border=5)
		self._panel._sizer.Add(wx.StaticText(self._panel, -1, _("To share your designs on YouMagine\nyou need an account on YouMagine.com\nand authorize Cura to access your account.")), (1, 1))
		self._panel._sizer.Add(self._requestButton, (2, 1), flag=wx.ALL)
		self._panel._sizer.Add(wx.StaticText(self._panel, -1, _("This will open a browser window where you can\nauthorize Cura to access your YouMagine account.\nYou can revoke access at any time\nfrom YouMagine.com")), (3, 1), flag=wx.ALL)
		self._panel._sizer.Add(wx.StaticLine(self._panel, -1), (4,0), span=(1,4), flag=wx.EXPAND | wx.ALL)
		self._panel._sizer.Add(self._authToken, (5, 1), flag=wx.EXPAND | wx.ALL)
		self._panel._sizer.Add(wx.StaticLine(self._panel, -1), (6,0), span=(1,4), flag=wx.EXPAND | wx.ALL)

		self.Bind(wx.EVT_BUTTON, self.OnRequestAuthorization, self._requestButton)
		self.Bind(wx.EVT_TEXT, self.OnEnterToken, self._authToken)
		self.Bind(wx.EVT_CLOSE, self.OnClose)

		self.Fit()
		self.Centre()

		self._authToken.SetFocus()
		self._authToken.SelectAll()

	def OnRequestAuthorization(self, e):
		webbrowser.open(self._ym.getAuthorizationUrl())

	def OnEnterToken(self, e):
		self._ym.setAuthToken(self._authToken.GetValue())

	def OnClose(self, e):
		self.abort = True

class newDesignWindow(wx.Frame):
	def __init__(self, parent, manager, ym):
		super(newDesignWindow, self).__init__(parent, title='Share on YouMagine')
		p = wx.Panel(self)
		self.SetSizer(wx.BoxSizer())
		self.GetSizer().Add(p, 1, wx.EXPAND)
		self._manager = manager
		self._ym = ym

		categoryOptions = ym.getCategories()
		licenseOptions = ym.getLicenses()
		self._designName = wx.TextCtrl(p, -1, _("Design name"))
		self._designDescription = wx.TextCtrl(p, -1, '', size=(1, 150), style = wx.TE_MULTILINE)
		self._designLicense = wx.ComboBox(p, -1, licenseOptions[0], choices=licenseOptions, style=wx.CB_DROPDOWN|wx.CB_READONLY)
		self._category = wx.ComboBox(p, -1, categoryOptions[-1], choices=categoryOptions, style=wx.CB_DROPDOWN|wx.CB_READONLY)
		self._publish = wx.CheckBox(p, -1, _("Publish after upload"))
		self._shareButton = wx.Button(p, -1, _("Share!"))
		self._imageScroll = wx.lib.scrolledpanel.ScrolledPanel(p)
		self._additionalFiles = wx.CheckListBox(p, -1)
		self._additionalFiles.InsertItems(getAdditionalFiles(self._manager._scene.objects(), True), 0)
		self._additionalFiles.SetChecked(range(0, self._additionalFiles.GetCount()))
		self._additionalFiles.InsertItems(getAdditionalFiles(self._manager._scene.objects(), False), self._additionalFiles.GetCount())

		self._imageScroll.SetSizer(wx.BoxSizer(wx.HORIZONTAL))
		self._addImageButton = wx.Button(self._imageScroll, -1, _("Add..."), size=(70,52))
		self._imageScroll.GetSizer().Add(self._addImageButton)
		self._snapshotButton = wx.Button(self._imageScroll, -1, _("Webcam..."), size=(70,52))
		self._imageScroll.GetSizer().Add(self._snapshotButton)
		if not webcam.hasWebcamSupport():
			self._snapshotButton.Hide()
		self._imageScroll.Fit()
		self._imageScroll.SetupScrolling(scroll_x=True, scroll_y=False)
		self._imageScroll.SetMinSize((20, self._imageScroll.GetSize()[1] + wx.SystemSettings_GetMetric(wx.SYS_HSCROLL_Y)))

		self._publish.SetValue(True)
		self._publish.SetToolTipString(
			_("Directly publish the design after uploading.\nWithout this check the design will not be public\nuntil you publish it yourself on YouMagine.com"))

		s = wx.GridBagSizer(5, 5)
		p.SetSizer(s)

		s.Add(wx.StaticBitmap(p, -1, wx.Bitmap(getPathForImage('youmagine-text.png'))), (0,0), span=(1,3), flag=wx.ALIGN_CENTRE | wx.ALL, border=5)
		s.Add(wx.StaticText(p, -1, _("Design name:")), (1, 0), flag=wx.LEFT|wx.TOP, border=5)
		s.Add(self._designName, (1, 1), span=(1,2), flag=wx.EXPAND|wx.LEFT|wx.TOP|wx.RIGHT, border=5)
		s.Add(wx.StaticText(p, -1, _("Description:")), (2, 0), flag=wx.LEFT|wx.TOP, border=5)
		s.Add(self._designDescription, (2, 1), span=(1,2), flag=wx.EXPAND|wx.LEFT|wx.TOP|wx.RIGHT, border=5)
		s.Add(wx.StaticText(p, -1, _("Category:")), (3, 0), flag=wx.LEFT|wx.TOP, border=5)
		s.Add(self._category, (3, 1), span=(1,2), flag=wx.EXPAND|wx.LEFT|wx.TOP|wx.RIGHT, border=5)
		s.Add(wx.StaticText(p, -1, _("License:")), (4, 0), flag=wx.LEFT|wx.TOP, border=5)
		s.Add(self._designLicense, (4, 1), span=(1,2), flag=wx.EXPAND|wx.LEFT|wx.TOP|wx.RIGHT, border=5)
		s.Add(wx.StaticLine(p, -1), (5,0), span=(1,3), flag=wx.EXPAND|wx.ALL)
		s.Add(wx.StaticText(p, -1, _("Images:")), (6, 0), flag=wx.LEFT|wx.TOP, border=5)
		s.Add(self._imageScroll, (6, 1), span=(1, 2), flag=wx.EXPAND|wx.LEFT|wx.TOP|wx.RIGHT, border=5)
		s.Add(wx.StaticLine(p, -1), (7,0), span=(1,3), flag=wx.EXPAND|wx.ALL)
		s.Add(wx.StaticText(p, -1, _("Related design files:")), (8, 0), flag=wx.LEFT|wx.TOP, border=5)

		s.Add(self._additionalFiles, (8, 1), span=(1, 2), flag=wx.EXPAND|wx.LEFT|wx.TOP|wx.RIGHT, border=5)
		s.Add(wx.StaticLine(p, -1), (9,0), span=(1,3), flag=wx.EXPAND|wx.ALL)
		s.Add(self._shareButton, (10, 1), flag=wx.BOTTOM, border=15)
		s.Add(self._publish, (10, 2), flag=wx.BOTTOM|wx.ALIGN_CENTER_VERTICAL, border=15)

		s.AddGrowableRow(2)
		s.AddGrowableCol(2)

		self.Bind(wx.EVT_BUTTON, self.OnShare, self._shareButton)
		self.Bind(wx.EVT_BUTTON, self.OnAddImage, self._addImageButton)
		self.Bind(wx.EVT_BUTTON, self.OnTakeImage, self._snapshotButton)

		self.Fit()
		self.Centre()

		self._designDescription.SetMinSize((1,1))
		self._designName.SetFocus()
		self._designName.SelectAll()

	def OnShare(self, e):
		if self._designName.GetValue() == '':
			wx.MessageBox(_("The name cannot be empty"), _("New design error."), wx.OK | wx.ICON_ERROR)
			self._designName.SetFocus()
			return
		if self._designDescription.GetValue() == '':
			wx.MessageBox(_("The description cannot be empty"), _("New design error."), wx.OK | wx.ICON_ERROR)
			self._designDescription.SetFocus()
			return
		imageList = []
		for child in self._imageScroll.GetChildren():
			if hasattr(child, 'imageFilename'):
				imageList.append(child.imageFilename)
			if hasattr(child, 'imageData'):
				imageList.append(child.imageData)
		self._manager.createNewDesign(self._designName.GetValue(), self._designDescription.GetValue(), self._category.GetValue(), self._designLicense.GetValue(), imageList, self._additionalFiles.GetCheckedStrings(), self._publish.GetValue())
		self.Destroy()

	def OnAddImage(self, e):
		dlg=wx.FileDialog(self, "Select image file...", style=wx.FD_OPEN|wx.FD_FILE_MUST_EXIST|wx.FD_MULTIPLE)
		dlg.SetWildcard("Image files (*.jpg,*.jpeg,*.png)|*.jpg;*.jpeg;*.png")
		if dlg.ShowModal() == wx.ID_OK:
			for filename in dlg.GetPaths():
				self._addImage(filename)
		dlg.Destroy()

	def OnTakeImage(self, e):
		w = webcamPhotoWindow(self)
		if w.hasCamera():
			w.Show()
		else:
			w.Destroy()
			wx.MessageBox(_("No webcam found on your system"), _("Webcam error"), wx.OK | wx.ICON_ERROR)

	def _addImage(self, image):
		wxImage = None
		if type(image) in types.StringTypes:
			try:
				wxImage = wx.ImageFromBitmap(wx.Bitmap(image))
			except:
				pass
		else:
			wxImage = wx.ImageFromBitmap(image)
		if wxImage is None:
			return

		width, height = wxImage.GetSize()
		if width > 70:
			height = height*70/width
			width = 70
		if height > 52:
			width = width*52/height
			height = 52
		wxImage.Rescale(width, height, wx.IMAGE_QUALITY_NORMAL)
		wxImage.Resize((70, 52), ((70-width)/2, (52-height)/2))
		ctrl = wx.StaticBitmap(self._imageScroll, -1, wx.BitmapFromImage(wxImage))
		if type(image) in types.StringTypes:
			ctrl.imageFilename = image
		else:
			ctrl.imageData = image

		delButton = wx.Button(ctrl, -1, 'X', style=wx.BU_EXACTFIT)
		self.Bind(wx.EVT_BUTTON, self.OnDeleteImage, delButton)

		self._imageScroll.GetSizer().Insert(len(self._imageScroll.GetChildren())-3, ctrl)
		self._imageScroll.Layout()
		self._imageScroll.Refresh()
		self._imageScroll.SetupScrolling(scroll_x=True, scroll_y=False)

	def OnDeleteImage(self, e):
		ctrl = e.GetEventObject().GetParent()
		self._imageScroll.GetSizer().Detach(ctrl)
		ctrl.Destroy()

		self._imageScroll.Layout()
		self._imageScroll.Refresh()
		self._imageScroll.SetupScrolling(scroll_x=True, scroll_y=False)

class webcamPhotoWindow(wx.Frame):
	def __init__(self, parent):
		super(webcamPhotoWindow, self).__init__(parent, title='YouMagine')
		p = wx.Panel(self)
		self.panel = p
		self.SetSizer(wx.BoxSizer())
		self.GetSizer().Add(p, 1, wx.EXPAND)

		self._cam = webcam.webcam()
		self._cam.takeNewImage(False)

		s = wx.GridBagSizer(3, 3)
		p.SetSizer(s)

		self._preview = wx.Panel(p)
		self._cameraSelect = wx.ComboBox(p, -1, self._cam.listCameras()[0], choices=self._cam.listCameras(), style=wx.CB_DROPDOWN|wx.CB_READONLY)
		self._takeImageButton = wx.Button(p, -1, 'Snap image')
		self._takeImageTimer = wx.Timer(self)

		s.Add(self._takeImageButton, pos=(1, 0), flag=wx.ALL, border=5)
		s.Add(self._cameraSelect, pos=(1, 1), flag=wx.ALL, border=5)
		s.Add(self._preview, pos=(0, 0), span=(1, 2), flag=wx.EXPAND|wx.ALL, border=5)

		if self._cam.getLastImage() is not None:
			self._preview.SetMinSize((self._cam.getLastImage().GetWidth(), self._cam.getLastImage().GetHeight()))
		else:
			self._preview.SetMinSize((640, 480))

		self._preview.Bind(wx.EVT_ERASE_BACKGROUND, self.OnCameraEraseBackground)
		self.Bind(wx.EVT_BUTTON, self.OnTakeImage, self._takeImageButton)
		self.Bind(wx.EVT_TIMER, self.OnTakeImageTimer, self._takeImageTimer)
		self.Bind(wx.EVT_COMBOBOX, self.OnCameraChange, self._cameraSelect)

		self.Fit()
		self.Centre()

		self._takeImageTimer.Start(200)

	def hasCamera(self):
		return self._cam.hasCamera()

	def OnCameraChange(self, e):
		self._cam.setActiveCamera(self._cameraSelect.GetSelection())

	def OnTakeImage(self, e):
		self.GetParent()._addImage(self._cam.getLastImage())
		self.Destroy()

	def OnTakeImageTimer(self, e):
		self._cam.takeNewImage(False)
		self.Refresh()

	def OnCameraEraseBackground(self, e):
		dc = e.GetDC()
		if not dc:
			dc = wx.ClientDC(self)
			rect = self.GetUpdateRegion().GetBox()
			dc.SetClippingRect(rect)
		dc.SetBackground(wx.Brush(self._preview.GetBackgroundColour(), wx.SOLID))
		if self._cam.getLastImage() is not None:
			self._preview.SetMinSize((self._cam.getLastImage().GetWidth(), self._cam.getLastImage().GetHeight()))
			self.panel.Fit()
			dc.DrawBitmap(self._cam.getLastImage(), 0, 0)
		else:
			dc.Clear()

########NEW FILE########
__FILENAME__ = dropTarget
__copyright__ = "Copyright (C) 2013 David Braam - Released under terms of the AGPLv3 License"

import wx

# Define File Drop Target class
class FileDropTarget(wx.FileDropTarget):
	def __init__(self, callback, filenameFilter = None):
		super(FileDropTarget, self).__init__()
		self.callback = callback
		self.filenameFilter = filenameFilter

	def OnDropFiles(self, x, y, files):
		filteredList = []
		if self.filenameFilter is not None:
			for f in files:
				for ext in self.filenameFilter:
					if f.endswith(ext) or f.endswith(ext.upper()):
						filteredList.append(f)
		else:
			filteredList = files
		if len(filteredList) > 0:
			self.callback(filteredList)


########NEW FILE########
__FILENAME__ = engineResultView
__copyright__ = "Copyright (C) 2013 David Braam - Released under terms of the AGPLv3 License"

import wx
import numpy
import math
import threading

import OpenGL
OpenGL.ERROR_CHECKING = False
from OpenGL.GLU import *
from OpenGL.GL import *

from Cura.util import profile
from Cura.gui.util import openglHelpers
from Cura.gui.util import openglGui

class engineResultView(object):
	def __init__(self, parent):
		self._parent = parent
		self._result = None
		self._enabled = False
		self._gcodeLoadProgress = 0
		self._resultLock = threading.Lock()
		self._layerVBOs = []
		self._layer20VBOs = []

		self.layerSelect = openglGui.glSlider(self._parent, 10000, 0, 1, (-1,-2), lambda : self._parent.QueueRefresh())

	def setResult(self, result):
		if self._result == result:
			return
		if result is None:
			self.setEnabled(False)

		self._resultLock.acquire()
		self._result = result

		#Clean the saved VBO's
		for layer in self._layerVBOs:
			for typeName in layer.keys():
				self._parent.glReleaseList.append(layer[typeName])
		for layer in self._layer20VBOs:
			for typeName in layer.keys():
				self._parent.glReleaseList.append(layer[typeName])
		self._layerVBOs = []
		self._layer20VBOs = []
		self._resultLock.release()

	def setEnabled(self, enabled):
		self._enabled = enabled
		self.layerSelect.setHidden(not enabled)

	def _gcodeLoadCallback(self, result, progress):
		if result != self._result:
			#Abort loading from this thread.
			return True
		self._gcodeLoadProgress = progress
		self._parent._queueRefresh()
		return False

	def OnDraw(self):
		if not self._enabled:
			return

		self._resultLock.acquire()
		result = self._result
		if result is not None:
			gcodeLayers = result.getGCodeLayers(self._gcodeLoadCallback)
			if result._polygons is not None and len(result._polygons) > 0:
				self.layerSelect.setRange(1, len(result._polygons))
			elif gcodeLayers is not None and len(gcodeLayers) > 0:
				self.layerSelect.setRange(1, len(gcodeLayers))
		else:
			gcodeLayers = None

		glPushMatrix()
		glEnable(GL_BLEND)
		if profile.getMachineSetting('machine_center_is_zero') != 'True':
			glTranslate(-profile.getMachineSettingFloat('machine_width') / 2, -profile.getMachineSettingFloat('machine_depth') / 2, 0)
		glLineWidth(2)

		layerNr = self.layerSelect.getValue()
		if layerNr == self.layerSelect.getMaxValue() and result is not None and len(result._polygons) > 0:
			layerNr = max(layerNr, len(result._polygons))
		if len(result._polygons) > layerNr-1 and 'inset0' in result._polygons[layerNr-1] and len(result._polygons[layerNr-1]['inset0']) > 0 and len(result._polygons[layerNr-1]['inset0'][0]) > 0:
			viewZ = result._polygons[layerNr-1]['inset0'][0][0][2]
		else:
			viewZ = (layerNr - 1) * profile.getProfileSettingFloat('layer_height') + profile.getProfileSettingFloat('bottom_thickness')
		self._parent._viewTarget[2] = viewZ
		msize = max(profile.getMachineSettingFloat('machine_width'), profile.getMachineSettingFloat('machine_depth'))
		lineTypeList = [
			('inset0',     'WALL-OUTER', [1,0,0,1]),
			('insetx',     'WALL-INNER', [0,1,0,1]),
			('openoutline', None,        [1,0,0,1]),
			('skin',       'FILL',       [1,1,0,1]),
			('infill',      None,        [1,1,0,1]),
			('support',    'SUPPORT',    [0,1,1,1]),
			('skirt',      'SKIRT',      [0,1,1,1]),
			('outline',     None,        [0,0,0,1])
		]
		n = layerNr - 1
		generatedVBO = False
		if result is not None:
			while n >= 0:
				if layerNr - n > 30 and n % 20 == 0 and len(result._polygons) > 0:
					idx = n / 20
					while len(self._layer20VBOs) < idx + 1:
						self._layer20VBOs.append({})
					if result._polygons is not None and n + 20 < len(result._polygons):
						layerVBOs = self._layer20VBOs[idx]
						for typeName, typeNameGCode, color in lineTypeList:
							allow = typeName in result._polygons[n + 19]
							if typeName == 'skirt':
								for i in xrange(0, 20):
									if typeName in result._polygons[n + i]:
										allow = True
							if allow:
								if typeName not in layerVBOs:
									if generatedVBO:
										continue
									polygons = []
									for i in xrange(0, 20):
										if typeName in result._polygons[n + i]:
											polygons += result._polygons[n + i][typeName]
									layerVBOs[typeName] = self._polygonsToVBO_lines(polygons)
									generatedVBO = True
								glColor4f(color[0]*0.5,color[1]*0.5,color[2]*0.5,color[3])
								layerVBOs[typeName].render()
					n -= 20
				else:
					c = 1.0 - ((layerNr - n) - 1) * 0.05
					c = max(0.5, c)
					while len(self._layerVBOs) < n + 1:
						self._layerVBOs.append({})
					layerVBOs = self._layerVBOs[n]
					if gcodeLayers is not None and ((layerNr - 10 < n < (len(gcodeLayers) - 1)) or len(result._polygons) < 1):
						for typeNamePolygons, typeName, color in lineTypeList:
							if typeName is None:
								continue
							if 'GCODE-' + typeName not in layerVBOs:
								layerVBOs['GCODE-' + typeName] = self._gcodeToVBO_quads(gcodeLayers[n+1:n+2], typeName)
							glColor4f(color[0]*c,color[1]*c,color[2]*c,color[3])
							layerVBOs['GCODE-' + typeName].render()

						if n == layerNr - 1:
							if 'GCODE-MOVE' not in layerVBOs:
								layerVBOs['GCODE-MOVE'] = self._gcodeToVBO_lines(gcodeLayers[n+1:n+2])
							glColor4f(0,0,c,1)
							layerVBOs['GCODE-MOVE'].render()
					elif n < len(result._polygons):
						polygons = result._polygons[n]
						for typeName, typeNameGCode, color in lineTypeList:
							if typeName in polygons:
								if typeName not in layerVBOs:
									layerVBOs[typeName] = self._polygonsToVBO_lines(polygons[typeName])
								glColor4f(color[0]*c,color[1]*c,color[2]*c,color[3])
								layerVBOs[typeName].render()
					n -= 1
		glPopMatrix()
		if generatedVBO:
			self._parent._queueRefresh()

		if gcodeLayers is not None and self._gcodeLoadProgress != 0.0 and self._gcodeLoadProgress != 1.0:
			glPushMatrix()
			glLoadIdentity()
			glTranslate(0,-0.8,-2)
			glColor4ub(60,60,60,255)
			openglHelpers.glDrawStringCenter(_("Loading toolpath for visualization (%d%%)") % (self._gcodeLoadProgress * 100))
			glPopMatrix()
		self._resultLock.release()

	def _polygonsToVBO_lines(self, polygons):
		verts = numpy.zeros((0, 3), numpy.float32)
		indices = numpy.zeros((0), numpy.uint32)
		for poly in polygons:
			if len(poly) > 2:
				i = numpy.arange(len(verts), len(verts) + len(poly) + 1, 1, numpy.uint32)
				i[-1] = len(verts)
				i = numpy.dstack((i[0:-1],i[1:])).flatten()
			else:
				i = numpy.arange(len(verts), len(verts) + len(poly), 1, numpy.uint32)
			indices = numpy.concatenate((indices, i), 0)
			verts = numpy.concatenate((verts, poly), 0)
		return openglHelpers.GLVBO(GL_LINES, verts, indicesArray=indices)

	def _polygonsToVBO_quads(self, polygons):
		verts = numpy.zeros((0, 3), numpy.float32)
		indices = numpy.zeros((0), numpy.uint32)
		for poly in polygons:
			i = numpy.arange(len(verts), len(verts) + len(poly) + 1, 1, numpy.uint32)
			i2 = numpy.arange(len(verts) + len(poly), len(verts) + len(poly) + len(poly) + 1, 1, numpy.uint32)
			i[-1] = len(verts)
			i2[-1] = len(verts) + len(poly)
			i = numpy.dstack((i[0:-1],i2[0:-1],i2[1:],i[1:])).flatten()
			indices = numpy.concatenate((indices, i), 0)
			verts = numpy.concatenate((verts, poly), 0)
			verts = numpy.concatenate((verts, poly * numpy.array([1,0,1],numpy.float32) + numpy.array([0,-100,0],numpy.float32)), 0)
		return openglHelpers.GLVBO(GL_QUADS, verts, indicesArray=indices)

	def _gcodeToVBO_lines(self, gcodeLayers, extrudeType):
		if ':' in extrudeType:
			extruder = int(extrudeType[extrudeType.find(':')+1:])
			extrudeType = extrudeType[0:extrudeType.find(':')]
		else:
			extruder = None
		verts = numpy.zeros((0, 3), numpy.float32)
		indices = numpy.zeros((0), numpy.uint32)
		for layer in gcodeLayers:
			for path in layer:
				if path['type'] == 'extrude' and path['pathType'] == extrudeType and (extruder is None or path['extruder'] == extruder):
					i = numpy.arange(len(verts), len(verts) + len(path['points']), 1, numpy.uint32)
					i = numpy.dstack((i[0:-1],i[1:])).flatten()
					indices = numpy.concatenate((indices, i), 0)
					verts = numpy.concatenate((verts, path['points']))
		return openglHelpers.GLVBO(GL_LINES, verts, indicesArray=indices)

	def _gcodeToVBO_quads(self, gcodeLayers, extrudeType):
		useFilamentArea = profile.getMachineSetting('gcode_flavor') == 'UltiGCode'
		filamentRadius = profile.getProfileSettingFloat('filament_diameter') / 2
		filamentArea = math.pi * filamentRadius * filamentRadius

		if ':' in extrudeType:
			extruder = int(extrudeType[extrudeType.find(':')+1:])
			extrudeType = extrudeType[0:extrudeType.find(':')]
		else:
			extruder = None

		verts = numpy.zeros((0, 3), numpy.float32)
		indices = numpy.zeros((0), numpy.uint32)
		for layer in gcodeLayers:
			for path in layer:
				if path['type'] == 'extrude' and path['pathType'] == extrudeType and (extruder is None or path['extruder'] == extruder):
					a = path['points']
					if extrudeType == 'FILL':
						a[:,2] += 0.01

					#Construct the normals of each line 90deg rotated on the X/Y plane
					normals = a[1:] - a[:-1]
					lengths = numpy.sqrt(normals[:,0]**2 + normals[:,1]**2)
					normals[:,0], normals[:,1] = -normals[:,1] / lengths, normals[:,0] / lengths
					normals[:,2] /= lengths

					ePerDist = path['extrusion'][1:] / lengths
					if useFilamentArea:
						lineWidth = ePerDist / path['layerThickness'] / 2.0
					else:
						lineWidth = ePerDist * (filamentArea / path['layerThickness'] / 2)

					normals[:,0] *= lineWidth
					normals[:,1] *= lineWidth

					b = numpy.zeros((len(a)-1, 0), numpy.float32)
					b = numpy.concatenate((b, a[1:] + normals), 1)
					b = numpy.concatenate((b, a[1:] - normals), 1)
					b = numpy.concatenate((b, a[:-1] - normals), 1)
					b = numpy.concatenate((b, a[:-1] + normals), 1)
					b = b.reshape((len(b) * 4, 3))

					i = numpy.arange(len(verts), len(verts) + len(b), 1, numpy.uint32)

					verts = numpy.concatenate((verts, b))
					indices = numpy.concatenate((indices, i))
		return openglHelpers.GLVBO(GL_QUADS, verts, indicesArray=indices)

	def _gcodeToVBO_lines(self, gcodeLayers):
		verts = numpy.zeros((0,3), numpy.float32)
		indices = numpy.zeros((0), numpy.uint32)
		for layer in gcodeLayers:
			for path in layer:
				if path['type'] == 'move':
					a = path['points'] + numpy.array([0,0,0.02], numpy.float32)
					i = numpy.arange(len(verts), len(verts) + len(a), 1, numpy.uint32)
					i = numpy.dstack((i[0:-1],i[1:])).flatten()
					verts = numpy.concatenate((verts, a))
					indices = numpy.concatenate((indices, i))
				if path['type'] == 'retract':
					a = path['points'] + numpy.array([0,0,0.02], numpy.float32)
					a = numpy.concatenate((a[:-1], a[1:] + numpy.array([0,0,1], numpy.float32)), 1)
					a = a.reshape((len(a) * 2, 3))
					i = numpy.arange(len(verts), len(verts) + len(a), 1, numpy.uint32)
					verts = numpy.concatenate((verts, a))
					indices = numpy.concatenate((indices, i))
		return openglHelpers.GLVBO(GL_LINES, verts, indicesArray=indices)

	def OnKeyChar(self, keyCode):
		if not self._enabled:
			return
		#TODO: This is strange behaviour. Overloaded functionality of keyboard buttons!
		if wx.GetKeyState(wx.WXK_SHIFT) or wx.GetKeyState(wx.WXK_CONTROL):
			if keyCode == wx.WXK_UP:
				self.layerSelect.setValue(self.layerSelect.getValue() + 1)
				self._parent.QueueRefresh()
				return True
			elif keyCode == wx.WXK_DOWN:
				self.layerSelect.setValue(self.layerSelect.getValue() - 1)
				self._parent.QueueRefresh()
				return True
			elif keyCode == wx.WXK_PAGEUP:
				self.layerSelect.setValue(self.layerSelect.getValue() + 10)
				self._parent.QueueRefresh()
				return True
			elif keyCode == wx.WXK_PAGEDOWN:
				self.layerSelect.setValue(self.layerSelect.getValue() - 10)
				self._parent.QueueRefresh()
				return True
		return False

########NEW FILE########
__FILENAME__ = gcodeTextArea
__copyright__ = "Copyright (C) 2013 David Braam - Released under terms of the AGPLv3 License"

import wx
import wx.stc
import sys

from Cura.util import profile

class GcodeTextArea(wx.stc.StyledTextCtrl):
	def __init__(self, parent):
		super(GcodeTextArea, self).__init__(parent)

		self.SetLexer(wx.stc.STC_LEX_CONTAINER)
		self.Bind(wx.stc.EVT_STC_STYLENEEDED, self.OnStyle)
	
		fontSize = wx.SystemSettings.GetFont(wx.SYS_ANSI_VAR_FONT).GetPointSize()
		fontName = wx.Font(wx.SystemSettings.GetFont(wx.SYS_ANSI_VAR_FONT).GetPointSize(), wx.FONTFAMILY_MODERN, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL).GetFaceName()
		self.SetStyleBits(5)
		self.StyleSetSpec(0, "face:%s,size:%d" % (fontName, fontSize))
		self.StyleSetSpec(1, "fore:#006000,face:%s,size:%d" % (fontName, fontSize))
		self.IndicatorSetStyle(0, wx.stc.STC_INDIC_TT)
		self.IndicatorSetForeground(0, "#0000FF")
		self.IndicatorSetStyle(1, wx.stc.STC_INDIC_SQUIGGLE)
		self.IndicatorSetForeground(1, "#FF0000")
		self.SetWrapMode(wx.stc.STC_WRAP_NONE)
		self.SetScrollWidth(1000)
		if sys.platform == 'darwin':
			self.Bind(wx.EVT_KEY_DOWN, self.OnMacKeyDown)
	
		#GCodes and MCodes as supported by Marlin
		#GCode 21 is not really supported by Marlin, but we still do not report it as error as it's often used.
		self.supportedGCodes = [0,1,2,3,4,21,28,90,91,92]
		self.supportedMCodes = [17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,42,80,81,82,83,84,85,92,104,105,106,107,109,114,115,117,119,140,190,201,202,203,204,205,206,220,221,240,301,302,303,400,500,501,502,503,999]
	
	def OnMacKeyDown(self, e):
		code = e.GetKeyCode();
		stopPropagation = True
		#Command
		if e.CmdDown():
			if code == wx._core.WXK_LEFT:
				self.GotoLine(self.GetCurrentLine())
			elif code == wx._core.WXK_RIGHT:
				self.GotoPos(self.GetLineEndPosition(self.GetCurrentLine()))
			elif code == wx._core.WXK_UP:
				self.GotoPos(0)
			elif code == wx._core.WXK_DOWN:
				self.GotoPos(self.GetLength())
			else:
				stopPropagation = False
		# Control
		elif e.GetModifiers() & 0xF0:
			if code == 65: # A
				self.GotoLine(self.GetCurrentLine())
			elif code == 69: # E
				self.GotoPos(self.GetLineEndPosition(self.GetCurrentLine()))
			else:
				stopPropagation = False
		else:
			stopPropagation = False
		# Event propagation
		if stopPropagation:
			e.StopPropagation()
		else:
			e.Skip()
	
	def OnStyle(self, e):
		lineNr = self.LineFromPosition(self.GetEndStyled())
		while self.PositionFromLine(lineNr) > -1:
			line = self.GetLine(lineNr)
			start = self.PositionFromLine(lineNr)
			length = self.LineLength(lineNr)
			self.StartStyling(start, 255)
			self.SetStyling(length, 0)
			if ';' in line:
				pos = line.index(';')
				self.StartStyling(start + pos, 31)
				self.SetStyling(length - pos, 1)
				length = pos
		
			pos = 0
			while pos < length:
				if line[pos] in " \t\n\r":
					while pos < length and line[pos] in " \t\n\r":
						pos += 1
				else:
					end = pos
					while end < length and not line[end] in " \t\n\r":
						end += 1
					if self.checkGCodePart(line[pos:end], start + pos):
						self.StartStyling(start + pos, 0x20)
						self.SetStyling(end - pos, 0x20)
					pos = end
			lineNr += 1

	def checkGCodePart(self, part, pos):
		if len(part) < 2:
			self.StartStyling(pos, 0x40)
			self.SetStyling(1, 0x40)
			return True
		if not part[0] in "GMXYZFESTBPIDCJ":
			self.StartStyling(pos, 0x40)
			self.SetStyling(1, 0x40)
			return True
		if part[1] == '{':
			if part[-1] != '}':
				return True
			tag = part[2:-1]
			if not profile.isProfileSetting(tag) and not profile.isPreference(tag):
				self.StartStyling(pos + 2, 0x40)
				self.SetStyling(len(tag), 0x40)
				return True
		elif part[0] in "GM":
			try:
				code = int(part[1:])
			except (ValueError):
				self.StartStyling(pos + 1, 0x40)
				self.SetStyling(len(part) - 1, 0x40)
				return True
			if part[0] == 'G':
				if not code in self.supportedGCodes:
					return True
			if part[0] == 'M':
				if not code in self.supportedMCodes:
					return True
		else:
			try:
				float(part[1:])
			except (ValueError):
				self.StartStyling(pos + 1, 0x40)
				self.SetStyling(len(part) - 1, 0x40)
				return True
		return False

	def GetValue(self):
		return self.GetText()

	def SetValue(self, s):
		self.SetText(s)


########NEW FILE########
__FILENAME__ = openglGui
from __future__ import division
__copyright__ = "Copyright (C) 2013 David Braam - Released under terms of the AGPLv3 License"

import wx
import traceback
import sys
import os
import time

from wx import glcanvas
import OpenGL
OpenGL.ERROR_CHECKING = False
from OpenGL.GL import *

from Cura.util import version
from Cura.gui.util import openglHelpers

class animation(object):
	def __init__(self, gui, start, end, runTime):
		self._start = start
		self._end = end
		self._startTime = time.time()
		self._runTime = runTime
		gui._animationList.append(self)

	def isDone(self):
		return time.time() > self._startTime + self._runTime

	def getPosition(self):
		if self.isDone():
			return self._end
		f = (time.time() - self._startTime) / self._runTime
		ts = f*f
		tc = f*f*f
		#f = 6*tc*ts + -15*ts*ts + 10*tc
		f = tc + -3*ts + 3*f
		return self._start + (self._end - self._start) * f

class glGuiControl(object):
	def __init__(self, parent, pos):
		self._parent = parent
		self._base = parent._base
		self._pos = pos
		self._size = (0,0, 1, 1)
		self._parent.add(self)

	def setSize(self, x, y, w, h):
		self._size = (x, y, w, h)

	def getSize(self):
		return self._size

	def getMinSize(self):
		return 1, 1

	def updateLayout(self):
		pass

	def focusNext(self):
		for n in xrange(self._parent._glGuiControlList.index(self) + 1, len(self._parent._glGuiControlList)):
			if self._parent._glGuiControlList[n].setFocus():
				return
		for n in xrange(0, self._parent._glGuiControlList.index(self)):
			if self._parent._glGuiControlList[n].setFocus():
				return

	def focusPrevious(self):
		for n in xrange(self._parent._glGuiControlList.index(self) -1, -1, -1):
			if self._parent._glGuiControlList[n].setFocus():
				return
		for n in xrange(len(self._parent._glGuiControlList) - 1, self._parent._glGuiControlList.index(self), -1):
			if self._parent._glGuiControlList[n].setFocus():
				return

	def setFocus(self):
		return False

	def hasFocus(self):
		return self._base._focus == self

	def OnMouseUp(self, x, y):
		pass

	def OnKeyChar(self, key):
		pass

class glGuiContainer(glGuiControl):
	def __init__(self, parent, pos):
		self._glGuiControlList = []
		glGuiLayoutButtons(self)
		super(glGuiContainer, self).__init__(parent, pos)

	def add(self, ctrl):
		self._glGuiControlList.append(ctrl)
		self.updateLayout()

	def OnMouseDown(self, x, y, button):
		for ctrl in self._glGuiControlList:
			if ctrl.OnMouseDown(x, y, button):
				return True
		return False

	def OnMouseUp(self, x, y):
		for ctrl in self._glGuiControlList:
			if ctrl.OnMouseUp(x, y):
				return True
		return False

	def OnMouseMotion(self, x, y):
		handled = False
		for ctrl in self._glGuiControlList:
			if ctrl.OnMouseMotion(x, y):
				handled = True
		return handled

	def draw(self):
		for ctrl in self._glGuiControlList:
			ctrl.draw()

	def updateLayout(self):
		self._layout.update()
		for ctrl in self._glGuiControlList:
			ctrl.updateLayout()

class glGuiPanel(glcanvas.GLCanvas):
	def __init__(self, parent):
		attribList = (glcanvas.WX_GL_RGBA, glcanvas.WX_GL_DOUBLEBUFFER, glcanvas.WX_GL_DEPTH_SIZE, 24, glcanvas.WX_GL_STENCIL_SIZE, 8, 0)
		glcanvas.GLCanvas.__init__(self, parent, style=wx.WANTS_CHARS, attribList = attribList)
		self._base = self
		self._focus = None
		self._container = None
		self._container = glGuiContainer(self, (0,0))
		self._shownError = False

		self._context = glcanvas.GLContext(self)
		self._glButtonsTexture = None
		self._glRobotTexture = None
		self._buttonSize = 64

		self._animationList = []
		self.glReleaseList = []
		self._refreshQueued = False
		self._idleCalled = False

		wx.EVT_PAINT(self, self._OnGuiPaint)
		wx.EVT_SIZE(self, self._OnSize)
		wx.EVT_ERASE_BACKGROUND(self, self._OnEraseBackground)
		wx.EVT_LEFT_DOWN(self, self._OnGuiMouseDown)
		wx.EVT_LEFT_DCLICK(self, self._OnGuiMouseDown)
		wx.EVT_LEFT_UP(self, self._OnGuiMouseUp)
		wx.EVT_RIGHT_DOWN(self, self._OnGuiMouseDown)
		wx.EVT_RIGHT_DCLICK(self, self._OnGuiMouseDown)
		wx.EVT_RIGHT_UP(self, self._OnGuiMouseUp)
		wx.EVT_MIDDLE_DOWN(self, self._OnGuiMouseDown)
		wx.EVT_MIDDLE_DCLICK(self, self._OnGuiMouseDown)
		wx.EVT_MIDDLE_UP(self, self._OnGuiMouseUp)
		wx.EVT_MOTION(self, self._OnGuiMouseMotion)
		wx.EVT_CHAR(self, self._OnGuiKeyChar)
		wx.EVT_KILL_FOCUS(self, self.OnFocusLost)
		wx.EVT_IDLE(self, self._OnIdle)

	def _OnIdle(self, e):
		self._idleCalled = True
		if len(self._animationList) > 0 or self._refreshQueued:
			self._refreshQueued = False
			for anim in self._animationList:
				if anim.isDone():
					self._animationList.remove(anim)
			self.Refresh()

	def _OnGuiKeyChar(self, e):
		if self._focus is not None:
			self._focus.OnKeyChar(e.GetKeyCode())
			self.Refresh()
		else:
			self.OnKeyChar(e.GetKeyCode())

	def OnFocusLost(self, e):
		self._focus = None
		self.Refresh()

	def _OnGuiMouseDown(self,e):
		self.SetFocus()
		if self._container.OnMouseDown(e.GetX(), e.GetY(), e.GetButton()):
			self.Refresh()
			return
		self.OnMouseDown(e)

	def _OnGuiMouseUp(self, e):
		if self._container.OnMouseUp(e.GetX(), e.GetY()):
			self.Refresh()
			return
		self.OnMouseUp(e)

	def _OnGuiMouseMotion(self,e):
		self.Refresh()
		if not self._container.OnMouseMotion(e.GetX(), e.GetY()):
			self.OnMouseMotion(e)

	def _OnGuiPaint(self, e):
		self._idleCalled = False
		h = self.GetSize().GetHeight()
		w = self.GetSize().GetWidth()
		oldButtonSize = self._buttonSize
		if h / 3 < w / 4:
			w = h * 4 / 3
		if w < 64 * 8:
			self._buttonSize = 32
		elif w < 64 * 10:
			self._buttonSize = 48
		elif w < 64 * 15:
			self._buttonSize = 64
		elif w < 64 * 20:
			self._buttonSize = 80
		else:
			self._buttonSize = 96
		if self._buttonSize != oldButtonSize:
			self._container.updateLayout()

		dc = wx.PaintDC(self)
		try:
			self.SetCurrent(self._context)
			for obj in self.glReleaseList:
				obj.release()
			del self.glReleaseList[:]
			renderStartTime = time.time()
			self.OnPaint(e)
			self._drawGui()
			glFlush()
			if version.isDevVersion():
				renderTime = time.time() - renderStartTime
				if renderTime == 0:
					renderTime = 0.001
				glLoadIdentity()
				glTranslate(10, self.GetSize().GetHeight() - 30, -1)
				glColor4f(0.2,0.2,0.2,0.5)
				openglHelpers.glDrawStringLeft("fps:%d" % (1 / renderTime))
			self.SwapBuffers()
		except:
			# When an exception happens, catch it and show a message box. If the exception is not caught the draw function bugs out.
			# Only show this exception once so we do not overload the user with popups.
			errStr = _("An error has occurred during the 3D view drawing.")
			tb = traceback.extract_tb(sys.exc_info()[2])
			errStr += "\n%s: '%s'" % (str(sys.exc_info()[0].__name__), str(sys.exc_info()[1]))
			for n in xrange(len(tb)-1, -1, -1):
				locationInfo = tb[n]
				errStr += "\n @ %s:%s:%d" % (os.path.basename(locationInfo[0]), locationInfo[2], locationInfo[1])
			if not self._shownError:
				traceback.print_exc()
				wx.CallAfter(wx.MessageBox, errStr, _("3D window error"), wx.OK | wx.ICON_EXCLAMATION)
				self._shownError = True

	def _drawGui(self):
		if self._glButtonsTexture is None:
			self._glButtonsTexture = openglHelpers.loadGLTexture('glButtons.png')
			self._glRobotTexture = openglHelpers.loadGLTexture('UltimakerRobot.png')

		glDisable(GL_DEPTH_TEST)
		glEnable(GL_BLEND)
		glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
		glDisable(GL_LIGHTING)
		glColor4ub(255,255,255,255)

		glMatrixMode(GL_PROJECTION)
		glLoadIdentity()
		size = self.GetSize()
		glOrtho(0, size.GetWidth()-1, size.GetHeight()-1, 0, -1000.0, 1000.0)
		glMatrixMode(GL_MODELVIEW)
		glLoadIdentity()

		self._container.draw()

		# glBindTexture(GL_TEXTURE_2D, self._glRobotTexture)
		# glEnable(GL_TEXTURE_2D)
		# glPushMatrix()
		# glColor4f(1,1,1,1)
		# glTranslate(size.GetWidth(),size.GetHeight(),0)
		# s = self._buttonSize * 1
		# glScale(s,s,s)
		# glTranslate(-1.2,-0.2,0)
		# glBegin(GL_QUADS)
		# glTexCoord2f(1, 0)
		# glVertex2f(0,-1)
		# glTexCoord2f(0, 0)
		# glVertex2f(-1,-1)
		# glTexCoord2f(0, 1)
		# glVertex2f(-1, 0)
		# glTexCoord2f(1, 1)
		# glVertex2f(0, 0)
		# glEnd()
		# glDisable(GL_TEXTURE_2D)
		# glPopMatrix()

	def _OnEraseBackground(self,event):
		#Workaround for windows background redraw flicker.
		pass

	def _OnSize(self,e):
		self._container.setSize(0, 0, self.GetSize().GetWidth(), self.GetSize().GetHeight())
		self._container.updateLayout()
		self.Refresh()

	def OnMouseDown(self,e):
		pass
	def OnMouseUp(self,e):
		pass
	def OnMouseMotion(self, e):
		pass
	def OnKeyChar(self, keyCode):
		pass
	def OnPaint(self, e):
		pass
	def OnKeyChar(self, keycode):
		pass

	def QueueRefresh(self):
		wx.CallAfter(self._queueRefresh)

	def _queueRefresh(self):
		if self._idleCalled:
			wx.CallAfter(self.Refresh)
		else:
			self._refreshQueued = True

	def add(self, ctrl):
		if self._container is not None:
			self._container.add(ctrl)

class glGuiLayoutButtons(object):
	def __init__(self, parent):
		self._parent = parent
		self._parent._layout = self

	def update(self):
		bs = self._parent._base._buttonSize
		x0, y0, w, h = self._parent.getSize()
		gridSize = bs * 1.0
		for ctrl in self._parent._glGuiControlList:
			pos = ctrl._pos
			if pos[0] < 0:
				x = w + pos[0] * gridSize - bs * 0.2
			else:
				x = pos[0] * gridSize + bs * 0.2
			if pos[1] < 0:
				y = h + pos[1] * gridSize * 1.2 - bs * 0.0
			else:
				y = pos[1] * gridSize * 1.2 + bs * 0.2
			ctrl.setSize(x, y, gridSize, gridSize)

	def getLayoutSize(self):
		_, _, w, h = self._parent.getSize()
		return w, h

class glGuiLayoutGrid(object):
	def __init__(self, parent):
		self._parent = parent
		self._parent._layout = self
		self._size = 0,0
		self._alignBottom = True

	def update(self):
		borderSize = self._parent._base._buttonSize * 0.2
		x0, y0, w, h = self._parent.getSize()
		x0 += borderSize
		y0 += borderSize
		widths = {}
		heights = {}
		for ctrl in self._parent._glGuiControlList:
			x, y = ctrl._pos
			w, h = ctrl.getMinSize()
			if not x in widths:
				widths[x] = w
			else:
				widths[x] = max(widths[x], w)
			if not y in heights:
				heights[y] = h
			else:
				heights[y] = max(heights[y], h)
		self._size = sum(widths.values()) + borderSize * 2, sum(heights.values()) + borderSize * 2
		if self._alignBottom:
			y0 -= self._size[1] - self._parent.getSize()[3]
			self._parent.setSize(x0 - borderSize, y0 - borderSize, self._size[0], self._size[1])
		for ctrl in self._parent._glGuiControlList:
			x, y = ctrl._pos
			x1 = x0
			y1 = y0
			for n in xrange(0, x):
				if not n in widths:
					widths[n] = 3
				x1 += widths[n]
			for n in xrange(0, y):
				if not n in heights:
					heights[n] = 3
				y1 += heights[n]
			ctrl.setSize(x1, y1, widths[x], heights[y])

	def getLayoutSize(self):
		return self._size

class glButton(glGuiControl):
	def __init__(self, parent, imageID, tooltip, pos, callback, size = None):
		self._buttonSize = size
		self._hidden = False
		super(glButton, self).__init__(parent, pos)
		self._tooltip = tooltip
		self._parent = parent
		self._imageID = imageID
		self._callback = callback
		self._selected = False
		self._focus = False
		self._disabled = False
		self._showExpandArrow = False
		self._progressBar = None
		self._altTooltip = ''

	def setSelected(self, value):
		self._selected = value

	def setExpandArrow(self, value):
		self._showExpandArrow = value

	def setHidden(self, value):
		self._hidden = value

	def setDisabled(self, value):
		self._disabled = value

	def setProgressBar(self, value):
		self._progressBar = value

	def getProgressBar(self):
		return self._progressBar

	def setBottomText(self, value):
		self._altTooltip = value

	def getSelected(self):
		return self._selected

	def getMinSize(self):
		if self._hidden:
			return 0, 0
		if self._buttonSize is not None:
			return self._buttonSize, self._buttonSize
		return self._base._buttonSize, self._base._buttonSize

	def _getPixelPos(self):
		x0, y0, w, h = self.getSize()
		return x0 + w / 2, y0 + h / 2

	def draw(self):
		if self._hidden:
			return

		cx = (self._imageID % 4) / 4
		cy = int(self._imageID / 4) / 4
		bs = self.getMinSize()[0]
		pos = self._getPixelPos()

		glBindTexture(GL_TEXTURE_2D, self._base._glButtonsTexture)
		scale = 0.8
		if self._selected:
			scale = 1.0
		elif self._focus:
			scale = 0.9
		if self._disabled:
			glColor4ub(128,128,128,128)
		else:
			glColor4ub(255,255,255,255)
		openglHelpers.glDrawTexturedQuad(pos[0]-bs*scale/2, pos[1]-bs*scale/2, bs*scale, bs*scale, 0)
		openglHelpers.glDrawTexturedQuad(pos[0]-bs*scale/2, pos[1]-bs*scale/2, bs*scale, bs*scale, self._imageID)
		if self._showExpandArrow:
			if self._selected:
				openglHelpers.glDrawTexturedQuad(pos[0]+bs*scale/2-bs*scale/4*1.2, pos[1]-bs*scale/2*1.2, bs*scale/4, bs*scale/4, 1)
			else:
				openglHelpers.glDrawTexturedQuad(pos[0]+bs*scale/2-bs*scale/4*1.2, pos[1]-bs*scale/2*1.2, bs*scale/4, bs*scale/4, 1, 2)
		glPushMatrix()
		glTranslatef(pos[0], pos[1], 0)
		glDisable(GL_TEXTURE_2D)
		if self._focus:
			glTranslatef(0, -0.55*bs*scale, 0)

			glPushMatrix()
			glColor4ub(60,60,60,255)
			glTranslatef(-1, -1, 0)
			openglHelpers.glDrawStringCenter(self._tooltip)
			glTranslatef(0, 2, 0)
			openglHelpers.glDrawStringCenter(self._tooltip)
			glTranslatef(2, 0, 0)
			openglHelpers.glDrawStringCenter(self._tooltip)
			glTranslatef(0, -2, 0)
			openglHelpers.glDrawStringCenter(self._tooltip)
			glPopMatrix()

			glColor4ub(255,255,255,255)
			openglHelpers.glDrawStringCenter(self._tooltip)
		glPopMatrix()
		progress = self._progressBar
		if progress is not None:
			glColor4ub(60,60,60,255)
			openglHelpers.glDrawQuad(pos[0]-bs/2, pos[1]+bs/2, bs, bs / 4)
			glColor4ub(255,255,255,255)
			openglHelpers.glDrawQuad(pos[0]-bs/2+2, pos[1]+bs/2+2, (bs - 5) * progress + 1, bs / 4 - 4)
		elif len(self._altTooltip) > 0:
			glPushMatrix()
			glTranslatef(pos[0], pos[1], 0)
			glTranslatef(0, 0.6*bs, 0)
			glTranslatef(0, 6, 0)
			#glTranslatef(0.6*bs*scale, 0, 0)

			for line in self._altTooltip.split('\n'):
				glPushMatrix()
				glColor4ub(60,60,60,255)
				glTranslatef(-1, -1, 0)
				openglHelpers.glDrawStringCenter(line)
				glTranslatef(0, 2, 0)
				openglHelpers.glDrawStringCenter(line)
				glTranslatef(2, 0, 0)
				openglHelpers.glDrawStringCenter(line)
				glTranslatef(0, -2, 0)
				openglHelpers.glDrawStringCenter(line)
				glPopMatrix()

				glColor4ub(255,255,255,255)
				openglHelpers.glDrawStringCenter(line)
				glTranslatef(0, 18, 0)
			glPopMatrix()

	def _checkHit(self, x, y):
		if self._hidden or self._disabled:
			return False
		bs = self.getMinSize()[0]
		pos = self._getPixelPos()
		return -bs * 0.5 <= x - pos[0] <= bs * 0.5 and -bs * 0.5 <= y - pos[1] <= bs * 0.5

	def OnMouseMotion(self, x, y):
		if self._checkHit(x, y):
			self._focus = True
			return True
		self._focus = False
		return False

	def OnMouseDown(self, x, y, button):
		if self._checkHit(x, y):
			self._callback(button)
			return True
		return False

class glRadioButton(glButton):
	def __init__(self, parent, imageID, tooltip, pos, group, callback):
		super(glRadioButton, self).__init__(parent, imageID, tooltip, pos, self._onRadioSelect)
		self._group = group
		self._radioCallback = callback
		self._group.append(self)

	def setSelected(self, value):
		self._selected = value

	def _onRadioSelect(self, button):
		self._base._focus = None
		for ctrl in self._group:
			if ctrl != self:
				ctrl.setSelected(False)
		if self.getSelected():
			self.setSelected(False)
		else:
			self.setSelected(True)
		self._radioCallback(button)

class glComboButton(glButton):
	def __init__(self, parent, tooltip, imageIDs, tooltips, pos, callback):
		super(glComboButton, self).__init__(parent, imageIDs[0], tooltip, pos, self._onComboOpenSelect)
		self._imageIDs = imageIDs
		self._tooltips = tooltips
		self._comboCallback = callback
		self._selection = 0

	def _onComboOpenSelect(self, button):
		if self.hasFocus():
			self._base._focus = None
		else:
			self._base._focus = self

	def draw(self):
		if self._hidden:
			return
		self._selected = self.hasFocus()
		super(glComboButton, self).draw()

		bs = self._base._buttonSize / 2
		pos = self._getPixelPos()

		if not self._selected:
			return

		glPushMatrix()
		glTranslatef(pos[0]+bs*0.5, pos[1] + bs*0.5, 0)
		glBindTexture(GL_TEXTURE_2D, self._base._glButtonsTexture)
		for n in xrange(0, len(self._imageIDs)):
			glTranslatef(0, bs, 0)
			glColor4ub(255,255,255,255)
			openglHelpers.glDrawTexturedQuad(-0.5*bs,-0.5*bs,bs,bs, 0)
			openglHelpers.glDrawTexturedQuad(-0.5*bs,-0.5*bs,bs,bs, self._imageIDs[n])
			glDisable(GL_TEXTURE_2D)

			glPushMatrix()
			glTranslatef(-0.55*bs, 0.1*bs, 0)

			glPushMatrix()
			glColor4ub(60,60,60,255)
			glTranslatef(-1, -1, 0)
			openglHelpers.glDrawStringRight(self._tooltips[n])
			glTranslatef(0, 2, 0)
			openglHelpers.glDrawStringRight(self._tooltips[n])
			glTranslatef(2, 0, 0)
			openglHelpers.glDrawStringRight(self._tooltips[n])
			glTranslatef(0, -2, 0)
			openglHelpers.glDrawStringRight(self._tooltips[n])
			glPopMatrix()

			glColor4ub(255,255,255,255)
			openglHelpers.glDrawStringRight(self._tooltips[n])
			glPopMatrix()
		glPopMatrix()

	def getValue(self):
		return self._selection

	def setValue(self, value):
		self._selection = value
		self._imageID = self._imageIDs[self._selection]
		self._comboCallback()

	def OnMouseDown(self, x, y, button):
		if self._hidden or self._disabled:
			return False
		if self.hasFocus():
			bs = self._base._buttonSize / 2
			pos = self._getPixelPos()
			if 0 <= x - pos[0] <= bs and 0 <= y - pos[1] - bs <= bs * len(self._imageIDs):
				self._selection = int((y - pos[1] - bs) / bs)
				self._imageID = self._imageIDs[self._selection]
				self._base._focus = None
				self._comboCallback()
				return True
		return super(glComboButton, self).OnMouseDown(x, y, button)

class glFrame(glGuiContainer):
	def __init__(self, parent, pos):
		super(glFrame, self).__init__(parent, pos)
		self._selected = False
		self._focus = False
		self._hidden = False

	def setSelected(self, value):
		self._selected = value

	def setHidden(self, value):
		self._hidden = value
		for child in self._glGuiControlList:
			if self._base._focus == child:
				self._base._focus = None

	def getSelected(self):
		return self._selected

	def getMinSize(self):
		return self._base._buttonSize, self._base._buttonSize

	def _getPixelPos(self):
		x0, y0, w, h = self.getSize()
		return x0, y0

	def draw(self):
		if self._hidden:
			return

		bs = self._parent._buttonSize
		pos = self._getPixelPos()

		size = self._layout.getLayoutSize()
		glColor4ub(255,255,255,255)
		openglHelpers.glDrawStretchedQuad(pos[0], pos[1], size[0], size[1], bs*0.75, 0)
		#Draw the controls on the frame
		super(glFrame, self).draw()

	def _checkHit(self, x, y):
		if self._hidden:
			return False
		pos = self._getPixelPos()
		w, h = self._layout.getLayoutSize()
		return 0 <= x - pos[0] <= w and 0 <= y - pos[1] <= h

	def OnMouseMotion(self, x, y):
		super(glFrame, self).OnMouseMotion(x, y)
		if self._checkHit(x, y):
			self._focus = True
			return True
		self._focus = False
		return False

	def OnMouseDown(self, x, y, button):
		if self._checkHit(x, y):
			super(glFrame, self).OnMouseDown(x, y, button)
			return True
		return False

class glNotification(glFrame):
	def __init__(self, parent, pos):
		self._anim = None
		super(glNotification, self).__init__(parent, pos)
		glGuiLayoutGrid(self)._alignBottom = False
		self._label = glLabel(self, "Notification", (0, 0))
		self._buttonExtra = glButton(self, 31, "???", (1, 0), self.onExtraButton, 25)
		self._button = glButton(self, 30, "", (2, 0), self.onClose, 25)
		self._padding = glLabel(self, "", (0, 1))
		self.setHidden(True)

	def setSize(self, x, y, w, h):
		w, h = self._layout.getLayoutSize()
		baseSize = self._base.GetSizeTuple()
		if self._anim is not None:
			super(glNotification, self).setSize(baseSize[0] / 2 - w / 2, baseSize[1] - self._anim.getPosition() - self._base._buttonSize * 0.2, 1, 1)
		else:
			super(glNotification, self).setSize(baseSize[0] / 2 - w / 2, baseSize[1] - self._base._buttonSize * 0.2, 1, 1)

	def draw(self):
		self.setSize(0,0,0,0)
		self.updateLayout()
		super(glNotification, self).draw()

	def message(self, text, extraButtonCallback = None, extraButtonIcon = None, extraButtonTooltip = None):
		self._anim = animation(self._base, -20, 25, 1)
		self.setHidden(False)
		self._label.setLabel(text)
		self._buttonExtra.setHidden(extraButtonCallback is None)
		self._buttonExtra._imageID = extraButtonIcon
		self._buttonExtra._tooltip = extraButtonTooltip
		self._extraButtonCallback = extraButtonCallback
		self._base._queueRefresh()
		self.updateLayout()

	def onExtraButton(self, button):
		self.onClose(button)
		self._extraButtonCallback()

	def onClose(self, button):
		if self._anim is not None:
			self._anim = animation(self._base, self._anim.getPosition(), -20, 1)
		else:
			self._anim = animation(self._base, 25, -20, 1)

class glLabel(glGuiControl):
	def __init__(self, parent, label, pos):
		self._label = label
		super(glLabel, self).__init__(parent, pos)

	def setLabel(self, label):
		self._label = label

	def getMinSize(self):
		w, h = openglHelpers.glGetStringSize(self._label)
		return w + 10, h + 4

	def _getPixelPos(self):
		x0, y0, w, h = self.getSize()
		return x0, y0

	def draw(self):
		x, y, w, h = self.getSize()

		glPushMatrix()
		glTranslatef(x, y, 0)

#		glColor4ub(255,255,255,128)
#		glBegin(GL_QUADS)
#		glTexCoord2f(1, 0)
#		glVertex2f( w, 0)
#		glTexCoord2f(0, 0)
#		glVertex2f( 0, 0)
#		glTexCoord2f(0, 1)
#		glVertex2f( 0, h)
#		glTexCoord2f(1, 1)
#		glVertex2f( w, h)
#		glEnd()

		glTranslate(5, h - 5, 0)
		glColor4ub(255,255,255,255)
		openglHelpers.glDrawStringLeft(self._label)
		glPopMatrix()

	def _checkHit(self, x, y):
		return False

	def OnMouseMotion(self, x, y):
		return False

	def OnMouseDown(self, x, y, button):
		return False

class glNumberCtrl(glGuiControl):
	def __init__(self, parent, value, pos, callback):
		self._callback = callback
		self._value = str(value)
		self._selectPos = 0
		self._maxLen = 6
		self._inCallback = False
		super(glNumberCtrl, self).__init__(parent, pos)

	def setValue(self, value):
		if self._inCallback:
			return
		self._value = str(value)

	def getMinSize(self):
		w, h = openglHelpers.glGetStringSize("VALUES")
		return w + 10, h + 4

	def _getPixelPos(self):
		x0, y0, w, h = self.getSize()
		return x0, y0

	def draw(self):
		x, y, w, h = self.getSize()

		glPushMatrix()
		glTranslatef(x, y, 0)

		if self.hasFocus():
			glColor4ub(255,255,255,255)
		else:
			glColor4ub(255,255,255,192)
		glBegin(GL_QUADS)
		glTexCoord2f(1, 0)
		glVertex2f( w, 0)
		glTexCoord2f(0, 0)
		glVertex2f( 0, 0)
		glTexCoord2f(0, 1)
		glVertex2f( 0, h-1)
		glTexCoord2f(1, 1)
		glVertex2f( w, h-1)
		glEnd()

		glTranslate(5, h - 5, 0)
		glColor4ub(0,0,0,255)
		openglHelpers.glDrawStringLeft(self._value)
		if self.hasFocus():
			glTranslate(openglHelpers.glGetStringSize(self._value[0:self._selectPos])[0] - 2, -1, 0)
			openglHelpers.glDrawStringLeft('|')
		glPopMatrix()

	def _checkHit(self, x, y):
		x1, y1, w, h = self.getSize()
		return 0 <= x - x1 <= w and 0 <= y - y1 <= h

	def OnMouseMotion(self, x, y):
		return False

	def OnMouseDown(self, x, y, button):
		if self._checkHit(x, y):
			self.setFocus()
			return True
		return False

	def OnKeyChar(self, c):
		self._inCallback = True
		if c == wx.WXK_LEFT:
			self._selectPos -= 1
			self._selectPos = max(0, self._selectPos)
		if c == wx.WXK_RIGHT:
			self._selectPos += 1
			self._selectPos = min(self._selectPos, len(self._value))
		if c == wx.WXK_UP:
			try:
				value = float(self._value)
			except:
				pass
			else:
				value += 0.1
				self._value = str(value)
				self._callback(self._value)
		if c == wx.WXK_DOWN:
			try:
				value = float(self._value)
			except:
				pass
			else:
				value -= 0.1
				if value > 0:
					self._value = str(value)
					self._callback(self._value)
		if c == wx.WXK_BACK and self._selectPos > 0:
			self._value = self._value[0:self._selectPos - 1] + self._value[self._selectPos:]
			self._selectPos -= 1
			self._callback(self._value)
		if c == wx.WXK_DELETE:
			self._value = self._value[0:self._selectPos] + self._value[self._selectPos + 1:]
			self._callback(self._value)
		if c == wx.WXK_TAB or c == wx.WXK_NUMPAD_ENTER or c == wx.WXK_RETURN:
			if wx.GetKeyState(wx.WXK_SHIFT):
				self.focusPrevious()
			else:
				self.focusNext()
		if (ord('0') <= c <= ord('9') or c == ord('.')) and len(self._value) < self._maxLen:
			self._value = self._value[0:self._selectPos] + chr(c) + self._value[self._selectPos:]
			self._selectPos += 1
			self._callback(self._value)
		self._inCallback = False

	def setFocus(self):
		self._base._focus = self
		self._selectPos = len(self._value)
		return True

class glCheckbox(glGuiControl):
	def __init__(self, parent, value, pos, callback):
		self._callback = callback
		self._value = value
		self._selectPos = 0
		self._maxLen = 6
		self._inCallback = False
		super(glCheckbox, self).__init__(parent, pos)

	def setValue(self, value):
		if self._inCallback:
			return
		self._value = str(value)

	def getValue(self):
		return self._value

	def getMinSize(self):
		return 20, 20

	def _getPixelPos(self):
		x0, y0, w, h = self.getSize()
		return x0, y0

	def draw(self):
		x, y, w, h = self.getSize()

		glPushMatrix()
		glTranslatef(x, y, 0)

		glColor3ub(255,255,255)
		if self._value:
			openglHelpers.glDrawTexturedQuad(w/2-h/2,0, h, h, 28)
		else:
			openglHelpers.glDrawTexturedQuad(w/2-h/2,0, h, h, 29)

		glPopMatrix()

	def _checkHit(self, x, y):
		x1, y1, w, h = self.getSize()
		return 0 <= x - x1 <= w and 0 <= y - y1 <= h

	def OnMouseMotion(self, x, y):
		return False

	def OnMouseDown(self, x, y, button):
		if self._checkHit(x, y):
			self._value = not self._value
			return True
		return False

class glSlider(glGuiControl):
	def __init__(self, parent, value, minValue, maxValue, pos, callback):
		super(glSlider, self).__init__(parent, pos)
		self._callback = callback
		self._focus = False
		self._hidden = False
		self._value = value
		self._minValue = minValue
		self._maxValue = maxValue

	def setValue(self, value):
		self._value = value

	def getValue(self):
		if self._value < self._minValue:
			return self._minValue
		if self._value > self._maxValue:
			return self._maxValue
		return self._value

	def setRange(self, minValue, maxValue):
		if maxValue < minValue:
			maxValue = minValue
		self._minValue = minValue
		self._maxValue = maxValue

	def getMinValue(self):
		return self._minValue

	def getMaxValue(self):
		return self._maxValue

	def setHidden(self, value):
		self._hidden = value

	def getMinSize(self):
		return self._base._buttonSize * 0.2, self._base._buttonSize * 4

	def _getPixelPos(self):
		x0, y0, w, h = self.getSize()
		minSize = self.getMinSize()
		return x0 + w / 2 - minSize[0] / 2, y0 + h / 2 - minSize[1] / 2

	def draw(self):
		if self._hidden:
			return

		w, h = self.getMinSize()
		pos = self._getPixelPos()

		glPushMatrix()
		glTranslatef(pos[0], pos[1], 0)
		glDisable(GL_TEXTURE_2D)
		if self.hasFocus():
			glColor4ub(60,60,60,255)
		else:
			glColor4ub(60,60,60,192)
		glBegin(GL_QUADS)
		glVertex2f( w/2,-h/2)
		glVertex2f(-w/2,-h/2)
		glVertex2f(-w/2, h/2)
		glVertex2f( w/2, h/2)
		glEnd()
		scrollLength = h - w
		if self._maxValue-self._minValue != 0:
			valueNormalized = ((self.getValue()-self._minValue)/(self._maxValue-self._minValue))
		else:
			valueNormalized = 0
		glTranslate(0.0,scrollLength/2,0)
		if True:  # self._focus:
			glColor4ub(0,0,0,255)
			glPushMatrix()
			glTranslate(-w/2,openglHelpers.glGetStringSize(str(self._minValue))[1]/2,0)
			openglHelpers.glDrawStringRight(str(self._minValue))
			glTranslate(0,-scrollLength,0)
			openglHelpers.glDrawStringRight(str(self._maxValue))
			glTranslate(w,scrollLength-scrollLength*valueNormalized,0)
			openglHelpers.glDrawStringLeft(str(self.getValue()))
			glPopMatrix()
		glColor4ub(255,255,255,240)
		glTranslate(0.0,-scrollLength*valueNormalized,0)
		glBegin(GL_QUADS)
		glVertex2f( w/2,-w/2)
		glVertex2f(-w/2,-w/2)
		glVertex2f(-w/2, w/2)
		glVertex2f( w/2, w/2)
		glEnd()
		glPopMatrix()

	def _checkHit(self, x, y):
		if self._hidden:
			return False
		pos = self._getPixelPos()
		w, h = self.getMinSize()
		return -w/2 <= x - pos[0] <= w/2 and -h/2 <= y - pos[1] <= h/2

	def setFocus(self):
		self._base._focus = self
		return True

	def OnMouseMotion(self, x, y):
		if self.hasFocus():
			w, h = self.getMinSize()
			scrollLength = h - w
			pos = self._getPixelPos()
			self.setValue(int(self._minValue + (self._maxValue - self._minValue) * -(y - pos[1] - scrollLength/2) / scrollLength))
			self._callback()
			return True
		if self._checkHit(x, y):
			self._focus = True
			return True
		self._focus = False
		return False

	def OnMouseDown(self, x, y, button):
		if self._checkHit(x, y):
			self.setFocus()
			self.OnMouseMotion(x, y)
			return True
		return False

	def OnMouseUp(self, x, y):
		if self.hasFocus():
			self._base._focus = None
			return True
		return False

########NEW FILE########
__FILENAME__ = openglHelpers
__copyright__ = "Copyright (C) 2013 David Braam - Released under terms of the AGPLv3 License"

import math
import numpy
import wx
import time

from Cura.util.resources import getPathForImage

import OpenGL

OpenGL.ERROR_CHECKING = False
from OpenGL.GLUT import *
from OpenGL.GLU import *
from OpenGL.GL import *
from OpenGL.GL import shaders
glutInit() #Hack; required before glut can be called. Not required for all OS.

class GLReferenceCounter(object):
	def __init__(self):
		self._refCounter = 1

	def incRef(self):
		self._refCounter += 1

	def decRef(self):
		self._refCounter -= 1
		return self._refCounter <= 0

def hasShaderSupport():
	if bool(glCreateShader):
		return True
	return False

class GLShader(GLReferenceCounter):
	def __init__(self, vertexProgram, fragmentProgram):
		super(GLShader, self).__init__()
		self._vertexString = vertexProgram
		self._fragmentString = fragmentProgram
		try:
			vertexShader = shaders.compileShader(vertexProgram, GL_VERTEX_SHADER)
			fragmentShader = shaders.compileShader(fragmentProgram, GL_FRAGMENT_SHADER)

			#shader.compileProgram tries to return the shader program as a overloaded int. But the return value of a shader does not always fit in a int (needs to be a long). So we do raw OpenGL calls.
			# This is to ensure that this works on intel GPU's
			# self._program = shaders.compileProgram(self._vertexProgram, self._fragmentProgram)
			self._program = glCreateProgram()
			glAttachShader(self._program, vertexShader)
			glAttachShader(self._program, fragmentShader)
			glLinkProgram(self._program)
			# Validation has to occur *after* linking
			glValidateProgram(self._program)
			if glGetProgramiv(self._program, GL_VALIDATE_STATUS) == GL_FALSE:
				raise RuntimeError("Validation failure: %s"%(glGetProgramInfoLog(self._program)))
			if glGetProgramiv(self._program, GL_LINK_STATUS) == GL_FALSE:
				raise RuntimeError("Link failure: %s" % (glGetProgramInfoLog(self._program)))
			glDeleteShader(vertexShader)
			glDeleteShader(fragmentShader)
		except RuntimeError, e:
			print str(e)
			self._program = None

	def bind(self):
		if self._program is not None:
			shaders.glUseProgram(self._program)

	def unbind(self):
		shaders.glUseProgram(0)

	def release(self):
		if self._program is not None:
			glDeleteProgram(self._program)
			self._program = None

	def setUniform(self, name, value):
		if self._program is not None:
			if type(value) is float:
				glUniform1f(glGetUniformLocation(self._program, name), value)
			elif type(value) is numpy.matrix:
				glUniformMatrix3fv(glGetUniformLocation(self._program, name), 1, False, value.getA().astype(numpy.float32))
			else:
				print 'Unknown type for setUniform: %s' % (str(type(value)))

	def isValid(self):
		return self._program is not None

	def getVertexShader(self):
		return self._vertexString

	def getFragmentShader(self):
		return self._fragmentString

	def __del__(self):
		if self._program is not None and bool(glDeleteProgram):
			print "Shader was not properly released!"

class GLFakeShader(GLReferenceCounter):
	"""
	A Class that acts as an OpenGL shader, but in reality is not one. Used if shaders are not supported.
	"""
	def __init__(self):
		super(GLFakeShader, self).__init__()

	def bind(self):
		glEnable(GL_LIGHTING)
		glEnable(GL_LIGHT0)
		glEnable(GL_COLOR_MATERIAL)
		glLightfv(GL_LIGHT0, GL_DIFFUSE, [1,1,1,1])
		glLightfv(GL_LIGHT0, GL_AMBIENT, [0,0,0,0])
		glLightfv(GL_LIGHT0, GL_SPECULAR, [0,0,0,0])

	def unbind(self):
		glDisable(GL_LIGHTING)

	def release(self):
		pass

	def setUniform(self, name, value):
		pass

	def isValid(self):
		return True

	def getVertexShader(self):
		return ''

	def getFragmentShader(self):
		return ''

class GLVBO(GLReferenceCounter):
	"""
	Vertex buffer object. Used for faster rendering.
	"""
	def __init__(self, renderType, vertexArray, normalArray = None, indicesArray = None):
		super(GLVBO, self).__init__()
		# TODO: Add size check to see if normal and vertex arrays have same size.
		self._renderType = renderType
		if not bool(glGenBuffers): # Fallback if buffers are not supported.
			self._vertexArray = vertexArray
			self._normalArray = normalArray
			self._indicesArray = indicesArray
			self._size = len(vertexArray)
			self._buffers = None
			self._hasNormals = self._normalArray is not None
			self._hasIndices = self._indicesArray is not None
			if self._hasIndices:
				self._size = len(indicesArray)
		else:
			self._buffers = []
			self._size = len(vertexArray)
			self._hasNormals = normalArray is not None
			self._hasIndices = indicesArray is not None
			maxVertsPerBuffer = 30000
			if self._hasIndices:
				maxVertsPerBuffer = self._size
			if maxVertsPerBuffer > 0:
				bufferCount = ((self._size-1) / maxVertsPerBuffer) + 1
				for n in xrange(0, bufferCount):
					bufferInfo = {
						'buffer': glGenBuffers(1),
						'size': maxVertsPerBuffer
					}
					offset = n * maxVertsPerBuffer
					if n == bufferCount - 1:
						bufferInfo['size'] = ((self._size - 1) % maxVertsPerBuffer) + 1
					glBindBuffer(GL_ARRAY_BUFFER, bufferInfo['buffer'])
					if self._hasNormals:
						glBufferData(GL_ARRAY_BUFFER, numpy.concatenate((vertexArray[offset:offset+bufferInfo['size']], normalArray[offset:offset+bufferInfo['size']]), 1), GL_STATIC_DRAW)
					else:
						glBufferData(GL_ARRAY_BUFFER, vertexArray[offset:offset+bufferInfo['size']], GL_STATIC_DRAW)
					glBindBuffer(GL_ARRAY_BUFFER, 0)
					self._buffers.append(bufferInfo)
			if self._hasIndices:
				self._size = len(indicesArray)
				self._bufferIndices = glGenBuffers(1)
				glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self._bufferIndices)
				glBufferData(GL_ELEMENT_ARRAY_BUFFER, numpy.array(indicesArray, numpy.uint32), GL_STATIC_DRAW)

	def render(self):
		glEnableClientState(GL_VERTEX_ARRAY)
		if self._buffers is None:
			glVertexPointer(3, GL_FLOAT, 0, self._vertexArray)
			if self._hasNormals:
				glEnableClientState(GL_NORMAL_ARRAY)
				glNormalPointer(GL_FLOAT, 0, self._normalArray)
			if self._hasIndices:
				glDrawElements(self._renderType, self._size, GL_UNSIGNED_INT, self._indicesArray)
			else:
				batchSize = 996	#Warning, batchSize needs to be dividable by 4 (quads), 3 (triangles) and 2 (lines). Current value is magic.
				extraStartPos = int(self._size / batchSize) * batchSize #leftovers.
				extraCount = self._size - extraStartPos
				for i in xrange(0, int(self._size / batchSize)):
					glDrawArrays(self._renderType, i * batchSize, batchSize)
				glDrawArrays(self._renderType, extraStartPos, extraCount)
		else:
			for info in self._buffers:
				glBindBuffer(GL_ARRAY_BUFFER, info['buffer'])
				if self._hasNormals:
					glEnableClientState(GL_NORMAL_ARRAY)
					glVertexPointer(3, GL_FLOAT, 2*3*4, c_void_p(0))
					glNormalPointer(GL_FLOAT, 2*3*4, c_void_p(3 * 4))
				else:
					glVertexPointer(3, GL_FLOAT, 3*4, c_void_p(0))
				if self._hasIndices:
					glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, self._bufferIndices)
					glDrawElements(self._renderType, self._size, GL_UNSIGNED_INT, c_void_p(0))
				else:
					glDrawArrays(self._renderType, 0, info['size'])

				glBindBuffer(GL_ARRAY_BUFFER, 0)
				if self._hasIndices:
					glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, 0)

		glDisableClientState(GL_VERTEX_ARRAY)
		if self._hasNormals:
			glDisableClientState(GL_NORMAL_ARRAY)

	def release(self):
		if self._buffers is not None:
			for info in self._buffers:
				glBindBuffer(GL_ARRAY_BUFFER, info['buffer'])
				glBufferData(GL_ARRAY_BUFFER, None, GL_STATIC_DRAW)
				glBindBuffer(GL_ARRAY_BUFFER, 0)
				glDeleteBuffers(1, [info['buffer']])
			self._buffers = None
			if self._hasIndices:
				glBindBuffer(GL_ARRAY_BUFFER, self._bufferIndices)
				glBufferData(GL_ARRAY_BUFFER, None, GL_STATIC_DRAW)
				glBindBuffer(GL_ARRAY_BUFFER, 0)
				glDeleteBuffers(1, [self._bufferIndices])
		self._vertexArray = None
		self._normalArray = None

	def __del__(self):
		if self._buffers is not None and bool(glDeleteBuffers):
			print "VBO was not properly released!"

def glDrawStringCenter(s):
	"""
	Draw string on current draw pointer position
	"""
	glRasterPos2f(0, 0)
	glBitmap(0,0,0,0, -glGetStringSize(s)[0]/2, 0, None)
	for c in s:
		glutBitmapCharacter(OpenGL.GLUT.GLUT_BITMAP_HELVETICA_18, ord(c))

def glGetStringSize(s):
	"""
	Get size in pixels of string
	"""
	width = 0
	for c in s:
		width += glutBitmapWidth(OpenGL.GLUT.GLUT_BITMAP_HELVETICA_18, ord(c))
	height = 18
	return width, height

def glDrawStringLeft(s):
	glRasterPos2f(0, 0)
	n = 1
	for c in s:
		if c == '\n':
			glPushMatrix()
			glTranslate(0, 18 * n, 0)
			n += 1
			glRasterPos2f(0, 0)
			glPopMatrix()
		else:
			glutBitmapCharacter(OpenGL.GLUT.GLUT_BITMAP_HELVETICA_18, ord(c))

def glDrawStringRight(s):
	glRasterPos2f(0, 0)
	glBitmap(0,0,0,0, -glGetStringSize(s)[0], 0, None)
	for c in s:
		glutBitmapCharacter(OpenGL.GLUT.GLUT_BITMAP_HELVETICA_18, ord(c))

def glDrawQuad(x, y, w, h):
	glPushMatrix()
	glTranslatef(x, y, 0)
	glDisable(GL_TEXTURE_2D)
	glBegin(GL_QUADS)
	glVertex2f(w, 0)
	glVertex2f(0, 0)
	glVertex2f(0, h)
	glVertex2f(w, h)
	glEnd()
	glPopMatrix()

def glDrawTexturedQuad(x, y, w, h, texID, mirror = 0):
	tx = float(texID % 4) / 4
	ty = float(int(texID / 4)) / 8
	tsx = 0.25
	tsy = 0.125
	if mirror & 1:
		tx += tsx
		tsx = -tsx
	if mirror & 2:
		ty += tsy
		tsy = -tsy
	glPushMatrix()
	glTranslatef(x, y, 0)
	glEnable(GL_TEXTURE_2D)
	glBegin(GL_QUADS)
	glTexCoord2f(tx+tsx, ty)
	glVertex2f(w, 0)
	glTexCoord2f(tx, ty)
	glVertex2f(0, 0)
	glTexCoord2f(tx, ty+tsy)
	glVertex2f(0, h)
	glTexCoord2f(tx+tsx, ty+tsy)
	glVertex2f(w, h)
	glEnd()
	glPopMatrix()

def glDrawStretchedQuad(x, y, w, h, cornerSize, texID):
	"""
	Same as draw texured quad, but without stretching the corners. Useful for resizable windows.
	"""
	tx0 = float(texID % 4) / 4
	ty0 = float(int(texID / 4)) / 8
	tx1 = tx0 + 0.25 / 2.0
	ty1 = ty0 + 0.125 / 2.0
	tx2 = tx0 + 0.25
	ty2 = ty0 + 0.125

	glPushMatrix()
	glTranslatef(x, y, 0)
	glEnable(GL_TEXTURE_2D)
	glBegin(GL_QUADS)
	#TopLeft
	glTexCoord2f(tx1, ty0)
	glVertex2f( cornerSize, 0)
	glTexCoord2f(tx0, ty0)
	glVertex2f( 0, 0)
	glTexCoord2f(tx0, ty1)
	glVertex2f( 0, cornerSize)
	glTexCoord2f(tx1, ty1)
	glVertex2f( cornerSize, cornerSize)
	#TopRight
	glTexCoord2f(tx2, ty0)
	glVertex2f( w, 0)
	glTexCoord2f(tx1, ty0)
	glVertex2f( w - cornerSize, 0)
	glTexCoord2f(tx1, ty1)
	glVertex2f( w - cornerSize, cornerSize)
	glTexCoord2f(tx2, ty1)
	glVertex2f( w, cornerSize)
	#BottomLeft
	glTexCoord2f(tx1, ty1)
	glVertex2f( cornerSize, h - cornerSize)
	glTexCoord2f(tx0, ty1)
	glVertex2f( 0, h - cornerSize)
	glTexCoord2f(tx0, ty2)
	glVertex2f( 0, h)
	glTexCoord2f(tx1, ty2)
	glVertex2f( cornerSize, h)
	#BottomRight
	glTexCoord2f(tx2, ty1)
	glVertex2f( w, h - cornerSize)
	glTexCoord2f(tx1, ty1)
	glVertex2f( w - cornerSize, h - cornerSize)
	glTexCoord2f(tx1, ty2)
	glVertex2f( w - cornerSize, h)
	glTexCoord2f(tx2, ty2)
	glVertex2f( w, h)

	#Center
	glTexCoord2f(tx1, ty1)
	glVertex2f( w-cornerSize, cornerSize)
	glTexCoord2f(tx1, ty1)
	glVertex2f( cornerSize, cornerSize)
	glTexCoord2f(tx1, ty1)
	glVertex2f( cornerSize, h-cornerSize)
	glTexCoord2f(tx1, ty1)
	glVertex2f( w-cornerSize, h-cornerSize)

	#Right
	glTexCoord2f(tx2, ty1)
	glVertex2f( w, cornerSize)
	glTexCoord2f(tx1, ty1)
	glVertex2f( w-cornerSize, cornerSize)
	glTexCoord2f(tx1, ty1)
	glVertex2f( w-cornerSize, h-cornerSize)
	glTexCoord2f(tx2, ty1)
	glVertex2f( w, h-cornerSize)

	#Left
	glTexCoord2f(tx1, ty1)
	glVertex2f( cornerSize, cornerSize)
	glTexCoord2f(tx0, ty1)
	glVertex2f( 0, cornerSize)
	glTexCoord2f(tx0, ty1)
	glVertex2f( 0, h-cornerSize)
	glTexCoord2f(tx1, ty1)
	glVertex2f( cornerSize, h-cornerSize)

	#Top
	glTexCoord2f(tx1, ty0)
	glVertex2f( w-cornerSize, 0)
	glTexCoord2f(tx1, ty0)
	glVertex2f( cornerSize, 0)
	glTexCoord2f(tx1, ty1)
	glVertex2f( cornerSize, cornerSize)
	glTexCoord2f(tx1, ty1)
	glVertex2f( w-cornerSize, cornerSize)

	#Bottom
	glTexCoord2f(tx1, ty1)
	glVertex2f( w-cornerSize, h-cornerSize)
	glTexCoord2f(tx1, ty1)
	glVertex2f( cornerSize, h-cornerSize)
	glTexCoord2f(tx1, ty2)
	glVertex2f( cornerSize, h)
	glTexCoord2f(tx1, ty2)
	glVertex2f( w-cornerSize, h)

	glEnd()
	glDisable(GL_TEXTURE_2D)
	glPopMatrix()

def unproject(winx, winy, winz, modelMatrix, projMatrix, viewport):
	"""
	Projects window position to 3D space. (gluUnProject). Reimplentation as some drivers crash with the original.
	"""
	npModelMatrix = numpy.matrix(numpy.array(modelMatrix, numpy.float64).reshape((4,4)))
	npProjMatrix = numpy.matrix(numpy.array(projMatrix, numpy.float64).reshape((4,4)))
	finalMatrix = npModelMatrix * npProjMatrix
	finalMatrix = numpy.linalg.inv(finalMatrix)

	viewport = map(float, viewport)
	vector = numpy.array([(winx - viewport[0]) / viewport[2] * 2.0 - 1.0, (winy - viewport[1]) / viewport[3] * 2.0 - 1.0, winz * 2.0 - 1.0, 1]).reshape((1,4))
	vector = (numpy.matrix(vector) * finalMatrix).getA().flatten()
	ret = list(vector)[0:3] / vector[3]
	return ret

def convert3x3MatrixTo4x4(matrix):
	return list(matrix.getA()[0]) + [0] + list(matrix.getA()[1]) + [0] + list(matrix.getA()[2]) + [0, 0,0,0,1]

def loadGLTexture(filename):
	tex = glGenTextures(1)
	glBindTexture(GL_TEXTURE_2D, tex)
	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
	glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
	img = wx.ImageFromBitmap(wx.Bitmap(getPathForImage(filename)))
	rgbData = img.GetData()
	alphaData = img.GetAlphaData()
	if alphaData is not None:
		data = ''
		for i in xrange(0, len(alphaData)):
			data += rgbData[i*3:i*3+3] + alphaData[i]
		glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, img.GetWidth(), img.GetHeight(), 0, GL_RGBA, GL_UNSIGNED_BYTE, data)
	else:
		glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, img.GetWidth(), img.GetHeight(), 0, GL_RGB, GL_UNSIGNED_BYTE, rgbData)
	return tex

def DrawBox(vMin, vMax):
	""" Draw wireframe box
	"""
	glBegin(GL_LINE_LOOP)
	glVertex3f(vMin[0], vMin[1], vMin[2])
	glVertex3f(vMax[0], vMin[1], vMin[2])
	glVertex3f(vMax[0], vMax[1], vMin[2])
	glVertex3f(vMin[0], vMax[1], vMin[2])
	glEnd()

	glBegin(GL_LINE_LOOP)
	glVertex3f(vMin[0], vMin[1], vMax[2])
	glVertex3f(vMax[0], vMin[1], vMax[2])
	glVertex3f(vMax[0], vMax[1], vMax[2])
	glVertex3f(vMin[0], vMax[1], vMax[2])
	glEnd()
	glBegin(GL_LINES)
	glVertex3f(vMin[0], vMin[1], vMin[2])
	glVertex3f(vMin[0], vMin[1], vMax[2])
	glVertex3f(vMax[0], vMin[1], vMin[2])
	glVertex3f(vMax[0], vMin[1], vMax[2])
	glVertex3f(vMax[0], vMax[1], vMin[2])
	glVertex3f(vMax[0], vMax[1], vMax[2])
	glVertex3f(vMin[0], vMax[1], vMin[2])
	glVertex3f(vMin[0], vMax[1], vMax[2])
	glEnd()
########NEW FILE########
__FILENAME__ = previewTools
__copyright__ = "Copyright (C) 2013 David Braam - Released under terms of the AGPLv3 License"

import math
import wx
import numpy

import OpenGL
OpenGL.ERROR_CHECKING = False
from OpenGL.GLU import *
from OpenGL.GL import *

from Cura.gui.util import openglHelpers
#TODO: Rename these. Name is vague.
class toolNone(object):
	def __init__(self, parent):
		self.parent = parent

	def OnMouseMove(self, p0, p1):
		pass

	def OnDragStart(self, p0, p1):
		return False

	def OnDrag(self, p0, p1):
		pass

	def OnDragEnd(self):
		pass

	def OnDraw(self):
		pass

class toolInfo(object):
	def __init__(self, parent):
		self.parent = parent

	def OnMouseMove(self, p0, p1):
		pass

	def OnDragStart(self, p0, p1):
		return False

	def OnDrag(self, p0, p1):
		pass

	def OnDragEnd(self):
		pass

	def OnDraw(self):
		glDisable(GL_LIGHTING)
		glDisable(GL_BLEND)
		glDisable(GL_DEPTH_TEST)
		glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
		glColor3ub(0,0,0)
		size = self.parent.getObjectSize()
		radius = self.parent.getObjectBoundaryCircle()
		glPushMatrix()
		glTranslate(0,0,size[2]/2 + 5)
		glRotate(-self.parent.yaw, 0,0,1)
		if self.parent.pitch < 80:
			glTranslate(0, radius + 5,0)
		elif self.parent.pitch < 100:
			glTranslate(0, (radius + 5) * (90 - self.parent.pitch) / 10,0)
		else:
			glTranslate(0,-(radius + 5),0)
		openglHelpers.glDrawStringCenter("%dx%dx%d" % (size[0], size[1], size[2]))
		glPopMatrix()

		glColor(255,255,255)
		size = size / 2
		glLineWidth(1)
		glBegin(GL_LINES)
		glVertex3f(size[0], size[1], size[2])
		glVertex3f(size[0], size[1], size[2]/4*3)
		glVertex3f(size[0], size[1], size[2])
		glVertex3f(size[0], size[1]/4*3, size[2])
		glVertex3f(size[0], size[1], size[2])
		glVertex3f(size[0]/4*3, size[1], size[2])

		glVertex3f(-size[0], -size[1], size[2])
		glVertex3f(-size[0], -size[1], size[2]/4*3)
		glVertex3f(-size[0], -size[1], size[2])
		glVertex3f(-size[0], -size[1]/4*3, size[2])
		glVertex3f(-size[0], -size[1], size[2])
		glVertex3f(-size[0]/4*3, -size[1], size[2])

		glVertex3f(size[0], -size[1], -size[2])
		glVertex3f(size[0], -size[1], -size[2]/4*3)
		glVertex3f(size[0], -size[1], -size[2])
		glVertex3f(size[0], -size[1]/4*3, -size[2])
		glVertex3f(size[0], -size[1], -size[2])
		glVertex3f(size[0]/4*3, -size[1], -size[2])

		glVertex3f(-size[0], size[1], -size[2])
		glVertex3f(-size[0], size[1], -size[2]/4*3)
		glVertex3f(-size[0], size[1], -size[2])
		glVertex3f(-size[0], size[1]/4*3, -size[2])
		glVertex3f(-size[0], size[1], -size[2])
		glVertex3f(-size[0]/4*3, size[1], -size[2])
		glEnd()

class toolRotate(object):
	def __init__(self, parent):
		self.parent = parent
		self.rotateRingDist = 1.5
		self.rotateRingDistMin = 1.3
		self.rotateRingDistMax = 1.7
		self.dragPlane = None
		self.dragStartAngle = None
		self.dragEndAngle = None

	def _ProjectToPlanes(self, p0, p1):
		cursorX0 = p0 - (p1 - p0) * (p0[0] / (p1[0] - p0[0]))
		cursorY0 = p0 - (p1 - p0) * (p0[1] / (p1[1] - p0[1]))
		cursorZ0 = p0 - (p1 - p0) * (p0[2] / (p1[2] - p0[2]))
		cursorYZ = math.sqrt((cursorX0[1] * cursorX0[1]) + (cursorX0[2] * cursorX0[2]))
		cursorXZ = math.sqrt((cursorY0[0] * cursorY0[0]) + (cursorY0[2] * cursorY0[2]))
		cursorXY = math.sqrt((cursorZ0[0] * cursorZ0[0]) + (cursorZ0[1] * cursorZ0[1]))
		return cursorX0, cursorY0, cursorZ0, cursorYZ, cursorXZ, cursorXY

	def OnMouseMove(self, p0, p1):
		radius = self.parent.getObjectBoundaryCircle()
		cursorX0, cursorY0, cursorZ0, cursorYZ, cursorXZ, cursorXY = self._ProjectToPlanes(p0, p1)
		oldDragPlane = self.dragPlane
		if radius * self.rotateRingDistMin <= cursorXY <= radius * self.rotateRingDistMax or radius * self.rotateRingDistMin <= cursorYZ <= radius * self.rotateRingDistMax or radius * self.rotateRingDistMin <= cursorXZ <= radius * self.rotateRingDistMax:
			#self.parent.SetCursor(wx.StockCursor(wx.CURSOR_SIZING))
			if self.dragStartAngle is None:
				if radius * self.rotateRingDistMin <= cursorXY <= radius * self.rotateRingDistMax:
					self.dragPlane = 'XY'
				elif radius * self.rotateRingDistMin <= cursorXZ <= radius * self.rotateRingDistMax:
					self.dragPlane = 'XZ'
				else:
					self.dragPlane = 'YZ'
		else:
			if self.dragStartAngle is None:
				self.dragPlane = ''
			#self.parent.SetCursor(wx.StockCursor(wx.CURSOR_DEFAULT))

	def OnDragStart(self, p0, p1):
		radius = self.parent.getObjectBoundaryCircle()
		cursorX0, cursorY0, cursorZ0, cursorYZ, cursorXZ, cursorXY = self._ProjectToPlanes(p0, p1)
		if radius * self.rotateRingDistMin <= cursorXY <= radius * self.rotateRingDistMax or radius * self.rotateRingDistMin <= cursorYZ <= radius * self.rotateRingDistMax or radius * self.rotateRingDistMin <= cursorXZ <= radius * self.rotateRingDistMax:
			if radius * self.rotateRingDistMin <= cursorXY <= radius * self.rotateRingDistMax:
				self.dragPlane = 'XY'
				self.dragStartAngle = math.atan2(cursorZ0[1], cursorZ0[0]) * 180 / math.pi
			elif radius * self.rotateRingDistMin <= cursorXZ <= radius * self.rotateRingDistMax:
				self.dragPlane = 'XZ'
				self.dragStartAngle = math.atan2(cursorY0[2], cursorY0[0]) * 180 / math.pi
			else:
				self.dragPlane = 'YZ'
				self.dragStartAngle = math.atan2(cursorX0[2], cursorX0[1]) * 180 / math.pi
			self.dragEndAngle = self.dragStartAngle
			return True
		return False

	def OnDrag(self, p0, p1):
		cursorX0, cursorY0, cursorZ0, cursorYZ, cursorXZ, cursorXY = self._ProjectToPlanes(p0, p1)
		if self.dragPlane == 'XY':
			angle = math.atan2(cursorZ0[1], cursorZ0[0]) * 180 / math.pi
		elif self.dragPlane == 'XZ':
			angle = math.atan2(cursorY0[2], cursorY0[0]) * 180 / math.pi
		else:
			angle = math.atan2(cursorX0[2], cursorX0[1]) * 180 / math.pi
		diff = angle - self.dragStartAngle
		if wx.GetKeyState(wx.WXK_SHIFT):
			diff = round(diff / 1) * 1
		else:
			diff = round(diff / 15) * 15
		if diff > 180:
			diff -= 360
		if diff < -180:
			diff += 360
		rad = diff / 180.0 * math.pi
		self.dragEndAngle = self.dragStartAngle + diff
		if self.dragPlane == 'XY':
			self.parent.tempMatrix = numpy.matrix([[math.cos(rad), math.sin(rad), 0], [-math.sin(rad), math.cos(rad), 0], [0,0,1]], numpy.float64)
		elif self.dragPlane == 'XZ':
			self.parent.tempMatrix = numpy.matrix([[math.cos(rad), 0, math.sin(rad)], [0,1,0], [-math.sin(rad), 0, math.cos(rad)]], numpy.float64)
		else:
			self.parent.tempMatrix = numpy.matrix([[1,0,0], [0, math.cos(rad), math.sin(rad)], [0, -math.sin(rad), math.cos(rad)]], numpy.float64)

	def OnDragEnd(self):
		self.dragStartAngle = None

	def OnDraw(self):
		glDisable(GL_LIGHTING)
		glDisable(GL_BLEND)
		glDisable(GL_DEPTH_TEST)
		glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
		radius = self.parent.getObjectBoundaryCircle()
		glScalef(self.rotateRingDist * radius, self.rotateRingDist * radius, self.rotateRingDist * radius)
		if self.dragPlane == 'XY':
			glLineWidth(3)
			glColor4ub(255,64,64,255)
			if self.dragStartAngle is not None:
				glPushMatrix()
				glRotate(self.dragStartAngle, 0,0,1)
				glBegin(GL_LINES)
				glVertex3f(0,0,0)
				glVertex3f(1,0,0)
				glEnd()
				glPopMatrix()
				glPushMatrix()
				glRotate(self.dragEndAngle, 0,0,1)
				glBegin(GL_LINES)
				glVertex3f(0,0,0)
				glVertex3f(1,0,0)
				glEnd()
				glTranslatef(1.1,0,0)
				glColor4ub(0,0,0,255)
				openglHelpers.glDrawStringCenter("%d" % (abs(self.dragEndAngle - self.dragStartAngle) + 0.5))
				glColor4ub(255,64,64,255)
				glPopMatrix()
		else:
			glLineWidth(1)
			glColor4ub(128,0,0,255)
		glBegin(GL_LINE_LOOP)
		for i in xrange(0, 64):
			glVertex3f(math.cos(i/32.0*math.pi), math.sin(i/32.0*math.pi),0)
		glEnd()
		if self.dragPlane == 'YZ':
			glColor4ub(64,255,64,255)
			glLineWidth(3)
			if self.dragStartAngle is not None:
				glPushMatrix()
				glRotate(self.dragStartAngle, 1,0,0)
				glBegin(GL_LINES)
				glVertex3f(0,0,0)
				glVertex3f(0,1,0)
				glEnd()
				glPopMatrix()
				glPushMatrix()
				glRotate(self.dragEndAngle, 1,0,0)
				glBegin(GL_LINES)
				glVertex3f(0,0,0)
				glVertex3f(0,1,0)
				glEnd()
				glTranslatef(0,1.1,0)
				glColor4ub(0,0,0,255)
				openglHelpers.glDrawStringCenter("%d" % (abs(self.dragEndAngle - self.dragStartAngle)))
				glColor4ub(64,255,64,255)
				glPopMatrix()
		else:
			glColor4ub(0,128,0,255)
			glLineWidth(1)
		glBegin(GL_LINE_LOOP)
		for i in xrange(0, 64):
			glVertex3f(0, math.cos(i/32.0*math.pi), math.sin(i/32.0*math.pi))
		glEnd()
		if self.dragPlane == 'XZ':
			glLineWidth(3)
			glColor4ub(255,255,0,255)
			if self.dragStartAngle is not None:
				glPushMatrix()
				glRotate(self.dragStartAngle, 0,-1,0)
				glBegin(GL_LINES)
				glVertex3f(0,0,0)
				glVertex3f(1,0,0)
				glEnd()
				glPopMatrix()
				glPushMatrix()
				glRotate(self.dragEndAngle, 0,-1,0)
				glBegin(GL_LINES)
				glVertex3f(0,0,0)
				glVertex3f(1,0,0)
				glEnd()
				glTranslatef(1.1,0,0)
				glColor4ub(0,0,0,255)
				openglHelpers.glDrawStringCenter("%d" % (round(abs(self.dragEndAngle - self.dragStartAngle))))
				glColor4ub(255,255,0,255)
				glPopMatrix()
		else:
			glColor4ub(128,128,0,255)
			glLineWidth(1)
		glBegin(GL_LINE_LOOP)
		for i in xrange(0, 64):
			glVertex3f(math.cos(i/32.0*math.pi), 0, math.sin(i/32.0*math.pi))
		glEnd()
		glEnable(GL_DEPTH_TEST)

class toolScale(object):
	def __init__(self, parent):
		self.parent = parent
		self.node = None
		self.scale = None

	def _pointDist(self, p0, p1, p2):
		return numpy.linalg.norm(numpy.cross((p0 - p1), (p0 - p2))) / numpy.linalg.norm(p2 - p1)

	def _traceNodes(self, p0, p1):
		s = self._nodeSize()
		if self._pointDist(numpy.array([0,0,0],numpy.float32), p0, p1) < s * 2:
			return 1
		if self._pointDist(numpy.array([s*15,0,0],numpy.float32), p0, p1) < s * 2:
			return 2
		if self._pointDist(numpy.array([0,s*15,0],numpy.float32), p0, p1) < s * 2:
			return 3
		if self._pointDist(numpy.array([0,0,s*15],numpy.float32), p0, p1) < s * 2:
			return 4
		return None

	def _lineLineCrossingDistOnLine(self, s0, e0, s1, e1):
		d0 = e0 - s0
		d1 = e1 - s1
		a = numpy.dot(d0, d0)
		b = numpy.dot(d0, d1)
		e = numpy.dot(d1, d1)
		d = a*e - b*b

		r = s0 - s1
		c = numpy.dot(d0, r)
		f = numpy.dot(d1, r)

		s = (b*f - c*e) / d
		t = (a*f - b*c) / d
		return t

	def _nodeSize(self):
		return float(self.parent._zoom) / float(self.parent.GetSize().GetWidth()) * 6.0

	def OnMouseMove(self, p0, p1):
		self.node = self._traceNodes(p0, p1)

	def OnDragStart(self, p0, p1):
		if self.node is None:
			return False
		return True

	def OnDrag(self, p0, p1):
		s = self._nodeSize()
		endPoint = [1,1,1]
		if self.node == 2:
			endPoint = [1,0,0]
		elif self.node == 3:
			endPoint = [0,1,0]
		elif self.node == 4:
			endPoint = [0,0,1]
		scale = self._lineLineCrossingDistOnLine(p0, p1, numpy.array([0,0,0], numpy.float32), numpy.array(endPoint, numpy.float32)) / 15.0 / s
		if not wx.GetKeyState(wx.WXK_SHIFT):
			objMatrix = self.parent.getObjectMatrix()
			scaleX = numpy.linalg.norm(objMatrix[::,0].getA().flatten())
			scaleY = numpy.linalg.norm(objMatrix[::,1].getA().flatten())
			scaleZ = numpy.linalg.norm(objMatrix[::,2].getA().flatten())
			if self.node == 1 or not wx.GetKeyState(wx.WXK_CONTROL):
				matrixScale = (scaleX + scaleY + scaleZ) / 3
			elif self.node == 2:
				matrixScale = scaleX
			elif self.node == 3:
				matrixScale = scaleY
			elif self.node == 4:
				matrixScale = scaleZ
			scale = (round((matrixScale * scale) * 10) / 10) / matrixScale
		if scale < 0:
			scale = -scale
		if scale < 0.1:
			scale = 0.1
		self.scale = scale
		if self.node == 1 or not wx.GetKeyState(wx.WXK_CONTROL):
			self.parent.tempMatrix = numpy.matrix([[scale,0,0], [0, scale, 0], [0, 0, scale]], numpy.float64)
		elif self.node == 2:
			self.parent.tempMatrix = numpy.matrix([[scale,0,0], [0, 1, 0], [0, 0, 1]], numpy.float64)
		elif self.node == 3:
			self.parent.tempMatrix = numpy.matrix([[1,0,0], [0, scale, 0], [0, 0, 1]], numpy.float64)
		elif self.node == 4:
			self.parent.tempMatrix = numpy.matrix([[1,0,0], [0, 1, 0], [0, 0, scale]], numpy.float64)

	def OnDragEnd(self):
		self.scale = None

	def OnDraw(self):
		s = self._nodeSize()
		sx = s*15
		sy = s*15
		sz = s*15
		if self.node == 2 and self.scale is not None:
			sx *= self.scale
		if self.node == 3 and self.scale is not None:
			sy *= self.scale
		if self.node == 4 and self.scale is not None:
			sz *= self.scale
		objMatrix = self.parent.getObjectMatrix()
		scaleX = numpy.linalg.norm(objMatrix[::,0].getA().flatten())
		scaleY = numpy.linalg.norm(objMatrix[::,1].getA().flatten())
		scaleZ = numpy.linalg.norm(objMatrix[::,2].getA().flatten())
		if self.scale is not None:
			scaleX *= self.scale
			scaleY *= self.scale
			scaleZ *= self.scale

		glDisable(GL_LIGHTING)
		glDisable(GL_DEPTH_TEST)
		glEnable(GL_BLEND)
		glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

		glColor3ub(0,0,0)
		size = self.parent.getObjectSize()
		radius = self.parent.getObjectBoundaryCircle()
		if self.scale is not None:
			radius *= self.scale
		glPushMatrix()
		glTranslate(0,0,size[2]/2 + 5)
		glRotate(-self.parent._yaw, 0,0,1)
		if self.parent._pitch < 80:
			glTranslate(0, radius + 5,0)
		elif self.parent._pitch < 100:
			glTranslate(0, (radius + 5) * (90 - self.parent._pitch) / 10,0)
		else:
			glTranslate(0,-(radius + 5),0)
		if self.parent.tempMatrix is not None:
			size = (numpy.matrix([size]) * self.parent.tempMatrix).getA().flatten()
		openglHelpers.glDrawStringCenter("W, D, H: %0.1f, %0.1f, %0.1f mm" % (size[0], size[1], size[2]))
		glPopMatrix()

		glLineWidth(1)
		glBegin(GL_LINES)
		glColor3ub(128,0,0)
		glVertex3f(0, 0, 0)
		glVertex3f(sx, 0, 0)
		glColor3ub(0,128,0)
		glVertex3f(0, 0, 0)
		glVertex3f(0, sy, 0)
		glColor3ub(0,0,128)
		glVertex3f(0, 0, 0)
		glVertex3f(0, 0, sz)
		glEnd()

		glLineWidth(2)
		if self.node == 1:
			glColor3ub(255,255,255)
		else:
			glColor3ub(192,192,192)
		openglHelpers.DrawBox([-s,-s,-s], [s,s,s])
		if self.node == 1:
			glColor3ub(0,0,0)
			openglHelpers.glDrawStringCenter("%0.2f" % ((scaleX + scaleY + scaleZ) / 3.0))

		if self.node == 2:
			glColor3ub(255,64,64)
		else:
			glColor3ub(128,0,0)
		glPushMatrix()
		glTranslatef(sx,0,0)
		openglHelpers.DrawBox([-s,-s,-s], [s,s,s])
		if self.node == 2:
			glColor3ub(0,0,0)
			openglHelpers.glDrawStringCenter("%0.2f" % (scaleX))
		glPopMatrix()
		if self.node == 3:
			glColor3ub(64,255,64)
		else:
			glColor3ub(0,128,0)
		glPushMatrix()
		glTranslatef(0,sy,0)
		openglHelpers.DrawBox([-s,-s,-s], [s,s,s])
		if self.node == 3:
			glColor3ub(0,0,0)
			openglHelpers.glDrawStringCenter("%0.2f" % (scaleY))
		glPopMatrix()
		if self.node == 4:
			glColor3ub(64,64,255)
		else:
			glColor3ub(0,0,128)
		glPushMatrix()
		glTranslatef(0,0,sz)
		openglHelpers.DrawBox([-s,-s,-s], [s,s,s])
		if self.node == 4:
			glColor3ub(0,0,0)
			openglHelpers.glDrawStringCenter("%0.2f" % (scaleZ))
		glPopMatrix()

		glEnable(GL_DEPTH_TEST)
		glColor(255,255,255)
		size = size / 2
		size += 0.01
		glLineWidth(1)
		glBegin(GL_LINES)
		glVertex3f(size[0], size[1], size[2])
		glVertex3f(size[0], size[1], size[2]/4*3)
		glVertex3f(size[0], size[1], size[2])
		glVertex3f(size[0], size[1]/4*3, size[2])
		glVertex3f(size[0], size[1], size[2])
		glVertex3f(size[0]/4*3, size[1], size[2])

		glVertex3f(-size[0], size[1], size[2])
		glVertex3f(-size[0], size[1], size[2]/4*3)
		glVertex3f(-size[0], size[1], size[2])
		glVertex3f(-size[0], size[1]/4*3, size[2])
		glVertex3f(-size[0], size[1], size[2])
		glVertex3f(-size[0]/4*3, size[1], size[2])

		glVertex3f(size[0], -size[1], size[2])
		glVertex3f(size[0], -size[1], size[2]/4*3)
		glVertex3f(size[0], -size[1], size[2])
		glVertex3f(size[0], -size[1]/4*3, size[2])
		glVertex3f(size[0], -size[1], size[2])
		glVertex3f(size[0]/4*3, -size[1], size[2])

		glVertex3f(-size[0], -size[1], size[2])
		glVertex3f(-size[0], -size[1], size[2]/4*3)
		glVertex3f(-size[0], -size[1], size[2])
		glVertex3f(-size[0], -size[1]/4*3, size[2])
		glVertex3f(-size[0], -size[1], size[2])
		glVertex3f(-size[0]/4*3, -size[1], size[2])

		glVertex3f(size[0], size[1], -size[2])
		glVertex3f(size[0], size[1], -size[2]/4*3)
		glVertex3f(size[0], size[1], -size[2])
		glVertex3f(size[0], size[1]/4*3, -size[2])
		glVertex3f(size[0], size[1], -size[2])
		glVertex3f(size[0]/4*3, size[1], -size[2])

		glVertex3f(-size[0], size[1], -size[2])
		glVertex3f(-size[0], size[1], -size[2]/4*3)
		glVertex3f(-size[0], size[1], -size[2])
		glVertex3f(-size[0], size[1]/4*3, -size[2])
		glVertex3f(-size[0], size[1], -size[2])
		glVertex3f(-size[0]/4*3, size[1], -size[2])

		glVertex3f(size[0], -size[1], -size[2])
		glVertex3f(size[0], -size[1], -size[2]/4*3)
		glVertex3f(size[0], -size[1], -size[2])
		glVertex3f(size[0], -size[1]/4*3, -size[2])
		glVertex3f(size[0], -size[1], -size[2])
		glVertex3f(size[0]/4*3, -size[1], -size[2])

		glVertex3f(-size[0], -size[1], -size[2])
		glVertex3f(-size[0], -size[1], -size[2]/4*3)
		glVertex3f(-size[0], -size[1], -size[2])
		glVertex3f(-size[0], -size[1]/4*3, -size[2])
		glVertex3f(-size[0], -size[1], -size[2])
		glVertex3f(-size[0]/4*3, -size[1], -size[2])
		glEnd()

		glEnable(GL_DEPTH_TEST)

########NEW FILE########
__FILENAME__ = taskbar
"""
Api for taskbar. Only for windows 7 or higher (filling up the icon while its progressing).
"""
__copyright__ = "Copyright (C) 2013 David Braam - Released under terms of the AGPLv3 License"

try:
	import comtypes.client as cc
	cc.GetModule('taskbarlib.tlb')
	import comtypes.gen.TaskbarLib as tbl

	ITaskbarList3 = cc.CreateObject("{56FDF344-FD6D-11d0-958A-006097C9A090}", interface=tbl.ITaskbarList3)
	ITaskbarList3.HrInit()

	#Stops displaying progress and returns the button to its normal state. Call this method with this flag to dismiss the progress bar when the operation is complete or canceled.
	TBPF_NOPROGRESS = 0x00000000
	#The progress indicator does not grow in size, but cycles repeatedly along the length of the taskbar button. This indicates activity without specifying what proportion of the progress is complete. Progress is taking place, but there is no prediction as to how long the operation will take.
	TBPF_INDETERMINATE = 0x00000001
	#The progress indicator grows in size from left to right in proportion to the estimated amount of the operation completed. This is a determinate progress indicator; a prediction is being made as to the duration of the operation.
	TBPF_NORMAL = 0x00000002
	#The progress indicator turns red to show that an error has occurred in one of the windows that is broadcasting progress. This is a determinate state. If the progress indicator is in the indeterminate state, it switches to a red determinate display of a generic percentage not indicative of actual progress.
	TBPF_ERROR = 0x00000004
	#The progress indicator turns yellow to show that progress is currently stopped in one of the windows but can be resumed by the user. No error condition exists and nothing is preventing the progress from continuing. This is a determinate state. If the progress indicator is in the indeterminate state, it switches to a yellow determinate display of a generic percentage not indicative of actual progress.
	TBPF_PAUSED = 0x00000008
except:
	#The taskbar API is only available for Windows7, on lower windows versions, linux or Mac it will cause an exception. Ignore the exception and don't use the API
	ITaskbarList3 = None

def setBusy(frame, busy):
	if ITaskbarList3 is not None:
		if busy:
			ITaskbarList3.SetProgressState(frame.GetHandle(), TBPF_INDETERMINATE)
		else:
			ITaskbarList3.SetProgressState(frame.GetHandle(), TBPF_NOPROGRESS)

def setPause(frame, pause):
	if ITaskbarList3 is not None:
		if pause:
			ITaskbarList3.SetProgressState(frame.GetHandle(), TBPF_PAUSED)
		else:
			ITaskbarList3.SetProgressState(frame.GetHandle(), TBPF_NORMAL)

def setProgress(frame, done, total):
	if ITaskbarList3 is not None:
		ITaskbarList3.SetProgressState(frame.GetHandle(), TBPF_NORMAL)
		ITaskbarList3.SetProgressValue(frame.GetHandle(), done, total)

########NEW FILE########
__FILENAME__ = webcam
__copyright__ = "Copyright (C) 2013 David Braam - Released under terms of the AGPLv3 License"

import os
import glob
import subprocess
import platform

import wx

from Cura.util import profile
from Cura.util.resources import getPathForImage

try:
	#Try to find the OpenCV library for video capture.
	from opencv import cv
	from opencv import highgui
except:
	cv = None

try:
	#Use the vidcap library directly from the VideoCapture package. (Windows only)
	#	http://videocapture.sourceforge.net/
	# We're using the binary interface, not the python interface, so we don't depend on PIL
	import vidcap as win32vidcap
except:
	win32vidcap = None

def hasWebcamSupport():
	if cv is None and win32vidcap is None:
		return False
	if not os.path.exists(getFFMPEGpath()):
		return False
	return True


def getFFMPEGpath():
	if platform.system() == "Windows":
		return os.path.normpath(os.path.join(os.path.split(__file__)[0], "../../ffmpeg.exe"))
	elif os.path.exists('/usr/bin/ffmpeg'):
		return '/usr/bin/ffmpeg'
	return os.path.normpath(os.path.join(os.path.split(__file__)[0], "../../ffmpeg"))


class webcam(object):
	def __init__(self):
		self._cam = None
		self._cameraList = None
		self._activeId = -1
		self._overlayImage = wx.Bitmap(getPathForImage('cura-overlay.png'))
		self._overlayUltimaker = wx.Bitmap(getPathForImage('ultimaker-overlay.png'))
		self._doTimelapse = False
		self._bitmap = None

		#open the camera and close it to check if we have a camera, then open the camera again when we use it for the
		# first time.
		cameraList = []
		tryNext = True
		self._camId = 0
		while tryNext:
			tryNext = False
			self._openCam()
			if self._cam is not None:
				cameraList.append(self._cam.getdisplayname())
				tryNext = True
				del self._cam
				self._cam = None
				self._camId += 1
		self._camId = 0
		self._activeId = -1
		self._cameraList = cameraList

	def hasCamera(self):
		return len(self._cameraList) > 0

	def listCameras(self):
		return self._cameraList

	def setActiveCamera(self, cameraIdx):
		self._camId = cameraIdx

	def _openCam(self):
		if self._cameraList is not None and self._camId >= len(self._cameraList):
			return False
		if self._cam is not None:
			if self._activeId != self._camId:
				del self._cam
				self._cam = None
			else:
				return True

		self._activeId = self._camId
		if cv is not None:
			self._cam = highgui.cvCreateCameraCapture(self._camId)
		elif win32vidcap is not None:
			try:
				self._cam = win32vidcap.new_Dev(self._camId, False)
			except:
				pass
		return self._cam is not None

	def propertyPages(self):
		if cv is not None:
			#TODO Make an OpenCV property page
			return []
		elif win32vidcap is not None:
			return ['Image properties', 'Format properties']

	def openPropertyPage(self, pageType=0):
		if not self._openCam():
			return
		if cv is not None:
			pass
		elif win32vidcap is not None:
			if pageType == 0:
				self._cam.displaycapturefilterproperties()
			else:
				del self._cam
				self._cam = None
				tmp = win32vidcap.new_Dev(0, False)
				tmp.displaycapturepinproperties()
				self._cam = tmp

	def takeNewImage(self, withOverlay = True):
		if not self._openCam():
			return
		if cv is not None:
			frame = cv.QueryFrame(self._cam)
			cv.CvtColor(frame, frame, cv.CV_BGR2RGB)
			bitmap = wx.BitmapFromBuffer(frame.width, frame.height, frame.imageData)
		elif win32vidcap is not None:
			buffer, width, height = self._cam.getbuffer()
			try:
				wxImage = wx.EmptyImage(width, height)
				wxImage.SetData(buffer[::-1])
				wxImage = wxImage.Mirror()
				if self._bitmap is not None:
					del self._bitmap
				bitmap = wxImage.ConvertToBitmap()
				del wxImage
				del buffer
			except:
				pass

		if withOverlay:
			dc = wx.MemoryDC()
			dc.SelectObject(bitmap)
			dc.DrawBitmap(self._overlayImage, bitmap.GetWidth() - self._overlayImage.GetWidth() - 5, 5, True)
			if profile.getMachineSetting('machine_type').startswith('ultimaker'):
				dc.DrawBitmap(self._overlayUltimaker, (bitmap.GetWidth() - self._overlayUltimaker.GetWidth()) / 2,
					bitmap.GetHeight() - self._overlayUltimaker.GetHeight() - 5, True)
			dc.SelectObject(wx.NullBitmap)

		self._bitmap = bitmap

		if self._doTimelapse:
			filename = os.path.normpath(os.path.join(os.path.split(__file__)[0], "../__tmp_snap",
				"__tmp_snap_%04d.jpg" % (self._snapshotCount)))
			self._snapshotCount += 1
			bitmap.SaveFile(filename, wx.BITMAP_TYPE_JPEG)

		return self._bitmap

	def getLastImage(self):
		return self._bitmap

	def startTimelapse(self, filename):
		if not self._openCam():
			return
		self._cleanTempDir()
		self._timelapseFilename = filename
		self._snapshotCount = 0
		self._doTimelapse = True
		print "startTimelapse"

	def endTimelapse(self):
		if self._doTimelapse:
			ffmpeg = getFFMPEGpath()
			basePath = os.path.normpath(
				os.path.join(os.path.split(__file__)[0], "../__tmp_snap", "__tmp_snap_%04d.jpg"))
			subprocess.call(
				[ffmpeg, '-r', '12.5', '-i', basePath, '-vcodec', 'mpeg2video', '-pix_fmt', 'yuv420p', '-r', '25', '-y',
				 '-b:v', '1500k', '-f', 'vob', self._timelapseFilename])
		self._doTimelapse = False

	def _cleanTempDir(self):
		basePath = os.path.normpath(os.path.join(os.path.split(__file__)[0], "../__tmp_snap"))
		try:
			os.makedirs(basePath)
		except:
			pass
		for filename in glob.iglob(basePath + "/*.jpg"):
			os.remove(filename)

########NEW FILE########
__FILENAME__ = serialCommunication
"""
Serial communication with the printer for printing is done from a separate process,
this to ensure that the PIL does not block the serial printing.

This file is the 2nd process that is started to handle communication with the printer.
And handles all communication with the initial process.
"""

__copyright__ = "Copyright (C) 2013 David Braam - Released under terms of the AGPLv3 License"
import sys
import time
import os
import json

from Cura.util import machineCom

class serialComm(object):
	"""
	The serialComm class is the interface class which handles the communication between stdin/stdout and the machineCom class.
	This interface class is used to run the (USB) serial communication in a different process then the GUI.
	"""
	def __init__(self, portName, baudrate):
		self._comm = None
		self._gcodeList = []

		try:
			baudrate = int(baudrate)
		except ValueError:
			baudrate = 0
		self._comm = machineCom.MachineCom(portName, baudrate, callbackObject=self)

	def mcLog(self, message):
		sys.stdout.write('log:%s\n' % (message))

	def mcTempUpdate(self, temp, bedTemp, targetTemp, bedTargetTemp):
		sys.stdout.write('temp:%s:%s:%f:%f\n' % (json.dumps(temp), json.dumps(targetTemp), bedTemp, bedTargetTemp))

	def mcStateChange(self, state):
		if self._comm is None:
			return
		sys.stdout.write('state:%d:%s\n' % (state, self._comm.getStateString()))

	def mcMessage(self, message):
		sys.stdout.write('message:%s\n' % (message))

	def mcProgress(self, lineNr):
		sys.stdout.write('progress:%d\n' % (lineNr))

	def mcZChange(self, newZ):
		sys.stdout.write('changeZ:%d\n' % (newZ))

	def monitorStdin(self):
		while not self._comm.isClosed():
			line = sys.stdin.readline().strip()
			line = line.split(':', 1)
			if line[0] == 'STOP':
				self._comm.cancelPrint()
				self._gcodeList = ['M110']
			elif line[0] == 'G':
				self._gcodeList.append(line[1])
			elif line[0] == 'C':
				self._comm.sendCommand(line[1])
			elif line[0] == 'START':
				self._comm.printGCode(self._gcodeList)
			else:
				sys.stderr.write(str(line))

def startMonitor(portName, baudrate):
	sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 0)
	comm = serialComm(portName, baudrate)
	comm.monitorStdin()

def main():
	if len(sys.argv) != 3:
		return
	portName, baudrate = sys.argv[1], sys.argv[2]
	startMonitor(portName, baudrate)

if __name__ == '__main__':
	main()

########NEW FILE########
__FILENAME__ = explorer
"""
Simple utility module to open "explorer" file dialogs.
The name "explorer" comes from the windows file explorer, which is called explorer.
"""
__copyright__ = "Copyright (C) 2013 David Braam - Released under terms of the AGPLv3 License"

import sys
import os
import subprocess

def hasExplorer():
	"""Check if we have support for opening file dialog windows."""
	if sys.platform == 'win32' or sys.platform == 'cygwin' or sys.platform == 'darwin':
		return True
	if sys.platform == 'linux2':
		if os.path.isfile('/usr/bin/nautilus'):
			return True
		if os.path.isfile('/usr/bin/dolphin'):
			return True
	return False

def openExplorer(filename):
	"""Open an file dialog window in the directory of a file, and select the file."""
	if sys.platform == 'win32' or sys.platform == 'cygwin':
		subprocess.Popen(r'explorer /select,"%s"' % (filename))
	if sys.platform == 'darwin':
		subprocess.Popen(['open', '-R', filename])
	if sys.platform.startswith('linux'):
		#TODO: On linux we cannot seem to select a certain file, only open the specified path.
		if os.path.isfile('/usr/bin/nautilus'):
			subprocess.Popen(['/usr/bin/nautilus', os.path.split(filename)[0]])
		elif os.path.isfile('/usr/bin/dolphin'):
			subprocess.Popen(['/usr/bin/dolphin', os.path.split(filename)[0]])

def openExplorerPath(filename):
	"""Open a file dialog inside a directory, without selecting any file."""
	if sys.platform == 'win32' or sys.platform == 'cygwin':
		subprocess.Popen(r'explorer "%s"' % (filename))
	if sys.platform == 'darwin':
		subprocess.Popen(['open', filename])
	if sys.platform.startswith('linux'):
		if os.path.isfile('/usr/bin/nautilus'):
			subprocess.Popen(['/usr/bin/nautilus', filename])
		elif os.path.isfile('/usr/bin/dolphin'):
			subprocess.Popen(['/usr/bin/dolphin', filename])


########NEW FILE########
__FILENAME__ = gcodeGenerator
"""
A simple generator for GCode. To assist in creation of simple GCode instructions.
This is not intended for advanced use or complex paths. The CuraEngine generates the real GCode instructions.
"""
__copyright__ = "Copyright (C) 2013 David Braam - Released under terms of the AGPLv3 License"

import math

from Cura.util import profile

class gcodeGenerator(object):
	"""
	Generates a simple set of GCode commands for RepRap GCode firmware.
	Use the add* commands to build the GCode, and then use the list function to retrieve the resulting gcode.
	"""
	def __init__(self):
		self._feedPrint = profile.getProfileSettingFloat('print_speed') * 60
		self._feedTravel = profile.getProfileSettingFloat('travel_speed') * 60
		self._feedRetract = profile.getProfileSettingFloat('retraction_speed') * 60
		filamentRadius = profile.getProfileSettingFloat('filament_diameter') / 2
		filamentArea = math.pi * filamentRadius * filamentRadius
		self._ePerMM = (profile.getProfileSettingFloat('nozzle_size') * 0.1) / filamentArea
		self._eValue = 0.0
		self._x = 0
		self._y = 0
		self._z = 0

		self._list = ['M110', 'G92 E0']

	def setPrintSpeed(self, speed):
		self._feedPrint = speed * 60

	def setExtrusionRate(self, lineWidth, layerHeight):
		filamentRadius = profile.getProfileSettingFloat('filament_diameter') / 2
		filamentArea = math.pi * filamentRadius * filamentRadius
		self._ePerMM = (lineWidth * layerHeight) / filamentArea

	def home(self):
		self._x = 0
		self._y = 0
		self._z = 0
		self._list += ['G28']

	def addMove(self, x=None, y=None, z=None):
		cmd = "G0 "
		if x is not None:
			cmd += "X%f " % (x)
			self._x = x
		if y is not None:
			cmd += "Y%f " % (y)
			self._y = y
		if z is not None:
			cmd += "Z%f " % (z)
			self._z = z
		cmd += "F%d" % (self._feedTravel)
		self._list += [cmd]

	def addPrime(self, amount=5):
		self._eValue += amount
		self._list += ['G1 E%f F%f' % (self._eValue, self._feedRetract)]

	def addRetract(self, amount=5):
		self._eValue -= amount
		self._list += ['G1 E%f F%f' % (self._eValue, self._feedRetract)]

	def _addExtrude(self, x=None, y=None, z=None):
		cmd = "G1 "
		oldX = self._x
		oldY = self._y
		if x is not None:
			cmd += "X%f " % (x)
			self._x = x
		if y is not None:
			cmd += "Y%f " % (y)
			self._y = y
		if z is not None:
			cmd += "Z%f " % (z)
			self._z = z
		self._eValue += math.sqrt((self._x - oldX) * (self._x - oldX) + (self._y - oldY) * (self._y - oldY)) * self._ePerMM
		cmd += "E%f F%d" % (self._eValue, self._feedPrint)
		self._list += [cmd]

	def addExtrude(self, x=None, y=None, z=None):
		if x is not None and abs(self._x - x) > 10:
			self.addExtrude((self._x + x) / 2.0, y, z)
			self.addExtrude(x, y, z)
			return
		if y is not None and abs(self._y - y) > 10:
			self.addExtrude(x, (self._y + y) / 2.0, z)
			self.addExtrude(x, y, z)
			return
		self._addExtrude(x, y, z)

	def addHome(self):
		self._list += ['G28']

	def addCmd(self, cmd):
		self._list += [cmd]

	def list(self):
		return self._list
########NEW FILE########
__FILENAME__ = gcodeInterpreter
"""
The GCodeInterpreter module generates layer information from GCode.
It does this by parsing the whole GCode file. On large files this can take a while and should be used from a thread.
"""
__copyright__ = "Copyright (C) 2013 David Braam - Released under terms of the AGPLv3 License"

import sys
import math
import os
import time
import numpy
import types
import cStringIO as StringIO

from Cura.util import profile

def gcodePath(newType, pathType, layerThickness, startPoint):
	"""
	Build a gcodePath object. This used to be objects, however, this code is timing sensitive and dictionaries proved to be faster.
	"""
	if layerThickness <= 0.0:
		layerThickness = 0.01
	if profile.getProfileSetting('spiralize') == 'True':
		layerThickness = profile.getProfileSettingFloat('layer_height')
	return {'type': newType,
			'pathType': pathType,
			'layerThickness': layerThickness,
			'points': [startPoint],
			'extrusion': [0.0]}

class gcode(object):
	"""
	The heavy lifting GCode parser. This is most likely the hardest working python code in Cura.
	It parses a GCode file and stores the result in layers where each layer as paths that describe the GCode.
	"""
	def __init__(self):
		self.regMatch = {}
		self.layerList = None
		self.extrusionAmount = 0
		self.filename = None
		self.progressCallback = None
	
	def load(self, data):
		self.filename = None
		if type(data) in types.StringTypes and os.path.isfile(data):
			self.filename = data
			self._fileSize = os.stat(data).st_size
			gcodeFile = open(data, 'r')
			self._load(gcodeFile)
			gcodeFile.close()
		elif type(data) is list:
			self._load(data)
		else:
			data = data.getvalue()
			self._fileSize = len(data)
			self._load(StringIO.StringIO(data))

	def calculateWeight(self):
		#Calculates the weight of the filament in kg
		radius = float(profile.getProfileSetting('filament_diameter')) / 2
		volumeM3 = (self.extrusionAmount * (math.pi * radius * radius)) / (1000*1000*1000)
		return volumeM3 * profile.getPreferenceFloat('filament_physical_density')
	
	def calculateCost(self):
		cost_kg = profile.getPreferenceFloat('filament_cost_kg')
		cost_meter = profile.getPreferenceFloat('filament_cost_meter')
		if cost_kg > 0.0 and cost_meter > 0.0:
			return "%.2f / %.2f" % (self.calculateWeight() * cost_kg, self.extrusionAmount / 1000 * cost_meter)
		elif cost_kg > 0.0:
			return "%.2f" % (self.calculateWeight() * cost_kg)
		elif cost_meter > 0.0:
			return "%.2f" % (self.extrusionAmount / 1000 * cost_meter)
		return None
	
	def _load(self, gcodeFile):
		self.layerList = []
		pos = [0.0,0.0,0.0]
		posOffset = [0.0, 0.0, 0.0]
		currentE = 0.0
		currentExtruder = 0
		extrudeAmountMultiply = 1.0
		absoluteE = True
		scale = 1.0
		posAbs = True
		feedRate = 3600.0
		moveType = 'move'
		layerThickness = 0.1
		pathType = 'CUSTOM'
		currentLayer = []
		currentPath = gcodePath('move', pathType, layerThickness, pos)
		currentPath['extruder'] = currentExtruder

		currentLayer.append(currentPath)
		for line in gcodeFile:
			if type(line) is tuple:
				line = line[0]

			#Parse Cura_SF comments
			if line.startswith(';TYPE:'):
				pathType = line[6:].strip()

			if ';' in line:
				comment = line[line.find(';')+1:].strip()
				#Slic3r GCode comment parser
				if comment == 'fill':
					pathType = 'FILL'
				elif comment == 'perimeter':
					pathType = 'WALL-INNER'
				elif comment == 'skirt':
					pathType = 'SKIRT'
				#Cura layer comments.
				if comment.startswith('LAYER:'):
					currentPath = gcodePath(moveType, pathType, layerThickness, currentPath['points'][-1])
					layerThickness = 0.0
					currentPath['extruder'] = currentExtruder
					for path in currentLayer:
						path['points'] = numpy.array(path['points'], numpy.float32)
						path['extrusion'] = numpy.array(path['extrusion'], numpy.float32)
					self.layerList.append(currentLayer)
					if self.progressCallback is not None:
						if self.progressCallback(float(gcodeFile.tell()) / float(self._fileSize)):
							#Abort the loading, we can safely return as the results here will be discarded
							gcodeFile.close()
							return
					currentLayer = [currentPath]
				line = line[0:line.find(';')]
			T = getCodeInt(line, 'T')
			if T is not None:
				if currentExtruder > 0:
					posOffset[0] -= profile.getMachineSettingFloat('extruder_offset_x%d' % (currentExtruder))
					posOffset[1] -= profile.getMachineSettingFloat('extruder_offset_y%d' % (currentExtruder))
				currentExtruder = T
				if currentExtruder > 0:
					posOffset[0] += profile.getMachineSettingFloat('extruder_offset_x%d' % (currentExtruder))
					posOffset[1] += profile.getMachineSettingFloat('extruder_offset_y%d' % (currentExtruder))
			
			G = getCodeInt(line, 'G')
			if G is not None:
				if G == 0 or G == 1:	#Move
					x = getCodeFloat(line, 'X')
					y = getCodeFloat(line, 'Y')
					z = getCodeFloat(line, 'Z')
					e = getCodeFloat(line, 'E')
					#f = getCodeFloat(line, 'F')
					oldPos = pos
					pos = pos[:]
					if posAbs:
						if x is not None:
							pos[0] = x * scale + posOffset[0]
						if y is not None:
							pos[1] = y * scale + posOffset[1]
						if z is not None:
							pos[2] = z * scale + posOffset[2]
					else:
						if x is not None:
							pos[0] += x * scale
						if y is not None:
							pos[1] += y * scale
						if z is not None:
							pos[2] += z * scale
					moveType = 'move'
					if e is not None:
						if absoluteE:
							e -= currentE
						if e > 0.0:
							moveType = 'extrude'
						if e < 0.0:
							moveType = 'retract'
						currentE += e
					else:
						e = 0.0
					if moveType == 'move' and oldPos[2] != pos[2]:
						if oldPos[2] > pos[2] and abs(oldPos[2] - pos[2]) > 5.0 and pos[2] < 1.0:
							oldPos[2] = 0.0
						if layerThickness == 0.0:
							layerThickness = abs(oldPos[2] - pos[2])
					if currentPath['type'] != moveType or currentPath['pathType'] != pathType:
						currentPath = gcodePath(moveType, pathType, layerThickness, currentPath['points'][-1])
						currentPath['extruder'] = currentExtruder
						currentLayer.append(currentPath)

					currentPath['points'].append(pos)
					currentPath['extrusion'].append(e * extrudeAmountMultiply)
				elif G == 4:	#Delay
					S = getCodeFloat(line, 'S')
					P = getCodeFloat(line, 'P')
				elif G == 10:	#Retract
					currentPath = gcodePath('retract', pathType, layerThickness, currentPath['points'][-1])
					currentPath['extruder'] = currentExtruder
					currentLayer.append(currentPath)
					currentPath['points'].append(currentPath['points'][0])
				elif G == 11:	#Push back after retract
					pass
				elif G == 20:	#Units are inches
					scale = 25.4
				elif G == 21:	#Units are mm
					scale = 1.0
				elif G == 28:	#Home
					x = getCodeFloat(line, 'X')
					y = getCodeFloat(line, 'Y')
					z = getCodeFloat(line, 'Z')
					center = [0.0,0.0,0.0]
					if x is None and y is None and z is None:
						pos = center
					else:
						pos = pos[:]
						if x is not None:
							pos[0] = center[0]
						if y is not None:
							pos[1] = center[1]
						if z is not None:
							pos[2] = center[2]
				elif G == 90:	#Absolute position
					posAbs = True
				elif G == 91:	#Relative position
					posAbs = False
				elif G == 92:
					x = getCodeFloat(line, 'X')
					y = getCodeFloat(line, 'Y')
					z = getCodeFloat(line, 'Z')
					e = getCodeFloat(line, 'E')
					if e is not None:
						currentE = e
					#if x is not None:
					#	posOffset[0] = pos[0] - x
					#if y is not None:
					#	posOffset[1] = pos[1] - y
					#if z is not None:
					#	posOffset[2] = pos[2] - z
				else:
					print "Unknown G code:" + str(G)
			else:
				M = getCodeInt(line, 'M')
				if M is not None:
					if M == 0:	#Message with possible wait (ignored)
						pass
					elif M == 1:	#Message with possible wait (ignored)
						pass
					elif M == 25:	#Stop SD printing
						pass
					elif M == 80:	#Enable power supply
						pass
					elif M == 81:	#Suicide/disable power supply
						pass
					elif M == 82:   #Absolute E
						absoluteE = True
					elif M == 83:   #Relative E
						absoluteE = False
					elif M == 84:	#Disable step drivers
						pass
					elif M == 92:	#Set steps per unit
						pass
					elif M == 101:	#Enable extruder
						pass
					elif M == 103:	#Disable extruder
						pass
					elif M == 104:	#Set temperature, no wait
						pass
					elif M == 105:	#Get temperature
						pass
					elif M == 106:	#Enable fan
						pass
					elif M == 107:	#Disable fan
						pass
					elif M == 108:	#Extruder RPM (these should not be in the final GCode, but they are)
						pass
					elif M == 109:	#Set temperature, wait
						pass
					elif M == 110:	#Reset N counter
						pass
					elif M == 113:	#Extruder PWM (these should not be in the final GCode, but they are)
						pass
					elif M == 117:	#LCD message
						pass
					elif M == 140:	#Set bed temperature
						pass
					elif M == 190:	#Set bed temperature & wait
						pass
					elif M == 221:	#Extrude amount multiplier
						s = getCodeFloat(line, 'S')
						if s is not None:
							extrudeAmountMultiply = s / 100.0
					else:
						print "Unknown M code:" + str(M)
		for path in currentLayer:
			path['points'] = numpy.array(path['points'], numpy.float32)
			path['extrusion'] = numpy.array(path['extrusion'], numpy.float32)
		self.layerList.append(currentLayer)
		if self.progressCallback is not None and self._fileSize > 0:
			self.progressCallback(float(gcodeFile.tell()) / float(self._fileSize))

def getCodeInt(line, code):
	n = line.find(code) + 1
	if n < 1:
		return None
	m = line.find(' ', n)
	try:
		if m < 0:
			return int(line[n:])
		return int(line[n:m])
	except:
		return None

def getCodeFloat(line, code):
	n = line.find(code) + 1
	if n < 1:
		return None
	m = line.find(' ', n)
	try:
		if m < 0:
			return float(line[n:])
		return float(line[n:m])
	except:
		return None

if __name__ == '__main__':
	t = time.time()
	for filename in sys.argv[1:]:
		g = gcode()
		g.load(filename)
	print time.time() - t


########NEW FILE########
__FILENAME__ = machineCom
"""
MachineCom handles communication with GCode based printers trough (USB) serial ports.
For actual printing of objects this module is used from Cura.serialCommunication and ran in a separate process.
"""
__copyright__ = "Copyright (C) 2013 David Braam - Released under terms of the AGPLv3 License"

import os
import glob
import sys
import time
import math
import re
import traceback
import threading
import platform
import Queue as queue

import serial

from Cura.avr_isp import stk500v2
from Cura.avr_isp import ispBase

from Cura.util import profile
from Cura.util import version

try:
	import _winreg
except:
	pass

def serialList(forAutoDetect=False):
	"""
		Retrieve a list of serial ports found in the system.
	:param forAutoDetect: if true then only the USB serial ports are listed. Else all ports are listed.
	:return: A list of strings where each string is a serial port.
	"""
	baselist=[]
	if platform.system() == "Windows":
		try:
			key=_winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE,"HARDWARE\\DEVICEMAP\\SERIALCOMM")
			i=0
			while True:
				values = _winreg.EnumValue(key, i)
				if not forAutoDetect or 'USBSER' in values[0]:
					baselist+=[values[1]]
				i+=1
		except:
			pass
	if forAutoDetect:
		baselist = baselist + glob.glob('/dev/ttyUSB*') + glob.glob('/dev/ttyACM*') + glob.glob("/dev/cu.usb*")
		baselist = filter(lambda s: not 'Bluetooth' in s, baselist)
		prev = profile.getMachineSetting('serial_port_auto')
		if prev in baselist:
			baselist.remove(prev)
			baselist.insert(0, prev)
	else:
		baselist = baselist + glob.glob('/dev/ttyUSB*') + glob.glob('/dev/ttyACM*') + glob.glob("/dev/cu.*") + glob.glob("/dev/tty.usb*") + glob.glob("/dev/rfcomm*") + glob.glob('/dev/serial/by-id/*')
	if version.isDevVersion() and not forAutoDetect:
		baselist.append('VIRTUAL')
	return baselist

def baudrateList():
	"""
	:return: a list of integers containing all possible baudrates at which we can communicate.
			Used for auto-baudrate detection as well as manual baudrate selection.
	"""
	ret = [250000, 230400, 115200, 57600, 38400, 19200, 9600]
	if profile.getMachineSetting('serial_baud_auto') != '':
		prev = int(profile.getMachineSetting('serial_baud_auto'))
		if prev in ret:
			ret.remove(prev)
			ret.insert(0, prev)
	return ret

class VirtualPrinter():
	"""
	A virtual printer class used for debugging. Acts as a serial.Serial class, but without connecting to any port.
	Only available when running the development version of Cura.
	"""
	def __init__(self):
		self.readList = ['start\n', 'Marlin: Virtual Marlin!\n', '\x80\n']
		self.temp = 0.0
		self.targetTemp = 0.0
		self.lastTempAt = time.time()
		self.bedTemp = 1.0
		self.bedTargetTemp = 1.0
	
	def write(self, data):
		if self.readList is None:
			return
		#print "Send: %s" % (data.rstrip())
		if 'M104' in data or 'M109' in data:
			try:
				self.targetTemp = float(re.search('S([0-9]+)', data).group(1))
			except:
				pass
		if 'M140' in data or 'M190' in data:
			try:
				self.bedTargetTemp = float(re.search('S([0-9]+)', data).group(1))
			except:
				pass
		if 'M105' in data:
			self.readList.append("ok T:%.2f /%.2f B:%.2f /%.2f @:64\n" % (self.temp, self.targetTemp, self.bedTemp, self.bedTargetTemp))
		elif len(data.strip()) > 0:
			self.readList.append("ok\n")

	def readline(self):
		if self.readList is None:
			return ''
		n = 0
		timeDiff = self.lastTempAt - time.time()
		self.lastTempAt = time.time()
		if abs(self.temp - self.targetTemp) > 1:
			self.temp += math.copysign(timeDiff * 10, self.targetTemp - self.temp)
		if abs(self.bedTemp - self.bedTargetTemp) > 1:
			self.bedTemp += math.copysign(timeDiff * 10, self.bedTargetTemp - self.bedTemp)
		while len(self.readList) < 1:
			time.sleep(0.1)
			n += 1
			if n == 20:
				return ''
			if self.readList is None:
				return ''
		time.sleep(0.001)
		#print "Recv: %s" % (self.readList[0].rstrip())
		return self.readList.pop(0)
	
	def close(self):
		self.readList = None

class MachineComPrintCallback(object):
	"""
	Base class for callbacks from the MachineCom class.
	This class has all empty implementations and is attached to the MachineCom if no other callback object is attached.
	"""
	def mcLog(self, message):
		pass
	
	def mcTempUpdate(self, temp, bedTemp, targetTemp, bedTargetTemp):
		pass
	
	def mcStateChange(self, state):
		pass
	
	def mcMessage(self, message):
		pass
	
	def mcProgress(self, lineNr):
		pass
	
	def mcZChange(self, newZ):
		pass

class MachineCom(object):
	"""
	Class for (USB) serial communication with 3D printers.
	This class keeps track of if the connection is still live, can auto-detect serial ports and baudrates.
	"""
	STATE_NONE = 0
	STATE_OPEN_SERIAL = 1
	STATE_DETECT_SERIAL = 2
	STATE_DETECT_BAUDRATE = 3
	STATE_CONNECTING = 4
	STATE_OPERATIONAL = 5
	STATE_PRINTING = 6
	STATE_PAUSED = 7
	STATE_CLOSED = 8
	STATE_ERROR = 9
	STATE_CLOSED_WITH_ERROR = 10
	
	def __init__(self, port = None, baudrate = None, callbackObject = None):
		if port is None:
			port = profile.getMachineSetting('serial_port')
		if baudrate is None:
			if profile.getMachineSetting('serial_baud') == 'AUTO':
				baudrate = 0
			else:
				baudrate = int(profile.getMachineSetting('serial_baud'))
		if callbackObject is None:
			callbackObject = MachineComPrintCallback()

		self._port = port
		self._baudrate = baudrate
		self._callback = callbackObject
		self._state = self.STATE_NONE
		self._serial = None
		self._serialDetectList = []
		self._baudrateDetectList = baudrateList()
		self._baudrateDetectRetry = 0
		self._extruderCount = int(profile.getMachineSetting('extruder_amount'))
		self._temperatureRequestExtruder = 0
		self._temp = [0] * self._extruderCount
		self._targetTemp = [0] * self._extruderCount
		self._bedTemp = 0
		self._bedTargetTemp = 0
		self._gcodeList = None
		self._gcodePos = 0
		self._commandQueue = queue.Queue()
		self._logQueue = queue.Queue(256)
		self._feedRateModifier = {}
		self._currentZ = -1
		self._heatupWaitStartTime = 0
		self._heatupWaitTimeLost = 0.0
		self._printStartTime100 = None
		
		self.thread = threading.Thread(target=self._monitor)
		self.thread.daemon = True
		self.thread.start()
	
	def _changeState(self, newState):
		if self._state == newState:
			return
		oldState = self.getStateString()
		self._state = newState
		self._log('Changing monitoring state from \'%s\' to \'%s\'' % (oldState, self.getStateString()))
		self._callback.mcStateChange(newState)
	
	def getState(self):
		return self._state
	
	def getStateString(self):
		if self._state == self.STATE_NONE:
			return "Offline"
		if self._state == self.STATE_OPEN_SERIAL:
			return "Opening serial port"
		if self._state == self.STATE_DETECT_SERIAL:
			return "Detecting serial port"
		if self._state == self.STATE_DETECT_BAUDRATE:
			return "Detecting baudrate"
		if self._state == self.STATE_CONNECTING:
			return "Connecting"
		if self._state == self.STATE_OPERATIONAL:
			return "Operational"
		if self._state == self.STATE_PRINTING:
			return "Printing"
		if self._state == self.STATE_PAUSED:
			return "Paused"
		if self._state == self.STATE_CLOSED:
			return "Closed"
		if self._state == self.STATE_ERROR:
			return "Error: %s" % (self.getShortErrorString())
		if self._state == self.STATE_CLOSED_WITH_ERROR:
			return "Error: %s" % (self.getShortErrorString())
		return "?%d?" % (self._state)
	
	def getShortErrorString(self):
		if len(self._errorValue) < 35:
			return self._errorValue
		return self._errorValue[:35] + "..."

	def getErrorString(self):
		return self._errorValue

	def isClosed(self):
		return self._state == self.STATE_CLOSED_WITH_ERROR or self._state == self.STATE_CLOSED

	def isClosedOrError(self):
		return self._state == self.STATE_ERROR or self._state == self.STATE_CLOSED_WITH_ERROR or self._state == self.STATE_CLOSED

	def isError(self):
		return self._state == self.STATE_ERROR or self._state == self.STATE_CLOSED_WITH_ERROR
	
	def isOperational(self):
		return self._state == self.STATE_OPERATIONAL or self._state == self.STATE_PRINTING or self._state == self.STATE_PAUSED
	
	def isPrinting(self):
		return self._state == self.STATE_PRINTING
	
	def isPaused(self):
		return self._state == self.STATE_PAUSED

	def getPrintPos(self):
		return self._gcodePos
	
	def getPrintTime(self):
		return time.time() - self._printStartTime

	def getPrintTimeRemainingEstimate(self):
		if self._printStartTime100 is None or self.getPrintPos() < 200:
			return None
		printTime = (time.time() - self._printStartTime100) / 60
		printTimeTotal = printTime * (len(self._gcodeList) - 100) / (self.getPrintPos() - 100)
		printTimeLeft = printTimeTotal - printTime
		return printTimeLeft
	
	def getTemp(self):
		return self._temp
	
	def getBedTemp(self):
		return self._bedTemp
	
	def getLog(self):
		ret = []
		while not self._logQueue.empty():
			ret.append(self._logQueue.get())
		for line in ret:
			self._logQueue.put(line, False)
		return ret
	
	def _monitor(self):
		#Open the serial port.
		if self._port == 'AUTO':
			self._changeState(self.STATE_DETECT_SERIAL)
			programmer = stk500v2.Stk500v2()
			for p in serialList(True):
				try:
					self._log("Connecting to: %s (programmer)" % (p))
					programmer.connect(p)
					self._serial = programmer.leaveISP()
					profile.putMachineSetting('serial_port_auto', p)
					break
				except ispBase.IspError as (e):
					self._log("Error while connecting to %s: %s" % (p, str(e)))
					pass
				except:
					self._log("Unexpected error while connecting to serial port: %s %s" % (p, getExceptionString()))
				programmer.close()
			if self._serial is None:
				self._log("Serial port list: %s" % (str(serialList(True))))
				self._serialDetectList = serialList(True)
		elif self._port == 'VIRTUAL':
			self._changeState(self.STATE_OPEN_SERIAL)
			self._serial = VirtualPrinter()
		else:
			self._changeState(self.STATE_OPEN_SERIAL)
			try:
				if self._baudrate == 0:
					self._log("Connecting to: %s with baudrate: 115200 (fallback)" % (self._port))
					self._serial = serial.Serial(str(self._port), 115200, timeout=3, writeTimeout=10000)
				else:
					self._log("Connecting to: %s with baudrate: %s (configured)" % (self._port, self._baudrate))
					self._serial = serial.Serial(str(self._port), self._baudrate, timeout=5, writeTimeout=10000)
			except:
				self._log("Unexpected error while connecting to serial port: %s %s" % (self._port, getExceptionString()))
		if self._serial is None:
			baudrate = self._baudrate
			if baudrate == 0:
				baudrate = self._baudrateDetectList.pop(0)
			if len(self._serialDetectList) < 1:
				self._log("Found no ports to try for auto detection")
				self._errorValue = 'Failed to autodetect serial port.'
				self._changeState(self.STATE_ERROR)
				return
			port = self._serialDetectList.pop(0)
			self._log("Connecting to: %s with baudrate: %s (auto)" % (port, baudrate))
			try:
				self._serial = serial.Serial(port, baudrate, timeout=3, writeTimeout=10000)
			except:
				pass
		else:
			self._log("Connected to: %s, starting monitor" % (self._serial))
			if self._baudrate == 0:
				self._changeState(self.STATE_DETECT_BAUDRATE)
			else:
				self._changeState(self.STATE_CONNECTING)

		#Start monitoring the serial port.
		if self._state == self.STATE_CONNECTING:
			timeout = time.time() + 15
		else:
			timeout = time.time() + 5
		tempRequestTimeout = timeout
		while True:
			line = self._readline()
			if line is None:
				break
			
			#No matter the state, if we see an fatal error, goto the error state and store the error for reference.
			# Only goto error on known fatal errors.
			if line.startswith('Error:'):
				#Oh YEAH, consistency.
				# Marlin reports an MIN/MAX temp error as "Error:x\n: Extruder switched off. MAXTEMP triggered !\n"
				#	But a bed temp error is reported as "Error: Temperature heated bed switched off. MAXTEMP triggered !!"
				#	So we can have an extra newline in the most common case. Awesome work people.
				if re.match('Error:[0-9]\n', line):
					line = line.rstrip() + self._readline()
				#Skip the communication errors, as those get corrected.
				if 'Extruder switched off' in line or 'Temperature heated bed switched off' in line or 'Something is wrong, please turn off the printer.' in line:
					if not self.isError():
						self._errorValue = line[6:]
						self._changeState(self.STATE_ERROR)
			if ' T:' in line or line.startswith('T:'):
				try:
					self._temp[self._temperatureRequestExtruder] = float(re.search("T: *([0-9\.]*)", line).group(1))
				except:
					pass
				if 'B:' in line:
					try:
						self._bedTemp = float(re.search("B: *([0-9\.]*)", line).group(1))
					except:
						pass
				self._callback.mcTempUpdate(self._temp, self._bedTemp, self._targetTemp, self._bedTargetTemp)
				#If we are waiting for an M109 or M190 then measure the time we lost during heatup, so we can remove that time from our printing time estimate.
				if not 'ok' in line and self._heatupWaitStartTime != 0:
					t = time.time()
					self._heatupWaitTimeLost = t - self._heatupWaitStartTime
					self._heatupWaitStartTime = t
			elif line.strip() != '' and line.strip() != 'ok' and not line.startswith('Resend:') and not line.startswith('Error:checksum mismatch') and not line.startswith('Error:Line Number is not Last Line Number+1') and line != 'echo:Unknown command:""\n' and self.isOperational():
				self._callback.mcMessage(line)

			if self._state == self.STATE_DETECT_BAUDRATE or self._state == self.STATE_DETECT_SERIAL:
				if line == '' or time.time() > timeout:
					if len(self._baudrateDetectList) < 1:
						self.close()
						self._errorValue = "No more baudrates to test, and no suitable baudrate found."
						self._changeState(self.STATE_ERROR)
					elif self._baudrateDetectRetry > 0:
						self._baudrateDetectRetry -= 1
						self._serial.write('\n')
						self._log("Baudrate test retry: %d" % (self._baudrateDetectRetry))
						self._sendCommand("M105")
						self._testingBaudrate = True
					else:
						if self._state == self.STATE_DETECT_SERIAL:
							if len(self._serialDetectList) == 0:
								if len(self._baudrateDetectList) == 0:
									self._log("Tried all serial ports and baudrates, but still not printer found that responds to M105.")
									self._errorValue = 'Failed to autodetect serial port.'
									self._changeState(self.STATE_ERROR)
									return
								else:
									self._serialDetectList = serialList(True)
									baudrate = self._baudrateDetectList.pop(0)
							self._serial.close()
							self._serial = serial.Serial(self._serialDetectList.pop(0), baudrate, timeout=2.5, writeTimeout=10000)
						else:
							baudrate = self._baudrateDetectList.pop(0)
						try:
							self._setBaudrate(baudrate)
							self._serial.timeout = 0.5
							self._log("Trying baudrate: %d" % (baudrate))
							self._baudrateDetectRetry = 5
							self._baudrateDetectTestOk = 0
							timeout = time.time() + 5
							self._serial.write('\n')
							self._sendCommand("M105")
							self._testingBaudrate = True
						except:
							self._log("Unexpected error while setting baudrate: %d %s" % (baudrate, getExceptionString()))
				elif 'T:' in line:
					self._baudrateDetectTestOk += 1
					if self._baudrateDetectTestOk < 10:
						self._log("Baudrate test ok: %d" % (self._baudrateDetectTestOk))
						self._sendCommand("M105")
					else:
						self._sendCommand("M999")
						self._serial.timeout = 2
						profile.putMachineSetting('serial_baud_auto', self._serial.baudrate)
						self._changeState(self.STATE_OPERATIONAL)
				else:
					self._testingBaudrate = False
			elif self._state == self.STATE_CONNECTING:
				if line == '' or 'wait' in line:        # 'wait' needed for Repetier (kind of watchdog)
					self._sendCommand("M105")
				elif 'ok' in line:
					self._changeState(self.STATE_OPERATIONAL)
				if time.time() > timeout:
					self.close()
			elif self._state == self.STATE_OPERATIONAL:
				#Request the temperature on comm timeout (every 2 seconds) when we are not printing.
				if line == '':
					if self._extruderCount > 0:
						self._temperatureRequestExtruder = (self._temperatureRequestExtruder + 1) % self._extruderCount
						self.sendCommand("M105 T%d" % (self._temperatureRequestExtruder))
					else:
						self.sendCommand("M105")
					tempRequestTimeout = time.time() + 5
			elif self._state == self.STATE_PRINTING:
				#Even when printing request the temperature every 5 seconds.
				if time.time() > tempRequestTimeout:
					if self._extruderCount > 0:
						self._temperatureRequestExtruder = (self._temperatureRequestExtruder + 1) % self._extruderCount
						self.sendCommand("M105 T%d" % (self._temperatureRequestExtruder))
					else:
						self.sendCommand("M105")
					tempRequestTimeout = time.time() + 5
				if line == '' and time.time() > timeout:
					self._log("Communication timeout during printing, forcing a line")
					line = 'ok'
				if 'ok' in line:
					timeout = time.time() + 5
					if not self._commandQueue.empty():
						self._sendCommand(self._commandQueue.get())
					else:
						self._sendNext()
				elif "resend" in line.lower() or "rs" in line:
					try:
						self._gcodePos = int(line.replace("N:"," ").replace("N"," ").replace(":"," ").split()[-1])
					except:
						if "rs" in line:
							self._gcodePos = int(line.split()[1])
		self._log("Connection closed, closing down monitor")

	def _setBaudrate(self, baudrate):
		try:
			self._serial.baudrate = baudrate
		except:
			print getExceptionString()

	def _log(self, message):
		self._callback.mcLog(message)
		try:
			self._logQueue.put(message, False)
		except:
			#If the log queue is full, remove the first message and append the new message again
			self._logQueue.get()
			try:
				self._logQueue.put(message, False)
			except:
				pass

	def _readline(self):
		if self._serial is None:
			return None
		try:
			ret = self._serial.readline()
		except:
			self._log("Unexpected error while reading serial port: %s" % (getExceptionString()))
			self._errorValue = getExceptionString()
			self.close(True)
			return None
		if ret == '':
			#self._log("Recv: TIMEOUT")
			return ''
		self._log("Recv: %s" % (unicode(ret, 'ascii', 'replace').encode('ascii', 'replace').rstrip()))
		return ret
	
	def close(self, isError = False):
		if self._serial != None:
			self._serial.close()
			if isError:
				self._changeState(self.STATE_CLOSED_WITH_ERROR)
			else:
				self._changeState(self.STATE_CLOSED)
		self._serial = None
	
	def __del__(self):
		self.close()
	
	def _sendCommand(self, cmd):
		if self._serial is None:
			return
		if 'M109' in cmd or 'M190' in cmd:
			self._heatupWaitStartTime = time.time()
		if 'M104' in cmd or 'M109' in cmd:
			try:
				t = 0
				if 'T' in cmd:
					t = int(re.search('T([0-9]+)', cmd).group(1))
				self._targetTemp[t] = float(re.search('S([0-9]+)', cmd).group(1))
			except:
				pass
		if 'M140' in cmd or 'M190' in cmd:
			try:
				self._bedTargetTemp = float(re.search('S([0-9]+)', cmd).group(1))
			except:
				pass
		self._log('Send: %s' % (cmd))
		try:
			self._serial.write(cmd + '\n')
		except serial.SerialTimeoutException:
			self._log("Serial timeout while writing to serial port, trying again.")
			try:
				time.sleep(0.5)
				self._serial.write(cmd + '\n')
			except:
				self._log("Unexpected error while writing serial port: %s" % (getExceptionString()))
				self._errorValue = getExceptionString()
				self.close(True)
		except:
			self._log("Unexpected error while writing serial port: %s" % (getExceptionString()))
			self._errorValue = getExceptionString()
			self.close(True)
	
	def _sendNext(self):
		if self._gcodePos >= len(self._gcodeList):
			self._changeState(self.STATE_OPERATIONAL)
			return
		if self._gcodePos == 100:
			self._printStartTime100 = time.time()
		line = self._gcodeList[self._gcodePos]
		if type(line) is tuple:
			self._printSection = line[1]
			line = line[0]
		try:
			if line == 'M0' or line == 'M1':
				self.setPause(True)
				line = 'M105'	#Don't send the M0 or M1 to the machine, as M0 and M1 are handled as an LCD menu pause.
			if self._printSection in self._feedRateModifier:
				line = re.sub('F([0-9]*)', lambda m: 'F' + str(int(int(m.group(1)) * self._feedRateModifier[self._printSection])), line)
			if ('G0' in line or 'G1' in line) and 'Z' in line:
				z = float(re.search('Z([0-9\.]*)', line).group(1))
				if self._currentZ != z:
					self._currentZ = z
					self._callback.mcZChange(z)
		except:
			self._log("Unexpected error: %s" % (getExceptionString()))
		checksum = reduce(lambda x,y:x^y, map(ord, "N%d%s" % (self._gcodePos, line)))
		self._sendCommand("N%d%s*%d" % (self._gcodePos, line, checksum))
		self._gcodePos += 1
		self._callback.mcProgress(self._gcodePos)
	
	def sendCommand(self, cmd):
		cmd = cmd.encode('ascii', 'replace')
		if self.isPrinting():
			self._commandQueue.put(cmd)
		elif self.isOperational():
			self._sendCommand(cmd)
	
	def printGCode(self, gcodeList):
		if not self.isOperational() or self.isPrinting():
			return
		self._gcodeList = gcodeList
		self._gcodePos = 0
		self._printStartTime100 = None
		self._printSection = 'CUSTOM'
		self._changeState(self.STATE_PRINTING)
		self._printStartTime = time.time()
		for i in xrange(0, 4):
			self._sendNext()
	
	def cancelPrint(self):
		if self.isOperational():
			self._changeState(self.STATE_OPERATIONAL)
	
	def setPause(self, pause):
		if not pause and self.isPaused():
			self._changeState(self.STATE_PRINTING)
			for i in xrange(0, 6):
				self._sendNext()
		if pause and self.isPrinting():
			self._changeState(self.STATE_PAUSED)
	
	def setFeedrateModifier(self, type, value):
		self._feedRateModifier[type] = value

def getExceptionString():
	locationInfo = traceback.extract_tb(sys.exc_info()[2])[0]
	return "%s: '%s' @ %s:%s:%d" % (str(sys.exc_info()[0].__name__), str(sys.exc_info()[1]), os.path.basename(locationInfo[0]), locationInfo[2], locationInfo[1])

########NEW FILE########
__FILENAME__ = meshLoader
"""
The meshLoader module contains a universal interface for loading 3D files.
Depending on the file extension the proper meshLoader is called to load the file.
"""
__copyright__ = "Copyright (C) 2013 David Braam - Released under terms of the AGPLv3 License"

import os

from Cura.util.meshLoaders import stl
from Cura.util.meshLoaders import obj
from Cura.util.meshLoaders import dae
from Cura.util.meshLoaders import amf

def loadSupportedExtensions():
	""" return a list of supported file extensions for loading. """
	return ['.stl', '.obj', '.dae', '.amf']

def saveSupportedExtensions():
	""" return a list of supported file extensions for saving. """
	return ['.amf', '.stl']

def loadMeshes(filename):
	"""
	loadMeshes loads 1 or more printableObjects from a file.
	STL files are a single printableObject with a single mesh, these are most common.
	OBJ files usually contain a single mesh, but they can contain multiple meshes
	AMF can contain whole scenes of objects with each object having multiple meshes.
	DAE files are a mess, but they can contain scenes of objects as well as grouped meshes
	"""
	ext = os.path.splitext(filename)[1].lower()
	if ext == '.stl':
		return stl.loadScene(filename)
	if ext == '.obj':
		return obj.loadScene(filename)
	if ext == '.dae':
		return dae.loadScene(filename)
	if ext == '.amf':
		return amf.loadScene(filename)
	print 'Error: Unknown model extension: %s' % (ext)
	return []

def saveMeshes(filename, objects):
	"""
	Save a list of objects into the file given by the filename. Use the filename extension to find out the file format.
	"""
	ext = os.path.splitext(filename)[1].lower()
	if ext == '.stl':
		stl.saveScene(filename, objects)
		return
	if ext == '.amf':
		amf.saveScene(filename, objects)
		return
	print 'Error: Unknown model extension: %s' % (ext)

########NEW FILE########
__FILENAME__ = amf
"""
AMF file reader.
AMF files are the proposed replacement for STL. AMF is an open standard to share 3D manufacturing files.
Many of the features found in AMF are currently not yet support in Cura. Most important the curved surfaces.

http://en.wikipedia.org/wiki/Additive_Manufacturing_File_Format
"""
__copyright__ = "Copyright (C) 2013 David Braam - Released under terms of the AGPLv3 License"

import cStringIO as StringIO
import zipfile
import os
try:
	from xml.etree import cElementTree as ElementTree
except:
	from xml.etree import ElementTree

from Cura.util import printableObject
from Cura.util import profile

def loadScene(filename):
	try:
		zfile = zipfile.ZipFile(filename)
		xml = zfile.read(zfile.namelist()[0])
		zfile.close()
	except zipfile.BadZipfile:
		f = open(filename, "r")
		xml = f.read()
		f.close()
	amf = ElementTree.fromstring(xml)
	if 'unit' in amf.attrib:
		unit = amf.attrib['unit'].lower()
	else:
		unit = 'millimeter'
	if unit == 'millimeter':
		scale = 1.0
	elif unit == 'meter':
		scale = 1000.0
	elif unit == 'inch':
		scale = 25.4
	elif unit == 'feet':
		scale = 304.8
	elif unit == 'micron':
		scale = 0.001
	else:
		print "Unknown unit in amf: %s" % (unit)
		scale = 1.0

	ret = []
	for amfObj in amf.iter('object'):
		obj = printableObject.printableObject(filename)
		for amfMesh in amfObj.iter('mesh'):
			vertexList = []
			for vertices in amfMesh.iter('vertices'):
				for vertex in vertices.iter('vertex'):
					for coordinates in vertex.iter('coordinates'):
						v = [0.0,0.0,0.0]
						for t in coordinates:
							if t.tag == 'x':
								v[0] = float(t.text)
							elif t.tag == 'y':
								v[1] = float(t.text)
							elif t.tag == 'z':
								v[2] = float(t.text)
						vertexList.append(v)

			for volume in amfMesh.iter('volume'):
				m = obj._addMesh()
				count = 0
				for triangle in volume.iter('triangle'):
					count += 1
				m._prepareFaceCount(count)

				for triangle in volume.iter('triangle'):
					for t in triangle:
						if t.tag == 'v1':
							v1 = vertexList[int(t.text)]
						elif t.tag == 'v2':
							v2 = vertexList[int(t.text)]
						elif t.tag == 'v3':
							v3 = vertexList[int(t.text)]
							m._addFace(v1[0], v1[1], v1[2], v2[0], v2[1], v2[2], v3[0], v3[1], v3[2])
		obj._postProcessAfterLoad()
		ret.append(obj)

	return ret

def saveScene(filename, objects):
	f = open(filename, 'wb')
	saveSceneStream(f, filename, objects)
	f.close()

def saveSceneStream(s, filename, objects):
	xml = StringIO.StringIO()
	xml.write('<?xml version="1.0" encoding="utf-8"?>\n')
	xml.write('<amf unit="millimeter" version="1.1">\n')
	n = 0
	for obj in objects:
		n += 1
		xml.write('  <object id="%d">\n' % (n))
		xml.write('    <mesh>\n')
		xml.write('      <vertices>\n')
		vertexList, meshList = obj.getVertexIndexList()
		for v in vertexList:
			xml.write('        <vertex>\n')
			xml.write('          <coordinates>\n')
			xml.write('            <x>%f</x>\n' % (v[0]))
			xml.write('            <y>%f</y>\n' % (v[1]))
			xml.write('            <z>%f</z>\n' % (v[2]))
			xml.write('          </coordinates>\n')
			xml.write('        </vertex>\n')
		xml.write('      </vertices>\n')

		matID = 1
		for m in meshList:
			xml.write('      <volume materialid="%i">\n' % (matID))
			for idx in xrange(0, len(m), 3):
				xml.write('        <triangle>\n')
				xml.write('          <v1>%i</v1>\n' % (m[idx]))
				xml.write('          <v2>%i</v2>\n' % (m[idx+1]))
				xml.write('          <v3>%i</v3>\n' % (m[idx+2]))
				xml.write('        </triangle>\n')
			xml.write('      </volume>\n')
			matID += 1
		xml.write('    </mesh>\n')
		xml.write('  </object>\n')

	n += 1
	xml.write('  <constellation id="%d">\n' % (n))
	for idx in xrange(1, n):
		xml.write('    <instance objectid="%d">\n' % (idx))
		xml.write('      <deltax>0</deltax>\n')
		xml.write('      <deltay>0</deltay>\n')
		xml.write('      <deltaz>0</deltaz>\n')
		xml.write('      <rx>0</rx>\n')
		xml.write('      <ry>0</ry>\n')
		xml.write('      <rz>0</rz>\n')
		xml.write('    </instance>\n')
	xml.write('  </constellation>\n')
	for n in xrange(0, 4):
		xml.write('  <material id="%i">\n' % (n + 1))
		xml.write('    <metadata type="Name">Material %i</metadata>\n' % (n + 1))
		if n == 0:
			col = profile.getPreferenceColour('model_colour')
		else:
			col = profile.getPreferenceColour('model_colour%i' % (n + 1))
		xml.write('    <color><r>%.2f</r><g>%.2f</g><b>%.2f</b></color>\n' % (col[0], col[1], col[2]))
		xml.write('  </material>\n')
	xml.write('</amf>\n')

	zfile = zipfile.ZipFile(s, "w", zipfile.ZIP_DEFLATED)
	zfile.writestr(os.path.basename(filename), xml.getvalue())
	zfile.close()
	xml.close()

########NEW FILE########
__FILENAME__ = dae
"""
DAE are COLLADA files.
The DAE reader is a limited COLLADA reader. And has only been tested with DAE exports from SketchUp, http://www.sketchup.com/
The reason for this reader in Cura is that the free version of SketchUp by default does not support any other format that we can read.

http://en.wikipedia.org/wiki/COLLADA
"""
__copyright__ = "Copyright (C) 2013 David Braam - Released under terms of the AGPLv3 License"

from  xml.parsers.expat import ParserCreate
import os

from Cura.util import printableObject

def loadScene(filename):
	loader = daeLoader(filename)
	return [loader.obj]

class daeLoader(object):
	"""
	COLLADA object loader. This class is a bit of a mess, COLLADA files are complex beasts, and this code has only been tweaked to accept
	the COLLADA files exported from SketchUp.

	Parts of this class can be cleaned up and improved by using more numpy.
	"""
	def __init__(self, filename):
		self.obj = printableObject.printableObject(filename)
		self.mesh = self.obj._addMesh()

		r = ParserCreate()
		r.StartElementHandler = self._StartElementHandler
		r.EndElementHandler = self._EndElementHandler
		r.CharacterDataHandler = self._CharacterDataHandler

		self._base = {}
		self._cur = self._base
		self._idMap = {}
		self._geometryList = []
		self._faceCount = 0
		r.ParseFile(open(filename, "r"))
		
		self.vertexCount = 0
		for instance_visual_scene in self._base['collada'][0]['scene'][0]['instance_visual_scene']:
			for node in self._idMap[instance_visual_scene['_url']]['node']:
				self._ProcessNode1(node)
		self.mesh._prepareFaceCount(self._faceCount)
		for instance_visual_scene in self._base['collada'][0]['scene'][0]['instance_visual_scene']:
			for node in self._idMap[instance_visual_scene['_url']]['node']:
				self._ProcessNode2(node)

		scale = float(self._base['collada'][0]['asset'][0]['unit'][0]['_meter']) * 1000
		self.mesh.vertexes *= scale
		
		self._base = None
		self._cur = None
		self._idMap = None
		
		self.obj._postProcessAfterLoad()

	def _ProcessNode1(self, node):
		if 'node' in node:
			for n in node['node']:
				self._ProcessNode1(n)
		if 'instance_geometry' in node:
			for instance_geometry in node['instance_geometry']:
				mesh = self._idMap[instance_geometry['_url']]['mesh'][0]
				if 'triangles' in mesh:
					for triangles in mesh['triangles']:
						self._faceCount += int(triangles['_count'])
				elif 'lines' in mesh:
					pass #Ignore lines
				else:
					print mesh.keys()
		if 'instance_node' in node:
			for instance_node in node['instance_node']:
				self._ProcessNode1(self._idMap[instance_node['_url']])

	def _ProcessNode2(self, node, matrix = None):
		if 'matrix' in node:
			oldMatrix = matrix
			matrix = map(float, node['matrix'][0]['__data'].split())
			if oldMatrix is not None:
				newMatrix = [0]*16
				newMatrix[0] = oldMatrix[0] * matrix[0] + oldMatrix[1] * matrix[4] + oldMatrix[2] * matrix[8] + oldMatrix[3] * matrix[12]
				newMatrix[1] = oldMatrix[0] * matrix[1] + oldMatrix[1] * matrix[5] + oldMatrix[2] * matrix[9] + oldMatrix[3] * matrix[13]
				newMatrix[2] = oldMatrix[0] * matrix[2] + oldMatrix[1] * matrix[6] + oldMatrix[2] * matrix[10] + oldMatrix[3] * matrix[14]
				newMatrix[3] = oldMatrix[0] * matrix[3] + oldMatrix[1] * matrix[7] + oldMatrix[2] * matrix[11] + oldMatrix[3] * matrix[15]
				newMatrix[4] = oldMatrix[4] * matrix[0] + oldMatrix[5] * matrix[4] + oldMatrix[6] * matrix[8] + oldMatrix[7] * matrix[12]
				newMatrix[5] = oldMatrix[4] * matrix[1] + oldMatrix[5] * matrix[5] + oldMatrix[6] * matrix[9] + oldMatrix[7] * matrix[13]
				newMatrix[6] = oldMatrix[4] * matrix[2] + oldMatrix[5] * matrix[6] + oldMatrix[6] * matrix[10] + oldMatrix[7] * matrix[14]
				newMatrix[7] = oldMatrix[4] * matrix[3] + oldMatrix[5] * matrix[7] + oldMatrix[6] * matrix[11] + oldMatrix[7] * matrix[15]
				newMatrix[8] = oldMatrix[8] * matrix[0] + oldMatrix[9] * matrix[4] + oldMatrix[10] * matrix[8] + oldMatrix[11] * matrix[12]
				newMatrix[9] = oldMatrix[8] * matrix[1] + oldMatrix[9] * matrix[5] + oldMatrix[10] * matrix[9] + oldMatrix[11] * matrix[13]
				newMatrix[10] = oldMatrix[8] * matrix[2] + oldMatrix[9] * matrix[6] + oldMatrix[10] * matrix[10] + oldMatrix[11] * matrix[14]
				newMatrix[11] = oldMatrix[8] * matrix[3] + oldMatrix[9] * matrix[7] + oldMatrix[10] * matrix[11] + oldMatrix[11] * matrix[15]
				newMatrix[12] = oldMatrix[12] * matrix[0] + oldMatrix[13] * matrix[4] + oldMatrix[14] * matrix[8] + oldMatrix[15] * matrix[12]
				newMatrix[13] = oldMatrix[12] * matrix[1] + oldMatrix[13] * matrix[5] + oldMatrix[14] * matrix[9] + oldMatrix[15] * matrix[13]
				newMatrix[14] = oldMatrix[12] * matrix[2] + oldMatrix[13] * matrix[6] + oldMatrix[14] * matrix[10] + oldMatrix[15] * matrix[14]
				newMatrix[15] = oldMatrix[12] * matrix[3] + oldMatrix[13] * matrix[7] + oldMatrix[14] * matrix[11] + oldMatrix[15] * matrix[15]
				matrix = newMatrix
		if 'node' in node:
			for n in node['node']:
				self._ProcessNode2(n, matrix)
		if 'instance_geometry' in node:
			for instance_geometry in node['instance_geometry']:
				mesh = self._idMap[instance_geometry['_url']]['mesh'][0]
				
				if 'triangles' in mesh:
					for triangles in mesh['triangles']:
						for input in triangles['input']:
							if input['_semantic'] == 'VERTEX':
								vertices = self._idMap[input['_source']]
						for input in vertices['input']:
							if input['_semantic'] == 'POSITION':
								vertices = self._idMap[input['_source']]
						indexList = map(int, triangles['p'][0]['__data'].split())
						positionList = map(float, vertices['float_array'][0]['__data'].split())

						faceCount = int(triangles['_count'])
						stepSize = len(indexList) / (faceCount * 3)
						for i in xrange(0, faceCount):
							idx0 = indexList[((i * 3) + 0) * stepSize]
							idx1 = indexList[((i * 3) + 1) * stepSize]
							idx2 = indexList[((i * 3) + 2) * stepSize]
							x0 = positionList[idx0*3]
							y0 = positionList[idx0*3+1]
							z0 = positionList[idx0*3+2]
							x1 = positionList[idx1*3]
							y1 = positionList[idx1*3+1]
							z1 = positionList[idx1*3+2]
							x2 = positionList[idx2*3]
							y2 = positionList[idx2*3+1]
							z2 = positionList[idx2*3+2]
							if matrix is not None:
								self.mesh._addFace(
									x0 * matrix[0] + y0 * matrix[1] + z0 * matrix[2] + matrix[3], x0 * matrix[4] + y0 * matrix[5] + z0 * matrix[6] + matrix[7], x0 * matrix[8] + y0 * matrix[9] + z0 * matrix[10] + matrix[11],
									x1 * matrix[0] + y1 * matrix[1] + z1 * matrix[2] + matrix[3], x1 * matrix[4] + y1 * matrix[5] + z1 * matrix[6] + matrix[7], x1 * matrix[8] + y1 * matrix[9] + z1 * matrix[10] + matrix[11],
									x2 * matrix[0] + y2 * matrix[1] + z2 * matrix[2] + matrix[3], x2 * matrix[4] + y2 * matrix[5] + z2 * matrix[6] + matrix[7], x2 * matrix[8] + y2 * matrix[9] + z2 * matrix[10] + matrix[11]
								)
							else:
								self.mesh._addFace(x0, y0, z0, x1, y1, z1, x2, y2, z2)
		if 'instance_node' in node:
			for instance_node in node['instance_node']:
				self._ProcessNode2(self._idMap[instance_node['_url']], matrix)
	
	def _StartElementHandler(self, name, attributes):
		name = name.lower()
		if not name in self._cur:
			self._cur[name] = []
		new = {'__name': name, '__parent': self._cur}
		self._cur[name].append(new)
		self._cur = new
		for k in attributes.keys():
			self._cur['_' + k] = attributes[k]
		
		if 'id' in attributes:
			self._idMap['#' + attributes['id']] = self._cur
		
	def _EndElementHandler(self, name):
		self._cur = self._cur['__parent']

	def _CharacterDataHandler(self, data):
		if len(data.strip()) < 1:
			return
		if '__data' in self._cur:
			self._cur['__data'] += data
		else:
			self._cur['__data'] = data
	
	def _GetWithKey(self, item, basename, key, value):
		input = basename
		while input in item:
			if item[basename]['_'+key] == value:
				return self._idMap[item[input]['_source']]
			basename += "!"

########NEW FILE########
__FILENAME__ = obj
"""
OBJ file reader.
OBJ are wavefront object files. These are quite common and can be exported from a lot of 3D tools.
Only vertex information is read from the OBJ file, information about textures and normals is ignored.

http://en.wikipedia.org/wiki/Wavefront_.obj_file
"""
__copyright__ = "Copyright (C) 2013 David Braam - Released under terms of the AGPLv3 License"

import os
from Cura.util import printableObject

def loadScene(filename):
	obj = printableObject.printableObject(filename)
	m = obj._addMesh()

	vertexList = []
	faceList = []

	f = open(filename, "r")
	for line in f:
		parts = line.split()
		if len(parts) < 1:
			continue
		if parts[0] == 'v':
			vertexList.append([float(parts[1]), float(parts[2]), float(parts[3])])
		if parts[0] == 'f':
			parts = map(lambda p: p.split('/')[0], parts)
			for idx in xrange(1, len(parts)-2):
				faceList.append([int(parts[1]), int(parts[idx+1]), int(parts[idx+2])])
	f.close()

	m._prepareFaceCount(len(faceList))
	for f in faceList:
		i = f[0] - 1
		j = f[1] - 1
		k = f[2] - 1
		if i < 0 or i >= len(vertexList):
			i = 0
		if j < 0 or j >= len(vertexList):
			j = 0
		if k < 0 or k >= len(vertexList):
			k = 0
		m._addFace(vertexList[i][0], vertexList[i][1], vertexList[i][2], vertexList[j][0], vertexList[j][1], vertexList[j][2], vertexList[k][0], vertexList[k][1], vertexList[k][2])

	obj._postProcessAfterLoad()
	return [obj]

########NEW FILE########
__FILENAME__ = stl
"""
STL file mesh loader.
STL is the most common file format used for 3D printing right now.
STLs come in 2 flavors.
	Binary, which is easy and quick to read.
	Ascii, which is harder to read, as can come with windows, mac and unix style newlines.
	The ascii reader has been designed so it has great compatibility with all kinds of formats or slightly broken exports from tools.

This module also contains a function to save objects as an STL file.

http://en.wikipedia.org/wiki/STL_(file_format)
"""
__copyright__ = "Copyright (C) 2013 David Braam - Released under terms of the AGPLv3 License"

import sys
import os
import struct
import time

from Cura.util import printableObject

def _loadAscii(m, f):
	cnt = 0
	for lines in f:
		for line in lines.split('\r'):
			if 'vertex' in line:
				cnt += 1
	m._prepareFaceCount(int(cnt) / 3)
	f.seek(5, os.SEEK_SET)
	cnt = 0
	data = [None,None,None]
	for lines in f:
		for line in lines.split('\r'):
			if 'vertex' in line:
				data[cnt] = line.replace(',', '.').split()[1:]
				cnt += 1
				if cnt == 3:
					m._addFace(float(data[0][0]), float(data[0][1]), float(data[0][2]), float(data[1][0]), float(data[1][1]), float(data[1][2]), float(data[2][0]), float(data[2][1]), float(data[2][2]))
					cnt = 0

def _loadBinary(m, f):
	#Skip the header
	f.read(80-5)
	faceCount = struct.unpack('<I', f.read(4))[0]
	m._prepareFaceCount(faceCount)
	for idx in xrange(0, faceCount):
		data = struct.unpack("<ffffffffffffH", f.read(50))
		m._addFace(data[3], data[4], data[5], data[6], data[7], data[8], data[9], data[10], data[11])

def loadScene(filename):
	obj = printableObject.printableObject(filename)
	m = obj._addMesh()

	f = open(filename, "rb")
	if f.read(5).lower() == "solid":
		_loadAscii(m, f)
		if m.vertexCount < 3:
			f.seek(5, os.SEEK_SET)
			_loadBinary(m, f)
	else:
		_loadBinary(m, f)
	f.close()
	obj._postProcessAfterLoad()
	return [obj]

def saveScene(filename, objects):
	f = open(filename, 'wb')
	saveSceneStream(f, objects)
	f.close()

def saveSceneStream(stream, objects):
	#Write the STL binary header. This can contain any info, except for "SOLID" at the start.
	stream.write(("CURA BINARY STL EXPORT. " + time.strftime('%a %d %b %Y %H:%M:%S')).ljust(80, '\000'))

	vertexCount = 0
	for obj in objects:
		for m in obj._meshList:
			vertexCount += m.vertexCount

	#Next follow 4 binary bytes containing the amount of faces, and then the face information.
	stream.write(struct.pack("<I", int(vertexCount / 3)))
	for obj in objects:
		for m in obj._meshList:
			vertexes = m.getTransformedVertexes(True)
			for idx in xrange(0, m.vertexCount, 3):
				v1 = vertexes[idx]
				v2 = vertexes[idx+1]
				v3 = vertexes[idx+2]
				stream.write(struct.pack("<fff", 0.0, 0.0, 0.0))
				stream.write(struct.pack("<fff", v1[0], v1[1], v1[2]))
				stream.write(struct.pack("<fff", v2[0], v2[1], v2[2]))
				stream.write(struct.pack("<fff", v3[0], v3[1], v3[2]))
				stream.write(struct.pack("<H", 0))

########NEW FILE########
__FILENAME__ = objectScene
"""
The objectScene module contain a objectScene class,
this class contains a group of printableObjects that are located on the build platform.

The objectScene handles the printing order of these objects, and if they collide.
"""
__copyright__ = "Copyright (C) 2013 David Braam - Released under terms of the AGPLv3 License"
import random
import numpy

from Cura.util import profile
from Cura.util import polygon

class _objectOrder(object):
	"""
	Internal object used by the _objectOrderFinder to keep track of a possible order in which to print objects.
	"""
	def __init__(self, order, todo):
		"""
		:param order:	List of indexes in which to print objects, ordered by printing order.
		:param todo: 	List of indexes which are not yet inserted into the order list.
		"""
		self.order = order
		self.todo = todo

class _objectOrderFinder(object):
	"""
	Internal object used by the Scene class to figure out in which order to print objects.
	"""
	def __init__(self, scene, leftToRight, frontToBack, gantryHeight):
		self._scene = scene
		self._objs = scene.objects()
		self._leftToRight = leftToRight
		self._frontToBack = frontToBack
		initialList = []
		for n in xrange(0, len(self._objs)):
			if scene.checkPlatform(self._objs[n]):
				initialList.append(n)
		for n in initialList:
			if self._objs[n].getSize()[2] > gantryHeight and len(initialList) > 1:
				self.order = None
				return
		if len(initialList) == 0:
			self.order = []
			return

		self._hitMap = [None] * (max(initialList)+1)
		for a in initialList:
			self._hitMap[a] = [False] * (max(initialList)+1)
			for b in initialList:
				self._hitMap[a][b] = self._checkHit(a, b)

		#Check if we have 2 files that overlap so that they can never be printed one at a time.
		for a in initialList:
			for b in initialList:
				if a != b and self._hitMap[a][b] and self._hitMap[b][a]:
					self.order = None
					return

		initialList.sort(self._objIdxCmp)

		n = 0
		self._todo = [_objectOrder([], initialList)]
		while len(self._todo) > 0:
			n += 1
			current = self._todo.pop()
			#print len(self._todo), len(current.order), len(initialList), current.order
			for addIdx in current.todo:
				if not self._checkHitFor(addIdx, current.order) and not self._checkBlocks(addIdx, current.todo):
					todoList = current.todo[:]
					todoList.remove(addIdx)
					order = current.order[:] + [addIdx]
					if len(todoList) == 0:
						self._todo = None
						self.order = order
						return
					self._todo.append(_objectOrder(order, todoList))
		self.order = None

	def _objIdxCmp(self, a, b):
		scoreA = sum(self._hitMap[a])
		scoreB = sum(self._hitMap[b])
		return scoreA - scoreB

	def _checkHitFor(self, addIdx, others):
		for idx in others:
			if self._hitMap[addIdx][idx]:
				return True
		return False

	def _checkBlocks(self, addIdx, others):
		for idx in others:
			if addIdx != idx and self._hitMap[idx][addIdx]:
				return True
		return False

	#Check if printing one object will cause printhead colission with other object.
	def _checkHit(self, addIdx, idx):
		obj = self._scene._objectList[idx]
		addObj = self._scene._objectList[addIdx]
		return polygon.polygonCollision(obj._boundaryHull + obj.getPosition(), addObj._headAreaHull + addObj.getPosition())

class Scene(object):
	"""
	The scene class keep track of an collection of objects on a build platform and their state.
	It can figure out in which order to print them (if any) and if an object can be printed at all.
	"""
	def __init__(self):
		self._objectList = []
		self._sizeOffsets = numpy.array([0.0,0.0], numpy.float32)
		self._machineSize = numpy.array([100,100,100], numpy.float32)
		self._headSizeOffsets = numpy.array([18.0,18.0], numpy.float32)
		self._minExtruderCount = None
		self._extruderOffset = [numpy.array([0,0], numpy.float32)] * 4

		#Print order variables
		self._leftToRight = False
		self._frontToBack = True
		self._gantryHeight = 60
		self._oneAtATime = True

	# update the physical machine dimensions
	def updateMachineDimensions(self):
		self._machineSize = numpy.array([profile.getMachineSettingFloat('machine_width'), profile.getMachineSettingFloat('machine_depth'), profile.getMachineSettingFloat('machine_height')])
		self._machinePolygons = profile.getMachineSizePolygons()
		self.updateHeadSize()

	# Size offsets are offsets caused by brim, skirt, etc.
	def updateSizeOffsets(self, force=False):
		newOffsets = numpy.array(profile.calculateObjectSizeOffsets(), numpy.float32)
		minExtruderCount = profile.minimalExtruderCount()
		if not force and numpy.array_equal(self._sizeOffsets, newOffsets) and self._minExtruderCount == minExtruderCount:
			return
		self._sizeOffsets = newOffsets
		self._minExtruderCount = minExtruderCount

		extends = [numpy.array([[-newOffsets[0],-newOffsets[1]],[ newOffsets[0],-newOffsets[1]],[ newOffsets[0], newOffsets[1]],[-newOffsets[0], newOffsets[1]]], numpy.float32)]
		for n in xrange(1, 4):
			headOffset = numpy.array([[0, 0], [-profile.getMachineSettingFloat('extruder_offset_x%d' % (n)), -profile.getMachineSettingFloat('extruder_offset_y%d' % (n))]], numpy.float32)
			extends.append(polygon.minkowskiHull(extends[n-1], headOffset))
		if minExtruderCount > 1:
			extends[0] = extends[1]

		for obj in self._objectList:
			obj.setPrintAreaExtends(extends[len(obj._meshList) - 1])

	#size of the printing head.
	def updateHeadSize(self, obj = None):
		xMin = profile.getMachineSettingFloat('extruder_head_size_min_x')
		xMax = profile.getMachineSettingFloat('extruder_head_size_max_x')
		yMin = profile.getMachineSettingFloat('extruder_head_size_min_y')
		yMax = profile.getMachineSettingFloat('extruder_head_size_max_y')
		gantryHeight = profile.getMachineSettingFloat('extruder_head_size_height')

		self._leftToRight = xMin < xMax
		self._frontToBack = yMin < yMax
		self._headSizeOffsets[0] = min(xMin, xMax)
		self._headSizeOffsets[1] = min(yMin, yMax)
		self._gantryHeight = gantryHeight
		self._oneAtATime = self._gantryHeight > 0 and profile.getPreference('oneAtATime') == 'True'
		for obj in self._objectList:
			if obj.getSize()[2] > self._gantryHeight:
				self._oneAtATime = False

		headArea = numpy.array([[-xMin,-yMin],[ xMax,-yMin],[ xMax, yMax],[-xMin, yMax]], numpy.float32)

		if obj is None:
			for obj in self._objectList:
				obj.setHeadArea(headArea, self._headSizeOffsets)
		else:
			obj.setHeadArea(headArea, self._headSizeOffsets)

	def isOneAtATime(self):
		return self._oneAtATime

	def setExtruderOffset(self, extruderNr, offsetX, offsetY):
		self._extruderOffset[extruderNr] = numpy.array([offsetX, offsetY], numpy.float32)

	def objects(self):
		return self._objectList

	#Add new object to print area
	def add(self, obj):
		if numpy.max(obj.getSize()[0:2]) > numpy.max(self._machineSize[0:2]) * 2.5:
			scale = numpy.max(self._machineSize[0:2]) * 2.5 / numpy.max(obj.getSize()[0:2])
			matrix = [[scale,0,0], [0, scale, 0], [0, 0, scale]]
			obj.applyMatrix(numpy.matrix(matrix, numpy.float64))
		self._findFreePositionFor(obj)
		self._objectList.append(obj)
		self.updateHeadSize(obj)
		self.updateSizeOffsets(True)
		self.pushFree(obj)

	def remove(self, obj):
		self._objectList.remove(obj)

	#Dual(multiple) extrusion merge
	def merge(self, obj1, obj2):
		self.remove(obj2)
		obj1._meshList += obj2._meshList
		for m in obj2._meshList:
			m._obj = obj1
		obj1.processMatrix()
		obj1.setPosition((obj1.getPosition() + obj2.getPosition()) / 2)
		self.pushFree(obj1)

	def pushFree(self, staticObj = None):
		if staticObj is None:
			for obj in self._objectList:
				self.pushFree(obj)
			return
		if not self.checkPlatform(staticObj):
			return
		pushList = []
		for obj in self._objectList:
			if obj == staticObj or not self.checkPlatform(obj):
				continue
			if self._oneAtATime:
				v = polygon.polygonCollisionPushVector(obj._headAreaMinHull + obj.getPosition(), staticObj._boundaryHull + staticObj.getPosition())
			else:
				v = polygon.polygonCollisionPushVector(obj._boundaryHull + obj.getPosition(), staticObj._boundaryHull + staticObj.getPosition())
			if type(v) is bool:
				continue
			obj.setPosition(obj.getPosition() + v * 1.01)
			pushList.append(obj)
		for obj in pushList:
			self.pushFree(obj)

	def arrangeAll(self):
		oldList = self._objectList
		self._objectList = []
		for obj in oldList:
			obj.setPosition(numpy.array([0,0], numpy.float32))
			self.add(obj)

	def centerAll(self):
		minPos = numpy.array([9999999,9999999], numpy.float32)
		maxPos = numpy.array([-9999999,-9999999], numpy.float32)
		for obj in self._objectList:
			pos = obj.getPosition()
			size = obj.getSize()
			minPos[0] = min(minPos[0], pos[0] - size[0] / 2)
			minPos[1] = min(minPos[1], pos[1] - size[1] / 2)
			maxPos[0] = max(maxPos[0], pos[0] + size[0] / 2)
			maxPos[1] = max(maxPos[1], pos[1] + size[1] / 2)
		offset = -(maxPos + minPos) / 2
		for obj in self._objectList:
			obj.setPosition(obj.getPosition() + offset)

	def printOrder(self):
		if self._oneAtATime:
			order = _objectOrderFinder(self, self._leftToRight, self._frontToBack, self._gantryHeight).order
		else:
			order = None
		return order

	#Check if two objects are hitting each-other (+ head space).
	def _checkHit(self, a, b):
		if a == b:
			return False
		if self._oneAtATime:
			return polygon.polygonCollision(a._headAreaMinHull + a.getPosition(), b._boundaryHull + b.getPosition())
		else:
			return polygon.polygonCollision(a._boundaryHull + a.getPosition(), b._boundaryHull + b.getPosition())

	def checkPlatform(self, obj):
		area = obj._printAreaHull + obj.getPosition()
		if obj.getSize()[2] > self._machineSize[2]:
			return False
		if not polygon.fullInside(area, self._machinePolygons[0]):
			return False
		#Check the "no go zones"
		for poly in self._machinePolygons[1:]:
			if polygon.polygonCollision(poly, area):
				return False
		return True

	def _findFreePositionFor(self, obj):
		posList = []
		for a in self._objectList:
			p = a.getPosition()
			if self._oneAtATime:
				s = (a.getSize()[0:2] + obj.getSize()[0:2]) / 2 + self._sizeOffsets + self._headSizeOffsets + numpy.array([4,4], numpy.float32)
			else:
				s = (a.getSize()[0:2] + obj.getSize()[0:2]) / 2 + numpy.array([4,4], numpy.float32)
			posList.append(p + s * ( 1.0, 1.0))
			posList.append(p + s * ( 0.0, 1.0))
			posList.append(p + s * (-1.0, 1.0))
			posList.append(p + s * ( 1.0, 0.0))
			posList.append(p + s * (-1.0, 0.0))
			posList.append(p + s * ( 1.0,-1.0))
			posList.append(p + s * ( 0.0,-1.0))
			posList.append(p + s * (-1.0,-1.0))

		best = None
		bestDist = None
		for p in posList:
			obj.setPosition(p)
			ok = True
			for a in self._objectList:
				if self._checkHit(a, obj):
					ok = False
					break
			if not ok:
				continue
			dist = numpy.linalg.norm(p)
			if not self.checkPlatform(obj):
				dist *= 3
			if best is None or dist < bestDist:
				best = p
				bestDist = dist
		if best is not None:
			obj.setPosition(best)

########NEW FILE########
__FILENAME__ = pluginInfo
"""
The plugin module contains information about the plugins found for Cura.
It keeps track of a list of installed plugins and the information contained within.
"""
__copyright__ = "Copyright (C) 2013 David Braam - Released under terms of the AGPLv3 License"

import os
import sys
import traceback
import platform
import re
import tempfile
import cPickle as pickle

from Cura.util import profile
from Cura.util import resources

_pluginList = None

class pluginInfo(object):
	"""
	Plugin information object. Used to keep track of information about the available plugins in this installation of Cura.
	Each plugin as meta-data associated with it which can be retrieved from this class.
	"""
	def __init__(self, dirname, filename):
		self._dirname = dirname
		self._filename = filename
		self._name = os.path.splitext(os.path.basename(filename))[0]
		self._type = 'unknown'
		self._info = ''
		self._params = []
		with open(os.path.join(dirname, filename), "r") as f:
			for line in f:
				line = line.strip()
				if not line.startswith('#'):
					break
				line = line[1:].split(':', 1)
				if len(line) != 2:
					continue
				if line[0].upper() == 'NAME':
					self._name = line[1].strip()
				elif line[0].upper() == 'INFO':
					self._info = line[1].strip()
				elif line[0].upper() == 'TYPE':
					self._type = line[1].strip()
				elif line[0].upper() == 'DEPEND':
					pass
				elif line[0].upper() == 'PARAM':
					m = re.match('([a-zA-Z][a-zA-Z0-9_]*)\(([a-zA-Z_]*)(?::([^\)]*))?\) +(.*)', line[1].strip())
					if m is not None:
						self._params.append({'name': m.group(1), 'type': m.group(2), 'default': m.group(3), 'description': m.group(4)})
				# else:
				# 	print "Unknown item in plugin meta data: %s %s" % (line[0], line[1])

	def getFilename(self):
		return self._filename

	def getFullFilename(self):
		return os.path.join(self._dirname, self._filename)

	def getType(self):
		return self._type

	def getName(self):
		return self._name

	def getInfo(self):
		return self._info

	def getParams(self):
		return self._params

def getPostProcessPluginConfig():
	try:
		return pickle.loads(str(profile.getProfileSetting('plugin_config')))
	except:
		return []

def setPostProcessPluginConfig(config):
	profile.putProfileSetting('plugin_config', pickle.dumps(config))

def getPluginBasePaths():
	ret = []
	if platform.system() != "Windows":
		ret.append(os.path.expanduser('~/.cura/plugins/'))
	if platform.system() == "Darwin" and hasattr(sys, 'frozen'):
		ret.append(os.path.normpath(os.path.join(resources.resourceBasePath, "plugins")))
	else:
		ret.append(os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'plugins')))
	return ret

def getPluginList(pluginType):
	global _pluginList
	if _pluginList is None:
		_pluginList = []
		for basePath in getPluginBasePaths():
			if os.path.isdir(basePath):
				for filename in os.listdir(basePath):
					if filename.startswith('.'):
						continue
					if filename.startswith('_'):
						continue
					if os.path.isdir(os.path.join(basePath, filename)):
						if os.path.exists(os.path.join(basePath, filename, 'script.py')):
							_pluginList.append(pluginInfo(basePath, os.path.join(filename, 'script.py')))
					elif filename.endswith('.py'):
						_pluginList.append(pluginInfo(basePath, filename))
	ret = []
	for plugin in _pluginList:
		if plugin.getType() == pluginType:
			ret.append(plugin)
	return ret

def runPostProcessingPlugins(engineResult):
	pluginConfigList = getPostProcessPluginConfig()
	pluginList = getPluginList('postprocess')

	tempfilename = None
	for pluginConfig in pluginConfigList:
		plugin = None
		for pluginTest in pluginList:
			if pluginTest.getFilename() == pluginConfig['filename']:
				plugin = pluginTest
		if plugin is None:
			continue

		pythonFile = plugin.getFullFilename()

		if tempfilename is None:
			f = tempfile.NamedTemporaryFile(prefix='CuraPluginTemp', delete=False)
			tempfilename = f.name
			f.write(engineResult.getGCode())
			f.close()

		locals = {'filename': tempfilename}
		for param in plugin.getParams():
			value = param['default']
			if param['name'] in pluginConfig['params']:
				value = pluginConfig['params'][param['name']]

			if param['type'] == 'float':
				try:
					value = float(value)
				except:
					value = float(param['default'])

			locals[param['name']] = value
		try:
			execfile(pythonFile, locals)
		except:
			locationInfo = traceback.extract_tb(sys.exc_info()[2])[-1]
			return "%s: '%s' @ %s:%s:%d" % (str(sys.exc_info()[0].__name__), str(sys.exc_info()[1]), os.path.basename(locationInfo[0]), locationInfo[2], locationInfo[1])
	if tempfilename is not None:
		f = open(tempfilename, "r")
		engineResult.setGCode(f.read())
		f.close()
		os.unlink(tempfilename)
	return None

########NEW FILE########
__FILENAME__ = polygon
"""
The polygon module has functions that assist in working with 2D convex polygons.
"""
__copyright__ = "Copyright (C) 2013 David Braam - Released under terms of the AGPLv3 License"

import numpy

def convexHull(pointList):
	""" Create a convex hull from a list of points. """
	def _isRightTurn((p, q, r)):
		sum1 = q[0]*r[1] + p[0]*q[1] + r[0]*p[1]
		sum2 = q[0]*p[1] + r[0]*q[1] + p[0]*r[1]

		if sum1 - sum2 < 0:
			return 1
		else:
			return 0

	unique = {}
	for p in pointList:
		unique[p[0],p[1]] = 1

	points = unique.keys()
	points.sort()
	if len(points) < 1:
		return numpy.zeros((0, 2), numpy.float32)
	if len(points) < 2:
		return numpy.array(points, numpy.float32)

	# Build upper half of the hull.
	upper = [points[0], points[1]]
	for p in points[2:]:
		upper.append(p)
		while len(upper) > 2 and not _isRightTurn(upper[-3:]):
			del upper[-2]

	# Build lower half of the hull.
	points = points[::-1]
	lower = [points[0], points[1]]
	for p in points[2:]:
		lower.append(p)
		while len(lower) > 2 and not _isRightTurn(lower[-3:]):
			del lower[-2]

	# Remove duplicates.
	del lower[0]
	del lower[-1]

	return numpy.array(upper + lower, numpy.float32)

def minkowskiHull(a, b):
	"""Calculate the minkowski hull of 2 convex polygons"""
	points = numpy.zeros((len(a) * len(b), 2))
	for n in xrange(0, len(a)):
		for m in xrange(0, len(b)):
			points[n * len(b) + m] = a[n] + b[m]
	return convexHull(points.copy())

def projectPoly(poly, normal):
	"""
	Project a convex polygon on a given normal.
	A projection of a convex polygon on a infinite line is a finite line.
	Give the min and max value on the normal line.
	"""
	pMin = numpy.dot(normal, poly[0])
	pMax = pMin
	for n in xrange(1 , len(poly)):
		p = numpy.dot(normal, poly[n])
		pMin = min(pMin, p)
		pMax = max(pMax, p)
	return pMin, pMax

def polygonCollision(polyA, polyB):
	""" Check if convexy polygon A and B collide, return True if this is the case. """
	for n in xrange(0, len(polyA)):
		p0 = polyA[n-1]
		p1 = polyA[n]
		normal = (p1 - p0)[::-1]
		normal[1] = -normal[1]
		normal /= numpy.linalg.norm(normal)
		aMin, aMax = projectPoly(polyA, normal)
		bMin, bMax = projectPoly(polyB, normal)
		if aMin > bMax:
			return False
		if bMin > aMax:
			return False
	for n in xrange(0, len(polyB)):
		p0 = polyB[n-1]
		p1 = polyB[n]
		normal = (p1 - p0)[::-1]
		normal[1] = -normal[1]
		normal /= numpy.linalg.norm(normal)
		aMin, aMax = projectPoly(polyA, normal)
		bMin, bMax = projectPoly(polyB, normal)
		if aMin > bMax:
			return False
		if aMax < bMin:
			return False
	return True

def polygonCollisionPushVector(polyA, polyB):
	""" Check if convex polygon A and B collide, return the vector of penetration if this is the case, else return False. """
	retSize = 10000000.0
	ret = False
	for n in xrange(0, len(polyA)):
		p0 = polyA[n-1]
		p1 = polyA[n]
		normal = (p1 - p0)[::-1]
		normal[1] = -normal[1]
		normal /= numpy.linalg.norm(normal)
		aMin, aMax = projectPoly(polyA, normal)
		bMin, bMax = projectPoly(polyB, normal)
		if aMin > bMax:
			return False
		if bMin > aMax:
			return False
		size = min(bMax, bMax) - max(aMin, bMin)
		if size < retSize:
			ret = normal * (size + 0.1)
			retSize = size
	for n in xrange(0, len(polyB)):
		p0 = polyB[n-1]
		p1 = polyB[n]
		normal = (p1 - p0)[::-1]
		normal[1] = -normal[1]
		normal /= numpy.linalg.norm(normal)
		aMin, aMax = projectPoly(polyA, normal)
		bMin, bMax = projectPoly(polyB, normal)
		if aMin > bMax:
			return False
		if aMax < bMin:
			return False
		size = min(bMax, bMax) - max(aMin, bMin)
		if size < retSize:
			ret = normal * -(size + 0.1)
			retSize = size
	return ret

def fullInside(polyA, polyB):
	"""
	Check if convex polygon A is completely inside of convex polygon B.
	"""
	for n in xrange(0, len(polyA)):
		p0 = polyA[n-1]
		p1 = polyA[n]
		normal = (p1 - p0)[::-1]
		normal[1] = -normal[1]
		normal /= numpy.linalg.norm(normal)
		aMin, aMax = projectPoly(polyA, normal)
		bMin, bMax = projectPoly(polyB, normal)
		if aMax > bMax:
			return False
		if aMin < bMin:
			return False
	for n in xrange(0, len(polyB)):
		p0 = polyB[n-1]
		p1 = polyB[n]
		normal = (p1 - p0)[::-1]
		normal[1] = -normal[1]
		normal /= numpy.linalg.norm(normal)
		aMin, aMax = projectPoly(polyA, normal)
		bMin, bMax = projectPoly(polyB, normal)
		if aMax > bMax:
			return False
		if aMin < bMin:
			return False
	return True

def isLeft(a, b, c):
	""" Check if C is left of the infinite line from A to B """
	return ((b[0] - a[0])*(c[1] - a[1]) - (b[1] - a[1])*(c[0] - a[0])) > 0

def lineLineIntersection(p0, p1, p2, p3):
	""" Return the intersection of the infinite line trough points p0 and p1 and infinite line trough points p2 and p3. """
	A1 = p1[1] - p0[1]
	B1 = p0[0] - p1[0]
	C1 = A1*p0[0] + B1*p0[1]

	A2 = p3[1] - p2[1]
	B2 = p2[0] - p3[0]
	C2 = A2 * p2[0] + B2 * p2[1]

	det = A1*B2 - A2*B1
	if det == 0:
		return p0
	return [(B2*C1 - B1*C2)/det, (A1 * C2 - A2 * C1) / det]

def clipConvex(poly0, poly1):
	""" Cut the convex polygon 0 so that it completely fits in convex polygon 1, any part sticking out of polygon 1 is cut off """
	res = poly0
	for p1idx in xrange(0, len(poly1)):
		src = res
		res = []
		p0 = poly1[p1idx-1]
		p1 = poly1[p1idx]
		for n in xrange(0, len(src)):
			p = src[n]
			if not isLeft(p0, p1, p):
				if isLeft(p0, p1, src[n-1]):
					res.append(lineLineIntersection(p0, p1, src[n-1], p))
				res.append(p)
			elif not isLeft(p0, p1, src[n-1]):
				res.append(lineLineIntersection(p0, p1, src[n-1], p))
	return numpy.array(res, numpy.float32)

########NEW FILE########
__FILENAME__ = printableObject
"""
The printableObject module contains a printableObject class,
which is used to represent a single object that can be printed.
A single object can have 1 or more meshes which represent different sections for multi-material extrusion.
"""
__copyright__ = "Copyright (C) 2013 David Braam - Released under terms of the AGPLv3 License"

import time
import math
import os

import numpy
numpy.seterr(all='ignore')

from Cura.util import polygon

class printableObject(object):
	"""
	A printable object is an object that can be printed and is on the build platform.
	It contains 1 or more Meshes. Where more meshes are used for multi-extrusion.

	Each object has a 3x3 transformation matrix to rotate/scale the object.
	This object also keeps track of the 2D boundary polygon used for object collision in the objectScene class.
	"""
	def __init__(self, originFilename):
		self._originFilename = originFilename
		if originFilename is None:
			self._name = 'None'
		else:
			self._name = os.path.basename(originFilename)
		if '.' in self._name:
			self._name = os.path.splitext(self._name)[0]
		self._meshList = []
		self._position = numpy.array([0.0, 0.0])
		self._matrix = numpy.matrix([[1,0,0],[0,1,0],[0,0,1]], numpy.float64)
		self._transformedMin = None
		self._transformedMax = None
		self._transformedSize = None
		self._boundaryCircleSize = None
		self._drawOffset = None
		self._boundaryHull = None
		self._printAreaExtend = numpy.array([[-1,-1],[ 1,-1],[ 1, 1],[-1, 1]], numpy.float32)
		self._headAreaExtend = numpy.array([[-1,-1],[ 1,-1],[ 1, 1],[-1, 1]], numpy.float32)
		self._headMinSize = numpy.array([1, 1], numpy.float32)
		self._printAreaHull = None
		self._headAreaHull = None
		self._headAreaMinHull = None

		self._loadAnim = None

	def copy(self):
		ret = printableObject(self._originFilename)
		ret._matrix = self._matrix.copy()
		ret._transformedMin = self._transformedMin.copy()
		ret._transformedMax = self._transformedMax.copy()
		ret._transformedSize = self._transformedSize.copy()
		ret._boundaryCircleSize = self._boundaryCircleSize
		ret._boundaryHull = self._boundaryHull.copy()
		ret._printAreaExtend = self._printAreaExtend.copy()
		ret._printAreaHull = self._printAreaHull.copy()
		ret._drawOffset = self._drawOffset.copy()
		for m in self._meshList[:]:
			m2 = ret._addMesh()
			m2.vertexes = m.vertexes
			m2.vertexCount = m.vertexCount
			m2.vbo = m.vbo
			m2.vbo.incRef()
		return ret

	def _addMesh(self):
		m = mesh(self)
		self._meshList.append(m)
		return m

	def _postProcessAfterLoad(self):
		for m in self._meshList:
			m._calculateNormals()
		self.processMatrix()
		if numpy.max(self.getSize()) > 10000.0:
			for m in self._meshList:
				m.vertexes /= 1000.0
			self.processMatrix()
		if numpy.max(self.getSize()) < 1.0:
			for m in self._meshList:
				m.vertexes *= 1000.0
			self.processMatrix()

	def applyMatrix(self, m):
		self._matrix *= m
		self.processMatrix()

	def processMatrix(self):
		self._transformedMin = numpy.array([999999999999,999999999999,999999999999], numpy.float64)
		self._transformedMax = numpy.array([-999999999999,-999999999999,-999999999999], numpy.float64)
		self._boundaryCircleSize = 0

		hull = numpy.zeros((0, 2), numpy.int)
		for m in self._meshList:
			transformedVertexes = m.getTransformedVertexes()
			hull = polygon.convexHull(numpy.concatenate((numpy.rint(transformedVertexes[:,0:2]).astype(int), hull), 0))
			transformedMin = transformedVertexes.min(0)
			transformedMax = transformedVertexes.max(0)
			for n in xrange(0, 3):
				self._transformedMin[n] = min(transformedMin[n], self._transformedMin[n])
				self._transformedMax[n] = max(transformedMax[n], self._transformedMax[n])

			#Calculate the boundary circle
			transformedSize = transformedMax - transformedMin
			center = transformedMin + transformedSize / 2.0
			boundaryCircleSize = round(math.sqrt(numpy.max(((transformedVertexes[::,0] - center[0]) * (transformedVertexes[::,0] - center[0])) + ((transformedVertexes[::,1] - center[1]) * (transformedVertexes[::,1] - center[1])) + ((transformedVertexes[::,2] - center[2]) * (transformedVertexes[::,2] - center[2])))), 3)
			self._boundaryCircleSize = max(self._boundaryCircleSize, boundaryCircleSize)
		self._transformedSize = self._transformedMax - self._transformedMin
		self._drawOffset = (self._transformedMax + self._transformedMin) / 2
		self._drawOffset[2] = self._transformedMin[2]
		self._transformedMax -= self._drawOffset
		self._transformedMin -= self._drawOffset

		self._boundaryHull = polygon.minkowskiHull((hull.astype(numpy.float32) - self._drawOffset[0:2]), numpy.array([[-1,-1],[-1,1],[1,1],[1,-1]],numpy.float32))
		self._printAreaHull = polygon.minkowskiHull(self._boundaryHull, self._printAreaExtend)
		self.setHeadArea(self._headAreaExtend, self._headMinSize)

	def getName(self):
		return self._name
	def getOriginFilename(self):
		return self._originFilename
	def getPosition(self):
		return self._position
	def setPosition(self, newPos):
		self._position = newPos
	def getMatrix(self):
		return self._matrix

	def getMaximum(self):
		return self._transformedMax
	def getMinimum(self):
		return self._transformedMin
	def getSize(self):
		return self._transformedSize
	def getDrawOffset(self):
		return self._drawOffset
	def getBoundaryCircle(self):
		return self._boundaryCircleSize

	def setPrintAreaExtends(self, poly):
		self._printAreaExtend = poly
		self._printAreaHull = polygon.minkowskiHull(self._boundaryHull, self._printAreaExtend)

		self.setHeadArea(self._headAreaExtend, self._headMinSize)

	def setHeadArea(self, poly, minSize):
		self._headAreaExtend = poly
		self._headMinSize = minSize
		self._headAreaHull = polygon.minkowskiHull(self._printAreaHull, self._headAreaExtend)
		pMin = numpy.min(self._printAreaHull, 0) - self._headMinSize
		pMax = numpy.max(self._printAreaHull, 0) + self._headMinSize
		square = numpy.array([pMin, [pMin[0], pMax[1]], pMax, [pMax[0], pMin[1]]], numpy.float32)
		self._headAreaMinHull = polygon.clipConvex(self._headAreaHull, square)

	def mirror(self, axis):
		matrix = [[1,0,0], [0, 1, 0], [0, 0, 1]]
		matrix[axis][axis] = -1
		self.applyMatrix(numpy.matrix(matrix, numpy.float64))

	def getScale(self):
		return numpy.array([
			numpy.linalg.norm(self._matrix[::,0].getA().flatten()),
			numpy.linalg.norm(self._matrix[::,1].getA().flatten()),
			numpy.linalg.norm(self._matrix[::,2].getA().flatten())], numpy.float64);

	def setScale(self, scale, axis, uniform):
		currentScale = numpy.linalg.norm(self._matrix[::,axis].getA().flatten())
		scale /= currentScale
		if scale == 0:
			return
		if uniform:
			matrix = [[scale,0,0], [0, scale, 0], [0, 0, scale]]
		else:
			matrix = [[1.0,0,0], [0, 1.0, 0], [0, 0, 1.0]]
			matrix[axis][axis] = scale
		self.applyMatrix(numpy.matrix(matrix, numpy.float64))

	def setSize(self, size, axis, uniform):
		scale = self.getSize()[axis]
		scale = size / scale
		if scale == 0:
			return
		if uniform:
			matrix = [[scale,0,0], [0, scale, 0], [0, 0, scale]]
		else:
			matrix = [[1,0,0], [0, 1, 0], [0, 0, 1]]
			matrix[axis][axis] = scale
		self.applyMatrix(numpy.matrix(matrix, numpy.float64))

	def resetScale(self):
		x = 1/numpy.linalg.norm(self._matrix[::,0].getA().flatten())
		y = 1/numpy.linalg.norm(self._matrix[::,1].getA().flatten())
		z = 1/numpy.linalg.norm(self._matrix[::,2].getA().flatten())
		self.applyMatrix(numpy.matrix([[x,0,0],[0,y,0],[0,0,z]], numpy.float64))

	def resetRotation(self):
		x = numpy.linalg.norm(self._matrix[::,0].getA().flatten())
		y = numpy.linalg.norm(self._matrix[::,1].getA().flatten())
		z = numpy.linalg.norm(self._matrix[::,2].getA().flatten())
		self._matrix = numpy.matrix([[x,0,0],[0,y,0],[0,0,z]], numpy.float64)
		self.processMatrix()

	def layFlat(self):
		transformedVertexes = self._meshList[0].getTransformedVertexes()
		minZvertex = transformedVertexes[transformedVertexes.argmin(0)[2]]
		dotMin = 1.0
		dotV = None
		for v in transformedVertexes:
			diff = v - minZvertex
			len = math.sqrt(diff[0] * diff[0] + diff[1] * diff[1] + diff[2] * diff[2])
			if len < 5:
				continue
			dot = (diff[2] / len)
			if dotMin > dot:
				dotMin = dot
				dotV = diff
		if dotV is None:
			return
		rad = -math.atan2(dotV[1], dotV[0])
		self._matrix *= numpy.matrix([[math.cos(rad), math.sin(rad), 0], [-math.sin(rad), math.cos(rad), 0], [0,0,1]], numpy.float64)
		rad = -math.asin(dotMin)
		self._matrix *= numpy.matrix([[math.cos(rad), 0, math.sin(rad)], [0,1,0], [-math.sin(rad), 0, math.cos(rad)]], numpy.float64)


		transformedVertexes = self._meshList[0].getTransformedVertexes()
		minZvertex = transformedVertexes[transformedVertexes.argmin(0)[2]]
		dotMin = 1.0
		dotV = None
		for v in transformedVertexes:
			diff = v - minZvertex
			len = math.sqrt(diff[1] * diff[1] + diff[2] * diff[2])
			if len < 5:
				continue
			dot = (diff[2] / len)
			if dotMin > dot:
				dotMin = dot
				dotV = diff
		if dotV is None:
			return
		if dotV[1] < 0:
			rad = math.asin(dotMin)
		else:
			rad = -math.asin(dotMin)
		self.applyMatrix(numpy.matrix([[1,0,0], [0, math.cos(rad), math.sin(rad)], [0, -math.sin(rad), math.cos(rad)]], numpy.float64))

	def scaleUpTo(self, size):
		vMin = self._transformedMin
		vMax = self._transformedMax

		scaleX1 = (size[0] / 2 - self._position[0]) / ((vMax[0] - vMin[0]) / 2)
		scaleY1 = (size[1] / 2 - self._position[1]) / ((vMax[1] - vMin[1]) / 2)
		scaleX2 = (self._position[0] + size[0] / 2) / ((vMax[0] - vMin[0]) / 2)
		scaleY2 = (self._position[1] + size[1] / 2) / ((vMax[1] - vMin[1]) / 2)
		scaleZ = size[2] / (vMax[2] - vMin[2])
		scale = min(scaleX1, scaleY1, scaleX2, scaleY2, scaleZ)
		if scale > 0:
			self.applyMatrix(numpy.matrix([[scale,0,0],[0,scale,0],[0,0,scale]], numpy.float64))

	#Split splits an object with multiple meshes into different objects, where each object is a part of the original mesh that has
	# connected faces. This is useful to split up plate STL files.
	def split(self, callback):
		ret = []
		for oriMesh in self._meshList:
			ret += oriMesh.split(callback)
		return ret

	def canStoreAsSTL(self):
		return len(self._meshList) < 2

	#getVertexIndexList returns an array of vertexes, and an integer array for each mesh in this object.
	# the integer arrays are indexes into the vertex array for each triangle in the model.
	def getVertexIndexList(self):
		vertexMap = {}
		vertexList = []
		meshList = []
		for m in self._meshList:
			verts = m.getTransformedVertexes(True)
			meshIdxList = []
			for idx in xrange(0, len(verts)):
				v = verts[idx]
				hashNr = int(v[0] * 100) | int(v[1] * 100) << 10 | int(v[2] * 100) << 20
				vIdx = None
				if hashNr in vertexMap:
					for idx2 in vertexMap[hashNr]:
						if numpy.linalg.norm(v - vertexList[idx2]) < 0.001:
							vIdx = idx2
				if vIdx is None:
					vIdx = len(vertexList)
					vertexMap[hashNr] = [vIdx]
					vertexList.append(v)
				meshIdxList.append(vIdx)
			meshList.append(numpy.array(meshIdxList, numpy.int32))
		return numpy.array(vertexList, numpy.float32), meshList

class mesh(object):
	"""
	A mesh is a list of 3D triangles build from vertexes. Each triangle has 3 vertexes.

	A "VBO" can be associated with this object, which is used for rendering this object.
	"""
	def __init__(self, obj):
		self.vertexes = None
		self.vertexCount = 0
		self.vbo = None
		self._obj = obj

	def _addFace(self, x0, y0, z0, x1, y1, z1, x2, y2, z2):
		n = self.vertexCount
		self.vertexes[n][0] = x0
		self.vertexes[n][1] = y0
		self.vertexes[n][2] = z0
		n += 1
		self.vertexes[n][0] = x1
		self.vertexes[n][1] = y1
		self.vertexes[n][2] = z1
		n += 1
		self.vertexes[n][0] = x2
		self.vertexes[n][1] = y2
		self.vertexes[n][2] = z2
		self.vertexCount += 3
	
	def _prepareFaceCount(self, faceNumber):
		#Set the amount of faces before loading data in them. This way we can create the numpy arrays before we fill them.
		self.vertexes = numpy.zeros((faceNumber*3, 3), numpy.float32)
		self.normal = numpy.zeros((faceNumber*3, 3), numpy.float32)
		self.vertexCount = 0

	def _calculateNormals(self):
		#Calculate the normals
		tris = self.vertexes.reshape(self.vertexCount / 3, 3, 3)
		normals = numpy.cross( tris[::,1 ] - tris[::,0]  , tris[::,2 ] - tris[::,0] )
		lens = numpy.sqrt( normals[:,0]**2 + normals[:,1]**2 + normals[:,2]**2 )
		normals[:,0] /= lens
		normals[:,1] /= lens
		normals[:,2] /= lens
		
		n = numpy.zeros((self.vertexCount / 3, 9), numpy.float32)
		n[:,0:3] = normals
		n[:,3:6] = normals
		n[:,6:9] = normals
		self.normal = n.reshape(self.vertexCount, 3)
		self.invNormal = -self.normal

	def _vertexHash(self, idx):
		v = self.vertexes[idx]
		return int(v[0] * 100) | int(v[1] * 100) << 10 | int(v[2] * 100) << 20

	def _idxFromHash(self, map, idx):
		vHash = self._vertexHash(idx)
		for i in map[vHash]:
			if numpy.linalg.norm(self.vertexes[i] - self.vertexes[idx]) < 0.001:
				return i

	def getTransformedVertexes(self, applyOffsets = False):
		if applyOffsets:
			pos = self._obj._position.copy()
			pos.resize((3))
			pos[2] = self._obj.getSize()[2] / 2
			offset = self._obj._drawOffset.copy()
			offset[2] += self._obj.getSize()[2] / 2
			return (numpy.matrix(self.vertexes, copy = False) * numpy.matrix(self._obj._matrix, numpy.float32)).getA() - offset + pos
		return (numpy.matrix(self.vertexes, copy = False) * numpy.matrix(self._obj._matrix, numpy.float32)).getA()

	def split(self, callback):
		vertexMap = {}

		vertexToFace = []
		for idx in xrange(0, self.vertexCount):
			if (idx % 100) == 0:
				callback(idx * 100 / self.vertexCount)
			vHash = self._vertexHash(idx)
			if vHash not in vertexMap:
				vertexMap[vHash] = []
			vertexMap[vHash].append(idx)
			vertexToFace.append([])

		faceList = []
		for idx in xrange(0, self.vertexCount, 3):
			if (idx % 100) == 0:
				callback(idx * 100 / self.vertexCount)
			f = [self._idxFromHash(vertexMap, idx), self._idxFromHash(vertexMap, idx+1), self._idxFromHash(vertexMap, idx+2)]
			vertexToFace[f[0]].append(idx / 3)
			vertexToFace[f[1]].append(idx / 3)
			vertexToFace[f[2]].append(idx / 3)
			faceList.append(f)

		ret = []
		doneSet = set()
		for idx in xrange(0, len(faceList)):
			if idx in doneSet:
				continue
			doneSet.add(idx)
			todoList = [idx]
			meshFaceList = []
			while len(todoList) > 0:
				idx = todoList.pop()
				meshFaceList.append(idx)
				for n in xrange(0, 3):
					for i in vertexToFace[faceList[idx][n]]:
						if not i in doneSet:
							doneSet.add(i)
							todoList.append(i)

			obj = printableObject(self._obj.getOriginFilename())
			obj._matrix = self._obj._matrix.copy()
			m = obj._addMesh()
			m._prepareFaceCount(len(meshFaceList))
			for idx in meshFaceList:
				m.vertexes[m.vertexCount] = self.vertexes[faceList[idx][0]]
				m.vertexCount += 1
				m.vertexes[m.vertexCount] = self.vertexes[faceList[idx][1]]
				m.vertexCount += 1
				m.vertexes[m.vertexCount] = self.vertexes[faceList[idx][2]]
				m.vertexCount += 1
			obj._postProcessAfterLoad()
			ret.append(obj)
		return ret

########NEW FILE########
__FILENAME__ = doodle3dConnect
"""
Doodle3D printer connection. Auto-detects any Doodle3D boxes on the local network, and finds if they have a printer connected.
This connection can then be used to send GCode to the printer.
"""
__copyright__ = "Copyright (C) 2013 David Braam - Released under terms of the AGPLv3 License"

import threading
import json
import httplib as httpclient
import urllib
import time

from Cura.util.printerConnection import printerConnectionBase

class doodle3dConnectionGroup(printerConnectionBase.printerConnectionGroup):
	"""
	The Doodle3D connection group runs a thread to poll for Doodle3D boxes.
	For each Doodle3D box it finds, it creates a Doodle3DConnect object.
	"""
	PRINTER_LIST_HOST = 'connect.doodle3d.com'
	PRINTER_LIST_PATH = '/api/list.php'

	def __init__(self):
		super(doodle3dConnectionGroup, self).__init__("Doodle3D")
		self._http = None
		self._host = self.PRINTER_LIST_HOST
		self._connectionMap = {}

		self._thread = threading.Thread(target=self._doodle3DThread)
		self._thread.daemon = True
		self._thread.start()

	def getAvailableConnections(self):
		return filter(lambda c: c.isAvailable(), self._connectionMap.values())

	def remove(self, host):
		del self._connectionMap[host]

	def getIconID(self):
		return 27

	def getPriority(self):
		return 100

	def _doodle3DThread(self):
		self._waitDelay = 0
		while True:
			printerList = self._request('GET', self.PRINTER_LIST_PATH)
			if not printerList or type(printerList) is not dict or 'data' not in printerList or type(printerList['data']) is not list:
				#Check if we are connected to the Doodle3D box in access point mode, as this gives an
				# invalid reply on the printer list API
				printerList = {'data': [{'localip': 'draw.doodle3d.com'}]}

			#Add the 192.168.5.1 IP to the list of printers to check, as this is the LAN port IP, which could also be available.
			# (connect.doodle3d.com also checks for this IP in the javascript code)
			printerList['data'].append({'localip': '192.168.5.1'})

			#Check the status of each possible IP, if we find a valid box with a printer connected. Use that IP.
			for possiblePrinter in printerList['data']:
				if possiblePrinter['localip'] not in self._connectionMap:
					status = self._request('GET', '/d3dapi/config/?network.cl.wifiboxid=', host=possiblePrinter['localip'])
					if status and 'data' in status and 'network.cl.wifiboxid' in status['data']:
						name = status['data']['network.cl.wifiboxid']
						if 'wifiboxid' in possiblePrinter:
							name = possiblePrinter['wifiboxid']
						self._connectionMap[possiblePrinter['localip']] = doodle3dConnect(possiblePrinter['localip'], name, self)

			# Delay a bit more after every request. This so we do not stress the connect.doodle3d.com api too much
			if self._waitDelay < 10:
				self._waitDelay += 1
			time.sleep(self._waitDelay * 60)

	def _request(self, method, path, postData = None, host = None):
		if host is None:
			host = self._host
		if self._http is None or self._http.host != host:
			self._http = httpclient.HTTPConnection(host, timeout=30)

		try:
			if postData is not None:
				self._http.request(method, path, urllib.urlencode(postData), {"Content-type": "application/x-www-form-urlencoded", "User-Agent": "Cura Doodle3D connection"})
			else:
				self._http.request(method, path, headers={"Content-type": "application/x-www-form-urlencoded", "User-Agent": "Cura Doodle3D connection"})
		except:
			self._http.close()
			return None
		try:
			response = self._http.getresponse()
			responseText = response.read()
		except:
			self._http.close()
			return None
		try:
			response = json.loads(responseText)
		except ValueError:
			self._http.close()
			return None
		if response['status'] != 'success':
			return False

		return response

class doodle3dConnect(printerConnectionBase.printerConnectionBase):
	"""
	Class to connect and print files with the doodle3d.com wifi box
	Auto-detects if the Doodle3D box is available with a printer and handles communication with the Doodle3D API
	"""
	def __init__(self, host, name, group):
		super(doodle3dConnect, self).__init__(name)

		self._http = None
		self._group = group
		self._host = host

		self._isAvailable = False
		self._printing = False
		self._fileBlocks = []
		self._commandList = []
		self._blockIndex = None
		self._lineCount = 0
		self._progressLine = 0
		self._hotendTemperature = [None] * 4
		self._bedTemperature = None
		self._errorCount = 0
		self._interruptSleep = False

		self.checkThread = threading.Thread(target=self._doodle3DThread)
		self.checkThread.daemon = True
		self.checkThread.start()

	#Load the file into memory for printing.
	def loadGCodeData(self, dataStream):
		if self._printing:
			return False
		self._fileBlocks = []
		self._lineCount = 0
		block = []
		blockSize = 0
		for line in dataStream:
			#Strip out comments, we do not need to send comments
			if ';' in line:
				line = line[:line.index(';')]
			#Strip out whitespace at the beginning/end this saves data to send.
			line = line.strip()

			if len(line) < 1:
				continue
			self._lineCount += 1
			#Put the lines in 8k sized blocks, so we can send those blocks as http requests.
			if blockSize + len(line) > 1024 * 8:
				self._fileBlocks.append('\n'.join(block) + '\n')
				block = []
				blockSize = 0
			blockSize += len(line) + 1
			block.append(line)
		self._fileBlocks.append('\n'.join(block) + '\n')
		self._doCallback()
		return True

	#Start printing the previously loaded file
	def startPrint(self):
		if self._printing or len(self._fileBlocks) < 1:
			return
		self._progressLine = 0
		self._blockIndex = 0
		self._printing = True
		self._interruptSleep = True

	#Abort the previously loaded print file
	def cancelPrint(self):
		if not self._printing:
			return
		if self._request('POST', '/d3dapi/printer/stop', {'gcode': 'M104 S0\nG28'}):
			self._printing = False

	def isPrinting(self):
		return self._printing

	#Amount of progression of the current print file. 0.0 to 1.0
	def getPrintProgress(self):
		if self._lineCount < 1:
			return 0.0
		return float(self._progressLine) / float(self._lineCount)

	# Return if the printer with this connection type is available
	def isAvailable(self):
		return self._isAvailable

	#Are we able to send a direct coammand with sendCommand at this moment in time.
	def isAbleToSendDirectCommand(self):
		#The delay on direct commands is very high and so we disabled it.
		return False #self._isAvailable and not self._printing

	#Directly send a command to the printer.
	def sendCommand(self, command):
		if not self._isAvailable or self._printing:
			return
		self._commandList.append(command)
		self._interruptSleep = True

	# Get the connection status string. This is displayed to the user and can be used to communicate
	#  various information to the user.
	def getStatusString(self):
		if not self._isAvailable:
			return "Doodle3D box not found"
		if self._printing:
			if self._blockIndex < len(self._fileBlocks):
				ret = "Sending GCode: %.1f%%" % (float(self._blockIndex) * 100.0 / float(len(self._fileBlocks)))
			elif len(self._fileBlocks) > 0:
				ret = "Finished sending GCode to Doodle3D box."
			else:
				ret = "Different print still running..."
			#ret += "\nErrorCount: %d" % (self._errorCount)
			return ret
		return "Printer found, waiting for print command."

	#Get the temperature of an extruder, returns None is no temperature is known for this extruder
	def getTemperature(self, extruder):
		return self._hotendTemperature[extruder]

	#Get the temperature of the heated bed, returns None is no temperature is known for the heated bed
	def getBedTemperature(self):
		return self._bedTemperature

	def _doodle3DThread(self):
		while True:
			stateReply = self._request('GET', '/d3dapi/info/status')
			if stateReply is None or not stateReply:
				# No API, wait 5 seconds before looking for Doodle3D again.
				# API gave back an error (this can happen if the Doodle3D box is connecting to the printer)
				# The Doodle3D box could also be offline, if we reach a high enough errorCount then assume the box is gone.
				self._errorCount += 1
				if self._errorCount > 10:
					if self._isAvailable:
						self._printing = False
						self._isAvailable = False
						self._doCallback()
					self._sleep(15)
					self._group.remove(self._host)
					return
				else:
					self._sleep(3)
				continue
			if stateReply['data']['state'] == 'disconnected':
				# No printer connected, we do not have a printer available, but the Doodle3D box is there.
				# So keep trying to find a printer connected to it.
				if self._isAvailable:
					self._printing = False
					self._isAvailable = False
					self._doCallback()
				self._sleep(15)
				continue
			self._errorCount = 0

			#We got a valid status, set the doodle3d printer as available.
			if not self._isAvailable:
				self._isAvailable = True

			if 'hotend' in stateReply['data']:
				self._hotendTemperature[0] = stateReply['data']['hotend']
			if 'bed' in stateReply['data']:
				self._bedTemperature = stateReply['data']['bed']

			if stateReply['data']['state'] == 'idle' or stateReply['data']['state'] == 'buffering':
				if self._printing:
					if self._blockIndex < len(self._fileBlocks):
						if self._request('POST', '/d3dapi/printer/print', {'gcode': self._fileBlocks[self._blockIndex], 'start': 'True', 'first': 'True'}):
							self._blockIndex += 1
						else:
							self._sleep(1)
					else:
						self._printing = False
				else:
					if len(self._commandList) > 0:
						if self._request('POST', '/d3dapi/printer/print', {'gcode': self._commandList[0], 'start': 'True', 'first': 'True'}):
							self._commandList.pop(0)
						else:
							self._sleep(1)
					else:
						self._sleep(5)
			elif stateReply['data']['state'] == 'printing':
				if self._printing:
					if self._blockIndex < len(self._fileBlocks):
						for n in xrange(0, 5):
							if self._blockIndex < len(self._fileBlocks):
								if self._request('POST', '/d3dapi/printer/print', {'gcode': self._fileBlocks[self._blockIndex]}):
									self._blockIndex += 1
								else:
									#Cannot send new block, wait a bit, so we do not overload the API
									self._sleep(15)
									break
					else:
						#If we are no longer sending new GCode delay a bit so we request the status less often.
						self._sleep(5)
					if 'current_line' in stateReply['data']:
						self._progressLine = stateReply['data']['current_line']
				else:
					#Got a printing state without us having send the print file, set the state to printing, but make sure we never send anything.
					if 'current_line' in stateReply['data'] and 'total_lines' in stateReply['data'] and stateReply['data']['total_lines'] > 2:
						self._printing = True
						self._fileBlocks = []
						self._blockIndex = 1
						self._progressLine = stateReply['data']['current_line']
						self._lineCount = stateReply['data']['total_lines']
					self._sleep(5)
			self._doCallback()

	def _sleep(self, timeOut):
		while timeOut > 0.0:
			if not self._interruptSleep:
				time.sleep(0.1)
			timeOut -= 0.1
		self._interruptSleep = False

	def _request(self, method, path, postData = None, host = None):
		if host is None:
			host = self._host
		if self._http is None or self._http.host != host:
			self._http = httpclient.HTTPConnection(host, timeout=30)

		try:
			if postData is not None:
				self._http.request(method, path, urllib.urlencode(postData), {"Content-type": "application/x-www-form-urlencoded", "User-Agent": "Cura Doodle3D connection"})
			else:
				self._http.request(method, path, headers={"Content-type": "application/x-www-form-urlencoded", "User-Agent": "Cura Doodle3D connection"})
		except:
			self._http.close()
			return None
		try:
			response = self._http.getresponse()
			responseText = response.read()
		except:
			self._http.close()
			return None
		try:
			response = json.loads(responseText)
		except ValueError:
			self._http.close()
			return None
		if response['status'] != 'success':
			return False

		return response

if __name__ == '__main__':
	d = doodle3dConnect()
	print 'Searching for Doodle3D box'
	while not d.isAvailable():
		time.sleep(1)

	while d.isPrinting():
		print 'Doodle3D already printing! Requesting stop!'
		d.cancelPrint()
		time.sleep(5)

	print 'Doodle3D box found, printing!'
	d.loadFile("C:/Models/belt-tensioner-wave_export.gcode")
	d.startPrint()
	while d.isPrinting() and d.isAvailable():
		time.sleep(1)
		print d.getTemperature(0), d.getStatusString(), d.getPrintProgress(), d._progressLine, d._lineCount, d._blockIndex, len(d._fileBlocks)
	print 'Done'

########NEW FILE########
__FILENAME__ = dummyConnection
"""
The dummy connection is a virtual printer connection which simulates the connection to a printer without doing anything.
This is only enabled when you have a development version. And is used for debugging.
"""
__copyright__ = "Copyright (C) 2013 David Braam - Released under terms of the AGPLv3 License"

import threading
import json
import httplib as httpclient
import urllib
import time

from Cura.util.printerConnection import printerConnectionBase

class dummyConnectionGroup(printerConnectionBase.printerConnectionGroup):
	"""
	Group used for dummy conections. Always shows 2 dummy connections for debugging.
	Has a very low priority so it does not prevent other connections from taking priority.
	"""
	def __init__(self):
		super(dummyConnectionGroup, self).__init__("Dummy")
		self._list = [dummyConnection("Dummy 1"), dummyConnection("Dummy 2")]

	def getAvailableConnections(self):
		return self._list

	def getIconID(self):
		return 5

	def getPriority(self):
		return -100

class dummyConnection(printerConnectionBase.printerConnectionBase):
	"""
	A dummy printer class to debug printer windows.
	"""
	def __init__(self, name):
		super(dummyConnection, self).__init__(name)

		self._printing = False
		self._lineCount = 0
		self._progressLine = 0

		self.printThread = threading.Thread(target=self._dummyThread)
		self.printThread.daemon = True
		self.printThread.start()

	#Load the data into memory for printing, returns True on success
	def loadGCodeData(self, dataStream):
		if self._printing:
			return False
		self._lineCount = 0
		for line in dataStream:
			#Strip out comments, we do not need to send comments
			if ';' in line:
				line = line[:line.index(';')]
			#Strip out whitespace at the beginning/end this saves data to send.
			line = line.strip()

			if len(line) < 1:
				continue
			self._lineCount += 1
		self._doCallback()
		return True

	#Start printing the previously loaded file
	def startPrint(self):
		print 'startPrint', self._printing, self._lineCount
		if self._printing or self._lineCount < 1:
			return
		self._progressLine = 0
		self._printing = True

	#Abort the previously loaded print file
	def cancelPrint(self):
		self._printing = False

	def isPrinting(self):
		return self._printing

	#Amount of progression of the current print file. 0.0 to 1.0
	def getPrintProgress(self):
		if self._lineCount < 1:
			return 0.0
		return float(self._progressLine) / float(self._lineCount)

	# Return if the printer with this connection type is available
	def isAvailable(self):
		return True

	# Get the connection status string. This is displayed to the user and can be used to communicate
	#  various information to the user.
	def getStatusString(self):
		return "DUMMY!:%i %i:%i" % (self._progressLine, self._lineCount, self._printing)

	def _dummyThread(self):
		while True:
			if not self._printing:
				time.sleep(5)
				self._doCallback()
			else:
				time.sleep(0.01)
				self._progressLine += 1
				if self._progressLine == self._lineCount:
					self._printing = False
				self._doCallback()

########NEW FILE########
__FILENAME__ = printerConnectionBase
"""
Base of all printer connections. A printer connection is a way a connection can be made with a printer.
The connections are based on a group, where each group can have 1 or more connections.
"""
__copyright__ = "Copyright (C) 2013 David Braam - Released under terms of the AGPLv3 License"

import traceback

class printerConnectionGroup(object):
	"""
	Base for the printer connection group, needs to be subclassed.
	Has functions for all available connections, getting the name, icon and priority.

	The getIconID, getPriority and getAvailableConnections functions should be overloaded in a subclass.
	"""
	def __init__(self, name):
		self._name = name

	def getAvailableConnections(self):
		return []

	def getName(self):
		return self._name

	def getIconID(self):
		return 5

	def getPriority(self):
		return -100

	def __cmp__(self, other):
		return self.getPriority() - other.getPriority()

	def __repr__(self):
		return '%s %d' % (self._name, self.getPriority())

class printerConnectionBase(object):
	"""
	Base class for different printer connection implementations.
		A printer connection can connect to printers in different ways, trough network, USB or carrier pigeons.
		Each printer connection has different capabilities that you can query with the "has" functions.
		Each printer connection has a state that you can query with the "is" functions.
		Each printer connection has callback objects that receive status updates from the printer when information changes.
	"""
	def __init__(self, name):
		self._callbackList = []
		self._name = name
		self.window = None

	def getName(self):
		return self._name

	#Load the data into memory for printing, returns True on success
	def loadGCodeData(self, dataStream):
		return False

	#Start printing the previously loaded file
	def startPrint(self):
		pass

	#Abort the previously loaded print file
	def cancelPrint(self):
		pass

	def isPrinting(self):
		return False

	#Amount of progression of the current print file. 0.0 to 1.0
	def getPrintProgress(self):
		return 0.0

	#Returns true if we need to establish an active connection.
	# Depending on the type of the connection some types do not need an active connection (Doodle3D WiFi Box for example)
	def hasActiveConnection(self):
		return False

	#Open the active connection to the printer so we can send commands
	def openActiveConnection(self):
		pass

	#Close the active connection to the printer
	def closeActiveConnection(self):
		pass

	#Is the active connection open right now.
	def isActiveConnectionOpen(self):
		return False

	#Are we trying to open an active connection right now.
	def isActiveConnectionOpening(self):
		return False

	#Returns true if we have the ability to pause the file printing.
	def hasPause(self):
		return False

	def isPaused(self):
		return False

	#Pause or unpause the printing depending on the value, if supported.
	def pause(self, value):
		pass

	#Are we able to send a direct coammand with sendCommand at this moment in time.
	def isAbleToSendDirectCommand(self):
		return False

	#Directly send a command to the printer.
	def sendCommand(self, command):
		pass

	# Return if the printer with this connection type is available for possible printing right now.
	#  It is used to auto-detect which connection should default to the print button.
	#  This means the printer is detected, but no connection has been made yet.
	#  Example: COM port is detected, but no connection has been made.
	#  Example: WiFi box is detected and is ready to print with a printer connected
	def isAvailable(self):
		return False

	#Get the temperature of an extruder, returns None is no temperature is known for this extruder
	def getTemperature(self, extruder):
		return None

	#Get the temperature of the heated bed, returns None is no temperature is known for the heated bed
	def getBedTemperature(self):
		return None

	# Get the connection status string. This is displayed to the user and can be used to communicate
	#  various information to the user.
	def getStatusString(self):
		return "TODO"

	def addCallback(self, callback):
		self._callbackList.append(callback)

	def removeCallback(self, callback):
		if callback in self._callbackList:
			self._callbackList.remove(callback)

	#Returns true if we got some kind of error. The getErrorLog returns all the information to diagnose the problem.
	def isInErrorState(self):
		return False
	#Returns the error log in case there was an error.
	def getErrorLog(self):
		return ""

	#Run a callback, this can be ran from a different thread, the receivers of the callback need to make sure they are thread safe.
	def _doCallback(self, param=None):
		for callback in self._callbackList:
			try:
				callback(self, param)
			except:
				self.removeCallback(callback)
				traceback.print_exc()

########NEW FILE########
__FILENAME__ = printerConnectionManager
"""
The printer connection manager keeps track of all the possible printer connections that can be made.
It sorts them by priority and gives easy access to the first available connection type.

This is used by the print/save button to give access to the first available print connection.
As well as listing all printers under the right mouse button.
"""
__copyright__ = "Copyright (C) 2013 David Braam - Released under terms of the AGPLv3 License"

from Cura.util import profile
from Cura.util import version
from Cura.util.printerConnection import dummyConnection
from Cura.util.printerConnection import serialConnection
from Cura.util.printerConnection import doodle3dConnect

class PrinterConnectionManager(object):
	"""
	The printer connection manager has one of each printer connection groups. Sorted on priority.
	It can retrieve the first available connection as well as all available connections.
	"""
	def __init__(self):
		self._groupList = []
		if version.isDevVersion():
			self._groupList.append(dummyConnection.dummyConnectionGroup())
		self._groupList.append(serialConnection.serialConnectionGroup())
		self._groupList.append(doodle3dConnect.doodle3dConnectionGroup())

		#Sort the connections by highest priority first.
		self._groupList.sort(reverse=True)

	#Return the highest priority available connection.
	def getAvailableGroup(self):
		if profile.getMachineSetting('gcode_flavor') == 'UltiGCode':
			return None
		for g in self._groupList:
			if len(g.getAvailableConnections()) > 0:
				return g
		return None

	#Return all available connections.
	def getAvailableConnections(self):
		ret = []
		for e in self._groupList:
			ret += e.getAvailableConnections()
		return ret

########NEW FILE########
__FILENAME__ = serialConnection
"""
The serial/USB printer connection. Uses a 2nd python process to connect to the printer so we never
have locking problems where other threads in python can block the USB printing.
"""
__copyright__ = "Copyright (C) 2013 David Braam - Released under terms of the AGPLv3 License"

import threading
import time
import platform
import os
import sys
import subprocess
import json

from Cura.util import profile
from Cura.util import machineCom
from Cura.util.printerConnection import printerConnectionBase

class serialConnectionGroup(printerConnectionBase.printerConnectionGroup):
	"""
	The serial connection group. Keeps track of all available serial ports,
	and builds a serialConnection for each port.
	"""
	def __init__(self):
		super(serialConnectionGroup, self).__init__("USB")
		self._connectionMap = {}

	def getAvailableConnections(self):
		if profile.getMachineSetting('serial_port') == 'AUTO':
			serialList = machineCom.serialList(True)
		else:
			serialList = [profile.getMachineSetting('serial_port')]
		for port in serialList:
			if port not in self._connectionMap:
				self._connectionMap[port] = serialConnection(port)
		for key in self._connectionMap.keys():
			if key not in serialList and not self._connectionMap[key].isActiveConnectionOpen():
				self._connectionMap.pop(key)
		return self._connectionMap.values()

	def getIconID(self):
		return 6

	def getPriority(self):
		return 50

class serialConnection(printerConnectionBase.printerConnectionBase):
	"""
	A serial connection. Needs to build an active-connection.
	When an active connection is created, a 2nd python process is spawned which handles the actual serial communication.

	This class communicates with the Cura.serialCommunication module trough stdin/stdout pipes.
	"""
	def __init__(self, port):
		super(serialConnection, self).__init__(port)
		self._portName = port

		self._process = None
		self._thread = None

		self._temperature = []
		self._targetTemperature = []
		self._bedTemperature = 0
		self._targetBedTemperature = 0
		self._log = []

		self._commState = None
		self._commStateString = None
		self._gcodeData = []

	#Load the data into memory for printing, returns True on success
	def loadGCodeData(self, dataStream):
		if self.isPrinting() is None:
			return False
		self._gcodeData = []
		for line in dataStream:
			#Strip out comments, we do not need to send comments
			if ';' in line:
				line = line[:line.index(';')]
			#Strip out whitespace at the beginning/end this saves data to send.
			line = line.strip()

			if len(line) < 1:
				continue
			self._gcodeData.append(line)
		return True

	#Start printing the previously loaded file
	def startPrint(self):
		if self.isPrinting() or len(self._gcodeData) < 1 or self._process is None:
			return
		self._process.stdin.write('STOP\n')
		for line in self._gcodeData:
			self._process.stdin.write('G:%s\n' % (line))
		self._process.stdin.write('START\n')
		self._printProgress = 0

	#Abort the previously loaded print file
	def cancelPrint(self):
		if not self.isPrinting()or self._process is None:
			return
		self._process.stdin.write('STOP\n')
		self._printProgress = 0

	def isPrinting(self):
		return self._commState == machineCom.MachineCom.STATE_PRINTING

	#Amount of progression of the current print file. 0.0 to 1.0
	def getPrintProgress(self):
		if len(self._gcodeData) < 1:
			return 0.0
		return float(self._printProgress) / float(len(self._gcodeData))

	# Return if the printer with this connection type is available
	def isAvailable(self):
		return True

	# Get the connection status string. This is displayed to the user and can be used to communicate
	#  various information to the user.
	def getStatusString(self):
		return "%s" % (self._commStateString)

	#Returns true if we need to establish an active connection. True for serial connections.
	def hasActiveConnection(self):
		return True

	#Open the active connection to the printer so we can send commands
	def openActiveConnection(self):
		self.closeActiveConnection()
		self._thread = threading.Thread(target=self._serialCommunicationThread)
		self._thread.daemon = True
		self._thread.start()

	#Close the active connection to the printer
	def closeActiveConnection(self):
		if self._process is not None:
			self._process.terminate()
			self._thread.join()

	#Is the active connection open right now.
	def isActiveConnectionOpen(self):
		if self._process is None:
			return False
		return self._commState == machineCom.MachineCom.STATE_OPERATIONAL or self._commState == machineCom.MachineCom.STATE_PRINTING or self._commState == machineCom.MachineCom.STATE_PAUSED

	#Are we trying to open an active connection right now.
	def isActiveConnectionOpening(self):
		if self._process is None:
			return False
		return self._commState == machineCom.MachineCom.STATE_OPEN_SERIAL or self._commState == machineCom.MachineCom.STATE_CONNECTING or self._commState == machineCom.MachineCom.STATE_DETECT_SERIAL or self._commState == machineCom.MachineCom.STATE_DETECT_BAUDRATE

	def getTemperature(self, extruder):
		if extruder >= len(self._temperature):
			return None
		return self._temperature[extruder]

	def getBedTemperature(self):
		return self._bedTemperature

	#Are we able to send a direct command with sendCommand at this moment in time.
	def isAbleToSendDirectCommand(self):
		return self.isActiveConnectionOpen()

	#Directly send a command to the printer.
	def sendCommand(self, command):
		if self._process is None:
			return
		self._process.stdin.write('C:%s\n' % (command))

	#Returns true if we got some kind of error. The getErrorLog returns all the information to diagnose the problem.
	def isInErrorState(self):
		return self._commState == machineCom.MachineCom.STATE_ERROR or self._commState == machineCom.MachineCom.STATE_CLOSED_WITH_ERROR

	#Returns the error log in case there was an error.
	def getErrorLog(self):
		return '\n'.join(self._log)

	def _serialCommunicationThread(self):
		if platform.system() == "Darwin" and hasattr(sys, 'frozen'):
			cmdList = [os.path.join(os.path.dirname(sys.executable), 'Cura'), '--serialCommunication']
			cmdList += [self._portName + ':' + profile.getMachineSetting('serial_baud')]
		else:
			cmdList = [sys.executable, '-m', 'Cura.serialCommunication']
			cmdList += [self._portName, profile.getMachineSetting('serial_baud')]
		if platform.system() == "Darwin":
			if platform.machine() == 'i386':
				cmdList = ['arch', '-i386'] + cmdList
		self._process = subprocess.Popen(cmdList, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
		line = self._process.stdout.readline()
		while len(line) > 0:
			line = line.strip()
			line = line.split(':', 1)
			if line[0] == '':
				pass
			elif line[0] == 'log':
				self._log.append(line[1])
				if len(self._log) > 30:
					self._log.pop(0)
			elif line[0] == 'temp':
				line = line[1].split(':')
				self._temperature = json.loads(line[0])
				self._targetTemperature = json.loads(line[1])
				self._bedTemperature = float(line[2])
				self._targetBedTemperature = float(line[3])
				self._doCallback()
			elif line[0] == 'message':
				self._doCallback(line[1])
			elif line[0] == 'state':
				line = line[1].split(':', 1)
				self._commState = int(line[0])
				self._commStateString = line[1]
				self._doCallback()
			elif line[0] == 'progress':
				self._printProgress = int(line[1])
				self._doCallback()
			else:
				print line
			line = self._process.stdout.readline()
		self._process = None

########NEW FILE########
__FILENAME__ = profile
"""
The profile module contains all the settings for Cura.
These settings can be globally accessed and modified.
"""
from __future__ import division
__copyright__ = "Copyright (C) 2013 David Braam - Released under terms of the AGPLv3 License"

import os
import traceback
import math
import re
import zlib
import base64
import time
import sys
import platform
import glob
import string
import stat
import types
import cPickle as pickle
import numpy
if sys.version_info[0] < 3:
	import ConfigParser
else:
	import configparser as ConfigParser

from Cura.util import version
from Cura.util import validators

#The settings dictionary contains a key/value reference to all possible settings. With the setting name as key.
settingsDictionary = {}
#The settings list is used to keep a full list of all the settings. This is needed to keep the settings in the proper order,
# as the dictionary will not contain insertion order.
settingsList = []

#Currently selected machine (by index) Cura support multiple machines in the same preferences and can switch between them.
# Each machine has it's own index and unique name.
_selectedMachineIndex = 0

class setting(object):
	"""
		A setting object contains a configuration setting. These are globally accessible trough the quick access functions
		and trough the settingsDictionary function.
		Settings can be:
		* profile settings (settings that effect the slicing process and the print result)
		* preferences (settings that effect how cura works and acts)
		* machine settings (settings that relate to the physical configuration of your machine)
		* alterations (bad name copied from Skeinforge. These are the start/end code pieces)
		Settings have validators that check if the value is valid, but do not prevent invalid values!
		Settings have conditions that enable/disable this setting depending on other settings. (Ex: Dual-extrusion)
	"""
	def __init__(self, name, default, type, category, subcategory):
		self._name = name
		self._label = name
		self._tooltip = ''
		self._default = unicode(default)
		self._values = []
		self._type = type
		self._category = category
		self._subcategory = subcategory
		self._validators = []
		self._conditions = []

		if type is types.FloatType:
			validators.validFloat(self)
		elif type is types.IntType:
			validators.validInt(self)

		global settingsDictionary
		settingsDictionary[name] = self
		global settingsList
		settingsList.append(self)

	def setLabel(self, label, tooltip = ''):
		self._label = label
		self._tooltip = tooltip
		return self

	def setRange(self, minValue=None, maxValue=None):
		if len(self._validators) < 1:
			return
		self._validators[0].minValue = minValue
		self._validators[0].maxValue = maxValue
		return self

	def getLabel(self):
		return _(self._label)

	def getTooltip(self):
		return _(self._tooltip)

	def getCategory(self):
		return self._category

	def getSubCategory(self):
		return self._subcategory

	def isPreference(self):
		return self._category == 'preference'

	def isMachineSetting(self):
		return self._category == 'machine'

	def isAlteration(self):
		return self._category == 'alteration'

	def isProfile(self):
		return not self.isAlteration() and not self.isPreference() and not self.isMachineSetting()

	def getName(self):
		return self._name

	def getType(self):
		return self._type

	def getValue(self, index = None):
		if index is None:
			index = self.getValueIndex()
		if index >= len(self._values):
			return self._default
		return self._values[index]

	def getDefault(self):
		return self._default

	def setValue(self, value, index = None):
		if index is None:
			index = self.getValueIndex()
		while index >= len(self._values):
			self._values.append(self._default)
		self._values[index] = unicode(value)

	def getValueIndex(self):
		if self.isMachineSetting() or self.isProfile() or self.isAlteration():
			global _selectedMachineIndex
			return _selectedMachineIndex
		return 0

	def validate(self):
		result = validators.SUCCESS
		msgs = []
		for validator in self._validators:
			res, err = validator.validate()
			if res == validators.ERROR:
				result = res
			elif res == validators.WARNING and result != validators.ERROR:
				result = res
			if res != validators.SUCCESS:
				msgs.append(err)
		return result, '\n'.join(msgs)

	def addCondition(self, conditionFunction):
		self._conditions.append(conditionFunction)

	def checkConditions(self):
		for condition in self._conditions:
			if not condition():
				return False
		return True

#########################################################
## Settings
#########################################################

#Define a fake _() function to fake the gettext tools in to generating strings for the profile settings.
def _(n):
	return n

setting('layer_height',              0.1, float, 'basic',    _('Quality')).setRange(0.0001).setLabel(_("Layer height (mm)"), _("Layer height in millimeters.\nThis is the most important setting to determine the quality of your print. Normal quality prints are 0.1mm, high quality is 0.06mm. You can go up to 0.25mm with an Ultimaker for very fast prints at low quality."))
setting('wall_thickness',            0.8, float, 'basic',    _('Quality')).setRange(0.0).setLabel(_("Shell thickness (mm)"), _("Thickness of the outside shell in the horizontal direction.\nThis is used in combination with the nozzle size to define the number\nof perimeter lines and the thickness of those perimeter lines."))
setting('retraction_enable',        True, bool,  'basic',    _('Quality')).setLabel(_("Enable retraction"), _("Retract the filament when the nozzle is moving over a none-printed area. Details about the retraction can be configured in the advanced tab."))
setting('solid_layer_thickness',     0.6, float, 'basic',    _('Fill')).setRange(0).setLabel(_("Bottom/Top thickness (mm)"), _("This controls the thickness of the bottom and top layers, the amount of solid layers put down is calculated by the layer thickness and this value.\nHaving this value a multiple of the layer thickness makes sense. And keep it near your wall thickness to make an evenly strong part."))
setting('fill_density',               20, float, 'basic',    _('Fill')).setRange(0, 100).setLabel(_("Fill Density (%)"), _("This controls how densely filled the insides of your print will be. For a solid part use 100%, for an empty part use 0%. A value around 20% is usually enough.\nThis won't affect the outside of the print and only adjusts how strong the part becomes."))
setting('nozzle_size',               0.4, float, 'advanced', _('Machine')).setRange(0.1,10).setLabel(_("Nozzle size (mm)"), _("The nozzle size is very important, this is used to calculate the line width of the infill, and used to calculate the amount of outside wall lines and thickness for the wall thickness you entered in the print settings."))
setting('print_speed',                50, float, 'basic',    _('Speed and Temperature')).setRange(1).setLabel(_("Print speed (mm/s)"), _("Speed at which printing happens. A well adjusted Ultimaker can reach 150mm/s, but for good quality prints you want to print slower. Printing speed depends on a lot of factors. So you will be experimenting with optimal settings for this."))
setting('print_temperature',         220, int,   'basic',    _('Speed and Temperature')).setRange(0,340).setLabel(_("Printing temperature (C)"), _("Temperature used for printing. Set at 0 to pre-heat yourself.\nFor PLA a value of 210C is usually used.\nFor ABS a value of 230C or higher is required."))
setting('print_temperature2',          0, int,   'basic',    _('Speed and Temperature')).setRange(0,340).setLabel(_("2nd nozzle temperature (C)"), _("Temperature used for printing. Set at 0 to pre-heat yourself.\nFor PLA a value of 210C is usually used.\nFor ABS a value of 230C or higher is required."))
setting('print_temperature3',          0, int,   'basic',    _('Speed and Temperature')).setRange(0,340).setLabel(_("3th nozzle temperature (C)"), _("Temperature used for printing. Set at 0 to pre-heat yourself.\nFor PLA a value of 210C is usually used.\nFor ABS a value of 230C or higher is required."))
setting('print_temperature4',          0, int,   'basic',    _('Speed and Temperature')).setRange(0,340).setLabel(_("4th nozzle temperature (C)"), _("Temperature used for printing. Set at 0 to pre-heat yourself.\nFor PLA a value of 210C is usually used.\nFor ABS a value of 230C or higher is required."))
setting('print_bed_temperature',      70, int,   'basic',    _('Speed and Temperature')).setRange(0,340).setLabel(_("Bed temperature (C)"), _("Temperature used for the heated printer bed. Set at 0 to pre-heat yourself."))
setting('support',                'None', [_('None'), _('Touching buildplate'), _('Everywhere')], 'basic', _('Support')).setLabel(_("Support type"), _("Type of support structure build.\n\"Touching buildplate\" is the most commonly used support setting.\n\nNone does not do any support.\nTouching buildplate only creates support where the support structure will touch the build platform.\nEverywhere creates support even on top of parts of the model."))
setting('platform_adhesion',      'None', [_('None'), _('Brim'), _('Raft')], 'basic', _('Support')).setLabel(_("Platform adhesion type"), _("Different options that help in preventing corners from lifting due to warping.\nBrim adds a single layer thick flat area around your object which is easy to cut off afterwards, and it is the recommended option.\nRaft adds a thick raster below the object and a thin interface between this and your object.\n(Note that enabling the brim or raft disables the skirt)"))
setting('support_dual_extrusion',  'Both', [_('Both'), _('First extruder'), _('Second extruder')], 'basic', _('Support')).setLabel(_("Support dual extrusion"), _("Which extruder to use for support material, for break-away support you can use both extruders.\nBut if one of the materials is more expensive then the other you could select an extruder to use for support material. This causes more extruder switches.\nYou can also use the 2nd extruder for soluble support materials."))
setting('wipe_tower',              False, bool,  'basic',    _('Dual extrusion')).setLabel(_("Wipe&prime tower"), _("The wipe-tower is a tower printed on every layer when switching between nozzles.\nThe old nozzle is wiped off on the tower before the new nozzle is used to print the 2nd color."))
setting('wipe_tower_volume',          15, float, 'expert',   _('Dual extrusion')).setLabel(_("Wipe&prime tower volume per layer (mm3)"), _("The amount of material put in the wipe/prime tower.\nThis is done in volume because in general you want to extrude a\ncertain amount of volume to get the extruder going, independent on the layer height.\nThis means that with thinner layers, your tower gets bigger."))
setting('ooze_shield',             False, bool,  'basic',    _('Dual extrusion')).setLabel(_("Ooze shield"), _("The ooze shield is a 1 line thick shell around the object which stands a few mm from the object.\nThis shield catches any oozing from the unused nozzle in dual-extrusion."))
setting('filament_diameter',        2.85, float, 'basic',    _('Filament')).setRange(1).setLabel(_("Diameter (mm)"), _("Diameter of your filament, as accurately as possible.\nIf you cannot measure this value you will have to calibrate it, a higher number means less extrusion, a smaller number generates more extrusion."))
setting('filament_diameter2',          0, float, 'basic',    _('Filament')).setRange(0).setLabel(_("Diameter2 (mm)"), _("Diameter of your filament for the 2nd nozzle. Use 0 to use the same diameter as for nozzle 1."))
setting('filament_diameter3',          0, float, 'basic',    _('Filament')).setRange(0).setLabel(_("Diameter3 (mm)"), _("Diameter of your filament for the 3th nozzle. Use 0 to use the same diameter as for nozzle 1."))
setting('filament_diameter4',          0, float, 'basic',    _('Filament')).setRange(0).setLabel(_("Diameter4 (mm)"), _("Diameter of your filament for the 4th nozzle. Use 0 to use the same diameter as for nozzle 1."))
setting('filament_flow',            100., float, 'basic',    _('Filament')).setRange(5,300).setLabel(_("Flow (%)"), _("Flow compensation, the amount of material extruded is multiplied by this value"))
setting('retraction_speed',         40.0, float, 'advanced', _('Retraction')).setRange(0.1).setLabel(_("Speed (mm/s)"), _("Speed at which the filament is retracted, a higher retraction speed works better. But a very high retraction speed can lead to filament grinding."))
setting('retraction_amount',         4.5, float, 'advanced', _('Retraction')).setRange(0).setLabel(_("Distance (mm)"), _("Amount of retraction, set at 0 for no retraction at all. A value of 4.5mm seems to generate good results."))
setting('retraction_dual_amount',   16.5, float, 'advanced', _('Retraction')).setRange(0).setLabel(_("Dual extrusion switch amount (mm)"), _("Amount of retraction when switching nozzle with dual-extrusion, set at 0 for no retraction at all. A value of 16.0mm seems to generate good results."))
setting('retraction_min_travel',     1.5, float, 'expert',   _('Retraction')).setRange(0).setLabel(_("Minimum travel (mm)"), _("Minimum amount of travel needed for a retraction to happen at all. To make sure you do not get a lot of retractions in a small area."))
setting('retraction_combing',       True, bool,  'expert',   _('Retraction')).setLabel(_("Enable combing"), _("Combing is the act of avoiding holes in the print for the head to travel over. If combing is disabled the printer head moves straight from the start point to the end point and it will always retract."))
setting('retraction_minimal_extrusion',0.02, float,'expert', _('Retraction')).setRange(0).setLabel(_("Minimal extrusion before retracting (mm)"), _("The minimal amount of extrusion that needs to be done before retracting again if a retraction needs to happen before this minimal is reached the retraction is ignored.\nThis avoids retracting a lot on the same piece of filament which flattens the filament and causes grinding issues."))
setting('retraction_hop',            0.0, float, 'expert',   _('Retraction')).setRange(0).setLabel(_("Z hop when retracting (mm)"), _("When a retraction is done, the head is lifted by this amount to travel over the print. A value of 0.075 works well. This feature has a lot of positive effect on delta towers."))
setting('bottom_thickness',          0.3, float, 'advanced', _('Quality')).setRange(0).setLabel(_("Initial layer thickness (mm)"), _("Layer thickness of the bottom layer. A thicker bottom layer makes sticking to the bed easier. Set to 0.0 to have the bottom layer thickness the same as the other layers."))
setting('object_sink',               0.0, float, 'advanced', _('Quality')).setRange(0).setLabel(_("Cut off object bottom (mm)"), _("Sinks the object into the platform, this can be used for objects that do not have a flat bottom and thus create a too small first layer."))
#setting('enable_skin',             False, bool,  'advanced', _('Quality')).setLabel(_("Duplicate outlines"), _("Skin prints the outer lines of the prints twice, each time with half the thickness. This gives the illusion of a higher print quality."))
setting('overlap_dual',             0.15, float, 'advanced', _('Quality')).setLabel(_("Dual extrusion overlap (mm)"), _("Add a certain amount of overlapping extrusion on dual-extrusion prints. This bonds the different colors together."))
setting('travel_speed',            150.0, float, 'advanced', _('Speed')).setRange(0.1).setLabel(_("Travel speed (mm/s)"), _("Speed at which travel moves are done, a well built Ultimaker can reach speeds of 250mm/s. But some machines might miss steps then."))
setting('bottom_layer_speed',         20, float, 'advanced', _('Speed')).setRange(0.1).setLabel(_("Bottom layer speed (mm/s)"), _("Print speed for the bottom layer, you want to print the first layer slower so it sticks better to the printer bed."))
setting('infill_speed',              0.0, float, 'advanced', _('Speed')).setRange(0.0).setLabel(_("Infill speed (mm/s)"), _("Speed at which infill parts are printed. If set to 0 then the print speed is used for the infill. Printing the infill faster can greatly reduce printing time, but this can negatively affect print quality."))
setting('inset0_speed',              0.0, float, 'advanced', _('Speed')).setRange(0.0).setLabel(_("Outer shell speed (mm/s)"), _("Speed at which outer shell is printed. If set to 0 then the print speed is used. Printing the outer shell at a lower speed improves the final skin quality. However, having a large difference between the inner shell speed and the outer shell speed will effect quality in a negative way."))
setting('insetx_speed',              0.0, float, 'advanced', _('Speed')).setRange(0.0).setLabel(_("Inner shell speed (mm/s)"), _("Speed at which inner shells are printed. If set to 0 then the print speed is used. Printing the inner shell faster then the outer shell will reduce printing time. It is good to set this somewhere in between the outer shell speed and the infill/printing speed."))
setting('cool_min_layer_time',         5, float, 'advanced', _('Cool')).setRange(0).setLabel(_("Minimal layer time (sec)"), _("Minimum time spent in a layer, gives the layer time to cool down before the next layer is put on top. If the layer will be placed down too fast the printer will slow down to make sure it has spent at least this amount of seconds printing this layer."))
setting('fan_enabled',              True, bool,  'advanced', _('Cool')).setLabel(_("Enable cooling fan"), _("Enable the cooling fan during the print. The extra cooling from the cooling fan is essential during faster prints."))

setting('skirt_line_count',            1, int,   'expert', 'Skirt').setRange(0).setLabel(_("Line count"), _("The skirt is a line drawn around the object at the first layer. This helps to prime your extruder, and to see if the object fits on your platform.\nSetting this to 0 will disable the skirt. Multiple skirt lines can help priming your extruder better for small objects."))
setting('skirt_gap',                 3.0, float, 'expert', 'Skirt').setRange(0).setLabel(_("Start distance (mm)"), _("The distance between the skirt and the first layer.\nThis is the minimal distance, multiple skirt lines will be put outwards from this distance."))
setting('skirt_minimal_length',    150.0, float, 'expert', 'Skirt').setRange(0).setLabel(_("Minimal length (mm)"), _("The minimal length of the skirt, if this minimal length is not reached it will add more skirt lines to reach this minimal lenght.\nNote: If the line count is set to 0 this is ignored."))
setting('fan_full_height',           0.5, float, 'expert',   _('Cool')).setRange(0).setLabel(_("Fan full on at height (mm)"), _("The height at which the fan is turned on completely. For the layers below this the fan speed is scaled linearly with the fan off at layer 0."))
setting('fan_speed',                 100, int,   'expert',   _('Cool')).setRange(0,100).setLabel(_("Fan speed min (%)"), _("When the fan is turned on, it is enabled at this speed setting. If cool slows down the layer, the fan is adjusted between the min and max speed. Minimal fan speed is used if the layer is not slowed down due to cooling."))
setting('fan_speed_max',             100, int,   'expert',   _('Cool')).setRange(0,100).setLabel(_("Fan speed max (%)"), _("When the fan is turned on, it is enabled at this speed setting. If cool slows down the layer, the fan is adjusted between the min and max speed. Maximal fan speed is used if the layer is slowed down due to cooling by more than 200%."))
setting('cool_min_feedrate',          10, float, 'expert',   _('Cool')).setRange(0).setLabel(_("Minimum speed (mm/s)"), _("The minimal layer time can cause the print to slow down so much it starts to ooze. The minimal feedrate protects against this. Even if a print gets slowed down it will never be slower than this minimal speed."))
setting('cool_head_lift',          False, bool,  'expert',   _('Cool')).setLabel(_("Cool head lift"), _("Lift the head if the minimal speed is hit because of cool slowdown, and wait the extra time so the minimal layer time is always hit."))
setting('solid_top', True, bool, 'expert', _('Infill')).setLabel(_("Solid infill top"), _("Create a solid top surface, if set to false the top is filled with the fill percentage. Useful for cups/vases."))
setting('solid_bottom', True, bool, 'expert', _('Infill')).setLabel(_("Solid infill bottom"), _("Create a solid bottom surface, if set to false the bottom is filled with the fill percentage. Useful for buildings."))
setting('fill_overlap', 15, int, 'expert', _('Infill')).setRange(0,100).setLabel(_("Infill overlap (%)"), _("Amount of overlap between the infill and the walls. There is a slight overlap with the walls and the infill so the walls connect firmly to the infill."))
setting('support_type', 'Grid', ['Grid', 'Lines'], 'expert', _('Support')).setLabel(_("Structure type"), _("The type of support structure.\nGrid is very strong and can come off in 1 piece, however, sometimes it is too strong.\nLines are single walled lines that break off one at a time. Which is more work to remove, but as it is less strong it does work better on tricky prints."))
setting('support_angle', 60, float, 'expert', _('Support')).setRange(0,90).setLabel(_("Overhang angle for support (deg)"), _("The minimal angle that overhangs need to have to get support. With 0 degree being horizontal and 90 degree being vertical."))
setting('support_fill_rate', 15, int, 'expert', _('Support')).setRange(0,100).setLabel(_("Fill amount (%)"), _("Amount of infill structure in the support material, less material gives weaker support which is easier to remove. 15% seems to be a good average."))
setting('support_xy_distance', 0.7, float, 'expert', _('Support')).setRange(0,10).setLabel(_("Distance X/Y (mm)"), _("Distance of the support material from the print, in the X/Y directions.\n0.7mm gives a nice distance from the print so the support does not stick to the print."))
setting('support_z_distance', 0.15, float, 'expert', _('Support')).setRange(0,10).setLabel(_("Distance Z (mm)"), _("Distance from the top/bottom of the support to the print. A small gap here makes it easier to remove the support but makes the print a bit uglier.\n0.15mm gives a good seperation of the support material."))
setting('spiralize', False, bool, 'expert', 'Black Magic').setLabel(_("Spiralize the outer contour"), _("Spiralize is smoothing out the Z move of the outer edge. This will create a steady Z increase over the whole print. This feature turns a solid object into a single walled print with a solid bottom.\nThis feature used to be called Joris in older versions."))
setting('simple_mode', False, bool, 'expert', 'Black Magic').setLabel(_("Only follow mesh surface"), _("Only follow the mesh surfaces of the 3D model, do not do anything else. No infill, no top/bottom, nothing."))
#setting('bridge_speed', 100, int, 'expert', 'Bridge').setRange(0,100).setLabel(_("Bridge speed (%)"), _("Speed at which layers with bridges are printed, compared to normal printing speed."))
setting('brim_line_count', 20, int, 'expert', _('Brim')).setRange(1,100).setLabel(_("Brim line amount"), _("The amount of lines used for a brim, more lines means a larger brim which sticks better, but this also makes your effective print area smaller."))
setting('raft_margin', 5.0, float, 'expert', _('Raft')).setRange(0).setLabel(_("Extra margin (mm)"), _("If the raft is enabled, this is the extra raft area around the object which is also rafted. Increasing this margin will create a stronger raft while using more material and leaving less area for your print."))
setting('raft_line_spacing', 3.0, float, 'expert', _('Raft')).setRange(0).setLabel(_("Line spacing (mm)"), _("When you are using the raft this is the distance between the centerlines of the raft line."))
setting('raft_base_thickness', 0.3, float, 'expert', _('Raft')).setRange(0).setLabel(_("Base thickness (mm)"), _("When you are using the raft this is the thickness of the base layer which is put down."))
setting('raft_base_linewidth', 1.0, float, 'expert', _('Raft')).setRange(0).setLabel(_("Base line width (mm)"), _("When you are using the raft this is the width of the base layer lines which are put down."))
setting('raft_interface_thickness', 0.27, float, 'expert', _('Raft')).setRange(0).setLabel(_("Interface thickness (mm)"), _("When you are using the raft this is the thickness of the interface layer which is put down."))
setting('raft_interface_linewidth', 0.4, float, 'expert', _('Raft')).setRange(0).setLabel(_("Interface line width (mm)"), _("When you are using the raft this is the width of the interface layer lines which are put down."))
setting('raft_airgap', 0.22, float, 'expert', _('Raft')).setRange(0).setLabel(_("Airgap"), _("Gap between the last layer of the raft and the first printing layer. A small gap of 0.2mm works wonders on PLA and makes the raft easy to remove."))
setting('raft_surface_layers', 2, int, 'expert', _('Raft')).setRange(0).setLabel(_("Surface layers"), _("Amount of surface layers put on top of the raft, these are fully filled layers on which the model is printed."))
setting('fix_horrible_union_all_type_a', True,  bool, 'expert', _('Fix horrible')).setLabel(_("Combine everything (Type-A)"), _("This expert option adds all parts of the model together. The result is usually that internal cavities disappear. Depending on the model this can be intended or not. Enabling this option is at your own risk. Type-A is dependent on the model normals and tries to keep some internal holes intact. Type-B ignores all internal holes and only keeps the outside shape per layer."))
setting('fix_horrible_union_all_type_b', False, bool, 'expert', _('Fix horrible')).setLabel(_("Combine everything (Type-B)"), _("This expert option adds all parts of the model together. The result is usually that internal cavities disappear. Depending on the model this can be intended or not. Enabling this option is at your own risk. Type-A is dependent on the model normals and tries to keep some internal holes intact. Type-B ignores all internal holes and only keeps the outside shape per layer."))
setting('fix_horrible_use_open_bits', False, bool, 'expert', _('Fix horrible')).setLabel(_("Keep open faces"), _("This expert option keeps all the open bits of the model intact. Normally Cura tries to stitch up small holes and remove everything with big holes, but this option keeps bits that are not properly part of anything and just goes with whatever is left. This option is usually not what you want, but it might enable you to slice models otherwise failing to produce proper paths.\nAs with all \"Fix horrible\" options, results may vary and use at your own risk."))
setting('fix_horrible_extensive_stitching', False, bool, 'expert', _('Fix horrible')).setLabel(_("Extensive stitching"), _("Extensive stitching tries to fix up open holes in the model by closing the hole with touching polygons. This algorthm is quite expensive and could introduce a lot of processing time.\nAs with all \"Fix horrible\" options, results may vary and use at your own risk."))

setting('plugin_config', '', str, 'hidden', 'hidden')
setting('object_center_x', -1, float, 'hidden', 'hidden')
setting('object_center_y', -1, float, 'hidden', 'hidden')

setting('start.gcode', """;Sliced at: {day} {date} {time}
;Basic settings: Layer height: {layer_height} Walls: {wall_thickness} Fill: {fill_density}
;Print time: {print_time}
;Filament used: {filament_amount}m {filament_weight}g
;Filament cost: {filament_cost}
;M190 S{print_bed_temperature} ;Uncomment to add your own bed temperature line
;M109 S{print_temperature} ;Uncomment to add your own temperature line
G21        ;metric values
G90        ;absolute positioning
M82        ;set extruder to absolute mode
M107       ;start with the fan off

G28 X0 Y0  ;move X/Y to min endstops
G28 Z0     ;move Z to min endstops

G1 Z15.0 F{travel_speed} ;move the platform down 15mm

G92 E0                  ;zero the extruded length
G1 F200 E3              ;extrude 3mm of feed stock
G92 E0                  ;zero the extruded length again
G1 F{travel_speed}
;Put printing message on LCD screen
M117 Printing...
""", str, 'alteration', 'alteration')
#######################################################################################
setting('end.gcode', """;End GCode
M104 S0                     ;extruder heater off
M140 S0                     ;heated bed heater off (if you have it)

G91                                    ;relative positioning
G1 E-1 F300                            ;retract the filament a bit before lifting the nozzle, to release some of the pressure
G1 Z+0.5 E-5 X-20 Y-20 F{travel_speed} ;move Z up a bit and retract filament even more
G28 X0 Y0                              ;move X/Y to min endstops, so the head is out of the way

M84                         ;steppers off
G90                         ;absolute positioning
;{profile_string}
""", str, 'alteration', 'alteration')
#######################################################################################
setting('start2.gcode', """;Sliced at: {day} {date} {time}
;Basic settings: Layer height: {layer_height} Walls: {wall_thickness} Fill: {fill_density}
;Print time: {print_time}
;Filament used: {filament_amount}m {filament_weight}g
;Filament cost: {filament_cost}
;M190 S{print_bed_temperature} ;Uncomment to add your own bed temperature line
;M104 S{print_temperature} ;Uncomment to add your own temperature line
;M109 T1 S{print_temperature2} ;Uncomment to add your own temperature line
;M109 T0 S{print_temperature} ;Uncomment to add your own temperature line
G21        ;metric values
G90        ;absolute positioning
M107       ;start with the fan off

G28 X0 Y0  ;move X/Y to min endstops
G28 Z0     ;move Z to min endstops

G1 Z15.0 F{travel_speed} ;move the platform down 15mm

T1                      ;Switch to the 2nd extruder
G92 E0                  ;zero the extruded length
G1 F200 E10             ;extrude 10mm of feed stock
G92 E0                  ;zero the extruded length again
G1 F200 E-{retraction_dual_amount}

T0                      ;Switch to the first extruder
G92 E0                  ;zero the extruded length
G1 F200 E10             ;extrude 10mm of feed stock
G92 E0                  ;zero the extruded length again
G1 F{travel_speed}
;Put printing message on LCD screen
M117 Printing...
""", str, 'alteration', 'alteration')
#######################################################################################
setting('end2.gcode', """;End GCode
M104 T0 S0                     ;extruder heater off
M104 T1 S0                     ;extruder heater off
M140 S0                     ;heated bed heater off (if you have it)

G91                                    ;relative positioning
G1 E-1 F300                            ;retract the filament a bit before lifting the nozzle, to release some of the pressure
G1 Z+0.5 E-5 X-20 Y-20 F{travel_speed} ;move Z up a bit and retract filament even more
G28 X0 Y0                              ;move X/Y to min endstops, so the head is out of the way

M84                         ;steppers off
G90                         ;absolute positioning
;{profile_string}
""", str, 'alteration', 'alteration')
#######################################################################################
setting('start3.gcode', """;Sliced at: {day} {date} {time}
;Basic settings: Layer height: {layer_height} Walls: {wall_thickness} Fill: {fill_density}
;Print time: {print_time}
;Filament used: {filament_amount}m {filament_weight}g
;Filament cost: {filament_cost}
;M190 S{print_bed_temperature} ;Uncomment to add your own bed temperature line
;M104 S{print_temperature} ;Uncomment to add your own temperature line
;M109 T1 S{print_temperature2} ;Uncomment to add your own temperature line
;M109 T0 S{print_temperature} ;Uncomment to add your own temperature line
G21        ;metric values
G90        ;absolute positioning
M107       ;start with the fan off

G28 X0 Y0  ;move X/Y to min endstops
G28 Z0     ;move Z to min endstops

G1 Z15.0 F{travel_speed} ;move the platform down 15mm

T2                      ;Switch to the 2nd extruder
G92 E0                  ;zero the extruded length
G1 F200 E10             ;extrude 10mm of feed stock
G92 E0                  ;zero the extruded length again
G1 F200 E-{retraction_dual_amount}

T1                      ;Switch to the 2nd extruder
G92 E0                  ;zero the extruded length
G1 F200 E10             ;extrude 10mm of feed stock
G92 E0                  ;zero the extruded length again
G1 F200 E-{retraction_dual_amount}

T0                      ;Switch to the first extruder
G92 E0                  ;zero the extruded length
G1 F200 E10             ;extrude 10mm of feed stock
G92 E0                  ;zero the extruded length again
G1 F{travel_speed}
;Put printing message on LCD screen
M117 Printing...
""", str, 'alteration', 'alteration')
#######################################################################################
setting('end3.gcode', """;End GCode
M104 T0 S0                     ;extruder heater off
M104 T1 S0                     ;extruder heater off
M104 T2 S0                     ;extruder heater off
M140 S0                     ;heated bed heater off (if you have it)

G91                                    ;relative positioning
G1 E-1 F300                            ;retract the filament a bit before lifting the nozzle, to release some of the pressure
G1 Z+0.5 E-5 X-20 Y-20 F{travel_speed} ;move Z up a bit and retract filament even more
G28 X0 Y0                              ;move X/Y to min endstops, so the head is out of the way

M84                         ;steppers off
G90                         ;absolute positioning
;{profile_string}
""", str, 'alteration', 'alteration')
setting('start4.gcode', """;Sliced at: {day} {date} {time}
;Basic settings: Layer height: {layer_height} Walls: {wall_thickness} Fill: {fill_density}
;Print time: {print_time}
;Filament used: {filament_amount}m {filament_weight}g
;Filament cost: {filament_cost}
;M190 S{print_bed_temperature} ;Uncomment to add your own bed temperature line
;M104 S{print_temperature} ;Uncomment to add your own temperature line
;M109 T2 S{print_temperature2} ;Uncomment to add your own temperature line
;M109 T1 S{print_temperature2} ;Uncomment to add your own temperature line
;M109 T0 S{print_temperature} ;Uncomment to add your own temperature line
G21        ;metric values
G90        ;absolute positioning
M107       ;start with the fan off

G28 X0 Y0  ;move X/Y to min endstops
G28 Z0     ;move Z to min endstops

G1 Z15.0 F{travel_speed} ;move the platform down 15mm

T3                      ;Switch to the 4th extruder
G92 E0                  ;zero the extruded length
G1 F200 E10             ;extrude 10mm of feed stock
G92 E0                  ;zero the extruded length again
G1 F200 E-{retraction_dual_amount}

T2                      ;Switch to the 3th extruder
G92 E0                  ;zero the extruded length
G1 F200 E10             ;extrude 10mm of feed stock
G92 E0                  ;zero the extruded length again
G1 F200 E-{retraction_dual_amount}

T1                      ;Switch to the 2nd extruder
G92 E0                  ;zero the extruded length
G1 F200 E10             ;extrude 10mm of feed stock
G92 E0                  ;zero the extruded length again
G1 F200 E-{retraction_dual_amount}

T0                      ;Switch to the first extruder
G92 E0                  ;zero the extruded length
G1 F200 E10             ;extrude 10mm of feed stock
G92 E0                  ;zero the extruded length again
G1 F{travel_speed}
;Put printing message on LCD screen
M117 Printing...
""", str, 'alteration', 'alteration')
#######################################################################################
setting('end4.gcode', """;End GCode
M104 T0 S0                     ;extruder heater off
M104 T1 S0                     ;extruder heater off
M104 T2 S0                     ;extruder heater off
M104 T3 S0                     ;extruder heater off
M140 S0                     ;heated bed heater off (if you have it)

G91                                    ;relative positioning
G1 E-1 F300                            ;retract the filament a bit before lifting the nozzle, to release some of the pressure
G1 Z+0.5 E-5 X-20 Y-20 F{travel_speed} ;move Z up a bit and retract filament even more
G28 X0 Y0                              ;move X/Y to min endstops, so the head is out of the way

M84                         ;steppers off
G90                         ;absolute positioning
;{profile_string}
""", str, 'alteration', 'alteration')
#######################################################################################
setting('support_start.gcode', '', str, 'alteration', 'alteration')
setting('support_end.gcode', '', str, 'alteration', 'alteration')
setting('cool_start.gcode', '', str, 'alteration', 'alteration')
setting('cool_end.gcode', '', str, 'alteration', 'alteration')
setting('replace.csv', '', str, 'alteration', 'alteration')
#######################################################################################
setting('preSwitchExtruder.gcode', """;Switch between the current extruder and the next extruder, when printing with multiple extruders.
;This code is added before the T(n)
""", str, 'alteration', 'alteration')
setting('postSwitchExtruder.gcode', """;Switch between the current extruder and the next extruder, when printing with multiple extruders.
;This code is added after the T(n)
""", str, 'alteration', 'alteration')

setting('startMode', 'Simple', ['Simple', 'Normal'], 'preference', 'hidden')
setting('oneAtATime', 'True', bool, 'preference', 'hidden')
setting('lastFile', os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'resources', 'example', 'UltimakerRobot_support.stl')), str, 'preference', 'hidden')
setting('save_profile', 'False', bool, 'preference', 'hidden').setLabel(_("Save profile on slice"), _("When slicing save the profile as [stl_file]_profile.ini next to the model."))
setting('filament_cost_kg', '0', float, 'preference', 'hidden').setLabel(_("Cost (price/kg)"), _("Cost of your filament per kg, to estimate the cost of the final print."))
setting('filament_cost_meter', '0', float, 'preference', 'hidden').setLabel(_("Cost (price/m)"), _("Cost of your filament per meter, to estimate the cost of the final print."))
setting('auto_detect_sd', 'True', bool, 'preference', 'hidden').setLabel(_("Auto detect SD card drive"), _("Auto detect the SD card. You can disable this because on some systems external hard-drives or USB sticks are detected as SD card."))
setting('check_for_updates', 'True', bool, 'preference', 'hidden').setLabel(_("Check for updates"), _("Check for newer versions of Cura on startup"))
setting('submit_slice_information', 'False', bool, 'preference', 'hidden').setLabel(_("Send usage statistics"), _("Submit anonymous usage information to improve future versions of Cura"))
setting('youmagine_token', '', str, 'preference', 'hidden')
setting('filament_physical_density', '1240', float, 'preference', 'hidden').setRange(500.0, 3000.0).setLabel(_("Density (kg/m3)"), _("Weight of the filament per m3. Around 1240 for PLA. And around 1040 for ABS. This value is used to estimate the weight if the filament used for the print."))
setting('language', 'English', str, 'preference', 'hidden').setLabel(_('Language'), _('Change the language in which Cura runs. Switching language requires a restart of Cura'))
setting('active_machine', '0', int, 'preference', 'hidden')

setting('model_colour', '#FFC924', str, 'preference', 'hidden').setLabel(_('Model colour'), _('Display color for first extruder'))
setting('model_colour2', '#CB3030', str, 'preference', 'hidden').setLabel(_('Model colour (2)'), _('Display color for second extruder'))
setting('model_colour3', '#DDD93C', str, 'preference', 'hidden').setLabel(_('Model colour (3)'), _('Display color for third extruder'))
setting('model_colour4', '#4550D3', str, 'preference', 'hidden').setLabel(_('Model colour (4)'), _('Display color for forth extruder'))
setting('printing_window', 'Basic', ['Basic'], 'preference', 'hidden').setLabel(_('Printing window type'), _('Select the interface used for USB printing.'))

setting('window_maximized', 'True', bool, 'preference', 'hidden')
setting('window_pos_x', '-1', float, 'preference', 'hidden')
setting('window_pos_y', '-1', float, 'preference', 'hidden')
setting('window_width', '-1', float, 'preference', 'hidden')
setting('window_height', '-1', float, 'preference', 'hidden')
setting('window_normal_sash', '320', float, 'preference', 'hidden')
setting('last_run_version', '', str, 'preference', 'hidden')

setting('machine_name', '', str, 'machine', 'hidden')
setting('machine_type', 'unknown', str, 'machine', 'hidden') #Ultimaker, Ultimaker2, RepRap
setting('machine_width', '205', float, 'machine', 'hidden').setLabel(_("Maximum width (mm)"), _("Size of the machine in mm"))
setting('machine_depth', '205', float, 'machine', 'hidden').setLabel(_("Maximum depth (mm)"), _("Size of the machine in mm"))
setting('machine_height', '200', float, 'machine', 'hidden').setLabel(_("Maximum height (mm)"), _("Size of the machine in mm"))
setting('machine_center_is_zero', 'False', bool, 'machine', 'hidden').setLabel(_("Machine center 0,0"), _("Machines firmware defines the center of the bed as 0,0 instead of the front left corner."))
setting('machine_shape', 'Square', ['Square','Circular'], 'machine', 'hidden').setLabel(_("Build area shape"), _("The shape of machine build area."))
setting('ultimaker_extruder_upgrade', 'False', bool, 'machine', 'hidden')
setting('has_heated_bed', 'False', bool, 'machine', 'hidden').setLabel(_("Heated bed"), _("If you have an heated bed, this enabled heated bed settings (requires restart)"))
setting('gcode_flavor', 'RepRap (Marlin/Sprinter)', ['RepRap (Marlin/Sprinter)', 'RepRap (Volumetric)', 'UltiGCode', 'MakerBot', 'BFB', 'Mach3'], 'machine', 'hidden').setLabel(_("GCode Flavor"), _("Flavor of generated GCode.\nRepRap is normal 5D GCode which works on Marlin/Sprinter based firmwares.\nUltiGCode is a variation of the RepRap GCode which puts more settings in the machine instead of the slicer.\nMakerBot GCode has a few changes in the way GCode is generated, but still requires MakerWare to generate to X3G.\nBFB style generates RPM based code.\nMach3 uses A,B,C instead of E for extruders."))
setting('extruder_amount', '1', ['1','2','3','4'], 'machine', 'hidden').setLabel(_("Extruder count"), _("Amount of extruders in your machine."))
setting('extruder_offset_x1', '0.0', float, 'machine', 'hidden').setLabel(_("Offset X"), _("The offset of your secondary extruder compared to the primary."))
setting('extruder_offset_y1', '21.6', float, 'machine', 'hidden').setLabel(_("Offset Y"), _("The offset of your secondary extruder compared to the primary."))
setting('extruder_offset_x2', '0.0', float, 'machine', 'hidden').setLabel(_("Offset X"), _("The offset of your tertiary extruder compared to the primary."))
setting('extruder_offset_y2', '0.0', float, 'machine', 'hidden').setLabel(_("Offset Y"), _("The offset of your tertiary extruder compared to the primary."))
setting('extruder_offset_x3', '0.0', float, 'machine', 'hidden').setLabel(_("Offset X"), _("The offset of your forth extruder compared to the primary."))
setting('extruder_offset_y3', '0.0', float, 'machine', 'hidden').setLabel(_("Offset Y"), _("The offset of your forth extruder compared to the primary."))
setting('steps_per_e', '0', float, 'machine', 'hidden').setLabel(_("E-Steps per 1mm filament"), _("Amount of steps per mm filament extrusion. If set to 0 then this value is ignored and the value in your firmware is used."))
setting('serial_port', 'AUTO', str, 'machine', 'hidden').setLabel(_("Serial port"), _("Serial port to use for communication with the printer"))
setting('serial_port_auto', '', str, 'machine', 'hidden')
setting('serial_baud', 'AUTO', str, 'machine', 'hidden').setLabel(_("Baudrate"), _("Speed of the serial port communication\nNeeds to match your firmware settings\nCommon values are 250000, 115200, 57600"))
setting('serial_baud_auto', '', int, 'machine', 'hidden')

setting('extruder_head_size_min_x', '0.0', float, 'machine', 'hidden').setLabel(_("Head size towards X min (mm)"), _("The head size when printing multiple objects, measured from the tip of the nozzle towards the outer part of the head. 75mm for an Ultimaker if the fan is on the left side."))
setting('extruder_head_size_min_y', '0.0', float, 'machine', 'hidden').setLabel(_("Head size towards Y min (mm)"), _("The head size when printing multiple objects, measured from the tip of the nozzle towards the outer part of the head. 18mm for an Ultimaker if the fan is on the left side."))
setting('extruder_head_size_max_x', '0.0', float, 'machine', 'hidden').setLabel(_("Head size towards X max (mm)"), _("The head size when printing multiple objects, measured from the tip of the nozzle towards the outer part of the head. 18mm for an Ultimaker if the fan is on the left side."))
setting('extruder_head_size_max_y', '0.0', float, 'machine', 'hidden').setLabel(_("Head size towards Y max (mm)"), _("The head size when printing multiple objects, measured from the tip of the nozzle towards the outer part of the head. 35mm for an Ultimaker if the fan is on the left side."))
setting('extruder_head_size_height', '0.0', float, 'machine', 'hidden').setLabel(_("Printer gantry height (mm)"), _("The height of the gantry holding up the printer head. If an object is higher then this then you cannot print multiple objects one for one. 60mm for an Ultimaker."))

validators.warningAbove(settingsDictionary['filament_flow'], 150, _("More flow than 150% is rare and usually not recommended."))
validators.warningBelow(settingsDictionary['filament_flow'], 50, _("Less flow than 50% is rare and usually not recommended."))
validators.warningAbove(settingsDictionary['layer_height'], lambda : (float(getProfileSetting('nozzle_size')) * 80.0 / 100.0), _("Thicker layers then %.2fmm (80%% nozzle size) usually give bad results and are not recommended."))
validators.wallThicknessValidator(settingsDictionary['wall_thickness'])
validators.warningAbove(settingsDictionary['print_speed'], 150.0, _("It is highly unlikely that your machine can achieve a printing speed above 150mm/s"))
validators.printSpeedValidator(settingsDictionary['print_speed'])
validators.warningAbove(settingsDictionary['print_temperature'], 260.0, _("Temperatures above 260C could damage your machine, be careful!"))
validators.warningAbove(settingsDictionary['print_temperature2'], 260.0, _("Temperatures above 260C could damage your machine, be careful!"))
validators.warningAbove(settingsDictionary['print_temperature3'], 260.0, _("Temperatures above 260C could damage your machine, be careful!"))
validators.warningAbove(settingsDictionary['print_temperature4'], 260.0, _("Temperatures above 260C could damage your machine, be careful!"))
validators.warningAbove(settingsDictionary['filament_diameter'], 3.5, _("Are you sure your filament is that thick? Normal filament is around 3mm or 1.75mm."))
validators.warningAbove(settingsDictionary['filament_diameter2'], 3.5, _("Are you sure your filament is that thick? Normal filament is around 3mm or 1.75mm."))
validators.warningAbove(settingsDictionary['filament_diameter3'], 3.5, _("Are you sure your filament is that thick? Normal filament is around 3mm or 1.75mm."))
validators.warningAbove(settingsDictionary['filament_diameter4'], 3.5, _("Are you sure your filament is that thick? Normal filament is around 3mm or 1.75mm."))
validators.warningAbove(settingsDictionary['travel_speed'], 300.0, _("It is highly unlikely that your machine can achieve a travel speed above 300mm/s"))
validators.warningAbove(settingsDictionary['bottom_thickness'], lambda : (float(getProfileSetting('nozzle_size')) * 3.0 / 4.0), _("A bottom layer of more then %.2fmm (3/4 nozzle size) usually give bad results and is not recommended."))

#Conditions for multiple extruders
settingsDictionary['print_temperature2'].addCondition(lambda : int(getMachineSetting('extruder_amount')) > 1)
settingsDictionary['print_temperature3'].addCondition(lambda : int(getMachineSetting('extruder_amount')) > 2)
settingsDictionary['print_temperature4'].addCondition(lambda : int(getMachineSetting('extruder_amount')) > 3)
settingsDictionary['filament_diameter2'].addCondition(lambda : int(getMachineSetting('extruder_amount')) > 1)
settingsDictionary['filament_diameter3'].addCondition(lambda : int(getMachineSetting('extruder_amount')) > 2)
settingsDictionary['filament_diameter4'].addCondition(lambda : int(getMachineSetting('extruder_amount')) > 3)
settingsDictionary['support_dual_extrusion'].addCondition(lambda : int(getMachineSetting('extruder_amount')) > 1)
settingsDictionary['retraction_dual_amount'].addCondition(lambda : int(getMachineSetting('extruder_amount')) > 1)
settingsDictionary['wipe_tower'].addCondition(lambda : int(getMachineSetting('extruder_amount')) > 1)
settingsDictionary['wipe_tower_volume'].addCondition(lambda : int(getMachineSetting('extruder_amount')) > 1)
settingsDictionary['ooze_shield'].addCondition(lambda : int(getMachineSetting('extruder_amount')) > 1)
#Heated bed
settingsDictionary['print_bed_temperature'].addCondition(lambda : getMachineSetting('has_heated_bed') == 'True')

#UltiGCode uses less settings, as these settings are located inside the machine instead of gcode.
settingsDictionary['print_temperature'].addCondition(lambda : getMachineSetting('gcode_flavor') != 'UltiGCode')
settingsDictionary['print_temperature2'].addCondition(lambda : getMachineSetting('gcode_flavor') != 'UltiGCode')
settingsDictionary['print_temperature3'].addCondition(lambda : getMachineSetting('gcode_flavor') != 'UltiGCode')
settingsDictionary['print_temperature4'].addCondition(lambda : getMachineSetting('gcode_flavor') != 'UltiGCode')
settingsDictionary['filament_diameter'].addCondition(lambda : getMachineSetting('gcode_flavor') != 'UltiGCode')
settingsDictionary['filament_diameter2'].addCondition(lambda : getMachineSetting('gcode_flavor') != 'UltiGCode')
settingsDictionary['filament_diameter3'].addCondition(lambda : getMachineSetting('gcode_flavor') != 'UltiGCode')
settingsDictionary['filament_diameter4'].addCondition(lambda : getMachineSetting('gcode_flavor') != 'UltiGCode')
settingsDictionary['filament_flow'].addCondition(lambda : getMachineSetting('gcode_flavor') != 'UltiGCode')
settingsDictionary['print_bed_temperature'].addCondition(lambda : getMachineSetting('gcode_flavor') != 'UltiGCode')
settingsDictionary['retraction_speed'].addCondition(lambda : getMachineSetting('gcode_flavor') != 'UltiGCode')
settingsDictionary['retraction_amount'].addCondition(lambda : getMachineSetting('gcode_flavor') != 'UltiGCode')
settingsDictionary['retraction_dual_amount'].addCondition(lambda : getMachineSetting('gcode_flavor') != 'UltiGCode')

#Remove fake defined _() because later the localization will define a global _()
del _

#########################################################
## Profile and preferences functions
#########################################################

def getSubCategoriesFor(category):
	done = {}
	ret = []
	for s in settingsList:
		if s.getCategory() == category and not s.getSubCategory() in done and s.checkConditions():
			done[s.getSubCategory()] = True
			ret.append(s.getSubCategory())
	return ret

def getSettingsForCategory(category, subCategory = None):
	ret = []
	for s in settingsList:
		if s.getCategory() == category and (subCategory is None or s.getSubCategory() == subCategory) and s.checkConditions():
			ret.append(s)
	return ret

## Profile functions
def getBasePath():
	"""
	:return: The path in which the current configuration files are stored. This depends on the used OS.
	"""
	if platform.system() == "Windows":
		basePath = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
		#If we have a frozen python install, we need to step out of the library.zip
		if hasattr(sys, 'frozen'):
			basePath = os.path.normpath(os.path.join(basePath, ".."))
	else:
		basePath = os.path.expanduser('~/.cura/%s' % version.getVersion(False))
	if not os.path.isdir(basePath):
		try:
			os.makedirs(basePath)
		except:
			print "Failed to create directory: %s" % (basePath)
	return basePath

def getAlternativeBasePaths():
	"""
	Search for alternative installations of Cura and their preference files. Used to load configuration from older versions of Cura.
	"""
	paths = []
	basePath = os.path.normpath(os.path.join(getBasePath(), '..'))
	for subPath in os.listdir(basePath):
		path = os.path.join(basePath, subPath)
		if os.path.isdir(path) and os.path.isfile(os.path.join(path, 'preferences.ini')) and path != getBasePath():
			paths.append(path)
		path = os.path.join(basePath, subPath, 'Cura')
		if os.path.isdir(path) and os.path.isfile(os.path.join(path, 'preferences.ini')) and path != getBasePath():
			paths.append(path)
	return paths

def getDefaultProfilePath():
	"""
	:return: The default path where the currently used profile is stored and loaded on open and close of Cura.
	"""
	return os.path.join(getBasePath(), 'current_profile.ini')

def loadProfile(filename, allMachines = False):
	"""
		Read a profile file as active profile settings.
	:param filename:    The ini filename to save the profile in.
	:param allMachines: When False only the current active profile is saved. If True all profiles for all machines are saved.
	"""
	global settingsList
	profileParser = ConfigParser.ConfigParser()
	try:
		profileParser.read(filename)
	except ConfigParser.ParsingError:
		return
	if allMachines:
		n = 0
		while profileParser.has_section('profile_%d' % (n)):
			for set in settingsList:
				if set.isPreference():
					continue
				section = 'profile_%d' % (n)
				if set.isAlteration():
					section = 'alterations_%d' % (n)
				if profileParser.has_option(section, set.getName()):
					set.setValue(unicode(profileParser.get(section, set.getName()), 'utf-8', 'replace'), n)
			n += 1
	else:
		for set in settingsList:
			if set.isPreference():
				continue
			section = 'profile'
			if set.isAlteration():
				section = 'alterations'
			if profileParser.has_option(section, set.getName()):
				set.setValue(unicode(profileParser.get(section, set.getName()), 'utf-8', 'replace'))

def saveProfile(filename, allMachines = False):
	"""
		Save the current profile to an ini file.
	:param filename:    The ini filename to save the profile in.
	:param allMachines: When False only the current active profile is saved. If True all profiles for all machines are saved.
	"""
	global settingsList
	profileParser = ConfigParser.ConfigParser()
	if allMachines:
		for set in settingsList:
			if set.isPreference() or set.isMachineSetting():
				continue
			for n in xrange(0, getMachineCount()):
				if set.isAlteration():
					section = 'alterations_%d' % (n)
				else:
					section = 'profile_%d' % (n)
				if not profileParser.has_section(section):
					profileParser.add_section(section)
				profileParser.set(section, set.getName(), set.getValue(n).encode('utf-8'))
	else:
		profileParser.add_section('profile')
		profileParser.add_section('alterations')
		for set in settingsList:
			if set.isPreference() or set.isMachineSetting():
				continue
			if set.isAlteration():
				profileParser.set('alterations', set.getName(), set.getValue().encode('utf-8'))
			else:
				profileParser.set('profile', set.getName(), set.getValue().encode('utf-8'))

	profileParser.write(open(filename, 'w'))

def resetProfile():
	""" Reset the profile for the current machine to default. """
	global settingsList
	for set in settingsList:
		if not set.isProfile():
			continue
		set.setValue(set.getDefault())

	if getMachineSetting('machine_type') == 'ultimaker':
		putProfileSetting('nozzle_size', '0.4')
		if getMachineSetting('ultimaker_extruder_upgrade') == 'True':
			putProfileSetting('retraction_enable', 'True')
	elif getMachineSetting('machine_type') == 'ultimaker2':
		putProfileSetting('nozzle_size', '0.4')
		putProfileSetting('retraction_enable', 'True')
	else:
		putProfileSetting('nozzle_size', '0.5')
		putProfileSetting('retraction_enable', 'True')

def setProfileFromString(options):
	"""
	Parse an encoded string which has all the profile settings stored inside of it.
	Used in combination with getProfileString to ease sharing of profiles.
	"""
	options = base64.b64decode(options)
	options = zlib.decompress(options)
	(profileOpts, alt) = options.split('\f', 1)
	global settingsDictionary
	for option in profileOpts.split('\b'):
		if len(option) > 0:
			(key, value) = option.split('=', 1)
			if key in settingsDictionary:
				if settingsDictionary[key].isProfile():
					settingsDictionary[key].setValue(value)
	for option in alt.split('\b'):
		if len(option) > 0:
			(key, value) = option.split('=', 1)
			if key in settingsDictionary:
				if settingsDictionary[key].isAlteration():
					settingsDictionary[key].setValue(value)

def getProfileString():
	"""
	Get an encoded string which contains all profile settings.
	Used in combination with setProfileFromString to share settings in files, forums or other text based ways.
	"""
	p = []
	alt = []
	global settingsList
	for set in settingsList:
		if set.isProfile():
			if set.getName() in tempOverride:
				p.append(set.getName() + "=" + tempOverride[set.getName()])
			else:
				p.append(set.getName() + "=" + set.getValue().encode('utf-8'))
		elif set.isAlteration():
			if set.getName() in tempOverride:
				alt.append(set.getName() + "=" + tempOverride[set.getName()])
			else:
				alt.append(set.getName() + "=" + set.getValue().encode('utf-8'))
	ret = '\b'.join(p) + '\f' + '\b'.join(alt)
	ret = base64.b64encode(zlib.compress(ret, 9))
	return ret

def insertNewlines(string, every=64): #This should be moved to a better place then profile.
	lines = []
	for i in xrange(0, len(string), every):
		lines.append(string[i:i+every])
	return '\n'.join(lines)

def getPreferencesString():
	"""
	:return: An encoded string which contains all the current preferences.
	"""
	p = []
	global settingsList
	for set in settingsList:
		if set.isPreference():
			p.append(set.getName() + "=" + set.getValue().encode('utf-8'))
	ret = '\b'.join(p)
	ret = base64.b64encode(zlib.compress(ret, 9))
	return ret


def getProfileSetting(name):
	"""
		Get the value of an profile setting.
	:param name: Name of the setting to retrieve.
	:return:     Value of the current setting.
	"""
	if name in tempOverride:
		return tempOverride[name]
	global settingsDictionary
	if name in settingsDictionary and settingsDictionary[name].isProfile():
		return settingsDictionary[name].getValue()
	traceback.print_stack()
	sys.stderr.write('Error: "%s" not found in profile settings\n' % (name))
	return ''

def getProfileSettingFloat(name):
	try:
		setting = getProfileSetting(name).replace(',', '.')
		return float(eval(setting, {}, {}))
	except:
		return 0.0

def putProfileSetting(name, value):
	""" Store a certain value in a profile setting. """
	global settingsDictionary
	if name in settingsDictionary and settingsDictionary[name].isProfile():
		settingsDictionary[name].setValue(value)

def isProfileSetting(name):
	""" Check if a certain key name is actually a profile value. """
	global settingsDictionary
	if name in settingsDictionary and settingsDictionary[name].isProfile():
		return True
	return False

## Preferences functions
def getPreferencePath():
	"""
	:return: The full path of the preference ini file.
	"""
	return os.path.join(getBasePath(), 'preferences.ini')

def getPreferenceFloat(name):
	"""
	Get the float value of a preference, returns 0.0 if the preference is not a invalid float
	"""
	try:
		setting = getPreference(name).replace(',', '.')
		return float(eval(setting, {}, {}))
	except:
		return 0.0

def getPreferenceColour(name):
	"""
	Get a preference setting value as a color array. The color is stored as #RRGGBB hex string in the setting.
	"""
	colorString = getPreference(name)
	return [float(int(colorString[1:3], 16)) / 255, float(int(colorString[3:5], 16)) / 255, float(int(colorString[5:7], 16)) / 255, 1.0]

def loadPreferences(filename):
	"""
	Read a configuration file as global config
	"""
	global settingsList
	profileParser = ConfigParser.ConfigParser()
	try:
		profileParser.read(filename)
	except ConfigParser.ParsingError:
		return

	for set in settingsList:
		if set.isPreference():
			if profileParser.has_option('preference', set.getName()):
				set.setValue(unicode(profileParser.get('preference', set.getName()), 'utf-8', 'replace'))

	n = 0
	while profileParser.has_section('machine_%d' % (n)):
		for set in settingsList:
			if set.isMachineSetting():
				if profileParser.has_option('machine_%d' % (n), set.getName()):
					set.setValue(unicode(profileParser.get('machine_%d' % (n), set.getName()), 'utf-8', 'replace'), n)
		n += 1

	setActiveMachine(int(getPreferenceFloat('active_machine')))

def loadMachineSettings(filename):
	global settingsList
	#Read a configuration file as global config
	profileParser = ConfigParser.ConfigParser()
	try:
		profileParser.read(filename)
	except ConfigParser.ParsingError:
		return

	for set in settingsList:
		if set.isMachineSetting():
			if profileParser.has_option('machine', set.getName()):
				set.setValue(unicode(profileParser.get('machine', set.getName()), 'utf-8', 'replace'))
	checkAndUpdateMachineName()

def savePreferences(filename):
	global settingsList
	#Save the current profile to an ini file
	parser = ConfigParser.ConfigParser()
	parser.add_section('preference')

	for set in settingsList:
		if set.isPreference():
			parser.set('preference', set.getName(), set.getValue().encode('utf-8'))

	n = 0
	while getMachineSetting('machine_name', n) != '':
		parser.add_section('machine_%d' % (n))
		for set in settingsList:
			if set.isMachineSetting():
				parser.set('machine_%d' % (n), set.getName(), set.getValue(n).encode('utf-8'))
		n += 1
	parser.write(open(filename, 'w'))

def getPreference(name):
	if name in tempOverride:
		return tempOverride[name]
	global settingsDictionary
	if name in settingsDictionary and settingsDictionary[name].isPreference():
		return settingsDictionary[name].getValue()
	traceback.print_stack()
	sys.stderr.write('Error: "%s" not found in preferences\n' % (name))
	return ''

def putPreference(name, value):
	#Check if we have a configuration file loaded, else load the default.
	global settingsDictionary
	if name in settingsDictionary and settingsDictionary[name].isPreference():
		settingsDictionary[name].setValue(value)
		savePreferences(getPreferencePath())
		return
	traceback.print_stack()
	sys.stderr.write('Error: "%s" not found in preferences\n' % (name))

def isPreference(name):
	global settingsDictionary
	if name in settingsDictionary and settingsDictionary[name].isPreference():
		return True
	return False

def getMachineSettingFloat(name, index = None):
	try:
		setting = getMachineSetting(name, index).replace(',', '.')
		return float(eval(setting, {}, {}))
	except:
		return 0.0

def getMachineSetting(name, index = None):
	if name in tempOverride:
		return tempOverride[name]
	global settingsDictionary
	if name in settingsDictionary and settingsDictionary[name].isMachineSetting():
		return settingsDictionary[name].getValue(index)
	traceback.print_stack()
	sys.stderr.write('Error: "%s" not found in machine settings\n' % (name))
	return ''

def putMachineSetting(name, value):
	#Check if we have a configuration file loaded, else load the default.
	global settingsDictionary
	if name in settingsDictionary and settingsDictionary[name].isMachineSetting():
		settingsDictionary[name].setValue(value)
	savePreferences(getPreferencePath())

def isMachineSetting(name):
	global settingsDictionary
	if name in settingsDictionary and settingsDictionary[name].isMachineSetting():
		return True
	return False

def checkAndUpdateMachineName():
	global _selectedMachineIndex
	name = getMachineSetting('machine_name')
	index = None
	if name == '':
		name = getMachineSetting('machine_type')
	for n in xrange(0, getMachineCount()):
		if n == _selectedMachineIndex:
			continue
		if index is None:
			if name == getMachineSetting('machine_name', n):
				index = 1
		else:
			if '%s (%d)' % (name, index) == getMachineSetting('machine_name', n):
				index += 1
	if index is not None:
		name = '%s (%d)' % (name, index)
	putMachineSetting('machine_name', name)
	putPreference('active_machine', _selectedMachineIndex)

def getMachineCount():
	n = 0
	while getMachineSetting('machine_name', n) != '':
		n += 1
	if n < 1:
		return 1
	return n

def setActiveMachine(index):
	global _selectedMachineIndex
	_selectedMachineIndex = index
	putPreference('active_machine', _selectedMachineIndex)

def removeMachine(index):
	global _selectedMachineIndex
	global settingsList
	if getMachineCount() < 2:
		return
	for n in xrange(index, getMachineCount()):
		for setting in settingsList:
			if setting.isMachineSetting():
				setting.setValue(setting.getValue(n+1), n)

	if _selectedMachineIndex >= index:
		setActiveMachine(getMachineCount() - 1)

## Temp overrides for multi-extruder slicing and the project planner.
tempOverride = {}
def setTempOverride(name, value):
	tempOverride[name] = unicode(value).encode("utf-8")
def clearTempOverride(name):
	del tempOverride[name]
def resetTempOverride():
	tempOverride.clear()

#########################################################
## Utility functions to calculate common profile values
#########################################################
def calculateEdgeWidth():
	wallThickness = getProfileSettingFloat('wall_thickness')
	nozzleSize = getProfileSettingFloat('nozzle_size')

	if getProfileSetting('spiralize') == 'True' or getProfileSetting('simple_mode') == 'True':
		return wallThickness

	if wallThickness < 0.01:
		return nozzleSize
	if wallThickness < nozzleSize:
		return wallThickness

	lineCount = int(wallThickness / (nozzleSize - 0.0001))
	if lineCount == 0:
		return nozzleSize
	lineWidth = wallThickness / lineCount
	lineWidthAlt = wallThickness / (lineCount + 1)
	if lineWidth > nozzleSize * 1.5:
		return lineWidthAlt
	return lineWidth

def calculateLineCount():
	wallThickness = getProfileSettingFloat('wall_thickness')
	nozzleSize = getProfileSettingFloat('nozzle_size')

	if wallThickness < 0.01:
		return 0
	if wallThickness < nozzleSize:
		return 1
	if getProfileSetting('spiralize') == 'True' or getProfileSetting('simple_mode') == 'True':
		return 1

	lineCount = int(wallThickness / (nozzleSize - 0.0001))
	if lineCount < 1:
		lineCount = 1
	lineWidth = wallThickness / lineCount
	lineWidthAlt = wallThickness / (lineCount + 1)
	if lineWidth > nozzleSize * 1.5:
		return lineCount + 1
	return lineCount

def calculateSolidLayerCount():
	layerHeight = getProfileSettingFloat('layer_height')
	solidThickness = getProfileSettingFloat('solid_layer_thickness')
	if layerHeight == 0.0:
		return 1
	return int(math.ceil(solidThickness / (layerHeight - 0.0001)))

def calculateObjectSizeOffsets():
	size = 0.0

	if getProfileSetting('platform_adhesion') == 'Brim':
		size += getProfileSettingFloat('brim_line_count') * calculateEdgeWidth()
	elif getProfileSetting('platform_adhesion') == 'Raft':
		pass
	else:
		if getProfileSettingFloat('skirt_line_count') > 0:
			size += getProfileSettingFloat('skirt_line_count') * calculateEdgeWidth() + getProfileSettingFloat('skirt_gap')

	#if getProfileSetting('enable_raft') != 'False':
	#	size += profile.getProfileSettingFloat('raft_margin') * 2
	#if getProfileSetting('support') != 'None':
	#	extraSizeMin = extraSizeMin + numpy.array([3.0, 0, 0])
	#	extraSizeMax = extraSizeMax + numpy.array([3.0, 0, 0])
	return [size, size]

def getMachineCenterCoords():
	if getMachineSetting('machine_center_is_zero') == 'True':
		return [0, 0]
	return [getMachineSettingFloat('machine_width') / 2, getMachineSettingFloat('machine_depth') / 2]

#Returns a list of convex polygons, first polygon is the allowed area of the machine,
# the rest of the polygons are the dis-allowed areas of the machine.
def getMachineSizePolygons():
	size = numpy.array([getMachineSettingFloat('machine_width'), getMachineSettingFloat('machine_depth'), getMachineSettingFloat('machine_height')], numpy.float32)
	ret = []
	if getMachineSetting('machine_shape') == 'Circular':
		# Circle platform for delta printers...
		circle = []
		steps = 32
		for n in xrange(0, steps):
			circle.append([math.cos(float(n)/steps*2*math.pi) * size[0]/2, math.sin(float(n)/steps*2*math.pi) * size[1]/2])
		ret.append(numpy.array(circle, numpy.float32))
	else:
		ret.append(numpy.array([[-size[0]/2,-size[1]/2],[size[0]/2,-size[1]/2],[size[0]/2, size[1]/2], [-size[0]/2, size[1]/2]], numpy.float32))

	if getMachineSetting('machine_type') == 'ultimaker2':
		#UM2 no-go zones
		w = 25
		h = 10
		ret.append(numpy.array([[-size[0]/2,-size[1]/2],[-size[0]/2+w+2,-size[1]/2], [-size[0]/2+w,-size[1]/2+h], [-size[0]/2,-size[1]/2+h]], numpy.float32))
		ret.append(numpy.array([[ size[0]/2-w-2,-size[1]/2],[ size[0]/2,-size[1]/2], [ size[0]/2,-size[1]/2+h],[ size[0]/2-w,-size[1]/2+h]], numpy.float32))
		ret.append(numpy.array([[-size[0]/2+w+2, size[1]/2],[-size[0]/2, size[1]/2], [-size[0]/2, size[1]/2-h],[-size[0]/2+w, size[1]/2-h]], numpy.float32))
		ret.append(numpy.array([[ size[0]/2, size[1]/2],[ size[0]/2-w-2, size[1]/2], [ size[0]/2-w, size[1]/2-h],[ size[0]/2, size[1]/2-h]], numpy.float32))
	return ret

#returns the number of extruders minimal used. Normally this returns 1, but with dual-extrusion support material it returns 2
def minimalExtruderCount():
	if int(getMachineSetting('extruder_amount')) < 2:
		return 1
	if getProfileSetting('support') == 'None':
		return 1
	if getProfileSetting('support_dual_extrusion') == 'Second extruder':
		return 2
	return 1

def getGCodeExtension():
	if getMachineSetting('gcode_flavor') == 'BFB':
		return '.bfb'
	return '.gcode'

#########################################################
## Alteration file functions
#########################################################
def replaceTagMatch(m):
	pre = m.group(1)
	tag = m.group(2)
	if tag == 'time':
		return pre + time.strftime('%H:%M:%S')
	if tag == 'date':
		return pre + time.strftime('%d-%m-%Y')
	if tag == 'day':
		return pre + ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'][int(time.strftime('%w'))]
	if tag == 'print_time':
		return pre + '#P_TIME#'
	if tag == 'filament_amount':
		return pre + '#F_AMNT#'
	if tag == 'filament_weight':
		return pre + '#F_WGHT#'
	if tag == 'filament_cost':
		return pre + '#F_COST#'
	if tag == 'profile_string':
		return pre + 'CURA_PROFILE_STRING:%s' % (getProfileString())
	if pre == 'F' and tag == 'max_z_speed':
		f = getProfileSettingFloat('travel_speed') * 60
	if pre == 'F' and tag in ['print_speed', 'retraction_speed', 'travel_speed', 'bottom_layer_speed', 'cool_min_feedrate']:
		f = getProfileSettingFloat(tag) * 60
	elif isProfileSetting(tag):
		f = getProfileSettingFloat(tag)
	elif isPreference(tag):
		f = getProfileSettingFloat(tag)
	else:
		return '%s?%s?' % (pre, tag)
	if (f % 1) == 0:
		return pre + str(int(f))
	return pre + str(f)

def replaceGCodeTags(filename, gcodeInt):
	f = open(filename, 'r+')
	data = f.read(2048)
	data = data.replace('#P_TIME#', ('%5d:%02d' % (int(gcodeInt.totalMoveTimeMinute / 60), int(gcodeInt.totalMoveTimeMinute % 60)))[-8:])
	data = data.replace('#F_AMNT#', ('%8.2f' % (gcodeInt.extrusionAmount / 1000))[-8:])
	data = data.replace('#F_WGHT#', ('%8.2f' % (gcodeInt.calculateWeight() * 1000))[-8:])
	cost = gcodeInt.calculateCost()
	if cost is None:
		cost = 'Unknown'
	data = data.replace('#F_COST#', ('%8s' % (cost.split(' ')[0]))[-8:])
	f.seek(0)
	f.write(data)
	f.close()

def replaceGCodeTagsFromSlicer(filename, slicerInt):
	f = open(filename, 'r+')
	data = f.read(2048)
	data = data.replace('#P_TIME#', ('%8.2f' % (int(slicerInt._printTimeSeconds)))[-8:])
	data = data.replace('#F_AMNT#', ('%8.2f' % (slicerInt._filamentMM[0]))[-8:])
	data = data.replace('#F_WGHT#', ('%8.2f' % (float(slicerInt.getFilamentWeight()) * 1000))[-8:])
	cost = slicerInt.getFilamentCost()
	if cost is None:
		cost = 'Unknown'
	data = data.replace('#F_COST#', ('%8s' % (cost.split(' ')[0]))[-8:])
	f.seek(0)
	f.write(data)
	f.close()

### Get aleration raw contents. (Used internally in Cura)
def getAlterationFile(filename):
	if filename in tempOverride:
		return tempOverride[filename]
	global settingsDictionary
	if filename in settingsDictionary and settingsDictionary[filename].isAlteration():
		return settingsDictionary[filename].getValue()
	traceback.print_stack()
	sys.stderr.write('Error: "%s" not found in alteration settings\n' % (filename))
	return ''

def setAlterationFile(name, value):
	#Check if we have a configuration file loaded, else load the default.
	global settingsDictionary
	if name in settingsDictionary and settingsDictionary[name].isAlteration():
		settingsDictionary[name].setValue(value)
	saveProfile(getDefaultProfilePath(), True)

def isTagIn(tag, contents):
	contents = re.sub(';[^\n]*\n', '', contents)
	return tag in contents

### Get the alteration file for output. (Used by Skeinforge)
def getAlterationFileContents(filename, extruderCount = 1):
	prefix = ''
	postfix = ''
	alterationContents = getAlterationFile(filename)
	if getMachineSetting('gcode_flavor') == 'UltiGCode':
		if filename == 'end.gcode':
			return 'M25 ;Stop reading from this point on.\n;CURA_PROFILE_STRING:%s\n' % (getProfileString())
		return ''
	if filename == 'start.gcode':
		if extruderCount > 1:
			alterationContents = getAlterationFile("start%d.gcode" % (extruderCount))
		#For the start code, hack the temperature and the steps per E value into it. So the temperature is reached before the start code extrusion.
		#We also set our steps per E here, if configured.
		eSteps = getMachineSettingFloat('steps_per_e')
		if eSteps > 0:
			prefix += 'M92 E%f\n' % (eSteps)
		temp = getProfileSettingFloat('print_temperature')
		bedTemp = 0
		if getMachineSetting('has_heated_bed') == 'True':
			bedTemp = getProfileSettingFloat('print_bed_temperature')

		if bedTemp > 0 and not isTagIn('{print_bed_temperature}', alterationContents):
			prefix += 'M140 S%f\n' % (bedTemp)
		if temp > 0 and not isTagIn('{print_temperature}', alterationContents):
			if extruderCount > 0:
				for n in xrange(1, extruderCount):
					t = temp
					if n > 0 and getProfileSettingFloat('print_temperature%d' % (n+1)) > 0:
						t = getProfileSettingFloat('print_temperature%d' % (n+1))
					prefix += 'M104 T%d S%f\n' % (n, t)
				for n in xrange(0, extruderCount):
					t = temp
					if n > 0 and getProfileSettingFloat('print_temperature%d' % (n+1)) > 0:
						t = getProfileSettingFloat('print_temperature%d' % (n+1))
					prefix += 'M109 T%d S%f\n' % (n, t)
				prefix += 'T0\n'
			else:
				prefix += 'M109 S%f\n' % (temp)
		if bedTemp > 0 and not isTagIn('{print_bed_temperature}', alterationContents):
			prefix += 'M190 S%f\n' % (bedTemp)
	elif filename == 'end.gcode':
		if extruderCount > 1:
			alterationContents = getAlterationFile("end%d.gcode" % (extruderCount))
		#Append the profile string to the end of the GCode, so we can load it from the GCode file later.
		#postfix = ';CURA_PROFILE_STRING:%s\n' % (getProfileString())
	return unicode(prefix + re.sub("(.)\{([^\}]*)\}", replaceTagMatch, alterationContents).rstrip() + '\n' + postfix).strip().encode('utf-8') + '\n'

########NEW FILE########
__FILENAME__ = biome_types
biome_types = {
    -1: "Will be computed",
    0: "Ocean",
    1: "Plains",
    2: "Desert",
    3: "Extreme Hills",
    4: "Forest",
    5: "Taiga",
    6: "Swampland",
    7: "River",
    8: "Hell",
    9: "Sky",
    10: "FrozenOcean",
    11: "FrozenRiver",
    12: "Ice Plains",
    13: "Ice Mountains",
    14: "MushroomIsland",
    15: "MushroomIslandShore",
    16: "Beach",
    17: "DesertHills",
    18: "ForestHills",
    19: "TaigaHills",
    20: "Extreme Hills Edge",
    21: "Jungle",
    22: "JungleHills",
}

########NEW FILE########
__FILENAME__ = blockrotation
from materials import alphaMaterials
from numpy import arange, zeros


def genericVerticalFlip(cls):
    rotation = arange(16, dtype='uint8')
    if hasattr(cls, "Up") and hasattr(cls, "Down"):
        rotation[cls.Up] = cls.Down
        rotation[cls.Down] = cls.Up

    if hasattr(cls, "TopNorth") and hasattr(cls, "TopWest") and hasattr(cls, "TopSouth") and hasattr(cls, "TopEast"):
        rotation[cls.North] = cls.TopNorth
        rotation[cls.West] = cls.TopWest
        rotation[cls.South] = cls.TopSouth
        rotation[cls.East] = cls.TopEast
        rotation[cls.TopNorth] = cls.North
        rotation[cls.TopWest] = cls.West
        rotation[cls.TopSouth] = cls.South
        rotation[cls.TopEast] = cls.East

    return rotation


def genericRotation(cls):
    rotation = arange(16, dtype='uint8')
    rotation[cls.North] = cls.West
    rotation[cls.West] = cls.South
    rotation[cls.South] = cls.East
    rotation[cls.East] = cls.North
    if hasattr(cls, "TopNorth") and hasattr(cls, "TopWest") and hasattr(cls, "TopSouth") and hasattr(cls, "TopEast"):
        rotation[cls.TopNorth] = cls.TopWest
        rotation[cls.TopWest] = cls.TopSouth
        rotation[cls.TopSouth] = cls.TopEast
        rotation[cls.TopEast] = cls.TopNorth

    return rotation


def genericEastWestFlip(cls):
    rotation = arange(16, dtype='uint8')
    rotation[cls.West] = cls.East
    rotation[cls.East] = cls.West
    if hasattr(cls, "TopWest") and hasattr(cls, "TopEast"):
        rotation[cls.TopWest] = cls.TopEast
        rotation[cls.TopEast] = cls.TopWest

    return rotation


def genericNorthSouthFlip(cls):
    rotation = arange(16, dtype='uint8')
    rotation[cls.South] = cls.North
    rotation[cls.North] = cls.South
    if hasattr(cls, "TopNorth") and hasattr(cls, "TopSouth"):
        rotation[cls.TopSouth] = cls.TopNorth
        rotation[cls.TopNorth] = cls.TopSouth

    return rotation

rotationClasses = []


def genericFlipRotation(cls):
    cls.rotateLeft = genericRotation(cls)

    cls.flipVertical = genericVerticalFlip(cls)
    cls.flipEastWest = genericEastWestFlip(cls)
    cls.flipNorthSouth = genericNorthSouthFlip(cls)
    rotationClasses.append(cls)


class Torch:
    blocktypes = [
        alphaMaterials.Torch.ID,
        alphaMaterials.RedstoneTorchOn.ID,
        alphaMaterials.RedstoneTorchOff.ID,
    ]

    South = 1
    North = 2
    West = 3
    East = 4

genericFlipRotation(Torch)


class Ladder:
    blocktypes = [alphaMaterials.Ladder.ID]

    East = 2
    West = 3
    North = 4
    South = 5
genericFlipRotation(Ladder)


class Stair:
    blocktypes = [b.ID for b in alphaMaterials.AllStairs]

    South = 0
    North = 1
    West = 2
    East = 3
    TopSouth = 4
    TopNorth = 5
    TopWest = 6
    TopEast = 7
genericFlipRotation(Stair)


class HalfSlab:
    blocktypes = [alphaMaterials.StoneSlab.ID]

    StoneSlab = 0
    SandstoneSlab = 1
    WoodenSlab = 2
    CobblestoneSlab = 3
    BrickSlab = 4
    StoneBrickSlab = 5
    TopStoneSlab = 8
    TopSandstoneSlab = 9
    TopWoodenSlab = 10
    TopCobblestoneSlab = 11
    TopBrickSlab = 12
    TopStoneBrickSlab = 13

HalfSlab.flipVertical =  arange(16, dtype='uint8')
HalfSlab.flipVertical[HalfSlab.StoneSlab] = HalfSlab.TopStoneSlab
HalfSlab.flipVertical[HalfSlab.SandstoneSlab] = HalfSlab.TopSandstoneSlab
HalfSlab.flipVertical[HalfSlab.WoodenSlab] = HalfSlab.TopWoodenSlab
HalfSlab.flipVertical[HalfSlab.CobblestoneSlab] = HalfSlab.TopCobblestoneSlab
HalfSlab.flipVertical[HalfSlab.BrickSlab] = HalfSlab.TopBrickSlab
HalfSlab.flipVertical[HalfSlab.StoneBrickSlab] = HalfSlab.TopStoneBrickSlab
HalfSlab.flipVertical[HalfSlab.TopStoneSlab] = HalfSlab.StoneSlab
HalfSlab.flipVertical[HalfSlab.TopSandstoneSlab] = HalfSlab.SandstoneSlab
HalfSlab.flipVertical[HalfSlab.TopWoodenSlab] = HalfSlab.WoodenSlab
HalfSlab.flipVertical[HalfSlab.TopCobblestoneSlab] = HalfSlab.CobblestoneSlab
HalfSlab.flipVertical[HalfSlab.TopBrickSlab] = HalfSlab.BrickSlab
HalfSlab.flipVertical[HalfSlab.TopStoneBrickSlab] = HalfSlab.StoneBrickSlab
rotationClasses.append(HalfSlab)


class WallSign:
    blocktypes = [alphaMaterials.WallSign.ID]

    East = 2
    West = 3
    North = 4
    South = 5
genericFlipRotation(WallSign)


class FurnaceDispenserChest:
    blocktypes = [
        alphaMaterials.Furnace.ID,
        alphaMaterials.LitFurnace.ID,
        alphaMaterials.Dispenser.ID,
        alphaMaterials.Chest.ID,
    ]
    East = 2
    West = 3
    North = 4
    South = 5
genericFlipRotation(FurnaceDispenserChest)


class Pumpkin:
    blocktypes = [
        alphaMaterials.Pumpkin.ID,
        alphaMaterials.JackOLantern.ID,
    ]

    East = 0
    South = 1
    West = 2
    North = 3
genericFlipRotation(Pumpkin)


class Rail:
    blocktypes = [alphaMaterials.Rail.ID]

    EastWest = 0
    NorthSouth = 1
    South = 2
    North = 3
    East = 4
    West = 5

    Northeast = 6
    Southeast = 7
    Southwest = 8
    Northwest = 9


def generic8wayRotation(cls):

    cls.rotateLeft = genericRotation(cls)
    cls.rotateLeft[cls.Northeast] = cls.Northwest
    cls.rotateLeft[cls.Southeast] = cls.Northeast
    cls.rotateLeft[cls.Southwest] = cls.Southeast
    cls.rotateLeft[cls.Northwest] = cls.Southwest

    cls.flipEastWest = genericEastWestFlip(cls)
    cls.flipEastWest[cls.Northeast] = cls.Northwest
    cls.flipEastWest[cls.Northwest] = cls.Northeast
    cls.flipEastWest[cls.Southwest] = cls.Southeast
    cls.flipEastWest[cls.Southeast] = cls.Southwest

    cls.flipNorthSouth = genericNorthSouthFlip(cls)
    cls.flipNorthSouth[cls.Northeast] = cls.Southeast
    cls.flipNorthSouth[cls.Southeast] = cls.Northeast
    cls.flipNorthSouth[cls.Southwest] = cls.Northwest
    cls.flipNorthSouth[cls.Northwest] = cls.Southwest
    rotationClasses.append(cls)

generic8wayRotation(Rail)
Rail.rotateLeft[Rail.NorthSouth] = Rail.EastWest
Rail.rotateLeft[Rail.EastWest] = Rail.NorthSouth


def applyBit(apply):
    def _applyBit(class_or_array):
        if hasattr(class_or_array, "rotateLeft"):
            for a in (class_or_array.flipEastWest,
                      class_or_array.flipNorthSouth,
                      class_or_array.rotateLeft):
                apply(a)
        else:
            array = class_or_array
            apply(array)

    return _applyBit


@applyBit
def applyBit8(array):
    array[8:16] = array[0:8] | 0x8


@applyBit
def applyBit4(array):
    array[4:8] = array[0:4] | 0x4
    array[12:16] = array[8:12] | 0x4


@applyBit
def applyBits48(array):
    array[4:8] = array[0:4] | 0x4
    array[8:16] = array[0:8] | 0x8

applyThrownBit = applyBit8


class PoweredDetectorRail(Rail):
    blocktypes = [alphaMaterials.PoweredRail.ID, alphaMaterials.DetectorRail.ID]
PoweredDetectorRail.rotateLeft = genericRotation(PoweredDetectorRail)

PoweredDetectorRail.rotateLeft[PoweredDetectorRail.NorthSouth] = PoweredDetectorRail.EastWest
PoweredDetectorRail.rotateLeft[PoweredDetectorRail.EastWest] = PoweredDetectorRail.NorthSouth

PoweredDetectorRail.flipEastWest = genericEastWestFlip(PoweredDetectorRail)
PoweredDetectorRail.flipNorthSouth = genericNorthSouthFlip(PoweredDetectorRail)
applyThrownBit(PoweredDetectorRail)
rotationClasses.append(PoweredDetectorRail)


class Lever:
    blocktypes = [alphaMaterials.Lever.ID]
    ThrownBit = 0x8
    South = 1
    North = 2
    West = 3
    East = 4
    EastWest = 5
    NorthSouth = 6
Lever.rotateLeft = genericRotation(Lever)
Lever.rotateLeft[Lever.NorthSouth] = Lever.EastWest
Lever.rotateLeft[Lever.EastWest] = Lever.NorthSouth
Lever.flipEastWest = genericEastWestFlip(Lever)
Lever.flipNorthSouth = genericNorthSouthFlip(Lever)
applyThrownBit(Lever)
rotationClasses.append(Lever)


class Button:
    blocktypes = [alphaMaterials.Button.ID]
    PressedBit = 0x8
    South = 1
    North = 2
    West = 3
    East = 4
Button.rotateLeft = genericRotation(Button)
Button.flipEastWest = genericEastWestFlip(Button)
Button.flipNorthSouth = genericNorthSouthFlip(Button)
applyThrownBit(Button)
rotationClasses.append(Button)


class SignPost:
    blocktypes = [alphaMaterials.Sign.ID]
    #west is 0, increasing clockwise

    rotateLeft = arange(16, dtype='uint8')
    rotateLeft -= 4
    rotateLeft &= 0xf

    flipEastWest = arange(16, dtype='uint8')
    flipNorthSouth = arange(16, dtype='uint8')
    pass

rotationClasses.append(SignPost)


class Bed:
    blocktypes = [alphaMaterials.Bed.ID]
    West = 0
    North = 1
    East = 2
    South = 3

genericFlipRotation(Bed)
applyBit8(Bed)
applyBit4(Bed)


class Door:
    blocktypes = [
        alphaMaterials.IronDoor.ID,
        alphaMaterials.WoodenDoor.ID,
    ]
    TopHalfBit = 0x8
    SwungCCWBit = 0x4

    Northeast = 0
    Southeast = 1
    Southwest = 2
    Northwest = 3

    rotateLeft = arange(16, dtype='uint8')

Door.rotateLeft[Door.Northeast] = Door.Northwest
Door.rotateLeft[Door.Southeast] = Door.Northeast
Door.rotateLeft[Door.Southwest] = Door.Southeast
Door.rotateLeft[Door.Northwest] = Door.Southwest

applyBit4(Door.rotateLeft)

#when flipping horizontally, swing the doors so they at least look the same

Door.flipEastWest = arange(16, dtype='uint8')
Door.flipEastWest[Door.Northeast] = Door.Northwest
Door.flipEastWest[Door.Northwest] = Door.Northeast
Door.flipEastWest[Door.Southwest] = Door.Southeast
Door.flipEastWest[Door.Southeast] = Door.Southwest
Door.flipEastWest[4:8] = Door.flipEastWest[0:4]
Door.flipEastWest[0:4] = Door.flipEastWest[4:8] | 0x4
Door.flipEastWest[8:16] = Door.flipEastWest[0:8] | 0x8

Door.flipNorthSouth = arange(16, dtype='uint8')
Door.flipNorthSouth[Door.Northeast] = Door.Southeast
Door.flipNorthSouth[Door.Northwest] = Door.Southwest
Door.flipNorthSouth[Door.Southwest] = Door.Northwest
Door.flipNorthSouth[Door.Southeast] = Door.Northeast
Door.flipNorthSouth[4:8] = Door.flipNorthSouth[0:4]
Door.flipNorthSouth[0:4] = Door.flipNorthSouth[4:8] | 0x4
Door.flipNorthSouth[8:16] = Door.flipNorthSouth[0:8] | 0x8

rotationClasses.append(Door)


class RedstoneRepeater:
    blocktypes = [
        alphaMaterials.RedstoneRepeaterOff.ID,
        alphaMaterials.RedstoneRepeaterOn.ID,

    ]

    East = 0
    South = 1
    West = 2
    North = 3

genericFlipRotation(RedstoneRepeater)

#high bits of the repeater indicate repeater delay, and should be preserved
applyBits48(RedstoneRepeater)


class Trapdoor:
    blocktypes = [alphaMaterials.Trapdoor.ID]

    West = 0
    East = 1
    South = 2
    North = 3

genericFlipRotation(Trapdoor)
applyOpenedBit = applyBit4
applyOpenedBit(Trapdoor)


class PistonBody:
    blocktypes = [alphaMaterials.StickyPiston.ID, alphaMaterials.Piston.ID]

    Down = 0
    Up = 1
    East = 2
    West = 3
    North = 4
    South = 5

genericFlipRotation(PistonBody)
applyPistonBit = applyBit8
applyPistonBit(PistonBody)


class PistonHead(PistonBody):
    blocktypes = [alphaMaterials.PistonHead.ID]
rotationClasses.append(PistonHead)


class Vines:
    blocktypes = [alphaMaterials.Vines.ID]

    WestBit = 1
    NorthBit = 2
    EastBit = 4
    SouthBit = 8

    rotateLeft = arange(16, dtype='uint8')
    flipEastWest = arange(16, dtype='uint8')
    flipNorthSouth = arange(16, dtype='uint8')


#Mushroom types:
#Value     Description     Textures
#0     Fleshy piece     Pores on all sides
#1     Corner piece     Cap texture on top, directions 1 (cloud direction) and 2 (sunrise)
#2     Side piece     Cap texture on top and direction 2 (sunrise)
#3     Corner piece     Cap texture on top, directions 2 (sunrise) and 3 (cloud origin)
#4     Side piece     Cap texture on top and direction 1 (cloud direction)
#5     Top piece     Cap texture on top
#6     Side piece     Cap texture on top and direction 3 (cloud origin)
#7     Corner piece     Cap texture on top, directions 0 (sunset) and 1 (cloud direction)
#8     Side piece     Cap texture on top and direction 0 (sunset)
#9     Corner piece     Cap texture on top, directions 3 (cloud origin) and 0 (sunset)
#10     Stem piece     Stem texture on all four sides, pores on top and bottom


class HugeMushroom:
    blocktypes = [alphaMaterials.HugeRedMushroom.ID, alphaMaterials.HugeBrownMushroom.ID]
    Northeast = 1
    East = 2
    Southeast = 3
    South = 6
    Southwest = 9
    West = 8
    Northwest = 7
    North = 4

generic8wayRotation(HugeMushroom)

#Hmm... Since each bit is a direction, we can rotate by shifting!
Vines.rotateLeft = 0xf & ((Vines.rotateLeft >> 1) | (Vines.rotateLeft << 3))
# Wherever each bit is set, clear it and set the opposite bit
EastWestBits = (Vines.EastBit | Vines.WestBit)
Vines.flipEastWest[(Vines.flipEastWest & EastWestBits) > 0] ^= EastWestBits

NorthSouthBits = (Vines.NorthBit | Vines.SouthBit)
Vines.flipNorthSouth[(Vines.flipNorthSouth & NorthSouthBits) > 0] ^= NorthSouthBits

rotationClasses.append(Vines)


def masterRotationTable(attrname):
    # compute a 256x16 table mapping each possible blocktype/data combination to
    # the resulting data when the block is rotated
    table = zeros((256, 16), dtype='uint8')
    table[:] = arange(16, dtype='uint8')
    for cls in rotationClasses:
        if hasattr(cls, attrname):
            blocktable = getattr(cls, attrname)
            for blocktype in cls.blocktypes:
                table[blocktype] = blocktable

    return table


def rotationTypeTable():
    table = {}
    for cls in rotationClasses:
        for b in cls.blocktypes:
            table[b] = cls

    return table


class BlockRotation:
    rotateLeft = masterRotationTable("rotateLeft")
    flipEastWest = masterRotationTable("flipEastWest")
    flipNorthSouth = masterRotationTable("flipNorthSouth")
    flipVertical = masterRotationTable("flipVertical")
    typeTable = rotationTypeTable()


def SameRotationType(blocktype1, blocktype2):
    #use different default values for typeTable.get() to make it return false when neither blocktype is present
    return BlockRotation.typeTable.get(blocktype1.ID) == BlockRotation.typeTable.get(blocktype2.ID, BlockRotation)


def FlipVertical(blocks, data):
    data[:] = BlockRotation.flipVertical[blocks, data]


def FlipNorthSouth(blocks, data):
    data[:] = BlockRotation.flipNorthSouth[blocks, data]


def FlipEastWest(blocks, data):
    data[:] = BlockRotation.flipEastWest[blocks, data]


def RotateLeft(blocks, data):
    data[:] = BlockRotation.rotateLeft[blocks, data]

########NEW FILE########
__FILENAME__ = block_copy
from datetime import datetime
import logging
log = logging.getLogger(__name__)

import numpy
from box import BoundingBox, Vector
from mclevelbase import exhaust
import materials
from entity import Entity, TileEntity


def convertBlocks(destLevel, sourceLevel, blocks, blockData):
    return materials.convertBlocks(destLevel.materials, sourceLevel.materials, blocks, blockData)

def sourceMaskFunc(blocksToCopy):
    if blocksToCopy is not None:
        typemask = numpy.zeros(256, dtype='bool')
        typemask[blocksToCopy] = 1

        def maskedSourceMask(sourceBlocks):
            return typemask[sourceBlocks]

        return maskedSourceMask

    def unmaskedSourceMask(_sourceBlocks):
        return slice(None, None)

    return unmaskedSourceMask


def adjustCopyParameters(destLevel, sourceLevel, sourceBox, destinationPoint):
    # if the destination box is outside the level, it and the source corners are moved inward to fit.
    (dx, dy, dz) = map(int, destinationPoint)

    log.debug(u"Asked to copy {} blocks \n\tfrom {} in {}\n\tto {} in {}" .format(
              sourceBox.volume, sourceBox, sourceLevel, destinationPoint, destLevel))
    if destLevel.Width == 0:
        return sourceBox, destinationPoint

    destBox = BoundingBox(destinationPoint, sourceBox.size)
    actualDestBox = destBox.intersect(destLevel.bounds)

    actualSourceBox = BoundingBox(sourceBox.origin + actualDestBox.origin - destBox.origin, destBox.size)
    actualDestPoint = actualDestBox.origin

    return actualSourceBox, actualDestPoint



def copyBlocksFromIter(destLevel, sourceLevel, sourceBox, destinationPoint, blocksToCopy=None, entities=True, create=False):
    """ copy blocks between two infinite levels by looping through the
    destination's chunks. make a sub-box of the source level for each chunk
    and copy block and entities in the sub box to the dest chunk."""

    (lx, ly, lz) = sourceBox.size

    sourceBox, destinationPoint = adjustCopyParameters(destLevel, sourceLevel, sourceBox, destinationPoint)
    # needs work xxx
    log.info(u"Copying {0} blocks from {1} to {2}" .format(ly * lz * lx, sourceBox, destinationPoint))
    startTime = datetime.now()

    destBox = BoundingBox(destinationPoint, sourceBox.size)
    chunkCount = destBox.chunkCount
    i = 0
    e = 0
    t = 0

    sourceMask = sourceMaskFunc(blocksToCopy)

    copyOffset = [d - s for s, d in zip(sourceBox.origin, destinationPoint)]

    # Visit each chunk in the destination area.
    #   Get the region of the source area corresponding to that chunk
    #   Visit each chunk of the region of the source area
    #     Get the slices of the destination chunk
    #     Get the slices of the source chunk
    #     Copy blocks and data

    for destCpos in destBox.chunkPositions:
        cx, cz = destCpos

        destChunkBox = BoundingBox((cx << 4, 0, cz << 4), (16, destLevel.Height, 16)).intersect(destBox)
        destChunkBoxInSourceLevel = BoundingBox([d - o for o, d in zip(copyOffset, destChunkBox.origin)], destChunkBox.size)

        if not destLevel.containsChunk(*destCpos):
            if create and any(sourceLevel.containsChunk(*c) for c in destChunkBoxInSourceLevel.chunkPositions):
                # Only create chunks in the destination level if the source level has chunks covering them.
                destLevel.createChunk(*destCpos)
            else:
                continue

        destChunk = destLevel.getChunk(*destCpos)


        i += 1
        yield (i, chunkCount)
        if i % 100 == 0:
            log.info("Chunk {0}...".format(i))

        for srcCpos in destChunkBoxInSourceLevel.chunkPositions:
            if not sourceLevel.containsChunk(*srcCpos):
                continue

            sourceChunk = sourceLevel.getChunk(*srcCpos)

            sourceChunkBox, sourceSlices = sourceChunk.getChunkSlicesForBox(destChunkBoxInSourceLevel)
            sourceChunkBoxInDestLevel = BoundingBox([d + o for o, d in zip(copyOffset, sourceChunkBox.origin)], sourceChunkBox.size)

            _, destSlices = destChunk.getChunkSlicesForBox(sourceChunkBoxInDestLevel)

            sourceBlocks = sourceChunk.Blocks[sourceSlices]
            sourceData = sourceChunk.Data[sourceSlices]

            mask = sourceMask(sourceBlocks)
            convertedSourceBlocks, convertedSourceData = convertBlocks(destLevel, sourceLevel, sourceBlocks, sourceData)

            destChunk.Blocks[destSlices][mask] = convertedSourceBlocks[mask]
            if convertedSourceData is not None:
                destChunk.Data[destSlices][mask] = convertedSourceData[mask]

            if entities:
                ents = sourceChunk.getEntitiesInBox(destChunkBoxInSourceLevel)
                e += len(ents)
                for entityTag in ents:
                    eTag = Entity.copyWithOffset(entityTag, copyOffset)
                    destLevel.addEntity(eTag)

            tileEntities = sourceChunk.getTileEntitiesInBox(destChunkBoxInSourceLevel)
            t += len(tileEntities)
            for tileEntityTag in tileEntities:
                eTag = TileEntity.copyWithOffset(tileEntityTag, copyOffset)
                destLevel.addTileEntity(eTag)

        destChunk.chunkChanged()

    log.info("Duration: {0}".format(datetime.now() - startTime))
    log.info("Copied {0} entities and {1} tile entities".format(e, t))

def copyBlocksFrom(destLevel, sourceLevel, sourceBox, destinationPoint, blocksToCopy=None, entities=True, create=False):
    return exhaust(copyBlocksFromIter(destLevel, sourceLevel, sourceBox, destinationPoint, blocksToCopy, entities, create))






########NEW FILE########
__FILENAME__ = block_fill
import logging
log = logging.getLogger(__name__)

import numpy

from mclevelbase import exhaust
import blockrotation
from entity import TileEntity

def blockReplaceTable(blocksToReplace):
    blocktable = numpy.zeros((256, 16), dtype='bool')
    for b in blocksToReplace:
        if b.hasVariants:
            blocktable[b.ID, b.blockData] = True
        else:
            blocktable[b.ID] = True

    return blocktable

def fillBlocks(level, box, blockInfo, blocksToReplace=()):
    return exhaust(level.fillBlocksIter(box, blockInfo, blocksToReplace))

def fillBlocksIter(level, box, blockInfo, blocksToReplace=()):
    if box is None:
        chunkIterator = level.getAllChunkSlices()
        box = level.bounds
    else:
        chunkIterator = level.getChunkSlices(box)

    # shouldRetainData = (not blockInfo.hasVariants and not any([b.hasVariants for b in blocksToReplace]))
    # if shouldRetainData:
    #    log.info( "Preserving data bytes" )
    shouldRetainData = False  # xxx old behavior overwrote blockdata with 0 when e.g. replacing water with lava

    log.info("Replacing {0} with {1}".format(blocksToReplace, blockInfo))

    changesLighting = True
    blocktable = None
    if len(blocksToReplace):
        blocktable = blockReplaceTable(blocksToReplace)
        shouldRetainData = all([blockrotation.SameRotationType(blockInfo, b) for b in blocksToReplace])

        newAbsorption = level.materials.lightAbsorption[blockInfo.ID]
        oldAbsorptions = [level.materials.lightAbsorption[b.ID] for b in blocksToReplace]
        changesLighting = False
        for a in oldAbsorptions:
            if a != newAbsorption:
                changesLighting = True

        newEmission = level.materials.lightEmission[blockInfo.ID]
        oldEmissions = [level.materials.lightEmission[b.ID] for b in blocksToReplace]
        for a in oldEmissions:
            if a != newEmission:
                changesLighting = True

    i = 0
    skipped = 0
    replaced = 0

    for (chunk, slices, point) in chunkIterator:
        i += 1
        if i % 100 == 0:
            log.info(u"Chunk {0}...".format(i))
        yield i, box.chunkCount

        blocks = chunk.Blocks[slices]
        data = chunk.Data[slices]
        mask = slice(None)

        needsLighting = changesLighting

        if blocktable is not None:
            mask = blocktable[blocks, data]

            blockCount = mask.sum()
            replaced += blockCount

            # don't waste time relighting and copying if the mask is empty
            if blockCount:
                blocks[:][mask] = blockInfo.ID
                if not shouldRetainData:
                    data[mask] = blockInfo.blockData
            else:
                skipped += 1
                needsLighting = False

            def include(tileEntity):
                p = TileEntity.pos(tileEntity)
                x, y, z = map(lambda a, b, c: (a - b) - c, p, point, box.origin)
                return not ((p in box) and mask[x, z, y])

            chunk.TileEntities[:] = filter(include, chunk.TileEntities)

        else:
            blocks[:] = blockInfo.ID
            if not shouldRetainData:
                data[:] = blockInfo.blockData
            chunk.removeTileEntitiesInBox(box)

        chunk.chunkChanged(needsLighting)

    if len(blocksToReplace):
        log.info(u"Replace: Skipped {0} chunks, replaced {1} blocks".format(skipped, replaced))

########NEW FILE########
__FILENAME__ = box
from collections import namedtuple
import itertools

_Vector = namedtuple("_Vector", ("x", "y", "z"))

class Vector(_Vector):

    __slots__ = ()

    def __add__(self, other):
        return Vector(self[0] + other[0], self[1] + other[1], self[2] + other[2])
    def __sub__(self, other):
        return Vector(self[0] - other[0], self[1] - other[1], self[2] - other[2])
    def __mul__(self, other):
        return Vector(self[0] * other[0], self[1] * other[1], self[2] * other[2])

class BoundingBox (object):
    type = int

    def __init__(self, origin=(0, 0, 0), size=(0, 0, 0)):
        if isinstance(origin, BoundingBox):
            self._origin = origin._origin
            self._size = origin._size
        else:
            self._origin, self._size = Vector(*(self.type(a) for a in origin)), Vector(*(self.type(a) for a in size))

    def __repr__(self):
        return "BoundingBox({0}, {1})".format(self.origin, self.size)

    @property
    def origin(self):
        "The smallest position in the box"
        return self._origin

    @property
    def size(self):
        "The size of the box"
        return self._size

    @property
    def width(self):
        "The dimension along the X axis"
        return self._size.x

    @property
    def height(self):
        "The dimension along the Y axis"
        return self._size.y

    @property
    def length(self):
        "The dimension along the Z axis"
        return self._size.z

    @property
    def minx(self):
        return self.origin.x

    @property
    def miny(self):
        return self.origin.y

    @property
    def minz(self):
        return self.origin.z

    @property
    def maxx(self):
        return self.origin.x + self.size.x

    @property
    def maxy(self):
        return self.origin.y + self.size.y

    @property
    def maxz(self):
        return self.origin.z + self.size.z

    @property
    def maximum(self):
        "The largest point of the box; origin plus size."
        return self._origin + self._size

    @property
    def volume(self):
        "The volume of the box in blocks"
        return self.size.x * self.size.y * self.size.z

    @property
    def positions(self):
        """iterate through all of the positions within this selection box"""
        return itertools.product(
            xrange(self.minx, self.maxx),
            xrange(self.miny, self.maxy),
            xrange(self.minz, self.maxz)
        )

    def intersect(self, box):
        """
        Return a box containing the area self and box have in common. Box will have zero volume
         if there is no common area.
        """
        if (self.minx > box.maxx or self.maxx < box.minx or
            self.miny > box.maxy or self.maxy < box.miny or
            self.minz > box.maxz or self.maxz < box.minz):
            #Zero size intersection.
            return BoundingBox()

        origin = Vector(
            max(self.minx, box.minx),
            max(self.miny, box.miny),
            max(self.minz, box.minz),
        )
        maximum = Vector(
            min(self.maxx, box.maxx),
            min(self.maxy, box.maxy),
            min(self.maxz, box.maxz),
        )

        #print "Intersect of {0} and {1}: {2}".format(self, box, newbox)
        return BoundingBox(origin, maximum - origin)

    def union(self, box):
        """
        Return a box large enough to contain both self and box.
        """
        origin = Vector(
            min(self.minx, box.minx),
            min(self.miny, box.miny),
            min(self.minz, box.minz),
        )
        maximum = Vector(
            max(self.maxx, box.maxx),
            max(self.maxy, box.maxy),
            max(self.maxz, box.maxz),
        )
        return BoundingBox(origin, maximum - origin)

    def expand(self, dx, dy=None, dz=None):
        """
        Return a new box with boundaries expanded by dx, dy, dz.
        If only dx is passed, expands by dx in all dimensions.
        """
        if dz is None:
            dz = dx
        if dy is None:
            dy = dx

        origin = self.origin - (dx, dy, dz)
        size = self.size + (dx * 2, dy * 2, dz * 2)

        return BoundingBox(origin, size)

    def __contains__(self, pos):
        x, y, z = pos
        if x < self.minx or x >= self.maxx:
            return False
        if y < self.miny or y >= self.maxy:
            return False
        if z < self.minz or z >= self.maxz:
            return False

        return True

    def __cmp__(self, b):
        return cmp((self.origin, self.size), (b.origin, b.size))


    # --- Chunk positions ---

    @property
    def mincx(self):
        "The smallest chunk position contained in this box"
        return self.origin.x >> 4

    @property
    def mincz(self):
        "The smallest chunk position contained in this box"
        return self.origin.z >> 4

    @property
    def maxcx(self):
        "The largest chunk position contained in this box"
        return ((self.origin.x + self.size.x - 1) >> 4) + 1

    @property
    def maxcz(self):
        "The largest chunk position contained in this box"
        return ((self.origin.z + self.size.z - 1) >> 4) + 1

    def chunkBox(self, level):
        """Returns this box extended to the chunk boundaries of the given level"""
        box = self
        return BoundingBox((box.mincx << 4, 0, box.mincz << 4),
                           (box.maxcx - box.mincx << 4, level.Height, box.maxcz - box.mincz << 4))

    @property
    def chunkPositions(self):
        #iterate through all of the chunk positions within this selection box
        return itertools.product(xrange(self.mincx, self.maxcx), xrange(self.mincz, self.maxcz))

    @property
    def chunkCount(self):
        return (self.maxcx - self.mincx) * (self.maxcz - self.mincz)

    @property
    def isChunkAligned(self):
        return (self.origin.x & 0xf == 0) and (self.origin.z & 0xf == 0)

class FloatBox (BoundingBox):
    type = float

########NEW FILE########
__FILENAME__ = cachefunc
# From http://code.activestate.com/recipes/498245/
import collections
import functools
from itertools import ifilterfalse
from heapq import nsmallest
from operator import itemgetter


class Counter(dict):
    'Mapping where default values are zero'

    def __missing__(self, key):
        return 0


def lru_cache(maxsize=100):
    '''Least-recently-used cache decorator.

    Arguments to the cached function must be hashable.
    Cache performance statistics stored in f.hits and f.misses.
    Clear the cache with f.clear().
    http://en.wikipedia.org/wiki/Cache_algorithms#Least_Recently_Used

    '''
    maxqueue = maxsize * 10

    def decorating_function(user_function,
            len=len, iter=iter, tuple=tuple, sorted=sorted, KeyError=KeyError):
        cache = {}                   # mapping of args to results
        queue = collections.deque()  # order that keys have been used
        refcount = Counter()         # times each key is in the queue
        sentinel = object()          # marker for looping around the queue
        kwd_mark = object()          # separate positional and keyword args

        # lookup optimizations (ugly but fast)
        queue_append, queue_popleft = queue.append, queue.popleft
        queue_appendleft, queue_pop = queue.appendleft, queue.pop

        @functools.wraps(user_function)
        def wrapper(*args, **kwds):
            # cache key records both positional and keyword args
            key = args
            if kwds:
                key += (kwd_mark,) + tuple(sorted(kwds.items()))

            # record recent use of this key
            queue_append(key)
            refcount[key] += 1

            # get cache entry or compute if not found
            try:
                result = cache[key]
                wrapper.hits += 1
            except KeyError:
                result = user_function(*args, **kwds)
                cache[key] = result
                wrapper.misses += 1

                # purge least recently used cache entry
                if len(cache) > maxsize:
                    key = queue_popleft()
                    refcount[key] -= 1
                    while refcount[key]:
                        key = queue_popleft()
                        refcount[key] -= 1
                    del cache[key], refcount[key]

            # periodically compact the queue by eliminating duplicate keys
            # while preserving order of most recent access
            if len(queue) > maxqueue:
                refcount.clear()
                queue_appendleft(sentinel)
                for key in ifilterfalse(refcount.__contains__,
                                        iter(queue_pop, sentinel)):
                    queue_appendleft(key)
                    refcount[key] = 1

            return result

        def clear():
            cache.clear()
            queue.clear()
            refcount.clear()
            wrapper.hits = wrapper.misses = 0

        wrapper.hits = wrapper.misses = 0
        wrapper.clear = clear
        return wrapper
    return decorating_function


def lfu_cache(maxsize=100):
    '''Least-frequenty-used cache decorator.

    Arguments to the cached function must be hashable.
    Cache performance statistics stored in f.hits and f.misses.
    Clear the cache with f.clear().
    http://en.wikipedia.org/wiki/Least_Frequently_Used

    '''

    def decorating_function(user_function):
        cache = {}                      # mapping of args to results
        use_count = Counter()           # times each key has been accessed
        kwd_mark = object()             # separate positional and keyword args

        @functools.wraps(user_function)
        def wrapper(*args, **kwds):
            key = args
            if kwds:
                key += (kwd_mark,) + tuple(sorted(kwds.items()))
            use_count[key] += 1

            # get cache entry or compute if not found
            try:
                result = cache[key]
                wrapper.hits += 1
            except KeyError:
                result = user_function(*args, **kwds)
                cache[key] = result
                wrapper.misses += 1

                # purge least frequently used cache entry
                if len(cache) > maxsize:
                    for key, _ in nsmallest(maxsize // 10,
                                            use_count.iteritems(),
                                            key=itemgetter(1)):
                        del cache[key], use_count[key]

            return result

        def clear():
            cache.clear()
            use_count.clear()
            wrapper.hits = wrapper.misses = 0

        wrapper.hits = wrapper.misses = 0
        wrapper.clear = clear
        return wrapper
    return decorating_function

if __name__ == '__main__':

    @lru_cache(maxsize=20)
    def f_lru(x, y):
        return 3 * x + y

    domain = range(5)
    from random import choice
    for i in range(1000):
        r = f_lru(choice(domain), choice(domain))

    print(f_lru.hits, f_lru.misses)

    @lfu_cache(maxsize=20)
    def f_lfu(x, y):
        return 3 * x + y

    domain = range(5)
    from random import choice
    for i in range(1000):
        r = f_lfu(choice(domain), choice(domain))

    print(f_lfu.hits, f_lfu.misses)

########NEW FILE########
__FILENAME__ = entity
'''
Created on Jul 23, 2011

@author: Rio
'''
from math import isnan

import nbt
from copy import deepcopy

__all__ = ["Entity", "TileEntity"]

class TileEntity(object):
    baseStructures = {
        "Furnace": (
            ("BurnTime", nbt.TAG_Short),
            ("CookTime", nbt.TAG_Short),
            ("Items", nbt.TAG_List),
        ),
        "Sign": (
            ("Items", nbt.TAG_List),
        ),
        "MobSpawner": (
            ("Items", nbt.TAG_List),
        ),
        "Chest": (
            ("Items", nbt.TAG_List),
        ),
        "Music": (
            ("note", nbt.TAG_Byte),
        ),
        "Trap": (
            ("Items", nbt.TAG_List),
        ),
        "RecordPlayer": (
            ("Record", nbt.TAG_Int),
        ),
        "Piston": (
            ("blockId", nbt.TAG_Int),
            ("blockData", nbt.TAG_Int),
            ("facing", nbt.TAG_Int),
            ("progress", nbt.TAG_Float),
            ("extending", nbt.TAG_Byte),
        ),
        "Cauldron": (
            ("Items", nbt.TAG_List),
            ("BrewTime", nbt.TAG_Int),
        ),
    }

    knownIDs = baseStructures.keys()
    maxItems = {
        "Furnace": 3,
        "Chest": 27,
        "Trap": 9,
        "Cauldron": 4,
    }
    slotNames = {
        "Furnace": {
            0: "Raw",
            1: "Fuel",
            2: "Product"
        },
        "Cauldron": {
            0: "Potion",
            1: "Potion",
            2: "Potion",
            3: "Reagent",
        }
    }

    @classmethod
    def Create(cls, tileEntityID, **kw):
        tileEntityTag = nbt.TAG_Compound()
        tileEntityTag["id"] = nbt.TAG_String(tileEntityID)
        base = cls.baseStructures.get(tileEntityID, None)
        if base:
            for (name, tag) in base:
                tileEntityTag[name] = tag()

        cls.setpos(tileEntityTag, (0, 0, 0))
        return tileEntityTag

    @classmethod
    def pos(cls, tag):
        return [tag[a].value for a in 'xyz']

    @classmethod
    def setpos(cls, tag, pos):
        for a, p in zip('xyz', pos):
            tag[a] = nbt.TAG_Int(p)

    @classmethod
    def copyWithOffset(cls, tileEntity, copyOffset):
        eTag = deepcopy(tileEntity)
        eTag['x'] = nbt.TAG_Int(tileEntity['x'].value + copyOffset[0])
        eTag['y'] = nbt.TAG_Int(tileEntity['y'].value + copyOffset[1])
        eTag['z'] = nbt.TAG_Int(tileEntity['z'].value + copyOffset[2])
        return eTag


class Entity(object):
    monsters = ["Creeper",
                "Skeleton",
                "Spider",
                "CaveSpider",
                "Giant",
                "Zombie",
                "Slime",
                "PigZombie",
                "Ghast",
                "Pig",
                "Sheep",
                "Cow",
                "Chicken",
                "Squid",
                "Wolf",
                "Monster",
                "Enderman",
                "Silverfish",
                "Blaze",
                "Villager",
                "LavaSlime",
                "WitherBoss",
                ]
    projectiles = ["Arrow",
                   "Snowball",
                   "Egg",
                   "Fireball",
                   "SmallFireball",
                   "ThrownEnderpearl",
                   ]

    items = ["Item",
             "XPOrb",
             "Painting",
             "EnderCrystal",
             "ItemFrame",
             "WitherSkull",
             ]
    vehicles = ["Minecart", "Boat"]
    tiles = ["PrimedTnt", "FallingSand"]

    @classmethod
    def Create(cls, entityID, **kw):
        entityTag = nbt.TAG_Compound()
        entityTag["id"] = nbt.TAG_String(entityID)
        Entity.setpos(entityTag, (0, 0, 0))
        return entityTag

    @classmethod
    def pos(cls, tag):
        if "Pos" not in tag:
            raise InvalidEntity(tag)
        values = [a.value for a in tag["Pos"]]

        if isnan(values[0]) and 'xTile' in tag :
            values[0] = tag['xTile'].value
        if isnan(values[1]) and 'yTile' in tag:
            values[1] = tag['yTile'].value
        if isnan(values[2]) and 'zTile' in tag:
            values[2] = tag['zTile'].value

        return values

    @classmethod
    def setpos(cls, tag, pos):
        tag["Pos"] = nbt.TAG_List([nbt.TAG_Double(p) for p in pos])

    @classmethod
    def copyWithOffset(cls, entity, copyOffset):
        eTag = deepcopy(entity)

        positionTags = map(lambda p, co: nbt.TAG_Double(p.value + co), eTag["Pos"], copyOffset)
        eTag["Pos"] = nbt.TAG_List(positionTags)

        if eTag["id"].value in ("Painting", "ItemFrame"):
            eTag["TileX"].value += copyOffset[0]
            eTag["TileY"].value += copyOffset[1]
            eTag["TileZ"].value += copyOffset[2]

        return eTag


class InvalidEntity(ValueError):
    pass


class InvalidTileEntity(ValueError):
    pass

########NEW FILE########
__FILENAME__ = faces

FaceXIncreasing = 0
FaceXDecreasing = 1
FaceYIncreasing = 2
FaceYDecreasing = 3
FaceZIncreasing = 4
FaceZDecreasing = 5
MaxDirections = 6

faceDirections = (
                            (FaceXIncreasing, (1, 0, 0)),
                            (FaceXDecreasing, (-1, 0, 0)),
                            (FaceYIncreasing, (0, 1, 0)),
                            (FaceYDecreasing, (0, -1, 0)),
                            (FaceZIncreasing, (0, 0, 1)),
                            (FaceZDecreasing, (0, 0, -1))
                            )

########NEW FILE########
__FILENAME__ = indev
"""
Created on Jul 22, 2011

@author: Rio

Indev levels:

TAG_Compound "MinecraftLevel"
{
   TAG_Compound "Environment"
   {
      TAG_Short "SurroundingGroundHeight"// Height of surrounding ground (in blocks)
      TAG_Byte "SurroundingGroundType"   // Block ID of surrounding ground
      TAG_Short "SurroundingWaterHeight" // Height of surrounding water (in blocks)
      TAG_Byte "SurroundingWaterType"    // Block ID of surrounding water
      TAG_Short "CloudHeight"            // Height of the cloud layer (in blocks)
      TAG_Int "CloudColor"               // Hexadecimal value for the color of the clouds
      TAG_Int "SkyColor"                 // Hexadecimal value for the color of the sky
      TAG_Int "FogColor"                 // Hexadecimal value for the color of the fog
      TAG_Byte "SkyBrightness"           // The brightness of the sky, from 0 to 100
   }

   TAG_List "Entities"
   {
      TAG_Compound
      {
         // One of these per entity on the map.
         // These can change a lot, and are undocumented.
         // Feel free to play around with them, though.
         // The most interesting one might be the one with ID "LocalPlayer", which contains the player inventory
      }
   }

   TAG_Compound "Map"
   {
      // To access a specific block from either byte array, use the following algorithm:
      // Index = x + (y * Depth + z) * Width

      TAG_Short "Width"                  // Width of the level (along X)
      TAG_Short "Height"                 // Height of the level (along Y)
      TAG_Short "Length"                 // Length of the level (along Z)
      TAG_Byte_Array "Blocks"             // An array of Length*Height*Width bytes specifying the block types
      TAG_Byte_Array "Data"              // An array of Length*Height*Width bytes with data for each blocks

      TAG_List "Spawn"                   // Default spawn position
      {
         TAG_Short x  // These values are multiplied by 32 before being saved
         TAG_Short y  // That means that the actual values are x/32.0, y/32.0, z/32.0
         TAG_Short z
      }
   }

   TAG_Compound "About"
   {
      TAG_String "Name"                  // Level name
      TAG_String "Author"                // Name of the player who made the level
      TAG_Long "CreatedOn"               // Timestamp when the level was first created
   }
}
"""

from entity import TileEntity
from level import MCLevel
from logging import getLogger
from materials import indevMaterials
from numpy import array, swapaxes
import nbt
import os

log = getLogger(__name__)

MinecraftLevel = "MinecraftLevel"

Environment = "Environment"
SurroundingGroundHeight = "SurroundingGroundHeight"
SurroundingGroundType = "SurroundingGroundType"
SurroundingWaterHeight = "SurroundingWaterHeight"
SurroundingWaterType = "SurroundingWaterType"
CloudHeight = "CloudHeight"
CloudColor = "CloudColor"
SkyColor = "SkyColor"
FogColor = "FogColor"
SkyBrightness = "SkyBrightness"

About = "About"
Name = "Name"
Author = "Author"
CreatedOn = "CreatedOn"
Spawn = "Spawn"

__all__ = ["MCIndevLevel"]

from level import EntityLevel


class MCIndevLevel(EntityLevel):
    """ IMPORTANT: self.Blocks and self.Data are indexed with [x,z,y] via axis
    swapping to be consistent with infinite levels."""

    materials = indevMaterials

    def setPlayerSpawnPosition(self, pos, player=None):
        assert len(pos) == 3
        self.Spawn = array(pos)

    def playerSpawnPosition(self, player=None):
        return self.Spawn

    def setPlayerPosition(self, pos, player="Ignored"):
        self.LocalPlayer["Pos"] = nbt.TAG_List([nbt.TAG_Float(p) for p in pos])

    def getPlayerPosition(self, player="Ignored"):
        return array(map(lambda x: x.value, self.LocalPlayer["Pos"]))

    def setPlayerOrientation(self, yp, player="Ignored"):
        self.LocalPlayer["Rotation"] = nbt.TAG_List([nbt.TAG_Float(p) for p in yp])

    def getPlayerOrientation(self, player="Ignored"):
        """ returns (yaw, pitch) """
        return array(map(lambda x: x.value, self.LocalPlayer["Rotation"]))

    def setBlockDataAt(self, x, y, z, newdata):
        if x < 0 or y < 0 or z < 0:
            return 0
        if x >= self.Width or y >= self.Height or z >= self.Length:
            return 0
        self.Data[x, z, y] = (newdata & 0xf)

    def blockDataAt(self, x, y, z):
        if x < 0 or y < 0 or z < 0:
            return 0
        if x >= self.Width or y >= self.Height or z >= self.Length:
            return 0
        return self.Data[x, z, y]

    def blockLightAt(self, x, y, z):
        if x < 0 or y < 0 or z < 0:
            return 0
        if x >= self.Width or y >= self.Height or z >= self.Length:
            return 0
        return self.BlockLight[x, z, y]

    def __repr__(self):
        return u"MCIndevLevel({0}): {1}W {2}L {3}H".format(self.filename, self.Width, self.Length, self.Height)

    @classmethod
    def _isTagLevel(cls, root_tag):
        return "MinecraftLevel" == root_tag.name

    def __init__(self, root_tag=None, filename=""):
        self.Width = 0
        self.Height = 0
        self.Length = 0
        self.Blocks = array([], "uint8")
        self.Data = array([], "uint8")
        self.Spawn = (0, 0, 0)
        self.filename = filename

        if root_tag:

            self.root_tag = root_tag
            mapTag = root_tag["Map"]
            self.Width = mapTag["Width"].value
            self.Length = mapTag["Length"].value
            self.Height = mapTag["Height"].value

            mapTag["Blocks"].value.shape = (self.Height, self.Length, self.Width)

            self.Blocks = swapaxes(mapTag["Blocks"].value, 0, 2)

            mapTag["Data"].value.shape = (self.Height, self.Length, self.Width)

            self.Data = swapaxes(mapTag["Data"].value, 0, 2)

            self.BlockLight = self.Data & 0xf

            self.Data >>= 4

            self.Spawn = [mapTag[Spawn][i].value for i in range(3)]

            if "Entities" not in root_tag:
                root_tag["Entities"] = nbt.TAG_List()
            self.Entities = root_tag["Entities"]

            # xxx fixup Motion and Pos to match infdev format
            def numbersToDoubles(ent):
                for attr in "Motion", "Pos":
                    if attr in ent:
                        ent[attr] = nbt.TAG_List([nbt.TAG_Double(t.value) for t in ent[attr]])
            for ent in self.Entities:
                numbersToDoubles(ent)

            if "TileEntities" not in root_tag:
                root_tag["TileEntities"] = nbt.TAG_List()
            self.TileEntities = root_tag["TileEntities"]
            # xxx fixup TileEntities positions to match infdev format
            for te in self.TileEntities:
                pos = te["Pos"].value

                (x, y, z) = self.decodePos(pos)

                TileEntity.setpos(te, (x, y, z))


            localPlayerList = [tag for tag in root_tag["Entities"] if tag['id'].value == 'LocalPlayer']
            if len(localPlayerList) == 0:  # omen doesn't make a player entity
                playerTag = nbt.TAG_Compound()
                playerTag['id'] = nbt.TAG_String('LocalPlayer')
                playerTag['Pos'] = nbt.TAG_List([nbt.TAG_Float(0.), nbt.TAG_Float(64.), nbt.TAG_Float(0.)])
                playerTag['Rotation'] = nbt.TAG_List([nbt.TAG_Float(0.), nbt.TAG_Float(45.)])
                self.LocalPlayer = playerTag

            else:
                self.LocalPlayer = localPlayerList[0]

        else:
            log.info(u"Creating new Indev levels is not yet implemented.!")
            raise ValueError("Can't do that yet")
#            self.SurroundingGroundHeight = root_tag[Environment][SurroundingGroundHeight].value
#            self.SurroundingGroundType = root_tag[Environment][SurroundingGroundType].value
#            self.SurroundingWaterHeight = root_tag[Environment][SurroundingGroundHeight].value
#            self.SurroundingWaterType = root_tag[Environment][SurroundingWaterType].value
#            self.CloudHeight = root_tag[Environment][CloudHeight].value
#            self.CloudColor = root_tag[Environment][CloudColor].value
#            self.SkyColor = root_tag[Environment][SkyColor].value
#            self.FogColor = root_tag[Environment][FogColor].value
#            self.SkyBrightness = root_tag[Environment][SkyBrightness].value
#            self.TimeOfDay = root_tag[Environment]["TimeOfDay"].value
#
#
#            self.Name = self.root_tag[About][Name].value
#            self.Author = self.root_tag[About][Author].value
#            self.CreatedOn = self.root_tag[About][CreatedOn].value

    def rotateLeft(self):
        MCLevel.rotateLeft(self)

        self.Data = swapaxes(self.Data, 1, 0)[:, ::-1, :]  # x=y; y=-x

        torchRotation = array([0, 4, 3, 1, 2, 5,
                               6, 7,

                               8, 9, 10, 11, 12, 13, 14, 15])

        torchIndexes = (self.Blocks == self.materials.Torch.ID)
        log.info(u"Rotating torches: {0}".format(len(torchIndexes.nonzero()[0])))
        self.Data[torchIndexes] = torchRotation[self.Data[torchIndexes]]

    def decodePos(self, v):
        b = 10
        m = (1 << b) - 1
        return v & m, (v >> b) & m, (v >> (2 * b))

    def encodePos(self, x, y, z):
        b = 10
        return x + (y << b) + (z << (2 * b))

    def saveToFile(self, filename=None):
        if filename is None:
            filename = self.filename
        if filename is None:
            log.warn(u"Attempted to save an unnamed file in place")
            return  # you fool!

        self.Data <<= 4
        self.Data |= (self.BlockLight & 0xf)

        self.Blocks = swapaxes(self.Blocks, 0, 2)
        self.Data = swapaxes(self.Data, 0, 2)

        mapTag = nbt.TAG_Compound()
        mapTag["Width"] = nbt.TAG_Short(self.Width)
        mapTag["Height"] = nbt.TAG_Short(self.Height)
        mapTag["Length"] = nbt.TAG_Short(self.Length)
        mapTag["Blocks"] = nbt.TAG_Byte_Array(self.Blocks)
        mapTag["Data"] = nbt.TAG_Byte_Array(self.Data)

        self.Blocks = swapaxes(self.Blocks, 0, 2)
        self.Data = swapaxes(self.Data, 0, 2)

        mapTag[Spawn] = nbt.TAG_List([nbt.TAG_Short(i) for i in self.Spawn])

        self.root_tag["Map"] = mapTag

        self.Entities.append(self.LocalPlayer)
        # fix up Entities imported from Alpha worlds
        def numbersToFloats(ent):
            for attr in "Motion", "Pos":
                if attr in ent:
                    ent[attr] = nbt.TAG_List([nbt.TAG_Double(t.value) for t in ent[attr]])
        for ent in self.Entities:
            numbersToFloats(ent)

        # fix up TileEntities imported from Alpha worlds.
        for ent in self.TileEntities:
            if "Pos" not in ent and all(c in ent for c in 'xyz'):
                ent["Pos"] = nbt.TAG_Int(self.encodePos(ent['x'].value, ent['y'].value, ent['z'].value))
        # output_file = gzip.open(self.filename, "wb", compresslevel=1)
        try:
            os.rename(filename, filename + ".old")
        except Exception:
            pass

        try:
            self.root_tag.save(filename)
        except:
            os.rename(filename + ".old", filename)

        try:
            os.remove(filename + ".old")
        except Exception:
            pass

        self.Entities.remove(self.LocalPlayer)

        self.BlockLight = self.Data & 0xf

        self.Data >>= 4

########NEW FILE########
__FILENAME__ = infiniteworld
'''
Created on Jul 22, 2011

@author: Rio
'''

import copy
from datetime import datetime
import itertools
from logging import getLogger
from math import floor
import os
import re
import random
import shutil
import struct
import time
import traceback
import weakref
import zlib
import sys

import blockrotation
from box import BoundingBox
from entity import Entity, TileEntity
from faces import FaceXDecreasing, FaceXIncreasing, FaceZDecreasing, FaceZIncreasing
from level import LightedChunk, EntityLevel, computeChunkHeightMap, MCLevel, ChunkBase
from materials import alphaMaterials
from mclevelbase import ChunkMalformed, ChunkNotPresent, exhaust, PlayerNotFound
import nbt
from numpy import array, clip, maximum, zeros
from regionfile import MCRegionFile

log = getLogger(__name__)


DIM_NETHER = -1
DIM_END = 1

__all__ = ["ZeroChunk", "AnvilChunk", "ChunkedLevelMixin", "MCInfdevOldLevel", "MCAlphaDimension", "ZipSchematic"]
_zeros = {}

class SessionLockLost(IOError):
    pass



def ZeroChunk(height=512):
    z = _zeros.get(height)
    if z is None:
        z = _zeros[height] = _ZeroChunk(height)
    return z


class _ZeroChunk(ChunkBase):
    " a placebo for neighboring-chunk routines "

    def __init__(self, height=512):
        zeroChunk = zeros((16, 16, height), 'uint8')
        whiteLight = zeroChunk + 15
        self.Blocks = zeroChunk
        self.BlockLight = whiteLight
        self.SkyLight = whiteLight
        self.Data = zeroChunk


def unpackNibbleArray(dataArray):
    s = dataArray.shape
    unpackedData = zeros((s[0], s[1], s[2] * 2), dtype='uint8')

    unpackedData[:, :, ::2] = dataArray
    unpackedData[:, :, ::2] &= 0xf
    unpackedData[:, :, 1::2] = dataArray
    unpackedData[:, :, 1::2] >>= 4
    return unpackedData


def packNibbleArray(unpackedData):
    packedData = array(unpackedData.reshape(16, 16, unpackedData.shape[2] / 2, 2))
    packedData[..., 1] <<= 4
    packedData[..., 1] |= packedData[..., 0]
    return array(packedData[:, :, :, 1])

def sanitizeBlocks(chunk):
    # change grass to dirt where needed so Minecraft doesn't flip out and die
    grass = chunk.Blocks == chunk.materials.Grass.ID
    grass |= chunk.Blocks == chunk.materials.Dirt.ID
    badgrass = grass[:, :, 1:] & grass[:, :, :-1]

    chunk.Blocks[:, :, :-1][badgrass] = chunk.materials.Dirt.ID

    # remove any thin snow layers immediately above other thin snow layers.
    # minecraft doesn't flip out, but it's almost never intended
    if hasattr(chunk.materials, "SnowLayer"):
        snowlayer = chunk.Blocks == chunk.materials.SnowLayer.ID
        badsnow = snowlayer[:, :, 1:] & snowlayer[:, :, :-1]

        chunk.Blocks[:, :, 1:][badsnow] = chunk.materials.Air.ID


class AnvilChunkData(object):
    """ This is the chunk data backing an AnvilChunk. Chunk data is retained by the MCInfdevOldLevel until its
    AnvilChunk is no longer used, then it is either cached in memory, discarded, or written to disk according to
    resource limits.

    AnvilChunks are stored in a WeakValueDictionary so we can find out when they are no longer used by clients. The
    AnvilChunkData for an unused chunk may safely be discarded or written out to disk. The client should probably
     not keep references to a whole lot of chunks or else it will run out of memory.
    """
    def __init__(self, world, chunkPosition, root_tag = None, create = False):
        self.chunkPosition = chunkPosition
        self.world = world
        self.root_tag = root_tag
        self.dirty = False

        self.Blocks = zeros((16, 16, world.Height), 'uint8')  # xxx uint16?
        self.Data = zeros((16, 16, world.Height), 'uint8')
        self.BlockLight = zeros((16, 16, world.Height), 'uint8')
        self.SkyLight = zeros((16, 16, world.Height), 'uint8')
        self.SkyLight[:] = 15


        if create:
            self._create()
        else:
            self._load(root_tag)

    def _create(self):
        (cx, cz) = self.chunkPosition
        chunkTag = nbt.TAG_Compound()
        chunkTag.name = ""

        levelTag = nbt.TAG_Compound()
        chunkTag["Level"] = levelTag

        levelTag["HeightMap"] = nbt.TAG_Int_Array(zeros((16, 16), 'uint32').newbyteorder())
        levelTag["TerrainPopulated"] = nbt.TAG_Byte(1)
        levelTag["xPos"] = nbt.TAG_Int(cx)
        levelTag["zPos"] = nbt.TAG_Int(cz)

        levelTag["LastUpdate"] = nbt.TAG_Long(0)

        levelTag["Entities"] = nbt.TAG_List()
        levelTag["TileEntities"] = nbt.TAG_List()

        self.root_tag = chunkTag

        self.dirty = True

    def _load(self, root_tag):
        self.root_tag = root_tag

        for sec in self.root_tag["Level"].pop("Sections", []):
            y = sec["Y"].value * 16
            for name in "Blocks", "Data", "SkyLight", "BlockLight":
                arr = getattr(self, name)
                secarray = sec[name].value
                if name == "Blocks":
                    secarray.shape = (16, 16, 16)
                else:
                    secarray.shape = (16, 16, 8)
                    secarray = unpackNibbleArray(secarray)

                arr[..., y:y + 16] = secarray.swapaxes(0, 2)


    def savedTagData(self):
        """ does not recalculate any data or light """

        log.debug(u"Saving chunk: {0}".format(self))
        sanitizeBlocks(self)

        sections = nbt.TAG_List()
        for y in range(0, self.world.Height, 16):
            section = nbt.TAG_Compound()

            Blocks = self.Blocks[..., y:y + 16].swapaxes(0, 2)
            Data = self.Data[..., y:y + 16].swapaxes(0, 2)
            BlockLight = self.BlockLight[..., y:y + 16].swapaxes(0, 2)
            SkyLight = self.SkyLight[..., y:y + 16].swapaxes(0, 2)

            if (not Blocks.any() and
                not BlockLight.any() and
                (SkyLight == 15).all()):
                continue

            Data = packNibbleArray(Data)
            BlockLight = packNibbleArray(BlockLight)
            SkyLight = packNibbleArray(SkyLight)

            section['Blocks'] = nbt.TAG_Byte_Array(array(Blocks))
            section['Data'] = nbt.TAG_Byte_Array(array(Data))
            section['BlockLight'] = nbt.TAG_Byte_Array(array(BlockLight))
            section['SkyLight'] = nbt.TAG_Byte_Array(array(SkyLight))

            section["Y"] = nbt.TAG_Byte(y / 16)
            sections.append(section)

        self.root_tag["Level"]["Sections"] = sections
        data = self.root_tag.save(compressed=False)
        del self.root_tag["Level"]["Sections"]

        log.debug(u"Saved chunk {0}".format(self))
        return data

    @property
    def materials(self):
        return self.world.materials


class AnvilChunk(LightedChunk):
    """ This is a 16x16xH chunk in an (infinite) world.
    The properties Blocks, Data, SkyLight, BlockLight, and Heightmap
    are ndarrays containing the respective blocks in the chunk file.
    Each array is indexed [x,z,y].  The Data, Skylight, and BlockLight
    arrays are automatically unpacked from nibble arrays into byte arrays
    for better handling.
    """

    def __init__(self, chunkData):
        self.world = chunkData.world
        self.chunkPosition = chunkData.chunkPosition
        self.chunkData = chunkData


    def savedTagData(self):
        return self.chunkData.savedTagData()


    def __str__(self):
        return u"AnvilChunk, coords:{0}, world: {1}, D:{2}, L:{3}".format(self.chunkPosition, self.world.displayName, self.dirty, self.needsLighting)

    @property
    def needsLighting(self):
        return self.chunkPosition in self.world.chunksNeedingLighting

    @needsLighting.setter
    def needsLighting(self, value):
        if value:
            self.world.chunksNeedingLighting.add(self.chunkPosition)
        else:
            self.world.chunksNeedingLighting.discard(self.chunkPosition)

    def generateHeightMap(self):
        if self.world.dimNo == DIM_NETHER:
            self.HeightMap[:] = 0
        else:
            computeChunkHeightMap(self.materials, self.Blocks, self.HeightMap)

    def addEntity(self, entityTag):

        def doubleize(name):
            # This is needed for compatibility with Indev levels. Those levels use TAG_Float for entity motion and pos
            if name in entityTag:
                m = entityTag[name]
                entityTag[name] = nbt.TAG_List([nbt.TAG_Double(i.value) for i in m])

        doubleize("Motion")
        doubleize("Position")

        self.dirty = True
        return super(AnvilChunk, self).addEntity(entityTag)

    def removeEntitiesInBox(self, box):
        self.dirty = True
        return super(AnvilChunk, self).removeEntitiesInBox(box)

    def removeTileEntitiesInBox(self, box):
        self.dirty = True
        return super(AnvilChunk, self).removeTileEntitiesInBox(box)

    # --- AnvilChunkData accessors ---

    @property
    def root_tag(self):
        return self.chunkData.root_tag

    @property
    def dirty(self):
        return self.chunkData.dirty

    @dirty.setter
    def dirty(self, val):
        self.chunkData.dirty = val

    # --- Chunk attributes ---

    @property
    def materials(self):
        return self.world.materials

    @property
    def Blocks(self):
        return self.chunkData.Blocks

    @property
    def Data(self):
        return self.chunkData.Data

    @property
    def SkyLight(self):
        return self.chunkData.SkyLight

    @property
    def BlockLight(self):
        return self.chunkData.BlockLight

    @property
    def Biomes(self):
        return self.root_tag["Level"]["Biomes"].value.reshape((16, 16))

    @property
    def HeightMap(self):
        return self.root_tag["Level"]["HeightMap"].value.reshape((16, 16))

    @property
    def Entities(self):
        return self.root_tag["Level"]["Entities"]

    @property
    def TileEntities(self):
        return self.root_tag["Level"]["TileEntities"]

    @property
    def TerrainPopulated(self):
        return self.root_tag["Level"]["TerrainPopulated"].value

    @TerrainPopulated.setter
    def TerrainPopulated(self, val):
        """True or False. If False, the game will populate the chunk with
        ores and vegetation on next load"""
        self.root_tag["Level"]["TerrainPopulated"].value = val
        self.dirty = True


base36alphabet = "0123456789abcdefghijklmnopqrstuvwxyz"


def decbase36(s):
    return int(s, 36)


def base36(n):
    global base36alphabet

    n = int(n)
    if 0 == n:
        return '0'
    neg = ""
    if n < 0:
        neg = "-"
        n = -n

    work = []

    while n:
        n, digit = divmod(n, 36)
        work.append(base36alphabet[digit])

    return neg + ''.join(reversed(work))


def deflate(data):
    # zobj = zlib.compressobj(6,zlib.DEFLATED,-zlib.MAX_WBITS,zlib.DEF_MEM_LEVEL,0)
    # zdata = zobj.compress(data)
    # zdata += zobj.flush()
    # return zdata
    return zlib.compress(data)


def inflate(data):
    return zlib.decompress(data)


class ChunkedLevelMixin(MCLevel):
    def blockLightAt(self, x, y, z):
        if y < 0 or y >= self.Height:
            return 0
        zc = z >> 4
        xc = x >> 4

        xInChunk = x & 0xf
        zInChunk = z & 0xf
        ch = self.getChunk(xc, zc)

        return ch.BlockLight[xInChunk, zInChunk, y]

    def setBlockLightAt(self, x, y, z, newLight):
        if y < 0 or y >= self.Height:
            return 0
        zc = z >> 4
        xc = x >> 4

        xInChunk = x & 0xf
        zInChunk = z & 0xf

        ch = self.getChunk(xc, zc)
        ch.BlockLight[xInChunk, zInChunk, y] = newLight
        ch.chunkChanged(False)

    def blockDataAt(self, x, y, z):
        if y < 0 or y >= self.Height:
            return 0
        zc = z >> 4
        xc = x >> 4

        xInChunk = x & 0xf
        zInChunk = z & 0xf

        try:
            ch = self.getChunk(xc, zc)
        except ChunkNotPresent:
            return 0

        return ch.Data[xInChunk, zInChunk, y]

    def setBlockDataAt(self, x, y, z, newdata):
        if y < 0 or y >= self.Height:
            return 0
        zc = z >> 4
        xc = x >> 4

        xInChunk = x & 0xf
        zInChunk = z & 0xf

        try:
            ch = self.getChunk(xc, zc)
        except ChunkNotPresent:
            return 0

        ch.Data[xInChunk, zInChunk, y] = newdata
        ch.dirty = True
        ch.needsLighting = True

    def blockAt(self, x, y, z):
        """returns 0 for blocks outside the loadable chunks.  automatically loads chunks."""
        if y < 0 or y >= self.Height:
            return 0

        zc = z >> 4
        xc = x >> 4
        xInChunk = x & 0xf
        zInChunk = z & 0xf

        try:
            ch = self.getChunk(xc, zc)
        except ChunkNotPresent:
            return 0

        return ch.Blocks[xInChunk, zInChunk, y]

    def setBlockAt(self, x, y, z, blockID):
        """returns 0 for blocks outside the loadable chunks.  automatically loads chunks."""
        if y < 0 or y >= self.Height:
            return 0

        zc = z >> 4
        xc = x >> 4
        xInChunk = x & 0xf
        zInChunk = z & 0xf

        try:
            ch = self.getChunk(xc, zc)
        except ChunkNotPresent:
            return 0

        ch.Blocks[xInChunk, zInChunk, y] = blockID
        ch.dirty = True
        ch.needsLighting = True

    def skylightAt(self, x, y, z):

        if y < 0 or y >= self.Height:
            return 0
        zc = z >> 4
        xc = x >> 4

        xInChunk = x & 0xf
        zInChunk = z & 0xf

        ch = self.getChunk(xc, zc)

        return ch.SkyLight[xInChunk, zInChunk, y]

    def setSkylightAt(self, x, y, z, lightValue):
        if y < 0 or y >= self.Height:
            return 0
        zc = z >> 4
        xc = x >> 4

        xInChunk = x & 0xf
        zInChunk = z & 0xf

        ch = self.getChunk(xc, zc)
        skyLight = ch.SkyLight

        oldValue = skyLight[xInChunk, zInChunk, y]

        ch.chunkChanged(False)
        if oldValue < lightValue:
            skyLight[xInChunk, zInChunk, y] = lightValue
        return oldValue < lightValue

    createChunk = NotImplemented



    def generateLights(self, dirtyChunkPositions=None):
        return exhaust(self.generateLightsIter(dirtyChunkPositions))

    def generateLightsIter(self, dirtyChunkPositions=None):
        """ dirtyChunks may be an iterable yielding (xPos,zPos) tuples
        if none, generate lights for all chunks that need lighting
        """

        startTime = datetime.now()

        if dirtyChunkPositions is None:
            dirtyChunkPositions = self.chunksNeedingLighting
        else:
            dirtyChunkPositions = (c for c in dirtyChunkPositions if self.containsChunk(*c))

        dirtyChunkPositions = sorted(dirtyChunkPositions)

        maxLightingChunks = getattr(self, 'loadedChunkLimit', 400)

        log.info(u"Asked to light {0} chunks".format(len(dirtyChunkPositions)))
        chunkLists = [dirtyChunkPositions]

        def reverseChunkPosition((cx, cz)):
            return cz, cx

        def splitChunkLists(chunkLists):
            newChunkLists = []
            for l in chunkLists:

                # list is already sorted on x position, so this splits into left and right

                smallX = l[:len(l) / 2]
                bigX = l[len(l) / 2:]

                # sort halves on z position
                smallX = sorted(smallX, key=reverseChunkPosition)
                bigX = sorted(bigX, key=reverseChunkPosition)

                # add quarters to list

                newChunkLists.append(smallX[:len(smallX) / 2])
                newChunkLists.append(smallX[len(smallX) / 2:])

                newChunkLists.append(bigX[:len(bigX) / 2])
                newChunkLists.append(bigX[len(bigX) / 2:])

            return newChunkLists

        while len(chunkLists[0]) > maxLightingChunks:
            chunkLists = splitChunkLists(chunkLists)

        if len(chunkLists) > 1:
            log.info(u"Using {0} batches to conserve memory.".format(len(chunkLists)))
        # batchSize = min(len(a) for a in chunkLists)
        estimatedTotals = [len(a) * 32 for a in chunkLists]
        workDone = 0

        for i, dc in enumerate(chunkLists):
            log.info(u"Batch {0}/{1}".format(i, len(chunkLists)))

            dc = sorted(dc)
            workTotal = sum(estimatedTotals)
            t = 0
            for c, t, p in self._generateLightsIter(dc):

                yield c + workDone, t + workTotal - estimatedTotals[i], p

            estimatedTotals[i] = t
            workDone += t

        timeDelta = datetime.now() - startTime

        if len(dirtyChunkPositions):
            log.info(u"Completed in {0}, {1} per chunk".format(timeDelta, dirtyChunkPositions and timeDelta / len(dirtyChunkPositions) or 0))

        return

    def _generateLightsIter(self, dirtyChunkPositions):
        la = array(self.materials.lightAbsorption)
        clip(la, 1, 15, la)

        dirtyChunks = set(self.getChunk(*cPos) for cPos in dirtyChunkPositions)

        workDone = 0
        workTotal = len(dirtyChunks) * 29

        progressInfo = (u"Lighting {0} chunks".format(len(dirtyChunks)))
        log.info(progressInfo)

        for i, chunk in enumerate(dirtyChunks):

            chunk.chunkChanged()
            yield i, workTotal, progressInfo
            assert chunk.dirty and chunk.needsLighting

        workDone += len(dirtyChunks)
        workTotal = len(dirtyChunks)

        for ch in list(dirtyChunks):
            # relight all blocks in neighboring chunks in case their light source disappeared.
            cx, cz = ch.chunkPosition
            for dx, dz in itertools.product((-1, 0, 1), (-1, 0, 1)):
                try:
                    ch = self.getChunk(cx + dx, cz + dz)
                except (ChunkNotPresent, ChunkMalformed):
                    continue
                dirtyChunks.add(ch)
                ch.dirty = True

        dirtyChunks = sorted(dirtyChunks, key=lambda x: x.chunkPosition)
        workTotal += len(dirtyChunks) * 28

        for i, chunk in enumerate(dirtyChunks):
            chunk.BlockLight[:] = self.materials.lightEmission[chunk.Blocks]
            chunk.dirty = True

        zeroChunk = ZeroChunk(self.Height)
        zeroChunk.BlockLight[:] = 0
        zeroChunk.SkyLight[:] = 0

        startingDirtyChunks = dirtyChunks

        oldLeftEdge = zeros((1, 16, self.Height), 'uint8')
        oldBottomEdge = zeros((16, 1, self.Height), 'uint8')
        oldChunk = zeros((16, 16, self.Height), 'uint8')
        if self.dimNo in (-1, 1):
            lights = ("BlockLight",)
        else:
            lights = ("BlockLight", "SkyLight")
        log.info(u"Dispersing light...")

        def clipLight(light):
            # light arrays are all uint8 by default, so when results go negative
            # they become large instead.  reinterpret as signed int using view()
            # and then clip to range
            light.view('int8').clip(0, 15, light)

        for j, light in enumerate(lights):
            zerochunkLight = getattr(zeroChunk, light)
            newDirtyChunks = list(startingDirtyChunks)

            work = 0

            for i in range(14):
                if len(newDirtyChunks) == 0:
                    workTotal -= len(startingDirtyChunks) * (14 - i)
                    break

                progressInfo = u"{0} Pass {1}: {2} chunks".format(light, i, len(newDirtyChunks))
                log.info(progressInfo)

#                propagate light!
#                for each of the six cardinal directions, figure a new light value for
#                adjoining blocks by reducing this chunk's light by light absorption and fall off.
#                compare this new light value against the old light value and update with the maximum.
#
#                we calculate all chunks one step before moving to the next step, to ensure all gaps at chunk edges are filled.
#                we do an extra cycle because lights sent across edges may lag by one cycle.
#
#                xxx this can be optimized by finding the highest and lowest blocks
#                that changed after one pass, and only calculating changes for that
#                vertical slice on the next pass. newDirtyChunks would have to be a
#                list of (cPos, miny, maxy) tuples or a cPos : (miny, maxy) dict

                newDirtyChunks = set(newDirtyChunks)
                newDirtyChunks.discard(zeroChunk)

                dirtyChunks = sorted(newDirtyChunks, key=lambda x: x.chunkPosition)

                newDirtyChunks = list()

                for chunk in dirtyChunks:
                    (cx, cz) = chunk.chunkPosition
                    neighboringChunks = {}

                    for dir, dx, dz in ((FaceXDecreasing, -1, 0),
                                        (FaceXIncreasing, 1, 0),
                                        (FaceZDecreasing, 0, -1),
                                        (FaceZIncreasing, 0, 1)):
                        try:
                            neighboringChunks[dir] = self.getChunk(cx + dx, cz + dz)
                        except (ChunkNotPresent, ChunkMalformed):
                            neighboringChunks[dir] = zeroChunk
                        neighboringChunks[dir].dirty = True

                    chunkLa = la[chunk.Blocks]
                    chunkLight = getattr(chunk, light)
                    oldChunk[:] = chunkLight[:]

                    ### Spread light toward -X

                    nc = neighboringChunks[FaceXDecreasing]
                    ncLight = getattr(nc, light)
                    oldLeftEdge[:] = ncLight[15:16, :, 0:self.Height]  # save the old left edge

                    # left edge
                    newlight = (chunkLight[0:1, :, :self.Height] - la[nc.Blocks[15:16, :, 0:self.Height]])
                    clipLight(newlight)

                    maximum(ncLight[15:16, :, 0:self.Height], newlight, ncLight[15:16, :, 0:self.Height])

                    # chunk body
                    newlight = (chunkLight[1:16, :, 0:self.Height] - chunkLa[0:15, :, 0:self.Height])
                    clipLight(newlight)

                    maximum(chunkLight[0:15, :, 0:self.Height], newlight, chunkLight[0:15, :, 0:self.Height])

                    # right edge
                    nc = neighboringChunks[FaceXIncreasing]
                    ncLight = getattr(nc, light)

                    newlight = ncLight[0:1, :, :self.Height] - chunkLa[15:16, :, 0:self.Height]
                    clipLight(newlight)

                    maximum(chunkLight[15:16, :, 0:self.Height], newlight, chunkLight[15:16, :, 0:self.Height])

                    ### Spread light toward +X

                    # right edge
                    nc = neighboringChunks[FaceXIncreasing]
                    ncLight = getattr(nc, light)

                    newlight = (chunkLight[15:16, :, 0:self.Height] - la[nc.Blocks[0:1, :, 0:self.Height]])
                    clipLight(newlight)

                    maximum(ncLight[0:1, :, 0:self.Height], newlight, ncLight[0:1, :, 0:self.Height])

                    # chunk body
                    newlight = (chunkLight[0:15, :, 0:self.Height] - chunkLa[1:16, :, 0:self.Height])
                    clipLight(newlight)

                    maximum(chunkLight[1:16, :, 0:self.Height], newlight, chunkLight[1:16, :, 0:self.Height])

                    # left edge
                    nc = neighboringChunks[FaceXDecreasing]
                    ncLight = getattr(nc, light)

                    newlight = ncLight[15:16, :, :self.Height] - chunkLa[0:1, :, 0:self.Height]
                    clipLight(newlight)

                    maximum(chunkLight[0:1, :, 0:self.Height], newlight, chunkLight[0:1, :, 0:self.Height])

                    zerochunkLight[:] = 0  # zero the zero chunk after each direction
                    # so the lights it absorbed don't affect the next pass

                    # check if the left edge changed and dirty or compress the chunk appropriately
                    if (oldLeftEdge != ncLight[15:16, :, :self.Height]).any():
                        # chunk is dirty
                        newDirtyChunks.append(nc)

                    ### Spread light toward -Z

                    # bottom edge
                    nc = neighboringChunks[FaceZDecreasing]
                    ncLight = getattr(nc, light)
                    oldBottomEdge[:] = ncLight[:, 15:16, :self.Height]  # save the old bottom edge

                    newlight = (chunkLight[:, 0:1, :self.Height] - la[nc.Blocks[:, 15:16, :self.Height]])
                    clipLight(newlight)

                    maximum(ncLight[:, 15:16, :self.Height], newlight, ncLight[:, 15:16, :self.Height])

                    # chunk body
                    newlight = (chunkLight[:, 1:16, :self.Height] - chunkLa[:, 0:15, :self.Height])
                    clipLight(newlight)

                    maximum(chunkLight[:, 0:15, :self.Height], newlight, chunkLight[:, 0:15, :self.Height])

                    # top edge
                    nc = neighboringChunks[FaceZIncreasing]
                    ncLight = getattr(nc, light)

                    newlight = ncLight[:, 0:1, :self.Height] - chunkLa[:, 15:16, 0:self.Height]
                    clipLight(newlight)

                    maximum(chunkLight[:, 15:16, 0:self.Height], newlight, chunkLight[:, 15:16, 0:self.Height])

                    ### Spread light toward +Z

                    # top edge
                    nc = neighboringChunks[FaceZIncreasing]

                    ncLight = getattr(nc, light)

                    newlight = (chunkLight[:, 15:16, :self.Height] - la[nc.Blocks[:, 0:1, :self.Height]])
                    clipLight(newlight)

                    maximum(ncLight[:, 0:1, :self.Height], newlight, ncLight[:, 0:1, :self.Height])

                    # chunk body
                    newlight = (chunkLight[:, 0:15, :self.Height] - chunkLa[:, 1:16, :self.Height])
                    clipLight(newlight)

                    maximum(chunkLight[:, 1:16, :self.Height], newlight, chunkLight[:, 1:16, :self.Height])

                    # bottom edge
                    nc = neighboringChunks[FaceZDecreasing]
                    ncLight = getattr(nc, light)

                    newlight = ncLight[:, 15:16, :self.Height] - chunkLa[:, 0:1, 0:self.Height]
                    clipLight(newlight)

                    maximum(chunkLight[:, 0:1, 0:self.Height], newlight, chunkLight[:, 0:1, 0:self.Height])

                    zerochunkLight[:] = 0

                    if (oldBottomEdge != ncLight[:, 15:16, :self.Height]).any():
                        newDirtyChunks.append(nc)

                    newlight = (chunkLight[:, :, 0:self.Height - 1] - chunkLa[:, :, 1:self.Height])
                    clipLight(newlight)
                    maximum(chunkLight[:, :, 1:self.Height], newlight, chunkLight[:, :, 1:self.Height])

                    newlight = (chunkLight[:, :, 1:self.Height] - chunkLa[:, :, 0:self.Height - 1])
                    clipLight(newlight)
                    maximum(chunkLight[:, :, 0:self.Height - 1], newlight, chunkLight[:, :, 0:self.Height - 1])

                    if (oldChunk != chunkLight).any():
                        newDirtyChunks.append(chunk)

                    work += 1
                    yield workDone + work, workTotal, progressInfo

                workDone += work
                workTotal -= len(startingDirtyChunks)
                workTotal += work

                work = 0

        for ch in startingDirtyChunks:
            ch.needsLighting = False


def TagProperty(tagName, tagType, default_or_func=None):
    def getter(self):
        if tagName not in self.root_tag["Data"]:
            if hasattr(default_or_func, "__call__"):
                default = default_or_func(self)
            else:
                default = default_or_func

            self.root_tag["Data"][tagName] = tagType(default)
        return self.root_tag["Data"][tagName].value

    def setter(self, val):
        self.root_tag["Data"][tagName] = tagType(value=val)

    return property(getter, setter)

class AnvilWorldFolder(object):
    def __init__(self, filename):
        if not os.path.exists(filename):
            os.mkdir(filename)

        elif not os.path.isdir(filename):
            raise IOError, "AnvilWorldFolder: Not a folder: %s" % filename

        self.filename = filename
        self.regionFiles = {}

    # --- File paths ---

    def getFilePath(self, path):
        path = path.replace("/", os.path.sep)
        return os.path.join(self.filename, path)

    def getFolderPath(self, path):
        path = self.getFilePath(path)
        if not os.path.exists(path):
            os.makedirs(path)

        return path

    # --- Region files ---

    def getRegionFilename(self, rx, rz):
        return os.path.join(self.getFolderPath("region"), "r.%s.%s.%s" % (rx, rz, "mca"))

    def getRegionFile(self, rx, rz):
        regionFile = self.regionFiles.get((rx, rz))
        if regionFile:
            return regionFile
        regionFile = MCRegionFile(self.getRegionFilename(rx, rz), (rx, rz))
        self.regionFiles[rx, rz] = regionFile
        return regionFile

    def getRegionForChunk(self, cx, cz):
        rx = cx >> 5
        rz = cz >> 5
        return self.getRegionFile(rx, rz)

    def closeRegions(self):
        for rf in self.regionFiles.values():
            rf.close()

        self.regionFiles = {}

    # --- Chunks and chunk listing ---

    def tryLoadRegionFile(self, filepath):
        filename = os.path.basename(filepath)
        bits = filename.split('.')
        if len(bits) < 4 or bits[0] != 'r' or bits[3] != "mca":
            return None

        try:
            rx, rz = map(int, bits[1:3])
        except ValueError:
            return None

        return MCRegionFile(filepath, (rx, rz))

    def findRegionFiles(self):
        regionDir = self.getFolderPath("region")

        regionFiles = os.listdir(regionDir)
        for filename in regionFiles:
            yield os.path.join(regionDir, filename)

    def listChunks(self):
        chunks = set()

        for filepath in self.findRegionFiles():
            regionFile = self.tryLoadRegionFile(filepath)
            if regionFile is None:
                continue

            if regionFile.offsets.any():
                rx, rz = regionFile.regionCoords
                self.regionFiles[rx, rz] = regionFile

                for index, offset in enumerate(regionFile.offsets):
                    if offset:
                        cx = index & 0x1f
                        cz = index >> 5

                        cx += rx << 5
                        cz += rz << 5

                        chunks.add((cx, cz))
            else:
                log.info(u"Removing empty region file {0}".format(filepath))
                regionFile.close()
                os.unlink(regionFile.path)

        return chunks

    def containsChunk(self, cx, cz):
        rx = cx >> 5
        rz = cz >> 5
        if not os.path.exists(self.getRegionFilename(rx, rz)):
            return False

        return self.getRegionForChunk(cx, cz).containsChunk(cx, cz)

    def deleteChunk(self, cx, cz):
        r = cx >> 5, cz >> 5
        rf = self.getRegionFile(*r)
        if rf:
            rf.setOffset(cx & 0x1f, cz & 0x1f, 0)
            if (rf.offsets == 0).all():
                rf.close()
                os.unlink(rf.path)
                del self.regionFiles[r]

    def readChunk(self, cx, cz):
        if not self.containsChunk(cx, cz):
            raise ChunkNotPresent((cx, cz))

        return self.getRegionForChunk(cx, cz).readChunk(cx, cz)

    def saveChunk(self, cx, cz, data):
        regionFile = self.getRegionForChunk(cx, cz)
        regionFile.saveChunk(cx, cz, data)

    def copyChunkFrom(self, worldFolder, cx, cz):
        fromRF = worldFolder.getRegionForChunk(cx, cz)
        rf = self.getRegionForChunk(cx, cz)
        rf.copyChunkFrom(fromRF, cx, cz)

class MCInfdevOldLevel(ChunkedLevelMixin, EntityLevel):

    def __init__(self, filename=None, create=False, random_seed=None, last_played=None, readonly=False):
        """
        Load an Alpha level from the given filename. It can point to either
        a level.dat or a folder containing one. If create is True, it will
        also create the world using the random_seed and last_played arguments.
        If they are none, a random 64-bit seed will be selected for RandomSeed
        and long(time.time() * 1000) will be used for LastPlayed.

        If you try to create an existing world, its level.dat will be replaced.
        """

        self.Length = 0
        self.Width = 0
        self.Height = 256

        self.playerTagCache = {}
        self.players = []
        assert not (create and readonly)

        if os.path.basename(filename) in ("level.dat", "level.dat_old"):
            filename = os.path.dirname(filename)

        if not os.path.exists(filename):
            if not create:
                raise IOError('File not found')

            os.mkdir(filename)

        if not os.path.isdir(filename):
            raise IOError('File is not a Minecraft Alpha world')


        self.worldFolder = AnvilWorldFolder(filename)
        self.filename = self.worldFolder.getFilePath("level.dat")
        self.readonly = readonly
        if not readonly:
            self.acquireSessionLock()

            workFolderPath = self.worldFolder.getFolderPath("##MCEDIT.TEMP##")
            if os.path.exists(workFolderPath):
                # xxxxxxx Opening a world a second time deletes the first world's work folder and crashes when the first
                # world tries to read a modified chunk from the work folder. This mainly happens when importing a world
                # into itself after modifying it.
                shutil.rmtree(workFolderPath, True)

            self.unsavedWorkFolder = AnvilWorldFolder(workFolderPath)

        # maps (cx, cz) pairs to AnvilChunk
        self._loadedChunks = weakref.WeakValueDictionary()

        # maps (cx, cz) pairs to AnvilChunkData
        self._loadedChunkData = {}

        self.chunksNeedingLighting = set()
        self._allChunks = None
        self.dimensions = {}

        self.loadLevelDat(create, random_seed, last_played)

        assert self.version == self.VERSION_ANVIL, "Pre-Anvil world formats are not supported (for now)"


        self.playersFolder = self.worldFolder.getFolderPath("players")
        self.players = [x[:-4] for x in os.listdir(self.playersFolder) if x.endswith(".dat")]
        if "Player" in self.root_tag["Data"]:
            self.players.append("Player")

        self.preloadDimensions()

    # --- Load, save, create ---

    def _create(self, filename, random_seed, last_played):

        # create a new level
        root_tag = nbt.TAG_Compound()
        root_tag["Data"] = nbt.TAG_Compound()
        root_tag["Data"]["SpawnX"] = nbt.TAG_Int(0)
        root_tag["Data"]["SpawnY"] = nbt.TAG_Int(2)
        root_tag["Data"]["SpawnZ"] = nbt.TAG_Int(0)

        if last_played is None:
            last_played = long(time.time() * 1000)
        if random_seed is None:
            random_seed = long(random.random() * 0xffffffffffffffffL) - 0x8000000000000000L

        self.root_tag = root_tag
        root_tag["Data"]['version'] = nbt.TAG_Int(self.VERSION_ANVIL)

        self.LastPlayed = long(last_played)
        self.RandomSeed = long(random_seed)
        self.SizeOnDisk = 0
        self.Time = 1
        self.LevelName = os.path.basename(self.worldFolder.filename)

        ### if singleplayer:

        self.createPlayer("Player")

    def acquireSessionLock(self):
        lockfile = self.worldFolder.getFilePath("session.lock")
        self.initTime = int(time.time() * 1000)
        with file(lockfile, "wb") as f:
            f.write(struct.pack(">q", self.initTime))


    def checkSessionLock(self):
        if self.readonly:
            raise SessionLockLost, "World is opened read only."

        lockfile = self.worldFolder.getFilePath("session.lock")
        try:
            (lock, ) = struct.unpack(">q", file(lockfile, "rb").read())
        except struct.error:
            lock = -1
        if lock != self.initTime:
            raise SessionLockLost, "Session lock lost. This world is being accessed from another location."

    def loadLevelDat(self, create=False, random_seed=None, last_played=None):

        if create:
            self._create(self.filename, random_seed, last_played)
            self.saveInPlace()
        else:
            try:
                self.root_tag = nbt.load(self.filename)
            except Exception, e:
                filename_old = self.worldFolder.getFilePath("level.dat_old")
                log.info("Error loading level.dat, trying level.dat_old ({0})".format(e))
                try:
                    self.root_tag = nbt.load(filename_old)
                    log.info("level.dat restored from backup.")
                    self.saveInPlace()
                except Exception, e:
                    traceback.print_exc()
                    print repr(e)
                    log.info("Error loading level.dat_old. Initializing with defaults.")
                    self._create(self.filename, random_seed, last_played)

    def saveInPlace(self):
        if self.readonly:
            raise IOError, "World is opened read only."

        self.checkSessionLock()

        for level in self.dimensions.itervalues():
            level.saveInPlace(True)

        dirtyChunkCount = 0
        for chunk in self._loadedChunkData.itervalues():
            cx, cz = chunk.chunkPosition
            if chunk.dirty:
                data = chunk.savedTagData()
                dirtyChunkCount += 1
                self.worldFolder.saveChunk(cx, cz, data)
                chunk.dirty = False

        for cx, cz in self.unsavedWorkFolder.listChunks():
            if (cx, cz) not in self._loadedChunkData:
                data = self.unsavedWorkFolder.readChunk(cx, cz)
                self.worldFolder.saveChunk(cx, cz, data)
                dirtyChunkCount += 1


        self.unsavedWorkFolder.closeRegions()
        shutil.rmtree(self.unsavedWorkFolder.filename, True)
        os.mkdir(self.unsavedWorkFolder.filename)

        for path, tag in self.playerTagCache.iteritems():
            tag.save(path)

        self.playerTagCache.clear()

        self.root_tag.save(self.filename)
        log.info(u"Saved {0} chunks (dim {1})".format(dirtyChunkCount, self.dimNo))

    def unload(self):
        """
        Unload all chunks and close all open filehandles.
        """
        self.worldFolder.closeRegions()
        if not self.readonly:
            self.unsavedWorkFolder.closeRegions()

        self._allChunks = None
        self._loadedChunks.clear()
        self._loadedChunkData.clear()

    def close(self):
        """
        Unload all chunks and close all open filehandles. Discard any unsaved data.
        """
        self.unload()
        try:
            self.checkSessionLock()
            shutil.rmtree(self.unsavedWorkFolder.filename, True)
        except SessionLockLost:
            pass

    # --- Resource limits ---

    loadedChunkLimit = 400

    # --- Constants ---

    GAMETYPE_SURVIVAL = 0
    GAMETYPE_CREATIVE = 1

    VERSION_MCR = 19132
    VERSION_ANVIL = 19133

    # --- Instance variables  ---

    materials = alphaMaterials
    isInfinite = True
    parentWorld = None
    dimNo = 0
    Height = 256
    _bounds = None

    # --- NBT Tag variables ---

    SizeOnDisk = TagProperty('SizeOnDisk', nbt.TAG_Long, 0)
    RandomSeed = TagProperty('RandomSeed', nbt.TAG_Long, 0)
    Time = TagProperty('Time', nbt.TAG_Long, 0)  # Age of the world in ticks. 20 ticks per second; 24000 ticks per day.
    LastPlayed = TagProperty('LastPlayed', nbt.TAG_Long, lambda self: long(time.time() * 1000))

    LevelName = TagProperty('LevelName', nbt.TAG_String, lambda self: self.displayName)

    MapFeatures = TagProperty('MapFeatures', nbt.TAG_Byte, 1)

    GameType = TagProperty('GameType', nbt.TAG_Int, 0)  # 0 for survival, 1 for creative

    version = TagProperty('version', nbt.TAG_Int, VERSION_ANVIL)

    # --- World info ---

    def __str__(self):
        return "MCInfdevOldLevel(\"%s\")" % os.path.basename(self.worldFolder.filename)

    @property
    def displayName(self):
        # shortname = os.path.basename(self.filename)
        # if shortname == "level.dat":
        shortname = os.path.basename(os.path.dirname(self.filename))

        return shortname

    @property
    def bounds(self):
        if self._bounds is None:
            self._bounds = self.getWorldBounds()
        return self._bounds

    def getWorldBounds(self):
        if self.chunkCount == 0:
            return BoundingBox((0, 0, 0), (0, 0, 0))

        allChunks = array(list(self.allChunks))
        mincx = (allChunks[:, 0]).min()
        maxcx = (allChunks[:, 0]).max()
        mincz = (allChunks[:, 1]).min()
        maxcz = (allChunks[:, 1]).max()

        origin = (mincx << 4, 0, mincz << 4)
        size = ((maxcx - mincx + 1) << 4, self.Height, (maxcz - mincz + 1) << 4)

        return BoundingBox(origin, size)

    @property
    def size(self):
        return self.bounds.size

    # --- Format detection ---

    @classmethod
    def _isLevel(cls, filename):

        if os.path.exists(os.path.join(filename, "chunks.dat")):
            return False  # exclude Pocket Edition folders

        if not os.path.isdir(filename):
            f = os.path.basename(filename)
            if f not in ("level.dat", "level.dat_old"):
                return False
            filename = os.path.dirname(filename)

        files = os.listdir(filename)
        if "level.dat" in files or "level.dat_old" in files:
            return True

        return False

    # --- Dimensions ---

    def preloadDimensions(self):
        worldDirs = os.listdir(self.worldFolder.filename)

        for dirname in worldDirs:
            if dirname.startswith("DIM"):
                try:
                    dimNo = int(dirname[3:])
                    log.info("Found dimension {0}".format(dirname))
                    dim = MCAlphaDimension(self, dimNo)
                    self.dimensions[dimNo] = dim
                except Exception, e:
                    log.error(u"Error loading dimension {0}: {1}".format(dirname, e))

    def getDimension(self, dimNo):
        if self.dimNo != 0:
            return self.parentWorld.getDimension(dimNo)

        if dimNo in self.dimensions:
            return self.dimensions[dimNo]
        dim = MCAlphaDimension(self, dimNo, create=True)
        self.dimensions[dimNo] = dim
        return dim

    # --- Region I/O ---

    def preloadChunkPositions(self):
        log.info(u"Scanning for regions...")
        self._allChunks = self.worldFolder.listChunks()
        if not self.readonly:
            self._allChunks.update(self.unsavedWorkFolder.listChunks())
        self._allChunks.update(self._loadedChunkData.iterkeys())

    def getRegionForChunk(self, cx, cz):
        return self.worldFolder.getRegionFile(cx, cz)

    # --- Chunk I/O ---

    def dirhash(self, n):
        return self.dirhashes[n % 64]

    def _dirhash(self):
        n = self
        n = n % 64
        s = u""
        if n >= 36:
            s += u"1"
            n -= 36
        s += u"0123456789abcdefghijklmnopqrstuvwxyz"[n]

        return s

    dirhashes = [_dirhash(n) for n in range(64)]

    def _oldChunkFilename(self, cx, cz):
        return self.worldFolder.getFilePath("%s/%s/c.%s.%s.dat" % (self.dirhash(cx), self.dirhash(cz), base36(cx), base36(cz)))

    def extractChunksInBox(self, box, parentFolder):
        for cx, cz in box.chunkPositions:
            if self.containsChunk(cx, cz):
                self.extractChunk(cx, cz, parentFolder)

    def extractChunk(self, cx, cz, parentFolder):
        if not os.path.exists(parentFolder):
            os.mkdir(parentFolder)

        chunkFilename = self._oldChunkFilename(cx, cz)
        outputFile = os.path.join(parentFolder, os.path.basename(chunkFilename))

        chunk = self.getChunk(cx, cz)

        chunk.root_tag.save(outputFile)

    @property
    def chunkCount(self):
        """Returns the number of chunks in the level. May initiate a costly
        chunk scan."""
        if self._allChunks is None:
            self.preloadChunkPositions()
        return len(self._allChunks)

    @property
    def allChunks(self):
        """Iterates over (xPos, zPos) tuples, one for each chunk in the level.
        May initiate a costly chunk scan."""
        if self._allChunks is None:
            self.preloadChunkPositions()
        return self._allChunks.__iter__()

    def copyChunkFrom(self, world, cx, cz):
        """
        Copy a chunk from world into the same chunk position in self.
        """
        assert isinstance(world, MCInfdevOldLevel)
        if self.readonly:
            raise IOError, "World is opened read only."
        self.checkSessionLock()

        destChunk = self._loadedChunks.get((cx, cz))
        sourceChunk = world._loadedChunks.get((cx, cz))

        if sourceChunk:
            if destChunk:
                log.debug("Both chunks loaded. Using block copy.")
                # Both chunks loaded. Use block copy.
                self.copyBlocksFrom(world, destChunk.bounds, destChunk.bounds.origin)
                return
            else:
                log.debug("Source chunk loaded. Saving into work folder.")

                # Only source chunk loaded. Discard destination chunk and save source chunk in its place.
                self._loadedChunkData.pop((cx, cz), None)
                self.unsavedWorkFolder.saveChunk(cx, cz, sourceChunk.savedTagData())
                return
        else:
            if destChunk:
                log.debug("Destination chunk loaded. Using block copy.")
                # Only destination chunk loaded. Use block copy.
                self.copyBlocksFrom(world, destChunk.bounds, destChunk.bounds.origin)
            else:
                log.debug("No chunk loaded. Using world folder.copyChunkFrom")
                # Neither chunk loaded. Copy via world folders.
                self._loadedChunkData.pop((cx, cz), None)

                # If the source chunk is dirty, write it to the work folder.
                chunkData = world._loadedChunkData.pop((cx, cz), None)
                if chunkData and chunkData.dirty:
                    data = chunkData.savedTagData()
                    world.unsavedWorkFolder.saveChunk(cx, cz, data)

                if world.unsavedWorkFolder.containsChunk(cx, cz):
                    sourceFolder = world.unsavedWorkFolder
                else:
                    sourceFolder = world.worldFolder

                self.unsavedWorkFolder.copyChunkFrom(sourceFolder, cx, cz)

    def _getChunkBytes(self, cx, cz):
        if not self.readonly and self.unsavedWorkFolder.containsChunk(cx, cz):
            return self.unsavedWorkFolder.readChunk(cx, cz)
        else:
            return self.worldFolder.readChunk(cx, cz)

    def _getChunkData(self, cx, cz):
        chunkData = self._loadedChunkData.get((cx, cz))
        if chunkData is not None: return chunkData

        try:
            data = self._getChunkBytes(cx, cz)
            root_tag = nbt.load(buf=data)
            chunkData = AnvilChunkData(self, (cx, cz), root_tag)
        except (MemoryError, ChunkNotPresent):
            raise
        except Exception, e:
            raise ChunkMalformed, "Chunk {0} had an error: {1!r}".format((cx, cz), e), sys.exc_info()[2]

        if not self.readonly and self.unsavedWorkFolder.containsChunk(cx, cz):
            chunkData.dirty = True

        self._storeLoadedChunkData(chunkData)

        return chunkData

    def _storeLoadedChunkData(self, chunkData):
        if len(self._loadedChunkData) > self.loadedChunkLimit:
            # Try to find a chunk to unload. The chunk must not be in _loadedChunks, which contains only chunks that
            # are in use by another object. If the chunk is dirty, save it to the temporary folder.
            if not self.readonly:
                self.checkSessionLock()
            for (ocx, ocz), oldChunkData in self._loadedChunkData.items():
                if (ocx, ocz) not in self._loadedChunks:
                    if oldChunkData.dirty and not self.readonly:
                        data = oldChunkData.savedTagData()
                        self.unsavedWorkFolder.saveChunk(ocx, ocz, data)

                    del self._loadedChunkData[ocx, ocz]
                    break

        self._loadedChunkData[chunkData.chunkPosition] = chunkData

    def getChunk(self, cx, cz):
        """ read the chunk from disk, load it, and return it."""

        chunk = self._loadedChunks.get((cx, cz))
        if chunk is not None:
            return chunk

        chunkData = self._getChunkData(cx, cz)
        chunk = AnvilChunk(chunkData)

        self._loadedChunks[cx, cz] = chunk
        return chunk

    def markDirtyChunk(self, cx, cz):
        self.getChunk(cx, cz).chunkChanged()

    def markDirtyBox(self, box):
        for cx, cz in box.chunkPositions:
            self.markDirtyChunk(cx, cz)

    def listDirtyChunks(self):
        for cPos, chunkData in self._loadedChunkData.iteritems():
            if chunkData.dirty:
                yield cPos

    # --- HeightMaps ---

    def heightMapAt(self, x, z):
        zc = z >> 4
        xc = x >> 4
        xInChunk = x & 0xf
        zInChunk = z & 0xf

        ch = self.getChunk(xc, zc)

        heightMap = ch.HeightMap

        return heightMap[zInChunk, xInChunk]  # HeightMap indices are backwards

    # --- Entities and TileEntities ---

    def addEntity(self, entityTag):
        assert isinstance(entityTag, nbt.TAG_Compound)
        x, y, z = map(lambda x: int(floor(x)), Entity.pos(entityTag))

        try:
            chunk = self.getChunk(x >> 4, z >> 4)
        except (ChunkNotPresent, ChunkMalformed):
            return None
            # raise Error, can't find a chunk?
        chunk.addEntity(entityTag)
        chunk.dirty = True

    def tileEntityAt(self, x, y, z):
        chunk = self.getChunk(x >> 4, z >> 4)
        return chunk.tileEntityAt(x, y, z)

    def addTileEntity(self, tileEntityTag):
        assert isinstance(tileEntityTag, nbt.TAG_Compound)
        if not 'x' in tileEntityTag:
            return
        x, y, z = TileEntity.pos(tileEntityTag)

        try:
            chunk = self.getChunk(x >> 4, z >> 4)
        except (ChunkNotPresent, ChunkMalformed):
            return
            # raise Error, can't find a chunk?
        chunk.addTileEntity(tileEntityTag)
        chunk.dirty = True

    def getEntitiesInBox(self, box):
        entities = []
        for chunk, slices, point in self.getChunkSlices(box):
            entities += chunk.getEntitiesInBox(box)

        return entities

    def removeEntitiesInBox(self, box):
        count = 0
        for chunk, slices, point in self.getChunkSlices(box):
            count += chunk.removeEntitiesInBox(box)

        log.info("Removed {0} entities".format(count))
        return count

    def removeTileEntitiesInBox(self, box):
        count = 0
        for chunk, slices, point in self.getChunkSlices(box):
            count += chunk.removeTileEntitiesInBox(box)

        log.info("Removed {0} tile entities".format(count))
        return count

    # --- Chunk manipulation ---

    def containsChunk(self, cx, cz):
        if self._allChunks is not None:
            return (cx, cz) in self._allChunks
        if (cx, cz) in self._loadedChunkData:
            return True

        return self.worldFolder.containsChunk(cx, cz)

    def containsPoint(self, x, y, z):
        if y < 0 or y > 127:
            return False
        return self.containsChunk(x >> 4, z >> 4)

    def createChunk(self, cx, cz):
        if self.containsChunk(cx, cz):
            raise ValueError("{0}:Chunk {1} already present!".format(self, (cx, cz)))
        if self._allChunks is not None:
            self._allChunks.add((cx, cz))

        self._storeLoadedChunkData(AnvilChunkData(self, (cx, cz), create=True))
        self._bounds = None

    def createChunks(self, chunks):

        i = 0
        ret = []
        for cx, cz in chunks:
            i += 1
            if not self.containsChunk(cx, cz):
                ret.append((cx, cz))
                self.createChunk(cx, cz)
            assert self.containsChunk(cx, cz), "Just created {0} but it didn't take".format((cx, cz))
            if i % 100 == 0:
                log.info(u"Chunk {0}...".format(i))

        log.info("Created {0} chunks.".format(len(ret)))

        return ret

    def createChunksInBox(self, box):
        log.info(u"Creating {0} chunks in {1}".format((box.maxcx - box.mincx) * (box.maxcz - box.mincz), ((box.mincx, box.mincz), (box.maxcx, box.maxcz))))
        return self.createChunks(box.chunkPositions)

    def deleteChunk(self, cx, cz):
        self.worldFolder.deleteChunk(cx, cz)
        if self._allChunks is not None:
            self._allChunks.discard((cx, cz))

        self._bounds = None


    def deleteChunksInBox(self, box):
        log.info(u"Deleting {0} chunks in {1}".format((box.maxcx - box.mincx) * (box.maxcz - box.mincz), ((box.mincx, box.mincz), (box.maxcx, box.maxcz))))
        i = 0
        ret = []
        for cx, cz in itertools.product(xrange(box.mincx, box.maxcx), xrange(box.mincz, box.maxcz)):
            i += 1
            if self.containsChunk(cx, cz):
                self.deleteChunk(cx, cz)
                ret.append((cx, cz))

            assert not self.containsChunk(cx, cz), "Just deleted {0} but it didn't take".format((cx, cz))

            if i % 100 == 0:
                log.info(u"Chunk {0}...".format(i))

        return ret

    # --- Player and spawn manipulation ---

    def playerSpawnPosition(self, player=None):
        """
        xxx if player is None then it gets the default spawn position for the world
        if player hasn't used a bed then it gets the default spawn position
        """
        dataTag = self.root_tag["Data"]
        if player is None:
            playerSpawnTag = dataTag
        else:
            playerSpawnTag = self.getPlayerTag(player)

        return [playerSpawnTag.get(i, dataTag[i]).value for i in ("SpawnX", "SpawnY", "SpawnZ")]

    def setPlayerSpawnPosition(self, pos, player=None):
        """ xxx if player is None then it sets the default spawn position for the world """
        if player is None:
            playerSpawnTag = self.root_tag["Data"]
        else:
            playerSpawnTag = self.getPlayerTag(player)
        for name, val in zip(("SpawnX", "SpawnY", "SpawnZ"), pos):
            playerSpawnTag[name] = nbt.TAG_Int(val)

    def getPlayerPath(self, player):
        assert player != "Player"
        return os.path.join(self.playersFolder, "%s.dat" % player)

    def getPlayerTag(self, player="Player"):
        if player == "Player":
            if player in self.root_tag["Data"]:
                # single-player world
                return self.root_tag["Data"]["Player"]
            raise PlayerNotFound(player)
        else:
            playerFilePath = self.getPlayerPath(player)
            if os.path.exists(playerFilePath):
                # multiplayer world, found this player
                playerTag = self.playerTagCache.get(playerFilePath)
                if playerTag is None:
                    playerTag = nbt.load(playerFilePath)
                    self.playerTagCache[playerFilePath] = playerTag
                return playerTag
            else:
                raise PlayerNotFound(player)

    def getPlayerDimension(self, player="Player"):
        playerTag = self.getPlayerTag(player)
        if "Dimension" not in playerTag:
            return 0
        return playerTag["Dimension"].value

    def setPlayerDimension(self, d, player="Player"):
        playerTag = self.getPlayerTag(player)
        if "Dimension" not in playerTag:
            playerTag["Dimension"] = nbt.TAG_Int(0)
        playerTag["Dimension"].value = d

    def setPlayerPosition(self, pos, player="Player"):
        posList = nbt.TAG_List([nbt.TAG_Double(p) for p in pos])
        playerTag = self.getPlayerTag(player)

        playerTag["Pos"] = posList

    def getPlayerPosition(self, player="Player"):
        playerTag = self.getPlayerTag(player)
        posList = playerTag["Pos"]

        pos = map(lambda x: x.value, posList)
        return pos

    def setPlayerOrientation(self, yp, player="Player"):
        self.getPlayerTag(player)["Rotation"] = nbt.TAG_List([nbt.TAG_Float(p) for p in yp])

    def getPlayerOrientation(self, player="Player"):
        """ returns (yaw, pitch) """
        yp = map(lambda x: x.value, self.getPlayerTag(player)["Rotation"])
        y, p = yp
        if p == 0:
            p = 0.000000001
        if p == 180.0:
            p -= 0.000000001
        yp = y, p
        return array(yp)

    def setPlayerAbilities(self, gametype, player="Player"):
        playerTag = self.getPlayerTag(player)

        # Check for the Abilities tag.  It will be missing in worlds from before
        # Beta 1.9 Prerelease 5.
        if not 'abilities' in playerTag:
            playerTag['abilities'] = nbt.TAG_Compound()

        # Assumes creative (1) is the only mode with these abilities set,
        # which is true for now.  Future game modes may not hold this to be
        # true, however.
        if gametype == 1:
            playerTag['abilities']['instabuild'] = nbt.TAG_Byte(1)
            playerTag['abilities']['mayfly'] = nbt.TAG_Byte(1)
            playerTag['abilities']['invulnerable'] = nbt.TAG_Byte(1)
        else:
            playerTag['abilities']['flying'] = nbt.TAG_Byte(0)
            playerTag['abilities']['instabuild'] = nbt.TAG_Byte(0)
            playerTag['abilities']['mayfly'] = nbt.TAG_Byte(0)
            playerTag['abilities']['invulnerable'] = nbt.TAG_Byte(0)

    def setPlayerGameType(self, gametype, player="Player"):
        playerTag = self.getPlayerTag(player)
        # This annoyingly works differently between single- and multi-player.
        if player == "Player":
            self.GameType = gametype
            self.setPlayerAbilities(gametype, player)
        else:
            playerTag['playerGameType'] = nbt.TAG_Int(gametype)
            self.setPlayerAbilities(gametype, player)

    def getPlayerGameType(self, player="Player"):
        if player == "Player":
            return self.GameType
        else:
            playerTag = self.getPlayerTag(player)
            return playerTag["playerGameType"].value

    def createPlayer(self, playerName):
        if playerName == "Player":
            playerTag = self.root_tag["Data"].setdefault(playerName, nbt.TAG_Compound())
        else:
            playerTag = nbt.TAG_Compound()

        playerTag['Air'] = nbt.TAG_Short(300)
        playerTag['AttackTime'] = nbt.TAG_Short(0)
        playerTag['DeathTime'] = nbt.TAG_Short(0)
        playerTag['Fire'] = nbt.TAG_Short(-20)
        playerTag['Health'] = nbt.TAG_Short(20)
        playerTag['HurtTime'] = nbt.TAG_Short(0)
        playerTag['Score'] = nbt.TAG_Int(0)
        playerTag['FallDistance'] = nbt.TAG_Float(0)
        playerTag['OnGround'] = nbt.TAG_Byte(0)

        playerTag["Inventory"] = nbt.TAG_List()

        playerTag['Motion'] = nbt.TAG_List([nbt.TAG_Double(0) for i in range(3)])
        playerTag['Pos'] = nbt.TAG_List([nbt.TAG_Double([0.5, 2.8, 0.5][i]) for i in range(3)])
        playerTag['Rotation'] = nbt.TAG_List([nbt.TAG_Float(0), nbt.TAG_Float(0)])

        if playerName != "Player":
            if self.readonly:
                raise IOError, "World is opened read only."
            self.checkSessionLock()
            playerTag.save(self.getPlayerPath(playerName))


class MCAlphaDimension (MCInfdevOldLevel):
    def __init__(self, parentWorld, dimNo, create=False):
        filename = parentWorld.worldFolder.getFolderPath("DIM" + str(int(dimNo)))

        self.parentWorld = parentWorld
        MCInfdevOldLevel.__init__(self, filename, create)
        self.dimNo = dimNo
        self.filename = parentWorld.filename
        self.players = self.parentWorld.players
        self.playersFolder = self.parentWorld.playersFolder
        self.playerTagCache = self.parentWorld.playerTagCache

    @property
    def root_tag(self):
        return self.parentWorld.root_tag

    def __str__(self):
        return u"MCAlphaDimension({0}, {1})".format(self.parentWorld, self.dimNo)

    def loadLevelDat(self, create=False, random_seed=None, last_played=None):
        pass

    def preloadDimensions(self):
        pass

    def _create(self, *args, **kw):
        pass

    def acquireSessionLock(self):
        pass

    def checkSessionLock(self):
        self.parentWorld.checkSessionLock()

    dimensionNames = {-1: "Nether", 1: "The End"}

    @property
    def displayName(self):
        return u"{0} ({1})".format(self.parentWorld.displayName,
                                   self.dimensionNames.get(self.dimNo, "Dimension %d" % self.dimNo))

    def saveInPlace(self, saveSelf=False):
        """saving the dimension will save the parent world, which will save any
         other dimensions that need saving.  the intent is that all of them can
         stay loaded at once for fast switching """

        if saveSelf:
            MCInfdevOldLevel.saveInPlace(self)
        else:
            self.parentWorld.saveInPlace()


########NEW FILE########
__FILENAME__ = items
from logging import getLogger
logger = getLogger(__file__)

items_txt = """
:version 34
:mc-version Minecraft 1.4

#            Blocks
# ID  NAME                   FILE         CORDS   DAMAGE
   1  Stone                  terrain.png  1,0
   2  Grass                  terrain.png  3,0
   3  Dirt                   terrain.png  2,0
   4  Cobblestone            terrain.png  0,1
   5  Oak_Wooden_Planks      terrain.png  4,0    0
   5  Spruce_Wooden_Planks   terrain.png  6,12   1
   5  Birch_Wooden_Planks    terrain.png  6,13   2
   5  Jungle_Wooden_Planks   terrain.png  7,12   3
   6  Oak_Sapling            terrain.png  15,0   0
   6  Spruce_Sapling         terrain.png  15,3   1
   6  Birch_Sapling          terrain.png  15,4   2
   6  Jungle_Sapling         terrain.png  14,1   3
   7  Bedrock                terrain.png  1,1
   8  Water                  terrain.png  15,13
   9  Still_Water            terrain.png  15,13
  10  Lava                   terrain.png  15,15
  11  Still_Lava             terrain.png  15,15
  12  Sand                   terrain.png  2,1
  13  Gravel                 terrain.png  3,1
  14  Gold_Ore               terrain.png  0,2
  15  Iron_Ore               terrain.png  1,2
  16  Coal_Ore               terrain.png  2,2
  17  Oak_Wood               terrain.png  4,1    0
  17  Dark_Wood              terrain.png  4,7    1
  17  Birch_Wood             terrain.png  5,7    2
  17  Jungle_Wood            terrain.png  9,9    3
  18  Oak_Leaves             special.png  15,0   0
  18  Dark_Leaves            special.png  14,1   1
  18  Birch_Leaves           special.png  14,2   2
  18  Jungle_Leaves          special.png  14,3   3
  19  Sponge                 terrain.png  0,3
  20  Glass                  terrain.png  1,3
  21  Lapis_Lazuli_Ore       terrain.png  0,10
  22  Lapis_Lazuli_Block     terrain.png  0,9
  23  Dispenser              terrain.png  14,2
  24  Sandstone              terrain.png  0,12   0
  24  Chiseled_Sandstone     terrain.png  5,14   1
  24  Smooth_Sandstone       terrain.png  6,14   2
  25  Note_Block             terrain.png  10,4
  26  Bed_Block              terrain.png  6,8
  27  Powered_Rail           terrain.png  3,10
  28  Detector_Rail          terrain.png  3,12
  29  Sticky_Piston          terrain.png  10,6
  30  Cobweb                 terrain.png  11,0
  31  Dead_Bush              terrain.png  7,3    0
  31  Tall_Grass             special.png  15,0   1
  31  Fern                   special.png  15,1   2
  32  Dead_Bush              terrain.png  7,3
  33  Piston                 terrain.png  11,6
  34  Piston_(head)          terrain.png  11,6
  35  Wool                   terrain.png  0,4    0
  35  Orange_Wool            terrain.png  2,13   1
  35  Magenta_Wool           terrain.png  2,12   2
  35  Light_Blue_Wool        terrain.png  2,11   3
  35  Yellow_Wool            terrain.png  2,10   4
  35  Lime_Wool              terrain.png  2,9    5
  35  Pink_Wool              terrain.png  2,8    6
  35  Gray_Wool              terrain.png  2,7    7
  35  Light_Gray_Wool        terrain.png  1,14   8
  35  Cyan_Wool              terrain.png  1,13   9
  35  Purple_Wool            terrain.png  1,12   10
  35  Blue_Wool              terrain.png  1,11   11
  35  Brown_Wool             terrain.png  1,10   12
  35  Green_Wool             terrain.png  1,9    13
  35  Red_Wool               terrain.png  1,8    14
  35  Black_Wool             terrain.png  1,7    15
  37  Flower                 terrain.png  13,0
  38  Rose                   terrain.png  12,0
  39  Brown_Mushroom         terrain.png  13,1
  40  Red_Mushroom           terrain.png  12,1
  41  Block_of_Gold          terrain.png  7,1
  42  Block_of_Iron          terrain.png  6,1
  43  Double_Stone_Slab      terrain.png  5,0    0
  43  Double_Sandstone_Slab  terrain.png  0,12   1
  43  Double_Wooden_Slab     terrain.png  4,0    2
  43  Double_Stone_Slab      terrain.png  0,1    3
  44  Stone_Slab             special.png  2,2    0
  44  Sandstone_Slab         special.png  8,0    1
  44  Wooden_Slab            special.png  3,0    2
  44  Stone_Slab             special.png  1,0    3
  44  Brick_Slab             special.png  0,0    4
  44  Stone_Brick_Slab       special.png  2,0    5
  45  Bricks                 terrain.png  7,0
  46  TNT                    terrain.png  8,0
  47  Bookshelf              terrain.png  3,2
  48  Moss_Stone             terrain.png  4,2
  49  Obsidian               terrain.png  5,2
  50  Torch                  terrain.png  0,5
  51  Fire                   special.png  0,5
  52  Monster_Spawner        terrain.png  1,4
  53  Oak_Wood_Stair         special.png  3,1
  54  Chest                  special.png  0,6
  55  Redstone_Dust          terrain.png  4,5
  56  Diamond_Ore            terrain.png  2,3
  57  Block_of_Diamond       terrain.png  8,1
  58  Workbench              terrain.png  12,3   (x1)
  59  Crops                  terrain.png  15,5
  60  Farmland               terrain.png  7,5
  61  Furnace                terrain.png  12,2
  62  Lit_Furnace            terrain.png  13,3
  63  Sign_Block             terrain.png  0,0
  64  Wooden_Door_Block      terrain.png  1,6
  65  Ladder                 terrain.png  3,5
  66  Rail                   terrain.png  0,8
  67  Stone_Stairs           special.png  1,1
  68  Wall_Sign              terrain.png  4,0
  69  Lever                  terrain.png  0,6
  70  Stone_Pressure_Plate   special.png  2,4
  71  Iron_Door_Block        terrain.png  2,6
  72  Wooden_Pressure_Plate  special.png  3,4
  73  Redstone_Ore           terrain.png  3,3
  74  Glowing_Redstone_Ore   terrain.png  3,3
  75  Redstone_Torch_(off)   terrain.png  3,7
  76  Redstone_Torch         terrain.png  3,6
  77  Stone_Button           special.png  2,3
  78  Snow_Layer             special.png  1,4
  79  Ice                    terrain.png  3,4
  80  Snow                   terrain.png  2,4
  81  Cactus                 terrain.png  6,4
  82  Clay                   terrain.png  8,4
  83  Sugar_cane             terrain.png  9,4
  84  Jukebox                terrain.png  10,4
  85  Fence                  special.png  3,2
  86  Pumpkin                terrain.png  7,7
  87  Netherrack             terrain.png  7,6
  88  Soul_Sand              terrain.png  8,6
  89  Glowstone              terrain.png  9,6
  90  Portal                 special.png  1,5
  91  Jack-o'-lantern        terrain.png  8,7
  92  Cake                   special.png  0,4
  93  Repeater_Block_(off)   terrain.png  3,8
  94  Repeater_Block         terrain.png  3,9
  95  Locked_Chest           special.png  0,2
  96  Trapdoor               terrain.png  4,5
  97  Silverfish_Block       terrain.png  1,0
  98  Stone_Brick            terrain.png  6,3    0
  98  Mossy_Stone_Brick      terrain.png  4,6    1
  98  Cracked_Stone_Brick    terrain.png  5,6    2
  98  Chiseled_Stone_Brick   terrain.png  5,13   3
  99  Brown_Mushroom_Block   terrain.png  13,7
 100  Red_Mushroom_Block     terrain.png  14,7
 101  Iron_Bars              terrain.png  5,5
 102  Glass_Pane             special.png  1,3
 103  Melon                  terrain.png  8,8
 104  Pumpkin_Stem           special.png  15,4
 105  Melon_Stem             special.png  15,4
 106  Vines                  special.png  15,2
 107  Fence_Gate             special.png  4,3
 108  Brick_Stairs           special.png  0,1
 109  Stone_Brick_Stairs     special.png  2,1
 110  Mycelium               terrain.png  13,4
 111  Lily_Pad               special.png  15,3
 112  Nether_Brick           terrain.png  0,14
 113  Nether_Brick_Fence     special.png  7,2
 114  Nether_Brick_Stairs    special.png  7,1
 115  Nether_Wart            terrain.png  2,14
 116  Enchantment_Table      terrain.png  6,11   (x1)
 117  Brewing_Stand          terrain.png  13,9
 118  Cauldron               terrain.png  10,9
 119  End_Portal             special.png  2,5
 120  End_Portal_Frame       terrain.png  15,9
 121  End_Stone              terrain.png  15,10
 122  Dragon_Egg             special.png  0,7
 123  Redstone_Lamp          terrain.png  3,13
 124  Redstone_Lamp_(on)     terrain.png  4,13
 125  Oak_Wooden_D._Slab     terrain.png  4,0    0
 125  Spruce_Wooden_D._Slab  terrain.png  6,12   1
 125  Birch_Wooden_D._Slab   terrain.png  6,13   2
 125  Jungle_Wooden_D._Slab  terrain.png  7,12   3
 126  Oak_Wooden_Slab        special.png  3,0    0
 126  Spruce_Wooden_Slab     special.png  4,0    1
 126  Birch_Wooden_Slab      special.png  5,0    2
 126  Jungle_Wooden_Slab     special.png  6,0    3
 127  Cocoa_Plant            special.png  15,5
 128  Sandstone_Stairs       special.png  8,1
 129  Emerald_Ore            terrain.png  11,10
 130  Ender_Chest            special.png  1,6
 131  Tripwire_Hook          terrain.png  12,10
 132  Tripwire               terrain.png  5,11
 133  Block_of_Emerald       terrain.png  9,1
 134  Spruce_Wood_Stairs     special.png  4,1
 135  Birch_Wood_Stairs      special.png  5,1
 136  Jungle_Wood_Stairs     special.png  6,1
 137  Command_Block          terrain.png  8,11
 138  Beacon                 special.png  2,6
 139  Cobblestone_Wall       special.png  1,2    0
 140  Moss_Stone_Wall        special.png  0,2    1
 141  Flower_Pot             terrain.png  9,11
 142  Carrots                terrain.png  11,12
 143  Potatoes               terrain.png  12,12
 144  Wooden_Button          special.png  3,3
 145  Head                     items.png  0,14
 146  Anvil                  special.png  3,6    0
 146  Slightly_Damaged_Anvil special.png  4,6    1
 146  Very_Damaged_Anvil     special.png  5,6    2

#            Items
# ID  NAME                   FILE       CORDS  DAMAGE
 256  Iron_Shovel            items.png  2,5    +250
 257  Iron_Pickaxe           items.png  2,6    +250
 258  Iron_Axe               items.png  2,7    +250
 259  Flint_and_Steel        items.png  5,0    +64
 260  Apple                  items.png  10,0
 261  Bow                    items.png  5,1    +384
 262  Arrow                  items.png  5,2
 263  Coal                   items.png  7,0    0
 263  Charcoal               items.png  7,0    1
 264  Diamond                items.png  7,3
 265  Iron_Ingot             items.png  7,1
 266  Gold_Ingot             items.png  7,2
 267  Iron_Sword             items.png  2,4    +250
 268  Wooden_Sword           items.png  0,4    +59
 269  Wooden_Shovel          items.png  0,5    +59
 270  Wooden_Pickaxe         items.png  0,6    +59
 271  Wooden_Axe             items.png  0,7    +59
 272  Stone_Sword            items.png  1,4    +131
 273  Stone_Shovel           items.png  1,5    +131
 274  Stone_Pickaxe          items.png  1,6    +131
 275  Stone_Axe              items.png  1,7    +131
 276  Diamond_Sword          items.png  3,4    +1561
 277  Diamond_Shovel         items.png  3,5    +1561
 278  Diamond_Pickaxe        items.png  3,6    +1561
 279  Diamond_Axe            items.png  3,7    +1561
 280  Stick                  items.png  5,3
 281  Bowl                   items.png  7,4
 282  Mushroom_Stew          items.png  8,4    x1
 283  Golden_Sword           items.png  4,4    +32
 284  Golden_Shovel          items.png  4,5    +32
 285  Golden_Pickaxe         items.png  4,6    +32
 286  Golden_Axe             items.png  4,7    +32
 287  String                 items.png  8,0
 288  Feather                items.png  8,1
 289  Gunpowder              items.png  8,2
 290  Wooden_Hoe             items.png  0,8    +59
 291  Stone_Hoe              items.png  1,8    +131
 292  Iron_Hoe               items.png  2,8    +250
 293  Diamond_Hoe            items.png  3,8    +1561
 294  Golden_Hoe             items.png  4,8    +32
 295  Seeds                  items.png  9,0
 296  Wheat                  items.png  9,1
 297  Bread                  items.png  9,2
 298  Leather_Cap            items.png  0,0    +34
 299  Leather_Tunic          items.png  0,1    +48
 300  Leather_Pants          items.png  0,2    +46
 301  Leather_Boots          items.png  0,3    +40
 302  Chainmail_Helmet       items.png  1,0    +68
 303  Chainmail_Chestplate   items.png  1,1    +96
 304  Chainmail_Leggings     items.png  1,2    +92
 305  Chainmail_Boots        items.png  1,3    +80
 306  Iron_Helmet            items.png  2,0    +136
 307  Iron_Chestplate        items.png  2,1    +192
 308  Iron_Leggings          items.png  2,2    +184
 309  Iron_Boots             items.png  2,3    +160
 310  Diamond_Helmet         items.png  3,0    +272
 311  Diamond_Chestplate     items.png  3,1    +384
 312  Diamond_Leggings       items.png  3,2    +368
 313  Diamond_Boots          items.png  3,3    +320
 314  Golden_Helmet          items.png  4,0    +68
 315  Golden_Chestplate      items.png  4,1    +96
 316  Golden_Leggings        items.png  4,2    +92
 317  Golden_Boots           items.png  4,3    +80
 318  Flint                  items.png  6,0
 319  Raw_Porkchop           items.png  7,5
 320  Cooked_Porkchop        items.png  8,5
 321  Painting               items.png  10,1
 322  Golden_Apple           items.png  11,0
 322  Ench._Golden_Apple   special.png  0,3    1
 323  Sign                   items.png  10,2   x16
 324  Wooden_Door            items.png  11,2   x1
 325  Bucket                 items.png  10,4   x16
 326  Water_Bucket           items.png  11,4   x1
 327  Lava_Bucket            items.png  12,4   x1
 328  Minecart               items.png  7,8    x1
 329  Saddle                 items.png  8,6    x1
 330  Iron_Door              items.png  12,2   x1
 331  Redstone               items.png  8,3
 332  Snowball               items.png  14,0   x16
 333  Boat                   items.png  8,8    x1
 334  Leather                items.png  7,6
 335  Milk                   items.png  13,4   x1
 336  Brick                  items.png  6,1
 337  Clay                   items.png  9,3
 338  Sugar_Canes            items.png  11,1
 339  Paper                  items.png  10,3
 340  Book                   items.png  11,3
 341  Slimeball              items.png  14,1
 342  Minecart_with_Chest    items.png  7,9    x1
 343  Minecart_with_Furnace  items.png  7,10   x1
 344  Egg                    items.png  12,0
 345  Compass                items.png  6,3    (x1)
 346  Fishing_Rod            items.png  5,4    +64
 347  Clock                  items.png  6,4    (x1)
 348  Glowstone_Dust         items.png  9,4
 349  Raw_Fish               items.png  9,5
 350  Cooked_Fish            items.png  10,5
 351  Ink_Sack               items.png  14,4   0
 351  Rose_Red               items.png  14,5   1
 351  Cactus_Green           items.png  14,6   2
 351  Coco_Beans             items.png  14,7   3
 351  Lapis_Lazuli           items.png  14,8   4
 351  Purple_Dye             items.png  14,9   5
 351  Cyan_Dye               items.png  14,10  6
 351  Light_Gray_Dye         items.png  14,11  7
 351  Gray_Dye               items.png  15,4   8
 351  Pink_Dye               items.png  15,5   9
 351  Lime_Dye               items.png  15,6   10
 351  Dandelion_Yellow       items.png  15,7   11
 351  Light_Blue_Dye         items.png  15,8   12
 351  Magenta_Dye            items.png  15,9   13
 351  Orange_Dye             items.png  15,10  14
 351  Bone_Meal              items.png  15,11  15
 352  Bone                   items.png  12,1
 353  Sugar                  items.png  13,0
 354  Cake                   items.png  13,1   x1
 355  Bed                    items.png  13,2   x1
 356  Redstone_Repeater      items.png  6,5
 357  Cookie                 items.png  12,5
 358  Map                    items.png  12,3   x1
 359  Shears                 items.png  13,5   +238
 360  Melon                  items.png  13,6
 361  Pumpkin_Seeds          items.png  13,3
 362  Melon_Seeds            items.png  14,3
 363  Raw_Beef               items.png  9,6
 364  Steak                  items.png  10,6
 365  Raw_Chicken            items.png  9,7
 366  Cooked_Chicken         items.png  10,7
 367  Rotten_Flesh           items.png  11,5
 368  Ender_Pearl            items.png  11,6
 369  Blaze_Rod              items.png  12,6
 370  Ghast_Tear             items.png  11,7
 371  Gold_Nugget            items.png  12,7
 372  Nether_Wart            items.png  13,7
 374  Glass_Bottle           items.png  12,8
 375  Spider_Eye             items.png  11,8
 376  Fermented_Spider_Eye   items.png  10,8
 377  Blaze_Powder           items.png  13,9
 378  Magma_Cream            items.png  13,10
 379  Brewing_Stand          items.png  12,10  (x1)
 380  Cauldron               items.png  12,9   (x1)
 381  Eye_of_Ender           items.png  11,9
 382  Glistering_Melon       items.png  9,8
 383  Spawn_Egg              items.png  9,9
 384  Bottle_o'_Enchanting   items.png  11,10
 385  Fire_Charge            items.png  14,2
 386  Book_and_Quill         items.png  11,11  x1
 387  Written_Book           items.png  12,11  x1
 388  Emerald                items.png  10,11
 389  Item_Frame             items.png  14,12
 390  Flower_Pot             items.png  13,11
 391  Carrot                 items.png  8,7
 392  Potato                 items.png  7,7
 393  Baked_Potato           items.png  6,7
 394  Poisonous_Potato       items.png  6,8
 395  Empty_Map              items.png  13,12  x1
 396  Golden_Carrot          items.png  6,9
 397  Skeleton_Head          items.png  0,14   0
 397  Wither_Skeleton_Head   items.png  1,14   1
 397  Zombie_Head            items.png  2,14   2
 397  Human_Head             items.png  3,14   3
 397  Creeper_Head           items.png  4,14   4
 398  Carrot_on_a_Stick      items.png  6,6    +25
 399  Nether_Star            items.png  9,11
 400  Pumpkin_Pie            items.png  8,9
2256  C418_-_13              items.png  0,15   x1
2257  C418_-_cat             items.png  1,15   x1
2258  C418_-_blocks          items.png  2,15   x1
2259  C418_-_chirp           items.png  3,15   x1
2260  C418_-_far             items.png  4,15   x1
2261  C418_-_mall            items.png  5,15   x1
2262  C418_-_mellohi         items.png  6,15   x1
2263  C418_-_stal            items.png  7,15   x1
2264  C418_-_strad           items.png  8,15   x1
2265  C418_-_ward            items.png  9,15   x1
2266  C418_-_11              items.png  10,15  x1

#           Potions
# ID  NAME                    FILE         CORDS  DAMAGE
 373  Water_Bottle            special.png  0,14   0
 373  Awkward_Potion          special.png  1,14   16
 373  Thick_Potion            special.png  1,14   32
 373  Mundane_Potion          special.png  1,14   64
 373  Mundane_Potion          special.png  1,14   8192
 373  Regeneration_(0:45)     special.png  2,14   8193
 373  Regeneration_(2:00)     special.png  2,14   8257
 373  Regeneration_II_(0:22)  special.png  2,14   8225
 373  Swiftness_(3:00)        special.png  3,14   8194
 373  Swiftness_(8:00)        special.png  3,14   8258
 373  Swiftness_II_(1:30)     special.png  3,14   8226
 373  Fire_Resistance_(3:00)  special.png  4,14   8195
 373  Fire_Resistance_(3:00)  special.png  4,14   8227
 373  Fire_Resistance_(8:00)  special.png  4,14   8259
 373  Healing                 special.png  6,14   8197
 373  Healing                 special.png  6,14   8261
 373  Healing_II              special.png  6,14   8229
 373  Strength_(3:00)         special.png  8,14   8201
 373  Strength_(8:00)         special.png  8,14   8265
 373  Strength_II_(1:30)      special.png  8,14   8233
 373  Poison_(0:45)           special.png  5,14   8196
 373  Poison_(2:00)           special.png  5,14   8260
 373  Poison_II_(0:22)        special.png  5,14   8228
 373  Weakness_(1:30)         special.png  7,14   8200
 373  Weakness_(1:30)         special.png  7,14   8332
 373  Weakness_(4:00)         special.png  7,14   8264
 373  Slowness_(1:30)         special.png  9,14   8202
 373  Slowness_(1:30)         special.png  9,14   8234
 373  Slowness_(4:00)         special.png  9,14   8266
 373  Harming                 special.png  10,14  8204
 373  Harming                 special.png  10,14  8268
 373  Harming_II              special.png  10,14  8236
# Unbrewable:
 373  Regeneration_II_(1:00)  special.png  2,14   8289
 373  Swiftness_II_(4:00)     special.png  3,14   8290
 373  Strength_II_(4:00)      special.png  8,14   8297
 373  Poison_II_(1:00)        special.png  5,14   8292

#           Splash Potions
# ID  NAME                    FILE         CORDS  DAMAGE
 373  Splash_Mundane          special.png  1,13   16384
 373  Regeneration_(0:33)     special.png  2,13   16385
 373  Regeneration_(1:30)     special.png  2,13   16499
 373  Regeneration_II_(0:16)  special.png  2,13   16417
 373  Swiftness_(2:15)        special.png  3,13   16386
 373  Swiftness_(6:00)        special.png  3,13   16450
 373  Swiftness_II_(1:07)     special.png  3,13   16418
 373  Fire_Resistance_(2:15)  special.png  4,13   16387
 373  Fire_Resistance_(2:15)  special.png  4,13   16419
 373  Fire_Resistance_(6:00)  special.png  4,13   16451
 373  Healing                 special.png  6,13   16389
 373  Healing                 special.png  6,13   16453
 373  Healing_II              special.png  6,13   16421
 373  Strength_(2:15)         special.png  8,13   16393
 373  Strength_(6:00)         special.png  8,13   16457
 373  Strength_II_(1:07)      special.png  8,13   16425
 373  Poison_(0:33)           special.png  5,13   16388
 373  Poison_(1:30)           special.png  5,13   16452
 373  Poison_II_(0:16)        special.png  5,13   16420
 373  Weakness_(1:07)         special.png  7,13   16392
 373  Weakness_(1:07)         special.png  7,13   16424
 373  Weakness_(3:00)         special.png  7,13   16456
 373  Slowness_(1:07)         special.png  9,13   16394
 373  Slowness_(1:07)         special.png  9,13   16426
 373  Slowness_(3:00)         special.png  9,13   16458
 373  Harming                 special.png  10,13  16396
 373  Harming                 special.png  10,13  16460
 373  Harming_II              special.png  10,13  16428
# Unbrewable:
 373  Regeneration_II_(0:45)  special.png  2,13   16481
 373  Swiftness_II_(3:00)     special.png  3,13   16482
 373  Strength_II_(3:00)      special.png  8,13   16489
 373  Poison_II_(0:45)        special.png  5,13   16484

#           Spawn Eggs
# ID  NAME                   FILE         CORDS  DAMAGE
 383  Spawn_Creeper          special.png  0,9    50
 383  Spawn_Skeleton         special.png  1,9    51
 383  Spawn_Spider           special.png  2,9    52
 383  Spawn_Zombie           special.png  3,9    54
 383  Spawn_Slime            special.png  4,9    55
 383  Spawn_Ghast            special.png  0,10   56
 383  Spawn_Zombie_Pigmen    special.png  1,10   57
 383  Spawn_Enderman         special.png  2,10   58
 383  Spawn_Cave_Spider      special.png  3,10   59
 383  Spawn_Silverfish       special.png  4,10   60
 383  Spawn_Blaze            special.png  0,11   61
 383  Spawn_Magma_Cube       special.png  1,11   62
 383  Spawn_Bat              special.png  5,9    65
 383  Spawn_Witch            special.png  5,10   66
 383  Spawn_Pig              special.png  2,11   90
 383  Spawn_Sheep            special.png  3,11   91
 383  Spawn_Cow              special.png  4,11   92
 383  Spawn_Chicken          special.png  0,12   93
 383  Spawn_Squid            special.png  1,12   94
 383  Spawn_Wolf             special.png  2,12   95
 383  Spawn_Mooshroom        special.png  3,12   96
 383  Spawn_Villager         special.png  4,12   120

#           Groups
# NAME      ICON  ITEMS
# Column 1
~ Natural    2     2,3,12,24,128,44~1,13,82,79,80,78
~ Stone      1     1,4,48,67,44~3,139,140,98,109,44~5,44~0,45,108,44~4,101
~ Wood       5     17,5,53,134,135,136,126,47,85,107,20,102,30
~ NetherEnd  87    87,88,89,348,112,114,113,372,121,122
~ Ores       56    16,15,14,56,129,73,21,49,42,41,57,133,22,263~0,265,266,264,388
~ Special    54    46,52,58,54,130,61,23,25,84,116,379,380,138,146~0,321,389,323,324,330,355,65,96,390,397
~ Plants1    81    31~1,31~2,106,111,18,81,86,91,103,110
~ Plants2    6     295,361,362,6,296,338,37,38,39,40,32
~ Transport  328   66,27,28,328,342,343,333,329,398
~ Logic      331   331,76,356,69,70,72,131,77,144,33,29,123,137
~ Wool       35    35~0,35~8,35~7,35~15,35~14,35~12,35~1,35~4,35~5,35~13,35~11,35~3,35~9,35~10,35~2,35~6
~ Dye        351   351~15,351~7,351~8,351~0,351~1,351~3,351~14,351~11,351~10,351~2,351~4,351~12,351~6,351~5,351~13,351~9
# Column 2
~ TierWood   299   298,299,300,301,269,270,271,290,268
~ TierStone  303   302,303,304,305,273,274,275,291,272
~ TierIron   307   306,307,308,309,256,257,258,292,267
~ TierDiam   311   310,311,312,313,277,278,279,293,276
~ TierGold   315   314,315,316,317,284,285,286,294,283
~ Tools      261   50,261,262,259,346,359,345,347,395,358,325,326,327,335,384,385,386,387
~ Food       297   260,322,282,297,360,319,320,363,364,365,366,349,350,354,357,391,396,392,393,394,400
~ Items      318   280,281,318,337,336,353,339,340,332,376,377,382,381
~ Drops      341   344,288,334,287,352,289,367,375,341,368,369,370,371,378,399
~ Music      2257  2256,2257,2258,2259,2260,2261,2262,2263,2264,2265,2266
# New
~ Potion     373   373~0,373~16,373~32,373~8192,373~8193,373~8257,373~8225,373~8289,373~8194,373~8258,373~8226,373~8290,373~8195,373~8259,373~8197,373~8229,373~8201,373~8265,373~8233,373~8297,373~8196,373~8260,373~8228,373~8292,373~8200,373~8264,373~8202,373~8266,373~8204,373~8236,373~16384,373~16385,373~16499,373~16417,373~16481,373~16386,373~16450,373~16418,373~16482,373~16387,373~16451,373~16389,373~16421,373~16393,373~16457,373~16425,373~16489,373~16388,373~16452,373~16420,373~16484,373~16392,373~16456,373~16394,373~16458,373~16396,373~16428
~ Eggs       383   383~50,383~51,383~52,383~54,383~55,383~56,383~57,383~58,383~59,383~60,383~61,383~62,383~65,383~66,383~90,383~91,383~92,383~93,383~94,383~95,383~96,383~120

#            Enchantments
# EID  NAME                   MAX  ITEMS
+   0  Protection             4    298,299,300,301,302,303,304,305,306,307,308,309,310,311,312,313,314,315,316,317
+   1  Fire_Protection        4    298,299,300,301,302,303,304,305,306,307,308,309,310,311,312,313,314,315,316,317
+   2  Feather_Falling        4    301,305,309,313,317
+   3  Blast_Protection       4    298,299,300,301,302,303,304,305,306,307,308,309,310,311,312,313,314,315,316,317
+   4  Projectile_Protection  4    298,299,300,301,302,303,304,305,306,307,308,309,310,311,312,313,314,315,316,317
+   5  Respiration            3    298,302,306,310,314
+   6  Aqua_Affinity          1    298,302,306,310,314
+  16  Sharpness              5    268,272,267,276,283
+  17  Smite                  5    268,272,267,276,283
+  18  Bane_of_Arthropods     5    268,272,267,276,283
+  19  Knockback              2    268,272,267,276,283
+  20  Fire_Aspect            2    268,272,267,276,283
+  21  Looting                3    268,272,267,276,283
+  32  Efficiency             5    269,270,271,273,274,275,256,257,258,277,278,279,284,285,286
+  33  Silk_Touch             1    269,270,271,273,274,275,256,257,258,277,278,279,284,285,286
+  34  Unbreaking             3    269,270,271,273,274,275,256,257,258,277,278,279,284,285,286
+  35  Fortune                3    269,270,271,273,274,275,256,257,258,277,278,279,284,285,286
+  48  Power                  5    261
+  49  Punch                  2    261
+  50  Flame                  1    261
+  51  Infinity               1    261
"""


class ItemType (object):
    def __init__(self, id, name, imagefile=None, imagecoords=None, maxdamage=0, damagevalue=0, stacksize=64):
        self.id = id
        self.name = name
        self.imagefile = imagefile
        self.imagecoords = imagecoords
        self.maxdamage = maxdamage
        self.damagevalue = damagevalue
        self.stacksize = stacksize

    def __repr__(self):
        return "ItemType({0}, '{1}')".format(self.id, self.name)

    def __str__(self):
        return "ItemType {0}: {1}".format(self.id, self.name)


class Items (object):
    items_txt = items_txt

    def __init__(self, filename=None):
        if filename is None:
            items_txt = self.items_txt
        else:
            try:
                with file(filename) as f:
                    items_txt = f.read()
            except Exception, e:
                logger.info("Error reading items.txt: %s", e)
                logger.info("Using internal data.")
                items_txt = self.items_txt

        self.itemtypes = {}
        self.itemgroups = []

        for line in items_txt.split("\n"):
            try:
                line = line.strip()
                if len(line) == 0:
                    continue
                if line[0] == "#":  # comment
                    continue
                if line[0] == "+":  # enchantment
                    continue
                if line[0] == "~":  # category
                    fields = line.split()
                    name, icon, items = fields[1:4]
                    items = items.split(",")
                    self.itemgroups.append((name, icon, items))
                    continue

                stacksize = 64
                damagevalue = None
                maxdamage = 0

                fields = line.split()
                if len(fields) >= 4:
                    maxdamage = None
                    id, name, imagefile, imagecoords = fields[0:4]
                    if len(fields) > 4:
                        info = fields[4]
                        if info[0] == '(':
                            info = info[1:-1]
                        if info[0] == 'x':
                            stacksize = int(info[1:])
                        elif info[0] == '+':
                            maxdamage = int(info[1:])
                        else:
                            damagevalue = int(info)
                    id = int(id)
                    name = name.replace("_", " ")
                    imagecoords = imagecoords.split(",")

                    self.itemtypes[(id, damagevalue)] = ItemType(id, name, imagefile, imagecoords, maxdamage, damagevalue, stacksize)
            except Exception, e:
                print "Error reading line:", e
                print "Line: ", line
                print

        self.names = dict((item.name, item.id) for item in self.itemtypes.itervalues())

    def findItem(self, id=0, damage=None):
        item = self.itemtypes.get((id, damage))
        if item:
            return item

        item = self.itemtypes.get((id, None))
        if item:
            return item

        item = self.itemtypes.get((id, 0))
        if item:
            return item

        return ItemType(id, "Unknown Item {0}:{1}".format(id, damage), damagevalue=damage)
        #raise ItemNotFound, "Item {0}:{1} not found".format(id, damage)


class ItemNotFound(KeyError):
    pass

items = Items()

########NEW FILE########
__FILENAME__ = java
'''
Created on Jul 22, 2011

@author: Rio
'''

__all__ = ["MCJavaLevel"]

from cStringIO import StringIO
import gzip
from level import MCLevel
from logging import getLogger
from numpy import fromstring
import os
import re

log = getLogger(__name__)

class MCJavaLevel(MCLevel):
    def setBlockDataAt(self, *args):
        pass

    def blockDataAt(self, *args):
        return 0

    @property
    def Height(self):
        return self.Blocks.shape[2]

    @property
    def Length(self):
        return self.Blocks.shape[1]

    @property
    def Width(self):
        return self.Blocks.shape[0]

    def guessSize(self, data):
        Width = 64
        Length = 64
        Height = 64
        if data.shape[0] <= (32 * 32 * 64) * 2:
            log.warn(u"Can't guess the size of a {0} byte level".format(data.shape[0]))
            raise IOError("MCJavaLevel attempted for smaller than 64 blocks cubed")
        if data.shape[0] > (64 * 64 * 64) * 2:
            Width = 128
            Length = 128
            Height = 64
        if data.shape[0] > (128 * 128 * 64) * 2:
            Width = 256
            Length = 256
            Height = 64
        if data.shape[0] > (256 * 256 * 64) * 2:  # could also be 256*256*256
            Width = 512
            Length = 512
            Height = 64
        if data.shape[0] > 512 * 512 * 64 * 2:  # just to load shadowmarch castle
            Width = 512
            Length = 512
            Height = 256
        return Width, Length, Height

    @classmethod
    def _isDataLevel(cls, data):
        return (data[0] == 0x27 and
                data[1] == 0x1B and
                data[2] == 0xb7 and
                data[3] == 0x88)

    def __init__(self, filename, data):
        self.filename = filename
        if isinstance(data, basestring):
            data = fromstring(data, dtype='uint8')
        self.filedata = data

        # try to take x,z,y from the filename
        r = re.findall("\d+", os.path.basename(filename))
        if r and len(r) >= 3:
            (w, l, h) = map(int, r[-3:])
            if w * l * h > data.shape[0]:
                log.info("Not enough blocks for size " + str((w, l, h)))
                w, l, h = self.guessSize(data)
        else:
            w, l, h = self.guessSize(data)

        log.info(u"MCJavaLevel created for potential level of size " + str((w, l, h)))

        blockCount = h * l * w
        if blockCount > data.shape[0]:
            raise ValueError("Level file does not contain enough blocks! (size {s}) Try putting the size into the filename, e.g. server_level_{w}_{l}_{h}.dat".format(w=w, l=l, h=h, s=data.shape))

        blockOffset = data.shape[0] - blockCount
        blocks = data[blockOffset:blockOffset + blockCount]

        maxBlockType = 64  # maximum allowed in classic
        while max(blocks[-4096:]) > maxBlockType:
            # guess the block array by starting at the end of the file
            # and sliding the blockCount-sized window back until it
            # looks like every block has a valid blockNumber
            blockOffset -= 1
            blocks = data[blockOffset:blockOffset + blockCount]

            if blockOffset <= -data.shape[0]:
                raise IOError("Can't find a valid array of blocks <= #%d" % maxBlockType)

        self.Blocks = blocks
        self.blockOffset = blockOffset
        blocks.shape = (w, l, h)
        blocks.strides = (1, w, w * l)

    def saveInPlace(self):

        s = StringIO()
        g = gzip.GzipFile(fileobj=s, mode='wb')


        g.write(self.filedata.tostring())
        g.flush()
        g.close()

        try:
            os.rename(self.filename, self.filename + ".old")
        except Exception, e:
            pass

        try:
            with open(self.filename, 'wb') as f:
                f.write(s.getvalue())
        except Exception, e:
            log.info(u"Error while saving java level in place: {0}".format(e))
            try:
                os.remove(self.filename)
            except:
                pass
            os.rename(self.filename + ".old", self.filename)

        try:
            os.remove(self.filename + ".old")
        except Exception, e:
            pass


class MCSharpLevel(MCLevel):
    """ int magic = convert(data.readShort())
        logger.trace("Magic number: {}", magic)
        if (magic != 1874)
            throw new IOException("Only version 1 MCSharp levels supported (magic number was "+magic+")")

        int width = convert(data.readShort())
        int height = convert(data.readShort())
        int depth = convert(data.readShort())
        logger.trace("Width: {}", width)
        logger.trace("Depth: {}", depth)
        logger.trace("Height: {}", height)

        int spawnX = convert(data.readShort())
        int spawnY = convert(data.readShort())
        int spawnZ = convert(data.readShort())

        int spawnRotation = data.readUnsignedByte()
        int spawnPitch = data.readUnsignedByte()

        int visitRanks = data.readUnsignedByte()
        int buildRanks = data.readUnsignedByte()

        byte[][][] blocks = new byte[width][height][depth]
        int i = 0
        BlockManager manager = BlockManager.getBlockManager()
        for(int z = 0;z<depth;z++) {
            for(int y = 0;y<height;y++) {
                byte[] row = new byte[height]
                data.readFully(row)
                for(int x = 0;x<width;x++) {
                    blocks[x][y][z] = translateBlock(row[x])
                }
            }
        }

        lvl.setBlocks(blocks, new byte[width][height][depth], width, height, depth)
        lvl.setSpawnPosition(new Position(spawnX, spawnY, spawnZ))
        lvl.setSpawnRotation(new Rotation(spawnRotation, spawnPitch))
        lvl.setEnvironment(new Environment())

        return lvl
    }"""

########NEW FILE########
__FILENAME__ = level
'''
Created on Jul 22, 2011

@author: Rio
'''

import blockrotation
from box import BoundingBox
from collections import defaultdict
from entity import Entity, TileEntity
import itertools
from logging import getLogger
import materials
from math import floor
from mclevelbase import ChunkMalformed, ChunkNotPresent, exhaust
import nbt
from numpy import argmax, swapaxes, zeros, zeros_like
import os.path

log = getLogger(__name__)

def computeChunkHeightMap(materials, blocks, HeightMap=None):
    """Computes the HeightMap array for a chunk, which stores the lowest
    y-coordinate of each column where the sunlight is still at full strength.
    The HeightMap array is indexed z,x contrary to the blocks array which is x,z,y.

    If HeightMap is passed, fills it with the result and returns it. Otherwise, returns a
    new array.
    """

    lightAbsorption = materials.lightAbsorption[blocks]
    heights = extractHeights(lightAbsorption)
    heights = heights.swapaxes(0, 1)
    if HeightMap is None:
        return heights.astype('uint8')
    else:
        HeightMap[:] = heights
        return HeightMap


def extractHeights(array):
    """ Given an array of bytes shaped (x, z, y), return the coordinates of the highest
    non-zero value in each y-column into heightMap
    """

    # The fastest way I've found to do this is to make a boolean array with >0,
    # then turn it upside down with ::-1 and use argmax to get the _first_ nonzero
    # from each column.

    w, h = array.shape[:2]
    heightMap = zeros((w, h), 'int16')

    heights = argmax((array > 0)[..., ::-1], 2)
    heights = array.shape[2] - heights

    # if the entire column is air, argmax finds the first air block and the result is a top height column
    # top height columns won't ever have air in the top block so we can find air columns by checking for both
    heights[(array[..., -1] == 0) & (heights == array.shape[2])] = 0

    heightMap[:] = heights

    return heightMap


def getSlices(box, height):
    """ call this method to iterate through a large slice of the world by
        visiting each chunk and indexing its data with a subslice.

    this returns an iterator, which yields 3-tuples containing:
    +  a pair of chunk coordinates (cx, cz),
    +  a x,z,y triplet of slices that can be used to index the AnvilChunk's data arrays,
    +  a x,y,z triplet representing the relative location of this subslice within the requested world slice.

    Note the different order of the coordinates between the 'slices' triplet
    and the 'offset' triplet. x,z,y ordering is used only
    to index arrays, since it reflects the order of the blocks in memory.
    In all other places, including an entity's 'Pos', the order is x,y,z.
    """

    # when yielding slices of chunks on the edge of the box, adjust the
    # slices by an offset
    minxoff, minzoff = box.minx - (box.mincx << 4), box.minz - (box.mincz << 4)
    maxxoff, maxzoff = box.maxx - (box.maxcx << 4) + 16, box.maxz - (box.maxcz << 4) + 16

    newMinY = 0
    if box.miny < 0:
        newMinY = -box.miny
    miny = max(0, box.miny)
    maxy = min(height, box.maxy)

    for cx in range(box.mincx, box.maxcx):
        localMinX = 0
        localMaxX = 16
        if cx == box.mincx:
            localMinX = minxoff

        if cx == box.maxcx - 1:
            localMaxX = maxxoff
        newMinX = localMinX + (cx << 4) - box.minx

        for cz in range(box.mincz, box.maxcz):
            localMinZ = 0
            localMaxZ = 16
            if cz == box.mincz:
                localMinZ = minzoff
            if cz == box.maxcz - 1:
                localMaxZ = maxzoff
            newMinZ = localMinZ + (cz << 4) - box.minz
            slices, point = (
                (slice(localMinX, localMaxX), slice(localMinZ, localMaxZ), slice(miny, maxy)),
                (newMinX, newMinY, newMinZ)
            )

            yield (cx, cz), slices, point


class MCLevel(object):
    """ MCLevel is an abstract class providing many routines to the different level types,
    including a common copyEntitiesFrom built on class-specific routines, and
    a dummy getChunk/allChunks for the finite levels.

    MCLevel subclasses must have Width, Length, and Height attributes.  The first two are always zero for infinite levels.
    Subclasses must also have Blocks, and optionally Data and BlockLight.
    """

    ### common to Creative, Survival and Indev. these routines assume
    ### self has Width, Height, Length, and Blocks

    materials = materials.classicMaterials
    isInfinite = False

    root_tag = None

    Height = None
    Length = None
    Width = None

    players = ["Player"]
    dimNo = 0
    parentWorld = None
    world = None

    @classmethod
    def isLevel(cls, filename):
        """Tries to find out whether the given filename can be loaded
        by this class.  Returns True or False.

        Subclasses should implement _isLevel, _isDataLevel, or _isTagLevel.
        """
        if hasattr(cls, "_isLevel"):
            return cls._isLevel(filename)

        with file(filename) as f:
            data = f.read()

        if hasattr(cls, "_isDataLevel"):
            return cls._isDataLevel(data)

        if hasattr(cls, "_isTagLevel"):
            try:
                root_tag = nbt.load(filename, data)
            except:
                return False

            return cls._isTagLevel(root_tag)

        return False

    def getWorldBounds(self):
        return BoundingBox((0, 0, 0), self.size)

    @property
    def displayName(self):
        return os.path.basename(self.filename)

    @property
    def size(self):
        "Returns the level's dimensions as a tuple (X,Y,Z)"
        return self.Width, self.Height, self.Length

    @property
    def bounds(self):
        return BoundingBox((0, 0, 0), self.size)

    def close(self):
        pass

    # --- Entity Methods ---
    def addEntity(self, entityTag):
        pass

    def addEntities(self, entities):
        pass

    def tileEntityAt(self, x, y, z):
        return None

    def addTileEntity(self, entityTag):
        pass

    def getEntitiesInBox(self, box):
        return []

    def getTileEntitiesInBox(self, box):
        return []

    def removeEntitiesInBox(self, box):
        pass

    def removeTileEntitiesInBox(self, box):
        pass

    @property
    def chunkCount(self):
        return (self.Width + 15 >> 4) * (self.Length + 15 >> 4)

    @property
    def allChunks(self):
        """Returns a synthetic list of chunk positions (xPos, zPos), to fake
        being a chunked level format."""
        return itertools.product(xrange(0, self.Width + 15 >> 4), xrange(0, self.Length + 15 >> 4))

    def getChunks(self, chunks=None):
        """ pass a list of chunk coordinate tuples to get an iterator yielding
        AnvilChunks. pass nothing for an iterator of every chunk in the level.
        the chunks are automatically loaded."""
        if chunks is None:
            chunks = self.allChunks
        return (self.getChunk(cx, cz) for (cx, cz) in chunks if self.containsChunk(cx, cz))

    def _getFakeChunkEntities(self, cx, cz):
        """Returns Entities, TileEntities"""
        return nbt.TAG_List(), nbt.TAG_List()

    def getChunk(self, cx, cz):
        """Synthesize a FakeChunk object representing the chunk at the given
        position. Subclasses override fakeBlocksForChunk and fakeDataForChunk
        to fill in the chunk arrays"""

        f = FakeChunk()
        f.world = self
        f.chunkPosition = (cx, cz)

        f.Blocks = self.fakeBlocksForChunk(cx, cz)

        f.Data = self.fakeDataForChunk(cx, cz)

        whiteLight = zeros_like(f.Blocks)
        whiteLight[:] = 15

        f.BlockLight = whiteLight
        f.SkyLight = whiteLight

        f.Entities, f.TileEntities = self._getFakeChunkEntities(cx, cz)

        f.root_tag = nbt.TAG_Compound()

        return f

    def getAllChunkSlices(self):
        slices = (slice(None), slice(None), slice(None),)
        box = self.bounds
        x, y, z = box.origin

        for cpos in self.allChunks:
            xPos, zPos = cpos
            try:
                chunk = self.getChunk(xPos, zPos)
            except (ChunkMalformed, ChunkNotPresent):
                continue

            yield (chunk, slices, (xPos * 16 - x, 0, zPos * 16 - z))

    def _getSlices(self, box):
        if box == self.bounds:
            log.info("All chunks selected! Selecting %s chunks instead of %s", self.chunkCount, box.chunkCount)
            y = box.miny
            slices = slice(0, 16), slice(0, 16), slice(0, box.maxy)

            def getAllSlices():
                for cPos in self.allChunks:
                    x, z = cPos
                    x *= 16
                    z *= 16
                    x -= box.minx
                    z -= box.minz
                    yield cPos, slices, (x, y, z)
            return getAllSlices()
        else:
            return getSlices(box, self.Height)

    def getChunkSlices(self, box):
        return ((self.getChunk(*cPos), slices, point)
                for cPos, slices, point in self._getSlices(box)
                if self.containsChunk(*cPos))

    def containsPoint(self, x, y, z):
        return (x, y, z) in self.bounds

    def containsChunk(self, cx, cz):
        bounds = self.bounds
        return ((bounds.mincx <= cx < bounds.maxcx) and
                (bounds.mincz <= cz < bounds.maxcz))

    def fakeBlocksForChunk(self, cx, cz):
        # return a 16x16xH block array for rendering.  Alpha levels can
        # just return the chunk data.  other levels need to reorder the
        # indices and return a slice of the blocks.

        cxOff = cx << 4
        czOff = cz << 4
        b = self.Blocks[cxOff:cxOff + 16, czOff:czOff + 16, 0:self.Height, ]
        # (w, l, h) = b.shape
        # if w<16 or l<16:
        #    b = resize(b, (16,16,h) )
        return b

    def fakeDataForChunk(self, cx, cz):
        # Data is emulated for flexibility
        cxOff = cx << 4
        czOff = cz << 4

        if hasattr(self, "Data"):
            return self.Data[cxOff:cxOff + 16, czOff:czOff + 16, 0:self.Height, ]

        else:
            return zeros(shape=(16, 16, self.Height), dtype='uint8')

    # --- Block accessors ---
    def skylightAt(self, *args):
        return 15

    def setSkylightAt(self, *args):
        pass

    def setBlockDataAt(self, x, y, z, newdata):
        pass

    def blockDataAt(self, x, y, z):
        return 0

    def blockLightAt(self, x, y, z):
        return 15

    def blockAt(self, x, y, z):
        if (x, y, z) not in self.bounds:
            return 0
        return self.Blocks[x, z, y]

    def setBlockAt(self, x, y, z, blockID):
        if (x, y, z) not in self.bounds:
            return 0
        self.Blocks[x, z, y] = blockID

    # --- Fill and Replace ---

    from block_fill import fillBlocks, fillBlocksIter

    # --- Transformations ---
    def rotateLeft(self):
        self.Blocks = swapaxes(self.Blocks, 1, 0)[:, ::-1, :]  # x=z; z=-x
        pass

    def roll(self):
        self.Blocks = swapaxes(self.Blocks, 2, 0)[:, :, ::-1]  # x=y; y=-x
        pass

    def flipVertical(self):
        self.Blocks = self.Blocks[:, :, ::-1]  # y=-y
        pass

    def flipNorthSouth(self):
        self.Blocks = self.Blocks[::-1, :, :]  # x=-x
        pass

    def flipEastWest(self):
        self.Blocks = self.Blocks[:, ::-1, :]  # z=-z
        pass

    # --- Copying ---

    from block_copy import copyBlocksFrom, copyBlocksFromIter


    def saveInPlace(self):
        self.saveToFile(self.filename)

    # --- Player Methods ---
    def setPlayerPosition(self, pos, player="Player"):
        pass

    def getPlayerPosition(self, player="Player"):
        return 8, self.Height * 0.75, 8

    def getPlayerDimension(self, player="Player"):
        return 0

    def setPlayerDimension(self, d, player="Player"):
        return

    def setPlayerSpawnPosition(self, pos, player=None):
        pass

    def playerSpawnPosition(self, player=None):
        return self.getPlayerPosition()

    def setPlayerOrientation(self, yp, player="Player"):
        pass

    def getPlayerOrientation(self, player="Player"):
        return -45., 0.

    # --- Dummy Lighting Methods ---
    def generateLights(self, dirtyChunks=None):
        pass

    def generateLightsIter(self, dirtyChunks=None):
        yield 0


class EntityLevel(MCLevel):
    """Abstract subclass of MCLevel that adds default entity behavior"""

    def getEntitiesInBox(self, box):
        """Returns a list of references to entities in this chunk, whose positions are within box"""
        return [ent for ent in self.Entities if Entity.pos(ent) in box]

    def getTileEntitiesInBox(self, box):
        """Returns a list of references to tile entities in this chunk, whose positions are within box"""
        return [ent for ent in self.TileEntities if TileEntity.pos(ent) in box]

    def removeEntitiesInBox(self, box):

        newEnts = []
        for ent in self.Entities:
            if Entity.pos(ent) in box:
                continue
            newEnts.append(ent)

        entsRemoved = len(self.Entities) - len(newEnts)
        log.debug("Removed {0} entities".format(entsRemoved))

        self.Entities.value[:] = newEnts

        return entsRemoved

    def removeTileEntitiesInBox(self, box):

        if not hasattr(self, "TileEntities"):
            return
        newEnts = []
        for ent in self.TileEntities:
            if TileEntity.pos(ent) in box:
                continue
            newEnts.append(ent)

        entsRemoved = len(self.TileEntities) - len(newEnts)
        log.debug("Removed {0} tile entities".format(entsRemoved))

        self.TileEntities.value[:] = newEnts

        return entsRemoved

    def addEntities(self, entities):
        for e in entities:
            self.addEntity(e)

    def addEntity(self, entityTag):
        assert isinstance(entityTag, nbt.TAG_Compound)
        self.Entities.append(entityTag)
        self._fakeEntities = None

    def tileEntityAt(self, x, y, z):
        entities = []
        for entityTag in self.TileEntities:
            if TileEntity.pos(entityTag) == [x, y, z]:
                entities.append(entityTag)

        if len(entities) > 1:
            log.info("Multiple tile entities found: {0}".format(entities))
        if len(entities) == 0:
            return None

        return entities[0]

    def addTileEntity(self, tileEntityTag):
        assert isinstance(tileEntityTag, nbt.TAG_Compound)

        def differentPosition(a):

            return not ((tileEntityTag is a) or TileEntity.pos(a) == TileEntity.pos(tileEntityTag))

        self.TileEntities.value[:] = filter(differentPosition, self.TileEntities)

        self.TileEntities.append(tileEntityTag)
        self._fakeEntities = None

    _fakeEntities = None

    def _getFakeChunkEntities(self, cx, cz):
        """distribute entities into sublists based on fake chunk position
        _fakeEntities keys are (cx, cz) and values are (Entities, TileEntities)"""
        if self._fakeEntities is None:
            self._fakeEntities = defaultdict(lambda: (nbt.TAG_List(), nbt.TAG_List()))
            for i, e in enumerate((self.Entities, self.TileEntities)):
                for ent in e:
                    x, y, z = [Entity, TileEntity][i].pos(ent)
                    ecx, ecz = map(lambda x: (int(floor(x)) >> 4), (x, z))

                    self._fakeEntities[ecx, ecz][i].append(ent)

        return self._fakeEntities[cx, cz]


class ChunkBase(EntityLevel):
    dirty = False
    needsLighting = False

    chunkPosition = NotImplemented
    Blocks = Data = SkyLight = BlockLight = HeightMap = NotImplemented  # override these!

    Width = Length = 16

    @property
    def Height(self):
        return self.world.Height

    @property
    def bounds(self):
        cx, cz = self.chunkPosition
        return BoundingBox((cx << 4, 0, cz << 4), self.size)


    def chunkChanged(self, needsLighting=True):
        self.dirty = True
        self.needsLighting = needsLighting or self.needsLighting

    @property
    def materials(self):
        return self.world.materials


    def getChunkSlicesForBox(self, box):
        """
         Given a BoundingBox enclosing part of the world, return a smaller box enclosing the part of this chunk
         intersecting the given box, and a tuple of slices that can be used to select the corresponding parts
         of this chunk's block and data arrays.
        """
        bounds = self.bounds
        localBox = box.intersect(bounds)

        slices = (
            slice(localBox.minx - bounds.minx, localBox.maxx - bounds.minx),
            slice(localBox.minz - bounds.minz, localBox.maxz - bounds.minz),
            slice(localBox.miny - bounds.miny, localBox.maxy - bounds.miny),
        )
        return localBox, slices


class FakeChunk(ChunkBase):
    @property
    def HeightMap(self):
        if hasattr(self, "_heightMap"):
            return self._heightMap

        self._heightMap = computeChunkHeightMap(self.materials, self.Blocks)
        return self._heightMap


class LightedChunk(ChunkBase):
    def generateHeightMap(self):
        computeChunkHeightMap(self.materials, self.Blocks, self.HeightMap)

    def chunkChanged(self, calcLighting=True):
        """ You are required to call this function after you are done modifying
        the chunk. Pass False for calcLighting if you know your changes will
        not change any lights."""

        self.dirty = True
        self.needsLighting = calcLighting or self.needsLighting
        self.generateHeightMap()
        if calcLighting:
            self.genFastLights()

    def genFastLights(self):
        self.SkyLight[:] = 0
        if self.world.dimNo in (-1, 1):
            return  # no light in nether or the end

        blocks = self.Blocks
        la = self.world.materials.lightAbsorption
        skylight = self.SkyLight
        heightmap = self.HeightMap

        for x, z in itertools.product(xrange(16), xrange(16)):

            skylight[x, z, heightmap[z, x]:] = 15
            lv = 15
            for y in reversed(range(heightmap[z, x])):
                lv -= (la[blocks[x, z, y]] or 1)

                if lv <= 0:
                    break
                skylight[x, z, y] = lv

########NEW FILE########
__FILENAME__ = materials

from logging import getLogger
from numpy import zeros, rollaxis, indices
import traceback
from os.path import join
from collections import defaultdict
from pprint import pformat

import os

NOTEX = (0x90, 0xD0)

try:
	import yaml
except:
	yaml = None

log = getLogger(__file__)


class Block(object):
    """
    Value object representing an (id, data) pair.
    Provides elements of its parent material's block arrays.
    Blocks will have (name, ID, blockData, aka, color, brightness, opacity, blockTextures)
    """

    def __str__(self):
        return "<Block {name} ({id}:{data}) hasVariants:{ha}>".format(
            name=self.name, id=self.ID, data=self.blockData, ha=self.hasVariants)

    def __repr__(self):
        return str(self)

    def __cmp__(self, other):
        if not isinstance(other, Block):
            return -1
        key = lambda a: a and (a.ID, a.blockData)
        return cmp(key(self), key(other))

    hasVariants = False  # True if blockData defines additional blocktypes

    def __init__(self, materials, blockID, blockData=0):
        self.materials = materials
        self.ID = blockID
        self.blockData = blockData

    def __getattr__(self, attr):
        if attr in self.__dict__:
            return self.__dict__[attr]
        if attr == "name":
            r = self.materials.names[self.ID]
        else:
            r = getattr(self.materials, attr)[self.ID]
        if attr in ("name", "aka", "color", "type"):
            r = r[self.blockData]
        return r


class MCMaterials(object):
    defaultColor = (0xc9, 0x77, 0xf0, 0xff)
    defaultBrightness = 0
    defaultOpacity = 15
    defaultTexture = NOTEX
    defaultTex = [t // 16 for t in defaultTexture]

    def __init__(self, defaultName="Unused Block"):
        object.__init__(self)
        self.yamlDatas = []

        self.defaultName = defaultName

        self.blockTextures = zeros((256, 16, 6, 2), dtype='uint8')
        self.blockTextures[:] = self.defaultTexture
        self.names = [[defaultName] * 16 for i in range(256)]
        self.aka = [[""] * 16 for i in range(256)]

        self.type = [["NORMAL"] * 16] * 256
        self.blocksByType = defaultdict(list)
        self.allBlocks = []
        self.blocksByID = {}

        self.lightEmission = zeros(256, dtype='uint8')
        self.lightEmission[:] = self.defaultBrightness
        self.lightAbsorption = zeros(256, dtype='uint8')
        self.lightAbsorption[:] = self.defaultOpacity
        self.flatColors = zeros((256, 16, 4), dtype='uint8')
        self.flatColors[:] = self.defaultColor

        self.idStr = {}

        self.color = self.flatColors
        self.brightness = self.lightEmission
        self.opacity = self.lightAbsorption

        self.Air = self.addBlock(0,
            name="Air",
            texture=(0x80, 0xB0),
            opacity=0,
        )

    def __repr__(self):
        return "<MCMaterials ({0})>".format(self.name)

    @property
    def AllStairs(self):
        return [b for b in self.allBlocks if b.name.endswith("Stairs")]

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def __len__(self):
        return len(self.allBlocks)

    def __iter__(self):
        return iter(self.allBlocks)

    def __getitem__(self, key):
        """ Let's be magic. If we get a string, return the first block whose
            name matches exactly. If we get a (id, data) pair or an id, return
            that block. for example:

                level.materials[0]  # returns Air
                level.materials["Air"]  # also returns Air
                level.materials["Powered Rail"]  # returns Powered Rail
                level.materials["Lapis Lazuli Block"]  # in Classic

           """
        if isinstance(key, basestring):
            for b in self.allBlocks:
                if b.name == key:
                    return b
            raise KeyError("No blocks named: " + key)
        if isinstance(key, (tuple, list)):
            id, blockData = key
            return self.blockWithID(id, blockData)
        return self.blockWithID(key)

    def blocksMatching(self, name):
        name = name.lower()
        return [v for v in self.allBlocks if name in v.name.lower() or name in v.aka.lower()]

    def blockWithID(self, id, data=0):
        if (id, data) in self.blocksByID:
            return self.blocksByID[id, data]
        else:
            bl = Block(self, id, blockData=data)
            bl.hasVariants = True
            return bl

    def addYamlBlocksFromFile(self, filename):
        if yaml is None:
            return

        try:
            import pkg_resources

            f = pkg_resources.resource_stream(__name__, filename)
        except (ImportError, IOError):
            root = os.environ.get("PYMCLEVEL_YAML_ROOT", "pymclevel")  # fall back to cwd as last resort
            path = join(root, filename)

            log.exception("Failed to read %s using pkg_resources. Trying %s instead." % (filename, path))

            f = file(path)
        try:
            log.info(u"Loading block info from %s", f)
            blockyaml = yaml.load(f)
            self.addYamlBlocks(blockyaml)

        except Exception, e:
            log.warn(u"Exception while loading block info from %s: %s", f, e)
            traceback.print_exc()

    def addYamlBlocks(self, blockyaml):
        self.yamlDatas.append(blockyaml)
        for block in blockyaml['blocks']:
            try:
                self.addYamlBlock(block)
            except Exception, e:
                log.warn(u"Exception while parsing block: %s", e)
                traceback.print_exc()
                log.warn(u"Block definition: \n%s", pformat(block))

    def addYamlBlock(self, kw):
        blockID = kw['id']

        # xxx unused_yaml_properties variable unused; needed for
        #     documentation purpose of some sort?  -zothar
        #unused_yaml_properties = \
        #['explored',
        # # 'id',
        # # 'idStr',
        # # 'mapcolor',
        # # 'name',
        # # 'tex',
        # ### 'tex_data',
        # # 'tex_direction',
        # ### 'tex_direction_data',
        # 'tex_extra',
        # # 'type'
        # ]

        for val, data in kw.get('data', {0: {}}).items():
            datakw = dict(kw)
            datakw.update(data)
            idStr = datakw.get('idStr', "")
            tex = [t * 16 for t in datakw.get('tex', self.defaultTex)]
            texture = [tex] * 6
            texDirs = {
                "FORWARD": 5,
                "BACKWARD": 4,
                "LEFT": 1,
                "RIGHT": 0,
                "TOP": 2,
                "BOTTOM": 3,
            }
            for dirname, dirtex in datakw.get('tex_direction', {}).items():
                if dirname == "SIDES":
                    for dirname in ("LEFT", "RIGHT"):
                        texture[texDirs[dirname]] = [t * 16 for t in dirtex]
                if dirname in texDirs:
                    texture[texDirs[dirname]] = [t * 16 for t in dirtex]
            datakw['texture'] = texture
            # print datakw
            block = self.addBlock(blockID, val, **datakw)
            block.yaml = datakw
            if idStr not in self.idStr:
                self.idStr[idStr] = block

        tex_direction_data = kw.get('tex_direction_data')
        if tex_direction_data:
            texture = datakw['texture']
            # X+0, X-1, Y+, Y-, Z+b, Z-f
            texDirMap = {
                "NORTH": 0,
                "EAST": 1,
                "SOUTH": 2,
                "WEST": 3,
            }

            def rot90cw():
                rot = (5, 0, 2, 3, 4, 1)
                texture[:] = [texture[r] for r in rot]

            for data, dir in tex_direction_data.items():
                for _i in range(texDirMap.get(dir, 0)):
                    rot90cw()
                self.blockTextures[blockID][data] = texture

    def addBlock(self, blockID, blockData=0, **kw):
        name = kw.pop('name', self.names[blockID][blockData])

        self.lightEmission[blockID] = kw.pop('brightness', self.defaultBrightness)
        self.lightAbsorption[blockID] = kw.pop('opacity', self.defaultOpacity)
        self.aka[blockID][blockData] = kw.pop('aka', "")
        type = kw.pop('type', 'NORMAL')

        color = kw.pop('mapcolor', self.flatColors[blockID, blockData])
        self.flatColors[blockID, (blockData or slice(None))] = (tuple(color) + (255,))[:4]

        texture = kw.pop('texture', None)

        if texture:
            self.blockTextures[blockID, (blockData or slice(None))] = texture

        if blockData is 0:
            self.names[blockID] = [name] * 16
            self.type[blockID] = [type] * 16
        else:
            self.names[blockID][blockData] = name
            self.type[blockID][blockData] = type

        block = Block(self, blockID, blockData)

        self.allBlocks.append(block)
        self.blocksByType[type].append(block)

        if (blockID, 0) in self.blocksByID:
            self.blocksByID[blockID, 0].hasVariants = True
            block.hasVariants = True

        self.blocksByID[blockID, blockData] = block

        return block

alphaMaterials = MCMaterials(defaultName="Future Block!")
alphaMaterials.name = "Alpha"
alphaMaterials.addYamlBlocksFromFile("minecraft.yaml")

# --- Special treatment for some blocks ---

HugeMushroomTypes = {
   "Northwest": 1,
   "North": 2,
   "Northeast": 3,
   "East": 6,
   "Southeast": 9,
   "South": 8,
   "Southwest": 7,
   "West": 4,
   "Stem": 10,
   "Top": 5,
}
from faces import FaceXDecreasing, FaceXIncreasing, FaceYIncreasing, FaceZDecreasing, FaceZIncreasing

Red = (0xD0, 0x70)
Brown = (0xE0, 0x70)
Pore = (0xE0, 0x80)
Stem = (0xD0, 0x80)


def defineShroomFaces(Shroom, id, name):
    for way, data in sorted(HugeMushroomTypes.items(), key=lambda a: a[1]):
        loway = way.lower()
        if way is "Stem":
            tex = [Stem, Stem, Pore, Pore, Stem, Stem]
        elif way is "Pore":
            tex = Pore
        else:
            tex = [Pore] * 6
            tex[FaceYIncreasing] = Shroom
            if "north" in loway:
                tex[FaceZDecreasing] = Shroom
            if "south" in loway:
                tex[FaceZIncreasing] = Shroom
            if "west" in loway:
                tex[FaceXDecreasing] = Shroom
            if "east" in loway:
                tex[FaceXIncreasing] = Shroom

        alphaMaterials.addBlock(id, blockData=data,
            name="Huge " + name + " Mushroom (" + way + ")",
            texture=tex,
            )

defineShroomFaces(Brown, 99, "Brown")
defineShroomFaces(Red, 100, "Red")

classicMaterials = MCMaterials(defaultName="Not present in Classic")
classicMaterials.name = "Classic"
classicMaterials.addYamlBlocksFromFile("classic.yaml")

indevMaterials = MCMaterials(defaultName="Not present in Indev")
indevMaterials.name = "Indev"
indevMaterials.addYamlBlocksFromFile("indev.yaml")

pocketMaterials = MCMaterials()
pocketMaterials.name = "Pocket"
pocketMaterials.addYamlBlocksFromFile("pocket.yaml")

# --- Static block defs ---

alphaMaterials.Stone = alphaMaterials[1, 0]
alphaMaterials.Grass = alphaMaterials[2, 0]
alphaMaterials.Dirt = alphaMaterials[3, 0]
alphaMaterials.Cobblestone = alphaMaterials[4, 0]
alphaMaterials.WoodPlanks = alphaMaterials[5, 0]
alphaMaterials.Sapling = alphaMaterials[6, 0]
alphaMaterials.SpruceSapling = alphaMaterials[6, 1]
alphaMaterials.BirchSapling = alphaMaterials[6, 2]
alphaMaterials.Bedrock = alphaMaterials[7, 0]
alphaMaterials.WaterActive = alphaMaterials[8, 0]
alphaMaterials.Water = alphaMaterials[9, 0]
alphaMaterials.LavaActive = alphaMaterials[10, 0]
alphaMaterials.Lava = alphaMaterials[11, 0]
alphaMaterials.Sand = alphaMaterials[12, 0]
alphaMaterials.Gravel = alphaMaterials[13, 0]
alphaMaterials.GoldOre = alphaMaterials[14, 0]
alphaMaterials.IronOre = alphaMaterials[15, 0]
alphaMaterials.CoalOre = alphaMaterials[16, 0]
alphaMaterials.Wood = alphaMaterials[17, 0]
alphaMaterials.Ironwood = alphaMaterials[17, 1]
alphaMaterials.BirchWood = alphaMaterials[17, 2]
alphaMaterials.Leaves = alphaMaterials[18, 0]
alphaMaterials.PineLeaves = alphaMaterials[18, 1]
alphaMaterials.BirchLeaves = alphaMaterials[18, 2]
alphaMaterials.JungleLeaves = alphaMaterials[18, 3]
alphaMaterials.LeavesPermanent = alphaMaterials[18, 4]
alphaMaterials.PineLeavesPermanent = alphaMaterials[18, 5]
alphaMaterials.BirchLeavesPermanent = alphaMaterials[18, 6]
alphaMaterials.JungleLeavesPermanent = alphaMaterials[18, 7]
alphaMaterials.LeavesDecaying = alphaMaterials[18, 8]
alphaMaterials.PineLeavesDecaying = alphaMaterials[18, 9]
alphaMaterials.BirchLeavesDecaying = alphaMaterials[18, 10]
alphaMaterials.JungleLeavesDecaying = alphaMaterials[18, 11]
alphaMaterials.Sponge = alphaMaterials[19, 0]
alphaMaterials.Glass = alphaMaterials[20, 0]

alphaMaterials.LapisLazuliOre = alphaMaterials[21, 0]
alphaMaterials.LapisLazuliBlock = alphaMaterials[22, 0]
alphaMaterials.Dispenser = alphaMaterials[23, 0]
alphaMaterials.Sandstone = alphaMaterials[24, 0]
alphaMaterials.NoteBlock = alphaMaterials[25, 0]
alphaMaterials.Bed = alphaMaterials[26, 0]
alphaMaterials.PoweredRail = alphaMaterials[27, 0]
alphaMaterials.DetectorRail = alphaMaterials[28, 0]
alphaMaterials.StickyPiston = alphaMaterials[29, 0]
alphaMaterials.Web = alphaMaterials[30, 0]
alphaMaterials.UnusedShrub = alphaMaterials[31, 0]
alphaMaterials.TallGrass = alphaMaterials[31, 1]
alphaMaterials.Shrub = alphaMaterials[31, 2]
alphaMaterials.DesertShrub2 = alphaMaterials[32, 0]
alphaMaterials.Piston = alphaMaterials[33, 0]
alphaMaterials.PistonHead = alphaMaterials[34, 0]
alphaMaterials.WhiteWool = alphaMaterials[35, 0]
alphaMaterials.OrangeWool = alphaMaterials[35, 1]
alphaMaterials.MagentaWool = alphaMaterials[35, 2]
alphaMaterials.LightBlueWool = alphaMaterials[35, 3]
alphaMaterials.YellowWool = alphaMaterials[35, 4]
alphaMaterials.LightGreenWool = alphaMaterials[35, 5]
alphaMaterials.PinkWool = alphaMaterials[35, 6]
alphaMaterials.GrayWool = alphaMaterials[35, 7]
alphaMaterials.LightGrayWool = alphaMaterials[35, 8]
alphaMaterials.CyanWool = alphaMaterials[35, 9]
alphaMaterials.PurpleWool = alphaMaterials[35, 10]
alphaMaterials.BlueWool = alphaMaterials[35, 11]
alphaMaterials.BrownWool = alphaMaterials[35, 12]
alphaMaterials.DarkGreenWool = alphaMaterials[35, 13]
alphaMaterials.RedWool = alphaMaterials[35, 14]
alphaMaterials.BlackWool = alphaMaterials[35, 15]

alphaMaterials.Flower = alphaMaterials[37, 0]
alphaMaterials.Rose = alphaMaterials[38, 0]
alphaMaterials.BrownMushroom = alphaMaterials[39, 0]
alphaMaterials.RedMushroom = alphaMaterials[40, 0]
alphaMaterials.BlockofGold = alphaMaterials[41, 0]
alphaMaterials.BlockofIron = alphaMaterials[42, 0]
alphaMaterials.DoubleStoneSlab = alphaMaterials[43, 0]
alphaMaterials.DoubleSandstoneSlab = alphaMaterials[43, 1]
alphaMaterials.DoubleWoodenSlab = alphaMaterials[43, 2]
alphaMaterials.DoubleCobblestoneSlab = alphaMaterials[43, 3]
alphaMaterials.DoubleBrickSlab = alphaMaterials[43, 4]
alphaMaterials.DoubleStoneBrickSlab = alphaMaterials[43, 5]
alphaMaterials.StoneSlab = alphaMaterials[44, 0]
alphaMaterials.SandstoneSlab = alphaMaterials[44, 1]
alphaMaterials.WoodenSlab = alphaMaterials[44, 2]
alphaMaterials.CobblestoneSlab = alphaMaterials[44, 3]
alphaMaterials.BrickSlab = alphaMaterials[44, 4]
alphaMaterials.StoneBrickSlab = alphaMaterials[44, 5]
alphaMaterials.Brick = alphaMaterials[45, 0]
alphaMaterials.TNT = alphaMaterials[46, 0]
alphaMaterials.Bookshelf = alphaMaterials[47, 0]
alphaMaterials.MossStone = alphaMaterials[48, 0]
alphaMaterials.Obsidian = alphaMaterials[49, 0]

alphaMaterials.Torch = alphaMaterials[50, 0]
alphaMaterials.Fire = alphaMaterials[51, 0]
alphaMaterials.MonsterSpawner = alphaMaterials[52, 0]
alphaMaterials.WoodenStairs = alphaMaterials[53, 0]
alphaMaterials.Chest = alphaMaterials[54, 0]
alphaMaterials.RedstoneWire = alphaMaterials[55, 0]
alphaMaterials.DiamondOre = alphaMaterials[56, 0]
alphaMaterials.BlockofDiamond = alphaMaterials[57, 0]
alphaMaterials.CraftingTable = alphaMaterials[58, 0]
alphaMaterials.Crops = alphaMaterials[59, 0]
alphaMaterials.Farmland = alphaMaterials[60, 0]
alphaMaterials.Furnace = alphaMaterials[61, 0]
alphaMaterials.LitFurnace = alphaMaterials[62, 0]
alphaMaterials.Sign = alphaMaterials[63, 0]
alphaMaterials.WoodenDoor = alphaMaterials[64, 0]
alphaMaterials.Ladder = alphaMaterials[65, 0]
alphaMaterials.Rail = alphaMaterials[66, 0]
alphaMaterials.StoneStairs = alphaMaterials[67, 0]
alphaMaterials.WallSign = alphaMaterials[68, 0]
alphaMaterials.Lever = alphaMaterials[69, 0]
alphaMaterials.StoneFloorPlate = alphaMaterials[70, 0]
alphaMaterials.IronDoor = alphaMaterials[71, 0]
alphaMaterials.WoodFloorPlate = alphaMaterials[72, 0]
alphaMaterials.RedstoneOre = alphaMaterials[73, 0]
alphaMaterials.RedstoneOreGlowing = alphaMaterials[74, 0]
alphaMaterials.RedstoneTorchOff = alphaMaterials[75, 0]
alphaMaterials.RedstoneTorchOn = alphaMaterials[76, 0]
alphaMaterials.Button = alphaMaterials[77, 0]
alphaMaterials.SnowLayer = alphaMaterials[78, 0]
alphaMaterials.Ice = alphaMaterials[79, 0]
alphaMaterials.Snow = alphaMaterials[80, 0]

alphaMaterials.Cactus = alphaMaterials[81, 0]
alphaMaterials.Clay = alphaMaterials[82, 0]
alphaMaterials.SugarCane = alphaMaterials[83, 0]
alphaMaterials.Jukebox = alphaMaterials[84, 0]
alphaMaterials.Fence = alphaMaterials[85, 0]
alphaMaterials.Pumpkin = alphaMaterials[86, 0]
alphaMaterials.Netherrack = alphaMaterials[87, 0]
alphaMaterials.SoulSand = alphaMaterials[88, 0]
alphaMaterials.Glowstone = alphaMaterials[89, 0]
alphaMaterials.NetherPortal = alphaMaterials[90, 0]
alphaMaterials.JackOLantern = alphaMaterials[91, 0]
alphaMaterials.Cake = alphaMaterials[92, 0]
alphaMaterials.RedstoneRepeaterOff = alphaMaterials[93, 0]
alphaMaterials.RedstoneRepeaterOn = alphaMaterials[94, 0]
alphaMaterials.AprilFoolsChest = alphaMaterials[95, 0]
alphaMaterials.Trapdoor = alphaMaterials[96, 0]

alphaMaterials.HiddenSilverfishStone = alphaMaterials[97, 0]
alphaMaterials.HiddenSilverfishCobblestone = alphaMaterials[97, 1]
alphaMaterials.HiddenSilverfishStoneBrick = alphaMaterials[97, 2]
alphaMaterials.StoneBricks = alphaMaterials[98, 0]
alphaMaterials.MossyStoneBricks = alphaMaterials[98, 1]
alphaMaterials.CrackedStoneBricks = alphaMaterials[98, 2]
alphaMaterials.HugeBrownMushroom = alphaMaterials[99, 0]
alphaMaterials.HugeRedMushroom = alphaMaterials[100, 0]
alphaMaterials.IronBars = alphaMaterials[101, 0]
alphaMaterials.GlassPane = alphaMaterials[102, 0]
alphaMaterials.Watermelon = alphaMaterials[103, 0]
alphaMaterials.PumpkinStem = alphaMaterials[104, 0]
alphaMaterials.MelonStem = alphaMaterials[105, 0]
alphaMaterials.Vines = alphaMaterials[106, 0]
alphaMaterials.FenceGate = alphaMaterials[107, 0]
alphaMaterials.BrickStairs = alphaMaterials[108, 0]
alphaMaterials.StoneBrickStairs = alphaMaterials[109, 0]
alphaMaterials.Mycelium = alphaMaterials[110, 0]
alphaMaterials.Lilypad = alphaMaterials[111, 0]
alphaMaterials.NetherBrick = alphaMaterials[112, 0]
alphaMaterials.NetherBrickFence = alphaMaterials[113, 0]
alphaMaterials.NetherBrickStairs = alphaMaterials[114, 0]
alphaMaterials.NetherWart = alphaMaterials[115, 0]

# --- Classic static block defs ---
classicMaterials.Stone = classicMaterials[1]
classicMaterials.Grass = classicMaterials[2]
classicMaterials.Dirt = classicMaterials[3]
classicMaterials.Cobblestone = classicMaterials[4]
classicMaterials.WoodPlanks = classicMaterials[5]
classicMaterials.Sapling = classicMaterials[6]
classicMaterials.Bedrock = classicMaterials[7]
classicMaterials.WaterActive = classicMaterials[8]
classicMaterials.Water = classicMaterials[9]
classicMaterials.LavaActive = classicMaterials[10]
classicMaterials.Lava = classicMaterials[11]
classicMaterials.Sand = classicMaterials[12]
classicMaterials.Gravel = classicMaterials[13]
classicMaterials.GoldOre = classicMaterials[14]
classicMaterials.IronOre = classicMaterials[15]
classicMaterials.CoalOre = classicMaterials[16]
classicMaterials.Wood = classicMaterials[17]
classicMaterials.Leaves = classicMaterials[18]
classicMaterials.Sponge = classicMaterials[19]
classicMaterials.Glass = classicMaterials[20]

classicMaterials.RedWool = classicMaterials[21]
classicMaterials.OrangeWool = classicMaterials[22]
classicMaterials.YellowWool = classicMaterials[23]
classicMaterials.LimeWool = classicMaterials[24]
classicMaterials.GreenWool = classicMaterials[25]
classicMaterials.AquaWool = classicMaterials[26]
classicMaterials.CyanWool = classicMaterials[27]
classicMaterials.BlueWool = classicMaterials[28]
classicMaterials.PurpleWool = classicMaterials[29]
classicMaterials.IndigoWool = classicMaterials[30]
classicMaterials.VioletWool = classicMaterials[31]
classicMaterials.MagentaWool = classicMaterials[32]
classicMaterials.PinkWool = classicMaterials[33]
classicMaterials.BlackWool = classicMaterials[34]
classicMaterials.GrayWool = classicMaterials[35]
classicMaterials.WhiteWool = classicMaterials[36]

classicMaterials.Flower = classicMaterials[37]
classicMaterials.Rose = classicMaterials[38]
classicMaterials.BrownMushroom = classicMaterials[39]
classicMaterials.RedMushroom = classicMaterials[40]
classicMaterials.BlockofGold = classicMaterials[41]
classicMaterials.BlockofIron = classicMaterials[42]
classicMaterials.DoubleStoneSlab = classicMaterials[43]
classicMaterials.StoneSlab = classicMaterials[44]
classicMaterials.Brick = classicMaterials[45]
classicMaterials.TNT = classicMaterials[46]
classicMaterials.Bookshelf = classicMaterials[47]
classicMaterials.MossStone = classicMaterials[48]
classicMaterials.Obsidian = classicMaterials[49]

# --- Indev static block defs ---
indevMaterials.Stone = indevMaterials[1]
indevMaterials.Grass = indevMaterials[2]
indevMaterials.Dirt = indevMaterials[3]
indevMaterials.Cobblestone = indevMaterials[4]
indevMaterials.WoodPlanks = indevMaterials[5]
indevMaterials.Sapling = indevMaterials[6]
indevMaterials.Bedrock = indevMaterials[7]
indevMaterials.WaterActive = indevMaterials[8]
indevMaterials.Water = indevMaterials[9]
indevMaterials.LavaActive = indevMaterials[10]
indevMaterials.Lava = indevMaterials[11]
indevMaterials.Sand = indevMaterials[12]
indevMaterials.Gravel = indevMaterials[13]
indevMaterials.GoldOre = indevMaterials[14]
indevMaterials.IronOre = indevMaterials[15]
indevMaterials.CoalOre = indevMaterials[16]
indevMaterials.Wood = indevMaterials[17]
indevMaterials.Leaves = indevMaterials[18]
indevMaterials.Sponge = indevMaterials[19]
indevMaterials.Glass = indevMaterials[20]

indevMaterials.RedWool = indevMaterials[21]
indevMaterials.OrangeWool = indevMaterials[22]
indevMaterials.YellowWool = indevMaterials[23]
indevMaterials.LimeWool = indevMaterials[24]
indevMaterials.GreenWool = indevMaterials[25]
indevMaterials.AquaWool = indevMaterials[26]
indevMaterials.CyanWool = indevMaterials[27]
indevMaterials.BlueWool = indevMaterials[28]
indevMaterials.PurpleWool = indevMaterials[29]
indevMaterials.IndigoWool = indevMaterials[30]
indevMaterials.VioletWool = indevMaterials[31]
indevMaterials.MagentaWool = indevMaterials[32]
indevMaterials.PinkWool = indevMaterials[33]
indevMaterials.BlackWool = indevMaterials[34]
indevMaterials.GrayWool = indevMaterials[35]
indevMaterials.WhiteWool = indevMaterials[36]

indevMaterials.Flower = indevMaterials[37]
indevMaterials.Rose = indevMaterials[38]
indevMaterials.BrownMushroom = indevMaterials[39]
indevMaterials.RedMushroom = indevMaterials[40]
indevMaterials.BlockofGold = indevMaterials[41]
indevMaterials.BlockofIron = indevMaterials[42]
indevMaterials.DoubleStoneSlab = indevMaterials[43]
indevMaterials.StoneSlab = indevMaterials[44]
indevMaterials.Brick = indevMaterials[45]
indevMaterials.TNT = indevMaterials[46]
indevMaterials.Bookshelf = indevMaterials[47]
indevMaterials.MossStone = indevMaterials[48]
indevMaterials.Obsidian = indevMaterials[49]

indevMaterials.Torch = indevMaterials[50, 0]
indevMaterials.Fire = indevMaterials[51, 0]
indevMaterials.InfiniteWater = indevMaterials[52, 0]
indevMaterials.InfiniteLava = indevMaterials[53, 0]
indevMaterials.Chest = indevMaterials[54, 0]
indevMaterials.Cog = indevMaterials[55, 0]
indevMaterials.DiamondOre = indevMaterials[56, 0]
indevMaterials.BlockofDiamond = indevMaterials[57, 0]
indevMaterials.CraftingTable = indevMaterials[58, 0]
indevMaterials.Crops = indevMaterials[59, 0]
indevMaterials.Farmland = indevMaterials[60, 0]
indevMaterials.Furnace = indevMaterials[61, 0]
indevMaterials.LitFurnace = indevMaterials[62, 0]

# --- Pocket static block defs ---

pocketMaterials.Air = pocketMaterials[0, 0]
pocketMaterials.Stone = pocketMaterials[1, 0]
pocketMaterials.Grass = pocketMaterials[2, 0]
pocketMaterials.Dirt = pocketMaterials[3, 0]
pocketMaterials.Cobblestone = pocketMaterials[4, 0]
pocketMaterials.WoodPlanks = pocketMaterials[5, 0]
pocketMaterials.Sapling = pocketMaterials[6, 0]
pocketMaterials.SpruceSapling = pocketMaterials[6, 1]
pocketMaterials.BirchSapling = pocketMaterials[6, 2]
pocketMaterials.Bedrock = pocketMaterials[7, 0]
pocketMaterials.Wateractive = pocketMaterials[8, 0]
pocketMaterials.Water = pocketMaterials[9, 0]
pocketMaterials.Lavaactive = pocketMaterials[10, 0]
pocketMaterials.Lava = pocketMaterials[11, 0]
pocketMaterials.Sand = pocketMaterials[12, 0]
pocketMaterials.Gravel = pocketMaterials[13, 0]
pocketMaterials.GoldOre = pocketMaterials[14, 0]
pocketMaterials.IronOre = pocketMaterials[15, 0]
pocketMaterials.CoalOre = pocketMaterials[16, 0]
pocketMaterials.Wood = pocketMaterials[17, 0]
pocketMaterials.PineWood = pocketMaterials[17, 1]
pocketMaterials.BirchWood = pocketMaterials[17, 2]
pocketMaterials.Leaves = pocketMaterials[18, 0]
pocketMaterials.Glass = pocketMaterials[20, 0]

pocketMaterials.LapisLazuliOre = pocketMaterials[21, 0]
pocketMaterials.LapisLazuliBlock = pocketMaterials[22, 0]
pocketMaterials.Sandstone = pocketMaterials[24, 0]
pocketMaterials.Bed = pocketMaterials[26, 0]
pocketMaterials.Web = pocketMaterials[30, 0]
pocketMaterials.UnusedShrub = pocketMaterials[31, 0]
pocketMaterials.TallGrass = pocketMaterials[31, 1]
pocketMaterials.Shrub = pocketMaterials[31, 2]
pocketMaterials.WhiteWool = pocketMaterials[35, 0]
pocketMaterials.OrangeWool = pocketMaterials[35, 1]
pocketMaterials.MagentaWool = pocketMaterials[35, 2]
pocketMaterials.LightBlueWool = pocketMaterials[35, 3]
pocketMaterials.YellowWool = pocketMaterials[35, 4]
pocketMaterials.LightGreenWool = pocketMaterials[35, 5]
pocketMaterials.PinkWool = pocketMaterials[35, 6]
pocketMaterials.GrayWool = pocketMaterials[35, 7]
pocketMaterials.LightGrayWool = pocketMaterials[35, 8]
pocketMaterials.CyanWool = pocketMaterials[35, 9]
pocketMaterials.PurpleWool = pocketMaterials[35, 10]
pocketMaterials.BlueWool = pocketMaterials[35, 11]
pocketMaterials.BrownWool = pocketMaterials[35, 12]
pocketMaterials.DarkGreenWool = pocketMaterials[35, 13]
pocketMaterials.RedWool = pocketMaterials[35, 14]
pocketMaterials.BlackWool = pocketMaterials[35, 15]
pocketMaterials.Flower = pocketMaterials[37, 0]
pocketMaterials.Rose = pocketMaterials[38, 0]
pocketMaterials.BrownMushroom = pocketMaterials[39, 0]
pocketMaterials.RedMushroom = pocketMaterials[40, 0]
pocketMaterials.BlockofGold = pocketMaterials[41, 0]
pocketMaterials.BlockofIron = pocketMaterials[42, 0]
pocketMaterials.DoubleStoneSlab = pocketMaterials[43, 0]
pocketMaterials.DoubleSandstoneSlab = pocketMaterials[43, 1]
pocketMaterials.DoubleWoodenSlab = pocketMaterials[43, 2]
pocketMaterials.DoubleCobblestoneSlab = pocketMaterials[43, 3]
pocketMaterials.DoubleBrickSlab = pocketMaterials[43, 4]
pocketMaterials.StoneSlab = pocketMaterials[44, 0]
pocketMaterials.SandstoneSlab = pocketMaterials[44, 1]
pocketMaterials.WoodenSlab = pocketMaterials[44, 2]
pocketMaterials.CobblestoneSlab = pocketMaterials[44, 3]
pocketMaterials.BrickSlab = pocketMaterials[44, 4]
pocketMaterials.Brick = pocketMaterials[45, 0]
pocketMaterials.TNT = pocketMaterials[46, 0]
pocketMaterials.Bookshelf = pocketMaterials[47, 0]
pocketMaterials.MossStone = pocketMaterials[48, 0]
pocketMaterials.Obsidian = pocketMaterials[49, 0]

pocketMaterials.Torch = pocketMaterials[50, 0]
pocketMaterials.Fire = pocketMaterials[51, 0]
pocketMaterials.WoodenStairs = pocketMaterials[53, 0]
pocketMaterials.Chest = pocketMaterials[54, 0]
pocketMaterials.DiamondOre = pocketMaterials[56, 0]
pocketMaterials.BlockofDiamond = pocketMaterials[57, 0]
pocketMaterials.CraftingTable = pocketMaterials[58, 0]
pocketMaterials.Crops = pocketMaterials[59, 0]
pocketMaterials.Farmland = pocketMaterials[60, 0]
pocketMaterials.Furnace = pocketMaterials[61, 0]
pocketMaterials.LitFurnace = pocketMaterials[62, 0]
pocketMaterials.WoodenDoor = pocketMaterials[64, 0]
pocketMaterials.Ladder = pocketMaterials[65, 0]
pocketMaterials.StoneStairs = pocketMaterials[67, 0]
pocketMaterials.IronDoor = pocketMaterials[71, 0]
pocketMaterials.RedstoneOre = pocketMaterials[73, 0]
pocketMaterials.RedstoneOreGlowing = pocketMaterials[74, 0]
pocketMaterials.SnowLayer = pocketMaterials[78, 0]
pocketMaterials.Ice = pocketMaterials[79, 0]

pocketMaterials.Snow = pocketMaterials[80, 0]
pocketMaterials.Cactus = pocketMaterials[81, 0]
pocketMaterials.Clay = pocketMaterials[82, 0]
pocketMaterials.SugarCane = pocketMaterials[83, 0]
pocketMaterials.Fence = pocketMaterials[85, 0]
pocketMaterials.Glowstone = pocketMaterials[89, 0]
pocketMaterials.InvisibleBedrock = pocketMaterials[95, 0]
pocketMaterials.Trapdoor = pocketMaterials[96, 0]

pocketMaterials.StoneBricks = pocketMaterials[98, 0]
pocketMaterials.GlassPane = pocketMaterials[102, 0]
pocketMaterials.Watermelon = pocketMaterials[103, 0]
pocketMaterials.MelonStem = pocketMaterials[105, 0]
pocketMaterials.FenceGate = pocketMaterials[107, 0]
pocketMaterials.BrickStairs = pocketMaterials[108, 0]

pocketMaterials.GlowingObsidian = pocketMaterials[246, 0]
pocketMaterials.NetherReactor = pocketMaterials[247, 0]
pocketMaterials.NetherReactorUsed = pocketMaterials[247, 1]

# print "\n".join(["pocketMaterials.{0} = pocketMaterials[{1},{2}]".format(
#                      b.name.replace(" ", "").replace("(","").replace(")",""),
#                      b.ID, b.blockData)
#                  for b in sorted(mats.pocketMaterials.allBlocks)])

_indices = rollaxis(indices((256, 16)), 0, 3)


def _filterTable(filters, unavailable, default=(0, 0)):
    # a filter table is a 256x16 table of (ID, data) pairs.
    table = zeros((256, 16, 2), dtype='uint8')
    table[:] = _indices
    for u in unavailable:
        try:
            if u[1] == 0:
                u = u[0]
        except TypeError:
            pass
        table[u] = default
    for f, t in filters:
        try:
            if f[1] == 0:
                f = f[0]
        except TypeError:
            pass
        table[f] = t
    return table

nullConversion = lambda b, d: (b, d)


def filterConversion(table):
    def convert(blocks, data):
        if data is None:
            data = 0
        t = table[blocks, data]
        return t[..., 0], t[..., 1]

    return convert


def guessFilterTable(matsFrom, matsTo):
    """ Returns a pair (filters, unavailable)
    filters is a list of (from, to) pairs;  from and to are (ID, data) pairs
    unavailable is a list of (ID, data) pairs in matsFrom not found in matsTo.

    Searches the 'name' and 'aka' fields to find matches.
    """
    filters = []
    unavailable = []
    toByName = dict(((b.name, b) for b in sorted(matsTo.allBlocks, reverse=True)))
    for fromBlock in matsFrom.allBlocks:
        block = toByName.get(fromBlock.name)
        if block is None:
            for b in matsTo.allBlocks:
                if b.name.startswith(fromBlock.name):
                    block = b
                    break
        if block is None:
            for b in matsTo.allBlocks:
                if fromBlock.name in b.name:
                    block = b
                    break
        if block is None:
            for b in matsTo.allBlocks:
                if fromBlock.name in b.aka:
                    block = b
                    break
        if block is None:
            if "Indigo Wool" == fromBlock.name:
                block = toByName.get("Purple Wool")
            elif "Violet Wool" == fromBlock.name:
                block = toByName.get("Purple Wool")

        if block:
            if block != fromBlock:
                filters.append(((fromBlock.ID, fromBlock.blockData), (block.ID, block.blockData)))
        else:
            unavailable.append((fromBlock.ID, fromBlock.blockData))

    return filters, unavailable

allMaterials = (alphaMaterials, classicMaterials, pocketMaterials, indevMaterials)

_conversionFuncs = {}


def conversionFunc(destMats, sourceMats):
    if destMats is sourceMats:
        return nullConversion
    func = _conversionFuncs.get((destMats, sourceMats))
    if func:
        return func

    filters, unavailable = guessFilterTable(sourceMats, destMats)
    log.debug("")
    log.debug("%s %s %s", sourceMats.name, "=>", destMats.name)
    for a, b in [(sourceMats.blockWithID(*a), destMats.blockWithID(*b)) for a, b in filters]:
        log.debug("{0:20}: \"{1}\"".format('"' + a.name + '"', b.name))

    log.debug("")
    log.debug("Missing blocks: %s", [sourceMats.blockWithID(*a).name for a in unavailable])

    table = _filterTable(filters, unavailable, (35, 0))
    func = filterConversion(table)
    _conversionFuncs[(destMats, sourceMats)] = func
    return func


def convertBlocks(destMats, sourceMats, blocks, blockData):
    if sourceMats == destMats:
        return blocks, blockData

    return conversionFunc(destMats, sourceMats)(blocks, blockData)

namedMaterials = dict((i.name, i) for i in allMaterials)

__all__ = "indevMaterials, pocketMaterials, alphaMaterials, classicMaterials, namedMaterials, MCMaterials".split(", ")

########NEW FILE########
__FILENAME__ = mce
#!/usr/bin/env python
import mclevelbase
import mclevel
import infiniteworld
import sys
import os
from box import BoundingBox, Vector
import numpy
from numpy import zeros, bincount
import logging
import itertools
import traceback
import shlex
import operator
import codecs

from math import floor
try:
    import readline  # if available, used by raw_input()
except:
    pass


class UsageError(RuntimeError):
    pass


class BlockMatchError(RuntimeError):
    pass


class PlayerNotFound(RuntimeError):
    pass


class mce(object):
    """
    Block commands:
       {commandPrefix}clone <sourceBox> <destPoint> [noair] [nowater]
       {commandPrefix}fill <blockType> [ <box> ]
       {commandPrefix}replace <blockType> [with] <newBlockType> [ <box> ]

       {commandPrefix}export <filename> <sourceBox>
       {commandPrefix}import <filename> <destPoint> [noair] [nowater]

       {commandPrefix}createChest <point> <item> [ <count> ]
       {commandPrefix}analyze

    Player commands:
       {commandPrefix}player [ <player> [ <point> ] ]
       {commandPrefix}spawn [ <point> ]

    Entity commands:
       {commandPrefix}removeEntities [ <EntityID> ]
       {commandPrefix}dumpSigns [ <filename> ]
       {commandPrefix}dumpChests [ <filename> ]

    Chunk commands:
       {commandPrefix}createChunks <box>
       {commandPrefix}deleteChunks <box>
       {commandPrefix}prune <box>
       {commandPrefix}relight [ <box> ]

    World commands:
       {commandPrefix}create <filename>
       {commandPrefix}dimension [ <dim> ]
       {commandPrefix}degrief
       {commandPrefix}time [ <time> ]
       {commandPrefix}worldsize
       {commandPrefix}heightmap <filename>
       {commandPrefix}randomseed [ <seed> ]
       {commandPrefix}gametype [ <player> [ <gametype> ] ]

    Editor commands:
       {commandPrefix}save
       {commandPrefix}reload
       {commandPrefix}load <filename> | <world number>
       {commandPrefix}execute <filename>
       {commandPrefix}quit

    Informational:
       {commandPrefix}blocks [ <block name> | <block ID> ]
       {commandPrefix}help [ <command> ]

    **IMPORTANT**
       {commandPrefix}box

       Type 'box' to learn how to specify points and areas.

    """
    random_seed = os.getenv('MCE_RANDOM_SEED', None)
    last_played = os.getenv("MCE_LAST_PLAYED", None)

    def commandUsage(self, command):
        " returns usage info for the named command - just give the docstring for the handler func "
        func = getattr(self, "_" + command)
        return func.__doc__

    commands = [
        "clone",
        "fill",
        "replace",

        "export",
        "execute",
        "import",

        "createchest",

        "player",
        "spawn",

        "removeentities",
        "dumpsigns",
        "dumpchests",

        "createchunks",
        "deletechunks",
        "prune",
        "relight",

        "create",
        "degrief",
        "time",
        "worldsize",
        "heightmap",
        "randomseed",
        "gametype",

        "save",
        "load",
        "reload",
        "dimension",
        "repair",

        "quit",
        "exit",

        "help",
        "blocks",
        "analyze",
        "region",

        "debug",
        "log",
        "box",
    ]
    debug = False
    needsSave = False

    def readInt(self, command):
        try:
            val = int(command.pop(0))
        except ValueError:
            raise UsageError("Cannot understand numeric input")
        return val

    def prettySplit(self, command):
        cmdstring = " ".join(command)

        lex = shlex.shlex(cmdstring)
        lex.whitespace_split = True
        lex.whitespace += "(),"

        command[:] = list(lex)

    def readBox(self, command):
        self.prettySplit(command)

        sourcePoint = self.readIntPoint(command)
        if command[0].lower() == "to":
            command.pop(0)
            sourcePoint2 = self.readIntPoint(command)
            sourceSize = sourcePoint2 - sourcePoint
        else:
            sourceSize = self.readIntPoint(command, isPoint=False)
        if len([p for p in sourceSize if p <= 0]):
            raise UsageError("Box size cannot be zero or negative")
        box = BoundingBox(sourcePoint, sourceSize)
        return box

    def readIntPoint(self, command, isPoint=True):
        point = self.readPoint(command, isPoint)
        point = map(int, map(floor, point))
        return Vector(*point)

    def readPoint(self, command, isPoint=True):
        self.prettySplit(command)
        try:
            word = command.pop(0)
            if isPoint and (word in self.level.players):
                x, y, z = self.level.getPlayerPosition(word)
                if len(command) and command[0].lower() == "delta":
                    command.pop(0)
                    try:
                        x += int(command.pop(0))
                        y += int(command.pop(0))
                        z += int(command.pop(0))

                    except ValueError:
                        raise UsageError("Error decoding point input (expected a number).")
                return x, y, z

        except IndexError:
            raise UsageError("Error decoding point input (expected more values).")

        try:
            try:
                x = float(word)
            except ValueError:
                if isPoint:
                    raise PlayerNotFound(word)
                raise
            y = float(command.pop(0))
            z = float(command.pop(0))
        except ValueError:
            raise UsageError("Error decoding point input (expected a number).")
        except IndexError:
            raise UsageError("Error decoding point input (expected more values).")

        return x, y, z

    def readBlockInfo(self, command):
        keyword = command.pop(0)

        matches = self.level.materials.blocksMatching(keyword)
        blockInfo = None

        if len(matches):
            if len(matches) == 1:
                blockInfo = matches[0]

            # eat up more words that possibly specify a block.  stop eating when 0 matching blocks.
            while len(command):
                newMatches = self.level.materials.blocksMatching(keyword + " " + command[0])

                if len(newMatches) == 1:
                    blockInfo = newMatches[0]
                if len(newMatches) > 0:
                    matches = newMatches
                    keyword = keyword + " " + command.pop(0)
                else:
                    break

        else:
            try:
                data = 0
                if ":" in keyword:
                    blockID, data = map(int, keyword.split(":"))
                else:
                    blockID = int(keyword)
                blockInfo = self.level.materials.blockWithID(blockID, data)

            except ValueError:
                blockInfo = None

        if blockInfo is None:
                print "Ambiguous block specifier: ", keyword
                if len(matches):
                    print "Matches: "
                    for m in matches:
                        if m == self.level.materials.defaultName:
                            continue
                        print "{0:3}:{1:<2} : {2}".format(m.ID, m.blockData, m.name)
                else:
                    print "No blocks matched."
                raise BlockMatchError

        return blockInfo

    def readBlocksToCopy(self, command):
        blocksToCopy = range(256)
        while len(command):
            word = command.pop()
            if word == "noair":
                blocksToCopy.remove(0)
            if word == "nowater":
                blocksToCopy.remove(8)
                blocksToCopy.remove(9)

        return blocksToCopy

    def _box(self, command):
        """
        Boxes:

    Many commands require a <box> as arguments. A box can be specified with
    a point and a size:
        (12, 5, 15), (5, 5, 5)

    or with two points, making sure to put the keyword "to" between them:
        (12, 5, 15) to (17, 10, 20)

    The commas and parentheses are not important.
    You may add them for improved readability.


        Points:

    Points and sizes are triplets of numbers ordered X Y Z.
    X is position north-south, increasing southward.
    Y is position up-down, increasing upward.
    Z is position east-west, increasing westward.


        Players:

    A player's name can be used as a point - it will use the
    position of the player's head. Use the keyword 'delta' after
    the name to specify a point near the player.

    Example:
       codewarrior delta 0 5 0

    This refers to a point 5 blocks above codewarrior's head.

    """
        raise UsageError

    def _debug(self, command):
        self.debug = not self.debug
        print "Debug", ("disabled", "enabled")[self.debug]

    def _log(self, command):
        """
    log [ <number> ]

    Get or set the log threshold. 0 logs everything; 50 only logs major errors.
    """
        if len(command):
            try:
                logging.getLogger().level = int(command[0])
            except ValueError:
                raise UsageError("Cannot understand numeric input.")
        else:
            print "Log level: {0}".format(logging.getLogger().level)

    def _clone(self, command):
        """
    clone <sourceBox> <destPoint> [noair] [nowater]

    Clone blocks in a cuboid starting at sourcePoint and extending for
    sourceSize blocks in each direction. Blocks and entities in the area
    are cloned at destPoint.
    """
        if len(command) == 0:
            self.printUsage("clone")
            return

        box = self.readBox(command)

        destPoint = self.readPoint(command)

        destPoint = map(int, map(floor, destPoint))
        blocksToCopy = self.readBlocksToCopy(command)

        tempSchematic = self.level.extractSchematic(box)
        self.level.copyBlocksFrom(tempSchematic, BoundingBox((0, 0, 0), box.origin), destPoint, blocksToCopy)

        self.needsSave = True
        print "Cloned 0 blocks."

    def _fill(self, command):
        """
    fill <blockType> [ <box> ]

    Fill blocks with blockType in a cuboid starting at point and
    extending for size blocks in each direction. Without a
    destination, fills the whole world. blockType and may be a
    number from 0-255 or a name listed by the 'blocks' command.
    """
        if len(command) == 0:
            self.printUsage("fill")
            return

        blockInfo = self.readBlockInfo(command)

        if len(command):
            box = self.readBox(command)
        else:
            box = None

        print "Filling with {0}".format(blockInfo.name)

        self.level.fillBlocks(box, blockInfo)

        self.needsSave = True
        print "Filled {0} blocks.".format("all" if box is None else box.volume)

    def _replace(self, command):
        """
    replace <blockType> [with] <newBlockType> [ <box> ]

    Replace all blockType blocks with newBlockType in a cuboid
    starting at point and extending for size blocks in
    each direction. Without a destination, replaces blocks over
    the whole world. blockType and newBlockType may be numbers
    from 0-255 or names listed by the 'blocks' command.
    """
        if len(command) == 0:
            self.printUsage("replace")
            return

        blockInfo = self.readBlockInfo(command)

        if command[0].lower() == "with":
            command.pop(0)
        newBlockInfo = self.readBlockInfo(command)

        if len(command):
            box = self.readBox(command)
        else:
            box = None

        print "Replacing {0} with {1}".format(blockInfo.name, newBlockInfo.name)

        self.level.fillBlocks(box, newBlockInfo, blocksToReplace=[blockInfo])

        self.needsSave = True
        print "Done."

    def _createchest(self, command):
        """
    createChest <point> <item> [ <count> ]

    Create a chest filled with the specified item.
    Stacks are 64 if count is not given.
    """
        point = map(lambda x: int(floor(float(x))), self.readPoint(command))
        itemID = self.readInt(command)
        count = 64
        if len(command):
            count = self.readInt(command)

        chest = mclevel.MCSchematic.chestWithItemID(itemID, count)
        self.level.copyBlocksFrom(chest, chest.bounds, point)
        self.needsSave = True

    def _analyze(self, command):
        """
        analyze

        Counts all of the block types in every chunk of the world.
        """
        blockCounts = zeros((4096,), 'uint64')
        sizeOnDisk = 0

        print "Analyzing {0} chunks...".format(self.level.chunkCount)
        # for input to bincount, create an array of uint16s by
        # shifting the data left and adding the blocks

        for i, cPos in enumerate(self.level.allChunks, 1):
            ch = self.level.getChunk(*cPos)
            btypes = numpy.array(ch.Data.ravel(), dtype='uint16')
            btypes <<= 8
            btypes += ch.Blocks.ravel()
            counts = bincount(btypes)

            blockCounts[:counts.shape[0]] += counts
            if i % 100 == 0:
                logging.info("Chunk {0}...".format(i))

        for blockID in range(256):
            block = self.level.materials.blockWithID(blockID, 0)
            if block.hasVariants:
                for data in range(16):
                    i = (data << 8) + blockID
                    if blockCounts[i]:
                        idstring = "({id}:{data})".format(id=blockID, data=data)

                        print "{idstring:9} {name:30}: {count:<10}".format(
                            idstring=idstring, name=self.level.materials.blockWithID(blockID, data).name, count=blockCounts[i])

            else:
                count = int(sum(blockCounts[(d << 8) + blockID] for d in range(16)))
                if count:
                    idstring = "({id})".format(id=blockID)
                    print "{idstring:9} {name:30}: {count:<10}".format(
                          idstring=idstring, name=self.level.materials.blockWithID(blockID, 0).name, count=count)

        self.needsSave = True

    def _export(self, command):
        """
    export <filename> <sourceBox>

    Exports blocks in the specified region to a file in schematic format.
    This file can be imported with mce or MCEdit.
    """
        if len(command) == 0:
            self.printUsage("export")
            return

        filename = command.pop(0)
        box = self.readBox(command)

        tempSchematic = self.level.extractSchematic(box)

        tempSchematic.saveToFile(filename)

        print "Exported {0} blocks.".format(tempSchematic.bounds.volume)

    def _import(self, command):
        """
    import <filename> <destPoint> [noair] [nowater]

    Imports a level or schematic into this world, beginning at destPoint.
    Supported formats include
    - Alpha single or multiplayer world folder containing level.dat,
    - Zipfile containing Alpha world folder,
    - Classic single-player .mine,
    - Classic multiplayer server_level.dat,
    - Indev .mclevel
    - Schematic from RedstoneSim, MCEdit, mce
    - .inv from INVEdit (appears as a chest)
    """
        if len(command) == 0:
            self.printUsage("import")
            return

        filename = command.pop(0)
        destPoint = self.readPoint(command)
        blocksToCopy = self.readBlocksToCopy(command)

        importLevel = mclevel.fromFile(filename)

        self.level.copyBlocksFrom(importLevel, importLevel.bounds, destPoint, blocksToCopy, create=True)

        self.needsSave = True
        print "Imported {0} blocks.".format(importLevel.bounds.volume)

    def _player(self, command):
        """
    player [ <player> [ <point> ] ]

    Move the named player to the specified point.
    Without a point, prints the named player's position.
    Without a player, prints all players and positions.

    In a single-player world, the player is named Player.
    """
        if len(command) == 0:
            print "Players: "
            for player in self.level.players:
                print "    {0}: {1}".format(player, self.level.getPlayerPosition(player))
            return

        player = command.pop(0)
        if len(command) == 0:
            print "Player {0}: {1}".format(player, self.level.getPlayerPosition(player))
            return

        point = self.readPoint(command)
        self.level.setPlayerPosition(point, player)

        self.needsSave = True
        print "Moved player {0} to {1}".format(player, point)

    def _spawn(self, command):
        """
    spawn [ <point> ]

    Move the world's spawn point.
    Without a point, prints the world's spawn point.
    """
        if len(command):
            point = self.readPoint(command)
            point = map(int, map(floor, point))

            self.level.setPlayerSpawnPosition(point)

            self.needsSave = True
            print "Moved spawn point to ", point
        else:
            print "Spawn point: ", self.level.playerSpawnPosition()

    def _dumpsigns(self, command):
        """
    dumpSigns [ <filename> ]

    Saves the text and location of every sign in the world to a text file.
    With no filename, saves signs to <worldname>.signs

    Output is newline-delimited. 5 lines per sign. Coordinates are
    on the first line, followed by four lines of sign text. For example:

        [229, 118, -15]
        "To boldy go
        where no man
        has gone
        before."

    Coordinates are ordered the same as point inputs:
        [North/South, Down/Up, East/West]

    """
        if len(command):
            filename = command[0]
        else:
            filename = self.level.displayName + ".signs"

        # It appears that Minecraft interprets the sign text as UTF-8,
        # so we should decode it as such too.
        decodeSignText = codecs.getdecoder('utf-8')
        # We happen to encode the output file in UTF-8 too, although
        # we could use another UTF encoding.  The '-sig' encoding puts
        # a signature at the start of the output file that tools such
        # as Microsoft Windows Notepad and Emacs understand to mean
        # the file has UTF-8 encoding.
        outFile = codecs.open(filename, "w", encoding='utf-8-sig')

        print "Dumping signs..."
        signCount = 0

        for i, cPos in enumerate(self.level.allChunks):
            try:
                chunk = self.level.getChunk(*cPos)
            except mclevelbase.ChunkMalformed:
                continue

            for tileEntity in chunk.TileEntities:
                if tileEntity["id"].value == "Sign":
                    signCount += 1

                    outFile.write(str(map(lambda x: tileEntity[x].value, "xyz")) + "\n")
                    for i in range(4):
                        signText = tileEntity["Text{0}".format(i + 1)].value
                        outFile.write(decodeSignText(signText)[0] + u"\n")

            if i % 100 == 0:
                print "Chunk {0}...".format(i)


        print "Dumped {0} signs to {1}".format(signCount, filename)

        outFile.close()

    def _region(self, command):
        """
    region [rx rz]

    List region files in this world.
    """
        level = self.level
        assert(isinstance(level, mclevel.MCInfdevOldLevel))
        assert level.version

        def getFreeSectors(rf):
            runs = []
            start = None
            count = 0
            for i, free in enumerate(rf.freeSectors):
                if free:
                    if start is None:
                        start = i
                        count = 1
                    else:
                        count += 1
                else:
                    if start is None:
                        pass
                    else:
                        runs.append((start, count))
                        start = None
                        count = 0

            return runs

        def printFreeSectors(runs):

            for i, (start, count) in enumerate(runs):
                if i % 4 == 3:
                    print ""
                print "{start:>6}+{count:<4}".format(**locals()),

            print ""

        if len(command):
            if len(command) > 1:
                rx, rz = map(int, command[:2])
                print "Calling allChunks to preload region files: %d chunks" % len(level.allChunks)
                rf = level.regionFiles.get((rx, rz))
                if rf is None:
                    print "Region {rx},{rz} not found.".format(**locals())
                    return

                print "Region {rx:6}, {rz:6}: {used}/{sectors} sectors".format(used=rf.usedSectors, sectors=rf.sectorCount)
                print "Offset Table:"
                for cx in range(32):
                    for cz in range(32):
                        if cz % 4 == 0:
                            print ""
                            print "{0:3}, {1:3}: ".format(cx, cz),
                        off = rf.getOffset(cx, cz)
                        sector, length = off >> 8, off & 0xff
                        print "{sector:>6}+{length:<2} ".format(**locals()),
                    print ""

                runs = getFreeSectors(rf)
                if len(runs):
                    print "Free sectors:",

                    printFreeSectors(runs)

            else:
                if command[0] == "free":
                    print "Calling allChunks to preload region files: %d chunks" % len(level.allChunks)
                    for (rx, rz), rf in level.regionFiles.iteritems():

                        runs = getFreeSectors(rf)
                        if len(runs):
                            print "R {0:3}, {1:3}:".format(rx, rz),
                            printFreeSectors(runs)

        else:
            print "Calling allChunks to preload region files: %d chunks" % len(level.allChunks)
            coords = (r for r in level.regionFiles)
            for i, (rx, rz) in enumerate(coords):
                print "({rx:6}, {rz:6}): {count}, ".format(count=level.regionFiles[rx, rz].chunkCount),
                if i % 5 == 4:
                    print ""

    def _repair(self, command):
        """
    repair

    Attempt to repair inconsistent region files.
    MAKE A BACKUP. WILL DELETE YOUR DATA.

    Scans for and repairs errors in region files:
        Deletes chunks whose sectors overlap with another chunk
        Rearranges chunks that are in the wrong slot in the offset table
        Deletes completely unreadable chunks

    Only usable with region-format saves.
    """
        if self.level.version:
            self.level.preloadRegions()
            for rf in self.level.regionFiles.itervalues():
                rf.repair()

    def _dumpchests(self, command):
        """
    dumpChests [ <filename> ]

    Saves the content and location of every chest in the world to a text file.
    With no filename, saves signs to <worldname>.chests

    Output is delimited by brackets and newlines. A set of coordinates in
    brackets begins a chest, followed by a line for each inventory slot.
    For example:

        [222, 51, 22]
        2 String
        3 String
        3 Iron bar

    Coordinates are ordered the same as point inputs:
        [North/South, Down/Up, East/West]

    """
        from items import items
        if len(command):
            filename = command[0]
        else:
            filename = self.level.displayName + ".chests"

        outFile = file(filename, "w")

        print "Dumping chests..."
        chestCount = 0

        for i, cPos in enumerate(self.level.allChunks):
            try:
                chunk = self.level.getChunk(*cPos)
            except mclevelbase.ChunkMalformed:
                continue

            for tileEntity in chunk.TileEntities:
                if tileEntity["id"].value == "Chest":
                    chestCount += 1

                    outFile.write(str(map(lambda x: tileEntity[x].value, "xyz")) + "\n")
                    itemsTag = tileEntity["Items"]
                    if len(itemsTag):
                        for itemTag in itemsTag:
                            try:
                                id = itemTag["id"].value
                                damage = itemTag["Damage"].value
                                item = items.findItem(id, damage)
                                itemname = item.name
                            except KeyError:
                                itemname = "Unknown Item {0}".format(itemTag)
                            except Exception, e:
                                itemname = repr(e)
                            outFile.write("{0} {1}\n".format(itemTag["Count"].value, itemname))
                    else:
                        outFile.write("Empty Chest\n")

            if i % 100 == 0:
                print "Chunk {0}...".format(i)


        print "Dumped {0} chests to {1}".format(chestCount, filename)

        outFile.close()

    def _removeentities(self, command):
        """
    removeEntities [ [except] [ <EntityID> [ <EntityID> ... ] ] ]

    Remove all entities matching one or more entity IDs.
    With the except keyword, removes all entities not
    matching one or more entity IDs.

    Without any IDs, removes all entities in the world,
    except for Paintings.

    Known Mob Entity IDs:
        Mob Monster Creeper Skeleton Spider Giant
        Zombie Slime Pig Sheep Cow Chicken

    Known Item Entity IDs: Item Arrow Snowball Painting

    Known Vehicle Entity IDs: Minecart Boat

    Known Dynamic Tile Entity IDs: PrimedTnt FallingSand
    """
        ENT_MATCHTYPE_ANY = 0
        ENT_MATCHTYPE_EXCEPT = 1
        ENT_MATCHTYPE_NONPAINTING = 2

        def match(entityID, matchType, matchWords):
            if ENT_MATCHTYPE_ANY == matchType:
                return entityID.lower() in matchWords
            elif ENT_MATCHTYPE_EXCEPT == matchType:
                return not (entityID.lower() in matchWords)
            else:
                # ENT_MATCHTYPE_EXCEPT == matchType
                return entityID != "Painting"

        removedEntities = {}
        match_words = []

        if len(command):
            if command[0].lower() == "except":
                command.pop(0)
                print "Removing all entities except ", command
                match_type = ENT_MATCHTYPE_EXCEPT
            else:
                print "Removing {0}...".format(", ".join(command))
                match_type = ENT_MATCHTYPE_ANY

            match_words = map(lambda x: x.lower(), command)

        else:
            print "Removing all entities except Painting..."
            match_type = ENT_MATCHTYPE_NONPAINTING

        for cx, cz in self.level.allChunks:
            chunk = self.level.getChunk(cx, cz)
            entitiesRemoved = 0

            for entity in list(chunk.Entities):
                entityID = entity["id"].value

                if match(entityID, match_type, match_words):
                    removedEntities[entityID] = removedEntities.get(entityID, 0) + 1

                    chunk.Entities.remove(entity)
                    entitiesRemoved += 1

            if entitiesRemoved:
                chunk.chunkChanged(False)


        if len(removedEntities) == 0:
            print "No entities to remove."
        else:
            print "Removed entities:"
            for entityID in sorted(removedEntities.keys()):
                print "  {0}: {1:6}".format(entityID, removedEntities[entityID])

        self.needsSave = True

    def _createchunks(self, command):
        """
    createChunks <box>

    Creates any chunks not present in the specified region.
    New chunks are filled with only air. New chunks are written
    to disk immediately.
    """
        if len(command) == 0:
            self.printUsage("createchunks")
            return

        box = self.readBox(command)

        chunksCreated = self.level.createChunksInBox(box)

        print "Created {0} chunks." .format(len(chunksCreated))

        self.needsSave = True

    def _deletechunks(self, command):
        """
    deleteChunks <box>

    Removes all chunks contained in the specified region.
    Chunks are deleted from disk immediately.
    """
        if len(command) == 0:
            self.printUsage("deletechunks")
            return

        box = self.readBox(command)

        deletedChunks = self.level.deleteChunksInBox(box)

        print "Deleted {0} chunks." .format(len(deletedChunks))

    def _prune(self, command):
        """
    prune <box>

    Removes all chunks not contained in the specified region. Useful for enforcing a finite map size.
    Chunks are deleted from disk immediately.
    """
        if len(command) == 0:
            self.printUsage("prune")
            return

        box = self.readBox(command)

        i = 0
        for cx, cz in list(self.level.allChunks):
            if cx < box.mincx or cx >= box.maxcx or cz < box.mincz or cz >= box.maxcz:
                self.level.deleteChunk(cx, cz)
                i += 1

        print "Pruned {0} chunks." .format(i)

    def _relight(self, command):
        """
    relight [ <box> ]

    Recalculates lights in the region specified. If omitted,
    recalculates the entire world.
    """
        if len(command):
            box = self.readBox(command)
            chunks = itertools.product(range(box.mincx, box.maxcx), range(box.mincz, box.maxcz))

        else:
            chunks = self.level.allChunks

        self.level.generateLights(chunks)

        print "Relit 0 chunks."
        self.needsSave = True

    def _create(self, command):
        """
    create [ <filename> ]

    Create and load a new Minecraft Alpha world. This world will have no
    chunks and a random terrain seed. If run from the shell, filename is not
    needed because you already specified a filename earlier in the command.
    For example:

        mce.py MyWorld create

    """
        if len(command) < 1:
            raise UsageError("Expected a filename")

        filename = command[0]
        if not os.path.exists(filename):
            os.mkdir(filename)

        if not os.path.isdir(filename):
            raise IOError("{0} already exists".format(filename))

        if mclevel.MCInfdevOldLevel.isLevel(filename):
            raise IOError("{0} is already a Minecraft Alpha world".format(filename))

        level = mclevel.MCInfdevOldLevel(filename, create=True)

        self.level = level

    def _degrief(self, command):
        """
    degrief [ <height> ]

    Reverse a few forms of griefing by removing
    Adminium, Obsidian, Fire, and Lava wherever
    they occur above the specified height.
    Without a height, uses height level 32.

    Removes natural surface lava.

    Also see removeEntities
    """
        box = self.level.bounds
        box = BoundingBox(box.origin + (0, 32, 0), box.size - (0, 32, 0))
        if len(command):
            try:
                box.miny = int(command[0])
            except ValueError:
                pass

        print "Removing grief matter and surface lava above height {0}...".format(box.miny)

        self.level.fillBlocks(box,
                              self.level.materials.Air,
                              blocksToReplace=[self.level.materials.Bedrock,
                                self.level.materials.Obsidian,
                                self.level.materials.Fire,
                                self.level.materials.LavaActive,
                                self.level.materials.Lava,
                                ]
                              )
        self.needsSave = True

    def _time(self, command):
        """
    time [time of day]

    Set or display the time of day. Acceptable values are "morning", "noon",
    "evening", "midnight", or a time of day such as 8:02, 12:30 PM, or 16:45.
    """
        ticks = self.level.Time
        timeOfDay = ticks % 24000
        ageInTicks = ticks - timeOfDay
        if len(command) == 0:

            days = ageInTicks / 24000
            hours = timeOfDay / 1000
            clockHours = (hours + 6) % 24

            ampm = ("AM", "PM")[clockHours > 11]

            minutes = (timeOfDay % 1000) / 60

            print "It is {0}:{1:02} {2} on Day {3}".format(clockHours % 12 or 12, minutes, ampm, days)
        else:
            times = {"morning": 6, "noon": 12, "evening": 18, "midnight": 24}
            word = command[0]
            minutes = 0

            if word in times:
                hours = times[word]
            else:
                try:
                    if ":" in word:
                        h, m = word.split(":")
                        hours = int(h)
                        minutes = int(m)
                    else:
                        hours = int(word)
                except Exception, e:
                    raise UsageError(("Cannot interpret time, ", e))

                if len(command) > 1:
                    if command[1].lower() == "pm":
                        hours += 12

            ticks = ageInTicks + hours * 1000 + minutes * 1000 / 60 - 6000
            if ticks < 0:
                ticks += 18000

            ampm = ("AM", "PM")[hours > 11 and hours < 24]
            print "Changed time to {0}:{1:02} {2}".format(hours % 12 or 12, minutes, ampm)
            self.level.Time = ticks
            self.needsSave = True

    def _randomseed(self, command):
        """
    randomseed [ <seed> ]

    Set or display the world's random seed, a 64-bit integer that uniquely
    defines the world's terrain.
    """
        if len(command):
            try:
                seed = long(command[0])
            except ValueError:
                raise UsageError("Expected a long integer.")

            self.level.RandomSeed = seed
            self.needsSave = True
        else:
            print "Random Seed: ", self.level.RandomSeed

    def _gametype(self, command):
        """
    gametype [ <player> [ <gametype> ] ]

    Set or display the player's game type, an integer that identifies whether
    their game is survival (0) or creative (1).  On single-player worlds, the
    player is just 'Player'.
    """
        if len(command) == 0:
            print "Players: "
            for player in self.level.players:
                print "    {0}: {1}".format(player, self.level.getPlayerGameType(player))
            return

        player = command.pop(0)
        if len(command) == 0:
            print "Player {0}: {1}".format(player, self.level.getPlayerGameType(player))
            return

        try:
            gametype = int(command[0])
        except ValueError:
            raise UsageError("Expected an integer.")

        self.level.setPlayerGameType(gametype, player)
        self.needsSave = True

    def _worldsize(self, command):
        """
    worldsize

    Computes and prints the dimensions of the world.  For infinite worlds,
    also prints the most negative corner.
    """
        bounds = self.level.bounds
        if isinstance(self.level, mclevel.MCInfdevOldLevel):
            print "\nWorld size: \n  {0[0]:7} north to south\n  {0[2]:7} east to west\n".format(bounds.size)
            print "Smallest and largest points: ({0[0]},{0[2]}), ({1[0]},{1[2]})".format(bounds.origin, bounds.maximum)

        else:
            print "\nWorld size: \n  {0[0]:7} wide\n  {0[1]:7} tall\n  {0[2]:7} long\n".format(bounds.size)

    def _heightmap(self, command):
        """
    heightmap <filename>

    Takes a png and imports it as the terrain starting at chunk 0,0.
    Data is internally converted to greyscale and scaled to the maximum height.
    The game will fill the terrain with trees and mineral deposits the next
    time you play the level.

    Please please please try out a small test image before using a big source.
    Using the levels tool to get a good heightmap is an art, not a science.
    A smaller map lets you experiment and get it right before having to blow
    all night generating the really big map.

    Requires the PIL library.
    """
        if len(command) == 0:
            self.printUsage("heightmap")
            return

        if not sys.stdin.isatty() or raw_input(
     "This will destroy a large portion of the map and may take a long time.  Did you really want to do this?"
     ).lower() in ("yes", "y", "1", "true"):

            from PIL import Image
            import datetime

            filename = command.pop(0)

            imgobj = Image.open(filename)

            greyimg = imgobj.convert("L")  # luminance
            del imgobj

            width, height = greyimg.size

            water_level = 64

            xchunks = (height + 15) / 16
            zchunks = (width + 15) / 16

            start = datetime.datetime.now()
            for cx in range(xchunks):
                for cz in range(zchunks):
                    try:
                        self.level.createChunk(cx, cz)
                    except:
                        pass
                    c = self.level.getChunk(cx, cz)

                    imgarray = numpy.asarray(greyimg.crop((cz * 16, cx * 16, cz * 16 + 16, cx * 16 + 16)))
                    imgarray = imgarray / 2  # scale to 0-127

                    for x in range(16):
                        for z in range(16):
                            if z + (cz * 16) < width - 1 and x + (cx * 16) < height - 1:
                                # world dimension X goes north-south
                                # first array axis goes up-down

                                h = imgarray[x, z]

                                c.Blocks[x, z, h + 1:] = 0  # air
                                c.Blocks[x, z, h:h + 1] = 2  # grass
                                c.Blocks[x, z, h - 4:h] = 3  # dirt
                                c.Blocks[x, z, :h - 4] = 1  # rock

                                if h < water_level:
                                    c.Blocks[x, z, h + 1:water_level] = 9  # water
                                if h < water_level + 2:
                                    c.Blocks[x, z, h - 2:h + 1] = 12  # sand if it's near water level

                                c.Blocks[x, z, 0] = 7  # bedrock

                    c.chunkChanged()
                    c.TerrainPopulated = False
                    # the quick lighting from chunkChanged has already lit this simple terrain completely
                    c.needsLighting = False

                logging.info("%s Just did chunk %d,%d" % (datetime.datetime.now().strftime("[%H:%M:%S]"), cx, cz))

            logging.info("Done with mapping!")
            self.needsSave = True
            stop = datetime.datetime.now()
            logging.info("Took %s." % str(stop - start))

            spawnz = width / 2
            spawnx = height / 2
            spawny = greyimg.getpixel((spawnx, spawnz))
            logging.info("You probably want to change your spawn point. I suggest {0}".format((spawnx, spawny, spawnz)))

    def _execute(self, command):
        """
    execute <filename>
    Execute all commands in a file and save.
    """
        if len(command) == 0:
            print "You must give the file with commands to execute"
        else:
            commandFile = open(command[0], "r")
            commandsFromFile = commandFile.readlines()
            for commandFromFile in commandsFromFile:
                print commandFromFile
                self.processCommand(commandFromFile)
            self._save("")

    def _quit(self, command):
        """
    quit [ yes | no ]

    Quits the program.
    Without 'yes' or 'no', prompts to save before quitting.

    In batch mode, an end of file automatically saves the level.
    """
        if len(command) == 0 or not (command[0].lower() in ("yes", "no")):
            if raw_input("Save before exit? ").lower() in ("yes", "y", "1", "true"):
                self._save(command)
                raise SystemExit
        if len(command) and command[0].lower == "yes":
            self._save(command)

        raise SystemExit

    def _exit(self, command):
        self._quit(command)

    def _save(self, command):
        if self.needsSave:
            self.level.generateLights()
            self.level.saveInPlace()
            self.needsSave = False

    def _load(self, command):
        """
    load [ <filename> | <world number> ]

    Loads another world, discarding all changes to this world.
    """
        if len(command) == 0:
            self.printUsage("load")
        self.loadWorld(command[0])

    def _reload(self, command):
        self.level = mclevel.fromFile(self.level.filename)

    def _dimension(self, command):
        """
    dimension [ <dim> ]

    Load another dimension, a sub-world of this level. Without options, lists
    all of the dimensions found in this world. <dim> can be a number or one of
    these keywords:
        nether, hell, slip: DIM-1
        earth, overworld, parent: parent world
        end: DIM1
    """

        if len(command):
            if command[0].lower() in ("earth", "overworld", "parent"):
                if self.level.parentWorld:
                    self.level = self.level.parentWorld
                    return
                else:
                    print "You are already on earth."
                    return

            elif command[0].lower() in ("hell", "nether", "slip"):
                dimNo = -1
            elif command[0].lower() == "end":
                dimNo = 1
            else:
                dimNo = self.readInt(command)

            if dimNo in self.level.dimensions:
                self.level = self.level.dimensions[dimNo]
                return

        if self.level.parentWorld:
            print u"Parent world: {0} ('dimension parent' to return)".format(self.level.parentWorld.displayName)

        if len(self.level.dimensions):
            print u"Dimensions in {0}:".format(self.level.displayName)
            for k in self.level.dimensions:
                print "{0}: {1}".format(k, infiniteworld.MCAlphaDimension.dimensionNames.get(k, "Unknown"))

    def _help(self, command):
        if len(command):
            self.printUsage(command[0])
        else:
            self.printUsage()

    def _blocks(self, command):
        """
    blocks [ <block name> | <block ID> ]

    Prints block IDs matching the name, or the name matching the ID.
    With nothing, prints a list of all blocks.
    """

        searchName = None
        if len(command):
            searchName = " ".join(command)
            try:
                searchNumber = int(searchName)
            except ValueError:
                searchNumber = None
                matches = self.level.materials.blocksMatching(searchName)
            else:
                matches = [b for b in self.level.materials.allBlocks if b.ID == searchNumber]
#                print "{0:3}: {1}".format(searchNumber, self.level.materials.names[searchNumber])
 #               return

        else:
            matches = self.level.materials.allBlocks

        print "{id:9} : {name} {aka}".format(id="(ID:data)", name="Block name", aka="[Other names]")
        for b in sorted(matches):
            idstring = "({ID}:{data})".format(ID=b.ID, data=b.blockData)
            aka = b.aka and " [{aka}]".format(aka=b.aka) or ""

            print "{idstring:9} : {name} {aka}".format(idstring=idstring, name=b.name, aka=aka)

    def printUsage(self, command=""):
        if command.lower() in self.commands:
            print "Usage: ", self.commandUsage(command.lower())
        else:
            print self.__doc__.format(commandPrefix=("", "mce.py <world> ")[not self.batchMode])

    def printUsageAndQuit(self):
        self.printUsage()
        raise SystemExit

    def loadWorld(self, world):

        worldpath = os.path.expanduser(world)
        if os.path.exists(worldpath):
            self.level = mclevel.fromFile(worldpath)
        else:
            self.level = mclevel.loadWorld(world)

    level = None

    batchMode = False

    def run(self):
        logging.basicConfig(format=u'%(levelname)s:%(message)s')
        logging.getLogger().level = logging.INFO

        sys.argv.pop(0)

        if len(sys.argv):
            world = sys.argv.pop(0)

            if world.lower() in ("-h", "--help"):
                self.printUsageAndQuit()

            if len(sys.argv) and sys.argv[0].lower() == "create":
                # accept the syntax, "mce world3 create"
                self._create([world])
                print "Created world {0}".format(world)

                sys.exit(0)
            else:
                self.loadWorld(world)
        else:
            self.batchMode = True
            self.printUsage()

            while True:
                try:
                    world = raw_input("Please enter world name or path to world folder: ")
                    self.loadWorld(world)
                except EOFError, e:
                    print "End of input."
                    raise SystemExit
                except Exception, e:
                    print "Cannot open {0}: {1}".format(world, e)
                else:
                    break

        if len(sys.argv):
            # process one command from command line
            try:
                self.processCommand(" ".join(sys.argv))
            except UsageError:
                self.printUsageAndQuit()
            self._save([])

        else:
            # process many commands on standard input, maybe interactively
            command = [""]
            self.batchMode = True
            while True:
                try:
                    command = raw_input(u"{0}> ".format(self.level.displayName))
                    print
                    self.processCommand(command)

                except EOFError, e:
                    print "End of file. Saving automatically."
                    self._save([])
                    raise SystemExit
                except Exception, e:
                    if self.debug:
                        traceback.print_exc()
                    print 'Exception during command: {0!r}'.format(e)
                    print "Use 'debug' to enable tracebacks."

                    # self.printUsage()

    def processCommand(self, command):
        command = command.strip()

        if len(command) == 0:
            return

        if command[0] == "#":
            return

        commandWords = command.split()

        keyword = commandWords.pop(0).lower()
        if not keyword in self.commands:
            matches = filter(lambda x: x.startswith(keyword), self.commands)
            if len(matches) == 1:
                keyword = matches[0]
            elif len(matches):
                print "Ambiguous command. Matches: "
                for k in matches:
                    print "  ", k
                return
            else:
                raise UsageError("Command {0} not recognized.".format(keyword))

        func = getattr(self, "_" + keyword)

        try:
            func(commandWords)
        except PlayerNotFound, e:
            print "Cannot find player {0}".format(e.args[0])
            self._player([])

        except UsageError, e:
            print e
            if self.debug:
                traceback.print_exc()
            self.printUsage(keyword)


def main(argv):
    profile = os.getenv("MCE_PROFILE", None)
    editor = mce()
    if profile:
        print "Profiling enabled"
        import cProfile
        cProfile.runctx('editor.run()', locals(), globals(), profile)
    else:
        editor.run()

    return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv))

########NEW FILE########
__FILENAME__ = mclevel
# -*- coding: utf-8 -*-
"""
MCLevel interfaces

Sample usage:

import mclevel

# Call mclevel.fromFile to identify and open any of these four file formats:
#
# Classic levels - gzipped serialized java objects.  Returns an instance of MCJavalevel
# Indev levels - gzipped NBT data in a single file.  Returns an MCIndevLevel
# Schematics - gzipped NBT data in a single file.  Returns an MCSchematic.
#   MCSchematics have the special method rotateLeft which will reorient torches, stairs, and other tiles appropriately.
# Alpha levels - world folder structure containing level.dat and chunk folders.  Single or Multiplayer.
#   Can accept a path to the world folder or a path to the level.dat.  Returns an MCInfdevOldLevel

# Load a Classic level.
level = mclevel.fromFile("server_level.dat");

# fromFile identified the file type and returned a MCJavaLevel.  MCJavaLevel doesn't actually know any java. It guessed the
# location of the Blocks array by starting at the end of the file and moving backwards until it only finds valid blocks.
# It also doesn't know the dimensions of the level.  This is why you have to tell them to MCEdit via the filename.
# This works here too:  If the file were 512 wide, 512 long, and 128 high, I'd have to name it "server_level_512_512_128.dat"
#
# This is one area for improvement.

# Classic and Indev levels have all of their blocks in one place.
blocks = level.Blocks

# Sand to glass.
blocks[blocks == level.materials.Sand.ID] = level.materials.Glass.ID

# Save the file with another name.  This only works for non-Alpha levels.
level.saveToFile("server_level_glassy.dat");

# Load an Alpha world
# Loading an Alpha world immediately scans the folder for chunk files.  This takes longer for large worlds.
ourworld = mclevel.fromFile("C:\\Minecraft\\OurWorld");

# Convenience method to load a numbered world from the saves folder.
world1 = mclevel.loadWorldNumber(1);

# Find out which chunks are present. Doing this will scan the chunk folders the
# first time it is used. If you already know where you want to be, skip to
# world1.getChunk(xPos, zPos)

chunkPositions = list(world1.allChunks)

# allChunks returns an iterator that yields a (xPos, zPos) tuple for each chunk
xPos, zPos = chunkPositions[0];

# retrieve an AnvilChunk object. this object will load and decompress
# the chunk as needed, and remember whether it needs to be saved or relighted

chunk = world1.getChunk(xPos, zPos)

### Access the data arrays of the chunk like so:
# Take note that the array is indexed x, z, y.  The last index corresponds to
# height or altitude.

blockType = chunk.Blocks[0,0,64]
chunk.Blocks[0,0,64] = 1

# Access the chunk's Entities and TileEntities as arrays of TAG_Compound as
# they appear in the save format.

# Entities usually have Pos, Health, and id
# TileEntities usually have tileX, tileY, tileZ, and id
# For more information, google "Chunk File Format"

for entity in chunk.Entities:
    if entity["id"].value == "Spider":
        entity["Health"].value = 50


# Accessing one byte at a time from the Blocks array is very slow in Python.
# To get around this, we have methods to access multiple bytes at once.
# The first technique is slicing. You can use slicing to restrict your access
# to certain depth levels, or to extract a column or a larger section from the
# array. Standard python slice notation is used.

# Set the top half of the array to 0. The : says to use the entire array along
# that dimension. The syntax []= indicates we are overwriting part of the array
chunk.Blocks[:,:,64:] = 0

# Using [] without =  creates a 'view' on part of the array.  This is not a
# copy, it is a reference to a portion of the original array.
midBlocks = chunk.Blocks[:,:,32:64]

# Here's a gotcha:  You can't just write 'midBlocks = 0' since it will replace
# the 'midBlocks' reference itself instead of accessing the array. Instead, do
# this to access and overwrite the array using []= syntax.
midBlocks[:] = 0


# The second is masking.  Using a comparison operator ( <, >, ==, etc )
# against the Blocks array will return a 'mask' that we can use to specify
# positions in the array.

# Create the mask from the result of the equality test.
fireBlocks = ( chunk.Blocks==world.materials.Fire.ID )

# Access Blocks using the mask to set elements. The syntax is the same as
# using []= with slices
chunk.Blocks[fireBlocks] = world.materials.Leaves.ID

# You can also combine mask arrays using logical operations (&, |, ^) and use
# the mask to access any other array of the same shape.
# Here we turn all trees into birch trees.

# Extract a mask from the Blocks array to find the locations of tree trunks.
# Or | it with another mask to find the locations of leaves.
# Use the combined mask to access the Data array and set those locations to birch

# Note that the Data, BlockLight, and SkyLight arrays have been
# unpacked from 4-bit arrays to numpy uint8 arrays. This makes them much easier
# to work with.

treeBlocks = ( chunk.Blocks == world.materials.Wood.ID )
treeBlocks |= ( chunk.Blocks == world.materials.Leaves.ID )
chunk.Data[treeBlocks] = 2 # birch


# The chunk doesn't know you've changed any of that data.  Call chunkChanged()
# to let it know. This will mark the chunk for lighting calculation,
# recompression, and writing to disk. It will also immediately recalculate the
# chunk's HeightMap and fill the SkyLight only with light falling straight down.
# These are relatively fast and were added here to aid MCEdit.

chunk.chunkChanged();

# To recalculate all of the dirty lights in the world, call generateLights
world.generateLights();


# Move the player and his spawn
world.setPlayerPosition( (0, 67, 0) ) # add 3 to make sure his head isn't in the ground.
world.setPlayerSpawnPosition( (0, 64, 0) )


# Save the level.dat and any chunks that have been marked for writing to disk
# This also compresses any chunks marked for recompression.
world.saveInPlace();


# Advanced use:
# The getChunkSlices method returns an iterator that returns slices of chunks within the specified range.
# the slices are returned as tuples of (chunk, slices, point)

# chunk:  The AnvilChunk object we're interested in.
# slices:  A 3-tuple of slice objects that can be used to index chunk's data arrays
# point:  A 3-tuple of floats representing the relative position of this subslice within the larger slice.
#
# Take caution:
# the point tuple is ordered (x,y,z) in accordance with the tuples used to initialize a bounding box
# however, the slices tuple is ordered (x,z,y) for easy indexing into the arrays.

# Here is an old version of MCInfdevOldLevel.fillBlocks in its entirety:

def fillBlocks(self, box, blockType, blockData = 0):
    chunkIterator = self.getChunkSlices(box)

    for (chunk, slices, point) in chunkIterator:
        chunk.Blocks[slices] = blockType
        chunk.Data[slices] = blockData
        chunk.chunkChanged();


Copyright 2010 David Rio Vierra
"""

from indev import MCIndevLevel
from infiniteworld import MCInfdevOldLevel
from java import MCJavaLevel
from logging import getLogger
from mclevelbase import saveFileDir
import nbt
from numpy import fromstring
import os
from pocket import PocketWorld
from schematic import INVEditChest, MCSchematic, ZipSchematic
import sys
import traceback

log = getLogger(__name__)

class LoadingError(RuntimeError):
    pass


def fromFile(filename, loadInfinite=True, readonly=True):
    ''' The preferred method for loading Minecraft levels of any type.
    pass False to loadInfinite if you'd rather not load infdev levels.
    '''
    log.info(u"Identifying " + filename)

    if not filename:
        raise IOError("File not found: " + filename)
    if not os.path.exists(filename):
        raise IOError("File not found: " + filename)

    if ZipSchematic._isLevel(filename):
        log.info("Zipfile found, attempting zipped infinite level")
        lev = ZipSchematic(filename)
        log.info("Detected zipped Infdev level")
        return lev

    if PocketWorld._isLevel(filename):
        return PocketWorld(filename)

    if MCInfdevOldLevel._isLevel(filename):
        log.info(u"Detected Infdev level.dat")
        if loadInfinite:
            return MCInfdevOldLevel(filename=filename, readonly=readonly)
        else:
            raise ValueError("Asked to load {0} which is an infinite level, loadInfinite was False".format(os.path.basename(filename)))

    if os.path.isdir(filename):
        raise ValueError("Folder {0} was not identified as a Minecraft level.".format(os.path.basename(filename)))

    f = file(filename, 'rb')
    rawdata = f.read()
    f.close()
    if len(rawdata) < 4:
        raise ValueError("{0} is too small! ({1}) ".format(filename, len(rawdata)))

    data = fromstring(rawdata, dtype='uint8')
    if not data.any():
        raise ValueError("{0} contains only zeroes. This file is damaged beyond repair.")

    if MCJavaLevel._isDataLevel(data):
        log.info(u"Detected Java-style level")
        lev = MCJavaLevel(filename, data)
        lev.compressed = False
        return lev

    #ungzdata = None
    compressed = True
    unzippedData = None
    try:
        unzippedData = nbt.gunzip(rawdata)
    except Exception, e:
        log.info(u"Exception during Gzip operation, assuming {0} uncompressed: {1!r}".format(filename, e))
        if unzippedData is None:
            compressed = False
            unzippedData = rawdata

    #data =
    data = unzippedData
    if MCJavaLevel._isDataLevel(data):
        log.info(u"Detected compressed Java-style level")
        lev = MCJavaLevel(filename, data)
        lev.compressed = compressed
        return lev

    try:
        root_tag = nbt.load(buf=data)

    except Exception, e:
        log.info(u"Error during NBT load: {0!r}".format(e))
        log.info(traceback.format_exc())
        log.info(u"Fallback: Detected compressed flat block array, yzx ordered ")
        try:
            lev = MCJavaLevel(filename, data)
            lev.compressed = compressed
            return lev
        except Exception, e2:
            raise LoadingError(("Multiple errors encountered", e, e2), sys.exc_info()[2])

    else:
        if MCIndevLevel._isTagLevel(root_tag):
            log.info(u"Detected Indev .mclevel")
            return MCIndevLevel(root_tag, filename)
        if MCSchematic._isTagLevel(root_tag):
            log.info(u"Detected Schematic.")
            return MCSchematic(root_tag=root_tag, filename=filename)

        if INVEditChest._isTagLevel(root_tag):
            log.info(u"Detected INVEdit inventory file")
            return INVEditChest(root_tag=root_tag, filename=filename)

    raise IOError("Cannot detect file type.")


def loadWorld(name):
    filename = os.path.join(saveFileDir, name)
    return fromFile(filename, True)


def loadWorldNumber(i):
    #deprecated
    filename = u"{0}{1}{2}{3}{1}".format(saveFileDir, os.sep, u"World", i)
    return fromFile(filename, True)

########NEW FILE########
__FILENAME__ = mclevelbase
'''
Created on Jul 22, 2011

@author: Rio
'''

from contextlib import contextmanager
from logging import getLogger
import sys
import os

log = getLogger(__name__)

@contextmanager
def notclosing(f):
    yield f


class PlayerNotFound(Exception):
    pass


class ChunkNotPresent(Exception):
    pass


class RegionMalformed(Exception):
    pass


class ChunkMalformed(ChunkNotPresent):
    pass


def exhaust(_iter):
    """Functions named ending in "Iter" return an iterable object that does
    long-running work and yields progress information on each call. exhaust()
    is used to implement the non-Iter equivalents"""
    i = None
    for i in _iter:
        pass
    return i



def win32_appdata():
    # try to use win32 api to get the AppData folder since python doesn't populate os.environ with unicode strings.

    try:
        import win32com.client
        objShell = win32com.client.Dispatch("WScript.Shell")
        return objShell.SpecialFolders("AppData")
    except Exception, e:
        #print "Error while getting AppData folder using WScript.Shell.SpecialFolders: {0!r}".format(e)
        try:
            from win32com.shell import shell, shellcon
            return shell.SHGetPathFromIDListEx(
                shell.SHGetSpecialFolderLocation(0, shellcon.CSIDL_APPDATA)
            )
        except Exception, e:
            #print "Error while getting AppData folder using SHGetSpecialFolderLocation: {0!r}".format(e)
            try:
                return os.environ['APPDATA'].decode(sys.getfilesystemencoding())
            except KeyError:
                return 'C:/'

if sys.platform == "win32":
    appDataDir = win32_appdata()
    minecraftDir = os.path.join(appDataDir, u".minecraft")
    appSupportDir = os.path.join(appDataDir, u"pymclevel")

elif sys.platform == "darwin":
    appDataDir = os.path.expanduser(u"~/Library/Application Support")
    minecraftDir = os.path.join(appDataDir, u"minecraft")
    appSupportDir = os.path.expanduser(u"~/Library/Application Support/pymclevel/")

else:
    appDataDir = os.path.expanduser(u"~")
    minecraftDir = os.path.expanduser(u"~/.minecraft")
    appSupportDir = os.path.expanduser(u"~/.pymclevel")

saveFileDir = os.path.join(minecraftDir, u"saves")



########NEW FILE########
__FILENAME__ = minecraft_server
import itertools
import logging
import os
from os.path import dirname, join, basename
import random
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib

import infiniteworld
from mclevelbase import appSupportDir, exhaust, ChunkNotPresent

log = logging.getLogger(__name__)

__author__ = 'Rio'

# Thank you, Stackoverflow
# http://stackoverflow.com/questions/377017/test-if-executable-exists-in-python
def which(program):
    def is_exe(f):
        return os.path.exists(f) and os.access(f, os.X_OK)

    fpath, _fname = os.path.split(program)
    if fpath:
        if is_exe(program):
            return program
    else:
        if sys.platform == "win32":
            if "SYSTEMROOT" in os.environ:
                root = os.environ["SYSTEMROOT"]
                exe_file = os.path.join(root, program)
                if is_exe(exe_file):
                    return exe_file
        if "PATH" in os.environ:
            for path in os.environ["PATH"].split(os.pathsep):
                exe_file = os.path.join(path, program)
                if is_exe(exe_file):
                    return exe_file

    return None


convert = lambda text: int(text) if text.isdigit() else text
alphanum_key = lambda key: [convert(c) for c in re.split('([0-9]+)', key)]


def sort_nicely(l):
    """ Sort the given list in the way that humans expect.
    """
    l.sort(key=alphanum_key)


class ServerJarStorage(object):
    defaultCacheDir = os.path.join(appSupportDir, u"ServerJarStorage")

    def __init__(self, cacheDir=None):
        if cacheDir is None:
            cacheDir = self.defaultCacheDir

        self.cacheDir = cacheDir

        if not os.path.exists(self.cacheDir):
            os.makedirs(self.cacheDir)
        readme = os.path.join(self.cacheDir, "README.TXT")
        if not os.path.exists(readme):
            with file(readme, "w") as f:
                f.write("""
About this folder:

This folder is used by MCEdit and pymclevel to store different versions of the
Minecraft Server to use for terrain generation. It should have one or more
subfolders, one for each version of the server. Each subfolder must hold at
least one file named minecraft_server.jar, and the subfolder's name should
have the server's version plus the names of any installed mods.

There may already be a subfolder here (for example, "Beta 1.7.3") if you have
used the Chunk Create feature in MCEdit to create chunks using the server.

Version numbers can be automatically detected. If you place one or more
minecraft_server.jar files in this folder, they will be placed automatically
into well-named subfolders the next time you run MCEdit. If a file's name
begins with "minecraft_server" and ends with ".jar", it will be detected in
this way.
""")

        self.reloadVersions()

    def reloadVersions(self):
        cacheDirList = os.listdir(self.cacheDir)
        self.versions = list(reversed(sorted([v for v in cacheDirList if os.path.exists(self.jarfileForVersion(v))], key=alphanum_key)))

        if MCServerChunkGenerator.javaExe:
            for f in cacheDirList:
                p = os.path.join(self.cacheDir, f)
                if f.startswith("minecraft_server") and f.endswith(".jar") and os.path.isfile(p):
                    print "Unclassified minecraft_server.jar found in cache dir. Discovering version number..."
                    self.cacheNewVersion(p)
                    os.remove(p)

        print "Minecraft_Server.jar storage initialized."
        print u"Each server is stored in a subdirectory of {0} named with the server's version number".format(self.cacheDir)

        print "Cached servers: ", self.versions

    def downloadCurrentServer(self):
        print "Downloading the latest Minecraft Server..."
        try:
            (filename, headers) = urllib.urlretrieve("http://www.minecraft.net/download/minecraft_server.jar")
        except Exception, e:
            print "Error downloading server: {0!r}".format(e)
            return

        self.cacheNewVersion(filename, allowDuplicate=False)

    def cacheNewVersion(self, filename, allowDuplicate=True):
        """ Finds the version number from the server jar at filename and copies
        it into the proper subfolder of the server jar cache folder"""

        version = MCServerChunkGenerator._serverVersionFromJarFile(filename)
        print "Found version ", version
        versionDir = os.path.join(self.cacheDir, version)

        i = 1
        newVersionDir = versionDir
        while os.path.exists(newVersionDir):
            if not allowDuplicate:
                return

            newVersionDir = versionDir + " (" + str(i) + ")"
            i += 1

        os.mkdir(newVersionDir)

        shutil.copy2(filename, os.path.join(newVersionDir, "minecraft_server.jar"))

        if version not in self.versions:
            self.versions.append(version)

    def jarfileForVersion(self, v):
        return os.path.join(self.cacheDir, v, "minecraft_server.jar").encode(sys.getfilesystemencoding())

    def checksumForVersion(self, v):
        jf = self.jarfileForVersion(v)
        with file(jf, "rb") as f:
            import hashlib
            return hashlib.md5(f.read()).hexdigest()

    broken_versions = ["Beta 1.9 Prerelease {0}".format(i) for i in (1, 2, 3)]

    @property
    def latestVersion(self):
        if len(self.versions) == 0:
            return None
        return max((v for v in self.versions if v not in self.broken_versions), key=alphanum_key)

    def getJarfile(self, version=None):
        if len(self.versions) == 0:
            print "No servers found in cache."
            self.downloadCurrentServer()

        version = version or self.latestVersion
        if version not in self.versions:
            return None
        return self.jarfileForVersion(version)


class JavaNotFound(RuntimeError):
    pass


class VersionNotFound(RuntimeError):
    pass


def readProperties(filename):
    if not os.path.exists(filename):
        return {}

    with file(filename) as f:
        properties = dict((line.split("=", 2) for line in (l.strip() for l in f) if not line.startswith("#")))

    return properties


def saveProperties(filename, properties):
    with file(filename, "w") as f:
        for k, v in properties.iteritems():
            f.write("{0}={1}\n".format(k, v))


def findJava():
    if sys.platform == "win32":
        javaExe = which("java.exe")
        if javaExe is None:
            KEY_NAME = "HKLM\SOFTWARE\JavaSoft\Java Runtime Environment"
            try:
                p = subprocess.Popen(["REG", "QUERY", KEY_NAME, "/v", "CurrentVersion"], stdout=subprocess.PIPE, universal_newlines=True)
                o, e = p.communicate()
                lines = o.split("\n")
                for l in lines:
                    l = l.strip()
                    if l.startswith("CurrentVersion"):
                        words = l.split(None, 2)
                        version = words[-1]
                        p = subprocess.Popen(["REG", "QUERY", KEY_NAME + "\\" + version, "/v", "JavaHome"], stdout=subprocess.PIPE, universal_newlines=True)
                        o, e = p.communicate()
                        lines = o.split("\n")
                        for l in lines:
                            l = l.strip()
                            if l.startswith("JavaHome"):
                                w = l.split(None, 2)
                                javaHome = w[-1]
                                javaExe = os.path.join(javaHome, "bin", "java.exe")
                                print "RegQuery: java.exe found at ", javaExe
                                break

            except Exception, e:
                print "Error while locating java.exe using the Registry: ", repr(e)
    else:
        javaExe = which("java")

    return javaExe


class MCServerChunkGenerator(object):
    """Generates chunks using minecraft_server.jar. Uses a ServerJarStorage to
    store different versions of minecraft_server.jar in an application support
    folder.

        from pymclevel import *

    Example usage:

        gen = MCServerChunkGenerator()  # with no arguments, use the newest
                                        # server version in the cache, or download
                                        # the newest one automatically
        level = loadWorldNamed("MyWorld")

        gen.generateChunkInLevel(level, 12, 24)


    Using an older version:

        gen = MCServerChunkGenerator("Beta 1.6.5")

    """
    defaultJarStorage = None

    javaExe = findJava()
    jarStorage = None
    tempWorldCache = {}

    def __init__(self, version=None, jarfile=None, jarStorage=None):

        self.jarStorage = jarStorage or self.getDefaultJarStorage()

        if self.javaExe is None:
            raise JavaNotFound("Could not find java. Please check that java is installed correctly. (Could not find java in your PATH environment variable.)")
        if jarfile is None:
            jarfile = self.jarStorage.getJarfile(version)
        if jarfile is None:
            raise VersionNotFound("Could not find minecraft_server.jar for version {0}. Please make sure that a minecraft_server.jar is placed under {1} in a subfolder named after the server's version number.".format(version or "(latest)", self.jarStorage.cacheDir))
        self.serverJarFile = jarfile
        self.serverVersion = version or self._serverVersion()

    @classmethod
    def getDefaultJarStorage(cls):
        if cls.defaultJarStorage is None:
            cls.defaultJarStorage = ServerJarStorage()
        return cls.defaultJarStorage

    @classmethod
    def clearWorldCache(cls):
        cls.tempWorldCache = {}

        for tempDir in os.listdir(cls.worldCacheDir):
            t = os.path.join(cls.worldCacheDir, tempDir)
            if os.path.isdir(t):
                shutil.rmtree(t)

    def createReadme(self):
        readme = os.path.join(self.worldCacheDir, "README.TXT")

        if not os.path.exists(readme):
            with file(readme, "w") as f:
                f.write("""
    About this folder:

    This folder is used by MCEdit and pymclevel to cache levels during terrain
    generation. Feel free to delete it for any reason.
    """)

    worldCacheDir = os.path.join(tempfile.gettempdir(), "pymclevel_MCServerChunkGenerator")

    def tempWorldForLevel(self, level):

        # tempDir = tempfile.mkdtemp("mclevel_servergen")
        tempDir = os.path.join(self.worldCacheDir, self.jarStorage.checksumForVersion(self.serverVersion), str(level.RandomSeed))
        propsFile = os.path.join(tempDir, "server.properties")
        properties = readProperties(propsFile)

        tempWorld = self.tempWorldCache.get((self.serverVersion, level.RandomSeed))

        if tempWorld is None:
            if not os.path.exists(tempDir):
                os.makedirs(tempDir)
                self.createReadme()

            worldName = "world"
            worldName = properties.setdefault("level-name", worldName)

            tempWorldDir = os.path.join(tempDir, worldName)
            tempWorld = infiniteworld.MCInfdevOldLevel(tempWorldDir, create=True, random_seed=level.RandomSeed)
            tempWorld.close()

            tempWorldRO = infiniteworld.MCInfdevOldLevel(tempWorldDir, readonly=True)

            self.tempWorldCache[self.serverVersion, level.RandomSeed] = tempWorldRO

        if level.dimNo == 0:
            properties["allow-nether"] = "false"
        else:
            tempWorld = tempWorld.getDimension(level.dimNo)

            properties["allow-nether"] = "true"

        properties["server-port"] = int(32767 + random.random() * 32700)
        saveProperties(propsFile, properties)

        return tempWorld, tempDir

    def generateAtPosition(self, tempWorld, tempDir, cx, cz):
        return exhaust(self.generateAtPositionIter(tempWorld, tempDir, cx, cz))

    def generateAtPositionIter(self, tempWorld, tempDir, cx, cz, simulate=False):
        tempWorldRW = infiniteworld.MCInfdevOldLevel(tempWorld.filename)
        tempWorldRW.setPlayerSpawnPosition((cx * 16, 64, cz * 16))
        tempWorldRW.saveInPlace()
        tempWorldRW.close()
        del tempWorldRW

        tempWorld.unload()

        startTime = time.time()
        proc = self.runServer(tempDir)
        while proc.poll() is None:
            line = proc.stderr.readline().strip()
            log.info(line)
            yield line

#            Forge and FML change stderr output, causing MCServerChunkGenerator to wait endlessly.
#
#            Vanilla:
#              2012-11-13 11:29:19 [INFO] Done (9.962s)!
#
#            Forge/FML:
#              2012-11-13 11:47:13 [INFO] [Minecraft] Done (8.020s)!

            if "[INFO]" in line and "Done" in line:
                if simulate:
                    duration = time.time() - startTime

                    simSeconds = max(8, int(duration) + 1)

                    for i in range(simSeconds):
                        # process tile ticks
                        yield "%2d/%2d: Simulating the world for a little bit..." % (i, simSeconds)
                        time.sleep(1)

                proc.stdin.write("stop\n")
                proc.wait()
                break
            if "FAILED TO BIND" in line:
                proc.kill()
                proc.wait()
                raise RuntimeError("Server failed to bind to port!")

        stdout, _ = proc.communicate()

        if "Could not reserve enough space" in stdout and not MCServerChunkGenerator.lowMemory:
            MCServerChunkGenerator.lowMemory = True
            for i in self.generateAtPositionIter(tempWorld, tempDir, cx, cz):
                yield i

        (tempWorld.parentWorld or tempWorld).loadLevelDat()  # reload version number

    def copyChunkAtPosition(self, tempWorld, level, cx, cz):
        if level.containsChunk(cx, cz):
            return
        try:
            tempChunkBytes = tempWorld._getChunkBytes(cx, cz)
        except ChunkNotPresent, e:
            raise ChunkNotPresent, "While generating a world in {0} using server {1} ({2!r})".format(tempWorld, self.serverJarFile, e), sys.exc_info()[2]

        level.worldFolder.saveChunk(cx, cz, tempChunkBytes)
        level._allChunks = None

    def generateChunkInLevel(self, level, cx, cz):
        assert isinstance(level, infiniteworld.MCInfdevOldLevel)

        tempWorld, tempDir = self.tempWorldForLevel(level)
        self.generateAtPosition(tempWorld, tempDir, cx, cz)
        self.copyChunkAtPosition(tempWorld, level, cx, cz)

    minRadius = 5
    maxRadius = 20

    def createLevel(self, level, box, simulate=False, **kw):
        return exhaust(self.createLevelIter(level, box, simulate, **kw))

    def createLevelIter(self, level, box, simulate=False, **kw):
        if isinstance(level, basestring):
            filename = level
            level = infiniteworld.MCInfdevOldLevel(filename, create=True, **kw)

        assert isinstance(level, infiniteworld.MCInfdevOldLevel)
        minRadius = self.minRadius

        genPositions = list(itertools.product(
                       xrange(box.mincx, box.maxcx, minRadius * 2),
                       xrange(box.mincz, box.maxcz, minRadius * 2)))

        for i, (cx, cz) in enumerate(genPositions):
            log.info("Generating at %s" % ((cx, cz),))
            parentDir = dirname(os.path.abspath(level.worldFolder.filename))
            propsFile = join(parentDir, "server.properties")
            props = readProperties(join(dirname(self.serverJarFile), "server.properties"))
            props["level-name"] = basename(level.worldFolder.filename)
            props["server-port"] = int(32767 + random.random() * 32700)
            saveProperties(propsFile, props)

            for p in self.generateAtPositionIter(level, parentDir, cx, cz, simulate):
                yield i, len(genPositions), p

        level.close()

    def generateChunksInLevel(self, level, chunks):
        return exhaust(self.generateChunksInLevelIter(level, chunks))

    def generateChunksInLevelIter(self, level, chunks, simulate=False):
        tempWorld, tempDir = self.tempWorldForLevel(level)

        startLength = len(chunks)
        minRadius = self.minRadius
        maxRadius = self.maxRadius
        chunks = set(chunks)

        while len(chunks):
            length = len(chunks)
            centercx, centercz = chunks.pop()
            chunks.add((centercx, centercz))
            # assume the generator always generates at least an 11x11 chunk square.
            centercx += minRadius
            centercz += minRadius

            # boxedChunks = [cPos for cPos in chunks if inBox(cPos)]

            print "Generating {0} chunks out of {1} starting from {2}".format("XXX", len(chunks), (centercx, centercz))
            yield startLength - len(chunks), startLength

            # chunks = [c for c in chunks if not inBox(c)]

            for p in self.generateAtPositionIter(tempWorld, tempDir, centercx, centercz, simulate):
                yield startLength - len(chunks), startLength, p

            i = 0
            for cx, cz in itertools.product(
                            xrange(centercx - maxRadius, centercx + maxRadius),
                            xrange(centercz - maxRadius, centercz + maxRadius)):
                if level.containsChunk(cx, cz):
                    chunks.discard((cx, cz))
                elif ((cx, cz) in chunks
                    and all(tempWorld.containsChunk(ncx, ncz) for ncx, ncz in itertools.product(xrange(cx-1, cx+2), xrange(cz-1, cz+2)))
                    ):
                    self.copyChunkAtPosition(tempWorld, level, cx, cz)
                    i += 1
                    chunks.discard((cx, cz))
                    yield startLength - len(chunks), startLength

            if length == len(chunks):
                print "No chunks were generated. Aborting."
                break

        level.saveInPlace()

    def runServer(self, startingDir):
        if isinstance(startingDir, unicode):
            startingDir = startingDir.encode(sys.getfilesystemencoding())

        return self._runServer(startingDir, self.serverJarFile)

    lowMemory = False

    @classmethod
    def _runServer(cls, startingDir, jarfile):
        log.info("Starting server %s in %s", jarfile, startingDir)
        if cls.lowMemory:
            memflags = []
        else:
            memflags = ["-Xmx1024M", "-Xms1024M", ]

        proc = subprocess.Popen([cls.javaExe, "-Djava.awt.headless=true"] + memflags + ["-jar", jarfile],
            executable=cls.javaExe,
            cwd=startingDir,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            )
        return proc

    def _serverVersion(self):
        return self._serverVersionFromJarFile(self.serverJarFile)

    @classmethod
    def _serverVersionFromJarFile(cls, jarfile):
        tempdir = tempfile.mkdtemp("mclevel_servergen")
        proc = cls._runServer(tempdir, jarfile)

        version = "Unknown"
        # out, err = proc.communicate()
        # for line in err.split("\n"):

        while proc.poll() is None:
            line = proc.stderr.readline()
            if "Preparing start region" in line:
                break
            if "Starting minecraft server version" in line:
                version = line.split("Starting minecraft server version")[1].strip()
                break

        if proc.returncode is None:
            try:
                proc.kill()
            except WindowsError:
                pass  # access denied, process already terminated

        proc.wait()
        shutil.rmtree(tempdir)
        if ";)" in version:
            version = version.replace(";)", "")  # Damnit, Jeb!
        # Versions like "0.2.1" are alphas, and versions like "1.0.0" without "Beta" are releases
        if version[0] == "0":
            version = "Alpha " + version
        try:
            if int(version[0]) > 0:
                version = "Release " + version
        except ValueError:
            pass

        return version

########NEW FILE########
__FILENAME__ = nbt

# vim:set sw=2 sts=2 ts=2:

"""
Named Binary Tag library. Serializes and deserializes TAG_* objects
to and from binary data. Load a Minecraft level by calling nbt.load().
Create your own TAG_* objects and set their values.
Save a TAG_* object to a file or StringIO object.

Read the test functions at the end of the file to get started.

This library requires Numpy.    Get it here:
http://new.scipy.org/download.html

Official NBT documentation is here:
http://www.minecraft.net/docs/NBT.txt


Copyright 2010 David Rio Vierra
"""
import collections
import gzip
import itertools
import logging
import struct
import zlib
from cStringIO import StringIO

import numpy
from numpy import array, zeros, fromstring


log = logging.getLogger(__name__)


class NBTFormatError(RuntimeError):
    pass


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
TAG_SHORT_ARRAY = 12


class TAG_Value(object):
    """Simple values. Subclasses override fmt to change the type and size.
    Subclasses may set data_type instead of overriding setValue for automatic data type coercion"""
    __slots__ = ('_name', '_value')

    def __init__(self, value=0, name=""):
        self.value = value
        self.name = name

    fmt = struct.Struct("b")
    tagID = NotImplemented
    data_type = NotImplemented

    _name = None
    _value = None

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, newVal):
        """Change the TAG's value. Data types are checked and coerced if needed."""
        self._value = self.data_type(newVal)

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, newVal):
        """Change the TAG's name. Coerced to a unicode."""
        self._name = unicode(newVal)

    @classmethod
    def load_from(cls, ctx):
        data = ctx.data[ctx.offset:]
        (value,) = cls.fmt.unpack_from(data)
        self = cls(value=value)
        ctx.offset += self.fmt.size
        return self

    def __repr__(self):
        return "<%s name=\"%s\" value=%r>" % (str(self.__class__.__name__), self.name, self.value)

    def write_tag(self, buf):
        buf.write(chr(self.tagID))

    def write_name(self, buf):
        if self.name is not None:
            write_string(self.name, buf)

    def write_value(self, buf):
        buf.write(self.fmt.pack(self.value))


class TAG_Byte(TAG_Value):
    __slots__ = ('_name', '_value')
    tagID = TAG_BYTE
    fmt = struct.Struct(">b")
    data_type = int


class TAG_Short(TAG_Value):
    __slots__ = ('_name', '_value')
    tagID = TAG_SHORT
    fmt = struct.Struct(">h")
    data_type = int


class TAG_Int(TAG_Value):
    __slots__ = ('_name', '_value')
    tagID = TAG_INT
    fmt = struct.Struct(">i")
    data_type = int


class TAG_Long(TAG_Value):
    __slots__ = ('_name', '_value')
    tagID = TAG_LONG
    fmt = struct.Struct(">q")
    data_type = long


class TAG_Float(TAG_Value):
    __slots__ = ('_name', '_value')
    tagID = TAG_FLOAT
    fmt = struct.Struct(">f")
    data_type = float


class TAG_Double(TAG_Value):
    __slots__ = ('_name', '_value')
    tagID = TAG_DOUBLE
    fmt = struct.Struct(">d")
    data_type = float


class TAG_Byte_Array(TAG_Value):
    """Like a string, but for binary data. Four length bytes instead of
    two. Value is a numpy array, and you can change its elements"""

    tagID = TAG_BYTE_ARRAY

    def __init__(self, value=None, name=""):
        if value is None:
            value = zeros(0, self.dtype)
        self.name = name
        self.value = value

    def __repr__(self):
        return "<%s name=%s length=%d>" % (self.__class__, self.name, len(self.value))

    __slots__ = ('_name', '_value')

    def data_type(self, value):
        return array(value, self.dtype)

    dtype = numpy.dtype('uint8')

    @classmethod
    def load_from(cls, ctx):
        data = ctx.data[ctx.offset:]
        (string_len,) = TAG_Int.fmt.unpack_from(data)
        value = fromstring(data[4:string_len * cls.dtype.itemsize + 4], cls.dtype)
        self = cls(value)
        ctx.offset += string_len * cls.dtype.itemsize + 4
        return self

    def write_value(self, buf):
        value_str = self.value.tostring()
        buf.write(struct.pack(">I%ds" % (len(value_str),), self.value.size, value_str))


class TAG_Int_Array(TAG_Byte_Array):
    """An array of big-endian 32-bit integers"""
    tagID = TAG_INT_ARRAY
    __slots__ = ('_name', '_value')
    dtype = numpy.dtype('>u4')



class TAG_Short_Array(TAG_Int_Array):
    """An array of big-endian 16-bit integers. Not official, but used by some mods."""
    tagID = TAG_SHORT_ARRAY
    __slots__ = ('_name', '_value')
    dtype = numpy.dtype('>u2')


class TAG_String(TAG_Value):
    """String in UTF-8
    The value parameter must be a 'unicode' or a UTF-8 encoded 'str'
    """

    tagID = TAG_STRING

    def __init__(self, value="", name=""):
        if name:
            self.name = name
        self.value = value

    _decodeCache = {}

    __slots__ = ('_name', '_value')

    def data_type(self, value):
        if isinstance(value, unicode):
            return value
        else:
            decoded = self._decodeCache.get(value)
            if decoded is None:
                decoded = value.decode('utf-8')
                self._decodeCache[value] = decoded

            return decoded


    @classmethod
    def load_from(cls, ctx):
        value = load_string(ctx)
        return cls(value)

    def write_value(self, buf):
        write_string(self._value, buf)

string_len_fmt = struct.Struct(">H")


def load_string(ctx):
    data = ctx.data[ctx.offset:]
    (string_len,) = string_len_fmt.unpack_from(data)

    value = data[2:string_len + 2].tostring()
    ctx.offset += string_len + 2
    return value


def write_string(string, buf):
    encoded = string.encode('utf-8')
    buf.write(struct.pack(">h%ds" % (len(encoded),), len(encoded), encoded))

#noinspection PyMissingConstructor


class TAG_Compound(TAG_Value, collections.MutableMapping):
    """A heterogenous list of named tags. Names must be unique within
    the TAG_Compound. Add tags to the compound using the subscript
    operator [].    This will automatically name the tags."""

    tagID = TAG_COMPOUND

    ALLOW_DUPLICATE_KEYS = False

    __slots__ = ('_name', '_value')

    def __init__(self, value=None, name=""):
        self.value = value or []
        self.name = name

    def __repr__(self):
        return "<%s name='%s' keys=%r>" % (str(self.__class__.__name__), self.name, self.keys())

    def data_type(self, val):
        for i in val:
            self.check_value(i)
        return list(val)

    def check_value(self, val):
        if not isinstance(val, TAG_Value):
            raise TypeError("Invalid type for TAG_Compound element: %s" % val.__class__.__name__)
        if not val.name:
            raise ValueError("Tag needs a name to be inserted into TAG_Compound: %s" % val)

    @classmethod
    def load_from(cls, ctx):
        self = cls()
        while ctx.offset < len(ctx.data):
            tag_type = ctx.data[ctx.offset]
            ctx.offset += 1

            if tag_type == 0:
                break

            tag_name = load_string(ctx)
            tag = tag_classes[tag_type].load_from(ctx)
            tag.name = tag_name

            self._value.append(tag)

        return self

    def save(self, filename_or_buf=None, compressed=True):
        """
        Save the TAG_Compound element to a file. Since this element is the root tag, it can be named.

        Pass a filename to save the data to a file. Pass a file-like object (with a read() method)
        to write the data to that object. Pass nothing to return the data as a string.
        """
        if self.name is None:
            self.name = ""

        buf = StringIO()
        self.write_tag(buf)
        self.write_name(buf)
        self.write_value(buf)
        data = buf.getvalue()

        if compressed:
            gzio = StringIO()
            gz = gzip.GzipFile(fileobj=gzio, mode='wb')
            gz.write(data)
            gz.close()
            data = gzio.getvalue()

        if filename_or_buf is None:
            return data

        if isinstance(filename_or_buf, basestring):
            f = file(filename_or_buf, "wb")
            f.write(data)
        else:
            filename_or_buf.write(data)

    def write_value(self, buf):
        for tag in self.value:
            tag.write_tag(buf)
            tag.write_name(buf)
            tag.write_value(buf)

        buf.write("\x00")

    # --- collection functions ---

    def __getitem__(self, key):
        # hits=filter(lambda x: x.name==key, self.value)
        # if(len(hits)): return hits[0]
        for tag in self.value:
            if tag.name == key:
                return tag
        raise KeyError("Key {0} not found in tag {1}".format(key, self))

    def __iter__(self):
        return itertools.imap(lambda x: x.name, self.value)

    def __contains__(self, key):
        return key in map(lambda x: x.name, self.value)

    def __len__(self):
        return self.value.__len__()

    def __setitem__(self, key, item):
        """Automatically wraps lists and tuples in a TAG_List, and wraps strings
        and unicodes in a TAG_String."""
        if isinstance(item, (list, tuple)):
            item = TAG_List(item)
        elif isinstance(item, basestring):
            item = TAG_String(item)

        item.name = key
        self.check_value(item)

        # remove any items already named "key".
        if not self.ALLOW_DUPLICATE_KEYS:
            self._value = filter(lambda x: x.name != key, self._value)

        self._value.append(item)

    def __delitem__(self, key):
        self.value.__delitem__(self.value.index(self[key]))

    def add(self, value):
        if value.name is None:
            raise ValueError("Tag %r must have a name." % value)

        self[value.name] = value

    def get_all(self, key):
        return [v for v in self._value if v.name == key]

class TAG_List(TAG_Value, collections.MutableSequence):
    """A homogenous list of unnamed data of a single TAG_* type.
    Once created, the type can only be changed by emptying the list
    and adding an element of the new type. If created with no arguments,
    returns a list of TAG_Compound

    Empty lists in the wild have been seen with type TAG_Byte"""

    tagID = 9

    def __init__(self, value=None, name="", list_type=TAG_BYTE):
        # can be created from a list of tags in value, with an optional
        # name, or created from raw tag data, or created with list_type
        # taken from a TAG class or instance

        self.name = name
        self.list_type = list_type
        self.value = value or []

    __slots__ = ('_name', '_value')


    def __repr__(self):
        return "<%s name='%s' list_type=%r length=%d>" % (self.__class__.__name__, self.name,
                                                          tag_classes[self.list_type],
                                                          len(self))

    def data_type(self, val):
        if val:
            self.list_type = val[0].tagID
        assert all([x.tagID == self.list_type for x in val])
        return list(val)



    @classmethod
    def load_from(cls, ctx):
        self = cls()
        self.list_type = ctx.data[ctx.offset]
        ctx.offset += 1

        (list_length,) = TAG_Int.fmt.unpack_from(ctx.data, ctx.offset)
        ctx.offset += TAG_Int.fmt.size

        for i in range(list_length):
            tag = tag_classes[self.list_type].load_from(ctx)
            self.append(tag)

        return self


    def write_value(self, buf):
       buf.write(chr(self.list_type))
       buf.write(TAG_Int.fmt.pack(len(self.value)))
       for i in self.value:
           i.write_value(buf)

    def check_tag(self, value):
        if value.tagID != self.list_type:
            raise TypeError("Invalid type %s for TAG_List(%s)" % (value.__class__, tag_classes[self.list_type]))

    # --- collection methods ---

    def __iter__(self):
        return iter(self.value)

    def __contains__(self, tag):
        return tag in self.value

    def __getitem__(self, index):
        return self.value[index]

    def __len__(self):
        return len(self.value)

    def __setitem__(self, index, value):
        if isinstance(index, slice):
            for tag in value:
                self.check_tag(tag)
        else:
            self.check_tag(value)

        self.value[index] = value

    def __delitem__(self, index):
        del self.value[index]

    def insert(self, index, value):
        if len(self) == 0:
            self.list_type = value.tagID
        else:
            self.check_tag(value)

        value.name = ""
        self.value.insert(index, value)


tag_classes = { c.tagID: c for c in (TAG_Byte, TAG_Short, TAG_Int, TAG_Long, TAG_Float, TAG_Double, TAG_String,
    TAG_Byte_Array, TAG_List, TAG_Compound, TAG_Int_Array, TAG_Short_Array) }



def gunzip(data):
    return gzip.GzipFile(fileobj=StringIO(data)).read()


def try_gunzip(data):
    try:
        data = gunzip(data)
    except IOError, zlib.error:
        pass
    return data


def load(filename="", buf=None):
    """
    Unserialize data from an NBT file and return the root TAG_Compound object. If filename is passed,
    reads from the file, otherwise uses data from buf. Buf can be a buffer object with a read() method or a string
    containing NBT data.
    """
    if filename:
        buf = file(filename, "rb")

    if hasattr(buf, "read"):
        buf = buf.read()

    return _load_buffer(try_gunzip(buf))

class load_ctx(object):
    pass

def _load_buffer(buf):
    if isinstance(buf, str):
        buf = fromstring(buf, 'uint8')
    data = buf

    if not len(data):
        raise NBTFormatError("Asked to load root tag of zero length")

    tag_type = data[0]
    if tag_type != 10:
        magic = data[:4]
        raise NBTFormatError('Not an NBT file with a root TAG_Compound '
                             '(file starts with "%s" (0x%08x)' % (magic.tostring(), magic.view(dtype='uint32')))

    ctx = load_ctx()
    ctx.offset = 1
    ctx.data = data

    tag_name = load_string(ctx)
    tag = TAG_Compound.load_from(ctx)
    tag.name = tag_name

    return tag


__all__ = [a.__name__ for a in tag_classes.itervalues()] + ["load", "gunzip"]

import nbt_util

TAG_Value.__str__ = nbt_util.nested_string

try:
    #noinspection PyUnresolvedReferences
    from _nbt import (load, TAG_Byte, TAG_Short, TAG_Int, TAG_Long, TAG_Float, TAG_Double, TAG_String,
    TAG_Byte_Array, TAG_List, TAG_Compound, TAG_Int_Array, TAG_Short_Array, NBTFormatError)
except ImportError:
    pass


########NEW FILE########
__FILENAME__ = nbt_util
import nbt

def nested_string(tag, indent_string="  ", indent=0):
    result = ""

    if tag.tagID == nbt.TAG_COMPOUND:
        result += 'TAG_Compound({\n'
        indent += 1
        for key, value in tag.iteritems():
            result += indent_string * indent + '"%s": %s,\n' % (key, nested_string(value, indent_string, indent))
        indent -= 1
        result += indent_string * indent + '})'

    elif tag.tagID == nbt.TAG_LIST:
        result += 'TAG_List([\n'
        indent += 1
        for index, value in enumerate(tag):
            result += indent_string * indent + nested_string(value, indent_string, indent) + ",\n"
        indent -= 1
        result += indent_string * indent + '])'

    else:
        result += "%s(%r)" % (tag.__class__.__name__, tag.value)

    return result



########NEW FILE########
__FILENAME__ = pocket
from level import FakeChunk
import logging
from materials import pocketMaterials
from mclevelbase import ChunkNotPresent, notclosing
from nbt import TAG_List
from numpy import array, fromstring, zeros
import os
import struct

# values are usually little-endian, unlike Minecraft PC

logger = logging.getLogger(__file__)


class PocketChunksFile(object):
    holdFileOpen = False  # if False, reopens and recloses the file on each access
    SECTOR_BYTES = 4096
    CHUNK_HEADER_SIZE = 4

    @property
    def file(self):
        openfile = lambda: file(self.path, "rb+")
        if PocketChunksFile.holdFileOpen:
            if self._file is None:
                self._file = openfile()
            return notclosing(self._file)
        else:
            return openfile()

    def close(self):
        if PocketChunksFile.holdFileOpen:
            self._file.close()
            self._file = None

    def __init__(self, path):
        self.path = path
        self._file = None
        if not os.path.exists(path):
            file(path, "w").close()

        with self.file as f:

            filesize = os.path.getsize(path)
            if filesize & 0xfff:
                filesize = (filesize | 0xfff) + 1
                f.truncate(filesize)

            if filesize == 0:
                filesize = self.SECTOR_BYTES
                f.truncate(filesize)

            f.seek(0)
            offsetsData = f.read(self.SECTOR_BYTES)

            self.freeSectors = [True] * (filesize / self.SECTOR_BYTES)
            self.freeSectors[0] = False

            self.offsets = fromstring(offsetsData, dtype='<u4')

        needsRepair = False

        for index, offset in enumerate(self.offsets):
            sector = offset >> 8
            count = offset & 0xff

            for i in xrange(sector, sector + count):
                if i >= len(self.freeSectors):
                    # raise RegionMalformed("Region file offset table points to sector {0} (past the end of the file)".format(i))
                    print  "Region file offset table points to sector {0} (past the end of the file)".format(i)
                    needsRepair = True
                    break
                if self.freeSectors[i] is False:
                    logger.debug("Double-allocated sector number %s (offset %s @ %s)", i, offset, index)
                    needsRepair = True
                self.freeSectors[i] = False

        if needsRepair:
            self.repair()

        logger.info("Found region file {file} with {used}/{total} sectors used and {chunks} chunks present".format(
             file=os.path.basename(path), used=self.usedSectors, total=self.sectorCount, chunks=self.chunkCount))

    @property
    def usedSectors(self):
        return len(self.freeSectors) - sum(self.freeSectors)

    @property
    def sectorCount(self):
        return len(self.freeSectors)

    @property
    def chunkCount(self):
        return sum(self.offsets > 0)

    def repair(self):
        pass
#        lostAndFound = {}
#        _freeSectors = [True] * len(self.freeSectors)
#        _freeSectors[0] = _freeSectors[1] = False
#        deleted = 0
#        recovered = 0
#        logger.info("Beginning repairs on {file} ({chunks} chunks)".format(file=os.path.basename(self.path), chunks=sum(self.offsets > 0)))
#        rx, rz = self.regionCoords
#        for index, offset in enumerate(self.offsets):
#            if offset:
#                cx = index & 0x1f
#                cz = index >> 5
#                cx += rx << 5
#                cz += rz << 5
#                sectorStart = offset >> 8
#                sectorCount = offset & 0xff
#                try:
#
#                    if sectorStart + sectorCount > len(self.freeSectors):
#                        raise RegionMalformed("Offset {start}:{end} ({offset}) at index {index} pointed outside of the file".format()
#                            start=sectorStart, end=sectorStart + sectorCount, index=index, offset=offset)
#
#                    compressedData = self._readChunk(cx, cz)
#                    if compressedData is None:
#                        raise RegionMalformed("Failed to read chunk data for {0}".format((cx, cz)))
#
#                    format, data = self.decompressSectors(compressedData)
#                    chunkTag = nbt.load(buf=data)
#                    lev = chunkTag["Level"]
#                    xPos = lev["xPos"].value
#                    zPos = lev["zPos"].value
#                    overlaps = False
#
#                    for i in xrange(sectorStart, sectorStart + sectorCount):
#                        if _freeSectors[i] is False:
#                            overlaps = True
#                        _freeSectors[i] = False
#
#
#                    if xPos != cx or zPos != cz or overlaps:
#                        lostAndFound[xPos, zPos] = (format, compressedData)
#
#                        if (xPos, zPos) != (cx, cz):
#                            raise RegionMalformed("Chunk {found} was found in the slot reserved for {expected}".format(found=(xPos, zPos), expected=(cx, cz)))
#                        else:
#                            raise RegionMalformed("Chunk {found} (in slot {expected}) has overlapping sectors with another chunk!".format(found=(xPos, zPos), expected=(cx, cz)))
#
#
#
#                except Exception, e:
#                    logger.info("Unexpected chunk data at sector {sector} ({exc})".format(sector=sectorStart, exc=e))
#                    self.setOffset(cx, cz, 0)
#                    deleted += 1
#
#        for cPos, (format, foundData) in lostAndFound.iteritems():
#            cx, cz = cPos
#            if self.getOffset(cx, cz) == 0:
#                logger.info("Found chunk {found} and its slot is empty, recovering it".format(found=cPos))
#                self._saveChunk(cx, cz, foundData[5:], format)
#                recovered += 1
#
#        logger.info("Repair complete. Removed {0} chunks, recovered {1} chunks, net {2}".format(deleted, recovered, recovered - deleted))
#


    def _readChunk(self, cx, cz):
        cx &= 0x1f
        cz &= 0x1f
        offset = self.getOffset(cx, cz)
        if offset == 0:
            return None

        sectorStart = offset >> 8
        numSectors = offset & 0xff
        if numSectors == 0:
            return None

        if sectorStart + numSectors > len(self.freeSectors):
            return None

        with self.file as f:
            f.seek(sectorStart * self.SECTOR_BYTES)
            data = f.read(numSectors * self.SECTOR_BYTES)
        assert(len(data) > 0)
        logger.debug("REGION LOAD %s,%s sector %s", cx, cz, sectorStart)
        return data

    def loadChunk(self, cx, cz, world):
        data = self._readChunk(cx, cz)
        if data is None:
            raise ChunkNotPresent((cx, cz, self))

        chunk = PocketChunk(cx, cz, data[4:], world)
        return chunk

    def saveChunk(self, chunk):
        cx, cz = chunk.chunkPosition

        cx &= 0x1f
        cz &= 0x1f
        offset = self.getOffset(cx, cz)
        sectorNumber = offset >> 8
        sectorsAllocated = offset & 0xff

        data = chunk._savedData()

        sectorsNeeded = (len(data) + self.CHUNK_HEADER_SIZE) / self.SECTOR_BYTES + 1
        if sectorsNeeded >= 256:
            return

        if sectorNumber != 0 and sectorsAllocated >= sectorsNeeded:
            logger.debug("REGION SAVE {0},{1} rewriting {2}b".format(cx, cz, len(data)))
            self.writeSector(sectorNumber, data, format)
        else:
            # we need to allocate new sectors

            # mark the sectors previously used for this chunk as free
            for i in xrange(sectorNumber, sectorNumber + sectorsAllocated):
                self.freeSectors[i] = True

            runLength = 0
            try:
                runStart = self.freeSectors.index(True)

                for i in range(runStart, len(self.freeSectors)):
                    if runLength:
                        if self.freeSectors[i]:
                            runLength += 1
                        else:
                            runLength = 0
                    elif self.freeSectors[i]:
                        runStart = i
                        runLength = 1

                    if runLength >= sectorsNeeded:
                        break
            except ValueError:
                pass

            # we found a free space large enough
            if runLength >= sectorsNeeded:
                logger.debug("REGION SAVE {0},{1}, reusing {2}b".format(cx, cz, len(data)))
                sectorNumber = runStart
                self.setOffset(cx, cz, sectorNumber << 8 | sectorsNeeded)
                self.writeSector(sectorNumber, data, format)
                self.freeSectors[sectorNumber:sectorNumber + sectorsNeeded] = [False] * sectorsNeeded

            else:
                # no free space large enough found -- we need to grow the
                # file

                logger.debug("REGION SAVE {0},{1}, growing by {2}b".format(cx, cz, len(data)))

                with self.file as f:
                    f.seek(0, 2)
                    filesize = f.tell()

                    sectorNumber = len(self.freeSectors)

                    assert sectorNumber * self.SECTOR_BYTES == filesize

                    filesize += sectorsNeeded * self.SECTOR_BYTES
                    f.truncate(filesize)

                self.freeSectors += [False] * sectorsNeeded

                self.setOffset(cx, cz, sectorNumber << 8 | sectorsNeeded)
                self.writeSector(sectorNumber, data, format)

    def writeSector(self, sectorNumber, data, format):
        with self.file as f:
            logger.debug("REGION: Writing sector {0}".format(sectorNumber))

            f.seek(sectorNumber * self.SECTOR_BYTES)
            f.write(struct.pack("<I", len(data) + self.CHUNK_HEADER_SIZE))  # // chunk length
            f.write(data)  # // chunk data
            # f.flush()

    def containsChunk(self, cx, cz):
        return self.getOffset(cx, cz) != 0

    def getOffset(self, cx, cz):
        cx &= 0x1f
        cz &= 0x1f
        return self.offsets[cx + cz * 32]

    def setOffset(self, cx, cz, offset):
        cx &= 0x1f
        cz &= 0x1f
        self.offsets[cx + cz * 32] = offset
        with self.file as f:
            f.seek(0)
            f.write(self.offsets.tostring())

    def chunkCoords(self):
        indexes = (i for (i, offset) in enumerate(self.offsets) if offset)
        coords = ((i % 32, i // 32) for i in indexes)
        return coords

from infiniteworld import ChunkedLevelMixin
from level import MCLevel, LightedChunk


class PocketWorld(ChunkedLevelMixin, MCLevel):
    Height = 128
    Length = 512
    Width = 512

    isInfinite = True  # Wrong. isInfinite actually means 'isChunked' and should be changed
    materials = pocketMaterials

    @property
    def allChunks(self):
        return list(self.chunkFile.chunkCoords())

    def __init__(self, filename):
        if not os.path.isdir(filename):
            filename = os.path.dirname(filename)
        self.filename = filename
        self.dimensions = {}

        self.chunkFile = PocketChunksFile(os.path.join(filename, "chunks.dat"))
        self._loadedChunks = {}

    def getChunk(self, cx, cz):
        for p in cx, cz:
            if not 0 <= p <= 31:
                raise ChunkNotPresent((cx, cz, self))

        c = self._loadedChunks.get((cx, cz))
        if c is None:
            c = self.chunkFile.loadChunk(cx, cz, self)
            self._loadedChunks[cx, cz] = c
        return c

    @classmethod
    def _isLevel(cls, filename):
        clp = ("chunks.dat", "level.dat")

        if not os.path.isdir(filename):
            f = os.path.basename(filename)
            if f not in clp:
                return False
            filename = os.path.dirname(filename)

        return all([os.path.exists(os.path.join(filename, f)) for f in clp])

    def saveInPlace(self):
        for chunk in self._loadedChunks.itervalues():
            if chunk.dirty:
                self.chunkFile.saveChunk(chunk)
                chunk.dirty = False

    def containsChunk(self, cx, cz):
        if cx > 31 or cz > 31 or cx < 0 or cz < 0:
            return False
        return self.chunkFile.getOffset(cx, cz) != 0

    @property
    def chunksNeedingLighting(self):
        for chunk in self._loadedChunks.itervalues():
            if chunk.needsLighting:
                yield chunk.chunkPosition

class PocketChunk(LightedChunk):
    HeightMap = FakeChunk.HeightMap

    Entities = TileEntities = property(lambda self: TAG_List())

    dirty = False
    filename = "chunks.dat"

    def __init__(self, cx, cz, data, world):
        self.chunkPosition = (cx, cz)
        self.world = world
        data = fromstring(data, dtype='uint8')

        self.Blocks, data = data[:32768], data[32768:]
        self.Data, data = data[:16384], data[16384:]
        self.SkyLight, data = data[:16384], data[16384:]
        self.BlockLight, data = data[:16384], data[16384:]
        self.DirtyColumns = data[:256]

        self.unpackChunkData()
        self.shapeChunkData()


    def unpackChunkData(self):
        for key in ('SkyLight', 'BlockLight', 'Data'):
            dataArray = getattr(self, key)
            dataArray.shape = (16, 16, 64)
            s = dataArray.shape
            # assert s[2] == self.world.Height / 2
            # unpackedData = insert(dataArray[...,newaxis], 0, 0, 3)

            unpackedData = zeros((s[0], s[1], s[2] * 2), dtype='uint8')

            unpackedData[:, :, ::2] = dataArray
            unpackedData[:, :, ::2] &= 0xf
            unpackedData[:, :, 1::2] = dataArray
            unpackedData[:, :, 1::2] >>= 4
            setattr(self, key, unpackedData)

    def shapeChunkData(self):
        chunkSize = 16
        self.Blocks.shape = (chunkSize, chunkSize, self.world.Height)
        self.SkyLight.shape = (chunkSize, chunkSize, self.world.Height)
        self.BlockLight.shape = (chunkSize, chunkSize, self.world.Height)
        self.Data.shape = (chunkSize, chunkSize, self.world.Height)
        self.DirtyColumns.shape = chunkSize, chunkSize

    def _savedData(self):
        def packData(dataArray):
            assert dataArray.shape[2] == self.world.Height

            data = array(dataArray).reshape(16, 16, self.world.Height / 2, 2)
            data[..., 1] <<= 4
            data[..., 1] |= data[..., 0]
            return array(data[:, :, :, 1])

        if self.dirty:
            # elements of DirtyColumns are bitfields. Each bit corresponds to a
            # 16-block segment of the column. We set all of the bits because
            # we only track modifications at the chunk level.
            self.DirtyColumns[:] = 255

        return "".join([self.Blocks.tostring(),
                       packData(self.Data).tostring(),
                       packData(self.SkyLight).tostring(),
                       packData(self.BlockLight).tostring(),
                       self.DirtyColumns.tostring(),
                       ])

########NEW FILE########
__FILENAME__ = regionfile
import logging
import os
import struct
import zlib

from numpy import fromstring
from mclevelbase import notclosing, RegionMalformed, ChunkNotPresent
import nbt

log = logging.getLogger(__name__)

__author__ = 'Rio'

def deflate(data):
    return zlib.compress(data, 2)

def inflate(data):
    return zlib.decompress(data)


class MCRegionFile(object):
    holdFileOpen = False  # if False, reopens and recloses the file on each access

    @property
    def file(self):
        openfile = lambda: file(self.path, "rb+")
        if MCRegionFile.holdFileOpen:
            if self._file is None:
                self._file = openfile()
            return notclosing(self._file)
        else:
            return openfile()

    def close(self):
        if MCRegionFile.holdFileOpen:
            self._file.close()
            self._file = None

    def __del__(self):
        self.close()

    def __init__(self, path, regionCoords):
        self.path = path
        self.regionCoords = regionCoords
        self._file = None
        if not os.path.exists(path):
            file(path, "w").close()

        with self.file as f:

            filesize = os.path.getsize(path)
            if filesize & 0xfff:
                filesize = (filesize | 0xfff) + 1
                f.truncate(filesize)

            if filesize == 0:
                filesize = self.SECTOR_BYTES * 2
                f.truncate(filesize)

            f.seek(0)
            offsetsData = f.read(self.SECTOR_BYTES)
            modTimesData = f.read(self.SECTOR_BYTES)

            self.freeSectors = [True] * (filesize / self.SECTOR_BYTES)
            self.freeSectors[0:2] = False, False

            self.offsets = fromstring(offsetsData, dtype='>u4')
            self.modTimes = fromstring(modTimesData, dtype='>u4')

        needsRepair = False

        for offset in self.offsets:
            sector = offset >> 8
            count = offset & 0xff

            for i in xrange(sector, sector + count):
                if i >= len(self.freeSectors):
                    # raise RegionMalformed("Region file offset table points to sector {0} (past the end of the file)".format(i))
                    print  "Region file offset table points to sector {0} (past the end of the file)".format(i)
                    needsRepair = True
                    break
                if self.freeSectors[i] is False:
                    needsRepair = True
                self.freeSectors[i] = False

        if needsRepair:
            self.repair()

        log.info("Found region file {file} with {used}/{total} sectors used and {chunks} chunks present".format(
             file=os.path.basename(path), used=self.usedSectors, total=self.sectorCount, chunks=self.chunkCount))

    def __repr__(self):
        return "%s(\"%s\")" % (self.__class__.__name__, self.path)
    @property
    def usedSectors(self):
        return len(self.freeSectors) - sum(self.freeSectors)

    @property
    def sectorCount(self):
        return len(self.freeSectors)

    @property
    def chunkCount(self):
        return sum(self.offsets > 0)

    def repair(self):
        lostAndFound = {}
        _freeSectors = [True] * len(self.freeSectors)
        _freeSectors[0] = _freeSectors[1] = False
        deleted = 0
        recovered = 0
        log.info("Beginning repairs on {file} ({chunks} chunks)".format(file=os.path.basename(self.path), chunks=sum(self.offsets > 0)))
        rx, rz = self.regionCoords
        for index, offset in enumerate(self.offsets):
            if offset:
                cx = index & 0x1f
                cz = index >> 5
                cx += rx << 5
                cz += rz << 5
                sectorStart = offset >> 8
                sectorCount = offset & 0xff
                try:

                    if sectorStart + sectorCount > len(self.freeSectors):
                        raise RegionMalformed("Offset {start}:{end} ({offset}) at index {index} pointed outside of the file".format(
                            start=sectorStart, end=sectorStart + sectorCount, index=index, offset=offset))

                    data = self.readChunk(cx, cz)
                    if data is None:
                        raise RegionMalformed("Failed to read chunk data for {0}".format((cx, cz)))

                    chunkTag = nbt.load(buf=data)
                    lev = chunkTag["Level"]
                    xPos = lev["xPos"].value
                    zPos = lev["zPos"].value
                    overlaps = False

                    for i in xrange(sectorStart, sectorStart + sectorCount):
                        if _freeSectors[i] is False:
                            overlaps = True
                        _freeSectors[i] = False

                    if xPos != cx or zPos != cz or overlaps:
                        lostAndFound[xPos, zPos] = data

                        if (xPos, zPos) != (cx, cz):
                            raise RegionMalformed("Chunk {found} was found in the slot reserved for {expected}".format(found=(xPos, zPos), expected=(cx, cz)))
                        else:
                            raise RegionMalformed("Chunk {found} (in slot {expected}) has overlapping sectors with another chunk!".format(found=(xPos, zPos), expected=(cx, cz)))

                except Exception, e:
                    log.info("Unexpected chunk data at sector {sector} ({exc})".format(sector=sectorStart, exc=e))
                    self.setOffset(cx, cz, 0)
                    deleted += 1

        for cPos, (format, foundData) in lostAndFound.iteritems():
            cx, cz = cPos
            if self.getOffset(cx, cz) == 0:
                log.info("Found chunk {found} and its slot is empty, recovering it".format(found=cPos))
                self.saveChunk(cx, cz, foundData[5:])
                recovered += 1

        log.info("Repair complete. Removed {0} chunks, recovered {1} chunks, net {2}".format(deleted, recovered, recovered - deleted))


    def _readChunk(self, cx, cz):
        cx &= 0x1f
        cz &= 0x1f
        offset = self.getOffset(cx, cz)
        if offset == 0:
            raise ChunkNotPresent((cx, cz))

        sectorStart = offset >> 8
        numSectors = offset & 0xff
        if numSectors == 0:
            raise ChunkNotPresent((cx, cz))

        if sectorStart + numSectors > len(self.freeSectors):
            raise ChunkNotPresent((cx, cz))

        with self.file as f:
            f.seek(sectorStart * self.SECTOR_BYTES)
            data = f.read(numSectors * self.SECTOR_BYTES)
        if len(data) < 5:
            raise RegionMalformed, "Chunk data is only %d bytes long (expected 5)" % len(data)

        # log.debug("REGION LOAD {0},{1} sector {2}".format(cx, cz, sectorStart))

        length = struct.unpack_from(">I", data)[0]
        format = struct.unpack_from("B", data, 4)[0]
        data = data[5:length + 5]
        return data, format

    def readChunk(self, cx, cz):
        data, format = self._readChunk(cx, cz)
        if format == self.VERSION_GZIP:
            return nbt.gunzip(data)
        if format == self.VERSION_DEFLATE:
            return inflate(data)

        raise IOError("Unknown compress format: {0}".format(format))

    def copyChunkFrom(self, regionFile, cx, cz):
        """
        Silently fails if regionFile does not contain the requested chunk.
        """
        try:
            data, format = regionFile._readChunk(cx, cz)
            self._saveChunk(cx, cz, data, format)
        except ChunkNotPresent:
            pass

    def saveChunk(self, cx, cz, uncompressedData):
        data = deflate(uncompressedData)
        self._saveChunk(cx, cz, data, self.VERSION_DEFLATE)

    def _saveChunk(self, cx, cz, data, format):
        cx &= 0x1f
        cz &= 0x1f
        offset = self.getOffset(cx, cz)
        sectorNumber = offset >> 8
        sectorsAllocated = offset & 0xff



        sectorsNeeded = (len(data) + self.CHUNK_HEADER_SIZE) / self.SECTOR_BYTES + 1
        if sectorsNeeded >= 256:
            return

        if sectorNumber != 0 and sectorsAllocated >= sectorsNeeded:
            log.debug("REGION SAVE {0},{1} rewriting {2}b".format(cx, cz, len(data)))
            self.writeSector(sectorNumber, data, format)
        else:
            # we need to allocate new sectors

            # mark the sectors previously used for this chunk as free
            for i in xrange(sectorNumber, sectorNumber + sectorsAllocated):
                self.freeSectors[i] = True

            runLength = 0
            runStart = 0
            try:
                runStart = self.freeSectors.index(True)

                for i in range(runStart, len(self.freeSectors)):
                    if runLength:
                        if self.freeSectors[i]:
                            runLength += 1
                        else:
                            runLength = 0
                    elif self.freeSectors[i]:
                        runStart = i
                        runLength = 1

                    if runLength >= sectorsNeeded:
                        break
            except ValueError:
                pass

            # we found a free space large enough
            if runLength >= sectorsNeeded:
                log.debug("REGION SAVE {0},{1}, reusing {2}b".format(cx, cz, len(data)))
                sectorNumber = runStart
                self.setOffset(cx, cz, sectorNumber << 8 | sectorsNeeded)
                self.writeSector(sectorNumber, data, format)
                self.freeSectors[sectorNumber:sectorNumber + sectorsNeeded] = [False] * sectorsNeeded

            else:
                # no free space large enough found -- we need to grow the
                # file

                log.debug("REGION SAVE {0},{1}, growing by {2}b".format(cx, cz, len(data)))

                with self.file as f:
                    f.seek(0, 2)
                    filesize = f.tell()

                    sectorNumber = len(self.freeSectors)

                    assert sectorNumber * self.SECTOR_BYTES == filesize

                    filesize += sectorsNeeded * self.SECTOR_BYTES
                    f.truncate(filesize)

                self.freeSectors += [False] * sectorsNeeded

                self.setOffset(cx, cz, sectorNumber << 8 | sectorsNeeded)
                self.writeSector(sectorNumber, data, format)

    def writeSector(self, sectorNumber, data, format):
        with self.file as f:
            log.debug("REGION: Writing sector {0}".format(sectorNumber))

            f.seek(sectorNumber * self.SECTOR_BYTES)
            f.write(struct.pack(">I", len(data) + 1))  # // chunk length
            f.write(struct.pack("B", format))  # // chunk version number
            f.write(data)  # // chunk data
            # f.flush()

    def containsChunk(self, cx, cz):
        return self.getOffset(cx, cz) != 0

    def getOffset(self, cx, cz):
        cx &= 0x1f
        cz &= 0x1f
        return self.offsets[cx + cz * 32]

    def setOffset(self, cx, cz, offset):
        cx &= 0x1f
        cz &= 0x1f
        self.offsets[cx + cz * 32] = offset
        with self.file as f:
            f.seek(0)
            f.write(self.offsets.tostring())

    SECTOR_BYTES = 4096
    SECTOR_INTS = SECTOR_BYTES / 4
    CHUNK_HEADER_SIZE = 5
    VERSION_GZIP = 1
    VERSION_DEFLATE = 2

    compressMode = VERSION_DEFLATE

########NEW FILE########
__FILENAME__ = schematic
'''
Created on Jul 22, 2011

@author: Rio
'''
import atexit
from contextlib import closing
import os
import shutil
import zipfile
from logging import getLogger

import blockrotation
from box import BoundingBox
import infiniteworld
from level import MCLevel, EntityLevel
from materials import alphaMaterials, MCMaterials, namedMaterials
from mclevelbase import exhaust
import nbt
from numpy import array, swapaxes, uint8, zeros

log = getLogger(__name__)

__all__ = ['MCSchematic', 'INVEditChest']


class MCSchematic (EntityLevel):
    materials = alphaMaterials

    def __init__(self, shape=None, root_tag=None, filename=None, mats='Alpha'):
        """ shape is (x,y,z) for a new level's shape.  if none, takes
        root_tag as a TAG_Compound for an existing schematic file.  if
        none, tries to read the tag from filename.  if none, results
        are undefined. materials can be a MCMaterials instance, or one of
        "Classic", "Alpha", "Pocket" to indicate allowable blocks. The default
        is Alpha.

        block coordinate order in the file is y,z,x to use the same code as classic/indev levels.
        in hindsight, this was a completely arbitrary decision.

        the Entities and TileEntities are nbt.TAG_List objects containing TAG_Compounds.
        this makes it easy to copy entities without knowing about their insides.

        rotateLeft swaps the axes of the different arrays.  because of this, the Width, Height, and Length
        reflect the current dimensions of the schematic rather than the ones specified in the NBT structure.
        I'm not sure what happens when I try to re-save a rotated schematic.
        """

        # if(shape != None):
        #    self.setShape(shape)

        if filename:
            self.filename = filename
            if None is root_tag and os.path.exists(filename):
                root_tag = nbt.load(filename)
        else:
            self.filename = None

        if mats in namedMaterials:
            self.materials = namedMaterials[mats]
        else:
            assert(isinstance(mats, MCMaterials))
            self.materials = mats

        if root_tag:
            self.root_tag = root_tag
            if "Materials" in root_tag:
                self.materials = namedMaterials[self.Materials]
            else:
                root_tag["Materials"] = nbt.TAG_String(self.materials.name)
            self.shapeChunkData()

        else:
            assert shape is not None
            root_tag = nbt.TAG_Compound(name="Schematic")
            root_tag["Height"] = nbt.TAG_Short(shape[1])
            root_tag["Length"] = nbt.TAG_Short(shape[2])
            root_tag["Width"] = nbt.TAG_Short(shape[0])

            root_tag["Entities"] = nbt.TAG_List()
            root_tag["TileEntities"] = nbt.TAG_List()
            root_tag["Materials"] = nbt.TAG_String(self.materials.name)

            root_tag["Blocks"] = nbt.TAG_Byte_Array(zeros((shape[1], shape[2], shape[0]), uint8))
            root_tag["Data"] = nbt.TAG_Byte_Array(zeros((shape[1], shape[2], shape[0]), uint8))

            self.root_tag = root_tag

        self.packUnpack()
        self.root_tag["Data"].value &= 0xF  # discard high bits


    def saveToFile(self, filename=None):
        """ save to file named filename, or use self.filename.  XXX NOT THREAD SAFE AT ALL. """
        if filename is None:
            filename = self.filename
        if filename is None:
            raise IOError, u"Attempted to save an unnamed schematic in place"

        self.Materials = self.materials.name

        self.packUnpack()
        with open(filename, 'wb') as chunkfh:
            self.root_tag.save(chunkfh)

        self.packUnpack()

    def __str__(self):
        return u"MCSchematic(shape={0}, materials={2}, filename=\"{1}\")".format(self.size, self.filename or u"", self.Materials)

    # these refer to the blocks array instead of the file's height because rotation swaps the axes
    # this will have an impact later on when editing schematics instead of just importing/exporting
    @property
    def Length(self):
        return self.Blocks.shape[1]

    @property
    def Width(self):
        return self.Blocks.shape[0]

    @property
    def Height(self):
        return self.Blocks.shape[2]

    @property
    def Blocks(self):
        return self.root_tag["Blocks"].value

    @property
    def Data(self):
        return self.root_tag["Data"].value

    @property
    def Entities(self):
        return self.root_tag["Entities"]

    @property
    def TileEntities(self):
        return self.root_tag["TileEntities"]

    @property
    def Materials(self):
        return self.root_tag["Materials"].value

    @Materials.setter
    def Materials(self, val):
        if "Materials" not in self.root_tag:
            self.root_tag["Materials"] = nbt.TAG_String()
        self.root_tag["Materials"].value = val

    @classmethod
    def _isTagLevel(cls, root_tag):
        return "Schematic" == root_tag.name

    def shapeChunkData(self):
        w = self.root_tag["Width"].value
        l = self.root_tag["Length"].value
        h = self.root_tag["Height"].value

        self.root_tag["Blocks"].value.shape = (h, l, w)
        self.root_tag["Data"].value.shape = (h, l, w)

    def packUnpack(self):
        self.root_tag["Blocks"].value = swapaxes(self.root_tag["Blocks"].value, 0, 2)  # yzx to xzy
        self.root_tag["Data"].value = swapaxes(self.root_tag["Data"].value, 0, 2)  # yzx to xzy


    def _update_shape(self):
        root_tag = self.root_tag
        shape = self.Blocks.shape
        root_tag["Height"] = nbt.TAG_Short(shape[2])
        root_tag["Length"] = nbt.TAG_Short(shape[1])
        root_tag["Width"] = nbt.TAG_Short(shape[0])

    def rotateLeft(self):

        self.root_tag["Blocks"].value = swapaxes(self.Blocks, 1, 0)[:, ::-1, :]  # x=z; z=-x
        self.root_tag["Data"].value   = swapaxes(self.Data, 1, 0)[:, ::-1, :]  # x=z; z=-x
        self._update_shape()

        blockrotation.RotateLeft(self.Blocks, self.Data)

        log.info(u"Relocating entities...")
        for entity in self.Entities:
            for p in "Pos", "Motion":
                if p == "Pos":
                    zBase = self.Length
                else:
                    zBase = 0.0
                newX = entity[p][2].value
                newZ = zBase - entity[p][0].value

                entity[p][0].value = newX
                entity[p][2].value = newZ
            entity["Rotation"][0].value -= 90.0
            if entity["id"].value in ("Painting", "ItemFrame"):
                x, z = entity["TileX"].value, entity["TileZ"].value
                newx = z
                newz = self.Length - x - 1

                entity["TileX"].value, entity["TileZ"].value = newx, newz
                entity["Dir"].value = (entity["Dir"].value + 1) % 4

        for tileEntity in self.TileEntities:
            if not 'x' in tileEntity:
                continue

            newX = tileEntity["z"].value
            newZ = self.Length - tileEntity["x"].value - 1

            tileEntity["x"].value = newX
            tileEntity["z"].value = newZ

    def roll(self):
        " xxx rotate stuff "
        self.root_tag["Blocks"].value = swapaxes(self.Blocks, 2, 0)[:, :, ::-1]  # x=z; z=-x
        self.root_tag["Data"].value = swapaxes(self.Data, 2, 0)[:, :, ::-1]
        self._update_shape()

    def flipVertical(self):
        " xxx delete stuff "
        blockrotation.FlipVertical(self.Blocks, self.Data)
        self.root_tag["Blocks"].value = self.Blocks[:, :, ::-1]  # y=-y
        self.root_tag["Data"].value = self.Data[:, :, ::-1]

    def flipNorthSouth(self):
        blockrotation.FlipNorthSouth(self.Blocks, self.Data)
        self.root_tag["Blocks"].value = self.Blocks[::-1, :, :]  # x=-x
        self.root_tag["Data"].value = self.Data[::-1, :, :]

        northSouthPaintingMap = [0, 3, 2, 1]

        log.info(u"N/S Flip: Relocating entities...")
        for entity in self.Entities:

            entity["Pos"][0].value = self.Width - entity["Pos"][0].value
            entity["Motion"][0].value = -entity["Motion"][0].value

            entity["Rotation"][0].value -= 180.0

            if entity["id"].value in ("Painting", "ItemFrame"):
                entity["TileX"].value = self.Width - entity["TileX"].value
                entity["Dir"].value = northSouthPaintingMap[entity["Dir"].value]

        for tileEntity in self.TileEntities:
            if not 'x' in tileEntity:
                continue

            tileEntity["x"].value = self.Width - tileEntity["x"].value - 1

    def flipEastWest(self):
        " xxx flip entities "
        blockrotation.FlipEastWest(self.Blocks, self.Data)
        self.root_tag["Blocks"].value = self.Blocks[:, ::-1, :]  # z=-z
        self.root_tag["Data"].value = self.Data[:, ::-1, :]

        eastWestPaintingMap = [2, 1, 0, 3]

        log.info(u"E/W Flip: Relocating entities...")
        for entity in self.Entities:

            entity["Pos"][2].value = self.Length - entity["Pos"][2].value
            entity["Motion"][2].value = -entity["Motion"][2].value

            entity["Rotation"][0].value -= 180.0

            if entity["id"].value in ("Painting", "ItemFrame"):
                entity["TileZ"].value = self.Length - entity["TileZ"].value
                entity["Dir"].value = eastWestPaintingMap[entity["Dir"].value]

        for tileEntity in self.TileEntities:
            tileEntity["z"].value = self.Length - tileEntity["z"].value - 1

    def setShape(self, shape):
        """shape is a tuple of (width, height, length).  sets the
        schematic's properties and clears the block and data arrays"""

        x, y, z = shape
        shape = (x, z, y)

        self.root_tag["Blocks"].value = zeros(dtype='uint8', shape=shape)
        self.root_tag["Data"].value = zeros(dtype='uint8', shape=shape)
        self.shapeChunkData()


    def setBlockDataAt(self, x, y, z, newdata):
        if x < 0 or y < 0 or z < 0:
            return 0
        if x >= self.Width or y >= self.Height or z >= self.Length:
            return 0
        self.Data[x, z, y] = (newdata & 0xf)

    def blockDataAt(self, x, y, z):
        if x < 0 or y < 0 or z < 0:
            return 0
        if x >= self.Width or y >= self.Height or z >= self.Length:
            return 0
        return self.Data[x, z, y]

    @classmethod
    def chestWithItemID(cls, itemID, count=64, damage=0):
        """ Creates a chest with a stack of 'itemID' in each slot.
        Optionally specify the count of items in each stack. Pass a negative
        value for damage to create unnaturally sturdy tools. """
        root_tag = nbt.TAG_Compound()
        invTag = nbt.TAG_List()
        root_tag["Inventory"] = invTag
        for slot in range(9, 36):
            itemTag = nbt.TAG_Compound()
            itemTag["Slot"] = nbt.TAG_Byte(slot)
            itemTag["Count"] = nbt.TAG_Byte(count)
            itemTag["id"] = nbt.TAG_Short(itemID)
            itemTag["Damage"] = nbt.TAG_Short(damage)
            invTag.append(itemTag)

        chest = INVEditChest(root_tag, "")

        return chest


class INVEditChest(MCSchematic):
    Width = 1
    Height = 1
    Length = 1
    Blocks = array([[[alphaMaterials.Chest.ID]]], 'uint8')
    Data = array([[[0]]], 'uint8')
    Entities = nbt.TAG_List()
    Materials = alphaMaterials

    @classmethod
    def _isTagLevel(cls, root_tag):
        return "Inventory" in root_tag

    def __init__(self, root_tag, filename):

        if filename:
            self.filename = filename
            if None is root_tag:
                try:
                    root_tag = nbt.load(filename)
                except IOError, e:
                    log.info(u"Failed to load file {0}".format(e))
                    raise
        else:
            assert root_tag, "Must have either root_tag or filename"
            self.filename = None

        for item in list(root_tag["Inventory"]):
            slot = item["Slot"].value
            if slot < 9 or slot >= 36:
                root_tag["Inventory"].remove(item)
            else:
                item["Slot"].value -= 9  # adjust for different chest slot indexes

        self.root_tag = root_tag

    @property
    def TileEntities(self):
        chestTag = nbt.TAG_Compound()
        chestTag["id"] = nbt.TAG_String("Chest")
        chestTag["Items"] = nbt.TAG_List(self.root_tag["Inventory"])
        chestTag["x"] = nbt.TAG_Int(0)
        chestTag["y"] = nbt.TAG_Int(0)
        chestTag["z"] = nbt.TAG_Int(0)

        return nbt.TAG_List([chestTag], name="TileEntities")


class ZipSchematic (infiniteworld.MCInfdevOldLevel):
    def __init__(self, filename, create=False):
        self.zipfilename = filename

        tempdir = tempfile.mktemp("schematic")
        if create is False:
            zf = zipfile.ZipFile(filename)
            zf.extractall(tempdir)
            zf.close()

        super(ZipSchematic, self).__init__(tempdir, create)
        atexit.register(shutil.rmtree, self.worldFolder.filename, True)


        try:
            schematicDat = nbt.load(self.worldFolder.getFilePath("schematic.dat"))

            self.Width = schematicDat['Width'].value
            self.Height = schematicDat['Height'].value
            self.Length = schematicDat['Length'].value

            if "Materials" in schematicDat:
                self.materials = namedMaterials[schematicDat["Materials"].value]

        except Exception, e:
            print "Exception reading schematic.dat, skipping: {0!r}".format(e)
            self.Width = 0
            self.Length = 0

    def __del__(self):
        shutil.rmtree(self.worldFolder.filename, True)

    def saveInPlace(self):
        self.saveToFile(self.zipfilename)

    def saveToFile(self, filename):
        super(ZipSchematic, self).saveInPlace()
        schematicDat = nbt.TAG_Compound()
        schematicDat.name = "Mega Schematic"

        schematicDat["Width"] = nbt.TAG_Int(self.size[0])
        schematicDat["Height"] = nbt.TAG_Int(self.size[1])
        schematicDat["Length"] = nbt.TAG_Int(self.size[2])
        schematicDat["Materials"] = nbt.TAG_String(self.materials.name)

        schematicDat.save(self.worldFolder.getFilePath("schematic.dat"))

        basedir = self.worldFolder.filename
        assert os.path.isdir(basedir)
        with closing(zipfile.ZipFile(filename, "w", zipfile.ZIP_STORED)) as z:
            for root, dirs, files in os.walk(basedir):
                # NOTE: ignore empty directories
                for fn in files:
                    absfn = os.path.join(root, fn)
                    zfn = absfn[len(basedir) + len(os.sep):]  # XXX: relative path
                    z.write(absfn, zfn)

    def getWorldBounds(self):
        return BoundingBox((0, 0, 0), (self.Width, self.Height, self.Length))

    @classmethod
    def _isLevel(cls, filename):
        return zipfile.is_zipfile(filename)




def adjustExtractionParameters(self, box):
    x, y, z = box.origin
    w, h, l = box.size
    destX = destY = destZ = 0

    if y < 0:
        destY -= y
        h += y
        y = 0

    if y >= self.Height:
        return

    if y + h >= self.Height:
        h -= y + h - self.Height
        y = self.Height - h

    if h <= 0:
        return

    if self.Width:
        if x < 0:
            w += x
            destX -= x
            x = 0
        if x >= self.Width:
            return

        if x + w >= self.Width:
            w = self.Width - x

        if w <= 0:
            return

        if z < 0:
            l += z
            destZ -= z
            z = 0

        if z >= self.Length:
            return

        if z + l >= self.Length:
            l = self.Length - z

        if l <= 0:
            return

    box = BoundingBox((x, y, z), (w, h, l))

    return box, (destX, destY, destZ)


def extractSchematicFrom(sourceLevel, box, entities=True):
    return exhaust(extractSchematicFromIter(sourceLevel, box, entities))


def extractSchematicFromIter(sourceLevel, box, entities=True):
    p = sourceLevel.adjustExtractionParameters(box)
    if p is None:
        yield None
        return
    newbox, destPoint = p

    tempSchematic = MCSchematic(shape=box.size, mats=sourceLevel.materials)
    for i in tempSchematic.copyBlocksFromIter(sourceLevel, newbox, destPoint, entities=entities):
        yield i

    yield tempSchematic

MCLevel.extractSchematic = extractSchematicFrom
MCLevel.extractSchematicIter = extractSchematicFromIter
MCLevel.adjustExtractionParameters = adjustExtractionParameters

import tempfile


def extractZipSchematicFrom(sourceLevel, box, zipfilename=None, entities=True):
    return exhaust(extractZipSchematicFromIter(sourceLevel, box, zipfilename, entities))


def extractZipSchematicFromIter(sourceLevel, box, zipfilename=None, entities=True):
    # converts classic blocks to alpha
    # probably should only apply to alpha levels

    if zipfilename is None:
        zipfilename = tempfile.mktemp("zipschematic.zip")
    atexit.register(shutil.rmtree, zipfilename, True)

    p = sourceLevel.adjustExtractionParameters(box)
    if p is None:
        return
    sourceBox, destPoint = p

    destPoint = (0, 0, 0)

    tempSchematic = ZipSchematic(zipfilename, create=True)
    tempSchematic.materials = sourceLevel.materials

    for i in tempSchematic.copyBlocksFromIter(sourceLevel, sourceBox, destPoint, entities=entities, create=True):
        yield i

    tempSchematic.Width, tempSchematic.Height, tempSchematic.Length = sourceBox.size
    tempSchematic.saveInPlace()  # lights not needed for this format - crashes minecraft though
    yield tempSchematic

MCLevel.extractZipSchematic = extractZipSchematicFrom
MCLevel.extractZipSchematicIter = extractZipSchematicFromIter


def extractAnySchematic(level, box):
    return exhaust(level.extractAnySchematicIter(box))


def extractAnySchematicIter(level, box):
    if box.chunkCount < infiniteworld.MCInfdevOldLevel.loadedChunkLimit:
        for i in level.extractSchematicIter(box):
            yield i
    else:
        for i in level.extractZipSchematicIter(box):
            yield i

MCLevel.extractAnySchematic = extractAnySchematic
MCLevel.extractAnySchematicIter = extractAnySchematicIter


########NEW FILE########
__FILENAME__ = removableStorage
"""
This module handles detection and clean ejection of removable storage. (Mainly SD cards)
This is OS depended.
	On windows it looks for removable storage drives.
	On MacOS it specificly looks for SD cards.
	On Linux it looks for anything mounted in /media/
"""
__copyright__ = "Copyright (C) 2013 David Braam - Released under terms of the AGPLv3 License"
import platform
import string
import glob
import os
import stat
import time
import subprocess
import threading
try:
	from xml.etree import cElementTree as ElementTree
except:
	from xml.etree import ElementTree

from Cura.util import profile

_removableCacheUpdateThread = None
_removableCache = []

def _parseStupidPListXML(e):
	if e.tag == 'plist':
		return _parseStupidPListXML(list(e)[0])
	if e.tag == 'array':
		ret = []
		for c in list(e):
			ret.append(_parseStupidPListXML(c))
		return ret
	if e.tag == 'dict':
		ret = {}
		key = None
		for c in list(e):
			if c.tag == 'key':
				key = c.text
			elif key is not None:
				ret[key] = _parseStupidPListXML(c)
				key = None
		return ret
	if e.tag == 'true':
		return True
	if e.tag == 'false':
		return False
	return e.text

def _findInTree(t, n):
	ret = []
	if type(t) is dict:
		if '_name' in t and t['_name'] == n:
			ret.append(t)
		for k, v in t.items():
			ret += _findInTree(v, n)
	if type(t) is list:
		for v in t:
			ret += _findInTree(v, n)
	return ret

def getPossibleSDcardDrives():
	global _removableCache, _removableCacheUpdateThread

	if profile.getPreference('auto_detect_sd') == 'False':
		return []

	if _removableCacheUpdateThread is None:
		_removableCacheUpdateThread = threading.Thread(target=_updateCache)
		_removableCacheUpdateThread.daemon = True
		_removableCacheUpdateThread.start()
	return _removableCache

def _updateCache():
	global _removableCache

	while True:
		drives = []
		if platform.system() == "Windows":
			from ctypes import windll
			import ctypes
			bitmask = windll.kernel32.GetLogicalDrives()
			for letter in string.uppercase:
				if letter != 'A' and letter != 'B' and bitmask & 1 and windll.kernel32.GetDriveTypeA(letter + ':/') == 2:
					volumeName = ''
					nameBuffer = ctypes.create_unicode_buffer(1024)
					if windll.kernel32.GetVolumeInformationW(ctypes.c_wchar_p(letter + ':/'), nameBuffer, ctypes.sizeof(nameBuffer), None, None, None, None, 0) == 0:
						volumeName = nameBuffer.value
					if volumeName == '':
						volumeName = 'NO NAME'

					freeBytes = ctypes.c_longlong(0)
					if windll.kernel32.GetDiskFreeSpaceExA(letter + ':/', ctypes.byref(freeBytes), None, None) == 0:
						continue
					if freeBytes.value < 1:
						continue
					drives.append(('%s (%s:)' % (volumeName, letter), letter + ':/', volumeName))
				bitmask >>= 1
		elif platform.system() == "Darwin":
			p = subprocess.Popen(['system_profiler', 'SPUSBDataType', '-xml'], stdout=subprocess.PIPE)
			xml = ElementTree.fromstring(p.communicate()[0])
			p.wait()

			xml = _parseStupidPListXML(xml)
			for dev in _findInTree(xml, 'Mass Storage Device'):
				if 'removable_media' in dev and dev['removable_media'] == 'yes' and 'volumes' in dev and len(dev['volumes']) > 0:
					for vol in dev['volumes']:
						if 'mount_point' in vol:
							volume = vol['mount_point']
							drives.append((os.path.basename(volume), volume + '/', os.path.basename(volume)))

			p = subprocess.Popen(['system_profiler', 'SPCardReaderDataType', '-xml'], stdout=subprocess.PIPE)
			xml = ElementTree.fromstring(p.communicate()[0])
			p.wait()

			xml = _parseStupidPListXML(xml)
			for entry in xml:
				if '_items' in entry:
					for item in entry['_items']:
						for dev in item['_items']:
							if 'removable_media' in dev and dev['removable_media'] == 'yes' and 'volumes' in dev and len(dev['volumes']) > 0:
								for vol in dev['volumes']:
									if 'mount_point' in vol:
										volume = vol['mount_point']
										drives.append((os.path.basename(volume), volume + '/', os.path.basename(volume)))
		else:
			for volume in glob.glob('/media/*'):
				if os.path.ismount(volume):
					drives.append((os.path.basename(volume), volume + '/', os.path.basename(volume)))
				elif volume == '/media/'+os.getenv('USER'):
					for volume in glob.glob('/media/'+os.getenv('USER')+'/*'):
						if os.path.ismount(volume):
							drives.append((os.path.basename(volume), volume + '/', os.path.basename(volume)))

		_removableCache = drives
		time.sleep(1)

def ejectDrive(driveName):
	if platform.system() == "Windows":
		cmd = [os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'EjectMedia.exe')), driveName]
	elif platform.system() == "Darwin":
		cmd = ["diskutil", "eject", driveName]
	else:
		cmd = ["umount", driveName]

	kwargs = {}
	if subprocess.mswindows:
		su = subprocess.STARTUPINFO()
		su.dwFlags |= subprocess.STARTF_USESHOWWINDOW
		su.wShowWindow = subprocess.SW_HIDE
		kwargs['startupinfo'] = su
	p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, **kwargs)
	output = p.communicate()

	if p.wait():
		print output[0]
		print output[1]
		return False
	else:
		return True

if __name__ == '__main__':
	print getPossibleSDcardDrives()

########NEW FILE########
__FILENAME__ = resources
"""
Helper module to get easy access to the path where resources are stored.
This is because the resource location is depended on the packaging method and OS
"""
__copyright__ = "Copyright (C) 2013 David Braam - Released under terms of the AGPLv3 License"

import os
import sys
import glob

#Cura/util classes should not depend on wx...
import wx
import gettext

if sys.platform.startswith('darwin'):
	try:
		#Foundation import can crash on some MacOS installs
		from Foundation import *
	except:
		pass

if sys.platform.startswith('darwin'):
	if hasattr(sys, 'frozen'):
		try:
			resourceBasePath = NSBundle.mainBundle().resourcePath()
		except:
			resourceBasePath = os.path.join(os.path.dirname(__file__), "../../../../../")
	else:
		resourceBasePath = os.path.join(os.path.dirname(__file__), "../../resources")
else:
	resourceBasePath = os.path.join(os.path.dirname(__file__), "../../resources")

def getPathForResource(dir, subdir, resource_name):
	assert os.path.isdir(dir), "{p} is not a directory".format(p=dir)
	path = os.path.normpath(os.path.join(dir, subdir, resource_name))
	assert os.path.isfile(path), "{p} is not a file.".format(p=path)
	return path

def getPathForImage(name):
	return getPathForResource(resourceBasePath, 'images', name)

def getPathForMesh(name):
	return getPathForResource(resourceBasePath, 'meshes', name)

def getPathForFirmware(name):
	return getPathForResource(resourceBasePath, 'firmware', name)

def getDefaultMachineProfiles():
	path = os.path.normpath(os.path.join(resourceBasePath, 'machine_profiles', '*.ini'))
	return glob.glob(path)

def setupLocalization(selectedLanguage = None):
	#Default to english
	languages = ['en']

	if selectedLanguage is not None:
		for item in getLanguageOptions():
			if item[1] == selectedLanguage and item[0] is not None:
				languages = [item[0]]

	locale_path = os.path.normpath(os.path.join(resourceBasePath, 'locale'))
	translation = gettext.translation('Cura', locale_path, languages, fallback=True)
	translation.install(unicode=True)

def getLanguageOptions():
	return [
		['en', 'English'],
		# ['de', 'Deutsch'],
		# ['fr', 'French'],
		# ['nl', 'Nederlands'],
		# ['sp', 'Spanish'],
		# ['po', 'Polish']
	]

########NEW FILE########
__FILENAME__ = sliceEngine
"""
Slice engine communication.
This module handles all communication with the slicing engine.
"""
__copyright__ = "Copyright (C) 2013 David Braam - Released under terms of the AGPLv3 License"
import subprocess
import time
import math
import numpy
import os
import warnings
import threading
import traceback
import platform
import sys
import urllib
import urllib2
import hashlib
import socket
import struct
import errno
import cStringIO as StringIO

from Cura.util import profile
from Cura.util import pluginInfo
from Cura.util import version
from Cura.util import gcodeInterpreter

def getEngineFilename():
	"""
		Finds and returns the path to the current engine executable. This is OS depended.
	:return: The full path to the engine executable.
	"""
	if platform.system() == 'Windows':
		if version.isDevVersion() and os.path.exists('C:/Software/Cura_SteamEngine/_bin/Release/Cura_SteamEngine.exe'):
			return 'C:/Software/Cura_SteamEngine/_bin/Release/Cura_SteamEngine.exe'
		return os.path.abspath(os.path.join(os.path.dirname(__file__), '../..', 'CuraEngine.exe'))
	if hasattr(sys, 'frozen'):
		return os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../..', 'CuraEngine'))
	if os.path.isfile('/usr/bin/CuraEngine'):
		return '/usr/bin/CuraEngine'
	if os.path.isfile('/usr/local/bin/CuraEngine'):
		return '/usr/local/bin/CuraEngine'
	tempPath = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..', 'CuraEngine'))
	if os.path.isdir(tempPath):
		tempPath = os.path.join(tempPath,'CuraEngine')
	return tempPath

class EngineResult(object):
	"""
	Result from running the CuraEngine.
	Contains the engine log, polygons retrieved from the engine, the GCode and some meta-data.
	"""
	def __init__(self):
		self._engineLog = []
		self._gcodeData = StringIO.StringIO()
		self._polygons = []
		self._replaceInfo = {}
		self._success = False
		self._printTimeSeconds = None
		self._filamentMM = [0.0] * 4
		self._modelHash = None
		self._profileString = profile.getProfileString()
		self._preferencesString = profile.getPreferencesString()
		self._gcodeInterpreter = gcodeInterpreter.gcode()
		self._gcodeLoadThread = None
		self._finished = False

	def getFilamentWeight(self, e=0):
		#Calculates the weight of the filament in kg
		radius = float(profile.getProfileSetting('filament_diameter')) / 2
		volumeM3 = (self._filamentMM[e] * (math.pi * radius * radius)) / (1000*1000*1000)
		return volumeM3 * profile.getPreferenceFloat('filament_physical_density')

	def getFilamentCost(self, e=0):
		cost_kg = profile.getPreferenceFloat('filament_cost_kg')
		cost_meter = profile.getPreferenceFloat('filament_cost_meter')
		if cost_kg > 0.0 and cost_meter > 0.0:
			return "%.2f / %.2f" % (self.getFilamentWeight(e) * cost_kg, self._filamentMM[e] / 1000.0 * cost_meter)
		elif cost_kg > 0.0:
			return "%.2f" % (self.getFilamentWeight(e) * cost_kg)
		elif cost_meter > 0.0:
			return "%.2f" % (self._filamentMM[e] / 1000.0 * cost_meter)
		return None

	def getPrintTime(self):
		if self._printTimeSeconds is None:
			return ''
		if int(self._printTimeSeconds / 60 / 60) < 1:
			return '%d minutes' % (int(self._printTimeSeconds / 60) % 60)
		if int(self._printTimeSeconds / 60 / 60) == 1:
			return '%d hour %d minutes' % (int(self._printTimeSeconds / 60 / 60), int(self._printTimeSeconds / 60) % 60)
		return '%d hours %d minutes' % (int(self._printTimeSeconds / 60 / 60), int(self._printTimeSeconds / 60) % 60)

	def getFilamentAmount(self, e=0):
		if self._filamentMM[e] == 0.0:
			return None
		return '%0.2f meter %0.0f gram' % (float(self._filamentMM[e]) / 1000.0, self.getFilamentWeight(e) * 1000.0)

	def getLog(self):
		return self._engineLog

	def getGCode(self):
		data = self._gcodeData.getvalue()
		if len(self._replaceInfo) > 0:
			block0 = data[0:2048]
			for k, v in self._replaceInfo.items():
				v = (v + ' ' * len(k))[:len(k)]
				block0 = block0.replace(k, v)
			return block0 + data[2048:]
		return data

	def setGCode(self, gcode):
		self._gcodeData = StringIO.StringIO(gcode)
		self._replaceInfo = {}

	def addLog(self, line):
		self._engineLog.append(line)

	def setHash(self, hash):
		self._modelHash = hash

	def setFinished(self, result):
		self._finished = result

	def isFinished(self):
		return self._finished

	def getGCodeLayers(self, loadCallback):
		if not self._finished:
			return None
		if self._gcodeInterpreter.layerList is None and self._gcodeLoadThread is None:
			self._gcodeInterpreter.progressCallback = self._gcodeInterpreterCallback
			self._gcodeLoadThread = threading.Thread(target=lambda : self._gcodeInterpreter.load(self._gcodeData))
			self._gcodeLoadCallback = loadCallback
			self._gcodeLoadThread.daemon = True
			self._gcodeLoadThread.start()
		return self._gcodeInterpreter.layerList

	def _gcodeInterpreterCallback(self, progress):
		if len(self._gcodeInterpreter.layerList) % 5 == 0:
			time.sleep(0.1)
		return self._gcodeLoadCallback(self, progress)

	def submitInfoOnline(self):
		if profile.getPreference('submit_slice_information') != 'True':
			return
		if version.isDevVersion():
			return
		data = {
			'processor': platform.processor(),
			'machine': platform.machine(),
			'platform': platform.platform(),
			'profile': self._profileString,
			'preferences': self._preferencesString,
			'modelhash': self._modelHash,
			'version': version.getVersion(),
		}
		try:
			f = urllib2.urlopen("https://www.youmagine.com/curastats/", data = urllib.urlencode(data), timeout = 1)
			f.read()
			f.close()
		except:
			import traceback
			traceback.print_exc()

class Engine(object):
	"""
	Class used to communicate with the CuraEngine.
	The CuraEngine is ran as a 2nd process and reports back information trough stderr.
	GCode trough stdout and has a socket connection for polygon information and loading the 3D model into the engine.
	"""
	GUI_CMD_REQUEST_MESH = 0x01
	GUI_CMD_SEND_POLYGONS = 0x02
	GUI_CMD_FINISH_OBJECT = 0x03

	def __init__(self, progressCallback):
		self._process = None
		self._thread = None
		self._callback = progressCallback
		self._progressSteps = ['inset', 'skin', 'export']
		self._objCount = 0
		self._result = None

		self._serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self._serverPortNr = 0xC20A
		while True:
			try:
				self._serversocket.bind(('127.0.0.1', self._serverPortNr))
			except:
				print "Failed to listen on port: %d" % (self._serverPortNr)
				self._serverPortNr += 1
				if self._serverPortNr > 0xFFFF:
					print "Failed to listen on any port..."
					break
			else:
				break
		thread = threading.Thread(target=self._socketListenThread)
		thread.daemon = True
		thread.start()

	def _socketListenThread(self):
		self._serversocket.listen(1)
		print 'Listening for engine communications on %d' % (self._serverPortNr)
		while True:
			try:
				sock, _ = self._serversocket.accept()
				thread = threading.Thread(target=self._socketConnectionThread, args=(sock,))
				thread.daemon = True
				thread.start()
			except socket.error, e:
				if e.errno != errno.EINTR:
					raise

	def _socketConnectionThread(self, sock):
		layerNrOffset = 0
		while True:
			try:
				data = sock.recv(4)
			except:
				data = ''
			if len(data) == 0:
				sock.close()
				return
			cmd = struct.unpack('@i', data)[0]
			if cmd == self.GUI_CMD_REQUEST_MESH:
				meshInfo = self._modelData[0]
				self._modelData = self._modelData[1:]
				sock.sendall(struct.pack('@i', meshInfo[0]))
				sock.sendall(meshInfo[1].tostring())
			elif cmd == self.GUI_CMD_SEND_POLYGONS:
				cnt = struct.unpack('@i', sock.recv(4))[0]
				layerNr = struct.unpack('@i', sock.recv(4))[0]
				layerNr += layerNrOffset
				z = struct.unpack('@i', sock.recv(4))[0]
				z = float(z) / 1000.0
				typeNameLen = struct.unpack('@i', sock.recv(4))[0]
				typeName = sock.recv(typeNameLen)
				while len(self._result._polygons) < layerNr + 1:
					self._result._polygons.append({})
				polygons = self._result._polygons[layerNr]
				if typeName not in polygons:
					polygons[typeName] = []
				for n in xrange(0, cnt):
					length = struct.unpack('@i', sock.recv(4))[0]
					data = ''
					while len(data) < length * 8 * 2:
						recvData = sock.recv(length * 8 * 2 - len(data))
						if len(recvData) < 1:
							return
						data += recvData
					polygon2d = numpy.array(numpy.fromstring(data, numpy.int64), numpy.float32) / 1000.0
					polygon2d = polygon2d.reshape((len(polygon2d) / 2, 2))
					polygon = numpy.empty((len(polygon2d), 3), numpy.float32)
					polygon[:,:-1] = polygon2d
					polygon[:,2] = z
					polygons[typeName].append(polygon)
			elif cmd == self.GUI_CMD_FINISH_OBJECT:
				layerNrOffset = len(self._result._polygons)
			else:
				print "Unknown command on socket: %x" % (cmd)

	def cleanup(self):
		self.abortEngine()
		self._serversocket.close()

	def abortEngine(self):
		if self._process is not None:
			try:
				self._process.terminate()
			except:
				pass
		if self._thread is not None:
			self._thread.join()
		self._thread = None

	def wait(self):
		if self._thread is not None:
			self._thread.join()

	def getResult(self):
		return self._result

	def runEngine(self, scene):
		if len(scene.objects()) < 1:
			return
		extruderCount = 1
		for obj in scene.objects():
			if scene.checkPlatform(obj):
				extruderCount = max(extruderCount, len(obj._meshList))

		extruderCount = max(extruderCount, profile.minimalExtruderCount())

		commandList = [getEngineFilename(), '-v', '-p']
		for k, v in self._engineSettings(extruderCount).iteritems():
			commandList += ['-s', '%s=%s' % (k, str(v))]
		commandList += ['-g', '%d' % (self._serverPortNr)]
		self._objCount = 0
		engineModelData = []
		hash = hashlib.sha512()
		order = scene.printOrder()
		if order is None:
			pos = numpy.array(profile.getMachineCenterCoords()) * 1000
			objMin = None
			objMax = None
			for obj in scene.objects():
				if scene.checkPlatform(obj):
					oMin = obj.getMinimum()[0:2] + obj.getPosition()
					oMax = obj.getMaximum()[0:2] + obj.getPosition()
					if objMin is None:
						objMin = oMin
						objMax = oMax
					else:
						objMin[0] = min(oMin[0], objMin[0])
						objMin[1] = min(oMin[1], objMin[1])
						objMax[0] = max(oMax[0], objMax[0])
						objMax[1] = max(oMax[1], objMax[1])
			if objMin is None:
				return
			pos += (objMin + objMax) / 2.0 * 1000
			commandList += ['-s', 'posx=%d' % int(pos[0]), '-s', 'posy=%d' % int(pos[1])]

			vertexTotal = [0] * 4
			meshMax = 1
			for obj in scene.objects():
				if scene.checkPlatform(obj):
					meshMax = max(meshMax, len(obj._meshList))
					for n in xrange(0, len(obj._meshList)):
						vertexTotal[n] += obj._meshList[n].vertexCount

			for n in xrange(0, meshMax):
				verts = numpy.zeros((0, 3), numpy.float32)
				for obj in scene.objects():
					if scene.checkPlatform(obj):
						if n < len(obj._meshList):
							vertexes = (numpy.matrix(obj._meshList[n].vertexes, copy = False) * numpy.matrix(obj._matrix, numpy.float32)).getA()
							vertexes -= obj._drawOffset
							vertexes += numpy.array([obj.getPosition()[0], obj.getPosition()[1], 0.0])
							verts = numpy.concatenate((verts, vertexes))
							hash.update(obj._meshList[n].vertexes.tostring())
				engineModelData.append((vertexTotal[n], verts))

			commandList += ['$' * meshMax]
			self._objCount = 1
		else:
			for n in order:
				obj = scene.objects()[n]
				for mesh in obj._meshList:
					engineModelData.append((mesh.vertexCount, mesh.vertexes))
					hash.update(mesh.vertexes.tostring())
				pos = obj.getPosition() * 1000
				pos += numpy.array(profile.getMachineCenterCoords()) * 1000
				commandList += ['-m', ','.join(map(str, obj._matrix.getA().flatten()))]
				commandList += ['-s', 'posx=%d' % int(pos[0]), '-s', 'posy=%d' % int(pos[1])]
				commandList += ['$' * len(obj._meshList)]
				self._objCount += 1
		modelHash = hash.hexdigest()
		if self._objCount > 0:
			self._thread = threading.Thread(target=self._watchProcess, args=(commandList, self._thread, engineModelData, modelHash))
			self._thread.daemon = True
			self._thread.start()

	def _watchProcess(self, commandList, oldThread, engineModelData, modelHash):
		if oldThread is not None:
			if self._process is not None:
				self._process.terminate()
			oldThread.join()
		self._callback(-1.0)
		self._modelData = engineModelData
		try:
			self._process = self._runEngineProcess(commandList)
		except OSError:
			traceback.print_exc()
			return
		if self._thread != threading.currentThread():
			self._process.terminate()

		self._result = EngineResult()
		self._result.addLog('Running: %s' % (' '.join(commandList)))
		self._result.setHash(modelHash)
		self._callback(0.0)

		logThread = threading.Thread(target=self._watchStderr, args=(self._process.stderr,))
		logThread.daemon = True
		logThread.start()

		data = self._process.stdout.read(4096)
		while len(data) > 0:
			self._result._gcodeData.write(data)
			data = self._process.stdout.read(4096)

		returnCode = self._process.wait()
		logThread.join()
		if returnCode == 0:
			pluginError = pluginInfo.runPostProcessingPlugins(self._result)
			if pluginError is not None:
				print pluginError
				self._result.addLog(pluginError)
			self._result.setFinished(True)
			self._callback(1.0)
		else:
			for line in self._result.getLog():
				print line
			self._callback(-1.0)
		self._process = None

	def _watchStderr(self, stderr):
		objectNr = 0
		line = stderr.readline()
		while len(line) > 0:
			line = line.strip()
			if line.startswith('Progress:'):
				line = line.split(':')
				if line[1] == 'process':
					objectNr += 1
				elif line[1] in self._progressSteps:
					progressValue = float(line[2]) / float(line[3])
					progressValue /= len(self._progressSteps)
					progressValue += 1.0 / len(self._progressSteps) * self._progressSteps.index(line[1])

					progressValue /= self._objCount
					progressValue += 1.0 / self._objCount * objectNr
					try:
						self._callback(progressValue)
					except:
						pass
			elif line.startswith('Print time:'):
				self._result._printTimeSeconds = int(line.split(':')[1].strip())
			elif line.startswith('Filament:'):
				self._result._filamentMM[0] = int(line.split(':')[1].strip())
				if profile.getMachineSetting('gcode_flavor') == 'UltiGCode':
					radius = profile.getProfileSettingFloat('filament_diameter') / 2.0
					self._result._filamentMM[0] /= (math.pi * radius * radius)
			elif line.startswith('Filament2:'):
				self._result._filamentMM[1] = int(line.split(':')[1].strip())
				if profile.getMachineSetting('gcode_flavor') == 'UltiGCode':
					radius = profile.getProfileSettingFloat('filament_diameter') / 2.0
					self._result._filamentMM[1] /= (math.pi * radius * radius)
			elif line.startswith('Replace:'):
				self._result._replaceInfo[line.split(':')[1].strip()] = line.split(':')[2].strip()
			else:
				self._result.addLog(line)
			line = stderr.readline()

	def _engineSettings(self, extruderCount):
		settings = {
			'layerThickness': int(profile.getProfileSettingFloat('layer_height') * 1000),
			'initialLayerThickness': int(profile.getProfileSettingFloat('bottom_thickness') * 1000) if profile.getProfileSettingFloat('bottom_thickness') > 0.0 else int(profile.getProfileSettingFloat('layer_height') * 1000),
			'filamentDiameter': int(profile.getProfileSettingFloat('filament_diameter') * 1000),
			'filamentFlow': int(profile.getProfileSettingFloat('filament_flow')),
			'extrusionWidth': int(profile.calculateEdgeWidth() * 1000),
			'layer0extrusionWidth': int(profile.calculateEdgeWidth() * 1000),
			'insetCount': int(profile.calculateLineCount()),
			'downSkinCount': int(profile.calculateSolidLayerCount()) if profile.getProfileSetting('solid_bottom') == 'True' else 0,
			'upSkinCount': int(profile.calculateSolidLayerCount()) if profile.getProfileSetting('solid_top') == 'True' else 0,
			'infillOverlap': int(profile.getProfileSettingFloat('fill_overlap')),
			'initialSpeedupLayers': int(4),
			'initialLayerSpeed': int(profile.getProfileSettingFloat('bottom_layer_speed')),
			'printSpeed': int(profile.getProfileSettingFloat('print_speed')),
			'infillSpeed': int(profile.getProfileSettingFloat('infill_speed')) if int(profile.getProfileSettingFloat('infill_speed')) > 0 else int(profile.getProfileSettingFloat('print_speed')),
			'inset0Speed': int(profile.getProfileSettingFloat('inset0_speed')) if int(profile.getProfileSettingFloat('inset0_speed')) > 0 else int(profile.getProfileSettingFloat('print_speed')),
			'insetXSpeed': int(profile.getProfileSettingFloat('insetx_speed')) if int(profile.getProfileSettingFloat('insetx_speed')) > 0 else int(profile.getProfileSettingFloat('print_speed')),
			'moveSpeed': int(profile.getProfileSettingFloat('travel_speed')),
			'fanSpeedMin': int(profile.getProfileSettingFloat('fan_speed')) if profile.getProfileSetting('fan_enabled') == 'True' else 0,
			'fanSpeedMax': int(profile.getProfileSettingFloat('fan_speed_max')) if profile.getProfileSetting('fan_enabled') == 'True' else 0,
			'supportAngle': int(-1) if profile.getProfileSetting('support') == 'None' else int(profile.getProfileSettingFloat('support_angle')),
			'supportEverywhere': int(1) if profile.getProfileSetting('support') == 'Everywhere' else int(0),
			'supportLineDistance': int(100 * profile.calculateEdgeWidth() * 1000 / profile.getProfileSettingFloat('support_fill_rate')) if profile.getProfileSettingFloat('support_fill_rate') > 0 else -1,
			'supportXYDistance': int(1000 * profile.getProfileSettingFloat('support_xy_distance')),
			'supportZDistance': int(1000 * profile.getProfileSettingFloat('support_z_distance')),
			'supportExtruder': 0 if profile.getProfileSetting('support_dual_extrusion') == 'First extruder' else (1 if profile.getProfileSetting('support_dual_extrusion') == 'Second extruder' and profile.minimalExtruderCount() > 1 else -1),
			'retractionAmount': int(profile.getProfileSettingFloat('retraction_amount') * 1000) if profile.getProfileSetting('retraction_enable') == 'True' else 0,
			'retractionSpeed': int(profile.getProfileSettingFloat('retraction_speed')),
			'retractionMinimalDistance': int(profile.getProfileSettingFloat('retraction_min_travel') * 1000),
			'retractionAmountExtruderSwitch': int(profile.getProfileSettingFloat('retraction_dual_amount') * 1000),
			'retractionZHop': int(profile.getProfileSettingFloat('retraction_hop') * 1000),
			'minimalExtrusionBeforeRetraction': int(profile.getProfileSettingFloat('retraction_minimal_extrusion') * 1000),
			'enableCombing': 1 if profile.getProfileSetting('retraction_combing') == 'True' else 0,
			'multiVolumeOverlap': int(profile.getProfileSettingFloat('overlap_dual') * 1000),
			'objectSink': max(0, int(profile.getProfileSettingFloat('object_sink') * 1000)),
			'minimalLayerTime': int(profile.getProfileSettingFloat('cool_min_layer_time')),
			'minimalFeedrate': int(profile.getProfileSettingFloat('cool_min_feedrate')),
			'coolHeadLift': 1 if profile.getProfileSetting('cool_head_lift') == 'True' else 0,
			'startCode': profile.getAlterationFileContents('start.gcode', extruderCount),
			'endCode': profile.getAlterationFileContents('end.gcode', extruderCount),
			'preSwitchExtruderCode': profile.getAlterationFileContents('preSwitchExtruder.gcode', extruderCount),
			'postSwitchExtruderCode': profile.getAlterationFileContents('postSwitchExtruder.gcode', extruderCount),

			'extruderOffset[1].X': int(profile.getMachineSettingFloat('extruder_offset_x1') * 1000),
			'extruderOffset[1].Y': int(profile.getMachineSettingFloat('extruder_offset_y1') * 1000),
			'extruderOffset[2].X': int(profile.getMachineSettingFloat('extruder_offset_x2') * 1000),
			'extruderOffset[2].Y': int(profile.getMachineSettingFloat('extruder_offset_y2') * 1000),
			'extruderOffset[3].X': int(profile.getMachineSettingFloat('extruder_offset_x3') * 1000),
			'extruderOffset[3].Y': int(profile.getMachineSettingFloat('extruder_offset_y3') * 1000),
			'fixHorrible': 0,
		}
		fanFullHeight = int(profile.getProfileSettingFloat('fan_full_height') * 1000)
		settings['fanFullOnLayerNr'] = (fanFullHeight - settings['initialLayerThickness'] - 1) / settings['layerThickness'] + 1
		if settings['fanFullOnLayerNr'] < 0:
			settings['fanFullOnLayerNr'] = 0
		if profile.getProfileSetting('support_type') == 'Lines':
			settings['supportType'] = 1

		if profile.getProfileSettingFloat('fill_density') == 0:
			settings['sparseInfillLineDistance'] = -1
		elif profile.getProfileSettingFloat('fill_density') == 100:
			settings['sparseInfillLineDistance'] = settings['extrusionWidth']
			#Set the up/down skins height to 10000 if we want a 100% filled object.
			# This gives better results then normal 100% infill as the sparse and up/down skin have some overlap.
			settings['downSkinCount'] = 10000
			settings['upSkinCount'] = 10000
		else:
			settings['sparseInfillLineDistance'] = int(100 * profile.calculateEdgeWidth() * 1000 / profile.getProfileSettingFloat('fill_density'))
		if profile.getProfileSetting('platform_adhesion') == 'Brim':
			settings['skirtDistance'] = 0
			settings['skirtLineCount'] = int(profile.getProfileSettingFloat('brim_line_count'))
		elif profile.getProfileSetting('platform_adhesion') == 'Raft':
			settings['skirtDistance'] = 0
			settings['skirtLineCount'] = 0
			settings['raftMargin'] = int(profile.getProfileSettingFloat('raft_margin') * 1000)
			settings['raftLineSpacing'] = int(profile.getProfileSettingFloat('raft_line_spacing') * 1000)
			settings['raftBaseThickness'] = int(profile.getProfileSettingFloat('raft_base_thickness') * 1000)
			settings['raftBaseLinewidth'] = int(profile.getProfileSettingFloat('raft_base_linewidth') * 1000)
			settings['raftInterfaceThickness'] = int(profile.getProfileSettingFloat('raft_interface_thickness') * 1000)
			settings['raftInterfaceLinewidth'] = int(profile.getProfileSettingFloat('raft_interface_linewidth') * 1000)
			settings['raftInterfaceLineSpacing'] = int(profile.getProfileSettingFloat('raft_interface_linewidth') * 1000 * 2.0)
			settings['raftAirGapLayer0'] = int(profile.getProfileSettingFloat('raft_airgap') * 1000)
			settings['raftBaseSpeed'] = int(profile.getProfileSettingFloat('bottom_layer_speed'))
			settings['raftFanSpeed'] = 100
			settings['raftSurfaceThickness'] = settings['raftInterfaceThickness']
			settings['raftSurfaceLinewidth'] = int(profile.calculateEdgeWidth() * 1000)
			settings['raftSurfaceLineSpacing'] = int(profile.calculateEdgeWidth() * 1000 * 0.9)
			settings['raftSurfaceLayers'] = int(profile.getProfileSettingFloat('raft_surface_layers'))
			settings['raftSurfaceSpeed'] = int(profile.getProfileSettingFloat('bottom_layer_speed'))
		else:
			settings['skirtDistance'] = int(profile.getProfileSettingFloat('skirt_gap') * 1000)
			settings['skirtLineCount'] = int(profile.getProfileSettingFloat('skirt_line_count'))
			settings['skirtMinLength'] = int(profile.getProfileSettingFloat('skirt_minimal_length') * 1000)

		if profile.getProfileSetting('fix_horrible_union_all_type_a') == 'True':
			settings['fixHorrible'] |= 0x01
		if profile.getProfileSetting('fix_horrible_union_all_type_b') == 'True':
			settings['fixHorrible'] |= 0x02
		if profile.getProfileSetting('fix_horrible_use_open_bits') == 'True':
			settings['fixHorrible'] |= 0x10
		if profile.getProfileSetting('fix_horrible_extensive_stitching') == 'True':
			settings['fixHorrible'] |= 0x04

		if settings['layerThickness'] <= 0:
			settings['layerThickness'] = 1000
		if profile.getMachineSetting('gcode_flavor') == 'UltiGCode':
			settings['gcodeFlavor'] = 1
		elif profile.getMachineSetting('gcode_flavor') == 'MakerBot':
			settings['gcodeFlavor'] = 2
		elif profile.getMachineSetting('gcode_flavor') == 'BFB':
			settings['gcodeFlavor'] = 3
		elif profile.getMachineSetting('gcode_flavor') == 'Mach3':
			settings['gcodeFlavor'] = 4
		elif profile.getMachineSetting('gcode_flavor') == 'RepRap (Volumetric)':
			settings['gcodeFlavor'] = 5
		if profile.getProfileSetting('spiralize') == 'True':
			settings['spiralizeMode'] = 1
		if profile.getProfileSetting('simple_mode') == 'True':
			settings['simpleMode'] = 1
		if profile.getProfileSetting('wipe_tower') == 'True' and extruderCount > 1:
			settings['wipeTowerSize'] = int(math.sqrt(profile.getProfileSettingFloat('wipe_tower_volume') * 1000 * 1000 * 1000 / settings['layerThickness']))
		if profile.getProfileSetting('ooze_shield') == 'True':
			settings['enableOozeShield'] = 1
		return settings

	def _runEngineProcess(self, cmdList):
		kwargs = {}
		if subprocess.mswindows:
			su = subprocess.STARTUPINFO()
			su.dwFlags |= subprocess.STARTF_USESHOWWINDOW
			su.wShowWindow = subprocess.SW_HIDE
			kwargs['startupinfo'] = su
			kwargs['creationflags'] = 0x00004000 #BELOW_NORMAL_PRIORITY_CLASS
		return subprocess.Popen(cmdList, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, **kwargs)

########NEW FILE########
__FILENAME__ = util3d
"""
The util3d module a vector class to work with 3D points. All the basic math operators have been overloaded to work on this object.
This module is deprecated and only used by the SplitModels function.

Use numpy arrays instead to work with vectors.
"""
__copyright__ = "Copyright (C) 2013 David Braam - Released under terms of the AGPLv3 License"

import math

class Vector3(object):
	""" 3D vector object. """
	def __init__(self, x=0.0, y=0.0, z=0.0):
		"""Create a new 3D vector"""
		self.x = x
		self.y = y
		self.z = z

	def __copy__(self):
		return Vector3(self.x, self.y, self.z)

	def copy(self):
		return Vector3(self.x, self.y, self.z)

	def __repr__(self):
		return 'V[%s, %s, %s]' % ( self.x, self.y, self.z )

	def __add__(self, v):
		return Vector3( self.x + v.x, self.y + v.y, self.z + v.z )

	def __sub__(self, v):
		return Vector3( self.x - v.x, self.y - v.y, self.z - v.z )

	def __mul__(self, v):
		return Vector3( self.x * v, self.y * v, self.z * v )

	def __div__(self, v):
		return Vector3( self.x / v, self.y / v, self.z / v )
	__truediv__ = __div__

	def __neg__(self):
		return Vector3( - self.x, - self.y, - self.z )

	def __iadd__(self, v):
		self.x += v.x
		self.y += v.y
		self.z += v.z
		return self

	def __isub__(self, v):
		self.x += v.x
		self.y += v.y
		self.z += v.z
		return self

	def __imul__(self, v):
		self.x *= v
		self.y *= v
		self.z *= v
		return self

	def __idiv__(self, v):
		self.x /= v
		self.y /= v
		self.z /= v
		return self

	def almostEqual(self, v):
		return (abs(self.x - v.x) + abs(self.y - v.y) + abs(self.z - v.z)) < 0.00001
	
	def cross(self, v):
		return Vector3(self.y * v.z - self.z * v.y, -self.x * v.z + self.z * v.x, self.x * v.y - self.y * v.x)

	def vsize(self):
		return math.sqrt( self.x * self.x + self.y * self.y + self.z * self.z )

	def normalize(self):
		f = self.vsize()
		if f != 0.0:
			self.x /= f
			self.y /= f
			self.z /= f

	def min(self, v):
		return Vector3(min(self.x, v.x), min(self.y, v.y), min(self.z, v.z))

	def max(self, v):
		return Vector3(max(self.x, v.x), max(self.y, v.y), max(self.z, v.z))


########NEW FILE########
__FILENAME__ = validators
"""
Setting validators.
These are the validators for various profile settings, each validator can be attached to a setting.
The validators can be queried to see if the setting is valid.
There are 3 possible outcomes:
	Valid	- No problems found
	Warning - The value is valid, but not recommended
	Error	- The value is not a proper number, out of range, or some other way wrong.
"""
from __future__ import division
__copyright__ = "Copyright (C) 2013 David Braam - Released under terms of the AGPLv3 License"

import types
import math

SUCCESS = 0
WARNING = 1
ERROR   = 2

class validFloat(object):
	"""
	Checks if the given value in the setting is a valid float. An invalid float is an error condition.
	And supports a minimum and/or maximum value. The min/max values are error conditions.
	If the value == min or max then this is also an error.
	"""
	def __init__(self, setting, minValue = None, maxValue = None):
		self.setting = setting
		self.setting._validators.append(self)
		self.minValue = minValue
		self.maxValue = maxValue
	
	def validate(self):
		try:
			f = float(eval(self.setting.getValue().replace(',','.'), {}, {}))
			if self.minValue is not None and f < self.minValue:
				return ERROR, 'This setting should not be below ' + str(round(self.minValue, 3))
			if self.maxValue is not None and f > self.maxValue:
				return ERROR, 'This setting should not be above ' + str(self.maxValue)
			return SUCCESS, ''
		except (ValueError, SyntaxError, TypeError, NameError):
			return ERROR, '"' + str(self.setting.getValue()) + '" is not a valid number or expression'

class validInt(object):
	"""
	Checks if the given value in the setting is a valid integer. An invalid integer is an error condition.
	And supports a minimum and/or maximum value. The min/max values are error conditions.
	If the value == min or max then this is also an error.
	"""
	def __init__(self, setting, minValue = None, maxValue = None):
		self.setting = setting
		self.setting._validators.append(self)
		self.minValue = minValue
		self.maxValue = maxValue
	
	def validate(self):
		try:
			f = int(eval(self.setting.getValue(), {}, {}))
			if self.minValue is not None and f < self.minValue:
				return ERROR, 'This setting should not be below ' + str(self.minValue)
			if self.maxValue is not None and f > self.maxValue:
				return ERROR, 'This setting should not be above ' + str(self.maxValue)
			return SUCCESS, ''
		except (ValueError, SyntaxError, TypeError, NameError):
			return ERROR, '"' + str(self.setting.getValue()) + '" is not a valid whole number or expression'

class warningAbove(object):
	"""
	A validator to give off a warning if a value is equal or above a certain value.
	"""
	def __init__(self, setting, minValueForWarning, warningMessage):
		self.setting = setting
		self.setting._validators.append(self)
		self.minValueForWarning = minValueForWarning
		self.warningMessage = warningMessage
	
	def validate(self):
		try:
			f = float(eval(self.setting.getValue().replace(',','.'), {}, {}))
			if isinstance(self.minValueForWarning, types.FunctionType):
				if f >= self.minValueForWarning():
					return WARNING, self.warningMessage % (self.minValueForWarning())
			else:
				if f >= self.minValueForWarning:
					return WARNING, self.warningMessage
			return SUCCESS, ''
		except (ValueError, SyntaxError, TypeError):
			#We already have an error by the int/float validator in this case.
			return SUCCESS, ''

class warningBelow(object):
	"""
	A validator to give off a warning if a value is equal or below a certain value.
	"""
	def __init__(self, setting, minValueForWarning, warningMessage):
		self.setting = setting
		self.setting._validators.append(self)
		self.minValueForWarning = minValueForWarning
		self.warningMessage = warningMessage

	def validate(self):
		try:
			f = float(eval(self.setting.getValue().replace(',','.'), {}, {}))
			if isinstance(self.minValueForWarning, types.FunctionType):
				if f <= self.minValueForWarning():
					return WARNING, self.warningMessage % (self.minValueForWarning())
			else:
				if f <= self.minValueForWarning:
					return WARNING, self.warningMessage
			return SUCCESS, ''
		except (ValueError, SyntaxError, TypeError):
			#We already have an error by the int/float validator in this case.
			return SUCCESS, ''

class wallThicknessValidator(object):
	"""
	Special wall-thickness validator. The wall thickness is used to calculate the amount of shells and the thickness of the shells.
	But, on certain conditions the resulting wall-thickness is not really suitable for printing. The range in which this can happen is small.
	But better warn for it.
	"""
	def __init__(self, setting):
		self.setting = setting
		self.setting._validators.append(self)
	
	def validate(self):
		from Cura.util import profile
		try:
			wallThickness = profile.getProfileSettingFloat('wall_thickness')
			nozzleSize = profile.getProfileSettingFloat('nozzle_size')
			if wallThickness < 0.01:
				return SUCCESS, ''
			if wallThickness <= nozzleSize * 0.5:
				return ERROR, 'Trying to print walls thinner then the half of your nozzle size, this will not produce anything usable'
			if wallThickness <= nozzleSize * 0.85:
				return WARNING, 'Trying to print walls thinner then the 0.8 * nozzle size. Small chance that this will produce usable results'
			if wallThickness < nozzleSize:
				return SUCCESS, ''
			if nozzleSize <= 0:
				return ERROR, 'Incorrect nozzle size'
			
			lineCount = int(wallThickness / nozzleSize)
			lineWidth = wallThickness / lineCount
			lineWidthAlt = wallThickness / (lineCount + 1)
			if lineWidth >= nozzleSize * 1.5 and lineWidthAlt <= nozzleSize * 0.85:
				return WARNING, 'Current selected wall thickness results in a line thickness of ' + str(lineWidthAlt) + 'mm which is not recommended with your nozzle of ' + str(nozzleSize) + 'mm'
			return SUCCESS, ''
		except ValueError:
			#We already have an error by the int/float validator in this case.
			return SUCCESS, ''

class printSpeedValidator(object):
	"""
	Validate the printing speed by checking for a certain amount of volume per second.
	This is based on the fact that you can push 10mm3 per second trough an UM-Origonal nozzle.
	TODO: Update this code so it works better for different machine times with other feeders.
	"""
	def __init__(self, setting):
		self.setting = setting
		self.setting._validators.append(self)

	def validate(self):
		from Cura.util import profile
		try:
			nozzleSize = profile.getProfileSettingFloat('nozzle_size')
			layerHeight = profile.getProfileSettingFloat('layer_height')
			printSpeed = profile.getProfileSettingFloat('print_speed')
			
			printVolumePerMM = layerHeight * nozzleSize
			printVolumePerSecond = printVolumePerMM * printSpeed
			#Using 10mm3 per second with a 0.4mm nozzle (normal max according to Joergen Geerds)
			maxPrintVolumePerSecond = 10 / (math.pi*(0.2*0.2)) * (math.pi*(nozzleSize/2*nozzleSize/2))
			
			if printVolumePerSecond > maxPrintVolumePerSecond:
				return WARNING, 'You are trying to print more then %.1fmm^3 of filament per second. This might cause filament slipping. (You are printing at %0.1fmm^3 per second)' % (maxPrintVolumePerSecond, printVolumePerSecond)
			
			return SUCCESS, ''
		except ValueError:
			#We already have an error by the int/float validator in this case.
			return SUCCESS, ''

########NEW FILE########
__FILENAME__ = version
"""
The version utility module is used to get the current Cura version, and check for updates.
It can also see if we are running a development build of Cura.
"""
__copyright__ = "Copyright (C) 2013 David Braam - Released under terms of the AGPLv3 License"

import os
import sys
import urllib2
import platform
import subprocess
try:
	from xml.etree import cElementTree as ElementTree
except:
	from xml.etree import ElementTree

from Cura.util import resources

def getVersion(getGitVersion = True):
	gitPath = os.path.abspath(os.path.join(os.path.split(os.path.abspath(__file__))[0], "../.."))
	if hasattr(sys, 'frozen'):
		versionFile = os.path.normpath(os.path.join(resources.resourceBasePath, "version"))
	else:
		versionFile = os.path.abspath(os.path.join(os.path.split(os.path.abspath(__file__))[0], "../version"))

	if getGitVersion:
		try:
			gitProcess = subprocess.Popen(args = "git show -s --pretty=format:%H", shell = True, cwd = gitPath, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
			(stdoutdata, stderrdata) = gitProcess.communicate()

			if gitProcess.returncode == 0:
				return stdoutdata
		except:
			pass

	gitHeadFile = gitPath + "/.git/refs/heads/SteamEngine"
	if os.path.isfile(gitHeadFile):
		if not getGitVersion:
			return "dev"
		f = open(gitHeadFile, "r")
		version = f.readline()
		f.close()
		return version.strip()
	if os.path.exists(versionFile):
		f = open(versionFile, "r")
		version = f.readline()
		f.close()
		return version.strip()
	versionFile = os.path.abspath(os.path.join(os.path.split(os.path.abspath(__file__))[0], "../../version"))
	if os.path.exists(versionFile):
		f = open(versionFile, "r")
		version = f.readline()
		f.close()
		return version.strip()
	return "?" #No idea what the version is. TODO:Tell the user.

def isDevVersion():
	gitPath = os.path.abspath(os.path.join(os.path.split(os.path.abspath(__file__))[0], "../../.git"))
	hgPath  = os.path.abspath(os.path.join(os.path.split(os.path.abspath(__file__))[0], "../../.hg"))
	return os.path.exists(gitPath) or os.path.exists(hgPath)

def checkForNewerVersion():
	if isDevVersion():
		return None
	try:
		updateBaseURL = 'http://software.ultimaker.com'
		localVersion = map(int, getVersion(False).split('.'))
		while len(localVersion) < 3:
			localVersion += [1]
		latestFile = urllib2.urlopen("%s/latest.xml" % (updateBaseURL))
		latestXml = latestFile.read()
		latestFile.close()
		xmlTree = ElementTree.fromstring(latestXml)
		for release in xmlTree.iter('release'):
			os = str(release.attrib['os'])
			version = [int(release.attrib['major']), int(release.attrib['minor']), int(release.attrib['revision'])]
			filename = release.find("filename").text
			if platform.system() == os:
				if version > localVersion:
					return "%s/current/%s" % (updateBaseURL, filename)
	except:
		#print sys.exc_info()
		return None
	return None

if __name__ == '__main__':
	print(getVersion())

########NEW FILE########
__FILENAME__ = youmagine
"""
YouMagine communication module.
This module handles all communication with the YouMagine API.
"""
__copyright__ = "Copyright (C) 2013 David Braam - Released under terms of the AGPLv3 License"

import json
import httplib as httpclient
import urllib
import textwrap

class httpUploadDataStream(object):
	"""
	For http uploads we need a readable/writable datasteam to use with the httpclient.HTTPSConnection class.
	This is used to facilitate file uploads towards Youmagine.
	"""
	def __init__(self, progressCallback):
		self._dataList = []
		self._totalLength = 0
		self._readPos = 0
		self._progressCallback = progressCallback

	def write(self, data):
		size = len(data)
		if size < 1:
			return
		blocks = size / 2048
		for n in xrange(0, blocks):
			self._dataList.append(data[n*2048:n*2048+2048])
		self._dataList.append(data[blocks*2048:])
		self._totalLength += size

	def read(self, size):
		if self._readPos >= len(self._dataList):
			return None
		ret = self._dataList[self._readPos]
		self._readPos += 1
		if self._progressCallback is not None:
			self._progressCallback(float(self._readPos / len(self._dataList)))
		return ret

	def __len__(self):
		return self._totalLength

class Youmagine(object):
	"""
	Youmagine connection object. Has various functions to communicate with Youmagine.
	These functions are blocking and thus this class should be used from a thread.
	"""
	def __init__(self, authToken, progressCallback = None):
		self._hostUrl = 'api.youmagine.com'
		self._viewUrl = 'www.youmagine.com'
		self._authUrl = 'https://www.youmagine.com/integrations/cura/authorized_integrations/new'
		self._authToken = authToken
		self._userName = None
		self._userID = None
		self._http = None
		self._hostReachable = True
		self._progressCallback = progressCallback
		self._categories = [
			('Art', 2),
			('Fashion', 3),
			('For your home', 4),
			('Gadget', 5),
			('Games', 6),
			('Jewelry', 7),
			('Maker/DIY', 8),
			('Miniatures', 9),
			('Toys', 10),
			('3D printer parts and enhancements', 11),
			('Other', 1),
		]
		self._licenses = [
			('Creative Commons - Attribution Share Alike', 'ccbysa'),
			('Creative Commons - Attribution Non-Commercial ShareAlike', 'ccbyncsa'),
			('Creative Commons - Attribution No Derivatives', 'ccbynd'),
			('Creative Commons - Attribution Non-Commercial No Derivatives', 'ccbyncsa'),
			('GPLv3', 'gplv3'),
		]

	def getAuthorizationUrl(self):
		return self._authUrl

	def getCategories(self):
		return map(lambda n: n[0], self._categories)

	def getLicenses(self):
		return map(lambda n: n[0], self._licenses)

	def setAuthToken(self, token):
		self._authToken = token
		self._userName = None
		self._userID = None

	def getAuthToken(self):
		return self._authToken

	def isHostReachable(self):
		return self._hostReachable

	def viewUrlForDesign(self, id):
		return 'https://%s/designs/%d' % (self._viewUrl, id)

	def editUrlForDesign(self, id):
		return 'https://%s/designs/%d/edit' % (self._viewUrl, id)

	def isAuthorized(self):
		if self._authToken is None:
			return False
		if self._userName is None:
			#No username yet, try to request the username to see if the authToken is valid.
			result = self._request('GET', '/authorized_integrations/%s/whoami.json' % (self._authToken))

			if 'error' in result:
				self._authToken = None
				return False
			self._userName = result['screen_name']
			self._userID = result['id']
		return True

	def createDesign(self, name, description, category, license):
		excerpt = description
		description = ''
		if len(excerpt) >= 300:
			lines = textwrap.wrap(excerpt, 300)
			excerpt = lines[0]
			description = '\n'.join(lines[1:])
		res = self._request('POST', '/designs.json', {'design[name]': name, 'design[excerpt]': excerpt, 'design[description]': description, 'design[design_category_id]': filter(lambda n: n[0] == category, self._categories)[0][1], 'design[license]': filter(lambda n: n[0] == license, self._licenses)[0][1]})
		if 'id' in res:
			return res['id']
		print res
		return None

	def publishDesign(self, id):
		res = self._request('PUT', '/designs/%d/mark_as/publish.json' % (id), {'ignore': 'me'})
		if res is not None:
			return False
		return True

	def createDocument(self, designId, name, contents):
		res = self._request('POST', '/designs/%d/documents.json' % (designId), {'document[name]': name, 'document[description]': 'Uploaded from Cura'}, {'document[file]': (name, contents)})
		if 'id' in res:
			return res['id']
		print res
		return None

	def createImage(self, designId, name, contents):
		res = self._request('POST', '/designs/%d/images.json' % (designId), {'image[name]': name, 'image[description]': 'Uploaded from Cura'}, {'image[file]': (name, contents)})
		if 'id' in res:
			return res['id']
		print res
		return None

	def listDesigns(self):
		res = self._request('GET', '/users/%s/designs.json' % (self._userID))
		return res

	def _request(self, method, url, postData = None, files = None):
		retryCount = 2
		if self._authToken is not None:
			url += '?auth_token=%s' % (self._authToken)
		error = 'Failed to connect to %s' % self._hostUrl
		for n in xrange(0, retryCount):
			if self._http is None:
				self._http = httpclient.HTTPSConnection(self._hostUrl)
			try:
				if files is not None:
					boundary = 'wL36Yn8afVp8Ag7AmP8qZ0SA4n1v9T'
					s = httpUploadDataStream(self._progressCallback)
					for k, v in files.iteritems():
						filename = v[0]
						fileContents = v[1]
						s.write('--%s\r\n' % (boundary))
						s.write('Content-Disposition: form-data; name="%s"; filename="%s"\r\n' % (k, filename))
						s.write('Content-Type: application/octet-stream\r\n')
						s.write('Content-Transfer-Encoding: binary\r\n')
						s.write('\r\n')
						s.write(fileContents)
						s.write('\r\n')

					for k, v in postData.iteritems():
						s.write('--%s\r\n' % (boundary))
						s.write('Content-Disposition: form-data; name="%s"\r\n' % (k))
						s.write('\r\n')
						s.write(str(v))
						s.write('\r\n')
					s.write('--%s--\r\n' % (boundary))

					self._http.request(method, url, s, {"Content-type": "multipart/form-data; boundary=%s" % (boundary), "Content-Length": len(s)})
				elif postData is not None:
					self._http.request(method, url, urllib.urlencode(postData), {"Content-type": "application/x-www-form-urlencoded"})
				else:
					self._http.request(method, url)
			except IOError:
				self._http.close()
				continue
			try:
				response = self._http.getresponse()
				responseText = response.read()
			except:
				self._http.close()
				continue
			try:
				if responseText == '':
					return None
				return json.loads(responseText)
			except ValueError:
				print response.getheaders()
				print responseText
				error = 'Failed to decode JSON response'
		self._hostReachable = False
		return {'error': error}


class FakeYoumagine(Youmagine):
	"""
	Fake Youmagine class to test without internet, acts the same as the YouMagine class, but without going to the internet.
	Assists in testing UI features.
	"""
	def __init__(self, authToken, callback):
		super(FakeYoumagine, self).__init__(authToken)
		self._authUrl = 'file:///C:/Models/output.html'
		self._authToken = None

	def isAuthorized(self):
		if self._authToken is None:
			return False
		if self._userName is None:
			self._userName = 'FakeYoumagine'
			self._userID = '1'
		return True

	def isHostReachable(self):
		return True

	def createDesign(self, name, description, category, license):
		return 1

	def publishDesign(self, id):
		pass

	def createDocument(self, designId, name, contents):
		print "Create document: %s" % (name)
		f = open("C:/models/%s" % (name), "wb")
		f.write(contents)
		f.close()
		return 1

	def createImage(self, designId, name, contents):
		print "Create image: %s" % (name)
		f = open("C:/models/%s" % (name), "wb")
		f.write(contents)
		f.close()
		return 1

	def listDesigns(self):
		return []

	def _request(self, method, url, postData = None, files = None):
		print "Err: Tried to do request: %s %s" % (method, url)

########NEW FILE########
__FILENAME__ = pauseAtZ
#Name: Pause at height
#Info: Pause the printer at a certain height
#Depend: GCode
#Type: postprocess
#Param: pauseLevel(float:5.0) Pause height (mm)
#Param: parkX(float:190) Head park X (mm)
#Param: parkY(float:190) Head park Y (mm)
#Param: retractAmount(float:5) Retraction amount (mm)

__copyright__ = "Copyright (C) 2013 David Braam - Released under terms of the AGPLv3 License"
import re

def getValue(line, key, default = None):
	if not key in line or (';' in line and line.find(key) > line.find(';')):
		return default
	subPart = line[line.find(key) + 1:]
	m = re.search('^[0-9]+\.?[0-9]*', subPart)
	if m is None:
		return default
	try:
		return float(m.group(0))
	except:
		return default

with open(filename, "r") as f:
	lines = f.readlines()

z = 0.
x = 0.
y = 0.
pauseState = 0
currentSectionType = 'STARTOFFILE'
with open(filename, "w") as f:
	for line in lines:
		if line.startswith(';'):
			if line.startswith(';TYPE:'):
				currentSectionType = line[6:].strip()
			f.write(line)
			continue
		if getValue(line, 'G', None) == 1 or getValue(line, 'G', None) == 0:
			newZ = getValue(line, 'Z', z)
			x = getValue(line, 'X', x)
			y = getValue(line, 'Y', y)
			if newZ != z and currentSectionType != 'CUSTOM':
				z = newZ
				if z < pauseLevel and pauseState == 0:
					pauseState = 1
				if z >= pauseLevel and pauseState == 1:
					pauseState = 2
					f.write(";TYPE:CUSTOM\n")
					#Retract
					f.write("M83\n")
					f.write("G1 E-%f F6000\n" % (retractAmount))
					#Move the head away
					f.write("G1 X%f Y%f F9000\n" % (parkX, parkY))
					if z < 15:
						f.write("G1 Z15 F300\n")
					#Wait till the user continues printing
					f.write("M0\n")
					#Push the filament back, and retract again, the properly primes the nozzle when changing filament.
					f.write("G1 E%f F6000\n" % (retractAmount))
					f.write("G1 E-%f F6000\n" % (retractAmount))
					#Move the head back
					if z < 15:
						f.write("G1 Z%f F300\n" % (z+1))
					f.write("G1 X%f Y%f F9000\n" % (x, y))
					f.write("G1 E%f F6000\n" % (retractAmount))
					f.write("G1 F9000\n")
					f.write("M82\n")
		f.write(line)

########NEW FILE########
__FILENAME__ = script
#Name: Pronterface UI
#Info: Pronterface like UI for Cura
#Depend: printwindow
#Type: printwindow

# Printer UI based on the Printrun interface by Kliment.
# Printrun is GPLv3, so this file, and the used images are GPLv3

setImage('image.png', 'map.png')

addColorCommand(0, 0, 255, sendGCode, "G91; G1 X100 F2000; G90")
addColorCommand(0, 0, 240, sendGCode, "G91; G1 X10 F2000; G90")
addColorCommand(0, 0, 220, sendGCode, "G91; G1 X1 F2000; G90")
addColorCommand(0, 0, 200, sendGCode, "G91; G1 X0.1 F2000; G90")
addColorCommand(0, 0, 180, sendGCode, "G91; G1 X-0.1 F2000; G90")
addColorCommand(0, 0, 160, sendGCode, "G91; G1 X-1 F2000; G90")
addColorCommand(0, 0, 140, sendGCode, "G91; G1 X-10 F2000; G90")
addColorCommand(0, 0, 120, sendGCode, "G91; G1 X-100 F2000; G90")

addColorCommand(0, 255, 0, sendGCode, "G91; G1 Y100 F2000; G90")
addColorCommand(0, 240, 0, sendGCode, "G91; G1 Y10 F2000; G90")
addColorCommand(0, 220, 0, sendGCode, "G91; G1 Y1 F2000; G90")
addColorCommand(0, 200, 0, sendGCode, "G91; G1 Y0.1 F2000; G90")
addColorCommand(0, 180, 0, sendGCode, "G91; G1 Y-0.1 F2000; G90")
addColorCommand(0, 160, 0, sendGCode, "G91; G1 Y-1 F2000; G90")
addColorCommand(0, 140, 0, sendGCode, "G91; G1 Y-10 F2000; G90")
addColorCommand(0, 120, 0, sendGCode, "G91; G1 Y-100 F2000; G90")

addColorCommand(255, 0, 0, sendGCode, "G91; G1 Z10 F200; G90")
addColorCommand(220, 0, 0, sendGCode, "G91; G1 Z1 F200; G90")
addColorCommand(200, 0, 0, sendGCode, "G91; G1 Z0.1 F200; G90")
addColorCommand(180, 0, 0, sendGCode, "G91; G1 Z-0.1 F200; G90")
addColorCommand(160, 0, 0, sendGCode, "G91; G1 Z-1 F200; G90")
addColorCommand(140, 0, 0, sendGCode, "G91; G1 Z-10 F200; G90")

addColorCommand(255, 180, 0, sendGCode, "G91; G1 E10 F120; G90")
addColorCommand(255, 160, 0, sendGCode, "G91; G1 E1 F120; G90")
addColorCommand(255, 140, 0, sendGCode, "G91; G1 E0.1 F120; G90")
addColorCommand(255, 120, 0, sendGCode, "G91; G1 E-0.1 F120; G90")
addColorCommand(255, 100, 0, sendGCode, "G91; G1 E-1 F120; G90")
addColorCommand(255,  80, 0, sendGCode, "G91; G1 E-10 F120; G90")

addColorCommand(255, 255, 0, sendGCode, "G28")
addColorCommand(240, 255, 0, sendGCode, "G28 X0")
addColorCommand(220, 255, 0, sendGCode, "G28 Y0")
addColorCommand(200, 255, 0, sendGCode, "G28 Z0")

addSpinner(180, 0, 160, sendGCode, "M104 S%d")
addSpinner(180, 0, 180, sendGCode, "M140 S%d")

addTerminal(255, 0, 255)
addTemperatureGraph(180, 0, 255)
addProgressbar(255, 200, 200)

addButton(0, 255, 255, 'Connect', connect)
addButton(0, 240, 255, 'Print', startPrint)
addButton(0, 220, 255, 'Pause', pausePrint)
addButton(0, 200, 255, 'Cancel', cancelPrint)
addButton(0, 180, 255, 'Error log', showErrorLog)

########NEW FILE########
__FILENAME__ = TweakAtZ
#Name: Tweak At Z 3.1.2
#Info: Change printing parameters at a given height
#Help: TweakAtZ
#Depend: GCode
#Type: postprocess
#Param: targetZ(float:5.0) Z height to tweak at (mm)
#Param: targetL(int:) (ALT) Layer no. to tweak at
#Param: speed(int:) New Speed (%)
#Param: flowrate(int:) New Flow Rate (%)
#Param: platformTemp(int:) New Bed Temp (deg C)
#Param: extruderOne(int:) New Extruder 1 Temp (deg C)
#Param: extruderTwo(int:) New Extruder 2 Temp (deg C)
#Ex3 #Param: extruderThree(int:) New Extruder 3 Temp (deg C)
#Param: fanSpeed(int:) New Fan Speed (0-255 PWM)

## Written by Steven Morlock, smorloc@gmail.com
## Modified by Ricardo Gomez, ricardoga@otulook.com, to add Bed Temperature and make it work with Cura_13.06.04+
## Modified by Stefan Heule, Dim3nsioneer@gmx.ch, to add Flow Rate, restoration of initial values when returning to low Z, extended stage numbers, direct stage manipulation by GCODE-comments, UltiGCode regocnition, addition of fan speed, alternative selection by layer no., disabling extruder three
## This script is licensed under the Creative Commons - Attribution - Share Alike (CC BY-SA) terms

# Uses -
# M220 S<factor in percent> - set speed factor override percentage
# M221 S<factor in percent> - set flow factor override percentage
# M104 S<temp> T<0-#toolheads> - set extruder <T> to target temperature <S>
# M140 S<temp> - set bed target temperature
# M106 S<PWM> - set fan speed to target speed <S>

#history / changelog:
#V3.0.1: TweakAtZ-state default 1 (i.e. the plugin works without any TweakAtZ comment)
#V3.1:   Recognizes UltiGCode and deactivates value reset, fan speed added, alternatively layer no. to tweak at, extruder three temperature disabled by '#Ex3'
#V3.1.1: Bugfix reset flow rate
#V3.1.2: Bugfix disable TweakAtZ on Cool Head Lift / Retraction Hop

version = '3.1.2'

import re

def getValue(line, key, default = None):
	if not key in line or (';' in line and line.find(key) > line.find(';') and not ";TweakAtZ" in key and not ";LAYER:" in key):
		return default
	subPart = line[line.find(key) + len(key):] #allows for string lengths larger than 1
        if ";TweakAtZ" in key:
                m = re.search('^[0-3]', subPart)
        elif ";LAYER:" in key:
                m = re.search('^[+-]?[0-9]*', subPart)
        else:
                m = re.search('^[0-9]+\.?[0-9]*', subPart)
	if m == None:
		return default
	try:
		return float(m.group(0))
	except:
		return default

with open(filename, "r") as f:
	lines = f.readlines()

old_speed = 100
old_flowrate = 100
old_platformTemp = -1
old_extruderOne = -1
old_extruderTwo = -1
#Ex3 old_extruderThree = -1
old_fanSpeed = 0
pres_ext = 0
z = 0
x = None
y = None
layer = -100000 #layer no. may be negative (raft) but never that low
state = 1 #state 0: deactivated, state 1: activated, state 2: active, but below z, state 3: active, passed z
old_state = -1
no_reset = 0 #Default setting is reset (ok for Marlin/Sprinter), has to be set to 1 for UltiGCode (work-around for missing default values)

try:
        targetL_i = int(targetL)
        targetZ = 100000
except:
        targetL_i = -100000

with open(filename, "w") as f:
	for line in lines:
		f.write(line)
                if 'FLAVOR:UltiGCode' in line: #Flavor is UltiGCode! No reset of values
                        no_reset = 1
                if ';TweakAtZ-state' in line: #checks for state change comment
                        state = getValue(line, ';TweakAtZ-state', state)
                if ';Small layer' in line: #checks for begin of Cool Head Lift
                        old_state = state
                        state = 0
                if ('G4' in line) and old_state > -1:
                        state = old_state
                        old_state = -1
                if ';LAYER:' in line: #new layer no. found
                        layer = getValue(line, ';LAYER:', layer)
                        if targetL_i > -100000: #target selected by layer no.
                                if state == 2 and layer >= targetL_i: #determine targetZ from layer no.
                                        targetZ = z + 0.001
                if (getValue(line, 'T', None) is not None) and (getValue(line, 'M', None) is None): #looking for single T-command
                        pres_ext = getValue(line, 'T', pres_ext)
                if 'M190' in line or 'M140' in line and state < 3: #looking for bed temp, stops after target z is passed
                        old_platformTemp = getValue(line, 'S', old_platformTemp)
                if 'M109' in line or 'M104' in line and state < 3: #looking for extruder temp, stops after target z is passed
                        if getValue(line, 'T', pres_ext) == 0:
                                old_extruderOne = getValue(line, 'S', old_extruderOne)
                        elif getValue(line, 'T', pres_ext) == 1:
                                old_extruderTwo = getValue(line, 'S', old_extruderTwo)
#Ex3                        elif getValue(line, 'T', pres_ext) == 2:
#Ex3                                old_extruderThree = getValue(line, 'S', old_extruderThree)
                if 'M107' in line: #fan is stopped; is always updated in order not to miss switch off for next object
                        old_fanSpeed = 0
                if 'M106' in line and state < 3: #looking for fan speed
                        old_fanSpeed = getValue(line, 'S', old_fanSpeed)
                if 'M221' in line and state < 3: #looking for flow rate
                        old_flowrate = getValue(line, 'S', old_flowrate)
		if 'G1' in line or 'G0' in line:
			newZ = getValue(line, 'Z', z)
			x = getValue(line, 'X', None)
			y = getValue(line, 'Y', None)
			if (newZ != z) and (x is not None) and (y is not None): #no tweaking on retraction hops which have no x and y coordinate
				z = newZ
				if z < targetZ and state == 1:
					state = 2
				if z >= targetZ and state == 2:
					state = 3
                                        if targetL_i > -100000:
                                                f.write(";TweakAtZ V%s: executed at Layer %d\n" % (version,targetL_i))
                                        else:
                                                f.write(";TweakAtZ V%s: executed at %1.2f mm\n" % (version,targetZ))
					if speed is not None and speed != '':
						f.write("M220 S%f\n" % float(speed))
					if flowrate is not None and flowrate != '':
						f.write("M221 S%f\n" % float(flowrate))
					if platformTemp is not None and platformTemp != '':
						f.write("M140 S%f\n" % float(platformTemp))
					if extruderOne is not None and extruderOne != '':
						f.write("M104 S%f T0\n" % float(extruderOne))
					if extruderTwo is not None and extruderTwo != '':
						f.write("M104 S%f T1\n" % float(extruderTwo))
#Ex3					if extruderThree is not None and extruderThree != '':
#Ex3						f.write("M104 S%f T2\n" % float(extruderThree))					
					if fanSpeed is not None and fanSpeed != '':
						f.write("M106 S%d\n" % int(fanSpeed))					
                                if z < targetZ and state == 3: #re-activates the plugin if executed by pre-print G-command, resets settings
                                        state = 2
                                        if no_reset == 0: #executes only for UM Original and UM2 with RepRap flavor
                                                if targetL_i > -100000:
                                                        f.write(";TweakAtZ V%s: reset below Layer %d\n" % (version,targetL_i))
                                                else:
                                                        f.write(";TweakAtZ V%s: reset below %1.2f mm\n" % (version,targetZ))
                                                if speed is not None and speed != '':
                                                        f.write("M220 S%f\n" % float(old_speed))
                                                if flowrate is not None and flowrate != '':
                                                        f.write("M221 S%f\n" % float(old_flowrate))
                                                if platformTemp is not None and platformTemp != '':
                                                        f.write("M140 S%f\n" % float(old_platformTemp))
                                                if extruderOne is not None and extruderOne != '':
                                                        f.write("M104 S%f T0\n" % float(old_extruderOne))
                                                if extruderTwo is not None and extruderTwo != '':
                                                        f.write("M104 S%f T1\n" % float(old_extruderTwo))
#Ex3                                                if extruderThree is not None and extruderThree != '':
#Ex3                                                        f.write("M104 S%f T2\n" % float(old_extruderThree))					
                                                if fanSpeed is not None and fanSpeed != '':
                                                        f.write("M106 S%d;\n" % int(old_fanSpeed))					
				

########NEW FILE########
__FILENAME__ = cura
#!/usr/bin/python

import os, sys

sys.path.insert(1, os.path.dirname(__file__))

try:
	import OpenGL
	import wx
	import serial
	import numpy
	import power
except ImportError as e:
	if e.message[0:16] == 'No module named ':
		module = e.message[16:]

		if module == 'OpenGL':
			module = 'PyOpenGL'
		elif module == 'serial':
			module = 'pyserial'
		print 'Requires ' + module

		if module == 'power':
			print "Install from: https://github.com/GreatFruitOmsk/Power"
		else:
			print "Try sudo easy_install " + module
		print e.message
    
	exit(1)


import Cura.cura as cura

cura.main()

########NEW FILE########
