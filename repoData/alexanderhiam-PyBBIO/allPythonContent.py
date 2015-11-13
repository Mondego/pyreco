__FILENAME__ = bbio
"""
 PyBBIO - bbio.py
 Author: Alexander Hiam - ahiam@marlboro.edu - www.alexanderhiam.com
 Website: https://github.com/alexanderhiam/PyBBIO

 A Python library for hardware IO support on the TI Beaglebone.
 Currently only supporting basic digital and analog IO, but more 
 peripheral support is on the way, so keep checking the Github page
 for updates.

 Copyright (c) 2012-2014 - Alexander Hiam <hiamalexander@gmail.com>

 Licensed under the Apache License, Version 2.0 (the "License");
 you may not use this file except in compliance with the License.
 You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

 Unless required by applicable law or agreed to in writing, software
 distributed under the License is distributed on an "AS IS" BASIS,
 WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 See the License for the specific language governing permissions and
 limitations under the License.
"""

import sys

from platform import *
from util import *
from config import LIBRARIES_PATH

sys.path.append(LIBRARIES_PATH)

def bbio_init():
  """ Pre-run initialization, i.e. starting module clocks, etc. """
  util_init()
  platform_init()

def bbio_cleanup():
  """ Post-run cleanup, i.e. stopping module clocks, etc. """
  # Run user cleanup routines:
  for cleanup in ADDITIONAL_CLEANUP:
    try:
      cleanup()
    except Exception as e:
      # Something went wrong with one of the cleanup routines, but we
      # want to keep going; just print the error and continue
      print "*Exception raised trying to call cleanup routine '%s':\n  %s" %\
            (cleanup, e)
  platform_cleanup()

# The following code detects if Python is running interactively,
# and if so initializes PyBBIO on import and registers PyBBIO's
# cleanup to be called at exit, otherwise it defines the run() and
# stop() methods for the file based control flow:
import __main__
if not hasattr(__main__, '__file__'):
  # We're in the interpreter, see: 
  #  http://stackoverflow.com/questions/2356399/tell-if-python-is-in-interactive-mode
  bbio_init()
  print "PyBBIO initialized"
  import atexit
  def interactive_cleanup():
    bbio_cleanup()
    print "Finished PyBBIO cleanup"
  atexit.register(interactive_cleanup)

else:
  # Imported in a Python file, define run() and stop():
  def run(setup, loop):
    """ The main loop; must be passed a setup and a loop function.
        First the setup function will be called once, then the loop
        function wil be called continuously until a stop signal is 
        raised, e.g. CTRL-C or a call to the stop() function from 
        within the loop. """
    try:
      bbio_init()
      setup()
      while (True):
        loop()
    except KeyboardInterrupt:
      # Manual exit signal, clean up and exit happy
      bbio_cleanup()
    except Exception, e:
      # Something may have gone wrong, clean up and re-raise exception
      bbio_cleanup()
      raise 
      
  def stop():
    """ Preffered way for a program to stop itself. """
    raise KeyboardInterrupt # Expected happy stop condition in run()

########NEW FILE########
__FILENAME__ = config
# Config file for PyBBIO

LIBRARIES_PATH = """Do not edit!"""
# This will be replaced in installed config file with
# the correct path to the libraries folder; Do not edit
# this line!


########NEW FILE########
__FILENAME__ = adc
# adc.py 
# Part of PyBBIO
# github.com/alexanderhiam/PyBBIO
# Apache 2.0 license
# 
# Beaglebone ADC driver for kernels < 3.8.
#
# Uses direct memory access to configure and control the ADC
# sampling. 

import memory
from config import *


def analog_init():
  """ Initializes the on-board 8ch 12bit ADC. """
  # Enable ADC module clock, though should already be enabled on
  # newer Angstrom images:
  memory.setReg(CM_WKUP_ADC_TSC_CLKCTRL, MODULEMODE_ENABLE)
  # Wait for enable complete:
  while (memory.getReg(CM_WKUP_ADC_TSC_CLKCTRL) & IDLEST_MASK): delay(1)

  # Software reset:
  memory.setReg(ADC_SYSCONFIG, ADC_SOFTRESET)
  while(memory.getReg(ADC_SYSCONFIG) & ADC_SOFTRESET): pass

  # Make sure STEPCONFIG write protect is off:
  memory.setReg(ADC_CTRL, ADC_STEPCONFIG_WRITE_PROTECT_OFF)

  # Set STEPCONFIG1-STEPCONFIG8 to correspond to ADC inputs 0-7:
  for i in xrange(8):
    config = SEL_INP('AIN%i' % i) | ADC_AVG2
    memory.setReg(eval('ADCSTEPCONFIG%i' % (i+1)), config)
    memory.setReg(eval('ADCSTEPDELAY%i' % (i+1)), SAMPLE_DELAY(15))
  # Now we can enable ADC subsystem, leaving write protect off:
  memory.orReg(ADC_CTRL, TSC_ADC_SS_ENABLE)

def analog_cleanup():
  # Software reset:
  memory.setReg(ADC_SYSCONFIG, ADC_SOFTRESET)
  while(memory.getReg(ADC_SYSCONFIG) & ADC_SOFTRESET): pass

  # When I started writing PyBBIO on an older Angstrom image, the ADC
  # was not enabled on boot, so I had these lines to shut it back off:
  # Disable ADC subsystem:
  #_clearReg(ADC_CTRL, TSC_ADC_SS_ENABLE)
  # Disable ADC module clock:
  #_clearReg(CM_WKUP_ADC_TSC_CLKCTRL, MODULEMODE_ENABLE)
  # Newer images enable the ADC module at boot, so we just leave it 
  # running.


def analogRead(analog_pin):
  """ Returns analog value read on given analog input pin. """
  assert (analog_pin in ADC), "*Invalid analog pin: '%s'" % analog_pin

  if (memory.getReg(CM_WKUP_ADC_TSC_CLKCTRL) & IDLEST_MASK):
    # The ADC module clock has been shut off, e.g. by a different 
    # PyBBIO script stopping while this one was running, turn back on:
    analog_init() 

  # Enable sequncer step that's set for given input:
  memory.setReg(ADC_STEPENABLE, ADC_ENABLE(analog_pin))
  # Sequencer starts automatically after enabling step, wait for complete:
  while(memory.getReg(ADC_STEPENABLE) & ADC_ENABLE(analog_pin)): pass
  # Return 12-bit value from the ADC FIFO register:
  return memory.getReg(ADC_FIFO0DATA) & ADC_FIFO_MASK

def inVolts(adc_value, bits=12, vRef=1.8):
  """ Converts and returns the given ADC value to a voltage according
      to the given number of bits and reference voltage. """
  return adc_value*(vRef/2**bits)


########NEW FILE########
__FILENAME__ = config
# PyBBIO config file for BeagleBones with pre-3.8 kernels. 

#---------------------------------------------------#
# Changes to this file may lead to permanent damage #
# to you Beaglebone, edit with care.                #
#---------------------------------------------------#

# Load the common beaglebone configuration:
from config_common import *


##############################
##--- Start PRCM config: ---##
## Power Management and Clock Module

#--- Module clock control: ---
CM_PER = 0x44e00000-MMAP_OFFSET
CM_WKUP = 0x44e00400-MMAP_OFFSET

CM_PER_EPWMSS0_CLKCTRL = 0xd4+CM_PER
CM_PER_EPWMSS1_CLKCTRL = 0xcc+CM_PER
CM_PER_EPWMSS2_CLKCTRL = 0xd8+CM_PER

CM_WKUP_ADC_TSC_CLKCTRL = 0xbc+CM_WKUP

MODULEMODE_ENABLE = 0x02
IDLEST_MASK = 0x03<<16
# To enable module clock:
#  _setReg(CM_WKUP_module_CLKCTRL, MODULEMODE_ENABLE)
#  while (_getReg(CM_WKUP_module_CLKCTRL) & IDLEST_MASK): pass
# To disable module clock:
#  _andReg(CM_WKUP_module_CLKCTRL, ~MODULEMODE_ENABLE)
#-----------------------------

##--- End PRCM config ------##
##############################


########################################
##--- Start control module config: ---##

PINMUX_PATH = '/sys/kernel/debug/omap_mux/'

CONF_UART_TX     = CONF_PULL_DISABLE
CONF_UART_RX     = CONF_PULLUP | CONF_RX_ACTIVE

##--- End control module config ------##
########################################


##############################
##--- Start ADC config: ----##

ADC_TSC = 0x44e0d000-MMAP_OFFSET

## Registers:

ADC_SYSCONFIG = ADC_TSC+0x10

ADC_SOFTRESET = 0x01


#--- ADC_CTRL ---
ADC_CTRL = ADC_TSC+0x40

ADC_STEPCONFIG_WRITE_PROTECT_OFF = 0x01<<2
# Write protect default on, must first turn off to change stepconfig:
#  _setReg(ADC_CTRL, ADC_STEPCONFIG_WRITE_PROTECT_OFF)
# To set write protect on:
#  _clearReg(ADC_CTRL, ADC_STEPCONFIG_WRITE_PROTECT_OFF)
 
TSC_ADC_SS_ENABLE = 0x01 
# To enable:
# _setReg(ADC_CTRL, TSC_ADC_SS_ENABLE)
#  This will turn STEPCONFIG write protect back on 
# To keep write protect off:
# _orReg(ADC_CTRL, TSC_ADC_SS_ENABLE)
#----------------

ADC_CLKDIV = ADC_TSC+0x4c  # Write desired value-1

#--- ADC_STEPENABLE ---
ADC_STEPENABLE = ADC_TSC+0x54

ADC_ENABLE = lambda AINx: 0x01<<(ADC[AINx]+1)
#----------------------

ADC_IDLECONFIG = ADC_TSC+0x58

#--- ADC STEPCONFIG ---
ADCSTEPCONFIG1 = ADC_TSC+0x64
ADCSTEPDELAY1  = ADC_TSC+0x68
ADCSTEPCONFIG2 = ADC_TSC+0x6c
ADCSTEPDELAY2  = ADC_TSC+0x70
ADCSTEPCONFIG3 = ADC_TSC+0x74
ADCSTEPDELAY3  = ADC_TSC+0x78
ADCSTEPCONFIG4 = ADC_TSC+0x7c
ADCSTEPDELAY4  = ADC_TSC+0x80
ADCSTEPCONFIG5 = ADC_TSC+0x84
ADCSTEPDELAY5  = ADC_TSC+0x88
ADCSTEPCONFIG6 = ADC_TSC+0x8c
ADCSTEPDELAY6  = ADC_TSC+0x90
ADCSTEPCONFIG7 = ADC_TSC+0x94
ADCSTEPDELAY7  = ADC_TSC+0x98
ADCSTEPCONFIG8 = ADC_TSC+0x9c
ADCSTEPDELAY8  = ADC_TSC+0xa0
# Only need the first 8 steps - 1 for each AIN pin


ADC_RESET = 0x00 # Default value of STEPCONFIG

ADC_AVG2  = 0x01<<2
ADC_AVG4  = 0x02<<2
ADC_AVG8  = 0x03<<2
ADC_AVG16 = 0x04<<2

#SEL_INP = lambda AINx: (ADC[AINx]+1)<<19
# Set input with _orReg(ADCSTEPCONFIGx, SEL_INP(AINx))
# ADC[AINx]+1 because positive AMUX input 0 is VREFN 
#  (see user manual section 12.3.7)
SEL_INP = lambda AINx: (ADC[AINx])<<19

SAMPLE_DELAY = lambda cycles: (cycles&0xff)<<24
# SAMPLE_DELAY is the number of cycles to sample for
# Set delay with _orReg(ADCSTEPDELAYx, SAMPLE_DELAY(cycles))

#----------------------
 
#--- ADC FIFO ---
ADC_FIFO0DATA = ADC_TSC+0x100

ADC_FIFO_MASK = 0xfff
# ADC result = _getReg(ADC_FIFO0DATA)&ADC_FIFO_MASK
#----------------

## ADC pins:

ADC = {
  'AIN0' : 0x00,
  'AIN1' : 0x01,
  'AIN2' : 0x02,
  'AIN3' : 0x03,
  'AIN4' : 0x04,
  'AIN5' : 0x05,
  'AIN6' : 0x06,
  'AIN7' : 0x07,
  'VSYS' : 0x07
}
# And some constants so the user doesn't need to use strings:
AIN0 = A0 = 'AIN0'
AIN1 = A1 = 'AIN1'
AIN2 = A2 = 'AIN2'
AIN3 = A3 = 'AIN3'
AIN4 = A4 = 'AIN4'
AIN5 = A5 = 'AIN5'
AIN6 = A6 = 'AIN6'
AIN7 = A7 = VSYS = 'AIN7'

##--- End ADC config -------##
##############################


##############################
##--- Start UART config: ---##

# UART ports must be in form: 
#    [port, tx_pinmux_filename, tx_pinmux_mode, 
#           rx_pinmux_filename, rx_pinmux_mode]

UART = {
  'UART1' : ['/dev/ttyO1', 'uart1_txd', 0,  'uart1_rxd', 0],
  'UART2' : ['/dev/ttyO2',   'spi0_d0', 1,  'spi0_sclk', 1],
  'UART4' : ['/dev/ttyO4',  'gpmc_wpn', 6, 'gpmc_wait0', 6],
  'UART5' : ['/dev/ttyO5', 'lcd_data8', 4,  'lcd_data9', 4]
}


##--- End UART config ------##
##############################


##############################
##--- Start PWM config: ----##

PWM_CTRL_DIR = "/sys/class/pwm/"

# EHRPWM pinmux config dict in form:
#  [mux_file, mux_mode, pwm_ctrl_dir]

PWM_PINS = {
  'PWM1A' : [ 'gpmc_a2', 0x06, 'ehrpwm.1:0/'],
  'PWM1B' : [ 'gpmc_a3', 0x06, 'ehrpwm.1:1/']
}
PWM1A = 'PWM1A'
PWM1B = 'PWM1B'


import os
if (os.path.exists(PWM_CTRL_DIR+'ehrpwm.2:0/')):
  PWM_PINS['PWM2A'] = ['gpmc_ad8', 0x04, 'ehrpwm.2:0/']
  PWM_PINS['PWM2B'] = ['gpmc_ad9', 0x04, 'ehrpwm.2:1/']
  PWM2A = 'PWM2A'
  PWM2B = 'PWM2B'


PWM_FILES = dict(\
  (i, [open(PWM_CTRL_DIR+PWM_PINS[i][2]+'request', 'r+'),
       open(PWM_CTRL_DIR+PWM_PINS[i][2]+'run', 'r+'),
       open(PWM_CTRL_DIR+PWM_PINS[i][2]+'duty_ns', 'r+'),
       open(PWM_CTRL_DIR+PWM_PINS[i][2]+'period_freq', 'r+') ])\
  for i in PWM_PINS.keys())


# Indexes in PWM_FILES lists:
PWM_REQUEST = 0
PWM_ENABLE  = 1
PWM_DUTY    = 2
PWM_FREQ    = 3

##--- End PWM config: ------##
##############################

##############################
##--- Start I2C config: ---##

# I2C bus address must be in form: 
#    [dev-entry, I2C-overlay-name]

I2C = {
  'i2c1' : ['/dev/i2c-2', 'BB-I2C1'],
  'i2c2' : ['/dev/i2c-1', 'BB-I2C2'],
}

##--- End I2C config ------##
##############################


########NEW FILE########
__FILENAME__ = pinmux
# 3.2/pinmux.py 
# Part of PyBBIO
# github.com/alexanderhiam/PyBBIO
# Apache 2.0 license
# 
# Beaglebone pinmux driver
# For Beaglebones with 3.2 kernel

from config import *
from sysfs import kernelFileIO

def pinMux(gpio_pin, mode, preserve_mode_on_exit=False):
  """ Uses kernel omap_mux files to set pin modes. """
  # There's no simple way to write the control module registers from a 
  # user-level process because it lacks the proper privileges, but it's 
  # easy enough to just use the built-in file-based system and let the 
  # kernel do the work. 
  fn = GPIO[gpio_pin][0]
  try:
    with open(PINMUX_PATH+fn, 'wb') as f:
      f.write(hex(mode)[2:]) # Write hex string (stripping off '0x')
  except IOError:
    print "*omap_mux file not found: '%s'" % (PINMUX_PATH+fn)

def export(gpio_pin):
  """ Reserves a pin for userspace use with sysfs /sys/class/gpio interface. 
      Returns True if pin was exported, False if it was already under 
      userspace control. """
  if ("USR" in gpio_pin):
    # The user LEDs are already under userspace control
    return False
  gpio_num = GPIO[gpio_pin][2]
  gpio_file = '%s/gpio%i' % (GPIO_FILE_BASE, gpio_num)
  if (os.path.exists(gpio_file)): 
    # Pin already under userspace control
    return False
  with open(EXPORT_FILE, 'wb') as f:
    f.write(str(gpio_num))
  return True

def unexport(gpio_pin):
  """ Returns a pin to the kernel with sysfs /sys/class/gpio interface.
      Returns True if pin was unexported, False if it was already under 
      kernel control. """
  if ("USR" in gpio_pin):
    # The user LEDs are always under userspace control
    return False
  gpio_num = GPIO[gpio_pin][2]
  gpio_file = '%s/gpio%i' % (GPIO_FILE_BASE, gpio_num)
  if (not os.path.exists(gpio_file)): 
    # Pin not under userspace control
    return False
  with open(UNEXPORT_FILE, 'wb') as f:
    f.write(str(gpio_num))
  return True

########NEW FILE########
__FILENAME__ = pwm
# pwm.py 
# Part of PyBBIO
# github.com/alexanderhiam/PyBBIO
# Apache 2.0 license
# 
# Beaglebone PWM driver for kernel < 3.8


import memory, pinmux
from bbio.util import delay
from config import *


def pwm_init():
  # Enable EHRPWM module clocks:
  memory.setReg(CM_PER_EPWMSS1_CLKCTRL, MODULEMODE_ENABLE)
  # Wait for enable complete:
  while (memory.getReg(CM_PER_EPWMSS1_CLKCTRL) & IDLEST_MASK): delay(1)
  memory.setReg(CM_PER_EPWMSS2_CLKCTRL, MODULEMODE_ENABLE)
  # Wait for enable complete:
  while (memory.getReg(CM_PER_EPWMSS2_CLKCTRL) & IDLEST_MASK): delay(1)

