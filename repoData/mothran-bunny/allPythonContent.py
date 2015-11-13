__FILENAME__ = bunnyChat
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#    bunnyChat.py
#
#    Copyright 2013 W. Parker Thompson <w.parker.thompson@gmail.com>
#		
#    This file is part of Bunny.
#
#    Bunny is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    Bunny is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with Bunny.  If not, see <http://www.gnu.org/licenses/>.

import libbunny
import threading, getopt, sys, time

def usage():
	"""
	
	print out usage
	
	"""
	print "BunnyChat.py [COMANDS]"
	print "  -l              --   Listen mode, gets packets and prints data"
	print "  -s [data]       --   Send mode, sends packets over and over"
	print "  -m              --   Passive profiling of all the channels (1-11)"
	print "  -c [UserName]   --   Chat client mode"
	print "  -r              --   Reloop shows the mod/remainder of the specified channel"
	print "  -p              --   Ping/Pong testing, Run this on one machine and it will"
	print "                        respond with a pong."
	print "  -k              --   Ping server mode, will repsond to pings with pong and current time"

def main():
	listen_mode = send_mode = scan_chans_mode = chat_mode = ping_mode_serv = ping_mode_client = reloop_mode = False
	
	# parse arguments
	try:
		opts, args = getopt.getopt(sys.argv[1:],"hlrmkpc:s:f:")
	except getopt.GetoptError as err:
		print str(err)
		usage()
		sys.exit(1)
	for opt, arg in opts:
		if opt == "-h":
			usage()
			sys.exit(0)
		elif opt == "-f":
			config_file = arg
		elif opt == "-l": 
			listen_mode = True
		elif opt == "-r":
			reloop_mode = True
		elif opt == "-s":
			send_mode = True
			send_data = arg
		elif opt == "-m":
			scan_chans_mode = True
		elif opt == "-c":
			UserName = arg
			chat_mode = True
		elif opt == "-k":
			ping_mode_serv = True
		elif opt == "-p":
			ping_mode_client = True
	if listen_mode:
		print "Bunny in listen mode"
		print "Building model: . . . "
		bunny = libbunny.Bunny()
		print "Bunny model built and ready to listen"
		while True:
			print bunny.recvBunny()
		bunny.killBunny()
	elif reloop_mode:
		#bunny = libbunny.Bunny()
		inandout = libbunny.SendRec()
		inandout.reloop()
		
	elif send_mode:
		if send_data is not None:
			bunny = libbunny.Bunny()
			print "Bunny model built"
			bunny.model.printTypes()
			bunny.model.printMacs()
			print "sending message: %s" % send_data
			bunny.sendBunny(send_data)
			
			while True:
				print "again? [Y/N]"
				input = sys.stdin.readline()
				if input == "Y\n" or input == "y\n":
					print "sending message: %s" % send_data
					bunny.sendBunny(send_data)
				elif input == "N\n" or input == "n\n":
					bunny.killBunny()
					sys.exit()
		else:
			print usage()
			sys.exit()
			
	elif chat_mode:
		print "chat client mode:"
		print "building traffic model: . . "
		bunny = libbunny.Bunny()
		
		print "built traffic model"
		bunny.model.printTypes()
		bunny.model.printMacs()
		print "starting threads: "
		
		# create list of threads
		# one thread for input and the other for output.
		# both use stdin or stdout
		workers = [StdInThread(bunny, UserName), BunnyThread(bunny, UserName)]
		
		for worker in workers:
			worker.daemon = True
			worker.start()
		
		# loop through every 3 seconds and check for dead threads
		while True:
			for worker in workers:
				if not worker.isAlive():
					bunny.killBunny()
					sys.exit()
			time.sleep(3)
		
	elif scan_chans_mode:
		for c in range(1,12):
			chan = c
			print "\nChannel: %d" % chan			
			bunny = libbunny.Bunny()
			bunny.model.printTypes()
			#bunny.model.printMacs()
			bunny.killBunny()
			
	elif ping_mode_serv:
		import struct
		
		bunny = libbunny.Bunny()
		print "Model completed, ready to play pong"
		while True:
			text = bunny.recvBunny()
			if text.find("ping") != -1:
				bunny.sendBunny(struct.pack("4sfs", "pong", time.time(), "\xff"))
				print "Pong sent"
				
		bunny.killBunny()
	
	elif ping_mode_client:
		import struct 
		
		total = 10.0
		bunny = libbunny.Bunny()
		count = 0
		avg_time = 0
		for num in range(0, int(total)):
			send_time = time.time()
			bunny.sendBunny("ping")
			text = bunny.recvBunny(2)
			if text is not False:
				#print text
				try:
					pong, mid_time, pad = struct.unpack("4sfs", text)
					
					if pong == "pong":
						in_time = time.time() - send_time
						avg_time += in_time
						count += 1
						print "got pong!"
						print "Travel time: %f\n" % (in_time)
						
				except struct.error as err:
					if text.find("ping") != -1:
						print "got ping, wtf!"
					else:
						print "bad data"
			else:
				print "ping timeout"
				time.sleep(0.1)
			#time.sleep(0.01)
		print "received:       %d packets" % (count)
		try:
			print "Percent recv'd: %02f%s" % (count * 100.0/ total, "%")
			print "Mean time:   %f" % (avg_time / count)
		except ZeroDivisionError:
			pass
		bunny.killBunny()
		
	else:
		usage()
		sys.exit()

