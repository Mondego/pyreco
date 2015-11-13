__FILENAME__ = sensortag
#!/usr/bin/env python
# Michael Saunby. April 2013
#
# Notes.
# pexpect uses regular expression so characters that have special meaning
# in regular expressions, e.g. [ and ] must be escaped with a backslash.
#
#   Copyright 2013 Michael Saunby
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import pexpect
import sys
import time
from sensor_calcs import *
import json
import select

def floatfromhex(h):
    t = float.fromhex(h)
    if t > float.fromhex('7FFF'):
        t = -(float.fromhex('FFFF') - t)
        pass
    return t

class SensorTag:

    def __init__( self, bluetooth_adr ):
        self.con = pexpect.spawn('gatttool -b ' + bluetooth_adr + ' --interactive')
        self.con.expect('\[LE\]>', timeout=600)
        print "Preparing to connect. You might need to press the side button..."
        self.con.sendline('connect')
        # test for success of connect
	self.con.expect('Connection successful.*\[LE\]>')
        # Earlier versions of gatttool returned a different message.  Use this pattern -
        #self.con.expect('\[CON\].*>')
        self.cb = {}
        return

        self.con.expect('\[CON\].*>')
        self.cb = {}
        return

    def char_write_cmd( self, handle, value ):
        # The 0%x for value is VERY naughty!  Fix this!
        cmd = 'char-write-cmd 0x%02x 0%x' % (handle, value)
        print cmd
        self.con.sendline( cmd )
        return

    def char_read_hnd( self, handle ):
        self.con.sendline('char-read-hnd 0x%02x' % handle)
        self.con.expect('descriptor: .*? \r')
        after = self.con.after
        rval = after.split()[1:]
        return [long(float.fromhex(n)) for n in rval]

    # Notification handle = 0x0025 value: 9b ff 54 07
    def notification_loop( self ):
        while True:
	    try:
              pnum = self.con.expect('Notification handle = .*? \r', timeout=4)
            except pexpect.TIMEOUT:
              print "TIMEOUT exception!"
              break
	    if pnum==0:
                after = self.con.after
	        hxstr = after.split()[3:]
            	handle = long(float.fromhex(hxstr[0]))
            	#try:
	        if True:
                  self.cb[handle]([long(float.fromhex(n)) for n in hxstr[2:]])
            	#except:
                #  print "Error in callback for %x" % handle
                #  print sys.argv[1]
                pass
            else:
              print "TIMEOUT!!"
        pass

    def register_cb( self, handle, fn ):
        self.cb[handle]=fn;
        return

barometer = None
datalog = sys.stdout

class SensorCallbacks:

    data = {}

    def __init__(self,addr):
        self.data['addr'] = addr

    def tmp006(self,v):
        objT = (v[1]<<8)+v[0]
        ambT = (v[3]<<8)+v[2]
        targetT = calcTmpTarget(objT, ambT)
        self.data['t006'] = targetT
        print "T006 %.1f" % targetT

    def accel(self,v):
        (xyz,mag) = calcAccel(v[0],v[1],v[2])
        self.data['accl'] = xyz
        print "ACCL", xyz

    def humidity(self, v):
        rawT = (v[1]<<8)+v[0]
        rawH = (v[3]<<8)+v[2]
        (t, rh) = calcHum(rawT, rawH)
        self.data['humd'] = [t, rh]
        print "HUMD %.1f" % rh

    def baro(self,v):
        global barometer
        global datalog
        rawT = (v[1]<<8)+v[0]
        rawP = (v[3]<<8)+v[2]
        (temp, pres) =  self.data['baro'] = barometer.calc(rawT, rawP)
        print "BARO", temp, pres
        self.data['time'] = long(time.time() * 1000);
        # The socket or output file might not be writeable
        # check with select so we don't block.
        (re,wr,ex) = select.select([],[datalog],[],0)
        if len(wr) > 0:
            datalog.write(json.dumps(self.data) + "\n")
            datalog.flush()
            pass

    def magnet(self,v):
        x = (v[1]<<8)+v[0]
        y = (v[3]<<8)+v[2]
        z = (v[5]<<8)+v[4]
        xyz = calcMagn(x, y, z)
        self.data['magn'] = xyz
        print "MAGN", xyz

    def gyro(self,v):
        print "GYRO", v