def pwm_cleanup():
  # Disable all PWM outputs:
  for i in PWM_PINS.keys():
    pwmDisable(i)
  # Could disable EHRPWM module clocks here to save some power when
  # PyBBIO isn't running, but I'm not really worried about it for the 
  # time being.

def analogWrite(pwm_pin, value, resolution=RES_8BIT):
  """ Sets the duty cycle of the given PWM output using the
      given resolution. """
  # Make sure the pin is configured:
  pwmEnable(pwm_pin)
  try:
    assert resolution > 0, "*PWM resolution must be greater than 0"
    if (value < 0): value = 0
    if (value >= resolution): value = resolution-1
    freq = int(pinmux.kernelFileIO(PWM_FILES[pwm_pin][PWM_FREQ]))
    period_ns = (1e9/freq)
    # Todo: round values properly!: 
    duty_ns = int(value * (period_ns/resolution))
    pinmux.kernelFileIO(PWM_FILES[pwm_pin][PWM_DUTY], str(duty_ns))
    # Enable output:
    if (pinmux.kernelFileIO(PWM_FILES[pwm_pin][PWM_ENABLE]) == '0\n'):
      pinmux.kernelFileIO(PWM_FILES[pwm_pin][PWM_ENABLE], '1') 
  except IOError:
    print "*PWM pin '%s' reserved by another process!" % pwm_pin

# For those who don't like calling a digital signal analog:
pwmWrite = analogWrite

def pwmFrequency(pwm_pin, freq_hz):
  """ Sets the frequncy in Hertz of the given PWM output's module. """
  assert (pwm_pin in PWM_PINS), "*Invalid PWM pin: '%s'" % pwm_pin
  assert freq_hz > 0, "*PWM frequency must be greater than 0"
  # Make sure the pin is configured:
  pwmEnable(pwm_pin)
  # calculate the duty cycle in nanoseconds for the new period:
  old_duty_ns = int(kernelFileIO(PWM_FILES[pwm_pin][PWM_DUTY]))
  old_period_ns = 1e9/int(kernelFileIO(PWM_FILES[pwm_pin][PWM_FREQ]))
  duty_percent = old_duty_ns / old_period_ns
  new_period_ns = 1e9/freq_hz
  # Todo: round values properly!:
  new_duty_ns = int(duty_percent * new_period_ns)

  try: 
    # Duty cyle must be set to 0 before changing frequency:
    pinmux.kernelFileIO(PWM_FILES[pwm_pin][PWM_DUTY], '0')
    # Set new frequency:
    pinmux.kernelFileIO(PWM_FILES[pwm_pin][PWM_FREQ], str(freq_hz))
    # Set the duty cycle:
    pinmux.kernelFileIO(PWM_FILES[pwm_pin][PWM_DUTY], str(new_duty_ns))
  except IOError:
    print "*PWM pin '%s' reserved by another process!" % pwm_pin
  
def pwmEnable(pwm_pin):
  """ Ensures given PWM output is reserved for userspace use and 
      sets proper pinmux. Sets frequency to default value if output
      not already reserved. """
  assert (pwm_pin in PWM_PINS), "*Invalid PWM pin: '%s'" % pwm_pin
  # Set pinmux mode:
  pinmux.pinMux(PWM_PINS[pwm_pin][0], PWM_PINS[pwm_pin][1])
  if ('sysfs' not in pinmux.kernelFileIO(PWM_FILES[pwm_pin][PWM_REQUEST])):
    # Reserve use of output:
    pinmux.kernelFileIO(PWM_FILES[pwm_pin][PWM_REQUEST], '1')
    delay(1) # Give it some time to take effect
    # Make sure output is disabled, so it won't start outputing a 
    # signal until analogWrite() is called: 
    if (pinmux.kernelFileIO(PWM_FILES[pwm_pin][PWM_ENABLE]) == '1\n'):
      pinmux.kernelFileIO(PWM_FILES[pwm_pin][PWM_ENABLE], '0')
    # Duty cyle must be set to 0 before changing frequency:
    pinmux.kernelFileIO(PWM_FILES[pwm_pin][PWM_DUTY], '0')
    # Set frequency to default:
    pinmux.kernelFileIO(PWM_FILES[pwm_pin][PWM_FREQ], str(PWM_DEFAULT_FREQ))

def pwmDisable(pwm_pin):
  """ Disables PWM output on given pin. """
  assert (pwm_pin in PWM_PINS), "*Invalid PWM pin: '%s'" % pwm_pin
  # Disable PWM output:
  if (pinmux.kernelFileIO(PWM_FILES[pwm_pin][PWM_ENABLE]) == '1\n'):
    pinmux.kernelFileIO(PWM_FILES[pwm_pin][PWM_ENABLE], '0')
  # Relinquish userspace control:
  if ('sysfs' in pinmux.kernelFileIO(PWM_FILES[pwm_pin][PWM_REQUEST])):
    pinmux.kernelFileIO(PWM_FILES[pwm_pin][PWM_REQUEST], '0')

########NEW FILE########
__FILENAME__ = uart
# 3.2/uart.py 
# Part of PyBBIO
# github.com/alexanderhiam/PyBBIO
# Apache 2.0 license
# 
# Beaglebone pinmux driver
# For Beaglebones with 3.2 kernel

from config import UART, CONF_UART_TX, CONF_UART_RX
import pinmux


def uartInit(uart):
  """ Muxes given serial port's header pins for use. Returns True
      if successful, False otherwise. """
  tx_pinmux_filename = UART[self.config][1]
  tx_pinmux_mode     = UART[self.config][2] | CONF_UART_TX
  pinmux.pinMux(tx_pinmux_filename, tx_pinmux_mode)

  rx_pinmux_filename = UART[self.config][3]
  rx_pinmux_mode     = UART[self.config][4] | CONF_UART_RX
  pinmux.pinMux(rx_pinmux_filename, rx_pinmux_mode)    
  # Not catching errors for now, not sure what could go wrong here...
  return True
########NEW FILE########
__FILENAME__ = adc
# adc.py 
# Part of PyBBIO
# github.com/alexanderhiam/PyBBIO
# Apache 2.0 license
# 
# Beaglebone ADC driver for kernels >= 3.8.
#
# Just a wrapper for the sysfs ADC driver for the time being. 

import os, glob
import cape_manager
from config import *

def analog_init():
  """ Initializes the on-board 8ch 12bit ADC. """
  cape_manager.load(ADC_ENABLE_DTS_OVERLAY, auto_unload=False)
  # Don't unload the overlay on exit for now because it can 
  # cause kernel panic.

def analog_cleanup():
  pass

def analogRead(adc_pin):
  """ Returns voltage read on given analog input pin in millivolts. """
  if adc_pin in ADC: adc_pin = ADC[adc_pin]
  adc_file = adc_pin[0]
  if not os.path.exists(adc_file):
    # Overlay not loaded yet
    overlay = adc_pin[1]
    cape_manager.load(overlay, auto_unload=False)
  # Occasionally the kernel will be writing to the file when you try 
  # to read it, to avoid IOError try up to 5 times:
  for i in range(5):
    try:
      with open(glob.glob(adc_file)[0], 'rb') as f: 
        mv = f.read()
      return int(mv)
    except IOError:
      continue
  raise Exception('*Could not open AIN file: %s' % adc_file)


def inVolts(mv):
  """ Converts millivolts to volts... you know, to keep the API 
      consistent. """
  return mv/1000.0


########NEW FILE########
__FILENAME__ = cape_manager
# cape_manager.py 
# Part of PyBBIO
# github.com/alexanderhiam/PyBBIO
# Apache 2.0 license
# 
# Beaglebone Cape Manager driver
# For Beaglebone's with 3.8 kernel or greater

from config import SLOTS_FILE
from bbio.util import addToCleanup

def load(overlay, auto_unload=True):
  """ Attempt to load an overlay with the given name. If auto_unload=True it
      will be auto-unloaded at program exit (the current cape manager crashes
      when trying to unload certain overlay fragments). """
  with open(SLOTS_FILE, 'rb') as f:
    capes = f.read()
  if overlay in capes:
    # already loaded (this should do a better job checking)
    return
  with open(SLOTS_FILE, 'wb') as f:
    f.write(overlay)
  if auto_unload:
    addToCleanup(lambda: unload(overlay))
    
def unload(overlay):
  """ Unload the first overlay matching the given name if present. Returns 
      True if successful, False if no mathcing overlay loaded. """ 
  with open(SLOTS_FILE, 'rb') as f:
    slots = f.readlines()
  for slot in slots:
    if overlay in slot:
      load('-%i' % int(slot.split(':')[0]))
      return True
  return False 

########NEW FILE########
__FILENAME__ = config
# PyBBIO config file for BeagleBones with 3.8 kernels. 

#---------------------------------------------------#
# Changes to this file may lead to permanent damage #
# to you Beaglebone, edit with care.                #
#---------------------------------------------------#

# Load the common beaglebone configuration:
from config_common import *
import glob

########################################
##--- Start device tree: ---##

SLOTS_FILE = glob.glob('/sys/devices/bone_capemgr.*/slots')[0]
OCP_PATH = glob.glob('/sys/devices/ocp.*')[0]

##--- End device tree config ------##
########################################

##############################
##--- Start GPIO config: ---##

GET_USR_LED_DIRECTORY = lambda USRX : \
  "/sys/class/leds/beaglebone:green:%s" % USRX.lower()

##--- End GPIO config ------##
##############################



#############################
##--- Start ADC config: ---##

ADC_ENABLE_DTS_OVERLAY = 'PyBBIO-ADC'

# ADC pins should be in the form:
#          ['path/to/adc-file', 'Channel-enable-overlay', 'header_pin'] 

ADC = {
  'AIN0' : ['%s/PyBBIO-AIN0.*/AIN0' % OCP_PATH, 'PyBBIO-AIN0', 'P9.39'],
  'AIN1' : ['%s/PyBBIO-AIN1.*/AIN1' % OCP_PATH, 'PyBBIO-AIN1', 'P9.40'],
  'AIN2' : ['%s/PyBBIO-AIN2.*/AIN2' % OCP_PATH, 'PyBBIO-AIN2', 'P9.37'],
  'AIN3' : ['%s/PyBBIO-AIN3.*/AIN3' % OCP_PATH, 'PyBBIO-AIN3', 'P9.38'],
  'AIN4' : ['%s/PyBBIO-AIN4.*/AIN4' % OCP_PATH, 'PyBBIO-AIN4', 'P9.33'],
  'AIN5' : ['%s/PyBBIO-AIN5.*/AIN5' % OCP_PATH, 'PyBBIO-AIN5', 'P9.36'],
  'AIN6' : ['%s/PyBBIO-AIN6.*/AIN6' % OCP_PATH, 'PyBBIO-AIN6', 'P9.35'],
  'AIN7' : ['%s/PyBBIO-AIN7.*/AIN7' % OCP_PATH, 'PyBBIO-AIN7', 'vsys'],
}

# And some constants so the user doesn't need to use strings:

AIN0 = A0 = 'AIN0'
AIN1 = A1 = 'AIN1'
AIN2 = A2 = 'AIN2'
AIN3 = A3 = 'AIN3'
AIN4 = A4 = 'AIN4'
AIN5 = A5 = 'AIN5'
AIN6 = A6 = 'AIN6'
AIN7 = A7 = VSYS = 'AIN7'


##--- End ADC config ------##
#############################



#############################
##--- Start PWM config: ---##

# PWM config dict in form:
#  ['overlay_file', 'path/to/ocp_helper_dir', ['required', 'overlays']]

PWM_PINS = {
  'PWM1A' : ['bone_pwm_P9_14', '%s/pwm_test_P9_14.*' % OCP_PATH, 
             ['PyBBIO-epwmss1', 'PyBBIO-ehrpwm1']],
  'PWM1B' : ['bone_pwm_P9_16', '%s/pwm_test_P9_16.*' % OCP_PATH, 
             ['PyBBIO-epwmss1', 'PyBBIO-ehrpwm1']],

  'PWM2A' : ['bone_pwm_P8_19', '%s/pwm_test_P8_19.*' % OCP_PATH, 
             ['PyBBIO-epwmss2', 'PyBBIO-ehrpwm2']],
  'PWM2B' : ['bone_pwm_P8_13', '%s/pwm_test_P8_13.*' % OCP_PATH, 
             ['PyBBIO-epwmss2', 'PyBBIO-ehrpwm2']],

  'ECAP0' : ['bone_pwm_P9_42', '%s/pwm_test_P9_42.*' % OCP_PATH, 
             ['PyBBIO-epwmss0', 'PyBBIO-ecap0']],
  'ECAP1' : ['bone_pwm_P9_28', '%s/pwm_test_P9_28.*' % OCP_PATH, 
             ['PyBBIO-epwmss1', 'PyBBIO-ecap1']],

}
# Using the built-in pin overlays for now, I see no need for custom ones 

PWM1A = 'PWM1A'
PWM1B = 'PWM1B'
PWM2A = 'PWM2A'
PWM2B = 'PWM2B'
ECAP0 = 'ECAP0'
ECAP1 = 'ECAP1'

# ocp helper filenames:
PWM_RUN      = 'run'
PWM_DUTY     = 'duty'
PWM_PERIOD   = 'period'
PWM_POLARITY = 'polarity'

PWM_DEFAULT_PERIOD = int(1e9/PWM_DEFAULT_FREQ)

##--- End PWM config ------##
#############################


##############################
##--- Start UART config: ---##

# UART ports must be in form: 
#    [port, uart-overlay-name]

UART = {
  'UART1' : ['/dev/ttyO1', 'BB-UART1'],
  'UART2' : ['/dev/ttyO2', 'BB-UART2'],
  'UART4' : ['/dev/ttyO4', 'BB-UART4'],
  'UART5' : ['/dev/ttyO5', 'BB-UART5']
}

##--- End UART config ------##
##############################


##############################
##--- Start I2C config: ---##

# I2C bus address must be in form: 
#    [dev-entry, I2C-overlay-name]
# rather confusing bus address and dev-entry don't exactly match
# i2c0, i2c2 buses are activated by default i.e. /dev/12c-0 and /dev/i2c-1
# more info - http://datko.net/2013/11/03/bbb_i2c/
# NOTE : 1st I2C bus - i2c0 is used to read eeproms of capes - Don't use that for other purposes


I2C = {
  'i2c0' : ['/dev/i2c-0', 'BB-I2C0'],
  'i2c1' : ['/dev/i2c-2', 'BB-I2C1'],
  'i2c2' : ['/dev/i2c-1', 'BB-I2C2'],
}

##--- End I2C config ------##
##############################


########NEW FILE########
__FILENAME__ = pinmux
# 3.8/pinmux.py 
# Part of PyBBIO
# github.com/alexanderhiam/PyBBIO
# Apache 2.0 license
# 
# Beaglebone pinmux driver
# For Beaglebones with 3.8 kernel

from config import *
import glob, os, cape_manager, bbio

def pinMux(gpio_pin, mode, preserve_mode_on_exit=False):
  """ Uses custom device tree overlays to set pin modes.
      If preserve_mode_on_exit=True the overlay will remain loaded
      when the program exits, otherwise it will be unloaded before
      exiting.
      *This should generally not be called directly from user code. """
  gpio_pin = gpio_pin.lower()

  if not gpio_pin:
    print "*unknown pinmux pin: %s" % gpio_pin
    return
  mux_file_glob = glob.glob('%s/*%s*/state' % (OCP_PATH, gpio_pin))
  if len(mux_file_glob) == 0:
    try:
      cape_manager.load('PyBBIO-%s' % gpio_pin, not preserve_mode_on_exit)
      bbio.delay(250) # Give driver time to load
    except IOError:
      print "*Could not load %s overlay, resource busy" % gpio_pin
      return
    
  mux_file_glob = glob.glob('%s/*%s*/state' % (OCP_PATH, gpio_pin))
  if len(mux_file_glob) == 0:
    print "*Could not load overlay for pin: %s" % gpio_pin
    return 
  mux_file = mux_file_glob[0]
  # Convert mode to ocp mux name:
  mode = 'mode_%s' % format(mode, '#010b') 
  # Possible modes:
  #  mode_0b00100111  # rx active | pull down
  #  mode_0b00110111  # rx active | pull up
  #  mode_0b00101111  # rx active | no pull
  #  mode_0b00000111  # pull down
  #  mode_0b00010111  # pull up
  #  mode_0b00001111  # no pull
  # See /lib/firmware/PyBBIO-src/*.dts for more info  
  with open(mux_file, 'wb') as f:
    f.write(mode)

def export(gpio_pin):
  """ Reserves a pin for userspace use with sysfs /sys/class/gpio interface. 
      Returns True if pin was exported, False if it was already under 
      userspace control. """
  if ("USR" in gpio_pin):
    # The user LEDs are already under userspace control
    return True
  gpio_num = GPIO[gpio_pin][2]
  gpio_file = '%s/gpio%i' % (GPIO_FILE_BASE, gpio_num)
  if (os.path.exists(gpio_file)): 
    # Pin already under userspace control
    return True
  with open(EXPORT_FILE, 'wb') as f:
    f.write(str(gpio_num))
  return True

def unexport(gpio_pin):
  """ Returns a pin to the kernel with sysfs /sys/class/gpio interface.
      Returns True if pin was unexported, False if it was already under 
      kernel control. """
  if ("USR" in gpio_pin):
    # The user LEDs are always under userspace control
    return False
  gpio_num = GPIO[gpio_pin][2]
  gpio_file = '%s/gpio%i' % (GPIO_FILE_BASE, gpio_num)
  print gpio_file
  if (not os.path.exists(gpio_file)): 
    # Pin not under userspace control
    return False
  print UNEXPORT_FILE
  with open(UNEXPORT_FILE, 'wb') as f:
    f.write(str(gpio_num))
  return True


########NEW FILE########
__FILENAME__ = pwm
# pwm.py 
# Part of PyBBIO
# github.com/alexanderhiam/PyBBIO
# Apache 2.0 license
# 
# Beaglebone PWM driver for kernel >= 3.8

import cape_manager, sysfs
from bbio.util import delay, addToCleanup
from config import *

