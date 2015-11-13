__FILENAME__ = LibPebblesCommand
import fnmatch
import logging
import os
import sh
import subprocess
import time

import pebble as libpebble

from PblCommand import PblCommand
import PblAnalytics

PEBBLE_PHONE_ENVVAR='PEBBLE_PHONE'
PEBBLE_ID_ENVVAR='PEBBLE_ID'

class ConfigurationException(Exception):
    pass

class NoCompilerException(Exception):
    """ Returned by PblBuildCommand if we couldn't find the ARM tools """
    pass

class BuildErrorException(Exception):
    """ Returned by PblBuildCommand if there was a compile or link error """
    pass

class AppTooBigException(Exception):
    """ Returned by PblBuildCommand if the app is too big"""
    pass


class LibPebbleCommand(PblCommand):

    def configure_subparser(self, parser):
        PblCommand.configure_subparser(self, parser)
        parser.add_argument('--phone', type=str, default=os.getenv(PEBBLE_PHONE_ENVVAR),
                help='The IP address or hostname of your phone - Can also be provided through PEBBLE_PHONE environment variable.')
        parser.add_argument('--pebble_id', type=str, default=os.getenv(PEBBLE_ID_ENVVAR),
                help='Last 4 digits of the MAC address of your Pebble - Can also be provided through PEBBLE_ID environment variable.')
        parser.add_argument('--verbose', type=bool, default=False, help='Prints received system logs in addition to APP_LOG')

    def run(self, args):
        if not args.phone and not args.pebble_id:
            raise ConfigurationException("Argument --phone or --pebble_id is required (Or set a PEBBLE_{PHONE,ID} environment variable)")
        self.pebble = libpebble.Pebble()
        self.pebble.set_print_pbl_logs(args.verbose)

        if args.phone:
            self.pebble.connect_via_websocket(args.phone)

        if args.pebble_id:
            self.pebble.connect_via_serial(args.pebble_id)

    def tail(self, interactive=False, skip_enable_app_log=False):
        if not skip_enable_app_log:
            self.pebble.app_log_enable()
        if interactive:
            logging.info('Entering interactive mode ... Ctrl-D to interrupt.')
            def start_repl(pebble):
                import code
                import readline
                import rlcompleter

                readline.set_completer(rlcompleter.Completer(locals()).complete)
                readline.parse_and_bind('tab:complete')
                code.interact(local=locals())
            start_repl(self.pebble)
        else:
            logging.info('Displaying logs ... Ctrl-C to interrupt.')
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print "\n"
        self.pebble.app_log_disable()

class PblPingCommand(LibPebbleCommand):
    name = 'ping'
    help = 'Ping your Pebble project to your watch'

    def configure_subparser(self, parser):
        LibPebbleCommand.configure_subparser(self, parser)

    def run(self, args):
        LibPebbleCommand.run(self, args)
        self.pebble.ping(cookie=0xDEADBEEF)

class PblInstallCommand(LibPebbleCommand):
    name = 'install'
    help = 'Install your Pebble project to your watch'

    def get_pbw_path(self):
        return 'build/{}.pbw'.format(os.path.basename(os.getcwd()))

    def configure_subparser(self, parser):
        LibPebbleCommand.configure_subparser(self, parser)
        parser.add_argument('pbw_path', type=str, nargs='?', default=self.get_pbw_path(), help='Path to the pbw to install (ie: build/*.pbw)')
        parser.add_argument('--launch', action='store_true', help='Launch on install (only works over Bluetooth connection)')
        parser.add_argument('--logs', action='store_true', help='Display logs after installing the app')

    def run(self, args):
        LibPebbleCommand.run(self, args)

        if not os.path.exists(args.pbw_path):
            logging.error("Could not find pbw <{}> for install.".format(args.pbw_path))
            return 1

        self.pebble.app_log_enable()

        success = self.pebble.install_app(args.pbw_path, args.launch)

        # Send the phone OS version to analytics
        phoneInfoStr = self.pebble.get_phone_info()
        PblAnalytics.phone_info_evt(phoneInfoStr = phoneInfoStr)

        if success and args.logs:
            self.tail(skip_enable_app_log=True)

class PblInstallFWCommand(LibPebbleCommand):
    name = 'install_fw'
    help = 'Install a Pebble firmware'

    def configure_subparser(self, parser):
        LibPebbleCommand.configure_subparser(self, parser)
        parser.add_argument('pbz_path', type=str, help='Path to the pbz to install')

    def run(self, args):
        LibPebbleCommand.run(self, args)

        if not os.path.exists(args.pbz_path):
            logging.error("Could not find pbz <{}> for install.".format(args.pbz_path))
            return 1

        self.pebble.install_firmware(args.pbz_path)
        time.sleep(5)
        logging.info('Resetting to apply firmware update...')
        self.pebble.reset()

class PblListCommand(LibPebbleCommand):
    name = 'list'
    help = 'List the apps installed on your watch'

    def configure_subparser(self, parser):
        LibPebbleCommand.configure_subparser(self, parser)

    def run(self, args):
        LibPebbleCommand.run(self, args)

        try:
            response = self.pebble.get_appbank_status()
            apps = response['apps']
            if len(apps) == 0:
                logging.info("No apps installed.")
            for app in apps:
                logging.info('[{}] {}'.format(app['index'], app['name']))
        except:
            logging.error("Error getting apps list.")
            return 1

class PblRemoteCommand(LibPebbleCommand):
    name = 'remote'
    help = 'Use Pebble\'s music app as a remote control for a local application'

    def configure_subparser(self, parser):
        LibPebbleCommand.configure_subparser(self, parser)
        parser.add_argument('app_name', type=str, help='Local application name to control')

    def do_oscacript(self, command):
        cmd = "osascript -e 'tell application \""+self.args.app_name+"\" to "+command+"'"
        try:
            return subprocess.check_output(cmd, shell=True)
        except subprocess.CalledProcessError:
            print "Failed to send message to "+self.args.app_name+", is it running?"
            return False

    def music_control_handler(self, endpoint, resp):
        control_events = {
            "PLAYPAUSE": "playpause",
            "PREVIOUS": "previous track",
            "NEXT": "next track"
        }
        if resp in control_events:
            self.do_oscacript(control_events[resp])
        elif resp == 'GET_NOW_PLAYING':
            self.update_metadata()

    def update_metadata(self):
        artist = self.do_oscacript("artist of current track as string")
        title = self.do_oscacript("name of current track as string")
        album = self.do_oscacript("album of current track as string")

        if not artist or not title or not album:
            self.pebble.set_nowplaying_metadata("No Music Found", "", "")
        else:
            self.pebble.set_nowplaying_metadata(title, album, artist)

    def run(self, args):
        LibPebbleCommand.run(self, args)
        self.args = args

        self.pebble.register_endpoint("MUSIC_CONTROL", self.music_control_handler)

        logging.info('Waiting for music control events...')
        try:
            while True:
                self.update_metadata()
                time.sleep(5)
        except KeyboardInterrupt:
            return

class PblRemoveCommand(LibPebbleCommand):
    name = 'rm'
    help = 'Remove an app from your watch'

    def configure_subparser(self, parser):
        LibPebbleCommand.configure_subparser(self, parser)
        parser.add_argument('bank_id', type=int, help="The bank id of the app to remove (between 1 and 8)")

    def run(self, args):
        LibPebbleCommand.run(self, args)

        for app in self.pebble.get_appbank_status()['apps']:
            if app['index'] == args.bank_id:
                self.pebble.remove_app(app["id"], app["index"])
                logging.info("App removed")
                return 0

        logging.info("No app found in bank %u" % args.bank_id)
        return 1

class PblCurrentAppCommand(LibPebbleCommand):
    name = 'current'
    help = 'Get the uuid and name of the current app'

    def run(self, args):
        LibPebbleCommand.run(self, args)

        uuid = self.pebble.current_running_uuid()
        uuid_hex = uuid.translate(None, '-')
        if not uuid:
            return
        elif int(uuid_hex, 16) == 0:
            print "System"
            return

        print uuid
        d = self.pebble.describe_app_by_uuid(uuid_hex)
        if not isinstance(d, dict):
            return
        print "Name: %s\nCompany: %s\nVersion: %d" % (d.get("name"), d.get("company"), d.get("version"))
        return

class PblListUuidCommand(LibPebbleCommand):
    name = 'uuids'
    help = 'List the uuids and names of installed apps'

    def run(self, args):
        LibPebbleCommand.run(self, args)

        uuids = self.pebble.list_apps_by_uuid()
        if len(uuids) is 0:
            logging.info("No apps installed.")

        for uuid in uuids:
            uuid_hex = uuid.translate(None, '-')
            description = self.pebble.describe_app_by_uuid(uuid_hex)
            if not description:
                continue

            print '%s - %s' % (description["name"], uuid)

class PblScreenshotCommand(LibPebbleCommand):
    name = 'screenshot'
    help = 'take a screenshot of the pebble'

    def run(self, args):
        LibPebbleCommand.run(self, args)

        logging.info("Taking screenshot...")
        def progress_callback(amount):
            logging.info("%.2f%% done..." % (amount*100.0))

        image = self.pebble.screenshot(progress_callback)
        name = time.strftime("pebble-screenshot_%Y-%m-%d_%H-%M-%S.png")
        image.save(name, "PNG")
        logging.info("Screenshot saved to %s" % name)

        # Open up the image in the user's default image viewer. For some
        # reason, this doesn't seem to open it up in their webbrowser,
        # unlike how it might appear. See
        # http://stackoverflow.com/questions/7715501/pil-image-show-doesnt-work-on-windows-7
        try:
            import webbrowser
            webbrowser.open(name)
        except:
            logging.info("Note: Failed to open image, you'll have to open it "
                         "manually if you want to see what it looks like ("
                         "it has still been saved, however).")

class PblLogsCommand(LibPebbleCommand):
    name = 'logs'
    help = 'Continuously displays logs from the watch'

    def configure_subparser(self, parser):
        LibPebbleCommand.configure_subparser(self, parser)

    def run(self, args):
        LibPebbleCommand.run(self, args)
        self.tail()

class PblLaunchApp(LibPebbleCommand):
    name = 'launch'
    help = 'Launch an application.'

    def configure_subparser(self, parser):
        LibPebbleCommand.configure_subparser(self, parser)
        parser.add_argument('app_uuid', type=int, help="a valid app UUID in the form of: 54D3008F0E46462C995C0D0B4E01148C")

    def run(self, args):
        LibPebbleCommand.run(self, args)
        self.pebble.launcher_message(args.app_uuid, "RUNNING")

class PblReplCommand(LibPebbleCommand):
    name = 'repl'
    help = 'Launch an interactive python shell with a `pebble` object to execute methods on.'

    def run(self, args):
        LibPebbleCommand.run(self, args)
        self.tail(interactive=True)

########NEW FILE########
__FILENAME__ = LightBluePebble
#!/usr/bin/env python
import logging as log
import multiprocessing
import os
import Queue
import re
import socket
from multiprocessing import Process
from struct import unpack

class LightBluePebbleError(Exception):
    def __init__(self, id, message):
        self._id = id
        self._message = message

    def __str__(self):
        return "%s ID:(%s) on LightBlue API" % (self._message, self._id)