def main():
    global datalog
    global barometer

    bluetooth_adr = sys.argv[1]
    #data['addr'] = bluetooth_adr
    if len(sys.argv) > 2:
        datalog = open(sys.argv[2], 'w+')

    while True:
     try:   
      print "[re]starting.."

      tag = SensorTag(bluetooth_adr)
      cbs = SensorCallbacks(bluetooth_adr)

      # enable TMP006 sensor
      tag.register_cb(0x25,cbs.tmp006)
      tag.char_write_cmd(0x29,0x01)
      tag.char_write_cmd(0x26,0x0100)

      # enable accelerometer
      tag.register_cb(0x2d,cbs.accel)
      tag.char_write_cmd(0x31,0x01)
      tag.char_write_cmd(0x2e,0x0100)

      # enable humidity
      tag.register_cb(0x38, cbs.humidity)
      tag.char_write_cmd(0x3c,0x01)
      tag.char_write_cmd(0x39,0x0100)

      # enable magnetometer
      tag.register_cb(0x40,cbs.magnet)
      tag.char_write_cmd(0x44,0x01)
      tag.char_write_cmd(0x41,0x0100)

      # enable gyroscope
      tag.register_cb(0x57,cbs.gyro)
      tag.char_write_cmd(0x5b,0x07)
      tag.char_write_cmd(0x58,0x0100)

      # fetch barometer calibration
      tag.char_write_cmd(0x4f,0x02)
      rawcal = tag.char_read_hnd(0x52)
      barometer = Barometer( rawcal )
      # enable barometer
      tag.register_cb(0x4b,cbs.baro)
      tag.char_write_cmd(0x4f,0x01)
      tag.char_write_cmd(0x4c,0x0100)

      tag.notification_loop()
     except:
      pass

if __name__ == "__main__":
    main()


########NEW FILE########
__FILENAME__ = sensortag_test
#!/usr/bin/env python
# Michael Saunby. April 2013   
# 
# Read temperature from the TMP006 sensor in the TI SensorTag 
# It's a BLE (Bluetooth low energy) device so using gatttool to
# read and write values. 
#
# Usage.
# sensortag_test.py BLUETOOTH_ADR
#
# To find the address of your SensorTag run 'sudo hcitool lescan'
# You'll need to press the side button to enable discovery.
#
# Notes.
# pexpect uses regular expression so characters that have special meaning
# in regular expressions, e.g. [ and ] must be escaped with a backslash.
#

import pexpect
import sys
import time

def floatfromhex(h):
    t = float.fromhex(h)
    if t > float.fromhex('7FFF'):
        t = -(float.fromhex('FFFF') - t)
        pass
    return t


# This algorithm borrowed from 
# http://processors.wiki.ti.com/index.php/SensorTag_User_Guide#Gatt_Server
# which most likely took it from the datasheet.  I've not checked it, other
# than noted that the temperature values I got seemed reasonable.
#
def calcTmpTarget(objT, ambT):
    m_tmpAmb = ambT/128.0
    Vobj2 = objT * 0.00000015625
    Tdie2 = m_tmpAmb + 273.15
    S0 = 6.4E-14            # Calibration factor
    a1 = 1.75E-3
    a2 = -1.678E-5
    b0 = -2.94E-5
    b1 = -5.7E-7
    b2 = 4.63E-9
    c2 = 13.4
    Tref = 298.15
    S = S0*(1+a1*(Tdie2 - Tref)+a2*pow((Tdie2 - Tref),2))
    Vos = b0 + b1*(Tdie2 - Tref) + b2*pow((Tdie2 - Tref),2)
    fObj = (Vobj2 - Vos) + c2*pow((Vobj2 - Vos),2)
    tObj = pow(pow(Tdie2,4) + (fObj/S),.25)
    tObj = (tObj - 273.15)
    print "%.2f C" % tObj


bluetooth_adr = sys.argv[1]
tool = pexpect.spawn('gatttool -b ' + bluetooth_adr + ' --interactive')
tool.expect('\[LE\]>')
print "Preparing to connect. You might need to press the side button..."
tool.sendline('connect')
# test for success of connect
tool.expect('\[CON\].*>')
tool.sendline('char-write-cmd 0x29 01')
tool.expect('\[LE\]>')
while True:
    time.sleep(1)
    tool.sendline('char-read-hnd 0x25')
    tool.expect('descriptor: .*') 
    rval = tool.after.split()
    objT = floatfromhex(rval[2] + rval[1])
    ambT = floatfromhex(rval[4] + rval[3])
    #print rval
    calcTmpTarget(objT, ambT)



