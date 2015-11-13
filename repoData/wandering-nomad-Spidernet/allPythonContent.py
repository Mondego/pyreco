__FILENAME__ = core
#!usr/bin/env python
################################################
# SpiderNet 
#  By Wandering-Nomad (@wand3ringn0mad)
################################################
#
# This tool for educational uses only.  This  
#  code should not be used for systems that one
#  does not have authorization for.  All 
#  modification / rebranding / public use 
#  requires the authors concent 
#                                               
################################################


import os
import sys

from lib.server import *

active_hosts = []

def start_spidernet():
	while True:
		menu()
	

def read_host_file():
	try:
		if (  os.path.exists('hostlist' ) ): 
			with open( 'hostlist' ) as handle_host_file:
			    return handle_host_file.readlines()
		else:
			sys.exit(" [X] Put Host List in hostlist")
	except IOError:
		sys.exit(" [X] Put Host List in hostlist")

	
def parse_host_file(host_file_handle):
	for host_row in host_file_handle:
		if host_row[0] != "#":
			hostname, port, user, password = host_row.rstrip().split(":")
			connect_hosts(hostname, port, user, password)


def connect_hosts(hostname, port, user, password):
	tmp_server = server(hostname, port, user, password)
	result_status = tmp_server.connect_host()

	if (result_status != 1):
		active_hosts.append(tmp_server)

def menu():
	for num, desc in enumerate(["Connect Hosts", "Update Hosts", "List Hosts", "Host Details", "Run Command", "Open Shell", "Exit"]):
		print "[" + str(num) + "] " + desc

	while True:
		raw_choice = raw_input("#> ")
		if raw_choice.isdigit():
			choice = int(raw_choice)
			break
	print "-----------------------------------"

	if choice == 0:
		parse_host_file(read_host_file())
		print "----------Active Hosts-------------"
		for host in active_hosts:
			host.details()
		print "-----------------------------------"
	elif choice == 1:
		print "----------Clearing Hosts-----------"
		active_hosts[:] = []
		parse_host_file(read_host_file())
		print "----------Active Hosts-------------"
		for host in active_hosts:
			host.details()
		print "-----------------------------------"
	elif choice == 2:
		print "----------Active Hosts-------------"
		for host in active_hosts:
			host.details()		
		print "-----------------------------------"
	elif choice == 3:
		print "----------Hosts Details------------"
		for host in active_hosts:
			host.fulldetails()		
		print "-----------------------------------"
						
	elif choice == 4:
		cmd = raw_input("Command: ")
		for host in active_hosts:
			print "%s : %s" % (host.hostname, host.execute_command(cmd) )

		print "-----------------------------------"	
		
	elif choice == 5:
		for num, host in enumerate(active_hosts):
			print "[%s] %s (%s)" % ( str(num), host.hostname, host.execute_command("ifconfig eth0 | grep 'inet addr' | awk '{ print $2 }' | sed 's/addr://'" ) )

		while True:
			raw_cmd = raw_input("Host: ")
			if raw_cmd.isdigit():
				cmd = int(raw_cmd)
				break
				
		active_hosts[int(cmd)].shell()

		print "-----------------------------------"	
				
	elif choice == 6:
		for host in active_hosts:
			host.shutdown()

		sys.exit(0)	
		
		
		
			
	return;		
########NEW FILE########
__FILENAME__ = interactive
# Copyright (C) 2003-2007  Robey Pointer <robeypointer@gmail.com>
#
# This file is part of paramiko.
#
# Paramiko is free software; you can redistribute it and/or modify it under the
# terms of the GNU Lesser General Public License as published by the Free
# Software Foundation; either version 2.1 of the License, or (at your option)
# any later version.
#
# Paramiko is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
# A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with Paramiko; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA.


import socket
import sys

# windows does not have termios...
try:
    import termios
    import tty
    has_termios = True
except ImportError:
    has_termios = False


def interactive_shell(chan):
    if has_termios:
        posix_shell(chan)
    else:
        windows_shell(chan)


def posix_shell(chan):
    import select
    
    oldtty = termios.tcgetattr(sys.stdin)
    try:
        tty.setraw(sys.stdin.fileno())
        tty.setcbreak(sys.stdin.fileno())
        chan.settimeout(0.0)

        while True:
            r, w, e = select.select([chan, sys.stdin], [], [])
            if chan in r:
                try:
                    x = chan.recv(1024)
                    if len(x) == 0:
                        print '\r\n*** EOF\r\n',
                        break
                    sys.stdout.write(x)
                    sys.stdout.flush()
                except socket.timeout:
                    pass
            if sys.stdin in r:
                x = sys.stdin.read(1)
                if len(x) == 0:
                    break
                chan.send(x)

    finally:
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, oldtty)

    
# thanks to Mike Looijmans for this code
def windows_shell(chan):
    import threading

    sys.stdout.write("Line-buffered terminal emulation. Press F6 or ^Z to send EOF.\r\n\r\n")
        
    def writeall(sock):
        while True:
            data = sock.recv(256)
            if not data:
                sys.stdout.write('\r\n*** EOF ***\r\n\r\n')
                sys.stdout.flush()
                break
            sys.stdout.write(data)
            sys.stdout.flush()
        
    writer = threading.Thread(target=writeall, args=(chan,))
    writer.start()
        
    try:
        while True:
            d = sys.stdin.read(1)
            if not d:
                break
            chan.send(d)
    except EOFError:
        pass


