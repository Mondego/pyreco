__FILENAME__ = Adafruit_ADS1x15
#!/usr/bin/python

import time
import smbus
from Adafruit_I2C import Adafruit_I2C

# ===========================================================================
# ADS1x15 Class
#
# Originally written by K. Townsend, Adafruit (https://github.com/adafruit/Adafruit-Raspberry-Pi-Python-Code/tree/master/Adafruit_ADS1x15)
# Updates and new functions implementation by Pedro Villanueva, 03/2013.
# The only error in the original code was in line 57:
#              __ADS1015_REG_CONFIG_DR_920SPS    = 0x0050
# should be 
#              __ADS1015_REG_CONFIG_DR_920SPS    = 0x0060     
#
# NOT IMPLEMENTED: Conversion ready pin, page 15 datasheet.
# ===========================================================================

class ADS1x15:
  i2c = None

  # IC Identifiers
  __IC_ADS1015                      = 0x00
  __IC_ADS1115                      = 0x01

  # Pointer Register
  __ADS1015_REG_POINTER_MASK        = 0x03
  __ADS1015_REG_POINTER_CONVERT     = 0x00
  __ADS1015_REG_POINTER_CONFIG      = 0x01
  __ADS1015_REG_POINTER_LOWTHRESH   = 0x02
  __ADS1015_REG_POINTER_HITHRESH    = 0x03

  # Config Register
  __ADS1015_REG_CONFIG_OS_MASK      = 0x8000
  __ADS1015_REG_CONFIG_OS_SINGLE    = 0x8000  # Write: Set to start a single-conversion
  __ADS1015_REG_CONFIG_OS_BUSY      = 0x0000  # Read: Bit = 0 when conversion is in progress
  __ADS1015_REG_CONFIG_OS_NOTBUSY   = 0x8000  # Read: Bit = 1 when device is not performing a conversion

  __ADS1015_REG_CONFIG_MUX_MASK     = 0x7000
  __ADS1015_REG_CONFIG_MUX_DIFF_0_1 = 0x0000  # Differential P = AIN0, N = AIN1 (default)
  __ADS1015_REG_CONFIG_MUX_DIFF_0_3 = 0x1000  # Differential P = AIN0, N = AIN3
  __ADS1015_REG_CONFIG_MUX_DIFF_1_3 = 0x2000  # Differential P = AIN1, N = AIN3
  __ADS1015_REG_CONFIG_MUX_DIFF_2_3 = 0x3000  # Differential P = AIN2, N = AIN3
  __ADS1015_REG_CONFIG_MUX_SINGLE_0 = 0x4000  # Single-ended AIN0
  __ADS1015_REG_CONFIG_MUX_SINGLE_1 = 0x5000  # Single-ended AIN1
  __ADS1015_REG_CONFIG_MUX_SINGLE_2 = 0x6000  # Single-ended AIN2
  __ADS1015_REG_CONFIG_MUX_SINGLE_3 = 0x7000  # Single-ended AIN3

  __ADS1015_REG_CONFIG_PGA_MASK     = 0x0E00
  __ADS1015_REG_CONFIG_PGA_6_144V   = 0x0000  # +/-6.144V range
  __ADS1015_REG_CONFIG_PGA_4_096V   = 0x0200  # +/-4.096V range
  __ADS1015_REG_CONFIG_PGA_2_048V   = 0x0400  # +/-2.048V range (default)
  __ADS1015_REG_CONFIG_PGA_1_024V   = 0x0600  # +/-1.024V range
  __ADS1015_REG_CONFIG_PGA_0_512V   = 0x0800  # +/-0.512V range
  __ADS1015_REG_CONFIG_PGA_0_256V   = 0x0A00  # +/-0.256V range

  __ADS1015_REG_CONFIG_MODE_MASK    = 0x0100
  __ADS1015_REG_CONFIG_MODE_CONTIN  = 0x0000  # Continuous conversion mode
  __ADS1015_REG_CONFIG_MODE_SINGLE  = 0x0100  # Power-down single-shot mode (default)

  __ADS1015_REG_CONFIG_DR_MASK      = 0x00E0  
  __ADS1015_REG_CONFIG_DR_128SPS    = 0x0000  # 128 samples per second
  __ADS1015_REG_CONFIG_DR_250SPS    = 0x0020  # 250 samples per second
  __ADS1015_REG_CONFIG_DR_490SPS    = 0x0040  # 490 samples per second
  __ADS1015_REG_CONFIG_DR_920SPS    = 0x0060  # 920 samples per second
  __ADS1015_REG_CONFIG_DR_1600SPS   = 0x0080  # 1600 samples per second (default)
  __ADS1015_REG_CONFIG_DR_2400SPS   = 0x00A0  # 2400 samples per second
  __ADS1015_REG_CONFIG_DR_3300SPS   = 0x00C0  # 3300 samples per second (also 0x00E0)

  __ADS1115_REG_CONFIG_DR_8SPS      = 0x0000  # 8 samples per second
  __ADS1115_REG_CONFIG_DR_16SPS     = 0x0020  # 16 samples per second
  __ADS1115_REG_CONFIG_DR_32SPS     = 0x0040  # 32 samples per second
  __ADS1115_REG_CONFIG_DR_64SPS     = 0x0060  # 64 samples per second
  __ADS1115_REG_CONFIG_DR_128SPS    = 0x0080  # 128 samples per second
  __ADS1115_REG_CONFIG_DR_250SPS    = 0x00A0  # 250 samples per second (default)
  __ADS1115_REG_CONFIG_DR_475SPS    = 0x00C0  # 475 samples per second
  __ADS1115_REG_CONFIG_DR_860SPS    = 0x00E0  # 860 samples per second

  __ADS1015_REG_CONFIG_CMODE_MASK   = 0x0010
  __ADS1015_REG_CONFIG_CMODE_TRAD   = 0x0000  # Traditional comparator with hysteresis (default)
  __ADS1015_REG_CONFIG_CMODE_WINDOW = 0x0010  # Window comparator

  __ADS1015_REG_CONFIG_CPOL_MASK    = 0x0008
  __ADS1015_REG_CONFIG_CPOL_ACTVLOW = 0x0000  # ALERT/RDY pin is low when active (default)
  __ADS1015_REG_CONFIG_CPOL_ACTVHI  = 0x0008  # ALERT/RDY pin is high when active

  __ADS1015_REG_CONFIG_CLAT_MASK    = 0x0004  # Determines if ALERT/RDY pin latches once asserted
  __ADS1015_REG_CONFIG_CLAT_NONLAT  = 0x0000  # Non-latching comparator (default)
  __ADS1015_REG_CONFIG_CLAT_LATCH   = 0x0004  # Latching comparator

  __ADS1015_REG_CONFIG_CQUE_MASK    = 0x0003
  __ADS1015_REG_CONFIG_CQUE_1CONV   = 0x0000  # Assert ALERT/RDY after one conversions
  __ADS1015_REG_CONFIG_CQUE_2CONV   = 0x0001  # Assert ALERT/RDY after two conversions
  __ADS1015_REG_CONFIG_CQUE_4CONV   = 0x0002  # Assert ALERT/RDY after four conversions
  __ADS1015_REG_CONFIG_CQUE_NONE    = 0x0003  # Disable the comparator and put ALERT/RDY in high state (default)
  
  
  # Dictionaries with the sampling speed values
  # These simplify and clean the code (avoid the abuse of if/elif/else clauses)
  spsADS1115 = {
    8:__ADS1115_REG_CONFIG_DR_8SPS,
    16:__ADS1115_REG_CONFIG_DR_16SPS,
    32:__ADS1115_REG_CONFIG_DR_32SPS,
    64:__ADS1115_REG_CONFIG_DR_64SPS,
    128:__ADS1115_REG_CONFIG_DR_128SPS,
    250:__ADS1115_REG_CONFIG_DR_250SPS,
    475:__ADS1115_REG_CONFIG_DR_475SPS,
    860:__ADS1115_REG_CONFIG_DR_860SPS
  }    
  spsADS1015 = {
    128:__ADS1015_REG_CONFIG_DR_128SPS,
    250:__ADS1015_REG_CONFIG_DR_250SPS,
    490:__ADS1015_REG_CONFIG_DR_490SPS,
    920:__ADS1015_REG_CONFIG_DR_920SPS,
    1600:__ADS1015_REG_CONFIG_DR_1600SPS,
    2400:__ADS1015_REG_CONFIG_DR_2400SPS,
    3300:__ADS1015_REG_CONFIG_DR_3300SPS
  }
  # Dictionariy with the programable gains
  pgaADS1x15 = {
    6144:__ADS1015_REG_CONFIG_PGA_6_144V,
    4096:__ADS1015_REG_CONFIG_PGA_4_096V,
    2048:__ADS1015_REG_CONFIG_PGA_2_048V,
    1024:__ADS1015_REG_CONFIG_PGA_1_024V,
    512:__ADS1015_REG_CONFIG_PGA_0_512V,
    256:__ADS1015_REG_CONFIG_PGA_0_256V
  }    
  

  # Constructor
  def __init__(self, address=0x48, ic=__IC_ADS1015, debug=False):
    # Depending on if you have an old or a new Raspberry Pi, you
    # may need to change the I2C bus.  Older Pis use SMBus 0,
    # whereas new Pis use SMBus 1.  If you see an error like:
    # 'Error accessing 0x48: Check your I2C address '
    # change the SMBus number in the initializer below!
    self.i2c = Adafruit_I2C(address)
    self.address = address
    self.debug = debug

    # Make sure the IC specified is valid
    if ((ic < self.__IC_ADS1015) | (ic > self.__IC_ADS1115)):
      if (self.debug):
        print "ADS1x15: Invalid IC specfied: %h" % ic
      return -1
    else:
      self.ic = ic
        
    # Set pga value, so that getLastConversionResult() can use it,
    # any function that accepts a pga value must update this.
    self.pga = 6144    
  
    
  def readADCSingleEnded(self, channel=0, pga=6144, sps=250):
    "Gets a single-ended ADC reading from the specified channel in mV. \
    The sample rate for this mode (single-shot) can be used to lower the noise \
    (low sps) or to lower the power consumption (high sps) by duty cycling, \
    see datasheet page 14 for more info. \
    The pga must be given in mV, see page 13 for the supported values."
    
    # With invalid channel return -1
    if (channel > 3):
      if (self.debug):
        print "ADS1x15: Invalid channel specified: %d" % channel
      return -1
    
    # Disable comparator, Non-latching, Alert/Rdy active low
    # traditional comparator, single-shot mode
    config = self.__ADS1015_REG_CONFIG_CQUE_NONE    | \
             self.__ADS1015_REG_CONFIG_CLAT_NONLAT  | \
             self.__ADS1015_REG_CONFIG_CPOL_ACTVLOW | \
             self.__ADS1015_REG_CONFIG_CMODE_TRAD   | \
             self.__ADS1015_REG_CONFIG_MODE_SINGLE    

    # Set sample per seconds, defaults to 250sps
    # If sps is in the dictionary (defined in init) it returns the value of the constant
    # othewise it returns the value for 250sps. This saves a lot of if/elif/else code!
    if (self.ic == self.__IC_ADS1015):
      config |= self.spsADS1015.setdefault(sps, self.__ADS1015_REG_CONFIG_DR_1600SPS)
    else:
      if ( (sps not in self.spsADS1115) & self.debug):	  
	print "ADS1x15: Invalid pga specified: %d, using 6144mV" % sps     
      config |= self.spsADS1115.setdefault(sps, self.__ADS1115_REG_CONFIG_DR_250SPS)

    # Set PGA/voltage range, defaults to +-6.144V
    if ( (pga not in self.pgaADS1x15) & self.debug):	  
      print "ADS1x15: Invalid pga specified: %d, using 6144mV" % sps     
    config |= self.pgaADS1x15.setdefault(pga, self.__ADS1015_REG_CONFIG_PGA_6_144V)
    self.pga = pga

    # Set the channel to be converted
    if channel == 3:
      config |= self.__ADS1015_REG_CONFIG_MUX_SINGLE_3
    elif channel == 2:
      config |= self.__ADS1015_REG_CONFIG_MUX_SINGLE_2
    elif channel == 1:
      config |= self.__ADS1015_REG_CONFIG_MUX_SINGLE_1
    else:
      config |= self.__ADS1015_REG_CONFIG_MUX_SINGLE_0

    # Set 'start single-conversion' bit
    config |= self.__ADS1015_REG_CONFIG_OS_SINGLE

    # Write config register to the ADC
    bytes = [(config >> 8) & 0xFF, config & 0xFF]
    self.i2c.writeList(self.__ADS1015_REG_POINTER_CONFIG, bytes)

    # Wait for the ADC conversion to complete
    # The minimum delay depends on the sps: delay >= 1/sps
    # We add 0.1ms to be sure
    delay = 1.0/sps+0.0001
    time.sleep(delay)

    # Read the conversion results
    result = self.i2c.readList(self.__ADS1015_REG_POINTER_CONVERT, 2)
    if (self.ic == self.__IC_ADS1015):
    	# Shift right 4 bits for the 12-bit ADS1015 and convert to mV
    	return ( ((result[0] << 8) | (result[1] & 0xFF)) >> 4 )*pga/2048.0
    else:
	# Return a mV value for the ADS1115
	# (Take signed values into account as well)
	val = (result[0] << 8) | (result[1])
	if val > 0x7FFF:
	  return (val - 0xFFFF)*pga/32768.0
	else:
	  return ( (result[0] << 8) | (result[1]) )*pga/32768.0
	

  def readADCDifferential(self, chP=0, chN=1, pga=6144, sps=250):
    "Gets a differential ADC reading from channels chP and chN in mV. \
    The sample rate for this mode (single-shot) can be used to lower the noise \
    (low sps) or to lower the power consumption (high sps) by duty cycling, \
    see data sheet page 14 for more info. \
    The pga must be given in mV, see page 13 for the supported values."
    
    # Disable comparator, Non-latching, Alert/Rdy active low
    # traditional comparator, single-shot mode    
    config = self.__ADS1015_REG_CONFIG_CQUE_NONE    | \
             self.__ADS1015_REG_CONFIG_CLAT_NONLAT  | \
             self.__ADS1015_REG_CONFIG_CPOL_ACTVLOW | \
             self.__ADS1015_REG_CONFIG_CMODE_TRAD   | \
             self.__ADS1015_REG_CONFIG_MODE_SINGLE  
    
    # Set channels
    if ( (chP == 0) & (chN == 1) ):
      config |= self.__ADS1015_REG_CONFIG_MUX_DIFF_0_1
    elif ( (chP == 0) & (chN == 3) ):
      config |= self.__ADS1015_REG_CONFIG_MUX_DIFF_0_3
    elif ( (chP == 2) & (chN == 3) ):
      config |= self.__ADS1015_REG_CONFIG_MUX_DIFF_2_3
    elif ( (chP == 1) & (chN == 3) ):
      config |= self.__ADS1015_REG_CONFIG_MUX_DIFF_1_3  
    else:
      if (self.debug):
	print "ADS1x15: Invalid channels specified: %d, %d" % (chP, chN)
	return -1
         
    # Set sample per seconds, defaults to 250sps
    # If sps is in the dictionary (defined in init()) it returns the value of the constant
    # othewise it returns the value for 250sps. This saves a lot of if/elif/else code!
    if (self.ic == self.__IC_ADS1015):
      config |= self.spsADS1015.setdefault(sps, self.__ADS1015_REG_CONFIG_DR_1600SPS)
    else:
      if ( (sps not in self.spsADS1115) & self.debug):	  
	print "ADS1x15: Invalid pga specified: %d, using 6144mV" % sps     
      config |= self.spsADS1115.setdefault(sps, self.__ADS1115_REG_CONFIG_DR_250SPS)
  
    # Set PGA/voltage range, defaults to +-6.144V
    if ( (pga not in self.pgaADS1x15) & self.debug):	  
      print "ADS1x15: Invalid pga specified: %d, using 6144mV" % sps     
    config |= self.pgaADS1x15.setdefault(pga, self.__ADS1015_REG_CONFIG_PGA_6_144V)
    self.pga = pga

    # Set 'start single-conversion' bit
    config |= self.__ADS1015_REG_CONFIG_OS_SINGLE

    # Write config register to the ADC
    bytes = [(config >> 8) & 0xFF, config & 0xFF]
    self.i2c.writeList(self.__ADS1015_REG_POINTER_CONFIG, bytes)

    # Wait for the ADC conversion to complete
    # The minimum delay depends on the sps: delay >= 1/sps
    # We add 0.1ms to be sure
    delay = 1.0/sps+0.0001
    time.sleep(delay)

    # Read the conversion results
    result = self.i2c.readList(self.__ADS1015_REG_POINTER_CONVERT, 2)
    if (self.ic == self.__IC_ADS1015):
    	# Shift right 4 bits for the 12-bit ADS1015 and convert to mV
    	return ( ((result[0] << 8) | (result[1] & 0xFF)) >> 4 )*pga/2048.0
    else:
	# Return a mV value for the ADS1115
	# (Take signed values into account as well)
	val = (result[0] << 8) | (result[1])
	if val > 0x7FFF:
	  return (val - 0xFFFF)*pga/32768.0
	else:
	  return ( (result[0] << 8) | (result[1]) )*pga/32768.0


  def readADCDifferential01(self, pga=6144, sps=250):
    "Gets a differential ADC reading from channels 0 and 1 in mV\
    The sample rate for this mode (single-shot) can be used to lower the noise \
    (low sps) or to lower the power consumption (high sps) by duty cycling, \
    see data sheet page 14 for more info. \
    The pga must be given in mV, see page 13 for the supported values."
    return self.readADCDifferential(0, 1, pga, sps)
   
  
  def readADCDifferential03(self, pga=6144, sps=250):
    "Gets a differential ADC reading from channels 0 and 3 in mV \
    The sample rate for this mode (single-shot) can be used to lower the noise \
    (low sps) or to lower the power consumption (high sps) by duty cycling, \
    see data sheet page 14 for more info. \
    The pga must be given in mV, see page 13 for the supported values."
    return self.readADCDifferential(0, 3, pga, sps)
     
  
  def readADCDifferential13(self, pga=6144, sps=250):
    "Gets a differential ADC reading from channels 1 and 3 in mV \
    The sample rate for this mode (single-shot) can be used to lower the noise \
    (low sps) or to lower the power consumption (high sps) by duty cycling, \
    see data sheet page 14 for more info. \
    The pga must be given in mV, see page 13 for the supported values."
    return self.__readADCDifferential(1, 3, pga, sps)  


  def readADCDifferential23(self, pga=6144, sps=250):
    "Gets a differential ADC reading from channels 2 and 3 in mV \
    The sample rate for this mode (single-shot) can be used to lower the noise \
    (low sps) or to lower the power consumption (high sps) by duty cycling, \
    see data sheet page 14 for more info. \
    The pga must be given in mV, see page 13 for the supported values."
    return self.readADCDifferential(2, 3, pga, sps)   
  
  
  def startContinuousConversion(self, channel=0, pga=6144, sps=250): 
    "Starts the continuous conversion mode and returns the first ADC reading \
    in mV from the specified channel. \
    The sps controls the sample rate. \
    The pga must be given in mV, see datasheet page 13 for the supported values. \
    Use getLastConversionResults() to read the next values and \
    stopContinuousConversion() to stop converting."
    
    # Default to channel 0 with invalid channel, or return -1?
    if (channel > 3):
      if (self.debug):
	print "ADS1x15: Invalid channel specified: %d" % channel
      return -1
    
    # Disable comparator, Non-latching, Alert/Rdy active low
    # traditional comparator, continuous mode
    # The last flag is the only change we need, page 11 datasheet
    config = self.__ADS1015_REG_CONFIG_CQUE_NONE    | \
             self.__ADS1015_REG_CONFIG_CLAT_NONLAT  | \
             self.__ADS1015_REG_CONFIG_CPOL_ACTVLOW | \
             self.__ADS1015_REG_CONFIG_CMODE_TRAD   | \
             self.__ADS1015_REG_CONFIG_MODE_CONTIN    

    # Set sample per seconds, defaults to 250sps
    # If sps is in the dictionary (defined in init()) it returns the value of the constant
    # othewise it returns the value for 250sps. This saves a lot of if/elif/else code!
    if (self.ic == self.__IC_ADS1015):
      config |= self.spsADS1015.setdefault(sps, self.__ADS1015_REG_CONFIG_DR_1600SPS)
    else:
      if ( (sps not in self.spsADS1115) & self.debug):	  
	print "ADS1x15: Invalid pga specified: %d, using 6144mV" % sps     
      config |= self.spsADS1115.setdefault(sps, self.__ADS1115_REG_CONFIG_DR_250SPS)
  
    # Set PGA/voltage range, defaults to +-6.144V
    if ( (pga not in self.pgaADS1x15) & self.debug):	  
      print "ADS1x15: Invalid pga specified: %d, using 6144mV" % sps     
    config |= self.pgaADS1x15.setdefault(pga, self.__ADS1015_REG_CONFIG_PGA_6_144V)
    self.pga = pga 
    
    # Set the channel to be converted
    if channel == 3:
      config |= self.__ADS1015_REG_CONFIG_MUX_SINGLE_3
    elif channel == 2:
      config |= self.__ADS1015_REG_CONFIG_MUX_SINGLE_2
    elif channel == 1:
      config |= self.__ADS1015_REG_CONFIG_MUX_SINGLE_1
    else:
      config |= self.__ADS1015_REG_CONFIG_MUX_SINGLE_0    
  
    # Set 'start single-conversion' bit to begin conversions
    # No need to change this for continuous mode!
    config |= self.__ADS1015_REG_CONFIG_OS_SINGLE

    # Write config register to the ADC
    # Once we write the ADC will convert continously
    # we can read the next values using getLastConversionResult
    bytes = [(config >> 8) & 0xFF, config & 0xFF]
    self.i2c.writeList(self.__ADS1015_REG_POINTER_CONFIG, bytes)

    # Wait for the ADC conversion to complete
    # The minimum delay depends on the sps: delay >= 1/sps
    # We add 0.5ms to be sure
    delay = 1.0/sps+0.0005
    time.sleep(delay)
  
    # Read the conversion results
    result = self.i2c.readList(self.__ADS1015_REG_POINTER_CONVERT, 2)
    if (self.ic == self.__IC_ADS1015):
    	# Shift right 4 bits for the 12-bit ADS1015 and convert to mV
    	return ( ((result[0] << 8) | (result[1] & 0xFF)) >> 4 )*pga/2048.0
    else:
	# Return a mV value for the ADS1115
	# (Take signed values into account as well)
	val = (result[0] << 8) | (result[1])
	if val > 0x7FFF:
	  return (val - 0xFFFF)*pga/32768.0
	else:
	  return ( (result[0] << 8) | (result[1]) )*pga/32768.0  

  def startContinuousDifferentialConversion(self, chP=0, chN=1, pga=6144, sps=250): 
    "Starts the continuous differential conversion mode and returns the first ADC reading \
    in mV as the difference from the specified channels. \
    The sps controls the sample rate. \
    The pga must be given in mV, see datasheet page 13 for the supported values. \
    Use getLastConversionResults() to read the next values and \
    stopContinuousConversion() to stop converting."
    
    # Disable comparator, Non-latching, Alert/Rdy active low
    # traditional comparator, continuous mode
    # The last flag is the only change we need, page 11 datasheet
    config = self.__ADS1015_REG_CONFIG_CQUE_NONE    | \
             self.__ADS1015_REG_CONFIG_CLAT_NONLAT  | \
             self.__ADS1015_REG_CONFIG_CPOL_ACTVLOW | \
             self.__ADS1015_REG_CONFIG_CMODE_TRAD   | \
             self.__ADS1015_REG_CONFIG_MODE_CONTIN    
  
    # Set sample per seconds, defaults to 250sps
    # If sps is in the dictionary (defined in init()) it returns the value of the constant
    # othewise it returns the value for 250sps. This saves a lot of if/elif/else code!
    if (self.ic == self.__IC_ADS1015):
      config |= self.spsADS1015.setdefault(sps, self.__ADS1015_REG_CONFIG_DR_1600SPS)
    else:
      if ( (sps not in self.spsADS1115) & self.debug):	  
	print "ADS1x15: Invalid pga specified: %d, using 6144mV" % sps     
      config |= self.spsADS1115.setdefault(sps, self.__ADS1115_REG_CONFIG_DR_250SPS)
  
    # Set PGA/voltage range, defaults to +-6.144V
    if ( (pga not in self.pgaADS1x15) & self.debug):	  
      print "ADS1x15: Invalid pga specified: %d, using 6144mV" % sps     
    config |= self.pgaADS1x15.setdefault(pga, self.__ADS1015_REG_CONFIG_PGA_6_144V)
    self.pga = pga 
    
    # Set channels
    if ( (chP == 0) & (chN == 1) ):
      config |= self.__ADS1015_REG_CONFIG_MUX_DIFF_0_1
    elif ( (chP == 0) & (chN == 3) ):
      config |= self.__ADS1015_REG_CONFIG_MUX_DIFF_0_3
    elif ( (chP == 2) & (chN == 3) ):
      config |= self.__ADS1015_REG_CONFIG_MUX_DIFF_2_3
    elif ( (chP == 1) & (chN == 3) ):
      config |= self.__ADS1015_REG_CONFIG_MUX_DIFF_1_3  
    else:
      if (self.debug):
	print "ADS1x15: Invalid channels specified: %d, %d" % (chP, chN)
	return -1  
    
    # Set 'start single-conversion' bit to begin conversions
    # No need to change this for continuous mode!
    config |= self.__ADS1015_REG_CONFIG_OS_SINGLE
  
    # Write config register to the ADC
    # Once we write the ADC will convert continously
    # we can read the next values using getLastConversionResult
    bytes = [(config >> 8) & 0xFF, config & 0xFF]
    self.i2c.writeList(self.__ADS1015_REG_POINTER_CONFIG, bytes)
  
    # Wait for the ADC conversion to complete
    # The minimum delay depends on the sps: delay >= 1/sps
    # We add 0.5ms to be sure
    delay = 1.0/sps+0.0005
    time.sleep(delay)
  
    # Read the conversion results
    result = self.i2c.readList(self.__ADS1015_REG_POINTER_CONVERT, 2)
    if (self.ic == self.__IC_ADS1015):
	# Shift right 4 bits for the 12-bit ADS1015 and convert to mV
	return ( ((result[0] << 8) | (result[1] & 0xFF)) >> 4 )*pga/2048.0
    else:
	# Return a mV value for the ADS1115
	# (Take signed values into account as well)
	val = (result[0] << 8) | (result[1])
	if val > 0x7FFF:
	  return (val - 0xFFFF)*pga/32768.0
	else:
	  return ( (result[0] << 8) | (result[1]) )*pga/32768.0  

	  
  def stopContinuousConversion(self):
    "Stops the ADC's conversions when in continuous mode \
    and resets the configuration to its default value."
    # Write the default config register to the ADC
    # Once we write, the ADC will do a single conversion and 
    # enter power-off mode.
    config = 0x8583 # Page 18 datasheet.
    bytes = [(config >> 8) & 0xFF, config & 0xFF]
    self.i2c.writeList(self.__ADS1015_REG_POINTER_CONFIG, bytes)    
    return True

  def getLastConversionResults(self):
    "Returns the last ADC conversion result in mV"
    # Read the conversion results
    result = self.i2c.readList(self.__ADS1015_REG_POINTER_CONVERT, 2)
    if (self.ic == self.__IC_ADS1015):
    	# Shift right 4 bits for the 12-bit ADS1015 and convert to mV
    	return ( ((result[0] << 8) | (result[1] & 0xFF)) >> 4 )*self.pga/2048.0
    else:
	# Return a mV value for the ADS1115
	# (Take signed values into account as well)
	val = (result[0] << 8) | (result[1])
	if val > 0x7FFF:
	  return (val - 0xFFFF)*self.pga/32768.0
	else:
	  return ( (result[0] << 8) | (result[1]) )*self.pga/32768.0  
	
	
  def startSingleEndedComparator(self, channel, thresholdHigh, thresholdLow, \
                                 pga=6144, sps=250, \
                                 activeLow=True, traditionalMode=True, latching=False, \
                                 numReadings=1):
    "Starts the comparator mode on the specified channel, see datasheet pg. 15. \
    In traditional mode it alerts (ALERT pin will go low)  when voltage exceeds  \
    thresholdHigh until it falls below thresholdLow (both given in mV). \
    In window mode (traditionalMode=False) it alerts when voltage doesn't lie\
    between both thresholds.\
    In latching mode the alert will continue until the conversion value is read. \
    numReadings controls how many readings are necessary to trigger an alert: 1, 2 or 4.\
    Use getLastConversionResults() to read the current value  (which may differ \
    from the one that triggered the alert) and clear the alert pin in latching mode. \
    This function starts the continuous conversion mode.  The sps controls \
    the sample rate and the pga the gain, see datasheet page 13. "
    
    # With invalid channel return -1
    if (channel > 3):
      if (self.debug):
	print "ADS1x15: Invalid channel specified: %d" % channel
      return -1
    
    # Continuous mode
    config = self.__ADS1015_REG_CONFIG_MODE_CONTIN     
    
    if (activeLow==False):
      config |= self.__ADS1015_REG_CONFIG_CPOL_ACTVHI
    else:
      config |= self.__ADS1015_REG_CONFIG_CPOL_ACTVLOW
      
    if (traditionalMode==False):
      config |= self.__ADS1015_REG_CONFIG_CMODE_WINDOW
    else:
      config |= self.__ADS1015_REG_CONFIG_CMODE_TRAD
      
    if (latching==True):
      config |= self.__ADS1015_REG_CONFIG_CLAT_LATCH
    else:
      config |= self.__ADS1015_REG_CONFIG_CLAT_NONLAT
      
    if (numReadings==4):
      config |= self.__ADS1015_REG_CONFIG_CQUE_4CONV
    elif (numReadings==2):
      config |= self.__ADS1015_REG_CONFIG_CQUE_2CONV
    else:
      config |= self.__ADS1015_REG_CONFIG_CQUE_1CONV
    
    # Set sample per seconds, defaults to 250sps
    # If sps is in the dictionary (defined in init()) it returns the value of the constant
    # othewise it returns the value for 250sps. This saves a lot of if/elif/else code!
    if (self.ic == self.__IC_ADS1015):
      if ( (sps not in self.spsADS1015) & self.debug):	  
	print "ADS1x15: Invalid sps specified: %d, using 1600sps" % sps       
      config |= self.spsADS1015.setdefault(sps, self.__ADS1015_REG_CONFIG_DR_1600SPS)
    else:
      if ( (sps not in self.spsADS1115) & self.debug):	  
	print "ADS1x15: Invalid sps specified: %d, using 250sps" % sps     
      config |= self.spsADS1115.setdefault(sps, self.__ADS1115_REG_CONFIG_DR_250SPS)

    # Set PGA/voltage range, defaults to +-6.144V
    if ( (pga not in self.pgaADS1x15) & self.debug):	  
      print "ADS1x15: Invalid pga specified: %d, using 6144mV" % pga     
    config |= self.pgaADS1x15.setdefault(pga, self.__ADS1015_REG_CONFIG_PGA_6_144V)
    self.pga = pga
    
    # Set the channel to be converted
    if channel == 3:
      config |= self.__ADS1015_REG_CONFIG_MUX_SINGLE_3
    elif channel == 2:
      config |= self.__ADS1015_REG_CONFIG_MUX_SINGLE_2
    elif channel == 1:
      config |= self.__ADS1015_REG_CONFIG_MUX_SINGLE_1
    else:
      config |= self.__ADS1015_REG_CONFIG_MUX_SINGLE_0

    # Set 'start single-conversion' bit to begin conversions
    config |= self.__ADS1015_REG_CONFIG_OS_SINGLE
    
    # Write threshold high and low registers to the ADC
    # V_digital = (2^(n-1)-1)/pga*V_analog
    if (self.ic == self.__IC_ADS1015):
      thresholdHighWORD = int(thresholdHigh*(2048.0/pga))
    else:
      thresholdHighWORD = int(thresholdHigh*(32767.0/pga))
    bytes = [(thresholdHighWORD >> 8) & 0xFF, thresholdHighWORD & 0xFF]
    self.i2c.writeList(self.__ADS1015_REG_POINTER_HITHRESH, bytes) 
  
    if (self.ic == self.__IC_ADS1015):
      thresholdLowWORD = int(thresholdLow*(2048.0/pga))
    else:
      thresholdLowWORD = int(thresholdLow*(32767.0/pga))    
    bytes = [(thresholdLowWORD >> 8) & 0xFF, thresholdLowWORD & 0xFF]
    self.i2c.writeList(self.__ADS1015_REG_POINTER_LOWTHRESH, bytes)     

    # Write config register to the ADC
    # Once we write the ADC will convert continously and alert when things happen,
    # we can read the converted values using getLastConversionResult
    bytes = [(config >> 8) & 0xFF, config & 0xFF]
    self.i2c.writeList(self.__ADS1015_REG_POINTER_CONFIG, bytes)    


  def startDifferentialComparator(self, chP, chN, thresholdHigh, thresholdLow, \
                                 pga=6144, sps=250, \
                                 activeLow=True, traditionalMode=True, latching=False, \
                                 numReadings=1):
    "Starts the comparator mode on the specified channel, see datasheet pg. 15. \
    In traditional mode it alerts (ALERT pin will go low)  when voltage exceeds  \
    thresholdHigh until it falls below thresholdLow (both given in mV). \
    In window mode (traditionalMode=False) it alerts when voltage doesn't lie\
    between both thresholds.\
    In latching mode the alert will continue until the conversion value is read. \
    numReadings controls how many readings are necessary to trigger an alert: 1, 2 or 4.\
    Use getLastConversionResults() to read the current value  (which may differ \
    from the one that triggered the alert) and clear the alert pin in latching mode. \
    This function starts the continuous conversion mode.  The sps controls \
    the sample rate and the pga the gain, see datasheet page 13. "

    # Continuous mode
    config = self.__ADS1015_REG_CONFIG_MODE_CONTIN     
    
    if (activeLow==False):
      config |= self.__ADS1015_REG_CONFIG_CPOL_ACTVHI
    else:
      config |= self.__ADS1015_REG_CONFIG_CPOL_ACTVLOW
      
    if (traditionalMode==False):
      config |= self.__ADS1015_REG_CONFIG_CMODE_WINDOW
    else:
      config |= self.__ADS1015_REG_CONFIG_CMODE_TRAD
      
    if (latching==True):
      config |= self.__ADS1015_REG_CONFIG_CLAT_LATCH
    else:
      config |= self.__ADS1015_REG_CONFIG_CLAT_NONLAT
      
    if (numReadings==4):
      config |= self.__ADS1015_REG_CONFIG_CQUE_4CONV
    elif (numReadings==2):
      config |= self.__ADS1015_REG_CONFIG_CQUE_2CONV
    else:
      config |= self.__ADS1015_REG_CONFIG_CQUE_1CONV
    
    # Set sample per seconds, defaults to 250sps
    # If sps is in the dictionary (defined in init()) it returns the value of the constant
    # othewise it returns the value for 250sps. This saves a lot of if/elif/else code!
    if (self.ic == self.__IC_ADS1015):
      if ( (sps not in self.spsADS1015) & self.debug):	  
	print "ADS1x15: Invalid sps specified: %d, using 1600sps" % sps       
      config |= self.spsADS1015.setdefault(sps, self.__ADS1015_REG_CONFIG_DR_1600SPS)
    else:
      if ( (sps not in self.spsADS1115) & self.debug):	  
	print "ADS1x15: Invalid sps specified: %d, using 250sps" % sps     
      config |= self.spsADS1115.setdefault(sps, self.__ADS1115_REG_CONFIG_DR_250SPS)

    # Set PGA/voltage range, defaults to +-6.144V
    if ( (pga not in self.pgaADS1x15) & self.debug):	  
      print "ADS1x15: Invalid pga specified: %d, using 6144mV" % pga     
    config |= self.pgaADS1x15.setdefault(pga, self.__ADS1015_REG_CONFIG_PGA_6_144V)
    self.pga = pga
    
    # Set channels
    if ( (chP == 0) & (chN == 1) ):
      config |= self.__ADS1015_REG_CONFIG_MUX_DIFF_0_1
    elif ( (chP == 0) & (chN == 3) ):
      config |= self.__ADS1015_REG_CONFIG_MUX_DIFF_0_3
    elif ( (chP == 2) & (chN == 3) ):
      config |= self.__ADS1015_REG_CONFIG_MUX_DIFF_2_3
    elif ( (chP == 1) & (chN == 3) ):
      config |= self.__ADS1015_REG_CONFIG_MUX_DIFF_1_3  
    else:
      if (self.debug):
	print "ADS1x15: Invalid channels specified: %d, %d" % (chP, chN)
	return -1

    # Set 'start single-conversion' bit to begin conversions
    config |= self.__ADS1015_REG_CONFIG_OS_SINGLE
    
    # Write threshold high and low registers to the ADC
    # V_digital = (2^(n-1)-1)/pga*V_analog
    if (self.ic == self.__IC_ADS1015):
      thresholdHighWORD = int(thresholdHigh*(2048.0/pga))
    else:
      thresholdHighWORD = int(thresholdHigh*(32767.0/pga))
    bytes = [(thresholdHighWORD >> 8) & 0xFF, thresholdHighWORD & 0xFF]
    self.i2c.writeList(self.__ADS1015_REG_POINTER_HITHRESH, bytes) 
  
    if (self.ic == self.__IC_ADS1015):
      thresholdLowWORD = int(thresholdLow*(2048.0/pga))
    else:
      thresholdLowWORD = int(thresholdLow*(32767.0/pga))    
    bytes = [(thresholdLowWORD >> 8) & 0xFF, thresholdLowWORD & 0xFF]
    self.i2c.writeList(self.__ADS1015_REG_POINTER_LOWTHRESH, bytes)     

    # Write config register to the ADC
    # Once we write the ADC will convert continously and alert when things happen,
    # we can read the converted values using getLastConversionResult
    bytes = [(config >> 8) & 0xFF, config & 0xFF]
    self.i2c.writeList(self.__ADS1015_REG_POINTER_CONFIG, bytes)    


