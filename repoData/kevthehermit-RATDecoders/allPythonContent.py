__FILENAME__ = adWind
#!/usr/bin/env python
'''
adWind Rat Config Decoder
'''


__description__ = 'adWind Rat Config Extractor'
__author__ = 'Kevin Breen http://techanarchy.net http://malwareconfig.com'
__version__ = '0.1'
__date__ = '2014/04/10'

#Standard Imports Go Here
import os
import sys
import string
import binascii
from zipfile import ZipFile
from cStringIO import StringIO
import xml.etree.ElementTree as ET
from optparse import OptionParser

#Non Standard Imports
try:
	from Crypto.Cipher import ARC4
	from Crypto.Cipher import DES
except ImportError:
	print "[+] Couldn't Import Cipher, try 'sudo pip install pycrypto'"


# Main Decode Function Goes Here
'''
data is a read of the file
Must return a python dict of values
'''

def run(data):	
	Key = "awenubisskqi"
	newZip = StringIO(data)
	rawConfig = {}
	with ZipFile(newZip, 'r') as zip:
		for name in zip.namelist():
			if name == "config.xml": # contains the encryption key
				# We need two attempts here first try DES for V1 If not try RC4 for V2
				try:
					config = zip.read(name)
					result = DecryptDES(Key[:-4], config)
				except:
					config = zip.read(name)
					result = DecryptRC4(Key, config)								
				xml = filter(lambda x: x in string.printable, result)
				root = ET.fromstring(xml)
				for child in root:
					if child.text.startswith("Adwind RAT"):
						rawConfig["Version"] = child.text
					else:
						rawConfig[child.attrib["key"]] = child.text
				newConfig = sortConfig(rawConfig)
				return newConfig
	
		
#Helper Functions Go Here	


def sortConfig(oldConfig):
	if oldConfig["Version"] == "Adwind RAT v1.0":
		newConfig = {}
		newConfig["Version"] = oldConfig["Version"]
		newConfig["Delay"] = oldConfig["delay"]
		newConfig["Domain"] = oldConfig["dns"]
		newConfig["Install Flag"] = oldConfig["instalar"]
		newConfig["Jar Name"] = oldConfig["jarname"]
		newConfig["Reg Key"] = oldConfig["keyClase"]
		newConfig["Install Folder"] = oldConfig["nombreCarpeta"]
		newConfig["Password"] = oldConfig["password"]
		newConfig["Campaign ID"] = oldConfig["prefijo"]
		newConfig["Port1"] = oldConfig["puerto1"]
		newConfig["Port2"] = oldConfig["puerto2"]
		newConfig["Reg Value"] = oldConfig["regname"]
		print newConfig
		return newConfig

	if oldConfig["Version"] == "Adwind RAT v2.0":
		newConfig = {}
		newConfig["Version"] = oldConfig["Version"]
		newConfig["Delay"] = oldConfig["delay"]
		newConfig["Domain"] = oldConfig["dns"]
		newConfig["Install Flag"] = oldConfig["instalar"]
		newConfig["Reg Key"] = oldConfig["keyClase"]
		newConfig["Password"] = oldConfig["password"]
		newConfig["Campaign ID"] = oldConfig["prefijo"]
		newConfig["Port1"] = oldConfig["puerto"]
		print newConfig
		return newConfig
	
	return oldConfig
		
def DecryptDES(enckey, data):
	cipher = DES.new(enckey, DES.MODE_ECB) # set the ciper
	return cipher.decrypt(data) # decrpyt the data
	
def DecryptRC4(enckey, data):
	cipher = ARC4.new(enckey) # set the ciper
	return cipher.decrypt(data) # decrpyt the data


#Recursive Function Goes Here

def runRecursive(folder, output):
	counter1 = 0
	counter2 = 0
	print "[+] Writing Configs to File {0}".format(output)
	with open(output, 'a+') as out:
		#This line will need changing per Decoder
		out.write("Filename,Domain, Port, Install Path, Install Name, StartupKey, Campaign ID, Mutex Main, Mutex Per, YPER, YGRB, Mutex Grabber, Screen Rec Link, Mutex 4, YVID, YIM, No, Smart, Plugins, Flag1, Flag2, Flag3, Flag4, WebPanel, Remote Delay\n")	
		for server in os.listdir(folder):
			fileData = open(os.path.join(folder,server), 'rb').read()
			config = run(fileData)
			if config != None:
				#This line will need changing per Decoder
				out.write('{0},{1},{2},{3},{4},{5},{6},{7},{8},{9},{10},{11},{12},{13},{14},{15},{16},{17},{18},{19},{20},{21},{22},{23},{24},{25}\n'.format(server, config["Domain"],config["Port"],config["Install Path"],config["Install Name"],config["Startup Key"],config["Campaign ID"],config["Mutex Main"],config["Mutex Per"],config["YPER"],config["YGRB"],config["Mutex Grabber"],config["Screen Rec Link"],config["Mutex 4"],config["YVID"],config["YIM"],config["NO"],config["Smart Broadcast"],config["YES"],config["Plugins"],config["Flag1"],config["Flag2"],config["Flag3"],config["Flag4"],config["WebPanel"],config["Remote Delay"]))
				counter1 += 1
			counter2 += 1
	print "[+] Decoded {0} out of {1} Files".format(counter1, counter2)
	return "Complete"

# Main

if __name__ == "__main__":
	parser = OptionParser(usage='usage: %prog inFile outConfig\n' + __description__, version='%prog ' + __version__)
	parser.add_option("-r", "--recursive", action='store_true', default=False, help="Recursive Mode")
	(options, args) = parser.parse_args()
	# If we dont have args quit with help page
	if len(args) > 0:
		pass
	else:
		parser.print_help()
		sys.exit()
	# if we want a recursive extract run this function
	if options.recursive == True:
		if len(args) == 2:
			runRecursive(args[0], args[1])
			sys.exit()
		else:
			print "[+] You need to specify Both Dir to read AND Output File"
			parser.print_help()
			sys.exit()
	
	# If not recurisve try to open file
	try:
		print "[+] Reading file"
		fileData = open(args[0], 'rb').read()
	except:
		print "[+] Couldn't Open File {0}".format(args[0])
	#Run the config extraction
	print "[+] Searching for Config"
	config = run(fileData)
	#If we have a config figure out where to dump it out.
	if config == None:
		print "[+] Config not found"
		sys.exit()
	#if you gave me two args im going to assume the 2nd arg is where you want to save the file
	if len(args) == 2:
		print "[+] Writing Config to file {0}".format(args[1])
		with open(args[1], 'a') as outFile:
			for key, value in sorted(config.iteritems()):
				clean_value = filter(lambda x: x in string.printable, value)
				outFile.write("Key: {0}\t Value: {1}\n".format(key,clean_value))
	# if no seconds arg then assume you want it printing to screen
	else:
		print "[+] Printing Config to screen"
		for key, value in sorted(config.iteritems()):
			clean_value = filter(lambda x: x in string.printable, value)
			print "   [-] Key: {0}\t Value: {1}".format(key,clean_value)
		print "[+] End of Config"

########NEW FILE########
__FILENAME__ = Arcom
#!/usr/bin/env python
'''
ArCom Rat Config Decoder
'''


__description__ = 'ArCom Rat Config Extractor'
__author__ = 'Kevin Breen http://techanarchy.net http://malwareconfig.com'
__version__ = '0.1'
__date__ = '2014/04/10'

#Imports Go Here
import os
import sys
import base64
import string
from optparse import OptionParser
try:
	from Crypto.Cipher import Blowfish
except ImportError:
	print "[+] Couldn't Import Cipher, try 'sudo pip install pycrypto'"


# Main Decode Function Goes Here

key = "CVu3388fnek3W(3ij3fkp0930di"
def run(data):
	dict = {}
	try:
		config = data.split("\x18\x12\x00\x00")[1].replace('\xA3\x24\x25\x21\x64\x01\x00\x00','')
		configdecode = base64.b64decode(config)
		configDecrypt = decryptBlowfish(key, configdecode)
		parts = configDecrypt.split('|')
		if len(parts) > 3:
			dict["Domain"] = parts[0]
			dict["Port"] = parts[1]
			dict["Install Path"] = parts[2]
			dict["Install Name"] = parts[3]
			dict["Startup Key"] = parts[4]
			dict["Campaign ID"] = parts[5]
			dict["Mutex Main"] = parts[6]
			dict["Mutex Per"] = parts[7]
			dict["YPER"] = parts[8]
			dict["YGRB"] = parts[9]
			dict["Mutex Grabber"] = parts[10]
			dict["Screen Rec Link"] = parts[11]
			dict["Mutex 4"] = parts[12]
			dict["YVID"] = parts[13]
			dict["YIM"] = parts[14]
			dict["NO"] = parts[15]
			dict["Smart Broadcast"] = parts[16]
			dict["YES"] = parts[17]
			dict["Plugins"] = parts[18]
			dict["Flag1"] = parts[19]
			dict["Flag2"] = parts[20]
			dict["Flag3"] = parts[21]
			dict["Flag4"] = parts[22]
			dict["WebPanel"] = parts[23]
			dict["Remote Delay"] = parts[24]
			return dict
	except:
		return None
		
#Helper Functions Go Here

def decryptBlowfish(key, data):
	cipher = Blowfish.new(key)
	return cipher.decrypt(data)

#Recursive Function Goes Here

def runRecursive(folder, output):
	counter1 = 0
	counter2 = 0
	print "[+] Writing Configs to File {0}".format(output)
	with open(output, 'a+') as out:
		out.write("Filename,Domain, Port, Install Path, Install Name, StartupKey, Campaign ID, Mutex Main, Mutex Per, YPER, YGRB, Mutex Grabber, Screen Rec Link, Mutex 4, YVID, YIM, No, Smart, Plugins, Flag1, Flag2, Flag3, Flag4, WebPanel, Remote Delay\n")	
		for server in os.listdir(folder):
			fileData = open(os.path.join(folder,server), 'rb').read()
			dict = run(fileData)
			if dict != None:
				out.write('{0},{1},{2},{3},{4},{5},{6},{7},{8},{9},{10},{11},{12},{13},{14},{15},{16},{17},{18},{19},{20},{21},{22},{23},{24},{25}\n'.format(server, dict["Domain"],dict["Port"],dict["Install Path"],dict["Install Name"],dict["Startup Key"],dict["Campaign ID"],dict["Mutex Main"],dict["Mutex Per"],dict["YPER"],dict["YGRB"],dict["Mutex Grabber"],dict["Screen Rec Link"],dict["Mutex 4"],dict["YVID"],dict["YIM"],dict["NO"],dict["Smart Broadcast"],dict["YES"],dict["Plugins"],dict["Flag1"],dict["Flag2"],dict["Flag3"],dict["Flag4"],dict["WebPanel"],dict["Remote Delay"]))
				counter1 += 1
			counter2 += 1
	print "[+] Decoded {0} out of {1} Files".format(counter1, counter2)
	return "Complete"

# Main

if __name__ == "__main__":
	parser = OptionParser(usage='usage: %prog inFile outConfig\n' + __description__, version='%prog ' + __version__)
	parser.add_option("-r", "--recursive", action='store_true', default=False, help="Recursive Mode")
	(options, args) = parser.parse_args()
	# If we dont have args quit with help page
	if len(args) > 0:
		pass
	else:
		parser.print_help()
		sys.exit()
	# if we want a recursive extract run this function
	if options.recursive == True:
		if len(args) == 2:
			runRecursive(args[0], args[1])
			sys.exit()
		else:
			print "[+] You need to specify Both Dir to read AND Output File"
			parser.print_help()
			sys.exit()
	
	# If not recurisve try to open file
	try:
		print "[+] Reading file"
		fileData = open(args[0], 'rb').read()
	except:
		print "[+] Couldn't Open File {0}".format(args[0])
	#Run the config extraction
	print "[+] Searching for Config"
	config = run(fileData)
	#If we have a config figure out where to dump it out.
	if config == None:
		print "[+] Config not found"
		sys.exit()
	#if you gave me two args im going to assume the 2nd arg is where you want to save the file
	if len(args) == 2:
		print "[+] Writing Config to file {0}".format(args[1])
		with open(args[1], 'a') as outFile:
			for key, value in sorted(config.iteritems()):
				clean_value = filter(lambda x: x in string.printable, value)
				outFile.write("Key: {0}\t Value: {1}\n".format(key,clean_value))
	# if no seconds arg then assume you want it printing to screen
	else:
		print "[+] Printing Config to screen"
		for key, value in sorted(config.iteritems()):
			clean_value = filter(lambda x: x in string.printable, value)
			print "   [-] Key: {0}\t Value: {1}".format(key,clean_value)
		print "[+] End of Config"

########NEW FILE########
__FILENAME__ = BlackNix
#!/usr/bin/env python
'''
BlackNix Rat Config Decoder
'''


__description__ = 'BlackNix Rat Config Extractor'
__author__ = 'Kevin Breen http://techanarchy.net http://malwareconfig.com'
__version__ = '0.1'
__date__ = '2014/04/10'

#Standard Imports Go Here
import os
import sys
import string
from zipfile import ZipFile
from cStringIO import StringIO
from optparse import OptionParser

#Non Standard Imports



# Main Decode Function Goes Here
'''
data is a read of the file
Must return a python dict of values
'''

def run(data):
	conf = {}
	config = configExtract(data)
	if config != None:
		for i in range(0,len(config)):
			print i, decode(config[i])[::-1]
		conf["Mutex"] = decode(config[1])[::-1]
		conf["Anti Sandboxie"] = decode(config[2])[::-1]
		conf["Max Folder Size"] = decode(config[3])[::-1]
		conf["Delay Time"] = decode(config[4])[::-1]
		conf["Password"] = decode(config[5])[::-1]
		conf["Kernel Mode Unhooking"] = decode(config[6])[::-1]
		conf["User More Unhooking"] = decode(config[7])[::-1]
		conf["Melt Server"] = decode(config[8])[::-1]
		conf["Offline Screen Capture"] = decode(config[9])[::-1]
		conf["Offline Keylogger"] = decode(config[10])[::-1]
		conf["Copy To ADS"] = decode(config[11])[::-1]
		conf["Domain"] = decode(config[12])[::-1]
		conf["Persistence Thread"] = decode(config[13])[::-1]
		conf["Active X Key"] = decode(config[14])[::-1]
		conf["Registry Key"] = decode(config[15])[::-1]
		conf["Active X Run"] = decode(config[16])[::-1]
		conf["Registry Run"] = decode(config[17])[::-1]
		conf["Safe Mode Startup"] = decode(config[18])[::-1]
		conf["Inject winlogon.exe"] = decode(config[19])[::-1]
		conf["Install Name"] = decode(config[20])[::-1]
		conf["Install Path"] = decode(config[21])[::-1]
		conf["Campaign Name"] = decode(config[22])[::-1]
		conf["Campaign Group"] = decode(config[23])[::-1]
	return conf
	
		
#Helper Functions Go Here

def configExtract(rawData):
	try:
		pe = pefile.PE(data=rawData)

		try:
		  rt_string_idx = [
		  entry.id for entry in 
		  pe.DIRECTORY_ENTRY_RESOURCE.entries].index(pefile.RESOURCE_TYPE['RT_RCDATA'])
		except ValueError, e:
			sys.exit()
		except AttributeError, e:
			sys.exit()

		rt_string_directory = pe.DIRECTORY_ENTRY_RESOURCE.entries[rt_string_idx]

		for entry in rt_string_directory.directory.entries:
			if str(entry.name) == "SETTINGS":
				data_rva = entry.directory.entries[0].data.struct.OffsetToData
				size = entry.directory.entries[0].data.struct.Size
				data = pe.get_memory_mapped_image()[data_rva:data_rva+size]
				config = data.split('}')
				return config
	except:
		return None		

def decode(string):
	result = ""
	for i in range(0,len(string)):
		a = ord(string[i])
		result += chr(a-1)
	return result
	

#Recursive Function Goes Here


# Main

