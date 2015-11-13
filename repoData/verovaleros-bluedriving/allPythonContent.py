__FILENAME__ = bluedriving
#!/usr/bin/python
#  Copyright (C) 2009  Veronica Valeros, Juan Manuel Abrigo, Sebastian Garcia
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
#
# Author:
# Veronica Valeros vero.valeros@gmail.com
#
# Changelog
#  - Cache the requested coordinates and addresses to save bandwith
#  - Cache the device information to avoid extra queries to the database
#  - Updated README on the github wiki
#
# TODO
# When there is a communication error with the bluetooth device do not kill the thread and continue working.
# Check this: Fix crashing when multiple threads try to write in the database
# Redesign the whole program. 
#
# KNOWN BUGS
#
# Description
#

# standar imports
import sys
import re
import getopt
import copy
import os
import time
try:
    import sqlite3
except:
    print 'Library needed. apt-get install python-sqlite'
    exit(-1)
try:
    import bluetooth
except:
    print 'Library needed. apt-get install python-bluez'
    exit(-1)
import time
try:
    from gps import *;
except:
    print 'Library needed. apt-get install python-gps . Includes gpsd and gpsd-clients'
    exit(-1)
import threading
#import getCoordinatesFromAddress
from getCoordinatesFromAddress import getCoordinates
from bluedrivingWebServer import createWebServer
try:
    import lightblue
except:
    print 'Library needed. apt-get install python-lightblue'
    exit(-1)
import Queue
try:
    import pygame
except:
    print 'Library needed. apt-get install python-pygame'
    exit(-1)
import getpass
import smtplib

# Global variables
vernum = '0.1'
debug = False
verbose = False
threadbreak = False
global_location = ""
flag_sound = True
flag_internet = True
flag_gps = True
flag_lookup_services = True
flag_alarm = True
list_devices = {}
queue_devices = ""
mail_username = ""
mail_password = ""

address_cache = {}
deviceservices = {}

GRE='\033[92m'
END='\033[0m'
RED='\033[91m'
CYA='\033[96m'

# End global variables

def version():
    """
    This function prints information about this utility
    """
    global RED
    global END

    print RED
    print "   "+ sys.argv[0] + " Version "+ vernum +" @COPYLEFT"
    print "   Authors: Veronica Valeros (vero.valeros@gmail.com), Seba Garcia (eldraco@gmail.com)"
    print "   Contributors: nanojaus"
    print "   Bluedriving is a bluetooth wardriving utility."
    print 
    print END
 
def usage():
    """
    This function prints the posible options of this program.
    """
    global RED
    global END
    
    print RED
    print
    print "   "+ sys.argv[0] + " Version "+ vernum +" @COPYLEFT"
    print "   Authors: Veronica Valeros (vero.valeros@gmail.com), Seba Garcia (eldraco@gmail.com)"
    print "   Contributors: nanojaus"
    print "   Bluedriving is a bluetooth wardriving utility."
    print 
    print "\n   Usage: %s <options>" % sys.argv[0]
    print "   Options:"
    print "  \t-h, --help                           Show this help message and exit."
    print "  \t-D, --debug                          Debug mode ON. Prints debug information on the screen."
    print "  \t-d, --database-name                  Name of the database to store the data."
    print "  \t-w, --webserver                      It runs a local webserver to visualize and interact with "
    print "                                             the collected information. Defaults to port 8000."
    print "  \t-p, --webserver-port                 Port where the webserver is going to listen. Defaults to 8000."
    print "  \t-I, --webserver-ip                   IP address where the webserver binds. Defaults to 127.0.0.1."
    print "  \t-s, --not-sound                      Do not play the beautiful discovering sounds. Are you sure you wanna miss this?"
    print "  \t-i, --not-internet                   If you dont have internet use this option to save time while getting "
    print "                                             coordinates and addresses from the web."
    print "  \t-l, --not-lookup-services            Use this option to not lookup for services for each device. "
    print "                                             This option makes the discovering a little faster."
    print "  \t-g, --not-gps                        Use this option when you want to run the bluedriving withouth a gpsd connection."
    print "  \t-f, --fake-gps                       Use a fake gps position. Useful when you don't have a gps but know your location from google maps."
    print "                                             Example: -f '38.897388,-77.036543'"
    print "  \t-m, --mail-user                      Gmail user to send mails from and to when a mail alarm is found. The password is entered later."
    print "                                             Alarms can be set up only from the web interface at the moment."
    print 
    print END
 

def getGPS():
    """
    This functions gets the gps data from the gpsd session already started.
    """
    global debug
    global global_location
    global threadbreak

    counter = 0
    gps_session = ""
    gps_flag = False
    try:
        gps_session = gps(mode=WATCH_ENABLE)
        
        while not threadbreak:
            if counter > 10:
                global_location = ""
            try:
                location = gps_session.next()
                location['lon']
                location['lat']
                if global_location == "":
                    pygame.mixer.music.load('gps.ogg')
                    pygame.mixer.music.play()
                global_location = location
                counter = 0
                time.sleep(0.5)
            except:
                counter = counter + 1
                pass

    except KeyboardInterrupt:
        print 'Exiting received in getGPS() function. It may take a few seconds.'
        threadbreak = True
    except Exception as inst:
        print 'Exception getGPS() function.'
        threadbreak = True
        print 'Ending threads, exiting when finished'
        print type(inst) # the exception instance
        print inst.args # arguments stored in .args
        print inst # _str_ allows args to printed directly
        x, y = inst # _getitem_ allows args to be unpacked directly
        print 'x =', x
        print 'y =', y
        sys.exit(1)

def get_address_from_gps(location_gps):
    """
    This function gets an address from gps coordinates. 
    """
    global debug
    global verbose
    global address_cache
    global flag_internet
    global threadbreak
    
    coordinates = ""
    address = ""
    try:
        if location_gps:
            if debug:
                print 'Coordinates: {}'.format(location_gps)
            try:
                # If the location is already stored, we get it.
                address = address_cache[location_gps]
            except:
                if flag_internet:
                    # print location_gps
                    #[coordinates,address] = getCoordinatesFromAddress.getCoordinates(location_gps)
                    [coordinates,address] = getCoordinates(location_gps)
                    address = address.encode('utf-8')
                    if debug:
                        print 'Coordinates: {} Address: {}'.format(coordinates,address)
                    
                    address_cache[location_gps] = address
                else:
                    address = "Internet option deactivated"
        return address

    except KeyboardInterrupt:
        print 'Exiting received in get_address_from_gps(location_gps) function. It may take a few seconds.'
        threadbreak = True
    except Exception as inst:
        print 'Exception in get_address_from_gps(location_gps)'
        print 'Received coordinates: {}'.format(location_gps)
        print 'Retrieved coordinates: {}'.format(coordinates)
        print 'Retrieved Address: {}'.format(address)
        threadbreak = True
        print 'Ending threads, exiting when finished'
        print type(inst) # the exception instance
        print inst.args # arguments stored in .args
        print inst # _str_ allows args to printed directly
        x, y = inst # _getitem_ allows args to be unpacked directly
        print 'x =', x
        print 'y =', y
        sys.exit(1)

# Discovering function
def bluetooth_discovering():
    """
    This function performs a continue discovering of the nearby bluetooth devices. 
    It sends the list of devices to the lookupdevices function.
    """
    global debug
    global verbose
    global threadbreak
    global flag_sound
    global global_location

    try:
        if debug:
            print '# In bluetooth_discovering() function'
            print '# debug={0}'.format(debug)
            print '# verbose={0}'.format(verbose)
            print '# threadbreak={0}'.format(threadbreak)
            print '# flag_sound={0}'.format(flag_sound)
            print '# global_location={0}'.format(global_location)
            print
            
        counter=0
        while not threadbreak:
            data = ""

            try:
                if debug:
                    print '# In bluetooth_discovering() function'
                    print '# Discovering devices...'
                    print
                # Discovering devices
                data = bluetooth.bluez.discover_devices(duration=3,lookup_names=True)
                #data = bluetooth.discover_devices(duration=3,lookup_names=True)
                if debug:
                    print '# In bluetooth_discovering() function'
                    print '# Data retrieved: {}'.format(data)
                    print
                
                if data:
                    # If there is some data:
                    # We start a new thread that process the information retrieved 
                    loc = global_location
                    if debug:
                        print '# We start a new thread that process the information retrieved'
                        print '# loc={}'.format(loc)
                        print '# threading.Thread(None,target = process_devices,args=(data,loc))'
                        print '# process_device_information_thread.setDaemon(True)'
                        print
                    if verbose:
                        print 'Found: {} devices'.format(len(data))
                    process_device_information_thread = threading.Thread(None,target = process_devices,args=(data,loc))
                    process_device_information_thread.setDaemon(True)
                    process_device_information_thread.start()
                else: 
                    # If there is NO data:
                    # we print a dash and play a sound
                    print '  -'
                    if flag_sound:
                        if global_location:
                            # If we have gps, play a sound
                            pygame.mixer.music.load('nodevice-withgps.ogg')
                            pygame.mixer.music.play()
                        else:
                            if debug:
                                print 'No global location on discover_devices'
                                print global_location
                            # If we do not have gps, play a sound
                            pygame.mixer.music.load('nodevice-withoutgps.ogg')
                            pygame.mixer.music.play()
                counter=0
            except KeyboardInterrupt:
                print 'Exiting received in bluetooth_discovering() function, inside the while loop. It may take a few seconds.'
                threadbreak = True
            except:
                counter=counter+1
                if debug:
                    print 'An exception occured on the bluetooth_discovering() function. Trying to continue the scanning'
                if counter > 9000:
                    print 'Too many exceptions in bluetooth_discovering() function'
                    threadbreak = True
                    print 'Ending threads, exiting when finished'
                    print type(inst) # the exception instance
                    print inst.args # arguments stored in .args
                    print inst # _str_ allows args to printed directly
                    x, y = inst # _getitem_ allows args to be unpacked directly
                    print 'x =', x
                    print 'y =', y
                    sys.exit(1)


        threadbreak = True
        return True

    except KeyboardInterrupt:
        print 'Exiting received in bluetooth_discovering function. It may take a few seconds.'
        threadbreak = True
    except Exception as inst:
        print 'Exception in bluetooth_discovering() function'
        threadbreak = True
        print 'Ending threads, exiting when finished'
        print type(inst) # the exception instance
        print inst.args # arguments stored in .args
        print inst # _str_ allows args to printed directly
        x, y = inst # _getitem_ allows args to be unpacked directly
        print 'x =', x
        print 'y =', y
        sys.exit(1)

def process_devices(device_list,loc):
    """
    This function gets a list of discovered devices and gets it ready for storing on the database. The services discovering happens here.
    """
    global debug
    global verbose
    global threadbreak
    global flag_gps
    global flag_internet
    global flag_sound
    global list_devices
    global queue_devices

    location_gps = ""
    location_address = ""
    ftime = ""
    #this flag will help us identify if we found a new device or we already seen the device before.
    #with this we can play different sounds.
    flag_new_device = False
    try:
        if device_list:
            if debug:
                print '# In process_devices(device_list,loc) function'
                print '# device_list len={}'.format(len(device_list))
                print '# loc={}'.format(loc)
            # We process all devices retrieved in one run of the discovery function
            for d in device_list:
                flag_new_device = False
                try:
                    #if the device is on list devices, then we already see it.
                    list_devices[d[0]]
                    flag_new_device = False
                except:
                    #if the device is not in the list is a new device
                    list_devices[d[0]]=d[1]
                    flag_new_device = True
                    if debug:
                        print 'New device found'

                # We setup the timestamp
                ftime = time.strftime("%Y-%m-%d %H:%M:%S",time.localtime())

                # We get location's related information
                if flag_gps:
                    if debug:
                        print "# flag_gps={}".format(flag_gps)
                    try:
                        location_gps = str(loc.get('lat'))+","+str(loc.get('lon'))
                        if debug:
                            print "# location_gps={}".format(location_gps)
                        if flag_internet:
                            location_address = get_address_from_gps(location_gps)
                            if debug:
                                print "# location_address={}".format(location_gps)
                    except:
                        location_address=""
                        if debug:
                            print "# location_address={}".format(location_gps)
                else:
                    if loc:
                        location_gps=loc
                        if debug:
                            print "# flag_gps={}".format(flag_gps)
                            print "# location_gps={}".format(location_gps)
                        if flag_internet:
                            location_address = get_address_from_gps(location_gps)
                            if debug:
                                print "# location_address={}".format(location_gps)

                # We try to lookup more information about the device
                device_services = []
                if flag_lookup_services:
                    if debug:
                        print '# flag_lookup_services={}'.format(flag_lookup_services)
                    try:
                        services_data = lightblue.findservices(d[0])
                    except:
                        print 'Exception in process_devices, lightblue.findservices(d[0])'
                        services_data=[]
                    if services_data:
                        for i in services_data:
                            device_services.append(i[2])

                if len(device_services) > 1:
                    print '  {:<24}  {:<17}  {:<30}  {:<27}  {:<30}  {:<20}'.format(ftime,d[0],d[1],location_gps,location_address.split(',')[0],device_services[0])
                    for service in device_services[1:]:
                        print '  {:<24}  {:<17}  {:<30}  {:<27}  {:<30}  {:<20}'.format('','','','','',service)
                        #print '\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t{:<30}'.format(service)
                else:
                    print '  {:<24}  {:<17}  {:<30}  {:<27}  {:<30}  {:<20}'.format(ftime,d[0],d[1],location_gps,location_address.split(',')[0],device_services)
                    
                if flag_sound:
                    if flag_new_device:
                        pygame.mixer.music.load('new.ogg')
                        pygame.mixer.music.play()
                    else:
                        pygame.mixer.music.load('old.ogg')
                        pygame.mixer.music.play()

                queue_devices.put([ftime,d[0],d[1],location_gps,location_address,device_services])

                if debug:
                    print 'Data loaded to queue'
        # no devices?
        
    except KeyboardInterrupt:
        print 'Exiting. It may take a few seconds.'
        threadbreak = True
    except Exception as inst:
        print 'Exception in process_devices() function'
        threadbreak = True
        print 'Ending threads, exiting when finished'
        print type(inst) # the exception instance
        print inst.args # arguments stored in .args
        print inst # _str_ allows args to printed directly
        x, y = inst # _getitem_ allows args to be unpacked directly
        print 'x =', x
        print 'y =', y
        sys.exit(1)

