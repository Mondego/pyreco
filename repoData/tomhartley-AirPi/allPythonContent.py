__FILENAME__ = airpi
#This file takes in inputs from a variety of sensor files, and outputs information to a variety of services
import sys
sys.dont_write_bytecode = True

import RPi.GPIO as GPIO
import ConfigParser
import time
import inspect
import os
from sys import exit
from sensors import sensor
from outputs import output

def get_subclasses(mod,cls):
	for name, obj in inspect.getmembers(mod):
		if hasattr(obj, "__bases__") and cls in obj.__bases__:
			return obj


if not os.path.isfile('sensors.cfg'):
	print "Unable to access config file: sensors.cfg"
	exit(1)

sensorConfig = ConfigParser.SafeConfigParser()
sensorConfig.read('sensors.cfg')

sensorNames = sensorConfig.sections()

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM) #Use BCM GPIO numbers.

sensorPlugins = []
for i in sensorNames:
	try:	
		try:
			filename = sensorConfig.get(i,"filename")
		except Exception:
			print("Error: no filename config option found for sensor plugin " + i)
			raise
		try:
			enabled = sensorConfig.getboolean(i,"enabled")
		except Exception:
			enabled = True

		#if enabled, load the plugin
		if enabled:
			try:
				mod = __import__('sensors.'+filename,fromlist=['a']) #Why does this work?
			except Exception:
				print("Error: could not import sensor module " + filename)
				raise

			try:	
				sensorClass = get_subclasses(mod,sensor.Sensor)
				if sensorClass == None:
					raise AttributeError
			except Exception:
				print("Error: could not find a subclass of sensor.Sensor in module " + filename)
				raise

			try:	
				reqd = sensorClass.requiredData
			except Exception:
				reqd =  []
			try:
				opt = sensorClass.optionalData
			except Exception:
				opt = []

			pluginData = {}

			class MissingField(Exception): pass
						
			for requiredField in reqd:
				if sensorConfig.has_option(i,requiredField):
					pluginData[requiredField]=sensorConfig.get(i,requiredField)
				else:
					print "Error: Missing required field '" + requiredField + "' for sensor plugin " + i
					raise MissingField
			for optionalField in opt:
				if sensorConfig.has_option(i,optionalField):
					pluginData[optionalField]=sensorConfig.get(i,optionalField)
			instClass = sensorClass(pluginData)
			sensorPlugins.append(instClass)
			print ("Success: Loaded sensor plugin " + i)
	except Exception as e: #add specific exception for missing module
		print("Error: Did not import sensor plugin " + i )
		raise e


if not os.path.isfile("outputs.cfg"):
	print "Unable to access config file: outputs.cfg"

outputConfig = ConfigParser.SafeConfigParser()
outputConfig.read("outputs.cfg")

outputNames = outputConfig.sections()

outputPlugins = []

for i in outputNames:
	try:	
		try:
			filename = outputConfig.get(i,"filename")
		except Exception:
			print("Error: no filename config option found for output plugin " + i)
			raise
		try:
			enabled = outputConfig.getboolean(i,"enabled")
		except Exception:
			enabled = True

		#if enabled, load the plugin
		if enabled:
			try:
				mod = __import__('outputs.'+filename,fromlist=['a']) #Why does this work?
			except Exception:
				print("Error: could not import output module " + filename)
				raise

			try:	
				outputClass = get_subclasses(mod,output.Output)
				if outputClass == None:
					raise AttributeError
			except Exception:
				print("Error: could not find a subclass of output.Output in module " + filename)
				raise
			try:	
				reqd = outputClass.requiredData
			except Exception:
				reqd =  []
			try:
				opt = outputClass.optionalData
			except Exception:
				opt = []
			
			if outputConfig.has_option(i,"async"):
				async = outputConfig.getbool(i,"async")
			else:
				async = False
			
			pluginData = {}

			class MissingField(Exception): pass
						
			for requiredField in reqd:
				if outputConfig.has_option(i,requiredField):
					pluginData[requiredField]=outputConfig.get(i,requiredField)
				else:
					print "Error: Missing required field '" + requiredField + "' for output plugin " + i
					raise MissingField
			for optionalField in opt:
				if outputConfig.has_option(i,optionalField):
					pluginData[optionalField]=outputConfig.get(i,optionalField)
			instClass = outputClass(pluginData)
			instClass.async = async
			outputPlugins.append(instClass)
			print ("Success: Loaded output plugin " + i)
	except Exception as e: #add specific exception for missing module
		print("Error: Did not import output plugin " + i )
		raise e

