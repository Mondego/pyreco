__FILENAME__ = bison
"""
A bot to automatically play Burrito Bison. 

This was my first big project that I tackled in Python. It has been 
one year since I wrote it, and it still gets forked every now and 
again. So, high time for a refactoring session! 

The original bison.py will remain. It's like a time capsule now. 
"""

import os
import csv
import sys
import time
import Image
import offset
import win32api
import win32con
import ImageOps
import ImageGrab
from ctypes import *
from random import random
from random import randrange
from multiprocessing import Process
from desktop_magic import getMonitorCoordinates 
from desktop_magic import getScreenAsImage as grab

def get_play_area(monitor):
	'''
	Snaps an image of the chosen monitor (zero indexed). 
	Loops through the RGB pixels looking for the value 
	(244,222,176), which corresponds to the top left 
	most pixel of the game.

	It returns the coordinates of the playarea. 
	'''
	
	TOP_LEFT_PIXELS = (204,204,204)
	GREY_BORDER = (204,204,204)
	SCREEN_WIDTH = 719
	SCREEN_HEIGH = 479

	monitor_coords = getMonitorCoordinates(0) #set to whatever monitor you have the game screen on
	im = grab(monitor_coords)
	imageWidth, imHeight = im.size
	imageArray = im.getdata()

	for index, pixel in enumerate(imageArray):
		if pixel == TOP_LEFT_PIXELS:
			# getdata returns a flat array, so the below figures out
			# the 2d coords based on the index position.
			top = (index / imageWidth)
			left = (index % imageWidth)
			if (im.getpixel((left + 1, top + 1)) == GREY_BORDER and
				im.getpixel((left + 2, top + 2)) == GREY_BORDER):
				top += 5
				left += 5
				
				return (left, top, left + SCREEN_WIDTH, top + SCREEN_HEIGH) 

	raise Exception("Play area not in view." 
			"Make sure the game is visible on screen!")	


def _getLocationOffsetAndPixel():
	playArea = get_play_area()
	offset.x = playArea[0]
	offset.y = playArea[1]

	snapshot = ImageGrab.grab(playArea)

	pos = list(win32api.GetCursorPos())
	pos[0] = pos[0] - offset.x
	pos[1] = pos[1] - offset.y
	pixelAtMousePos = getPixel(pos[0], pos[1])

	print pos, pixelAtMousePos

def _dumpDataToExcel(data):
	'''
	dump frequency and bin information to a csv
	file for Histogram creation. 
	'''
	data.sort()
	bins = _createBins(data)
	with open('histogram.csv', 'wb') as csvfile:
		writer = csv.writer(csvfile, delimiter=',')
		writer.writerow(['Frequency', 'Bins'])
		for i in range(len(data)):
			if i < len(bins):
				writer.writerow([data[i], bins[i]])
			else:
				writer.writerow([data[i]])

def _createBins(data, binNum=15):
	'''
	Generates equally sized bins for 
	histogram output
	'''
	minVal = data[0]
	maxVal = data[-1]
	dataRange = maxVal - minVal
	binRange = dataRange/binNum
	bins = []
	for i in range(binNum):
		bins.append(minVal)
		minVal += binRange
	return bins


def getPixel(x,y):
	offset.x
	offset.y
	

	gdi= windll.gdi32
	RGBInt = gdi.GetPixel(windll.user32.GetDC(0),
				offset.x + x, offset.y + y)

	red = RGBInt & 255
	green = (RGBInt >> 8) & 255
	blue = (RGBInt >> 16) & 255
	return (red, green, blue)

def check_pixel(location, color):
	pixel = getPixel(location[0], location[1])
	print 'input color:      ', color
	print 'check pixel color:', pixel 
	if pixel in [color]:
		return True
	return False	

def is_spinner_screen():
	STAR_LOCATION = (339, 47)
	GOLD_STAR_COLOR = (255, 225, 13)
	
	return check_pixel(STAR_LOCATION, GOLD_STAR_COLOR)

def wait_for_needle():
	NEEDLE_CENTER = (327, 121)
	BOARD_COLOR = (250,114,95)

	s = time.time()
	hit_count = 0
	while time.time() - s < 15: #If STILL not found after 15 sec. Prob on wrong screen
		if not check_pixel(NEEDLE_CENTER, BOARD_COLOR):
			hit_count += 1 
			if hit_count > 30:
				return True