########NEW FILE########
__FILENAME__ = server
#!usr/bin/env python
################################################
# SpiderNet 
#  By Wandering-Nomad (@wand3ringn0mad)
################################################
#
# This tool for educational uses only.  This  
#  code should not be used for systems that one
#  does not have authorization for.  All 
#  modification / rebranding / public use 
#  requires the authors concent 
#                                               
################################################

import paramiko
import interactive
import socket
import os

class server(object):
	def __init__(self, hostname, port, username, password):
		self.active = False
		self.hostname = hostname
		self.port = port
		self.username = username
		self.password = password
		self.connection_handle = ""

	def details(self):
		print "Host: %s:%s (%s/%s)" % (self.hostname, self.port, self.username, self.password)
		print "Active: %s" % self.active

	def fulldetails(self):
		print "[+] Host           : %s:%s (%s/%s)" % (self.hostname, self.port, self.username, self.password)
		print " - Active          : %s" % self.active
		print " - R - Hostname    : %s" % self.execute_command('hostname')
		print " - R - IP Address  : %s" % self.execute_command("ifconfig eth0 | grep 'inet addr' | awk '{ print $2 }' | sed 's/addr://'" )
		print " - R - User        : %s" % self.execute_command('whoami')
		print " - uname           : %s" % self.execute_command('uname -a')
		print " - uptime          :%s"  % self.execute_command('uptime')

		
	def connect_host(self):
		if self.active:
			print "[x] Server Already Active"
			return 1
		try:
			sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			sock.connect((self.hostname, int(self.port)))
		except Exception, e:
			print "[x] Failed to Connect to %s " % self.hostname
			return 1
		
		try:
			self.connection_handle = paramiko.Transport(sock)
			try:
				self.connection_handle.start_client()
			except paramiko.SSHException:
				print '[x]  %s  SSH negotiation failed.' % self.hostname
				return 1
			
			try:						
				keys = paramiko.util.load_host_keys('ssh_keys/known_hosts')
			except IOError:
				print '[x] Unable to open host keys file'
				keys = {}		
			key = self.connection_handle.get_remote_server_key()
			if not keys.has_key(self.hostname):
				print '[x] %s  WARNING: Unknown host key!' % self.hostname
			elif not keys[self.hostname].has_key(key.get_name()):
				print '[x] %s  WARNING: Unknown host key!' % self.hostname
			elif keys[self.hostname][key.get_name()] != key:
				print '[x] %s  WARNING: Host key has changed!!!' % self.hostname
				return 1

			try:
				key = paramiko.RSAKey.from_private_key_file('ssh_keys/id_rsa')
			except paramiko.PasswordRequiredException:
				password = getpass.getpass('RSA key password: ')
				key = paramiko.RSAKey.from_private_key_file('ssh_keys/id_rsa', password)
				
			self.connection_handle.auth_publickey(self.username, key)		
			
			if not self.connection_handle.is_authenticated():
				manual_auth(self.username, self.hostname)
			if not self.connection_handle.is_authenticated():
				print '[x]  Authentication failed. :('
				self.connection_handle.close()
				return 1		
			
			self.active = True
			return 0



			
		except Exception, e:
		    print '[x]  Caught exception: ' + str(e.__class__) + ': ' + str(e)
		    try:
		        self.connection_handle.close()
		    except:
		        pass
		    return 1			
			
			
	def execute_command(self,command):
		stdout_data = []
		stderr_data = []
		
		session = self.connection_handle.open_session()
		session.exec_command(command)

		while True:
			if session.recv_ready():
				stdout_data.append(session.recv(4096))
			if session.recv_stderr_ready():
				stderr_data.append(session.recv_stderr(4096))
			if session.exit_status_ready():
				break
			
		return ''.join(stdout_data).rstrip()

	def shell(self):
		if not self.active:
			print "[x] Server Already Active"
			return 1
		session = self.connection_handle.open_session()
		session.get_pty()
		session.invoke_shell()
		interactive.interactive_shell(session)
		session.close()

	def shutdown(self):
		if not self.active:
			print "[x] %s Server Not Active" % self.hostname
			return 1
		self.connection_handle.close()
		self.active = False
		print "[x] %s server shutdown" % self.hostname














########NEW FILE########
__FILENAME__ = spidernet
#!usr/bin/env python
################################################
# SpiderNet 
#  By Wandering-Nomad (@wand3ringn0mad)
################################################
#
# This tool for educational uses only.  This  
#  code should not be used for systems that one
#  does not have authorization for.  All 
#  modification / rebranding / public use 
#  requires the authors concent 
#                                               
################################################
#
# Original concept based on RaiderSec's "Building
#  an SSH Botnet C&C using Python and Fabric
# http://raidersec.blogspot.com/2013/07/building-ssh-botnet-c-using-python-and.html
#
################################################

from lib.core import *

def main():
	start_spidernet()
	
if __name__ == "__main__":
	main()     

########NEW FILE########