if not os.path.isfile("settings.cfg"):
	print "Unable to access config file: settings.cfg"

mainConfig = ConfigParser.SafeConfigParser()
mainConfig.read("settings.cfg")

lastUpdated = 0
delayTime = mainConfig.getfloat("Main","uploadDelay")
redPin = mainConfig.getint("Main","redPin")
greenPin = mainConfig.getint("Main","greenPin")
GPIO.setup(redPin,GPIO.OUT,initial=GPIO.LOW)
GPIO.setup(greenPin,GPIO.OUT,initial=GPIO.LOW)
while True:
	curTime = time.time()
	if (curTime-lastUpdated)>delayTime:
		lastUpdated = curTime
		data = []
		#Collect the data from each sensor
		for i in sensorPlugins:
			dataDict = {}
			val = i.getVal()
			if val==None: #this means it has no data to upload.
				continue
			dataDict["value"] = i.getVal()
			dataDict["unit"] = i.valUnit
			dataDict["symbol"] = i.valSymbol
			dataDict["name"] = i.valName
			dataDict["sensor"] = i.sensorName
			data.append(dataDict)
		working = True
		for i in outputPlugins:
			working = working and i.outputData(data)
		if working:
			print "Uploaded successfully"
			GPIO.output(greenPin,GPIO.HIGH)
		else:
			print "Failed to upload"
			GPIO.output(redPin,GPIO.HIGH)
		time.sleep(1)
		GPIO.output(greenPin,GPIO.LOW)
		GPIO.output(redPin,GPIO.LOW)

########NEW FILE########
__FILENAME__ = output
class Output():
	def __init__(self,data):
		raise NotImplementedError
	
	def outputData(self,dataPoints):
		raise NotImplementedError

########NEW FILE########
__FILENAME__ = print
import output
import datetime

class Print(output.Output):
	requiredData = []
	optionalData = []
	def __init__(self,data):
		pass
	def outputData(self,dataPoints):
		print ""
		print "Time: " + str(datetime.datetime.now())
		for i in dataPoints:
			print i["name"] + ": " + str(i["value"]) + " " + i["symbol"]
		return True

########NEW FILE########
__FILENAME__ = xively
import output
import requests
import json

class Xively(output.Output):
	requiredData = ["APIKey","FeedID"]
	optionalData = []
	def __init__(self,data):
		self.APIKey=data["APIKey"]
		self.FeedID=data["FeedID"]
	def outputData(self,dataPoints):
		arr = []
		for i in dataPoints:
			arr.append({"id":i["name"],"current_value":i["value"]})
		a = json.dumps({"version":"1.0.0","datastreams":arr})
		try:
			z = requests.put("https://api.xively.com/v2/feeds/"+self.FeedID+".json",headers={"X-ApiKey":self.APIKey},data=a)
			if z.text!="": 
				print "Xively Error: " + z.text
				return False
		except Exception:
			return False
		return True

########NEW FILE########
__FILENAME__ = Adafruit_I2C
#!/usr/bin/python

import smbus

# ===========================================================================
# Adafruit_I2C Base Class
# ===========================================================================