# quick and dirty threading for the send/rec chat client mode.
class StdInThread(threading.Thread):
	"""
	
	Thread class for reading from STDIN
	
	"""
	# takes the bunny object as an argument
	def __init__(self, bunny, username):
		self.bunny = bunny
		self.username = username
		threading.Thread.__init__(self)
	def run (self):
		print "ready to read! (type: /quit to kill)"
		while True:
			input = sys.stdin.readline().strip("\n")
			if input == "/quit":
				break
			# send with UserName and a trailer to prevent the stripping of 'A's as padding
			# see the comment in the __init__() in AEScrypt
			self.bunny.sendBunny(self.username + ": " + input + "\xff")
			
class BunnyThread(threading.Thread):
	"""
	
	Thread class for reading from the bunny interface
	
	"""
	# takes the bunny object as an argument
	def __init__(self, bunny, username):
		self.bunny = bunny
		self.username = username
		threading.Thread.__init__(self)
	def run (self):
		# Standard calling should look like this:
		while True:
			text = self.bunny.recvBunny()
			# if we get our own UserName do not display it,
			# FIX THIS
			if text.split(":")[0] == self.username:
				continue
			else:
				# strip out the ending char.
				print text.rstrip("\xff")
				
		
if __name__ == "__main__":
	main()

########NEW FILE########
__FILENAME__ = AEScrypt
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#    bunny.py
#
#    Copyright 2013 W. Parker Thompson <w.parker.thompson@gmail.com>
#		
#    This file is part of Bunny.
#
#    Bunny is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    Bunny is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with Bunny.  If not, see <http://www.gnu.org/licenses/>.

import os, sys, struct

from keyczar.errors import InvalidSignatureError
from keyczar.keys import AesKey

from config import *

class AEScrypt:
	"""
	
	Class for encrypting and decrypting AES256 data.
	
	"""
	
	def __init__(self):
		# check if the key.kz file exists
		try:
			with open("keys.kz", "r") as fd:
				data = fd.read()
		except IOError:
			print "ERROR: no key file found, generating the file"
			self.key = AesKey.Generate()
			with open("keys.kz", "w+") as fd:
				fd.write(str(self.key))
		else:
			self.key = AesKey.Read(data)
			if DEBUG:
				print self.key.key_string
				print self.key.hmac_key
		
		# If keyczar changes their header format this would need to change:
		#  5 bytes for the header and 16 for the IV
		self.header_len = 5 + 16
		self.block_len = self.key.block_size
		self.hmac_len = self.key.hmac_key.size/8
		self.overhead = self.header_len + self.hmac_len
		
	def encrypt(self, data):
		
		# returns a block of string of cipher text.
		output = self.key.Encrypt(data)		
		return output
		
	def decrypt(self, data):
		
		try:
			output = self.key.Decrypt(data)
		except InvalidSignatureError:
			if DEBUG:
				print "ERROR: Invalid Signature, either there was a corruption or there was an attempted attack"
			return False
		except:
			# TODO: what exception is causing this?
			print "ERROR: Failed to decrypt the packet"
			if DEBUG:
				print "Exception: \n" + str(sys.exc_info()[0])
			return False
		
		return output
		

########NEW FILE########
__FILENAME__ = bunny
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#    bunny.py
#
#    Copyright 2013 W. Parker Thompson <w.parker.thompson@gmail.com>
#		
#    This file is part of Bunny.
#
#    Bunny is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    Bunny is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with Bunny.  If not, see <http://www.gnu.org/licenses/>.


import threading, Queue, binascii

from AEScrypt import *
from SendRec import *
from Templates import *
from TrafficModel import *
from config import *


# So this is the heart and soul of bunny and also the biggest mess in the code base.
#  if anyone wants to look over my use of threads, queue and deques it would be lovely
#  to get some feedback and if anyone thinks there is a way to speed this up it would help.

class Bunny:
	"""
	
	High level send and receive for wrapping all the lower-level functions of bunny in paranoid mode.
	
	"""
	
	def __init__(self):
		"""
		
		Setup and build the bunny model and starts the read_packet_thread()
		
		"""
		
		self.inandout = SendRec()
		self.cryptor = AEScrypt()
		self.model = TrafficModel()
		
		# each item should be an full bunny message that can be passed to the .decrypt() method
		# TODO: put a upper bound of number of messages or a cleanup thread to clear out old messages
		# 		if not consumed.
		self.msg_queue = Queue.LifoQueue()
		
		# The out queue is a FiFo Queue because it maintaines the ordering of the bunny data
		#  format: [data, Bool (relay or not)]
		self.out_queue = Queue.Queue()
		
		# The Deque is used because it is a thread safe iterable that can be filled with 'seen'
		# messages between the send and recv threads. 
		self.msg_deque = []
		
		# init the threads and name them
		self.workers = [BunnyReadThread(self.msg_queue, self.out_queue, self.inandout, self.model, self.cryptor), \
			BroadCaster(self.out_queue, self.inandout, self.model)]
		self.workers[0].name = "BunnyReadThread"
		self.workers[1].name = "BroadCasterThread"
		
		# spin up the threads
		for worker in self.workers:
			worker.daemon = True
			worker.start()
		
		#TODO: can I add a 'isAlive()' checking loop here?
		
	def sendBunny(self, packet):
		"""
		
		Send a Bunny (paranoid) packet
		
		"""
		packet = self.cryptor.encrypt(packet)
		# Prepend the length of the packet as the first two bytes.
		#  This allows for Bunny to know when to stop reading in packets.
		size = struct.pack("H", len(packet))
		packet = "%s%s" % (size, packet)
		
		self.msg_deque.append([packet, time.time()])
		self.out_queue.put([packet, False])
		
	def recvBunny(self, timer=False):
		"""
		
		Grab the next bunny message in the queue and decrypt it and return the plaintext message
		
		Arg: timer
			If not false, bunny will timeout in the number of seconds in timer
		
		Returns:
			Decrypted bunny message or if timedout, False
		
		"""
		# this is looped just so if the message has been seen we can come back and keep trying.
		while True:
			relay = False
			if timer:
				try:
					data = self.msg_queue.get(True, timer)
				except Queue.Empty:
					return False
			else:
				data = self.msg_queue.get()
			
			# check if the message has already been seen
			#  TODO: move this whole thing to a new thread
			cur_time = time.time()
			for message in self.msg_deque:
				if message[0] == data:
					if DEBUG:
						print "Already seen message, not sending to user"
					relay = True
				# remove old known messages
				if cur_time - message[1] > 60:
					self.msg_deque.remove(message)
					
			if relay == True:
				continue
			else:
				self.out_queue.put([data, True])
				self.msg_deque.append([data, time.time()])
				
				# remove the size data:
				data = data[2:]
				plaintext = self.cryptor.decrypt(data)
				if plaintext == False:
					continue
				else:
					return plaintext
				
	def killBunny(self):
		for worker in self.workers:
			worker.kill()

