__FILENAME__ = brewpi
#!/usr/bin/python
# Copyright 2012 BrewPi
# This file is part of BrewPi.

# BrewPi is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# BrewPi is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with BrewPi.  If not, see <http://www.gnu.org/licenses/>.

import sys
# Check needed software dependencies to nudge users to fix their setup
if sys.version_info < (2, 7):
    print "Sorry, requires Python 2.7."
    sys.exit(1)

# standard libraries
import time
import socket
import os
import getopt
from pprint import pprint
import shutil
import traceback
import urllib

# load non standard packages, exit when they are not installed
try:
    import serial
except ImportError:
    print "BrewPi requires PySerial to run, please install it with 'sudo apt-get install python-serial"
    sys.exit(1)
try:
    import simplejson as json
except ImportError:
    print "BrewPi requires simplejson to run, please install it with 'sudo apt-get install python-simplejson"
    sys.exit(1)
try:
    from configobj import ConfigObj
except ImportError:
    print "BrewPi requires ConfigObj to run, please install it with 'sudo apt-get install python-configobj"
    sys.exit(1)


#local imports
import temperatureProfile
import programArduino as programmer
import brewpiJson
import BrewPiUtil as util
import brewpiVersion
import pinList
import expandLogMessage
import BrewPiProcess


# Settings will be read from Arduino, initialize with same defaults as Arduino
# This is mainly to show what's expected. Will all be overwritten on the first update from the arduino

compatibleHwVersion = "0.2.4"

# Control Settings
cs = dict(mode='b', beerSet=20.0, fridgeSet=20.0, heatEstimator=0.2, coolEstimator=5)

# Control Constants
cc = dict(tempFormat="C", tempSetMin=1.0, tempSetMax=30.0, pidMax=10.0, Kp=20.000, Ki=0.600, Kd=-3.000, iMaxErr=0.500,
          idleRangeH=1.000, idleRangeL=-1.000, heatTargetH=0.301, heatTargetL=-0.199, coolTargetH=0.199,
          coolTargetL=-0.301, maxHeatTimeForEst="600", maxCoolTimeForEst="1200", fridgeFastFilt="1", fridgeSlowFilt="4",
          fridgeSlopeFilt="3", beerFastFilt="3", beerSlowFilt="5", beerSlopeFilt="4", lah=0, hs=0)

# Control variables
cv = dict(beerDiff=0.000, diffIntegral=0.000, beerSlope=0.000, p=0.000, i=0.000, d=0.000, estPeak=0.000,
          negPeakEst=0.000, posPeakEst=0.000, negPeak=0.000, posPeak=0.000)

# listState = "", "d", "h", "dh" to reflect whether the list is up to date for installed (d) and available (h)
deviceList = dict(listState="", installed=[], available=[])

lcdText = ['Script starting up', ' ', ' ', ' ']


def logMessage(message):
    print >> sys.stderr, time.strftime("%b %d %Y %H:%M:%S   ") + message

# Read in command line arguments
try:
    opts, args = getopt.getopt(sys.argv[1:], "hc:sqkfld",
                               ['help', 'config=', 'status', 'quit', 'kill', 'force', 'log', 'dontrunfile', 'checkstartuponly'])
except getopt.GetoptError:
    print "Unknown parameter, available Options: --help, --config <path to config file>, " \
          "--status, --quit, --kill, --force, --log, --dontrunfile"
    sys.exit()

configFile = None
checkDontRunFile = False
checkStartupOnly = False
logToFiles = False
serialRestoreTimeOut = None  # used to temporarily increase the serial timeout

for o, a in opts:
    # print help message for command line options
    if o in ('-h', '--help'):
        print "\n Available command line options: "
        print "--help: print this help message"
        print "--config <path to config file>: specify a config file to use. When omitted settings/config.cf is used"
        print "--status: check which scripts are already running"
        print "--quit: ask all  instances of BrewPi to quit by sending a message to their socket"
        print "--kill: kill all instances of BrewPi by sending SIGKILL"
        print "--force: Force quit/kill conflicting instances of BrewPi and keep this one"
        print "--log: redirect stderr and stdout to log files"
        print "--dontrunfile: check dontrunfile in www directory and quit if it exists"
        print "--checkstartuponly: exit after startup checks, return 1 if startup is allowed"
        exit()
    # supply a config file
    if o in ('-c', '--config'):
        configFile = os.path.abspath(a)
        if not os.path.exists(configFile):
            sys.exit('ERROR: Config file "%s" was not found!' % configFile)
    # send quit instruction to all running instances of BrewPi
    if o in ('-s', '--status'):
        allProcesses = BrewPiProcess.BrewPiProcesses()
        allProcesses.update()
        running = allProcesses.as_dict()
        if running:
            pprint(running)
        else:
            print "No BrewPi scripts running"
        exit()
    # quit/kill running instances, then keep this one
    if o in ('-q', '--quit'):
        logMessage("Asking all BrewPi Processes to quit on their socket")
        allProcesses = BrewPiProcess.BrewPiProcesses()
        allProcesses.quitAll()
        time.sleep(2)
        exit()
    # send SIGKILL to all running instances of BrewPi
    if o in ('-k', '--kill'):
        logMessage("Killing all BrewPi Processes")
        allProcesses = BrewPiProcess.BrewPiProcesses()
        allProcesses.killAll()
        exit()
    # close all existing instances of BrewPi by quit/kill and keep this one
    if o in ('-f', '--force'):
        logMessage("Closing all existing processes of BrewPi and keeping this one")
        allProcesses = BrewPiProcess.BrewPiProcesses()
        if len(allProcesses.update()) > 1:  # if I am not the only one running
            allProcesses.quitAll()
            time.sleep(2)
            if len(allProcesses.update()) > 1:
                print "Asking the other processes to quit nicely did not work. Killing them with force!"
    # redirect output of stderr and stdout to files in log directory
    if o in ('-l', '--log'):
        logToFiles = True
    # only start brewpi when the dontrunfile is not found
    if o in ('-d', '--dontrunfile'):
        checkDontRunFile = True
    if o in ('--checkstartuponly'):
        checkStartupOnly = True

if not configFile:
    configFile = util.addSlash(sys.path[0]) + 'settings/config.cfg'

config = util.readCfgWithDefaults(configFile)

dontRunFilePath = config['wwwPath'] + 'do_not_run_brewpi'
# check dont run file when it exists and exit it it does
if checkDontRunFile:
    if os.path.exists(dontRunFilePath):
        # do not print anything, this will flood the logs
        exit(0)

# check for other running instances of BrewPi that will cause conflicts with this instance
allProcesses = BrewPiProcess.BrewPiProcesses()
allProcesses.update()
myProcess = allProcesses.me()
if allProcesses.findConflicts(myProcess):
    if not checkDontRunFile:
        logMessage("Another instance of BrewPi is already running, which will conflict with this instance. " +
                   "This instance will exit")
    exit(0)

if checkStartupOnly:
    exit(1)

localJsonFileName = ""
localCsvFileName = ""
wwwJsonFileName = ""
wwwCsvFileName = ""
lastDay = ""
day = ""

if logToFiles:
    logPath = util.addSlash(config['scriptPath']) + 'logs/'
    print logPath
    logMessage("Redirecting output to log files in %s, output will not be shown in console" % logPath)
    sys.stderr = open(logPath + 'stderr.txt', 'a', 0)  # append to stderr file, unbuffered
    sys.stdout = open(logPath + 'stdout.txt', 'w', 0)  # overwrite stdout file on script start, unbuffered


# userSettings.json is a copy of some of the settings that are needed by the web server.
# This allows the web server to load properly, even when the script is not running.
def changeWwwSetting(settingName, value):
    wwwSettingsFileName = util.addSlash(config['wwwPath']) + 'userSettings.json'
    if os.path.exists(wwwSettingsFileName):
        wwwSettingsFile = open(wwwSettingsFileName, 'r+b')
        try:
            wwwSettings = json.load(wwwSettingsFile)  # read existing settings
        except json.JSONDecodeError:
            logMessage("Error in decoding userSettings.json, creating new empty json file")
            wwwSettings = {}  # start with a fresh file when the json is corrupt.
    else:
        wwwSettingsFile = open(wwwSettingsFileName, 'w+b')  # create new file
        wwwSettings = {}

    wwwSettings[settingName] = str(value)
    wwwSettingsFile.seek(0)
    wwwSettingsFile.write(json.dumps(wwwSettings))
    wwwSettingsFile.truncate()
    wwwSettingsFile.close()

def setFiles():
    global config
    global localJsonFileName
    global localCsvFileName
    global wwwJsonFileName
    global wwwCsvFileName
    global lastDay
    global day

    # create directory for the data if it does not exist
    beerFileName = config['beerName']
    dataPath = util.addSlash(util.addSlash(config['scriptPath']) + 'data/' + beerFileName)
    wwwDataPath = util.addSlash(util.addSlash(config['wwwPath']) + 'data/' + beerFileName)

    if not os.path.exists(dataPath):
        os.makedirs(dataPath)
        os.chmod(dataPath, 0775)  # give group all permissions
    if not os.path.exists(wwwDataPath):
        os.makedirs(wwwDataPath)
        os.chmod(wwwDataPath, 0775)  # give group all permissions

    # Keep track of day and make new data file for each day
    day = time.strftime("%Y-%m-%d")
    lastDay = day
    # define a JSON file to store the data
    jsonFileName = beerFileName + '-' + day

    #if a file for today already existed, add suffix
    if os.path.isfile(dataPath + jsonFileName + '.json'):
        i = 1
        while os.path.isfile(dataPath + jsonFileName + '-' + str(i) + '.json'):
            i += 1
        jsonFileName = jsonFileName + '-' + str(i)

    localJsonFileName = dataPath + jsonFileName + '.json'
    brewpiJson.newEmptyFile(localJsonFileName)

    # Define a location on the web server to copy the file to after it is written
    wwwJsonFileName = wwwDataPath + jsonFileName + '.json'

    # Define a CSV file to store the data as CSV (might be useful one day)
    localCsvFileName = (dataPath + beerFileName + '.csv')
    wwwCsvFileName = (wwwDataPath + beerFileName + '.csv')

    # create new empty json file
    brewpiJson.newEmptyFile(localJsonFileName)

def startBeer(beerName):
    if config['dataLogging'] == 'active':
        setFiles()

    changeWwwSetting('beerName', beerName)


def startNewBrew(newName):
    global config
    if len(newName) > 1:     # shorter names are probably invalid
        config = util.configSet(configFile, 'beerName', newName)
        config = util.configSet(configFile, 'dataLogging', 'active')
        startBeer(newName)
        logMessage("Notification: Restarted logging for beer '%s'." % newName)
        return {'status': 0, 'statusMessage': "Successfully switched to new brew '%s'. " % urllib.unquote(newName) +
                                              "Please reload the page."}
    else:
        return {'status': 1, 'statusMessage': "Invalid new brew name '%s', "
                                              "please enter a name with at least 2 characters" % urllib.unquote(newName)}


def stopLogging():
    global config
    logMessage("Stopped data logging, as requested in web interface. " +
               "BrewPi will continue to control temperatures, but will not log any data.")
    config = util.configSet(configFile, 'beerName', None)
    config = util.configSet(configFile, 'dataLogging', 'stopped')
    changeWwwSetting('beerName', None)
    return {'status': 0, 'statusMessage': "Successfully stopped logging"}


def pauseLogging():
    global config
    logMessage("Paused logging data, as requested in web interface. " +
               "BrewPi will continue to control temperatures, but will not log any data until resumed.")
    if config['dataLogging'] == 'active':
        config = util.configSet(configFile, 'dataLogging', 'paused')
        return {'status': 0, 'statusMessage': "Successfully paused logging."}
    else:
        return {'status': 1, 'statusMessage': "Logging already paused or stopped."}


def resumeLogging():
    global config
    logMessage("Continued logging data, as requested in web interface.")
    if config['dataLogging'] == 'paused':
        config = util.configSet(configFile, 'dataLogging', 'active')
        return {'status': 0, 'statusMessage': "Successfully continued logging."}
    else:
        return {'status': 1, 'statusMessage': "Logging was not paused."}

port = config['port']
ser, conn = util.setupSerial(config)

logMessage("Notification: Script started for beer '" + urllib.unquote(config['beerName']) + "'")
# wait for 10 seconds to allow an Uno to reboot (in case an Uno is being used)
time.sleep(float(config.get('startupDelay', 10)))

ser.flush()

hwVersion = brewpiVersion.getVersionFromSerial(ser)
if hwVersion is None:
    logMessage("Warning: Cannot receive version number from Arduino. " +
               "Your Arduino is either not programmed or running a very old version of BrewPi. " +
               "Please upload a new version of BrewPi to your Arduino.")
    # script will continue so you can at least program the Arduino
    lcdText = ['Could not receive', 'version from Arduino', 'Please (re)program', 'your Arduino']
else:
    logMessage("Found " + hwVersion.toExtendedString() + \
               " on port " + port + "\n")
    if hwVersion.toString() != compatibleHwVersion:
        logMessage("Warning: BrewPi version compatible with this script is " +
                   compatibleHwVersion +
                   " but version number received is " + hwVersion.toString())
    if int(hwVersion.log) != int(expandLogMessage.getVersion()):
        logMessage("Warning: version number of local copy of logMessages.h " +
                   "does not match log version number received from Arduino." +
                   "Arduino version = " + str(hwVersion.log) +
                   ", local copy version = " + str(expandLogMessage.getVersion()))

if hwVersion is not None:
    ser.flush()
    # request settings from Arduino, processed later when reply is received
    ser.write('s')  # request control settings cs
    ser.write('c')  # request control constants cc
    # answer from Arduino is received asynchronously later.