########NEW FILE########
__FILENAME__ = Adafruit_I2C
../Adafruit_I2C/Adafruit_I2C.py
########NEW FILE########
__FILENAME__ = ads1x15_ex_comparator
#!/usr/bin/python

import time, signal, sys
from Adafruit_ADS1x15 import ADS1x15

def signal_handler(signal, frame):
        print 'You pressed Ctrl+C!'
        print adc.getLastConversionResults()/1000.0
        adc.stopContinuousConversion()
        sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
# Print 'Press Ctrl+C to exit'

ADS1015 = 0x00	# 12-bit ADC
ADS1115 = 0x01	# 16-bit ADC

# Initialise the ADC using the default mode (use default I2C address)
# Set this to ADS1015 or ADS1115 depending on the ADC you are using!
adc = ADS1x15(ic=ADS1115)

# start comparator on channel 2 with a thresholdHigh=200mV and low=100mV
# in traditional mode, non-latching, +/-1.024V and 250sps
adc.startSingleEndedComparator(2, 200, 100, pga=1024, sps=250, activeLow=True, traditionalMode=True, latching=False, numReadings=1)

while True:
		print adc.getLastConversionResults()/1000.0
		time.sleep(0.25)

#time.sleep(0.1)

########NEW FILE########
__FILENAME__ = ads1x15_ex_differential
#!/usr/bin/python