class LightBluePebble(object):
    """ a wrapper for LightBlue that provides Serial-style read, write and close"""

    def __init__(self, id, should_pair, debug_protocol=False, connection_process_timeout=60):

        self.mac_address = id
        self.debug_protocol = debug_protocol
        self.should_pair = should_pair

        manager = multiprocessing.Manager()
        self.send_queue = manager.Queue()
        self.rec_queue = manager.Queue()

        self.bt_teardown = multiprocessing.Event()
        self.bt_message_sent = multiprocessing.Event()
        self.bt_connected = multiprocessing.Event()

        self.bt_socket_proc = Process(target=self.run)
        self.bt_socket_proc.daemon = True
        self.bt_socket_proc.start()

        # wait for a successful connection from child process before returning to main process
        self.bt_connected.wait(connection_process_timeout)
        if not self.bt_connected.is_set():
            raise LightBluePebbleError(id, "Connection timed out, LightBlueProcess was provided %d seconds to complete connecting" % connection_process_timeout)

    def write(self, message):
        """ send a message to the LightBlue processs"""
        try:
            self.send_queue.put(message)
            self.bt_message_sent.wait()
        except:
            self.bt_teardown.set()
            if self.debug_protocol:
                log.debug("LightBlue process has shutdown (queue write)")

    def read(self):
        """ read a pebble message from the LightBlue processs"""
        try:
            tup = self.rec_queue.get()
            return tup
        except Queue.Empty:
            return (None, None, '')
        except:
            self.bt_teardown.set()
            if self.debug_protocol:
                log.debug("LightBlue process has shutdown (queue read)")
            return (None, None, '')

    def close(self):
        """ close the LightBlue connection process"""
        self.bt_teardown.set()

    def is_alive(self):
        return self.bt_socket_proc.is_alive()

    def run(self):
        """ create bluetooth process paired to mac_address, must be run as a process"""
        from lightblue import pair, socket as lb_socket, finddevices, selectdevice

        def autodetect(self):
            list_of_pebbles = list()

            if self.mac_address is not None and len(self.mac_address) is 4:
                # we have the friendly name, let's get the full mac address
                log.warn("Going to get full address for device %s, ensure device is broadcasting." % self.mac_address)
                # scan for active devices
                devices = finddevices(timeout=8)

                for device in devices:
                    if re.search(r'Pebble ' + self.mac_address, device[1], re.IGNORECASE):
                        log.debug("Found Pebble: %s @ %s" % (device[1], device[0]))
                        list_of_pebbles.append(device)

                if len(list_of_pebbles) is 1:
                    return list_of_pebbles[0][0]
                else:
                    raise LightBluePebbleError(self.mac_address, "Failed to find Pebble")
            else:
                # no pebble id was provided... give them the GUI selector
                try:
                    return selectdevice()[0]
                except TypeError:
                    log.warn("failed to select a device in GUI selector")
                    self.mac_address = None

        # notify that the process has started
        log.debug("LightBlue process has started on pid %d" % os.getpid())

        # do we need to autodetect?
        if self.mac_address is None or len(self.mac_address) is 4:
            self.mac_address = autodetect(self)

        # create the bluetooth socket from the mac address
        if self.should_pair and self.mac_address is not None:
            pair(self.mac_address)
        try:
            self._bts = lb_socket()
            self._bts.connect((self.mac_address, 1))  # pebble uses RFCOMM port 1
            self._bts.setblocking(False)
        except:
            raise LightBluePebbleError(self.mac_address, "Failed to connect to Pebble")

        # give them the mac address for using in faster connections
        log.debug("Connection established to " + self.mac_address)

        # Tell our parent that we have a pebble connected now
        self.bt_connected.set()

        send_data = e = None
        while not self.bt_teardown.is_set():
            # send anything in the send queue
            try:
                send_data = self.send_queue.get_nowait()
                self._bts.send(send_data)
                if self.debug_protocol:
                    log.debug("LightBlue Send: %r" % send_data)
                self.bt_message_sent.set()
            except Queue.Empty:
                pass
            except (IOError, EOFError):
                self.bt_teardown.set()
                e = "Queue Error while sending data"

            # if anything is received relay it back
            rec_data = None
            try:
                rec_data = self._bts.recv(4)
            except (socket.timeout, socket.error):
                # Exception raised from timing out on nonblocking
                pass

            if (rec_data is not None) and (len(rec_data) == 4):
                # check the Stream Multiplexing Layer message and get the length of the data to read
                size, endpoint = unpack("!HH", rec_data)
                resp = ''
                while len(resp) < size:
                    try:
                        resp += self._bts.recv(size-len(resp))
                    except (socket.timeout, socket.error):
                        # Exception raised from timing out on nonblocking
                        # TODO: Should probably have some kind of timeout here
                        pass
                try:
                    if self.debug_protocol:
                        log.debug("{}: {} {} ".format(endpoint, resp, rec_data))
                    self.rec_queue.put((endpoint, resp, rec_data))

                except (IOError, EOFError):
                    self.BT_TEARDOWN.set()
                    e = "Queue Error while recieving data"
                    pass
                if self.debug_protocol:
                    log.debug("LightBlue Read: %r " % resp)

        # just let it die silent whenever the parent dies and it throws an EOFERROR
        if e is not None and self.debug_protocol:
            raise LightBluePebbleError(self.mac_address, "LightBlue polling loop closed due to " + e)

########NEW FILE########
__FILENAME__ = PblAnalytics
#!/usr/bin/env python


from urllib2 import urlopen, Request
from urllib import urlencode
import datetime
import time
import logging
import os
import platform
import uuid
import pprint
import subprocess


####################################################################
def _running_in_vm():
    """ Return true if we are running in a VM """

    try:
        drv_name = "/proc/scsi/scsi"
        if os.path.exists(drv_name):
            contents = open(drv_name).read()
            if "VBOX" in contents or "VMware" in contents:
                return True
    except:
        pass
        
    return False


####################################################################
####################################################################
class _Analytics(object):
    """ Internal singleton that contains globals and functions for the 
    analytics module """
    
    _instance = None

    @classmethod
    def get(cls):
        if cls._instance is None:
            cls._instance = _Analytics()
        return cls._instance


    ####################################################################
    def __init__(self):
        """ Initialize the analytics module. 
        
        Here we do one-time setup like forming the client id, checking
        if this is the first time running after an install, etc. 
        """
        
        self.tracking_id = 'UA-30638158-7'
        self.endpoint = 'https://www.google-analytics.com/collect'
        
        cur_sdk_version = self._get_sdk_version()
        self.os_str = platform.platform()
        if _running_in_vm():
            self.os_str += " (VM)"
        self.user_agent = 'Pebble SDK/%s (%s-python-%s)' % (cur_sdk_version, 
                            self.os_str, platform.python_version()) 
        
        
        # Get installation info. If we detect a new install, post an 
        # appropriate event
        homeDir = os.path.expanduser("~")
        settingsDir = os.path.join(homeDir, ".pebble")
        if not os.path.exists(settingsDir):
            os.makedirs(settingsDir)
            
        # Get (and create if necessary) the client id
        try:
            clientId = open(os.path.join(settingsDir, "client_id")).read()
        except:
            clientId = None
        if clientId is None:
            clientId = str(uuid.uuid4())
            with open(os.path.join(settingsDir, "client_id"), 'w') as fd:
                fd.write(clientId)

        self.client_id = clientId
            
        # Should we track analytics?
        sdkPath = os.path.normpath(os.path.join(os.path.dirname(__file__), 
                                                '..', '..'))
        dntFile = os.path.join(sdkPath, "NO_TRACKING")
        self.do_not_track = os.path.exists(dntFile)

        # Don't track if internet connection is down
        if not self.do_not_track:
            try:
                urlopen(self.endpoint, timeout=0.1)
            except:
                self.do_not_track = True
                logging.debug("Analytics collection disabled due to lack of"
                              "internet connectivity")
            
        if self.do_not_track:
            return
        
        # Detect if this is a new install and send an event if so
        try:
            cached_version = open(os.path.join(settingsDir, "sdk_version")).read()
        except:
            cached_version = None
        if not cached_version or cached_version != cur_sdk_version:
            with open(os.path.join(settingsDir, "sdk_version"), 'w') as fd:
                fd.write(cur_sdk_version)
            if cached_version is None:
                action = 'firstTime'
            else:
                action = 'upgrade'
            self.post_event(category='install', action=action, 
                           label=cur_sdk_version)
            
        
        
    ####################################################################
    def _get_sdk_version(self):
        """ Get the SDK version """
        try:
            from VersionGenerated import SDK_VERSION
            return SDK_VERSION
        except:
            return "'Development'"
        
        
    ####################################################################
    def post_event(self, category, action, label, value=None):
        """ Send an event to the analytics collection server. 
        
        We are being a little un-orthodox with how we use the fields in the
        event and are hijacking some of the fields for alternature purposes:
        
        Campaign Name ('cn'): We are using this to represent the operating
        system as returned by python.platform(). We tried putting this into the
        user-agent string but it isn't picked up by the Google Analytics web 
        UI for some reason - perhaps it's the wrong format for that purpose. 
        
        Campaign Source ('cs'): We are also copying the client id ('cid') to
        this field. The 'cid' field is not accessible from the web UI but the
        'cs' field is. 
        
        Campaign Keyword ('ck'): We are using this to store the python version. 
        
        
        Parameters:
        ----------------------------------------------------------------
        category: The event category
        action: The event action
        label: The event label
        value: The optional event value (integer)
        """

    
        data = {}
        data['v'] = 1
        data['tid'] = self.tracking_id
        data['cid'] = self.client_id
        
        # TODO: Set this to PEBBLE-INTERNAL or PEBBLE-AUTOMATED as appropriate
        data['cn'] = self.os_str
        data['cs'] = self.client_id
        data['ck'] = platform.python_version()
        
        # Generate an event
        data['t'] = 'event'
        data['ec'] = category
        data['ea'] = action
        data['el'] = label
        if value:
            data['ev'] = value
        else:
            data['ev'] = 0
            
        # Convert all strings to utf-8
        for key,value in data.items():
            if isinstance(value, basestring):
                if isinstance(value, unicode):
                    data[key] = value.encode('utf-8')
                else:
                    data[key] = unicode(value, errors='replace').encode('utf-8')

                
        headers = {
                'User-Agent': self.user_agent
                } 
        
        # We still build up the request but just don't send it if
        #  doNotTrack is on. Building it up allows us to still generate
        #  debug logging messages to see the content we would have sent
        if self.do_not_track:
            logging.debug("Not sending analytics - tracking disabled") 
        else:
            request = Request(self.endpoint,
                          data=urlencode(data),
                          headers = headers)
        
            try:
                urlopen(request, timeout=0.1)
            except Exception as e:
                # Turn off tracking so we don't incur a delay on subsequent
                #  events in this same session. 
                self.do_not_track = True
                logging.debug("Exception occurred sending analytics: %s" %
                              str(e))
                logging.debug("Disabling analytics due to intermittent "
                              "connectivity")
        
        # Debugging output?
        dumpDict = dict(data)
        for key in ['ec', 'ea', 'el', 'ev']:
            dumpDict.pop(key, None)
        logging.debug("[Analytics] header: %s, data: %s"  
                      "\ncategory: %s"  
                      "\naction: %s"    
                      "\nlabel: %s"     
                      "\nvalue: %s" % 
                      (headers, str(dumpDict), 
                       data['ec'], data['ea'], data['el'], data['ev']))
                      
    

####################################################################
# Our public functions for posting events to analytics
def cmd_success_evt(cmdName):
    """ Sent when a pebble.py command succeeds with no error 
    
    Parameters:
    --------------------------------------------------------
    cmdName: name of the pebble command that succeeded (build. install, etc.)
    """
    _Analytics.get().post_event(category='pebbleCmd', action=cmdName, 
                              label='success')


def missing_tools_evt():
    """ Sent when we detect that the ARM tools have not been installed 
    
    Parameters:
    --------------------------------------------------------
    cmdName: name of the pebble command that failed (build. install, etc.)
    reason: description of error (missing compiler, compilation error, 
                outdated project, app too big, configuration error, etc.)
    """
    _Analytics.get().post_event(category='install', action='tools', 
               label='fail: The compiler/linker tools could not be found')
    

def missing_python_dependency_evt(text):
    """ Sent when pebble.py fails to launch because of a missing python
        dependency. 
    
    Parameters:
    --------------------------------------------------------
    text: description of missing dependency
    """
    _Analytics.get().post_event(category='install', action='import', 
               label='fail: missing import: %s' % (text))


def cmd_fail_evt(cmdName, reason):
    """ Sent when a pebble.py command fails  during execution 
    
    Parameters:
    --------------------------------------------------------
    cmdName: name of the pebble command that failed (build. install, etc.)
    reason: description of error (missing compiler, compilation error, 
                outdated project, app too big, configuration error, etc.)
    """
    _Analytics.get().post_event(category='pebbleCmd', action=cmdName, 
               label='fail: %s' % (reason))
    

def code_size_evt(uuid, segSizes):
    """ Sent after a successful build of a pebble app to record the app size
    
    Parameters:
    --------------------------------------------------------
    uuid: application's uuid
    segSizes: a dict containing the size of each segment
                    i.e. {"text": 490, "bss": 200, "data": 100}    
    """
    totalSize = sum(segSizes.values())
    _Analytics.get().post_event(category='appCode', action='totalSize', 
               label=uuid, value = totalSize)


def code_line_count_evt(uuid, c_line_count, js_line_count):
    """ Sent after a successful build of a pebble app to record the number of
    lines of source code in the app
    
    Parameters:
    --------------------------------------------------------
    uuid: application's uuid
    c_line_count: number of lines of C source code
    js_line_count: number of lines of javascript source code
    """
    _Analytics.get().post_event(category='appCode', action='cLineCount', 
               label=uuid, value = c_line_count)
    _Analytics.get().post_event(category='appCode', action='jsLineCount', 
               label=uuid, value = js_line_count)


def code_has_java_script_evt(uuid, hasJS):
    """ Sent after a successful build of a pebble app to record whether or not
    this app has javascript code in it
    
    Parameters:
    --------------------------------------------------------
    uuid: application's uuid
    hasJS: True if this app has JavaScript in it
    """
    _Analytics.get().post_event(category='appCode', action='hasJavaScript', 
               label=uuid, value = 1 if hasJS else 0)


def res_sizes_evt(uuid, resCounts, resSizes):
    """ Sent after a successful build of a pebble app to record the sizes of
    the resources
    
    Parameters:
    --------------------------------------------------------
    uuid: application's uuid
    resCounts: a dict containing the number of resources of each type
                    i.e. {"image": 4, "font": 2, "raw": 1}
    resSizes: a dict containing the size of resources of each type
                    i.e. {"image": 490, "font": 200, "raw": 100}    
    """
    totalSize = sum(resSizes.values())
    totalCount = sum(resCounts.values())
    _Analytics.get().post_event(category='appResources', action='totalSize', 
               label=uuid, value = totalSize)
    _Analytics.get().post_event(category='appResources', action='totalCount', 
               label=uuid, value = totalCount)
    
    for key in resSizes.keys():
        _Analytics.get().post_event(category='appResources', 
                action='%sSize' % (key), label=uuid, value = resSizes[key])
        _Analytics.get().post_event(category='appResources', 
                action='%sCount' % (key), label=uuid, value = resCounts[key])
        