def set_mouse_pos(pos=(0,0)):
	x,y = pos
	x = x + offset.x
	y = y + offset.y
	win32api.SetCursorPos((x,y))

def launcher():
    
    expectedVal= (250, 152, 135)
    im = ImageGrab.grab((455, 435, 501, 467))
    inVal =  im.getpixel((41,24))
##    print inVal
##    im.save(os.getcwd() + '\\' + 'launcher.png', "PNG")
##    im.putpixel((32,28), (0,0,0))
##    print inVal
    if inVal != expectedVal:
        left_click()
        im.save(os.getcwd() + '\\' + 'launcher.png', "PNG")
        print 'Launch!'
        return 1
    else:
        print 'missed'
        launcher()


    

def runFinished():
    expectedVal = (42,181,240)
    eVal2 = (17,31,75)
    box = (181,362,850,452)
    
    im = ImageGrab.grab(box)
    
    inVal = im.getpixel((591, 30))
    inVal2 = im.getpixel((35, 49))
    
    if inVal == expectedVal and inVal2 == eVal2:
        return True


def fuzzCheck(im):
    coppa = (99,104,137)
    if im.getpixel((randrange(263,290),(randrange(196,223)))) == coppa:
        print 'A cop!'
        return True
    if im.getpixel((randrange(295,320),(randrange(196,223)))) == coppa:
        print 'A cop!'
        return True



def bubbleCheck(im):
    bubble = (252,114,186)
    if im.getpixel((randrange(298,325),randrange(100,120))) == bubble:
        print 'A Bubble!'
        return True
    if im.getpixel((randrange(325,350),randrange(80,200))) == bubble:
        print 'A Bubble!'

    

def specialChecker(im):
    special = (255,250,240)
    if im.getpixel((624,130)) == special:
        return(True)

def spinCheck(im):
    launchGuy = (255,242,252)
    if im.getpixel((546,90)) == launchGuy:
        return True
    
def multiClick():
    for i in range(14):
        left_click()
        
def eventFinder():
    
    box = (200,500,884,750)
    im = ImageGrab.grab(box)

    if specialChecker(im):
        print 'Special spotted!\n'
        p = Process(target= multiClick())
        p.start()
        p.join()
        

    if bubbleCheck(im):
        print "A bubble has appeared!\n"
        left_click()

##    if specialChecker(im):
##        print 'Special spotted!\n'
##        for i in range(15):
##            left_click()

    if fuzzCheck(im):
        left_click()

    if specialChecker(im):
        print 'Special spotted!\n'
        

    if spinCheck(im):
        if isSpinning():
            launcher()
            
    print 'searching...'
        
        


def can_shop():
	SHOP_BUTTON = (497, 55)
	BUTTON_COLOR = (39, 178, 237)

	if not check_pixel(SHOP_BUTTON, BUTTON_COLOR):
		return True
	return False

def enter_shop():
	SHOP_BUTTON = (497, 55)
	set_mouse_pos(SHOP_BUTTON)
	left_click()

def exitShop():
    set_mouse_pos((685, 446))
    left_click()

def check_sales_and_purcahse():
	shop_items = {
		'elastic_cables': [(116, 99), (236, 138, 207)],
		'slippery_lotion': [(209, 104), (228, 132, 200)],
		'pickpocket': [(304, 101), (234, 136, 205)],
		'bounciness': [(112, 191), (235, 136, 206)],
		'rocket_slam': [(207, 188), (234, 136, 205)],
		'resistance': [(303, 191), (237, 138, 208)],
		'bubble_gummies': [(115, 293), (232, 133, 203)],
		'glider_gummies': [(206, 296), (235, 136, 206)],
		'rocket_gummies': [(303, 295), (227, 131, 199)],
		'pogostick': [(111, 381), (235, 136, 206)],
		'pepper_gummies': [(210, 383), (234, 136, 205)],
		'general_goods': [(306, 380), (233, 134, 204)]
	}

	while True:
		item_available = get_available_items(shop_items)
		if item_available is None:
			break
		purchase_item(item_available)
	print 'Done shopping'