# create a listening socket to communicate with PHP
is_windows = sys.platform.startswith('win')
useInetSocket = bool(config.get('useInetSocket', is_windows))
if useInetSocket:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    socketPort = config.get('socketPort', 6332)
    s.bind((config.get('socketHost', 'localhost'), int(socketPort)))
    logMessage('Bound to TCP socket on port %d ' % int(socketPort))
else:
    socketFile = util.addSlash(config['scriptPath']) + 'BEERSOCKET'
    if os.path.exists(socketFile):
    # if socket already exists, remove it
        os.remove(socketFile)
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(socketFile)  # Bind BEERSOCKET
    # set all permissions for socket
    os.chmod(socketFile, 0777)

serialCheckInterval = 0.5
s.setblocking(1)  # set socket functions to be blocking
s.listen(10)  # Create a backlog queue for up to 10 connections
# blocking socket functions wait 'serialCheckInterval' seconds
s.settimeout(serialCheckInterval)

prevDataTime = 0.0  # keep track of time between new data requests
prevTimeOut = time.time()

run = 1

startBeer(config['beerName'])
outputTemperature = True

prevTempJson = {
    "BeerTemp": 0,
    "FridgeTemp": 0,
    "BeerAnn": None,
    "FridgeAnn": None,
    "RoomTemp": None,
    "State": None,
    "BeerSet": 0,
    "FridgeSet": 0}


def renameTempKey(key):
    rename = {
        "bt": "BeerTemp",
        "bs": "BeerSet",
        "ba": "BeerAnn",
        "ft": "FridgeTemp",
        "fs": "FridgeSet",
        "fa": "FridgeAnn",
        "rt": "RoomTemp",
        "s": "State",
        "t": "Time"}
    return rename.get(key, key)

while run:
    if config['dataLogging'] == 'active':
        # Check whether it is a new day
        lastDay = day
        day = time.strftime("%Y-%m-%d")
        if lastDay != day:
            logMessage("Notification: New day, creating new JSON file.")
            setFiles()

    # Wait for incoming socket connections.
    # When nothing is received, socket.timeout will be raised after
    # serialCheckInterval seconds. Serial receive will be done then.
    # When messages are expected on serial, the timeout is raised 'manually'
    try:
        conn, addr = s.accept()
        conn.setblocking(1)
        # blocking receive, times out in serialCheckInterval
        message = conn.recv(4096)
        if "=" in message:
            messageType, value = message.split("=", 1)
        else:
            messageType = message
            value = ""
        if messageType == "ack":  # acknowledge request
            conn.send('ack')
        elif messageType == "lcd":  # lcd contents requested
            conn.send(json.dumps(lcdText))
        elif messageType == "getMode":  # echo cs['mode'] setting
            conn.send(cs['mode'])
        elif messageType == "getFridge":  # echo fridge temperature setting
            conn.send(str(cs['fridgeSet']))
        elif messageType == "getBeer":  # echo fridge temperature setting
            conn.send(str(cs['beerSet']))
        elif messageType == "getControlConstants":
            conn.send(json.dumps(cc))
        elif messageType == "getControlSettings":
            if cs['mode'] == "p":
                profileFile = util.addSlash(config['scriptPath']) + 'settings/tempProfile.csv'
                with file(profileFile, 'r') as prof:
                    cs['profile'] = prof.readline().split(",")[-1].rstrip("\n")
            cs['dataLogging'] = config['dataLogging']
            conn.send(json.dumps(cs))
        elif messageType == "getControlVariables":
            conn.send(json.dumps(cv))
        elif messageType == "refreshControlConstants":
            ser.write("c")
            raise socket.timeout
        elif messageType == "refreshControlSettings":
            ser.write("s")
            raise socket.timeout
        elif messageType == "refreshControlVariables":
            ser.write("v")
            raise socket.timeout
        elif messageType == "loadDefaultControlSettings":
            ser.write("S")
            raise socket.timeout
        elif messageType == "loadDefaultControlConstants":
            ser.write("C")
            raise socket.timeout
        elif messageType == "setBeer":  # new constant beer temperature received
            try:
                newTemp = float(value)
            except ValueError:
                logMessage("Cannot convert temperature '" + value + "' to float")
                continue
            if cc['tempSetMin'] <= newTemp <= cc['tempSetMax']:
                cs['mode'] = 'b'
                # round to 2 dec, python will otherwise produce 6.999999999
                cs['beerSet'] = round(newTemp, 2)
                ser.write("j{mode:b, beerSet:" + str(cs['beerSet']) + "}")
                logMessage("Notification: Beer temperature set to " +
                           str(cs['beerSet']) +
                           " degrees in web interface")
                raise socket.timeout  # go to serial communication to update Arduino
            else:
                logMessage("Beer temperature setting " + str(newTemp) +
                           " is outside of allowed range " +
                           str(cc['tempSetMin']) + " - " + str(cc['tempSetMax']) +
                           ". These limits can be changed in advanced settings.")
        elif messageType == "setFridge":  # new constant fridge temperature received
            try:
                newTemp = float(value)
            except ValueError:
                logMessage("Cannot convert temperature '" + value + "' to float")
                continue

            if cc['tempSetMin'] <= newTemp <= cc['tempSetMax']:
                cs['mode'] = 'f'
                cs['fridgeSet'] = round(newTemp, 2)
                ser.write("j{mode:f, fridgeSet:" + str(cs['fridgeSet']) + "}")
                logMessage("Notification: Fridge temperature set to " +
                           str(cs['fridgeSet']) +
                           " degrees in web interface")
                raise socket.timeout  # go to serial communication to update Arduino
            else:
                logMessage("Fridge temperature setting " + str(newTemp) +
                           " is outside of allowed range " +
                           str(cc['tempSetMin']) + " - " + str(cc['tempSetMax']) +
                           ". These limits can be changed in advanced settings.")
        elif messageType == "setOff":  # cs['mode'] set to OFF
            cs['mode'] = 'o'
            ser.write("j{mode:o}")
            logMessage("Notification: Temperature control disabled")
            raise socket.timeout
        elif messageType == "setParameters":
            # receive JSON key:value pairs to set parameters on the Arduino
            try:
                decoded = json.loads(value)
                ser.write("j" + json.dumps(decoded))
                if 'tempFormat' in decoded:
                    changeWwwSetting('tempFormat', decoded['tempFormat'])  # change in web interface settings too.
            except json.JSONDecodeError:
                logMessage("Error: invalid JSON parameter string received: " + value)
            raise socket.timeout
        elif messageType == "stopScript":  # exit instruction received. Stop script.
            # voluntary shutdown.
            # write a file to prevent the cron job from restarting the script
            logMessage("stopScript message received on socket. " +
                       "Stopping script and writing dontrunfile to prevent automatic restart")
            run = 0
            dontrunfile = open(dontRunFilePath, "w")
            dontrunfile.write("1")
            dontrunfile.close()
            continue
        elif messageType == "quit":  # quit instruction received. Probably sent by another brewpi script instance
            logMessage("quit message received on socket. Stopping script.")
            run = 0
            # Leave dontrunfile alone.
            # This instruction is meant to restart the script or replace it with another instance.
            continue
        elif messageType == "eraseLogs":
            # erase the log files for stderr and stdout
            open(util.scriptPath() + '/logs/stderr.txt', 'wb').close()
            open(util.scriptPath() + '/logs/stdout.txt', 'wb').close()
            logMessage("Fresh start! Log files erased.")
            continue
        elif messageType == "interval":  # new interval received
            newInterval = int(value)
            if 5 < newInterval < 5000:
                try:
                    config = util.configSet(configFile, 'interval', float(newInterval))
                except ValueError:
                    logMessage("Cannot convert interval '" + value + "' to float")
                    continue
                logMessage("Notification: Interval changed to " +
                           str(newInterval) + " seconds")
        elif messageType == "startNewBrew":  # new beer name
            newName = value
            result = startNewBrew(newName)
            conn.send(json.dumps(result))
        elif messageType == "pauseLogging":
            result = pauseLogging()
            conn.send(json.dumps(result))
        elif messageType == "stopLogging":
            result = stopLogging()
            conn.send(json.dumps(result))
        elif messageType == "resumeLogging":
            result = resumeLogging()
            conn.send(json.dumps(result))
        elif messageType == "dateTimeFormatDisplay":
            config = util.configSet(configFile, 'dateTimeFormatDisplay', value)
            changeWwwSetting('dateTimeFormatDisplay', value)
            logMessage("Changing date format config setting: " + value)
        elif messageType == "setActiveProfile":
            # copy the profile CSV file to the working directory
            logMessage("Setting profile '%s' as active profile" % value)
            config = util.configSet(configFile, 'profileName', value)
            changeWwwSetting('profileName', value)
            profileSrcFile = util.addSlash(config['wwwPath']) + "/data/profiles/" + value + ".csv"
            profileDestFile = util.addSlash(config['scriptPath']) + 'settings/tempProfile.csv'
            profileDestFileOld = profileDestFile + '.old'
            try:
                if os.path.isfile(profileDestFile):
                    if os.path.isfile(profileDestFileOld):
                        os.remove(profileDestFileOld)
                    os.rename(profileDestFile, profileDestFileOld)
                shutil.copy(profileSrcFile, profileDestFile)
                # for now, store profile name in header row (in an additional column)
                with file(profileDestFile, 'r') as original:
                    line1 = original.readline().rstrip("\n")
                    rest = original.read()
                with file(profileDestFile, 'w') as modified:
                    modified.write(line1 + "," + value + "\n" + rest)
            except IOError as e:  # catch all exceptions and report back an error
                conn.send("I/O Error(%d) updating profile: %s " % (e.errno, e.strerror))
            else:
                conn.send("Profile successfully updated")
                if cs['mode'] is not 'p':
                    cs['mode'] = 'p'
                    ser.write("j{mode:p}")
                    logMessage("Notification: Profile mode enabled")
                    raise socket.timeout  # go to serial communication to update Arduino
        elif messageType == "programArduino":
            ser.close()  # close serial port before programming
            del ser  # Arduino won't reset when serial port is not completely removed
            try:
                programParameters = json.loads(value)
                hexFile = programParameters['fileName']
                boardType = programParameters['boardType']
                restoreSettings = programParameters['restoreSettings']
                restoreDevices = programParameters['restoreDevices']
                programmer.programArduino(config, boardType, hexFile,
                                          {'settings': restoreSettings, 'devices': restoreDevices})
                logMessage("New program uploaded to Arduino, script will restart")
            except json.JSONDecodeError:
                logMessage("Error: cannot decode programming parameters: " + value)
                logMessage("Restarting script without programming.")

            # restart the script when done. This replaces this process with the new one
            time.sleep(5)  # give the Arduino time to reboot
            python = sys.executable
            os.execl(python, python, *sys.argv)
        elif messageType == "refreshDeviceList":
            deviceList['listState'] = ""  # invalidate local copy
            if value.find("readValues") != -1:
                ser.write("d{r:1}")  # request installed devices
                serialRestoreTimeOut = ser.getTimeout()
                ser.setTimeout(2)  # set timeOut to 2 seconds because retreiving values takes a while
                ser.write("h{u:-1,v:1}")  # request available, but not installed devices
            else:
                ser.write("d{}")  # request installed devices
                ser.write("h{u:-1}")  # request available, but not installed devices
        elif messageType == "getDeviceList":
            if deviceList['listState'] in ["dh", "hd"]:
                response = dict(board=hwVersion.board,
                                shield=hwVersion.shield,
                                deviceList=deviceList,
                                pinList=pinList.getPinList(hwVersion.board, hwVersion.shield))
                conn.send(json.dumps(response))
            else:
                conn.send("device-list-not-up-to-date")
        elif messageType == "applyDevice":
            try:
                configStringJson = json.loads(value)  # load as JSON to check syntax
            except json.JSONDecodeError:
                logMessage("Error: invalid JSON parameter string received: " + value)
                continue
            ser.write("U" + value)
            deviceList['listState'] = ""  # invalidate local copy
        else:
            logMessage("Error: Received invalid message on socket: " + message)

        if (time.time() - prevTimeOut) < serialCheckInterval:
            continue
        else:
            # raise exception to check serial for data immediately
            raise socket.timeout

    except socket.timeout:
        # Do serial communication and update settings every SerialCheckInterval
        prevTimeOut = time.time()

        if hwVersion is None:
            continue  # do nothing with the serial port when the arduino has not been recognized

        # request new LCD text
        ser.write('l')
        # request Settings from Arduino to stay up to date
        ser.write('s')

        # if no new data has been received for serialRequestInteval seconds
        if (time.time() - prevDataTime) >= float(config['interval']):
            ser.write("t")  # request new from arduino

        elif (time.time() - prevDataTime) > float(config['interval']) + 2 * float(config['interval']):
            #something is wrong: arduino is not responding to data requests
            logMessage("Error: Arduino is not responding to new data requests")

        for line in ser:  # read all lines on serial interface
            try:
                if line[0] == 'T':
                    # print it to stdout
                    if outputTemperature:
                        print time.strftime("%b %d %Y %H:%M:%S  ") + line[2:]

                    # store time of last new data for interval check
                    prevDataTime = time.time()

                    if config['dataLogging'] == 'paused' or config['dataLogging'] == 'stopped':
                        continue  # skip if logging is paused or stopped

                    # process temperature line
                    newData = json.loads(line[2:])
                    # copy/rename keys
                    for key in newData:
                        prevTempJson[renameTempKey(key)] = newData[key]

                    newRow = prevTempJson
                    # add to JSON file
                    brewpiJson.addRow(localJsonFileName, newRow)
                    # copy to www dir.
                    # Do not write directly to www dir to prevent blocking www file.
                    shutil.copyfile(localJsonFileName, wwwJsonFileName)
                    #write csv file too
                    csvFile = open(localCsvFileName, "a")
                    try:
                        lineToWrite = (time.strftime("%b %d %Y %H:%M:%S;") +
                                       str(newRow['BeerTemp']) + ';' +
                                       str(newRow['BeerSet']) + ';' +
                                       str(newRow['BeerAnn']) + ';' +
                                       str(newRow['FridgeTemp']) + ';' +
                                       str(newRow['FridgeSet']) + ';' +
                                       str(newRow['FridgeAnn']) + ';' +
                                       str(newRow['State']) + ';' +
                                       str(newRow['RoomTemp']) + '\n')
                        csvFile.write(lineToWrite)
                    except KeyError, e:
                        logMessage("KeyError in line from Arduino: %s" % str(e))

                    csvFile.close()
                    shutil.copyfile(localCsvFileName, wwwCsvFileName)

                elif line[0] == 'D':
                    # debug message received
                    try:
                        expandedMessage = expandLogMessage.expandLogMessage(line[2:])
                        logMessage("Arduino debug message: " + expandedMessage)
                    except Exception, e:  # catch all exceptions, because out of date file could cause errors
                        logMessage("Error while expanding log message '" + line[2:] + "'" + str(e))

                elif line[0] == 'L':
                    # lcd content received
                    lcdTextReplaced = line[2:].replace('\xb0', '&deg')  # replace degree sign with &deg
                    lcdText = json.loads(lcdTextReplaced)
                elif line[0] == 'C':
                    # Control constants received
                    cc = json.loads(line[2:])
                elif line[0] == 'S':
                    # Control settings received
                    cs = json.loads(line[2:])
                # do not print this to the log file. This is requested continuously.
                elif line[0] == 'V':
                    # Control settings received
                    cv = json.loads(line[2:])
                elif line[0] == 'N':
                    pass  # version number received. Do nothing, just ignore
                elif line[0] == 'h':
                    deviceList['available'] = json.loads(line[2:])
                    oldListState = deviceList['listState']
                    deviceList['listState'] = oldListState.strip('h') + "h"
                    logMessage("Available devices received: " + str(deviceList['available']))
                    if serialRestoreTimeOut:
                        ser.setTimeout(serialRestoreTimeOut)
                        serialRestoreTimeOut = None
                elif line[0] == 'd':
                    deviceList['installed'] = json.loads(line[2:])
                    oldListState = deviceList['listState']
                    deviceList['listState'] = oldListState.strip('d') + "d"
                    logMessage("Installed devices received: " + str(deviceList['installed']))
                elif line[0] == 'U':
                    logMessage("Device updated to: " + line[2:])
                else:
                    logMessage("Cannot process line from Arduino: " + line)
                # end or processing a line
            except json.decoder.JSONDecodeError, e:
                logMessage("JSON decode error: %s" % str(e))
                logMessage("Line received was: " + line)
            except UnicodeDecodeError as e:
                logMessage("Unicode decode error: %s" % str(e))
                logMessage("Line received was: " + line)

        # Check for update from temperature profile
        if cs['mode'] == 'p':
            newTemp = temperatureProfile.getNewTemp(config['scriptPath'])
            if newTemp != cs['beerSet']:
                cs['beerSet'] = newTemp
                if cc['tempSetMin'] < newTemp < cc['tempSetMax']:
                    # if temperature has to be updated send settings to arduino
                    ser.write("j{beerSet:" + str(cs['beerSet']) + "}")
                elif newTemp is None:
                    # temperature control disabled by profile
                    logMessage("Temperature control disabled by empty cell in profile.")
                    ser.write("j{beerSet:-99999}")  # send as high negative value that will result in INT_MIN on Arduino

    except socket.error as e:
        logMessage("Socket error(%d): %s" % (e.errno, e.strerror))
        traceback.print_exc()

