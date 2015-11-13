__FILENAME__ = feedback
import pygame, sys
from numpy import *
from pygame.locals import *
import scipy
from pymindwave.pyeeg import bin_power
from time import time
fpsClock= pygame.time.Clock()
from random import random, choice

class FeedbackTask:
	def __init__(self):
		font = pygame.font.Font("freesansbold.ttf",20)
		self.title_img = font.render(self.name,False, pygame.Color(255,0,0))

	def process_baseline_recording(raw_values):
		pass

	def frame(self,p,surface):
		surface.blit(self.title_img,(300,50))


class FeedbackGraph:
	def __init__(self):
		self.values = []
		self.times = []

	def insert_value(self,t, value):

		self.values.append(value)
		self.times.append(time())

	def draw_graph(self,surface, scale):
		x = 600
		i = len(self.values)
		if len(self.values)>3:
			while x>0:
				i-=1
				v = self.values[i]
				t = self.times[i]
				x = 500-(time()-t)*10
				y = 400-v*scale
				if i<len(self.values)-1:
					pygame.draw.line(surface, pygame.Color(255,0,0),(x,y),(lx,ly), 5)
				ly = y
				lt = t
				lx = x
				if i==0:
					break


class Attention(FeedbackTask):
	name = "Attention"
	def __init__(self):
		FeedbackTask.__init__(self)
		self.values = []
		self.times = []
		self.graph = FeedbackGraph()

	def process_baseline_recording(raw_values):
		pass

	def frame(self,p, window):
		FeedbackTask.frame(self, p, window)
		value = p.current_attention
		if value>0 and value<=100:
			if len(self.graph.times)==0 or time()>=self.graph.times[-1]+1:
				self.graph.insert_value(time(), value)

		for i in range(6):
			pygame.draw.line(window, pygame.Color(0,0,200),(0,400-i*20*3),(600,400-i*20*3), 2)
		self.graph.draw_graph(window,3.0)


class Meditation(FeedbackTask):
	name = "Meditation"
	def __init__(self):
		FeedbackTask.__init__(self)
		self.values = []
		self.times = []
		self.graph = FeedbackGraph()

	def process_baseline_recording(raw_values):
		pass

	def frame(self,p, window):
		FeedbackTask.frame(self, p, window)
		value = p.current_meditation
		if value>0 and value<=100:
			if len(self.graph.times)==0 or time()>=self.graph.times[-1]+1:
				self.graph.insert_value(time(), value)

		for i in range(6):
			pygame.draw.line(window, pygame.Color(0,0,200),(0,400-i*20*3),(600,400-i*20*3), 2)
		self.graph.draw_graph(window,3.0)



class ThetaLowerTask(FeedbackTask):
	name = "Lower Theta"
	def __init__(self):
		FeedbackTask.__init__(self)
		self.spectra = []
		self.graph = FeedbackGraph()

	def process_baseline_recording(raw_values):
		pass

	def frame(self, p,window):
		flen = 50
		spectrum, relative_spectrum = bin_power(p.raw_values[-p.buffer_len:], range(flen),512)
		self.spectra.append(array(relative_spectrum))
		if len(self.spectra)>30:
			self.spectra.pop(0)
		spectrum = mean(array(self.spectra),axis=0)
		value = (1-sum(spectrum[3:8]))*100
		self.graph.insert_value(time(), value)
		for i in range(6):
			pygame.draw.line(window, pygame.Color(0,0,200),(0,400-i*20*3),(600,400-i*20*3), 2)
		self.graph.draw_graph(window,3.0)



class ThetaIncreaseTask(FeedbackTask):
	name = "Increase Theta"
	def __init__(self):
		FeedbackTask.__init__(self)
		self.spectra = []
		self.graph = FeedbackGraph()
	def process_baseline_recording(raw_values):
		pass
	def frame(self, p,window):
		FeedbackTask.frame(self,p,window)
		flen = 50
		spectrum, relative_spectrum = bin_power(p.raw_values[-p.buffer_len:], range(flen),512)
		self.spectra.append(array(relative_spectrum))
		if len(self.spectra)>10:
			self.spectra.pop(0)
		spectrum = mean(array(self.spectra),axis=0)
		value = (sum(spectrum[3:8] / sum(spectrum[8:40])))*200
		self.graph.insert_value(time(), value)
		for i in range(6):
			pygame.draw.line(window, pygame.Color(0,0,200),(0,400-i*20*3),(600,400-i*20*3), 2)
		self.graph.draw_graph(window,3.0)


tasks = [Attention, Meditation, ThetaLowerTask, ThetaIncreaseTask]

task_keys ={
	K_1: Attention,
	K_2: Meditation,
	K_3: ThetaLowerTask,
	K_4: ThetaIncreaseTask

}

def feedback_menu(window,p):
	quit = False
	font = pygame.font.Font("freesansbold.ttf",20)
	task_images = [font.render("%i: %s" % (i+1, cls.name), False, pygame.Color(255,0,0)) for i,cls in enumerate(tasks)]
	while not quit:
		window.fill(pygame.Color(0,0,0))
		y= 300
		for img in task_images:
			window.blit(img, (400,y))
			y+= img.get_height()
		p.update()
		pygame.display.update()
		for event in pygame.event.get():
			if event.type==QUIT:
				pygame.quit()
				sys.exit()
			if event.type==KEYDOWN:
					if event.key== K_F5:
						pass
					elif event.key == K_ESCAPE:
						quit = True
					elif event.key in task_keys:
						start_session(task_keys[event.key])

def start_session(Task):
	quit = False
	font = pygame.font.Font("freesansbold.ttf",20)
	task = Task()
	while not quit:
		window.fill(pygame.Color(0,0,0))
		p.update()
		for event in pygame.event.get():
			if event.type==QUIT:
				pygame.quit()
				sys.exit()
			if event.type==KEYDOWN:
				if event.key== K_F5:
					pass
				elif event.key == K_ESCAPE:
					quit = True
		task.frame(p,window)
		pygame.display.update()
		fpsClock.tick(20)

if __name__=="__main__":
	pygame.init()

	fpsClock= pygame.time.Clock()

	window = pygame.display.set_mode((1280,720))
	pygame.display.set_caption("PyGame Neurofeedback Trainer")

	from pymindwave.parser import Parser
	p = Parser('/dev/ttyUSB0')
	feedback_menu(window, p)


########NEW FILE########
__FILENAME__ = mind_echo
#!/usr/bin/env python
# -*- coding:utf-8 -*-

import platform
import sys, time
from pymindwave import headset
from pymindwave.pyeeg import bin_power

def raw_to_spectrum(rawdata):
    flen = 50
    spectrum, relative_spectrum = bin_power(rawdata, range(flen), 512)
    #print spectrum
    #print relative_spectrum
    return spectrum