def get_available_items(shop_items):
	for k, v in shop_items.iteritems():
		item_location = v[0]
		item_color = v[1]	
		print 'checking:', k

		if not check_pixel(item_location, item_color):
			print 'purchasing item:', k
			return item_location
	return None

def purchase_item(item_location):
	set_mouse_pos(item_location)
	left_click()

	BUY_BUTTON = (582, 193)
	set_mouse_pos(BUY_BUTTON)
	left_click()
	time.sleep(1)

def on_retry_screen():
	RETRY_LOC, RETRY_COLOR = [(637, 56), (35, 175, 243)]
	if check_pixel(RETRY_LOC, RETRY_COLOR):
		return True
	return False

def infoBoxLeft():
    expectedVal = (46,195,251)
    eVal2 = (251,223,114)
    box = (160,339,460,652)
    
    im = ImageGrab.grab(box)
    
    inVal2 = im.getpixel((92,84))
    inVal = im.getpixel((24,82))

    if inVal == expectedVal and inVal2 == eVal2:
        print "an InfoBox is on screen"
        return True

def infoBoxMid():
    expectedVal = (28,184,250)
    eVal2 = (251,223,114)
    box = (160,339,460,652)
    
    im = ImageGrab.grab(box)
    
    inVal2 = im.getpixel((230,164))
    inVal = im.getpixel((178,166))

    if inVal == expectedVal and inVal2 == eVal2:
        print "mis-screen InfoBox showing"
        return True

def infoExplosive():
    box = (160,339,460,652)
    im = ImageGrab.grab()
    
    expectedVal = (33,175,235)
    inVal = im.getpixel((389,442))

    eVal2 = (241,216,117)
    inVal2 = im.getpixel((445,440))    

    if inVal == expectedVal and inVal2 == eVal2:
        print "InfoExplosion Dialog On screen"
        return True

def infoBubble():
    im = ImageGrab.grab()

    inPix = (59,195,246)
    if im.getpixel((385,440)) == inPix:
        return True
    
    


boxes = [1,1,1,1,1,1]
def play():    
    shopping = False
    count =0
    
    while True:
        if shopping == False:
            if infoBoxLeft() == True:
                clickInfo()
                boxes[0]=0
                               
            elif infoBoxMid() == True:
                set_mouse_pos((345,505))
                left_click()

            elif infoExplosive() == True:
                set_mouse_pos((395,440))
                left_click()
            if infoBubble():
                set_mouse_pos((385,440))
                left_click()
                                   
            else:
                eventFinder()
                count +=1
                print count
                if count >15:
                    left_click()
                    count=0
                eventFinder()
                
            if runFinished() == True:
                if canShop() == True:
                    set_mouse_pos((695,385))
                    left_click()
                    shopping = True
                else:               
                    retry()
                    time.sleep(2)



        else:
            
            while checkSales() == True:
                buy()
            exitShop()
            time.sleep(2)
            play()

def left_click():
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN,0,0)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP,0,0)
    print "MOUSE CLICK!!"
    time.sleep(.05)

def main():
	play_area = get_play_area(0)
	# print play_area
	offset.save_to_json((play_area[0], play_area[1]))
	reload(offset)
	# print offset.x, offset.y

	im = grab(play_area)
	im.save('adfsadsf.png', 'png')
	# # print is_spinner_screen()
	# # set_mouse_pos((720, 270))
	# # wait_for_needle()
	# # left_click()

	# if can_shop():
	# 	enter_shop()

	# time.sleep(3)

	# for i in range(12):
	# 	time.sleep(3)
	pos = win32api.GetCursorPos()
	x = pos[0] - offset.x
	y = pos[1] - offset.y
	print '[(%d, %d), %s]' % (x,y, str(getPixel(x,y)))
	print 

	print on_retry_screen()
	# print on_retry_screen()
	# check_sales_and_purcahse()
	# print getPixel(631, 54)
	