import time, signal, sys
from Adafruit_ADS1x15 import ADS1x15

def signal_handler(signal, frame):
        #print 'You pressed Ctrl+C!'
        sys.exit(0)
signal.signal(signal.SIGINT, signal_handler)
#print 'Press Ctrl+C to exit'

ADS1015 = 0x00	# 12-bit ADC
ADS1115 = 0x01	# 16-bit ADC

# Initialise the ADC using the default mode (use default I2C address)
# Set this to ADS1015 or ADS1115 depending on the ADC you are using!
adc = ADS1x15(ic=ADS1115)

# Read channels 2 and 3 in single-ended mode, at +/-4.096V and 250sps
volts2 = adc.readADCSingleEnded(2, 4096, 250)/1000.0
volts3 = adc.readADCSingleEnded(3, 4096, 250)/1000.0

# Now do a differential reading of channels 2 and 3
voltsdiff = adc.readADCDifferential23(4096, 250)/1000.0

# Display the two different reading for comparison purposes
print "%.8f %.8f %.8f %.8f" % (volts2, volts3, volts3-volts2, -voltsdiff)

########NEW FILE########
__FILENAME__ = ads1x15_ex_singleended
#!/usr/bin/python

import time, signal, sys
from Adafruit_ADS1x15 import ADS1x15

def signal_handler(signal, frame):
        print 'You pressed Ctrl+C!'
        sys.exit(0)
signal.signal(signal.SIGINT, signal_handler)
#print 'Press Ctrl+C to exit'

ADS1015 = 0x00  # 12-bit ADC
ADS1115 = 0x01	# 16-bit ADC

# Select the gain
# gain = 61    # +/- 6.144V
gain = 4096  # +/- 4.096V
# gain = 2048  # +/- 2.048V
# gain = 1024  # +/- 1.024V
# gain = 512   # +/- 0.512V
# gain = 256   # +/- 0.256V

# Select the sample rate
# sps = 8    # 8 samples per second
# sps = 16   # 16 samples per second
# sps = 32   # 32 samples per second
# sps = 64   # 64 samples per second
# sps = 128  # 128 samples per second
sps = 250  # 250 samples per second
# sps = 475  # 475 samples per second
# sps = 860  # 860 samples per second

# Initialise the ADC using the default mode (use default I2C address)
# Set this to ADS1015 or ADS1115 depending on the ADC you are using!
adc = ADS1x15(ic=ADS1115)

# Read channel 0 in single-ended mode using the settings above
volts = adc.readADCSingleEnded(0, gain, sps) / 1000

# To read channel 3 in single-ended mode, +/- 1.024V, 860 sps use:
# volts = adc.readADCSingleEnded(3, 1024, 860)

print "%.6f" % (volts)

########NEW FILE########
__FILENAME__ = Adafruit_ADXL345
#!/usr/bin/python

# Python library for ADXL345 accelerometer.

# Copyright 2013 Adafruit Industries

# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.

from Adafruit_I2C import Adafruit_I2C


class Adafruit_ADXL345(Adafruit_I2C):

    # Minimal constants carried over from Arduino library

    ADXL345_ADDRESS          = 0x53

    ADXL345_REG_DEVID        = 0x00 # Device ID
    ADXL345_REG_DATAX0       = 0x32 # X-axis data 0 (6 bytes for X/Y/Z)
    ADXL345_REG_POWER_CTL    = 0x2D # Power-saving features control

    ADXL345_DATARATE_0_10_HZ = 0x00
    ADXL345_DATARATE_0_20_HZ = 0x01
    ADXL345_DATARATE_0_39_HZ = 0x02
    ADXL345_DATARATE_0_78_HZ = 0x03
    ADXL345_DATARATE_1_56_HZ = 0x04
    ADXL345_DATARATE_3_13_HZ = 0x05
    ADXL345_DATARATE_6_25HZ  = 0x06
    ADXL345_DATARATE_12_5_HZ = 0x07
    ADXL345_DATARATE_25_HZ   = 0x08
    ADXL345_DATARATE_50_HZ   = 0x09
    ADXL345_DATARATE_100_HZ  = 0x0A # (default)
    ADXL345_DATARATE_200_HZ  = 0x0B
    ADXL345_DATARATE_400_HZ  = 0x0C
    ADXL345_DATARATE_800_HZ  = 0x0D
    ADXL345_DATARATE_1600_HZ = 0x0E
    ADXL345_DATARATE_3200_HZ = 0x0F

    ADXL345_RANGE_2_G        = 0x00 # +/-  2g (default)
    ADXL345_RANGE_4_G        = 0x01 # +/-  4g
    ADXL345_RANGE_8_G        = 0x02 # +/-  8g
    ADXL345_RANGE_16_G       = 0x03 # +/- 16g


    def __init__(self, busnum=-1, debug=False):

        self.accel = Adafruit_I2C(self.ADXL345_ADDRESS, busnum, debug)

        if self.accel.readU8(self.ADXL345_REG_DEVID) == 0xE5:
            # Enable the accelerometer
            self.accel.write8(self.ADXL345_REG_POWER_CTL, 0x08)


    def setRange(self, range):
        # Read the data format register to preserve bits.  Update the data
        # rate, make sure that the FULL-RES bit is enabled for range scaling
        format = ((self.accel.readU8(self.ADXL345_REG_DATA_FORMAT) & ~0x0F) |
          range | 0x08)
        # Write the register back to the IC
        seld.accel.write8(self.ADXL345_REG_DATA_FORMAT, format)


    def getRange(self):
        return self.accel.readU8(self.ADXL345_REG_DATA_FORMAT) & 0x03


    def setDataRate(self, dataRate):
        # Note: The LOW_POWER bits are currently ignored,
        # we always keep the device in 'normal' mode
        self.accel.write8(self.ADXL345_REG_BW_RATE, dataRate & 0x0F)


    def getDataRate(self):
        return self.accel.readU8(self.ADXL345_REG_BW_RATE) & 0x0F


    # Read the accelerometer
    def read(self):
        raw = self.accel.readList(self.ADXL345_REG_DATAX0, 6)
        res = []
        for i in range(0, 6, 2):
            g = raw[i] | (raw[i+1] << 8)
            if g > 32767: g -= 65536
            res.append(g)
        return res


# Simple example prints accelerometer data once per second:
if __name__ == '__main__':

    from time import sleep

    accel = Adafruit_ADXL345()

    print '[Accelerometer X, Y, Z]'
    while True:
        print accel.read()
        sleep(1) # Output is fun to watch if this is commented out

########NEW FILE########
__FILENAME__ = Adafruit_I2C
../Adafruit_I2C/Adafruit_I2C.py
########NEW FILE########
__FILENAME__ = Adafruit_BMP085
#!/usr/bin/python

import time
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
  def __init__(self, address=0x77, mode=1, debug=False):
    self.i2c = Adafruit_I2C(address)

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

  def readS16(self, register):
    "Reads a signed 16-bit value"
    hi = self.i2c.readS8(register)
    lo = self.i2c.readU8(register+1)
    return (hi << 8) + lo

  def readU16(self, register):
    "Reads an unsigned 16-bit value"
    hi = self.i2c.readU8(register)
    lo = self.i2c.readU8(register+1)
    return (hi << 8) + lo

  def readCalibrationData(self):
    "Reads the calibration data from the IC"
    self._cal_AC1 = self.readS16(self.__BMP085_CAL_AC1)   # INT16
    self._cal_AC2 = self.readS16(self.__BMP085_CAL_AC2)   # INT16
    self._cal_AC3 = self.readS16(self.__BMP085_CAL_AC3)   # INT16
    self._cal_AC4 = self.readU16(self.__BMP085_CAL_AC4)   # UINT16
    self._cal_AC5 = self.readU16(self.__BMP085_CAL_AC5)   # UINT16
    self._cal_AC6 = self.readU16(self.__BMP085_CAL_AC6)   # UINT16
    self._cal_B1 = self.readS16(self.__BMP085_CAL_B1)     # INT16
    self._cal_B2 = self.readS16(self.__BMP085_CAL_B2)     # INT16
    self._cal_MB = self.readS16(self.__BMP085_CAL_MB)     # INT16
    self._cal_MC = self.readS16(self.__BMP085_CAL_MC)     # INT16
    self._cal_MD = self.readS16(self.__BMP085_CAL_MD)     # INT16
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
    raw = self.readU16(self.__BMP085_TEMPDATA)
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
      self._cal_MB = -32768;
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
      print "DBG: X3 = %d" % (X3)
      print "DBG: B3 = %d" % (B3)

    X1 = (self._cal_AC3 * B6) >> 13
    X2 = (self._cal_B1 * ((B6 * B6) >> 12)) >> 16
    X3 = ((X1 + X2) + 2) >> 2
    B4 = (self._cal_AC4 * (X3 + 32768)) >> 15
    B7 = (UP - B3) * (50000 >> self.mode)
    if (self.debug):
      print "DBG: X1 = %d" % (X1)
      print "DBG: X2 = %d" % (X2)
      print "DBG: X3 = %d" % (X3)
      print "DBG: B4 = %d" % (B4)
      print "DBG: B7 = %d" % (B7)

    if (B7 < 0x80000000):
      p = (B7 * 2) / B4
    else:
      p = (B7 / B4) * 2

    if (self.debug):
      print "DBG: X1 = %d" % (X1)
      
    X1 = (p >> 8) * (p >> 8)
    X1 = (X1 * 3038) >> 16
    X2 = (-7357 * p) >> 16
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

########NEW FILE########
__FILENAME__ = Adafruit_BMP085_example
#!/usr/bin/python

from Adafruit_BMP085 import BMP085

# ===========================================================================
# Example Code
# ===========================================================================

# Initialise the BMP085 and use STANDARD mode (default value)
# bmp = BMP085(0x77, debug=True)
bmp = BMP085(0x77)

# To specify a different operating mode, uncomment one of the following:
# bmp = BMP085(0x77, 0)  # ULTRALOWPOWER Mode
# bmp = BMP085(0x77, 1)  # STANDARD Mode
# bmp = BMP085(0x77, 2)  # HIRES Mode
# bmp = BMP085(0x77, 3)  # ULTRAHIRES Mode

temp = bmp.readTemperature()

# Read the current barometric pressure level
pressure = bmp.readPressure()

# To calculate altitude based on an estimated mean sea level pressure
# (1013.25 hPa) call the function as follows, but this won't be very accurate
altitude = bmp.readAltitude()

# To specify a more accurate altitude, enter the correct mean sea level
# pressure level.  For example, if the current pressure level is 1023.50 hPa
# enter 102350 since we include two decimal places in the integer value
# altitude = bmp.readAltitude(102350)

print "Temperature: %.2f C" % temp
print "Pressure:    %.2f hPa" % (pressure / 100.0)
print "Altitude:    %.2f" % altitude

########NEW FILE########
__FILENAME__ = Adafruit_BMP085_googledocs_ex
#!/usr/bin/python

import sys
import time
import datetime
import gspread
from Adafruit_BMP085 import BMP085

# ===========================================================================
# Google Account Details
# ===========================================================================

# Account details for google docs
email       = 'you@somewhere.com'
password    = '$hhh!'
spreadsheet = 'SpreadsheetName'

# ===========================================================================
# Example Code
# ===========================================================================

# Initialise the BMP085 and use STANDARD mode (default value)
# bmp = BMP085(0x77, debug=True)
bmp = BMP085(0x77)

# To specify a different operating mode, uncomment one of the following:
# bmp = BMP085(0x77, 0)  # ULTRALOWPOWER Mode
# bmp = BMP085(0x77, 1)  # STANDARD Mode
# bmp = BMP085(0x77, 2)  # HIRES Mode
# bmp = BMP085(0x77, 3)  # ULTRAHIRES Mode

# Login with your Google account
try:
  gc = gspread.login(email, password)
except:
  print "Unable to log in.  Check your email address/password"
  sys.exit()

# Open a worksheet from your spreadsheet using the filename
try:
  worksheet = gc.open(spreadsheet).sheet1
  # Alternatively, open a spreadsheet using the spreadsheet's key
  # worksheet = gc.open_by_key('0BmgG6nO_6dprdS1MN3d3MkdPa142WFRrdnRRUWl1UFE')
except:
  print "Unable to open the spreadsheet.  Check your filename: %s" % spreadsheet
  sys.exit()

# Continuously append data
while(True):
  temp = bmp.readTemperature()
  pressure = bmp.readPressure()
  altitude = bmp.readAltitude()

  print "Temperature: %.2f C" % temp
  print "Pressure:    %.2f hPa" % (pressure / 100.0)
  print "Altitude:    %.2f" % altitude

  # Append the data in the spreadsheet, including a timestamp
  try:
    values = [datetime.datetime.now(), temp, pressure, altitude]
    worksheet.append_row(values)
  except:
    print "Unable to append data.  Check your connection?"
    sys.exit()

  # Wait 5 seconds before continuing
  print "Wrote a row to %s" % spreadsheet
  time.sleep(5)


########NEW FILE########
__FILENAME__ = Adafruit_I2C
../Adafruit_I2C/Adafruit_I2C.py
########NEW FILE########
__FILENAME__ = Adafruit_CharLCD
#!/usr/bin/python

#
# based on code from lrvick and LiquidCrystal
# lrvic - https://github.com/lrvick/raspi-hd44780/blob/master/hd44780.py
# LiquidCrystal - https://github.com/arduino/Arduino/blob/master/libraries/LiquidCrystal/LiquidCrystal.cpp
#

from time import sleep

class Adafruit_CharLCD:

    # commands
    LCD_CLEARDISPLAY 		= 0x01
    LCD_RETURNHOME 		= 0x02
    LCD_ENTRYMODESET 		= 0x04
    LCD_DISPLAYCONTROL 		= 0x08
    LCD_CURSORSHIFT 		= 0x10
    LCD_FUNCTIONSET 		= 0x20
    LCD_SETCGRAMADDR 		= 0x40
    LCD_SETDDRAMADDR 		= 0x80

    # flags for display entry mode
    LCD_ENTRYRIGHT 		= 0x00
    LCD_ENTRYLEFT 		= 0x02
    LCD_ENTRYSHIFTINCREMENT 	= 0x01
    LCD_ENTRYSHIFTDECREMENT 	= 0x00

    # flags for display on/off control
    LCD_DISPLAYON 		= 0x04
    LCD_DISPLAYOFF 		= 0x00
    LCD_CURSORON 		= 0x02
    LCD_CURSOROFF 		= 0x00
    LCD_BLINKON 		= 0x01
    LCD_BLINKOFF 		= 0x00

    # flags for display/cursor shift
    LCD_DISPLAYMOVE 		= 0x08
    LCD_CURSORMOVE 		= 0x00

    # flags for display/cursor shift
    LCD_DISPLAYMOVE 		= 0x08
    LCD_CURSORMOVE 		= 0x00
    LCD_MOVERIGHT 		= 0x04
    LCD_MOVELEFT 		= 0x00

    # flags for function set
    LCD_8BITMODE 		= 0x10
    LCD_4BITMODE 		= 0x00
    LCD_2LINE 			= 0x08
    LCD_1LINE 			= 0x00
    LCD_5x10DOTS 		= 0x04
    LCD_5x8DOTS 		= 0x00



    def __init__(self, pin_rs=25, pin_e=24, pins_db=[23, 17, 21, 22], GPIO = None):
	# Emulate the old behavior of using RPi.GPIO if we haven't been given
	# an explicit GPIO interface to use
	if not GPIO:
	    import RPi.GPIO as GPIO
   	self.GPIO = GPIO
        self.pin_rs = pin_rs
        self.pin_e = pin_e
        self.pins_db = pins_db

        self.GPIO.setmode(GPIO.BCM)
        self.GPIO.setup(self.pin_e, GPIO.OUT)
        self.GPIO.setup(self.pin_rs, GPIO.OUT)

        for pin in self.pins_db:
            self.GPIO.setup(pin, GPIO.OUT)

	self.write4bits(0x33) # initialization
	self.write4bits(0x32) # initialization
	self.write4bits(0x28) # 2 line 5x7 matrix
	self.write4bits(0x0C) # turn cursor off 0x0E to enable cursor
	self.write4bits(0x06) # shift cursor right

	self.displaycontrol = self.LCD_DISPLAYON | self.LCD_CURSOROFF | self.LCD_BLINKOFF

	self.displayfunction = self.LCD_4BITMODE | self.LCD_1LINE | self.LCD_5x8DOTS
	self.displayfunction |= self.LCD_2LINE

	""" Initialize to default text direction (for romance languages) """
	self.displaymode =  self.LCD_ENTRYLEFT | self.LCD_ENTRYSHIFTDECREMENT
	self.write4bits(self.LCD_ENTRYMODESET | self.displaymode) #  set the entry mode

        self.clear()


    def begin(self, cols, lines):

	if (lines > 1):
		self.numlines = lines
    		self.displayfunction |= self.LCD_2LINE
		self.currline = 0


    def home(self):

	self.write4bits(self.LCD_RETURNHOME) # set cursor position to zero
	self.delayMicroseconds(3000) # this command takes a long time!
	

    def clear(self):

	self.write4bits(self.LCD_CLEARDISPLAY) # command to clear display
	self.delayMicroseconds(3000)	# 3000 microsecond sleep, clearing the display takes a long time


    def setCursor(self, col, row):

	self.row_offsets = [ 0x00, 0x40, 0x14, 0x54 ]

	if ( row > self.numlines ): 
		row = self.numlines - 1 # we count rows starting w/0

	self.write4bits(self.LCD_SETDDRAMADDR | (col + self.row_offsets[row]))


    def noDisplay(self): 
	""" Turn the display off (quickly) """

	self.displaycontrol &= ~self.LCD_DISPLAYON
	self.write4bits(self.LCD_DISPLAYCONTROL | self.displaycontrol)


    def display(self):
	""" Turn the display on (quickly) """

	self.displaycontrol |= self.LCD_DISPLAYON
	self.write4bits(self.LCD_DISPLAYCONTROL | self.displaycontrol)


    def noCursor(self):
	""" Turns the underline cursor on/off """

	self.displaycontrol &= ~self.LCD_CURSORON
	self.write4bits(self.LCD_DISPLAYCONTROL | self.displaycontrol)


    def cursor(self):
	""" Cursor On """

	self.displaycontrol |= self.LCD_CURSORON
	self.write4bits(self.LCD_DISPLAYCONTROL | self.displaycontrol)


    def noBlink(self):
	""" Turn on and off the blinking cursor """

	self.displaycontrol &= ~self.LCD_BLINKON
	self.write4bits(self.LCD_DISPLAYCONTROL | self.displaycontrol)


    def noBlink(self):
	""" Turn on and off the blinking cursor """

	self.displaycontrol &= ~self.LCD_BLINKON
	self.write4bits(self.LCD_DISPLAYCONTROL | self.displaycontrol)


    def DisplayLeft(self):
	""" These commands scroll the display without changing the RAM """

	self.write4bits(self.LCD_CURSORSHIFT | self.LCD_DISPLAYMOVE | self.LCD_MOVELEFT)


    def scrollDisplayRight(self):
	""" These commands scroll the display without changing the RAM """

	self.write4bits(self.LCD_CURSORSHIFT | self.LCD_DISPLAYMOVE | self.LCD_MOVERIGHT);


    def leftToRight(self):
	""" This is for text that flows Left to Right """

	self.displaymode |= self.LCD_ENTRYLEFT
	self.write4bits(self.LCD_ENTRYMODESET | self.displaymode);


    def rightToLeft(self):
	""" This is for text that flows Right to Left """
	self.displaymode &= ~self.LCD_ENTRYLEFT
	self.write4bits(self.LCD_ENTRYMODESET | self.displaymode)


    def autoscroll(self):
	""" This will 'right justify' text from the cursor """

	self.displaymode |= self.LCD_ENTRYSHIFTINCREMENT
	self.write4bits(self.LCD_ENTRYMODESET | self.displaymode)


    def noAutoscroll(self): 
	""" This will 'left justify' text from the cursor """

	self.displaymode &= ~self.LCD_ENTRYSHIFTINCREMENT
	self.write4bits(self.LCD_ENTRYMODESET | self.displaymode)


    def write4bits(self, bits, char_mode=False):
        """ Send command to LCD """

	self.delayMicroseconds(1000) # 1000 microsecond sleep

        bits=bin(bits)[2:].zfill(8)

        self.GPIO.output(self.pin_rs, char_mode)

        for pin in self.pins_db:
            self.GPIO.output(pin, False)

        for i in range(4):
            if bits[i] == "1":
                self.GPIO.output(self.pins_db[::-1][i], True)

	self.pulseEnable()

        for pin in self.pins_db:
            self.GPIO.output(pin, False)

        for i in range(4,8):
            if bits[i] == "1":
                self.GPIO.output(self.pins_db[::-1][i-4], True)

	self.pulseEnable()


    def delayMicroseconds(self, microseconds):
	seconds = microseconds / float(1000000)	# divide microseconds by 1 million for seconds
	sleep(seconds)


    def pulseEnable(self):
	self.GPIO.output(self.pin_e, False)
	self.delayMicroseconds(1)		# 1 microsecond pause - enable pulse must be > 450ns 
	self.GPIO.output(self.pin_e, True)
	self.delayMicroseconds(1)		# 1 microsecond pause - enable pulse must be > 450ns 
	self.GPIO.output(self.pin_e, False)
	self.delayMicroseconds(1)		# commands need > 37us to settle


    def message(self, text):
        """ Send string to LCD. Newline wraps to second line"""

        for char in text:
            if char == '\n':
                self.write4bits(0xC0) # next line
            else:
                self.write4bits(ord(char),True)


