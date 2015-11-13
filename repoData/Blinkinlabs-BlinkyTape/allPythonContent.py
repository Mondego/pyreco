__FILENAME__ = BlinkyTape
import serial
import glob

class BlinkyTape:
  def __init__(self, port=None):
    self.port = port

    if port != None:
      self.serial = serial.Serial(port, 115200)
      self.show() # Flush

  def connect(self, port):
    self.port = port

    self.serial = serial.Serial(port, 115200)
    self.serial.write(chr(255))
    self.serial.flush()

  def disconnct(self):
    self.port = None
    self.serial = None

  def sendPixel(self,r,g,b):
    data = bytearray()
    if r == 255: r = 254
    if g == 255: g = 254
    if b == 255: b = 254
    data.append(r)
    data.append(g)
    data.append(b)
    self.serial.write(str(data))  # change for new python/pyserial?
    self.serial.flush()

  def show(self):
    self.serial.write(chr(255))
    self.serial.flush()
    ret = self.serial.read(1)
    return ret


if __name__ == "__main__":

  import sys

  LED_COUNT = 60

  parser = optparse.OptionParser()
  parser.add_option("-p", "--port", dest="portname",
                    help="serial port (ex: /dev/ttyUSB0)", default=None)
  (options, args) = parser.parse_args()

  if options.portName != None:
    port = options.portname
  else:
    serialPorts = glob.glob("/dev/cu.usbmodem*")
    port = serialPorts[0]

  bb = BlinkyTape(port)


  while True:

    for x in range(0, LED_COUNT):
      bb.sendPixel(255,255,255)
    bb.show();

    for x in range(0, LED_COUNT):
      bb.sendPixel(0,0,0)
    bb.show()

########NEW FILE########
__FILENAME__ = BlinkyTapeUnitTest
import unittest
import time

import UserInterface
import Logger

class BlinkyTapeTestCase(unittest.TestCase):
  def __init__(self, methodName):
    super(BlinkyTapeTestCase, self).__init__(methodName)
    self.l = Logger.logger
    self.testResultData = None
    self.stopTests = False

  def StoreTestResultData(self, trd):
    self.testResultData = trd

  def Stop(self):
    self.stopTests = True

  def LogDataPoint(self, message, data):
    """Record a datapoint from testing.  This will log to all available logging outputs w/ the included data (db, sdcard, usb)."""
    tid = self.l.GetTestId(self.id())
    self.l.Log(self.id(), message, data, "data", testId=tid)


class BlinkyTapeTestRunner():
  """
  A test runner class that logs to the database and interacts with the LCD screen to display test results.
  """
  def __init__(self):
    self.i = UserInterface.interface
    self.l = Logger.logger

  def run(self, test):
    "Run the given test case or test suite."
    result = BlinkyTapeTestResult()
    startTime = time.time()
    test(result)
    stopTime = time.time()

    timeTaken = stopTime - startTime
    run = result.testsRun
    output = "Ran %d test%s in %.3fs\n" % (run, run != 1 and "s" or "", timeTaken)
    if not result.wasSuccessful():
      failed, errored = map(len, (result.failures, result.errors))
      if failed:
        output += "\nFAILED: %d\n" % failed
      if errored:
        output += "\nERRORS: %d\n" % errored
      textColor = (255, 255, 255)
      outColor = (255, 0, 0)
    else:
      output += "\nALL OK!\n"
      textColor = (0, 0, 0)
      outColor = (0, 255, 0)
    self.i.DisplayMessage(output, color = textColor, bgcolor = outColor, boxed=True)
    time.sleep(2)
      
    return result

class BlinkyTapeTestResult(unittest.TestResult):
  """A test result class that can log formatted text results to a stream.

  Used by BlinkyTapeTestRunner.
  """
  def __init__(self):
    unittest.TestResult.__init__(self)
    self.i = UserInterface.interface
    self.l = Logger.logger

  def getDescription(self, test):
    return test.shortDescription() or str(test)

  def startTest(self, test):
    unittest.TestResult.startTest(self, test)
    self.l.TestStart(test)

  def stopTest(self, test):
    self.shouldStop = test.stopTests

  def addSuccess(self, test):
    unittest.TestResult.addSuccess(self, test)
    self.i.DisplayPass()
    self.l.TestPass(test)

  def addError(self, test, err):
    unittest.TestResult.addError(self, test, err)
    self.i.DisplayError()
    self.l.TestError(test, err)

  def addFailure(self, test, err):
    unittest.TestResult.addFailure(self, test, err)
    self.i.DisplayFail()
    self.l.TestFail(test)


########NEW FILE########
__FILENAME__ = Config
import json

class Config():
  """
  Hopefully the simplest configuration object that could possibly work.
  Configurations are stored in json format to a text file, and are updated
  immediately when accessed.
  """
  def __init__(self, filename = 'default.cfg'):
    self.filename = filename
    self.reload()

  def reload(self):
    """
    Reload all configuration data from the config file. If the file cannot be loaded,
    the configuration data is cleared. This is automatically called by module initialization,
    and should not need to be called directly.
    """
    try:
      json_data = open(self.filename,'r')
      self.data = json.load(json_data)
    except:
      self.data = {}
      pass

  def save(self):
    """
    Save the configuration data to the configuration file. This is handled automatically
    by the set() and get() functions, and should not need to be called directly.
    """
    json_data = json.dumps(self.data)
      
    file = open(self.filename,'w')
    file.write(json_data)


  def set(self, module, key, value):
    """
    Set a value in the config file
    @param module Name of the module that the config value belongs to (for example, Logger)
    @param key Name of the config option to store
    @param value Value to store
    """
    if not self.data.has_key(module):
      self.data[module] = {}

    self.data[module][key] = value
    self.save()

  def get(self, module, key, default = ""):
    """
    Retrieve a value from the config file. If the value was not previously contained
    in the config file, then the default is saved to the file, and returned.
    @param module Name of the module that the config value belongs to (for example, Logger)
    @param key Name of the config option to store
    @param default Default value of the option, used if the config file does not already
                   contain the config option.
    """
    if not self.data.has_key(module):
      self.data[module] = {}

    if not self.data[module].has_key(key):
      self.data[module][key] = default
      self.save()

    return self.data[module][key]

########NEW FILE########
__FILENAME__ = DetectPlatform
import subprocess
import time
import glob


def detectPlatform():
  data = []
  proc = subprocess.Popen(["uname"], stdout=subprocess.PIPE, stdin=subprocess.PIPE)

  while True:
    read = proc.stdout.readline() #block / wait
    if not read:
        break
    data.append(read)

  if data[0] == 'Darwin\n':
    return "Darwin"

  return "Unknown"

def ListSerialPorts():
  # Scan for all connected devices; platform dependent
  platform = detectPlatform()

  if platform == 'Darwin':
    ports =      glob.glob("/dev/cu.usb*")
  else:
    # TODO: linux?
    ports =      glob.glob("/dev/ttyACM*")
    ports.extend(glob.glob("/dev/ttyUSB*"))

  return ports

########NEW FILE########
__FILENAME__ = IcspUtils
import subprocess
import time
import optparse
import sys
import cStringIO

def writeFuses(portName, lockFuses, eFuses, hFuses, lFuses, programmer="avrisp"):
  """
  Attempt to write the fuses of the attached Atmega device.

  """
  command = [
    "avrdude",
    "-c", programmer,
    "-P", portName,
    "-p", "m32u4",
    "-B", "200",
    "-e",
    "-U", "lock:w:%#02X:m"  % lockFuses,
    "-U", "efuse:w:%#02X:m" % eFuses,
    "-U", "hfuse:w:%#02X:m" % hFuses,
    "-U", "lfuse:w:%#02X:m" % lFuses,
  ]

  s = open('result.log','w')
  e = open('errorresult.log','w')
  result = subprocess.call(command, stdout=s, stderr=e)
  s.close()
  e.close()

  s = open('result.log','r')
  e = open('errorresult.log','r')
  stdout = s.readlines()
  stderr = e.readlines()
  s.close()
  e.close()

  return result, stdout, stderr
  
def loadFlash(portName, flashFile, programmer="avrisp"):
  """
  Attempt to write a .hex file to the flash of the attached Atmega device.
  @param portName String of the port name to write to
  @param flashFile Array of file(s) to write to the device
  """
  command = [
    "avrdude",
    "-c", programmer,
    "-P", portName,
    "-p", "m32u4",
    "-B", "1",
    "-U" "flash:w:%s:i" % flashFile,
  ]

  s = open('result.log','w')
  e = open('errorresult.log','w')
  result = subprocess.call(command, stdout=s, stderr=e)
  s.close()
  e.close()

  s = open('result.log','r')
  e = open('errorresult.log','r')
  stdout = s.readlines()
  stderr = e.readlines()
  s.close()
  e.close()

  return result, stdout, stderr