def phone_info_evt(phoneInfoStr):
    """ Sent after a successful install of a pebble app to record the OS
    running on the phone
    
    Parameters:
    --------------------------------------------------------
    phoneInfoStr: Phone info string as returned from pebble.get_phone_info()
                   This is a comma separated string containing OS name, 
                   version, model. For example: "Android,4.3,Nexus 4"
    """
    items = phoneInfoStr.split(',')
    
    _Analytics.get().post_event(category='phone', action='os', 
               label=items[0], value=0)
    if len(items) >= 2:
        _Analytics.get().post_event(category='phone', action='osVersion', 
                   label=items[1], value=0)
    if len(items) >= 3:
        _Analytics.get().post_event(category='phone', action='model', 
                   label=items[2], value=0)





####################################################################
if __name__ == '__main__':
    _Analytics.get().post_event('newCategory', 'newAction', 'newLabel')
    



########NEW FILE########
__FILENAME__ = PblBuildCommand

import logging
import sh, os, subprocess
import json
import StringIO
import traceback
import sys

import PblAnalytics
from PblCommand import PblCommand
from PblProjectCreator import requires_project_dir
from LibPebblesCommand import (NoCompilerException, BuildErrorException,
                               AppTooBigException)



########################################################################
def create_sh_cmd_obj(cmdPath):
    """ Create a sh.Command() instance and check for error condition of
    the executable not in the path. 
    
    If the argument to sh.Command can not be found in the path, then 
    executing it raises a very obscure exception:
        'TypeError: sequence item 0: expected string, NoneType found'
        
    This method raise a more description exception. 
    
    NOTE: If you use the sh.<cmdname>(cmdargs) syntax for calling
    a command instead of sh.Command(<cmdname>), the sh module returns a 
    more descriptive sh.CommandNotFound exception. But, if the cmdname 
    includes a directory path in it, you must use this sh.Command()
    syntax.  
    """
    
    cmdObj = sh.Command(cmdPath)
    
    # By checking the _path member of the cmdObj, we can do a pre-flight to 
    # detect this situation and raise a more friendly error message
    if cmdObj._path is None:
        raise RuntimeError("The executable %s could not be "
                           "found. " % (cmdPath))
    
    return cmdObj
    

###############################################################################
###############################################################################
class PblWafCommand(PblCommand):
    """ Helper class for build commands that execute waf """

    waf_cmds = ""

    ###########################################################################
    def waf_path(self, args):
        return os.path.join(os.path.join(self.sdk_path(args), 'Pebble'), 'waf')
    
    
    ###########################################################################
    def _send_memory_usage(self, args, appInfo):
        """ Send app memory usage to analytics 
        
        Parameters:
        --------------------------------------------------------------------
        args: the args passed to the run() method
        appInfo: the applications appInfo
        """
        
        cmdName = 'arm_none_eabi_size'
        cmdArgs = [os.path.join("build", "pebble-app.elf")]
        try:
            output = sh.arm_none_eabi_size(*cmdArgs)
            (textSize, dataSize, bssSize) = [int(x) for x in \
                                     output.stdout.splitlines()[1].split()[:3]]
            sizeDict = {'text': textSize, 'data': dataSize, 'bss': bssSize}
            PblAnalytics.code_size_evt(uuid=appInfo["uuid"], 
                                    segSizes = sizeDict)
        except sh.ErrorReturnCode as e:
            logging.error("command %s %s failed. stdout: %s, stderr: %s" %
                          (cmdName, ' '.join(cmdArgs), e.stdout, e.stderr))
        except sh.CommandNotFound as e:
            logging.error("The command %s could not be found. Could not "
                          "collect memory usage analytics." % (e.message))


    ###########################################################################
    def _count_lines(self, path, exts):
        """ Count number of lines of source code in the given path. This will
        recurse into subdirectories as well. 
        
        Parameters:
        --------------------------------------------------------------------
        path: directory name to search
        exts: list of extensions to include in the search, i.e. ['.c', '.h']
        """
        
        srcLines = 0
        files = os.listdir(path)
        for name in files:
            if name.startswith('.'):
                continue
            if os.path.isdir(os.path.join(path, name)):
                if not os.path.islink(os.path.join(path, name)):
                    srcLines += self._count_lines(os.path.join(path, name), exts)
                continue
            ext = os.path.splitext(name)[1]
            if ext in exts:
                srcLines += sum(1 for line in open(os.path.join(path, name)))
        return srcLines
    

    ###########################################################################
    def _send_line_counts(self, args, appInfo):
        """ Send app line counts up to analytics 
        
        Parameters:
        --------------------------------------------------------------------
        args: the args passed to the run() method
        appInfo: the applications appInfo
        """
        
        c_line_count = 0
        js_line_count = 0
        if os.path.exists('src'):
            c_line_count += self._count_lines('src', ['.h', '.c'])
            js_line_count += self._count_lines('src', ['.js'])

        PblAnalytics.code_line_count_evt(uuid=appInfo["uuid"], 
                                c_line_count = c_line_count,
                                js_line_count = js_line_count)


    ###########################################################################
    def _send_resource_usage(self, args, appInfo):
        """ Send app resource usage up to analytics 
        
        Parameters:
        --------------------------------------------------------------------
        args: the args passed to the run() method
        appInfo: the applications appInfo
        """
        
        # Collect the number and total size of each class of resource:
        resCounts = {"raw": 0, "image": 0, "font": 0}
        resSizes = {"raw": 0, "image": 0, "font": 0}
        
        for resDict in appInfo["resources"]["media"]:
            if resDict["type"] in ["png", "png-trans"]:
                type = "image"
            elif resDict["type"] in ["font"]: 
                type = "font"
            elif resDict["type"] in ["raw"]:
                type = "raw"
            else:
                raise RuntimeError("Unsupported resource type %s" % 
                                (resDict["type"]))

            # Look for the generated blob in the build/resource directory.
            # As far as we can tell, the generated blob always starts with
            # the original filename and adds an extension to it, or (for
            # fonts), a name and extension. 
            (dirName, fileName) = os.path.split(resDict["file"])
            dirToSearch = os.path.join("build", "resources", dirName)
            found = False
            for name in os.listdir(dirToSearch):
                if name.startswith(fileName):
                    size = os.path.getsize(os.path.join(dirToSearch, name))
                    found = True
                    break
            if not found:
                raise RuntimeError("Could not find generated resource "
                            "corresponding to %s." % (resDict["file"]))
                
            resCounts[type] += 1
            resSizes[type] += size
            
        # Send the stats now
        PblAnalytics.res_sizes_evt(uuid=appInfo["uuid"],
                                 resCounts = resCounts,
                                 resSizes = resSizes)
                

    ###########################################################################
    @requires_project_dir
    def run(self, args):
        os.environ['PATH'] = "{}:{}".format(os.path.join(self.sdk_path(args), 
                                "arm-cs-tools", "bin"), os.environ['PATH'])
        
        cmdLine = self.waf_path(args) + " " + self.waf_cmds
        retval = subprocess.call(cmdLine, shell=True)
        
        # If an error occurred, we need to do some sleuthing to determine a
        # cause. This allows the caller to post more useful information to
        # analytics. We normally don't capture stdout and stderr using Poepn()
        # because you lose the nice color coding produced when the command
        # outputs to a terminal directly.
        #
        # But, if an error occurs, let's run it again capturing the output
        #  so we can determine the cause
          
        if (retval):
            cmdArgs = cmdLine.split()
            try:
                cmdObj = create_sh_cmd_obj(cmdArgs[0])
                output = cmdObj(*cmdArgs[1:])
                stderr = output.stderr
            except sh.ErrorReturnCode as e:
                stderr = e.stderr        
                 
            # Look for common problems
            if "Could not determine the compiler version" in stderr:
                raise NoCompilerException
            
            elif "region `APP' overflowed" in stderr:
                raise AppTooBigException
            
            else:
                raise BuildErrorException
            
        elif args.command == 'build':
            # No error building. Send up app memory usage and resource usage
            #  up to analytics
            # Read in the appinfo.json to get the list of resources
            try:
                appInfo = json.load(open("appinfo.json"))
                self._send_memory_usage(args, appInfo)
                self._send_resource_usage(args, appInfo)
                self._send_line_counts(args, appInfo)
                hasJS = os.path.exists(os.path.join('src', 'js'))
                PblAnalytics.code_has_java_script_evt(uuid=appInfo["uuid"],
                                         hasJS=hasJS)
            except Exception as e:
                logging.error("Exception occurred collecting app analytics: "
                              "%s" % str(e))
                logging.debug(traceback.format_exc())
            
        return 0

    ###########################################################################
    def configure_subparser(self, parser):
        PblCommand.configure_subparser(self, parser)


###########################################################################
###########################################################################
class PblBuildCommand(PblWafCommand):
    name = 'build'
    help = 'Build your Pebble project'
    waf_cmds = 'configure build'

###########################################################################
###########################################################################
class PblCleanCommand(PblWafCommand):
    name = 'clean'
    help = 'Clean your Pebble project'
    waf_cmds = 'distclean'

########NEW FILE########
__FILENAME__ = PblCommand
import os

class PblCommand:
    name = ''
    help = ''

    def run(args):
        pass

    def configure_subparser(self, parser):
        parser.add_argument('--sdk', help='Path to Pebble SDK (ie: ~/pebble-dev/PebbleSDK-2.X/)')

    def sdk_path(self, args):
        """
        Tries to guess the location of the Pebble SDK
        """

        if args.sdk:
            return args.sdk
        else:
            return os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..'))

########NEW FILE########
__FILENAME__ = PblProjectConverter
import json
import os
import re
import shutil

from PblCommand import PblCommand
from PblProjectCreator import *

def read_c_code(c_file_path):

    C_SINGLELINE_COMMENT_PATTERN = '//.*'
    C_MULTILINE_COMMENT_PATTERN = '/\*.*\*/'

    with open(c_file_path, 'r') as f:
        c_code = f.read()

        c_code = re.sub(C_SINGLELINE_COMMENT_PATTERN, '', c_code)
        c_code = re.sub(C_MULTILINE_COMMENT_PATTERN, '', c_code)

        return c_code

def convert_c_uuid(c_uuid):

    C_UUID_BYTE_PATTERN = '0x([0-9A-Fa-f]{2})'
    C_UUID_PATTERN = '^{\s*' + '\s*,\s*'.join([C_UUID_BYTE_PATTERN] * 16) + '\s*}$'

    UUID_FORMAT = "{}{}{}{}-{}{}-{}{}-{}{}-{}{}{}{}{}{}"

    c_uuid = c_uuid.lower()
    if re.match(C_UUID_PATTERN, c_uuid):
        return UUID_FORMAT.format(*re.findall(C_UUID_BYTE_PATTERN, c_uuid))
    else:
        return c_uuid

def extract_c_macros_from_code(c_code, macros={}):

    C_IDENTIFIER_PATTERN = '[A-Za-z_]\w*'
    C_DEFINE_PATTERN = '#define\s+('+C_IDENTIFIER_PATTERN+')\s+\(*(.+)\)*\s*'

    for m in re.finditer(C_DEFINE_PATTERN, c_code):
        groups = m.groups()
        macros[groups[0]] = groups[1].strip()

def extract_c_macros_from_project(project_root, macros={}):
    src_path = os.path.join(project_root, 'src')
    for root, dirnames, filenames in os.walk(src_path):
        for f in filenames:
            file_path = os.path.join(root, f)
            extract_c_macros_from_code(read_c_code(file_path), macros)

    return macros

def convert_c_expr_dict(c_expr_dict, project_root):

    C_STRING_PATTERN = '^"(.*)"$'

    macros = extract_c_macros_from_project(project_root)
    for k, v in c_expr_dict.iteritems():
        if v == None:
            continue

        # Expand C macros
        if v in macros:
            v = macros[v]

        # Format C strings
        m = re.match(C_STRING_PATTERN, v)
        if m:
            v = m.groups()[0].decode('string-escape')

        c_expr_dict[k] = v

    return c_expr_dict

def find_pbl_app_info(project_root):

    C_LITERAL_PATTERN = '([^,]+|"[^"]*")'

    PBL_APP_INFO_PATTERN = (
            'PBL_APP_INFO(?:_SIMPLE)?\(\s*' +
            '\s*,\s*'.join([C_LITERAL_PATTERN] * 4) +
            '(?:\s*,\s*' + '\s*,\s*'.join([C_LITERAL_PATTERN] * 3) + ')?' +
            '\s*\)'
            )

    PBL_APP_INFO_FIELDS = [
            'uuid',
            'project_name',
            'company_name',
            'version_major',
            'version_minor',
            'menu_icon',
            'type'
            ]

    src_path = os.path.join(project_root, 'src')
    for root, dirnames, filenames in os.walk(src_path):
        for f in filenames:
            file_path = os.path.join(root, f)
            m = re.search(PBL_APP_INFO_PATTERN, read_c_code(file_path))
            if m:
                return dict(zip(PBL_APP_INFO_FIELDS, m.groups()))