class Adafruit_I2C :

  def __init__(self, address, bus=0, debug=False):
    self.address = address
    self.bus = smbus.SMBus(bus)
    self.debug = debug

  def reverseByteOrder(self, data):
    "Reverses the byte order of an int (16-bit) or long (32-bit) value"
    # Courtesy Vishal Sapre
    dstr = hex(data)[2:].replace('L','')
    byteCount = len(dstr[::2])
    val = 0
    for i, n in enumerate(range(byteCount)):
      d = data & 0xFF
      val |= (d << (8 * (byteCount - i - 1)))
      data >>= 8
    return val

  def write8(self, reg, value):
    "Writes an 8-bit value to the specified register/address"
    try:
      self.bus.write_byte_data(self.address, reg, value)
      if (self.debug):
        print("I2C: Wrote 0x%02X to register 0x%02X" % (value, reg))
    except IOError, err:
      print "Error accessing 0x%02X: Check your I2C address" % self.address
      return -1

  def writeList(self, reg, list):
    "Writes an array of bytes using I2C format"
    try:
      self.bus.write_i2c_block_data(self.address, reg, list)
    except IOError, err:
      print "Error accessing 0x%02X: Check your I2C address" % self.address
      return -1

  def readU8(self, reg):
    "Read an unsigned byte from the I2C device"
    try:
      result = self.bus.read_byte_data(self.address, reg)
      if (self.debug):
        print "I2C: Device 0x%02X returned 0x%02X from reg 0x%02X" % (self.address, result & 0xFF, reg)
      return result
    except IOError, err:
      print "Error accessing 0x%02X: Check your I2C address" % self.address
      return -1

  def readS8(self, reg):
    "Reads a signed byte from the I2C device"
    try:
      result = self.bus.read_byte_data(self.address, reg)
      if (self.debug):
        print "I2C: Device 0x%02X returned 0x%02X from reg 0x%02X" % (self.address, result & 0xFF, reg)
      if (result > 127):
        return result - 256
      else:
        return result
    except IOError, err:
      print "Error accessing 0x%02X: Check your I2C address" % self.address
      return -1

  def readU16(self, reg):
    "Reads an unsigned 16-bit value from the I2C device"
    try:
      hibyte = self.bus.read_byte_data(self.address, reg)
      result = (hibyte << 8) + self.bus.read_byte_data(self.address, reg+1)
      if (self.debug):
        print "I2C: Device 0x%02X returned 0x%04X from reg 0x%02X" % (self.address, result & 0xFFFF, reg)
      return result
    except IOError, err:
      print "Error accessing 0x%02X: Check your I2C address" % self.address
      return -1

  def readS16(self, reg):
    "Reads a signed 16-bit value from the I2C device"
    try:
      hibyte = self.bus.read_byte_data(self.address, reg)
      if (hibyte > 127):
        hibyte -= 256
      result = (hibyte << 8) + self.bus.read_byte_data(self.address, reg+1)
      if (self.debug):
        print "I2C: Device 0x%02X returned 0x%04X from reg 0x%02X" % (self.address, result & 0xFFFF, reg)
      return result
    except IOError, err:
      print "Error accessing 0x%02X: Check your I2C address" % self.address
      return -1

########NEW FILE########
__FILENAME__ = analogue
import mcp3008
import sensor
class Analogue(sensor.Sensor):
	requiredData = ["adcPin","measurement","sensorName"]
	optionalData = ["pullUpResistance","pullDownResistance"]
	def __init__(self, data):
		self.adc = mcp3008.MCP3008.sharedClass
		self.adcPin = int(data["adcPin"])
		self.valName = data["measurement"]
		self.sensorName = data["sensorName"]
		self.pullUp, self.pullDown = None, None
		if "pullUpResistance" in data:
			self.pullUp = int(data["pullUpResistance"])
		if "pullDownResistance" in data:
			self.pullDown = int(data["pullDownResistance"])
		class ConfigError(Exception): pass
		if self.pullUp!=None and self.pullDown!=None:
			print "Please choose whether there is a pull up or pull down resistor for the " + self.valName + " measurement by only entering one of them into the settings file"
			raise ConfigError
		self.valUnit = "Ohms"
		self.valSymbol = "Ohms"
		if self.pullUp==None and self.pullDown==None:
			self.valUnit = "millvolts"
			self.valSymbol = "mV"
		
	def getVal(self):
		result = self.adc.readADC(self.adcPin)
		if result==0:
			print "Check wiring for the " + self.sensorName + " measurement, no voltage detected on ADC input " + str(self.adcPin)
			return None
		if result == 1023:
			print "Check wiring for the " + self.sensorName + " measurement, full voltage detected on ADC input " + str(self.adcPin)
			return None
		vin = 3.3
		vout = float(result)/1023 * vin
		
		if self.pullDown!=None:
			#Its a pull down resistor
			resOut = (self.pullDown*vin)/vout - self.pullDown
		elif self.pullUp!=None:
			resOut = self.pullUp/((vin/vout)-1)
		else:
			resOut = vout*1000
		return resOut
		