if __name__ == '__main__':
  parser = optparse.OptionParser()

  parser.add_option("-p", "--port", dest="portname",
                    help="serial port (ex: /dev/ttyUSB0)", default="/dev/ttyACM0")
  (options, args) = parser.parse_args()

  port=options.portname

  lockFuses = 0x2F
  eFuses    = 0xCB
  hFuses    = 0xD8
  lFuses    = 0xFF
  
  returnCode = writeFuses(port, lockFuses, eFuses, hFuses, lFuses)

 
  if (returnCode[0] != 0):
    print "FAIL. Error writing the fuses!"
    exit(1)
  print "PASS. Fuses written correctly"

  productionFile = "firmware/BlinkyTape-Production.hex"

  returnCode = loadFlash(port, productionFile)

  if (returnCode[0]!= 0):
    print "FAIL. Error programming bootloader!"
    exit(1)
  print "PASS. Bootlaoder programmed successfully"

########NEW FILE########
__FILENAME__ = Logger
import datetime
import json
#import MySQLdb
import traceback
import sys
import os

import TestRig
import UserInterface
import Config

class FileSink():
  def __init__(self, fileName):
    self.fileName = fileName
    print "Logging to logfile: %s" % self.fileName

    try:
      self.logFile = open(self.fileName, 'a')
    except Exception:
      self.logFile = None
      print "Cannot open logfile at %s" % self.fileName

  def Log(self, data):
    """ Log a message to the file """
    try:
      msg = json.dumps(data)   
      if self.logFile is not None:
        self.logFile.write(msg + '\n')
        self.logFile.flush()
    except:
      print "Error logging to file %s." % self.fileName
      #raise #prevent logging errors from killing things.

class Logger():
  def __init__(self):
    self.r = TestRig.testRig
    self.i = UserInterface.interface

    config = Config.Config()
    self.RequireDB = config.get('Logger','RequireDB',False)

    self.Verbose       = config.get('Logger','Verbose',True)
    self.ProductionRun = config.get('Logger','ProductionRun',"pp")

    self.dbHost     = config.get('Logger','dbHost',"host")
    self.dbUser     = config.get('Logger','dbUser',"user")
    self.dbPassword = config.get('Logger','dbPassword',"pw")
    self.dbDatabase = config.get('Logger','dbDatabase',"db")

    self.testIds = {}  # dictionary to store test <--> database ID mappings.

    self.sinks = []

  def Init(self):
    self.sinks.append(FileSink("./sd-log.log"))

    # If a usb stick is connected, log to it as well.
    if os.access('/media/usb0', os.R_OK):
      self.sinks.append(FileSink("/media/usb0/usb-log.log"))

    if self.RequireDB:
      self.InitDB() # moved to menu_functional test area.

  def InitDB(self):
    try: 
      self.db = MySQLdb.connect(host = self.dbHost, user = self.dbUser, passwd = self.dbPassword, db = self.dbDatabase)
    except Exception as err:
      self.db = None
      if self.RequireDB:
        traceback.print_exc(file=sys.stderr)
        raise Exception("CANNOT CONNECT TO DATABASE")

    self.ClearStaleEntries()
    self.LookupMachineInfo()

  def ClearStaleEntries(self):
    """Sometimes we get stale tests if the code crashes.  Clear and error them out."""
    if self.RequireDB:
      cursor = self.db.cursor()
      try:
        cursor.execute("UPDATE test_log SET test_status = 'error', test_result = 'STALLED' WHERE mac = %s AND test_status = 'running'", (self.MACAddress))
        self.db.commit()
        cursor.close()
      except Exception as err:
        traceback.print_exc(file=sys.stderr)
        self.db.rollback()
        raise Exception("DB LOGGING ERROR #6")
        
  def LookupMachineInfo(self, create = True):
    """Look to see if we have any info about our machine available."""
    if self.RequireDB:
      cursor = self.db.cursor()
      try:
        cursor.execute("SELECT * FROM machines WHERE mac = %s", (self.MACAddress))
        row = cursor.fetchone()
        if row == None:
          if create:
            self.CreateMachineEntry()
        else:
          self.MachineInfo = row
        cursor.close()
      except Exception as err:
        traceback.print_exc(file=sys.stderr)
        raise Exception("DB LOGGING ERROR #7")   

  def CreateMachineEntry(self):
    """Create a machine entry in our tracking table."""
    if self.RequireDB:
      cursor = self.db.cursor()
      try:
        cursor.execute("INSERT INTO machines (mac, production_run, machine_type, manufacture_date) VALUES (%s, %s, %s, NOW())", (self.MACAddress, self.ProductionRun, self.MachineType))
        self.db.commit()
        cursor.close()
        self.LookupMachineInfo(False) #pull it into our 
      except Exception as err:
        traceback.print_exc(file=sys.stderr)
        self.db.rollback()
        raise Exception("DB LOGGING ERROR #8")
        
  def Log(self, testName, message, extraData = None, logType = "raw", testId=0):
    """
    Logs a message during testing.  The message will be converted to a JSON string and
    sprayed across as many different output modes as possible: all file logers, and database.
    """
    data = {}
    data['production_run'] = self.ProductionRun
    data['test'] = testName
    d = datetime.datetime.today()
    data['timestamp'] = d.strftime("%Y-%m-%d %H:%M:%S")
    data['message'] = message
    data['data'] = extraData
    data['type'] = logType

    #send the data to all our various endpoints
    if self.RequireDB:
      self.LogToDB(data, testId)

    for sink in self.sinks:
      sink.Log(data)

  def LogToDB(self, data, testId=0):
    """Record the log message to the database if present."""
    if self.RequireDB:
      cursor = self.db.cursor()
      try:
        cursor.execute("INSERT INTO raw_log (result_id, production_run, mac, log_type, test_name, test_time, message, data, machine_status) VALUES (%s, %s, %s, %s, %s, NOW(), %s, %s, %s)",
                                            (testId, self.ProductionRun, self.MACAddress, data['type'], data['test'], data['message'], json.dumps(data['data']), json.dumps(data['status'])))
        self.db.commit()
        cursor.close()
      except:
        traceback.print_exc(file=sys.stderr)
        #self.db.rollback() #if our db has gone away... then this triggers another error.  plus mysql does not do transactions.
        #raise Exception("DB LOGGING ERROR #1") #raise #prevent logging errors from killing things.

  def GetTestId(self, testId):
    if self.RequireDB:
      return self.testIds[testId]
    else:
      return 0
      
  def TestStart(self, test):
    #insert new record into test_log table
    if self.RequireDB:
      cursor = self.db.cursor()
      try:
        cursor.execute("INSERT INTO test_log (mac, production_run, test_name, test_start, test_status) VALUES (%s, %s, %s, NOW(), 'running')",
                                            (self.MACAddress, self.ProductionRun, test.id()))
        self.db.commit()
        self.testIds[test.id()] = cursor.lastrowid #store new id test:id dictionary for later use
        cursor.close()
      except Exception as err:
        traceback.print_exc(file=sys.stderr)
        self.db.rollback()
        raise Exception("DB LOGGING ERROR #2")

    self.Log(test.id(), "START", testId=self.GetTestId(test.id()))

  def TestPass(self, test):
    tid = self.GetTestId(test.id())
    self.Log(test.id(), "PASS", test.testResultData, testId=tid)

    if self.RequireDB:
      cursor = self.db.cursor()
      try:
        cursor.execute("UPDATE test_log SET test_status = 'pass', test_end = NOW(), test_result = %s WHERE id = %s", (test.testResultData, self.GetTestId(test.id())))
        self.db.commit()
        cursor.close()
      except Exception as err:
        traceback.print_exc(file=sys.stderr)
        self.db.rollback()
        raise Exception("DB LOGGING ERROR #3")

  def TestError(self, test, err):
    tid = self.GetTestId(test.id())
    etype, value, tb = err
    data = traceback.format_exception(etype, value, tb, 10)
    self.Log(test.id(), "ERROR", data, "error", testId=tid)

    if self.RequireDB:
      cursor = self.db.cursor()
      try:
        cursor.execute("UPDATE test_log SET test_status = 'error', test_end = NOW(), test_result = %s WHERE id = %s", (test.testResultData, self.GetTestId(test.id())))
        self.db.commit()
        cursor.close()
      except Exception as err:
        traceback.print_exc(file=sys.stderr)
        self.db.rollback()
        raise Exception("DB LOGGING ERROR #4")

  def TestFail(self, test):
    tid = self.GetTestId(test.id())
    self.Log(test.id(), "FAIL", test.testResultData, testId=tid)

    if self.RequireDB:
      cursor = self.db.cursor()
      try:
        cursor.execute("UPDATE test_log SET test_status = 'fail', test_end = NOW(), test_result = %s WHERE id = %s", (test.testResultData, self.GetTestId(test.id())))
        self.db.commit()
        cursor.close()
      except Exception as err:
        traceback.print_exc(file=sys.stderr)
        self.db.rollback()
        raise Exception("DB LOGGING ERROR #5")