def db_create_database(database_name):
    """
    This function creates a database for storing the data collected
    """
    global debug
    global verbose
    global threadbreak

    try:
        # We check if the database exists
        if not os.path.exists(database_name):
            if debug:
                print 'Creating database'
            # Creating database
            connection = sqlite3.connect(database_name)
            # Creating tables
            #connection.execute("CREATE TABLE Devices(Id INTEGER PRIMARY KEY AUTOINCREMENT, Mac TEXT , Info TEXT)")
            connection.execute("CREATE TABLE Devices(Id INTEGER PRIMARY KEY AUTOINCREMENT, Mac TEXT , Info TEXT, Vendor TEXT)")
            connection.execute("CREATE TABLE Locations(Id INTEGER PRIMARY KEY AUTOINCREMENT, MacId INTEGER, GPS TEXT, FirstSeen TEXT, LastSeen TEXT, Address TEXT, Name TEXT, UNIQUE(MacId,GPS))")
            connection.execute("CREATE TABLE Notes(Id INTEGER, Note TEXT)")
            connection.execute("CREATE TABLE Alarms(Id INTEGER, Alarm TEXT)")
            if debug:
                print 'Database created'
        else:
            if debug:
                print 'Database already exist'

    except KeyboardInterrupt:
        print 'Exiting. It may take a few seconds.'
        threadbreak = True
    except Exception as inst:
        print 'Exception in db_create_database(database_name) function'
        threadbreak = True
        print 'Ending threads, exiting when finished'
        print type(inst) # the exception instance
        print inst.args # arguments stored in .args
        print inst # _str_ allows args to printed directly
        x, y = inst # _getitem_ allows args to be unpacked directly
        print 'x =', x
        print 'y =', y
        sys.exit(1)

def db_get_database_connection(database_name):
    """
    This function creates a database connection and returns it
    """
    global debug
    global verbose
    global threadbreak

    try:
        if not os.path.exists(database_name):
            db_create_database(database_name)
        connection = sqlite3.connect(database_name)
        if debug:
            print 'Database connection retrieved'
        return connection

    except KeyboardInterrupt:
        print 'Exiting. It may take a few seconds.'
        threadbreak = True
    except Exception as inst:
        print 'Exception in get_database_connection(database_name) function'
        threadbreak = True
        print 'Ending threads, exiting when finished'
        print type(inst) # the exception instance
        print inst.args # arguments stored in .args
        print inst # _str_ allows args to printed directly
        x, y = inst # _getitem_ allows args to be unpacked directly
        print 'x =', x
        print 'y =', y
        sys.exit(1)

def db_get_device_id(connection,bdaddr,device_information):
    """
    Receives a device address and returns a device id from the database. If device does not exists in database, it adds it.
    """
    global debug
    global verbose
    global threadbreak

    try:
        mac_id = ""
        try:
            mac_id = connection.execute("SELECT Id FROM Devices WHERE Mac = \""+bdaddr+"\" limit 1")
            mac_id = mac_id.fetchall()

            if not mac_id:
                db_add_device(connection,bdaddr,device_information)
                mac_id = connection.execute("SELECT Id FROM Devices WHERE Mac = \""+bdaddr+"\" limit 1")
                mac_id = mac_id.fetchall()

            if debug:
                print 'Macid in db_get_device_id() function: {}'.format(mac_id)
            return mac_id[0][0]
        except:
            print 'Device Id could not be retrieved. BDADDR: {}'.format(bdaddr)
            return False

    except KeyboardInterrupt:
        print 'Exiting. It may take a few seconds.'
        threadbreak = True
    except Exception as inst:
        print 'Exception in db_get_device_id() function'
        threadbreak = True
        print 'Ending threads, exiting when finished'
        print type(inst) # the exception instance
        print inst.args # arguments stored in .args
        print inst # _str_ allows args to printed directly
        x, y = inst # _getitem_ allows args to be unpacked directly
        print 'x =', x
        print 'y =', y
        sys.exit(1)

def db_add_device(connection,bdaddr,device_information):
    """
    This function receives a db connection ,mac address and device information. It insert this information in the table Devices. If the mac is already there it will ignore it.
    """
    global debug
    global verbose
    global threadbreak

    try:
        try:
            connection.execute("INSERT OR IGNORE INTO Devices (Mac,Info) VALUES (?,?)",(bdaddr,repr(device_information)))
            connection.commit()
            if debug:
                print 'New device added'
            return True
        except:
            if debug:
                print 'Device already exists'
            return False
        
    except KeyboardInterrupt:
        print 'Exiting. It may take a few seconds.'
        threadbreak = True
    except Exception as inst:
        print 'Exception in db_add_device() function'
        threadbreak = True
        print 'Ending threads, exiting when finished'
        print type(inst) # the exception instance
        print inst.args # arguments stored in .args
        print inst # _str_ allows args to printed directly
        x, y = inst # _getitem_ allows args to be unpacked directly
        print 'x =', x
        print 'y =', y
        sys.exit(1)

def db_update_device(connection,device_id,device_information):
    """
    This function updates the Info field of the table devices with the new device information.
    """
    global debug
    global verbose
    global threadbreak

    try:
        try:
            connection.execute("UPDATE Devices SET Info=? WHERE Id=?", (repr(device_information), repr(device_id)))
            connection.commit()
            if debug:
                print 'Device information updated'
            return True
        except:
            if debug:
                print 'Device information not updated'
                print 'Device ID: {}'.format(device_id)
                print 'Device Information: {}'.format(device_information)
            return False

    except KeyboardInterrupt:
        print 'Exiting. It may take a few seconds.'
        threadbreak = True
    except Exception as inst:
        print 'Exception in db_update_device() function'
        threadbreak = True
        print 'Ending threads, exiting when finished'
        print type(inst) # the exception instance
        print inst.args # arguments stored in .args
        print inst # _str_ allows args to printed directly
        x, y = inst # _getitem_ allows args to be unpacked directly
        print 'x =', x
        print 'y =', y
        sys.exit(1)

def db_add_location(connection,device_id,location_gps,first_seen,location_address,device_name):
    """
    This function adds a new location to the Locations database
    """
    global debug
    global verbose
    global threadbreak

    try:
        try:
            connection.execute("INSERT INTO Locations(MacId, GPS, FirstSeen, LastSeen, Address, Name) VALUES (?, ?, ?, ?, ?, ?)",(int(device_id), repr(location_gps),repr(first_seen),repr(first_seen),repr(location_address),repr(device_name.replace("'","''"))))
            connection.commit()
            if debug:
                print 'Location added'
        except:
            if debug:
                print 'Location not added'
                print 'Device ID: {}'.format(device_id)
                print 'Device Name: {}'.format(device_name)
                print 'GPS Location: {}'.format(location_gps)
                print 'First seen: {}'.format(first_seen)
                print 'Last seen: {}'.format(first_seen)
            return False

    except KeyboardInterrupt:
        print 'Exiting. It may take a few seconds.'
        threadbreak = True
    except Exception as inst:
        print 'Exception in db_add_location() function'
        threadbreak = True
        print 'Ending threads, exiting when finished'
        print type(inst) # the exception instance
        print inst.args # arguments stored in .args
        print inst # _str_ allows args to printed directly
        x, y = inst # _getitem_ allows args to be unpacked directly
        print 'x =', x
        print 'y =', y
        sys.exit(1)

def db_update_location(connection,device_id,location_gps,first_seen):
    """
    This function updates the lastSeen time of the table Locations for a given macId.
    """
    global debug
    global verbose
    global threadbreak

    try:
        try:
            connection.execute("UPDATE Locations SET LastSeen=? WHERE MacId=? AND GPS=?",(repr(first_seen), int(device_id), repr(location_gps)))
            connection.commit()
            if debug:
                print 'Location updated'
                print 'Device ID: {}'.format(device_id)
                print 'GPS Location: {}'.format(location_gps)
                print 'Last seen: {}'.format(first_seen)
        except:
            if debug:
                print 'Location not updated'
                print 'Device ID: {}'.format(device_id)
                print 'GPS Location: {}'.format(location_gps)
                print 'Last seen: {}'.format(first_seen)
            return False

    except KeyboardInterrupt:
        print 'Exiting. It may take a few seconds.'
        threadbreak = True
    except Exception as inst:
        print 'Exception in db_update_location() function'
        threadbreak = True
        print 'Ending threads, exiting when finished'
        print type(inst) # the exception instance
        print inst.args # arguments stored in .args
        print inst # _str_ allows args to printed directly
        x, y = inst # _getitem_ allows args to be unpacked directly
        print 'x =', x
        print 'y =', y
        sys.exit(1)

def device_alert(device_id,device_name,database_name,location_gps,location_address,last_seen):
    """
    This function handles the alerts for devices already seen.
    """
    global debug
    global verbose
    global mail_username
    global mail_password
    global flag_internet

    try:
        connection = db_get_database_connection(database_name)
        result = connection.execute('select * from alarms where id = ?',(device_id,))
        data = result.fetchall()
        
        for alarm in data:
            if 'Sound' in alarm:
                pygame.mixer.music.load('alarm.ogg')
                pygame.mixer.music.play()
                break
            if 'Festival' in alarm:
                os.system("echo "+device_name+"|festival --tts")
                break
            if 'Mail' in alarm:
                if flag_internet:
                    fromaddr = mail_username+'@gmail.com'
                    toaddrs = mail_username+'@gmail.com'
                    msg = 'Device '+device_name+'\nLocation '+location_gps+'\nAddress '+location_address+'\nLast seen '+last_seen
                    server = smtplib.SMTP('smtp.gmail.com:587')
                    server.starttls()
                    server.login(mail_username,mail_password)
                    server.sendmail(fromaddr, toaddrs, msg)
                    server.quit()
                break
        connection.commit()
        connection.close()

    except KeyboardInterrupt:
        print 'Exiting. It may take a few seconds.'
        threadbreak = True
    except Exception as inst:
        print 'Exception in device_alert() function'
        threadbreak = True
        print 'Ending threads, exiting when finished'
        print type(inst) # the exception instance
        print inst.args # arguments stored in .args
        print inst # _str_ allows args to printed directly
        x, y = inst # _getitem_ allows args to be unpacked directly
        print 'x =', x
        print 'y =', y
        sys.exit(1)

def store_device_information(database_name):
    """
    This function handles the storage of the information collected by the bluetooth_discovering. The information is stored in the database.
    """
    global debug
    global verbose
    global queue_devices
    global threadbreak
    global flag_alarm

    connection = ""
    try:
        # We create a database connection
        connection = db_get_database_connection(database_name)
        while not threadbreak:
            while not queue_devices.empty():
                # We clear the variables to use
                device_id = ""
                device_bdaddr = ""
                device_name = ""
                device_information = ""
                location_gps = ""
                location_address = ""
                first_seen = ""
                last_seen = ""

                if not queue_devices.empty():
                    # We extract the device from the queue
                    temp = queue_devices.get()

                    # We load the information

                    # From the text to time structure
                                        #temp2 = time.strptime(temp[0],"%a %b %d %H:%M:%S %Y")

                    # From time structure to supported text.
                    #temp_date = time.strftime("%Y-%m-%d %H:%M:%S",temp2)

                    last_seen = temp[0]
                    first_seen = temp[0]
                    device_bdaddr = temp[1]
                    device_name = temp[2]
                    location_gps = temp[3]
                    location_address = temp[4]
                    device_information = temp[5]
                    
                    device_id = db_get_device_id(connection,device_bdaddr,device_information)
                    
                    if flag_alarm: 
                        # Here we start the discovering devices threads
                        device_alert_thread = threading.Thread(None,target = device_alert, args=(device_id,device_name,database_name,location_gps,location_address,last_seen))
                        device_alert_thread.setDaemon(True)
                        device_alert_thread.start()

                    if device_id:
                        # If we have a device information, then we update the information for the device
                        result = db_update_device(connection,device_id,device_information)
                        if not result:
                            print 'Device information could not be updated'
                        # We try to store a new location
                        result = db_add_location(connection,device_id,location_gps,first_seen,location_address,device_name)

                        # If the location has not changed, result will be False. We update the last seen field into locations.
                        if not result:
                            result = db_update_location(connection,device_id,location_gps,last_seen)

                    #print '  {:<24}  {:<17}  {:<30}  {:<27}  {:<30}  {:<20}'.format(temp[0],temp[1],temp[2],temp[3],temp[4],temp[5])
            time.sleep(2)

    except KeyboardInterrupt:
        print 'Exiting. It may take a few seconds.'
        threadbreak = True
    except Exception as inst:
        print 'Exception in store_device_information() function'
        threadbreak = True
        print 'Ending threads, exiting when finished'
        print type(inst) # the exception instance
        print inst.args # arguments stored in .args
        print inst # _str_ allows args to printed directly
        x, y = inst # _getitem_ allows args to be unpacked directly
        print 'x =', x
        print 'y =', y
        sys.exit(1)