PWM_PINS_ENABLED = {}

def pwm_init():
  pass

def pwm_cleanup():
  pass

def analogWrite(pwm_pin, value, resolution=RES_8BIT, polarity=0):
  """ Sets the duty cycle of the given PWM output using the
      given resolution. If polarity=0 this will set the width of
      the positive pulse, otherwise it will set the width of the
      negative pulse. """
  # Make sure the pin is configured:
  pwmEnable(pwm_pin)
  pin_config = PWM_PINS[pwm_pin]
  helper_path = pin_config[1]
  try:
    assert resolution > 0, "*PWM resolution must be greater than 0"
    if (value < 0): value = 0
    if (value >= resolution): value = resolution-1
    period_ns = int(sysfs.kernelFilenameIO('%s/%s' % (helper_path, PWM_PERIOD)))
    # Todo: round values properly!: 
    duty_ns = int(value * (period_ns/resolution))
    sysfs.kernelFilenameIO('%s/%s' % (helper_path, PWM_DUTY), str(duty_ns))
    if polarity == 0:
      sysfs.kernelFilenameIO('%s/%s' % (helper_path, PWM_POLARITY), '0')
    else:
      sysfs.kernelFilenameIO('%s/%s' % (helper_path, PWM_POLARITY), '1')
    # Enable output:
    if (sysfs.kernelFilenameIO('%s/%s' % (helper_path, PWM_RUN)) == '0\n'):
      sysfs.kernelFilenameIO('%s/%s' % (helper_path, PWM_RUN), '1') 
  except IOError:
    print "*PWM pin '%s' reserved by another process!" % pwm_pin

# For those who don't like calling a digital signal analog:
pwmWrite = analogWrite

def pwmFrequency(pwm_pin, freq_hz):
  """ Sets the frequncy in Hertz of the given PWM output's module. """
  assert (pwm_pin in PWM_PINS), "*Invalid PWM pin: '%s'" % pwm_pin
  assert freq_hz > 0, "*PWM frequency must be greater than 0"
  # Make sure the pin is configured:
  pwmEnable(pwm_pin)
  # calculate the duty cycle in nanoseconds for the new period:
  pin_config = PWM_PINS[pwm_pin]
  helper_path = pin_config[1]

  old_duty_ns = int(sysfs.kernelFilenameIO('%s/%s' % (helper_path, PWM_DUTY)))
  old_period_ns = int(sysfs.kernelFilenameIO('%s/%s' % (helper_path, PWM_PERIOD)))

  duty_percent = old_duty_ns / old_period_ns
  new_period_ns = int(1e9/freq_hz)
  # Todo: round values properly!:
  new_duty_ns = int(duty_percent * new_period_ns)

  try: 
    # Duty cyle must be set to 0 before changing frequency:
    sysfs.kernelFilenameIO('%s/%s' % (helper_path, PWM_DUTY), '0')
    # Set new frequency:
    sysfs.kernelFilenameIO('%s/%s' % (helper_path, PWM_PERIOD), str(new_period_ns))
    # Set the duty cycle:
    sysfs.kernelFilenameIO('%s/%s' % (helper_path, PWM_DUTY), str(new_duty_ns))
  except IOError:
    print "*PWM pin '%s' reserved by another process!" % pwm_pin
    # that's probably not the best way to handle this error...
  
def pwmEnable(pwm_pin):
  """ Ensures PWM module for the given pin is enabled and its ocp helper
      is loaded. """
  global PWM_PINS_ENABLED
  if PWM_PINS_ENABLED.get(pwm_pin): return
  pin_config = PWM_PINS[pwm_pin]
  assert (pin_config), "*Invalid PWM pin: '%s'" % pwm_pin

  for overlay in pin_config[2]:
    cape_manager.load(overlay, auto_unload=False)
    delay(250) # Give it some time to take effect
  cape_manager.load(pin_config[0], auto_unload=False)
  delay(250)

  helper_path = pin_config[1]
  # Make sure output is disabled, so it won't start outputing a 
  # signal until analogWrite() is called: 
  if (sysfs.kernelFilenameIO('%s/%s' % (helper_path, PWM_RUN)) == '1\n'):
    sysfs.kernelFilenameIO('%s/%s' % (helper_path, PWM_RUN), '0')

  # Duty cyle must be set to 0 before changing frequency:
  sysfs.kernelFilenameIO('%s/%s' % (helper_path, PWM_DUTY), '0')
  # Is this still true??

  sysfs.kernelFilenameIO('%s/%s' % (helper_path, PWM_PERIOD), 
                      str(PWM_DEFAULT_PERIOD))
  addToCleanup(lambda : pwmDisable(pwm_pin))
  PWM_PINS_ENABLED[pwm_pin] = True


def pwmDisable(pwm_pin):
  """ Disables PWM output on given pin. """
  pin_config = PWM_PINS[pwm_pin]
  assert (pin_config), "*Invalid PWM pin: '%s'" % pwm_pin
  helper_path = pin_config[1]
  sysfs.kernelFilenameIO('%s/%s' % (helper_path, PWM_RUN), '0')
  PWM_PINS_ENABLED[pwm_pin] = False

########NEW FILE########
__FILENAME__ = uart
# 3.8/uart.py 
# Part of PyBBIO
# github.com/alexanderhiam/PyBBIO
# Apache 2.0 license
# 
# Beaglebone pinmux driver
# For Beaglebones with 3.8 kernel

import os, glob, cape_manager, bbio
from config import UART

def uartInit(uart):
  """ Enables the given uart by loading its dto. """
  port, overlay = UART[uart]
  if os.path.exists(port): return True
  # Unloading serial port overlays crashes the current cape manager, 
  # disable until it gets fixed:
  cape_manager.load(overlay, auto_unload=False)
  if os.path.exists(port): return True

  for i in range(5):
    # Give it some time to load
    bbio.delay(100)
    if os.path.exists(port): return True
    
  # If we make it here it's pretty safe to say the overlay couldn't load
  return False
########NEW FILE########
__FILENAME__ = api
# api.py 
# Part of PyBBIO
# github.com/alexanderhiam/PyBBIO
# Apache 2.0 license
# 
# Beaglebone platform API file.


from bbio.platform.beaglebone import *

def platform_init():
  analog_init()
  pwm_init()

def platform_cleanup():
  analog_cleanup()
  pwm_cleanup()
  serial_cleanup()



########NEW FILE########
__FILENAME__ = config_common
# PyBBIO config file for bealebone

#---------------------------------------------------#
# Changes to this file may lead to permanent damage #
# to you Beaglebone, edit with care.                #
#---------------------------------------------------#

MMAP_OFFSET = 0x44c00000 
MMAP_SIZE   = 0x48ffffff-MMAP_OFFSET


########################################
##--- Start control module config: ---##

CONF_SLEW_SLOW    = 1<<6
CONF_RX_ACTIVE    = 1<<5
CONF_PULLUP       = 1<<4
CONF_PULLDOWN     = 0x00
CONF_PULL_DISABLE = 1<<3

CONF_GPIO_MODE   = 0x07 
CONF_GPIO_OUTPUT = CONF_GPIO_MODE
CONF_GPIO_INPUT  = CONF_GPIO_MODE | CONF_RX_ACTIVE
CONF_ADC_PIN     = CONF_RX_ACTIVE | CONF_PULL_DISABLE

##--- End control module config ------##
########################################

##############################
##--- Start GPIO config: ---##

GPIO_FILE_BASE = '/sys/class/gpio'
EXPORT_FILE = GPIO_FILE_BASE + '/export'
UNEXPORT_FILE = GPIO_FILE_BASE + '/unexport'


# Digital IO keywords:
INPUT    =  1
OUTPUT   =  0
PULLDOWN = -1
NOPULL   =  0
PULLUP   =  1
HIGH     =  1
LOW      =  0
RISING   =  1
FALLING  = -1
BOTH     =  0
MSBFIRST =  1
LSBFIRST = -1

## GPIO pins:

# GPIO pins must be in form: 
#             [signal_name, dt_offset, gpio_num], where 'dt_offset' is 
# the control module register offset from 44e10800 as used in the device 
# tree, and 'gpio_num' is the pin number used by the kernel driver,  e.g.:
# "GPIO1_4" = [ 'gpmc_ad4',      0x10, 32*1 + 4]

GPIO = {
      "USR0" : [          'gpmc_a5', 0x054, 1*32+21],
      "USR1" : [          'gpmc_a6', 0x058, 1*32+22],
      "USR2" : [          'gpmc_a7', 0x05c, 1*32+23],
      "USR3" : [          'gpmc_a8', 0x060, 1*32+24],
   "GPIO0_2" : [        'spi0_sclk', 0x150, 0*32+ 2],
   "GPIO0_3" : [          'spi0_d0', 0x154, 0*32+ 3],
   "GPIO0_4" : [          'spi0_d1', 0x158, 0*32+ 4],
   "GPIO0_5" : [         'spi0_cs0', 0x15c, 0*32+ 5],
   "GPIO0_7" : ['ecap0_in_pwm0_out', 0x164, 0*32+ 7],
   "GPIO0_8" : [       'lcd_data12', 0x0d0, 0*32+ 8],
   "GPIO0_9" : [       'lcd_data13', 0x0d4, 0*32+ 9],
  "GPIO0_10" : [       'lcd_data14', 0x0d8, 0*32+10],
  "GPIO0_11" : [       'lcd_data15', 0x0dc, 0*32+11],
  "GPIO0_12" : [       'uart1_ctsn', 0x178, 0*32+12],
  "GPIO0_13" : [       'uart1_rtsn', 0x17c, 0*32+13],
  "GPIO0_14" : [        'uart1_rxd', 0x180, 0*32+14],
  "GPIO0_15" : [        'uart1_txd', 0x184, 0*32+15],
  "GPIO0_20" : [ 'xdma_event_intr1', 0x1b4, 0*32+20],
  "GPIO0_22" : [         'gpmc_ad8', 0x020, 0*32+22],
  "GPIO0_23" : [         'gpmc_ad9', 0x024, 0*32+23],
  "GPIO0_26" : [        'gpmc_ad10', 0x028, 0*32+26],
  "GPIO0_27" : [        'gpmc_ad11', 0x02c, 0*32+27],
  "GPIO0_30" : [       'gpmc_wait0', 0x070, 0*32+30],
  "GPIO0_31" : [         'gpmc_wpn', 0x074, 0*32+31],
   "GPIO1_0" : [         'gpmc_ad0', 0x000, 1*32+ 0],
   "GPIO1_1" : [         'gpmc_ad1', 0x004, 1*32+ 1],
   "GPIO1_2" : [         'gpmc_ad2', 0x008, 1*32+ 2],
   "GPIO1_3" : [         'gpmc_ad3', 0x00c, 1*32+ 3],
   "GPIO1_4" : [         'gpmc_ad4', 0x010, 1*32+ 4],
   "GPIO1_5" : [         'gpmc_ad5', 0x014, 1*32+ 5],
   "GPIO1_6" : [         'gpmc_ad6', 0x018, 1*32+ 6],
   "GPIO1_7" : [         'gpmc_ad7', 0x01c, 1*32+ 7],
  "GPIO1_12" : [        'gpmc_ad12', 0x030, 1*32+12],
  "GPIO1_13" : [        'gpmc_ad13', 0x034, 1*32+13],
  "GPIO1_14" : [        'gpmc_ad14', 0x038, 1*32+14],
  "GPIO1_15" : [        'gpmc_ad15', 0x03c, 1*32+15],
  "GPIO1_16" : [          'gpmc_a0', 0x040, 1*32+16],
  "GPIO1_17" : [          'gpmc_a1', 0x044, 1*32+17],
  "GPIO1_18" : [          'gpmc_a2', 0x048, 1*32+18],
  "GPIO1_19" : [          'gpmc_a3', 0x04c, 1*32+19],
  "GPIO1_28" : [        'gpmc_ben1', 0x078, 1*32+28],
  "GPIO1_29" : [        'gpmc_csn0', 0x07c, 1*32+29],
  "GPIO1_30" : [        'gpmc_csn1', 0x080, 1*32+30],
  "GPIO1_31" : [        'gpmc_csn2', 0x084, 1*32+31],
   "GPIO2_1" : [         'gpmc_clk', 0x08c, 2*32+ 1],
   "GPIO2_2" : [    'gpmc_advn_ale', 0x090, 2*32+ 2],
   "GPIO2_3" : [     'gpmc_oen_ren', 0x094, 2*32+ 3],
   "GPIO2_4" : [         'gpmc_wen', 0x098, 2*32+ 4],
   "GPIO2_5" : [    'gpmc_ben0_cle', 0x09c, 2*32+ 5],
   "GPIO2_6" : [        'lcd_data0', 0x0a0, 2*32+ 6],
   "GPIO2_7" : [        'lcd_data1', 0x0a4, 2*32+ 7],
   "GPIO2_8" : [        'lcd_data2', 0x0a8, 2*32+ 8],
   "GPIO2_9" : [        'lcd_data3', 0x0ac, 2*32+ 9],
  "GPIO2_10" : [        'lcd_data4', 0x0b0, 2*32+10],
  "GPIO2_11" : [        'lcd_data5', 0x0b4, 2*32+11],
  "GPIO2_12" : [        'lcd_data6', 0x0b8, 2*32+12],
  "GPIO2_13" : [        'lcd_data7', 0x0bc, 2*32+13],
  "GPIO2_14" : [        'lcd_data8', 0x0c0, 2*32+14],
  "GPIO2_15" : [        'lcd_data9', 0x0c4, 2*32+15],
  "GPIO2_16" : [       'lcd_data10', 0x0c8, 2*32+16],
  "GPIO2_17" : [       'lcd_data11', 0x0cc, 2*32+17],
  "GPIO2_22" : [        'lcd_vsync', 0x0e0, 2*32+22],
  "GPIO2_23" : [        'lcd_hsync', 0x0e4, 2*32+23],
  "GPIO2_24" : [         'lcd_pclk', 0x0e8, 2*32+24],
  "GPIO2_25" : [   'lcd_ac_bias_en', 0x0ec, 2*32+25],
  "GPIO3_14" : [     'mcasp0_aclkx', 0x190, 3*32+14],
  "GPIO3_15" : [       'mcasp0_fsx', 0x194, 3*32+15],
  "GPIO3_16" : [      'mcasp0_axr0', 0x198, 3*32+16],
  "GPIO3_17" : [    'mcasp0_ahclkr', 0x19c, 3*32+17],
  "GPIO3_19" : [       'mcasp0_fsr', 0x1a4, 3*32+19],
  "GPIO3_21" : [    'mcasp0_ahclkx', 0x1ac, 3*32+21]
}

# Having available pins in a dictionary makes it easy to
# check for invalid pins, but it's nice not to have to pass
# around strings, so here's some friendly constants:
USR0 = "USR0"
USR1 = "USR1"
USR2 = "USR2"
USR3 = "USR3"
GPIO0_2  = "GPIO0_2"
GPIO0_3  = "GPIO0_3"
GPIO0_4  = "GPIO0_4"
GPIO0_5  = "GPIO0_5"
GPIO0_7  = "GPIO0_7"
GPIO0_8  = "GPIO0_8"
GPIO0_9  = "GPIO0_9"
GPIO0_10 = "GPIO0_10"
GPIO0_11 = "GPIO0_11"
GPIO0_12 = "GPIO0_12"
GPIO0_13 = "GPIO0_13"
GPIO0_14 = "GPIO0_14"
GPIO0_15 = "GPIO0_15"
GPIO0_20 = "GPIO0_20"
GPIO0_22 = "GPIO0_22"
GPIO0_23 = "GPIO0_23"
GPIO0_26 = "GPIO0_26"
GPIO0_27 = "GPIO0_27"
GPIO0_30 = "GPIO0_30"
GPIO0_31 = "GPIO0_31"
GPIO1_0  = "GPIO1_0"
GPIO1_1  = "GPIO1_1"
GPIO1_2  = "GPIO1_2"
GPIO1_3  = "GPIO1_3"
GPIO1_4  = "GPIO1_4"
GPIO1_5  = "GPIO1_5"
GPIO1_6  = "GPIO1_6"
GPIO1_7  = "GPIO1_7"
GPIO1_12 = "GPIO1_12"
GPIO1_13 = "GPIO1_13"
GPIO1_14 = "GPIO1_14"
GPIO1_15 = "GPIO1_15"
GPIO1_16 = "GPIO1_16"
GPIO1_17 = "GPIO1_17"
GPIO1_18 = "GPIO1_18"
GPIO1_19 = "GPIO1_19"
GPIO1_28 = "GPIO1_28"
GPIO1_29 = "GPIO1_29"
GPIO1_30 = "GPIO1_30"
GPIO1_31 = "GPIO1_31"
GPIO2_1  = "GPIO2_1"
GPIO2_2  = "GPIO2_2"
GPIO2_3  = "GPIO2_3"
GPIO2_4  = "GPIO2_4"
GPIO2_5  = "GPIO2_5"
GPIO2_6  = "GPIO2_6"
GPIO2_7  = "GPIO2_7"
GPIO2_8  = "GPIO2_8"
GPIO2_9  = "GPIO2_9"
GPIO2_10 = "GPIO2_10"
GPIO2_11 = "GPIO2_11"
GPIO2_12 = "GPIO2_12"
GPIO2_13 = "GPIO2_13"
GPIO2_14 = "GPIO2_14"
GPIO2_15 = "GPIO2_15"
GPIO2_16 = "GPIO2_16"
GPIO2_17 = "GPIO2_17"
GPIO2_22 = "GPIO2_22"
GPIO2_23 = "GPIO2_23" 
GPIO2_24 = "GPIO2_24"
GPIO2_25 = "GPIO2_25"
GPIO3_14 = "GPIO3_14"
GPIO3_15 = "GPIO3_15"
GPIO3_16 = "GPIO3_16"
GPIO3_17 = "GPIO3_17"
GPIO3_19 = "GPIO3_19"
GPIO3_21 = "GPIO3_21"


##--- End GPIO config ------##
##############################


##############################
##--- Start UART config: ---##

# Formatting constants to mimic Arduino's serial.print() formatting:
DEC = 'DEC'
BIN = 'BIN'
OCT = 'OCT'
HEX = 'HEX'

##--- End UART config ------##
##############################


##############################
##--- Start PWM config: ----##