def extract_c_appinfo(project_root):

    appinfo_c_def = find_pbl_app_info(project_root)
    if not appinfo_c_def:
        raise Exception("Could not find usage of PBL_APP_INFO")

    appinfo_c_def = convert_c_expr_dict(appinfo_c_def, project_root)

    version_major = int(appinfo_c_def['version_major'] or '1', 0)
    version_minor = int(appinfo_c_def['version_minor'] or '0', 0)

    appinfo_json_def = {
        'uuid': convert_c_uuid(appinfo_c_def['uuid']),
        'project_name': appinfo_c_def['project_name'],
        'company_name': appinfo_c_def['company_name'],
        'version_code': version_major,
        'version_label': '{}.{}.0'.format(version_major, version_minor),
        'menu_icon': appinfo_c_def['menu_icon'],
        'is_watchface': 'true' if appinfo_c_def['type'] == 'APP_INFO_WATCH_FACE' else 'false',
        'app_keys': '{}',
        'resources_media': '[]',
    }

    return appinfo_json_def

def load_app_keys(js_appinfo_path):
    with open(js_appinfo_path, "r") as f:
        try:
            app_keys = json.load(f)['app_keys']
        except:
            raise Exception("Failed to import app_keys from {} into new appinfo.json".format(js_appinfo_path))

        app_keys = json.dumps(app_keys, indent=2)
        return re.sub('\s*\n', '\n  ', app_keys)

def load_resources_map(resources_map_path, menu_icon_name=None):

    C_RESOURCE_PREFIX = 'RESOURCE_ID_'

    def convert_resources_media_item(item):
        if item['file'] == 'resource_map.json':
            return None
        else:
            item_name = item['defName']
            del item['defName']
            item['name'] = item_name

            if menu_icon_name and C_RESOURCE_PREFIX + item_name == menu_icon_name:
                item['menuIcon'] = True

            return item

    with open(resources_map_path, "r") as f:
        try:
            resources_media = json.load(f)['media']
        except:
            raise Exception("Failed to import {} into appinfo.json".format(resources_map_path))

        resources_media = filter(None, [convert_resources_media_item(item) for item in resources_media])
        resources_media = json.dumps(resources_media, indent=2)
        return re.sub('\s*\n', '\n    ', resources_media)

def generate_appinfo_from_old_project(project_root, js_appinfo_path=None, resources_media_path=None):
    appinfo_json_def = extract_c_appinfo(project_root)

    if js_appinfo_path and os.path.exists(js_appinfo_path):
        appinfo_json_def['app_keys'] = load_app_keys(js_appinfo_path)

    if resources_media_path and os.path.exists(resources_media_path):
        menu_icon_name = appinfo_json_def['menu_icon']
        appinfo_json_def['resources_media'] = load_resources_map(resources_media_path, menu_icon_name)

    with open(os.path.join(project_root, "appinfo.json"), "w") as f:
        f.write(FILE_DUMMY_APPINFO.substitute(**appinfo_json_def))

def convert_project():
    project_root = os.getcwd()

    js_appinfo_path = os.path.join(project_root, 'src/js/appinfo.json')

    resources_path = 'resources/src'
    resources_media_path = os.path.join(project_root, os.path.join(resources_path, 'resource_map.json'))

    generate_appinfo_from_old_project(
            project_root,
            js_appinfo_path=js_appinfo_path,
            resources_media_path=resources_media_path)

    links_to_remove = [
            'include',
            'lib',
            'pebble_app.ld',
            'tools',
            'waf',
            'wscript'
            ]

    for l in links_to_remove:
        if os.path.islink(l):
            os.unlink(l)

    if os.path.exists('.gitignore'):
        os.remove('.gitignore')

    if os.path.exists('.hgignore'):
        os.remove('.hgignore')

    with open("wscript", "w") as f:
        f.write(FILE_WSCRIPT)

    with open(".gitignore", "w") as f:
        f.write(FILE_GITIGNORE)

    if os.path.exists(js_appinfo_path):
        os.remove(js_appinfo_path)

    if os.path.exists(resources_media_path):
        os.remove(resources_media_path)

    if os.path.exists(resources_path):
        try:
            for f in os.listdir(resources_path):
                shutil.move(os.path.join(resources_path, f), os.path.join('resources', f))
            os.rmdir(resources_path)
        except:
            raise Exception("Could not move all files in {} up one level".format(resources_path))

class PblProjectConverter(PblCommand):
    name = 'convert-project'
    help = """convert an existing Pebble project to the current SDK.

Note: This will only convert the project, you'll still have to update your source to match the new APIs."""

    def run(self, args):
        try:
            check_project_directory()
            print "No conversion required"
        except OutdatedProjectException:
            convert_project()
            print "Project successfully converted!"


########NEW FILE########
__FILENAME__ = PblProjectCreator
import os
import string
import uuid

from PblCommand import PblCommand

class PblProjectCreator(PblCommand):
    name = 'new-project'
    help = 'Create a new Pebble project'

    def configure_subparser(self, parser):
        parser.add_argument("name", help = "Name of the project you want to create")
        parser.add_argument("--javascript", action="store_true", help = "Generate javascript related files")

    def run(self, args):
        print "Creating new project {}".format(args.name)

        # User can give a path to a new project dir
        project_path = args.name
        project_name = os.path.split(project_path)[1]
        project_root = os.path.join(os.getcwd(), project_path)

        project_src = os.path.join(project_root, "src")

        # Create directories
        os.makedirs(project_root)
        os.makedirs(os.path.join(project_root, "resources"))
        os.makedirs(project_src)

        # Create main .c file
        with open(os.path.join(project_src, "%s.c" % (project_name)), "w") as f:
            f.write(FILE_DUMMY_MAIN)

        # Add wscript file
        with open(os.path.join(project_root, "wscript"), "w") as f:
            f.write(FILE_WSCRIPT)

        # Add appinfo.json file
        appinfo_dummy = DICT_DUMMY_APPINFO.copy()
        appinfo_dummy['uuid'] = str(uuid.uuid4())
        appinfo_dummy['project_name'] = project_name
        with open(os.path.join(project_root, "appinfo.json"), "w") as f:
            f.write(FILE_DUMMY_APPINFO.substitute(**appinfo_dummy))

        # Add .gitignore file
        with open(os.path.join(project_root, ".gitignore"), "w") as f:
            f.write(FILE_GITIGNORE)

        if args.javascript:
            project_js_src = os.path.join(project_src, "js")
            os.makedirs(project_js_src)

            with open(os.path.join(project_js_src, "pebble-js-app.js"), "w") as f:
                f.write(FILE_DUMMY_JAVASCRIPT_SRC)



FILE_GITIGNORE = """
# Ignore build generated files
build
"""

FILE_WSCRIPT = """
#
# This file is the default set of rules to compile a Pebble project.
#
# Feel free to customize this to your needs.
#

top = '.'
out = 'build'

def options(ctx):
    ctx.load('pebble_sdk')

def configure(ctx):
    ctx.load('pebble_sdk')

def build(ctx):
    ctx.load('pebble_sdk')

    ctx.pbl_program(source=ctx.path.ant_glob('src/**/*.c'),
                    target='pebble-app.elf')

    ctx.pbl_bundle(elf='pebble-app.elf',
                   js=ctx.path.ant_glob('src/js/**/*.js'))
"""

FILE_DUMMY_MAIN = """#include <pebble.h>

static Window *window;
static TextLayer *text_layer;

static void select_click_handler(ClickRecognizerRef recognizer, void *context) {
  text_layer_set_text(text_layer, "Select");
}

static void up_click_handler(ClickRecognizerRef recognizer, void *context) {
  text_layer_set_text(text_layer, "Up");
}

static void down_click_handler(ClickRecognizerRef recognizer, void *context) {
  text_layer_set_text(text_layer, "Down");
}

static void click_config_provider(void *context) {
  window_single_click_subscribe(BUTTON_ID_SELECT, select_click_handler);
  window_single_click_subscribe(BUTTON_ID_UP, up_click_handler);
  window_single_click_subscribe(BUTTON_ID_DOWN, down_click_handler);
}

static void window_load(Window *window) {
  Layer *window_layer = window_get_root_layer(window);
  GRect bounds = layer_get_bounds(window_layer);

  text_layer = text_layer_create((GRect) { .origin = { 0, 72 }, .size = { bounds.size.w, 20 } });
  text_layer_set_text(text_layer, "Press a button");
  text_layer_set_text_alignment(text_layer, GTextAlignmentCenter);
  layer_add_child(window_layer, text_layer_get_layer(text_layer));
}

static void window_unload(Window *window) {
  text_layer_destroy(text_layer);
}

static void init(void) {
  window = window_create();
  window_set_click_config_provider(window, click_config_provider);
  window_set_window_handlers(window, (WindowHandlers) {
    .load = window_load,
    .unload = window_unload,
  });
  const bool animated = true;
  window_stack_push(window, animated);
}

static void deinit(void) {
  window_destroy(window);
}

int main(void) {
  init();

  APP_LOG(APP_LOG_LEVEL_DEBUG, "Done initializing, pushed window: %p", window);

  app_event_loop();
  deinit();
}
"""

DICT_DUMMY_APPINFO = {
    'company_name': 'MakeAwesomeHappen',
    'version_code': 1,
    'version_label': '1.0.0',
    'is_watchface': 'false',
    'app_keys': """{
    "dummy": 0
  }""",
    'resources_media': '[]'
}

FILE_DUMMY_APPINFO = string.Template("""{
  "uuid": "${uuid}",
  "shortName": "${project_name}",
  "longName": "${project_name}",
  "companyName": "${company_name}",
  "versionCode": ${version_code},
  "versionLabel": "${version_label}",
  "watchapp": {
    "watchface": ${is_watchface}
  },
  "appKeys": ${app_keys},
  "resources": {
    "media": ${resources_media}
  }
}
""")

FILE_DUMMY_JAVASCRIPT_SRC = """\
Pebble.addEventListener("ready",
    function(e) {
        console.log("Hello world! - Sent from your javascript application.");
    }
);
"""

class PebbleProjectException(Exception):
    pass

class InvalidProjectException(PebbleProjectException):
    pass

class OutdatedProjectException(PebbleProjectException):
    pass

def check_project_directory():
    """Check to see if the current directly matches what is created by PblProjectCreator.run.

    Raises an InvalidProjectException or an OutdatedProjectException if everything isn't quite right.
    """

    if not os.path.isdir('src') or not os.path.exists('wscript'):
        raise InvalidProjectException

    if os.path.islink('pebble_app.ld') or os.path.exists('resources/src/resource_map.json'):
        raise OutdatedProjectException

def requires_project_dir(func):
    def wrapper(self, args):
        check_project_directory()
        return func(self, args)
    return wrapper


########NEW FILE########
__FILENAME__ = pebble
#!/usr/bin/env python

import binascii
import datetime
import glob
import itertools
import json
import logging as log
import os
import sh
import signal
import stm32_crc
import struct
import threading
import time
import traceback
import re
import uuid
import zipfile
import WebSocketPebble

from collections import OrderedDict
from struct import pack, unpack
from PIL import Image

DEFAULT_PEBBLE_ID = None #Triggers autodetection on unix-like systems
DEFAULT_WEBSOCKET_PORT = 9000
DEBUG_PROTOCOL = False
APP_ELF_PATH = 'build/pebble-app.elf'

class PebbleBundle(object):
    MANIFEST_FILENAME = 'manifest.json'

    STRUCT_DEFINITION = [
            '8s',   # header
            '2B',   # struct version
            '2B',   # sdk version
            '2B',   # app version
            'H',    # size
            'I',    # offset
            'I',    # crc
            '32s',  # app name
            '32s',  # company name
            'I',    # icon resource id
            'I',    # symbol table address
            'I',    # flags
            'I',    # relocation list start
            'I',    # num relocation list entries
            '16s'   # uuid
    ]

    def __init__(self, bundle_path):
        bundle_abs_path = os.path.abspath(bundle_path)
        if not os.path.exists(bundle_abs_path):
            raise Exception("Bundle does not exist: " + bundle_path)

        self.zip = zipfile.ZipFile(bundle_abs_path)
        self.path = bundle_abs_path
        self.manifest = None
        self.header = None

        self.app_metadata_struct = struct.Struct(''.join(self.STRUCT_DEFINITION))
        self.app_metadata_length_bytes = self.app_metadata_struct.size

        self.print_pbl_logs = False

    def get_manifest(self):
        if (self.manifest):
            return self.manifest

        if self.MANIFEST_FILENAME not in self.zip.namelist():
            raise Exception("Could not find {}; are you sure this is a PebbleBundle?".format(self.MANIFEST_FILENAME))

        self.manifest = json.loads(self.zip.read(self.MANIFEST_FILENAME))
        return self.manifest

    def get_app_metadata(self):

        if (self.header):
            return self.header

        app_manifest = self.get_manifest()['application']

        app_bin = self.zip.open(app_manifest['name']).read()

        header = app_bin[0:self.app_metadata_length_bytes]
        values = self.app_metadata_struct.unpack(header)
        self.header = {
                'sentinel' : values[0],
                'struct_version_major' : values[1],
                'struct_version_minor' : values[2],
                'sdk_version_major' : values[3],
                'sdk_version_minor' : values[4],
                'app_version_major' : values[5],
                'app_version_minor' : values[6],
                'app_size' : values[7],
                'offset' : values[8],
                'crc' : values[9],
                'app_name' : values[10].rstrip('\0'),
                'company_name' : values[11].rstrip('\0'),
                'icon_resource_id' : values[12],
                'symbol_table_addr' : values[13],
                'flags' : values[14],
                'relocation_list_index' : values[15],
                'num_relocation_entries' : values[16],
                'uuid' : uuid.UUID(bytes=values[17])
        }
        return self.header

    def close(self):
        self.zip.close()

    def is_firmware_bundle(self):
        return 'firmware' in self.get_manifest()

    def is_app_bundle(self):
        return 'application' in self.get_manifest()

    def has_resources(self):
        return 'resources' in self.get_manifest()

    def has_javascript(self):
        return 'js' in self.get_manifest()

    def get_firmware_info(self):
        if not self.is_firmware_bundle():
            return None

        return self.get_manifest()['firmware']

    def get_application_info(self):
        if not self.is_app_bundle():
            return None

        return self.get_manifest()['application']

    def get_resources_info(self):
        if not self.has_resources():
            return None

        return self.get_manifest()['resources']