##########
# MAIN
##########
def main():
    global debug
    global threadbreak
    global flag_sound
    global flag_internet
    global flag_gps
    global flag_lookup_services
    global flag_alarm
    global queue_devices
    global GRE
    global CYA
    global END
    global global_location
    global mail_username
    global mail_password

    database_name = "bluedriving.db"
    flag_run_webserver = False
    fake_gps = ''
    mail_username = ""
    mail_password = ""
    webserver_port = 8000
    webserver_ip = "127.0.0.1"
    flag_fake_gps=False

    try:
        
        opts, args = getopt.getopt(sys.argv[1:], "hDd:wsilgf:m:I:p:", ["help","debug","database-name=","webserver","disable-sound","not-internet","not-lookup-services","not-gps","fake-gps=","mail-user=","webserver-port=","webserver-ip="])
    except: 
        usage()
        exit(-1)

    for opt, arg in opts:
        if opt in ("-h", "--help"): usage(); sys.exit()
        if opt in ("-D", "--debug"): debug = True
        if opt in ("-d", "--database-name"): database_name = arg
        if opt in ("-w", "--webserver"): flag_run_webserver = True
        if opt in ("-s", "--disable-sound"): flag_sound = False
        if opt in ("-i", "--not-internet"): flag_internet = False
        if opt in ("-l", "--not-lookup-services"): flag_lookup_services = False
        if opt in ("-g", "--not-gps"): flag_gps = False; flag_internet = False
        if opt in ("-f", "--fake-gps"): fake_gps = arg; flag_gps = False;
        if opt in ("-m", "--mail-user"): mail_username = arg; print 'Provide your gmail password for given user: ',; mail_password = getpass.getpass()
        if opt in ("-p", "--webserver-port"): webserver_port = int(arg)
        if opt in ("-I", "--webserver-ip"): webserver_ip = str(arg)
    try:
        
        version()
        queue_devices = Queue.Queue()
        startTime = time.time()

        if flag_lookup_services:
            # We print the header for printing results on console
            print '  {:<24}  {:<17}  {:<30}  {:<27}  {:<30}  {:<20}'.format("Date","MAC address","Device name","Global Position","Aproximate address","Info")
            print '  {:<24}  {:<17}  {:<30}  {:<27}  {:<30}  {:<20}'.format("----","-----------","-----------","---------------","------------------","----")
        else:
            # We print the header for printing results on console
            print '  {:<24}  {:<17}  {:<30}  {:<27}  {:<30}'.format("Date","MAC address","Device name","Global Position","Aproximate address")
            print '  {:<24}  {:<17}  {:<30}  {:<27}  {:<30}'.format("----","-----------","-----------","---------------","------------------")

        # Here we start the thread to get gps location        
        if flag_gps and not flag_fake_gps:
            if debug:
                print '# Here we start the thread to get gps location'
                print '# flag_gps={0}'.format(flag_gps)
                print '# fake_gps={0}'.format(fake_gps)
                print
            #gps_thread = threading.Thread(None,target=get_coordinates_from_gps)
            gps_thread = threading.Thread(None,target=getGPS)
            gps_thread.setDaemon(True)
            gps_thread.start()
        elif fake_gps:
            # Here we are setting up the global location to use the fake gps
            if debug:
                print '# Here we are setting up the global location to use the fake gps'
                print '# flag_gps={0}'.format(flag_gps)
                print '# fake_gps={0}'.format(fake_gps)
            global_location = fake_gps
            if debug:
                print '# global_location={0}'.format(global_location)
                print
        
        # Here we start the web server
        if flag_run_webserver:
            if debug:
                print '# Here we start the thread to get the web server running'
                print '# flag_run_webserver={}'.format(flag_run_webserver)
                print
            #webserver_thread = threading.Thread(None,createWebServer,"web_server",args=(webserver_port,webserver_ip))
            webserver_thread = threading.Thread(None,createWebServer,"web_server",args=(webserver_port,webserver_ip,database_name))
            webserver_thread.setDaemon(True)
            webserver_thread.start()
        else:
            if debug:
                print '# The webserver flag is not set. Not running webserver.'
                print '# flag_run_webserver={}'.format(flag_run_webserver)
                print

        # Here we start the discovering devices threads
        if debug:
            print '# Here we start the discovering devices thread'
            print '# threading.Thread(None,target = bluetooth_discovering)'
            print '# bluetooth_discovering_thread.setDaemon(True)'
            print
        bluetooth_discovering_thread = threading.Thread(None,target = bluetooth_discovering)
        bluetooth_discovering_thread.setDaemon(True)
        bluetooth_discovering_thread.start()

        # Here we start the thread that will continuosly store data to the database
        if debug:
            print '# Here we start the thread that will continuosly store data to the database'
            print '# threading.Thread(None,target = store_device_information,args=(database_name,))'
            print '# store_device_information_thread.setDaemon(True)'
            print
        store_device_information_thread = threading.Thread(None,target = store_device_information,args=(database_name,))
        store_device_information_thread.setDaemon(True)
        store_device_information_thread.start()

        # Initializating sound
        if flag_sound:
            if debug:
                print '# Initializating soud'
                print '# pygame.init()'
            try:
                pygame.init()
            except:
                print '(!) pygame couldn''t been initialized. Mutting bluedriving.'
                flag_sound=False
                print '(!) flag_sound=()'.format(flag_sound)
                print

        # This options are for live-options interaction
        k = ""
        while True:
            k = raw_input()
            if k == 'a' or k == 'A':
                if flag_alarm: 
                    flag_alarm = False
                    print GRE+'Alarms desactivated'+END
                else:
                    flag_alarm = True
                    print GRE+'Alarms activated'+END

            if k == 'd' or k == 'D':
                if debug:
                    debug = False
                    print GRE+'Debug mode desactivated'+END
                else:
                    debug = True
                    print GRE+'Debug mode activated'+END
    
            if k == 's':
                if flag_sound == True:
                    flag_sound = False
                    print GRE+'Sound desactivated'+END
                else:
                    pygame.init()
                    flag_sound = True
                    print GRE+'Sound activated'+END
            if k == 'i':
                if flag_internet == True:
                    flag_internet = False
                    print GRE+'Internet desactivated'+END
                else:
                    flag_internet = True
                    print GRE+'Internet activated'+END
            if k == 'l':
                if flag_lookup_services == True:
                    flag_lookup_services = False
                    print GRE+'Look up services desactivated'+END
                else:
                    flag_lookup_services = True
                    print GRE+'Look up services activated'+END
            """
            if k == 'g':
                if flag_gps == True:
                    flag_gps = False
                    flag_internet = False
                    print GRE+'GPS desactivated'+END
                    print GRE+'Internet desactivated'+END
                else:
                    flag_gps = True
                    print GRE+'GPS activated'+END
            """
            if k == 'Q' or k == 'q':
                break

        threadbreak = True
        print '\n[+] Exiting'

    except KeyboardInterrupt:
        print 'Exiting. It may take a few seconds.'
        threadbreak = True
        time.sleep(1)
        for thread in threading.enumerate():
            try:
                thread.stop_now()
            except:
                pass
    except Exception as inst:
        print 'Error in main() function'
        print 'Ending threads, exiting when finished'
        threadbreak = True
        print type(inst) # the exception instance
        print inst.args # arguments stored in .args
        print inst # _str_ allows args to printed directly
        x, y = inst # _getitem_ allows args to be unpacked directly
        print 'x =', x
        print 'y =', y
        sys.exit(1)


if __name__ == '__main__':
        main()


########NEW FILE########
__FILENAME__ = bluedrivingWebServer
#! /usr/bin/env python
#  Copyright (C) 2009  Veronica Valeros, Juan Manuel Abrigo, Sebastian Garcia
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
#
# Author:
# Sebastian Garcia eldraco@gmail.com
#
# Changelog

#
# TODO

#
# KNOWN BUGS

#
# Description
# Web server for the bludriving.py
#
#
# TODO
# When the first position of a device is '', them map does not show.


# Standard imports
import getopt
import sys
import BaseHTTPServer
from os import curdir, sep
try:
    import simplejson as json
except:
    print 'Library needed. apt-get install python-simplejson'
    exit(-1)
        
try:
    import sqlite3
except:
    print 'Library needed. apt-get install python-sqlite'
    exit(-1)
import copy

####################
# Global Variables

# Debug
debug=0
vernum="0.1.2"
database = 'bluedriving.db'
verbose=False
####################



# Print version information and exit
def version():
  print "+----------------------------------------------------------------------+"
  print "| bludrivingWebServer.py Version "+ vernum +"                                      |"
  print "| This program is free software; you can redistribute it and/or modify |"
  print "| it under the terms of the GNU General Public License as published by |"
  print "| the Free Software Foundation; either version 2 of the License, or    |"
  print "| (at your option) any later version.                                  |"
  print "|                                                                      |"
  print "| Author: Sebastian Garcia, eldraco@gmail.com                          |"
  print "| Mateslab Hackspace, www.mateslab.com.ar                              |"
  print "+----------------------------------------------------------------------+"
  print


# Print help information and exit:
def usage():
  print "+----------------------------------------------------------------------+"
  print "| bludrivingWebServer.py Version "+ vernum +"                                      |"
  print "| This program is free software; you can redistribute it and/or modify |"
  print "| it under the terms of the GNU General Public License as published by |"
  print "| the Free Software Foundation; either version 2 of the License, or    |"
  print "| (at your option) any later version.                                  |"
  print "|                                                                      |"
  print "| Author: Sebastian Garcia, eldraco@gmail.com                          |"
  print "| Mateslab Hackspace, www.mateslab.com.ar                              |"
  print "+----------------------------------------------------------------------+"
  print "\nusage: %s <options>" % sys.argv[0]
  print "options:"
  print "  -h, --help           Show this help message and exit"
  print "  -V, --version        Show the version"
  print "  -v, --verbose        Be verbose"
  print "  -D, --debug          Debug"
  print "  -p, --webserver-port           Web server tcp port to use. Defaults to 8000"
  print "  -I, --webserver-ip           Web server ip to bind to. Defaults to 127.0.0.1"
  print "  -d, --database       If you wish to analyze another database, just give the file name here."


def createWebServer(port, ip_addresss, current_database):
    """ Crate a web server """
    global debug

    global database
    database = current_database

    # By default bind to localhost
    server_address = (ip_addresss, port)

    # Create a webserver
    try:
        httpd = BaseHTTPServer.HTTPServer(server_address, MyHandler)
        # Get the socket
        sa = httpd.socket.getsockname()

        if debug:
            print "Serving HTTP on", sa[0], "port", sa[1], "..."

        # Run forever
        httpd.serve_forever()
    except KeyboardInterrupt:
        print ' Received, shutting down the server.'
        httpd.socket.close()
    except:
        print "Probably can not assing that IP address. Are you sure your device has this IP?"
        print
        sys.exit(-1)


def get_unread_registers():
    """ Get unread registers from the database since the last read and return a json with all the data"""
    try:
        global debug
        global database

        conn = sqlite3.connect(database)
        cursor = conn.cursor()

        # Encoder
        je = json.JSONEncoder()

        top = {}
        array = []

        top['UnReadData'] = array

        # First select all the locations
        # This can be VERY HEAVY with a huge database...
        #for row in cursor.execute('SELECT * FROM Locations order by lastseen DESC limit 9000'):
        askname = ('%%',)

        for row in cursor.execute('SELECT * FROM Locations where Name like ? order by lastseen DESC limit 9000 ',askname):

            if debug:
                print ' >> Read locations {0}'.format(row)
            dev_id = (row[1],)

            # Update location id

            newcursor = conn.cursor()

            # add the limit!
            for newrow in newcursor.execute('SELECT * FROM Devices WHERE Id = ?',dev_id):
                dict = {}
                # ID
                # GPS
                dict['gps'] = row[2]
                # first seen
                dict['firstseen'] = row[3]
                # last seen
                dict['lastseen'] = row[4]
                # address
                dict['address'] = row[5]
                # name
                dict['name'] = row[6]
                # MAC
                dict['mac'] = newrow[1]
                # Name
                dict['info'] = newrow[2]
            
                array.append(dict)

        response = je.encode(top)
        return response

    except Exception as inst:
        if debug:
            print '\tError on get_unread_registers()'
        print type(inst)     # the exception instance
        print inst.args      # arguments stored in .args
        print inst           # __str__ allows args to printed directly
        exit(-1)



def get_info_from_mac(temp_mac):
    """ Get info from one mac """
    global debug
    global database

    try:
        conn = sqlite3.connect(database)
        cursor = conn.cursor()
        mac = (temp_mac,)

        # Encoder
        je = json.JSONEncoder()

        top = {}
        info = []

        for row in cursor.execute('SELECT Info FROM Devices WHERE Mac == ?',mac):
            (info,) = row
            if debug:
                print ' >> Info retrived: {0}'.format(info)

        top['Info'] = info
        return je.encode(top)

    except Exception as inst:
        if debug:
            print '\tError on get_info_from_mac()'
        print type(inst)     # the exception instance
        print inst.args      # arguments stored in .args
        print inst           # __str__ allows args to printed directly
        x, y = inst          # __getitem__ allows args to be unpacked directly
        print 'x =', x
        print 'y =', y
        exit(-1)


