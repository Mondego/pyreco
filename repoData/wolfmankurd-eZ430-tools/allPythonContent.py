__FILENAME__ = eZ430
#!/usr/bin/env python
import serial

class watch():
        def __init__(self, dev = "/dev/ttyACM0", deb = 50):
                self.dev = dev
                self.deb = deb
		self.start()
	def start(self):
                self.conn = serial.Serial(self.dev, 115200, timeout = 1)
                self.write("\xFF\x07\x03")
	def stop(self):
		self.write("\xFF\x09\x03")
		self.conn.close()
        def write(self,msg):
                self.conn.write(msg)
        def read(self, len = 7):
                self.conn.write("\xFF\x08\x07\x00\x00\x00\x00")
                return self.conn.read(len)
        def debounce(self):
                i=self.deb
                while i:
                        self.read()
                        i-=1
	

########NEW FILE########
__FILENAME__ = mouse
#!/usr/bin/env python
import os, eZ430

watch = eZ430.watch()
print "Opening eZ430 on",watch.dev
if(os.system("xdotool --version")!=0):
	print "You need xdotool."
	os.exit(1)
while 1:
	data = watch.read(7)
	y=ord(data[0])
	x=ord(data[1])
	if(x*y != 0):
		x-=128
		y-=128
		x/=50
		y/=50
		os.system('xdotool mousemove_relative -- %s %s'%(x,y))

########NEW FILE########
__FILENAME__ = music_control
#!/usr/bin/env python
import eZ430, dbus, time, math
#Rhythmbox dbus
session_bus = dbus.SessionBus()
proxy_obj = session_bus.get_object('org.gnome.Rhythmbox', '/org/gnome/Rhythmbox/Player')
player = dbus.Interface(proxy_obj, 'org.gnome.Rhythmbox.Player')
#Wireless link init
watch = eZ430.watch()

#Variables
#link=0
#pd=0
r=0
l=0
down=0
up=0
playing=0
paused=0

downmillies=int(round(time.time()*1000))
upmillies=int(round(time.time()*1000))

x=0
y=0
z=0

#Gestures
def raised():
	print "Gesture detected!"
	print "Name:\tHeld up"
	print "Bind:\tToggle Play/Pause\n"
	playing!=playing
	player.playPause(playing)
def pronate():
	print "Gesture detected!"
	print "Name:\tPronate"
	print "Bind:\tVolume +1%\n"
	player.setVolumeRelative(0.01)
def supanate():
	print "Gesture detected!"
	print "Name:\tSupanate"
	print "Bind:\tVolume -1%\n"
	player.setVolumeRelative(-0.01)
def swing_down():
	print "Gesture detected!"
	print "Name:\tSwing down"
	print "Bind:\tNext track\n"
	player.next()
#def clear():
#	down=0
#	l=0
#	r=0
while 1:
	data = watch.read()
   	acc={'x':ord(data[0]), 'y':ord(data[1]), 'z':ord(data[2])}
	if acc['x']+acc['y']+acc['z']!=0:
		x=(acc['x'] + x) /2
		y=(acc['y'] + y) /2
		z=(acc['z'] + z) /2
		print "x: %s\ty:%s\tz:%s"%(acc['x'],acc['y'],acc['z'])
	if (y>25) & (y<100) & (z>35):
		down+=1
	if (y<220) & (y>190) & (z>240) & (z<250):
		up+=1
	# volume, but only if hand not holding the head ;)
	if (y>230) or (y<30):
		if (x>20) & (x<=35):
			r+=1;
		elif (x>35) & (x<55):
			r+=8 #strong tilt
		elif (x<225) & (x>=205):
			l+=1
		elif (x<205) & (x>190):
			l+=8 #strong tilt
		else:
			r=0
			l=0
	if (r>20):
		pronate()
		r=0
	if (l>20):
		supanate()
		l=0
	#down gesture unpaus OR next title
	if (down>5) & (downmillies-int(round(time.time()*1000))<-2000):
		downmillies=int(round(time.time()*1000))
		down=0
		up=0
		if (paused==1):
				paused=0
				raised()
		else:
			swing_down()
	#raise hand to pause, down gesture to unpause
	if (up>5) & (paused==0) & (upmillies-int(round(time.time()*1000))<-2000):
		paused=1
		upmillies=int(round(time.time()*1000))
		up=0
		down=0
		raised()

########NEW FILE########
__FILENAME__ = pass-the-ball
#!/usr/bin/env python
import eZ430
import time
import urllib2

#Wireless link init
watch = eZ430.watch("/dev/tty.usbmodem001")

#Variables
current = 1
baseurl = "http://localhost:8080/"

def neutral():
	print "Neutral"

def left():
	print "Left"
	try:
		urllib2.urlopen(baseurl + "moveleft")
	except urllib2.URLError:
		error()

def right():
	print "Right"
	try:
		urllib2.urlopen(baseurl + "moveright")
	except urllib2.URLError:
		error()

def error():
	print "Some error in opening url"

#Gestures
while 1:
	time.sleep(1)
	data = watch.read()
   	acc={'x':ord(data[0]), 'y':ord(data[1]), 'z':ord(data[2])}
   	
	if acc['x']+acc['y']+acc['z']!=0:
#    		print "x: %s\ty:%s\tz:%s\tpd:%s"%(acc['x'],acc['y'],acc['z'],pd)
		x=acc['x']
		y=acc['y']
		z=acc['z']
		
		#left
		if (y > 220 and y < 235):
			print "l"
			if (current != 0):
				current = 0
				left()

		#neutral
		if (y > 210 and y < 215):
			print "n"
			if (current != 1):
				current = 1
				neutral()

		#right
		if (y > 0 and y < 20):
			print "r"
			if (current != 2):
				current = 2
				right()
		

########NEW FILE########
__FILENAME__ = ppt-mac
#!/usr/bin/env python
import os, eZ430
from time import sleep

verbose = 1 # set this to 0 if you don't want detailed log

watch = eZ430.watch("/dev/tty.usbmodem001") #replace this 

# commands
leftcmd = """
osascript -e 'tell application "System Events" to key code 124' 
"""

rightcmd = """
osascript -e 'tell application "System Events" to key code 123' 
"""

while 1:
	data = watch.read(7)
	button = int(ord(data[6]))

	if(button == 18):
		if(verbose): print "Right pressed."
		os.system(rightcmd)
		watch.debounce()
		sleep(0.3) # sleep for 300 ms. So that the slide doesn't move very fast
	elif(button == 50):
		if verbose: print "Left pressed."
		os.system(leftcmd)
		watch.debounce()
		sleep(0.3) # sleep for 300 ms. So that the slide doesn't move very fast

########NEW FILE########
__FILENAME__ = ppt
#!/usr/bin/env python
import os, eZ430

verbose = 1
watch = eZ430.watch()
if verbose: print "Opening eZ430 on",watch.dev
if(os.system("xdotool --version")!=0):
	print "You need xdotool."
	os.exit(1)
while 1:
	data = watch.read(7)
	button = int(ord(data[6]))
	if(button == 18):
		if(verbose): print "Right pressed."
		os.system("xdotool click 3")
		watch.debounce()
	elif(button == 50):
		if verbose: print "Left pressed."
		os.system("xdotool click 1")
		watch.debounce()
	elif(button == 34):
		if verbose: print "Home pressed."
		os.system("xdotool key Home")
		watch.debounce()

########NEW FILE########