if ser:
    ser.close()  # close port
if conn:
    conn.shutdown(socket.SHUT_RDWR)  # close socket
    conn.close()

########NEW FILE########
__FILENAME__ = brewpiJson
# Copyright 2012 BrewPi
# This file is part of BrewPi.

# BrewPi is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# BrewPi is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with BrewPi.  If not, see <http://www.gnu.org/licenses/>.

from datetime import datetime
import time
import os
import re

jsonCols = ("\"cols\":[" +
            "{\"type\":\"datetime\",\"id\":\"Time\",\"label\":\"Time\"}," +
            "{\"type\":\"number\",\"id\":\"BeerTemp\",\"label\":\"Beer temperature\"}," +
            "{\"type\":\"number\",\"id\":\"BeerSet\",\"label\":\"Beer setting\"}," +
            "{\"type\":\"string\",\"id\":\"BeerAnn\",\"label\":\"Beer Annotate\"}," +
            "{\"type\":\"number\",\"id\":\"FridgeTemp\",\"label\":\"Fridge temperature\"}," +
            "{\"type\":\"number\",\"id\":\"FridgeSet\",\"label\":\"Fridge setting\"}," +
            "{\"type\":\"string\",\"id\":\"FridgeAnn\",\"label\":\"Fridge Annotate\"}," +
            "{\"type\":\"number\",\"id\":\"RoomTemp\",\"label\":\"Room temp.\"}," +
            "{\"type\":\"number\",\"id\":\"State\",\"label\":\"State\"}" +
            "]")


def fixJson(j):
	j = re.sub(r"'{\s*?(|\w)", r'{"\1', j)
	j = re.sub(r"',\s*?(|\w)", r',"\1', j)
	j = re.sub(r"'(|\w)?\s*:", r'\1":', j)
	j = re.sub(r"':\s*(|\w*)\s*(|[,}])", r':"\1"\2', j)
	return j


def addRow(jsonFileName, row):
	jsonFile = open(jsonFileName, "r+")
	jsonFile.seek(-3, 2)  # Go insert point to add the last row
	ch = jsonFile.read(1)
	jsonFile.seek(0, os.SEEK_CUR)
	# when alternating between reads and writes, the file contents should be flushed, see
	# http://bugs.python.org/issue3207. This prevents IOError, Errno 0
	if ch != '[':
		# not the first item
		jsonFile.write(',')
	newRow = {}
	newRow['Time'] = datetime.today()

	# insert something like this into the file:
	# {"c":[{"v":"Date(2012,8,26,0,1,0)"},{"v":18.96},{"v":19.0},null,{"v":19.94},{"v":19.6},null]},
	jsonFile.write(os.linesep)
	jsonFile.write("{\"c\":[")
	now = datetime.now()
	jsonFile.write("{{\"v\":\"Date({y},{M},{d},{h},{m},{s})\"}},".format(
		y=now.year, M=(now.month - 1), d=now.day, h=now.hour, m=now.minute, s=now.second))
	if row['BeerTemp'] is None:
		jsonFile.write("null,")
	else:
		jsonFile.write("{\"v\":" + str(row['BeerTemp']) + "},")

	if row['BeerSet'] is None:
		jsonFile.write("null,")
	else:
		jsonFile.write("{\"v\":" + str(row['BeerSet']) + "},")

	if row['BeerAnn'] is None:
		jsonFile.write("null,")
	else:
		jsonFile.write("{\"v\":\"" + str(row['BeerAnn']) + "\"},")

	if row['FridgeTemp'] is None:
		jsonFile.write("null,")
	else:
		jsonFile.write("{\"v\":" + str(row['FridgeTemp']) + "},")

	if row['FridgeSet'] is None:
		jsonFile.write("null,")
	else:
		jsonFile.write("{\"v\":" + str(row['FridgeSet']) + "},")

	if row['FridgeAnn'] is None:
		jsonFile.write("null,")
	else:
		jsonFile.write("{\"v\":\"" + str(row['FridgeAnn']) + "\"},")

	if row['RoomTemp'] is None:
		jsonFile.write("null,")
	else:
		jsonFile.write("{\"v\":\"" + str(row['RoomTemp']) + "\"},")

	if row['State'] is None:
		jsonFile.write("null")
	else:
		jsonFile.write("{\"v\":\"" + str(row['State']) + "\"}")

	# rewrite end of json file
	jsonFile.write("]}]}")
	jsonFile.close()


def newEmptyFile(jsonFileName):
	jsonFile = open(jsonFileName, "w")
	jsonFile.write("{" + jsonCols + ",\"rows\":[]}")
	jsonFile.close()

########NEW FILE########
__FILENAME__ = BrewPiProcess
# Copyright 2013 BrewPi
# This file is part of BrewPi.

# BrewPi is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# BrewPi is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with BrewPi.  If not, see <http://www.gnu.org/licenses/>.


import pprint
import os
import sys
from time import sleep

try:
    import psutil
except ImportError:
    print "BrewPi requires psutil to run, please install it with 'sudo apt-get install python-psutil"
    sys.exit(1)

import BrewPiSocket
import BrewPiUtil as util


class BrewPiProcess:
    """
    This class represents a running BrewPi process.
    It allows other instances of BrewPi to see if there would be conflicts between them.
    It can also use the socket to send a quit signal or the pid to kill the other instance.
    """
    def __init__(self):
        self.pid = None  # pid of process
        self.cfg = None  # config file of process, full path
        self.port = None  # serial port the process is connected to
        self.sock = None  # BrewPiSocket object which the process is connected to

    def as_dict(self):
        """
        Returns: member variables as a dictionary
        """
        return self.__dict__

    def quit(self):
        """
        Sends a friendly quit message to this BrewPi process over its socket to aks the process to exit.
        """
        if self.sock is not None:
            conn = self.sock.connect()
            if conn:
                conn.send('quit')
                conn.close()  # do not shutdown the socket, other processes are still connected to it.
                print "Quit message sent to BrewPi instance with pid %s!" % self.pid
                return True
            else:
                print "Could not connect to socket of BrewPi process, maybe it just started and is not listening yet."
                print "Could not send quit message to BrewPi instance with pid %d!" % self.pid
                return False

    def kill(self):
        """
        Kills this BrewPiProcess with force, use when quit fails.
        """
        process = psutil.Process(self.pid)  # get psutil process my pid
        try:
            process.kill()
            print "SIGKILL sent to BrewPi instance with pid %d!" % self.pid
        except psutil.error.AccessDenied:
            print >> sys.stderr, "Cannot kill process %d, you need root permission to do that." % self.pid
            print >> sys.stderr, "Is the process running under the same user?"

    def conflict(self, otherProcess):
        if self.pid == otherProcess.pid:
            return 0  # this is me! I don't have a conflict with myself
        if otherProcess.cfg == self.cfg:
            print "Conflict: same config file as another BrewPi instance already running."
            return 1
        if otherProcess.port == self.port:
            print "Conflict: same serial port as another BrewPi instance already running."
            return 1
        if [otherProcess.sock.type, otherProcess.sock.file, otherProcess.sock.host, otherProcess.sock.port] == \
                [self.sock.type, self.sock.file, self.sock.host, self.sock.port]:
            print "Conflict: same socket as another BrewPi instance already running."
            return 1
        return 0


class BrewPiProcesses():
    """
    This class can get all running BrewPi instances on the system as a list of BrewPiProcess objects.
    """
    def __init__(self):
        self.list = []

    def update(self):
        """
        Update the list of BrewPi processes by receiving them from the system with psutil.
        Returns: list of BrewPiProcess objects
        """
        bpList = []
        matching = [p for p in psutil.process_iter() if any('python' in p.name and 'brewpi.py'in s for s in p.cmdline)]
        for p in matching:
            bp = self.parseProcess(p)
            bpList.append(bp)
        self.list = bpList
        return self.list

    def parseProcess(self, process):
        """
        Converts a psutil process into a BrewPiProcess object by parsing the config file it has been called with.
        Params: a psutil.Process object
        Returns: BrewPiProcess object
        """
        bp = BrewPiProcess()
        bp.pid = process._pid

        cfg = [s for s in process.cmdline if '.cfg' in s]  # get config file argument
        if cfg:
            cfg = cfg[0]  # add full path to config file
        bp.cfg = util.readCfgWithDefaults(cfg)

        bp.port = bp.cfg['port']
        bp.sock = BrewPiSocket.BrewPiSocket(bp.cfg)
        return bp

    def get(self):
        """
        Returns a non-updated list of BrewPiProcess objects
        """
        return self.list

    def me(self):
        """
        Get a BrewPiProcess object of the process this function is called from
        """
        myPid = os.getpid()
        myProcess = psutil.Process(myPid)
        return self.parseProcess(myProcess)

    def findConflicts(self, process):
        """
        Finds out if the process given as argument will conflict with other running instances of BrewPi

        Params:
        process: a BrewPiProcess object that will be compared with other running instances

        Returns:
        bool: True means there are conflicts, False means no conflict
        """
        for p in self.list:
            if process.pid == p.pid:  # skip the process itself
                continue
            elif process.conflict(p):
                return 1
        return 0

    def as_dict(self):
        """
        Returns the list of BrewPiProcesses as a list of dicts, except for the process calling this function
        """
        outputList = []
        myPid = os.getpid()
        self.update()
        for p in self.list:
            if p.pid == myPid:  # do not send quit message to myself
                continue
            outputList.append(p.as_dict())
        return outputList

    def __repr__(self):
        """
        Print BrewPiProcesses as a dict when passed to a print statement
        """
        return repr(self.as_dict())

    def quitAll(self):
        """
        Ask all running BrewPi processes to exit
        """
        myPid = os.getpid()
        self.update()
        for p in self.list:
            if p.pid == myPid:  # do not send quit message to myself
                continue
            else:
                p.quit()
    def stopAll(self, dontRunFilePath):
        """
        Ask all running Brewpi processes to exit, and prevent restarting by writing
        the do_not_run file
        """
        if not os.path.exists(dontRunFilePath):
            # if do not run file does not exist, create it
            dontrunfile = open(dontRunFilePath, "w")
            dontrunfile.write("1")
            dontrunfile.close()
        myPid = os.getpid()
        self.update()
        for p in self.list:
            if p.pid == myPid:  # do not send quit message to myself
                continue
            else:
                p.quit()

    def killAll(self):
        """
        Kill all running BrewPi processes with force by sending a sigkill signal.
        """
        myPid = os.getpid()
        self.update()
        for p in self.list:
            if p.pid == myPid:  # do not commit suicide
                continue
            else:
                p.kill()