def get_all_devices_positions(amount):
    """ Get every position of all devices """
    global debug
    global database

    try:
        conn = sqlite3.connect(database)
        cursor = conn.cursor()
        askamount = (amount,)

        row = cursor.execute("SELECT MacId FROM Locations order by id desc limit 0,?",askamount)
        res = row.fetchall()

        if len(res) != 0:

            # Encoder
            je = json.JSONEncoder()

            # Top stores everythin
            top = []

            for macid in res:
                mac_dict = {}
                # Get the mac
                cursor3 = conn.cursor()
                row = cursor3.execute("SELECT mac FROM devices where id = ?",askamount)
                res = row.fetchall()
                (mac,) = res[0]

                mac_dict['Mac'] = mac
                mac_data_dict = {}
                mac_dict['Data'] = mac_data_dict
                mac_pos = []
                mac_data_dict['Pos'] = mac_pos
                # Example: { "Mac":"11:22:33:44:55:66", "Data":{"Name":"test", "Pos":["1","2"] }, "Mac":"aa:bb:cc:dd:ee:ff", "Data":{"Name":"jorge", "Pos":["3","4"] } }

                # For each id, get the data
                cursor2 = conn.cursor()
                # Flag to know if this mac has at least one position and avoid returning an empty position vector.
                no_gps_at_all = True
                for row in cursor2.execute("SELECT * FROM Locations WHERE Macid = ?",macid):
                    
                    # firstseen and name do not change with more positions. We store them every time...
                    firstseen = row[3]
                    name = row[6]
                    mac_data_dict['Name'] = name
                    mac_data_dict['FirstSeen'] = firstseen

                    # lastseen changes with more positions. So only the last one will remain.
                    lastseen = row[4]
                    mac_data_dict['LastSeen'] = lastseen

                    gps = row[2]
                    # Add the other string for no gps
                    if gps and "''" not in gps and 'not available' not in gps and 'NO' not in gps and 'Not' not in gps and 'False' not in gps :
                        no_gps_at_all = False
                        mac_pos.append(gps)
                    
                    if debug:
                        print ' > Name: {0}, FirstSeen: {1}, LastSeen: {2}, Gps: {3}, Mac: {4}'.format(name, firstseen, lastseen, gps, mac)
                top.append(mac_dict)

            return je.encode(top)



    except Exception as inst:
        if debug:
            print '\tError on get_all_devices_positions()'
        print type(inst)     # the exception instance
        print inst.args      # arguments stored in .args
        print inst           # __str__ allows args to printed directly
        x, y = inst          # __getitem__ allows args to be unpacked directly
        print 'x =', x
        print 'y =', y
        exit(-1)



def get_n_positions(mac):
    """ Get every position of a given MAC in the database """
    global debug
    global database

    try:
        conn = sqlite3.connect(database)
        cursor = conn.cursor()

        # Get all the macs into an array
        askmac = ('%'+mac+'%',)

        row = cursor.execute("SELECT Id FROM Devices WHERE Mac like ? limit 0,1",askmac)

        # Check the results, Does this mac exists?
        res = row.fetchall()
        if len(res) != 0:
            (id,) = res[0]
        else:
            if debug:
                print ' >> This mac does not exist: {0}'.format(mac)
            return ''

        # Get the name of the device
        cursor2 = conn.cursor()
        row2 = cursor2.execute("SELECT Name FROM Locations WHERE MacId = ?",(id,))
        res = row2.fetchall()
        if len(res) != 0:
            (name,) = res[0]
        else:
            if debug:
                print ' >> Some problem getting the name of the device: {0}'.format(mac)
            return ''

        # Encoder
        je = json.JSONEncoder()
        
        # Example
        # { "map": [ 
        #        { "MAC":"00:11:22:33:44:55", 
        #            "pos": [                     // Called pos_vect below
        #                    "gps":"-21.0001 -32.0023",     // Called gps_data below
        #                    "gps":"-44.5423 -56.65544" 
        #                ] }, 
        #        {}, // Each of this is called data below
        #        {}, 
        #        {} 
        #       ] } 

        # Top stores everythin
        top = {}

        pos_vect=[]

        # Link the map vector with the name 'Map'
        top['Name'] = name
        top['Mac'] = mac
        top['Pos'] = pos_vect

        cursor2 = conn.cursor()

        if debug:
            print ' >> Asking for mac: {0}'.format(mac)

        askid = (id,)

        # Flag to know if this mac has at least one position and avoid returning an empty position vector.
        no_gps_at_all = True
        for row in cursor2.execute("SELECT * FROM Locations WHERE Macid = ?",askid):
            gps = row[2]

            # Add the other string for no gps
            if 'not available' not in gps and 'NO' not in gps and 'Not' not in gps and gps != '' and 'False' not in gps :
                no_gps_at_all = False
                pos_vect.append(gps)
                if debug:
                    print '\t >> MAC {0} has position: {1}'.format(mac,gps)

        if no_gps_at_all:
            if debug:
                print ' >> MAC {0} has no gps position at all.'.format(mac)
            # This avoids adding an empty data to the map results.

        return je.encode(top)

    except Exception as inst:
        if debug:
            print '\tProblem in get_n_positions()'
        print type(inst)     # the exception instance
        print inst.args      # arguments stored in .args
        print inst           # __str__ allows args to printed directly
        x, y = inst          # __getitem__ allows args to be unpacked directly print 'x =', x
        print 'y =', y
        exit(-1)


def note_to(typeof_call, mac,note):
    """ Get a MAC and a note and add the note to the database """
    import re
    global debug
    global database

    try:

        # Input sanitizing
        ##################

        # Replace + with spaces.
        note = note.replace('+', ' ')
        # Replace %20 with spaces.
        note = note.replace('%20', ' ')
        if debug:
            print ' >> Sanitizing Mac: {0} and Note: {1}'.format(mac, note)

        # verify the data types
        try:
            # Are they strings?
            if type(mac) != str or type(note) != str:
                if debug:
                    print ' >> Some strange attempt to hack the server:1'
                return ''
                # Is the format ok?
            if len(mac.split(':')) != 6 or len(mac) != 17:
                if debug:
                    print ' >> Some strange attempt to hack the server:2'
                return ''
                # Is the len of the noteok?
            if len(note) > 253:
                if debug:
                    print ' >> Some strange attempt to hack the server:4'
                return ''
            # Characters fot the mac
            if not re.match('^[a-fA-F0-9:]+$',mac):
                if debug:
                    print ' >> Some strange attempt to hack the server:4'
                return ''
            # Characters fot the note
            if note and not re.match('^[a-zA-Z0-9 .,?]+$',note):
                if debug:
                    print ' >> Some strange attempt to hack the server:5'
                return ''
        except Exception as inst:
            if debug:
                print ' >> Some strange attempt to hack the server.6'
            print type(inst)     # the exception instance
            print inst.args      # arguments stored in .args
            print inst           # __str__ allows args to printed directly
            x, y = inst          # __getitem__ allows args to be unpacked directly
            print 'x =', x
            print 'y =', y
            return ''

        # We are hopefully safe here...
        if debug:
            print ' >> We are safe'
        # END Input sanitizing
        ##################


        if typeof_call == 'add':
            # Search fot that mac on the database first...
            conn = sqlite3.connect(database)
            cursor = conn.cursor()
            askmac = ('%'+mac+'%',)

            row = cursor.execute("SELECT Id FROM Devices WHERE Mac like ? limit 0,1",askmac)

            # Check the results, Does this mac exists?
            res = row.fetchall()
            if len(res) != 0:
                (id,) = res[0]
            else:
                if debug:
                    print ' >> This mac does not exist: {0}'.format(mac)
                return ''
                
            cursor = conn.cursor()

            # Try to insert
            try:
                cursor.execute("INSERT INTO Notes (Id,Note) values (?,?) ",(id,note))
                conn.commit()
                if debug:
                    print ' >> Inserted values. Id: {0}, Note:{1}'.format(id,note)
                conn.close()
            except Exception as inst:
                if debug:
                    print ' >> Some problem inserting in the database in the funcion note_to()'
                print type(inst)     # the exception instance
                print inst.args      # arguments stored in .args
                print inst           # __str__ allows args to printed directly
                x, y = inst          # __getitem__ allows args to be unpacked directly
                print 'x =', x
                print 'y =', y
                return ''

            return "{'Result':'Added'}"

        elif typeof_call == 'del':
            # Search fot that mac on the database first...
            conn = sqlite3.connect(database)
            cursor = conn.cursor()
            askmac = ('%'+mac+'%',)

            row = cursor.execute("SELECT Id FROM devices WHERE Mac like ? limit 0,1",askmac)

            # Check the results, Does this mac exists?
            res = row.fetchall()
            if len(res) != 0:
                (id,) = res[0]
            else:
                if debug:
                    print ' >> This mac does not exist: {0}'.format(mac)
                return ''
        
            asknote = ('%'+note+'%',)

            # The mac does exist. Let's delete it.
            cursor2 = conn.cursor()

            # Try to delete
            try:
                cursor2.execute("DELETE FROM Notes where Id like ? and Note like ?",(id,note))
                conn.commit()
                if debug:
                    print ' >> Deleted values. Id: {0}, Note:{1}'.format(id,note)
                conn.close()
            except Exception as inst:
                if debug:
                    print ' >> Some problem deleting in the database in the funcion note_to()'
                print type(inst)     # the exception instance
                print inst.args      # arguments stored in .args
                print inst           # __str__ allows args to printed directly
                x, y = inst          # __getitem__ allows args to be unpacked directly
                print 'x =', x
                print 'y =', y
                return ''

            return 'Deleted'

        elif typeof_call == 'get':
            # Search fot that mac on the database first...
            conn = sqlite3.connect(database)
            cursor = conn.cursor()
            askmac = ('%'+mac+'%',)

            je = json.JSONEncoder()

            row = cursor.execute("SELECT Id FROM devices WHERE Mac like ? limit 0,1",askmac)

            # Check the results, Does this mac exists?
            res = row.fetchall()
            if len(res) != 0:
                (id,) = res[0]
            else:
                if debug:
                    print ' >> This mac does not exist: {0}'.format(mac)
                return ''
            # The mac does exist. Let's delete it.
            cursor2 = conn.cursor()

            notesdict = {}
            notes = []
            notesdict['Notes'] = notes

            # Try to get the values
            try:
                row2 = cursor2.execute("SELECT Note from notes where Id like ? ",(id,))
                for row in row2:
                    notes.append(str(row[0]))

                conn.commit()
                if debug:
                    print ' >> Getting values. Id: {0}, Note:{1}'.format(id,note)
                conn.close()
            except Exception as inst:
                if debug:
                    print ' >> Some problem getting the notes in the funcion note_to()'
                print type(inst)     # the exception instance
                print inst.args      # arguments stored in .args
                print inst           # __str__ allows args to printed directly
                x, y = inst          # __getitem__ allows args to be unpacked directly
                print 'x =', x
                print 'y =', y
                return ''
            response = je.encode(notesdict)
            return response
        else:
            return ''

    except Exception as inst:
        if debug:
            print '\tProblem in note_to()'
        print type(inst)     # the exception instance
        print inst.args      # arguments stored in .args
        print inst           # __str__ allows args to printed directly
        x, y = inst          # __getitem__ allows args to be unpacked directly
        print 'x =', x
        print 'y =', y
        exit(-1)

def alarm_to(type_ofcall, mac, alarm_type):
    """ Get a MAC and add, get or remove an alarm """
    global debug
    global database
    import re

    try:
        # verify the data types
        try:
            # Are they strings?
            if type(mac) != str or type(alarm_type) != str:
                if debug:
                    print ' >> Some strange attempt to hack the server:1'
                return ''
                # Is the format ok?
            if len(mac.split(':')) != 6 or len(mac) != 17:
                if debug:
                    print ' >> Some strange attempt to hack the server:2'
                return ''
                # Is the len of the noteok?
            if len(alarm_type) > 253:
                if debug:
                    print ' >> Some strange attempt to hack the server:4'
                return ''
            # Characters fot the mac
            if not re.match('^[a-fA-F0-9:]+$',mac):
                if debug:
                    print ' >> Some strange attempt to hack the server:4'
                return ''
            # Characters fot the note
            if alarm_type and not re.match('^[a-zA-Z0-9 .,?]+$',alarm_type):
                if debug:
                    print ' >> Some strange attempt to hack the server:5'
                return ''
        except Exception as inst:
            if debug:
                print ' >> Some strange attempt to hack the server.6'
            print type(inst)     # the exception instance
            print inst.args      # arguments stored in .args
            print inst           # __str__ allows args to printed directly
            x, y = inst          # __getitem__ allows args to be unpacked directly
            print 'x =', x
            print 'y =', y
            return ''


        if type_ofcall == 'add':

            # Search fot that mac on the database first...
            conn = sqlite3.connect(database)
            cursor = conn.cursor()
            askmac = ('%'+mac+'%',)

            row = cursor.execute("SELECT Id FROM Devices WHERE Mac like ? limit 0,1",askmac)

            # Check the results, Does this mac exists?
            res = row.fetchall()
            if len(res) != 0:
                (id,) = res[0]
            else:
                if debug:
                    print ' >> This mac does not exist: {0}'.format(mac)
                return ''
                
            cursor = conn.cursor()

            # Try to insert
            try:
                cursor.execute("INSERT INTO Alarms (Id,Alarm) values (?,?) ",(id,alarm_type))
                conn.commit()
                if debug:
                    print ' >> Inserted values. Id: {0}, Alarm:{1}, Mac:{2}'.format(id, alarm_type, mac)
                conn.close()
            except Exception as inst:
                if debug:
                    print ' >> Some problem inserting in the database in the funcion alarm_to()'
                print type(inst)     # the exception instance
                print inst.args      # arguments stored in .args
                print inst           # __str__ allows args to printed directly
                x, y = inst          # __getitem__ allows args to be unpacked directly
                print 'x =', x
                print 'y =', y
                return ''

            return "{'Result':'Added'}"

        elif type_ofcall == 'del':

            # Search fot that mac on the database first...
            conn = sqlite3.connect(database)
            cursor = conn.cursor()
            askmac = ('%'+mac+'%',)

            row = cursor.execute("SELECT Id FROM Devices WHERE Mac like ? limit 0,1",askmac)

            # Check the results, Does this mac exists?
            res = row.fetchall()
            if len(res) != 0:
                (id,) = res[0]
            else:
                if debug:
                    print ' >> This mac does not exist: {0}'.format(mac)
                return ''
                
            cursor = conn.cursor()

            # Try to insert
            try:
                cursor.execute("DELETE From Alarms where Id like ? and Alarm like ?",(id,alarm_type))
                conn.commit()
                if debug:
                    print ' >> Deleted values. Id: {0}, Alarm:{1}, Mac:{2}'.format(id, alarm_type, mac)
                conn.close()
            except Exception as inst:
                if debug:
                    print ' >> Some problem deleting in the database in the funcion alarm_to()'
                print type(inst)     # the exception instance
                print inst.args      # arguments stored in .args
                print inst           # __str__ allows args to printed directly
                x, y = inst          # __getitem__ allows args to be unpacked directly
                print 'x =', x
                print 'y =', y
                return ''

            return "{'Result':'Deleted'}"

        elif type_ofcall == 'get':

            # Search fot that mac on the database first...
            conn = sqlite3.connect(database)
            cursor = conn.cursor()
            askmac = ('%'+mac+'%',)

            je = json.JSONEncoder()

            row = cursor.execute("SELECT Id FROM Devices WHERE Mac like ? limit 0,1",askmac)

            # Check the results, Does this mac exists?
            res = row.fetchall()
            if len(res) != 0:
                (id,) = res[0]
            else:
                if debug:
                    print ' >> This mac does not exist: {0}'.format(mac)
                return ''
                
            cursor = conn.cursor()

            alarmsdict = {}
            alarms = []
            alarmsdict['Alarms'] = alarms
            # Try to insert
            try:
                row2 = cursor.execute("SELECT Alarm from Alarms where Id like ?",(id,))
                for row in row2:
                    alarms.append(row)
                conn.commit()
                if debug:
                    print ' >> Get values. Id: {0}, Alarm:{1}, Mac:{2}'.format(id, alarm_type, mac)
                conn.close()
            except Exception as inst:
                if debug:
                    print ' >> Some problem getting from the database in the funcion alarm_to()'
                print type(inst)     # the exception instance
                print inst.args      # arguments stored in .args
                print inst           # __str__ allows args to printed directly
                x, y = inst          # __getitem__ allows args to be unpacked directly
                print 'x =', x
                print 'y =', y
                return ''

            response = je.encode(alarmsdict)
            return response


    except Exception as inst:
        if debug:
            print '\tProblem in alarm_to()'
        print type(inst)     # the exception instance
        print inst.args      # arguments stored in .args
        print inst           # __str__ allows args to printed directly
        x, y = inst          # __getitem__ allows args to be unpacked directly
        print 'x =', x
        print 'y =', y
        exit(-1)