########NEW FILE########
__FILENAME__ = sensortag_xively
#!/usr/bin/env python
# Michael Saunby. April 2013
#
# Notes.
# pexpect uses regular expression so characters that have special meaning
# in regular expressions, e.g. [ and ] must be escaped with a backslash.
#
#   Copyright 2013 Michael Saunby
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import pexpect
import sys
import time
from sensor_calcs import *
import json
import select
from xively_fns import xively_init, xively_write


def floatfromhex(h):
    t = float.fromhex(h)
    if t > float.fromhex('7FFF'):
        t = -(float.fromhex('FFFF') - t)
        pass
    return t

class SensorTag:

    def __init__( self, bluetooth_adr ):
        self.con = pexpect.spawn('gatttool -b ' + bluetooth_adr + ' --interactive')
        self.con.expect('\[LE\]>', timeout=600)
        print "Preparing to connect. You might need to press the side button..."
        self.con.sendline('connect')
        # test for success of connect
	self.con.expect('Connection successful.*\[LE\]>')
        # Earlier versions of gatttool returned a different message.  Use this pattern -
        #self.con.expect('\[CON\].*>')
        self.cb = {}
        return

        self.con.expect('\[CON\].*>')
        self.cb = {}
        return

    def char_write_cmd( self, handle, value ):
        # The 0%x for value is VERY naughty!  Fix this!
        cmd = 'char-write-cmd 0x%02x 0%x' % (handle, value)
        print cmd
        self.con.sendline( cmd )
        return

    def char_read_hnd( self, handle ):
        self.con.sendline('char-read-hnd 0x%02x' % handle)
        self.con.expect('descriptor: .*? \r')
        after = self.con.after
        rval = after.split()[1:]
        return [long(float.fromhex(n)) for n in rval]

    # Notification handle = 0x0025 value: 9b ff 54 07
    def notification_loop( self ):
        while True:
	    try:
              pnum = self.con.expect('Notification handle = .*? \r', timeout=4)
            except pexpect.TIMEOUT:
              print "TIMEOUT exception!"
              break
	    if pnum==0:
                after = self.con.after
	        hxstr = after.split()[3:]
            	handle = long(float.fromhex(hxstr[0]))
            	#try:
	        if True:
                  self.cb[handle]([long(float.fromhex(n)) for n in hxstr[2:]])
            	#except:
                #  print "Error in callback for %x" % handle
                #  print sys.argv[1]
                pass
            else:
              print "TIMEOUT!!"
        pass

    def register_cb( self, handle, fn ):
        self.cb[handle]=fn;
        return

barometer = None
datalog = sys.stdout
xively_feed = None

def datalog_out(data):
    # The socket or output file might not be writeable
    # check with select so we don't block.
    (re,wr,ex) = select.select([],[datalog],[],0)
    if len(wr) > 0:
       datalog.write(json.dumps(data) + "\n")
       datalog.flush()
       pass
    return


class SensorCallbacks:

    #Set some dummy values so the first time we write data to Xively we've got all parameters.
    #Alternative is try,except when writing.
    data = {}
    data['t006']=100
    data['accl']=[0,0,0]
    data['humd']=[100,0]
    data['baro']=[100,0]
    data['magn']=[0,0,0]
    data['gyro']=[0,0,0]

    def __init__(self,addr):
        self.data['addr'] = addr

    def tmp006(self,v):
        objT = (v[1]<<8)+v[0]
        ambT = (v[3]<<8)+v[2]
        targetT = calcTmpTarget(objT, ambT)
        self.data['t006'] = targetT
        print "T006 %.1f" % targetT

    def accel(self,v):
        (xyz,mag) = calcAccel(v[0],v[1],v[2])
        self.data['accl'] = xyz
        print "ACCL", xyz

    def humidity(self, v):
        rawT = (v[1]<<8)+v[0]
        rawH = (v[3]<<8)+v[2]
        (t, rh) = calcHum(rawT, rawH)
        self.data['humd'] = [t, rh]
        print "HUMD %.1f" % rh

    def baro(self,v):
        global barometer
        global datalog
        rawT = (v[1]<<8)+v[0]
        rawP = (v[3]<<8)+v[2]
        (temp, pres) =  self.data['baro'] = barometer.calc(rawT, rawP)
        self.data['time'] = long(time.time() * 1000);
        print "BARO", temp, pres
        #datalog_out(self.data)
	xively_write(xively_feed, self.data)

    def magnet(self,v):
        x = (v[1]<<8)+v[0]
        y = (v[3]<<8)+v[2]
        z = (v[5]<<8)+v[4]
        xyz = calcMagn(x, y, z)
        self.data['magn'] = xyz
        print "MAGN", xyz

    def gyro(self,v):
        print "GYRO", v