bot_logo = '''



		 ____                      _  _          
		|  _ \                    (_)| |         
		| |_) | _   _  _ __  _ __  _ | |_   ___  
		|  _ < | | | || '__|| '__|| || __| / _ \ 
		| |_) || |_| || |   | |   | || |_ | (_) |
		|____/  \__,_||_|   |_|   |_| \__| \___/ 
				 ____          _   
				|  _ \        | |  
				| |_) |  ___  | |_ 
				|  _ <  / _ \ | __|
				| |_) || (_) || |_ 
				|____/  \___/  \__|



		1. Start Bot
		2. Quit
'''

if __name__ == '__main__':
    print bot_logo
    c = input('Select an option:')
            

    
            

########NEW FILE########
__FILENAME__ = bison
"""

All of this is configured to run at 1280x1024 resolution, playing at
http://notdoppler.com/burritobison.php

Also on chrome. It'll mess up if browser is a different size as it uses
very fragil and poorly designed getpixel() calls to check for things.. 

"""

import ImageGrab, ImageOps
import Image
import sys, os
import win32api, win32con
import time
from random import random
from random import randrange
from multiprocessing import Process

##GLOBALS
shopping = True
playing = True

def mousePos(x=(0,0)):
    win32api.SetCursorPos(x)
    #Temporary position. Eventually this will receive arguments based on
    #game logic
    tmp = (156, 335)

def isSpinning():
    mousePos((475,620))
    expectedVal = (255, 225, 13)
    box = (473,377,530,432)
    
    im = ImageGrab.grab()
    
    inVal = im.getpixel((500, 390))
    ##print inVal
    ##print expectedVal
    im.save(os.getcwd() + '\\' + 'Spinning.png', "PNG")
    if inVal == expectedVal:
        print 'Spinning = True'
        return True
    else:
        print 'Not spinning'
        return False
    ##im.save(os.getcwd() + '\\' + 'text_002.png', "PNG")

def launcher():
    
    expectedVal= (250, 152, 135)
    im = ImageGrab.grab((455, 435, 501, 467))
    inVal =  im.getpixel((41,24))
##    print inVal
##    im.save(os.getcwd() + '\\' + 'launcher.png', "PNG")
##    im.putpixel((32,28), (0,0,0))
##    print inVal
    if inVal != expectedVal:
        leftClick()
        im.save(os.getcwd() + '\\' + 'launcher.png', "PNG")
        print 'Launch!'
        return 1
    else:
        print 'missed'
        launcher()

def leftClick():
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN,0,0)
##    time.sleep(.1)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP,0,0)
    print "MOUSE CLICK!!"
    time.sleep(.05)
    

def runFinished():
    expectedVal = (42,181,240)
    eVal2 = (17,31,75)
    box = (181,362,850,452)
    
    im = ImageGrab.grab(box)
    
    inVal = im.getpixel((591, 30))
    inVal2 = im.getpixel((35, 49))
    
    if inVal == expectedVal and inVal2 == eVal2:
        return True


def fuzzCheck(im):
    coppa = (99,104,137)
    if im.getpixel((randrange(263,290),(randrange(196,223)))) == coppa:
        print 'A cop!'
        return True
    if im.getpixel((randrange(295,320),(randrange(196,223)))) == coppa:
        print 'A cop!'
        return True



def bubbleCheck(im):
    bubble = (252,114,186)
    if im.getpixel((randrange(298,325),randrange(100,120))) == bubble:
        print 'A Bubble!'
        return True
    if im.getpixel((randrange(325,350),randrange(80,200))) == bubble:
        print 'A Bubble!'

    

def specialChecker(im):
    special = (255,250,240)
    if im.getpixel((624,130)) == special:
        return(True)

def spinCheck(im):
    launchGuy = (255,242,252)
    if im.getpixel((546,90)) == launchGuy:
        return True
    
def multiClick():
    for i in range(14):
        leftClick()
        
def eventFinder():
    
    box = (200,500,884,750)
    im = ImageGrab.grab(box)

    if specialChecker(im):
        print 'Special spotted!\n'
        p = Process(target= multiClick())
        p.start()
        p.join()
        

    if bubbleCheck(im):
        print "A bubble has appeared!\n"
        leftClick()