class MyHandler (BaseHTTPServer.BaseHTTPRequestHandler):
    """ Handle the requests """

    def log_message(self, format, *args):
        return

    def do_GET(self):
        global debug
        global verbose
        note = ""
        alarm_type = ""
        try:
            if debug:
                print ' >> Path: {0}'.format(self.path)

            # Return the basic info about the MACs since last request
            if self.path == '/data':
                if debug:
                    print ' >> Get /data'
                # Get the unread registers from the DB since last time
                json_to_send = get_unread_registers()

                self.send_response(200)
                self.send_header('Content-Type',        'text/html')
                self.end_headers()
                self.wfile.write(json_to_send)

            # Get a MAC and add a note in the database 
            elif self.path.rfind('/addnote?mac=') == 0: # and self.path.find("note=") > 0:
                if debug:
                    print ' >> Get /addnote'
                mac = str(self.path.split('mac=')[1].split('&')[0])
                note = str(self.path.split('note=')[1])
                json_to_send = note_to('add', mac, note)
                if verbose:
                    print mac,note

                self.send_response(200)
                self.send_header('Content-Type',        'text/html')
                self.end_headers()
                self.wfile.write(json_to_send)

            # Get a MAC and del a note from the database 
            elif self.path.rfind('/delnote?mac=') == 0: # and self.path.find("note=") > 0:
                if debug:
                    print ' >> Get /delnote'
                mac = str(self.path.split('mac=')[1].split('&')[0])
                note = str(self.path.split('note=')[1])
                json_to_send = note_to('del', mac, note)

                self.send_response(200)
                self.send_header('Content-Type',        'text/html')
                self.end_headers()
                self.wfile.write(json_to_send)

            # Get a MAC and get all the notes from the database 
            elif self.path.rfind('/getnote?mac=') == 0: # and self.path.find("note=") > 0:
                if debug:
                    print ' >> Get /getnote'
                mac = str(self.path.split('mac=')[1].split('&')[0])
                json_to_send = note_to('get', mac, "")

                self.send_response(200)
                self.send_header('Content-Type',        'text/html')
                self.end_headers()
                self.wfile.write(json_to_send)
            # Get alarms from a MAC  
            elif self.path.rfind('/getalarm?mac=') == 0: # and self.path.find("note=") > 0:
                if debug:
                    print ' >> Get /getalarm'
                mac = str(self.path.split('mac=')[1].split('&')[0])
                json_to_send = alarm_to('get', mac, '')

                self.send_response(200)
                self.send_header('Content-Type',        'text/html')
                self.end_headers()
                self.wfile.write(json_to_send)
            # Add an alarm to a MAC  
            elif self.path.rfind('/addalarm?mac=') == 0: # and self.path.find("note=") > 0:
                if debug:
                    print ' >> Get /addalarm'
                mac = str(self.path.split('mac=')[1].split('&')[0])
                alarm_type = str(self.path.split('type=')[1].split('&')[0])
                if verbose:
                    print mac,alarm_type
                json_to_send = alarm_to('add', mac, alarm_type)

                self.send_response(200)
                self.send_header('Content-Type',        'text/html')
                self.end_headers()
                self.wfile.write(json_to_send)
            # Del an alarm from a MAC  
            elif self.path.rfind('/delalarm?mac=') == 0: # and self.path.find("note=") > 0:
                if debug:
                    print ' >> Get /delalarm'
                mac = str(self.path.split('mac=')[1].split('&')[0])
                alarm_type = str(self.path.split('type=')[1].split('&')[0])
                json_to_send = alarm_to('del', mac, alarm_type)

                self.send_response(200)
                self.send_header('Content-Type',        'text/html')
                self.end_headers()
                self.wfile.write(json_to_send)
            # Get a MAC and return all the info about that MAC
            elif self.path.rfind('/info?mac=') == 0:
                if debug:
                    print ' >> Get /info'
                
                mac = self.path.split('mac=')[1]
                json_to_send = get_info_from_mac(mac)

                self.send_response(200)
                self.send_header('Content-Type',        'text/html')
                self.end_headers()
                self.wfile.write(json_to_send)

            # Get an X amount and return for every MAC the last X positions.
            elif self.path.rfind('/map?info=') == 0:
                if debug:
                    print ' >> Get /map'
                info = self.path.split('info=')[1]

                # It is a mac
                if len(info.split(':')) == 6 and len(info) == 17:
                    mac = self.path.split('info=')[1]
                    json_to_send = get_n_positions(mac)
                elif type(info) == str and int(info) > 0:
                    json_to_send = get_all_devices_positions(int(info))

                self.send_response(200)
                self.send_header('Content-Type',        'text/html')
                self.end_headers()
                self.wfile.write(json_to_send)

            elif self.path == "/":
                if debug:
                    print ' >> Get /'
                # Return the index.html
                file = open(curdir + sep + 'index.html')

                temp_read = file.read()
                file_len = len(temp_read)

                self.send_response(200)
                self.send_header('Content-Type','text/html; charset=UTF-8')
                self.send_header('Content-Length',file_len)
                self.end_headers()

                self.wfile.write(temp_read)
                file.close()


            elif self.path != "/":
                # Read files in the directory
                if debug:
                    print ' >> Get generic file'

                try:
                    extension = self.path.split('.')[-1]
                    if len(extension.split('?')) >= 2:
                        extension = self.path.split('.')[-1].split('?')[0]
                        self.path = self.path.split('?')[0]
                except:
                    # Does not have . on it...
                    self.send_response(200)
                    return

                self.send_response(200)

                if extension == 'css':
                    file = open(curdir + sep + self.path)
                    temp_read = file.read()
                    file_len = len(temp_read)
                    self.send_header('Content-Type','text/css')
                    self.send_header('Content-Length',file_len)
                    self.end_headers()

                elif extension == 'png':
                    file = open(curdir + sep + self.path)
                    temp_read = file.read()
                    file_len = len(temp_read)
                    self.send_header('Content-Type','image/png')
                    self.send_header('Content-Length',file_len)
                    self.end_headers()

                elif extension == 'js':
                    file = open(curdir + sep + self.path)
                    temp_read = file.read()
                    file_len = len(temp_read)
                    self.send_header('Content-Type','text/javascript')
                    self.send_header('Content-Length', file_len)
                    self.end_headers()

                elif extension == 'html':
                    file = open(curdir + sep + self.path)
                    temp_read = file.read()
                    file_len = len(temp_read)
                    self.send_header('Content-Type','text/html; charset=UTF-8')
                    self.send_header('Content-Length',file_len)
                    self.end_headers()
                else:
                    self.send_header('Content-Type','text/html; charset=UTF-8')
                    self.send_header('Content-Length','9')
                    self.end_headers()
                    self.wfile.write('Hi there.')
                    return

                self.wfile.write(temp_read)
                file.close()

            return

        except IOError:
            self.send_error(404,'File Not Found: {0}'.format(self.path))





def main():
    try:
        global debug
        global database
        global verbose
        # Default port to use
        webserver_port = 8000
        webserver_ip = "127.0.0.1"

        opts, args = getopt.getopt(sys.argv[1:], "VvDhp:I:d:", ["help","version","verbose","debug","webserver-port=","database=","webserver-ip="])
    except getopt.GetoptError: usage()

    for opt, arg in opts:
        if opt in ("-h", "--help"): usage();exit(-1)
        if opt in ("-V", "--version"): version();exit(-1)
        if opt in ("-v", "--verbose"): verbose = True
        if opt in ("-D", "--debug"): debug = 1
        if opt in ("-p", "--webserver-port"): webserver_port = int(arg)
        if opt in ("-I", "--webserver-ip"): webserver_ip = str(arg)
        if opt in ("-d", "--database"): database = str(arg)
    try:

        try:
            # TODO sanitize the input of the ip_addresss and port
            createWebServer(webserver_port, webserver_ip, database)

        except Exception, e:
            print "misc. exception (runtime error from user callback?):", e
        except KeyboardInterrupt:
            sys.exit(1)


    except KeyboardInterrupt:
        # CTRL-C pretty handling.
        print "Keyboard Interruption!. Exiting."
        sys.exit(1)

    except:
        usage()
        sys.exit(-1)


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = getCoordinatesFromAddress
#! /usr/bin/env python
#  Copyright (C) 2009  Veronica Valeros
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
#
# Author: Veronica Valeros, vero () valeros () gmail () com
#
# Changelog

# Description
# This little scripst receives an address and gets the coordinates using a Google Maps API



# standard imports
import os, pwd, string, sys
import getopt
import re
import urllib2
try:
    import simplejson
except:
    print 'Library needed. apt-get install python-simplejson'
    exit(-1)



####################
# Global Variables
vernum = 0.1
#########


# Print version information and exit
def version():
  print "+----------------------------------------------------------------------+"
  print "| getCoordinatesFromAddress.py Version "+ str(vernum) +"                             |"
  print "| This program is free software; you can redistribute it and/or modify |"
  print "| it under the terms of the GNU General Public License as published by |"
  print "| the Free Software Foundation; either version 2 of the License, or    |"
  print "| (at your option) any later version.                                  |"
  print "|                                                                      |"
  print "| Author: Veronica Valeros - vero () valeros () gmail () com           |"
  print "+----------------------------------------------------------------------+"
  print


# Print help information and exit:
def usage():
  print "+----------------------------------------------------------------------+"
  print "| getCoordinatesFromAddress.py Version "+ str(vernum) +"                             |"
  print "| This program is free software; you can redistribute it and/or modify |"
  print "| it under the terms of the GNU General Public License as published by |"
  print "| the Free Software Foundation; either version 2 of the License, or    |"
  print "| (at your option) any later version.                                  |"
  print "|                                                                      |"
  print "| Author: Veronica Valeros - vero () valeros () gmail () com           |"
  print "+----------------------------------------------------------------------+"
  print "\nusage: %s <options>" % sys.argv[0]
  print "options:"
  print "  -h, --help           Show this help message and exit"
  print "  -V, --version        Output version information and exit"
  print "  -v, --verbose        Output more information."
  print "  -D, --debug          Debug. In debug mode the statistics run live."
  print "  -a, --address        Address or coordinates between quotes. Ex: \"1600 Amphitheatre Parkway, Mountain View, Canada\"."
  print
  sys.exit(1)