# Declare a single instance of the logger interface, that all modules can share
# TODO: This is so that new modules can be loaded dynamically and run, but there
# is probably a more elegent way to do this.
logger = Logger()


########NEW FILE########
__FILENAME__ = Menu
import UserInterface
import os
import re
import pygame
import unittest
import RPi.GPIO as GPIO

class Menu(object):
  """
  Display a menu of all files in the given directory that match the given
  filename, and allow the user to select one and run it.

  The menu looks like this:
  item1  <- Min item
  item2
  item3  <- Top item to display  <-|
  item4                          <-| Items currently being dispalyed
  item5  <- Selected item        <-|
  item6                          <-|
  item7  <- Max item

  This is a simple state machine, which draws a subset of the available items
  in the item list. Unselected items are drawn with one style, and selected items
  are drawn with a different style. The top item and selected item index are updated
  when the user presses the up and down buttons.
  """

  def __init__(self, interface):
    """
    Init a new test menu.
    @param interface UserInterface to draw on
    @param items List of possible items to display
    """
    self.i = interface

    self.visible_item_count = 4 # Maximum items to display at once
 
    self.selection_index = 0
    self.top_visible_index = 0
 
    self.selection_animate_state = 0 
    self.selection_animate_offset = 0

  def DrawItem(self, name, position, selected):
    """
    Draw an unselected menu item
    @param name Name item to dispaly
    @param position Place to draw the item (0-3)
    @param selected True if the current item is selected, false otherwise
    """

    if (selected):
      color = (255,255,255)
      self.i.screen.fill((0,0,200),(0,32*position,320,32))
      text = self.i.font.render(name,1,color)

      if (self.selection_animate_state < 15):
        self.selection_animate_state += 1
      elif (self.selection_animate_state == 15):
        self.selection_animate_offset += 1
        if (self.selection_animate_offset > text.get_width() + 180):
          self.selection_animate_state = 0
          self.selection_animate_offset = 0
 
      offset = -self.selection_animate_offset
      self.i.screen.blit(text, (offset,32*position))
      self.i.screen.blit(text, (offset+text.get_width() + 180,32*position))

    else:
      color = (0,0,0)
      text = self.i.font.render(name,1,color)
      offset = 0
      self.i.screen.blit(text, (offset,32*position))


  def DrawMenu(self):
    """ Draw the current menu screen """
    self.i.screen.fill((255,255,255))

    for i in range(0, self.visible_item_count):
      index = self.top_visible_index + i
      selected = (index == self.selection_index)

      #if this is a valid item, draw it
      if (index < len(self.items)):
        name = str(index + 1) + ":" + self.items[index][0]
        self.DrawItem(name,i,selected)
    
    pygame.display.flip()


  def Display(self):
    """ Run an interactive menu """
    while True:
      if(self.i.useFramebuffer == False):
        print ""
        i = 1
        for entry in self.items:
          print str(i) + ". " + entry[0]
          i = i + 1


          s = raw_input("Type a selection or press enter to run all tests")
          try:
            if len(s) == 0:
    	      n = 0
            else:
              n = int(s) - 1
          except ValueError:
            pass
          else:
            if n >= 0 and n < len(self.items):
              self.HandleSelection(self.items[n])

      else:
        self.DrawMenu()
       
        last_selection_index = self.selection_index

        if(self.i.usePi):
          if(GPIO.input(23) == 0):
            self.HandleSelection(self.items[self.selection_index])

        else:
          for event in pygame.event.get(pygame.KEYUP):
            if (event.key == pygame.K_UP):
              # Try to decrease the selection index
              self.selection_index = max(self.selection_index - 1, 0)
              # If the selection index crashes into the top top visible index, try to decrease the top visible index.
              if (self.selection_index == self.top_visible_index):
                self.top_visible_index = max(self.top_visible_index - 1, 0)
        
            if (event.key == pygame.K_DOWN or event.key == pygame.K_LEFT):
              # Try to increase the selection index
              self.selection_index = min(self.selection_index + 1, len(self.items) - 1)
              # If the selection index crashes into the top top visible index, try to increase the top visible index.
              if (self.selection_index == self.top_visible_index + self.visible_item_count - 1):
                self.top_visible_index = min(self.top_visible_index + 1, len(self.items) - self.visible_item_count)
        
            if (event.key == pygame.K_RETURN or event.key == pygame.K_RIGHT):
              self.HandleSelection(self.items[self.selection_index])
        
            if (event.key == pygame.K_ESCAPE):
              exit(1)
        
          # If we have a new selection, reset the animation
          if (last_selection_index != self.selection_index):
            self.selection_animate_state = 0 
            self.selection_animate_offset = 0

  def HandleSelection(self, selection):
    print "Item selected: " + str(selection)

if __name__ == '__main__':
  interface = UserInterface.interface

  # a static array for menu entries
  entries = [
          ('short name', 'a_data'),
          ('This one has a really long name', ''),
          ('Third selection', ''),
          ('Dictionary for data', {'option1':32, 'option2':10}),
          ('Last Selection', '')
  ]

  menu = Menu(interface)
  menu.items = entries
  menu.Display()

########NEW FILE########
__FILENAME__ = menus
menus = {
'pcba_test' : [
          ('Run all Tests'           , ['test_power_on',
                                        'test_bootloader',
                                        'test_functional']),
          ('Power on Test'           , 'test_power_on'),
          ('Flash Bootloader test'   , 'test_bootloader'),
          ('Function Test'           , 'test_functional'),
	],
}


########NEW FILE########
__FILENAME__ = menu_pcba_test
import os
import re
import unittest
import inspect
import time
import traceback
import sys

import Logger
import Menu  
import UserInterface
import BlinkyTapeUnitTest
import Config
import menus

class PcbaTestMenu(Menu.Menu):
  """
  Display a menu of the functional tests. When a functional test is selected,
  the pyunit test loader is used to load and run all tests from the module.
  """
  items = []

  def __init__(self, interface):
    # Look up which menu item to display, then display it.
    config = Config.Config()
    self.menu_name = config.get('Menu','name','pcba_test')
    self.items = list(menus.menus[self.menu_name])

    super(PcbaTestMenu, self).__init__(interface)

  def HandleSelection(self, selection):
    # Remove the extension before attempting to load the module.
    module_name = selection[1]

    if type(module_name) is list:
      allTests = unittest.TestSuite()
      for module_n in module_name:
        module = __import__(module_n)
        tests = unittest.defaultTestLoader.loadTestsFromModule(module)
        allTests.addTests(tests)

      runner = BlinkyTapeUnitTest.BlinkyTapeTestRunner()
      result = runner.run(allTests)

    elif (module_name.startswith('test')):
      module = __import__(module_name)

      tests = unittest.defaultTestLoader.loadTestsFromModule(module)

      runner = BlinkyTapeUnitTest.BlinkyTapeTestRunner()
      result = runner.run(tests)

    elif (module_name.startswith('menu')):
      module = __import__(module_name)

      # Look for the first class which inherits from Menu, then load it.
      for name, obj in inspect.getmembers(module):
        if inspect.isclass(obj):
          for base in obj.__bases__:
            if (base == Menu.Menu):
              menu = obj(self.i)
              menu.Display()

if __name__ == '__main__':
  try:
    Logger.logger.Init()

    interface = UserInterface.interface
    interface.DisplayMessage("Loading test interface...")

    menu = PcbaTestMenu(interface)
    menu.Display()
  except Exception as err:
    traceback.print_exc(file=sys.stderr)
    UserInterface.interface.DisplayError(str(err))
    while True:
      time.sleep(500)


########NEW FILE########
__FILENAME__ = RemoteArduino
import serial
import time

STK_OK      = 0x10
STK_INSYNC  = 0x14
CRC_EOP     = 0x20
BT_COMMAND  = 0x21