def testKillAll():
    """
    Test function that prints the process list, sends a kill signal to all processes and prints the updated list again.
    """
    allScripts = BrewPiProcesses()
    allScripts.update()
    print ("Running instances of BrewPi before killing them:")
    pprint.pprint(allScripts)
    allScripts.killAll()
    allScripts.update()
    print ("Running instances of BrewPi before after them:")
    pprint.pprint(allScripts)


def testQuitAll():
    """
    Test function that prints the process list, sends a quit signal to all processes and prints the updated list again.
    """
    allScripts = BrewPiProcesses()
    allScripts.update()
    print ("Running instances of BrewPi before asking them to quit:")
    pprint.pprint(allScripts)
    allScripts.quitAll()
    sleep(2)
    allScripts.update()
    print ("Running instances of BrewPi after asking them to quit:")
    pprint.pprint(allScripts)

########NEW FILE########
__FILENAME__ = BrewPiSocket
# Copyright 2013 BrewPi
# This file is part of BrewPi.

# BrewPi is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# BrewPi is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with BrewPi.  If not, see <http://www.gnu.org/licenses/>.

import sys
import socket
import os
import BrewPiUtil as util

class BrewPiSocket:
	"""
	A wrapper class for the standard socket class.
	"""

	def __init__(self, cfg):
		""" Creates a BrewPi socket object and reads the settings from a BrewPi ConfigObj.
		Does not create a socket, just prepares the settings.

		Args:
		cfg: a ConfigObj object form a BrewPi config file
		"""

		self.type = 'f'  # default to file socket
		self.file = None
		self.host = 'localhost'
		self.port = None
		self.sock = 0

		isWindows = sys.platform.startswith('win')
		useInternetSocket = bool(cfg.get('useInternetSocket', isWindows))
		if useInternetSocket:
			self.port = cfg.get('socketPort', 6332)
			self.type = 'i'
		else:
			self.file = util.addSlash(cfg['scriptPath']) + 'BEERSOCKET'

	def __repr__(self):
		"""
		This special function ensures BrewPiSocket is printed as a dict of its member variables in print statements.
		"""
		return repr(self.__dict__)

	def create(self):
		""" Creates a socket socket based on the settings in the member variables and assigns it to self.sock
		This function deletes old sockets for file sockets, so do not use it to connect to a socket that is in use.
		"""
		if self.type == 'i':  # Internet socket
			self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
			self.sock.bind((self.host, self.port))
			util.logMessage('Bound to TCP socket on port %d ' % self.port)
		else:
			if os.path.exists(self.file):
				# if socket already exists, remove it. This prevents  errors when the socket is corrupt after a crash.
				os.remove(self.file)
			self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
			self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
			self.sock.bind(self.file)  # Bind BEERSOCKET
			# set all permissions for socket
			os.chmod(self.file, 0777)

	def connect(self):
		"""	Connect to the socket represented by BrewPiSocket. Returns a new connected socket object.
		This function should be called when the socket is created by a different instance of brewpi.
		"""
		sock = socket.socket
		try:
			if self.type == 'i':  # Internet socket
				sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
				sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
				util.logMessage('Bound to existing TCP socket on port %d ' % self.port)
				sock.connect((self.host, self.port))
			else:
				sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
				sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
				sock.connect(self.file)
		except socket.error:
			sock = False
		finally:
			return sock

	def listen(self):
		"""
		Start listing on the socket, with default settings for blocking/backlog/timeout
		"""
		self.sock.setblocking(1)  # set socket functions to be blocking
		self.sock.listen(10)  # Create a backlog queue for up to 10 connections
		self.sock.settimeout(0.1)  # set to block 0.1 seconds, for instance for reading from the socket

	def read(self):
		"""
		Accept a connection from the socket and reads the incoming message.

		Returns:
		conn: socket object when an incoming connection is accepted, otherwise returns False
		msgType: the type of the message received on the socket
		msg: the message body
		"""
		conn = False
		msgType = ""
		msg = ""
		try:
			conn, addr = self.sock.accept()
			message = conn.recv(4096)
			if "=" in message:
				msgType, msg = message.split("=", 1)
			else:
				msgType = message
		except socket.timeout:
			conn = False
		finally:
			return conn, msgType, msg


########NEW FILE########
__FILENAME__ = BrewPiUtil
# Copyright 2013 BrewPi
# This file is part of BrewPi.

# BrewPi is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# BrewPi is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with BrewPi.  If not, see <http://www.gnu.org/licenses/>.

import time
import sys
import os
import serial

try:
	import configobj
except ImportError:
	print "BrewPi requires ConfigObj to run, please install it with 'sudo apt-get install python-configobj"
	sys.exit(1)


def addSlash(path):
	"""
	Adds a slash to the path, but only when it does not already have a slash at the end
	Params: a string
	Returns: a string
	"""
	if not path.endswith('/'):
		path += '/'
	return path


def readCfgWithDefaults(cfg):
	"""
	Reads a config file with the default config file as fallback

	Params:
	cfg: string, path to cfg file
	defaultCfg: string, path to defaultConfig file.

	Returns:
	ConfigObj of settings
	"""
	defaultCfg = scriptPath() + '/settings/defaults.cfg'
	config = configobj.ConfigObj(defaultCfg)

	if cfg:
		try:
			userConfig = configobj.ConfigObj(cfg)
			config.merge(userConfig)
		except configobj.ParseError:
			logMessage("ERROR: Could not parse user config file %s" % cfg)
		except IOError:
			logMessage("Could not open user config file %s. Using only default config file" % cfg)
	return config


def configSet(configFile, settingName, value):
	if not os.path.isfile(configFile):
		logMessage("User config file %s does not exist yet, creating it..." % configFile)
	try:
		config = configobj.ConfigObj(configFile)
		config[settingName] = value
		config.write()
	except IOError as e:
		logMessage("I/O error(%d) while updating %s: %s " % (e.errno, configFile, e.strerror))
		logMessage("Probably your permissions are not set correctly. " +
		           "To fix this, run 'sudo sh /home/brewpi/fixPermissions.sh'")
	return readCfgWithDefaults(configFile)  # return updated ConfigObj


def logMessage(message):
	"""
	Prints a timestamped message to stderr
	"""
	print >> sys.stderr, time.strftime("%b %d %Y %H:%M:%S   ") + message


def scriptPath():
	"""
	Return the path of BrewPiUtil.py. __file__ only works in modules, not in the main script.
	That is why this function is needed.
	"""
	return os.path.dirname(__file__)

def removeDontRunFile(path='/var/www/do_not_run_brewpi'):
	if os.path.isfile(path):
		os.remove(path)
		print "BrewPi set to be automatically restarted by cron"
	else:
		print "File do_not_run_brewpi does not exist at "+path
	
def setupSerial(config):
    ser = None
    conn = None
    port = config['port']
    dumpSerial = config.get('dumpSerial', False)
    # open serial port
    try:
        ser = serial.Serial(port, 57600, timeout=0.1)  # use non blocking serial.
    except serial.SerialException as e:
        logMessage("Error opening serial port: %s. Trying alternative serial port %s." % (str(e), config['altport']))
        try:
            port = config['altport']
            ser = serial.Serial(port, 57600, timeout=0.1)  # use non blocking serial.
        except serial.SerialException as e:
            logMessage("Error opening alternative serial port: %s. Script will exit." % str(e))
            exit(1)

    # yes this is monkey patching, but I don't see how to replace the methods on a dynamically instantiated type any other way
    if dumpSerial:
        ser.readOriginal = ser.read
        ser.writeOriginal = ser.write

        def readAndDump(size=1):
            r = ser.readOriginal(size)
            sys.stdout.write(r)
            return r

        def writeAndDump(data):
            ser.writeOriginal(data)
            sys.stderr.write(data)
        ser.read = readAndDump
        ser.write = writeAndDump
    return ser, conn

########NEW FILE########
__FILENAME__ = brewpiVersion
# Copyright 2013 BrewPi
# This file is part of BrewPi.

# BrewPi is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# BrewPi is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with BrewPi.  If not, see <http://www.gnu.org/licenses/>.

import simplejson as json
import sys
import time

def getVersionFromSerial(ser):
    version = None
    retries = 0
    requestVersion = True
    startTime = time.time()
    while requestVersion:
        retry = True
        for line in ser:
            if line[0] == 'N':
                data = line.strip('\n')[2:]
                version = AvrInfo(data)
                requestVersion = False
                retry = False
                break
            if time.time() - startTime > ser.timeout:
                # have read entire buffer, now just reading data as it comes in. Break to prevent an endless loop.
                break

        if retry:
            ser.write('n')  # request version info
            time.sleep(1)
            retries += 1
            if retries > 15:
                break
    return version


class AvrInfo:
    """ Parses and stores the version and other compile-time details reported by the Arduino """
    version = "v"
    build = "n"
    simulator = "y"
    board = "b"
    shield = "s"
    log = "l"
    commit = "c"

    shield_revA = "revA"
    shield_revC = "revC"

    shields = {1: shield_revA, 2: shield_revC}

    board_leonardo = "leonardo"
    board_standard = "standard"
    board_mega = "mega"

    boards = {'l': board_leonardo, 's': board_standard, 'm': board_mega}

    def __init__(self, s=None):
        self.major = 0
        self.minor = 0
        self.revision = 0
        self.version = None
        self.build = 0
        self.commit = None
        self.simulator = False
        self.board = None
        self.shield = None
        self.log = 0
        self.parse(s)

    def parse(self, s):
        if s is None or len(s) == 0:
            pass
        else:
            s = s.strip()
            if s[0] == '{':
                self.parseJsonVersion(s)
            else:
                self.parseStringVersion(s)

    def parseJsonVersion(self, s):
        try:
            j = json.loads(s)
        except json.decoder.JSONDecodeError, e:
            print >> sys.stderr, "JSON decode error: %s" % str(e)
            print >> sys.stderr, "Could not parse version number: " + s
        except UnicodeDecodeError, e:
            print >> sys.stderr, "Unicode decode error: %s" % str(e)
            print >> sys.stderr, "Could not parse version number: " + s

        if AvrInfo.version in j:
            self.parseStringVersion(j[AvrInfo.version])
        if AvrInfo.simulator in j:
            self.simulator = j[AvrInfo.simulator] == 1
        if AvrInfo.board in j:
            self.board = AvrInfo.boards.get(j[AvrInfo.board])
        if AvrInfo.shield in j:
            self.shield = AvrInfo.shields.get(j[AvrInfo.shield])
        if AvrInfo.log in j:
            self.log = j[AvrInfo.log]
        if AvrInfo.build in j:
            self.build = j[AvrInfo.build]
        if AvrInfo.commit in j:
            self.commit = j[AvrInfo.commit]

    def parseStringVersion(self, s):
        s = s.strip()
        parts = [int(x) for x in s.split('.')]
        parts += [0] * (3 - len(parts))			# pad to 3
        self.major, self.minor, self.revision = parts[0], parts[1], parts[2]
        self.version = s

    def toString(self):
        return str(self.major) + "." + str(self.minor) + "." + str(self.revision)

    def toExtendedString(self):
        string = "BrewPi v" + self.toString()
        if self.commit:
            string += ", running commit " + str(self.commit)
        if self.build:
            string += " build " + str(self.build)
        if self.board:
            string += ", on an Arduino " + str(self.board)
        if self.shield:
            string += " with a " + str(self.shield) + " shield"
        if(self.simulator):
           string += ", running as simulator"
        return string


########NEW FILE########
__FILENAME__ = expandLogMessage
# Copyright 2012 BrewPi
# This file is part of BrewPi.

# BrewPi is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# BrewPi is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with BrewPi.  If not, see <http://www.gnu.org/licenses/>.

import brewpiJson
import simplejson as json
import parseEnum
import os

logMessagesFile = os.path.dirname(__file__) + '/LogMessages.h'

errorDict = parseEnum.parseEnumInFile(logMessagesFile, 'errorMessages')
infoDict = parseEnum.parseEnumInFile(logMessagesFile, 'infoMessages')
warningDict = parseEnum.parseEnumInFile(logMessagesFile, 'warningMessages')

def valToFunction(val):
	functions = ['None',  # 0
	             'Chamber Door',  # 1
	             'Chamber Heater',  # 2
	             'Chamber Cooler',  # 3
				 'Chamber Light',  # 4
				 'Chamber Temp',  # 5
				 'Room Temp',  # 6
				 'Chamber Fan',  # 7
				 'Chamber Reserved 1',  # 8
				 'Beer Temp',  # 9
				 'Beer Temperature 2',  # 10
				 'Beer Heater',  # 11
				 'Beer Cooler',  # 12
				 'Beer S.G.',  # 13
				 'Beer Reserved 1',  #14
				 'Beer Reserved 2']  #15
	if val < len(functions):
		return functions[val]
	else:
		return 'Unknown Device Function'