# funtions here
def getCoordinates(address):
	global debug
	global verbose

	api_url = "http://maps.google.com/maps/api/geocode/json?sensor=false&address="
	query = ""
	answer = ""
	lat = ""
	lng = ""
	content = "" 
	coordinates = ""
	formattedaddress = ""

	try:
            # We verify the given address
            try:
                # Type
                if type(address) != str:
                    return 'Bad format. The given address is not a string. Do you used quotes?'
                # Format
                if len(address.split(',')) < 2 or len(address.split(',')) > 4:
                        return 'Bad address. Remember that the address should be like: \"Street number Street, City, Country\"'
                # Length of the address
                if len(address) > 255:
                    return 'Too long. The address is too long, request ignored.'
                # Characters accepted
                if not re.match('^[a-zA-Z0-9, .-]+$',address):
                    return 'Bad sintax. Unaccepted characters found in address. Try again.'
            
                address = address.rstrip(' ').strip(' ').replace(' ','+')
                query = api_url+address
                
                try:
                    answer = urllib2.urlopen(query)
                    content = simplejson.load(answer)
                    lat = content['results'][0]['geometry']['location']['lat']
                    lng = content['results'][0]['geometry']['location']['lng']
                
                    coordinates = str(lat)+','+str(lng)
                    formattedaddress = content['results'][0]['formatted_address']
                    return [coordinates,formattedaddress]
                except:
                    return [" "," "]
			
            except Exception, e:
                print "misc. exception (runtime error from user callback?):", e
                return [" "," "]

	except Exception, e:
		print "misc. exception (runtime error from user callback?):", e
		sys.exit(1)
	except KeyboardInterrupt:
		sys.exit(1)




def main():
        try:
                global debug
                global verbose

                address=""

		opts, args = getopt.getopt(sys.argv[1:], "VvDha:", ["help","version","verbose","debug","address="])
        except getopt.GetoptError: usage()

        for opt, arg in opts:
            if opt in ("-h", "--help"): usage()
            if opt in ("-V", "--version"): version();exit(-1)
            if opt in ("-v", "--verbose"): verbose=True
            if opt in ("-D", "--debug"): debug=True
	    if opt in ("-a", "--address"): address=arg
        try:
                try:
			if address:
				version()
				[coordinates,address] = getCoordinates(address)
				if coordinates or address: 
					print '[+] Location found: '
					if address: 
						print '\t '+address
					else: 
						print '\t No address found'
					if coordinates: 
						print '\t '+coordinates
					else:
						print '\t Not coordinates found.'
				else:
					print '\t Not address nor coordinates found.'
				print 
				print
                        else:
                                usage()
                                sys.exit(1)
                except Exception, e:
                        print "misc. exception (runtime error from user callback?):", e
                except KeyboardInterrupt:
                        sys.exit(1)
        except KeyboardInterrupt:
                # CTRL-C pretty handling.
                print "Keyboard Interruption!. Exiting."
                sys.exit(1)


if __name__ == '__main__':
    main()


########NEW FILE########
__FILENAME__ = manageDB
#!/usr/bin/python
#  Copyright (C) 2009  Veronica Valeros, Juan Manuel Abrigo, Sebastian Garcia
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
#
# Author:
# Veronica Valeros  vero.valeros@gmail.com
#
# Changelog
# - Added a function to list for a given mac the date, position, and name
#
# Description
# manageDB is a python tool to manage bluedriving database
#
# TODO
# - with -L if the device does not exists, output nothing.
# - For all the devices output all the locations with gps address and mac and vendor.
# - Given one date, print all the devices found that day, along with the gps and address.
# - When -L is used, check the address in the DB. If it exists, print it and do not search it again. If not, search for it and store it on the DB.

# standar imports
import sys
import re
import getopt
import copy
import os
import time
import sqlite3
from getCoordinatesFromAddress import getCoordinates


# Global variables
vernum = '0.1'
debug = False
quiet = False


def version():
    """
    This function prints information about this utility
    """

    print
    print "   "+ sys.argv[0] + " Version "+ vernum 
    print "   Authors: Vero Valeros (vero.valeros@gmail.com)"
    print "   manageDB is a python tool to manage bluedriving database.            "
    print

def usage():
    """
    This function prints the posible options of this program.
    """
    print
    print "   "+ sys.argv[0] + " Version "+ vernum +" @COPYLEFT"
    print "   Authors: Vero Valeros (vero.valeros@gmail.com), Seba Garcia (eldraco@gmail.com)"
    print "   Contributors: nanojaus"
    print "   manageDB is a python tool to manage bluedriving database.            "
    print
    print "\n   Usage: %s <options>" % sys.argv[0]
    print "   Options:"
    print "  \t-h, --help                           Show this help message and exit."
    print "  \t-D, --debug                          Debug mode ON. Prints debug information on the screen."
    print "  \t-d, --database-name                  Name of the database to store the data."
    print "  \t-l, --limit                          Limits the number of results when querying the database"
    print "  \t-e, --get-devices                    List all the MAC addresses of the devices stored in the DB"
    print "  \t-n, --get-devices-with-names         List all the MAC addresses and the names of the devices stored in the DB"
    print "  \t-E, --device-exists <mac>            Check if a MAC address is present on the database"
    print "  \t-R, --remove-device <mac>            Remove a device using a MAC address"
    print "  \t-g, --grep-names <string>            Look names matching the given string"
    print "  \t-r, --rank-devices <limit>           Shows a top 10 of the most seen devices on the database"
    print "  \t-m, --merge-with <db>                Merge the database (-d) with this database.Ex. bluedriving.py -d blu.db -m netbook.db"
    print "  \t-L, --get-locations-with-date <mac>  Prints a list of locations and dates in which the mac has been seen."
    print "  \t-q, --quiet-devices                  Print only the results"
    print "  \t-C, --count-devices                  Count the amount of devices on the database"
    print "  \t-c, --create-db                      Create an empty database. Useful for merging."
    print "  \t-S, --grep-locations                 Find devices near this GPS location. Use % for pattern matching, like '%50.071%,14.402%' "
    print "  \t-A, --all-data                       Get all the data for all the devices in the database."

def db_create(database_name):
    """
    This function creates a new bluedriving database. 
    """
    global debug
    global verbose

    connection = ""

    try:
        # We check if the database exists
        if not os.path.exists(database_name):
            if debug:
                print 'Creating database'
            # Creating database
            connection = sqlite3.connect(database_name)
            # Creating tables
            connection.execute("CREATE TABLE Devices(Id INTEGER PRIMARY KEY AUTOINCREMENT, Mac TEXT , Info TEXT, Vendor TEXT)")
            connection.execute("CREATE TABLE Locations(Id INTEGER PRIMARY KEY AUTOINCREMENT, MacId INTEGER, GPS TEXT, FirstSeen TEXT, LastSeen TEXT, Address TEXT, Name TEXT, UNIQUE(MacId,GPS))")
            connection.execute("CREATE TABLE Notes(Id INTEGER, Note TEXT)")
            connection.execute("CREATE TABLE Alarms(Id INTEGER, Alarm TEXT)")
            connection.commit()
            connection.close()
            if debug:
                print 'Database created'
            return True
        else:
            if debug:
                print 'Database already exist. Choose a different name.'
            return False
    except KeyboardInterrupt:
        print 'Exiting. It may take a few seconds.'
        sys.exit(1)
    except Exception as inst:
        print 'Exception in db_create(database_name) function'
        print 'Ending threads, exiting when finished'
        print type(inst) # the exception instance
        print inst.args # arguments stored in .args
        print inst # _str_ allows args to printed directly
        x, y = inst # _getitem_ allows args to be unpacked directly
        print 'x =', x
        print 'y =', y
        sys.exit(1)


def db_connect(database_name):
    """
    This function creates a connection to the database and return the connection
    """
    global debug
    global verbose

    connection = ""

    try:
        if not os.path.exists(database_name):
            return False
        connection = sqlite3.connect(database_name)
        if debug:
            print 'Database connection retrieved'
        return connection

    except KeyboardInterrupt:
        print 'Exiting. It may take a few seconds.'
        sys.exit(1)
    except Exception as inst:
        print 'Exception in db_connect(database_name) function'
        print 'Ending threads, exiting when finished'
        print type(inst) # the exception instance
        print inst.args # arguments stored in .args
        print inst # _str_ allows args to printed directly
        x, y = inst # _getitem_ allows args to be unpacked directly
        print 'x =', x
        print 'y =', y
        sys.exit(1)

def db_count_devices(connection):
    """
    This function returns the amount of devices in table Devices
    """
    global debug
    global verbose

    try:
        result = connection.execute("SELECT count(*) FROM Devices")
        if result:
            result = result.fetchall()
            return result[0][0]
        else:
            return False

    except KeyboardInterrupt:
        print 'Exiting. It may take a few seconds.'
        sys.exit(1)
    except Exception as inst:
        print 'Exception in db_count_devices(connection) function'
        print 'Ending threads, exiting when finished'
        print type(inst) # the exception instance
        print inst.args # arguments stored in .args
        print inst # _str_ allows args to printed directly
        x, y = inst # _getitem_ allows args to be unpacked directly
        print 'x =', x
        print 'y =', y
        sys.exit(1)

def db_locations_and_dates(connection,mac):
    """
    This function returns a set of Id, GPS, FSeen, LSeen, Name and Address, for a given mac.
    """
    global debug
    global verbose

    try:
        macId = db_get_id_from_mac(connection, mac)
        if macId:
            result = connection.execute("SELECT Id, GPS, FirstSeen, LastSeen, Name, Address FROM Locations WHERE MacId="+str(macId)+" ORDER BY FirstSeen ASC;")
            if result:
                result = result.fetchall()
                return result
            else:
                return False
        else:
            print 'The device seems not to be in the database. Please check the MAC address.'
            return False

    except KeyboardInterrupt:
        print 'Exiting. It may take a few seconds.'
        sys.exit(1)
    except Exception as inst:
        print 'Exception in db_locations_and_dates(connection,mac) function'
        print 'Ending threads, exiting when finished'
        print type(inst) # the exception instance
        print inst.args # arguments stored in .args
        print inst # _str_ allows args to printed directly
        x, y = inst # _getitem_ allows args to be unpacked directly
        print 'x =', x
        print 'y =', y
        sys.exit(1)

def db_get_mac_from_id(connection, MacId):
    """
    Given a MacId this function returns the MAC address of it.
    """
    global debug
    global verbose

    try:
        result = connection.execute("SELECT Mac FROM Devices WHERE Id = "+str(MacId)+";")
        if result:
            result = result.fetchall()
            return result[0][0]
        else:
            return False

    except KeyboardInterrupt:
        print 'Exiting. It may take a few seconds.'
        sys.exit(1)
    except Exception as inst:
        print 'Exception in db_get_mac_from_id(connection,MacId) function'
        print 'Ending threads, exiting when finished'
        print type(inst) # the exception instance
        print inst.args # arguments stored in .args
        print inst # _str_ allows args to printed directly
        x, y = inst # _getitem_ allows args to be unpacked directly
        print 'x =', x
        print 'y =', y
        sys.exit(1)

def db_get_id_from_mac(connection, Mac):
    """
    Given a MAC address this function returns the mac id 
    """
    global debug
    global verbose

    try:
        result = connection.execute("SELECT Id FROM Devices WHERE Mac = \""+str(Mac)+"\";")
        if result:
            result = result.fetchall()
            return result[0][0]
        else:
            return False

    except KeyboardInterrupt:
        print 'Exiting. It may take a few seconds.'
        sys.exit(1)
    except Exception as inst:
        print 'Exception in db_get_id_from_mac(connection,mac) function'
        print 'Ending threads, exiting when finished'
        print type(inst) # the exception instance
        print inst.args # arguments stored in .args
        print inst # _str_ allows args to printed directly
        x, y = inst # _getitem_ allows args to be unpacked directly
        print 'x =', x
        print 'y =', y
        sys.exit(1)