class BunnyReadThread(threading.Thread):

	def __init__(self, queue, out_queue, ioObj, model, cryptor):
		self.msg_queue = queue
		self.out_queue = out_queue
		self.inandout = ioObj
		self.model = model
		self.cryptor = cryptor
		
		self.running = True
		threading.Thread.__init__(self)

	def run(self):
		blockget = False
		decoded = ""
		
		while self.running:
			# declare / clear the type array.
			type = []
	
			encoded = self.inandout.recPacket_timeout(self.model.FCS)
				#TIMING
				#start_t = time.time()
			if encoded is False:
				blockget = False
				decoded = ""
				continue
			
			if DEBUG:
				print "\nHit packet"
				print "Type: %s\t Raw: %s" % (binascii.hexlify(encoded[0:1]), self.model.rawToType(encoded[0:1]))
			
			for entry in self.model.type_ranges:
				if entry[0] == encoded[0:1]:
					if entry[3] > 0:
						# check so that the injectable length is over 0
						type = entry
						break
			
			if len(type) < 2:
				if DEBUG:
					print "Packet type not in templates"
				
				entry = self.model.insertNewTemplate(encoded)
				if entry is not False:
					if DEBUG:
						print "successfuly inserted template"
					self.model.type_ranges.append(entry)
					type = entry
				else:
					if DEBUG:
						print "Packet type not implemented"
					continue
			
			# decode the bunny packet
			temp = type[2].decode(encoded)

			if temp is False:
				if DEBUG:
					print "decoding fail"
				continue
			else:
				if DEBUG:
					print "CypherText: " + binascii.hexlify(temp)
				
				if blockget == False:
					pack_len, = struct.unpack("H", temp[0:2])
					if DEBUG:
						print "size: " + str(pack_len)
					
					blockget = True
					decoded = "%s%s" % (decoded, temp)
					decoded_len = len(decoded)
				elif decoded_len < pack_len:
					decoded = "%s%s" % (decoded, temp)
					decoded_len = len(decoded)
				if decoded_len >= pack_len:
					if DEBUG:
						print "Adding message to Queues"
					self.msg_queue.put(decoded)
					
					#TIMING
					#print "recv time: %f" % (time.time() - start_t)
					
					# clean up for the next loop
					blockget = False
					decoded = ""
	def kill(self):
		self.running = False
		self.inandout.close()
						
class BroadCaster(threading.Thread):
	
	def __init__(self, queue, ioObj, model):
		self.out_queue = queue
		self.inandout = ioObj
		self.model = model
		
		self.seen_chunks = []

		self.running = True
		threading.Thread.__init__(self)
	
	def run(self):
		while self.running:
			relay = True
			
			element = self.out_queue.get()
			#TIMING
			#start_t = time.time()
			
			# sleep here if the packet is a relay packet, this prevents corruption by a 
			#	node in between two machines that are in range.  
			#	TODO: This value needs to be modified and played with.  
			if element[1] is True:
				time.sleep(0.01)
			packet = element[0]
			
			if DEBUG:
				print "CypherText: " + binascii.hexlify(packet)
				blocks, = struct.unpack("H", packet[0:2])
				print "size: " + str(blocks)
			
			
			while ( len(packet) != 0 ):
				entry = self.model.getEntryFrom(self.model.type_ranges)
				try:
					outpacket = entry[2].makePacket(packet[:entry[3]])
					if DEBUG:
						print "Sending with: %s" % self.model.rawToType(entry[0])
						print "length: " + str(len(outpacket))
					
				except AttributeError:
					#TODO: WTF does this do?
					continue
				packet = packet[entry[3]:]
				self.inandout.sendPacket(outpacket)
			#TIMING
			#print "Send time: " + str(time.time() - start_t)
	def kill(self):
		self.running = False
		self.inandout.close()
########NEW FILE########
__FILENAME__ = config
CAPLENGTH = 3

CHANNEL = 8
IFACE = "wlan1"
MODULUS = 1.21
REMAINDER = 0.85
TIMEOUT = 1

DEBUG = False

########NEW FILE########
__FILENAME__ = SendRec
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#    bunny.py
#
#    Copyright 2013 W. Parker Thompson <w.parker.thompson@gmail.com>
#		
#    This file is part of Bunny.
#
#    Bunny is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    Bunny is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with Bunny.  If not, see <http://www.gnu.org/licenses/>.

import struct, os, time, pipes

import PyLorcon2
from pcapy import open_live

from config import *