########NEW FILE########
__FILENAME__ = bmp085
import sensor
import bmpBackend

class BMP085(sensor.Sensor):
	bmpClass = None
	requiredData = ["measurement","i2cbus"]
	optionalData = ["altitude","mslp","unit"]
	def __init__(self,data):
		self.sensorName = "BMP085"
		if "temp" in data["measurement"].lower():
			self.valName = "Temperature"
			self.valUnit = "Celsius"
			self.valSymbol = "C"
			if "unit" in data:
				if data["unit"]=="F":
					self.valUnit = "Fahrenheit"
					self.valSymbol = "F"
		elif "pres" in data["measurement"].lower():
			self.valName = "Pressure"
			self.valSymbol = "hPa"
			self.valUnit = "Hectopascal"
			self.altitude = 0
			self.mslp = False
			if "mslp" in data:
				if data["mslp"].lower in ["on","true","1","yes"]:
					self.mslp = True
					if "altitude" in data:
						self.altitude=data["altitude"]
					else:
						print "To calculate MSLP, please provide an 'altitude' config setting (in m) for the BMP085 pressure module"
						self.mslp = False
		if (BMP085.bmpClass==None):
			BMP085.bmpClass = bmpBackend.BMP085(bus=int(data["i2cbus"]))
		return

	def getVal(self):
		if self.valName == "Temperature":
			temp = BMP085.bmpClass.readTemperature()
			if self.valUnit == "Fahrenheit":
				temp = temp * 1.8 + 32
			return temp
		elif self.valName == "Pressure":
			if self.mslp:
				return BMP085.bmpClass.readMSLPressure(self.altitude) * 0.01 #to convert to Hectopascals
			else:
				return BMP085.bmpClass.readPressure() * 0.01 #to convert to Hectopascals

########NEW FILE########
__FILENAME__ = bmpBackend
#!/usr/bin/python

import time
import math

from Adafruit_I2C import Adafruit_I2C

# ===========================================================================
# BMP085 Class
# ===========================================================================