def getVersion():
	hFile = open(logMessagesFile)
	for line in hFile:
		if 'BREWPI_LOG_MESSAGES_VERSION ' in line:
			splitLine = line.split('BREWPI_LOG_MESSAGES_VERSION')
			return int(splitLine[1]) # return version number
	print "ERROR: could not find version number in log messages header file"
	return 0


def expandLogMessage(logMessageJsonString):
	expanded = ""
	logMessageJson = json.loads(logMessageJsonString)
	logId = int(logMessageJson['logID'])
	logType = logMessageJson['logType']
	values = logMessageJson['V']
	dict  = 0
	logTypeString = "**UNKNOWN MESSAGE TYPE**"
	if logType == "E":
		dict = errorDict
		logTypeString = "ERROR"
	elif logType == "W":
		dict = warningDict
		logTypeString = "WARNING"
	elif logType == "I":
		dict = infoDict
		logTypeString = "INFO MESSAGE"

	if logId in dict:
		expanded += logTypeString + " "
		expanded += str(logId) + ": "
		count = 0
		for v in values:
			try:
				if dict[logId]['paramNames'][count] == "config.deviceFunction":
					values[count] = valToFunction(v)
				elif dict[logId]['paramNames'][count] == "character":
					if values[count] == -1:
						# No character received
						values[count] = 'END OF INPUT'
					else:
						values[count] = chr(values[count])
			except IndexError:
				pass
			count += 1
		printString = dict[logId]['logString'].replace("%d", "%s").replace("%c", "%s")
		numVars = printString.count("%s")
		numReceived = len(values)
		if numVars == numReceived:
			expanded +=  printString % tuple(values)
		else:
			expanded += printString + "  | Number of arguments mismatch!, expected " + str(numVars) + "arguments, received " + str(values)
	else:
		expanded += logTypeString + " with unknown ID " + str(logId)

	return expanded

getVersion()

########NEW FILE########
__FILENAME__ = parseEnum
# Copyright 2012 BrewPi
# This file is part of BrewPi.

# BrewPi is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# BrewPi is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with BrewPi.  If not, see <http://www.gnu.org/licenses/>.

import re

def parseEnumInFile(hFilePath, enumName):
	messageDict = {}
	hFile = open(hFilePath)
	regex = re.compile("[A-Z]+\(([A-Za-z][A-Z0-9a-z_]*),\s*\"([^\"]*)\"((?:\s*,\s*[A-Za-z][A-Z0-9a-z_\.]*\s*)*)\)\s*,?")
	for line in hFile:
		if 'enum ' + enumName in line:
			break  # skip lines until enum open is encountered

	count = 0
	for line in hFile:
		if 'MSG(' in line:
			# print line
			# print regex
			# r = regex.search(str(line))
			groups = regex.findall(line)
			logKey = groups[0][0]
			logString = groups[0][1]
			paramNames = groups[0][2].replace(",", " ").split()
			messageDict[count] = {'logKey': logKey, 'logString': logString,'paramNames': paramNames}
			count += 1

		if 'END enum ' + enumName in line:
			break

	hFile.close()
	return messageDict


########NEW FILE########
__FILENAME__ = pinList
# Copyright 2013 BrewPi
# This file is part of BrewPi.

# BrewPi is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# BrewPi is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with BrewPi.  If not, see <http://www.gnu.org/licenses/>.

import simplejson as json


def getPinList(arduinoType, shieldType):
    if arduinoType == "leonardo" and shieldType == "revC":
        pinList = [{'val': 6, 'text': ' 6 (Act 1)', 'type': 'act'},
                   {'val': 5, 'text': ' 5 (Act 2)', 'type': 'act'},
                   {'val': 2, 'text': ' 2 (Act 3)', 'type': 'act'},
                   {'val': 23, 'text': 'A5 (Act 4)', 'type': 'act'},
                   {'val': 4, 'text': ' 4 (Door)', 'type': 'door'},
                   {'val': 22, 'text': 'A4 (OneWire)', 'type': 'onewire'},
                   {'val': 3, 'text': ' 3', 'type': 'beep'},
                   {'val': 7, 'text': ' 7', 'type': 'rotary'},
                   {'val': 8, 'text': ' 8', 'type': 'rotary'},
                   {'val': 9, 'text': ' 9', 'type': 'rotary'},
                   {'val': 10, ' text': '10', 'type': 'spi'},
                   {'val': 0, 'text': ' 0', 'type': 'free'},
                   {'val': 1, 'text': ' 1', 'type': 'free'},
                   {'val': 11, ' text': '11', 'type': 'free'},
                   {'val': 12, ' text': '12', 'type': 'free'},
                   {'val': 13, ' text': '13', 'type': 'free'},
                   {'val': 18, 'text': 'A0', 'type': 'free'},
                   {'val': 19, 'text': 'A1', 'type': 'free'},
                   {'val': 20, 'text': 'A2', 'type': 'free'},
                   {'val': 21, 'text': 'A3', 'type': 'free'}]
    elif arduinoType == "standard" and shieldType == "revC":
        pinList = [{'val': 6, 'text': ' 6 (Act 1)', 'type': 'act'},
                   {'val': 5, 'text': ' 5 (Act 2)', 'type': 'act'},
                   {'val': 2, 'text': ' 2 (Act 3)', 'type': 'act'},
                   {'val': 19, 'text': 'A5 (Act 4)', 'type': 'act'},
                   {'val': 4, 'text': ' 4 (Door)', 'type': 'door'},
                   {'val': 18, 'text': 'A4 (OneWire)', 'type': 'onewire'},
                   {'val': 3, 'text': ' 3', 'type': 'beep'},
                   {'val': 7, 'text': ' 7', 'type': 'rotary'},
                   {'val': 8, 'text': ' 8', 'type': 'rotary'},
                   {'val': 9, 'text': ' 9', 'type': 'rotary'},
                   {'val': 10, ' text': '10', 'type': 'spi'},
                   {'val': 11, ' text': '11', 'type': 'spi'},
                   {'val': 12, ' text': '12', 'type': 'spi'},
                   {'val': 13, ' text': '13', 'type': 'spi'},
                   {'val': 0, 'text': ' 0', 'type': 'serial'},
                   {'val': 1, 'text': ' 1', 'type': 'serial'},
                   {'val': 14, 'text': 'A0', 'type': 'free'},
                   {'val': 15, 'text': 'A1', 'type': 'free'},
                   {'val': 16, 'text': 'A2', 'type': 'free'},
                   {'val': 17, 'text': 'A3', 'type': 'free'}]
    elif arduinoType == "leonardo" and shieldType == "revA":
        pinList = [{'val': 6, 'text': '  6 (Cool)', 'type': 'act'},
                   {'val': 5, 'text': '  5 (Heat)', 'type': 'act'},
                   {'val': 4, 'text': ' 4 (Door)', 'type': 'door'},
                   {'val': 22, 'text': 'A4 (OneWire)', 'type': 'onewire'},
                   {'val': 23, 'text': 'A5 (OneWire1)', 'type': 'onewire'},
                   {'val': 3, 'text': ' 3', 'type': 'beep'},
                   {'val': 7, 'text': ' 7', 'type': 'rotary'},
                   {'val': 8, 'text': ' 8', 'type': 'rotary'},
                   {'val': 9, 'text': ' 9', 'type': 'rotary'},
                   {'val': 10, ' text': '10', 'type': 'spi'},
                   {'val': 0, 'text': ' 0', 'type': 'free'},
                   {'val': 1, 'text': ' 1', 'type': 'free'},
                   {'val': 2, 'text': '  2', 'type': 'free'},
                   {'val': 11, ' text': '11', 'type': 'free'},
                   {'val': 12, ' text': '12', 'type': 'free'},
                   {'val': 13, ' text': '13', 'type': 'free'},
                   {'val': 18, 'text': 'A0', 'type': 'free'},
                   {'val': 19, 'text': 'A1', 'type': 'free'},
                   {'val': 20, 'text': 'A2', 'type': 'free'},
                   {'val': 21, 'text': 'A3', 'type': 'free'}]
    elif arduinoType == "standard" and shieldType == "revA":
        pinList = [{'val': 6, 'text': '  6 (Cool)', 'type': 'act'},
                   {'val': 5, 'text': '  5 (Heat)', 'type': 'act'},
                   {'val': 4, 'text': ' 4 (Door)', 'type': 'door'},
                   {'val': 18, 'text': 'A4 (OneWire)', 'type': 'onewire'},
                   {'val': 19, 'text': 'A5 (OneWire1)', 'type': 'onewire'},
                   {'val': 3, 'text': ' 3', 'type': 'beep'},
                   {'val': 7, 'text': ' 7', 'type': 'rotary'},
                   {'val': 8, 'text': ' 8', 'type': 'rotary'},
                   {'val': 9, 'text': ' 9', 'type': 'rotary'},
                   {'val': 10, ' text': '10', 'type': 'spi'},
                   {'val': 11, ' text': '11', 'type': 'spi'},
                   {'val': 12, ' text': '12', 'type': 'spi'},
                   {'val': 13, ' text': '13', 'type': 'spi'},
                   {'val': 0, 'text': ' 0', 'type': 'serial'},
                   {'val': 1, 'text': ' 1', 'type': 'serial'},
                   {'val': 2, 'text': '  2', 'type': 'free'},
                   {'val': 14, 'text': 'A0', 'type': 'free'},
                   {'val': 15, 'text': 'A1', 'type': 'free'},
                   {'val': 16, 'text': 'A2', 'type': 'free'},
                   {'val': 17, 'text': 'A3', 'type': 'free'}]
    elif arduinoType == "leonardo" and shieldType == "diy":
        pinList = [{'val': 12, 'text': '  12 (Cool)', 'type': 'act'},
                   {'val': 13, 'text': '  13 (Heat)', 'type': 'act'},
                   {'val': 23, 'text': ' A5 (Door)', 'type': 'door'},
                   {'val': 10, 'text': '10 (OneWire)', 'type': 'onewire'},
                   {'val': 11, 'text': '11 (OneWire1)', 'type': 'onewire'},
                   {'val': 0, 'text': ' 0', 'type': 'rotary'},
                   {'val': 1, 'text': ' 1', 'type': 'rotary'},
                   {'val': 2, 'text': ' 2', 'type': 'rotary'},
                   {'val': 3, 'text': ' 3', 'type': 'display'},
                   {'val': 4, ' text': '4', 'type': 'display'},
                   {'val': 5, ' text': '5', 'type': 'display'},
                   {'val': 6, ' text': '6', 'type': 'display'},
                   {'val': 7, ' text': '7', 'type': 'display'},
                   {'val': 8, ' text': '8', 'type': 'display'},
                   {'val': 9, ' text': '9', 'type': 'display'},
                   {'val': 18, 'text': 'A0', 'type': 'free'},
                   {'val': 19, 'text': 'A1', 'type': 'free'},
                   {'val': 20, 'text': 'A2', 'type': 'free'},
                   {'val': 21, 'text': 'A3', 'type': 'free'},
                   {'val': 22, 'text': 'A4', 'type': 'free'}]
    else:
        print 'Unknown Arduino or board type'
        pinList = {}
    return pinList


def getPinListJson(arduinoType, shieldType):
    try:
        pinList = getPinList(arduinoType, shieldType)
        return json.dumps(pinList)
    except json.JSONDecodeError:
        print "Cannot process pin list JSON"
        return 0

def pinListTest():
    print getPinListJson("leonardo", "revC")
    print getPinListJson("standard", "revC")
    print getPinListJson("leonardo", "revA")
    print getPinListJson("standard", "revA")

# pinListTest()

########NEW FILE########
__FILENAME__ = programArduino
import os.path
# Copyright 2012 BrewPi/Elco Jacobs.
# This file is part of BrewPi.

# BrewPi is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# BrewPi is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with BrewPi.  If not, see <http://www.gnu.org/licenses/>.

import subprocess as sub
import serial
import time
import simplejson as json
import os
import brewpiVersion
import expandLogMessage
import settingRestore
from sys import stderr
import BrewPiUtil as util


def printStdErr(string):
    print >> stderr, string + '\n'


def fetchBoardSettings(boardsFile, boardType):
    boardSettings = {}
    for line in boardsFile:
        if line.startswith(boardType):
            setting = line.replace(boardType + '.', '', 1).strip()  # strip board name, period and \n
            [key, sign, val] = setting.rpartition('=')
            boardSettings[key] = val
    return boardSettings


def loadBoardsFile(arduinohome):
    return open(arduinohome + 'hardware/arduino/boards.txt', 'rb').readlines()


def openSerial(port, altport, baud, timeoutVal):
    # open serial port
    try:
        ser = serial.Serial(port, baud, timeout=timeoutVal)
        return [ser, port]
    except serial.SerialException as e:
        printStdErr("Error opening serial port: %s. Trying alternative serial port %s." % (str(e), altport))
        try:
            ser = serial.Serial(altport, baud, timeout=timeoutVal)
            return [ser, altport]
        except serial.SerialException as e:
            printStdErr("Error opening alternative serial port: %s. Script will exit." % str(e))
            return [None, None]