class SendRec:
	"""
	
	Main IO functionality of bunny, using pcapy and lorcon to do send and receive.
	
	"""
	def __init__(self):		
		try:
			self.lorcon = PyLorcon2.Context(IFACE)
		except PyLorcon2.Lorcon2Exception as err:
			print "Error creating lorcon object: "
			print str(err)
			exit()
		
		try:
			self.lorcon.open_injmon()
		except PyLorcon2.Lorcon2Exception as err:
			print "Error while setting injection mode, are you root?"
			print str(err)
			exit()

		self.lorcon.set_channel(CHANNEL)
		
		# This needs an audit.
		os.system("ifconfig " + pipes.quote(IFACE) + " up")
		
		# Quick definitions for pcapy
		MAX_LEN      = 1514		# max size of packet to capture
		PROMISCUOUS  = 1		# promiscuous mode?
		READ_TIMEOUT = 0		# in milliseconds
		MAX_PKTS     = 1		# number of packets to capture; 0 => no limit
		
		try:
			self.pcapy = open_live(IFACE, MAX_LEN, PROMISCUOUS, READ_TIMEOUT)
		except PcapError as err:
			print "Error creating pcapy descriptor, try turning on the target interface or setting it to monitor mode"
			print str(err)
		
	def updateChan(self, channel):
		"""
		
		Updates the current channel
		
		"""
		self.lorcon.set_channel(channel)
	
	# These send/rec functions should be used in hidden / paranoid mode.
	def sendPacket(self, data):
		if data is not None:
			try:
				self.lorcon.send_bytes(data)
			except PyLorcon2.Lorcon2Exception as err:
				print "ERROR sending packet: "
				print str(err)
	def recPacket_timeout(self, fcs):
		"""
		return the raw packet if the mod/remain value is correct. 
		returns False upon a timeout
		
		"""
		start_t = time.time()
		while(time.time() - start_t < TIMEOUT):
			header, rawPack = self.pcapy.next()
			if rawPack is None:
				continue
			# H = unsigned short
			size = struct.unpack("<H", rawPack[2:4])
			size = int(size[0])
			
			# check if the radio tap header is from the interface face itself (loop backs)
			#  that '18' might need to change with different hardware and software drivers
			if size >= 18:
				rawPack = rawPack[size:]
				size = len(rawPack)
				# subtract the FCS to account for the radiotap header adding a CRC32
				if (round( (size - fcs) % MODULUS, 2) == REMAINDER):
					return rawPack
		else:
			return False
	
	def reloop(self):
		"""
		This exists only for testing purposes.
		To ensure proper packets are read properly and at a high enough rate. 
		"""
		count = 0
		packNum = 200
		startTime = time.time()
		for n in range(packNum):
			header, rawPack = self.pcapy.next()
			if rawPack is None:
				continue
			# H = unsigned short
			size = struct.unpack("<H", rawPack[2:4])
			size = int(size[0])
			
			# check if the radio tap header is from the interface face itself (loop backs)
			#  that '18' might need to change with different hardware and software drivers
			if size >= 18:
				rawPack = rawPack[size:]
				size = len(rawPack)
				# subtract the FCS to account for the radiotap header adding a CRC32
				if (round( (size - 4) % MODULUS, 2) == REMAINDER):
					print "pack num: %d, " % n  
		endTime = time.time()
		totalTime = endTime - startTime
		packPerSec = packNum / totalTime
		print "Total Packets (p/s): %s" % packPerSec

	def recvRaw(self):
		""" Returns packet	
		
		RadioTap headers included
		
		"""
		header, rawPack = self.pcapy.next()
		return rawPack

	def close(self):
		self.lorcon.close()
		
########NEW FILE########
__FILENAME__ = Templates
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#    bunny.py
#
#    Copyright 2013 W. Parker Thompson <w.parker.thompson@gmail.com>
#		
#    This file is part of Bunny.
#
#    Bunny is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    Bunny is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with Bunny.  If not, see <http://www.gnu.org/licenses/>.

import struct, random, os

from config import *