class BMP085 :
  i2c = None

  # Operating Modes
  __BMP085_ULTRALOWPOWER     = 0
  __BMP085_STANDARD          = 1
  __BMP085_HIGHRES           = 2
  __BMP085_ULTRAHIGHRES      = 3

  # BMP085 Registers
  __BMP085_CAL_AC1           = 0xAA  # R   Calibration data (16 bits)
  __BMP085_CAL_AC2           = 0xAC  # R   Calibration data (16 bits)
  __BMP085_CAL_AC3           = 0xAE  # R   Calibration data (16 bits)
  __BMP085_CAL_AC4           = 0xB0  # R   Calibration data (16 bits)
  __BMP085_CAL_AC5           = 0xB2  # R   Calibration data (16 bits)
  __BMP085_CAL_AC6           = 0xB4  # R   Calibration data (16 bits)
  __BMP085_CAL_B1            = 0xB6  # R   Calibration data (16 bits)
  __BMP085_CAL_B2            = 0xB8  # R   Calibration data (16 bits)
  __BMP085_CAL_MB            = 0xBA  # R   Calibration data (16 bits)
  __BMP085_CAL_MC            = 0xBC  # R   Calibration data (16 bits)
  __BMP085_CAL_MD            = 0xBE  # R   Calibration data (16 bits)
  __BMP085_CONTROL           = 0xF4
  __BMP085_TEMPDATA          = 0xF6
  __BMP085_PRESSUREDATA      = 0xF6
  __BMP085_READTEMPCMD       = 0x2E
  __BMP085_READPRESSURECMD   = 0x34

  # Private Fields
  _cal_AC1 = 0
  _cal_AC2 = 0
  _cal_AC3 = 0
  _cal_AC4 = 0
  _cal_AC5 = 0
  _cal_AC6 = 0
  _cal_B1 = 0
  _cal_B2 = 0
  _cal_MB = 0
  _cal_MC = 0
  _cal_MD = 0

  # Constructor
  def __init__(self, address=0x77, mode=1, bus=0, debug=False):
    self.i2c = Adafruit_I2C(address, bus)

    self.address = address
    self.debug = debug
    # Make sure the specified mode is in the appropriate range
    if ((mode < 0) | (mode > 3)):
      if (self.debug):
        print "Invalid Mode: Using STANDARD by default"
      self.mode = self.__BMP085_STANDARD
    else:
      self.mode = mode
    # Read the calibration data
    self.readCalibrationData()

  def readCalibrationData(self):
    "Reads the calibration data from the IC"
    self._cal_AC1 = self.i2c.readS16(self.__BMP085_CAL_AC1)   # INT16
    self._cal_AC2 = self.i2c.readS16(self.__BMP085_CAL_AC2)   # INT16
    self._cal_AC3 = self.i2c.readS16(self.__BMP085_CAL_AC3)   # INT16
    self._cal_AC4 = self.i2c.readU16(self.__BMP085_CAL_AC4)   # UINT16
    self._cal_AC5 = self.i2c.readU16(self.__BMP085_CAL_AC5)   # UINT16
    self._cal_AC6 = self.i2c.readU16(self.__BMP085_CAL_AC6)   # UINT16
    self._cal_B1 = self.i2c.readS16(self.__BMP085_CAL_B1)     # INT16
    self._cal_B2 = self.i2c.readS16(self.__BMP085_CAL_B2)     # INT16
    self._cal_MB = self.i2c.readS16(self.__BMP085_CAL_MB)     # INT16
    self._cal_MC = self.i2c.readS16(self.__BMP085_CAL_MC)     # INT16
    self._cal_MD = self.i2c.readS16(self.__BMP085_CAL_MD)     # INT16
    if (self.debug):
      self.showCalibrationData()

  def showCalibrationData(self):
      "Displays the calibration values for debugging purposes"
      print "DBG: AC1 = %6d" % (self._cal_AC1)
      print "DBG: AC2 = %6d" % (self._cal_AC2)
      print "DBG: AC3 = %6d" % (self._cal_AC3)
      print "DBG: AC4 = %6d" % (self._cal_AC4)
      print "DBG: AC5 = %6d" % (self._cal_AC5)
      print "DBG: AC6 = %6d" % (self._cal_AC6)
      print "DBG: B1  = %6d" % (self._cal_B1)
      print "DBG: B2  = %6d" % (self._cal_B2)
      print "DBG: MB  = %6d" % (self._cal_MB)
      print "DBG: MC  = %6d" % (self._cal_MC)
      print "DBG: MD  = %6d" % (self._cal_MD)

  def readRawTemp(self):
    "Reads the raw (uncompensated) temperature from the sensor"
    self.i2c.write8(self.__BMP085_CONTROL, self.__BMP085_READTEMPCMD)
    time.sleep(0.005)  # Wait 5ms
    raw = self.i2c.readU16(self.__BMP085_TEMPDATA)
    if (self.debug):
      print "DBG: Raw Temp: 0x%04X (%d)" % (raw & 0xFFFF, raw)
    return raw

  def readRawPressure(self):
    "Reads the raw (uncompensated) pressure level from the sensor"
    self.i2c.write8(self.__BMP085_CONTROL, self.__BMP085_READPRESSURECMD + (self.mode << 6))
    if (self.mode == self.__BMP085_ULTRALOWPOWER):
      time.sleep(0.005)
    elif (self.mode == self.__BMP085_HIGHRES):
      time.sleep(0.014)
    elif (self.mode == self.__BMP085_ULTRAHIGHRES):
      time.sleep(0.026)
    else:
      time.sleep(0.008)
    msb = self.i2c.readU8(self.__BMP085_PRESSUREDATA)
    lsb = self.i2c.readU8(self.__BMP085_PRESSUREDATA+1)
    xlsb = self.i2c.readU8(self.__BMP085_PRESSUREDATA+2)
    raw = ((msb << 16) + (lsb << 8) + xlsb) >> (8 - self.mode)
    if (self.debug):
      print "DBG: Raw Pressure: 0x%04X (%d)" % (raw & 0xFFFF, raw)
    return raw

  def readTemperature(self):
    "Gets the compensated temperature in degrees celcius"
    UT = 0
    X1 = 0
    X2 = 0
    B5 = 0
    temp = 0.0

    # Read raw temp before aligning it with the calibration values
    UT = self.readRawTemp()
    X1 = ((UT - self._cal_AC6) * self._cal_AC5) >> 15
    X2 = (self._cal_MC << 11) / (X1 + self._cal_MD)
    B5 = X1 + X2
    temp = ((B5 + 8) >> 4) / 10.0
    if (self.debug):
      print "DBG: Calibrated temperature = %f C" % temp
    return temp

  def readPressure(self):
    "Gets the compensated pressure in pascal"
    UT = 0
    UP = 0
    B3 = 0
    B5 = 0
    B6 = 0
    X1 = 0
    X2 = 0
    X3 = 0
    p = 0
    B4 = 0
    B7 = 0

    UT = self.readRawTemp()
    UP = self.readRawPressure()

    # You can use the datasheet values to test the conversion results
    # dsValues = True
    dsValues = False

    if (dsValues):
      UT = 27898
      UP = 23843
      self._cal_AC6 = 23153
      self._cal_AC5 = 32757
      self._cal_MC = -8711
      self._cal_MD = 2868
      self._cal_B1 = 6190
      self._cal_B2 = 4
      self._cal_AC3 = -14383
      self._cal_AC2 = -72
      self._cal_AC1 = 408
      self._cal_AC4 = 32741
      self.mode = self.__BMP085_ULTRALOWPOWER
      if (self.debug):
        self.showCalibrationData()

    # True Temperature Calculations
    X1 = ((UT - self._cal_AC6) * self._cal_AC5) >> 15
    X2 = (self._cal_MC << 11) / (X1 + self._cal_MD)
    B5 = X1 + X2
    if (self.debug):
      print "DBG: X1 = %d" % (X1)
      print "DBG: X2 = %d" % (X2)
      print "DBG: B5 = %d" % (B5)
      print "DBG: True Temperature = %.2f C" % (((B5 + 8) >> 4) / 10.0)

    # Pressure Calculations
    B6 = B5 - 4000
    X1 = (self._cal_B2 * (B6 * B6) >> 12) >> 11
    X2 = (self._cal_AC2 * B6) >> 11
    X3 = X1 + X2
    B3 = (((self._cal_AC1 * 4 + X3) << self.mode) + 2) / 4
    if (self.debug):
      print "DBG: B6 = %d" % (B6)
      print "DBG: X1 = %d" % (X1)
      print "DBG: X2 = %d" % (X2)
      print "DBG: B3 = %d" % (B3)

    X1 = (self._cal_AC3 * B6) >> 13
    X2 = (self._cal_B1 * ((B6 * B6) >> 12)) >> 16
    X3 = ((X1 + X2) + 2) >> 2
    B4 = (self._cal_AC4 * (X3 + 32768)) >> 15
    B7 = (UP - B3) * (50000 >> self.mode)
    if (self.debug):
      print "DBG: X1 = %d" % (X1)
      print "DBG: X2 = %d" % (X2)
      print "DBG: B4 = %d" % (B4)
      print "DBG: B7 = %d" % (B7)

    if (B7 < 0x80000000):
      p = (B7 * 2) / B4
    else:
      p = (B7 / B4) * 2

    X1 = (p >> 8) * (p >> 8)
    X1 = (X1 * 3038) >> 16
    X2 = (-7375 * p) >> 16
    if (self.debug):
      print "DBG: p  = %d" % (p)
      print "DBG: X1 = %d" % (X1)
      print "DBG: X2 = %d" % (X2)

    p = p + ((X1 + X2 + 3791) >> 4)
    if (self.debug):
      print "DBG: Pressure = %d Pa" % (p)

    return p

  def readAltitude(self, seaLevelPressure=101325):
    "Calculates the altitude in meters"
    altitude = 0.0
    pressure = float(self.readPressure())
    altitude = 44330.0 * (1.0 - pow(pressure / seaLevelPressure, 0.1903))
    if (self.debug):
      print "DBG: Altitude = %d" % (altitude)
    return altitude

    return 0

  def readMSLPressure(self, altitude):
    "Calculates the mean sea level pressure"
    pressure = float(self.readPressure())
    T0 = float(altitude) / 44330
    T1 = math.pow(1 - T0, 5.255)
    mslpressure = pressure / T1
    return mslpressure