class ScreenshotSync():
    timeout = 60
    SCREENSHOT_OK = 0
    SCREENSHOT_MALFORMED_COMMAND = 1
    SCREENSHOT_OOM_ERROR = 2

    def __init__(self, pebble, endpoint, progress_callback):
        self.marker = threading.Event()
        self.data = ''
        self.have_read_header = False
        self.length_received = 0
        self.progress_callback = progress_callback
        pebble.register_endpoint(endpoint, self.message_callback)

    # Received a reply message from the watch. We expect several of these...
    def message_callback(self, endpoint, data):
        if not self.have_read_header:
            data = self.read_header(data)
            self.have_read_header = True

        self.data += data
        self.length_received += len(data) * 8 # in bits
        self.progress_callback(float(self.length_received)/self.total_length)
        if self.length_received >= self.total_length:
            self.marker.set()

    def read_header(self, data):
        image_header = struct.Struct("!BIII")
        header_len = image_header.size
        header_data = data[:header_len]
        data = data[header_len:]
        response_code, version, self.width, self.height = \
          image_header.unpack(header_data)

        if response_code is not ScreenshotSync.SCREENSHOT_OK:
            raise PebbleError(None, "Pebble responded with nonzero response "
                "code %d, signaling an error on the watch side." %
                response_code)

        if version is not 1:
            raise PebbleError(None, "Received unrecognized image format "
                "version %d from watch. Maybe your libpebble is out of "
                "sync with your firmware version?" % version)

        self.total_length = self.width * self.height
        return data

    def get_data(self):
        try:
            self.marker.wait(timeout=self.timeout)
            return Image.frombuffer('1', (self.width, self.height), \
                self.data, "raw", "1;R", 0, 1)
        except:
            raise PebbleError(None, "Timed out... Is the Pebble phone app connected?")

class EndpointSync():
    timeout = 10

    def __init__(self, pebble, endpoint):
        self.marker = threading.Event()
        pebble.register_endpoint(endpoint, self.callback)

    def callback(self, endpoint, response):
        self.data = response
        self.marker.set()

    def get_data(self):
        try:
            self.marker.wait(timeout=self.timeout)
            return self.data
        except:
            raise PebbleError(None, "Timed out... Is the Pebble phone app connected?")

class PebbleError(Exception):
    def __init__(self, id, message):
        self._id = id
        self._message = message

    def __str__(self):
        return "%s (ID:%s)" % (self._message, self._id)