# Predefined resolutions for analogWrite():
RES_16BIT = 2**16
RES_8BIT  = 2**8
PERCENT   = 100

# Default frequency in Hz of PWM modules (must be >0):
PWM_DEFAULT_FREQ = 100000

##--- End PWM config: ------##
##############################

########NEW FILE########
__FILENAME__ = gpio
# gpio.py 
# Part of PyBBIO
# github.com/alexanderhiam/PyBBIO
# Apache 2.0 license
# 
# Beaglebone GPIO driver

import os, pinmux, math, sysfs
from bbio.util import addToCleanup
from config import *


def getGPIODirectory(gpio_pin):
  """ Returns the sysfs kernel driver base directory for the given pin. """
  if 'USR' in gpio_pin:
    # USR LEDs use a different driver
    return GET_USR_LED_DIRECTORY(gpio_pin)
  gpio_num = GPIO[gpio_pin][2]
  return '%s/gpio%i' % (GPIO_FILE_BASE, gpio_num)


def getGPIODirectionFile(gpio_pin):
  """ Returns the absolute path to the state control file for the given pin. """
  if 'USR' in gpio_pin:
    # USR LED driver doesn't have a direction file
    return ''
  d = getGPIODirectory(gpio_pin)
  return '%s/direction' % d


def getGPIOStateFile(gpio_pin):
  """ Returns the absolute path to the state control file for the given pin. """
  d = getGPIODirectory(gpio_pin)
  if 'USR' in gpio_pin:
    # USR LEDs use a different driver
    return '%s/brightness' % d
  return '%s/value' % d


def pinMode(gpio_pin, direction, pull=0, preserve_mode_on_exit=False):
  """ Sets given digital pin to input if direction=1, output otherwise.
      'pull' will set the pull up/down resistor if setting as an input:
      pull=-1 for pull-down, pull=1 for pull up, pull=0 for none. 
      If preserve_mode_on_exit=True, the DT overlay and will remain 
      loaded, the pin will remain exported to user-space control, and 
      the INPUT/OUTPUT mode will be preserved when the program exits. """

  if 'USR' in gpio_pin:
    print 'warning: pinMode() not supported for USR LEDs'
    return
  assert (gpio_pin in GPIO), "*Invalid GPIO pin: '%s'" % gpio_pin
  exported = pinmux.export(gpio_pin)
  if not exported:
    print "warning: could not export pin '%s', skipping pinMode()" % gpio_pin
    return
  elif preserve_mode_on_exit:
    addToCleanup(lambda: pinmux.unexport(gpio_pin))

  direction_file = getGPIODirectionFile(gpio_pin)

  if (direction == INPUT):
    # Pinmux:
    if (pull > 0): pull = CONF_PULLUP
    elif (pull < 0): pull = CONF_PULLDOWN
    else: pull = CONF_PULL_DISABLE
    pinmux.pinMux(gpio_pin, CONF_GPIO_INPUT | pull, preserve_mode_on_exit)
    # Set input:
    with open(direction_file, 'wb') as f:
      f.write('in')
    return
  # Pinmux:
  pinmux.pinMux(gpio_pin, CONF_GPIO_OUTPUT, preserve_mode_on_exit)
  # Set output:
  with open(direction_file, 'wb') as f:
    f.write('out')


def digitalWrite(gpio_pin, state):
  """ Writes given digital pin low if state=0, high otherwise. """
  assert (gpio_pin in GPIO), "*Invalid GPIO pin: '%s'" % gpio_pin
  gpio_file = getGPIOStateFile(gpio_pin)
  if not os.path.exists(gpio_file):
    print "warning: digitalWrite() failed, pin '%s' not exported." % gpio_pin +\
          " Did you call pinMode()?" 
    return
  if (state):    
    sysfs.kernelFilenameIO(gpio_file, '1')
  else:
    sysfs.kernelFilenameIO(gpio_file, '0')


def digitalRead(gpio_pin):
  """ Returns input pin state as 1 or 0. """
  assert (gpio_pin in GPIO), "*Invalid GPIO pin: '%s'" % gpio_pin
  gpio_file = getGPIOStateFile(gpio_pin)
  return int(sysfs.kernelFilenameIO(gpio_file))


def toggle(gpio_pin):
  """ Toggles the state of the given digital pin. """
  digitalWrite(gpio_pin, digitalRead(gpio_pin) ^ 1)


def pinState(gpio_pin):
  """ Returns the state of a digital pin if it is configured as
      an output. Returns None if it is configuredas an input. """
  # With sysfs driver this is identical to digitalRead()
  return digitalRead(gpio_pin)


def shiftIn(data_pin, clk_pin, bit_order, n_bits=8, edge=FALLING):
  """ Implements software SPI on the given pins to receive given  number
      of bits from a slave device. edge is the edge which triggers the
      device to write data. """
  # Ensure clock is in idle state:
  digitalWrite(clk_pin, HIGH if (edge==FALLING) else LOW)
  if (bit_order == MSBFIRST): loop_range = (n_bits-1, -1, -1)
  else: loop_range = (n_bits,) 
  data = 0
  for i in range(*loop_range):    
    digitalWrite(clk_pin, LOW if (edge==FALLING) else HIGH)
    digitalWrite(clk_pin, HIGH if (edge==FALLING) else LOW)
    data |= digitalRead(data_pin) << i
  return data

def shiftOut(data_pin, clk_pin, bit_order, data, edge=FALLING):
  """ Implements software SPI on the given pins to shift out data.
      data can be list, string, or integer, and if more than one byte
      each byte will be shifted out with the same endianness as the 
      bits. """
  assert (type(data) != dict), "*shiftOut() does not support dictionaries" 
  assert (type(data) != float), "*shiftOut() does not support floats" 

  if ((type(data) != int) and ((len(data) > 1) or (type(data) == list))):
    # Test for type list here to handle lists of length 1
    for i in data if (bit_order == MSBFIRST) else data[::-1]:
      # Loop through forward if MSB first, otherwise in reverse
      shiftOut(data_pin, clk_pin, bit_order, i, edge)
  else: 
    if (type(data) == str): 
      # Data is a single character here, get ascii value:
      data = ord(data)
      n_bytes = 1
    else:
      # Value is a number, calculate number of bytes:
      if (data == 0):
        # int.bit_length(0) returns 0:
        n_bytes = 1
      else: 
        n_bytes = int(math.ceil(data.bit_length()/8.0))

    # Ensure clock is in idle state:
    digitalWrite(clk_pin, HIGH if (edge==FALLING) else LOW)

    byte_range = (n_bytes-1, -1, -1) if (bit_order == MSBFIRST) else (n_bytes,)
    bit_range = (7, -1, -1)if (bit_order == MSBFIRST) else (8,)
    # Shift out the data:
    for i in range(*byte_range):
      byte = data >> (8*i)
      for j in range(*bit_range):
        digitalWrite(data_pin, (byte>>j) & 0x01)
        digitalWrite(clk_pin, LOW if (edge==FALLING) else HIGH)
        digitalWrite(clk_pin, HIGH if (edge==FALLING) else LOW)

########NEW FILE########
__FILENAME__ = i2c
# i2c.py 
# Part of PyBBIO
# github.com/alexanderhiam/PyBBIO
# This library - github.com/deepakkarki
# Apache 2.0 license
# 
# Beaglebone i2c driver

#Note : Three i2c buses are present on the BBB; i2c-0 is used for eeprom access - so not useable
#       i2c-1 is loaded default; /devices/ocp.2/4819c000.i2c/i2c-1  ---- this actually is the i2c2 bus
#       to activate i2c1 bus; echo BB-I2C1 > /sys/devices/bone_capemgr.8/slots; will be now present at /dev/i2c-2
#       reference : http://datko.net/2013/11/03/bbb_i2c/

##
##


import bbio
from config import I2C
from i2c_setup import i2cInit

try:
  import smbus
except:
  print "\n python-smbus module not found\n"
  print "on Angstrom Linux : ~#opkg install python-smbus\n"
  print "on Ubuntu, Debian : ~#apt-get install python-smbus"


class _I2C_BUS(object):

    def __init__(self, bus):
        '''
        self : _I2C_BUS object
        bus : string - represents bus address eg. i2c1, i2c2; not dev_file
        '''
        assert bus in I2C, "Invalid bus address %s" %bus
        self.config = bus
        self.bus = None # This is the smbus object
        self.open = False

    def begin(self):
        '''
        Initializes the I2C bus with BBB as master
        '''
        if not i2cInit(self.config):
            print "Could not initialize i2c bus : %s" % self.config 
            return
        self.bus = smbus.SMBus(int(I2C[self.config][0][-1]))
        #smbus takes the dev_file number as parameter, not bus number
        #so if I pass 1 as the parameter, is uses /dev/i2c-1 file not i2c1 bus
        self.open = True

    def write(self, addr, reg, val):
        '''
        Writes value 'val' to address 'addr'
        addr : integer between (0-127) - Address of slave device
        reg : register of the slave device you want to write to
        val : string, integer or list - if list, writes each value in the list
        returns number of bytes written
        '''
        if not self.open:
            print "I2C bus : %s - not initialized" % self.config
            return

        try:
            if type(val) == int:
                self.bus.write_byte_data(addr, reg, val)
                return 1

            else:
                data = self._format(val)
                if data:
                    for i, unit in enumerate(data):
                        self.bus.write_byte_data(addr, reg+i, unit)
                        bbio.delay(4) #4 microsecond delay
                        #delay reqd, otherwise loss of data
                    return len(data)
                else: 
                    return 0

        except IOError as e:
            print "Bus is active : check if device with address %d is connected/activated" %addr


    def _format(self, val):
        '''
        used to format values given to write into reqd format 
        val : string or list (of integers or strings)
        returns : list of integers, if bad paramater - returns None
        '''

        if type(val) == str:
            return map(lambda x: ord(x), list(val))

        if type(val) == list and len(val):
            #non empty list

            if len(filter(lambda x: type(x) == int, val)) == len(val):
                #all variables are integers
                return val

            if len(filter(lambda x: type(x) == str, val)) == len(val):
                #all variables are strings
                data = []
                for unit in val:
                    data.extend(list(unit))
                return map(lambda x: ord(x), list(data))

        return None


    def read(self, addr, reg, size=1):
        '''
        Reads 'size' number of bytes from slave device 'addr'
        addr : integer between (0-127) - Address of slave device
        reg : register of the slave device you want to read from
        size : integer - number of bytes to be read
        returns an int if size is 1; else list of integers
        '''
        if not self.open:
            print "I2C bus : %s - not initialized, open before read" % self.config

        try:

            if size == 1:
                return self.bus.read_byte_data(addr, reg)

            else:
                read_data = []
                for i in range(size):
                    data = self.bus.read_byte_data(addr, reg+i)
                    bbio.delay(4)
                    read_data.append(data)

            return read_data

        except IOError as e:
            print "Bus is active : check if device with address %d is connected/activated" %addr


    def end(self):
        '''
        BBB exits the bus
        '''
        if self.bus:
            result = self.bus.close()
            self.open = False
            return True
        else:
            print "i2c bus : %s - is not open. use begin() first" % self.config 
            return False



    def _process(self, val):
        '''
        Internal function to handle datatype conversions while writing to the devices
        val - some object
        returns a processed val that can be written to the I2C device
        '''
        # Keep this for prints
        pass

    def prints(self, addr, string):
        '''
        prints a string to the device with address 'addr' 
        addr : integer(0-127) - address of slave device
        string : string - to be written to slave device
        '''
        pass
        #fill this later - could be used to send formatted text across to some I2C based screens (?)

def i2c_cleanup():
    """
    Ensures that all i2c buses opened by current process are freed. 
    """
    for bus in (Wire1, Wire2):
        if bus.open:
            bus.end()

#For arduino like similariy 
Wire1 = _I2C_BUS('i2c1') #pins 17-18 OR 24-26
# ^ not initialized by default; /dev/i2c-2
#need to apply overlay for this

Wire2 = _I2C_BUS('i2c2') #pins 19-20 OR 21-22
#initialized by default; /dev/i2c-1# i2c.py 

########NEW FILE########
__FILENAME__ = interrupt
# interrupt.py 
# Part of PyBBIO
# github.com/alexanderhiam/PyBBIO
# Apache 2.0 license
# 
# Beaglebone GPIO interrupt driver
#
# Most of the code in this file was written and contributed by 
# Alan Christopher Thomas - https://github.com/alanctkc
# Thanks!

from config import *
from gpio import *
import select, threading, os


INTERRUPT_VALUE_FILES = {}

class EpollListener(threading.Thread):
  def __init__(self):
    self.epoll = select.epoll()
    self.epoll_callbacks = {}
    super(EpollListener, self).__init__()

  def run(self):
    while True:
      if len(self.epoll_callbacks) == 0: break
      events = self.epoll.poll()
      for fileno, event in events:
        if fileno in self.epoll_callbacks:
          self.epoll_callbacks[fileno]()
        
  def register(self, gpio_pin, callback):
    """ Register an epoll trigger for the specified fileno, and store
        the callback for that trigger. """
    fileno = INTERRUPT_VALUE_FILES[gpio_pin].fileno()
    self.epoll.register(fileno, select.EPOLLIN | select.EPOLLET)
    self.epoll_callbacks[fileno] = callback
    
  def unregister(self, gpio_pin):
    fileno = INTERRUPT_VALUE_FILES[gpio_pin].fileno()
    self.epoll.unregister(fileno)
    INTERRUPT_VALUE_FILES[gpio_pin].close()
    del INTERRUPT_VALUE_FILES[gpio_pin]
    del self.epoll_callbacks[fileno]  

EPOLL_LISTENER = EpollListener()
EPOLL_LISTENER.daemon = True

def attachInterrupt(gpio_pin, callback, mode=BOTH):
  """ Sets an interrupt on the specified pin. 'mode' can be RISING, FALLING,
      or BOTH. 'callback' is the method called when an event is triggered. """
  # Start the listener thread
  if not EPOLL_LISTENER.is_alive():
    EPOLL_LISTENER.start()
  gpio_num = int(gpio_pin[4])*32 + int(gpio_pin[6:])
  INTERRUPT_VALUE_FILES[gpio_pin] = open(
    os.path.join(GPIO_FILE_BASE, 'gpio%i' % gpio_num, 'value'), 'r')
  _edge(gpio_pin, mode)
  EPOLL_LISTENER.register(gpio_pin, callback)

def detachInterrupt(gpio_pin):
  """ Detaches the interrupt from the given pin if set. """
  gpio_num = int(gpio_pin[4])*32 + int(gpio_pin[6:])
  EPOLL_LISTENER.unregister(gpio_pin)
  
def _edge(gpio_pin, mode):
  """ Sets an edge-triggered interrupt with sysfs /sys/class/gpio
      interface. Returns True if successful, False if unsuccessful. """
  gpio_num = int(gpio_pin[4])*32 + int(gpio_pin[6:])
  if (not os.path.exists(GPIO_FILE_BASE + 'gpio%i' % gpio_num)): 
    # Pin not under userspace control
    return False
  edge_file = os.path.join(GPIO_FILE_BASE, 'gpio%i' % gpio_num, 'edge')
  with open(edge_file, 'wb') as f:
    if mode == RISING:
      f.write('rising')
    elif mode == FALLING:
      f.write('falling')
    elif mode == BOTH:
      f.write('both')
  return True

########NEW FILE########
__FILENAME__ = memory
# memory.py 
# Part of PyBBIO
# github.com/alexanderhiam/PyBBIO
# Apache 2.0 license
# 
# Beaglebone memory register access driver
#
# 16-bit register support mod from sbma44 - https://github.com/sbma44


from bbio.platform.beaglebone import driver

def andReg(address, mask, length=32):
  """ Sets 16 or 32 bit Register at address to its current value AND mask. """
  setReg(address, getReg(address, length)&mask, length)

def orReg(address, mask, length=32):
  """ Sets 16 or 32 bit Register at address to its current value OR mask. """
  setReg(address, getReg(address, length)|mask, length)

def xorReg(address, mask, length=32):
  """ Sets 16 or 32 bit Register at address to its current value XOR mask. """
  setReg(address, getReg(address, length)^mask, length)

def clearReg(address, mask, length=32):
  """ Clears mask bits in 16 or 32 bit register at given address. """
  andReg(address, ~mask, length)

def getReg(address, length=32):
  """ Returns unpacked 16 or 32 bit register value starting from address. """
  if (length == 32):
    return driver.getReg(address)
  elif (length == 16):
    return driver.getReg16(address)
  else:
    raise ValueError("Invalid register length: %i - must be 16 or 32" % length)

def setReg(address, new_value, length=32):
  """ Sets 16 or 32 bits at given address to given value. """
  if (length == 32):
      driver.setReg(address, new_value)
  elif (length == 16):
      driver.setReg16(address, new_value)
  else:
    raise ValueError("Invalid register length: %i - must be 16 or 32" % length)

########NEW FILE########
__FILENAME__ = serial_port
# serial_port.py 
# Part of PyBBIO
# github.com/alexanderhiam/PyBBIO
# Apache 2.0 license
# 
# Beaglebone serial driver


from uart import uartInit
from config import *

try:
  import serial
except:
  print "\n pyserial module not found; to install:\n\
   # opkg update && opkg install python-pyserial\n"