if __name__ == "__main__":
	parser = OptionParser(usage='usage: %prog inFile outConfig\n' + __description__, version='%prog ' + __version__)
	parser.add_option("-r", "--recursive", action='store_true', default=False, help="Recursive Mode")
	(options, args) = parser.parse_args()
	# If we dont have args quit with help page
	if len(args) > 0:
		pass
	else:
		parser.print_help()
		sys.exit()
	# if we want a recursive extract run this function
	if options.recursive == True:
		print "[+] Sorry Not Here Yet Come Back Soon"
	
	# If not recurisve try to open file
	try:
		print "[+] Reading file"
		fileData = open(args[0], 'rb').read()
	except:
		print "[+] Couldn't Open File {0}".format(args[0])
	#Run the config extraction
	print "[+] Searching for Config"
	config = run(fileData)
	#If we have a config figure out where to dump it out.
	if config == None:
		print "[+] Config not found"
		sys.exit()
	#if you gave me two args im going to assume the 2nd arg is where you want to save the file
	if len(args) == 2:
		print "[+] Writing Config to file {0}".format(args[1])
		with open(args[1], 'a') as outFile:
			for key, value in sorted(config.iteritems()):
				clean_value = filter(lambda x: x in string.printable, value)
				outFile.write("Key: {0}\t Value: {1}\n".format(key,clean_value))
	# if no seconds arg then assume you want it printing to screen
	else:
		print "[+] Printing Config to screen"
		for key, value in sorted(config.iteritems()):
			clean_value = filter(lambda x: x in string.printable, value)
			print "   [-] Key: {0}\t Value: {1}".format(key,clean_value)
		print "[+] End of Config"

########NEW FILE########
__FILENAME__ = BlackShades
#!/usr/bin/env python
'''
BlackShades RAT Decoder

Original Script by Brian Wallace (@botnet_hunter)


'''

__description__ = 'DarkComet Rat Config Extractor\nOriginal Script by Brian Wallace (@botnet_hunter)'
__author__ = 'Kevin Breen http://techanarchy.net'
__OrigionalCode__ = 'v1.0.0 by Brian Wallace (@botnet_hunter)'
__version__ = '0.1'
__date__ = '2014/05/23'

import os
import sys
import string
import re
from optparse import OptionParser

prng_seed = 0


def is_valid_config(config):
    if config[:3] != "\x0c\x0c\x0c":
        return False
    if config.count("\x0C\x0C\x0C") < 15:
        return False
    return True


def get_next_rng_value():
    global prng_seed
    prng_seed = ((prng_seed * 1140671485 + 12820163) & 0xffffff)
    return prng_seed / 65536

def decrypt_configuration(hex):
    global prng_seed
    ascii = hex.decode('hex')
    tail = ascii[0x20:]

    pre_check = []
    for x in xrange(3):
        pre_check.append(ord(tail[x]) ^ 0x0c)

    for x in xrange(0xffffff):
        prng_seed = x
        if get_next_rng_value() != pre_check[0] or get_next_rng_value() != pre_check[1] or get_next_rng_value() != pre_check[2]:
            continue
        prng_seed = x
        config = "".join((chr(ord(c) ^ int(get_next_rng_value())) for c in tail))
        if is_valid_config(config):
            return config.split("\x0c\x0c\x0c")
    return None
 

def config_extract(raw_data):
    config_pattern = re.findall('[0-9a-fA-F]{154,}', raw_data)
    for s in config_pattern:
        if (len(s) % 2) == 1:
            s = s[:-1]
    return s

def config_parser(config):
    config_dict = {}
    config_dict['Domain'] = config[1]
    config_dict['Client Control Port'] = config[2]
    config_dict['Client Transfer Port'] = config[3]
    config_dict['Campaign ID'] = config[4]
    config_dict['File Name'] = config[5]
    config_dict['Install Path'] = config[6]
    config_dict['Registry Key'] = config[7]
    config_dict['ActiveX Key'] = config[8]
    config_dict['Install Flag'] = config[9]
    config_dict['Hide File'] = config[10]
    config_dict['Melt File'] = config[11]
    config_dict['Delay'] = config[12]
    config_dict['USB Spread'] = config[13]
    config_dict['Mutex'] = config[14]
    config_dict['Log File'] = config[15]
    config_dict['Folder Name'] = config[16]
    config_dict['Smart DNS'] = config[17]
    config_dict['Protect Process'] = config[18]
    return config_dict
        
def run(data):
    raw_config = config_extract(data)
    config = decrypt_configuration(raw_config)
    if config is not None and len(config) > 15:
        sorted_config = config_parser(config)
        return sorted_config
    return None


#Recursive Function Goes Here

def runRecursive(folder, output):
	counter1 = 0
	counter2 = 0
	print "[+] Writing Configs to File {0}".format(output)
	with open(output, 'a+') as out:
		#This line will need changing per Decoder
		out.write("File Name, Campaign ID, Domain, Transfer Port, Control Port, File Name, Install Path, Registry Key, ActiveX Key, Install Flag, Hide File, Melt File, Delay, USB Spread, Mutex, Log File, Folder Name, Smart DNS, Protect Process\n")	
		for server in os.listdir(folder):
			fileData = open(os.path.join(folder,server), 'rb').read()
			configOut = run(fileData)
			if configOut != None:
				#This line will need changing per Decoder
				out.write('{0},{1},{2},{3},{4},{5},{6},{7},{8},{9},{10},{11},{12},{13},{14},{15},{16},{17},{18}\n'.format(server, configOut["Campaign ID"],configOut["Domain"],configOut["Client Transfer Port"],configOut["Client Control Port"],configOut["File Name"],configOut["Install Path"],configOut["Registry Key"],configOut["ActiveX Key"],configOut["Install Flag"],configOut["Hide File"],configOut["Melt File"],configOut["Delay"],configOut["USB Spread"],configOut["Mutex"],configOut["Log File"],configOut["Folder Name"],configOut["Smart DNS"],configOut["Protect Process"]))
				counter1 += 1
			counter2 += 1
	print "[+] Decoded {0} out of {1} Files".format(counter1, counter2)
	return "Complete"


if __name__ == "__main__":
	parser = OptionParser(usage='usage: %prog inFile outConfig\n' + __description__, version='%prog ' + __version__)
	parser.add_option("-r", "--recursive", action='store_true', default=False, help="Recursive Mode")
	(options, args) = parser.parse_args()
	# If we dont have args quit with help page
	if len(args) > 0:
		pass
	else:
		parser.print_help()
		sys.exit()
	# if we want a recursive extract run this function
	if options.recursive == True:
		if len(args) == 2:
			runRecursive(args[0], args[1])
			sys.exit()
		else:
			print "[+] You need to specify Both Dir to read AND Output File"
			parser.print_help()
			sys.exit()
	
	# If not recurisve try to open file
	try:
		print "[+] Reading file"
		fileData = open(args[0], 'rb').read()
	except:
		print "[+] Couldn't Open File {0}".format(args[0])
        sys.exit()
	#Run the config extraction
	print "[+] Searching for Config"
	config = run(fileData)
	#If we have a config figure out where to dump it out.
	if config == None:
		print "[+] Config not found"
		sys.exit()
	#if you gave me two args im going to assume the 2nd arg is where you want to save the file
	if len(args) == 2:
		print "[+] Writing Config to file {0}".format(args[1])
		with open(args[1], 'a') as outFile:
			for key, value in sorted(config.iteritems()):
				clean_value = filter(lambda x: x in string.printable, value)
				outFile.write("Key: {0}\t Value: {1}\n".format(key,clean_value))
	# if no seconds arg then assume you want it printing to screen
	else:
		print "[+] Printing Config to screen"
		for key, value in sorted(config.iteritems()):
			clean_value = filter(lambda x: x in string.printable, value)
			print "   [-] Key: {0}\t Value: {1}".format(key,clean_value)
		print "[+] End of Config"

########NEW FILE########
__FILENAME__ = BlueBanana
#!/usr/bin/env python
'''
BlueBanana Rat Config Decoder
'''


__description__ = 'BlueBanana Rat Config Extractor'
__author__ = 'Kevin Breen http://techanarchy.net http://malwareconfig.com'
__version__ = '0.1'
__date__ = '2014/04/10'

#Standard Imports Go Here
import os
import sys
import string
from zipfile import ZipFile
from cStringIO import StringIO
from optparse import OptionParser

#Non Standard Imports
try:
	from Crypto.Cipher import AES
except ImportError:
	print "[+] Couldn't Import Cipher, try 'sudo pip install pycrypto'"


# Main Decode Function Goes Here
'''
data is a read of the file
Must return a python dict of values
'''

def run(data):
	newZip = StringIO(data)
	with ZipFile(newZip) as zip:
		for name in zip.namelist(): # get all the file names
			if name == "config.txt": # this file contains the encrypted config
				conFile = zip.read(name)
	if conFile: # 
		confRaw = decryptConf(conFile)
		conf = configParse(confRaw)
	return conf
	
		
#Helper Functions Go Here

def DecryptAES(enckey, data):
	cipher = AES.new(enckey) # set the cipher
	return cipher.decrypt(data) # decrpyt the data

def decryptConf(conFile):
	key1 = "15af8sd4s1c5s511"
	key2 = "4e3f5a4c592b243f"
	first = DecryptAES(key1, conFile.decode('hex'))
	second = DecryptAES(key2, first[:-16].decode('hex'))
	return second
	
def configParse(confRaw):
	config = {}
	clean = filter(lambda x: x in string.printable, confRaw)
	list = clean.split("<separator>")
	config["Domain"] = list[0]
	config["Password"] = list[1]
	config["Port1"] = list[2]
	config["Port2"] = list[3]
	if len(list) > 4:
		config["InstallName"] = list[4]
		config["JarName"] = list[5]
	return config

#Recursive Function Goes Here


# Main

if __name__ == "__main__":
	parser = OptionParser(usage='usage: %prog inFile outConfig\n' + __description__, version='%prog ' + __version__)
	parser.add_option("-r", "--recursive", action='store_true', default=False, help="Recursive Mode")
	(options, args) = parser.parse_args()
	# If we dont have args quit with help page
	if len(args) > 0:
		pass
	else:
		parser.print_help()
		sys.exit()
	# if we want a recursive extract run this function
	if options.recursive == True:
		print "[+] Sorry Not Here Yet Come Back Soon"
	
	# If not recurisve try to open file
	try:
		print "[+] Reading file"
		fileData = open(args[0], 'rb').read()
	except:
		print "[+] Couldn't Open File {0}".format(args[0])
	#Run the config extraction
	print "[+] Searching for Config"
	config = run(fileData)
	#If we have a config figure out where to dump it out.
	if config == None:
		print "[+] Config not found"
		sys.exit()
	#if you gave me two args im going to assume the 2nd arg is where you want to save the file
	if len(args) == 2:
		print "[+] Writing Config to file {0}".format(args[1])
		with open(args[1], 'a') as outFile:
			for key, value in sorted(config.iteritems()):
				clean_value = filter(lambda x: x in string.printable, value)
				outFile.write("Key: {0}\t Value: {1}\n".format(key,clean_value))
	# if no seconds arg then assume you want it printing to screen
	else:
		print "[+] Printing Config to screen"
		for key, value in sorted(config.iteritems()):
			clean_value = filter(lambda x: x in string.printable, value)
			print "   [-] Key: {0}\t Value: {1}".format(key,clean_value)
		print "[+] End of Config"

########NEW FILE########
__FILENAME__ = Bozok
#!/usr/bin/env python
'''
Bozok Rat Config Decoder
'''


__description__ = 'Bozok Rat Config Extractor'
__author__ = 'Kevin Breen http://techanarchy.net http://malwareconfig.com'
__version__ = '0.2'
__date__ = '2014/04/10'

#Standard Imports Go Here
import os
import sys
import string
from optparse import OptionParser

#Non Standard Imports
import pefile


# Main Decode Function Goes Here
'''
data is a read of the file
Must return a python dict of values
'''

def run(data):
	conf = {}
	rawConfig = configExtract(data).replace('\x00', '')
	config = rawConfig.split("|")
	print config
	if config != None:
		conf["ServerID"] = config[0]
		conf["Mutex"] = config[1]
		conf["InstallName"] = config[2]
		conf["StartupName"] = config[3]
		conf["Extension"] = config[4]
		conf["Password"] = config[5]
		conf["Install Flag"] = config[6]
		conf["Startup Flag"] = config[7]
		conf["Visible Flag"] = config[8]
		conf["Unknown Flag1"] = config[9]
		conf["Unknown Flag2"] = config[10]
		conf["Port"] = config[11]
		conf["Domain"] = config[12]
		conf["Unknown Flag3"] = config[13]
	print conf
	return conf
	
		
#Helper Functions Go Here

def configExtract(rawData):

		pe = pefile.PE(data=rawData)

		try:
		  rt_string_idx = [
		  entry.id for entry in 
		  pe.DIRECTORY_ENTRY_RESOURCE.entries].index(pefile.RESOURCE_TYPE['RT_RCDATA'])
		except ValueError, e:
			sys.exit()
		except AttributeError, e:
			sys.exit()

		rt_string_directory = pe.DIRECTORY_ENTRY_RESOURCE.entries[rt_string_idx]

		for entry in rt_string_directory.directory.entries:
			if str(entry.name) == "CFG":
				data_rva = entry.directory.entries[0].data.struct.OffsetToData
				size = entry.directory.entries[0].data.struct.Size
				data = pe.get_memory_mapped_image()[data_rva:data_rva+size]
				return data


#Recursive Function Goes Here


# Main

if __name__ == "__main__":
	parser = OptionParser(usage='usage: %prog inFile outConfig\n' + __description__, version='%prog ' + __version__)
	parser.add_option("-r", "--recursive", action='store_true', default=False, help="Recursive Mode")
	(options, args) = parser.parse_args()
	# If we dont have args quit with help page
	if len(args) > 0:
		pass
	else:
		parser.print_help()
		sys.exit()
	# if we want a recursive extract run this function
	if options.recursive == True:
		print "[+] Sorry Not Here Yet Come Back Soon"
	
	# If not recurisve try to open file
	try:
		print "[+] Reading file"
		fileData = open(args[0], 'rb').read()
	except:
		print "[+] Couldn't Open File {0}".format(args[0])
	#Run the config extraction
	print "[+] Searching for Config"
	config = run(fileData)
	#If we have a config figure out where to dump it out.
	if config == None:
		print "[+] Config not found"
		sys.exit()
	#if you gave me two args im going to assume the 2nd arg is where you want to save the file
	if len(args) == 2:
		print "[+] Writing Config to file {0}".format(args[1])
		with open(args[1], 'a') as outFile:
			for key, value in sorted(config.iteritems()):
				clean_value = filter(lambda x: x in string.printable, value)
				outFile.write("Key: {0}\t Value: {1}\n".format(key,clean_value))
	# if no seconds arg then assume you want it printing to screen
	else:
		print "[+] Printing Config to screen"
		for key, value in sorted(config.iteritems()):
			clean_value = filter(lambda x: x in string.printable, value)
			print "   [-] Key: {0}\t Value: {1}".format(key,clean_value)
		print "[+] End of Config"

########NEW FILE########
__FILENAME__ = CyberGate
#!/usr/bin/env python
'''
CyberGate Rat Config Decoder
'''


__description__ = 'CyberGate Rat Config Extractor'
__author__ = 'Kevin Breen http://techanarchy.net http://malwareconfig.com'
__version__ = '0.1'
__date__ = '2014/04/10'

#Standard Imports Go Here
import os
import sys
import string
from optparse import OptionParser

#Non Standard Imports
try:
	import pefile
except ImportError:
	print "[+] Couldn't Import Cipher, try 'sudo pip install pefile'"


# Main Decode Function Goes Here
'''
data is a read of the file
Must return a python dict of values
'''