class Pebble(object):

    """
    A connection to a Pebble watch; data and commands may be sent
    to the watch through an instance of this class.
    """

    endpoints = {
            "TIME": 11,
            "VERSION": 16,
            "PHONE_VERSION": 17,
            "SYSTEM_MESSAGE": 18,
            "MUSIC_CONTROL": 32,
            "PHONE_CONTROL": 33,
            "APPLICATION_MESSAGE": 48,
            "LAUNCHER": 49,
            "LOGS": 2000,
            "PING": 2001,
            "LOG_DUMP": 2002,
            "RESET": 2003,
            "APP": 2004,
            "APP_LOGS": 2006,
            "NOTIFICATION": 3000,
            "RESOURCE": 4000,
            "APP_MANAGER": 6000,
            "SCREENSHOT": 8000,
            "PUTBYTES": 48879,
    }

    log_levels = {
            0: "*",
            1: "E",
            50: "W",
            100: "I",
            200: "D",
            250: "V"
    }


    @staticmethod
    def AutodetectDevice():
        if os.name != "posix": #i.e. Windows
            raise NotImplementedError("Autodetection is only implemented on UNIX-like systems.")

        pebbles = glob.glob("/dev/tty.Pebble????-SerialPortSe")

        if len(pebbles) == 0:
            raise PebbleError(None, "Autodetection could not find any Pebble devices")
        elif len(pebbles) > 1:
            log.warn("Autodetect found %d Pebbles; using most recent" % len(pebbles))
            #NOTE: Not entirely sure if this is the correct approach
            pebbles.sort(key=lambda x: os.stat(x).st_mtime, reverse=True)

        id = pebbles[0][15:19]
        log.info("Autodetect found a Pebble with ID %s" % id)
        return id



    def __init__(self, id = None):
        self.id = id
        self._connection_type = None
        self._ser = None
        self._read_thread = None
        self._alive = True
        self._ws_client = None
        self._endpoint_handlers = {}
        self._internal_endpoint_handlers = {
                self.endpoints["TIME"]: self._get_time_response,
                self.endpoints["VERSION"]: self._version_response,
                self.endpoints["PHONE_VERSION"]: self._phone_version_response,
                self.endpoints["SYSTEM_MESSAGE"]: self._system_message_response,
                self.endpoints["MUSIC_CONTROL"]: self._music_control_response,
                self.endpoints["APPLICATION_MESSAGE"]: self._application_message_response,
                self.endpoints["LAUNCHER"]: self._application_message_response,
                self.endpoints["LOGS"]: self._log_response,
                self.endpoints["PING"]: self._ping_response,
                self.endpoints["APP_LOGS"]: self._app_log_response,
                self.endpoints["APP_MANAGER"]: self._appbank_status_response,
                self.endpoints["SCREENSHOT"]: self._screenshot_response,
        }

    def init_reader(self):
        try:
            log.debug("Initializing reader thread")
            self._read_thread = threading.Thread(target=self._reader)
            self._read_thread.setDaemon(True)
            self._read_thread.start()
            log.debug("Reader thread loaded on tid %s" % self._read_thread.name)
        except PebbleError:
            raise PebbleError(id, "Failed to connect to Pebble")
        except:
            raise

    def connect_via_serial(self, id = None):
        self._connection_type = 'serial'

        if id != None:
            self.id = id
        if self.id is None:
            self.id = Pebble.AutodetectDevice()

        import serial
        devicefile = "/dev/tty.Pebble{}-SerialPortSe".format(self.id)
        log.debug("Attempting to open %s as Pebble device %s" % (devicefile, self.id))
        self._ser = serial.Serial(devicefile, 115200, timeout=1)
        self.init_reader()

    def connect_via_lightblue(self, pair_first = False):
        self._connection_type = 'lightblue'

        from LightBluePebble import LightBluePebble
        self._ser = LightBluePebble(self.id, pair_first)
        signal.signal(signal.SIGINT, self._exit_signal_handler)
        self.init_reader()

    def connect_via_websocket(self, host, port=DEFAULT_WEBSOCKET_PORT):
        self._connection_type = 'websocket'

        WebSocketPebble.enableTrace(False)
        self._ser = WebSocketPebble.create_connection(host, port, connect_timeout=5)
        self.init_reader()

    def _exit_signal_handler(self, signum, frame):
        log.warn("Disconnecting before exiting...")
        self.disconnect()
        time.sleep(1)
        os._exit(0)

    def __del__(self):
        try:
            self._ser.close()
        except:
            pass

    def _reader(self):
        try:
            while self._alive:
                source, endpoint, resp = self._recv_message()
                #reading message if socket is closed causes exceptions

                if resp is None or source is None:
                    # ignore message
                    continue

                if source == 'ws':
                    if endpoint in ['status', 'phoneInfo']:
                        # phone -> sdk message
                        self._ws_client.handle_response(endpoint, resp)
                    elif endpoint == 'log':
                        log.info(resp)
                    continue

                #log.info("message for endpoint " + str(endpoint) + " resp : " + str(resp))
                if DEBUG_PROTOCOL:
                    log.debug('<< ' + binascii.hexlify(resp))

                if endpoint in self._internal_endpoint_handlers:
                    resp = self._internal_endpoint_handlers[endpoint](endpoint, resp)

                if endpoint in self._endpoint_handlers and resp is not None:
                    self._endpoint_handlers[endpoint](endpoint, resp)
        except Exception, e:
            print str(e)
            log.error("Lost connection to Pebble")
            self._alive = False
            os._exit(-1)


    def _pack_message_data(self, lead, parts):
        pascal = map(lambda x: x[:255], parts)
        d = pack("b" + reduce(lambda x,y: str(x) + "p" + str(y), map(lambda x: len(x) + 1, pascal)) + "p", lead, *pascal)
        return d

    def _build_message(self, endpoint, data):
        return pack("!HH", len(data), endpoint)+data

    def _send_message(self, endpoint, data, callback = None):
        if endpoint not in self.endpoints:
            raise PebbleError(self.id, "Invalid endpoint specified")

        msg = self._build_message(self.endpoints[endpoint], data)

        if DEBUG_PROTOCOL:
            log.debug('>> ' + binascii.hexlify(msg))

        self._ser.write(msg)

    def _recv_message(self):
        if self._connection_type != 'serial':
            try:
                source, endpoint, resp, data = self._ser.read()
                if resp is None:
                    return None, None, None
            except TypeError:
                # the lightblue process has likely shutdown and cannot be read from
                self.alive = False
                return None, None, None
        else:
            data = self._ser.read(4)
            if len(data) == 0:
                return (None, None, None)
            elif len(data) < 4:
                raise PebbleError(self.id, "Malformed response with length "+str(len(data)))
            size, endpoint = unpack("!HH", data)
            resp = self._ser.read(size)
        if DEBUG_PROTOCOL:
            log.debug("Got message for endpoint %s of length %d" % (endpoint, len(resp)))
            log.debug('<<< ' + (data + resp).encode('hex'))

        return ("serial", endpoint, resp)

    def register_endpoint(self, endpoint_name, func):
        if endpoint_name not in self.endpoints:
            raise PebbleError(self.id, "Invalid endpoint specified")

        endpoint = self.endpoints[endpoint_name]
        self._endpoint_handlers[endpoint] = func

    def notification_sms(self, sender, body):

        """Send a 'SMS Notification' to the displayed on the watch."""

        ts = str(int(time.time())*1000)
        parts = [sender, body, ts]
        self._send_message("NOTIFICATION", self._pack_message_data(1, parts))

    def notification_email(self, sender, subject, body):

        """Send an 'Email Notification' to the displayed on the watch."""

        ts = str(int(time.time())*1000)
        parts = [sender, body, ts, subject]
        self._send_message("NOTIFICATION", self._pack_message_data(0, parts))

    def set_nowplaying_metadata(self, track, album, artist):

        """Update the song metadata displayed in Pebble's music app."""

        parts = [artist[:30], album[:30], track[:30]]
        self._send_message("MUSIC_CONTROL", self._pack_message_data(16, parts))

    def screenshot(self, progress_callback):
        self._send_message("SCREENSHOT", "\x00")
        return ScreenshotSync(self, "SCREENSHOT", progress_callback).get_data()

    def get_versions(self, async = False):

        """
        Retrieve a summary of version information for various software
        (firmware, bootloader, etc) running on the watch.
        """

        self._send_message("VERSION", "\x00")

        if not async:
            return EndpointSync(self, "VERSION").get_data()


    def list_apps_by_uuid(self, async=False):
        data = pack("b", 0x05)
        self._send_message("APP_MANAGER", data)
        if not async:
            return EndpointSync(self, "APP_MANAGER").get_data()

    def describe_app_by_uuid(self, uuid, uuid_is_string=True, async = False):
        if uuid_is_string:
            uuid = uuid.decode('hex')
        elif type(uuid) is uuid.UUID:
            uuid = uuid.bytes
        # else, assume it's a byte array

        data = pack("b", 0x06) + str(uuid)
        self._send_message("APP_MANAGER", data)

        if not async:
            return EndpointSync(self, "APP_MANAGER").get_data()

    def current_running_uuid(self, async = False):
        data = pack("b", 0x07)
        self._send_message("APP_MANAGER", data)
        if not async:
            return EndpointSync(self, "APP_MANAGER").get_data()


    def get_appbank_status(self, async = False):

        """
        Retrieve a list of all installed watch-apps.

        This is particularly useful when trying to locate a
        free app-bank to use when installing a new watch-app.
        """
        self._send_message("APP_MANAGER", "\x01")

        if not async:
            apps = EndpointSync(self, "APP_MANAGER").get_data()
            return apps if type(apps) is dict else { 'apps': [] }

    def remove_app(self, appid, index, async=False):

        """Remove an installed application from the target app-bank."""

        data = pack("!bII", 2, appid, index)
        self._send_message("APP_MANAGER", data)

        if not async:
            return EndpointSync(self, "APP_MANAGER").get_data()

    def remove_app_by_uuid(self, uuid_to_remove, uuid_is_string=True, async = False):

        """Remove an installed application by UUID."""

        if uuid_is_string:
            uuid_to_remove = uuid_to_remove.decode('hex')
        elif type(uuid_to_remove) is uuid.UUID:
            uuid_to_remove = uuid_to_remove.bytes
        # else, assume it's a byte array

        data = pack("b", 0x02) + str(uuid_to_remove)
        self._send_message("APP_MANAGER", data)

        if not async:
            return EndpointSync(self, "APP_MANAGER").get_data()

    def get_time(self, async = False):

        """Retrieve the time from the Pebble's RTC."""

        self._send_message("TIME", "\x00")

        if not async:
            return EndpointSync(self, "TIME").get_data()

    def set_time(self, timestamp):

        """Set the time stored in the target Pebble's RTC."""

        data = pack("!bL", 2, timestamp)
        self._send_message("TIME", data)


    def install_app_ws(self, pbw_path):
        self._ws_client = WSClient()
        f = open(pbw_path, 'r')
        data = f.read()
        self._ser.write(data, ws_cmd=WebSocketPebble.WS_CMD_APP_INSTALL)
        self._ws_client.listen()
        while not self._ws_client._received and not self._ws_client._error:
            pass
        if self._ws_client._topic == 'status' \
                and self._ws_client._response == 0:
            log.info("Installation successful")
            return True
        log.debug("WS Operation failed with response %s" % 
                                        self._ws_client._response)
        log.error("Failed to install %s" % repr(pbw_path))
        return False


    def get_phone_info(self):
        if self._connection_type != 'ws':
            return 'Unknown'

        self._ws_client = WSClient()
        # The first byte is reserved for future use as a protocol version ID
        #  and must be 0 for now. 
        data = pack("!b", 0)
        self._ser.write(data, ws_cmd=WebSocketPebble.WS_CMD_PHONE_INFO)
        self._ws_client.listen()
        while not self._ws_client._received and not self._ws_client._error:
          pass
        if self._ws_client._topic == 'phoneInfo':
          return self._ws_client._response
        else:
          log.error('get_phone_info: Unexpected response to "%s"' % self._ws_client._topic)
          return 'Unknown'

    def install_app_pebble_protocol(self, pbw_path, launch_on_install=True):

        bundle = PebbleBundle(pbw_path)
        if not bundle.is_app_bundle():
            raise PebbleError(self.id, "This is not an app bundle")

        app_metadata = bundle.get_app_metadata()
        self.remove_app_by_uuid(app_metadata['uuid'].bytes, uuid_is_string=False)

        apps = self.get_appbank_status()
        if not apps:
            raise PebbleError(self.id, "could not obtain app list; try again")

        first_free = 1
        for app in apps["apps"]:
            if app["index"] == first_free:
                first_free += 1
        if first_free == apps["banks"]:
            raise PebbleError(self.id, "All %d app banks are full" % apps["banks"])
        log.debug("Attempting to add app to bank %d of %d" % (first_free, apps["banks"]))

        binary = bundle.zip.read(bundle.get_application_info()['name'])
        if bundle.has_resources():
            resources = bundle.zip.read(bundle.get_resources_info()['name'])
        else:
            resources = None
        client = PutBytesClient(self, first_free, "BINARY", binary)
        self.register_endpoint("PUTBYTES", client.handle_message)
        client.init()
        while not client._done and not client._error:
            pass
        if client._error:
            raise PebbleError(self.id, "Failed to send application binary %s/pebble-app.bin" % pbw_path)

        if resources:
            client = PutBytesClient(self, first_free, "RESOURCES", resources)
            self.register_endpoint("PUTBYTES", client.handle_message)
            client.init()
            while not client._done and not client._error:
                pass
            if client._error:
                raise PebbleError(self.id, "Failed to send application resources %s/app_resources.pbpack" % pbw_path)

        time.sleep(2)
        self._add_app(first_free)
        time.sleep(2)

        if launch_on_install:
            self.launcher_message(app_metadata['uuid'].bytes, "RUNNING", uuid_is_string=False)

    def install_app(self, pbw_path, launch_on_install=True):

        """Install an app bundle (*.pbw) to the target Pebble."""

        if self._connection_type == 'websocket':
            self.install_app_ws(pbw_path)
        else:
            self.install_app_pebble_protocol(pbw_path, launch_on_install)

    def install_firmware(self, pbz_path, recovery=False):

        """Install a firmware bundle to the target watch."""

        resources = None
        with zipfile.ZipFile(pbz_path) as pbz:
            binary = pbz.read("tintin_fw.bin")
            if not recovery:
                resources = pbz.read("system_resources.pbpack")

        self.system_message("FIRMWARE_START")
        time.sleep(2)

        if resources:
            client = PutBytesClient(self, 0, "SYS_RESOURCES", resources)
            self.register_endpoint("PUTBYTES", client.handle_message)
            client.init()
            while not client._done and not client._error:
                pass
            if client._error:
                raise PebbleError(self.id, "Failed to send firmware resources %s/system_resources.pbpack" % pbz_path)


        client = PutBytesClient(self, 0, "RECOVERY" if recovery else "FIRMWARE", binary)
        self.register_endpoint("PUTBYTES", client.handle_message)
        client.init()
        while not client._done and not client._error:
            pass
        if client._error:
            raise PebbleError(self.id, "Failed to send firmware binary %s/tintin_fw.bin" % pbz_path)

        self.system_message("FIRMWARE_COMPLETE")

    def launcher_message(self, app_uuid, key_value, uuid_is_string = True, async = False):
        """ send an appication message to launch or kill a specified application"""

        launcher_keys = {
                "RUN_STATE_KEY": 1,
        }

        launcher_key_values = {
                "NOT_RUNNING": b'\x00',
                "RUNNING": b'\x01'
        }

        if key_value not in launcher_key_values:
            raise PebbleError(self.id, "not a valid application message")

        if uuid_is_string:
            app_uuid = app_uuid.decode('hex')
        elif type(app_uuid) is uuid.UUID:
            app_uuid = app_uuid.bytes
        #else we can assume it's a byte array

        amsg = AppMessage()

        # build and send a single tuple-sized launcher command
        app_message_tuple = amsg.build_tuple(launcher_keys["RUN_STATE_KEY"], "UINT", launcher_key_values[key_value])
        app_message_dict = amsg.build_dict(app_message_tuple)
        packed_message = amsg.build_message(app_message_dict, "PUSH", app_uuid)
        self._send_message("LAUNCHER", packed_message)

        # wait for either ACK or NACK response
        if not async:
            return EndpointSync(self, "LAUNCHER").get_data()

    def app_message_send_tuple(self, app_uuid, key, tuple_datatype, tuple_data):

        """  Send a Dictionary with a single tuple to the app corresponding to UUID """

        app_uuid = app_uuid.decode('hex')
        amsg = AppMessage()

        app_message_tuple = amsg.build_tuple(key, tuple_datatype, tuple_data)
        app_message_dict = amsg.build_dict(app_message_tuple)
        packed_message = amsg.build_message(app_message_dict, "PUSH", app_uuid)
        self._send_message("APPLICATION_MESSAGE", packed_message)

    def app_message_send_string(self, app_uuid, key, string):

        """  Send a Dictionary with a single tuple of type CSTRING to the app corresponding to UUID """

        # NULL terminate and pack
        string = string + '\0'
        fmt =  '<' + str(len(string)) + 's'
        string = pack(fmt, string);

        self.app_message_send_tuple(app_uuid, key, "CSTRING", string)

    def app_message_send_uint(self, app_uuid, key, tuple_uint):

        """  Send a Dictionary with a single tuple of type UINT to the app corresponding to UUID """

        fmt = '<' + str(tuple_uint.bit_length() / 8 + 1) + 'B'
        tuple_uint = pack(fmt, tuple_uint)

        self.app_message_send_tuple(app_uuid, key, "UINT", tuple_uint)

    def app_message_send_int(self, app_uuid, key, tuple_int):

        """  Send a Dictionary with a single tuple of type INT to the app corresponding to UUID """

        fmt = '<' + str(tuple_int.bit_length() / 8 + 1) + 'b'
        tuple_int = pack(fmt, tuple_int)

        self.app_message_send_tuple(app_uuid, key, "INT", tuple_int)

    def app_message_send_byte_array(self, app_uuid, key, tuple_byte_array):

        """  Send a Dictionary with a single tuple of type BYTE_ARRAY to the app corresponding to UUID """

        # Already packed, fix endianness
        tuple_byte_array = tuple_byte_array[::-1]

        self.app_message_send_tuple(app_uuid, key, "BYTE_ARRAY", tuple_byte_array)

    def system_message(self, command):

        """
        Send a 'system message' to the watch.

        These messages are used to signal important events/state-changes to the watch firmware.
        """

        commands = {
                "FIRMWARE_AVAILABLE": 0,
                "FIRMWARE_START": 1,
                "FIRMWARE_COMPLETE": 2,
                "FIRMWARE_FAIL": 3,
                "FIRMWARE_UP_TO_DATE": 4,
                "FIRMWARE_OUT_OF_DATE": 5,
                "BLUETOOTH_START_DISCOVERABLE": 6,
                "BLUETOOTH_END_DISCOVERABLE": 7
        }
        if command not in commands:
            raise PebbleError(self.id, "Invalid command \"%s\"" % command)
        data = pack("!bb", 0, commands[command])
        log.debug("Sending command %s (code %d)" % (command, commands[command]))
        self._send_message("SYSTEM_MESSAGE", data)



    def ping(self, cookie = 0xDEC0DE, async = False):

        """Send a 'ping' to the watch to test connectivity."""

        data = pack("!bL", 0, cookie)
        self._send_message("PING", data)

        if not async:
            return EndpointSync(self, "PING").get_data()

    phone_control_commands = {
        "ANSWER" : 1,
        "HANGUP" : 2,
        "GET_STATE" : 3,
        "INCOMING_CALL" : 4,
        "OUTGOING_CALL" : 5,
        "MISSED_CALL" : 6,
        "RING" : 7,
        "START" : 8,
        "END" : 9,
    }

    def phone_call_start(self, number, name, incoming = True, cookie = 0):

        """Send a 'phone_control' notification for incoming call."""

        fmt = "!bL" + str(1+len(number)) + "p" + str(1+len(name)) + "p"
        event = "INCOMING_CALL" if incoming else "OUTGOING_CALL"
        data = pack(fmt, self.phone_control_commands[event], cookie, number, name)
        self._send_message("PHONE_CONTROL", data)

    def phone_event(self, event, cookie = 0):

        """Send a 'phone_control' notification of start."""

        data = pack("!bL", self.phone_control_commands[event], cookie)
        self._send_message("PHONE_CONTROL", data)

    def reset(self):

        """Reset the watch remotely."""

        self._send_message("RESET", "\x00")

    def dump_logs(self, generation_number):
        """Dump the saved logs from the watch.

        Arguments:
        generation_number -- The genration to dump, where 0 is the current boot and 3 is the oldest boot.
        """

        if generation_number > 3:
            raise Exception("Invalid generation number %u, should be [0-3]" % generation_number)

        log.info('=== Generation %u ===' % generation_number)

        class LogDumpClient(object):
            def __init__(self, pebble):
                self.done = False
                self._pebble = pebble

            def parse_log_dump_response(self, endpoint, data):
                if (len(data) < 5):
                    log.warn("Unable to decode log dump message (length %d is less than 8)" % len(data))
                    return

                response_type, response_cookie = unpack("!BI", data[:5])
                if response_type == 0x81:
                    self.done = True
                    return
                elif response_type != 0x80 or response_cookie != cookie:
                    log.info("Received unexpected message with type 0x%x cookie %u expected 0x80 %u" %
                        (response_type, response_cookie, cookie))
                    self.done = True
                    return

                timestamp, str_level, filename, linenumber, message = self._pebble._parse_log_response(data[5:])

                timestamp_str = datetime.datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')

                log.info("{} {} {}:{}> {}".format(str_level, timestamp_str, filename, linenumber, message))

        client = LogDumpClient(self)
        self.register_endpoint("LOG_DUMP", client.parse_log_dump_response)

        import random
        cookie = random.randint(0, pow(2, 32) - 1)
        self._send_message("LOG_DUMP", pack("!BBI", 0x10, generation_number, cookie))

        while not client.done:
            time.sleep(1)

    def app_log_enable(self):
        log.info("Enabling application logging...")
        self._send_message("APP_LOGS", pack("!B", 0x01))

    def app_log_disable(self):
        log.info("Disabling application logging...")
        self._send_message("APP_LOGS", pack("!B", 0x00))

    def disconnect(self):

        """Disconnect from the target Pebble."""

        self._alive = False
        self._ser.close()

    def set_print_pbl_logs(self, value):
        self.print_pbl_logs = value

    def _add_app(self, index):
        data = pack("!bI", 3, index)
        self._send_message("APP_MANAGER", data)

    def _screenshot_response(self, endpoint, data):
        return data

    def _ping_response(self, endpoint, data):
        restype, retcookie = unpack("!bL", data)
        return retcookie

    def _get_time_response(self, endpoint, data):
        restype, timestamp = unpack("!bL", data)
        return timestamp

    def _system_message_response(self, endpoint, data):
        if len(data) >= 2:
            log.info("Got system message %s" % repr(unpack('!bb', data[:2])))
        else:
            log.info("Got 'unknown' system message: " + binascii.hexlify(data))

    def _parse_log_response(self, log_message_data):
        timestamp, level, msgsize, linenumber = unpack("!IBBH", log_message_data[:8])
        filename = log_message_data[8:24].decode('utf-8')
        message = log_message_data[24:24+msgsize].decode('utf-8')

        str_level = self.log_levels[level] if level in self.log_levels else "?"

        return timestamp, str_level, filename, linenumber, message

    def _log_response(self, endpoint, data):
        if (len(data) < 8):
            log.warn("Unable to decode log message (length %d is less than 8)" % len(data))
            return

        if self.print_pbl_logs:
            timestamp, str_level, filename, linenumber, message = self._parse_log_response(data)

            log.info("{} {} {} {} {}".format(timestamp, str_level, filename, linenumber, message))

    def _print_crash_message(self, crashed_uuid, crashed_pc, crashed_lr):
        # Read the current projects UUID from it's appinfo.json. If we can't do this or the uuid doesn't match
        # the uuid of the crashed app we don't print anything.
        from PblProjectCreator import check_project_directory, PebbleProjectException
        try:
            check_project_directory()
        except PebbleProjectException:
            # We're not in the project directory
            return

        with open('appinfo.json', 'r') as f:
            try:
                app_info = json.load(f)
                app_uuid = uuid.UUID(app_info['uuid'])
            except ValueError as e:
                log.warn("Could not look up debugging symbols.")
                log.warn("Failed parsing appinfo.json")
                log.warn(str(e))
                return

        if (app_uuid != crashed_uuid):
            # Someone other than us crashed, just bail
            return


        if not os.path.exists(APP_ELF_PATH):
            log.warn("Could not look up debugging symbols.")
            log.warn("Could not find ELF file: %s" % APP_ELF_PATH)
            log.warn("Please try rebuilding your project")
            return


        def print_register(register_name, addr_str):
            if (addr_str[0] == '?') or (int(addr_str, 16) > 0x20000):
                # We log '???' when the reigster isn't available

                # The firmware translates app crash addresses to be relative to the start of the firmware
                # image. We filter out addresses that are higher than 128k since we know those higher addresses
                # are most likely from the firmware itself and not the app

                result = '???'
            else:
                result = sh.arm_none_eabi_addr2line(addr_str, exe=APP_ELF_PATH).strip()

            log.warn("%24s %10s %s", register_name + ':', addr_str, result)

        print_register("Program Counter (PC)", crashed_pc)
        print_register("Link Register (LR)", crashed_lr)


    def _app_log_response(self, endpoint, data):
        if (len(data) < 8):
            log.warn("Unable to decode log message (length %d is less than 8)" % len(data))
            return

        app_uuid = uuid.UUID(bytes=data[0:16])
        timestamp, str_level, filename, linenumber, message = self._parse_log_response(data[16:])

        log.info("{} {}:{} {}".format(str_level, filename, linenumber, message))

        # See if the log message we printed matches the message we print when we crash. If so, try to provide
        # some additional information by looking up the filename and linenumber for the symbol we crasehd at.
        m = re.search('App fault! ({[0-9a-fA-F\-]+}) PC: (\S+) LR: (\S+)', message)
        if m:
            crashed_uuid_str = m.group(1)
            crashed_uuid = uuid.UUID(crashed_uuid_str)

            self._print_crash_message(crashed_uuid, m.group(2), m.group(3))

    def _appbank_status_response(self, endpoint, data):
        def unpack_uuid(data):
            UUID_FORMAT = "{}{}{}{}-{}{}-{}{}-{}{}-{}{}{}{}{}{}"
            uuid = unpack("!bbbbbbbbbbbbbbbb", data)
            uuid = ["%02x" % (x & 0xff) for x in uuid]
            return UUID_FORMAT.format(*uuid)
        apps = {}
        restype, = unpack("!b", data[0])

        app_install_message = {
                0: "app available",
                1: "app removed",
                2: "app updated"
        }

        if restype == 1:
            apps["banks"], apps_installed = unpack("!II", data[1:9])
            apps["apps"] = []

            appinfo_size = 78
            offset = 9
            for i in xrange(apps_installed):
                app = {}
                try:
                    app["id"], app["index"], app["name"], app["company"], app["flags"], app["version"] = \
                            unpack("!II32s32sIH", data[offset:offset+appinfo_size])
                    app["name"] = app["name"].replace("\x00", "")
                    app["company"] = app["company"].replace("\x00", "")
                    apps["apps"] += [app]
                except:
                    if offset+appinfo_size > len(data):
                        log.warn("Couldn't load bank %d; remaining data = %s" % (i,repr(data[offset:])))
                    else:
                        raise
                offset += appinfo_size

            return apps

        elif restype == 2:
            message_id = unpack("!I", data[1:])
            message_id = int(''.join(map(str, message_id)))
            return app_install_message[message_id]

        elif restype == 5:
            apps_installed = unpack("!I", data[1:5])[0]
            uuids = []

            uuid_size = 16
            offset = 5
            for i in xrange(apps_installed):
                uuid = unpack_uuid(data[offset:offset+uuid_size])
                offset += uuid_size
                uuids.append(uuid)
            return uuids

        elif restype == 6:
            app = {}
            app["version"], app["name"], app["company"] = unpack("H32s32s", data[1:])
            app["name"] = app["name"].replace("\x00", "")
            app["company"] = app["company"].replace("\x00", "")
            return app

        elif restype == 7:
            uuid = unpack_uuid(data[1:17])
            return uuid

        else:
            return restype

    def _version_response(self, endpoint, data):
        fw_names = {
                0: "normal_fw",
                1: "recovery_fw"
        }

        resp = {}
        for i in xrange(2):
            fwver_size = 47
            offset = i*fwver_size+1
            fw = {}
            fw["timestamp"],fw["version"],fw["commit"],fw["is_recovery"], \
                    fw["hardware_platform"],fw["metadata_ver"] = \
                    unpack("!i32s8s?bb", data[offset:offset+fwver_size])

            fw["version"] = fw["version"].replace("\x00", "")
            fw["commit"] = fw["commit"].replace("\x00", "")

            fw_name = fw_names[i]
            resp[fw_name] = fw

        resp["bootloader_timestamp"],resp["hw_version"],resp["serial"] = \
                unpack("!L9s12s", data[95:120])

        resp["hw_version"] = resp["hw_version"].replace("\x00","")

        btmac_hex = binascii.hexlify(data[120:126])
        resp["btmac"] = ":".join([btmac_hex[i:i+2].upper() for i in reversed(xrange(0, 12, 2))])

        return resp

    def _application_message_response(self, endpoint, data):
        app_messages = {
                b'\x01': "PUSH",
                b'\x02': "REQUEST",
                b'\xFF': "ACK",
                b'\x7F': "NACK"
        }

        if len(data) > 1:
            rest = data[1:]
        else:
            rest = ''
        if data[0] in app_messages:
            return app_messages[data[0]] + rest


    def _phone_version_response(self, endpoint, data):
        session_cap = {
                "GAMMA_RAY" : 0x80000000,
        }
        remote_cap = {
                "TELEPHONY" : 16,
                "SMS" : 32,
                "GPS" : 64,
                "BTLE" : 128,
                "CAMERA_REAR" : 256,
                "ACCEL" : 512,
                "GYRO" : 1024,
                "COMPASS" : 2048,
        }
        os = {
                "UNKNOWN" : 0,
                "IOS" : 1,
                "ANDROID" : 2,
                "OSX" : 3,
                "LINUX" : 4,
                "WINDOWS" : 5,
        }

        # Then session capabilities, android adds GAMMA_RAY and it's
        # the only session flag so far
        session = session_cap["GAMMA_RAY"]

        # Then phone capabilities, android app adds TELEPHONY and SMS,
        # and the phone type (we know android works for now)
        remote = remote_cap["TELEPHONY"] | remote_cap["SMS"] | os["ANDROID"]

        msg = pack("!biII", 1, -1, session, remote)
        self._send_message("PHONE_VERSION", msg);

    def _music_control_response(self, endpoint, data):
        event, = unpack("!b", data)

        event_names = {
                1: "PLAYPAUSE",
                2: "PAUSE",
                3: "PLAY",
                4: "NEXT",
                5: "PREVIOUS",
                6: "VOLUME_UP",
                7: "VOLUME_DOWN",
                8: "GET_NOW_PLAYING",
                9: "SEND_NOW_PLAYING",
        }

        return event_names[event] if event in event_names else None