if __name__ == '__main__':

    lcd = Adafruit_CharLCD()

    lcd.clear()
    lcd.message("  Adafruit 16x2\n  Standard LCD")


########NEW FILE########
__FILENAME__ = Adafruit_CharLCD_IPclock_example
#!/usr/bin/python

from Adafruit_CharLCD import Adafruit_CharLCD
from subprocess import * 
from time import sleep, strftime
from datetime import datetime

lcd = Adafruit_CharLCD()

cmd = "ip addr show eth0 | grep inet | awk '{print $2}' | cut -d/ -f1"

lcd.begin(16,1)

def run_cmd(cmd):
        p = Popen(cmd, shell=True, stdout=PIPE)
        output = p.communicate()[0]
        return output

while 1:
	lcd.clear()
	ipaddr = run_cmd(cmd)
	lcd.message(datetime.now().strftime('%b %d  %H:%M:%S\n'))
	lcd.message('IP %s' % ( ipaddr ) )
	sleep(2)

########NEW FILE########
__FILENAME__ = Adafruit_I2C
../Adafruit_I2C/Adafruit_I2C.py
########NEW FILE########
__FILENAME__ = Adafruit_CharLCDPlate
#!/usr/bin/python

# Python library for Adafruit RGB-backlit LCD plate for Raspberry Pi.
# Written by Adafruit Industries.  MIT license.

# This is essentially a complete rewrite, but the calling syntax
# and constants are based on code from lrvick and LiquidCrystal.
# lrvic - https://github.com/lrvick/raspi-hd44780/blob/master/hd44780.py
# LiquidCrystal - https://github.com/arduino/Arduino/blob/master/libraries/LiquidCrystal/LiquidCrystal.cpp

from Adafruit_I2C import Adafruit_I2C
from time import sleep

class Adafruit_CharLCDPlate(Adafruit_I2C):

    # ----------------------------------------------------------------------
    # Constants

    # Port expander registers
    MCP23017_IOCON_BANK0    = 0x0A  # IOCON when Bank 0 active
    MCP23017_IOCON_BANK1    = 0x15  # IOCON when Bank 1 active
    # These are register addresses when in Bank 1 only:
    MCP23017_GPIOA          = 0x09
    MCP23017_IODIRB         = 0x10
    MCP23017_GPIOB          = 0x19

    # Port expander input pin definitions
    SELECT                  = 0
    RIGHT                   = 1
    DOWN                    = 2
    UP                      = 3
    LEFT                    = 4

    # LED colors
    OFF                     = 0x00
    RED                     = 0x01
    GREEN                   = 0x02
    BLUE                    = 0x04
    YELLOW                  = RED + GREEN
    TEAL                    = GREEN + BLUE
    VIOLET                  = RED + BLUE
    WHITE                   = RED + GREEN + BLUE
    ON                      = RED + GREEN + BLUE

    # LCD Commands
    LCD_CLEARDISPLAY        = 0x01
    LCD_RETURNHOME          = 0x02
    LCD_ENTRYMODESET        = 0x04
    LCD_DISPLAYCONTROL      = 0x08
    LCD_CURSORSHIFT         = 0x10
    LCD_FUNCTIONSET         = 0x20
    LCD_SETCGRAMADDR        = 0x40
    LCD_SETDDRAMADDR        = 0x80

    # Flags for display on/off control
    LCD_DISPLAYON           = 0x04
    LCD_DISPLAYOFF          = 0x00
    LCD_CURSORON            = 0x02
    LCD_CURSOROFF           = 0x00
    LCD_BLINKON             = 0x01
    LCD_BLINKOFF            = 0x00

    # Flags for display entry mode
    LCD_ENTRYRIGHT          = 0x00
    LCD_ENTRYLEFT           = 0x02
    LCD_ENTRYSHIFTINCREMENT = 0x01
    LCD_ENTRYSHIFTDECREMENT = 0x00

    # Flags for display/cursor shift
    LCD_DISPLAYMOVE = 0x08
    LCD_CURSORMOVE  = 0x00
    LCD_MOVERIGHT   = 0x04
    LCD_MOVELEFT    = 0x00


    # ----------------------------------------------------------------------
    # Constructor

    def __init__(self, busnum=-1, addr=0x20, debug=False):

        self.i2c = Adafruit_I2C(addr, busnum, debug)

        # I2C is relatively slow.  MCP output port states are cached
        # so we don't need to constantly poll-and-change bit states.
        self.porta, self.portb, self.ddrb = 0, 0, 0b00010000

        # Set MCP23017 IOCON register to Bank 0 with sequential operation.
        # If chip is already set for Bank 0, this will just write to OLATB,
        # which won't seriously bother anything on the plate right now
        # (blue backlight LED will come on, but that's done in the next
        # step anyway).
        self.i2c.bus.write_byte_data(
          self.i2c.address, self.MCP23017_IOCON_BANK1, 0)

        # Brute force reload ALL registers to known state.  This also
        # sets up all the input pins, pull-ups, etc. for the Pi Plate.
        self.i2c.bus.write_i2c_block_data(
          self.i2c.address, 0, 
          [ 0b00111111,   # IODIRA    R+G LEDs=outputs, buttons=inputs
            self.ddrb ,   # IODIRB    LCD D7=input, Blue LED=output
            0b00111111,   # IPOLA     Invert polarity on button inputs
            0b00000000,   # IPOLB
            0b00000000,   # GPINTENA  Disable interrupt-on-change
            0b00000000,   # GPINTENB
            0b00000000,   # DEFVALA
            0b00000000,   # DEFVALB
            0b00000000,   # INTCONA
            0b00000000,   # INTCONB
            0b00000000,   # IOCON
            0b00000000,   # IOCON
            0b00111111,   # GPPUA     Enable pull-ups on buttons
            0b00000000,   # GPPUB
            0b00000000,   # INTFA
            0b00000000,   # INTFB
            0b00000000,   # INTCAPA
            0b00000000,   # INTCAPB
            self.porta,   # GPIOA
            self.portb,   # GPIOB
            self.porta,   # OLATA     0 on all outputs; side effect of
            self.portb ]) # OLATB     turning on R+G+B backlight LEDs.

        # Switch to Bank 1 and disable sequential operation.
        # From this point forward, the register addresses do NOT match
        # the list immediately above.  Instead, use the constants defined
        # at the start of the class.  Also, the address register will no
        # longer increment automatically after this -- multi-byte
        # operations must be broken down into single-byte calls.
        self.i2c.bus.write_byte_data(
          self.i2c.address, self.MCP23017_IOCON_BANK0, 0b10100000)

        self.displayshift   = (self.LCD_CURSORMOVE |
                               self.LCD_MOVERIGHT)
        self.displaymode    = (self.LCD_ENTRYLEFT |
                               self.LCD_ENTRYSHIFTDECREMENT)
        self.displaycontrol = (self.LCD_DISPLAYON |
                               self.LCD_CURSOROFF |
                               self.LCD_BLINKOFF)

        self.write(0x33) # Init
        self.write(0x32) # Init
        self.write(0x28) # 2 line 5x8 matrix
        self.write(self.LCD_CLEARDISPLAY)
        self.write(self.LCD_CURSORSHIFT    | self.displayshift)
        self.write(self.LCD_ENTRYMODESET   | self.displaymode)
        self.write(self.LCD_DISPLAYCONTROL | self.displaycontrol)
        self.write(self.LCD_RETURNHOME)


    # ----------------------------------------------------------------------
    # Write operations

    # The LCD data pins (D4-D7) connect to MCP pins 12-9 (PORTB4-1), in
    # that order.  Because this sequence is 'reversed,' a direct shift
    # won't work.  This table remaps 4-bit data values to MCP PORTB
    # outputs, incorporating both the reverse and shift.
    flip = ( 0b00000000, 0b00010000, 0b00001000, 0b00011000,
             0b00000100, 0b00010100, 0b00001100, 0b00011100,
             0b00000010, 0b00010010, 0b00001010, 0b00011010,
             0b00000110, 0b00010110, 0b00001110, 0b00011110 )

    # Low-level 4-bit interface for LCD output.  This doesn't actually
    # write data, just returns a byte array of the PORTB state over time.
    # Can concatenate the output of multiple calls (up to 8) for more
    # efficient batch write.
    def out4(self, bitmask, value):
        hi = bitmask | self.flip[value >> 4]
        lo = bitmask | self.flip[value & 0x0F]
        return [hi | 0b00100000, hi, lo | 0b00100000, lo]


    # The speed of LCD accesses is inherently limited by I2C through the
    # port expander.  A 'well behaved program' is expected to poll the
    # LCD to know that a prior instruction completed.  But the timing of
    # most instructions is a known uniform 37 mS.  The enable strobe
    # can't even be twiddled that fast through I2C, so it's a safe bet
    # with these instructions to not waste time polling (which requires
    # several I2C transfers for reconfiguring the port direction).
    # The D7 pin is set as input when a potentially time-consuming
    # instruction has been issued (e.g. screen clear), as well as on
    # startup, and polling will then occur before more commands or data
    # are issued.

    pollables = ( LCD_CLEARDISPLAY, LCD_RETURNHOME )

    # Write byte, list or string value to LCD
    def write(self, value, char_mode=False):
        """ Send command/data to LCD """

        # If pin D7 is in input state, poll LCD busy flag until clear.
        if self.ddrb & 0b00010000:
            lo = (self.portb & 0b00000001) | 0b01000000
            hi = lo | 0b00100000 # E=1 (strobe)
            self.i2c.bus.write_byte_data(
              self.i2c.address, self.MCP23017_GPIOB, lo)
            while True:
                # Strobe high (enable)
                self.i2c.bus.write_byte(self.i2c.address, hi)
                # First nybble contains busy state
                bits = self.i2c.bus.read_byte(self.i2c.address)
                # Strobe low, high, low.  Second nybble (A3) is ignored.
                self.i2c.bus.write_i2c_block_data(
                  self.i2c.address, self.MCP23017_GPIOB, [lo, hi, lo])
                if (bits & 0b00000010) == 0: break # D7=0, not busy
            self.portb = lo

            # Polling complete, change D7 pin to output
            self.ddrb &= 0b11101111
            self.i2c.bus.write_byte_data(self.i2c.address,
              self.MCP23017_IODIRB, self.ddrb)

        bitmask = self.portb & 0b00000001   # Mask out PORTB LCD control bits
        if char_mode: bitmask |= 0b10000000 # Set data bit if not a command

        # If string or list, iterate through multiple write ops
        if isinstance(value, str):
            last = len(value) - 1 # Last character in string
            data = []             # Start with blank list
            for i, v in enumerate(value): # For each character...
                # Append 4 bytes to list representing PORTB over time.
                # First the high 4 data bits with strobe (enable) set
                # and unset, then same with low 4 data bits (strobe 1/0).
                data.extend(self.out4(bitmask, ord(v)))
                # I2C block data write is limited to 32 bytes max.
                # If limit reached, write data so far and clear.
                # Also do this on last byte if not otherwise handled.
                if (len(data) >= 32) or (i == last):
                    self.i2c.bus.write_i2c_block_data(
                      self.i2c.address, self.MCP23017_GPIOB, data)
                    self.portb = data[-1] # Save state of last byte out
                    data       = []       # Clear list for next iteration
        elif isinstance(value, list):
            # Same as above, but for list instead of string
            last = len(value) - 1
            data = []
            for i, v in enumerate(value):
                data.extend(self.out4(bitmask, v))
                if (len(data) >= 32) or (i == last):
                    self.i2c.bus.write_i2c_block_data(
                      self.i2c.address, self.MCP23017_GPIOB, data)
                    self.portb = data[-1]
                    data       = []
        else:
            # Single byte
            data = self.out4(bitmask, value)
            self.i2c.bus.write_i2c_block_data(
              self.i2c.address, self.MCP23017_GPIOB, data)
            self.portb = data[-1]

        # If a poll-worthy instruction was issued, reconfigure D7
        # pin as input to indicate need for polling on next call.
        if (not char_mode) and (value in self.pollables):
            self.ddrb |= 0b00010000
            self.i2c.bus.write_byte_data(self.i2c.address,
              self.MCP23017_IODIRB, self.ddrb)


    # ----------------------------------------------------------------------
    # Utility methods

    def begin(self, cols, lines):
        self.currline = 0
        self.numlines = lines
        self.clear()


    # Puts the MCP23017 back in Bank 0 + sequential write mode so
    # that other code using the 'classic' library can still work.
    # Any code using this newer version of the library should
    # consider adding an atexit() handler that calls this.
    def stop(self):
        self.porta = 0b11000000  # Turn off LEDs on the way out
        self.portb = 0b00000001
        sleep(0.0015)
        self.i2c.bus.write_byte_data(
          self.i2c.address, self.MCP23017_IOCON_BANK1, 0)
        self.i2c.bus.write_i2c_block_data(
          self.i2c.address, 0, 
          [ 0b00111111,   # IODIRA
            self.ddrb ,   # IODIRB
            0b00000000,   # IPOLA
            0b00000000,   # IPOLB
            0b00000000,   # GPINTENA
            0b00000000,   # GPINTENB
            0b00000000,   # DEFVALA
            0b00000000,   # DEFVALB
            0b00000000,   # INTCONA
            0b00000000,   # INTCONB
            0b00000000,   # IOCON
            0b00000000,   # IOCON
            0b00111111,   # GPPUA
            0b00000000,   # GPPUB
            0b00000000,   # INTFA
            0b00000000,   # INTFB
            0b00000000,   # INTCAPA
            0b00000000,   # INTCAPB
            self.porta,   # GPIOA
            self.portb,   # GPIOB
            self.porta,   # OLATA
            self.portb ]) # OLATB


    def clear(self):
        self.write(self.LCD_CLEARDISPLAY)


    def home(self):
        self.write(self.LCD_RETURNHOME)


    row_offsets = ( 0x00, 0x40, 0x14, 0x54 )
    def setCursor(self, col, row):
        if row > self.numlines: row = self.numlines - 1
        elif row < 0:           row = 0
        self.write(self.LCD_SETDDRAMADDR | (col + self.row_offsets[row]))


    def display(self):
        """ Turn the display on (quickly) """
        self.displaycontrol |= self.LCD_DISPLAYON
        self.write(self.LCD_DISPLAYCONTROL | self.displaycontrol)


    def noDisplay(self):
        """ Turn the display off (quickly) """
        self.displaycontrol &= ~self.LCD_DISPLAYON
        self.write(self.LCD_DISPLAYCONTROL | self.displaycontrol)


    def cursor(self):
        """ Underline cursor on """
        self.displaycontrol |= self.LCD_CURSORON
        self.write(self.LCD_DISPLAYCONTROL | self.displaycontrol)


    def noCursor(self):
        """ Underline cursor off """
        self.displaycontrol &= ~self.LCD_CURSORON
        self.write(self.LCD_DISPLAYCONTROL | self.displaycontrol)


    def ToggleCursor(self):
        """ Toggles the underline cursor On/Off """
        self.displaycontrol ^= self.LCD_CURSORON
        self.write(self.LCD_DISPLAYCONTROL | self.displaycontrol)


    def blink(self):
        """ Turn on the blinking cursor """
        self.displaycontrol |= self.LCD_BLINKON
        self.write(self.LCD_DISPLAYCONTROL | self.displaycontrol)


    def noBlink(self):
        """ Turn off the blinking cursor """
        self.displaycontrol &= ~self.LCD_BLINKON
        self.write(self.LCD_DISPLAYCONTROL | self.displaycontrol)


    def ToggleBlink(self):
        """ Toggles the blinking cursor """
        self.displaycontrol ^= self.LCD_BLINKON
        self.write(self.LCD_DISPLAYCONTROL | self.displaycontrol)


    def scrollDisplayLeft(self):
        """ These commands scroll the display without changing the RAM """
        self.displayshift = self.LCD_DISPLAYMOVE | self.LCD_MOVELEFT
        self.write(self.LCD_CURSORSHIFT | self.displayshift)


    def scrollDisplayRight(self):
        """ These commands scroll the display without changing the RAM """
        self.displayshift = self.LCD_DISPLAYMOVE | self.LCD_MOVERIGHT
        self.write(self.LCD_CURSORSHIFT | self.displayshift)


    def leftToRight(self):
        """ This is for text that flows left to right """
        self.displaymode |= self.LCD_ENTRYLEFT
        self.write(self.LCD_ENTRYMODESET | self.displaymode)


    def rightToLeft(self):
        """ This is for text that flows right to left """
        self.displaymode &= ~self.LCD_ENTRYLEFT
        self.write(self.LCD_ENTRYMODESET | self.displaymode)


    def autoscroll(self):
        """ This will 'right justify' text from the cursor """
        self.displaymode |= self.LCD_ENTRYSHIFTINCREMENT
        self.write(self.LCD_ENTRYMODESET | self.displaymode)


    def noAutoscroll(self):
        """ This will 'left justify' text from the cursor """
        self.displaymode &= ~self.LCD_ENTRYSHIFTINCREMENT
        self.write(self.LCD_ENTRYMODESET | self.displaymode)


    def createChar(self, location, bitmap):
        self.write(self.LCD_SETCGRAMADDR | ((location & 7) << 3))
        self.write(bitmap, True)
        self.write(self.LCD_SETDDRAMADDR)


    def message(self, text):
        """ Send string to LCD. Newline wraps to second line"""
        lines = str(text).split('\n')    # Split at newline(s)
        for i, line in enumerate(lines): # For each substring...
            if i > 0:                    # If newline(s),
                self.write(0xC0)         #  set DDRAM address to 2nd line
            self.write(line, True)       # Issue substring


    def backlight(self, color):
        c          = ~color
        self.porta = (self.porta & 0b00111111) | ((c & 0b011) << 6)
        self.portb = (self.portb & 0b11111110) | ((c & 0b100) >> 2)
        # Has to be done as two writes because sequential operation is off.
        self.i2c.bus.write_byte_data(
          self.i2c.address, self.MCP23017_GPIOA, self.porta)
        self.i2c.bus.write_byte_data(
          self.i2c.address, self.MCP23017_GPIOB, self.portb)


    # Read state of single button
    def buttonPressed(self, b):
        return (self.i2c.readU8(self.MCP23017_GPIOA) >> b) & 1


    # Read and return bitmask of combined button state
    def buttons(self):
        return self.i2c.readU8(self.MCP23017_GPIOA) & 0b11111


    # ----------------------------------------------------------------------
    # Test code