# _UART_PORT is a wrapper class for pySerial to enable Arduino-like access
# to the UART1, UART2, UART4, and UART5 serial ports on the expansion headers:
class _UART_PORT(object):
  def __init__(self, uart):
    assert uart in UART, "*Invalid UART: %s" % uart
    self.config = uart
    self.baud = 0
    self.open = False
    self.ser_port = None
    self.peek_char = ''

  def begin(self, baud, timeout=1, **kwargs):
    """ Starts the serial port at the given baud rate. 'timeout' as well
        as any other given keyword arguments will be passed to the PySerial 
        Serial class' __init__() method, see the PySerial docs for more info. 
    """
    if not uartInit(self.config):
      print "*Could not open serial port defined by: %s" % self.config
      self.ser_port = None
      return
    port = UART[self.config][0]
    self.baud = baud
    self.ser_port = serial.Serial(port, baud, timeout=timeout, **kwargs)
    self.open = True 

  def end(self):
    """ Closes the serial port if open. """
    if not(self.open): return
    self.flush()
    self.ser_port.close()
    self.ser_port = None
    self.baud = 0
    self.open = False

  def available(self):
    """ Returns the number of bytes currently in the receive buffer. """
    return self.ser_port.inWaiting() + len(self.peek_char)

  def read(self):
    """ Returns first byte of data in the receive buffer or -1 if timeout reached. """
    if (self.peek_char):
      c = self.peek_char
      self.peek_char = ''
      return c
    byte = self.ser_port.read(1)
    return -1 if (byte == None) else byte

  def peek(self):
    """ Returns the next char from the receive buffer without removing it, 
        or -1 if no data available. """
    if (self.peek_char):
      return self.peek_char
    if self.available():
      self.peek_char = self.ser_port.read(1)
      return self.peek_char
    return -1    

  def flush(self):
    """ Waits for current write to finish then flushes rx/tx buffers. """
    self.ser_port.flush()
    self.peek_char = ''

  def prints(self, data, base=None):
    """ Prints string of given data to the serial port. Returns the number
        of bytes written. The optional 'base' argument is used to format the
        data per the Arduino serial.print() formatting scheme, see:
        http://arduino.cc/en/Serial/Print """
    return self.write(self._process(data, base))

  def println(self, data, base=None):
    """ Prints string of given data to the serial port followed by a 
        carriage return and line feed. Returns the number of bytes written.
        The optional 'base' argument is used to format the data per the Arduino
        serial.print() formatting scheme, see: http://arduino.cc/en/Serial/Print """
    return self.write(self._process(data, base)+"\r\n")

  def write(self, data):
    """ Writes given data to serial port. If data is list or string each
        element/character is sent sequentially. If data is float it is 
        converted to an int, if data is int it is sent as a single byte 
        (least significant if data > 1 byte). Returns the number of bytes
        written. """
    assert self.open, "*%s not open, call begin() method before writing" %\
                      UART[self.config][0]

    if (type(data) == float): data = int(data)
    if (type(data) == int): data = chr(data & 0xff)

    elif ((type(data) == list) or (type(data) == tuple)):
      bytes_written = 0
      for i in data:
        bytes_written += self.write(i)  
      return bytes_written

    elif (type(data) != str):
      # Type not supported by write, e.g. dict; use prints().
      return 0

    written = self.ser_port.write(data)
    # Serial.write() returns None if no bits written, we want 0:
    return written if written else 0

  def _process(self, data, base):
    """ Processes and returns given data per Arduino format specified on 
        serial.print() page: http://arduino.cc/en/Serial/Print """
    if (type(data) == str):
      # Can't format if already a string:
      return data

    if (type(data) is int):
      if not (base): base = DEC # Default for ints
      if (base == DEC):
        return str(data) # e.g. 20 -> "20"
      if (base == BIN):
        return bin(data)[2:] # e.g. 20 -> "10100"
      if (base == OCT):
        return oct(data)[1:] # e.g. 20 -> "24"
      if (base == HEX):
        return hex(data)[2:] # e.g. 20 -> "14"

    elif (type(data) is float):
      if not (base): base = 2 # Default for floats
      if ((base == 0)):
        return str(int(data))
      if ((type(base) == int) and (base > 0)):
        return ("%0." + ("%i" % base) + "f") % data

    # If we get here data isn't supported by this formatting scheme,
    # just convert to a string and return:
    return str(data)

# Initialize the global serial port instances:
Serial1 = _UART_PORT('UART1')
Serial2 = _UART_PORT('UART2')
Serial4 = _UART_PORT('UART4')
Serial5 = _UART_PORT('UART5')

def serial_cleanup():
  """ Ensures that all serial ports opened by current process are closed. """
  for port in (Serial1, Serial2, Serial4, Serial5):
    port.end()

########NEW FILE########
__FILENAME__ = sysfs
# sysfs.py 
# Part of PyBBIO
# github.com/alexanderhiam/PyBBIO
# Apache 2.0 license
# 
# Helper routines for sysfs kernel drivers

import glob
from bbio.platform._sysfs import _kernelFileIO


def kernelFilenameIO(fn, val=''):
  """ Calls _kernelFileIO. The filename should be a complete absolute path,
      and may inlcued asterisks, e.g. /sys/devices/ocp.*/some/file.
      For reading/writing files open in 'r+' mode. When called just
      with a file name, will return contents of file. When called
      with file name and 'val', the file will be overritten with
      new value and the changes flushed and returned. 'val' must be type str.
      Meant to be used with Kernel driver files for much more
      efficient IO (no need to reopen every time). """
  fn = glob.glob(fn)[0]
  return _kernelFileIO(fn, val)

########NEW FILE########
__FILENAME__ = util
# util.py
# Part of PyBBIO
# github.com/alexanderhiam/PyBBIO
# Apache 2.0 license
#
# This file contains routines and variables that may need to be
# accessed by internal drivers, which cannot import the bbio.py
# file because it imports them.

import time

ADDITIONAL_CLEANUP = [] # See add_cleanup() below.
START_TIME_MS = 0 # Set in run() - used by millis() and micros().

START_TIME_MS = 0
def util_init():
  global START_TIME_MS
  START_TIME_MS = time.time()*1000

def addToCleanup(routine):
  """ Takes a callable object to be called during the cleanup once a 
      program has stopped, e.g. a function to close a log file, kill 
      a thread, etc. """
  ADDITIONAL_CLEANUP.append(routine)

def millis():
  """ Returns roughly the number of millisoconds since program start. """
  return time.time()*1000 - START_TIME_MS

def micros():
  """ Returns roughly the number of microsoconds since program start. """
  return time.time()*1000000 - START_TIME_MS*1000

def delay(ms):
  """ Sleeps for given number of milliseconds. """
  time.sleep(ms/1000.0)

def delayMicroseconds(us):
  """ Sleeps for given number of microseconds > ~30; still working 
      on a more accurate method. """
  t = time.time()
  while (((time.time()-t)*1000000) < us): pass

########NEW FILE########
__FILENAME__ = ADS786x_test
"""
 ADS786x_test.py 
 Alexander Hiam - 12/2012
 
 Example program for PyBBIO's ADS786x library.

 This example program is in the public domain.
"""

from bbio import *
from ADS786x import *

# Set variables for the pins connected to the ADC:
data_pin = GPIO1_15  # P8.15
clk_pin  = GPIO1_14  # P8.16
cs_pin   = GPIO0_27  # P8.17

# Create an instance of the ADC class:
adc = ADS7866(data_pin, clk_pin, cs_pin)

def setup():
  # Nothing to do here, the ADS786x class sets pin modes
  pass

def loop():
  # Read the voltage and print it to the terminal:
  voltage = adc.readVolts()
  print "%0.3f V" % voltage
  delay(1000)


run(setup, loop)

########NEW FILE########
__FILENAME__ = analog_test
# analog_test.py - Alexander Hiam
# Testing analogRead() 
#
# Example circuit:
#  -Connect two equal value resistors around 10k ohm in series
#   between the 3.3v supply (pin 3 on P9) and GND (pin 2 on P9) 
#   to form a voltage divider. Where the two resistors connect 
#   will be near 1.8v (confirm with a voltmeter if available).
#
#  -Connect two potentiometers so that each has one of its outer 
#   pins connected to GND and the other to the 1.8v of the 
#   voltage divider. Connect the center pin of one to AIN0 (pin 
#   39 on P9) and the other to AIN2 (pin 37 on P9). 
#
#  -Run this program and watch the output as you turn the pots.
#
# *** NOTICE *** 
# The maximum ADC input voltage is 1.8v,
# applying greater voltages will likely cause
# permanent damage to the ADC module! 
#
# This example is in the public domain
 

# Import PyBBIO library:
from bbio import *

pot1 = AIN0 # pin 39 on header P9 
pot2 = AIN2 # pin 37 on header P9 

def setup():
  # Nothing to do here
  pass

def loop():
  # Get the ADC values:
  val1 = analogRead(pot1)
  val2 = analogRead(pot2)
  # And convert to voltages:
  voltage1 = inVolts(val1)
  voltage2 = inVolts(val2)
  print " pot1 ADC value: %i - voltage: %fv" % (val1, voltage1)
  print " pot2 ADC value: %i - voltage: %fv\n" % (val2, voltage2)
  delay(500)

# Start the loop:
run(setup, loop)

########NEW FILE########
__FILENAME__ = available_pins
# available_pins.py - Alexander Hiam
# Prints all the pins available for IO expansion by their 
# names used in PyBBIO (refer to beaglebone schematic for
# header locations).
#
# This example is in the public domain

# Import PyBBIO library:
from bbio import *

# Create a setup function:
def setup():
  print "\n GPIO pins:" 
  for i in GPIO.keys(): 
    print "   %s" % i
  print "\n ADC pins:" 
  for i in ADC.keys():
    print "   %s" % i
  print "\n PWM pins:" 
  for i in PWM_PINS.keys():
    print "   %s" % i


# Create a main function:
def loop():
  # No need to keep running
  stop()

# Start the loop:
run(setup, loop)


########NEW FILE########
__FILENAME__ = BBIOServer_mobile_test
#!/usr/bin/env python
"""
 BBIOServer_mobile_test.py 
 Alexander Hiam

 An example to demonstrate the use of the BBIOServer library
 for PyBBIO.

 This creates the same interface as BBIOServer_test.py, except
 the pages use the 'mobile.css' stylesheet, making it mobile
 device friendly. 

 This example program is in the public domain.
"""

# First we must import PyBBIO: 
from bbio import *
# Then we can import BBIOServer:
from BBIOServer import *

# Now we create a server instance:
server = BBIOServer()
# Port 8000 is used by default, but can be specified when creating
# server instance:
#  server = BBIOServer(port_number)
# It also defaults to blocking mode, but if we wanted it to run
# non-blocking, i.e. the loop() routine continues as normal while 
# the server runs in the background, we could say:
#  server = BBIOServer(blocking=False)


def voltage(analog_pin):
  """ Takes analog reading from given pin and returns a string 
      of the voltage to 2 decimal places. """
  return "%0.2f" % inVolts(analogRead(analog_pin))

def print_entry(text):
  """ Just prints the given text. """
  print "Text entered: \n  '%s'" % text

def setup():
  # Set the LEDs we'll be ontrolling as outputs:
  pinMode(USR2, OUTPUT)
  pinMode(USR3, OUTPUT)

  # Create our first page with the title 'PyBBIO Test', specifying the
  # mobile device stylesheet:
  home = Page("PyBBIO Test", stylesheet="mobile.css")
  # Add some text to the page:
  home.add_text("This is a test of the BBIOServer library for PyBBIO, "+\
                "using the 'mobile.css' mobile device stylesheet. " +\
                "Follow the links above to test the different pages.")                 
  # Create a new page to test the text input:
  text = Page("Text Input", stylesheet="mobile.css")
  text.add_text("Press submit to send the text in entry box:")

  # Create the text entry box on a new line; button will say 'Submit',
  # and when submitted the text in the box will be sent to print_entry():
  text.add_entry(lambda text: print_entry(text), "Submit", newline=True)

  # Create a new page to test the buttons and monitors:
  io = Page("I/O", stylesheet="mobile.css")
 
  # Make a LED control section using a heading:
  io.add_heading("LED Control")
  io.add_text("Control the on-board LEDs", newline=True)

  # Add a button on a new line with the label 'Toggle USR2 LED' that will
  # call 'toggle(USR2)' when pressed:
  io.add_button(lambda: toggle(USR2), "Toggle USR2 LED", newline=True)

  # Add a monitor which will continually call 'pinState(USR2)' and 
  # display the return value in the form: 'current state: [value]':
  io.add_monitor(lambda: pinState(USR2), "current state:")

  # Same thing here with the other LED:
  io.add_button(lambda: toggle(USR3), "Toggle USR3 LED", newline=True)
  io.add_monitor(lambda: pinState(USR3), "current state:")

  # Create another section for ADC readings:
  io.add_heading("ADC Readings")
  io.add_text("Read some ADC inputs", newline=True)

  # Add a monitor to display the ADC value:
  io.add_monitor(lambda: analogRead(AIN0), "AIN0 value:", newline=True)

  # And one on the same line to display the voltage using the voltage()
  # function defined above. Because the units variable is used this time
  # the value will be displayed in the form: 'voltage: [value] v':
  io.add_monitor(lambda: voltage(AIN0), "voltage:", units="v")

  # Same thing here:
  io.add_monitor(lambda: analogRead(AIN1), "AIN1 value:", newline=True)
  io.add_monitor(lambda: voltage(AIN1), "voltage:", units="v")

  # Then start the server, passing it all the pages. The first page
  # passed in will be the home page:
  server.start(home, text, io)


def loop():
  # We're running in blocking mode, so we won't get here until ctrl-c
  # is preseed. 
  print "\nServer has stopped"
  stop()



# Then run it the usual way:
run(setup, loop)

# Now, on a computer on the same network as you beaglebone, open your
# browser and navigate to:
#  your_beaglebone_ip:8000 
#  (replacing 8000 if you specified a different port)
# You should be redirected to your_beaglebone_ip:8000/pages/PyBBIOTest.html

########NEW FILE########
__FILENAME__ = BBIOServer_test
#!/usr/bin/env python
"""
 BBIOServer_test.py 
 Alexander Hiam

 An example to demonstrate the use of the BBIOServer library
 for PyBBIO.

 This example program is in the public domain.
"""

# First we must import PyBBIO: 
from bbio import *
# Then we can import BBIOServer:
from BBIOServer import *

# Now we create a server instance:
server = BBIOServer()
# Port 8000 is used by default, but can be specified when creating
# server instance:
#  server = BBIOServer(port_number)
# It also defaults to blocking mode, but if we wanted it to run
# non-blocking, i.e. the loop() routine continues as normal while 
# the server runs in the background, we could say:
#  server = BBIOServer(blocking=False)


def voltage(analog_pin):
  """ Takes analog reading from given pin and returns a string 
      of the voltage to 2 decimal places. """
  return "%0.2f" % inVolts(analogRead(analog_pin))

def print_entry(text):
  """ Just prints the given text. """
  print "Text entered: \n  '%s'" % text

def setup():
  # Set the LEDs we'll be ontrolling as outputs:
  pinMode(USR2, OUTPUT)
  pinMode(USR3, OUTPUT)

  # Create our first page with the title 'PyBBIO Test':
  home = Page("PyBBIO Test")
  # Add some text to the page:
  home.add_text("This is a test of the BBIOServer library for PyBBIO."+\
                " Follow the links at the left to test the different pages.")                 
  # Create a new page to test the text input:
  text = Page("Text Input")
  text.add_text("Press submit to send the text in entry box:")

  # Create the text entry box on a new line; button will say 'Submit',
  # and when submitted the text in the box will be sent to print_entry():
  text.add_entry(lambda text: print_entry(text), "Submit", newline=True)

  # Create a new page to test the buttons and monitors:
  io = Page("I/O")
 
  # Make a LED control section using a heading:
  io.add_heading("LED Control")
  io.add_text("Control the on-board LEDs", newline=True)

  # Add a button on a new line with the label 'Toggle USR2 LED' that will
  # call 'toggle(USR2)' when pressed:
  io.add_button(lambda: toggle(USR2), "Toggle USR2 LED", newline=True)

  # Add a monitor which will continually call 'pinState(USR2)' and 
  # display the return value in the form: 'current state: [value]':
  io.add_monitor(lambda: pinState(USR2), "current state:")

  # Same thing here with the other LED:
  io.add_button(lambda: toggle(USR3), "Toggle USR3 LED", newline=True)
  io.add_monitor(lambda: pinState(USR3), "current state:")

  # Create another section for ADC readings:
  io.add_heading("ADC Readings")
  io.add_text("Read some ADC inputs", newline=True)

  # Add a monitor to display the ADC value:
  io.add_monitor(lambda: analogRead(AIN0), "AIN0 value:", newline=True)

  # And one on the same line to display the voltage using the voltage()
  # function defined above. Because the units variable is used this time
  # the value will be displayed in the form: 'voltage: [value] v':
  io.add_monitor(lambda: voltage(AIN0), "voltage:", units="v")

  # Same thing here:
  io.add_monitor(lambda: analogRead(AIN1), "AIN1 value:", newline=True)
  io.add_monitor(lambda: voltage(AIN1), "voltage:", units="v")

  # Then start the server, passing it all the pages. The first page
  # passed in will be the home page:
  server.start(home, text, io)


def loop():
  # We're running in blocking mode, so we won't get here until ctrl-c
  # is preseed. 
  print "\nServer has stopped"
  stop()



# Then run it the usual way:
run(setup, loop)

# Now, on a computer on the same network as you beaglebone, open your
# browser and navigate to:
#  your_beaglebone_ip:8000 
#  (replacing 8000 if you specified a different port)
# You should be redirected to your_beaglebone_ip:8000/pages/PyBBIOTest.html

########NEW FILE########
__FILENAME__ = blink
# blink.py - Alexander Hiam - 2/2012
# Blinks two of the Beagleboard's on-board LEDs until CTRL-C is pressed.
#
# This example is in the public domain

# Import PyBBIO library:
from bbio import *

# Create a setup function:
def setup():
  # Set the two LEDs as outputs: 
  pinMode(USR2, OUTPUT)
  pinMode(USR3, OUTPUT)

  # Start one high and one low:
  digitalWrite(USR2, HIGH)
  digitalWrite(USR3, LOW)

# Create a main function:
def loop():
  # Toggle the two LEDs and sleep a few seconds:
  toggle(USR2)
  toggle(USR3)
  delay(500)

# Start the loop:
run(setup, loop)