class Templates:
	"""
	
	Contains templates for all packet types used by bunny.
	
	"""
	class Beacon:
		"""
		
		Template for Beacon packet types.  Initialize the template with a raw packet dump 
		of a beacon packet.
		
		"""
		# declares the number of bytes of communication this template can hold for a single injection
		injectable = 0
		
		type = ""
		frame_control = ""
		duration = ""
		BSSID = ""
		SA = ""
		DA = ""
		sequence_num = ""
		QOS = ""
		
		timestamp = ""
		beacon_interval = ""
		capability = ""
		
		# an array for taged fields 
		# tag [tagID, length, value]
		tags = []
		
		# a list of vendors found
		vendors = []
		
		SSID = ""

		def __init__(self, packet):
			# For a speed up we could use the struct.unpack() method
			#self.type, self.frame_control, struct.unpack("", pack_data)
			self.type = packet[0:1]
			self.frame_control = packet[1:2]
			self.duration = packet[2:4]
			self.BSSID = packet[4:10]
			self.SA = packet[10:16]
			self.DA = packet[16:22]
			self.sequence_num = packet[22:24]
			#self.RS = packet[21:26]
			self.timestamp = packet[24:32]
			self.beacon_interval = packet[32:34]
			self.capability = packet[34:36]
			
			packet = packet[36:]
			
			# Simple command to debug the current var's of this object.
			# print self.__dict__.keys()
			
			# loop through the tags and SAP them off into in the tags array
			# also appends any vendor OUI's into the vendors list.
			
			# this might be the place we have an error with comp to comp sending.
			# due to the fact it tries read past the end of the.
			while (len(packet) >= 4):
				id = packet[:1]
				length, = struct.unpack("B", packet[1:2])
				value = packet[2:length+2]
				self.tags.append([id, length, value])
				if id == "\xdd":
					self.vendors.append([value[:3]])
				packet = packet[length + 2:]
				
			#self.SSID = self.tagGrabber("\x00")
			
			# design problem here, after attempting dynamic lengths for the injection
			# fields I relized that for interconnectivity between clients I need to hardcode
			# injection lengths.  So the vendor tag is 24 bytes of data:
			self.injectable = 26 + 2
			
		def makePacket(self, inject_data):
			"""
			
			Creates and returns a beacon packet from the inject_data input
			inject_data must be of length Beacon.injectable
			
			injectable fields are:
			capabilities, 2nd to last vendor tags.
			
			NOTE: sequence_num had to be removed due to an issue with the AR9271 firmware, see:
				https://github.com/qca/open-ath9k-htc-firmware/issues/16
			
			"""
			# timestamp needs more testing.
			outbound = self.type + self.frame_control + self.duration + self.BSSID + self.SA + self.DA + self.sequence_num + self.timestamp + self.beacon_interval + inject_data[0:2]
			
			for i in range(0, len(self.tags)-2):
				outbound = outbound + self.tags[i][0] + struct.pack("<B", self.tags[i][1]) + self.tags[i][2]
			outbound = outbound + "\xdd" + struct.pack("<B", len(inject_data[2:])) + inject_data[2:]
			#outbound += struct.pack("!i", zlib.crc32(outbound))
			
			outbound = self.resize(outbound)
			#print "len of injectedBEACON: %d" % len(inject_data)
			return outbound
		def resize(self, outpack):
			"""
			
			Resizes the packet with the proper mod / REMAINDER value
			
			Primarly uses last vendor tag.
			
			"""
			# counter will be the size of the tag
			# using \xdd for vendor tag.
			#print self.vendors
			if len(self.vendors) > 0:
				tag = ["\xdd", 0, self.vendors[random.randrange(0, len(self.vendors))][0]]
			else:
				tag = ["\xdd", 0, ""]
			
			#while( round((len(outpack) + tag[1] + 2 + RADIOTAPLEN) % MODULUS, 2) != REMAINDER):
			while( round((len(outpack) + tag[1] + 2) % MODULUS, 2) != REMAINDER):
				tag[2] = tag[2] + os.urandom(1)
				tag[1] = len(tag[2])
			
			# + 4 if for eating the checksum that for w/e reason gets parsed as a tag.	
			outpack = outpack + tag[0] + struct.pack("B", tag[1]+4) + tag[2]
			
			return outpack
		
		def decode(self, input):
			
			# sequence num
			#output = input[22:24]
			
			# capabilities.
			output = input[34:36]
			
			temp_tags = []
			input = input[36:]
			data_size = len(input)
			
			# protect from non-Bunny packets
			if data_size < 4:
				return False
				
			# loop through and grab the second to last vendor tag
			while (len(input) >= 4):
				id = input[:1]
				length, = struct.unpack("B", input[1:2])
				value = input[2:length+2]
				temp_tags.append([id, length, value])
				input = input[length + 2:]
			
			value_chunk = temp_tags[len(temp_tags) - 2][2]
			
			# Fail design:
			#if value_chunk == self.tags[len(self.tags)-2]:
			#	return False
			
			#if DEBUG:
			#	print "Value_chuck: " + binascii.hexlify(value_chunk)
			output = output + value_chunk
			
			return output
			
		def tagGrabber(self, id):
			"""
			
			return the whole tag from an array of tags by its tag id
			
			"""
			for entry in self.tags:
				if (entry[0] == id):
					return entry
	class DataQOS:
		"""
		
		Template to hold a example Data packet type, currently we only support simple LLC
		packets for injection, encrypted data needs to be included.
		
		"""
		injectable = 0
		
		# 802.11
		type = ""
		frame_control = ""
		duration = ""
		BSSID = ""
		SA = ""
		DA = ""
		sequence_num = ""
		QOS = ""
		crypto = ""
		
		# LLC
		
		
		def __init__(self, packet):
			# For a speed up we could use the struct.unpack() method
			# self.type, self.frame_control, struct.unpack("", packet)
			self.type = packet[0:1]
			self.frame_control = packet[1:2]
			self.duration = packet[2:4]
			self.BSSID = packet[4:10]
			self.SA = packet[10:16]
			self.DA = packet[16:22]
			self.sequence_num = packet[22:24]
			self.QOS = packet[24:26]
			self.databody = packet[26:]
			
			# TODO: dynamic lengths of injectable data. randomly?
			# Temp size is 40 bytes
			self.injectable = 40
			
		def makePacket(self, inject_data):
			"""
			
			Make a QOS data packet with injected data, fields are: Sequence num and databody
			
			"""
			outbound = self.type + self.frame_control + self.duration+ self.BSSID + self.SA + self.DA + self.sequence_num + self.QOS
			
			outbound = outbound + struct.pack("B", len(inject_data)) + inject_data
			
			outbound = self.resize(outbound)
			return outbound
			
		def resize(self, outpack):
			
			while(round( (len(outpack)) % MODULUS, 2) != REMAINDER):
				outpack = outpack + os.urandom(1)
			return outpack
			
		def decode(self, input):
			
			# If the packet is not 27 bytes long it does not have any data in it. return false
			if len(input) < 27:
				return False
			
			# read the databody up to the size of the byte of length
			size, = struct.unpack("B", input[26:27])
			output = input[27:size+27]
			return  output		
	class ProbeRequest:
		"""
		
		ProbeRequst packet type template, injectable fields are sequence number and SSID.
		
		"""
		injectable = 0
		tags = []
		vendors = []
		
		type = ""
		frame_control = ""
		duration = ""
		BSSID = ""
		SA = ""
		DA = ""
		sequence_num = ""
		
		def __init__(self, packet):
			# For a speed up we could use the struct.unpack() method
			# self.type, self.frame_control, struct.unpack("", packet)
			self.type = packet[0:1]
			self.frame_control = packet[1:2]
			self.duration = packet[2:4]
			self.DA = packet[4:10]
			self.SA = packet[10:16]
			self.BSSID = packet[16:22]
			self.sequence_num = packet[22:24]
			
			packet = packet[24:]
			
			while (len(packet) >= 4):
				id = packet[:1]
				length, = struct.unpack("B", packet[1:2])
				value = packet[2:length+2]
				self.tags.append([id, length, value])
				if id == "\xdd":
					self.vendors.append([value[:3]])
				packet = packet[length + 2:]
			
			# in the event there is zero vendor tags, make one up.
			if len(self.vendors) == 0:
				self.vendors.append([os.urandom(3)])
			
			# ProbeRequests get the data injected into the ssid's
			# and are resized by a vendor tag, default SSID length is 12, again 
			# possibly signatureable.
			self.injectable = 12
			
		def makePacket(self, inject_data):
			"""
			
			Creates a packet with injected encrypted data.
			
			"""
			
			outbound = self.type + self.frame_control + self.duration + self.DA + self.SA + self.BSSID + self.sequence_num
			outbound = outbound + "\x00" + struct.pack("<B", len(inject_data)) + inject_data 
			for i in range(1, len(self.tags)-1):
				outbound = outbound + self.tags[i][0] + struct.pack("<B", self.tags[i][1]) + self.tags[i][2]

			return self.resize(outbound)
		def resize(self, outpack):
			"""
			
			Resizes the packet with the proper mod / REMAINDER value
			Uses last vendor tag.
			
			"""
			# counter will be the size of the tag
			# using \xdd for vendor tag.
			tag = ["\xdd", 0, self.vendors[-1][0]]
			
			while( round( (len(outpack) + tag[1] + 2) % MODULUS, 2) != REMAINDER):
				tag[2] = tag[2] + os.urandom(1)
				tag[1] = len(tag[2])
			outpack = outpack + tag[0] + struct.pack("<B", tag[1]) + tag[2]
			return outpack
		
		def decode(self, input):
			"""
			
			Decodes the encrypted data out of the inputed packet
			
			"""
			
			# sequence_num
			#output = input[22:24]
			temp_tags = []
			
			input = input[24:]
			data_size = len(input)
			
			# This should protect from non-Bunny probe requests being decoded
			if data_size < 4:
				return False
			while (len(input) >= 4):
				id = input[:1]
				length, = struct.unpack("B", input[1:2])
				value = input[2:length+2]
				temp_tags.append([id, length, value])
				input = input[length + 2:]
			return temp_tags[0][2]
			
		def tagGrabber(self, id):
			"""
			
			return the whole tag from an array of tags by its tag id
			
			"""
			for entry in self.tags:
				if (entry[0] == id):
					return entry
					