if __name__ == '__main__':

    lcd = Adafruit_CharLCDPlate()
    lcd.begin(16, 2)
    lcd.clear()
    lcd.message("Adafruit RGB LCD\nPlate w/Keypad!")
    sleep(1)

    col = (('Red' , lcd.RED) , ('Yellow', lcd.YELLOW), ('Green' , lcd.GREEN),
           ('Teal', lcd.TEAL), ('Blue'  , lcd.BLUE)  , ('Violet', lcd.VIOLET),
           ('Off' , lcd.OFF) , ('On'    , lcd.ON))

    print "Cycle thru backlight colors"
    for c in col:
       print c[0]
       lcd.clear()
       lcd.message(c[0])
       lcd.backlight(c[1])
       sleep(0.5)

    btn = ((lcd.SELECT, 'Select', lcd.ON),
           (lcd.LEFT  , 'Left'  , lcd.RED),
           (lcd.UP    , 'Up'    , lcd.BLUE),
           (lcd.DOWN  , 'Down'  , lcd.GREEN),
           (lcd.RIGHT , 'Right' , lcd.VIOLET))
    
    print "Try buttons on plate"
    lcd.clear()
    lcd.message("Try buttons")
    prev = -1
    while True:
        for b in btn:
            if lcd.buttonPressed(b[0]):
                if b is not prev:
                    print b[1]
                    lcd.clear()
                    lcd.message(b[1])
                    lcd.backlight(b[2])
                    prev = b
                break

########NEW FILE########
__FILENAME__ = Adafruit_I2C
../../Adafruit-Raspberry-Pi-Python-Code/Adafruit_I2C/Adafruit_I2C.py
########NEW FILE########
__FILENAME__ = Adafruit_MCP230xx
../../Adafruit-Raspberry-Pi-Python-Code/Adafruit_MCP230xx/Adafruit_MCP230xx.py
########NEW FILE########
__FILENAME__ = LCDtest
#!/usr/bin/python

from time import sleep
from Adafruit_CharLCDPlate import Adafruit_CharLCDPlate

# Initialize the LCD plate.  Should auto-detect correct I2C bus.  If not,
# pass '0' for early 256 MB Model B boards or '1' for all later versions
lcd = Adafruit_CharLCDPlate()

# Clear display and show greeting, pause 1 sec
lcd.clear()
lcd.message("Adafruit RGB LCD\nPlate w/Keypad!")
sleep(1)

# Cycle through backlight colors
col = (lcd.RED , lcd.YELLOW, lcd.GREEN, lcd.TEAL,
       lcd.BLUE, lcd.VIOLET, lcd.ON   , lcd.OFF)
for c in col:
    lcd.backlight(c)
    sleep(.5)

# Poll buttons, display message & set backlight accordingly
btn = ((lcd.LEFT  , 'Red Red Wine'              , lcd.RED),
       (lcd.UP    , 'Sita sings\nthe blues'     , lcd.BLUE),
       (lcd.DOWN  , 'I see fields\nof green'    , lcd.GREEN),
       (lcd.RIGHT , 'Purple mountain\nmajesties', lcd.VIOLET),
       (lcd.SELECT, ''                          , lcd.ON))
prev = -1
while True:
    for b in btn:
        if lcd.buttonPressed(b[0]):
            if b is not prev:
                lcd.clear()
                lcd.message(b[1])
                lcd.backlight(b[2])
                prev = b
            break

########NEW FILE########
__FILENAME__ = Adafruit_DHT_googledocs.ex
#!/usr/bin/python

import subprocess
import re
import sys
import time
import datetime
import gspread

# ===========================================================================
# Google Account Details
# ===========================================================================

# Account details for google docs
email       = 'you@somewhere.com'
password    = '$hhh!'
spreadsheet = 'SpreadsheetName'

# ===========================================================================
# Example Code
# ===========================================================================


# Login with your Google account
try:
  gc = gspread.login(email, password)
except:
  print "Unable to log in.  Check your email address/password"
  sys.exit()

# Open a worksheet from your spreadsheet using the filename
try:
  worksheet = gc.open(spreadsheet).sheet1
  # Alternatively, open a spreadsheet using the spreadsheet's key
  # worksheet = gc.open_by_key('0BmgG6nO_6dprdS1MN3d3MkdPa142WFRrdnRRUWl1UFE')
except:
  print "Unable to open the spreadsheet.  Check your filename: %s" % spreadsheet
  sys.exit()

# Continuously append data
while(True):
  # Run the DHT program to get the humidity and temperature readings!

  output = subprocess.check_output(["./Adafruit_DHT", "2302", "4"]);
  print output
  matches = re.search("Temp =\s+([0-9.]+)", output)
  if (not matches):
	time.sleep(3)
	continue
  temp = float(matches.group(1))
  
  # search for humidity printout
  matches = re.search("Hum =\s+([0-9.]+)", output)
  if (not matches):
	time.sleep(3)
	continue
  humidity = float(matches.group(1))

  print "Temperature: %.1f C" % temp
  print "Humidity:    %.1f %%" % humidity
 
  # Append the data in the spreadsheet, including a timestamp
  try:
    values = [datetime.datetime.now(), temp, humidity]
    worksheet.append_row(values)
  except:
    print "Unable to append data.  Check your connection?"
    sys.exit()

  # Wait 30 seconds before continuing
  print "Wrote a row to %s" % spreadsheet
  time.sleep(30)

########NEW FILE########
__FILENAME__ = Adafruit_DHT
#!/usr/bin/env python
# -*- coding:utf-8 -*-

import sys
import dhtreader

DHT11 = 11
DHT22 = 22
AM2302 = 22


dhtreader.init()

if len(sys.argv) != 3:
    print("usage: {0} [11|22|2302] GPIOpin#".format(sys.argv[0]))
    print("example: {0} 2302 Read from an AM2302 connected to GPIO #4".format(sys.argv[0]))
    sys.exit(2)

dev_type = None
if sys.argv[1] == "11":
    dev_type = DHT11
elif sys.argv[1] == "22":
    dev_type = DHT22
elif sys.argv[1] == "2302":
    dev_type = AM2302
else:
    print("invalid type, only 11, 22 and 2302 are supported for now!")
    sys.exit(3)

dhtpin = int(sys.argv[2])
if dhtpin <= 0:
    print("invalid GPIO pin#")
    sys.exit(3)

print("using pin #{0}".format(dhtpin))
t, h = dhtreader.read(dev_type, dhtpin)
if t and h:
    print("Temp = {0} *C, Hum = {1} %".format(t, h))
else:
    print("Failed to read from sensor, maybe try again?")

########NEW FILE########
__FILENAME__ = Adafruit_I2C
#!/usr/bin/python

import smbus

# ===========================================================================
# Adafruit_I2C Class
# ===========================================================================

class Adafruit_I2C :

  @staticmethod
  def getPiRevision():
    "Gets the version number of the Raspberry Pi board"
    # Courtesy quick2wire-python-api
    # https://github.com/quick2wire/quick2wire-python-api
    try:
      with open('/proc/cpuinfo','r') as f:
        for line in f:
          if line.startswith('Revision'):
            return 1 if line.rstrip()[-1] in ['1','2'] else 2
    except:
      return 0

  @staticmethod
  def getPiI2CBusNumber():
    # Gets the I2C bus number /dev/i2c#
    return 1 if Adafruit_I2C.getPiRevision() > 1 else 0
 
  def __init__(self, address, busnum=-1, debug=False):
    self.address = address
    # By default, the correct I2C bus is auto-detected using /proc/cpuinfo
    # Alternatively, you can hard-code the bus version below:
    # self.bus = smbus.SMBus(0); # Force I2C0 (early 256MB Pi's)
    # self.bus = smbus.SMBus(1); # Force I2C1 (512MB Pi's)
    self.bus = smbus.SMBus(
      busnum if busnum >= 0 else Adafruit_I2C.getPiI2CBusNumber())
    self.debug = debug

  def reverseByteOrder(self, data):
    "Reverses the byte order of an int (16-bit) or long (32-bit) value"
    # Courtesy Vishal Sapre
    byteCount = len(hex(data)[2:].replace('L','')[::2])
    val       = 0
    for i in range(byteCount):
      val    = (val << 8) | (data & 0xff)
      data >>= 8
    return val

  def errMsg(self):
    print "Error accessing 0x%02X: Check your I2C address" % self.address
    return -1

  def write8(self, reg, value):
    "Writes an 8-bit value to the specified register/address"
    try:
      self.bus.write_byte_data(self.address, reg, value)
      if self.debug:
        print "I2C: Wrote 0x%02X to register 0x%02X" % (value, reg)
    except IOError, err:
      return self.errMsg()

  def write16(self, reg, value):
    "Writes a 16-bit value to the specified register/address pair"
    try:
      self.bus.write_word_data(self.address, reg, value)
      if self.debug:
        print ("I2C: Wrote 0x%02X to register pair 0x%02X,0x%02X" %
         (value, reg, reg+1))
    except IOError, err:
      return self.errMsg()

  def writeList(self, reg, list):
    "Writes an array of bytes using I2C format"
    try:
      if self.debug:
        print "I2C: Writing list to register 0x%02X:" % reg
        print list
      self.bus.write_i2c_block_data(self.address, reg, list)
    except IOError, err:
      return self.errMsg()

  def readList(self, reg, length):
    "Read a list of bytes from the I2C device"
    try:
      results = self.bus.read_i2c_block_data(self.address, reg, length)
      if self.debug:
        print ("I2C: Device 0x%02X returned the following from reg 0x%02X" %
         (self.address, reg))
        print results
      return results
    except IOError, err:
      return self.errMsg()

  def readU8(self, reg):
    "Read an unsigned byte from the I2C device"
    try:
      result = self.bus.read_byte_data(self.address, reg)
      if self.debug:
        print ("I2C: Device 0x%02X returned 0x%02X from reg 0x%02X" %
         (self.address, result & 0xFF, reg))
      return result
    except IOError, err:
      return self.errMsg()

  def readS8(self, reg):
    "Reads a signed byte from the I2C device"
    try:
      result = self.bus.read_byte_data(self.address, reg)
      if result > 127: result -= 256
      if self.debug:
        print ("I2C: Device 0x%02X returned 0x%02X from reg 0x%02X" %
         (self.address, result & 0xFF, reg))
      return result
    except IOError, err:
      return self.errMsg()

  def readU16(self, reg):
    "Reads an unsigned 16-bit value from the I2C device"
    try:
      result = self.bus.read_word_data(self.address,reg)
      if (self.debug):
        print "I2C: Device 0x%02X returned 0x%04X from reg 0x%02X" % (self.address, result & 0xFFFF, reg)
      return result
    except IOError, err:
      return self.errMsg()

  def readS16(self, reg):
    "Reads a signed 16-bit value from the I2C device"
    try:
      result = self.bus.read_word_data(self.address,reg)
      if (self.debug):
        print "I2C: Device 0x%02X returned 0x%04X from reg 0x%02X" % (self.address, result & 0xFFFF, reg)
      return result
    except IOError, err:
      return self.errMsg()

if __name__ == '__main__':
  try:
    bus = Adafruit_I2C(address=0)
    print "Default I2C bus is accessible"
  except:
    print "Error accessing default I2C bus"

########NEW FILE########
__FILENAME__ = Adafruit_7Segment
#!/usr/bin/python

import time
import datetime
from Adafruit_LEDBackpack import LEDBackpack

# ===========================================================================
# 7-Segment Display
# ===========================================================================

# This class is meant to be used with the four-character, seven segment
# displays available from Adafruit

class SevenSegment:
  disp = None
 
  # Hexadecimal character lookup table (row 1 = 0..9, row 2 = A..F)
  digits = [ 0x3F, 0x06, 0x5B, 0x4F, 0x66, 0x6D, 0x7D, 0x07, 0x7F, 0x6F, \
             0x77, 0x7C, 0x39, 0x5E, 0x79, 0x71 ]

  # Constructor
  def __init__(self, address=0x70, debug=False):
    if (debug):
      print "Initializing a new instance of LEDBackpack at 0x%02X" % address
    self.disp = LEDBackpack(address=address, debug=debug)

  def writeDigitRaw(self, charNumber, value):
    "Sets a digit using the raw 16-bit value"
    if (charNumber > 7):
      return
    # Set the appropriate digit
    self.disp.setBufferRow(charNumber, value)

  def writeDigit(self, charNumber, value, dot=False):
    "Sets a single decimal or hexademical value (0..9 and A..F)"
    if (charNumber > 7):
      return
    if (value > 0xF):
      return
    # Set the appropriate digit
    self.disp.setBufferRow(charNumber, self.digits[value] | (dot << 7))

  def setColon(self, state=True):
    "Enables or disables the colon character"
    # Warning: This function assumes that the colon is character '2',
    # which is the case on 4 char displays, but may need to be modified
    # if another display type is used
    if (state):
      self.disp.setBufferRow(2, 0xFFFF)
    else:
      self.disp.setBufferRow(2, 0)


########NEW FILE########
__FILENAME__ = Adafruit_8x8
#!/usr/bin/python

import time
import datetime
from Adafruit_LEDBackpack import LEDBackpack

# ===========================================================================
# 8x8 Pixel Display
# ===========================================================================

class EightByEight:
  disp = None

  # Constructor
  def __init__(self, address=0x70, debug=False):
    if (debug):
      print "Initializing a new instance of LEDBackpack at 0x%02X" % address
    self.disp = LEDBackpack(address=address, debug=debug)

  def writeRowRaw(self, charNumber, value):
    "Sets a row of pixels using a raw 16-bit value"
    if (charNumber > 7):
      return
    # Set the appropriate row
    self.disp.setBufferRow(charNumber, value)

  def clearPixel(self, x, y):
    "A wrapper function to clear pixels (purely cosmetic)"
    self.setPixel(x, y, 0)

  def setPixel(self, x, y, color=1):
    "Sets a single pixel"
    if (x >= 8):
      return
    if (y >= 8):
      return    
    x += 7   # ATTN: This might be a bug?  On the color matrix, this causes x=0 to draw on the last line instead of the first.
    x %= 8
    # Set the appropriate pixel
    buffer = self.disp.getBuffer()
    if (color):
      self.disp.setBufferRow(y, buffer[y] | 1 << x)
    else:
      self.disp.setBufferRow(y, buffer[y] & ~(1 << x))

  def clear(self):
    "Clears the entire display"
    self.disp.clear()

class ColorEightByEight(EightByEight):
  def setPixel(self, x, y, color=1):
    "Sets a single pixel"
    if (x >= 8):
      return
    if (y >= 8):
      return

    x %= 8

    # Set the appropriate pixel
    buffer = self.disp.getBuffer()

    # TODO : Named color constants?
    # ATNN : This code was mostly taken from the arduino code, but with the addition of clearing the other bit when setting red or green.
    #        The arduino code does not do that, and might have the bug where if you draw red or green, then the other color, it actually draws yellow.
    #        The bug doesn't show up in the examples because it's always clearing.

    if (color == 1):
      self.disp.setBufferRow(y, (buffer[y] | (1 << x)) & ~(1 << (x+8)) )
    elif (color == 2):
      self.disp.setBufferRow(y, (buffer[y] | 1 << (x+8)) & ~(1 << x) )
    elif (color == 3):
      self.disp.setBufferRow(y, buffer[y] | (1 << (x+8)) | (1 << x) )
    else:
      self.disp.setBufferRow(y, buffer[y] & ~(1 << x) & ~(1 << (x+8)) )

########NEW FILE########
__FILENAME__ = Adafruit_I2C
../Adafruit_I2C/Adafruit_I2C.py
########NEW FILE########
__FILENAME__ = Adafruit_LEDBackpack
#!/usr/bin/python

import time
from copy import copy
from Adafruit_I2C import Adafruit_I2C

# ============================================================================
# LEDBackpack Class
# ============================================================================

class LEDBackpack:
  i2c = None

  # Registers
  __HT16K33_REGISTER_DISPLAY_SETUP        = 0x80
  __HT16K33_REGISTER_SYSTEM_SETUP         = 0x20
  __HT16K33_REGISTER_DIMMING              = 0xE0

  # Blink rate
  __HT16K33_BLINKRATE_OFF                 = 0x00
  __HT16K33_BLINKRATE_2HZ                 = 0x01
  __HT16K33_BLINKRATE_1HZ                 = 0x02
  __HT16K33_BLINKRATE_HALFHZ              = 0x03

  # Display buffer (8x16-bits)
  __buffer = [0x0000, 0x0000, 0x0000, 0x0000, \
              0x0000, 0x0000, 0x0000, 0x0000 ]

  # Constructor
  def __init__(self, address=0x70, debug=False):
    self.i2c = Adafruit_I2C(address)
    self.address = address
    self.debug = debug

    # Turn the oscillator on
    self.i2c.write8(self.__HT16K33_REGISTER_SYSTEM_SETUP | 0x01, 0x00)

    # Turn blink off
    self.setBlinkRate(self.__HT16K33_BLINKRATE_OFF)

    # Set maximum brightness
    self.setBrightness(15)

    # Clear the screen
    self.clear()

  def setBrightness(self, brightness):
    "Sets the brightness level from 0..15"
    if (brightness > 15):
      brightness = 15
    self.i2c.write8(self.__HT16K33_REGISTER_DIMMING | brightness, 0x00)

  def setBlinkRate(self, blinkRate):
    "Sets the blink rate"
    if (blinkRate > self.__HT16K33_BLINKRATE_HALFHZ):
       blinkRate = self.__HT16K33_BLINKRATE_OFF
    self.i2c.write8(self.__HT16K33_REGISTER_DISPLAY_SETUP | 0x01 | (blinkRate << 1), 0x00)

  def setBufferRow(self, row, value, update=True):
    "Updates a single 16-bit entry in the 8*16-bit buffer"
    if (row > 7):
      return                    # Prevent buffer overflow
    self.__buffer[row] = value  # value # & 0xFFFF
    if (update):
      self.writeDisplay()       # Update the display

  def getBuffer(self):
    "Returns a copy of the raw buffer contents"
    bufferCopy = copy(self.__buffer)
    return bufferCopy
 
  def writeDisplay(self):
    "Updates the display memory"
    bytes = []
    for item in self.__buffer:
      bytes.append(item & 0xFF)
      bytes.append((item >> 8) & 0xFF)
    self.i2c.writeList(0x00, bytes)

  def clear(self, update=True):
    "Clears the display memory"
    self.__buffer = [ 0, 0, 0, 0, 0, 0, 0, 0 ]
    if (update):
      self.writeDisplay()

led = LEDBackpack(0x70)


########NEW FILE########
__FILENAME__ = ex_7segment_clock
#!/usr/bin/python

import time
import datetime
from Adafruit_7Segment import SevenSegment

# ===========================================================================
# Clock Example
# ===========================================================================
segment = SevenSegment(address=0x70)

print "Press CTRL+Z to exit"

# Continually update the time on a 4 char, 7-segment display
while(True):
  now = datetime.datetime.now()
  hour = now.hour
  minute = now.minute
  second = now.second
  # Set hours
  segment.writeDigit(0, int(hour / 10))     # Tens
  segment.writeDigit(1, hour % 10)          # Ones
  # Set minutes
  segment.writeDigit(3, int(minute / 10))   # Tens
  segment.writeDigit(4, minute % 10)        # Ones
  # Toggle color
  segment.setColon(second % 2)              # Toggle colon at 1Hz
  # Wait one second
  time.sleep(1)