def run(data):
	Config = {}
	rawConfig = configExtract(data)
	if rawConfig != None:
		if len(rawConfig) > 20:
			domains = ""
			ports = ""
			#Config sections 0 - 19 contain a list of Domains and Ports
			for x in range(0,19):
				if len(rawConfig[x]) > 1:
					domains += xorDecode(rawConfig[x]).split(':')[0]
					domains += "|"
					ports += xorDecode(rawConfig[x]).split(':')[1]
					ports += "|"				
			Config["Domain"] = domains
			Config["Port"] = ports
			Config["ServerID"] = xorDecode(rawConfig[20])
			Config["Password"] = xorDecode(rawConfig[21])
			Config["Install Flag"] = xorDecode(rawConfig[22])
			Config["Install Directory"] = xorDecode(rawConfig[25])
			Config["Install File Name"] = xorDecode(rawConfig[26])
			Config["Active X Startup"] = xorDecode(rawConfig[27])
			Config["REG Key HKLM"] = xorDecode(rawConfig[28])
			Config["REG Key HKCU"] = xorDecode(rawConfig[29])
			Config["Enable Message Box"] = xorDecode(rawConfig[30])
			Config["Message Box Icon"] = xorDecode(rawConfig[31])
			Config["Message Box Button"] = xorDecode(rawConfig[32])
			Config["Install Message Title"] = xorDecode(rawConfig[33])
			Config["Install Message Box"] = xorDecode(rawConfig[34]).replace('\r\n', ' ')
			Config["Activate Keylogger"] = xorDecode(rawConfig[35])
			Config["Keylogger Backspace = Delete"] = xorDecode(rawConfig[36])
			Config["Keylogger Enable FTP"] = xorDecode(rawConfig[37])
			Config["FTP Address"] = xorDecode(rawConfig[38])
			Config["FTP Directory"] = xorDecode(rawConfig[39])
			Config["FTP UserName"] = xorDecode(rawConfig[41])
			Config["FTP Password"] = xorDecode(rawConfig[42])
			Config["FTP Port"] = xorDecode(rawConfig[43])
			Config["FTP Interval"] = xorDecode(rawConfig[44])
			Config["Persistance"] = xorDecode(rawConfig[59])
			Config["Hide File"] = xorDecode(rawConfig[60])
			Config["Change Creation Date"] = xorDecode(rawConfig[61])
			Config["Mutex"] = xorDecode(rawConfig[62])		
			Config["Melt File"] = xorDecode(rawConfig[63])
			Config["CyberGate Version"] = xorDecode(rawConfig[67])		
			Config["Startup Policies"] = xorDecode(rawConfig[69])
			Config["USB Spread"] = xorDecode(rawConfig[70])
			Config["P2P Spread"] = xorDecode(rawConfig[71])
			Config["Google Chrome Passwords"] = xorDecode(rawConfig[73])
			Config["Process Injection"] = "Disabled"
			if xorDecode(rawConfig[57]) == 0 or xorDecode(rawConfig[57]) == None:
				Config["Process Injection"] = "Disabled"
			elif xorDecode(rawConfig[57]) == 1:
				Config["Process Injection"] = "Default Browser"
			elif xorDecode(rawConfig[57]) == 2:
				Config["Process Injection"] = xorDecode(rawConfig[58])
		else:
			return None
		return Config
	
		
#Helper Functions Go Here

def xorDecode(data):
	key = 0xBC
	encoded = bytearray(data)
	for i in range(len(encoded)):
		encoded[i] ^= key
	return filter(lambda x: x in string.printable, str(encoded))

def configExtract(rawData):
	try:
		pe = pefile.PE(data=rawData)

		try:
		  rt_string_idx = [
		  entry.id for entry in 
		  pe.DIRECTORY_ENTRY_RESOURCE.entries].index(pefile.RESOURCE_TYPE['RT_RCDATA'])
		except ValueError, e:
			return None
		except AttributeError, e:
			return None

		rt_string_directory = pe.DIRECTORY_ENTRY_RESOURCE.entries[rt_string_idx]

		for entry in rt_string_directory.directory.entries:
			if str(entry.name) == "XX-XX-XX-XX" or str(entry.name) == "CG-CG-CG-CG":
				data_rva = entry.directory.entries[0].data.struct.OffsetToData
				size = entry.directory.entries[0].data.struct.Size
				data = pe.get_memory_mapped_image()[data_rva:data_rva+size]
				config = data.split('####@####')
				return config
	except:
		return None		


#Recursive Function Goes Here

def runRecursive(folder, output):
	counter1 = 0
	counter2 = 0
	print "[+] Writing Configs to File {0}".format(output)
	with open(output, 'a+') as out:
		#This line will need changing per Decoder
		out.write("Filename,Domains, Ports, Campaign ID, Password, Install Flag, Install Dir, Install File Name, ActiveX Key, HKLM Key, HKCU Key, Enable MessageBox, Message Box Icon, Mesage Box Button, Message Title, Message Box Text, Enable Keylogger, KeyLogger Backspace, Keylogger FTP, FTP Address, FTP UserName, FTP Password, FTP Port, FTP Interval, Persistnace, Hide File, Change Creation Date, Mutex, Melt File, Verison, Startup Polocies, USB Spread, P2P Spread, Google Chrome Passwords, Process Injection\n")	
		for server in os.listdir(folder):
			fileData = open(os.path.join(folder,server), 'rb').read()
			Config = run(fileData)
			if Config != None:
				#This line will need changing per Decoder
				out.write('{0},{1},{2},{3},{4},{5},{6},{7},{8},{9},{10},{11},{12},{13},{14},{15},{16},{17},{18},{19},{20},{21},{22},{23},{24},{25},{26},{27},{28},{29},{30},{31},{32},{33},{34},{35}\n'.format(server, Config["Domain"],Config["Port"],Config["ServerID"],Config["Password"],Config["Install Flag"],Config["Install Directory"],Config["Install File Name"],Config["Active X Startup"],Config["REG Key HKLM"],Config["REG Key HKCU"],Config["Enable Message Box"],Config["Message Box Icon"],Config["Message Box Button"],Config["Install Message Title"],Config["Install Message Box"],Config["Activate Keylogger"],Config["Keylogger Backspace = Delete"],Config["Keylogger Enable FTP"],Config["FTP Address"],Config["FTP Directory"],Config["FTP UserName"],Config["FTP Password"],Config["FTP Port"],Config["FTP Interval"],Config["Persistance"],Config["Hide File"],Config["Change Creation Date"],Config["Mutex"],Config["Melt File"],Config["CyberGate Version"],Config["Startup Policies"],Config["USB Spread"],Config["P2P Spread"],Config["Google Chrome Passwords"],Config["Process Injection"]))
				counter1 += 1
			counter2 += 1
	print "[+] Decoded {0} out of {1} Files".format(counter1, counter2)
	return "Complete"

# Main

if __name__ == "__main__":
	parser = OptionParser(usage='usage: %prog inFile outConfig\n' + __description__, version='%prog ' + __version__)
	parser.add_option("-r", "--recursive", action='store_true', default=False, help="Recursive Mode")
	(options, args) = parser.parse_args()
	# If we dont have args quit with help page
	if len(args) > 0:
		pass
	else:
		parser.print_help()
		sys.exit()
	# if we want a recursive extract run this function
	if options.recursive == True:
		if len(args) == 2:
			runRecursive(args[0], args[1])
			sys.exit()
		else:
			print "[+] You need to specify Both Dir to read AND Output File"
			parser.print_help()
			sys.exit()
	
	# If not recurisve try to open file
	try:
		print "[+] Reading file"
		fileData = open(args[0], 'rb').read()
	except:
		print "[+] Couldn't Open File {0}".format(args[0])
	#Run the config extraction
	print "[+] Searching for Config"
	config = run(fileData)
	#If we have a config figure out where to dump it out.
	if config == None:
		print "[+] Config not found"
		sys.exit()
	#if you gave me two args im going to assume the 2nd arg is where you want to save the file
	if len(args) == 2:
		print "[+] Writing Config to file {0}".format(args[1])
		with open(args[1], 'a') as outFile:
			for key, value in sorted(config.iteritems()):
				clean_value = filter(lambda x: x in string.printable, value)
				outFile.write("Key: {0}\t Value: {1}\n".format(key,clean_value))
	# if no seconds arg then assume you want it printing to screen
	else:
		print "[+] Printing Config to screen"
		for key, value in sorted(config.iteritems()):
			clean_value = filter(lambda x: x in string.printable, value)
			print "   [-] Key: {0}\t Value: {1}".format(key,clean_value)
		print "[+] End of Config"

########NEW FILE########
__FILENAME__ = DarkComet
#!/usr/bin/env python
'''
DarkComet Rat Config Decoder
'''

__description__ = 'DarkComet Rat Config Extractor'
__author__ = 'Kevin Breen http://techanarchy.net'
__version__ = '0.1'
__date__ = '2014/03/15'

import sys
import string
from struct import unpack
try:
	import pefile
except ImportError:
	print "Couldnt Import pefile. Try 'sudo pip install pefile'"
from optparse import OptionParser
from binascii import *



def rc4crypt(data, key):
    x = 0
    box = range(256)
    for i in range(256):
        x = (x + box[i] + ord(key[i % len(key)])) % 256
        box[i], box[x] = box[x], box[i]
    x = 0
    y = 0
    out = []
    for char in data:
        x = (x + 1) % 256
        y = (y + box[x]) % 256
        box[x], box[y] = box[y], box[x]
        out.append(chr(ord(char) ^ box[(box[x] + box[y]) % 256]))
    
    return ''.join(out)

def v51_data(data, enckey):
	config = {"FWB": "", "GENCODE": "", "MUTEX": "", "NETDATA": "", "OFFLINEK": "", "SID": "", "FTPUPLOADK": "", "FTPHOST": "", "FTPUSER": "", "FTPPASS": "", "FTPPORT": "", "FTPSIZE": "", "FTPROOT": "", "PWD": ""}
	dec = rc4crypt(unhexlify(data), enckey)
	dec_list = dec.split('\n')
	for entries in dec_list[1:-1]:
		key, value = entries.split('=')
		key = key.strip()
		value = value.rstrip()[1:-1]
		clean_value = filter(lambda x: x in string.printable, value)
		config[key] = clean_value
		config["Version"] = enckey[:-4]
	print config
	return config

def v3_data(data, key):
	config = {"FWB": "", "GENCODE": "", "MUTEX": "", "NETDATA": "", "OFFLINEK": "", "SID": "", "FTPUPLOADK": "", "FTPHOST": "", "FTPUSER": "", "FTPPASS": "", "FTPPORT": "", "FTPSIZE": "", "FTPROOT": "", "PWD": ""}
	dec = rc4crypt(unhexlify(data), key)
	config[str(entry.name)] = dec
	config["Version"] = enckey[:-4]

	return config

def versionCheck(rawData):
	if "#KCMDDC2#" in rawData:
		return "#KCMDDC2#-890"
		
	elif "#KCMDDC4#" in rawData:
		return "#KCMDDC4#-890"
		
	elif "#KCMDDC42#" in rawData:
		return "#KCMDDC42#-890"

	elif "#KCMDDC42F#" in rawData:
		return "#KCMDDC42F#-890"
		
	elif "#KCMDDC5#" in rawData:
		return "#KCMDDC5#-890"

	elif "#KCMDDC51#" in rawData:
		return "#KCMDDC51#-890"
	else:
		return None

def configExtract(rawData, key):			
	config = {"FWB": "", "GENCODE": "", "MUTEX": "", "NETDATA": "", "OFFLINEK": "", "SID": "", "FTPUPLOADK": "", "FTPHOST": "", "FTPUSER": "", "FTPPASS": "", "FTPPORT": "", "FTPSIZE": "", "FTPROOT": "", "PWD": ""}

	pe = pefile.PE(data=rawData)
	rt_string_idx = [
	entry.id for entry in 
	pe.DIRECTORY_ENTRY_RESOURCE.entries].index(pefile.RESOURCE_TYPE['RT_RCDATA'])
	rt_string_directory = pe.DIRECTORY_ENTRY_RESOURCE.entries[rt_string_idx]
	for entry in rt_string_directory.directory.entries:
		if str(entry.name) == "DCDATA":
			
			data_rva = entry.directory.entries[0].data.struct.OffsetToData
			size = entry.directory.entries[0].data.struct.Size
			data = pe.get_memory_mapped_image()[data_rva:data_rva+size]
			config = v51_data(data, key)

		elif str(entry.name) in config.keys():

			data_rva = entry.directory.entries[0].data.struct.OffsetToData
			size = entry.directory.entries[0].data.struct.Size
			data = pe.get_memory_mapped_image()[data_rva:data_rva+size]
			dec = rc4crypt(unhexlify(data), key)
			config[str(entry.name)] = filter(lambda x: x in string.printable, dec)
			config["Version"] = key[:-4]
	return config


def configClean(config):
	try:
		newConf = {}
		newConf["FireWallBypass"] = config["FWB"]
		newConf["FTPHost"] = config["FTPHOST"]
		newConf["FTPPassword"] = config["FTPPASS"]
		newConf["FTPPort"] = config["FTPPORT"]
		newConf["FTPRoot"] = config["FTPROOT"]
		newConf["FTPSize"] = config["FTPSIZE"]
		newConf["FTPKeyLogs"] = config["FTPUPLOADK"]
		newConf["FTPUserName"] = config["FTPUSER"]
		newConf["Gencode"] = config["GENCODE"]
		newConf["Mutex"] = config["MUTEX"]
		newConf["Domains"] = config["NETDATA"]
		newConf["OfflineKeylogger"] = config["OFFLINEK"]
		newConf["Password"] = config["PWD"]
		newConf["CampaignID"] = config["SID"]
		newConf["Version"] = config["Version"]
		return newConf
	except:
		return config
	
def run(data):
	versionKey = versionCheck(data)
	if versionKey != None:
		config = configExtract(data, versionKey)
		print config
		config = configClean(config)

		return config
	else:
		return None

if __name__ == "__main__":
	parser = OptionParser(usage='usage: %prog inFile outConfig\n' + __description__, version='%prog ' + __version__)
	(options, args) = parser.parse_args()
	if len(args) > 0:
		pass
	else:
		parser.print_help()
		sys.exit()
	try:
		print "[+] Reading file"
		fileData = open(args[0], 'rb').read()
	except:
		print "[+] Couldn't Open File {0}".format(args[0])
	print "[+] Searching for Config"
	config = run(fileData)
	if config == None:
		print "[+] Config not found"
		sys.exit()
	if len(args) == 2:
		print "[+] Writing Config to file {0}".format(args[1])
		with open(args[1], 'a') as outFile:
			for key, value in sorted(config.iteritems()):
				outFile.write("Key: {0}\t Value: {1}\n".format(key,value))
		
	else:
		print "[+] Printing Config to screen"
		for key, value in sorted(config.iteritems()):
			print "   [-] Key: {0}\t Value: {1}".format(key,value)
		print "[+] End of Config"

########NEW FILE########
__FILENAME__ = darkddoser
# Author: Jason Jones
########################################################################
# Copyright 2014
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
########################################################################

import argparse
import os
import string
import pefile

def decrypt_str(encrypted_str,key_str):
    d = 0
    decrypted = ''
    for e in encrypted_str:
        for c in key_str:
            d = (ord(c)+d) ^ 9
        decrypted += chr(((d>>3) ^ ord(e)) % 256)
    return decrypted

def load_rsrc(pe):
    strs = {}
    rcd = pefile.RESOURCE_TYPE['RT_RCDATA']
    for entry in pe.DIRECTORY_ENTRY_RESOURCE.entries:
        if entry.id == rcd:
            for e in entry.directory.entries:
                data_rva = e.directory.entries[0].data.struct.OffsetToData
                size = e.directory.entries[0].data.struct.Size
                data = pe.get_memory_mapped_image()[data_rva:data_rva+size]
                strs[str(e.name)] = data                
            break
    return strs