########NEW FILE########
__FILENAME__ = TrafficModel
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#    bunny.py
#
#    Copyright 2013 W. Parker Thompson <w.parker.thompson@gmail.com>
#		
#    This file is part of Bunny.
#
#    Bunny is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    Bunny is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with Bunny.  If not, see <http://www.gnu.org/licenses/>.

import time, struct, operator, binascii, random

# This is indicative of object reuse. 
from SendRec import *
from Templates import *

class TrafficModel():
	"""
	
	Builds a model of current traffic that can be used at a later time to make packets.
	
	"""
	# In network byte order
	# If you do a lookup on this table and dont find a match it is probly
	# a 'reserved' type.
	Dot11_Types = {
		# management
		"assocReq": "\x00",
		"assocRes": "\x10",
		"reAssocReq": "\x20",
		"reAssocRes": "\x30",
		"probeReq": "\x40",
		"probeRes": "\x50",
		"beacon": "\x80",
		"ATIM": "\x90",
		"disAssoc": "\xa0",
		"auth": "\xb0",
		"deAuth": "\xc0",
		"action": "\xd0",

		# control
		"blockAckReq": "\x81",
		"blockAck": "\x91",
		"PSPoll": "\xa1",
		"RTS": "\xb1",
		"CTS": "\xc1",
		"ACK": "\xd1",
		"ACK2": "\xd4",
		"CFend": "\xe1",
		"CFendCFack": "\xf1",

		# data
		"data": "\x02",
		"data-CFAck": "\x12",
		"data-CFPoll": "\x22",
		"data-CFAckPoll": "\x32",
		"dataNULL": "\x42",
		"dataNULLfunc": "\x48",
		"data-CFAckNULL": "\x52",
		"data-CFPollNULL": "\x62",
		"data-CFAckPollNULL": "\x72",
		"dataQOS": "\x82",
		"dataQOS2": "\x88",
		"dataQOS-CFAck": "\x92",
		"dataQOS-CFPoll": "\xa2",
		"dataQOS-CFAckPoll": "\xb2",
		"dataQOSNULL": "\x82",  # wtf why?
		"dataQOS-CFPollNULL": "\xe2",
		"dataQOS-CFAckPollNULL": "\xf2",
	}
	
	# Model attributes:
	# -Type ranges
	# -MAC addresses
	# -
	# raw packets
	data = []
	
	# [type, freq, template, injectlen]
	type_ranges = []
	
	# [addr, freq, AP(bool)]
	mac_addresses = []
	
	# FCS is the number of bytes for the Checksum if it is found in stripRadioTap()
	FCS = 0
	
	def __init__(self):
		"""
		
		Starts up the model, collects data and inserts it into its respective lists
		
		"""
		# clear any old data
		self.mac_addresses = []
		self.type_ranges = []
		self.data = []
		
		# spin up and build the model
		self.interface = SendRec()
		self.collectData()
		self.stripRadioTap()
		self.extractModel()
		self.insertTemplates()
			
	def collectData(self):
		"""
		
		Collect packets for the pre determined amount of time.
		
		"""
		start_time = time.time()
		current_time = start_time
		
		# caplength is a glocal var from config.
		while ( (current_time - start_time) < CAPLENGTH):
			packet = self.interface.recvRaw()
			self.data.append(packet)
			current_time = time.time()
	
	def stripRadioTap(self):
		"""
		Strips the RadioTap header info out of the packets are replaces the data 
		list with the new packets.
		
		It also checks if this hardware has FCS (Frame Check sums's) at the end
		"""
		temp_data = []
		
		# Check for FCS flag in the radiotap header
		flags = self.data[0][4:8]
		flags = struct.unpack("i", flags)[0]

		#	  bval         idx 
		if ((flags & (1 << 0)) != 0):
			subflags = self.data[0][16:17]
			subflags = struct.unpack("B", subflags)[0]
		else:
			subflags = self.data[0][8:9]
			subflags = struct.unpack("B", subflags)[0]
		
		if ((flags & (1 << 1)) != 0):
			if ((subflags & (1 << 4)) != 0):
				self.FCS = 4
		
		if DEBUG:
			print "FCS: %s" % (self.FCS)
		#  now strip the headers.
		for packet in self.data:
			sizeHead = struct.unpack("<H", packet[2:4])
			temp_data.append(packet[sizeHead[0]:])
		self.data = temp_data
	
	def rawToType(self, type_raw):
		"""
		
		input the byte and return a string of the 802.11 type
		
		"""
		for k,v in self.Dot11_Types.iteritems():
			if (v == type_raw[0]):
				return k
		return "reserved (" + binascii.hexlify(type_raw[0]) + ")"
	
	def buildModelTypes(self, graphs):
		"""
		
		Adds the extracted types and %'s to the model
		
		"""
		count = 0.0
		for type in graphs:
			count += type[1]
		for type in graphs:
			type[1] = (type[1] / count)
			self.type_ranges.append(type)
					
	def buildModelAddresses(self, addresses):
		""""
		
		Adds the extracted addresses and %'s to the model
		
		"""
		count = 0.0
		for addr in addresses:
			count += addr[1]
		for addr in addresses:
			addr[1] = (addr[1] / count)
			self.mac_addresses.append(addr)
			
	def extractModel(self):
		"""
		
		Loops through all collected packets and creates different aspects of the model
		
		"""
		graphs = []
		addresses = []
	
		# loop through all packets, then loop through all types,
		# append if the type is not found,
		# inrement count if it is.
		for packet in self.data:
			beacon = False
			
			# graphs[type, count]
			type = packet[:1]
			
			# check if its a beacon packet
			if(type == self.Dot11_Types['beacon']):
				beacon = True
			found = False
			for types in graphs:
				if (type == types[0]):
					types[1] = types[1] + 1
					found = True
			if(found == False):
				graphs.append([type, 1, packet, 0])
			
			
			# addresses[addr, count, AP?]
			# model common mac addresses used
			mac = packet[10:15]
			
			found = False
			for addr in addresses:
				if (mac == addr[0]):
					addr[1] = addr[1] + 1
					found = True
			if(found == False):
				if (beacon == True):
					addresses.append([mac, 1, True])
				else:
					addresses.append([mac, 1, False])
		
		# sort by count		
		graphs.sort(key=operator.itemgetter(1), reverse=True)
		addresses.sort(key=operator.itemgetter(1), reverse=True)
		
		self.buildModelTypes(graphs)
		self.buildModelAddresses(addresses)
		
	def insertTemplates(self):
		"""
		
		loops through the type_ranges list and replaces the raw packet data with template objects
		type_ranges becomes:
		[type, freq, templateObject, injectLen]
		
		"""
		for entry in self.type_ranges:
			if entry[0] is None:
				continue
			type = self.rawToType(entry[0])
			if (type == "beacon"):
				# replace raw data with object of template type, then append the injection length
				entry[2] = Templates.Beacon(entry[2])
				entry[3] = entry[2].injectable
			elif (type == "data" or type == "dataQOS" or type == "dataQOS2"):
				entry[2] = Templates.DataQOS(entry[2])
				entry[3] = entry[2].injectable
			elif (type == "probeReq"):
				entry[2] = Templates.ProbeRequest(entry[2])
				entry[3] = entry[2].injectable
			# add more
	def insertNewTemplate(self, raw_packet):
		"""
		
		This is a copy past of the insertTemplate() func but does not loop through, instead
		a raw_packet is passed in as an argument then, then this function finds its type and inserts
		it, if an corresponding Template exists
		
		returns false if the packet type does not have a template
		returns the entry in type_ranges[] if found
		
		TODO: Currently only lets this bunny instance READ 
		with this packet type because there is zero frequency.
		"""
		entry = [0, 0, 0, 0]
		
		raw_type = raw_packet[:1]
		type = self.rawToType(raw_type)
		
		if (type == "beacon"):
			# replace raw data with object of template type, then append the injection length
			entry[0] = raw_type
			entry[2] = Templates.Beacon(raw_packet)
			entry[3] = entry[2].injectable
		elif (type == "data" or type == "dataQOS" or type == "dataQOS2"):
			entry[0] = raw_type
			entry[2] = Templates.DataQOS(raw_packet)
			entry[3] = entry[2].injectable
		elif (type == "probeReq"):
			entry[0] = raw_type
			entry[2] = Templates.ProbeRequest(raw_packet)
			entry[3] = entry[2].injectable
		else:
			entry = False
		
		return entry
		
	# debugging:
	def printTypes(self):
		"""
		
		Prints out a list of the packet types and percentages in the model
		
		"""
		print "%-15s%s" % ("Type", "Percent")
		print "-" * 20
		for entry in self.type_ranges:
			print "%-15s%f" % (self.rawToType(entry[0]), entry[1])

	def printTypesWithPackets(self):
		"""
		
		Prints out a list of the packet types and percentages in the model
		
		"""
		print "%-15s%-10s%s" % ("Type", "Percent", "Template")
		print "-" * 30
		for entry in self.type_ranges:
			print "%-15s%-10f%s" % (self.rawToType(entry[0]), entry[1], binascii.hexlify(entry[2]))

	def printMacs(self):
		"""
		
		Prints out a list of src mac address and percentages in the model
		
		"""
		print "\n%-15s%-10s%s" % ("Addr", "Percent", "AP")
		print "-" * 30
		for entry in self.mac_addresses:
			print "%-15s%-10f%s" % (binascii.hexlify(entry[0]), entry[1], entry[2])

	def getEntryFrom(self, array):
		"""
		
		Returns a frequency adjusted random entry from an array such as type_ranges
		Follows the [name, freq, ...] structure.
		
		"""
		num = random.random()
		count = 0.0
		for entry in array:
			count += entry[1] 
			if count > num:
				break
		return entry