class RemoteArduino:
  """Class to control an Arduino remotely. A light Firmata-like thing.
     The Arduino must be loaded with the TestProgram_Arduino sketch.
  """
  def __init__(self, port):
    """ Open a connection to an arduino running the SerialTester sketch.
    port: Serial port device name, for example: '/dev/cu.usbmodelfa1321'
    """
    self.serial = serial.Serial(port, baudrate=19200, timeout=2)

  def sendCommand(self, command, channel, responseCount):
    self.serial.write(chr(BT_COMMAND))
    self.serial.write(command)
    self.serial.write(chr(channel))
    self.serial.write(chr(CRC_EOP))
    # TODO: Read back response?
    # response is: STK_INSYNC, [data], STK_OK
    try:
      data = self.serial.read(1)
      response = ord(data)
    except TypeError:
      raise Exception(" Bad response from test rig. Data='" + data + "'")

    if(STK_INSYNC != response):
      raise Exception(" Bad response from test rig. Expected: " + hex(STK_INSYNC) + ", got: " + hex(response))

    returnData = []
    for i in range(0, responseCount):
      returnData.append(ord(self.serial.read(1)))

    response = ord(self.serial.read(1))
    if(STK_OK != response):
      raise Exception(" Bad response from test rig. Expected: " + hex(STK_OK) + ", got: " + hex(response))
    
    return returnData

  def getRemoteVersion(self):
    return self.sendCommand('v', 1, 1)

  def setProgrammerSpeed(self, speed):
    return self.sendCommand('s', speed, 0)

  def analogRead(self, pin):
    """Read the value of an analog pin"""
    # TODO: How to send float cleanly?
    counts = 100
    analogValue = 0
    for i in range(0, counts):
      response = self.sendCommand('m', pin, 2)
      analogValue += (response[0]*256 + response[1])
    return float(analogValue/counts)

  def digitalRead(self, pin):
    """Read the value of a digital pin"""
    return (self.sendCommand('r', pin, 1))[0]

  def pinMode(self, pin, mode):
    """Change the mode of a digital pin"""
    if mode == 'OUTPUT':
      self.sendCommand('o', pin, 0)
    elif mode == 'INPUT':
      self.sendCommand('i', pin, 0)
    elif mode == 'INPUT_PULLUP':
      self.sendCommand('p', pin, 0)
    else:
      raise Exception("Mode " + mode + " not understood")

  def digitalWrite(self, pin, value):
    """Change the state of a digital pin configured as output"""
    if value == 'HIGH':
      self.sendCommand('h', pin, 0)
    elif value == 'LOW':
      self.sendCommand('l', pin, 0)
    else:
      raise Exception("Value" + value + " not understood")

########NEW FILE########
__FILENAME__ = run_strip_test
import os
import re
import unittest
import inspect
import time
import traceback
import sys

import Logger
import Menu  
import UserInterface
import TestRig
import BlinkyTapeUnitTest
import Config
import menus

class PcbaTestMenu(Menu.Menu):
  """
  Display a menu of the functional tests. When a functional test is selected,
  the pyunit test loader is used to load and run all tests from the module.
  """
  items = []

  def __init__(self, interface):
    # Look up which menu item to display, then display it.
    config = Config.Config()
    self.menu_name = config.get('Menu','name','pcba_test')
    self.items = list(menus.menus[self.menu_name])

    super(PcbaTestMenu, self).__init__(interface)

  def HandleSelection(self, selection):
    # Remove the extension before attempting to load the module.
    module_name = selection[1]

    if type(module_name) is list:
      allTests = unittest.TestSuite()
      for module_n in module_name:
        module = __import__(module_n)
        tests = unittest.defaultTestLoader.loadTestsFromModule(module)
        allTests.addTests(tests)

      runner = BlinkyTapeUnitTest.BlinkyTapeTestRunner()
      result = runner.run(allTests)

    elif (module_name.startswith('test')):
      module = __import__(module_name)

      tests = unittest.defaultTestLoader.loadTestsFromModule(module)

      runner = BlinkyTapeUnitTest.BlinkyTapeTestRunner()
      result = runner.run(tests)

    elif (module_name.startswith('menu')):
      module = __import__(module_name)

      # Look for the first class which inherits from Menu, then load it.
      for name, obj in inspect.getmembers(module):
        if inspect.isclass(obj):
          for base in obj.__bases__:
            if (base == Menu.Menu):
              menu = obj(self.i)
              menu.Display()

if __name__ == '__main__':
  try:
    Logger.logger.Init()
    
    # Add in some new defines for this test rig
    newShortTestPins = [
      TestRig.ArduinoPin('START_BUTTON',   16),
    ]
    TestRig.testRig.shortTestPins.extend(newShortTestPins)

    newRelayPins = [
      TestRig.ArduinoPin('LED_R',         11),
      TestRig.ArduinoPin('LED_G',         10),
      TestRig.ArduinoPin('LED_B',         17),  # Note: for Duemilanova, different for Leonardo
    ]
    TestRig.testRig.relayPins.extend(newRelayPins)

    interface = UserInterface.interface

    TestRig.testRig.enableRelay('LED_G')

    while(True):
      TestRig.testRig.setInputPullup('START_BUTTON')

      while(TestRig.testRig.readInput('START_BUTTON') == 1):
        time.sleep(.05)

      module = __import__("test_strip")

      tests = unittest.defaultTestLoader.loadTestsFromModule(module)

      runner = BlinkyTapeUnitTest.BlinkyTapeTestRunner()
      result = runner.run(tests)
      print result
      if(len(result.errors) == 0 and len(result.failures) == 0):
        TestRig.testRig.enableRelay('LED_G')
      else:
        TestRig.testRig.enableRelay('LED_R')

  except Exception as err:
    traceback.print_exc(file=sys.stderr)
    UserInterface.interface.DisplayError(str(err))
    while True:
      time.sleep(500)


########NEW FILE########
__FILENAME__ = TestRig
import time

import DetectPlatform
import RemoteArduino



class ArduinoPin:
  def __init__(self, name, number, net = None, suppressHigh = False, suppressLow = False):
    self.name = name
    self.number = number

    if(net == None):
      self.net = name
    else:
      self.net = net

    self.suppressHigh = suppressHigh
    self.suppressLow = suppressLow

  def __str__(self):
    return self.name

class MeasurementPin():
  def __init__(self, name, number, M, B):
    self.name = name
    self.number = number
    self.M = M
    self.B = B

  def __str__(self):
    return self.name


class TestRig:
  """ Class that represents a BlinkyTape test rig"""

  def __init__(self, port, measurementPins, relayPins, shortTestPins):
    self.measurementPins = measurementPins
    self.relayPins = relayPins
    self.shortTestPins = shortTestPins

    # TODO: don't connect here?
    self.connect(port)

  def connect(self, port):
    """Initialize a connection to a test rig"""
    self.port = port
    self.arduino = RemoteArduino.RemoteArduino(port)
    remoteVersion = self.arduino.getRemoteVersion()
    if remoteVersion < 1:
      raise Exception("Remote version (" + hex(remoteVersion) + ") too low, upgrade the Arduino sketch")

    self.resetState()

  def disconnect(self):
    self.arduino = None

  def resetState(self):
    """ Set all relay pins to output and low, and all short test pins to high-impedance inputs """
    for pin in self.relayPins:
      self.arduino.digitalWrite(pin.number, 'LOW')
      self.arduino.pinMode(pin.number, 'OUTPUT')

    for pin in self.shortTestPins:
      self.arduino.pinMode(pin.number, 'INPUT')

    # TODO: reset analog pins?

  def enableRelay(self, relayName):
    """ Enable an output relay """
    for pin in self.relayPins:
      if pin.name == relayName:
        self.arduino.digitalWrite(pin.number, 'HIGH')
        return
    raise Exception("Relay " + relayName + "not found!")
    
  def disableRelay(self, relayName):
    """ Disable an output relay """
    for pin in self.relayPins:
      if pin.name == relayName:
        self.arduino.digitalWrite(pin.number, 'LOW')
        return
    raise Exception("Relay " + relayName + "not found!")

  def setOutputLow(self, pinName):
    """ Disable an output relay """
    for pin in self.shortTestPins:
      if pin.name == pinName:
        self.arduino.pinMode(pin.number, 'OUTPUT')
        self.arduino.digitalWrite(pin.number, 'LOW')
        return
    raise Exception("Pin" + pinName + "not found!")

  def setInput(self, pinName):
    """ Set up a pin as input"""
    for pin in self.shortTestPins:
      if pin.name == pinName:
        self.arduino.pinMode(pin.number, 'INPUT')
        return
    raise Exception("Pin" + pinName + "not found!")

  def setInputPullup(self, pinName):
    """ Set up a pin as input in pullup mode"""
    for pin in self.shortTestPins:
      if pin.name == pinName:
        self.arduino.pinMode(pin.number, 'INPUT_PULLUP')
        return
    raise Exception("Pin" + pinName + "not found!")

  def readInput(self, pinName):
    """ Set up a pin as input in pullup mode"""
    for pin in self.shortTestPins:
      if pin.name == pinName:
        return self.arduino.digitalRead(pin.number)
    raise Exception("Pin" + pinName + "not found!")

  def setProgrammerSpeed(self, speed):
    """ Set the speed of the programmer"""
    return self.arduino.setProgrammerSpeed(speed)
    
  def measure(self, measurementName):
    """ Read a measurement pin """
    for pin in self.measurementPins:
      if pin.name == measurementName:
        return pin.M*(self.arduino.analogRead(pin.number) + pin.B)

    raise Exception("Measurement pin " + measurementName + "not found!")

  def shortTest(self, pinName):
    """ Perform a short test between the given pin and all other pins by pulling the given pin low,
        then each other pin high using a weak pull-up, and measuring the other pin
    """
    faults = []

    # Step through each pin, setting it as a low output, then reading in the value of all other pins
    for pin in self.shortTestPins:
      if pin.name != pinName:
        continue

      # Short everything together by setting it to high output, to discharge passives
      for p in self.shortTestPins:
        self.arduino.pinMode(p.number, 'OUTPUT')
        self.arduino.digitalWrite(p.number, 'LOW')
      time.sleep(.2)

      # Reset all pins to inputs
      for p in self.shortTestPins:
        self.arduino.pinMode(p.number, 'INPUT_PULLUP')

      # Set the left-side pin to low output
      self.arduino.pinMode(pin.number, 'OUTPUT')
      self.arduino.digitalWrite(pin.number, 'LOW')


      # Now, iterate through all the other pins
      # There are a few cases here:
      # - If neither pin nor inputPin are suppressHigh nor suppressLow, test them against each other.
      # - If pin is suppresslow or inputPin is suppresshigh, only test if they are on the same net.
      for inputPin in self.shortTestPins:
        if pin.name != inputPin.name:
          if (pin.suppressLow or inputPin.suppressHigh) and (pin.net != inputPin.net):
            continue

          shorted = (0 == self.arduino.digitalRead(inputPin.number))
          expectedShorted = (inputPin.net == pin.net)

          if shorted != expectedShorted:
            faults.append((pin.name, inputPin.name, expectedShorted, shorted))
   
    return sorted(list(dict.fromkeys(faults)))