##    if specialChecker(im):
##        print 'Special spotted!\n'
##        for i in range(15):
##            leftClick()

    if fuzzCheck(im):
        leftClick()

    if specialChecker(im):
        print 'Special spotted!\n'
        

    if spinCheck(im):
        if isSpinning():
            launcher()
            
    print 'searching...'
        
        


def canShop():
    im = ImageGrab.grab()
    
    expectedVal = (242,227,110)
    inVal = im.getpixel((695,385))
    if expectedVal == inVal:
        return True

def exitShop():
    mousePos((840,785))
    leftClick()

def checkSales():
    im = ImageGrab.grab()

    
    if im.getpixel((275,440))[2] < 150:
        print 'Elastic for sale\n'
        mousePos((275,525))
        leftClick()
        time.sleep(.05)
        return True
    
    elif im.getpixel((370,435))[2] < 150:
        print 'slip for sale\n'
        mousePos((370,435))
        leftClick()
        time.sleep(.05)
        return True
    
    elif im.getpixel((465,439))[2] < 150:
        print 'Pickpocket for sale\n'
        mousePos((465,439))
        leftClick()
        time.sleep(.05)
        return True
    
    elif im.getpixel((458,532))[2] < 150:
        print 'Resistance for sale\n'
        mousePos((458,532))
        leftClick()
        time.sleep(.05)
        return True
    
    elif im.getpixel((365,530))[2] < 150:
        print 'rocket for sale\n'
        mousePos((365,530))
        leftClick()
        time.sleep(.05)
        return True
    
    elif im.getpixel((270,530))[2] < 150:
        print 'Bouncies for sale\n'
        mousePos((270,530))
        leftClick()
        time.sleep(.1)
        return True
    
    elif im.getpixel((272, 635))[2] < 150:
        print 'BubbleGum for sale\n'
        mousePos((272, 635))
        leftClick()
        time.sleep(.1)
        return True
    
    elif im.getpixel((367,635))[2] < 150:
        print 'Glider for sale\n'
        mousePos((367,635))
        leftClick()
        time.sleep(.1)
        return True
    
    elif im.getpixel((460,635))[2] < 130:
        print 'Rocket for sale\n'
        mousePos((460,635))
        leftClick()
        time.sleep(.1)
        return True
    
    elif im.getpixel((270,725))[2] < 150:
        print 'Pogo for sale\n'
        mousePos((270,725))
        leftClick()
        time.sleep(.1)
        return True
    
    elif im.getpixel((370,725))[2] < 150:
        print 'Pepper for sale\n'
        mousePos((370,725))
        leftClick()
        time.sleep(.1)
        return True
    
    elif im.getpixel((463,725))[2] < 150:
        print 'general for sale\n'
        mousePos((463,725))
        leftClick()
        time.sleep(.1)
        return True
    
    else:
        return False


def buy():
    mousePos((745,535))
    leftClick()
  
def retry():
    mousePos((780,415))
    leftClick()

def clickInfo():
    mousePos((195,424))
    leftClick()

def infoBoxLeft():
    expectedVal = (46,195,251)
    eVal2 = (251,223,114)
    box = (160,339,460,652)
    
    im = ImageGrab.grab(box)
    
    inVal2 = im.getpixel((92,84))
    inVal = im.getpixel((24,82))

    if inVal == expectedVal and inVal2 == eVal2:
        print "an InfoBox is on screen"
        return True

def infoBoxMid():
    expectedVal = (28,184,250)
    eVal2 = (251,223,114)
    box = (160,339,460,652)
    
    im = ImageGrab.grab(box)
    
    inVal2 = im.getpixel((230,164))
    inVal = im.getpixel((178,166))

    if inVal == expectedVal and inVal2 == eVal2:
        print "mis-screen InfoBox showing"
        return True

def infoExplosive():
    box = (160,339,460,652)
    im = ImageGrab.grab()
    
    expectedVal = (33,175,235)
    inVal = im.getpixel((389,442))

    eVal2 = (241,216,117)
    inVal2 = im.getpixel((445,440))    

    if inVal == expectedVal and inVal2 == eVal2:
        print "InfoExplosion Dialog On screen"
        return True

def infoBubble():
    im = ImageGrab.grab()

    inPix = (59,195,246)
    if im.getpixel((385,440)) == inPix:
        return True
    
    