if __name__ == "__main__":
    if platform.system() == 'Darwin':
        hs = headset.Headset('/dev/tty.MindWave')
    else:
        hs = headset.Headset('/dev/ttyUSB0')

    # wait some time for parser to udpate state so we might be able
    # to reuse last opened connection.
    time.sleep(1)
    if hs.get_state() != 'connected':
        hs.disconnect()

    while hs.get_state() != 'connected':
        time.sleep(1)
        print 'current state: {0}'.format(hs.get_state())
        if (hs.get_state() == 'standby'):
            print 'trying to connect...'
            hs.connect()

    print 'now connected!'
    while True:
        print 'wait 1s to collect data...'
        time.sleep(1)
        print 'attention {0}, meditation {1}'.format(hs.get('attention'), hs.get('meditation'))
        print 'alpha_waves {0}'.format(hs.get('alpha_waves'))
        print 'blink_strength {0}'.format(hs.get('blink_strength'))
        print 'raw data:'
        print hs.get('rawdata')
        #print raw_to_spectrum(hs.get('rawdata'))

    print 'disconnecting...'
    hs.disconnect()
    hs.destroy()
    sys.exit(0)

########NEW FILE########
__FILENAME__ = sdl_viewer
import pygame, sys
from numpy import *
from pygame.locals import *
import scipy
from pymindwave.pyeeg import bin_power

pygame.init()

fpsClock= pygame.time.Clock()

window = pygame.display.set_mode((1280,720))
pygame.display.set_caption("Mindwave Viewer")

from pymindwave.parser import Parser

p = Parser('/dev/ttyUSB0')

blackColor = pygame.Color(0,0,0)
redColor = pygame.Color(255,0,0)
greenColor = pygame.Color(0,255,0)
deltaColor = pygame.Color(100,0,0)
thetaColor = pygame.Color(0,0,255)
alphaColor = pygame.Color(255,0,0)
betaColor = pygame.Color(0,255,00)
gammaColor = pygame.Color(0,255,255)


background_img = pygame.image.load("sdl_viewer_background.png")


font = pygame.font.Font("freesansbold.ttf",20)
raw_eeg = True
spectra = []
iteration = 0

meditation_img = font.render("Meditation", False, redColor)
attention_img = font.render("Attention", False, redColor)

record_baseline = False

while True:
    p.update()
    window.blit(background_img,(0,0))
    if p.sending_data:
        iteration+=1

        flen = 50

        if len(p.raw_values)>=500:
            spectrum, relative_spectrum = bin_power(p.raw_values[-p.buffer_len:], range(flen),512)
            spectra.append(array(relative_spectrum))
            if len(spectra)>30:
                spectra.pop(0)

            spectrum = mean(array(spectra),axis=0)
            for i in range (flen-1):
                value = float(spectrum[i]*1000)
                if i<3:
                    color = deltaColor
                elif i<8:
                    color = thetaColor
                elif i<13:
                    color = alphaColor
                elif i<30:
                    color = betaColor
                else:
                    color = gammaColor
                pygame.draw.rect(window, color, (25+i*10, 400-value, 5, value))
        else:
            pass
        pygame.draw.circle(window, redColor, (800,200), p.current_attention/2)
        pygame.draw.circle(window, greenColor, (800,200), 60/2,1)
        pygame.draw.circle(window, greenColor, (800,200), 100/2,1)
        window.blit(attention_img, (760,260))
        pygame.draw.circle(window, redColor, (700,200), p.current_meditation/2)
        pygame.draw.circle(window, greenColor, (700,200), 60/2, 1)
        pygame.draw.circle(window, greenColor, (700,200), 100/2, 1)

        window.blit(meditation_img, (600,260))
        if len(p.current_vector)>7:
            m = max(p.current_vector)
            for i in range(7):
                if m == 0:
                    value = 0
                else:
                    value = p.current_vector[i] *100.0/m
                pygame.draw.rect(window, redColor, (600+i*30,450-value, 6,value))

        if raw_eeg:
            lv = 0
            for i,value in enumerate(p.raw_values[-1000:]):
                v = value/ 255.0/ 5
                pygame.draw.line(window, redColor, (i+25, 500-lv), (i+25, 500-v))
                lv = v
    else:
        img = font.render("Mindwave Headset is not sending data... Press F5 to autoconnect or F6 to disconnect.", False, redColor)
        window.blit(img,(100,100))
        pass

    for event in pygame.event.get():
        if event.type==QUIT:
            pygame.quit()
            sys.exit()
        if event.type==KEYDOWN:
            if event.key== K_F5:
                p.write_serial("\xc2")
            elif event.key== K_F6:
                p.write_serial("\xc1")
            elif event.key==K_ESCAPE:
                pygame.quit()
                sys.exit()
            elif event.key == K_F7:
                record_baseline = True
                p.start_raw_recording("baseline_raw.csv")
                p.start_esense_recording("baseline_esense.csv")
            elif event.key == K_F8:
                record_baseline = False
                p.stop_esense_recording()
                p.stop_raw_recording()
    pygame.display.update()
    fpsClock.tick(30)

########NEW FILE########
__FILENAME__ = headset
#!/usr/bin/env python
# -*- coding:utf-8 -*-

import threading
import serial
import parser
import time


COMMAND_BYTES = {
    'auto_connect': '\xc2',
    'disconnect': '\xc1',
}



class DongleReader(threading.Thread):
    def __init__(self, parser, *args, **kwargs):
        self.parser = parser
        self.running = True
        super(DongleReader, self).__init__(*args, **kwargs)

    def run(self):
        while self.running:
            if not self.parser.sending_data:
                time.sleep(0.5)
            self.parser.update()

    def stop(self):
        self.running = False
        self._Thread__stop()


class Headset():
    def __init__(self, dongle_dev, global_id=None):
        if global_id:
            self.auto_connect = False
            self.global_id = global_id
        else:
            self.auto_connect = True
        self.dongle_dev = dongle_dev
        self.dongle_fs = serial.Serial(dongle_dev,  115200, timeout=0.001)
        self.parser = parser.VirtualParser(self.dongle_fs)
        # setup listening thread
        self.dongle_reader = DongleReader(self.parser)
        self.dongle_reader.daemon = True
        self.dongle_reader.start()

    def connect(self):
        if self.auto_connect:
            self.dongle_fs.write(COMMAND_BYTES['auto_connect'])
        else:
            #@TODO connect to specific headset  11.07 2013 (houqp)
            pass

    def disconnect(self):
        self.dongle_fs.write(COMMAND_BYTES['disconnect'])

    def destroy(self):
        self.dongle_reader.stop()
        self.dongle_fs.close()

    def get_state(self):
        return self.parser.dongle_state

    def get_current_attention(self):
        return self.parser.current_attention

    def get_current_meditation(self):
        return self.parser.current_meditation

    def get_rawdata(self):
        return self.parser.raw_values

    def get_waves_vector(self):
        return self.parser.current_vector

    def get_delta_waves(self):
        return self.parser.current_vector[0]

    def get_theta_waves(self):
        return self.parser.current_vector[1]

    def get_alpha_waves(self):
        return (self.parser.current_vector[2] + self.parser.current_vector[3]) / 2

    def get_beta_waves(self):
        return (self.parser.current_vector[4] + self.parser.current_vector[5]) / 2

    def get_gamma_waves(self):
        return (self.parser.current_vector[6] + self.parser.current_vector[7]) / 2

    def get_blink_strength(self):
        return self.parser.current_blink_strength

    def get(self, stuff):
        if stuff == 'attention':
            return self.get_current_attention()
        elif stuff == 'meditation':
            return self.get_current_meditation()
        elif stuff == 'rawdata':
            return self.get_rawdata()
        elif stuff == 'state':
            return self.get_state()
        elif stuff == 'waves_vector':
            return self.get_waves_vector()
        elif stuff == 'delta_waves':
            return self.get_delta_waves()
        elif stuff == 'theta_waves':
            return self.get_theta_waves()
        elif stuff == 'alpha_waves':
            return self.get_alpha_waves()
        elif stuff == 'beta_waves':
            return self.get_beta_waves()
        elif stuff == 'gamma_waves':
            return self.get_gamma_waves()
        elif stuff == 'blink_strength':
            return self.get_blink_strength()
        else:
            return None