def extract(filename,rsrc_name,key):
    decrypted = []
    try:
        pe = pefile.PE(filename)
        rsrc = load_rsrc(pe)
        if rsrc.get(rsrc_name,''):
            crypted_config = rsrc[rsrc_name]
            if crypted_config.find('[{#}]') != -1:
                for crypt_str in crypted_config.split('[{#}]'):
                    crypt_str = ''.join([chr(ord(c)^0xbc) for c in crypt_str])
                    decrypted.append(decrypt_str(crypt_str,key))
    except Exception, e:
        print '[+] %s: %s' % (Exception, e)
    if decrypted:
        try:
            int(decrypted[1]) # easiest way to test success, port = int
            print '[+] Filename: %s' % filename
            print '[+] CnC: %s:%s' % (decrypted[0],decrypted[1])
            print '[+] Server: %s' % decrypted[2]
            print '[+] Version: %s' % decrypted[8]
            print '[+] Mutex: %s' % decrypted[4]
            print '[+] Install: %s' % decrypted[7]
            print '[+] Service Name: %s' % decrypted[6]
            print
        except:
            print '[+] Filename: %s' % filename
            print '[+] Did not successfully decrypt config'
    else:
        print '[+] Could not locate encrypted config'

def main():
    parser = argparse.ArgumentParser(description='Extract configuration data from DarkDDoser')
    parser.add_argument('filenames',nargs='+',help='Executables to extract configuration from')
    parser.add_argument('--resource',default='BUBZ',help='Custom resource string name where encrypted config is kept')
    parser.add_argument('--key',default='darkddoser',help='Custom encryption key for encrypted config')
    args = parser.parse_args()

    if args.filenames:
        for filename in args.filenames:
            extract(filename,args.resource,args.key)
    else:
        print args.usage()

if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = DarkRAT
#!/usr/bin/env python
'''
DarkRAT Config Decoder
'''

__description__ = 'DarkRAT Config Extractor'
__author__ = 'Kevin Breen http://techanarchy.net http://malwareconfig.com'
__version__ = '0.1'
__date__ = '2014/04/10'

#Standard Imports Go Here
import os
import sys
import string
from optparse import OptionParser

#Non Standard Imports


# Main Decode Function Goes Here
'''
data is a read of the file
Must return a python dict of values
'''

def run(data):
	Config = {}
	rawConfig = data.split("@1906dark1996coder@")
	if len(rawConfig) > 3:
		Config["Domain"] = rawConfig[1][7:-1]#
		Config["AutoRun"] = rawConfig[2]#
		Config["USB Spread"] = rawConfig[3]#
		Config["Hide Form"] = rawConfig[4]#
		Config["Msg Box Title"] = rawConfig[6]#
		Config["Msg Box Text"] = rawConfig[7]#
		Config["Timer Interval"] = rawConfig[8]#
		if rawConfig[5] == 4:
			Config["Msg Box Type"] = "Information"
		elif rawConfig[5] == 2:
			Config["Msg Box Type"] = "Question"
		elif rawConfig[5] == 3:
			Config["Msg Box Type"] = "Exclamation"
		elif rawConfig[5] == 1:
			Config["Msg Box Type"] = "Critical"
		else:
			Config["Msg Box Type"] = "None"
		return Config
		
#Helper Functions Go Here



#Recursive Function Goes Here

def runRecursive(folder, output):
	counter1 = 0
	counter2 = 0
	print "[+] Writing Configs to File {0}".format(output)
	with open(output, 'a+') as out:
		#This line will need changing per Decoder
		out.write("Filename,Domain, AutoRun, USB Spread, Hide Form, MsgBox Title, MsgBox Text, Timer Interval, Msg Box Type\n")	
		for server in os.listdir(folder):
			fileData = open(os.path.join(folder,server), 'rb').read()
			configOut = run(fileData)
			if configOut != None:
				#This line will need changing per Decoder
				out.write('{0},{1},{2},{3},{4},{5},{6},{7},{8}\n'.format(server, configOut["Domain"],configOut["AutoRun"],configOut["USB Spread"],configOut["Hide Form"],configOut["Msg Box Title"],configOut["Msg Box Text"],configOut["Timer Interval"],configOut["Msg Box Type"]))
				counter1 += 1
			counter2 += 1
	print "[+] Decoded {0} out of {1} Files".format(counter1, counter2)
	return "Complete"

# Main

if __name__ == "__main__":
	parser = OptionParser(usage='usage: %prog inFile outConfig\n' + __description__, version='%prog ' + __version__)
	parser.add_option("-r", "--recursive", action='store_true', default=False, help="Recursive Mode")
	(options, args) = parser.parse_args()
	# If we dont have args quit with help page
	if len(args) > 0:
		pass
	else:
		parser.print_help()
		sys.exit()
	# if we want a recursive extract run this function
	if options.recursive == True:
		if len(args) == 2:
			runRecursive(args[0], args[1])
			sys.exit()
		else:
			print "[+] You need to specify Both Dir to read AND Output File"
			parser.print_help()
			sys.exit()
	
	# If not recurisve try to open file
	try:
		print "[+] Reading file"
		fileData = open(args[0], 'rb').read()
	except:
		print "[+] Couldn't Open File {0}".format(args[0])
	#Run the config extraction
	print "[+] Searching for Config"
	config = run(fileData)
	#If we have a config figure out where to dump it out.
	if config == None:
		print "[+] Config not found"
		sys.exit()
	#if you gave me two args im going to assume the 2nd arg is where you want to save the file
	if len(args) == 2:
		print "[+] Writing Config to file {0}".format(args[1])
		with open(args[1], 'a') as outFile:
			for key, value in sorted(config.iteritems()):
				clean_value = filter(lambda x: x in string.printable, value)
				outFile.write("Key: {0}\t Value: {1}\n".format(key,clean_value))
	# if no seconds arg then assume you want it printing to screen
	else:
		print "[+] Printing Config to screen"
		for key, value in sorted(config.iteritems()):
			clean_value = filter(lambda x: x in string.printable, value)
			print "   [-] Key: {0}\t Value: {1}".format(key,clean_value)
		print "[+] End of Config"

########NEW FILE########
__FILENAME__ = Greame
#!/usr/bin/env python
'''
Greame Rat Config Decoder
'''


__description__ = 'Greame Rat Config Extractor'
__author__ = 'Kevin Breen http://techanarchy.net http://malwareconfig.com'
__version__ = '0.1'
__date__ = '2014/04/10'

#Standard Imports Go Here
import os
import sys
import string
from optparse import OptionParser

#Non Standard Imports
try:
	import pefile
except ImportError:
	print "[+] Couldn't Import pefile. Try 'sudo pip install pefile'"


# Main Decode Function Goes Here
'''
data is a read of the file
Must return a python dict of values
'''

def run(data):
	finalConfig = {}
	config = configExtract(data)
	if config != None and len(config) > 20:
		domains = ""
		ports = ""
		#Config sections 0 - 19 contain a list of Domains and Ports
		for x in range(0,19):
			if len(config[x]) > 1:
				domains += xorDecode(config[x]).split(':')[0]
				domains += "|"
				ports += xorDecode(config[x]).split(':')[1]
				ports += "|"
			
		finalConfig["Domain"] = domains
		finalConfig["Port"] = ports
		finalConfig["ServerID"] = xorDecode(config[20])
		finalConfig["Password"] = xorDecode(config[21])
		finalConfig["Install Flag"] = xorDecode(config[22])
		finalConfig["Install Directory"] = xorDecode(config[25])
		finalConfig["Install File Name"] = xorDecode(config[26])
		finalConfig["Active X Startup"] = xorDecode(config[27])
		finalConfig["REG Key HKLM"] = xorDecode(config[28])
		finalConfig["REG Key HKCU"] = xorDecode(config[29])
		finalConfig["Enable Message Box"] = xorDecode(config[30])
		finalConfig["Message Box Icon"] = xorDecode(config[31])
		finalConfig["Message Box Button"] = xorDecode(config[32])
		finalConfig["Install Message Title"] = xorDecode(config[33])
		finalConfig["Install Message Box"] = xorDecode(config[34]).replace('\r\n', ' ')
		finalConfig["Activate Keylogger"] = xorDecode(config[35])
		finalConfig["Keylogger Backspace = Delete"] = xorDecode(config[36])
		finalConfig["Keylogger Enable FTP"] = xorDecode(config[37])
		finalConfig["FTP Address"] = xorDecode(config[38])
		finalConfig["FTP Directory"] = xorDecode(config[39])
		finalConfig["FTP UserName"] = xorDecode(config[41])
		finalConfig["FTP Password"] = xorDecode(config[42])
		finalConfig["FTP Port"] = xorDecode(config[43])
		finalConfig["FTP Interval"] = xorDecode(config[44])
		finalConfig["Persistance"] = xorDecode(config[59])
		finalConfig["Hide File"] = xorDecode(config[60])
		finalConfig["Change Creation Date"] = xorDecode(config[61])
		finalConfig["Mutex"] = xorDecode(config[62])		
		finalConfig["Melt File"] = xorDecode(config[63])		
		finalConfig["Startup Policies"] = xorDecode(config[69])
		finalConfig["USB Spread"] = xorDecode(config[70])
		finalConfig["P2P Spread"] = xorDecode(config[71])
		finalConfig["Google Chrome Passwords"] = xorDecode(config[73])		
		if xorDecode(config[57]) == 0:
			finalConfig["Process Injection"] = "Disabled"
		elif xorDecode(config[57]) == 1:
			finalConfig["Process Injection"] = "Default Browser"
		elif xorDecode(config[57]) == 2:
			finalConfig["Process Injection"] = xorDecode(config[58])
		else: finalConfig["Process Injection"] = "None"
	else:
		return None
	print xorDecode(config[33]).encode('hex')
	return finalConfig
	
		
#Helper Functions Go Here
def configExtract(rawData):
	try:
		pe = pefile.PE(data=rawData)
		try:
		  rt_string_idx = [
		  entry.id for entry in 
		  pe.DIRECTORY_ENTRY_RESOURCE.entries].index(pefile.RESOURCE_TYPE['RT_RCDATA'])
		except ValueError, e:
			sys.exit()
		except AttributeError, e:
			sys.exit()
		rt_string_directory = pe.DIRECTORY_ENTRY_RESOURCE.entries[rt_string_idx]
		for entry in rt_string_directory.directory.entries:
			if str(entry.name) == "GREAME":
				data_rva = entry.directory.entries[0].data.struct.OffsetToData
				size = entry.directory.entries[0].data.struct.Size
				data = pe.get_memory_mapped_image()[data_rva:data_rva+size]
				config = data.split('####@####')
				return config
	except:
		return None

def xorDecode(data):
	key = 0xBC
	encoded = bytearray(data)
	for i in range(len(encoded)):
		encoded[i] ^= key
	return filter(lambda x: x in string.printable, str(encoded))


#Recursive Function Goes Here

def runRecursive(folder, output):
	counter1 = 0
	counter2 = 0
	print "[+] Writing Configs to File {0}".format(output)
	with open(output, 'a+') as out:
		#This line will need changing per Decoder
		out.write("Filename,Domains, Ports, Campaign ID, Password, Install Flag, Install Dir, Install File Name, ActiveX Key, HKLM Key, HKCU Key, Enable MessageBox, Message Box Icon, Mesage Box Button, Message Title, Message Box Text, Enable Keylogger, KeyLogger Backspace, Keylogger FTP, FTP Address, FTP UserName, FTP Password, FTP Port, FTP Interval, Persistnace, Hide File, Change Creation Date, Mutex, Melt File, Startup Polocies, USB Spread, P2P Spread, Google Chrome Passwords, Process Injection\n")	
		for server in os.listdir(folder):
			fileData = open(os.path.join(folder,server), 'rb').read()
			finalConfig = run(fileData)
			if finalConfig != None:
				#This line will need changing per Decoder
				out.write('{0},{1},{2},{3},{4},{5},{6},{7},{8},{9},{10},{11},{12},{13},{14},{15},{16},{17},{18},{19},{20},{21},{22},{23},{24},{25},{26},{27},{28},{29},{30},{31},{32},{33},{34}\n'.format(server, finalConfig["Domain"],finalConfig["Port"],finalConfig["ServerID"],finalConfig["Password"],finalConfig["Install Flag"],finalConfig["Install Directory"],finalConfig["Install File Name"],finalConfig["Active X Startup"],finalConfig["REG Key HKLM"],finalConfig["REG Key HKCU"],finalConfig["Enable Message Box"],finalConfig["Message Box Icon"],finalConfig["Message Box Button"],finalConfig["Install Message Title"],finalConfig["Install Message Box"],finalConfig["Activate Keylogger"],finalConfig["Keylogger Backspace = Delete"],finalConfig["Keylogger Enable FTP"],finalConfig["FTP Address"],finalConfig["FTP Directory"],finalConfig["FTP UserName"],finalConfig["FTP Password"],finalConfig["FTP Port"],finalConfig["FTP Interval"],finalConfig["Persistance"],finalConfig["Hide File"],finalConfig["Change Creation Date"],finalConfig["Mutex"],finalConfig["Melt File"],finalConfig["Startup Policies"],finalConfig["USB Spread"],finalConfig["P2P Spread"],finalConfig["Google Chrome Passwords"],finalConfig["Process Injection"]))
				counter1 += 1
			counter2 += 1
	print "[+] Decoded {0} out of {1} Files".format(counter1, counter2)
	return "Complete"

# Main

if __name__ == "__main__":
	parser = OptionParser(usage='usage: %prog inFile outConfig\n' + __description__, version='%prog ' + __version__)
	parser.add_option("-r", "--recursive", action='store_true', default=False, help="Recursive Mode")
	(options, args) = parser.parse_args()
	# If we dont have args quit with help page
	if len(args) > 0:
		pass
	else:
		parser.print_help()
		sys.exit()
	# if we want a recursive extract run this function
	if options.recursive == True:
		if len(args) == 2:
			runRecursive(args[0], args[1])
			sys.exit()
		else:
			print "[+] You need to specify Both Dir to read AND Output File"
			parser.print_help()
			sys.exit()
	
	# If not recurisve try to open file
	try:
		print "[+] Reading file"
		fileData = open(args[0], 'rb').read()
	except:
		print "[+] Couldn't Open File {0}".format(args[0])
	#Run the config extraction
	print "[+] Searching for Config"
	config = run(fileData)
	#If we have a config figure out where to dump it out.
	if config == None:
		print "[+] Config not found"
		sys.exit()
	#if you gave me two args im going to assume the 2nd arg is where you want to save the file
	if len(args) == 2:
		print "[+] Writing Config to file {0}".format(args[1])
		with open(args[1], 'a') as outFile:
			for key, value in sorted(config.iteritems()):
				clean_value = filter(lambda x: x in string.printable, value)
				outFile.write("Key: {0}\t Value: {1}\n".format(key,clean_value))
	# if no seconds arg then assume you want it printing to screen
	else:
		print "[+] Printing Config to screen"
		for key, value in sorted(config.iteritems()):
			clean_value = filter(lambda x: x in string.printable, value)
			print "   [-] Key: {0}\t Value: {1}".format(key,clean_value)
		print "[+] End of Config"

########NEW FILE########
__FILENAME__ = jRat
#!/usr/bin/env python
'''
jRat Config Parser

'''
__description__ = 'jRat Config Parser'
__author__ = 'Kevin Breen'
__version__ = '0.1'
__date__ = '2013/08/05'

import sys
import base64
import string
from zipfile import ZipFile
from optparse import OptionParser
try:
	from Crypto.Cipher import AES
	from Crypto.Cipher import DES3
except ImportError:
	print "Cannot import PyCrypto, Is it installed?"


def main():
	parser = OptionParser(usage='usage: %prog [options] InFile SavePath\n' + __description__, version='%prog ' + __version__)
	parser.add_option("-v", "--verbose", action='store_true', default=False, help="Verbose Output")
	(options, args) = parser.parse_args()
	if len(args) != 2:
		parser.print_help()
		sys.exit()

	archive = args[0]
	outfile = args[1]
	dropper = None
	conf = None
	with ZipFile(archive, 'r') as zip:
		for name in zip.namelist(): # get all the file names
			if name == "key.dat": # this file contains the encrytpion key
				enckey = zip.read(name)
			if name == "enc.dat": # if this file exists, jrat has an installer / dropper				
				dropper = zip.read(name)
			if name == "config.dat": # this is the encrypted config file
				conf = zip.read(name)
		if dropper != None: # we need to process the dropper first
			print "Dropper Detected"
			ExtractDrop(enckey, dropper, outfile)
		elif conf != None: # if theres not dropper just decrpyt the config file
			if len(enckey) == 16: # version > 3.2.3 use AES
				cleandrop = DecryptAES(enckey, conf)
				WriteReport(enckey, outfile, cleandrop)
			elif len(enckey) == 24: # versions <= 3.2.3 use DES
				cleandrop = DecryptDES(enckey, conf)
				WriteReport(enckey, outfile, cleandrop)