def programArduino(config, boardType, hexFile, restoreWhat):
    printStdErr("****    Arduino Program script started    ****")

    arduinohome = config.get('arduinoHome', '/usr/share/arduino/')  # location of Arduino sdk
    avrdudehome = config.get('avrdudeHome', arduinohome + 'hardware/tools/')  # location of avr tools
    avrsizehome = config.get('avrsizeHome', '')  # default to empty string because avrsize is on path
    avrconf = config.get('avrConf', avrdudehome + 'avrdude.conf')  # location of global avr conf

    boardsFile = loadBoardsFile(arduinohome)
    boardSettings = fetchBoardSettings(boardsFile, boardType)

    restoreSettings = False
    restoreDevices = False
    if 'settings' in restoreWhat:
        if restoreWhat['settings']:
            restoreSettings = True
    if 'devices' in restoreWhat:
        if restoreWhat['devices']:
            restoreDevices = True
    # Even when restoreSettings and restoreDevices are set to True here,
    # they might be set to false due to version incompatibility later

    printStdErr("Settings will " + ("" if restoreSettings else "not ") + "be restored" +
                (" if possible" if restoreSettings else ""))
    printStdErr("Devices will " + ("" if restoreDevices else "not ") + "be restored" +
                (" if possible" if restoreSettings else ""))

    ser, port = openSerial(config['port'], config['altport'], 57600, 0.2)
    if ser is None:
        printStdErr("Could not open serial port. Programming aborted.")
        return 0

    time.sleep(5)  # give the arduino some time to reboot in case of an Arduino UNO

    printStdErr("Checking old version before programming.")

    avrVersionOld = brewpiVersion.getVersionFromSerial(ser)
    if avrVersionOld is None:
        printStdErr(("Warning: Cannot receive version number from Arduino. " +
                     "Your Arduino is either not programmed yet or running a very old version of BrewPi. "
                     "Arduino will be reset to defaults."))
    else:
        printStdErr("Found " + avrVersionOld.toExtendedString() + \
                    " on port " + port + "\n")

    oldSettings = {}


    # request all settings from board before programming
    if avrVersionOld is not None:
        printStdErr("Requesting old settings from Arduino...")
        if avrVersionOld.minor > 1:  # older versions did not have a device manager
            ser.write("d{}")  # installed devices
            time.sleep(1)
        ser.write("c")  # control constants
        ser.write("s")  # control settings
        time.sleep(2)

        for line in ser:
            try:
                if line[0] == 'C':
                    oldSettings['controlConstants'] = json.loads(line[2:])
                elif line[0] == 'S':
                    oldSettings['controlSettings'] = json.loads(line[2:])
                elif line[0] == 'd':
                    oldSettings['installedDevices'] = json.loads(line[2:])

            except json.decoder.JSONDecodeError, e:
                printStdErr("JSON decode error: " + str(e))
                printStdErr("Line received was: " + line)

        oldSettingsFileName = 'oldAvrSettings-' + time.strftime("%b-%d-%Y-%H-%M-%S") + '.json'
        printStdErr("Saving old settings to file " + oldSettingsFileName)

        scriptDir = util.scriptPath()  # <-- absolute dir the script is in
        if not os.path.exists(scriptDir + '/settings/avr-backup/'):
            os.makedirs(scriptDir + '/settings/avr-backup/')

        oldSettingsFile = open(scriptDir + '/settings/avr-backup/' + oldSettingsFileName, 'wb')
        oldSettingsFile.write(json.dumps(oldSettings))

        oldSettingsFile.truncate()
        oldSettingsFile.close()

    printStdErr("Loading programming settings from board.txt")

    # parse the Arduino board file to get the right program settings
    for line in boardsFile:
        if line.startswith(boardType):
            # strip board name, period and \n
            setting = line.replace(boardType + '.', '', 1).strip()
            [key, sign, val] = setting.rpartition('=')
            boardSettings[key] = val

    printStdErr("Checking hex file size with avr-size...")

    # start programming the Arduino
    avrsizeCommand = avrsizehome + 'avr-size ' + "\"" + hexFile + "\""

    # check program size against maximum size
    p = sub.Popen(avrsizeCommand, stdout=sub.PIPE, stderr=sub.PIPE, shell=True)
    output, errors = p.communicate()
    if errors != "":
        printStdErr('avr-size error: ' + errors)
        return 0

    programSize = output.split()[7]
    printStdErr(('Program size: ' + programSize +
                 ' bytes out of max ' + boardSettings['upload.maximum_size']))

    # Another check just to be sure!
    if int(programSize) > int(boardSettings['upload.maximum_size']):
        printStdErr("ERROR: program size is bigger than maximum size for your Arduino " + boardType)
        return 0

    hexFileDir = os.path.dirname(hexFile)
    hexFileLocal = os.path.basename(hexFile)

    programCommand = (avrdudehome + 'avrdude' +
                      ' -F ' +  # override device signature check
                      ' -e ' +  # erase flash and eeprom before programming. This prevents issues with corrupted EEPROM
                      ' -p ' + boardSettings['build.mcu'] +
                      ' -c ' + boardSettings['upload.protocol'] +
                      ' -b ' + boardSettings['upload.speed'] +
                      ' -P ' + port +
                      ' -U ' + 'flash:w:' + "\"" + hexFileLocal + "\"" +
                      ' -C ' + avrconf)

    printStdErr("Programming Arduino with avrdude: " + programCommand)

    # open and close serial port at 1200 baud. This resets the Arduino Leonardo
    # the Arduino Uno resets every time the serial port is opened automatically
    ser.close()
    del ser  # Arduino won't reset when serial port is not completely removed
    if boardType == 'leonardo':
        ser, port = openSerial(config['port'], config['altport'], 1200, 0.2)
        if ser is None:
            printStdErr("Could not open serial port at 1200 baud to reset Arduino Leonardo")
            return 0

        ser.close()
        time.sleep(1)  # give the bootloader time to start up

    p = sub.Popen(programCommand, stdout=sub.PIPE, stderr=sub.PIPE, shell=True, cwd=hexFileDir)
    output, errors = p.communicate()

    # avrdude only uses stderr, append its output to the returnString
    printStdErr("result of invoking avrdude:\n" + errors)

    printStdErr("avrdude done!")

    printStdErr("Giving the Arduino a few seconds to power up...")
    countDown = 6
    while countDown > 0:
        time.sleep(1)
        countDown -= 1
        printStdErr("Back up in " + str(countDown) + "...")

    ser, port = openSerial(config['port'], config['altport'], 57600, 0.2)
    if ser is None:
        printStdErr("Error opening serial port after programming. Program script will exit. Settings are not restored.")
        return 0

    printStdErr("Now checking which settings and devices can be restored...")

    # read new version
    avrVersionNew = brewpiVersion.getVersionFromSerial(ser)
    if avrVersionNew is None:
        printStdErr(("Warning: Cannot receive version number from Arduino. " +
                     "Your Arduino is either not programmed yet or running a very old version of BrewPi. "
                     "Arduino will be reset to defaults."))
    else:
        printStdErr("Checking new version: Found " + avrVersionNew.toExtendedString() +
                    " on port " + port + "\n")

    printStdErr("Resetting EEPROM to default settings")
    ser.write('E')
    time.sleep(5)  # resetting EEPROM takes a while, wait 5 seconds
    while 1:  # read all lines on serial interface
        line = ser.readline()
        if line:  # line available?
            if line[0] == 'D':
                # debug message received
                try:
                    expandedMessage = expandLogMessage.expandLogMessage(line[2:])
                    printStdErr("Arduino debug message: " + expandedMessage)
                except Exception, e:  # catch all exceptions, because out of date file could cause errors
                    printStdErr("Error while expanding log message: " + str(e))
                    printStdErr("Arduino debug message was: " + line[2:])
        else:
            break

    if avrVersionNew is None:
        printStdErr(("Warning: Cannot receive version number from Arduino after programming. " +
                     "Something must have gone wrong. Restoring settings/devices settings failed.\n"))
        return 0
    if avrVersionOld is None:
        printStdErr("Could not receive version number from old board, " +
                    "No settings/devices are restored.")
        return 0

    if restoreSettings:
        printStdErr("Trying to restore compatible settings from " +
                    avrVersionOld.toString() + " to " + avrVersionNew.toString())
        settingsRestoreLookupDict = {}

        if avrVersionNew.toString() == avrVersionOld.toString():
            printStdErr("New version is equal to old version, restoring all settings")
            settingsRestoreLookupDict = "all"
        elif avrVersionNew.major == 0 and avrVersionNew.minor == 2:
            if avrVersionOld.major == 0:
                if avrVersionOld.minor == 0:
                    printStdErr("Could not receive version number from old board, " +
                                "resetting to defaults without restoring settings.")
                    restoreDevices = False
                    restoreSettings = False
                elif avrVersionOld.minor == 1:
                    # version 0.1.x, try to restore most of the settings
                    settingsRestoreLookupDict = settingRestore.keys_0_1_x_to_0_2_x
                    printStdErr("Settings can only be partially restored when going from 0.1.x to 0.2.x")
                    restoreDevices = False
                elif avrVersionOld.minor == 2:
                    # restore settings and devices
                    if avrVersionNew.revision == 0:
                        settingsRestoreLookupDict = settingRestore.keys_0_2_x_to_0_2_0
                    elif avrVersionNew.revision == 1:
                        settingsRestoreLookupDict = settingRestore.keys_0_2_x_to_0_2_1
                    elif avrVersionNew.revision == 2:
                        settingsRestoreLookupDict = settingRestore.keys_0_2_x_to_0_2_2
                    elif avrVersionNew.revision == 3:
                        settingsRestoreLookupDict = settingRestore.keys_0_2_x_to_0_2_3
                    elif avrVersionNew.revision == 4:
                        if avrVersionOld.revision >= 3:
                            settingsRestoreLookupDict = settingRestore.keys_0_2_3_to_0_2_4
                        else:
                            settingsRestoreLookupDict = settingRestore.keys_0_2_x_to_0_2_4


                    printStdErr("Will try to restore compatible settings")
        else:
            printStdErr("Sorry, settings can only be restored when updating to BrewPi 0.2.0 or higher")


        restoredSettings = {}
        ccOld = oldSettings['controlConstants']
        csOld = oldSettings['controlSettings']

        ccNew = {}
        csNew = {}
        tries = 0
        while ccNew == {} or csNew == {}:
            if ccNew == {}:
                ser.write('c')
                time.sleep(2)
            if csNew == {}:
                ser.write('s')
                time.sleep(2)
            for line in ser:
                try:
                    if line[0] == 'C':
                        ccNew = json.loads(line[2:])
                    elif line[0] == 'S':
                        csNew = json.loads(line[2:])
                    elif line[0] == 'D':
                        try:  # debug message received
                            expandedMessage = expandLogMessage.expandLogMessage(line[2:])
                            printStdErr(expandedMessage)
                        except Exception, e:  # catch all exceptions, because out of date file could cause errors
                            printStdErr("Error while expanding log message: " + str(e))
                            printStdErr("Arduino debug message: " + line[2:])
                except json.JSONDecodeError, e:
                        printStdErr("JSON decode error: " + str(e))
                        printStdErr("Line received was: " + line)
            else:
                tries += 1
                if tries > 5:
                    printStdErr("Could not receive all keys for settings to restore from Arduino")
                    break

        printStdErr("Trying to restore old control constants and settings")
        # find control constants to restore
        for key in ccNew.keys():  # for all new keys
            if settingsRestoreLookupDict == "all":
                restoredSettings[key] = ccOld[key]
            else:
                for alias in settingRestore.getAliases(settingsRestoreLookupDict, key):  # get valid aliases in old keys
                    if alias in ccOld.keys():  # if they are in the old settings
                        restoredSettings[key] = ccOld[alias]  # add the old setting to the restoredSettings

        # find control settings to restore
        for key in csNew.keys():  # for all new keys
            if settingsRestoreLookupDict == "all":
                restoredSettings[key] = csOld[key]
            else:
                for alias in settingRestore.getAliases(settingsRestoreLookupDict, key):  # get valid aliases in old keys
                    if alias in csOld.keys():  # if they are in the old settings
                        restoredSettings[key] = csOld[alias]  # add the old setting to the restoredSettings

        printStdErr("Restoring these settings: " + json.dumps(restoredSettings))

        for key in settingRestore.restoreOrder:
            if key in restoredSettings.keys():
                # send one by one or the arduino cannot keep up
                if restoredSettings[key] is not None:
                    command = "j{" + str(key) + ":" + str(restoredSettings[key]) + "}\n"
                    ser.write(command)
                    time.sleep(0.5)
                # read all replies
                while 1:
                    line = ser.readline()
                    if line:  # line available?
                        if line[0] == 'D':
                            try:  # debug message received
                                expandedMessage = expandLogMessage.expandLogMessage(line[2:])
                                printStdErr(expandedMessage)
                            except Exception, e:  # catch all exceptions, because out of date file could cause errors
                                printStdErr("Error while expanding log message: " + str(e))
                                printStdErr("Arduino debug message: " + line[2:])
                    else:
                        break

        printStdErr("restoring settings done!")
    else:
        printStdErr("No settings to restore!")

    if restoreDevices:
        printStdErr("Now trying to restore previously installed devices: " + str(oldSettings['installedDevices']))
        detectedDevices = None
        for device in oldSettings['installedDevices']:
            printStdErr("Restoring device: " + json.dumps(device))
            if "a" in device.keys(): # check for sensors configured as first on bus
                if(int(device['a'], 16) == 0 ):
                    printStdErr("OneWire sensor was configured to autodetect the first sensor on the bus, " +
                                "but this is no longer supported. " +
                                "We'll attempt to automatically find the address and add the sensor based on its address")
                    if detectedDevices is None:
                        ser.write("h{}")  # installed devices
                        time.sleep(1)
                        # get list of detected devices
                        for line in ser:
                            try:
                                if line[0] == 'h':
                                    detectedDevices = json.loads(line[2:])
                            except json.decoder.JSONDecodeError, e:
                                printStdErr("JSON decode error: " + str(e))
                                printStdErr("Line received was: " + line)
                    for detectedDevice in detectedDevices:
                        if device['p'] == detectedDevice['p']:
                            device['a'] = detectedDevice['a'] # get address from sensor that was first on bus

            ser.write("U" + json.dumps(device))

            time.sleep(3)  # give the Arduino time to respond

            # read log messages from arduino
            while 1:  # read all lines on serial interface
                line = ser.readline()
                if line:  # line available?
                    if line[0] == 'D':
                        try:  # debug message received
                            expandedMessage = expandLogMessage.expandLogMessage(line[2:])
                            printStdErr(expandedMessage)
                        except Exception, e:  # catch all exceptions, because out of date file could cause errors
                            printStdErr("Error while expanding log message: " + str(e))
                            printStdErr("Arduino debug message: " + line[2:])
                    elif line[0] == 'U':
                        printStdErr("Arduino reports: device updated to: " + line[2:])
                else:
                    break
        printStdErr("Restoring installed devices done!")
    else:
        printStdErr("No devices to restore!")

    printStdErr("****    Program script done!    ****")
    printStdErr("If you started the program script from the web interface, BrewPi will restart automatically")
    ser.close()
    return 1