def main():
    global datalog
    global barometer
    global xively_feed

    bluetooth_adr = sys.argv[1]
    if len(sys.argv) > 2:
        datalog = open(sys.argv[2], 'w+')

    xively_feed = xively_init()

    while True:

      tag = SensorTag(bluetooth_adr)
      cbs = SensorCallbacks(bluetooth_adr)

      # enable TMP006 sensor
      tag.register_cb(0x25,cbs.tmp006)
      tag.char_write_cmd(0x29,0x01)
      tag.char_write_cmd(0x26,0x0100)

      # enable accelerometer
      tag.register_cb(0x2d,cbs.accel)
      tag.char_write_cmd(0x31,0x01)
      tag.char_write_cmd(0x2e,0x0100)

      # enable humidity
      tag.register_cb(0x38, cbs.humidity)
      tag.char_write_cmd(0x3c,0x01)
      tag.char_write_cmd(0x39,0x0100)

      # enable magnetometer
      tag.register_cb(0x40,cbs.magnet)
      tag.char_write_cmd(0x44,0x01)
      tag.char_write_cmd(0x41,0x0100)

      # enable gyroscope
      tag.register_cb(0x57,cbs.gyro)
      tag.char_write_cmd(0x5b,0x07)
      tag.char_write_cmd(0x58,0x0100)

      # fetch barometer calibration
      tag.char_write_cmd(0x4f,0x02)
      rawcal = tag.char_read_hnd(0x52)
      barometer = Barometer( rawcal )
      # enable barometer
      tag.register_cb(0x4b,cbs.baro)
      tag.char_write_cmd(0x4f,0x01)
      tag.char_write_cmd(0x4c,0x0100)

      tag.notification_loop()

if __name__ == "__main__":
    main()


########NEW FILE########
__FILENAME__ = sensor_calcs
#
# Michael Saunby. April 2013   
# 
# Read temperature from the TMP006 sensor in the TI SensorTag.

# This algorithm borrowed from 
# http://processors.wiki.ti.com/index.php/SensorTag_User_Guide#Gatt_Server
# which most likely took it from the datasheet.  I've not checked it, other
# than noted that the temperature values I got seemed reasonable.
#
#   Copyright 2013 Michael Saunby
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.


tosigned = lambda n: float(n-0x10000) if n>0x7fff else float(n)
tosignedbyte = lambda n: float(n-0x100) if n>0x7f else float(n)

def calcTmpTarget(objT, ambT):
        
    objT = tosigned(objT)
    ambT = tosigned(ambT)

    m_tmpAmb = ambT/128.0
    Vobj2 = objT * 0.00000015625
    Tdie2 = m_tmpAmb + 273.15
    S0 = 6.4E-14            # Calibration factor
    a1 = 1.75E-3
    a2 = -1.678E-5
    b0 = -2.94E-5
    b1 = -5.7E-7
    b2 = 4.63E-9
    c2 = 13.4
    Tref = 298.15
    S = S0*(1+a1*(Tdie2 - Tref)+a2*pow((Tdie2 - Tref),2))
    Vos = b0 + b1*(Tdie2 - Tref) + b2*pow((Tdie2 - Tref),2)
    fObj = (Vobj2 - Vos) + c2*pow((Vobj2 - Vos),2)
    tObj = pow(pow(Tdie2,4) + (fObj/S),.25)
    tObj = (tObj - 273.15)
    return tObj