def MakeDefaultRig():
  """ Actually we only have one version of the hardware. Make a class instance to represent it.
  """
  serialPorts = DetectPlatform.ListSerialPorts()
  port = serialPorts[0]

  # List of pins that are connected to analog sensors on the board
  measurementPins = [
    MeasurementPin('DUT_CURRENT',0, 1, 0),  # Note: an analog pin! Values determined by experiment
    ]

  # List of pins that control a relay on the test rig
  relayPins = [
    ArduinoPin('EN_USB_VCC_LIMIT', 8),
    ArduinoPin('EN_USB_VCC',       9),
    ArduinoPin('EN_USB_DATA',     10),
    ArduinoPin('EN_USB_GND',      11),
    ArduinoPin('EN_LED_OUT',      23),
    ]
  

  # List of pins that are connected directly to an I/O pin on the DUT,
  # that should be used to do an n*n short test
  # For nodes with reverse protection diodes (eg, VCC and GND), specifcy
  # 'suppressHigh' to prevent them from being pulled higher than any other
  # nets, and 'suppressLow' to prevent them from being pulled lower than any
  # other nets.
  shortTestPins = [
    ArduinoPin('DUT_USB_GND',    19, net='GND', suppressHigh=True), # Analog input pins as digital, A0 = 18, A1 = 19, etc
    ArduinoPin('DUT_OUT_GND',    22, net='GND', suppressHigh=True),
    ArduinoPin('DUT_USB_VCC',    20, net='VCC', suppressLow=True),
    ArduinoPin('DUT_OUT_VCC',    21, net='VCC', suppressLow=True),
    ArduinoPin('ICSP_RESET',      0),  # Regular digital pins
    ArduinoPin('DUT_A9',          1),
    # 2,3 used by I2C port for current sensor
    ArduinoPin('DUT_D11',         4),
    ArduinoPin('DUT_D7',          5),
    ArduinoPin('DUT_D13',         6),
    ArduinoPin('DUT_USB_SHIELD',  7),
    ArduinoPin('TAP_USB_D-',     12),
    ArduinoPin('TAP_USB_D+',     13),
    ArduinoPin('ICSP_MISO',      14),   # ICSP pins
    ArduinoPin('ICSP_SCK',       15),
    ArduinoPin('ICSP_MOSI',      16),
    ]
  

  return TestRig(port, measurementPins, relayPins, shortTestPins)


testRig = MakeDefaultRig()

########NEW FILE########
__FILENAME__ = test_bootloader
import time
import subprocess

import BlinkyTapeUnitTest
import TestRig
import UserInterface
import IcspUtils
import Logger

class TestProgramBootloader(BlinkyTapeUnitTest.BlinkyTapeTestCase):
  def __init__(self, methodName):
    super(TestProgramBootloader, self).__init__(methodName)
    self.testRig = TestRig.testRig
    self.port = self.testRig.port
    self.i = UserInterface.interface

  def setUp(self):
    self.stopMe = True

  def tearDown(self):
    self.testRig.connect(self.port)
    self.testRig.resetState()

    if self.stopMe:
      self.Stop()

  def test_010_program_fuses(self):
    self.i.DisplayMessage("Programming fuses...")

    self.testRig.resetState()
    self.testRig.enableRelay('EN_USB_VCC')
    self.testRig.enableRelay('EN_USB_GND')
    self.testRig.setProgrammerSpeed(0)
    self.testRig.disconnect()

    lockFuses = 0x2F
    eFuses    = 0xCB
    hFuses    = 0xD8
    lFuses    = 0xFF
#    lFuses    = 0x5E #default
    
    result = IcspUtils.writeFuses(self.port, lockFuses, eFuses, hFuses, lFuses)
    
    self.LogDataPoint('fuses stdout', result[1])
    self.LogDataPoint('fuses stderr', result[2])

    self.assertEqual(result[0], 0)
    self.stopMe = False

  def test_020_program_production(self):
    self.i.DisplayMessage("Programming firmware...")

    self.testRig.connect(self.port)
    self.testRig.resetState()
    self.testRig.enableRelay('EN_USB_VCC')
    self.testRig.enableRelay('EN_USB_GND')
    self.testRig.setProgrammerSpeed(1)
    self.testRig.disconnect()

    productionFile = "firmware/BlinkyTape-Production.hex"

    result = IcspUtils.loadFlash(self.port, productionFile)

    self.LogDataPoint('firmware stdout', result[1])
    self.LogDataPoint('firmware stderr', result[2])

    self.assertEqual(result[0], 0)
    self.stopMe = False

########NEW FILE########
__FILENAME__ = test_functional
# NOTE: The Producion version of this is slighly different. The guard bands for current
# measurement were changed, and the LED strip output is turned on before USB power, to
# prevent the LEDs from being damaged. This version is an attempt to bring these changes
# in, however they have to be retrieved from the factory test rig.

import time
import serial

import BlinkyTapeUnitTest
import TestRig
import UserInterface
import BlinkyTape
import DetectPlatform