def ExtractDrop(enckey, data, outfile):
	split = enckey.split('\x2c')
	key = split[0][:16]
	with open(outfile, 'a') as new:
		print "### Dropper Information ###"
		new.write("### Dropper Information ###\n")
		for x in split: # grab each line of the config and decode it.		
			try:
				drop = base64.b64decode(x).decode('hex')
				print drop
				new.write(drop+'\n')
			except:
				drop = base64.b64decode(x[16:]).decode('hex')
				print drop
				new.write(drop+'\n')
	newzipdata = DecryptAES(key, data)
	from cStringIO import StringIO
	newZip = StringIO(newzipdata) # Write new zip file to memory instead of to disk
	with ZipFile(newZip) as zip:
		for name in zip.namelist():
			if name == "key.dat": # contains the encryption key
				enckey = zip.read(name)
			if name == "config.dat":
				conf = zip.read(name) # the encrypted config file
			if len(enckey) == 16: # version > 3.2.3 use AES
				printkey = enckey.encode('hex')
				print "AES Key Found: ", printkey
				cleandrop = DecryptAES(enckey, conf) # pass to the decrpyt function
				print "### Configuration File ###"
				WriteReport(printkey, outfile, cleandrop)
			elif len(enckey) == 24: # versions <= 3.2.3 use DES
				printkey = enckey
				print "DES Key Found: ", enckey
				cleandrop = DecryptDES(enckey, conf) # pass to the decrpyt function
				print "### Configuration File ###"
				WriteReport(enckey, outfile, cleandrop)
				
def DecryptAES(enckey, data):					
		cipher = AES.new(enckey) # set the cipher
		return cipher.decrypt(data) # decrpyt the data
		
def DecryptDES(enckey, data):

		cipher = DES3.new(enckey) # set the ciper
		return cipher.decrypt(data) # decrpyt the data

def WriteReport(key, outfile, data): # this should be self expanatory		
	split = data.split("SPLIT")
	with open(outfile, 'a') as new:
		new.write(key)
		new.write('\n')
		for s in split:
			stripped = (char for char in s if 32 < ord(char) < 127) # im only interested in ASCII Characters
			line = ''.join(stripped)
			#if options.verbose == True:
			print line
			new.write(line)
			new.write('\n')
	print "Config Written To: ", outfile


if __name__ == "__main__":
	main()

########NEW FILE########
__FILENAME__ = njRat
#!/usr/bin/env python
'''
njRat Config Decoder
'''


__description__ = 'njRat Config Extractor'
__author__ = 'Kevin Breen http://techanarchy.net http://malwareconfig.com'
__version__ = '0.1'
__date__ = '2014/04/10'

#Standard Imports Go Here
import os
import sys
import base64
import string
from optparse import OptionParser

#Non Standard Imports
try:
	import pype32
except ImportError:
	print "[+] Couldn't Import pype32 'https://github.com/crackinglandia/pype32'"


# Main Decode Function Goes Here
'''
data is a read of the file
Must return a python dict of values
'''

def run(data):
	try:
		pe = pype32.PE(data=data) 
		rawConfig = getStream(pe)
		rawConfig = pypefix(rawConfig)
		# Get a list of strings
		stringList = parseStrings(rawConfig)
		#parse the string list
		dict = parseConfig(stringList)
		return dict
	except:
		return None
	
		
#Helper Functions Go Here

# Confirm if there is Net MetaData in the File 
def getStream(pe):
	counter = 0   
	for dir in pe.ntHeaders.optionalHeader.dataDirectory:
		if dir.name.value == "NET_METADATA_DIRECTORY":
			rawConfig = findUSStream(pe, counter)
		else:
			counter += 1
	return rawConfig

# I only want to extract the User Strings Section
def findUSStream(pe, dir):
	for i in range(0,4):
		name = pe.ntHeaders.optionalHeader.dataDirectory[dir].info.netMetaDataStreams[i].name.value
		if name.startswith("#US"):
			return pe.ntHeaders.optionalHeader.dataDirectory[dir].info.netMetaDataStreams[i].info
	return None

#Walk the User Strings and create a list of individual strings
def parseStrings(rawConfig):
	stringList = []
	offset = 1
	config = bytearray(rawConfig)
	while offset < len(config):
		length = int(config[offset])
		that = config[offset+1:offset+int(length)]
		stringList.append(str(that.replace("\x00", "")))
		offset += int(length+1)
	return stringList
			
#Turn the strings in to a python Dict
def parseConfig(stringList):
	dict = {}
	if '0.3.5' in stringList:
		dict["Campaign ID"] = base64.b64decode(stringList[3])
		dict["version"] = stringList[4]
		dict["Install Name"] = stringList[0]
		dict["Install Dir"] = stringList[1]
		dict["Registry Value"] = stringList[2]
		dict["Domain"] = stringList[6]
		dict["Port"] = stringList[7]
		dict["Network Separator"] = stringList[8]
		dict["Install Flag"] = stringList[5]
		
	elif '0.3.6' in stringList:
		index = stringList.index('[endof]')
		dict["Campaign ID"] = base64.b64decode(stringList[index+4])
		dict["version"] = stringList[index+5]
		dict["Install Name"] = stringList[index+1]
		dict["Install Dir"] = stringList[index+2]
		dict["Registry Value"] = stringList[index+3]
		dict["Domain"] = stringList[index+7]
		dict["Port"] = stringList[index+8]
		dict["Network Separator"] = stringList[index+9]
		dict["Install Flag"] = stringList[index+10]
		
	elif '0.4.1a' in stringList:
		index = stringList.index('[endof]')
		dict["Campaign ID"] = base64.b64decode(stringList[index+1])
		dict["version"] = stringList[index+2]
		dict["Install Name"] = stringList[index+4]
		dict["Install Dir"] = stringList[index+5]
		dict["Registry Value"] = stringList[index+6]
		dict["Domain"] = stringList[index+7]
		dict["Port"] = stringList[index+8]
		dict["Network Separator"] = stringList[index+10]
		dict["Install Flag"] = stringList[index+3]

		
	elif '0.5.0E' in stringList:
		index = stringList.index('[endof]')
		dict["Campaign ID"] = base64.b64decode(stringList[index-8])
		dict["version"] = stringList[index-7]
		dict["Install Name"] = stringList[index-6]
		dict["Install Dir"] = stringList[index-5]
		dict["Registry Value"] = stringList[index-4]
		dict["Domain"] = stringList[index-3]
		dict["Port"] = stringList[index-2]
		dict["Network Separator"] = stringList[index-1]
		dict["Install Flag"] = stringList[index+3]

		
	elif '0.6.4' in stringList:
		dict["Campaign ID"] = base64.b64decode(stringList[0])
		dict["version"] = stringList[1]
		dict["Install Name"] = stringList[2]
		dict["Install Dir"] = stringList[3]
		dict["Registry Value"] = stringList[4]
		dict["Domain"] = stringList[5]
		dict["Port"] = stringList[6]
		dict["Network Separator"] = stringList[7]
		dict["Install Flag"] = stringList[8]
		
	elif '0.7d' in stringList:
		dict["Campaign ID"] = base64.b64decode(stringList[0])
		dict["version"] = stringList[1]
		dict["Install Name"] = stringList[2]
		dict["Install Dir"] = stringList[3]
		dict["Registry Value"] = stringList[4]
		dict["Domain"] = stringList[5]
		dict["Port"] = stringList[6]
		dict["Network Separator"] = stringList[7]
		dict["Install Flag"] = stringList[8]
		
	else:
		return None
		
	# Really hacky test to check for a valid config.	
	if dict["Install Flag"] == "True" or dict["Install Flag"] == "False" or dict["Install Flag"] == "":
		return dict
	else:
		return None

# theres an error when you try to get the strings section, this trys to fix that.
def pypefix(rawConfig):
	counter = 0
	while counter < 10:
		x = rawConfig[counter]
		if x == '\x00':
			return rawConfig[counter:]
			
		else:
			counter += 1


#Recursive Function Goes Here

def runRecursive(folder, output):
	counter1 = 0
	counter2 = 0
	print "[+] Writing Configs to File {0}".format(output)
	with open(output, 'a+') as out:
		#This line will need changing per Decoder
		out.write("Filename,Campaign ID, Version, Install Name, Install Dir, Registry Value, Domain, Network Seperator, Install Flag\n")	
		for server in os.listdir(folder):
			fileData = open(os.path.join(folder,server), 'rb').read()
			dict = run(fileData)
			if dict != None:
				#This line will need changing per Decoder
				out.write('{0},{1},{2},{3},{4},{5},{6},{7},{8},{9},\n'.format(server, dict["Campaign ID"],dict["version"],dict["Install Name"],dict["Install Dir"],dict["Registry Value"],dict["Domain"],dict["Port"],dict["Network Separator"],dict["Install Flag"]))
				counter1 += 1
			counter2 += 1
	print "[+] Decoded {0} out of {1} Files".format(counter1, counter2)
	return "Complete"

# Main

if __name__ == "__main__":
	parser = OptionParser(usage='usage: %prog inFile outConfig\n' + __description__, version='%prog ' + __version__)
	parser.add_option("-r", "--recursive", action='store_true', default=False, help="Recursive Mode")
	(options, args) = parser.parse_args()
	# If we dont have args quit with help page
	if len(args) > 0:
		pass
	else:
		parser.print_help()
		sys.exit()
	# if we want a recursive extract run this function
	if options.recursive == True:
		if len(args) == 2:
			runRecursive(args[0], args[1])
			sys.exit()
		else:
			print "[+] You need to specify Both Dir to read AND Output File"
			parser.print_help()
			sys.exit()
	
	# If not recurisve try to open file
	try:
		print "[+] Reading file"
		fileData = open(args[0], 'rb').read()
	except:
		print "[+] Couldn't Open File {0}".format(args[0])
	#Run the config extraction
	print "[+] Searching for Config"
	config = run(fileData)
	#If we have a config figure out where to dump it out.
	if config == None:
		print "[+] Config not found"
		sys.exit()
	#if you gave me two args im going to assume the 2nd arg is where you want to save the file
	if len(args) == 2:
		print "[+] Writing Config to file {0}".format(args[1])
		with open(args[1], 'a') as outFile:
			for key, value in sorted(config.iteritems()):
				clean_value = filter(lambda x: x in string.printable, value)
				outFile.write("Key: {0}\t Value: {1}\n".format(key,clean_value))
	# if no seconds arg then assume you want it printing to screen
	else:
		print "[+] Printing Config to screen"
		for key, value in sorted(config.iteritems()):
			clean_value = filter(lambda x: x in string.printable, value)
			print "   [-] Key: {0}\t Value: {1}".format(key,clean_value)
		print "[+] End of Config"

########NEW FILE########
__FILENAME__ = Pandora
#!/usr/bin/env python
'''
Pandora Rat Config Decoder
'''


__description__ = 'Pandora Rat Config Extractor'
__author__ = 'Kevin Breen http://techanarchy.net http://malwareconfig.com'
__version__ = '0.1'
__date__ = '2014/04/10'

#Standard Imports Go Here
import os
import sys
import base64
import string
from optparse import OptionParser

#Non Standard Imports
try:
	import pefile
except ImportError:
	print "[+] Couldn't Import pefile. Try 'sudo pip install pefile'"


# Main Decode Function Goes Here
'''
data is a read of the file
Must return a python dict of values
'''

def run(data):
	newConfig = {}
	config = configExtract(data)
	if config != None:
		newConfig["Domain"] = config[0]
		newConfig["Port"] = config[1]
		newConfig["Password"] = config[2]
		newConfig["Install Path"] = config[3]
		newConfig["Install Name"] = config[4]
		newConfig["HKCU Startup"] = config[5]
		newConfig["ActiveX Install"] = config[6]
		newConfig["Flag1"] = config[7]
		newConfig["Flag2"] = config[8]
		newConfig["Flag3"] = config[9]
		newConfig["Flag4"] = config[10]
		newConfig["Mutex"] = config[11]
		newConfig["Flag5"] = config[12]
		newConfig["Flag6"] = config[13]
		newConfig["Flag7"] = config[13]
		newConfig["ID"] = config[14]
		newConfig["Campaign ID"] = config[15]
		newConfig["Flag9"] = config[16]
		return newConfig
	else:
		return None
	
		
#Helper Functions Go Here
def configExtract(rawData):
	try:
		pe = pefile.PE(data=rawData)
		try:
		  rt_string_idx = [
		  entry.id for entry in 
		  pe.DIRECTORY_ENTRY_RESOURCE.entries].index(pefile.RESOURCE_TYPE['RT_RCDATA'])
		except ValueError, e:
			sys.exit()
		except AttributeError, e:
			sys.exit()
		rt_string_directory = pe.DIRECTORY_ENTRY_RESOURCE.entries[rt_string_idx]
		for entry in rt_string_directory.directory.entries:
			if str(entry.name) == "CFG":
				data_rva = entry.directory.entries[0].data.struct.OffsetToData
				size = entry.directory.entries[0].data.struct.Size
				data = pe.get_memory_mapped_image()[data_rva:data_rva+size]
				cleaned = data.replace('\x00', '')
				config = cleaned.split('##')
				return config
	except:
		print "Couldn't Locate the Config, Is it Packed?"
		return None	


#Recursive Function Goes Here

def runRecursive(folder, output):
	counter1 = 0
	counter2 = 0
	print "[+] Writing Configs to File {0}".format(output)
	with open(output, 'a+') as out:
		#This line will need changing per Decoder
		out.write("Filename,Domain, Port, Password, Install Path, Install Name, HKCU Startup, ActiveX Startup, ID,Campaign ID\n")	
		for server in os.listdir(folder):
			fileData = open(os.path.join(folder,server), 'rb').read()
			configOut = run(fileData)
			if configOut != None:
				#This line will need changing per Decoder
				out.write('{0},{1},{2},{3},{4},{5},{6},{7},{8},{9},\n'.format(server, configOut["Domain"],configOut["Port"],configOut["Password"],configOut["Install Path"],configOut["Install Name"],configOut["HKCU Startup"],configOut["ActiveX Install"],configOut["ID"],configOut["Campaign ID"]))
				counter1 += 1
			counter2 += 1
	print "[+] Decoded {0} out of {1} Files".format(counter1, counter2)
	return "Complete"

# Main

if __name__ == "__main__":
	parser = OptionParser(usage='usage: %prog inFile outConfig\n' + __description__, version='%prog ' + __version__)
	parser.add_option("-r", "--recursive", action='store_true', default=False, help="Recursive Mode")
	(options, args) = parser.parse_args()
	# If we dont have args quit with help page
	if len(args) > 0:
		pass
	else:
		parser.print_help()
		sys.exit()
	# if we want a recursive extract run this function
	if options.recursive == True:
		if len(args) == 2:
			runRecursive(args[0], args[1])
			sys.exit()
		else:
			print "[+] You need to specify Both Dir to read AND Output File"
			parser.print_help()
			sys.exit()
	
	# If not recurisve try to open file
	try:
		print "[+] Reading file"
		fileData = open(args[0], 'rb').read()
	except:
		print "[+] Couldn't Open File {0}".format(args[0])
	#Run the config extraction
	print "[+] Searching for Config"
	config = run(fileData)
	#If we have a config figure out where to dump it out.
	if config == None:
		print "[+] Config not found"
		sys.exit()
	#if you gave me two args im going to assume the 2nd arg is where you want to save the file
	if len(args) == 2:
		print "[+] Writing Config to file {0}".format(args[1])
		with open(args[1], 'a') as outFile:
			for key, value in sorted(config.iteritems()):
				clean_value = filter(lambda x: x in string.printable, value)
				outFile.write("Key: {0}\t Value: {1}\n".format(key,clean_value))
	# if no seconds arg then assume you want it printing to screen
	else:
		print "[+] Printing Config to screen"
		for key, value in sorted(config.iteritems()):
			clean_value = filter(lambda x: x in string.printable, value)
			print "   [-] Key: {0}\t Value: {1}".format(key,clean_value)
		print "[+] End of Config"