########NEW FILE########
__FILENAME__ = parser
import struct
from time import time
from time import sleep
from numpy import mean
import serial


SYNC_BYTES = [0xaa, 0xaa]

def bigend_24b(b1, b2, b3):
    return b1* 255 * 255 + 255 * b2 + b3


"""
This is a Driver Class for the Neurosky Mindwave. The Mindwave consists of a
headset and an usb dongle.  The dongle communicates with the mindwave headset
wirelessly and can relay the data to a program that opens its usb serial port.

Some clarification on the Neurosky docs: The Neurosky Chip/Board is used in
several devices, for example the Neurosky Mindset, the Neurosky Mindwave,
Mattel MindFlex and several others. These chips all use the same protocol over
a serial connection, but depending on the device, some kind of middleware is
used. The Mindset uses bluetooth to communicate with the computer, the Mindwave
has its own proprietary dongle, and the MindFlex uses a dumbed down RF protocol
to communicate with the "main" board of the game.

However, all of these devices speak essentially the same protocol. I also had
the impression, before reading the docs, that only the Mindset provides raw
values, which is obviously not the case.

The Mindwave ships with a TCP/IP server to provide apps a relatively easy way
to access the data. Maybe I will write a substitute in Python in the future,
but for now I am satisfied with using Python only.
"""

class VirtualParser(object):
    def __init__(self, input_fstream):
        #self.parser = self.run()
        #self.parser.next()
        self.current_vector  = [0 for i in range(8)]
        self.raw_values = []
        self.current_meditation = 0
        self.current_attention= 0
        self.current_blink_strength = 0
        self.current_spectrum = []
        self.sending_data = False
        self.dongle_state ="initializing"
        self.raw_file = None
        self.esense_file = None
        self.input_fstream = input_fstream
        self.input_stream = []
        self.read_more_stream()
        self.buffer_len = 512*3

    def is_sending_data(self):
        self.sending_data = True
        self.dongle_state = 'connected'

    def read_more_stream(self):
        self.input_stream += [ord(b) for b in list(self.input_fstream.read(1000))]
        sleep(0.1)

    def parse_payload(self, payload):
        while len(payload) > 0:
            #@TODO parse excode?  13.07 2013 (houqp)
            code = payload.pop(0)
            if code >= 0x80:
                vlen = payload.pop(0)
                # multi-byte codes
                if code == 0x80:
                    self.is_sending_data()
                    high_word = payload.pop(0)
                    low_word = payload.pop(0)
                    self.raw_values.append(high_word * 255 + low_word)
                    if (len(self.raw_values)) > 512:
                        self.raw_values.pop(0)
                elif code == 0x83:
                    self.is_sending_data()
                    # ASIC_EEG_POWER_INT
                    # delta, theta, low-alpha, high-alpha, low-beta, high-beta,
                    # low-gamma, high-gamma
                    self.current_vector = []
                    for i in range(8):
                        self.current_vector.append(
                            bigend_24b(payload.pop(0), payload.pop(0), payload.pop(0)))
                elif code == 0xd0:
                    # headset found
                    # 0xaa 0xaa 0x04 0xd0 0x02 0x05 0x05 0x23
                    self.global_id = 255 * payload.pop(0) + payload.pop(0)
                    self.dongle_state = 'connected'
                elif code == 0xd1:
                    # headset not found
                    # 0xaa 0xaa 0x04 0xd1 0x02 0x05 0x05 0xf2
                    self.error = 'not found'
                elif code == 0xd2:
                    # 0xaa 0xaa 0x04 0xd2 0x02 0x05 0x05 0x21
                    self.disconnected_global_id = 255 * payload.pop(0) + payload.pop(0)
                    self.dongle_state = 'disconnected'
                elif code == 0xd3:
                    # request denied
                    # 0xaa 0xaa 0x02 0xd3 0x00 0x2c
                    self.error = 'request denied'
                elif code == 0xd4:
                    # standby mode, only pop the useless byte
                    # 0xaa 0xaa 0x03 0xd4 0x01 0x00 0x2a
                    self.dongle_state = 'standby'
                    payload.pop(0)
                else:
                    # unknown multi-byte codes
                    pass
            else:
                # single-byte codes
                val = payload.pop(0)
                self.is_sending_data()
                if code == 0x02:
                    self.poor_signal = val
                elif code == 0x04:
                    self.current_attention = val
                elif code == 0x05:
                    self.current_meditation = val
                elif code == 0x16:
                    self.current_blink_strength = val
                else:
                    # unknown code
                    pass

    def consume_stream(self):
        while 1:
            while self.input_stream[:2] != SYNC_BYTES:
                retry = 0
                while len(self.input_stream) <= 3:
                    retry += 1
                    if retry > 3:
                        return False
                    self.read_more_stream()
                self.input_stream.pop(0)
            # remove sync bytes
            self.input_stream.pop(0)
            self.input_stream.pop(0)
            plen = 170
            while plen == 170:
                # we are in sync now
                if len(self.input_stream) == 0:
                    return False
                plen = self.input_stream.pop(0)
                if plen == 170:
                    # in sync
                    continue
                else:
                    break
            if plen > 170:
                # plen too large
                continue

            if (len(self.input_stream) < plen + 1):
                # read the payload and checksum
                self.read_more_stream()
            if (len(self.input_stream) < plen + 1):
                return False

            chksum = 0
            for bv in self.input_stream[:plen]:
                chksum += bv
            # take the lowest byte and invert
            chksum = chksum & ord('\xff')
            chksum = (~chksum) & ord('\xff')
            payload = self.input_stream[:plen+1]
            self.input_stream = self.input_stream[plen+1:]
            # pop chksum and compare
            if chksum != payload.pop():
                # invalid payload, skip
                continue
            else:
                self.parse_payload(payload)
                return

    def update(self):
        self.consume_stream()
        #input_stream = self.input_fstream.read(1000)
        #for b in input_stream:
            #self.parser.send(ord(b))	# Send each byte to the generator

    def write_serial(self, string):
        self.input_fstream.write(string)

    def start_raw_recording(self, file_name):
        self.raw_file = file(file_name, "wt")
        self.raw_start_time = time()

    def start_esense_recording(self, file_name):
        self.esense_file = file(file_name, "wt")
        self.esense_start_time = time()

    def stop_raw_recording(self):
        if self.raw_file:
            self.raw_file.close()
            self.raw_file = None

    def stop_esense_recording(self):
        if self.esense_file:
            self.esense_file.close()
            self.esense_file = None

    def run(self):
        """
            This generator parses one byte at a time.
        """
        last = time()
        i = 1
        times = []
        while 1:
            byte = yield
            if byte== 0xaa:
                byte = yield # This byte should be "\aa" too
                if byte== 0xaa:
                    # packet synced by 0xaa 0xaa
                    packet_length = yield
                    packet_code = yield
                    if packet_code == 0xd4:
                        # standing by
                        self.dongle_state= "standby"
                    elif packet_code == 0xd0:
                        self.dongle_state = "connected"
                    elif packet_code == 0xd2:
                        data_len = yield
                        headset_id = yield
                        headset_id += yield
                        self.dongle_state = "disconnected"
                    else:
                        self.sending_data = True
                        left = packet_length-2
                        while left>0:
                            if packet_code ==0x80: # raw value
                                row_length = yield
                                a = yield
                                b = yield
                                value = struct.unpack("<h",chr(a)+chr(b))[0]
                                self.raw_values.append(value)
                                if len(self.raw_values)>self.buffer_len:
                                    self.raw_values = self.raw_values[-self.buffer_len:]
                                left-=2

                                if self.raw_file:
                                    t = time()-self.raw_start_time
                                    self.raw_file.write("%.4f,%i\n" %(t, value))
                            elif packet_code == 0x02: # Poor signal
                                a = yield
                                self.poor_signal = a
                                if a>0:
                                    pass
                                left-=1
                            elif packet_code == 0x04: # Attention (eSense)
                                a = yield
                                if a>0:
                                    v = struct.unpack("b",chr(a))[0]
                                    if v>0:
                                        self.current_attention = v
                                        if self.esense_file:
                                            self.esense_file.write("%.2f,,%i\n" % (time()-self.esense_start_time, v))
                                left-=1
                            elif packet_code == 0x05: # Meditation (eSense)
                                a = yield
                                if a>0:
                                    v = struct.unpack("b",chr(a))[0]
                                    if v>0:
                                        self.current_meditation = v
                                        if self.esense_file:
                                            self.esense_file.write("%.2f,%i,\n" % (time()-self.esense_start_time, v))

                                left-=1
                            elif packet_code == 0x16: # Blink Strength
                                self.current_blink_strength = yield
                                left-=1
                            elif packet_code == 0x83:
                                vlength = yield
                                self.current_vector = []
                                for row in range(8):
                                    a = yield
                                    b = yield
                                    c = yield
                                    value = a*255*255+b*255+c
                                    #value = c*255*255+b*255+a
                                    self.current_vector.append(value)
                                left -= vlength
                            packet_code = yield
                else:
                    pass # sync failed
            else:
                pass # sync failed