class TestFunctionalTests(BlinkyTapeUnitTest.BlinkyTapeTestCase):
  def __init__(self, methodName):
    super(TestFunctionalTests, self).__init__(methodName)

  @classmethod
  def setUpClass(self):
    # TODO: Why can't access self.testRig from __init__ here?
    self.testRig = TestRig.testRig
    self.testRig.resetState()

    self.i = UserInterface.interface
    self.dut = BlinkyTape.BlinkyTape()

  @classmethod
  def tearDownClass(self):
    self.dut = None
    self.testRig.resetState()

  def setUp(self):
    self.stopMe = True

  def tearDown(self):
    if self.stopMe:
      self.Stop()

  def test_010_dutDisconnectedCurrent(self):
    self.i.DisplayMessage("Checking disconnected current...")
    MIN_OFF_CURRENT = -1
    MAX_OFF_CURRENT = 1

    current = self.testRig.measure('DUT_CURRENT')

    self.i.DisplayMessage("DUT disconnectd current: %0.2f < %0.2f < %0.2f." % (MIN_OFF_CURRENT, current, MAX_OFF_CURRENT))
    self.StoreTestResultData("%0.2f" % current)

    self.assertTrue(current> MIN_OFF_CURRENT
                    and current < MAX_OFF_CURRENT)
    self.stopMe = False

  def test_020_usbEnumeration(self):
    self.i.DisplayMessage("Waiting for device to enumerate on USB...")

    MAX_ENUMERATION_TIME_S = 5
    # Scan for all connected devices; platform dependent
    originalPorts = set(DetectPlatform.ListSerialPorts())
 
    self.testRig.enableRelay('EN_LED_OUT')
    self.testRig.enableRelay('EN_USB_GND')
    self.testRig.enableRelay('EN_USB_VCC')
    self.testRig.enableRelay('EN_USB_DATA')

    # Wait for the device to enumerate
    startTime = time.time()
    while(time.time() < startTime + 5):
      finalPorts = set(DetectPlatform.ListSerialPorts())
      newPorts = finalPorts - originalPorts
      if len(newPorts) == 1:
        self.dut.port = list(newPorts)[0]
        break

    self.LogDataPoint("DUT Usb port:", self.dut.port)
    self.assertTrue(self.dut.port != '')
    self.stopMe = False

  def test_030_dutConnected(self):
    self.i.DisplayMessage("Connecting to DUT")

    connected = False
    try:
      self.dut.connect(self.dut.port)
    except serial.SerialException:
      pass
    else:
      connected = True

    self.assertTrue(connected)
    self.stopMe = False

  def test_040_dutConnectedCurrent(self):
    self.i.DisplayMessage("Checking connected current...")

    MIN_CONNECTED_CURRENT = 20
    MAX_CONNECTED_CURRENT = 100

    current = self.testRig.measure('DUT_CURRENT')

    self.i.DisplayMessage("DUT connected current: %0.2f < %0.2f < %0.2f." % (MIN_CONNECTED_CURRENT, current, MAX_CONNECTED_CURRENT))
    self.StoreTestResultData("%0.2f" % current)

    self.assertTrue(current > MIN_CONNECTED_CURRENT
                    and current < MAX_CONNECTED_CURRENT)
    self.stopMe = False

  def test_045_LedsConnectedCurrent(self):
    self.i.DisplayMessage("Checking LEDs connected current...")

    MIN_CONNECTED_CURRENT = 20
    MAX_CONNECTED_CURRENT = 150


    current = self.testRig.measure('DUT_CURRENT')

    self.i.DisplayMessage("LEDs connected current: %0.2f < %0.2f < %0.2f." % (MIN_CONNECTED_CURRENT, current, MAX_CONNECTED_CURRENT))
    self.StoreTestResultData("%0.2f" % current)

    self.assertTrue(current > MIN_CONNECTED_CURRENT
                    and current < MAX_CONNECTED_CURRENT)
    self.stopMe = False

  def test_050_redLedsOnCurrent(self):
    self.i.DisplayMessage("Checking red LEDs on...")

    MIN_RED_CURRENT = 50
    MAX_RED_CURRENT = 100
    # TODO: Why send this twice?
    for j in range (0, 2):
      for x in range(0, 60):
        self.dut.sendPixel(255,0,0)
      self.dut.show();

    current = self.testRig.measure('DUT_CURRENT')

    self.i.DisplayMessage("Red LEDs current: %0.2f < %0.2f < %0.2f." % (MIN_RED_CURRENT, current, MAX_RED_CURRENT))
    self.StoreTestResultData("%0.2f" % current)

    self.assertTrue(current > MIN_RED_CURRENT
                    and current < MAX_RED_CURRENT)
    self.stopMe = False

  def skip_test_060_greenLedsOnCurrent(self):
    self.i.DisplayMessage("Checking green LEDs on...")

    MIN_GREEN_CURRENT = 50
    MAX_GREEN_CURRENT = 100
    # TODO: Why send this twice?
    for j in range (0, 2):
      for x in range(0, 60):
        self.dut.sendPixel(0,255,0)
      self.dut.show();

    current = self.testRig.measure('DUT_CURRENT')

    self.i.DisplayMessage("Green LEDs current: %0.2f < %0.2f < %0.2f." % (MIN_GREEN_CURRENT, current, MAX_GREEN_CURRENT))
    self.StoreTestResultData("%0.2f" % current)

    self.assertTrue(current > MIN_GREEN_CURRENT
                    and current < MAX_GREEN_CURRENT)
    self.stopMe = False

  def skip_test_070_blueLedsOnCurrent(self):
    self.i.DisplayMessage("Checking blue LEDs on...")

    MIN_BLUE_CURRENT = 50
    MAX_BLUE_CURRENT = 100
    # TODO: Why send this twice?
    for j in range (0, 2):
      for x in range(0, 60):
        self.dut.sendPixel(0,0,255)
      self.dut.show();

    current = self.testRig.measure('DUT_CURRENT')

    self.i.DisplayMessage("Blue LEDs current: %0.2f < %0.2f < %0.2f." % (MIN_BLUE_CURRENT, current, MAX_BLUE_CURRENT))
    self.StoreTestResultData("%0.2f" % current)

    self.assertTrue(current > MIN_BLUE_CURRENT
                    and current < MAX_BLUE_CURRENT)
    self.stopMe = False

  def test_080_whiteLedsOnCurrent(self):
    self.i.DisplayMessage("Checking white LEDs on...")

    MIN_WHITE_CURRENT = 100
    MAX_WHITE_CURRENT = 300
    # TODO: Why send this twice?
    for j in range (0, 2):
      for x in range(0, 60):
        self.dut.sendPixel(255,255,255)
      self.dut.show();

    current = self.testRig.measure('DUT_CURRENT')

    self.i.DisplayMessage("White LEDs current: %0.2f < %0.2f < %0.2f." % (MIN_WHITE_CURRENT, current, MAX_WHITE_CURRENT))
    self.StoreTestResultData("%0.2f" % current)

    self.assertTrue(current > MIN_WHITE_CURRENT
                    and current < MAX_WHITE_CURRENT)
    self.stopMe = False

  def test_090_D7_connected(self):
    self.i.DisplayMessage("Checking D7 input works...")
    self.testRig.setOutputLow('DUT_D7')

    pinStates = 0
    for j in range (0, 2):
      for x in range(0, 60):
        self.dut.sendPixel(0,0,0)
      pinStates = self.dut.show();

    self.testRig.setInput('DUT_D7')
    
    self.assertTrue(ord(pinStates[0]) == 11)
    self.stopMe = False

  def test_091_D11_connected(self):
    self.i.DisplayMessage("Checking D11 input works...")
    self.testRig.setOutputLow('DUT_D11')

    pinStates = 0
    for j in range (0, 2):
      for x in range(0, 60):
        self.dut.sendPixel(0,0,0)
      pinStates = self.dut.show();

    self.testRig.setInput('DUT_D11')
    
    self.assertTrue(ord(pinStates[0]) == 13)
    self.stopMe = False

  def test_092_A9_connected(self):
    self.i.DisplayMessage("Checking A9 input works...")
    self.testRig.setOutputLow('DUT_A9')

    pinStates = 0
    for j in range (0, 2):
      for x in range(0, 60):
        self.dut.sendPixel(0,0,0)
      pinStates = self.dut.show();

    self.testRig.setInput('DUT_A9')
   
    self.assertTrue(ord(pinStates[0]) == 14)
    self.stopMe = False

  def test_100_button_connected(self):
    self.i.DisplayMessage("Checking button input works...")

    MAX_TIME_SECONDS = 60;

    startTime = time.time()
    found = False
    mode = True

    while((not found) and (time.time() < startTime + MAX_TIME_SECONDS)):
      pinStates = 0
      for j in range (0, 2):
        for x in range(0, 60):
	  if mode:
            self.dut.sendPixel(0,0,100)
          else:
            self.dut.sendPixel(0,0,0)
        pinStates = self.dut.show();

      if ord(pinStates[0]) == 0x07:
        found = True

      mode = not mode
      time.sleep(.5)
   
    self.assertTrue(found)
    self.stopMe = False


########NEW FILE########
__FILENAME__ = test_led_current
import time
import glob
import serial

import BlinkyTapeUnitTest
import TestRig
import UserInterface
import BlinkyTape
import DetectPlatform

class TestFunctionalTests(BlinkyTapeUnitTest.BlinkyTapeTestCase):
  def __init__(self, methodName):
    super(TestFunctionalTests, self).__init__(methodName)

  @classmethod
  def setUpClass(self):
    # TODO: Why can't access self.testRig from __init__ here?
    self.testRig = TestRig.testRig
    self.testRig.resetState()

    self.i = UserInterface.interface
    self.dut = BlinkyTape.BlinkyTape()

  @classmethod
  def tearDownClass(self):
    self.dut = None
    self.testRig.resetState()

  def setUp(self):
    self.stopMe = True

  def tearDown(self):
    if self.stopMe:
      self.Stop()

  def test_010_usbEnumeration(self):
    self.i.DisplayMessage("Waiting for device to enumerate on USB...")

    MAX_ENUMERATION_TIME_S = 5
    platform = DetectPlatform.detectPlatform()
    if platform == 'Darwin':
      SERIAL_DEVICE_PATH = "/dev/cu.usbmodem*"
    else:
      # TODO: linux?
      SERIAL_DEVICE_PATH = "/dev/cu.usbmodem*"

    # Scan for all connected devices; platform dependent
    originalPorts = set(glob.glob(SERIAL_DEVICE_PATH))
 
    self.testRig.enableRelay('EN_USB_GND')
    self.testRig.enableRelay('EN_USB_VCC')
    self.testRig.enableRelay('EN_USB_DATA')

    # Wait for the device to enumerate
    startTime = time.time()
    while(time.time() < startTime + 5):
      finalPorts =set(glob.glob("/dev/cu.usbmodem*"))
      newPorts = finalPorts - originalPorts
      if len(newPorts) == 1:
        self.dut.port = list(newPorts)[0]
        break

    self.LogDataPoint("DUT Usb port:", self.dut.port)
    self.assertTrue(self.dut.port != '')
    self.stopMe = False

  def test_020_dutConnected(self):
    self.i.DisplayMessage("Connecting to DUT")

    connected = False
    try:
      self.dut.connect(self.dut.port)
    except serial.SerialException:
      pass
    else:
      connected = True

    self.assertTrue(connected)
    self.stopMe = False

  def test_030_stepGrayscaleBrightness(self):
    self.i.DisplayMessage("Measuring current for strip brightness 0-255")
    self.testRig.enableRelay('EN_LED_OUT')

    for bright in range(0,255):
      # TODO: Why send this twice?
      for j in range (0, 2):
        for x in range(0, 60):
          self.dut.sendPixel(bright,0,0)
        self.dut.show();
      current = self.testRig.measure('DUT_CURRENT')
      print bright, current

    self.stopMe = False