########NEW FILE########
__FILENAME__ = ex_8x8_color_pixels
#!/usr/bin/python

import time
import datetime
from Adafruit_8x8 import ColorEightByEight

# ===========================================================================
# 8x8 Pixel Example
# ===========================================================================
grid = ColorEightByEight(address=0x70)

print "Press CTRL+Z to exit"

iter = 0

# Continually update the 8x8 display one pixel at a time
while(True):
  iter += 1

  for x in range(0, 8):
    for y in range(0, 8):
      grid.setPixel(x, y, iter % 4 )
      time.sleep(0.02)

########NEW FILE########
__FILENAME__ = ex_8x8_pixels
#!/usr/bin/python

import time
import datetime
from Adafruit_8x8 import EightByEight

# ===========================================================================
# 8x8 Pixel Example
# ===========================================================================
grid = EightByEight(address=0x70)

print "Press CTRL+Z to exit"

# Continually update the 8x8 display one pixel at a time
while(True):
  for x in range(0, 8):
    for y in range(0, 8):
      grid.setPixel(x, y)
      time.sleep(0.05)
  time.sleep(0.5)
  grid.clear()
  time.sleep(0.5)

########NEW FILE########
__FILENAME__ = Adafruit_LEDpixels
#!/usr/bin/env python

# Test code for Adafruit LED Pixels, uses hardware SPI

import RPi.GPIO as GPIO, time, os

DEBUG = 1
GPIO.setmode(GPIO.BCM)

def slowspiwrite(clockpin, datapin, byteout):
	GPIO.setup(clockpin, GPIO.OUT)
	GPIO.setup(datapin, GPIO.OUT)
	for i in range(8):
		if (byteout & 0x80):
			GPIO.output(datapin, True)
		else:
			GPIO.output(clockpin, False)
		byteout <<= 1
		GPIO.output(clockpin, True)
		GPIO.output(clockpin, False)


SPICLK = 18
SPIDO = 17

ledpixels = [0] * 25

def writestrip(pixels):
	spidev = file("/dev/spidev0.0", "w")
	for i in range(len(pixels)):
		spidev.write(chr((pixels[i]>>16) & 0xFF))
		spidev.write(chr((pixels[i]>>8) & 0xFF))
		spidev.write(chr(pixels[i] & 0xFF))
	spidev.close()
	time.sleep(0.002)

def Color(r, g, b):
	return ((r & 0xFF) << 16) | ((g & 0xFF) << 8) | (b & 0xFF)

def setpixelcolor(pixels, n, r, g, b):
	if (n >= len(pixels)):
		return
	pixels[n] = Color(r,g,b)

def setpixelcolor(pixels, n, c):
	if (n >= len(pixels)):
		return
	pixels[n] = c

def colorwipe(pixels, c, delay):
	for i in range(len(pixels)):
		setpixelcolor(pixels, i, c)
		writestrip(pixels)
		time.sleep(delay)		

def Wheel(WheelPos):
	if (WheelPos < 85):
   		return Color(WheelPos * 3, 255 - WheelPos * 3, 0)
	elif (WheelPos < 170):
   		WheelPos -= 85;
   		return Color(255 - WheelPos * 3, 0, WheelPos * 3)
	else:
		WheelPos -= 170;
		return Color(0, WheelPos * 3, 255 - WheelPos * 3)

def rainbowCycle(pixels, wait):
	for j in range(256): # one cycle of all 256 colors in the wheel
    	   for i in range(len(pixels)):
# tricky math! we use each pixel as a fraction of the full 96-color wheel
# (thats the i / strip.numPixels() part)
# Then add in j which makes the colors go around per pixel
# the % 96 is to make the wheel cycle around
      		setpixelcolor(pixels, i, Wheel( ((i * 256 / len(pixels)) + j) % 256) )
	   writestrip(pixels)
	   time.sleep(wait)

colorwipe(ledpixels, Color(255, 0, 0), 0.05)
colorwipe(ledpixels, Color(0, 255, 0), 0.05)
colorwipe(ledpixels, Color(0, 0, 255), 0.05)
while True:
	rainbowCycle(ledpixels, 0.00)

########NEW FILE########
__FILENAME__ = Adafruit_I2C
../Adafruit_I2C/Adafruit_I2C.py
########NEW FILE########
__FILENAME__ = Adafruit_LSM303
#!/usr/bin/python

# Python library for Adafruit Flora Accelerometer/Compass Sensor (LSM303).
# This is pretty much a direct port of the current Arduino library and is
# similarly incomplete (e.g. no orientation value returned from read()
# method).  This does add optional high resolution mode to accelerometer
# though.

# Copyright 2013 Adafruit Industries

# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.

from Adafruit_I2C import Adafruit_I2C


class Adafruit_LSM303(Adafruit_I2C):

    # Minimal constants carried over from Arduino library
    LSM303_ADDRESS_ACCEL = (0x32 >> 1)  # 0011001x
    LSM303_ADDRESS_MAG   = (0x3C >> 1)  # 0011110x
                                             # Default    Type
    LSM303_REGISTER_ACCEL_CTRL_REG1_A = 0x20 # 00000111   rw
    LSM303_REGISTER_ACCEL_CTRL_REG4_A = 0x23 # 00000000   rw
    LSM303_REGISTER_ACCEL_OUT_X_L_A   = 0x28
    LSM303_REGISTER_MAG_CRB_REG_M     = 0x01
    LSM303_REGISTER_MAG_MR_REG_M      = 0x02
    LSM303_REGISTER_MAG_OUT_X_H_M     = 0x03

    # Gain settings for setMagGain()
    LSM303_MAGGAIN_1_3 = 0x20 # +/- 1.3
    LSM303_MAGGAIN_1_9 = 0x40 # +/- 1.9
    LSM303_MAGGAIN_2_5 = 0x60 # +/- 2.5
    LSM303_MAGGAIN_4_0 = 0x80 # +/- 4.0
    LSM303_MAGGAIN_4_7 = 0xA0 # +/- 4.7
    LSM303_MAGGAIN_5_6 = 0xC0 # +/- 5.6
    LSM303_MAGGAIN_8_1 = 0xE0 # +/- 8.1


    def __init__(self, busnum=-1, debug=False, hires=False):

        # Accelerometer and magnetometer are at different I2C
        # addresses, so invoke a separate I2C instance for each
        self.accel = Adafruit_I2C(self.LSM303_ADDRESS_ACCEL, busnum, debug)
        self.mag   = Adafruit_I2C(self.LSM303_ADDRESS_MAG  , busnum, debug)

        # Enable the accelerometer
        self.accel.write8(self.LSM303_REGISTER_ACCEL_CTRL_REG1_A, 0x27)
        # Select hi-res (12-bit) or low-res (10-bit) output mode.
        # Low-res mode uses less power and sustains a higher update rate,
        # output is padded to compatible 12-bit units.
        if hires:
            self.accel.write8(self.LSM303_REGISTER_ACCEL_CTRL_REG4_A,
              0b00001000)
        else:
            self.accel.write8(self.LSM303_REGISTER_ACCEL_CTRL_REG4_A, 0)
  
        # Enable the magnetometer
        self.mag.write8(self.LSM303_REGISTER_MAG_MR_REG_M, 0x00)


    # Interpret signed 12-bit acceleration component from list
    def accel12(self, list, idx):
        n = list[idx] | (list[idx+1] << 8) # Low, high bytes
        if n > 32767: n -= 65536           # 2's complement signed
        return n >> 4                      # 12-bit resolution


    # Interpret signed 16-bit magnetometer component from list
    def mag16(self, list, idx):
        n = (list[idx] << 8) | list[idx+1]   # High, low bytes
        return n if n < 32768 else n - 65536 # 2's complement signed


    def read(self):
        # Read the accelerometer
        list = self.accel.readList(
          self.LSM303_REGISTER_ACCEL_OUT_X_L_A | 0x80, 6)
        res = [( self.accel12(list, 0),
                 self.accel12(list, 2),
                 self.accel12(list, 4) )]

        # Read the magnetometer
        list = self.mag.readList(self.LSM303_REGISTER_MAG_OUT_X_H_M, 6)
        res.append((self.mag16(list, 0),
                    self.mag16(list, 2),
                    self.mag16(list, 4),
                    0.0 )) # ToDo: Calculate orientation

        return res


    def setMagGain(gain=LSM303_MAGGAIN_1_3):
        self.mag.write8( LSM303_REGISTER_MAG_CRB_REG_M, gain)


# Simple example prints accel/mag data once per second:
if __name__ == '__main__':

    from time import sleep

    lsm = Adafruit_LSM303()

    print '[(Accelerometer X, Y, Z), (Magnetometer X, Y, Z, orientation)]'
    while True:
        print lsm.read()
        sleep(1) # Output is fun to watch if this is commented out

########NEW FILE########
__FILENAME__ = Adafruit_I2C
../Adafruit_I2C/Adafruit_I2C.py
########NEW FILE########
__FILENAME__ = Adafruit_MCP230xx
#!/usr/bin/python