########NEW FILE########
__FILENAME__ = charLCD
"""
PyBBIO HD44780 Example
Created: 9/2012
Author: Alexander Besser - netidx@gmail.com
Based on: PyBBIO library and satellite code by Alexander Hiam - ahiam@marlboro.edu

 A Python example for hardware IO support of HD44780 displays on the TI Beaglebone.
 Connections for example code:
 Pins on Expansion Header P8, LCD used in 4 BIT mode. 
 BB  LCD
  
 12 - RS
 14 - CLK
 16 - D4
 18 - D5
 20 - D6
 22 - D7
 
 LCD VSS - LCD RW (We not going to be reading anything from HD44780)
 
 I have 5V LCD with 3.3V signal lines, so word of caution,
 make sure your LCD doesn't have 5V feedback to Beaglebone, 
 or you WILL fry something, better yet all around 3.3V LCD.
 Code has a bug, I have yet to find, that crashes it after ~4-5 hours.
 most likely overflowing clock buffer, but I have no time to poke around.
 EDIT: 3/25/2013
 Reason for crash has been located, culprit was in fact integer overflow.
 Replaced faulty code with OS Built-in uptime counter.
 
 Copyright 2012-2013 Alexander Besser

 Licensed under the Apache License, Version 2.0 (the "License")
 you may not use this file except in compliance with the License.
 You may obtain a copy of the License at

 http://www.apache.org/licenses/LICENSE-2.0

 Unless required by applicable law or agreed to in writing, software
 distributed under the License is distributed on an "AS IS" BASIS,
 WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 See the License for the specific language governing permissions and
 limitations under the License.
"""

from bbio import *
import time
import datetime

import os
import sys

# To properly clock LCD I had to use exotic microsecond range sleep function
usleep = lambda x: time.sleep(x/100000.0) # Can go higher, but will eat up whole CPU on that. 
# IOMAP = [RS, CLK(E), B7, B6, B5, B4]
iomap = [GPIO1_12, GPIO0_26, GPIO1_5, GPIO1_31, GPIO2_1, GPIO1_14]

ticks = time.time()
i = 0

# LCD instruction mode
# For some reason my LCD takes longer to ACK that mode, hence longer delays. 
def lcdcommand( str ):
  digitalWrite(iomap[1], 1)
  usleep(500)
  digitalWrite(iomap[0], 0)
  iteration = 0
  for idr in str:
      digitalWrite(iomap[iteration+2], int(idr))
      iteration = iteration + 1
      if iteration == 4:
        iteration = 0
        usleep(100)
        digitalWrite(iomap[1], LOW)
        usleep(100)
        digitalWrite(iomap[1], HIGH)
        usleep(500)
  return

# LCD Data mode
def lcdprint( str ):
  for char in str:
    # Binary character value
    bitmap = bin(ord(char))[2:].zfill(8)
    digitalWrite(iomap[1], 1)
    usleep(20)
    digitalWrite(iomap[0], 1)
    iteration = 0
    for idr in bitmap:
      digitalWrite(iomap[iteration+2], int(idr))
      iteration = iteration + 1
      if iteration == 4:
        iteration = 0
        usleep(20)
        digitalWrite(iomap[1], LOW)
        usleep(20)
        digitalWrite(iomap[1], HIGH)
        usleep(20)
  return

  # Create a setup function:
def setup():

  sys.stdout.write("Python HD44780 LCD Driver REV 2")
  sys.stdout.write('\n')

  # Set BITMAP of outputs: 
  pinMode(iomap[1], OUTPUT)
  pinMode(iomap[0], OUTPUT)
  
  pinMode(iomap[2], OUTPUT)
  pinMode(iomap[3], OUTPUT)
  pinMode(iomap[4], OUTPUT)
  pinMode(iomap[5], OUTPUT)

  sys.stdout.write("Setting Up Screen")
  sys.stdout.write('\n')

  # lcdcommand('00000001')
  
  lcdcommand('0011') # \
  lcdcommand('0011') # | Initialization Sequence
  lcdcommand('0011') # /
  lcdcommand('0010') # 4BIT Mode
  
  # lcdcommand('00001111')
  
  lcdcommand('00000001') # Reset
  lcdcommand('00001100') # Dispaly On
  
  #lcdcommand('11000000') # Shift to 2nd Line
  # Shift Reference
  #10000000  Moves cursor to first address on the left of LINE 1
  #11000000  Moves cursor to first address on the left of LINE 2
  #10010100  Moves cursor to first address on the left of LINE 3
  #11010100  Moves cursor to first address on the left of LINE 4
    
  sys.stdout.write("Transferring LCD Control to main loop")
  sys.stdout.write('\n')
  
  sys.stdout.write("Process PID: ")
  sys.stdout.write(str(os.getpid()))
  sys.stdout.write('\n')
    
# Create a main function:
def loop():

  with open('/proc/uptime', 'r') as f:
    uptime_seconds = float(f.readline().split()[0])
    uptime_string = str(datetime.timedelta(seconds = uptime_seconds))

    
  pid = str(os.getpid())

  ticker1 = str(datetime.timedelta(seconds=round(time.time() - ticks, 0)))
  ticker2 =  pid + " : " + str(round(time.time() - ticks, 3))
  # Debug Options
  #ticker1 = "    " + str(s)
  #ticker2 = "    " + str(datetime.timedelta(seconds=round(s, 0)))
  #ticker2 = "    " + str(datetime.timedelta(seconds=round(time.time() - ticks, 0)))

  
  #lcdprint(ticker1)
  lcdprint("B-Bone Uptime")
  lcdcommand('11000000')
  #lcdprint(ticker2)
  lcdprint(uptime_string)
  lcdcommand('10000000')
  usleep(10000)
  #usleep(100)

# exit()

# Start the loop:
run(setup, loop)

from datetime import timedelta

########NEW FILE########
__FILENAME__ = DACx311_test
"""
 DACx311.py 
 Alexander Hiam - 11/2012
 
 Example program for PyBBIO's DACx311 library to 
 output a triangle wave.

 This example program is in the public domain.
"""

from bbio import *
from DACx311 import *

# Set variables for the pins connected to the DAC:
data_pin = GPIO1_6  # P8.3
clk_pin  = GPIO1_7  # P8.4
sync_pin = GPIO1_2  # P8.5

# Create an instance of the DAC class:
dac = DAC7311(data_pin, clk_pin, sync_pin)

# Set a few global variables:
volts     = 0.0 # Initial voltage
increment = 0.1 # Ammount to increment volts by each time
pause     = 75  # ms to wait between each increment

def setup():
  # Nothing to do here, the DACx311 class sets pin modes
  pass

def loop():
  global volts, increment
  # Set voltage in volts and increment:
  dac.setVolts(volts)
  volts += increment

  # If at upper or lower limit, negate the incrememnt value:
  if((volts >= 3.3) or (volts <= 0)):
    # Notice here that it's still possible that volts is either
    # above 3.3 or below 0, and it won't be incremented again until
    # after the DAC is next set. That's OK though, because values
    # passed to the DACx311 class are checked and constrained to
    # within this range.
    increment = -increment

  # Wait a bit:
  delay(10)

# Run the program:
run(setup, loop)

########NEW FILE########
__FILENAME__ = digitalRead
# digitalRead.py - Alexander Hiam - 2/2012
# USR3 LED mirrors GPIO1_6 until CTRL-C is pressed.
#
# This example is in the public domain

# Import PyBBIO library:
from bbio import *

# Create a setup function:
def setup():
  # Set the GPIO pins:
  pinMode(USR3, OUTPUT)
  pinMode(GPIO1_6, INPUT)

# Create a main function:
def loop():
  state = digitalRead(GPIO1_6)
  digitalWrite(USR3, state)
  # It's good to put a bit of a delay in if possible
  # to keep the processor happy:
  delay(100)

# Start the loop:
run(setup, loop)

########NEW FILE########
__FILENAME__ = EventIO_test
#!/usr/bin/env python
"""
 EventIO_test.py 
 Alexander Hiam

 An example to demonstrate the use of the EventIO library
 for PyBBIO.

 Example circuit:
  -A switch from 3.3v (P9.3) to GPIO1_7 (P8.4) with a 10k pull-down
   resistor to GND (P9.2)
 
  -A switch from 3.3v to GPIO1_3 (P8.6) with a 10k pull-down resistor.

  -A voltage divider with two equal resistors around 10k between 3.3v
   and GND to make about 1.6v   

  -A potentiometer with the two outer pins connected to the 1.6v output
   of the voltage divider and GND, and the center wiper pin connected to
   AIN0 (P9.39).

 This example program is in the public domain.
"""

# First we import PyBBIO: 
from bbio import *
# Then we can import EventIO:
from EventIO import *

sw1 = GPIO1_7
sw2 = GPIO1_3
pot = AIN0

# Create an event loop:
event_loop = EventLoop()

#--- The events to be triggered: ---
def event1():
  toggle(USR1)
  return EVENT_CONTINUE

def event2():
  toggle(USR2)
  return EVENT_CONTINUE

def event3():
  digitalWrite(USR3, HIGH)
  return EVENT_CONTINUE

def event4():
  digitalWrite(USR3, LOW)
  return EVENT_CONTINUE
#-----------------------------------

def setup():
  # This sets sw1 to trigger event1 when pressed with a debounce
  # time of 50ms:
  event_loop.add_event(DigitalTrigger(sw1, HIGH, event1, 50))

  # This sets sw2 to trigger event2 when pressed with a debounce
  # time of 270ms:
  event_loop.add_event(DigitalTrigger(sw2, HIGH, event2, 270))

  # This sets event3 to be called when the value on pot is above
  # 1820: 
  event_loop.add_event(AnalogLevel(pot, 1820, event3))

  # This sets event3 to be called when the value on pot is below
  # 1820: 
  event_loop.add_event(AnalogLevel(pot, 1820, event4, direction=-1))

  # Then start the event loop:
  event_loop.start()

def loop():
  # Because the event loop is run as a seperate process, this will
  # be executed normally.
  print "Time running: %ims" % int(millis())
  delay(3000)

run(setup, loop)
# As soon as ctrl-c is pressed the event loop process will be 
# automatically termintated and the program wil exit happily.

########NEW FILE########
__FILENAME__ = fade
# fade.py - Alexander Hiam - 10/2012
# Uses pulse width modulation to fade an LED on PWM1A 
# (pin 14 on header P9). 
#
# This example is in the public domain

# Import PyBBIO library:
from bbio import *

LED = PWM2B 
brightness = 0  # Global variable to store brightness level
inc = 1         # How much to increment the brightness by
pause = 10      # Delay in ms between each step 

# Create a setup function:
def setup():
  # nothing to do here
  pass

# Create a main function:
def loop():
  global brightness, inc

  # Set the PWM duty cycle:
  analogWrite(LED, brightness)
  # Increment value:
  brightness += inc
  if ((brightness == 255) or (brightness == 0)):
    # Change increment direction:
    inc *= -1
  # Sleep a bit:
  delay(pause)

# Start the loop:
run(setup, loop)

########NEW FILE########
__FILENAME__ = interrupt
# interrupt.py - Alexander Hiam - 12/2013
# Sets P9.12 as an input with a pull-up resistor and attaches a 
# falling edge interrupt. The 5th time the pin goes low the interrupt
# is detached.
#
# This example is in the public domain

from bbio import *

pin = GPIO1_28 

n_interrupts = 0

def countInterrupts():
  # This function will be called every time the pin goes low
  global n_interrupts
  n_interrupts += 1
  print "interrupt # %i" % n_interrupts
  if n_interrupts >= 5:
    print "detaching interrupt"
    detachInterrupt(pin)
    
def setup():
  pinMode(pin, INPUT, PULLUP)
  attachInterrupt(pin, countInterrupts, FALLING)
  print "falling edge interrupt attached to P9.12 (GPIO1_28)"
  
def loop():
  print "The loop continues..."
  delay(1000)
  
run(setup, loop)
########NEW FILE########
__FILENAME__ = knock
"""
 knock.py - Alexander Hiam - 3/21/2012
 Adapted from the Ardiuno knock.pde example skecth for use
 with PyBBIO - https://github.com/alexanderhiam/PyBBIO

 Uses a Piezo element to detect knocks. If a knock is detected
 above the defined threshold one of the on-board LEDs is toggled
 and 'knock' is written to stdout.

 This is based quite directly on the Knock Sensor example 
 sketch, which can be found in the Arduino IDE examples or 
 here:
   http://www.arduino.cc/en/Tutorial/Knock

 Version history of knock.pde:   
   created 25 Mar 2007
   by David Cuartielles <http://www.0j0.org>
   modified 4 Sep 2010
   by Tom Igoe

 This example is in the public domain.
"""

from bbio import *

LED = USR3        # On-board LED
KNOCK_SENSOR = A0 # AIN0 - pin 39 on header P9
THRESHOLD = 245   # analogRead() value > THRESHOLD indicates knock


def setup():
  pinMode(LED, OUTPUT)  
  print "PyBBIO Knock Sensor"

def loop():
  value = analogRead(KNOCK_SENSOR)
  #print value
  if (value > THRESHOLD):
    toggle(LED)
    print "knock!"
  delay(100)
run(setup, loop)

########NEW FILE########
__FILENAME__ = MAX31855_test
"""
 MAX31855_test.py 
 Alexander Hiam - 12/2012
 
 Example program for PyBBIO's MAX31855 library.
 Reads the temerature from the MAX31855 thermocouple
 amplifier using software SPI.
 
 This example program is in the public domain.
"""

from bbio import *
from MAX31855 import *

# Set variables for the pins connected to the ADC:
data_pin = GPIO1_15  # P8.15
clk_pin  = GPIO1_14  # P8.16
cs_pin   = GPIO0_27  # P8.17

# Create an instance of the MAX31855 class:
thermocouple = MAX31855(data_pin, clk_pin, cs_pin)

def setup():
  # Nothing to do here, the MAX31855 class sets pin modes
  pass

def loop():
  temp = thermocouple.readTempC()
  if (not temp):
    # The MAX31855 reported an error, print it:
    print thermocouple.error
  else:
    print "Temp: %0.2f C" % temp;
  delay(1000)

run(setup, loop)

########NEW FILE########
__FILENAME__ = SafeProcess_test
#!/usr/bin/env python
"""
 SafeProcess_test.py 
 Alexander Hiam

 An example to demonstrate the use of the SafeProcess library
 for PyBBIO.

 This example program is in the public domain.
"""

from bbio import *
from SafeProcess import *

def foo():
  while(True):
    print "foo"
    delay(1000)

def setup():
  p = SafeProcess(target=foo)
  p.start()

def loop():
  print "loop"
  delay(500)

run(setup, loop)

########NEW FILE########
__FILENAME__ = serial_echo
# serial_echo.py - Alexander Hiam - 4/15/12
# 
# Prints all incoming data on Serial2 and echos it back.
# 
# Serial2 TX = pin 21 on P9 header
# Serial2 RX = pin 22 on P9 header
# 
# This example is in the public domain

from bbio import *

def setup():
  # Start Serial2 at 9600 baud:
  Serial2.begin(9600)


def loop():
  if (Serial2.available()):
    # There's incoming data
    data = ''
    while(Serial2.available()):
      # If multiple characters are being sent we want to catch
      # them all, so add received byte to our data string and 
      # delay a little to give the next byte time to arrive:
      data += Serial2.read()
      delay(5)

    # Print what was sent:
    print "Data received:\n  '%s'" % data
    # And write it back to the serial port:
    Serial2.write(data)
  # And a little delay to keep the Beaglebone happy:
  delay(200)

run(setup, loop)

########NEW FILE########
__FILENAME__ = serial_server
# serial_server.py - Alexander Hiam - 4/15/12
# 
# Creates a simple web interface to the Serial2 port.
#
# Serial2 TX = pin 21 on P9 header
# Serial2 RX = pin 22 on P9 header
#
# Run this program and navigate to http://your_beaglebone_ip:8000
# in your web brower.
#
# See BBIOServer tutorial:
#  https://github.com/alexanderhiam/PyBBIO/wiki/BBIOServer
#
# This example is in the public domain

from bbio import *
from BBIOServer import *

# Create a server instance:
server = BBIOServer()

# A global buffer for received data:
data =''

def serial_tx(string):
  """ Sends given string to Serial2. """
  Serial2.println(string)

def serial_rx():
  """ Returns received data if any, otherwise current data buffer. """
  global data
  if (Serial2.available()):
    # There's incoming data
    data =''
    while(Serial2.available()):
      # If multiple characters are being sent we want to catch
      # them all, so add received byte to our data string and 
      # delay a little to give the next byte time to arrive:
      data += Serial2.read()
      delay(5) 
  return data

def setup():
  # Start the serial port at 9600 baud:
  Serial2.begin(9600)
  # Create the web page:
  serial = Page("Serial")
  serial.add_text("A simple interface to Serial2.")
  serial.add_entry(lambda string: serial_tx(string), "Send", newline=True)
  serial.add_monitor(lambda: serial_rx(), "Received:", newline=True)

  # Start the server:
  server.start(serial)

def loop():
  # Server has stopped; exit happily:
  stop()

run(setup, loop)

########NEW FILE########
__FILENAME__ = Servo_sweep
#!/usr/bin/env python
"""
 Servo_sweep.py
 Alexander Hiam - 11/7/12

 An example use of PyBBIO's Servo library to sweep the angle 
 of a servo motor back and forth between 0 and 180 degrees.

 Based on Arduino's Servo library example:
  http://arduino.cc/en/Tutorial/Sweep

 Connect the servo's power wires to 5V (P9.8) and ground (P9.2),
 and the signal wire to PWM1A (P9.14). 


 This example is in the public domain.
"""

# First we must import PyBBIO: 
from bbio import *
# Then we can import Servo:
from Servo import *

# Create an instance of the Servo object:
servo1 = Servo(PWM1A)
# We could have left out the PWM pin here and used 
# Servo.attach(PWM1A) in setup() instead.

def setup():
  # Nothing to do here
  pass

def loop():
  for angle in range(180):  # 0-180 degrees
    servo1.write(angle)
    delay(15)

  for angle in range(180, 0, -1):  # 180-0 degrees
    servo1.write(angle)
    delay(15)

run(setup, loop)

########NEW FILE########
__FILENAME__ = switch
# switch.py - Alexander Hiam - 2/2012
#
# Uses a switch to toggle the state of two LEDs.
# Demonstrates the use of global variables in Python.
# 
# The circuit:
#  - Momentary switch between 3.3v and GPIO1_15
#  - 10k ohm resistor from GPIO1_15 to ground
#  - Green LED from GPIO1_17 through 330 ohm resistor to ground
#  - Red LED from GPIO3_21 through 330 ohm resistor to ground
#
# This example is in the public domain

# Import PyBBIO library:
from bbio import *

SWITCH  = GPIO1_15 # P8.15
LED_GRN = GPIO1_17 # P9.23
LED_RED = GPIO3_21 # P9.25