class AppMessage(object):
# tools to build a valid app message
    def build_tuple(self, key, data_type, data):
        """ make a single app_message tuple"""
        # available app message datatypes:
        tuple_datatypes = {
                "BYTE_ARRAY": b'\x00',
                "CSTRING": b'\x01',
                "UINT": b'\x02',
                "INT": b'\x03'
        }

        # build the message_tuple
        app_message_tuple = OrderedDict([
                ("KEY", pack('<L', key)),
                ("TYPE", tuple_datatypes[data_type]),
                ("LENGTH", pack('<H', len(data))),
                ("DATA", data)
        ])

        return app_message_tuple

    def build_dict(self, tuple_of_tuples):
        """ make a dictionary from a list of app_message tuples"""
        # note that "TUPLE" can refer to 0 or more tuples. Tuples must be correct endian-ness already
        tuple_count = len(tuple_of_tuples)
        # make the bytearray from the flattened tuples
        tuple_total_bytes = ''.join(item for item in itertools.chain(*tuple_of_tuples.values()))
        # now build the dict
        app_message_dict = OrderedDict([
                ("TUPLECOUNT", pack('B', tuple_count)),
                ("TUPLE", tuple_total_bytes)
        ])
        return app_message_dict

    def build_message(self, dict_of_tuples, command, uuid, transaction_id=b'\x00'):
        """ build the app_message intended for app with matching uuid"""
        # NOTE: uuid must be a byte array
        # available app_message commands:
        app_messages = {
                "PUSH": b'\x01',
                "REQUEST": b'\x02',
                "ACK": b'\xFF',
                "NACK": b'\x7F'
        }
        # finally build the entire message
        app_message = OrderedDict([
                ("COMMAND", app_messages[command]),
                ("TRANSACTIONID", transaction_id),
                ("UUID", uuid),
                ("DICT", ''.join(dict_of_tuples.values()))
        ])
        return ''.join(app_message.values())


class WSClient(object):
    states = {
      "IDLE": 0,
      "LISTENING": 1,
    }

    def __init__(self):
      self._state = self.states["IDLE"]
      self._response = None
      self._topic = None
      self._received = False
      self._error = False
      self._timer = threading.Timer(30.0, self.timeout)

    def timeout(self):
      if (self._state != self.states["LISTENING"]):
        log.error("Timeout triggered when not listening")
        return
      self._error = True
      self._received = False
      self._state = self.states["IDLE"]

    def listen(self):
      self._state = self.states["LISTENING"]
      self._received = False
      self._error = False
      self._timer.start()

    def handle_response(self, topic, response):
      if self._state != self.states["LISTENING"]:
        log.debug("Unexpected status message")
        self._error = True

      self._timer.cancel()
      self._topic = topic
      self._response = response;
      self._received = True


class PutBytesClient(object):
    states = {
            "NOT_STARTED": 0,
            "WAIT_FOR_TOKEN": 1,
            "IN_PROGRESS": 2,
            "COMMIT": 3,
            "COMPLETE": 4,
            "FAILED": 5
    }

    transfer_types = {
            "FIRMWARE": 1,
            "RECOVERY": 2,
            "SYS_RESOURCES": 3,
            "RESOURCES": 4,
            "BINARY": 5
    }

    def __init__(self, pebble, index, transfer_type, buffer):
        self._pebble = pebble
        self._state = self.states["NOT_STARTED"]
        self._transfer_type = self.transfer_types[transfer_type]
        self._buffer = buffer
        self._index = index
        self._done = False
        self._error = False

    def init(self):
        data = pack("!bIbb", 1, len(self._buffer), self._transfer_type, self._index)
        self._pebble._send_message("PUTBYTES", data)
        self._state = self.states["WAIT_FOR_TOKEN"]

    def wait_for_token(self, resp):
        res, = unpack("!b", resp[0])
        if res != 1:
            log.error("init failed with code %d" % res)
            self._error = True
            return
        self._token, = unpack("!I", resp[1:])
        self._left = len(self._buffer)
        self._state = self.states["IN_PROGRESS"]
        self.send()

    def in_progress(self, resp):
        res, = unpack("!b", resp[0])
        if res != 1:
            self.abort()
            return
        if self._left > 0:
            self.send()
            log.debug("Sent %d of %d bytes" % (len(self._buffer)-self._left, len(self._buffer)))
        else:
            self._state = self.states["COMMIT"]
            self.commit()

    def commit(self):
        data = pack("!bII", 3, self._token & 0xFFFFFFFF, stm32_crc.crc32(self._buffer))
        self._pebble._send_message("PUTBYTES", data)

    def handle_commit(self, resp):
        res, = unpack("!b", resp[0])
        if res != 1:
            self.abort()
            return
        self._state = self.states["COMPLETE"]
        self.complete()

    def complete(self):
        data = pack("!bI", 5, self._token & 0xFFFFFFFF)
        self._pebble._send_message("PUTBYTES", data)

    def handle_complete(self, resp):
        res, = unpack("!b", resp[0])
        if res != 1:
            self.abort()
            return
        self._done = True

    def abort(self):
        msgdata = pack("!bI", 4, self._token & 0xFFFFFFFF)
        self._pebble._send_message("PUTBYTES", msgdata)
        self._error = True

    def send(self):
        datalen =  min(self._left, 2000)
        rg = len(self._buffer)-self._left
        msgdata = pack("!bII", 2, self._token & 0xFFFFFFFF, datalen)
        msgdata += self._buffer[rg:rg+datalen]
        self._pebble._send_message("PUTBYTES", msgdata)
        self._left -= datalen

    def handle_message(self, endpoint, resp):
        if self._state == self.states["WAIT_FOR_TOKEN"]:
            self.wait_for_token(resp)
        elif self._state == self.states["IN_PROGRESS"]:
            self.in_progress(resp)
        elif self._state == self.states["COMMIT"]:
            self.handle_commit(resp)
        elif self._state == self.states["COMPLETE"]:
            self.handle_complete(resp)