if __name__=="__main__":
	bmp = BMP085()
	print str(bmp.readTemperature()) + " C"
	print str(bmp.readPressure()) + " Pa"

########NEW FILE########
__FILENAME__ = dht22
import sensor
import dhtreader
import time
class DHT22(sensor.Sensor):
	requiredData = ["measurement","pinNumber"]
	optionalData = ["unit"]
	def __init__(self,data):
		dhtreader.init()
		dhtreader.lastDataTime = 0
		dhtreader.lastData = (None,None)
		self.sensorName = "DHT22"
		self.pinNum = int(data["pinNumber"])
		if "temp" in data["measurement"].lower():
			self.valName = "Temperature"
			self.valUnit = "Celsius"
			self.valSymbol = "C"
			if "unit" in data:
				if data["unit"]=="F":
					self.valUnit = "Fahrenheit"
					self.valSymbol = "F"
		elif "h" in data["measurement"].lower():
			self.valName = "Relative_Humidity"
			self.valSymbol = "%"
			self.valUnit = "% Relative Humidity"
		return

	def getVal(self):
		tm = dhtreader.lastDataTime
		if (time.time()-tm)<2:
			t, h = dhtreader.lastData
		else:
			tim = time.time()
			try:
				t, h = dhtreader.read(22,self.pinNum)
			except Exception:
				t, h = dhtreader.lastData
			dhtreader.lastData = (t,h)
			dhtreader.lastDataTime=tim
		if self.valName == "Temperature":
			temp = t
			if self.valUnit == "Fahrenheit":
				temp = temp * 1.8 + 32
			return temp
		elif self.valName == "Relative_Humidity":
			return h