class Parser(VirtualParser):
    def __init__(self, serial_dev='/dev/ttyUSB0'):
        self.dongle = serial.Serial(serial_dev,  115200, timeout=0.001)
        VirtualParser.__init__(self, self.dongle)




########NEW FILE########
__FILENAME__ = pyeeg
"""Copyleft 2010 Forrest Sheng Bao http://fsbao.net

PyEEG, a Python module to extract EEG features, v 0.02_r2

Project homepage: http://pyeeg.org

**Data structure**

PyEEG only uses standard Python and numpy data structures,
so you need to import numpy before using it.
For numpy, please visit http://numpy.scipy.org

**Naming convention**

I follow "Style Guide for Python Code" to code my program
http://www.python.org/dev/peps/pep-0008/

Constants: UPPER_CASE_WITH_UNDERSCORES, e.g., SAMPLING_RATE, LENGTH_SIGNAL.

Function names: lower_case_with_underscores, e.g., spectrum_entropy.

Variables (global and local): CapitalizedWords or CapWords, e.g., Power.

If a variable name consists of one letter, I may use lower case, e.g., x, y.

Functions listed alphabetically
--------------------------------------------------

"""

from numpy.fft import fft
from numpy import zeros, floor, log10, log, mean, array, sqrt, vstack, cumsum, \
				  ones, log2, std
from numpy.linalg import svd, lstsq
import time

######################## Functions contributed by Xin Liu #################

def hurst(X):
	""" Compute the Hurst exponent of X. If the output H=0.5,the behavior
	of the time-series is similar to random walk. If H<0.5, the time-series
	cover less "distance" than a random walk, vice verse. 

	Parameters
	----------

	X

		list    
		
		a time series

	Returns
	-------
	H
        
		float    

		Hurst exponent

	Examples
	--------

	>>> import pyeeg
	>>> from numpy.random import randn
	>>> a = randn(4096)
	>>> pyeeg.hurst(a)
	>>> 0.5057444
	
	"""
	
	N = len(X)
    
	T = array([float(i) for i in xrange(1,N+1)])
	Y = cumsum(X)
	Ave_T = Y/T
	
	S_T = zeros((N))
	R_T = zeros((N))
	for i in xrange(N):
		S_T[i] = std(X[:i+1])
		X_T = Y - T * Ave_T[i]
		R_T[i] = max(X_T[:i + 1]) - min(X_T[:i + 1])
    
	R_S = R_T / S_T
	R_S = log(R_S)
	n = log(T).reshape(N, 1)
	H = lstsq(n[1:], R_S[1:])[0]
	return H[0]


######################## Begin function definitions #######################