########NEW FILE########
__FILENAME__ = programArduinoFirstTime
# Copyright 2012 BrewPi/Elco Jacobs.
# This file is part of BrewPi.

# BrewPi is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# BrewPi is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with BrewPi.  If not, see <http://www.gnu.org/licenses/>.

import os
import sys
from configobj import ConfigObj

import programArduino as programmer
import BrewPiUtil as util

# Read in command line arguments
if len(sys.argv) < 2:
	sys.exit('Usage: %s <config file full path>' % sys.argv[0])
if not os.path.exists(sys.argv[1]):
	sys.exit('ERROR: Config file "%s" was not found!' % sys.argv[1])

configFile = sys.argv[1]
config = ConfigObj(configFile)

# global variables, will be initialized by startBeer()
util.readCfgWithDefaults(configFile)

hexFile = config['wwwPath'] + 'uploads/brewpi-uno-revC.hex'
boardType = config['boardType']

result = programmer.programArduino(config, boardType, hexFile, {'settings': True, 'devices': True})

print result

########NEW FILE########
__FILENAME__ = settingRestore
# Copyright 2013 BrewPi
# This file is part of BrewPi.

# BrewPi is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# BrewPi is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with BrewPi.  If not, see <http://www.gnu.org/licenses/>.

restoreOrder = ("tempFormat", "tempSetMin", "tempSetMax",  # it is critical that these are applied first
                "pidMax", "Kp", "Ki", "Kd", "iMaxErr",
                "idleRangeH", "idleRangeL", "heatTargetH", "heatTargetL", "coolTargetH", "coolTargetL",
                "maxHeatTimeForEst", "maxCoolTimeForEst",
                "fridgeFastFilt", "fridgeSlowFilt", "fridgeSlopeFilt", "beerFastFilt", "beerSlowFilt",
                "beerSlopeFilt", "lah", "hs", "heatEst", "coolEst", "mode", "fridgeSet", "beerSet")

keys_0_1_x_to_0_2_x = [{'key': "mode", 'validAliases': ["mode"]},
                       {'key': "beerSet", 'validAliases': ["beerSet"]},
                       {'key': "fridgeSet", 'validAliases': ["fridgeSet"]},
                       {'key': "heatEst", 'validAliases': ["heatEst"]},
                       {'key': "coolEst", 'validAliases': ["coolEst"]},
                       {'key': "tempFormat", 'validAliases': ["tempFormat"]},
                       {'key': "tempSetMin", 'validAliases': ["tempSetMin"]},
                       {'key': "tempSetMax", 'validAliases': ["tempSetMax"]},
                       {'key': "pidMax", 'validAliases': []},
                       {'key': "Kp", 'validAliases': ["Kp"]},
                       {'key': "Ki", 'validAliases': ["Ki"]},
                       {'key': "Kd", 'validAliases': ["Kd"]},
                       {'key': "iMaxErr", 'validAliases': ["iMaxErr"]},
                       {'key': "idleRangeH", 'validAliases': ["idleRangeH"]},
                       {'key': "idleRangeL", 'validAliases': ["idleRangeL"]},
                       {'key': "heatTargetH", 'validAliases': ["heatTargetH"]},
                       {'key': "heatTargetL", 'validAliases': ["heatTargetL"]},
                       {'key': "coolTargetH", 'validAliases': ["coolTargetH"]},
                       {'key': "coolTargetL", 'validAliases': ["coolTargetL"]},
                       {'key': "maxHeatTimeForEst", 'validAliases': ["maxHeatTimeForEst"]},
                       {'key': "maxCoolTimeForEst", 'validAliases': ["maxCoolTimeForEst"]},
                       # Skip filters, these could mess things up when they are in the old format
                       {'key': "fridgeFastFilt", 'validAliases': []},
                       {'key': "fridgeSlowFilt", 'validAliases': []},
                       {'key': "fridgeSlopeFilt", 'validAliases': []},
                       {'key': "beerFastFilt", 'validAliases': []},
                       {'key': "beerSlowFilt", 'validAliases': []},
                       {'key': "beerSlopeFilt", 'validAliases': []},
                       {'key': "lah", 'validAliases': ["lah"]},
                       {'key': "hs", 'validAliases': ["hs"]}]

keys_0_2_x_to_0_2_0 = [{'key': "mode", 'validAliases': ["mode"]},
                       {'key': "beerSet", 'validAliases': ["beerSet"]},
                       {'key': "fridgeSet", 'validAliases': ["fridgeSet"]},
                       {'key': "heatEst", 'validAliases': ["heatEst"]},
                       {'key': "coolEst", 'validAliases': ["coolEst"]},
                       {'key': "tempFormat", 'validAliases': ["tempFormat"]},
                       {'key': "tempSetMin", 'validAliases': ["tempSetMin"]},
                       {'key': "tempSetMax", 'validAliases': ["tempSetMax"]},
                       {'key': "pidMax", 'validAliases': []},
                       {'key': "Kp", 'validAliases': ["Kp"]},
                       {'key': "Ki", 'validAliases': ["Ki"]},
                       {'key': "Kd", 'validAliases': ["Kd"]},
                       {'key': "iMaxErr", 'validAliases': ["iMaxErr"]},
                       {'key': "idleRangeH", 'validAliases': ["idleRangeH"]},
                       {'key': "idleRangeL", 'validAliases': ["idleRangeL"]},
                       {'key': "heatTargetH", 'validAliases': ["heatTargetH"]},
                       {'key': "heatTargetL", 'validAliases': ["heatTargetL"]},
                       {'key': "coolTargetH", 'validAliases': ["coolTargetH"]},
                       {'key': "coolTargetL", 'validAliases': ["coolTargetL"]},
                       {'key': "maxHeatTimeForEst", 'validAliases': ["maxHeatTimeForEst"]},
                       {'key': "maxCoolTimeForEst", 'validAliases': ["maxCoolTimeForEst"]},
                       {'key': "fridgeFastFilt", 'validAliases': ["fridgeFastFilt"]},
                       {'key': "fridgeSlowFilt", 'validAliases': ["fridgeSlowFilt"]},
                       {'key': "fridgeSlopeFilt", 'validAliases': ["fridgeSlopeFilt"]},
                       {'key': "beerFastFilt", 'validAliases': ["beerFastFilt"]},
                       {'key': "beerSlowFilt", 'validAliases': ["beerSlowFilt"]},
                       {'key': "beerSlopeFilt", 'validAliases': ["beerSlopeFilt"]},
                       {'key': "lah", 'validAliases': ["lah"]},
                       {'key': "hs", 'validAliases': ["hs"]}]

keys_0_2_x_to_0_2_2 = [{'key': "mode", 'validAliases': ["mode"]},
                       {'key': "beerSet", 'validAliases': ["beerSet"]},
                       {'key': "fridgeSet", 'validAliases': ["fridgeSet"]},
                       {'key': "heatEst", 'validAliases': ["heatEst"]},
                       {'key': "coolEst", 'validAliases': ["coolEst"]},
                       {'key': "tempFormat", 'validAliases': ["tempFormat"]},
                       {'key': "tempSetMin", 'validAliases': ["tempSetMin"]},
                       {'key': "tempSetMax", 'validAliases': ["tempSetMax"]},
                       {'key': "pidMax", 'validAliases': []},
                       {'key': "Kp", 'validAliases': ["Kp"]},
                       {'key': "Ki", 'validAliases': ["Ki"]},
                       {'key': "Kd", 'validAliases': ["Kd"]},
                       {'key': "iMaxErr", 'validAliases': ["iMaxErr"]},
                       {'key': "idleRangeH", 'validAliases': ["idleRangeH"]},
                       {'key': "idleRangeL", 'validAliases': ["idleRangeL"]},
                       {'key': "heatTargetH", 'validAliases': ["heatTargetH"]},
                       {'key': "heatTargetL", 'validAliases': ["heatTargetL"]},
                       {'key': "coolTargetH", 'validAliases': ["coolTargetH"]},
                       {'key': "coolTargetL", 'validAliases': ["coolTargetL"]},
                       {'key': "maxHeatTimeForEst", 'validAliases': ["maxHeatTimeForEst"]},
                       {'key': "maxCoolTimeForEst", 'validAliases': ["maxCoolTimeForEst"]},
                       {'key': "fridgeFastFilt", 'validAliases': ["fridgeFastFilt"]},
                       {'key': "fridgeSlowFilt", 'validAliases': ["fridgeSlowFilt"]},
                       {'key': "fridgeSlopeFilt", 'validAliases': ["fridgeSlopeFilt"]},
                       {'key': "beerFastFilt", 'validAliases': ["beerFastFilt"]},
                       {'key': "beerSlowFilt", 'validAliases': []},
                       {'key': "beerSlopeFilt", 'validAliases': []},
                       {'key': "lah", 'validAliases': ["lah"]},
                       {'key': "hs", 'validAliases': ["hs"]}]

keys_0_2_x_to_0_2_1 = keys_0_2_x_to_0_2_2

keys_0_2_x_to_0_2_3 = [{'key': "mode", 'validAliases': ["mode"]},
                       {'key': "beerSet", 'validAliases': ["beerSet"]},
                       {'key': "fridgeSet", 'validAliases': ["fridgeSet"]},
                       {'key': "heatEst", 'validAliases': ["heatEst"]},
                       {'key': "coolEst", 'validAliases': ["coolEst"]},
                       {'key': "tempFormat", 'validAliases': ["tempFormat"]},
                       {'key': "tempSetMin", 'validAliases': ["tempSetMin"]},
                       {'key': "tempSetMax", 'validAliases': ["tempSetMax"]},
                       {'key': "pidMax", 'validAliases': []},
                       {'key': "Kp", 'validAliases': ["Kp"]},
                       {'key': "Ki", 'validAliases': ["Ki"]},
                       {'key': "Kd", 'validAliases': ["Kd"]},
                       {'key': "iMaxErr", 'validAliases': ["iMaxErr"]},
                       {'key': "idleRangeH", 'validAliases': ["idleRangeH"]},
                       {'key': "idleRangeL", 'validAliases': ["idleRangeL"]},
                       {'key': "heatTargetH", 'validAliases': ["heatTargetH"]},
                       {'key': "heatTargetL", 'validAliases': ["heatTargetL"]},
                       {'key': "coolTargetH", 'validAliases': ["coolTargetH"]},
                       {'key': "coolTargetL", 'validAliases': ["coolTargetL"]},
                       {'key': "maxHeatTimeForEst", 'validAliases': ["maxHeatTimeForEst"]},
                       {'key': "maxCoolTimeForEst", 'validAliases': ["maxCoolTimeForEst"]},
                       {'key': "fridgeFastFilt", 'validAliases': ["fridgeFastFilt"]},
                       {'key': "fridgeSlowFilt", 'validAliases': ["fridgeSlowFilt"]},
                       {'key': "fridgeSlopeFilt", 'validAliases': ["fridgeSlopeFilt"]},
                       {'key': "beerFastFilt", 'validAliases': ["beerFastFilt"]},
                       {'key': "beerSlowFilt", 'validAliases': []},
                       {'key': "beerSlopeFilt", 'validAliases': []},
                       {'key': "lah", 'validAliases': ["lah"]},
                       {'key': "hs", 'validAliases': ["hs"]}]

keys_0_2_x_to_0_2_4 = [{'key': "mode", 'validAliases': ["mode"]},
                       {'key': "beerSet", 'validAliases': ["beerSet"]},
                       {'key': "fridgeSet", 'validAliases': ["fridgeSet"]},
                       {'key': "heatEst", 'validAliases': ["heatEst"]},
                       {'key': "coolEst", 'validAliases': ["coolEst"]},
                       {'key': "tempFormat", 'validAliases': ["tempFormat"]},
                       {'key': "tempSetMin", 'validAliases': ["tempSetMin"]},
                       {'key': "tempSetMax", 'validAliases': ["tempSetMax"]},
                       {'key': "pidMax", 'validAliases': []},
                       {'key': "Kp", 'validAliases': ["Kp"]},
                       {'key': "Ki", 'validAliases': ["Ki"]},
                       {'key': "Kd", 'validAliases': ["Kd"]},
                       {'key': "iMaxErr", 'validAliases': ["iMaxErr"]},
                       {'key': "idleRangeH", 'validAliases': ["idleRangeH"]},
                       {'key': "idleRangeL", 'validAliases': ["idleRangeL"]},
                       {'key': "heatTargetH", 'validAliases': ["heatTargetH"]},
                       {'key': "heatTargetL", 'validAliases': ["heatTargetL"]},
                       {'key': "coolTargetH", 'validAliases': ["coolTargetH"]},
                       {'key': "coolTargetL", 'validAliases': ["coolTargetL"]},
                       {'key': "maxHeatTimeForEst", 'validAliases': ["maxHeatTimeForEst"]},
                       {'key': "maxCoolTimeForEst", 'validAliases': ["maxCoolTimeForEst"]},
                       {'key': "fridgeFastFilt", 'validAliases': ["fridgeFastFilt"]},
                       {'key': "fridgeSlowFilt", 'validAliases': ["fridgeSlowFilt"]},
                       {'key': "fridgeSlopeFilt", 'validAliases': ["fridgeSlopeFilt"]},
                       {'key': "beerFastFilt", 'validAliases': ["beerFastFilt"]},
                       {'key': "beerSlowFilt", 'validAliases': []},
                       {'key': "beerSlopeFilt", 'validAliases': []},
                       {'key': "lah", 'validAliases': ["lah"]},
                       {'key': "hs", 'validAliases': ["hs"]}]