boxes = [1,1,1,1,1,1]
def play():    
    shopping = False
    count =0
    
    while True:
        if shopping == False:
            if infoBoxLeft() == True:
                clickInfo()
                boxes[0]=0
                               
            elif infoBoxMid() == True:
                mousePos((345,505))
                leftClick()

            elif infoExplosive() == True:
                mousePos((395,440))
                leftClick()
            if infoBubble():
                mousePos((385,440))
                leftClick()
                                   
            else:
                eventFinder()
                count +=1
                print count
                if count >15:
                    leftClick()
                    count=0
                eventFinder()
                
            if runFinished() == True:
                if canShop() == True:
                    mousePos((695,385))
                    leftClick()
                    shopping = True
                else:               
                    retry()
                    time.sleep(2)



        else:
            
            while checkSales() == True:
                buy()
            exitShop()
            time.sleep(2)
            play()

                

def main():
##    pass  
    time.sleep(2)
    play()
        
if __name__ == '__main__':
    main()
            

    
            

########NEW FILE########
__FILENAME__ = desktop_magic
"""
Robust functions for grabbing and saving screenshots on Windows.
"""

# TODO: support capture of individual displays (and at the same time with a "single screenshot")
# Use GetDeviceCaps; see http://msdn.microsoft.com/en-us/library/dd144877%28v=vs.85%29.aspx

import ctypes
import win32gui
import win32ui
import win32con
import win32api


class BITMAPINFOHEADER(ctypes.Structure):
	_fields_ = [
		('biSize', ctypes.c_uint32),
		('biWidth', ctypes.c_int),
		('biHeight', ctypes.c_int),
		('biPlanes', ctypes.c_short),
		('biBitCount', ctypes.c_short),
		('biCompression', ctypes.c_uint32),
		('biSizeImage', ctypes.c_uint32),
		('biXPelsPerMeter', ctypes.c_long),
		('biYPelsPerMeter', ctypes.c_long),
		('biClrUsed', ctypes.c_uint32),
		('biClrImportant', ctypes.c_uint32)
	]



class BITMAPINFO(ctypes.Structure):
	_fields_ = [
		('bmiHeader', BITMAPINFOHEADER),
		('bmiColors', ctypes.c_ulong * 3)
	]

class GrabFailed(Exception):
	"""
	Could not take a screenshot.
	"""

class MonitorSelectionOutOfBounds(Exception):
	'''
	Argument out of bounds
	'''

class BoundingBoxOutOfRange(Exception):
	'''
	Coordinates are too large for the current resolution
	'''


class DIBFailed(Exception):
	pass



def _deleteDCAndBitMap(dc, bitmap):
	dc.DeleteDC()
	win32gui.DeleteObject(bitmap.GetHandle())

def getMonitorCoordinates(targetMonitor):
	'''
	Enumerates the available monitor. Return the 
	Screen Dimensions of the selected monitor. 
	'''
	HMONITOR = 0
	HDCMONITOR = 1
	SCREENRECT = 2

	try:
		monitors = win32api.EnumDisplayMonitors(None, None)

		if targetMonitor > len(monitors)-1:
			raise MonitorSelectionOutOfBounds("Monitor argument exceeds attached number of devices.\n"
				"There are only %d display devices attached.\n" % len(monitors) + 
				"Please select appropriate device ( 0=Primary, 1=Secondary, etc..)." )

		left,top,right,bottom = monitors[targetMonitor][SCREENRECT]
		width = right - left
		height = bottom

	finally:
		# I can't figure out what to do with the handle to the Monitor 
		# that gets returned from EnumDisplayMonitors (the first object in
		# the tuple). Trying to close it throws an error.. Does it not need 
		# cleaned up at all? Most of the winApi is back magic to me... 
		
		# These device context handles were the only things that I could Close()
		for monitor in monitors:
			monitor[HDCMONITOR].Close()

	return (left, top, width, height)