def embed_seq(X,Tau,D):
	"""Build a set of embedding sequences from given time series X with lag Tau
	and embedding dimension DE. Let X = [x(1), x(2), ... , x(N)], then for each
	i such that 1 < i <  N - (D - 1) * Tau, we build an embedding sequence,
	Y(i) = [x(i), x(i + Tau), ... , x(i + (D - 1) * Tau)]. All embedding 
	sequence are placed in a matrix Y.

	Parameters
	----------

	X
		list	

		a time series
		
	Tau
		integer

		the lag or delay when building embedding sequence 

	D
		integer

		the embedding dimension

	Returns
	-------

	Y
		2-D list

		embedding matrix built

	Examples
	---------------
	>>> import pyeeg
	>>> a=range(0,9)
	>>> pyeeg.embed_seq(a,1,4)
	array([[ 0.,  1.,  2.,  3.],
	       [ 1.,  2.,  3.,  4.],
	       [ 2.,  3.,  4.,  5.],
	       [ 3.,  4.,  5.,  6.],
	       [ 4.,  5.,  6.,  7.],
	       [ 5.,  6.,  7.,  8.]])
	>>> pyeeg.embed_seq(a,2,3)
	array([[ 0.,  2.,  4.],
	       [ 1.,  3.,  5.],
	       [ 2.,  4.,  6.],
	       [ 3.,  5.,  7.],
	       [ 4.,  6.,  8.]])
	>>> pyeeg.embed_seq(a,4,1)
	array([[ 0.],
	       [ 1.],
	       [ 2.],
	       [ 3.],
	       [ 4.],
	       [ 5.],
	       [ 6.],
	       [ 7.],
	       [ 8.]])

	

	"""
	N =len(X)

	if D * Tau > N:
		print "Cannot build such a matrix, because D * Tau > N" 
		exit()

	if Tau<1:
		print "Tau has to be at least 1"
		exit()

	Y=zeros((N - (D - 1) * Tau, D))
	for i in xrange(0, N - (D - 1) * Tau):
		for j in xrange(0, D):
			Y[i][j] = X[i + j * Tau]
	return Y

def in_range(Template, Scroll, Distance):
	"""Determines whether one vector is the the range of another vector.
	
	The two vectors should have equal length.
	
	Parameters
	-----------------
	Template
		list
		The template vector, one of two vectors being compared

	Scroll
		list
		The scroll vector, one of the two vectors being compared
		
	D
		float
		Two vectors match if their distance is less than D
		
	Bit
		
	
	Notes
	-------
	The distance between two vectors can be defined as Euclidean distance
	according to some publications.
	
	The two vector should of equal length
	
	"""
	
	for i in range(0,  len(Template)):
			if abs(Template[i] - Scroll[i]) > Distance:
			     return False
	return True
	""" Desperate code, but do not delete
	def bit_in_range(Index): 
		if abs(Scroll[Index] - Template[Bit]) <=  Distance : 
			print "Bit=", Bit, "Scroll[Index]", Scroll[Index], "Template[Bit]",\
			 Template[Bit], "abs(Scroll[Index] - Template[Bit])",\
			 abs(Scroll[Index] - Template[Bit])
			return Index + 1 # move 

	Match_No_Tail = range(0, len(Scroll) - 1) # except the last one 
#	print Match_No_Tail

	# first compare Template[:-2] and Scroll[:-2]

	for Bit in xrange(0, len(Template) - 1): # every bit of Template is in range of Scroll
		Match_No_Tail = filter(bit_in_range, Match_No_Tail)
		print Match_No_Tail
		
	# second and last, check whether Template[-1] is in range of Scroll and 
	#	Scroll[-1] in range of Template

	# 2.1 Check whether Template[-1] is in the range of Scroll
	Bit = - 1
	Match_All =  filter(bit_in_range, Match_No_Tail)
	
	# 2.2 Check whether Scroll[-1] is in the range of Template
	# I just write a  loop for this. 
	for i in Match_All:
		if abs(Scroll[-1] - Template[i] ) <= Distance:
			Match_All.remove(i)
	
	
	return len(Match_All), len(Match_No_Tail)
	"""

def bin_power(X,Band,Fs):
	"""Compute power in each frequency bin specified by Band from FFT result of 
	X. By default, X is a real signal. 

	Note
	-----
	A real signal can be synthesized, thus not real.

	Parameters
	-----------

	Band
		list
	
		boundary frequencies (in Hz) of bins. They can be unequal bins, e.g. 
		[0.5,4,7,12,30] which are delta, theta, alpha and beta respectively. 
		You can also use range() function of Python to generate equal bins and 
		pass the generated list to this function.

		Each element of Band is a physical frequency and shall not exceed the 
		Nyquist frequency, i.e., half of sampling frequency. 

 	X
		list
	
		a 1-D real time series.

	Fs
		integer
	
		the sampling rate in physical frequency

	Returns
	-------

	Power
		list
	
		spectral power in each frequency bin.

	Power_ratio
		list

		spectral power in each frequency bin normalized by total power in ALL 
		frequency bins.

	"""

	C = fft(X)
	C = abs(C)
	Power =zeros(len(Band)-1);
	for Freq_Index in xrange(0,len(Band)-1):
		Freq = float(Band[Freq_Index])										## Xin Liu
		Next_Freq = float(Band[Freq_Index+1])
		Power[Freq_Index] = sum(C[floor(Freq/Fs*len(X)):floor(Next_Freq/Fs*len(X))])
	Power_Ratio = Power/sum(Power)
	return Power, Power_Ratio	

def first_order_diff(X):
	""" Compute the first order difference of a time series.

		For a time series X = [x(1), x(2), ... , x(N)], its	first order 
		difference is:
		Y = [x(2) - x(1) , x(3) - x(2), ..., x(N) - x(N-1)]
		
	"""
	D=[]
	
	for i in xrange(1,len(X)):
		D.append(X[i]-X[i-1])

	return D

def pfd(X, D=None):
	"""Compute Petrosian Fractal Dimension of a time series from either two 
	cases below:
		1. X, the time series of type list (default)
		2. D, the first order differential sequence of X (if D is provided, 
		   recommended to speed up)

	In case 1, D is computed by first_order_diff(X) function of pyeeg

	To speed up, it is recommended to compute D before calling this function 
	because D may also be used by other functions whereas computing it here 
	again will slow down.
	"""
	if D is None:																						## Xin Liu
		D = first_order_diff(X)
	N_delta= 0; #number of sign changes in derivative of the signal
	for i in xrange(1,len(D)):
		if D[i]*D[i-1]<0:
			N_delta += 1
	n = len(X)
	return log10(n)/(log10(n)+log10(n/n+0.4*N_delta))


def hfd(X, Kmax):
	""" Compute Hjorth Fractal Dimension of a time series X, kmax
	 is an HFD parameter
	"""
	L = [];
	x = []
	N = len(X)
	for k in xrange(1,Kmax):
		Lk = []
		for m in xrange(0,k):
			Lmk = 0
			for i in xrange(1,int(floor((N-m)/k))):
				Lmk += abs(X[m+i*k] - X[m+i*k-k])
			Lmk = Lmk*(N - 1)/floor((N - m) / float(k)) / k
			Lk.append(Lmk)
		L.append(log(mean(Lk)))
		x.append([log(float(1) / k), 1])
	
	(p, r1, r2, s)=lstsq(x, L)
	return p[0]