keys_0_2_3_to_0_2_4 = [{'key': "mode", 'validAliases': ["mode"]},
                       {'key': "beerSet", 'validAliases': ["beerSet"]},
                       {'key': "fridgeSet", 'validAliases': ["fridgeSet"]},
                       {'key': "heatEst", 'validAliases': ["heatEst"]},
                       {'key': "coolEst", 'validAliases': ["coolEst"]},
                       {'key': "tempFormat", 'validAliases': ["tempFormat"]},
                       {'key': "tempSetMin", 'validAliases': ["tempSetMin"]},
                       {'key': "tempSetMax", 'validAliases': ["tempSetMax"]},
                       {'key': "pidMax", 'validAliases': []},
                       {'key': "Kp", 'validAliases': ["Kp"]},
                       {'key': "Ki", 'validAliases': ["Ki"]},
                       {'key': "Kd", 'validAliases': ["Kd"]},
                       {'key': "iMaxErr", 'validAliases': ["iMaxErr"]},
                       {'key': "idleRangeH", 'validAliases': ["idleRangeH"]},
                       {'key': "idleRangeL", 'validAliases': ["idleRangeL"]},
                       {'key': "heatTargetH", 'validAliases': ["heatTargetH"]},
                       {'key': "heatTargetL", 'validAliases': ["heatTargetL"]},
                       {'key': "coolTargetH", 'validAliases': ["coolTargetH"]},
                       {'key': "coolTargetL", 'validAliases': ["coolTargetL"]},
                       {'key': "maxHeatTimeForEst", 'validAliases': ["maxHeatTimeForEst"]},
                       {'key': "maxCoolTimeForEst", 'validAliases': ["maxCoolTimeForEst"]},
                       {'key': "fridgeFastFilt", 'validAliases': ["fridgeFastFilt"]},
                       {'key': "fridgeSlowFilt", 'validAliases': ["fridgeSlowFilt"]},
                       {'key': "fridgeSlopeFilt", 'validAliases': ["fridgeSlopeFilt"]},
                       {'key': "beerFastFilt", 'validAliases': ["beerFastFilt"]},
                       {'key': "beerSlowFilt", 'validAliases': ["beerSlowFilt"]},
                       {'key': "beerSlopeFilt", 'validAliases': ["beerSlopeFilt"]},
                       {'key': "lah", 'validAliases': ["lah"]},
                       {'key': "hs", 'validAliases': ["hs"]}]


def getAliases(restoreDict, key):
    for keyDict in restoreDict:
        if keyDict['key'] == key:
            return keyDict['validAliases']
    return []

# defaults, will be overwritten
ccNew = {"tempFormat": "C", "tempSetMin": 1.0, "tempSetMax": 30.0, "pidMax": 10.0, "Kp": 5.000, "Ki": 0.25, "Kd": -1.500,
         "iMaxErr": 0.500, "idleRangeH": 1.000, "idleRangeL": -1.000, "heatTargetH": 0.301, "heatTargetL": -0.199,
         "coolTargetH": 0.199, "coolTargetL": -0.301, "maxHeatTimeForEst": "600", "maxCoolTimeForEst": "1200",
         "fridgeFastFilt": "1", "fridgeSlowFilt": "4", "fridgeSlopeFilt": "3", "beerFastFilt": "3", "beerSlowFilt": "5",
         "beerSlopeFilt": "4"}
ccOld = {"tempFormat": "C", "tempSetMin": 1.0, "tempSetMax": 30.0, "pidMax": 10.0, "Kp": 5.000, "Ki": 0.25, "Kd": -1.500,
         "iMaxErr": 0.500, "idleRangeH": 1.000, "idleRangeL": -1.000, "heatTargetH": 0.301, "heatTargetL": -0.199,
         "coolTargetH": 0.199, "coolTargetL": -0.301, "maxHeatTimeForEst": "600", "maxCoolTimeForEst": "1200",
         "fridgeFastFilt": "1", "fridgeSlowFilt": "4", "fridgeSlopeFilt": "3", "beerFastFilt": "3", "beerSlowFilt": "5",
         "beerSlopeFilt": "4"}
csNew = {"mode": "b", "beerSet": 20.00, "fridgeSet": 1.00, "heatEst": 0.199, "coolEst": 5.000}
csOld = {"mode": "b", "beerSet": 20.00, "fridgeSet": 1.00, "heatEst": 0.199, "coolEst": 5.000}
settingsRestoreLookupDict = keys_0_1_x_to_0_2_x

########NEW FILE########
__FILENAME__ = temperatureProfile
# Copyright 2012 BrewPi/Elco Jacobs.
# This file is part of BrewPi.

# BrewPi is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# BrewPi is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with BrewPi.  If not, see <http://www.gnu.org/licenses/>.

import time
import csv
import sys
import BrewPiUtil as util


# also defined in brewpi.py. TODO: move to shared import
def logMessage(message):
    print >> sys.stderr, time.strftime("%b %d %Y %H:%M:%S   ") + message


def getNewTemp(scriptPath):
    temperatureReader = csv.reader(	open(util.addSlash(scriptPath) + 'settings/tempProfile.csv', 'rb'),
                                    delimiter=',', quoting=csv.QUOTE_ALL)
    temperatureReader.next()  # discard the first row, which is the table header
    prevTemp = None
    nextTemp = None
    interpolatedTemp = -99
    prevDate = None
    nextDate = None


    now = time.mktime(time.localtime())  # get current time in seconds since epoch

    for row in temperatureReader:
        dateString = row[0]
        try:
            date = time.mktime(time.strptime(dateString, "%Y-%m-%dT%H:%M:%S"))
        except ValueError:
            continue  # skip dates that cannot be parsed

        try:
            temperature = float(row[1])
        except ValueError:
            if row[1].strip() == '':
                # cell is left empty, this is allowed to disable temperature control in part of the profile
                temperature = None
            else:
                # invalid number string, skip this row
                continue

        prevTemp = nextTemp
        nextTemp = temperature
        prevDate = nextDate
        nextDate = date
        timeDiff = now - nextDate
        if timeDiff < 0:
            if prevDate is None:
                interpolatedTemp = nextTemp  # first set point is in the future
                break
            else:
                if prevTemp is None or nextTemp is None:
                    # When the previous or next temperature is an empty cell, disable temperature control.
                    # This is useful to stop temperature control after a while or to not start right away.
                    interpolatedTemp = None
                else:
                    interpolatedTemp = ((now - prevDate) / (nextDate - prevDate) * (nextTemp - prevTemp) + prevTemp)
                    interpolatedTemp = round(interpolatedTemp, 2)
                break

    if interpolatedTemp == -99:  # all set points in the past
        interpolatedTemp = nextTemp

    return interpolatedTemp

########NEW FILE########
__FILENAME__ = loadBoardSettings
import os.path
# To change this template, choose Tools | Templates
# and open the template in the editor.

from programArduino import fetchBoardSettings
import os
import sys
import unittest
import programArduino
from configobj import ConfigObj


def loadDefaultConfig():
    currentScript = os.path.abspath( __file__ )
    currentDir = os.path.dirname(currentScript)
    configFile = os.path.abspath(currentDir + '/../settings/config.cfg')
    config = ConfigObj(configFile)
    return config

class  LoadBoardSettingsTestCase(unittest.TestCase):

    def setUp(self):
        self.config = loadDefaultConfig()
        self.boardsFile = programArduino.loadBoardsFile(self.config);
    #
    
    def test_loadBoardSettings_Leonardo(self):
        boardType = 'leonardo'
        self.assertBoardSettings(boardType, 28672);

    def test_loadBoardSettings_Mega2560(self):
        self.assertBoardSettings('mega2560', 258048)

    def assertBoardSettings(self, boardType, maxUploadSize):
        boardSettings = fetchBoardSettings(self.boardsFile, boardType);
        assert len(boardSettings) > 0
        self.assertEquals(int(boardSettings['upload.maximum_size']), maxUploadSize)


if __name__ == '__main__':
    unittest.main()


########NEW FILE########
__FILENAME__ = versionTest
__author__ = 'mat'

import unittest
from brewpiVersion import AvrInfo


class VersionTestCase(unittest.TestCase):
    def assertVersionEqual(self, v, major, minor, rev, versionString):
        self.assertEqual(major, v.major)
        self.assertEqual(minor, v.minor)
        self.assertEqual(rev, v.revision)
        self.assertEqual(versionString, v.version)

    def assertEmptyVersion(self, v):
        self.assertVersionEqual(v, 0, 0, 0, None)

    def newVersion(self):
        return AvrInfo()

    def test_instantiatedVersionIsEmpty(self):
        v = self.newVersion()
        self.assertEmptyVersion(v)

    def test_parseEmptyStringIsEmptyVersion(self):
        v = self.newVersion()
        v.parse("")
        self.assertEmptyVersion(v)

    def test_parseNoStringIsEmptyVersion(self):
        v = self.newVersion()
        s = None
        v.parse(s)
        self.assertEmptyVersion(v)

    def test_canParseStringVersion(self):
        v = self.newVersion()
        v.parse("0.1.0")
        self.assertVersionEqual(v, 0, 1, 0, "0.1.0")

    def test_canParseJsonVersion(self):
        v = self.newVersion()
        v.parse('{"v":"0.1.0"}')
        self.assertVersionEqual(v, 0, 1, 0, "0.1.0")

    def test_canParseJsonSimulatorEnabled(self):
        v = self.newVersion()
        v.parse('{"y":1}')
        self.assertEqual(v.simulator, True)

    def test_canParseJsonSimulatorDisabled(self):
        v = self.newVersion()
        v.parse('{"y":0}')
        self.assertEqual(v.simulator, False)

    def test_canParseShieldRevC(self):
        v = self.newVersion()
        v.parse('{"s":2}')
        self.assertEqual(v.shield, AvrInfo.shield_revC)

    def test_canParseBoardLeonardo(self):
        v = self.newVersion()
        v.parse('{"b":"l"}')
        self.assertEqual(v.board, AvrInfo.board_leonardo)

    def test_canParseBoardStandard(self):
        v = self.newVersion()
        v.parse('{"b":"s"}')
        self.assertEqual(v.board, AvrInfo.board_standard)

    def test_canParseAll(self):
        v = AvrInfo('{"v":"1.2.3","n":"99","c":"12345678", "b":"l", "y":0, "s":2 }')
        self.assertVersionEqual(v, 1, 2, 3, "1.2.3")
        self.assertEqual(v.build, "99")
        self.assertEqual(v.commit, "12345678")
        self.assertEqual(v.board, AvrInfo.board_leonardo)
        self.assertEqual(v.simulator, False)
        self.assertEqual(v.shield, AvrInfo.shield_revC)

    def test_canPrintExtendedVersionEmpty(self):
        v = AvrInfo("")
        self.assertEqual("BrewPi v0.0.0", v.toExtendedString());

    def test_canPrintExtendedVersionFull(self):
        v = AvrInfo('{"v":"1.2.3","c":"12345678", "b":"l", "y":1, "s":2 }')
        self.assertEqual('BrewPi v1.2.3, running commit 12345678, on an Arduino leonardo with a revC shield, running as simulator', v.toExtendedString());

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = testTerminal
# Copyright 2012 BrewPi
# This file is part of BrewPi.

# BrewPi is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# BrewPi is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with BrewPi.  If not, see <http://www.gnu.org/licenses/>.

import serial
import msvcrt
import sys
import os
import simplejson as json
import expandLogMessage
import BrewPiUtil as util

# Read in command line arguments
if len(sys.argv) < 2:
    print >> sys.stderr, 'Using default config path ./settings/config.cfg, to override use : %s <config file full path>' % sys.argv[0]
    configFile = util.addSlash(sys.path[0]) + 'settings/config.cfg'
else:
    configFile = sys.argv[1]

if not os.path.exists(configFile):
    sys.exit('ERROR: Config file "%s" was not found!' % configFile)

config = util.readCfgWithDefaults(configFile)

print "***** BrewPi Windows Test Terminal ****"
print "This simple Python script lets you send commands to the Arduino."
print "It also echoes everything the Arduino returns."
print "On known debug ID's in JSON format, it expands the messages to the full message"
print "press 's' to send a string to the Arduino, press 'q' to quit"

ser = 0

# open serial port
try:
    ser = serial.Serial(config['port'], 57600, timeout=1)
except serial.SerialException, e:
    print e
    exit()

while 1:
    if msvcrt.kbhit():
        received = msvcrt.getch()
        if received == 's':
            print "type the string you want to send to the Arduino: "
            userInput = raw_input()
            print "sending: " + userInput
            ser.write(userInput)
        elif received == 'q':
            ser.close()
            exit()

    line = ser.readline()
    if line:
        if(line[0]=='D'):
            try:
                decoded = json.loads(line[2:])
                print "debug message received: " + expandLogMessage.expandLogMessage(line[2:])
            except json.JSONDecodeError:
                # print line normally, is not json
                print "debug message received: " + line[2:]

        else:
            print line


########NEW FILE########