########NEW FILE########
__FILENAME__ = drivers
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#    bunny.py
#
#    Copyright 2013 W. Parker Thompson <w.parker.thompson@gmail.com>
#		
#    This file is part of Bunny.
#
#    Bunny is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    Bunny is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with Bunny.  If not, see <http://www.gnu.org/licenses/>.

import pylorcon

cards = pylorcon.getcardlist()

# ebay search string:
#	Without Alpha:
# 	("AWLL3026", "NT-WGHU", "WUSB54GC", Netgear WG111, "Asus WL-167g v2", "Digitus DN-7003GS", "D-Link DWL-G122", "D-Link WUA-1340", "Hawking HWUG1", "Linksys WUSB54G v4")
#
#	With Alpha:
#	("Alfa AWUS036E", "Alfa AWUS036H", "Alfa AWUS036S", "Alfa AWUS050NH", "Asus WL-167g v2", "Digitus DN-7003GS", "D-Link DWL-G122", "D-Link WUA-1340", "Hawking HWUG1", "Linksys WUSB54G v4")
#
# always cross ref with: http://www.aircrack-ng.org/doku.php?id=compatibility_drivers

for card in cards:
	print card['name']


########NEW FILE########
__FILENAME__ = mod
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#    bunny.py
#
#    Copyright 2013 W. Parker Thompson <w.parker.thompson@gmail.com>
#		
#    This file is part of Bunny.
#
#    Bunny is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    Bunny is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with Bunny.  If not, see <http://www.gnu.org/licenses/>.