def hjorth(X, D = None):
	""" Compute Hjorth mobility and complexity of a time series from either two 
	cases below:
		1. X, the time series of type list (default)
		2. D, a first order differential sequence of X (if D is provided, 
		   recommended to speed up)

	In case 1, D is computed by first_order_diff(X) function of pyeeg

	Notes
	-----
	To speed up, it is recommended to compute D before calling this function 
	because D may also be used by other functions whereas computing it here 
	again will slow down.

	Parameters
	----------

	X
		list
		
		a time series
	
	D
		list
	
		first order differential sequence of a time series

	Returns
	-------

	As indicated in return line

	Hjorth mobility and complexity

	"""
	
	if D is None:
		D = first_order_diff(X)

	D.insert(0, X[0]) # pad the first difference
	D = array(D)

	n = len(X)

	M2 = float(sum(D ** 2)) / n
	TP = sum(array(X) ** 2)
	M4 = 0;
	for i in xrange(1, len(D)):
		M4 += (D[i] - D[i - 1]) ** 2
	M4 = M4 / n
	
	return sqrt(M2 / TP), sqrt(float(M4) * TP / M2 / M2)	# Hjorth Mobility and Complexity

def spectral_entropy(X, Band, Fs, Power_Ratio = None):
	"""Compute spectral entropy of a time series from either two cases below:
	1. X, the time series (default)
	2. Power_Ratio, a list of normalized signal power in a set of frequency 
	bins defined in Band (if Power_Ratio is provided, recommended to speed up)

	In case 1, Power_Ratio is computed by bin_power() function.

	Notes
	-----
	To speed up, it is recommended to compute Power_Ratio before calling this 
	function because it may also be used by other functions whereas computing 
	it here again will slow down.

	Parameters
	----------

	Band
		list

		boundary frequencies (in Hz) of bins. They can be unequal bins, e.g. 
		[0.5,4,7,12,30] which are delta, theta, alpha and beta respectively. 
		You can also use range() function of Python to generate equal bins and 
		pass the generated list to this function.

		Each element of Band is a physical frequency and shall not exceed the 
		Nyquist frequency, i.e., half of sampling frequency. 

 	X
		list

		a 1-D real time series.

	Fs
		integer

		the sampling rate in physical frequency

	Returns
	-------

	As indicated in return line	

	See Also
	--------
	bin_power: pyeeg function that computes spectral power in frequency bins

	"""
	
	if Power_Ratio is None:
		Power, Power_Ratio = bin_power(X, Band, Fs)

	Spectral_Entropy = 0
	for i in xrange(0, len(Power_Ratio) - 1):
		Spectral_Entropy += Power_Ratio[i] * log(Power_Ratio[i])
	Spectral_Entropy /= log(len(Power_Ratio))	# to save time, minus one is omitted
	return -1 * Spectral_Entropy

def svd_entropy(X, Tau, DE, W = None):
	"""Compute SVD Entropy from either two cases below:
	1. a time series X, with lag tau and embedding dimension dE (default)
	2. a list, W, of normalized singular values of a matrix (if W is provided,
	recommend to speed up.)

	If W is None, the function will do as follows to prepare singular spectrum:

		First, computer an embedding matrix from X, Tau and DE using pyeeg 
		function embed_seq(): 
					M = embed_seq(X, Tau, DE)

		Second, use scipy.linalg function svd to decompose the embedding matrix 
		M and obtain a list of singular values:
					W = svd(M, compute_uv=0)

		At last, normalize W:
					W /= sum(W)
	
	Notes
	-------------

	To speed up, it is recommended to compute W before calling this function 
	because W may also be used by other functions whereas computing	it here 
	again will slow down.
	"""

	if W is None:
		Y = EmbedSeq(X, tau, dE)
		W = svd(Y, compute_uv = 0)
		W /= sum(W) # normalize singular values

	return -1*sum(W * log(W))

def fisher_info(X, Tau, DE, W = None):
	""" Compute Fisher information of a time series from either two cases below:
	1. X, a time series, with lag Tau and embedding dimension DE (default)
	2. W, a list of normalized singular values, i.e., singular spectrum (if W is
	   provided, recommended to speed up.)

	If W is None, the function will do as follows to prepare singular spectrum:

		First, computer an embedding matrix from X, Tau and DE using pyeeg 
		function embed_seq():
			M = embed_seq(X, Tau, DE)

		Second, use scipy.linalg function svd to decompose the embedding matrix 
		M and obtain a list of singular values:
			W = svd(M, compute_uv=0)

		At last, normalize W:
			W /= sum(W)
	
	Parameters
	----------

	X
		list

		a time series. X will be used to build embedding matrix and compute 
		singular values if W or M is not provided.
	Tau
		integer

		the lag or delay when building a embedding sequence. Tau will be used 
		to build embedding matrix and compute singular values if W or M is not
		provided.
	DE
		integer

		the embedding dimension to build an embedding matrix from a given 
		series. DE will be used to build embedding matrix and compute 
		singular values if W or M is not provided.
	W
		list or array

		the set of singular values, i.e., the singular spectrum

	Returns
	-------

	FI
		integer

		Fisher information

	Notes
	-----
	To speed up, it is recommended to compute W before calling this function 
	because W may also be used by other functions whereas computing	it here 
	again will slow down.

	See Also
	--------
	embed_seq : embed a time series into a matrix
	"""

	if W is None:
		M = embed_seq(X, Tau, DE)
		W = svd(M, compute_uv = 0)
		W /= sum(W)	
	
	FI = 0
	for i in xrange(0, len(W) - 1):	# from 1 to M
		FI += ((W[i +1] - W[i]) ** 2) / (W[i])
	
	return FI

def ap_entropy(X, M, R):
	"""Computer approximate entropy (ApEN) of series X, specified by M and R.

	Suppose given time series is X = [x(1), x(2), ... , x(N)]. We first build
	embedding matrix Em, of dimension (N-M+1)-by-M, such that the i-th row of Em 
	is x(i),x(i+1), ... , x(i+M-1). Hence, the embedding lag and dimension are
	1 and M-1 respectively. Such a matrix can be built by calling pyeeg function 
	as Em = embed_seq(X, 1, M). Then we build matrix Emp, whose only 
	difference with Em is that the length of each embedding sequence is M + 1

	Denote the i-th and j-th row of Em as Em[i] and Em[j]. Their k-th elments 
	are	Em[i][k] and Em[j][k] respectively. The distance between Em[i] and Em[j]
	is defined as 1) the maximum difference of their corresponding scalar 
	components, thus, max(Em[i]-Em[j]), or 2) Euclidean distance. We say two 1-D
	vectors Em[i] and Em[j] *match* in *tolerance* R, if the distance between them 
	is no greater than R, thus, max(Em[i]-Em[j]) <= R. Mostly, the value of R is
	defined as 20% - 30% of standard deviation of X. 

	Pick Em[i] as a template, for all j such that 0 < j < N - M + 1, we can 
	check whether Em[j] matches with Em[i]. Denote the number of Em[j],  
	which is in the range of Em[i], as k[i], which is the i-th element of the 
	vector k. The probability that a random row in Em matches Em[i] is 
	\simga_1^{N-M+1} k[i] / (N - M + 1), thus sum(k)/ (N - M + 1), 
	denoted as Cm[i].

	We repeat the same process on Emp and obtained Cmp[i], but here 0<i<N-M 
	since the length of each sequence in Emp is M + 1.

	The probability that any two embedding sequences in Em match is then 
	sum(Cm)/ (N - M +1 ). We define Phi_m = sum(log(Cm)) / (N - M + 1) and
	Phi_mp = sum(log(Cmp)) / (N - M ).

	And the ApEn is defined as Phi_m - Phi_mp.


	Notes
	-----
	
	#. Please be aware that self-match is also counted in ApEn. 
	#. This function now runs very slow. We are still trying to speed it up.

	References
	----------

	Costa M, Goldberger AL, Peng CK, Multiscale entropy analysis of biolgical
	signals, Physical Review E, 71:021906, 2005

	See also
	--------
	samp_entropy: sample entropy of a time series
	
	Notes
	-----
	Extremely slow implementation. Do NOT use if your dataset is not small.

	"""
	N = len(X)

	Em = embed_seq(X, 1, M)	
	Emp = embed_seq(X, 1, M + 1) #	try to only build Emp to save time

	Cm, Cmp = zeros(N - M + 1), zeros(N - M)
	# in case there is 0 after counting. Log(0) is undefined.

	for i in xrange(0, N - M):