def getSecondaryMonitorCoordinates():
	'''
	Enumerates the available monitors. Return the 
	Screen Dimensions of the secondary monitor. 
	'''
	HMONITOR = 0
	HDCMONITOR = 1
	SCREENRECT = 2

	try:
		monitors = win32api.EnumDisplayMonitors(None, None)

		# if targetMonitor > len(monitors)-1:
		# 	raise MonitorSelectionOutOfBounds("Monitor argument exceeds attached number of devices.\n"
		# 		"There are only %d display devices attached.\n" % len(monitors) + 
		# 		"Please select appropriate device ( 0=Primary, 1=Secondary, etc..)." )

		left,top,right,bottom = monitors[-1][SCREENRECT]
		width = right - left
		height = bottom

	finally:
		# I can't figure out what to do with the handle to the Monitor 
		# that gets returned from EnumDisplayMonitors (the first object in
		# the tuple). Trying to close it throws an error.. Does it not need 
		# cleaned up at all? Most of the winApi is back magic to me... 
		
		# These device context handles were the only things that I could Close()
		for monitor in monitors:
			monitor[HDCMONITOR].Close()

	return (left, top, width, height)


def getDCAndBitMap(saveBmpFilename=None, bbox=None):
	"""
	Returns a (DC, PyCBitmap).  On the returned PyCBitmap, you *must* call
	win32gui.DeleteObject(aPyCBitmap.GetHandle()).  On the returned DC,
	you *must* call aDC.DeleteDC()
	"""
	hwnd = win32gui.GetDesktopWindow()
	if bbox:
		left, top, width, height = bbox
		if (left < win32api.GetSystemMetrics(win32con.SM_XVIRTUALSCREEN) or 
			top < win32api.GetSystemMetrics(win32con.SM_YVIRTUALSCREEN) or 
			width > win32api.GetSystemMetrics(win32con.SM_CXVIRTUALSCREEN) or
			height > win32api.GetSystemMetrics(win32con.SM_CYVIRTUALSCREEN)):
			raise Exception('Invalid bounding box. Range exceeds available screen area.')	
		width = width - left
		height = height - top

	else:
		# Get complete virtual screen, including all monitors.
		left = win32api.GetSystemMetrics(win32con.SM_XVIRTUALSCREEN)
		top = win32api.GetSystemMetrics(win32con.SM_YVIRTUALSCREEN)
		width = win32api.GetSystemMetrics(win32con.SM_CXVIRTUALSCREEN)
		height = win32api.GetSystemMetrics(win32con.SM_CYVIRTUALSCREEN)
		##print "L", left, "T", top, "dim:", width, "x", height

		# Retrieve the device context (DC) for the entire window.
	
	hwndDevice = win32gui.GetWindowDC(hwnd)
	##print "device", hwndDevice
	assert isinstance(hwndDevice, (int, long)), hwndDevice

	mfcDC  = win32ui.CreateDCFromHandle(hwndDevice)
	try:
		saveDC = mfcDC.CreateCompatibleDC()
		saveBitMap = win32ui.CreateBitmap()
		# Above line is assumed to never raise an exception.
		try:
			saveBitMap.CreateCompatibleBitmap(mfcDC, width, height)
			saveDC.SelectObject(saveBitMap)
			try:
				saveDC.BitBlt((0, 0), (width, height), mfcDC, (left, top), win32con.SRCCOPY)
			except win32ui.error, e:
				raise GrabFailed("Error during BitBlt. "
					"Possible reasons: locked workstation, no display, "
					"or an active UAC elevation screen. Error was: " + str(e))
			if saveBmpFilename is not None:
				saveBitMap.SaveBitmapFile(saveDC, saveBmpFilename)
		except:
			_deleteDCAndBitMap(saveDC, saveBitMap)
			# Let's just hope the above line doesn't raise an exception
			# (or it will mask the previous exception)
			raise
	finally:
		mfcDC.DeleteDC()

	return saveDC, saveBitMap