#
# Again from http://processors.wiki.ti.com/index.php/SensorTag_User_Guide#Gatt_Server
#
def calcHum(rawT, rawH):
    # -- calculate temperature [deg C] --
    t = -46.85 + 175.72/65536.0 * rawT

    rawH = float(int(rawH) & ~0x0003); # clear bits [1..0] (status bits)
    # -- calculate relative humidity [%RH] --
    rh = -6.0 + 125.0/65536.0 * rawH # RH= -6 + 125 * SRH/2^16
    return (t, rh)


#
# Again from http://processors.wiki.ti.com/index.php/SensorTag_User_Guide#Gatt_Server
# but combining all three values and giving magnitude.
# Magnitude tells us if we are at rest, falling, etc.

def calcAccel(rawX, rawY, rawZ):
    accel = lambda v: tosignedbyte(v) / 64.0  # Range -2G, +2G
    xyz = [accel(rawX), accel(rawY), accel(rawZ)]
    mag = (xyz[0]**2 + xyz[1]**2 + xyz[2]**2)**0.5
    return (xyz, mag)


#
# Again from http://processors.wiki.ti.com/index.php/SensorTag_User_Guide#Gatt_Server
# but combining all three values.
#

def calcMagn(rawX, rawY, rawZ):
    magforce = lambda v: (tosigned(v) * 1.0) / (65536.0/2000.0)
    return [magforce(rawX),magforce(rawY),magforce(rawZ)]


class Barometer:

# Ditto.
# Conversion algorithm for barometer temperature
# 
#  Formula from application note, rev_X:
#  Ta = ((c1 * Tr) / 2^24) + (c2 / 2^10)
#
#  c1 - c8: calibration coefficients the can be read from the sensor
#  c1 - c4: unsigned 16-bit integers
#  c5 - c8: signed 16-bit integers
#

    def calcBarTmp(self, raw_temp):
        c1 = self.m_barCalib.c1
        c2 = self.m_barCalib.c2
        val = long((c1 * raw_temp) * 100)
        temp = val >> 24
        val = long(c2 * 100)
        temp += (val >> 10)
        return float(temp) / 100.0


# Conversion algorithm for barometer pressure (hPa)
# 
# Formula from application note, rev_X:
# Sensitivity = (c3 + ((c4 * Tr) / 2^17) + ((c5 * Tr^2) / 2^34))
# Offset = (c6 * 2^14) + ((c7 * Tr) / 2^3) + ((c8 * Tr^2) / 2^19)
# Pa = (Sensitivity * Pr + Offset) / 2^14
#
    def calcBarPress(self,Tr,Pr):
        c3 = self.m_barCalib.c3
        c4 = self.m_barCalib.c4
        c5 = self.m_barCalib.c5
        c6 = self.m_barCalib.c6
        c7 = self.m_barCalib.c7
        c8 = self.m_barCalib.c8
    # Sensitivity
        s = long(c3)
        val = long(c4 * Tr)
        s += (val >> 17)
        val = long(c5 * Tr * Tr)
        s += (val >> 34)
    # Offset
        o = long(c6) << 14
        val = long(c7 * Tr)
        o += (val >> 3)
        val = long(c8 * Tr * Tr)
        o += (val >> 19)
    # Pressure (Pa)
        pres = ((s * Pr) + o) >> 14
        return float(pres)/100.0
    

    class Calib:

        # This works too
        # i = (hi<<8)+lo        
        def bld_int(self, lobyte, hibyte):
            return (lobyte & 0x0FF) + ((hibyte & 0x0FF) << 8)
        
        def __init__( self, pData ):
            self.c1 = self.bld_int(pData[0],pData[1])
            self.c2 = self.bld_int(pData[2],pData[3])
            self.c3 = self.bld_int(pData[4],pData[5])
            self.c4 = self.bld_int(pData[6],pData[7])
            self.c5 = tosigned(self.bld_int(pData[8],pData[9]))
            self.c6 = tosigned(self.bld_int(pData[10],pData[11]))
            self.c7 = tosigned(self.bld_int(pData[12],pData[13]))
            self.c8 = tosigned(self.bld_int(pData[14],pData[15]))
            

    def __init__(self, rawCalibration):
        self.m_barCalib = self.Calib( rawCalibration )
        return

    def calc(self,  rawT, rawP):
        self.m_raw_temp = tosigned(rawT)
        self.m_raw_pres = rawP # N.B.  Unsigned value
        bar_temp = self.calcBarTmp( self.m_raw_temp )
        bar_pres = self.calcBarPress( self.m_raw_temp, self.m_raw_pres )
        return( bar_temp, bar_pres)

        