#		print i
		for j in xrange(i, N - M): # start from i, self-match counts in ApEn
#			if max(abs(Em[i]-Em[j])) <= R:# compare N-M scalars in each subseq v 0.01b_r1
			if in_range(Em[i], Em[j], R):
				Cm[i] += 1																						### Xin Liu
				Cm[j] += 1
				if abs(Emp[i][-1] - Emp[j][-1]) <= R: # check last one
					Cmp[i] += 1
					Cmp[j] += 1
		if in_range(Em[i], Em[N-M], R):
			Cm[i] += 1
			Cm[N-M] += 1
		# try to count Cm[j] and Cmp[j] as well here
	
#		if max(abs(Em[N-M]-Em[N-M])) <= R: # index from 0, so N-M+1 is N-M  v 0.01b_r1
#	if in_range(Em[i], Em[N - M], R):  # for Cm, there is one more iteration than Cmp
#			Cm[N - M] += 1 # cross-matches on Cm[N - M]
	
	Cm[N - M] += 1 # Cm[N - M] self-matches
#	import code;code.interact(local=locals())
	Cm /= (N - M +1 )
	Cmp /= ( N - M )
#	import code;code.interact(local=locals())
	Phi_m, Phi_mp = sum(log(Cm)),  sum(log(Cmp))

	Ap_En = (Phi_m - Phi_mp) / (N - M)

	return Ap_En

def samp_entropy(X, M, R):
	"""Computer sample entropy (SampEn) of series X, specified by M and R.

	SampEn is very close to ApEn. 

	Suppose given time series is X = [x(1), x(2), ... , x(N)]. We first build
	embedding matrix Em, of dimension (N-M+1)-by-M, such that the i-th row of Em 
	is x(i),x(i+1), ... , x(i+M-1). Hence, the embedding lag and dimension are
	1 and M-1 respectively. Such a matrix can be built by calling pyeeg function 
	as Em = embed_seq(X, 1, M). Then we build matrix Emp, whose only 
	difference with Em is that the length of each embedding sequence is M + 1

	Denote the i-th and j-th row of Em as Em[i] and Em[j]. Their k-th elments 
	are	Em[i][k] and Em[j][k] respectively. The distance between Em[i] and Em[j]
	is defined as 1) the maximum difference of their corresponding scalar 
	components, thus, max(Em[i]-Em[j]), or 2) Euclidean distance. We say two 1-D
	vectors Em[i] and Em[j] *match* in *tolerance* R, if the distance between them 
	is no greater than R, thus, max(Em[i]-Em[j]) <= R. Mostly, the value of R is
	defined as 20% - 30% of standard deviation of X. 

	Pick Em[i] as a template, for all j such that 0 < j < N - M , we can 
	check whether Em[j] matches with Em[i]. Denote the number of Em[j],  
	which is in the range of Em[i], as k[i], which is the i-th element of the 
	vector k.

	We repeat the same process on Emp and obtained Cmp[i], 0 < i < N - M.

	The SampEn is defined as log(sum(Cm)/sum(Cmp))

	References
	----------

	Costa M, Goldberger AL, Peng C-K, Multiscale entropy analysis of biolgical
	signals, Physical Review E, 71:021906, 2005

	See also
	--------
	ap_entropy: approximate entropy of a time series


	Notes
	-----
	Extremely slow computation. Do NOT use if your dataset is not small and you
	are not patient enough.

	"""

	N = len(X)

	Em = embed_seq(X, 1, M)	
	Emp = embed_seq(X, 1, M + 1)

	Cm, Cmp = zeros(N - M - 1) + 1e-100, zeros(N - M - 1) + 1e-100
	# in case there is 0 after counting. Log(0) is undefined.

	for i in xrange(0, N - M):
		for j in xrange(i + 1, N - M): # no self-match
#			if max(abs(Em[i]-Em[j])) <= R:  # v 0.01_b_r1 
			if in_range(Em[i], Em[j], R):
				Cm[i] += 1
#			if max(abs(Emp[i] - Emp[j])) <= R: # v 0.01_b_r1
				if abs(Emp[i][-1] - Emp[j][-1]) <= R: # check last one
					Cmp[i] += 1

	Samp_En = log(sum(Cm)/sum(Cmp))

	return Samp_En

