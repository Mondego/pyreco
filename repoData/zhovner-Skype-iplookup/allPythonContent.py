__FILENAME__ = client
# -*- coding: utf-8 -*-
import socket
import os, os.path
import sys
import re
import time

#------------------------------------------------------------------------
# Put here path to debug log that is currently written by skypekit runtime
# you need run "skypekit -d logname" before edit this
# also you can parse log by youself like "tail -F /some/folder/logname | grep -a noticing" and use client.py only for send username into socket
PathToLog = "/some/folder/logname"


if len(sys.argv) == 1:
        print('Usage: python skyip.py <skypename>')
        sys.exit();

Username = sys.argv[1]

if os.path.exists( "/tmp/skype_iplookup" ):
	client = socket.socket( socket.AF_UNIX, socket.SOCK_DGRAM )
	client.connect( "/tmp/skype_iplookup" )
	client.send(Username)
	client.close()
	time.sleep(3)
	File = open(PathToLog,'rb').readlines()
	finds = []
	for matches in File:
		finded = re.findall('.*noticing.{0}.0.*-r(.*?)-l(.*?:[0-9]*?)[^0-9].*'.format(Username), matches)
		if len(finded)>0:
			finds.append('%s - %s'%(finded[0][0],finded[0][1]))
	finds = list(set(finds))
	for f in finds:
		print f
else:
  print "Can't connect to unix socket /tmp/skype_iplookup"

########NEW FILE########
__FILENAME__ = server
print('****************************************************************************');
print('Skype IP lookup deamon');
print('****************************************************************************');

# This deamon listen unix socket for username string and then make RefreshProfile() for username.
# If username online in Skypekit debug log will be string with IP adress.
# 
# Put this script in skypekit-sdk_runtime-3.7.0/examples/python/tutorial and run there.
#
# You will need to launch the SkypeKit runtime before running this deamon.



#----------------------------------------------------------------------------------
# Importing necessary libraries. Note that you will need to set the keyFileName value
# in the keypair.py file.

import sys;
import socket
import os, os.path
import time
import keypair;
import stat
from time import sleep;

sys.path.append(keypair.distroRoot + '/ipc/python');
sys.path.append(keypair.distroRoot + '/interfaces/skype/python');

try:
	import Skype;	
except ImportError:
  raise SystemExit('Program requires Skype and skypekit modules');

#----------------------------------------------------------------------------------
# Taking skypename and password arguments from command-line.

if len(sys.argv) != 3:
	print('Usage: python vcard_socket.py <skypename> <password>');
	sys.exit();

accountName = sys.argv[1];
accountPsw  = sys.argv[2];
loggedIn	= False;

#----------------------------------------------------------------------------------
# Creating our main Skype object

try:
	MySkype = Skype.GetSkype(keypair.keyFileName);	
	MySkype.Start();
except Exception:
	raise SystemExit('Unable to create Skype instance');

#----------------------------------------------------------------------------------
# Defining our own Account property change callback and assigning it to the
# Skype.Account class.

def AccountOnChange (self, property_name):
	global loggedIn;
	if property_name == 'status':
		if self.status == 'LOGGED_IN':
			loggedIn = True;
			print('Login complete.');

Skype.Account.OnPropertyChange = AccountOnChange;

#----------------------------------------------------------------------------------
# Defining our own Contact property change callback and assigning it to the
# SkyLib.Contact class.

def ContactOnPropertyChange(self, property_name):
	if property_name == 'availability':
		print('Online status event: ' + self.displayname + ' is now ' + self.availability);
		
Skype.Contact.OnPropertyChange = ContactOnPropertyChange;

#----------------------------------------------------------------------------------
# Retrieving account and logging in with it.

account = MySkype.GetAccount(accountName);

print('Logging in with ' + accountName);
account.LoginWithPassword(accountPsw, False, False);

while loggedIn == False:
	sleep(1);


#----------------------------------------------------------------------------------
# Unix socket start

if os.path.exists( "/tmp/skype_iplookup" ):
  os.remove( "/tmp/skype_iplookup" )

print "Opening socket..."

MySocket = socket.socket( socket.AF_UNIX, socket.SOCK_DGRAM )
MySocket.bind("/tmp/skype_iplookup")
os.chmod("/tmp/skype_iplookup", stat.S_IRWXU | stat.S_IRGRP | stat.S_IRWXO)

print "OK. Now listening..."

#----------------------------------------------------------------------------------
# Main cycle.
#

while True:
	MyUsername = MySocket.recv( 1024 )
	if not MyUsername:
	 break
	else:
	 print ('Looking for ' + MyUsername + '...')
	# Be aware, string will put in MySkype.GetContact(MyUsername).RefreshProfile() without any verification of input data
	# string with illegal characters and "echo123" can broke whole programm.
	 MySkype.GetContact(MyUsername).RefreshProfile()
	 print ('Maybe done.')
########NEW FILE########