########NEW FILE########
__FILENAME__ = xively_fns
#!/usr/bin/env python
# Michael Saunby. April 2014
#
#   Copyright 2014 Michael Saunby
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import xively
import datetime
import time
import os

def xively_init():
   print os.getenv('XIVELY_API_KEY')
   api = xively.XivelyAPIClient(os.getenv('XIVELY_API_KEY'))
   return api.feeds.get(os.getenv('XIVELY_FEED_ID'))


t006 = []
accl_x = []
accl_y = []
accl_z = []
humd_t = []
humd_rh = []
baro_t = []
baro_p = []
magn_x = []
magn_y = []
magn_z = []
gyro_x = []
gyro_y = []
gyro_z = []


def xively_write(feed, data):
  global t006, accl_x, accl_y, accl_z, humd_t, humd_rh, baro_t, baro_p, magn_x, magn_y, magn_z, gyro_x, gyro_y, gyro_z
  t006.append(xively.Datapoint(datetime.datetime.utcnow(), data['t006']))
  accl_x.append(xively.Datapoint(datetime.datetime.utcnow(), data['accl'][0]))
  accl_y.append(xively.Datapoint(datetime.datetime.utcnow(), data['accl'][1]))
  accl_z.append(xively.Datapoint(datetime.datetime.utcnow(), data['accl'][2]))
  humd_t.append(xively.Datapoint(datetime.datetime.utcnow(), data['humd'][0]))
  humd_rh.append(xively.Datapoint(datetime.datetime.utcnow(), data['humd'][1]))
  baro_t.append(xively.Datapoint(datetime.datetime.utcnow(), data['baro'][0]))
  baro_p.append(xively.Datapoint(datetime.datetime.utcnow(), data['baro'][1]))
  magn_x.append(xively.Datapoint(datetime.datetime.utcnow(), data['magn'][0]))
  magn_y.append(xively.Datapoint(datetime.datetime.utcnow(), data['magn'][1]))
  magn_z.append(xively.Datapoint(datetime.datetime.utcnow(), data['magn'][2]))
  #gyro_x.append(xively.Datapoint(datetime.datetime.utcnow(), data['gyro'][0]))
  #gyro_y.append(xively.Datapoint(datetime.datetime.utcnow(), data['gyro'][1]))
  #gyro_z.append(xively.Datapoint(datetime.datetime.utcnow(), data['gyro'][2]))

  if len(t006) < 10:
    return
  else:
    feed.datastreams = [
      xively.Datastream(id=  't006', datapoints=t006),
      xively.Datastream(id=  'accl_x', datapoints=accl_x),
      xively.Datastream(id=  'accl_y', datapoints=accl_y),
      xively.Datastream(id=  'accl_z', datapoints=accl_z),
      xively.Datastream(id=  'humd_t', datapoints=humd_t),
      xively.Datastream(id=  'humd_rh', datapoints=humd_rh),
      xively.Datastream(id=  'baro_t', datapoints=baro_t),
      xively.Datastream(id=  'baro_p', datapoints=baro_p),
      xively.Datastream(id=  'magn_x', datapoints=magn_x),
      xively.Datastream(id=  'magn_y', datapoints=magn_y),
      xively.Datastream(id=  'magn_z', datapoints=magn_z),
      #xively.Datastream(id=  'gyro_x', datapoints=gyro_x),
      #xively.Datastream(id=  'gyro_x', datapoints=gyro_y),
      #xively.Datastream(id=  'gyro_x', datapoints=gyro_z),
     # when dealing with single data values can do this instead -
     # xively.Datastream(id=  't006', current_value=data['t006'],  at=now),
    ]
    t006 = []
    accl_x = []
    accl_y = []
    accl_z = []
    humd_t = []
    humd_rh = []
    baro_t = []
    baro_p = []
    magn_x = []
    magn_y = []
    magn_z = []
    gyro_x = []
    gyro_y = []
    gyro_z = []
    feed.update()



########NEW FILE########