import sys
mod = 1.23
remain = 0.82

if len(sys.argv) > 2:
	mod = float(sys.argv[1])
	remain = float(sys.argv[2])

print ("Mod:\t%f" % mod)
print ("Remain:\t%f" % remain)

for i in range(1, 400):
	if round( i % mod, 2) == remain:
		print i

########NEW FILE########
__FILENAME__ = readpck
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#    bunny.py
#
#    Copyright 2013 W. Parker Thompson <w.parker.thompson@gmail.com>
#		
#    This file is part of Bunny.
#
#    Bunny is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    Bunny is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with Bunny.  If not, see <http://www.gnu.org/licenses/>.

import binascii
import struct
import time

from pcapy import open_live

IFACE = "wlan2"
MAX_LEN      = 1514		# max size of packet to capture
PROMISCUOUS  = 1		# promiscuous mode?
READ_TIMEOUT = 0		# in milliseconds
MAX_PKTS     = 1		# number of packets to capture; 0 => no limit
try:
	pcapy = open_live(IFACE, MAX_LEN, PROMISCUOUS, READ_TIMEOUT)
except:
	print "Error creating pcapy descriptor, try turning on the target interface or setting it to monitor mode"

cnt = 0

start_t = time.time()
while(time.time() - start_t < 5):
	header, rawPack = pcapy.next()
	# H = unsigned short
	size = struct.unpack("<H", rawPack[2:4])
	size = int(size[0])
	
	# check if the radio tap header is from the interface face itself (loop backs)
	#  that '18' might need to change with different hardware and software drivers
	if size >= 18:
		rawPack = rawPack[size:]
		size = len(rawPack)
		# subtract the FCS to account for the radiotap header adding a CRC32
		if (round( (size - 4) % 1.21, 2) == 0.85):
			#print "got packet"
			cnt = cnt + 1
	
print cnt

########NEW FILE########
__FILENAME__ = simplesend
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#    bunny.py
#
#    Copyright 2013 W. Parker Thompson <w.parker.thompson@gmail.com>
#		
#    This file is part of Bunny.
#
#    Bunny is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    Bunny is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with Bunny.  If not, see <http://www.gnu.org/licenses/>.
import sys
import pylorcon

try:
	lorcon = pylorcon.Lorcon("wlan4", "rt2800usb")
except pylorcon.LorconError:
	print "Please run me as root"
	
lorcon.setfunctionalmode("INJECT");
lorcon.setmode("MONITOR");
lorcon.setchannel(11);

packet = "A" * 1400
for a in range(1, 200):
	lorcon.txpacket(packet);

########NEW FILE########
