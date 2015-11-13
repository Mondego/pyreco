__FILENAME__ = mongol
#!/usr/bin/env python

import socket
import logging
import sys, getopt, time

logging.getLogger("scapy.runtime").setLevel(logging.ERROR)
from scapy.all import *

# a few silly globals
debug = True
MESSAGE = "GET %s HTTP/1.1" + "\x0d\x0a" + "Host: %s" + "\x0d\x0a\x0d\x0a"
port = 80
inputfile = ""
outputfile = "output.txt"


def usage():
	print "Mongol.py -- a tool for pin pointing the ip addresses\n\t of the great firewall of china keyword blocking devices"
	print ""
	print "usage: python mongol.py -i hostslist.txt -o outputfilename.txt"
	print "-i: required newline seperated list of hosts to scan"

# Basically a slightly modified traceroute
def ackattack(host):
        port = RandNum(1024,65535)

	# build a simple ACK packet, using a range (1,255) for the ttl creates 255 packets
        ack = IP(dst=host, ttl=(1,255))/TCP(sport=port, dport=80, flags="A")
        
	# send packets and collect answers
	ans,unans = sr(ack, timeout=4, verbose=1)

	iplist = []
	retdata = ""
        for snd,rcv in ans:
		#print rcv.summary()
                endpoint = isinstance(rcv.payload, TCP)
                #retdata += "%s %s %s\n" % (snd.ttl,rcv.src,endpoint)
		retdata += "%s\n" % (rcv.src)
                iplist.append(rcv.src)

		if endpoint:
                        break
	
	return retdata, iplist


# parse arguments
try:
	opts, args = getopt.getopt(sys.argv[1:],"hi:o:")
except getopt.GetoptError:
	usage()
	sys.exit(1)
for opt, arg in opts:
	if opt == "-h":
		usage()
		sys.exit(0)
	elif opt == "-i":
		inputfile = arg
	elif opt == "-o":
		outputfile = arg

# read the hostnames in from the intputfile
if not inputfile:
	usage()
	print "ERROR: Please select an input file of hostnames, one hostname per line"
	sys.exit(1)

hostnames = []
fd = open(inputfile, "r")
hosts = fd.readlines()
for addr in hosts:
	hostnames.append(addr.rstrip("\n"))

# empty list of found firewalls
firewalls = []

for host in hostnames:
	# first we create a real handshake and send the censored term
	s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	
	# why 5 seconds?  idk you got a better idea?
	s.settimeout(5)

	# make sure we can resolve the host
	try:
		ipaddr = socket.gethostbyname(host)
	except socket.gaierror:
		print "Could not resolve " + host
		continue

	# make sure the host is up
	try:
		s.connect((ipaddr, port))
	except socket.timeout:
		print "connection to " + host + " has timed out moving on"
		continue 
	except socket.error:
		print "connection failed, moving on"
		continue
	s.send(MESSAGE % ("/", host))
	
	try:
		response = s.recv(1024)
	except socket.timeout:
		print "connection to " + host + " has timedout moving on, Possibly not a webserver"
		continue
	except socket.error:
		print "RST: Possibly already blocked"
		continue

	s.close()

	# TODO: implement other valid response codes, this is a hack.
	if response.find("200 OK") != -1 or response.find("302 Redirect") != -1 or response.find("401 Unauthorized") != -1:

		# get a non firewalled ACK trace.
		noFWprint, noFWlist = ackattack(ipaddr)

		# http://en.wikipedia.org/wiki/List_of_blacklisted_keywords_in_the_People%27s_Republic_of_China
                # tibetalk
		print "Sending stimulus"				
		s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		s.settimeout(5)

		try:
 	               s.connect((ipaddr, port))
 	        except socket.timeout:
         	       	print "connection to " + host + " has timedout moving on"
			continue
		except socket.error:
			print "connection to " + host + " has timedout moving on"
                        continue

		s.send(MESSAGE % ("/tibetalk", host) )

		# possibly a delay from the IDS to reaction time
		time.sleep(3)
		try:
			response = s.recv(1024)

		except socket.error:
			print "Found a filter\n\n"

			# get a firewalled trace
			FWprint, FWlist = ackattack(ipaddr)

			if debug:
				print "\n\nIPADDR: " + ipaddr
				print "Without FW:"
				print noFWprint
				print "\n\nWith FW:"
                		print FWprint
			
			filterIP = FWlist[-2]
			# we only check the first 3 octecs because of variation in the routers depending on
			# firewall status
			# fuck regex's
			shortip = filterIP.split(".")
			shortip = "%s.%s.%s." % (shortip[0], shortip[1], shortip[2])
			print "shortip: " + shortip

			# add the firewall's IP to the list to be written out if it does not already exist
			if filterIP not in firewalls:
				firewalls.append(filterIP)

			if shortip in noFWlist:
				hopsdiff = noFWlist.index(filterIP) - FWlist.index(filterIP)
				print "Guess: " + filterIP
				print "IP block: " + shortip
				print "Hops diff:    " + str(hopsdiff)
			else:
				print "Guess: " + filterIP

		else:
			print "Appears not to be blocking"

	else:
		print "Bad response code from " + host
		#print response
		continue
	s.close()

# output the ip's to a file.
fd = open(outputfile, "w")
for ip in firewalls:
	fd.write(ip + "\n")
fd.close()

########NEW FILE########