########NEW FILE########
__FILENAME__ = PoisonIvy
#!/usr/bin/env python
'''
PoisonIvy Rat Config Decoder
'''


__description__ = 'PoisonIvy Rat Config Extractor'
__author__ = 'Kevin Breen http://techanarchy.net http://malwareconfig.com'
__version__ = '0.1'
__date__ = '2014/04/10'

#Standard Imports Go Here
import os
import sys
import string
from struct import unpack
from optparse import OptionParser

#Non Standard Imports


# Main Decode Function Goes Here
'''
data is a read of the file
Must return a python dict of values
'''

def run(data):
	# Split to get start of Config
	one = firstSplit(data)
	if one == None:
		return None
	# If the split works try to walk the strings
	two = dataWalk(one)
	# lets Process this and format the config
	three = configProcess(two)
	return three
	
		
#Helper Functions Go Here
def calcLength(byteStr):
	try:
		return unpack("<H", byteStr)[0]
	except:
		return None

def stringPrintable(line):
	return filter(lambda x: x in string.printable, line)

def firstSplit(data):
	splits = data.split('Software\\Microsoft\\Active Setup\\Installed Components\\')
	if len(splits) == 2:
		return splits[1]
	else:
		return None
		
def bytetohex(byteStr):
	return ''.join(["%02X" % ord(x) for x in byteStr]).strip()

	
def dataWalk(splitdata):
	# Byte array to make things easier
	stream = bytearray(splitdata)
	# End of file for our while loop
	EOF = len(stream)
	# offset to track position
	offset = 0
	this = []
	maxCount = 0
	while offset < EOF and maxCount < 22:
		try:
			length = calcLength(str(stream[offset+2:offset+4]))
			temp = []
			for i in range(offset+4, offset+4+length):
				temp.append(chr(stream[i]))
			dataType = bytetohex(splitdata[offset]+splitdata[offset+1])
			this.append((dataType,''.join(temp)))
			offset += length+4
			maxCount += 1
		except:
			return this
	return this

def domainWalk(rawStream):
	domains = ''
	offset = 0
	stream = bytearray(rawStream)
	while offset < len(stream):
		length = stream[offset]
		temp = []
		for i in range(offset+1, offset+1+length):
			temp.append(chr(stream[i]))
		domain = ''.join(temp)

		rawPort = rawStream[offset+length+2:offset+length+4]
		port = calcLength(rawPort)
		offset += length+4
		domains += "{0}:{1}|".format(domain, port)
	return domains	


def configProcess(rawConfig):
	configDict = {"Campaign ID" : "" , "Group ID" : "" , "Domains" : "" , "Password" : "" , "Enable HKLM" : "" , "HKLM Value" : "" , "Enable ActiveX" : "" , "ActiveX Key" : "" , "Flag 3" : "" , "Inject Exe" : "" , "Mutex" : "" , "Hijack Proxy" : "" , "Persistent Proxy" : "" , "Install Name" : "" , "Install Path" : "" , "Copy to ADS" : "" , "Melt" : "" , "Enable Thread Persistence" : "" , "Inject Default Browser" : "" , "Enable KeyLogger" : ""}
	for x in rawConfig:
		if x[0] == 'FA0A':
			configDict["Campaign ID"] = stringPrintable(x[1])
		if x[0] == 'F90B':
			configDict["Group ID"] = stringPrintable(x[1])
		if x[0] == '9001':
			configDict["Domains"] = domainWalk(x[1])
		if x[0] == '4501':
			configDict["Password"] = stringPrintable(x[1])
		if x[0] == '090D':
			configDict["Enable HKLM"] = bytetohex(x[1])
		if x[0] == '120E':
			configDict["HKLM Value"] = stringPrintable(x[1])
		if x[0] == 'F603':
			configDict["Enable ActiveX"] = bytetohex(x[1])
		if x[0] == '6501':
			configDict["ActiveX Key"] = stringPrintable(x[1])
		if x[0] == '4101':
			configDict["Flag 3"] = bytetohex(x[1])
		if x[0] == '4204':
			configDict["Inject Exe"] = stringPrintable(x[1])
		if x[0] == 'Fb03':
			configDict["Mutex"] = stringPrintable(x[1])
		if x[0] == 'F40A':
			configDict["Hijack Proxy"] = bytetohex(x[1])
		if x[0] == 'F50A':
			configDict["Persistent Proxy"] = bytetohex(x[1])
		if x[0] == '2D01':
			configDict["Install Name"] = stringPrintable(x[1])
		if x[0] == 'F703':
			configDict["Install Path"] = stringPrintable(x[1])
		if x[0] == '120D':
			configDict["Copy to ADS"] = bytetohex(x[1])
		if x[0] == 'F803':
			configDict["Melt"] = bytetohex(x[1])
		if x[0] == 'F903':
			configDict["Enable Thread Persistence"] = bytetohex(x[1])
		if x[0] == '080D':
			configDict["Inject Default Browser"] = bytetohex(x[1])
		if x[0] == 'FA03':
			configDict["Enable KeyLogger"] = bytetohex(x[1])
	return configDict
	
#Recursive Function Goes Here

def runRecursive(folder, output):
	counter1 = 0
	counter2 = 0
	print "[+] Writing Configs to File {0}".format(output)
	with open(output, 'a+') as out:
		#This line will need changing per Decoder
		out.write("Filename,Campaign ID, Group ID, Domains, Password, Enable HKLM, HKLM Value, Enable ActiveX, ActiveX Value, Flag 3, Inject Exe, Mutex, Hijack Proxy, Persistant Proxy, Install Name, Install Path, Copy To ADS, Mely, Enable Thread Persistance, Inject Default Browser, Enable Keylogger\n")	
		for server in os.listdir(folder):
			fileData = open(os.path.join(folder,server), 'rb').read()
			configOut = run(fileData)
			if configOut != None:
				#This line will need changing per Decoder
				out.write('{0},{1},{2},{3},{4},{5},{6},{7},{8},{9},{10},{11},{12},{13},{14},{15},{16},{17},{18},{19},{20}\n'.format(server, configOut["Campaign ID"],configOut["Group ID"],configOut["Domains"],configOut["Password"],configOut["Enable HKLM"],configOut["HKLM Value"],configOut["Enable ActiveX"],configOut["ActiveX Key"],configOut["Flag 3"],configOut["Inject Exe"],configOut["Mutex"],configOut["Hijack Proxy"],configOut["Persistent Proxy"],configOut["Install Name"],configOut["Install Path"],configOut["Copy to ADS"],configOut["Melt"],configOut["Enable Thread Persistence"],configOut["Inject Default Browser"],configOut["Enable KeyLogger"]))
				counter1 += 1
			counter2 += 1
	print "[+] Decoded {0} out of {1} Files".format(counter1, counter2)
	return "Complete"

# Main

if __name__ == "__main__":
	parser = OptionParser(usage='usage: %prog inFile outConfig\n' + __description__, version='%prog ' + __version__)
	parser.add_option("-r", "--recursive", action='store_true', default=False, help="Recursive Mode")
	(options, args) = parser.parse_args()
	# If we dont have args quit with help page
	if len(args) > 0:
		pass
	else:
		parser.print_help()
		sys.exit()
	# if we want a recursive extract run this function
	if options.recursive == True:
		if len(args) == 2:
			runRecursive(args[0], args[1])
			sys.exit()
		else:
			print "[+] You need to specify Both Dir to read AND Output File"
			parser.print_help()
			sys.exit()
	
	# If not recurisve try to open file
	try:
		print "[+] Reading file"
		fileData = open(args[0], 'rb').read()
	except:
		print "[+] Couldn't Open File {0}".format(args[0])
	#Run the config extraction
	print "[+] Searching for Config"
	config = run(fileData)
	#If we have a config figure out where to dump it out.
	if config == None:
		print "[+] Config not found"
		sys.exit()
	#if you gave me two args im going to assume the 2nd arg is where you want to save the file
	if len(args) == 2:
		print "[+] Writing Config to file {0}".format(args[1])
		with open(args[1], 'a') as outFile:
			for key, value in sorted(config.iteritems()):
				clean_value = filter(lambda x: x in string.printable, value)
				outFile.write("Key: {0}\t Value: {1}\n".format(key,clean_value))
	# if no seconds arg then assume you want it printing to screen
	else:
		print "[+] Printing Config to screen"
		for key, value in sorted(config.iteritems()):
			clean_value = filter(lambda x: x in string.printable, value)
			print "   [-] Key: {0}\t Value: {1}".format(key,clean_value)
		print "[+] End of Config"

########NEW FILE########
__FILENAME__ = Punisher
#!/usr/bin/env python
'''
Pandora Config Decoder
'''

__description__ = 'Pandora Config Extractor'
__author__ = 'Kevin Breen http://techanarchy.net'
__version__ = '0.1'
__date__ = '2014/03/15'

import sys
import string
from optparse import OptionParser
try:
	import pefile
except ImportError:
	print "[+] Couldnt Import pefile. Try 'sudo pip install pefile'"
	

def configExtract(rawData):
	try:
		pe = pefile.PE(data=rawData)

		try:
		  rt_string_idx = [
		  entry.id for entry in 
		  pe.DIRECTORY_ENTRY_RESOURCE.entries].index(pefile.RESOURCE_TYPE['RT_RCDATA'])
		except ValueError, e:
			sys.exit()
		except AttributeError, e:
			sys.exit()

		rt_string_directory = pe.DIRECTORY_ENTRY_RESOURCE.entries[rt_string_idx]

		for entry in rt_string_directory.directory.entries:
			if str(entry.name) == "CFG":
				data_rva = entry.directory.entries[0].data.struct.OffsetToData
				size = entry.directory.entries[0].data.struct.Size
				data = pe.get_memory_mapped_image()[data_rva:data_rva+size]
				cleaned = data.replace('\x00', '')
				config = cleaned.split('##')
				return config
	except:
		print "Couldn't Locate the Config, Is it Packed?"
		return None			

def run(data):
	dict = {}
	config = data.split("abccba")
	if len(config) > 5:
		dict["Domain"] = config[1]#
		dict["Port"] = config[2]#
		dict["Campaign Name"] = config[3]#
		dict["Copy StartUp"] = config[4]#
		dict["Unknown"] = config[5]#
		dict["Add To Registry"] = config[6]#
		dict["Registry Key"] = config[7]#
		dict["Password"] = config[8]#
		dict["Anti Kill Process"] = config[9]#
		dict["USB Spread"] = config[10]#
		dict["Anti VMWare VirtualBox"] = config[11]
		dict["Kill Sandboxie"] = config[12]#
		dict["Kill WireShark / Apate DNS"] = config[13]#
		dict["Kill NO-IP"] = config[14]#
		dict["Block Virus Total"] = config[15]#
		dict["Install Name"] = config[16]#
		dict["ByPass Malware Bytes"] = config[20]#
		dict["Kill SpyTheSPy"] = config[21]#
		dict["Connection Delay"] = config[22]#
		dict["Copy To All Drives"] = config[23]#
		dict["HideProcess"] = config[24]
		if config[17] == "True":
			dict["Install Path"] = "App Data"
		if config[18] == "True":
			dict["Install Path"] = "TEMP"
		if config[19] == "True":
			dict["Install Path"] = "Documents"
		return dict
	else:
		return None

	
if __name__ == "__main__":
	parser = OptionParser(usage='usage: %prog inFile outConfig\n' + __description__, version='%prog ' + __version__)
	(options, args) = parser.parse_args()
	if len(args) > 0:
		pass
	else:
		parser.print_help()
		sys.exit()
	try:
		print "[+] Reading file"
		fileData = open(args[0], 'rb').read()
	except:
		print "[+] Couldn't Open File {0}".format(args[0])
	print "[+] Searching for Config"
	config = run(fileData)
	if config == None:
		print "[+] Config not found"
		sys.exit()
	if len(args) == 2:
		print "[+] Writing Config to file {0}".format(args[1])
		with open(args[1], 'a') as outFile:
			for key, value in sorted(config.iteritems()):
				clean_value = filter(lambda x: x in string.printable, value)
				outFile.write("Key: {0}\t\t Value: {1}\n".format(key,clean_value))
		
	else:
		print "[+] Printing Config to screen"
		for key, value in sorted(config.iteritems()):
			clean_value = filter(lambda x: x in string.printable, value)
			print "   [-] Key: {0}\t\t Value: {1}".format(key,clean_value)
		print "[+] End of Config"
########NEW FILE########
__FILENAME__ = SmallNet
#!/usr/bin/env python
'''
SmallNet Config Decoder
'''

__description__ = 'SmallNet Config Extractor'
__author__ = 'Kevin Breen http://techanarchy.net'
__version__ = '0.1'
__date__ = '2014/03/15'

import sys
import string
from optparse import OptionParser

def run(data):
	if "!!<3SAFIA<3!!" in data:
		config = version52(data)
		return config
	elif "!!ElMattadorDz!!" in data:
		config = version5(data)
		return config
	else:
		return None
	

def version52(data):
	dict = {}
	config = data.split("!!<3SAFIA<3!!")
	dict["Domain"] = config[1]
	dict["Port"] = config[2]
	dict["Disbale Registry"] = config[3]
	dict["Disbale TaskManager"] = config[4]
	dict["Install Server"] = config[5]
	dict["Registry Key"] = config[8]
	dict["Install Name"] = config[9]
	dict["Disbale UAC"] = config[10]
	dict["Anti-Sandboxie"] = config[13]
	dict["Anti-Anubis"] = config[14]
	dict["Anti-VirtualBox"] = config[15]
	dict["Anti-VmWare"] = config[16]
	dict["Anti-VirtualPC"] = config[17]
	dict["ServerID"] = config[18]
	dict["USB Spread"] = config[19]
	dict["P2P Spread"] = config[20]
	dict["RAR Spread"] = config[21]
	dict["MSN Spread"] = config[22]
	dict["Yahoo Spread"] = config[23]
	dict["LAN Spread"] = config[24]
	dict["Disbale Firewall"] = config[25] #Correct
	dict["Delay Execution MiliSeconds"] = config[26]
	dict["Attribute Read Only"] = config[27]
	dict["Attribute System File"] = config[28]
	dict["Attribute Hidden"] = config[29]
	dict["Attribute Compressed"] = config[30]
	dict["Attribute Temporary"] = config[31]
	dict["Attribute Archive"] = config[32]
	dict["Modify Creation Date"] = config[33]
	dict["Modified Creation Data"] = config[34]
	dict["Thread Persistance"] = config[35]
	dict["Anti-ZoneAlarm"] = config[36]
	dict["Anti-SpyTheSpy"] = config[37]
	dict["Anti-NetStat"] = config[38]
	dict["Anti-TiGeRFirewall"] = config[39]
	dict["Anti-TCPview"] = config[40]
	dict["Anti-CurrentPorts"] = config[41]
	dict["Anti-RogueKiller"] = config[42]
	dict["Enable MessageBox"] = config[43]
	dict["MessageBox Message"] = config[44]
	dict["MessageBox Icon"] = config[45]
	dict["MessageBox Buttons"] = config[46]
	dict["MessageBox Title"] = config[47]	
	if config[6] == 1:
		dict["Install Path"] = "Temp"
	if config[7] == 1:
		dict["Install Path"] = "Windows"
	if config[11] == 1:
		dict["Install Path"] = "System32"
	if config[12] == 1:
		dict["Install Path"] = "Program Files"
	return dict