def db_merge(db_merged_connection,db_to_merge_connection):
    """
    This function merges two databases into one
    """
    global debug
    global verbose

    count_dev = 0
    count_loc = 0
    count_ala = 0
    count_not = 0

    try:
        # Adding data from devices database
        try:
            result = db_to_merge_connection.execute("SELECT Id, Mac, Info FROM Devices")
        except:
            print "Exception in sql query: \"SELECT Id, Mac,Info FROM Devices\""
            sys.exit(0)
        devices = result.fetchall()
        for (MacId,Mac,Info) in devices:
            #result = db_merged_connection.execute("INSERT OR IGNORE INTO Devices (Mac,Info) VALUES(\"11:11:11:11:11:11\",\"[]\");")
            try:
                result= db_merged_connection.execute("INSERT OR IGNORE INTO Devices (Mac,Info) VALUES(\""+str(Mac)+"\",\""+str(Info[0])+"\");")
                count_dev = count_dev+1
            except:
                print 'Exception mergin this device: {}, {}'.format(Mac,Info[0])
                sys.exit(0)

            db_merged_connection.commit()

            #Adding data from locations table
            try:
                result = db_to_merge_connection.execute("SELECT MacId,GPS,FirstSeen,LastSeen,Address,Name FROM Locations WHERE MacId="+str(MacId)+";")
            except:
                print "Exception in sql query: \"SELECT MacId,GPS,FirstSeen,LastSeen,Address,Name FROM Locations WHERE MacId=\""
                sys.exit(0)
            locationinfo = result.fetchall()
            for (MacIdLoc,GPS,FSeen,LSeen,Address,Name) in locationinfo:
                # To avoid the errors when inserting in the db from old databases
                Address = Address.encode('utf-8').replace('"','').replace('<','').replace('>','').replace('/', '')
                Name = Name.encode('utf-8').replace('"','').replace('<','').replace('>', '').replace('/', '')
                if debug:
                    print '{} {} {} {} {} {}'.format(MacIdLoc,GPS,FSeen,LSeen,Address,Name)
                newMacId = db_get_id_from_mac(db_merged_connection,Mac)
                if debug:
                    print 'New macId: {}'.format(newMacId)
                try:
                    result = db_merged_connection.execute("INSERT OR IGNORE INTO Locations (MacId, GPS, FirstSeen, LastSeen, Address, Name) VALUES("+str(newMacId)+",\""+str(GPS)+"\",\""+str(FSeen)+"\",\""+str(LSeen)+"\",\""+str(Address)+"\",\""+str(Name)+"\");")
                except:
                    print "Exception in sql query: \"INSERT OR IGNORE INTO Locations (MacId, GPS, FirstSeen, LastSeen, Address, Name) VALUES(\""
                    print str(GPS)+","+str(FSeen)+","+str(LSeen)+","+str(Address)+","+str(Name).encode('utf-8')

                    sys.exit(0)
                count_loc = count_loc+1

            db_merged_connection.commit()

            #Adding data from notes table
            try:
                result = db_to_merge_connection.execute("SELECT Id,Note FROM Notes WHERE Id="+str(MacId)+";")
            except:
                print "Exeption in sql query: \"SELECT Id,Note FROM Notes WHERE Id=\""
                sys.exit(0)
            notesinfo = result.fetchall()
            for (Id,Note) in notesinfo:
                newMacId = db_get_id_from_mac(db_merged_connection,Mac)
                try:
                    result = db_merged_connection.execute("INSERT OR IGNORE INTO Notes (Id, Note) VALUES("+str(newMacId)+",\""+str(Note)+"\");")
                except:
                    print "Exception in sql query: \"INSERT OR IGNORE INTO Notes (Id, Note) VALUES(\""
                    sys.exit(0)
                count_not = count_not+1

            #Adding data from alarm table
            try:
                result = db_to_merge_connection.execute("SELECT Id,Alarm FROM Alarms WHERE Id="+str(MacId)+";")
            except:
                print "Error in sql query: \"SELECT Id,Alarm FROM Alarms WHERE MacId=\""
            notesinfo = result.fetchall()
            for (Id,alarm) in notesinfo:
                newMacId = db_get_id_from_mac(db_merged_connection,Mac)
                try:
                    result = db_merged_connection.execute("INSERT OR IGNORE INTO Alarms (Id, Alarm) VALUES("+str(newMacId)+",\""+str(alarm)+"\");")
                except:
                    print "Exception in sql query: \"INSERT OR IGNORE INTO Alarms (Id, Alarm) VALUES(\""
                    sys.exit(0)
                count_ala = count_ala+1

            if debug:
                print "Amount of devices processed: {}".format(count_dev)
                print "Amount of locations processed: {}".format(count_loc)
                print "Amount of notes processed: {}".format(count_not)
                print "Amount of alarms processed: {}".format(count_ala)

        db_merged_connection.commit()
        db_to_merge_connection.close()

    except KeyboardInterrupt:
        print 'Exiting. It may take a few seconds.'
        sys.exit(1)
    except Exception as inst:
        print 'Exception in db_merge(database_name) function'
        print 'Ending threads, exiting when finished'
        print type(inst) # the exception instance
        print inst.args # arguments stored in .args
        print inst # _str_ allows args to printed directly
        x, y = inst # _getitem_ allows args to be unpacked directly
        print 'x =', x
        print 'y =', y
        sys.exit(1)

def db_list_devices(connection, limit):
    """
    This function returns a list of devices (macs). Variable limit can limit the results
    """
    global debug
    global verbose

    devices=""

    try:
        try:
            result = connection.execute("SELECT Mac FROM Devices LIMIT "+str(limit))
            devices = result.fetchall()
            return devices
        except:
            return False
    
    except KeyboardInterrupt:
        print 'Exiting. It may take a few seconds.'
        sys.exit(1)
    except Exception as inst:
        print 'Exception in db_list_devices(connection) function'
        print 'Ending threads, exiting when finished'
        print type(inst) # the exception instance
        print inst.args # arguments stored in .args
        print inst # _str_ allows args to printed directly
        x, y = inst # _getitem_ allows args to be unpacked directly
        print 'x =', x
        print 'y =', y
        sys.exit(1)


def db_list_devices_and_names(connection, limit):
    """
    This function returns a list of MAC, Names of an amount of devices defined by the parameter limit.
    """
    global debug
    global verbose

    devices=""
    deviceswname=[]

    try:
        try:
            result = connection.execute("SELECT Id,Mac FROM Devices LIMIT "+str(limit))
            devices = result.fetchall()
            for dev in devices:
                name=""
                result = connection.execute("SELECT Name FROM Locations WHERE MacId=\""+str(dev[0])+"\" LIMIT 1") 
                name = result.fetchall()
                if not name:
                    print 'The device existed, but there are no locations for it. Maybe a broken merge.'
                    continue
                deviceswname.append([dev[1],name[0][0]])
                if debug:
                    print "{} - {} - {}".format(dev[0],dev[1],name[0][0])
            if debug:
                print deviceswname
            return deviceswname
        except:
            print "Exception in db_list_devices_and_names"
            return False
    
    except KeyboardInterrupt:
        print 'Exiting. It may take a few seconds.'
        sys.exit(1)
    except Exception as inst:
        print 'Exception in db_list_devices_and_names(connection,limit) function'
        print 'Ending threads, exiting when finished'
        print type(inst) # the exception instance
        print inst.args # arguments stored in .args
        print inst # _str_ allows args to printed directly
        x, y = inst # _getitem_ allows args to be unpacked directly
        print 'x =', x
        print 'y =', y
        sys.exit(1)

def db_device_exists(connection, mac):
    """
    This function returns true if the given mac is stored on the database 
    """
    global debug
    global verbose

    device=""
    result=False

    try:
        try:
            result = connection.execute("SELECT Id FROM Devices WHERE Mac=\""+str(mac)+"\"") 
            if result:
                device = result.fetchall()
                if device:
                    return True
                else:
                    return False
            else:
                print "no result"
                return False
            
        except:
            print "Exception in db_device_exists"
            return False
    
    except KeyboardInterrupt:
        print 'Exiting. It may take a few seconds.'
        sys.exit(1)
    except Exception as inst:
        print 'Exception in db_device_exists(connection) function'
        print 'Ending threads, exiting when finished'
        print type(inst) # the exception instance
        print inst.args # arguments stored in .args
        print inst # _str_ allows args to printed directly
        x, y = inst # _getitem_ allows args to be unpacked directly
        print 'x =', x
        print 'y =', y
        sys.exit(1)

def db_grep_names(connection,string):
    """
    This function returns devices which names are similar to the given string
    """
    global debug
    global verbose

    try:
        try:
            result = connection.execute("SELECT DISTINCT MacId,Name FROM Locations WHERE Name LIKE \"%"+str(string)+"%\"") 
            if result:
                result = result.fetchall()
                return result
            else:  
                return False
            
        except:
            print "Exception in db_grep_names()"
            return False
    
    except KeyboardInterrupt:
        print 'Exiting. It may take a few seconds.'
        sys.exit(1)
    except Exception as inst:
        print 'Exception in db_grep_names(connection,string) function'
        print 'Ending threads, exiting when finished'
        print type(inst) # the exception instance
        print inst.args # arguments stored in .args
        print inst # _str_ allows args to printed directly
        x, y = inst # _getitem_ allows args to be unpacked directly
        print 'x =', x
        print 'y =', y
        sys.exit(1)

def db_update_address(connection,mac=False):
    """
    
    """
    global debug
    global verbose

    result = ""
    addr=""
    MacId=""
    GPS=""
    Address=""

    try:
            if mac:
                macid = db_get_id_from_mac(connection, mac)
                result = connection.execute("SELECT MacId,GPS,Address FROM Locations WHERE MacId="+str(macid)+";") 
            else:
                result = connection.execute("SELECT MacId,GPS,Address FROM Locations WHERE Address like \"NO ADDRESS RETRIEVED\" OR Address=\"\";") 
            if result:
                result = result.fetchall()
                print
                for (MacId,GPS,Address) in result:
                    if GPS != 'False':
                        if Address in ['NO ADDRESS RETRIEVED','']:
                            temp= getCoordinates(GPS)
                            temp= getCoordinates(str(GPS.strip("\'").strip("\'")))
                            addr = temp[1]
                            addr = addr.encode('utf-8')
                            result_update = connection.execute("UPDATE Locations SET Address=? WHERE MacId=? AND GPS=?;",(repr(addr),str(MacId),str(GPS))) 
                            print 'Updating {}'.format(mac)
                            print '   {} :: {} :: {}'.format(GPS, Address.encode('utf-8'), addr)
                        else:
                            print 'Address of the device already exists: {}'.format(mac)
                            print '   {} :: {}'.format(GPS, Address.encode('utf-8'))

                    else:
                        print 'No location stored for device {}'.format(mac)
                        print '   {} {} {}'.format(MacId, GPS, Address)
                    time.sleep(1)
                    print
            else:  
                print 'No results found with empty address to update.'
            connection.commit()
    
    except KeyboardInterrupt:
        print 'Exiting. It may take a few seconds.'
        sys.exit(1)
    except Exception as inst:
        print 'Exception in db_update_address(connection,mac=False) function'
        print 'Ending threads, exiting when finished'
        print type(inst) # the exception instance
        print inst.args # arguments stored in .args
        print inst # _str_ allows args to printed directly
        x, y = inst # _getitem_ allows args to be unpacked directly
        print 'x =', x
        print 'y =', y
        sys.exit(1)


def db_grep_locations(connection,coordinates):
    """
    This function returns a list of mac, name and first seen of devices that are near the given coordinates.
    """
    global debug
    global verbose

    try:
        try:
            if debug:
                print "On db_grep_locations()"
                print "Coordinates to search: {}".format(coordinates)
            result = connection.execute("SELECT Name,MacId,FirstSeen,GPS FROM Locations WHERE GPS LIKE \""+str(coordinates)+"\";") 
            if result:
                result = result.fetchall()
                if debug:
                    print "Result:"
                    print result
                return result
            else:  
                if debug:
                    print 'Result is empty'
                return False
            
        except:
            print "Exception in db_grep_locations()"
            return False
    
    except KeyboardInterrupt:
        print 'Exiting. It may take a few seconds.'
        sys.exit(1)
    except Exception as inst:
        print 'Exception in db_grep_locations(connection,coordinates) function'
        print 'Ending threads, exiting when finished'
        print type(inst) # the exception instance
        print inst.args # arguments stored in .args
        print inst # _str_ allows args to printed directly
        x, y = inst # _getitem_ allows args to be unpacked directly
        print 'x =', x
        print 'y =', y
        sys.exit(1)


def db_rank_devices(connection,limit):
    """
    This function returns a list of devices and the amount of times that were observed. Number of results is defined by limit.
    """
    global debug
    global verbose

    result = ""
    try:
        try:
            result = connection.execute("SELECT Name, MacId, count(MacId) as amount FROM Locations GROUP BY MacId ORDER BY amount DESC LIMIT "+str(limit)+" ;") 
            result = result.fetchall()
            
            if result:
                return result
            else:
                return False
        except:
            print "Exception in db_rank_devices()"
            return False
    
    except KeyboardInterrupt:
        print 'Exiting. It may take a few seconds.'
        sys.exit(1)
    except Exception as inst:
        print 'Exception in db_rank_devices(connection,limit) function'
        print 'Ending threads, exiting when finished'
        print type(inst) # the exception instance
        print inst.args # arguments stored in .args
        print inst # _str_ allows args to printed directly
        x, y = inst # _getitem_ allows args to be unpacked directly
        print 'x =', x
        print 'y =', y
        sys.exit(1)


def db_remove_device(connection, mac):
    """
    This function removes a device from the database
    """
    global debug
    global verbose

    try:
        try:
            #Here we check that the device is present on the database
            exists = db_device_exists(connection, mac)
            if exists:
                    result = connection.execute("SELECT Id FROM Devices WHERE Mac=\""+str(mac)+"\" LIMIT 1")
                    id = result.fetchall()
                    id = id[0][0]
                    try:
                            result = connection.execute("DELETE FROM Locations WHERE MacId = "+str(id))
                    except:
                            if debug:
                                print "No rows affected"
                    try:
                            result = connection.execute("DELETE FROM Alarms WHERE Id = "+str(id))
                    except:
                            if debug:
                                print "No rows affected"
                    try:
                            result = connection.execute("DELETE FROM Notes WHERE Id = "+str(id))
                    except:
                            if debug:
                                print "No rows affected"
                    try:
                            result = connection.execute("DELETE FROM Devices WHERE Id = "+str(id))
                    except:
                            if debug:
                                print "No rows affected"
                    
                    connection.commit()

                    print "Checking if the deletion was efective"
                    result = connection.execute("SELECT Mac FROM Devices WHERE Id = "+str(id))
                    result = result.fetchall()
                    if not result:
                        print "\t[-] Deletion from Devices was effectve"
                    result = connection.execute("SELECT Id FROM Locations WHERE MacId = "+str(id))
                    result = result.fetchall()
                    if not result:
                        print "\t[-] Deletion from Locations was effectve"
                    result = connection.execute("SELECT Id FROM Alarms WHERE Id = "+str(id))
                    result = result.fetchall()
                    if not result:
                        print "\t[-] Deletion from Alarms was effectve"
                    result = connection.execute("SELECT Id FROM Notes WHERE Id = "+str(id))
                    result = result.fetchall()
                    if not result:
                        print "\t[-] Deletion from Notes was effectve"
        except:
            print "Exception in db_remove_device(connection,mac)"
            return False
    
    except KeyboardInterrupt:
        print 'Exiting. It may take a few seconds.'
        sys.exit(1)
    except Exception as inst:
        print 'Exception in db_remove_device(connection,mac) function'
        print 'Ending threads, exiting when finished'
        print type(inst) # the exception instance
        print inst.args # arguments stored in .args
        print inst # _str_ allows args to printed directly
        x, y = inst # _getitem_ allows args to be unpacked directly
        print 'x =', x
        print 'y =', y
        sys.exit(1)