LED_STATE = 0 # 0=green LED lit, 1=red LED lit.
SW_STATE  = 0 # =1 when switch pressed; only change LED_STATE
              # once per press.

# Create a setup function:
def setup():
  # Set the switch as input:
  pinMode(SWITCH, INPUT)
  # Set the LEDs as outputs:
  pinMode(LED_GRN, OUTPUT)
  pinMode(LED_RED, OUTPUT)
  
# Create a main function:
def main(): 
  global LED_STATE, SW_STATE 
  # Python requires you explicitely declare all global variables 
  # that you want to change within a code block using the global
  # statement; see:
  #  http://docs.python.org/reference/simple_stmts.html#the-global-statement

  if (digitalRead(SWITCH) == HIGH):
    if (SW_STATE == 0):
      # Just pressed, not held down.
      # Set SW_STATE and toggle LED_STATE
      SW_STATE = 1 
      LED_STATE ^= 1
    # Otherwise switch is held down, don't do anything.
  else:
    # Switch not pressed, reset SW_STATE:
    SW_STATE = 0

  if (LED_STATE == 0):
    digitalWrite(LED_GRN, HIGH)
    digitalWrite(LED_RED, LOW)
  else:
    digitalWrite(LED_GRN, LOW)
    digitalWrite(LED_RED, HIGH)
  # It's good to put a bit of a delay in if possible
  # to keep the processor happy:
  delay(50)

# Start the loop:
run(setup, main)

########NEW FILE########
__FILENAME__ = ads786x
"""
 ADS786x - v0.1
 Copyright 2012 Alexander Hiam
 A library for interfacing with TI's ADS786x series
 analog-to-digital converters
"""

from bbio import *

class ADS786x(object):
  """ Base class for all each of ADS786x series classes. """
  def __init__(self, data_pin, clk_pin, cs_pin, vref=3.3):
    self._data = data_pin
    self._clk = clk_pin
    self._cs = cs_pin
    pinMode(self._data, INPUT)
    for i in (self._cs, self._clk): pinMode(i, OUTPUT)

    # Idle state for clock and cs (data doesn't matter):
    for i in (self._cs, self._clk): digitalWrite(i, HIGH)
    
    # Calculate volts per bit:
    self.dv = float(vref)/2**self.n_bits

  def read(self):
    """ Read and return the ADC value. """
    digitalWrite(self._cs, LOW)
    value = shiftIn(self._data, self._clk, MSBFIRST, n_bits=self.n_bits+3)
    digitalWrite(self._cs, HIGH)
    return value

  def readVolts(self):
    """ Sets the DAC output to the given voltage. """
    return self.read() * self.dv


class ADS7866(ADS786x):
  # Tested, working
  n_bits = 12

class ADS7867(ADS786x):
  # Untested
  n_bits = 10

class ADS7868(ADS786x):
  # Untested
  n_bits = 8

########NEW FILE########
__FILENAME__ = bbio_server
"""
 BBIOServer - v1.2
 Copyright 2012 Alexander Hiam
 A dynamic web interface library for PyBBIO.
"""

import os, sys, urlparse, traceback, threading
from SimpleHTTPServer import SimpleHTTPRequestHandler
from BaseHTTPServer import HTTPServer

from bbio import *

BBIOSERVER_VERSION = "1.2"

THIS_DIR = os.path.dirname(__file__)
PAGES_DIR = "%s/pages" % THIS_DIR
HEADER = "%s/src/header.html" % THIS_DIR
SIDEBAR = "%s/src/sidebar.html" % THIS_DIR
FOOTER = "%s/src/footer.html" % THIS_DIR
INDEX_TEMPLATE = "%s/src/index.html.template" % THIS_DIR
INDEX = "%s/index.html" % THIS_DIR

# Change working directory to the BBIOServer library directory,
# otherwise the request handler will try to deliver pages from the
# directory where the program using the library is being run from:
os.chdir(THIS_DIR)

# This is where we store the function strings indexed by their
# unique ids:
FUNCTIONS = {}


class BBIORequestHandler(SimpleHTTPRequestHandler):

  def do_GET(self):
    """ Overrides SimpleHTTPRequestHandler.do_GET() to handle
        PyBBIO function calls. """
    url = self.raw_requestline.split(' ')[1]
    if ('?' in url):
      # We've received a request for a PyBBIO function call,
      # parse out parameters:
      url = url.split('?')[1]
      params = urlparse.parse_qs(url)
      function_id = params['function_id'][0]
      
      function = FUNCTIONS.get(function_id)
      if (function):
        if ("entry_text" in params):
          # This is a request from a text entry, so we also need to
          # parse out the text to be passed to the function:
          text = params['entry_text'][0]
          if (text == " "):
            # An empty text box is converted into a space character
            # by the Javascript, because otherwise the parsed url
            # would not have an entry_text param and we'd get errors
            # trying to call the function; convert it back:
            text = "" 

          response = str(function(text))
        else:
          # The function takes no arguments, just call it.
          response = str(function())

      else:
        # The function id is not in the dictionary. This happens if
        # the server has restarted, which generates new function ids, 
        # and the page has not been refreshed.
        response = "*Refresh page*"

      # Send the HTTP headers:
      self.send_response(200)
      self.send_header('Content-Type', 'text/html')
      # Our length is simply the length of our function return value:
      self.send_header("Content-length", len(response))
      self.send_header('Server', 'PyBBIO Server')
      self.end_headers()

      # And finally we write the response:
      self.wfile.write(response)
      return

    # If we get here there's no function id in the request, which
    # means it's a normal page request; let SimpleHTTPRequestHandler
    # handle it the standard way:
    SimpleHTTPRequestHandler.do_GET(self)

  def address_string(self):
    host, port = self.client_address[:2]
    

class BBIOHTTPServer(HTTPServer):

  def handle_error(self, request, client_address):
    """ Overrides HTTPServer.handle_error(). """
    # Sometimes when refreshing or navigating away from pages with
    # monitor divs, a Broken pipe exception is thrown on the socket
    # level. By overriding handle_error() we are able to ignore these:
    error = traceback.format_exc()
    if ("Broken pipe" in error):
      return

    # Otherwise we want to print the error like normal, except that,
    # because BBIOServer redirects stderr by default, we want it to
    # print to stdout:
    traceback.print_exc(file=sys.stdout)
    print '-'*40
    print 'Exception happened during processing of request from',
    print client_address    
    print '-'*40


class RequestFilter():
  # This acts as a file object, but it doesn't print any messages
  # from the server.
  def write(self, err):
    if not (('GET' in err) or ('404' in err)):
      print err
  def flush(self):
    pass

class BBIOServer():
  def __init__(self, port=8000, verbose=False, blocking=True):
    self._server = BBIOHTTPServer(('',port), BBIORequestHandler)
    self.blocking = blocking
    if not(verbose):
      # A log of every request to the server is written to stderr.
      # This makes for a lot of printing when using the monitors. 
      # We can avoid this by redirecting stderr to a RequestFilter() 
      # instance:
      sys.stderr = RequestFilter()

  def start(self, *pages):
    """ Takes a list of Page instances, creates html files, and starts
        the server. """

    # Make sure at least one page has been given:
    if not(pages):
      print "*Can't start server - no pages provided."
      return

    # Make sure pages/ directory exists:
    if not(os.path.exists(PAGES_DIR)):
      os.system("mkdir %s" % PAGES_DIR)
    # Remove old pages if any:
    if (os.listdir(PAGES_DIR)):
      os.system("rm %s/*" % PAGES_DIR)
    
    # We treat the first page passed in as the home page and create
    # an index.html page in the base directory that redirects to it:
    home = pages[0]
    with open(INDEX, 'w') as index:
      with open(INDEX_TEMPLATE, 'r') as index_template:
        index.write(index_template.read() % home.filename)

    # Generate a list of links for the sidebar:
    links = ''
    for page in pages:
      links += '<li><a href="%s">%s</a></li>\n' % (page.filename, page.title)

    # Add sidebar to each page and write them to files:
    for page in pages:
      path =  "%s/%s" % (PAGES_DIR, page.filename)
      with open(path, 'w') as f:
        f.write(str(page) % links)

    # Start srver in a daemon thread:
    server_thread = threading.Thread(target=self._server.serve_forever)
    server_thread.daemon = True
    server_thread.start()
    
    if (self.blocking):
      try:
        while(True): delay(10000)
      except KeyboardInterrupt:
        pass

  def stop(self):
    raise KeyboardInterrupt

class Page(object):
  def __init__(self, title, stylesheet="style.css"):
    self.title = title
    # Convert the title to a valid .html filename:
    not_allowed = " \"';:,.<>/\|?!@#$%^&*()+="
    self.filename = ''
    for c in title: 
      self.filename += '' if c in not_allowed else c
    self.filename += ".html" 
   
    # The header template has three string formatting operators:
    # the document and page titles, and the sidebar. The sidebar
    # template has one formatting operator where the list of links
    # goes. When we insert the two titles and the sidebar content
    # into the header template, we end up with the one formatting
    # operator from the sidebar template. This way the BBIOServer
    # will be able to insert the links even though the pages are 
    # all created separately:
    self.html = open(HEADER, 'r').read() % \
                (title, stylesheet, title, open(SIDEBAR, 'r').read())

  def add_heading(self, text):
    """ Add a heading to the current position in the page. """
    self.html += '<div class="heading">%s</div>\n' % (text)

  def add_text(self, text, newline=False):
    """ Add text to the current position in the page. If newline=True
        the text will be put on a new line, otherwise it will be stacked
        on the current line. """
    style = "clear: left;" if newline else ''
    self.html += '<div class="text" style="%s">%s</div>\n' %\
                 (style, text)

  def add_button(self, function, label, newline=False):
    """ Add a button to the current position in the page with the given
        label, which will execute the given lambda function, e.g.:
        'lambda: digitalWrite(USR3)'. If newline=True the text will be put
        on a new line, otherwise it will be stacked on the current line. """
    # Use system time to create a unique id for the given function.
    # This is used as a lookup value in the FUNCTION_STRINGS dictionary.
    function_id = str(int(time.time()*1e6) & 0xffff)
    FUNCTIONS[function_id] = function

    style = "clear: left;" if newline else ''

    # Add the HTML. Set the button to call the javascript function 
    # which communicates with the request handler, passing it the
    # function id and a string to indicate that it is a button:
    self.html +=\
      '<div class="object-wrapper" style="%s">\n' % (style) +\
      '<div class="button" onclick="call_function(%s, \'button\')">%s\n' %\
        (function_id, label) +\
     '</div>\n</div>\n'

  def add_entry(self, function, submit_label, newline=False):
    """ Add a text entry box and a submit button with the given label to the 
        current position in the page. When submitted, the given function will
        be called, passing it the text currently in the entry. The function 
        must take take a value, e.g.: 'lambda s: print s'. If newline=True 
        the text will be put on a new line, otherwise it will be stacked on
        the current line. """

    # Create the unique id and store the function:
    function_id = str(int(time.time()*1e6) & 0xffff)
    FUNCTIONS[function_id] = function

    style = "clear: left;" if newline else ''

    # Add the HTML. Pass the Javascript function the function id,
    # as well as a string to indicate it's an entry. This way the
    # Javascript function will know to extract the text from the 
    # entry and pass it as part of its request. 
    self.html +=\
      '<div class="object-wrapper" style="%s">\n' % (style) +\
      '<input class="entry" id="%s" type="text" name="entry" />\n' %\
      (function_id) +\
      '<div class="button" onclick="call_function(%s, \'entry\')">%s\n' % \
      (function_id, submit_label) +\
     '</div>\n</div>\n'

  def add_monitor(self, function, label, units='', newline=False):
    """ Add a monitor to the current position in the page. It will be
        displayed in the format: 'label' 'value' 'units', where value is 
        the most recent return value of the given function; will be 
        updated every 200 ms or so. If newline=True the text will be put
        on a new line, otherwise it will be stacked on the current line. """
    
    # Create the unique id and store the function:
    function_id = str(int(time.time()*1e6) & 0xffff)
    FUNCTIONS[function_id] = function

    style = "clear: left;" if newline else ''

    # Add the HTML. Set the monitor id as the function id. When
    # the page loads a Javascript function is called which continually
    # loops throught each monitor, extracts the id, passes it to the
    # server, then sets the text in the monitor div to the return
    # value.
    self.html +=\
      '<div class="object-wrapper" style="%s">\n' % (style) +\
      '<div class="value-field">%s</div>\n' % (label) +\
      '<div class="monitor-field" id="%s"></div>\n' % (function_id) +\
      '<div class="value-field">%s</div>\n' % (units) +\
      '</div>\n'

  def __str__(self):
    # Return the HTML with the content of the footer template
    # appended to it: 
    return self.html + open(FOOTER, 'r').read() % (BBIOSERVER_VERSION)

########NEW FILE########
__FILENAME__ = dacx311
"""
 DACx311 - v0.1
 Copyright 2012 Alexander Hiam
 A library for interfacing with TI's DACx311 series
 digital-to-analog converters
"""

from bbio import *

class DACx311(object):
  """ Base class for all each of DACx311 series classes. """
  def __init__(self, data_pin, clk_pin, sync_pin, vref=3.3):
    self._data = data_pin
    self._clk = clk_pin
    self._sync = sync_pin
    for i in (self._data, self._sync, self._clk): pinMode(i, OUTPUT)

    # Idle state for clock and sync (data doesn't matter):
    for i in (self._sync, self._clk): digitalWrite(i, HIGH)
    
    self.max_value = 2**self.n_bits - 1
    # Calculate volts per bit:
    self.dv = float(vref)/2**self.n_bits

  def set(self, value):
    """ Set the DAC control register to the given value. """
    if (value > self.max_value): value = self.max_value
    if (value < 0): value = 0
    value <<= self.bit_shift
    digitalWrite(self._sync, LOW)

    shiftOut(self._data, self._clk, MSBFIRST, (value>>8), FALLING)
    shiftOut(self._data, self._clk, MSBFIRST, value & 0xff, FALLING)

    digitalWrite(self._sync, HIGH)

  def setVolts(self, volts):
    """ Sets the DAC output to the given voltage. """
    value = int(volts/self.dv)
    self.set(value)


class DAC5311(DACx311):
  # Untested 
  n_bits = 8
  bit_shift = 6

class DAC6311(DACx311):
  # Untested
  n_bits = 10
  bit_shift = 4

class DAC7311(DACx311):
  # Tested working
  n_bits = 12
  bit_shift = 2

class DAC8311(DACx311):
  # Untested
  n_bits = 14
  bit_shift = 0

########NEW FILE########
__FILENAME__ = eventio
"""
 EventIO - v0.2
 Copyright 2012 - Alexander Hiam <ahiam@marlboro.edu>
 Apache 2.0 license

 Basic multi-process event-driven programming for PyBBIO.
"""

from bbio import *
from SafeProcess import *
import time
from collections import deque
from multiprocessing import Process

# Return value of an event function to put it back into the event loop:
EVENT_CONTINUE = True

class EventLoop(SafeProcess):

  def config(self):
    # deque is better optimized for applications like FIFO queues than 
    # lists are:
    self.events = deque()

  def add_event(self, event):
    """ Adds given Event instance to the queue. """
    self.events.append(event)

  def run(self):
    """ Starts the event loop. Once started, no new events can be added. """
    try:
      while(True):
        event = self.events.popleft()
        if (event.run() == EVENT_CONTINUE):
          self.events.append(event)
        delay(0.1)
    except IndexError:
      # Queue is empty; end loop.
      pass


# This is the most basic event class. Takes two functions; when 'trigger'
# returns True 'event' is called. If 'event' returns EVENT_CONTINUE the event
# is put back in the event loop. Otherwise it will only be triggered once.
class Event(object):
  def __init__(self, trigger, event):
    # The trigger function must return something that will evaluate to True
    # to trigger the event function.
    self.trigger = trigger
    self.event = event

  def run(self):
    if self.trigger():
      # The event loop needs the return value of the event function so it can 
      # signal whether or not to re-add it:
      return self.event()
    # Otherwise re-add it to keep checking the trigger:
    return EVENT_CONTINUE


# This is the same as the basic Event class with the addition of debouncing;
# if an event is triggered and re-added to an event loop, the trigger will be 
# ignored for the given number of milliseconds.
class DebouncedEvent(object):
  def __init__(self, trigger, event, debounce_ms):
    self.trigger = trigger
    self.event = event
    self.debounce_ms = debounce_ms
    self.debouncing = False
    self.last_trigger = 0
  
  def run(self):
    if (self.debouncing):
      if (time.time()*1000-self.last_trigger <= self.debounce_ms):
        return EVENT_CONTINUE
      self.debouncing = False
    if self.trigger():
      self.last_trigger = time.time()*1000
      self.debouncing = True
      return self.event()
    return EVENT_CONTINUE


# This event will be triggered after the given number of milliseconds has
# elapsed. If the event function returns EVENT_CONTINUE the timer will 
# restart.
class TimedEvent(Event):
  def __init__(self, event, event_time_ms):
    self.event = event
    self.event_time_ms = event_time_ms
    self.start_time = millis()

  def trigger(self):
    if (millis() - self.start_time >= self.event_time_ms):
      self.start_time = millis()
      return True
    return False


# This event is based on the debounced event and compares the state of a given
# digital pin to the trigger state and calls the event function if they're the 
# same. Sets the pin to an input when created.
class DigitalTrigger(DebouncedEvent):
  def __init__(self, digital_pin, trigger_state, event, debounce_ms, pull=0):
    pinMode(digital_pin, INPUT, pull)
    trigger = lambda: digitalRead(digital_pin) == trigger_state
    super(DigitalTrigger, self).__init__(trigger, event, debounce_ms)


# This Event compares the value on the given analog pin to the trigger level
# and calls the event function if direction=1 and the value is above, or if 
# direction=-1 and the value is below. Either looks at a single reading or a 
# running average of size n_points.
class AnalogLevel(Event):
  def __init__(self, analog_pin, threshold, event, direction=1, n_points=4):
    self.analog_pin = analog_pin
    self.threshold = threshold
    self.event = event
    if (n_points < 1): n_points = 1
    # Construct the window regardless of n_points; will only be used if
    # n_points > 1:
    window = [0 if direction > 0 else 2**12 for i in range(n_points)]
    self.window = deque(window)
    self.direction = direction
    self.n_points = n_points

  def trigger(self): 
    if (self.n_points > 1):
      self.window.popleft()
      self.window.append(analogRead(self.analog_pin))
      val = sum(self.window)/self.n_points
    else: 
      val = analogRead(self.analog_pin)
    if (self.direction > 0): 
      return True if val > self.threshold else False
    return True if val < self.threshold else False