def version5(data):
	dict = {}
	config = data.split("!!ElMattadorDz!!")
	dict["Domain"] = config[1] #Correct
	dict["Port"] = config[2] #Correct
	dict["Disable Registry"] = config[3]
	dict["Disbale TaskManager"] = config[4] #Correct
	dict["Install Server"] = config[5] #Correct
	dict["Registry Key"] = config[8] #Correct
	dict["Install Name"] = config[9] #Correct
	dict["Disbale UAC"] = config[10]
	dict["Anti-Sandboxie"] = config[13]
	dict["Anti-Anubis"] = config[14]
	dict["Anti-VirtualBox"] = config[15]
	dict["Anti-VmWare"] = config[16]
	dict["Anti-VirtualPC"] = config[17]
	dict["ServerID"] = config[18] # Correct
	dict["USB Spread"] = config[19] #Correct
	dict["P2P Spread"] = config[20] #Correct
	dict["RAR Spread"] = config[21]
	dict["MSN Spread"] = config[22]
	dict["Yahoo Spread"] = config[23]
	dict["LAN Spread"] = config[24]
	dict["Disbale Firewall"] = config[25] #Correct
	dict["Delay Execution MiliSeconds"] = config[26] #Correct
	if config[6] == 1: #Correct
		dict["Install Path"] = "Temp"
	if config[7] == 1: #Correct
		dict["Install Path"] = "Windows" 
	if config[11] == 1: #Correct
		dict["Install Path"] = "System32"
	if config[12] == 1: #Correct
		dict["Install Path"] = "Program Files"
	return dict

	
if __name__ == "__main__":
	parser = OptionParser(usage='usage: %prog inFile outConfig\n' + __description__, version='%prog ' + __version__)
	(options, args) = parser.parse_args()
	if len(args) > 0:
		pass
	else:
		parser.print_help()
		sys.exit()
	try:
		print "[+] Reading file"
		fileData = open(args[0], 'rb').read()
	except:
		print "[+] Couldn't Open File {0}".format(args[0])
	print "[+] Searching for Config"
	config = run(fileData)
	if config == None:
		print "[+] Config not found"
		sys.exit()
	if len(args) == 2:
		print "[+] Writing Config to file {0}".format(args[1])
		with open(args[1], 'a') as outFile:
			for key, value in sorted(config.iteritems()):
				clean_value = filter(lambda x: x in string.printable, value)
				outFile.write("Key: {0}\t Value: {1}\n".format(key,clean_value))
		
	else:
		print "[+] Printing Config to screen"
		for key, value in sorted(config.iteritems()):
			clean_value = filter(lambda x: x in string.printable, value)
			print "   [-] Key: {0}\t Value: {1}".format(key,clean_value)
		print "[+] End of Config"
########NEW FILE########
__FILENAME__ = SpyGate
#!/usr/bin/env python
'''
CyberGate Config Decoder
'''

__description__ = 'CyberGate Config Extractor'
__author__ = 'Kevin Breen http://techanarchy.net'
__version__ = '0.1'
__date__ = '2014/03/15'

import sys
import string
from optparse import OptionParser
import pype32


def run(rawData):
	#try:
		rawconfig = rawData.split("abccba")
		if len(rawconfig) > 1:
			print "Running Abccba"
			dict = oldversions(rawconfig)
		else:
			print "Running pype32"
			pe = pype32.PE(data=rawData) 
			rawConfig = getStream(pe)
			if rawConfig.startswith("bute"): # workaround for an error in pype32 will still work when fixed
				rawConfig = rawConfig[8:]
			dict = parseConfig(rawConfig)
		#except:
			#return None
		print dict
		

		
# Confirm if there is Net MetaData in the File 
def getStream(pe):
	counter = 0   
	for dir in pe.ntHeaders.optionalHeader.dataDirectory:
		if dir.name.value == "NET_METADATA_DIRECTORY":
			rawConfig = findUSStream(pe, counter)
		else:
			counter += 1
	return rawConfig

# I only want to extract the User Strings Section
def findUSStream(pe, dir):
	for i in range(0,4):
		name = pe.ntHeaders.optionalHeader.dataDirectory[dir].info.netMetaDataStreams[i].name.value
		if name.startswith("#US"):
			return pe.ntHeaders.optionalHeader.dataDirectory[dir].info.netMetaDataStreams[i].info
 
#Walk the User Strings and create a list of individual strings
def parseConfig(rawConfig):
	stringList = []
	offset = 1
	config = bytearray(rawConfig)
	while offset < len(config):
		length = int(config[offset])
		that = config[offset+1:offset+int(length)]
		stringList.append(str(that.replace("\x00", "")))
		offset += int(length+1)
	print stringList
	dict = {}
	for i in range(0,60):
		dict["Domain"] = stringList[37]
		dict["Port"] = stringList[39]
		dict["Campaign Name"] = stringList[38]
		dict["FolderName"] = stringList[41]
		dict["Exe Name"] = stringList[40]
		dict["Install Folder"] = stringList[44]
	return dict
	
def oldversions(config):
	dict = {}
	if len(config) == 48:
		dict["Version"] = "V0.2.6"
		for i in range(1, len(config)):
			dict["Domain"] = config[1] #
			dict["Port"] = config[2] #
			dict["Campaign Name"] = config[3] #
			dict["Dan Option"] = config[5] #
			dict["Startup Name"] = config[7] #
			dict["Password"] = config[9] #
			dict["Anti Kill Server"] = config[10] #
			dict["USB Spread / lnk"] = config[11]
			dict["Anti Process Explorer"] = config[12]
			dict["Anti Process Hacker"] = config[13]
			dict["Anti ApateDNS"] = config[14]
			dict["Anti MalwareBytes"] = config[15]
			dict["Anti AntiLogger"] = config[16]
			dict["Block Virus Total"] = config[17] #
			dict["Mutex"] = config[18] #
			dict["Persistance"] = config[19] #
			dict["SpyGate Key"] = config[20]
			dict["Startup Folder"] = config[21] #
			dict["Anti Avira"] = config[23]
			dict["USB Spread / exe"] = config[24]
			# 25 if statement below
			dict["Install Folder1"] = config[26] #
			dict["StartUp Name"] = config[27] #
			dict["Melt After Run"] = config[28] #
			dict["Hide After Run"] = config[29] #
			#dict[""] = config[30]
			#dict[""] = config[31]
			#dict[""] = config[32]
			dict["Install Folder2"] = config[33] #
			# 34 and 35 in if statement below
			dict["Install Folder3"] = config[36]
			#dict[""] = config[37]
			dict["Anti SbieCtrl"] = config[38]
			dict["Anti SpyTheSpy"] = config[39]
			dict["Anti SpeedGear"] = config[40]
			dict["Anti Wireshark"] = config[41]
			dict["Anti IPBlocker"] = config[42]
			dict["Anti Cports"] = config[43]
			dict["Anti AVG"] = config[44]
			dict["Anti OllyDbg"] = config[45]
			dict["Anti X Netstat"] = config[46]
			#dict["Anti Keyscrambler"] = config[47]
				
		if config[25] == "True":
			dict["Application Data Folder"] = "True"
		else:
			dict["Application Data Folder"] = "False"
			
		if config[34] == "True":
			dict["Templates Folder"] = "True"
		else:
			dict["Templates Folder"] = "False"
			
		if config[35] == "True":
			dict["Programs Folder"] = "True"
		else:
			dict["Programs Folder"] = "False"
	elif len(config) == 18:
		dict["Version"] = "V2.0"
		for i in range(1, len(config)):
			print i, config[i]
			dict["Domain"] = config[1] #
			dict["Port"] = config[2] #
			dict["Campaign Name"] = config[3] #
			dict["Dan Option"] = config[5] #
			dict["Add To Startup"] = config[5] #
			dict["Startup Key"] = config[7] #
			dict["Password"] = config[9] #
			dict["Anti Kill Server"] = config[10]  #
			dict["USB Spread"] = config[11] #
			dict["Kill Process Explorer"] = config[12] #
			dict["Anti Process Hacker"] = config[13] #
			dict["Anti ApateDNS"] = config[14]
			dict["Anti MalwareBytes"] = config[15]
			dict["Anti AntiLogger"] = config[16]
			dict["Block Virus Total"] = config[17]
	else:
		return None
	return dict
	
if __name__ == "__main__":
	parser = OptionParser(usage='usage: %prog inFile outConfig\n' + __description__, version='%prog ' + __version__)
	(options, args) = parser.parse_args()
	if len(args) > 0:
		pass
	else:
		parser.print_help()
		sys.exit()
	try:
		print "[+] Reading file"
		fileData = open(args[0], 'rb').read()
	except:
		print "[+] Couldn't Open File {0}".format(args[0])
	print "[+] Searching for Config"
	config = run(fileData)
	if config == None:
		print "[+] Config not found"
		sys.exit()
	if len(args) == 2:
		print "[+] Writing Config to file {0}".format(args[1])
		with open(args[1], 'a') as outFile:
			for key, value in sorted(config.iteritems()):
				clean_value = filter(lambda x: x in string.printable, value)
				outFile.write("Key: {0}\t Value: {1}\n".format(key,clean_value))
		
	else:
		print "[+] Printing Config to screen"
		for key, value in sorted(config.iteritems()):
			clean_value = filter(lambda x: x in string.printable, value)
			print "   [-] Key: {0}\t Value: {1}".format(key,clean_value)
		print "[+] End of Config"
########NEW FILE########
__FILENAME__ = TEMPLATE
#!/usr/bin/env python
'''
ArCom Rat Config Decoder
'''


__description__ = 'ArCom Rat Config Extractor'
__author__ = 'Kevin Breen http://techanarchy.net http://malwareconfig.com'
__version__ = '0.1'
__date__ = '2014/04/10'

#Standard Imports Go Here
import os
import sys
import base64
import string
from optparse import OptionParser

#Non Standard Imports
try:
	from Crypto.Cipher import Blowfish
except ImportError:
	print "[+] Couldn't Import Cipher, try 'sudo pip install pycrypto'"


# Main Decode Function Goes Here
'''
data is a read of the file
Must return a python dict of values
'''

def run(data):
	
	pass
	
		
#Helper Functions Go Here



#Recursive Function Goes Here

def runRecursive(folder, output):
	counter1 = 0
	counter2 = 0
	print "[+] Writing Configs to File {0}".format(output)
	with open(output, 'a+') as out:
		#This line will need changing per Decoder
		out.write("Filename,Domain, Port, Install Path, Install Name, StartupKey, Campaign ID, Mutex Main, Mutex Per, YPER, YGRB, Mutex Grabber, Screen Rec Link, Mutex 4, YVID, YIM, No, Smart, Plugins, Flag1, Flag2, Flag3, Flag4, WebPanel, Remote Delay\n")	
		for server in os.listdir(folder):
			fileData = open(os.path.join(folder,server), 'rb').read()
			configOut = run(fileData)
			if configOut != None:
				#This line will need changing per Decoder
				out.write('{0},{1},{2},{3},{4},{5},{6},{7},{8},{9},{10},{11},{12},{13},{14},{15},{16},{17},{18},{19},{20},{21},{22},{23},{24},{25}\n'.format(server, configOut["Domain"],configOut["Port"],configOut["Install Path"],configOut["Install Name"],configOut["Startup Key"],configOut["Campaign ID"],configOut["Mutex Main"],configOut["Mutex Per"],configOut["YPER"],configOut["YGRB"],configOut["Mutex Grabber"],configOut["Screen Rec Link"],configOut["Mutex 4"],configOut["YVID"],configOut["YIM"],configOut["NO"],configOut["Smart Broadcast"],configOut["YES"],configOut["Plugins"],configOut["Flag1"],configOut["Flag2"],configOut["Flag3"],configOut["Flag4"],configOut["WebPanel"],configOut["Remote Delay"]))
				counter1 += 1
			counter2 += 1
	print "[+] Decoded {0} out of {1} Files".format(counter1, counter2)
	return "Complete"

# Main

if __name__ == "__main__":
	parser = OptionParser(usage='usage: %prog inFile outConfig\n' + __description__, version='%prog ' + __version__)
	parser.add_option("-r", "--recursive", action='store_true', default=False, help="Recursive Mode")
	(options, args) = parser.parse_args()
	# If we dont have args quit with help page
	if len(args) > 0:
		pass
	else:
		parser.print_help()
		sys.exit()
	# if we want a recursive extract run this function
	if options.recursive == True:
		if len(args) == 2:
			runRecursive(args[0], args[1])
			sys.exit()
		else:
			print "[+] You need to specify Both Dir to read AND Output File"
			parser.print_help()
			sys.exit()
	
	# If not recurisve try to open file
	try:
		print "[+] Reading file"
		fileData = open(args[0], 'rb').read()
	except:
		print "[+] Couldn't Open File {0}".format(args[0])
	#Run the config extraction
	print "[+] Searching for Config"
	config = run(fileData)
	#If we have a config figure out where to dump it out.
	if config == None:
		print "[+] Config not found"
		sys.exit()
	#if you gave me two args im going to assume the 2nd arg is where you want to save the file
	if len(args) == 2:
		print "[+] Writing Config to file {0}".format(args[1])
		with open(args[1], 'a') as outFile:
			for key, value in sorted(config.iteritems()):
				clean_value = filter(lambda x: x in string.printable, value)
				outFile.write("Key: {0}\t Value: {1}\n".format(key,clean_value))
	# if no seconds arg then assume you want it printing to screen
	else:
		print "[+] Printing Config to screen"
		for key, value in sorted(config.iteritems()):
			clean_value = filter(lambda x: x in string.printable, value)
			print "   [-] Key: {0}\t Value: {1}".format(key,clean_value)
		print "[+] End of Config"

########NEW FILE########
__FILENAME__ = unrecom
#!/usr/bin/env python
'''
Unrecom Rat Config Parser

'''
__description__ = 'unrecom rat Config Parser'
__author__ = 'Kevin Breen'
__version__ = '0.1'
__date__ = '2014/05/22'

import sys

import string
from zipfile import ZipFile
from optparse import OptionParser
import xml.etree.ElementTree as ET

try:
    from Crypto.Cipher import ARC4
except ImportError:
    print "Cannot import PyCrypto, Is it installed?"


def main():
    parser = OptionParser(usage='usage: %prog jarfile\n' + __description__, version='%prog ' + __version__)
    (options, args) = parser.parse_args()
    if len(args) != 1:
        parser.print_help()
        sys.exit()
    archive = args[0]
    # Decrypt & Extract the embedded Jar
    print "[+] Reading File"
    try:
        embedded = extract_embedded(archive)
    except:
        print "[+] Failed to Read File"
        sys.exit()
    # Look for our config file
    print "    [-] Looking for Config"
    config = parse_embedded(embedded)
    # Print to pretty Output
    print "[+] Found Config"
    print_config(config)    
    
def extract_embedded(archive):
    enckey = None
    adwind_flag = False
    with ZipFile(archive, 'r') as zip:
        for name in zip.namelist(): # get all the file names
            if name == "load/ID": # contains first part of key
                partial_key = zip.read(name)
                enckey = partial_key + 'DESW7OWKEJRU4P2K' # complete key
                print "    [-] Found Key {0}".format(zip.read(name))
            if name == "load/MANIFEST.MF": # this is the embedded jar                
                raw_embedded = zip.read(name)
            if name == "load/stub.adwind": # This is adwind 3
                raw_embedded = zip.read(name)
                adwind_flag = True
                
    if adwind_flag:
        enckey = partial_key
    if enckey != None:
        # Decrypt The raw file
        print "    [-] Decrypting Embedded Jar"
        dec_embedded = decrypt_arc4(enckey, raw_embedded)
        return dec_embedded
    else:
        print "[+] No embedded File Found"
        sys.exit()


def parse_embedded(data):
    newzipdata = data
    from cStringIO import StringIO
    newZip = StringIO(newzipdata) # Write new zip file to memory instead of to disk
    with ZipFile(newZip) as zip:
        for name in zip.namelist():
            if name == "config.xml": # this is the config in clear
                config = zip.read(name)
    return config
        
def decrypt_arc4(enckey, data):
        cipher = ARC4.new(enckey) # set the ciper
        return cipher.decrypt(data) # decrpyt the data

def print_config(config):
    xml = filter(lambda x: x in string.printable, config)
    root = ET.fromstring(xml)
    raw_config = {}
    for child in root:
        if child.text.startswith("Unrecom"):
            raw_config["Version"] = child.text
        else:
            raw_config[child.attrib["key"]] = child.text
    
    for key, value in sorted(raw_config.iteritems()):
        print "    [-] Key: {0}\t Value: {1}".format(key, value)
    
    