########NEW FILE########
__FILENAME__ = test_power_on
import time

import BlinkyTapeUnitTest
import TestRig
import UserInterface

class TestPowerOnTests(BlinkyTapeUnitTest.BlinkyTapeTestCase):
  def __init__(self, methodName):
    super(TestPowerOnTests, self).__init__(methodName)
    self.testRig = TestRig.testRig
    self.i = UserInterface.interface

  def setUp(self):
    self.stopMe = True

    self.testRig.resetState()

  def tearDown(self):
    self.testRig.resetState()

    if self.stopMe:
      self.Stop()


  def test_010_off_current(self):
    MIN_OFF_CURRENT = -1
    MAX_OFF_CURRENT = 2
    self.testRig.enableRelay('EN_USB_GND')
    time.sleep(.5)

    current = self.testRig.measure('DUT_CURRENT')

    self.i.DisplayMessage("Off current: %0.2f < %0.2f < %0.2f." % (MIN_OFF_CURRENT, current, MAX_OFF_CURRENT))
    self.StoreTestResultData("%0.2f" % current)

    result = current > MIN_OFF_CURRENT and current < MAX_OFF_CURRENT
    self.assertTrue(result)
    self.stopMe = False

  def test_020_limited_current(self):
    MIN_LIMITED_CURRENT = 5
    MAX_LIMITED_CURRENT = 35

    self.testRig.enableRelay('EN_USB_GND')
    self.testRig.enableRelay('EN_USB_VCC_LIMIT')
    time.sleep(.5)

    current = self.testRig.measure('DUT_CURRENT')

    self.i.DisplayMessage("Limited current: %0.2f < %0.2f < %0.2f." % (MIN_LIMITED_CURRENT, current, MAX_LIMITED_CURRENT))
    self.StoreTestResultData("%0.2f" % current)

    result = current > MIN_LIMITED_CURRENT and current < MAX_LIMITED_CURRENT
    self.assertTrue(result)
    self.stopMe = False

  def test_030_full_current(self):
    MIN_OPERATING_CURRENT = 10
    MAX_OPERATING_CURRENT = 40
 
    self.testRig.enableRelay('EN_USB_GND')
    self.testRig.enableRelay('EN_USB_VCC')
    time.sleep(.5)

    current = self.testRig.measure('DUT_CURRENT')

    self.i.DisplayMessage("Full current: %0.2f < %0.2f < %0.2f." % (MIN_OPERATING_CURRENT, current, MAX_OPERATING_CURRENT))
    self.StoreTestResultData("%0.2f" % current)

    result = current > MIN_OPERATING_CURRENT and current < MAX_OPERATING_CURRENT
    self.assertTrue(result)
    self.stopMe = False

########NEW FILE########
__FILENAME__ = test_short_test
import BlinkyTapeUnitTest
import UserInterface
import TestRig


class TestShortTests(BlinkyTapeUnitTest.BlinkyTapeTestCase):
  def __init__(self, methodName):
    super(TestShortTests, self).__init__(methodName)
    self.testRig = TestRig.testRig
    self.i = UserInterface.interface

  def setUp(self):
    self.stopMe = True

    self.testRig.resetState()

  def tearDown(self):
    self.testRig.resetState()

    if self.stopMe:
      self.Stop()

  def test_010_short_tests(self):
    """ Run the n*n test case """
    
    allFaults = []
    for pin in self.testRig.shortTestPins:
      self.i.DisplayMessage("testing pin %s..." % pin.name)

      faults = self.testRig.shortTest(pin.name)
      for fault in faults:
        self.i.DisplayMessage(fault)
      allFaults += faults

    self.assertEquals(len(allFaults), 0)
    self.stopMe = False

########NEW FILE########
__FILENAME__ = test_strip
# Note: the current sensor on this board is a little whack, and also it uses the wrong sense resistor,
# so these constants were adjusted accordingly.

import time
import serial

import BlinkyTapeUnitTest
import TestRig
import UserInterface
import BlinkyTape
import DetectPlatform

class TestFunctionalTests(BlinkyTapeUnitTest.BlinkyTapeTestCase):
  def __init__(self, methodName):
    super(TestFunctionalTests, self).__init__(methodName)

  @classmethod
  def setUpClass(self):
    # TODO: Why can't access self.testRig from __init__ here?
    self.testRig = TestRig.testRig
    self.testRig.resetState()

    self.i = UserInterface.interface
    self.dut = BlinkyTape.BlinkyTape()

    self.testRig.enableRelay("LED_B")

  @classmethod
  def tearDownClass(self):
    self.dut = None
    self.testRig.resetState()

  def setUp(self):
    self.stopMe = True

  def tearDown(self):
    if self.stopMe:
      self.Stop()

  def test_010_off_current(self):
    MIN_OFF_CURRENT = -1
    MAX_OFF_CURRENT = 2

    current = self.testRig.measure('DUT_CURRENT')

    self.i.DisplayMessage("Off current: %0.2f < %0.2f < %0.2f." % (MIN_OFF_CURRENT, current, MAX_OFF_CURRENT))
    self.StoreTestResultData("%0.2f" % current)

    result = current > MIN_OFF_CURRENT and current < MAX_OFF_CURRENT
    self.assertTrue(result)
    self.stopMe = False

  def test_020_limited_current(self):
    MIN_LIMITED_CURRENT = 200
    MAX_LIMITED_CURRENT = 500

    self.testRig.enableRelay('EN_USB_VCC_LIMIT')
    time.sleep(.5)

    current = self.testRig.measure('DUT_CURRENT')

    self.testRig.disableRelay('EN_USB_VCC_LIMIT')

    self.i.DisplayMessage("Limited current: %0.2f < %0.2f < %0.2f." % (MIN_LIMITED_CURRENT, current, MAX_LIMITED_CURRENT))
    self.StoreTestResultData("%0.2f" % current)

    result = current > MIN_LIMITED_CURRENT and current < MAX_LIMITED_CURRENT
    self.assertTrue(result)
    self.stopMe = False


  def test_040_usbEnumeration(self):
    self.i.DisplayMessage("Waiting for device to enumerate on USB...")

    MAX_ENUMERATION_TIME_S = 5
    # Scan for all connected devices; platform dependent
    originalPorts = set(DetectPlatform.ListSerialPorts())
 
    self.testRig.enableRelay('EN_USB_VCC')

    # Wait for the device to enumerate
    startTime = time.time()
    while(time.time() < startTime + 5):
      finalPorts = set(DetectPlatform.ListSerialPorts())
      newPorts = finalPorts - originalPorts
      if len(newPorts) == 1:
        self.dut.port = list(newPorts)[0]
        break

    self.LogDataPoint("DUT Usb port:", self.dut.port)
    self.assertTrue(self.dut.port != '')
    self.stopMe = False

  def test_050_dutConnected(self):
    self.i.DisplayMessage("Connecting to DUT")

    connected = False
    try:
      self.dut.connect(self.dut.port)
    except serial.SerialException:
      pass
    else:
      connected = True

    self.assertTrue(connected)
    self.stopMe = False

  def test_060_redLedsOnCurrent(self):
    self.i.DisplayMessage("Checking red LEDs on...")

    MIN_RED_CURRENT = 500
    MAX_RED_CURRENT = 10000
    # TODO: Why send this twice?
    for j in range (0, 2):
      for x in range(0, 60):
        self.dut.sendPixel(255,0,0)
      self.dut.show();

    current = self.testRig.measure('DUT_CURRENT')

    self.i.DisplayMessage("Red LEDs current: %0.2f < %0.2f < %0.2f." % (MIN_RED_CURRENT, current, MAX_RED_CURRENT))
    self.StoreTestResultData("%0.2f" % current)

    self.assertTrue(current > MIN_RED_CURRENT
                    and current < MAX_RED_CURRENT)
    self.stopMe = False

  def test_080_whiteLedsOnCurrent(self):
    self.i.DisplayMessage("Checking white LEDs on...")

    MIN_WHITE_CURRENT = 100
    MAX_WHITE_CURRENT = 30000
    # TODO: Why send this twice?
    for j in range (0, 2):
      for x in range(0, 60):
        self.dut.sendPixel(255,255,255)
      self.dut.show();

    current = self.testRig.measure('DUT_CURRENT')

    self.i.DisplayMessage("White LEDs current: %0.2f < %0.2f < %0.2f." % (MIN_WHITE_CURRENT, current, MAX_WHITE_CURRENT))
    self.StoreTestResultData("%0.2f" % current)

    self.assertTrue(current > MIN_WHITE_CURRENT
                    and current < MAX_WHITE_CURRENT)
    self.stopMe = False


  def test_100_button_connected(self):
    self.i.DisplayMessage("Checking button input works...")

    MAX_TIME_SECONDS = 30;

    startTime = time.time()
    found = False
    mode = True

    while((not found) and (time.time() < startTime + MAX_TIME_SECONDS)):
      pinStates = 0
      for j in range (0, 2):
        for x in range(0, 60):
	  if mode:
            self.dut.sendPixel(0,0,100)
          else:
            self.dut.sendPixel(0,0,0)
        pinStates = self.dut.show();

      if ord(pinStates[0]) == 0x07:
        found = True

      mode = not mode
      time.sleep(.5)
   
    self.assertTrue(found)
    self.stopMe = False