########NEW FILE########
__FILENAME__ = stm32_crc
import array
import sys

CRC_POLY = 0x04C11DB7

def process_word(data, crc=0xffffffff):
    if (len(data) < 4):
        d_array = array.array('B', data)
        for x in range(0, 4 - len(data)):
            d_array.insert(0,0)
        d_array.reverse()
        data = d_array.tostring()

    d = array.array('I', data)[0]
    crc = crc ^ d

    for i in xrange(0, 32):
        if (crc & 0x80000000) != 0:
            crc = (crc << 1) ^ CRC_POLY
        else:
            crc = (crc << 1)

    result = crc & 0xffffffff
    return result

def process_buffer(buf, c = 0xffffffff):
    word_count = len(buf) / 4
    if (len(buf) % 4 != 0):
        word_count += 1

    crc = c
    for i in xrange(0, word_count):
        crc = process_word(buf[i * 4 : (i + 1) * 4], crc)
    return crc

def crc32(data):
    return process_buffer(data)

########NEW FILE########
__FILENAME__ = VersionGenerated
SDK_VERSION = "2.0-BETA2"
########NEW FILE########
__FILENAME__ = WebSocketPebble
import errno
import sys
import logging
from websocket import *
from struct import unpack
from struct import pack

# This file contains the libpebble websocket client.
# Based on websocket.py from:
# https://github.com/liris/websocket-client

WS_CMD_WATCH_TO_PHONE = 0x00
WS_CMD_PHONE_TO_WATCH = 0x01
WS_CMD_PHONE_APP_LOG = 0x02
WS_CMD_SERVER_LOG = 0x03
WS_CMD_APP_INSTALL = 0x04
WS_CMD_STATUS = 0x5
WS_CMD_PHONE_INFO = 0x06

class WebSocketPebble(WebSocket):

######## libPebble Bridge Methods #########

    def write(self, payload, opcode = ABNF.OPCODE_BINARY, ws_cmd = WS_CMD_PHONE_TO_WATCH):
        """
        BRIDGES THIS METHOD:
        def write(self, message):
            try:
                self.send_queue.put(message)
                self.bt_message_sent.wait()
            except:
                self.bt_teardown.set()
                if self.debug_protocol:
                    log.debug("LightBlue process has shutdown (queue write)")

        """
        # Append command byte to the payload:
        payload = pack("B", ws_cmd) + payload
        frame = ABNF.create_frame(payload, opcode)
        if self.get_mask_key:
            frame.get_mask_key = self.get_mask_key
        data = frame.format()

        sent = 0
        while sent < len(data):
            sent += self.sock.send(data[sent:])
            if traceEnabled:
                logging.debug('send>>> ' + data.encode('hex'))

    def read(self):
        """
        BRIDGES THIS METHOD:
        def read(self):
            try:
                return self.rec_queue.get()
            except Queue.Empty:
                return (None, None, '')
            except:
                self.bt_teardown.set()
                if self.debug_protocol:
                    log.debug("LightBlue process has shutdown (queue read)")
                return (None, None, '')
                
        NOTE: The return value of this method was modified from 3 tuples to
        4 tuples in order to support multiple possible WS_CMD id's besides
        just WS_CMD_WATCH_TO_PHONE and WS_CMD_STATUS. Now, the first item in
        the tuple (source) identifies which WS_CMD we received. The other
        transports (LightBlue, etc.), if/when they are re-instantiated into
        active use will have to be updated to return this new 4 item tuple. 
                
        retval:   (source, topic, response, data)
            source can be either 'ws' or 'watch'
            if source is 'watch', then topic is the endpoint identifier
            if source is 'ws', then topic is either 'status','phoneInfo',
                    or 'log'
            
        """
        opcode, data = self.recv_data()
        ws_cmd = unpack('!b',data[0])
        if ws_cmd[0]==WS_CMD_SERVER_LOG:
            logging.debug("Server: %s" % repr(data[1:]))
        if ws_cmd[0]==WS_CMD_PHONE_APP_LOG:
            logging.debug("Log: %s" % repr(data[1:]))
            return ('ws', 'log', data[1:], data)
        if ws_cmd[0]==WS_CMD_PHONE_TO_WATCH:
            logging.debug("Phone ==> Watch: %s" % data[1:].encode("hex"))
        if ws_cmd[0]==WS_CMD_WATCH_TO_PHONE:
            logging.debug("Watch ==> Phone: %s" % data[1:].encode("hex"))
            size, endpoint = unpack("!HH", data[1:5])
            resp = data[5:]
            return ('watch', endpoint, resp, data[1:5])
        if ws_cmd[0]==WS_CMD_STATUS:
            logging.debug("Status: %s" % repr(data[1:]))
            status = unpack("I", data[1:5])[0]
            return ('ws', 'status', status, data[1:5])
        if ws_cmd[0]==WS_CMD_PHONE_INFO:
            logging.debug("Phone info: %s" % repr(data[1:]))
            response = data[1:]
            return ('ws', 'phoneInfo', response, data)
        else:
            return (None, None, None, data)



######################################

def create_connection(host, port=9000, timeout=None, connect_timeout=None, **options):
    """
    connect to ws://host:port and return websocket object.

    Connect to ws://host:port and return the WebSocket object.
    Passing optional timeout parameter will set the timeout on the socket.
    If no timeout is supplied, the global default timeout setting returned by getdefauttimeout() is used.
    You can customize using 'options'.
    If you set "header" dict object, you can set your own custom header.

    >>> conn = create_connection("ws://echo.websocket.org/",
         ...     header=["User-Agent: MyProgram",
         ...             "x-custom: header"])


    timeout: socket timeout time. This value is integer.
             if you set None for this value, it means "use default_timeout value"

    options: current support option is only "header".
             if you set header as dict value, the custom HTTP headers are added.
    """

    url = "ws://{}:{}".format(host, port)
    try:
        sockopt = options.get("sockopt", ())
        websock = WebSocketPebble(sockopt=sockopt)
        websock.settimeout(connect_timeout is not None and connect_timeout or default_timeout)
        websock.connect(url, **options)
        websock.settimeout(timeout is not None and timeout or default_timeout)
    except socket.timeout as e:
        logging.error("Could not connect to phone at {}:{}. Connection timed out".format(host, port))
        os._exit(-1)
    except socket.error as e:
        if e.errno == errno.ECONNREFUSED:
            logging.error("Could not connect to phone at {}:{}. "
                      "Ensure that 'Developer Connection' is enabled in the Pebble app.".format(host, port))
            os._exit(-1)
        else:
            raise e
    except WebSocketConnectionClosedException as e:
        logging.error("Connection was rejected. The Pebble app is already connected to another client.")
        os._exit(-1)
    return websock

_MAX_INTEGER = (1 << 32) -1
_AVAILABLE_KEY_CHARS = range(0x21, 0x2f + 1) + range(0x3a, 0x7e + 1)
_MAX_CHAR_BYTE = (1<<8) -1




if __name__ == "__main__":
    enableTrace(True)
    if len(sys.argv) < 2:
        print "Need the WebSocket server address, i.e. ws://localhost:9000"
        sys.exit(1)
    ws = create_connection(sys.argv[1])
    print("Sending 'Hello, World'...")
    ws.send("Hello, World")
    print("Sent")
    print("Receiving...")
    result = ws.recv()
    print("Received '%s'" % result)

########NEW FILE########
__FILENAME__ = pebble
#!/usr/bin/env python

import argparse
import logging
import sys

import pebble.PblAnalytics as PblAnalytics

# Catch any missing python dependencies so we can send an event to analytics
try:
    import pebble as libpebble
    from pebble.PblProjectCreator   import (PblProjectCreator, 
                                            InvalidProjectException, 
                                            OutdatedProjectException)
    from pebble.PblProjectConverter import PblProjectConverter
    from pebble.PblBuildCommand     import PblBuildCommand, PblCleanCommand
    from pebble.LibPebblesCommand   import *
except Exception as e:
    logging.basicConfig(format='[%(levelname)-8s] %(message)s', 
                    level = logging.DEBUG)
    PblAnalytics.missing_python_dependency_evt(str(e))
    raise

class PbSDKShell:
    commands = []

    def __init__(self):
        self.commands.append(PblProjectCreator())
        self.commands.append(PblProjectConverter())
        self.commands.append(PblBuildCommand())
        self.commands.append(PblCleanCommand())
        self.commands.append(PblInstallCommand())
        self.commands.append(PblInstallFWCommand())
        self.commands.append(PblPingCommand())
        self.commands.append(PblListCommand())
        self.commands.append(PblRemoteCommand())
        self.commands.append(PblRemoveCommand())
        self.commands.append(PblCurrentAppCommand())
        self.commands.append(PblListUuidCommand())
        self.commands.append(PblLogsCommand())
        self.commands.append(PblReplCommand())
        self.commands.append(PblScreenshotCommand())
        self.commands.append(PblLaunchApp())

    def _get_version(self):
        try:
            from pebble.VersionGenerated import SDK_VERSION
            return SDK_VERSION
        except:
            return "'Development'"
        

    def main(self):
        parser = argparse.ArgumentParser(description = 'Pebble SDK Shell')
        parser.add_argument('--debug', action="store_true", 
                            help="Enable debugging output")
        parser.add_argument('--version', action='version', 
                            version='PebbleSDK %s' % self._get_version())
        subparsers = parser.add_subparsers(dest="command", title="Command", 
                                           description="Action to perform")
        for command in self.commands:
            subparser = subparsers.add_parser(command.name, help = command.help)
            command.configure_subparser(subparser)
        args = parser.parse_args()

        log_level = logging.INFO
        if args.debug:
            log_level = logging.DEBUG

        logging.basicConfig(format='[%(levelname)-8s] %(message)s', 
                            level = log_level)

        return self.run_action(args.command, args)

    def run_action(self, action, args):
        # Find the extension that was called
        command = [x for x in self.commands if x.name == args.command][0]

        try:
            retval = command.run(args)
            if retval:
                PblAnalytics.cmd_fail_evt(args.command, 'unknown error')
            else:
                cmdName = args.command
                if cmdName == 'install' and args.logs is True:
                    cmdName = 'install --logs'
                PblAnalytics.cmd_success_evt(cmdName)
            return retval
                
        except libpebble.PebbleError as e:
            PblAnalytics.cmd_fail_evt(args.command, 'pebble error')
            if args.debug:
                raise e
            else:
                logging.error(e)
                return 1
            
        except ConfigurationException as e:
            PblAnalytics.cmd_fail_evt(args.command, 'configuration error')
            logging.error(e)
            return 1
        
        except InvalidProjectException as e:
            PblAnalytics.cmd_fail_evt(args.command, 'invalid project')
            logging.error("This command must be run from a Pebble project "
                          "directory")
            return 1
        
        except OutdatedProjectException as e:
            PblAnalytics.cmd_fail_evt(args.command, 'outdated project')
            logging.error("The Pebble project directory is using an outdated "
                          "version of the SDK!")
            logging.error("Try running `pebble convert-project` to update the "
                          "project")
            return 1
        
        except NoCompilerException as e:
            PblAnalytics.missing_tools_evt()
            logging.error("The compiler/linker tools could not be found. "
                          "Ensure that the arm-cs-tools directory is present "
                          "in the Pebble SDK directory (%s)" % 
                          PblCommand().sdk_path(args))
            return 1
        
        except BuildErrorException as e:
            PblAnalytics.cmd_fail_evt(args.command, 'compilation error')
            logging.error("A compilation error occurred")
            return 1
        
        except AppTooBigException as e:
            PblAnalytics.cmd_fail_evt(args.command, 'application too big')
            logging.error("The built application is too big")
            return 1
        
        except Exception as e:
            PblAnalytics.cmd_fail_evt(args.command, 'unhandled exception: %s' %
                                 str(e))
            logging.error(str(e))
            return 1


if __name__ == '__main__':
    retval = PbSDKShell().main()
    if retval is None:
        retval = 0
    sys.exit(retval)


########NEW FILE########