########NEW FILE########
__FILENAME__ = mcp3008
#!/usr/bin/python

import RPi.GPIO as GPIO
import sensor

class MCP3008(sensor.Sensor):
	requiredData = []
	optionalData = ["mosiPin","misoPin","csPin","clkPin"]
	sharedClass = None
	def __init__(self, data):
		GPIO.setmode(GPIO.BCM)
		GPIO.setwarnings(False)
		self.SPIMOSI = 23
		self.SPIMISO = 24
		self.SPICLK = 18
		self.SPICS = 25
		if "mosiPin" in data:
			self.SPIMOSI = data["mosiPin"]
		if "misoPin" in data:
			self.SPIMISO = data["misoPin"]
		if "clkPin" in data:
			self.SPICLK = data["clkPin"]
		if "csPin" in data:
			self.SPICS = data["csPin"] 
		GPIO.setup(self.SPIMOSI, GPIO.OUT)
		GPIO.setup(self.SPIMISO, GPIO.IN)
		GPIO.setup(self.SPICLK, GPIO.OUT)
		GPIO.setup(self.SPICS, GPIO.OUT)
		if MCP3008.sharedClass == None:
			MCP3008.sharedClass = self

	#read SPI data from MCP3008 chip, 8 possible adc's (0 thru 7)
	def readADC(self,adcnum):
		if ((adcnum > 7) or (adcnum < 0)):
			return -1
		GPIO.output(self.SPICS, True)

		GPIO.output(self.SPICLK, False)  # start clock low
		GPIO.output(self.SPICS, False)     # bring CS low

		commandout = adcnum
		commandout |= 0x18  # start bit + single-ended bit
		commandout <<= 3    # we only need to send 5 bits here
		for i in range(5):
			if (commandout & 0x80):
				GPIO.output(self.SPIMOSI, True)
			else:
	   			GPIO.output(self.SPIMOSI, False)
	                commandout <<= 1
	                GPIO.output(self.SPICLK, True)
	                GPIO.output(self.SPICLK, False)

		adcout = 0
		# read in one empty bit, one null bit and 10 ADC bits
		for i in range(11):
			GPIO.output(self.SPICLK, True)
			GPIO.output(self.SPICLK, False)
			adcout <<= 1
			if (GPIO.input(self.SPIMISO)):
				adcout |= 0x1

		GPIO.output(self.SPICS, True)
		return adcout
	
	def getVal(self):
		return None #not that kind of plugin, this is to be used by other plugins

########NEW FILE########
__FILENAME__ = sensor
class Sensor():
	def __init__(data):
		raise NotImplementedError
	
	def getData():
		raise NotImplementedError

########NEW FILE########