def dfa(X, Ave = None, L = None):
	"""Compute Detrended Fluctuation Analysis from a time series X and length of
	boxes L.
	
	The first step to compute DFA is to integrate the signal. Let original seres
	be X= [x(1), x(2), ..., x(N)]. 

	The integrated signal Y = [y(1), y(2), ..., y(N)] is otained as follows
	y(k) = \sum_{i=1}^{k}{x(i)-Ave} where Ave is the mean of X. 

	The second step is to partition/slice/segment the integrated sequence Y into
	boxes. At least two boxes are needed for computing DFA. Box sizes are
	specified by the L argument of this function. By default, it is from 1/5 of
	signal length to one (x-5)-th of the signal length, where x is the nearest 
	power of 2 from the length of the signal, i.e., 1/16, 1/32, 1/64, 1/128, ...

	In each box, a linear least square fitting is employed on data in the box. 
	Denote the series on fitted line as Yn. Its k-th elements, yn(k), 
	corresponds to y(k).
	
	For fitting in each box, there is a residue, the sum of squares of all 
	offsets, difference between actual points and points on fitted line. 

	F(n) denotes the square root of average total residue in all boxes when box
	length is n, thus
	Total_Residue = \sum_{k=1}^{N}{(y(k)-yn(k))}
	F(n) = \sqrt(Total_Residue/N)

	The computing to F(n) is carried out for every box length n. Therefore, a 
	relationship between n and F(n) can be obtained. In general, F(n) increases
	when n increases.

	Finally, the relationship between F(n) and n is analyzed. A least square 
	fitting is performed between log(F(n)) and log(n). The slope of the fitting 
	line is the DFA value, denoted as Alpha. To white noise, Alpha should be 
	0.5. Higher level of signal complexity is related to higher Alpha.
	
	Parameters
	----------

	X:
		1-D Python list or numpy array
		a time series

	Ave:
		integer, optional
		The average value of the time series

	L:
		1-D Python list of integers
		A list of box size, integers in ascending order

	Returns
	-------
	
	Alpha:
		integer
		the result of DFA analysis, thus the slope of fitting line of log(F(n)) 
		vs. log(n). where n is the 

	Examples
	--------
	>>> import pyeeg
	>>> from numpy.random import randn
	>>> print pyeeg.dfa(randn(4096))
	0.490035110345

	Reference
	---------
	Peng C-K, Havlin S, Stanley HE, Goldberger AL. Quantification of scaling 
	exponents and 	crossover phenomena in nonstationary heartbeat time series. 
	_Chaos_ 1995;5:82-87

	Notes
	-----

	This value depends on the box sizes very much. When the input is a white
	noise, this value should be 0.5. But, some choices on box sizes can lead to
	the value lower or higher than 0.5, e.g. 0.38 or 0.58. 

	Based on many test, I set the box sizes from 1/5 of	signal length to one 
	(x-5)-th of the signal length, where x is the nearest power of 2 from the 
	length of the signal, i.e., 1/16, 1/32, 1/64, 1/128, ...

	You may generate a list of box sizes and pass in such a list as a parameter.

	"""

	X = array(X)

	if Ave is None:
		Ave = mean(X)

	Y = cumsum(X)
	Y -= Ave

	if L is None:
		L = floor(len(X)*1/(2**array(range(4,int(log2(len(X)))-4))))

	F = zeros(len(L)) # F(n) of different given box length n

	for i in xrange(0,len(L)):
		n = int(L[i])						# for each box length L[i]
		if n==0:
			print "time series is too short while the box length is too big"
			print "abort"
			exit()
		for j in xrange(0,len(X),n): # for each box
			if j+n < len(X):
				c = range(j,j+n)
				c = vstack([c, ones(n)]).T # coordinates of time in the box
				y = Y[j:j+n]				# the value of data in the box
				F[i] += lstsq(c,y)[1]	# add residue in this box
		F[i] /= ((len(X)/n)*n)
	F = sqrt(F)
	
	Alpha = lstsq(vstack([log(L), ones(len(L))]).T,log(F))[0][0]
	
	return Alpha

########NEW FILE########
__FILENAME__ = test_parser
#!/usr/bin/env python
# -*- coding:utf-8 -*-

import StringIO
from pymindwave import parser

standby_test_stream = StringIO.StringIO(
    '\xaa\xaa' + # [SYNC] sync packets
    '\x03' + # [PLENGTH] payload length
    '\xd4\x01\x00' + # in standby mode
    '\x2a' # [CHKSUM]
)

sync_test_stream1 = StringIO.StringIO(
    '\x00\x12\x71\xaa' +
    '\xaa\xaa' + # [SYNC] sync packets
    '\x03' + # [PLENGTH] payload length
    '\xd4\x01\x00' + # in standby mode
    '\x2a' # [CHKSUM]
)

sync_test_stream2 = StringIO.StringIO(
    '\x00\x12\x71' +
    '\xaa\xaa' + # [SYNC] sync packets
    '\x03' + # [PLENGTH] payload length
    '\xd4\x01\x00' + # in standby mode
    '\x2a' # [CHKSUM]
)

disconnected_test_stream = StringIO.StringIO(
    '\xaa\xaa' + # [SYNC] sync packets
    '\x04' + # [PLENGTH] payload length
    '\xd2' + # headset disconnected
    '\x02' + # data len
    '\xa1\x6c' + # headset global ID: 0xa16c
    '\x1e' # [CHKSUM]
)

raw_data_test_stream = StringIO.StringIO(
    '\x65\x02\x00\x64\x61' +
    '\xaa\xaa' +
    '\x04' +
    '\x80' +
    '\x02' +
    '\x00\x28' +
    '\x55'
)

official_test_stream = StringIO.StringIO(
    '\xaa\xaa' + # [SYNC] sync packets
    '\x20' + # [PLENGTH] payload length
    '\x02' + # [POOR_SIGNAL] quality
    '\x00' + # No poor signal detected (0/200)
    '\x83' + # [ASIC_EEG_POWER_INT]
    '\x18' + # [VLENGTH] 24 bytes
    '\x00' + # (1/3) Begin Delta bytes
    '\x00' + # (2/3)
    '\x94' + # (3/3) End Delta bytes
    '\x00' + # (1/3) Begin Theta bytes
    '\x00' + # (2/3)
    '\x42' + # (3/3) End Theta bytes
    '\x00' + # (1/3) Begin Low-alpha bytes
    '\x00' + # (2/3)
    '\x0b' + # (3/3) End Low-alpha bytes
    '\x00' + # (1/3) Begin High-alpha bytes
    '\x00' + # (2/3)
    '\x64' + # (3/3) End High-alpha bytes
    '\x00' + # (1/3) Begin Low-beta bytes
    '\x00' + # (2/3)
    '\x4d' + # (3/3) End Low-beta bytes
    '\x00' + # (1/3) Begin High-beta bytes
    '\x00' + # (2/3)
    '\x3d' + # (3/3) End High-beta bytes
    '\x00' + # (1/3) Begin Low-gamma bytes
    '\x00' + # (2/3)
    '\x07' + # (3/3) End Low-gamma bytes
    '\x00' + # (1/3) Begin Mid-gamma bytes
    '\x00' + # (2/3)
    '\x05' + # (3/3) End Mid-gamma bytes
    '\x04' + # [ATTENTION] eSense
    '\x0d' + # eSense Attention level of 13
    '\x05' + # [MEDITATION] eSense
    '\x3d' + # eSense Meditation level of 61
    '\x34' # [CHKSUM] (1's comp inverse of 8-bit Payload sum of 0xCB)
)


def test_standby_mode():
    p = parser.VirtualParser(standby_test_stream)
    p.update()
    assert (p.dongle_state == 'standby')

def test_sync():
    p = parser.VirtualParser(sync_test_stream1)
    p.update()
    assert (p.dongle_state == 'standby')
    p = parser.VirtualParser(sync_test_stream2)
    p.update()
    assert (p.dongle_state == 'standby')

def test_official_test_stream():
    p = parser.VirtualParser(official_test_stream)
    p.update()
    assert (p.sending_data)
    assert (p.current_attention == 13)
    assert (p.current_meditation == 61)
    assert (p.current_vector == [148, 66, 11, 100, 77, 61, 7, 5])

def test_disconnected_mode():
    p = parser.VirtualParser(disconnected_test_stream)
    p.update()
    assert (p.dongle_state == 'disconnected')

def test_rawdata_test():
    p = parser.VirtualParser(raw_data_test_stream)
    p.update()
    print p.raw_values
    assert (p.raw_values == [0x28])

########NEW FILE########