def steam_vendors_names(vendor):
    """
    """
    try:
        global debug
        global verbose

        steamed_vendor = ''

        if 'samsung' in vendor.lower():
            steamed_vendor = 'Samsung'
        elif 'nokia' in vendor.lower():
            steamed_vendor = 'Nokia'
        elif 'parrot' in vendor.lower():
            steamed_vendor = 'Parrot'
        elif 'garmin' in vendor.lower():
            steamed_vendor = 'Garmin'
        elif 'ericsson' in vendor.lower():
            steamed_vendor = 'Ericsson'
        elif 'lg' in vendor.lower():
            steamed_vendor = 'LG'
        elif 'hon hai precision' in vendor.lower():
            steamed_vendor = 'Hon Hai Precision'
        elif 'apple' in vendor.lower():
            steamed_vendor = 'Apple'
        elif 'research in motion' in vendor.lower() or 'rim' in vendor.lower():
            steamed_vendor = 'RIM'
        elif 'motorola' in vendor.lower():
            steamed_vendor = 'Motorola'
        elif 'cisco' in vendor.lower():
            steamed_vendor = 'Cisco'
        else:
            steamed_vendor = vendor

        return steamed_vendor
   
    except KeyboardInterrupt:
        print 'Exiting. It may take a few seconds.'
        sys.exit(1)
    except Exception as inst:
        print 'Exception in steam_vendors_names function'
        print 'Ending threads, exiting when finished'
        print type(inst) # the exception instance
        print inst.args # arguments stored in .args
        print inst # _str_ allows args to printed directly
        sys.exit(1)


def db_update_vendor(connection, mac):
    """
    Get a mac and if its vendor is not in the db, look it up and update the db.
    """
    try:
        global debug
        global verbose
        import os

        
        if debug:
            print 'Updating vendor for mac {}'.format(mac)

        # Get the curent vendor for this mac
        try:
            ((vendor,),) = connection.execute("SELECT Vendor FROM Devices WHERE mac like '%" + mac + "%'")
        except :
            if debug:
                print 'There was no column vendor!! Maybe an old database? Add it manually.'
            exit(-1)


        # If there is no vendor, get it
        if vendor == None or vendor == '':
            if debug:
                print 'Getting the vendor from internet.'
            vendor = os.popen("wget -qO- 'http://www.coffer.com/mac_find/?string=" + mac + "'|grep -i 'class=\"Table2\"><a'|awk -F\"q=\" '{print $2}'|awk -F\> '{print $1}' |uniq").read().strip('\n').split('\n')[0][:-1] 
            if debug:
                print 'Vendor: {0}'.format(vendor)

            if debug:
                print 'Updating the database.'
            try:
                connection.execute("UPDATE Devices SET Vendor='" + str(vendor)+ "' WHERE mac like '%" + mac + "%'")
                connection.commit()
            except :
                if debug:
                    print 'There was no column vendor'
                exit(-1)

            # If you need to verify the writing
            #(vendor,) = connection.execute("SELECT Vendor FROM Devices WHERE mac like '%" + mac + "%'")
            #for a in vendor:
                #print a
        #elif vendor != (None,):
            #print vendor

        return vendor

    except KeyboardInterrupt:
        print 'Exiting. It may take a few seconds.'
        sys.exit(1)
    except Exception as inst:
        print 'Exception in db_update_vendor function'
        print 'Ending threads, exiting when finished'
        print type(inst) # the exception instance
        print inst.args # arguments stored in .args
        print inst # _str_ allows args to printed directly
        sys.exit(1)




def get_locations_and_dates(connection, mac):
    """
    Get a mac address and return all its locations, dates and vendor
    """
    try:
        global debug
        global verbose
        global quiet


        if debug:
            print '* In get locations and dates from device'
        addresslist = {}
        address = ""
        address_to_insert = ""

        locations_dates_results = db_locations_and_dates(connection,mac)

        # Update the mac vendor if it is not there.
        vendor = db_update_vendor(connection, str(mac))

        # Get the steamed version also
        steamed_vendor = steam_vendors_names(vendor)

        if not quiet:
            print "\tMAC Address: {0}. Vendor: {1}. Steamed Vendor: {2}".format(mac,vendor,steamed_vendor)

        # Get all the locations from the db for this mac
        for (Id,gps,fseen,lseen,name,address) in locations_dates_results:
            address = address.encode('utf-8')
            gps = str(gps)


            if debug:
                print '\n\n* This is the data that is currently being processed:'
                print '* Id: {}, GPS: {}, FirstSeen: {}, LastSeen: {}, Name: {}, Address: {}'.format(Id,gps,fseen,lseen,name,address)
                print


            #if (str(gps) != "False") or (str(gps) != ' ') or (str(gps) != 'GPS') or ('NO GPS' not in str(gps)):
            #if ( len(gps.split(',')) == 2 and len(gps.split(',')[0].split('.')) == 2 and len(gps.split(',')[1].split('.')) == 2 ):

            # Search for a proper gps position string using regular expresions
            import re
            gpspattern = re.compile('[0-9]+\.[0-9]+,[0-9]+\.[0-9]+')
            if ( gpspattern.search(gps) ):
                if debug:
                    print '* gps: {} is not \'False\' nor empty nor \'GPS\''.format(gps)
                    print 
                if ('NO ADDRESS' in address) or (len(address)<8):
                    if debug:
                        print '* address: {} is not \'NO ADDRESS\' nor empty'.format(address)
                        print
                    try:
                        address_to_insert = addresslist[gps]
                        if debug:
                            print '* Address to insert: {}'.format(address_to_insert)
                            print
                        print 'Address cached: {}'.format(address_to_insert)
                    except KeyboardInterrupt: 
                        print 'Exiting'
                        sys.exit(1)
                        break
                    except:
                        # This can be deleted. There is nothing here that is not a proper gps...
                        try:
                            gps.split(",")[1]
                        except:
                            print '\t\tNO GPS.'
                            print "\t\t\tIgnoring: {}: {}-{}, {} ({})".format(name, fseen, lseen, gps, str(address_to_insert))
                            break
                        #time.sleep(1)
                        a = gps
                        addr = getCoordinates(str(a.strip("\'").strip("\'")))
                        address_to_insert = addr[1]
                        address_to_insert = address_to_insert.encode('utf-8')
                        try:
                            addresslist[gps]=address_to_insert 
                        except:
                            print 'Cannot add new address to cache'
                    try:
                        if debug:
                            print '* Updating Locations table, setting address.'
                        if len(address_to_insert) > 5:
                                connection.execute("UPDATE Locations SET Address=\""+str(address_to_insert)+"\" WHERE Id="+str(Id))
                                connection.commit()
                                print "\t\t*{}: {}-{}, {} ({})".format(name, fseen, lseen, gps, str(address_to_insert))
                        else:
                                print '\t\tAddress content seems incorrect'
                                print "\t\t\tNot updating: {}: {}-{}, {} ({})".format(name, fseen, lseen, gps, str(address_to_insert))
                    except KeyboardInterrupt: 
                        print 'Exiting'
                        sys.exit(1)
                        break
                    except:
                        print "Exception updating device address"
                        print "{}".format(gps)
                        print "{}".format(address)
                        print "{}".format(address_to_insert)
                else:
                    if debug:
                        print 'Address already exists'
                    print "\t\t{}: {}-{}, {} ({})".format(name, fseen, lseen, gps, address)
            else:
                if debug:
                    print 'There is no GPS.'
                print "\t\t#{}: {}-{}, {} ({})".format(name, fseen, lseen, gps, address)


    except KeyboardInterrupt:
        print 'Exiting. It may take a few seconds.'
        sys.exit(1)
    except Exception as inst:
        print 'Exception in get_locations_and_dates() function'
        print 'Ending threads, exiting when finished'
        print type(inst) # the exception instance
        print inst.args # arguments stored in .args
        print inst # _str_ allows args to printed directly
        sys.exit(1)





def main():
    """
    manageDB.py is a tool that allows to query and manage the database generated by bluedriving. Use -h for help.
    """
    global debug
    global verbose
    global quiet

    database=""
    connection=""
    get_devices=""
    get_devices_with_names=""
    device_mac=""
    device_exists = False
    remove_device = False
    grep_names = False
    rank_devices = False
    ranking=""
    limit=99999999
    merge_db=False
    db_to_merge=""
    db_count=False
    create_db=False
    locations_and_dates=False
    grep_locations=False
    coordinates=""
    update_address=False

    try:

        # By default we crawl a max of 5000 distinct URLs
        opts, args = getopt.getopt(sys.argv[1:], "hDd:l:enE:R:g:r:qm:Cc:L:S:A", ["help","debug","database-name=","limit=","get-devices","get-devices-with-names","device-exists=","remove-device=","grep-names=","rank-devices=","quiet","merge-with=","count-devices","create-db=","get-locations-with-dates=","grep-locations=","all-data"])
    except:
        usage()
        exit(-1)

    for opt, arg in opts:
        if opt in ("-h", "--help"): usage(); sys.exit()
        if opt in ("-D", "--debug"): debug = True
        if opt in ("-d", "--database"): database = arg
        if opt in ("-l", "--limit"): limit = arg
        if opt in ("-e","--get-devices"): get_devices = True
        if opt in ("-n","--get-devices-with-names"): get_devices_with_names = True
        if opt in ("-E","--device-exists"): device_mac = arg; device_exists=True
        if opt in ("-R","--remove-device"): device_mac = arg; remove_device=True
        if opt in ("-g","--grep-names"): string = arg; grep_names=True
        if opt in ("-r","--rank-devices"): limit = arg; rank_devices=True
        if opt in ("-q","--quiet-devices"): quiet=True
        if opt in ("-m","--merge-with"): db_to_merge=arg; merge_db=True
        if opt in ("-C","--count-devices"): db_count=True
        if opt in ("-c", "--create-db"): database = arg; create_db=True
        if opt in ("-L", "--get-locations-with-dates"): mac = arg; locations_and_dates=True
        if opt in ("-S", "--grep-locations"): coordinates = arg; grep_locations=True
        if opt in ("-A", "--all-data"): all_data = True

    try:
        if create_db:
            result = db_create(database)
            if result:
                print '[+] Database created'
            else:
                print '[+] Database not created'
            sys.exit()

        if database:
            if not quiet:
                version()
                print "[+] Database: {}".format(database)
            import os
            if not os.path.isfile(database):
                print 'The database does not exists.'
                exit(-1)
            connection = db_connect(database)

            if connection:
                if not quiet:
                    print "[+] Connection established"

                #List devices
                if get_devices:
                    devices = db_list_devices(connection, limit)
                    if devices:
                        if not quiet:
                            print "[+] List of devices in the database:"
                        for key in devices:
                            print "\t{}".format(key[0])
                # List devices with name
                elif get_devices_with_names:
                    deviceswnames= db_list_devices_and_names(connection,limit)
                    if deviceswnames:
                        for (mac,name) in deviceswnames:
                            print "\t{} - {}".format(mac,name)
                elif device_exists:
                    exists = db_device_exists(connection,device_mac)
                    if exists:
                        print "\tDevice {} exists in the database".format(device_mac)
                    else:
                        print "\tDevice {} is not present in the database".format(device_mac)
                elif remove_device:
                    db_remove_device(connection,device_mac)
                    exists = db_device_exists(connection,device_mac)
                    if exists:
                        print "\tDevice {} exists in the database".format(device_mac)
                    else:
                        print "\tDevice {} is not present in the database".format(device_mac)
                elif grep_names:
                    similar_names = db_grep_names(connection,string)
                    if similar_names:
                        for (macId,name) in similar_names:
                            mac = db_get_mac_from_id(connection,macId)
                            print "\t{} | {}".format(mac, name)
                elif rank_devices:
                    ranking = db_rank_devices(connection,limit)
                    if ranking:
                        for (name,macId,count) in ranking:
                            mac = db_get_mac_from_id(connection,macId)
                            print "\t{} - {} ({})".format(count, name, mac)
                elif merge_db:
                    db_to_merge_connection = db_connect(db_to_merge)
                    db_merge(connection,db_to_merge_connection)
                elif db_count:
                    number_of_devices = db_count_devices(connection)
                    print '\tNumber of devices on the database: {}'.format(number_of_devices)

                elif locations_and_dates:
                    # Get all the Locations and dates from the devices
                    get_locations_and_dates(connection, mac)

                elif grep_locations:
                    locations = db_grep_locations(connection,coordinates)
                    if locations:
                        for (name,macid,fseen,gps) in locations:
                            mac = db_get_mac_from_id(connection,macid)
                            print ' {}::{} {} {}'.format(mac,name,fseen,gps)
                elif all_data:
                    
                    # Get all the macs
                    if debug:
                        print 'Getting all the information from all the macs'
                    result = connection.execute("SELECT Mac FROM Devices")
                    # Get the data for all the macs
                    for mac in result:
                        (mac,) = mac
                        get_locations_and_dates(connection, mac)

                else:
                    print "Nothing to do. Please select an option."

                if connection: 
                    connection.commit()
                    connection.close()
                    if not quiet:
                        print "[+] Connection closed"

            else:
                print "A connection to the database could not be retrieved"
        else:
            print "You have to select a database. Use the -d option or -h for help."

    except KeyboardInterrupt:
        print 'Exiting. It may take a few seconds.'
        sys.exit(1)
    except Exception as inst:
        print 'Error in main() function'
        print 'Ending threads, exiting when finished'
        threadbreak = True
        print type(inst) # the exception instance
        print inst.args # arguments stored in .args
        print inst # _str_ allows args to printed directly
        x, y = inst # _getitem_ allows args to be unpacked directly
        print 'x =', x
        print 'y =', y
        sys.exit(1)

if __name__ == '__main__':
        main()



########NEW FILE########