def getBGR32(dc, bitmap):
	"""
	Returns a (raw BGR str, (width, height)) for C{dc}, C{bitmap}.
	Guaranteed to be 32-bit.  Note that the origin of the returned image is
	in the bottom-left corner, and the image has 32-bit line padding.
	"""
	bmpInfo = bitmap.GetInfo()
	width, height = bmpInfo['bmWidth'], bmpInfo['bmHeight']

	bmi = BITMAPINFO()
	ctypes.memset(ctypes.byref(bmi), 0x00, ctypes.sizeof(bmi))
	bmi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
	bmi.bmiHeader.biWidth = width
	bmi.bmiHeader.biHeight = height
	bmi.bmiHeader.biBitCount = 24
	bmi.bmiHeader.biPlanes = 1

	bufferLen = height * ((width * 3 + 3) & -4)
	pbBits = ctypes.create_string_buffer(bufferLen)

	ret = ctypes.windll.gdi32.GetDIBgetits(
		dc.GetHandleAttrib(),
		bitmap.GetHandle(),
		0,
		height,
		ctypes.byref(pbBits),
		ctypes.pointer(bmi),
		win32con.DIB_RGB_COLORS)
	if ret == 0:
		raise DIBFailed("Return code 0 from GetDIBits")

	assert len(pbBits.raw) == bufferLen, len(pbBits.raw)

	return pbBits.raw, (width, height)


def getScreenAsImage(bbox=None):
	"""
	Returns a PIL Image object (mode RGB) of the current screen (incl.
	all monitors).

	bbox =  boundingBox. Used to snap a subarea of the screen. 
	A tuple of (x, y, width, height). 
	"""
	import Image
	dc, bitmap = getDCAndBitMap(bbox=bbox)
	try:
		bmpInfo = bitmap.GetInfo()
		# bmpInfo is something like {
		# 	'bmType': 0, 'bmWidthBytes': 5120, 'bmHeight': 1024,
		# 	'bmBitsPixel': 32, 'bmPlanes': 1, 'bmWidth': 1280}
		##print bmpInfo
		size = (bmpInfo['bmWidth'], bmpInfo['bmHeight'])

		if bmpInfo['bmBitsPixel'] == 32:
			# Use GetBitmapBits and BGRX if the bpp == 32, because
			# it's ~15% faster than the method below.
			data = bitmap.GetBitmapBits(True) # asString=True
			return Image.frombuffer(
				'RGB', size, data, 'raw', 'BGRX', 0, 1)
		else:
			# If bpp != 32, we cannot use GetBitmapBits, because it
			# does not return a 24/32-bit image when the screen is at
			# a lower color depth.
			try:
				data, size = getBGR32(dc, bitmap)
			except DIBFailed, e:
				raise GrabFailed("getBGR32 failed. Error was " + str(e))
			# BGR, 32-bit line padding, origo in lower left corner
			return Image.frombuffer(
				'RGB', size, data, 'raw', 'BGR', (size[0] * 3 + 3) & -4, -1)
	finally:
		_deleteDCAndBitMap(dc, bitmap)


def saveScreenToBmp(bmpFilename, bbox=None):
	"""
	Save a screenshot (incl. all monitors) to a .bmp file.  Does not require PIL.
	The .bmp file will have the same bit-depth as the screen; it is not
	guaranteed to be 32-bit.

	bbox = boundingBox. Used to snap a subarea of the screen. 
	A tuple of (x, y, width, height). 
	"""
	dc, bitmap = getDCAndBitMap(saveBmpFilename=bmpFilename, bbox=bbox)
	_deleteDCAndBitMap(dc, bitmap)


def _demo():
	saveNames = ['allMonitors', 'primaryMonitor', 'secondaryMonitor', 'boundingTestOne', 'boundingTestTwo']
	params = [None, getMonitorCoordinates(0), getMonitorCoordinates(1), (0,0,100,50), (400,300, 200,200)]

	# for i in range(len(saveNames)):
	# 	saveScreenToBmp( saveNames[i] + '.bmp', params[i])
	# 	im = getScreenAsImage(params[i])
	# 	im.save(saveNames[i] + '.png', format='png' )


if __name__ == '__main__':
	im = getScreenAsImage((588, 117, 1307, 596))
	im.save('testttttttt.png', 'png')

########NEW FILE########
__FILENAME__ = offset
import json

def load_from_json():
	with open('offsets.json', 'rb') as f:
		return json.load(f)

def save_to_json(offsets):
	with open('offsets.json', 'wb') as f:
		f.write(json.dumps(offsets))

__offsets = load_from_json()

x = __offsets[0]
y = __offsets[1]


########NEW FILE########