# Copyright 2012 Daniel Berlin (with some changes by Adafruit Industries/Limor Fried)
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal  MCP230XX_GPIO(1, 0xin
# the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
# of the Software, and to permit persons to whom the Software is furnished to do
# so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

from Adafruit_I2C import Adafruit_I2C
import smbus
import time

MCP23017_IODIRA = 0x00
MCP23017_IODIRB = 0x01
MCP23017_GPIOA  = 0x12
MCP23017_GPIOB  = 0x13
MCP23017_GPPUA  = 0x0C
MCP23017_GPPUB  = 0x0D
MCP23017_OLATA  = 0x14
MCP23017_OLATB  = 0x15
MCP23008_GPIOA  = 0x09
MCP23008_GPPUA  = 0x06
MCP23008_OLATA  = 0x0A

class Adafruit_MCP230XX(object):
    OUTPUT = 0
    INPUT = 1

    def __init__(self, address, num_gpios):
        assert num_gpios >= 0 and num_gpios <= 16, "Number of GPIOs must be between 0 and 16"
        self.i2c = Adafruit_I2C(address=address)
        self.address = address
        self.num_gpios = num_gpios

        # set defaults
        if num_gpios <= 8:
            self.i2c.write8(MCP23017_IODIRA, 0xFF)  # all inputs on port A
            self.direction = self.i2c.readU8(MCP23017_IODIRA)
            self.i2c.write8(MCP23008_GPPUA, 0x00)
        elif num_gpios > 8 and num_gpios <= 16:
            self.i2c.write8(MCP23017_IODIRA, 0xFF)  # all inputs on port A
            self.i2c.write8(MCP23017_IODIRB, 0xFF)  # all inputs on port B
            self.direction = self.i2c.readU8(MCP23017_IODIRA)
            self.direction |= self.i2c.readU8(MCP23017_IODIRB) << 8
            self.i2c.write8(MCP23017_GPPUA, 0x00)
            self.i2c.write8(MCP23017_GPPUB, 0x00)

    def _changebit(self, bitmap, bit, value):
        assert value == 1 or value == 0, "Value is %s must be 1 or 0" % value
        if value == 0:
            return bitmap & ~(1 << bit)
        elif value == 1:
            return bitmap | (1 << bit)

    def _readandchangepin(self, port, pin, value, currvalue = None):
        assert pin >= 0 and pin < self.num_gpios, "Pin number %s is invalid, only 0-%s are valid" % (pin, self.num_gpios)
        #assert self.direction & (1 << pin) == 0, "Pin %s not set to output" % pin
        if not currvalue:
             currvalue = self.i2c.readU8(port)
        newvalue = self._changebit(currvalue, pin, value)
        self.i2c.write8(port, newvalue)
        return newvalue


    def pullup(self, pin, value):
        if self.num_gpios <= 8:
            return self._readandchangepin(MCP23008_GPPUA, pin, value)
        if self.num_gpios <= 16:
            lvalue = self._readandchangepin(MCP23017_GPPUA, pin, value)
            if (pin < 8):
                return
            else:
                return self._readandchangepin(MCP23017_GPPUB, pin-8, value) << 8

    # Set pin to either input or output mode
    def config(self, pin, mode):
        if self.num_gpios <= 8:
            self.direction = self._readandchangepin(MCP23017_IODIRA, pin, mode)
        if self.num_gpios <= 16:
            if (pin < 8):
                self.direction = self._readandchangepin(MCP23017_IODIRA, pin, mode)
            else:
                self.direction |= self._readandchangepin(MCP23017_IODIRB, pin-8, mode) << 8

        return self.direction

    def output(self, pin, value):
        # assert self.direction & (1 << pin) == 0, "Pin %s not set to output" % pin
        if self.num_gpios <= 8:
            self.outputvalue = self._readandchangepin(MCP23008_GPIOA, pin, value, self.i2c.readU8(MCP23008_OLATA))
        if self.num_gpios <= 16:
            if (pin < 8):
                self.outputvalue = self._readandchangepin(MCP23017_GPIOA, pin, value, self.i2c.readU8(MCP23017_OLATA))
            else:
                self.outputvalue = self._readandchangepin(MCP23017_GPIOB, pin-8, value, self.i2c.readU8(MCP23017_OLATB)) << 8

        return self.outputvalue


        self.outputvalue = self._readandchangepin(MCP23017_IODIRA, pin, value, self.outputvalue)
        return self.outputvalue

    def input(self, pin):
        assert pin >= 0 and pin < self.num_gpios, "Pin number %s is invalid, only 0-%s are valid" % (pin, self.num_gpios)
        assert self.direction & (1 << pin) != 0, "Pin %s not set to input" % pin
        if self.num_gpios <= 8:
            value = self.i2c.readU8(MCP23008_GPIOA)
        elif self.num_gpios > 8 and self.num_gpios <= 16:
            value = self.i2c.readU8(MCP23017_GPIOA)
            value |= self.i2c.readU8(MCP23017_GPIOB) << 8
        return value & (1 << pin)

    def readU8(self):
        result = self.i2c.readU8(MCP23008_OLATA)
        return(result)

    def readS8(self):
        result = self.i2c.readU8(MCP23008_OLATA)
        if (result > 127): result -= 256
        return result

    def readU16(self):
        assert self.num_gpios >= 16, "16bits required"
        lo = self.i2c.readU8(MCP23017_OLATA)
        hi = self.i2c.readU8(MCP23017_OLATB)
        return((hi << 8) | lo)

    def readS16(self):
        assert self.num_gpios >= 16, "16bits required"
        lo = self.i2c.readU8(MCP23017_OLATA)
        hi = self.i2c.readU8(MCP23017_OLATB)
        if (hi > 127): hi -= 256
        return((hi << 8) | lo)

    def write8(self, value):
        self.i2c.write8(MCP23008_OLATA, value)

    def write16(self, value):
        assert self.num_gpios >= 16, "16bits required"
        self.i2c.write8(MCP23017_OLATA, value & 0xFF)
        self.i2c.write8(MCP23017_OLATB, (value >> 8) & 0xFF)

# RPi.GPIO compatible interface for MCP23017 and MCP23008

class MCP230XX_GPIO(object):
    OUT = 0
    IN = 1
    BCM = 0
    BOARD = 0
    def __init__(self, busnum, address, num_gpios):
        self.chip = Adafruit_MCP230XX(busnum, address, num_gpios)
    def setmode(self, mode):
        # do nothing
        pass
    def setup(self, pin, mode):
        self.chip.config(pin, mode)
    def input(self, pin):
        return self.chip.input(pin)
    def output(self, pin, value):
        self.chip.output(pin, value)
    def pullup(self, pin, value):
        self.chip.pullup(pin, value)


if __name__ == '__main__':
    # ***************************************************
    # Set num_gpios to 8 for MCP23008 or 16 for MCP23017!
    # ***************************************************
    mcp = Adafruit_MCP230XX(address = 0x20, num_gpios = 8) # MCP23008
    # mcp = Adafruit_MCP230XX(address = 0x20, num_gpios = 16) # MCP23017

    # Set pins 0, 1 and 2 to output (you can set pins 0..15 this way)
    mcp.config(0, mcp.OUTPUT)
    mcp.config(1, mcp.OUTPUT)
    mcp.config(2, mcp.OUTPUT)

    # Set pin 3 to input with the pullup resistor enabled
    mcp.config(3, mcp.INPUT)
    mcp.pullup(3, 1)

    # Read input pin and display the results
    print "Pin 3 = %d" % (mcp.input(3) >> 3)

    # Python speed test on output 0 toggling at max speed
    print "Starting blinky on pin 0 (CTRL+C to quit)"
    while (True):
      mcp.output(0, 1)  # Pin 0 High
      time.sleep(1);
      mcp.output(0, 0)  # Pin 0 Low
      time.sleep(1);

########NEW FILE########
__FILENAME__ = MCP3002
#!/usr/bin/env python

# just some bitbang code for testing both channels

import RPi.GPIO as GPIO, time, os

DEBUG = 1
GPIO.setmode(GPIO.BCM)

# this function is not used, its for future reference!
def slowspiwrite(clockpin, datapin, byteout):
	GPIO.setup(clockpin, GPIO.OUT)
	GPIO.setup(datapin, GPIO.OUT)
	for i in range(8):
		if (byteout & 0x80):
			GPIO.output(datapin, True)
		else:
			GPIO.output(datapin, False)
		byteout <<= 1
		GPIO.output(clockpin, True)
		GPIO.output(clockpin, False)

# this function is not used, its for future reference!
def slowspiread(clockpin, datapin):
	GPIO.setup(clockpin, GPIO.OUT)
	GPIO.setup(datapin, GPIO.IN)
	byteout = 0
	for i in range(8):
		GPIO.output(clockpin, False)
		GPIO.output(clockpin, True)
		byteout <<= 1
		if (GPIO.input(datapin)):
			byteout = byteout | 0x1
	return byteout

# read SPI data from MCP3002 chip, 2 possible adc's (0 thru 1)
def readadc(adcnum, clockpin, mosipin, misopin, cspin):
    if ((adcnum > 1) or (adcnum < 0)):
        return -1
    GPIO.output(cspin, True)
    
    GPIO.output(clockpin, False)  # start clock low
    GPIO.output(cspin, False)     # bring CS low
    
    commandout = adcnum << 1;
    commandout |= 0x0D  # start bit + single-ended bit + MSBF bit
    commandout <<= 4    # we only need to send 4 bits here
    
    for i in range(4):
        if (commandout & 0x80):
            GPIO.output(mosipin, True)
        else:
            GPIO.output(mosipin, False)
        commandout <<= 1
        GPIO.output(clockpin, True)
        GPIO.output(clockpin, False)
    
    adcout = 0
    
    # read in one null bit and 10 ADC bits
    for i in range(11):
        GPIO.output(clockpin, True)
        GPIO.output(clockpin, False)
        adcout <<= 1
        if (GPIO.input(misopin)):
            adcout |= 0x1
    GPIO.output(cspin, True)
    
    adcout /= 2       # first bit is 'null' so drop it
    return adcout
# change these as desired
SPICLK = 18
SPIMOSI = 17
SPIMISO = 21
SPICS = 22

# set up the SPI interface pins
GPIO.setup(SPIMOSI, GPIO.OUT)
GPIO.setup(SPIMISO, GPIO.IN)
GPIO.setup(SPICLK, GPIO.OUT)
GPIO.setup(SPICS, GPIO.OUT)

# Note that bitbanging SPI is incredibly slow on the Pi as its not
# a RTOS - reading the ADC takes about 30 ms (~30 samples per second)
# which is awful for a microcontroller but better-than-nothing for Linux

print "| #0 \t #1|"
print "-----------------------------------------------------------------"
while True:
	print "|",
	for adcnum in range(2):
		ret = readadc(adcnum, SPICLK, SPIMOSI, SPIMISO, SPICS)
		print ret,"\t",
	print "|"

########NEW FILE########
__FILENAME__ = mcp3008
#!/usr/bin/env python

# just some bitbang code for testing all 8 channels

import RPi.GPIO as GPIO, time, os

DEBUG = 1
GPIO.setmode(GPIO.BCM)

# this function is not used, its for future reference!
def slowspiwrite(clockpin, datapin, byteout):
	GPIO.setup(clockpin, GPIO.OUT)
	GPIO.setup(datapin, GPIO.OUT)
	for i in range(8):
		if (byteout & 0x80):
			GPIO.output(datapin, True)
		else:
			GPIO.output(datapin, False)
		byteout <<= 1
		GPIO.output(clockpin, True)
		GPIO.output(clockpin, False)

# this function is not used, its for future reference!
def slowspiread(clockpin, datapin):
	GPIO.setup(clockpin, GPIO.OUT)
	GPIO.setup(datapin, GPIO.IN)
	byteout = 0
	for i in range(8):
		GPIO.output(clockpin, False)
		GPIO.output(clockpin, True)
		byteout <<= 1
		if (GPIO.input(datapin)):
			byteout = byteout | 0x1
	return byteout

# read SPI data from MCP3008 chip, 8 possible adc's (0 thru 7)
def readadc(adcnum, clockpin, mosipin, misopin, cspin):
	if ((adcnum > 7) or (adcnum < 0)):
		return -1
	GPIO.output(cspin, True)

	GPIO.output(clockpin, False)  # start clock low
	GPIO.output(cspin, False)     # bring CS low

	commandout = adcnum
	commandout |= 0x18  # start bit + single-ended bit
	commandout <<= 3    # we only need to send 5 bits here
	for i in range(5):
		if (commandout & 0x80):
			GPIO.output(mosipin, True)
		else:
   			GPIO.output(mosipin, False)
                commandout <<= 1
                GPIO.output(clockpin, True)
                GPIO.output(clockpin, False)

	adcout = 0
	# read in one empty bit, one null bit and 10 ADC bits
	for i in range(12):
		GPIO.output(clockpin, True)
		GPIO.output(clockpin, False)
		adcout <<= 1
		if (GPIO.input(misopin)):
			adcout |= 0x1

	GPIO.output(cspin, True)

	adcout /= 2       # first bit is 'null' so drop it
	return adcout
	
# change these as desired
SPICLK = 18
SPIMOSI = 17
SPIMISO = 21
SPICS = 22

# set up the SPI interface pins 
GPIO.setup(SPIMOSI, GPIO.OUT)
GPIO.setup(SPIMISO, GPIO.IN)
GPIO.setup(SPICLK, GPIO.OUT)
GPIO.setup(SPICS, GPIO.OUT)

# Note that bitbanging SPI is incredibly slow on the Pi as its not
# a RTOS - reading the ADC takes about 30 ms (~30 samples per second)
# which is awful for a microcontroller but better-than-nothing for Linux

print "| #0 \t #1 \t #2 \t #3 \t #4 \t #5 \t #6 \t #7\t|"
print "-----------------------------------------------------------------"
while True:
	print "|",
	for adcnum in range(8):
		ret = readadc(adcnum, SPICLK, SPIMOSI, SPIMISO, SPICS)
		print ret,"\t",
	print "|"

########NEW FILE########
__FILENAME__ = Adafruit_I2C
../Adafruit_I2C/Adafruit_I2C.py
########NEW FILE########
__FILENAME__ = Adafruit_MCP4725
#!/usr/bin/python

from Adafruit_I2C import Adafruit_I2C

# ============================================================================
# Adafruit MCP4725 12-Bit DAC
# ============================================================================

class MCP4725 :
  i2c = None
  
  # Registers
  __REG_WRITEDAC         = 0x40
  __REG_WRITEDACEEPROM   = 0x60

  # Constructor
  def __init__(self, address=0x62, debug=False):
    self.i2c = Adafruit_I2C(address)
    self.address = address
    self.debug = debug

  def setVoltage(self, voltage, persist=False):
    "Sets the output voltage to the specified value"
    if (voltage > 4095):
      voltage = 4095
    if (voltage < 0):
      voltage = 0
    if (self.debug):
      print "Setting voltage to %04d" % voltage
    # Value needs to be left-shifted four bytes for the MCP4725
    bytes = [(voltage >> 4) & 0xFF, (voltage << 4) & 0xFF]
    if (persist):
      self.i2c.writeList(self.__REG_WRITEDACEEPROM, bytes)
    else:
      self.i2c.writeList(self.__REG_WRITEDAC, bytes)

########NEW FILE########
__FILENAME__ = sinewave
#!/usr/bin/python

from Adafruit_MCP4725 import MCP4725
import time

# Set this value to 9, 8, 7, 6 or 5 to adjust the resolution
DAC_RESOLUTION    = 9

# 9-Bit Lookup Table (512 values)
DACLookup_FullSine_9Bit = \
[ 2048, 2073, 2098, 2123, 2148, 2174, 2199, 2224,
  2249, 2274, 2299, 2324, 2349, 2373, 2398, 2423,
  2448, 2472, 2497, 2521, 2546, 2570, 2594, 2618,
  2643, 2667, 2690, 2714, 2738, 2762, 2785, 2808,
  2832, 2855, 2878, 2901, 2924, 2946, 2969, 2991,
  3013, 3036, 3057, 3079, 3101, 3122, 3144, 3165,
  3186, 3207, 3227, 3248, 3268, 3288, 3308, 3328,
  3347, 3367, 3386, 3405, 3423, 3442, 3460, 3478,
  3496, 3514, 3531, 3548, 3565, 3582, 3599, 3615,
  3631, 3647, 3663, 3678, 3693, 3708, 3722, 3737,
  3751, 3765, 3778, 3792, 3805, 3817, 3830, 3842,
  3854, 3866, 3877, 3888, 3899, 3910, 3920, 3930,
  3940, 3950, 3959, 3968, 3976, 3985, 3993, 4000,
  4008, 4015, 4022, 4028, 4035, 4041, 4046, 4052,
  4057, 4061, 4066, 4070, 4074, 4077, 4081, 4084,
  4086, 4088, 4090, 4092, 4094, 4095, 4095, 4095,
  4095, 4095, 4095, 4095, 4094, 4092, 4090, 4088,
  4086, 4084, 4081, 4077, 4074, 4070, 4066, 4061,
  4057, 4052, 4046, 4041, 4035, 4028, 4022, 4015,
  4008, 4000, 3993, 3985, 3976, 3968, 3959, 3950,
  3940, 3930, 3920, 3910, 3899, 3888, 3877, 3866,
  3854, 3842, 3830, 3817, 3805, 3792, 3778, 3765,
  3751, 3737, 3722, 3708, 3693, 3678, 3663, 3647,
  3631, 3615, 3599, 3582, 3565, 3548, 3531, 3514,
  3496, 3478, 3460, 3442, 3423, 3405, 3386, 3367,
  3347, 3328, 3308, 3288, 3268, 3248, 3227, 3207,
  3186, 3165, 3144, 3122, 3101, 3079, 3057, 3036,
  3013, 2991, 2969, 2946, 2924, 2901, 2878, 2855,
  2832, 2808, 2785, 2762, 2738, 2714, 2690, 2667,
  2643, 2618, 2594, 2570, 2546, 2521, 2497, 2472,
  2448, 2423, 2398, 2373, 2349, 2324, 2299, 2274,
  2249, 2224, 2199, 2174, 2148, 2123, 2098, 2073,
  2048, 2023, 1998, 1973, 1948, 1922, 1897, 1872,
  1847, 1822, 1797, 1772, 1747, 1723, 1698, 1673,
  1648, 1624, 1599, 1575, 1550, 1526, 1502, 1478,
  1453, 1429, 1406, 1382, 1358, 1334, 1311, 1288,
  1264, 1241, 1218, 1195, 1172, 1150, 1127, 1105,
  1083, 1060, 1039, 1017,  995,  974,  952,  931,
   910,  889,  869,  848,  828,  808,  788,  768,
   749,  729,  710,  691,  673,  654,  636,  618,
   600,  582,  565,  548,  531,  514,  497,  481,
   465,  449,  433,  418,  403,  388,  374,  359,
   345,  331,  318,  304,  291,  279,  266,  254,
   242,  230,  219,  208,  197,  186,  176,  166,
   156,  146,  137,  128,  120,  111,  103,   96,
    88,   81,   74,   68,   61,   55,   50,   44,
    39,   35,   30,   26,   22,   19,   15,   12,
    10,    8,    6,    4,    2,    1,    1,    0,
     0,    0,    1,    1,    2,    4,    6,    8,
    10,   12,   15,   19,   22,   26,   30,   35,
    39,   44,   50,   55,   61,   68,   74,   81,
    88,   96,  103,  111,  120,  128,  137,  146,
   156,  166,  176,  186,  197,  208,  219,  230,
   242,  254,  266,  279,  291,  304,  318,  331,
   345,  359,  374,  388,  403,  418,  433,  449,
   465,  481,  497,  514,  531,  548,  565,  582,
   600,  618,  636,  654,  673,  691,  710,  729,
   749,  768,  788,  808,  828,  848,  869,  889,
   910,  931,  952,  974,  995, 1017, 1039, 1060,
  1083, 1105, 1127, 1150, 1172, 1195, 1218, 1241,
  1264, 1288, 1311, 1334, 1358, 1382, 1406, 1429,
  1453, 1478, 1502, 1526, 1550, 1575, 1599, 1624,
  1648, 1673, 1698, 1723, 1747, 1772, 1797, 1822,
  1847, 1872, 1897, 1922, 1948, 1973, 1998, 2023 ]

# 8-bit Lookup Table (256 values)
DACLookup_FullSine_8Bit = \
[ 2048, 2098, 2148, 2198, 2248, 2298, 2348, 2398,
  2447, 2496, 2545, 2594, 2642, 2690, 2737, 2784,
  2831, 2877, 2923, 2968, 3013, 3057, 3100, 3143,
  3185, 3226, 3267, 3307, 3346, 3385, 3423, 3459,
  3495, 3530, 3565, 3598, 3630, 3662, 3692, 3722,
  3750, 3777, 3804, 3829, 3853, 3876, 3898, 3919,
  3939, 3958, 3975, 3992, 4007, 4021, 4034, 4045,
  4056, 4065, 4073, 4080, 4085, 4089, 4093, 4094,
  4095, 4094, 4093, 4089, 4085, 4080, 4073, 4065,
  4056, 4045, 4034, 4021, 4007, 3992, 3975, 3958,
  3939, 3919, 3898, 3876, 3853, 3829, 3804, 3777,
  3750, 3722, 3692, 3662, 3630, 3598, 3565, 3530,
  3495, 3459, 3423, 3385, 3346, 3307, 3267, 3226,
  3185, 3143, 3100, 3057, 3013, 2968, 2923, 2877,
  2831, 2784, 2737, 2690, 2642, 2594, 2545, 2496,
  2447, 2398, 2348, 2298, 2248, 2198, 2148, 2098,
  2048, 1997, 1947, 1897, 1847, 1797, 1747, 1697,
  1648, 1599, 1550, 1501, 1453, 1405, 1358, 1311,
  1264, 1218, 1172, 1127, 1082, 1038,  995,  952,
   910,  869,  828,  788,  749,  710,  672,  636,
   600,  565,  530,  497,  465,  433,  403,  373,
   345,  318,  291,  266,  242,  219,  197,  176,
   156,  137,  120,  103,   88,   74,   61,   50,
    39,   30,   22,   15,   10,    6,    2,    1,
     0,    1,    2,    6,   10,   15,   22,   30,
    39,   50,   61,   74,   88,  103,  120,  137,
   156,  176,  197,  219,  242,  266,  291,  318,
   345,  373,  403,  433,  465,  497,  530,  565,
   600,  636,  672,  710,  749,  788,  828,  869,
   910,  952,  995, 1038, 1082, 1127, 1172, 1218,
  1264, 1311, 1358, 1405, 1453, 1501, 1550, 1599,
  1648, 1697, 1747, 1797, 1847, 1897, 1947, 1997 ]

# 7-bit Lookup Table (128 values)
DACLookup_FullSine_7Bit = \
[ 2048, 2148, 2248, 2348, 2447, 2545, 2642, 2737,
  2831, 2923, 3013, 3100, 3185, 3267, 3346, 3423,
  3495, 3565, 3630, 3692, 3750, 3804, 3853, 3898,
  3939, 3975, 4007, 4034, 4056, 4073, 4085, 4093,
  4095, 4093, 4085, 4073, 4056, 4034, 4007, 3975,
  3939, 3898, 3853, 3804, 3750, 3692, 3630, 3565,
  3495, 3423, 3346, 3267, 3185, 3100, 3013, 2923,
  2831, 2737, 2642, 2545, 2447, 2348, 2248, 2148,
  2048, 1947, 1847, 1747, 1648, 1550, 1453, 1358,
  1264, 1172, 1082,  995,  910,  828,  749,  672,
   600,  530,  465,  403,  345,  291,  242,  197,
   156,  120,   88,   61,   39,   22,   10,    2,
     0,    2,   10,   22,   39,   61,   88,  120,
   156,  197,  242,  291,  345,  403,  465,  530,
   600,  672,  749,  828,  910,  995, 1082, 1172,
  1264, 1358, 1453, 1550, 1648, 1747, 1847, 1947 ]

# 6-bit Lookup Table (64 values)
DACLookup_FullSine_6Bit = \
[ 2048, 2248, 2447, 2642, 2831, 3013, 3185, 3346,
  3495, 3630, 3750, 3853, 3939, 4007, 4056, 4085,
  4095, 4085, 4056, 4007, 3939, 3853, 3750, 3630,
  3495, 3346, 3185, 3013, 2831, 2642, 2447, 2248,
  2048, 1847, 1648, 1453, 1264, 1082,  910,  749,
   600,  465,  345,  242,  156,   88,   39,   10,
     0,   10,   39,   88,  156,  242,  345,  465,
   600,  749,  910, 1082, 1264, 1453, 1648, 1847 ]

# 5-bit Lookup Table (32 values)
DACLookup_FullSine_5Bit = \
[ 2048, 2447, 2831, 3185, 3495, 3750, 3939, 4056,
  4095, 4056, 3939, 3750, 3495, 3185, 2831, 2447,
  2048, 1648, 1264,  910,  600,  345,  156,   39,
     0,   39,  156,  345,  600,  910, 1264, 1648 ]

# Initialise the DAC using the default address
dac = MCP4725(0x62)

if (DAC_RESOLUTION < 5) | (DAC_RESOLUTION > 9):
  print "Invalid DAC resolution: Set DAC_RESOLUTION from 5..9"
else:
  print "Generating a sine wave with %d-bit resolution" % DAC_RESOLUTION
  print "Press CTRL+C to stop"
  while(True):
    if (DAC_RESOLUTION == 9):
      for val in DACLookup_FullSine_9Bit:
        dac.setVoltage(val)
    if (DAC_RESOLUTION == 8):
      for val in DACLookup_FullSine_8Bit:
        dac.setVoltage(val)
    if (DAC_RESOLUTION == 7):
       for val in DACLookup_FullSine_7Bit:
        dac.setVoltage(val)
    if (DAC_RESOLUTION == 6):
      for val in DACLookup_FullSine_6Bit:
        dac.setVoltage(val)
    if (DAC_RESOLUTION == 5):
      for val in DACLookup_FullSine_5Bit:
        dac.setVoltage(val)


########NEW FILE########
__FILENAME__ = Adafruit_I2C
../Adafruit_I2C/Adafruit_I2C.py
########NEW FILE########
__FILENAME__ = Adafruit_PWM_Servo_Driver
#!/usr/bin/python

import time
import math
from Adafruit_I2C import Adafruit_I2C

# ============================================================================
# Adafruit PCA9685 16-Channel PWM Servo Driver
# ============================================================================

class PWM :
  i2c = None

  # Registers/etc.
  __SUBADR1            = 0x02
  __SUBADR2            = 0x03
  __SUBADR3            = 0x04
  __MODE1              = 0x00
  __PRESCALE           = 0xFE
  __LED0_ON_L          = 0x06
  __LED0_ON_H          = 0x07
  __LED0_OFF_L         = 0x08
  __LED0_OFF_H         = 0x09
  __ALLLED_ON_L        = 0xFA
  __ALLLED_ON_H        = 0xFB
  __ALLLED_OFF_L       = 0xFC
  __ALLLED_OFF_H       = 0xFD

  def __init__(self, address=0x40, debug=False):
    self.i2c = Adafruit_I2C(address)
    self.address = address
    self.debug = debug
    if (self.debug):
      print "Reseting PCA9685"
    self.i2c.write8(self.__MODE1, 0x00)

  def setPWMFreq(self, freq):
    "Sets the PWM frequency"
    prescaleval = 25000000.0    # 25MHz
    prescaleval /= 4096.0       # 12-bit
    prescaleval /= float(freq)
    prescaleval -= 1.0
    if (self.debug):
      print "Setting PWM frequency to %d Hz" % freq
      print "Estimated pre-scale: %d" % prescaleval
    prescale = math.floor(prescaleval + 0.5)
    if (self.debug):
      print "Final pre-scale: %d" % prescale

    oldmode = self.i2c.readU8(self.__MODE1);
    newmode = (oldmode & 0x7F) | 0x10             # sleep
    self.i2c.write8(self.__MODE1, newmode)        # go to sleep
    self.i2c.write8(self.__PRESCALE, int(math.floor(prescale)))
    self.i2c.write8(self.__MODE1, oldmode)
    time.sleep(0.005)
    self.i2c.write8(self.__MODE1, oldmode | 0x80)

  def setPWM(self, channel, on, off):
    "Sets a single PWM channel"
    self.i2c.write8(self.__LED0_ON_L+4*channel, on & 0xFF)
    self.i2c.write8(self.__LED0_ON_H+4*channel, on >> 8)
    self.i2c.write8(self.__LED0_OFF_L+4*channel, off & 0xFF)
    self.i2c.write8(self.__LED0_OFF_H+4*channel, off >> 8)





########NEW FILE########
__FILENAME__ = Servo_Example
#!/usr/bin/python

from Adafruit_PWM_Servo_Driver import PWM
import time

# ===========================================================================
# Example Code
# ===========================================================================

# Initialise the PWM device using the default address
# bmp = PWM(0x40, debug=True)
pwm = PWM(0x40, debug=True)

servoMin = 150  # Min pulse length out of 4096
servoMax = 600  # Max pulse length out of 4096

def setServoPulse(channel, pulse):
  pulseLength = 1000000                   # 1,000,000 us per second
  pulseLength /= 60                       # 60 Hz
  print "%d us per period" % pulseLength
  pulseLength /= 4096                     # 12 bits of resolution
  print "%d us per bit" % pulseLength
  pulse *= 1000
  pulse /= pulseLength
  pwm.setPWM(channel, 0, pulse)

pwm.setPWMFreq(60)                        # Set frequency to 60 Hz
while (True):
  # Change speed of continuous servo on channel O
  pwm.setPWM(0, 0, servoMin)
  time.sleep(1)
  pwm.setPWM(0, 0, servoMax)
  time.sleep(1)




########NEW FILE########
__FILENAME__ = Adafruit_I2C
#!/usr/bin/python

import smbus

# ===========================================================================
# Adafruit_I2C Class
# ===========================================================================

class Adafruit_I2C :

  @staticmethod
  def getPiRevision():
    "Gets the version number of the Raspberry Pi board"
    # Courtesy quick2wire-python-api
    # https://github.com/quick2wire/quick2wire-python-api
    try:
      with open('/proc/cpuinfo','r') as f:
        for line in f:
          if line.startswith('Revision'):
            return 1 if line.rstrip()[-1] in ['1','2'] else 2
    except:
      return 0

  @staticmethod
  def getPiI2CBusNumber():
    # Gets the I2C bus number /dev/i2c#
    return 1 if Adafruit_I2C.getPiRevision() > 1 else 0
 
  def __init__(self, address, busnum=-1, debug=False):
    self.address = address
    # By default, the correct I2C bus is auto-detected using /proc/cpuinfo
    # Alternatively, you can hard-code the bus version below:
    # self.bus = smbus.SMBus(0); # Force I2C0 (early 256MB Pi's)
    # self.bus = smbus.SMBus(1); # Force I2C1 (512MB Pi's)
    self.bus = smbus.SMBus(
      busnum if busnum >= 0 else Adafruit_I2C.getPiI2CBusNumber())
    self.debug = debug

  def reverseByteOrder(self, data):
    "Reverses the byte order of an int (16-bit) or long (32-bit) value"
    # Courtesy Vishal Sapre
    byteCount = len(hex(data)[2:].replace('L','')[::2])
    val       = 0
    for i in range(byteCount):
      val    = (val << 8) | (data & 0xff)
      data >>= 8
    return val

  def errMsg(self):
    print "Error accessing 0x%02X: Check your I2C address" % self.address
    return -1

  def write8(self, reg, value):
    "Writes an 8-bit value to the specified register/address"
    try:
      self.bus.write_byte_data(self.address, reg, value)
      if self.debug:
        print "I2C: Wrote 0x%02X to register 0x%02X" % (value, reg)
    except IOError, err:
      return self.errMsg()

  def write16(self, reg, value):
    "Writes a 16-bit value to the specified register/address pair"
    try:
      self.bus.write_word_data(self.address, reg, value)
      if self.debug:
        print ("I2C: Wrote 0x%02X to register pair 0x%02X,0x%02X" %
         (value, reg, reg+1))
    except IOError, err:
      return self.errMsg()

  def writeList(self, reg, list):
    "Writes an array of bytes using I2C format"
    try:
      if self.debug:
        print "I2C: Writing list to register 0x%02X:" % reg
        print list
      self.bus.write_i2c_block_data(self.address, reg, list)
    except IOError, err:
      return self.errMsg()

  def readList(self, reg, length):
    "Read a list of bytes from the I2C device"
    try:
      results = self.bus.read_i2c_block_data(self.address, reg, length)
      if self.debug:
        print ("I2C: Device 0x%02X returned the following from reg 0x%02X" %
         (self.address, reg))
        print results
      return results
    except IOError, err:
      return self.errMsg()

  def readU8(self, reg):
    "Read an unsigned byte from the I2C device"
    try:
      result = self.bus.read_byte_data(self.address, reg)
      if self.debug:
        print ("I2C: Device 0x%02X returned 0x%02X from reg 0x%02X" %
         (self.address, result & 0xFF, reg))
      return result
    except IOError, err:
      return self.errMsg()

  def readS8(self, reg):
    "Reads a signed byte from the I2C device"
    try:
      result = self.bus.read_byte_data(self.address, reg)
      if result > 127: result -= 256
      if self.debug:
        print ("I2C: Device 0x%02X returned 0x%02X from reg 0x%02X" %
         (self.address, result & 0xFF, reg))
      return result
    except IOError, err:
      return self.errMsg()

  def readU16(self, reg):
    "Reads an unsigned 16-bit value from the I2C device"
    try:
      hibyte = self.readU8(reg)
      lobyte = self.readU8(reg+1)
      result = (hibyte << 8) + lobyte
      if (self.debug):
        print "I2C: Device 0x%02X returned 0x%04X from reg 0x%02X" % (self.address, result & 0xFFFF, reg)
      return result
    except IOError, err:
      return self.errMsg()

  def readS16(self, reg):
    "Reads a signed 16-bit value from the I2C device"
    try:
      hibyte = self.readS8(reg)
      lobyte = self.readU8(reg+1)
      result = (hibyte << 8) + lobyte
      if (self.debug):
        print "I2C: Device 0x%02X returned 0x%04X from reg 0x%02X" % (self.address, result & 0xFFFF, reg)
      return result
    except IOError, err:
      return self.errMsg()

  def readU16Rev(self, reg):
    "Reads an unsigned 16-bit value from the I2C device with rev byte order"
    try:
      lobyte = self.readU8(reg)
      hibyte = self.readU8(reg+1)
      result = (hibyte << 8) + lobyte
      if (self.debug):
        print "I2C: Device 0x%02X returned 0x%04X from reg 0x%02X" % (self.address, result & 0xFFFF, reg)
      return result
    except IOError, err:
      return self.errMsg()

  def readS16Rev(self, reg):
    "Reads a signed 16-bit value from the I2C device with rev byte order"
    try:
      lobyte = self.readS8(reg)
      hibyte = self.readU8(reg+1)
      result = (hibyte << 8) + lobyte
      if (self.debug):
        print "I2C: Device 0x%02X returned 0x%04X from reg 0x%02X" % (self.address, result & 0xFFFF, reg)
      return result
    except IOError, err:
      return self.errMsg()

if __name__ == '__main__':
  try:
    bus = Adafruit_I2C(address=0)
    print "Default I2C bus is accessible"
  except:
    print "Error accessing default I2C bus"

########NEW FILE########
__FILENAME__ = Adafruit_TCS34725
#!/usr/bin/python

import time
from Adafruit_I2C import Adafruit_I2C

# ===========================================================================
# TCS3472 Class
# ===========================================================================


class TCS34725:
    i2c = None

    __TCS34725_ADDRESS          = 0x29
    __TCS34725_ID               = 0x12 # 0x44 = TCS34721/TCS34725, 0x4D = TCS34723/TCS34727

    __TCS34725_COMMAND_BIT      = 0x80

    __TCS34725_ENABLE           = 0x00
    __TCS34725_ENABLE_AIEN      = 0x10 # RGBC Interrupt Enable
    __TCS34725_ENABLE_WEN       = 0x08 # Wait enable - Writing 1 activates the wait timer
    __TCS34725_ENABLE_AEN       = 0x02 # RGBC Enable - Writing 1 actives the ADC, 0 disables it
    __TCS34725_ENABLE_PON       = 0x01 # Power on - Writing 1 activates the internal oscillator, 0 disables it
    __TCS34725_ATIME            = 0x01 # Integration time
    __TCS34725_WTIME            = 0x03 # Wait time (if TCS34725_ENABLE_WEN is asserted)
    __TCS34725_WTIME_2_4MS      = 0xFF # WLONG0 = 2.4ms   WLONG1 = 0.029s
    __TCS34725_WTIME_204MS      = 0xAB # WLONG0 = 204ms   WLONG1 = 2.45s
    __TCS34725_WTIME_614MS      = 0x00 # WLONG0 = 614ms   WLONG1 = 7.4s
    __TCS34725_AILTL            = 0x04 # Clear channel lower interrupt threshold
    __TCS34725_AILTH            = 0x05
    __TCS34725_AIHTL            = 0x06 # Clear channel upper interrupt threshold
    __TCS34725_AIHTH            = 0x07
    __TCS34725_PERS             = 0x0C # Persistence register - basic SW filtering mechanism for interrupts
    __TCS34725_PERS_NONE        = 0b0000 # Every RGBC cycle generates an interrupt
    __TCS34725_PERS_1_CYCLE     = 0b0001 # 1 clean channel value outside threshold range generates an interrupt
    __TCS34725_PERS_2_CYCLE     = 0b0010 # 2 clean channel values outside threshold range generates an interrupt
    __TCS34725_PERS_3_CYCLE     = 0b0011 # 3 clean channel values outside threshold range generates an interrupt
    __TCS34725_PERS_5_CYCLE     = 0b0100 # 5 clean channel values outside threshold range generates an interrupt
    __TCS34725_PERS_10_CYCLE    = 0b0101 # 10 clean channel values outside threshold range generates an interrupt
    __TCS34725_PERS_15_CYCLE    = 0b0110 # 15 clean channel values outside threshold range generates an interrupt
    __TCS34725_PERS_20_CYCLE    = 0b0111 # 20 clean channel values outside threshold range generates an interrupt
    __TCS34725_PERS_25_CYCLE    = 0b1000 # 25 clean channel values outside threshold range generates an interrupt
    __TCS34725_PERS_30_CYCLE    = 0b1001 # 30 clean channel values outside threshold range generates an interrupt
    __TCS34725_PERS_35_CYCLE    = 0b1010 # 35 clean channel values outside threshold range generates an interrupt
    __TCS34725_PERS_40_CYCLE    = 0b1011 # 40 clean channel values outside threshold range generates an interrupt
    __TCS34725_PERS_45_CYCLE    = 0b1100 # 45 clean channel values outside threshold range generates an interrupt
    __TCS34725_PERS_50_CYCLE    = 0b1101 # 50 clean channel values outside threshold range generates an interrupt
    __TCS34725_PERS_55_CYCLE    = 0b1110 # 55 clean channel values outside threshold range generates an interrupt
    __TCS34725_PERS_60_CYCLE    = 0b1111 # 60 clean channel values outside threshold range generates an interrupt
    __TCS34725_CONFIG           = 0x0D
    __TCS34725_CONFIG_WLONG     = 0x02 # Choose between short and long (12x) wait times via TCS34725_WTIME
    __TCS34725_CONTROL          = 0x0F # Set the gain level for the sensor
    __TCS34725_ID               = 0x12 # 0x44 = TCS34721/TCS34725, 0x4D = TCS34723/TCS34727
    __TCS34725_STATUS           = 0x13
    __TCS34725_STATUS_AINT      = 0x10 # RGBC Clean channel interrupt
    __TCS34725_STATUS_AVALID    = 0x01 # Indicates that the RGBC channels have completed an integration cycle

    __TCS34725_CDATAL           = 0x14 # Clear channel data
    __TCS34725_CDATAH           = 0x15
    __TCS34725_RDATAL           = 0x16 # Red channel data
    __TCS34725_RDATAH           = 0x17
    __TCS34725_GDATAL           = 0x18 # Green channel data
    __TCS34725_GDATAH           = 0x19
    __TCS34725_BDATAL           = 0x1A # Blue channel data
    __TCS34725_BDATAH           = 0x1B

    __TCS34725_INTEGRATIONTIME_2_4MS  = 0xFF   #  2.4ms - 1 cycle    - Max Count: 1024
    __TCS34725_INTEGRATIONTIME_24MS   = 0xF6   # 24ms  - 10 cycles  - Max Count: 10240
    __TCS34725_INTEGRATIONTIME_50MS   = 0xEB   #  50ms  - 20 cycles  - Max Count: 20480
    __TCS34725_INTEGRATIONTIME_101MS  = 0xD5   #  101ms - 42 cycles  - Max Count: 43008
    __TCS34725_INTEGRATIONTIME_154MS  = 0xC0   #  154ms - 64 cycles  - Max Count: 65535
    __TCS34725_INTEGRATIONTIME_700MS  = 0x00   #  700ms - 256 cycles - Max Count: 65535

    __TCS34725_GAIN_1X                  = 0x00   #  No gain
    __TCS34725_GAIN_4X                  = 0x01   #  2x gain
    __TCS34725_GAIN_16X                 = 0x02   #  16x gain
    __TCS34725_GAIN_60X                 = 0x03   #  60x gain

    __integrationTimeDelay = {
        0xFF: 0.0024,  # 2.4ms - 1 cycle    - Max Count: 1024
        0xF6: 0.024,   # 24ms  - 10 cycles  - Max Count: 10240
        0xEB: 0.050,   # 50ms  - 20 cycles  - Max Count: 20480
        0xD5: 0.101,   # 101ms - 42 cycles  - Max Count: 43008
        0xC0: 0.154,   # 154ms - 64 cycles  - Max Count: 65535
        0x00: 0.700    # 700ms - 256 cycles - Max Count: 65535
    }

    # Private Methods
    def __readU8(self, reg):
        return self.i2c.readU8(self.__TCS34725_COMMAND_BIT | reg)

    def __readU16Rev(self, reg):
        return self.i2c.readU16Rev(self.__TCS34725_COMMAND_BIT | reg)

    def __write8(self, reg, value):
        self.i2c.write8(self.__TCS34725_COMMAND_BIT | reg, value & 0xff)

    # Constructor
    def __init__(self, address=0x29, debug=False, integrationTime=0xFF, gain=0x01):
        self.i2c = Adafruit_I2C(address)

        self.address = address
        self.debug = debug
        self.integrationTime = integrationTime
        self.initialize(integrationTime, gain)

    def initialize(self, integrationTime, gain):
        "Initializes I2C and configures the sensor (call this function before \
        doing anything else)"
        # Make sure we're actually connected
        result = self.__readU8(self.__TCS34725_ID)
        if (result != 0x44):
            return -1

        # Set default integration time and gain
        self.setIntegrationTime(integrationTime)
        self.setGain(gain)

        # Note: by default, the device is in power down mode on bootup
        self.enable()

    def enable(self):
        self.__write8(self.__TCS34725_ENABLE, self.__TCS34725_ENABLE_PON)
        time.sleep(0.01)
        self.__write8(self.__TCS34725_ENABLE, (self.__TCS34725_ENABLE_PON | self.__TCS34725_ENABLE_AEN))

    def disable(self):
        reg = 0
        reg = self.__readU8(self.__TCS34725_ENABLE)
        self.__write8(self.__TCS34725_ENABLE, (reg & ~(self.__TCS34725_ENABLE_PON | self.__TCS34725_ENABLE_AEN)))

    def setIntegrationTime(self, integrationTime):
        "Sets the integration time for the TC34725"
        self.integrationTime = integrationTime

        self.__write8(self.__TCS34725_ATIME, integrationTime)

    def getIntegrationTime(self):
        return self.__readU8(self.__TCS34725_ATIME)

    def setGain(self, gain):
        "Adjusts the gain on the TCS34725 (adjusts the sensitivity to light)"
        self.__write8(self.__TCS34725_CONTROL, gain)

    def getGain(self):
        return self.__readU8(self.__TCS34725_CONTROL)

    def getRawData(self):
        "Reads the raw red, green, blue and clear channel values"

        color = {}

        color["r"] = self.__readU16Rev(self.__TCS34725_RDATAL)
        color["b"] = self.__readU16Rev(self.__TCS34725_BDATAL)
        color["g"] = self.__readU16Rev(self.__TCS34725_GDATAL)
        color["c"] = self.__readU16Rev(self.__TCS34725_CDATAL)

        # Set a delay for the integration time
        delay = self.__integrationTimeDelay.get(self.integrationTime)
        time.sleep(delay)

        return color

    def setInterrupt(self, int):
        r = self.__readU8(self.__TCS34725_ENABLE)

        if (int):
            r |= self.__TCS34725_ENABLE_AIEN
        else:
            r &= ~self.__TCS34725_ENABLE_AIEN

        self.__write8(self.__TCS34725_ENABLE, r)

    def clearInterrupt(self):
        self.i2c.write8(0x66 & 0xff)

    def setIntLimits(self, low, high):
        self.i2c.write8(0x04, low & 0xFF)
        self.i2c.write8(0x05, low >> 8)
        self.i2c.write8(0x06, high & 0xFF)
        self.i2c.write8(0x07, high >> 8)

    #Static Utility Methods
    @staticmethod
    def calculateColorTemperature(rgb):
        "Converts the raw R/G/B values to color temperature in degrees Kelvin"

        if not isinstance(rgb, dict):
            raise ValueError('calculateColorTemperature expects dict as parameter')

        # 1. Map RGB values to their XYZ counterparts.
        # Based on 6500K fluorescent, 3000K fluorescent
        # and 60W incandescent values for a wide range.
        # Note: Y = Illuminance or lux
        X = (-0.14282 * rgb['r']) + (1.54924 * rgb['g']) + (-0.95641 * rgb['b'])
        Y = (-0.32466 * rgb['r']) + (1.57837 * rgb['g']) + (-0.73191 * rgb['b'])
        Z = (-0.68202 * rgb['r']) + (0.77073 * rgb['g']) + ( 0.56332 * rgb['b'])

        # 2. Calculate the chromaticity co-ordinates
        xc = (X) / (X + Y + Z)
        yc = (Y) / (X + Y + Z)

        # 3. Use McCamy's formula to determine the CCT
        n = (xc - 0.3320) / (0.1858 - yc)

        # Calculate the final CCT
        cct = (449.0 * (n ** 3.0)) + (3525.0 *(n ** 2.0)) + (6823.3 * n) + 5520.33

        return int(cct)

    @staticmethod
    def calculateLux(rgb):
        "Converts the raw R/G/B values to color temperature in degrees Kelvin"

        if not isinstance(rgb, dict):
            raise ValueError('calculateLux expects dict as parameter')

        illuminance = (-0.32466 * rgb['r']) + (1.57837 * rgb['g']) + (-0.73191 * rgb['b'])

        return int(illuminance)

########NEW FILE########
__FILENAME__ = Adafruit_TCS34725_Example
#!/usr/bin/python
from time import sleep
from Adafruit_TCS34725 import TCS34725

# ===========================================================================
# Example Code
# ===========================================================================

# Initialize the TCS34725 and use default integration time and gain
# tcs34725 = TCS34725(debug=True)
tcs = TCS34725(integrationTime=0xEB, gain=0x01)
tcs.setInterrupt(False)
sleep(1)

rgb = tcs.getRawData()
colorTemp = tcs.calculateColorTemperature(rgb)
lux = tcs.calculateLux(rgb)
print rgb
print "Color Temperature: %d K" % colorTemp
print "Luminosity: %d lux" % lux
tcs.setInterrupt(True)
sleep(1)
tcs.disable()

########NEW FILE########
__FILENAME__ = Adafruit_I2C
../Adafruit_I2C/Adafruit_I2C.py
########NEW FILE########
__FILENAME__ = Adafruit_VCNL4000
#!/usr/bin/python

import time
from Adafruit_I2C import Adafruit_I2C

# ===========================================================================
# VCNL4000 Class
# ===========================================================================

# Address of the sensor
VCNL4000_ADDRESS = 0x13

# Commands
VCNL4000_COMMAND = 0x80
VCNL4000_PRODUCTID = 0x81
VCNL4000_IRLED = 0x83
VCNL4000_AMBIENTPARAMETER = 0x84
VCNL4000_AMBIENTDATA = 0x85
VCNL4000_PROXIMITYDATA = 0x87
VCNL4000_SIGNALFREQ = 0x89
VCNL4000_PROXINITYADJUST = 0x8A

VCNL4000_3M125 = 0
VCNL4000_1M5625 = 1
VCNL4000_781K25 = 2
VCNL4000_390K625 = 3

VCNL4000_MEASUREAMBIENT = 0x10
VCNL4000_MEASUREPROXIMITY = 0x08
VCNL4000_AMBIENTREADY = 0x40
VCNL4000_PROXIMITYREADY = 0x20

class VCNL4000 :
  i2c = None

  # Constructor
  def __init__(self, address=0x13):
    self.i2c = Adafruit_I2C(address)

    self.address = address

    # Write proximity adjustement register
    self.i2c.write8(VCNL4000_PROXINITYADJUST, 0x81);

  # Read data from proximity sensor
  def read_proximity(self):
    self.i2c.write8(VCNL4000_COMMAND, VCNL4000_MEASUREPROXIMITY)
    while True:
      result = self.i2c.readU8(VCNL4000_COMMAND)
      if (result and VCNL4000_PROXIMITYREADY):
        return self.i2c.readU16(VCNL4000_PROXIMITYDATA)
      time.sleep(0.001)



########NEW FILE########
__FILENAME__ = Adafruit_VCNL4000_example
#!/usr/bin/python

from Adafruit_VCNL4000 import VCNL4000
import time

# ===========================================================================
# Example Code
# ===========================================================================

# Initialise the VNCL4000 sensor
vcnl = VCNL4000(0x13)

# Print proximity sensor data every 100 ms
while True:
	
	print "Data from proximity sensor", vcnl.read_proximity()
	time.sleep(0.1)

########NEW FILE########