########NEW FILE########
__FILENAME__ = example
# This is just an example to demonstrate libraries directory
# scheme for PyBBIO. 
# To test:
#   run PyBBIO/tests/library_test.py


def foo():
  print "Hello, world!"



########NEW FILE########
__FILENAME__ = max31855
"""
 MAX31855 - v0.2
 Copyright 2012 Alexander Hiam
 A library for PyBBIO to interface with Maxim's MAX31855 
 thermocouple amplifier.
"""

from bbio import *


class MAX31855(object):
  def __init__(self, data_pin, clk_pin, cs_pin, offset=0):
    self._data = data_pin
    self._clk = clk_pin
    self._cs = cs_pin
    self.offset = offset
    pinMode(self._data, INPUT)
    for i in (self._cs, self._clk): pinMode(i, OUTPUT)
    self.error = None

    # Idle state for clock and cs (data doesn't matter):
    for i in (self._cs, self._clk): digitalWrite(i, HIGH)

  def readTempF(self):
    """ Reads temperature, converts to Fahrenheit and returns, or 
        returns None if error detected. """
    temp = self.readTempC() 
    return temp if not temp else temp * 9.0/5.0 + 32

  def readTempC(self):
    """ Reads and returns the temperature in Celsius, or returns None
        if error detected. """
    value = self.read()
    if not value: return None
    # Extract 14-bit signed temperature value:
    temp = (value >> 18) & 0x3fff
    sign = temp & (1<<14)
    if sign: temp = -(~temp+1 & 0x1fff)
    return temp*0.25 + self.offset
    
  def readTempInternal(self):
    """ Reads and returns the MAX31855 reference junction temperature 
        in Celsius, or returns None if error detected. """
    value = self.read()
    if not value: return None
    # Extract 12-bit signed temperature value:
    temp = (value >> 4) & 0xfff
    sign = temp & (1<<12)
    if sign: temp = -(~temp+1 & 0x7ff)
    return temp*0.0625

  def read(self):
    """ Receives and returns full 32-bit map from MAX31855, or sets
        self.error and returns None if fault detected. """
    self.error = None
    digitalWrite(self._cs, LOW)
    value = shiftIn(self._data, self._clk, MSBFIRST, n_bits=32)
    digitalWrite(self._cs, HIGH)

    if (value & (1<<16)):
      # Fault detected, check error bits:
      if (value & (1<<2)):
        self.error = "*Thermocouple shorted to Vcc*"
      elif (value & (1<<1)):
        self.error = "*Thermocouple shorted to GND*"
      else:
        self.error = "*Thermocouple not connected*"
      return None

    return value

########NEW FILE########
__FILENAME__ = safe_process
"""
 SafeProcess - v0.1
 Copyright 2012 - Alexander Hiam <ahiam@marlboro.edu>
 Apache 2.0 license

 Provides a wrapper for Python's mutliprocessing.Process class
 which will be terminated during PyBBIO's cleanup.
"""

from multiprocessing import Process 
from bbio import *


class SafeProcess(Process):
  def __init__(self, group=None, target=None, name=None, args=(), kwargs={}):

    # This is the magic line: 
    addToCleanup(lambda: self.terminate())
    # This way the process will be terminated as part of PyBBIO's 
    # cleanup routine.

    self.config()
    Process.__init__(self, group=group, target=target, name=name, 
                     args=args, kwargs=kwargs)

  def config(self):
    """ This function may be overriden by an inheriting class to handle any
        initialization that does not require any arguments be passed in. """
    pass

########NEW FILE########
__FILENAME__ = Servo
"""
 Servo - v0.1
 Copyright 2012 Alexander Hiam

 Library for controlling servo motors with the BeagleBone's PWM pins.
"""

from bbio import *

class Servo(object):
  def __init__(self, pwm_pin=None, pwm_freq=50, min_ms=0.5, max_ms=2.4):
    assert (pwm_freq > 0), "pwm_freq must be positive, given: %s" %\
                          str(pwm_freq)    
    assert (min_ms > 0), "0 min_ms must be positive, given: %s" %\
                          str(min_ms)
    assert (max_ms > 0), "max_ms must be positive, given: %s" %\
                          str(max_ms)
    self.pwm_freq = pwm_freq
    self.min_ms = min_ms
    self.max_ms = max_ms
    self.pwm_pin = None
    if (pwm_pin): self.attach(pwm_pin)
    self.angle = None

  def attach(self, pwm_pin):
    """ Attach servo to PWM pin; alternative to passing PWM pin to
        __init__(). Can also be used to change pins. """
    if (self.pwm_pin):
      # Already attached to a pin, detach first
      self.detach()
    self.pwm_pin = pwm_pin

    pwmFrequency(self.pwm_pin, self.pwm_freq)
    self.period_ms = 1000.0/self.pwm_freq

  def write(self, angle):
    """ Set the angle ofthe servo in degrees. """
    if (angle < 0): angle = 0
    if(angle > 180): angle = 180
    value = (self.max_ms-self.min_ms)/180.0 * angle + self.min_ms
    analogWrite(self.pwm_pin, value, self.period_ms)
    self.angle= angle

  def read(self):
    """ return the current angle of the servo, or None if it has not
        yet been set. """
    return self.angle

  def detach(self):
    """ Detaches the servo so so pin can be used for normal PWM 
        operation. """
    if (not self.pwm_pin): return
    pwmDisable(self.pwm_pin)
    self.pwm_pin = None
    self.angle = None

########NEW FILE########
__FILENAME__ = io_test
# io_test.py - Alexander Hiam 
# This was a quick test I wrote before starting in on PyBBIO.
# It's a good demonstration of how to use /dev/mem for hardware
# access. Blinks the on-board LED marked USR2

from mmap import mmap
import time, struct

GPIO1_offset = 0x4804c000  # Start of GPIO1 mux
GPIO1_size = 0x4804cfff-GPIO1_offset
GPIO_OE = 0x134
GPIO_SETDATAOUT = 0x194
GPIO_CLEARDATAOUT = 0x190
LED2 = 1<<22 # Pin 22 in gpio registers

f = open("/dev/mem", "r+b" )
map = mmap(f.fileno(), GPIO1_size, offset=GPIO1_offset) 
f.close() # Only needed to make map

# Grab the entire GPIO_OE register: 
packed_reg = map[GPIO_OE:GPIO_OE+4] # This is a packed string
# Unpack it:
reg_status = struct.unpack("<L", packed_reg)[0]
# Set LED1 bit low for output without effecting anything else:
reg_status &= ~(LED2)
# Repack and set register:
map[GPIO_OE:GPIO_OE+4] = struct.pack("<L", reg_status)

# blink 10 times:
for i in xrange(5):
  # Set it high:
  map[GPIO_SETDATAOUT:GPIO_SETDATAOUT+4] = struct.pack("<L", LED2)
  time.sleep(0.5) # Wait half a second
  # Set it low:
  map[GPIO_CLEARDATAOUT:GPIO_CLEARDATAOUT+4] = struct.pack("<L", LED2)
  time.sleep(0.5)

########NEW FILE########
__FILENAME__ = library_test
# A quick test to demonstrate the libraries directory scheme.
# 
# imports and tests PyBBIO/libraries/example.py

try:
  import example
except:
  print "\nWe can't import the PyBBIO library until we've imported bbio"

print "Importing bbio"
from bbio import *

print "now we can import example"
import example

print "testing example library:"
example.foo()

########NEW FILE########
__FILENAME__ = sleep_test
#!/usr/bin/env python
"""
 sleep_test.py - Alexander Hiam - 3/2012

 Testing the accuracy of different methods of sleeping
 in units of microseconds and milliseconds. Uses Python's
 time.sleep(), as well as usleep() and nanosleep() from libc
 using ctypes.

 This was written for testing delay methods for the Beaglebone,
 which did not have python ctypes installed by default for me.
 Install on the Beaglebone with:
   # opkg update && opkg install python-ctypes 
"""

import ctypes, time

#--- Microsecond delay functions: ---

# Load libc shared library:
libc = ctypes.CDLL('libc.so.6')


def sleepMicroseconds(us):
  """ Delay microseconds using time.sleep(). """
  time.sleep(us * 1e-6)

def delayMicroseconds(us):
  """ Delay microseconds with libc usleep() using ctypes. """
  libc.usleep(int(us))


class Timespec(ctypes.Structure):
  """ timespec struct for nanosleep, see:
      http://linux.die.net/man/2/nanosleep """
  _fields_ = [('tv_sec', ctypes.c_long), 
              ('tv_nsec', ctypes.c_long)]

libc.nanosleep.argtypes = [ctypes.POINTER(Timespec), 
                           ctypes.POINTER(Timespec)]
nanosleep_req = Timespec()
nanosleep_rem = Timespec()

def nanosleepMicroseconds(us):
  """ Delay microseconds with libc nanosleep() using ctypes. """
  if (us >= 1000000): 
    sec = us/1000000
    us %= 1000000
  else: sec = 0
  nanosleep_req.tv_sec = sec
  nanosleep_req.tv_nsec = int(us * 1000)

  libc.nanosleep(nanosleep_req, nanosleep_rem)

#------------------------------------

#--- Millisecond delay functions: ---

def sleepDelay(ms):
  """ Delay milliseconds using time.sleep(). """
  time.sleep(ms/1000.0)

def delay(ms):
  """ Delay milliseconds with libc usleep() using ctypes. """
  ms = int(ms*1000)
  libc.usleep(ms)

def betterDelay(ms):
  """ Delay milliseconds with libc usleep() using ctypes and
      some simple error compensation. """
  if (ms >= 0.1):
    # Fix some of the error calculated through testing 
    # different sleep values on the Beaglebone, change 
    # accordingly:
    ms -= 0.1 
  ms = int(ms*1000)
  libc.usleep(ms)

#------------------------------------

#--- Tests: -------------------------

def test_delayus(delayus):
  """ Tests microsecond delay function. """

  n_tests = [1000, 1000, 1000, 500, 500, 250, 100,  100,      10,       2]
  tests   = [   0,  0.5,    1,  10,  50, 100, 500, 1000,  100000, 1000000]

  total_error = 0.0
  time_no_delay = 0 

  for i in range(len(n_tests)):
    total = 0.0
    error = 0.0
    for j in range(n_tests[i]):
      before = time.time()
      t = tests[i]
      if (t != 0): 
        delayus(t)
        # If testing no delay, i.e. t=0, then we don't
        # call the delay function. That way we can record
        # the time it takes to call the time() functions,
        # get test values, etc.
      total += time.time() - before 

    avg = (total/n_tests[i])
    avg *= 1000000 # sec -> usec
    # Subtract time recorded without calling delayus():
    avg -= time_no_delay 
    if (t == 0): time_no_delay = avg # Record no delay time
    error = abs(avg-t)
    if (t): 
      total_error += error
      # Because our no delay test doesn't call delayus(),
      # it wouldn't make sense to include it in our average error.
    print "%10.1f usec delay: time = %0.3f usec, error = %0.3f" %\
           (tests[i], avg, error)

  print "\n  avg error = +- %0.3f usec\n" % (total_error/len(n_tests))


def test_delayms(delayms):  
  """ Tests millisecond delay function. """

  n_tests = [1000, 1000, 1000, 1000,  100,   40,  10,   4,    2,   1]
  tests   = [   0,  0.1,  0.5,    1,   10,  50, 100, 500, 1000, 5000]

  # Uncomment to test a 1 minute delay:
  #tests.append(60000); n_tests.append(1)

  total_error = 0.0
  time_no_delay = 0 

  for i in range(len(n_tests)):
    total = 0.0
    error = 0.0
    for j in range(n_tests[i]):
      before = time.time()
      t = tests[i]
      if (t != 0): 
        delayms(t)
        # If testing no delay, i.e. t=0, then we don't
        # call the delay function. That way we can record
        # the time it takes to call the time() functions,
        # get test values, etc.
      total += time.time() - before 

    avg = (total/n_tests[i])
    avg *= 1000 # sec -> msec
    # Subtract time recorded without calling delayms():
    avg -= time_no_delay 
    if (t == 0): time_no_delay = avg # Record no delay time
    error = abs(avg-t)
    if (t): 
      total_error += error
      # Because our no delay test doesn't call delayms(),
      # it wouldn't make sense to include it in our average error.
    print "%10.1f msec delay: time = %0.3f msec, error = %0.3f" %\
           (tests[i], avg, error)

  print "\n  avg error = +- %0.3f msec\n" % (total_error/len(n_tests))

#------------------------------------


print "\n Microsecond delay using time.sleep():"
test_delayus(sleepMicroseconds)
print 20*'-'
print "\n Microsecond delay using ctypes and usleep():"
test_delayus(delayMicroseconds)
print 20*'-'
print "\n Microsecond delay using ctypes and nanosleep():"
test_delayus(nanosleepMicroseconds)
print 20*'-'

print "\n Millisecond delay using time.sleep():"
test_delayms(sleepDelay)
print 20*'-'
print "\n Millisecond delay using ctypes and usleep():"
test_delayms(delay)
print 20*'-'
print "\n Millisecond delay using ctypes and usleep() \n\
 with simple error compensation:"
test_delayms(betterDelay)
print 20*'-'


########NEW FILE########
__FILENAME__ = speed_test

from bbio import *

def setup():
  pinMode(GPIO1_6, OUTPUT)
  

def loop():
  state = 1
  while(True):
    digitalWrite(GPIO1_6, state)
    state ^= 1

run(setup, loop) 

########NEW FILE########
__FILENAME__ = install-bb-overlays
"""
 install-overlays.py
 Part of PyBBIO
 github.com/alexanderhiam/PyBBIO
 Apache 2.0 license

 Generates and installs device tree overlays used for pinmuxing on 
 BeagleBones running a 3.8 or newer kernel.
"""

import sys, os, glob, shutil

cwd = os.path.dirname(os.path.realpath(__file__))

config_path = os.path.realpath('%s/../bbio/platform/beaglebone' % cwd)
firmware_path = '/lib/firmware'
firmware_source_path = '%s/PyBBIO-src' % firmware_path
dtc_compile = ' dtc -O dtb -o %s.dtbo -b 0 -@ %s.dts'

overlays_to_copy = [
  '%s/overlays/PyBBIO-ADC-00A0.dts' % cwd,

  '%s/overlays/PyBBIO-epwmss0-00A0.dts' % cwd,
  '%s/overlays/PyBBIO-ecap0-00A0.dts' % cwd,

  '%s/overlays/PyBBIO-epwmss1-00A0.dts' % cwd,
  '%s/overlays/PyBBIO-ehrpwm1-00A0.dts' % cwd,
  '%s/overlays/PyBBIO-ecap1-00A0.dts' % cwd,

  '%s/overlays/PyBBIO-epwmss2-00A0.dts' % cwd,
  '%s/overlays/PyBBIO-ehrpwm2-00A0.dts' % cwd,
]

sys.path.append(config_path)
from config_common import GPIO

sys.path.append("%s/3.8" % config_path)
from config import ADC

with open('%s/overlays/gpio-template.txt' % cwd, 'rb') as f:
  gpio_template = f.read()

with open('%s/overlays/adc-template.txt' % cwd, 'rb') as f:
  adc_template = f.read()


header = \
"""
/* This file was generated as part of PyBBIO
 * github.com/alexanderhiam/PyBBIO
 * 
 * This file is in the Public Domain.
 */

"""

def copyOverlays():
  print "Copying and compiling static overlays...",
  for overlay in overlays_to_copy:
    if not os.path.exists(overlay):
      print "*Couldn't find static overlay %s!" % overlay
      continue
    shutil.copy2(overlay, firmware_source_path)
    name = os.path.splitext(os.path.basename(overlay))[0]
    os.system(dtc_compile % ('%s/%s' % (firmware_path, name),
                             '%s/%s' % (firmware_source_path, name)))

  print "Done!"

def generateOverlays():
  print "Generating and compiling GPIO overlays...",
  version = '00A0'
  for pin, config in GPIO.items():
    gpio_pin = pin.lower()
    register_name = config[0]
    offset = str(config[1])
    overlay_name = 'PyBBIO-%s' % gpio_pin
    dts = gpio_template.replace('{gpio_pin}', gpio_pin)\
                       .replace('{name}', register_name)\
                       .replace('{overlay_name}', overlay_name)\
                       .replace('{version}', version)\
                       .replace('{offset}', offset)
    with open('%s/%s-%s.dts' % (firmware_source_path, overlay_name, version), 'wb') as f:
      f.write(dts)
    os.system(dtc_compile % ('%s/%s-%s' % (firmware_path, overlay_name, version),
                             '%s/%s-%s' % (firmware_source_path, overlay_name, 
                                           version)))

  #print "Generating and compiling PWM overlays...",
  #version = '00A0'
  print "Done!"

  print "Generating and compiling ADC overlays...",
  version = '00A0'
  adc_scale = '100'
  for adc_ch, config in ADC.items():
    overlay_name = 'PyBBIO-%s' % adc_ch
    header_pin = config[2]
    dts = adc_template.replace('{adc_ch}', adc_ch)\
                      .replace('{header_pin}', header_pin)\
                      .replace('{overlay_name}', overlay_name)\
                      .replace('{adc_scale}', adc_scale)\
                      .replace('{version}', version)
    with open('%s/%s-%s.dts' % (firmware_source_path, overlay_name, version), 'wb') as f:
      f.write(dts)
    os.system(dtc_compile % ('%s/%s-%s' % (firmware_path, overlay_name, version),
                             '%s/%s-%s' % (firmware_source_path, overlay_name, 
                                           version)))
                                           
  print "Done!"
      
if __name__ == '__main__':
  if not os.path.exists(firmware_source_path):
    print "PyBBIO device tree overlay directory not found, creating..."
    os.makedirs(firmware_source_path)
  else:
    print "Old PyBBIO device tree overlay directory found, overwriting..."

  generateOverlays()
  copyOverlays()

########NEW FILE########