########NEW FILE########
__FILENAME__ = textrect
#! /usr/bin/env python

# From here:
# http://www.pygame.org/pcr/text_rect/index.php

class TextRectException:
    def __init__(self, message = None):
        self.message = message
    def __str__(self):
        return self.message

def render_textrect(string, font, rect, text_color, background_color, justification=0):
    """Returns a surface containing the passed text string, reformatted
    to fit within the given rect, word-wrapping as necessary. The text
    will be anti-aliased.

    Takes the following arguments:

    string - the text you wish to render. \n begins a new line.
    font - a Font object
    rect - a rectstyle giving the size of the surface requested.
    text_color - a three-byte tuple of the rgb value of the
                 text color. ex (0, 0, 0) = BLACK
    background_color - a three-byte tuple of the rgb value of the surface.
    justification - 0 (default) left-justified
                    1 horizontally centered
                    2 right-justified

    Returns the following values:

    Success - a surface object with the text rendered onto it.
    Failure - raises a TextRectException if the text won't fit onto the surface.
    """

    import pygame

    final_lines = []

    requested_lines = string.splitlines()

    # Create a series of lines that will fit on the provided
    # rectangle.

    for requested_line in requested_lines:
        if font.size(requested_line)[0] > rect.width:
            words = requested_line.split(' ')
            # if any of our words are too long to fit, return.
            for word in words:
                if font.size(word)[0] >= rect.width:
                    raise TextRectException, "The word " + word + " is too long to fit in the rect passed."
            # Start a new line
            accumulated_line = ""
            for word in words:
                test_line = accumulated_line + word + " "
                # Build the line while the words fit.    
                if font.size(test_line)[0] < rect.width:
                    accumulated_line = test_line
                else:
                    final_lines.append(accumulated_line)
                    accumulated_line = word + " "
            final_lines.append(accumulated_line)
        else:
            final_lines.append(requested_line)

    # Let's try to write the text out on the surface.

    surface = pygame.Surface(rect.size)
    surface.fill(background_color)

    accumulated_height = 0
    for line in final_lines:
        if accumulated_height + font.size(line)[1] >= rect.height:
            raise TextRectException, "Once word-wrapped, the text string was too tall to fit in the rect."
        if line != "":
            tempsurface = font.render(line, 1, text_color)
            if justification == 0:
                surface.blit(tempsurface, (0, accumulated_height))
            elif justification == 1:
                surface.blit(tempsurface, ((rect.width - tempsurface.get_width()) / 2, accumulated_height))
            elif justification == 2:
                surface.blit(tempsurface, (rect.width - tempsurface.get_width(), accumulated_height))
            else:
                raise TextRectException, "Invalid justification argument: " + str(justification)
        accumulated_height += font.size(line)[1]

    return surface


if __name__ == '__main__':
    import pygame
    import pygame.font
    from pygame.locals import *

    pygame.init()

    display = pygame.display.set_mode((400, 400))

    my_font = pygame.font.Font(None, 22)


########NEW FILE########
__FILENAME__ = UserInterface
import time
import pygame
import textrect
import TestRig
import RPi.GPIO as GPIO

class UserInterface():
  """
  The user interface is a simple class for displaying messages on the LCD screen,
  and reading input from the front keypad.
  """
  screen = None
  useFramebuffer = True
  usePi = True

  def __init__(self):
    self.rig = TestRig.testRig

    if(self.useFramebuffer):
      pygame.init()
      size=[320,240]
      self.screen=pygame.display.set_mode(size)
      pygame.mouse.set_visible(False)

      self.font = pygame.font.Font("FreeMono.ttf", 20)
      self.displayRect = pygame.Rect((0,0,320,240))

    if(self.usePi):
      GPIO.setmode(GPIO.BCM)
      GPIO.setup(23, GPIO.IN, pull_up_down = GPIO.PUD_UP)
   
  def DisplayFill(self, color):
    """
    Fill screen in a color
    @param color Fill color (RGB tuple)
    """
    self.screen.fill(color)
    pygame.display.flip()
    pass

  def DisplayMessage(self, message, color=(255,255,255), bgcolor=(0,0,0), boxed=False): 
    """
    Display a message on the screen
    @param message Message to display, can be multi-line
    @apram color Text color (RGB tuple)
    @param bgcolor Background color (RGB tuple)
    """
    if self.screen != None:
      self.screen.fill(bgcolor, self.displayRect)

      text = textrect.render_textrect(message,self.font,self.displayRect,color,bgcolor,0)
   
      self.screen.blit(text, self.displayRect.topleft)

      pygame.display.flip()

    if boxed:
      print "**********************************************************************"
      print ""
    print message
    if boxed:
      print ""
      print "**********************************************************************"

  def DisplayPass(self, message = 'PASS', timeout=0):
    """
    Display a pass message to the user, for a given amout of time.
    @param timeout Time to display the message, in seconds
    """
    self.DisplayMessage(message, color=(0,0,0), bgcolor=(0,255,0), boxed=True)
    time.sleep(timeout)

  def DisplayError(self, message = 'ERROR', timeout=1):
    """
    Display a failure message to the user, for a given amout of time.
    @param timeout Time to display the message, in seconds
    """
    self.DisplayMessage(message, color=(0,0,0), bgcolor=(255,0,0), boxed=True)
    
  def DisplayFail(self, message = 'FAIL', timeout=1):
    """
    Display a failure message to the user, for a given amout of time.
    @param timeout Time to display the message, in seconds
    """
    self.DisplayMessage(message, color=(0,0,0), bgcolor=(255,0,0), boxed=True)
    time.sleep(timeout)

  def Notify(self, message, color=(255,255,255), bgcolor=(0,0,0), strobe = False, strobeColor = (0,0,1)):
    """
    Display a message, then wait for user conformation
    To confirm that a message was received, press the right arrow key.
    @param message Messgae to display, can be multi-line
    """
    self.DisplayMessage(message, color, bgcolor, boxed=True)
    
#    pygame.event.clear()  # clear previous events
#    
#    while True:
#      for event in pygame.event.get(pygame.KEYUP):
#        if (event.key == pygame.K_RIGHT):
#          return 
    raw_input('Press return to continue')

  def StrobeInit(self, scMax = 10.0):
    self.sc = 0.0
    self.scDir = True
    self.scMax = scMax
  
  def UpdateStrobe(self, strobeColor):
    red = strobeColor[0] * (self.sc/self.scMax)
    green = strobeColor[1] * (self.sc/self.scMax)
    blue = strobeColor[2] * (self.sc/self.scMax)

    if self.scDir:
      self.sc += 1.0
    else:
      self.sc -= 1.0
    if self.sc > self.scMax:
      self.scDir = False
    elif self.sc < 0:
      self.scDir = True
      self.sc = 0.0

  def YesNo(self, message, color=(255,255,255), bgcolor=(0,0,0), strobe = False, strobeColor = (0,0,1)):
    """
    Display a question, then prompt user for yes/no response
    To select yes, press the right arrow key. To select down, press the
    down arrow key.
    @param message Messgae to display, can be multi-line
    @return true if yes was selected, false otherwise
    """
    self.DisplayMessage(message, color, bgcolor, boxed=True)

#    pygame.event.clear()  # clear previous events
#
#    while True:
#      for event in pygame.event.get(pygame.KEYUP):
#        if (event.key == pygame.K_RIGHT):
#          return True
#        if (event.key == pygame.K_UP):
#          return False
    s = ''
    while(s != 'y' and s != 'n'):
      s = raw_input('y for yes, n for no')
    return s == 'y'


# Declare a single instance of the user interface, that all modules can share
# TODO: This is so that new modules can be loaded dynamically and run, but there
# is probably a more elegent way to do this.
interface = UserInterface()

########NEW FILE########