if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = VirusRat
#!/usr/bin/env python
'''
VirusRat Config Decoder
'''

__description__ = 'VirusRat Config Extractor'
__author__ = 'Kevin Breen http://techanarchy.net'
__version__ = '0.1'
__date__ = '2014/03/15'

import sys
import string
from optparse import OptionParser

	

def run(data):
	dict = {}
	config = data.split("abccba")
	if len(config) > 5:
		dict["Domain"] = config[1]
		dict["Port"] = config[2]
		dict["Campaign Name"] = config[3]
		dict["Copy StartUp"] = config[4]
		dict["StartUp Name"] = config[5]
		dict["Add To Registry"] = config[6]
		dict["Registry Key"] = config[7]
		dict["Melt + Inject SVCHost"] = config[8]
		dict["Anti Kill Process"] = config[9]
		dict["USB Spread"] = config[10]
		dict["Kill AVG 2012-2013"] = config[11]
		dict["Kill Process Hacker"] = config[12]
		dict["Kill Process Explorer"] = config[13]
		dict["Kill NO-IP"] = config[14]
		dict["Block Virus Total"] = config[15]
		dict["Block Virus Scan"] = config[16]
		dict["HideProcess"] = config[17]
		return dict
	else:
		return None

	
if __name__ == "__main__":
	parser = OptionParser(usage='usage: %prog inFile outConfig\n' + __description__, version='%prog ' + __version__)
	(options, args) = parser.parse_args()
	if len(args) > 0:
		pass
	else:
		parser.print_help()
		sys.exit()
	try:
		print "[+] Reading file"
		fileData = open(args[0], 'rb').read()
	except:
		print "[+] Couldn't Open File {0}".format(args[0])
	print "[+] Searching for Config"
	config = run(fileData)
	if config == None:
		print "[+] Config not found"
		sys.exit()
	if len(args) == 2:
		print "[+] Writing Config to file {0}".format(args[1])
		with open(args[1], 'a') as outFile:
			for key, value in sorted(config.iteritems()):
				clean_value = filter(lambda x: x in string.printable, value)
				outFile.write("Key: {0}\t Value: {1}\n".format(key,clean_value))
		
	else:
		print "[+] Printing Config to screen"
		for key, value in sorted(config.iteritems()):
			clean_value = filter(lambda x: x in string.printable, value)
			print "   [-] Key: {0}\t Value: {1}".format(key,clean_value)
		print "[+] End of Config"
########NEW FILE########
__FILENAME__ = Xtreme
#!/usr/bin/env python
'''
xtreme Rat Config Decoder
'''


__description__ = 'xtreme Rat Config Extractor'
__author__ = 'Kevin Breen http://techanarchy.net http://malwareconfig.com'
__version__ = '0.1'
__date__ = '2014/04/10'

#Standard Imports Go Here
import os
import sys
import string
from struct import unpack
from optparse import OptionParser

#Non Standard Imports
try:
	import pefile
except ImportError:
	print "Couldn't Import pefile. Try 'sudo pip install pefile'"



# Main Decode Function Goes Here
'''
data is a read of the file
Must return a python dict of values
'''

def run(data):
	key = "C\x00O\x00N\x00F\x00I\x00G"
	codedConfig = configExtract(data)
	if codedConfig is not None:
        	rawConfig = rc4crypt(codedConfig, key)
        	#1.3.x # Not implemented yet
        	if len(rawConfig) == 0xe10:
        		config = None
        	#2.9.x #Not a stable extract
        	elif len(rawConfig) == 0x1390 or len(rawConfig) == 0x1392:
        		config = v29(rawConfig)
        	#3.1 & 3.2
        	elif len(rawConfig) == 0x5Cc:
        		config = v32(rawConfig)
        	#3.5
        	elif len(rawConfig) == 0x7f0:
        		config = v35(rawConfig)
        	else:
        		config = None
        	return config
        else:
                print '[-] Coded config not found'
                sys.exit()
	
		
#Helper Functions Go Here
def rc4crypt(data, key): # modified for bad implemented key length
    x = 0
    box = range(256)
    for i in range(256):
        x = (x + box[i] + ord(key[i % 6])) % 256
        box[i], box[x] = box[x], box[i]
    x = 0
    y = 0
    out = []
    for char in data:
        x = (x + 1) % 256
        y = (y + box[x]) % 256
        box[x], box[y] = box[y], box[x]
        out.append(chr(ord(char) ^ box[(box[x] + box[y]) % 256]))
    
    return ''.join(out)

def configExtract(rawData):
	try:
		pe = pefile.PE(data=rawData)
		try:
		  rt_string_idx = [
		  entry.id for entry in 
		  pe.DIRECTORY_ENTRY_RESOURCE.entries].index(pefile.RESOURCE_TYPE['RT_RCDATA'])
		except ValueError, e:
			return None
		except AttributeError, e:
			return None
		rt_string_directory = pe.DIRECTORY_ENTRY_RESOURCE.entries[rt_string_idx]
		for entry in rt_string_directory.directory.entries:
			if str(entry.name) == "XTREME":
				data_rva = entry.directory.entries[0].data.struct.OffsetToData
				size = entry.directory.entries[0].data.struct.Size
				data = pe.get_memory_mapped_image()[data_rva:data_rva+size]
				return data
	except:
		return None	

		
def v29(rawConfig):
	dict = {}
	dict["ID"] = getUnicodeString(rawConfig, 0x9e0)
	dict["Group"] = getUnicodeString(rawConfig, 0xa5a)
	dict["Version"] = getUnicodeString(rawConfig, 0xf2e) # use this to recalc offsets
	dict["Mutex"] = getUnicodeString(rawConfig, 0xfaa)
	dict["Install Dir"] = getUnicodeString(rawConfig, 0xb50)
	dict["Install Name"] = getUnicodeString(rawConfig, 0xad6)
	dict["HKLM"] = getUnicodeString(rawConfig, 0xc4f)
	dict["HKCU"] = getUnicodeString(rawConfig, 0xcc8)
	dict["Custom Reg Key"] = getUnicodeString(rawConfig, 0xdc0)
	dict["Custom Reg Name"] = getUnicodeString(rawConfig, 0xe3a)
	dict["Custom Reg Value"] = getUnicodeString(rawConfig, 0xa82)
	dict["ActiveX Key"] = getUnicodeString(rawConfig, 0xd42)
	dict["Injection"] = getUnicodeString(rawConfig, 0xbd2)
	dict["FTP Server"] = getUnicodeString(rawConfig, 0x111c)
	dict["FTP UserName"] = getUnicodeString(rawConfig, 0x1210)
	dict["FTP Password"] = getUnicodeString(rawConfig, 0x128a)
	dict["FTP Folder"] = getUnicodeString(rawConfig, 0x1196)
	dict["Domain1"] = str(getUnicodeString(rawConfig, 0x50)+":"+str(unpack("<I",rawConfig[0:4])[0]))
	dict["Domain2"] = str(getUnicodeString(rawConfig, 0xca)+":"+str(unpack("<I",rawConfig[4:8])[0]))
	dict["Domain3"] = str(getUnicodeString(rawConfig, 0x144)+":"+str(unpack("<I",rawConfig[8:12])[0]))
	dict["Domain4"] = str(getUnicodeString(rawConfig, 0x1be)+":"+str(unpack("<I",rawConfig[12:16])[0]))
	dict["Domain5"] = str(getUnicodeString(rawConfig, 0x238)+":"+str(unpack("<I",rawConfig[16:20])[0]))
	dict["Domain6"] = str(getUnicodeString(rawConfig, 0x2b2)+":"+str(unpack("<I",rawConfig[20:24])[0]))
	dict["Domain7"] = str(getUnicodeString(rawConfig, 0x32c)+":"+str(unpack("<I",rawConfig[24:28])[0]))
	dict["Domain8"] = str(getUnicodeString(rawConfig, 0x3a6)+":"+str(unpack("<I",rawConfig[28:32])[0]))
	dict["Domain9"] = str(getUnicodeString(rawConfig, 0x420)+":"+str(unpack("<I",rawConfig[32:36])[0]))
	dict["Domain10"] = str(getUnicodeString(rawConfig, 0x49a)+":"+str(unpack("<I",rawConfig[36:40])[0]))
	dict["Domain11"] = str(getUnicodeString(rawConfig, 0x514)+":"+str(unpack("<I",rawConfig[40:44])[0]))
	dict["Domain12"] = str(getUnicodeString(rawConfig, 0x58e)+":"+str(unpack("<I",rawConfig[44:48])[0]))
	dict["Domain13"] = str(getUnicodeString(rawConfig, 0x608)+":"+str(unpack("<I",rawConfig[48:52])[0]))
	dict["Domain14"] = str(getUnicodeString(rawConfig, 0x682)+":"+str(unpack("<I",rawConfig[52:56])[0]))
	dict["Domain15"] = str(getUnicodeString(rawConfig, 0x6fc)+":"+str(unpack("<I",rawConfig[56:60])[0]))
	dict["Domain16"] = str(getUnicodeString(rawConfig, 0x776)+":"+str(unpack("<I",rawConfig[60:64])[0]))
	dict["Domain17"] = str(getUnicodeString(rawConfig, 0x7f0)+":"+str(unpack("<I",rawConfig[64:68])[0]))
	dict["Domain18"] = str(getUnicodeString(rawConfig, 0x86a)+":"+str(unpack("<I",rawConfig[68:72])[0]))
	dict["Domain19"] = str(getUnicodeString(rawConfig, 0x8e4)+":"+str(unpack("<I",rawConfig[72:76])[0]))
	dict["Domain20"] = str(getUnicodeString(rawConfig, 0x95e)+":"+str(unpack("<I",rawConfig[76:80])[0]))

	return dict
		
def v32(rawConfig):
	dict = {}
	dict["ID"] = getUnicodeString(rawConfig, 0x1b4)
	dict["Group"] = getUnicodeString(rawConfig, 0x1ca)
	dict["Version"] = getUnicodeString(rawConfig, 0x2bc)
	dict["Mutex"] = getUnicodeString(rawConfig, 0x2d4)
	dict["Install Dir"] = getUnicodeString(rawConfig, 0x1f8)
	dict["Install Name"] = getUnicodeString(rawConfig, 0x1e2)
	dict["HKLM"] = getUnicodeString(rawConfig, 0x23a)
	dict["HKCU"] = getUnicodeString(rawConfig, 0x250)
	dict["ActiveX Key"] = getUnicodeString(rawConfig, 0x266)
	dict["Injection"] = getUnicodeString(rawConfig, 0x216)
	dict["FTP Server"] = getUnicodeString(rawConfig, 0x35e)
	dict["FTP UserName"] = getUnicodeString(rawConfig, 0x402)
	dict["FTP Password"] = getUnicodeString(rawConfig, 0x454)
	dict["FTP Folder"] = getUnicodeString(rawConfig, 0x3b0)
	dict["Domain1"] = str(getUnicodeString(rawConfig, 0x14)+":"+str(unpack("<I",rawConfig[0:4])[0]))
	dict["Domain2"] = str(getUnicodeString(rawConfig, 0x66)+":"+str(unpack("<I",rawConfig[4:8])[0]))
	dict["Domain3"] = str(getUnicodeString(rawConfig, 0xb8)+":"+str(unpack("<I",rawConfig[8:12])[0]))
	dict["Domain4"] = str(getUnicodeString(rawConfig, 0x10a)+":"+str(unpack("<I",rawConfig[12:16])[0]))
	dict["Domain5"] = str(getUnicodeString(rawConfig, 0x15c)+":"+str(unpack("<I",rawConfig[16:20])[0]))
	dict["Msg Box Title"] = getUnicodeString(rawConfig, 0x50c)
	dict["Msg Box Text"] = getUnicodeString(rawConfig, 0x522)
	return dict
		

def v35(rawConfig):
	dict = {}
	dict["ID"] = getUnicodeString(rawConfig, 0x1b4)
	dict["Group"] = getUnicodeString(rawConfig, 0x1ca)
	dict["Version"] = getUnicodeString(rawConfig, 0x2d8)
	dict["Mutex"] = getUnicodeString(rawConfig, 0x2f0)
	dict["Install Dir"] = getUnicodeString(rawConfig, 0x1f8)
	dict["Install Name"] = getUnicodeString(rawConfig, 0x1e2)
	dict["HKLM"] = getUnicodeString(rawConfig, 0x23a)
	dict["HKCU"] = getUnicodeString(rawConfig, 0x250)
	dict["ActiveX Key"] = getUnicodeString(rawConfig, 0x266)
	dict["Injection"] = getUnicodeString(rawConfig, 0x216)
	dict["FTP Server"] = getUnicodeString(rawConfig, 0x380)
	dict["FTP UserName"] = getUnicodeString(rawConfig, 0x422)
	dict["FTP Password"] = getUnicodeString(rawConfig, 0x476)
	dict["FTP Folder"] = getUnicodeString(rawConfig, 0x3d2)
	dict["Domain1"] = str(getUnicodeString(rawConfig, 0x14)+":"+str(unpack("<I",rawConfig[0:4])[0]))
	dict["Domain2"] = str(getUnicodeString(rawConfig, 0x66)+":"+str(unpack("<I",rawConfig[4:8])[0]))
	dict["Domain3"] = str(getUnicodeString(rawConfig, 0xb8)+":"+str(unpack("<I",rawConfig[8:12])[0]))
	dict["Domain4"] = str(getUnicodeString(rawConfig, 0x10a)+":"+str(unpack("<I",rawConfig[12:16])[0]))
	dict["Domain5"] = str(getUnicodeString(rawConfig, 0x15c)+":"+str(unpack("<I",rawConfig[16:20])[0]))
	dict["Msg Box Title"] = getUnicodeString(rawConfig, 0x52c)
	dict["Msg Box Text"] = getUnicodeString(rawConfig, 0x542)
	return dict


def getString(buf,pos):
	out = ""
	for c in buf[pos:]:
		if ord(c) == 0:
			break
		out += c
	
	if out == "":
		return None
	else:
		return out

def getUnicodeString(buf,pos):
	out = ""
	for i in range(len(buf[pos:])):
		if not (ord(buf[pos+i]) >= 32 and ord(buf[pos+i]) <= 126) and not (ord(buf[pos+i+1]) >= 32 and ord(buf[pos+i+1]) <= 126):
			out += "\x00"
			break
		out += buf[pos+i]
	if out == "":
		return None
	else:
		return out.replace("\x00","")


#Recursive Function Goes Here


# Main

if __name__ == "__main__":
	parser = OptionParser(usage='usage: %prog inFile outConfig\n' + __description__, version='%prog ' + __version__)
	parser.add_option("-r", "--recursive", action='store_true', default=False, help="Recursive Mode")
	(options, args) = parser.parse_args()
	# If we dont have args quit with help page
	if len(args) > 0:
		pass
	else:
		parser.print_help()
		sys.exit()
	# if we want a recursive extract run this function
	if options.recursive == True:
		print "[+] Sorry No Recursive Yet Check Back Soon"
		parser.print_help()
		sys.exit()
	
	# If not recurisve try to open file
	try:
		print "[+] Reading file"
		fileData = open(args[0], 'rb').read()
	except:
		print "[+] Couldn't Open File {0}".format(args[0])
	#Run the config extraction
	print "[+] Searching for Config"
	config = run(fileData)
	#If we have a config figure out where to dump it out.
	if config == None:
		print "[+] Config not found"
		sys.exit()
	#if you gave me two args im going to assume the 2nd arg is where you want to save the file
	if len(args) == 2:
		print "[+] Writing Config to file {0}".format(args[1])
		with open(args[1], 'a') as outFile:
			for key, value in sorted(config.iteritems()):
				clean_value = filter(lambda x: x in string.printable, value)
				outFile.write("Key: {0}\t Value: {1}\n".format(key,clean_value))
	# if no seconds arg then assume you want it printing to screen
	else:
		print "[+] Printing Config to screen"
		for key, value in sorted(config.iteritems()):
			clean_value = filter(lambda x: x in string.printable, value)
			print "   [-] Key: {0}\t Value: {1}".format(key,clean_value)
		print "[+] End of Config"

########NEW FILE########
